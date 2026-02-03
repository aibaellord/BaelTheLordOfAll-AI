#!/usr/bin/env python3
"""
BAEL - Service Mesh Manager
Comprehensive service mesh and inter-service communication.

Features:
- Service discovery
- Load balancing
- Circuit breaking
- Retry policies
- Timeout management
- Traffic shaping
- Mutual TLS
- Service routing
- Observability
- Health checks
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


# =============================================================================
# ENUMS
# =============================================================================

class ServiceState(Enum):
    """Service states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    OFFLINE = "offline"


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    WEIGHTED = "weighted"
    CONSISTENT_HASH = "consistent_hash"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryPolicy(Enum):
    """Retry policies."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class TrafficPolicy(Enum):
    """Traffic policies."""
    ALLOW = "allow"
    DENY = "deny"
    RATE_LIMIT = "rate_limit"
    REDIRECT = "redirect"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ServiceEndpoint:
    """Service endpoint."""
    endpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    host: str = ""
    port: int = 80
    protocol: str = "http"
    weight: int = 100
    state: ServiceState = ServiceState.HEALTHY
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class ServiceDefinition:
    """Service definition."""
    service_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    namespace: str = "default"
    version: str = "1.0.0"
    endpoints: List[ServiceEndpoint] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def healthy_endpoints(self) -> List[ServiceEndpoint]:
        return [e for e in self.endpoints if e.state == ServiceState.HEALTHY]


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: float = 30.0
    half_open_max_calls: int = 3


@dataclass
class CircuitBreakerState:
    """Circuit breaker state."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure: float = 0.0
    last_state_change: float = field(default_factory=time.time)


@dataclass
class RetryConfig:
    """Retry configuration."""
    policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    retryable_codes: List[int] = field(default_factory=lambda: [502, 503, 504])


@dataclass
class TimeoutConfig:
    """Timeout configuration."""
    connect_timeout: float = 5.0
    request_timeout: float = 30.0
    idle_timeout: float = 60.0


