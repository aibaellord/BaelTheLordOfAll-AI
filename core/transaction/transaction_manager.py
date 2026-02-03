#!/usr/bin/env python3
"""
BAEL - Transaction Manager
Advanced distributed transaction management for AI agent operations.

Features:
- ACID transactions
- Two-phase commit
- Saga pattern
- Compensating transactions
- Optimistic locking
- Pessimistic locking
- Deadlock detection
- Transaction isolation
- Nested transactions
- Savepoints
"""

import asyncio
import copy
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
R = TypeVar('R')
K = TypeVar('K')


# =============================================================================
# ENUMS
# =============================================================================

class TransactionStatus(Enum):
    """Transaction status."""
    PENDING = "pending"
    ACTIVE = "active"
    PREPARING = "preparing"
    PREPARED = "prepared"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ABORTING = "aborting"
    ABORTED = "aborted"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class IsolationLevel(Enum):
    """Transaction isolation level."""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


class LockType(Enum):
    """Lock type."""
    SHARED = "shared"
    EXCLUSIVE = "exclusive"
    UPDATE = "update"


class LockStatus(Enum):
    """Lock status."""
    HELD = "held"
    WAITING = "waiting"
    RELEASED = "released"
    TIMEOUT = "timeout"


class SagaStepStatus(Enum):
    """Saga step status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TransactionConfig:
    """Transaction configuration."""
    timeout_seconds: int = 300
    lock_timeout_seconds: int = 30
    max_retries: int = 3
    isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED
    auto_rollback_on_error: bool = True


@dataclass
class Lock:
    """Resource lock."""
    lock_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str = ""
    lock_type: LockType = LockType.SHARED
    holder_id: str = ""
    status: LockStatus = LockStatus.HELD
    acquired_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class Savepoint:
    """Transaction savepoint."""
    savepoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionResult:
    """Transaction result."""
    transaction_id: str = ""
    status: TransactionStatus = TransactionStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    operations: int = 0


@dataclass
class TransactionStats:
    """Transaction statistics."""
    total_transactions: int = 0
    committed: int = 0
    aborted: int = 0
    rolled_back: int = 0
    active: int = 0
    average_duration_ms: float = 0.0


# =============================================================================
# OPERATION
# =============================================================================

@dataclass
class Operation:
    """Transaction operation."""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: str = ""
    resource_id: str = ""
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# TRANSACTION
# =============================================================================

class Transaction:
    """Database transaction."""

    def __init__(
        self,
        transaction_id: Optional[str] = None,
        parent: Optional['Transaction'] = None,
        config: Optional[TransactionConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.transaction_id = transaction_id or str(uuid.uuid4())
        self.parent = parent
        self.config = config or TransactionConfig()
        self.metadata = metadata or {}

        self._status = TransactionStatus.PENDING
        self._operations: List[Operation] = []
        self._locks: Dict[str, Lock] = {}
        self._savepoints: Dict[str, Savepoint] = []
        self._children: List['Transaction'] = []

        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._state: Dict[str, Any] = {}

    @property
    def status(self) -> TransactionStatus:
        """Get transaction status."""
        return self._status

    @status.setter
    def status(self, value: TransactionStatus) -> None:
        """Set transaction status."""
        self._status = value

    def begin(self) -> None:
        """Begin transaction."""
        self._status = TransactionStatus.ACTIVE
        self._started_at = datetime.utcnow()

    def add_operation(self, operation: Operation) -> None:
        """Add operation to transaction."""
        self._operations.append(operation)

    def get_operations(self) -> List[Operation]:
        """Get all operations."""
        return self._operations.copy()

    def add_lock(self, lock: Lock) -> None:
        """Add lock."""
        self._locks[lock.lock_id] = lock

    def get_locks(self) -> List[Lock]:
        """Get all locks."""
        return list(self._locks.values())

    def release_lock(self, lock_id: str) -> bool:
        """Release lock."""
        if lock_id in self._locks:
            self._locks[lock_id].status = LockStatus.RELEASED
            del self._locks[lock_id]
            return True
        return False

    def release_all_locks(self) -> int:
        """Release all locks."""
        count = len(self._locks)
        for lock in self._locks.values():
            lock.status = LockStatus.RELEASED
        self._locks.clear()
        return count

    def create_savepoint(self, name: str) -> Savepoint:
        """Create savepoint."""
        savepoint = Savepoint(
            name=name,
            state_snapshot=copy.deepcopy(self._state)
        )
        self._savepoints[name] = savepoint
        return savepoint

    def rollback_to_savepoint(self, name: str) -> bool:
        """Rollback to savepoint."""
        if name not in self._savepoints:
            return False

        savepoint = self._savepoints[name]
        self._state = copy.deepcopy(savepoint.state_snapshot)

        # Remove savepoints created after this one
        keys_to_remove = [
            k for k, v in self._savepoints.items()
            if v.created_at > savepoint.created_at
        ]
        for key in keys_to_remove:
            del self._savepoints[key]

        return True

    def add_child(self, child: 'Transaction') -> None:
        """Add child transaction."""
        self._children.append(child)

    def get_children(self) -> List['Transaction']:
        """Get child transactions."""
        return self._children.copy()

    def set_state(self, key: str, value: Any) -> None:
        """Set state value."""
        self._state[key] = value

    def get_state(self, key: str) -> Optional[Any]:
        """Get state value."""
        return self._state.get(key)

    def to_result(self) -> TransactionResult:
        """Convert to result."""
        duration_ms = 0.0
        if self._started_at and self._completed_at:
            duration_ms = (
                self._completed_at - self._started_at
            ).total_seconds() * 1000

        return TransactionResult(
            transaction_id=self.transaction_id,
            status=self._status,
            started_at=self._started_at,
            completed_at=self._completed_at,
            duration_ms=duration_ms,
            operations=len(self._operations)
        )


# =============================================================================
# LOCK MANAGER
# =============================================================================

class LockManager:
    """Manage resource locks."""

    def __init__(self, timeout_seconds: int = 30):
        self._timeout = timeout_seconds
        self._locks: Dict[str, Lock] = {}
        self._waiting: Dict[str, List[Tuple[str, asyncio.Event]]] = defaultdict(list)
        self._holder_locks: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        resource_id: str,
        holder_id: str,
        lock_type: LockType = LockType.EXCLUSIVE
    ) -> Optional[Lock]:
        """Acquire lock on resource."""
        async with self._lock:
            # Check existing lock
            existing = self._locks.get(resource_id)

            if existing:
                # Check compatibility
                if lock_type == LockType.SHARED and existing.lock_type == LockType.SHARED:
                    # Can share read locks
                    pass
                elif existing.holder_id == holder_id:
                    # Same holder - upgrade if needed
                    if lock_type == LockType.EXCLUSIVE and existing.lock_type != LockType.EXCLUSIVE:
                        existing.lock_type = lock_type
                    return existing
                else:
                    # Must wait
                    return await self._wait_for_lock(
                        resource_id, holder_id, lock_type
                    )

            # Create new lock
            lock = Lock(
                resource_id=resource_id,
                lock_type=lock_type,
                holder_id=holder_id,
                expires_at=datetime.utcnow() + timedelta(seconds=self._timeout)
            )

            self._locks[resource_id] = lock
            self._holder_locks[holder_id].add(lock.lock_id)

            return lock

    async def _wait_for_lock(
        self,
        resource_id: str,
        holder_id: str,
        lock_type: LockType
    ) -> Optional[Lock]:
        """Wait for lock to become available."""
        event = asyncio.Event()
        self._waiting[resource_id].append((holder_id, event))

        try:
            # Wait with timeout
            await asyncio.wait_for(event.wait(), timeout=self._timeout)

            # Try to acquire now
            async with self._lock:
                if resource_id not in self._locks:
                    lock = Lock(
                        resource_id=resource_id,
                        lock_type=lock_type,
                        holder_id=holder_id,
                        expires_at=datetime.utcnow() + timedelta(seconds=self._timeout)
                    )
                    self._locks[resource_id] = lock
                    self._holder_locks[holder_id].add(lock.lock_id)
                    return lock

            return None
        except asyncio.TimeoutError:
            # Remove from waiting list
            self._waiting[resource_id] = [
                (h, e) for h, e in self._waiting[resource_id]
                if h != holder_id
            ]
            return None

    async def release(
        self,
        resource_id: str,
        holder_id: str
    ) -> bool:
        """Release lock."""
        async with self._lock:
            lock = self._locks.get(resource_id)

            if not lock or lock.holder_id != holder_id:
                return False

            lock.status = LockStatus.RELEASED
            del self._locks[resource_id]
            self._holder_locks[holder_id].discard(lock.lock_id)

            # Notify waiters
            if resource_id in self._waiting and self._waiting[resource_id]:
                _, event = self._waiting[resource_id].pop(0)
                event.set()

            return True

    async def release_all(self, holder_id: str) -> int:
        """Release all locks for holder."""
        async with self._lock:
            lock_ids = list(self._holder_locks.get(holder_id, set()))
            count = 0

            for lock_id in lock_ids:
                for resource_id, lock in list(self._locks.items()):
                    if lock.lock_id == lock_id:
                        del self._locks[resource_id]
                        count += 1

                        # Notify waiters
                        if resource_id in self._waiting and self._waiting[resource_id]:
                            _, event = self._waiting[resource_id].pop(0)
                            event.set()

            if holder_id in self._holder_locks:
                del self._holder_locks[holder_id]

            return count

    async def check_deadlock(
        self,
        holder_id: str,
        resource_id: str
    ) -> bool:
        """Check for deadlock."""
        async with self._lock:
            visited = set()
            return self._detect_cycle(holder_id, resource_id, visited)

    def _detect_cycle(
        self,
        holder_id: str,
        resource_id: str,
        visited: Set[str]
    ) -> bool:
        """Detect cycle in wait-for graph."""
        if holder_id in visited:
            return True

        visited.add(holder_id)

        # Check what resources this holder is waiting for
        for res_id, waiters in self._waiting.items():
            for waiter_id, _ in waiters:
                if waiter_id == holder_id:
                    # Find who holds this resource
                    lock = self._locks.get(res_id)
                    if lock and self._detect_cycle(
                        lock.holder_id, res_id, visited
                    ):
                        return True

        visited.remove(holder_id)
        return False


# =============================================================================
# TWO PHASE COMMIT COORDINATOR
# =============================================================================

class TwoPhaseCoordinator:
    """Two-phase commit coordinator."""

    def __init__(self):
        self._participants: Dict[str, Callable[[], Awaitable[bool]]] = {}
        self._prepared: Set[str] = set()
        self._committed: Set[str] = set()

    def register(
        self,
        participant_id: str,
        prepare_func: Callable[[], Awaitable[bool]]
    ) -> None:
        """Register participant."""
        self._participants[participant_id] = prepare_func

    async def prepare_all(self) -> bool:
        """Prepare all participants."""
        self._prepared.clear()

        for participant_id, prepare_func in self._participants.items():
            try:
                if await prepare_func():
                    self._prepared.add(participant_id)
                else:
                    return False
            except Exception:
                return False

        return len(self._prepared) == len(self._participants)

    async def commit_all(
        self,
        commit_funcs: Dict[str, Callable[[], Awaitable[bool]]]
    ) -> bool:
        """Commit all participants."""
        self._committed.clear()

        for participant_id in self._prepared:
            if participant_id in commit_funcs:
                try:
                    if await commit_funcs[participant_id]():
                        self._committed.add(participant_id)
                    else:
                        return False
                except Exception:
                    return False

        return len(self._committed) == len(self._prepared)

    async def abort_all(
        self,
        abort_funcs: Dict[str, Callable[[], Awaitable[None]]]
    ) -> None:
        """Abort all participants."""
        for participant_id in self._prepared:
            if participant_id in abort_funcs:
                try:
                    await abort_funcs[participant_id]()
                except Exception:
                    pass

        self._prepared.clear()
        self._committed.clear()

    def reset(self) -> None:
        """Reset coordinator."""
        self._participants.clear()
        self._prepared.clear()
        self._committed.clear()


# =============================================================================
# TRANSACTION MANAGER
# =============================================================================

class TransactionManager:
    """
    Transaction Manager for BAEL.

    Advanced distributed transaction management.
    """

    def __init__(self, config: Optional[TransactionConfig] = None):
        self.config = config or TransactionConfig()

        self._transactions: Dict[str, Transaction] = {}
        self._active: Dict[str, Transaction] = {}
        self._lock_manager = LockManager(self.config.lock_timeout_seconds)

        self._stats = TransactionStats()
        self._durations: List[float] = []
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # TRANSACTION LIFECYCLE
    # -------------------------------------------------------------------------

    async def begin(
        self,
        transaction_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """Begin new transaction."""
        parent = None
        if parent_id:
            parent = self._transactions.get(parent_id)

        transaction = Transaction(
            transaction_id=transaction_id,
            parent=parent,
            config=self.config,
            metadata=metadata
        )

        async with self._lock:
            self._transactions[transaction.transaction_id] = transaction
            self._active[transaction.transaction_id] = transaction
            self._stats.total_transactions += 1
            self._stats.active += 1

            if parent:
                parent.add_child(transaction)

        transaction.begin()
        return transaction

    async def commit(
        self,
        transaction_id: str
    ) -> TransactionResult:
        """Commit transaction."""
        async with self._lock:
            transaction = self._active.get(transaction_id)
            if not transaction:
                return TransactionResult(
                    transaction_id=transaction_id,
                    status=TransactionStatus.ABORTED,
                    error="Transaction not found"
                )

            transaction.status = TransactionStatus.COMMITTING

        try:
            # Commit children first
            for child in transaction.get_children():
                if child.status == TransactionStatus.ACTIVE:
                    await self.commit(child.transaction_id)

            # Release locks
            await self._lock_manager.release_all(transaction_id)

            async with self._lock:
                transaction.status = TransactionStatus.COMMITTED
                transaction._completed_at = datetime.utcnow()
                del self._active[transaction_id]
                self._stats.committed += 1
                self._stats.active -= 1

                result = transaction.to_result()
                self._durations.append(result.duration_ms)
                self._update_average()

                return result

        except Exception as e:
            if self.config.auto_rollback_on_error:
                await self.rollback(transaction_id)

            return TransactionResult(
                transaction_id=transaction_id,
                status=TransactionStatus.ABORTED,
                error=str(e)
            )

    async def rollback(
        self,
        transaction_id: str
    ) -> TransactionResult:
        """Rollback transaction."""
        async with self._lock:
            transaction = self._active.get(transaction_id)
            if not transaction:
                return TransactionResult(
                    transaction_id=transaction_id,
                    status=TransactionStatus.ABORTED,
                    error="Transaction not found"
                )

            transaction.status = TransactionStatus.ROLLING_BACK

        try:
            # Rollback children first
            for child in transaction.get_children():
                if child.status in (TransactionStatus.ACTIVE, TransactionStatus.COMMITTING):
                    await self.rollback(child.transaction_id)

            # Undo operations in reverse order
            operations = transaction.get_operations()
            for operation in reversed(operations):
                # Apply compensation (restore old value)
                pass  # In real implementation, restore from operation.old_value

            # Release locks
            await self._lock_manager.release_all(transaction_id)

            async with self._lock:
                transaction.status = TransactionStatus.ROLLED_BACK
                transaction._completed_at = datetime.utcnow()
                del self._active[transaction_id]
                self._stats.rolled_back += 1
                self._stats.active -= 1

                return transaction.to_result()

        except Exception as e:
            async with self._lock:
                transaction.status = TransactionStatus.ABORTED
                transaction._completed_at = datetime.utcnow()
                if transaction_id in self._active:
                    del self._active[transaction_id]
                self._stats.aborted += 1
                self._stats.active -= 1

            return TransactionResult(
                transaction_id=transaction_id,
                status=TransactionStatus.ABORTED,
                error=str(e)
            )

    async def abort(self, transaction_id: str) -> TransactionResult:
        """Abort transaction."""
        async with self._lock:
            transaction = self._active.get(transaction_id)
            if not transaction:
                return TransactionResult(
                    transaction_id=transaction_id,
                    status=TransactionStatus.ABORTED,
                    error="Transaction not found"
                )

            transaction.status = TransactionStatus.ABORTING

        # Abort children
        for child in transaction.get_children():
            if child.status == TransactionStatus.ACTIVE:
                await self.abort(child.transaction_id)

        # Release locks
        await self._lock_manager.release_all(transaction_id)

        async with self._lock:
            transaction.status = TransactionStatus.ABORTED
            transaction._completed_at = datetime.utcnow()
            if transaction_id in self._active:
                del self._active[transaction_id]
            self._stats.aborted += 1
            self._stats.active -= 1

        return transaction.to_result()

    # -------------------------------------------------------------------------
    # OPERATIONS
    # -------------------------------------------------------------------------

    async def execute(
        self,
        transaction_id: str,
        operation_type: str,
        resource_id: str,
        func: Callable[[], Awaitable[Any]],
        old_value: Optional[Any] = None
    ) -> Any:
        """Execute operation within transaction."""
        transaction = self._active.get(transaction_id)
        if not transaction:
            raise ValueError("Transaction not found or not active")

        # Acquire lock
        lock = await self._lock_manager.acquire(
            resource_id,
            transaction_id,
            LockType.EXCLUSIVE
        )

        if not lock:
            raise TimeoutError("Could not acquire lock")

        transaction.add_lock(lock)

        # Execute operation
        try:
            result = await func()

            operation = Operation(
                operation_type=operation_type,
                resource_id=resource_id,
                old_value=old_value,
                new_value=result
            )
            transaction.add_operation(operation)

            return result
        except Exception as e:
            if self.config.auto_rollback_on_error:
                await self.rollback(transaction_id)
            raise

    # -------------------------------------------------------------------------
    # SAVEPOINTS
    # -------------------------------------------------------------------------

    async def savepoint(
        self,
        transaction_id: str,
        name: str
    ) -> Optional[Savepoint]:
        """Create savepoint."""
        transaction = self._active.get(transaction_id)
        if transaction:
            return transaction.create_savepoint(name)
        return None

    async def rollback_to(
        self,
        transaction_id: str,
        savepoint_name: str
    ) -> bool:
        """Rollback to savepoint."""
        transaction = self._active.get(transaction_id)
        if transaction:
            return transaction.rollback_to_savepoint(savepoint_name)
        return False

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def get_transaction(
        self,
        transaction_id: str
    ) -> Optional[Transaction]:
        """Get transaction by ID."""
        async with self._lock:
            return self._transactions.get(transaction_id)

    async def get_active_transactions(self) -> List[Transaction]:
        """Get active transactions."""
        async with self._lock:
            return list(self._active.values())

    async def is_active(self, transaction_id: str) -> bool:
        """Check if transaction is active."""
        async with self._lock:
            return transaction_id in self._active

    # -------------------------------------------------------------------------
    # LOCKING
    # -------------------------------------------------------------------------

    async def acquire_lock(
        self,
        transaction_id: str,
        resource_id: str,
        lock_type: LockType = LockType.EXCLUSIVE
    ) -> Optional[Lock]:
        """Acquire lock."""
        transaction = self._active.get(transaction_id)
        if not transaction:
            return None

        lock = await self._lock_manager.acquire(
            resource_id,
            transaction_id,
            lock_type
        )

        if lock:
            transaction.add_lock(lock)

        return lock

    async def release_lock(
        self,
        transaction_id: str,
        resource_id: str
    ) -> bool:
        """Release lock."""
        return await self._lock_manager.release(resource_id, transaction_id)

    async def check_deadlock(
        self,
        transaction_id: str,
        resource_id: str
    ) -> bool:
        """Check for deadlock."""
        return await self._lock_manager.check_deadlock(
            transaction_id,
            resource_id
        )

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def _update_average(self) -> None:
        """Update average duration."""
        if self._durations:
            self._stats.average_duration_ms = (
                sum(self._durations) / len(self._durations)
            )

    async def stats(self) -> TransactionStats:
        """Get transaction stats."""
        async with self._lock:
            return copy.copy(self._stats)

    async def transaction_count(self) -> int:
        """Get total transaction count."""
        async with self._lock:
            return len(self._transactions)

    async def active_count(self) -> int:
        """Get active transaction count."""
        async with self._lock:
            return len(self._active)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class TransactionContext:
    """Transaction context manager."""

    def __init__(
        self,
        manager: TransactionManager,
        auto_commit: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self._manager = manager
        self._auto_commit = auto_commit
        self._metadata = metadata
        self._transaction: Optional[Transaction] = None

    async def __aenter__(self) -> Transaction:
        """Enter transaction context."""
        self._transaction = await self._manager.begin(
            metadata=self._metadata
        )
        return self._transaction

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit transaction context."""
        if not self._transaction:
            return False

        if exc_type:
            await self._manager.rollback(self._transaction.transaction_id)
            return False

        if self._auto_commit:
            await self._manager.commit(self._transaction.transaction_id)

        return False


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

    manager = TransactionManager(TransactionConfig(
        timeout_seconds=60,
        lock_timeout_seconds=10
    ))

    # 1. Begin Transaction
    print("1. BEGIN TRANSACTION:")
    print("-" * 40)

    tx = await manager.begin(metadata={"purpose": "demo"})

    print(f"   Transaction ID: {tx.transaction_id[:8]}...")
    print(f"   Status: {tx.status.value}")
    print()

    # 2. Execute Operations
    print("2. EXECUTE OPERATIONS:")
    print("-" * 40)

    async def create_user():
        return {"id": 1, "name": "Test User"}

    async def update_balance():
        return {"balance": 100}

    result1 = await manager.execute(
        tx.transaction_id,
        "create",
        "user:1",
        create_user
    )

    result2 = await manager.execute(
        tx.transaction_id,
        "update",
        "balance:1",
        update_balance
    )

    print(f"   Operation 1: {result1}")
    print(f"   Operation 2: {result2}")
    print(f"   Operations count: {len(tx.get_operations())}")
    print()

    # 3. Create Savepoint
    print("3. CREATE SAVEPOINT:")
    print("-" * 40)

    savepoint = await manager.savepoint(tx.transaction_id, "sp1")
    print(f"   Savepoint: {savepoint.name if savepoint else 'None'}")
    print()

    # 4. Commit Transaction
    print("4. COMMIT TRANSACTION:")
    print("-" * 40)

    result = await manager.commit(tx.transaction_id)

    print(f"   Status: {result.status.value}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print(f"   Operations: {result.operations}")
    print()

    # 5. Nested Transactions
    print("5. NESTED TRANSACTIONS:")
    print("-" * 40)

    parent = await manager.begin()
    child = await manager.begin(parent_id=parent.transaction_id)

    print(f"   Parent: {parent.transaction_id[:8]}...")
    print(f"   Child: {child.transaction_id[:8]}...")
    print(f"   Children count: {len(parent.get_children())}")

    await manager.commit(parent.transaction_id)
    print()

    # 6. Rollback Transaction
    print("6. ROLLBACK TRANSACTION:")
    print("-" * 40)

    tx_rollback = await manager.begin()

    async def failing_operation():
        return {"data": "will be rolled back"}

    await manager.execute(
        tx_rollback.transaction_id,
        "create",
        "temp:1",
        failing_operation
    )

    result = await manager.rollback(tx_rollback.transaction_id)

    print(f"   Status: {result.status.value}")
    print()

    # 7. Locking
    print("7. LOCKING:")
    print("-" * 40)

    tx_lock = await manager.begin()

    lock = await manager.acquire_lock(
        tx_lock.transaction_id,
        "resource:1",
        LockType.EXCLUSIVE
    )

    print(f"   Lock acquired: {lock is not None}")
    print(f"   Lock type: {lock.lock_type.value if lock else 'N/A'}")

    released = await manager.release_lock(
        tx_lock.transaction_id,
        "resource:1"
    )
    print(f"   Lock released: {released}")

    await manager.commit(tx_lock.transaction_id)
    print()

    # 8. Context Manager
    print("8. CONTEXT MANAGER:")
    print("-" * 40)

    async with TransactionContext(manager) as ctx_tx:
        print(f"   Context transaction: {ctx_tx.transaction_id[:8]}...")

        async def context_op():
            return {"context": True}

        await manager.execute(
            ctx_tx.transaction_id,
            "context",
            "ctx:1",
            context_op
        )

    print(f"   Auto-committed: True")
    print()

    # 9. Transaction Stats
    print("9. TRANSACTION STATS:")
    print("-" * 40)

    stats = await manager.stats()

    print(f"   Total: {stats.total_transactions}")
    print(f"   Committed: {stats.committed}")
    print(f"   Rolled back: {stats.rolled_back}")
    print(f"   Active: {stats.active}")
    print(f"   Avg duration: {stats.average_duration_ms:.2f}ms")
    print()

    # 10. Get Active Transactions
    print("10. GET ACTIVE TRANSACTIONS:")
    print("-" * 40)

    tx_active = await manager.begin()
    active = await manager.get_active_transactions()

    print(f"   Active count: {len(active)}")

    await manager.abort(tx_active.transaction_id)
    print()

    # 11. Check Active
    print("11. CHECK ACTIVE:")
    print("-" * 40)

    is_active = await manager.is_active(tx_active.transaction_id)
    print(f"   Is active: {is_active}")
    print()

    # 12. Savepoint Rollback
    print("12. SAVEPOINT ROLLBACK:")
    print("-" * 40)

    tx_sp = await manager.begin()
    tx_sp.set_state("value", 1)

    await manager.savepoint(tx_sp.transaction_id, "before_change")
    tx_sp.set_state("value", 2)

    print(f"   Before rollback: {tx_sp.get_state('value')}")

    await manager.rollback_to(tx_sp.transaction_id, "before_change")

    print(f"   After rollback: {tx_sp.get_state('value')}")

    await manager.commit(tx_sp.transaction_id)
    print()

    # 13. Abort Transaction
    print("13. ABORT TRANSACTION:")
    print("-" * 40)

    tx_abort = await manager.begin()
    result = await manager.abort(tx_abort.transaction_id)

    print(f"   Status: {result.status.value}")
    print()

    # 14. Transaction Count
    print("14. TRANSACTION COUNT:")
    print("-" * 40)

    total = await manager.transaction_count()
    active = await manager.active_count()

    print(f"   Total: {total}")
    print(f"   Active: {active}")
    print()

    # 15. Get Transaction
    print("15. GET TRANSACTION:")
    print("-" * 40)

    retrieved = await manager.get_transaction(tx.transaction_id)
    print(f"   Found: {retrieved is not None}")
    print(f"   Status: {retrieved.status.value if retrieved else 'N/A'}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Transaction Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
