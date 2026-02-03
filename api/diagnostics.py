"""
Self-Diagnostics System for BAEL Phase 2

Implements continuous monitoring, health checks, auto-optimization,
and self-healing mechanisms for the entire system.

Key Components:
- Real-time health monitoring
- Performance profiling and analytics
- Auto-scaling and optimization
- Anomaly detection
- Self-healing triggers
- System state reporting
"""

import json
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """System health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class ComponentType(str, Enum):
    """Types of system components."""
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    MEMORY = "memory"
    COMPUTE = "compute"
    NETWORK = "network"
    STORAGE = "storage"
    REASONING = "reasoning"
    LEARNING = "learning"
    SWARMS = "swarms"


@dataclass
class HealthMetric:
    """Single health metric."""
    metric_name: str
    component: ComponentType
    current_value: float
    normal_range: Tuple[float, float]  # (min, max)
    status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.now)
    history: List[Tuple[datetime, float]] = field(default_factory=list)

    def add_reading(self, value: float) -> None:
        """Add new reading."""
        self.current_value = value
        self.history.append((datetime.now(), value))
        self._update_status()

    def _update_status(self) -> None:
        """Update status based on value."""
        if self.normal_range[0] <= self.current_value <= self.normal_range[1]:
            self.status = HealthStatus.HEALTHY
        elif self.normal_range[0] * 0.8 <= self.current_value <= self.normal_range[1] * 1.2:
            self.status = HealthStatus.DEGRADED
        else:
            self.status = HealthStatus.UNHEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "component": self.component.value,
            "current_value": self.current_value,
            "normal_range": self.normal_range,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ComponentHealth:
    """Health status of a component."""
    component_type: ComponentType
    status: HealthStatus
    metrics: Dict[str, HealthMetric] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)
    error_count: int = 0
    recovery_attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component": self.component_type.value,
            "status": self.status.value,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "error_count": self.error_count,
            "recovery_attempts": self.recovery_attempts,
            "last_check": self.last_check.isoformat(),
        }


@dataclass
class PerformanceProfile:
    """Performance profile of system."""
    timestamp: datetime = field(default_factory=datetime.now)
    avg_latency_ms: float = 0.0  # milliseconds
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    throughput_rps: float = 0.0  # Requests per second
    error_rate: float = 0.0  # 0.0 to 1.0
    cpu_usage: float = 0.0  # 0.0 to 1.0
    memory_usage: float = 0.0
    cache_hit_rate: float = 0.0
    db_query_time_ms: float = 0.0
    overall_efficiency: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "throughput_rps": self.throughput_rps,
            "error_rate": self.error_rate,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "cache_hit_rate": self.cache_hit_rate,
            "db_query_time_ms": self.db_query_time_ms,
            "overall_efficiency": self.overall_efficiency,
        }


class AnomalyDetector:
    """Detects anomalies in metrics."""

    def __init__(self, window_size: int = 100):
        """Initialize detector."""
        self.window_size = window_size
        self.metric_history: Dict[str, List[float]] = defaultdict(list)

    def add_reading(self, metric_name: str, value: float) -> None:
        """Add reading for metric."""
        history = self.metric_history[metric_name]
        history.append(value)

        # Keep only recent values
        if len(history) > self.window_size:
            history.pop(0)

    def is_anomaly(self, metric_name: str, value: float, threshold: float = 3.0) -> bool:
        """
        Detect if value is anomalous.

        Args:
            metric_name: Metric to check
            value: New value
            threshold: Standard deviations for anomaly

        Returns:
            True if anomalous
        """
        history = self.metric_history.get(metric_name, [])

        if len(history) < 10:
            return False  # Not enough history

        mean = statistics.mean(history)
        stdev = statistics.stdev(history)

        if stdev == 0:
            return value != mean

        z_score = abs(value - mean) / stdev
        return z_score > threshold

    def get_anomalies(self, metrics: Dict[str, float]) -> List[Tuple[str, float]]:
        """Get anomalous metrics."""
        anomalies = []

        for metric_name, value in metrics.items():
            if self.is_anomaly(metric_name, value):
                anomalies.append((metric_name, value))

        return anomalies


class OptimizationTrigger:
    """Triggers optimization actions based on metrics."""

    def __init__(self):
        """Initialize trigger."""
        self.optimization_rules = self._load_rules()
        self.triggered_actions: List[str] = []

    def _load_rules(self) -> Dict[str, Callable]:
        """Load optimization rules."""
        return {
            "high_latency": self._handle_high_latency,
            "high_cpu": self._handle_high_cpu,
            "low_cache_hit": self._handle_low_cache_hit,
            "high_error_rate": self._handle_high_error_rate,
            "memory_pressure": self._handle_memory_pressure,
        }

    def evaluate(self, profile: PerformanceProfile) -> List[str]:
        """
        Evaluate profile and return optimization actions.

        Returns:
            List of recommended actions
        """
        self.triggered_actions = []

        if profile.avg_latency_ms > 500:
            self.triggered_actions.extend(self._handle_high_latency(profile))

        if profile.cpu_usage > 0.8:
            self.triggered_actions.extend(self._handle_high_cpu(profile))

        if profile.cache_hit_rate < 0.6:
            self.triggered_actions.extend(self._handle_low_cache_hit(profile))

        if profile.error_rate > 0.05:
            self.triggered_actions.extend(self._handle_high_error_rate(profile))

        if profile.memory_usage > 0.85:
            self.triggered_actions.extend(self._handle_memory_pressure(profile))

        return self.triggered_actions

    def _handle_high_latency(self, profile: PerformanceProfile) -> List[str]:
        """Handle high latency."""
        return [
            "enable_caching_for_frequent_queries",
            "increase_cache_ttl",
            "optimize_database_indexes",
            "consider_load_balancing",
        ]

    def _handle_high_cpu(self, profile: PerformanceProfile) -> List[str]:
        """Handle high CPU usage."""
        return [
            "reduce_computation_precision",
            "enable_request_batching",
            "scale_horizontally",
            "profile_cpu_hotspots",
        ]

    def _handle_low_cache_hit(self, profile: PerformanceProfile) -> List[str]:
        """Handle low cache hit rate."""
        return [
            "increase_cache_size",
            "adjust_ttl_policy",
            "preload_common_queries",
            "analyze_access_patterns",
        ]

    def _handle_high_error_rate(self, profile: PerformanceProfile) -> List[str]:
        """Handle high error rate."""
        return [
            "enable_retry_logic",
            "add_circuit_breaker",
            "increase_timeout_values",
            "review_error_logs",
        ]

    def _handle_memory_pressure(self, profile: PerformanceProfile) -> List[str]:
        """Handle memory pressure."""
        return [
            "enable_memory_compression",
            "clear_expired_cache",
            "reduce_batch_sizes",
            "optimize_data_structures",
        ]


class SelfHealer:
    """Automatically heals detected issues."""

    def __init__(self):
        """Initialize healer."""
        self.healing_actions: Dict[str, Callable] = {}
        self.healing_history: List[Dict[str, Any]] = []

    def register_action(self, name: str, action: Callable) -> None:
        """Register healing action."""
        self.healing_actions[name] = action

    def execute_healing(self, action_name: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute healing action.

        Args:
            action_name: Name of action to execute
            params: Parameters for action

        Returns:
            Success status
        """
        if action_name not in self.healing_actions:
            logger.warning(f"Unknown healing action: {action_name}")
            return False

        try:
            action = self.healing_actions[action_name]
            params = params or {}
            action(**params)

            self.healing_history.append({
                "action": action_name,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "params": params,
            })

            logger.info(f"Executed healing action: {action_name}")
            return True

        except Exception as e:
            logger.error(f"Healing action failed: {e}")
            return False

    def get_healing_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent healing history."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            h for h in self.healing_history
            if datetime.fromisoformat(h["timestamp"]) > cutoff
        ]


