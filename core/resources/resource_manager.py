#!/usr/bin/env python3
"""
BAEL - Resource Manager
Advanced resource management for AI agent operations.

Features:
- Resource lifecycle management
- Resource pooling
- Reference counting
- Lazy initialization
- Resource cleanup
- Dependency tracking
- Health monitoring
- Resource limits
- Allocation tracking
- Leak detection
"""

import asyncio
import logging
import threading
import time
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, AsyncIterator, Callable, Coroutine, Dict, Generic,
                    Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')
R = TypeVar('R', bound='Resource')


# =============================================================================
# ENUMS
# =============================================================================

class ResourceState(Enum):
    """Resource states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    IN_USE = "in_use"
    RELEASING = "releasing"
    RELEASED = "released"
    ERROR = "error"


class ResourceType(Enum):
    """Resource types."""
    CONNECTION = "connection"
    FILE = "file"
    MEMORY = "memory"
    THREAD = "thread"
    SOCKET = "socket"
    HANDLE = "handle"
    LOCK = "lock"
    BUFFER = "buffer"
    CUSTOM = "custom"


class AllocationStrategy(Enum):
    """Allocation strategies."""
    EAGER = "eager"
    LAZY = "lazy"
    POOLED = "pooled"


class CleanupPolicy(Enum):
    """Cleanup policies."""
    IMMEDIATE = "immediate"
    DEFERRED = "deferred"
    ON_IDLE = "on_idle"
    NEVER = "never"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ResourceConfig:
    """Resource configuration."""
    max_instances: int = 100
    idle_timeout: float = 300.0  # 5 minutes
    max_lifetime: float = 3600.0  # 1 hour
    health_check_interval: float = 60.0
    allocation_strategy: AllocationStrategy = AllocationStrategy.LAZY
    cleanup_policy: CleanupPolicy = CleanupPolicy.ON_IDLE


@dataclass
class ResourceInfo:
    """Resource information."""
    resource_id: str
    resource_type: ResourceType
    state: ResourceState
    created_at: datetime
    last_used: datetime
    use_count: int
    ref_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceStats:
    """Resource statistics."""
    total_created: int = 0
    total_released: int = 0
    current_active: int = 0
    current_idle: int = 0
    peak_active: int = 0
    total_errors: int = 0
    avg_lifetime_ms: float = 0.0
    avg_use_count: float = 0.0


@dataclass
class AllocationRequest:
    """Resource allocation request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource_type: ResourceType = ResourceType.CUSTOM
    timeout: float = 30.0
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeakInfo:
    """Resource leak information."""
    resource_id: str
    resource_type: ResourceType
    created_at: datetime
    stack_trace: Optional[str] = None
    allocated_by: Optional[str] = None


# =============================================================================
# RESOURCE BASE CLASS
# =============================================================================

