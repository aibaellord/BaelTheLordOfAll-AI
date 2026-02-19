"""
BAEL Judgment Heuristics Engine
=================================

Kahneman & Tversky heuristics.
Anchoring, availability, representativeness.

"Ba'el shortcuts wisely." — Ba'el
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

logger = logging.getLogger("BAEL.JudgmentHeuristics")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class HeuristicType(Enum):
    """Types of judgment heuristics."""
    REPRESENTATIVENESS = auto()    # Similarity to prototype
    AVAILABILITY = auto()           # Ease of retrieval
    ANCHORING = auto()              # Adjustment from anchor
    AFFECT = auto()                 # Emotional influence
    RECOGNITION = auto()            # Familiarity-based
    FLUENCY = auto()                # Processing ease


class BiasType(Enum):
    """Types of cognitive biases."""
    BASE_RATE_NEGLECT = auto()     # Ignoring prior probabilities
    CONJUNCTION_FALLACY = auto()   # P(A&B) > P(A)
    INSUFFICIENT_ADJUSTMENT = auto()
    RECENCY_BIAS = auto()
    VIVIDNESS_BIAS = auto()
    OVERCONFIDENCE = auto()
    HINDSIGHT = auto()


class JudgmentDomain(Enum):
    """Domains for judgment."""
    PROBABILITY = auto()
    FREQUENCY = auto()
    PREDICTION = auto()
    RISK = auto()
    VALUE = auto()


@dataclass
class Anchor:
    """
    An anchor value.
    """
    value: float
    source: str
    relevance: float


@dataclass
class MemoryInstance:
    """
    An instance in memory for availability.
    """
    id: str
    content: str
    vividness: float
    recency: float
    retrieval_ease: float


@dataclass
class Prototype:
    """
    A prototype for representativeness.
    """
    category: str
    features: Dict[str, float]
    typicality: float


@dataclass
class JudgmentResult:
    """
    Result of a judgment.
    """
    heuristic: HeuristicType
    judgment: float
    confidence: float
    biases_present: List[BiasType]
    normative_value: Optional[float]


@dataclass
class HeuristicMetrics:
    """
    Heuristic usage metrics.
    """
    representativeness_usage: float
    availability_usage: float
    anchoring_effect: float
    bias_rate: float


# ============================================================================
# REPRESENTATIVENESS HEURISTIC
# ============================================================================

class RepresentativenessHeuristic:
    """
    Kahneman & Tversky representativeness.

    "Ba'el judges by similarity." — Ba'el
    """

    def __init__(self):
        """Initialize heuristic."""
        self._prototypes: Dict[str, Prototype] = {}
        self._base_rates: Dict[str, float] = {}

        self._lock = threading.RLock()

    def add_prototype(
        self,
        category: str,
        features: Dict[str, float],
        base_rate: float = 0.5
    ) -> None:
        """Add a category prototype."""
        self._prototypes[category] = Prototype(
            category=category,
            features=features,
            typicality=1.0
        )
        self._base_rates[category] = base_rate

    def calculate_similarity(
        self,
        instance_features: Dict[str, float],
        category: str
    ) -> float:
        """Calculate similarity to prototype."""
        prototype = self._prototypes.get(category)
        if not prototype:
            return 0.0

        total_sim = 0.0
        count = 0

        for feature, proto_value in prototype.features.items():
            if feature in instance_features:
                inst_value = instance_features[feature]
                # Feature match
                match = 1 - abs(proto_value - inst_value)
                total_sim += match
                count += 1

        return total_sim / count if count > 0 else 0.0

    def judge_category_membership(
        self,
        instance_features: Dict[str, float],
        category: str,
        use_base_rate: bool = False
    ) -> JudgmentResult:
        """Judge probability of category membership."""
        similarity = self.calculate_similarity(instance_features, category)

        # By default, judge by similarity alone (base rate neglect)
        if use_base_rate:
            base_rate = self._base_rates.get(category, 0.5)
            # Bayesian: P(category|features) ∝ P(features|category) × P(category)
            judgment = similarity * base_rate
            biases = []
        else:
            judgment = similarity
            biases = [BiasType.BASE_RATE_NEGLECT]

        return JudgmentResult(
            heuristic=HeuristicType.REPRESENTATIVENESS,
            judgment=judgment,
            confidence=0.7 + similarity * 0.3,
            biases_present=biases,
            normative_value=similarity * self._base_rates.get(category, 0.5)
        )

    def demonstrate_conjunction_fallacy(
        self,
        person_features: Dict[str, float],
        broad_category: str,
        narrow_conjunction: Tuple[str, str]
    ) -> Dict[str, Any]:
        """Demonstrate conjunction fallacy."""
        # Probability of broad category
        broad_sim = self.calculate_similarity(person_features, broad_category)

        # Probability of conjunction (should always be <= broad)
        cat1_sim = self.calculate_similarity(person_features, narrow_conjunction[0])
        cat2_sim = self.calculate_similarity(person_features, narrow_conjunction[1])

        # People often judge conjunction as more likely if representative
        conjunction_sim = (cat1_sim + cat2_sim) / 2

        # Fallacy occurs when conjunction judged more likely
        fallacy_present = conjunction_sim > broad_sim

        return {
            'broad_category': broad_category,
            'broad_probability': broad_sim,
            'conjunction': f"{narrow_conjunction[0]} & {narrow_conjunction[1]}",
            'conjunction_probability': conjunction_sim,
            'fallacy_present': fallacy_present,
            'normative': f"P({narrow_conjunction[0]} & {narrow_conjunction[1]}) <= P({broad_category})"
        }


# ============================================================================
# AVAILABILITY HEURISTIC
# ============================================================================

class AvailabilityHeuristic:
    """
    Tversky & Kahneman availability heuristic.

    "Ba'el judges by what comes to mind." — Ba'el
    """

    def __init__(self):
        """Initialize heuristic."""
        self._memory: List[MemoryInstance] = []
        self._category_instances: Dict[str, List[str]] = defaultdict(list)

        self._instance_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._instance_counter += 1
        return f"mem_{self._instance_counter}"

    def add_instance(
        self,
        content: str,
        category: str,
        vividness: float = 0.5,
        recency: float = 0.5
    ) -> MemoryInstance:
        """Add a memory instance."""
        # Retrieval ease based on vividness and recency
        retrieval_ease = 0.4 * vividness + 0.4 * recency + 0.2

        instance = MemoryInstance(
            id=self._generate_id(),
            content=content,
            vividness=vividness,
            recency=recency,
            retrieval_ease=retrieval_ease
        )

        self._memory.append(instance)
        self._category_instances[category].append(instance.id)

        return instance

    def estimate_frequency(
        self,
        category: str
    ) -> JudgmentResult:
        """Estimate frequency/probability based on availability."""
        instances = self._category_instances.get(category, [])

        # Find instances
        available_instances = [
            m for m in self._memory
            if m.id in instances
        ]

        if not available_instances:
            return JudgmentResult(
                heuristic=HeuristicType.AVAILABILITY,
                judgment=0.0,
                confidence=0.3,
                biases_present=[],
                normative_value=None
            )

        # Weight by retrieval ease
        ease_weighted = sum(
            inst.retrieval_ease for inst in available_instances
        )

        # Normalize by total memory
        if self._memory:
            judgment = ease_weighted / len(self._memory)
        else:
            judgment = 0.5

        # Biases
        biases = []

        # Check for vividness bias
        avg_vividness = sum(i.vividness for i in available_instances) / len(available_instances)
        if avg_vividness > 0.7:
            biases.append(BiasType.VIVIDNESS_BIAS)

        # Check for recency bias
        avg_recency = sum(i.recency for i in available_instances) / len(available_instances)
        if avg_recency > 0.7:
            biases.append(BiasType.RECENCY_BIAS)

        return JudgmentResult(
            heuristic=HeuristicType.AVAILABILITY,
            judgment=judgment,
            confidence=0.5 + avg_vividness * 0.3,
            biases_present=biases,
            normative_value=len(instances) / len(self._memory) if self._memory else None
        )

    def demonstrate_availability_bias(
        self,
        category_a: str,
        category_b: str,
        actual_freq_a: int,
        actual_freq_b: int,
        vividness_a: float,
        vividness_b: float
    ) -> Dict[str, Any]:
        """Demonstrate availability bias."""
        # Add instances with different vividness
        for _ in range(actual_freq_a):
            self.add_instance(f"{category_a} event", category_a, vividness_a)

        for _ in range(actual_freq_b):
            self.add_instance(f"{category_b} event", category_b, vividness_b)

        # Judge frequencies
        result_a = self.estimate_frequency(category_a)
        result_b = self.estimate_frequency(category_b)

        # Check for bias: vivid category judged more frequent
        normative_a_more = actual_freq_a > actual_freq_b
        judged_a_more = result_a.judgment > result_b.judgment

        bias_present = normative_a_more != judged_a_more

        return {
            'category_a': category_a,
            'actual_freq_a': actual_freq_a,
            'judged_freq_a': result_a.judgment,
            'vividness_a': vividness_a,
            'category_b': category_b,
            'actual_freq_b': actual_freq_b,
            'judged_freq_b': result_b.judgment,
            'vividness_b': vividness_b,
            'bias_present': bias_present,
            'explanation': 'Vivid events are overestimated'
        }


# ============================================================================
# ANCHORING HEURISTIC
# ============================================================================

class AnchoringHeuristic:
    """
    Tversky & Kahneman anchoring and adjustment.

    "Ba'el starts from the anchor." — Ba'el
    """

    def __init__(
        self,
        adjustment_factor: float = 0.4
    ):
        """Initialize heuristic."""
        self._adjustment_factor = adjustment_factor  # How much we adjust from anchor
        self._anchors: Dict[str, Anchor] = {}

        self._lock = threading.RLock()

    def set_anchor(
        self,
        question: str,
        value: float,
        source: str = "arbitrary",
        relevance: float = 0.5
    ) -> None:
        """Set an anchor for a question."""
        self._anchors[question] = Anchor(
            value=value,
            source=source,
            relevance=relevance
        )

    def estimate(
        self,
        question: str,
        anchor: float = None,
        true_value: float = None
    ) -> JudgmentResult:
        """Make an estimate with anchoring."""
        # Use provided anchor or stored anchor
        if anchor is None:
            stored = self._anchors.get(question)
            if stored:
                anchor = stored.value
            else:
                anchor = 50.0  # Default middle anchor

        # Adjustment is typically insufficient
        if true_value is not None:
            # We know the true value - calculate ideal adjustment
            needed_adjustment = true_value - anchor
            actual_adjustment = needed_adjustment * self._adjustment_factor
            judgment = anchor + actual_adjustment

            biases = [BiasType.INSUFFICIENT_ADJUSTMENT]
            normative = true_value
        else:
            # Random adjustment when we don't know true value
            adjustment = random.gauss(0, 20) * self._adjustment_factor
            judgment = anchor + adjustment

            biases = [BiasType.INSUFFICIENT_ADJUSTMENT]
            normative = None

        return JudgmentResult(
            heuristic=HeuristicType.ANCHORING,
            judgment=judgment,
            confidence=0.6,
            biases_present=biases,
            normative_value=normative
        )

    def demonstrate_anchoring(
        self,
        question: str,
        low_anchor: float,
        high_anchor: float,
        true_value: float
    ) -> Dict[str, Any]:
        """Demonstrate anchoring effect."""
        # Estimate with low anchor
        result_low = self.estimate(question, low_anchor, true_value)

        # Estimate with high anchor
        result_high = self.estimate(question, high_anchor, true_value)

        anchoring_effect = result_high.judgment - result_low.judgment
        expected_effect = (high_anchor - low_anchor) * (1 - self._adjustment_factor)

        return {
            'question': question,
            'low_anchor': low_anchor,
            'high_anchor': high_anchor,
            'true_value': true_value,
            'low_anchor_estimate': result_low.judgment,
            'high_anchor_estimate': result_high.judgment,
            'anchoring_effect': anchoring_effect,
            'insufficient_adjustment': result_high.judgment > true_value or result_low.judgment < true_value
        }


# ============================================================================
# JUDGMENT HEURISTICS ENGINE
# ============================================================================

class JudgmentHeuristicsEngine:
    """
    Complete judgment heuristics engine.

    "Ba'el's bounded rationality." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._representativeness = RepresentativenessHeuristic()
        self._availability = AvailabilityHeuristic()
        self._anchoring = AnchoringHeuristic()

        self._judgments: List[JudgmentResult] = []

        self._lock = threading.RLock()

    # Representativeness

    def add_category_prototype(
        self,
        category: str,
        features: Dict[str, float],
        base_rate: float = 0.5
    ) -> None:
        """Add a category prototype."""
        self._representativeness.add_prototype(category, features, base_rate)

    def judge_representativeness(
        self,
        instance_features: Dict[str, float],
        category: str,
        use_base_rate: bool = False
    ) -> JudgmentResult:
        """Judge by representativeness."""
        result = self._representativeness.judge_category_membership(
            instance_features, category, use_base_rate
        )
        self._judgments.append(result)
        return result

    def demonstrate_linda_problem(self) -> Dict[str, Any]:
        """Classic Linda problem (conjunction fallacy)."""
        # Add prototypes
        self.add_category_prototype(
            "bank_teller",
            {"conservative": 0.7, "quiet": 0.6, "conventional": 0.8},
            base_rate=0.1
        )
        self.add_category_prototype(
            "feminist",
            {"progressive": 0.9, "active": 0.8, "outspoken": 0.7},
            base_rate=0.2
        )

        # Linda's description
        linda_features = {
            "progressive": 0.9,
            "active": 0.85,
            "outspoken": 0.8,
            "concerned_social": 0.95,
            "conservative": 0.1,
            "quiet": 0.2
        }

        return self._representativeness.demonstrate_conjunction_fallacy(
            linda_features,
            "bank_teller",
            ("bank_teller", "feminist")
        )

    # Availability

    def add_memory_event(
        self,
        content: str,
        category: str,
        vividness: float = 0.5,
        recency: float = 0.5
    ) -> None:
        """Add a memory event."""
        self._availability.add_instance(content, category, vividness, recency)

    def judge_frequency(
        self,
        category: str
    ) -> JudgmentResult:
        """Judge frequency by availability."""
        result = self._availability.estimate_frequency(category)
        self._judgments.append(result)
        return result

    def demonstrate_availability_effect(self) -> Dict[str, Any]:
        """Demonstrate availability bias."""
        # Clear previous
        self._availability._memory.clear()
        self._availability._category_instances.clear()

        # Plane crashes: rare but vivid
        # Car accidents: common but less vivid
        return self._availability.demonstrate_availability_bias(
            "plane_crash", "car_accident",
            actual_freq_a=5, actual_freq_b=50,
            vividness_a=0.95, vividness_b=0.3
        )

    # Anchoring

    def judge_with_anchor(
        self,
        question: str,
        anchor: float,
        true_value: float = None
    ) -> JudgmentResult:
        """Make judgment with anchor."""
        result = self._anchoring.estimate(question, anchor, true_value)
        self._judgments.append(result)
        return result

    def demonstrate_anchoring_effect(self) -> Dict[str, Any]:
        """Demonstrate anchoring effect."""
        return self._anchoring.demonstrate_anchoring(
            "Percentage of African countries in UN",
            low_anchor=10,
            high_anchor=65,
            true_value=28
        )

    # Analysis

    def get_bias_summary(self) -> Dict[str, int]:
        """Get summary of biases observed."""
        bias_counts = defaultdict(int)

        for judgment in self._judgments:
            for bias in judgment.biases_present:
                bias_counts[bias.name] += 1

        return dict(bias_counts)

    def get_heuristic_usage(self) -> Dict[str, int]:
        """Get heuristic usage counts."""
        usage = defaultdict(int)

        for judgment in self._judgments:
            usage[judgment.heuristic.name] += 1

        return dict(usage)

    def get_metrics(self) -> HeuristicMetrics:
        """Get heuristic metrics."""
        total = len(self._judgments) if self._judgments else 1

        rep_count = sum(1 for j in self._judgments if j.heuristic == HeuristicType.REPRESENTATIVENESS)
        avail_count = sum(1 for j in self._judgments if j.heuristic == HeuristicType.AVAILABILITY)

        bias_count = sum(len(j.biases_present) for j in self._judgments)

        # Anchoring effect: average difference from normative
        anchor_judgments = [
            j for j in self._judgments
            if j.heuristic == HeuristicType.ANCHORING and j.normative_value is not None
        ]
        if anchor_judgments:
            anchor_effect = sum(
                abs(j.judgment - j.normative_value) for j in anchor_judgments
            ) / len(anchor_judgments)
        else:
            anchor_effect = 0.0

        return HeuristicMetrics(
            representativeness_usage=rep_count / total,
            availability_usage=avail_count / total,
            anchoring_effect=anchor_effect,
            bias_rate=bias_count / total
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'prototypes': len(self._representativeness._prototypes),
            'memory_instances': len(self._availability._memory),
            'judgments': len(self._judgments),
            'biases_observed': sum(len(j.biases_present) for j in self._judgments)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_judgment_heuristics_engine() -> JudgmentHeuristicsEngine:
    """Create judgment heuristics engine."""
    return JudgmentHeuristicsEngine()


def demonstrate_judgment_heuristics() -> Dict[str, Any]:
    """Demonstrate judgment heuristics."""
    engine = create_judgment_heuristics_engine()

    # Representativeness: Linda problem
    linda = engine.demonstrate_linda_problem()

    # Availability bias
    avail = engine.demonstrate_availability_effect()

    # Anchoring
    anchor = engine.demonstrate_anchoring_effect()

    metrics = engine.get_metrics()

    return {
        'representativeness': {
            'linda_problem': linda['fallacy_present'],
            'conjunction_judged_higher': linda['conjunction_probability'] > linda['broad_probability']
        },
        'availability': {
            'bias_present': avail['bias_present'],
            'vivid_category_overestimated': avail['judged_freq_a'] > avail['judged_freq_b']
        },
        'anchoring': {
            'effect_magnitude': anchor['anchoring_effect'],
            'insufficient_adjustment': anchor['insufficient_adjustment']
        },
        'interpretation': (
            f"Conjunction fallacy: {linda['fallacy_present']}, "
            f"Availability bias: {avail['bias_present']}, "
            f"Anchoring effect: {anchor['anchoring_effect']:.1f}"
        )
    }


def get_judgment_heuristics_facts() -> Dict[str, str]:
    """Get facts about judgment heuristics."""
    return {
        'kahneman_tversky': 'Pioneering research on heuristics and biases',
        'representativeness': 'Judge probability by similarity to prototype',
        'availability': 'Judge frequency by ease of retrieval',
        'anchoring': 'Insufficient adjustment from initial value',
        'base_rate_neglect': 'Ignoring prior probabilities',
        'conjunction_fallacy': 'Specific combination judged more likely than general',
        'affect_heuristic': 'Feelings guide judgments',
        'system_1_2': 'Fast intuitive vs slow deliberate thinking'
    }
