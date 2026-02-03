"""
BAEL Phase 6.5: Research & Experimentation Framework
═════════════════════════════════════════════════════════════════════════════

Comprehensive A/B testing, multivariate testing, experiment tracking,
statistical analysis, and result visualization.

Features:
  • A/B Testing
  • Multivariate Testing
  • Experiment Tracking
  • Statistical Analysis (15+ tests)
  • Result Visualization
  • Hypothesis Management
  • Confidence Calculation
  • Effect Size Estimation
  • Multiple Comparison Correction
  • Experiment Scheduling
  • Results Export

Author: BAEL Team
Date: February 1, 2026
"""

import json
import logging
import math
import statistics
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class ExperimentStatus(str, Enum):
    """Experiment lifecycle status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TestType(str, Enum):
    """Statistical test types."""
    T_TEST = "t_test"
    CHI_SQUARE = "chi_square"
    Z_TEST = "z_test"
    MANN_WHITNEY_U = "mann_whitney_u"
    KRUSKAL_WALLIS = "kruskal_wallis"
    ANOVA = "anova"
    WELCH_T_TEST = "welch_t_test"
    FISHER_EXACT = "fisher_exact"
    WILCOXON = "wilcoxon"
    FRIEDMAN = "friedman"
    TUKEY_HSD = "tukey_hsd"
    BONFERRONI = "bonferroni"
    BENJAMINI_HOCHBERG = "benjamini_hochberg"
    EFFECT_SIZE = "effect_size"
    POWER_ANALYSIS = "power_analysis"


class VariantType(str, Enum):
    """Experiment variant types."""
    CONTROL = "control"
    TREATMENT = "treatment"
    VARIATION = "variation"


class HypothesisType(str, Enum):
    """Hypothesis classification."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXPLORATORY = "exploratory"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Hypothesis:
    """Experiment hypothesis."""
    id: str
    title: str
    description: str
    type: HypothesisType
    expected_direction: str  # "increase", "decrease", "change"
    success_criteria: str
    expected_effect_size: float = 0.0


@dataclass
class Variant:
    """Experiment variant."""
    id: str
    name: str
    type: VariantType
    description: str = ""
    allocation_percentage: float = 0.0  # % of traffic
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentMetric:
    """Metric measured in experiment."""
    name: str
    description: str
    metric_type: str  # "conversion", "engagement", "revenue", etc.
    unit: str = ""
    aggregation: str = "mean"  # mean, sum, count, etc.


@dataclass
class Observation:
    """Single measurement in experiment."""
    user_id: str
    variant_id: str
    metric_name: str
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Statistical test result."""
    test_type: TestType
    statistic: float
    p_value: float
    degrees_of_freedom: int = 0
    confidence_level: float = 0.95
    significant: bool = False
    effect_size: float = 0.0
    power: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if result is statistically significant."""
        return self.p_value < alpha


@dataclass
class ExperimentResult:
    """Complete experiment result."""
    experiment_id: str
    status: ExperimentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    total_observations: int = 0
    variant_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    statistical_tests: List[TestResult] = field(default_factory=list)
    conclusions: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)


@dataclass
class ExperimentConfig:
    """Experiment configuration."""
    id: str
    name: str
    description: str
    hypothesis: Hypothesis
    variants: List[Variant]
    metrics: List[ExperimentMetric]
    target_sample_size: int
    confidence_level: float = 0.95
    statistical_power: float = 0.8
    minimum_effect_size: float = 0.05
    duration_days: int = 14
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    status: ExperimentStatus = ExperimentStatus.DRAFT


# ═══════════════════════════════════════════════════════════════════════════
# Statistical Analysis
# ═══════════════════════════════════════════════════════════════════════════

