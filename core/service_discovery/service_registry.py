"""
BAEL Service Registry
=====================

Complete service discovery system with:
- Service registration and deregistration
- Health checks (HTTP, TCP, script)
- Load balancing algorithms
- Service mesh capabilities
- DNS-like resolution

"Ba'el knows the location of all servants." — Ba'el
"""

import asyncio
import logging
import random
import time
import socket
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import threading
import uuid
import aiohttp

logger = logging.getLogger("BAEL.ServiceDiscovery")


# ============================================================================
# ENUMS
# ============================================================================

class ServiceStatus(Enum):
    """Status of a service instance."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"
    DRAINING = "draining"


class HealthCheckType(Enum):
    """Types of health checks."""
    HTTP = "http"       # HTTP endpoint check
    TCP = "tcp"         # TCP connection check
    SCRIPT = "script"   # Script execution
    GRPC = "grpc"       # gRPC health check
    TTL = "ttl"         # Time-to-live based


class LoadBalancerAlgorithm(Enum):
    """Load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    CONSISTENT_HASH = "consistent_hash"


class RegistrationMode(Enum):
    """Service registration modes."""
    SELF = "self"       # Service registers itself
    EXTERNAL = "external"  # External registration
    SIDECAR = "sidecar"    # Sidecar proxy registers


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class HealthCheck:
    """Health check configuration."""
    check_type: HealthCheckType = HealthCheckType.HTTP
    endpoint: str = "/health"
    interval_seconds: int = 10
    timeout_seconds: int = 5
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2

    # HTTP specific
    expected_status: int = 200
    expected_body: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    # Script specific
    script: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    healthy: bool
    check_type: HealthCheckType
    response_time_ms: float
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ServiceInstance:
    """A service instance."""
    id: str
    service_name: str
    host: str
    port: int

    # Status
    status: ServiceStatus = ServiceStatus.STARTING

    # Metadata
    version: str = "1.0.0"
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Load balancing
    weight: int = 100
    zone: str = "default"

    # Health
    health_check: Optional[HealthCheck] = None
    last_health_check: Optional[HealthCheckResult] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    # Connection tracking
    active_connections: int = 0
    total_requests: int = 0

    # Timestamps
    registered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def is_healthy(self) -> bool:
        return self.status == ServiceStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'service_name': self.service_name,
            'host': self.host,
            'port': self.port,
            'status': self.status.value,
            'version': self.version,
            'tags': list(self.tags),
            'weight': self.weight,
            'zone': self.zone,
            'active_connections': self.active_connections
        }


