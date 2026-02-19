"""
BAEL Continuous Improvement Engine
===================================

Learns from every operation to continuously improve.

"Perfection is not a destination, but an endless journey." — Ba'el
"""

import asyncio
import logging
import json
import hashlib
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("BAEL.ContinuousImprovement")


class ImprovementType(Enum):
    """Types of improvements."""
    PERFORMANCE = "performance"
    ACCURACY = "accuracy"
    RELIABILITY = "reliability"
    EFFICIENCY = "efficiency"
    QUALITY = "quality"
    SPEED = "speed"
    COST = "cost"


class LearningSource(Enum):
    """Sources of learning."""
    EXECUTION = "execution"         # From running tasks
    USER_FEEDBACK = "user_feedback" # From user ratings
    ERROR_ANALYSIS = "error_analysis"  # From errors
    COMPARISON = "comparison"       # From A/B tests
    METRICS = "metrics"             # From metrics analysis
    PATTERN = "pattern"             # From pattern recognition


class OptimizationType(Enum):
    """Types of optimizations."""
    PARAMETER = "parameter"         # Tune parameters
    ALGORITHM = "algorithm"         # Change algorithm
    STRATEGY = "strategy"           # Change strategy
    CACHING = "caching"             # Improve caching
    BATCHING = "batching"           # Improve batching
    PRUNING = "pruning"             # Remove unused code
    ORDERING = "ordering"           # Reorder operations


@dataclass
class Observation:
    """An observation for learning."""
    id: str
    operation: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    metrics: Dict[str, float]  # time_ms, memory_mb, etc.
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Set[str] = field(default_factory=set)


@dataclass
class Insight:
    """An insight derived from observations."""
    id: str
    insight_type: ImprovementType
    description: str
    confidence: float  # 0-1
    supporting_observations: int
    suggested_action: str
    estimated_impact: float  # % improvement
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Improvement:
    """An implemented improvement."""
    id: str
    insight_id: str
    improvement_type: ImprovementType
    optimization_type: OptimizationType
    description: str
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    improvement_percent: float
    applied_at: datetime = field(default_factory=datetime.now)
    rollback_available: bool = True


@dataclass
class ABTest:
    """An A/B test configuration."""
    id: str
    name: str
    variants: List[str]  # ["A", "B"]
    weights: List[float]  # [0.5, 0.5]
    metrics_to_track: List[str]
    start_time: datetime
    end_time: Optional[datetime] = None
    results: Dict[str, Dict[str, float]] = field(default_factory=dict)


class PatternRecognizer:
    """Recognizes patterns in observations."""

    def __init__(self):
        self._patterns: Dict[str, List[Observation]] = defaultdict(list)
        self._correlations: Dict[Tuple[str, str], float] = {}

    def add_observation(self, obs: Observation) -> None:
        """Add observation for pattern analysis."""
        # Group by operation
        self._patterns[obs.operation].append(obs)

        # Keep only recent observations
        cutoff = datetime.now() - timedelta(days=7)
        self._patterns[obs.operation] = [
            o for o in self._patterns[obs.operation] if o.timestamp > cutoff
        ]

    def find_patterns(self, operation: str) -> List[Dict[str, Any]]:
        """Find patterns for an operation."""
        observations = self._patterns.get(operation, [])
        if len(observations) < 10:
            return []

        patterns = []

        # Success rate pattern
        success_count = sum(1 for o in observations if o.success)
        success_rate = success_count / len(observations)

        if success_rate < 0.8:
            # Analyze what leads to failure
            failed = [o for o in observations if not o.success]
            patterns.append({
                "type": "low_success_rate",
                "rate": success_rate,
                "sample_size": len(observations),
                "failed_count": len(failed),
            })

        # Performance patterns
        times = [o.metrics.get("time_ms", 0) for o in observations]
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)

            if max_time > avg_time * 3:
                patterns.append({
                    "type": "high_variance",
                    "avg_time": avg_time,
                    "max_time": max_time,
                    "variance_ratio": max_time / avg_time,
                })

        # Time-based patterns
        hourly_success = defaultdict(lambda: {"success": 0, "total": 0})
        for obs in observations:
            hour = obs.timestamp.hour
            hourly_success[hour]["total"] += 1
            if obs.success:
                hourly_success[hour]["success"] += 1

        # Find problematic hours
        for hour, stats in hourly_success.items():
            if stats["total"] >= 5:
                rate = stats["success"] / stats["total"]
                if rate < 0.7:
                    patterns.append({
                        "type": "time_based_failure",
                        "hour": hour,
                        "success_rate": rate,
                        "sample_size": stats["total"],
                    })

        return patterns

    def find_correlations(
        self,
        metric1: str,
        metric2: str,
        operation: str,
    ) -> float:
        """Find correlation between two metrics."""
        observations = self._patterns.get(operation, [])
        if len(observations) < 5:
            return 0.0

        values1 = [o.metrics.get(metric1, 0) for o in observations]
        values2 = [o.metrics.get(metric2, 0) for o in observations]

        # Pearson correlation
        n = len(values1)
        if n == 0:
            return 0.0

        sum1 = sum(values1)
        sum2 = sum(values2)
        sum1_sq = sum(v * v for v in values1)
        sum2_sq = sum(v * v for v in values2)
        sum_prod = sum(a * b for a, b in zip(values1, values2))

        numerator = n * sum_prod - sum1 * sum2
        denominator = ((n * sum1_sq - sum1 * sum1) * (n * sum2_sq - sum2 * sum2)) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator


