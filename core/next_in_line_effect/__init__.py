"""
BAEL Next-In-Line Effect Engine
=================================

Memory impairment when waiting to perform.
Bond's next-in-line phenomenon.

"Ba'el awaits the spotlight, mind elsewhere." — Ba'el
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

logger = logging.getLogger("BAEL.NextInLineEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PositionType(Enum):
    """Position in sequence."""
    JUST_PERFORMED = auto()      # -1 from target
    IMMEDIATELY_BEFORE = auto()  # Target position
    TWO_BEFORE = auto()          # -2 from target
    FAR_BEFORE = auto()          # Many before
    FAR_AFTER = auto()           # Many after


class TaskType(Enum):
    """Type of performance task."""
    READ_ALOUD = auto()
    INTRODUCE_SELF = auto()
    GIVE_OPINION = auto()
    PERFORM_SKILL = auto()


class AnxietyLevel(Enum):
    """Anxiety level."""
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()


class AttentionFocus(Enum):
    """Focus of attention."""
    SELF = auto()           # Own performance
    OTHERS = auto()         # Others' performance
    ENVIRONMENT = auto()    # General


@dataclass
class Performer:
    """
    A performer in sequence.
    """
    id: str
    name: str
    position: int
    anxiety_level: AnxietyLevel


@dataclass
class Performance:
    """
    A performance event.
    """
    performer: Performer
    content: str
    task_type: TaskType
    duration_s: float


@dataclass
class MemoryTest:
    """
    Memory test for performances.
    """
    observer: Performer
    target_performance: Performance
    position_relative: PositionType
    recalled: bool
    detail_accuracy: float


@dataclass
class NextInLineMetrics:
    """
    Next-in-line effect metrics.
    """
    baseline_recall: float
    next_in_line_recall: float
    effect_magnitude: float
    by_position: Dict[str, float]


# ============================================================================
# NEXT IN LINE MODEL
# ============================================================================

class NextInLineModel:
    """
    Model of next-in-line effect.

    "Ba'el's performance anxiety model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base recall rate
        self._base_recall = 0.70

        # Position effects (relative to own performance)
        self._position_effects = {
            PositionType.JUST_PERFORMED: -0.10,      # Just went
            PositionType.IMMEDIATELY_BEFORE: -0.25,  # About to go
            PositionType.TWO_BEFORE: -0.15,
            PositionType.FAR_BEFORE: -0.05,
            PositionType.FAR_AFTER: 0.0
        }

        # Anxiety effects
        self._anxiety_effects = {
            AnxietyLevel.LOW: 0.0,
            AnxietyLevel.MODERATE: -0.10,
            AnxietyLevel.HIGH: -0.20
        }

        # Task type effects
        self._task_effects = {
            TaskType.READ_ALOUD: 0.0,
            TaskType.INTRODUCE_SELF: -0.05,
            TaskType.GIVE_OPINION: -0.08,
            TaskType.PERFORM_SKILL: -0.12
        }

        # Self-focus effects
        self._self_focus_reduction = 0.15

        # Rehearsal effects
        self._rehearsal_reduction = 0.12

        # Recovery after performance
        self._post_performance_recovery = 0.05  # Per position after

        self._lock = threading.RLock()

    def calculate_recall_probability(
        self,
        position_relative: PositionType,
        anxiety_level: AnxietyLevel,
        task_type: TaskType = TaskType.READ_ALOUD,
        was_rehearsing: bool = True
    ) -> float:
        """Calculate recall probability."""
        prob = self._base_recall

        # Position effect
        prob += self._position_effects[position_relative]

        # Anxiety
        prob += self._anxiety_effects[anxiety_level]

        # Task
        prob += self._task_effects[task_type]

        # Rehearsal interference
        if was_rehearsing and position_relative == PositionType.IMMEDIATELY_BEFORE:
            prob -= self._rehearsal_reduction

        # Add noise
        prob += random.uniform(-0.1, 0.1)

        return max(0.2, min(0.90, prob))

    def calculate_attention_distribution(
        self,
        position_relative: PositionType
    ) -> Dict[AttentionFocus, float]:
        """Calculate attention distribution."""
        if position_relative == PositionType.IMMEDIATELY_BEFORE:
            return {
                AttentionFocus.SELF: 0.70,
                AttentionFocus.OTHERS: 0.15,
                AttentionFocus.ENVIRONMENT: 0.15
            }
        elif position_relative == PositionType.TWO_BEFORE:
            return {
                AttentionFocus.SELF: 0.50,
                AttentionFocus.OTHERS: 0.30,
                AttentionFocus.ENVIRONMENT: 0.20
            }
        elif position_relative == PositionType.JUST_PERFORMED:
            return {
                AttentionFocus.SELF: 0.40,  # Post-mortem
                AttentionFocus.OTHERS: 0.35,
                AttentionFocus.ENVIRONMENT: 0.25
            }
        else:
            return {
                AttentionFocus.SELF: 0.20,
                AttentionFocus.OTHERS: 0.55,
                AttentionFocus.ENVIRONMENT: 0.25
            }

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get underlying mechanisms."""
        return {
            'self_focused_attention': 'Attention on own performance',
            'rehearsal': 'Mentally practicing own contribution',
            'performance_anxiety': 'Anxiety interferes with encoding',
            'resource_depletion': 'Cognitive resources diverted'
        }


# ============================================================================
# NEXT IN LINE SYSTEM
# ============================================================================

class NextInLineSystem:
    """
    Next-in-line simulation system.

    "Ba'el's sequence system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = NextInLineModel()

        self._performers: Dict[str, Performer] = {}
        self._performances: Dict[str, Performance] = {}
        self._tests: List[MemoryTest] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"perf_{self._counter}"

    def create_performer(
        self,
        name: str,
        position: int,
        anxiety: AnxietyLevel = AnxietyLevel.MODERATE
    ) -> Performer:
        """Create performer."""
        performer = Performer(
            id=self._generate_id(),
            name=name,
            position=position,
            anxiety_level=anxiety
        )

        self._performers[performer.id] = performer

        return performer

    def create_performance(
        self,
        performer: Performer,
        content: str,
        task_type: TaskType = TaskType.READ_ALOUD
    ) -> Performance:
        """Create performance."""
        performance = Performance(
            performer=performer,
            content=content,
            task_type=task_type,
            duration_s=random.uniform(5, 30)
        )

        self._performances[performer.id] = performance

        return performance

    def determine_position_type(
        self,
        observer_position: int,
        target_position: int
    ) -> PositionType:
        """Determine relative position type."""
        diff = observer_position - target_position

        if diff == 1:
            return PositionType.IMMEDIATELY_BEFORE
        elif diff == 2:
            return PositionType.TWO_BEFORE
        elif diff > 2:
            return PositionType.FAR_BEFORE
        elif diff == -1:
            return PositionType.JUST_PERFORMED
        else:
            return PositionType.FAR_AFTER

    def test_memory(
        self,
        observer: Performer,
        target_performance: Performance
    ) -> MemoryTest:
        """Test memory for a performance."""
        position_rel = self.determine_position_type(
            observer.position,
            target_performance.performer.position
        )

        prob = self._model.calculate_recall_probability(
            position_rel,
            observer.anxiety_level,
            target_performance.task_type
        )

        recalled = random.random() < prob

        test = MemoryTest(
            observer=observer,
            target_performance=target_performance,
            position_relative=position_rel,
            recalled=recalled,
            detail_accuracy=random.uniform(0.3, 0.8) if recalled else 0.0
        )

        self._tests.append(test)

        return test


