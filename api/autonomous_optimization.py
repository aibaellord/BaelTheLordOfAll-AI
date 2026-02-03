"""
Autonomous Optimization System for BAEL

System-wide optimization engine that continuously improves performance,
costs, and user satisfaction through autonomous adjustments.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class OptimizationStrategy(Enum):
    """Optimization strategies."""
    PERFORMANCE = "performance"
    COST = "cost"
    RELIABILITY = "reliability"
    USER_SATISFACTION = "user_satisfaction"
    BALANCED = "balanced"


class OptimizationTarget(Enum):
    """Optimization targets."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CPU = "cpu"
    COST = "cost"
    ERROR_RATE = "error_rate"
    USER_SATISFACTION = "user_satisfaction"


@dataclass
class OptimizationGoal:
    """Optimization goal."""
    goal_id: str
    target: OptimizationTarget
    current_value: float
    target_value: float
    priority: int = 1
    deadline: Optional[datetime] = None
    progress: float = 0.0
    is_achieved: bool = False


@dataclass
class Adjustment:
    """System adjustment."""
    adjustment_id: str
    target_component: str
    parameter_name: str
    old_value: Any
    new_value: Any
    rationale: str
    impact_score: float = 0.5
    applied_at: datetime = field(default_factory=datetime.now)
    reverted_at: Optional[datetime] = None
    is_active: bool = True


class PerformanceOptimizer:
    """Optimizes system performance."""

    def __init__(self):
        self.metric_history: Dict[str, List[float]] = {}
        self.adjustment_history: List[Adjustment] = []
        self.optimization_rules: Dict[str, Callable] = {}

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record performance metric."""
        if metric_name not in self.metric_history:
            self.metric_history[metric_name] = []
        self.metric_history[metric_name].append(value)

    def get_metric_trend(self, metric_name: str, window_size: int = 10) -> str:
        """Get trend for metric."""
        if metric_name not in self.metric_history:
            return "unknown"

        recent = self.metric_history[metric_name][-window_size:]
        if len(recent) < 2:
            return "insufficient_data"

        if recent[-1] < recent[-2]:
            return "improving"
        elif recent[-1] > recent[-2]:
            return "degrading"
        else:
            return "stable"

    def suggest_optimization(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Suggest optimization for metric."""
        trend = self.get_metric_trend(metric_name)

        if trend == "improving":
            return None

        if trend == "degrading":
            return {
                "metric": metric_name,
                "suggestion": f"Optimize {metric_name}",
                "priority": "high",
                "potential_improvement": "15-20%"
            }

        return None

    def apply_adjustment(self, adjustment: Adjustment) -> bool:
        """Apply system adjustment."""
        self.adjustment_history.append(adjustment)
        return True

    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get optimization summary."""
        improving = sum(
            1 for metric in self.metric_history.keys()
            if self.get_metric_trend(metric) == "improving"
        )

        degrading = sum(
            1 for metric in self.metric_history.keys()
            if self.get_metric_trend(metric) == "degrading"
        )

        return {
            "total_metrics": len(self.metric_history),
            "improving": improving,
            "degrading": degrading,
            "adjustments_applied": len(self.adjustment_history),
            "avg_improvement": self._calculate_avg_improvement()
        }

    def _calculate_avg_improvement(self) -> float:
        """Calculate average improvement across metrics."""
        improvements = []

        for metric_values in self.metric_history.values():
            if len(metric_values) >= 2:
                change = (metric_values[0] - metric_values[-1]) / metric_values[0]
                improvements.append(change)

        return sum(improvements) / len(improvements) if improvements else 0


class CostOptimizer:
    """Optimizes operational costs."""

    def __init__(self):
        self.resource_costs: Dict[str, float] = {}
        self.cost_history: List[Tuple[datetime, float]] = []
        self.budget: Optional[float] = None
        self.spending: float = 0.0

    def set_budget(self, budget: float) -> None:
        """Set monthly/yearly budget."""
        self.budget = budget

    def record_cost(self, resource_name: str, cost: float) -> None:
        """Record resource cost."""
        self.resource_costs[resource_name] = cost
        self.spending += cost
        self.cost_history.append((datetime.now(), cost))

    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get cost breakdown."""
        return {
            "total_spending": self.spending,
            "budget": self.budget,
            "utilization_percent": (self.spending / self.budget * 100) if self.budget else 0,
            "by_resource": self.resource_costs
        }

    def identify_cost_savings(self) -> List[Dict[str, Any]]:
        """Identify potential cost savings."""
        savings = []

        for resource, cost in self.resource_costs.items():
            if cost > 100:  # Arbitrary threshold
                savings.append({
                    "resource": resource,
                    "current_cost": cost,
                    "suggestion": f"Optimize {resource} usage",
                    "potential_savings": cost * 0.2  # 20% potential reduction
                })

        return sorted(savings, key=lambda x: x["potential_savings"], reverse=True)


