"""
BAEL Memory Inhibition Engine
===============================

Suppressing unwanted memories.
Anderson's think/no-think paradigm.

"Ba'el controls what is forgotten." — Ba'el
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

logger = logging.getLogger("BAEL.MemoryInhibition")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class InhibitionType(Enum):
    """Type of memory inhibition."""
    RETRIEVAL_INDUCED = auto()    # From retrieving related items
    DIRECTED_FORGETTING = auto()  # Intentional suppression
    THINK_NO_THINK = auto()       # Thought suppression
    PART_SET_CUING = auto()       # From partial cues


class TrialType(Enum):
    """Type of trial."""
    THINK = auto()      # Retrieve the memory
    NO_THINK = auto()   # Suppress the memory
    BASELINE = auto()   # No practice


class CueType(Enum):
    """Type of memory cue."""
    SAME_PROBE = auto()      # Original cue
    INDEPENDENT_PROBE = auto()  # Novel cue


class EmotionalValence(Enum):
    """Emotional valence of memory."""
    NEGATIVE = auto()
    NEUTRAL = auto()
    POSITIVE = auto()


@dataclass
class MemoryPair:
    """
    A cue-target memory pair.
    """
    id: str
    cue: str
    target: str
    strength: float
    valence: EmotionalValence
    n_suppressions: int
    n_retrievals: int


@dataclass
class InhibitionTrial:
    """
    A trial in the paradigm.
    """
    id: str
    pair_id: str
    trial_type: TrialType
    attempt_number: int
    success: bool


@dataclass
class RecallResult:
    """
    Result of recall attempt.
    """
    pair_id: str
    trial_type: TrialType
    cue_type: CueType
    recalled: bool
    intrusion: bool
    response_time_ms: float


@dataclass
class InhibitionMetrics:
    """
    Inhibition metrics.
    """
    think_recall: float
    no_think_recall: float
    baseline_recall: float
    suppression_effect: float     # Baseline - NoThink
    facilitation_effect: float    # Think - Baseline


# ============================================================================
# MEMORY INHIBITION MODEL
# ============================================================================

class MemoryInhibitionModel:
    """
    Model of memory inhibition.

    "Ba'el's forgetting model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall
        self._base_recall = 0.75

        # Suppression effects
        self._suppression_per_attempt = 0.03
        self._max_suppression = 0.30

        # Retrieval effects
        self._retrieval_boost_per_attempt = 0.02
        self._max_boost = 0.20

        # Individual differences
        self._suppression_ability_mean = 0.5
        self._suppression_ability_sd = 0.15

        # Emotional effects
        self._emotional_effects = {
            EmotionalValence.NEGATIVE: -0.10,  # Harder to suppress
            EmotionalValence.NEUTRAL: 0.0,
            EmotionalValence.POSITIVE: 0.05
        }

        # Independent probe effect
        self._independent_probe_recovery = 0.15

        self._lock = threading.RLock()

    def calculate_suppression_effect(
        self,
        n_attempts: int,
        valence: EmotionalValence,
        suppression_ability: float
    ) -> float:
        """Calculate suppression effect."""
        base_effect = n_attempts * self._suppression_per_attempt

        # Cap at maximum
        base_effect = min(base_effect, self._max_suppression)

        # Modulate by ability
        base_effect *= suppression_ability * 2  # ability range 0-1

        # Emotional modulation
        base_effect += self._emotional_effects[valence]

        return max(0.0, base_effect)

    def calculate_recall_probability(
        self,
        pair: MemoryPair,
        trial_type: TrialType,
        cue_type: CueType,
        suppression_ability: float
    ) -> float:
        """Calculate recall probability."""
        prob = self._base_recall

        if trial_type == TrialType.THINK:
            # Retrieval practice boost
            boost = min(
                pair.n_retrievals * self._retrieval_boost_per_attempt,
                self._max_boost
            )
            prob += boost

        elif trial_type == TrialType.NO_THINK:
            # Suppression decrement
            suppression = self.calculate_suppression_effect(
                pair.n_suppressions,
                pair.valence,
                suppression_ability
            )
            prob -= suppression

            # Independent probe recovery
            if cue_type == CueType.INDEPENDENT_PROBE:
                prob += self._independent_probe_recovery

        # Baseline: no change

        return max(0.0, min(1.0, prob))

    def calculate_intrusion_probability(
        self,
        pair: MemoryPair,
        n_suppressions: int
    ) -> float:
        """Calculate intrusion probability during suppression."""
        # More attempts = fewer intrusions
        base = 0.4
        reduction = n_suppressions * 0.05

        return max(0.1, base - reduction)


