#!/usr/bin/env python3
"""
BAEL - Migration Engine
Data migration for agents.

Features:
- Schema migrations
- Data transformations
- Version tracking
- Rollback support
- Batch processing
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MigrationState(Enum):
    """Migration states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationDirection(Enum):
    """Migration direction."""
    UP = "up"
    DOWN = "down"


class MigrationType(Enum):
    """Migration types."""
    SCHEMA = "schema"
    DATA = "data"
    TRANSFORM = "transform"
    SEED = "seed"
    CLEANUP = "cleanup"


class TransformOperation(Enum):
    """Transform operations."""
    RENAME = "rename"
    COPY = "copy"
    DELETE = "delete"
    CONVERT = "convert"
    MERGE = "merge"
    SPLIT = "split"
    MAP = "map"
    FILTER = "filter"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MigrationConfig:
    """Migration configuration."""
    batch_size: int = 1000
    timeout_seconds: float = 3600.0
    retry_attempts: int = 3
    dry_run: bool = False
    parallel: bool = False


@dataclass
class MigrationInfo:
    """Migration information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    version: int = 0
    migration_type: MigrationType = MigrationType.DATA
    state: MigrationState = MigrationState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: str = ""
    records_processed: int = 0
    records_failed: int = 0


@dataclass
class FieldMapping:
    """Field mapping for transformations."""
    source: str = ""
    target: str = ""
    operation: TransformOperation = TransformOperation.COPY
    transform: Optional[Callable[[Any], Any]] = None
    default: Any = None


@dataclass
class SchemaChange:
    """Schema change definition."""
    field_name: str = ""
    action: str = "add"
    field_type: str = "string"
    default_value: Any = None
    nullable: bool = True


@dataclass
class MigrationResult:
    """Migration result."""
    migration_id: str = ""
    success: bool = True
    records_processed: int = 0
    records_failed: int = 0
    duration_seconds: float = 0.0
    error: str = ""


@dataclass
class RollbackInfo:
    """Rollback information."""
    migration_id: str = ""
    backup_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MigrationStats:
    """Migration statistics."""
    total_migrations: int = 0
    successful_migrations: int = 0
    failed_migrations: int = 0
    rolled_back_migrations: int = 0
    total_records_processed: int = 0
    total_records_failed: int = 0


# =============================================================================
# MIGRATION INTERFACE
# =============================================================================

class Migration(ABC):
    """Abstract migration."""
    
    def __init__(self, name: str, version: int):
        self._name = name
        self._version = version
        self._info = MigrationInfo(name=name, version=version)
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> int:
        return self._version
    
    @property
    def info(self) -> MigrationInfo:
        return self._info
    
    @abstractmethod
    async def up(self, context: Dict[str, Any]) -> bool:
        """Run migration forward."""
        pass
    
    @abstractmethod
    async def down(self, context: Dict[str, Any]) -> bool:
        """Run migration backward."""
        pass
    
    def get_checksum(self) -> str:
        """Get migration checksum."""
        content = f"{self._name}:{self._version}"
        return hashlib.md5(content.encode()).hexdigest()[:8]


# =============================================================================
# DATA STORE
# =============================================================================

class DataStore:
    """Simple data store for migrations."""
    
    def __init__(self, name: str):
        self._name = name
        self._data: Dict[str, Dict[str, Any]] = {}
        self._schema: Dict[str, str] = {}
    
    @property
    def name(self) -> str:
        return self._name
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get record by key."""
        return self._data.get(key)
    
    def put(self, key: str, record: Dict[str, Any]) -> None:
        """Put record."""
        self._data[key] = record
    
    def delete(self, key: str) -> bool:
        """Delete record."""
        if key in self._data:
            del self._data[key]
            return True
        return False
    
    def all(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get all records."""
        return list(self._data.items())
    
    def count(self) -> int:
        """Count records."""
        return len(self._data)
    
    def add_field(self, name: str, field_type: str, default: Any = None) -> None:
        """Add field to schema."""
        self._schema[name] = field_type
        
        for record in self._data.values():
            if name not in record:
                record[name] = default
    
    def remove_field(self, name: str) -> None:
        """Remove field from schema."""
        if name in self._schema:
            del self._schema[name]
        
        for record in self._data.values():
            if name in record:
                del record[name]
    
    def rename_field(self, old_name: str, new_name: str) -> None:
        """Rename field."""
        if old_name in self._schema:
            self._schema[new_name] = self._schema.pop(old_name)
        
        for record in self._data.values():
            if old_name in record:
                record[new_name] = record.pop(old_name)
    
    def get_schema(self) -> Dict[str, str]:
        """Get schema."""
        return dict(self._schema)
    
    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()
    
    def export(self) -> Dict[str, Any]:
        """Export data."""
        return {
            "name": self._name,
            "schema": dict(self._schema),
            "data": dict(self._data)
        }
    
    def load(self, data: Dict[str, Any]) -> None:
        """Load data."""
        if "schema" in data:
            self._schema = data["schema"]
        if "data" in data:
            self._data = data["data"]


# =============================================================================
# SCHEMA MIGRATION
# =============================================================================

class SchemaMigration(Migration):
    """Schema migration."""
    
    def __init__(
        self,
        name: str,
        version: int,
        store_name: str,
        changes: List[SchemaChange]
    ):
        super().__init__(name, version)
        self._store_name = store_name
        self._changes = changes
        self._info.migration_type = MigrationType.SCHEMA
    
    async def up(self, context: Dict[str, Any]) -> bool:
        """Apply schema changes."""
        store = context.get("stores", {}).get(self._store_name)
        
        if not store:
            self._info.error = f"Store not found: {self._store_name}"
            return False
        
        for change in self._changes:
            if change.action == "add":
                store.add_field(
                    change.field_name,
                    change.field_type,
                    change.default_value
                )
            elif change.action == "remove":
                store.remove_field(change.field_name)
            elif change.action == "rename":
                old_name, new_name = change.field_name.split(":")
                store.rename_field(old_name, new_name)
        
        return True
    
    async def down(self, context: Dict[str, Any]) -> bool:
        """Rollback schema changes."""
        store = context.get("stores", {}).get(self._store_name)
        
        if not store:
            return False
        
        for change in reversed(self._changes):
            if change.action == "add":
                store.remove_field(change.field_name)
            elif change.action == "remove":
                store.add_field(
                    change.field_name,
                    change.field_type,
                    change.default_value
                )
            elif change.action == "rename":
                old_name, new_name = change.field_name.split(":")
                store.rename_field(new_name, old_name)
        
        return True


# =============================================================================
# DATA MIGRATION
# =============================================================================

class DataMigration(Migration):
    """Data migration with transformations."""
    
    def __init__(
        self,
        name: str,
        version: int,
        source_store: str,
        target_store: str,
        mappings: List[FieldMapping]
    ):
        super().__init__(name, version)
        self._source_store = source_store
        self._target_store = target_store
        self._mappings = mappings
        self._info.migration_type = MigrationType.DATA
    
    async def up(self, context: Dict[str, Any]) -> bool:
        """Run data migration."""
        stores = context.get("stores", {})
        source = stores.get(self._source_store)
        target = stores.get(self._target_store)
        
        if not source or not target:
            self._info.error = "Source or target store not found"
            return False
        
        for key, record in source.all():
            try:
                transformed = self._transform_record(record)
                target.put(key, transformed)
                self._info.records_processed += 1
            except Exception as e:
                self._info.records_failed += 1
                self._info.error = str(e)
        
        return self._info.records_failed == 0
    
    async def down(self, context: Dict[str, Any]) -> bool:
        """Rollback data migration."""
        stores = context.get("stores", {})
        target = stores.get(self._target_store)
        
        if target:
            target.clear()
        
        return True
    
    def _transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a record."""
        result = {}
        
        for mapping in self._mappings:
            value = record.get(mapping.source, mapping.default)
            
            if mapping.operation == TransformOperation.COPY:
                result[mapping.target] = value
            
            elif mapping.operation == TransformOperation.RENAME:
                result[mapping.target] = value
            
            elif mapping.operation == TransformOperation.CONVERT:
                if mapping.transform:
                    result[mapping.target] = mapping.transform(value)
                else:
                    result[mapping.target] = value
            
            elif mapping.operation == TransformOperation.MAP:
                if mapping.transform:
                    result[mapping.target] = mapping.transform(value)
                else:
                    result[mapping.target] = value
            
            elif mapping.operation == TransformOperation.DELETE:
                pass
        
        return result


# =============================================================================
# SEED MIGRATION
# =============================================================================

class SeedMigration(Migration):
    """Seed data migration."""
    
    def __init__(
        self,
        name: str,
        version: int,
        store_name: str,
        seed_data: List[Dict[str, Any]]
    ):
        super().__init__(name, version)
        self._store_name = store_name
        self._seed_data = seed_data
        self._info.migration_type = MigrationType.SEED
    
    async def up(self, context: Dict[str, Any]) -> bool:
        """Seed data."""
        store = context.get("stores", {}).get(self._store_name)
        
        if not store:
            self._info.error = f"Store not found: {self._store_name}"
            return False
        
        for i, record in enumerate(self._seed_data):
            key = record.get("id", f"seed_{i}")
            store.put(str(key), record)
            self._info.records_processed += 1
        
        return True
    
    async def down(self, context: Dict[str, Any]) -> bool:
        """Remove seeded data."""
        store = context.get("stores", {}).get(self._store_name)
        
        if not store:
            return False
        
        for i, record in enumerate(self._seed_data):
            key = record.get("id", f"seed_{i}")
            store.delete(str(key))
        
        return True


# =============================================================================
# CUSTOM MIGRATION
# =============================================================================

class CustomMigration(Migration):
    """Custom migration with callbacks."""
    
    def __init__(
        self,
        name: str,
        version: int,
        up_callback: Callable[[Dict[str, Any]], bool],
        down_callback: Optional[Callable[[Dict[str, Any]], bool]] = None
    ):
        super().__init__(name, version)
        self._up_callback = up_callback
        self._down_callback = down_callback
        self._info.migration_type = MigrationType.TRANSFORM
    
    async def up(self, context: Dict[str, Any]) -> bool:
        """Run up callback."""
        try:
            if asyncio.iscoroutinefunction(self._up_callback):
                return await self._up_callback(context)
            else:
                return self._up_callback(context)
        except Exception as e:
            self._info.error = str(e)
            return False
    
    async def down(self, context: Dict[str, Any]) -> bool:
        """Run down callback."""
        if not self._down_callback:
            return True
        
        try:
            if asyncio.iscoroutinefunction(self._down_callback):
                return await self._down_callback(context)
            else:
                return self._down_callback(context)
        except Exception as e:
            self._info.error = str(e)
            return False


# =============================================================================
# MIGRATION RUNNER
# =============================================================================

class MigrationRunner:
    """Runs migrations."""
    
    def __init__(self, config: Optional[MigrationConfig] = None):
        self._config = config or MigrationConfig()
        self._migrations: List[Migration] = []
        self._applied: Set[str] = set()
        self._rollback_info: Dict[str, RollbackInfo] = {}
        self._stats = MigrationStats()
    
    def add(self, migration: Migration) -> None:
        """Add a migration."""
        self._migrations.append(migration)
        self._migrations.sort(key=lambda m: m.version)
    
    def add_all(self, migrations: List[Migration]) -> None:
        """Add multiple migrations."""
        for migration in migrations:
            self.add(migration)
    
    async def run(
        self,
        context: Dict[str, Any],
        target_version: Optional[int] = None
    ) -> List[MigrationResult]:
        """Run pending migrations."""
        results = []
        
        for migration in self._migrations:
            if migration.info.id in self._applied:
                continue
            
            if target_version is not None and migration.version > target_version:
                break
            
            result = await self._run_migration(migration, context, MigrationDirection.UP)
            results.append(result)
            
            if not result.success:
                break
        
        return results
    
    async def rollback(
        self,
        context: Dict[str, Any],
        steps: int = 1
    ) -> List[MigrationResult]:
        """Rollback migrations."""
        results = []
        applied_list = [
            m for m in reversed(self._migrations)
            if m.info.id in self._applied
        ]
        
        for migration in applied_list[:steps]:
            result = await self._run_migration(migration, context, MigrationDirection.DOWN)
            results.append(result)
            
            if not result.success:
                break
        
        return results
    
    async def _run_migration(
        self,
        migration: Migration,
        context: Dict[str, Any],
        direction: MigrationDirection
    ) -> MigrationResult:
        """Run a single migration."""
        start_time = time.time()
        migration.info.state = MigrationState.RUNNING
        migration.info.started_at = datetime.now()
        
        self._stats.total_migrations += 1
        
        try:
            if direction == MigrationDirection.UP:
                success = await migration.up(context)
                
                if success:
                    self._applied.add(migration.info.id)
                    migration.info.state = MigrationState.COMPLETED
                    self._stats.successful_migrations += 1
                else:
                    migration.info.state = MigrationState.FAILED
                    self._stats.failed_migrations += 1
            else:
                success = await migration.down(context)
                
                if success:
                    self._applied.discard(migration.info.id)
                    migration.info.state = MigrationState.ROLLED_BACK
                    self._stats.rolled_back_migrations += 1
                else:
                    migration.info.state = MigrationState.FAILED
                    self._stats.failed_migrations += 1
        
        except Exception as e:
            success = False
            migration.info.state = MigrationState.FAILED
            migration.info.error = str(e)
            self._stats.failed_migrations += 1
        
        migration.info.completed_at = datetime.now()
        duration = time.time() - start_time
        
        self._stats.total_records_processed += migration.info.records_processed
        self._stats.total_records_failed += migration.info.records_failed
        
        return MigrationResult(
            migration_id=migration.info.id,
            success=success,
            records_processed=migration.info.records_processed,
            records_failed=migration.info.records_failed,
            duration_seconds=duration,
            error=migration.info.error
        )
    
    def get_pending(self) -> List[Migration]:
        """Get pending migrations."""
        return [m for m in self._migrations if m.info.id not in self._applied]
    
    def get_applied(self) -> List[Migration]:
        """Get applied migrations."""
        return [m for m in self._migrations if m.info.id in self._applied]
    
    def get_status(self) -> Dict[str, Any]:
        """Get migration status."""
        return {
            "total": len(self._migrations),
            "applied": len(self._applied),
            "pending": len(self._migrations) - len(self._applied),
            "migrations": [
                {
                    "name": m.name,
                    "version": m.version,
                    "state": m.info.state.value
                }
                for m in self._migrations
            ]
        }
    
    @property
    def stats(self) -> MigrationStats:
        return self._stats


# =============================================================================
# MIGRATION ENGINE
# =============================================================================

class MigrationEngine:
    """
    Migration Engine for BAEL.
    
    Data migration for agents.
    """
    
    def __init__(self, config: Optional[MigrationConfig] = None):
        self._config = config or MigrationConfig()
        self._stores: Dict[str, DataStore] = {}
        self._runners: Dict[str, MigrationRunner] = {}
        self._migrations: Dict[str, Migration] = {}
        self._stats = MigrationStats()
    
    # ----- Store Management -----
    
    def create_store(self, name: str) -> DataStore:
        """Create a data store."""
        store = DataStore(name)
        self._stores[name] = store
        return store
    
    def get_store(self, name: str) -> Optional[DataStore]:
        """Get a data store."""
        return self._stores.get(name)
    
    def list_stores(self) -> List[str]:
        """List all stores."""
        return list(self._stores.keys())
    
    # ----- Migration Management -----
    
    def create_schema_migration(
        self,
        name: str,
        version: int,
        store_name: str,
        changes: List[SchemaChange]
    ) -> SchemaMigration:
        """Create a schema migration."""
        migration = SchemaMigration(name, version, store_name, changes)
        self._migrations[migration.info.id] = migration
        return migration
    
    def create_data_migration(
        self,
        name: str,
        version: int,
        source_store: str,
        target_store: str,
        mappings: List[FieldMapping]
    ) -> DataMigration:
        """Create a data migration."""
        migration = DataMigration(name, version, source_store, target_store, mappings)
        self._migrations[migration.info.id] = migration
        return migration
    
    def create_seed_migration(
        self,
        name: str,
        version: int,
        store_name: str,
        seed_data: List[Dict[str, Any]]
    ) -> SeedMigration:
        """Create a seed migration."""
        migration = SeedMigration(name, version, store_name, seed_data)
        self._migrations[migration.info.id] = migration
        return migration
    
    def create_custom_migration(
        self,
        name: str,
        version: int,
        up_callback: Callable[[Dict[str, Any]], bool],
        down_callback: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> CustomMigration:
        """Create a custom migration."""
        migration = CustomMigration(name, version, up_callback, down_callback)
        self._migrations[migration.info.id] = migration
        return migration
    
    # ----- Runner Management -----
    
    def create_runner(self, name: str) -> MigrationRunner:
        """Create a migration runner."""
        runner = MigrationRunner(self._config)
        self._runners[name] = runner
        return runner
    
    def get_runner(self, name: str) -> Optional[MigrationRunner]:
        """Get a migration runner."""
        return self._runners.get(name)
    
    # ----- Migration Execution -----
    
    async def run_migrations(
        self,
        runner_name: str,
        target_version: Optional[int] = None
    ) -> List[MigrationResult]:
        """Run migrations."""
        runner = self._runners.get(runner_name)
        
        if not runner:
            return []
        
        context = {"stores": self._stores}
        results = await runner.run(context, target_version)
        
        self._update_stats(results)
        return results
    
    async def rollback_migrations(
        self,
        runner_name: str,
        steps: int = 1
    ) -> List[MigrationResult]:
        """Rollback migrations."""
        runner = self._runners.get(runner_name)
        
        if not runner:
            return []
        
        context = {"stores": self._stores}
        results = await runner.rollback(context, steps)
        
        self._update_stats(results)
        return results
    
    def _update_stats(self, results: List[MigrationResult]) -> None:
        """Update statistics."""
        for result in results:
            self._stats.total_migrations += 1
            
            if result.success:
                self._stats.successful_migrations += 1
            else:
                self._stats.failed_migrations += 1
            
            self._stats.total_records_processed += result.records_processed
            self._stats.total_records_failed += result.records_failed
    
    # ----- Status -----
    
    def get_runner_status(self, runner_name: str) -> Dict[str, Any]:
        """Get runner status."""
        runner = self._runners.get(runner_name)
        
        if not runner:
            return {}
        
        return runner.get_status()
    
    @property
    def stats(self) -> MigrationStats:
        return self._stats
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "stores": len(self._stores),
            "migrations": len(self._migrations),
            "runners": len(self._runners),
            "total_migrations": self._stats.total_migrations,
            "successful_migrations": self._stats.successful_migrations,
            "failed_migrations": self._stats.failed_migrations,
            "records_processed": self._stats.total_records_processed
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Migration Engine."""
    print("=" * 70)
    print("BAEL - MIGRATION ENGINE DEMO")
    print("Data Migration for Agents")
    print("=" * 70)
    print()
    
    engine = MigrationEngine()
    
    # 1. Create Stores
    print("1. CREATE DATA STORES:")
    print("-" * 40)
    
    users_v1 = engine.create_store("users_v1")
    users_v2 = engine.create_store("users_v2")
    
    print(f"   Created stores: {engine.list_stores()}")
    print()
    
    # 2. Seed Initial Data
    print("2. SEED INITIAL DATA:")
    print("-" * 40)
    
    users_v1.put("1", {"id": 1, "first_name": "Alice", "last_name": "Smith", "email": "alice@example.com"})
    users_v1.put("2", {"id": 2, "first_name": "Bob", "last_name": "Jones", "email": "bob@example.com"})
    users_v1.put("3", {"id": 3, "first_name": "Charlie", "last_name": "Brown", "email": "charlie@example.com"})
    
    print(f"   Seeded {users_v1.count()} users")
    for key, record in users_v1.all():
        print(f"   - {key}: {record}")
    print()
    
    # 3. Create Schema Migration
    print("3. CREATE SCHEMA MIGRATION:")
    print("-" * 40)
    
    schema_migration = engine.create_schema_migration(
        name="add_active_field",
        version=1,
        store_name="users_v1",
        changes=[
            SchemaChange(field_name="active", action="add", field_type="bool", default_value=True),
            SchemaChange(field_name="created_at", action="add", field_type="datetime", default_value="2024-01-01")
        ]
    )
    
    print(f"   Created: {schema_migration.name} v{schema_migration.version}")
    print()
    
    # 4. Create Data Migration
    print("4. CREATE DATA MIGRATION:")
    print("-" * 40)
    
    data_migration = engine.create_data_migration(
        name="migrate_users",
        version=2,
        source_store="users_v1",
        target_store="users_v2",
        mappings=[
            FieldMapping(source="id", target="id", operation=TransformOperation.COPY),
            FieldMapping(
                source="first_name",
                target="name",
                operation=TransformOperation.CONVERT,
                transform=lambda r: f"{r}"
            ),
            FieldMapping(source="email", target="email", operation=TransformOperation.COPY),
            FieldMapping(source="active", target="is_active", operation=TransformOperation.RENAME)
        ]
    )
    
    print(f"   Created: {data_migration.name} v{data_migration.version}")
    print()
    
    # 5. Create Seed Migration
    print("5. CREATE SEED MIGRATION:")
    print("-" * 40)
    
    seed_migration = engine.create_seed_migration(
        name="seed_admin",
        version=3,
        store_name="users_v2",
        seed_data=[
            {"id": "admin", "name": "Admin", "email": "admin@example.com", "is_active": True}
        ]
    )
    
    print(f"   Created: {seed_migration.name} v{seed_migration.version}")
    print()
    
    # 6. Create Custom Migration
    print("6. CREATE CUSTOM MIGRATION:")
    print("-" * 40)
    
    def custom_up(context: Dict[str, Any]) -> bool:
        stores = context.get("stores", {})
        v2 = stores.get("users_v2")
        if v2:
            for key, record in v2.all():
                record["migrated"] = True
        return True
    
    def custom_down(context: Dict[str, Any]) -> bool:
        stores = context.get("stores", {})
        v2 = stores.get("users_v2")
        if v2:
            for key, record in v2.all():
                if "migrated" in record:
                    del record["migrated"]
        return True
    
    custom_migration = engine.create_custom_migration(
        name="mark_migrated",
        version=4,
        up_callback=custom_up,
        down_callback=custom_down
    )
    
    print(f"   Created: {custom_migration.name} v{custom_migration.version}")
    print()
    
    # 7. Create Runner and Add Migrations
    print("7. CREATE MIGRATION RUNNER:")
    print("-" * 40)
    
    runner = engine.create_runner("main")
    runner.add(schema_migration)
    runner.add(data_migration)
    runner.add(seed_migration)
    runner.add(custom_migration)
    
    status = engine.get_runner_status("main")
    print(f"   Total migrations: {status['total']}")
    print(f"   Applied: {status['applied']}")
    print(f"   Pending: {status['pending']}")
    print()
    
    # 8. Run Schema Migration
    print("8. RUN SCHEMA MIGRATION:")
    print("-" * 40)
    
    results = await engine.run_migrations("main", target_version=1)
    
    for result in results:
        print(f"   Migration: {result.migration_id}")
        print(f"   Success: {result.success}")
        print(f"   Duration: {result.duration_seconds:.3f}s")
    
    print(f"\n   Updated records:")
    for key, record in users_v1.all():
        print(f"   - {key}: {record}")
    print()
    
    # 9. Run Data Migration
    print("9. RUN DATA MIGRATION:")
    print("-" * 40)
    
    results = await engine.run_migrations("main", target_version=2)
    
    for result in results:
        print(f"   Migration: {result.migration_id}")
        print(f"   Records processed: {result.records_processed}")
    
    print(f"\n   Migrated to users_v2:")
    for key, record in users_v2.all():
        print(f"   - {key}: {record}")
    print()
    
    # 10. Run Remaining Migrations
    print("10. RUN REMAINING MIGRATIONS:")
    print("-" * 40)
    
    results = await engine.run_migrations("main")
    
    for result in results:
        print(f"   Migration: {result.migration_id} - Success: {result.success}")
    
    print(f"\n   Final users_v2:")
    for key, record in users_v2.all():
        print(f"   - {key}: {record}")
    print()
    
    # 11. Migration Status
    print("11. MIGRATION STATUS:")
    print("-" * 40)
    
    status = engine.get_runner_status("main")
    print(f"   Total: {status['total']}")
    print(f"   Applied: {status['applied']}")
    print(f"   Pending: {status['pending']}")
    
    for m in status['migrations']:
        print(f"   - {m['name']} v{m['version']}: {m['state']}")
    print()
    
    # 12. Rollback
    print("12. ROLLBACK MIGRATION:")
    print("-" * 40)
    
    results = await engine.rollback_migrations("main", steps=1)
    
    for result in results:
        print(f"   Rolled back: {result.migration_id}")
    
    print(f"\n   After rollback:")
    for key, record in users_v2.all():
        print(f"   - {key}: {record}")
    print()
    
    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats
    print(f"   Total migrations: {stats.total_migrations}")
    print(f"   Successful: {stats.successful_migrations}")
    print(f"   Failed: {stats.failed_migrations}")
    print(f"   Records processed: {stats.total_records_processed}")
    print()
    
    # 14. Engine Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Migration Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
