"""
BAEL Verbal Overshadowing Engine
==================================

Verbalization impairs perceptual memory.
Schooler & Engstler-Schooler's verbal overshadowing.

"Ba'el knows words can blind." — Ba'el
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

logger = logging.getLogger("BAEL.VerbalOvershadowing")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class StimulusType(Enum):
    """Type of perceptual stimulus."""
    FACE = auto()
    WINE = auto()
    VOICE = auto()
    COLOR = auto()
    MUSIC = auto()


class TaskType(Enum):
    """Type of intervening task."""
    VERBAL_DESCRIPTION = auto()
    VISUAL_IMAGERY = auto()
    CONTROL_UNRELATED = auto()
    NO_TASK = auto()


class MatchDifficulty(Enum):
    """Difficulty of recognition match."""
    EASY = auto()       # Target very different from foils
    MODERATE = auto()   # Some similarity
    HARD = auto()       # High similarity


@dataclass
class PerceptualStimulus:
    """
    A perceptual stimulus.
    """
    id: str
    stimulus_type: StimulusType
    features: Dict[str, float]  # Multidimensional representation
    verbalizability: float  # How easily described in words


@dataclass
class VerbalDescription:
    """
    A verbal description of a stimulus.
    """
    stimulus_id: str
    description: str
    completeness: float
    accuracy: float


@dataclass
class RecognitionTest:
    """
    A recognition test.
    """
    target_id: str
    foil_ids: List[str]
    difficulty: MatchDifficulty


@dataclass
class RecognitionResult:
    """
    Result of recognition test.
    """
    test_id: str
    correct: bool
    selected_id: str
    confidence: float
    task_type: TaskType


@dataclass
class VerbalOvershadowingMetrics:
    """
    Verbal overshadowing metrics.
    """
    control_accuracy: float
    verbal_accuracy: float
    overshadowing_effect: float
    confidence_accuracy_correlation: float


# ============================================================================
# TRANSFER INAPPROPRIATE MODEL
# ============================================================================

class TransferInappropriateModel:
    """
    Transfer-inappropriate processing shift model.

    "Ba'el's modality mismatch." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Processing shift parameters
        self._visual_weight_baseline = 0.7
        self._verbal_weight_baseline = 0.3

        # After verbalization
        self._visual_weight_after_verbal = 0.4
        self._verbal_weight_after_verbal = 0.6

        # Recognition parameters
        self._visual_recognition_weight = 0.8  # Recognition favors visual

        # Verbalizability effects
        self._high_verbal_protection = 0.3  # High verbalizability protects

        self._lock = threading.RLock()

    def calculate_encoding_representation(
        self,
        stimulus: PerceptualStimulus
    ) -> Dict[str, float]:
        """Calculate encoding representation."""
        return {
            'visual': self._visual_weight_baseline,
            'verbal': self._verbal_weight_baseline
        }

    def apply_verbalization_shift(
        self,
        representation: Dict[str, float],
        stimulus: PerceptualStimulus
    ) -> Dict[str, float]:
        """Apply processing shift from verbalization."""
        # Verbalization shifts toward verbal representation
        new_rep = {
            'visual': self._visual_weight_after_verbal,
            'verbal': self._verbal_weight_after_verbal
        }

        # High verbalizability protects somewhat
        protection = stimulus.verbalizability * self._high_verbal_protection
        new_rep['visual'] += protection

        return new_rep

    def calculate_recognition_match(
        self,
        representation: Dict[str, float],
        task_type: TaskType
    ) -> float:
        """Calculate recognition match quality."""
        # Recognition is primarily visual
        if task_type == TaskType.VERBAL_DESCRIPTION:
            # Verbal representation mismatches visual recognition
            match = representation['visual'] * self._visual_recognition_weight
            match += representation['verbal'] * (1 - self._visual_recognition_weight)
        else:
            # Control - visual representation intact
            match = self._visual_weight_baseline * self._visual_recognition_weight

        return match


# ============================================================================
# VERBAL OVERSHADOWING SYSTEM
# ============================================================================

