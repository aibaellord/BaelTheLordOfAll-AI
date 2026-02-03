#!/usr/bin/env python3
"""
BAEL - Resource Pool Manager
Comprehensive resource pooling and management system.

This module provides a complete resource pooling system for
managing connections, objects, and resources efficiently.

Features:
- Generic resource pooling
- Connection pooling
- Object pooling
- Resource lifecycle management
- Health checking
- Automatic cleanup
- Pool sizing (min/max)
- Wait queuing
- Resource validation
- Statistics tracking
"""

import asyncio
import hashlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)
from weakref import WeakValueDictionary

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class ResourceState(Enum):
    """Resource state."""
    IDLE = "idle"
    IN_USE = "in_use"
    EXPIRED = "expired"
    INVALID = "invalid"


class PoolState(Enum):
    """Pool state."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    DRAINING = "draining"
    CLOSED = "closed"


class AcquireStrategy(Enum):
    """Resource acquisition strategy."""
    FIFO = "fifo"
    LIFO = "lifo"
    RANDOM = "random"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ResourceWrapper(Generic[T]):
    """Wrapper for pooled resources."""
    resource: T
    resource_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    state: ResourceState = ResourceState.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_used(self) -> None:
        """Mark resource as in use."""
        self.state = ResourceState.IN_USE
        self.last_used = time.time()
        self.use_count += 1

    def mark_idle(self) -> None:
        """Mark resource as idle."""
        self.state = ResourceState.IDLE

    def mark_expired(self) -> None:
        """Mark resource as expired."""
        self.state = ResourceState.EXPIRED

    def mark_invalid(self) -> None:
        """Mark resource as invalid."""
        self.state = ResourceState.INVALID

    def age(self) -> float:
        """Get resource age in seconds."""
        return time.time() - self.created_at

    def idle_time(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self.last_used


@dataclass
class PoolConfig:
    """Pool configuration."""
    min_size: int = 0
    max_size: int = 10
    max_idle_time: float = 300.0  # 5 minutes
    max_lifetime: float = 3600.0  # 1 hour
    max_use_count: int = 0  # 0 = unlimited
    acquire_timeout: float = 30.0
    validation_interval: float = 60.0
    acquire_strategy: AcquireStrategy = AcquireStrategy.FIFO
    health_check_enabled: bool = True

    def __post_init__(self):
        if self.min_size > self.max_size:
            raise ValueError("min_size cannot be greater than max_size")


@dataclass
class PoolStats:
    """Pool statistics."""
    total_created: int = 0
    total_destroyed: int = 0
    total_acquired: int = 0
    total_released: int = 0
    current_size: int = 0
    idle_count: int = 0
    in_use_count: int = 0
    wait_count: int = 0
    failed_acquisitions: int = 0
    failed_validations: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "total_created": self.total_created,
            "total_destroyed": self.total_destroyed,
            "total_acquired": self.total_acquired,
            "total_released": self.total_released,
            "current_size": self.current_size,
            "idle_count": self.idle_count,
            "in_use_count": self.in_use_count,
            "wait_count": self.wait_count,
            "failed_acquisitions": self.failed_acquisitions,
            "failed_validations": self.failed_validations
        }


# =============================================================================
# RESOURCE FACTORY
# =============================================================================

class ResourceFactory(ABC, Generic[T]):
    """Abstract factory for creating resources."""

    @abstractmethod
    async def create(self) -> T:
        """Create a new resource."""
        pass

    @abstractmethod
    async def destroy(self, resource: T) -> None:
        """Destroy a resource."""
        pass

    async def validate(self, resource: T) -> bool:
        """Validate a resource is still usable."""
        return True

    async def reset(self, resource: T) -> bool:
        """Reset a resource before returning to pool."""
        return True


class SimpleFactory(ResourceFactory[T]):
    """Simple factory using callables."""

    def __init__(
        self,
        create_func: Callable[[], Awaitable[T]],
        destroy_func: Callable[[T], Awaitable[None]] = None,
        validate_func: Callable[[T], Awaitable[bool]] = None,
        reset_func: Callable[[T], Awaitable[bool]] = None
    ):
        self._create = create_func
        self._destroy = destroy_func
        self._validate = validate_func
        self._reset = reset_func

    async def create(self) -> T:
        return await self._create()

    async def destroy(self, resource: T) -> None:
        if self._destroy:
            await self._destroy(resource)

    async def validate(self, resource: T) -> bool:
        if self._validate:
            return await self._validate(resource)
        return True

    async def reset(self, resource: T) -> bool:
        if self._reset:
            return await self._reset(resource)
        return True


# =============================================================================
# RESOURCE POOL
# =============================================================================

class ResourcePool(Generic[T]):
    """
    Generic resource pool.
    """

    def __init__(
        self,
        factory: ResourceFactory[T],
        config: PoolConfig = None
    ):
        self.factory = factory
        self.config = config or PoolConfig()

        # Pool state
        self.state = PoolState.INITIALIZING
        self._lock = asyncio.Lock()

        # Resources
        self._resources: Dict[str, ResourceWrapper[T]] = {}
        self._idle: deque = deque()
        self._in_use: Set[str] = set()

        # Wait queue
        self._waiters: deque = deque()

        # Statistics
        self.stats = PoolStats()

        # Background tasks
        self._maintenance_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the pool."""
        async with self._lock:
            # Pre-create minimum resources
            for _ in range(self.config.min_size):
                await self._create_resource()

            self.state = PoolState.RUNNING

            # Start maintenance
            self._maintenance_task = asyncio.create_task(
                self._maintenance_loop()
            )

    async def _create_resource(self) -> ResourceWrapper[T]:
        """Create a new resource."""
        resource = await self.factory.create()
        wrapper = ResourceWrapper(resource=resource)

        self._resources[wrapper.resource_id] = wrapper
        self._idle.append(wrapper.resource_id)

        self.stats.total_created += 1
        self.stats.current_size += 1
        self.stats.idle_count += 1

        return wrapper

    async def _destroy_resource(self, resource_id: str) -> None:
        """Destroy a resource."""
        wrapper = self._resources.get(resource_id)
        if not wrapper:
            return

        try:
            await self.factory.destroy(wrapper.resource)
        except Exception as e:
            logger.error(f"Error destroying resource {resource_id}: {e}")

        # Clean up
        del self._resources[resource_id]

        if resource_id in self._idle:
            self._idle.remove(resource_id)
            self.stats.idle_count -= 1

        if resource_id in self._in_use:
            self._in_use.discard(resource_id)
            self.stats.in_use_count -= 1

        self.stats.total_destroyed += 1
        self.stats.current_size -= 1

    async def acquire(self, timeout: float = None) -> T:
        """Acquire a resource from the pool."""
        if self.state != PoolState.RUNNING:
            raise RuntimeError("Pool is not running")

        timeout = timeout or self.config.acquire_timeout
        start_time = time.time()

        while True:
            async with self._lock:
                # Try to get idle resource
                wrapper = await self._get_idle_resource()

                if wrapper:
                    wrapper.mark_used()
                    self._in_use.add(wrapper.resource_id)
                    self.stats.total_acquired += 1
                    self.stats.in_use_count += 1
                    return wrapper.resource

                # Try to create new resource if under limit
                if self.stats.current_size < self.config.max_size:
                    wrapper = await self._create_resource()
                    wrapper.mark_used()

                    self._idle.remove(wrapper.resource_id)
                    self.stats.idle_count -= 1

                    self._in_use.add(wrapper.resource_id)
                    self.stats.total_acquired += 1
                    self.stats.in_use_count += 1

                    return wrapper.resource

            # Wait for available resource
            elapsed = time.time() - start_time
            remaining = timeout - elapsed

            if remaining <= 0:
                self.stats.failed_acquisitions += 1
                raise TimeoutError("Timeout waiting for resource")

            # Create waiter
            waiter = asyncio.Event()
            self._waiters.append(waiter)
            self.stats.wait_count += 1

            try:
                await asyncio.wait_for(waiter.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                self._waiters.remove(waiter)
                self.stats.wait_count -= 1
                self.stats.failed_acquisitions += 1
                raise TimeoutError("Timeout waiting for resource")
            finally:
                if waiter in self._waiters:
                    self._waiters.remove(waiter)
                    self.stats.wait_count -= 1

    async def _get_idle_resource(self) -> Optional[ResourceWrapper[T]]:
        """Get an idle resource."""
        while self._idle:
            if self.config.acquire_strategy == AcquireStrategy.LIFO:
                resource_id = self._idle.pop()
            else:  # FIFO
                resource_id = self._idle.popleft()

            self.stats.idle_count -= 1

            wrapper = self._resources.get(resource_id)
            if not wrapper:
                continue

            # Check validity
            if await self._is_resource_valid(wrapper):
                return wrapper

            # Invalid resource, destroy it
            await self._destroy_resource(resource_id)

        return None

    async def _is_resource_valid(self, wrapper: ResourceWrapper[T]) -> bool:
        """Check if resource is valid."""
        # Check lifetime
        if wrapper.age() > self.config.max_lifetime:
            wrapper.mark_expired()
            return False

        # Check use count
        if self.config.max_use_count > 0:
            if wrapper.use_count >= self.config.max_use_count:
                wrapper.mark_expired()
                return False

        # Health check
        if self.config.health_check_enabled:
            try:
                if not await self.factory.validate(wrapper.resource):
                    wrapper.mark_invalid()
                    self.stats.failed_validations += 1
                    return False
            except Exception as e:
                logger.error(f"Validation error: {e}")
                wrapper.mark_invalid()
                self.stats.failed_validations += 1
                return False

        return True

    async def release(self, resource: T) -> None:
        """Release a resource back to the pool."""
        async with self._lock:
            # Find wrapper
            wrapper = None
            for w in self._resources.values():
                if w.resource is resource:
                    wrapper = w
                    break

            if not wrapper:
                logger.warning("Releasing unknown resource")
                return

            # Remove from in-use
            self._in_use.discard(wrapper.resource_id)
            self.stats.in_use_count -= 1
            self.stats.total_released += 1

            # Check if still valid
            if wrapper.state in (ResourceState.EXPIRED, ResourceState.INVALID):
                await self._destroy_resource(wrapper.resource_id)
                return

            # Reset resource
            try:
                if not await self.factory.reset(wrapper.resource):
                    await self._destroy_resource(wrapper.resource_id)
                    return
            except Exception as e:
                logger.error(f"Reset error: {e}")
                await self._destroy_resource(wrapper.resource_id)
                return

            # Return to idle pool
            wrapper.mark_idle()
            self._idle.append(wrapper.resource_id)
            self.stats.idle_count += 1

            # Notify waiters
            if self._waiters:
                waiter = self._waiters.popleft()
                self.stats.wait_count -= 1
                waiter.set()

    async def _maintenance_loop(self) -> None:
        """Background maintenance loop."""
        while self.state == PoolState.RUNNING:
            try:
                await asyncio.sleep(self.config.validation_interval)
                await self._perform_maintenance()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance error: {e}")

    async def _perform_maintenance(self) -> None:
        """Perform maintenance tasks."""
        async with self._lock:
            # Remove expired idle resources
            to_remove = []

            for resource_id in list(self._idle):
                wrapper = self._resources.get(resource_id)
                if not wrapper:
                    continue

                # Check idle timeout
                if wrapper.idle_time() > self.config.max_idle_time:
                    if self.stats.current_size > self.config.min_size:
                        to_remove.append(resource_id)
                        continue

                # Check lifetime
                if wrapper.age() > self.config.max_lifetime:
                    to_remove.append(resource_id)

            for resource_id in to_remove:
                await self._destroy_resource(resource_id)

            # Create resources to meet minimum
            while self.stats.current_size < self.config.min_size:
                await self._create_resource()

    async def close(self) -> None:
        """Close the pool."""
        self.state = PoolState.DRAINING

        # Cancel maintenance
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        # Destroy all resources
        async with self._lock:
            for resource_id in list(self._resources.keys()):
                await self._destroy_resource(resource_id)

            # Clear waiters
            for waiter in self._waiters:
                waiter.set()
            self._waiters.clear()

        self.state = PoolState.CLOSED

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "state": self.state.value,
            **self.stats.to_dict()
        }

    # Context manager support
    async def __aenter__(self) -> T:
        return await self.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # Note: This requires the resource to be tracked
        pass


