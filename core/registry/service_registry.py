#!/usr/bin/env python3
"""
BAEL - Service Registry and Discovery
Comprehensive service discovery and registry system.

Features:
- Service registration
- Health checking
- Load balancing
- Service discovery
- Heartbeat mechanism
- Metadata management
- Namespace/environment support
- Service versioning
- Leader election
- Clustering support
"""

import asyncio
import hashlib
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generator, List, Optional,
                    Set, Tuple, Type, TypeVar)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ServiceStatus(Enum):
    """Service instance status."""
    UP = "up"
    DOWN = "down"
    STARTING = "starting"
    STOPPING = "stopping"
    OUT_OF_SERVICE = "out_of_service"
    UNKNOWN = "unknown"


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    CONSISTENT_HASH = "consistent_hash"
    RESPONSE_TIME = "response_time"


class EventType(Enum):
    """Registry event types."""
    REGISTERED = "registered"
    DEREGISTERED = "deregistered"
    STATUS_CHANGED = "status_changed"
    HEALTH_CHANGED = "health_changed"
    HEARTBEAT_MISSED = "heartbeat_missed"
    LEADER_ELECTED = "leader_elected"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ServiceEndpoint:
    """Service endpoint information."""
    host: str
    port: int
    protocol: str = "http"
    path: str = ""

    @property
    def url(self) -> str:
        """Get full URL."""
        path = self.path.strip("/")
        return f"{self.protocol}://{self.host}:{self.port}/{path}".rstrip("/")


@dataclass
class HealthCheck:
    """Health check configuration."""
    endpoint: str = "/health"
    interval_seconds: float = 30.0
    timeout_seconds: float = 10.0
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3


@dataclass
class ServiceInstance:
    """Service instance information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    version: str = "1.0.0"
    endpoint: Optional[ServiceEndpoint] = None
    status: ServiceStatus = ServiceStatus.UP
    health: HealthStatus = HealthStatus.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    weight: int = 100
    zone: str = "default"
    namespace: str = "default"
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    connections: int = 0
    response_time: float = 0.0


@dataclass
class ServiceDefinition:
    """Service definition."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    health_check: Optional[HealthCheck] = None
    required_tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegistryEvent:
    """Registry event."""
    event_type: EventType
    service_name: str
    instance_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegistryStats:
    """Registry statistics."""
    total_services: int = 0
    total_instances: int = 0
    healthy_instances: int = 0
    unhealthy_instances: int = 0
    registrations: int = 0
    deregistrations: int = 0
    heartbeats: int = 0
    missed_heartbeats: int = 0


# =============================================================================
# LOAD BALANCERS
# =============================================================================

class LoadBalancer(ABC):
    """Abstract load balancer."""

    @abstractmethod
    def select(self, instances: List[ServiceInstance], key: Optional[str] = None) -> Optional[ServiceInstance]:
        """Select an instance."""
        pass


class RoundRobinBalancer(LoadBalancer):
    """Round-robin load balancer."""

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)

    def select(self, instances: List[ServiceInstance], key: Optional[str] = None) -> Optional[ServiceInstance]:
        if not instances:
            return None

        service = instances[0].service_name
        index = self._counters[service] % len(instances)
        self._counters[service] += 1

        return instances[index]


class RandomBalancer(LoadBalancer):
    """Random load balancer."""

    def select(self, instances: List[ServiceInstance], key: Optional[str] = None) -> Optional[ServiceInstance]:
        if not instances:
            return None
        return random.choice(instances)


class WeightedBalancer(LoadBalancer):
    """Weighted random load balancer."""

    def select(self, instances: List[ServiceInstance], key: Optional[str] = None) -> Optional[ServiceInstance]:
        if not instances:
            return None

        total_weight = sum(i.weight for i in instances)
        if total_weight == 0:
            return random.choice(instances)

        r = random.uniform(0, total_weight)
        cumulative = 0

        for instance in instances:
            cumulative += instance.weight
            if cumulative >= r:
                return instance

        return instances[-1]


class LeastConnectionsBalancer(LoadBalancer):
    """Least connections load balancer."""

    def select(self, instances: List[ServiceInstance], key: Optional[str] = None) -> Optional[ServiceInstance]:
        if not instances:
            return None
        return min(instances, key=lambda i: i.connections)


