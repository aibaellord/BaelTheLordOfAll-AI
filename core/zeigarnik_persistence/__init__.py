"""
BAEL Zeigarnik Persistence Engine
===================================

Uncompleted tasks remain active in memory.
Bluma Zeigarnik's interrupted task effect.

"Ba'el's unfinished business haunts the mind." — Ba'el
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

logger = logging.getLogger("BAEL.ZeigarnikPersistence")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TaskStatus(Enum):
    """Task completion status."""
    COMPLETED = auto()
    INTERRUPTED = auto()
    NOT_STARTED = auto()


class TaskType(Enum):
    """Type of task."""
    PUZZLE = auto()
    PROBLEM_SOLVING = auto()
    CREATIVE = auto()
    ROUTINE = auto()
    ACHIEVEMENT = auto()


class InterruptionType(Enum):
    """Type of interruption."""
    EXTERNAL = auto()       # Interrupted by experimenter
    INTERNAL = auto()       # Self-interrupted
    FAILURE = auto()        # Failed to complete


class InvolvementLevel(Enum):
    """Level of ego involvement."""
    HIGH = auto()
    MODERATE = auto()
    LOW = auto()


@dataclass
class Task:
    """
    A task to perform.
    """
    id: str
    name: str
    task_type: TaskType
    difficulty: float
    ego_involvement: InvolvementLevel


@dataclass
class TaskExecution:
    """
    Task execution record.
    """
    task: Task
    status: TaskStatus
    progress: float         # 0-1
    time_spent_s: float
    interruption_type: Optional[InterruptionType]


@dataclass
class RecallResult:
    """
    Recall result for a task.
    """
    task: Task
    status: TaskStatus
    recalled: bool
    recall_order: int
    latency_ms: int


@dataclass
class ZeigarnikMetrics:
    """
    Zeigarnik effect metrics.
    """
    completed_recall: float
    interrupted_recall: float
    zeigarnik_ratio: float
    zeigarnik_effect: float


# ============================================================================
# ZEIGARNIK MODEL
# ============================================================================

class ZeigarnikModel:
    """
    Model of Zeigarnik effect.

    "Ba'el's tension-memory model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall rates
        self._base_recall = {
            TaskStatus.COMPLETED: 0.55,
            TaskStatus.INTERRUPTED: 0.68,
            TaskStatus.NOT_STARTED: 0.25
        }

        # Zeigarnik ratio (interrupted/completed)
        self._classic_ratio = 1.9  # Original finding

        # Ego involvement effects
        self._ego_effects = {
            InvolvementLevel.HIGH: 0.15,
            InvolvementLevel.MODERATE: 0.0,
            InvolvementLevel.LOW: -0.10
        }

        # Difficulty effects
        self._difficulty_weight = 0.10

        # Time since interruption
        self._recency_decay = 0.02  # Per hour

        # Progress at interruption
        self._progress_effects = {
            'near_completion': 0.20,  # > 80%
            'middle': 0.10,           # 40-80%
            'early': -0.05            # < 40%
        }

        # Tension system
        self._tension_build = 0.15   # Tension increases with task
        self._tension_release = 0.80 # Completion releases tension

        # Individual differences
        self._need_achievement_weight = 0.12

        self._lock = threading.RLock()

    def calculate_recall_probability(
        self,
        status: TaskStatus,
        ego_involvement: InvolvementLevel = InvolvementLevel.MODERATE,
        progress: float = 0.5,
        hours_since: float = 0.5
    ) -> float:
        """Calculate recall probability for a task."""
        base = self._base_recall[status]

        # Ego involvement
        base += self._ego_effects[ego_involvement]

        # Progress at interruption (for interrupted tasks)
        if status == TaskStatus.INTERRUPTED:
            if progress > 0.8:
                base += self._progress_effects['near_completion']
            elif progress > 0.4:
                base += self._progress_effects['middle']
            else:
                base += self._progress_effects['early']

        # Recency decay (stronger for completed)
        if status == TaskStatus.COMPLETED:
            base -= hours_since * self._recency_decay

        # Add noise
        base += random.uniform(-0.08, 0.08)

        return max(0.15, min(0.95, base))

    def calculate_tension(
        self,
        progress: float,
        completed: bool
    ) -> float:
        """Calculate psychological tension."""
        # Tension builds with progress
        tension = progress * self._tension_build

        # Completion releases tension
        if completed:
            tension *= (1 - self._tension_release)

        return tension

    def calculate_zeigarnik_ratio(
        self,
        interrupted_recall: float,
        completed_recall: float
    ) -> float:
        """Calculate Zeigarnik ratio."""
        if completed_recall == 0:
            return float('inf')
        return interrupted_recall / completed_recall

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'tension_system': 'Quasi-needs create tension',
            'completion': 'Completion releases tension',
            'rehearsal': 'Uncompleted tasks rehearsed more',
            'goal_gradient': 'Near-completion increases persistence',
            'ego_involvement': 'Personal relevance increases effect'
        }

    def get_boundary_conditions(
        self
    ) -> Dict[str, str]:
        """Get boundary conditions."""
        return {
            'ego_involvement': 'Stronger with high involvement',
            'failure': 'May reverse for threatening failure',
            'time': 'Effect decays over time',
            'closure': 'Alternative closure reduces effect',
            'culture': 'Stronger in achievement-oriented cultures'
        }

    def get_lewinian_formula(
        self
    ) -> str:
        """Get Lewin's tension system formula."""
        return (
            "Tension = Goal_Valence × (1 - Completion)\n"
            "Recall = f(Tension)\n"
            "Completion → Tension_Release"
        )


