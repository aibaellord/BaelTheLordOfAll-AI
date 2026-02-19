"""
BAEL Cognitive Control Engine
==============================

Executive control and inhibition.
Task switching and monitoring.

"Ba'el controls cognition." — Ba'el
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

logger = logging.getLogger("BAEL.CognitiveControl")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ControlMode(Enum):
    """Control mode."""
    PROACTIVE = auto()     # Preparation before event
    REACTIVE = auto()      # Response to event
    DUAL = auto()          # Both modes


class ConflictType(Enum):
    """Types of cognitive conflict."""
    RESPONSE = auto()      # Response competition
    STIMULUS = auto()       # Stimulus competition
    TASK = auto()          # Task-set conflict


class InhibitionType(Enum):
    """Types of inhibition."""
    RESPONSE = auto()      # Stop ongoing response
    PROACTIVE = auto()     # Prevent prepotent response
    INTERFERENCE = auto()  # Filter interference


class MonitoringSignal(Enum):
    """Monitoring signals."""
    CONFLICT = auto()
    ERROR = auto()
    UNCERTAINTY = auto()
    OVERLOAD = auto()


@dataclass
class Task:
    """
    A cognitive task.
    """
    id: str
    name: str
    rules: Dict[str, Any]
    active: bool = False
    activation: float = 0.0
    switch_cost: float = 0.0
    last_switch: float = field(default_factory=time.time)


@dataclass
class Stimulus:
    """
    A stimulus requiring response.
    """
    id: str
    features: Dict[str, Any]
    congruent: bool = True
    presented_at: float = field(default_factory=time.time)


@dataclass
class Response:
    """
    A response to stimulus.
    """
    id: str
    stimulus_id: str
    task_id: str
    response_value: Any
    reaction_time: float
    correct: bool
    conflict_level: float = 0.0


@dataclass
class ControlSignal:
    """
    A control signal.
    """
    type: MonitoringSignal
    strength: float
    source: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class TaskSet:
    """
    A set of task rules.
    """
    id: str
    name: str
    stimulus_response_mappings: Dict[str, Any]
    attention_weights: Dict[str, float]
    readiness: float = 0.0


# ============================================================================
# CONFLICT MONITOR
# ============================================================================

class ConflictMonitor:
    """
    Monitor for cognitive conflict.

    "Ba'el detects conflict." — Ba'el
    """

    def __init__(self, threshold: float = 0.5):
        """Initialize monitor."""
        self._threshold = threshold
        self._conflict_history: deque = deque(maxlen=100)
        self._lock = threading.RLock()

    def detect_conflict(
        self,
        response_activations: Dict[str, float]
    ) -> float:
        """Detect response conflict."""
        with self._lock:
            if len(response_activations) < 2:
                return 0.0

            values = list(response_activations.values())

            # Conflict = product of activations (Botvinick et al.)
            # High when multiple responses active
            conflict = 1.0
            for v in values:
                conflict *= max(0.01, v)

            # Normalize
            conflict = conflict ** (1.0 / len(values))

            self._conflict_history.append(conflict)

            return conflict

    def detect_stroop_conflict(
        self,
        word: str,
        color: str
    ) -> float:
        """Detect Stroop-like conflict."""
        with self._lock:
            if word.lower() == color.lower():
                return 0.0  # Congruent
            elif word.lower() in ['red', 'green', 'blue', 'yellow']:
                return 0.8  # Incongruent
            else:
                return 0.3  # Neutral

    def should_upregulate(self) -> bool:
        """Should control be upregulated?"""
        if not self._conflict_history:
            return False

        recent = list(self._conflict_history)[-10:]
        avg_conflict = sum(recent) / len(recent)

        return avg_conflict > self._threshold

    @property
    def average_conflict(self) -> float:
        if not self._conflict_history:
            return 0.0
        return sum(self._conflict_history) / len(self._conflict_history)


# ============================================================================
# INHIBITORY CONTROL
# ============================================================================

class InhibitoryControl:
    """
    Inhibitory control mechanisms.

    "Ba'el inhibits impulses." — Ba'el
    """

    def __init__(self):
        """Initialize inhibitor."""
        self._stop_signal_delay: float = 0.2
        self._inhibition_strength: float = 0.5
        self._active_inhibitions: Dict[str, float] = {}
        self._lock = threading.RLock()

    def stop_signal(
        self,
        response_id: str,
        delay: float = None
    ) -> bool:
        """
        Issue stop signal.

        Returns True if response was inhibited.
        """
        with self._lock:
            d = delay or self._stop_signal_delay

            # Probabilistic inhibition based on delay
            # Shorter delay = more likely to inhibit
            inhibit_prob = 1.0 / (1.0 + math.exp(10.0 * (d - 0.2)))

            inhibited = random.random() < inhibit_prob

            if inhibited:
                self._active_inhibitions[response_id] = time.time()

            return inhibited

    def is_inhibited(self, response_id: str) -> bool:
        """Check if response is inhibited."""
        return response_id in self._active_inhibitions

    def release(self, response_id: str) -> None:
        """Release inhibition."""
        self._active_inhibitions.pop(response_id, None)

    def proactive_inhibition(
        self,
        response_activations: Dict[str, float],
        target_response: str
    ) -> Dict[str, float]:
        """Apply proactive inhibition."""
        with self._lock:
            result = {}

            for resp_id, activation in response_activations.items():
                if resp_id == target_response:
                    result[resp_id] = activation
                else:
                    # Inhibit non-target responses
                    result[resp_id] = activation * (1.0 - self._inhibition_strength)

            return result

    def interference_control(
        self,
        target_activation: float,
        distractor_activation: float
    ) -> float:
        """Filter interference."""
        with self._lock:
            # Enhance target relative to distractor
            interference = distractor_activation * 0.3
            return max(0.0, target_activation - interference)


# ============================================================================
# TASK SWITCHING
# ============================================================================

class TaskSwitcher:
    """
    Task switching mechanism.

    "Ba'el switches tasks." — Ba'el
    """

    def __init__(
        self,
        switch_cost: float = 0.2,
        residual_cost: float = 0.1
    ):
        """Initialize switcher."""
        self._switch_cost = switch_cost
        self._residual_cost = residual_cost
        self._current_task: Optional[Task] = None
        self._previous_task: Optional[Task] = None
        self._switch_count = 0
        self._lock = threading.RLock()

    def switch_to(self, task: Task) -> float:
        """Switch to new task. Returns switch cost."""
        with self._lock:
            if self._current_task is None:
                self._current_task = task
                task.active = True
                task.activation = 1.0
                return 0.0

            if task.id == self._current_task.id:
                return 0.0  # No switch

            # Deactivate current
            self._current_task.active = False
            self._current_task.activation *= 0.5

            # Switch
            self._previous_task = self._current_task
            self._current_task = task
            task.active = True
            task.activation = 1.0
            task.last_switch = time.time()

            self._switch_count += 1

            # Compute switch cost
            cost = self._switch_cost

            # Add residual from previous task
            if self._previous_task:
                residual = self._previous_task.activation * self._residual_cost
                cost += residual

            task.switch_cost = cost

            return cost

    def get_switch_cost(self) -> float:
        """Get current switch cost."""
        if self._current_task:
            return self._current_task.switch_cost
        return 0.0

    @property
    def current_task(self) -> Optional[Task]:
        return self._current_task

    @property
    def switch_count(self) -> int:
        return self._switch_count


# ============================================================================
# COGNITIVE CONTROL ENGINE
# ============================================================================

class CognitiveControlEngine:
    """
    Complete cognitive control engine.

    "Ba'el's executive function." — Ba'el
    """

    def __init__(
        self,
        mode: ControlMode = ControlMode.DUAL
    ):
        """Initialize engine."""
        self._mode = mode
        self._monitor = ConflictMonitor()
        self._inhibitor = InhibitoryControl()
        self._switcher = TaskSwitcher()

        self._tasks: Dict[str, Task] = {}
        self._responses: List[Response] = []
        self._control_signals: List[ControlSignal] = []

        self._task_counter = 0
        self._response_counter = 0
        self._lock = threading.RLock()

    def _generate_task_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter}"

    def _generate_response_id(self) -> str:
        self._response_counter += 1
        return f"resp_{self._response_counter}"

    # Task management

    def create_task(
        self,
        name: str,
        rules: Dict[str, Any] = None
    ) -> Task:
        """Create task."""
        with self._lock:
            task = Task(
                id=self._generate_task_id(),
                name=name,
                rules=rules or {}
            )
            self._tasks[task.id] = task
            return task

    def switch_task(self, task_name: str) -> float:
        """Switch to task. Returns switch cost."""
        task = self.get_task(task_name)
        if not task:
            return 0.0
        return self._switcher.switch_to(task)

    def get_task(self, name: str) -> Optional[Task]:
        """Get task by name."""
        for task in self._tasks.values():
            if task.name.lower() == name.lower():
                return task
        return None

    # Response processing

    def process_stimulus(
        self,
        stimulus: Stimulus,
        response_options: Dict[str, float]
    ) -> Response:
        """Process stimulus and generate response."""
        with self._lock:
            start_time = time.time()

            current_task = self._switcher.current_task

            # Detect conflict
            conflict = self._monitor.detect_conflict(response_options)

            # Apply control
            if self._mode in [ControlMode.PROACTIVE, ControlMode.DUAL]:
                # Boost task-relevant response
                if current_task and 'target_response' in current_task.rules:
                    target = current_task.rules['target_response']
                    response_options = self._inhibitor.proactive_inhibition(
                        response_options, target
                    )

            if self._mode in [ControlMode.REACTIVE, ControlMode.DUAL]:
                # Upregulate control on high conflict
                if self._monitor.should_upregulate():
                    # Increase inhibition
                    for resp_id in response_options:
                        if response_options[resp_id] < 0.5:
                            response_options[resp_id] *= 0.5

            # Select response
            best_response = max(response_options, key=response_options.get)

            # Add RT cost from conflict and switching
            base_rt = 0.3
            conflict_cost = conflict * 0.2
            switch_cost = self._switcher.get_switch_cost()

            rt = base_rt + conflict_cost + switch_cost

            response = Response(
                id=self._generate_response_id(),
                stimulus_id=stimulus.id,
                task_id=current_task.id if current_task else "",
                response_value=best_response,
                reaction_time=rt,
                correct=stimulus.congruent or conflict < 0.5,
                conflict_level=conflict
            )

            self._responses.append(response)

            return response

    # Inhibition

    def stop(self, response_id: str, delay: float = 0.2) -> bool:
        """Issue stop signal."""
        return self._inhibitor.stop_signal(response_id, delay)

    def is_inhibited(self, response_id: str) -> bool:
        """Check if response is inhibited."""
        return self._inhibitor.is_inhibited(response_id)

    # Monitoring

    def emit_signal(
        self,
        signal_type: MonitoringSignal,
        strength: float,
        source: str
    ) -> ControlSignal:
        """Emit control signal."""
        signal = ControlSignal(
            type=signal_type,
            strength=strength,
            source=source
        )
        self._control_signals.append(signal)
        return signal

    def detect_error(self, response: Response, correct_response: Any) -> bool:
        """Detect response error."""
        is_error = response.response_value != correct_response

        if is_error:
            self.emit_signal(MonitoringSignal.ERROR, 1.0, response.id)

        return is_error

    # Analysis

    def get_conflict_history(self) -> List[float]:
        """Get conflict history."""
        return list(self._monitor._conflict_history)

    def get_accuracy(self) -> float:
        """Get response accuracy."""
        if not self._responses:
            return 0.0
        correct = sum(1 for r in self._responses if r.correct)
        return correct / len(self._responses)

    def get_mean_rt(self) -> float:
        """Get mean reaction time."""
        if not self._responses:
            return 0.0
        return sum(r.reaction_time for r in self._responses) / len(self._responses)

    @property
    def current_task(self) -> Optional[Task]:
        return self._switcher.current_task

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'mode': self._mode.name,
            'tasks': len(self._tasks),
            'responses': len(self._responses),
            'current_task': self._switcher.current_task.name if self._switcher.current_task else None,
            'switch_count': self._switcher.switch_count,
            'average_conflict': self._monitor.average_conflict,
            'accuracy': self.get_accuracy(),
            'mean_rt': self.get_mean_rt()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_cognitive_control_engine(
    mode: ControlMode = ControlMode.DUAL
) -> CognitiveControlEngine:
    """Create cognitive control engine."""
    return CognitiveControlEngine(mode)


def detect_stroop_conflict(
    word: str,
    color: str
) -> float:
    """Quick Stroop conflict detection."""
    monitor = ConflictMonitor()
    return monitor.detect_stroop_conflict(word, color)
