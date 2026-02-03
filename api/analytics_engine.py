"""
Advanced Analytics Engine for BAEL

Performance metrics, usage analytics, pattern detection, insights generation,
and predictive dashboards.
"""

import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Metric:
    """Single metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


class TimeSeries:
    """Time series data storage and analysis."""

    def __init__(self, name: str, retention_days: int = 30):
        self.name = name
        self.data_points: List[Metric] = []
        self.retention_days = retention_days

    def add_point(self, value: float, tags: Optional[Dict] = None) -> None:
        """Add data point."""
        metric = Metric(
            name=self.name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.data_points.append(metric)
        self._cleanup_old_data()

    def _cleanup_old_data(self) -> None:
        """Remove old data beyond retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        self.data_points = [m for m in self.data_points if m.timestamp >= cutoff]

    def get_statistics(self) -> Dict[str, float]:
        """Calculate statistics."""
        if not self.data_points:
            return {}

        values = [m.value for m in self.data_points]
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "sum": sum(values)
        }

    def get_trend(self, window_size: int = 10) -> Optional[str]:
        """Determine trend direction."""
        if len(self.data_points) < window_size * 2:
            return None

        recent = [m.value for m in self.data_points[-window_size:]]
        older = [m.value for m in self.data_points[-window_size*2:-window_size]]

        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)

        if recent_avg > older_avg * 1.1:
            return "increasing"
        elif recent_avg < older_avg * 0.9:
            return "decreasing"
        return "stable"

    def get_anomalies(self, threshold: float = 2.0) -> List[Metric]:
        """Detect anomalies using standard deviations."""
        stats = self.get_statistics()
        if "stdev" not in stats or stats["stdev"] == 0:
            return []

        mean = stats["mean"]
        stdev = stats["stdev"]

        anomalies = []
        for point in self.data_points:
            z_score = abs((point.value - mean) / stdev)
            if z_score > threshold:
                anomalies.append(point)

        return anomalies


class MetricsCollector:
    """Collects and stores metrics."""

    def __init__(self):
        self.metrics: Dict[str, TimeSeries] = defaultdict(lambda: TimeSeries("metric", 30))

    def record_metric(self, name: str, value: float,
                     tags: Optional[Dict] = None) -> None:
        """Record metric."""
        if name not in self.metrics:
            self.metrics[name] = TimeSeries(name, 30)
        self.metrics[name].add_point(value, tags)

    def get_metrics(self, name_pattern: str) -> Dict[str, Dict]:
        """Get metrics matching pattern."""
        results = {}
        for name, series in self.metrics.items():
            if name_pattern in name:
                results[name] = series.get_statistics()
        return results

    def get_metric_stats(self, name: str) -> Optional[Dict]:
        """Get statistics for metric."""
        if name in self.metrics:
            return self.metrics[name].get_statistics()
        return None


class PatternDetector:
    """Detects patterns in data and behavior."""

    def __init__(self):
        self.patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.pattern_count = 0

    def detect_recurring_pattern(self, data: List[Any], pattern_name: str) -> bool:
        """Detect recurring pattern in data."""
        if len(data) < 3:
            return False

        # Simple pattern detection: repeated sequences
        for i in range(len(data) - 1):
            if data[i] == data[i + 1]:
                if pattern_name not in self.patterns or not self.patterns[pattern_name]:
                    self.patterns[pattern_name].append({
                        "first_observed": datetime.now().isoformat(),
                        "occurrences": 1
                    })
                    self.pattern_count += 1
                    return True
                else:
                    self.patterns[pattern_name][-1]["occurrences"] += 1
                    return True

        return False

    def detect_correlation(self, series1: List[float], series2: List[float]) -> float:
        """Detect correlation between two series."""
        if len(series1) != len(series2) or len(series1) < 2:
            return 0.0

        mean1 = statistics.mean(series1)
        mean2 = statistics.mean(series2)

        numerator = sum(
            (series1[i] - mean1) * (series2[i] - mean2)
            for i in range(len(series1))
        )

        denom1 = statistics.stdev(series1) if len(series1) > 1 else 1
        denom2 = statistics.stdev(series2) if len(series2) > 1 else 1

        if denom1 == 0 or denom2 == 0:
            return 0.0

        return numerator / (denom1 * denom2 * len(series1))

    def get_patterns(self) -> Dict[str, List]:
        """Get detected patterns."""
        return dict(self.patterns)


