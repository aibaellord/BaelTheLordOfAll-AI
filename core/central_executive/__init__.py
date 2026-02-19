"""
BAEL Central Executive Engine
===============================

The supervisory attention system.
Baddeley's working memory controller.

"Ba'el's executive commands all." — Ba'el
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

logger = logging.getLogger("BAEL.CentralExecutive")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ExecutiveFunction(Enum):
    """Executive functions."""
    FOCUS = auto()         # Selective attention
    DIVIDE = auto()        # Divided attention
    SWITCH = auto()        # Task switching
    UPDATE = auto()        # Working memory updating
    INHIBIT = auto()       # Response inhibition


class TaskType(Enum):
    """Type of cognitive task."""
    STROOP = auto()
    NBACK = auto()
    TASK_SWITCH = auto()
    DUAL_TASK = auto()
    RANDOM_GENERATION = auto()


class AttentionState(Enum):
    """State of attention."""
    FOCUSED = auto()
    DIVIDED = auto()
    SWITCHING = auto()
    OVERLOADED = auto()


class LoadLevel(Enum):
    """Cognitive load level."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    OVERLOAD = auto()


@dataclass
class Task:
    """
    A cognitive task.
    """
    id: str
    name: str
    task_type: TaskType
    difficulty: float
    requires: List[ExecutiveFunction]


@dataclass
class ExecutiveState:
    """
    State of the central executive.
    """
    current_focus: Optional[Task]
    active_tasks: List[Task]
    attention_state: AttentionState
    load_level: LoadLevel
    resources_available: float


@dataclass
class SwitchTrial:
    """
    A task-switching trial.
    """
    id: str
    current_task: Task
    previous_task: Optional[Task]
    is_switch: bool
    preparation_time_ms: float


@dataclass
class ExecutiveResult:
    """
    Result of executive processing.
    """
    task_id: str
    function_used: ExecutiveFunction
    response_time_ms: float
    accuracy: float
    switch_cost: float
    mixing_cost: float


@dataclass
class ExecutiveMetrics:
    """
    Executive function metrics.
    """
    switch_cost: float
    mixing_cost: float
    dual_task_cost: float
    inhibition_efficiency: float
    updating_accuracy: float


# ============================================================================
# CENTRAL EXECUTIVE MODEL
# ============================================================================

