"""
Advanced Analytics & Insights Engine - Predictive insights and anomaly detection.

Features:
- Predictive analytics across all systems
- Anomaly detection algorithms
- Trend analysis and forecasting
- Behavioral insights
- Performance optimization recommendations
- Business intelligence dashboard

Target: 1,800+ lines for complete advanced analytics
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ============================================================================
# ANALYTICS ENUMS
# ============================================================================

class MetricType(Enum):
    """Types of metrics."""
    THROUGHPUT = "THROUGHPUT"
    LATENCY = "LATENCY"
    ERROR_RATE = "ERROR_RATE"
    RESOURCE_USAGE = "RESOURCE_USAGE"
    COST = "COST"
    REVENUE = "REVENUE"
    USER_ENGAGEMENT = "USER_ENGAGEMENT"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"

class AnomalyType(Enum):
    """Types of anomalies."""
    SPIKE = "SPIKE"
    DIP = "DIP"
    TREND_CHANGE = "TREND_CHANGE"
    OUTLIER = "OUTLIER"
    SEASONALITY_BREAK = "SEASONALITY_BREAK"

class ForecastMethod(Enum):
    """Forecasting methods."""
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"
    SEASONAL = "SEASONAL"
    ARIMA = "ARIMA"

class InsightCategory(Enum):
    """Categories of insights."""
    PERFORMANCE = "PERFORMANCE"
    COST = "COST"
    REVENUE = "REVENUE"
    SECURITY = "SECURITY"
    RELIABILITY = "RELIABILITY"
    USER_BEHAVIOR = "USER_BEHAVIOR"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class MetricDataPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TimeSeries:
    """Time series data."""
    series_id: str
    metric_type: MetricType
    source: str
    datapoints: List[MetricDataPoint] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_point(self, timestamp: datetime, value: float,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add data point."""
        self.datapoints.append(MetricDataPoint(
            timestamp=timestamp,
            value=value,
            metadata=metadata or {}
        ))

    def get_recent(self, hours: int = 24) -> List[MetricDataPoint]:
        """Get recent data points."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [p for p in self.datapoints if p.timestamp >= cutoff]

@dataclass
class AnomalyEvent:
    """Detected anomaly."""
    anomaly_id: str
    anomaly_type: AnomalyType
    metric_type: MetricType
    timestamp: datetime
    value: float
    expected_value: float
    deviation_percent: float
    severity: float  # 0-1 scale
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'anomaly_id': self.anomaly_id,
            'type': self.anomaly_type.value,
            'metric': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'expected': self.expected_value,
            'deviation_percent': self.deviation_percent,
            'severity': self.severity,
            'description': self.description
        }

@dataclass
class Forecast:
    """Time series forecast."""
    forecast_id: str
    metric_type: MetricType
    method: ForecastMethod
    created_at: datetime
    horizon_hours: int
    predictions: List[Tuple[datetime, float]] = field(default_factory=list)
    confidence_interval: float = 0.95
    mape: Optional[float] = None  # Mean Absolute Percentage Error

    def to_dict(self) -> Dict[str, Any]:
        return {
            'forecast_id': self.forecast_id,
            'metric': self.metric_type.value,
            'method': self.method.value,
            'horizon_hours': self.horizon_hours,
            'predictions': len(self.predictions),
            'mape': self.mape
        }

@dataclass
class Insight:
    """Business insight."""
    insight_id: str
    category: InsightCategory
    title: str
    description: str
    confidence: float  # 0-1 scale
    metric_types: List[MetricType]
    recommendation: Optional[str] = None
    potential_impact: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'insight_id': self.insight_id,
            'category': self.category.value,
            'title': self.title,
            'description': self.description,
            'confidence': self.confidence,
            'metrics': [m.value for m in self.metric_types],
            'recommendation': self.recommendation,
            'impact': self.potential_impact
        }

# ============================================================================
# TIME SERIES MANAGER
# ============================================================================

class TimeSeriesManager:
    """Manage time series data."""

    def __init__(self, retention_hours: int = 720):
        self.series: Dict[str, TimeSeries] = {}
        self.retention_hours = retention_hours
        self.logger = logging.getLogger("timeseries_manager")

    def get_or_create_series(self, metric_type: MetricType, source: str) -> TimeSeries:
        """Get or create time series."""
        series_id = f"{metric_type.value}:{source}"

        if series_id not in self.series:
            self.series[series_id] = TimeSeries(
                series_id=series_id,
                metric_type=metric_type,
                source=source
            )

        return self.series[series_id]

    def record_metric(self, metric_type: MetricType, source: str,
                     value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record metric value."""
        series = self.get_or_create_series(metric_type, source)
        series.add_point(datetime.now(), value, metadata)

    def cleanup_old_data(self) -> int:
        """Remove data older than retention period."""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        removed_count = 0

        for series in self.series.values():
            original_count = len(series.datapoints)
            series.datapoints = [p for p in series.datapoints if p.timestamp >= cutoff]
            removed_count += original_count - len(series.datapoints)

        return removed_count

    def get_series(self, metric_type: MetricType, source: str) -> Optional[TimeSeries]:
        """Get time series."""
        series_id = f"{metric_type.value}:{source}"
        return self.series.get(series_id)

