#!/usr/bin/env python3
"""
BAEL - Migration Manager
Advanced migration management for AI agent data transformations.

Features:
- Version tracking
- Forward/backward migrations
- Dry-run support
- Rollback capability
- Dependency resolution
- Migration locking
- Batch migrations
- Data transformations
- Schema evolution
- Migration history
"""

import asyncio
import hashlib
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar)

logger = logging.getLogger(__name__)


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
    SKIPPED = "skipped"


class MigrationDirection(Enum):
    """Migration direction."""
    UP = "up"
    DOWN = "down"


class MigrationStrategy(Enum):
    """Migration execution strategy."""
    SEQUENTIAL = "sequential"
    TRANSACTIONAL = "transactional"
    BATCH = "batch"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MigrationVersion:
    """Migration version."""
    major: int = 0
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: 'MigrationVersion') -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MigrationVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))

    @classmethod
    def parse(cls, version_str: str) -> 'MigrationVersion':
        parts = version_str.split('.')
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 0,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0
        )


@dataclass
class MigrationConfig:
    """Migration configuration."""
    strategy: MigrationStrategy = MigrationStrategy.SEQUENTIAL
    dry_run: bool = False
    batch_size: int = 100
    timeout: float = 300.0
    allow_downgrade: bool = True
    auto_backup: bool = True


@dataclass
class MigrationResult:
    """Migration execution result."""
    migration_id: str
    direction: MigrationDirection
    success: bool
    duration_ms: float
    changes_made: int = 0
    error: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MigrationHistory:
    """Migration history entry."""
    migration_id: str
    version: str
    name: str
    direction: MigrationDirection
    state: MigrationState
    executed_at: datetime
    duration_ms: float
    checksum: str


@dataclass
class MigrationStats:
    """Migration statistics."""
    total_migrations: int = 0
    completed: int = 0
    failed: int = 0
    pending: int = 0
    avg_duration_ms: float = 0.0


@dataclass
class MigrationContext:
    """Context passed to migrations."""
    migration_id: str
    direction: MigrationDirection
    dry_run: bool
    data: Dict[str, Any] = field(default_factory=dict)
    changes: List[str] = field(default_factory=list)


# =============================================================================
# MIGRATION BASE
# =============================================================================

class Migration(ABC):
    """
    Abstract base migration.
    """

    def __init__(
        self,
        migration_id: Optional[str] = None,
        version: Optional[MigrationVersion] = None,
        name: str = "",
        dependencies: Optional[List[str]] = None
    ):
        self.migration_id = migration_id or str(uuid.uuid4())
        self.version = version or MigrationVersion()
        self.name = name or self.__class__.__name__
        self.dependencies = dependencies or []
        self.state = MigrationState.PENDING

    @property
    def checksum(self) -> str:
        """Calculate migration checksum."""
        content = f"{self.migration_id}:{self.version}:{self.name}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @abstractmethod
    async def up(self, ctx: MigrationContext) -> None:
        """Apply migration."""
        pass

    @abstractmethod
    async def down(self, ctx: MigrationContext) -> None:
        """Rollback migration."""
        pass


class DataMigration(Migration):
    """
    Data transformation migration.
    """

    def __init__(
        self,
        transform_up: Callable[[Any], Any],
        transform_down: Callable[[Any], Any],
        **kwargs
    ):
        super().__init__(**kwargs)
        self._transform_up = transform_up
        self._transform_down = transform_down
        self._data: Dict[str, Any] = {}

    async def up(self, ctx: MigrationContext) -> None:
        """Transform data up."""
        for key, value in list(self._data.items()):
            new_value = self._transform_up(value)
            self._data[key] = new_value
            ctx.changes.append(f"Transformed {key}")

    async def down(self, ctx: MigrationContext) -> None:
        """Transform data down."""
        for key, value in list(self._data.items()):
            new_value = self._transform_down(value)
            self._data[key] = new_value
            ctx.changes.append(f"Reverted {key}")

    def set_data(self, data: Dict[str, Any]) -> None:
        """Set data to transform."""
        self._data = data


