"""
Prometheus metrics exporter for BAEL.

Provides comprehensive application metrics for monitoring and alerting.
"""

import logging
import time
from typing import Any, Dict

import psutil
from prometheus_client import (CONTENT_TYPE_LATEST, CollectorRegistry, Counter,
                               Gauge, Histogram, Summary, generate_latest)

logger = logging.getLogger(__name__)


class BAELMetrics:
    """Central metrics registry for BAEL application."""

    def __init__(self, registry: CollectorRegistry = None):
        """
        Initialize metrics.

        Args:
            registry: Prometheus registry (creates new if None)
        """
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()

    def _setup_metrics(self):
        """Set up all Prometheus metrics."""

        # =================================================================
        # HTTP/API Metrics
        # =================================================================
        self.http_requests_total = Counter(
            'bael_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )

        self.http_request_duration = Histogram(
            'bael_http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.registry,
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )

        self.http_requests_in_progress = Gauge(
            'bael_http_requests_in_progress',
            'HTTP requests currently in progress',
            registry=self.registry
        )

        # =================================================================
        # Agent Metrics
        # =================================================================
        self.agents_total = Gauge(
            'bael_agents_total',
            'Total number of agents',
            ['status'],
            registry=self.registry
        )

        self.agent_tasks_total = Counter(
            'bael_agent_tasks_total',
            'Total tasks executed by agents',
            ['agent_id', 'status'],
            registry=self.registry
        )

        self.agent_response_time = Histogram(
            'bael_agent_response_time_seconds',
            'Agent response time',
            ['agent_id', 'persona'],
            registry=self.registry,
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
        )

        self.agent_errors_total = Counter(
            'bael_agent_errors_total',
            'Total agent errors',
            ['agent_id', 'error_type'],
            registry=self.registry
        )

        # =================================================================
        # Workflow Metrics
        # =================================================================
        self.workflows_total = Gauge(
            'bael_workflows_total',
            'Total number of workflows',
            registry=self.registry
        )

        self.workflow_executions_total = Counter(
            'bael_workflow_executions_total',
            'Total workflow executions',
            ['workflow_id', 'status'],
            registry=self.registry
        )

        self.workflow_duration = Histogram(
            'bael_workflow_duration_seconds',
            'Workflow execution duration',
            ['workflow_id'],
            registry=self.registry,
            buckets=(1, 5, 10, 30, 60, 300, 600, 1800)
        )

        self.workflow_tasks_per_execution = Histogram(
            'bael_workflow_tasks_per_execution',
            'Number of tasks per workflow execution',
            ['workflow_id'],
            registry=self.registry,
            buckets=(1, 3, 5, 10, 20, 50, 100)
        )

        # =================================================================
        # Plugin Metrics
        # =================================================================
        self.plugins_total = Gauge(
            'bael_plugins_total',
            'Total number of plugins',
            ['category', 'installed'],
            registry=self.registry
        )

        self.plugin_downloads_total = Counter(
            'bael_plugin_downloads_total',
            'Total plugin downloads',
            ['plugin_id'],
            registry=self.registry
        )

        self.plugin_execution_time = Histogram(
            'bael_plugin_execution_time_seconds',
            'Plugin execution time',
            ['plugin_id'],
            registry=self.registry,
            buckets=(0.01, 0.1, 0.5, 1.0, 5.0, 10.0)
        )

        # =================================================================
        # Cache Metrics
        # =================================================================
        self.cache_hits_total = Counter(
            'bael_cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )

        self.cache_misses_total = Counter(
            'bael_cache_misses_total',
            'Total cache misses',
            ['cache_type'],
            registry=self.registry
        )

        self.cache_size = Gauge(
            'bael_cache_size_bytes',
            'Cache size in bytes',
            ['cache_type'],
            registry=self.registry
        )

        self.cache_evictions_total = Counter(
            'bael_cache_evictions_total',
            'Total cache evictions',
            ['cache_type'],
            registry=self.registry
        )

        # =================================================================
        # Gateway Metrics
        # =================================================================
        self.gateway_requests_total = Counter(
            'bael_gateway_requests_total',
            'Total gateway requests',
            ['backend', 'status'],
            registry=self.registry
        )

        self.gateway_backend_latency = Histogram(
            'bael_gateway_backend_latency_seconds',
            'Gateway backend latency',
            ['backend'],
            registry=self.registry,
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
        )

        self.gateway_backend_health = Gauge(
            'bael_gateway_backend_health',
            'Gateway backend health (1=healthy, 0=unhealthy)',
            ['backend'],
            registry=self.registry
        )

        self.gateway_circuit_breaker_state = Gauge(
            'bael_gateway_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half_open)',
            ['backend'],
            registry=self.registry
        )

        # =================================================================
        # Cluster Metrics
        # =================================================================
        self.cluster_nodes_total = Gauge(
            'bael_cluster_nodes_total',
            'Total cluster nodes',
            ['status'],
            registry=self.registry
        )

        self.cluster_leader_elections_total = Counter(
            'bael_cluster_leader_elections_total',
            'Total leader elections',
            registry=self.registry
        )

        self.cluster_lock_acquisitions_total = Counter(
            'bael_cluster_lock_acquisitions_total',
            'Total lock acquisitions',
            ['lock_name', 'status'],
            registry=self.registry
        )

        self.cluster_heartbeat_failures_total = Counter(
            'bael_cluster_heartbeat_failures_total',
            'Total heartbeat failures',
            ['node_id'],
            registry=self.registry
        )

        # =================================================================
        # Database Metrics
        # =================================================================
        self.db_queries_total = Counter(
            'bael_db_queries_total',
            'Total database queries',
            ['operation', 'table'],
            registry=self.registry
        )

        self.db_query_duration = Histogram(
            'bael_db_query_duration_seconds',
            'Database query duration',
            ['operation', 'table'],
            registry=self.registry,
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
        )

        self.db_connections_active = Gauge(
            'bael_db_connections_active',
            'Active database connections',
            registry=self.registry
        )

        self.db_errors_total = Counter(
            'bael_db_errors_total',
            'Total database errors',
            ['error_type'],
            registry=self.registry
        )

        # =================================================================
        # Redis Metrics
        # =================================================================
        self.redis_commands_total = Counter(
            'bael_redis_commands_total',
            'Total Redis commands',
            ['command', 'status'],
            registry=self.registry
        )

        self.redis_command_duration = Histogram(
            'bael_redis_command_duration_seconds',
            'Redis command duration',
            ['command'],
            registry=self.registry,
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1)
        )

        self.redis_connections_active = Gauge(
            'bael_redis_connections_active',
            'Active Redis connections',
            registry=self.registry
        )

        # =================================================================
        # WebSocket Metrics
        # =================================================================
        self.websocket_connections_total = Gauge(
            'bael_websocket_connections_total',
            'Total WebSocket connections',
            ['authenticated'],
            registry=self.registry
        )

        self.websocket_messages_total = Counter(
            'bael_websocket_messages_total',
            'Total WebSocket messages',
            ['direction', 'event_type'],
            registry=self.registry
        )

        self.websocket_rooms_total = Gauge(
            'bael_websocket_rooms_total',
            'Total WebSocket rooms',
            registry=self.registry
        )

        # =================================================================
        # System Metrics
        # =================================================================
        self.system_cpu_usage = Gauge(
            'bael_system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )

        self.system_memory_usage = Gauge(
            'bael_system_memory_usage_bytes',
            'System memory usage in bytes',
            registry=self.registry
        )

        self.system_disk_usage = Gauge(
            'bael_system_disk_usage_bytes',
            'System disk usage in bytes',
            ['mountpoint'],
            registry=self.registry
        )

        self.system_uptime_seconds = Gauge(
            'bael_system_uptime_seconds',
            'System uptime in seconds',
            registry=self.registry
        )

        # =================================================================
        # Business Metrics
        # =================================================================
        self.users_active_total = Gauge(
            'bael_users_active_total',
            'Total active users',
            registry=self.registry
        )

        self.requests_per_tenant = Counter(
            'bael_requests_per_tenant_total',
            'Total requests per tenant',
            ['tenant_id'],
            registry=self.registry
        )

        self.revenue_metrics = Counter(
            'bael_revenue_total',
            'Total revenue',
            ['plan_type'],
            registry=self.registry
        )

    def update_system_metrics(self):
        """Update system metrics (CPU, memory, disk)."""
        try:
            # CPU usage
            self.system_cpu_usage.set(psutil.cpu_percent())

            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.used)

            # Disk usage
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    self.system_disk_usage.labels(
                        mountpoint=partition.mountpoint
                    ).set(usage.used)
                except PermissionError:
                    continue

            # Uptime (approximate from process)
            process = psutil.Process()
            uptime = time.time() - process.create_time()
            self.system_uptime_seconds.set(uptime)

        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")

    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus format.

        Returns:
            bytes: Prometheus metrics
        """
        # Update system metrics before exporting
        self.update_system_metrics()

        return generate_latest(self.registry)


# Global metrics instance
metrics_registry = BAELMetrics()


def get_metrics_handler():
    """
    FastAPI handler for metrics endpoint.

    Returns:
        Response: Prometheus metrics response
    """
    from fastapi import Response

    metrics_data = metrics_registry.get_metrics()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Example usage
if __name__ == "__main__":
    metrics = BAELMetrics()

    # Simulate some metrics
    metrics.http_requests_total.labels(
        method="GET",
        endpoint="/api/agents",
        status="200"
    ).inc()

    metrics.agent_response_time.labels(
        agent_id="agent-1",
        persona="assistant"
    ).observe(0.5)

    # Get metrics
    print(metrics.get_metrics().decode('utf-8'))