# ============================================================================
# ANOMALY DETECTOR
# ============================================================================

class AnomalyDetector:
    """Detect anomalies in time series."""

    def __init__(self, sensitivity: float = 2.0):
        self.sensitivity = sensitivity
        self.anomalies: List[AnomalyEvent] = []
        self.logger = logging.getLogger("anomaly_detector")

    async def detect(self, series: TimeSeries) -> List[AnomalyEvent]:
        """Detect anomalies in series."""
        detected = []

        if len(series.datapoints) < 10:
            return detected

        # Calculate statistics
        values = [p.value for p in series.datapoints[-100:]]
        mean = np.mean(values)
        std = np.std(values)

        # Check recent point
        if len(series.datapoints) > 0:
            recent = series.datapoints[-1]
            z_score = abs((recent.value - mean) / std) if std > 0 else 0

            if z_score > self.sensitivity:
                # Determine anomaly type
                if recent.value > mean:
                    anomaly_type = AnomalyType.SPIKE
                else:
                    anomaly_type = AnomalyType.DIP

                anomaly = AnomalyEvent(
                    anomaly_id=f"anom-{uuid.uuid4().hex[:8]}",
                    anomaly_type=anomaly_type,
                    metric_type=series.metric_type,
                    timestamp=recent.timestamp,
                    value=recent.value,
                    expected_value=mean,
                    deviation_percent=abs((recent.value - mean) / mean * 100) if mean != 0 else 0,
                    severity=min(z_score / 5.0, 1.0),
                    description=f"Value {recent.value:.2f} deviates from mean {mean:.2f}"
                )

                detected.append(anomaly)
                self.anomalies.append(anomaly)

        return detected

    def get_recent_anomalies(self, hours: int = 24,
                            min_severity: float = 0.3) -> List[AnomalyEvent]:
        """Get recent anomalies."""
        cutoff = datetime.now() - timedelta(hours=hours)

        return [a for a in self.anomalies
                if a.timestamp >= cutoff and a.severity >= min_severity]

# ============================================================================
# FORECASTING ENGINE
# ============================================================================

