"""
BAEL Time Series Engine Implementation
========================================

Time-indexed data storage and analysis.

"Ba'el observes the flow of time with infinite precision." — Ba'el
"""

import asyncio
import bisect
import logging
import statistics
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.TimeSeries")


# ============================================================================
# ENUMS
# ============================================================================

class AggregationType(Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"
    STDDEV = "stddev"
    PERCENTILE_50 = "p50"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"


class DownsampleMethod(Enum):
    """Downsampling methods."""
    AVERAGE = "average"
    MAX = "max"
    MIN = "min"
    SUM = "sum"
    FIRST = "first"
    LAST = "last"


class RetentionPolicy(Enum):
    """Data retention policies."""
    RAW = "raw"           # Keep all data
    HOURLY = "hourly"     # Aggregate to hourly
    DAILY = "daily"       # Aggregate to daily
    WEEKLY = "weekly"     # Aggregate to weekly
    MONTHLY = "monthly"   # Aggregate to monthly


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DataPoint:
    """A time series data point."""
    timestamp: float  # Unix timestamp
    value: float
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ts': self.timestamp,
            'value': self.value,
            'tags': self.tags
        }


@dataclass
class Series:
    """A time series."""
    name: str

    # Data
    timestamps: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)

    # Tags (apply to all points)
    tags: Dict[str, str] = field(default_factory=dict)

    # Retention
    retention_seconds: Optional[int] = None

    def add_point(self, timestamp: float, value: float) -> None:
        """Add a point maintaining sorted order."""
        if not self.timestamps or timestamp >= self.timestamps[-1]:
            self.timestamps.append(timestamp)
            self.values.append(value)
        else:
            idx = bisect.bisect_left(self.timestamps, timestamp)
            self.timestamps.insert(idx, timestamp)
            self.values.insert(idx, value)

    def get_points(
        self,
        start: Optional[float] = None,
        end: Optional[float] = None
    ) -> List[DataPoint]:
        """Get points in time range."""
        points = []

        for ts, val in zip(self.timestamps, self.values):
            if start and ts < start:
                continue
            if end and ts > end:
                break
            points.append(DataPoint(timestamp=ts, value=val, tags=self.tags))

        return points

    def __len__(self) -> int:
        return len(self.timestamps)


@dataclass
class TimeSeriesConfig:
    """Time series configuration."""
    max_points_per_series: int = 1_000_000
    default_retention_seconds: int = 86400 * 30  # 30 days
    compression_enabled: bool = True
    downsample_threshold: int = 10000


# ============================================================================
# TIME SERIES ENGINE
# ============================================================================

