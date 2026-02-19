"""
BAEL Service Mesh Engine Implementation
========================================

Service mesh for microservice communication.

"Ba'el weaves the mesh that connects all services." — Ba'el
"""

import asyncio
import logging
import threading
import time
import random
import hashlib
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("BAEL.ServiceMesh")


# ============================================================================
# ENUMS
# ============================================================================

class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    CONSISTENT_HASH = "consistent_hash"
    LEAST_LATENCY = "least_latency"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject calls
    HALF_OPEN = "half_open" # Testing if recovered


class ServiceState(Enum):
    """Service states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ServiceEndpoint:
    """A service endpoint."""
    id: str
    service_name: str
    host: str
    port: int

    # State
    state: ServiceState = ServiceState.UNKNOWN
    weight: float = 1.0

    # Metrics
    connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0

    # Circuit breaker
    circuit_state: CircuitState = CircuitState.CLOSED
    circuit_failures: int = 0
    circuit_opened_at: Optional[datetime] = None

    # Timestamps
    registered_at: datetime = field(default_factory=datetime.now)
    last_health_check: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def is_available(self) -> bool:
        """Check if endpoint is available."""
        if self.state == ServiceState.UNHEALTHY:
            return False
        if self.circuit_state == CircuitState.OPEN:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'service_name': self.service_name,
            'host': self.host,
            'port': self.port,
            'address': self.address,
            'state': self.state.value,
            'weight': self.weight,
            'connections': self.connections,
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'avg_latency_ms': self.avg_latency_ms,
            'circuit_state': self.circuit_state.value,
            'metadata': self.metadata
        }


@dataclass
class ServiceMeshConfig:
    """Service mesh configuration."""
    # Load balancing
    default_strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN

    # Circuit breaker
    circuit_threshold: int = 5          # Failures to open
    circuit_reset_timeout: float = 30.0 # Seconds before half-open
    circuit_half_open_max: int = 3      # Test requests in half-open

    # Health check
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0
    unhealthy_threshold: int = 3

    # Retries
    max_retries: int = 3
    retry_delay: float = 0.5

    # Timeouts
    default_timeout: float = 30.0


# ============================================================================
# SERVICE MESH
# ============================================================================

class ServiceMesh:
    """
    Service mesh for microservice communication.

    Features:
    - Service discovery
    - Load balancing
    - Circuit breaker
    - Health checking
    - Retries with backoff

    "Ba'el orchestrates the symphony of services." — Ba'el
    """

    def __init__(self, config: Optional[ServiceMeshConfig] = None):
        """Initialize service mesh."""
        self.config = config or ServiceMeshConfig()

        # Services: service_name -> [endpoints]
        self._services: Dict[str, List[ServiceEndpoint]] = {}

        # Endpoints: endpoint_id -> endpoint
        self._endpoints: Dict[str, ServiceEndpoint] = {}

        # Round robin index per service
        self._rr_index: Dict[str, int] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Background tasks
        self._health_check_task = None
        self._running = False

        # Handlers
        self._service_handlers: Dict[str, Callable] = {}

        # Stats
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'circuit_breaks': 0
        }

        logger.info("Service Mesh initialized")

    # ========================================================================
    # SERVICE REGISTRATION
    # ========================================================================

    def register(
        self,
        service_name: str,
        host: str,
        port: int,
        endpoint_id: Optional[str] = None,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceEndpoint:
        """
        Register a service endpoint.

        Args:
            service_name: Name of the service
            host: Host address
            port: Port number
            endpoint_id: Optional endpoint ID
            weight: Load balancing weight
            metadata: Additional metadata

        Returns:
            ServiceEndpoint
        """
        endpoint_id = endpoint_id or f"{service_name}_{host}_{port}"

        endpoint = ServiceEndpoint(
            id=endpoint_id,
            service_name=service_name,
            host=host,
            port=port,
            weight=weight,
            state=ServiceState.HEALTHY,
            metadata=metadata or {}
        )

        with self._lock:
            # Store endpoint
            self._endpoints[endpoint_id] = endpoint

            # Add to service list
            if service_name not in self._services:
                self._services[service_name] = []
            self._services[service_name].append(endpoint)

            # Initialize RR index
            if service_name not in self._rr_index:
                self._rr_index[service_name] = 0

        logger.info(f"Service registered: {service_name} at {endpoint.address}")

        return endpoint

    def deregister(self, endpoint_id: str) -> bool:
        """Deregister a service endpoint."""
        with self._lock:
            endpoint = self._endpoints.get(endpoint_id)

            if not endpoint:
                return False

            # Remove from endpoints
            del self._endpoints[endpoint_id]

            # Remove from service list
            service_name = endpoint.service_name
            if service_name in self._services:
                self._services[service_name] = [
                    e for e in self._services[service_name]
                    if e.id != endpoint_id
                ]

            logger.info(f"Service deregistered: {endpoint_id}")

            return True

    # ========================================================================
    # SERVICE DISCOVERY
    # ========================================================================

    def discover(
        self,
        service_name: str,
        only_healthy: bool = True
    ) -> List[ServiceEndpoint]:
        """
        Discover service endpoints.

        Args:
            service_name: Service to discover
            only_healthy: Return only healthy endpoints

        Returns:
            List of endpoints
        """
        with self._lock:
            endpoints = self._services.get(service_name, [])

            if only_healthy:
                endpoints = [e for e in endpoints if e.is_available()]

            return endpoints.copy()

    def select_endpoint(
        self,
        service_name: str,
        strategy: Optional[LoadBalanceStrategy] = None,
        key: Optional[str] = None
    ) -> Optional[ServiceEndpoint]:
        """
        Select an endpoint using load balancing.

        Args:
            service_name: Service name
            strategy: Load balancing strategy
            key: Key for consistent hashing

        Returns:
            Selected endpoint or None
        """
        strategy = strategy or self.config.default_strategy
        endpoints = self.discover(service_name, only_healthy=True)

        if not endpoints:
            return None

        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin(service_name, endpoints)
        elif strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(endpoints)
        elif strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return min(endpoints, key=lambda e: e.connections)
        elif strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted_select(endpoints)
        elif strategy == LoadBalanceStrategy.CONSISTENT_HASH:
            return self._consistent_hash(endpoints, key or "")
        elif strategy == LoadBalanceStrategy.LEAST_LATENCY:
            return min(endpoints, key=lambda e: e.avg_latency_ms)

        return endpoints[0]

    def _round_robin(
        self,
        service_name: str,
        endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Round robin selection."""
        with self._lock:
            index = self._rr_index.get(service_name, 0)
            endpoint = endpoints[index % len(endpoints)]
            self._rr_index[service_name] = (index + 1) % len(endpoints)
        return endpoint

    def _weighted_select(
        self,
        endpoints: List[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """Weighted random selection."""
        total_weight = sum(e.weight for e in endpoints)
        r = random.uniform(0, total_weight)

        cumulative = 0.0
        for endpoint in endpoints:
            cumulative += endpoint.weight
            if r <= cumulative:
                return endpoint

        return endpoints[-1]

    def _consistent_hash(
        self,
        endpoints: List[ServiceEndpoint],
        key: str
    ) -> ServiceEndpoint:
        """Consistent hashing selection."""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        index = hash_value % len(endpoints)
        return endpoints[index]

    # ========================================================================
    # SERVICE CALLS
    # ========================================================================

    async def call(
        self,
        service_name: str,
        method: str,
        *args,
        timeout: Optional[float] = None,
        retry: bool = True,
        strategy: Optional[LoadBalanceStrategy] = None,
        **kwargs
    ) -> Any:
        """
        Call a service method.

        Args:
            service_name: Service to call
            method: Method name
            *args: Method arguments
            timeout: Call timeout
            retry: Enable retries
            strategy: Load balancing strategy
            **kwargs: Method keyword arguments

        Returns:
            Method result
        """
        timeout = timeout or self.config.default_timeout
        max_retries = self.config.max_retries if retry else 1

        last_error = None

        for attempt in range(max_retries):
            endpoint = self.select_endpoint(service_name, strategy)

            if not endpoint:
                raise Exception(f"No available endpoints for: {service_name}")

            try:
                # Check circuit breaker
                if not self._check_circuit(endpoint):
                    continue

                # Update metrics
                endpoint.connections += 1
                start_time = time.time()

                # Call service
                handler = self._service_handlers.get(service_name)
                if handler:
                    result = await asyncio.wait_for(
                        handler(endpoint, method, *args, **kwargs),
                        timeout=timeout
                    )
                else:
                    raise NotImplementedError(f"No handler for: {service_name}")

                # Update metrics on success
                latency = (time.time() - start_time) * 1000
                self._update_metrics(endpoint, latency, success=True)
                self._stats['successful_requests'] += 1

                return result

            except asyncio.TimeoutError as e:
                last_error = e
                self._update_metrics(endpoint, 0, success=False)
                self._handle_failure(endpoint)

            except Exception as e:
                last_error = e
                self._update_metrics(endpoint, 0, success=False)
                self._handle_failure(endpoint)

            finally:
                endpoint.connections = max(0, endpoint.connections - 1)
                self._stats['total_requests'] += 1

            # Retry delay
            if attempt < max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        self._stats['failed_requests'] += 1
        raise Exception(f"Service call failed after {max_retries} attempts: {last_error}")

    def register_handler(
        self,
        service_name: str,
        handler: Callable
    ) -> None:
        """Register a service call handler."""
        self._service_handlers[service_name] = handler

    # ========================================================================
    # CIRCUIT BREAKER
    # ========================================================================

    def _check_circuit(self, endpoint: ServiceEndpoint) -> bool:
        """Check if circuit allows request."""
        if endpoint.circuit_state == CircuitState.CLOSED:
            return True

        if endpoint.circuit_state == CircuitState.OPEN:
            # Check if reset timeout passed
            if endpoint.circuit_opened_at:
                elapsed = (datetime.now() - endpoint.circuit_opened_at).total_seconds()
                if elapsed >= self.config.circuit_reset_timeout:
                    endpoint.circuit_state = CircuitState.HALF_OPEN
                    endpoint.circuit_failures = 0
                    return True
            return False

        if endpoint.circuit_state == CircuitState.HALF_OPEN:
            return True

        return False

    def _handle_failure(self, endpoint: ServiceEndpoint) -> None:
        """Handle endpoint failure."""
        endpoint.circuit_failures += 1

        if endpoint.circuit_state == CircuitState.CLOSED:
            if endpoint.circuit_failures >= self.config.circuit_threshold:
                endpoint.circuit_state = CircuitState.OPEN
                endpoint.circuit_opened_at = datetime.now()
                self._stats['circuit_breaks'] += 1
                logger.warning(f"Circuit opened for: {endpoint.id}")

        elif endpoint.circuit_state == CircuitState.HALF_OPEN:
            endpoint.circuit_state = CircuitState.OPEN
            endpoint.circuit_opened_at = datetime.now()

    def _handle_success(self, endpoint: ServiceEndpoint) -> None:
        """Handle endpoint success."""
        if endpoint.circuit_state == CircuitState.HALF_OPEN:
            endpoint.circuit_state = CircuitState.CLOSED
            logger.info(f"Circuit closed for: {endpoint.id}")

        endpoint.circuit_failures = 0

    def _update_metrics(
        self,
        endpoint: ServiceEndpoint,
        latency_ms: float,
        success: bool
    ) -> None:
        """Update endpoint metrics."""
        endpoint.total_requests += 1

        if success:
            # Update average latency
            if endpoint.avg_latency_ms == 0:
                endpoint.avg_latency_ms = latency_ms
            else:
                endpoint.avg_latency_ms = (
                    endpoint.avg_latency_ms * 0.9 + latency_ms * 0.1
                )
            self._handle_success(endpoint)
        else:
            endpoint.failed_requests += 1

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    async def start_health_checks(self) -> None:
        """Start background health checks."""
        if self._running:
            return

        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_checks(self) -> None:
        """Stop background health checks."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()

    async def _health_check_loop(self) -> None:
        """Health check loop."""
        while self._running:
            try:
                await self._check_all_endpoints()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _check_all_endpoints(self) -> None:
        """Check all endpoints."""
        for endpoint in list(self._endpoints.values()):
            try:
                # Simple check - can be extended
                endpoint.last_health_check = datetime.now()
                endpoint.state = ServiceState.HEALTHY
            except Exception:
                endpoint.state = ServiceState.UNHEALTHY

    # ========================================================================
    # QUERIES
    # ========================================================================

    def list_services(self) -> List[str]:
        """List all registered services."""
        with self._lock:
            return list(self._services.keys())

    def list_endpoints(
        self,
        service_name: Optional[str] = None
    ) -> List[ServiceEndpoint]:
        """List endpoints."""
        with self._lock:
            if service_name:
                return self._services.get(service_name, []).copy()
            return list(self._endpoints.values())

    def get_endpoint(self, endpoint_id: str) -> Optional[ServiceEndpoint]:
        """Get specific endpoint."""
        return self._endpoints.get(endpoint_id)

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get mesh statistics."""
        with self._lock:
            healthy = sum(
                1 for e in self._endpoints.values()
                if e.state == ServiceState.HEALTHY
            )

        return {
            'services': len(self._services),
            'endpoints': len(self._endpoints),
            'healthy_endpoints': healthy,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

service_mesh = ServiceMesh()


def register_service(
    service_name: str,
    host: str,
    port: int,
    **kwargs
) -> ServiceEndpoint:
    """Register a service."""
    return service_mesh.register(service_name, host, port, **kwargs)


def discover_service(service_name: str) -> List[ServiceEndpoint]:
    """Discover a service."""
    return service_mesh.discover(service_name)


async def call_service(service_name: str, method: str, *args, **kwargs) -> Any:
    """Call a service."""
    return await service_mesh.call(service_name, method, *args, **kwargs)
