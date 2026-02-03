"""
BAEL - Production Monitoring
Prometheus metrics, OpenTelemetry tracing, and comprehensive health checks.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Monitoring")


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

try:
    from prometheus_client import (CONTENT_TYPE_LATEST, CollectorRegistry,
                                   Counter, Gauge, Histogram, Summary,
                                   generate_latest)
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Metrics disabled.")


class MetricsCollector:
    """
    Collects Prometheus metrics for BAEL system.

    Metrics:
    - Request counters
    - Response times
    - Active operations
    - Error rates
    - Resource usage
    """

    def __init__(self, registry: Optional['CollectorRegistry'] = None):
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus metrics not available")
            return

        self.registry = registry or CollectorRegistry()

        # Request metrics
        self.requests_total = Counter(
            'bael_requests_total',
            'Total number of requests',
            ['endpoint', 'method', 'status'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'bael_request_duration_seconds',
            'Request duration in seconds',
            ['endpoint', 'method'],
            registry=self.registry
        )

        # Task metrics
        self.tasks_total = Counter(
            'bael_tasks_total',
            'Total number of tasks',
            ['status'],
            registry=self.registry
        )

        self.tasks_active = Gauge(
            'bael_tasks_active',
            'Number of active tasks',
            registry=self.registry
        )

        self.task_duration = Histogram(
            'bael_task_duration_seconds',
            'Task duration in seconds',
            ['task_type'],
            registry=self.registry
        )

        # Brain metrics
        self.brain_operations = Counter(
            'bael_brain_operations_total',
            'Total brain operations',
            ['operation'],
            registry=self.registry
        )

        self.brain_tokens = Counter(
            'bael_brain_tokens_total',
            'Total tokens processed',
            ['direction'],  # input/output
            registry=self.registry
        )

        # Memory metrics
        self.memory_operations = Counter(
            'bael_memory_operations_total',
            'Memory operations',
            ['operation', 'layer'],
            registry=self.registry
        )

        self.memory_size = Gauge(
            'bael_memory_size_bytes',
            'Memory size in bytes',
            ['layer'],
            registry=self.registry
        )

        # Agent metrics
        self.agents_active = Gauge(
            'bael_agents_active',
            'Number of active agents',
            registry=self.registry
        )

        self.agent_operations = Counter(
            'bael_agent_operations_total',
            'Agent operations',
            ['agent_type', 'operation'],
            registry=self.registry
        )

        # System metrics
        self.system_errors = Counter(
            'bael_errors_total',
            'Total system errors',
            ['component', 'error_type'],
            registry=self.registry
        )

        self.cache_hits = Counter(
            'bael_cache_hits_total',
            'Cache hits',
            ['cache_type'],
            registry=self.registry
        )

        self.cache_misses = Counter(
            'bael_cache_misses_total',
            'Cache misses',
            ['cache_type'],
            registry=self.registry
        )

        logger.info("✅ Prometheus metrics collector initialized")

    def record_request(self, endpoint: str, method: str, status: int, duration: float):
        """Record HTTP request metrics."""
        if not PROMETHEUS_AVAILABLE:
            return

        self.requests_total.labels(
            endpoint=endpoint,
            method=method,
            status=str(status)
        ).inc()

        self.request_duration.labels(
            endpoint=endpoint,
            method=method
        ).observe(duration)

    def record_task(self, status: str, duration: Optional[float] = None, task_type: str = "general"):
        """Record task metrics."""
        if not PROMETHEUS_AVAILABLE:
            return

        self.tasks_total.labels(status=status).inc()

        if duration is not None:
            self.task_duration.labels(task_type=task_type).observe(duration)

    def set_active_tasks(self, count: int):
        """Set number of active tasks."""
        if not PROMETHEUS_AVAILABLE:
            return
        self.tasks_active.set(count)

    def record_brain_operation(self, operation: str, tokens_in: int = 0, tokens_out: int = 0):
        """Record brain operation metrics."""
        if not PROMETHEUS_AVAILABLE:
            return

        self.brain_operations.labels(operation=operation).inc()

        if tokens_in > 0:
            self.brain_tokens.labels(direction="input").inc(tokens_in)
        if tokens_out > 0:
            self.brain_tokens.labels(direction="output").inc(tokens_out)

    def record_memory_operation(self, operation: str, layer: str, size_bytes: Optional[int] = None):
        """Record memory operation metrics."""
        if not PROMETHEUS_AVAILABLE:
            return

        self.memory_operations.labels(operation=operation, layer=layer).inc()

        if size_bytes is not None:
            self.memory_size.labels(layer=layer).set(size_bytes)

    def set_active_agents(self, count: int):
        """Set number of active agents."""
        if not PROMETHEUS_AVAILABLE:
            return
        self.agents_active.set(count)

    def record_agent_operation(self, agent_type: str, operation: str):
        """Record agent operation."""
        if not PROMETHEUS_AVAILABLE:
            return
        self.agent_operations.labels(agent_type=agent_type, operation=operation).inc()

    def record_error(self, component: str, error_type: str):
        """Record system error."""
        if not PROMETHEUS_AVAILABLE:
            return
        self.system_errors.labels(component=component, error_type=error_type).inc()

    def record_cache_hit(self, cache_type: str):
        """Record cache hit."""
        if not PROMETHEUS_AVAILABLE:
            return
        self.cache_hits.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str):
        """Record cache miss."""
        if not PROMETHEUS_AVAILABLE:
            return
        self.cache_misses.labels(cache_type=cache_type).inc()

    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        if not PROMETHEUS_AVAILABLE:
            return b""
        return generate_latest(self.registry)


# Global metrics collector
_metrics = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


# =============================================================================
# OPENTELEMETRY TRACING
# =============================================================================

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (BatchSpanProcessor,
                                                ConsoleSpanExporter)
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not installed. Tracing disabled.")


class TracingManager:
    """Manages OpenTelemetry distributed tracing."""

    def __init__(self, service_name: str = "bael"):
        if not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry tracing not available")
            self.tracer = None
            return

        # Create resource
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "2.1.0"
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Add span processor (console for now, would add OTLP exporter in production)
        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

        # Set global provider
        trace.set_tracer_provider(provider)

        # Get tracer
        self.tracer = trace.get_tracer(__name__)

        logger.info("✅ OpenTelemetry tracing initialized")

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Start a new span."""
        if not self.tracer:
            return DummySpan()

        span = self.tracer.start_span(name)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        return span

    @contextmanager
    def trace(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Context manager for tracing a block of code."""
        if not self.tracer:
            yield
            return

        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span


class DummySpan:
    """Dummy span when tracing is disabled."""
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, key, value):
        pass

    def add_event(self, name, attributes=None):
        pass


# Global tracing manager
_tracing = None


def get_tracing_manager() -> TracingManager:
    """Get global tracing manager."""
    global _tracing
    if _tracing is None:
        _tracing = TracingManager()
    return _tracing


def trace(name: str = None):
    """Decorator to trace a function."""
    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracing = get_tracing_manager()
            with tracing.trace(span_name):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracing = get_tracing_manager()
            with tracing.trace(span_name):
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# =============================================================================
# HEALTH CHECKS
# =============================================================================

class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a component."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    Manages comprehensive health checks.

    Components checked:
    - Brain availability
    - Memory systems
    - Task queue
    - External integrations
    - Database connections
    - Cache systems
    """

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, ComponentHealth] = {}
        self.start_time = datetime.now()

    def register_check(self, name: str, check_func: Callable):
        """Register a health check function."""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")

    async def check_component(self, name: str) -> ComponentHealth:
        """Check health of a specific component."""
        if name not in self.checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Check not registered"
            )

        start = time.time()

        try:
            check_func = self.checks[name]

            # Run check
            import asyncio
            import inspect

            if inspect.iscoroutinefunction(check_func):
                is_healthy = await check_func()
            else:
                is_healthy = check_func()

            latency = (time.time() - start) * 1000

            if is_healthy:
                status = HealthStatus.HEALTHY
                message = "OK"
            else:
                status = HealthStatus.DEGRADED
                message = "Check failed"

            result = ComponentHealth(
                name=name,
                status=status,
                message=message,
                latency_ms=latency
            )

        except Exception as e:
            latency = (time.time() - start) * 1000
            result = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=latency
            )

        self.last_results[name] = result
        return result

    async def check_all(self) -> Dict[str, ComponentHealth]:
        """Check all registered components."""
        results = {}

        for name in self.checks.keys():
            results[name] = await self.check_component(name)

        return results

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        if not self.last_results:
            return HealthStatus.HEALTHY

        statuses = [r.status for r in self.last_results.values()]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def get_uptime_seconds(self) -> float:
        """Get system uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        return {
            "status": self.get_overall_status().value,
            "uptime_seconds": self.get_uptime_seconds(),
            "components": {
                name: {
                    "status": health.status.value,
                    "message": health.message,
                    "latency_ms": health.latency_ms,
                    "metadata": health.metadata
                }
                for name, health in self.last_results.items()
            }
        }


# Global health checker
_health_checker = None


def get_health_checker() -> HealthChecker:
    """Get global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


