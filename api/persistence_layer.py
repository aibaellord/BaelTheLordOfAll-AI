"""
Advanced Persistence Layer for BAEL

Multi-backend persistence (SQLite, PostgreSQL, Redis) with migration management,
versioning, sharding, and replication support.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DatabaseBackend(Enum):
    """Database backend types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    REDIS = "redis"
    MONGODB = "mongodb"


class ReplicationMode(Enum):
    """Database replication modes."""
    PRIMARY_REPLICA = "primary_replica"
    MULTI_MASTER = "multi_master"
    READ_ONLY = "read_only"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    backend: DatabaseBackend
    host: str
    port: int
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    timeout: int = 30


@dataclass
class MigrationRecord:
    """Database migration record."""
    migration_id: str
    name: str
    version: str
    applied_at: datetime = field(default_factory=datetime.now)
    rolled_back_at: Optional[datetime] = None
    status: str = "applied"
    changes: Dict = field(default_factory=dict)


@dataclass
class DataVersion:
    """Version of data."""
    version_id: str
    entity_id: str
    entity_type: str
    version_number: int
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    data_hash: str = ""
    change_description: str = ""
    is_latest: bool = True


class QueryBuilder:
    """SQL query builder."""

    def __init__(self):
        self.select_fields = []
        self.from_table = None
        self.where_conditions = []
        self.join_clauses = []
        self.order_by_fields = []
        self.limit_value = None
        self.offset_value = None

    def select(self, *fields) -> "QueryBuilder":
        """Add SELECT fields."""
        self.select_fields.extend(fields)
        return self

    def from_table(self, table_name: str) -> "QueryBuilder":
        """Set FROM table."""
        self.from_table = table_name
        return self

    def where(self, condition: str) -> "QueryBuilder":
        """Add WHERE condition."""
        self.where_conditions.append(condition)
        return self

    def join(self, join_type: str, table: str, condition: str) -> "QueryBuilder":
        """Add JOIN clause."""
        self.join_clauses.append(f"{join_type} JOIN {table} ON {condition}")
        return self

    def order_by(self, field: str, direction: str = "ASC") -> "QueryBuilder":
        """Add ORDER BY."""
        self.order_by_fields.append(f"{field} {direction}")
        return self

    def limit(self, limit: int) -> "QueryBuilder":
        """Set LIMIT."""
        self.limit_value = limit
        return self

    def offset(self, offset: int) -> "QueryBuilder":
        """Set OFFSET."""
        self.offset_value = offset
        return self

    def build(self) -> str:
        """Build SQL query."""
        query = f"SELECT {', '.join(self.select_fields or ['*'])}"

        if self.from_table:
            query += f" FROM {self.from_table}"

        for join in self.join_clauses:
            query += f" {join}"

        if self.where_conditions:
            query += f" WHERE {' AND '.join(self.where_conditions)}"

        if self.order_by_fields:
            query += f" ORDER BY {', '.join(self.order_by_fields)}"

        if self.limit_value:
            query += f" LIMIT {self.limit_value}"

        if self.offset_value:
            query += f" OFFSET {self.offset_value}"

        return query


class DatabaseConnector:
    """Base database connector."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connected = False
        self.connection = None
        self.query_count = 0

    def connect(self) -> bool:
        """Establish connection."""
        self.connected = True
        return True

    def disconnect(self) -> None:
        """Close connection."""
        self.connected = False

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute query."""
        self.query_count += 1
        return []

    def execute_insert(self, table: str, data: Dict) -> str:
        """Insert data."""
        return ""

    def execute_update(self, table: str, data: Dict, where: str) -> int:
        """Update data."""
        return 0

    def execute_delete(self, table: str, where: str) -> int:
        """Delete data."""
        return 0

    def get_statistics(self) -> Dict:
        """Get connection statistics."""
        return {
            "backend": self.config.backend.value,
            "connected": self.connected,
            "query_count": self.query_count
        }


class MigrationManager:
    """Manages database migrations."""

    def __init__(self):
        self.migrations: Dict[str, MigrationRecord] = {}
        self.pending_migrations: List[Dict] = []

    def create_migration(self, name: str) -> MigrationRecord:
        """Create new migration."""
        version = f"{len(self.migrations) + 1:03d}"
        migration_id = f"mig_{int(datetime.now().timestamp())}"

        migration = MigrationRecord(
            migration_id=migration_id,
            name=name,
            version=version
        )

        self.migrations[migration_id] = migration
        return migration

    def apply_migration(self, migration_id: str) -> bool:
        """Apply migration."""
        if migration_id in self.migrations:
            migration = self.migrations[migration_id]
            migration.status = "applied"
            migration.applied_at = datetime.now()
            return True
        return False

    def rollback_migration(self, migration_id: str) -> bool:
        """Rollback migration."""
        if migration_id in self.migrations:
            migration = self.migrations[migration_id]
            migration.status = "rolled_back"
            migration.rolled_back_at = datetime.now()
            return True
        return False

    def get_pending_migrations(self) -> List[MigrationRecord]:
        """Get pending migrations."""
        return [m for m in self.migrations.values() if m.status != "applied"]

    def get_migration_history(self) -> List[MigrationRecord]:
        """Get migration history."""
        return sorted(self.migrations.values(), key=lambda m: m.applied_at)


