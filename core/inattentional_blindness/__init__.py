"""
BAEL Inattentional Blindness Engine
=====================================

Failing to see what's right in front of you.
Mack & Rock's discovery.

"Ba'el sees all, even the unseen." — Ba'el
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

logger = logging.getLogger("BAEL.InattentionalBlindness")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class StimType(Enum):
    """Type of stimulus."""
    ATTENDED = auto()       # Task-relevant
    UNATTENDED = auto()     # Task-irrelevant
    CRITICAL = auto()       # The unexpected object


class Conspicuity(Enum):
    """How noticeable the critical stimulus is."""
    LOW = auto()            # Hard to see
    MEDIUM = auto()         # Moderate
    HIGH = auto()           # Very salient


class LoadLevel(Enum):
    """Attentional load level."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class SimilarityLevel(Enum):
    """Similarity to attended items."""
    LOW = auto()            # Very different
    MEDIUM = auto()         # Somewhat similar
    HIGH = auto()           # Very similar


@dataclass
class DisplayItem:
    """
    An item in the display.
    """
    id: str
    stim_type: StimType
    x: float
    y: float
    size: float
    color: str
    shape: str


@dataclass
class Trial:
    """
    A trial in the experiment.
    """
    id: str
    items: List[DisplayItem]
    primary_task: str
    has_critical: bool
    critical_item: Optional[DisplayItem]
    load: LoadLevel


@dataclass
class TrialResult:
    """
    Result of a trial.
    """
    trial_id: str
    primary_task_correct: bool
    noticed_critical: bool
    reported_features: Optional[Dict[str, str]]


@dataclass
class BlindnessMetrics:
    """
    Inattentional blindness metrics.
    """
    detection_rate: float
    blindness_rate: float
    by_conspicuity: Dict[str, float]
    by_load: Dict[str, float]


# ============================================================================
# INATTENTIONAL BLINDNESS MODEL
# ============================================================================

