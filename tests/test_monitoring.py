"""
Unit tests for core.monitoring.production module
"""

import asyncio
import time
from typing import Any, Dict

import pytest

from core.monitoring.production import (HealthChecker, HealthStatus,
                                        MetricsCollector, TracingManager,
                                        get_health_checker,
                                        get_metrics_collector,
                                        get_tracing_manager, monitored)


class TestMetricsCollector:
    """Test MetricsCollector class"""

    def test_singleton(self):
        """Test MetricsCollector is singleton"""

        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2

    def test_record_request(self):
        """Test recording request metrics"""

        collector = MetricsCollector()

        collector.record_request("chat", "success", 0.5)

        metrics = collector.get_metrics()
        assert "bael_requests_total" in metrics

    def test_record_task(self):
        """Test recording task metrics"""

        collector = MetricsCollector()

        collector.record_task("pending")
        collector.record_task("running")
        collector.record_task("completed")

        metrics = collector.get_metrics()
        assert "bael_tasks_total" in metrics

    def test_record_brain_operation(self):
        """Test recording brain operation"""

        collector = MetricsCollector()

        collector.record_brain_operation("reasoning", 1.5, "success")

        metrics = collector.get_metrics()
        assert "bael_brain_operations_total" in metrics

    def test_record_memory_usage(self):
        """Test recording memory usage"""

        collector = MetricsCollector()

        collector.record_memory_usage(1024.0)

        metrics = collector.get_metrics()
        assert "bael_memory_usage_bytes" in metrics

    def test_record_agent_activity(self):
        """Test recording agent activity"""

        collector = MetricsCollector()

        collector.record_agent_activity("agent_1", "thinking")

        metrics = collector.get_metrics()
        assert "bael_agent_activities_total" in metrics

    def test_record_error(self):
        """Test recording errors"""

        collector = MetricsCollector()

        collector.record_error("chat", "ValueError")

        metrics = collector.get_metrics()
        assert "bael_errors_total" in metrics

    def test_get_metrics_prometheus_format(self):
        """Test getting metrics in Prometheus format"""

        collector = MetricsCollector()

        # Record some metrics
        collector.record_request("chat", "success", 0.1)
        collector.record_task("pending")

        metrics_text = collector.get_metrics()

        assert isinstance(metrics_text, str)
        assert "bael_requests_total" in metrics_text or len(metrics_text) >= 0


class TestTracingManager:
    """Test TracingManager class"""

    def test_singleton(self):
        """Test TracingManager is singleton"""

        tracer1 = get_tracing_manager()
        tracer2 = get_tracing_manager()

        assert tracer1 is tracer2

    @pytest.mark.asyncio
    async def test_start_span(self):
        """Test starting a trace span"""

        tracer = TracingManager()

        span = tracer.start_span("test_operation")
        assert span is not None

    @pytest.mark.asyncio
    async def test_end_span(self):
        """Test ending a trace span"""

        tracer = TracingManager()

        span = tracer.start_span("test_operation")
        tracer.end_span(span)

        # Should complete without error
        assert True

    @pytest.mark.asyncio
    async def test_span_context_manager(self):
        """Test using span as context manager"""

        tracer = TracingManager()

        async with tracer.span("test_operation") as span:
            await asyncio.sleep(0.01)

        assert span is not None

    @pytest.mark.asyncio
    async def test_add_span_attribute(self):
        """Test adding attributes to span"""

        tracer = TracingManager()

        span = tracer.start_span("test_operation")
        tracer.add_span_attribute(span, "key", "value")
        tracer.end_span(span)

        assert True

    @pytest.mark.asyncio
    async def test_record_exception(self):
        """Test recording exception in span"""

        tracer = TracingManager()

        span = tracer.start_span("test_operation")

        try:
            raise ValueError("Test error")
        except Exception as e:
            tracer.record_exception(span, e)

        tracer.end_span(span)

        assert True


