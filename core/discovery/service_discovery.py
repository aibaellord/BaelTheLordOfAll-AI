#!/usr/bin/env python3
"""
BAEL - Service Discovery System
Comprehensive service discovery and registry.

This module provides a complete service discovery framework
for dynamic service registration and lookup.

Features:
- Service registration
- Health checking
- Load balancing
- Service mesh
- Endpoint management
- DNS-like resolution
- Circuit breaker integration
- Service versioning
- Metadata support
- Watch/Subscribe patterns
"""

import asyncio
import hashlib
import heapq
import json
import logging
import os
import random
import socket
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    DRAINING = "draining"
    STARTING = "starting"


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    IP_HASH = "ip_hash"
    LEAST_LATENCY = "least_latency"


class HealthCheckType(Enum):
    """Health check types."""
    HTTP = "http"
    TCP = "tcp"
    GRPC = "grpc"
    SCRIPT = "script"
    TTL = "ttl"


class ServiceProtocol(Enum):
    """Service protocols."""
    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    TCP = "tcp"
    UDP = "udp"
    WEBSOCKET = "websocket"


class EventType(Enum):
    """Service event types."""
    REGISTERED = "registered"
    DEREGISTERED = "deregistered"
    HEALTH_CHANGED = "health_changed"
    UPDATED = "updated"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ServiceEndpoint:
    """Service endpoint."""
    host: str
    port: int
    protocol: ServiceProtocol = ServiceProtocol.HTTP
    path: str = ""

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def url(self) -> str:
        base = f"{self.protocol.value}://{self.host}:{self.port}"
        return f"{base}{self.path}" if self.path else base


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    check_type: HealthCheckType = HealthCheckType.TCP
    interval: float = 10.0  # seconds
    timeout: float = 5.0
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3

    # HTTP check
    http_path: str = "/health"
    http_method: str = "GET"
    expected_status: List[int] = field(default_factory=lambda: [200])

    # TCP check
    tcp_port: int = None