# =============================================================================
# POOLED CONTEXT MANAGER
# =============================================================================

class PooledResource(Generic[T]):
    """Context manager for pooled resources."""

    def __init__(self, pool: ResourcePool[T]):
        self.pool = pool
        self.resource: Optional[T] = None

    async def __aenter__(self) -> T:
        self.resource = await self.pool.acquire()
        return self.resource

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.resource is not None:
            await self.pool.release(self.resource)
            self.resource = None


# =============================================================================
# CONNECTION POOL
# =============================================================================

class ConnectionPool(ResourcePool[T]):
    """Specialized pool for database connections."""

    def connection(self) -> PooledResource[T]:
        """Get a connection context manager."""
        return PooledResource(self)


# =============================================================================
# OBJECT POOL
# =============================================================================

class ObjectPool(ResourcePool[T]):
    """Pool for reusable objects."""

    def get(self) -> PooledResource[T]:
        """Get an object context manager."""
        return PooledResource(self)


# =============================================================================
# POOL MANAGER
# =============================================================================

class PoolManager:
    """
    Manages multiple resource pools.
    """

    def __init__(self):
        self.pools: Dict[str, ResourcePool] = {}
        self._lock = asyncio.Lock()

    async def create_pool(
        self,
        name: str,
        factory: ResourceFactory[T],
        config: PoolConfig = None
    ) -> ResourcePool[T]:
        """Create and register a pool."""
        async with self._lock:
            if name in self.pools:
                raise ValueError(f"Pool '{name}' already exists")

            pool = ResourcePool(factory, config)
            await pool.initialize()
            self.pools[name] = pool

            return pool

    async def create_connection_pool(
        self,
        name: str,
        factory: ResourceFactory[T],
        config: PoolConfig = None
    ) -> ConnectionPool[T]:
        """Create a connection pool."""
        async with self._lock:
            if name in self.pools:
                raise ValueError(f"Pool '{name}' already exists")

            pool = ConnectionPool(factory, config)
            await pool.initialize()
            self.pools[name] = pool

            return pool

    def get_pool(self, name: str) -> Optional[ResourcePool]:
        """Get a pool by name."""
        return self.pools.get(name)

    async def close_pool(self, name: str) -> bool:
        """Close a pool."""
        async with self._lock:
            pool = self.pools.get(name)
            if not pool:
                return False

            await pool.close()
            del self.pools[name]
            return True

    async def close_all(self) -> None:
        """Close all pools."""
        async with self._lock:
            for pool in self.pools.values():
                await pool.close()
            self.pools.clear()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all pools."""
        return {name: pool.get_stats() for name, pool in self.pools.items()}


# =============================================================================
# RESOURCE POOL MANAGER
# =============================================================================

class ResourcePoolManager:
    """
    Master resource pool manager for BAEL.
    """

    def __init__(self):
        self.manager = PoolManager()

    async def create_pool(
        self,
        name: str,
        create_func: Callable[[], Awaitable[T]],
        destroy_func: Callable[[T], Awaitable[None]] = None,
        validate_func: Callable[[T], Awaitable[bool]] = None,
        reset_func: Callable[[T], Awaitable[bool]] = None,
        config: PoolConfig = None
    ) -> ResourcePool[T]:
        """Create a resource pool with simple functions."""
        factory = SimpleFactory(
            create_func=create_func,
            destroy_func=destroy_func,
            validate_func=validate_func,
            reset_func=reset_func
        )
        return await self.manager.create_pool(name, factory, config)

    async def create_connection_pool(
        self,
        name: str,
        create_func: Callable[[], Awaitable[T]],
        destroy_func: Callable[[T], Awaitable[None]] = None,
        validate_func: Callable[[T], Awaitable[bool]] = None,
        config: PoolConfig = None
    ) -> ConnectionPool[T]:
        """Create a connection pool."""
        factory = SimpleFactory(
            create_func=create_func,
            destroy_func=destroy_func,
            validate_func=validate_func
        )
        return await self.manager.create_connection_pool(name, factory, config)

    def get_pool(self, name: str) -> Optional[ResourcePool]:
        """Get a pool."""
        return self.manager.get_pool(name)

    async def close_pool(self, name: str) -> bool:
        """Close a pool."""
        return await self.manager.close_pool(name)

    async def close_all(self) -> None:
        """Close all pools."""
        await self.manager.close_all()

    def get_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get all statistics."""
        return self.manager.get_all_stats()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Resource Pool Manager."""
    print("=" * 70)
    print("BAEL - RESOURCE POOL MANAGER DEMO")
    print("Efficient Resource Pooling System")
    print("=" * 70)
    print()

    manager = ResourcePoolManager()

    # 1. Simple Object Pool
    print("1. SIMPLE OBJECT POOL:")
    print("-" * 40)

    counter = {"value": 0}

    async def create_worker():
        counter["value"] += 1
        return {"id": counter["value"], "status": "ready"}

    async def destroy_worker(worker):
        print(f"   Destroyed worker {worker['id']}")

    async def validate_worker(worker):
        return worker["status"] == "ready"

    pool = await manager.create_pool(
        "workers",
        create_func=create_worker,
        destroy_func=destroy_worker,
        validate_func=validate_worker,
        config=PoolConfig(min_size=2, max_size=5)
    )

    print(f"   Pool created with {pool.stats.current_size} workers")
    print()

    # 2. Acquire and Release
    print("2. ACQUIRE AND RELEASE:")
    print("-" * 40)

    worker1 = await pool.acquire()
    print(f"   Acquired worker: {worker1}")

    worker2 = await pool.acquire()
    print(f"   Acquired worker: {worker2}")

    stats = pool.get_stats()
    print(f"   In use: {stats['in_use_count']}, Idle: {stats['idle_count']}")

    await pool.release(worker1)
    print(f"   Released worker {worker1['id']}")

    stats = pool.get_stats()
    print(f"   In use: {stats['in_use_count']}, Idle: {stats['idle_count']}")

    await pool.release(worker2)
    print()

    # 3. Context Manager
    print("3. CONTEXT MANAGER:")
    print("-" * 40)

    pooled = PooledResource(pool)
    async with pooled as worker:
        print(f"   Using worker: {worker}")
        worker["status"] = "working"

    print("   Worker returned to pool")
    stats = pool.get_stats()
    print(f"   Total acquired: {stats['total_acquired']}")
    print()

    # 4. Multiple Concurrent Acquisitions
    print("4. CONCURRENT ACQUISITIONS:")
    print("-" * 40)

    async def use_worker(duration: float):
        w = await pool.acquire()
        print(f"   Worker {w['id']} acquired for {duration}s task")
        await asyncio.sleep(duration)
        await pool.release(w)
        print(f"   Worker {w['id']} released")

    tasks = [
        use_worker(0.1),
        use_worker(0.2),
        use_worker(0.15)
    ]

    await asyncio.gather(*tasks)
    print()

    # 5. Connection Pool
    print("5. CONNECTION POOL:")
    print("-" * 40)

    connection_counter = {"value": 0}

    async def create_connection():
        connection_counter["value"] += 1
        return {"conn_id": connection_counter["value"], "connected": True}

    async def close_connection(conn):
        conn["connected"] = False
        print(f"   Closed connection {conn['conn_id']}")

    async def ping_connection(conn):
        return conn["connected"]

    conn_pool = await manager.create_connection_pool(
        "database",
        create_func=create_connection,
        destroy_func=close_connection,
        validate_func=ping_connection,
        config=PoolConfig(min_size=1, max_size=3)
    )

    async with conn_pool.connection() as conn:
        print(f"   Using connection: {conn}")

    print("   Connection returned")
    print()

    # 6. Pool Exhaustion
    print("6. POOL EXHAUSTION:")
    print("-" * 40)

    # Create a small pool
    small_counter = {"value": 0}

    async def create_small():
        small_counter["value"] += 1
        return f"resource_{small_counter['value']}"

    small_pool = await manager.create_pool(
        "small",
        create_func=create_small,
        config=PoolConfig(
            min_size=1,
            max_size=2,
            acquire_timeout=1.0
        )
    )

    # Acquire all resources
    r1 = await small_pool.acquire()
    r2 = await small_pool.acquire()

    print(f"   Acquired: {r1}, {r2}")
    print("   Pool exhausted, waiting for timeout...")

    try:
        await small_pool.acquire()
    except TimeoutError:
        print("   ✓ Timeout as expected")

    await small_pool.release(r1)
    await small_pool.release(r2)
    print()

    # 7. Pool Statistics
    print("7. POOL STATISTICS:")
    print("-" * 40)

    all_stats = manager.get_statistics()
    for pool_name, stats in all_stats.items():
        print(f"   {pool_name}:")
        print(f"     State: {stats['state']}")
        print(f"     Size: {stats['current_size']}")
        print(f"     Created: {stats['total_created']}")
        print(f"     Acquired: {stats['total_acquired']}")
    print()

    # 8. Resource Lifecycle
    print("8. RESOURCE LIFECYCLE:")
    print("-" * 40)

    lifecycle_counter = {"created": 0, "destroyed": 0, "validated": 0, "reset": 0}

    async def create_tracked():
        lifecycle_counter["created"] += 1
        return {"id": lifecycle_counter["created"]}

    async def destroy_tracked(r):
        lifecycle_counter["destroyed"] += 1

    async def validate_tracked(r):
        lifecycle_counter["validated"] += 1
        return True

    async def reset_tracked(r):
        lifecycle_counter["reset"] += 1
        return True

    lifecycle_pool = await manager.create_pool(
        "lifecycle",
        create_func=create_tracked,
        destroy_func=destroy_tracked,
        validate_func=validate_tracked,
        reset_func=reset_tracked,
        config=PoolConfig(min_size=1, max_size=3)
    )

    # Use resources
    for _ in range(3):
        r = await lifecycle_pool.acquire()
        await lifecycle_pool.release(r)

    print(f"   Created: {lifecycle_counter['created']}")
    print(f"   Validated: {lifecycle_counter['validated']}")
    print(f"   Reset: {lifecycle_counter['reset']}")
    print(f"   Destroyed: {lifecycle_counter['destroyed']}")
    print()

    # 9. Close Pools
    print("9. CLOSE POOLS:")
    print("-" * 40)

    await manager.close_pool("workers")
    print("   ✓ Closed 'workers' pool")

    await manager.close_all()
    print("   ✓ Closed all remaining pools")
    print()

    # 10. Final Summary
    print("10. FINAL SUMMARY:")
    print("-" * 40)

    print("   Resource pooling features demonstrated:")
    print("   ✓ Generic resource pooling")
    print("   ✓ Connection pooling")
    print("   ✓ Resource lifecycle management")
    print("   ✓ Health checking")
    print("   ✓ Pool sizing (min/max)")
    print("   ✓ Timeout handling")
    print("   ✓ Statistics tracking")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Resource Pool Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
