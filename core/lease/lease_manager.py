#!/usr/bin/env python3
"""
BAEL - Lease Manager
Advanced distributed lease management for AI agent operations.

Features:
- Distributed locking
- Lease acquisition
- Lease renewal
- Lease expiration
- Fencing tokens
- Leader election
- Resource ownership
- Lease callbacks
- Deadlock detection
- Lock ordering
"""

import asyncio
import hashlib
import heapq
import random
import threading
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
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class LeaseState(Enum):
    """Lease state."""
    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"
    PENDING = "pending"


class LockType(Enum):
    """Lock types."""
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    READ = "read"
    WRITE = "write"


class AcquireResult(Enum):
    """Acquire result."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    DENIED = "denied"
    ERROR = "error"


class LeaderState(Enum):
    """Leader state."""
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LeaseConfig:
    """Lease configuration."""
    default_ttl_seconds: int = 30
    renewal_interval_seconds: int = 10
    max_renewals: int = 100
    enable_fencing: bool = True
    deadlock_detection: bool = True


@dataclass
class Lease:
    """Lease definition."""
    lease_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str = ""
    holder_id: str = ""
    lock_type: LockType = LockType.EXCLUSIVE
    state: LeaseState = LeaseState.PENDING
    ttl_seconds: int = 30
    fencing_token: int = 0
    renewals: int = 0
    acquired_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LockRequest:
    """Lock request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str = ""
    requester_id: str = ""
    lock_type: LockType = LockType.EXCLUSIVE
    timeout_seconds: float = 30.0
    priority: int = 0
    requested_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LeaderInfo:
    """Leader information."""
    leader_id: str = ""
    term: int = 0
    state: LeaderState = LeaderState.FOLLOWER
    elected_at: Optional[datetime] = None
    lease_id: Optional[str] = None


@dataclass
class WaitInfo:
    """Wait graph node for deadlock detection."""
    holder_id: str = ""
    waiting_for: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)


@dataclass
class LeaseStats:
    """Lease statistics."""
    total_leases: int = 0
    active_leases: int = 0
    expired_leases: int = 0
    acquisitions: int = 0
    renewals: int = 0
    releases: int = 0
    timeouts: int = 0
    deadlocks_detected: int = 0


# =============================================================================
# FENCING TOKEN GENERATOR
# =============================================================================

class FencingTokenGenerator:
    """Generates monotonically increasing fencing tokens."""

    def __init__(self):
        self._counter = 0
        self._lock = threading.Lock()

    def next(self) -> int:
        """Get next fencing token."""
        with self._lock:
            self._counter += 1
            return self._counter

    def current(self) -> int:
        """Get current token value."""
        with self._lock:
            return self._counter


# =============================================================================
# LEASE STORE
# =============================================================================

class LeaseStore:
    """In-memory lease store."""

    def __init__(self):
        self._leases: Dict[str, Lease] = {}
        self._by_resource: Dict[str, List[str]] = defaultdict(list)
        self._by_holder: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()

    def create(self, lease: Lease) -> bool:
        """Create lease."""
        with self._lock:
            if lease.lease_id in self._leases:
                return False

            self._leases[lease.lease_id] = lease
            self._by_resource[lease.resource_id].append(lease.lease_id)
            self._by_holder[lease.holder_id].append(lease.lease_id)

            return True

    def get(self, lease_id: str) -> Optional[Lease]:
        """Get lease by ID."""
        with self._lock:
            return self._leases.get(lease_id)

    def update(self, lease: Lease) -> bool:
        """Update lease."""
        with self._lock:
            if lease.lease_id not in self._leases:
                return False

            self._leases[lease.lease_id] = lease
            return True

    def delete(self, lease_id: str) -> Optional[Lease]:
        """Delete lease."""
        with self._lock:
            lease = self._leases.pop(lease_id, None)

            if lease:
                self._by_resource[lease.resource_id].remove(lease_id)
                self._by_holder[lease.holder_id].remove(lease_id)

            return lease

    def get_by_resource(self, resource_id: str) -> List[Lease]:
        """Get leases by resource."""
        with self._lock:
            lease_ids = self._by_resource.get(resource_id, [])
            return [
                self._leases[lid] for lid in lease_ids
                if lid in self._leases
            ]

    def get_by_holder(self, holder_id: str) -> List[Lease]:
        """Get leases by holder."""
        with self._lock:
            lease_ids = self._by_holder.get(holder_id, [])
            return [
                self._leases[lid] for lid in lease_ids
                if lid in self._leases
            ]

    def get_all(self) -> List[Lease]:
        """Get all leases."""
        with self._lock:
            return list(self._leases.values())

    def get_expired(self) -> List[Lease]:
        """Get expired leases."""
        now = datetime.utcnow()
        with self._lock:
            return [
                l for l in self._leases.values()
                if l.expires_at and l.expires_at < now
                and l.state == LeaseState.ACTIVE
            ]


