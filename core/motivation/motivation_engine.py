#!/usr/bin/env python3
"""
BAEL - Motivation Engine
Motivational systems for agent drives and goal pursuit.

Features:
- Need modeling
- Drive systems
- Intrinsic motivation
- Goal prioritization
- Reward processing
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class NeedType(Enum):
    """Types of agent needs."""
    COMPETENCE = "competence"
    AUTONOMY = "autonomy"
    RELATEDNESS = "relatedness"
    KNOWLEDGE = "knowledge"
    ACHIEVEMENT = "achievement"
    SECURITY = "security"
    GROWTH = "growth"


class DriveType(Enum):
    """Types of drives."""
    EXPLORATION = "exploration"
    MASTERY = "mastery"
    SOCIAL = "social"
    CURIOSITY = "curiosity"
    SELF_IMPROVEMENT = "self_improvement"
    TASK_COMPLETION = "task_completion"


class MotivationLevel(Enum):
    """Motivation levels."""
    NONE = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    INTENSE = 4


class RewardType(Enum):
    """Types of rewards."""
    INTRINSIC = "intrinsic"
    EXTRINSIC = "extrinsic"
    SOCIAL = "social"
    ACHIEVEMENT = "achievement"


class GoalState(Enum):
    """Goal states."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MotivationState(Enum):
    """Motivation states."""
    IDLE = "idle"
    ENGAGED = "engaged"
    DRIVEN = "driven"
    EXHAUSTED = "exhausted"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Need:
    """An agent need."""
    need_id: str = ""
    need_type: NeedType = NeedType.COMPETENCE
    current_level: float = 0.5
    target_level: float = 1.0
    decay_rate: float = 0.01
    priority: float = 0.5
    last_satisfied: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.need_id:
            self.need_id = str(uuid.uuid4())[:8]


@dataclass
class Drive:
    """An agent drive."""
    drive_id: str = ""
    drive_type: DriveType = DriveType.EXPLORATION
    intensity: float = 0.5
    threshold: float = 0.3
    satiation_rate: float = 0.1
    deprivation_rate: float = 0.02
    active: bool = True
    last_activated: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.drive_id:
            self.drive_id = str(uuid.uuid4())[:8]


@dataclass
class Goal:
    """A motivational goal."""
    goal_id: str = ""
    name: str = ""
    description: str = ""
    priority: float = 0.5
    progress: float = 0.0
    state: GoalState = GoalState.ACTIVE
    related_needs: List[NeedType] = field(default_factory=list)
    related_drives: List[DriveType] = field(default_factory=list)
    expected_reward: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None

    def __post_init__(self):
        if not self.goal_id:
            self.goal_id = str(uuid.uuid4())[:8]


@dataclass
class Reward:
    """A reward signal."""
    reward_id: str = ""
    reward_type: RewardType = RewardType.INTRINSIC
    value: float = 0.0
    source: str = ""
    goal_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.reward_id:
            self.reward_id = str(uuid.uuid4())[:8]


@dataclass
class MotivationSnapshot:
    """Snapshot of motivation state."""
    snapshot_id: str = ""
    overall_motivation: float = 0.5
    dominant_drive: Optional[DriveType] = None
    unmet_needs: List[NeedType] = field(default_factory=list)
    active_goals: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = str(uuid.uuid4())[:8]


@dataclass
class MotivationConfig:
    """Motivation configuration."""
    base_decay: float = 0.01
    reward_sensitivity: float = 1.0
    goal_boost: float = 0.2
    fatigue_threshold: float = 0.8


# =============================================================================
# NEED MANAGER
# =============================================================================