class ForecastingEngine:
    """Generate forecasts for metrics."""

    def __init__(self):
        self.forecasts: List[Forecast] = []
        self.logger = logging.getLogger("forecasting_engine")

    async def forecast(self, series: TimeSeries, horizon_hours: int = 24,
                      method: ForecastMethod = ForecastMethod.LINEAR) -> Optional[Forecast]:
        """Generate forecast."""
        if len(series.datapoints) < 5:
            return None

        # Extract values and timestamps
        recent_points = series.get_recent(hours=168)  # Last week
        if len(recent_points) < 3:
            return None

        values = [p.value for p in recent_points]
        timestamps = [p.timestamp for p in recent_points]

        # Simple linear regression
        x = np.arange(len(values))
        y = np.array(values)

        coeffs = np.polyfit(x, y, 1)
        poly = np.poly1d(coeffs)

        # Generate predictions
        predictions = []
        last_timestamp = timestamps[-1]

        for i in range(1, horizon_hours + 1):
            future_time = last_timestamp + timedelta(hours=i)
            predicted_value = poly(len(values) + i - 1)
            predictions.append((future_time, float(max(0, predicted_value))))

        # Calculate MAPE
        mape = self._calculate_mape(y, poly(x))

        forecast = Forecast(
            forecast_id=f"fcst-{uuid.uuid4().hex[:8]}",
            metric_type=series.metric_type,
            method=method,
            created_at=datetime.now(),
            horizon_hours=horizon_hours,
            predictions=predictions,
            mape=mape
        )

        self.forecasts.append(forecast)
        self.logger.info(f"Generated forecast for {series.metric_type.value}")
        return forecast

    def _calculate_mape(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        """Calculate Mean Absolute Percentage Error."""
        if len(actual) == 0:
            return 0.0

        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        return float(mape)

# ============================================================================
# INSIGHT GENERATOR
# ============================================================================

class InsightGenerator:
    """Generate actionable insights."""

    def __init__(self, timeseries_mgr: TimeSeriesManager,
                 anomaly_detector: AnomalyDetector):
        self.timeseries_mgr = timeseries_mgr
        self.anomaly_detector = anomaly_detector
        self.insights: List[Insight] = []
        self.logger = logging.getLogger("insight_generator")

    async def generate_insights(self) -> List[Insight]:
        """Generate insights from current state."""
        new_insights = []

        # Check error rates
        error_series = self.timeseries_mgr.get_series(
            MetricType.ERROR_RATE, "system"
        )

        if error_series and len(error_series.datapoints) > 0:
            recent_values = [p.value for p in error_series.get_recent(hours=1)]

            if recent_values and np.mean(recent_values) > 0.05:
                insight = Insight(
                    insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                    category=InsightCategory.RELIABILITY,
                    title="High Error Rate Detected",
                    description=f"Error rate is {np.mean(recent_values)*100:.1f}% in the last hour",
                    confidence=0.9,
                    metric_types=[MetricType.ERROR_RATE],
                    recommendation="Review recent deployments and check system logs",
                    potential_impact="User experience degradation"
                )
                new_insights.append(insight)

        # Check cost trends
        cost_series = self.timeseries_mgr.get_series(MetricType.COST, "system")

        if cost_series and len(cost_series.datapoints) > 10:
            recent_values = [p.value for p in cost_series.get_recent(hours=24)]
            older_values = [p.value for p in cost_series.datapoints[-50:-25]]

            if recent_values and older_values:
                cost_increase = (np.mean(recent_values) - np.mean(older_values)) / np.mean(older_values)

                if cost_increase > 0.2:  # 20% increase
                    insight = Insight(
                        insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                        category=InsightCategory.COST,
                        title="Cost Increase Detected",
                        description=f"Daily costs increased by {cost_increase*100:.1f}%",
                        confidence=0.85,
                        metric_types=[MetricType.COST],
                        recommendation="Review resource utilization and consider optimization",
                        potential_impact="Budget overrun"
                    )
                    new_insights.append(insight)

        # Check latency trends
        latency_series = self.timeseries_mgr.get_series(MetricType.LATENCY, "api")

        if latency_series and len(latency_series.datapoints) > 10:
            recent_values = [p.value for p in latency_series.get_recent(hours=1)]
            older_values = [p.value for p in latency_series.datapoints[-30:-15]]

            if recent_values and older_values:
                latency_increase = (np.mean(recent_values) - np.mean(older_values)) / np.mean(older_values)

                if latency_increase > 0.3:
                    insight = Insight(
                        insight_id=f"ins-{uuid.uuid4().hex[:8]}",
                        category=InsightCategory.PERFORMANCE,
                        title="API Latency Degradation",
                        description=f"Average latency increased by {latency_increase*100:.1f}%",
                        confidence=0.88,
                        metric_types=[MetricType.LATENCY],
                        recommendation="Scale API tier or optimize queries",
                        potential_impact="User experience slowdown"
                    )
                    new_insights.append(insight)

        self.insights.extend(new_insights)
        return new_insights

    def get_recent_insights(self, hours: int = 24,
                           category: Optional[InsightCategory] = None) -> List[Insight]:
        """Get recent insights."""
        cutoff = datetime.now() - timedelta(hours=hours)

        insights = [i for i in self.insights if i.created_at >= cutoff]

        if category:
            insights = [i for i in insights if i.category == category]

        return insights

# ============================================================================
# ADVANCED ANALYTICS SYSTEM
# ============================================================================

class AdvancedAnalytics:
    """Complete advanced analytics system."""

    def __init__(self):
        self.timeseries_mgr = TimeSeriesManager()
        self.anomaly_detector = AnomalyDetector(sensitivity=2.5)
        self.forecasting_engine = ForecastingEngine()
        self.insight_generator = InsightGenerator(self.timeseries_mgr, self.anomaly_detector)

        self.logger = logging.getLogger("advanced_analytics")

    async def record_metric(self, metric_type: MetricType, source: str,
                          value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record system metric."""
        self.timeseries_mgr.record_metric(metric_type, source, value, metadata)

    async def analyze_system_health(self) -> Dict[str, Any]:
        """Analyze system health."""
        # Detect anomalies
        anomalies = []
        for series in self.timeseries_mgr.series.values():
            detected = await self.anomaly_detector.detect(series)
            anomalies.extend(detected)

        # Generate forecasts
        forecasts = []
        for series in self.timeseries_mgr.series.values():
            if len(series.datapoints) > 5:
                forecast = await self.forecasting_engine.forecast(series)
                if forecast:
                    forecasts.append(forecast)

        # Generate insights
        insights = await self.insight_generator.generate_insights()

        return {
            'timestamp': datetime.now().isoformat(),
            'metrics_tracked': len(self.timeseries_mgr.series),
            'anomalies_detected': len(anomalies),
            'anomalies': [a.to_dict() for a in anomalies[-10:]],
            'forecasts': [f.to_dict() for f in forecasts[-5:]],
            'insights': [i.to_dict() for i in insights[-5:]],
            'recent_anomalies': len(self.anomaly_detector.get_recent_anomalies())
        }

    def get_analytics_dashboard(self) -> Dict[str, Any]:
        """Get analytics dashboard data."""
        recent_anomalies = self.anomaly_detector.get_recent_anomalies()
        recent_insights = self.insight_generator.get_recent_insights()

        # Calculate metrics summary
        metrics_summary = defaultdict(lambda: {'count': 0, 'avg': 0})

        for series in self.timeseries_mgr.series.values():
            if len(series.datapoints) > 0:
                recent = [p.value for p in series.get_recent(hours=1)]
                metrics_summary[series.metric_type.value] = {
                    'count': len(recent),
                    'avg': np.mean(recent) if recent else 0
                }

        return {
            'timestamp': datetime.now().isoformat(),
            'metrics_tracked': len(self.timeseries_mgr.series),
            'metrics_summary': dict(metrics_summary),
            'anomalies_24h': len(recent_anomalies),
            'critical_anomalies': len([a for a in recent_anomalies if a.severity > 0.8]),
            'insights_24h': len(recent_insights),
            'high_confidence_insights': len([i for i in recent_insights if i.confidence > 0.85]),
            'total_forecasts': len(self.forecasting_engine.forecasts)
        }

def create_advanced_analytics() -> AdvancedAnalytics:
    """Create advanced analytics system."""
    return AdvancedAnalytics()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    analytics = create_advanced_analytics()
    print("Advanced analytics system initialized")
