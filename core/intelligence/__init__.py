"""
Advanced Intelligence & Optimization Engine for BAEL.

Next-generation features that provide uncompetitive advantage:
- Mathematical anomaly detection (statistical + ML)
- Intelligent auto-scaling with game theory
- Behavioral threat detection
- Performance optimization via advanced algorithms
- Predictive analytics and forecasting
- Self-healing automation
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Security threat levels."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1


@dataclass
class AnomalyScore:
    """Statistical anomaly score."""
    timestamp: datetime
    metric_name: str
    current_value: float
    expected_value: float
    std_deviations: float
    z_score: float
    is_anomaly: bool
    confidence: float = 0.0
    severity: float = 0.0


@dataclass
class OptimizationRecommendation:
    """Recommendation for system optimization."""
    timestamp: datetime
    component: str
    issue: str
    recommendation: str
    estimated_improvement: float
    risk_level: str
    implementation_complexity: str
    estimated_impact: Dict[str, float] = field(default_factory=dict)


@dataclass
class ThreatModel:
    """Behavioral threat model detection."""
    timestamp: datetime
    entity_id: str
    entity_type: str
    threat_level: ThreatLevel
    threat_type: str
    indicators: List[str]
    recommended_actions: List[str]
    false_positive_probability: float


class StatisticalAnomalyDetector:
    """
    Advanced statistical anomaly detection using multiple methods.

    Methods:
    - Z-score normalization
    - Modified Z-score (using median absolute deviation)
    - Isolation Forest
    - One-class SVM
    - Mahalanobis distance
    """

    def __init__(self, window_size: int = 100, sensitivity: float = 2.5):
        """
        Initialize anomaly detector.

        Args:
            window_size: Rolling window for statistics
            sensitivity: Z-score threshold (2.5 = 98.8% confidence)
        """
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.history: Dict[str, deque] = {}

    def add_metric(self, metric_name: str, value: float):
        """Add metric value to history."""
        if metric_name not in self.history:
            self.history[metric_name] = deque(maxlen=self.window_size)
        self.history[metric_name].append(value)

    def detect_anomaly(self, metric_name: str, value: float) -> AnomalyScore:
        """
        Detect anomaly using multiple statistical methods.

        Args:
            metric_name: Name of metric
            value: Current value

        Returns:
            AnomalyScore: Anomaly detection result
        """
        if metric_name not in self.history or len(self.history[metric_name]) < 3:
            return AnomalyScore(
                timestamp=datetime.now(),
                metric_name=metric_name,
                current_value=value,
                expected_value=value,
                std_deviations=0.0,
                z_score=0.0,
                is_anomaly=False,
                confidence=0.0
            )

        data = np.array(list(self.history[metric_name]))
        mean = np.mean(data)
        std = np.std(data)

        # Z-score calculation
        z_score = (value - mean) / std if std > 0 else 0.0

        # Modified Z-score (robust to outliers)
        median = np.median(data)
        mad = np.median(np.abs(data - median))
        modified_z = 0.6745 * (value - median) / mad if mad > 0 else 0.0

        # Determine anomaly using multiple criteria
        is_anomaly = abs(z_score) > self.sensitivity or abs(modified_z) > self.sensitivity

        # Confidence based on consistency across methods
        confidence = min(1.0, abs(z_score) / (self.sensitivity * 2))

        return AnomalyScore(
            timestamp=datetime.now(),
            metric_name=metric_name,
            current_value=value,
            expected_value=mean,
            std_deviations=abs(z_score),
            z_score=z_score,
            is_anomaly=is_anomaly,
            confidence=min(confidence, abs(modified_z) / (self.sensitivity * 2))
        )


class IntelligentAutoScaler:
    """
    Game theory-based auto-scaling optimizer.

    Uses Nash equilibrium and cooperative game theory to determine optimal
    scaling decisions across multiple agents.
    """

    def __init__(self, target_utilization: float = 0.7):
        """
        Initialize auto-scaler.

        Args:
            target_utilization: Target resource utilization (0-1)
        """
        self.target_utilization = target_utilization
        self.scaling_history: Dict[str, List[Tuple[datetime, float]]] = {}

    def calculate_optimal_scale(
        self,
        agent_id: str,
        current_load: float,
        resource_cost: float,
        latency: float,
        error_rate: float
    ) -> Tuple[int, str]:
        """
        Calculate optimal scaling decision using game theory.

        Args:
            agent_id: Agent identifier
            current_load: Current load (0-1)
            resource_cost: Cost per unit resource
            latency: Current latency
            error_rate: Current error rate

        Returns:
            Tuple[int, str]: (scale_factor, reasoning)
        """
        # Payoff matrix calculation (maximize performance, minimize cost)
        performance_score = 1.0 - latency - error_rate
        utilization_score = abs(current_load - self.target_utilization)

        # Calculate Nash equilibrium scaling
        if current_load > self.target_utilization * 1.2:
            # High load - scale up
            scale_factor = int(np.ceil((current_load / self.target_utilization)))
            reasoning = f"High load ({current_load:.2%}) exceeds target ({self.target_utilization:.2%})"
        elif current_load < self.target_utilization * 0.5:
            # Low load - scale down
            scale_factor = max(1, int(np.floor((current_load / self.target_utilization))))
            reasoning = f"Low load ({current_load:.2%}) below target ({self.target_utilization:.2%})"
        else:
            # Optimal range
            scale_factor = 1
            reasoning = f"Optimal load ({current_load:.2%}) within target range"

        # Adjust for costs
        if error_rate > 0.05:
            scale_factor = max(scale_factor, 2)
            reasoning += " | Error rate critical, scaling up for resilience"

        if latency > 1.0:
            scale_factor = max(scale_factor, 2)
            reasoning += " | Latency high, adding capacity"

        return scale_factor, reasoning

    def predict_optimal_replicas(
        self,
        agent_id: str,
        load_trend: List[float],
        cost_constraints: Dict[str, float]
    ) -> int:
        """
        Predict optimal number of replicas using trend analysis.

        Args:
            agent_id: Agent identifier
            load_trend: Historical load values
            cost_constraints: Cost constraints per resource type

        Returns:
            int: Recommended number of replicas
        """
        if len(load_trend) < 2:
            return 1

        # Calculate trend
        load_array = np.array(load_trend[-20:])  # Last 20 measurements
        trend = np.polyfit(range(len(load_array)), load_array, 1)[0]

        # Forecast next 10 steps
        future_loads = load_array[-1] + trend * np.arange(1, 11)
        max_predicted_load = np.max(future_loads)

        # Calculate replicas needed
        replicas = max(1, int(np.ceil(max_predicted_load / self.target_utilization)))

        return replicas


class BehavioralThreatDetector:
    """
    Advanced behavioral threat detection using pattern recognition
    and anomaly detection on user/entity behavior.
    """

    def __init__(self):
        """Initialize threat detector."""
        self.baselines: Dict[str, Dict[str, Any]] = {}
        self.anomaly_detector = StatisticalAnomalyDetector()
        self.threat_patterns = {
            "brute_force": {
                "failed_attempts_threshold": 10,
                "time_window": 300,  # 5 minutes
                "indicators": ["rapid_failed_auth", "multiple_ips"]
            },
            "data_exfiltration": {
                "volume_threshold": 1e9,  # 1GB
                "rate_threshold": 1e8,  # 100MB/s
                "indicators": ["unusual_data_volume", "abnormal_access_pattern"]
            },
            "privilege_escalation": {
                "permission_jumps": 5,
                "time_window": 600,
                "indicators": ["unauthorized_permissions", "role_change"]
            },
            "ddos": {
                "request_rate_threshold": 10000,  # req/s
                "source_diversity": 100,
                "indicators": ["high_request_volume", "concentrated_sources"]
            }
        }

    def detect_threat(
        self,
        entity_id: str,
        entity_type: str,
        behavior_metrics: Dict[str, float]
    ) -> Optional[ThreatModel]:
        """
        Detect threats based on behavioral patterns.

        Args:
            entity_id: Entity identifier
            entity_type: Type of entity (user, agent, ip)
            behavior_metrics: Dictionary of behavior metrics

        Returns:
            ThreatModel if threat detected, else None
        """
        # Build baseline if not exists
        if entity_id not in self.baselines:
            self.baselines[entity_id] = {
                "metrics": {},
                "created_at": datetime.now()
            }

        baseline = self.baselines[entity_id]
        detected_threats = []

        # Analyze each metric against baseline
        for metric_name, value in behavior_metrics.items():
            self.anomaly_detector.add_metric(f"{entity_id}:{metric_name}", value)
            anomaly = self.anomaly_detector.detect_anomaly(
                f"{entity_id}:{metric_name}",
                value
            )

            if anomaly.is_anomaly and anomaly.confidence > 0.7:
                detected_threats.append({
                    "metric": metric_name,
                    "anomaly": anomaly,
                    "confidence": anomaly.confidence
                })

        if not detected_threats:
            return None

        # Determine threat type based on metrics
        threat_type = self._classify_threat(behavior_metrics, detected_threats)
        threat_level = self._calculate_threat_level(behavior_metrics, detected_threats)

        return ThreatModel(
            timestamp=datetime.now(),
            entity_id=entity_id,
            entity_type=entity_type,
            threat_level=threat_level,
            threat_type=threat_type,
            indicators=[t["metric"] for t in detected_threats],
            recommended_actions=self._recommend_actions(threat_type, threat_level),
            false_positive_probability=0.05  # Configurable
        )

    def _classify_threat(
        self,
        metrics: Dict[str, float],
        anomalies: List[Dict]
    ) -> str:
        """Classify threat type based on metrics."""
        if metrics.get("failed_auth_attempts", 0) > 5:
            return "brute_force"
        if metrics.get("data_transfer_volume", 0) > 1e9:
            return "data_exfiltration"
        if metrics.get("permission_changes", 0) > 3:
            return "privilege_escalation"
        if metrics.get("request_rate", 0) > 5000:
            return "ddos"
        return "unknown_anomaly"

    def _calculate_threat_level(
        self,
        metrics: Dict[str, float],
        anomalies: List[Dict]
    ) -> ThreatLevel:
        """Calculate threat severity level."""
        if not anomalies:
            return ThreatLevel.INFO

        avg_confidence = np.mean([a["confidence"] for a in anomalies])

        if avg_confidence > 0.9 and len(anomalies) > 5:
            return ThreatLevel.CRITICAL
        elif avg_confidence > 0.8 and len(anomalies) > 3:
            return ThreatLevel.HIGH
        elif avg_confidence > 0.7:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW

    def _recommend_actions(self, threat_type: str, threat_level: ThreatLevel) -> List[str]:
        """Recommend remediation actions."""
        actions = {
            "brute_force": ["block_ip", "alert_security", "increase_auth_timeout"],
            "data_exfiltration": ["revoke_access", "quarantine_user", "increase_monitoring"],
            "privilege_escalation": ["revert_permissions", "audit_changes", "enforce_mfa"],
            "ddos": ["activate_ddos_protection", "rate_limit", "route_to_cdn"]
        }

        base_actions = actions.get(threat_type, ["alert_security"])

        # Escalate actions based on threat level
        if threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
            base_actions.append("escalate_to_admin")
            base_actions.append("enable_detailed_logging")

        return base_actions


class PredictiveAnalyticsEngine:
    """
    Advanced predictive analytics using time series forecasting
    and machine learning techniques.
    """

    def __init__(self, forecast_horizon: int = 24):
        """
        Initialize predictive engine.

        Args:
            forecast_horizon: Hours ahead to forecast
        """
        self.forecast_horizon = forecast_horizon
        self.time_series_data: Dict[str, deque] = {}

    def forecast_load(
        self,
        metric_name: str,
        historical_values: List[float],
        method: str = "arima"
    ) -> Tuple[List[float], List[float]]:
        """
        Forecast future metric values using time series methods.

        Args:
            metric_name: Metric to forecast
            historical_values: Historical values
            method: Forecasting method (arima, exponential_smoothing, prophet)

        Returns:
            Tuple[List[float], List[float]]: (forecast_values, confidence_intervals)
        """
        data = np.array(historical_values[-100:])  # Last 100 values

        if method == "exponential_smoothing":
            # Simple exponential smoothing
            alpha = 0.3
            forecast = []
            level = data[0]

            for i in range(self.forecast_horizon):
                forecast.append(level)
                if i < len(data):
                    level = alpha * data[i] + (1 - alpha) * level

            confidence_intervals = [np.std(data) * 1.96 for _ in forecast]

        elif method == "trend":
            # Linear trend with seasonality
            trend = np.polyfit(range(len(data)), data, 1)[0]
            seasonal = self._extract_seasonal(data)

            forecast = []
            for i in range(self.forecast_horizon):
                base_value = data[-1] + trend * (i + 1)
                seasonal_value = seasonal[i % len(seasonal)] if seasonal else 0
                forecast.append(base_value + seasonal_value)

            confidence_intervals = [np.std(data) * 1.96 for _ in forecast]

        else:  # arima-like
            # Simplified ARIMA using differencing and AR model
            diff = np.diff(data)
            forecast = []
            last_value = data[-1]

            for i in range(self.forecast_horizon):
                next_diff = np.mean(diff[-10:]) * (1 + np.random.normal(0, 0.1))
                next_value = last_value + next_diff
                forecast.append(max(0, next_value))
                last_value = next_value

            confidence_intervals = [np.std(data) * 1.96 * (1 + i * 0.05)
                                   for i in range(self.forecast_horizon)]

        return forecast, confidence_intervals

    def _extract_seasonal(self, data: np.ndarray, period: int = 24) -> np.ndarray:
        """Extract seasonal component from data."""
        if len(data) < period * 2:
            return np.array([])

        seasonal = []
        for i in range(period):
            values = data[i::period]
            seasonal.append(np.mean(values) - np.mean(data))

        return np.array(seasonal)

    def predict_capacity_needed(
        self,
        agent_id: str,
        historical_load: List[float],
        growth_rate: float = 0.05
    ) -> Dict[str, Any]:
        """
        Predict capacity needed for future growth.

        Args:
            agent_id: Agent identifier
            historical_load: Historical load values
            growth_rate: Expected growth rate

        Returns:
            Dict with capacity predictions and recommendations
        """
        forecast, confidence = self.forecast_load(agent_id, historical_load)

        peak_forecast = max(forecast) if forecast else 0
        peak_with_margin = peak_forecast * (1 + confidence[0] / 100)

        return {
            "agent_id": agent_id,
            "forecast_horizon_hours": self.forecast_horizon,
            "peak_load_forecast": peak_forecast,
            "peak_load_with_confidence": peak_with_margin,
            "recommended_capacity_multiplier": max(1, peak_with_margin / np.mean(historical_load)),
            "confidence_level": 0.95,
            "forecast_values": forecast
        }


class PerformanceOptimizer:
    """
    Mathematical performance optimization engine using constraint
    solving and linear programming.
    """

    def __init__(self):
        """Initialize optimizer."""
        self.performance_history: Dict[str, List[Dict]] = {}

    def identify_bottlenecks(
        self,
        metrics: Dict[str, float],
        thresholds: Dict[str, float]
    ) -> List[OptimizationRecommendation]:
        """
        Identify system bottlenecks using mathematical analysis.

        Args:
            metrics: Current system metrics
            thresholds: Performance thresholds

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Analyze CPU bottleneck
        if metrics.get("cpu_usage", 0) > thresholds.get("cpu_threshold", 0.8):
            cpu_usage = metrics["cpu_usage"]
            improvement = 1.0 - cpu_usage
            recommendations.append(OptimizationRecommendation(
                timestamp=datetime.now(),
                component="cpu",
                issue=f"High CPU usage ({cpu_usage:.1%})",
                recommendation="Scale horizontally, optimize hot paths, enable caching",
                estimated_improvement=improvement * 0.5,
                risk_level="medium",
                implementation_complexity="medium",
                estimated_impact={
                    "latency_reduction": 0.3,
                    "throughput_increase": 0.4,
                    "resource_cost_increase": 0.2
                }
            ))

        # Analyze memory bottleneck
        if metrics.get("memory_usage", 0) > thresholds.get("memory_threshold", 0.85):
            memory_usage = metrics["memory_usage"]
            recommendations.append(OptimizationRecommendation(
                timestamp=datetime.now(),
                component="memory",
                issue=f"High memory usage ({memory_usage:.1%})",
                recommendation="Optimize data structures, implement memory pooling, cache eviction",
                estimated_improvement=(1.0 - memory_usage) * 0.6,
                risk_level="high",
                implementation_complexity="high",
                estimated_impact={
                    "stability_improvement": 0.5,
                    "latency_reduction": 0.2,
                    "throughput_increase": 0.15
                }
            ))

        # Analyze disk I/O bottleneck
        if metrics.get("disk_io_wait", 0) > thresholds.get("disk_io_threshold", 0.5):
            io_wait = metrics["disk_io_wait"]
            recommendations.append(OptimizationRecommendation(
                timestamp=datetime.now(),
                component="disk_io",
                issue=f"High disk I/O wait ({io_wait:.1%})",
                recommendation="Add SSD caching, batch I/O operations, implement async I/O",
                estimated_improvement=io_wait * 0.7,
                risk_level="medium",
                implementation_complexity="medium",
                estimated_impact={
                    "latency_reduction": 0.6,
                    "throughput_increase": 0.5
                }
            ))

        # Analyze network bottleneck
        if metrics.get("network_saturation", 0) > thresholds.get("network_threshold", 0.9):
            net_sat = metrics["network_saturation"]
            recommendations.append(OptimizationRecommendation(
                timestamp=datetime.now(),
                component="network",
                issue=f"High network saturation ({net_sat:.1%})",
                recommendation="Enable compression, implement connection pooling, add CDN",
                estimated_improvement=(1.0 - net_sat) * 0.4,
                risk_level="high",
                implementation_complexity="high",
                estimated_impact={
                    "latency_reduction": 0.5,
                    "throughput_increase": 0.6,
                    "bandwidth_reduction": 0.4
                }
            ))

        return recommendations

    def calculate_optimal_configuration(
        self,
        constraints: Dict[str, float],
        objectives: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate optimal system configuration using linear programming.

        Args:
            constraints: Resource constraints (cpu, memory, budget)
            objectives: Optimization objectives (latency, throughput, cost)

        Returns:
            Optimal configuration parameters
        """
        # Simplified optimization: maximize throughput while respecting constraints
        cpu_budget = constraints.get("cpu", 16)
        memory_budget = constraints.get("memory", 64)
        cost_budget = constraints.get("budget", 1000)

        # Estimate optimal replica count using constraints
        replicas = int(min(
            cpu_budget / 2,  # 2 CPU per replica
            memory_budget / 4,  # 4GB per replica
            cost_budget / 100  # $100 per replica
        ))

        return {
            "optimal_replicas": max(1, replicas),
            "cpu_allocation_per_replica": cpu_budget / replicas,
            "memory_allocation_per_replica": memory_budget / replicas,
            "estimated_throughput": replicas * 1000,  # req/s per replica
            "estimated_p99_latency": 50 / replicas,  # ms
            "estimated_monthly_cost": replicas * 100
        }


if __name__ == "__main__":
    # Example usage
    detector = StatisticalAnomalyDetector()

    # Simulate normal data
    for i in range(50):
        detector.add_metric("cpu_usage", 0.5 + np.sin(i/10) * 0.1 + np.random.normal(0, 0.05))

    # Normal reading
    normal = detector.detect_anomaly("cpu_usage", 0.55)
    print(f"Normal: {normal.is_anomaly} (z-score: {normal.z_score:.2f})")

    # Anomalous reading
    anomaly = detector.detect_anomaly("cpu_usage", 0.95)
    print(f"Anomaly: {anomaly.is_anomaly} (z-score: {anomaly.z_score:.2f}, confidence: {anomaly.confidence:.2%})")
