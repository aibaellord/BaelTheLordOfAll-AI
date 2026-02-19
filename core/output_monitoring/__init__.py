"""
BAEL Output Monitoring Engine
===============================

Monitoring own responses during retrieval.
Koriat's output monitoring framework.

"Ba'el watches what the mind produces." — Ba'el
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

logger = logging.getLogger("BAEL.OutputMonitoring")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MonitoringStage(Enum):
    """Stage of monitoring."""
    PRE_RETRIEVAL = auto()    # Before responding
    OUTPUT_BOUND = auto()     # During response
    POST_OUTPUT = auto()      # After responding


class ResponseType(Enum):
    """Type of response."""
    CORRECT = auto()
    INTRUSION = auto()        # Wrong but related
    CONFABULATION = auto()    # Wrong and unrelated
    WITHHOLD = auto()         # No response


class CriterionType(Enum):
    """Type of monitoring criterion."""
    STRICT = auto()           # High threshold
    MODERATE = auto()
    LIBERAL = auto()          # Low threshold


class ConfidenceSource(Enum):
    """Source of confidence."""
    FLUENCY = auto()          # Retrieval ease
    FAMILIARITY = auto()      # Recognition signal
    RECOLLECTION = auto()     # Specific details
    PLAUSIBILITY = auto()     # Makes sense


@dataclass
class RetrievalAttempt:
    """
    A retrieval attempt.
    """
    id: str
    query: str
    candidate_response: str
    is_correct: bool
    confidence: float
    fluency: float


@dataclass
class MonitoringDecision:
    """
    A monitoring decision.
    """
    attempt: RetrievalAttempt
    stage: MonitoringStage
    criterion: CriterionType
    decision: str           # "output" or "withhold"
    final_response: Optional[str]


@dataclass
class OutputResult:
    """
    Result of output.
    """
    response_type: ResponseType
    confidence: float
    calibration: float      # Accuracy of confidence


@dataclass
class MonitoringMetrics:
    """
    Output monitoring metrics.
    """
    accuracy: float
    intrusion_rate: float
    withhold_rate: float
    calibration: float
    by_criterion: Dict[str, float]


# ============================================================================
# OUTPUT MONITORING MODEL
# ============================================================================

class OutputMonitoringModel:
    """
    Model of output monitoring.

    "Ba'el's monitoring model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base confidence for correct items
        self._correct_confidence = 0.75

        # Base confidence for errors
        self._error_confidence = 0.45

        # Monitoring thresholds
        self._thresholds = {
            CriterionType.STRICT: 0.70,
            CriterionType.MODERATE: 0.50,
            CriterionType.LIBERAL: 0.30
        }

        # Fluency-confidence relationship
        self._fluency_weight = 0.30

        # Familiarity contribution
        self._familiarity_weight = 0.25

        # Plausibility check
        self._plausibility_weight = 0.20

        # Recollection contribution
        self._recollection_weight = 0.25

        # Intrusion characteristics
        self._intrusion_confidence = 0.50
        self._intrusion_fluency = 0.55

        # Age effects
        self._young_monitoring = 1.0
        self._older_monitoring = 0.75

        self._lock = threading.RLock()

    def calculate_confidence(
        self,
        is_correct: bool,
        fluency: float,
        familiarity: float = 0.5,
        plausibility: float = 0.5,
        recollection: float = 0.5
    ) -> float:
        """Calculate response confidence."""
        if is_correct:
            base = self._correct_confidence
        else:
            base = self._error_confidence

        # Cue weights
        adjustment = (
            fluency * self._fluency_weight +
            familiarity * self._familiarity_weight +
            plausibility * self._plausibility_weight +
            recollection * self._recollection_weight
        )

        # Normalize adjustment to center at 0
        adjustment = (adjustment - 0.325) * 0.5

        confidence = base + adjustment

        # Add noise
        confidence += random.uniform(-0.1, 0.1)

        return max(0.1, min(0.95, confidence))

    def should_output(
        self,
        confidence: float,
        criterion: CriterionType
    ) -> bool:
        """Decide whether to output response."""
        threshold = self._thresholds[criterion]
        return confidence >= threshold

    def calculate_calibration(
        self,
        confidences: List[float],
        accuracies: List[bool]
    ) -> float:
        """Calculate confidence-accuracy calibration."""
        if not confidences or not accuracies:
            return 0.5

        # Bin confidences and calculate accuracy per bin
        bins = defaultdict(list)

        for conf, acc in zip(confidences, accuracies):
            bin_idx = int(conf * 10) / 10
            bins[bin_idx].append(acc)

        # Calculate mean absolute error
        total_error = 0
        n_bins = 0

        for bin_center, accs in bins.items():
            expected = bin_center
            actual = sum(accs) / len(accs)
            total_error += abs(expected - actual)
            n_bins += 1

        if n_bins == 0:
            return 0.5

        mae = total_error / n_bins
        calibration = 1.0 - mae

        return max(0.0, min(1.0, calibration))

    def calculate_intrusion_characteristics(
        self
    ) -> Dict[str, float]:
        """Get characteristics of intrusions."""
        return {
            'confidence': self._intrusion_confidence,
            'fluency': self._intrusion_fluency,
            'persistence': 0.60,  # How often output despite monitoring
            'recurrence': 0.30   # How often repeat same intrusion
        }

    def get_monitoring_effectiveness(
        self,
        criterion: CriterionType
    ) -> Dict[str, float]:
        """Get monitoring effectiveness by criterion."""
        # Strict: fewer outputs, more accurate
        # Liberal: more outputs, more errors

        if criterion == CriterionType.STRICT:
            return {
                'correct_output_rate': 0.70,
                'error_output_rate': 0.15,
                'withhold_rate': 0.35
            }
        elif criterion == CriterionType.MODERATE:
            return {
                'correct_output_rate': 0.85,
                'error_output_rate': 0.35,
                'withhold_rate': 0.20
            }
        else:  # LIBERAL
            return {
                'correct_output_rate': 0.95,
                'error_output_rate': 0.60,
                'withhold_rate': 0.08
            }


