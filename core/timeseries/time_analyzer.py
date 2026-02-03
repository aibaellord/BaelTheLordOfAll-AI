#!/usr/bin/env python3
"""
BAEL - Time Series Analyzer
Advanced time series analysis and forecasting.

Features:
- Trend detection
- Seasonality analysis
- Moving averages
- Exponential smoothing
- Forecasting
- Anomaly detection in time series
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TrendType(Enum):
    """Types of trends."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    CYCLIC = "cyclic"


class SeasonalityType(Enum):
    """Types of seasonality."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ForecastMethod(Enum):
    """Forecasting methods."""
    NAIVE = "naive"
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL = "exponential"
    HOLT_WINTERS = "holt_winters"


class SmoothingType(Enum):
    """Smoothing types."""
    SIMPLE = "simple"
    WEIGHTED = "weighted"
    EXPONENTIAL = "exponential"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TimePoint:
    """A point in time series."""
    point_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    value: float = 0.0
    label: Optional[str] = None


@dataclass
class TrendResult:
    """Trend analysis result."""
    trend_type: TrendType = TrendType.STABLE
    slope: float = 0.0
    intercept: float = 0.0
    r_squared: float = 0.0


@dataclass
class SeasonalResult:
    """Seasonality analysis result."""
    seasonality: SeasonalityType = SeasonalityType.NONE
    period: int = 0
    strength: float = 0.0
    seasonal_indices: List[float] = field(default_factory=list)


@dataclass
class Forecast:
    """A forecast value."""
    timestamp: datetime = field(default_factory=datetime.now)
    value: float = 0.0
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    confidence: float = 0.95


@dataclass
class DecompositionResult:
    """Time series decomposition."""
    trend: List[float] = field(default_factory=list)
    seasonal: List[float] = field(default_factory=list)
    residual: List[float] = field(default_factory=list)


# =============================================================================
# TIME SERIES STORE
# =============================================================================

class TimeSeriesStore:
    """Store for time series data."""

    def __init__(self):
        self._points: List[TimePoint] = []

    def add(
        self,
        value: float,
        timestamp: Optional[datetime] = None
    ) -> TimePoint:
        """Add a point."""
        point = TimePoint(
            timestamp=timestamp or datetime.now(),
            value=value
        )
        self._points.append(point)
        return point

    def all_points(self) -> List[TimePoint]:
        """Get all points sorted by time."""
        return sorted(self._points, key=lambda p: p.timestamp)

    def values(self) -> List[float]:
        """Get all values in time order."""
        return [p.value for p in self.all_points()]

    def timestamps(self) -> List[datetime]:
        """Get all timestamps."""
        return [p.timestamp for p in self.all_points()]

    def length(self) -> int:
        """Get series length."""
        return len(self._points)


# =============================================================================
# MOVING AVERAGE
# =============================================================================

class MovingAverage:
    """Moving average calculations."""

    def simple(self, values: List[float], window: int = 3) -> List[float]:
        """Simple moving average."""
        if not values or window <= 0:
            return []

        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            window_vals = values[start:i + 1]
            result.append(sum(window_vals) / len(window_vals))

        return result

    def weighted(self, values: List[float], window: int = 3) -> List[float]:
        """Weighted moving average."""
        if not values or window <= 0:
            return []

        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            window_vals = values[start:i + 1]
            weights = list(range(1, len(window_vals) + 1))

            weighted_sum = sum(v * w for v, w in zip(window_vals, weights))
            weight_sum = sum(weights)

            result.append(weighted_sum / weight_sum)

        return result

    def exponential(self, values: List[float], alpha: float = 0.3) -> List[float]:
        """Exponential moving average."""
        if not values:
            return []

        result = [values[0]]

        for i in range(1, len(values)):
            ema = alpha * values[i] + (1 - alpha) * result[-1]
            result.append(ema)

        return result


# =============================================================================
# TREND ANALYZER
# =============================================================================

class TrendAnalyzer:
    """Analyze trends in time series."""

    def linear_regression(self, values: List[float]) -> TrendResult:
        """Fit linear regression."""
        if len(values) < 2:
            return TrendResult()

        n = len(values)
        x = list(range(n))

        mean_x = sum(x) / n
        mean_y = sum(values) / n

        # Calculate slope and intercept
        numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            return TrendResult(trend_type=TrendType.STABLE)

        slope = numerator / denominator
        intercept = mean_y - slope * mean_x

        # R-squared
        ss_res = sum((values[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((values[i] - mean_y) ** 2 for i in range(n))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine trend type
        if abs(slope) < 0.01:
            trend_type = TrendType.STABLE
        elif slope > 0:
            trend_type = TrendType.INCREASING
        else:
            trend_type = TrendType.DECREASING

        return TrendResult(
            trend_type=trend_type,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared
        )

    def detect_trend(self, values: List[float]) -> TrendType:
        """Detect trend type."""
        result = self.linear_regression(values)
        return result.trend_type


# =============================================================================
# SEASONALITY ANALYZER
# =============================================================================

class SeasonalityAnalyzer:
    """Analyze seasonality in time series."""

    def autocorrelation(self, values: List[float], lag: int) -> float:
        """Calculate autocorrelation at given lag."""
        if len(values) <= lag:
            return 0.0

        n = len(values)
        mean = sum(values) / n

        numerator = sum(
            (values[i] - mean) * (values[i - lag] - mean)
            for i in range(lag, n)
        )

        denominator = sum((v - mean) ** 2 for v in values)

        return numerator / denominator if denominator > 0 else 0.0

    def find_period(self, values: List[float], max_lag: int = 50) -> int:
        """Find dominant period."""
        if len(values) < max_lag:
            max_lag = len(values) // 2

        autocorrs = []
        for lag in range(1, max_lag + 1):
            ac = self.autocorrelation(values, lag)
            autocorrs.append((lag, ac))

        # Find first significant peak
        for i in range(1, len(autocorrs) - 1):
            if autocorrs[i][1] > autocorrs[i-1][1] and autocorrs[i][1] > autocorrs[i+1][1]:
                if autocorrs[i][1] > 0.3:  # Significance threshold
                    return autocorrs[i][0]

        return 0

    def seasonal_indices(self, values: List[float], period: int) -> List[float]:
        """Calculate seasonal indices."""
        if period <= 0 or len(values) < period:
            return []

        n_periods = len(values) // period
        indices = [0.0] * period

        for i in range(period):
            period_values = [
                values[i + j * period]
                for j in range(n_periods)
                if i + j * period < len(values)
            ]
            indices[i] = sum(period_values) / len(period_values) if period_values else 0

        # Normalize
        mean_idx = sum(indices) / len(indices)
        if mean_idx > 0:
            indices = [idx / mean_idx for idx in indices]

        return indices

    def analyze(self, values: List[float]) -> SeasonalResult:
        """Analyze seasonality."""
        period = self.find_period(values)

        if period == 0:
            return SeasonalResult()

        indices = self.seasonal_indices(values, period)

        # Determine seasonality type
        if 5 <= period <= 8:
            seasonality = SeasonalityType.WEEKLY
        elif 28 <= period <= 32:
            seasonality = SeasonalityType.MONTHLY
        elif 360 <= period <= 370:
            seasonality = SeasonalityType.YEARLY
        else:
            seasonality = SeasonalityType.DAILY

        # Strength: variance of indices
        if indices:
            mean_idx = sum(indices) / len(indices)
            strength = math.sqrt(sum((idx - mean_idx) ** 2 for idx in indices) / len(indices))
        else:
            strength = 0.0

        return SeasonalResult(
            seasonality=seasonality,
            period=period,
            strength=strength,
            seasonal_indices=indices
        )


# =============================================================================
# FORECASTER
# =============================================================================

class Forecaster:
    """Time series forecasting."""

    def __init__(self):
        self._moving_avg = MovingAverage()

    def naive(self, values: List[float], steps: int = 1) -> List[Forecast]:
        """Naive forecast (last value)."""
        if not values:
            return []

        last_value = values[-1]

        return [
            Forecast(
                timestamp=datetime.now() + timedelta(hours=i),
                value=last_value
            )
            for i in range(1, steps + 1)
        ]

    def moving_average(
        self,
        values: List[float],
        steps: int = 1,
        window: int = 3
    ) -> List[Forecast]:
        """Moving average forecast."""
        if not values:
            return []

        # Forecast is average of last window values
        last_window = values[-window:]
        forecast_value = sum(last_window) / len(last_window)

        return [
            Forecast(
                timestamp=datetime.now() + timedelta(hours=i),
                value=forecast_value
            )
            for i in range(1, steps + 1)
        ]

    def exponential_smoothing(
        self,
        values: List[float],
        steps: int = 1,
        alpha: float = 0.3
    ) -> List[Forecast]:
        """Simple exponential smoothing forecast."""
        if not values:
            return []

        # Fit EMA
        ema = self._moving_avg.exponential(values, alpha)
        forecast_value = ema[-1] if ema else values[-1]

        return [
            Forecast(
                timestamp=datetime.now() + timedelta(hours=i),
                value=forecast_value
            )
            for i in range(1, steps + 1)
        ]

    def holt_linear(
        self,
        values: List[float],
        steps: int = 1,
        alpha: float = 0.3,
        beta: float = 0.1
    ) -> List[Forecast]:
        """Holt's linear trend method."""
        if len(values) < 2:
            return self.naive(values, steps)

        # Initialize
        level = values[0]
        trend = values[1] - values[0]

        # Fit
        for value in values[1:]:
            prev_level = level
            level = alpha * value + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        # Forecast
        forecasts = []
        for i in range(1, steps + 1):
            forecast_value = level + i * trend
            forecasts.append(Forecast(
                timestamp=datetime.now() + timedelta(hours=i),
                value=forecast_value
            ))

        return forecasts


