"""
BAEL Metacognition Engine
==========================

Thinking about thinking.
Cognitive self-monitoring and control.

"Ba'el knows what Ba'el knows." — Ba'el
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

logger = logging.getLogger("BAEL.Metacognition")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MetacognitiveLevel(Enum):
    """Levels of metacognition."""
    OBJECT_LEVEL = auto()    # First-order cognition
    META_LEVEL = auto()       # Monitoring/control
    HYPER_META = auto()       # Meta-metacognition


class MonitoringType(Enum):
    """Types of metacognitive monitoring."""
    FEELING_OF_KNOWING = auto()   # FOK
    JUDGMENT_OF_LEARNING = auto() # JOL
    CONFIDENCE = auto()
    FLUENCY = auto()
    TIP_OF_TONGUE = auto()


class ControlAction(Enum):
    """Metacognitive control actions."""
    ALLOCATE_TIME = auto()
    SWITCH_STRATEGY = auto()
    RESTUDY = auto()
    TERMINATE = auto()
    SEEK_HELP = auto()


class CognitiveProcess(Enum):
    """Monitored cognitive processes."""
    MEMORY = auto()
    REASONING = auto()
    PROBLEM_SOLVING = auto()
    LEARNING = auto()
    DECISION = auto()


@dataclass
class MetacognitiveJudgment:
    """
    A metacognitive judgment.
    """
    id: str
    type: MonitoringType
    target: str
    value: float  # 0-1 confidence/likelihood
    timestamp: float = field(default_factory=time.time)
    calibrated_value: Optional[float] = None
    actual_outcome: Optional[bool] = None


@dataclass
class CognitiveState:
    """
    Current cognitive state.
    """
    process: CognitiveProcess
    effort: float = 0.5
    fluency: float = 0.5
    progress: float = 0.0
    time_elapsed: float = 0.0
    errors: int = 0


@dataclass
class ControlDecision:
    """
    A control decision.
    """
    id: str
    action: ControlAction
    reason: str
    based_on: List[str]  # Judgment IDs
    timestamp: float = field(default_factory=time.time)


@dataclass
class CalibrationResult:
    """
    Calibration analysis result.
    """
    mean_confidence: float
    accuracy: float
    over_under_confidence: float  # Positive = overconfident
    brier_score: float


# ============================================================================
# METACOGNITIVE MONITORING
# ============================================================================

class MetacognitiveMonitor:
    """
    Monitor cognitive processes.

    "Ba'el monitors itself." — Ba'el
    """

    def __init__(self):
        """Initialize monitor."""
        self._judgments: Dict[str, MetacognitiveJudgment] = {}
        self._judgment_counter = 0
        self._history: deque = deque(maxlen=1000)
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._judgment_counter += 1
        return f"judgment_{self._judgment_counter}"

    def feeling_of_knowing(
        self,
        target: str,
        cue_familiarity: float = 0.5,
        partial_info: float = 0.0
    ) -> MetacognitiveJudgment:
        """Generate Feeling of Knowing judgment."""
        with self._lock:
            # FOK based on familiarity and partial info
            fok = (cue_familiarity * 0.6 + partial_info * 0.4)

            judgment = MetacognitiveJudgment(
                id=self._generate_id(),
                type=MonitoringType.FEELING_OF_KNOWING,
                target=target,
                value=fok
            )

            self._judgments[judgment.id] = judgment
            self._history.append(judgment)

            return judgment

    def judgment_of_learning(
        self,
        target: str,
        encoding_fluency: float = 0.5,
        study_time: float = 1.0
    ) -> MetacognitiveJudgment:
        """Generate Judgment of Learning."""
        with self._lock:
            # JOL based on fluency (often misleading)
            jol = encoding_fluency * 0.7 + min(1.0, study_time / 10.0) * 0.3

            judgment = MetacognitiveJudgment(
                id=self._generate_id(),
                type=MonitoringType.JUDGMENT_OF_LEARNING,
                target=target,
                value=jol
            )

            self._judgments[judgment.id] = judgment
            self._history.append(judgment)

            return judgment

    def confidence_judgment(
        self,
        target: str,
        evidence_strength: float = 0.5,
        consistency: float = 0.5
    ) -> MetacognitiveJudgment:
        """Generate confidence judgment."""
        with self._lock:
            confidence = (evidence_strength + consistency) / 2

            judgment = MetacognitiveJudgment(
                id=self._generate_id(),
                type=MonitoringType.CONFIDENCE,
                target=target,
                value=confidence
            )

            self._judgments[judgment.id] = judgment
            self._history.append(judgment)

            return judgment

    def record_outcome(
        self,
        judgment_id: str,
        success: bool
    ) -> None:
        """Record actual outcome for judgment."""
        with self._lock:
            if judgment_id in self._judgments:
                self._judgments[judgment_id].actual_outcome = success

    @property
    def judgments(self) -> List[MetacognitiveJudgment]:
        return list(self._judgments.values())


# ============================================================================
# METACOGNITIVE CONTROL
# ============================================================================

class MetacognitiveController:
    """
    Control cognitive processes.

    "Ba'el controls itself." — Ba'el
    """

    def __init__(self):
        """Initialize controller."""
        self._decisions: List[ControlDecision] = []
        self._decision_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._decision_counter += 1
        return f"decision_{self._decision_counter}"

    def decide(
        self,
        state: CognitiveState,
        judgments: List[MetacognitiveJudgment]
    ) -> ControlDecision:
        """Make control decision based on monitoring."""
        with self._lock:
            # Analyze situation
            avg_confidence = sum(j.value for j in judgments) / len(judgments) if judgments else 0.5

            # Decision rules
            action = ControlAction.ALLOCATE_TIME
            reason = ""

            if state.progress > 0.9:
                action = ControlAction.TERMINATE
                reason = "Goal nearly achieved"

            elif state.effort > 0.8 and state.progress < 0.3:
                action = ControlAction.SWITCH_STRATEGY
                reason = "High effort, low progress"

            elif avg_confidence < 0.3:
                action = ControlAction.RESTUDY
                reason = "Low confidence"

            elif state.errors > 3:
                action = ControlAction.SEEK_HELP
                reason = "Multiple errors"

            else:
                action = ControlAction.ALLOCATE_TIME
                reason = "Continue current approach"

            decision = ControlDecision(
                id=self._generate_id(),
                action=action,
                reason=reason,
                based_on=[j.id for j in judgments]
            )

            self._decisions.append(decision)

            return decision

    def time_allocation(
        self,
        items: List[str],
        judgments: Dict[str, float],
        total_time: float = 100.0
    ) -> Dict[str, float]:
        """Allocate study time based on judgments."""
        with self._lock:
            # Allocate more time to lower-confidence items
            inverse_confidence = {
                item: 1.0 - judgments.get(item, 0.5)
                for item in items
            }

            total_inverse = sum(inverse_confidence.values())

            if total_inverse == 0:
                # Equal allocation
                equal_time = total_time / len(items)
                return {item: equal_time for item in items}

            return {
                item: (inverse / total_inverse) * total_time
                for item, inverse in inverse_confidence.items()
            }

    @property
    def decisions(self) -> List[ControlDecision]:
        return list(self._decisions)


# ============================================================================
# CALIBRATION
# ============================================================================

class CalibrationAnalyzer:
    """
    Analyze metacognitive calibration.

    "Ba'el calibrates judgments." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._lock = threading.RLock()

    def analyze(
        self,
        judgments: List[MetacognitiveJudgment]
    ) -> CalibrationResult:
        """Analyze calibration of judgments."""
        with self._lock:
            # Filter judgments with outcomes
            with_outcomes = [j for j in judgments if j.actual_outcome is not None]

            if not with_outcomes:
                return CalibrationResult(
                    mean_confidence=0.0,
                    accuracy=0.0,
                    over_under_confidence=0.0,
                    brier_score=0.0
                )

            # Mean confidence
            mean_conf = sum(j.value for j in with_outcomes) / len(with_outcomes)

            # Accuracy
            correct = sum(1 for j in with_outcomes if j.actual_outcome)
            accuracy = correct / len(with_outcomes)

            # Over/under confidence
            over_under = mean_conf - accuracy

            # Brier score
            brier = sum(
                (j.value - (1.0 if j.actual_outcome else 0.0)) ** 2
                for j in with_outcomes
            ) / len(with_outcomes)

            return CalibrationResult(
                mean_confidence=mean_conf,
                accuracy=accuracy,
                over_under_confidence=over_under,
                brier_score=brier
            )

    def calibrate(
        self,
        judgment: MetacognitiveJudgment,
        calibration_result: CalibrationResult
    ) -> float:
        """Apply calibration to judgment."""
        # Adjust based on historical over/under confidence
        adjustment = -calibration_result.over_under_confidence
        calibrated = max(0.0, min(1.0, judgment.value + adjustment))
        judgment.calibrated_value = calibrated
        return calibrated


