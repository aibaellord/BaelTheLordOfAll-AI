"""
Monitoring module for BAEL.

Provides Prometheus metrics, OpenTelemetry tracing, and monitoring utilities.
"""

from .prometheus_exporter import BAELMetrics, metrics_registry
from .tracing import get_tracer, setup_tracing

__all__ = ['BAELMetrics', 'metrics_registry', 'setup_tracing', 'get_tracer']
