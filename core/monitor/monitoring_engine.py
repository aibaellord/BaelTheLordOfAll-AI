#!/usr/bin/env python3
"""
BAEL - Monitoring Engine
Production model monitoring and observability.

Features:
- Performance monitoring
- Data drift detection
- Model drift detection
- Alerting system
- Metrics collection
"""

import asyncio
import json
import math
import os
import random
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class DriftType(Enum):
    """Drift types."""
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    PERFORMANCE_DRIFT = "performance_drift"


class MonitoringStatus(Enum):
    """Monitoring status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AggregationType(Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class MetricSeries:
    """Time series of metric points."""
    name: str
    points: List[MetricPoint] = field(default_factory=list)
    max_points: int = 1000

    def add(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        point = MetricPoint(
            name=self.name,
            value=value,
            labels=labels or {}
        )
        self.points.append(point)

        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]

    def get_values(self) -> List[float]:
        return [p.value for p in self.points]

    def aggregate(self, agg_type: AggregationType) -> float:
        values = self.get_values()
        if not values:
            return 0.0

        if agg_type == AggregationType.SUM:
            return sum(values)
        elif agg_type == AggregationType.AVG:
            return statistics.mean(values)
        elif agg_type == AggregationType.MIN:
            return min(values)
        elif agg_type == AggregationType.MAX:
            return max(values)
        elif agg_type == AggregationType.COUNT:
            return len(values)
        elif agg_type == AggregationType.P50:
            return statistics.median(values)
        elif agg_type in (AggregationType.P90, AggregationType.P95, AggregationType.P99):
            percentiles = {
                AggregationType.P90: 0.90,
                AggregationType.P95: 0.95,
                AggregationType.P99: 0.99
            }
            p = percentiles[agg_type]
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * p)
            return sorted_vals[min(idx, len(sorted_vals) - 1)]

        return 0.0


@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str = ""
    name: str = ""
    metric_name: str = ""
    condition: str = "gt"
    threshold: float = 0.0
    severity: AlertSeverity = AlertSeverity.WARNING
    duration_seconds: int = 60
    labels: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def __post_init__(self):
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())[:8]


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str = ""
    rule_id: str = ""
    name: str = ""
    message: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.ACTIVE
    metric_value: float = 0.0
    threshold: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    fired_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    def __post_init__(self):
        if not self.alert_id:
            self.alert_id = str(uuid.uuid4())[:8]


@dataclass
class DriftResult:
    """Drift detection result."""
    drift_id: str = ""
    drift_type: DriftType = DriftType.DATA_DRIFT
    detected: bool = False
    score: float = 0.0
    threshold: float = 0.5
    feature_scores: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.drift_id:
            self.drift_id = str(uuid.uuid4())[:8]


@dataclass
class ModelHealth:
    """Model health status."""
    model_id: str = ""
    status: MonitoringStatus = MonitoringStatus.UNKNOWN
    latency_p50_ms: float = 0.0
    latency_p99_ms: float = 0.0
    error_rate: float = 0.0
    request_rate: float = 0.0
    drift_detected: bool = False
    active_alerts: int = 0
    last_check: datetime = field(default_factory=datetime.now)


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    collection_interval_s: int = 60
    retention_hours: int = 24
    drift_check_interval_s: int = 3600
    alert_check_interval_s: int = 60
    enable_drift_detection: bool = True
    enable_alerting: bool = True


# =============================================================================
# METRICS COLLECTORS
# =============================================================================

class BaseCollector(ABC):
    """Abstract base metrics collector."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get collector name."""
        pass

    @abstractmethod
    def collect(self) -> List[MetricPoint]:
        """Collect metrics."""
        pass


