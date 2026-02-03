#!/usr/bin/env python3
"""
BAEL - Observation Engine
Observation processing and pattern detection for agents.

Features:
- Observation capture and storage
- Pattern detection
- Anomaly detection
- Time series analysis
- Observation aggregation
"""

import asyncio
import hashlib
import json
import math
import re
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ObservationType(Enum):
    """Types of observations."""
    METRIC = "metric"
    EVENT = "event"
    LOG = "log"
    TRACE = "trace"
    STATE = "state"


class PatternType(Enum):
    """Pattern types."""
    TREND = "trend"
    CYCLE = "cycle"
    SPIKE = "spike"
    ANOMALY = "anomaly"
    STEADY = "steady"


class TrendDirection(Enum):
    """Trend directions."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    UNKNOWN = "unknown"


class AggregationType(Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    LAST = "last"


class AnomalyType(Enum):
    """Anomaly types."""
    THRESHOLD = "threshold"
    DEVIATION = "deviation"
    RATE_CHANGE = "rate_change"
    MISSING = "missing"


class Severity(Enum):
    """Severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Observation:
    """An observation."""
    obs_id: str = ""
    obs_type: ObservationType = ObservationType.METRIC
    name: str = ""
    value: Any = None
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""

    def __post_init__(self):
        if not self.obs_id:
            self.obs_id = str(uuid.uuid4())[:8]


@dataclass
class Pattern:
    """A detected pattern."""
    pattern_id: str = ""
    pattern_type: PatternType = PatternType.STEADY
    name: str = ""
    confidence: float = 0.0
    data_points: int = 0
    detected_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.pattern_id:
            self.pattern_id = str(uuid.uuid4())[:8]


@dataclass
class Trend:
    """A trend analysis."""
    direction: TrendDirection = TrendDirection.UNKNOWN
    slope: float = 0.0
    intercept: float = 0.0
    r_squared: float = 0.0
    data_points: int = 0


@dataclass
class Anomaly:
    """A detected anomaly."""
    anomaly_id: str = ""
    anomaly_type: AnomalyType = AnomalyType.THRESHOLD
    observation: Optional[Observation] = None
    severity: Severity = Severity.MEDIUM
    expected_value: Any = None
    actual_value: Any = None
    deviation: float = 0.0
    detected_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.anomaly_id:
            self.anomaly_id = str(uuid.uuid4())[:8]


@dataclass
class AggregateResult:
    """Aggregation result."""
    name: str = ""
    agg_type: AggregationType = AggregationType.SUM
    value: float = 0.0
    count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class ObservationConfig:
    """Observation engine configuration."""
    max_observations: int = 10000
    default_window: int = 3600
    anomaly_threshold: float = 2.0
    enable_patterns: bool = True


# =============================================================================
# OBSERVATION STORE
# =============================================================================