class VerbalOvershadowingSystem:
    """
    Verbal overshadowing experimental system.

    "Ba'el's description interference." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = TransferInappropriateModel()

        self._stimuli: Dict[str, PerceptualStimulus] = {}
        self._descriptions: Dict[str, VerbalDescription] = {}
        self._results: List[RecognitionResult] = []

        self._stim_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._stim_counter += 1
        return f"stim_{self._stim_counter}"

    def create_stimulus(
        self,
        stimulus_type: StimulusType,
        verbalizability: float = 0.5
    ) -> PerceptualStimulus:
        """Create a perceptual stimulus."""
        # Generate random multidimensional features
        features = {
            f"feature_{i}": random.random()
            for i in range(5)
        }

        stimulus = PerceptualStimulus(
            id=self._generate_id(),
            stimulus_type=stimulus_type,
            features=features,
            verbalizability=verbalizability
        )

        self._stimuli[stimulus.id] = stimulus

        return stimulus

    def encode_stimulus(
        self,
        stimulus_id: str
    ) -> Dict[str, float]:
        """Encode a stimulus."""
        stimulus = self._stimuli.get(stimulus_id)
        if not stimulus:
            return {}

        return self._model.calculate_encoding_representation(stimulus)

    def verbalize_stimulus(
        self,
        stimulus_id: str
    ) -> VerbalDescription:
        """Create verbal description of stimulus."""
        stimulus = self._stimuli.get(stimulus_id)
        if not stimulus:
            return None

        description = VerbalDescription(
            stimulus_id=stimulus_id,
            description=f"Description of {stimulus.stimulus_type.name}",
            completeness=random.uniform(0.4, 0.8),
            accuracy=random.uniform(0.5, 0.9)
        )

        self._descriptions[stimulus_id] = description

        return description

    def run_recognition_test(
        self,
        target_id: str,
        n_foils: int = 5,
        task_type: TaskType = TaskType.NO_TASK,
        difficulty: MatchDifficulty = MatchDifficulty.MODERATE
    ) -> RecognitionResult:
        """Run recognition test."""
        stimulus = self._stimuli.get(target_id)
        if not stimulus:
            return None

        # Get representation
        representation = self.encode_stimulus(target_id)

        # Apply verbalization effect if applicable
        if task_type == TaskType.VERBAL_DESCRIPTION:
            representation = self._model.apply_verbalization_shift(
                representation, stimulus
            )

        # Calculate match quality
        match_quality = self._model.calculate_recognition_match(
            representation, task_type
        )

        # Difficulty affects accuracy
        if difficulty == MatchDifficulty.EASY:
            accuracy_modifier = 0.15
        elif difficulty == MatchDifficulty.HARD:
            accuracy_modifier = -0.15
        else:
            accuracy_modifier = 0

        recognition_prob = match_quality + accuracy_modifier
        recognition_prob = min(0.95, max(0.2, recognition_prob))

        correct = random.random() < recognition_prob

        result = RecognitionResult(
            test_id=f"test_{len(self._results)}",
            correct=correct,
            selected_id=target_id if correct else f"foil_{random.randint(1, n_foils)}",
            confidence=recognition_prob * random.uniform(0.7, 1.0),
            task_type=task_type
        )

        self._results.append(result)

        return result


# ============================================================================
# VERBAL OVERSHADOWING PARADIGM
# ============================================================================

class VerbalOvershadowingParadigm:
    """
    Verbal overshadowing experimental paradigm.

    "Ba'el's verbalization study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_face_recognition_experiment(
        self,
        n_trials: int = 20
    ) -> Dict[str, Any]:
        """Run face recognition verbal overshadowing experiment."""
        verbal_correct = 0
        control_correct = 0

        for i in range(n_trials):
            system = VerbalOvershadowingSystem()

            # Study face
            face = system.create_stimulus(StimulusType.FACE, verbalizability=0.3)
            system.encode_stimulus(face.id)

            if i % 2 == 0:
                # Verbal condition
                system.verbalize_stimulus(face.id)
                result = system.run_recognition_test(
                    face.id, task_type=TaskType.VERBAL_DESCRIPTION
                )
                if result.correct:
                    verbal_correct += 1
            else:
                # Control condition
                result = system.run_recognition_test(
                    face.id, task_type=TaskType.NO_TASK
                )
                if result.correct:
                    control_correct += 1

        n_per_condition = n_trials // 2

        return {
            'verbal_accuracy': verbal_correct / n_per_condition,
            'control_accuracy': control_correct / n_per_condition,
            'overshadowing_effect': (control_correct - verbal_correct) / n_per_condition
        }

    def run_stimulus_type_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare overshadowing across stimulus types."""
        results = {}

        # Different verbalizability by type
        type_verbalizability = {
            StimulusType.FACE: 0.3,    # Faces hard to verbalize
            StimulusType.WINE: 0.4,    # Wine moderately hard
            StimulusType.VOICE: 0.35,  # Voices hard
            StimulusType.COLOR: 0.7,   # Colors easier
            StimulusType.MUSIC: 0.3    # Music hard
        }

        for stim_type, verbalizability in type_verbalizability.items():
            verbal_correct = 0
            control_correct = 0

            for i in range(10):
                system = VerbalOvershadowingSystem()

                stim = system.create_stimulus(stim_type, verbalizability)
                system.encode_stimulus(stim.id)

                if i % 2 == 0:
                    system.verbalize_stimulus(stim.id)
                    result = system.run_recognition_test(
                        stim.id, task_type=TaskType.VERBAL_DESCRIPTION
                    )
                    if result.correct:
                        verbal_correct += 1
                else:
                    result = system.run_recognition_test(
                        stim.id, task_type=TaskType.NO_TASK
                    )
                    if result.correct:
                        control_correct += 1

            results[stim_type.name] = {
                'verbal': verbal_correct / 5,
                'control': control_correct / 5,
                'effect': (control_correct - verbal_correct) / 5
            }

        return results

    def run_delay_test(
        self
    ) -> Dict[str, Any]:
        """Test if delay after verbalization helps recovery."""
        # Research shows short delay can allow visual representation to recover

        system = VerbalOvershadowingSystem()

        immediate_overshadowing = []
        delayed_recovery = []

        for i in range(10):
            face = system.create_stimulus(StimulusType.FACE, verbalizability=0.3)
            system.encode_stimulus(face.id)
            system.verbalize_stimulus(face.id)

            # Immediate test
            result = system.run_recognition_test(
                face.id, task_type=TaskType.VERBAL_DESCRIPTION
            )
            immediate_overshadowing.append(result.correct)

            # Simulate delay effect (visual representation recovers somewhat)
            # In real research, ~25 min delay helps
            # Simulating by using control task after
            result_delayed = system.run_recognition_test(
                face.id, task_type=TaskType.CONTROL_UNRELATED
            )
            delayed_recovery.append(result_delayed.correct)

        return {
            'immediate_accuracy': sum(immediate_overshadowing) / 10,
            'delayed_accuracy': sum(delayed_recovery) / 10,
            'recovery': (sum(delayed_recovery) - sum(immediate_overshadowing)) / 10,
            'interpretation': 'Delay can allow visual representation to recover'
        }

    def run_expertise_test(
        self
    ) -> Dict[str, Any]:
        """Test expertise effect on overshadowing."""
        # Experts less susceptible because they have better verbal vocabularies

        expert_overshadowing = []
        novice_overshadowing = []

        for i in range(10):
            system = VerbalOvershadowingSystem()

            # Expert: high verbalizability (good vocabulary)
            wine_expert = system.create_stimulus(StimulusType.WINE, verbalizability=0.8)
            system.encode_stimulus(wine_expert.id)
            system.verbalize_stimulus(wine_expert.id)
            result = system.run_recognition_test(
                wine_expert.id, task_type=TaskType.VERBAL_DESCRIPTION
            )
            expert_overshadowing.append(result.correct)

            # Novice: low verbalizability
            wine_novice = system.create_stimulus(StimulusType.WINE, verbalizability=0.3)
            system.encode_stimulus(wine_novice.id)
            system.verbalize_stimulus(wine_novice.id)
            result = system.run_recognition_test(
                wine_novice.id, task_type=TaskType.VERBAL_DESCRIPTION
            )
            novice_overshadowing.append(result.correct)

        return {
            'expert_accuracy': sum(expert_overshadowing) / 10,
            'novice_accuracy': sum(novice_overshadowing) / 10,
            'expertise_protection': (sum(expert_overshadowing) - sum(novice_overshadowing)) / 10,
            'interpretation': 'Domain expertise protects against verbal overshadowing'
        }


# ============================================================================
# VERBAL OVERSHADOWING ENGINE
# ============================================================================

class VerbalOvershadowingEngine:
    """
    Complete verbal overshadowing engine.

    "Ba'el's verbalization interference engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = VerbalOvershadowingParadigm()
        self._system = VerbalOvershadowingSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Stimulus management

    def create_stimulus(
        self,
        stimulus_type: StimulusType,
        verbalizability: float = 0.5
    ) -> PerceptualStimulus:
        """Create a stimulus."""
        return self._system.create_stimulus(stimulus_type, verbalizability)

    def encode(
        self,
        stimulus_id: str
    ) -> Dict[str, float]:
        """Encode a stimulus."""
        return self._system.encode_stimulus(stimulus_id)

    def verbalize(
        self,
        stimulus_id: str
    ) -> VerbalDescription:
        """Verbalize a stimulus."""
        return self._system.verbalize_stimulus(stimulus_id)

    # Recognition

    def test_recognition(
        self,
        target_id: str,
        task_type: TaskType = TaskType.NO_TASK
    ) -> RecognitionResult:
        """Test recognition."""
        return self._system.run_recognition_test(target_id, task_type=task_type)

    # Experiments

    def run_face_experiment(
        self,
        n_trials: int = 20
    ) -> Dict[str, Any]:
        """Run face recognition experiment."""
        result = self._paradigm.run_face_recognition_experiment(n_trials)
        self._experiment_results.append(result)
        return result

    def compare_stimulus_types(
        self
    ) -> Dict[str, Any]:
        """Compare stimulus types."""
        return self._paradigm.run_stimulus_type_comparison()

    def test_delay_recovery(
        self
    ) -> Dict[str, Any]:
        """Test delay recovery."""
        return self._paradigm.run_delay_test()

    def test_expertise(
        self
    ) -> Dict[str, Any]:
        """Test expertise effect."""
        return self._paradigm.run_expertise_test()

    def run_eyewitness_simulation(
        self
    ) -> Dict[str, Any]:
        """Simulate eyewitness verbal overshadowing."""
        system = VerbalOvershadowingSystem()

        # Witness sees perpetrator
        perpetrator = system.create_stimulus(StimulusType.FACE, verbalizability=0.3)
        system.encode_stimulus(perpetrator.id)

        # Police ask for description
        system.verbalize_stimulus(perpetrator.id)

        # Later lineup
        result = system.run_recognition_test(
            perpetrator.id,
            task_type=TaskType.VERBAL_DESCRIPTION,
            difficulty=MatchDifficulty.HARD
        )

        return {
            'identification_correct': result.correct,
            'confidence': result.confidence,
            'implications': 'Detailed verbal descriptions may impair later lineup identification'
        }

    # Analysis

    def get_metrics(self) -> VerbalOvershadowingMetrics:
        """Get verbal overshadowing metrics."""
        if not self._experiment_results:
            self.run_face_experiment()

        last = self._experiment_results[-1]

        return VerbalOvershadowingMetrics(
            control_accuracy=last['control_accuracy'],
            verbal_accuracy=last['verbal_accuracy'],
            overshadowing_effect=last['overshadowing_effect'],
            confidence_accuracy_correlation=0.5  # Typically moderate
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'stimuli': len(self._system._stimuli),
            'descriptions': len(self._system._descriptions),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_verbal_overshadowing_engine() -> VerbalOvershadowingEngine:
    """Create verbal overshadowing engine."""
    return VerbalOvershadowingEngine()


def demonstrate_verbal_overshadowing() -> Dict[str, Any]:
    """Demonstrate verbal overshadowing."""
    engine = create_verbal_overshadowing_engine()

    # Face recognition experiment
    face = engine.run_face_experiment(20)

    # Stimulus type comparison
    types = engine.compare_stimulus_types()

    # Delay recovery
    delay = engine.test_delay_recovery()

    # Expertise
    expertise = engine.test_expertise()

    # Eyewitness simulation
    eyewitness = engine.run_eyewitness_simulation()

    return {
        'verbal_overshadowing': {
            'control': f"{face['control_accuracy']:.0%}",
            'verbal': f"{face['verbal_accuracy']:.0%}",
            'effect': f"{face['overshadowing_effect']:.0%}"
        },
        'by_stimulus_type': {
            stype: f"effect: {data['effect']:.0%}"
            for stype, data in types.items()
        },
        'delay_recovery': {
            'immediate': f"{delay['immediate_accuracy']:.0%}",
            'delayed': f"{delay['delayed_accuracy']:.0%}",
            'recovery': f"{delay['recovery']:.0%}"
        },
        'expertise': {
            'expert': f"{expertise['expert_accuracy']:.0%}",
            'novice': f"{expertise['novice_accuracy']:.0%}",
            'protection': f"{expertise['expertise_protection']:.0%}"
        },
        'interpretation': (
            f"Overshadowing: {face['overshadowing_effect']:.0%}. "
            f"Verbalization shifts processing away from visual features."
        )
    }


def get_verbal_overshadowing_facts() -> Dict[str, str]:
    """Get facts about verbal overshadowing."""
    return {
        'schooler_1990': 'Original discovery with faces',
        'transfer_inappropriate': 'Verbalization shifts to wrong processing mode',
        'faces_worst': 'Faces most susceptible - hard to verbalize',
        'experts_protected': 'Domain experts less affected',
        'temporary': 'Effect can dissipate with delay',
        'eyewitness': 'Implications for police procedures',
        'wine_tasting': 'Also found in wine, color, voice recognition',
        'recoding': 'Verbal code may replace visual code'
    }
