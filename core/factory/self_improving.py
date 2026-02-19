"""
BAEL Self-Improving Engine
===========================

Self-improvement and optimization capabilities.
Enables BAEL to learn and improve over time.

Features:
- Performance tracking
- Pattern learning
- Automatic optimization
- A/B testing
- Feedback integration
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """Types of optimizations."""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    COST = "cost"
    RELIABILITY = "reliability"
    LATENCY = "latency"


class LearningMode(Enum):
    """Learning modes."""
    PASSIVE = "passive"      # Learn from observations
    ACTIVE = "active"        # Actively experiment
    REINFORCEMENT = "reinforcement"  # Learn from rewards


@dataclass
class ImprovementMetrics:
    """Metrics for measuring improvements."""
    # Performance
    execution_time_ms: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0

    # Quality
    output_quality: float = 0.0
    accuracy: float = 0.0

    # Resource usage
    memory_mb: float = 0.0
    api_calls: int = 0
    cost: float = 0.0

    # Reliability
    success_rate: float = 0.0
    uptime: float = 0.0

    def improvement_score(self, baseline: "ImprovementMetrics") -> float:
        """Calculate improvement score vs baseline."""
        if not baseline:
            return 0.0

        scores = []

        # Time improvement (lower is better)
        if baseline.execution_time_ms > 0:
            time_imp = 1 - (self.execution_time_ms / baseline.execution_time_ms)
            scores.append(time_imp)

        # Quality improvement (higher is better)
        if baseline.output_quality > 0:
            quality_imp = (self.output_quality / baseline.output_quality) - 1
            scores.append(quality_imp)

        # Error rate improvement (lower is better)
        if baseline.error_rate > 0:
            error_imp = 1 - (self.error_rate / baseline.error_rate)
            scores.append(error_imp)

        return sum(scores) / max(len(scores), 1)


@dataclass
class Observation:
    """An observation for learning."""
    timestamp: datetime
    context: Dict[str, Any]
    action: str
    result: Any
    metrics: ImprovementMetrics
    feedback: Optional[float] = None  # -1 to 1


@dataclass
class Pattern:
    """A learned pattern."""
    id: str
    name: str
    description: str = ""

    # Pattern definition
    conditions: Dict[str, Any] = field(default_factory=dict)
    action: str = ""

    # Performance
    success_count: int = 0
    failure_count: int = 0
    avg_improvement: float = 0.0

    # Confidence
    confidence: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


@dataclass
class Optimization:
    """An optimization to apply."""
    id: str
    type: OptimizationType
    description: str

    # Implementation
    apply_func: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Impact
    expected_improvement: float = 0.0
    actual_improvement: float = 0.0

    # Status
    applied: bool = False
    applied_at: Optional[datetime] = None

    # Validation
    validated: bool = False
    validation_passed: bool = False


@dataclass
class LearningConfig:
    """Learning configuration."""
    mode: LearningMode = LearningMode.PASSIVE

    # Learning parameters
    learning_rate: float = 0.1
    exploration_rate: float = 0.1
    discount_factor: float = 0.95

    # Thresholds
    min_observations: int = 10
    min_confidence: float = 0.7
    improvement_threshold: float = 0.05

    # A/B testing
    ab_test_duration_hours: float = 24.0
    ab_test_sample_size: int = 100


class SelfImprovingEngine:
    """
    Self-improving engine for BAEL.
    """

    def __init__(
        self,
        config: Optional[LearningConfig] = None,
    ):
        self.config = config or LearningConfig()

        # Learning storage
        self.observations: List[Observation] = []
        self.patterns: Dict[str, Pattern] = {}
        self.optimizations: Dict[str, Optimization] = {}

        # Baseline metrics
        self.baselines: Dict[str, ImprovementMetrics] = {}

        # A/B tests
        self.ab_tests: Dict[str, Dict[str, Any]] = {}

        # Callbacks
        self._on_improvement: List[Callable[[Optimization], None]] = []
        self._on_pattern_learned: List[Callable[[Pattern], None]] = []

        # Stats
        self.stats = {
            "observations": 0,
            "patterns_learned": 0,
            "optimizations_applied": 0,
            "total_improvement": 0.0,
        }

    def observe(
        self,
        context: Dict[str, Any],
        action: str,
        result: Any,
        metrics: ImprovementMetrics,
        feedback: Optional[float] = None,
    ) -> Observation:
        """
        Record an observation.

        Args:
            context: Context of the observation
            action: Action taken
            result: Result of action
            metrics: Performance metrics
            feedback: Optional feedback score (-1 to 1)

        Returns:
            Recorded observation
        """
        self.stats["observations"] += 1

        observation = Observation(
            timestamp=datetime.now(),
            context=context,
            action=action,
            result=result,
            metrics=metrics,
            feedback=feedback,
        )

        self.observations.append(observation)

        # Limit observation history
        if len(self.observations) > 10000:
            self.observations = self.observations[-10000:]

        # Trigger learning if in active mode
        if self.config.mode == LearningMode.ACTIVE:
            self._try_learn_pattern(observation)

        return observation

    def set_baseline(
        self,
        name: str,
        metrics: ImprovementMetrics,
    ) -> None:
        """Set baseline metrics for comparison."""
        self.baselines[name] = metrics

    def _try_learn_pattern(self, observation: Observation) -> Optional[Pattern]:
        """Try to learn a pattern from observation."""
        # Find similar observations
        similar = self._find_similar_observations(observation)

        if len(similar) < self.config.min_observations:
            return None

        # Check if there's a consistent pattern
        success_count = sum(1 for o in similar if o.feedback and o.feedback > 0)
        success_rate = success_count / len(similar)

        if success_rate < self.config.min_confidence:
            return None

        # Create pattern
        pattern_id = hashlib.md5(
            json.dumps(observation.context, sort_keys=True).encode()
        ).hexdigest()[:8]

        pattern = Pattern(
            id=pattern_id,
            name=f"Pattern from {observation.action}",
            conditions=observation.context,
            action=observation.action,
            success_count=success_count,
            failure_count=len(similar) - success_count,
            confidence=success_rate,
        )

        # Calculate average improvement
        improvements = []
        for obs in similar:
            if obs.feedback:
                improvements.append(obs.feedback)

        if improvements:
            pattern.avg_improvement = sum(improvements) / len(improvements)

        # Store pattern
        self.patterns[pattern_id] = pattern
        self.stats["patterns_learned"] += 1

        # Notify callbacks
        for callback in self._on_pattern_learned:
            try:
                callback(pattern)
            except Exception as e:
                logger.error(f"Pattern learned callback error: {e}")

        logger.info(f"Learned pattern: {pattern.name} (confidence: {pattern.confidence:.2f})")

        return pattern

    def _find_similar_observations(
        self,
        target: Observation,
        threshold: float = 0.8,
    ) -> List[Observation]:
        """Find observations similar to target."""
        similar = []

        for obs in self.observations:
            if obs == target:
                continue

            # Simple similarity based on matching context keys
            target_keys = set(target.context.keys())
            obs_keys = set(obs.context.keys())

            common_keys = target_keys & obs_keys
            if not common_keys:
                continue

            matching = sum(
                1 for k in common_keys
                if target.context.get(k) == obs.context.get(k)
            )

            similarity = matching / len(common_keys)

            if similarity >= threshold:
                similar.append(obs)

        return similar

    def suggest_optimization(
        self,
        metrics: ImprovementMetrics,
        baseline_name: str = "default",
    ) -> List[Optimization]:
        """
        Suggest optimizations based on metrics.

        Args:
            metrics: Current metrics
            baseline_name: Baseline to compare against

        Returns:
            List of suggested optimizations
        """
        suggestions = []
        baseline = self.baselines.get(baseline_name)

        # Performance optimizations
        if metrics.execution_time_ms > 1000:
            suggestions.append(Optimization(
                id="cache_results",
                type=OptimizationType.PERFORMANCE,
                description="Enable result caching",
                parameters={"cache_ttl": 3600},
                expected_improvement=0.3,
            ))

        # Quality optimizations
        if metrics.output_quality < 0.8:
            suggestions.append(Optimization(
                id="improve_prompts",
                type=OptimizationType.QUALITY,
                description="Optimize prompts for better quality",
                parameters={"use_examples": True},
                expected_improvement=0.2,
            ))

        # Cost optimizations
        if metrics.cost > 0.1:
            suggestions.append(Optimization(
                id="use_cheaper_model",
                type=OptimizationType.COST,
                description="Switch to more cost-effective model",
                parameters={"model": "gpt-3.5-turbo"},
                expected_improvement=0.5,
            ))

        # Error rate optimizations
        if metrics.error_rate > 0.1:
            suggestions.append(Optimization(
                id="add_retries",
                type=OptimizationType.RELIABILITY,
                description="Add retry logic with backoff",
                parameters={"max_retries": 3, "backoff": 2.0},
                expected_improvement=0.4,
            ))

        # Based on learned patterns
        for pattern in self.patterns.values():
            if pattern.confidence >= self.config.min_confidence:
                if pattern.avg_improvement > self.config.improvement_threshold:
                    suggestions.append(Optimization(
                        id=f"pattern_{pattern.id}",
                        type=OptimizationType.PERFORMANCE,
                        description=f"Apply learned pattern: {pattern.name}",
                        parameters={"pattern_id": pattern.id},
                        expected_improvement=pattern.avg_improvement,
                    ))

        return suggestions

    def apply_optimization(
        self,
        optimization: Optimization,
        target: Any,
    ) -> bool:
        """
        Apply an optimization.

        Args:
            optimization: Optimization to apply
            target: Target to optimize

        Returns:
            Success status
        """
        try:
            if optimization.apply_func:
                optimization.apply_func(target, optimization.parameters)

            optimization.applied = True
            optimization.applied_at = datetime.now()

            self.optimizations[optimization.id] = optimization
            self.stats["optimizations_applied"] += 1

            # Notify callbacks
            for callback in self._on_improvement:
                try:
                    callback(optimization)
                except Exception as e:
                    logger.error(f"Improvement callback error: {e}")

            logger.info(f"Applied optimization: {optimization.description}")

            return True

        except Exception as e:
            logger.error(f"Failed to apply optimization: {e}")
            return False

    def start_ab_test(
        self,
        name: str,
        variants: Dict[str, Any],
    ) -> str:
        """
        Start an A/B test.

        Args:
            name: Test name
            variants: Variant configurations

        Returns:
            Test ID
        """
        test_id = hashlib.md5(f"{name}:{time.time()}".encode()).hexdigest()[:8]

        self.ab_tests[test_id] = {
            "name": name,
            "variants": variants,
            "started_at": datetime.now(),
            "samples": {v: [] for v in variants},
            "winner": None,
        }

        logger.info(f"Started A/B test: {name} ({test_id})")

        return test_id

    def record_ab_result(
        self,
        test_id: str,
        variant: str,
        metrics: ImprovementMetrics,
    ) -> None:
        """Record A/B test result."""
        test = self.ab_tests.get(test_id)
        if not test:
            return

        if variant in test["samples"]:
            test["samples"][variant].append(metrics)

    def conclude_ab_test(self, test_id: str) -> Optional[str]:
        """
        Conclude an A/B test and determine winner.

        Returns:
            Winning variant name
        """
        test = self.ab_tests.get(test_id)
        if not test:
            return None

        # Calculate average metrics for each variant
        variant_scores = {}
        for variant, samples in test["samples"].items():
            if samples:
                avg_quality = sum(s.output_quality for s in samples) / len(samples)
                avg_time = sum(s.execution_time_ms for s in samples) / len(samples)
                # Score favoring quality and speed
                score = avg_quality - (avg_time / 10000)
                variant_scores[variant] = score

        if not variant_scores:
            return None

        # Determine winner
        winner = max(variant_scores, key=variant_scores.get)
        test["winner"] = winner

        logger.info(f"A/B test {test_id} winner: {winner}")

        return winner

    def get_improvement_report(self) -> Dict[str, Any]:
        """Generate improvement report."""
        # Calculate overall improvement
        improvements = []
        for opt in self.optimizations.values():
            if opt.validated and opt.validation_passed:
                improvements.append(opt.actual_improvement)

        avg_improvement = sum(improvements) / max(len(improvements), 1)

        # Top patterns
        top_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.confidence * p.avg_improvement,
            reverse=True,
        )[:5]

        # Recent optimizations
        recent_opts = sorted(
            [o for o in self.optimizations.values() if o.applied],
            key=lambda o: o.applied_at or datetime.min,
            reverse=True,
        )[:5]

        return {
            "total_observations": len(self.observations),
            "patterns_learned": len(self.patterns),
            "optimizations_applied": len([o for o in self.optimizations.values() if o.applied]),
            "average_improvement": avg_improvement,
            "top_patterns": [
                {"name": p.name, "confidence": p.confidence, "improvement": p.avg_improvement}
                for p in top_patterns
            ],
            "recent_optimizations": [
                {"id": o.id, "type": o.type.value, "improvement": o.actual_improvement}
                for o in recent_opts
            ],
        }

    def on_improvement(self, callback: Callable[[Optimization], None]) -> None:
        """Register improvement callback."""
        self._on_improvement.append(callback)

    def on_pattern_learned(self, callback: Callable[[Pattern], None]) -> None:
        """Register pattern learned callback."""
        self._on_pattern_learned.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "active_ab_tests": len([t for t in self.ab_tests.values() if not t.get("winner")]),
            "patterns_count": len(self.patterns),
            "optimizations_count": len(self.optimizations),
        }


def demo():
    """Demonstrate self-improving engine."""
    print("=" * 60)
    print("BAEL Self-Improving Engine Demo")
    print("=" * 60)

    engine = SelfImprovingEngine(LearningConfig(
        mode=LearningMode.ACTIVE,
        min_observations=3,
    ))

    # Set baseline
    baseline = ImprovementMetrics(
        execution_time_ms=500,
        output_quality=0.7,
        error_rate=0.1,
    )
    engine.set_baseline("default", baseline)

    print("\nBaseline metrics set")

    # Record observations
    for i in range(5):
        metrics = ImprovementMetrics(
            execution_time_ms=450 - i * 20,
            output_quality=0.75 + i * 0.03,
            error_rate=0.08 - i * 0.01,
        )

        engine.observe(
            context={"task_type": "generation", "complexity": "medium"},
            action="use_cache",
            result={"success": True},
            metrics=metrics,
            feedback=0.5 + i * 0.1,
        )

    print(f"Recorded {len(engine.observations)} observations")
    print(f"Learned {len(engine.patterns)} patterns")

    # Suggest optimizations
    current = ImprovementMetrics(
        execution_time_ms=2000,
        output_quality=0.6,
        error_rate=0.15,
        cost=0.2,
    )

    suggestions = engine.suggest_optimization(current)
    print(f"\nSuggested optimizations ({len(suggestions)}):")
    for opt in suggestions:
        print(f"  - {opt.type.value}: {opt.description} (expected: +{opt.expected_improvement:.0%})")

    # Start A/B test
    test_id = engine.start_ab_test("model_comparison", {
        "gpt-4": {"model": "gpt-4"},
        "gpt-3.5": {"model": "gpt-3.5-turbo"},
    })

    # Record test results
    engine.record_ab_result(test_id, "gpt-4", ImprovementMetrics(output_quality=0.9))
    engine.record_ab_result(test_id, "gpt-3.5", ImprovementMetrics(output_quality=0.75))

    winner = engine.conclude_ab_test(test_id)
    print(f"\nA/B test winner: {winner}")

    # Get report
    report = engine.get_improvement_report()
    print(f"\nImprovement report:")
    print(f"  Observations: {report['total_observations']}")
    print(f"  Patterns learned: {report['patterns_learned']}")
    print(f"  Avg improvement: {report['average_improvement']:.2%}")

    print(f"\nStats: {engine.get_stats()}")


if __name__ == "__main__":
    demo()
