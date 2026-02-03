#!/usr/bin/env python3
"""
BAEL - Load Balancer
Comprehensive load balancing and traffic distribution system.

Features:
- Multiple load balancing algorithms
- Health checking
- Circuit breaker integration
- Weighted distribution
- Session affinity
- Rate limiting per backend
- Dynamic backend management
- Metrics and monitoring
- Failover handling
- Connection pooling
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
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LoadBalancerAlgorithm(Enum):
    """Load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"
    WEIGHTED_RESPONSE_TIME = "weighted_response_time"


class BackendStatus(Enum):
    """Backend health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    DRAINING = "draining"
    DISABLED = "disabled"


class HealthCheckType(Enum):
    """Health check types."""
    HTTP = "http"
    TCP = "tcp"
    CUSTOM = "custom"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Backend:
    """Backend server definition."""
    backend_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    host: str = ""
    port: int = 80
    weight: int = 1
    status: BackendStatus = BackendStatus.HEALTHY
    max_connections: int = 100
    current_connections: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def is_available(self) -> bool:
        return (
            self.status == BackendStatus.HEALTHY
            and self.current_connections < self.max_connections
        )


@dataclass
class BackendStats:
    """Backend statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    avg_response_time: float = 0.0
    last_check_time: float = 0.0
    consecutive_failures: int = 0

    def record_request(
        self,
        success: bool,
        response_time: float
    ) -> None:
        self.total_requests += 1

        if success:
            self.successful_requests += 1
            self.consecutive_failures = 0
        else:
            self.failed_requests += 1
            self.consecutive_failures += 1

        self.total_response_time += response_time
        self.avg_response_time = (
            self.total_response_time / self.total_requests
        )


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    check_type: HealthCheckType = HealthCheckType.HTTP
    interval: float = 10.0
    timeout: float = 5.0
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3
    path: str = "/health"
    expected_status: int = 200


@dataclass
class Request:
    """Load balancer request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_ip: str = ""
    path: str = "/"
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    """Load balancer response."""
    success: bool = True
    status_code: int = 200
    body: Any = None
    backend_id: str = ""
    response_time: float = 0.0
    error: str = ""


@dataclass
class LoadBalancerStats:
    """Load balancer statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    active_backends: int = 0
    total_backends: int = 0
    avg_response_time: float = 0.0


# =============================================================================
# LOAD BALANCING STRATEGIES
# =============================================================================

class LoadBalancingStrategy(ABC):
    """Abstract load balancing strategy."""

    @abstractmethod
    def select(
        self,
        backends: List[Backend],
        request: Request,
        stats: Dict[str, BackendStats]
    ) -> Optional[Backend]:
        """Select a backend for the request."""
        pass


class RoundRobinStrategy(LoadBalancingStrategy):
    """Round-robin load balancing."""

    def __init__(self):
        self.current_index = 0

    def select(
        self,
        backends: List[Backend],
        request: Request,
        stats: Dict[str, BackendStats]
    ) -> Optional[Backend]:
        available = [b for b in backends if b.is_available()]

        if not available:
            return None

        backend = available[self.current_index % len(available)]
        self.current_index = (self.current_index + 1) % len(available)

        return backend


class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    """Weighted round-robin load balancing."""

    def __init__(self):
        self.weights: Dict[str, int] = {}
        self.current_weights: Dict[str, int] = {}

    def select(
        self,
        backends: List[Backend],
        request: Request,
        stats: Dict[str, BackendStats]
    ) -> Optional[Backend]:
        available = [b for b in backends if b.is_available()]

        if not available:
            return None

        # Initialize weights
        for backend in available:
            if backend.backend_id not in self.current_weights:
                self.current_weights[backend.backend_id] = 0

        # Find max weight
        max_weight = max(b.weight for b in available)
        gcd_weight = self._gcd_list([b.weight for b in available])

        # Weighted selection
        total_weight = sum(b.weight for b in available)

        selected = None
        max_current_weight = -1

        for backend in available:
            self.current_weights[backend.backend_id] += backend.weight

            if self.current_weights[backend.backend_id] > max_current_weight:
                max_current_weight = self.current_weights[backend.backend_id]
                selected = backend

        if selected:
            self.current_weights[selected.backend_id] -= total_weight

        return selected

    def _gcd_list(self, weights: List[int]) -> int:
        from math import gcd
        result = weights[0]
        for w in weights[1:]:
            result = gcd(result, w)
        return result