# =============================================================================
# WAIT QUEUE
# =============================================================================

class WaitQueue:
    """Priority queue for lock waiters."""

    def __init__(self):
        self._queues: Dict[str, List[Tuple[int, datetime, LockRequest]]] = defaultdict(list)
        self._lock = threading.RLock()

    def add(self, request: LockRequest) -> None:
        """Add request to queue."""
        with self._lock:
            entry = (-request.priority, request.requested_at, request)
            heapq.heappush(self._queues[request.resource_id], entry)

    def pop(self, resource_id: str) -> Optional[LockRequest]:
        """Pop next request."""
        with self._lock:
            queue = self._queues.get(resource_id, [])
            if queue:
                _, _, request = heapq.heappop(queue)
                return request
        return None

    def peek(self, resource_id: str) -> Optional[LockRequest]:
        """Peek next request."""
        with self._lock:
            queue = self._queues.get(resource_id, [])
            if queue:
                return queue[0][2]
        return None

    def remove(self, request_id: str) -> bool:
        """Remove request by ID."""
        with self._lock:
            for resource_id, queue in self._queues.items():
                for i, (_, _, req) in enumerate(queue):
                    if req.request_id == request_id:
                        queue.pop(i)
                        heapq.heapify(queue)
                        return True
        return False

    def get_waiters(self, resource_id: str) -> List[LockRequest]:
        """Get all waiters for resource."""
        with self._lock:
            queue = self._queues.get(resource_id, [])
            return [req for _, _, req in queue]

    def is_empty(self, resource_id: str) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return len(self._queues.get(resource_id, [])) == 0


# =============================================================================
# DEADLOCK DETECTOR
# =============================================================================

class DeadlockDetector:
    """Detects deadlocks using wait-for graph."""

    def __init__(self):
        self._wait_graph: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def add_wait(self, waiter: str, holder: str) -> None:
        """Add wait edge."""
        with self._lock:
            self._wait_graph[waiter].add(holder)

    def remove_wait(self, waiter: str, holder: Optional[str] = None) -> None:
        """Remove wait edge."""
        with self._lock:
            if holder:
                self._wait_graph[waiter].discard(holder)
            else:
                self._wait_graph.pop(waiter, None)

    def detect_cycle(self) -> Optional[List[str]]:
        """Detect cycle in wait graph (deadlock)."""
        with self._lock:
            visited = set()
            rec_stack = set()
            path = []

            def dfs(node: str) -> Optional[List[str]]:
                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                for neighbor in self._wait_graph.get(node, set()):
                    if neighbor not in visited:
                        result = dfs(neighbor)
                        if result:
                            return result
                    elif neighbor in rec_stack:
                        # Cycle found
                        idx = path.index(neighbor)
                        return path[idx:]

                path.pop()
                rec_stack.remove(node)
                return None

            for node in list(self._wait_graph.keys()):
                if node not in visited:
                    cycle = dfs(node)
                    if cycle:
                        return cycle

            return None

    def get_wait_info(self, holder_id: str) -> WaitInfo:
        """Get wait info for holder."""
        with self._lock:
            return WaitInfo(
                holder_id=holder_id,
                waiting_for=list(self._wait_graph.get(holder_id, set()))
            )


