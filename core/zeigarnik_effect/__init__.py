"""
BAEL Zeigarnik Effect Engine
==============================

Enhanced memory for incomplete tasks.
Zeigarnik's unfinished task phenomenon.

"Ba'el never forgets the unfinished." — Ba'el
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

logger = logging.getLogger("BAEL.ZeigarnikEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TaskStatus(Enum):
    """Status of a task."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    INTERRUPTED = auto()
    COMPLETED = auto()


class TaskComplexity(Enum):
    """Complexity of task."""
    SIMPLE = auto()
    MODERATE = auto()
    COMPLEX = auto()


class InterruptionType(Enum):
    """How task was interrupted."""
    NATURAL_BREAK = auto()
    FORCED_STOP = auto()
    TIME_LIMIT = auto()
    EXTERNAL = auto()


class MotivationType(Enum):
    """Task motivation level."""
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()


@dataclass
class Task:
    """
    A task that can be completed or interrupted.
    """
    id: str
    name: str
    complexity: TaskComplexity
    status: TaskStatus
    progress: float  # 0-1
    motivation: MotivationType
    time_on_task: float  # seconds


@dataclass
class TaskMemory:
    """
    Memory for a task.
    """
    task_id: str
    status: TaskStatus
    encoding_strength: float
    recall_probability: float


@dataclass
class RecallResult:
    """
    Result of task recall.
    """
    task_id: str
    status: TaskStatus
    recalled: bool
    recall_order: int


@dataclass
class ZeigarnikMetrics:
    """
    Zeigarnik effect metrics.
    """
    completed_recall: float
    interrupted_recall: float
    zeigarnik_ratio: float
    effect_magnitude: float


# ============================================================================
# TENSION SYSTEM MODEL
# ============================================================================