@dataclass
class TrafficRule:
    """Traffic routing rule."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    source_service: str = "*"
    destination_service: str = ""
    match_headers: Dict[str, str] = field(default_factory=dict)
    match_path: str = "*"
    policy: TrafficPolicy = TrafficPolicy.ALLOW
    weight: int = 100
    redirect_to: str = ""
    rate_limit: int = 0  # requests per second


@dataclass
class ServiceCall:
    """Service call record."""
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    destination: str = ""
    endpoint: str = ""
    method: str = "GET"
    path: str = ""
    status_code: int = 0
    duration_ms: float = 0.0
    error: str = ""
    timestamp: float = field(default_factory=time.time)
    retries: int = 0


@dataclass
class MeshMetrics:
    """Mesh metrics."""
    service: str = ""
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.request_count == 0:
            return 1.0
        return self.success_count / self.request_count

    @property
    def avg_latency_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

class ServiceRegistry:
    """Service registry for discovery."""

    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._by_name: Dict[str, List[str]] = defaultdict(list)

    def register(self, service: ServiceDefinition) -> str:
        """Register a service."""
        self._services[service.service_id] = service
        self._by_name[service.name].append(service.service_id)

        return service.service_id

    def deregister(self, service_id: str) -> bool:
        """Deregister a service."""
        service = self._services.get(service_id)

        if not service:
            return False

        del self._services[service_id]
        self._by_name[service.name].remove(service_id)

        return True

    def get(self, service_id: str) -> Optional[ServiceDefinition]:
        """Get service by ID."""
        return self._services.get(service_id)

    def find_by_name(self, name: str) -> List[ServiceDefinition]:
        """Find services by name."""
        service_ids = self._by_name.get(name, [])
        return [self._services[sid] for sid in service_ids if sid in self._services]

    def find_by_labels(self, labels: Dict[str, str]) -> List[ServiceDefinition]:
        """Find services by labels."""
        result = []

        for service in self._services.values():
            if all(service.labels.get(k) == v for k, v in labels.items()):
                result.append(service)

        return result

    def list_all(self) -> List[ServiceDefinition]:
        """List all services."""
        return list(self._services.values())

    def update_endpoint_state(
        self,
        service_id: str,
        endpoint_id: str,
        state: ServiceState
    ) -> bool:
        """Update endpoint state."""
        service = self._services.get(service_id)

        if not service:
            return False

        for endpoint in service.endpoints:
            if endpoint.endpoint_id == endpoint_id:
                endpoint.state = state
                return True

        return False


# =============================================================================
# LOAD BALANCER
# =============================================================================

class MeshLoadBalancer:
    """Load balancer for service mesh."""

    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self._counters: Dict[str, int] = defaultdict(int)
        self._connections: Dict[str, int] = defaultdict(int)

    def select(
        self,
        endpoints: List[ServiceEndpoint],
        key: str = None
    ) -> Optional[ServiceEndpoint]:
        """Select an endpoint."""
        healthy = [e for e in endpoints if e.state == ServiceState.HEALTHY]

        if not healthy:
            return None

        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin(healthy)

        if self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy)

        if self.strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(healthy)

        if self.strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted(healthy)

        if self.strategy == LoadBalanceStrategy.CONSISTENT_HASH:
            return self._consistent_hash(healthy, key or "")

        return healthy[0]

    def _round_robin(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Round robin selection."""
        key = ",".join(e.endpoint_id for e in endpoints)
        index = self._counters[key] % len(endpoints)
        self._counters[key] += 1
        return endpoints[index]

    def _least_connections(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Least connections selection."""
        return min(
            endpoints,
            key=lambda e: self._connections.get(e.endpoint_id, 0)
        )

    def _weighted(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Weighted random selection."""
        total_weight = sum(e.weight for e in endpoints)
        r = random.randint(0, total_weight - 1)

        for endpoint in endpoints:
            r -= endpoint.weight

            if r < 0:
                return endpoint

        return endpoints[-1]

    def _consistent_hash(
        self,
        endpoints: List[ServiceEndpoint],
        key: str
    ) -> ServiceEndpoint:
        """Consistent hash selection."""
        hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
        index = hash_val % len(endpoints)
        return endpoints[index]

    def record_connection(self, endpoint_id: str, active: bool) -> None:
        """Record connection state."""
        if active:
            self._connections[endpoint_id] += 1
        else:
            self._connections[endpoint_id] = max(0, self._connections[endpoint_id] - 1)


# =============================================================================
# CIRCUIT BREAKER MANAGER
# =============================================================================

class CircuitBreakerManager:
    """Manages circuit breakers."""

    def __init__(self, default_config: CircuitBreakerConfig = None):
        self.default_config = default_config or CircuitBreakerConfig()
        self._states: Dict[str, CircuitBreakerState] = {}
        self._configs: Dict[str, CircuitBreakerConfig] = {}

    def get_state(self, service: str) -> CircuitBreakerState:
        """Get circuit state for service."""
        if service not in self._states:
            self._states[service] = CircuitBreakerState()

        return self._states[service]

    def set_config(self, service: str, config: CircuitBreakerConfig) -> None:
        """Set circuit config for service."""
        self._configs[service] = config

    def can_call(self, service: str) -> bool:
        """Check if call is allowed."""
        state = self.get_state(service)
        config = self._configs.get(service, self.default_config)

        if state.state == CircuitState.CLOSED:
            return True

        if state.state == CircuitState.OPEN:
            # Check timeout
            if time.time() - state.last_state_change >= config.timeout:
                state.state = CircuitState.HALF_OPEN
                state.last_state_change = time.time()
                state.success_count = 0
                return True

            return False

        if state.state == CircuitState.HALF_OPEN:
            return state.success_count < config.half_open_max_calls

        return True

    def record_success(self, service: str) -> None:
        """Record successful call."""
        state = self.get_state(service)
        config = self._configs.get(service, self.default_config)

        if state.state == CircuitState.HALF_OPEN:
            state.success_count += 1

            if state.success_count >= config.success_threshold:
                state.state = CircuitState.CLOSED
                state.failure_count = 0
                state.last_state_change = time.time()

        elif state.state == CircuitState.CLOSED:
            state.failure_count = 0

    def record_failure(self, service: str) -> None:
        """Record failed call."""
        state = self.get_state(service)
        config = self._configs.get(service, self.default_config)

        state.failure_count += 1
        state.last_failure = time.time()

        if state.state == CircuitState.HALF_OPEN:
            state.state = CircuitState.OPEN
            state.last_state_change = time.time()

        elif state.state == CircuitState.CLOSED:
            if state.failure_count >= config.failure_threshold:
                state.state = CircuitState.OPEN
                state.last_state_change = time.time()


# =============================================================================
# RETRY MANAGER
# =============================================================================

class RetryManager:
    """Manages retry policies."""

    def __init__(self):
        self._configs: Dict[str, RetryConfig] = {}
        self._default_config = RetryConfig()

    def set_config(self, service: str, config: RetryConfig) -> None:
        """Set retry config for service."""
        self._configs[service] = config

    def get_config(self, service: str) -> RetryConfig:
        """Get retry config for service."""
        return self._configs.get(service, self._default_config)

    def should_retry(
        self,
        service: str,
        attempt: int,
        status_code: int
    ) -> Tuple[bool, float]:
        """Check if should retry and get delay."""
        config = self.get_config(service)

        if config.policy == RetryPolicy.NONE:
            return False, 0.0

        if attempt >= config.max_retries:
            return False, 0.0

        if status_code not in config.retryable_codes:
            return False, 0.0

        delay = self._calculate_delay(config, attempt)

        return True, delay

    def _calculate_delay(self, config: RetryConfig, attempt: int) -> float:
        """Calculate retry delay."""
        if config.policy == RetryPolicy.FIXED:
            return config.base_delay

        if config.policy == RetryPolicy.LINEAR:
            delay = config.base_delay * (attempt + 1)
            return min(delay, config.max_delay)

        if config.policy == RetryPolicy.EXPONENTIAL:
            delay = config.base_delay * (2 ** attempt)
            return min(delay, config.max_delay)

        return config.base_delay


# =============================================================================
# TRAFFIC MANAGER
# =============================================================================

class TrafficManager:
    """Manages traffic rules and routing."""

    def __init__(self):
        self._rules: Dict[str, TrafficRule] = {}
        self._rate_limiters: Dict[str, Tuple[int, float]] = {}  # (count, window_start)

    def add_rule(self, rule: TrafficRule) -> str:
        """Add traffic rule."""
        self._rules[rule.rule_id] = rule
        return rule.rule_id

    def remove_rule(self, rule_id: str) -> bool:
        """Remove traffic rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def evaluate(
        self,
        source: str,
        destination: str,
        headers: Dict[str, str] = None,
        path: str = "/"
    ) -> Tuple[TrafficPolicy, Optional[str]]:
        """Evaluate traffic rules."""
        headers = headers or {}

        matching_rules = []

        for rule in self._rules.values():
            if self._matches_rule(rule, source, destination, headers, path):
                matching_rules.append(rule)

        if not matching_rules:
            return TrafficPolicy.ALLOW, None

        # Sort by weight (higher first)
        matching_rules.sort(key=lambda r: r.weight, reverse=True)

        rule = matching_rules[0]

        # Handle rate limiting
        if rule.policy == TrafficPolicy.RATE_LIMIT:
            if not self._check_rate_limit(rule.rule_id, rule.rate_limit):
                return TrafficPolicy.DENY, None

            return TrafficPolicy.ALLOW, None

        # Handle redirect
        if rule.policy == TrafficPolicy.REDIRECT:
            return TrafficPolicy.REDIRECT, rule.redirect_to

        return rule.policy, None

    def _matches_rule(
        self,
        rule: TrafficRule,
        source: str,
        destination: str,
        headers: Dict[str, str],
        path: str
    ) -> bool:
        """Check if rule matches."""
        # Check source
        if rule.source_service != "*" and rule.source_service != source:
            return False

        # Check destination
        if rule.destination_service != destination:
            return False

        # Check path
        if rule.match_path != "*":
            import fnmatch
            if not fnmatch.fnmatch(path, rule.match_path):
                return False

        # Check headers
        for key, value in rule.match_headers.items():
            if headers.get(key) != value:
                return False

        return True

    def _check_rate_limit(self, rule_id: str, limit: int) -> bool:
        """Check rate limit."""
        now = time.time()
        window = 1.0  # 1 second window

        if rule_id not in self._rate_limiters:
            self._rate_limiters[rule_id] = (1, now)
            return True

        count, window_start = self._rate_limiters[rule_id]

        if now - window_start >= window:
            self._rate_limiters[rule_id] = (1, now)
            return True

        if count >= limit:
            return False

        self._rate_limiters[rule_id] = (count + 1, window_start)
        return True


# =============================================================================
# MESH OBSERVER
# =============================================================================

class MeshObserver:
    """Observability for service mesh."""

    def __init__(self, max_calls: int = 10000):
        self._calls: List[ServiceCall] = []
        self._max_calls = max_calls
        self._metrics: Dict[str, MeshMetrics] = {}

    def record_call(self, call: ServiceCall) -> None:
        """Record a service call."""
        self._calls.append(call)

        if len(self._calls) > self._max_calls:
            self._calls = self._calls[-self._max_calls:]

        # Update metrics
        self._update_metrics(call)

    def _update_metrics(self, call: ServiceCall) -> None:
        """Update metrics from call."""
        service = call.destination

        if service not in self._metrics:
            self._metrics[service] = MeshMetrics(service=service)

        metrics = self._metrics[service]
        metrics.request_count += 1
        metrics.total_latency_ms += call.duration_ms

        if call.status_code < 400:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1

    def get_metrics(self, service: str) -> Optional[MeshMetrics]:
        """Get metrics for service."""
        return self._metrics.get(service)

    def get_all_metrics(self) -> Dict[str, MeshMetrics]:
        """Get all metrics."""
        return self._metrics.copy()

    def get_recent_calls(
        self,
        source: str = None,
        destination: str = None,
        limit: int = 100
    ) -> List[ServiceCall]:
        """Get recent calls."""
        calls = self._calls

        if source:
            calls = [c for c in calls if c.source == source]

        if destination:
            calls = [c for c in calls if c.destination == destination]

        return calls[-limit:]

    def get_error_rate(self, service: str) -> float:
        """Get error rate for service."""
        metrics = self._metrics.get(service)

        if not metrics or metrics.request_count == 0:
            return 0.0

        return metrics.failure_count / metrics.request_count


# =============================================================================
# SERVICE MESH
# =============================================================================

class ServiceMesh:
    """
    Comprehensive Service Mesh Manager for BAEL.
    """

    def __init__(
        self,
        lb_strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN
    ):
        self.registry = ServiceRegistry()
        self.load_balancer = MeshLoadBalancer(lb_strategy)
        self.circuit_breaker = CircuitBreakerManager()
        self.retry_manager = RetryManager()
        self.traffic_manager = TrafficManager()
        self.observer = MeshObserver()

        self._handlers: Dict[str, Callable] = {}
        self._timeouts: Dict[str, TimeoutConfig] = {}
        self._default_timeout = TimeoutConfig()

    # -------------------------------------------------------------------------
    # SERVICE MANAGEMENT
    # -------------------------------------------------------------------------

    def register_service(
        self,
        name: str,
        endpoints: List[Tuple[str, int]],
        namespace: str = "default",
        version: str = "1.0.0",
        labels: Dict[str, str] = None
    ) -> ServiceDefinition:
        """Register a service."""
        service_endpoints = [
            ServiceEndpoint(host=host, port=port)
            for host, port in endpoints
        ]

        service = ServiceDefinition(
            name=name,
            namespace=namespace,
            version=version,
            endpoints=service_endpoints,
            labels=labels or {}
        )

        self.registry.register(service)

        return service

    def deregister_service(self, service_id: str) -> bool:
        """Deregister a service."""
        return self.registry.deregister(service_id)

    def discover(self, name: str) -> List[ServiceDefinition]:
        """Discover services by name."""
        return self.registry.find_by_name(name)

    def get_endpoint(
        self,
        service_name: str,
        key: str = None
    ) -> Optional[ServiceEndpoint]:
        """Get an endpoint for service."""
        services = self.discover(service_name)

        if not services:
            return None

        all_endpoints = []

        for service in services:
            all_endpoints.extend(service.healthy_endpoints)

        if not all_endpoints:
            return None

        return self.load_balancer.select(all_endpoints, key)

    # -------------------------------------------------------------------------
    # SERVICE CALLS
    # -------------------------------------------------------------------------

    async def call(
        self,
        source: str,
        destination: str,
        method: str = "GET",
        path: str = "/",
        headers: Dict[str, str] = None,
        body: Any = None,
        key: str = None
    ) -> ServiceCall:
        """Make a service call."""
        headers = headers or {}

        # Check traffic rules
        policy, redirect = self.traffic_manager.evaluate(
            source, destination, headers, path
        )

        if policy == TrafficPolicy.DENY:
            return ServiceCall(
                source=source,
                destination=destination,
                method=method,
                path=path,
                status_code=403,
                error="Denied by traffic policy"
            )

        if policy == TrafficPolicy.REDIRECT:
            destination = redirect

        # Check circuit breaker
        if not self.circuit_breaker.can_call(destination):
            return ServiceCall(
                source=source,
                destination=destination,
                method=method,
                path=path,
                status_code=503,
                error="Circuit breaker open"
            )

        # Get endpoint
        endpoint = self.get_endpoint(destination, key)

        if not endpoint:
            return ServiceCall(
                source=source,
                destination=destination,
                method=method,
                path=path,
                status_code=503,
                error="No healthy endpoints"
            )

        # Make call with retry
        call = await self._execute_call(
            source, destination, endpoint, method, path, headers, body
        )

        # Record metrics
        self.observer.record_call(call)

        # Update circuit breaker
        if call.status_code >= 500:
            self.circuit_breaker.record_failure(destination)
        else:
            self.circuit_breaker.record_success(destination)

        return call

    async def _execute_call(
        self,
        source: str,
        destination: str,
        endpoint: ServiceEndpoint,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Any
    ) -> ServiceCall:
        """Execute the actual call with retry."""
        retry_config = self.retry_manager.get_config(destination)
        timeout_config = self._timeouts.get(destination, self._default_timeout)

        attempt = 0
        last_call = None

        while True:
            self.load_balancer.record_connection(endpoint.endpoint_id, True)

            start_time = time.time()

            try:
                # Simulate call (in real impl, use aiohttp/httpx)
                await asyncio.sleep(0.01)  # Simulated latency

                # Simulated response
                status_code = 200 if random.random() > 0.1 else 503
                duration_ms = (time.time() - start_time) * 1000

                call = ServiceCall(
                    source=source,
                    destination=destination,
                    endpoint=endpoint.address,
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    retries=attempt
                )

                last_call = call

                # Check if should retry
                should_retry, delay = self.retry_manager.should_retry(
                    destination, attempt, status_code
                )

                if should_retry:
                    attempt += 1
                    await asyncio.sleep(delay)
                    continue

                return call

            except asyncio.TimeoutError:
                duration_ms = (time.time() - start_time) * 1000

                call = ServiceCall(
                    source=source,
                    destination=destination,
                    endpoint=endpoint.address,
                    method=method,
                    path=path,
                    status_code=504,
                    duration_ms=duration_ms,
                    error="Timeout",
                    retries=attempt
                )

                return call

            finally:
                self.load_balancer.record_connection(endpoint.endpoint_id, False)

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def configure_circuit_breaker(
        self,
        service: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 30.0
    ) -> None:
        """Configure circuit breaker for service."""
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout
        )

        self.circuit_breaker.set_config(service, config)

    def configure_retry(
        self,
        service: str,
        policy: RetryPolicy = RetryPolicy.EXPONENTIAL,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> None:
        """Configure retry for service."""
        config = RetryConfig(
            policy=policy,
            max_retries=max_retries,
            base_delay=base_delay
        )

        self.retry_manager.set_config(service, config)

    def configure_timeout(
        self,
        service: str,
        connect_timeout: float = 5.0,
        request_timeout: float = 30.0
    ) -> None:
        """Configure timeout for service."""
        self._timeouts[service] = TimeoutConfig(
            connect_timeout=connect_timeout,
            request_timeout=request_timeout
        )

    # -------------------------------------------------------------------------
    # TRAFFIC RULES
    # -------------------------------------------------------------------------

    def add_traffic_rule(
        self,
        name: str,
        destination: str,
        policy: TrafficPolicy = TrafficPolicy.ALLOW,
        source: str = "*",
        match_headers: Dict[str, str] = None,
        match_path: str = "*",
        rate_limit: int = 0,
        redirect_to: str = ""
    ) -> str:
        """Add traffic rule."""
        rule = TrafficRule(
            name=name,
            source_service=source,
            destination_service=destination,
            match_headers=match_headers or {},
            match_path=match_path,
            policy=policy,
            rate_limit=rate_limit,
            redirect_to=redirect_to
        )

        return self.traffic_manager.add_rule(rule)

    def remove_traffic_rule(self, rule_id: str) -> bool:
        """Remove traffic rule."""
        return self.traffic_manager.remove_rule(rule_id)

    # -------------------------------------------------------------------------
    # HEALTH
    # -------------------------------------------------------------------------

    def update_endpoint_health(
        self,
        service_name: str,
        endpoint_host: str,
        state: ServiceState
    ) -> bool:
        """Update endpoint health."""
        services = self.discover(service_name)

        for service in services:
            for endpoint in service.endpoints:
                if endpoint.host == endpoint_host:
                    endpoint.state = state
                    return True

        return False

    def drain_endpoint(self, service_name: str, endpoint_host: str) -> bool:
        """Mark endpoint as draining."""
        return self.update_endpoint_health(
            service_name, endpoint_host, ServiceState.DRAINING
        )

    # -------------------------------------------------------------------------
    # OBSERVABILITY
    # -------------------------------------------------------------------------

    def get_service_metrics(self, service: str) -> Optional[Dict[str, Any]]:
        """Get metrics for service."""
        metrics = self.observer.get_metrics(service)

        if not metrics:
            return None

        return {
            "service": service,
            "request_count": metrics.request_count,
            "success_count": metrics.success_count,
            "failure_count": metrics.failure_count,
            "success_rate": metrics.success_rate,
            "avg_latency_ms": metrics.avg_latency_ms
        }

    def get_mesh_status(self) -> Dict[str, Any]:
        """Get overall mesh status."""
        services = self.registry.list_all()

        total_endpoints = 0
        healthy_endpoints = 0

        for service in services:
            total_endpoints += len(service.endpoints)
            healthy_endpoints += len(service.healthy_endpoints)

        all_metrics = self.observer.get_all_metrics()

        return {
            "services": len(services),
            "total_endpoints": total_endpoints,
            "healthy_endpoints": healthy_endpoints,
            "health_rate": healthy_endpoints / total_endpoints if total_endpoints > 0 else 1.0,
            "metrics": {
                name: {
                    "requests": m.request_count,
                    "success_rate": m.success_rate,
                    "avg_latency_ms": m.avg_latency_ms
                }
                for name, m in all_metrics.items()
            }
        }

    def get_circuit_status(self, service: str) -> Dict[str, Any]:
        """Get circuit breaker status."""
        state = self.circuit_breaker.get_state(service)

        return {
            "service": service,
            "state": state.state.value,
            "failure_count": state.failure_count,
            "success_count": state.success_count,
            "last_failure": state.last_failure,
            "last_state_change": state.last_state_change
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Service Mesh System."""
    print("=" * 70)
    print("BAEL - SERVICE MESH MANAGER DEMO")
    print("Comprehensive Service Mesh System")
    print("=" * 70)
    print()

    mesh = ServiceMesh(LoadBalanceStrategy.ROUND_ROBIN)

    # 1. Register Services
    print("1. REGISTER SERVICES:")
    print("-" * 40)

    api_gateway = mesh.register_service(
        "api-gateway",
        [("gateway1.local", 8080), ("gateway2.local", 8080)],
        labels={"tier": "edge", "team": "platform"}
    )
    print(f"   Registered: {api_gateway.name} ({len(api_gateway.endpoints)} endpoints)")

    user_service = mesh.register_service(
        "user-service",
        [("user1.local", 8081), ("user2.local", 8081), ("user3.local", 8081)],
        labels={"tier": "backend", "team": "users"}
    )
    print(f"   Registered: {user_service.name} ({len(user_service.endpoints)} endpoints)")

    order_service = mesh.register_service(
        "order-service",
        [("order1.local", 8082), ("order2.local", 8082)],
        labels={"tier": "backend", "team": "commerce"}
    )
    print(f"   Registered: {order_service.name} ({len(order_service.endpoints)} endpoints)")
    print()

    # 2. Service Discovery
    print("2. SERVICE DISCOVERY:")
    print("-" * 40)

    services = mesh.discover("user-service")
    print(f"   Found {len(services)} service(s) named 'user-service'")

    for svc in services:
        print(f"      - {svc.name} v{svc.version}")

        for ep in svc.endpoints:
            print(f"         {ep.host}:{ep.port} ({ep.state.value})")
    print()

    # 3. Load Balancing
    print("3. LOAD BALANCING:")
    print("-" * 40)

    for i in range(5):
        endpoint = mesh.get_endpoint("user-service")
        print(f"   Request {i+1}: {endpoint.host}:{endpoint.port}")
    print()

    # 4. Configure Circuit Breaker
    print("4. CONFIGURE CIRCUIT BREAKER:")
    print("-" * 40)

    mesh.configure_circuit_breaker(
        "order-service",
        failure_threshold=3,
        success_threshold=2,
        timeout=15.0
    )
    print("   Configured for order-service:")
    print("      Failure threshold: 3")
    print("      Success threshold: 2")
    print("      Timeout: 15s")
    print()

    # 5. Configure Retry
    print("5. CONFIGURE RETRY:")
    print("-" * 40)

    mesh.configure_retry(
        "user-service",
        policy=RetryPolicy.EXPONENTIAL,
        max_retries=3,
        base_delay=0.5
    )
    print("   Configured for user-service:")
    print("      Policy: exponential")
    print("      Max retries: 3")
    print("      Base delay: 0.5s")
    print()

    # 6. Add Traffic Rules
    print("6. ADD TRAFFIC RULES:")
    print("-" * 40)

    rule1 = mesh.add_traffic_rule(
        "rate-limit-users",
        destination="user-service",
        policy=TrafficPolicy.RATE_LIMIT,
        rate_limit=100
    )
    print("   Added: rate-limit-users (100 req/s)")

    rule2 = mesh.add_traffic_rule(
        "block-external",
        destination="order-service",
        source="external-api",
        policy=TrafficPolicy.DENY
    )
    print("   Added: block-external (deny)")
    print()

    # 7. Make Service Calls
    print("7. MAKE SERVICE CALLS:")
    print("-" * 40)

    for i in range(5):
        call = await mesh.call(
            source="api-gateway",
            destination="user-service",
            method="GET",
            path="/users"
        )

        status = "✓" if call.status_code < 400 else "✗"
        print(f"   [{status}] Call {i+1}: {call.status_code} ({call.duration_ms:.1f}ms)")
    print()

    # 8. Simulate Failures
    print("8. SIMULATE FAILURES:")
    print("-" * 40)

    # Record some failures
    for i in range(4):
        mesh.circuit_breaker.record_failure("order-service")

    status = mesh.get_circuit_status("order-service")
    print(f"   Circuit state: {status['state']}")
    print(f"   Failure count: {status['failure_count']}")

    # Try to call (should be blocked)
    call = await mesh.call(
        source="api-gateway",
        destination="order-service",
        method="GET",
        path="/orders"
    )
    print(f"   Call result: {call.status_code} - {call.error}")
    print()

    # 9. Drain Endpoint
    print("9. DRAIN ENDPOINT:")
    print("-" * 40)

    mesh.drain_endpoint("user-service", "user1.local")
    print("   Draining: user1.local")

    services = mesh.discover("user-service")

    for svc in services:
        healthy = len(svc.healthy_endpoints)
        total = len(svc.endpoints)
        print(f"   {svc.name}: {healthy}/{total} healthy")
    print()

    # 10. Service Metrics
    print("10. SERVICE METRICS:")
    print("-" * 40)

    metrics = mesh.get_service_metrics("user-service")

    if metrics:
        print(f"   Service: {metrics['service']}")
        print(f"   Requests: {metrics['request_count']}")
        print(f"   Success rate: {metrics['success_rate']*100:.1f}%")
        print(f"   Avg latency: {metrics['avg_latency_ms']:.1f}ms")
    print()

    # 11. Recent Calls
    print("11. RECENT CALLS:")
    print("-" * 40)

    calls = mesh.observer.get_recent_calls(limit=5)

    for call in calls:
        print(f"   {call.source} -> {call.destination}: {call.status_code}")
    print()

    # 12. Mesh Status
    print("12. MESH STATUS:")
    print("-" * 40)

    status = mesh.get_mesh_status()

    print(f"   Services: {status['services']}")
    print(f"   Total endpoints: {status['total_endpoints']}")
    print(f"   Healthy endpoints: {status['healthy_endpoints']}")
    print(f"   Health rate: {status['health_rate']*100:.1f}%")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Service Mesh System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