# ============================================================================
# MEMORY INHIBITION SYSTEM
# ============================================================================

class MemoryInhibitionSystem:
    """
    Memory inhibition simulation system.

    "Ba'el's suppression system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = MemoryInhibitionModel()

        self._pairs: Dict[str, MemoryPair] = {}
        self._trials: List[InhibitionTrial] = []
        self._results: List[RecallResult] = []

        # Individual differences
        self._suppression_ability = random.gauss(
            self._model._suppression_ability_mean,
            self._model._suppression_ability_sd
        )
        self._suppression_ability = max(0.1, min(0.9, self._suppression_ability))

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_pair(
        self,
        cue: str,
        target: str,
        valence: EmotionalValence = EmotionalValence.NEUTRAL
    ) -> MemoryPair:
        """Create a cue-target pair."""
        pair = MemoryPair(
            id=self._generate_id(),
            cue=cue,
            target=target,
            strength=0.5 + random.uniform(-0.1, 0.1),
            valence=valence,
            n_suppressions=0,
            n_retrievals=0
        )

        self._pairs[pair.id] = pair

        return pair

    def run_training_trial(
        self,
        pair_id: str,
        trial_type: TrialType
    ) -> InhibitionTrial:
        """Run a training trial."""
        pair = self._pairs.get(pair_id)
        if not pair:
            return None

        # Update counts
        if trial_type == TrialType.THINK:
            pair.n_retrievals += 1
            success = random.random() < 0.9  # Usually successful
        elif trial_type == TrialType.NO_THINK:
            # Check for intrusion
            intrusion_prob = self._model.calculate_intrusion_probability(
                pair, pair.n_suppressions
            )
            success = random.random() > intrusion_prob  # Success = no intrusion
            pair.n_suppressions += 1
        else:
            success = True

        trial = InhibitionTrial(
            id=self._generate_id(),
            pair_id=pair_id,
            trial_type=trial_type,
            attempt_number=pair.n_suppressions + pair.n_retrievals,
            success=success
        )

        self._trials.append(trial)

        return trial

    def test_recall(
        self,
        pair_id: str,
        trial_type: TrialType,
        cue_type: CueType = CueType.SAME_PROBE
    ) -> RecallResult:
        """Test recall of a pair."""
        pair = self._pairs.get(pair_id)
        if not pair:
            return None

        recall_prob = self._model.calculate_recall_probability(
            pair, trial_type, cue_type, self._suppression_ability
        )

        recalled = random.random() < recall_prob

        # Intrusion during no-think
        intrusion = False
        if trial_type == TrialType.NO_THINK and not recalled:
            intrusion = random.random() < 0.15

        # Response time
        if recalled:
            base_rt = 1000
            rt = base_rt + random.uniform(-200, 400)
        else:
            rt = 3000 + random.uniform(0, 500)  # Timeout

        result = RecallResult(
            pair_id=pair_id,
            trial_type=trial_type,
            cue_type=cue_type,
            recalled=recalled,
            intrusion=intrusion,
            response_time_ms=rt
        )

        self._results.append(result)

        return result


# ============================================================================
# MEMORY INHIBITION PARADIGM
# ============================================================================

class MemoryInhibitionParadigm:
    """
    Memory inhibition paradigm.

    "Ba'el's think/no-think study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_think_no_think_paradigm(
        self,
        n_pairs: int = 12,
        n_suppressions: int = 8
    ) -> Dict[str, Any]:
        """Run Anderson's think/no-think paradigm."""
        system = MemoryInhibitionSystem()

        # Create pairs
        think_pairs = []
        no_think_pairs = []
        baseline_pairs = []

        words = [
            ("ordeal", "roach"), ("steam", "train"), ("jaw", "gum"),
            ("insect", "ant"), ("tree", "leaf"), ("knife", "blade"),
            ("ocean", "wave"), ("fruit", "apple"), ("bird", "wing"),
            ("metal", "iron"), ("cloth", "silk"), ("tool", "hammer")
        ]

        for i, (cue, target) in enumerate(words[:n_pairs]):
            pair = system.create_pair(cue, target)

            if i % 3 == 0:
                think_pairs.append(pair)
            elif i % 3 == 1:
                no_think_pairs.append(pair)
            else:
                baseline_pairs.append(pair)

        # Training phase
        for _ in range(n_suppressions):
            for pair in think_pairs:
                system.run_training_trial(pair.id, TrialType.THINK)

            for pair in no_think_pairs:
                system.run_training_trial(pair.id, TrialType.NO_THINK)

        # Test phase
        results = {
            'think': [],
            'no_think': [],
            'baseline': []
        }

        for pair in think_pairs:
            result = system.test_recall(pair.id, TrialType.THINK)
            results['think'].append(result.recalled)

        for pair in no_think_pairs:
            result = system.test_recall(pair.id, TrialType.NO_THINK)
            results['no_think'].append(result.recalled)

        for pair in baseline_pairs:
            result = system.test_recall(pair.id, TrialType.BASELINE)
            results['baseline'].append(result.recalled)

        # Calculate metrics
        think_recall = sum(results['think']) / max(1, len(results['think']))
        no_think_recall = sum(results['no_think']) / max(1, len(results['no_think']))
        baseline_recall = sum(results['baseline']) / max(1, len(results['baseline']))

        return {
            'think_recall': think_recall,
            'no_think_recall': no_think_recall,
            'baseline_recall': baseline_recall,
            'suppression_effect': baseline_recall - no_think_recall,
            'facilitation_effect': think_recall - baseline_recall,
            'interpretation': 'NoThink items recalled less than baseline'
        }

    def run_dose_response_study(
        self
    ) -> Dict[str, Any]:
        """Study suppression attempts dose-response."""
        results = {}

        for n_attempts in [1, 4, 8, 16]:
            system = MemoryInhibitionSystem()

            # Create pairs
            pairs = [
                system.create_pair(f"cue_{i}", f"target_{i}")
                for i in range(10)
            ]

            # Suppress
            for _ in range(n_attempts):
                for pair in pairs:
                    system.run_training_trial(pair.id, TrialType.NO_THINK)

            # Test
            recalled = 0
            for pair in pairs:
                result = system.test_recall(pair.id, TrialType.NO_THINK)
                if result.recalled:
                    recalled += 1

            results[f"attempts_{n_attempts}"] = {
                'recall': recalled / len(pairs)
            }

        return {
            'by_attempts': results,
            'interpretation': 'More suppression = lower recall'
        }

    def run_independent_probe_study(
        self
    ) -> Dict[str, Any]:
        """Study independent probe effects."""
        system = MemoryInhibitionSystem()

        # Create pairs
        pairs = [
            system.create_pair(f"cue_{i}", f"target_{i}")
            for i in range(20)
        ]

        # Suppress
        for _ in range(8):
            for pair in pairs:
                system.run_training_trial(pair.id, TrialType.NO_THINK)

        # Test with same vs independent probes
        results = {
            'same_probe': [],
            'independent_probe': []
        }

        for i, pair in enumerate(pairs):
            if i < 10:
                result = system.test_recall(pair.id, TrialType.NO_THINK, CueType.SAME_PROBE)
                results['same_probe'].append(result.recalled)
            else:
                result = system.test_recall(pair.id, TrialType.NO_THINK, CueType.INDEPENDENT_PROBE)
                results['independent_probe'].append(result.recalled)

        same_recall = sum(results['same_probe']) / max(1, len(results['same_probe']))
        independent_recall = sum(results['independent_probe']) / max(1, len(results['independent_probe']))

        return {
            'same_probe_recall': same_recall,
            'independent_probe_recall': independent_recall,
            'recovery': independent_recall - same_recall,
            'interpretation': 'Independent probes show partial recovery'
        }

    def run_emotional_study(
        self
    ) -> Dict[str, Any]:
        """Study emotional valence effects."""
        results = {}

        for valence in EmotionalValence:
            system = MemoryInhibitionSystem()

            # Create pairs with valence
            pairs = [
                system.create_pair(f"cue_{i}", f"target_{i}", valence)
                for i in range(10)
            ]

            # Suppress
            for _ in range(8):
                for pair in pairs:
                    system.run_training_trial(pair.id, TrialType.NO_THINK)

            # Test
            recalled = 0
            for pair in pairs:
                result = system.test_recall(pair.id, TrialType.NO_THINK)
                if result.recalled:
                    recalled += 1

            results[valence.name] = {
                'recall': recalled / len(pairs)
            }

        return {
            'by_valence': results,
            'interpretation': 'Negative memories harder to suppress'
        }

    def run_intrusion_study(
        self
    ) -> Dict[str, Any]:
        """Study intrusions during suppression."""
        system = MemoryInhibitionSystem()

        pairs = [
            system.create_pair(f"cue_{i}", f"target_{i}")
            for i in range(10)
        ]

        intrusions_by_attempt = defaultdict(list)

        for attempt in range(16):
            for pair in pairs:
                trial = system.run_training_trial(pair.id, TrialType.NO_THINK)
                intrusions_by_attempt[attempt].append(not trial.success)

        # Calculate intrusion rate by attempt
        rates = {}
        for attempt, results in intrusions_by_attempt.items():
            rates[f"attempt_{attempt}"] = sum(results) / len(results)

        return {
            'intrusion_rates': rates,
            'interpretation': 'Intrusions decrease with practice'
        }

    def run_retrieval_induced_forgetting(
        self
    ) -> Dict[str, Any]:
        """Run retrieval-induced forgetting paradigm."""
        system = MemoryInhibitionSystem()

        # Category-exemplar pairs
        # Fruit-Orange (Rp+), Fruit-Banana (Rp-), Weapon-Knife (Nrp)

        # Create pairs
        rp_plus = []  # Practiced
        rp_minus = []  # Same category, not practiced
        nrp = []  # Different category

        for i in range(4):
            rp_plus.append(system.create_pair("Fruit", f"fruit_{i}"))
            rp_minus.append(system.create_pair("Fruit", f"fruit_{i+4}"))
            nrp.append(system.create_pair("Weapon", f"weapon_{i}"))

        # Practice Rp+ items
        for _ in range(3):
            for pair in rp_plus:
                system.run_training_trial(pair.id, TrialType.THINK)

        # Test all
        results = {
            'rp_plus': [],
            'rp_minus': [],
            'nrp': []
        }

        for pair in rp_plus:
            result = system.test_recall(pair.id, TrialType.THINK)
            results['rp_plus'].append(result.recalled)

        for pair in rp_minus:
            # These should show inhibition due to competition
            result = system.test_recall(pair.id, TrialType.BASELINE)
            # Simulate RIF
            recalled = random.random() < (system._model._base_recall - 0.15)
            results['rp_minus'].append(recalled)

        for pair in nrp:
            result = system.test_recall(pair.id, TrialType.BASELINE)
            results['nrp'].append(result.recalled)

        rp_plus_recall = sum(results['rp_plus']) / max(1, len(results['rp_plus']))
        rp_minus_recall = sum(results['rp_minus']) / max(1, len(results['rp_minus']))
        nrp_recall = sum(results['nrp']) / max(1, len(results['nrp']))

        return {
            'rp_plus': rp_plus_recall,
            'rp_minus': rp_minus_recall,
            'nrp': nrp_recall,
            'rif_effect': nrp_recall - rp_minus_recall,
            'interpretation': 'Rp- recall below baseline due to competition'
        }