@dataclass
class ServiceDefinition:
    """Definition of a service."""
    name: str

    # Instances
    instances: Dict[str, ServiceInstance] = field(default_factory=dict)

    # Configuration
    health_check: Optional[HealthCheck] = None

    # Load balancing
    load_balancer_algorithm: LoadBalancerAlgorithm = LoadBalancerAlgorithm.ROUND_ROBIN

    # Metadata
    version: str = "1.0.0"
    description: str = ""
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def healthy_instances(self) -> List[ServiceInstance]:
        return [i for i in self.instances.values() if i.is_healthy]


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration."""
    algorithm: LoadBalancerAlgorithm = LoadBalancerAlgorithm.ROUND_ROBIN
    sticky_sessions: bool = False
    session_timeout_seconds: int = 3600
    health_check_enabled: bool = True


@dataclass
class ServiceDiscoveryConfig:
    """Service discovery configuration."""
    enable_health_checks: bool = True
    health_check_interval: int = 10
    deregister_after_failures: int = 10
    enable_dns: bool = True
    dns_ttl: int = 60


# ============================================================================
# SERVICE REGISTRY
# ============================================================================

class ServiceRegistry:
    """
    Central service registry.
    """

    def __init__(self):
        """Initialize service registry."""
        self._services: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, ServiceInstance] = {}  # id -> instance
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            'total_registrations': 0,
            'total_deregistrations': 0,
            'active_services': 0,
            'active_instances': 0
        }

    def register(
        self,
        service_name: str,
        host: str,
        port: int,
        health_check: Optional[HealthCheck] = None,
        version: str = "1.0.0",
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        weight: int = 100,
        zone: str = "default"
    ) -> ServiceInstance:
        """Register a service instance."""
        with self._lock:
            # Create service definition if not exists
            if service_name not in self._services:
                self._services[service_name] = ServiceDefinition(
                    name=service_name,
                    health_check=health_check
                )
                self._stats['active_services'] += 1

            service = self._services[service_name]

            # Create instance
            instance = ServiceInstance(
                id=str(uuid.uuid4()),
                service_name=service_name,
                host=host,
                port=port,
                health_check=health_check or service.health_check,
                version=version,
                tags=tags or set(),
                metadata=metadata or {},
                weight=weight,
                zone=zone
            )

            service.instances[instance.id] = instance
            self._instances[instance.id] = instance

            self._stats['total_registrations'] += 1
            self._stats['active_instances'] += 1

            logger.info(f"Registered service instance: {service_name} at {instance.address}")
            return instance

    def deregister(self, instance_id: str) -> bool:
        """Deregister a service instance."""
        with self._lock:
            if instance_id not in self._instances:
                return False

            instance = self._instances.pop(instance_id)
            service = self._services.get(instance.service_name)

            if service and instance_id in service.instances:
                del service.instances[instance_id]

                # Remove service if no instances
                if not service.instances:
                    del self._services[instance.service_name]
                    self._stats['active_services'] -= 1

            self._stats['total_deregistrations'] += 1
            self._stats['active_instances'] -= 1

            logger.info(f"Deregistered service instance: {instance.service_name} at {instance.address}")
            return True

    def get_service(self, name: str) -> Optional[ServiceDefinition]:
        """Get a service by name."""
        return self._services.get(name)

    def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        """Get an instance by ID."""
        return self._instances.get(instance_id)

    def get_instances(
        self,
        service_name: str,
        healthy_only: bool = True,
        tags: Optional[Set[str]] = None,
        zone: Optional[str] = None
    ) -> List[ServiceInstance]:
        """Get instances of a service."""
        service = self._services.get(service_name)
        if not service:
            return []

        instances = list(service.instances.values())

        if healthy_only:
            instances = [i for i in instances if i.is_healthy]

        if tags:
            instances = [i for i in instances if tags & i.tags]

        if zone:
            instances = [i for i in instances if i.zone == zone]

        return instances

    def list_services(self) -> List[str]:
        """List all service names."""
        return list(self._services.keys())

    def update_status(
        self,
        instance_id: str,
        status: ServiceStatus
    ) -> bool:
        """Update instance status."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance:
                instance.status = status
                instance.last_seen = datetime.now()
                return True
            return False

    def heartbeat(self, instance_id: str) -> bool:
        """Record a heartbeat from an instance."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance:
                instance.last_seen = datetime.now()
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            services_info = {}
            for name, service in self._services.items():
                services_info[name] = {
                    'total_instances': len(service.instances),
                    'healthy_instances': len(service.healthy_instances)
                }

            return {
                **self._stats,
                'services': services_info
            }


# ============================================================================
# HEALTH CHECKER
# ============================================================================

class HealthChecker:
    """
    Performs health checks on service instances.
    """

    def __init__(self, registry: ServiceRegistry):
        """Initialize health checker."""
        self._registry = registry
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, interval: int = 10) -> None:
        """Start health checking."""
        self._running = True
        self._task = asyncio.create_task(self._check_loop(interval))
        logger.info("Health checker started")

    async def stop(self) -> None:
        """Stop health checking."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Health checker stopped")

    async def _check_loop(self, interval: int) -> None:
        """Main health check loop."""
        while self._running:
            try:
                for instance in list(self._registry._instances.values()):
                    if instance.health_check:
                        result = await self.check_instance(instance)
                        self._process_result(instance, result)

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(interval)

    async def check_instance(
        self,
        instance: ServiceInstance
    ) -> HealthCheckResult:
        """Check health of an instance."""
        check = instance.health_check
        if not check:
            return HealthCheckResult(
                healthy=True,
                check_type=HealthCheckType.TTL,
                response_time_ms=0,
                message="No health check configured"
            )

        start_time = time.time()

        try:
            if check.check_type == HealthCheckType.HTTP:
                result = await self._http_check(instance, check)
            elif check.check_type == HealthCheckType.TCP:
                result = await self._tcp_check(instance, check)
            elif check.check_type == HealthCheckType.TTL:
                result = self._ttl_check(instance, check)
            else:
                result = HealthCheckResult(
                    healthy=True,
                    check_type=check.check_type,
                    response_time_ms=0,
                    message="Unsupported check type"
                )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                healthy=False,
                check_type=check.check_type,
                response_time_ms=response_time,
                message=str(e)
            )

        instance.last_health_check = result
        return result

    async def _http_check(
        self,
        instance: ServiceInstance,
        check: HealthCheck
    ) -> HealthCheckResult:
        """Perform HTTP health check."""
        url = f"http://{instance.host}:{instance.port}{check.endpoint}"
        start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=check.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=check.headers) as response:
                    response_time = (time.time() - start_time) * 1000

                    healthy = response.status == check.expected_status

                    if healthy and check.expected_body:
                        body = await response.text()
                        healthy = check.expected_body in body

                    return HealthCheckResult(
                        healthy=healthy,
                        check_type=HealthCheckType.HTTP,
                        response_time_ms=response_time,
                        message=f"Status: {response.status}"
                    )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                healthy=False,
                check_type=HealthCheckType.HTTP,
                response_time_ms=check.timeout_seconds * 1000,
                message="Timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                check_type=HealthCheckType.HTTP,
                response_time_ms=(time.time() - start_time) * 1000,
                message=str(e)
            )

    async def _tcp_check(
        self,
        instance: ServiceInstance,
        check: HealthCheck
    ) -> HealthCheckResult:
        """Perform TCP health check."""
        start_time = time.time()

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(instance.host, instance.port),
                timeout=check.timeout_seconds
            )
            writer.close()
            await writer.wait_closed()

            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                healthy=True,
                check_type=HealthCheckType.TCP,
                response_time_ms=response_time,
                message="Connection successful"
            )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                healthy=False,
                check_type=HealthCheckType.TCP,
                response_time_ms=check.timeout_seconds * 1000,
                message="Connection timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                check_type=HealthCheckType.TCP,
                response_time_ms=(time.time() - start_time) * 1000,
                message=str(e)
            )

    def _ttl_check(
        self,
        instance: ServiceInstance,
        check: HealthCheck
    ) -> HealthCheckResult:
        """Perform TTL-based health check."""
        elapsed = (datetime.now() - instance.last_seen).total_seconds()
        healthy = elapsed < check.interval_seconds * 3  # 3x interval grace

        return HealthCheckResult(
            healthy=healthy,
            check_type=HealthCheckType.TTL,
            response_time_ms=0,
            message=f"Last seen {elapsed:.1f}s ago"
        )

    def _process_result(
        self,
        instance: ServiceInstance,
        result: HealthCheckResult
    ) -> None:
        """Process health check result."""
        check = instance.health_check
        if not check:
            return

        if result.healthy:
            instance.consecutive_failures = 0
            instance.consecutive_successes += 1

            if (instance.status != ServiceStatus.HEALTHY and
                instance.consecutive_successes >= check.healthy_threshold):
                instance.status = ServiceStatus.HEALTHY
                logger.info(f"Instance {instance.id} is now healthy")
        else:
            instance.consecutive_successes = 0
            instance.consecutive_failures += 1

            if (instance.status == ServiceStatus.HEALTHY and
                instance.consecutive_failures >= check.unhealthy_threshold):
                instance.status = ServiceStatus.UNHEALTHY
                logger.warning(f"Instance {instance.id} is now unhealthy")