# ============================================================================
# METACOGNITION ENGINE
# ============================================================================

class MetacognitionEngine:
    """
    Complete metacognition engine.

    "Ba'el's self-awareness." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._monitor = MetacognitiveMonitor()
        self._controller = MetacognitiveController()
        self._calibration = CalibrationAnalyzer()

        self._cognitive_states: Dict[str, CognitiveState] = {}
        self._state_counter = 0
        self._lock = threading.RLock()

    def _generate_state_id(self) -> str:
        self._state_counter += 1
        return f"cog_state_{self._state_counter}"

    # Monitoring

    def feeling_of_knowing(
        self,
        target: str,
        familiarity: float = 0.5
    ) -> MetacognitiveJudgment:
        """Generate FOK judgment."""
        return self._monitor.feeling_of_knowing(target, familiarity)

    def judgment_of_learning(
        self,
        target: str,
        fluency: float = 0.5
    ) -> MetacognitiveJudgment:
        """Generate JOL."""
        return self._monitor.judgment_of_learning(target, fluency)

    def confidence(
        self,
        target: str,
        evidence: float = 0.5
    ) -> MetacognitiveJudgment:
        """Generate confidence judgment."""
        return self._monitor.confidence_judgment(target, evidence)

    def record_outcome(
        self,
        judgment_id: str,
        success: bool
    ) -> None:
        """Record outcome for judgment."""
        self._monitor.record_outcome(judgment_id, success)

    # Control

    def create_cognitive_state(
        self,
        process: CognitiveProcess,
        effort: float = 0.5,
        fluency: float = 0.5
    ) -> str:
        """Create cognitive state for monitoring."""
        state_id = self._generate_state_id()
        self._cognitive_states[state_id] = CognitiveState(
            process=process,
            effort=effort,
            fluency=fluency
        )
        return state_id

    def update_state(
        self,
        state_id: str,
        progress: float = None,
        effort: float = None,
        errors: int = None
    ) -> None:
        """Update cognitive state."""
        if state_id in self._cognitive_states:
            state = self._cognitive_states[state_id]
            if progress is not None:
                state.progress = progress
            if effort is not None:
                state.effort = effort
            if errors is not None:
                state.errors = errors

    def decide(
        self,
        state_id: str
    ) -> ControlDecision:
        """Make control decision for state."""
        state = self._cognitive_states.get(state_id)
        if not state:
            state = CognitiveState(process=CognitiveProcess.PROBLEM_SOLVING)

        judgments = self._monitor.judgments[-10:]  # Recent judgments
        return self._controller.decide(state, judgments)

    def allocate_time(
        self,
        items: List[str],
        total_time: float = 100.0
    ) -> Dict[str, float]:
        """Allocate study time."""
        judgments = {
            j.target: j.value
            for j in self._monitor.judgments
            if j.target in items
        }
        return self._controller.time_allocation(items, judgments, total_time)

    # Calibration

    def get_calibration(self) -> CalibrationResult:
        """Get calibration analysis."""
        return self._calibration.analyze(self._monitor.judgments)

    def calibrate_judgment(
        self,
        judgment: MetacognitiveJudgment
    ) -> float:
        """Calibrate a judgment."""
        calibration = self.get_calibration()
        return self._calibration.calibrate(judgment, calibration)

    # Self-assessment

    def know_what_i_know(
        self,
        domain: str
    ) -> Dict[str, float]:
        """Assess knowledge about domain."""
        relevant = [
            j for j in self._monitor.judgments
            if domain.lower() in j.target.lower()
        ]

        if not relevant:
            return {'known': 0.0, 'unknown': 1.0, 'uncertain': 0.0}

        known = sum(1 for j in relevant if j.value > 0.7)
        unknown = sum(1 for j in relevant if j.value < 0.3)
        uncertain = len(relevant) - known - unknown

        total = len(relevant)

        return {
            'known': known / total,
            'unknown': unknown / total,
            'uncertain': uncertain / total
        }

    @property
    def judgments(self) -> List[MetacognitiveJudgment]:
        return self._monitor.judgments

    @property
    def decisions(self) -> List[ControlDecision]:
        return self._controller.decisions

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        calibration = self.get_calibration()
        return {
            'judgments': len(self._monitor.judgments),
            'decisions': len(self._controller.decisions),
            'cognitive_states': len(self._cognitive_states),
            'calibration': {
                'mean_confidence': calibration.mean_confidence,
                'accuracy': calibration.accuracy,
                'over_under': calibration.over_under_confidence
            }
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_metacognition_engine() -> MetacognitionEngine:
    """Create metacognition engine."""
    return MetacognitionEngine()


def assess_confidence(
    target: str,
    evidence: float = 0.5
) -> MetacognitiveJudgment:
    """Quick confidence assessment."""
    engine = create_metacognition_engine()
    return engine.confidence(target, evidence)
