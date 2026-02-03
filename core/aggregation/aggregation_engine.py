#!/usr/bin/env python3
"""
BAEL - Aggregation Engine
Data aggregation for agents.

Features:
- Multiple aggregation types
- Window-based aggregation
- Group-by operations
- Rolling aggregations
- Statistical functions
"""

import asyncio
import hashlib
import json
import math
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from statistics import mean, median, mode, stdev, variance
from typing import (
    Any, Callable, Dict, Generic, Iterator, List, Optional, Set, Tuple,
    Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AggregationType(Enum):
    """Aggregation types."""
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    FIRST = "first"
    LAST = "last"
    MEDIAN = "median"
    MODE = "mode"
    STDDEV = "stddev"
    VARIANCE = "variance"
    PERCENTILE = "percentile"
    DISTINCT_COUNT = "distinct_count"
    LIST = "list"
    DISTINCT = "distinct"


class WindowType(Enum):
    """Window types."""
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    GLOBAL = "global"


class TimeUnit(Enum):
    """Time units."""
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


class GroupByType(Enum):
    """Group-by types."""
    FIELD = "field"
    EXPRESSION = "expression"
    TIME_BUCKET = "time_bucket"
    RANGE = "range"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class DataPoint:
    """A data point."""
    point_id: str = ""
    value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.point_id:
            self.point_id = str(uuid.uuid4())[:8]


@dataclass
class AggregationResult:
    """Aggregation result."""
    aggregation_type: AggregationType = AggregationType.SUM
    value: Any = None
    count: int = 0
    group_key: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WindowSpec:
    """Window specification."""
    window_type: WindowType = WindowType.TUMBLING
    size: float = 60.0
    slide: float = 0.0
    time_unit: TimeUnit = TimeUnit.SECONDS
    
    def size_seconds(self) -> float:
        """Get size in seconds."""
        if self.time_unit == TimeUnit.SECONDS:
            return self.size
        elif self.time_unit == TimeUnit.MINUTES:
            return self.size * 60
        elif self.time_unit == TimeUnit.HOURS:
            return self.size * 3600
        elif self.time_unit == TimeUnit.DAYS:
            return self.size * 86400
        return self.size
    
    def slide_seconds(self) -> float:
        """Get slide in seconds."""
        if self.slide == 0:
            return self.size_seconds()
        
        if self.time_unit == TimeUnit.SECONDS:
            return self.slide
        elif self.time_unit == TimeUnit.MINUTES:
            return self.slide * 60
        elif self.time_unit == TimeUnit.HOURS:
            return self.slide * 3600
        elif self.time_unit == TimeUnit.DAYS:
            return self.slide * 86400
        return self.slide


@dataclass
class GroupSpec:
    """Group specification."""
    group_type: GroupByType = GroupByType.FIELD
    field: Optional[str] = None
    expression: Optional[Callable] = None
    time_bucket_seconds: float = 60.0
    ranges: Optional[List[Tuple[Any, Any]]] = None


@dataclass
class AggregationConfig:
    """Aggregation configuration."""
    buffer_size: int = 10000
    default_window: WindowSpec = field(default_factory=WindowSpec)


# =============================================================================
# AGGREGATORS
# =============================================================================

class Aggregator(ABC):
    """Base aggregator."""
    
    @abstractmethod
    def add(self, value: Any) -> None:
        """Add a value."""
        pass
    
    @abstractmethod
    def result(self) -> Any:
        """Get result."""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset aggregator."""
        pass
    
    @abstractmethod
    def merge(self, other: "Aggregator") -> None:
        """Merge another aggregator."""
        pass


class SumAggregator(Aggregator):
    """Sum aggregator."""
    
    def __init__(self):
        self._sum = 0.0
        self._count = 0
    
    def add(self, value: Any) -> None:
        if value is not None:
            self._sum += float(value)
            self._count += 1
    
    def result(self) -> float:
        return self._sum
    
    def reset(self) -> None:
        self._sum = 0.0
        self._count = 0
    
    def merge(self, other: "SumAggregator") -> None:
        self._sum += other._sum
        self._count += other._count


class CountAggregator(Aggregator):
    """Count aggregator."""
    
    def __init__(self):
        self._count = 0
    
    def add(self, value: Any) -> None:
        if value is not None:
            self._count += 1
    
    def result(self) -> int:
        return self._count
    
    def reset(self) -> None:
        self._count = 0
    
    def merge(self, other: "CountAggregator") -> None:
        self._count += other._count


class AvgAggregator(Aggregator):
    """Average aggregator."""
    
    def __init__(self):
        self._sum = 0.0
        self._count = 0
    
    def add(self, value: Any) -> None:
        if value is not None:
            self._sum += float(value)
            self._count += 1
    
    def result(self) -> float:
        if self._count == 0:
            return 0.0
        return self._sum / self._count
    
    def reset(self) -> None:
        self._sum = 0.0
        self._count = 0
    
    def merge(self, other: "AvgAggregator") -> None:
        self._sum += other._sum
        self._count += other._count


class MinAggregator(Aggregator):
    """Minimum aggregator."""
    
    def __init__(self):
        self._min: Optional[float] = None
    
    def add(self, value: Any) -> None:
        if value is not None:
            val = float(value)
            if self._min is None or val < self._min:
                self._min = val
    
    def result(self) -> Optional[float]:
        return self._min
    
    def reset(self) -> None:
        self._min = None
    
    def merge(self, other: "MinAggregator") -> None:
        if other._min is not None:
            if self._min is None or other._min < self._min:
                self._min = other._min


class MaxAggregator(Aggregator):
    """Maximum aggregator."""
    
    def __init__(self):
        self._max: Optional[float] = None
    
    def add(self, value: Any) -> None:
        if value is not None:
            val = float(value)
            if self._max is None or val > self._max:
                self._max = val
    
    def result(self) -> Optional[float]:
        return self._max
    
    def reset(self) -> None:
        self._max = None
    
    def merge(self, other: "MaxAggregator") -> None:
        if other._max is not None:
            if self._max is None or other._max > self._max:
                self._max = other._max


class FirstAggregator(Aggregator):
    """First value aggregator."""
    
    def __init__(self):
        self._first: Any = None
        self._set = False
    
    def add(self, value: Any) -> None:
        if not self._set and value is not None:
            self._first = value
            self._set = True
    
    def result(self) -> Any:
        return self._first
    
    def reset(self) -> None:
        self._first = None
        self._set = False
    
    def merge(self, other: "FirstAggregator") -> None:
        if not self._set and other._set:
            self._first = other._first
            self._set = True


class LastAggregator(Aggregator):
    """Last value aggregator."""
    
    def __init__(self):
        self._last: Any = None
    
    def add(self, value: Any) -> None:
        if value is not None:
            self._last = value
    
    def result(self) -> Any:
        return self._last
    
    def reset(self) -> None:
        self._last = None
    
    def merge(self, other: "LastAggregator") -> None:
        if other._last is not None:
            self._last = other._last


class ListAggregator(Aggregator):
    """List aggregator."""
    
    def __init__(self):
        self._values: List[Any] = []
    
    def add(self, value: Any) -> None:
        if value is not None:
            self._values.append(value)
    
    def result(self) -> List[Any]:
        return list(self._values)
    
    def reset(self) -> None:
        self._values.clear()
    
    def merge(self, other: "ListAggregator") -> None:
        self._values.extend(other._values)


class DistinctAggregator(Aggregator):
    """Distinct values aggregator."""
    
    def __init__(self):
        self._values: Set[Any] = set()
    
    def add(self, value: Any) -> None:
        if value is not None:
            if isinstance(value, (list, dict)):
                value = json.dumps(value, sort_keys=True)
            self._values.add(value)
    
    def result(self) -> List[Any]:
        return list(self._values)
    
    def reset(self) -> None:
        self._values.clear()
    
    def merge(self, other: "DistinctAggregator") -> None:
        self._values.update(other._values)


class DistinctCountAggregator(Aggregator):
    """Distinct count aggregator."""
    
    def __init__(self):
        self._values: Set[Any] = set()
    
    def add(self, value: Any) -> None:
        if value is not None:
            if isinstance(value, (list, dict)):
                value = json.dumps(value, sort_keys=True)
            self._values.add(value)
    
    def result(self) -> int:
        return len(self._values)
    
    def reset(self) -> None:
        self._values.clear()
    
    def merge(self, other: "DistinctCountAggregator") -> None:
        self._values.update(other._values)


class StatisticalAggregator(Aggregator):
    """Statistical aggregator (median, mode, stdev, variance)."""
    
    def __init__(self, stat_type: str = "median"):
        self._values: List[float] = []
        self._stat_type = stat_type
    
    def add(self, value: Any) -> None:
        if value is not None:
            self._values.append(float(value))
    
    def result(self) -> Optional[float]:
        if not self._values:
            return None
        
        if self._stat_type == "median":
            return median(self._values)
        elif self._stat_type == "mode":
            try:
                return mode(self._values)
            except:
                return self._values[0]
        elif self._stat_type == "stddev":
            if len(self._values) < 2:
                return 0.0
            return stdev(self._values)
        elif self._stat_type == "variance":
            if len(self._values) < 2:
                return 0.0
            return variance(self._values)
        
        return None
    
    def reset(self) -> None:
        self._values.clear()
    
    def merge(self, other: "StatisticalAggregator") -> None:
        self._values.extend(other._values)


class PercentileAggregator(Aggregator):
    """Percentile aggregator."""
    
    def __init__(self, percentile: float = 50.0):
        self._values: List[float] = []
        self._percentile = percentile
    
    def add(self, value: Any) -> None:
        if value is not None:
            self._values.append(float(value))
    
    def result(self) -> Optional[float]:
        if not self._values:
            return None
        
        sorted_values = sorted(self._values)
        n = len(sorted_values)
        k = (n - 1) * (self._percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return sorted_values[int(k)]
        
        return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)
    
    def reset(self) -> None:
        self._values.clear()
    
    def merge(self, other: "PercentileAggregator") -> None:
        self._values.extend(other._values)


# =============================================================================
# AGGREGATOR FACTORY
# =============================================================================

class AggregatorFactory:
    """Create aggregators."""
    
    _registry: Dict[AggregationType, Type[Aggregator]] = {
        AggregationType.SUM: SumAggregator,
        AggregationType.COUNT: CountAggregator,
        AggregationType.AVG: AvgAggregator,
        AggregationType.MIN: MinAggregator,
        AggregationType.MAX: MaxAggregator,
        AggregationType.FIRST: FirstAggregator,
        AggregationType.LAST: LastAggregator,
        AggregationType.LIST: ListAggregator,
        AggregationType.DISTINCT: DistinctAggregator,
        AggregationType.DISTINCT_COUNT: DistinctCountAggregator,
    }
    
    @classmethod
    def create(
        cls,
        agg_type: AggregationType,
        **kwargs
    ) -> Aggregator:
        """Create an aggregator."""
        if agg_type == AggregationType.MEDIAN:
            return StatisticalAggregator("median")
        elif agg_type == AggregationType.MODE:
            return StatisticalAggregator("mode")
        elif agg_type == AggregationType.STDDEV:
            return StatisticalAggregator("stddev")
        elif agg_type == AggregationType.VARIANCE:
            return StatisticalAggregator("variance")
        elif agg_type == AggregationType.PERCENTILE:
            percentile = kwargs.get("percentile", 50.0)
            return PercentileAggregator(percentile)
        
        agg_class = cls._registry.get(agg_type, SumAggregator)
        return agg_class()
    
    @classmethod
    def available(cls) -> List[str]:
        """Get available aggregation types."""
        return [t.value for t in AggregationType]


# =============================================================================
# DATA BUFFER
# =============================================================================

class DataBuffer:
    """Buffer for data points."""
    
    def __init__(self, max_size: int = 10000):
        self._points: List[DataPoint] = []
        self._max_size = max_size
    
    def add(self, point: DataPoint) -> None:
        """Add a point."""
        self._points.append(point)
        
        if len(self._points) > self._max_size:
            self._points.pop(0)
    
    def get_all(self) -> List[DataPoint]:
        """Get all points."""
        return list(self._points)
    
    def get_in_window(
        self,
        window_seconds: float,
        reference_time: Optional[datetime] = None
    ) -> List[DataPoint]:
        """Get points in time window."""
        ref_time = reference_time or datetime.now()
        cutoff = ref_time - timedelta(seconds=window_seconds)
        
        return [p for p in self._points if p.timestamp >= cutoff]
    
    def get_by_labels(self, labels: Dict[str, str]) -> List[DataPoint]:
        """Get points matching labels."""
        results = []
        
        for point in self._points:
            match = True
            for key, value in labels.items():
                if point.labels.get(key) != value:
                    match = False
                    break
            if match:
                results.append(point)
        
        return results
    
    def clear(self) -> int:
        """Clear buffer."""
        count = len(self._points)
        self._points.clear()
        return count
    
    def count(self) -> int:
        """Count points."""
        return len(self._points)


# =============================================================================
# GROUP BY MANAGER
# =============================================================================

class GroupByManager:
    """Manage group-by operations."""
    
    def __init__(self):
        self._groups: Dict[str, List[DataPoint]] = defaultdict(list)
    
    def group(
        self,
        points: List[DataPoint],
        spec: GroupSpec
    ) -> Dict[str, List[DataPoint]]:
        """Group points by specification."""
        groups: Dict[str, List[DataPoint]] = defaultdict(list)
        
        for point in points:
            key = self._compute_group_key(point, spec)
            groups[key].append(point)
        
        return dict(groups)
    
    def _compute_group_key(
        self,
        point: DataPoint,
        spec: GroupSpec
    ) -> str:
        """Compute group key for point."""
        if spec.group_type == GroupByType.FIELD:
            if spec.field and spec.field in point.labels:
                return point.labels[spec.field]
            elif spec.field and isinstance(point.value, dict):
                return str(point.value.get(spec.field, "default"))
            return "default"
        
        elif spec.group_type == GroupByType.EXPRESSION:
            if spec.expression:
                try:
                    return str(spec.expression(point))
                except:
                    return "error"
            return "default"
        
        elif spec.group_type == GroupByType.TIME_BUCKET:
            bucket = int(point.timestamp.timestamp() / spec.time_bucket_seconds)
            return str(bucket)
        
        elif spec.group_type == GroupByType.RANGE:
            if spec.ranges and isinstance(point.value, (int, float)):
                for i, (low, high) in enumerate(spec.ranges):
                    if low <= point.value < high:
                        return f"range_{i}_{low}_{high}"
            return "out_of_range"
        
        return "default"


# =============================================================================
# WINDOW MANAGER
# =============================================================================

class WindowManager:
    """Manage windowed aggregations."""
    
    def __init__(self):
        self._windows: Dict[str, List[DataPoint]] = defaultdict(list)
    
    def get_windows(
        self,
        points: List[DataPoint],
        spec: WindowSpec
    ) -> List[List[DataPoint]]:
        """Get windowed data."""
        if not points:
            return []
        
        if spec.window_type == WindowType.GLOBAL:
            return [points]
        
        elif spec.window_type == WindowType.TUMBLING:
            return self._tumbling_windows(points, spec)
        
        elif spec.window_type == WindowType.SLIDING:
            return self._sliding_windows(points, spec)
        
        return [points]
    
    def _tumbling_windows(
        self,
        points: List[DataPoint],
        spec: WindowSpec
    ) -> List[List[DataPoint]]:
        """Create tumbling windows."""
        sorted_points = sorted(points, key=lambda p: p.timestamp)
        windows: List[List[DataPoint]] = []
        
        if not sorted_points:
            return []
        
        window_size = spec.size_seconds()
        start_time = sorted_points[0].timestamp
        current_window: List[DataPoint] = []
        
        for point in sorted_points:
            diff = (point.timestamp - start_time).total_seconds()
            
            if diff >= window_size:
                if current_window:
                    windows.append(current_window)
                current_window = [point]
                start_time = point.timestamp
            else:
                current_window.append(point)
        
        if current_window:
            windows.append(current_window)
        
        return windows
    
    def _sliding_windows(
        self,
        points: List[DataPoint],
        spec: WindowSpec
    ) -> List[List[DataPoint]]:
        """Create sliding windows."""
        sorted_points = sorted(points, key=lambda p: p.timestamp)
        windows: List[List[DataPoint]] = []
        
        if not sorted_points:
            return []
        
        window_size = spec.size_seconds()
        slide_size = spec.slide_seconds()
        
        min_time = sorted_points[0].timestamp
        max_time = sorted_points[-1].timestamp
        
        current_start = min_time
        
        while current_start <= max_time:
            window_end = current_start + timedelta(seconds=window_size)
            
            window_points = [
                p for p in sorted_points
                if current_start <= p.timestamp < window_end
            ]
            
            if window_points:
                windows.append(window_points)
            
            current_start += timedelta(seconds=slide_size)
        
        return windows


# =============================================================================
# ROLLING AGGREGATOR
# =============================================================================

class RollingAggregator:
    """Rolling aggregations."""
    
    def __init__(self, window_size: int = 10):
        self._window_size = window_size
        self._values: List[float] = []
    
    def add(self, value: float) -> None:
        """Add a value."""
        self._values.append(value)
        
        if len(self._values) > self._window_size:
            self._values.pop(0)
    
    def rolling_avg(self) -> float:
        """Get rolling average."""
        if not self._values:
            return 0.0
        return sum(self._values) / len(self._values)
    
    def rolling_sum(self) -> float:
        """Get rolling sum."""
        return sum(self._values)
    
    def rolling_min(self) -> Optional[float]:
        """Get rolling minimum."""
        return min(self._values) if self._values else None
    
    def rolling_max(self) -> Optional[float]:
        """Get rolling maximum."""
        return max(self._values) if self._values else None
    
    def rolling_stddev(self) -> float:
        """Get rolling standard deviation."""
        if len(self._values) < 2:
            return 0.0
        return stdev(self._values)
    
    def is_full(self) -> bool:
        """Check if window is full."""
        return len(self._values) >= self._window_size
    
    def clear(self) -> None:
        """Clear values."""
        self._values.clear()


# =============================================================================
# AGGREGATION ENGINE
# =============================================================================

class AggregationEngine:
    """
    Aggregation Engine for BAEL.
    
    Data aggregation with windows and groups.
    """
    
    def __init__(self, config: Optional[AggregationConfig] = None):
        self._config = config or AggregationConfig()
        
        self._buffer = DataBuffer(self._config.buffer_size)
        self._group_manager = GroupByManager()
        self._window_manager = WindowManager()
        self._rolling_aggregators: Dict[str, RollingAggregator] = {}
    
    # ----- Data Points -----
    
    def add(
        self,
        value: Any,
        labels: Optional[Dict[str, str]] = None
    ) -> DataPoint:
        """Add a data point."""
        point = DataPoint(
            value=value,
            labels=labels or {}
        )
        self._buffer.add(point)
        return point
    
    def add_many(
        self,
        values: List[Any],
        labels: Optional[Dict[str, str]] = None
    ) -> int:
        """Add many data points."""
        count = 0
        for value in values:
            self.add(value, labels)
            count += 1
        return count
    
    def get_points(
        self,
        window_seconds: Optional[float] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> List[DataPoint]:
        """Get data points."""
        if window_seconds:
            points = self._buffer.get_in_window(window_seconds)
        else:
            points = self._buffer.get_all()
        
        if labels:
            points = [
                p for p in points
                if all(p.labels.get(k) == v for k, v in labels.items())
            ]
        
        return points
    
    # ----- Basic Aggregation -----
    
    def aggregate(
        self,
        agg_type: AggregationType,
        points: Optional[List[DataPoint]] = None,
        field: Optional[str] = None,
        **kwargs
    ) -> AggregationResult:
        """Perform aggregation."""
        if points is None:
            points = self._buffer.get_all()
        
        aggregator = AggregatorFactory.create(agg_type, **kwargs)
        
        for point in points:
            if field and isinstance(point.value, dict):
                value = point.value.get(field)
            else:
                value = point.value
            
            aggregator.add(value)
        
        return AggregationResult(
            aggregation_type=agg_type,
            value=aggregator.result(),
            count=len(points)
        )
    
    def sum(self, points: Optional[List[DataPoint]] = None) -> float:
        """Sum values."""
        result = self.aggregate(AggregationType.SUM, points)
        return result.value or 0.0
    
    def count(self, points: Optional[List[DataPoint]] = None) -> int:
        """Count values."""
        result = self.aggregate(AggregationType.COUNT, points)
        return result.value or 0
    
    def avg(self, points: Optional[List[DataPoint]] = None) -> float:
        """Average values."""
        result = self.aggregate(AggregationType.AVG, points)
        return result.value or 0.0
    
    def min(self, points: Optional[List[DataPoint]] = None) -> Optional[float]:
        """Minimum value."""
        result = self.aggregate(AggregationType.MIN, points)
        return result.value
    
    def max(self, points: Optional[List[DataPoint]] = None) -> Optional[float]:
        """Maximum value."""
        result = self.aggregate(AggregationType.MAX, points)
        return result.value
    
    def median(self, points: Optional[List[DataPoint]] = None) -> Optional[float]:
        """Median value."""
        result = self.aggregate(AggregationType.MEDIAN, points)
        return result.value
    
    def stddev(self, points: Optional[List[DataPoint]] = None) -> float:
        """Standard deviation."""
        result = self.aggregate(AggregationType.STDDEV, points)
        return result.value or 0.0
    
    def percentile(
        self,
        p: float = 50.0,
        points: Optional[List[DataPoint]] = None
    ) -> Optional[float]:
        """Percentile value."""
        result = self.aggregate(
            AggregationType.PERCENTILE,
            points,
            percentile=p
        )
        return result.value
    
    def distinct(
        self,
        points: Optional[List[DataPoint]] = None
    ) -> List[Any]:
        """Distinct values."""
        result = self.aggregate(AggregationType.DISTINCT, points)
        return result.value or []
    
    def distinct_count(
        self,
        points: Optional[List[DataPoint]] = None
    ) -> int:
        """Distinct count."""
        result = self.aggregate(AggregationType.DISTINCT_COUNT, points)
        return result.value or 0
    
    # ----- Group By Aggregation -----
    
    def group_by(
        self,
        spec: GroupSpec,
        agg_type: AggregationType = AggregationType.COUNT,
        points: Optional[List[DataPoint]] = None
    ) -> Dict[str, AggregationResult]:
        """Aggregate with group by."""
        if points is None:
            points = self._buffer.get_all()
        
        groups = self._group_manager.group(points, spec)
        results = {}
        
        for group_key, group_points in groups.items():
            result = self.aggregate(agg_type, group_points)
            result.group_key = group_key
            results[group_key] = result
        
        return results
    
    def group_by_field(
        self,
        field: str,
        agg_type: AggregationType = AggregationType.COUNT
    ) -> Dict[str, AggregationResult]:
        """Group by field."""
        spec = GroupSpec(group_type=GroupByType.FIELD, field=field)
        return self.group_by(spec, agg_type)
    
    def group_by_time(
        self,
        bucket_seconds: float = 60.0,
        agg_type: AggregationType = AggregationType.COUNT
    ) -> Dict[str, AggregationResult]:
        """Group by time bucket."""
        spec = GroupSpec(
            group_type=GroupByType.TIME_BUCKET,
            time_bucket_seconds=bucket_seconds
        )
        return self.group_by(spec, agg_type)
    
    # ----- Windowed Aggregation -----
    
    def windowed(
        self,
        window: WindowSpec,
        agg_type: AggregationType = AggregationType.AVG,
        points: Optional[List[DataPoint]] = None
    ) -> List[AggregationResult]:
        """Windowed aggregation."""
        if points is None:
            points = self._buffer.get_all()
        
        windows = self._window_manager.get_windows(points, window)
        results = []
        
        for window_points in windows:
            result = self.aggregate(agg_type, window_points)
            if window_points:
                result.timestamp = window_points[0].timestamp
            results.append(result)
        
        return results
    
    def tumbling_window(
        self,
        size_seconds: float,
        agg_type: AggregationType = AggregationType.AVG
    ) -> List[AggregationResult]:
        """Tumbling window aggregation."""
        window = WindowSpec(
            window_type=WindowType.TUMBLING,
            size=size_seconds
        )
        return self.windowed(window, agg_type)
    
    def sliding_window(
        self,
        size_seconds: float,
        slide_seconds: float,
        agg_type: AggregationType = AggregationType.AVG
    ) -> List[AggregationResult]:
        """Sliding window aggregation."""
        window = WindowSpec(
            window_type=WindowType.SLIDING,
            size=size_seconds,
            slide=slide_seconds
        )
        return self.windowed(window, agg_type)
    
    # ----- Rolling Aggregation -----
    
    def add_to_rolling(
        self,
        name: str,
        value: float,
        window_size: int = 10
    ) -> None:
        """Add value to rolling aggregator."""
        if name not in self._rolling_aggregators:
            self._rolling_aggregators[name] = RollingAggregator(window_size)
        
        self._rolling_aggregators[name].add(value)
    
    def get_rolling_avg(self, name: str) -> float:
        """Get rolling average."""
        agg = self._rolling_aggregators.get(name)
        return agg.rolling_avg() if agg else 0.0
    
    def get_rolling_sum(self, name: str) -> float:
        """Get rolling sum."""
        agg = self._rolling_aggregators.get(name)
        return agg.rolling_sum() if agg else 0.0
    
    def get_rolling_stats(self, name: str) -> Dict[str, float]:
        """Get all rolling stats."""
        agg = self._rolling_aggregators.get(name)
        
        if not agg:
            return {}
        
        return {
            "avg": agg.rolling_avg(),
            "sum": agg.rolling_sum(),
            "min": agg.rolling_min(),
            "max": agg.rolling_max(),
            "stddev": agg.rolling_stddev()
        }
    
    # ----- Multi-Aggregation -----
    
    def multi_aggregate(
        self,
        agg_types: List[AggregationType],
        points: Optional[List[DataPoint]] = None
    ) -> Dict[str, Any]:
        """Multiple aggregations at once."""
        results = {}
        
        for agg_type in agg_types:
            result = self.aggregate(agg_type, points)
            results[agg_type.value] = result.value
        
        return results
    
    # ----- Management -----
    
    def clear(self) -> int:
        """Clear buffer."""
        return self._buffer.clear()
    
    def point_count(self) -> int:
        """Count points in buffer."""
        return self._buffer.count()
    
    # ----- Statistics -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        points = self._buffer.get_all()
        
        return {
            "total_points": len(points),
            "rolling_aggregators": len(self._rolling_aggregators),
            "buffer_size": self._config.buffer_size
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get data summary."""
        points = self._buffer.get_all()
        
        if not points:
            return {"points": 0}
        
        return {
            "points": len(points),
            "sum": self.sum(points),
            "avg": self.avg(points),
            "min": self.min(points),
            "max": self.max(points),
            "distinct": self.distinct_count(points)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Aggregation Engine."""
    print("=" * 70)
    print("BAEL - AGGREGATION ENGINE DEMO")
    print("Data Aggregation & Analysis")
    print("=" * 70)
    print()
    
    engine = AggregationEngine()
    
    # 1. Add Data Points
    print("1. ADD DATA POINTS:")
    print("-" * 40)
    
    for i in range(20):
        engine.add(
            value=i * 10 + (i % 5),
            labels={"category": f"cat_{i % 3}", "region": f"region_{i % 2}"}
        )
    
    print(f"   Added {engine.point_count()} data points")
    print()
    
    # 2. Basic Aggregations
    print("2. BASIC AGGREGATIONS:")
    print("-" * 40)
    
    print(f"   Sum: {engine.sum()}")
    print(f"   Count: {engine.count()}")
    print(f"   Average: {engine.avg():.2f}")
    print(f"   Min: {engine.min()}")
    print(f"   Max: {engine.max()}")
    print(f"   Median: {engine.median()}")
    print(f"   Std Dev: {engine.stddev():.2f}")
    print()
    
    # 3. Percentiles
    print("3. PERCENTILES:")
    print("-" * 40)
    
    print(f"   P25: {engine.percentile(25)}")
    print(f"   P50: {engine.percentile(50)}")
    print(f"   P75: {engine.percentile(75)}")
    print(f"   P90: {engine.percentile(90)}")
    print(f"   P99: {engine.percentile(99)}")
    print()
    
    # 4. Distinct Values
    print("4. DISTINCT VALUES:")
    print("-" * 40)
    
    print(f"   Distinct count: {engine.distinct_count()}")
    print(f"   Sample values: {engine.distinct()[:5]}...")
    print()
    
    # 5. Group By Field
    print("5. GROUP BY FIELD:")
    print("-" * 40)
    
    grouped = engine.group_by_field("category", AggregationType.SUM)
    for key, result in grouped.items():
        print(f"   {key}: {result.value} (count: {result.count})")
    print()
    
    # 6. Group By Region with Average
    print("6. GROUP BY REGION (AVG):")
    print("-" * 40)
    
    grouped = engine.group_by_field("region", AggregationType.AVG)
    for key, result in grouped.items():
        print(f"   {key}: {result.value:.2f} (count: {result.count})")
    print()
    
    # 7. Multi-Aggregation
    print("7. MULTI-AGGREGATION:")
    print("-" * 40)
    
    multi = engine.multi_aggregate([
        AggregationType.SUM,
        AggregationType.AVG,
        AggregationType.MIN,
        AggregationType.MAX,
        AggregationType.COUNT
    ])
    for agg_name, value in multi.items():
        print(f"   {agg_name}: {value}")
    print()
    
    # 8. Rolling Aggregation
    print("8. ROLLING AGGREGATION:")
    print("-" * 40)
    
    for i in range(15):
        engine.add_to_rolling("metrics", i * 2.5, window_size=5)
    
    stats = engine.get_rolling_stats("metrics")
    for key, value in stats.items():
        print(f"   Rolling {key}: {value}")
    print()
    
    # 9. Data Summary
    print("9. DATA SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")
    print()
    
    # 10. Engine Stats
    print("10. ENGINE STATS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 11. Aggregator Types
    print("11. AVAILABLE AGGREGATION TYPES:")
    print("-" * 40)
    
    types = AggregatorFactory.available()
    for i, agg_type in enumerate(types, 1):
        print(f"   {i:2d}. {agg_type}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Aggregation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