class InsightGenerator:
    """Generates insights from analytics data."""

    def __init__(self, collector: MetricsCollector, detector: PatternDetector):
        self.collector = collector
        self.detector = detector
        self.insights: List[Dict] = []

    def generate_insights(self) -> List[Dict]:
        """Generate insights from available data."""
        insights = []

        # Performance insights
        for metric_name, series in self.collector.metrics.items():
            stats = series.get_statistics()
            if stats:
                trend = series.get_trend()
                anomalies = series.get_anomalies()

                if trend == "increasing":
                    insights.append({
                        "type": "performance_improvement",
                        "metric": metric_name,
                        "message": f"{metric_name} is improving",
                        "severity": "positive"
                    })

                if anomalies:
                    insights.append({
                        "type": "anomaly_detected",
                        "metric": metric_name,
                        "count": len(anomalies),
                        "message": f"{len(anomalies)} anomalies in {metric_name}",
                        "severity": "warning"
                    })

        # Pattern insights
        for pattern_name, occurrences in self.detector.patterns.items():
            if occurrences:
                insights.append({
                    "type": "pattern_detected",
                    "pattern": pattern_name,
                    "occurrences": len(occurrences),
                    "message": f"Pattern {pattern_name} detected",
                    "severity": "info"
                })

        self.insights = insights
        return insights

    def get_recommendations(self) -> List[str]:
        """Get recommendations based on insights."""
        recommendations = []

        for insight in self.insights:
            if insight["type"] == "anomaly_detected":
                recommendations.append(
                    f"Investigate anomalies in {insight['metric']}"
                )
            elif insight["type"] == "pattern_detected":
                recommendations.append(
                    f"Optimize for detected pattern: {insight['pattern']}"
                )

        return recommendations


class Dashboard:
    """Analytics dashboard."""

    def __init__(self, collector: MetricsCollector, detector: PatternDetector):
        self.collector = collector
        self.detector = detector
        self.generator = InsightGenerator(collector, detector)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data."""
        insights = self.generator.generate_insights()
        recommendations = self.generator.get_recommendations()

        return {
            "timestamp": datetime.now().isoformat(),
            "metrics_summary": {
                name: series.get_statistics()
                for name, series in self.collector.metrics.items()
            },
            "trends": {
                name: series.get_trend()
                for name, series in self.collector.metrics.items()
            },
            "patterns": self.detector.get_patterns(),
            "insights": insights,
            "recommendations": recommendations,
            "metric_count": len(self.collector.metrics),
            "pattern_count": self.detector.pattern_count
        }


class AdvancedAnalyticsEngine:
    """Main analytics orchestrator."""

    def __init__(self):
        self.collector = MetricsCollector()
        self.detector = PatternDetector()
        self.dashboard = Dashboard(self.collector, self.detector)
        self.query_history: List[Dict] = []

    def record_metric(self, name: str, value: float,
                     tags: Optional[Dict] = None) -> None:
        """Record metric."""
        self.collector.record_metric(name, value, tags)

    def detect_pattern(self, pattern_name: str, data: List[Any]) -> bool:
        """Detect pattern."""
        detected = self.detector.detect_recurring_pattern(data, pattern_name)
        if detected:
            self.query_history.append({
                "type": "pattern_detection",
                "pattern": pattern_name,
                "timestamp": datetime.now().isoformat()
            })
        return detected

    def get_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics."""
        return self.dashboard.get_dashboard_data()

    def get_metric_analysis(self, metric_name: str) -> Optional[Dict]:
        """Get detailed analysis of metric."""
        if metric_name not in self.collector.metrics:
            return None

        series = self.collector.metrics[metric_name]
        return {
            "name": metric_name,
            "statistics": series.get_statistics(),
            "trend": series.get_trend(),
            "anomalies": len(series.get_anomalies()),
            "data_points": len(series.data_points)
        }

    def export_analytics(self, format: str = "json") -> str:
        """Export analytics data."""
        data = self.get_analytics()
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        return str(data)


# Global instance
_analytics_engine = None


def get_analytics_engine() -> AdvancedAnalyticsEngine:
    """Get or create global analytics engine."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AdvancedAnalyticsEngine()
    return _analytics_engine
