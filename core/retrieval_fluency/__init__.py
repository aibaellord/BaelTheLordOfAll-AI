"""
BAEL Retrieval Fluency Engine
===============================

Processing ease as memory signal.
Jacoby's fluency-attribution framework.

"Ba'el feels the flow of memory." — Ba'el
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

logger = logging.getLogger("BAEL.RetrievalFluency")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class FluencyType(Enum):
    """Type of fluency."""
    PERCEPTUAL = auto()       # Visual clarity
    CONCEPTUAL = auto()       # Semantic ease
    RETRIEVAL = auto()        # Memory accessibility
    PRODUCTION = auto()       # Response generation


class FluencySource(Enum):
    """Source of fluency."""
    PRIOR_EXPOSURE = auto()   # Studied before
    PRIMING = auto()          # Recent activation
    FAMILIARITY = auto()      # General familiarity
    CLARITY = auto()          # Physical clarity
    FREQUENCY = auto()        # Word frequency


class AttributionTarget(Enum):
    """Target of fluency attribution."""
    MEMORY = auto()           # "I remember this"
    LIKING = auto()           # "I like this"
    TRUTH = auto()            # "This is true"
    FAME = auto()             # "This person is famous"
    CONFIDENCE = auto()       # "I'm confident"


class JudgmentType(Enum):
    """Type of judgment."""
    OLD_NEW = auto()          # Recognition
    FAMILIARITY = auto()      # Feeling of knowing
    TRUTH = auto()            # Illusory truth
    PREFERENCE = auto()       # Mere exposure


@dataclass
class Stimulus:
    """
    A stimulus to be processed.
    """
    id: str
    content: str
    perceptual_fluency: float
    conceptual_fluency: float
    frequency: float


@dataclass
class FluencySignal:
    """
    A fluency signal.
    """
    stimulus: Stimulus
    fluency_type: FluencyType
    magnitude: float
    source: FluencySource
    attributed_to: AttributionTarget


@dataclass
class JudgmentResponse:
    """
    A judgment based on fluency.
    """
    stimulus: Stimulus
    judgment_type: JudgmentType
    response: float           # 0-1 scale
    fluency_contribution: float
    correct: Optional[bool]


@dataclass
class FluencyMetrics:
    """
    Fluency metrics.
    """
    mean_fluency: float
    fluency_attribution_rate: float
    misattribution_rate: float
    by_judgment: Dict[str, float]


# ============================================================================
# RETRIEVAL FLUENCY MODEL
# ============================================================================

class RetrievalFluencyModel:
    """
    Model of retrieval fluency and attribution.

    "Ba'el's fluency model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base fluency levels
        self._base_perceptual = 0.5
        self._base_conceptual = 0.5
        self._base_retrieval = 0.3

        # Prior exposure effects
        self._exposure_boost = 0.25
        self._repetition_boost = 0.10  # Per repetition
        self._recency_boost = 0.15

        # Clarity manipulation
        self._clarity_effect = 0.20    # Clear vs degraded

        # Attribution weights
        self._attribution_weights = {
            AttributionTarget.MEMORY: 0.7,
            AttributionTarget.LIKING: 0.3,
            AttributionTarget.TRUTH: 0.4,
            AttributionTarget.FAME: 0.3,
            AttributionTarget.CONFIDENCE: 0.5
        }

        # Awareness reduces misattribution
        self._source_awareness = 0.0

        # Judgment thresholds
        self._old_new_threshold = 0.5
        self._truth_threshold = 0.5

        self._lock = threading.RLock()

    def calculate_perceptual_fluency(
        self,
        stimulus: Stimulus,
        clarity: float = 1.0,
        repetitions: int = 0
    ) -> float:
        """Calculate perceptual fluency."""
        fluency = self._base_perceptual

        # Inherent fluency
        fluency += stimulus.perceptual_fluency * 0.2

        # Clarity manipulation
        fluency += (clarity - 0.5) * self._clarity_effect

        # Repetition priming
        fluency += min(repetitions * self._repetition_boost, 0.30)

        return max(0.1, min(0.95, fluency))

    def calculate_conceptual_fluency(
        self,
        stimulus: Stimulus,
        semantic_context: bool = False
    ) -> float:
        """Calculate conceptual fluency."""
        fluency = self._base_conceptual

        # Inherent fluency
        fluency += stimulus.conceptual_fluency * 0.2

        # Semantic context
        if semantic_context:
            fluency += 0.10

        # Word frequency
        fluency += (stimulus.frequency - 0.5) * 0.15

        return max(0.1, min(0.95, fluency))

    def calculate_retrieval_fluency(
        self,
        stimulus: Stimulus,
        prior_exposure: bool = False,
        exposure_recency: float = 0.0
    ) -> float:
        """Calculate retrieval fluency."""
        fluency = self._base_retrieval

        # Prior exposure
        if prior_exposure:
            fluency += self._exposure_boost

            # Recency boost (0-1, recent=1)
            fluency += exposure_recency * self._recency_boost

        return max(0.1, min(0.95, fluency))

    def attribute_fluency(
        self,
        fluency: float,
        target: AttributionTarget,
        source_identified: bool = False
    ) -> float:
        """Attribute fluency to target."""
        # Weight for this attribution
        weight = self._attribution_weights[target]

        # Source awareness reduces misattribution
        if source_identified:
            weight *= (1 - self._source_awareness)

        # Attribution = fluency * weight
        attribution = fluency * weight

        return max(0.1, min(0.95, attribution))

    def make_judgment(
        self,
        fluency: float,
        judgment_type: JudgmentType,
        actual_old: bool = False
    ) -> JudgmentResponse:
        """Make judgment based on fluency."""
        threshold = self._old_new_threshold

        # Add noise
        signal = fluency + random.uniform(-0.15, 0.15)

        response = min(1.0, max(0.0, signal))

        # Determine correctness
        if judgment_type == JudgmentType.OLD_NEW:
            responded_old = response > threshold
            correct = (responded_old == actual_old)
        else:
            correct = None

        return JudgmentResponse(
            stimulus=None,
            judgment_type=judgment_type,
            response=response,
            fluency_contribution=fluency,
            correct=correct
        )