class ConsistentHashBalancer(LoadBalancer):
    """Consistent hash load balancer."""

    def __init__(self, replicas: int = 100):
        self.replicas = replicas
        self._ring: Dict[int, str] = {}
        self._sorted_keys: List[int] = []

    def _hash(self, key: str) -> int:
        """Hash a key."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def _build_ring(self, instances: List[ServiceInstance]) -> None:
        """Build consistent hash ring."""
        self._ring.clear()

        for instance in instances:
            for i in range(self.replicas):
                key = f"{instance.id}:{i}"
                hash_val = self._hash(key)
                self._ring[hash_val] = instance.id

        self._sorted_keys = sorted(self._ring.keys())

    def select(self, instances: List[ServiceInstance], key: Optional[str] = None) -> Optional[ServiceInstance]:
        if not instances:
            return None

        if not key:
            key = str(uuid.uuid4())

        self._build_ring(instances)
        hash_val = self._hash(key)

        # Find first key >= hash_val
        for ring_key in self._sorted_keys:
            if ring_key >= hash_val:
                instance_id = self._ring[ring_key]
                for instance in instances:
                    if instance.id == instance_id:
                        return instance

        # Wrap around
        if self._sorted_keys:
            instance_id = self._ring[self._sorted_keys[0]]
            for instance in instances:
                if instance.id == instance_id:
                    return instance

        return instances[0]


class ResponseTimeBalancer(LoadBalancer):
    """Response time based load balancer."""

    def select(self, instances: List[ServiceInstance], key: Optional[str] = None) -> Optional[ServiceInstance]:
        if not instances:
            return None

        # Filter instances with response time data
        with_data = [i for i in instances if i.response_time > 0]

        if not with_data:
            return random.choice(instances)

        # Weight inversely by response time
        weights = [1.0 / i.response_time for i in with_data]
        total = sum(weights)

        r = random.uniform(0, total)
        cumulative = 0

        for i, weight in enumerate(weights):
            cumulative += weight
            if cumulative >= r:
                return with_data[i]

        return with_data[-1]


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """Health check executor."""

    def __init__(self):
        self._check_results: Dict[str, List[bool]] = defaultdict(list)
        self._callbacks: List[Callable] = []

    async def check(
        self,
        instance: ServiceInstance,
        check: HealthCheck
    ) -> HealthStatus:
        """Perform health check on instance."""
        # Simulate health check (in production, would make HTTP call)
        healthy = instance.status == ServiceStatus.UP

        self._check_results[instance.id].append(healthy)

        # Keep only recent results
        max_results = max(check.healthy_threshold, check.unhealthy_threshold)
        self._check_results[instance.id] = self._check_results[instance.id][-max_results:]

        results = self._check_results[instance.id]

        # Determine health status
        recent_healthy = sum(1 for r in results[-check.healthy_threshold:] if r)
        recent_unhealthy = sum(1 for r in results[-check.unhealthy_threshold:] if not r)

        if recent_healthy >= check.healthy_threshold:
            return HealthStatus.HEALTHY
        elif recent_unhealthy >= check.unhealthy_threshold:
            return HealthStatus.UNHEALTHY

        return HealthStatus.DEGRADED

    def clear_results(self, instance_id: str) -> None:
        """Clear results for instance."""
        self._check_results.pop(instance_id, None)


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

class ServiceRegistry:
    """
    Comprehensive Service Registry for BAEL.

    Provides service registration, discovery, and load balancing.
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 90.0
    ):
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        self._services: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, Dict[str, ServiceInstance]] = defaultdict(dict)
        self._namespaces: Dict[str, Set[str]] = defaultdict(set)

        self._balancers: Dict[LoadBalanceStrategy, LoadBalancer] = {
            LoadBalanceStrategy.ROUND_ROBIN: RoundRobinBalancer(),
            LoadBalanceStrategy.RANDOM: RandomBalancer(),
            LoadBalanceStrategy.WEIGHTED: WeightedBalancer(),
            LoadBalanceStrategy.LEAST_CONNECTIONS: LeastConnectionsBalancer(),
            LoadBalanceStrategy.CONSISTENT_HASH: ConsistentHashBalancer(),
            LoadBalanceStrategy.RESPONSE_TIME: ResponseTimeBalancer(),
        }

        self._health_checker = HealthChecker()
        self._event_listeners: List[Callable[[RegistryEvent], Awaitable[None]]] = []
        self._stats = RegistryStats()
        self._leader: Dict[str, str] = {}  # service -> instance_id

        self._running = False
        self._tasks: List[asyncio.Task] = []

    # -------------------------------------------------------------------------
    # SERVICE MANAGEMENT
    # -------------------------------------------------------------------------

    def define_service(self, definition: ServiceDefinition) -> None:
        """Define a service."""
        self._services[definition.name] = definition
        self._stats.total_services = len(self._services)

    def get_service_definition(self, name: str) -> Optional[ServiceDefinition]:
        """Get service definition."""
        return self._services.get(name)

    # -------------------------------------------------------------------------
    # INSTANCE REGISTRATION
    # -------------------------------------------------------------------------

    async def register(self, instance: ServiceInstance) -> str:
        """Register a service instance."""
        if not instance.service_name:
            raise ValueError("Service name required")

        # Auto-define service if not exists
        if instance.service_name not in self._services:
            self.define_service(ServiceDefinition(name=instance.service_name))

        self._instances[instance.service_name][instance.id] = instance
        self._namespaces[instance.namespace].add(instance.service_name)

        self._stats.registrations += 1
        self._stats.total_instances = sum(len(v) for v in self._instances.values())

        await self._emit_event(RegistryEvent(
            event_type=EventType.REGISTERED,
            service_name=instance.service_name,
            instance_id=instance.id,
            data={"endpoint": instance.endpoint.url if instance.endpoint else None}
        ))

        return instance.id

    async def deregister(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                del self._instances[service_name][instance_id]
                self._health_checker.clear_results(instance_id)

                self._stats.deregistrations += 1
                self._stats.total_instances = sum(len(v) for v in self._instances.values())

                # Remove leader if deregistered
                if self._leader.get(service_name) == instance_id:
                    del self._leader[service_name]

                await self._emit_event(RegistryEvent(
                    event_type=EventType.DEREGISTERED,
                    service_name=service_name,
                    instance_id=instance_id
                ))

                return True
        return False

    async def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Update heartbeat for instance."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                instance = self._instances[service_name][instance_id]
                instance.last_heartbeat = datetime.utcnow()
                self._stats.heartbeats += 1
                return True
        return False

    # -------------------------------------------------------------------------
    # SERVICE DISCOVERY
    # -------------------------------------------------------------------------

    def get_instances(
        self,
        service_name: str,
        namespace: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        healthy_only: bool = True,
        zone: Optional[str] = None
    ) -> List[ServiceInstance]:
        """Get service instances."""
        if service_name not in self._instances:
            return []

        instances = list(self._instances[service_name].values())

        # Filter by namespace
        if namespace:
            instances = [i for i in instances if i.namespace == namespace]

        # Filter by health
        if healthy_only:
            instances = [i for i in instances
                        if i.status == ServiceStatus.UP
                        and i.health in (HealthStatus.HEALTHY, HealthStatus.UNKNOWN)]

        # Filter by tags
        if tags:
            instances = [i for i in instances if tags.issubset(i.tags)]

        # Filter by zone
        if zone:
            instances = [i for i in instances if i.zone == zone]

        return instances

    def discover(
        self,
        service_name: str,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        key: Optional[str] = None,
        **filters
    ) -> Optional[ServiceInstance]:
        """Discover a service instance using load balancing."""
        instances = self.get_instances(service_name, **filters)

        if not instances:
            return None

        balancer = self._balancers.get(strategy)
        if not balancer:
            balancer = self._balancers[LoadBalanceStrategy.ROUND_ROBIN]

        return balancer.select(instances, key)

    def list_services(self, namespace: Optional[str] = None) -> List[str]:
        """List all services."""
        if namespace:
            return list(self._namespaces.get(namespace, set()))
        return list(self._services.keys())

    # -------------------------------------------------------------------------
    # STATUS MANAGEMENT
    # -------------------------------------------------------------------------

    async def update_status(
        self,
        service_name: str,
        instance_id: str,
        status: ServiceStatus
    ) -> bool:
        """Update instance status."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                instance = self._instances[service_name][instance_id]
                old_status = instance.status
                instance.status = status

                if old_status != status:
                    await self._emit_event(RegistryEvent(
                        event_type=EventType.STATUS_CHANGED,
                        service_name=service_name,
                        instance_id=instance_id,
                        data={"old": old_status.value, "new": status.value}
                    ))

                return True
        return False

    async def update_health(
        self,
        service_name: str,
        instance_id: str,
        health: HealthStatus
    ) -> bool:
        """Update instance health."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                instance = self._instances[service_name][instance_id]
                old_health = instance.health
                instance.health = health

                if old_health != health:
                    self._update_health_stats()

                    await self._emit_event(RegistryEvent(
                        event_type=EventType.HEALTH_CHANGED,
                        service_name=service_name,
                        instance_id=instance_id,
                        data={"old": old_health.value, "new": health.value}
                    ))

                return True
        return False

    def _update_health_stats(self) -> None:
        """Update health statistics."""
        healthy = 0
        unhealthy = 0

        for instances in self._instances.values():
            for instance in instances.values():
                if instance.health == HealthStatus.HEALTHY:
                    healthy += 1
                elif instance.health == HealthStatus.UNHEALTHY:
                    unhealthy += 1

        self._stats.healthy_instances = healthy
        self._stats.unhealthy_instances = unhealthy

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    def update_metadata(
        self,
        service_name: str,
        instance_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update instance metadata."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                self._instances[service_name][instance_id].metadata.update(metadata)
                return True
        return False

    def add_tag(self, service_name: str, instance_id: str, tag: str) -> bool:
        """Add tag to instance."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                self._instances[service_name][instance_id].tags.add(tag)
                return True
        return False

    def remove_tag(self, service_name: str, instance_id: str, tag: str) -> bool:
        """Remove tag from instance."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                self._instances[service_name][instance_id].tags.discard(tag)
                return True
        return False

    # -------------------------------------------------------------------------
    # LEADER ELECTION
    # -------------------------------------------------------------------------

    async def elect_leader(self, service_name: str) -> Optional[str]:
        """Elect a leader for a service."""
        instances = self.get_instances(service_name, healthy_only=True)

        if not instances:
            self._leader.pop(service_name, None)
            return None

        # Check if current leader is still valid
        current = self._leader.get(service_name)
        if current:
            for instance in instances:
                if instance.id == current:
                    return current

        # Elect new leader (oldest instance)
        leader = min(instances, key=lambda i: i.registered_at)
        self._leader[service_name] = leader.id

        await self._emit_event(RegistryEvent(
            event_type=EventType.LEADER_ELECTED,
            service_name=service_name,
            instance_id=leader.id
        ))

        return leader.id

    def get_leader(self, service_name: str) -> Optional[str]:
        """Get current leader for service."""
        return self._leader.get(service_name)

    def is_leader(self, service_name: str, instance_id: str) -> bool:
        """Check if instance is leader."""
        return self._leader.get(service_name) == instance_id

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------

    def update_metrics(
        self,
        service_name: str,
        instance_id: str,
        connections: Optional[int] = None,
        response_time: Optional[float] = None
    ) -> bool:
        """Update instance metrics."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                instance = self._instances[service_name][instance_id]
                if connections is not None:
                    instance.connections = connections
                if response_time is not None:
                    instance.response_time = response_time
                return True
        return False

    # -------------------------------------------------------------------------
    # EVENTS
    # -------------------------------------------------------------------------

    def add_listener(
        self,
        callback: Callable[[RegistryEvent], Awaitable[None]]
    ) -> None:
        """Add event listener."""
        self._event_listeners.append(callback)

    def remove_listener(
        self,
        callback: Callable[[RegistryEvent], Awaitable[None]]
    ) -> None:
        """Remove event listener."""
        if callback in self._event_listeners:
            self._event_listeners.remove(callback)

    async def _emit_event(self, event: RegistryEvent) -> None:
        """Emit event to listeners."""
        for listener in self._event_listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    # -------------------------------------------------------------------------
    # BACKGROUND TASKS
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start background tasks."""
        self._running = True
        self._tasks.append(asyncio.create_task(self._heartbeat_monitor()))
        self._tasks.append(asyncio.create_task(self._health_check_loop()))

    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def _heartbeat_monitor(self) -> None:
        """Monitor heartbeats."""
        while self._running:
            await asyncio.sleep(self.heartbeat_interval)

            now = datetime.utcnow()
            timeout = timedelta(seconds=self.heartbeat_timeout)

            for service_name, instances in list(self._instances.items()):
                for instance_id, instance in list(instances.items()):
                    if now - instance.last_heartbeat > timeout:
                        self._stats.missed_heartbeats += 1

                        await self._emit_event(RegistryEvent(
                            event_type=EventType.HEARTBEAT_MISSED,
                            service_name=service_name,
                            instance_id=instance_id
                        ))

                        await self.update_status(
                            service_name,
                            instance_id,
                            ServiceStatus.DOWN
                        )

    async def _health_check_loop(self) -> None:
        """Run periodic health checks."""
        while self._running:
            await asyncio.sleep(30)

            for service_name, definition in self._services.items():
                if not definition.health_check:
                    continue

                for instance in self.get_instances(service_name, healthy_only=False):
                    health = await self._health_checker.check(
                        instance,
                        definition.health_check
                    )
                    await self.update_health(service_name, instance.id, health)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> RegistryStats:
        """Get registry statistics."""
        return self._stats

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def export_state(self) -> Dict[str, Any]:
        """Export registry state."""
        return {
            "services": {
                name: {
                    "instances": [
                        {
                            "id": i.id,
                            "endpoint": i.endpoint.url if i.endpoint else None,
                            "status": i.status.value,
                            "health": i.health.value,
                            "zone": i.zone,
                            "namespace": i.namespace
                        }
                        for i in instances.values()
                    ]
                }
                for name, instances in self._instances.items()
            },
            "stats": {
                "total_services": self._stats.total_services,
                "total_instances": self._stats.total_instances,
                "healthy": self._stats.healthy_instances,
                "unhealthy": self._stats.unhealthy_instances
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Service Registry."""
    print("=" * 70)
    print("BAEL - SERVICE REGISTRY DEMO")
    print("Service Discovery and Load Balancing")
    print("=" * 70)
    print()

    registry = ServiceRegistry(
        heartbeat_interval=5.0,
        heartbeat_timeout=15.0
    )

    # Event listener
    events = []
    async def event_listener(event: RegistryEvent):
        events.append(event)
    registry.add_listener(event_listener)

    # 1. Define Services
    print("1. DEFINE SERVICES:")
    print("-" * 40)

    registry.define_service(ServiceDefinition(
        name="api-gateway",
        description="API Gateway service",
        health_check=HealthCheck(interval_seconds=10.0)
    ))

    registry.define_service(ServiceDefinition(
        name="user-service",
        description="User management service"
    ))

    print(f"   Defined: {registry.list_services()}")
    print()

    # 2. Register Instances
    print("2. REGISTER INSTANCES:")
    print("-" * 40)

    instances = []

    for i in range(3):
        instance = ServiceInstance(
            service_name="api-gateway",
            version="1.0.0",
            endpoint=ServiceEndpoint(host="10.0.0." + str(i+1), port=8080),
            weight=100 if i < 2 else 50,
            zone="us-east-1a" if i < 2 else "us-east-1b",
            tags={"production", "primary"} if i == 0 else {"production"}
        )
        instance_id = await registry.register(instance)
        instances.append(instance)
        print(f"   Registered: {instance.service_name} @ {instance.endpoint.host}")

    for i in range(2):
        instance = ServiceInstance(
            service_name="user-service",
            endpoint=ServiceEndpoint(host="10.0.1." + str(i+1), port=8081),
            connections=i * 10
        )
        await registry.register(instance)
        instances.append(instance)

    print()

    # 3. Discover Services
    print("3. DISCOVER SERVICES:")
    print("-" * 40)

    gateway = registry.discover("api-gateway")
    print(f"   Gateway: {gateway.endpoint.url if gateway else 'None'}")

    user_svc = registry.discover("user-service")
    print(f"   User Service: {user_svc.endpoint.url if user_svc else 'None'}")
    print()

    # 4. Load Balancing
    print("4. LOAD BALANCING STRATEGIES:")
    print("-" * 40)

    strategies = [
        LoadBalanceStrategy.ROUND_ROBIN,
        LoadBalanceStrategy.RANDOM,
        LoadBalanceStrategy.WEIGHTED,
        LoadBalanceStrategy.LEAST_CONNECTIONS
    ]

    for strategy in strategies:
        selections = []
        for _ in range(6):
            instance = registry.discover("api-gateway", strategy=strategy)
            if instance:
                selections.append(instance.endpoint.host.split(".")[-1])
        print(f"   {strategy.value:20}: {' -> '.join(selections)}")
    print()

    # 5. Consistent Hash
    print("5. CONSISTENT HASH (Sticky Sessions):")
    print("-" * 40)

    for user_id in ["user-1", "user-2", "user-3", "user-1"]:
        instance = registry.discover(
            "api-gateway",
            strategy=LoadBalanceStrategy.CONSISTENT_HASH,
            key=user_id
        )
        if instance:
            print(f"   {user_id} -> {instance.endpoint.host}")
    print()

    # 6. Filtering
    print("6. FILTERING:")
    print("-" * 40)

    primary = registry.get_instances("api-gateway", tags={"primary"})
    print(f"   Primary instances: {len(primary)}")

    zone_a = registry.get_instances("api-gateway", zone="us-east-1a")
    print(f"   Zone A instances: {len(zone_a)}")
    print()

    # 7. Heartbeat
    print("7. HEARTBEAT:")
    print("-" * 40)

    for instance in instances[:3]:
        await registry.heartbeat(instance.service_name, instance.id)

    stats = registry.get_stats()
    print(f"   Heartbeats processed: {stats.heartbeats}")
    print()

    # 8. Status Updates
    print("8. STATUS UPDATES:")
    print("-" * 40)

    instance = instances[0]
    await registry.update_status(instance.service_name, instance.id, ServiceStatus.STOPPING)
    print(f"   {instance.endpoint.host}: {instance.status.value}")

    await registry.update_status(instance.service_name, instance.id, ServiceStatus.UP)
    print(f"   {instance.endpoint.host}: {instance.status.value}")
    print()

    # 9. Health Updates
    print("9. HEALTH UPDATES:")
    print("-" * 40)

    await registry.update_health(instances[1].service_name, instances[1].id, HealthStatus.HEALTHY)
    await registry.update_health(instances[2].service_name, instances[2].id, HealthStatus.UNHEALTHY)

    healthy = registry.get_instances("api-gateway", healthy_only=True)
    print(f"   Healthy api-gateway instances: {len(healthy)}")
    print()

    # 10. Leader Election
    print("10. LEADER ELECTION:")
    print("-" * 40)

    leader_id = await registry.elect_leader("api-gateway")
    print(f"   Elected leader: {leader_id[:8]}...")

    leader_instance = None
    for inst in registry.get_instances("api-gateway", healthy_only=False):
        if inst.id == leader_id:
            leader_instance = inst
            break

    if leader_instance:
        print(f"   Leader endpoint: {leader_instance.endpoint.url}")
    print()

    # 11. Metadata and Tags
    print("11. METADATA AND TAGS:")
    print("-" * 40)

    registry.update_metadata(
        instances[0].service_name,
        instances[0].id,
        {"build": "v1.2.3", "git_sha": "abc123"}
    )
    registry.add_tag(instances[0].service_name, instances[0].id, "canary")

    print(f"   Metadata: {instances[0].metadata}")
    print(f"   Tags: {instances[0].tags}")
    print()

    # 12. Metrics
    print("12. METRICS:")
    print("-" * 40)

    registry.update_metrics(
        instances[0].service_name,
        instances[0].id,
        connections=42,
        response_time=0.125
    )

    print(f"   Connections: {instances[0].connections}")
    print(f"   Response time: {instances[0].response_time}s")
    print()

    # 13. Events
    print("13. EVENTS RECEIVED:")
    print("-" * 40)

    for event in events[:5]:
        print(f"   {event.event_type.value}: {event.service_name} ({event.instance_id[:8]}...)")
    print(f"   Total events: {len(events)}")
    print()

    # 14. Statistics
    print("14. REGISTRY STATISTICS:")
    print("-" * 40)

    stats = registry.get_stats()
    print(f"   Total services: {stats.total_services}")
    print(f"   Total instances: {stats.total_instances}")
    print(f"   Registrations: {stats.registrations}")
    print(f"   Heartbeats: {stats.heartbeats}")
    print()

    # 15. Export State
    print("15. EXPORT STATE:")
    print("-" * 40)

    state = registry.export_state()
    print(f"   Services: {list(state['services'].keys())}")
    for svc_name, svc_data in state['services'].items():
        print(f"   {svc_name}: {len(svc_data['instances'])} instances")
    print()

    # 16. Deregistration
    print("16. DEREGISTRATION:")
    print("-" * 40)

    await registry.deregister(instances[4].service_name, instances[4].id)
    print(f"   Deregistered: {instances[4].endpoint.host}")

    remaining = registry.get_instances("user-service")
    print(f"   Remaining user-service instances: {len(remaining)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Service Registry Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