# =============================================================================
# INTEGRATION DECORATORS
# =============================================================================

def monitored(operation_name: str = None):
    """
    Decorator to add monitoring to a function.

    Adds:
    - Metrics collection
    - Distributed tracing
    - Error tracking
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            tracing = get_tracing_manager()

            start_time = time.time()

            with tracing.trace(f"operation.{op_name}"):
                try:
                    result = await func(*args, **kwargs)

                    # Record success
                    duration = time.time() - start_time
                    metrics.record_brain_operation(op_name)

                    return result

                except Exception as e:
                    # Record error
                    metrics.record_error(
                        component=func.__module__,
                        error_type=type(e).__name__
                    )
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            tracing = get_tracing_manager()

            start_time = time.time()

            with tracing.trace(f"operation.{op_name}"):
                try:
                    result = func(*args, **kwargs)

                    # Record success
                    duration = time.time() - start_time
                    metrics.record_brain_operation(op_name)

                    return result

                except Exception as e:
                    # Record error
                    metrics.record_error(
                        component=func.__module__,
                        error_type=type(e).__name__
                    )
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


__all__ = [
    'MetricsCollector',
    'TracingManager',
    'HealthChecker',
    'HealthStatus',
    'ComponentHealth',
    'get_metrics_collector',
    'get_tracing_manager',
    'get_health_checker',
    'trace',
    'monitored'
]