class SchemaMigration(Migration):
    """
    Schema evolution migration.
    """

    def __init__(
        self,
        add_fields: Optional[Dict[str, Any]] = None,
        remove_fields: Optional[List[str]] = None,
        rename_fields: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.add_fields = add_fields or {}
        self.remove_fields = remove_fields or []
        self.rename_fields = rename_fields or {}
        self._schema: Dict[str, Any] = {}

    async def up(self, ctx: MigrationContext) -> None:
        """Apply schema changes."""
        # Add fields
        for field_name, default in self.add_fields.items():
            self._schema[field_name] = default
            ctx.changes.append(f"Added field: {field_name}")

        # Rename fields
        for old_name, new_name in self.rename_fields.items():
            if old_name in self._schema:
                self._schema[new_name] = self._schema.pop(old_name)
                ctx.changes.append(f"Renamed: {old_name} -> {new_name}")

        # Remove fields
        for field_name in self.remove_fields:
            self._schema.pop(field_name, None)
            ctx.changes.append(f"Removed field: {field_name}")

    async def down(self, ctx: MigrationContext) -> None:
        """Rollback schema changes."""
        # Re-add removed fields
        for field_name in self.remove_fields:
            self._schema[field_name] = None
            ctx.changes.append(f"Restored field: {field_name}")

        # Undo renames
        for old_name, new_name in self.rename_fields.items():
            if new_name in self._schema:
                self._schema[old_name] = self._schema.pop(new_name)
                ctx.changes.append(f"Renamed back: {new_name} -> {old_name}")

        # Remove added fields
        for field_name in self.add_fields:
            self._schema.pop(field_name, None)
            ctx.changes.append(f"Removed: {field_name}")

    def set_schema(self, schema: Dict[str, Any]) -> None:
        """Set current schema."""
        self._schema = schema


class FunctionMigration(Migration):
    """
    Function-based migration.
    """

    def __init__(
        self,
        up_fn: Callable[[MigrationContext], Awaitable[None]],
        down_fn: Callable[[MigrationContext], Awaitable[None]],
        **kwargs
    ):
        super().__init__(**kwargs)
        self._up_fn = up_fn
        self._down_fn = down_fn

    async def up(self, ctx: MigrationContext) -> None:
        await self._up_fn(ctx)

    async def down(self, ctx: MigrationContext) -> None:
        await self._down_fn(ctx)


# =============================================================================
# MIGRATION STORE
# =============================================================================

class MigrationStore(ABC):
    """Abstract migration history store."""

    @abstractmethod
    async def save_history(self, history: MigrationHistory) -> None:
        pass

    @abstractmethod
    async def get_history(self) -> List[MigrationHistory]:
        pass

    @abstractmethod
    async def get_last_version(self) -> Optional[MigrationVersion]:
        pass

    @abstractmethod
    async def is_applied(self, migration_id: str) -> bool:
        pass


class InMemoryMigrationStore(MigrationStore):
    """In-memory migration store."""

    def __init__(self):
        self._history: List[MigrationHistory] = []
        self._applied: Set[str] = set()
        self._lock = asyncio.Lock()

    async def save_history(self, history: MigrationHistory) -> None:
        async with self._lock:
            self._history.append(history)
            if history.state == MigrationState.COMPLETED:
                self._applied.add(history.migration_id)
            elif history.state == MigrationState.ROLLED_BACK:
                self._applied.discard(history.migration_id)

    async def get_history(self) -> List[MigrationHistory]:
        async with self._lock:
            return self._history.copy()

    async def get_last_version(self) -> Optional[MigrationVersion]:
        async with self._lock:
            if not self._history:
                return None

            completed = [
                h for h in self._history
                if h.state == MigrationState.COMPLETED
            ]

            if not completed:
                return None

            return MigrationVersion.parse(completed[-1].version)

    async def is_applied(self, migration_id: str) -> bool:
        async with self._lock:
            return migration_id in self._applied


# =============================================================================
# MIGRATION RUNNER
# =============================================================================

class MigrationRunner:
    """
    Executes migrations with proper ordering.
    """

    def __init__(self, config: Optional[MigrationConfig] = None):
        self.config = config or MigrationConfig()

    async def run(
        self,
        migration: Migration,
        direction: MigrationDirection
    ) -> MigrationResult:
        """Run a single migration."""
        ctx = MigrationContext(
            migration_id=migration.migration_id,
            direction=direction,
            dry_run=self.config.dry_run
        )

        start_time = time.time()

        try:
            if direction == MigrationDirection.UP:
                await asyncio.wait_for(
                    migration.up(ctx),
                    timeout=self.config.timeout
                )
            else:
                await asyncio.wait_for(
                    migration.down(ctx),
                    timeout=self.config.timeout
                )

            migration.state = MigrationState.COMPLETED

            return MigrationResult(
                migration_id=migration.migration_id,
                direction=direction,
                success=True,
                duration_ms=(time.time() - start_time) * 1000,
                changes_made=len(ctx.changes)
            )

        except asyncio.TimeoutError:
            migration.state = MigrationState.FAILED
            return MigrationResult(
                migration_id=migration.migration_id,
                direction=direction,
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error="Migration timeout"
            )

        except Exception as e:
            migration.state = MigrationState.FAILED
            return MigrationResult(
                migration_id=migration.migration_id,
                direction=direction,
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class DependencyResolver:
    """
    Resolves migration dependencies.
    """

    def __init__(self):
        self._graph: Dict[str, Set[str]] = defaultdict(set)

    def add_migration(self, migration: Migration) -> None:
        """Add migration with dependencies."""
        self._graph[migration.migration_id]
        for dep in migration.dependencies:
            self._graph[migration.migration_id].add(dep)

    def resolve(self, migrations: List[Migration]) -> List[Migration]:
        """Resolve and order migrations."""
        for m in migrations:
            self.add_migration(m)

        # Topological sort
        visited: Set[str] = set()
        temp_mark: Set[str] = set()
        result: List[str] = []

        def visit(node: str) -> None:
            if node in temp_mark:
                raise ValueError(f"Circular dependency: {node}")
            if node in visited:
                return

            temp_mark.add(node)

            for dep in self._graph.get(node, set()):
                visit(dep)

            temp_mark.remove(node)
            visited.add(node)
            result.append(node)

        for migration in migrations:
            if migration.migration_id not in visited:
                visit(migration.migration_id)

        # Map back to migrations
        id_map = {m.migration_id: m for m in migrations}
        return [id_map[mid] for mid in result if mid in id_map]


# =============================================================================
# MIGRATION LOCK
# =============================================================================

class MigrationLock:
    """
    Prevents concurrent migrations.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._holder: Optional[str] = None
        self._acquired_at: Optional[datetime] = None

    async def acquire(self, migration_id: str, timeout: float = 30.0) -> bool:
        """Acquire migration lock."""
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            self._holder = migration_id
            self._acquired_at = datetime.utcnow()
            return True
        except asyncio.TimeoutError:
            return False

    def release(self) -> None:
        """Release migration lock."""
        self._holder = None
        self._acquired_at = None
        if self._lock.locked():
            self._lock.release()

    @property
    def is_locked(self) -> bool:
        return self._lock.locked()

    @property
    def holder(self) -> Optional[str]:
        return self._holder


# =============================================================================
# MIGRATION MANAGER
# =============================================================================

class MigrationManager:
    """
    Migration Manager for BAEL.

    Advanced migration management.
    """

    def __init__(
        self,
        store: Optional[MigrationStore] = None,
        config: Optional[MigrationConfig] = None
    ):
        self.store = store or InMemoryMigrationStore()
        self.config = config or MigrationConfig()

        self._migrations: Dict[str, Migration] = {}
        self._runner = MigrationRunner(self.config)
        self._resolver = DependencyResolver()
        self._lock = MigrationLock()
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)

    # -------------------------------------------------------------------------
    # REGISTRATION
    # -------------------------------------------------------------------------

    def register(self, migration: Migration) -> None:
        """Register a migration."""
        self._migrations[migration.migration_id] = migration
        self._resolver.add_migration(migration)

    def register_many(self, migrations: List[Migration]) -> None:
        """Register multiple migrations."""
        for migration in migrations:
            self.register(migration)

    def create_migration(
        self,
        name: str,
        version: str,
        up_fn: Callable[[MigrationContext], Awaitable[None]],
        down_fn: Callable[[MigrationContext], Awaitable[None]],
        dependencies: Optional[List[str]] = None
    ) -> Migration:
        """Create and register a function migration."""
        migration = FunctionMigration(
            up_fn=up_fn,
            down_fn=down_fn,
            name=name,
            version=MigrationVersion.parse(version),
            dependencies=dependencies
        )
        self.register(migration)
        return migration

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def migrate(
        self,
        target_version: Optional[str] = None
    ) -> List[MigrationResult]:
        """Run all pending migrations."""
        if not await self._lock.acquire("migrate"):
            raise RuntimeError("Migration already in progress")

        try:
            results = []

            # Get pending migrations
            pending = await self.get_pending()

            if target_version:
                target = MigrationVersion.parse(target_version)
                pending = [m for m in pending if m.version <= target]

            # Resolve dependencies
            ordered = self._resolver.resolve(pending)

            # Execute migrations
            for migration in ordered:
                self._emit("before_migrate", migration)

                result = await self._runner.run(
                    migration,
                    MigrationDirection.UP
                )
                results.append(result)

                if result.success:
                    await self._save_history(migration, MigrationDirection.UP, result)
                    self._emit("after_migrate", migration, result)
                else:
                    self._emit("migration_failed", migration, result)
                    if self.config.strategy == MigrationStrategy.TRANSACTIONAL:
                        # Rollback all completed migrations
                        await self._rollback_completed(results[:-1])
                        break

            return results

        finally:
            self._lock.release()

    async def rollback(
        self,
        steps: int = 1
    ) -> List[MigrationResult]:
        """Rollback migrations."""
        if not self.config.allow_downgrade:
            raise RuntimeError("Downgrades not allowed")

        if not await self._lock.acquire("rollback"):
            raise RuntimeError("Migration already in progress")

        try:
            results = []

            # Get applied migrations in reverse order
            history = await self.store.get_history()
            applied = [
                h for h in reversed(history)
                if h.state == MigrationState.COMPLETED
            ][:steps]

            for hist in applied:
                migration = self._migrations.get(hist.migration_id)
                if not migration:
                    continue

                self._emit("before_rollback", migration)

                result = await self._runner.run(
                    migration,
                    MigrationDirection.DOWN
                )
                results.append(result)

                if result.success:
                    await self._save_history(migration, MigrationDirection.DOWN, result)
                    self._emit("after_rollback", migration, result)
                else:
                    self._emit("rollback_failed", migration, result)
                    break

            return results

        finally:
            self._lock.release()

    async def migrate_to(self, version: str) -> List[MigrationResult]:
        """Migrate to a specific version."""
        target = MigrationVersion.parse(version)
        current = await self.store.get_last_version()

        if current is None or target > current:
            # Forward migration
            return await self.migrate(version)
        elif target < current:
            # Backward migration (rollback)
            # Count how many to rollback
            history = await self.store.get_history()
            applied = [
                h for h in history
                if h.state == MigrationState.COMPLETED
                and MigrationVersion.parse(h.version) > target
            ]
            return await self.rollback(len(applied))

        return []  # Already at target version

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def get_pending(self) -> List[Migration]:
        """Get pending migrations."""
        pending = []

        for migration in self._migrations.values():
            if not await self.store.is_applied(migration.migration_id):
                pending.append(migration)

        # Sort by version
        pending.sort(key=lambda m: m.version)
        return pending

    async def get_applied(self) -> List[MigrationHistory]:
        """Get applied migrations."""
        history = await self.store.get_history()
        return [h for h in history if h.state == MigrationState.COMPLETED]

    async def get_current_version(self) -> Optional[MigrationVersion]:
        """Get current version."""
        return await self.store.get_last_version()

    async def get_status(self) -> Dict[str, Any]:
        """Get migration status."""
        current = await self.get_current_version()
        pending = await self.get_pending()
        applied = await self.get_applied()

        return {
            "current_version": str(current) if current else None,
            "pending_count": len(pending),
            "applied_count": len(applied),
            "is_locked": self._lock.is_locked,
            "pending_migrations": [
                {"id": m.migration_id, "name": m.name, "version": str(m.version)}
                for m in pending
            ]
        }

    async def get_stats(self) -> MigrationStats:
        """Get migration statistics."""
        history = await self.store.get_history()

        completed = [h for h in history if h.state == MigrationState.COMPLETED]
        failed = [h for h in history if h.state == MigrationState.FAILED]
        pending = await self.get_pending()

        avg_duration = 0.0
        if completed:
            avg_duration = sum(h.duration_ms for h in completed) / len(completed)

        return MigrationStats(
            total_migrations=len(self._migrations),
            completed=len(completed),
            failed=len(failed),
            pending=len(pending),
            avg_duration_ms=avg_duration
        )

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    async def validate(self) -> List[str]:
        """Validate migrations."""
        errors = []

        for migration in self._migrations.values():
            # Check dependencies exist
            for dep in migration.dependencies:
                if dep not in self._migrations:
                    errors.append(f"Missing dependency: {dep} for {migration.name}")

        # Check for circular dependencies
        try:
            self._resolver.resolve(list(self._migrations.values()))
        except ValueError as e:
            errors.append(str(e))

        # Check for duplicate versions
        versions: Dict[str, List[str]] = defaultdict(list)
        for m in self._migrations.values():
            versions[str(m.version)].append(m.name)

        for version, names in versions.items():
            if len(names) > 1:
                errors.append(f"Duplicate version {version}: {names}")

        return errors

    # -------------------------------------------------------------------------
    # DRY RUN
    # -------------------------------------------------------------------------

    async def dry_run(self) -> List[Dict[str, Any]]:
        """Simulate migrations without executing."""
        pending = await self.get_pending()
        ordered = self._resolver.resolve(pending)

        results = []
        for migration in ordered:
            results.append({
                "migration_id": migration.migration_id,
                "name": migration.name,
                "version": str(migration.version),
                "dependencies": migration.dependencies,
                "checksum": migration.checksum
            })

        return results

    # -------------------------------------------------------------------------
    # CALLBACKS
    # -------------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        self._callbacks[event].append(callback)

    def _emit(self, event: str, *args: Any) -> None:
        """Emit event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # -------------------------------------------------------------------------
    # INTERNAL
    # -------------------------------------------------------------------------

    async def _save_history(
        self,
        migration: Migration,
        direction: MigrationDirection,
        result: MigrationResult
    ) -> None:
        """Save migration history."""
        state = MigrationState.COMPLETED if result.success else MigrationState.FAILED

        if direction == MigrationDirection.DOWN and result.success:
            state = MigrationState.ROLLED_BACK

        history = MigrationHistory(
            migration_id=migration.migration_id,
            version=str(migration.version),
            name=migration.name,
            direction=direction,
            state=state,
            executed_at=result.executed_at,
            duration_ms=result.duration_ms,
            checksum=migration.checksum
        )

        await self.store.save_history(history)

    async def _rollback_completed(
        self,
        results: List[MigrationResult]
    ) -> None:
        """Rollback completed migrations on failure."""
        for result in reversed(results):
            if result.success:
                migration = self._migrations.get(result.migration_id)
                if migration:
                    await self._runner.run(migration, MigrationDirection.DOWN)


# =============================================================================
# MIGRATION BUILDER
# =============================================================================

class MigrationBuilder:
    """
    Fluent builder for migrations.
    """

    def __init__(self):
        self._name: str = ""
        self._version: str = "0.0.1"
        self._dependencies: List[str] = []
        self._up_actions: List[Callable[[MigrationContext], Awaitable[None]]] = []
        self._down_actions: List[Callable[[MigrationContext], Awaitable[None]]] = []

    def name(self, name: str) -> 'MigrationBuilder':
        self._name = name
        return self

    def version(self, version: str) -> 'MigrationBuilder':
        self._version = version
        return self

    def depends_on(self, *deps: str) -> 'MigrationBuilder':
        self._dependencies.extend(deps)
        return self

    def up(self, action: Callable[[MigrationContext], Awaitable[None]]) -> 'MigrationBuilder':
        self._up_actions.append(action)
        return self

    def down(self, action: Callable[[MigrationContext], Awaitable[None]]) -> 'MigrationBuilder':
        self._down_actions.append(action)
        return self

    def build(self) -> Migration:
        up_actions = self._up_actions.copy()
        down_actions = self._down_actions.copy()

        async def up_fn(ctx: MigrationContext) -> None:
            for action in up_actions:
                await action(ctx)

        async def down_fn(ctx: MigrationContext) -> None:
            for action in down_actions:
                await action(ctx)

        return FunctionMigration(
            up_fn=up_fn,
            down_fn=down_fn,
            name=self._name,
            version=MigrationVersion.parse(self._version),
            dependencies=self._dependencies
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Migration Manager."""
    print("=" * 70)
    print("BAEL - MIGRATION MANAGER DEMO")
    print("Advanced Migration Management for AI Agents")
    print("=" * 70)
    print()

    manager = MigrationManager()

    # Track events
    events: List[str] = []
    manager.on("before_migrate", lambda m: events.append(f"before: {m.name}"))
    manager.on("after_migrate", lambda m, r: events.append(f"after: {m.name}"))

    # 1. Create Migrations
    print("1. CREATE MIGRATIONS:")
    print("-" * 40)

    async def add_users_table(ctx: MigrationContext):
        ctx.changes.append("Created users table")
        print(f"   [UP] Creating users table...")

    async def remove_users_table(ctx: MigrationContext):
        ctx.changes.append("Dropped users table")
        print(f"   [DOWN] Dropping users table...")

    m1 = manager.create_migration(
        name="create_users_table",
        version="1.0.0",
        up_fn=add_users_table,
        down_fn=remove_users_table
    )
    print(f"   Created: {m1.name} (v{m1.version})")

    async def add_users_index(ctx: MigrationContext):
        ctx.changes.append("Created users index")
        print(f"   [UP] Creating users index...")

    async def remove_users_index(ctx: MigrationContext):
        ctx.changes.append("Dropped users index")
        print(f"   [DOWN] Dropping users index...")

    m2 = manager.create_migration(
        name="add_users_index",
        version="1.1.0",
        up_fn=add_users_index,
        down_fn=remove_users_index,
        dependencies=[m1.migration_id]
    )
    print(f"   Created: {m2.name} (v{m2.version})")

    async def add_email_column(ctx: MigrationContext):
        ctx.changes.append("Added email column")
        print(f"   [UP] Adding email column...")

    async def remove_email_column(ctx: MigrationContext):
        ctx.changes.append("Removed email column")
        print(f"   [DOWN] Removing email column...")

    m3 = manager.create_migration(
        name="add_email_column",
        version="1.2.0",
        up_fn=add_email_column,
        down_fn=remove_email_column,
        dependencies=[m1.migration_id]
    )
    print(f"   Created: {m3.name} (v{m3.version})")
    print()

    # 2. Check Status
    print("2. MIGRATION STATUS:")
    print("-" * 40)

    status = await manager.get_status()
    print(f"   Current version: {status['current_version']}")
    print(f"   Pending: {status['pending_count']}")
    print(f"   Applied: {status['applied_count']}")
    print()

    # 3. Dry Run
    print("3. DRY RUN:")
    print("-" * 40)

    dry_results = await manager.dry_run()
    for result in dry_results:
        print(f"   Would run: {result['name']} (v{result['version']})")
    print()

    # 4. Run Migrations
    print("4. RUN MIGRATIONS:")
    print("-" * 40)

    results = await manager.migrate()
    for result in results:
        status_icon = "✓" if result.success else "✗"
        print(f"   {status_icon} {result.migration_id[:8]}... ({result.duration_ms:.2f}ms)")
    print()

    # 5. Check Version
    print("5. CURRENT VERSION:")
    print("-" * 40)

    current = await manager.get_current_version()
    print(f"   Version: {current}")
    print()

    # 6. Events
    print("6. EVENTS TRIGGERED:")
    print("-" * 40)
    for event in events:
        print(f"   - {event}")
    print()

    # 7. Rollback
    print("7. ROLLBACK (1 step):")
    print("-" * 40)

    rollback_results = await manager.rollback(1)
    for result in rollback_results:
        status_icon = "✓" if result.success else "✗"
        print(f"   {status_icon} Rolled back: {result.migration_id[:8]}...")

    current = await manager.get_current_version()
    print(f"   New version: {current}")
    print()

    # 8. Migration Builder
    print("8. MIGRATION BUILDER:")
    print("-" * 40)

    async def add_orders(ctx: MigrationContext):
        ctx.changes.append("Created orders table")

    async def remove_orders(ctx: MigrationContext):
        ctx.changes.append("Dropped orders table")

    builder_migration = (
        MigrationBuilder()
        .name("create_orders_table")
        .version("2.0.0")
        .up(add_orders)
        .down(remove_orders)
        .build()
    )

    manager.register(builder_migration)
    print(f"   Built: {builder_migration.name}")
    print()

    # 9. Schema Migration
    print("9. SCHEMA MIGRATION:")
    print("-" * 40)

    schema_migration = SchemaMigration(
        name="update_user_schema",
        version=MigrationVersion.parse("2.1.0"),
        add_fields={"phone": None, "address": ""},
        remove_fields=["legacy_field"],
        rename_fields={"old_name": "new_name"}
    )
    schema_migration.set_schema({"id": 1, "legacy_field": "value", "old_name": "test"})

    manager.register(schema_migration)
    print(f"   Registered: {schema_migration.name}")
    print(f"   Add fields: {list(schema_migration.add_fields.keys())}")
    print(f"   Remove: {schema_migration.remove_fields}")
    print(f"   Rename: {schema_migration.rename_fields}")
    print()

    # 10. Data Migration
    print("10. DATA MIGRATION:")
    print("-" * 40)

    data_migration = DataMigration(
        name="uppercase_names",
        version=MigrationVersion.parse("2.2.0"),
        transform_up=lambda x: x.upper() if isinstance(x, str) else x,
        transform_down=lambda x: x.lower() if isinstance(x, str) else x
    )
    data_migration.set_data({"name1": "alice", "name2": "bob"})

    manager.register(data_migration)
    print(f"   Registered: {data_migration.name}")
    print(f"   Before: {data_migration._data}")

    ctx = MigrationContext(
        migration_id=data_migration.migration_id,
        direction=MigrationDirection.UP,
        dry_run=False
    )
    await data_migration.up(ctx)
    print(f"   After UP: {data_migration._data}")
    print()

    # 11. Validate
    print("11. VALIDATION:")
    print("-" * 40)

    errors = await manager.validate()
    if errors:
        for error in errors:
            print(f"   Error: {error}")
    else:
        print("   All migrations valid ✓")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    stats = await manager.get_stats()
    print(f"   Total migrations: {stats.total_migrations}")
    print(f"   Completed: {stats.completed}")
    print(f"   Failed: {stats.failed}")
    print(f"   Pending: {stats.pending}")
    print(f"   Avg duration: {stats.avg_duration_ms:.2f}ms")
    print()

    # 13. Migrate to Version
    print("13. MIGRATE TO SPECIFIC VERSION:")
    print("-" * 40)

    # First migrate all pending
    await manager.migrate()
    current = await manager.get_current_version()
    print(f"   Current: {current}")

    # Now migrate back to 1.1.0
    results = await manager.migrate_to("1.1.0")
    current = await manager.get_current_version()
    print(f"   After migrate_to('1.1.0'): {current}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Migration Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
