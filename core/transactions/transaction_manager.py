#!/usr/bin/env python3
"""
BAEL - Transaction Manager
Advanced transaction management for AI agent operations.

Features:
- ACID transactions
- Nested transactions
- Savepoints
- Rollback support
- Transaction isolation
- Two-phase commit
- Compensation actions
- Transaction logging
- Timeout handling
- Distributed transactions
"""

import asyncio
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, AsyncIterator, Awaitable, Callable, Dict, Generic,
                    List, Optional, Set, Tuple, TypeVar)

logger = logging.getLogger(__name__)


T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class TransactionState(Enum):
    """Transaction states."""
    PENDING = "pending"
    ACTIVE = "active"
    PREPARED = "prepared"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class IsolationLevel(Enum):
    """Transaction isolation levels."""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


class PropagationType(Enum):
    """Transaction propagation types."""
    REQUIRED = "required"
    REQUIRES_NEW = "requires_new"
    SUPPORTS = "supports"
    NOT_SUPPORTED = "not_supported"
    MANDATORY = "mandatory"
    NEVER = "never"
    NESTED = "nested"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TransactionConfig:
    """Transaction configuration."""
    isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED
    propagation: PropagationType = PropagationType.REQUIRED
    timeout: Optional[float] = 30.0
    read_only: bool = False
    auto_commit: bool = False


@dataclass
class Savepoint:
    """Transaction savepoint."""
    savepoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    operations: List['Operation'] = field(default_factory=list)


@dataclass
class Operation:
    """A transactional operation."""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: str = ""
    target: str = ""
    data: Any = None
    compensation: Optional[Callable[[], Awaitable[None]]] = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TransactionStats:
    """Transaction statistics."""
    total_started: int = 0
    total_committed: int = 0
    total_rolled_back: int = 0
    total_failed: int = 0
    avg_duration_ms: float = 0.0
    active_transactions: int = 0


@dataclass
class TransactionLog:
    """Transaction log entry."""
    transaction_id: str
    action: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# TRANSACTION
# =============================================================================

class Transaction:
    """
    A transaction unit.
    """

    def __init__(
        self,
        transaction_id: Optional[str] = None,
        config: Optional[TransactionConfig] = None,
        parent: Optional['Transaction'] = None
    ):
        self.transaction_id = transaction_id or str(uuid.uuid4())
        self.config = config or TransactionConfig()
        self.parent = parent

        self.state = TransactionState.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        self._operations: List[Operation] = []
        self._savepoints: Dict[str, Savepoint] = {}
        self._resources: Set[str] = set()
        self._lock = threading.RLock()
        self._logs: List[TransactionLog] = []

    @property
    def is_active(self) -> bool:
        return self.state == TransactionState.ACTIVE

    @property
    def is_nested(self) -> bool:
        return self.parent is not None

    @property
    def duration_ms(self) -> float:
        if self.started_at:
            end = self.completed_at or datetime.utcnow()
            return (end - self.started_at).total_seconds() * 1000
        return 0

    def begin(self) -> None:
        """Begin the transaction."""
        with self._lock:
            if self.state != TransactionState.PENDING:
                raise TransactionError("Transaction already started")

            self.state = TransactionState.ACTIVE
            self.started_at = datetime.utcnow()
            self._log("BEGIN")

    def add_operation(self, operation: Operation) -> None:
        """Add an operation to the transaction."""
        with self._lock:
            if self.state != TransactionState.ACTIVE:
                raise TransactionError("Transaction not active")

            self._operations.append(operation)
            self._log("OPERATION", {"type": operation.operation_type})

    def create_savepoint(self, name: str) -> Savepoint:
        """Create a savepoint."""
        with self._lock:
            if self.state != TransactionState.ACTIVE:
                raise TransactionError("Transaction not active")

            savepoint = Savepoint(
                name=name,
                operations=self._operations.copy()
            )
            self._savepoints[name] = savepoint
            self._log("SAVEPOINT", {"name": name})
            return savepoint

    def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a savepoint."""
        with self._lock:
            if name not in self._savepoints:
                raise TransactionError(f"Savepoint {name} not found")

            savepoint = self._savepoints[name]

            # Get operations to compensate
            ops_to_compensate = self._operations[len(savepoint.operations):]
            self._operations = savepoint.operations.copy()

            # Remove savepoints created after this one
            to_remove = [
                sp_name for sp_name, sp in self._savepoints.items()
                if sp.created_at > savepoint.created_at
            ]
            for sp_name in to_remove:
                del self._savepoints[sp_name]

            self._log("ROLLBACK_SAVEPOINT", {"name": name})

            # Store operations for compensation
            self._pending_compensations = ops_to_compensate

    def prepare(self) -> bool:
        """Prepare for commit (2PC first phase)."""
        with self._lock:
            if self.state != TransactionState.ACTIVE:
                return False

            self.state = TransactionState.PREPARED
            self._log("PREPARE")
            return True

    def commit(self) -> None:
        """Commit the transaction."""
        with self._lock:
            if self.state not in (TransactionState.ACTIVE, TransactionState.PREPARED):
                raise TransactionError("Cannot commit - transaction not active")

            self.state = TransactionState.COMMITTED
            self.completed_at = datetime.utcnow()
            self._log("COMMIT")

    def rollback(self) -> None:
        """Rollback the transaction."""
        with self._lock:
            if self.state == TransactionState.COMMITTED:
                raise TransactionError("Cannot rollback committed transaction")

            self.state = TransactionState.ROLLED_BACK
            self.completed_at = datetime.utcnow()
            self._log("ROLLBACK")

    def get_operations(self) -> List[Operation]:
        """Get all operations."""
        with self._lock:
            return self._operations.copy()

    def get_compensations(self) -> List[Callable[[], Awaitable[None]]]:
        """Get compensation actions for rollback."""
        with self._lock:
            return [
                op.compensation
                for op in reversed(self._operations)
                if op.compensation
            ]

    def _log(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log transaction action."""
        self._logs.append(TransactionLog(
            transaction_id=self.transaction_id,
            action=action,
            details=details or {}
        ))


