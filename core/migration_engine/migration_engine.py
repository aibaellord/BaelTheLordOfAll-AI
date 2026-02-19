"""
BAEL Migration Engine
=====================

Database migration and schema management with:
- Version tracking
- Up/down migrations
- Schema diffing
- Rollback support
- Migration generation

"Ba'el evolves the foundations of reality." — Ba'el
"""

import asyncio
import logging
import os
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
from pathlib import Path
import threading
import uuid
import re

logger = logging.getLogger("BAEL.Migration")


# ============================================================================
# ENUMS
# ============================================================================

class MigrationStatus(Enum):
    """Migration status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationDirection(Enum):
    """Migration direction."""
    UP = "up"
    DOWN = "down"


class SchemaChangeType(Enum):
    """Types of schema changes."""
    CREATE_TABLE = "create_table"
    DROP_TABLE = "drop_table"
    ALTER_TABLE = "alter_table"
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    ALTER_COLUMN = "alter_column"
    ADD_INDEX = "add_index"
    DROP_INDEX = "drop_index"
    ADD_CONSTRAINT = "add_constraint"
    DROP_CONSTRAINT = "drop_constraint"
    CREATE_SEQUENCE = "create_sequence"
    DROP_SEQUENCE = "drop_sequence"
    RAW_SQL = "raw_sql"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SchemaChange:
    """A schema change operation."""
    change_type: SchemaChangeType

    # Table context
    table_name: Optional[str] = None

    # Column changes
    column_name: Optional[str] = None
    column_type: Optional[str] = None
    column_options: Dict[str, Any] = field(default_factory=dict)

    # Index changes
    index_name: Optional[str] = None
    index_columns: List[str] = field(default_factory=list)
    index_unique: bool = False

    # Constraint changes
    constraint_name: Optional[str] = None
    constraint_type: Optional[str] = None
    constraint_options: Dict[str, Any] = field(default_factory=dict)

    # Raw SQL
    sql: Optional[str] = None

    def to_sql(self, dialect: str = "postgresql") -> str:
        """Generate SQL for this change."""
        if self.change_type == SchemaChangeType.CREATE_TABLE:
            return f"CREATE TABLE IF NOT EXISTS {self.table_name} (id SERIAL PRIMARY KEY)"

        elif self.change_type == SchemaChangeType.DROP_TABLE:
            return f"DROP TABLE IF EXISTS {self.table_name}"

        elif self.change_type == SchemaChangeType.ADD_COLUMN:
            col_def = self.column_type
            if self.column_options.get('nullable') is False:
                col_def += " NOT NULL"
            if 'default' in self.column_options:
                col_def += f" DEFAULT {self.column_options['default']}"
            return f"ALTER TABLE {self.table_name} ADD COLUMN {self.column_name} {col_def}"

        elif self.change_type == SchemaChangeType.DROP_COLUMN:
            return f"ALTER TABLE {self.table_name} DROP COLUMN {self.column_name}"

        elif self.change_type == SchemaChangeType.ALTER_COLUMN:
            return f"ALTER TABLE {self.table_name} ALTER COLUMN {self.column_name} TYPE {self.column_type}"

        elif self.change_type == SchemaChangeType.ADD_INDEX:
            unique = "UNIQUE " if self.index_unique else ""
            cols = ", ".join(self.index_columns)
            return f"CREATE {unique}INDEX {self.index_name} ON {self.table_name} ({cols})"

        elif self.change_type == SchemaChangeType.DROP_INDEX:
            return f"DROP INDEX IF EXISTS {self.index_name}"

        elif self.change_type == SchemaChangeType.ADD_CONSTRAINT:
            if self.constraint_type == "foreign_key":
                ref_table = self.constraint_options.get('references', {}).get('table')
                ref_col = self.constraint_options.get('references', {}).get('column')
                return f"ALTER TABLE {self.table_name} ADD CONSTRAINT {self.constraint_name} FOREIGN KEY ({self.column_name}) REFERENCES {ref_table}({ref_col})"
            elif self.constraint_type == "check":
                check = self.constraint_options.get('check')
                return f"ALTER TABLE {self.table_name} ADD CONSTRAINT {self.constraint_name} CHECK ({check})"
            return ""

        elif self.change_type == SchemaChangeType.DROP_CONSTRAINT:
            return f"ALTER TABLE {self.table_name} DROP CONSTRAINT IF EXISTS {self.constraint_name}"

        elif self.change_type == SchemaChangeType.RAW_SQL:
            return self.sql or ""

        return ""


@dataclass
class Migration:
    """A database migration."""
    id: str
    version: str
    name: str
    description: str = ""

    # Changes
    up_changes: List[SchemaChange] = field(default_factory=list)
    down_changes: List[SchemaChange] = field(default_factory=list)

    # Raw SQL (alternative to changes)
    up_sql: Optional[str] = None
    down_sql: Optional[str] = None

    # Checksums
    checksum: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.version}_{self.name}"

    def compute_checksum(self) -> str:
        """Compute checksum of migration."""
        content = json.dumps({
            'version': self.version,
            'name': self.name,
            'up_sql': self.up_sql,
            'down_sql': self.down_sql,
            'up_changes': [
                {'type': c.change_type.value, 'table': c.table_name, 'column': c.column_name}
                for c in self.up_changes
            ]
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class MigrationHistory:
    """Record of an executed migration."""
    id: str
    migration_id: str
    version: str
    name: str

    # Status
    status: MigrationStatus = MigrationStatus.PENDING
    direction: MigrationDirection = MigrationDirection.UP

    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: int = 0

    # Error
    error_message: Optional[str] = None

    # Checksum
    checksum: Optional[str] = None


@dataclass
class MigrationPlan:
    """A plan for executing migrations."""
    migrations: List[Migration] = field(default_factory=list)
    direction: MigrationDirection = MigrationDirection.UP

    # Target
    target_version: Optional[str] = None

    # Dry run results
    sql_statements: List[str] = field(default_factory=list)


@dataclass
class MigrationConfig:
    """Migration engine configuration."""
    migrations_dir: str = "migrations"
    history_table: str = "_migration_history"
    dialect: str = "postgresql"
    transaction_per_migration: bool = True
    auto_create_history_table: bool = True


# ============================================================================
# SCHEMA MANAGER
# ============================================================================

class SchemaManager:
    """
    Manages database schema operations.
    """

    def __init__(self, dialect: str = "postgresql"):
        """Initialize schema manager."""
        self.dialect = dialect
        self._tables: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def load_schema(self, schema: Dict[str, Any]) -> None:
        """Load schema definition."""
        with self._lock:
            self._tables = schema.get('tables', {})

    def get_table(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get table definition."""
        return self._tables.get(table_name)

    def get_tables(self) -> Dict[str, Dict[str, Any]]:
        """Get all tables."""
        return self._tables.copy()

    def diff_schemas(
        self,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any]
    ) -> List[SchemaChange]:
        """
        Compute differences between schemas.
        Returns list of changes to transform old to new.
        """
        changes = []

        old_tables = old_schema.get('tables', {})
        new_tables = new_schema.get('tables', {})

        # New tables
        for table_name in new_tables:
            if table_name not in old_tables:
                changes.append(SchemaChange(
                    change_type=SchemaChangeType.CREATE_TABLE,
                    table_name=table_name
                ))

                # Add columns
                for col_name, col_def in new_tables[table_name].get('columns', {}).items():
                    changes.append(SchemaChange(
                        change_type=SchemaChangeType.ADD_COLUMN,
                        table_name=table_name,
                        column_name=col_name,
                        column_type=col_def.get('type', 'TEXT'),
                        column_options=col_def
                    ))

        # Dropped tables
        for table_name in old_tables:
            if table_name not in new_tables:
                changes.append(SchemaChange(
                    change_type=SchemaChangeType.DROP_TABLE,
                    table_name=table_name
                ))

        # Modified tables
        for table_name in new_tables:
            if table_name in old_tables:
                old_cols = old_tables[table_name].get('columns', {})
                new_cols = new_tables[table_name].get('columns', {})

                # New columns
                for col_name in new_cols:
                    if col_name not in old_cols:
                        col_def = new_cols[col_name]
                        changes.append(SchemaChange(
                            change_type=SchemaChangeType.ADD_COLUMN,
                            table_name=table_name,
                            column_name=col_name,
                            column_type=col_def.get('type', 'TEXT'),
                            column_options=col_def
                        ))

                # Dropped columns
                for col_name in old_cols:
                    if col_name not in new_cols:
                        changes.append(SchemaChange(
                            change_type=SchemaChangeType.DROP_COLUMN,
                            table_name=table_name,
                            column_name=col_name
                        ))

                # Modified columns
                for col_name in new_cols:
                    if col_name in old_cols:
                        old_type = old_cols[col_name].get('type')
                        new_type = new_cols[col_name].get('type')
                        if old_type != new_type:
                            changes.append(SchemaChange(
                                change_type=SchemaChangeType.ALTER_COLUMN,
                                table_name=table_name,
                                column_name=col_name,
                                column_type=new_type
                            ))

        return changes

    def generate_create_table_sql(
        self,
        table_name: str,
        columns: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate CREATE TABLE SQL."""
        col_defs = []

        for col_name, col_def in columns.items():
            parts = [col_name, col_def.get('type', 'TEXT')]

            if col_def.get('primary_key'):
                parts.append("PRIMARY KEY")
            if col_def.get('nullable') is False:
                parts.append("NOT NULL")
            if 'default' in col_def:
                parts.append(f"DEFAULT {col_def['default']}")
            if col_def.get('unique'):
                parts.append("UNIQUE")

            col_defs.append(' '.join(parts))

        return f"CREATE TABLE IF NOT EXISTS {table_name} (\n  " + ",\n  ".join(col_defs) + "\n)"


# ============================================================================
# MIGRATION GENERATOR
# ============================================================================

class MigrationGenerator:
    """
    Generates migration files.
    """

    def __init__(self, config: MigrationConfig):
        """Initialize generator."""
        self.config = config

    def generate_version(self) -> str:
        """Generate a version string."""
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def generate_migration(
        self,
        name: str,
        up_changes: Optional[List[SchemaChange]] = None,
        down_changes: Optional[List[SchemaChange]] = None,
        up_sql: Optional[str] = None,
        down_sql: Optional[str] = None
    ) -> Migration:
        """Generate a migration."""
        version = self.generate_version()

        migration = Migration(
            id=str(uuid.uuid4()),
            version=version,
            name=name,
            up_changes=up_changes or [],
            down_changes=down_changes or [],
            up_sql=up_sql,
            down_sql=down_sql
        )

        migration.checksum = migration.compute_checksum()

        return migration

    def generate_from_diff(
        self,
        name: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any]
    ) -> Migration:
        """Generate migration from schema diff."""
        schema_manager = SchemaManager(self.config.dialect)

        up_changes = schema_manager.diff_schemas(old_schema, new_schema)
        down_changes = schema_manager.diff_schemas(new_schema, old_schema)

        return self.generate_migration(
            name=name,
            up_changes=up_changes,
            down_changes=down_changes
        )

    def save_migration(
        self,
        migration: Migration,
        directory: Optional[str] = None
    ) -> str:
        """Save migration to file."""
        directory = directory or self.config.migrations_dir
        Path(directory).mkdir(parents=True, exist_ok=True)

        filename = f"{migration.version}_{migration.name}.py"
        filepath = os.path.join(directory, filename)

        # Generate Python migration file
        content = self._generate_python_migration(migration)

        with open(filepath, 'w') as f:
            f.write(content)

        return filepath

    def _generate_python_migration(self, migration: Migration) -> str:
        """Generate Python migration file content."""
        lines = [
            '"""',
            f'Migration: {migration.name}',
            f'Version: {migration.version}',
            f'Created: {migration.created_at.isoformat()}',
            '"""',
            '',
            'from core.migration_engine import SchemaChange, SchemaChangeType',
            '',
            f'VERSION = "{migration.version}"',
            f'NAME = "{migration.name}"',
            f'CHECKSUM = "{migration.checksum}"',
            '',
        ]

        # Up migration
        if migration.up_sql:
            lines.append('def up(connection):')
            lines.append('    """Run the up migration."""')
            lines.append(f'    connection.execute("""{migration.up_sql}""")')
        else:
            lines.append('UP_CHANGES = [')
            for change in migration.up_changes:
                lines.append(f'    {self._change_to_code(change)},')
            lines.append(']')
            lines.append('')
            lines.append('def up(connection):')
            lines.append('    """Run the up migration."""')
            lines.append('    for change in UP_CHANGES:')
            lines.append('        sql = change.to_sql()')
            lines.append('        if sql:')
            lines.append('            connection.execute(sql)')

        lines.append('')

        # Down migration
        if migration.down_sql:
            lines.append('def down(connection):')
            lines.append('    """Run the down migration."""')
            lines.append(f'    connection.execute("""{migration.down_sql}""")')
        else:
            lines.append('DOWN_CHANGES = [')
            for change in migration.down_changes:
                lines.append(f'    {self._change_to_code(change)},')
            lines.append(']')
            lines.append('')
            lines.append('def down(connection):')
            lines.append('    """Run the down migration."""')
            lines.append('    for change in DOWN_CHANGES:')
            lines.append('        sql = change.to_sql()')
            lines.append('        if sql:')
            lines.append('            connection.execute(sql)')

        return '\n'.join(lines)

    def _change_to_code(self, change: SchemaChange) -> str:
        """Convert SchemaChange to Python code."""
        parts = [f"SchemaChange(change_type=SchemaChangeType.{change.change_type.name}"]

        if change.table_name:
            parts.append(f'table_name="{change.table_name}"')
        if change.column_name:
            parts.append(f'column_name="{change.column_name}"')
        if change.column_type:
            parts.append(f'column_type="{change.column_type}"')
        if change.index_name:
            parts.append(f'index_name="{change.index_name}"')
        if change.constraint_name:
            parts.append(f'constraint_name="{change.constraint_name}"')
        if change.sql:
            parts.append(f'sql="""{change.sql}"""')

        return ', '.join(parts) + ')'


