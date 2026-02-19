"""
BAEL Divided Attention Engine
================================

Multitasking and attention switching.
Bottleneck and resource theories.

"Ba'el divides focus." — Ba'el
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

logger = logging.getLogger("BAEL.DividedAttention")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TaskType(Enum):
    """Types of tasks."""
    PERCEPTUAL = auto()       # Visual, auditory
    COGNITIVE = auto()        # Thinking, deciding
    MOTOR = auto()            # Physical response
    VERBAL = auto()           # Language processing
    SPATIAL = auto()          # Spatial processing


class BottleneckType(Enum):
    """Types of processing bottlenecks."""
    EARLY = auto()            # Broadbent's filter
    LATE = auto()             # Late selection
    RESPONSE = auto()         # Response selection (PRP)
    CENTRAL = auto()          # Central executive


class ResourceType(Enum):
    """Types of processing resources."""
    GENERAL = auto()          # Domain-general
    VISUAL = auto()           # Visual processing
    AUDITORY = auto()         # Auditory processing
    VERBAL = auto()           # Verbal codes
    SPATIAL = auto()          # Spatial codes
    RESPONSE = auto()         # Response generation


class SwitchCost(Enum):
    """Types of switch costs."""
    RESTART = auto()          # Task-set reconfiguration
    PROACTIVE = auto()        # Preparation costs
    RESIDUAL = auto()         # Remaining costs


@dataclass
class Task:
    """
    A task requiring attention.
    """
    id: str
    name: str
    task_type: TaskType
    difficulty: float
    resources_required: Dict[ResourceType, float]
    processing_time: float  # ms


@dataclass
class TaskPerformance:
    """
    Performance on a task.
    """
    task_id: str
    accuracy: float
    response_time: float
    resources_available: float
    bottleneck_delay: float


@dataclass
class DualTaskResult:
    """
    Result of dual-task performance.
    """
    task1_performance: TaskPerformance
    task2_performance: TaskPerformance
    soa: float  # Stimulus onset asynchrony
    prp_effect: float  # Psychological refractory period


@dataclass
class SwitchResult:
    """
    Result of task switching.
    """
    task_from: str
    task_to: str
    switch_cost: float
    mixing_cost: float
    preparation_benefit: float


@dataclass
class DividedAttentionMetrics:
    """
    Divided attention metrics.
    """
    dual_task_cost: float
    switch_cost: float
    resource_efficiency: float
    bottleneck_severity: float


# ============================================================================
# RESOURCE POOL
# ============================================================================

class ResourcePool:
    """
    Multiple resource pools.

    "Ba'el's resource theory." — Ba'el
    """

    def __init__(
        self,
        general_capacity: float = 1.0
    ):
        """Initialize resource pool."""
        self._resources: Dict[ResourceType, float] = {
            ResourceType.GENERAL: general_capacity,
            ResourceType.VISUAL: 1.0,
            ResourceType.AUDITORY: 1.0,
            ResourceType.VERBAL: 1.0,
            ResourceType.SPATIAL: 1.0,
            ResourceType.RESPONSE: 1.0
        }

        self._current_allocation: Dict[str, Dict[ResourceType, float]] = {}

        self._lock = threading.RLock()

    def get_available(
        self,
        resource_type: ResourceType
    ) -> float:
        """Get available resources."""
        allocated = sum(
            alloc.get(resource_type, 0)
            for alloc in self._current_allocation.values()
        )
        return max(0, self._resources[resource_type] - allocated)

    def allocate(
        self,
        task_id: str,
        requirements: Dict[ResourceType, float]
    ) -> Dict[ResourceType, float]:
        """Allocate resources to task."""
        allocation = {}

        for resource_type, required in requirements.items():
            available = self.get_available(resource_type)
            allocation[resource_type] = min(required, available)

        self._current_allocation[task_id] = allocation
        return allocation

    def release(
        self,
        task_id: str
    ) -> None:
        """Release task resources."""
        if task_id in self._current_allocation:
            del self._current_allocation[task_id]

    def calculate_interference(
        self,
        task1_resources: Dict[ResourceType, float],
        task2_resources: Dict[ResourceType, float]
    ) -> float:
        """Calculate resource interference between tasks."""
        total_overlap = 0.0
        count = 0

        for resource_type in task1_resources:
            if resource_type in task2_resources:
                # Both tasks need this resource
                r1 = task1_resources[resource_type]
                r2 = task2_resources[resource_type]
                capacity = self._resources[resource_type]

                demand = r1 + r2
                if demand > capacity:
                    # Interference proportional to overdemand
                    total_overlap += (demand - capacity) / capacity

                count += 1

        return total_overlap / count if count > 0 else 0.0


# ============================================================================
# BOTTLENECK MODEL
# ============================================================================

class BottleneckModel:
    """
    Processing bottleneck model.

    "Ba'el's single channel." — Ba'el
    """

    def __init__(
        self,
        bottleneck_type: BottleneckType = BottleneckType.RESPONSE
    ):
        """Initialize bottleneck model."""
        self._bottleneck_type = bottleneck_type
        self._bottleneck_busy = False
        self._busy_until = 0.0

        self._lock = threading.RLock()

    def process_task(
        self,
        task: Task,
        start_time: float
    ) -> Tuple[float, float]:
        """Process task through bottleneck."""
        # Pre-bottleneck processing (parallel)
        pre_bottleneck = task.processing_time * 0.3

        # Bottleneck processing (serial)
        bottleneck_start = max(start_time + pre_bottleneck, self._busy_until)
        bottleneck_duration = task.processing_time * 0.4

        self._busy_until = bottleneck_start + bottleneck_duration

        # Post-bottleneck processing (parallel)
        post_bottleneck = task.processing_time * 0.3

        total_time = (
            bottleneck_start - start_time +
            bottleneck_duration +
            post_bottleneck
        )

        bottleneck_delay = max(0, bottleneck_start - start_time - pre_bottleneck)

        return total_time, bottleneck_delay

    def calculate_prp(
        self,
        task1: Task,
        task2: Task,
        soa: float
    ) -> Tuple[float, float, float]:
        """Calculate psychological refractory period."""
        # Task 1 starts at time 0
        t1_start = 0.0
        t1_time, _ = self.process_task(task1, t1_start)

        # Task 2 starts at SOA
        t2_start = soa
        t2_time, t2_delay = self.process_task(task2, t2_start)

        # PRP effect is the delay for task 2 at short SOAs
        # At long SOAs, bottleneck is free
        prp_effect = t2_delay

        return t1_time, t2_time, prp_effect

    def reset(self) -> None:
        """Reset bottleneck state."""
        self._busy_until = 0.0


# ============================================================================
# TASK SWITCHER
# ============================================================================

class TaskSwitcher:
    """
    Task switching model.

    "Ba'el changes sets." — Ba'el
    """

    def __init__(
        self,
        base_switch_cost: float = 200.0  # ms
    ):
        """Initialize switcher."""
        self._base_switch_cost = base_switch_cost
        self._current_task_set: Optional[str] = None

        # Task set strength
        self._task_set_strength: Dict[str, float] = defaultdict(float)

        # Preparation
        self._preparation_time = 0.0
        self._max_preparation_benefit = 0.6  # Max reduction from prep

        self._lock = threading.RLock()

    def set_current_task(
        self,
        task_id: str
    ) -> None:
        """Set current task set."""
        self._current_task_set = task_id
        self._task_set_strength[task_id] = 1.0

    def prepare_for_switch(
        self,
        next_task_id: str,
        preparation_time: float
    ) -> float:
        """Prepare for task switch."""
        # Preparation reduces switch cost
        max_prep = 500  # ms
        prep_ratio = min(1.0, preparation_time / max_prep)

        benefit = self._max_preparation_benefit * prep_ratio
        self._preparation_time = preparation_time

        return benefit

    def switch_to(
        self,
        task_id: str,
        prepared: bool = False
    ) -> SwitchResult:
        """Switch to a new task."""
        from_task = self._current_task_set

        if from_task is None:
            # First task, no switch cost
            self._current_task_set = task_id
            self._task_set_strength[task_id] = 1.0

            return SwitchResult(
                task_from="none",
                task_to=task_id,
                switch_cost=0.0,
                mixing_cost=0.0,
                preparation_benefit=0.0
            )

        if from_task == task_id:
            # No switch needed
            return SwitchResult(
                task_from=from_task,
                task_to=task_id,
                switch_cost=0.0,
                mixing_cost=0.0,
                preparation_benefit=0.0
            )

        # Calculate switch cost
        switch_cost = self._base_switch_cost

        # Preparation benefit
        prep_benefit = 0.0
        if prepared:
            prep_benefit = switch_cost * self._max_preparation_benefit
            switch_cost -= prep_benefit

        # Residual cost (not eliminated by preparation)
        residual = self._base_switch_cost * 0.2
        switch_cost = max(residual, switch_cost)

        # Mixing cost (cost of being in mixed-task context)
        mixing_cost = self._base_switch_cost * 0.3

        # Update task sets
        self._task_set_strength[from_task] *= 0.5  # Decay
        self._current_task_set = task_id
        self._task_set_strength[task_id] = 1.0

        return SwitchResult(
            task_from=from_task,
            task_to=task_id,
            switch_cost=switch_cost,
            mixing_cost=mixing_cost,
            preparation_benefit=prep_benefit
        )


# ============================================================================
# DIVIDED ATTENTION ENGINE
# ============================================================================

class DividedAttentionEngine:
    """
    Complete divided attention engine.

    "Ba'el's multitasking." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._resource_pool = ResourcePool()
        self._bottleneck = BottleneckModel()
        self._switcher = TaskSwitcher()

        self._tasks: Dict[str, Task] = {}
        self._performance_history: List[TaskPerformance] = []
        self._dual_task_results: List[DualTaskResult] = []
        self._switch_results: List[SwitchResult] = []

        self._task_counter = 0

        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter}"

    # Task creation

    def create_task(
        self,
        name: str,
        task_type: TaskType,
        difficulty: float = 0.5,
        processing_time: float = 300.0  # ms
    ) -> Task:
        """Create a task."""
        # Default resource requirements based on type
        resources = {ResourceType.GENERAL: difficulty * 0.5}

        if task_type == TaskType.PERCEPTUAL:
            resources[ResourceType.VISUAL] = 0.3
        elif task_type == TaskType.VERBAL:
            resources[ResourceType.VERBAL] = 0.4
        elif task_type == TaskType.SPATIAL:
            resources[ResourceType.SPATIAL] = 0.4
        elif task_type == TaskType.MOTOR:
            resources[ResourceType.RESPONSE] = 0.3
        elif task_type == TaskType.COGNITIVE:
            resources[ResourceType.GENERAL] = difficulty * 0.7

        task = Task(
            id=self._generate_id(),
            name=name,
            task_type=task_type,
            difficulty=difficulty,
            resources_required=resources,
            processing_time=processing_time
        )

        self._tasks[task.id] = task
        return task

    # Single task performance

    def perform_single_task(
        self,
        task: Task
    ) -> TaskPerformance:
        """Perform a single task."""
        # Full resources available
        allocation = self._resource_pool.allocate(
            task.id, task.resources_required
        )

        # Calculate performance
        resource_ratio = sum(allocation.values()) / sum(task.resources_required.values())

        accuracy = 0.95 * resource_ratio
        rt = task.processing_time * (1 + (1 - resource_ratio) * 0.5)

        self._resource_pool.release(task.id)

        performance = TaskPerformance(
            task_id=task.id,
            accuracy=accuracy,
            response_time=rt,
            resources_available=resource_ratio,
            bottleneck_delay=0.0
        )

        self._performance_history.append(performance)
        return performance

    # Dual task performance

    def perform_dual_task(
        self,
        task1: Task,
        task2: Task,
        soa: float = 0.0
    ) -> DualTaskResult:
        """Perform two tasks together."""
        self._bottleneck.reset()

        # Calculate interference
        interference = self._resource_pool.calculate_interference(
            task1.resources_required,
            task2.resources_required
        )

        # Bottleneck effects
        t1_time, t2_time, prp = self._bottleneck.calculate_prp(
            task1, task2, soa
        )

        # Resource-based performance degradation
        degradation1 = 1.0 / (1 + interference * 0.5)
        degradation2 = 1.0 / (1 + interference * 0.5 + prp / 200)

        perf1 = TaskPerformance(
            task_id=task1.id,
            accuracy=0.95 * degradation1,
            response_time=t1_time,
            resources_available=degradation1,
            bottleneck_delay=0.0
        )

        perf2 = TaskPerformance(
            task_id=task2.id,
            accuracy=0.95 * degradation2,
            response_time=t2_time,
            resources_available=degradation2,
            bottleneck_delay=prp
        )

        result = DualTaskResult(
            task1_performance=perf1,
            task2_performance=perf2,
            soa=soa,
            prp_effect=prp
        )

        self._dual_task_results.append(result)
        self._performance_history.extend([perf1, perf2])

        return result

    def run_prp_experiment(
        self,
        task1: Task,
        task2: Task,
        soas: List[float]
    ) -> Dict[str, List[float]]:
        """Run PRP experiment with multiple SOAs."""
        rt1s = []
        rt2s = []
        prps = []

        for soa in soas:
            self._bottleneck.reset()
            result = self.perform_dual_task(task1, task2, soa)

            rt1s.append(result.task1_performance.response_time)
            rt2s.append(result.task2_performance.response_time)
            prps.append(result.prp_effect)

        return {
            'soas': soas,
            'rt1': rt1s,
            'rt2': rt2s,
            'prp_effects': prps
        }

    # Task switching

    def switch_tasks(
        self,
        from_task: Task,
        to_task: Task,
        preparation_time: float = 0.0
    ) -> SwitchResult:
        """Switch from one task to another."""
        # Set current task if not set
        if self._switcher._current_task_set != from_task.id:
            self._switcher.set_current_task(from_task.id)

        # Prepare if time given
        prepared = False
        if preparation_time > 0:
            self._switcher.prepare_for_switch(to_task.id, preparation_time)
            prepared = True

        result = self._switcher.switch_to(to_task.id, prepared=prepared)
        self._switch_results.append(result)

        return result

    def run_switching_block(
        self,
        task_a: Task,
        task_b: Task,
        sequence: List[str],  # 'A' or 'B'
        cue_switch_interval: float = 0.0
    ) -> Dict[str, Any]:
        """Run a block of task switching."""
        switch_rts = []
        repeat_rts = []

        current_task = None

        for trial_type in sequence:
            target_task = task_a if trial_type == 'A' else task_b

            if current_task is None:
                # First trial
                result = self._switcher.switch_to(target_task.id)
                current_task = target_task
                repeat_rts.append(target_task.processing_time)
            elif current_task.id == target_task.id:
                # Repeat trial
                repeat_rts.append(target_task.processing_time)
            else:
                # Switch trial
                result = self.switch_tasks(
                    current_task, target_task,
                    cue_switch_interval
                )
                switch_rt = target_task.processing_time + result.switch_cost
                switch_rts.append(switch_rt)
                current_task = target_task

        return {
            'switch_trials': len(switch_rts),
            'repeat_trials': len(repeat_rts),
            'mean_switch_rt': sum(switch_rts) / len(switch_rts) if switch_rts else 0,
            'mean_repeat_rt': sum(repeat_rts) / len(repeat_rts) if repeat_rts else 0,
            'switch_cost': (
                (sum(switch_rts) / len(switch_rts)) -
                (sum(repeat_rts) / len(repeat_rts))
            ) if switch_rts and repeat_rts else 0
        }

    # Analysis

    def calculate_dual_task_cost(self) -> float:
        """Calculate overall dual-task cost."""
        if not self._dual_task_results:
            return 0.0

        total_cost = 0.0
        for result in self._dual_task_results:
            # Cost in accuracy and RT
            cost1 = 1 - result.task1_performance.accuracy
            cost2 = 1 - result.task2_performance.accuracy
            total_cost += (cost1 + cost2) / 2

        return total_cost / len(self._dual_task_results)

    def calculate_switch_cost(self) -> float:
        """Calculate average switch cost."""
        costs = [r.switch_cost for r in self._switch_results if r.switch_cost > 0]
        return sum(costs) / len(costs) if costs else 0.0

    def get_metrics(self) -> DividedAttentionMetrics:
        """Get divided attention metrics."""
        dual_task_cost = self.calculate_dual_task_cost()
        switch_cost = self.calculate_switch_cost()

        # Resource efficiency
        if self._performance_history:
            avg_resources = sum(
                p.resources_available
                for p in self._performance_history
            ) / len(self._performance_history)
        else:
            avg_resources = 1.0

        # Bottleneck severity
        if self._dual_task_results:
            avg_prp = sum(
                r.prp_effect for r in self._dual_task_results
            ) / len(self._dual_task_results)
            bottleneck_severity = min(1.0, avg_prp / 300)
        else:
            bottleneck_severity = 0.0

        return DividedAttentionMetrics(
            dual_task_cost=dual_task_cost,
            switch_cost=switch_cost,
            resource_efficiency=avg_resources,
            bottleneck_severity=bottleneck_severity
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'tasks': len(self._tasks),
            'performance_records': len(self._performance_history),
            'dual_task_trials': len(self._dual_task_results),
            'switch_trials': len(self._switch_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_divided_attention_engine() -> DividedAttentionEngine:
    """Create divided attention engine."""
    return DividedAttentionEngine()


def demonstrate_divided_attention() -> Dict[str, Any]:
    """Demonstrate divided attention."""
    engine = create_divided_attention_engine()

    # Create tasks
    visual_task = engine.create_task("Visual", TaskType.PERCEPTUAL, 0.5, 300)
    auditory_task = engine.create_task("Auditory", TaskType.COGNITIVE, 0.5, 350)

    # Single task performance
    single_visual = engine.perform_single_task(visual_task)
    single_auditory = engine.perform_single_task(auditory_task)

    # PRP experiment
    soas = [50, 100, 200, 400, 800]
    prp_result = engine.run_prp_experiment(visual_task, auditory_task, soas)

    # Task switching
    switching = engine.run_switching_block(
        visual_task, auditory_task,
        ['A', 'A', 'B', 'A', 'B', 'B', 'A', 'B'],
        cue_switch_interval=200
    )

    metrics = engine.get_metrics()

    return {
        'single_task': {
            'visual_rt': single_visual.response_time,
            'auditory_rt': single_auditory.response_time
        },
        'prp_experiment': {
            'soas': prp_result['soas'],
            'prp_at_50ms': prp_result['prp_effects'][0],
            'prp_at_800ms': prp_result['prp_effects'][-1]
        },
        'task_switching': {
            'switch_cost': switching['switch_cost'],
            'mean_switch_rt': switching['mean_switch_rt'],
            'mean_repeat_rt': switching['mean_repeat_rt']
        },
        'interpretation': (
            f"PRP: {prp_result['prp_effects'][0]:.0f}ms at short SOA, "
            f"Switch cost: {switching['switch_cost']:.0f}ms"
        )
    }


def get_divided_attention_facts() -> Dict[str, str]:
    """Get facts about divided attention."""
    return {
        'prp': 'Psychological refractory period - bottleneck in response selection',
        'wickens_resources': 'Multiple resource theory - separate pools',
        'switch_cost': 'Time cost of task-set reconfiguration',
        'mixing_cost': 'Cost of being in mixed-task context',
        'preparation': 'Advance preparation can reduce switch costs',
        'residual_cost': 'Switch cost not eliminated by preparation',
        'bottleneck': 'Serial processing stage limits parallel processing',
        'practice': 'Automaticity can reduce dual-task interference'
    }
