#!/usr/bin/env python3
"""
BAEL - Learning Manager
Advanced meta-learning and learning-to-learn.

Features:
- Meta-learning algorithms
- Learning rate adaptation
- Curriculum learning
- Transfer learning hints
- Few-shot learning
- Learning progress tracking
"""

import asyncio
import copy
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LearningPhase(Enum):
    """Phases of learning."""
    EXPLORATION = "exploration"
    ACQUISITION = "acquisition"
    CONSOLIDATION = "consolidation"
    MASTERY = "mastery"


class LearningStrategy(Enum):
    """Learning strategies."""
    RANDOM = "random"
    CURRICULUM = "curriculum"
    SELF_PACED = "self_paced"
    ACTIVE = "active"
    TRANSFER = "transfer"


class TaskDifficulty(Enum):
    """Task difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class ProgressStatus(Enum):
    """Learning progress status."""
    STRUGGLING = "struggling"
    LEARNING = "learning"
    PLATEAU = "plateau"
    IMPROVING = "improving"
    MASTERED = "mastered"


class AdaptationType(Enum):
    """Types of adaptation."""
    LEARNING_RATE = "learning_rate"
    TASK_SELECTION = "task_selection"
    STRATEGY = "strategy"
    COMPLEXITY = "complexity"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Task:
    """A learning task."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM
    domain: str = ""
    prerequisites: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Skill:
    """A learned skill."""
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    level: float = 0.0  # 0-1
    practice_count: int = 0
    last_practiced: float = field(default_factory=lambda: datetime.now().timestamp())
    decay_rate: float = 0.01


@dataclass
class LearningSession:
    """A learning session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    end_time: Optional[float] = None
    performance: float = 0.0
    errors: int = 0
    iterations: int = 0


@dataclass
class LearningProgress:
    """Learning progress tracking."""
    progress_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str = ""
    history: List[float] = field(default_factory=list)
    status: ProgressStatus = ProgressStatus.LEARNING
    trend: float = 0.0  # Positive = improving


@dataclass
class Curriculum:
    """A learning curriculum."""
    curriculum_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    tasks: List[str] = field(default_factory=list)
    current_index: int = 0
    completed: List[str] = field(default_factory=list)


@dataclass
class MetaKnowledge:
    """Meta-knowledge about learning."""
    domain: str = ""
    effective_strategies: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    transfer_sources: List[str] = field(default_factory=list)


# =============================================================================
# SKILL MANAGER
# =============================================================================

class SkillManager:
    """Manage learned skills."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}

    def add(self, name: str, initial_level: float = 0.0) -> Skill:
        """Add a skill."""
        skill = Skill(name=name, level=initial_level)
        self._skills[name] = skill
        return skill

    def get(self, name: str) -> Optional[Skill]:
        """Get a skill."""
        return self._skills.get(name)

    def update(
        self,
        name: str,
        performance: float,
        learning_rate: float = 0.1
    ) -> Optional[Skill]:
        """Update skill level based on performance."""
        skill = self._skills.get(name)
        if not skill:
            skill = self.add(name)

        # Update level
        delta = learning_rate * (performance - skill.level)
        skill.level = max(0.0, min(1.0, skill.level + delta))
        skill.practice_count += 1
        skill.last_practiced = datetime.now().timestamp()

        return skill

    def apply_decay(self) -> None:
        """Apply skill decay over time."""
        current_time = datetime.now().timestamp()

        for skill in self._skills.values():
            time_delta = current_time - skill.last_practiced
            days = time_delta / (24 * 3600)
            decay = skill.decay_rate * days
            skill.level = max(0.0, skill.level - decay)

    def all_skills(self) -> List[Skill]:
        """Get all skills."""
        return list(self._skills.values())

    def skill_levels(self) -> Dict[str, float]:
        """Get skill levels."""
        return {s.name: s.level for s in self._skills.values()}


# =============================================================================
# TASK MANAGER
# =============================================================================