# ============================================================================
# MIGRATION RUNNER
# ============================================================================

class MigrationRunner:
    """
    Executes migrations.
    """

    def __init__(self, config: MigrationConfig):
        """Initialize runner."""
        self.config = config
        self._history: List[MigrationHistory] = []
        self._lock = threading.RLock()

    def load_history(self) -> List[MigrationHistory]:
        """Load migration history."""
        # In a real implementation, this would query the database
        return self._history.copy()

    def save_history(self, record: MigrationHistory) -> None:
        """Save history record."""
        with self._lock:
            self._history.append(record)

    def get_applied_versions(self) -> List[str]:
        """Get list of applied migration versions."""
        return [
            h.version for h in self._history
            if h.status == MigrationStatus.COMPLETED
            and h.direction == MigrationDirection.UP
        ]

    def run_migration(
        self,
        migration: Migration,
        direction: MigrationDirection = MigrationDirection.UP,
        connection: Any = None
    ) -> MigrationHistory:
        """Run a single migration."""
        record = MigrationHistory(
            id=str(uuid.uuid4()),
            migration_id=migration.id,
            version=migration.version,
            name=migration.name,
            status=MigrationStatus.RUNNING,
            direction=direction,
            started_at=datetime.now(),
            checksum=migration.checksum
        )

        try:
            start_time = datetime.now()

            if direction == MigrationDirection.UP:
                if migration.up_sql:
                    self._execute_sql(connection, migration.up_sql)
                else:
                    for change in migration.up_changes:
                        sql = change.to_sql(self.config.dialect)
                        if sql:
                            self._execute_sql(connection, sql)
            else:
                if migration.down_sql:
                    self._execute_sql(connection, migration.down_sql)
                else:
                    for change in migration.down_changes:
                        sql = change.to_sql(self.config.dialect)
                        if sql:
                            self._execute_sql(connection, sql)

            record.status = MigrationStatus.COMPLETED
            record.completed_at = datetime.now()
            record.execution_time_ms = int(
                (record.completed_at - start_time).total_seconds() * 1000
            )

            logger.info(
                f"Migration {migration.full_name} {direction.value} completed "
                f"in {record.execution_time_ms}ms"
            )

        except Exception as e:
            record.status = MigrationStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now()
            logger.error(f"Migration {migration.full_name} failed: {e}")
            raise

        finally:
            self.save_history(record)

        return record

    def _execute_sql(self, connection: Any, sql: str) -> None:
        """Execute SQL statement."""
        if connection is None:
            # Dry run mode
            logger.info(f"DRY RUN SQL: {sql}")
            return

        # Execute the SQL
        if hasattr(connection, 'execute'):
            connection.execute(sql)
        elif hasattr(connection, 'cursor'):
            cursor = connection.cursor()
            cursor.execute(sql)
            connection.commit()

    def run_migrations(
        self,
        migrations: List[Migration],
        direction: MigrationDirection = MigrationDirection.UP,
        connection: Any = None
    ) -> List[MigrationHistory]:
        """Run multiple migrations."""
        results = []

        if direction == MigrationDirection.DOWN:
            migrations = list(reversed(migrations))

        for migration in migrations:
            result = self.run_migration(migration, direction, connection)
            results.append(result)

            if result.status == MigrationStatus.FAILED:
                break

        return results