class NeedManager:
    """Manage agent needs."""

    def __init__(self):
        self._needs: Dict[NeedType, Need] = {}

        self._initialize_needs()

    def _initialize_needs(self) -> None:
        """Initialize default needs."""
        for need_type in NeedType:
            self._needs[need_type] = Need(
                need_type=need_type,
                current_level=0.5,
                priority=0.5
            )

    def get_need(self, need_type: NeedType) -> Need:
        """Get a specific need."""
        return self._needs[need_type]

    def get_all_needs(self) -> Dict[NeedType, Need]:
        """Get all needs."""
        return self._needs.copy()

    def satisfy(
        self,
        need_type: NeedType,
        amount: float
    ) -> float:
        """Satisfy a need."""
        need = self._needs[need_type]

        old_level = need.current_level
        need.current_level = min(1.0, need.current_level + amount)
        need.last_satisfied = datetime.now()

        return need.current_level - old_level

    def deplete(
        self,
        need_type: NeedType,
        amount: float
    ) -> float:
        """Deplete a need."""
        need = self._needs[need_type]

        old_level = need.current_level
        need.current_level = max(0.0, need.current_level - amount)

        return old_level - need.current_level

    def decay_all(self) -> None:
        """Apply decay to all needs."""
        for need in self._needs.values():
            need.current_level = max(
                0.0,
                need.current_level - need.decay_rate
            )

    def get_deficit(self, need_type: NeedType) -> float:
        """Get need deficit."""
        need = self._needs[need_type]
        return max(0.0, need.target_level - need.current_level)

    def get_unmet_needs(self, threshold: float = 0.4) -> List[NeedType]:
        """Get needs below threshold."""
        return [
            need_type
            for need_type, need in self._needs.items()
            if need.current_level < threshold
        ]

    def get_priority_ordering(self) -> List[NeedType]:
        """Get needs ordered by priority and deficit."""
        return sorted(
            self._needs.keys(),
            key=lambda nt: (
                self._needs[nt].priority *
                self.get_deficit(nt)
            ),
            reverse=True
        )

    def set_priority(
        self,
        need_type: NeedType,
        priority: float
    ) -> None:
        """Set need priority."""
        self._needs[need_type].priority = max(0.0, min(1.0, priority))

    def get_overall_satisfaction(self) -> float:
        """Get overall need satisfaction."""
        if not self._needs:
            return 1.0

        return sum(n.current_level for n in self._needs.values()) / len(self._needs)


# =============================================================================
# DRIVE SYSTEM
# =============================================================================

class DriveSystem:
    """Manage agent drives."""

    def __init__(self):
        self._drives: Dict[DriveType, Drive] = {}

        self._initialize_drives()

    def _initialize_drives(self) -> None:
        """Initialize default drives."""
        for drive_type in DriveType:
            self._drives[drive_type] = Drive(
                drive_type=drive_type,
                intensity=0.5
            )

    def get_drive(self, drive_type: DriveType) -> Drive:
        """Get a specific drive."""
        return self._drives[drive_type]

    def get_all_drives(self) -> Dict[DriveType, Drive]:
        """Get all drives."""
        return self._drives.copy()

    def activate(self, drive_type: DriveType) -> None:
        """Activate a drive."""
        drive = self._drives[drive_type]
        drive.active = True
        drive.last_activated = datetime.now()

    def deactivate(self, drive_type: DriveType) -> None:
        """Deactivate a drive."""
        self._drives[drive_type].active = False

    def increase_intensity(
        self,
        drive_type: DriveType,
        amount: float
    ) -> float:
        """Increase drive intensity."""
        drive = self._drives[drive_type]

        old_intensity = drive.intensity
        drive.intensity = min(1.0, drive.intensity + amount)

        return drive.intensity - old_intensity

    def satiate(
        self,
        drive_type: DriveType,
        amount: Optional[float] = None
    ) -> float:
        """Satiate a drive."""
        drive = self._drives[drive_type]

        reduction = amount if amount else drive.satiation_rate

        old_intensity = drive.intensity
        drive.intensity = max(0.0, drive.intensity - reduction)

        return old_intensity - drive.intensity

    def deprive_all(self) -> None:
        """Apply deprivation to all drives."""
        for drive in self._drives.values():
            if drive.active:
                drive.intensity = min(
                    1.0,
                    drive.intensity + drive.deprivation_rate
                )

    def get_dominant_drive(self) -> Optional[DriveType]:
        """Get the most intense active drive."""
        active_drives = [
            (dt, d) for dt, d in self._drives.items()
            if d.active and d.intensity > d.threshold
        ]

        if not active_drives:
            return None

        return max(active_drives, key=lambda x: x[1].intensity)[0]

    def get_active_drives(self) -> List[DriveType]:
        """Get all active drives above threshold."""
        return [
            dt for dt, d in self._drives.items()
            if d.active and d.intensity > d.threshold
        ]

    def get_drive_strength(self, drive_type: DriveType) -> float:
        """Get drive strength."""
        drive = self._drives[drive_type]

        if not drive.active:
            return 0.0

        return drive.intensity