class ObservationStore:
    """Store and retrieve observations."""

    def __init__(self, max_size: int = 10000):
        self._observations: deque = deque(maxlen=max_size)
        self._by_name: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_size))
        self._by_type: Dict[ObservationType, deque] = defaultdict(lambda: deque(maxlen=max_size))

    def add(self, observation: Observation) -> None:
        """Add observation."""
        self._observations.append(observation)
        self._by_name[observation.name].append(observation)
        self._by_type[observation.obs_type].append(observation)

    def get_by_name(
        self,
        name: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[Observation]:
        """Get observations by name."""
        observations = list(self._by_name.get(name, []))

        if since:
            observations = [o for o in observations if o.timestamp >= since]
        if until:
            observations = [o for o in observations if o.timestamp <= until]

        return observations

    def get_by_type(
        self,
        obs_type: ObservationType,
        since: Optional[datetime] = None
    ) -> List[Observation]:
        """Get observations by type."""
        observations = list(self._by_type.get(obs_type, []))

        if since:
            observations = [o for o in observations if o.timestamp >= since]

        return observations

    def get_recent(self, count: int = 100) -> List[Observation]:
        """Get recent observations."""
        return list(self._observations)[-count:]

    def get_names(self) -> Set[str]:
        """Get all observation names."""
        return set(self._by_name.keys())

    def count(self) -> int:
        """Count observations."""
        return len(self._observations)

    def count_by_name(self, name: str) -> int:
        """Count observations by name."""
        return len(self._by_name.get(name, []))

    def clear(self) -> int:
        """Clear all observations."""
        count = len(self._observations)
        self._observations.clear()
        self._by_name.clear()
        self._by_type.clear()
        return count


# =============================================================================
# STATISTICS CALCULATOR
# =============================================================================

class StatisticsCalculator:
    """Calculate statistics on observations."""

    def calculate(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistics."""
        if not values:
            return {}

        result = {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
        }

        if len(values) >= 2:
            result["stdev"] = statistics.stdev(values)
            result["variance"] = statistics.variance(values)

        if len(values) >= 1:
            result["median"] = statistics.median(values)

        return result

    def percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return sorted_values[int(k)]

        return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)


# =============================================================================
# TREND ANALYZER
# =============================================================================

class TrendAnalyzer:
    """Analyze trends in observations."""

    def analyze(self, values: List[float]) -> Trend:
        """Analyze trend using linear regression."""
        n = len(values)

        if n < 2:
            return Trend(direction=TrendDirection.UNKNOWN, data_points=n)

        x = list(range(n))

        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return Trend(
                direction=TrendDirection.STABLE,
                slope=0.0,
                intercept=y_mean,
                data_points=n
            )

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        ss_res = sum((values[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        if abs(slope) < 0.01:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.UP
        else:
            direction = TrendDirection.DOWN

        return Trend(
            direction=direction,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            data_points=n
        )


# =============================================================================
# ANOMALY DETECTOR
# =============================================================================

class AnomalyDetector:
    """Detect anomalies in observations."""

    def __init__(self, threshold: float = 2.0):
        self._threshold = threshold
        self._stats_calc = StatisticsCalculator()

    def detect_threshold(
        self,
        observation: Observation,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Optional[Anomaly]:
        """Detect threshold anomalies."""
        if not isinstance(observation.value, (int, float)):
            return None

        value = float(observation.value)

        if min_value is not None and value < min_value:
            return Anomaly(
                anomaly_type=AnomalyType.THRESHOLD,
                observation=observation,
                severity=Severity.MEDIUM,
                expected_value=f">= {min_value}",
                actual_value=value,
                deviation=min_value - value
            )

        if max_value is not None and value > max_value:
            return Anomaly(
                anomaly_type=AnomalyType.THRESHOLD,
                observation=observation,
                severity=Severity.MEDIUM,
                expected_value=f"<= {max_value}",
                actual_value=value,
                deviation=value - max_value
            )

        return None

    def detect_deviation(
        self,
        observation: Observation,
        historical: List[float]
    ) -> Optional[Anomaly]:
        """Detect deviation anomalies."""
        if not isinstance(observation.value, (int, float)):
            return None

        if len(historical) < 3:
            return None

        stats = self._stats_calc.calculate(historical)
        mean = stats["mean"]
        stdev = stats.get("stdev", 0)

        if stdev == 0:
            return None

        value = float(observation.value)
        z_score = abs(value - mean) / stdev

        if z_score > self._threshold:
            severity = Severity.LOW
            if z_score > self._threshold * 2:
                severity = Severity.MEDIUM
            if z_score > self._threshold * 3:
                severity = Severity.HIGH
            if z_score > self._threshold * 4:
                severity = Severity.CRITICAL

            return Anomaly(
                anomaly_type=AnomalyType.DEVIATION,
                observation=observation,
                severity=severity,
                expected_value=mean,
                actual_value=value,
                deviation=z_score
            )

        return None

    def detect_rate_change(
        self,
        current: float,
        previous: float,
        max_change_rate: float = 0.5
    ) -> Optional[Anomaly]:
        """Detect rate of change anomalies."""
        if previous == 0:
            return None

        change_rate = abs(current - previous) / abs(previous)

        if change_rate > max_change_rate:
            severity = Severity.MEDIUM
            if change_rate > max_change_rate * 2:
                severity = Severity.HIGH

            return Anomaly(
                anomaly_type=AnomalyType.RATE_CHANGE,
                severity=severity,
                expected_value=f"<= {max_change_rate * 100}% change",
                actual_value=f"{change_rate * 100:.1f}% change",
                deviation=change_rate
            )

        return None


# =============================================================================
# PATTERN DETECTOR
# =============================================================================

class PatternDetector:
    """Detect patterns in observations."""

    def __init__(self):
        self._trend_analyzer = TrendAnalyzer()
        self._stats_calc = StatisticsCalculator()

    def detect(self, name: str, values: List[float]) -> List[Pattern]:
        """Detect patterns in values."""
        patterns = []

        if len(values) < 5:
            return patterns

        trend_pattern = self._detect_trend(name, values)
        if trend_pattern:
            patterns.append(trend_pattern)

        spike_pattern = self._detect_spike(name, values)
        if spike_pattern:
            patterns.append(spike_pattern)

        steady_pattern = self._detect_steady(name, values)
        if steady_pattern:
            patterns.append(steady_pattern)

        return patterns

    def _detect_trend(self, name: str, values: List[float]) -> Optional[Pattern]:
        """Detect trend pattern."""
        trend = self._trend_analyzer.analyze(values)

        if trend.direction in (TrendDirection.UP, TrendDirection.DOWN):
            if trend.r_squared > 0.7:
                return Pattern(
                    pattern_type=PatternType.TREND,
                    name=f"{name}_trend_{trend.direction.value}",
                    confidence=trend.r_squared,
                    data_points=len(values),
                    metadata={
                        "direction": trend.direction.value,
                        "slope": trend.slope,
                        "r_squared": trend.r_squared
                    }
                )

        return None

    def _detect_spike(self, name: str, values: List[float]) -> Optional[Pattern]:
        """Detect spike pattern."""
        stats = self._stats_calc.calculate(values)

        if "stdev" not in stats or stats["stdev"] == 0:
            return None

        mean = stats["mean"]
        stdev = stats["stdev"]
        max_val = stats["max"]

        z_score = (max_val - mean) / stdev

        if z_score > 3:
            return Pattern(
                pattern_type=PatternType.SPIKE,
                name=f"{name}_spike",
                confidence=min(z_score / 5, 1.0),
                data_points=len(values),
                metadata={
                    "max_value": max_val,
                    "z_score": z_score,
                    "mean": mean
                }
            )

        return None

    def _detect_steady(self, name: str, values: List[float]) -> Optional[Pattern]:
        """Detect steady state pattern."""
        stats = self._stats_calc.calculate(values)

        if "stdev" not in stats:
            return None

        mean = stats["mean"]
        stdev = stats["stdev"]

        if mean == 0:
            return None

        cv = stdev / abs(mean)

        if cv < 0.1:
            return Pattern(
                pattern_type=PatternType.STEADY,
                name=f"{name}_steady",
                confidence=max(0, 1 - cv * 10),
                data_points=len(values),
                metadata={
                    "mean": mean,
                    "stdev": stdev,
                    "cv": cv
                }
            )

        return None


# =============================================================================
# AGGREGATOR
# =============================================================================

class Aggregator:
    """Aggregate observations."""

    def aggregate(
        self,
        observations: List[Observation],
        agg_type: AggregationType
    ) -> AggregateResult:
        """Aggregate observation values."""
        if not observations:
            return AggregateResult(agg_type=agg_type)

        values = [float(o.value) for o in observations if isinstance(o.value, (int, float))]

        if not values:
            return AggregateResult(
                name=observations[0].name if observations else "",
                agg_type=agg_type,
                count=0
            )

        if agg_type == AggregationType.SUM:
            value = sum(values)
        elif agg_type == AggregationType.AVG:
            value = sum(values) / len(values)
        elif agg_type == AggregationType.MIN:
            value = min(values)
        elif agg_type == AggregationType.MAX:
            value = max(values)
        elif agg_type == AggregationType.COUNT:
            value = len(values)
        elif agg_type == AggregationType.LAST:
            value = values[-1]
        else:
            value = 0.0

        timestamps = [o.timestamp for o in observations]

        return AggregateResult(
            name=observations[0].name,
            agg_type=agg_type,
            value=value,
            count=len(values),
            start_time=min(timestamps),
            end_time=max(timestamps)
        )


# =============================================================================
# OBSERVATION ENGINE
# =============================================================================

class ObservationEngine:
    """
    Observation Engine for BAEL.

    Observation processing and pattern detection.
    """

    def __init__(self, config: Optional[ObservationConfig] = None):
        self._config = config or ObservationConfig()

        self._store = ObservationStore(self._config.max_observations)
        self._stats_calc = StatisticsCalculator()
        self._trend_analyzer = TrendAnalyzer()
        self._anomaly_detector = AnomalyDetector(self._config.anomaly_threshold)
        self._pattern_detector = PatternDetector()
        self._aggregator = Aggregator()

        self._anomalies: List[Anomaly] = []
        self._patterns: Dict[str, List[Pattern]] = defaultdict(list)

    # ----- Observation Operations -----

    def observe(
        self,
        name: str,
        value: Any,
        obs_type: ObservationType = ObservationType.METRIC,
        tags: Optional[Dict[str, str]] = None,
        source: str = ""
    ) -> Observation:
        """Record an observation."""
        observation = Observation(
            obs_type=obs_type,
            name=name,
            value=value,
            tags=tags or {},
            source=source
        )

        self._store.add(observation)

        if obs_type == ObservationType.METRIC and isinstance(value, (int, float)):
            self._check_for_anomalies(observation)

        return observation

    def metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> Observation:
        """Record a metric observation."""
        return self.observe(name, value, ObservationType.METRIC, tags)

    def event(
        self,
        name: str,
        data: Dict[str, Any],
        tags: Optional[Dict[str, str]] = None
    ) -> Observation:
        """Record an event observation."""
        return self.observe(name, data, ObservationType.EVENT, tags)

    def log(
        self,
        name: str,
        message: str,
        tags: Optional[Dict[str, str]] = None
    ) -> Observation:
        """Record a log observation."""
        return self.observe(name, message, ObservationType.LOG, tags)

    def state(
        self,
        name: str,
        state: Any,
        tags: Optional[Dict[str, str]] = None
    ) -> Observation:
        """Record a state observation."""
        return self.observe(name, state, ObservationType.STATE, tags)

    # ----- Query Operations -----

    def get_observations(
        self,
        name: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[Observation]:
        """Get observations by name."""
        return self._store.get_by_name(name, since, until)

    def get_values(self, name: str, since: Optional[datetime] = None) -> List[float]:
        """Get numeric values for a metric."""
        observations = self._store.get_by_name(name, since)
        return [float(o.value) for o in observations if isinstance(o.value, (int, float))]

    def get_recent(self, count: int = 100) -> List[Observation]:
        """Get recent observations."""
        return self._store.get_recent(count)

    def get_names(self) -> Set[str]:
        """Get all observation names."""
        return self._store.get_names()

    # ----- Statistics -----

    def stats(self, name: str, since: Optional[datetime] = None) -> Dict[str, float]:
        """Get statistics for a metric."""
        values = self.get_values(name, since)
        return self._stats_calc.calculate(values)

    def percentile(
        self,
        name: str,
        p: float,
        since: Optional[datetime] = None
    ) -> float:
        """Get percentile for a metric."""
        values = self.get_values(name, since)
        return self._stats_calc.percentile(values, p)

    # ----- Trend Analysis -----

    def trend(self, name: str, since: Optional[datetime] = None) -> Trend:
        """Analyze trend for a metric."""
        values = self.get_values(name, since)
        return self._trend_analyzer.analyze(values)

    # ----- Anomaly Detection -----

    def _check_for_anomalies(self, observation: Observation) -> None:
        """Check observation for anomalies."""
        historical = self.get_values(observation.name)

        if len(historical) > 10:
            historical = historical[:-1]

            anomaly = self._anomaly_detector.detect_deviation(observation, historical)

            if anomaly:
                self._anomalies.append(anomaly)

    def check_threshold(
        self,
        name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> List[Anomaly]:
        """Check for threshold anomalies."""
        anomalies = []

        for obs in self._store.get_by_name(name):
            anomaly = self._anomaly_detector.detect_threshold(obs, min_value, max_value)
            if anomaly:
                anomalies.append(anomaly)

        return anomalies

    def get_anomalies(
        self,
        severity: Optional[Severity] = None
    ) -> List[Anomaly]:
        """Get detected anomalies."""
        if severity:
            return [a for a in self._anomalies if a.severity == severity]
        return list(self._anomalies)

    # ----- Pattern Detection -----

    def detect_patterns(self, name: str) -> List[Pattern]:
        """Detect patterns for a metric."""
        values = self.get_values(name)
        patterns = self._pattern_detector.detect(name, values)

        self._patterns[name] = patterns

        return patterns

    def get_patterns(self, name: Optional[str] = None) -> List[Pattern]:
        """Get detected patterns."""
        if name:
            return self._patterns.get(name, [])

        all_patterns = []
        for patterns in self._patterns.values():
            all_patterns.extend(patterns)
        return all_patterns

    # ----- Aggregation -----

    def aggregate(
        self,
        name: str,
        agg_type: AggregationType,
        since: Optional[datetime] = None
    ) -> AggregateResult:
        """Aggregate observations."""
        observations = self._store.get_by_name(name, since)
        return self._aggregator.aggregate(observations, agg_type)

    def sum(self, name: str, since: Optional[datetime] = None) -> float:
        """Sum values."""
        return self.aggregate(name, AggregationType.SUM, since).value

    def avg(self, name: str, since: Optional[datetime] = None) -> float:
        """Average values."""
        return self.aggregate(name, AggregationType.AVG, since).value

    def min(self, name: str, since: Optional[datetime] = None) -> float:
        """Minimum value."""
        return self.aggregate(name, AggregationType.MIN, since).value

    def max(self, name: str, since: Optional[datetime] = None) -> float:
        """Maximum value."""
        return self.aggregate(name, AggregationType.MAX, since).value

    def count(self, name: str, since: Optional[datetime] = None) -> int:
        """Count values."""
        return int(self.aggregate(name, AggregationType.COUNT, since).value)

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_observations": self._store.count(),
            "unique_names": len(self._store.get_names()),
            "anomalies": len(self._anomalies),
            "patterns": sum(len(p) for p in self._patterns.values())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Observation Engine."""
    print("=" * 70)
    print("BAEL - OBSERVATION ENGINE DEMO")
    print("Observation Processing and Pattern Detection")
    print("=" * 70)
    print()

    engine = ObservationEngine()

    # 1. Record Observations
    print("1. RECORD OBSERVATIONS:")
    print("-" * 40)

    import random

    for i in range(100):
        value = 50 + random.gauss(0, 5)
        engine.metric("cpu_usage", value, {"host": "server1"})
        await asyncio.sleep(0.001)

    print(f"   Recorded 100 CPU usage observations")
    print(f"   Total observations: {engine._store.count()}")
    print()

    # 2. Add Trend Data
    print("2. ADD TREND DATA:")
    print("-" * 40)

    for i in range(50):
        value = 20 + i * 0.5 + random.gauss(0, 2)
        engine.metric("memory_usage", value, {"host": "server1"})

    print(f"   Recorded 50 memory observations with upward trend")
    print()

    # 3. Add Spike Data
    print("3. ADD SPIKE DATA:")
    print("-" * 40)

    for i in range(30):
        if i == 15:
            value = 200
        else:
            value = 30 + random.gauss(0, 3)
        engine.metric("request_count", value)

    print(f"   Recorded 30 request observations with spike")
    print()

    # 4. Statistics
    print("4. STATISTICS:")
    print("-" * 40)

    cpu_stats = engine.stats("cpu_usage")
    print(f"   CPU Usage Stats:")
    print(f"   - Count: {cpu_stats['count']}")
    print(f"   - Mean: {cpu_stats['mean']:.2f}")
    print(f"   - Min: {cpu_stats['min']:.2f}")
    print(f"   - Max: {cpu_stats['max']:.2f}")
    print(f"   - StdDev: {cpu_stats.get('stdev', 0):.2f}")
    print()

    # 5. Percentiles
    print("5. PERCENTILES:")
    print("-" * 40)

    p50 = engine.percentile("cpu_usage", 50)
    p90 = engine.percentile("cpu_usage", 90)
    p99 = engine.percentile("cpu_usage", 99)

    print(f"   CPU Usage Percentiles:")
    print(f"   - P50: {p50:.2f}")
    print(f"   - P90: {p90:.2f}")
    print(f"   - P99: {p99:.2f}")
    print()

    # 6. Trend Analysis
    print("6. TREND ANALYSIS:")
    print("-" * 40)

    cpu_trend = engine.trend("cpu_usage")
    mem_trend = engine.trend("memory_usage")

    print(f"   CPU Trend:")
    print(f"   - Direction: {cpu_trend.direction.value}")
    print(f"   - Slope: {cpu_trend.slope:.4f}")
    print(f"   - R²: {cpu_trend.r_squared:.4f}")

    print(f"   Memory Trend:")
    print(f"   - Direction: {mem_trend.direction.value}")
    print(f"   - Slope: {mem_trend.slope:.4f}")
    print(f"   - R²: {mem_trend.r_squared:.4f}")
    print()

    # 7. Pattern Detection
    print("7. PATTERN DETECTION:")
    print("-" * 40)

    cpu_patterns = engine.detect_patterns("cpu_usage")
    mem_patterns = engine.detect_patterns("memory_usage")
    req_patterns = engine.detect_patterns("request_count")

    print(f"   CPU Patterns: {len(cpu_patterns)}")
    for p in cpu_patterns:
        print(f"   - {p.pattern_type.value}: confidence={p.confidence:.2f}")

    print(f"   Memory Patterns: {len(mem_patterns)}")
    for p in mem_patterns:
        print(f"   - {p.pattern_type.value}: confidence={p.confidence:.2f}")

    print(f"   Request Patterns: {len(req_patterns)}")
    for p in req_patterns:
        print(f"   - {p.pattern_type.value}: confidence={p.confidence:.2f}")
    print()

    # 8. Anomaly Detection
    print("8. ANOMALY DETECTION:")
    print("-" * 40)

    anomalies = engine.get_anomalies()

    print(f"   Detected {len(anomalies)} anomalies")
    for a in anomalies[:3]:
        print(f"   - Type: {a.anomaly_type.value}, Severity: {a.severity.value}")
        print(f"     Deviation: {a.deviation:.2f}")
    print()

    # 9. Threshold Checking
    print("9. THRESHOLD CHECKING:")
    print("-" * 40)

    threshold_anomalies = engine.check_threshold("cpu_usage", min_value=40, max_value=60)

    print(f"   CPU threshold anomalies (40-60 range): {len(threshold_anomalies)}")
    print()

    # 10. Aggregations
    print("10. AGGREGATIONS:")
    print("-" * 40)

    print(f"   CPU Usage:")
    print(f"   - Sum: {engine.sum('cpu_usage'):.2f}")
    print(f"   - Avg: {engine.avg('cpu_usage'):.2f}")
    print(f"   - Min: {engine.min('cpu_usage'):.2f}")
    print(f"   - Max: {engine.max('cpu_usage'):.2f}")
    print(f"   - Count: {engine.count('cpu_usage')}")
    print()

    # 11. Event Observations
    print("11. EVENT OBSERVATIONS:")
    print("-" * 40)

    engine.event("user_login", {"user_id": "123", "ip": "192.168.1.1"})
    engine.event("user_login", {"user_id": "456", "ip": "192.168.1.2"})

    events = engine.get_observations("user_login")
    print(f"   Recorded {len(events)} login events")
    for e in events:
        print(f"   - User: {e.value.get('user_id')}, IP: {e.value.get('ip')}")
    print()

    # 12. Log Observations
    print("12. LOG OBSERVATIONS:")
    print("-" * 40)

    engine.log("app_logs", "Application started")
    engine.log("app_logs", "Connected to database")
    engine.log("app_logs", "Ready to serve requests")

    logs = engine.get_observations("app_logs")
    print(f"   Recorded {len(logs)} log messages")
    for l in logs:
        print(f"   - {l.value}")
    print()

    # 13. State Observations
    print("13. STATE OBSERVATIONS:")
    print("-" * 40)

    engine.state("server_status", "starting")
    engine.state("server_status", "running")
    engine.state("server_status", "healthy")

    states = engine.get_observations("server_status")
    print(f"   State history:")
    for s in states:
        print(f"   - {s.value} at {s.timestamp.strftime('%H:%M:%S')}")
    print()

    # 14. Metric Names
    print("14. METRIC NAMES:")
    print("-" * 40)

    names = engine.get_names()
    print(f"   Tracked metrics: {len(names)}")
    for name in names:
        print(f"   - {name}: {engine.count(name)} observations")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Observation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