# ============================================================================
# MAIN MIGRATION ENGINE
# ============================================================================

class MigrationEngine:
    """
    Main migration engine.

    Features:
    - Migration management
    - Schema versioning
    - Up/down migrations
    - Rollback support

    "Ba'el transforms the structure of existence." — Ba'el
    """

    def __init__(self, config: Optional[MigrationConfig] = None):
        """Initialize migration engine."""
        self.config = config or MigrationConfig()

        # Components
        self.schema_manager = SchemaManager(self.config.dialect)
        self.generator = MigrationGenerator(self.config)
        self.runner = MigrationRunner(self.config)

        # Migration storage
        self._migrations: Dict[str, Migration] = {}

        self._lock = threading.RLock()

        logger.info("MigrationEngine initialized")

    def register_migration(self, migration: Migration) -> None:
        """Register a migration."""
        with self._lock:
            self._migrations[migration.version] = migration

    def load_migrations(self, directory: Optional[str] = None) -> List[Migration]:
        """Load migrations from directory."""
        directory = directory or self.config.migrations_dir

        if not os.path.exists(directory):
            return []

        migrations = []

        for filename in sorted(os.listdir(directory)):
            if filename.endswith('.py') and not filename.startswith('_'):
                # Parse version and name from filename
                match = re.match(r'(\d+)_(.+)\.py', filename)
                if match:
                    version, name = match.groups()

                    # Load migration module
                    filepath = os.path.join(directory, filename)
                    migration = self._load_migration_file(filepath, version, name)

                    if migration:
                        migrations.append(migration)
                        self.register_migration(migration)

        return migrations

    def _load_migration_file(
        self,
        filepath: str,
        version: str,
        name: str
    ) -> Optional[Migration]:
        """Load a migration from file."""
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(f"migration_{version}", filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            migration = Migration(
                id=str(uuid.uuid4()),
                version=version,
                name=name
            )

            # Get up/down functions
            if hasattr(module, 'up'):
                migration.up_sql = None  # Use function instead

            if hasattr(module, 'down'):
                migration.down_sql = None

            if hasattr(module, 'UP_CHANGES'):
                migration.up_changes = module.UP_CHANGES

            if hasattr(module, 'DOWN_CHANGES'):
                migration.down_changes = module.DOWN_CHANGES

            if hasattr(module, 'CHECKSUM'):
                migration.checksum = module.CHECKSUM

            return migration

        except Exception as e:
            logger.error(f"Failed to load migration {filepath}: {e}")
            return None

    def get_pending_migrations(self) -> List[Migration]:
        """Get pending migrations."""
        applied = set(self.runner.get_applied_versions())

        pending = [
            m for m in sorted(self._migrations.values(), key=lambda x: x.version)
            if m.version not in applied
        ]

        return pending

    def create_migration(
        self,
        name: str,
        up_changes: Optional[List[SchemaChange]] = None,
        down_changes: Optional[List[SchemaChange]] = None,
        up_sql: Optional[str] = None,
        down_sql: Optional[str] = None,
        save: bool = True
    ) -> Migration:
        """Create a new migration."""
        migration = self.generator.generate_migration(
            name=name,
            up_changes=up_changes,
            down_changes=down_changes,
            up_sql=up_sql,
            down_sql=down_sql
        )

        self.register_migration(migration)

        if save:
            self.generator.save_migration(migration)

        return migration

    def create_migration_from_diff(
        self,
        name: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        save: bool = True
    ) -> Migration:
        """Create migration from schema diff."""
        migration = self.generator.generate_from_diff(name, old_schema, new_schema)

        self.register_migration(migration)

        if save:
            self.generator.save_migration(migration)

        return migration

    def plan(
        self,
        target_version: Optional[str] = None,
        direction: MigrationDirection = MigrationDirection.UP
    ) -> MigrationPlan:
        """Create migration plan."""
        if direction == MigrationDirection.UP:
            migrations = self.get_pending_migrations()

            if target_version:
                migrations = [m for m in migrations if m.version <= target_version]

        else:
            applied = self.runner.get_applied_versions()
            migrations = [
                self._migrations[v] for v in applied
                if v in self._migrations
            ]

            if target_version:
                migrations = [m for m in migrations if m.version > target_version]

        plan = MigrationPlan(
            migrations=migrations,
            direction=direction,
            target_version=target_version
        )

        # Generate SQL statements
        for migration in migrations:
            if direction == MigrationDirection.UP:
                if migration.up_sql:
                    plan.sql_statements.append(migration.up_sql)
                else:
                    for change in migration.up_changes:
                        sql = change.to_sql(self.config.dialect)
                        if sql:
                            plan.sql_statements.append(sql)
            else:
                if migration.down_sql:
                    plan.sql_statements.append(migration.down_sql)
                else:
                    for change in migration.down_changes:
                        sql = change.to_sql(self.config.dialect)
                        if sql:
                            plan.sql_statements.append(sql)

        return plan

    def migrate(
        self,
        target_version: Optional[str] = None,
        connection: Any = None,
        dry_run: bool = False
    ) -> List[MigrationHistory]:
        """Run pending migrations."""
        plan = self.plan(target_version, MigrationDirection.UP)

        if dry_run:
            logger.info(f"DRY RUN: Would run {len(plan.migrations)} migrations")
            for sql in plan.sql_statements:
                logger.info(f"  SQL: {sql}")
            return []

        return self.runner.run_migrations(
            plan.migrations,
            MigrationDirection.UP,
            connection
        )

    def rollback(
        self,
        steps: int = 1,
        target_version: Optional[str] = None,
        connection: Any = None,
        dry_run: bool = False
    ) -> List[MigrationHistory]:
        """Rollback migrations."""
        applied = self.runner.get_applied_versions()

        if target_version:
            versions_to_rollback = [v for v in applied if v > target_version]
        else:
            versions_to_rollback = applied[-steps:]

        migrations = [
            self._migrations[v] for v in versions_to_rollback
            if v in self._migrations
        ]

        if dry_run:
            logger.info(f"DRY RUN: Would rollback {len(migrations)} migrations")
            return []

        return self.runner.run_migrations(
            migrations,
            MigrationDirection.DOWN,
            connection
        )

    def get_status(self) -> Dict[str, Any]:
        """Get migration status."""
        pending = self.get_pending_migrations()
        applied = self.runner.get_applied_versions()

        return {
            'total_migrations': len(self._migrations),
            'applied': len(applied),
            'pending': len(pending),
            'current_version': applied[-1] if applied else None,
            'pending_versions': [m.version for m in pending]
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

migration_engine = MigrationEngine()