# =============================================================================
# LEASE MANAGER
# =============================================================================

class LeaseManager:
    """
    Lease Manager for BAEL.

    Advanced distributed lease management.
    """

    def __init__(self, config: Optional[LeaseConfig] = None):
        self._config = config or LeaseConfig()
        self._store = LeaseStore()
        self._wait_queue = WaitQueue()
        self._deadlock_detector = DeadlockDetector()
        self._fencing = FencingTokenGenerator()
        self._callbacks: Dict[str, List[Callable[[Lease], None]]] = defaultdict(list)
        self._stats = LeaseStats()
        self._leader_info: Dict[str, LeaderInfo] = {}
        self._lock = threading.RLock()
        self._running = False
        self._expiry_task: Optional[asyncio.Task] = None

    # -------------------------------------------------------------------------
    # LEASE ACQUISITION
    # -------------------------------------------------------------------------

    async def acquire(
        self,
        resource_id: str,
        holder_id: str,
        lock_type: LockType = LockType.EXCLUSIVE,
        ttl_seconds: Optional[int] = None,
        timeout_seconds: float = 30.0,
        priority: int = 0,
        wait: bool = True
    ) -> Tuple[AcquireResult, Optional[Lease]]:
        """Acquire lease on resource."""
        ttl = ttl_seconds or self._config.default_ttl_seconds

        with self._lock:
            # Check existing leases
            existing = self._store.get_by_resource(resource_id)
            active_leases = [
                l for l in existing
                if l.state == LeaseState.ACTIVE
            ]

            # Check compatibility
            can_acquire = self._can_acquire(active_leases, lock_type, holder_id)

            if can_acquire:
                return self._grant_lease(
                    resource_id, holder_id, lock_type, ttl
                )

            if not wait:
                return (AcquireResult.DENIED, None)

        # Wait for lease
        request = LockRequest(
            resource_id=resource_id,
            requester_id=holder_id,
            lock_type=lock_type,
            timeout_seconds=timeout_seconds,
            priority=priority
        )

        self._wait_queue.add(request)

        # Add to wait graph for deadlock detection
        if self._config.deadlock_detection:
            for lease in active_leases:
                self._deadlock_detector.add_wait(holder_id, lease.holder_id)

            # Check for deadlock
            cycle = self._deadlock_detector.detect_cycle()
            if cycle:
                self._wait_queue.remove(request.request_id)
                self._deadlock_detector.remove_wait(holder_id)
                self._stats.deadlocks_detected += 1
                return (AcquireResult.DENIED, None)

        # Wait with timeout
        deadline = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        while datetime.utcnow() < deadline:
            await asyncio.sleep(0.1)

            with self._lock:
                existing = self._store.get_by_resource(resource_id)
                active = [l for l in existing if l.state == LeaseState.ACTIVE]

                if self._can_acquire(active, lock_type, holder_id):
                    self._wait_queue.remove(request.request_id)
                    self._deadlock_detector.remove_wait(holder_id)

                    return self._grant_lease(
                        resource_id, holder_id, lock_type, ttl
                    )

        # Timeout
        self._wait_queue.remove(request.request_id)
        self._deadlock_detector.remove_wait(holder_id)
        self._stats.timeouts += 1

        return (AcquireResult.TIMEOUT, None)

    def _can_acquire(
        self,
        active_leases: List[Lease],
        lock_type: LockType,
        holder_id: str
    ) -> bool:
        """Check if can acquire lock."""
        if not active_leases:
            return True

        # Check for reentrant
        for lease in active_leases:
            if lease.holder_id == holder_id:
                # Same holder - check compatibility
                if lock_type == lease.lock_type:
                    return True

        # Shared/Read locks are compatible
        if lock_type in (LockType.SHARED, LockType.READ):
            all_shared = all(
                l.lock_type in (LockType.SHARED, LockType.READ)
                for l in active_leases
            )
            return all_shared

        return False

    def _grant_lease(
        self,
        resource_id: str,
        holder_id: str,
        lock_type: LockType,
        ttl: int
    ) -> Tuple[AcquireResult, Lease]:
        """Grant lease."""
        now = datetime.utcnow()

        lease = Lease(
            resource_id=resource_id,
            holder_id=holder_id,
            lock_type=lock_type,
            state=LeaseState.ACTIVE,
            ttl_seconds=ttl,
            fencing_token=self._fencing.next() if self._config.enable_fencing else 0,
            acquired_at=now,
            expires_at=now + timedelta(seconds=ttl)
        )

        self._store.create(lease)
        self._stats.acquisitions += 1
        self._stats.total_leases += 1
        self._stats.active_leases += 1

        # Fire callbacks
        for callback in self._callbacks.get(resource_id, []):
            try:
                callback(lease)
            except Exception:
                pass

        return (AcquireResult.SUCCESS, lease)

    # -------------------------------------------------------------------------
    # LEASE OPERATIONS
    # -------------------------------------------------------------------------

    async def release(self, lease_id: str) -> bool:
        """Release lease."""
        with self._lock:
            lease = self._store.get(lease_id)

            if not lease:
                return False

            lease.state = LeaseState.RELEASED
            self._store.delete(lease_id)

            self._stats.releases += 1
            self._stats.active_leases -= 1

            # Process wait queue
            self._process_waiters(lease.resource_id)

        return True

    async def renew(
        self,
        lease_id: str,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Renew lease."""
        with self._lock:
            lease = self._store.get(lease_id)

            if not lease or lease.state != LeaseState.ACTIVE:
                return False

            if lease.renewals >= self._config.max_renewals:
                return False

            ttl = ttl_seconds or lease.ttl_seconds
            now = datetime.utcnow()

            lease.expires_at = now + timedelta(seconds=ttl)
            lease.renewals += 1

            # Optionally update fencing token
            if self._config.enable_fencing:
                lease.fencing_token = self._fencing.next()

            self._store.update(lease)
            self._stats.renewals += 1

        return True

    def get_lease(self, lease_id: str) -> Optional[Lease]:
        """Get lease by ID."""
        return self._store.get(lease_id)

    def get_leases_by_resource(self, resource_id: str) -> List[Lease]:
        """Get leases by resource."""
        return self._store.get_by_resource(resource_id)

    def get_leases_by_holder(self, holder_id: str) -> List[Lease]:
        """Get leases by holder."""
        return self._store.get_by_holder(holder_id)

    def is_held(
        self,
        resource_id: str,
        holder_id: Optional[str] = None
    ) -> bool:
        """Check if resource is held."""
        leases = self._store.get_by_resource(resource_id)
        active = [l for l in leases if l.state == LeaseState.ACTIVE]

        if not active:
            return False

        if holder_id:
            return any(l.holder_id == holder_id for l in active)

        return True

    # -------------------------------------------------------------------------
    # FENCING
    # -------------------------------------------------------------------------

    def validate_fencing_token(
        self,
        resource_id: str,
        token: int
    ) -> bool:
        """Validate fencing token."""
        leases = self._store.get_by_resource(resource_id)

        for lease in leases:
            if lease.state == LeaseState.ACTIVE:
                if lease.fencing_token >= token:
                    return True

        return False

    def get_current_fencing_token(
        self,
        resource_id: str
    ) -> Optional[int]:
        """Get current fencing token for resource."""
        leases = self._store.get_by_resource(resource_id)

        for lease in leases:
            if lease.state == LeaseState.ACTIVE:
                return lease.fencing_token

        return None

    # -------------------------------------------------------------------------
    # EXPIRATION
    # -------------------------------------------------------------------------

    async def expire_leases(self) -> List[Lease]:
        """Expire expired leases."""
        expired = []

        with self._lock:
            for lease in self._store.get_expired():
                lease.state = LeaseState.EXPIRED
                self._store.delete(lease.lease_id)
                expired.append(lease)

                self._stats.expired_leases += 1
                self._stats.active_leases -= 1

                # Process waiters
                self._process_waiters(lease.resource_id)

        return expired

    def _process_waiters(self, resource_id: str) -> None:
        """Process wait queue for resource."""
        while True:
            request = self._wait_queue.peek(resource_id)
            if not request:
                break

            leases = self._store.get_by_resource(resource_id)
            active = [l for l in leases if l.state == LeaseState.ACTIVE]

            if self._can_acquire(active, request.lock_type, request.requester_id):
                self._wait_queue.pop(resource_id)
            else:
                break

    async def start_expiry_monitor(self, interval: float = 1.0) -> None:
        """Start expiry monitor."""
        self._running = True

        while self._running:
            await self.expire_leases()
            await asyncio.sleep(interval)

    def stop_expiry_monitor(self) -> None:
        """Stop expiry monitor."""
        self._running = False

    # -------------------------------------------------------------------------
    # LEADER ELECTION
    # -------------------------------------------------------------------------

    async def elect_leader(
        self,
        election_id: str,
        candidate_id: str,
        ttl_seconds: int = 30
    ) -> LeaderInfo:
        """Participate in leader election."""
        with self._lock:
            info = self._leader_info.get(election_id)

            if info and info.state == LeaderState.LEADER:
                # Check if lease still valid
                if info.lease_id:
                    lease = self._store.get(info.lease_id)
                    if lease and lease.state == LeaseState.ACTIVE:
                        return info

            # Try to acquire leadership lease
            result, lease = await self.acquire(
                resource_id=f"__election__{election_id}",
                holder_id=candidate_id,
                lock_type=LockType.EXCLUSIVE,
                ttl_seconds=ttl_seconds,
                wait=False
            )

            if result == AcquireResult.SUCCESS and lease:
                info = LeaderInfo(
                    leader_id=candidate_id,
                    term=info.term + 1 if info else 1,
                    state=LeaderState.LEADER,
                    elected_at=datetime.utcnow(),
                    lease_id=lease.lease_id
                )
            else:
                info = LeaderInfo(
                    leader_id=self._get_current_leader(election_id) or "",
                    term=info.term if info else 0,
                    state=LeaderState.FOLLOWER
                )

            self._leader_info[election_id] = info
            return info

    def _get_current_leader(self, election_id: str) -> Optional[str]:
        """Get current leader."""
        leases = self._store.get_by_resource(f"__election__{election_id}")

        for lease in leases:
            if lease.state == LeaseState.ACTIVE:
                return lease.holder_id

        return None

    def is_leader(self, election_id: str, candidate_id: str) -> bool:
        """Check if candidate is leader."""
        info = self._leader_info.get(election_id)

        if info and info.state == LeaderState.LEADER:
            return info.leader_id == candidate_id

        return False

    def get_leader_info(self, election_id: str) -> Optional[LeaderInfo]:
        """Get leader info."""
        return self._leader_info.get(election_id)

    async def renew_leadership(self, election_id: str) -> bool:
        """Renew leadership lease."""
        info = self._leader_info.get(election_id)

        if not info or not info.lease_id:
            return False

        return await self.renew(info.lease_id)

    # -------------------------------------------------------------------------
    # CALLBACKS
    # -------------------------------------------------------------------------

    def on_lease(
        self,
        resource_id: str,
        callback: Callable[[Lease], None]
    ) -> str:
        """Register lease callback."""
        callback_id = str(uuid.uuid4())

        with self._lock:
            self._callbacks[resource_id].append(callback)

        return callback_id

    # -------------------------------------------------------------------------
    # DEADLOCK DETECTION
    # -------------------------------------------------------------------------

    def detect_deadlocks(self) -> Optional[List[str]]:
        """Detect deadlocks."""
        return self._deadlock_detector.detect_cycle()

    def get_wait_info(self, holder_id: str) -> WaitInfo:
        """Get wait info."""
        return self._deadlock_detector.get_wait_info(holder_id)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> LeaseStats:
        """Get statistics."""
        with self._lock:
            return LeaseStats(
                total_leases=self._stats.total_leases,
                active_leases=self._stats.active_leases,
                expired_leases=self._stats.expired_leases,
                acquisitions=self._stats.acquisitions,
                renewals=self._stats.renewals,
                releases=self._stats.releases,
                timeouts=self._stats.timeouts,
                deadlocks_detected=self._stats.deadlocks_detected
            )

    def get_all_leases(self) -> List[Lease]:
        """Get all leases."""
        return self._store.get_all()


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

class LeaseContext:
    """Context manager for leases."""

    def __init__(
        self,
        manager: LeaseManager,
        resource_id: str,
        holder_id: str,
        lock_type: LockType = LockType.EXCLUSIVE,
        ttl_seconds: Optional[int] = None
    ):
        self._manager = manager
        self._resource_id = resource_id
        self._holder_id = holder_id
        self._lock_type = lock_type
        self._ttl_seconds = ttl_seconds
        self._lease: Optional[Lease] = None

    async def __aenter__(self) -> Optional[Lease]:
        result, lease = await self._manager.acquire(
            self._resource_id,
            self._holder_id,
            self._lock_type,
            self._ttl_seconds
        )

        if result == AcquireResult.SUCCESS:
            self._lease = lease

        return self._lease

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._lease:
            await self._manager.release(self._lease.lease_id)


def lease_context(
    manager: LeaseManager,
    resource_id: str,
    holder_id: str,
    lock_type: LockType = LockType.EXCLUSIVE
) -> LeaseContext:
    """Create lease context."""
    return LeaseContext(manager, resource_id, holder_id, lock_type)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Lease Manager."""
    print("=" * 70)
    print("BAEL - LEASE MANAGER DEMO")
    print("Advanced Distributed Lease Management for AI Agents")
    print("=" * 70)
    print()

    manager = LeaseManager(LeaseConfig(
        default_ttl_seconds=30,
        enable_fencing=True,
        deadlock_detection=True
    ))

    # 1. Basic Lease Acquisition
    print("1. BASIC LEASE ACQUISITION:")
    print("-" * 40)

    result, lease = await manager.acquire(
        resource_id="resource:1",
        holder_id="agent:1"
    )

    print(f"   Acquire resource:1: {result.value}")
    if lease:
        print(f"   Lease ID: {lease.lease_id[:8]}...")
        print(f"   Fencing token: {lease.fencing_token}")
    print()

    # 2. Attempt Concurrent Acquisition
    print("2. CONCURRENT ACQUISITION:")
    print("-" * 40)

    result2, lease2 = await manager.acquire(
        resource_id="resource:1",
        holder_id="agent:2",
        wait=False
    )

    print(f"   Acquire by agent:2: {result2.value}")
    print()

    # 3. Shared Locks
    print("3. SHARED LOCKS:")
    print("-" * 40)

    r1, l1 = await manager.acquire(
        resource_id="resource:2",
        holder_id="reader:1",
        lock_type=LockType.SHARED
    )
    print(f"   Reader 1: {r1.value}")

    r2, l2 = await manager.acquire(
        resource_id="resource:2",
        holder_id="reader:2",
        lock_type=LockType.SHARED
    )
    print(f"   Reader 2: {r2.value}")

    r3, l3 = await manager.acquire(
        resource_id="resource:2",
        holder_id="writer:1",
        lock_type=LockType.EXCLUSIVE,
        wait=False
    )
    print(f"   Writer 1 (exclusive): {r3.value}")
    print()

    # 4. Release Lease
    print("4. RELEASE LEASE:")
    print("-" * 40)

    if lease:
        released = await manager.release(lease.lease_id)
        print(f"   Released resource:1: {released}")
    print()

    # 5. Renew Lease
    print("5. RENEW LEASE:")
    print("-" * 40)

    result, new_lease = await manager.acquire(
        resource_id="resource:3",
        holder_id="agent:3"
    )

    if new_lease:
        renewed = await manager.renew(new_lease.lease_id)
        print(f"   Renewed lease: {renewed}")
        print(f"   New fencing token: {manager.get_lease(new_lease.lease_id).fencing_token}")
    print()

    # 6. Check if Held
    print("6. CHECK IF HELD:")
    print("-" * 40)

    print(f"   resource:2 held: {manager.is_held('resource:2')}")
    print(f"   resource:2 held by reader:1: {manager.is_held('resource:2', 'reader:1')}")
    print(f"   resource:99 held: {manager.is_held('resource:99')}")
    print()

    # 7. Leader Election
    print("7. LEADER ELECTION:")
    print("-" * 40)

    info1 = await manager.elect_leader("cluster:1", "node:1")
    print(f"   Node 1 election: {info1.state.value}, leader={info1.leader_id}")

    info2 = await manager.elect_leader("cluster:1", "node:2")
    print(f"   Node 2 election: {info2.state.value}, leader={info2.leader_id}")
    print()

    # 8. Get Leases by Holder
    print("8. GET LEASES BY HOLDER:")
    print("-" * 40)

    leases = manager.get_leases_by_holder("reader:1")

    for l in leases:
        print(f"   {l.resource_id}: {l.lock_type.value}")
    print()

    # 9. Fencing Token Validation
    print("9. FENCING TOKEN VALIDATION:")
    print("-" * 40)

    token = manager.get_current_fencing_token("resource:3")
    print(f"   Current token for resource:3: {token}")

    if token:
        valid = manager.validate_fencing_token("resource:3", token)
        print(f"   Token {token} valid: {valid}")

        valid_old = manager.validate_fencing_token("resource:3", token - 1)
        print(f"   Token {token - 1} valid: {valid_old}")
    print()

    # 10. Context Manager
    print("10. CONTEXT MANAGER:")
    print("-" * 40)

    async with lease_context(manager, "resource:4", "agent:4") as ctx_lease:
        if ctx_lease:
            print(f"   Acquired in context: {ctx_lease.resource_id}")
        else:
            print("   Failed to acquire")

    print(f"   After context - resource:4 held: {manager.is_held('resource:4')}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total leases: {stats.total_leases}")
    print(f"   Active leases: {stats.active_leases}")
    print(f"   Acquisitions: {stats.acquisitions}")
    print(f"   Renewals: {stats.renewals}")
    print(f"   Releases: {stats.releases}")
    print()

    # 12. All Leases
    print("12. ALL LEASES:")
    print("-" * 40)

    all_leases = manager.get_all_leases()

    for l in all_leases[:5]:
        print(f"   {l.resource_id}: {l.holder_id}, {l.state.value}")

    if len(all_leases) > 5:
        print(f"   ... and {len(all_leases) - 5} more")
    print()

    # 13. Expire Leases
    print("13. EXPIRE LEASES:")
    print("-" * 40)

    expired = await manager.expire_leases()
    print(f"   Expired leases: {len(expired)}")
    print()

    # 14. Renew Leadership
    print("14. RENEW LEADERSHIP:")
    print("-" * 40)

    renewed = await manager.renew_leadership("cluster:1")
    print(f"   Renewed leadership: {renewed}")
    print()

    # 15. Leader Check
    print("15. LEADER CHECK:")
    print("-" * 40)

    is_leader = manager.is_leader("cluster:1", "node:1")
    print(f"   Node 1 is leader: {is_leader}")

    leader_info = manager.get_leader_info("cluster:1")
    if leader_info:
        print(f"   Term: {leader_info.term}")
        print(f"   Elected: {leader_info.elected_at}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Lease Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