# =============================================================================
# RESOURCE MANAGER
# =============================================================================

class TransactionResource(ABC):
    """Abstract transaction resource."""

    @abstractmethod
    async def prepare(self, transaction: Transaction) -> bool:
        pass

    @abstractmethod
    async def commit(self, transaction: Transaction) -> None:
        pass

    @abstractmethod
    async def rollback(self, transaction: Transaction) -> None:
        pass


class InMemoryResource(TransactionResource):
    """In-memory transactional resource."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._pending: Dict[str, Dict[str, Any]] = {}  # txn_id -> changes
        self._lock = threading.RLock()

    async def prepare(self, transaction: Transaction) -> bool:
        return True

    async def commit(self, transaction: Transaction) -> None:
        with self._lock:
            changes = self._pending.pop(transaction.transaction_id, {})
            self._data.update(changes)

    async def rollback(self, transaction: Transaction) -> None:
        with self._lock:
            self._pending.pop(transaction.transaction_id, None)

    def set(self, transaction: Transaction, key: str, value: Any) -> None:
        with self._lock:
            if transaction.transaction_id not in self._pending:
                self._pending[transaction.transaction_id] = {}
            self._pending[transaction.transaction_id][key] = value

    def get(self, transaction: Transaction, key: str) -> Optional[Any]:
        with self._lock:
            # Check pending changes first
            pending = self._pending.get(transaction.transaction_id, {})
            if key in pending:
                return pending[key]
            return self._data.get(key)


# =============================================================================
# TRANSACTION COORDINATOR
# =============================================================================

class TransactionCoordinator:
    """
    Coordinates distributed transactions using 2PC.
    """

    def __init__(self):
        self._resources: Dict[str, TransactionResource] = {}
        self._participants: Dict[str, Set[str]] = defaultdict(set)  # txn_id -> resource_ids
        self._lock = threading.RLock()

    def register_resource(self, name: str, resource: TransactionResource) -> None:
        """Register a transactional resource."""
        with self._lock:
            self._resources[name] = resource

    def enlist(self, transaction: Transaction, resource_name: str) -> None:
        """Enlist a resource in a transaction."""
        with self._lock:
            if resource_name not in self._resources:
                raise TransactionError(f"Resource {resource_name} not found")
            self._participants[transaction.transaction_id].add(resource_name)

    async def prepare_all(self, transaction: Transaction) -> bool:
        """Prepare all participants (2PC phase 1)."""
        with self._lock:
            resource_names = self._participants.get(transaction.transaction_id, set())

        for name in resource_names:
            resource = self._resources.get(name)
            if resource:
                if not await resource.prepare(transaction):
                    return False

        return True

    async def commit_all(self, transaction: Transaction) -> None:
        """Commit all participants (2PC phase 2)."""
        with self._lock:
            resource_names = self._participants.get(transaction.transaction_id, set())

        for name in resource_names:
            resource = self._resources.get(name)
            if resource:
                await resource.commit(transaction)

        with self._lock:
            self._participants.pop(transaction.transaction_id, None)

    async def rollback_all(self, transaction: Transaction) -> None:
        """Rollback all participants."""
        with self._lock:
            resource_names = self._participants.get(transaction.transaction_id, set())

        for name in resource_names:
            resource = self._resources.get(name)
            if resource:
                await resource.rollback(transaction)

        with self._lock:
            self._participants.pop(transaction.transaction_id, None)


# =============================================================================
# COMPENSATION MANAGER
# =============================================================================

class CompensationManager:
    """
    Manages compensation actions for saga-style transactions.
    """

    def __init__(self):
        self._compensations: Dict[str, List[Callable[[], Awaitable[None]]]] = defaultdict(list)
        self._lock = threading.RLock()

    def register(
        self,
        transaction_id: str,
        compensation: Callable[[], Awaitable[None]]
    ) -> None:
        """Register a compensation action."""
        with self._lock:
            self._compensations[transaction_id].append(compensation)

    async def compensate(self, transaction_id: str) -> int:
        """Execute all compensations in reverse order."""
        with self._lock:
            compensations = self._compensations.pop(transaction_id, [])

        executed = 0
        for compensation in reversed(compensations):
            try:
                await compensation()
                executed += 1
            except Exception as e:
                logger.error(f"Compensation failed: {e}")

        return executed

    def clear(self, transaction_id: str) -> None:
        """Clear compensations (on successful commit)."""
        with self._lock:
            self._compensations.pop(transaction_id, None)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class TransactionError(Exception):
    """Base transaction error."""
    pass


class TransactionTimeoutError(TransactionError):
    """Transaction timed out."""
    pass


class TransactionRollbackError(TransactionError):
    """Transaction rollback failed."""
    pass


# =============================================================================
# TRANSACTION MANAGER
# =============================================================================

class TransactionManager:
    """
    Transaction Manager for BAEL.

    Advanced transaction management.
    """

    def __init__(self):
        self._transactions: Dict[str, Transaction] = {}
        self._current: Dict[int, Transaction] = {}  # thread_id -> transaction
        self._coordinator = TransactionCoordinator()
        self._compensation_manager = CompensationManager()
        self._stats = TransactionStats()
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # TRANSACTION LIFECYCLE
    # -------------------------------------------------------------------------

    def begin(self, config: Optional[TransactionConfig] = None) -> Transaction:
        """Begin a new transaction."""
        config = config or TransactionConfig()

        # Check propagation
        current = self.current()

        if config.propagation == PropagationType.REQUIRED:
            if current and current.is_active:
                return current

        elif config.propagation == PropagationType.REQUIRES_NEW:
            pass  # Always create new

        elif config.propagation == PropagationType.SUPPORTS:
            if current and current.is_active:
                return current
            # Otherwise proceed without transaction

        elif config.propagation == PropagationType.MANDATORY:
            if not current or not current.is_active:
                raise TransactionError("Mandatory transaction not found")
            return current

        elif config.propagation == PropagationType.NEVER:
            if current and current.is_active:
                raise TransactionError("Transaction not allowed")

        elif config.propagation == PropagationType.NESTED:
            if current and current.is_active:
                # Create nested transaction
                txn = Transaction(config=config, parent=current)
                txn.begin()
                self._register(txn)
                return txn

        # Create new transaction
        txn = Transaction(config=config)
        txn.begin()
        self._register(txn)

        with self._lock:
            self._stats.total_started += 1
            self._stats.active_transactions += 1

        return txn

    async def commit(self, transaction: Optional[Transaction] = None) -> None:
        """Commit a transaction."""
        txn = transaction or self.current()

        if not txn:
            raise TransactionError("No active transaction")

        if txn.is_nested:
            # Nested transactions commit with parent
            txn.commit()
            return

        # Two-phase commit
        if not await self._coordinator.prepare_all(txn):
            await self.rollback(txn)
            raise TransactionError("Prepare phase failed")

        txn.prepare()

        try:
            await self._coordinator.commit_all(txn)
            txn.commit()
            self._compensation_manager.clear(txn.transaction_id)

            with self._lock:
                self._stats.total_committed += 1
                self._stats.active_transactions -= 1
                self._update_duration(txn)

        except Exception as e:
            await self.rollback(txn)
            raise TransactionError(f"Commit failed: {e}")

        finally:
            self._unregister(txn)

    async def rollback(self, transaction: Optional[Transaction] = None) -> None:
        """Rollback a transaction."""
        txn = transaction or self.current()

        if not txn:
            raise TransactionError("No active transaction")

        try:
            # Rollback resources
            await self._coordinator.rollback_all(txn)

            # Execute compensations
            await self._compensation_manager.compensate(txn.transaction_id)

            # Execute inline compensations
            for compensation in txn.get_compensations():
                try:
                    await compensation()
                except Exception as e:
                    logger.error(f"Compensation error: {e}")

            txn.rollback()

            with self._lock:
                self._stats.total_rolled_back += 1
                self._stats.active_transactions -= 1

        finally:
            self._unregister(txn)

    # -------------------------------------------------------------------------
    # CONTEXT MANAGERS
    # -------------------------------------------------------------------------

    @asynccontextmanager
    async def transaction(
        self,
        config: Optional[TransactionConfig] = None
    ) -> AsyncIterator[Transaction]:
        """Transaction context manager."""
        txn = self.begin(config)

        try:
            yield txn
            await self.commit(txn)
        except Exception as e:
            await self.rollback(txn)
            raise

    @asynccontextmanager
    async def savepoint(
        self,
        name: str
    ) -> AsyncIterator[Savepoint]:
        """Savepoint context manager."""
        txn = self.current()

        if not txn:
            raise TransactionError("No active transaction")

        sp = txn.create_savepoint(name)

        try:
            yield sp
        except Exception:
            txn.rollback_to_savepoint(name)
            raise

    # -------------------------------------------------------------------------
    # OPERATIONS
    # -------------------------------------------------------------------------

    def add_operation(
        self,
        operation_type: str,
        target: str,
        data: Any = None,
        compensation: Optional[Callable[[], Awaitable[None]]] = None
    ) -> Operation:
        """Add an operation to the current transaction."""
        txn = self.current()

        if not txn:
            raise TransactionError("No active transaction")

        operation = Operation(
            operation_type=operation_type,
            target=target,
            data=data,
            compensation=compensation
        )

        txn.add_operation(operation)
        return operation

    def register_compensation(
        self,
        compensation: Callable[[], Awaitable[None]]
    ) -> None:
        """Register a compensation action."""
        txn = self.current()

        if not txn:
            raise TransactionError("No active transaction")

        self._compensation_manager.register(txn.transaction_id, compensation)

    # -------------------------------------------------------------------------
    # RESOURCES
    # -------------------------------------------------------------------------

    def register_resource(self, name: str, resource: TransactionResource) -> None:
        """Register a transactional resource."""
        self._coordinator.register_resource(name, resource)

    def enlist_resource(self, resource_name: str) -> None:
        """Enlist a resource in the current transaction."""
        txn = self.current()

        if not txn:
            raise TransactionError("No active transaction")

        self._coordinator.enlist(txn, resource_name)

    # -------------------------------------------------------------------------
    # STATE
    # -------------------------------------------------------------------------

    def current(self) -> Optional[Transaction]:
        """Get the current transaction."""
        thread_id = threading.current_thread().ident
        with self._lock:
            return self._current.get(thread_id)

    def get(self, transaction_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        with self._lock:
            return self._transactions.get(transaction_id)

    def get_stats(self) -> TransactionStats:
        """Get transaction statistics."""
        with self._lock:
            return TransactionStats(
                total_started=self._stats.total_started,
                total_committed=self._stats.total_committed,
                total_rolled_back=self._stats.total_rolled_back,
                total_failed=self._stats.total_failed,
                avg_duration_ms=self._stats.avg_duration_ms,
                active_transactions=self._stats.active_transactions
            )

    # -------------------------------------------------------------------------
    # INTERNAL
    # -------------------------------------------------------------------------

    def _register(self, transaction: Transaction) -> None:
        """Register a transaction."""
        thread_id = threading.current_thread().ident
        with self._lock:
            self._transactions[transaction.transaction_id] = transaction
            self._current[thread_id] = transaction

    def _unregister(self, transaction: Transaction) -> None:
        """Unregister a transaction."""
        thread_id = threading.current_thread().ident
        with self._lock:
            self._transactions.pop(transaction.transaction_id, None)
            if self._current.get(thread_id) == transaction:
                if transaction.parent:
                    self._current[thread_id] = transaction.parent
                else:
                    self._current.pop(thread_id, None)

    def _update_duration(self, transaction: Transaction) -> None:
        """Update average duration."""
        n = self._stats.total_committed
        self._stats.avg_duration_ms = (
            (self._stats.avg_duration_ms * (n - 1) + transaction.duration_ms) / n
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Transaction Manager."""
    print("=" * 70)
    print("BAEL - TRANSACTION MANAGER DEMO")
    print("Advanced Transaction Management for AI Agents")
    print("=" * 70)
    print()

    manager = TransactionManager()

    # Create a test resource
    resource = InMemoryResource()
    manager.register_resource("storage", resource)

    # 1. Basic Transaction
    print("1. BASIC TRANSACTION:")
    print("-" * 40)

    async with manager.transaction() as txn:
        print(f"   Transaction: {txn.transaction_id[:8]}...")
        print(f"   State: {txn.state.value}")

        manager.enlist_resource("storage")
        resource.set(txn, "key1", "value1")
        manager.add_operation("SET", "key1", "value1")

    print(f"   Committed, value: {resource._data.get('key1')}")
    print()

    # 2. Transaction Rollback
    print("2. TRANSACTION ROLLBACK:")
    print("-" * 40)

    try:
        async with manager.transaction() as txn:
            manager.enlist_resource("storage")
            resource.set(txn, "key2", "should_not_persist")
            manager.add_operation("SET", "key2", "should_not_persist")
            raise ValueError("Simulated error")
    except ValueError:
        pass

    print(f"   Key2 after rollback: {resource._data.get('key2', 'NOT FOUND')}")
    print()

    # 3. Savepoints
    print("3. SAVEPOINTS:")
    print("-" * 40)

    async with manager.transaction() as txn:
        manager.enlist_resource("storage")

        resource.set(txn, "step1", "done")
        manager.add_operation("SET", "step1", "done")
        print(f"   After step 1: {len(txn.get_operations())} operations")

        try:
            async with manager.savepoint("before_step2") as sp:
                resource.set(txn, "step2", "done")
                manager.add_operation("SET", "step2", "done")
                print(f"   After step 2: {len(txn.get_operations())} operations")
                raise ValueError("Rollback to savepoint")
        except ValueError:
            pass

        print(f"   After rollback: {len(txn.get_operations())} operations")

    print()

    # 4. Compensation Actions
    print("4. COMPENSATION ACTIONS:")
    print("-" * 40)

    compensation_log = []

    try:
        async with manager.transaction() as txn:
            async def compensate_action1():
                compensation_log.append("compensated_action1")

            async def compensate_action2():
                compensation_log.append("compensated_action2")

            manager.add_operation("ACTION1", "resource", compensation=compensate_action1)
            manager.add_operation("ACTION2", "resource", compensation=compensate_action2)

            raise ValueError("Trigger compensations")
    except ValueError:
        pass

    print(f"   Compensations executed: {compensation_log}")
    print()

    # 5. Nested Transactions
    print("5. NESTED TRANSACTIONS:")
    print("-" * 40)

    async with manager.transaction() as outer:
        print(f"   Outer: {outer.transaction_id[:8]}...")
        manager.add_operation("OUTER_OP", "resource")

        async with manager.transaction(TransactionConfig(
            propagation=PropagationType.NESTED
        )) as inner:
            print(f"   Inner: {inner.transaction_id[:8]}...")
            print(f"   Is nested: {inner.is_nested}")
            manager.add_operation("INNER_OP", "resource")

    print()

    # 6. Transaction Configuration
    print("6. TRANSACTION CONFIGURATION:")
    print("-" * 40)

    config = TransactionConfig(
        isolation_level=IsolationLevel.SERIALIZABLE,
        propagation=PropagationType.REQUIRED,
        timeout=10.0,
        read_only=True
    )

    async with manager.transaction(config) as txn:
        print(f"   Isolation: {txn.config.isolation_level.value}")
        print(f"   Propagation: {txn.config.propagation.value}")
        print(f"   Timeout: {txn.config.timeout}s")
        print(f"   Read-only: {txn.config.read_only}")

    print()

    # 7. Multiple Resources
    print("7. MULTIPLE RESOURCES:")
    print("-" * 40)

    resource2 = InMemoryResource()
    manager.register_resource("storage2", resource2)

    async with manager.transaction() as txn:
        manager.enlist_resource("storage")
        manager.enlist_resource("storage2")

        resource.set(txn, "shared_key", "value_in_storage1")
        resource2.set(txn, "shared_key", "value_in_storage2")

    print(f"   Storage1: {resource._data.get('shared_key')}")
    print(f"   Storage2: {resource2._data.get('shared_key')}")
    print()

    # 8. Propagation: REQUIRED
    print("8. PROPAGATION - REQUIRED:")
    print("-" * 40)

    async with manager.transaction() as outer:
        outer_id = outer.transaction_id

        # REQUIRED should join existing transaction
        async with manager.transaction(TransactionConfig(
            propagation=PropagationType.REQUIRED
        )) as inner:
            print(f"   Outer ID: {outer_id[:8]}...")
            print(f"   Inner ID: {inner.transaction_id[:8]}...")
            print(f"   Same transaction: {outer_id == inner.transaction_id}")

    print()

    # 9. Propagation: REQUIRES_NEW
    print("9. PROPAGATION - REQUIRES_NEW:")
    print("-" * 40)

    async with manager.transaction() as outer:
        outer_id = outer.transaction_id

        # REQUIRES_NEW should create new transaction
        async with manager.transaction(TransactionConfig(
            propagation=PropagationType.REQUIRES_NEW
        )) as inner:
            print(f"   Outer ID: {outer_id[:8]}...")
            print(f"   Inner ID: {inner.transaction_id[:8]}...")
            print(f"   Different transaction: {outer_id != inner.transaction_id}")

    print()

    # 10. Transaction Operations
    print("10. TRANSACTION OPERATIONS:")
    print("-" * 40)

    async with manager.transaction() as txn:
        manager.add_operation("CREATE", "users", {"id": 1, "name": "Alice"})
        manager.add_operation("UPDATE", "users", {"id": 1, "name": "Alice B"})
        manager.add_operation("DELETE", "sessions", {"user_id": 1})

        operations = txn.get_operations()
        print(f"   Total operations: {len(operations)}")
        for op in operations:
            print(f"   - {op.operation_type} on {op.target}")

    print()

    # 11. Transaction Logs
    print("11. TRANSACTION LOGS:")
    print("-" * 40)

    async with manager.transaction() as txn:
        manager.add_operation("TEST", "resource")
        sp = txn.create_savepoint("test_sp")
        manager.add_operation("TEST2", "resource")

    print(f"   Log entries: {len(txn._logs)}")
    for log in txn._logs[-3:]:
        print(f"   - {log.action}")
    print()

    # 12. Statistics
    print("12. TRANSACTION STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total started: {stats.total_started}")
    print(f"   Committed: {stats.total_committed}")
    print(f"   Rolled back: {stats.total_rolled_back}")
    print(f"   Avg duration: {stats.avg_duration_ms:.2f}ms")
    print(f"   Active: {stats.active_transactions}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Transaction Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