class TensionSystemModel:
    """
    Lewin's tension system model of memory for incomplete tasks.

    "Ba'el's unfinished tension." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Tension parameters
        self._base_tension = 0.3
        self._incomplete_tension_boost = 0.4
        self._completion_tension_release = 0.6

        # Memory parameters
        self._tension_to_memory = 0.5
        self._base_encoding = 0.4

        # Task factors
        self._complexity_factors = {
            TaskComplexity.SIMPLE: 0.8,
            TaskComplexity.MODERATE: 1.0,
            TaskComplexity.COMPLEX: 1.2
        }

        self._motivation_factors = {
            MotivationType.LOW: 0.7,
            MotivationType.MODERATE: 1.0,
            MotivationType.HIGH: 1.3
        }

        self._lock = threading.RLock()

    def calculate_tension(
        self,
        task: Task
    ) -> float:
        """Calculate psychological tension for a task."""
        if task.status == TaskStatus.COMPLETED:
            # Tension released
            return self._base_tension * (1 - self._completion_tension_release)

        elif task.status == TaskStatus.INTERRUPTED:
            # High tension for interrupted tasks
            base = self._base_tension + self._incomplete_tension_boost

            # More progress = more tension (investment)
            progress_factor = task.progress * 0.3

            return min(0.95, base + progress_factor)

        elif task.status == TaskStatus.IN_PROGRESS:
            return self._base_tension + self._incomplete_tension_boost * 0.7

        else:
            return self._base_tension

    def calculate_memory_strength(
        self,
        task: Task
    ) -> float:
        """Calculate memory encoding strength."""
        tension = self.calculate_tension(task)

        # Tension drives memory encoding
        encoding = self._base_encoding + tension * self._tension_to_memory

        # Complexity factor
        complexity = self._complexity_factors.get(task.complexity, 1.0)

        # Motivation factor
        motivation = self._motivation_factors.get(task.motivation, 1.0)

        strength = encoding * complexity * motivation

        return min(0.95, max(0.1, strength))

    def calculate_recall_probability(
        self,
        memory: TaskMemory
    ) -> float:
        """Calculate probability of recalling a task."""
        # Base on encoding strength
        prob = memory.encoding_strength

        # Interrupted tasks have advantage
        if memory.status == TaskStatus.INTERRUPTED:
            prob *= 1.3
        elif memory.status == TaskStatus.COMPLETED:
            prob *= 0.8

        return min(0.95, max(0.1, prob))


# ============================================================================
# ZEIGARNIK EFFECT SYSTEM
# ============================================================================

class ZeigarnikEffectSystem:
    """
    Zeigarnik effect experimental system.

    "Ba'el's incomplete task memory." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = TensionSystemModel()

        self._tasks: Dict[str, Task] = {}
        self._memories: Dict[str, TaskMemory] = {}
        self._recalls: List[RecallResult] = []

        self._task_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter}"

    def create_task(
        self,
        name: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        motivation: MotivationType = MotivationType.MODERATE
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=self._generate_id(),
            name=name,
            complexity=complexity,
            status=TaskStatus.NOT_STARTED,
            progress=0.0,
            motivation=motivation,
            time_on_task=0.0
        )

        self._tasks[task.id] = task

        return task

    def start_task(
        self,
        task_id: str
    ) -> Task:
        """Start a task."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.IN_PROGRESS
        return task

    def work_on_task(
        self,
        task_id: str,
        time_seconds: float,
        progress_amount: float
    ) -> Task:
        """Work on a task."""
        task = self._tasks.get(task_id)
        if task:
            task.time_on_task += time_seconds
            task.progress = min(1.0, task.progress + progress_amount)

            if task.progress >= 1.0:
                task.status = TaskStatus.COMPLETED

        return task

    def interrupt_task(
        self,
        task_id: str,
        interruption: InterruptionType = InterruptionType.FORCED_STOP
    ) -> Task:
        """Interrupt a task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.IN_PROGRESS:
            task.status = TaskStatus.INTERRUPTED

            # Create memory
            strength = self._model.calculate_memory_strength(task)

            memory = TaskMemory(
                task_id=task_id,
                status=TaskStatus.INTERRUPTED,
                encoding_strength=strength,
                recall_probability=self._model.calculate_recall_probability(
                    TaskMemory(task_id, TaskStatus.INTERRUPTED, strength, 0)
                )
            )
            self._memories[task_id] = memory

        return task

    def complete_task(
        self,
        task_id: str
    ) -> Task:
        """Complete a task."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0

            # Create memory
            strength = self._model.calculate_memory_strength(task)

            memory = TaskMemory(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                encoding_strength=strength,
                recall_probability=self._model.calculate_recall_probability(
                    TaskMemory(task_id, TaskStatus.COMPLETED, strength, 0)
                )
            )
            self._memories[task_id] = memory

        return task

    def recall_tasks(
        self
    ) -> List[RecallResult]:
        """Attempt to recall all tasks."""
        results = []
        recall_order = 0

        # Sort by recall probability (for order)
        sorted_memories = sorted(
            self._memories.values(),
            key=lambda m: m.recall_probability,
            reverse=True
        )

        for memory in sorted_memories:
            recalled = random.random() < memory.recall_probability

            if recalled:
                recall_order += 1
                result = RecallResult(
                    task_id=memory.task_id,
                    status=memory.status,
                    recalled=True,
                    recall_order=recall_order
                )
            else:
                result = RecallResult(
                    task_id=memory.task_id,
                    status=memory.status,
                    recalled=False,
                    recall_order=0
                )

            results.append(result)
            self._recalls.append(result)

        return results


# ============================================================================
# ZEIGARNIK PARADIGM
# ============================================================================

class ZeigarnikParadigm:
    """
    Zeigarnik effect experimental paradigm.

    "Ba'el's incomplete task study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_experiment(
        self,
        n_tasks: int = 20
    ) -> Dict[str, Any]:
        """Run classic Zeigarnik experiment."""
        system = ZeigarnikEffectSystem()

        # Create tasks
        completed_tasks = []
        interrupted_tasks = []

        for i in range(n_tasks):
            task = system.create_task(f"task_{i}")
            system.start_task(task.id)

            # Work on task
            system.work_on_task(task.id, random.uniform(30, 120), random.uniform(0.3, 0.7))

            if i % 2 == 0:
                # Allow completion
                system.work_on_task(task.id, 60, 1.0)
                system.complete_task(task.id)
                completed_tasks.append(task.id)
            else:
                # Interrupt
                system.interrupt_task(task.id)
                interrupted_tasks.append(task.id)

        # Recall phase
        results = system.recall_tasks()

        completed_recalled = sum(1 for r in results
                                if r.task_id in completed_tasks and r.recalled)
        interrupted_recalled = sum(1 for r in results
                                  if r.task_id in interrupted_tasks and r.recalled)

        n_comp = len(completed_tasks)
        n_int = len(interrupted_tasks)

        completed_rate = completed_recalled / n_comp if n_comp > 0 else 0
        interrupted_rate = interrupted_recalled / n_int if n_int > 0 else 0

        return {
            'completed_recall': completed_rate,
            'interrupted_recall': interrupted_rate,
            'zeigarnik_ratio': interrupted_rate / completed_rate if completed_rate > 0 else 0,
            'effect_magnitude': interrupted_rate - completed_rate
        }

    def run_motivation_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare effect across motivation levels."""
        results = {}

        for motivation in MotivationType:
            system = ZeigarnikEffectSystem()

            completed = []
            interrupted = []

            for i in range(10):
                task = system.create_task(f"task_{i}", motivation=motivation)
                system.start_task(task.id)
                system.work_on_task(task.id, 60, 0.5)

                if i % 2 == 0:
                    system.complete_task(task.id)
                    completed.append(task.id)
                else:
                    system.interrupt_task(task.id)
                    interrupted.append(task.id)

            recalls = system.recall_tasks()

            comp_recalled = sum(1 for r in recalls if r.task_id in completed and r.recalled)
            int_recalled = sum(1 for r in recalls if r.task_id in interrupted and r.recalled)

            results[motivation.name] = {
                'completed': comp_recalled / 5,
                'interrupted': int_recalled / 5,
                'effect': (int_recalled - comp_recalled) / 5
            }

        return results

    def run_progress_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare effect by progress level when interrupted."""
        progress_levels = [0.2, 0.5, 0.8]
        results = {}

        for progress in progress_levels:
            system = ZeigarnikEffectSystem()

            tasks = []
            for i in range(10):
                task = system.create_task(f"task_{i}")
                system.start_task(task.id)
                system.work_on_task(task.id, 60, progress)
                system.interrupt_task(task.id)
                tasks.append(task.id)

            recalls = system.recall_tasks()
            recalled = sum(1 for r in recalls if r.recalled)

            results[f"progress_{progress}"] = recalled / 10

        return results

    def run_delay_effect(
        self
    ) -> Dict[str, Any]:
        """Test effect of delay on Zeigarnik effect."""
        # In original research, immediate recall showed larger effect
        # After delay, effect diminishes

        system = ZeigarnikEffectSystem()

        # Create tasks
        for i in range(10):
            task = system.create_task(f"task_{i}")
            system.start_task(task.id)
            system.work_on_task(task.id, 60, 0.5)

            if i % 2 == 0:
                system.complete_task(task.id)
            else:
                system.interrupt_task(task.id)

        # Immediate recall
        immediate_results = system.recall_tasks()
        immediate_int = sum(1 for r in immediate_results
                          if r.status == TaskStatus.INTERRUPTED and r.recalled)
        immediate_comp = sum(1 for r in immediate_results
                           if r.status == TaskStatus.COMPLETED and r.recalled)

        # Simulate delay effect (tension dissipates)
        delayed_int = immediate_int * 0.6
        delayed_comp = immediate_comp * 0.7

        return {
            'immediate_effect': (immediate_int - immediate_comp) / 5,
            'delayed_effect': (delayed_int - delayed_comp) / 5,
            'effect_decay': 'Zeigarnik effect diminishes with delay as tension dissipates'
        }