class LatencyCollector(BaseCollector):
    """Latency metrics collector."""

    def __init__(self):
        self._latencies: deque = deque(maxlen=1000)

    @property
    def name(self) -> str:
        return "latency"

    def record(self, latency_ms: float) -> None:
        self._latencies.append(latency_ms)

    def collect(self) -> List[MetricPoint]:
        if not self._latencies:
            return []

        values = list(self._latencies)
        sorted_vals = sorted(values)

        return [
            MetricPoint(
                name="latency_p50_ms",
                value=sorted_vals[len(sorted_vals) // 2],
                metric_type=MetricType.GAUGE
            ),
            MetricPoint(
                name="latency_p99_ms",
                value=sorted_vals[int(len(sorted_vals) * 0.99)],
                metric_type=MetricType.GAUGE
            ),
            MetricPoint(
                name="latency_avg_ms",
                value=statistics.mean(values),
                metric_type=MetricType.GAUGE
            )
        ]


class ThroughputCollector(BaseCollector):
    """Throughput metrics collector."""

    def __init__(self):
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0
        self._last_reset = time.time()

    @property
    def name(self) -> str:
        return "throughput"

    def record_request(self, success: bool = True) -> None:
        self._request_count += 1
        if success:
            self._success_count += 1
        else:
            self._error_count += 1

    def collect(self) -> List[MetricPoint]:
        elapsed = time.time() - self._last_reset
        if elapsed == 0:
            elapsed = 1

        rps = self._request_count / elapsed
        error_rate = self._error_count / max(self._request_count, 1)

        metrics = [
            MetricPoint(
                name="request_rate",
                value=rps,
                metric_type=MetricType.GAUGE
            ),
            MetricPoint(
                name="error_rate",
                value=error_rate,
                metric_type=MetricType.GAUGE
            ),
            MetricPoint(
                name="total_requests",
                value=self._request_count,
                metric_type=MetricType.COUNTER
            )
        ]

        return metrics

    def reset(self) -> None:
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0
        self._last_reset = time.time()


class ResourceCollector(BaseCollector):
    """Resource utilization collector."""

    @property
    def name(self) -> str:
        return "resources"

    def collect(self) -> List[MetricPoint]:
        cpu = random.uniform(0.3, 0.8)
        memory = random.uniform(0.4, 0.7)
        gpu_memory = random.uniform(0.5, 0.9)

        return [
            MetricPoint(
                name="cpu_utilization",
                value=cpu,
                metric_type=MetricType.GAUGE
            ),
            MetricPoint(
                name="memory_utilization",
                value=memory,
                metric_type=MetricType.GAUGE
            ),
            MetricPoint(
                name="gpu_memory_utilization",
                value=gpu_memory,
                metric_type=MetricType.GAUGE
            )
        ]


# =============================================================================
# DRIFT DETECTORS
# =============================================================================

class BaseDriftDetector(ABC):
    """Abstract base drift detector."""

    @property
    @abstractmethod
    def drift_type(self) -> DriftType:
        """Get drift type."""
        pass

    @abstractmethod
    def detect(
        self,
        reference: List[float],
        current: List[float]
    ) -> DriftResult:
        """Detect drift."""
        pass


class KSTestDriftDetector(BaseDriftDetector):
    """Kolmogorov-Smirnov test drift detector."""

    def __init__(self, threshold: float = 0.1):
        self._threshold = threshold

    @property
    def drift_type(self) -> DriftType:
        return DriftType.DATA_DRIFT

    def _ks_statistic(
        self,
        sample1: List[float],
        sample2: List[float]
    ) -> float:
        """Compute KS statistic."""
        all_vals = sorted(set(sample1 + sample2))

        n1, n2 = len(sample1), len(sample2)
        cdf1 = [sum(1 for x in sample1 if x <= v) / n1 for v in all_vals]
        cdf2 = [sum(1 for x in sample2 if x <= v) / n2 for v in all_vals]

        return max(abs(c1 - c2) for c1, c2 in zip(cdf1, cdf2))

    def detect(
        self,
        reference: List[float],
        current: List[float]
    ) -> DriftResult:
        if not reference or not current:
            return DriftResult(drift_type=self.drift_type)

        ks_stat = self._ks_statistic(reference, current)

        return DriftResult(
            drift_type=self.drift_type,
            detected=ks_stat > self._threshold,
            score=ks_stat,
            threshold=self._threshold,
            details={"ks_statistic": ks_stat}
        )


class PredictionDriftDetector(BaseDriftDetector):
    """Prediction distribution drift detector."""

    def __init__(self, threshold: float = 0.15):
        self._threshold = threshold

    @property
    def drift_type(self) -> DriftType:
        return DriftType.PREDICTION_DRIFT

    def detect(
        self,
        reference: List[float],
        current: List[float]
    ) -> DriftResult:
        if not reference or not current:
            return DriftResult(drift_type=self.drift_type)

        ref_mean = statistics.mean(reference)
        cur_mean = statistics.mean(current)

        ref_std = statistics.stdev(reference) if len(reference) > 1 else 1

        if ref_std == 0:
            ref_std = 1

        normalized_diff = abs(cur_mean - ref_mean) / ref_std

        return DriftResult(
            drift_type=self.drift_type,
            detected=normalized_diff > self._threshold,
            score=normalized_diff,
            threshold=self._threshold,
            details={
                "reference_mean": ref_mean,
                "current_mean": cur_mean,
                "normalized_difference": normalized_diff
            }
        )


class PerformanceDriftDetector(BaseDriftDetector):
    """Performance metrics drift detector."""

    def __init__(self, threshold: float = 0.2):
        self._threshold = threshold

    @property
    def drift_type(self) -> DriftType:
        return DriftType.PERFORMANCE_DRIFT

    def detect(
        self,
        reference: List[float],
        current: List[float]
    ) -> DriftResult:
        if not reference or not current:
            return DriftResult(drift_type=self.drift_type)

        ref_mean = statistics.mean(reference)
        cur_mean = statistics.mean(current)

        if ref_mean == 0:
            relative_change = 0 if cur_mean == 0 else 1
        else:
            relative_change = abs(cur_mean - ref_mean) / ref_mean

        return DriftResult(
            drift_type=self.drift_type,
            detected=relative_change > self._threshold,
            score=relative_change,
            threshold=self._threshold,
            details={
                "reference_performance": ref_mean,
                "current_performance": cur_mean,
                "relative_change": relative_change
            }
        )


# =============================================================================
# ALERT EVALUATOR
# =============================================================================

class AlertEvaluator:
    """Alert rule evaluator."""

    def __init__(self):
        self._operators = {
            "gt": lambda v, t: v > t,
            "gte": lambda v, t: v >= t,
            "lt": lambda v, t: v < t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
            "neq": lambda v, t: v != t
        }

    def evaluate(
        self,
        rule: AlertRule,
        metric_value: float
    ) -> Optional[Alert]:
        """Evaluate alert rule."""
        if not rule.enabled:
            return None

        operator = self._operators.get(rule.condition, self._operators["gt"])

        if operator(metric_value, rule.threshold):
            return Alert(
                rule_id=rule.rule_id,
                name=rule.name,
                message=f"{rule.name}: {metric_value:.2f} {rule.condition} {rule.threshold}",
                severity=rule.severity,
                metric_value=metric_value,
                threshold=rule.threshold,
                labels=rule.labels
            )

        return None


# =============================================================================
# MONITORING ENGINE
# =============================================================================

class MonitoringEngine:
    """
    Monitoring Engine for BAEL.

    Production model monitoring and observability.
    """

    def __init__(self, config: Optional[MonitoringConfig] = None):
        self._config = config or MonitoringConfig()

        self._collectors: Dict[str, BaseCollector] = {
            "latency": LatencyCollector(),
            "throughput": ThroughputCollector(),
            "resources": ResourceCollector()
        }

        self._metrics: Dict[str, MetricSeries] = {}

        self._drift_detectors: Dict[DriftType, BaseDriftDetector] = {
            DriftType.DATA_DRIFT: KSTestDriftDetector(),
            DriftType.PREDICTION_DRIFT: PredictionDriftDetector(),
            DriftType.PERFORMANCE_DRIFT: PerformanceDriftDetector()
        }

        self._alert_rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._alert_evaluator = AlertEvaluator()

        self._model_health: Dict[str, ModelHealth] = {}
        self._drift_history: List[DriftResult] = []

    def register_collector(
        self,
        name: str,
        collector: BaseCollector
    ) -> None:
        """Register a metrics collector."""
        self._collectors[name] = collector

    def record_latency(self, latency_ms: float) -> None:
        """Record latency metric."""
        collector = self._collectors.get("latency")
        if isinstance(collector, LatencyCollector):
            collector.record(latency_ms)

    def record_request(self, success: bool = True) -> None:
        """Record request metric."""
        collector = self._collectors.get("throughput")
        if isinstance(collector, ThroughputCollector):
            collector.record_request(success)

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a custom metric."""
        if name not in self._metrics:
            self._metrics[name] = MetricSeries(name=name)

        self._metrics[name].add(value, labels)

    async def collect_metrics(self) -> List[MetricPoint]:
        """Collect all metrics."""
        all_metrics = []

        for collector in self._collectors.values():
            metrics = collector.collect()
            all_metrics.extend(metrics)

            for metric in metrics:
                self.record_metric(metric.name, metric.value, metric.labels)

        return all_metrics

    def get_metric(
        self,
        name: str,
        aggregation: AggregationType = AggregationType.AVG
    ) -> float:
        """Get aggregated metric value."""
        series = self._metrics.get(name)
        if not series:
            return 0.0

        return series.aggregate(aggregation)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._alert_rules[rule.rule_id] = rule

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self._alert_rules:
            del self._alert_rules[rule_id]
            return True
        return False

    async def check_alerts(self) -> List[Alert]:
        """Check all alert rules."""
        new_alerts = []

        for rule in self._alert_rules.values():
            metric_value = self.get_metric(rule.metric_name)

            alert = self._alert_evaluator.evaluate(rule, metric_value)

            if alert:
                self._alerts[alert.alert_id] = alert
                new_alerts.append(alert)

        return new_alerts

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = user
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if alert and alert.status != AlertStatus.RESOLVED:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            return True
        return False

    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get active alerts."""
        active = [
            a for a in self._alerts.values()
            if a.status == AlertStatus.ACTIVE
        ]

        if severity:
            active = [a for a in active if a.severity == severity]

        return active

    async def detect_drift(
        self,
        reference_data: Dict[str, List[float]],
        current_data: Dict[str, List[float]],
        drift_types: Optional[List[DriftType]] = None
    ) -> List[DriftResult]:
        """Detect drift across features."""
        drift_types = drift_types or list(self._drift_detectors.keys())
        results = []

        for drift_type in drift_types:
            detector = self._drift_detectors.get(drift_type)
            if not detector:
                continue

            feature_scores = {}
            overall_score = 0.0

            for feature, ref_values in reference_data.items():
                cur_values = current_data.get(feature, [])

                if not cur_values:
                    continue

                result = detector.detect(ref_values, cur_values)
                feature_scores[feature] = result.score
                overall_score = max(overall_score, result.score)

            drift_result = DriftResult(
                drift_type=drift_type,
                detected=overall_score > detector._threshold,
                score=overall_score,
                threshold=detector._threshold,
                feature_scores=feature_scores
            )

            results.append(drift_result)
            self._drift_history.append(drift_result)

        return results

    async def update_model_health(
        self,
        model_id: str
    ) -> ModelHealth:
        """Update model health status."""
        latency_p50 = self.get_metric("latency_p50_ms")
        latency_p99 = self.get_metric("latency_p99_ms")
        error_rate = self.get_metric("error_rate")
        request_rate = self.get_metric("request_rate")

        active_alerts = len(self.get_active_alerts())

        drift_detected = any(
            d.detected for d in self._drift_history[-10:]
        ) if self._drift_history else False

        if error_rate > 0.1 or active_alerts > 5:
            status = MonitoringStatus.UNHEALTHY
        elif error_rate > 0.05 or drift_detected or active_alerts > 0:
            status = MonitoringStatus.DEGRADED
        else:
            status = MonitoringStatus.HEALTHY

        health = ModelHealth(
            model_id=model_id,
            status=status,
            latency_p50_ms=latency_p50,
            latency_p99_ms=latency_p99,
            error_rate=error_rate,
            request_rate=request_rate,
            drift_detected=drift_detected,
            active_alerts=active_alerts
        )

        self._model_health[model_id] = health

        return health

    def get_model_health(self, model_id: str) -> Optional[ModelHealth]:
        """Get model health status."""
        return self._model_health.get(model_id)

    def get_drift_history(
        self,
        drift_type: Optional[DriftType] = None,
        limit: int = 100
    ) -> List[DriftResult]:
        """Get drift detection history."""
        history = self._drift_history

        if drift_type:
            history = [d for d in history if d.drift_type == drift_type]

        return history[-limit:]

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "collectors": list(self._collectors.keys()),
            "metrics_count": len(self._metrics),
            "drift_detectors": [d.value for d in self._drift_detectors.keys()],
            "alert_rules": len(self._alert_rules),
            "active_alerts": len(self.get_active_alerts()),
            "total_alerts": len(self._alerts),
            "drift_events": len(self._drift_history),
            "monitored_models": len(self._model_health)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Monitoring Engine."""
    print("=" * 70)
    print("BAEL - MONITORING ENGINE DEMO")
    print("Production Model Monitoring")
    print("=" * 70)
    print()

    engine = MonitoringEngine()

    # 1. Engine Capabilities
    print("1. ENGINE CAPABILITIES:")
    print("-" * 40)

    summary = engine.summary()
    print(f"   Collectors: {summary['collectors']}")
    print(f"   Drift Detectors: {summary['drift_detectors']}")
    print()

    # 2. Record Metrics
    print("2. RECORD METRICS:")
    print("-" * 40)

    for _ in range(100):
        engine.record_latency(random.uniform(10, 100))
        engine.record_request(success=random.random() > 0.05)

    engine.record_metric("custom_metric", 42.5)
    engine.record_metric("custom_metric", 45.0)

    print("   Recorded 100 latency samples")
    print("   Recorded 100 request samples")
    print()

    # 3. Collect Metrics
    print("3. COLLECT METRICS:")
    print("-" * 40)

    metrics = await engine.collect_metrics()

    for metric in metrics[:5]:
        print(f"   {metric.name}: {metric.value:.4f}")
    print()

    # 4. Aggregated Metrics
    print("4. AGGREGATED METRICS:")
    print("-" * 40)

    latency_avg = engine.get_metric("latency_avg_ms", AggregationType.AVG)
    latency_p99 = engine.get_metric("latency_p99_ms", AggregationType.MAX)
    error_rate = engine.get_metric("error_rate", AggregationType.AVG)

    print(f"   Latency (avg): {latency_avg:.2f}ms")
    print(f"   Latency (p99): {latency_p99:.2f}ms")
    print(f"   Error Rate: {error_rate * 100:.2f}%")
    print()

    # 5. Add Alert Rules
    print("5. ADD ALERT RULES:")
    print("-" * 40)

    latency_rule = AlertRule(
        name="High Latency",
        metric_name="latency_p99_ms",
        condition="gt",
        threshold=50.0,
        severity=AlertSeverity.WARNING
    )

    error_rule = AlertRule(
        name="High Error Rate",
        metric_name="error_rate",
        condition="gt",
        threshold=0.1,
        severity=AlertSeverity.ERROR
    )

    engine.add_alert_rule(latency_rule)
    engine.add_alert_rule(error_rule)

    print(f"   Added: {latency_rule.name}")
    print(f"   Added: {error_rule.name}")
    print()

    # 6. Check Alerts
    print("6. CHECK ALERTS:")
    print("-" * 40)

    alerts = await engine.check_alerts()

    if alerts:
        for alert in alerts:
            print(f"   [{alert.severity.value}] {alert.message}")
    else:
        print("   No alerts triggered")
    print()

    # 7. Drift Detection
    print("7. DRIFT DETECTION:")
    print("-" * 40)

    reference_data = {
        "feature_1": [random.gauss(0, 1) for _ in range(100)],
        "feature_2": [random.gauss(5, 2) for _ in range(100)]
    }

    current_data = {
        "feature_1": [random.gauss(0.5, 1) for _ in range(100)],
        "feature_2": [random.gauss(5, 2) for _ in range(100)]
    }

    drift_results = await engine.detect_drift(reference_data, current_data)

    for result in drift_results:
        status = "DETECTED" if result.detected else "OK"
        print(f"   {result.drift_type.value}: {status} (score={result.score:.4f})")
    print()

    # 8. Model Health
    print("8. MODEL HEALTH:")
    print("-" * 40)

    health = await engine.update_model_health("model-prod-v1")

    print(f"   Model: {health.model_id}")
    print(f"   Status: {health.status.value}")
    print(f"   Latency P50: {health.latency_p50_ms:.2f}ms")
    print(f"   Latency P99: {health.latency_p99_ms:.2f}ms")
    print(f"   Error Rate: {health.error_rate * 100:.2f}%")
    print(f"   Drift Detected: {health.drift_detected}")
    print(f"   Active Alerts: {health.active_alerts}")
    print()

    # 9. Alert Management
    print("9. ALERT MANAGEMENT:")
    print("-" * 40)

    active_alerts = engine.get_active_alerts()
    print(f"   Active Alerts: {len(active_alerts)}")

    if active_alerts:
        alert = active_alerts[0]
        engine.acknowledge_alert(alert.alert_id, "operator@bael.ai")
        print(f"   Acknowledged: {alert.name}")

        engine.resolve_alert(alert.alert_id)
        print(f"   Resolved: {alert.name}")
    print()

    # 10. Final Summary
    print("10. FINAL SUMMARY:")
    print("-" * 40)

    final_summary = engine.summary()

    print(f"   Metrics: {final_summary['metrics_count']}")
    print(f"   Alert Rules: {final_summary['alert_rules']}")
    print(f"   Total Alerts: {final_summary['total_alerts']}")
    print(f"   Active Alerts: {final_summary['active_alerts']}")
    print(f"   Drift Events: {final_summary['drift_events']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Monitoring Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