# ============================================================================
# NEXT IN LINE PARADIGM
# ============================================================================

class NextInLineParadigm:
    """
    Next-in-line paradigm.

    "Ba'el's sequence study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_performers: int = 10
    ) -> Dict[str, Any]:
        """Run classic next-in-line paradigm."""
        system = NextInLineSystem()

        # Create sequence of performers
        performers = []
        for i in range(n_performers):
            perf = system.create_performer(
                f"Person_{i}",
                i,
                AnxietyLevel.MODERATE
            )
            performers.append(perf)
            system.create_performance(perf, f"Content from {i}")

        results_by_position = defaultdict(list)

        # Test each observer's memory for all others
        for observer in performers:
            for target_id, performance in system._performances.items():
                if performance.performer.id != observer.id:
                    test = system.test_memory(observer, performance)
                    results_by_position[test.position_relative.name].append(test.recalled)

        # Calculate means
        mean_by_position = {}
        for pos, recalls in results_by_position.items():
            mean_by_position[pos] = sum(recalls) / max(1, len(recalls))

        baseline = mean_by_position.get('FAR_AFTER', 0.70)
        next_in_line = mean_by_position.get('IMMEDIATELY_BEFORE', 0.45)

        return {
            'by_position': mean_by_position,
            'baseline': baseline,
            'next_in_line': next_in_line,
            'effect': baseline - next_in_line,
            'interpretation': f'Next-in-line effect: {baseline - next_in_line:.0%}'
        }

    def run_anxiety_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare anxiety levels."""
        model = NextInLineModel()

        results = {}

        for anxiety in AnxietyLevel:
            recall = model.calculate_recall_probability(
                PositionType.IMMEDIATELY_BEFORE,
                anxiety
            )

            results[anxiety.name] = {
                'recall': recall
            }

        return {
            'by_anxiety': results,
            'interpretation': 'Higher anxiety = larger effect'
        }

    def run_task_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare task types."""
        model = NextInLineModel()

        results = {}

        for task in TaskType:
            recall = model.calculate_recall_probability(
                PositionType.IMMEDIATELY_BEFORE,
                AnxietyLevel.MODERATE,
                task
            )

            results[task.name] = {
                'recall': recall
            }

        return {
            'by_task': results,
            'interpretation': 'Complex tasks = larger effect'
        }

    def run_attention_study(
        self
    ) -> Dict[str, Any]:
        """Study attention distribution."""
        model = NextInLineModel()

        results = {}

        for position in PositionType:
            attention = model.calculate_attention_distribution(position)

            results[position.name] = {
                focus.name: pct for focus, pct in attention.items()
            }

        return {
            'by_position': results,
            'interpretation': 'Next-in-line = 70% self-focused'
        }

    def run_position_curve_study(
        self
    ) -> Dict[str, Any]:
        """Study full position curve."""
        model = NextInLineModel()

        results = {}

        for position in PositionType:
            recall = model.calculate_recall_probability(
                position, AnxietyLevel.MODERATE
            )

            results[position.name] = {
                'recall': recall
            }

        return {
            'by_position': results,
            'interpretation': 'U-shaped curve around own position'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = NextInLineModel()

        mechanisms = model.get_mechanisms()

        return {
            'mechanisms': mechanisms,
            'primary': 'Self-focused attention and rehearsal',
            'interpretation': 'Attention diverted from others'
        }


# ============================================================================
# NEXT IN LINE ENGINE
# ============================================================================

class NextInLineEngine:
    """
    Complete next-in-line engine.

    "Ba'el's sequence engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = NextInLineParadigm()
        self._system = NextInLineSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Performer operations

    def create_performer(
        self,
        name: str,
        position: int
    ) -> Performer:
        """Create performer."""
        return self._system.create_performer(name, position)

    def create_performance(
        self,
        performer: Performer,
        content: str
    ) -> Performance:
        """Create performance."""
        return self._system.create_performance(performer, content)

    def test_memory(
        self,
        observer: Performer,
        performance: Performance
    ) -> MemoryTest:
        """Test memory."""
        return self._system.test_memory(observer, performance)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_anxiety(
        self
    ) -> Dict[str, Any]:
        """Compare anxiety levels."""
        return self._paradigm.run_anxiety_comparison()

    def compare_tasks(
        self
    ) -> Dict[str, Any]:
        """Compare task types."""
        return self._paradigm.run_task_comparison()

    def study_attention(
        self
    ) -> Dict[str, Any]:
        """Study attention."""
        return self._paradigm.run_attention_study()

    def study_position_curve(
        self
    ) -> Dict[str, Any]:
        """Study position curve."""
        return self._paradigm.run_position_curve_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    # Analysis

    def get_metrics(self) -> NextInLineMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return NextInLineMetrics(
            baseline_recall=last['baseline'],
            next_in_line_recall=last['next_in_line'],
            effect_magnitude=last['effect'],
            by_position=last['by_position']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'performers': len(self._system._performers),
            'performances': len(self._system._performances),
            'tests': len(self._system._tests)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_next_in_line_engine() -> NextInLineEngine:
    """Create next-in-line engine."""
    return NextInLineEngine()


def demonstrate_next_in_line() -> Dict[str, Any]:
    """Demonstrate next-in-line effect."""
    engine = create_next_in_line_engine()

    # Classic
    classic = engine.run_classic()

    # Anxiety
    anxiety = engine.compare_anxiety()

    # Attention
    attention = engine.study_attention()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'baseline': f"{classic['baseline']:.0%}",
            'next_in_line': f"{classic['next_in_line']:.0%}",
            'effect': f"{classic['effect']:.0%}"
        },
        'by_anxiety': {
            k: f"{v['recall']:.0%}"
            for k, v in anxiety['by_anxiety'].items()
        },
        'attention': {
            k: v.get('SELF', 0)
            for k, v in list(attention['by_position'].items())[:3]
        },
        'mechanisms': mechanisms['mechanisms'],
        'interpretation': (
            f"Effect: {classic['effect']:.0%}. "
            f"Memory impaired when about to perform. "
            f"Self-focused attention and rehearsal."
        )
    }


def get_next_in_line_facts() -> Dict[str, str]:
    """Get facts about next-in-line effect."""
    return {
        'bond_1987': 'Next-in-line effect discovery',
        'effect': '20-30% memory reduction',
        'mechanism': 'Self-focused attention',
        'anxiety': 'Worsened by performance anxiety',
        'rehearsal': 'Mental rehearsal reduces encoding',
        'recovery': 'Memory improves after performing',
        'applications': 'Classrooms, presentations, meetings',
        'mitigation': 'Reduce performance pressure'
    }