@dataclass
class ServiceInstance:
    """A service instance."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    version: str = "1.0.0"

    # Endpoint
    endpoint: ServiceEndpoint = None

    # Health
    status: ServiceStatus = ServiceStatus.UNKNOWN
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    last_health_check: datetime = None
    healthy_count: int = 0
    unhealthy_count: int = 0

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    weight: int = 100

    # Tracking
    registered_at: datetime = field(default_factory=datetime.now)
    connections: int = 0
    total_requests: int = 0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "service_name": self.service_name,
            "version": self.version,
            "endpoint": {
                "host": self.endpoint.host,
                "port": self.endpoint.port,
                "protocol": self.endpoint.protocol.value
            } if self.endpoint else None,
            "status": self.status.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "weight": self.weight
        }


@dataclass
class ServiceDefinition:
    """Service definition/template."""
    name: str
    description: str = ""
    protocol: ServiceProtocol = ServiceProtocol.HTTP
    default_port: int = 8080
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    required_tags: List[str] = field(default_factory=list)
    metadata_schema: Dict[str, str] = field(default_factory=dict)


@dataclass
class ServiceEvent:
    """Service discovery event."""
    event_type: EventType
    service_name: str
    instance_id: str
    instance: ServiceInstance = None
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """Service health checker."""

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    async def check_health(
        self,
        instance: ServiceInstance,
        config: HealthCheckConfig
    ) -> bool:
        """Perform health check."""
        try:
            if config.check_type == HealthCheckType.TCP:
                return await self._tcp_check(instance, config)
            elif config.check_type == HealthCheckType.HTTP:
                return await self._http_check(instance, config)
            elif config.check_type == HealthCheckType.TTL:
                return self._ttl_check(instance, config)
            else:
                return True
        except Exception as e:
            logger.error(f"Health check failed for {instance.id}: {e}")
            return False

    async def _tcp_check(
        self,
        instance: ServiceInstance,
        config: HealthCheckConfig
    ) -> bool:
        """TCP port check."""
        try:
            port = config.tcp_port or instance.endpoint.port

            _, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    instance.endpoint.host,
                    port
                ),
                timeout=config.timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False

    async def _http_check(
        self,
        instance: ServiceInstance,
        config: HealthCheckConfig
    ) -> bool:
        """HTTP health check."""
        try:
            # Simple HTTP check without external dependencies
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    instance.endpoint.host,
                    instance.endpoint.port
                ),
                timeout=config.timeout
            )

            # Send HTTP request
            request = (
                f"{config.http_method} {config.http_path} HTTP/1.1\r\n"
                f"Host: {instance.endpoint.host}\r\n"
                f"Connection: close\r\n\r\n"
            )
            writer.write(request.encode())
            await writer.drain()

            # Read response
            response = await asyncio.wait_for(
                reader.read(1024),
                timeout=config.timeout
            )

            writer.close()
            await writer.wait_closed()

            # Check status code
            if response:
                status_line = response.decode().split('\r\n')[0]
                status_code = int(status_line.split()[1])
                return status_code in config.expected_status

            return False
        except:
            return False

    def _ttl_check(
        self,
        instance: ServiceInstance,
        config: HealthCheckConfig
    ) -> bool:
        """TTL-based check (service must heartbeat)."""
        if not instance.last_health_check:
            return False

        elapsed = (datetime.now() - instance.last_health_check).total_seconds()
        return elapsed < config.interval * 2


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """Load balancing implementation."""

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self._rr_index: Dict[str, int] = defaultdict(int)
        self._connection_counts: Dict[str, int] = defaultdict(int)

    def select(
        self,
        instances: List[ServiceInstance],
        client_key: str = None
    ) -> Optional[ServiceInstance]:
        """Select an instance based on strategy."""
        if not instances:
            return None

        # Filter healthy instances
        healthy = [i for i in instances if i.status == ServiceStatus.HEALTHY]
        if not healthy:
            healthy = instances  # Fallback to all if none healthy

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(healthy)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(healthy)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted(healthy)
        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            return self._ip_hash(healthy, client_key)
        elif self.strategy == LoadBalancingStrategy.LEAST_LATENCY:
            return self._least_latency(healthy)

        return healthy[0]

    def _round_robin(self, instances: List[ServiceInstance]) -> ServiceInstance:
        service_name = instances[0].service_name
        index = self._rr_index[service_name]
        self._rr_index[service_name] = (index + 1) % len(instances)
        return instances[index % len(instances)]

    def _least_connections(self, instances: List[ServiceInstance]) -> ServiceInstance:
        return min(instances, key=lambda i: i.connections)

    def _weighted(self, instances: List[ServiceInstance]) -> ServiceInstance:
        total_weight = sum(i.weight for i in instances)
        r = random.uniform(0, total_weight)

        cumulative = 0
        for instance in instances:
            cumulative += instance.weight
            if r <= cumulative:
                return instance

        return instances[-1]

    def _ip_hash(
        self,
        instances: List[ServiceInstance],
        client_key: str
    ) -> ServiceInstance:
        if not client_key:
            return random.choice(instances)

        hash_value = int(hashlib.md5(client_key.encode()).hexdigest(), 16)
        return instances[hash_value % len(instances)]

    def _least_latency(self, instances: List[ServiceInstance]) -> ServiceInstance:
        return min(instances, key=lambda i: i.avg_latency_ms or float('inf'))

    def record_connection(self, instance_id: str) -> None:
        """Record a new connection."""
        self._connection_counts[instance_id] += 1

    def release_connection(self, instance_id: str) -> None:
        """Release a connection."""
        if self._connection_counts[instance_id] > 0:
            self._connection_counts[instance_id] -= 1


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

class ServiceRegistry(ABC):
    """Abstract service registry."""

    @abstractmethod
    async def register(self, instance: ServiceInstance) -> bool:
        pass

    @abstractmethod
    async def deregister(self, instance_id: str) -> bool:
        pass

    @abstractmethod
    async def get_instances(self, service_name: str) -> List[ServiceInstance]:
        pass

    @abstractmethod
    async def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        pass


class MemoryServiceRegistry(ServiceRegistry):
    """In-memory service registry."""

    def __init__(self):
        self.instances: Dict[str, ServiceInstance] = {}
        self.by_service: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def register(self, instance: ServiceInstance) -> bool:
        async with self._lock:
            self.instances[instance.id] = instance
            self.by_service[instance.service_name].add(instance.id)
            return True

    async def deregister(self, instance_id: str) -> bool:
        async with self._lock:
            if instance_id in self.instances:
                instance = self.instances.pop(instance_id)
                self.by_service[instance.service_name].discard(instance_id)
                return True
            return False

    async def get_instances(self, service_name: str) -> List[ServiceInstance]:
        async with self._lock:
            instance_ids = self.by_service.get(service_name, set())
            return [
                self.instances[iid] for iid in instance_ids
                if iid in self.instances
            ]

    async def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        async with self._lock:
            return self.instances.get(instance_id)

    async def get_all_services(self) -> List[str]:
        async with self._lock:
            return list(self.by_service.keys())

    async def update_status(
        self,
        instance_id: str,
        status: ServiceStatus
    ) -> bool:
        async with self._lock:
            if instance_id in self.instances:
                self.instances[instance_id].status = status
                return True
            return False


class FileServiceRegistry(ServiceRegistry):
    """File-based service registry."""

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._memory = MemoryServiceRegistry()

    async def register(self, instance: ServiceInstance) -> bool:
        await self._memory.register(instance)
        await self._save(instance)
        return True

    async def deregister(self, instance_id: str) -> bool:
        path = self.directory / f"{instance_id}.json"
        if path.exists():
            path.unlink()
        return await self._memory.deregister(instance_id)

    async def get_instances(self, service_name: str) -> List[ServiceInstance]:
        return await self._memory.get_instances(service_name)

    async def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        return await self._memory.get_instance(instance_id)

    async def _save(self, instance: ServiceInstance) -> None:
        path = self.directory / f"{instance.id}.json"
        with open(path, 'w') as f:
            json.dump(instance.to_dict(), f, indent=2)

    async def load_all(self) -> int:
        """Load all instances from files."""
        count = 0
        for path in self.directory.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)

                endpoint = None
                if data.get("endpoint"):
                    endpoint = ServiceEndpoint(
                        host=data["endpoint"]["host"],
                        port=data["endpoint"]["port"],
                        protocol=ServiceProtocol(data["endpoint"]["protocol"])
                    )

                instance = ServiceInstance(
                    id=data["id"],
                    service_name=data["service_name"],
                    version=data.get("version", "1.0.0"),
                    endpoint=endpoint,
                    status=ServiceStatus(data.get("status", "unknown")),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                    weight=data.get("weight", 100)
                )

                await self._memory.register(instance)
                count += 1
            except Exception as e:
                logger.error(f"Failed to load {path}: {e}")

        return count


# =============================================================================
# SERVICE DISCOVERY
# =============================================================================

class ServiceDiscovery:
    """
    Master service discovery for BAEL.

    Provides comprehensive service registration and discovery.
    """

    def __init__(
        self,
        registry: ServiceRegistry = None,
        load_balancer: LoadBalancer = None
    ):
        self.registry = registry or MemoryServiceRegistry()
        self.load_balancer = load_balancer or LoadBalancer()
        self.health_checker = HealthChecker()

        # Definitions
        self.definitions: Dict[str, ServiceDefinition] = {}

        # Watchers
        self.watchers: Dict[str, List[Callable[[ServiceEvent], None]]] = defaultdict(list)

        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

        # Cache
        self._cache: Dict[str, Tuple[List[ServiceInstance], datetime]] = {}
        self._cache_ttl = 5.0  # seconds

        # Statistics
        self.registrations = 0
        self.deregistrations = 0
        self.lookups = 0
        self.health_checks = 0

    async def start(self) -> None:
        """Start background tasks."""
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    # Service Definition
    def define_service(self, definition: ServiceDefinition) -> None:
        """Define a service type."""
        self.definitions[definition.name] = definition

    def get_definition(self, name: str) -> Optional[ServiceDefinition]:
        """Get service definition."""
        return self.definitions.get(name)

    # Registration
    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        protocol: ServiceProtocol = ServiceProtocol.HTTP,
        version: str = "1.0.0",
        tags: List[str] = None,
        metadata: Dict[str, str] = None,
        weight: int = 100,
        health_check: HealthCheckConfig = None
    ) -> ServiceInstance:
        """Register a service instance."""
        instance = ServiceInstance(
            service_name=service_name,
            version=version,
            endpoint=ServiceEndpoint(host, port, protocol),
            status=ServiceStatus.STARTING,
            health_check=health_check or HealthCheckConfig(),
            tags=tags or [],
            metadata=metadata or {},
            weight=weight
        )

        await self.registry.register(instance)
        self.registrations += 1

        # Invalidate cache
        self._cache.pop(service_name, None)

        # Notify watchers
        await self._emit_event(ServiceEvent(
            event_type=EventType.REGISTERED,
            service_name=service_name,
            instance_id=instance.id,
            instance=instance
        ))

        return instance

    async def deregister(self, instance_id: str) -> bool:
        """Deregister a service instance."""
        instance = await self.registry.get_instance(instance_id)
        if not instance:
            return False

        result = await self.registry.deregister(instance_id)

        if result:
            self.deregistrations += 1
            self._cache.pop(instance.service_name, None)

            await self._emit_event(ServiceEvent(
                event_type=EventType.DEREGISTERED,
                service_name=instance.service_name,
                instance_id=instance_id
            ))

        return result

    # Discovery
    async def discover(
        self,
        service_name: str,
        tags: List[str] = None,
        version: str = None,
        healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """Discover service instances."""
        self.lookups += 1

        # Check cache
        if service_name in self._cache:
            instances, cached_at = self._cache[service_name]
            if (datetime.now() - cached_at).total_seconds() < self._cache_ttl:
                return self._filter_instances(instances, tags, version, healthy_only)

        # Get from registry
        instances = await self.registry.get_instances(service_name)

        # Update cache
        self._cache[service_name] = (instances, datetime.now())

        return self._filter_instances(instances, tags, version, healthy_only)

    def _filter_instances(
        self,
        instances: List[ServiceInstance],
        tags: List[str] = None,
        version: str = None,
        healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """Filter instances by criteria."""
        result = instances

        if healthy_only:
            result = [i for i in result if i.status == ServiceStatus.HEALTHY]

        if tags:
            result = [i for i in result if all(t in i.tags for t in tags)]

        if version:
            result = [i for i in result if i.version == version]

        return result

    async def resolve(
        self,
        service_name: str,
        client_key: str = None,
        tags: List[str] = None
    ) -> Optional[ServiceInstance]:
        """Resolve to a single instance using load balancing."""
        instances = await self.discover(service_name, tags=tags)
        return self.load_balancer.select(instances, client_key)

    async def resolve_url(
        self,
        service_name: str,
        path: str = "",
        client_key: str = None
    ) -> Optional[str]:
        """Resolve to a URL."""
        instance = await self.resolve(service_name, client_key)
        if not instance:
            return None

        base = instance.endpoint.url
        return f"{base}{path}" if path else base

    # Health Management
    async def update_health(
        self,
        instance_id: str,
        healthy: bool
    ) -> None:
        """Update instance health status."""
        instance = await self.registry.get_instance(instance_id)
        if not instance:
            return

        old_status = instance.status

        if healthy:
            instance.unhealthy_count = 0
            instance.healthy_count += 1

            if instance.healthy_count >= instance.health_check.healthy_threshold:
                instance.status = ServiceStatus.HEALTHY
        else:
            instance.healthy_count = 0
            instance.unhealthy_count += 1

            if instance.unhealthy_count >= instance.health_check.unhealthy_threshold:
                instance.status = ServiceStatus.UNHEALTHY

        instance.last_health_check = datetime.now()

        if old_status != instance.status:
            self._cache.pop(instance.service_name, None)

            await self._emit_event(ServiceEvent(
                event_type=EventType.HEALTH_CHANGED,
                service_name=instance.service_name,
                instance_id=instance_id,
                instance=instance,
                details={
                    "old_status": old_status.value,
                    "new_status": instance.status.value
                }
            ))

    async def heartbeat(self, instance_id: str) -> bool:
        """Send heartbeat for TTL-based health check."""
        instance = await self.registry.get_instance(instance_id)
        if not instance:
            return False

        instance.last_health_check = datetime.now()
        await self.update_health(instance_id, True)
        return True

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                # Get all services
                if isinstance(self.registry, MemoryServiceRegistry):
                    services = await self.registry.get_all_services()
                else:
                    services = list(self.definitions.keys())

                for service_name in services:
                    instances = await self.registry.get_instances(service_name)

                    for instance in instances:
                        if instance.health_check.check_type != HealthCheckType.TTL:
                            healthy = await self.health_checker.check_health(
                                instance,
                                instance.health_check
                            )
                            await self.update_health(instance.id, healthy)
                            self.health_checks += 1

                await asyncio.sleep(10)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)

    # Watch/Subscribe
    def watch(
        self,
        service_name: str,
        callback: Callable[[ServiceEvent], None]
    ) -> str:
        """Watch a service for changes."""
        watch_id = str(uuid.uuid4())
        self.watchers[service_name].append(callback)
        return watch_id

    def unwatch(self, service_name: str, watch_id: str) -> bool:
        """Stop watching a service."""
        # Simple implementation - remove last watcher
        if service_name in self.watchers and self.watchers[service_name]:
            self.watchers[service_name].pop()
            return True
        return False

    async def _emit_event(self, event: ServiceEvent) -> None:
        """Emit event to watchers."""
        callbacks = self.watchers.get(event.service_name, [])
        callbacks += self.watchers.get("*", [])  # Global watchers

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Watcher callback error: {e}")

    # Utilities
    async def list_services(self) -> List[str]:
        """List all registered services."""
        if isinstance(self.registry, MemoryServiceRegistry):
            return await self.registry.get_all_services()
        return list(self.definitions.keys())

    async def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get detailed service info."""
        instances = await self.registry.get_instances(service_name)
        definition = self.definitions.get(service_name)

        healthy = sum(1 for i in instances if i.status == ServiceStatus.HEALTHY)
        unhealthy = sum(1 for i in instances if i.status == ServiceStatus.UNHEALTHY)

        return {
            "name": service_name,
            "definition": definition.description if definition else None,
            "instances": len(instances),
            "healthy": healthy,
            "unhealthy": unhealthy,
            "versions": list(set(i.version for i in instances))
        }

    def set_load_balancing_strategy(
        self,
        strategy: LoadBalancingStrategy
    ) -> None:
        """Set load balancing strategy."""
        self.load_balancer.strategy = strategy

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "registrations": self.registrations,
            "deregistrations": self.deregistrations,
            "lookups": self.lookups,
            "health_checks": self.health_checks,
            "cache_size": len(self._cache),
            "watchers": sum(len(w) for w in self.watchers.values())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Service Discovery System."""
    print("=" * 70)
    print("BAEL - SERVICE DISCOVERY SYSTEM DEMO")
    print("Dynamic Service Registration and Discovery")
    print("=" * 70)
    print()

    discovery = ServiceDiscovery()
    await discovery.start()

    try:
        # 1. Service Registration
        print("1. SERVICE REGISTRATION:")
        print("-" * 40)

        api1 = await discovery.register(
            service_name="api-gateway",
            host="10.0.0.1",
            port=8080,
            tags=["api", "v1"],
            metadata={"region": "us-east"}
        )
        print(f"   Registered: {api1.service_name} @ {api1.endpoint.address}")

        api2 = await discovery.register(
            service_name="api-gateway",
            host="10.0.0.2",
            port=8080,
            tags=["api", "v1"],
            metadata={"region": "us-west"}
        )
        print(f"   Registered: {api2.service_name} @ {api2.endpoint.address}")

        db = await discovery.register(
            service_name="database",
            host="10.0.1.1",
            port=5432,
            protocol=ServiceProtocol.TCP,
            tags=["postgres", "primary"]
        )
        print(f"   Registered: {db.service_name} @ {db.endpoint.address}")
        print()

        # 2. Health Updates
        print("2. HEALTH UPDATES:")
        print("-" * 40)

        await discovery.update_health(api1.id, True)
        await discovery.update_health(api1.id, True)  # Meet threshold
        print(f"   {api1.endpoint.address} status: {api1.status.value}")

        await discovery.update_health(api2.id, True)
        await discovery.update_health(api2.id, True)
        print(f"   {api2.endpoint.address} status: {api2.status.value}")
        print()

        # 3. Service Discovery
        print("3. SERVICE DISCOVERY:")
        print("-" * 40)

        instances = await discovery.discover("api-gateway")
        print(f"   Found {len(instances)} api-gateway instances:")
        for inst in instances:
            print(f"      - {inst.endpoint.address} ({inst.status.value})")
        print()

        # 4. Load Balancing
        print("4. LOAD BALANCING (Round Robin):")
        print("-" * 40)

        for i in range(4):
            instance = await discovery.resolve("api-gateway")
            print(f"   Request {i + 1}: routed to {instance.endpoint.address}")
        print()

        # 5. Different Strategies
        print("5. LOAD BALANCING STRATEGIES:")
        print("-" * 40)

        discovery.set_load_balancing_strategy(LoadBalancingStrategy.RANDOM)
        selected = [
            (await discovery.resolve("api-gateway")).endpoint.address
            for _ in range(10)
        ]
        print(f"   Random: {selected}")

        discovery.set_load_balancing_strategy(LoadBalancingStrategy.IP_HASH)
        ip1 = await discovery.resolve("api-gateway", "192.168.1.1")
        ip2 = await discovery.resolve("api-gateway", "192.168.1.1")
        print(f"   IP Hash (same IP): {ip1.endpoint.address} == {ip2.endpoint.address}")
        print()

        # 6. URL Resolution
        print("6. URL RESOLUTION:")
        print("-" * 40)

        url = await discovery.resolve_url("api-gateway", "/api/v1/users")
        print(f"   Resolved URL: {url}")
        print()

        # 7. Tag Filtering
        print("7. TAG FILTERING:")
        print("-" * 40)

        v1_instances = await discovery.discover("api-gateway", tags=["v1"])
        print(f"   Instances with 'v1' tag: {len(v1_instances)}")

        postgres = await discovery.discover("database", tags=["postgres"])
        print(f"   Instances with 'postgres' tag: {len(postgres)}")
        print()

        # 8. Watch Events
        print("8. WATCH EVENTS:")
        print("-" * 40)

        events_received = []

        def on_event(event: ServiceEvent):
            events_received.append(event.event_type.value)

        discovery.watch("cache", on_event)

        cache = await discovery.register(
            service_name="cache",
            host="10.0.2.1",
            port=6379,
            tags=["redis"]
        )

        await discovery.deregister(cache.id)

        print(f"   Events received: {events_received}")
        print()

        # 9. Service Info
        print("9. SERVICE INFO:")
        print("-" * 40)

        info = await discovery.get_service_info("api-gateway")
        for key, value in info.items():
            print(f"   {key}: {value}")
        print()

        # 10. Statistics
        print("10. STATISTICS:")
        print("-" * 40)

        stats = discovery.get_statistics()
        for key, value in stats.items():
            print(f"    {key}: {value}")
        print()

    finally:
        await discovery.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Service Discovery System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