class CentralExecutiveModel:
    """
    Model of the central executive.

    "Ba'el's executive model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Attention parameters
        self._total_resources = 1.0
        self._focus_threshold = 0.3

        # Switch costs
        self._switch_cost_base = 150      # ms
        self._mixing_cost_base = 50       # ms
        self._preparation_benefit = 0.5   # Reduction with prep time

        # Dual-task costs
        self._dual_task_cost = 100        # ms per task
        self._resource_limit = 1.0

        # Inhibition
        self._stroop_effect = 100         # ms
        self._inhibition_variability = 0.2

        # Updating
        self._update_cost = 50            # ms per update
        self._nback_accuracy_drop = 0.05  # Per N level

        self._lock = threading.RLock()

    def calculate_switch_cost(
        self,
        prep_time_ms: float,
        task_similarity: float
    ) -> float:
        """Calculate task-switching cost."""
        base = self._switch_cost_base

        # Preparation reduces cost
        if prep_time_ms > 0:
            prep_benefit = min(1.0, prep_time_ms / 500) * self._preparation_benefit
            base *= (1 - prep_benefit)

        # Similar tasks = smaller cost
        base *= (1 - task_similarity * 0.3)

        return max(0, base + random.uniform(-30, 30))

    def calculate_mixing_cost(
        self,
        n_tasks: int
    ) -> float:
        """Calculate mixing cost (switching vs pure blocks)."""
        return self._mixing_cost_base * math.log2(max(1, n_tasks))

    def calculate_dual_task_cost(
        self,
        task1_demand: float,
        task2_demand: float
    ) -> Tuple[float, float]:
        """Calculate dual-task interference costs."""
        total_demand = task1_demand + task2_demand

        if total_demand <= self._resource_limit:
            # No bottleneck
            cost1 = self._dual_task_cost * task2_demand
            cost2 = self._dual_task_cost * task1_demand
        else:
            # Bottleneck - prioritize task1
            overflow = total_demand - self._resource_limit
            cost1 = self._dual_task_cost * task2_demand
            cost2 = self._dual_task_cost * task1_demand + overflow * 100

        return cost1, cost2

    def calculate_stroop_effect(
        self,
        congruent: bool,
        inhibition_ability: float
    ) -> float:
        """Calculate Stroop interference."""
        if congruent:
            return -20  # Facilitation
        else:
            # Interference reduced by inhibition ability
            return self._stroop_effect * (1 - inhibition_ability)

    def calculate_nback_accuracy(
        self,
        n: int,
        base_accuracy: float = 0.95
    ) -> float:
        """Calculate n-back accuracy."""
        return base_accuracy - n * self._nback_accuracy_drop

    def calculate_random_generation_quality(
        self,
        sequence_length: int,
        concurrent_load: float
    ) -> float:
        """Calculate random generation quality."""
        # Quality decreases with length and load
        base = 0.9
        length_penalty = min(0.3, sequence_length * 0.01)
        load_penalty = concurrent_load * 0.2

        return max(0.3, base - length_penalty - load_penalty)


# ============================================================================
# CENTRAL EXECUTIVE SYSTEM
# ============================================================================

class CentralExecutiveSystem:
    """
    Central executive simulation system.

    "Ba'el's executive system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = CentralExecutiveModel()

        self._tasks: Dict[str, Task] = {}
        self._results: List[ExecutiveResult] = []

        self._current_state = ExecutiveState(
            current_focus=None,
            active_tasks=[],
            attention_state=AttentionState.FOCUSED,
            load_level=LoadLevel.LOW,
            resources_available=1.0
        )

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_task(
        self,
        name: str,
        task_type: TaskType,
        difficulty: float = 0.5
    ) -> Task:
        """Create a task."""
        requires = {
            TaskType.STROOP: [ExecutiveFunction.INHIBIT, ExecutiveFunction.FOCUS],
            TaskType.NBACK: [ExecutiveFunction.UPDATE, ExecutiveFunction.FOCUS],
            TaskType.TASK_SWITCH: [ExecutiveFunction.SWITCH, ExecutiveFunction.UPDATE],
            TaskType.DUAL_TASK: [ExecutiveFunction.DIVIDE],
            TaskType.RANDOM_GENERATION: [ExecutiveFunction.UPDATE, ExecutiveFunction.INHIBIT]
        }

        task = Task(
            id=self._generate_id(),
            name=name,
            task_type=task_type,
            difficulty=difficulty,
            requires=requires.get(task_type, [ExecutiveFunction.FOCUS])
        )

        self._tasks[task.id] = task

        return task

    def focus_on(
        self,
        task_id: str
    ):
        """Focus attention on a task."""
        task = self._tasks.get(task_id)
        if task:
            self._current_state.current_focus = task
            self._current_state.attention_state = AttentionState.FOCUSED

    def divide_attention(
        self,
        task_ids: List[str]
    ):
        """Divide attention across tasks."""
        tasks = [self._tasks[tid] for tid in task_ids if tid in self._tasks]

        self._current_state.active_tasks = tasks
        self._current_state.attention_state = AttentionState.DIVIDED

        # Calculate load
        total_demand = sum(t.difficulty for t in tasks)

        if total_demand < 0.5:
            self._current_state.load_level = LoadLevel.LOW
        elif total_demand < 0.8:
            self._current_state.load_level = LoadLevel.MEDIUM
        elif total_demand < 1.0:
            self._current_state.load_level = LoadLevel.HIGH
        else:
            self._current_state.load_level = LoadLevel.OVERLOAD

    def switch_task(
        self,
        new_task_id: str,
        prep_time_ms: float = 0
    ) -> ExecutiveResult:
        """Switch to a new task."""
        new_task = self._tasks.get(new_task_id)
        if not new_task:
            return None

        old_task = self._current_state.current_focus
        is_switch = old_task is not None and old_task.id != new_task_id

        # Calculate switch cost
        switch_cost = 0
        if is_switch:
            similarity = 0.5  # Default similarity
            switch_cost = self._model.calculate_switch_cost(prep_time_ms, similarity)

        # Update state
        self._current_state.current_focus = new_task
        self._current_state.attention_state = AttentionState.SWITCHING if is_switch else AttentionState.FOCUSED

        # Base RT + switch cost
        base_rt = 400 + new_task.difficulty * 200
        rt = base_rt + switch_cost + random.uniform(-50, 50)

        result = ExecutiveResult(
            task_id=new_task_id,
            function_used=ExecutiveFunction.SWITCH,
            response_time_ms=rt,
            accuracy=0.95 - switch_cost / 1000,
            switch_cost=switch_cost,
            mixing_cost=0
        )

        self._results.append(result)

        return result

    def run_stroop(
        self,
        congruent: bool,
        inhibition_ability: float = 0.5
    ) -> ExecutiveResult:
        """Run a Stroop trial."""
        stroop_effect = self._model.calculate_stroop_effect(congruent, inhibition_ability)

        base_rt = 500
        rt = base_rt + stroop_effect + random.uniform(-40, 40)

        # Accuracy lower for incongruent
        if congruent:
            accuracy = 0.98
        else:
            accuracy = 0.92 + inhibition_ability * 0.05

        result = ExecutiveResult(
            task_id=self._generate_id(),
            function_used=ExecutiveFunction.INHIBIT,
            response_time_ms=max(200, rt),
            accuracy=accuracy,
            switch_cost=0,
            mixing_cost=0
        )

        self._results.append(result)

        return result

    def run_nback(
        self,
        n: int
    ) -> ExecutiveResult:
        """Run an n-back trial."""
        accuracy = self._model.calculate_nback_accuracy(n)

        # RT increases with N
        rt = 400 + n * self._model._update_cost + random.uniform(-50, 50)

        result = ExecutiveResult(
            task_id=self._generate_id(),
            function_used=ExecutiveFunction.UPDATE,
            response_time_ms=rt,
            accuracy=accuracy,
            switch_cost=0,
            mixing_cost=0
        )

        self._results.append(result)

        return result