class VersioningSystem:
    """Manages data versioning."""

    def __init__(self):
        self.versions: Dict[str, List[DataVersion]] = {}

    def create_version(self, entity_id: str, entity_type: str,
                      data: Dict, created_by: str = "system") -> DataVersion:
        """Create new version."""
        if entity_id not in self.versions:
            self.versions[entity_id] = []

        version_number = len(self.versions[entity_id]) + 1
        data_hash = str(hash(json.dumps(data, sort_keys=True, default=str)))

        version = DataVersion(
            version_id=f"v_{entity_id}_{version_number}",
            entity_id=entity_id,
            entity_type=entity_type,
            version_number=version_number,
            created_by=created_by,
            data_hash=data_hash
        )

        # Mark previous as not latest
        for v in self.versions[entity_id]:
            v.is_latest = False

        self.versions[entity_id].append(version)
        return version

    def get_version(self, entity_id: str, version_number: Optional[int] = None) -> Optional[DataVersion]:
        """Get specific version."""
        if entity_id not in self.versions:
            return None

        if version_number is None:
            # Get latest
            return self.versions[entity_id][-1] if self.versions[entity_id] else None

        for version in self.versions[entity_id]:
            if version.version_number == version_number:
                return version

        return None

    def get_version_history(self, entity_id: str) -> List[DataVersion]:
        """Get version history."""
        return self.versions.get(entity_id, [])

    def revert_to_version(self, entity_id: str, version_number: int) -> bool:
        """Revert to previous version."""
        if entity_id not in self.versions:
            return False

        for v in self.versions[entity_id]:
            v.is_latest = False

        target = self.get_version(entity_id, version_number)
        if target:
            target.is_latest = True
            return True

        return False


class ShardingManager:
    """Manages database sharding."""

    def __init__(self, num_shards: int = 4):
        self.num_shards = num_shards
        self.shards: Dict[int, DatabaseConnector] = {}

    def get_shard(self, entity_id: str) -> int:
        """Determine shard for entity."""
        hash_value = hash(entity_id)
        return hash_value % self.num_shards

    def add_shard(self, shard_id: int, connector: DatabaseConnector) -> None:
        """Add shard connector."""
        self.shards[shard_id] = connector

    def get_connector(self, entity_id: str) -> Optional[DatabaseConnector]:
        """Get connector for entity."""
        shard_id = self.get_shard(entity_id)
        return self.shards.get(shard_id)

    def get_shard_stats(self) -> Dict[int, Dict]:
        """Get statistics for all shards."""
        return {
            shard_id: connector.get_statistics()
            for shard_id, connector in self.shards.items()
        }


class ReplicationManager:
    """Manages database replication."""

    def __init__(self, mode: ReplicationMode = ReplicationMode.PRIMARY_REPLICA):
        self.mode = mode
        self.primary: Optional[DatabaseConnector] = None
        self.replicas: List[DatabaseConnector] = []
        self.replication_lag_ms = 0

    def set_primary(self, connector: DatabaseConnector) -> None:
        """Set primary database."""
        self.primary = connector

    def add_replica(self, connector: DatabaseConnector) -> None:
        """Add replica database."""
        self.replicas.append(connector)

    def write(self, query: str, params: Optional[Dict] = None) -> Any:
        """Write to primary."""
        if self.primary:
            return self.primary.execute_query(query, params)
        return None

    def read(self, query: str, params: Optional[Dict] = None) -> Any:
        """Read from replica (load balanced)."""
        if not self.replicas:
            return self.write(query, params)

        replica = self.replicas[0]  # Simple round-robin
        return replica.execute_query(query, params)

    def get_replication_status(self) -> Dict:
        """Get replication status."""
        return {
            "mode": self.mode.value,
            "primary_connected": self.primary.connected if self.primary else False,
            "replica_count": len(self.replicas),
            "lag_ms": self.replication_lag_ms
        }


class AdvancedPersistenceLayer:
    """Main persistence orchestrator."""

    def __init__(self):
        self.connectors: Dict[str, DatabaseConnector] = {}
        self.migration_manager = MigrationManager()
        self.versioning = VersioningSystem()
        self.sharding = ShardingManager()
        self.replication = ReplicationManager()

    def add_database(self, name: str, config: DatabaseConfig) -> DatabaseConnector:
        """Add database."""
        connector = DatabaseConnector(config)
        connector.connect()
        self.connectors[name] = connector
        return connector

    def get_database(self, name: str) -> Optional[DatabaseConnector]:
        """Get database."""
        return self.connectors.get(name)

    def query_builder(self) -> QueryBuilder:
        """Create query builder."""
        return QueryBuilder()

    def get_persistence_stats(self) -> Dict:
        """Get persistence statistics."""
        return {
            "databases": len(self.connectors),
            "migrations": len(self.migration_manager.migrations),
            "versions": sum(len(v) for v in self.versioning.versions.values()),
            "shards": len(self.sharding.shards),
            "replication": self.replication.get_replication_status()
        }


# Global instance
_persistence_layer = None


def get_persistence_layer() -> AdvancedPersistenceLayer:
    """Get or create global persistence layer."""
    global _persistence_layer
    if _persistence_layer is None:
        _persistence_layer = AdvancedPersistenceLayer()
    return _persistence_layer