# ============================================================================
# ZEIGARNIK SYSTEM
# ============================================================================

class ZeigarnikSystem:
    """
    Zeigarnik effect simulation system.

    "Ba'el's interrupted task system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = ZeigarnikModel()

        self._tasks: Dict[str, Task] = {}
        self._executions: Dict[str, TaskExecution] = {}
        self._recalls: List[RecallResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"task_{self._counter}"

    def create_task(
        self,
        name: str,
        task_type: TaskType = TaskType.PUZZLE,
        difficulty: float = 0.5,
        ego_involvement: InvolvementLevel = InvolvementLevel.MODERATE
    ) -> Task:
        """Create task."""
        task = Task(
            id=self._generate_id(),
            name=name,
            task_type=task_type,
            difficulty=difficulty,
            ego_involvement=ego_involvement
        )

        self._tasks[task.id] = task

        return task

    def execute_task(
        self,
        task: Task,
        status: TaskStatus = TaskStatus.COMPLETED,
        progress: float = 1.0,
        time_spent: float = 120
    ) -> TaskExecution:
        """Execute a task."""
        interruption = None
        if status == TaskStatus.INTERRUPTED:
            interruption = random.choice(list(InterruptionType))

        execution = TaskExecution(
            task=task,
            status=status,
            progress=progress,
            time_spent_s=time_spent,
            interruption_type=interruption
        )

        self._executions[task.id] = execution

        return execution

    def recall_tasks(
        self
    ) -> List[RecallResult]:
        """Attempt to recall tasks."""
        results = []
        order = 1

        for task_id, execution in self._executions.items():
            prob = self._model.calculate_recall_probability(
                execution.status,
                execution.task.ego_involvement,
                execution.progress
            )

            recalled = random.random() < prob

            result = RecallResult(
                task=execution.task,
                status=execution.status,
                recalled=recalled,
                recall_order=order if recalled else -1,
                latency_ms=random.randint(500, 3000)
            )

            if recalled:
                order += 1

            results.append(result)
            self._recalls.append(result)

        return results


# ============================================================================
# ZEIGARNIK PARADIGM
# ============================================================================

class ZeigarnikParadigm:
    """
    Zeigarnik paradigm.

    "Ba'el's interrupted task study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_tasks: int = 20
    ) -> Dict[str, Any]:
        """Run classic Zeigarnik paradigm."""
        system = ZeigarnikSystem()

        # Create and execute tasks
        for i in range(n_tasks):
            task = system.create_task(f"Task_{i}")

            if i % 2 == 0:  # Half interrupted
                system.execute_task(
                    task,
                    TaskStatus.INTERRUPTED,
                    progress=random.uniform(0.4, 0.9)
                )
            else:
                system.execute_task(
                    task,
                    TaskStatus.COMPLETED,
                    progress=1.0
                )

        # Recall
        results = system.recall_tasks()

        # Calculate rates
        completed = [r for r in results if r.status == TaskStatus.COMPLETED]
        interrupted = [r for r in results if r.status == TaskStatus.INTERRUPTED]

        comp_recall = sum(1 for r in completed if r.recalled) / max(1, len(completed))
        int_recall = sum(1 for r in interrupted if r.recalled) / max(1, len(interrupted))

        ratio = int_recall / max(0.01, comp_recall)
        effect = int_recall - comp_recall

        return {
            'completed_recall': comp_recall,
            'interrupted_recall': int_recall,
            'zeigarnik_ratio': ratio,
            'zeigarnik_effect': effect,
            'interpretation': f'Zeigarnik: {ratio:.2f} ratio (interrupted/completed)'
        }

    def run_ego_involvement_study(
        self
    ) -> Dict[str, Any]:
        """Study ego involvement effects."""
        model = ZeigarnikModel()

        results = {}

        for involvement in InvolvementLevel:
            comp = model.calculate_recall_probability(
                TaskStatus.COMPLETED, involvement
            )
            inter = model.calculate_recall_probability(
                TaskStatus.INTERRUPTED, involvement
            )

            results[involvement.name] = {
                'completed': comp,
                'interrupted': inter,
                'effect': inter - comp
            }

        return {
            'by_involvement': results,
            'interpretation': 'High ego involvement increases effect'
        }

    def run_progress_study(
        self
    ) -> Dict[str, Any]:
        """Study progress at interruption."""
        model = ZeigarnikModel()

        progress_levels = [0.2, 0.5, 0.8, 0.95]

        results = {}

        for prog in progress_levels:
            recall = model.calculate_recall_probability(
                TaskStatus.INTERRUPTED, progress=prog
            )
            results[f'progress_{int(prog*100)}'] = {'recall': recall}

        return {
            'by_progress': results,
            'interpretation': 'Near-completion shows strongest effect'
        }

    def run_tension_study(
        self
    ) -> Dict[str, Any]:
        """Study tension dynamics."""
        model = ZeigarnikModel()

        scenarios = [
            ('early_interrupt', 0.3, False),
            ('mid_interrupt', 0.6, False),
            ('near_complete_interrupt', 0.9, False),
            ('completed', 1.0, True)
        ]

        results = {}

        for name, progress, completed in scenarios:
            tension = model.calculate_tension(progress, completed)
            results[name] = {'tension': tension}

        return {
            'by_scenario': results,
            'interpretation': 'Completion releases tension'
        }

    def run_delay_study(
        self
    ) -> Dict[str, Any]:
        """Study time delay effects."""
        model = ZeigarnikModel()

        hours = [0.5, 1, 2, 6, 24]

        results = {}

        for h in hours:
            comp = model.calculate_recall_probability(
                TaskStatus.COMPLETED, hours_since=h
            )
            inter = model.calculate_recall_probability(
                TaskStatus.INTERRUPTED, hours_since=h
            )

            results[f'{h}h'] = {
                'completed': comp,
                'interrupted': inter,
                'effect': inter - comp
            }

        return {
            'by_delay': results,
            'interpretation': 'Effect persists but may decay'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = ZeigarnikModel()

        mechanisms = model.get_mechanisms()
        boundaries = model.get_boundary_conditions()
        formula = model.get_lewinian_formula()

        return {
            'mechanisms': mechanisms,
            'boundaries': boundaries,
            'formula': formula,
            'interpretation': 'Quasi-needs create persistent tension'
        }


# ============================================================================
# ZEIGARNIK ENGINE
# ============================================================================

class ZeigarnikEngine:
    """
    Complete Zeigarnik effect engine.

    "Ba'el's unfinished business engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = ZeigarnikParadigm()
        self._system = ZeigarnikSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Task operations

    def create_task(
        self,
        name: str,
        task_type: TaskType = TaskType.PUZZLE
    ) -> Task:
        """Create task."""
        return self._system.create_task(name, task_type)

    def execute_task(
        self,
        task: Task,
        status: TaskStatus = TaskStatus.COMPLETED
    ) -> TaskExecution:
        """Execute task."""
        return self._system.execute_task(task, status)

    def recall_tasks(
        self
    ) -> List[RecallResult]:
        """Recall tasks."""
        return self._system.recall_tasks()

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_ego_involvement(
        self
    ) -> Dict[str, Any]:
        """Study ego involvement."""
        return self._paradigm.run_ego_involvement_study()

    def study_progress(
        self
    ) -> Dict[str, Any]:
        """Study progress effects."""
        return self._paradigm.run_progress_study()

    def study_tension(
        self
    ) -> Dict[str, Any]:
        """Study tension dynamics."""
        return self._paradigm.run_tension_study()

    def study_delay(
        self
    ) -> Dict[str, Any]:
        """Study delay effects."""
        return self._paradigm.run_delay_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    # Analysis

    def get_metrics(self) -> ZeigarnikMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return ZeigarnikMetrics(
            completed_recall=last['completed_recall'],
            interrupted_recall=last['interrupted_recall'],
            zeigarnik_ratio=last['zeigarnik_ratio'],
            zeigarnik_effect=last['zeigarnik_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'tasks': len(self._system._tasks),
            'executions': len(self._system._executions),
            'recalls': len(self._system._recalls)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_zeigarnik_engine() -> ZeigarnikEngine:
    """Create Zeigarnik engine."""
    return ZeigarnikEngine()


def demonstrate_zeigarnik() -> Dict[str, Any]:
    """Demonstrate Zeigarnik effect."""
    engine = create_zeigarnik_engine()

    # Classic
    classic = engine.run_classic()

    # Ego involvement
    ego = engine.study_ego_involvement()

    # Progress
    progress = engine.study_progress()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'completed': f"{classic['completed_recall']:.0%}",
            'interrupted': f"{classic['interrupted_recall']:.0%}",
            'ratio': f"{classic['zeigarnik_ratio']:.2f}",
            'effect': f"{classic['zeigarnik_effect']:.0%}"
        },
        'by_involvement': {
            k: f"{v['effect']:.0%}"
            for k, v in ego['by_involvement'].items()
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Ratio: {classic['zeigarnik_ratio']:.2f}. "
            f"Interrupted tasks remembered better. "
            f"Quasi-needs create persistent tension."
        )
    }


def get_zeigarnik_facts() -> Dict[str, str]:
    """Get facts about Zeigarnik effect."""
    return {
        'zeigarnik_1927': 'Original discovery by Bluma Zeigarnik',
        'lewin': 'Kurt Lewin\'s field theory basis',
        'ratio': '~1.9:1 interrupted:completed recall',
        'mechanism': 'Quasi-needs create tension',
        'ego_involvement': 'Stronger with personal relevance',
        'completion': 'Completion releases tension',
        'applications': 'To-do lists, cliffhangers, learning',
        'ovsiankina': 'Related resumption effect'
    }