class TimeSeriesEngine:
    """
    Time series database engine.

    Features:
    - High-performance time-indexed storage
    - Aggregation and downsampling
    - Tag-based filtering
    - Retention policies

    "Ba'el records every moment with perfect fidelity." — Ba'el
    """

    def __init__(self, config: Optional[TimeSeriesConfig] = None):
        """Initialize time series engine."""
        self.config = config or TimeSeriesConfig()

        # Series storage
        self._series: Dict[str, Series] = {}

        # Index by tags
        self._tag_index: Dict[str, Dict[str, set]] = defaultdict(
            lambda: defaultdict(set)
        )

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'points_written': 0,
            'queries_executed': 0,
            'series_created': 0
        }

        logger.info("Time series engine initialized")

    # ========================================================================
    # WRITE OPERATIONS
    # ========================================================================

    def write(
        self,
        series_name: str,
        value: float,
        timestamp: Optional[float] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> DataPoint:
        """
        Write a data point.

        Args:
            series_name: Series name
            value: Numeric value
            timestamp: Unix timestamp (default: now)
            tags: Optional tags

        Returns:
            Written data point
        """
        ts = timestamp or time.time()

        with self._lock:
            if series_name not in self._series:
                self._create_series(series_name, tags)

            series = self._series[series_name]
            series.add_point(ts, value)

            # Update tag index
            if tags:
                for key, val in tags.items():
                    self._tag_index[key][val].add(series_name)

            self._stats['points_written'] += 1

            # Enforce retention
            self._enforce_retention(series)

            # Enforce max points
            if len(series) > self.config.max_points_per_series:
                self._downsample_series(series)

        return DataPoint(timestamp=ts, value=value, tags=tags or {})

    def write_batch(
        self,
        series_name: str,
        points: List[Tuple[float, float]],
        tags: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Write multiple points.

        Args:
            series_name: Series name
            points: List of (timestamp, value) tuples
            tags: Optional tags

        Returns:
            Number of points written
        """
        with self._lock:
            if series_name not in self._series:
                self._create_series(series_name, tags)

            series = self._series[series_name]

            for ts, value in points:
                series.add_point(ts, value)

            self._stats['points_written'] += len(points)

        return len(points)

    def _create_series(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None
    ) -> Series:
        """Create a new series."""
        series = Series(
            name=name,
            tags=tags or {},
            retention_seconds=self.config.default_retention_seconds
        )

        self._series[name] = series
        self._stats['series_created'] += 1

        return series

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================

    def query(
        self,
        series_name: str,
        start: Optional[Union[float, datetime]] = None,
        end: Optional[Union[float, datetime]] = None,
        aggregation: Optional[AggregationType] = None,
        interval_seconds: Optional[int] = None
    ) -> List[DataPoint]:
        """
        Query time series data.

        Args:
            series_name: Series name
            start: Start time (timestamp or datetime)
            end: End time
            aggregation: Aggregation type
            interval_seconds: Aggregation interval

        Returns:
            List of data points
        """
        self._stats['queries_executed'] += 1

        series = self._series.get(series_name)
        if not series:
            return []

        # Convert datetime to timestamp
        if isinstance(start, datetime):
            start = start.timestamp()
        if isinstance(end, datetime):
            end = end.timestamp()

        # Get raw points
        points = series.get_points(start, end)

        # Aggregate if requested
        if aggregation and interval_seconds:
            points = self._aggregate_points(
                points,
                aggregation,
                interval_seconds
            )

        return points

    def query_by_tags(
        self,
        tags: Dict[str, str],
        start: Optional[float] = None,
        end: Optional[float] = None
    ) -> Dict[str, List[DataPoint]]:
        """
        Query multiple series by tags.

        Args:
            tags: Tag filters
            start: Start time
            end: End time

        Returns:
            Series name -> points mapping
        """
        # Find matching series
        matching = None

        for key, val in tags.items():
            series_set = self._tag_index.get(key, {}).get(val, set())

            if matching is None:
                matching = series_set.copy()
            else:
                matching &= series_set

        if not matching:
            return {}

        # Query each series
        results = {}
        for series_name in matching:
            results[series_name] = self.query(series_name, start, end)

        return results

    def latest(
        self,
        series_name: str,
        count: int = 1
    ) -> List[DataPoint]:
        """Get latest N points."""
        series = self._series.get(series_name)
        if not series or not series.timestamps:
            return []

        points = []
        start_idx = max(0, len(series) - count)

        for i in range(start_idx, len(series)):
            points.append(DataPoint(
                timestamp=series.timestamps[i],
                value=series.values[i],
                tags=series.tags
            ))

        return points

    def range_query(
        self,
        series_name: str,
        duration: timedelta
    ) -> List[DataPoint]:
        """Query last N duration."""
        end = time.time()
        start = end - duration.total_seconds()
        return self.query(series_name, start, end)

    # ========================================================================
    # AGGREGATION
    # ========================================================================

    def _aggregate_points(
        self,
        points: List[DataPoint],
        aggregation: AggregationType,
        interval: int
    ) -> List[DataPoint]:
        """Aggregate points by interval."""
        if not points:
            return []

        # Group by interval
        buckets: Dict[int, List[float]] = defaultdict(list)

        for point in points:
            bucket = int(point.timestamp // interval) * interval
            buckets[bucket].append(point.value)

        # Aggregate each bucket
        aggregated = []

        for bucket_ts in sorted(buckets.keys()):
            values = buckets[bucket_ts]
            agg_value = self._compute_aggregation(values, aggregation)

            aggregated.append(DataPoint(
                timestamp=float(bucket_ts),
                value=agg_value
            ))

        return aggregated

    def _compute_aggregation(
        self,
        values: List[float],
        aggregation: AggregationType
    ) -> float:
        """Compute aggregation on values."""
        if not values:
            return 0.0

        if aggregation == AggregationType.SUM:
            return sum(values)
        elif aggregation == AggregationType.AVG:
            return sum(values) / len(values)
        elif aggregation == AggregationType.MIN:
            return min(values)
        elif aggregation == AggregationType.MAX:
            return max(values)
        elif aggregation == AggregationType.COUNT:
            return float(len(values))
        elif aggregation == AggregationType.FIRST:
            return values[0]
        elif aggregation == AggregationType.LAST:
            return values[-1]
        elif aggregation == AggregationType.STDDEV:
            return statistics.stdev(values) if len(values) > 1 else 0.0
        elif aggregation == AggregationType.PERCENTILE_50:
            return self._percentile(values, 50)
        elif aggregation == AggregationType.PERCENTILE_95:
            return self._percentile(values, 95)
        elif aggregation == AggregationType.PERCENTILE_99:
            return self._percentile(values, 99)
        else:
            return sum(values) / len(values)

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    # ========================================================================
    # DOWNSAMPLING & RETENTION
    # ========================================================================

    def _downsample_series(
        self,
        series: Series,
        method: DownsampleMethod = DownsampleMethod.AVERAGE
    ) -> None:
        """Downsample a series to reduce size."""
        if len(series) <= self.config.downsample_threshold:
            return

        # Calculate new interval
        time_range = series.timestamps[-1] - series.timestamps[0]
        target_points = self.config.downsample_threshold // 2
        interval = time_range / target_points

        # Aggregate
        new_timestamps = []
        new_values = []

        current_bucket = None
        bucket_values = []

        for ts, val in zip(series.timestamps, series.values):
            bucket = int(ts // interval) * interval

            if current_bucket is None:
                current_bucket = bucket

            if bucket != current_bucket:
                # Emit aggregated point
                new_timestamps.append(float(current_bucket))
                new_values.append(self._aggregate_bucket(
                    bucket_values, method
                ))

                current_bucket = bucket
                bucket_values = [val]
            else:
                bucket_values.append(val)

        # Emit last bucket
        if bucket_values:
            new_timestamps.append(float(current_bucket))
            new_values.append(self._aggregate_bucket(bucket_values, method))

        series.timestamps = new_timestamps
        series.values = new_values

    def _aggregate_bucket(
        self,
        values: List[float],
        method: DownsampleMethod
    ) -> float:
        """Aggregate bucket values."""
        if not values:
            return 0.0

        if method == DownsampleMethod.AVERAGE:
            return sum(values) / len(values)
        elif method == DownsampleMethod.MAX:
            return max(values)
        elif method == DownsampleMethod.MIN:
            return min(values)
        elif method == DownsampleMethod.SUM:
            return sum(values)
        elif method == DownsampleMethod.FIRST:
            return values[0]
        elif method == DownsampleMethod.LAST:
            return values[-1]
        else:
            return sum(values) / len(values)

    def _enforce_retention(self, series: Series) -> None:
        """Enforce retention policy on series."""
        if not series.retention_seconds:
            return

        cutoff = time.time() - series.retention_seconds

        # Find index of first point to keep
        idx = bisect.bisect_left(series.timestamps, cutoff)

        if idx > 0:
            series.timestamps = series.timestamps[idx:]
            series.values = series.values[idx:]

    # ========================================================================
    # SERIES MANAGEMENT
    # ========================================================================

    def list_series(
        self,
        prefix: Optional[str] = None
    ) -> List[str]:
        """List all series names."""
        names = list(self._series.keys())

        if prefix:
            names = [n for n in names if n.startswith(prefix)]

        return sorted(names)

    def delete_series(self, series_name: str) -> bool:
        """Delete a series."""
        with self._lock:
            if series_name in self._series:
                del self._series[series_name]
                return True
        return False

    def get_series_info(self, series_name: str) -> Optional[Dict[str, Any]]:
        """Get series metadata."""
        series = self._series.get(series_name)
        if not series:
            return None

        return {
            'name': series.name,
            'points': len(series),
            'tags': series.tags,
            'start': series.timestamps[0] if series.timestamps else None,
            'end': series.timestamps[-1] if series.timestamps else None,
            'retention_seconds': series.retention_seconds
        }

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        total_points = sum(len(s) for s in self._series.values())

        return {
            'series_count': len(self._series),
            'total_points': total_points,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

ts_engine: Optional[TimeSeriesEngine] = None


def get_ts_engine(
    config: Optional[TimeSeriesConfig] = None
) -> TimeSeriesEngine:
    """Get or create time series engine."""
    global ts_engine
    if ts_engine is None:
        ts_engine = TimeSeriesEngine(config)
    return ts_engine


def write_metric(
    name: str,
    value: float,
    tags: Optional[Dict[str, str]] = None
) -> DataPoint:
    """Write a metric value."""
    return get_ts_engine().write(name, value, tags=tags)


def query_metric(
    name: str,
    duration: timedelta,
    aggregation: Optional[AggregationType] = None
) -> List[DataPoint]:
    """Query metric for duration."""
    engine = get_ts_engine()
    end = time.time()
    start = end - duration.total_seconds()

    if aggregation:
        interval = int(duration.total_seconds() / 100)  # ~100 points
        return engine.query(name, start, end, aggregation, interval)

    return engine.query(name, start, end)