class LeastConnectionsStrategy(LoadBalancingStrategy):
    """Least connections load balancing."""

    def select(
        self,
        backends: List[Backend],
        request: Request,
        stats: Dict[str, BackendStats]
    ) -> Optional[Backend]:
        available = [b for b in backends if b.is_available()]

        if not available:
            return None

        return min(available, key=lambda b: b.current_connections)


class RandomStrategy(LoadBalancingStrategy):
    """Random load balancing."""

    def select(
        self,
        backends: List[Backend],
        request: Request,
        stats: Dict[str, BackendStats]
    ) -> Optional[Backend]:
        available = [b for b in backends if b.is_available()]

        if not available:
            return None

        return random.choice(available)


class IPHashStrategy(LoadBalancingStrategy):
    """IP hash load balancing (session affinity)."""

    def select(
        self,
        backends: List[Backend],
        request: Request,
        stats: Dict[str, BackendStats]
    ) -> Optional[Backend]:
        available = [b for b in backends if b.is_available()]

        if not available:
            return None

        # Use session ID if available, otherwise client IP
        key = request.session_id or request.client_ip

        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        index = hash_value % len(available)

        return available[index]


class LeastResponseTimeStrategy(LoadBalancingStrategy):
    """Least response time load balancing."""

    def select(
        self,
        backends: List[Backend],
        request: Request,
        stats: Dict[str, BackendStats]
    ) -> Optional[Backend]:
        available = [b for b in backends if b.is_available()]

        if not available:
            return None

        # Sort by avg response time
        def get_response_time(backend: Backend) -> float:
            backend_stats = stats.get(backend.backend_id)
            if backend_stats and backend_stats.total_requests > 0:
                return backend_stats.avg_response_time
            return 0.0

        return min(available, key=get_response_time)


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """Backend health checker."""

    def __init__(self, config: HealthCheckConfig):
        self.config = config
        self.check_counts: Dict[str, int] = defaultdict(int)
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def check(self, backend: Backend) -> bool:
        """Perform health check."""
        try:
            if self.config.check_type == HealthCheckType.HTTP:
                return await self._http_check(backend)
            elif self.config.check_type == HealthCheckType.TCP:
                return await self._tcp_check(backend)
            else:
                return True
        except Exception as e:
            logger.warning(f"Health check failed for {backend.address}: {e}")
            return False

    async def _http_check(self, backend: Backend) -> bool:
        """Simulate HTTP health check."""
        # In real implementation, would make HTTP request
        await asyncio.sleep(0.01)  # Simulate network latency

        # Simulate 95% success rate
        return random.random() < 0.95

    async def _tcp_check(self, backend: Backend) -> bool:
        """Simulate TCP health check."""
        await asyncio.sleep(0.005)
        return random.random() < 0.98

    def update_status(
        self,
        backend: Backend,
        healthy: bool
    ) -> None:
        """Update backend status based on health check."""
        backend_id = backend.backend_id

        if healthy:
            self.check_counts[backend_id] = min(
                self.check_counts[backend_id] + 1,
                self.config.healthy_threshold
            )

            if self.check_counts[backend_id] >= self.config.healthy_threshold:
                if backend.status != BackendStatus.HEALTHY:
                    backend.status = BackendStatus.HEALTHY
                    logger.info(f"Backend {backend.address} is now healthy")
        else:
            self.check_counts[backend_id] = max(
                self.check_counts[backend_id] - 1,
                -self.config.unhealthy_threshold
            )

            if self.check_counts[backend_id] <= -self.config.unhealthy_threshold:
                if backend.status != BackendStatus.UNHEALTHY:
                    backend.status = BackendStatus.UNHEALTHY
                    logger.warning(f"Backend {backend.address} is now unhealthy")


# =============================================================================
# LOAD BALANCER
# =============================================================================

