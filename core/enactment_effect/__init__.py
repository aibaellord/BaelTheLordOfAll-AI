"""
BAEL Enactment Effect Engine
==============================

Actions performed are better remembered.
Engelkamp's motor encoding theory.

"Ba'el acts to remember." — Ba'el
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

logger = logging.getLogger("BAEL.EnactmentEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class EncodingMode(Enum):
    """Mode of encoding."""
    VERBAL = auto()           # Hear/read only
    ENACTED = auto()          # Perform action
    OBSERVED = auto()         # Watch someone else
    IMAGINED = auto()         # Imagine performing


class ActionType(Enum):
    """Type of action."""
    SIMPLE = auto()           # Single movement
    COMPLEX = auto()          # Multiple movements
    OBJECT_RELATED = auto()   # With object
    PANTOMIME = auto()        # Without object
    SYMBOLIC = auto()         # Gesture


class TestType(Enum):
    """Type of memory test."""
    FREE_RECALL = auto()
    CUED_RECALL = auto()
    RECOGNITION = auto()
    ENACTMENT = auto()        # Re-enact to test


class MemoryComponent(Enum):
    """Component of action memory."""
    VERBAL = auto()           # Verbal description
    MOTOR = auto()            # Motor program
    VISUAL = auto()           # Visual image


@dataclass
class ActionPhrase:
    """
    An action phrase to be remembered.
    """
    id: str
    text: str               # e.g., "roll the ball"
    verb: str
    object: Optional[str]
    action_type: ActionType
    complexity: float


@dataclass
class StudyTrial:
    """
    A study trial.
    """
    id: str
    action: ActionPhrase
    encoding: EncodingMode
    study_time_ms: float
    object_present: bool


@dataclass
class RecallResult:
    """
    Result of recall.
    """
    encoding_mode: EncodingMode
    actions_presented: List[str]
    actions_recalled: List[str]
    proportion_recalled: float
    verb_recall: float
    object_recall: float


@dataclass
class EnactmentMetrics:
    """
    Enactment effect metrics.
    """
    enacted_recall: float
    verbal_recall: float
    enactment_effect: float
    by_action_type: Dict[str, float]
    by_test: Dict[str, float]


# ============================================================================
# ENACTMENT EFFECT MODEL
# ============================================================================

class EnactmentEffectModel:
    """
    Model of the enactment effect.

    "Ba'el's motor encoding model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall probability
        self._base_recall = 0.35

        # Enactment boost
        self._enactment_boost = 0.25

        # Other encoding effects
        self._encoding_effects = {
            EncodingMode.VERBAL: 0.0,
            EncodingMode.ENACTED: 0.25,
            EncodingMode.OBSERVED: 0.15,
            EncodingMode.IMAGINED: 0.18
        }

        # Action type effects
        self._action_type_effects = {
            ActionType.SIMPLE: 0.0,
            ActionType.COMPLEX: -0.05,  # Harder to remember
            ActionType.OBJECT_RELATED: 0.05,
            ActionType.PANTOMIME: 0.02,
            ActionType.SYMBOLIC: -0.03
        }

        # Test type modulation
        self._test_effects = {
            TestType.FREE_RECALL: 1.0,
            TestType.CUED_RECALL: 1.1,
            TestType.RECOGNITION: 0.8,
            TestType.ENACTMENT: 1.2  # Best for enacted items
        }

        # Object presence
        self._object_boost = 0.05

        # Motor program distinctiveness
        self._motor_distinctiveness = 0.10

        self._lock = threading.RLock()

    def get_memory_components(
        self,
        encoding: EncodingMode
    ) -> Dict[MemoryComponent, float]:
        """Get strength of memory components."""
        components = {
            EncodingMode.VERBAL: {
                MemoryComponent.VERBAL: 0.8,
                MemoryComponent.MOTOR: 0.1,
                MemoryComponent.VISUAL: 0.3
            },
            EncodingMode.ENACTED: {
                MemoryComponent.VERBAL: 0.7,
                MemoryComponent.MOTOR: 0.9,
                MemoryComponent.VISUAL: 0.6
            },
            EncodingMode.OBSERVED: {
                MemoryComponent.VERBAL: 0.6,
                MemoryComponent.MOTOR: 0.3,
                MemoryComponent.VISUAL: 0.8
            },
            EncodingMode.IMAGINED: {
                MemoryComponent.VERBAL: 0.6,
                MemoryComponent.MOTOR: 0.5,
                MemoryComponent.VISUAL: 0.7
            }
        }
        return components[encoding]

    def calculate_recall_probability(
        self,
        action: ActionPhrase,
        encoding: EncodingMode,
        test_type: TestType = TestType.FREE_RECALL,
        object_present: bool = True
    ) -> float:
        """Calculate recall probability."""
        prob = self._base_recall

        # Encoding effect
        prob += self._encoding_effects[encoding]

        # Action type effect
        prob += self._action_type_effects[action.action_type]

        # Test type modulation
        prob *= self._test_effects[test_type]

        # Object presence
        if object_present and action.object:
            prob += self._object_boost

        # Complexity penalty
        prob -= action.complexity * 0.05

        # Add noise
        prob += random.uniform(-0.1, 0.1)

        return max(0.05, min(0.95, prob))

    def calculate_enactment_effect(
        self,
        enacted_recall: float,
        verbal_recall: float
    ) -> float:
        """Calculate enactment effect size."""
        return enacted_recall - verbal_recall

    def get_component_contribution(
        self,
        encoding: EncodingMode
    ) -> Dict[str, float]:
        """Get contribution of each memory component."""
        components = self.get_memory_components(encoding)

        total = sum(components.values())

        return {
            comp.name: val / total
            for comp, val in components.items()
        }