class ParameterTuner:
    """Automatic parameter tuning."""

    def __init__(self):
        self._parameters: Dict[str, Dict[str, Any]] = {}
        self._results: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def register_parameter(
        self,
        name: str,
        default: Any,
        min_value: Any = None,
        max_value: Any = None,
        step: Any = None,
    ) -> None:
        """Register a tunable parameter."""
        self._parameters[name] = {
            "default": default,
            "current": default,
            "min": min_value,
            "max": max_value,
            "step": step,
        }

    def get_parameter(self, name: str) -> Any:
        """Get current parameter value."""
        if name in self._parameters:
            return self._parameters[name]["current"]
        return None

    def record_result(
        self,
        parameter: str,
        value: Any,
        performance: float,  # Higher is better
    ) -> None:
        """Record performance for a parameter value."""
        self._results[parameter].append({
            "value": value,
            "performance": performance,
        })

    def suggest_value(self, parameter: str) -> Any:
        """Suggest optimal value based on history."""
        if parameter not in self._parameters:
            return None

        config = self._parameters[parameter]
        results = self._results.get(parameter, [])

        if len(results) < 3:
            return config["current"]

        # Find best performing value
        best = max(results, key=lambda x: x["performance"])

        # If better than current, suggest it
        current_perf = next(
            (r["performance"] for r in results if r["value"] == config["current"]),
            0
        )

        if best["performance"] > current_perf * 1.1:  # 10% improvement threshold
            return best["value"]

        return config["current"]

    def tune(self, parameter: str) -> Any:
        """Get tuned value and update."""
        suggested = self.suggest_value(parameter)
        if parameter in self._parameters:
            self._parameters[parameter]["current"] = suggested
        return suggested