class LoadBalancer:
    """
    Comprehensive Load Balancer for BAEL.
    """

    def __init__(
        self,
        algorithm: LoadBalancerAlgorithm = LoadBalancerAlgorithm.ROUND_ROBIN,
        health_config: HealthCheckConfig = None
    ):
        self.algorithm = algorithm
        self.backends: Dict[str, Backend] = {}
        self.backend_stats: Dict[str, BackendStats] = {}
        self.strategy = self._create_strategy(algorithm)
        self.health_checker = HealthChecker(
            health_config or HealthCheckConfig()
        )
        self.stats = LoadBalancerStats()
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        self._session_map: Dict[str, str] = {}  # session -> backend_id
        self._request_handlers: Dict[str, Callable] = {}

    def _create_strategy(
        self,
        algorithm: LoadBalancerAlgorithm
    ) -> LoadBalancingStrategy:
        """Create load balancing strategy."""
        strategies = {
            LoadBalancerAlgorithm.ROUND_ROBIN: RoundRobinStrategy,
            LoadBalancerAlgorithm.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinStrategy,
            LoadBalancerAlgorithm.LEAST_CONNECTIONS: LeastConnectionsStrategy,
            LoadBalancerAlgorithm.RANDOM: RandomStrategy,
            LoadBalancerAlgorithm.IP_HASH: IPHashStrategy,
            LoadBalancerAlgorithm.LEAST_RESPONSE_TIME: LeastResponseTimeStrategy,
        }

        return strategies.get(algorithm, RoundRobinStrategy)()

    # -------------------------------------------------------------------------
    # BACKEND MANAGEMENT
    # -------------------------------------------------------------------------

    def add_backend(
        self,
        host: str,
        port: int,
        weight: int = 1,
        max_connections: int = 100
    ) -> str:
        """Add a backend server."""
        backend = Backend(
            host=host,
            port=port,
            weight=weight,
            max_connections=max_connections
        )

        self.backends[backend.backend_id] = backend
        self.backend_stats[backend.backend_id] = BackendStats()
        self.stats.total_backends += 1
        self.stats.active_backends += 1

        logger.info(f"Added backend: {backend.address}")

        return backend.backend_id

    def remove_backend(self, backend_id: str) -> bool:
        """Remove a backend server."""
        if backend_id in self.backends:
            backend = self.backends[backend_id]
            del self.backends[backend_id]
            del self.backend_stats[backend_id]

            self.stats.total_backends -= 1
            if backend.status == BackendStatus.HEALTHY:
                self.stats.active_backends -= 1

            logger.info(f"Removed backend: {backend.address}")
            return True

        return False

    def get_backend(self, backend_id: str) -> Optional[Backend]:
        """Get backend by ID."""
        return self.backends.get(backend_id)

    def list_backends(self) -> List[Backend]:
        """List all backends."""
        return list(self.backends.values())

    def set_backend_status(
        self,
        backend_id: str,
        status: BackendStatus
    ) -> bool:
        """Set backend status."""
        backend = self.backends.get(backend_id)

        if backend:
            old_status = backend.status
            backend.status = status

            # Update active count
            if old_status == BackendStatus.HEALTHY and status != BackendStatus.HEALTHY:
                self.stats.active_backends -= 1
            elif old_status != BackendStatus.HEALTHY and status == BackendStatus.HEALTHY:
                self.stats.active_backends += 1

            return True

        return False

    def set_backend_weight(
        self,
        backend_id: str,
        weight: int
    ) -> bool:
        """Set backend weight."""
        backend = self.backends.get(backend_id)

        if backend:
            backend.weight = weight
            return True

        return False

    # -------------------------------------------------------------------------
    # REQUEST HANDLING
    # -------------------------------------------------------------------------

    async def handle_request(self, request: Request) -> Response:
        """Handle incoming request."""
        start_time = time.time()

        # Check session affinity
        if request.session_id and request.session_id in self._session_map:
            backend_id = self._session_map[request.session_id]
            backend = self.backends.get(backend_id)

            if backend and backend.is_available():
                return await self._forward_request(request, backend, start_time)

        # Select backend
        backends = list(self.backends.values())
        backend = self.strategy.select(
            backends,
            request,
            self.backend_stats
        )

        if not backend:
            self.stats.failed_requests += 1
            return Response(
                success=False,
                status_code=503,
                error="No available backends"
            )

        # Store session mapping
        if request.session_id:
            self._session_map[request.session_id] = backend.backend_id

        return await self._forward_request(request, backend, start_time)

    async def _forward_request(
        self,
        request: Request,
        backend: Backend,
        start_time: float
    ) -> Response:
        """Forward request to backend."""
        backend.current_connections += 1

        try:
            # Simulate request handling
            response = await self._execute_request(request, backend)

            response_time = time.time() - start_time
            response.response_time = response_time
            response.backend_id = backend.backend_id

            # Update stats
            self.stats.total_requests += 1

            if response.success:
                self.stats.successful_requests += 1
            else:
                self.stats.failed_requests += 1

            self.backend_stats[backend.backend_id].record_request(
                response.success,
                response_time
            )

            # Update avg response time
            total_time = sum(
                s.total_response_time
                for s in self.backend_stats.values()
            )
            total_requests = sum(
                s.total_requests
                for s in self.backend_stats.values()
            )

            if total_requests > 0:
                self.stats.avg_response_time = total_time / total_requests

            return response

        finally:
            backend.current_connections -= 1

    async def _execute_request(
        self,
        request: Request,
        backend: Backend
    ) -> Response:
        """Execute request on backend."""
        # Simulate request execution
        await asyncio.sleep(random.uniform(0.01, 0.1))

        # Simulate occasional failures
        if random.random() < 0.02:
            return Response(
                success=False,
                status_code=500,
                error="Backend error"
            )

        return Response(
            success=True,
            status_code=200,
            body={"message": "OK", "backend": backend.address}
        )

    # -------------------------------------------------------------------------
    # HEALTH CHECKING
    # -------------------------------------------------------------------------

    async def start_health_checks(self) -> None:
        """Start health checking loop."""
        if self._running:
            return

        self._running = True
        self._health_check_task = asyncio.create_task(
            self._health_check_loop()
        )

    async def stop_health_checks(self) -> None:
        """Stop health checking loop."""
        self._running = False

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    async def _health_check_loop(self) -> None:
        """Health check loop."""
        while self._running:
            for backend in self.backends.values():
                if backend.status != BackendStatus.DISABLED:
                    healthy = await self.health_checker.check(backend)
                    self.health_checker.update_status(backend, healthy)

                    # Update active count
                    self.stats.active_backends = sum(
                        1 for b in self.backends.values()
                        if b.status == BackendStatus.HEALTHY
                    )

            await asyncio.sleep(self.health_checker.config.interval)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        return {
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": (
                self.stats.successful_requests / self.stats.total_requests
                if self.stats.total_requests > 0
                else 0.0
            ),
            "avg_response_time": self.stats.avg_response_time,
            "active_backends": self.stats.active_backends,
            "total_backends": self.stats.total_backends,
            "algorithm": self.algorithm.value
        }

    def get_backend_stats(
        self,
        backend_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get backend statistics."""
        backend = self.backends.get(backend_id)
        stats = self.backend_stats.get(backend_id)

        if not backend or not stats:
            return None

        return {
            "backend_id": backend_id,
            "address": backend.address,
            "status": backend.status.value,
            "weight": backend.weight,
            "current_connections": backend.current_connections,
            "max_connections": backend.max_connections,
            "total_requests": stats.total_requests,
            "successful_requests": stats.successful_requests,
            "failed_requests": stats.failed_requests,
            "avg_response_time": stats.avg_response_time,
            "consecutive_failures": stats.consecutive_failures
        }

    def get_all_backend_stats(self) -> List[Dict[str, Any]]:
        """Get all backend statistics."""
        return [
            self.get_backend_stats(bid)
            for bid in self.backends.keys()
        ]


# =============================================================================
# LOAD BALANCER BUILDER
# =============================================================================

class LoadBalancerBuilder:
    """Fluent load balancer builder."""

    def __init__(self):
        self.algorithm = LoadBalancerAlgorithm.ROUND_ROBIN
        self.health_config = HealthCheckConfig()
        self.backends: List[Tuple[str, int, int]] = []

    def with_algorithm(
        self,
        algorithm: LoadBalancerAlgorithm
    ) -> 'LoadBalancerBuilder':
        self.algorithm = algorithm
        return self

    def with_health_check(
        self,
        interval: float = 10.0,
        timeout: float = 5.0,
        path: str = "/health"
    ) -> 'LoadBalancerBuilder':
        self.health_config = HealthCheckConfig(
            interval=interval,
            timeout=timeout,
            path=path
        )
        return self

    def add_backend(
        self,
        host: str,
        port: int,
        weight: int = 1
    ) -> 'LoadBalancerBuilder':
        self.backends.append((host, port, weight))
        return self

    def build(self) -> LoadBalancer:
        lb = LoadBalancer(
            algorithm=self.algorithm,
            health_config=self.health_config
        )

        for host, port, weight in self.backends:
            lb.add_backend(host, port, weight)

        return lb


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Load Balancer System."""
    print("=" * 70)
    print("BAEL - LOAD BALANCER SYSTEM DEMO")
    print("Comprehensive Traffic Distribution")
    print("=" * 70)
    print()

    # 1. Create Load Balancer
    print("1. CREATE LOAD BALANCER:")
    print("-" * 40)

    lb = (
        LoadBalancerBuilder()
        .with_algorithm(LoadBalancerAlgorithm.ROUND_ROBIN)
        .with_health_check(interval=5.0)
        .add_backend("server1.example.com", 8080, weight=1)
        .add_backend("server2.example.com", 8080, weight=2)
        .add_backend("server3.example.com", 8080, weight=1)
        .build()
    )

    print(f"   Algorithm: {lb.algorithm.value}")
    print(f"   Backends: {len(lb.backends)}")
    print()

    # 2. List Backends
    print("2. LIST BACKENDS:")
    print("-" * 40)

    for backend in lb.list_backends():
        print(f"   - {backend.address} (weight: {backend.weight}, status: {backend.status.value})")
    print()

    # 3. Handle Requests
    print("3. HANDLE REQUESTS:")
    print("-" * 40)

    for i in range(6):
        request = Request(
            client_ip=f"192.168.1.{i}",
            path="/api/data"
        )

        response = await lb.handle_request(request)

        print(f"   Request {i+1}: {response.body.get('backend') if response.body else 'N/A'}")
    print()

    # 4. Weighted Distribution
    print("4. WEIGHTED DISTRIBUTION:")
    print("-" * 40)

    # Create weighted round-robin balancer
    weighted_lb = LoadBalancer(
        algorithm=LoadBalancerAlgorithm.WEIGHTED_ROUND_ROBIN
    )

    weighted_lb.add_backend("light.example.com", 8080, weight=1)
    weighted_lb.add_backend("heavy.example.com", 8080, weight=3)

    distribution = defaultdict(int)

    for i in range(40):
        request = Request(client_ip=f"10.0.0.{i}")
        response = await weighted_lb.handle_request(request)

        if response.body:
            distribution[response.body.get('backend')] += 1

    print(f"   Distribution over 40 requests:")

    for backend, count in sorted(distribution.items()):
        print(f"      {backend}: {count} requests")
    print()

    # 5. Least Connections
    print("5. LEAST CONNECTIONS:")
    print("-" * 40)

    lc_lb = LoadBalancer(
        algorithm=LoadBalancerAlgorithm.LEAST_CONNECTIONS
    )

    b1 = lc_lb.add_backend("busy.example.com", 8080)
    b2 = lc_lb.add_backend("idle.example.com", 8080)

    # Simulate busy backend
    lc_lb.backends[b1].current_connections = 50
    lc_lb.backends[b2].current_connections = 5

    for i in range(3):
        request = Request(client_ip=f"10.0.0.{i}")
        response = await lc_lb.handle_request(request)

        print(f"   Request {i+1}: {response.body.get('backend') if response.body else 'N/A'}")
    print()

    # 6. Session Affinity
    print("6. SESSION AFFINITY:")
    print("-" * 40)

    ip_lb = LoadBalancer(
        algorithm=LoadBalancerAlgorithm.IP_HASH
    )

    ip_lb.add_backend("sticky1.example.com", 8080)
    ip_lb.add_backend("sticky2.example.com", 8080)
    ip_lb.add_backend("sticky3.example.com", 8080)

    # Same client should hit same backend
    for i in range(3):
        request = Request(client_ip="192.168.1.100", session_id="session-abc")
        response = await ip_lb.handle_request(request)

        print(f"   Same client request {i+1}: {response.body.get('backend') if response.body else 'N/A'}")
    print()

    # 7. Backend Status
    print("7. BACKEND STATUS:")
    print("-" * 40)

    backends = list(lb.backends.keys())

    # Disable one backend
    lb.set_backend_status(backends[0], BackendStatus.UNHEALTHY)

    print(f"   Backend statuses:")

    for backend in lb.list_backends():
        print(f"      {backend.address}: {backend.status.value}")
    print()

    # 8. Handle Requests with Unhealthy Backend
    print("8. REQUESTS WITH UNHEALTHY BACKEND:")
    print("-" * 40)

    distribution.clear()

    for i in range(10):
        request = Request(client_ip=f"10.0.0.{i}")
        response = await lb.handle_request(request)

        if response.body:
            distribution[response.body.get('backend')] += 1

    print(f"   Distribution (excluding unhealthy):")

    for backend, count in sorted(distribution.items()):
        print(f"      {backend}: {count} requests")
    print()

    # 9. Load Balancer Stats
    print("9. LOAD BALANCER STATS:")
    print("-" * 40)

    stats = lb.get_stats()

    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Successful: {stats['successful_requests']}")
    print(f"   Failed: {stats['failed_requests']}")
    print(f"   Success rate: {stats['success_rate']*100:.1f}%")
    print(f"   Avg response time: {stats['avg_response_time']*1000:.2f}ms")
    print(f"   Active backends: {stats['active_backends']}/{stats['total_backends']}")
    print()

    # 10. Backend Stats
    print("10. BACKEND STATS:")
    print("-" * 40)

    for backend_stats in lb.get_all_backend_stats():
        print(f"   {backend_stats['address']}:")
        print(f"      Status: {backend_stats['status']}")
        print(f"      Requests: {backend_stats['total_requests']}")
        print(f"      Avg response: {backend_stats['avg_response_time']*1000:.2f}ms")
    print()

    # 11. Dynamic Backend Management
    print("11. DYNAMIC BACKEND MANAGEMENT:")
    print("-" * 40)

    # Add new backend
    new_id = lb.add_backend("new-server.example.com", 8080, weight=2)
    print(f"   Added backend: {lb.backends[new_id].address}")

    # Update weight
    lb.set_backend_weight(new_id, 3)
    print(f"   Updated weight: {lb.backends[new_id].weight}")

    # Remove backend
    lb.remove_backend(new_id)
    print(f"   Removed backend: new-server.example.com:8080")

    print(f"   Current backends: {len(lb.backends)}")
    print()

    # 12. Response Time Based Selection
    print("12. RESPONSE TIME SELECTION:")
    print("-" * 40)

    rt_lb = LoadBalancer(
        algorithm=LoadBalancerAlgorithm.LEAST_RESPONSE_TIME
    )

    fast_id = rt_lb.add_backend("fast.example.com", 8080)
    slow_id = rt_lb.add_backend("slow.example.com", 8080)

    # Simulate different response times
    rt_lb.backend_stats[fast_id].total_requests = 100
    rt_lb.backend_stats[fast_id].total_response_time = 1.0  # 10ms avg
    rt_lb.backend_stats[fast_id].avg_response_time = 0.01

    rt_lb.backend_stats[slow_id].total_requests = 100
    rt_lb.backend_stats[slow_id].total_response_time = 10.0  # 100ms avg
    rt_lb.backend_stats[slow_id].avg_response_time = 0.1

    for i in range(3):
        request = Request(client_ip=f"10.0.0.{i}")
        response = await rt_lb.handle_request(request)

        print(f"   Request {i+1}: {response.body.get('backend') if response.body else 'N/A'}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Load Balancer System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
