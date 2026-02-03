#!/usr/bin/env python3
"""
BAEL - Pooling Engine
Resource pooling for agents.

Features:
- Connection pooling
- Object pooling
- Resource lifecycle
- Pool sizing
- Health monitoring
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Coroutine, Dict, Generic, List, Optional, Set, Tuple,
    Type, TypeVar
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PoolState(Enum):
    """Pool states."""
    INITIALIZING = "initializing"
    READY = "ready"
    DRAINING = "draining"
    CLOSED = "closed"


class ResourceState(Enum):
    """Resource states."""
    IDLE = "idle"
    ACQUIRED = "acquired"
    VALIDATING = "validating"
    INVALID = "invalid"
    EXPIRED = "expired"


class AcquisitionStrategy(Enum):
    """Acquisition strategies."""
    FIFO = "fifo"
    LIFO = "lifo"
    RANDOM = "random"


class SizingStrategy(Enum):
    """Pool sizing strategies."""
    FIXED = "fixed"
    ELASTIC = "elastic"
    ADAPTIVE = "adaptive"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PoolConfig:
    """Pool configuration."""
    min_size: int = 5
    max_size: int = 20
    initial_size: int = 5
    acquisition_timeout_seconds: float = 30.0
    idle_timeout_seconds: float = 300.0
    max_lifetime_seconds: float = 3600.0
    validation_interval_seconds: float = 60.0
    acquisition_strategy: AcquisitionStrategy = AcquisitionStrategy.FIFO
    sizing_strategy: SizingStrategy = SizingStrategy.ELASTIC
    validation_on_acquire: bool = True
    validation_on_return: bool = False


@dataclass
class ResourceInfo(Generic[T]):
    """Resource information."""
    resource_id: str = ""
    resource: Optional[T] = None
    state: ResourceState = ResourceState.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    last_validated_at: Optional[datetime] = None
    acquisition_count: int = 0
    
    def __post_init__(self):
        if not self.resource_id:
            self.resource_id = str(uuid.uuid4())[:8]
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        if not self.last_used_at:
            return self.age_seconds
        return (datetime.now() - self.last_used_at).total_seconds()
    
    def is_expired(self, max_lifetime: float) -> bool:
        return self.age_seconds > max_lifetime
    
    def is_idle_timeout(self, idle_timeout: float) -> bool:
        return self.idle_seconds > idle_timeout


@dataclass
class PoolStats:
    """Pool statistics."""
    total_created: int = 0
    total_destroyed: int = 0
    total_acquired: int = 0
    total_returned: int = 0
    total_timeouts: int = 0
    total_validations: int = 0
    total_validation_failures: int = 0
    current_size: int = 0
    current_idle: int = 0
    current_acquired: int = 0
    peak_size: int = 0
    peak_acquired: int = 0
    
    @property
    def utilization(self) -> float:
        if self.current_size == 0:
            return 0.0
        return self.current_acquired / self.current_size


@dataclass
class AcquisitionResult(Generic[T]):
    """Acquisition result."""
    success: bool = True
    resource: Optional[T] = None
    resource_id: str = ""
    wait_time_seconds: float = 0.0
    error: Optional[str] = None


# =============================================================================
# RESOURCE FACTORY
# =============================================================================

class ResourceFactory(Generic[T], ABC):
    """Factory for creating resources."""
    
    @abstractmethod
    async def create(self) -> T:
        """Create a new resource."""
        pass
    
    @abstractmethod
    async def destroy(self, resource: T) -> None:
        """Destroy a resource."""
        pass
    
    @abstractmethod
    async def validate(self, resource: T) -> bool:
        """Validate a resource."""
        pass
    
    async def reset(self, resource: T) -> T:
        """Reset resource for reuse."""
        return resource


class SimpleFactory(ResourceFactory[Dict]):
    """Simple dictionary resource factory."""
    
    def __init__(self, initializer: Optional[Callable[[], Dict]] = None):
        self._initializer = initializer or (lambda: {})
        self._counter = 0
    
    async def create(self) -> Dict:
        self._counter += 1
        resource = self._initializer()
        resource["_id"] = self._counter
        resource["_created"] = datetime.now().isoformat()
        return resource
    
    async def destroy(self, resource: Dict) -> None:
        resource.clear()
    
    async def validate(self, resource: Dict) -> bool:
        return "_id" in resource
    
    async def reset(self, resource: Dict) -> Dict:
        keys_to_remove = [k for k in resource if not k.startswith("_")]
        for k in keys_to_remove:
            del resource[k]
        return resource


class CallableFactory(ResourceFactory[T]):
    """Factory using callable functions."""
    
    def __init__(
        self,
        creator: Callable[[], Coroutine[Any, Any, T]],
        destroyer: Optional[Callable[[T], Coroutine]] = None,
        validator: Optional[Callable[[T], Coroutine[Any, Any, bool]]] = None,
        resetter: Optional[Callable[[T], Coroutine[Any, Any, T]]] = None
    ):
        self._creator = creator
        self._destroyer = destroyer
        self._validator = validator
        self._resetter = resetter
    
    async def create(self) -> T:
        return await self._creator()
    
    async def destroy(self, resource: T) -> None:
        if self._destroyer:
            await self._destroyer(resource)
    
    async def validate(self, resource: T) -> bool:
        if self._validator:
            return await self._validator(resource)
        return True
    
    async def reset(self, resource: T) -> T:
        if self._resetter:
            return await self._resetter(resource)
        return resource


# =============================================================================
# RESOURCE POOL
# =============================================================================

class ResourcePool(Generic[T]):
    """Generic resource pool."""
    
    def __init__(
        self,
        name: str,
        factory: ResourceFactory[T],
        config: Optional[PoolConfig] = None
    ):
        self._name = name
        self._factory = factory
        self._config = config or PoolConfig()
        
        self._state = PoolState.INITIALIZING
        self._stats = PoolStats()
        
        self._idle: deque = deque()
        self._acquired: Dict[str, ResourceInfo[T]] = {}
        self._all_resources: Dict[str, ResourceInfo[T]] = {}
        
        self._lock = asyncio.Lock()
        self._available = asyncio.Semaphore(0)
        
        self._maintenance_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize pool with initial resources."""
        for _ in range(self._config.initial_size):
            await self._create_resource()
        
        self._state = PoolState.READY
        self._start_maintenance()
    
    async def _create_resource(self) -> ResourceInfo[T]:
        """Create a new resource."""
        resource = await self._factory.create()
        
        info = ResourceInfo(
            resource=resource,
            state=ResourceState.IDLE
        )
        
        self._all_resources[info.resource_id] = info
        self._idle.append(info.resource_id)
        self._available.release()
        
        self._stats.total_created += 1
        self._stats.current_size += 1
        self._stats.current_idle += 1
        self._stats.peak_size = max(
            self._stats.peak_size,
            self._stats.current_size
        )
        
        return info
    
    async def _destroy_resource(self, resource_id: str) -> None:
        """Destroy a resource."""
        info = self._all_resources.pop(resource_id, None)
        
        if info and info.resource:
            await self._factory.destroy(info.resource)
        
        self._stats.total_destroyed += 1
        self._stats.current_size -= 1
    
    async def acquire(
        self,
        timeout: Optional[float] = None
    ) -> AcquisitionResult[T]:
        """Acquire a resource from pool."""
        if self._state != PoolState.READY:
            return AcquisitionResult(
                success=False,
                error="Pool is not ready"
            )
        
        timeout = timeout or self._config.acquisition_timeout_seconds
        start = time.time()
        
        async with self._lock:
            if not self._idle and self._stats.current_size < self._config.max_size:
                await self._create_resource()
        
        try:
            await asyncio.wait_for(
                self._available.acquire(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self._stats.total_timeouts += 1
            return AcquisitionResult(
                success=False,
                wait_time_seconds=time.time() - start,
                error="Acquisition timeout"
            )
        
        async with self._lock:
            if not self._idle:
                return AcquisitionResult(
                    success=False,
                    wait_time_seconds=time.time() - start,
                    error="No resources available"
                )
            
            if self._config.acquisition_strategy == AcquisitionStrategy.LIFO:
                resource_id = self._idle.pop()
            else:
                resource_id = self._idle.popleft()
            
            info = self._all_resources.get(resource_id)
            
            if not info:
                return AcquisitionResult(
                    success=False,
                    error="Resource not found"
                )
            
            if self._config.validation_on_acquire:
                is_valid = await self._validate_resource(info)
                if not is_valid:
                    await self._destroy_resource(resource_id)
                    return await self.acquire(timeout - (time.time() - start))
            
            info.state = ResourceState.ACQUIRED
            info.last_used_at = datetime.now()
            info.acquisition_count += 1
            
            self._acquired[resource_id] = info
            
            self._stats.total_acquired += 1
            self._stats.current_idle -= 1
            self._stats.current_acquired += 1
            self._stats.peak_acquired = max(
                self._stats.peak_acquired,
                self._stats.current_acquired
            )
            
            return AcquisitionResult(
                success=True,
                resource=info.resource,
                resource_id=resource_id,
                wait_time_seconds=time.time() - start
            )
    
    async def release(self, resource_id: str) -> bool:
        """Release a resource back to pool."""
        async with self._lock:
            info = self._acquired.pop(resource_id, None)
            
            if not info:
                return False
            
            if self._config.validation_on_return:
                is_valid = await self._validate_resource(info)
                if not is_valid:
                    await self._destroy_resource(resource_id)
                    return True
            
            if info.resource:
                info.resource = await self._factory.reset(info.resource)
            
            if info.is_expired(self._config.max_lifetime_seconds):
                await self._destroy_resource(resource_id)
            else:
                info.state = ResourceState.IDLE
                info.last_used_at = datetime.now()
                self._idle.append(resource_id)
                self._available.release()
                
                self._stats.current_idle += 1
            
            self._stats.total_returned += 1
            self._stats.current_acquired -= 1
            
            return True
    
    async def _validate_resource(self, info: ResourceInfo[T]) -> bool:
        """Validate a resource."""
        self._stats.total_validations += 1
        
        info.state = ResourceState.VALIDATING
        info.last_validated_at = datetime.now()
        
        try:
            is_valid = await self._factory.validate(info.resource)
            
            if not is_valid:
                info.state = ResourceState.INVALID
                self._stats.total_validation_failures += 1
            
            return is_valid
        
        except Exception:
            info.state = ResourceState.INVALID
            self._stats.total_validation_failures += 1
            return False
    
    def _start_maintenance(self) -> None:
        """Start maintenance task."""
        async def maintenance():
            while self._state == PoolState.READY:
                await asyncio.sleep(self._config.validation_interval_seconds)
                await self._run_maintenance()
        
        self._maintenance_task = asyncio.create_task(maintenance())
    
    async def _run_maintenance(self) -> None:
        """Run maintenance tasks."""
        async with self._lock:
            to_remove = []
            
            for resource_id in list(self._idle):
                info = self._all_resources.get(resource_id)
                if not info:
                    continue
                
                if info.is_expired(self._config.max_lifetime_seconds):
                    to_remove.append(resource_id)
                elif info.is_idle_timeout(self._config.idle_timeout_seconds):
                    if self._stats.current_size > self._config.min_size:
                        to_remove.append(resource_id)
            
            for resource_id in to_remove:
                if resource_id in self._idle:
                    self._idle.remove(resource_id)
                    try:
                        self._available.acquire_nowait()
                    except:
                        pass
                    self._stats.current_idle -= 1
                    await self._destroy_resource(resource_id)
            
            while self._stats.current_size < self._config.min_size:
                await self._create_resource()
    
    async def close(self) -> None:
        """Close the pool."""
        self._state = PoolState.DRAINING
        
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            for resource_id in list(self._all_resources.keys()):
                await self._destroy_resource(resource_id)
            
            self._idle.clear()
            self._acquired.clear()
        
        self._state = PoolState.CLOSED
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def state(self) -> PoolState:
        return self._state
    
    @property
    def stats(self) -> PoolStats:
        return self._stats
    
    def size(self) -> int:
        return self._stats.current_size
    
    def idle_count(self) -> int:
        return self._stats.current_idle
    
    def acquired_count(self) -> int:
        return self._stats.current_acquired


# =============================================================================
# POOL MANAGER
# =============================================================================

class PoolManager:
    """Manage multiple pools."""
    
    def __init__(self):
        self._pools: Dict[str, ResourcePool] = {}
    
    async def create(
        self,
        name: str,
        factory: ResourceFactory,
        config: Optional[PoolConfig] = None
    ) -> ResourcePool:
        """Create a new pool."""
        pool = ResourcePool(name, factory, config)
        await pool.initialize()
        self._pools[name] = pool
        return pool
    
    def get(self, name: str) -> Optional[ResourcePool]:
        """Get a pool."""
        return self._pools.get(name)
    
    async def remove(self, name: str) -> bool:
        """Remove a pool."""
        pool = self._pools.pop(name, None)
        if pool:
            await pool.close()
            return True
        return False
    
    def list_pools(self) -> List[str]:
        """List pool names."""
        return list(self._pools.keys())
    
    async def close_all(self) -> None:
        """Close all pools."""
        for pool in self._pools.values():
            await pool.close()
        self._pools.clear()
    
    def stats(self) -> Dict[str, PoolStats]:
        """Get all pool stats."""
        return {
            name: pool.stats
            for name, pool in self._pools.items()
        }


# =============================================================================
# POOLING ENGINE
# =============================================================================

class PoolingEngine:
    """
    Pooling Engine for BAEL.
    
    Resource pooling for agents.
    """
    
    def __init__(self, default_config: Optional[PoolConfig] = None):
        self._default_config = default_config or PoolConfig()
        self._manager = PoolManager()
        
        self._active_acquisitions: Dict[str, str] = {}
    
    # ----- Pool Creation -----
    
    async def create_pool(
        self,
        name: str,
        factory: ResourceFactory,
        config: Optional[PoolConfig] = None
    ) -> ResourcePool:
        """Create a resource pool."""
        config = config or self._default_config
        return await self._manager.create(name, factory, config)
    
    async def create_simple_pool(
        self,
        name: str,
        initializer: Optional[Callable[[], Dict]] = None,
        config: Optional[PoolConfig] = None
    ) -> ResourcePool:
        """Create a simple dictionary pool."""
        factory = SimpleFactory(initializer)
        return await self.create_pool(name, factory, config)
    
    async def create_callable_pool(
        self,
        name: str,
        creator: Callable[[], Coroutine],
        destroyer: Optional[Callable] = None,
        validator: Optional[Callable] = None,
        config: Optional[PoolConfig] = None
    ) -> ResourcePool:
        """Create pool with callable factory."""
        factory = CallableFactory(creator, destroyer, validator)
        return await self.create_pool(name, factory, config)
    
    def get_pool(self, name: str) -> Optional[ResourcePool]:
        """Get a pool."""
        return self._manager.get(name)
    
    async def remove_pool(self, name: str) -> bool:
        """Remove a pool."""
        return await self._manager.remove(name)
    
    def list_pools(self) -> List[str]:
        """List pools."""
        return self._manager.list_pools()
    
    # ----- Resource Operations -----
    
    async def acquire(
        self,
        pool_name: str,
        timeout: Optional[float] = None
    ) -> AcquisitionResult:
        """Acquire resource from pool."""
        pool = self._manager.get(pool_name)
        
        if not pool:
            return AcquisitionResult(
                success=False,
                error=f"Pool '{pool_name}' not found"
            )
        
        result = await pool.acquire(timeout)
        
        if result.success:
            self._active_acquisitions[result.resource_id] = pool_name
        
        return result
    
    async def release(self, resource_id: str) -> bool:
        """Release resource back to pool."""
        pool_name = self._active_acquisitions.pop(resource_id, None)
        
        if not pool_name:
            return False
        
        pool = self._manager.get(pool_name)
        
        if pool:
            return await pool.release(resource_id)
        
        return False
    
    async def with_resource(
        self,
        pool_name: str,
        func: Callable[[Any], Coroutine],
        timeout: Optional[float] = None
    ) -> Any:
        """Execute function with acquired resource."""
        result = await self.acquire(pool_name, timeout)
        
        if not result.success:
            raise Exception(result.error)
        
        try:
            return await func(result.resource)
        finally:
            await self.release(result.resource_id)
    
    # ----- Pool Information -----
    
    def pool_size(self, name: str) -> int:
        """Get pool size."""
        pool = self._manager.get(name)
        return pool.size() if pool else 0
    
    def pool_idle(self, name: str) -> int:
        """Get idle count."""
        pool = self._manager.get(name)
        return pool.idle_count() if pool else 0
    
    def pool_acquired(self, name: str) -> int:
        """Get acquired count."""
        pool = self._manager.get(name)
        return pool.acquired_count() if pool else 0
    
    def pool_state(self, name: str) -> Optional[PoolState]:
        """Get pool state."""
        pool = self._manager.get(name)
        return pool.state if pool else None
    
    def pool_stats(self, name: str) -> Optional[PoolStats]:
        """Get pool stats."""
        pool = self._manager.get(name)
        return pool.stats if pool else None
    
    # ----- Engine Statistics -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        all_stats = self._manager.stats()
        
        total_size = sum(s.current_size for s in all_stats.values())
        total_acquired = sum(s.current_acquired for s in all_stats.values())
        total_idle = sum(s.current_idle for s in all_stats.values())
        
        return {
            "pools": len(self.list_pools()),
            "total_size": total_size,
            "total_acquired": total_acquired,
            "total_idle": total_idle,
            "active_acquisitions": len(self._active_acquisitions)
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        pool_info = {}
        
        for name in self.list_pools():
            pool = self.get_pool(name)
            if pool:
                pool_info[name] = {
                    "state": pool.state.value,
                    "size": pool.size(),
                    "idle": pool.idle_count(),
                    "acquired": pool.acquired_count(),
                    "utilization": f"{pool.stats.utilization:.2%}"
                }
        
        return {
            "pools": pool_info,
            "active_acquisitions": len(self._active_acquisitions)
        }
    
    async def close(self) -> None:
        """Close all pools."""
        await self._manager.close_all()
        self._active_acquisitions.clear()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Pooling Engine."""
    print("=" * 70)
    print("BAEL - POOLING ENGINE DEMO")
    print("Resource Pooling for Agents")
    print("=" * 70)
    print()
    
    engine = PoolingEngine()
    
    # 1. Create Simple Pool
    print("1. CREATE SIMPLE POOL:")
    print("-" * 40)
    
    pool = await engine.create_simple_pool(
        "connections",
        initializer=lambda: {"connected": True},
        config=PoolConfig(
            min_size=2,
            max_size=10,
            initial_size=3
        )
    )
    
    print(f"   Created: {pool.name}")
    print(f"   State: {pool.state.value}")
    print(f"   Size: {pool.size()}")
    print(f"   Idle: {pool.idle_count()}")
    print()
    
    # 2. Acquire Resource
    print("2. ACQUIRE RESOURCE:")
    print("-" * 40)
    
    result = await engine.acquire("connections")
    print(f"   Success: {result.success}")
    print(f"   Resource ID: {result.resource_id}")
    print(f"   Resource: {result.resource}")
    print(f"   Wait time: {result.wait_time_seconds:.4f}s")
    print()
    
    # 3. Release Resource
    print("3. RELEASE RESOURCE:")
    print("-" * 40)
    
    print(f"   Before release - Acquired: {engine.pool_acquired('connections')}")
    
    released = await engine.release(result.resource_id)
    print(f"   Released: {released}")
    print(f"   After release - Acquired: {engine.pool_acquired('connections')}")
    print()
    
    # 4. Multiple Acquisitions
    print("4. MULTIPLE ACQUISITIONS:")
    print("-" * 40)
    
    resources = []
    for i in range(3):
        r = await engine.acquire("connections")
        resources.append(r)
        print(f"   Acquired {i+1}: {r.resource_id}")
    
    print(f"   Pool size: {engine.pool_size('connections')}")
    print(f"   Acquired: {engine.pool_acquired('connections')}")
    print(f"   Idle: {engine.pool_idle('connections')}")
    
    for r in resources:
        await engine.release(r.resource_id)
    print(f"   After release - Idle: {engine.pool_idle('connections')}")
    print()
    
    # 5. With Resource Context
    print("5. WITH RESOURCE CONTEXT:")
    print("-" * 40)
    
    async def use_connection(conn):
        conn["query"] = "SELECT * FROM users"
        return conn
    
    result = await engine.with_resource("connections", use_connection)
    print(f"   Result: {result}")
    print(f"   Acquired after: {engine.pool_acquired('connections')}")
    print()
    
    # 6. Callable Pool
    print("6. CALLABLE POOL:")
    print("-" * 40)
    
    counter = [0]
    
    async def create_worker():
        counter[0] += 1
        return {"worker_id": counter[0], "status": "ready"}
    
    async def destroy_worker(worker):
        worker["status"] = "destroyed"
    
    async def validate_worker(worker):
        return worker.get("status") == "ready"
    
    worker_pool = await engine.create_callable_pool(
        "workers",
        creator=create_worker,
        destroyer=destroy_worker,
        validator=validate_worker,
        config=PoolConfig(min_size=2, max_size=5, initial_size=2)
    )
    
    print(f"   Created: {worker_pool.name}")
    print(f"   Size: {worker_pool.size()}")
    
    result = await engine.acquire("workers")
    print(f"   Worker: {result.resource}")
    await engine.release(result.resource_id)
    print()
    
    # 7. Pool Statistics
    print("7. POOL STATISTICS:")
    print("-" * 40)
    
    stats = engine.pool_stats("connections")
    print(f"   Total created: {stats.total_created}")
    print(f"   Total acquired: {stats.total_acquired}")
    print(f"   Total returned: {stats.total_returned}")
    print(f"   Current size: {stats.current_size}")
    print(f"   Peak size: {stats.peak_size}")
    print(f"   Utilization: {stats.utilization:.2%}")
    print()
    
    # 8. Pool State
    print("8. POOL STATE:")
    print("-" * 40)
    
    print(f"   connections: {engine.pool_state('connections').value}")
    print(f"   workers: {engine.pool_state('workers').value}")
    print()
    
    # 9. List Pools
    print("9. LIST POOLS:")
    print("-" * 40)
    
    pools = engine.list_pools()
    for p in pools:
        print(f"   - {p}")
    print()
    
    # 10. Acquisition Timeout
    print("10. ACQUISITION TIMEOUT:")
    print("-" * 40)
    
    small_pool = await engine.create_simple_pool(
        "limited",
        config=PoolConfig(min_size=1, max_size=1, initial_size=1)
    )
    
    r1 = await engine.acquire("limited")
    print(f"   Acquired first: {r1.success}")
    
    r2 = await engine.acquire("limited", timeout=0.5)
    print(f"   Acquired second: {r2.success}")
    print(f"   Error: {r2.error}")
    
    await engine.release(r1.resource_id)
    print()
    
    # 11. Elastic Sizing
    print("11. ELASTIC SIZING:")
    print("-" * 40)
    
    elastic_pool = await engine.create_simple_pool(
        "elastic",
        config=PoolConfig(
            min_size=1,
            max_size=10,
            initial_size=1,
            sizing_strategy=SizingStrategy.ELASTIC
        )
    )
    
    print(f"   Initial size: {elastic_pool.size()}")
    
    acquired = []
    for i in range(5):
        r = await engine.acquire("elastic")
        acquired.append(r)
    
    print(f"   After 5 acquires: {elastic_pool.size()}")
    
    for r in acquired:
        await engine.release(r.resource_id)
    print()
    
    # 12. Engine Statistics
    print("12. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 13. Engine Summary
    print("13. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    print(f"   Active acquisitions: {summary['active_acquisitions']}")
    for name, info in summary["pools"].items():
        print(f"   {name}: {info['state']}, size={info['size']}, util={info['utilization']}")
    print()
    
    # 14. Remove Pool
    print("14. REMOVE POOL:")
    print("-" * 40)
    
    print(f"   Pools before: {engine.list_pools()}")
    await engine.remove_pool("limited")
    print(f"   Pools after: {engine.list_pools()}")
    print()
    
    # 15. Close All
    print("15. CLOSE ALL:")
    print("-" * 40)
    
    await engine.close()
    print(f"   Pools after close: {engine.list_pools()}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Pooling Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
