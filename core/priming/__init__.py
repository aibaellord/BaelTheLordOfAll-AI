"""
BAEL Priming Engine
====================

Implicit memory and priming effects.
Facilitation from prior exposure.

"Ba'el is influenced by the unseen." — Ba'el
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

logger = logging.getLogger("BAEL.Priming")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PrimingType(Enum):
    """Types of priming."""
    REPETITION = auto()    # Same item repeated
    SEMANTIC = auto()      # Related meaning
    PERCEPTUAL = auto()    # Similar appearance
    CONCEPTUAL = auto()    # Same category
    ASSOCIATIVE = auto()   # Associated items
    NEGATIVE = auto()      # Inhibitory priming


class PrimeRelation(Enum):
    """Relation between prime and target."""
    IDENTICAL = auto()     # Same item
    RELATED = auto()       # Semantically related
    UNRELATED = auto()     # No relation
    OPPOSITE = auto()      # Antonym


class TaskType(Enum):
    """Priming task types."""
    LEXICAL_DECISION = auto()   # Is it a word?
    NAMING = auto()             # Say the word
    FRAGMENT_COMPLETION = auto() # Complete _O_S_
    IDENTIFICATION = auto()      # Degraded stimulus


@dataclass
class Prime:
    """
    A prime stimulus.
    """
    id: str
    content: str
    type: PrimingType
    presentation_time: float
    duration: float
    masked: bool = False


@dataclass
class Target:
    """
    A target stimulus.
    """
    id: str
    content: str
    relation_to_prime: PrimeRelation
    is_word: bool = True  # For lexical decision


@dataclass
class PrimingTrial:
    """
    A priming trial.
    """
    id: str
    prime: Prime
    target: Target
    soa: float  # Stimulus onset asynchrony
    task: TaskType
    response_time: Optional[float] = None
    correct: Optional[bool] = None


@dataclass
class PrimingEffect:
    """
    Measured priming effect.
    """
    priming_type: PrimingType
    facilitation: float      # RT reduction (positive = faster)
    inhibition: float        # RT increase (positive = slower)
    accuracy_boost: float    # Accuracy improvement


@dataclass
class PrimingMetrics:
    """
    Overall priming metrics.
    """
    mean_facilitation: float
    mean_inhibition: float
    repetition_effect: float
    semantic_effect: float
    perceptual_effect: float


@dataclass
class MemoryTrace:
    """
    Implicit memory trace.
    """
    id: str
    content: str
    strength: float  # 0-1
    creation_time: float
    access_count: int = 0


# ============================================================================
# PRIME PROCESSOR
# ============================================================================

class PrimeProcessor:
    """
    Process prime stimuli.

    "Ba'el absorbs the prime." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._traces: Dict[str, MemoryTrace] = {}
        self._trace_counter = 0

        self._decay_rate = 0.1  # Per second
        self._encoding_strength = 0.8

        self._lock = threading.RLock()

    def _generate_trace_id(self) -> str:
        self._trace_counter += 1
        return f"trace_{self._trace_counter}"

    def process_prime(
        self,
        prime: Prime
    ) -> MemoryTrace:
        """Process prime and create trace."""
        with self._lock:
            # Create or strengthen trace
            if prime.content in [t.content for t in self._traces.values()]:
                # Strengthen existing
                for trace in self._traces.values():
                    if trace.content == prime.content:
                        trace.strength = min(1.0, trace.strength + 0.2)
                        trace.access_count += 1
                        return trace

            # Create new trace
            strength = self._encoding_strength

            if prime.masked:
                strength *= 0.5  # Masked primes create weaker traces

            trace = MemoryTrace(
                id=self._generate_trace_id(),
                content=prime.content,
                strength=strength,
                creation_time=time.time()
            )

            self._traces[trace.id] = trace
            return trace

    def get_trace_strength(
        self,
        content: str,
        current_time: float = None
    ) -> float:
        """Get current trace strength."""
        if current_time is None:
            current_time = time.time()

        for trace in self._traces.values():
            if trace.content == content:
                # Apply decay
                elapsed = current_time - trace.creation_time
                decayed_strength = trace.strength * math.exp(-self._decay_rate * elapsed)
                return decayed_strength

        return 0.0

    def get_related_strength(
        self,
        content: str,
        semantic_network: Dict[str, List[str]] = None
    ) -> float:
        """Get strength from related traces."""
        if semantic_network is None:
            return 0.0

        related = semantic_network.get(content, [])

        total_strength = 0.0
        for rel in related:
            strength = self.get_trace_strength(rel)
            total_strength += strength * 0.5  # Spreading activation

        return total_strength


