"""
Adaptive Learning System for BAEL Phase 2

Learns from outcomes and continuously improves strategies. Tracks performance
patterns, adjusts parameters, and evolves approach based on feedback.

Key Components:
- Outcome tracking and analysis
- Performance pattern detection
- Strategy adjustment and optimization
- Feedback integration
- Learning history management
- Continuous improvement loops
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


class OutcomeType(str, Enum):
    """Types of learning outcomes."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    UNDEFINED = "undefined"


class LearningDomain(str, Enum):
    """Domains where learning occurs."""
    TOOL_SELECTION = "tool_selection"
    PARAMETER_TUNING = "parameter_tuning"
    STRATEGY_ADAPTATION = "strategy_adaptation"
    ERROR_RECOVERY = "error_recovery"
    PERFORMANCE = "performance"
    USER_PREFERENCES = "user_preferences"


@dataclass
class Outcome:
    """Result of an action or strategy."""
    action_id: str
    action_description: str
    outcome_type: OutcomeType
    success_score: float  # 0.0 to 1.0
    execution_time: float  # milliseconds
    resource_usage: Dict[str, float]  # CPU, memory, etc.
    feedback: str = ""
    domain: LearningDomain = LearningDomain.PERFORMANCE
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "action_description": self.action_description,
            "outcome_type": self.outcome_type.value,
            "success_score": self.success_score,
            "execution_time": self.execution_time,
            "resource_usage": self.resource_usage,
            "feedback": self.feedback,
            "domain": self.domain.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class PerformanceMetric:
    """Performance metric tracking."""
    metric_name: str
    current_value: float
    target_value: float
    historical_values: List[Tuple[datetime, float]] = field(default_factory=list)
    trend: str = "stable"  # 'improving', 'stable', 'declining'
    last_updated: datetime = field(default_factory=datetime.now)

    def add_value(self, value: float) -> None:
        """Add a new value to history."""
        self.current_value = value
        self.historical_values.append((datetime.now(), value))
        self._calculate_trend()
        self.last_updated = datetime.now()

    def _calculate_trend(self) -> None:
        """Calculate trend from historical data."""
        if len(self.historical_values) < 2:
            self.trend = "stable"
            return

        recent = self.historical_values[-10:]  # Last 10 values
        if len(recent) < 2:
            self.trend = "stable"
            return

        values = [v for _, v in recent]
        avg_early = statistics.mean(values[: len(values) // 2])
        avg_late = statistics.mean(values[len(values) // 2 :])

        if avg_late > avg_early * 1.05:
            self.trend = "improving"
        elif avg_late < avg_early * 0.95:
            self.trend = "declining"
        else:
            self.trend = "stable"


@dataclass
class StrategyAdjustment:
    """Record of strategy adjustments."""
    adjustment_id: str
    domain: LearningDomain
    old_parameters: Dict[str, Any]
    new_parameters: Dict[str, Any]
    rationale: str
    expected_improvement: float  # Percentage
    actual_improvement: float = 0.0
    applied_at: datetime = field(default_factory=datetime.now)
    verified_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "adjustment_id": self.adjustment_id,
            "domain": self.domain.value,
            "old_parameters": self.old_parameters,
            "new_parameters": self.new_parameters,
            "rationale": self.rationale,
            "expected_improvement": self.expected_improvement,
            "actual_improvement": self.actual_improvement,
            "applied_at": self.applied_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "metadata": self.metadata,
        }


class PerformanceAnalyzer:
    """Analyzes performance patterns and trends."""

    def __init__(self):
        """Initialize analyzer."""
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.baselines: Dict[str, float] = {}

    def track_metric(self, name: str, value: float, target: float) -> None:
        """Track a performance metric."""
        if name not in self.metrics:
            self.metrics[name] = PerformanceMetric(name, value, target)
            self.baselines[name] = value
        else:
            self.metrics[name].add_value(value)

    def get_improvement(self, metric_name: str) -> float:
        """
        Calculate improvement from baseline.

        Returns percentage improvement (0.0 to 1.0+).
        """
        if metric_name not in self.metrics:
            return 0.0

        baseline = self.baselines.get(metric_name, 1.0)
        current = self.metrics[metric_name].current_value

        if baseline == 0:
            return 0.0

        return (current - baseline) / baseline

    def detect_anomalies(self, metric_name: str, threshold: float = 2.0) -> List[float]:
        """
        Detect anomalies in metric values.

        Args:
            metric_name: Name of metric to analyze
            threshold: Standard deviations for anomaly threshold

        Returns:
            List of anomalous values
        """
        if metric_name not in self.metrics:
            return []

        values = [v for _, v in self.metrics[metric_name].historical_values]
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        stdev = statistics.stdev(values)

        anomalies = [
            v for v in values if abs(v - mean) > threshold * stdev
        ]
        return anomalies

    def get_recommendations(self, metric_name: str) -> List[str]:
        """Get recommendations for metric improvement."""
        if metric_name not in self.metrics:
            return []

        metric = self.metrics[metric_name]
        recommendations = []

        # Check trend
        if metric.trend == "declining":
            recommendations.append(
                f"{metric_name} is declining. Review recent changes."
            )

        # Check vs target
        if metric.current_value < metric.target_value * 0.8:
            recommendations.append(
                f"{metric_name} is below target. Consider optimization."
            )

        # Check for anomalies
        anomalies = self.detect_anomalies(metric_name)
        if anomalies:
            recommendations.append(
                f"Anomalies detected in {metric_name}. Investigate causes."
            )

        return recommendations


class OutcomeAnalyzer:
    """Analyzes outcomes to identify patterns."""

    def __init__(self):
        """Initialize analyzer."""
        self.outcomes: List[Outcome] = []
        self.patterns: Dict[str, Dict[str, float]] = defaultdict(dict)

    def record_outcome(self, outcome: Outcome) -> None:
        """Record an outcome."""
        self.outcomes.append(outcome)
        self._update_patterns(outcome)

    def _update_patterns(self, outcome: Outcome) -> None:
        """Update learned patterns from outcome."""
        domain = outcome.domain.value

        if domain not in self.patterns:
            self.patterns[domain] = {
                "total_attempts": 0,
                "successes": 0,
                "avg_success_score": 0.0,
                "avg_execution_time": 0.0,
            }

        patterns = self.patterns[domain]
        patterns["total_attempts"] = patterns.get("total_attempts", 0) + 1

        if outcome.outcome_type == OutcomeType.SUCCESS:
            patterns["successes"] = patterns.get("successes", 0) + 1

        # Update averages
        attempts = patterns["total_attempts"]
        patterns["avg_success_score"] = (
            patterns.get("avg_success_score", 0) * (attempts - 1) + outcome.success_score
        ) / attempts

        patterns["avg_execution_time"] = (
            patterns.get("avg_execution_time", 0) * (attempts - 1) +
            outcome.execution_time
        ) / attempts

    def get_success_rate(self, domain: Optional[LearningDomain] = None) -> float:
        """Get success rate for a domain."""
        if domain:
            domain_str = domain.value
            if domain_str in self.patterns:
                patterns = self.patterns[domain_str]
                total = patterns.get("total_attempts", 1)
                successes = patterns.get("successes", 0)
                return successes / total if total > 0 else 0.0

        # Overall success rate
        total = len(self.outcomes)
        successes = sum(
            1 for o in self.outcomes if o.outcome_type == OutcomeType.SUCCESS
        )
        return successes / total if total > 0 else 0.0

    def identify_high_performers(self) -> List[Tuple[str, float]]:
        """Identify high-performing actions."""
        action_scores = defaultdict(list)

        for outcome in self.outcomes:
            action_scores[outcome.action_description].append(
                outcome.success_score
            )

        performers = [
            (action, statistics.mean(scores))
            for action, scores in action_scores.items()
            if len(scores) >= 3
        ]

        performers.sort(key=lambda x: x[1], reverse=True)
        return performers[:10]

    def identify_weak_performers(self) -> List[Tuple[str, float]]:
        """Identify low-performing actions."""
        performers = self.identify_high_performers()
        return performers[::-1][:10]


class LearningStrategy:
    """Implements learning and adaptation strategy."""

    def __init__(self, domain: LearningDomain):
        """Initialize strategy."""
        self.domain = domain
        self.outcome_analyzer = OutcomeAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.adjustments: List[StrategyAdjustment] = []
        self.current_parameters: Dict[str, Any] = {}

    def learn_from_outcome(self, outcome: Outcome) -> None:
        """Learn from an outcome."""
        outcome.domain = self.domain
        self.outcome_analyzer.record_outcome(outcome)
        self._trigger_adaptation()

    def _trigger_adaptation(self) -> None:
        """Check if adaptation is needed."""
        success_rate = self.outcome_analyzer.get_success_rate(self.domain)

        if success_rate < 0.6:  # Below threshold
            self.propose_adjustment()

    def propose_adjustment(self) -> Optional[StrategyAdjustment]:
        """Propose parameter adjustment."""
        # Analyze weak performers
        weak = self.outcome_analyzer.identify_weak_performers()

        if not weak:
            return None

        adjustment_id = f"adj_{self.domain.value}_{datetime.now().timestamp()}"

        new_params = self._calculate_new_parameters(weak)

        adjustment = StrategyAdjustment(
            adjustment_id=adjustment_id,
            domain=self.domain,
            old_parameters=self.current_parameters.copy(),
            new_parameters=new_params,
            rationale=f"Low success rate detected for {weak[0][0]}",
            expected_improvement=0.15,  # 15% expected improvement
        )

        self.adjustments.append(adjustment)
        self.current_parameters = new_params
        return adjustment

    def _calculate_new_parameters(
        self, weak_performers: List[Tuple[str, float]]
    ) -> Dict[str, Any]:
        """Calculate new parameters based on analysis."""
        new_params = self.current_parameters.copy()

        # Increase exploration if success rate is low
        if "exploration_rate" in new_params:
            new_params["exploration_rate"] = min(
                new_params["exploration_rate"] * 1.2, 1.0
            )

        # Adjust confidence threshold
        if "confidence_threshold" in new_params:
            new_params["confidence_threshold"] = max(
                new_params["confidence_threshold"] * 0.9, 0.3
            )

        return new_params

    def verify_improvement(self, adjustment: StrategyAdjustment) -> bool:
        """Verify if adjustment improved performance."""
        previous_rate = self.outcome_analyzer.get_success_rate(self.domain)

        # Check if we should record improvement
        if adjustment.verified_at is None:
            adjustment.actual_improvement = (
                (previous_rate - 0.5) * 100
            ) if previous_rate > 0.5 else 0.0
            adjustment.verified_at = datetime.now()
            return adjustment.actual_improvement > 0

        return False


class AdaptiveLearner:
    """Main adaptive learning system."""

    def __init__(self):
        """Initialize adaptive learner."""
        self.strategies: Dict[LearningDomain, LearningStrategy] = {}
        self.learning_history: List[Dict[str, Any]] = []
        self.callbacks: List[Callable[[str, Dict[str, Any]], None]] = []

    def register_strategy(self, domain: LearningDomain) -> LearningStrategy:
        """Register a learning strategy for a domain."""
        if domain not in self.strategies:
            self.strategies[domain] = LearningStrategy(domain)
        return self.strategies[domain]

    def record_outcome(self, outcome: Outcome) -> None:
        """Record outcome for learning."""
        strategy = self.strategies.get(
            outcome.domain,
            self.register_strategy(outcome.domain)
        )
        strategy.learn_from_outcome(outcome)
        self._trigger_callbacks("outcome_recorded", outcome.to_dict())

    def get_strategy(self, domain: LearningDomain) -> Optional[LearningStrategy]:
        """Get strategy for domain."""
        return self.strategies.get(domain)

    def get_success_rate(self, domain: Optional[LearningDomain] = None) -> float:
        """Get overall or domain-specific success rate."""
        if domain:
            strategy = self.strategies.get(domain)
            if strategy:
                return strategy.outcome_analyzer.get_success_rate(domain)

        # Average across all domains
        rates = [
            s.outcome_analyzer.get_success_rate(s.domain)
            for s in self.strategies.values()
        ]
        return statistics.mean(rates) if rates else 0.0

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get improvement recommendations."""
        recommendations = []

        for domain, strategy in self.strategies.items():
            success_rate = strategy.outcome_analyzer.get_success_rate(domain)

            if success_rate < 0.7:
                recommendations.append({
                    "domain": domain.value,
                    "current_success_rate": success_rate,
                    "action": "Consider strategy adjustment",
                    "urgency": "high" if success_rate < 0.5 else "medium",
                })

        return recommendations

    def export_learning_profile(self) -> Dict[str, Any]:
        """Export complete learning profile."""
        profile = {
            "timestamp": datetime.now().isoformat(),
            "overall_success_rate": self.get_success_rate(),
            "domains": {},
            "recommendations": self.get_recommendations(),
        }

        for domain, strategy in self.strategies.items():
            profile["domains"][domain.value] = {
                "success_rate": strategy.outcome_analyzer.get_success_rate(domain),
                "total_attempts": len(strategy.outcome_analyzer.outcomes),
                "adjustments": len(strategy.adjustments),
                "current_parameters": strategy.current_parameters,
            }

        return profile

    def register_callback(
        self, callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Register callback for learning events."""
        self.callbacks.append(callback)

    def _trigger_callbacks(self, event: str, data: Dict[str, Any]) -> None:
        """Trigger all registered callbacks."""
        for callback in self.callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# Global adaptive learner instance
_adaptive_learner = None


def get_adaptive_learner() -> AdaptiveLearner:
    """Get or create global adaptive learner."""
    global _adaptive_learner
    if _adaptive_learner is None:
        _adaptive_learner = AdaptiveLearner()
    return _adaptive_learner
