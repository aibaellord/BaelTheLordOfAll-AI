"""
Grafana dashboard definitions for BAEL system monitoring.

Provides pre-configured dashboards for:
- System Overview
- Agent Monitoring
- Workflow Execution
- API Gateway
- Cluster Health
- Plugin Marketplace
- Database Performance
- Redis Metrics
- Error Tracking
- Business KPIs
"""

import json
from typing import Any, Dict


class GrafanaDashboard:
    """Helper class to generate Grafana dashboard JSON."""

    @staticmethod
    def create_dashboard(
        title: str,
        description: str,
        panels: list,
        tags: list,
        refresh: str = "30s",
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """Create Grafana dashboard JSON."""
        return {
            "dashboard": {
                "title": title,
                "description": description,
                "tags": tags,
                "timezone": timezone,
                "refresh": refresh,
                "panels": panels,
                "version": 1,
                "schemaVersion": 27,
                "templating": {
                    "list": []
                }
            }
        }

    @staticmethod
    def create_graph_panel(
        title: str,
        targets: list,
        gridPos: Dict,
        y_axes: Dict = None
    ) -> Dict[str, Any]:
        """Create graph panel."""
        return {
            "type": "graph",
            "title": title,
            "gridPos": gridPos,
            "id": 1,
            "targets": targets,
            "yaxes": y_axes or [
                {"format": "short", "label": "Value"},
                {"format": "short", "label": ""}
            ],
            "xaxis": {
                "bucketOffset": 0,
                "bucketSize": None
            }
        }

    @staticmethod
    def create_stat_panel(
        title: str,
        targets: list,
        gridPos: Dict,
        color_mode: str = "value"
    ) -> Dict[str, Any]:
        """Create stat panel for displaying single values."""
        return {
            "type": "stat",
            "title": title,
            "gridPos": gridPos,
            "id": 1,
            "targets": targets,
            "options": {
                "colorMode": color_mode,
                "graphMode": "area",
                "orientation": "auto",
                "textMode": "auto"
            }
        }

    @staticmethod
    def create_table_panel(
        title: str,
        targets: list,
        gridPos: Dict
    ) -> Dict[str, Any]:
        """Create table panel."""
        return {
            "type": "table",
            "title": title,
            "gridPos": gridPos,
            "id": 1,
            "targets": targets,
            "options": {
                "showHeader": True,
                "sortBy": []
            }
        }


# System Overview Dashboard
SYSTEM_OVERVIEW = {
    "dashboard": {
        "title": "BAEL System Overview",
        "description": "High-level system health and performance metrics",
        "tags": ["bael", "system", "overview"],
        "timezone": "UTC",
        "refresh": "30s",
        "panels": [
            {
                "type": "stat",
                "title": "Active Agents",
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {
                        "expr": "bael_agents_active_count",
                        "refId": "A"
                    }
                ],
                "options": {"colorMode": "value", "graphMode": "area"}
            },
            {
                "type": "stat",
                "title": "System Uptime (hours)",
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {
                        "expr": "bael_system_uptime_seconds / 3600",
                        "refId": "A"
                    }
                ],
                "options": {"colorMode": "value", "graphMode": "area"}
            },
            {
                "type": "stat",
                "title": "Total Workflows Executed",
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {
                        "expr": "bael_workflows_executions_total",
                        "refId": "A"
                    }
                ],
                "options": {"colorMode": "value", "graphMode": "area"}
            },
            {
                "type": "stat",
                "title": "API Requests/sec",
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {
                        "expr": "rate(bael_http_requests_total[1m])",
                        "refId": "A"
                    }
                ],
                "options": {"colorMode": "value", "graphMode": "area"}
            },
            {
                "type": "graph",
                "title": "System CPU Usage",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {
                        "expr": "bael_system_cpu_percent",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "graph",
                "title": "System Memory Usage",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {
                        "expr": "bael_system_memory_percent",
                        "refId": "A"
                    }
                ]
            },
            {
                "type": "graph",
                "title": "Active Connections",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {
                        "expr": "bael_http_active_requests",
                        "refId": "A",
                        "legendFormat": "HTTP Requests"
                    },
                    {
                        "expr": "bael_websocket_active_connections",
                        "refId": "B",
                        "legendFormat": "WebSocket Connections"
                    },
                    {
                        "expr": "bael_redis_connected_clients",
                        "refId": "C",
                        "legendFormat": "Redis Clients"
                    }
                ]
            },
            {
                "type": "graph",
                "title": "Request Latency (p95)",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, bael_http_request_duration_seconds)",
                        "refId": "A",
                        "legendFormat": "P95 Latency"
                    }
                ]
            }
        ],
        "version": 1,
        "schemaVersion": 27
    }
}


