"""
BAEL Attention Network Engine
==============================

Posner's attention networks.
Alerting, orienting, and executive control.

"Ba'el focuses attention." — Ba'el
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
from collections import deque, defaultdict
import copy

logger = logging.getLogger("BAEL.AttentionNetwork")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class AttentionNetwork(Enum):
    """The three attention networks."""
    ALERTING = auto()      # Achieving/maintaining alertness
    ORIENTING = auto()     # Selecting sensory information
    EXECUTIVE = auto()     # Resolving conflict


class CueType(Enum):
    """Types of attention cues."""
    EXOGENOUS = auto()     # Bottom-up, automatic
    ENDOGENOUS = auto()    # Top-down, voluntary
    DOUBLE_CUE = auto()
    NO_CUE = auto()


class TargetType(Enum):
    """Types of targets."""
    CONGRUENT = auto()     # No conflict
    INCONGRUENT = auto()   # Conflict present
    NEUTRAL = auto()


class SelectionMode(Enum):
    """Attention selection modes."""
    SPACE_BASED = auto()   # Spatial attention
    OBJECT_BASED = auto()  # Object attention
    FEATURE_BASED = auto() # Feature attention


@dataclass
class Stimulus:
    """
    An attention stimulus.
    """
    id: str
    content: Any
    location: Tuple[float, float]  # x, y position
    salience: float = 0.5          # Bottom-up salience
    relevance: float = 0.5         # Top-down relevance
    timestamp: float = field(default_factory=time.time)

    @property
    def priority(self) -> float:
        """Combined priority."""
        return (self.salience + self.relevance) / 2


@dataclass
class AttentionCue:
    """
    A cue for attention.
    """
    id: str
    cue_type: CueType
    location: Optional[Tuple[float, float]] = None
    validity: float = 0.8  # How often cue predicts target
    timestamp: float = field(default_factory=time.time)


@dataclass
class AttentionTarget:
    """
    An attention target.
    """
    id: str
    content: Any
    target_type: TargetType
    location: Tuple[float, float]
    flankers: List[Any] = field(default_factory=list)


@dataclass
class AttentionState:
    """
    Current attention state.
    """
    focus_location: Tuple[float, float] = (0.0, 0.0)
    alertness: float = 0.5
    orientation_speed: float = 0.5
    conflict_level: float = 0.0
    selection_mode: SelectionMode = SelectionMode.SPACE_BASED


@dataclass
class AttentionResponse:
    """
    Response to attention task.
    """
    correct: bool
    reaction_time: float
    conflict_cost: float
    cue_benefit: float


# ============================================================================
# ALERTING NETWORK
# ============================================================================

class AlertingNetwork:
    """
    Alerting network - achieving and maintaining alertness.

    "Ba'el stays alert." — Ba'el
    """

    def __init__(
        self,
        baseline_alertness: float = 0.5,
        decay_rate: float = 0.01
    ):
        """Initialize alerting network."""
        self._baseline = baseline_alertness
        self._current_alertness = baseline_alertness
        self._decay_rate = decay_rate
        self._phasic_boost = 0.0
        self._lock = threading.RLock()

    def alert(self, intensity: float = 0.3) -> float:
        """Receive alerting signal."""
        with self._lock:
            self._phasic_boost = intensity
            self._current_alertness = min(
                1.0,
                self._current_alertness + intensity
            )
            return self._current_alertness

    def decay(self) -> float:
        """Decay alertness toward baseline."""
        with self._lock:
            # Phasic component decays faster
            self._phasic_boost *= 0.9

            # Tonic component decays slowly
            diff = self._current_alertness - self._baseline
            self._current_alertness -= diff * self._decay_rate

            return self._current_alertness

    def get_response_benefit(self) -> float:
        """Get RT benefit from alertness."""
        # Higher alertness = faster responses
        return self._current_alertness * 0.3

    @property
    def alertness(self) -> float:
        return self._current_alertness

    @property
    def is_vigilant(self) -> bool:
        return self._current_alertness > 0.7


# ============================================================================
# ORIENTING NETWORK
# ============================================================================

class OrientingNetwork:
    """
    Orienting network - selecting sensory information.

    "Ba'el orients attention." — Ba'el
    """

    def __init__(
        self,
        spotlight_radius: float = 0.2,
        shift_speed: float = 0.1
    ):
        """Initialize orienting network."""
        self._focus = (0.0, 0.0)
        self._spotlight_radius = spotlight_radius
        self._shift_speed = shift_speed
        self._cue_history: deque = deque(maxlen=100)
        self._lock = threading.RLock()

    def cue(
        self,
        cue: AttentionCue
    ) -> float:
        """Process attention cue."""
        with self._lock:
            self._cue_history.append(cue)

            if cue.location and cue.cue_type == CueType.EXOGENOUS:
                # Automatic orienting to cue location
                self._shift_to(cue.location)
                return 0.1  # Fast exogenous shift
            elif cue.location and cue.cue_type == CueType.ENDOGENOUS:
                # Voluntary orienting
                self._shift_to(cue.location)
                return 0.3  # Slower endogenous shift

            return 0.0

    def _shift_to(self, location: Tuple[float, float]) -> None:
        """Shift attention to location."""
        self._focus = location

    def is_in_spotlight(
        self,
        location: Tuple[float, float]
    ) -> bool:
        """Check if location is in attention spotlight."""
        dx = location[0] - self._focus[0]
        dy = location[1] - self._focus[1]
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self._spotlight_radius

    def get_validity_effect(
        self,
        cue: AttentionCue,
        target_location: Tuple[float, float]
    ) -> float:
        """Get validity effect (valid cue benefit)."""
        if cue.location is None:
            return 0.0

        cue_predicts = self.is_in_spotlight(target_location)

        if cue_predicts:
            return 0.2  # Valid cue benefit
        else:
            return -0.1  # Invalid cue cost

    @property
    def focus(self) -> Tuple[float, float]:
        return self._focus

    @property
    def spotlight_radius(self) -> float:
        return self._spotlight_radius


# ============================================================================
# EXECUTIVE NETWORK
# ============================================================================

class ExecutiveNetwork:
    """
    Executive network - resolving conflict.

    "Ba'el resolves conflict." — Ba'el
    """

    def __init__(
        self,
        conflict_threshold: float = 0.5,
        resolution_capacity: float = 1.0
    ):
        """Initialize executive network."""
        self._conflict_threshold = conflict_threshold
        self._capacity = resolution_capacity
        self._current_conflict = 0.0
        self._resolution_history: deque = deque(maxlen=100)
        self._lock = threading.RLock()

    def detect_conflict(
        self,
        target: AttentionTarget
    ) -> float:
        """Detect conflict in target."""
        with self._lock:
            if target.target_type == TargetType.CONGRUENT:
                conflict = 0.1
            elif target.target_type == TargetType.INCONGRUENT:
                conflict = 0.7
                # More flankers = more conflict
                conflict += len(target.flankers) * 0.05
            else:
                conflict = 0.3

            self._current_conflict = min(1.0, conflict)
            return self._current_conflict

    def resolve_conflict(
        self,
        conflict_level: float
    ) -> Tuple[float, float]:
        """Resolve conflict, return (success_probability, time_cost)."""
        with self._lock:
            if conflict_level <= self._conflict_threshold:
                # Easy resolution
                success = 0.95
                time_cost = 0.05
            else:
                # Difficult resolution
                ratio = conflict_level / self._capacity
                success = max(0.5, 1.0 - ratio * 0.4)
                time_cost = ratio * 0.2

            self._resolution_history.append({
                'conflict': conflict_level,
                'success': success,
                'cost': time_cost
            })

            return success, time_cost

    def get_conflict_effect(self) -> float:
        """Get conflict effect (incongruent - congruent)."""
        return self._current_conflict * 0.15

    @property
    def conflict_level(self) -> float:
        return self._current_conflict

    @property
    def is_overloaded(self) -> bool:
        return self._current_conflict > self._capacity


# ============================================================================
# INTEGRATED ATTENTION
# ============================================================================

class IntegratedAttention:
    """
    Integrate all three attention networks.

    "Ba'el's unified attention." — Ba'el
    """

    def __init__(self):
        """Initialize integrated attention."""
        self._alerting = AlertingNetwork()
        self._orienting = OrientingNetwork()
        self._executive = ExecutiveNetwork()
        self._state = AttentionState()
        self._lock = threading.RLock()

    def process_trial(
        self,
        cue: AttentionCue,
        target: AttentionTarget
    ) -> AttentionResponse:
        """Process an attention trial (like ANT)."""
        with self._lock:
            # Alerting
            if cue.cue_type != CueType.NO_CUE:
                self._alerting.alert(0.2)
            alerting_benefit = self._alerting.get_response_benefit()

            # Orienting
            orienting_time = self._orienting.cue(cue)
            validity_effect = self._orienting.get_validity_effect(
                cue, target.location
            )

            # Executive
            conflict = self._executive.detect_conflict(target)
            success_prob, conflict_cost = self._executive.resolve_conflict(conflict)

            # Calculate response
            base_rt = 0.5
            rt = base_rt - alerting_benefit + orienting_time - validity_effect + conflict_cost
            rt = max(0.1, rt)

            correct = random.random() < success_prob

            # Update state
            self._state.alertness = self._alerting.alertness
            self._state.focus_location = self._orienting.focus
            self._state.conflict_level = conflict

            return AttentionResponse(
                correct=correct,
                reaction_time=rt,
                conflict_cost=conflict_cost,
                cue_benefit=validity_effect + alerting_benefit
            )

    def update(self) -> None:
        """Update attention state."""
        with self._lock:
            self._alerting.decay()
            self._state.alertness = self._alerting.alertness

    @property
    def alerting(self) -> AlertingNetwork:
        return self._alerting

    @property
    def orienting(self) -> OrientingNetwork:
        return self._orienting

    @property
    def executive(self) -> ExecutiveNetwork:
        return self._executive

    @property
    def state(self) -> AttentionState:
        return self._state


# ============================================================================
# ATTENTION NETWORK ENGINE
# ============================================================================

class AttentionNetworkEngine:
    """
    Complete attention network implementation.

    "Ba'el's attention mastery." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._attention = IntegratedAttention()
        self._stimulus_counter = 0
        self._trial_history: List[AttentionResponse] = []
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._stimulus_counter += 1
        return f"stim_{self._stimulus_counter}"

    # Stimulus creation

    def create_stimulus(
        self,
        content: Any,
        location: Tuple[float, float] = (0.0, 0.0),
        salience: float = 0.5
    ) -> Stimulus:
        """Create stimulus."""
        return Stimulus(
            id=self._generate_id(),
            content=content,
            location=location,
            salience=salience
        )

    def create_cue(
        self,
        cue_type: CueType,
        location: Tuple[float, float] = None,
        validity: float = 0.8
    ) -> AttentionCue:
        """Create attention cue."""
        return AttentionCue(
            id=self._generate_id(),
            cue_type=cue_type,
            location=location,
            validity=validity
        )

    def create_target(
        self,
        content: Any,
        target_type: TargetType,
        location: Tuple[float, float],
        flankers: List[Any] = None
    ) -> AttentionTarget:
        """Create attention target."""
        return AttentionTarget(
            id=self._generate_id(),
            content=content,
            target_type=target_type,
            location=location,
            flankers=flankers or []
        )

    # Attention operations

    def alert(self, intensity: float = 0.3) -> float:
        """Send alerting signal."""
        return self._attention.alerting.alert(intensity)

    def orient(
        self,
        location: Tuple[float, float],
        cue_type: CueType = CueType.ENDOGENOUS
    ) -> float:
        """Orient attention to location."""
        cue = self.create_cue(cue_type, location)
        return self._attention.orienting.cue(cue)

    def resolve_conflict(
        self,
        conflict_level: float
    ) -> Tuple[float, float]:
        """Resolve conflict."""
        return self._attention.executive.resolve_conflict(conflict_level)

    def run_trial(
        self,
        cue_type: CueType,
        target_type: TargetType,
        cue_location: Tuple[float, float] = None,
        target_location: Tuple[float, float] = (0.0, 0.0)
    ) -> AttentionResponse:
        """Run attention trial."""
        cue = self.create_cue(cue_type, cue_location)
        target = self.create_target(
            "target",
            target_type,
            target_location
        )

        response = self._attention.process_trial(cue, target)
        self._trial_history.append(response)

        return response

    def is_attended(
        self,
        location: Tuple[float, float]
    ) -> bool:
        """Check if location is attended."""
        return self._attention.orienting.is_in_spotlight(location)

    def update(self) -> None:
        """Update attention state."""
        self._attention.update()

    # Analysis

    def get_network_effects(self) -> Dict[str, float]:
        """Calculate network effects from trial history."""
        if len(self._trial_history) < 4:
            return {'alerting': 0.0, 'orienting': 0.0, 'conflict': 0.0}

        # Calculate average effects
        avg_cue_benefit = sum(t.cue_benefit for t in self._trial_history) / len(self._trial_history)
        avg_conflict = sum(t.conflict_cost for t in self._trial_history) / len(self._trial_history)

        return {
            'alerting': self._attention.alerting.get_response_benefit(),
            'orienting': avg_cue_benefit,
            'conflict': avg_conflict
        }

    @property
    def alertness(self) -> float:
        return self._attention.state.alertness

    @property
    def focus(self) -> Tuple[float, float]:
        return self._attention.state.focus_location

    @property
    def conflict_level(self) -> float:
        return self._attention.state.conflict_level

    @property
    def engine_state(self) -> Dict[str, Any]:
        """Get engine state."""
        state = self._attention.state
        return {
            'alertness': state.alertness,
            'focus': state.focus_location,
            'conflict': state.conflict_level,
            'selection_mode': state.selection_mode.name,
            'trials': len(self._trial_history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_attention_network_engine() -> AttentionNetworkEngine:
    """Create attention network engine."""
    return AttentionNetworkEngine()


def run_ant_trial(
    cue_type: CueType,
    target_type: TargetType
) -> AttentionResponse:
    """Run a quick ANT-style trial."""
    engine = create_attention_network_engine()
    return engine.run_trial(cue_type, target_type)
