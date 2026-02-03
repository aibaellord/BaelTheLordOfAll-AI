#!/usr/bin/env python3
"""
BAEL - Time Series Manager
Comprehensive time series data management system.

Features:
- Time series storage and retrieval
- Data aggregation (min, max, avg, sum, count)
- Rolling windows
- Downsampling
- Gap filling
- Anomaly detection
- Trend analysis
- Forecasting
- Multi-series support
- Query optimization
"""

import asyncio
import bisect
import hashlib
import heapq
import json
import logging
import math
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AggregationType(Enum):
    """Aggregation types."""
    MIN = "min"
    MAX = "max"
    AVG = "avg"
    SUM = "sum"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"
    MEDIAN = "median"
    STDDEV = "stddev"
    VARIANCE = "variance"


class InterpolationType(Enum):
    """Interpolation types for gap filling."""
    LINEAR = "linear"
    PREVIOUS = "previous"
    NEXT = "next"
    ZERO = "zero"
    NONE = "none"


class ResolutionUnit(Enum):
    """Time resolution units."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TrendDirection(Enum):
    """Trend direction."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    UNKNOWN = "unknown"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DataPoint:
    """Time series data point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def epoch(self) -> float:
        """Get timestamp as epoch."""
        return self.timestamp.timestamp()


@dataclass
class TimeRange:
    """Time range."""
    start: datetime
    end: datetime

    @property
    def duration(self) -> timedelta:
        """Get duration."""
        return self.end - self.start

    def contains(self, dt: datetime) -> bool:
        """Check if datetime is in range."""
        return self.start <= dt <= self.end


@dataclass
class Resolution:
    """Time resolution."""
    value: int
    unit: ResolutionUnit

    def to_seconds(self) -> int:
        """Convert to seconds."""
        multipliers = {
            ResolutionUnit.SECOND: 1,
            ResolutionUnit.MINUTE: 60,
            ResolutionUnit.HOUR: 3600,
            ResolutionUnit.DAY: 86400,
            ResolutionUnit.WEEK: 604800,
            ResolutionUnit.MONTH: 2592000  # 30 days
        }

        return self.value * multipliers[self.unit]

    def to_timedelta(self) -> timedelta:
        """Convert to timedelta."""
        return timedelta(seconds=self.to_seconds())


@dataclass
class SeriesMetadata:
    """Time series metadata."""
    name: str
    description: str = ""
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    retention_days: int = 365
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AggregationResult:
    """Aggregation result."""
    timestamp: datetime
    value: float
    count: int
    min_value: float
    max_value: float


@dataclass
class TrendInfo:
    """Trend information."""
    direction: TrendDirection
    slope: float
    strength: float  # 0-1, correlation coefficient
    change_percent: float


@dataclass
class AnomalyResult:
    """Anomaly detection result."""
    timestamp: datetime
    value: float
    expected: float
    deviation: float
    is_anomaly: bool
    score: float  # 0-1, anomaly score


@dataclass
class ForecastResult:
    """Forecast result."""
    timestamp: datetime
    predicted: float
    lower_bound: float
    upper_bound: float
    confidence: float


# =============================================================================
# TIME SERIES STORAGE
# =============================================================================

class TimeSeriesStorage(ABC):
    """Abstract time series storage."""

    @abstractmethod
    def write(self, series: str, point: DataPoint) -> None:
        """Write data point."""
        pass

    @abstractmethod
    def read(
        self,
        series: str,
        time_range: TimeRange
    ) -> List[DataPoint]:
        """Read data points in range."""
        pass

    @abstractmethod
    def delete(self, series: str, time_range: TimeRange) -> int:
        """Delete data points in range."""
        pass


class MemoryStorage(TimeSeriesStorage):
    """In-memory time series storage."""

    def __init__(self):
        self._data: Dict[str, List[DataPoint]] = defaultdict(list)
        self._indexes: Dict[str, List[float]] = defaultdict(list)

    def write(self, series: str, point: DataPoint) -> None:
        """Write data point."""
        epoch = point.epoch

        # Binary search insert position
        idx = bisect.bisect_left(self._indexes[series], epoch)

        self._data[series].insert(idx, point)
        self._indexes[series].insert(idx, epoch)

    def read(
        self,
        series: str,
        time_range: TimeRange
    ) -> List[DataPoint]:
        """Read data points in range."""
        if series not in self._data:
            return []

        start_epoch = time_range.start.timestamp()
        end_epoch = time_range.end.timestamp()

        # Binary search for range
        start_idx = bisect.bisect_left(self._indexes[series], start_epoch)
        end_idx = bisect.bisect_right(self._indexes[series], end_epoch)

        return self._data[series][start_idx:end_idx]

    def delete(self, series: str, time_range: TimeRange) -> int:
        """Delete data points in range."""
        if series not in self._data:
            return 0

        start_epoch = time_range.start.timestamp()
        end_epoch = time_range.end.timestamp()

        start_idx = bisect.bisect_left(self._indexes[series], start_epoch)
        end_idx = bisect.bisect_right(self._indexes[series], end_epoch)

        count = end_idx - start_idx

        del self._data[series][start_idx:end_idx]
        del self._indexes[series][start_idx:end_idx]

        return count

    def get_series(self) -> List[str]:
        """Get all series names."""
        return list(self._data.keys())

    def get_count(self, series: str) -> int:
        """Get point count for series."""
        return len(self._data.get(series, []))


# =============================================================================
# AGGREGATION ENGINE
# =============================================================================

class AggregationEngine:
    """Time series aggregation engine."""

    def __init__(self):
        self._aggregators: Dict[AggregationType, Callable[[List[float]], float]] = {
            AggregationType.MIN: min,
            AggregationType.MAX: max,
            AggregationType.AVG: statistics.mean,
            AggregationType.SUM: sum,
            AggregationType.COUNT: lambda x: float(len(x)),
            AggregationType.FIRST: lambda x: x[0] if x else 0.0,
            AggregationType.LAST: lambda x: x[-1] if x else 0.0,
            AggregationType.MEDIAN: statistics.median,
            AggregationType.STDDEV: lambda x: statistics.stdev(x) if len(x) > 1 else 0.0,
            AggregationType.VARIANCE: lambda x: statistics.variance(x) if len(x) > 1 else 0.0
        }

    def aggregate(
        self,
        points: List[DataPoint],
        resolution: Resolution,
        aggregation: AggregationType = AggregationType.AVG
    ) -> List[AggregationResult]:
        """Aggregate data points by resolution."""
        if not points:
            return []

        bucket_seconds = resolution.to_seconds()

        # Group points into buckets
        buckets: Dict[int, List[DataPoint]] = defaultdict(list)

        for point in points:
            bucket_key = int(point.epoch // bucket_seconds)
            buckets[bucket_key].append(point)

        # Aggregate each bucket
        results = []
        aggregator = self._aggregators[aggregation]

        for bucket_key in sorted(buckets.keys()):
            bucket_points = buckets[bucket_key]
            values = [p.value for p in bucket_points]

            results.append(AggregationResult(
                timestamp=datetime.fromtimestamp(bucket_key * bucket_seconds),
                value=aggregator(values),
                count=len(values),
                min_value=min(values),
                max_value=max(values)
            ))

        return results

    def downsample(
        self,
        points: List[DataPoint],
        target_points: int,
        aggregation: AggregationType = AggregationType.AVG
    ) -> List[DataPoint]:
        """Downsample to target number of points."""
        if len(points) <= target_points:
            return points

        # Calculate bucket size
        time_range = points[-1].epoch - points[0].epoch
        bucket_seconds = time_range / target_points

        resolution = Resolution(int(bucket_seconds), ResolutionUnit.SECOND)

        aggregated = self.aggregate(points, resolution, aggregation)

        return [
            DataPoint(timestamp=r.timestamp, value=r.value)
            for r in aggregated
        ]

    def rolling_window(
        self,
        points: List[DataPoint],
        window_size: int,
        aggregation: AggregationType = AggregationType.AVG
    ) -> List[DataPoint]:
        """Apply rolling window aggregation."""
        if len(points) < window_size:
            return []

        results = []
        aggregator = self._aggregators[aggregation]

        for i in range(window_size - 1, len(points)):
            window = points[i - window_size + 1:i + 1]
            values = [p.value for p in window]

            results.append(DataPoint(
                timestamp=points[i].timestamp,
                value=aggregator(values)
            ))

        return results


# =============================================================================
# GAP FILLER
# =============================================================================

class GapFiller:
    """Time series gap filler."""

    def fill_gaps(
        self,
        points: List[DataPoint],
        expected_interval: timedelta,
        method: InterpolationType = InterpolationType.LINEAR
    ) -> List[DataPoint]:
        """Fill gaps in time series."""
        if len(points) < 2:
            return points

        filled = []
        interval_seconds = expected_interval.total_seconds()

        for i in range(len(points) - 1):
            current = points[i]
            next_point = points[i + 1]

            filled.append(current)

            # Check for gap
            gap = next_point.epoch - current.epoch
            expected_points = int(gap / interval_seconds) - 1

            if expected_points > 0:
                # Fill gap
                for j in range(1, expected_points + 1):
                    fill_time = datetime.fromtimestamp(
                        current.epoch + j * interval_seconds
                    )

                    fill_value = self._interpolate(
                        current.value,
                        next_point.value,
                        j / (expected_points + 1),
                        method
                    )

                    filled.append(DataPoint(
                        timestamp=fill_time,
                        value=fill_value
                    ))

        filled.append(points[-1])

        return filled

    def _interpolate(
        self,
        v1: float,
        v2: float,
        t: float,
        method: InterpolationType
    ) -> float:
        """Interpolate value."""
        if method == InterpolationType.LINEAR:
            return v1 + (v2 - v1) * t

        elif method == InterpolationType.PREVIOUS:
            return v1

        elif method == InterpolationType.NEXT:
            return v2

        elif method == InterpolationType.ZERO:
            return 0.0

        else:
            return float('nan')


# =============================================================================
# TREND ANALYZER
# =============================================================================

class TrendAnalyzer:
    """Time series trend analyzer."""

    def analyze_trend(
        self,
        points: List[DataPoint],
        min_correlation: float = 0.5
    ) -> TrendInfo:
        """Analyze trend in time series."""
        if len(points) < 2:
            return TrendInfo(
                direction=TrendDirection.UNKNOWN,
                slope=0.0,
                strength=0.0,
                change_percent=0.0
            )

        # Calculate linear regression
        n = len(points)
        x = [i for i in range(n)]
        y = [p.value for p in points]

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        denominator_y = sum((y[i] - mean_y) ** 2 for i in range(n))

        if denominator_x == 0 or denominator_y == 0:
            return TrendInfo(
                direction=TrendDirection.STABLE,
                slope=0.0,
                strength=0.0,
                change_percent=0.0
            )

        slope = numerator / denominator_x
        correlation = numerator / math.sqrt(denominator_x * denominator_y)

        # Calculate change percent
        first_value = points[0].value
        last_value = points[-1].value

        if first_value != 0:
            change_percent = ((last_value - first_value) / abs(first_value)) * 100
        else:
            change_percent = 0.0

        # Determine direction
        if abs(correlation) < min_correlation:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.UP
        else:
            direction = TrendDirection.DOWN

        return TrendInfo(
            direction=direction,
            slope=slope,
            strength=abs(correlation),
            change_percent=change_percent
        )


# =============================================================================
# ANOMALY DETECTOR
# =============================================================================

class AnomalyDetector:
    """Time series anomaly detector."""

    def __init__(self, sensitivity: float = 2.0):
        self.sensitivity = sensitivity

    def detect(
        self,
        points: List[DataPoint],
        window_size: int = 10
    ) -> List[AnomalyResult]:
        """Detect anomalies using z-score method."""
        if len(points) < window_size:
            return []

        results = []

        for i in range(window_size, len(points)):
            window = points[i - window_size:i]
            values = [p.value for p in window]

            mean = statistics.mean(values)
            std = statistics.stdev(values) if len(values) > 1 else 0

            current = points[i]

            if std == 0:
                z_score = 0
                is_anomaly = False
            else:
                z_score = abs(current.value - mean) / std
                is_anomaly = z_score > self.sensitivity

            results.append(AnomalyResult(
                timestamp=current.timestamp,
                value=current.value,
                expected=mean,
                deviation=current.value - mean,
                is_anomaly=is_anomaly,
                score=min(1.0, z_score / (self.sensitivity * 2))
            ))

        return results

    def detect_iqr(
        self,
        points: List[DataPoint],
        multiplier: float = 1.5
    ) -> List[AnomalyResult]:
        """Detect anomalies using IQR method."""
        if len(points) < 4:
            return []

        values = sorted([p.value for p in points])
        n = len(values)

        q1 = values[n // 4]
        q3 = values[3 * n // 4]
        iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        median = statistics.median(values)

        results = []

        for point in points:
            is_anomaly = point.value < lower_bound or point.value > upper_bound
            deviation = abs(point.value - median)

            if iqr > 0:
                score = min(1.0, deviation / (2 * iqr))
            else:
                score = 0.0

            results.append(AnomalyResult(
                timestamp=point.timestamp,
                value=point.value,
                expected=median,
                deviation=point.value - median,
                is_anomaly=is_anomaly,
                score=score
            ))

        return results


# =============================================================================
# FORECASTER
# =============================================================================

class Forecaster:
    """Simple time series forecaster."""

    def forecast_linear(
        self,
        points: List[DataPoint],
        horizon: int,
        interval: timedelta
    ) -> List[ForecastResult]:
        """Forecast using linear regression."""
        if len(points) < 2:
            return []

        # Calculate linear regression
        n = len(points)
        x = [i for i in range(n)]
        y = [p.value for p in points]

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
            intercept = mean_y
        else:
            slope = numerator / denominator
            intercept = mean_y - slope * mean_x

        # Calculate prediction error
        predictions = [slope * i + intercept for i in x]
        errors = [abs(y[i] - predictions[i]) for i in range(n)]
        mean_error = sum(errors) / n

        # Generate forecasts
        results = []
        last_time = points[-1].timestamp

        for i in range(1, horizon + 1):
            predicted = slope * (n - 1 + i) + intercept
            timestamp = last_time + interval * i

            # Confidence decreases with horizon
            confidence = max(0.5, 1.0 - (i * 0.05))
            margin = mean_error * (1 + i * 0.1)

            results.append(ForecastResult(
                timestamp=timestamp,
                predicted=predicted,
                lower_bound=predicted - margin,
                upper_bound=predicted + margin,
                confidence=confidence
            ))

        return results

    def forecast_moving_average(
        self,
        points: List[DataPoint],
        horizon: int,
        interval: timedelta,
        window: int = 5
    ) -> List[ForecastResult]:
        """Forecast using moving average."""
        if len(points) < window:
            return []

        # Calculate moving average
        recent = points[-window:]
        avg = statistics.mean([p.value for p in recent])
        std = statistics.stdev([p.value for p in recent]) if window > 1 else 0

        results = []
        last_time = points[-1].timestamp

        for i in range(1, horizon + 1):
            timestamp = last_time + interval * i
            confidence = max(0.5, 1.0 - (i * 0.1))
            margin = std * 1.96  # 95% confidence interval

            results.append(ForecastResult(
                timestamp=timestamp,
                predicted=avg,
                lower_bound=avg - margin,
                upper_bound=avg + margin,
                confidence=confidence
            ))

        return results


# =============================================================================
# TIME SERIES MANAGER
# =============================================================================

class TimeSeriesManager:
    """
    Comprehensive Time Series Manager for BAEL.

    Provides time series data management and analysis.
    """

    def __init__(self, storage: Optional[TimeSeriesStorage] = None):
        self._storage = storage or MemoryStorage()
        self._metadata: Dict[str, SeriesMetadata] = {}
        self._aggregator = AggregationEngine()
        self._gap_filler = GapFiller()
        self._trend_analyzer = TrendAnalyzer()
        self._anomaly_detector = AnomalyDetector()
        self._forecaster = Forecaster()
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # SERIES MANAGEMENT
    # -------------------------------------------------------------------------

    def create_series(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        tags: Dict[str, str] = None
    ) -> SeriesMetadata:
        """Create new time series."""
        metadata = SeriesMetadata(
            name=name,
            description=description,
            unit=unit,
            tags=tags or {}
        )

        self._metadata[name] = metadata
        self._stats["series_created"] += 1

        return metadata

    def get_series(self, name: str) -> Optional[SeriesMetadata]:
        """Get series metadata."""
        return self._metadata.get(name)

    def list_series(self) -> List[SeriesMetadata]:
        """List all series."""
        return list(self._metadata.values())

    def delete_series(self, name: str) -> bool:
        """Delete series and its data."""
        if name not in self._metadata:
            return False

        del self._metadata[name]

        # Delete all data
        if isinstance(self._storage, MemoryStorage):
            if name in self._storage._data:
                del self._storage._data[name]
                del self._storage._indexes[name]

        return True

    # -------------------------------------------------------------------------
    # DATA OPERATIONS
    # -------------------------------------------------------------------------

    def write(
        self,
        series: str,
        value: float,
        timestamp: Optional[datetime] = None,
        tags: Dict[str, str] = None
    ) -> DataPoint:
        """Write single data point."""
        point = DataPoint(
            timestamp=timestamp or datetime.utcnow(),
            value=value,
            tags=tags or {}
        )

        self._storage.write(series, point)
        self._stats["points_written"] += 1

        return point

    def write_batch(
        self,
        series: str,
        points: List[Tuple[datetime, float]]
    ) -> int:
        """Write batch of data points."""
        count = 0

        for timestamp, value in points:
            self._storage.write(series, DataPoint(timestamp=timestamp, value=value))
            count += 1

        self._stats["points_written"] += count

        return count

    def read(
        self,
        series: str,
        start: datetime,
        end: Optional[datetime] = None
    ) -> List[DataPoint]:
        """Read data points in range."""
        end = end or datetime.utcnow()
        time_range = TimeRange(start=start, end=end)

        points = self._storage.read(series, time_range)
        self._stats["points_read"] += len(points)

        return points

    def read_latest(
        self,
        series: str,
        count: int = 1
    ) -> List[DataPoint]:
        """Read latest data points."""
        # Read all and take last N
        all_points = self._storage.read(
            series,
            TimeRange(
                start=datetime.min,
                end=datetime.utcnow()
            )
        )

        return all_points[-count:] if all_points else []

    def delete(
        self,
        series: str,
        start: datetime,
        end: datetime
    ) -> int:
        """Delete data points in range."""
        return self._storage.delete(series, TimeRange(start=start, end=end))

    # -------------------------------------------------------------------------
    # AGGREGATION
    # -------------------------------------------------------------------------

    def aggregate(
        self,
        series: str,
        start: datetime,
        end: datetime,
        resolution: Resolution,
        aggregation: AggregationType = AggregationType.AVG
    ) -> List[AggregationResult]:
        """Aggregate data by resolution."""
        points = self.read(series, start, end)

        return self._aggregator.aggregate(points, resolution, aggregation)

    def downsample(
        self,
        series: str,
        start: datetime,
        end: datetime,
        target_points: int
    ) -> List[DataPoint]:
        """Downsample series to target points."""
        points = self.read(series, start, end)

        return self._aggregator.downsample(points, target_points)

    def rolling_window(
        self,
        series: str,
        start: datetime,
        end: datetime,
        window_size: int,
        aggregation: AggregationType = AggregationType.AVG
    ) -> List[DataPoint]:
        """Apply rolling window aggregation."""
        points = self.read(series, start, end)

        return self._aggregator.rolling_window(points, window_size, aggregation)

    # -------------------------------------------------------------------------
    # GAP FILLING
    # -------------------------------------------------------------------------

    def fill_gaps(
        self,
        series: str,
        start: datetime,
        end: datetime,
        expected_interval: timedelta,
        method: InterpolationType = InterpolationType.LINEAR
    ) -> List[DataPoint]:
        """Fill gaps in time series."""
        points = self.read(series, start, end)

        return self._gap_filler.fill_gaps(points, expected_interval, method)

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def analyze_trend(
        self,
        series: str,
        start: datetime,
        end: datetime
    ) -> TrendInfo:
        """Analyze trend in series."""
        points = self.read(series, start, end)

        return self._trend_analyzer.analyze_trend(points)

    def detect_anomalies(
        self,
        series: str,
        start: datetime,
        end: datetime,
        sensitivity: float = 2.0
    ) -> List[AnomalyResult]:
        """Detect anomalies in series."""
        points = self.read(series, start, end)

        detector = AnomalyDetector(sensitivity)

        return detector.detect(points)

    def forecast(
        self,
        series: str,
        start: datetime,
        end: datetime,
        horizon: int,
        interval: timedelta
    ) -> List[ForecastResult]:
        """Forecast future values."""
        points = self.read(series, start, end)

        return self._forecaster.forecast_linear(points, horizon, interval)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_series_stats(
        self,
        series: str,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Get statistics for series."""
        points = self.read(series, start, end)

        if not points:
            return {}

        values = [p.value for p in points]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0,
            "first_timestamp": points[0].timestamp,
            "last_timestamp": points[-1].timestamp,
            "first_value": points[0].value,
            "last_value": points[-1].value
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "series_count": len(self._metadata),
            "series_created": self._stats["series_created"],
            "points_written": self._stats["points_written"],
            "points_read": self._stats["points_read"]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Time Series Manager."""
    print("=" * 70)
    print("BAEL - TIME SERIES MANAGER DEMO")
    print("Comprehensive Time Series Data Management")
    print("=" * 70)
    print()

    manager = TimeSeriesManager()

    # 1. Create Series
    print("1. CREATE SERIES:")
    print("-" * 40)

    metadata = manager.create_series(
        name="cpu_usage",
        description="CPU usage percentage",
        unit="%",
        tags={"host": "server1"}
    )

    print(f"   Created: {metadata.name}")
    print(f"   Description: {metadata.description}")
    print()

    # 2. Write Data
    print("2. WRITE DATA:")
    print("-" * 40)

    base_time = datetime.utcnow() - timedelta(hours=1)

    # Generate sample data
    import random

    for i in range(60):
        timestamp = base_time + timedelta(minutes=i)
        value = 50 + 20 * math.sin(i / 10) + random.uniform(-5, 5)
        manager.write("cpu_usage", value, timestamp)

    print(f"   Written: 60 data points")
    print()

    # 3. Read Data
    print("3. READ DATA:")
    print("-" * 40)

    points = manager.read(
        "cpu_usage",
        start=base_time,
        end=datetime.utcnow()
    )

    print(f"   Read: {len(points)} points")
    print(f"   First: {points[0].timestamp} = {points[0].value:.2f}")
    print(f"   Last: {points[-1].timestamp} = {points[-1].value:.2f}")
    print()

    # 4. Read Latest
    print("4. READ LATEST:")
    print("-" * 40)

    latest = manager.read_latest("cpu_usage", count=5)

    print(f"   Latest {len(latest)} points:")

    for p in latest:
        print(f"      {p.timestamp.strftime('%H:%M:%S')}: {p.value:.2f}")
    print()

    # 5. Aggregation
    print("5. AGGREGATION:")
    print("-" * 40)

    aggregated = manager.aggregate(
        "cpu_usage",
        start=base_time,
        end=datetime.utcnow(),
        resolution=Resolution(10, ResolutionUnit.MINUTE),
        aggregation=AggregationType.AVG
    )

    print(f"   Aggregated to {len(aggregated)} buckets (10 min each):")

    for agg in aggregated[:3]:
        print(f"      {agg.timestamp.strftime('%H:%M')}: avg={agg.value:.2f}, min={agg.min_value:.2f}, max={agg.max_value:.2f}")
    print()

    # 6. Downsampling
    print("6. DOWNSAMPLING:")
    print("-" * 40)

    downsampled = manager.downsample(
        "cpu_usage",
        start=base_time,
        end=datetime.utcnow(),
        target_points=10
    )

    print(f"   Downsampled from 60 to {len(downsampled)} points")
    print()

    # 7. Rolling Window
    print("7. ROLLING WINDOW:")
    print("-" * 40)

    rolling = manager.rolling_window(
        "cpu_usage",
        start=base_time,
        end=datetime.utcnow(),
        window_size=5,
        aggregation=AggregationType.AVG
    )

    print(f"   Rolling average (window=5): {len(rolling)} points")
    print(f"   Sample: {rolling[0].value:.2f} → {rolling[-1].value:.2f}")
    print()

    # 8. Gap Filling
    print("8. GAP FILLING:")
    print("-" * 40)

    # Create series with gaps
    manager.create_series("sparse_data")
    manager.write("sparse_data", 10, base_time)
    manager.write("sparse_data", 20, base_time + timedelta(minutes=10))
    manager.write("sparse_data", 30, base_time + timedelta(minutes=20))

    sparse = manager.read("sparse_data", base_time, datetime.utcnow())
    print(f"   Original: {len(sparse)} points")

    filled = manager.fill_gaps(
        "sparse_data",
        base_time,
        datetime.utcnow(),
        expected_interval=timedelta(minutes=5),
        method=InterpolationType.LINEAR
    )

    print(f"   After filling: {len(filled)} points")
    print()

    # 9. Trend Analysis
    print("9. TREND ANALYSIS:")
    print("-" * 40)

    # Create trending data
    manager.create_series("trending")

    for i in range(50):
        timestamp = base_time + timedelta(minutes=i)
        value = 10 + i * 0.5 + random.uniform(-2, 2)
        manager.write("trending", value, timestamp)

    trend = manager.analyze_trend(
        "trending",
        start=base_time,
        end=datetime.utcnow()
    )

    print(f"   Direction: {trend.direction.value}")
    print(f"   Slope: {trend.slope:.4f}")
    print(f"   Strength: {trend.strength:.2f}")
    print(f"   Change: {trend.change_percent:.1f}%")
    print()

    # 10. Anomaly Detection
    print("10. ANOMALY DETECTION:")
    print("-" * 40)

    # Create data with anomalies
    manager.create_series("with_anomalies")

    for i in range(50):
        timestamp = base_time + timedelta(minutes=i)
        value = 100 + random.uniform(-5, 5)

        # Add anomalies
        if i in [15, 30, 45]:
            value += 50

        manager.write("with_anomalies", value, timestamp)

    anomalies = manager.detect_anomalies(
        "with_anomalies",
        start=base_time,
        end=datetime.utcnow(),
        sensitivity=2.0
    )

    detected = [a for a in anomalies if a.is_anomaly]
    print(f"   Detected {len(detected)} anomalies out of {len(anomalies)} points")

    for a in detected[:3]:
        print(f"      {a.timestamp.strftime('%H:%M')}: value={a.value:.2f}, expected={a.expected:.2f}")
    print()

    # 11. Forecasting
    print("11. FORECASTING:")
    print("-" * 40)

    forecast = manager.forecast(
        "cpu_usage",
        start=base_time,
        end=datetime.utcnow(),
        horizon=5,
        interval=timedelta(minutes=1)
    )

    print(f"   Forecast for next {len(forecast)} periods:")

    for f in forecast:
        print(f"      {f.timestamp.strftime('%H:%M')}: {f.predicted:.2f} [{f.lower_bound:.2f}-{f.upper_bound:.2f}]")
    print()

    # 12. Series Statistics
    print("12. SERIES STATISTICS:")
    print("-" * 40)

    stats = manager.get_series_stats(
        "cpu_usage",
        start=base_time,
        end=datetime.utcnow()
    )

    print(f"   Count: {stats['count']}")
    print(f"   Min: {stats['min']:.2f}")
    print(f"   Max: {stats['max']:.2f}")
    print(f"   Mean: {stats['mean']:.2f}")
    print(f"   StdDev: {stats['stddev']:.2f}")
    print()

    # 13. List Series
    print("13. LIST SERIES:")
    print("-" * 40)

    series_list = manager.list_series()

    print(f"   Total series: {len(series_list)}")

    for series in series_list:
        print(f"      {series.name}: {series.description}")
    print()

    # 14. Manager Statistics
    print("14. MANAGER STATISTICS:")
    print("-" * 40)

    manager_stats = manager.get_stats()

    for key, value in manager_stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Time Series Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