# ============================================================================
# SEMANTIC NETWORK
# ============================================================================

class SemanticNetwork:
    """
    Semantic associations for priming.

    "Ba'el's web of meaning." — Ba'el
    """

    def __init__(self):
        """Initialize network."""
        self._associations: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Build some default associations
        self._build_default_network()

        self._lock = threading.RLock()

    def _build_default_network(self) -> None:
        """Build default semantic network."""
        # Category associations
        categories = {
            'dog': ['cat', 'pet', 'animal', 'bark', 'puppy'],
            'cat': ['dog', 'pet', 'animal', 'meow', 'kitten'],
            'doctor': ['nurse', 'hospital', 'patient', 'medicine'],
            'nurse': ['doctor', 'hospital', 'patient', 'care'],
            'bread': ['butter', 'toast', 'wheat', 'food'],
            'butter': ['bread', 'toast', 'spread', 'yellow'],
            'king': ['queen', 'crown', 'throne', 'royal'],
            'queen': ['king', 'crown', 'throne', 'royal'],
            'hot': ['cold', 'warm', 'heat', 'temperature'],
            'cold': ['hot', 'cool', 'freeze', 'winter']
        }

        for word, associates in categories.items():
            for assoc in associates:
                self._associations[word][assoc] = 0.8

    def add_association(
        self,
        word1: str,
        word2: str,
        strength: float = 0.5
    ) -> None:
        """Add association."""
        with self._lock:
            self._associations[word1][word2] = strength
            self._associations[word2][word1] = strength

    def get_associates(
        self,
        word: str
    ) -> Dict[str, float]:
        """Get associates and strengths."""
        return dict(self._associations.get(word, {}))

    def get_relation(
        self,
        word1: str,
        word2: str
    ) -> PrimeRelation:
        """Get relation between words."""
        if word1 == word2:
            return PrimeRelation.IDENTICAL

        associates = self._associations.get(word1, {})

        if word2 in associates:
            if associates[word2] < 0:
                return PrimeRelation.OPPOSITE
            return PrimeRelation.RELATED

        return PrimeRelation.UNRELATED

    def get_association_strength(
        self,
        word1: str,
        word2: str
    ) -> float:
        """Get association strength."""
        return self._associations.get(word1, {}).get(word2, 0.0)


# ============================================================================
# RESPONSE GENERATOR
# ============================================================================

class ResponseGenerator:
    """
    Generate primed responses.

    "Ba'el responds with primed speed." — Ba'el
    """

    def __init__(
        self,
        prime_processor: PrimeProcessor,
        semantic_network: SemanticNetwork
    ):
        """Initialize generator."""
        self._processor = prime_processor
        self._network = semantic_network

        self._base_rt = 0.6  # Base response time
        self._rt_variability = 0.1

        self._priming_effect = 0.05  # 50ms facilitation

        self._lock = threading.RLock()

    def generate_response(
        self,
        trial: PrimingTrial
    ) -> Tuple[float, bool]:
        """Generate response for trial."""
        with self._lock:
            # Base RT
            rt = random.gauss(self._base_rt, self._rt_variability)

            # Get priming effect
            prime_content = trial.prime.content
            target_content = trial.target.content

            # Repetition priming
            rep_strength = self._processor.get_trace_strength(target_content)

            # Semantic priming
            sem_strength = self._network.get_association_strength(
                prime_content, target_content
            )

            # Calculate facilitation
            if trial.target.relation_to_prime == PrimeRelation.IDENTICAL:
                facilitation = self._priming_effect * 2  # Strong repetition
            elif trial.target.relation_to_prime == PrimeRelation.RELATED:
                facilitation = self._priming_effect * (0.5 + sem_strength)
            elif trial.target.relation_to_prime == PrimeRelation.OPPOSITE:
                facilitation = -self._priming_effect * 0.5  # Inhibition
            else:
                facilitation = 0.0

            # SOA effects
            if trial.soa < 0.2:
                facilitation *= 0.5  # Reduced at short SOA
            elif trial.soa > 0.5:
                facilitation *= 0.8  # Reduced at long SOA

            # Masked priming
            if trial.prime.masked:
                facilitation *= 0.5

            # Apply facilitation
            rt -= facilitation
            rt = max(0.2, rt)  # Minimum RT

            # Accuracy
            base_accuracy = 0.95
            if trial.target.relation_to_prime == PrimeRelation.RELATED:
                accuracy = min(0.99, base_accuracy + 0.03)
            else:
                accuracy = base_accuracy

            correct = random.random() < accuracy

            return rt, correct