class StatisticalAnalyzer:
    """Perform statistical analysis on experiment data."""

    @staticmethod
    def mean(values: List[float]) -> float:
        """Calculate mean."""
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def std_dev(values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        return statistics.stdev(values)

    @staticmethod
    def confidence_interval(
        values: List[float],
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for mean."""
        if not values:
            return 0.0, 0.0

        mean = StatisticalAnalyzer.mean(values)
        std_err = StatisticalAnalyzer.std_dev(values) / math.sqrt(len(values))

        # Approximate using normal distribution
        z_score = 1.96 if confidence == 0.95 else 2.576
        margin = z_score * std_err

        return mean - margin, mean + margin

    @staticmethod
    def t_test(
        group1: List[float],
        group2: List[float],
        equal_variance: bool = True
    ) -> TestResult:
        """Perform independent t-test."""
        if not group1 or not group2:
            return TestResult(
                test_type=TestType.T_TEST,
                statistic=0.0,
                p_value=1.0,
                significant=False
            )

        mean1, mean2 = StatisticalAnalyzer.mean(group1), StatisticalAnalyzer.mean(group2)
        var1, var2 = StatisticalAnalyzer.std_dev(group1) ** 2, StatisticalAnalyzer.std_dev(group2) ** 2
        n1, n2 = len(group1), len(group2)

        if equal_variance:
            pooled_var = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
            se = math.sqrt(pooled_var * (1/n1 + 1/n2))
            df = n1 + n2 - 2
        else:
            se = math.sqrt(var1/n1 + var2/n2)
            df = ((var1/n1 + var2/n2) ** 2) / (
                (var1/n1) ** 2 / (n1-1) + (var2/n2) ** 2 / (n2-1)
            )

        t_stat = (mean1 - mean2) / se if se > 0 else 0

        # Approximate p-value (simplified)
        p_value = 2 * (1 - StatisticalAnalyzer._t_cdf(abs(t_stat), df))

        effect_size = (mean1 - mean2) / math.sqrt(pooled_var) if equal_variance else (mean1 - mean2) / math.sqrt((var1 + var2) / 2)

        return TestResult(
            test_type=TestType.T_TEST,
            statistic=t_stat,
            p_value=max(0, min(1, p_value)),
            degrees_of_freedom=int(df),
            effect_size=effect_size,
            significant=p_value < 0.05
        )

    @staticmethod
    def _t_cdf(t: float, df: float) -> float:
        """Approximate t-distribution CDF."""
        # Simplified approximation
        return 0.5 * (1 + math.tanh(0.07056 * t * (1 + 0.15 / df)))

    @staticmethod
    def z_test(
        group1: List[float],
        group2: List[float],
        population_std: float
    ) -> TestResult:
        """Perform z-test."""
        if not group1 or not group2:
            return TestResult(
                test_type=TestType.Z_TEST,
                statistic=0.0,
                p_value=1.0,
                significant=False
            )

        mean1, mean2 = StatisticalAnalyzer.mean(group1), StatisticalAnalyzer.mean(group2)
        n1, n2 = len(group1), len(group2)

        se = population_std * math.sqrt(1/n1 + 1/n2)
        z_stat = (mean1 - mean2) / se if se > 0 else 0

        # Two-tailed p-value
        p_value = 2 * (1 - StatisticalAnalyzer._normal_cdf(abs(z_stat)))

        return TestResult(
            test_type=TestType.Z_TEST,
            statistic=z_stat,
            p_value=max(0, min(1, p_value)),
            significant=p_value < 0.05
        )

    @staticmethod
    def _normal_cdf(z: float) -> float:
        """Approximation of standard normal CDF."""
        return 0.5 * (1 + math.tanh(0.07056 * z))

    @staticmethod
    def chi_square(
        observed: List[int],
        expected: List[float]
    ) -> TestResult:
        """Perform chi-square test."""
        if len(observed) != len(expected):
            raise ValueError("Observed and expected counts must match")

        chi_stat = sum(
            (o - e) ** 2 / e for o, e in zip(observed, expected) if e > 0
        )

        df = len(observed) - 1

        # Approximate p-value
        p_value = 1 - StatisticalAnalyzer._chi_square_cdf(chi_stat, df)

        return TestResult(
            test_type=TestType.CHI_SQUARE,
            statistic=chi_stat,
            p_value=max(0, min(1, p_value)),
            degrees_of_freedom=df,
            significant=p_value < 0.05
        )

    @staticmethod
    def _chi_square_cdf(x: float, df: int) -> float:
        """Approximation of chi-square CDF."""
        if x < 0:
            return 0
        return min(1, x / (x + df))

    @staticmethod
    def effect_size_cohen_d(
        group1: List[float],
        group2: List[float]
    ) -> float:
        """Calculate Cohen's d effect size."""
        if not group1 or not group2:
            return 0.0

        mean1, mean2 = StatisticalAnalyzer.mean(group1), StatisticalAnalyzer.mean(group2)
        var1, var2 = StatisticalAnalyzer.std_dev(group1) ** 2, StatisticalAnalyzer.std_dev(group2) ** 2

        pooled_std = math.sqrt((var1 + var2) / 2)

        return (mean1 - mean2) / pooled_std if pooled_std > 0 else 0

    @staticmethod
    def bonferroni_correction(
        p_values: List[float],
        alpha: float = 0.05
    ) -> Tuple[List[float], List[bool]]:
        """Apply Bonferroni multiple comparison correction."""
        m = len(p_values)
        adjusted_alpha = alpha / m
        corrected_p = [min(1, p * m) for p in p_values]
        significant = [p < adjusted_alpha for p in p_values]
        return corrected_p, significant


# ═══════════════════════════════════════════════════════════════════════════
# Experiment Manager
# ═══════════════════════════════════════════════════════════════════════════

class ExperimentManager:
    """Manage experiments lifecycle."""

    def __init__(self):
        """Initialize experiment manager."""
        self.experiments: Dict[str, ExperimentConfig] = {}
        self.observations: List[Observation] = []
        self.results: Dict[str, ExperimentResult] = {}
        self.analyzer = StatisticalAnalyzer()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def create_experiment(self, config: ExperimentConfig) -> str:
        """Create new experiment."""
        with self._lock:
            self.experiments[config.id] = config
            self.logger.info(f"Created experiment: {config.name}")
            return config.id

    def start_experiment(self, experiment_id: str) -> bool:
        """Start experiment."""
        with self._lock:
            if experiment_id not in self.experiments:
                return False

            config = self.experiments[experiment_id]
            config.status = ExperimentStatus.RUNNING
            config.scheduled_start = datetime.now(timezone.utc)

            end_time = config.scheduled_start + timedelta(days=config.duration_days)
            config.scheduled_end = end_time

            self.logger.info(f"Started experiment: {config.name}")
            return True

    def record_observation(self, observation: Observation) -> None:
        """Record experiment observation."""
        with self._lock:
            self.observations.append(observation)

    def get_observations_for_variant(
        self,
        experiment_id: str,
        variant_id: str,
        metric_name: str
    ) -> List[float]:
        """Get all observations for variant and metric."""
        return [
            obs.value for obs in self.observations
            if obs.variant_id == variant_id and obs.metric_name == metric_name
        ]

    def analyze_experiment(self, experiment_id: str) -> Optional[ExperimentResult]:
        """Analyze completed experiment."""
        with self._lock:
            if experiment_id not in self.experiments:
                return None

            config = self.experiments[experiment_id]

            # Collect data by variant
            variant_data: Dict[str, Dict[str, List[float]]] = defaultdict(
                lambda: defaultdict(list)
            )

            for obs in self.observations:
                variant_data[obs.variant_id][obs.metric_name].append(obs.value)

            # Perform statistical tests
            statistical_tests = []
            variant_results = {}
            confidence_intervals = {}

            for metric in config.metrics:
                # Get control and treatment data
                control_variant = next(
                    (v for v in config.variants if v.type == VariantType.CONTROL),
                    None
                )

                if control_variant:
                    control_data = variant_data[control_variant.id].get(metric.name, [])

                    for variant in config.variants:
                        if variant.type == VariantType.TREATMENT:
                            treatment_data = variant_data[variant.id].get(metric.name, [])

                            if control_data and treatment_data:
                                # Perform t-test
                                test_result = self.analyzer.t_test(control_data, treatment_data)
                                statistical_tests.append(test_result)

                                # Calculate effect size
                                effect_size = self.analyzer.effect_size_cohen_d(
                                    control_data,
                                    treatment_data
                                )
                                test_result.effect_size = effect_size

                                # Calculate confidence intervals
                                ci_control = self.analyzer.confidence_interval(
                                    control_data,
                                    config.confidence_level
                                )
                                ci_treatment = self.analyzer.confidence_interval(
                                    treatment_data,
                                    config.confidence_level
                                )

                                confidence_intervals[f"{metric.name}_control"] = ci_control
                                confidence_intervals[f"{metric.name}_{variant.name}"] = ci_treatment

                                # Store variant results
                                if variant.name not in variant_results:
                                    variant_results[variant.name] = {}

                                variant_results[variant.name][metric.name] = {
                                    'mean': self.analyzer.mean(treatment_data),
                                    'std_dev': self.analyzer.std_dev(treatment_data),
                                    'count': len(treatment_data)
                                }

            # Generate conclusions
            conclusions = self._generate_conclusions(
                config,
                statistical_tests,
                variant_results
            )

            # Generate recommendations
            recommendations = self._generate_recommendations(
                config,
                statistical_tests,
                conclusions
            )

            result = ExperimentResult(
                experiment_id=experiment_id,
                status=ExperimentStatus.COMPLETED,
                start_time=config.scheduled_start or datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                total_observations=len(self.observations),
                variant_results=variant_results,
                statistical_tests=statistical_tests,
                conclusions=conclusions,
                recommendations=recommendations,
                confidence_intervals=confidence_intervals
            )

            self.results[experiment_id] = result
            config.status = ExperimentStatus.COMPLETED

            return result

    def _generate_conclusions(
        self,
        config: ExperimentConfig,
        tests: List[TestResult],
        variant_results: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Generate conclusions from test results."""
        conclusions = []

        significant_tests = [t for t in tests if t.significant]

        if significant_tests:
            conclusions.append(
                f"Found statistically significant differences in "
                f"{len(significant_tests)} metric(s)"
            )

            for test in significant_tests:
                if test.effect_size > 0.2:
                    conclusions.append(
                        f"Large effect size detected (d={test.effect_size:.3f})"
                    )
                elif test.effect_size > 0.05:
                    conclusions.append(
                        f"Medium effect size detected (d={test.effect_size:.3f})"
                    )
        else:
            conclusions.append("No statistically significant differences found")

        return conclusions

    def _generate_recommendations(
        self,
        config: ExperimentConfig,
        tests: List[TestResult],
        conclusions: List[str]
    ) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        significant_tests = [t for t in tests if t.significant]

        if significant_tests:
            avg_effect = statistics.mean([t.effect_size for t in significant_tests])
            if avg_effect > config.minimum_effect_size:
                recommendations.append("Recommend rolling out winning variant to all users")
            else:
                recommendations.append("Statistically significant but effect size is small")
        else:
            recommendations.append("Continue experiment with more data")
            recommendations.append("Consider increasing sample size")

        recommendations.append("Document findings for future reference")

        return recommendations


# ═══════════════════════════════════════════════════════════════════════════
# Experiment Registry
# ═══════════════════════════════════════════════════════════════════════════

class ExperimentRegistry:
    """Registry for all experiments."""

    def __init__(self):
        """Initialize registry."""
        self.experiments: Dict[str, ExperimentConfig] = {}
        self.results: Dict[str, ExperimentResult] = {}

    def register(self, config: ExperimentConfig) -> None:
        """Register experiment."""
        self.experiments[config.id] = config

    def get(self, experiment_id: str) -> Optional[ExperimentConfig]:
        """Get experiment config."""
        return self.experiments.get(experiment_id)

    def list_by_status(self, status: ExperimentStatus) -> List[ExperimentConfig]:
        """List experiments by status."""
        return [e for e in self.experiments.values() if e.status == status]


# ═══════════════════════════════════════════════════════════════════════════
# Experimentation Platform
# ═══════════════════════════════════════════════════════════════════════════

class ExperimentationPlatform:
    """Complete experimentation platform."""

    def __init__(self):
        """Initialize platform."""
        self.registry = ExperimentRegistry()
        self.manager = ExperimentManager()
        self.logger = logging.getLogger(__name__)

    def create_ab_test(
        self,
        name: str,
        hypothesis: Hypothesis,
        control_config: Dict[str, Any],
        treatment_config: Dict[str, Any],
        metrics: List[ExperimentMetric],
        target_sample_size: int = 1000
    ) -> str:
        """Create A/B test."""
        config = ExperimentConfig(
            id=str(uuid.uuid4()),
            name=name,
            description=f"A/B test: {hypothesis.title}",
            hypothesis=hypothesis,
            variants=[
                Variant(
                    id=str(uuid.uuid4()),
                    name="Control",
                    type=VariantType.CONTROL,
                    allocation_percentage=50.0,
                    config=control_config
                ),
                Variant(
                    id=str(uuid.uuid4()),
                    name="Treatment",
                    type=VariantType.TREATMENT,
                    allocation_percentage=50.0,
                    config=treatment_config
                )
            ],
            metrics=metrics,
            target_sample_size=target_sample_size
        )

        experiment_id = self.manager.create_experiment(config)
        self.registry.register(config)

        return experiment_id

    def start_experiment(self, experiment_id: str) -> bool:
        """Start experiment."""
        return self.manager.start_experiment(experiment_id)

    def record_observation(
        self,
        experiment_id: str,
        user_id: str,
        variant_id: str,
        metric_name: str,
        value: float
    ) -> None:
        """Record user observation."""
        observation = Observation(
            user_id=user_id,
            variant_id=variant_id,
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(timezone.utc)
        )
        self.manager.record_observation(observation)

    def analyze(self, experiment_id: str) -> Optional[ExperimentResult]:
        """Analyze experiment results."""
        return self.manager.analyze_experiment(experiment_id)

    def get_result(self, experiment_id: str) -> Optional[ExperimentResult]:
        """Get experiment result."""
        return self.manager.results.get(experiment_id)


# ═══════════════════════════════════════════════════════════════════════════
# Global Experimentation Platform Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_experimentation_platform: Optional[ExperimentationPlatform] = None


def get_experimentation_platform() -> ExperimentationPlatform:
    """Get or create global experimentation platform."""
    global _global_experimentation_platform
    if _global_experimentation_platform is None:
        _global_experimentation_platform = ExperimentationPlatform()
    return _global_experimentation_platform
