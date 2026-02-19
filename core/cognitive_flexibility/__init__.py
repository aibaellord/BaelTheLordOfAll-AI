"""
BAEL Cognitive Flexibility Engine
==================================

Set shifting, task switching, and adaptive cognition.
Executive function for flexible thinking.

"Ba'el adapts to any challenge." — Ba'el
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

logger = logging.getLogger("BAEL.CognitiveFlexibility")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class FlexibilityType(Enum):
    """Types of cognitive flexibility."""
    REACTIVE = auto()      # Respond to changes
    SPONTANEOUS = auto()   # Self-initiated switching
    SET_SHIFTING = auto()  # Change mental set
    TASK_SWITCHING = auto() # Switch between tasks


class SwitchCost(Enum):
    """Types of switch costs."""
    RESTART = auto()       # Cost of restarting task
    MIXING = auto()        # Cost in mixed blocks
    RESIDUAL = auto()      # Lingering cost after switch


class TaskState(Enum):
    """State of a task."""
    INACTIVE = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    COMPLETED = auto()


class RuleType(Enum):
    """Types of rules."""
    DIMENSIONAL = auto()   # Rule by dimension (color, shape)
    CONDITIONAL = auto()   # If-then rules
    RELATIONAL = auto()    # Based on relations


@dataclass
class TaskSet:
    """
    A cognitive task set.
    """
    id: str
    name: str
    rules: Dict[str, Any]
    response_mapping: Dict[str, str]  # stimulus -> response
    state: TaskState = TaskState.INACTIVE
    activation_level: float = 0.0


@dataclass
class Trial:
    """
    A single trial.
    """
    id: str
    task_set_id: str
    stimulus: Dict[str, Any]
    correct_response: str
    actual_response: Optional[str] = None
    response_time: Optional[float] = None
    correct: Optional[bool] = None


@dataclass
class SwitchEvent:
    """
    A task switch event.
    """
    id: str
    from_task: str
    to_task: str
    timestamp: float
    switch_time: float  # Time to switch
    success: bool


@dataclass
class FlexibilityMetrics:
    """
    Metrics for cognitive flexibility.
    """
    switch_cost: float          # Average switch cost
    error_rate_switch: float    # Error rate on switch trials
    error_rate_repeat: float    # Error rate on repeat trials
    perseveration_errors: int   # Continuing old rule
    set_loss_errors: int        # Losing the new rule
    total_switches: int
    successful_switches: int


@dataclass
class MentalSet:
    """
    A mental set (cognitive bias/tendency).
    """
    id: str
    name: str
    strength: float  # 0-1
    rules: List[str]


# ============================================================================
# TASK SET MANAGER
# ============================================================================

class TaskSetManager:
    """
    Manage task sets and activation.

    "Ba'el manages mental states." — Ba'el
    """

    def __init__(self):
        """Initialize manager."""
        self._task_sets: Dict[str, TaskSet] = {}
        self._active_task: Optional[str] = None

        self._decay_rate = 0.1
        self._activation_boost = 0.5

        self._task_counter = 0
        self._lock = threading.RLock()

    def _generate_task_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter}"

    def create_task_set(
        self,
        name: str,
        rules: Dict[str, Any],
        response_mapping: Dict[str, str]
    ) -> TaskSet:
        """Create task set."""
        with self._lock:
            task_set = TaskSet(
                id=self._generate_task_id(),
                name=name,
                rules=rules,
                response_mapping=response_mapping
            )

            self._task_sets[task_set.id] = task_set
            return task_set

    def activate_task(
        self,
        task_id: str
    ) -> bool:
        """Activate task set."""
        with self._lock:
            if task_id not in self._task_sets:
                return False

            # Decay all tasks
            for tid, task in self._task_sets.items():
                if task.state == TaskState.ACTIVE:
                    task.state = TaskState.SUSPENDED
                task.activation_level *= (1 - self._decay_rate)

            # Activate target
            target = self._task_sets[task_id]
            target.state = TaskState.ACTIVE
            target.activation_level = min(1.0, target.activation_level + self._activation_boost)

            self._active_task = task_id
            return True

    def get_active_task(self) -> Optional[TaskSet]:
        """Get currently active task."""
        if self._active_task:
            return self._task_sets.get(self._active_task)
        return None

    def get_all_activations(self) -> Dict[str, float]:
        """Get all task activations."""
        return {
            tid: task.activation_level
            for tid, task in self._task_sets.items()
        }

    def decay_all(self) -> None:
        """Apply decay to all tasks."""
        with self._lock:
            for task in self._task_sets.values():
                task.activation_level *= (1 - self._decay_rate)


# ============================================================================
# SET SHIFTER
# ============================================================================

class SetShifter:
    """
    Shift between mental sets.

    "Ba'el shifts perspective." — Ba'el
    """

    def __init__(self, task_manager: TaskSetManager):
        """Initialize shifter."""
        self._task_manager = task_manager

        self._switch_history: List[SwitchEvent] = []
        self._switch_counter = 0

        self._base_switch_time = 0.2  # Base switch cost
        self._repetition_benefit = 0.05  # Benefit from repetition

        self._lock = threading.RLock()

    def _generate_switch_id(self) -> str:
        self._switch_counter += 1
        return f"switch_{self._switch_counter}"

    def shift_to(
        self,
        new_task_id: str
    ) -> SwitchEvent:
        """Shift to new task set."""
        with self._lock:
            old_task = self._task_manager.get_active_task()
            old_task_id = old_task.id if old_task else "none"

            # Calculate switch time
            if old_task_id == new_task_id:
                # Repetition - no switch cost
                switch_time = 0.0
            else:
                # Switch cost
                new_task = self._task_manager._task_sets.get(new_task_id)
                if new_task:
                    # Lower activation = higher switch cost
                    switch_time = self._base_switch_time * (1 - new_task.activation_level)
                else:
                    switch_time = self._base_switch_time

            # Perform switch
            success = self._task_manager.activate_task(new_task_id)

            event = SwitchEvent(
                id=self._generate_switch_id(),
                from_task=old_task_id,
                to_task=new_task_id,
                timestamp=time.time(),
                switch_time=switch_time,
                success=success
            )

            self._switch_history.append(event)
            return event

    def get_switch_cost(self) -> float:
        """Calculate average switch cost."""
        with self._lock:
            if not self._switch_history:
                return 0.0

            switch_times = [
                e.switch_time for e in self._switch_history
                if e.from_task != e.to_task
            ]

            if not switch_times:
                return 0.0

            return sum(switch_times) / len(switch_times)

    def get_switch_count(self) -> int:
        """Get total switch count."""
        return len([
            e for e in self._switch_history
            if e.from_task != e.to_task
        ])


# ============================================================================
# RESPONSE EXECUTOR
# ============================================================================

class ResponseExecutor:
    """
    Execute responses based on task rules.

    "Ba'el responds correctly." — Ba'el
    """

    def __init__(self, task_manager: TaskSetManager):
        """Initialize executor."""
        self._task_manager = task_manager

        self._trial_history: List[Trial] = []
        self._trial_counter = 0

        self._perseveration_rate = 0.05  # Chance of old rule
        self._attention_lapses = 0.02  # Chance of random error

        self._lock = threading.RLock()

    def _generate_trial_id(self) -> str:
        self._trial_counter += 1
        return f"trial_{self._trial_counter}"

    def execute_trial(
        self,
        stimulus: Dict[str, Any]
    ) -> Trial:
        """Execute a trial with current task set."""
        with self._lock:
            active_task = self._task_manager.get_active_task()

            if not active_task:
                return Trial(
                    id=self._generate_trial_id(),
                    task_set_id="none",
                    stimulus=stimulus,
                    correct_response="error",
                    actual_response="error",
                    correct=False
                )

            # Get correct response from mapping
            stimulus_key = self._stimulus_to_key(stimulus, active_task)
            correct_response = active_task.response_mapping.get(stimulus_key, "unknown")

            # Simulate response (with potential errors)
            actual_response = self._simulate_response(
                correct_response,
                active_task
            )

            # Timing (with switch cost)
            base_time = random.gauss(0.5, 0.1)
            switch_penalty = 0.1 if active_task.state == TaskState.ACTIVE else 0.0
            response_time = base_time + switch_penalty

            trial = Trial(
                id=self._generate_trial_id(),
                task_set_id=active_task.id,
                stimulus=stimulus,
                correct_response=correct_response,
                actual_response=actual_response,
                response_time=response_time,
                correct=(actual_response == correct_response)
            )

            self._trial_history.append(trial)
            return trial

    def _stimulus_to_key(
        self,
        stimulus: Dict[str, Any],
        task_set: TaskSet
    ) -> str:
        """Convert stimulus to response key."""
        # Use relevant dimension from rules
        relevant_dim = task_set.rules.get('relevant_dimension', 'value')
        return str(stimulus.get(relevant_dim, 'unknown'))

    def _simulate_response(
        self,
        correct_response: str,
        task_set: TaskSet
    ) -> str:
        """Simulate response with potential errors."""
        # Perseveration check
        if random.random() < self._perseveration_rate:
            # Return old response (simulated)
            return random.choice(['left', 'right'])

        # Attention lapse
        if random.random() < self._attention_lapses:
            return random.choice(['left', 'right'])

        return correct_response

    def get_error_rate(self) -> float:
        """Get overall error rate."""
        if not self._trial_history:
            return 0.0

        errors = sum(1 for t in self._trial_history if not t.correct)
        return errors / len(self._trial_history)


# ============================================================================
# FLEXIBILITY ANALYZER
# ============================================================================

class FlexibilityAnalyzer:
    """
    Analyze cognitive flexibility.

    "Ba'el measures adaptability." — Ba'el
    """

    def __init__(
        self,
        task_manager: TaskSetManager,
        set_shifter: SetShifter,
        executor: ResponseExecutor
    ):
        """Initialize analyzer."""
        self._task_manager = task_manager
        self._set_shifter = set_shifter
        self._executor = executor
        self._lock = threading.RLock()

    def compute_metrics(self) -> FlexibilityMetrics:
        """Compute flexibility metrics."""
        with self._lock:
            trials = self._executor._trial_history
            switches = self._set_shifter._switch_history

            if not trials:
                return FlexibilityMetrics(
                    switch_cost=0.0,
                    error_rate_switch=0.0,
                    error_rate_repeat=0.0,
                    perseveration_errors=0,
                    set_loss_errors=0,
                    total_switches=0,
                    successful_switches=0
                )

            # Identify switch vs repeat trials
            switch_trials = []
            repeat_trials = []

            prev_task = None
            for trial in trials:
                if prev_task is None or trial.task_set_id == prev_task:
                    repeat_trials.append(trial)
                else:
                    switch_trials.append(trial)
                prev_task = trial.task_set_id

            # Calculate metrics
            switch_cost = self._set_shifter.get_switch_cost()

            switch_errors = sum(1 for t in switch_trials if not t.correct)
            repeat_errors = sum(1 for t in repeat_trials if not t.correct)

            error_rate_switch = switch_errors / len(switch_trials) if switch_trials else 0.0
            error_rate_repeat = repeat_errors / len(repeat_trials) if repeat_trials else 0.0

            total_switches = len([s for s in switches if s.from_task != s.to_task])
            successful_switches = len([s for s in switches if s.success and s.from_task != s.to_task])

            return FlexibilityMetrics(
                switch_cost=switch_cost,
                error_rate_switch=error_rate_switch,
                error_rate_repeat=error_rate_repeat,
                perseveration_errors=0,  # Would need more detailed tracking
                set_loss_errors=0,
                total_switches=total_switches,
                successful_switches=successful_switches
            )


# ============================================================================
# COGNITIVE FLEXIBILITY ENGINE
# ============================================================================

class CognitiveFlexibilityEngine:
    """
    Complete cognitive flexibility engine.

    "Ba'el's adaptive mind." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._task_manager = TaskSetManager()
        self._set_shifter = SetShifter(self._task_manager)
        self._executor = ResponseExecutor(self._task_manager)
        self._analyzer = FlexibilityAnalyzer(
            self._task_manager,
            self._set_shifter,
            self._executor
        )

        self._lock = threading.RLock()

    # Task management

    def create_task(
        self,
        name: str,
        rules: Dict[str, Any],
        response_mapping: Dict[str, str]
    ) -> TaskSet:
        """Create task set."""
        return self._task_manager.create_task_set(name, rules, response_mapping)

    def switch_to(
        self,
        task_id: str
    ) -> SwitchEvent:
        """Switch to task."""
        return self._set_shifter.shift_to(task_id)

    def get_active_task(self) -> Optional[TaskSet]:
        """Get active task."""
        return self._task_manager.get_active_task()

    def get_activations(self) -> Dict[str, float]:
        """Get task activations."""
        return self._task_manager.get_all_activations()

    # Trial execution

    def run_trial(
        self,
        stimulus: Dict[str, Any]
    ) -> Trial:
        """Run a trial."""
        return self._executor.execute_trial(stimulus)

    def run_trials(
        self,
        stimuli: List[Dict[str, Any]],
        task_sequence: List[str]
    ) -> List[Trial]:
        """Run multiple trials with task sequence."""
        trials = []

        for i, (stim, task_id) in enumerate(zip(stimuli, task_sequence)):
            # Switch if needed
            current = self.get_active_task()
            if not current or current.id != task_id:
                self.switch_to(task_id)

            # Run trial
            trial = self.run_trial(stim)
            trials.append(trial)

        return trials

    # Analysis

    def get_metrics(self) -> FlexibilityMetrics:
        """Get flexibility metrics."""
        return self._analyzer.compute_metrics()

    def get_switch_cost(self) -> float:
        """Get switch cost."""
        return self._set_shifter.get_switch_cost()

    def get_error_rate(self) -> float:
        """Get error rate."""
        return self._executor.get_error_rate()

    # Wisconsin Card Sorting Test simulation

    def setup_wcst(self) -> Tuple[str, str, str]:
        """Setup Wisconsin Card Sorting Test tasks."""
        color_task = self.create_task(
            "color",
            {"relevant_dimension": "color"},
            {"red": "left", "blue": "right", "green": "left", "yellow": "right"}
        )

        shape_task = self.create_task(
            "shape",
            {"relevant_dimension": "shape"},
            {"circle": "left", "square": "right", "triangle": "left", "star": "right"}
        )

        number_task = self.create_task(
            "number",
            {"relevant_dimension": "number"},
            {"1": "left", "2": "right", "3": "left", "4": "right"}
        )

        return color_task.id, shape_task.id, number_task.id

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        active = self.get_active_task()
        return {
            'tasks': len(self._task_manager._task_sets),
            'active_task': active.name if active else None,
            'switches': self._set_shifter.get_switch_count(),
            'trials': len(self._executor._trial_history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_cognitive_flexibility_engine() -> CognitiveFlexibilityEngine:
    """Create cognitive flexibility engine."""
    return CognitiveFlexibilityEngine()


def run_wcst_simulation(
    num_trials: int = 48,
    switch_every: int = 10
) -> FlexibilityMetrics:
    """Run Wisconsin Card Sorting Test simulation."""
    engine = create_cognitive_flexibility_engine()

    color_id, shape_id, number_id = engine.setup_wcst()
    tasks = [color_id, shape_id, number_id]

    # Generate stimuli
    stimuli = []
    task_sequence = []

    colors = ['red', 'blue', 'green', 'yellow']
    shapes = ['circle', 'square', 'triangle', 'star']
    numbers = ['1', '2', '3', '4']

    current_task_idx = 0
    for i in range(num_trials):
        if i > 0 and i % switch_every == 0:
            current_task_idx = (current_task_idx + 1) % len(tasks)

        stim = {
            'color': random.choice(colors),
            'shape': random.choice(shapes),
            'number': random.choice(numbers)
        }

        stimuli.append(stim)
        task_sequence.append(tasks[current_task_idx])

    # Run
    engine.run_trials(stimuli, task_sequence)

    return engine.get_metrics()
