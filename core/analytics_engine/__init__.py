"""
BAEL Analytics Engine
=====================

Real-time analytics, metrics, time series, and alerting.

"Ba'el sees all patterns in the data." — Ba'el
"""

from core.analytics_engine.analytics_engine import (
    # Enums
    MetricType,
    AggregationType,
    AlertSeverity,
    AlertState,
    TimeGranularity,

    # Data structures
    DataPoint,
    MetricDefinition,
    TimeSeriesData,
    AlertRule,
    Alert,
    Dashboard,
    Panel,
    AnalyticsConfig,

    # Classes
    AnalyticsEngine,
    MetricsCollector,
    TimeSeriesStore,
    Aggregator,
    AlertManager,
    DashboardManager,

    # Instance
    analytics_engine
)

__all__ = [
    # Enums
    'MetricType',
    'AggregationType',
    'AlertSeverity',
    'AlertState',
    'TimeGranularity',

    # Data structures
    'DataPoint',
    'MetricDefinition',
    'TimeSeriesData',
    'AlertRule',
    'Alert',
    'Dashboard',
    'Panel',
    'AnalyticsConfig',

    # Classes
    'AnalyticsEngine',
    'MetricsCollector',
    'TimeSeriesStore',
    'Aggregator',
    'AlertManager',
    'DashboardManager',

    # Instance
    'analytics_engine'
]