# ============================================================================
# ZEIGARNIK ENGINE
# ============================================================================

class ZeigarnikEffectEngine:
    """
    Complete Zeigarnik effect engine.

    "Ba'el's unfinished business engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ZeigarnikParadigm()
        self._system = ZeigarnikEffectSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Task management

    def create_task(
        self,
        name: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE
    ) -> Task:
        """Create a task."""
        return self._system.create_task(name, complexity)

    def start(
        self,
        task_id: str
    ) -> Task:
        """Start a task."""
        return self._system.start_task(task_id)

    def work(
        self,
        task_id: str,
        progress: float
    ) -> Task:
        """Work on a task."""
        return self._system.work_on_task(task_id, 60, progress)

    def interrupt(
        self,
        task_id: str
    ) -> Task:
        """Interrupt a task."""
        return self._system.interrupt_task(task_id)

    def complete(
        self,
        task_id: str
    ) -> Task:
        """Complete a task."""
        return self._system.complete_task(task_id)

    # Recall

    def recall(
        self
    ) -> List[RecallResult]:
        """Recall tasks."""
        return self._system.recall_tasks()

    # Experiments

    def run_classic_experiment(
        self,
        n_tasks: int = 20
    ) -> Dict[str, Any]:
        """Run classic experiment."""
        result = self._paradigm.run_classic_experiment(n_tasks)
        self._experiment_results.append(result)
        return result

    def run_motivation_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare motivation levels."""
        return self._paradigm.run_motivation_comparison()

    def run_progress_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare progress levels."""
        return self._paradigm.run_progress_comparison()

    def run_delay_test(
        self
    ) -> Dict[str, Any]:
        """Test delay effect."""
        return self._paradigm.run_delay_effect()

    def run_complexity_test(
        self
    ) -> Dict[str, Any]:
        """Test complexity effect."""
        results = {}

        for complexity in TaskComplexity:
            system = ZeigarnikEffectSystem()

            interrupted = []
            for i in range(10):
                task = system.create_task(f"task_{i}", complexity)
                system.start_task(task.id)
                system.work_on_task(task.id, 60, 0.5)
                system.interrupt_task(task.id)
                interrupted.append(task.id)

            recalls = system.recall_tasks()
            recalled = sum(1 for r in recalls if r.recalled)

            results[complexity.name] = recalled / 10

        return results

    # Analysis

    def get_metrics(self) -> ZeigarnikMetrics:
        """Get Zeigarnik metrics."""
        if not self._experiment_results:
            self.run_classic_experiment()

        last = self._experiment_results[-1]

        return ZeigarnikMetrics(
            completed_recall=last['completed_recall'],
            interrupted_recall=last['interrupted_recall'],
            zeigarnik_ratio=last['zeigarnik_ratio'],
            effect_magnitude=last['effect_magnitude']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'tasks': len(self._system._tasks),
            'memories': len(self._system._memories),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_zeigarnik_engine() -> ZeigarnikEffectEngine:
    """Create Zeigarnik effect engine."""
    return ZeigarnikEffectEngine()


def demonstrate_zeigarnik() -> Dict[str, Any]:
    """Demonstrate Zeigarnik effect."""
    engine = create_zeigarnik_engine()

    # Classic experiment
    classic = engine.run_classic_experiment(20)

    # Motivation comparison
    motivation = engine.run_motivation_comparison()

    # Progress comparison
    progress = engine.run_progress_comparison()

    # Complexity test
    complexity = engine.run_complexity_test()

    # Delay test
    delay = engine.run_delay_test()

    return {
        'zeigarnik_effect': {
            'completed_recall': f"{classic['completed_recall']:.0%}",
            'interrupted_recall': f"{classic['interrupted_recall']:.0%}",
            'ratio': f"{classic['zeigarnik_ratio']:.2f}",
            'effect': f"{classic['effect_magnitude']:.0%}"
        },
        'motivation': {
            mot: f"effect: {data['effect']:.0%}"
            for mot, data in motivation.items()
        },
        'progress': {
            level: f"{rate:.0%}"
            for level, rate in progress.items()
        },
        'complexity': {
            level: f"{rate:.0%}"
            for level, rate in complexity.items()
        },
        'interpretation': (
            f"Zeigarnik ratio: {classic['zeigarnik_ratio']:.2f}. "
            f"Interrupted tasks remembered better than completed ones."
        )
    }


def get_zeigarnik_facts() -> Dict[str, str]:
    """Get facts about Zeigarnik effect."""
    return {
        'zeigarnik_1927': 'Original dissertation research',
        'lewin_tension': 'Based on Lewin\'s tension system theory',
        'quasi_need': 'Incomplete task creates quasi-need',
        'motivation': 'Effect stronger with high task motivation',
        'applications': 'Cliffhangers, open loops, GTD systems',
        'replication': 'Mixed replication success',
        'moderators': 'Ego involvement, task importance matter',
        'ovsiankina': 'Related Ovsiankina effect - tendency to resume'
    }