class ContinuousImprovementEngine:
    """
    Engine for continuous system improvement.

    Features:
    - Observation collection
    - Pattern recognition
    - Insight generation
    - A/B testing
    - Parameter tuning
    - Improvement tracking
    """

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path.home() / ".bael" / "improvements"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._observations: List[Observation] = []
        self._insights: List[Insight] = []
        self._improvements: List[Improvement] = []
        self._ab_tests: Dict[str, ABTest] = {}

        self._pattern_recognizer = PatternRecognizer()
        self._parameter_tuner = ParameterTuner()

        self._analysis_callbacks: List[Callable] = []

        # Load existing data
        self._load_state()

    def _load_state(self) -> None:
        """Load saved state."""
        state_file = self.storage_path / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)

                # Load insights
                for i in data.get("insights", []):
                    self._insights.append(Insight(
                        id=i["id"],
                        insight_type=ImprovementType(i["insight_type"]),
                        description=i["description"],
                        confidence=i["confidence"],
                        supporting_observations=i["supporting_observations"],
                        suggested_action=i["suggested_action"],
                        estimated_impact=i["estimated_impact"],
                    ))

                # Load improvements
                for imp in data.get("improvements", []):
                    self._improvements.append(Improvement(
                        id=imp["id"],
                        insight_id=imp["insight_id"],
                        improvement_type=ImprovementType(imp["improvement_type"]),
                        optimization_type=OptimizationType(imp["optimization_type"]),
                        description=imp["description"],
                        before_metrics=imp["before_metrics"],
                        after_metrics=imp["after_metrics"],
                        improvement_percent=imp["improvement_percent"],
                    ))
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

    def _save_state(self) -> None:
        """Save current state."""
        state_file = self.storage_path / "state.json"
        data = {
            "insights": [
                {
                    "id": i.id,
                    "insight_type": i.insight_type.value,
                    "description": i.description,
                    "confidence": i.confidence,
                    "supporting_observations": i.supporting_observations,
                    "suggested_action": i.suggested_action,
                    "estimated_impact": i.estimated_impact,
                }
                for i in self._insights[-100:]  # Keep last 100
            ],
            "improvements": [
                {
                    "id": imp.id,
                    "insight_id": imp.insight_id,
                    "improvement_type": imp.improvement_type.value,
                    "optimization_type": imp.optimization_type.value,
                    "description": imp.description,
                    "before_metrics": imp.before_metrics,
                    "after_metrics": imp.after_metrics,
                    "improvement_percent": imp.improvement_percent,
                }
                for imp in self._improvements[-100:]
            ],
        }

        with open(state_file, "w") as f:
            json.dump(data, f, indent=2)

    def observe(
        self,
        operation: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        metrics: Dict[str, float],
        success: bool,
        tags: Set[str] = None,
    ) -> Observation:
        """Record an observation."""
        obs = Observation(
            id=hashlib.sha256(f"{operation}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
            operation=operation,
            inputs=inputs,
            outputs=outputs,
            metrics=metrics,
            success=success,
            tags=tags or set(),
        )

        self._observations.append(obs)
        self._pattern_recognizer.add_observation(obs)

        # Keep observations bounded
        if len(self._observations) > 10000:
            self._observations = self._observations[-10000:]

        # Trigger analysis callbacks
        for callback in self._analysis_callbacks:
            try:
                callback(obs)
            except Exception:
                pass

        return obs

    def register_analysis_callback(self, callback: Callable[[Observation], None]) -> None:
        """Register callback for new observations."""
        self._analysis_callbacks.append(callback)

    async def analyze(self, operation: str = None) -> List[Insight]:
        """Analyze observations and generate insights."""
        new_insights = []

        operations = [operation] if operation else list(set(o.operation for o in self._observations))

        for op in operations:
            # Get patterns
            patterns = self._pattern_recognizer.find_patterns(op)

            for pattern in patterns:
                insight = self._generate_insight(op, pattern)
                if insight:
                    self._insights.append(insight)
                    new_insights.append(insight)

        self._save_state()
        return new_insights

    def _generate_insight(self, operation: str, pattern: Dict[str, Any]) -> Optional[Insight]:
        """Generate insight from pattern."""
        pattern_type = pattern.get("type")

        if pattern_type == "low_success_rate":
            return Insight(
                id=hashlib.sha256(f"{operation}{pattern_type}".encode()).hexdigest()[:16],
                insight_type=ImprovementType.RELIABILITY,
                description=f"Operation '{operation}' has low success rate: {pattern['rate']:.0%}",
                confidence=min(pattern["sample_size"] / 50, 1.0),  # More samples = more confidence
                supporting_observations=pattern["sample_size"],
                suggested_action=f"Add error handling and retry logic for '{operation}'",
                estimated_impact=20.0,  # 20% improvement potential
            )

        elif pattern_type == "high_variance":
            return Insight(
                id=hashlib.sha256(f"{operation}{pattern_type}".encode()).hexdigest()[:16],
                insight_type=ImprovementType.PERFORMANCE,
                description=f"Operation '{operation}' has high time variance ({pattern['variance_ratio']:.1f}x)",
                confidence=0.7,
                supporting_observations=100,
                suggested_action=f"Investigate outliers for '{operation}' - consider caching or batching",
                estimated_impact=30.0,
            )

        elif pattern_type == "time_based_failure":
            return Insight(
                id=hashlib.sha256(f"{operation}{pattern_type}{pattern['hour']}".encode()).hexdigest()[:16],
                insight_type=ImprovementType.RELIABILITY,
                description=f"Operation '{operation}' fails more at hour {pattern['hour']}",
                confidence=min(pattern["sample_size"] / 20, 1.0),
                supporting_observations=pattern["sample_size"],
                suggested_action=f"Schedule maintenance/backups outside hour {pattern['hour']}",
                estimated_impact=10.0,
            )

        return None

    def create_ab_test(
        self,
        name: str,
        variants: List[str],
        metrics_to_track: List[str],
        weights: List[float] = None,
    ) -> ABTest:
        """Create an A/B test."""
        if weights is None:
            weights = [1.0 / len(variants)] * len(variants)

        test = ABTest(
            id=hashlib.sha256(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
            name=name,
            variants=variants,
            weights=weights,
            metrics_to_track=metrics_to_track,
            start_time=datetime.now(),
        )

        self._ab_tests[name] = test
        return test

    def get_ab_variant(self, test_name: str, user_id: str = None) -> Optional[str]:
        """Get variant for A/B test (deterministic based on user_id)."""
        if test_name not in self._ab_tests:
            return None

        test = self._ab_tests[test_name]

        if user_id:
            # Deterministic assignment based on user_id
            hash_val = int(hashlib.sha256(f"{test_name}{user_id}".encode()).hexdigest(), 16)
            random_val = (hash_val % 1000) / 1000.0
        else:
            import random
            random_val = random.random()

        cumulative = 0.0
        for variant, weight in zip(test.variants, test.weights):
            cumulative += weight
            if random_val < cumulative:
                return variant

        return test.variants[-1]

    def record_ab_result(
        self,
        test_name: str,
        variant: str,
        metrics: Dict[str, float],
    ) -> None:
        """Record result for A/B test."""
        if test_name not in self._ab_tests:
            return

        test = self._ab_tests[test_name]

        if variant not in test.results:
            test.results[variant] = {m: 0.0 for m in test.metrics_to_track}
            test.results[variant]["_count"] = 0

        test.results[variant]["_count"] += 1
        for metric in test.metrics_to_track:
            if metric in metrics:
                # Running average
                count = test.results[variant]["_count"]
                old_avg = test.results[variant][metric]
                test.results[variant][metric] = old_avg + (metrics[metric] - old_avg) / count

    def get_ab_results(self, test_name: str) -> Dict[str, Any]:
        """Get results of A/B test."""
        if test_name not in self._ab_tests:
            return {}

        test = self._ab_tests[test_name]

        if len(test.results) < 2:
            return {"status": "insufficient_data", "results": test.results}

        # Find winner
        winner = None
        best_score = float("-inf")

        for variant, metrics in test.results.items():
            # Simple: sum of all metrics (assuming higher is better)
            score = sum(v for k, v in metrics.items() if k != "_count")
            if score > best_score:
                best_score = score
                winner = variant

        return {
            "status": "completed",
            "winner": winner,
            "results": test.results,
            "sample_sizes": {v: int(test.results[v].get("_count", 0)) for v in test.variants},
        }

    def register_tunable_parameter(
        self,
        name: str,
        default: Any,
        min_value: Any = None,
        max_value: Any = None,
    ) -> None:
        """Register a tunable parameter."""
        self._parameter_tuner.register_parameter(name, default, min_value, max_value)

    def get_tuned_parameter(self, name: str, performance: float = None) -> Any:
        """Get tuned parameter value."""
        if performance is not None:
            current = self._parameter_tuner.get_parameter(name)
            self._parameter_tuner.record_result(name, current, performance)

        return self._parameter_tuner.tune(name)

    def record_improvement(
        self,
        insight_id: str,
        improvement_type: ImprovementType,
        optimization_type: OptimizationType,
        description: str,
        before_metrics: Dict[str, float],
        after_metrics: Dict[str, float],
    ) -> Improvement:
        """Record an implemented improvement."""
        # Calculate improvement percentage
        total_before = sum(before_metrics.values())
        total_after = sum(after_metrics.values())

        if total_before > 0:
            improvement_percent = ((total_after - total_before) / total_before) * 100
        else:
            improvement_percent = 0.0

        improvement = Improvement(
            id=hashlib.sha256(f"{insight_id}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
            insight_id=insight_id,
            improvement_type=improvement_type,
            optimization_type=optimization_type,
            description=description,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            improvement_percent=improvement_percent,
        )

        self._improvements.append(improvement)
        self._save_state()

        logger.info(f"Improvement recorded: {description} ({improvement_percent:+.1f}%)")

        return improvement

    def get_summary(self) -> Dict[str, Any]:
        """Get improvement summary."""
        total_improvement = sum(imp.improvement_percent for imp in self._improvements)

        by_type = defaultdict(list)
        for imp in self._improvements:
            by_type[imp.improvement_type.value].append(imp.improvement_percent)

        return {
            "total_observations": len(self._observations),
            "total_insights": len(self._insights),
            "total_improvements": len(self._improvements),
            "total_improvement_percent": total_improvement,
            "improvements_by_type": {
                k: sum(v) for k, v in by_type.items()
            },
            "active_ab_tests": len(self._ab_tests),
            "pending_insights": len([i for i in self._insights if i.confidence > 0.7]),
        }


# =============================================================================
# DECORATOR
# =============================================================================

_improvement_engine = ContinuousImprovementEngine()


def observe(operation: str, tags: Set[str] = None):
    """Decorator to observe function execution."""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            import time
            start = time.time()
            success = True
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = (time.time() - start) * 1000
                _improvement_engine.observe(
                    operation=operation,
                    inputs={"args": str(args)[:100], "kwargs": str(kwargs)[:100]},
                    outputs={"result": str(result)[:100] if result else None},
                    metrics={"time_ms": duration},
                    success=success,
                    tags=tags,
                )

        def sync_wrapper(*args, **kwargs):
            import time
            start = time.time()
            success = True
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = (time.time() - start) * 1000
                _improvement_engine.observe(
                    operation=operation,
                    inputs={"args": str(args)[:100], "kwargs": str(kwargs)[:100]},
                    outputs={"result": str(result)[:100] if result else None},
                    metrics={"time_ms": duration},
                    success=success,
                    tags=tags,
                )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_improvement_engine() -> ContinuousImprovementEngine:
    """Get the global improvement engine."""
    return _improvement_engine
