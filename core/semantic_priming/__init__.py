"""
BAEL Semantic Priming Engine
================================

Lexical decision and word recognition.
Spreading activation in semantics.

"Ba'el primes the meaning." — Ba'el
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

logger = logging.getLogger("BAEL.SemanticPriming")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PrimingType(Enum):
    """Types of semantic priming."""
    ASSOCIATIVE = auto()       # Word associations (doctor-nurse)
    CATEGORICAL = auto()       # Category members (bird-robin)
    FUNCTIONAL = auto()        # Functional relations (broom-sweep)
    CONTEXTUAL = auto()        # Context-based (garden-plant)


class LexicalStatus(Enum):
    """Lexical status."""
    WORD = auto()
    NONWORD = auto()


class SOACondition(Enum):
    """SOA condition."""
    SHORT = auto()      # Automatic priming
    LONG = auto()       # Strategic priming


class RelatednessType(Enum):
    """Relatedness between prime and target."""
    RELATED = auto()
    UNRELATED = auto()
    NEUTRAL = auto()


@dataclass
class LexicalItem:
    """
    A lexical item (word or nonword).
    """
    id: str
    string: str
    status: LexicalStatus
    frequency: float  # Word frequency (0-1)
    length: int

    # For words only
    semantic_features: Set[str] = field(default_factory=set)
    associations: Dict[str, float] = field(default_factory=dict)


@dataclass
class PrimingTrial:
    """
    A priming trial.
    """
    prime: LexicalItem
    target: LexicalItem
    relatedness: RelatednessType
    soa: float
    response_time: float
    correct: bool
    priming_effect: float


@dataclass
class LexicalDecisionResult:
    """
    Result of lexical decision.
    """
    item: LexicalItem
    decision: LexicalStatus
    correct: bool
    response_time: float


@dataclass
class SemanticPrimingMetrics:
    """
    Semantic priming metrics.
    """
    facilitation: float
    inhibition: float
    net_priming: float
    automatic_vs_strategic: float


# ============================================================================
# MENTAL LEXICON
# ============================================================================

class MentalLexicon:
    """
    Mental lexicon with semantic associations.

    "Ba'el's word store." — Ba'el
    """

    def __init__(self):
        """Initialize lexicon."""
        self._items: Dict[str, LexicalItem] = {}
        self._associations: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._category_members: Dict[str, Set[str]] = defaultdict(set)

        self._item_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._item_counter += 1
        return f"item_{self._item_counter}"

    def add_word(
        self,
        word: str,
        frequency: float = 0.5,
        semantic_features: Set[str] = None,
        category: str = None
    ) -> LexicalItem:
        """Add a word to the lexicon."""
        item = LexicalItem(
            id=self._generate_id(),
            string=word.lower(),
            status=LexicalStatus.WORD,
            frequency=frequency,
            length=len(word),
            semantic_features=semantic_features or set()
        )

        self._items[word.lower()] = item

        if category:
            self._category_members[category].add(word.lower())

        return item

    def add_nonword(
        self,
        nonword: str
    ) -> LexicalItem:
        """Add a nonword."""
        item = LexicalItem(
            id=self._generate_id(),
            string=nonword.lower(),
            status=LexicalStatus.NONWORD,
            frequency=0.0,
            length=len(nonword)
        )

        self._items[nonword.lower()] = item
        return item

    def add_association(
        self,
        word1: str,
        word2: str,
        strength: float
    ) -> None:
        """Add bidirectional association."""
        w1, w2 = word1.lower(), word2.lower()

        self._associations[w1][w2] = strength
        self._associations[w2][w1] = strength

        if w1 in self._items:
            self._items[w1].associations[w2] = strength
        if w2 in self._items:
            self._items[w2].associations[w1] = strength

    def get_association_strength(
        self,
        word1: str,
        word2: str
    ) -> float:
        """Get association strength between words."""
        w1, w2 = word1.lower(), word2.lower()
        return self._associations.get(w1, {}).get(w2, 0.0)

    def get_item(
        self,
        string: str
    ) -> Optional[LexicalItem]:
        """Get lexical item."""
        return self._items.get(string.lower())

    def get_semantic_similarity(
        self,
        word1: str,
        word2: str
    ) -> float:
        """Get semantic similarity based on features."""
        item1 = self.get_item(word1)
        item2 = self.get_item(word2)

        if not item1 or not item2:
            return 0.0

        if not item1.semantic_features or not item2.semantic_features:
            return 0.0

        intersection = item1.semantic_features & item2.semantic_features
        union = item1.semantic_features | item2.semantic_features

        return len(intersection) / len(union) if union else 0.0

    def get_category_relatedness(
        self,
        word1: str,
        word2: str
    ) -> float:
        """Get relatedness based on shared categories."""
        w1, w2 = word1.lower(), word2.lower()

        shared_categories = 0
        total_categories = 0

        for category, members in self._category_members.items():
            if w1 in members or w2 in members:
                total_categories += 1
                if w1 in members and w2 in members:
                    shared_categories += 1

        return shared_categories / total_categories if total_categories > 0 else 0.0


# ============================================================================
# SPREADING ACTIVATION
# ============================================================================

class SpreadingActivationModel:
    """
    Spreading activation for priming.

    "Ba'el's activation spreads." — Ba'el
    """

    def __init__(
        self,
        decay_rate: float = 0.9,
        threshold: float = 0.1
    ):
        """Initialize model."""
        self._activations: Dict[str, float] = defaultdict(float)
        self._decay_rate = decay_rate
        self._threshold = threshold

        self._lock = threading.RLock()

    def reset(self) -> None:
        """Reset all activations."""
        self._activations.clear()

    def activate(
        self,
        word: str,
        amount: float = 1.0
    ) -> None:
        """Activate a word node."""
        self._activations[word.lower()] = min(
            1.0, self._activations[word.lower()] + amount
        )

    def spread(
        self,
        source: str,
        associations: Dict[str, float],
        spread_ratio: float = 0.5
    ) -> Dict[str, float]:
        """Spread activation to associated nodes."""
        source_activation = self._activations.get(source.lower(), 0)

        spread_amounts = {}

        for target, strength in associations.items():
            spread = source_activation * strength * spread_ratio

            if spread > self._threshold:
                old_activation = self._activations[target]
                self._activations[target] = min(
                    1.0, old_activation + spread
                )
                spread_amounts[target] = self._activations[target] - old_activation

        return spread_amounts

    def decay(self) -> None:
        """Apply decay to all activations."""
        for word in list(self._activations.keys()):
            self._activations[word] *= self._decay_rate

            if self._activations[word] < self._threshold:
                del self._activations[word]

    def get_activation(
        self,
        word: str
    ) -> float:
        """Get current activation of a word."""
        return self._activations.get(word.lower(), 0.0)


# ============================================================================
# LEXICAL DECISION
# ============================================================================

class LexicalDecisionTask:
    """
    Lexical decision task.

    "Ba'el decides: word or not." — Ba'el
    """

    def __init__(
        self,
        lexicon: MentalLexicon,
        base_rt: float = 500.0
    ):
        """Initialize task."""
        self._lexicon = lexicon
        self._base_rt = base_rt

        self._lock = threading.RLock()

    def decide(
        self,
        string: str,
        activation_level: float = 0.0
    ) -> LexicalDecisionResult:
        """Make a lexical decision."""
        item = self._lexicon.get_item(string)

        if item is None:
            # Unknown item - treat as nonword
            decision = LexicalStatus.NONWORD
            correct = True  # Assuming it's actually a nonword
            rt = self._base_rt + random.gauss(0, 50)
        else:
            # Known item
            decision = item.status
            correct = True

            # RT based on frequency and activation
            frequency_effect = (1 - item.frequency) * 100
            activation_benefit = activation_level * 80

            rt = self._base_rt + frequency_effect - activation_benefit
            rt += random.gauss(0, 30)

        return LexicalDecisionResult(
            item=item if item else LexicalItem(
                id="unknown",
                string=string,
                status=LexicalStatus.NONWORD,
                frequency=0.0,
                length=len(string)
            ),
            decision=decision,
            correct=correct,
            response_time=max(200, rt)
        )


# ============================================================================
# SEMANTIC PRIMING ENGINE
# ============================================================================

class SemanticPrimingEngine:
    """
    Complete semantic priming engine.

    "Ba'el's priming system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._lexicon = MentalLexicon()
        self._activation = SpreadingActivationModel()
        self._ldt = LexicalDecisionTask(self._lexicon)

        self._trials: List[PrimingTrial] = []

        self._lock = threading.RLock()

    # Lexicon building

    def add_word(
        self,
        word: str,
        frequency: float = 0.5,
        features: Set[str] = None,
        category: str = None
    ) -> LexicalItem:
        """Add a word."""
        return self._lexicon.add_word(word, frequency, features, category)

    def add_nonword(
        self,
        nonword: str
    ) -> LexicalItem:
        """Add a nonword."""
        return self._lexicon.add_nonword(nonword)

    def add_association(
        self,
        word1: str,
        word2: str,
        strength: float
    ) -> None:
        """Add association between words."""
        self._lexicon.add_association(word1, word2, strength)

    # Priming trials

    def run_trial(
        self,
        prime: str,
        target: str,
        soa: float = 250.0
    ) -> PrimingTrial:
        """Run a single priming trial."""
        self._activation.reset()

        # Get items
        prime_item = self._lexicon.get_item(prime)
        target_item = self._lexicon.get_item(target)

        if not prime_item or not target_item:
            return None

        # Present prime
        self._activation.activate(prime, 1.0)

        # SOA determines spread
        if soa >= 250:  # Enough time for spreading
            associations = prime_item.associations
            self._activation.spread(prime, associations)

            # Decay based on SOA
            decay_steps = int(soa / 100)
            for _ in range(decay_steps):
                self._activation.decay()

        # Get target activation
        target_activation = self._activation.get_activation(target)

        # Lexical decision on target
        result = self._ldt.decide(target, target_activation)

        # Determine relatedness
        association = self._lexicon.get_association_strength(prime, target)
        if association > 0.3:
            relatedness = RelatednessType.RELATED
        elif association < 0.1:
            relatedness = RelatednessType.UNRELATED
        else:
            relatedness = RelatednessType.NEUTRAL

        # Calculate priming effect (compared to baseline)
        baseline_rt = self._ldt._base_rt
        priming_effect = baseline_rt - result.response_time

        trial = PrimingTrial(
            prime=prime_item,
            target=target_item,
            relatedness=relatedness,
            soa=soa,
            response_time=result.response_time,
            correct=result.correct,
            priming_effect=priming_effect
        )

        self._trials.append(trial)
        return trial

    def run_priming_experiment(
        self,
        related_pairs: List[Tuple[str, str]],
        unrelated_pairs: List[Tuple[str, str]],
        soa: float = 250.0
    ) -> Dict[str, Any]:
        """Run a priming experiment."""
        related_rts = []
        unrelated_rts = []

        for prime, target in related_pairs:
            trial = self.run_trial(prime, target, soa)
            if trial:
                related_rts.append(trial.response_time)

        for prime, target in unrelated_pairs:
            trial = self.run_trial(prime, target, soa)
            if trial:
                unrelated_rts.append(trial.response_time)

        mean_related = sum(related_rts) / len(related_rts) if related_rts else 0
        mean_unrelated = sum(unrelated_rts) / len(unrelated_rts) if unrelated_rts else 0

        priming_effect = mean_unrelated - mean_related

        return {
            'related_rt': mean_related,
            'unrelated_rt': mean_unrelated,
            'priming_effect': priming_effect,
            'soa': soa,
            'n_related': len(related_rts),
            'n_unrelated': len(unrelated_rts)
        }

    def run_soa_manipulation(
        self,
        related_pairs: List[Tuple[str, str]],
        unrelated_pairs: List[Tuple[str, str]],
        soas: List[float]
    ) -> Dict[str, List[float]]:
        """Test priming at different SOAs."""
        priming_effects = []

        for soa in soas:
            result = self.run_priming_experiment(
                related_pairs, unrelated_pairs, soa
            )
            priming_effects.append(result['priming_effect'])

        return {
            'soas': soas,
            'priming_effects': priming_effects,
            'short_soa_priming': priming_effects[0] if priming_effects else 0,
            'long_soa_priming': priming_effects[-1] if priming_effects else 0
        }

    # Analysis

    def get_facilitation_and_inhibition(self) -> Tuple[float, float]:
        """Calculate facilitation and inhibition."""
        related_trials = [t for t in self._trials if t.relatedness == RelatednessType.RELATED]
        unrelated_trials = [t for t in self._trials if t.relatedness == RelatednessType.UNRELATED]

        if not related_trials or not unrelated_trials:
            return 0.0, 0.0

        baseline = self._ldt._base_rt

        related_rt = sum(t.response_time for t in related_trials) / len(related_trials)
        unrelated_rt = sum(t.response_time for t in unrelated_trials) / len(unrelated_trials)

        # Facilitation: faster than baseline (positive)
        facilitation = baseline - related_rt

        # Inhibition: slower than baseline (positive)
        inhibition = unrelated_rt - baseline

        return max(0, facilitation), max(0, inhibition)

    def get_metrics(self) -> SemanticPrimingMetrics:
        """Get semantic priming metrics."""
        facilitation, inhibition = self.get_facilitation_and_inhibition()
        net_priming = facilitation + inhibition

        # Automatic vs strategic ratio
        short_soa = [t for t in self._trials if t.soa < 300]
        long_soa = [t for t in self._trials if t.soa >= 300]

        if short_soa and long_soa:
            short_effect = sum(t.priming_effect for t in short_soa) / len(short_soa)
            long_effect = sum(t.priming_effect for t in long_soa) / len(long_soa)
            ratio = short_effect / long_effect if long_effect > 0 else 1.0
        else:
            ratio = 1.0

        return SemanticPrimingMetrics(
            facilitation=facilitation,
            inhibition=inhibition,
            net_priming=net_priming,
            automatic_vs_strategic=ratio
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'words': len([
                i for i in self._lexicon._items.values()
                if i.status == LexicalStatus.WORD
            ]),
            'nonwords': len([
                i for i in self._lexicon._items.values()
                if i.status == LexicalStatus.NONWORD
            ]),
            'associations': sum(
                len(a) for a in self._lexicon._associations.values()
            ) // 2,
            'trials': len(self._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_semantic_priming_engine() -> SemanticPrimingEngine:
    """Create semantic priming engine."""
    return SemanticPrimingEngine()


def demonstrate_semantic_priming() -> Dict[str, Any]:
    """Demonstrate semantic priming."""
    engine = create_semantic_priming_engine()

    # Build a small lexicon
    words = [
        ("doctor", 0.7, {"medical", "person", "profession"}),
        ("nurse", 0.6, {"medical", "person", "profession"}),
        ("hospital", 0.6, {"medical", "building"}),
        ("bread", 0.8, {"food", "baked"}),
        ("butter", 0.7, {"food", "dairy"}),
        ("table", 0.8, {"furniture", "flat"})
    ]

    for word, freq, features in words:
        engine.add_word(word, freq, features, word)

    # Add nonwords
    for nonword in ["nursp", "doctar", "tabble"]:
        engine.add_nonword(nonword)

    # Add associations
    engine.add_association("doctor", "nurse", 0.8)
    engine.add_association("doctor", "hospital", 0.7)
    engine.add_association("bread", "butter", 0.9)
    engine.add_association("doctor", "butter", 0.05)  # Unrelated

    # Related and unrelated pairs
    related = [("doctor", "nurse"), ("bread", "butter")]
    unrelated = [("doctor", "butter"), ("bread", "table")]

    # Run experiment
    result = engine.run_priming_experiment(related, unrelated, soa=250)

    # SOA manipulation
    soa_result = engine.run_soa_manipulation(
        related, unrelated,
        [100, 250, 500, 800]
    )

    metrics = engine.get_metrics()

    return {
        'priming_effect': result['priming_effect'],
        'related_rt': result['related_rt'],
        'unrelated_rt': result['unrelated_rt'],
        'soa_effects': {
            'short_soa_100': soa_result['priming_effects'][0],
            'long_soa_800': soa_result['priming_effects'][-1]
        },
        'facilitation': metrics.facilitation,
        'inhibition': metrics.inhibition,
        'interpretation': (
            f"Priming effect: {result['priming_effect']:.0f}ms, "
            f"Related faster than unrelated"
        )
    }


def get_semantic_priming_facts() -> Dict[str, str]:
    """Get facts about semantic priming."""
    return {
        'meyer_schvaneveldt': 'Classic 1971 lexical decision priming study',
        'spreading_activation': 'Collins & Loftus: activation spreads through network',
        'automatic_priming': 'Short SOA (<300ms): automatic, unavoidable',
        'strategic_priming': 'Long SOA (>500ms): expectancy-based, controllable',
        'facilitation': 'Related targets faster than neutral',
        'inhibition': 'Unrelated targets sometimes slower than neutral',
        'association_vs_semantic': 'Debate: association or true semantic priming',
        'mediated_priming': 'Indirect priming through intermediate concepts'
    }