# ============================================================================
# MEMORY INHIBITION ENGINE
# ============================================================================

class MemoryInhibitionEngine:
    """
    Complete memory inhibition engine.

    "Ba'el's forgetting engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = MemoryInhibitionParadigm()
        self._system = MemoryInhibitionSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Pair operations

    def create_pair(
        self,
        cue: str,
        target: str
    ) -> MemoryPair:
        """Create pair."""
        return self._system.create_pair(cue, target)

    def suppress(
        self,
        pair_id: str
    ) -> InhibitionTrial:
        """Suppress a memory."""
        return self._system.run_training_trial(pair_id, TrialType.NO_THINK)

    def retrieve(
        self,
        pair_id: str
    ) -> InhibitionTrial:
        """Retrieve a memory."""
        return self._system.run_training_trial(pair_id, TrialType.THINK)

    def test(
        self,
        pair_id: str
    ) -> RecallResult:
        """Test recall."""
        pair = self._system._pairs.get(pair_id)
        if not pair:
            return None

        trial_type = TrialType.BASELINE
        if pair.n_suppressions > 0:
            trial_type = TrialType.NO_THINK
        elif pair.n_retrievals > 0:
            trial_type = TrialType.THINK

        return self._system.test_recall(pair_id, trial_type)

    # Experiments

    def run_think_no_think(
        self
    ) -> Dict[str, Any]:
        """Run think/no-think."""
        result = self._paradigm.run_think_no_think_paradigm()
        self._experiment_results.append(result)
        return result

    def study_dose_response(
        self
    ) -> Dict[str, Any]:
        """Study dose-response."""
        return self._paradigm.run_dose_response_study()

    def study_independent_probe(
        self
    ) -> Dict[str, Any]:
        """Study independent probes."""
        return self._paradigm.run_independent_probe_study()

    def study_emotion(
        self
    ) -> Dict[str, Any]:
        """Study emotional effects."""
        return self._paradigm.run_emotional_study()

    def study_intrusions(
        self
    ) -> Dict[str, Any]:
        """Study intrusions."""
        return self._paradigm.run_intrusion_study()

    def run_rif(
        self
    ) -> Dict[str, Any]:
        """Run retrieval-induced forgetting."""
        return self._paradigm.run_retrieval_induced_forgetting()

    # Analysis

    def get_metrics(self) -> InhibitionMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_think_no_think()

        last = self._experiment_results[-1]

        return InhibitionMetrics(
            think_recall=last['think_recall'],
            no_think_recall=last['no_think_recall'],
            baseline_recall=last['baseline_recall'],
            suppression_effect=last['suppression_effect'],
            facilitation_effect=last['facilitation_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'pairs': len(self._system._pairs),
            'trials': len(self._system._trials),
            'suppression_ability': f"{self._system._suppression_ability:.2f}"
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_memory_inhibition_engine() -> MemoryInhibitionEngine:
    """Create memory inhibition engine."""
    return MemoryInhibitionEngine()


def demonstrate_memory_inhibition() -> Dict[str, Any]:
    """Demonstrate memory inhibition."""
    engine = create_memory_inhibition_engine()

    # Think/no-think
    tnt = engine.run_think_no_think()

    # Dose-response
    dose = engine.study_dose_response()

    # Independent probe
    probe = engine.study_independent_probe()

    # Emotion
    emotion = engine.study_emotion()

    return {
        'think_recall': f"{tnt['think_recall']:.0%}",
        'no_think_recall': f"{tnt['no_think_recall']:.0%}",
        'baseline_recall': f"{tnt['baseline_recall']:.0%}",
        'suppression_effect': f"{tnt['suppression_effect']:.0%}",
        'dose_response': {
            k: f"{v['recall']:.0%}"
            for k, v in dose['by_attempts'].items()
        },
        'independent_probe_recovery': f"{probe['recovery']:.0%}",
        'by_valence': {
            k: f"{v['recall']:.0%}"
            for k, v in emotion['by_valence'].items()
        },
        'interpretation': (
            f"Suppression effect: {tnt['suppression_effect']:.0%}. "
            f"More attempts = more forgetting. "
            f"Negative memories harder to suppress."
        )
    }


def get_memory_inhibition_facts() -> Dict[str, str]:
    """Get facts about memory inhibition."""
    return {
        'anderson_2001': 'Think/no-think paradigm discovery',
        'suppression_effect': '~10-15% reduction below baseline',
        'mechanism': 'Prefrontal control over hippocampus',
        'dose_response': 'More attempts = more forgetting',
        'independent_probe': 'Partial recovery suggests true inhibition',
        'emotional': 'Negative memories harder to suppress',
        'applications': 'PTSD, unwanted memories',
        'rif': 'Retrieval-induced forgetting - related phenomenon'
    }
