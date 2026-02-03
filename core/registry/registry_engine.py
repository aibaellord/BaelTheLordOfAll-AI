#!/usr/bin/env python3
"""
BAEL - Registry Engine
Service registry and discovery for agents.

Features:
- Service registration
- Service discovery
- Health monitoring
- Load balancing
- Service metadata
"""

import asyncio
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ServiceState(Enum):
    """Service states."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class HealthStatus(Enum):
    """Health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    HASH = "hash"


class DiscoveryType(Enum):
    """Discovery types."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    DNS = "dns"
    CONSUL = "consul"


class ProtocolType(Enum):
    """Protocol types."""
    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    TCP = "tcp"
    UDP = "udp"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ServiceEndpoint:
    """A service endpoint."""
    endpoint_id: str = ""
    host: str = ""
    port: int = 0
    protocol: ProtocolType = ProtocolType.HTTP
    weight: int = 1
    healthy: bool = True

    def __post_init__(self):
        if not self.endpoint_id:
            self.endpoint_id = str(uuid.uuid4())[:8]

    @property
    def address(self) -> str:
        """Get full address."""
        return f"{self.protocol.value}://{self.host}:{self.port}"


@dataclass
class ServiceInstance:
    """A service instance."""
    instance_id: str = ""
    service_name: str = ""
    endpoint: Optional[ServiceEndpoint] = None
    state: ServiceState = ServiceState.UNKNOWN
    health: HealthStatus = HealthStatus.UNKNOWN
    metadata: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    connections: int = 0

    def __post_init__(self):
        if not self.instance_id:
            self.instance_id = str(uuid.uuid4())[:8]


@dataclass
class ServiceDefinition:
    """A service definition."""
    service_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    instances: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.service_id:
            self.service_id = str(uuid.uuid4())[:8]


@dataclass
class HealthCheck:
    """Health check configuration."""
    check_id: str = ""
    service_name: str = ""
    interval: float = 30.0
    timeout: float = 5.0
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3
    path: str = "/health"

    def __post_init__(self):
        if not self.check_id:
            self.check_id = str(uuid.uuid4())[:8]


@dataclass
class RegistryConfig:
    """Registry engine configuration."""
    heartbeat_interval: float = 30.0
    heartbeat_timeout: float = 90.0
    enable_health_checks: bool = True
    default_lb_strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN


# =============================================================================
# SERVICE STORE
# =============================================================================

class ServiceStore:
    """Store service registrations."""

    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, ServiceInstance] = {}
        self._by_name: Dict[str, List[str]] = defaultdict(list)

    def add_service(self, service: ServiceDefinition) -> None:
        """Add service definition."""
        self._services[service.service_id] = service

    def get_service(self, service_id: str) -> Optional[ServiceDefinition]:
        """Get service by ID."""
        return self._services.get(service_id)

    def get_service_by_name(self, name: str) -> Optional[ServiceDefinition]:
        """Get service by name."""
        for service in self._services.values():
            if service.name == name:
                return service
        return None

    def add_instance(self, instance: ServiceInstance) -> None:
        """Add service instance."""
        self._instances[instance.instance_id] = instance
        self._by_name[instance.service_name].append(instance.instance_id)

    def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        """Get instance by ID."""
        return self._instances.get(instance_id)

    def get_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get all instances for a service."""
        instance_ids = self._by_name.get(service_name, [])
        return [self._instances[iid] for iid in instance_ids if iid in self._instances]

    def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get healthy instances for a service."""
        instances = self.get_instances(service_name)
        return [i for i in instances if i.health == HealthStatus.HEALTHY]

    def remove_instance(self, instance_id: str) -> bool:
        """Remove instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        if instance_id in self._by_name.get(instance.service_name, []):
            self._by_name[instance.service_name].remove(instance_id)

        del self._instances[instance_id]
        return True

    def remove_service(self, service_id: str) -> bool:
        """Remove service and its instances."""
        service = self._services.get(service_id)
        if not service:
            return False

        instance_ids = list(self._by_name.get(service.name, []))
        for instance_id in instance_ids:
            self.remove_instance(instance_id)

        del self._services[service_id]
        return True

    def list_services(self) -> List[ServiceDefinition]:
        """List all services."""
        return list(self._services.values())

    def list_instances(self) -> List[ServiceInstance]:
        """List all instances."""
        return list(self._instances.values())

    def count_services(self) -> int:
        """Count services."""
        return len(self._services)

    def count_instances(self) -> int:
        """Count instances."""
        return len(self._instances)


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """Balance load across service instances."""

    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self._strategy = strategy
        self._round_robin_idx: Dict[str, int] = defaultdict(int)

    def select(
        self,
        instances: List[ServiceInstance],
        key: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Select an instance based on strategy."""
        if not instances:
            return None

        healthy = [i for i in instances if i.health == HealthStatus.HEALTHY]

        if not healthy:
            healthy = instances

        if self._strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin(healthy, key or "default")

        elif self._strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(healthy)

        elif self._strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy)

        elif self._strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted(healthy)

        elif self._strategy == LoadBalanceStrategy.HASH:
            return self._hash_based(healthy, key or "default")

        return healthy[0] if healthy else None

    def _round_robin(
        self,
        instances: List[ServiceInstance],
        key: str
    ) -> ServiceInstance:
        """Round-robin selection."""
        idx = self._round_robin_idx[key]
        instance = instances[idx % len(instances)]
        self._round_robin_idx[key] = idx + 1
        return instance

    def _least_connections(
        self,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Least connections selection."""
        return min(instances, key=lambda i: i.connections)

    def _weighted(
        self,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Weighted random selection."""
        weights = [i.endpoint.weight if i.endpoint else 1 for i in instances]
        total = sum(weights)
        r = random.uniform(0, total)

        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return instances[i]

        return instances[-1]

    def _hash_based(
        self,
        instances: List[ServiceInstance],
        key: str
    ) -> ServiceInstance:
        """Hash-based selection."""
        hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
        idx = hash_val % len(instances)
        return instances[idx]

    def set_strategy(self, strategy: LoadBalanceStrategy) -> None:
        """Set load balancing strategy."""
        self._strategy = strategy


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """Check service health."""

    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, List[bool]] = defaultdict(list)

    def add_check(self, check: HealthCheck) -> None:
        """Add health check."""
        self._checks[check.check_id] = check

    def get_check(self, check_id: str) -> Optional[HealthCheck]:
        """Get health check."""
        return self._checks.get(check_id)

    async def run_check(
        self,
        instance: ServiceInstance,
        check: HealthCheck
    ) -> HealthStatus:
        """Run health check on instance."""
        try:
            success = random.random() > 0.1

            results = self._results[instance.instance_id]
            results.append(success)

            if len(results) > max(check.healthy_threshold, check.unhealthy_threshold):
                results.pop(0)

            if len(results) >= check.unhealthy_threshold:
                recent_failures = sum(1 for r in results[-check.unhealthy_threshold:] if not r)
                if recent_failures >= check.unhealthy_threshold:
                    return HealthStatus.UNHEALTHY

            if len(results) >= check.healthy_threshold:
                recent_success = sum(1 for r in results[-check.healthy_threshold:] if r)
                if recent_success >= check.healthy_threshold:
                    return HealthStatus.HEALTHY

            return HealthStatus.DEGRADED

        except Exception:
            return HealthStatus.UNHEALTHY

    def remove_check(self, check_id: str) -> bool:
        """Remove health check."""
        if check_id in self._checks:
            del self._checks[check_id]
            return True
        return False


# =============================================================================
# HEARTBEAT MANAGER
# =============================================================================

class HeartbeatManager:
    """Manage service heartbeats."""

    def __init__(self, timeout: float = 90.0):
        self._timeout = timeout

    def heartbeat(self, instance: ServiceInstance) -> None:
        """Record heartbeat."""
        instance.last_heartbeat = datetime.now()

    def is_alive(self, instance: ServiceInstance) -> bool:
        """Check if instance is alive."""
        elapsed = (datetime.now() - instance.last_heartbeat).total_seconds()
        return elapsed < self._timeout

    def get_dead_instances(
        self,
        instances: List[ServiceInstance]
    ) -> List[ServiceInstance]:
        """Get instances that missed heartbeat."""
        return [i for i in instances if not self.is_alive(i)]

    def set_timeout(self, timeout: float) -> None:
        """Set heartbeat timeout."""
        self._timeout = timeout


# =============================================================================
# DISCOVERY CLIENT
# =============================================================================

class DiscoveryClient:
    """Client for service discovery."""

    def __init__(self, store: ServiceStore, balancer: LoadBalancer):
        self._store = store
        self._balancer = balancer

    def discover(
        self,
        service_name: str,
        tags: Optional[List[str]] = None,
        healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """Discover service instances."""
        if healthy_only:
            instances = self._store.get_healthy_instances(service_name)
        else:
            instances = self._store.get_instances(service_name)

        if tags:
            instances = [
                i for i in instances
                if all(tag in i.tags for tag in tags)
            ]

        return instances

    def discover_one(
        self,
        service_name: str,
        key: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Discover single instance."""
        instances = self.discover(service_name)
        return self._balancer.select(instances, key)

    def get_endpoint(
        self,
        service_name: str,
        key: Optional[str] = None
    ) -> Optional[str]:
        """Get endpoint address for service."""
        instance = self.discover_one(service_name, key)

        if instance and instance.endpoint:
            return instance.endpoint.address

        return None


# =============================================================================
# REGISTRY ENGINE
# =============================================================================

class RegistryEngine:
    """
    Registry Engine for BAEL.

    Service registry and discovery.
    """

    def __init__(self, config: Optional[RegistryConfig] = None):
        self._config = config or RegistryConfig()

        self._store = ServiceStore()
        self._balancer = LoadBalancer(self._config.default_lb_strategy)
        self._health_checker = HealthChecker()
        self._heartbeat_manager = HeartbeatManager(self._config.heartbeat_timeout)
        self._discovery = DiscoveryClient(self._store, self._balancer)

    # ----- Service Registration -----

    def register_service(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        metadata: Optional[Dict[str, str]] = None
    ) -> ServiceDefinition:
        """Register a service."""
        service = ServiceDefinition(
            name=name,
            version=version,
            description=description,
            metadata=metadata or {}
        )

        self._store.add_service(service)

        return service

    def register_instance(
        self,
        service_name: str,
        host: str,
        port: int,
        protocol: ProtocolType = ProtocolType.HTTP,
        weight: int = 1,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None
    ) -> ServiceInstance:
        """Register a service instance."""
        endpoint = ServiceEndpoint(
            host=host,
            port=port,
            protocol=protocol,
            weight=weight
        )

        instance = ServiceInstance(
            service_name=service_name,
            endpoint=endpoint,
            state=ServiceState.RUNNING,
            health=HealthStatus.HEALTHY,
            metadata=metadata or {},
            tags=tags or []
        )

        self._store.add_instance(instance)

        service = self._store.get_service_by_name(service_name)
        if service:
            service.instances.append(instance.instance_id)

        return instance

    def deregister_instance(self, instance_id: str) -> bool:
        """Deregister a service instance."""
        instance = self._store.get_instance(instance_id)

        if instance:
            instance.state = ServiceState.STOPPED
            service = self._store.get_service_by_name(instance.service_name)
            if service and instance_id in service.instances:
                service.instances.remove(instance_id)

        return self._store.remove_instance(instance_id)

    def deregister_service(self, service_name: str) -> bool:
        """Deregister a service and all instances."""
        service = self._store.get_service_by_name(service_name)
        if service:
            return self._store.remove_service(service.service_id)
        return False

    # ----- Service Discovery -----

    def discover(
        self,
        service_name: str,
        tags: Optional[List[str]] = None,
        healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """Discover service instances."""
        return self._discovery.discover(service_name, tags, healthy_only)

    def discover_one(
        self,
        service_name: str,
        key: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Discover a single instance."""
        return self._discovery.discover_one(service_name, key)

    def get_endpoint(
        self,
        service_name: str,
        key: Optional[str] = None
    ) -> Optional[str]:
        """Get endpoint for service."""
        return self._discovery.get_endpoint(service_name, key)

    # ----- Service Info -----

    def get_service(self, service_name: str) -> Optional[ServiceDefinition]:
        """Get service definition."""
        return self._store.get_service_by_name(service_name)

    def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        """Get service instance."""
        return self._store.get_instance(instance_id)

    def list_services(self) -> List[str]:
        """List all service names."""
        return [s.name for s in self._store.list_services()]

    def list_instances(self, service_name: str) -> List[ServiceInstance]:
        """List instances for a service."""
        return self._store.get_instances(service_name)

    # ----- Health Management -----

    def add_health_check(
        self,
        service_name: str,
        interval: float = 30.0,
        path: str = "/health"
    ) -> HealthCheck:
        """Add health check for service."""
        check = HealthCheck(
            service_name=service_name,
            interval=interval,
            path=path
        )

        self._health_checker.add_check(check)

        return check

    async def check_health(self, instance_id: str) -> HealthStatus:
        """Check instance health."""
        instance = self._store.get_instance(instance_id)

        if not instance:
            return HealthStatus.UNKNOWN

        checks = [c for c in self._health_checker._checks.values()
                  if c.service_name == instance.service_name]

        if not checks:
            return instance.health

        check = checks[0]
        health = await self._health_checker.run_check(instance, check)
        instance.health = health

        return health

    def set_health(self, instance_id: str, health: HealthStatus) -> bool:
        """Set instance health status."""
        instance = self._store.get_instance(instance_id)

        if instance:
            instance.health = health
            return True

        return False

    def get_healthy_count(self, service_name: str) -> int:
        """Get count of healthy instances."""
        return len(self._store.get_healthy_instances(service_name))

    # ----- Heartbeat Management -----

    def heartbeat(self, instance_id: str) -> bool:
        """Record heartbeat for instance."""
        instance = self._store.get_instance(instance_id)

        if instance:
            self._heartbeat_manager.heartbeat(instance)
            return True

        return False

    def check_heartbeats(self) -> List[str]:
        """Check for dead instances."""
        instances = self._store.list_instances()
        dead = self._heartbeat_manager.get_dead_instances(instances)

        for instance in dead:
            instance.health = HealthStatus.UNHEALTHY
            instance.state = ServiceState.FAILED

        return [i.instance_id for i in dead]

    # ----- Load Balancing -----

    def set_strategy(self, strategy: LoadBalanceStrategy) -> None:
        """Set load balancing strategy."""
        self._balancer.set_strategy(strategy)

    def increment_connections(self, instance_id: str) -> bool:
        """Increment connection count."""
        instance = self._store.get_instance(instance_id)

        if instance:
            instance.connections += 1
            return True

        return False

    def decrement_connections(self, instance_id: str) -> bool:
        """Decrement connection count."""
        instance = self._store.get_instance(instance_id)

        if instance and instance.connections > 0:
            instance.connections -= 1
            return True

        return False

    # ----- Metadata -----

    def set_metadata(
        self,
        instance_id: str,
        key: str,
        value: str
    ) -> bool:
        """Set instance metadata."""
        instance = self._store.get_instance(instance_id)

        if instance:
            instance.metadata[key] = value
            return True

        return False

    def add_tag(self, instance_id: str, tag: str) -> bool:
        """Add tag to instance."""
        instance = self._store.get_instance(instance_id)

        if instance and tag not in instance.tags:
            instance.tags.append(tag)
            return True

        return False

    def remove_tag(self, instance_id: str, tag: str) -> bool:
        """Remove tag from instance."""
        instance = self._store.get_instance(instance_id)

        if instance and tag in instance.tags:
            instance.tags.remove(tag)
            return True

        return False

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        instances = self._store.list_instances()

        by_health = defaultdict(int)
        by_state = defaultdict(int)

        for instance in instances:
            by_health[instance.health.value] += 1
            by_state[instance.state.value] += 1

        return {
            "services": self._store.count_services(),
            "instances": self._store.count_instances(),
            "by_health": dict(by_health),
            "by_state": dict(by_state),
            "lb_strategy": self._balancer._strategy.value
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Registry Engine."""
    print("=" * 70)
    print("BAEL - REGISTRY ENGINE DEMO")
    print("Service Registry and Discovery")
    print("=" * 70)
    print()

    engine = RegistryEngine()

    # 1. Register Services
    print("1. REGISTER SERVICES:")
    print("-" * 40)

    user_svc = engine.register_service(
        "user-service",
        version="2.1.0",
        description="User management service"
    )
    print(f"   Registered: {user_svc.name} v{user_svc.version}")

    order_svc = engine.register_service(
        "order-service",
        version="1.5.0",
        description="Order processing service"
    )
    print(f"   Registered: {order_svc.name} v{order_svc.version}")
    print()

    # 2. Register Instances
    print("2. REGISTER INSTANCES:")
    print("-" * 40)

    user_1 = engine.register_instance(
        "user-service",
        host="192.168.1.10",
        port=8080,
        weight=2,
        tags=["primary", "us-east"]
    )
    print(f"   Instance: {user_1.instance_id} at {user_1.endpoint.address}")

    user_2 = engine.register_instance(
        "user-service",
        host="192.168.1.11",
        port=8080,
        weight=1,
        tags=["secondary", "us-west"]
    )
    print(f"   Instance: {user_2.instance_id} at {user_2.endpoint.address}")

    order_1 = engine.register_instance(
        "order-service",
        host="192.168.1.20",
        port=9090,
        tags=["primary"]
    )
    print(f"   Instance: {order_1.instance_id} at {order_1.endpoint.address}")
    print()

    # 3. Discover Services
    print("3. DISCOVER SERVICES:")
    print("-" * 40)

    instances = engine.discover("user-service")
    print(f"   Found {len(instances)} user-service instances:")
    for inst in instances:
        print(f"   - {inst.instance_id}: {inst.endpoint.address}")
    print()

    # 4. Discover by Tags
    print("4. DISCOVER BY TAGS:")
    print("-" * 40)

    primary_instances = engine.discover("user-service", tags=["primary"])
    print(f"   Primary instances: {len(primary_instances)}")

    west_instances = engine.discover("user-service", tags=["us-west"])
    print(f"   US-West instances: {len(west_instances)}")
    print()

    # 5. Load Balancing - Round Robin
    print("5. LOAD BALANCING - ROUND ROBIN:")
    print("-" * 40)

    engine.set_strategy(LoadBalanceStrategy.ROUND_ROBIN)

    for i in range(4):
        instance = engine.discover_one("user-service")
        print(f"   Request {i+1}: {instance.instance_id}")
    print()

    # 6. Load Balancing - Weighted
    print("6. LOAD BALANCING - WEIGHTED:")
    print("-" * 40)

    engine.set_strategy(LoadBalanceStrategy.WEIGHTED)

    selections = defaultdict(int)
    for _ in range(100):
        instance = engine.discover_one("user-service")
        selections[instance.instance_id] += 1

    for instance_id, count in selections.items():
        print(f"   {instance_id}: {count} selections")
    print()

    # 7. Get Endpoint
    print("7. GET ENDPOINT:")
    print("-" * 40)

    endpoint = engine.get_endpoint("user-service")
    print(f"   User service endpoint: {endpoint}")

    endpoint = engine.get_endpoint("order-service")
    print(f"   Order service endpoint: {endpoint}")
    print()

    # 8. Health Management
    print("8. HEALTH MANAGEMENT:")
    print("-" * 40)

    engine.add_health_check("user-service", interval=10.0)

    health = await engine.check_health(user_1.instance_id)
    print(f"   User-1 health: {health.value}")

    engine.set_health(user_2.instance_id, HealthStatus.UNHEALTHY)
    print(f"   User-2 set to unhealthy")

    healthy = engine.get_healthy_count("user-service")
    print(f"   Healthy instances: {healthy}")
    print()

    # 9. Heartbeat
    print("9. HEARTBEAT:")
    print("-" * 40)

    engine.heartbeat(user_1.instance_id)
    print(f"   Heartbeat sent for {user_1.instance_id}")

    instance = engine.get_instance(user_1.instance_id)
    print(f"   Last heartbeat: {instance.last_heartbeat.strftime('%H:%M:%S')}")

    dead = engine.check_heartbeats()
    print(f"   Dead instances: {len(dead)}")
    print()

    # 10. Connection Tracking
    print("10. CONNECTION TRACKING:")
    print("-" * 40)

    engine.set_strategy(LoadBalanceStrategy.LEAST_CONNECTIONS)

    engine.increment_connections(user_1.instance_id)
    engine.increment_connections(user_1.instance_id)
    engine.increment_connections(user_2.instance_id)

    inst1 = engine.get_instance(user_1.instance_id)
    inst2 = engine.get_instance(user_2.instance_id)

    print(f"   {user_1.instance_id}: {inst1.connections} connections")
    print(f"   {user_2.instance_id}: {inst2.connections} connections")

    selected = engine.discover_one("user-service")
    print(f"   Least connections selected: {selected.instance_id}")
    print()

    # 11. Metadata
    print("11. METADATA:")
    print("-" * 40)

    engine.set_metadata(user_1.instance_id, "region", "us-east-1")
    engine.set_metadata(user_1.instance_id, "zone", "a")

    instance = engine.get_instance(user_1.instance_id)
    print(f"   Instance metadata:")
    for key, value in instance.metadata.items():
        print(f"   - {key}: {value}")
    print()

    # 12. Tags
    print("12. TAGS:")
    print("-" * 40)

    engine.add_tag(user_1.instance_id, "canary")
    instance = engine.get_instance(user_1.instance_id)
    print(f"   Tags after add: {instance.tags}")

    engine.remove_tag(user_1.instance_id, "canary")
    instance = engine.get_instance(user_1.instance_id)
    print(f"   Tags after remove: {instance.tags}")
    print()

    # 13. List All
    print("13. LIST ALL:")
    print("-" * 40)

    services = engine.list_services()
    print(f"   Services: {services}")

    for svc_name in services:
        instances = engine.list_instances(svc_name)
        print(f"   {svc_name}: {len(instances)} instances")
    print()

    # 14. Deregister
    print("14. DEREGISTER:")
    print("-" * 40)

    engine.deregister_instance(order_1.instance_id)
    print(f"   Deregistered: {order_1.instance_id}")

    instances = engine.list_instances("order-service")
    print(f"   Order service instances: {len(instances)}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Registry Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
