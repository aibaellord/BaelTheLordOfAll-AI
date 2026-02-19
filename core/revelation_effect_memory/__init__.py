"""
BAEL Revelation Effect Memory Engine
======================================

Solving a problem just before judgment increases familiarity.
Westerman & Greene's revelation effect paradigm.

"Ba'el's puzzles distort truth judgments." — Ba'el
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

logger = logging.getLogger("BAEL.RevelationEffectMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class RevelationTask(Enum):
    """Type of revelation task."""
    ANAGRAM = auto()
    WORD_FRAGMENT = auto()
    MATH_PROBLEM = auto()
    ROTATE_LETTERS = auto()


class JudgmentType(Enum):
    """Type of judgment."""
    RECOGNITION = auto()    # Old/new
    FAMILIARITY = auto()    # Familiarity rating
    TRUTH = auto()          # True/false


class ItemStatus(Enum):
    """Status of item."""
    OLD = auto()            # Previously studied
    NEW = auto()            # Not studied


class TaskDifficulty(Enum):
    """Difficulty of revelation task."""
    EASY = auto()
    MODERATE = auto()
    HARD = auto()


@dataclass
class TestItem:
    """
    A test item.
    """
    id: str
    content: str
    status: ItemStatus
    presentation_count: int


@dataclass
class RevelationTrial:
    """
    A revelation trial.
    """
    item: TestItem
    task: Optional[RevelationTask]
    task_solved: bool
    judgment: bool           # Judged as old
    confidence: float
    latency_ms: int


@dataclass
class RevelationMetrics:
    """
    Revelation effect metrics.
    """
    with_revelation_hit: float
    without_revelation_hit: float
    with_revelation_fa: float
    without_revelation_fa: float
    revelation_effect: float


# ============================================================================
# REVELATION MODEL
# ============================================================================

class RevelationModel:
    """
    Model of revelation effect.

    "Ba'el's revelation distortion model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base rates
        self._base_hit_rate = 0.70
        self._base_fa_rate = 0.25

        # Revelation boost (key effect)
        self._revelation_boost_hits = 0.05
        self._revelation_boost_fa = 0.15   # Larger for false alarms

        # Task difficulty effects
        self._difficulty_effects = {
            TaskDifficulty.EASY: 0.08,
            TaskDifficulty.MODERATE: 0.12,
            TaskDifficulty.HARD: 0.15
        }

        # Task type effects
        self._task_effects = {
            RevelationTask.ANAGRAM: 0.12,
            RevelationTask.WORD_FRAGMENT: 0.10,
            RevelationTask.MATH_PROBLEM: 0.08,
            RevelationTask.ROTATE_LETTERS: 0.11
        }

        # Relatedness effects
        self._related_task_boost = 0.05   # Task related to item

        # Criterion shift
        self._criterion_shift = -0.20     # More liberal

        # Fluency attribution
        self._fluency_weight = 0.25

        # Decrement
        self._decrement_enabled = True    # Reduces with warnings

        self._lock = threading.RLock()

    def calculate_judgment_probability(
        self,
        item: TestItem,
        with_revelation: bool = False,
        task: Optional[RevelationTask] = None,
        difficulty: TaskDifficulty = TaskDifficulty.MODERATE
    ) -> float:
        """Calculate probability of 'old' judgment."""
        # Base by actual status
        if item.status == ItemStatus.OLD:
            base = self._base_hit_rate
        else:
            base = self._base_fa_rate

        # Revelation effect
        if with_revelation:
            if item.status == ItemStatus.OLD:
                base += self._revelation_boost_hits
            else:
                base += self._revelation_boost_fa

            # Task effects
            if task:
                base += self._task_effects[task]

            # Difficulty
            base += self._difficulty_effects[difficulty]

        # Add noise
        base += random.uniform(-0.08, 0.08)

        return max(0.10, min(0.95, base))

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'criterion_shift': 'More liberal criterion after task',
            'fluency_misattribution': 'Task fluency attributed to item',
            'global_matching': 'Disrupted memory signal',
            'arousal': 'Task arousal increases familiarity',
            'decrement_hypothesis': 'Revelation decreases discriminability'
        }

    def get_key_findings(
        self
    ) -> Dict[str, str]:
        """Get key empirical findings."""
        return {
            'hits_and_fa': 'Both increase with revelation',
            'unrelated_tasks': 'Effect occurs even with unrelated tasks',
            'math_problems': 'Even math problems produce effect',
            'warning': 'Warning reduces but doesn\'t eliminate',
            'false_memory': 'Increases false recognition'
        }

    def get_theoretical_debate(
        self
    ) -> Dict[str, Dict[str, str]]:
        """Get theoretical debate."""
        return {
            'criterion_shift': {
                'claim': 'Task shifts response criterion',
                'evidence': 'FA increase larger than hit increase',
                'problems': 'Doesn\'t explain all variants'
            },
            'fluency': {
                'claim': 'Task creates fluency',
                'evidence': 'Fluency manipulations affect size',
                'problems': 'Unrelated tasks still work'
            },
            'global_matching': {
                'claim': 'Disrupts memory signal',
                'evidence': 'Consistent with broad effects',
                'problems': 'Mechanism unclear'
            }
        }


