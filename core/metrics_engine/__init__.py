"""
BAEL Metrics Engine
===================

Prometheus-style metrics with:
- Counters, Gauges, Histograms
- Labels and dimensions
- Exporters
- Aggregation

"Ba'el measures all dimensions of reality." — Ba'el
"""

from .metrics_engine import (
    # Enums
    MetricType,
    AggregationType,

    # Data structures
    MetricLabels,
    MetricValue,
    Counter,
    Gauge,
    Histogram,
    Summary,
    MetricsConfig,

    # Engine
    MetricsRegistry,
    MetricsEngine,
    metrics_engine,
)

__all__ = [
    # Enums
    "MetricType",
    "AggregationType",

    # Data structures
    "MetricLabels",
    "MetricValue",
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "MetricsConfig",

    # Engine
    "MetricsRegistry",
    "MetricsEngine",
    "metrics_engine",
]
