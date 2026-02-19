"""
BAEL Analytics Engine
=====================

Comprehensive analytics with:
- Real-time metrics collection
- Time series storage and querying
- Multiple aggregation types
- Anomaly detection
- Alerting system
- Dashboard management

"Ba'el perceives all patterns across time and space." — Ba'el
"""

import asyncio
import logging
import time
import statistics
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict, deque
import threading
import uuid
import json
import re

logger = logging.getLogger("BAEL.Analytics")


# ============================================================================
# ENUMS
# ============================================================================

class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"       # Monotonically increasing
    GAUGE = "gauge"           # Point-in-time value
    HISTOGRAM = "histogram"   # Distribution
    SUMMARY = "summary"       # Statistical summary
    RATE = "rate"             # Events per second


class AggregationType(Enum):
    """Aggregation functions."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    MEDIAN = "median"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"
    STDDEV = "stddev"
    VARIANCE = "variance"
    RATE = "rate"
    INCREASE = "increase"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(Enum):
    """Alert states."""
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"


class TimeGranularity(Enum):
    """Time granularities."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DataPoint:
    """A single data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'labels': self.labels
        }


@dataclass
class MetricDefinition:
    """Definition of a metric."""
    name: str
    metric_type: MetricType = MetricType.GAUGE
    description: str = ""
    unit: str = ""
    labels: List[str] = field(default_factory=list)

    # Retention
    retention_days: int = 30

    # Aggregations to compute
    aggregations: List[AggregationType] = field(
        default_factory=lambda: [
            AggregationType.AVG,
            AggregationType.MAX,
            AggregationType.MIN
        ]
    )


@dataclass
class TimeSeriesData:
    """Time series data container."""
    metric_name: str
    labels: Dict[str, str]
    data_points: List[DataPoint] = field(default_factory=list)

    # Computed aggregations
    aggregations: Dict[str, float] = field(default_factory=dict)

    @property
    def latest_value(self) -> Optional[float]:
        if self.data_points:
            return self.data_points[-1].value
        return None

    @property
    def first_value(self) -> Optional[float]:
        if self.data_points:
            return self.data_points[0].value
        return None


@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str
    name: str
    metric_name: str

    # Condition
    condition: str  # Expression like "value > 100"

    # Timing
    for_duration_seconds: int = 0  # How long condition must be true

    # Severity and labels
    severity: AlertSeverity = AlertSeverity.WARNING
    labels: Dict[str, str] = field(default_factory=dict)

    # Annotations
    summary: str = ""
    description: str = ""

    # Actions
    notify_channels: List[str] = field(default_factory=list)


@dataclass
class Alert:
    """An active alert."""
    id: str
    rule: AlertRule
    state: AlertState = AlertState.PENDING

    # Values
    current_value: Optional[float] = None

    # Timestamps
    starts_at: datetime = field(default_factory=datetime.now)
    ends_at: Optional[datetime] = None

    # Labels and annotations
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'rule_name': self.rule.name,
            'state': self.state.value,
            'severity': self.rule.severity.value,
            'current_value': self.current_value,
            'starts_at': self.starts_at.isoformat(),
            'ends_at': self.ends_at.isoformat() if self.ends_at else None,
            'labels': self.labels,
            'annotations': self.annotations
        }


@dataclass
class Panel:
    """Dashboard panel."""
    id: str
    title: str

    # Query
    metric_name: str
    aggregation: AggregationType = AggregationType.AVG
    labels: Dict[str, str] = field(default_factory=dict)

    # Display
    panel_type: str = "line"  # line, bar, gauge, table
    width: int = 6
    height: int = 4
    position_x: int = 0
    position_y: int = 0

    # Options
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dashboard:
    """Analytics dashboard."""
    id: str
    name: str
    description: str = ""

    # Panels
    panels: List[Panel] = field(default_factory=list)

    # Time range
    default_time_range: str = "1h"
    refresh_interval: int = 30

    # Variables
    variables: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AnalyticsConfig:
    """Analytics engine configuration."""
    # Retention
    default_retention_days: int = 30

    # Sampling
    sample_rate: float = 1.0  # 1.0 = keep all

    # Aggregation
    aggregation_interval_seconds: int = 60

    # Alerting
    enable_alerting: bool = True
    alert_check_interval_seconds: int = 10

    # Storage
    max_data_points_per_series: int = 10000


# ============================================================================
# METRICS COLLECTOR
# ============================================================================

class MetricsCollector:
    """
    Collects and stores metrics.
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        """Initialize metrics collector."""
        self.config = config or AnalyticsConfig()

        self._definitions: Dict[str, MetricDefinition] = {}
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)

        self._lock = threading.RLock()

    def define(self, definition: MetricDefinition) -> None:
        """Define a metric."""
        self._definitions[definition.name] = definition

    def inc(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def set(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe a histogram value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

    def get_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """Get counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)

    def get_gauge(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key)

    def get_histogram(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, float]]:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        values = self._histograms.get(key)

        if not values:
            return None

        sorted_values = sorted(values)
        return {
            'count': len(values),
            'sum': sum(values),
            'avg': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'p50': self._percentile(sorted_values, 50),
            'p90': self._percentile(sorted_values, 90),
            'p95': self._percentile(sorted_values, 95),
            'p99': self._percentile(sorted_values, 99)
        }

    def _make_key(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """Make a unique key for a metric + labels."""
        if not labels:
            return name

        label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _percentile(self, sorted_values: List[float], p: float) -> float:
        """Calculate percentile."""
        if not sorted_values:
            return 0.0

        idx = (len(sorted_values) - 1) * p / 100
        lower = math.floor(idx)
        upper = math.ceil(idx)

        if lower == upper:
            return sorted_values[int(idx)]

        return sorted_values[lower] * (upper - idx) + sorted_values[upper] * (idx - lower)

    def collect_all(self) -> Dict[str, Any]:
        """Collect all current metric values."""
        with self._lock:
            result = {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': {}
            }

            for key, values in self._histograms.items():
                if values:
                    sorted_values = sorted(values)
                    result['histograms'][key] = {
                        'count': len(values),
                        'sum': sum(values),
                        'avg': statistics.mean(values),
                        'p95': self._percentile(sorted_values, 95)
                    }

            return result


# ============================================================================
# TIME SERIES STORE
# ============================================================================

class TimeSeriesStore:
    """
    Stores time series data.
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        """Initialize time series store."""
        self.config = config or AnalyticsConfig()

        # series_key -> deque of DataPoints
        self._series: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.config.max_data_points_per_series)
        )

        self._lock = threading.RLock()

    def write(
        self,
        metric_name: str,
        value: float,
        timestamp: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Write a data point."""
        key = self._make_series_key(metric_name, labels)

        point = DataPoint(
            timestamp=timestamp or datetime.now(),
            value=value,
            labels=labels or {}
        )

        with self._lock:
            self._series[key].append(point)

    def query(
        self,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> TimeSeriesData:
        """Query time series data."""
        key = self._make_series_key(metric_name, labels)

        with self._lock:
            points = list(self._series.get(key, []))

        # Filter by time range
        if start_time:
            points = [p for p in points if p.timestamp >= start_time]
        if end_time:
            points = [p for p in points if p.timestamp <= end_time]

        # Apply limit
        if limit and len(points) > limit:
            points = points[-limit:]

        return TimeSeriesData(
            metric_name=metric_name,
            labels=labels or {},
            data_points=points
        )

    def query_range(
        self,
        metric_name: str,
        time_range: str,  # e.g., "1h", "24h", "7d"
        labels: Optional[Dict[str, str]] = None
    ) -> TimeSeriesData:
        """Query with a time range string."""
        start_time = self._parse_time_range(time_range)
        return self.query(metric_name, labels, start_time=start_time)

    def aggregate(
        self,
        metric_name: str,
        aggregation: AggregationType,
        labels: Optional[Dict[str, str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[float]:
        """Aggregate time series data."""
        data = self.query(metric_name, labels, start_time, end_time)

        if not data.data_points:
            return None

        values = [p.value for p in data.data_points]
        return self._compute_aggregation(values, aggregation)

    def _make_series_key(
        self,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """Make a unique series key."""
        if not labels:
            return metric_name

        label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
        return f"{metric_name}{{{label_str}}}"

    def _parse_time_range(self, time_range: str) -> datetime:
        """Parse time range string to datetime."""
        now = datetime.now()

        match = re.match(r'(\d+)([smhdw])', time_range)
        if not match:
            return now - timedelta(hours=1)

        value = int(match.group(1))
        unit = match.group(2)

        if unit == 's':
            return now - timedelta(seconds=value)
        elif unit == 'm':
            return now - timedelta(minutes=value)
        elif unit == 'h':
            return now - timedelta(hours=value)
        elif unit == 'd':
            return now - timedelta(days=value)
        elif unit == 'w':
            return now - timedelta(weeks=value)

        return now - timedelta(hours=1)

    def _compute_aggregation(
        self,
        values: List[float],
        aggregation: AggregationType
    ) -> float:
        """Compute an aggregation."""
        if not values:
            return 0.0

        if aggregation == AggregationType.SUM:
            return sum(values)
        elif aggregation == AggregationType.AVG:
            return statistics.mean(values)
        elif aggregation == AggregationType.MIN:
            return min(values)
        elif aggregation == AggregationType.MAX:
            return max(values)
        elif aggregation == AggregationType.COUNT:
            return float(len(values))
        elif aggregation == AggregationType.MEDIAN:
            return statistics.median(values)
        elif aggregation in (AggregationType.P50, AggregationType.P90,
                            AggregationType.P95, AggregationType.P99):
            p = int(aggregation.value[1:])
            sorted_values = sorted(values)
            idx = (len(sorted_values) - 1) * p / 100
            lower = math.floor(idx)
            upper = math.ceil(idx)
            if lower == upper:
                return sorted_values[int(idx)]
            return sorted_values[lower] * (upper - idx) + sorted_values[upper] * (idx - lower)
        elif aggregation == AggregationType.STDDEV:
            return statistics.stdev(values) if len(values) > 1 else 0.0
        elif aggregation == AggregationType.VARIANCE:
            return statistics.variance(values) if len(values) > 1 else 0.0
        elif aggregation == AggregationType.RATE:
            if len(values) < 2:
                return 0.0
            return (values[-1] - values[0]) / len(values)
        elif aggregation == AggregationType.INCREASE:
            if len(values) < 2:
                return 0.0
            return values[-1] - values[0]

        return 0.0


# ============================================================================
# AGGREGATOR
# ============================================================================

class Aggregator:
    """
    Aggregates metrics over time windows.
    """

    def __init__(self, store: TimeSeriesStore):
        """Initialize aggregator."""
        self._store = store

    def downsample(
        self,
        metric_name: str,
        granularity: TimeGranularity,
        aggregation: AggregationType = AggregationType.AVG,
        labels: Optional[Dict[str, str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[DataPoint]:
        """Downsample data to a lower granularity."""
        data = self._store.query(metric_name, labels, start_time, end_time)

        if not data.data_points:
            return []

        # Group by time bucket
        buckets: Dict[datetime, List[float]] = defaultdict(list)

        for point in data.data_points:
            bucket = self._get_bucket(point.timestamp, granularity)
            buckets[bucket].append(point.value)

        # Aggregate each bucket
        result = []
        for bucket_time, values in sorted(buckets.items()):
            agg_value = self._store._compute_aggregation(values, aggregation)
            result.append(DataPoint(
                timestamp=bucket_time,
                value=agg_value,
                labels=labels or {}
            ))

        return result

    def _get_bucket(
        self,
        timestamp: datetime,
        granularity: TimeGranularity
    ) -> datetime:
        """Get the bucket for a timestamp."""
        if granularity == TimeGranularity.SECOND:
            return timestamp.replace(microsecond=0)
        elif granularity == TimeGranularity.MINUTE:
            return timestamp.replace(second=0, microsecond=0)
        elif granularity == TimeGranularity.HOUR:
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif granularity == TimeGranularity.DAY:
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == TimeGranularity.WEEK:
            # Start of week (Monday)
            days_since_monday = timestamp.weekday()
            return (timestamp - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif granularity == TimeGranularity.MONTH:
            return timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return timestamp


# ============================================================================
# ALERT MANAGER
# ============================================================================

class AlertManager:
    """
    Manages alerts and notifications.
    """

    def __init__(self, store: TimeSeriesStore):
        """Initialize alert manager."""
        self._store = store

        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._pending: Dict[str, datetime] = {}  # rule_id -> pending since

        self._handlers: List[Callable[[Alert], None]] = []

        self._running = False
        self._task: Optional[asyncio.Task] = None

        self._lock = threading.RLock()

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                if rule_id in self._alerts:
                    del self._alerts[rule_id]
                return True
            return False

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler."""
        self._handlers.append(handler)

    async def start(self, interval: int = 10) -> None:
        """Start alert checking."""
        self._running = True
        self._task = asyncio.create_task(self._check_loop(interval))
        logger.info("AlertManager started")

    async def stop(self) -> None:
        """Stop alert checking."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("AlertManager stopped")

    async def _check_loop(self, interval: int) -> None:
        """Main alert check loop."""
        while self._running:
            try:
                self._check_alerts()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert check error: {e}")
                await asyncio.sleep(interval)

    def _check_alerts(self) -> None:
        """Check all alert rules."""
        now = datetime.now()

        with self._lock:
            for rule in self._rules.values():
                try:
                    # Get current value
                    value = self._store.aggregate(
                        rule.metric_name,
                        AggregationType.AVG,
                        start_time=now - timedelta(minutes=5)
                    )

                    if value is None:
                        continue

                    # Evaluate condition
                    is_firing = self._evaluate_condition(rule.condition, value)

                    if is_firing:
                        self._handle_firing(rule, value, now)
                    else:
                        self._handle_resolved(rule, now)

                except Exception as e:
                    logger.error(f"Error checking rule {rule.id}: {e}")

    def _evaluate_condition(self, condition: str, value: float) -> bool:
        """Evaluate alert condition."""
        try:
            # Simple expression evaluation
            # Supports: value > 100, value < 50, value >= 80, value == 0
            expr = condition.replace('value', str(value))
            return eval(expr)
        except Exception:
            return False

    def _handle_firing(
        self,
        rule: AlertRule,
        value: float,
        now: datetime
    ) -> None:
        """Handle a firing alert."""
        # Check for duration
        if rule.for_duration_seconds > 0:
            if rule.id not in self._pending:
                self._pending[rule.id] = now
                return

            pending_since = self._pending[rule.id]
            elapsed = (now - pending_since).total_seconds()

            if elapsed < rule.for_duration_seconds:
                return

        # Create or update alert
        if rule.id in self._alerts:
            alert = self._alerts[rule.id]
            alert.current_value = value
        else:
            alert = Alert(
                id=str(uuid.uuid4()),
                rule=rule,
                state=AlertState.FIRING,
                current_value=value,
                labels=rule.labels.copy(),
                annotations={
                    'summary': rule.summary,
                    'description': rule.description
                }
            )
            self._alerts[rule.id] = alert

            # Notify handlers
            for handler in self._handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")

            logger.warning(f"Alert firing: {rule.name} (value={value})")

    def _handle_resolved(self, rule: AlertRule, now: datetime) -> None:
        """Handle a resolved alert."""
        # Clear pending
        if rule.id in self._pending:
            del self._pending[rule.id]

        # Resolve active alert
        if rule.id in self._alerts:
            alert = self._alerts[rule.id]
            alert.state = AlertState.RESOLVED
            alert.ends_at = now

            # Notify handlers
            for handler in self._handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")

            del self._alerts[rule.id]
            logger.info(f"Alert resolved: {rule.name}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        with self._lock:
            return list(self._alerts.values())

    def get_alert_count(self) -> Dict[str, int]:
        """Get alert counts by severity."""
        counts = {s.value: 0 for s in AlertSeverity}
        with self._lock:
            for alert in self._alerts.values():
                counts[alert.rule.severity.value] += 1
        return counts


# ============================================================================
# DASHBOARD MANAGER
# ============================================================================

class DashboardManager:
    """
    Manages analytics dashboards.
    """

    def __init__(self, store: TimeSeriesStore):
        """Initialize dashboard manager."""
        self._store = store
        self._dashboards: Dict[str, Dashboard] = {}

    def create(
        self,
        name: str,
        description: str = ""
    ) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(
            id=str(uuid.uuid4()),
            name=name,
            description=description
        )
        self._dashboards[dashboard.id] = dashboard
        return dashboard

    def get(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a dashboard by ID."""
        return self._dashboards.get(dashboard_id)

    def list(self) -> List[Dashboard]:
        """List all dashboards."""
        return list(self._dashboards.values())

    def delete(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False

    def add_panel(
        self,
        dashboard_id: str,
        panel: Panel
    ) -> bool:
        """Add a panel to a dashboard."""
        dashboard = self._dashboards.get(dashboard_id)
        if dashboard:
            dashboard.panels.append(panel)
            dashboard.updated_at = datetime.now()
            return True
        return False

    def remove_panel(
        self,
        dashboard_id: str,
        panel_id: str
    ) -> bool:
        """Remove a panel from a dashboard."""
        dashboard = self._dashboards.get(dashboard_id)
        if dashboard:
            dashboard.panels = [p for p in dashboard.panels if p.id != panel_id]
            dashboard.updated_at = datetime.now()
            return True
        return False

    def render(
        self,
        dashboard_id: str,
        time_range: str = "1h"
    ) -> Dict[str, Any]:
        """Render a dashboard with data."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return {}

        panels_data = []

        for panel in dashboard.panels:
            data = self._store.query_range(
                panel.metric_name,
                time_range,
                panel.labels
            )

            agg_value = self._store.aggregate(
                panel.metric_name,
                panel.aggregation,
                labels=panel.labels,
                start_time=self._store._parse_time_range(time_range)
            )

            panels_data.append({
                'panel': {
                    'id': panel.id,
                    'title': panel.title,
                    'type': panel.panel_type,
                    'position': {
                        'x': panel.position_x,
                        'y': panel.position_y,
                        'w': panel.width,
                        'h': panel.height
                    }
                },
                'data': [p.to_dict() for p in data.data_points],
                'aggregation': agg_value
            })

        return {
            'dashboard': {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description
            },
            'time_range': time_range,
            'panels': panels_data
        }


# ============================================================================
# MAIN ANALYTICS ENGINE
# ============================================================================

class AnalyticsEngine:
    """
    Main analytics engine.

    Features:
    - Real-time metrics collection
    - Time series storage
    - Aggregations and downsampling
    - Alerting
    - Dashboards

    "Ba'el analyzes all data streams." — Ba'el
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        """Initialize analytics engine."""
        self.config = config or AnalyticsConfig()

        # Components
        self.collector = MetricsCollector(self.config)
        self.store = TimeSeriesStore(self.config)
        self.aggregator = Aggregator(self.store)
        self.alerts = AlertManager(self.store)
        self.dashboards = DashboardManager(self.store)

        self._running = False

        logger.info("AnalyticsEngine initialized")

    async def start(self) -> None:
        """Start the analytics engine."""
        self._running = True

        if self.config.enable_alerting:
            await self.alerts.start(self.config.alert_check_interval_seconds)

        logger.info("AnalyticsEngine started")

    async def stop(self) -> None:
        """Stop the analytics engine."""
        self._running = False
        await self.alerts.stop()
        logger.info("AnalyticsEngine stopped")

    # ========================================================================
    # METRICS
    # ========================================================================

    def counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        self.collector.inc(name, value, labels)
        self.store.write(name, self.collector.get_counter(name, labels), labels=labels)

    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric."""
        self.collector.set(name, value, labels)
        self.store.write(name, value, labels=labels)

    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram observation."""
        self.collector.observe(name, value, labels)
        self.store.write(name, value, labels=labels)

    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing code."""
        return _Timer(self, name, labels)

    # ========================================================================
    # QUERYING
    # ========================================================================

    def query(
        self,
        metric_name: str,
        time_range: str = "1h",
        labels: Optional[Dict[str, str]] = None
    ) -> TimeSeriesData:
        """Query time series data."""
        return self.store.query_range(metric_name, time_range, labels)

    def aggregate(
        self,
        metric_name: str,
        aggregation: AggregationType,
        time_range: str = "1h",
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Aggregate metric data."""
        start_time = self.store._parse_time_range(time_range)
        return self.store.aggregate(metric_name, aggregation, labels, start_time)

    # ========================================================================
    # ALERTING
    # ========================================================================

    def add_alert_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        for_duration: int = 0
    ) -> AlertRule:
        """Add an alert rule."""
        rule = AlertRule(
            id=str(uuid.uuid4()),
            name=name,
            metric_name=metric_name,
            condition=condition,
            severity=severity,
            for_duration_seconds=for_duration
        )
        self.alerts.add_rule(rule)
        return rule

    def get_active_alerts(self) -> List[Alert]:
        """Get active alerts."""
        return self.alerts.get_active_alerts()

    # ========================================================================
    # DASHBOARDS
    # ========================================================================

    def create_dashboard(
        self,
        name: str,
        description: str = ""
    ) -> Dashboard:
        """Create a dashboard."""
        return self.dashboards.create(name, description)

    def add_panel(
        self,
        dashboard_id: str,
        title: str,
        metric_name: str,
        panel_type: str = "line"
    ) -> Panel:
        """Add a panel to a dashboard."""
        panel = Panel(
            id=str(uuid.uuid4()),
            title=title,
            metric_name=metric_name,
            panel_type=panel_type
        )
        self.dashboards.add_panel(dashboard_id, panel)
        return panel

    def render_dashboard(
        self,
        dashboard_id: str,
        time_range: str = "1h"
    ) -> Dict[str, Any]:
        """Render a dashboard."""
        return self.dashboards.render(dashboard_id, time_range)

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'running': self._running,
            'metrics': self.collector.collect_all(),
            'alerts': {
                'active': len(self.alerts.get_active_alerts()),
                'by_severity': self.alerts.get_alert_count()
            },
            'dashboards': len(self.dashboards.list())
        }


# ============================================================================
# TIMER CONTEXT MANAGER
# ============================================================================

class _Timer:
    """Context manager for timing code."""

    def __init__(
        self,
        engine: AnalyticsEngine,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ):
        self._engine = engine
        self._name = name
        self._labels = labels
        self._start_time: Optional[float] = None

    def __enter__(self):
        self._start_time = time.time()
        return self

    def __exit__(self, *args):
        if self._start_time:
            elapsed = (time.time() - self._start_time) * 1000  # ms
            self._engine.histogram(self._name, elapsed, self._labels)


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

analytics_engine = AnalyticsEngine()
