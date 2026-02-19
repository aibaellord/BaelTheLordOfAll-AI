"""
BAEL Predictive Analytics Engine
=================================

Advanced prediction and forecasting capabilities.

"The future is not written - it is computed." — Ba'el
"""

import asyncio
import json
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union,
    TypeVar, Generic
)


class PredictionType(Enum):
    """Types of predictions."""
    TIME_SERIES = "time_series"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    ANOMALY = "anomaly"
    CLUSTERING = "clustering"
    SEQUENCE = "sequence"
    RECOMMENDATION = "recommendation"
    CAUSAL = "causal"


class ModelType(Enum):
    """Types of predictive models."""
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    EXPONENTIAL = "exponential"
    ARIMA = "arima"
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    ENSEMBLE = "ensemble"
    BAYESIAN = "bayesian"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOST = "gradient_boost"


class ConfidenceLevel(Enum):
    """Confidence levels for predictions."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.9
    CERTAIN = 0.99


class AnomalyType(Enum):
    """Types of anomalies."""
    POINT = "point"           # Single outlier
    COLLECTIVE = "collective"  # Group of anomalies
    CONTEXTUAL = "contextual"  # Anomaly in context
    SEASONAL = "seasonal"      # Deviation from pattern
    TREND = "trend"           # Change in trend


@dataclass
class DataPoint:
    """A single data point."""
    timestamp: datetime
    value: float
    features: Dict[str, Any] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)


@dataclass
class TimeSeries:
    """Time series data."""
    name: str
    points: List[DataPoint] = field(default_factory=list)
    frequency: Optional[str] = None  # daily, hourly, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_point(self, timestamp: datetime, value: float, **kwargs) -> None:
        self.points.append(DataPoint(timestamp, value, **kwargs))

    @property
    def values(self) -> List[float]:
        return [p.value for p in self.points]

    @property
    def timestamps(self) -> List[datetime]:
        return [p.timestamp for p in self.points]


@dataclass
class Prediction:
    """A prediction result."""
    predicted_value: Any
    confidence: float
    prediction_type: PredictionType
    model_used: ModelType
    timestamp: datetime = field(default_factory=datetime.now)
    interval: Optional[Tuple[float, float]] = None  # Confidence interval
    features_importance: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Anomaly:
    """Detected anomaly."""
    data_point: DataPoint
    anomaly_type: AnomalyType
    severity: float  # 0-1
    confidence: float
    expected_value: Optional[float] = None
    deviation: Optional[float] = None
    explanation: str = ""


@dataclass
class Forecast:
    """Forecast result with multiple predictions."""
    predictions: List[Prediction]
    horizon: int
    start_time: datetime
    end_time: datetime
    model_type: ModelType
    metrics: Dict[str, float] = field(default_factory=dict)


class StatisticalAnalyzer:
    """Statistical analysis utilities."""

    @staticmethod
    def mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0

    @staticmethod
    def variance(values: List[float]) -> float:
        if not values:
            return 0
        m = StatisticalAnalyzer.mean(values)
        return sum((x - m) ** 2 for x in values) / len(values)

    @staticmethod
    def std_dev(values: List[float]) -> float:
        return math.sqrt(StatisticalAnalyzer.variance(values))

    @staticmethod
    def percentile(values: List[float], p: float) -> float:
        if not values:
            return 0
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_values[int(k)]
        return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)

    @staticmethod
    def z_score(value: float, mean: float, std: float) -> float:
        if std == 0:
            return 0
        return (value - mean) / std

    @staticmethod
    def correlation(x: List[float], y: List[float]) -> float:
        if len(x) != len(y) or not x:
            return 0

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        denom_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if denom_x == 0 or denom_y == 0:
            return 0

        return numerator / (denom_x * denom_y)

    @staticmethod
    def moving_average(values: List[float], window: int) -> List[float]:
        if len(values) < window:
            return values

        result = []
        for i in range(len(values) - window + 1):
            result.append(sum(values[i:i+window]) / window)

        return result

    @staticmethod
    def exponential_smoothing(values: List[float], alpha: float = 0.3) -> List[float]:
        if not values:
            return []

        result = [values[0]]
        for i in range(1, len(values)):
            result.append(alpha * values[i] + (1 - alpha) * result[-1])

        return result


class TimeSeriesPredictor:
    """Time series prediction models."""

    def __init__(self):
        self.analyzer = StatisticalAnalyzer()

    async def predict_linear(
        self,
        series: TimeSeries,
        horizon: int = 5
    ) -> Forecast:
        """Linear trend prediction."""
        values = series.values
        n = len(values)

        if n < 2:
            raise ValueError("Need at least 2 data points")

        # Simple linear regression
        x = list(range(n))
        mean_x = sum(x) / n
        mean_y = sum(values) / n

        numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((xi - mean_x) ** 2 for xi in x)

        slope = numerator / denominator if denominator else 0
        intercept = mean_y - slope * mean_x

        # Forecast
        predictions = []
        last_time = series.timestamps[-1] if series.timestamps else datetime.now()

        for i in range(1, horizon + 1):
            future_x = n + i - 1
            predicted_value = slope * future_x + intercept

            # Calculate confidence interval
            residuals = [values[j] - (slope * j + intercept) for j in range(n)]
            std_error = StatisticalAnalyzer.std_dev(residuals)
            interval = (predicted_value - 1.96 * std_error, predicted_value + 1.96 * std_error)

            predictions.append(Prediction(
                predicted_value=predicted_value,
                confidence=0.7,
                prediction_type=PredictionType.TIME_SERIES,
                model_used=ModelType.LINEAR,
                interval=interval
            ))

        return Forecast(
            predictions=predictions,
            horizon=horizon,
            start_time=last_time,
            end_time=last_time + timedelta(hours=horizon),
            model_type=ModelType.LINEAR,
            metrics={"slope": slope, "intercept": intercept}
        )

    async def predict_exponential_smoothing(
        self,
        series: TimeSeries,
        horizon: int = 5,
        alpha: float = 0.3
    ) -> Forecast:
        """Exponential smoothing prediction."""
        values = series.values
        smoothed = StatisticalAnalyzer.exponential_smoothing(values, alpha)

        if not smoothed:
            raise ValueError("Need data points for prediction")

        # Forecast
        predictions = []
        last_value = smoothed[-1]
        last_time = series.timestamps[-1] if series.timestamps else datetime.now()

        # Calculate trend from recent smoothed values
        if len(smoothed) >= 2:
            trend = smoothed[-1] - smoothed[-2]
        else:
            trend = 0

        for i in range(1, horizon + 1):
            predicted_value = last_value + trend * i * 0.5  # Damped trend

            # Confidence interval
            std = StatisticalAnalyzer.std_dev(values)
            interval = (predicted_value - 1.96 * std * math.sqrt(i),
                       predicted_value + 1.96 * std * math.sqrt(i))

            # Confidence decreases with horizon
            confidence = max(0.4, 0.8 - i * 0.05)

            predictions.append(Prediction(
                predicted_value=predicted_value,
                confidence=confidence,
                prediction_type=PredictionType.TIME_SERIES,
                model_used=ModelType.EXPONENTIAL,
                interval=interval
            ))

        return Forecast(
            predictions=predictions,
            horizon=horizon,
            start_time=last_time,
            end_time=last_time + timedelta(hours=horizon),
            model_type=ModelType.EXPONENTIAL,
            metrics={"alpha": alpha, "last_smoothed": last_value}
        )

    async def predict_arima_like(
        self,
        series: TimeSeries,
        horizon: int = 5,
        p: int = 1,
        d: int = 1,
        q: int = 1
    ) -> Forecast:
        """ARIMA-like prediction (simplified)."""
        values = series.values
        n = len(values)

        if n < p + d + 1:
            raise ValueError(f"Need at least {p + d + 1} data points")

        # Difference series for stationarity
        differenced = [values[i] - values[i-1] for i in range(1, n)] if d > 0 else values

        # Simple AR prediction
        predictions = []
        last_time = series.timestamps[-1] if series.timestamps else datetime.now()

        current = values[-1]
        mean_diff = StatisticalAnalyzer.mean(differenced) if differenced else 0
        std_diff = StatisticalAnalyzer.std_dev(differenced) if differenced else 1

        for i in range(1, horizon + 1):
            # AR component
            predicted_diff = mean_diff * 0.8 ** i
            predicted_value = current + predicted_diff
            current = predicted_value

            # Confidence interval
            margin = 1.96 * std_diff * math.sqrt(i)
            interval = (predicted_value - margin, predicted_value + margin)

            confidence = max(0.3, 0.85 - i * 0.08)

            predictions.append(Prediction(
                predicted_value=predicted_value,
                confidence=confidence,
                prediction_type=PredictionType.TIME_SERIES,
                model_used=ModelType.ARIMA,
                interval=interval
            ))

        return Forecast(
            predictions=predictions,
            horizon=horizon,
            start_time=last_time,
            end_time=last_time + timedelta(hours=horizon),
            model_type=ModelType.ARIMA,
            metrics={"p": p, "d": d, "q": q}
        )


class AnomalyDetector:
    """Anomaly detection engine."""

    def __init__(self, z_threshold: float = 2.5, iqr_multiplier: float = 1.5):
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.analyzer = StatisticalAnalyzer()

    async def detect_statistical(
        self,
        series: TimeSeries
    ) -> List[Anomaly]:
        """Detect anomalies using statistical methods."""
        values = series.values
        if len(values) < 3:
            return []

        anomalies = []
        mean = self.analyzer.mean(values)
        std = self.analyzer.std_dev(values)

        # Z-score method
        for point in series.points:
            z = self.analyzer.z_score(point.value, mean, std) if std > 0 else 0

            if abs(z) > self.z_threshold:
                anomalies.append(Anomaly(
                    data_point=point,
                    anomaly_type=AnomalyType.POINT,
                    severity=min(1.0, abs(z) / (self.z_threshold * 2)),
                    confidence=0.8,
                    expected_value=mean,
                    deviation=abs(point.value - mean),
                    explanation=f"Z-score: {z:.2f} exceeds threshold"
                ))

        return anomalies

    async def detect_iqr(
        self,
        series: TimeSeries
    ) -> List[Anomaly]:
        """Detect anomalies using IQR method."""
        values = series.values
        if len(values) < 4:
            return []

        q1 = self.analyzer.percentile(values, 0.25)
        q3 = self.analyzer.percentile(values, 0.75)
        iqr = q3 - q1

        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr

        anomalies = []
        for point in series.points:
            if point.value < lower_bound or point.value > upper_bound:
                deviation = min(abs(point.value - lower_bound), abs(point.value - upper_bound))

                anomalies.append(Anomaly(
                    data_point=point,
                    anomaly_type=AnomalyType.POINT,
                    severity=min(1.0, deviation / (iqr * 2)) if iqr > 0 else 0.5,
                    confidence=0.75,
                    expected_value=(q1 + q3) / 2,
                    deviation=deviation,
                    explanation=f"Outside IQR bounds [{lower_bound:.2f}, {upper_bound:.2f}]"
                ))

        return anomalies

    async def detect_seasonal(
        self,
        series: TimeSeries,
        period: int = 7
    ) -> List[Anomaly]:
        """Detect seasonal anomalies."""
        values = series.values
        n = len(values)

        if n < period * 2:
            return []

        anomalies = []

        # Calculate expected values per position in cycle
        cycles = defaultdict(list)
        for i, v in enumerate(values):
            cycles[i % period].append(v)

        expected = {pos: self.analyzer.mean(vals) for pos, vals in cycles.items()}
        stds = {pos: self.analyzer.std_dev(vals) for pos, vals in cycles.items()}

        for i, point in enumerate(series.points):
            pos = i % period
            exp = expected[pos]
            std = stds[pos]

            if std > 0:
                z = abs(point.value - exp) / std
                if z > self.z_threshold:
                    anomalies.append(Anomaly(
                        data_point=point,
                        anomaly_type=AnomalyType.SEASONAL,
                        severity=min(1.0, z / (self.z_threshold * 2)),
                        confidence=0.7,
                        expected_value=exp,
                        deviation=abs(point.value - exp),
                        explanation=f"Deviates from seasonal pattern at position {pos}"
                    ))

        return anomalies

    async def detect_trend_change(
        self,
        series: TimeSeries,
        window: int = 5
    ) -> List[Anomaly]:
        """Detect trend changes."""
        values = series.values
        n = len(values)

        if n < window * 2:
            return []

        # Calculate local trends
        anomalies = []

        for i in range(window, n - window):
            left = values[i-window:i]
            right = values[i:i+window]

            left_trend = (left[-1] - left[0]) / window if len(left) > 1 else 0
            right_trend = (right[-1] - right[0]) / window if len(right) > 1 else 0

            # Significant trend change
            if abs(right_trend - left_trend) > StatisticalAnalyzer.std_dev(values) * 0.5:
                point = series.points[i]
                anomalies.append(Anomaly(
                    data_point=point,
                    anomaly_type=AnomalyType.TREND,
                    severity=min(1.0, abs(right_trend - left_trend)),
                    confidence=0.65,
                    explanation=f"Trend change: {left_trend:.2f} -> {right_trend:.2f}"
                ))

        return anomalies


class CausalPredictor:
    """Causal inference and prediction."""

    def __init__(self):
        self.causal_relationships: Dict[str, List[str]] = defaultdict(list)
        self.effect_magnitudes: Dict[Tuple[str, str], float] = {}

    def add_relationship(
        self,
        cause: str,
        effect: str,
        magnitude: float = 1.0
    ) -> None:
        """Add a causal relationship."""
        self.causal_relationships[cause].append(effect)
        self.effect_magnitudes[(cause, effect)] = magnitude

    async def predict_effect(
        self,
        cause: str,
        cause_value_change: float
    ) -> Dict[str, Prediction]:
        """Predict effects of a change in cause."""
        effects = self.causal_relationships.get(cause, [])
        predictions = {}

        for effect in effects:
            magnitude = self.effect_magnitudes.get((cause, effect), 1.0)
            predicted_change = cause_value_change * magnitude

            predictions[effect] = Prediction(
                predicted_value=predicted_change,
                confidence=0.6,
                prediction_type=PredictionType.CAUSAL,
                model_used=ModelType.BAYESIAN,
                features_importance={cause: magnitude}
            )

        return predictions

    async def trace_effects(
        self,
        cause: str,
        depth: int = 3
    ) -> Dict[str, List[str]]:
        """Trace all downstream effects."""
        visited = set()
        effects = defaultdict(list)

        def trace(current: str, level: int, path: List[str]):
            if level > depth or current in visited:
                return
            visited.add(current)

            for effect in self.causal_relationships.get(current, []):
                effects[level].append(effect)
                trace(effect, level + 1, path + [effect])

        trace(cause, 1, [cause])
        return dict(effects)


class PredictiveAnalyticsEngine:
    """
    Main Predictive Analytics Engine

    Combines:
    - Time series prediction
    - Anomaly detection
    - Causal inference
    - Ensemble forecasting
    """

    def __init__(self):
        self.time_series = TimeSeriesPredictor()
        self.anomaly = AnomalyDetector()
        self.causal = CausalPredictor()

        self.series_store: Dict[str, TimeSeries] = {}
        self.prediction_history: List[Prediction] = []

        self.data_dir = Path("data/predictive")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def ingest_series(
        self,
        name: str,
        data: List[Tuple[datetime, float]]
    ) -> TimeSeries:
        """Ingest time series data."""
        series = TimeSeries(name=name)
        for timestamp, value in data:
            series.add_point(timestamp, value)

        self.series_store[name] = series
        return series

    async def forecast(
        self,
        series_name: str,
        horizon: int = 10,
        model: ModelType = ModelType.ENSEMBLE
    ) -> Forecast:
        """Forecast future values."""
        series = self.series_store.get(series_name)
        if not series:
            raise ValueError(f"Series '{series_name}' not found")

        if model == ModelType.ENSEMBLE:
            return await self._ensemble_forecast(series, horizon)
        elif model == ModelType.LINEAR:
            return await self.time_series.predict_linear(series, horizon)
        elif model == ModelType.EXPONENTIAL:
            return await self.time_series.predict_exponential_smoothing(series, horizon)
        elif model == ModelType.ARIMA:
            return await self.time_series.predict_arima_like(series, horizon)
        else:
            return await self.time_series.predict_linear(series, horizon)

    async def _ensemble_forecast(
        self,
        series: TimeSeries,
        horizon: int
    ) -> Forecast:
        """Ensemble forecast using multiple models."""
        # Get predictions from multiple models
        forecasts = []

        try:
            forecasts.append(await self.time_series.predict_linear(series, horizon))
        except Exception:
            pass

        try:
            forecasts.append(await self.time_series.predict_exponential_smoothing(series, horizon))
        except Exception:
            pass

        try:
            forecasts.append(await self.time_series.predict_arima_like(series, horizon))
        except Exception:
            pass

        if not forecasts:
            raise ValueError("No forecasts could be generated")

        # Combine predictions
        combined = []
        for i in range(horizon):
            values = [f.predictions[i].predicted_value for f in forecasts if i < len(f.predictions)]
            confidences = [f.predictions[i].confidence for f in forecasts if i < len(f.predictions)]

            avg_value = sum(values) / len(values)
            avg_conf = sum(confidences) / len(confidences)

            combined.append(Prediction(
                predicted_value=avg_value,
                confidence=avg_conf,
                prediction_type=PredictionType.TIME_SERIES,
                model_used=ModelType.ENSEMBLE,
                metadata={"models_used": len(forecasts)}
            ))

        last_time = series.timestamps[-1] if series.timestamps else datetime.now()

        return Forecast(
            predictions=combined,
            horizon=horizon,
            start_time=last_time,
            end_time=last_time + timedelta(hours=horizon),
            model_type=ModelType.ENSEMBLE,
            metrics={"ensemble_size": len(forecasts)}
        )

    async def detect_anomalies(
        self,
        series_name: str,
        methods: Optional[List[str]] = None
    ) -> List[Anomaly]:
        """Detect anomalies in series."""
        series = self.series_store.get(series_name)
        if not series:
            raise ValueError(f"Series '{series_name}' not found")

        methods = methods or ["statistical", "iqr", "seasonal"]
        all_anomalies = []

        if "statistical" in methods:
            all_anomalies.extend(await self.anomaly.detect_statistical(series))

        if "iqr" in methods:
            all_anomalies.extend(await self.anomaly.detect_iqr(series))

        if "seasonal" in methods:
            all_anomalies.extend(await self.anomaly.detect_seasonal(series))

        if "trend" in methods:
            all_anomalies.extend(await self.anomaly.detect_trend_change(series))

        # Deduplicate by timestamp
        seen = set()
        unique = []
        for a in all_anomalies:
            key = a.data_point.timestamp
            if key not in seen:
                seen.add(key)
                unique.append(a)

        return sorted(unique, key=lambda a: a.severity, reverse=True)

    async def analyze_correlations(
        self,
        series_names: List[str]
    ) -> Dict[Tuple[str, str], float]:
        """Analyze correlations between series."""
        correlations = {}

        for i, name1 in enumerate(series_names):
            for name2 in series_names[i+1:]:
                s1 = self.series_store.get(name1)
                s2 = self.series_store.get(name2)

                if s1 and s2:
                    min_len = min(len(s1.values), len(s2.values))
                    if min_len > 0:
                        corr = StatisticalAnalyzer.correlation(
                            s1.values[:min_len],
                            s2.values[:min_len]
                        )
                        correlations[(name1, name2)] = corr

        return correlations

    async def add_causal_relationship(
        self,
        cause: str,
        effect: str,
        magnitude: float = 1.0
    ) -> None:
        """Add causal relationship."""
        self.causal.add_relationship(cause, effect, magnitude)

    async def predict_causal_effects(
        self,
        cause: str,
        change: float
    ) -> Dict[str, Prediction]:
        """Predict effects of a causal change."""
        return await self.causal.predict_effect(cause, change)

    async def save_state(self, filename: str = "predictive_state.json") -> None:
        """Save engine state."""
        state = {
            "series": {
                name: {
                    "name": s.name,
                    "frequency": s.frequency,
                    "point_count": len(s.points),
                    "metadata": s.metadata
                }
                for name, s in self.series_store.items()
            },
            "prediction_count": len(self.prediction_history),
            "causal_relationships": dict(self.causal.causal_relationships),
            "saved_at": datetime.now().isoformat()
        }

        filepath = self.data_dir / filename
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def get_summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "series_count": len(self.series_store),
            "prediction_count": len(self.prediction_history),
            "causal_relationships": len(self.causal.causal_relationships),
            "capabilities": [
                "time_series_forecasting",
                "anomaly_detection",
                "causal_inference",
                "correlation_analysis",
                "ensemble_prediction"
            ]
        }


# Convenience instance
predictive_engine = PredictiveAnalyticsEngine()