# ============================================================================
# ENACTMENT EFFECT SYSTEM
# ============================================================================

class EnactmentEffectSystem:
    """
    Enactment effect simulation system.

    "Ba'el's enactment system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = EnactmentEffectModel()

        self._actions: Dict[str, ActionPhrase] = {}
        self._trials: Dict[str, StudyTrial] = {}

        self._counter = 0
        self._lock = threading.RLock()

        # Initialize action pool
        self._initialize_actions()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def _initialize_actions(self):
        """Initialize action pool."""
        actions = [
            ("roll the ball", "roll", "ball", ActionType.OBJECT_RELATED, 0.2),
            ("wave goodbye", "wave", None, ActionType.SIMPLE, 0.1),
            ("brush your teeth", "brush", "teeth", ActionType.OBJECT_RELATED, 0.3),
            ("open the book", "open", "book", ActionType.OBJECT_RELATED, 0.2),
            ("clap your hands", "clap", "hands", ActionType.SIMPLE, 0.1),
            ("pour the water", "pour", "water", ActionType.OBJECT_RELATED, 0.3),
            ("shake the bottle", "shake", "bottle", ActionType.OBJECT_RELATED, 0.2),
            ("tie the rope", "tie", "rope", ActionType.COMPLEX, 0.5),
            ("fold the paper", "fold", "paper", ActionType.OBJECT_RELATED, 0.3),
            ("spin the wheel", "spin", "wheel", ActionType.OBJECT_RELATED, 0.2),
            ("point at the door", "point", "door", ActionType.SIMPLE, 0.1),
            ("knock on wood", "knock", "wood", ActionType.OBJECT_RELATED, 0.2),
            ("twist the cap", "twist", "cap", ActionType.OBJECT_RELATED, 0.3),
            ("stretch your arms", "stretch", "arms", ActionType.SIMPLE, 0.1),
            ("shuffle the cards", "shuffle", "cards", ActionType.COMPLEX, 0.5),
            ("wipe the table", "wipe", "table", ActionType.OBJECT_RELATED, 0.2),
            ("snap your fingers", "snap", "fingers", ActionType.SIMPLE, 0.2),
            ("flip the coin", "flip", "coin", ActionType.OBJECT_RELATED, 0.3),
            ("push the button", "push", "button", ActionType.SIMPLE, 0.1),
            ("pull the lever", "pull", "lever", ActionType.OBJECT_RELATED, 0.2)
        ]

        for text, verb, obj, action_type, complexity in actions:
            self._actions[text] = ActionPhrase(
                id=self._generate_id(),
                text=text,
                verb=verb,
                object=obj,
                action_type=action_type,
                complexity=complexity
            )

    def create_study_trial(
        self,
        action_text: str,
        encoding: EncodingMode,
        object_present: bool = True
    ) -> StudyTrial:
        """Create study trial."""
        action = self._actions.get(action_text)
        if not action:
            return None

        trial = StudyTrial(
            id=self._generate_id(),
            action=action,
            encoding=encoding,
            study_time_ms=random.uniform(3000, 5000),
            object_present=object_present
        )

        self._trials[trial.id] = trial

        return trial

    def run_recall_test(
        self,
        trial_ids: List[str],
        test_type: TestType = TestType.FREE_RECALL
    ) -> Dict[EncodingMode, RecallResult]:
        """Run recall test."""
        trials = [self._trials[tid] for tid in trial_ids if tid in self._trials]

        # Group by encoding
        by_encoding = defaultdict(list)
        for trial in trials:
            by_encoding[trial.encoding].append(trial)

        results = {}

        for encoding, enc_trials in by_encoding.items():
            presented = [t.action.text for t in enc_trials]
            recalled = []
            verb_recalled = 0
            obj_recalled = 0

            for trial in enc_trials:
                prob = self._model.calculate_recall_probability(
                    trial.action, encoding, test_type, trial.object_present
                )

                if random.random() < prob:
                    recalled.append(trial.action.text)
                    verb_recalled += 1
                    if trial.action.object:
                        obj_recalled += 1

            n_presented = len(presented)
            n_with_obj = sum(1 for t in enc_trials if t.action.object)

            results[encoding] = RecallResult(
                encoding_mode=encoding,
                actions_presented=presented,
                actions_recalled=recalled,
                proportion_recalled=len(recalled) / max(1, n_presented),
                verb_recall=verb_recalled / max(1, n_presented),
                object_recall=obj_recalled / max(1, n_with_obj) if n_with_obj > 0 else 0
            )

        return results


# ============================================================================
# ENACTMENT EFFECT PARADIGM
# ============================================================================

class EnactmentEffectParadigm:
    """
    Enactment effect paradigm.

    "Ba'el's enactment study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_actions: int = 20
    ) -> Dict[str, Any]:
        """Run classic enactment effect paradigm."""
        system = EnactmentEffectSystem()

        actions = list(system._actions.keys())[:n_actions]
        random.shuffle(actions)

        # Split into enacted and verbal
        enacted_actions = actions[:n_actions // 2]
        verbal_actions = actions[n_actions // 2:]

        trial_ids = []

        for action in enacted_actions:
            trial = system.create_study_trial(action, EncodingMode.ENACTED)
            if trial:
                trial_ids.append(trial.id)

        for action in verbal_actions:
            trial = system.create_study_trial(action, EncodingMode.VERBAL)
            if trial:
                trial_ids.append(trial.id)

        # Test
        results = system.run_recall_test(trial_ids)

        enacted_recall = results.get(EncodingMode.ENACTED, RecallResult(
            EncodingMode.ENACTED, [], [], 0, 0, 0
        )).proportion_recalled

        verbal_recall = results.get(EncodingMode.VERBAL, RecallResult(
            EncodingMode.VERBAL, [], [], 0, 0, 0
        )).proportion_recalled

        effect = enacted_recall - verbal_recall

        return {
            'enacted_recall': enacted_recall,
            'verbal_recall': verbal_recall,
            'enactment_effect': effect,
            'interpretation': f'Enactment effect: {effect:.0%}'
        }

    def run_encoding_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare all encoding modes."""
        system = EnactmentEffectSystem()
        model = system._model

        results = {}

        for encoding in EncodingMode:
            probs = []

            for action in system._actions.values():
                prob = model.calculate_recall_probability(action, encoding)
                probs.append(prob)

            results[encoding.name] = {
                'mean_recall': sum(probs) / len(probs)
            }

        return {
            'by_encoding': results,
            'interpretation': 'Enacted > Imagined > Observed > Verbal'
        }

    def run_action_type_study(
        self
    ) -> Dict[str, Any]:
        """Study action type effects."""
        system = EnactmentEffectSystem()
        model = system._model

        results = {}

        for action_type in ActionType:
            type_actions = [
                a for a in system._actions.values()
                if a.action_type == action_type
            ]

            if type_actions:
                probs = []
                for action in type_actions:
                    prob = model.calculate_recall_probability(action, EncodingMode.ENACTED)
                    probs.append(prob)

                results[action_type.name] = {
                    'mean_recall': sum(probs) / len(probs)
                }

        return {
            'by_action_type': results,
            'interpretation': 'Object-related actions best remembered'
        }

    def run_component_analysis(
        self
    ) -> Dict[str, Any]:
        """Analyze memory component contributions."""
        model = EnactmentEffectModel()

        results = {}

        for encoding in EncodingMode:
            components = model.get_memory_components(encoding)

            results[encoding.name] = {
                comp.name: strength
                for comp, strength in components.items()
            }

        return {
            'by_encoding': results,
            'interpretation': 'Enactment adds strong motor component'
        }

    def run_test_type_study(
        self
    ) -> Dict[str, Any]:
        """Study test type effects."""
        system = EnactmentEffectSystem()
        model = system._model

        results = {}

        for test_type in TestType:
            enacted_probs = []
            verbal_probs = []

            for action in system._actions.values():
                enacted = model.calculate_recall_probability(
                    action, EncodingMode.ENACTED, test_type
                )
                verbal = model.calculate_recall_probability(
                    action, EncodingMode.VERBAL, test_type
                )

                enacted_probs.append(enacted)
                verbal_probs.append(verbal)

            enacted_mean = sum(enacted_probs) / len(enacted_probs)
            verbal_mean = sum(verbal_probs) / len(verbal_probs)

            results[test_type.name] = {
                'effect': enacted_mean - verbal_mean
            }

        return {
            'by_test': results,
            'interpretation': 'Enactment test shows largest effect'
        }

    def run_object_study(
        self
    ) -> Dict[str, Any]:
        """Study object presence effects."""
        system = EnactmentEffectSystem()
        model = system._model

        conditions = {
            'with_object': True,
            'pantomime': False
        }

        results = {}

        for condition, obj_present in conditions.items():
            probs = []

            for action in system._actions.values():
                if action.object:  # Only actions with objects
                    prob = model.calculate_recall_probability(
                        action, EncodingMode.ENACTED,
                        object_present=obj_present
                    )
                    probs.append(prob)

            if probs:
                results[condition] = {
                    'mean_recall': sum(probs) / len(probs)
                }

        return {
            'by_object': results,
            'interpretation': 'Real objects slightly better than pantomime'
        }


# ============================================================================
# ENACTMENT EFFECT ENGINE
# ============================================================================

class EnactmentEffectEngine:
    """
    Complete enactment effect engine.

    "Ba'el's enactment engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = EnactmentEffectParadigm()
        self._system = EnactmentEffectSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Trial operations

    def study_action(
        self,
        action_text: str,
        encoding: EncodingMode = EncodingMode.ENACTED
    ) -> StudyTrial:
        """Study an action."""
        return self._system.create_study_trial(action_text, encoding)

    def test_recall(
        self,
        trial_ids: List[str]
    ) -> Dict[EncodingMode, RecallResult]:
        """Test recall."""
        return self._system.run_recall_test(trial_ids)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_encoding(
        self
    ) -> Dict[str, Any]:
        """Compare encoding modes."""
        return self._paradigm.run_encoding_comparison()

    def study_action_types(
        self
    ) -> Dict[str, Any]:
        """Study action types."""
        return self._paradigm.run_action_type_study()

    def analyze_components(
        self
    ) -> Dict[str, Any]:
        """Analyze memory components."""
        return self._paradigm.run_component_analysis()

    def study_test_types(
        self
    ) -> Dict[str, Any]:
        """Study test types."""
        return self._paradigm.run_test_type_study()

    def study_objects(
        self
    ) -> Dict[str, Any]:
        """Study object effects."""
        return self._paradigm.run_object_study()

    # Analysis

    def get_metrics(self) -> EnactmentMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return EnactmentMetrics(
            enacted_recall=last['enacted_recall'],
            verbal_recall=last['verbal_recall'],
            enactment_effect=last['enactment_effect'],
            by_action_type={},
            by_test={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'actions': len(self._system._actions),
            'trials': len(self._system._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_enactment_effect_engine() -> EnactmentEffectEngine:
    """Create enactment effect engine."""
    return EnactmentEffectEngine()


def demonstrate_enactment_effect() -> Dict[str, Any]:
    """Demonstrate enactment effect."""
    engine = create_enactment_effect_engine()

    # Classic
    classic = engine.run_classic()

    # Encoding comparison
    encoding = engine.compare_encoding()

    # Components
    components = engine.analyze_components()

    # Test types
    tests = engine.study_test_types()

    return {
        'classic_effect': {
            'enacted': f"{classic['enacted_recall']:.0%}",
            'verbal': f"{classic['verbal_recall']:.0%}",
            'effect': f"{classic['enactment_effect']:.0%}"
        },
        'by_encoding': {
            k: f"{v['mean_recall']:.0%}"
            for k, v in encoding['by_encoding'].items()
        },
        'components_enacted': components['by_encoding']['ENACTED'],
        'by_test': {
            k: f"{v['effect']:.0%}"
            for k, v in tests['by_test'].items()
        },
        'interpretation': (
            f"Enactment effect: {classic['enactment_effect']:.0%}. "
            f"Motor encoding adds distinctive memory trace. "
            f"Enacted > Imagined > Observed > Verbal."
        )
    }


def get_enactment_effect_facts() -> Dict[str, str]:
    """Get facts about enactment effect."""
    return {
        'engelkamp_zimmer_1989': 'Motor encoding theory',
        'effect_size': '~20-30% better recall for enacted',
        'mechanism': 'Motor program adds distinctive trace',
        'components': 'Verbal + Motor + Visual',
        'imagery': 'Motor imagery partially effective',
        'observation': 'Watching helps but less than doing',
        'objects': 'Real objects slightly better',
        'applications': 'Language learning, procedural training'
    }
