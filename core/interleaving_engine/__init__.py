"""
BAEL Interleaving Engine
=========================

Interleaved practice effects.
Mixed vs blocked learning.

"Ba'el mixes for mastery." — Ba'el
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

logger = logging.getLogger("BAEL.Interleaving")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class PracticeSchedule(Enum):
    """Types of practice schedules."""
    BLOCKED = auto()       # AAA BBB CCC
    INTERLEAVED = auto()   # ABC ABC ABC
    RANDOM = auto()        # Random order
    HYBRID = auto()        # Initial blocked, then interleaved


class SkillType(Enum):
    """Types of skills."""
    MOTOR = auto()         # Physical skills
    COGNITIVE = auto()     # Mental skills
    PERCEPTUAL = auto()    # Recognition skills
    PROBLEM_SOLVING = auto()


class DifficultyLevel(Enum):
    """Difficulty levels."""
    EASY = 1
    MEDIUM = 2
    HARD = 3


@dataclass
class Skill:
    """
    A skill or category to learn.
    """
    id: str
    name: str
    skill_type: SkillType
    examples: List[Any]
    strength: float = 0.5
    discrimination: float = 0.5


@dataclass
class PracticeItem:
    """
    An item to practice.
    """
    id: str
    skill_id: str
    content: Any
    correct_response: Any
    difficulty: DifficultyLevel


@dataclass
class Trial:
    """
    A practice trial.
    """
    item_id: str
    skill_id: str
    schedule: PracticeSchedule
    response: Any
    correct: bool
    response_time: float
    trial_number: int


@dataclass
class PerformanceBlock:
    """
    Performance in a block.
    """
    schedule: PracticeSchedule
    trials: List[Trial]
    accuracy: float
    mean_rt: float


@dataclass
class InterleavingMetrics:
    """
    Interleaving effect metrics.
    """
    blocked_acquisition: float
    interleaved_acquisition: float
    blocked_retention: float
    interleaved_retention: float
    interleaving_benefit: float


# ============================================================================
# PRACTICE SCHEDULER
# ============================================================================

class PracticeScheduler:
    """
    Generate practice schedules.

    "Ba'el schedules practice." — Ba'el
    """

    def __init__(self):
        """Initialize scheduler."""
        self._lock = threading.RLock()

    def create_blocked_schedule(
        self,
        skills: List[Skill],
        trials_per_skill: int
    ) -> List[PracticeItem]:
        """Create blocked practice schedule."""
        items = []

        for skill in skills:
            for i in range(trials_per_skill):
                if skill.examples:
                    example = skill.examples[i % len(skill.examples)]
                else:
                    example = f"{skill.name}_{i}"

                items.append(PracticeItem(
                    id=f"{skill.id}_{i}",
                    skill_id=skill.id,
                    content=example,
                    correct_response=skill.name,
                    difficulty=DifficultyLevel.MEDIUM
                ))

        return items

    def create_interleaved_schedule(
        self,
        skills: List[Skill],
        trials_per_skill: int
    ) -> List[PracticeItem]:
        """Create interleaved practice schedule."""
        items = []

        for i in range(trials_per_skill):
            for skill in skills:
                if skill.examples:
                    example = skill.examples[i % len(skill.examples)]
                else:
                    example = f"{skill.name}_{i}"

                items.append(PracticeItem(
                    id=f"{skill.id}_{i}",
                    skill_id=skill.id,
                    content=example,
                    correct_response=skill.name,
                    difficulty=DifficultyLevel.MEDIUM
                ))

        return items

    def create_random_schedule(
        self,
        skills: List[Skill],
        trials_per_skill: int
    ) -> List[PracticeItem]:
        """Create random practice schedule."""
        items = self.create_blocked_schedule(skills, trials_per_skill)
        random.shuffle(items)
        return items

    def create_hybrid_schedule(
        self,
        skills: List[Skill],
        trials_per_skill: int,
        blocked_ratio: float = 0.3
    ) -> List[PracticeItem]:
        """Create hybrid schedule (blocked then interleaved)."""
        blocked_trials = int(trials_per_skill * blocked_ratio)
        interleaved_trials = trials_per_skill - blocked_trials

        blocked_items = self.create_blocked_schedule(skills, blocked_trials)
        interleaved_items = self.create_interleaved_schedule(skills, interleaved_trials)

        return blocked_items + interleaved_items


# ============================================================================
# LEARNING SIMULATOR
# ============================================================================

class LearningSimulator:
    """
    Simulate learning under different schedules.

    "Ba'el simulates learning." — Ba'el
    """

    def __init__(self):
        """Initialize simulator."""
        self._skills: Dict[str, Skill] = {}
        self._lock = threading.RLock()

    def register_skill(
        self,
        skill: Skill
    ) -> None:
        """Register a skill."""
        self._skills[skill.id] = skill

    def practice_trial(
        self,
        item: PracticeItem,
        schedule: PracticeSchedule,
        trial_number: int,
        previous_skill: Optional[str] = None
    ) -> Trial:
        """Simulate a single practice trial."""
        skill = self._skills.get(item.skill_id)

        if not skill:
            return Trial(
                item_id=item.id,
                skill_id=item.skill_id,
                schedule=schedule,
                response=None,
                correct=False,
                response_time=0.0,
                trial_number=trial_number
            )

        # Calculate performance probability
        base_prob = skill.strength

        # Schedule effects
        if schedule == PracticeSchedule.BLOCKED:
            # Blocked: high during acquisition (repetition priming)
            if previous_skill == item.skill_id:
                base_prob += 0.15  # Same skill = easier

        elif schedule in [PracticeSchedule.INTERLEAVED, PracticeSchedule.RANDOM]:
            # Interleaved: harder during acquisition (desirable difficulty)
            if previous_skill != item.skill_id and previous_skill is not None:
                base_prob -= 0.1  # Switch cost

            # But improves discrimination
            skill.discrimination += 0.02

        # Difficulty adjustment
        difficulty_factor = {
            DifficultyLevel.EASY: 0.1,
            DifficultyLevel.MEDIUM: 0.0,
            DifficultyLevel.HARD: -0.1
        }
        base_prob += difficulty_factor.get(item.difficulty, 0.0)

        # Ensure bounds
        base_prob = max(0.1, min(0.95, base_prob))

        correct = random.random() < base_prob

        # Learning: update skill strength
        if correct:
            skill.strength = min(1.0, skill.strength + 0.03)
        else:
            skill.strength = max(0.0, skill.strength - 0.01)

        # Response time (blocked faster during acquisition)
        base_rt = 1.5
        if schedule == PracticeSchedule.BLOCKED and previous_skill == item.skill_id:
            base_rt -= 0.3
        elif schedule == PracticeSchedule.INTERLEAVED and previous_skill != item.skill_id:
            base_rt += 0.2

        response_time = base_rt + random.uniform(-0.3, 0.5)

        return Trial(
            item_id=item.id,
            skill_id=item.skill_id,
            schedule=schedule,
            response=item.correct_response if correct else "wrong",
            correct=correct,
            response_time=max(0.3, response_time),
            trial_number=trial_number
        )

    def simulate_retention_test(
        self,
        skill_id: str,
        schedule: PracticeSchedule
    ) -> float:
        """Simulate retention test performance."""
        skill = self._skills.get(skill_id)

        if not skill:
            return 0.0

        # Retention depends on:
        # 1. Skill strength
        # 2. Discrimination (higher for interleaved)
        # 3. Schedule type

        base_retention = skill.strength * 0.7 + skill.discrimination * 0.3

        # Interleaved has retention advantage
        if schedule == PracticeSchedule.INTERLEAVED:
            base_retention += 0.1
        elif schedule == PracticeSchedule.BLOCKED:
            base_retention -= 0.05

        return min(1.0, max(0.0, base_retention))

    def apply_forgetting(
        self,
        days: float = 7
    ) -> None:
        """Apply forgetting over time."""
        decay_rate = 0.02 * days

        for skill in self._skills.values():
            skill.strength = max(0.1, skill.strength - decay_rate)
            # Discrimination decays slower
            skill.discrimination = max(0.1, skill.discrimination - decay_rate * 0.5)


# ============================================================================
# INTERLEAVING ENGINE
# ============================================================================

class InterleavingEngine:
    """
    Complete interleaving engine.

    "Ba'el's interleaved practice system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._scheduler = PracticeScheduler()
        self._simulator = LearningSimulator()

        self._skills: Dict[str, Skill] = {}
        self._trials: List[Trial] = []
        self._blocks: List[PerformanceBlock] = []

        self._skill_counter = 0

        self._lock = threading.RLock()

    def _generate_skill_id(self) -> str:
        self._skill_counter += 1
        return f"skill_{self._skill_counter}"

    # Skill management

    def add_skill(
        self,
        name: str,
        skill_type: SkillType,
        examples: List[Any] = None
    ) -> Skill:
        """Add a skill to learn."""
        skill = Skill(
            id=self._generate_skill_id(),
            name=name,
            skill_type=skill_type,
            examples=examples or [f"{name}_example_{i}" for i in range(5)]
        )

        self._skills[skill.id] = skill
        self._simulator.register_skill(skill)

        return skill

    # Practice sessions

    def run_practice_session(
        self,
        schedule: PracticeSchedule,
        trials_per_skill: int = 10
    ) -> PerformanceBlock:
        """Run a practice session with specified schedule."""
        skills = list(self._skills.values())

        # Create schedule
        if schedule == PracticeSchedule.BLOCKED:
            items = self._scheduler.create_blocked_schedule(skills, trials_per_skill)
        elif schedule == PracticeSchedule.INTERLEAVED:
            items = self._scheduler.create_interleaved_schedule(skills, trials_per_skill)
        elif schedule == PracticeSchedule.RANDOM:
            items = self._scheduler.create_random_schedule(skills, trials_per_skill)
        elif schedule == PracticeSchedule.HYBRID:
            items = self._scheduler.create_hybrid_schedule(skills, trials_per_skill)
        else:
            items = self._scheduler.create_blocked_schedule(skills, trials_per_skill)

        # Run trials
        session_trials = []
        previous_skill = None

        for i, item in enumerate(items):
            trial = self._simulator.practice_trial(
                item, schedule, i, previous_skill
            )
            session_trials.append(trial)
            self._trials.append(trial)
            previous_skill = item.skill_id

        # Calculate block performance
        accuracy = sum(1 for t in session_trials if t.correct) / len(session_trials)
        mean_rt = sum(t.response_time for t in session_trials) / len(session_trials)

        block = PerformanceBlock(
            schedule=schedule,
            trials=session_trials,
            accuracy=accuracy,
            mean_rt=mean_rt
        )

        self._blocks.append(block)
        return block

    def run_retention_test(
        self,
        delay_days: float = 7
    ) -> Dict[str, float]:
        """Run retention test after delay."""
        # Apply forgetting
        self._simulator.apply_forgetting(delay_days)

        results = {}

        for skill_id, skill in self._skills.items():
            # Determine schedule used for this skill
            skill_trials = [t for t in self._trials if t.skill_id == skill_id]

            if skill_trials:
                schedule = skill_trials[0].schedule
                retention = self._simulator.simulate_retention_test(skill_id, schedule)
                results[skill.name] = retention

        return results

    # Comparison experiment

    def run_comparison_experiment(
        self,
        trials_per_skill: int = 20,
        delay_days: float = 7
    ) -> Dict[str, Any]:
        """Run blocked vs interleaved comparison."""
        # Store initial state
        initial_skills = {k: copy.copy(v) for k, v in self._skills.items()}

        # Run blocked condition
        self._reset_skills()
        blocked_block = self.run_practice_session(
            PracticeSchedule.BLOCKED, trials_per_skill
        )
        blocked_retention = self.run_retention_test(delay_days)

        # Reset and run interleaved condition
        self._reset_skills()
        self._trials = []
        self._blocks = []

        interleaved_block = self.run_practice_session(
            PracticeSchedule.INTERLEAVED, trials_per_skill
        )
        interleaved_retention = self.run_retention_test(delay_days)

        return {
            'blocked_acquisition': blocked_block.accuracy,
            'interleaved_acquisition': interleaved_block.accuracy,
            'blocked_retention': sum(blocked_retention.values()) / len(blocked_retention) if blocked_retention else 0,
            'interleaved_retention': sum(interleaved_retention.values()) / len(interleaved_retention) if interleaved_retention else 0,
            'blocked_rt': blocked_block.mean_rt,
            'interleaved_rt': interleaved_block.mean_rt
        }

    def _reset_skills(self) -> None:
        """Reset skills to initial state."""
        for skill in self._skills.values():
            skill.strength = 0.5
            skill.discrimination = 0.5

    # Analysis

    def get_learning_curves(self) -> Dict[PracticeSchedule, List[float]]:
        """Get learning curves by schedule."""
        curves = defaultdict(list)

        for block in self._blocks:
            # Calculate accuracy over trials
            window_size = 5
            accuracies = []

            for i in range(0, len(block.trials), window_size):
                window = block.trials[i:i + window_size]
                acc = sum(1 for t in window if t.correct) / len(window)
                accuracies.append(acc)

            curves[block.schedule] = accuracies

        return dict(curves)

    # Metrics

    def get_metrics(self) -> InterleavingMetrics:
        """Get interleaving metrics."""
        blocked_blocks = [b for b in self._blocks if b.schedule == PracticeSchedule.BLOCKED]
        interleaved_blocks = [b for b in self._blocks if b.schedule == PracticeSchedule.INTERLEAVED]

        blocked_acq = (
            sum(b.accuracy for b in blocked_blocks) / len(blocked_blocks)
            if blocked_blocks else 0.0
        )
        interleaved_acq = (
            sum(b.accuracy for b in interleaved_blocks) / len(interleaved_blocks)
            if interleaved_blocks else 0.0
        )

        # Run quick retention test
        blocked_ret = sum(
            self._simulator.simulate_retention_test(s.id, PracticeSchedule.BLOCKED)
            for s in self._skills.values()
        ) / len(self._skills) if self._skills else 0.0

        interleaved_ret = sum(
            self._simulator.simulate_retention_test(s.id, PracticeSchedule.INTERLEAVED)
            for s in self._skills.values()
        ) / len(self._skills) if self._skills else 0.0

        return InterleavingMetrics(
            blocked_acquisition=blocked_acq,
            interleaved_acquisition=interleaved_acq,
            blocked_retention=blocked_ret,
            interleaved_retention=interleaved_ret,
            interleaving_benefit=interleaved_ret - blocked_ret
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'skills': len(self._skills),
            'trials': len(self._trials),
            'blocks': len(self._blocks)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_interleaving_engine() -> InterleavingEngine:
    """Create interleaving engine."""
    return InterleavingEngine()


def demonstrate_interleaving_effect() -> Dict[str, Any]:
    """Demonstrate the interleaving effect."""
    engine = create_interleaving_engine()

    # Add skills to learn
    engine.add_skill("category_A", SkillType.COGNITIVE)
    engine.add_skill("category_B", SkillType.COGNITIVE)
    engine.add_skill("category_C", SkillType.COGNITIVE)

    # Run comparison
    results = engine.run_comparison_experiment(
        trials_per_skill=15,
        delay_days=7
    )

    results['interpretation'] = (
        'Interleaving: worse during practice, better on test'
        if results['blocked_acquisition'] > results['interleaved_acquisition']
        and results['interleaved_retention'] > results['blocked_retention']
        else 'Desirable difficulty effect demonstrated'
    )

    return results


def get_interleaving_facts() -> Dict[str, str]:
    """Get facts about interleaving."""
    return {
        'rohrer_2012': 'Interleaving benefits category learning',
        'definition': 'Mixing practice of different skills/categories',
        'acquisition': 'Blocked better during initial learning',
        'retention': 'Interleaved better for long-term retention',
        'discrimination': 'Interleaving improves discrimination',
        'desirable_difficulty': 'Harder practice leads to better learning',
        'spacing': 'Interleaving provides natural spacing',
        'motor_learning': 'Effect demonstrated in motor skill learning'
    }