# =============================================================================
# DECOMPOSER
# =============================================================================

class Decomposer:
    """Time series decomposition."""

    def __init__(self):
        self._moving_avg = MovingAverage()

    def decompose(
        self,
        values: List[float],
        period: int = 7
    ) -> DecompositionResult:
        """Additive decomposition."""
        if len(values) < period * 2:
            return DecompositionResult()

        # Trend: centered moving average
        trend = self._moving_avg.simple(values, period)

        # Pad trend to match length
        while len(trend) < len(values):
            trend.insert(0, trend[0])

        # Detrended
        detrended = [v - t for v, t in zip(values, trend)]

        # Seasonal indices
        n_periods = len(values) // period
        seasonal = [0.0] * len(values)

        for i in range(period):
            period_values = [
                detrended[i + j * period]
                for j in range(n_periods)
                if i + j * period < len(detrended)
            ]
            avg = sum(period_values) / len(period_values) if period_values else 0

            for j in range(n_periods):
                idx = i + j * period
                if idx < len(seasonal):
                    seasonal[idx] = avg

        # Residual
        residual = [
            v - t - s
            for v, t, s in zip(values, trend, seasonal)
        ]

        return DecompositionResult(
            trend=trend,
            seasonal=seasonal,
            residual=residual
        )


# =============================================================================
# TIME SERIES ANALYZER
# =============================================================================

