"""
BAEL - Advanced Database Abstraction Layer
Multi-database support with migrations, ORM, and query building.

Features:
- Multiple database backends (SQLite, PostgreSQL, MySQL)
- Connection pooling
- Query builder
- Migrations
- ORM-like models
- Transaction management
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, List, Optional, Tuple, Type,
                    TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MEMORY = "memory"


class ColumnType(Enum):
    """Column data types."""
    INTEGER = "INTEGER"
    TEXT = "TEXT"
    REAL = "REAL"
    BLOB = "BLOB"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    JSON = "JSON"
    UUID = "UUID"


class JoinType(Enum):
    """SQL join types."""
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Column:
    """Table column definition."""
    name: str
    type: ColumnType
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    default: Any = None
    foreign_key: Optional[str] = None  # "table.column"

    def to_sql(self, dialect: str = "sqlite") -> str:
        """Generate SQL column definition."""
        parts = [self.name, self.type.value]

        if self.primary_key:
            parts.append("PRIMARY KEY")
            if dialect == "sqlite" and self.type == ColumnType.INTEGER:
                parts.append("AUTOINCREMENT")

        if not self.nullable and not self.primary_key:
            parts.append("NOT NULL")

        if self.unique and not self.primary_key:
            parts.append("UNIQUE")

        if self.default is not None:
            if isinstance(self.default, str):
                parts.append(f"DEFAULT '{self.default}'")
            else:
                parts.append(f"DEFAULT {self.default}")

        return " ".join(parts)


@dataclass
class Table:
    """Table definition."""
    name: str
    columns: List[Column] = field(default_factory=list)

    def to_sql(self, dialect: str = "sqlite") -> str:
        """Generate CREATE TABLE SQL."""
        columns_sql = ",\n    ".join(
            col.to_sql(dialect) for col in self.columns
        )

        # Add foreign keys
        fk_sql = []
        for col in self.columns:
            if col.foreign_key:
                ref_table, ref_col = col.foreign_key.split(".")
                fk_sql.append(
                    f"FOREIGN KEY ({col.name}) REFERENCES {ref_table}({ref_col})"
                )

        if fk_sql:
            columns_sql += ",\n    " + ",\n    ".join(fk_sql)

        return f"CREATE TABLE IF NOT EXISTS {self.name} (\n    {columns_sql}\n)"


@dataclass
class Migration:
    """Database migration."""
    version: str
    name: str
    up_sql: str
    down_sql: str
    created_at: float = field(default_factory=time.time)
    applied_at: Optional[float] = None


@dataclass
class QueryResult:
    """Query result container."""
    rows: List[Dict[str, Any]]
    affected_rows: int = 0
    last_insert_id: Optional[int] = None
    execution_time: float = 0.0


# =============================================================================
# DATABASE CONNECTION
# =============================================================================

class DatabaseConnection(ABC):
    """Abstract database connection."""

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def execute(
        self,
        query: str,
        params: Tuple = ()
    ) -> QueryResult:
        pass

    @abstractmethod
    async def executemany(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> QueryResult:
        pass

    @abstractmethod
    async def fetch_all(
        self,
        query: str,
        params: Tuple = ()
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_one(
        self,
        query: str,
        params: Tuple = ()
    ) -> Optional[Dict[str, Any]]:
        pass

    @asynccontextmanager
    async def transaction(self):
        """Transaction context manager."""
        await self.execute("BEGIN")
        try:
            yield
            await self.execute("COMMIT")
        except Exception:
            await self.execute("ROLLBACK")
            raise


class SQLiteConnection(DatabaseConnection):
    """SQLite database connection."""

    def __init__(self, path: str = ":memory:"):
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None

    async def connect(self) -> None:
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row

    async def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    async def execute(
        self,
        query: str,
        params: Tuple = ()
    ) -> QueryResult:
        start = time.time()
        cursor = self._conn.execute(query, params)
        self._conn.commit()

        return QueryResult(
            rows=[],
            affected_rows=cursor.rowcount,
            last_insert_id=cursor.lastrowid,
            execution_time=time.time() - start
        )

    async def executemany(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> QueryResult:
        start = time.time()
        cursor = self._conn.executemany(query, params_list)
        self._conn.commit()

        return QueryResult(
            rows=[],
            affected_rows=cursor.rowcount,
            execution_time=time.time() - start
        )

    async def fetch_all(
        self,
        query: str,
        params: Tuple = ()
    ) -> List[Dict[str, Any]]:
        cursor = self._conn.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetch_one(
        self,
        query: str,
        params: Tuple = ()
    ) -> Optional[Dict[str, Any]]:
        cursor = self._conn.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None


# =============================================================================
# CONNECTION POOL
# =============================================================================

class ConnectionPool:
    """Database connection pool."""

    def __init__(
        self,
        connection_factory: Callable[[], DatabaseConnection],
        min_size: int = 1,
        max_size: int = 10
    ):
        self._factory = connection_factory
        self._min_size = min_size
        self._max_size = max_size
        self._available: asyncio.Queue = asyncio.Queue()
        self._in_use: int = 0
        self._total: int = 0

    async def initialize(self) -> None:
        """Initialize pool with minimum connections."""
        for _ in range(self._min_size):
            conn = self._factory()
            await conn.connect()
            await self._available.put(conn)
            self._total += 1

    async def acquire(self) -> DatabaseConnection:
        """Acquire a connection from pool."""
        # Try to get from available
        try:
            conn = self._available.get_nowait()
            self._in_use += 1
            return conn
        except asyncio.QueueEmpty:
            pass

        # Create new if under limit
        if self._total < self._max_size:
            conn = self._factory()
            await conn.connect()
            self._total += 1
            self._in_use += 1
            return conn

        # Wait for available
        conn = await self._available.get()
        self._in_use += 1
        return conn

    async def release(self, conn: DatabaseConnection) -> None:
        """Release connection back to pool."""
        self._in_use -= 1
        await self._available.put(conn)

    @asynccontextmanager
    async def connection(self):
        """Get connection from pool."""
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await self.release(conn)

    async def close(self) -> None:
        """Close all connections."""
        while not self._available.empty():
            conn = await self._available.get()
            await conn.disconnect()
            self._total -= 1


# =============================================================================
# QUERY BUILDER
# =============================================================================

class QueryBuilder:
    """Fluent SQL query builder."""

    def __init__(self, table: str):
        self._table = table
        self._select: List[str] = ["*"]
        self._where: List[Tuple[str, str, Any]] = []
        self._order_by: List[Tuple[str, str]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._joins: List[Tuple[JoinType, str, str]] = []
        self._group_by: List[str] = []
        self._having: List[str] = []

    def select(self, *columns: str) -> "QueryBuilder":
        """Set SELECT columns."""
        self._select = list(columns)
        return self

    def where(
        self,
        column: str,
        operator: str,
        value: Any
    ) -> "QueryBuilder":
        """Add WHERE condition."""
        self._where.append((column, operator, value))
        return self

    def where_eq(self, column: str, value: Any) -> "QueryBuilder":
        """Add WHERE column = value."""
        return self.where(column, "=", value)

    def where_in(self, column: str, values: List[Any]) -> "QueryBuilder":
        """Add WHERE column IN (...)."""
        return self.where(column, "IN", values)

    def order_by(
        self,
        column: str,
        direction: str = "ASC"
    ) -> "QueryBuilder":
        """Add ORDER BY."""
        self._order_by.append((column, direction.upper()))
        return self

    def limit(self, limit: int) -> "QueryBuilder":
        """Set LIMIT."""
        self._limit = limit
        return self

    def offset(self, offset: int) -> "QueryBuilder":
        """Set OFFSET."""
        self._offset = offset
        return self

    def join(
        self,
        table: str,
        condition: str,
        join_type: JoinType = JoinType.INNER
    ) -> "QueryBuilder":
        """Add JOIN."""
        self._joins.append((join_type, table, condition))
        return self

    def group_by(self, *columns: str) -> "QueryBuilder":
        """Add GROUP BY."""
        self._group_by = list(columns)
        return self

    def build(self) -> Tuple[str, Tuple]:
        """Build SQL query and parameters."""
        params = []

        # SELECT
        sql = f"SELECT {', '.join(self._select)} FROM {self._table}"

        # JOINs
        for join_type, table, condition in self._joins:
            sql += f" {join_type.value} JOIN {table} ON {condition}"

        # WHERE
        if self._where:
            conditions = []
            for column, operator, value in self._where:
                if operator == "IN":
                    placeholders = ", ".join("?" * len(value))
                    conditions.append(f"{column} IN ({placeholders})")
                    params.extend(value)
                else:
                    conditions.append(f"{column} {operator} ?")
                    params.append(value)
            sql += " WHERE " + " AND ".join(conditions)

        # GROUP BY
        if self._group_by:
            sql += f" GROUP BY {', '.join(self._group_by)}"

        # ORDER BY
        if self._order_by:
            order_parts = [f"{col} {dir}" for col, dir in self._order_by]
            sql += f" ORDER BY {', '.join(order_parts)}"

        # LIMIT/OFFSET
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"

        if self._offset is not None:
            sql += f" OFFSET {self._offset}"

        return sql, tuple(params)


class InsertBuilder:
    """INSERT query builder."""

    def __init__(self, table: str):
        self._table = table
        self._columns: List[str] = []
        self._values: List[Any] = []
        self._on_conflict: Optional[str] = None

    def columns(self, *columns: str) -> "InsertBuilder":
        """Set columns."""
        self._columns = list(columns)
        return self

    def values(self, *values: Any) -> "InsertBuilder":
        """Set values."""
        self._values = list(values)
        return self

    def data(self, data: Dict[str, Any]) -> "InsertBuilder":
        """Set columns and values from dict."""
        self._columns = list(data.keys())
        self._values = list(data.values())
        return self

    def on_conflict_ignore(self) -> "InsertBuilder":
        """Add ON CONFLICT IGNORE."""
        self._on_conflict = "IGNORE"
        return self

    def on_conflict_replace(self) -> "InsertBuilder":
        """Add ON CONFLICT REPLACE."""
        self._on_conflict = "REPLACE"
        return self

    def build(self) -> Tuple[str, Tuple]:
        """Build INSERT query."""
        placeholders = ", ".join("?" * len(self._values))
        columns = ", ".join(self._columns)

        sql = f"INSERT"

        if self._on_conflict:
            sql += f" OR {self._on_conflict}"

        sql += f" INTO {self._table} ({columns}) VALUES ({placeholders})"

        return sql, tuple(self._values)


class UpdateBuilder:
    """UPDATE query builder."""

    def __init__(self, table: str):
        self._table = table
        self._set: Dict[str, Any] = {}
        self._where: List[Tuple[str, str, Any]] = []

    def set(self, **kwargs) -> "UpdateBuilder":
        """Set values to update."""
        self._set.update(kwargs)
        return self

    def where(
        self,
        column: str,
        operator: str,
        value: Any
    ) -> "UpdateBuilder":
        """Add WHERE condition."""
        self._where.append((column, operator, value))
        return self

    def where_eq(self, column: str, value: Any) -> "UpdateBuilder":
        """Add WHERE column = value."""
        return self.where(column, "=", value)

    def build(self) -> Tuple[str, Tuple]:
        """Build UPDATE query."""
        params = []

        # SET clause
        set_parts = []
        for col, val in self._set.items():
            set_parts.append(f"{col} = ?")
            params.append(val)

        sql = f"UPDATE {self._table} SET {', '.join(set_parts)}"

        # WHERE
        if self._where:
            conditions = []
            for column, operator, value in self._where:
                conditions.append(f"{column} {operator} ?")
                params.append(value)
            sql += " WHERE " + " AND ".join(conditions)

        return sql, tuple(params)


# =============================================================================
# MODEL BASE
# =============================================================================

T = TypeVar('T', bound='Model')


class Model:
    """Base model class with ORM-like functionality."""

    __table__: str = ""
    __primary_key__: str = "id"

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def table(cls) -> str:
        """Get table name."""
        return cls.__table__ or cls.__name__.lower() + "s"

    @classmethod
    def query(cls) -> QueryBuilder:
        """Get query builder for this model."""
        return QueryBuilder(cls.table())

    @classmethod
    async def find(
        cls: Type[T],
        db: DatabaseConnection,
        id: Any
    ) -> Optional[T]:
        """Find by primary key."""
        sql, params = (
            cls.query()
            .where_eq(cls.__primary_key__, id)
            .limit(1)
            .build()
        )

        row = await db.fetch_one(sql, params)
        return cls(**row) if row else None

    @classmethod
    async def all(
        cls: Type[T],
        db: DatabaseConnection
    ) -> List[T]:
        """Get all records."""
        sql, params = cls.query().build()
        rows = await db.fetch_all(sql, params)
        return [cls(**row) for row in rows]

    @classmethod
    async def where(
        cls: Type[T],
        db: DatabaseConnection,
        **conditions
    ) -> List[T]:
        """Find by conditions."""
        query = cls.query()

        for col, val in conditions.items():
            query.where_eq(col, val)

        sql, params = query.build()
        rows = await db.fetch_all(sql, params)
        return [cls(**row) for row in rows]

    async def save(self, db: DatabaseConnection) -> None:
        """Save model to database."""
        data = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

        pk = getattr(self, self.__primary_key__, None)

        if pk:
            # Update
            builder = UpdateBuilder(self.table())
            builder.set(**{k: v for k, v in data.items() if k != self.__primary_key__})
            builder.where_eq(self.__primary_key__, pk)
            sql, params = builder.build()
            await db.execute(sql, params)
        else:
            # Insert
            builder = InsertBuilder(self.table())
            builder.data(data)
            sql, params = builder.build()
            result = await db.execute(sql, params)
            setattr(self, self.__primary_key__, result.last_insert_id)

    async def delete(self, db: DatabaseConnection) -> None:
        """Delete model from database."""
        pk = getattr(self, self.__primary_key__, None)
        if pk:
            sql = f"DELETE FROM {self.table()} WHERE {self.__primary_key__} = ?"
            await db.execute(sql, (pk,))


# =============================================================================
# MIGRATIONS
# =============================================================================

class MigrationManager:
    """Manage database migrations."""

    def __init__(
        self,
        db: DatabaseConnection,
        migrations_dir: str = "migrations"
    ):
        self.db = db
        self.migrations_dir = migrations_dir
        self._migrations: List[Migration] = []

    async def initialize(self) -> None:
        """Create migrations table."""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at REAL NOT NULL
            )
        """)

    def add(self, migration: Migration) -> None:
        """Add migration."""
        self._migrations.append(migration)
        self._migrations.sort(key=lambda m: m.version)

    async def get_applied(self) -> List[str]:
        """Get list of applied migrations."""
        rows = await self.db.fetch_all(
            "SELECT version FROM _migrations ORDER BY version"
        )
        return [row["version"] for row in rows]

    async def migrate(self) -> List[str]:
        """Run pending migrations."""
        await self.initialize()
        applied = await self.get_applied()

        executed = []

        for migration in self._migrations:
            if migration.version in applied:
                continue

            logger.info(f"Applying migration: {migration.version} - {migration.name}")

            async with self.db.transaction():
                # Run migration
                await self.db.execute(migration.up_sql)

                # Record migration
                await self.db.execute(
                    "INSERT INTO _migrations (version, name, applied_at) VALUES (?, ?, ?)",
                    (migration.version, migration.name, time.time())
                )

            executed.append(migration.version)

        return executed

    async def rollback(self, steps: int = 1) -> List[str]:
        """Rollback migrations."""
        applied = await self.get_applied()
        applied.reverse()

        rolled_back = []

        for version in applied[:steps]:
            migration = next(
                (m for m in self._migrations if m.version == version),
                None
            )

            if not migration:
                continue

            logger.info(f"Rolling back: {migration.version} - {migration.name}")

            async with self.db.transaction():
                await self.db.execute(migration.down_sql)
                await self.db.execute(
                    "DELETE FROM _migrations WHERE version = ?",
                    (version,)
                )

            rolled_back.append(version)

        return rolled_back


# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """High-level database manager."""

    def __init__(self):
        self._connections: Dict[str, DatabaseConnection] = {}
        self._pools: Dict[str, ConnectionPool] = {}
        self._default: Optional[str] = None

    def register(
        self,
        name: str,
        connection: DatabaseConnection,
        default: bool = False
    ) -> None:
        """Register database connection."""
        self._connections[name] = connection

        if default or self._default is None:
            self._default = name

    async def connect(self, name: Optional[str] = None) -> DatabaseConnection:
        """Connect to database."""
        name = name or self._default
        conn = self._connections.get(name)

        if conn:
            await conn.connect()

        return conn

    def get(self, name: Optional[str] = None) -> Optional[DatabaseConnection]:
        """Get database connection."""
        return self._connections.get(name or self._default)

    async def close_all(self) -> None:
        """Close all connections."""
        for conn in self._connections.values():
            await conn.disconnect()

        for pool in self._pools.values():
            await pool.close()


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

# Example model
class User(Model):
    __table__ = "users"

    id: int
    name: str
    email: str
    created_at: float


async def main():
    """Demonstrate database functionality."""
    # Create connection
    db = SQLiteConnection(":memory:")
    await db.connect()

    print("=== BAEL Database Layer ===\n")

    # Create table
    users_table = Table(
        name="users",
        columns=[
            Column("id", ColumnType.INTEGER, primary_key=True),
            Column("name", ColumnType.TEXT, nullable=False),
            Column("email", ColumnType.TEXT, unique=True),
            Column("created_at", ColumnType.REAL, default="0")
        ]
    )

    print("Creating table:")
    print(users_table.to_sql())
    await db.execute(users_table.to_sql())

    # Insert data
    print("\n--- Inserting Users ---")

    insert = InsertBuilder("users").data({
        "name": "Alice",
        "email": "alice@example.com",
        "created_at": time.time()
    })
    sql, params = insert.build()
    result = await db.execute(sql, params)
    print(f"Inserted user with ID: {result.last_insert_id}")

    insert = InsertBuilder("users").data({
        "name": "Bob",
        "email": "bob@example.com",
        "created_at": time.time()
    })
    sql, params = insert.build()
    await db.execute(sql, params)

    insert = InsertBuilder("users").data({
        "name": "Charlie",
        "email": "charlie@example.com",
        "created_at": time.time()
    })
    sql, params = insert.build()
    await db.execute(sql, params)

    # Query with builder
    print("\n--- Query Builder ---")

    query = (
        QueryBuilder("users")
        .select("id", "name", "email")
        .where("name", "LIKE", "%a%")
        .order_by("name")
        .limit(10)
    )
    sql, params = query.build()
    print(f"Query: {sql}")
    print(f"Params: {params}")

    rows = await db.fetch_all(sql, params)
    print(f"Results: {rows}")

    # Using Model
    print("\n--- ORM Model ---")

    # Find all
    users = await User.all(db)
    print(f"All users: {[u.name for u in users]}")

    # Find by ID
    user = await User.find(db, 1)
    print(f"User 1: {user.name} ({user.email})")

    # Find by conditions
    users = await User.where(db, name="Bob")
    print(f"User named Bob: {users[0].email if users else 'Not found'}")

    # Create new user
    new_user = User(
        name="David",
        email="david@example.com",
        created_at=time.time()
    )
    await new_user.save(db)
    print(f"Created user with ID: {new_user.id}")

    # Update user
    new_user.name = "Dave"
    await new_user.save(db)
    print(f"Updated user name to: {new_user.name}")

    # Migrations
    print("\n--- Migrations ---")

    migrations = MigrationManager(db)

    migrations.add(Migration(
        version="001",
        name="add_age_column",
        up_sql="ALTER TABLE users ADD COLUMN age INTEGER DEFAULT 0",
        down_sql="ALTER TABLE users DROP COLUMN age"
    ))

    migrations.add(Migration(
        version="002",
        name="add_active_column",
        up_sql="ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1",
        down_sql="ALTER TABLE users DROP COLUMN active"
    ))

    executed = await migrations.migrate()
    print(f"Applied migrations: {executed}")

    # Verify columns
    rows = await db.fetch_all("PRAGMA table_info(users)")
    print(f"Table columns: {[row['name'] for row in rows]}")

    # Transaction example
    print("\n--- Transactions ---")

    try:
        async with db.transaction():
            await db.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                ("Eve", "eve@example.com")
            )
            # This will work

            await db.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                ("Alice", "alice@example.com")  # Duplicate email - will fail
            )
    except Exception as e:
        print(f"Transaction rolled back: {type(e).__name__}")

    # Check Eve was not inserted
    users = await User.all(db)
    print(f"Users after failed transaction: {[u.name for u in users]}")

    # Cleanup
    await db.disconnect()
    print("\nDatabase closed.")


if __name__ == "__main__":
    asyncio.run(main())