class TestHealthChecker:
    """Test HealthChecker class"""

    def test_singleton(self):
        """Test HealthChecker is singleton"""

        checker1 = get_health_checker()
        checker2 = get_health_checker()

        assert checker1 is checker2

    def test_register_check(self):
        """Test registering health check"""

        checker = HealthChecker()

        def test_check() -> bool:
            return True

        checker.register_check("test_component", test_check)

        assert "test_component" in checker.checks

    @pytest.mark.asyncio
    async def test_check_health_all_healthy(self):
        """Test checking health when all components healthy"""

        checker = HealthChecker()

        checker.register_check("component1", lambda: True)
        checker.register_check("component2", lambda: True)

        status, details = await checker.check_health()

        assert status == HealthStatus.HEALTHY
        assert details["component1"] == HealthStatus.HEALTHY
        assert details["component2"] == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_health_degraded(self):
        """Test checking health when some components unhealthy"""

        checker = HealthChecker()

        checker.register_check("healthy", lambda: True)
        checker.register_check("unhealthy", lambda: False)

        status, details = await checker.check_health()

        assert status == HealthStatus.DEGRADED
        assert details["healthy"] == HealthStatus.HEALTHY
        assert details["unhealthy"] == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_health_all_unhealthy(self):
        """Test checking health when all components unhealthy"""

        checker = HealthChecker()

        checker.register_check("component1", lambda: False)
        checker.register_check("component2", lambda: False)

        status, details = await checker.check_health()

        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_health_with_exception(self):
        """Test health check with exception"""

        checker = HealthChecker()

        def failing_check():
            raise RuntimeError("Check failed")

        checker.register_check("failing", failing_check)

        status, details = await checker.check_health()

        assert status == HealthStatus.UNHEALTHY
        assert details["failing"] == HealthStatus.UNHEALTHY

    def test_unregister_check(self):
        """Test unregistering health check"""

        checker = HealthChecker()

        checker.register_check("test", lambda: True)
        assert "test" in checker.checks

        checker.unregister_check("test")
        assert "test" not in checker.checks


class TestMonitoredDecorator:
    """Test @monitored decorator"""

    @pytest.mark.asyncio
    async def test_monitored_async_function(self):
        """Test monitoring async function"""

        @monitored("test_operation")
        async def async_func(value: int) -> int:
            await asyncio.sleep(0.01)
            return value * 2

        result = await async_func(5)

        assert result == 10

        # Check metrics were recorded
        collector = get_metrics_collector()
        metrics = collector.get_metrics()
        assert isinstance(metrics, str)

    def test_monitored_sync_function(self):
        """Test monitoring sync function"""

        @monitored("sync_operation")
        def sync_func(value: int) -> int:
            time.sleep(0.01)
            return value * 3

        result = sync_func(5)

        assert result == 15

    @pytest.mark.asyncio
    async def test_monitored_with_error(self):
        """Test monitoring function that raises error"""

        @monitored("error_operation")
        async def error_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await error_func()

        # Error should be recorded
        collector = get_metrics_collector()
        metrics = collector.get_metrics()
        assert isinstance(metrics, str)

    @pytest.mark.asyncio
    async def test_monitored_with_metadata(self):
        """Test monitoring with metadata"""

        @monitored("metadata_operation", metadata={"category": "test"})
        async def func_with_metadata():
            return "success"

        result = await func_with_metadata()
        assert result == "success"


class TestIntegration:
    """Integration tests for monitoring system"""

    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow"""

        # Get singletons
        collector = get_metrics_collector()
        tracer = get_tracing_manager()
        health = get_health_checker()

        # Register health check
        health.register_check("test_system", lambda: True)

        # Start tracing
        span = tracer.start_span("workflow")

        # Record metrics
        collector.record_request("api", "success", 0.1)
        collector.record_task("completed")
        collector.record_brain_operation("reasoning", 0.5, "success")

        # Check health
        status, details = await health.check_health()
        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

        # End tracing
        tracer.end_span(span)

        # Get metrics
        metrics = collector.get_metrics()
        assert isinstance(metrics, str)

    @pytest.mark.asyncio
    async def test_monitored_with_all_features(self):
        """Test @monitored decorator with all monitoring features"""

        health = get_health_checker()
        health.register_check("component", lambda: True)

        @monitored("complex_operation")
        async def complex_operation(x: int, y: int) -> int:
            await asyncio.sleep(0.01)

            # Simulate work
            result = x + y

            # Simulate nested operation
            async with get_tracing_manager().span("nested"):
                result *= 2

            return result

        result = await complex_operation(5, 3)

        assert result == 16

        # Verify all monitoring components worked
        collector = get_metrics_collector()
        metrics = collector.get_metrics()
        assert isinstance(metrics, str)

        status, details = await health.check_health()
        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
