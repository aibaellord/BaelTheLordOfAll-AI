"""
BAEL Perceptual Learning Engine
=================================

Expertise in perception.
Gibson's differentiation and attunement.

"Ba'el perceives with precision." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.PerceptualLearning")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class LearningMechanism(Enum):
    """Perceptual learning mechanisms."""
    DIFFERENTIATION = auto()   # Gibson: distinguishing features
    ATTUNEMENT = auto()        # Gibson: sensitivity to information
    UNITIZATION = auto()       # Goldstone: chunking features
    ATTENTION_WEIGHTING = auto()  # Selective attention


class ExpertiseDomain(Enum):
    """Domains of perceptual expertise."""
    FACE_RECOGNITION = auto()
    RADIOGRAPHY = auto()
    CHESS = auto()
    ORNITHOLOGY = auto()
    FINGERPRINTS = auto()
    WINE_TASTING = auto()
    MUSIC = auto()


class PerceptualDimension(Enum):
    """Perceptual dimensions."""
    SIZE = auto()
    COLOR = auto()
    SHAPE = auto()
    ORIENTATION = auto()
    TEXTURE = auto()
    MOTION = auto()
    SPATIAL_FREQUENCY = auto()


class DiscriminationLevel(Enum):
    """Discrimination ability level."""
    NOVICE = 1
    DEVELOPING = 2
    COMPETENT = 3
    PROFICIENT = 4
    EXPERT = 5


@dataclass
class PerceptualFeature:
    """
    A perceptual feature.
    """
    name: str
    dimension: PerceptualDimension
    value: float
    diagnostic: bool  # Distinguishes categories


@dataclass
class Stimulus:
    """
    A perceptual stimulus.
    """
    id: str
    category: str
    features: List[PerceptualFeature]


@dataclass
class DiscriminationTrial:
    """
    A discrimination trial.
    """
    stimulus1: Stimulus
    stimulus2: Stimulus
    same_category: bool
    response_correct: bool
    response_time: float
    difficulty: float


@dataclass
class PerceptualLearningResult:
    """
    Result of perceptual learning.
    """
    mechanism: LearningMechanism
    trials_completed: int
    initial_threshold: float
    final_threshold: float
    improvement: float


@dataclass
class PerceptualMetrics:
    """
    Perceptual learning metrics.
    """
    discrimination_level: DiscriminationLevel
    threshold: float
    d_prime: float
    attention_weights: Dict[str, float]


# ============================================================================
# DIFFERENTIATION LEARNER
# ============================================================================

class DifferentiationLearner:
    """
    Gibson's differentiation learning.

    "Ba'el distinguishes the subtle." — Ba'el
    """

    def __init__(self):
        """Initialize learner."""
        self._threshold: float = 0.5  # Discrimination threshold
        self._feature_weights: Dict[str, float] = defaultdict(lambda: 1.0)
        self._exposure_count = 0

        self._lock = threading.RLock()

    def expose(
        self,
        stimuli: List[Stimulus],
        category_labels: bool = True
    ) -> None:
        """Expose to stimuli."""
        for stimulus in stimuli:
            self._exposure_count += 1

            for feature in stimulus.features:
                if feature.diagnostic:
                    # Increase weight for diagnostic features
                    self._feature_weights[feature.name] += 0.05
                else:
                    # Decrease weight for non-diagnostic
                    self._feature_weights[feature.name] = max(
                        0.1, self._feature_weights[feature.name] - 0.01
                    )

        # Improve threshold with exposure
        self._threshold = max(0.1, self._threshold - 0.01)

    def discriminate(
        self,
        stimulus1: Stimulus,
        stimulus2: Stimulus
    ) -> Tuple[bool, float]:
        """Attempt to discriminate two stimuli."""
        # Calculate perceptual distance
        distance = self._calculate_weighted_distance(
            stimulus1, stimulus2
        )

        # Can discriminate if distance > threshold
        can_discriminate = distance > self._threshold

        # Response time faster with clear discrimination
        rt = 500 + (self._threshold / distance) * 200 if distance > 0 else 1000

        return can_discriminate, rt

    def _calculate_weighted_distance(
        self,
        s1: Stimulus,
        s2: Stimulus
    ) -> float:
        """Calculate weighted perceptual distance."""
        distance = 0.0

        s1_features = {f.name: f.value for f in s1.features}
        s2_features = {f.name: f.value for f in s2.features}

        all_features = set(s1_features.keys()) | set(s2_features.keys())

        for feature_name in all_features:
            v1 = s1_features.get(feature_name, 0)
            v2 = s2_features.get(feature_name, 0)

            weight = self._feature_weights[feature_name]
            distance += weight * abs(v1 - v2)

        return distance

    def get_threshold(self) -> float:
        """Get current discrimination threshold."""
        return self._threshold


# ============================================================================
# ATTUNEMENT LEARNER
# ============================================================================

class AttunementLearner:
    """
    Gibson's attunement - sensitivity to information.

    "Ba'el becomes sensitive." — Ba'el
    """

    def __init__(self):
        """Initialize learner."""
        self._sensitivities: Dict[str, float] = defaultdict(lambda: 0.5)
        self._affordances_detected: Set[str] = set()

        self._lock = threading.RLock()

    def attune_to_feature(
        self,
        feature_name: str,
        training_trials: int = 10
    ) -> float:
        """Attune to a specific feature."""
        initial = self._sensitivities[feature_name]

        for _ in range(training_trials):
            improvement = 0.05 * (1 - self._sensitivities[feature_name])
            self._sensitivities[feature_name] = min(
                1.0,
                self._sensitivities[feature_name] + improvement
            )

        return self._sensitivities[feature_name] - initial

    def detect_affordance(
        self,
        stimulus: Stimulus,
        affordance: str
    ) -> Tuple[bool, float]:
        """Detect an affordance."""
        # Sensitivity to relevant features affects detection
        relevant_sensitivity = 0.0
        count = 0

        for feature in stimulus.features:
            if feature.name in self._sensitivities:
                relevant_sensitivity += self._sensitivities[feature.name]
                count += 1

        if count > 0:
            avg_sensitivity = relevant_sensitivity / count
        else:
            avg_sensitivity = 0.5

        detected = random.random() < avg_sensitivity

        if detected:
            self._affordances_detected.add(affordance)

        return detected, avg_sensitivity

    def get_sensitivity(
        self,
        feature_name: str
    ) -> float:
        """Get sensitivity to feature."""
        return self._sensitivities[feature_name]


# ============================================================================
# UNITIZATION LEARNER
# ============================================================================

class UnitizationLearner:
    """
    Goldstone's unitization - feature chunking.

    "Ba'el perceives wholes." — Ba'el
    """

    def __init__(self):
        """Initialize learner."""
        self._units: Dict[str, List[str]] = {}  # Unit name -> features
        self._unit_strengths: Dict[str, float] = defaultdict(float)

        self._lock = threading.RLock()

    def create_unit(
        self,
        unit_name: str,
        features: List[str]
    ) -> None:
        """Create a perceptual unit from features."""
        self._units[unit_name] = features
        self._unit_strengths[unit_name] = 0.3  # Initial weak binding

    def strengthen_unit(
        self,
        unit_name: str,
        amount: float = 0.1
    ) -> None:
        """Strengthen a unit through practice."""
        if unit_name in self._units:
            self._unit_strengths[unit_name] = min(
                1.0,
                self._unit_strengths[unit_name] + amount
            )

    def recognize_as_unit(
        self,
        stimulus: Stimulus,
        unit_name: str
    ) -> Tuple[bool, float]:
        """Recognize stimulus as a unit."""
        if unit_name not in self._units:
            return False, 0.0

        unit_features = self._units[unit_name]
        stimulus_feature_names = [f.name for f in stimulus.features]

        # Check feature overlap
        overlap = len(
            set(unit_features) & set(stimulus_feature_names)
        ) / len(unit_features)

        unit_strength = self._unit_strengths[unit_name]

        # Recognition depends on overlap and strength
        recognition_prob = overlap * unit_strength
        recognized = random.random() < recognition_prob

        if recognized:
            # Strengthen unit through use
            self.strengthen_unit(unit_name, 0.02)

        return recognized, recognition_prob

    def get_processing_benefit(
        self,
        unit_name: str
    ) -> float:
        """Get processing benefit from unitization."""
        # Stronger units processed faster (fewer elements)
        if unit_name not in self._units:
            return 0.0

        n_features = len(self._units[unit_name])
        strength = self._unit_strengths[unit_name]

        # Benefit: process as 1 unit instead of n features
        return (1 - 1/n_features) * strength


# ============================================================================
# PERCEPTUAL LEARNING ENGINE
# ============================================================================

class PerceptualLearningEngine:
    """
    Complete perceptual learning engine.

    "Ba'el's perceptual expertise." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._differentiation = DifferentiationLearner()
        self._attunement = AttunementLearner()
        self._unitization = UnitizationLearner()

        self._stimuli: Dict[str, Stimulus] = {}
        self._trials: List[DiscriminationTrial] = []
        self._learning_results: List[PerceptualLearningResult] = []

        self._stimulus_counter = 0
        self._current_level = DiscriminationLevel.NOVICE

        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._stimulus_counter += 1
        return f"stim_{self._stimulus_counter}"

    # Stimulus creation

    def create_stimulus(
        self,
        category: str,
        features: List[Tuple[str, PerceptualDimension, float, bool]]
    ) -> Stimulus:
        """Create a stimulus."""
        feature_objects = []
        for name, dimension, value, diagnostic in features:
            feature_objects.append(PerceptualFeature(
                name=name,
                dimension=dimension,
                value=value,
                diagnostic=diagnostic
            ))

        stimulus = Stimulus(
            id=self._generate_id(),
            category=category,
            features=feature_objects
        )

        self._stimuli[stimulus.id] = stimulus
        return stimulus

    def create_category_exemplars(
        self,
        category: str,
        n: int,
        prototype_features: List[Tuple[str, PerceptualDimension, float, bool]],
        variance: float = 0.1
    ) -> List[Stimulus]:
        """Create category exemplars with variation."""
        exemplars = []

        for _ in range(n):
            varied_features = []
            for name, dim, value, diag in prototype_features:
                varied_value = value + random.gauss(0, variance)
                varied_features.append((name, dim, varied_value, diag))

            exemplar = self.create_stimulus(category, varied_features)
            exemplars.append(exemplar)

        return exemplars

    # Training

    def train_differentiation(
        self,
        stimuli: List[Stimulus],
        trials: int = 50
    ) -> PerceptualLearningResult:
        """Train differentiation."""
        initial_threshold = self._differentiation.get_threshold()

        for _ in range(trials):
            self._differentiation.expose(stimuli, category_labels=True)

        final_threshold = self._differentiation.get_threshold()

        result = PerceptualLearningResult(
            mechanism=LearningMechanism.DIFFERENTIATION,
            trials_completed=trials,
            initial_threshold=initial_threshold,
            final_threshold=final_threshold,
            improvement=initial_threshold - final_threshold
        )

        self._learning_results.append(result)
        self._update_level()

        return result

    def train_attunement(
        self,
        feature_names: List[str],
        trials_per_feature: int = 20
    ) -> Dict[str, float]:
        """Train attunement to features."""
        improvements = {}

        for feature in feature_names:
            improvement = self._attunement.attune_to_feature(
                feature, trials_per_feature
            )
            improvements[feature] = improvement

        return improvements

    def train_unitization(
        self,
        unit_name: str,
        features: List[str],
        repetitions: int = 20
    ) -> float:
        """Train unitization."""
        self._unitization.create_unit(unit_name, features)

        for _ in range(repetitions):
            self._unitization.strengthen_unit(unit_name, 0.03)

        return self._unitization._unit_strengths[unit_name]

    # Testing

    def run_discrimination_trial(
        self,
        stimulus1: Stimulus,
        stimulus2: Stimulus
    ) -> DiscriminationTrial:
        """Run a discrimination trial."""
        same_category = stimulus1.category == stimulus2.category

        can_discriminate, rt = self._differentiation.discriminate(
            stimulus1, stimulus2
        )

        # If same category, correct is "same"
        # If different category, correct is "different"
        if same_category:
            correct = not can_discriminate
        else:
            correct = can_discriminate

        trial = DiscriminationTrial(
            stimulus1=stimulus1,
            stimulus2=stimulus2,
            same_category=same_category,
            response_correct=correct,
            response_time=rt,
            difficulty=self._differentiation.get_threshold()
        )

        self._trials.append(trial)
        return trial

    def run_discrimination_test(
        self,
        stimuli: List[Stimulus],
        n_trials: int = 20
    ) -> Dict[str, Any]:
        """Run discrimination test."""
        correct = 0
        rts = []

        for _ in range(n_trials):
            s1, s2 = random.sample(stimuli, 2)
            trial = self.run_discrimination_trial(s1, s2)

            if trial.response_correct:
                correct += 1
            rts.append(trial.response_time)

        accuracy = correct / n_trials

        return {
            'accuracy': accuracy,
            'mean_rt': sum(rts) / len(rts),
            'd_prime': self._calculate_d_prime(self._trials[-n_trials:]),
            'threshold': self._differentiation.get_threshold()
        }

    def _calculate_d_prime(
        self,
        trials: List[DiscriminationTrial]
    ) -> float:
        """Calculate d' from trials."""
        hits = sum(1 for t in trials if t.response_correct and not t.same_category)
        fas = sum(1 for t in trials if not t.response_correct and t.same_category)

        total_different = sum(1 for t in trials if not t.same_category)
        total_same = sum(1 for t in trials if t.same_category)

        hit_rate = hits / total_different if total_different > 0 else 0.5
        fa_rate = fas / total_same if total_same > 0 else 0.5

        # Avoid extreme values
        hit_rate = max(0.01, min(0.99, hit_rate))
        fa_rate = max(0.01, min(0.99, fa_rate))

        # Approximate z-transform
        z_hit = math.sqrt(2) * self._erfinv(2 * hit_rate - 1)
        z_fa = math.sqrt(2) * self._erfinv(2 * fa_rate - 1)

        return z_hit - z_fa

    def _erfinv(
        self,
        x: float
    ) -> float:
        """Approximate inverse error function."""
        # Approximation
        a = 0.147
        sign = 1 if x >= 0 else -1
        x = abs(x)

        if x >= 1:
            return sign * 3.0

        ln = math.log(1 - x * x)
        term1 = 2 / (math.pi * a) + ln / 2
        term2 = ln / a

        result = sign * math.sqrt(math.sqrt(term1 * term1 - term2) - term1)
        return result

    def _update_level(self) -> None:
        """Update expertise level."""
        threshold = self._differentiation.get_threshold()

        if threshold < 0.1:
            self._current_level = DiscriminationLevel.EXPERT
        elif threshold < 0.2:
            self._current_level = DiscriminationLevel.PROFICIENT
        elif threshold < 0.3:
            self._current_level = DiscriminationLevel.COMPETENT
        elif threshold < 0.4:
            self._current_level = DiscriminationLevel.DEVELOPING
        else:
            self._current_level = DiscriminationLevel.NOVICE

    # Analysis

    def get_feature_weights(self) -> Dict[str, float]:
        """Get learned feature weights."""
        return dict(self._differentiation._feature_weights)

    def get_sensitivities(self) -> Dict[str, float]:
        """Get attunement sensitivities."""
        return dict(self._attunement._sensitivities)

    def get_metrics(self) -> PerceptualMetrics:
        """Get perceptual metrics."""
        recent_trials = self._trials[-50:] if len(self._trials) >= 50 else self._trials

        return PerceptualMetrics(
            discrimination_level=self._current_level,
            threshold=self._differentiation.get_threshold(),
            d_prime=self._calculate_d_prime(recent_trials) if recent_trials else 0.0,
            attention_weights=dict(self._differentiation._feature_weights)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'stimuli': len(self._stimuli),
            'trials': len(self._trials),
            'expertise_level': self._current_level.name,
            'threshold': self._differentiation.get_threshold()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_perceptual_learning_engine() -> PerceptualLearningEngine:
    """Create perceptual learning engine."""
    return PerceptualLearningEngine()


def demonstrate_perceptual_learning() -> Dict[str, Any]:
    """Demonstrate perceptual learning."""
    engine = create_perceptual_learning_engine()

    # Create two categories of stimuli
    cat_a = engine.create_category_exemplars(
        "A", 10,
        [
            ("feature1", PerceptualDimension.SIZE, 0.3, True),
            ("feature2", PerceptualDimension.COLOR, 0.5, True),
            ("feature3", PerceptualDimension.SHAPE, 0.7, False)
        ],
        variance=0.1
    )

    cat_b = engine.create_category_exemplars(
        "B", 10,
        [
            ("feature1", PerceptualDimension.SIZE, 0.7, True),
            ("feature2", PerceptualDimension.COLOR, 0.5, True),
            ("feature3", PerceptualDimension.SHAPE, 0.3, False)
        ],
        variance=0.1
    )

    all_stimuli = cat_a + cat_b

    # Pre-training test
    pre_test = engine.run_discrimination_test(all_stimuli, 20)

    # Train differentiation
    diff_result = engine.train_differentiation(all_stimuli, 100)

    # Train attunement
    engine.train_attunement(["feature1", "feature2"], 30)

    # Post-training test
    post_test = engine.run_discrimination_test(all_stimuli, 20)

    metrics = engine.get_metrics()

    return {
        'pre_training': {
            'accuracy': pre_test['accuracy'],
            'threshold': diff_result.initial_threshold
        },
        'post_training': {
            'accuracy': post_test['accuracy'],
            'threshold': diff_result.final_threshold
        },
        'improvement': diff_result.improvement,
        'expertise_level': metrics.discrimination_level.name,
        'feature_weights': dict(list(engine.get_feature_weights().items())[:3]),
        'interpretation': (
            f"Threshold improved by {diff_result.improvement:.2f}, "
            f"reached {metrics.discrimination_level.name} level"
        )
    }


def get_perceptual_learning_facts() -> Dict[str, str]:
    """Get facts about perceptual learning."""
    return {
        'gibson': 'Differentiation: learning to detect distinguishing features',
        'attunement': 'Becoming sensitive to relevant information',
        'unitization': 'Goldstone: integrating features into single units',
        'attention_weighting': 'Highlighting diagnostic features',
        'expertise': 'Experts see meaningful patterns novices miss',
        'transfer': 'Specific to trained stimuli and tasks',
        'neural': 'Changes in early visual cortex with training',
        'long_lasting': 'Effects persist for months/years'
    }
