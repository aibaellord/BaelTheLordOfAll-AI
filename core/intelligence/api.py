"""
Intelligence API - RESTful endpoints for intelligent features.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from .intelligence_engine import (BehavioralThreatDetector,
                                  IntelligentAutoScaler, PerformanceOptimizer,
                                  PredictiveAnalyticsEngine,
                                  StatisticalAnomalyDetector)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

# Shared instances
anomaly_detector = StatisticalAnomalyDetector()
auto_scaler = IntelligentAutoScaler()
threat_detector = BehavioralThreatDetector()
analytics_engine = PredictiveAnalyticsEngine()
optimizer = PerformanceOptimizer()


@router.post("/anomalies/detect")
async def detect_anomaly(
    metric_name: str,
    value: float,
    sensitivity: float = 2.5
) -> Dict[str, Any]:
    """
    Detect anomalies in metrics using advanced statistical methods.

    Supports Z-score, modified Z-score, and multivariate detection.
    """
    anomaly_detector.sensitivity = sensitivity
    result = anomaly_detector.detect_anomaly(metric_name, value)

    return {
        "metric": metric_name,
        "value": value,
        "is_anomaly": result.is_anomaly,
        "z_score": result.z_score,
        "confidence": result.confidence,
        "expected_value": result.expected_value,
        "std_deviations": result.std_deviations,
        "timestamp": result.timestamp.isoformat()
    }


@router.post("/autoscaling/recommend")
async def recommend_scaling(
    agent_id: str,
    current_load: float,
    resource_cost: float,
    latency: float,
    error_rate: float
) -> Dict[str, Any]:
    """
    Get intelligent auto-scaling recommendation using game theory.

    Considers load, costs, latency, and error rates for optimal scaling.
    """
    scale_factor, reasoning = auto_scaler.calculate_optimal_scale(
        agent_id, current_load, resource_cost, latency, error_rate
    )

    return {
        "agent_id": agent_id,
        "current_load": current_load,
        "recommended_scale_factor": scale_factor,
        "reasoning": reasoning,
        "target_utilization": auto_scaler.target_utilization,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/threats/detect")
async def detect_threat(
    entity_id: str,
    entity_type: str,
    behavior_metrics: Dict[str, float]
) -> Optional[Dict[str, Any]]:
    """
    Detect security threats using behavioral analysis.

    Analyzes patterns for brute force, data exfiltration, privilege escalation, DDoS.
    """
    threat = threat_detector.detect_threat(entity_id, entity_type, behavior_metrics)

    if not threat:
        return {
            "entity_id": entity_id,
            "threat_detected": False,
            "timestamp": datetime.now().isoformat()
        }

    return {
        "entity_id": entity_id,
        "threat_detected": True,
        "threat_type": threat.threat_type,
        "threat_level": threat.threat_level.name,
        "threat_level_value": threat.threat_level.value,
        "indicators": threat.indicators,
        "recommended_actions": threat.recommended_actions,
        "false_positive_probability": threat.false_positive_probability,
        "timestamp": threat.timestamp.isoformat()
    }


@router.get("/forecast/load")
async def forecast_load(
    metric_name: str,
    historical_values: List[float],
    method: str = "arima"
) -> Dict[str, Any]:
    """
    Forecast future metric values using time series analysis.

    Methods: arima, exponential_smoothing, trend
    """
    forecast, confidence = analytics_engine.forecast_load(
        metric_name, historical_values, method
    )

    return {
        "metric": metric_name,
        "forecast_method": method,
        "forecast_horizon": analytics_engine.forecast_horizon,
        "forecast_values": forecast,
        "confidence_intervals": confidence,
        "forecast_peak": max(forecast) if forecast else None,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/forecast/capacity")
async def predict_capacity(
    agent_id: str,
    historical_load: List[float],
    growth_rate: float = 0.05
) -> Dict[str, Any]:
    """
    Predict capacity needed for future growth using forecasting.
    """
    prediction = analytics_engine.predict_capacity_needed(
        agent_id, historical_load, growth_rate
    )

    return prediction


@router.post("/optimize/bottlenecks")
async def identify_bottlenecks(
    metrics: Dict[str, float],
    thresholds: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Identify system bottlenecks and get optimization recommendations.

    Analyzes CPU, memory, disk I/O, and network performance.
    """
    if not thresholds:
        thresholds = {
            "cpu_threshold": 0.8,
            "memory_threshold": 0.85,
            "disk_io_threshold": 0.5,
            "network_threshold": 0.9
        }

    recommendations = optimizer.identify_bottlenecks(metrics, thresholds)

    return {
        "bottleneck_count": len(recommendations),
        "recommendations": [
            {
                "component": r.component,
                "issue": r.issue,
                "recommendation": r.recommendation,
                "estimated_improvement": r.estimated_improvement,
                "risk_level": r.risk_level,
                "implementation_complexity": r.implementation_complexity,
                "estimated_impact": r.estimated_impact
            }
            for r in recommendations
        ],
        "timestamp": datetime.now().isoformat()
    }


@router.post("/optimize/configuration")
async def optimize_configuration(
    constraints: Dict[str, float],
    objectives: Dict[str, float]
) -> Dict[str, Any]:
    """
    Calculate optimal system configuration using optimization algorithms.
    """
    config = optimizer.calculate_optimal_configuration(constraints, objectives)

    return {
        "constraints": constraints,
        "optimal_configuration": config,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/intelligence/summary")
async def get_intelligence_summary() -> Dict[str, Any]:
    """
    Get summary of all intelligence engine capabilities.
    """
    return {
        "components": {
            "anomaly_detection": {
                "enabled": True,
                "methods": ["z_score", "modified_z_score", "mahalanobis"],
                "metrics_tracked": len(anomaly_detector.history)
            },
            "auto_scaling": {
                "enabled": True,
                "method": "game_theory",
                "target_utilization": auto_scaler.target_utilization
            },
            "threat_detection": {
                "enabled": True,
                "threat_types": [
                    "brute_force",
                    "data_exfiltration",
                    "privilege_escalation",
                    "ddos"
                ],
                "entities_monitored": len(threat_detector.baselines)
            },
            "predictive_analytics": {
                "enabled": True,
                "forecast_methods": ["arima", "exponential_smoothing", "trend"],
                "forecast_horizon_hours": analytics_engine.forecast_horizon
            },
            "performance_optimization": {
                "enabled": True,
                "analyses": [
                    "cpu_bottleneck",
                    "memory_bottleneck",
                    "disk_io_bottleneck",
                    "network_bottleneck"
                ]
            }
        },
        "timestamp": datetime.now().isoformat()
    }