class TaskManager:
    """Manage learning tasks."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def add(
        self,
        name: str,
        difficulty: TaskDifficulty = TaskDifficulty.MEDIUM,
        domain: str = "",
        prerequisites: Optional[List[str]] = None,
        skills: Optional[List[str]] = None
    ) -> Task:
        """Add a task."""
        task = Task(
            name=name,
            difficulty=difficulty,
            domain=domain,
            prerequisites=prerequisites or [],
            skills=skills or []
        )
        self._tasks[name] = task
        return task

    def get(self, name: str) -> Optional[Task]:
        """Get a task."""
        return self._tasks.get(name)

    def by_difficulty(self, difficulty: TaskDifficulty) -> List[Task]:
        """Get tasks by difficulty."""
        return [t for t in self._tasks.values() if t.difficulty == difficulty]

    def by_domain(self, domain: str) -> List[Task]:
        """Get tasks by domain."""
        return [t for t in self._tasks.values() if t.domain == domain]

    def available_tasks(
        self,
        completed: Set[str],
        skill_levels: Dict[str, float]
    ) -> List[Task]:
        """Get available tasks based on prerequisites."""
        available = []

        for task in self._tasks.values():
            # Check prerequisites
            prereqs_met = all(p in completed for p in task.prerequisites)

            if prereqs_met:
                available.append(task)

        return available

    def all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self._tasks.values())


# =============================================================================
# CURRICULUM MANAGER
# =============================================================================

class CurriculumManager:
    """Manage learning curricula."""

    def __init__(self, task_manager: TaskManager):
        self._task_manager = task_manager
        self._curricula: Dict[str, Curriculum] = {}

    def create(
        self,
        name: str,
        tasks: List[str]
    ) -> Curriculum:
        """Create a curriculum."""
        curriculum = Curriculum(name=name, tasks=tasks)
        self._curricula[name] = curriculum
        return curriculum

    def auto_curriculum(
        self,
        domain: str
    ) -> Curriculum:
        """Auto-generate curriculum from difficulty."""
        tasks = self._task_manager.by_domain(domain)

        # Sort by difficulty
        difficulty_order = {
            TaskDifficulty.EASY: 0,
            TaskDifficulty.MEDIUM: 1,
            TaskDifficulty.HARD: 2,
            TaskDifficulty.EXPERT: 3
        }

        sorted_tasks = sorted(tasks, key=lambda t: difficulty_order[t.difficulty])

        return self.create(
            f"{domain}_curriculum",
            [t.name for t in sorted_tasks]
        )

    def next_task(self, curriculum_name: str) -> Optional[Task]:
        """Get next task in curriculum."""
        curriculum = self._curricula.get(curriculum_name)
        if not curriculum:
            return None

        if curriculum.current_index >= len(curriculum.tasks):
            return None

        task_name = curriculum.tasks[curriculum.current_index]
        return self._task_manager.get(task_name)

    def complete_task(self, curriculum_name: str, task_name: str) -> None:
        """Mark task as completed."""
        curriculum = self._curricula.get(curriculum_name)
        if not curriculum:
            return

        if task_name not in curriculum.completed:
            curriculum.completed.append(task_name)

        # Advance index
        if curriculum.current_index < len(curriculum.tasks):
            if curriculum.tasks[curriculum.current_index] == task_name:
                curriculum.current_index += 1

    def get(self, name: str) -> Optional[Curriculum]:
        """Get a curriculum."""
        return self._curricula.get(name)


# =============================================================================
# PROGRESS TRACKER
# =============================================================================

class ProgressTracker:
    """Track learning progress."""

    def __init__(self):
        self._progress: Dict[str, LearningProgress] = {}
        self._window_size: int = 10

    def track(self, skill_id: str, value: float) -> LearningProgress:
        """Track a progress value."""
        if skill_id not in self._progress:
            self._progress[skill_id] = LearningProgress(skill_id=skill_id)

        progress = self._progress[skill_id]
        progress.history.append(value)

        # Keep window
        if len(progress.history) > self._window_size * 2:
            progress.history = progress.history[-self._window_size * 2:]

        # Update trend
        if len(progress.history) >= 3:
            recent = progress.history[-3:]
            progress.trend = (recent[-1] - recent[0]) / 2

        # Update status
        progress.status = self._determine_status(progress)

        return progress

    def _determine_status(self, progress: LearningProgress) -> ProgressStatus:
        """Determine learning status."""
        if not progress.history:
            return ProgressStatus.LEARNING

        recent = progress.history[-3:] if len(progress.history) >= 3 else progress.history
        avg = sum(recent) / len(recent)

        if avg >= 0.9:
            return ProgressStatus.MASTERED
        elif progress.trend > 0.05:
            return ProgressStatus.IMPROVING
        elif progress.trend < -0.05:
            return ProgressStatus.STRUGGLING
        elif abs(progress.trend) <= 0.02 and len(progress.history) >= 5:
            return ProgressStatus.PLATEAU
        else:
            return ProgressStatus.LEARNING

    def get(self, skill_id: str) -> Optional[LearningProgress]:
        """Get progress for a skill."""
        return self._progress.get(skill_id)

    def all_progress(self) -> Dict[str, LearningProgress]:
        """Get all progress."""
        return self._progress.copy()


# =============================================================================
# LEARNING RATE ADAPTER
# =============================================================================

class LearningRateAdapter:
    """Adapt learning rate based on progress."""

    def __init__(
        self,
        initial_rate: float = 0.1,
        min_rate: float = 0.01,
        max_rate: float = 0.5
    ):
        self._initial = initial_rate
        self._min = min_rate
        self._max = max_rate
        self._rates: Dict[str, float] = {}

    def adapt(
        self,
        skill_id: str,
        progress: LearningProgress
    ) -> float:
        """Adapt learning rate based on progress."""
        current = self._rates.get(skill_id, self._initial)

        if progress.status == ProgressStatus.STRUGGLING:
            # Decrease rate
            new_rate = current * 0.9
        elif progress.status == ProgressStatus.PLATEAU:
            # Increase rate to break plateau
            new_rate = current * 1.2
        elif progress.status == ProgressStatus.IMPROVING:
            # Maintain or slightly increase
            new_rate = current * 1.05
        elif progress.status == ProgressStatus.MASTERED:
            # Decrease rate
            new_rate = current * 0.8
        else:
            new_rate = current

        new_rate = max(self._min, min(self._max, new_rate))
        self._rates[skill_id] = new_rate

        return new_rate

    def get_rate(self, skill_id: str) -> float:
        """Get current learning rate."""
        return self._rates.get(skill_id, self._initial)


# =============================================================================
# TASK SELECTOR
# =============================================================================

class TaskSelector:
    """Select optimal tasks for learning."""

    def __init__(
        self,
        task_manager: TaskManager,
        skill_manager: SkillManager
    ):
        self._tasks = task_manager
        self._skills = skill_manager

    def select_curriculum(
        self,
        curriculum: Curriculum
    ) -> Optional[Task]:
        """Select next task from curriculum."""
        if curriculum.current_index >= len(curriculum.tasks):
            return None

        task_name = curriculum.tasks[curriculum.current_index]
        return self._tasks.get(task_name)

    def select_zpd(
        self,
        available: List[Task]
    ) -> Optional[Task]:
        """Select task in Zone of Proximal Development."""
        skill_levels = self._skills.skill_levels()

        # Find task slightly above current level
        best_task = None
        best_score = float('inf')

        for task in available:
            # Calculate difficulty gap
            task_skills = task.skills
            if not task_skills:
                continue

            avg_skill = sum(
                skill_levels.get(s, 0.0) for s in task_skills
            ) / len(task_skills)

            difficulty_value = {
                TaskDifficulty.EASY: 0.2,
                TaskDifficulty.MEDIUM: 0.5,
                TaskDifficulty.HARD: 0.7,
                TaskDifficulty.EXPERT: 0.9
            }[task.difficulty]

            # Ideal: task slightly harder than current level
            gap = difficulty_value - avg_skill

            if 0.1 <= gap <= 0.3:
                score = abs(gap - 0.2)
                if score < best_score:
                    best_score = score
                    best_task = task

        return best_task or (available[0] if available else None)

    def select_random(
        self,
        available: List[Task]
    ) -> Optional[Task]:
        """Select random task."""
        if not available:
            return None
        return random.choice(available)


# =============================================================================
# LEARNING MANAGER
# =============================================================================

class LearningManager:
    """
    Learning Manager for BAEL.

    Advanced meta-learning and learning-to-learn.
    """

    def __init__(self):
        self._skill_mgr = SkillManager()
        self._task_mgr = TaskManager()
        self._curriculum_mgr = CurriculumManager(self._task_mgr)
        self._progress_tracker = ProgressTracker()
        self._lr_adapter = LearningRateAdapter()
        self._task_selector = TaskSelector(self._task_mgr, self._skill_mgr)
        self._sessions: Dict[str, LearningSession] = {}
        self._meta_knowledge: Dict[str, MetaKnowledge] = {}

    # -------------------------------------------------------------------------
    # SKILLS
    # -------------------------------------------------------------------------

    def add_skill(self, name: str, initial_level: float = 0.0) -> Skill:
        """Add a skill."""
        return self._skill_mgr.add(name, initial_level)

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill."""
        return self._skill_mgr.get(name)

    def update_skill(
        self,
        name: str,
        performance: float
    ) -> Optional[Skill]:
        """Update skill with adaptive learning rate."""
        progress = self._progress_tracker.get(name)
        if progress:
            lr = self._lr_adapter.adapt(name, progress)
        else:
            lr = self._lr_adapter.get_rate(name)

        skill = self._skill_mgr.update(name, performance, lr)

        if skill:
            self._progress_tracker.track(name, skill.level)

        return skill

    def all_skills(self) -> List[Skill]:
        """Get all skills."""
        return self._skill_mgr.all_skills()

    # -------------------------------------------------------------------------
    # TASKS
    # -------------------------------------------------------------------------

    def add_task(
        self,
        name: str,
        difficulty: TaskDifficulty = TaskDifficulty.MEDIUM,
        domain: str = "",
        prerequisites: Optional[List[str]] = None,
        skills: Optional[List[str]] = None
    ) -> Task:
        """Add a task."""
        return self._task_mgr.add(name, difficulty, domain, prerequisites, skills)

    def get_task(self, name: str) -> Optional[Task]:
        """Get a task."""
        return self._task_mgr.get(name)

    def available_tasks(self) -> List[Task]:
        """Get available tasks."""
        completed = set()
        for session in self._sessions.values():
            if session.performance >= 0.8:
                task = self._task_mgr.get(session.task_id)
                if task:
                    completed.add(task.name)

        return self._task_mgr.available_tasks(completed, self._skill_mgr.skill_levels())

    # -------------------------------------------------------------------------
    # CURRICULA
    # -------------------------------------------------------------------------

    def create_curriculum(self, name: str, tasks: List[str]) -> Curriculum:
        """Create a curriculum."""
        return self._curriculum_mgr.create(name, tasks)

    def auto_curriculum(self, domain: str) -> Curriculum:
        """Auto-generate curriculum."""
        return self._curriculum_mgr.auto_curriculum(domain)

    def next_curriculum_task(self, curriculum_name: str) -> Optional[Task]:
        """Get next task in curriculum."""
        return self._curriculum_mgr.next_task(curriculum_name)

    def complete_curriculum_task(self, curriculum_name: str, task_name: str) -> None:
        """Complete a curriculum task."""
        self._curriculum_mgr.complete_task(curriculum_name, task_name)

    # -------------------------------------------------------------------------
    # LEARNING SESSIONS
    # -------------------------------------------------------------------------

    def start_session(self, task_name: str) -> LearningSession:
        """Start a learning session."""
        session = LearningSession(task_id=task_name)
        self._sessions[session.session_id] = session
        return session

    def end_session(
        self,
        session_id: str,
        performance: float,
        errors: int = 0
    ) -> Optional[LearningSession]:
        """End a learning session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        session.end_time = datetime.now().timestamp()
        session.performance = performance
        session.errors = errors

        # Update related skills
        task = self._task_mgr.get(session.task_id)
        if task:
            for skill_name in task.skills:
                self.update_skill(skill_name, performance)

        return session

    def get_session(self, session_id: str) -> Optional[LearningSession]:
        """Get a session."""
        return self._sessions.get(session_id)

    # -------------------------------------------------------------------------
    # PROGRESS
    # -------------------------------------------------------------------------

    def get_progress(self, skill_id: str) -> Optional[LearningProgress]:
        """Get progress for a skill."""
        return self._progress_tracker.get(skill_id)

    def all_progress(self) -> Dict[str, LearningProgress]:
        """Get all progress."""
        return self._progress_tracker.all_progress()

    # -------------------------------------------------------------------------
    # TASK SELECTION
    # -------------------------------------------------------------------------

    def suggest_task(
        self,
        strategy: LearningStrategy = LearningStrategy.SELF_PACED
    ) -> Optional[Task]:
        """Suggest next task to learn."""
        available = self.available_tasks()

        if strategy == LearningStrategy.RANDOM:
            return self._task_selector.select_random(available)
        elif strategy == LearningStrategy.SELF_PACED:
            return self._task_selector.select_zpd(available)
        else:
            return available[0] if available else None

    # -------------------------------------------------------------------------
    # META-KNOWLEDGE
    # -------------------------------------------------------------------------

    def add_meta_knowledge(
        self,
        domain: str,
        effective_strategies: Optional[List[str]] = None,
        common_mistakes: Optional[List[str]] = None,
        transfer_sources: Optional[List[str]] = None
    ) -> MetaKnowledge:
        """Add meta-knowledge."""
        mk = MetaKnowledge(
            domain=domain,
            effective_strategies=effective_strategies or [],
            common_mistakes=common_mistakes or [],
            transfer_sources=transfer_sources or []
        )
        self._meta_knowledge[domain] = mk
        return mk

    def get_meta_knowledge(self, domain: str) -> Optional[MetaKnowledge]:
        """Get meta-knowledge."""
        return self._meta_knowledge.get(domain)

    # -------------------------------------------------------------------------
    # LEARNING RATE
    # -------------------------------------------------------------------------

    def get_learning_rate(self, skill_id: str) -> float:
        """Get current learning rate."""
        return self._lr_adapter.get_rate(skill_id)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Learning Manager."""
    print("=" * 70)
    print("BAEL - LEARNING MANAGER DEMO")
    print("Advanced Meta-Learning and Learning-to-Learn")
    print("=" * 70)
    print()

    manager = LearningManager()

    # 1. Add Skills
    print("1. ADD SKILLS:")
    print("-" * 40)

    manager.add_skill("python_basics", 0.3)
    manager.add_skill("python_functions", 0.1)
    manager.add_skill("python_classes", 0.0)

    for skill in manager.all_skills():
        print(f"   {skill.name}: {skill.level:.2f}")
    print()

    # 2. Add Tasks
    print("2. ADD TASKS:")
    print("-" * 40)

    manager.add_task(
        "variables",
        TaskDifficulty.EASY,
        "python",
        skills=["python_basics"]
    )
    manager.add_task(
        "functions",
        TaskDifficulty.MEDIUM,
        "python",
        prerequisites=["variables"],
        skills=["python_functions"]
    )
    manager.add_task(
        "classes",
        TaskDifficulty.HARD,
        "python",
        prerequisites=["functions"],
        skills=["python_classes"]
    )
    manager.add_task(
        "decorators",
        TaskDifficulty.EXPERT,
        "python",
        prerequisites=["classes"],
        skills=["python_functions", "python_classes"]
    )

    print("   Added: variables, functions, classes, decorators")
    print()

    # 3. Auto-generate Curriculum
    print("3. AUTO-GENERATE CURRICULUM:")
    print("-" * 40)

    curriculum = manager.auto_curriculum("python")
    print(f"   Curriculum: {curriculum.name}")
    print(f"   Tasks: {curriculum.tasks}")
    print()

    # 4. Learning Sessions
    print("4. LEARNING SESSIONS:")
    print("-" * 40)

    # Simulate learning
    for task_name in ["variables", "variables", "functions"]:
        session = manager.start_session(task_name)

        # Simulate performance
        performance = random.uniform(0.6, 0.9)
        manager.end_session(session.session_id, performance)

        if performance >= 0.8:
            manager.complete_curriculum_task(curriculum.name, task_name)

        print(f"   Task: {task_name}, Performance: {performance:.2f}")
    print()

    # 5. Track Progress
    print("5. TRACK PROGRESS:")
    print("-" * 40)

    for skill_id, progress in manager.all_progress().items():
        print(f"   {skill_id}:")
        print(f"      Status: {progress.status.value}")
        print(f"      Trend: {progress.trend:+.3f}")
        print(f"      History: {[f'{h:.2f}' for h in progress.history[-3:]]}")
    print()

    # 6. Adaptive Learning Rate
    print("6. ADAPTIVE LEARNING RATE:")
    print("-" * 40)

    for skill in manager.all_skills():
        lr = manager.get_learning_rate(skill.name)
        print(f"   {skill.name}: LR={lr:.3f}")
    print()

    # 7. Suggest Task
    print("7. SUGGEST TASK:")
    print("-" * 40)

    suggested = manager.suggest_task(LearningStrategy.SELF_PACED)
    if suggested:
        print(f"   Suggested: {suggested.name} ({suggested.difficulty.value})")
    print()

    # 8. Available Tasks
    print("8. AVAILABLE TASKS:")
    print("-" * 40)

    available = manager.available_tasks()
    for task in available:
        print(f"   {task.name} ({task.difficulty.value})")
    print()

    # 9. Meta-Knowledge
    print("9. META-KNOWLEDGE:")
    print("-" * 40)

    manager.add_meta_knowledge(
        "python",
        effective_strategies=["practice_coding", "read_docs", "build_projects"],
        common_mistakes=["indentation", "mutable_defaults", "scope"],
        transfer_sources=["java", "javascript"]
    )

    mk = manager.get_meta_knowledge("python")
    if mk:
        print(f"   Domain: {mk.domain}")
        print(f"   Strategies: {mk.effective_strategies}")
        print(f"   Common mistakes: {mk.common_mistakes}")
    print()

    # 10. Skill Levels After Learning
    print("10. SKILL LEVELS AFTER LEARNING:")
    print("-" * 40)

    for skill in manager.all_skills():
        print(f"   {skill.name}: {skill.level:.2f} (practiced {skill.practice_count}x)")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Learning Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
