"""
BAEL Hindsight Bias Engine
============================

"I knew it all along" effect.
Retrospective distortion of predictions.

"Ba'el always knew." — Ba'el
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

logger = logging.getLogger("BAEL.HindsightBias")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class OutcomeType(Enum):
    """Types of outcomes."""
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()
    UNEXPECTED = auto()


class ConfidenceLevel(Enum):
    """Confidence levels."""
    VERY_LOW = 1
    LOW = 2
    SOMEWHAT_LOW = 3
    MODERATE = 4
    SOMEWHAT_HIGH = 5
    HIGH = 6
    VERY_HIGH = 7


class BiasType(Enum):
    """Types of hindsight bias."""
    MEMORY_DISTORTION = auto()  # Misremember original prediction
    INEVITABILITY = auto()       # "It had to happen"
    FORESEEABILITY = auto()      # "I should have known"


@dataclass
class Prediction:
    """
    An original prediction.
    """
    id: str
    event_description: str
    predicted_outcome: str
    confidence: ConfidenceLevel
    timestamp: float


@dataclass
class Outcome:
    """
    An actual outcome.
    """
    prediction_id: str
    actual_outcome: str
    outcome_type: OutcomeType
    surprise_level: float  # 0-1


@dataclass
class RecalledPrediction:
    """
    A recalled prediction (potentially distorted).
    """
    prediction_id: str
    recalled_confidence: ConfidenceLevel
    original_confidence: ConfidenceLevel
    confidence_shift: int
    recalled_outcome: str
    memory_distortion: bool


@dataclass
class HindsightBiasMetrics:
    """
    Hindsight bias metrics.
    """
    mean_confidence_shift: float
    memory_distortion_rate: float
    inevitability_judgment: float
    foreseeability_judgment: float


# ============================================================================
# MEMORY RECONSTRUCTION
# ============================================================================

class MemoryReconstructor:
    """
    Memory reconstruction system.

    "Ba'el's memory editor." — Ba'el
    """

    def __init__(self):
        """Initialize reconstructor."""
        # Reconstruction parameters
        self._outcome_influence = 0.4
        self._confidence_drift = 0.2

        self._lock = threading.RLock()

    def reconstruct_prediction(
        self,
        original: Prediction,
        outcome: Outcome
    ) -> RecalledPrediction:
        """Reconstruct memory of prediction after knowing outcome."""
        # Original confidence
        orig_conf = original.confidence.value

        # Outcome-congruent shift
        if outcome.outcome_type == OutcomeType.POSITIVE:
            shift_direction = 1  # Shift toward "I predicted success"
        elif outcome.outcome_type == OutcomeType.NEGATIVE:
            shift_direction = -1  # Shift toward "I predicted failure"
        else:
            shift_direction = 0

        # Calculate shift magnitude
        shift_magnitude = self._outcome_influence * (7 - abs(orig_conf - 4))
        shift = int(shift_direction * shift_magnitude * random.uniform(0.5, 1.5))

        # Apply shift
        new_conf_val = orig_conf + shift
        new_conf_val = max(1, min(7, new_conf_val))

        # Memory distortion check
        distortion = abs(shift) > 0

        # Recall the outcome as if predicted
        recalled_outcome = outcome.actual_outcome if distortion else original.predicted_outcome

        return RecalledPrediction(
            prediction_id=original.id,
            recalled_confidence=ConfidenceLevel(new_conf_val),
            original_confidence=original.confidence,
            confidence_shift=shift,
            recalled_outcome=recalled_outcome,
            memory_distortion=distortion
        )


# ============================================================================
# INEVITABILITY MODEL
# ============================================================================

class InevitabilityModel:
    """
    Model of inevitability judgments.

    "Ba'el's fatalism engine." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._base_inevitability = 0.5
        self._outcome_boost = 0.3

        self._lock = threading.RLock()

    def judge_inevitability(
        self,
        outcome: Outcome,
        original_prediction: Prediction
    ) -> float:
        """Judge how inevitable the outcome seems in hindsight."""
        # Base inevitability
        inevitability = self._base_inevitability

        # Outcome knowledge increases inevitability
        inevitability += self._outcome_boost

        # Low surprise increases inevitability
        inevitability += (1 - outcome.surprise_level) * 0.2

        # Add noise
        inevitability += random.gauss(0, 0.1)

        return max(0, min(1, inevitability))

    def judge_foreseeability(
        self,
        outcome: Outcome
    ) -> float:
        """Judge how foreseeable the outcome was."""
        # Higher for less surprising outcomes
        foreseeability = 1 - outcome.surprise_level * 0.6

        # Add hindsight boost
        foreseeability += 0.2

        # Add noise
        foreseeability += random.gauss(0, 0.1)

        return max(0, min(1, foreseeability))


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class HindsightParadigm:
    """
    Hindsight bias experimental paradigm.

    "Ba'el's 'knew it all along' test." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._reconstructor = MemoryReconstructor()
        self._inevitability = InevitabilityModel()

        self._predictions: Dict[str, Prediction] = {}
        self._outcomes: Dict[str, Outcome] = {}
        self._recalls: List[RecalledPrediction] = []

        self._pred_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._pred_counter += 1
        return f"pred_{self._pred_counter}"

    def make_prediction(
        self,
        event: str,
        predicted_outcome: str,
        confidence: ConfidenceLevel
    ) -> Prediction:
        """Make a prediction about an event."""
        pred = Prediction(
            id=self._generate_id(),
            event_description=event,
            predicted_outcome=predicted_outcome,
            confidence=confidence,
            timestamp=time.time()
        )

        self._predictions[pred.id] = pred
        return pred

    def provide_outcome(
        self,
        prediction_id: str,
        actual_outcome: str,
        outcome_type: OutcomeType,
        surprise: float = 0.5
    ) -> Outcome:
        """Provide the actual outcome."""
        outcome = Outcome(
            prediction_id=prediction_id,
            actual_outcome=actual_outcome,
            outcome_type=outcome_type,
            surprise_level=surprise
        )

        self._outcomes[prediction_id] = outcome
        return outcome

    def recall_prediction(
        self,
        prediction_id: str
    ) -> Optional[RecalledPrediction]:
        """Recall original prediction (after knowing outcome)."""
        pred = self._predictions.get(prediction_id)
        outcome = self._outcomes.get(prediction_id)

        if not pred or not outcome:
            return None

        recall = self._reconstructor.reconstruct_prediction(pred, outcome)
        self._recalls.append(recall)

        return recall

    def run_experiment(
        self,
        n_predictions: int = 20
    ) -> Dict[str, Any]:
        """Run hindsight bias experiment."""
        # Phase 1: Make predictions
        events = [f"event_{i}" for i in range(n_predictions)]

        for event in events:
            # Random initial confidence
            conf = ConfidenceLevel(random.randint(2, 6))
            self.make_prediction(event, f"outcome_{event}", conf)

        # Phase 2: Provide outcomes
        for pred_id in list(self._predictions.keys()):
            outcome_type = random.choice([
                OutcomeType.POSITIVE,
                OutcomeType.NEGATIVE,
                OutcomeType.NEUTRAL
            ])
            surprise = random.uniform(0.2, 0.8)

            self.provide_outcome(
                pred_id,
                f"actual_{pred_id}",
                outcome_type,
                surprise
            )

        # Phase 3: Recall predictions
        for pred_id in list(self._predictions.keys()):
            self.recall_prediction(pred_id)

        # Calculate bias metrics
        total_shift = 0
        distortions = 0
        inevitability_sum = 0
        foreseeability_sum = 0

        for recall in self._recalls:
            total_shift += abs(recall.confidence_shift)
            if recall.memory_distortion:
                distortions += 1

            pred = self._predictions[recall.prediction_id]
            outcome = self._outcomes[recall.prediction_id]

            inevitability_sum += self._inevitability.judge_inevitability(outcome, pred)
            foreseeability_sum += self._inevitability.judge_foreseeability(outcome)

        n = len(self._recalls)

        return {
            'n_predictions': n_predictions,
            'mean_confidence_shift': total_shift / n if n > 0 else 0,
            'distortion_rate': distortions / n if n > 0 else 0,
            'mean_inevitability': inevitability_sum / n if n > 0 else 0,
            'mean_foreseeability': foreseeability_sum / n if n > 0 else 0
        }


# ============================================================================
# HINDSIGHT BIAS ENGINE
# ============================================================================

class HindsightBiasEngine:
    """
    Complete hindsight bias engine.

    "Ba'el's retrospective certainty." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = HindsightParadigm()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Prediction making

    def predict(
        self,
        event: str,
        outcome: str,
        confidence: ConfidenceLevel
    ) -> Prediction:
        """Make a prediction."""
        return self._paradigm.make_prediction(event, outcome, confidence)

    # Outcome provision

    def provide_outcome(
        self,
        prediction_id: str,
        outcome: str,
        outcome_type: OutcomeType,
        surprise: float = 0.5
    ) -> Outcome:
        """Provide actual outcome."""
        return self._paradigm.provide_outcome(prediction_id, outcome, outcome_type, surprise)

    # Recall

    def recall(
        self,
        prediction_id: str
    ) -> Optional[RecalledPrediction]:
        """Recall original prediction."""
        return self._paradigm.recall_prediction(prediction_id)

    # Experiments

    def run_hindsight_experiment(
        self,
        n_predictions: int = 25
    ) -> Dict[str, Any]:
        """Run hindsight bias experiment."""
        # Reset paradigm
        self._paradigm = HindsightParadigm()
        result = self._paradigm.run_experiment(n_predictions)
        self._experiment_results.append(result)
        return result

    def run_outcome_type_comparison(
        self,
        n_per_type: int = 10
    ) -> Dict[str, Any]:
        """Compare bias across outcome types."""
        results = {}

        for outcome_type in [OutcomeType.POSITIVE, OutcomeType.NEGATIVE]:
            # Fresh paradigm
            paradigm = HindsightParadigm()

            shifts = []
            for i in range(n_per_type):
                pred = paradigm.make_prediction(
                    f"{outcome_type.name}_{i}",
                    f"predicted_{i}",
                    ConfidenceLevel.MODERATE
                )

                paradigm.provide_outcome(
                    pred.id,
                    f"actual_{i}",
                    outcome_type,
                    surprise=0.5
                )

                recall = paradigm.recall_prediction(pred.id)
                if recall:
                    shifts.append(recall.confidence_shift)

            results[outcome_type.name] = {
                'mean_shift': sum(shifts) / len(shifts) if shifts else 0,
                'n': len(shifts)
            }

        return results

    def run_surprise_comparison(
        self,
        n_per_level: int = 10
    ) -> Dict[str, Any]:
        """Compare bias across surprise levels."""
        results = {}

        for surprise in [0.2, 0.5, 0.8]:
            paradigm = HindsightParadigm()

            inevitabilities = []
            for i in range(n_per_level):
                pred = paradigm.make_prediction(
                    f"surprise_{surprise}_{i}",
                    f"predicted_{i}",
                    ConfidenceLevel.MODERATE
                )

                outcome = paradigm.provide_outcome(
                    pred.id,
                    f"actual_{i}",
                    OutcomeType.POSITIVE,
                    surprise=surprise
                )

                inevit = paradigm._inevitability.judge_inevitability(outcome, pred)
                inevitabilities.append(inevit)

            results[f"surprise_{surprise}"] = {
                'mean_inevitability': sum(inevitabilities) / len(inevitabilities) if inevitabilities else 0
            }

        return results

    # Analysis

    def get_metrics(self) -> HindsightBiasMetrics:
        """Get hindsight bias metrics."""
        if not self._experiment_results:
            self.run_hindsight_experiment(20)

        last = self._experiment_results[-1]

        return HindsightBiasMetrics(
            mean_confidence_shift=last['mean_confidence_shift'],
            memory_distortion_rate=last['distortion_rate'],
            inevitability_judgment=last['mean_inevitability'],
            foreseeability_judgment=last['mean_foreseeability']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'predictions': len(self._paradigm._predictions),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_hindsight_bias_engine() -> HindsightBiasEngine:
    """Create hindsight bias engine."""
    return HindsightBiasEngine()


def demonstrate_hindsight_bias() -> Dict[str, Any]:
    """Demonstrate hindsight bias."""
    engine = create_hindsight_bias_engine()

    # Basic experiment
    basic = engine.run_hindsight_experiment(25)

    # Outcome type comparison
    outcomes = engine.run_outcome_type_comparison(15)

    # Surprise comparison
    surprise = engine.run_surprise_comparison(10)

    return {
        'hindsight_bias': {
            'mean_confidence_shift': f"{basic['mean_confidence_shift']:.1f} levels",
            'memory_distortion': f"{basic['distortion_rate']:.0%}",
            'inevitability': f"{basic['mean_inevitability']:.0%}",
            'foreseeability': f"{basic['mean_foreseeability']:.0%}"
        },
        'outcome_types': {
            otype: f"shift: {data['mean_shift']:.1f}"
            for otype, data in outcomes.items()
        },
        'surprise_effect': {
            level: f"inevitability: {data['mean_inevitability']:.0%}"
            for level, data in surprise.items()
        },
        'interpretation': (
            f"Hindsight bias: {basic['mean_confidence_shift']:.1f} level shift. "
            f"People overestimate what they 'knew all along'."
        )
    }


def get_hindsight_bias_facts() -> Dict[str, str]:
    """Get facts about hindsight bias."""
    return {
        'fischhoff_1975': 'Original demonstration of hindsight bias',
        'knew_it_all_along': 'Classic formulation of the effect',
        'memory_distortion': 'People misremember their original predictions',
        'inevitability': 'Outcomes seem more inevitable in hindsight',
        'foreseeability': 'Outcomes seem more foreseeable in hindsight',
        'decision_making': 'Can impair learning from outcomes',
        'legal_implications': 'Affects negligence judgments',
        'debiasing': 'Consider alternatives before learning outcome'
    }