# ============================================================================
# OUTPUT MONITORING SYSTEM
# ============================================================================

class OutputMonitoringSystem:
    """
    Output monitoring simulation system.

    "Ba'el's monitoring system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = OutputMonitoringModel()

        self._attempts: Dict[str, RetrievalAttempt] = {}
        self._decisions: List[MonitoringDecision] = []
        self._results: List[OutputResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"attempt_{self._counter}"

    def create_retrieval_attempt(
        self,
        query: str,
        candidate: str,
        is_correct: bool,
        fluency: float = 0.5
    ) -> RetrievalAttempt:
        """Create retrieval attempt."""
        confidence = self._model.calculate_confidence(
            is_correct, fluency
        )

        attempt = RetrievalAttempt(
            id=self._generate_id(),
            query=query,
            candidate_response=candidate,
            is_correct=is_correct,
            confidence=confidence,
            fluency=fluency
        )

        self._attempts[attempt.id] = attempt

        return attempt

    def monitor_output(
        self,
        attempt_id: str,
        criterion: CriterionType = CriterionType.MODERATE
    ) -> MonitoringDecision:
        """Apply output monitoring."""
        attempt = self._attempts.get(attempt_id)
        if not attempt:
            return None

        should_output = self._model.should_output(attempt.confidence, criterion)

        decision = MonitoringDecision(
            attempt=attempt,
            stage=MonitoringStage.OUTPUT_BOUND,
            criterion=criterion,
            decision="output" if should_output else "withhold",
            final_response=attempt.candidate_response if should_output else None
        )

        self._decisions.append(decision)

        # Record result
        if should_output:
            if attempt.is_correct:
                response_type = ResponseType.CORRECT
            else:
                response_type = ResponseType.INTRUSION
        else:
            response_type = ResponseType.WITHHOLD

        result = OutputResult(
            response_type=response_type,
            confidence=attempt.confidence,
            calibration=0.0  # Calculated later
        )

        self._results.append(result)

        return decision

    def calculate_performance(
        self
    ) -> Dict[str, float]:
        """Calculate performance metrics."""
        if not self._results:
            return {'accuracy': 0.0, 'intrusion_rate': 0.0}

        outputs = [r for r in self._results if r.response_type != ResponseType.WITHHOLD]

        if not outputs:
            return {'accuracy': 0.0, 'intrusion_rate': 0.0}

        correct = sum(1 for r in outputs if r.response_type == ResponseType.CORRECT)
        intrusions = sum(1 for r in outputs if r.response_type == ResponseType.INTRUSION)

        return {
            'accuracy': correct / len(outputs),
            'intrusion_rate': intrusions / len(outputs),
            'withhold_rate': sum(1 for r in self._results if r.response_type == ResponseType.WITHHOLD) / len(self._results)
        }


# ============================================================================
# OUTPUT MONITORING PARADIGM
# ============================================================================

class OutputMonitoringParadigm:
    """
    Output monitoring paradigm.

    "Ba'el's monitoring study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_trials: int = 40
    ) -> Dict[str, Any]:
        """Run classic output monitoring paradigm."""
        system = OutputMonitoringSystem()

        # Create mix of correct and error trials
        for i in range(n_trials):
            is_correct = random.random() < 0.6
            fluency = random.uniform(0.3, 0.9)

            attempt = system.create_retrieval_attempt(
                f"query_{i}",
                f"response_{i}",
                is_correct,
                fluency
            )

            system.monitor_output(attempt.id, CriterionType.MODERATE)

        performance = system.calculate_performance()

        return {
            'accuracy': performance['accuracy'],
            'intrusion_rate': performance['intrusion_rate'],
            'withhold_rate': performance['withhold_rate'],
            'interpretation': f"Accuracy: {performance['accuracy']:.0%}, Intrusions: {performance['intrusion_rate']:.0%}"
        }

    def run_criterion_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare monitoring criteria."""
        model = OutputMonitoringModel()

        results = {}

        for criterion in CriterionType:
            effectiveness = model.get_monitoring_effectiveness(criterion)

            results[criterion.name] = effectiveness

        return {
            'by_criterion': results,
            'interpretation': 'Strict = accurate but misses; Liberal = complete but errors'
        }

    def run_confidence_accuracy_study(
        self
    ) -> Dict[str, Any]:
        """Study confidence-accuracy relationship."""
        system = OutputMonitoringSystem()
        model = system._model

        # Generate trials
        confidences = []
        accuracies = []

        for _ in range(100):
            is_correct = random.random() < 0.6
            fluency = random.uniform(0.3, 0.9)
            conf = model.calculate_confidence(is_correct, fluency)

            confidences.append(conf)
            accuracies.append(is_correct)

        calibration = model.calculate_calibration(confidences, accuracies)

        return {
            'calibration': calibration,
            'interpretation': f'Calibration: {calibration:.0%}'
        }

    def run_intrusion_study(
        self
    ) -> Dict[str, Any]:
        """Study intrusion characteristics."""
        model = OutputMonitoringModel()

        characteristics = model.calculate_intrusion_characteristics()

        return {
            'intrusion_characteristics': characteristics,
            'key_finding': 'Intrusions often have moderate confidence',
            'interpretation': 'Intrusions feel fluent but less sure'
        }

    def run_fluency_study(
        self
    ) -> Dict[str, Any]:
        """Study fluency effects on monitoring."""
        model = OutputMonitoringModel()

        fluency_levels = [0.2, 0.4, 0.6, 0.8]

        results = {
            'correct': {},
            'incorrect': {}
        }

        for fluency in fluency_levels:
            correct_conf = model.calculate_confidence(True, fluency)
            error_conf = model.calculate_confidence(False, fluency)

            results['correct'][f'{int(fluency * 100)}%'] = correct_conf
            results['incorrect'][f'{int(fluency * 100)}%'] = error_conf

        return {
            'by_fluency': results,
            'interpretation': 'Fluency increases confidence for both correct and errors'
        }

    def run_age_study(
        self
    ) -> Dict[str, Any]:
        """Study age effects on monitoring."""
        model = OutputMonitoringModel()

        conditions = {
            'young_adults': model._young_monitoring,
            'older_adults': model._older_monitoring
        }

        results = {}

        for condition, effectiveness in conditions.items():
            base_intrusion = 0.20
            adjusted = base_intrusion * (1 + (1 - effectiveness) * 0.5)

            results[condition] = {
                'monitoring_effectiveness': effectiveness,
                'intrusion_rate': adjusted
            }

        return {
            'by_age': results,
            'interpretation': 'Older adults: less effective monitoring'
        }

    def run_strategic_regulation_study(
        self
    ) -> Dict[str, Any]:
        """Study strategic regulation of criterion."""
        scenarios = {
            'high_stakes': {
                'recommended': CriterionType.STRICT,
                'cost_of_error': 'high',
                'withhold_acceptable': True
            },
            'brainstorming': {
                'recommended': CriterionType.LIBERAL,
                'cost_of_error': 'low',
                'withhold_acceptable': False
            },
            'normal_conversation': {
                'recommended': CriterionType.MODERATE,
                'cost_of_error': 'moderate',
                'withhold_acceptable': 'sometimes'
            }
        }

        return {
            'by_scenario': scenarios,
            'interpretation': 'Criterion adapts to context'
        }


# ============================================================================
# OUTPUT MONITORING ENGINE
# ============================================================================

class OutputMonitoringEngine:
    """
    Complete output monitoring engine.

    "Ba'el's monitoring engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = OutputMonitoringParadigm()
        self._system = OutputMonitoringSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Retrieval operations

    def create_attempt(
        self,
        query: str,
        candidate: str,
        is_correct: bool
    ) -> RetrievalAttempt:
        """Create retrieval attempt."""
        return self._system.create_retrieval_attempt(query, candidate, is_correct)

    def monitor_output(
        self,
        attempt_id: str,
        criterion: CriterionType = CriterionType.MODERATE
    ) -> MonitoringDecision:
        """Monitor output."""
        return self._system.monitor_output(attempt_id, criterion)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_criteria(
        self
    ) -> Dict[str, Any]:
        """Compare criteria."""
        return self._paradigm.run_criterion_comparison()

    def study_calibration(
        self
    ) -> Dict[str, Any]:
        """Study calibration."""
        return self._paradigm.run_confidence_accuracy_study()

    def study_intrusions(
        self
    ) -> Dict[str, Any]:
        """Study intrusions."""
        return self._paradigm.run_intrusion_study()

    def study_fluency(
        self
    ) -> Dict[str, Any]:
        """Study fluency effects."""
        return self._paradigm.run_fluency_study()

    def study_age(
        self
    ) -> Dict[str, Any]:
        """Study age effects."""
        return self._paradigm.run_age_study()

    def study_regulation(
        self
    ) -> Dict[str, Any]:
        """Study strategic regulation."""
        return self._paradigm.run_strategic_regulation_study()

    # Analysis

    def get_metrics(self) -> MonitoringMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return MonitoringMetrics(
            accuracy=last['accuracy'],
            intrusion_rate=last['intrusion_rate'],
            withhold_rate=last['withhold_rate'],
            calibration=0.7,
            by_criterion={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'attempts': len(self._system._attempts),
            'decisions': len(self._system._decisions),
            'results': len(self._system._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_output_monitoring_engine() -> OutputMonitoringEngine:
    """Create output monitoring engine."""
    return OutputMonitoringEngine()


def demonstrate_output_monitoring() -> Dict[str, Any]:
    """Demonstrate output monitoring."""
    engine = create_output_monitoring_engine()

    # Classic
    classic = engine.run_classic()

    # Criteria
    criteria = engine.compare_criteria()

    # Intrusions
    intrusions = engine.study_intrusions()

    # Age
    age = engine.study_age()

    return {
        'classic': {
            'accuracy': f"{classic['accuracy']:.0%}",
            'intrusion_rate': f"{classic['intrusion_rate']:.0%}",
            'withhold_rate': f"{classic['withhold_rate']:.0%}"
        },
        'by_criterion': {
            k: f"correct output: {v['correct_output_rate']:.0%}"
            for k, v in criteria['by_criterion'].items()
        },
        'intrusions': intrusions['intrusion_characteristics'],
        'by_age': {
            k: f"intrusions: {v['intrusion_rate']:.0%}"
            for k, v in age['by_age'].items()
        },
        'interpretation': (
            f"Accuracy: {classic['accuracy']:.0%}. "
            f"Output monitoring gates responses. "
            f"Criterion adjusts to context."
        )
    }


def get_output_monitoring_facts() -> Dict[str, str]:
    """Get facts about output monitoring."""
    return {
        'koriat_goldsmith_1996': 'Output monitoring framework',
        'mechanism': 'Confidence threshold for responding',
        'criterion': 'Adjustable threshold based on goals',
        'intrusions': 'Errors that pass monitoring',
        'fluency': 'Influences confidence for all responses',
        'calibration': 'Confidence-accuracy alignment',
        'age': 'Declines with age',
        'applications': 'Education, eyewitness memory, AI'
    }