# =============================================================================
# GOAL MANAGER
# =============================================================================

class GoalManager:
    """Manage motivational goals."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}

    def create_goal(
        self,
        name: str,
        description: str = "",
        priority: float = 0.5,
        related_needs: Optional[List[NeedType]] = None,
        related_drives: Optional[List[DriveType]] = None,
        expected_reward: float = 0.5,
        deadline: Optional[datetime] = None
    ) -> Goal:
        """Create a new goal."""
        goal = Goal(
            name=name,
            description=description,
            priority=priority,
            related_needs=related_needs or [],
            related_drives=related_drives or [],
            expected_reward=expected_reward,
            deadline=deadline
        )

        self._goals[goal.goal_id] = goal

        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals."""
        return [
            g for g in self._goals.values()
            if g.state == GoalState.ACTIVE
        ]

    def update_progress(
        self,
        goal_id: str,
        progress: float
    ) -> Optional[Goal]:
        """Update goal progress."""
        goal = self._goals.get(goal_id)

        if not goal:
            return None

        goal.progress = max(0.0, min(1.0, progress))

        if goal.progress >= 1.0:
            goal.state = GoalState.COMPLETED

        return goal

    def increment_progress(
        self,
        goal_id: str,
        amount: float
    ) -> Optional[Goal]:
        """Increment goal progress."""
        goal = self._goals.get(goal_id)

        if not goal:
            return None

        return self.update_progress(goal_id, goal.progress + amount)

    def suspend_goal(self, goal_id: str) -> bool:
        """Suspend a goal."""
        goal = self._goals.get(goal_id)

        if goal and goal.state == GoalState.ACTIVE:
            goal.state = GoalState.SUSPENDED
            return True

        return False

    def resume_goal(self, goal_id: str) -> bool:
        """Resume a suspended goal."""
        goal = self._goals.get(goal_id)

        if goal and goal.state == GoalState.SUSPENDED:
            goal.state = GoalState.ACTIVE
            return True

        return False

    def abandon_goal(self, goal_id: str) -> bool:
        """Abandon a goal."""
        goal = self._goals.get(goal_id)

        if goal and goal.state in [GoalState.ACTIVE, GoalState.SUSPENDED]:
            goal.state = GoalState.ABANDONED
            return True

        return False

    def get_prioritized_goals(self) -> List[Goal]:
        """Get goals ordered by priority."""
        active = self.get_active_goals()

        return sorted(
            active,
            key=lambda g: g.priority * (1 + g.expected_reward),
            reverse=True
        )

    def get_goals_by_need(self, need_type: NeedType) -> List[Goal]:
        """Get goals related to a need."""
        return [
            g for g in self.get_active_goals()
            if need_type in g.related_needs
        ]

    def get_goals_by_drive(self, drive_type: DriveType) -> List[Goal]:
        """Get goals related to a drive."""
        return [
            g for g in self.get_active_goals()
            if drive_type in g.related_drives
        ]

    def get_overdue_goals(self) -> List[Goal]:
        """Get overdue goals."""
        now = datetime.now()

        return [
            g for g in self.get_active_goals()
            if g.deadline and g.deadline < now
        ]