# Agent Monitoring Dashboard
AGENT_MONITORING = {
    "dashboard": {
        "title": "Agent Monitoring",
        "description": "Detailed agent performance and behavior tracking",
        "tags": ["bael", "agents"],
        "timezone": "UTC",
        "refresh": "30s",
        "panels": [
            {
                "type": "stat",
                "title": "Total Agents",
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {"expr": "bael_agents_total_count", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Healthy Agents",
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {"expr": "bael_agents_healthy_count", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Avg Response Time (ms)",
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {"expr": "bael_agents_response_time_avg * 1000", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Error Rate",
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {"expr": "rate(bael_agents_errors_total[1m]) / rate(bael_agents_tasks_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Agent Status Distribution",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {"expr": "bael_agents_status_count", "refId": "A"}
                ]
            },
            {
                "type": "table",
                "title": "Top Agents by Tasks Executed",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {"expr": "topk(10, bael_agents_tasks_total)", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Agent Task Execution Rate",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {"expr": "rate(bael_agents_tasks_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Agent Error Rate Trend",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {"expr": "rate(bael_agents_errors_total[5m])", "refId": "A"}
                ]
            }
        ],
        "version": 1,
        "schemaVersion": 27
    }
}


# Workflow Execution Dashboard
WORKFLOW_EXECUTION = {
    "dashboard": {
        "title": "Workflow Execution",
        "description": "Workflow performance and execution metrics",
        "tags": ["bael", "workflows"],
        "timezone": "UTC",
        "refresh": "30s",
        "panels": [
            {
                "type": "stat",
                "title": "Total Workflows",
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {"expr": "bael_workflows_total_count", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Active Executions",
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {"expr": "bael_workflows_executions_in_progress", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Avg Execution Time (ms)",
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {"expr": "bael_workflows_execution_duration_avg * 1000", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Success Rate",
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {"expr": "rate(bael_workflows_executions_success_total[1m]) / rate(bael_workflows_executions_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Executions Per Minute",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {"expr": "rate(bael_workflows_executions_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "table",
                "title": "Top Workflows by Execution Count",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {"expr": "topk(10, bael_workflows_executions_total)", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Execution Duration Distribution",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {"expr": "histogram_quantile(0.95, bael_workflows_execution_duration_seconds) * 1000", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Failure Rate Trend",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {"expr": "rate(bael_workflows_executions_failure_total[5m])", "refId": "A"}
                ]
            }
        ],
        "version": 1,
        "schemaVersion": 27
    }
}


# API Gateway Dashboard
API_GATEWAY = {
    "dashboard": {
        "title": "API Gateway",
        "description": "API performance and routing metrics",
        "tags": ["bael", "api-gateway"],
        "timezone": "UTC",
        "refresh": "30s",
        "panels": [
            {
                "type": "stat",
                "title": "Total Requests",
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {"expr": "bael_http_requests_total", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Current QPS",
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {"expr": "rate(bael_http_requests_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Avg Latency (ms)",
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {"expr": "bael_http_request_duration_avg * 1000", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Error Rate",
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {"expr": "rate(bael_http_errors_total[1m]) / rate(bael_http_requests_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Request Rate by Method",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {"expr": "rate(bael_http_requests_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Response Status Distribution",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {"expr": "bael_http_response_status_count", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Latency Percentiles",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {
                        "expr": "histogram_quantile(0.50, bael_http_request_duration_seconds) * 1000",
                        "refId": "A",
                        "legendFormat": "P50"
                    },
                    {
                        "expr": "histogram_quantile(0.95, bael_http_request_duration_seconds) * 1000",
                        "refId": "B",
                        "legendFormat": "P95"
                    },
                    {
                        "expr": "histogram_quantile(0.99, bael_http_request_duration_seconds) * 1000",
                        "refId": "C",
                        "legendFormat": "P99"
                    }
                ]
            },
            {
                "type": "graph",
                "title": "Circuit Breaker Status",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {"expr": "bael_gateway_circuit_breaker_state", "refId": "A"}
                ]
            }
        ],
        "version": 1,
        "schemaVersion": 27
    }
}


# Cluster Health Dashboard
CLUSTER_HEALTH = {
    "dashboard": {
        "title": "Cluster Health",
        "description": "Cluster node health and coordination metrics",
        "tags": ["bael", "cluster"],
        "timezone": "UTC",
        "refresh": "30s",
        "panels": [
            {
                "type": "stat",
                "title": "Active Nodes",
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {"expr": "bael_cluster_nodes_active", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Leader Elections",
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {"expr": "bael_cluster_elections_total", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Active Locks",
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {"expr": "bael_cluster_locks_active", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Heartbeat Latency (ms)",
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {"expr": "bael_cluster_heartbeat_latency_avg * 1000", "refId": "A"}
                ]
            },
            {
                "type": "table",
                "title": "Cluster Nodes Status",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {"expr": "bael_cluster_node_status", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Node Connectivity",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {"expr": "bael_cluster_node_connections_active", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Consensus Messages/sec",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {"expr": "rate(bael_cluster_consensus_messages_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Lock Contention",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {"expr": "bael_cluster_lock_wait_time_avg", "refId": "A"}
                ]
            }
        ],
        "version": 1,
        "schemaVersion": 27
    }
}


# Database Performance Dashboard
DATABASE_PERFORMANCE = {
    "dashboard": {
        "title": "Database Performance",
        "description": "Database query performance and connection metrics",
        "tags": ["bael", "database"],
        "timezone": "UTC",
        "refresh": "30s",
        "panels": [
            {
                "type": "stat",
                "title": "Total Queries",
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {"expr": "bael_database_queries_total", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Active Connections",
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {"expr": "bael_database_connections_active", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Avg Query Time (ms)",
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {"expr": "bael_database_query_duration_avg * 1000", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Error Rate",
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {"expr": "rate(bael_database_errors_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Query Rate by Type",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {"expr": "rate(bael_database_queries_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Query Latency Distribution",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {"expr": "histogram_quantile(0.95, bael_database_query_duration_seconds) * 1000", "refId": "A"}
                ]
            },
            {
                "type": "table",
                "title": "Slowest Queries",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {"expr": "topk(10, bael_database_query_duration_seconds)", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Connection Pool Usage",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {"expr": "bael_database_connections_active / bael_database_connections_max", "refId": "A"}
                ]
            }
        ],
        "version": 1,
        "schemaVersion": 27
    }
}


# Redis Metrics Dashboard
REDIS_METRICS = {
    "dashboard": {
        "title": "Redis Metrics",
        "description": "Redis cache performance and memory usage",
        "tags": ["bael", "redis"],
        "timezone": "UTC",
        "refresh": "30s",
        "panels": [
            {
                "type": "stat",
                "title": "Cache Hits",
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {"expr": "bael_cache_hits_total", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Cache Misses",
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {"expr": "bael_cache_misses_total", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Hit Ratio",
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {"expr": "bael_cache_hits_total / (bael_cache_hits_total + bael_cache_misses_total)", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Memory Usage (MB)",
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {"expr": "bael_redis_memory_bytes / 1024 / 1024", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Commands/sec",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {"expr": "rate(bael_redis_commands_total[1m])", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Hit/Miss Rate",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {
                        "expr": "rate(bael_cache_hits_total[1m])",
                        "refId": "A",
                        "legendFormat": "Hits/sec"
                    },
                    {
                        "expr": "rate(bael_cache_misses_total[1m])",
                        "refId": "B",
                        "legendFormat": "Misses/sec"
                    }
                ]
            },
            {
                "type": "graph",
                "title": "Memory Usage Trend",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {"expr": "bael_redis_memory_bytes / 1024 / 1024", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Evictions/sec",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {"expr": "rate(bael_cache_evictions_total[1m])", "refId": "A"}
                ]
            }
        ],
        "version": 1,
        "schemaVersion": 27
    }
}


# Business KPIs Dashboard
BUSINESS_KPIS = {
    "dashboard": {
        "title": "Business KPIs",
        "description": "High-level business metrics and KPIs",
        "tags": ["bael", "business"],
        "timezone": "UTC",
        "refresh": "60s",
        "panels": [
            {
                "type": "stat",
                "title": "Active Users",
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {"expr": "bael_active_users_count", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Monthly Revenue (USD)",
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {"expr": "bael_revenue_monthly_usd", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "Avg Response Time (ms)",
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {"expr": "bael_http_request_duration_avg * 1000", "refId": "A"}
                ]
            },
            {
                "type": "stat",
                "title": "System Availability",
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {"expr": "bael_uptime_percent", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Active Users Trend",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [
                    {"expr": "bael_active_users_count", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Requests per Tenant",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [
                    {"expr": "bael_requests_per_tenant_total", "refId": "A"}
                ]
            },
            {
                "type": "table",
                "title": "Top Tenants by Usage",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                "targets": [
                    {"expr": "topk(10, bael_requests_per_tenant_total)", "refId": "A"}
                ]
            },
            {
                "type": "graph",
                "title": "Revenue vs Usage Correlation",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                "targets": [
                    {
                        "expr": "bael_revenue_monthly_usd",
                        "refId": "A",
                        "legendFormat": "Revenue"
                    },
                    {
                        "expr": "rate(bael_http_requests_total[1m]) * 2592000",
                        "refId": "B",
                        "legendFormat": "Monthly Requests"
                    }
                ]
            }
        ],
        "version": 1,
        "schemaVersion": 27
    }
}


def get_all_dashboards():
    """Get all dashboard definitions."""
    return {
        "system_overview": SYSTEM_OVERVIEW,
        "agent_monitoring": AGENT_MONITORING,
        "workflow_execution": WORKFLOW_EXECUTION,
        "api_gateway": API_GATEWAY,
        "cluster_health": CLUSTER_HEALTH,
        "database_performance": DATABASE_PERFORMANCE,
        "redis_metrics": REDIS_METRICS,
        "business_kpis": BUSINESS_KPIS
    }


if __name__ == "__main__":
    import json

    dashboards = get_all_dashboards()
    print(f"Available dashboards: {len(dashboards)}")
    for name in dashboards:
        print(f"  - {name}: {dashboards[name]['dashboard']['title']}")

    # Export as JSON
    print("\nExporting dashboards...")
    for name, dashboard in dashboards.items():
        filename = f"dashboard_{name}.json"
        with open(filename, "w") as f:
            json.dump(dashboard, f, indent=2)
        print(f"  - Exported {filename}")