# ============================================================================
# RETRIEVAL FLUENCY SYSTEM
# ============================================================================

class RetrievalFluencySystem:
    """
    Retrieval fluency simulation system.

    "Ba'el's fluency system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = RetrievalFluencyModel()

        self._stimuli: Dict[str, Stimulus] = {}
        self._exposures: Dict[str, int] = defaultdict(int)
        self._signals: List[FluencySignal] = []
        self._responses: List[JudgmentResponse] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"stim_{self._counter}"

    def create_stimulus(
        self,
        content: str,
        perceptual_fluency: float = 0.5,
        conceptual_fluency: float = 0.5,
        frequency: float = 0.5
    ) -> Stimulus:
        """Create stimulus."""
        stim = Stimulus(
            id=self._generate_id(),
            content=content,
            perceptual_fluency=perceptual_fluency,
            conceptual_fluency=conceptual_fluency,
            frequency=frequency
        )

        self._stimuli[stim.id] = stim

        return stim

    def expose(
        self,
        stimulus_id: str
    ) -> int:
        """Expose to stimulus."""
        self._exposures[stimulus_id] += 1
        return self._exposures[stimulus_id]

    def measure_fluency(
        self,
        stimulus_id: str,
        fluency_type: FluencyType,
        clarity: float = 1.0
    ) -> FluencySignal:
        """Measure fluency."""
        stim = self._stimuli.get(stimulus_id)
        if not stim:
            return None

        exposures = self._exposures[stimulus_id]
        prior_exposure = exposures > 0

        if fluency_type == FluencyType.PERCEPTUAL:
            magnitude = self._model.calculate_perceptual_fluency(
                stim, clarity, exposures
            )
            source = FluencySource.CLARITY if clarity != 1.0 else FluencySource.PRIOR_EXPOSURE

        elif fluency_type == FluencyType.CONCEPTUAL:
            magnitude = self._model.calculate_conceptual_fluency(stim)
            source = FluencySource.FAMILIARITY

        else:  # RETRIEVAL
            magnitude = self._model.calculate_retrieval_fluency(
                stim, prior_exposure
            )
            source = FluencySource.PRIOR_EXPOSURE if prior_exposure else FluencySource.FAMILIARITY

        signal = FluencySignal(
            stimulus=stim,
            fluency_type=fluency_type,
            magnitude=magnitude,
            source=source,
            attributed_to=AttributionTarget.MEMORY
        )

        self._signals.append(signal)

        return signal

    def make_judgment(
        self,
        stimulus_id: str,
        judgment_type: JudgmentType
    ) -> JudgmentResponse:
        """Make judgment about stimulus."""
        stim = self._stimuli.get(stimulus_id)
        if not stim:
            return None

        # Calculate fluency
        exposures = self._exposures[stimulus_id]
        fluency = self._model.calculate_retrieval_fluency(
            stim, exposures > 0
        )

        response = self._model.make_judgment(
            fluency, judgment_type, exposures > 0
        )
        response.stimulus = stim

        self._responses.append(response)

        return response


# ============================================================================
# RETRIEVAL FLUENCY PARADIGM
# ============================================================================

class RetrievalFluencyParadigm:
    """
    Retrieval fluency paradigm.

    "Ba'el's fluency study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_repetition_paradigm(
        self,
        n_items: int = 40
    ) -> Dict[str, Any]:
        """Run repetition-fluency paradigm."""
        system = RetrievalFluencySystem()

        # Create stimuli
        words = [f"word_{i}" for i in range(n_items)]
        stimuli = []

        for word in words:
            stim = system.create_stimulus(word)
            stimuli.append(stim)

        # Half get repeated
        repeated = stimuli[:n_items // 2]
        new = stimuli[n_items // 2:]

        for stim in repeated:
            system.expose(stim.id)

        # Test all
        responses = []

        for stim in repeated:
            resp = system.make_judgment(stim.id, JudgmentType.OLD_NEW)
            responses.append(resp)

        for stim in new:
            resp = system.make_judgment(stim.id, JudgmentType.OLD_NEW)
            responses.append(resp)

        # Calculate
        repeated_mean = sum(r.fluency_contribution for r in responses[:n_items // 2]) / (n_items // 2)
        new_mean = sum(r.fluency_contribution for r in responses[n_items // 2:]) / (n_items // 2)

        return {
            'repeated_fluency': repeated_mean,
            'new_fluency': new_mean,
            'fluency_difference': repeated_mean - new_mean,
            'interpretation': 'Repetition increases fluency'
        }

    def run_clarity_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run clarity manipulation paradigm."""
        model = RetrievalFluencyModel()

        stim = Stimulus(
            id="test", content="test",
            perceptual_fluency=0.5, conceptual_fluency=0.5, frequency=0.5
        )

        conditions = {
            'clear': 1.0,
            'degraded': 0.5
        }

        results = {}

        for condition, clarity in conditions.items():
            fluency = model.calculate_perceptual_fluency(stim, clarity)
            results[condition] = {'fluency': fluency}

        effect = results['clear']['fluency'] - results['degraded']['fluency']

        return {
            'by_clarity': results,
            'clarity_effect': effect,
            'interpretation': 'Clear = more fluent = feels familiar'
        }

    def run_mere_exposure_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run mere exposure effect paradigm."""
        model = RetrievalFluencyModel()

        stim = Stimulus(
            id="test", content="test",
            perceptual_fluency=0.5, conceptual_fluency=0.5, frequency=0.5
        )

        # Different exposure levels
        exposure_levels = [0, 1, 3, 5, 10]

        results = {}

        for exposures in exposure_levels:
            fluency = model.calculate_perceptual_fluency(stim, repetitions=exposures)
            liking = model.attribute_fluency(fluency, AttributionTarget.LIKING)

            results[f'{exposures}_exposures'] = {
                'fluency': fluency,
                'liking': liking
            }

        return {
            'by_exposure': results,
            'interpretation': 'More exposure = more fluency = more liking'
        }

    def run_illusory_truth_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run illusory truth effect paradigm."""
        model = RetrievalFluencyModel()

        conditions = {
            'new_statement': {'prior_exposure': False},
            'repeated_statement': {'prior_exposure': True}
        }

        stim = Stimulus(
            id="test", content="test",
            perceptual_fluency=0.5, conceptual_fluency=0.5, frequency=0.5
        )

        results = {}

        for condition, params in conditions.items():
            fluency = model.calculate_retrieval_fluency(stim, params['prior_exposure'])
            truth = model.attribute_fluency(fluency, AttributionTarget.TRUTH)

            results[condition] = {
                'fluency': fluency,
                'judged_truth': truth
            }

        effect = results['repeated_statement']['judged_truth'] - results['new_statement']['judged_truth']

        return {
            'by_repetition': results,
            'illusory_truth_effect': effect,
            'interpretation': 'Repetition = fluency = feels more true'
        }

    def run_fame_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run false fame paradigm."""
        # Overnight fame: seeing name before makes it seem famous
        conditions = {
            'new_name': {'prior_exposure': False, 'source_recall': True},
            'old_name_source_remembered': {'prior_exposure': True, 'source_recall': True},
            'old_name_source_forgotten': {'prior_exposure': True, 'source_recall': False}
        }

        model = RetrievalFluencyModel()

        stim = Stimulus(
            id="test", content="test",
            perceptual_fluency=0.5, conceptual_fluency=0.5, frequency=0.5
        )

        results = {}

        for condition, params in conditions.items():
            fluency = model.calculate_retrieval_fluency(stim, params['prior_exposure'])

            # If source remembered, don't misattribute
            if params['prior_exposure'] and params['source_recall']:
                fame = fluency * 0.3  # Discount
            else:
                fame = model.attribute_fluency(fluency, AttributionTarget.FAME)

            results[condition] = {
                'fluency': fluency,
                'judged_fame': fame
            }

        return {
            'by_condition': results,
            'interpretation': 'Forgotten exposure = fluency = seems famous'
        }

    def run_attribution_awareness_study(
        self
    ) -> Dict[str, Any]:
        """Study awareness of fluency source."""
        model = RetrievalFluencyModel()

        conditions = {
            'source_unknown': False,
            'source_identified': True
        }

        fluency = 0.7

        results = {}

        for condition, identified in conditions.items():
            # Test attributions
            memory = model.attribute_fluency(fluency, AttributionTarget.MEMORY, identified)
            liking = model.attribute_fluency(fluency, AttributionTarget.LIKING, identified)
            truth = model.attribute_fluency(fluency, AttributionTarget.TRUTH, identified)

            results[condition] = {
                'memory': memory,
                'liking': liking,
                'truth': truth
            }

        return {
            'by_awareness': results,
            'interpretation': 'Knowing source reduces misattribution'
        }


# ============================================================================
# RETRIEVAL FLUENCY ENGINE
# ============================================================================

class RetrievalFluencyEngine:
    """
    Complete retrieval fluency engine.

    "Ba'el's fluency engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = RetrievalFluencyParadigm()
        self._system = RetrievalFluencySystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Stimulus operations

    def create_stimulus(
        self,
        content: str
    ) -> Stimulus:
        """Create stimulus."""
        return self._system.create_stimulus(content)

    def expose(
        self,
        stimulus_id: str
    ) -> int:
        """Expose to stimulus."""
        return self._system.expose(stimulus_id)

    def measure_fluency(
        self,
        stimulus_id: str,
        fluency_type: FluencyType = FluencyType.RETRIEVAL
    ) -> FluencySignal:
        """Measure fluency."""
        return self._system.measure_fluency(stimulus_id, fluency_type)

    def make_judgment(
        self,
        stimulus_id: str,
        judgment_type: JudgmentType = JudgmentType.OLD_NEW
    ) -> JudgmentResponse:
        """Make judgment."""
        return self._system.make_judgment(stimulus_id, judgment_type)

    # Experiments

    def run_repetition(
        self
    ) -> Dict[str, Any]:
        """Run repetition paradigm."""
        result = self._paradigm.run_repetition_paradigm()
        self._experiment_results.append(result)
        return result

    def run_clarity(
        self
    ) -> Dict[str, Any]:
        """Run clarity paradigm."""
        return self._paradigm.run_clarity_paradigm()

    def run_mere_exposure(
        self
    ) -> Dict[str, Any]:
        """Run mere exposure."""
        return self._paradigm.run_mere_exposure_paradigm()

    def run_illusory_truth(
        self
    ) -> Dict[str, Any]:
        """Run illusory truth."""
        return self._paradigm.run_illusory_truth_paradigm()

    def run_false_fame(
        self
    ) -> Dict[str, Any]:
        """Run false fame."""
        return self._paradigm.run_fame_paradigm()

    def study_attribution(
        self
    ) -> Dict[str, Any]:
        """Study attribution awareness."""
        return self._paradigm.run_attribution_awareness_study()

    # Analysis

    def get_metrics(self) -> FluencyMetrics:
        """Get metrics."""
        signals = self._system._signals

        if not signals:
            return FluencyMetrics(
                mean_fluency=0.5,
                fluency_attribution_rate=0.5,
                misattribution_rate=0.2,
                by_judgment={}
            )

        mean_fluency = sum(s.magnitude for s in signals) / len(signals)

        return FluencyMetrics(
            mean_fluency=mean_fluency,
            fluency_attribution_rate=0.7,
            misattribution_rate=0.2,
            by_judgment={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'stimuli': len(self._system._stimuli),
            'signals': len(self._system._signals),
            'responses': len(self._system._responses)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_retrieval_fluency_engine() -> RetrievalFluencyEngine:
    """Create retrieval fluency engine."""
    return RetrievalFluencyEngine()


def demonstrate_retrieval_fluency() -> Dict[str, Any]:
    """Demonstrate retrieval fluency."""
    engine = create_retrieval_fluency_engine()

    # Repetition
    repetition = engine.run_repetition()

    # Clarity
    clarity = engine.run_clarity()

    # Mere exposure
    mere_exposure = engine.run_mere_exposure()

    # Illusory truth
    truth = engine.run_illusory_truth()

    return {
        'repetition_effect': {
            'repeated': f"{repetition['repeated_fluency']:.2f}",
            'new': f"{repetition['new_fluency']:.2f}",
            'difference': f"{repetition['fluency_difference']:.2f}"
        },
        'clarity_effect': clarity['clarity_effect'],
        'mere_exposure': {
            k: f"liking: {v['liking']:.2f}"
            for k, v in mere_exposure['by_exposure'].items()
        },
        'illusory_truth': {
            'new': f"{truth['by_repetition']['new_statement']['judged_truth']:.2f}",
            'repeated': f"{truth['by_repetition']['repeated_statement']['judged_truth']:.2f}",
            'effect': f"{truth['illusory_truth_effect']:.2f}"
        },
        'interpretation': (
            f"Fluency ({repetition['repeated_fluency']:.2f}) signals familiarity. "
            f"Misattributed to memory, liking, truth, fame."
        )
    }


def get_retrieval_fluency_facts() -> Dict[str, str]:
    """Get facts about retrieval fluency."""
    return {
        'jacoby_1989': 'Fluency attribution framework',
        'mechanism': 'Processing ease signals familiarity',
        'mere_exposure': 'Fluency = liking (Zajonc)',
        'illusory_truth': 'Fluency = truth (Hasher)',
        'false_fame': 'Fluency = fame (Jacoby)',
        'awareness': 'Knowing source reduces misattribution',
        'perceptual': 'Clarity manipulation',
        'applications': 'Marketing, persuasion, interface design'
    }