# =============================================================================
# REWARD PROCESSOR
# =============================================================================

class RewardProcessor:
    """Process reward signals."""

    def __init__(self, sensitivity: float = 1.0):
        self._sensitivity = sensitivity

        self._rewards: List[Reward] = []
        self._total_reward: float = 0.0
        self._reward_by_type: Dict[RewardType, float] = defaultdict(float)

    def process_reward(
        self,
        value: float,
        reward_type: RewardType = RewardType.INTRINSIC,
        source: str = "",
        goal_id: Optional[str] = None
    ) -> Reward:
        """Process a reward signal."""
        adjusted_value = value * self._sensitivity

        reward = Reward(
            reward_type=reward_type,
            value=adjusted_value,
            source=source,
            goal_id=goal_id
        )

        self._rewards.append(reward)
        self._total_reward += adjusted_value
        self._reward_by_type[reward_type] += adjusted_value

        return reward

    def get_recent_rewards(
        self,
        limit: int = 20
    ) -> List[Reward]:
        """Get recent rewards."""
        return self._rewards[-limit:]

    def get_total_reward(self) -> float:
        """Get total accumulated reward."""
        return self._total_reward

    def get_reward_by_type(
        self,
        reward_type: RewardType
    ) -> float:
        """Get total reward by type."""
        return self._reward_by_type[reward_type]

    def get_average_reward(
        self,
        window: int = 10
    ) -> float:
        """Get average recent reward."""
        recent = self._rewards[-window:] if self._rewards else []

        if not recent:
            return 0.0

        return sum(r.value for r in recent) / len(recent)

    def get_reward_for_goal(self, goal_id: str) -> float:
        """Get total reward for a goal."""
        return sum(
            r.value for r in self._rewards
            if r.goal_id == goal_id
        )

    def set_sensitivity(self, sensitivity: float) -> None:
        """Set reward sensitivity."""
        self._sensitivity = max(0.1, min(2.0, sensitivity))

    def decay_rewards(self, factor: float = 0.99) -> None:
        """Apply decay to total reward."""
        self._total_reward *= factor

        for rt in self._reward_by_type:
            self._reward_by_type[rt] *= factor


# =============================================================================
# INTRINSIC MOTIVATION
# =============================================================================

class IntrinsicMotivation:
    """Compute intrinsic motivation signals."""

    def __init__(self):
        self._novelty_memory: Set[str] = set()
        self._competence_history: List[float] = []

    def compute_novelty_bonus(
        self,
        state_hash: str,
        base_value: float = 0.1
    ) -> float:
        """Compute novelty-based intrinsic motivation."""
        if state_hash not in self._novelty_memory:
            self._novelty_memory.add(state_hash)
            return base_value

        return 0.0

    def compute_competence_progress(
        self,
        performance: float
    ) -> float:
        """Compute competence progress motivation."""
        self._competence_history.append(performance)

        if len(self._competence_history) < 2:
            return 0.0

        recent = self._competence_history[-10:]

        if len(recent) < 2:
            return 0.0

        improvement = recent[-1] - sum(recent[:-1]) / len(recent[:-1])

        return max(0.0, improvement)

    def compute_curiosity_reward(
        self,
        prediction_error: float,
        max_reward: float = 0.5
    ) -> float:
        """Compute curiosity-based reward from prediction error."""
        return min(max_reward, abs(prediction_error) * max_reward)

    def compute_mastery_reward(
        self,
        task_difficulty: float,
        success: bool
    ) -> float:
        """Compute mastery reward based on difficulty."""
        if success:
            return task_difficulty * 0.3

        return 0.0

    def reset_novelty(self) -> None:
        """Reset novelty memory."""
        self._novelty_memory.clear()

    def get_exploration_drive(
        self,
        visited_states: int,
        total_states: int
    ) -> float:
        """Compute exploration drive."""
        if total_states == 0:
            return 1.0

        coverage = visited_states / total_states

        return 1.0 - coverage