# ============================================================================
# CENTRAL EXECUTIVE PARADIGM
# ============================================================================

class CentralExecutiveParadigm:
    """
    Central executive paradigm.

    "Ba'el's executive study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_task_switching_paradigm(
        self,
        n_trials: int = 48
    ) -> Dict[str, Any]:
        """Run task-switching paradigm."""
        system = CentralExecutiveSystem()

        # Create two tasks
        task_a = system.create_task("Task A", TaskType.TASK_SWITCH, 0.5)
        task_b = system.create_task("Task B", TaskType.TASK_SWITCH, 0.5)

        switch_rts = []
        repeat_rts = []

        current_task = task_a

        for i in range(n_trials):
            # Determine if switch
            if random.random() < 0.5:
                next_task = task_b if current_task == task_a else task_a
            else:
                next_task = current_task

            result = system.switch_task(next_task.id)

            if result.switch_cost > 0:
                switch_rts.append(result.response_time_ms)
            else:
                repeat_rts.append(result.response_time_ms)

            current_task = next_task

        switch_mean = sum(switch_rts) / max(1, len(switch_rts))
        repeat_mean = sum(repeat_rts) / max(1, len(repeat_rts))

        return {
            'switch_rt': switch_mean,
            'repeat_rt': repeat_mean,
            'switch_cost': switch_mean - repeat_mean,
            'interpretation': 'Switch trials slower than repeat trials'
        }

    def run_stroop_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run Stroop paradigm."""
        system = CentralExecutiveSystem()

        conditions = {
            'congruent': True,
            'incongruent': False
        }

        results = {}

        for condition, congruent in conditions.items():
            rts = []
            accuracies = []

            for _ in range(30):
                result = system.run_stroop(congruent)
                rts.append(result.response_time_ms)
                accuracies.append(result.accuracy)

            results[condition] = {
                'mean_rt': sum(rts) / len(rts),
                'accuracy': sum(accuracies) / len(accuracies)
            }

        stroop_effect = results['incongruent']['mean_rt'] - results['congruent']['mean_rt']

        return {
            'by_condition': results,
            'stroop_effect': stroop_effect,
            'interpretation': f'Stroop effect: {stroop_effect:.0f}ms'
        }

    def run_nback_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run n-back paradigm."""
        system = CentralExecutiveSystem()

        results = {}

        for n in [1, 2, 3]:
            rts = []
            accuracies = []

            for _ in range(30):
                result = system.run_nback(n)
                rts.append(result.response_time_ms)
                accuracies.append(result.accuracy)

            results[f"{n}-back"] = {
                'mean_rt': sum(rts) / len(rts),
                'accuracy': sum(accuracies) / len(accuracies)
            }

        return {
            'by_n': results,
            'interpretation': 'Accuracy and speed decrease with N'
        }

    def run_dual_task_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run dual-task paradigm."""
        model = CentralExecutiveModel()

        # Single vs dual task
        conditions = {
            'single_task': {'demand1': 0.5, 'demand2': 0.0},
            'dual_easy': {'demand1': 0.3, 'demand2': 0.3},
            'dual_hard': {'demand1': 0.5, 'demand2': 0.5}
        }

        results = {}

        for condition, params in conditions.items():
            cost1, cost2 = model.calculate_dual_task_cost(
                params['demand1'], params['demand2']
            )

            results[condition] = {
                'task1_cost': cost1,
                'task2_cost': cost2,
                'total_cost': cost1 + cost2
            }

        return {
            'by_condition': results,
            'interpretation': 'Dual-task costs increase with demand'
        }

    def run_random_generation_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run random generation paradigm."""
        model = CentralExecutiveModel()

        results = {}

        for load in [0.0, 0.3, 0.6]:
            quality = model.calculate_random_generation_quality(
                sequence_length=50,
                concurrent_load=load
            )

            results[f"load_{load}"] = {
                'randomness_quality': quality
            }

        return {
            'by_load': results,
            'interpretation': 'Concurrent load reduces randomness quality'
        }

    def run_preparation_effect_study(
        self
    ) -> Dict[str, Any]:
        """Study preparation time effects on switching."""
        model = CentralExecutiveModel()

        results = {}

        for prep_time in [0, 100, 300, 500, 1000]:
            cost = model.calculate_switch_cost(prep_time, task_similarity=0.5)

            results[f"prep_{prep_time}ms"] = {
                'switch_cost': cost
            }

        return {
            'by_prep_time': results,
            'interpretation': 'Preparation reduces switch cost'
        }


# ============================================================================
# CENTRAL EXECUTIVE ENGINE
# ============================================================================

class CentralExecutiveEngine:
    """
    Complete central executive engine.

    "Ba'el's executive engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = CentralExecutiveParadigm()
        self._system = CentralExecutiveSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Task operations

    def create_task(
        self,
        name: str,
        task_type: TaskType
    ) -> Task:
        """Create task."""
        return self._system.create_task(name, task_type)

    def switch_to(
        self,
        task_id: str
    ) -> ExecutiveResult:
        """Switch to task."""
        return self._system.switch_task(task_id)

    def run_stroop(
        self,
        congruent: bool
    ) -> ExecutiveResult:
        """Run Stroop trial."""
        return self._system.run_stroop(congruent)

    def run_nback(
        self,
        n: int
    ) -> ExecutiveResult:
        """Run n-back trial."""
        return self._system.run_nback(n)

    # Experiments

    def run_switching(
        self
    ) -> Dict[str, Any]:
        """Run task-switching paradigm."""
        result = self._paradigm.run_task_switching_paradigm()
        self._experiment_results.append(result)
        return result

    def run_stroop_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run Stroop paradigm."""
        return self._paradigm.run_stroop_paradigm()

    def run_nback_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run n-back paradigm."""
        return self._paradigm.run_nback_paradigm()

    def run_dual_task(
        self
    ) -> Dict[str, Any]:
        """Run dual-task paradigm."""
        return self._paradigm.run_dual_task_paradigm()

    def run_random_generation(
        self
    ) -> Dict[str, Any]:
        """Run random generation."""
        return self._paradigm.run_random_generation_paradigm()

    def study_preparation(
        self
    ) -> Dict[str, Any]:
        """Study preparation effects."""
        return self._paradigm.run_preparation_effect_study()

    # Analysis

    def get_metrics(self) -> ExecutiveMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_switching()

        last = self._experiment_results[-1]

        return ExecutiveMetrics(
            switch_cost=last['switch_cost'],
            mixing_cost=50,
            dual_task_cost=100,
            inhibition_efficiency=0.7,
            updating_accuracy=0.85
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'tasks': len(self._system._tasks),
            'results': len(self._system._results),
            'attention': self._system._current_state.attention_state.name
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_central_executive_engine() -> CentralExecutiveEngine:
    """Create central executive engine."""
    return CentralExecutiveEngine()


def demonstrate_central_executive() -> Dict[str, Any]:
    """Demonstrate central executive."""
    engine = create_central_executive_engine()

    # Task switching
    switching = engine.run_switching()

    # Stroop
    stroop = engine.run_stroop_paradigm()

    # N-back
    nback = engine.run_nback_paradigm()

    # Dual task
    dual = engine.run_dual_task()

    return {
        'task_switching': {
            'switch_rt': f"{switching['switch_rt']:.0f}ms",
            'repeat_rt': f"{switching['repeat_rt']:.0f}ms",
            'cost': f"{switching['switch_cost']:.0f}ms"
        },
        'stroop': {
            'effect': f"{stroop['stroop_effect']:.0f}ms"
        },
        'nback': {
            k: f"acc: {v['accuracy']:.0%}"
            for k, v in nback['by_n'].items()
        },
        'dual_task': {
            k: f"cost: {v['total_cost']:.0f}ms"
            for k, v in dual['by_condition'].items()
        },
        'interpretation': (
            f"Switch cost: {switching['switch_cost']:.0f}ms. "
            f"Stroop effect: {stroop['stroop_effect']:.0f}ms. "
            f"Executive control manages attention, switching, inhibition."
        )
    }


def get_central_executive_facts() -> Dict[str, str]:
    """Get facts about central executive."""
    return {
        'baddeley_1974': 'Working memory model - central executive',
        'functions': 'Focus, divide, switch, update, inhibit',
        'switch_cost': '~150ms slower on switch trials',
        'stroop_effect': '~100ms interference',
        'nback': 'Working memory updating task',
        'dual_task': 'Bottleneck with high demands',
        'frontal_lobe': 'Prefrontal cortex involvement',
        'individual_differences': 'Related to fluid intelligence'
    }