# ============================================================================
# REVELATION SYSTEM
# ============================================================================

class RevelationSystem:
    """
    Revelation effect system.

    "Ba'el's revelation system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = RevelationModel()

        self._items: Dict[str, TestItem] = {}
        self._trials: List[RevelationTrial] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_item(
        self,
        content: str,
        status: ItemStatus = ItemStatus.OLD,
        presentation_count: int = 1
    ) -> TestItem:
        """Create test item."""
        item = TestItem(
            id=self._generate_id(),
            content=content,
            status=status,
            presentation_count=presentation_count
        )

        self._items[item.id] = item

        return item

    def run_trial(
        self,
        item: TestItem,
        with_revelation: bool = False,
        task: Optional[RevelationTask] = None
    ) -> RevelationTrial:
        """Run revelation trial."""
        # Solve task (always succeed for simulation)
        task_solved = True if task else False

        # Calculate judgment
        prob = self._model.calculate_judgment_probability(
            item, with_revelation, task
        )

        judged_old = random.random() < prob

        trial = RevelationTrial(
            item=item,
            task=task,
            task_solved=task_solved,
            judgment=judged_old,
            confidence=random.uniform(0.4, 0.9),
            latency_ms=random.randint(500, 2500)
        )

        self._trials.append(trial)

        return trial


# ============================================================================
# REVELATION PARADIGM
# ============================================================================

class RevelationParadigm:
    """
    Revelation effect paradigm.

    "Ba'el's revelation study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_old: int = 20,
        n_new: int = 20
    ) -> Dict[str, Any]:
        """Run classic revelation paradigm."""
        system = RevelationSystem()

        # Create items
        old_items = [
            system.create_item(f"Old_{i}", ItemStatus.OLD)
            for i in range(n_old)
        ]
        new_items = [
            system.create_item(f"New_{i}", ItemStatus.NEW)
            for i in range(n_new)
        ]

        # Test with and without revelation
        results = {
            'with_revelation': {'old': [], 'new': []},
            'without_revelation': {'old': [], 'new': []}
        }

        # Half with revelation, half without
        for i, item in enumerate(old_items):
            if i % 2 == 0:
                trial = system.run_trial(item, True, RevelationTask.ANAGRAM)
                results['with_revelation']['old'].append(trial.judgment)
            else:
                trial = system.run_trial(item, False)
                results['without_revelation']['old'].append(trial.judgment)

        for i, item in enumerate(new_items):
            if i % 2 == 0:
                trial = system.run_trial(item, True, RevelationTask.ANAGRAM)
                results['with_revelation']['new'].append(trial.judgment)
            else:
                trial = system.run_trial(item, False)
                results['without_revelation']['new'].append(trial.judgment)

        # Calculate rates
        with_hit = sum(results['with_revelation']['old']) / max(1, len(results['with_revelation']['old']))
        without_hit = sum(results['without_revelation']['old']) / max(1, len(results['without_revelation']['old']))
        with_fa = sum(results['with_revelation']['new']) / max(1, len(results['with_revelation']['new']))
        without_fa = sum(results['without_revelation']['new']) / max(1, len(results['without_revelation']['new']))

        revelation_effect = (with_hit + with_fa) / 2 - (without_hit + without_fa) / 2

        return {
            'with_revelation_hit': with_hit,
            'without_revelation_hit': without_hit,
            'with_revelation_fa': with_fa,
            'without_revelation_fa': without_fa,
            'revelation_effect': revelation_effect,
            'interpretation': f'Revelation effect: {revelation_effect:.0%} boost'
        }

    def run_task_type_study(
        self
    ) -> Dict[str, Any]:
        """Study different revelation tasks."""
        model = RevelationModel()

        results = {}

        for task in RevelationTask:
            new_item = TestItem("test", "test", ItemStatus.NEW, 0)
            prob = model.calculate_judgment_probability(new_item, True, task)

            results[task.name] = {'fa_rate': prob}

        return {
            'by_task': results,
            'interpretation': 'All tasks produce revelation effect'
        }

    def run_difficulty_study(
        self
    ) -> Dict[str, Any]:
        """Study task difficulty effects."""
        model = RevelationModel()

        results = {}

        for difficulty in TaskDifficulty:
            new_item = TestItem("test", "test", ItemStatus.NEW, 0)
            prob = model.calculate_judgment_probability(
                new_item, True, RevelationTask.ANAGRAM, difficulty
            )

            results[difficulty.name] = {'fa_rate': prob}

        return {
            'by_difficulty': results,
            'interpretation': 'Harder tasks = larger effect'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = RevelationModel()

        mechanisms = model.get_mechanisms()
        findings = model.get_key_findings()
        debate = model.get_theoretical_debate()

        return {
            'mechanisms': mechanisms,
            'findings': findings,
            'debate': debate,
            'interpretation': 'Multiple mechanisms proposed'
        }

    def run_signal_detection_analysis(
        self
    ) -> Dict[str, Any]:
        """Run signal detection analysis."""
        # Calculate d' and c for with/without revelation
        classic = self.run_classic_paradigm()

        # With revelation
        h1 = max(0.01, min(0.99, classic['with_revelation_hit']))
        f1 = max(0.01, min(0.99, classic['with_revelation_fa']))
        z_h1 = norm_ppf(h1)
        z_f1 = norm_ppf(f1)
        d_prime_with = z_h1 - z_f1
        c_with = -0.5 * (z_h1 + z_f1)

        # Without revelation
        h2 = max(0.01, min(0.99, classic['without_revelation_hit']))
        f2 = max(0.01, min(0.99, classic['without_revelation_fa']))
        z_h2 = norm_ppf(h2)
        z_f2 = norm_ppf(f2)
        d_prime_without = z_h2 - z_f2
        c_without = -0.5 * (z_h2 + z_f2)

        return {
            'with_revelation': {'d_prime': d_prime_with, 'criterion': c_with},
            'without_revelation': {'d_prime': d_prime_without, 'criterion': c_without},
            'd_prime_difference': d_prime_without - d_prime_with,
            'criterion_difference': c_with - c_without,
            'interpretation': 'Revelation shifts criterion liberal'
        }


def norm_ppf(p: float) -> float:
    """Approximate inverse normal CDF."""
    # Simple approximation
    if p <= 0:
        return -3.0
    if p >= 1:
        return 3.0
    if p == 0.5:
        return 0.0

    sign = 1 if p > 0.5 else -1
    p = min(p, 1 - p)

    t = math.sqrt(-2 * math.log(p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308

    result = t - (c0 + c1*t + c2*t*t) / (1 + d1*t + d2*t*t + d3*t*t*t)
    return sign * result


# ============================================================================
# REVELATION ENGINE
# ============================================================================

class RevelationEngine:
    """
    Complete revelation effect engine.

    "Ba'el's revelation distortion engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = RevelationParadigm()
        self._system = RevelationSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Item operations

    def create_item(
        self,
        content: str,
        status: ItemStatus = ItemStatus.OLD
    ) -> TestItem:
        """Create item."""
        return self._system.create_item(content, status)

    def run_trial(
        self,
        item: TestItem,
        with_revelation: bool = False
    ) -> RevelationTrial:
        """Run trial."""
        task = RevelationTask.ANAGRAM if with_revelation else None
        return self._system.run_trial(item, with_revelation, task)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_tasks(
        self
    ) -> Dict[str, Any]:
        """Study tasks."""
        return self._paradigm.run_task_type_study()

    def study_difficulty(
        self
    ) -> Dict[str, Any]:
        """Study difficulty."""
        return self._paradigm.run_difficulty_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    def run_sdt_analysis(
        self
    ) -> Dict[str, Any]:
        """Run SDT analysis."""
        return self._paradigm.run_signal_detection_analysis()

    # Analysis

    def get_metrics(self) -> RevelationMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return RevelationMetrics(
            with_revelation_hit=last['with_revelation_hit'],
            without_revelation_hit=last['without_revelation_hit'],
            with_revelation_fa=last['with_revelation_fa'],
            without_revelation_fa=last['without_revelation_fa'],
            revelation_effect=last['revelation_effect']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'items': len(self._system._items),
            'trials': len(self._system._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_revelation_engine() -> RevelationEngine:
    """Create revelation engine."""
    return RevelationEngine()


def demonstrate_revelation_effect() -> Dict[str, Any]:
    """Demonstrate revelation effect."""
    engine = create_revelation_engine()

    # Classic
    classic = engine.run_classic()

    # Tasks
    tasks = engine.study_tasks()

    # Difficulty
    difficulty = engine.study_difficulty()

    # SDT
    sdt = engine.run_sdt_analysis()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'with_hit': f"{classic['with_revelation_hit']:.0%}",
            'without_hit': f"{classic['without_revelation_hit']:.0%}",
            'with_fa': f"{classic['with_revelation_fa']:.0%}",
            'without_fa': f"{classic['without_revelation_fa']:.0%}",
            'effect': f"{classic['revelation_effect']:.0%}"
        },
        'sdt': {
            'criterion_shift': f"{sdt['criterion_difference']:.2f}"
        },
        'mechanisms': list(mechanisms['mechanisms'].keys()),
        'interpretation': (
            f"Revelation effect: {classic['revelation_effect']:.0%}. "
            f"Task before judgment increases 'old' responses. "
            f"Criterion shift + fluency misattribution."
        )
    }


def get_revelation_effect_facts() -> Dict[str, str]:
    """Get facts about revelation effect."""
    return {
        'westerman_greene': 'Original discovery',
        'effect': 'Task increases old/familiar judgments',
        'false_alarm': 'Larger effect on false alarms',
        'unrelated': 'Even unrelated tasks work',
        'mechanism': 'Criterion shift + fluency',
        'warning': 'Warning reduces but doesn\'t eliminate',
        'robust': 'Robust across many paradigms',
        'false_memory': 'Increases false recognition'
    }