# =============================================================================
# MOTIVATION ENGINE
# =============================================================================

class MotivationEngine:
    """
    Motivation Engine for BAEL.

    Motivational systems for agent drives and goal pursuit.
    """

    def __init__(self, config: Optional[MotivationConfig] = None):
        self._config = config or MotivationConfig()

        self._need_manager = NeedManager()
        self._drive_system = DriveSystem()
        self._goal_manager = GoalManager()
        self._reward_processor = RewardProcessor(
            sensitivity=self._config.reward_sensitivity
        )
        self._intrinsic = IntrinsicMotivation()

        self._state = MotivationState.IDLE
        self._overall_motivation: float = 0.5

        self._snapshots: List[MotivationSnapshot] = []

    # ----- Need Operations -----

    def get_need(self, need_type: NeedType) -> Need:
        """Get a specific need."""
        return self._need_manager.get_need(need_type)

    def satisfy_need(
        self,
        need_type: NeedType,
        amount: float
    ) -> float:
        """Satisfy a need."""
        satisfied = self._need_manager.satisfy(need_type, amount)

        self._update_motivation()

        return satisfied

    def get_unmet_needs(self) -> List[NeedType]:
        """Get unmet needs."""
        return self._need_manager.get_unmet_needs()

    def get_priority_needs(self) -> List[NeedType]:
        """Get needs by priority."""
        return self._need_manager.get_priority_ordering()

    # ----- Drive Operations -----

    def get_drive(self, drive_type: DriveType) -> Drive:
        """Get a specific drive."""
        return self._drive_system.get_drive(drive_type)

    def get_dominant_drive(self) -> Optional[DriveType]:
        """Get dominant drive."""
        return self._drive_system.get_dominant_drive()

    def satiate_drive(
        self,
        drive_type: DriveType,
        amount: Optional[float] = None
    ) -> float:
        """Satiate a drive."""
        satiated = self._drive_system.satiate(drive_type, amount)

        self._update_motivation()

        return satiated

    def increase_drive(
        self,
        drive_type: DriveType,
        amount: float
    ) -> float:
        """Increase drive intensity."""
        return self._drive_system.increase_intensity(drive_type, amount)

    def get_active_drives(self) -> List[DriveType]:
        """Get active drives."""
        return self._drive_system.get_active_drives()

    # ----- Goal Operations -----

    def create_goal(
        self,
        name: str,
        description: str = "",
        priority: float = 0.5,
        related_needs: Optional[List[NeedType]] = None,
        related_drives: Optional[List[DriveType]] = None,
        expected_reward: float = 0.5,
        deadline: Optional[datetime] = None
    ) -> Goal:
        """Create a goal."""
        goal = self._goal_manager.create_goal(
            name=name,
            description=description,
            priority=priority,
            related_needs=related_needs,
            related_drives=related_drives,
            expected_reward=expected_reward,
            deadline=deadline
        )

        self._update_motivation()

        return goal

    def update_goal_progress(
        self,
        goal_id: str,
        progress: float
    ) -> Optional[Goal]:
        """Update goal progress."""
        goal = self._goal_manager.update_progress(goal_id, progress)

        if goal and goal.state == GoalState.COMPLETED:
            self._process_goal_completion(goal)

        return goal

    def increment_goal(
        self,
        goal_id: str,
        amount: float
    ) -> Optional[Goal]:
        """Increment goal progress."""
        goal = self._goal_manager.increment_progress(goal_id, amount)

        if goal and goal.state == GoalState.COMPLETED:
            self._process_goal_completion(goal)

        return goal

    def get_active_goals(self) -> List[Goal]:
        """Get active goals."""
        return self._goal_manager.get_active_goals()

    def get_prioritized_goals(self) -> List[Goal]:
        """Get prioritized goals."""
        return self._goal_manager.get_prioritized_goals()

    def abandon_goal(self, goal_id: str) -> bool:
        """Abandon a goal."""
        return self._goal_manager.abandon_goal(goal_id)

    def _process_goal_completion(self, goal: Goal) -> None:
        """Process goal completion."""
        self._reward_processor.process_reward(
            value=goal.expected_reward,
            reward_type=RewardType.ACHIEVEMENT,
            source="goal_completion",
            goal_id=goal.goal_id
        )

        for need_type in goal.related_needs:
            self._need_manager.satisfy(need_type, 0.2)

        for drive_type in goal.related_drives:
            self._drive_system.satiate(drive_type, 0.3)

    # ----- Reward Operations -----

    def process_reward(
        self,
        value: float,
        reward_type: RewardType = RewardType.EXTRINSIC,
        source: str = "",
        goal_id: Optional[str] = None
    ) -> Reward:
        """Process a reward."""
        reward = self._reward_processor.process_reward(
            value=value,
            reward_type=reward_type,
            source=source,
            goal_id=goal_id
        )

        self._update_motivation()

        return reward

    def get_total_reward(self) -> float:
        """Get total reward."""
        return self._reward_processor.get_total_reward()

    def get_average_reward(self) -> float:
        """Get average recent reward."""
        return self._reward_processor.get_average_reward()

    # ----- Intrinsic Motivation -----

    def compute_novelty_bonus(
        self,
        state_hash: str
    ) -> float:
        """Compute novelty bonus."""
        bonus = self._intrinsic.compute_novelty_bonus(state_hash)

        if bonus > 0:
            self._reward_processor.process_reward(
                value=bonus,
                reward_type=RewardType.INTRINSIC,
                source="novelty"
            )

        return bonus

    def compute_curiosity_reward(
        self,
        prediction_error: float
    ) -> float:
        """Compute curiosity reward."""
        reward = self._intrinsic.compute_curiosity_reward(prediction_error)

        if reward > 0:
            self._reward_processor.process_reward(
                value=reward,
                reward_type=RewardType.INTRINSIC,
                source="curiosity"
            )

        return reward

    def compute_mastery_reward(
        self,
        task_difficulty: float,
        success: bool
    ) -> float:
        """Compute mastery reward."""
        reward = self._intrinsic.compute_mastery_reward(task_difficulty, success)

        if reward > 0:
            self._reward_processor.process_reward(
                value=reward,
                reward_type=RewardType.INTRINSIC,
                source="mastery"
            )

        return reward

    # ----- Cycle Operations -----

    def step(self) -> None:
        """Run a motivation cycle step."""
        self._need_manager.decay_all()
        self._drive_system.deprive_all()
        self._reward_processor.decay_rewards()

        self._update_motivation()

    def _update_motivation(self) -> None:
        """Update overall motivation."""
        need_component = 1.0 - self._need_manager.get_overall_satisfaction()

        active_drives = self._drive_system.get_active_drives()
        drive_component = len(active_drives) / len(DriveType) if active_drives else 0.0

        active_goals = len(self._goal_manager.get_active_goals())
        goal_component = min(1.0, active_goals * self._config.goal_boost)

        avg_reward = self._reward_processor.get_average_reward()
        reward_component = min(1.0, max(0.0, avg_reward))

        self._overall_motivation = (
            need_component * 0.3 +
            drive_component * 0.3 +
            goal_component * 0.2 +
            reward_component * 0.2
        )

        if self._overall_motivation > self._config.fatigue_threshold:
            self._state = MotivationState.DRIVEN
        elif self._overall_motivation > 0.3:
            self._state = MotivationState.ENGAGED
        elif self._overall_motivation < 0.1:
            self._state = MotivationState.EXHAUSTED
        else:
            self._state = MotivationState.IDLE

    # ----- State and Snapshots -----

    def get_motivation_level(self) -> MotivationLevel:
        """Get current motivation level."""
        if self._overall_motivation >= 0.8:
            return MotivationLevel.INTENSE
        elif self._overall_motivation >= 0.6:
            return MotivationLevel.HIGH
        elif self._overall_motivation >= 0.4:
            return MotivationLevel.MODERATE
        elif self._overall_motivation >= 0.2:
            return MotivationLevel.LOW
        else:
            return MotivationLevel.NONE

    def get_state(self) -> MotivationState:
        """Get current motivation state."""
        return self._state

    def get_overall_motivation(self) -> float:
        """Get overall motivation value."""
        return self._overall_motivation

    def snapshot(self) -> MotivationSnapshot:
        """Take a motivation snapshot."""
        snapshot = MotivationSnapshot(
            overall_motivation=self._overall_motivation,
            dominant_drive=self._drive_system.get_dominant_drive(),
            unmet_needs=self._need_manager.get_unmet_needs(),
            active_goals=len(self._goal_manager.get_active_goals())
        )

        self._snapshots.append(snapshot)

        return snapshot

    def get_snapshots(
        self,
        limit: int = 20
    ) -> List[MotivationSnapshot]:
        """Get motivation snapshots."""
        return self._snapshots[-limit:]

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "state": self._state.value,
            "level": self.get_motivation_level().name,
            "overall": f"{self._overall_motivation:.2f}",
            "dominant_drive": (
                self.get_dominant_drive().value
                if self.get_dominant_drive() else "none"
            ),
            "active_goals": len(self.get_active_goals()),
            "unmet_needs": len(self.get_unmet_needs()),
            "total_reward": f"{self.get_total_reward():.2f}",
            "snapshots": len(self._snapshots)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Motivation Engine."""
    print("=" * 70)
    print("BAEL - MOTIVATION ENGINE DEMO")
    print("Motivational Systems for Agent Drives and Goal Pursuit")
    print("=" * 70)
    print()

    engine = MotivationEngine()

    # 1. Check Initial Needs
    print("1. INITIAL NEEDS:")
    print("-" * 40)

    for need_type in NeedType:
        need = engine.get_need(need_type)
        print(f"   {need_type.value}: {need.current_level:.2f}")
    print()

    # 2. Check Initial Drives
    print("2. INITIAL DRIVES:")
    print("-" * 40)

    for drive_type in DriveType:
        drive = engine.get_drive(drive_type)
        print(f"   {drive_type.value}: intensity={drive.intensity:.2f}")
    print()

    # 3. Create Goals
    print("3. CREATE GOALS:")
    print("-" * 40)

    goal1 = engine.create_goal(
        name="Learn New Framework",
        priority=0.8,
        related_needs=[NeedType.KNOWLEDGE, NeedType.COMPETENCE],
        related_drives=[DriveType.MASTERY, DriveType.CURIOSITY],
        expected_reward=0.7
    )
    print(f"   Created: {goal1.name} (priority={goal1.priority})")

    goal2 = engine.create_goal(
        name="Complete Project",
        priority=0.9,
        related_needs=[NeedType.ACHIEVEMENT],
        related_drives=[DriveType.TASK_COMPLETION],
        expected_reward=0.8,
        deadline=datetime.now() + timedelta(days=7)
    )
    print(f"   Created: {goal2.name} (priority={goal2.priority})")

    goal3 = engine.create_goal(
        name="Collaborate with Team",
        priority=0.6,
        related_needs=[NeedType.RELATEDNESS],
        related_drives=[DriveType.SOCIAL],
        expected_reward=0.5
    )
    print(f"   Created: {goal3.name} (priority={goal3.priority})")
    print()

    # 4. Check Motivation State
    print("4. MOTIVATION STATE:")
    print("-" * 40)

    print(f"   Overall: {engine.get_overall_motivation():.2f}")
    print(f"   Level: {engine.get_motivation_level().name}")
    print(f"   State: {engine.get_state().value}")
    print(f"   Dominant Drive: {engine.get_dominant_drive()}")
    print()

    # 5. Process Rewards
    print("5. PROCESS REWARDS:")
    print("-" * 40)

    r1 = engine.process_reward(0.3, RewardType.EXTRINSIC, "task_progress")
    print(f"   Processed: {r1.value:.2f} ({r1.reward_type.value})")

    r2 = engine.process_reward(0.5, RewardType.SOCIAL, "team_feedback")
    print(f"   Processed: {r2.value:.2f} ({r2.reward_type.value})")

    print(f"   Total Reward: {engine.get_total_reward():.2f}")
    print()

    # 6. Intrinsic Motivation
    print("6. INTRINSIC MOTIVATION:")
    print("-" * 40)

    novelty = engine.compute_novelty_bonus("new_state_abc")
    print(f"   Novelty bonus: {novelty:.2f}")

    novelty2 = engine.compute_novelty_bonus("new_state_abc")
    print(f"   Same state again: {novelty2:.2f}")

    curiosity = engine.compute_curiosity_reward(0.6)
    print(f"   Curiosity reward (error=0.6): {curiosity:.2f}")

    mastery = engine.compute_mastery_reward(0.8, True)
    print(f"   Mastery reward (diff=0.8, success): {mastery:.2f}")
    print()

    # 7. Goal Progress
    print("7. GOAL PROGRESS:")
    print("-" * 40)

    engine.increment_goal(goal1.goal_id, 0.3)
    print(f"   {goal1.name}: {engine._goal_manager.get_goal(goal1.goal_id).progress:.0%}")

    engine.increment_goal(goal2.goal_id, 0.5)
    print(f"   {goal2.name}: {engine._goal_manager.get_goal(goal2.goal_id).progress:.0%}")
    print()

    # 8. Complete Goal
    print("8. COMPLETE GOAL:")
    print("-" * 40)

    engine.update_goal_progress(goal1.goal_id, 1.0)

    completed = engine._goal_manager.get_goal(goal1.goal_id)
    print(f"   {completed.name}: {completed.state.value}")
    print(f"   Total Reward Now: {engine.get_total_reward():.2f}")
    print()

    # 9. Need Satisfaction
    print("9. NEED SATISFACTION:")
    print("-" * 40)

    print(f"   Before - Knowledge: {engine.get_need(NeedType.KNOWLEDGE).current_level:.2f}")

    engine.satisfy_need(NeedType.KNOWLEDGE, 0.3)

    print(f"   After - Knowledge: {engine.get_need(NeedType.KNOWLEDGE).current_level:.2f}")
    print()

    # 10. Drive Intensity
    print("10. DRIVE INTENSITY:")
    print("-" * 40)

    engine.increase_drive(DriveType.EXPLORATION, 0.3)
    print(f"   Exploration: {engine.get_drive(DriveType.EXPLORATION).intensity:.2f}")

    engine.satiate_drive(DriveType.TASK_COMPLETION, 0.2)
    print(f"   Task Completion: {engine.get_drive(DriveType.TASK_COMPLETION).intensity:.2f}")
    print()

    # 11. Motivation Cycle
    print("11. MOTIVATION CYCLE:")
    print("-" * 40)

    print(f"   Before step: {engine.get_overall_motivation():.2f}")

    for i in range(3):
        engine.step()

    print(f"   After 3 steps: {engine.get_overall_motivation():.2f}")
    print()

    # 12. Priority Ordering
    print("12. PRIORITY ORDERING:")
    print("-" * 40)

    print("   Goals:")
    for goal in engine.get_prioritized_goals():
        print(f"     - {goal.name} (priority={goal.priority})")

    print("\n   Needs:")
    for need_type in engine.get_priority_needs()[:3]:
        print(f"     - {need_type.value}")
    print()

    # 13. Snapshot
    print("13. TAKE SNAPSHOT:")
    print("-" * 40)

    snapshot = engine.snapshot()

    print(f"   Overall: {snapshot.overall_motivation:.2f}")
    print(f"   Dominant Drive: {snapshot.dominant_drive}")
    print(f"   Active Goals: {snapshot.active_goals}")
    print(f"   Unmet Needs: {len(snapshot.unmet_needs)}")
    print()

    # 14. Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Motivation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