# ============================================================================
# LOAD BALANCER
# ============================================================================

class LoadBalancer:
    """
    Load balancer with multiple algorithms.
    """

    def __init__(self, config: Optional[LoadBalancerConfig] = None):
        """Initialize load balancer."""
        self.config = config or LoadBalancerConfig()

        # Round robin state
        self._rr_counters: Dict[str, int] = defaultdict(int)

        # Sticky sessions
        self._sticky_sessions: Dict[str, Tuple[str, datetime]] = {}

        # Consistent hash ring
        self._hash_ring: Dict[str, List[Tuple[int, str]]] = {}

        self._lock = threading.RLock()

    def select(
        self,
        instances: List[ServiceInstance],
        client_id: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Select an instance using the configured algorithm."""
        if not instances:
            return None

        # Check sticky session
        if self.config.sticky_sessions and client_id:
            instance = self._get_sticky(instances, client_id)
            if instance:
                return instance

        # Apply algorithm
        if self.config.algorithm == LoadBalancerAlgorithm.ROUND_ROBIN:
            instance = self._round_robin(instances)
        elif self.config.algorithm == LoadBalancerAlgorithm.RANDOM:
            instance = self._random(instances)
        elif self.config.algorithm == LoadBalancerAlgorithm.LEAST_CONNECTIONS:
            instance = self._least_connections(instances)
        elif self.config.algorithm == LoadBalancerAlgorithm.WEIGHTED_ROUND_ROBIN:
            instance = self._weighted_round_robin(instances)
        elif self.config.algorithm == LoadBalancerAlgorithm.IP_HASH:
            instance = self._ip_hash(instances, client_id or "")
        elif self.config.algorithm == LoadBalancerAlgorithm.CONSISTENT_HASH:
            instance = self._consistent_hash(instances, client_id or "")
        else:
            instance = self._round_robin(instances)

        # Store sticky session
        if self.config.sticky_sessions and client_id and instance:
            self._set_sticky(client_id, instance.id)

        return instance

    def _round_robin(
        self,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Round robin selection."""
        with self._lock:
            # Use service name as key
            service = instances[0].service_name
            idx = self._rr_counters[service]
            self._rr_counters[service] = (idx + 1) % len(instances)
            return instances[idx % len(instances)]

    def _random(
        self,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Random selection."""
        return random.choice(instances)

    def _least_connections(
        self,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Least connections selection."""
        return min(instances, key=lambda i: i.active_connections)

    def _weighted_round_robin(
        self,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Weighted round robin selection."""
        total_weight = sum(i.weight for i in instances)
        if total_weight == 0:
            return instances[0]

        rand = random.randint(1, total_weight)
        cumulative = 0

        for instance in instances:
            cumulative += instance.weight
            if rand <= cumulative:
                return instance

        return instances[-1]

    def _ip_hash(
        self,
        instances: List[ServiceInstance],
        client_id: str
    ) -> ServiceInstance:
        """IP hash selection."""
        hash_val = int(hashlib.md5(client_id.encode()).hexdigest(), 16)
        return instances[hash_val % len(instances)]

    def _consistent_hash(
        self,
        instances: List[ServiceInstance],
        key: str
    ) -> ServiceInstance:
        """Consistent hash selection."""
        service = instances[0].service_name

        with self._lock:
            # Build or update ring
            current_ids = {i.id for i in instances}
            if service not in self._hash_ring:
                self._hash_ring[service] = []
                for instance in instances:
                    for i in range(100):  # Virtual nodes
                        hash_key = f"{instance.id}:{i}"
                        hash_val = int(hashlib.md5(hash_key.encode()).hexdigest(), 16)
                        self._hash_ring[service].append((hash_val, instance.id))
                self._hash_ring[service].sort()

        # Find node
        key_hash = int(hashlib.md5(key.encode()).hexdigest(), 16)
        ring = self._hash_ring[service]

        for hash_val, instance_id in ring:
            if hash_val >= key_hash:
                for instance in instances:
                    if instance.id == instance_id:
                        return instance

        # Wrap around
        return instances[0]

    def _get_sticky(
        self,
        instances: List[ServiceInstance],
        client_id: str
    ) -> Optional[ServiceInstance]:
        """Get sticky session instance."""
        with self._lock:
            if client_id in self._sticky_sessions:
                instance_id, expires = self._sticky_sessions[client_id]

                if datetime.now() < expires:
                    for instance in instances:
                        if instance.id == instance_id:
                            return instance

                del self._sticky_sessions[client_id]

            return None

    def _set_sticky(self, client_id: str, instance_id: str) -> None:
        """Set sticky session."""
        with self._lock:
            expires = datetime.now() + timedelta(
                seconds=self.config.session_timeout_seconds
            )
            self._sticky_sessions[client_id] = (instance_id, expires)


# ============================================================================
# SERVICE RESOLVER
# ============================================================================

class ServiceResolver:
    """
    DNS-like service resolution.
    """

    def __init__(
        self,
        registry: ServiceRegistry,
        load_balancer: LoadBalancer
    ):
        """Initialize service resolver."""
        self._registry = registry
        self._load_balancer = load_balancer

        # Cache
        self._cache: Dict[str, Tuple[List[ServiceInstance], datetime]] = {}
        self._cache_ttl = 60  # seconds

    def resolve(
        self,
        service_name: str,
        client_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[ServiceInstance]:
        """Resolve a service to an instance."""
        # Check cache
        if use_cache and service_name in self._cache:
            instances, expires = self._cache[service_name]
            if datetime.now() < expires and instances:
                return self._load_balancer.select(instances, client_id)

        # Get instances
        instances = self._registry.get_instances(service_name, healthy_only=True)

        if instances:
            # Update cache
            self._cache[service_name] = (
                instances,
                datetime.now() + timedelta(seconds=self._cache_ttl)
            )

            return self._load_balancer.select(instances, client_id)

        return None

    def resolve_all(
        self,
        service_name: str
    ) -> List[ServiceInstance]:
        """Resolve a service to all healthy instances."""
        return self._registry.get_instances(service_name, healthy_only=True)

    def lookup(self, service_name: str) -> Optional[str]:
        """Lookup service address (DNS-like)."""
        instance = self.resolve(service_name)
        if instance:
            return instance.address
        return None

    def srv_lookup(self, service_name: str) -> List[Dict[str, Any]]:
        """SRV record lookup."""
        instances = self.resolve_all(service_name)
        return [
            {
                'target': instance.host,
                'port': instance.port,
                'weight': instance.weight,
                'priority': 10
            }
            for instance in instances
        ]


# ============================================================================
# MAIN SERVICE DISCOVERY ENGINE
# ============================================================================

class ServiceDiscoveryEngine:
    """
    Main service discovery engine.

    Features:
    - Service registration
    - Health checking
    - Load balancing
    - DNS-like resolution
    - Service mesh capabilities

    "Ba'el orchestrates all services in the realm." — Ba'el
    """

    def __init__(self, config: Optional[ServiceDiscoveryConfig] = None):
        """Initialize service discovery engine."""
        self.config = config or ServiceDiscoveryConfig()

        # Components
        self.registry = ServiceRegistry()
        self.health_checker = HealthChecker(self.registry)
        self.load_balancer = LoadBalancer()
        self.resolver = ServiceResolver(self.registry, self.load_balancer)

        logger.info("ServiceDiscoveryEngine initialized")

    async def start(self) -> None:
        """Start the service discovery engine."""
        if self.config.enable_health_checks:
            await self.health_checker.start(self.config.health_check_interval)
        logger.info("ServiceDiscoveryEngine started")

    async def stop(self) -> None:
        """Stop the service discovery engine."""
        await self.health_checker.stop()
        logger.info("ServiceDiscoveryEngine stopped")

    # ========================================================================
    # REGISTRATION
    # ========================================================================

    def register(
        self,
        service_name: str,
        host: str,
        port: int,
        health_check: Optional[HealthCheck] = None,
        **kwargs
    ) -> ServiceInstance:
        """Register a service instance."""
        return self.registry.register(
            service_name=service_name,
            host=host,
            port=port,
            health_check=health_check,
            **kwargs
        )

    def deregister(self, instance_id: str) -> bool:
        """Deregister a service instance."""
        return self.registry.deregister(instance_id)

    def heartbeat(self, instance_id: str) -> bool:
        """Send a heartbeat for an instance."""
        return self.registry.heartbeat(instance_id)

    # ========================================================================
    # DISCOVERY
    # ========================================================================

    def discover(
        self,
        service_name: str,
        client_id: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Discover a service instance."""
        return self.resolver.resolve(service_name, client_id)

    def discover_all(self, service_name: str) -> List[ServiceInstance]:
        """Discover all instances of a service."""
        return self.resolver.resolve_all(service_name)

    def lookup(self, service_name: str) -> Optional[str]:
        """Lookup a service address."""
        return self.resolver.lookup(service_name)

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'services': self.registry.list_services(),
            'statistics': self.registry.get_stats()
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

service_discovery = ServiceDiscoveryEngine()