class TimeSeriesAnalyzer:
    """
    Time Series Analyzer for BAEL.

    Advanced time series analysis and forecasting.
    """

    def __init__(self):
        self._store = TimeSeriesStore()
        self._moving_avg = MovingAverage()
        self._trend = TrendAnalyzer()
        self._seasonal = SeasonalityAnalyzer()
        self._forecaster = Forecaster()
        self._decomposer = Decomposer()

    # -------------------------------------------------------------------------
    # DATA
    # -------------------------------------------------------------------------

    def add_point(
        self,
        value: float,
        timestamp: Optional[datetime] = None
    ) -> TimePoint:
        """Add a data point."""
        return self._store.add(value, timestamp)

    def add_values(self, values: List[float]) -> None:
        """Add multiple values."""
        base_time = datetime.now()
        for i, value in enumerate(values):
            timestamp = base_time + timedelta(hours=i)
            self._store.add(value, timestamp)

    def all_points(self) -> List[TimePoint]:
        """Get all points."""
        return self._store.all_points()

    def values(self) -> List[float]:
        """Get all values."""
        return self._store.values()

    # -------------------------------------------------------------------------
    # SMOOTHING
    # -------------------------------------------------------------------------

    def smooth_sma(self, window: int = 3) -> List[float]:
        """Simple moving average."""
        return self._moving_avg.simple(self._store.values(), window)

    def smooth_wma(self, window: int = 3) -> List[float]:
        """Weighted moving average."""
        return self._moving_avg.weighted(self._store.values(), window)

    def smooth_ema(self, alpha: float = 0.3) -> List[float]:
        """Exponential moving average."""
        return self._moving_avg.exponential(self._store.values(), alpha)

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def analyze_trend(self) -> TrendResult:
        """Analyze trend."""
        return self._trend.linear_regression(self._store.values())

    def analyze_seasonality(self) -> SeasonalResult:
        """Analyze seasonality."""
        return self._seasonal.analyze(self._store.values())

    def decompose(self, period: int = 7) -> DecompositionResult:
        """Decompose time series."""
        return self._decomposer.decompose(self._store.values(), period)

    # -------------------------------------------------------------------------
    # FORECASTING
    # -------------------------------------------------------------------------

    def forecast(
        self,
        steps: int = 1,
        method: ForecastMethod = ForecastMethod.EXPONENTIAL
    ) -> List[Forecast]:
        """Generate forecast."""
        values = self._store.values()

        if method == ForecastMethod.NAIVE:
            return self._forecaster.naive(values, steps)
        elif method == ForecastMethod.MOVING_AVERAGE:
            return self._forecaster.moving_average(values, steps)
        elif method == ForecastMethod.EXPONENTIAL:
            return self._forecaster.exponential_smoothing(values, steps)
        elif method == ForecastMethod.HOLT_WINTERS:
            return self._forecaster.holt_linear(values, steps)

        return []

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def statistics(self) -> Dict[str, float]:
        """Get basic statistics."""
        values = self._store.values()

        if not values:
            return {}

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)

        sorted_vals = sorted(values)
        median = sorted_vals[len(sorted_vals) // 2]

        return {
            "count": len(values),
            "mean": mean,
            "std": std,
            "min": min(values),
            "max": max(values),
            "median": median,
            "range": max(values) - min(values)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Time Series Analyzer."""
    print("=" * 70)
    print("BAEL - TIME SERIES ANALYZER DEMO")
    print("Advanced Time Series Analysis and Forecasting")
    print("=" * 70)
    print()

    analyzer = TimeSeriesAnalyzer()

    # 1. Generate Time Series
    print("1. GENERATE TIME SERIES:")
    print("-" * 40)

    # Create synthetic data with trend and seasonality
    values = []
    for i in range(100):
        trend = 0.1 * i  # Linear trend
        seasonal = 5 * math.sin(2 * math.pi * i / 7)  # Weekly seasonality
        noise = random.gauss(0, 1)
        values.append(50 + trend + seasonal + noise)

    analyzer.add_values(values)

    print(f"   Generated {len(analyzer.values())} points")
    print(f"   With linear trend and weekly seasonality")
    print()

    # 2. Basic Statistics
    print("2. BASIC STATISTICS:")
    print("-" * 40)

    stats = analyzer.statistics()
    for key, value in stats.items():
        print(f"   {key}: {value:.2f}")
    print()

    # 3. Smoothing
    print("3. SMOOTHING:")
    print("-" * 40)

    sma = analyzer.smooth_sma(window=5)
    wma = analyzer.smooth_wma(window=5)
    ema = analyzer.smooth_ema(alpha=0.3)

    print(f"   Simple MA (window=5): last values = {[f'{v:.2f}' for v in sma[-3:]]}")
    print(f"   Weighted MA (window=5): last values = {[f'{v:.2f}' for v in wma[-3:]]}")
    print(f"   Exponential MA (alpha=0.3): last values = {[f'{v:.2f}' for v in ema[-3:]]}")
    print()

    # 4. Trend Analysis
    print("4. TREND ANALYSIS:")
    print("-" * 40)

    trend = analyzer.analyze_trend()
    print(f"   Trend type: {trend.trend_type.value}")
    print(f"   Slope: {trend.slope:.4f}")
    print(f"   Intercept: {trend.intercept:.2f}")
    print(f"   R-squared: {trend.r_squared:.4f}")
    print()

    # 5. Seasonality Analysis
    print("5. SEASONALITY ANALYSIS:")
    print("-" * 40)

    seasonal = analyzer.analyze_seasonality()
    print(f"   Seasonality: {seasonal.seasonality.value}")
    print(f"   Period: {seasonal.period}")
    print(f"   Strength: {seasonal.strength:.4f}")
    if seasonal.seasonal_indices:
        print(f"   Indices: {[f'{i:.2f}' for i in seasonal.seasonal_indices[:7]]}")
    print()

    # 6. Decomposition
    print("6. DECOMPOSITION:")
    print("-" * 40)

    decomp = analyzer.decompose(period=7)
    print(f"   Trend component: {len(decomp.trend)} values")
    print(f"   Seasonal component: {len(decomp.seasonal)} values")
    print(f"   Residual component: {len(decomp.residual)} values")

    if decomp.residual:
        residual_std = math.sqrt(sum(r**2 for r in decomp.residual) / len(decomp.residual))
        print(f"   Residual std: {residual_std:.4f}")
    print()

    # 7. Forecasting
    print("7. FORECASTING:")
    print("-" * 40)

    methods = [
        ForecastMethod.NAIVE,
        ForecastMethod.MOVING_AVERAGE,
        ForecastMethod.EXPONENTIAL,
        ForecastMethod.HOLT_WINTERS
    ]

    for method in methods:
        forecasts = analyzer.forecast(steps=3, method=method)
        values_str = [f"{f.value:.2f}" for f in forecasts]
        print(f"   {method.value}: {values_str}")
    print()

    # 8. Summary
    print("8. SUMMARY:")
    print("-" * 40)

    print(f"   Time series length: {analyzer.statistics()['count']:.0f}")
    print(f"   Detected trend: {analyzer.analyze_trend().trend_type.value}")
    print(f"   Detected seasonality: {analyzer.analyze_seasonality().seasonality.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Time Series Analyzer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