# ============================================================================
# PRIMING ENGINE
# ============================================================================

class PrimingEngine:
    """
    Complete priming engine.

    "Ba'el's implicit memory." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._processor = PrimeProcessor()
        self._network = SemanticNetwork()
        self._response_gen = ResponseGenerator(self._processor, self._network)

        self._trials: List[PrimingTrial] = []
        self._prime_counter = 0
        self._target_counter = 0
        self._trial_counter = 0

        self._lock = threading.RLock()

    def _generate_prime_id(self) -> str:
        self._prime_counter += 1
        return f"prime_{self._prime_counter}"

    def _generate_target_id(self) -> str:
        self._target_counter += 1
        return f"target_{self._target_counter}"

    def _generate_trial_id(self) -> str:
        self._trial_counter += 1
        return f"trial_{self._trial_counter}"

    # Prime creation

    def create_prime(
        self,
        content: str,
        priming_type: PrimingType = PrimingType.REPETITION,
        duration: float = 0.05,
        masked: bool = False
    ) -> Prime:
        """Create prime stimulus."""
        return Prime(
            id=self._generate_prime_id(),
            content=content,
            type=priming_type,
            presentation_time=time.time(),
            duration=duration,
            masked=masked
        )

    def create_target(
        self,
        content: str,
        prime: Prime,
        is_word: bool = True
    ) -> Target:
        """Create target stimulus."""
        relation = self._network.get_relation(prime.content, content)

        return Target(
            id=self._generate_target_id(),
            content=content,
            relation_to_prime=relation,
            is_word=is_word
        )

    # Trial execution

    def run_trial(
        self,
        prime: Prime,
        target: Target,
        soa: float = 0.3,
        task: TaskType = TaskType.LEXICAL_DECISION
    ) -> PrimingTrial:
        """Run a priming trial."""
        with self._lock:
            # Process prime
            self._processor.process_prime(prime)

            # Create trial
            trial = PrimingTrial(
                id=self._generate_trial_id(),
                prime=prime,
                target=target,
                soa=soa,
                task=task
            )

            # Generate response
            rt, correct = self._response_gen.generate_response(trial)

            trial.response_time = rt
            trial.correct = correct

            self._trials.append(trial)
            return trial

    def run_priming_experiment(
        self,
        word_pairs: List[Tuple[str, str, PrimeRelation]],
        soa: float = 0.3,
        masked: bool = False
    ) -> List[PrimingTrial]:
        """Run priming experiment with word pairs."""
        trials = []

        for prime_word, target_word, _ in word_pairs:
            prime = self.create_prime(
                prime_word,
                PrimingType.SEMANTIC,
                masked=masked
            )

            target = self.create_target(target_word, prime)

            trial = self.run_trial(prime, target, soa)
            trials.append(trial)

        return trials

    # Semantic network

    def add_association(
        self,
        word1: str,
        word2: str,
        strength: float = 0.5
    ) -> None:
        """Add semantic association."""
        self._network.add_association(word1, word2, strength)

    def get_associates(
        self,
        word: str
    ) -> Dict[str, float]:
        """Get semantic associates."""
        return self._network.get_associates(word)

    # Analysis

    def get_priming_effect(
        self,
        priming_type: PrimingType = None
    ) -> PrimingEffect:
        """Calculate priming effect."""
        with self._lock:
            related_rts = []
            unrelated_rts = []

            for trial in self._trials:
                if priming_type and trial.prime.type != priming_type:
                    continue

                if trial.response_time is None:
                    continue

                if trial.target.relation_to_prime in [PrimeRelation.IDENTICAL, PrimeRelation.RELATED]:
                    related_rts.append(trial.response_time)
                else:
                    unrelated_rts.append(trial.response_time)

            if not related_rts or not unrelated_rts:
                return PrimingEffect(
                    priming_type=priming_type or PrimingType.SEMANTIC,
                    facilitation=0.0,
                    inhibition=0.0,
                    accuracy_boost=0.0
                )

            mean_related = sum(related_rts) / len(related_rts)
            mean_unrelated = sum(unrelated_rts) / len(unrelated_rts)

            facilitation = mean_unrelated - mean_related

            # Accuracy
            related_acc = sum(1 for t in self._trials
                            if t.target.relation_to_prime == PrimeRelation.RELATED
                            and t.correct) / max(1, len(related_rts))
            unrelated_acc = sum(1 for t in self._trials
                               if t.target.relation_to_prime == PrimeRelation.UNRELATED
                               and t.correct) / max(1, len(unrelated_rts))

            return PrimingEffect(
                priming_type=priming_type or PrimingType.SEMANTIC,
                facilitation=facilitation,
                inhibition=0.0,
                accuracy_boost=related_acc - unrelated_acc
            )

    def get_metrics(self) -> PrimingMetrics:
        """Get overall priming metrics."""
        rep_effect = self.get_priming_effect(PrimingType.REPETITION)
        sem_effect = self.get_priming_effect(PrimingType.SEMANTIC)

        return PrimingMetrics(
            mean_facilitation=rep_effect.facilitation,
            mean_inhibition=rep_effect.inhibition,
            repetition_effect=rep_effect.facilitation,
            semantic_effect=sem_effect.facilitation,
            perceptual_effect=0.0  # Would need perceptual trials
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'trials': len(self._trials),
            'traces': len(self._processor._traces),
            'associations': sum(len(v) for v in self._network._associations.values())
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_priming_engine() -> PrimingEngine:
    """Create priming engine."""
    return PrimingEngine()


def run_semantic_priming_experiment(
    num_trials: int = 40
) -> PrimingEffect:
    """Run semantic priming experiment."""
    engine = create_priming_engine()

    # Default word pairs
    pairs = [
        ('doctor', 'nurse', PrimeRelation.RELATED),
        ('doctor', 'bread', PrimeRelation.UNRELATED),
        ('dog', 'cat', PrimeRelation.RELATED),
        ('dog', 'chair', PrimeRelation.UNRELATED),
        ('king', 'queen', PrimeRelation.RELATED),
        ('king', 'lamp', PrimeRelation.UNRELATED),
        ('hot', 'cold', PrimeRelation.RELATED),
        ('hot', 'desk', PrimeRelation.UNRELATED),
    ]

    # Repeat to get enough trials
    all_pairs = pairs * (num_trials // len(pairs) + 1)
    all_pairs = all_pairs[:num_trials]

    random.shuffle(all_pairs)

    engine.run_priming_experiment(all_pairs)

    return engine.get_priming_effect(PrimingType.SEMANTIC)


def get_priming_types_explained() -> Dict[PrimingType, str]:
    """Get explanation of priming types."""
    return {
        PrimingType.REPETITION: "Same stimulus repeated - strongest effect",
        PrimingType.SEMANTIC: "Related meaning - DOCTOR primes NURSE",
        PrimingType.PERCEPTUAL: "Similar appearance - same font, degradation",
        PrimingType.CONCEPTUAL: "Same category - APPLE primes ORANGE",
        PrimingType.ASSOCIATIVE: "Learned association - SALT primes PEPPER",
        PrimingType.NEGATIVE: "Inhibitory - STOP primes inhibition"
    }