class DiagnosticsSystem:
    """Main diagnostics and self-optimization system."""

    def __init__(self):
        """Initialize diagnostics system."""
        self.components: Dict[ComponentType, ComponentHealth] = {
            ct: ComponentHealth(ct, HealthStatus.HEALTHY)
            for ct in ComponentType
        }
        self.anomaly_detector = AnomalyDetector()
        self.optimization_trigger = OptimizationTrigger()
        self.self_healer = SelfHealer()
        self.performance_profiles: List[PerformanceProfile] = []

    def report_metric(
        self,
        component: ComponentType,
        metric_name: str,
        value: float,
        normal_range: Tuple[float, float],
    ) -> None:
        """Report a metric."""
        # Update component health
        comp_health = self.components[component]
        metric = HealthMetric(
            metric_name=metric_name,
            component=component,
            current_value=value,
            normal_range=normal_range,
            status=HealthStatus.HEALTHY,
        )
        metric.add_reading(value)
        comp_health.metrics[metric_name] = metric

        # Check for anomalies
        self.anomaly_detector.add_reading(metric_name, value)
        if self.anomaly_detector.is_anomaly(metric_name, value):
            logger.warning(f"Anomaly detected in {metric_name}: {value}")
            comp_health.error_count += 1

    def get_component_health(self, component: ComponentType) -> Optional[ComponentHealth]:
        """Get health of component."""
        return self.components.get(component)

    def get_overall_health(self) -> HealthStatus:
        """Get overall system health."""
        statuses = [c.status for c in self.components.values()]

        if any(s == HealthStatus.CRITICAL for s in statuses):
            return HealthStatus.CRITICAL
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def record_performance(self, profile: PerformanceProfile) -> None:
        """Record performance snapshot."""
        self.performance_profiles.append(profile)

        # Keep only recent profiles
        cutoff = datetime.now() - timedelta(hours=24)
        self.performance_profiles = [
            p for p in self.performance_profiles
            if p.timestamp > cutoff
        ]

        # Evaluate for optimization
        actions = self.optimization_trigger.evaluate(profile)
        if actions:
            logger.info(f"Triggered optimizations: {actions}")

    def run_diagnostics(self) -> Dict[str, Any]:
        """Run full system diagnostics."""
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": self.get_overall_health().value,
            "components": {
                ct.value: ch.to_dict()
                for ct, ch in self.components.items()
            },
            "performance": self._get_performance_summary(),
            "recommendations": self._generate_recommendations(),
        }

        return diagnostics

    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.performance_profiles:
            return {}

        recent = self.performance_profiles[-10:]  # Last 10
        latencies = [p.avg_latency_ms for p in recent]
        errors = [p.error_rate for p in recent]

        return {
            "avg_latency_ms": statistics.mean(latencies),
            "avg_error_rate": statistics.mean(errors),
            "num_profiles": len(self.performance_profiles),
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations."""
        recommendations = []

        # Check for concerning metrics
        if self.get_overall_health() != HealthStatus.HEALTHY:
            recommendations.append("System health is degraded. Review component metrics.")

        # Check performance
        if self.performance_profiles:
            latest = self.performance_profiles[-1]
            if latest.avg_latency_ms > 500:
                recommendations.append("High latency detected. Consider optimization.")

        return recommendations

    def export_report(self) -> Dict[str, Any]:
        """Export comprehensive diagnostics report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "diagnostics": self.run_diagnostics(),
            "healing_history": self.self_healer.get_healing_history(),
            "anomaly_metrics": {
                ct.value: {
                    "error_count": self.components[ct].error_count,
                    "recovery_attempts": self.components[ct].recovery_attempts,
                }
                for ct in ComponentType
            },
        }


# Global diagnostics system
_diagnostics = None


def get_diagnostics_system() -> DiagnosticsSystem:
    """Get or create global diagnostics system."""
    global _diagnostics
    if _diagnostics is None:
        _diagnostics = DiagnosticsSystem()
    return _diagnostics