class Resource(ABC, Generic[T]):
    """
    Base resource class.
    """

    def __init__(self, resource_type: ResourceType = ResourceType.CUSTOM):
        self._id = str(uuid.uuid4())
        self._type = resource_type
        self._state = ResourceState.UNINITIALIZED
        self._created_at = datetime.utcnow()
        self._last_used = self._created_at
        self._use_count = 0
        self._ref_count = 0
        self._lock = threading.RLock()
        self._value: Optional[T] = None
        self._error: Optional[Exception] = None
        self._metadata: Dict[str, Any] = {}

    @property
    def id(self) -> str:
        return self._id

    @property
    def resource_type(self) -> ResourceType:
        return self._type

    @property
    def state(self) -> ResourceState:
        return self._state

    @property
    def is_ready(self) -> bool:
        return self._state == ResourceState.READY

    @property
    def is_in_use(self) -> bool:
        return self._state == ResourceState.IN_USE

    @property
    def ref_count(self) -> int:
        return self._ref_count

    @property
    def value(self) -> Optional[T]:
        return self._value

    @property
    def age_seconds(self) -> float:
        return (datetime.utcnow() - self._created_at).total_seconds()

    @property
    def idle_seconds(self) -> float:
        return (datetime.utcnow() - self._last_used).total_seconds()

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the resource."""
        pass

    @abstractmethod
    async def release(self) -> None:
        """Release the resource."""
        pass

    async def validate(self) -> bool:
        """Validate the resource is healthy."""
        return self._state in (ResourceState.READY, ResourceState.IN_USE)

    def acquire(self) -> None:
        """Acquire the resource."""
        with self._lock:
            self._ref_count += 1
            self._use_count += 1
            self._last_used = datetime.utcnow()
            if self._state == ResourceState.READY:
                self._state = ResourceState.IN_USE

    def release_ref(self) -> int:
        """Release a reference."""
        with self._lock:
            self._ref_count = max(0, self._ref_count - 1)
            if self._ref_count == 0 and self._state == ResourceState.IN_USE:
                self._state = ResourceState.READY
            return self._ref_count

    def get_info(self) -> ResourceInfo:
        """Get resource information."""
        return ResourceInfo(
            resource_id=self._id,
            resource_type=self._type,
            state=self._state,
            created_at=self._created_at,
            last_used=self._last_used,
            use_count=self._use_count,
            ref_count=self._ref_count,
            metadata=self._metadata.copy()
        )


# =============================================================================
# RESOURCE IMPLEMENTATIONS
# =============================================================================

class ManagedValue(Resource[T]):
    """A managed value resource."""

    def __init__(
        self,
        factory: Callable[[], T],
        cleanup: Optional[Callable[[T], None]] = None,
        resource_type: ResourceType = ResourceType.CUSTOM
    ):
        super().__init__(resource_type)
        self._factory = factory
        self._cleanup = cleanup

    async def initialize(self) -> None:
        with self._lock:
            if self._state != ResourceState.UNINITIALIZED:
                return
            self._state = ResourceState.INITIALIZING

        try:
            self._value = self._factory()
            with self._lock:
                self._state = ResourceState.READY
        except Exception as e:
            with self._lock:
                self._state = ResourceState.ERROR
                self._error = e
            raise

    async def release(self) -> None:
        with self._lock:
            if self._state in (ResourceState.RELEASED, ResourceState.UNINITIALIZED):
                return
            self._state = ResourceState.RELEASING

        try:
            if self._value and self._cleanup:
                self._cleanup(self._value)
        finally:
            with self._lock:
                self._value = None
                self._state = ResourceState.RELEASED


class AsyncManagedValue(Resource[T]):
    """An async managed value resource."""

    def __init__(
        self,
        factory: Callable[[], Coroutine[Any, Any, T]],
        cleanup: Optional[Callable[[T], Coroutine[Any, Any, None]]] = None,
        resource_type: ResourceType = ResourceType.CUSTOM
    ):
        super().__init__(resource_type)
        self._factory = factory
        self._cleanup = cleanup

    async def initialize(self) -> None:
        with self._lock:
            if self._state != ResourceState.UNINITIALIZED:
                return
            self._state = ResourceState.INITIALIZING

        try:
            self._value = await self._factory()
            with self._lock:
                self._state = ResourceState.READY
        except Exception as e:
            with self._lock:
                self._state = ResourceState.ERROR
                self._error = e
            raise

    async def release(self) -> None:
        with self._lock:
            if self._state in (ResourceState.RELEASED, ResourceState.UNINITIALIZED):
                return
            self._state = ResourceState.RELEASING

        try:
            if self._value and self._cleanup:
                await self._cleanup(self._value)
        finally:
            with self._lock:
                self._value = None
                self._state = ResourceState.RELEASED


class LazyResource(Resource[T]):
    """A lazily initialized resource."""

    def __init__(
        self,
        factory: Callable[[], T],
        resource_type: ResourceType = ResourceType.CUSTOM
    ):
        super().__init__(resource_type)
        self._factory = factory
        self._initialized = False

    async def initialize(self) -> None:
        # Lazy resources don't initialize until first use
        with self._lock:
            self._state = ResourceState.READY

    def get_value(self) -> T:
        """Get value, initializing if needed."""
        with self._lock:
            if not self._initialized:
                self._value = self._factory()
                self._initialized = True
            return self._value

    async def release(self) -> None:
        with self._lock:
            self._value = None
            self._initialized = False
            self._state = ResourceState.RELEASED


# =============================================================================
# REFERENCE COUNTER
# =============================================================================

class RefCounter(Generic[T]):
    """Reference counter for resources."""

    def __init__(self, value: T, on_zero: Optional[Callable[[T], None]] = None):
        self._value = value
        self._count = 0
        self._on_zero = on_zero
        self._lock = threading.Lock()

    @property
    def value(self) -> T:
        return self._value

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    def acquire(self) -> T:
        """Acquire a reference."""
        with self._lock:
            self._count += 1
            return self._value

    def release(self) -> int:
        """Release a reference."""
        with self._lock:
            self._count = max(0, self._count - 1)
            count = self._count

        if count == 0 and self._on_zero:
            self._on_zero(self._value)

        return count


# =============================================================================
# RESOURCE POOL
# =============================================================================

class ResourcePool(Generic[R]):
    """
    Pool of reusable resources.
    """

    def __init__(
        self,
        factory: Callable[[], R],
        config: Optional[ResourceConfig] = None
    ):
        self._factory = factory
        self._config = config or ResourceConfig()
        self._available: List[R] = []
        self._in_use: Dict[str, R] = {}
        self._lock = threading.RLock()
        self._stats = ResourceStats()
        self._condition = threading.Condition(self._lock)

    @property
    def available_count(self) -> int:
        with self._lock:
            return len(self._available)

    @property
    def in_use_count(self) -> int:
        with self._lock:
            return len(self._in_use)

    @property
    def total_count(self) -> int:
        with self._lock:
            return len(self._available) + len(self._in_use)

    async def acquire(self, timeout: float = 30.0) -> R:
        """Acquire a resource from the pool."""
        deadline = time.time() + timeout

        with self._lock:
            while True:
                # Try to get from available
                if self._available:
                    resource = self._available.pop()

                    # Validate resource
                    if await resource.validate():
                        self._in_use[resource.id] = resource
                        resource.acquire()
                        return resource
                    else:
                        # Resource is invalid, release it
                        await resource.release()
                        self._stats.total_released += 1
                        continue

                # Create new if under limit
                if self.total_count < self._config.max_instances:
                    resource = self._factory()
                    await resource.initialize()
                    self._in_use[resource.id] = resource
                    resource.acquire()
                    self._stats.total_created += 1
                    self._stats.current_active += 1
                    self._stats.peak_active = max(
                        self._stats.peak_active,
                        self._stats.current_active
                    )
                    return resource

                # Wait for available resource
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise ResourceExhaustedError("Resource pool exhausted")

                self._condition.wait(timeout=remaining)

    async def release(self, resource: R) -> None:
        """Release a resource back to the pool."""
        with self._lock:
            if resource.id in self._in_use:
                del self._in_use[resource.id]
                resource.release_ref()

                # Check if resource is still valid
                if (
                    resource.age_seconds < self._config.max_lifetime and
                    await resource.validate()
                ):
                    self._available.append(resource)
                    self._stats.current_idle += 1
                else:
                    await resource.release()
                    self._stats.total_released += 1

                self._stats.current_active = max(0, self._stats.current_active - 1)
                self._condition.notify()

    @asynccontextmanager
    async def get(self, timeout: float = 30.0) -> AsyncIterator[R]:
        """Context manager for acquiring a resource."""
        resource = await self.acquire(timeout)
        try:
            yield resource
        finally:
            await self.release(resource)

    async def cleanup_idle(self, max_idle: Optional[float] = None) -> int:
        """Clean up idle resources."""
        max_idle = max_idle or self._config.idle_timeout
        cleaned = 0

        with self._lock:
            still_available = []
            for resource in self._available:
                if resource.idle_seconds > max_idle:
                    await resource.release()
                    self._stats.total_released += 1
                    self._stats.current_idle = max(0, self._stats.current_idle - 1)
                    cleaned += 1
                else:
                    still_available.append(resource)
            self._available = still_available

        return cleaned

    async def shutdown(self) -> None:
        """Shutdown the pool."""
        with self._lock:
            # Release all available resources
            for resource in self._available:
                await resource.release()
                self._stats.total_released += 1
            self._available.clear()

            # Release all in-use resources (forced)
            for resource in self._in_use.values():
                await resource.release()
                self._stats.total_released += 1
            self._in_use.clear()

            self._stats.current_active = 0
            self._stats.current_idle = 0

    def get_stats(self) -> ResourceStats:
        """Get pool statistics."""
        with self._lock:
            return ResourceStats(
                total_created=self._stats.total_created,
                total_released=self._stats.total_released,
                current_active=len(self._in_use),
                current_idle=len(self._available),
                peak_active=self._stats.peak_active,
                total_errors=self._stats.total_errors
            )


# =============================================================================
# RESOURCE TRACKER
# =============================================================================

class ResourceTracker:
    """
    Tracks resources for leak detection.
    """

    def __init__(self):
        self._resources: Dict[str, weakref.ref] = {}
        self._allocation_info: Dict[str, LeakInfo] = {}
        self._lock = threading.RLock()

    def track(
        self,
        resource: Resource,
        allocated_by: Optional[str] = None
    ) -> None:
        """Track a resource."""
        with self._lock:
            self._resources[resource.id] = weakref.ref(resource)
            self._allocation_info[resource.id] = LeakInfo(
                resource_id=resource.id,
                resource_type=resource.resource_type,
                created_at=datetime.utcnow(),
                allocated_by=allocated_by
            )

    def untrack(self, resource_id: str) -> None:
        """Untrack a resource."""
        with self._lock:
            self._resources.pop(resource_id, None)
            self._allocation_info.pop(resource_id, None)

    def get_active(self) -> List[ResourceInfo]:
        """Get all active resources."""
        active = []

        with self._lock:
            for resource_id, ref in list(self._resources.items()):
                resource = ref()
                if resource:
                    active.append(resource.get_info())
                else:
                    # Resource was garbage collected
                    del self._resources[resource_id]
                    self._allocation_info.pop(resource_id, None)

        return active

    def detect_leaks(self, max_age: float = 3600.0) -> List[LeakInfo]:
        """Detect potential resource leaks."""
        leaks = []
        now = datetime.utcnow()

        with self._lock:
            for resource_id, ref in list(self._resources.items()):
                resource = ref()
                if resource:
                    info = self._allocation_info.get(resource_id)
                    if info:
                        age = (now - info.created_at).total_seconds()
                        if age > max_age:
                            leaks.append(info)

        return leaks


# =============================================================================
# RESOURCE LIMITS
# =============================================================================

@dataclass
class ResourceLimits:
    """Resource limits configuration."""
    max_memory_bytes: int = 1024 * 1024 * 1024  # 1GB
    max_connections: int = 100
    max_files: int = 1000
    max_threads: int = 50
    max_handles: int = 500


class LimitEnforcer:
    """Enforces resource limits."""

    def __init__(self, limits: ResourceLimits):
        self._limits = limits
        self._current: Dict[ResourceType, int] = defaultdict(int)
        self._lock = threading.RLock()

    def can_allocate(self, resource_type: ResourceType, count: int = 1) -> bool:
        """Check if allocation is allowed."""
        with self._lock:
            current = self._current[resource_type]
            limit = self._get_limit(resource_type)
            return current + count <= limit

    def allocate(self, resource_type: ResourceType, count: int = 1) -> bool:
        """Allocate resources."""
        with self._lock:
            if not self.can_allocate(resource_type, count):
                return False
            self._current[resource_type] += count
            return True

    def release(self, resource_type: ResourceType, count: int = 1) -> None:
        """Release resources."""
        with self._lock:
            self._current[resource_type] = max(0, self._current[resource_type] - count)

    def _get_limit(self, resource_type: ResourceType) -> int:
        """Get limit for resource type."""
        limits_map = {
            ResourceType.CONNECTION: self._limits.max_connections,
            ResourceType.FILE: self._limits.max_files,
            ResourceType.THREAD: self._limits.max_threads,
            ResourceType.HANDLE: self._limits.max_handles,
        }
        return limits_map.get(resource_type, 1000)

    def get_usage(self) -> Dict[ResourceType, Tuple[int, int]]:
        """Get current usage (current, limit)."""
        with self._lock:
            return {
                rt: (self._current[rt], self._get_limit(rt))
                for rt in ResourceType
            }


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ResourceError(Exception):
    """Base resource error."""
    pass


class ResourceExhaustedError(ResourceError):
    """Resources exhausted."""
    pass


class ResourceNotFoundError(ResourceError):
    """Resource not found."""
    pass


class ResourceLimitExceededError(ResourceError):
    """Resource limit exceeded."""
    pass


# =============================================================================
# RESOURCE MANAGER
# =============================================================================

class ResourceManager:
    """
    Resource Manager for BAEL.

    Advanced resource lifecycle management.
    """

    def __init__(self, config: Optional[ResourceConfig] = None):
        self._config = config or ResourceConfig()
        self._resources: Dict[str, Resource] = {}
        self._pools: Dict[str, ResourcePool] = {}
        self._tracker = ResourceTracker()
        self._limits = LimitEnforcer(ResourceLimits())
        self._lock = threading.RLock()
        self._stats = ResourceStats()

    # -------------------------------------------------------------------------
    # RESOURCE CREATION
    # -------------------------------------------------------------------------

    async def create(
        self,
        factory: Callable[[], T],
        resource_type: ResourceType = ResourceType.CUSTOM,
        cleanup: Optional[Callable[[T], None]] = None
    ) -> ManagedValue[T]:
        """Create a managed resource."""
        if not self._limits.can_allocate(resource_type):
            raise ResourceLimitExceededError(f"Limit exceeded for {resource_type.value}")

        resource = ManagedValue(
            factory=factory,
            cleanup=cleanup,
            resource_type=resource_type
        )

        await resource.initialize()

        with self._lock:
            self._resources[resource.id] = resource
            self._limits.allocate(resource_type)
            self._stats.total_created += 1
            self._stats.current_active += 1

        self._tracker.track(resource)

        return resource

    async def create_async(
        self,
        factory: Callable[[], Coroutine[Any, Any, T]],
        resource_type: ResourceType = ResourceType.CUSTOM,
        cleanup: Optional[Callable[[T], Coroutine[Any, Any, None]]] = None
    ) -> AsyncManagedValue[T]:
        """Create an async managed resource."""
        if not self._limits.can_allocate(resource_type):
            raise ResourceLimitExceededError(f"Limit exceeded for {resource_type.value}")

        resource = AsyncManagedValue(
            factory=factory,
            cleanup=cleanup,
            resource_type=resource_type
        )

        await resource.initialize()

        with self._lock:
            self._resources[resource.id] = resource
            self._limits.allocate(resource_type)
            self._stats.total_created += 1
            self._stats.current_active += 1

        self._tracker.track(resource)

        return resource

    def create_lazy(
        self,
        factory: Callable[[], T],
        resource_type: ResourceType = ResourceType.CUSTOM
    ) -> LazyResource[T]:
        """Create a lazy resource."""
        resource = LazyResource(factory=factory, resource_type=resource_type)

        with self._lock:
            self._resources[resource.id] = resource

        self._tracker.track(resource)

        return resource

    # -------------------------------------------------------------------------
    # RESOURCE POOLS
    # -------------------------------------------------------------------------

    def create_pool(
        self,
        name: str,
        factory: Callable[[], R],
        config: Optional[ResourceConfig] = None
    ) -> ResourcePool[R]:
        """Create a resource pool."""
        pool = ResourcePool(factory=factory, config=config or self._config)

        with self._lock:
            self._pools[name] = pool

        return pool

    def get_pool(self, name: str) -> Optional[ResourcePool]:
        """Get a pool by name."""
        with self._lock:
            return self._pools.get(name)

    # -------------------------------------------------------------------------
    # RESOURCE ACCESS
    # -------------------------------------------------------------------------

    def get(self, resource_id: str) -> Optional[Resource]:
        """Get a resource by ID."""
        with self._lock:
            return self._resources.get(resource_id)

    async def release(self, resource_id: str) -> bool:
        """Release a resource."""
        with self._lock:
            resource = self._resources.pop(resource_id, None)

        if not resource:
            return False

        await resource.release()

        self._tracker.untrack(resource_id)
        self._limits.release(resource.resource_type)

        with self._lock:
            self._stats.total_released += 1
            self._stats.current_active = max(0, self._stats.current_active - 1)

        return True

    # -------------------------------------------------------------------------
    # CONTEXT MANAGERS
    # -------------------------------------------------------------------------

    @asynccontextmanager
    async def managed(
        self,
        factory: Callable[[], T],
        resource_type: ResourceType = ResourceType.CUSTOM,
        cleanup: Optional[Callable[[T], None]] = None
    ) -> AsyncIterator[T]:
        """Context manager for a managed resource."""
        resource = await self.create(
            factory=factory,
            resource_type=resource_type,
            cleanup=cleanup
        )

        try:
            yield resource.value
        finally:
            await self.release(resource.id)

    # -------------------------------------------------------------------------
    # MONITORING
    # -------------------------------------------------------------------------

    def get_active_resources(self) -> List[ResourceInfo]:
        """Get all active resources."""
        return self._tracker.get_active()

    def detect_leaks(self, max_age: float = 3600.0) -> List[LeakInfo]:
        """Detect potential resource leaks."""
        return self._tracker.detect_leaks(max_age)

    def get_usage(self) -> Dict[ResourceType, Tuple[int, int]]:
        """Get resource usage."""
        return self._limits.get_usage()

    def get_stats(self) -> ResourceStats:
        """Get resource statistics."""
        with self._lock:
            return ResourceStats(
                total_created=self._stats.total_created,
                total_released=self._stats.total_released,
                current_active=self._stats.current_active,
                current_idle=sum(p.available_count for p in self._pools.values()),
                peak_active=self._stats.peak_active
            )

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------

    async def cleanup_idle(self) -> int:
        """Clean up idle resources in all pools."""
        total = 0
        for pool in self._pools.values():
            total += await pool.cleanup_idle()
        return total

    async def cleanup_old(self, max_age: float = 3600.0) -> int:
        """Clean up old resources."""
        to_release = []

        with self._lock:
            for resource_id, resource in self._resources.items():
                if resource.age_seconds > max_age:
                    to_release.append(resource_id)

        for resource_id in to_release:
            await self.release(resource_id)

        return len(to_release)

    async def shutdown(self) -> None:
        """Shutdown the resource manager."""
        # Shutdown all pools
        for pool in self._pools.values():
            await pool.shutdown()

        # Release all resources
        resource_ids = list(self._resources.keys())
        for resource_id in resource_ids:
            await self.release(resource_id)

        logger.info("Resource Manager shutdown complete")


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Resource Manager."""
    print("=" * 70)
    print("BAEL - RESOURCE MANAGER DEMO")
    print("Advanced Resource Management for AI Agents")
    print("=" * 70)
    print()

    manager = ResourceManager()

    # 1. Basic Managed Resource
    print("1. BASIC MANAGED RESOURCE:")
    print("-" * 40)

    counter = {"value": 0}

    def create_counter():
        counter["value"] += 1
        return counter["value"]

    resource = await manager.create(
        factory=create_counter,
        resource_type=ResourceType.CUSTOM
    )

    print(f"   Resource ID: {resource.id[:8]}...")
    print(f"   Value: {resource.value}")
    print(f"   State: {resource.state.value}")
    print()

    # 2. Resource with Cleanup
    print("2. RESOURCE WITH CLEANUP:")
    print("-" * 40)

    cleanup_called = []

    def create_data():
        return {"data": "important"}

    def cleanup_data(data):
        cleanup_called.append(data)
        print(f"   Cleanup called for: {data}")

    resource2 = await manager.create(
        factory=create_data,
        cleanup=cleanup_data
    )

    print(f"   Resource created: {resource2.value}")
    await manager.release(resource2.id)
    print(f"   Cleanup callbacks: {len(cleanup_called)}")
    print()

    # 3. Lazy Resource
    print("3. LAZY RESOURCE:")
    print("-" * 40)

    lazy_init_count = {"count": 0}

    def lazy_factory():
        lazy_init_count["count"] += 1
        return f"lazy_value_{lazy_init_count['count']}"

    lazy = manager.create_lazy(factory=lazy_factory)
    print(f"   After creation - init count: {lazy_init_count['count']}")

    value = lazy.get_value()
    print(f"   After first access - value: {value}")
    print(f"   After first access - init count: {lazy_init_count['count']}")

    value2 = lazy.get_value()
    print(f"   After second access - same value: {value == value2}")
    print()

    # 4. Resource Pool
    print("4. RESOURCE POOL:")
    print("-" * 40)

    connection_id = {"id": 0}

    def create_connection() -> ManagedValue[str]:
        connection_id["id"] += 1
        resource = ManagedValue(
            factory=lambda: f"conn_{connection_id['id']}",
            resource_type=ResourceType.CONNECTION
        )
        return resource

    pool = manager.create_pool(
        name="connections",
        factory=create_connection,
        config=ResourceConfig(max_instances=5)
    )

    # Acquire and release resources
    async with pool.get() as conn1:
        print(f"   Connection 1: {conn1.value}")

        async with pool.get() as conn2:
            print(f"   Connection 2: {conn2.value}")
            print(f"   Pool in-use: {pool.in_use_count}")

    print(f"   After release - available: {pool.available_count}")
    print()

    # 5. Pool Statistics
    print("5. POOL STATISTICS:")
    print("-" * 40)

    stats = pool.get_stats()
    print(f"   Total created: {stats.total_created}")
    print(f"   Total released: {stats.total_released}")
    print(f"   Current active: {stats.current_active}")
    print(f"   Current idle: {stats.current_idle}")
    print(f"   Peak active: {stats.peak_active}")
    print()

    # 6. Reference Counter
    print("6. REFERENCE COUNTER:")
    print("-" * 40)

    ref_released = []

    def on_ref_zero(val):
        ref_released.append(val)

    ref = RefCounter(value="shared_data", on_zero=on_ref_zero)

    v1 = ref.acquire()
    v2 = ref.acquire()
    print(f"   After 2 acquires - count: {ref.count}")

    ref.release()
    print(f"   After 1 release - count: {ref.count}")

    ref.release()
    print(f"   After 2nd release - count: {ref.count}")
    print(f"   On-zero called: {len(ref_released) > 0}")
    print()

    # 7. Resource Limits
    print("7. RESOURCE LIMITS:")
    print("-" * 40)

    usage = manager.get_usage()
    for rt, (current, limit) in usage.items():
        if current > 0:
            print(f"   {rt.value}: {current}/{limit}")
    print()

    # 8. Active Resources
    print("8. ACTIVE RESOURCES:")
    print("-" * 40)

    active = manager.get_active_resources()
    print(f"   Total active: {len(active)}")
    for info in active[:3]:
        print(f"   - {info.resource_id[:8]}... ({info.resource_type.value})")
    print()

    # 9. Leak Detection
    print("9. LEAK DETECTION:")
    print("-" * 40)

    leaks = manager.detect_leaks(max_age=0.001)  # Very short for demo
    print(f"   Potential leaks detected: {len(leaks)}")
    print()

    # 10. Managed Context
    print("10. MANAGED CONTEXT:")
    print("-" * 40)

    async with manager.managed(
        factory=lambda: "temp_resource",
        resource_type=ResourceType.BUFFER
    ) as value:
        print(f"   Inside context: {value}")

    print("   Resource automatically released")
    print()

    # 11. Cleanup
    print("11. CLEANUP:")
    print("-" * 40)

    cleaned_idle = await manager.cleanup_idle()
    print(f"   Cleaned idle resources: {cleaned_idle}")

    cleaned_old = await manager.cleanup_old(max_age=0.001)
    print(f"   Cleaned old resources: {cleaned_old}")
    print()

    # 12. Final Stats
    print("12. FINAL STATISTICS:")
    print("-" * 40)

    final_stats = manager.get_stats()
    print(f"   Total created: {final_stats.total_created}")
    print(f"   Total released: {final_stats.total_released}")
    print(f"   Still active: {final_stats.current_active}")
    print()

    # Shutdown
    await manager.shutdown()
    print("   Manager shutdown complete")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Resource Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
