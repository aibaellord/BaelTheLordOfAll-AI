"""
BAEL Observability Stack
=========================

Comprehensive monitoring and observability.
Provides full visibility into system behavior.

Components:
- TracingEngine: Distributed tracing
- MetricsCollector: Metrics collection
- AlertManager: Alert management
- DashboardEngine: Visualization dashboards
- LogAggregator: Log collection and analysis
"""

from .alert_manager import (Alert, AlertManager, AlertRule, AlertSeverity,
                            NotificationChannel)
from .dashboard_engine import (ChartType, Dashboard, DashboardEngine, Panel,
                               Widget)
from .log_aggregator import (LogAggregator, LogEntry, LogLevel, LogPattern,
                             LogQuery)
from .metrics_collector import (Counter, Gauge, Histogram, Metric,
                                MetricsCollector, Timer)
from .tracing_engine import (Span, SpanContext, TraceExporter, Tracer,
                             TracingEngine)

__all__ = [
    # Tracing
    "TracingEngine",
    "Span",
    "SpanContext",
    "Tracer",
    "TraceExporter",
    # Metrics
    "MetricsCollector",
    "Metric",
    "Counter",
    "Gauge",
    "Histogram",
    "Timer",
    # Alerts
    "AlertManager",
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "NotificationChannel",
    # Dashboards
    "DashboardEngine",
    "Dashboard",
    "Panel",
    "Widget",
    "ChartType",
    # Logs
    "LogAggregator",
    "LogEntry",
    "LogLevel",
    "LogQuery",
    "LogPattern",
]