class InattentionalBlindnessModel:
    """
    Model of inattentional blindness.

    "Ba'el's attention model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base detection rates
        self._base_detection = 0.5

        # Conspicuity effects
        self._conspicuity_effects = {
            Conspicuity.LOW: -0.3,
            Conspicuity.MEDIUM: 0.0,
            Conspicuity.HIGH: 0.2
        }

        # Load effects (higher load = more blindness)
        self._load_effects = {
            LoadLevel.LOW: 0.2,
            LoadLevel.MEDIUM: 0.0,
            LoadLevel.HIGH: -0.2
        }

        # Similarity effects (similar = more blindness)
        self._similarity_effects = {
            SimilarityLevel.LOW: 0.15,
            SimilarityLevel.MEDIUM: 0.0,
            SimilarityLevel.HIGH: -0.15
        }

        # Location effects
        self._foveal_advantage = 0.2
        self._peripheral_penalty = 0.1

        # Expectation effect
        self._expectation_boost = 0.3

        self._lock = threading.RLock()

    def calculate_detection_probability(
        self,
        conspicuity: Conspicuity,
        load: LoadLevel,
        similarity: SimilarityLevel,
        is_foveal: bool = False,
        expected: bool = False
    ) -> float:
        """Calculate probability of detecting critical stimulus."""
        prob = self._base_detection

        # Conspicuity effect
        prob += self._conspicuity_effects[conspicuity]

        # Load effect
        prob += self._load_effects[load]

        # Similarity effect
        prob += self._similarity_effects[similarity]

        # Location effect
        if is_foveal:
            prob += self._foveal_advantage
        else:
            prob -= self._peripheral_penalty

        # Expectation effect
        if expected:
            prob += self._expectation_boost

        return max(0.0, min(1.0, prob))

    def calculate_feature_report_accuracy(
        self,
        detected: bool
    ) -> float:
        """Calculate accuracy of feature reports if detected."""
        if not detected:
            return 0.0

        # Even if detected, features may not be accurate
        return random.uniform(0.5, 0.9)


# ============================================================================
# INATTENTIONAL BLINDNESS SYSTEM
# ============================================================================

class InattentionalBlindnessSystem:
    """
    Inattentional blindness simulation system.

    "Ba'el's awareness system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = InattentionalBlindnessModel()

        self._trials: Dict[str, Trial] = {}
        self._results: List[TrialResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_trial(
        self,
        n_attended: int = 4,
        has_critical: bool = True,
        load: LoadLevel = LoadLevel.MEDIUM
    ) -> Trial:
        """Create a trial."""
        items = []

        # Add attended items
        for i in range(n_attended):
            item = DisplayItem(
                id=self._generate_id(),
                stim_type=StimType.ATTENDED,
                x=random.uniform(-5, 5),
                y=random.uniform(-5, 5),
                size=1.0,
                color="white",
                shape="cross"
            )
            items.append(item)

        # Add critical item
        critical = None
        if has_critical:
            critical = DisplayItem(
                id=self._generate_id(),
                stim_type=StimType.CRITICAL,
                x=random.uniform(-3, 3),
                y=random.uniform(-3, 3),
                size=1.5,
                color="red",
                shape="square"
            )
            items.append(critical)

        trial = Trial(
            id=self._generate_id(),
            items=items,
            primary_task="count_crosses",
            has_critical=has_critical,
            critical_item=critical,
            load=load
        )

        self._trials[trial.id] = trial

        return trial

    def run_trial(
        self,
        trial_id: str,
        conspicuity: Conspicuity = Conspicuity.MEDIUM,
        similarity: SimilarityLevel = SimilarityLevel.LOW
    ) -> TrialResult:
        """Run a trial."""
        trial = self._trials.get(trial_id)
        if not trial:
            return None

        # Primary task performance
        primary_correct = random.random() < 0.9

        # Critical stimulus detection
        noticed = False
        reported = None

        if trial.has_critical:
            # Check if foveal
            is_foveal = (
                abs(trial.critical_item.x) < 2 and
                abs(trial.critical_item.y) < 2
            )

            detection_prob = self._model.calculate_detection_probability(
                conspicuity, trial.load, similarity, is_foveal
            )

            noticed = random.random() < detection_prob

            if noticed:
                # Report features
                accuracy = self._model.calculate_feature_report_accuracy(noticed)

                reported = {
                    'color': trial.critical_item.color if random.random() < accuracy else 'unknown',
                    'shape': trial.critical_item.shape if random.random() < accuracy else 'unknown'
                }

        result = TrialResult(
            trial_id=trial_id,
            primary_task_correct=primary_correct,
            noticed_critical=noticed,
            reported_features=reported
        )

        self._results.append(result)

        return result


# ============================================================================
# INATTENTIONAL BLINDNESS PARADIGM
# ============================================================================

class InattentionalBlindnessParadigm:
    """
    Inattentional blindness paradigm.

    "Ba'el's blindness study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_mack_rock_paradigm(
        self,
        n_trials: int = 30
    ) -> Dict[str, Any]:
        """Run Mack & Rock paradigm."""
        system = InattentionalBlindnessSystem()

        noticed = 0
        not_noticed = 0

        for _ in range(n_trials):
            trial = system.create_trial(has_critical=True)
            result = system.run_trial(trial.id)

            if result.noticed_critical:
                noticed += 1
            else:
                not_noticed += 1

        detection_rate = noticed / n_trials
        blindness_rate = not_noticed / n_trials

        return {
            'noticed': noticed,
            'not_noticed': not_noticed,
            'detection_rate': detection_rate,
            'blindness_rate': blindness_rate,
            'interpretation': f'{blindness_rate:.0%} failed to notice unexpected object'
        }

    def run_gorilla_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run Simons & Chabris gorilla paradigm."""
        # Simulate the famous basketball/gorilla study
        system = InattentionalBlindnessSystem()

        # High load condition (counting passes)
        results = []

        for _ in range(50):
            trial = system.create_trial(
                n_attended=6,  # Players
                has_critical=True,  # Gorilla
                load=LoadLevel.HIGH  # Counting is demanding
            )

            result = system.run_trial(
                trial.id,
                conspicuity=Conspicuity.HIGH,  # Gorilla is obvious
                similarity=SimilarityLevel.LOW  # Very different from players
            )

            results.append(result)

        noticed = sum(1 for r in results if r.noticed_critical)
        detection_rate = noticed / len(results)

        return {
            'noticed': noticed,
            'total': len(results),
            'detection_rate': detection_rate,
            'blindness_rate': 1 - detection_rate,
            'interpretation': 'Even salient unexpected objects often missed'
        }

    def run_load_study(
        self
    ) -> Dict[str, Any]:
        """Study load effects."""
        results = {}

        for load in LoadLevel:
            system = InattentionalBlindnessSystem()

            trial_results = []
            for _ in range(30):
                trial = system.create_trial(load=load)
                result = system.run_trial(trial.id)
                trial_results.append(result)

            noticed = sum(1 for r in trial_results if r.noticed_critical)

            results[load.name] = {
                'detection_rate': noticed / len(trial_results)
            }

        return {
            'by_load': results,
            'interpretation': 'Higher load = more blindness'
        }

    def run_conspicuity_study(
        self
    ) -> Dict[str, Any]:
        """Study conspicuity effects."""
        results = {}

        for conspicuity in Conspicuity:
            system = InattentionalBlindnessSystem()

            trial_results = []
            for _ in range(30):
                trial = system.create_trial()
                result = system.run_trial(trial.id, conspicuity=conspicuity)
                trial_results.append(result)

            noticed = sum(1 for r in trial_results if r.noticed_critical)

            results[conspicuity.name] = {
                'detection_rate': noticed / len(trial_results)
            }

        return {
            'by_conspicuity': results,
            'interpretation': 'More conspicuous = higher detection'
        }

    def run_similarity_study(
        self
    ) -> Dict[str, Any]:
        """Study similarity effects."""
        results = {}

        for similarity in SimilarityLevel:
            system = InattentionalBlindnessSystem()

            trial_results = []
            for _ in range(30):
                trial = system.create_trial()
                result = system.run_trial(trial.id, similarity=similarity)
                trial_results.append(result)

            noticed = sum(1 for r in trial_results if r.noticed_critical)

            results[similarity.name] = {
                'detection_rate': noticed / len(trial_results)
            }

        return {
            'by_similarity': results,
            'interpretation': 'Similar items more likely missed'
        }

    def run_expectation_study(
        self
    ) -> Dict[str, Any]:
        """Study expectation effects."""
        system = InattentionalBlindnessSystem()

        conditions = {
            'unexpected': 0.0,
            'expected': 1.0
        }

        results = {}

        for condition, expectation in conditions.items():
            # Modify model for expectation
            original_boost = system._model._expectation_boost

            trial_results = []
            for _ in range(30):
                trial = system.create_trial()

                # Expectation affects detection
                if condition == 'expected':
                    # More likely to notice
                    result = system.run_trial(trial.id, conspicuity=Conspicuity.HIGH)
                else:
                    result = system.run_trial(trial.id)

                trial_results.append(result)

            noticed = sum(1 for r in trial_results if r.noticed_critical)

            results[condition] = {
                'detection_rate': noticed / len(trial_results)
            }

        return {
            'by_expectation': results,
            'interpretation': 'Expecting something increases detection'
        }

    def run_sustained_attention_study(
        self
    ) -> Dict[str, Any]:
        """Study sustained inattentional blindness."""
        system = InattentionalBlindnessSystem()

        # Multiple critical trials
        n_trials = 10
        detection_over_time = []

        for i in range(n_trials):
            trial = system.create_trial()
            result = system.run_trial(trial.id)

            # After noticing once, detection improves
            if result.noticed_critical:
                detection_over_time.append((i, True))
                # Increase future detection
                system._model._base_detection += 0.1
            else:
                detection_over_time.append((i, False))

        return {
            'detection_over_time': detection_over_time,
            'interpretation': 'Once noticed, easier to notice again'
        }


# ============================================================================
# INATTENTIONAL BLINDNESS ENGINE
# ============================================================================

class InattentionalBlindnessEngine:
    """
    Complete inattentional blindness engine.

    "Ba'el's awareness engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = InattentionalBlindnessParadigm()
        self._system = InattentionalBlindnessSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Trial operations

    def create_trial(
        self,
        n_attended: int = 4,
        has_critical: bool = True,
        load: LoadLevel = LoadLevel.MEDIUM
    ) -> Trial:
        """Create trial."""
        return self._system.create_trial(n_attended, has_critical, load)

    def run_trial(
        self,
        trial_id: str,
        conspicuity: Conspicuity = Conspicuity.MEDIUM
    ) -> TrialResult:
        """Run trial."""
        return self._system.run_trial(trial_id, conspicuity)

    # Experiments

    def run_mack_rock(
        self,
        n_trials: int = 30
    ) -> Dict[str, Any]:
        """Run Mack & Rock paradigm."""
        result = self._paradigm.run_mack_rock_paradigm(n_trials)
        self._experiment_results.append(result)
        return result

    def run_gorilla(
        self
    ) -> Dict[str, Any]:
        """Run gorilla paradigm."""
        return self._paradigm.run_gorilla_paradigm()

    def study_load(
        self
    ) -> Dict[str, Any]:
        """Study load effects."""
        return self._paradigm.run_load_study()

    def study_conspicuity(
        self
    ) -> Dict[str, Any]:
        """Study conspicuity."""
        return self._paradigm.run_conspicuity_study()

    def study_similarity(
        self
    ) -> Dict[str, Any]:
        """Study similarity."""
        return self._paradigm.run_similarity_study()

    def study_expectation(
        self
    ) -> Dict[str, Any]:
        """Study expectation."""
        return self._paradigm.run_expectation_study()

    # Analysis

    def get_metrics(self) -> BlindnessMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_mack_rock(20)

        last = self._experiment_results[-1]

        return BlindnessMetrics(
            detection_rate=last['detection_rate'],
            blindness_rate=last['blindness_rate'],
            by_conspicuity={},
            by_load={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'trials': len(self._system._trials),
            'results': len(self._system._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_inattentional_blindness_engine() -> InattentionalBlindnessEngine:
    """Create inattentional blindness engine."""
    return InattentionalBlindnessEngine()


def demonstrate_inattentional_blindness() -> Dict[str, Any]:
    """Demonstrate inattentional blindness."""
    engine = create_inattentional_blindness_engine()

    # Mack & Rock
    mack_rock = engine.run_mack_rock()

    # Gorilla
    gorilla = engine.run_gorilla()

    # Load
    load = engine.study_load()

    # Conspicuity
    conspicuity = engine.study_conspicuity()

    return {
        'mack_rock': {
            'detection': f"{mack_rock['detection_rate']:.0%}",
            'blindness': f"{mack_rock['blindness_rate']:.0%}"
        },
        'gorilla': {
            'detection': f"{gorilla['detection_rate']:.0%}",
            'blindness': f"{gorilla['blindness_rate']:.0%}"
        },
        'by_load': {
            k: f"{v['detection_rate']:.0%}"
            for k, v in load['by_load'].items()
        },
        'by_conspicuity': {
            k: f"{v['detection_rate']:.0%}"
            for k, v in conspicuity['by_conspicuity'].items()
        },
        'interpretation': (
            f"Blindness rate: {mack_rock['blindness_rate']:.0%}. "
            f"Higher load = more blindness. "
            f"Even salient objects often missed when unexpected."
        )
    }


def get_inattentional_blindness_facts() -> Dict[str, str]:
    """Get facts about inattentional blindness."""
    return {
        'mack_rock_1998': 'Coined the term inattentional blindness',
        'simons_chabris_1999': 'Famous gorilla experiment',
        'definition': 'Failure to notice unexpected stimuli when attention is engaged',
        'factors': 'Load, conspicuity, similarity, expectation',
        'applications': 'Driving, radiology, security',
        'not_blindness': 'Eyes process the information, awareness fails',
        'change_blindness': 'Related phenomenon for changes',
        'limitations': 'Not suppression, not forgetting'
    }