class ReliabilityOptimizer:
    """Optimizes system reliability."""

    def __init__(self):
        self.error_rates: Dict[str, float] = {}
        self.incident_log: List[Dict[str, Any]] = []
        self.uptime_target = 0.99  # 99% uptime

    def record_error(self, component: str, error_type: str) -> None:
        """Record error."""
        if component not in self.error_rates:
            self.error_rates[component] = 0.0
        self.error_rates[component] += 1

        self.incident_log.append({
            "component": component,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        })

    def get_reliability_metrics(self) -> Dict[str, Any]:
        """Get reliability metrics."""
        total_errors = sum(self.error_rates.values())
        critical_components = sorted(
            self.error_rates.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        return {
            "total_errors": total_errors,
            "uptime_target": f"{self.uptime_target * 100}%",
            "critical_components": critical_components,
            "incidents": len(self.incident_log)
        }

    def identify_failure_points(self) -> List[str]:
        """Identify components with high error rates."""
        return [
            component for component, errors in self.error_rates.items()
            if errors > 5
        ]


class UserSatisfactionOptimizer:
    """Optimizes user satisfaction."""

    def __init__(self):
        self.satisfaction_scores: Dict[str, List[float]] = {}
        self.feature_ratings: Dict[str, float] = {}
        self.improvement_areas: List[str] = []

    def record_satisfaction(self, user_id: str, score: float) -> None:
        """Record user satisfaction."""
        if user_id not in self.satisfaction_scores:
            self.satisfaction_scores[user_id] = []
        self.satisfaction_scores[user_id].append(score)

    def rate_feature(self, feature_name: str, rating: float) -> None:
        """Rate feature."""
        self.feature_ratings[feature_name] = rating

    def get_satisfaction_metrics(self) -> Dict[str, Any]:
        """Get satisfaction metrics."""
        all_scores = [
            score for scores in self.satisfaction_scores.values()
            for score in scores
        ]

        avg_satisfaction = sum(all_scores) / len(all_scores) if all_scores else 0

        poorly_rated = sorted(
            self.feature_ratings.items(),
            key=lambda x: x[1]
        )[:3]

        return {
            "avg_satisfaction": avg_satisfaction,
            "users_surveyed": len(self.satisfaction_scores),
            "poorly_rated_features": poorly_rated
        }

    def identify_improvement_areas(self) -> List[str]:
        """Identify areas needing improvement."""
        return [
            feature for feature, rating in self.feature_ratings.items()
            if rating < 0.6
        ]


class AutonomousOptimizationEngine:
    """Main autonomous optimization orchestrator."""

    def __init__(self):
        self.strategy = OptimizationStrategy.BALANCED
        self.goals: Dict[str, OptimizationGoal] = {}
        self.performance = PerformanceOptimizer()
        self.cost = CostOptimizer()
        self.reliability = ReliabilityOptimizer()
        self.satisfaction = UserSatisfactionOptimizer()
        self.active_optimizations: List[str] = []
        self.optimization_count = 0

    def set_strategy(self, strategy: OptimizationStrategy) -> None:
        """Set optimization strategy."""
        self.strategy = strategy

    def add_goal(self, goal: OptimizationGoal) -> None:
        """Add optimization goal."""
        self.goals[goal.goal_id] = goal

    def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run single optimization cycle."""
        self.optimization_count += 1

        results = {
            "cycle_number": self.optimization_count,
            "strategy": self.strategy.value,
            "optimizations": []
        }

        if self.strategy in [OptimizationStrategy.PERFORMANCE, OptimizationStrategy.BALANCED]:
            perf_results = self.performance.get_optimization_summary()
            results["optimizations"].append(("performance", perf_results))

        if self.strategy in [OptimizationStrategy.COST, OptimizationStrategy.BALANCED]:
            savings = self.cost.identify_cost_savings()
            results["optimizations"].append(("cost", savings))

        if self.strategy in [OptimizationStrategy.RELIABILITY, OptimizationStrategy.BALANCED]:
            failures = self.reliability.identify_failure_points()
            results["optimizations"].append(("reliability", failures))

        if self.strategy in [OptimizationStrategy.USER_SATISFACTION, OptimizationStrategy.BALANCED]:
            improvements = self.satisfaction.identify_improvement_areas()
            results["optimizations"].append(("satisfaction", improvements))

        return results

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get overall optimization status."""
        return {
            "strategy": self.strategy.value,
            "total_cycles": self.optimization_count,
            "active_optimizations": len(self.active_optimizations),
            "performance": self.performance.get_optimization_summary(),
            "reliability": self.reliability.get_reliability_metrics(),
            "satisfaction": self.satisfaction.get_satisfaction_metrics(),
            "cost": self.cost.get_cost_breakdown(),
            "goals": {
                gid: {
                    "target": g.target.value,
                    "progress": g.progress,
                    "achieved": g.is_achieved
                }
                for gid, g in self.goals.items()
            }
        }


# Global instance
_autonomous_optimizer = None


def get_autonomous_optimization_engine() -> AutonomousOptimizationEngine:
    """Get or create global autonomous optimization engine."""
    global _autonomous_optimizer
    if _autonomous_optimizer is None:
        _autonomous_optimizer = AutonomousOptimizationEngine()
    return _autonomous_optimizer
