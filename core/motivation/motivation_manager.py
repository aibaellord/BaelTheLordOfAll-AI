#!/usr/bin/env python3
"""
BAEL - Motivation Manager
Advanced motivation and goal-driven behavior system.

Features:
- Intrinsic motivation modeling
- Extrinsic reward management
- Goal hierarchy management
- Drive system modeling
- Need satisfaction tracking
- Incentive computation
- Motivation dynamics
- Self-determination support
"""

import asyncio
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MotivationType(Enum):
    """Types of motivation."""
    INTRINSIC = "intrinsic"
    EXTRINSIC = "extrinsic"
    AUTONOMOUS = "autonomous"
    CONTROLLED = "controlled"


class DriveType(Enum):
    """Basic drive types."""
    CURIOSITY = "curiosity"
    COMPETENCE = "competence"
    AUTONOMY = "autonomy"
    RELATEDNESS = "relatedness"
    ACHIEVEMENT = "achievement"
    POWER = "power"
    AFFILIATION = "affiliation"


class NeedType(Enum):
    """Psychological needs."""
    COMPETENCE = "competence"
    AUTONOMY = "autonomy"
    RELATEDNESS = "relatedness"
    SECURITY = "security"
    NOVELTY = "novelty"
    MEANING = "meaning"


class GoalStatus(Enum):
    """Goal status."""
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class GoalPriority(Enum):
    """Goal priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class IncentiveType(Enum):
    """Incentive types."""
    REWARD = "reward"
    PUNISHMENT_AVOIDANCE = "punishment_avoidance"
    SOCIAL_APPROVAL = "social_approval"
    ACHIEVEMENT = "achievement"
    GROWTH = "growth"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Drive:
    """Motivational drive."""
    drive_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    drive_type: DriveType = DriveType.CURIOSITY
    intensity: float = 0.5  # 0-1
    baseline: float = 0.5
    decay_rate: float = 0.01
    satisfaction: float = 0.0
    last_satisfied: datetime = field(default_factory=datetime.now)


@dataclass
class Need:
    """Psychological need."""
    need_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    need_type: NeedType = NeedType.COMPETENCE
    satisfaction_level: float = 0.5  # 0-1
    importance: float = 0.5
    threshold: float = 0.3  # Below this triggers motivation
    history: List[float] = field(default_factory=list)


@dataclass
class Goal:
    """Motivational goal."""
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.ACTIVE
    parent_goal: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)
    progress: float = 0.0  # 0-1
    deadline: Optional[datetime] = None
    associated_drives: List[DriveType] = field(default_factory=list)
    associated_needs: List[NeedType] = field(default_factory=list)
    reward_value: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Incentive:
    """Motivational incentive."""
    incentive_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    incentive_type: IncentiveType = IncentiveType.REWARD
    value: float = 0.0
    source: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    expiry: Optional[datetime] = None
    claimed: bool = False


@dataclass
class MotivationState:
    """Current motivation state."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    overall_motivation: float = 0.5
    dominant_drive: Optional[DriveType] = None
    active_goals: List[str] = field(default_factory=list)
    unsatisfied_needs: List[NeedType] = field(default_factory=list)
    pending_incentives: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MotivationEvent:
    """Motivation-related event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    impact: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# DRIVE SYSTEM
# =============================================================================

class DriveSystem:
    """Manage motivational drives."""

    def __init__(self):
        self._drives: Dict[DriveType, Drive] = {}
        self._initialize_drives()

    def _initialize_drives(self) -> None:
        """Initialize default drives."""
        for drive_type in DriveType:
            self._drives[drive_type] = Drive(
                drive_type=drive_type,
                intensity=0.5,
                baseline=0.5
            )

    def get_drive(self, drive_type: DriveType) -> Drive:
        """Get drive by type."""
        return self._drives.get(drive_type, Drive(drive_type=drive_type))

    def set_drive_intensity(
        self,
        drive_type: DriveType,
        intensity: float
    ) -> None:
        """Set drive intensity."""
        drive = self._drives.get(drive_type)
        if drive:
            drive.intensity = max(0.0, min(1.0, intensity))

    def increase_drive(
        self,
        drive_type: DriveType,
        amount: float
    ) -> float:
        """Increase drive intensity."""
        drive = self._drives.get(drive_type)
        if drive:
            drive.intensity = min(1.0, drive.intensity + amount)
            return drive.intensity
        return 0.0

    def satisfy_drive(
        self,
        drive_type: DriveType,
        satisfaction: float
    ) -> float:
        """Satisfy a drive (reduces intensity)."""
        drive = self._drives.get(drive_type)
        if drive:
            drive.satisfaction += satisfaction
            drive.intensity = max(0.0, drive.intensity - satisfaction)
            drive.last_satisfied = datetime.now()
            return drive.intensity
        return 0.0

    def update_drives(self, delta_time: float = 1.0) -> None:
        """Update drives (homeostatic return to baseline)."""
        for drive in self._drives.values():
            # Drives naturally return toward baseline
            diff = drive.baseline - drive.intensity
            drive.intensity += diff * drive.decay_rate * delta_time

            # Drives also increase when not satisfied
            time_since = (datetime.now() - drive.last_satisfied).total_seconds()
            if time_since > 60:  # After 1 minute
                drive.intensity = min(1.0, drive.intensity + 0.01 * delta_time)

    def get_dominant_drive(self) -> Optional[DriveType]:
        """Get the dominant drive."""
        if not self._drives:
            return None

        dominant = max(
            self._drives.items(),
            key=lambda x: x[1].intensity
        )

        return dominant[0]

    def get_all_drives(self) -> Dict[DriveType, float]:
        """Get all drive intensities."""
        return {
            drive_type: drive.intensity
            for drive_type, drive in self._drives.items()
        }


# =============================================================================
# NEED SATISFACTION SYSTEM
# =============================================================================

class NeedSatisfactionSystem:
    """Track and manage psychological needs."""

    def __init__(self):
        self._needs: Dict[NeedType, Need] = {}
        self._initialize_needs()

    def _initialize_needs(self) -> None:
        """Initialize default needs."""
        defaults = {
            NeedType.COMPETENCE: 0.6,
            NeedType.AUTONOMY: 0.5,
            NeedType.RELATEDNESS: 0.5,
            NeedType.SECURITY: 0.7,
            NeedType.NOVELTY: 0.4,
            NeedType.MEANING: 0.5,
        }

        for need_type, importance in defaults.items():
            self._needs[need_type] = Need(
                need_type=need_type,
                satisfaction_level=0.5,
                importance=importance
            )

    def get_need(self, need_type: NeedType) -> Need:
        """Get need by type."""
        return self._needs.get(need_type, Need(need_type=need_type))

    def satisfy_need(
        self,
        need_type: NeedType,
        amount: float
    ) -> float:
        """Satisfy a need."""
        need = self._needs.get(need_type)
        if need:
            need.satisfaction_level = min(1.0, need.satisfaction_level + amount)
            need.history.append(need.satisfaction_level)
            return need.satisfaction_level
        return 0.0

    def deplete_need(
        self,
        need_type: NeedType,
        amount: float
    ) -> float:
        """Deplete a need."""
        need = self._needs.get(need_type)
        if need:
            need.satisfaction_level = max(0.0, need.satisfaction_level - amount)
            need.history.append(need.satisfaction_level)
            return need.satisfaction_level
        return 0.0

    def get_unsatisfied_needs(self) -> List[NeedType]:
        """Get list of unsatisfied needs (below threshold)."""
        unsatisfied = []

        for need_type, need in self._needs.items():
            if need.satisfaction_level < need.threshold:
                unsatisfied.append(need_type)

        # Sort by importance and satisfaction (most urgent first)
        unsatisfied.sort(
            key=lambda n: (
                self._needs[n].importance *
                (1 - self._needs[n].satisfaction_level)
            ),
            reverse=True
        )

        return unsatisfied

    def get_need_satisfaction_summary(self) -> Dict[str, float]:
        """Get summary of all need satisfaction levels."""
        return {
            need_type.value: need.satisfaction_level
            for need_type, need in self._needs.items()
        }

    def compute_wellbeing(self) -> float:
        """Compute overall wellbeing from need satisfaction."""
        if not self._needs:
            return 0.5

        weighted_sum = sum(
            need.satisfaction_level * need.importance
            for need in self._needs.values()
        )

        total_weight = sum(
            need.importance
            for need in self._needs.values()
        )

        return weighted_sum / total_weight if total_weight > 0 else 0.5


# =============================================================================
# GOAL HIERARCHY
# =============================================================================

class GoalHierarchy:
    """Manage hierarchical goal structure."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._root_goals: Set[str] = set()

    def add_goal(
        self,
        name: str,
        description: str = "",
        priority: GoalPriority = GoalPriority.MEDIUM,
        parent_goal: Optional[str] = None,
        deadline: Optional[datetime] = None,
        associated_drives: Optional[List[DriveType]] = None,
        associated_needs: Optional[List[NeedType]] = None,
        reward_value: float = 1.0
    ) -> Goal:
        """Add a goal."""
        goal = Goal(
            name=name,
            description=description,
            priority=priority,
            parent_goal=parent_goal,
            deadline=deadline,
            associated_drives=associated_drives or [],
            associated_needs=associated_needs or [],
            reward_value=reward_value
        )

        self._goals[goal.goal_id] = goal

        if parent_goal:
            parent = self._goals.get(parent_goal)
            if parent:
                parent.sub_goals.append(goal.goal_id)
        else:
            self._root_goals.add(goal.goal_id)

        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get goal by ID."""
        return self._goals.get(goal_id)

    def update_progress(
        self,
        goal_id: str,
        progress: float
    ) -> bool:
        """Update goal progress."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.progress = max(0.0, min(1.0, progress))

            # Check if completed
            if goal.progress >= 1.0:
                goal.status = GoalStatus.ACHIEVED

            return True
        return False

    def set_status(
        self,
        goal_id: str,
        status: GoalStatus
    ) -> bool:
        """Set goal status."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.status = status
            return True
        return False

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals."""
        return [
            goal for goal in self._goals.values()
            if goal.status == GoalStatus.ACTIVE
        ]

    def get_goals_by_priority(
        self,
        priority: GoalPriority
    ) -> List[Goal]:
        """Get goals by priority."""
        return [
            goal for goal in self._goals.values()
            if goal.priority == priority and goal.status == GoalStatus.ACTIVE
        ]

    def get_sub_goals(self, goal_id: str) -> List[Goal]:
        """Get sub-goals of a goal."""
        goal = self._goals.get(goal_id)
        if not goal:
            return []

        return [
            self._goals[sub_id]
            for sub_id in goal.sub_goals
            if sub_id in self._goals
        ]

    def compute_goal_value(self, goal_id: str) -> float:
        """Compute motivational value of achieving a goal."""
        goal = self._goals.get(goal_id)
        if not goal:
            return 0.0

        # Base reward value
        value = goal.reward_value

        # Priority multiplier
        priority_mult = {
            GoalPriority.CRITICAL: 2.0,
            GoalPriority.HIGH: 1.5,
            GoalPriority.MEDIUM: 1.0,
            GoalPriority.LOW: 0.7,
            GoalPriority.OPTIONAL: 0.5,
        }
        value *= priority_mult.get(goal.priority, 1.0)

        # Deadline urgency
        if goal.deadline:
            time_left = (goal.deadline - datetime.now()).total_seconds()
            if time_left < 0:
                value *= 0.5  # Overdue
            elif time_left < 3600:  # Less than 1 hour
                value *= 1.5

        return value

    def get_root_goals(self) -> List[Goal]:
        """Get root (top-level) goals."""
        return [
            self._goals[goal_id]
            for goal_id in self._root_goals
            if goal_id in self._goals
        ]


# =============================================================================
# INCENTIVE SYSTEM
# =============================================================================

class IncentiveSystem:
    """Manage incentives and rewards."""

    def __init__(self):
        self._incentives: Dict[str, Incentive] = {}
        self._claimed_history: List[Tuple[str, datetime, float]] = []

    def create_incentive(
        self,
        incentive_type: IncentiveType,
        value: float,
        source: str,
        conditions: Optional[Dict[str, Any]] = None,
        expiry: Optional[datetime] = None
    ) -> Incentive:
        """Create an incentive."""
        incentive = Incentive(
            incentive_type=incentive_type,
            value=value,
            source=source,
            conditions=conditions or {},
            expiry=expiry
        )

        self._incentives[incentive.incentive_id] = incentive
        return incentive

    def get_incentive(self, incentive_id: str) -> Optional[Incentive]:
        """Get incentive by ID."""
        return self._incentives.get(incentive_id)

    def claim_incentive(self, incentive_id: str) -> float:
        """Claim an incentive."""
        incentive = self._incentives.get(incentive_id)
        if not incentive or incentive.claimed:
            return 0.0

        # Check expiry
        if incentive.expiry and datetime.now() > incentive.expiry:
            return 0.0

        incentive.claimed = True
        self._claimed_history.append(
            (incentive_id, datetime.now(), incentive.value)
        )

        return incentive.value

    def get_pending_incentives(self) -> List[Incentive]:
        """Get pending (unclaimed) incentives."""
        now = datetime.now()
        return [
            inc for inc in self._incentives.values()
            if not inc.claimed and (inc.expiry is None or inc.expiry > now)
        ]

    def compute_total_pending_value(self) -> float:
        """Compute total value of pending incentives."""
        return sum(
            inc.value
            for inc in self.get_pending_incentives()
        )

    def get_claim_history(
        self,
        since: Optional[datetime] = None
    ) -> List[Tuple[str, datetime, float]]:
        """Get incentive claim history."""
        if since:
            return [
                (id, time, value)
                for id, time, value in self._claimed_history
                if time >= since
            ]
        return list(self._claimed_history)


# =============================================================================
# MOTIVATION DYNAMICS
# =============================================================================

class MotivationDynamics:
    """Model motivation dynamics over time."""

    def __init__(self):
        self._history: deque = deque(maxlen=1000)
        self._events: List[MotivationEvent] = []

    def record_state(self, state: MotivationState) -> None:
        """Record motivation state."""
        self._history.append(state)

    def record_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        impact: float
    ) -> MotivationEvent:
        """Record motivation event."""
        event = MotivationEvent(
            event_type=event_type,
            details=details,
            impact=impact
        )

        self._events.append(event)
        return event

    def compute_momentum(self) -> float:
        """Compute motivation momentum (trend)."""
        if len(self._history) < 2:
            return 0.0

        recent = list(self._history)[-10:]

        if len(recent) < 2:
            return 0.0

        first_half = sum(s.overall_motivation for s in recent[:len(recent)//2])
        second_half = sum(s.overall_motivation for s in recent[len(recent)//2:])

        first_avg = first_half / (len(recent)//2)
        second_avg = second_half / (len(recent) - len(recent)//2)

        return second_avg - first_avg

    def compute_volatility(self) -> float:
        """Compute motivation volatility."""
        if len(self._history) < 2:
            return 0.0

        recent = [s.overall_motivation for s in list(self._history)[-20:]]

        if len(recent) < 2:
            return 0.0

        mean = sum(recent) / len(recent)
        variance = sum((v - mean) ** 2 for v in recent) / len(recent)

        return math.sqrt(variance)

    def predict_motivation(self, steps_ahead: int = 1) -> float:
        """Predict future motivation level."""
        if not self._history:
            return 0.5

        current = list(self._history)[-1].overall_motivation
        momentum = self.compute_momentum()

        predicted = current + momentum * steps_ahead
        return max(0.0, min(1.0, predicted))

    def get_recent_events(
        self,
        count: int = 10
    ) -> List[MotivationEvent]:
        """Get recent motivation events."""
        return self._events[-count:]


# =============================================================================
# MOTIVATION MANAGER
# =============================================================================

class MotivationManager:
    """
    Motivation Manager for BAEL.

    Advanced motivation and goal-driven behavior system.
    """

    def __init__(self):
        self._drive_system = DriveSystem()
        self._need_system = NeedSatisfactionSystem()
        self._goal_hierarchy = GoalHierarchy()
        self._incentive_system = IncentiveSystem()
        self._dynamics = MotivationDynamics()

        self._current_state: Optional[MotivationState] = None

    # -------------------------------------------------------------------------
    # DRIVE MANAGEMENT
    # -------------------------------------------------------------------------

    def get_drive(self, drive_type: DriveType) -> Drive:
        """Get drive by type."""
        return self._drive_system.get_drive(drive_type)

    def set_drive_intensity(
        self,
        drive_type: DriveType,
        intensity: float
    ) -> None:
        """Set drive intensity."""
        self._drive_system.set_drive_intensity(drive_type, intensity)

    def increase_drive(
        self,
        drive_type: DriveType,
        amount: float
    ) -> float:
        """Increase drive intensity."""
        new_intensity = self._drive_system.increase_drive(drive_type, amount)

        self._dynamics.record_event(
            "drive_increased",
            {"drive": drive_type.value, "amount": amount},
            amount
        )

        return new_intensity

    def satisfy_drive(
        self,
        drive_type: DriveType,
        satisfaction: float
    ) -> float:
        """Satisfy a drive."""
        new_intensity = self._drive_system.satisfy_drive(drive_type, satisfaction)

        self._dynamics.record_event(
            "drive_satisfied",
            {"drive": drive_type.value, "satisfaction": satisfaction},
            -satisfaction
        )

        return new_intensity

    def get_dominant_drive(self) -> Optional[DriveType]:
        """Get the dominant drive."""
        return self._drive_system.get_dominant_drive()

    def get_all_drives(self) -> Dict[DriveType, float]:
        """Get all drive intensities."""
        return self._drive_system.get_all_drives()

    # -------------------------------------------------------------------------
    # NEED MANAGEMENT
    # -------------------------------------------------------------------------

    def get_need(self, need_type: NeedType) -> Need:
        """Get need by type."""
        return self._need_system.get_need(need_type)

    def satisfy_need(
        self,
        need_type: NeedType,
        amount: float
    ) -> float:
        """Satisfy a need."""
        new_level = self._need_system.satisfy_need(need_type, amount)

        self._dynamics.record_event(
            "need_satisfied",
            {"need": need_type.value, "amount": amount},
            amount
        )

        return new_level

    def deplete_need(
        self,
        need_type: NeedType,
        amount: float
    ) -> float:
        """Deplete a need."""
        new_level = self._need_system.deplete_need(need_type, amount)

        self._dynamics.record_event(
            "need_depleted",
            {"need": need_type.value, "amount": amount},
            -amount
        )

        return new_level

    def get_unsatisfied_needs(self) -> List[NeedType]:
        """Get list of unsatisfied needs."""
        return self._need_system.get_unsatisfied_needs()

    def get_wellbeing(self) -> float:
        """Compute overall wellbeing."""
        return self._need_system.compute_wellbeing()

    # -------------------------------------------------------------------------
    # GOAL MANAGEMENT
    # -------------------------------------------------------------------------

    def add_goal(
        self,
        name: str,
        description: str = "",
        priority: GoalPriority = GoalPriority.MEDIUM,
        parent_goal: Optional[str] = None,
        deadline: Optional[datetime] = None,
        associated_drives: Optional[List[DriveType]] = None,
        associated_needs: Optional[List[NeedType]] = None,
        reward_value: float = 1.0
    ) -> Goal:
        """Add a goal."""
        goal = self._goal_hierarchy.add_goal(
            name=name,
            description=description,
            priority=priority,
            parent_goal=parent_goal,
            deadline=deadline,
            associated_drives=associated_drives,
            associated_needs=associated_needs,
            reward_value=reward_value
        )

        self._dynamics.record_event(
            "goal_added",
            {"goal_id": goal.goal_id, "name": name, "priority": priority.value},
            0.2
        )

        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get goal by ID."""
        return self._goal_hierarchy.get_goal(goal_id)

    def update_goal_progress(
        self,
        goal_id: str,
        progress: float
    ) -> bool:
        """Update goal progress."""
        success = self._goal_hierarchy.update_progress(goal_id, progress)

        if success:
            goal = self._goal_hierarchy.get_goal(goal_id)
            if goal and goal.status == GoalStatus.ACHIEVED:
                self._on_goal_achieved(goal)

        return success

    def _on_goal_achieved(self, goal: Goal) -> None:
        """Handle goal achievement."""
        # Satisfy associated drives
        for drive_type in goal.associated_drives:
            self.satisfy_drive(drive_type, goal.reward_value * 0.3)

        # Satisfy associated needs
        for need_type in goal.associated_needs:
            self.satisfy_need(need_type, goal.reward_value * 0.2)

        self._dynamics.record_event(
            "goal_achieved",
            {"goal_id": goal.goal_id, "name": goal.name},
            goal.reward_value
        )

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals."""
        return self._goal_hierarchy.get_active_goals()

    def get_goals_by_priority(
        self,
        priority: GoalPriority
    ) -> List[Goal]:
        """Get goals by priority."""
        return self._goal_hierarchy.get_goals_by_priority(priority)

    def compute_goal_value(self, goal_id: str) -> float:
        """Compute motivational value of a goal."""
        return self._goal_hierarchy.compute_goal_value(goal_id)

    # -------------------------------------------------------------------------
    # INCENTIVE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_incentive(
        self,
        incentive_type: IncentiveType,
        value: float,
        source: str,
        conditions: Optional[Dict[str, Any]] = None,
        expiry: Optional[datetime] = None
    ) -> Incentive:
        """Create an incentive."""
        return self._incentive_system.create_incentive(
            incentive_type=incentive_type,
            value=value,
            source=source,
            conditions=conditions,
            expiry=expiry
        )

    def claim_incentive(self, incentive_id: str) -> float:
        """Claim an incentive."""
        value = self._incentive_system.claim_incentive(incentive_id)

        if value > 0:
            self._dynamics.record_event(
                "incentive_claimed",
                {"incentive_id": incentive_id, "value": value},
                value
            )

        return value

    def get_pending_incentives(self) -> List[Incentive]:
        """Get pending incentives."""
        return self._incentive_system.get_pending_incentives()

    def get_total_pending_incentive_value(self) -> float:
        """Get total value of pending incentives."""
        return self._incentive_system.compute_total_pending_value()

    # -------------------------------------------------------------------------
    # MOTIVATION STATE
    # -------------------------------------------------------------------------

    def compute_motivation_state(self) -> MotivationState:
        """Compute current motivation state."""
        # Get components
        drive_intensities = self._drive_system.get_all_drives()
        unsatisfied_needs = self._need_system.get_unsatisfied_needs()
        active_goals = [g.goal_id for g in self._goal_hierarchy.get_active_goals()]
        pending_incentives = [
            i.incentive_id for i in self._incentive_system.get_pending_incentives()
        ]
        dominant_drive = self._drive_system.get_dominant_drive()

        # Compute overall motivation
        drive_component = sum(drive_intensities.values()) / len(drive_intensities) if drive_intensities else 0.5
        need_component = len(unsatisfied_needs) * 0.1  # Unmet needs increase motivation
        goal_component = min(1.0, len(active_goals) * 0.1)
        incentive_component = min(1.0, self._incentive_system.compute_total_pending_value() * 0.1)

        overall = (
            drive_component * 0.4 +
            need_component * 0.2 +
            goal_component * 0.2 +
            incentive_component * 0.2
        )

        overall = max(0.0, min(1.0, overall))

        state = MotivationState(
            overall_motivation=overall,
            dominant_drive=dominant_drive,
            active_goals=active_goals,
            unsatisfied_needs=unsatisfied_needs,
            pending_incentives=pending_incentives
        )

        self._current_state = state
        self._dynamics.record_state(state)

        return state

    def get_current_state(self) -> Optional[MotivationState]:
        """Get current motivation state."""
        return self._current_state

    # -------------------------------------------------------------------------
    # DYNAMICS
    # -------------------------------------------------------------------------

    def get_motivation_momentum(self) -> float:
        """Get motivation momentum."""
        return self._dynamics.compute_momentum()

    def get_motivation_volatility(self) -> float:
        """Get motivation volatility."""
        return self._dynamics.compute_volatility()

    def predict_motivation(self, steps_ahead: int = 1) -> float:
        """Predict future motivation."""
        return self._dynamics.predict_motivation(steps_ahead)

    def get_recent_events(self, count: int = 10) -> List[MotivationEvent]:
        """Get recent motivation events."""
        return self._dynamics.get_recent_events(count)

    # -------------------------------------------------------------------------
    # UPDATE
    # -------------------------------------------------------------------------

    def update(self, delta_time: float = 1.0) -> MotivationState:
        """Update motivation system."""
        # Update drives
        self._drive_system.update_drives(delta_time)

        # Compute new state
        return self.compute_motivation_state()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Motivation Manager."""
    print("=" * 70)
    print("BAEL - MOTIVATION MANAGER DEMO")
    print("Advanced Motivation and Goal-Driven Behavior System")
    print("=" * 70)
    print()

    manager = MotivationManager()

    # 1. Initial State
    print("1. INITIAL STATE:")
    print("-" * 40)

    state = manager.compute_motivation_state()
    print(f"   Overall motivation: {state.overall_motivation:.1%}")
    print(f"   Dominant drive: {state.dominant_drive.value if state.dominant_drive else 'None'}")
    print()

    # 2. Drive System
    print("2. DRIVE SYSTEM:")
    print("-" * 40)

    drives = manager.get_all_drives()
    for drive_type, intensity in drives.items():
        print(f"   {drive_type.value}: {intensity:.2f}")
    print()

    # 3. Increase Drive
    print("3. INCREASE CURIOSITY DRIVE:")
    print("-" * 40)

    new_intensity = manager.increase_drive(DriveType.CURIOSITY, 0.3)
    print(f"   Curiosity drive: {new_intensity:.2f}")

    dominant = manager.get_dominant_drive()
    print(f"   Dominant drive: {dominant.value if dominant else 'None'}")
    print()

    # 4. Need Satisfaction
    print("4. NEED SATISFACTION:")
    print("-" * 40)

    unsatisfied = manager.get_unsatisfied_needs()
    print(f"   Unsatisfied needs: {[n.value for n in unsatisfied]}")

    # Satisfy autonomy
    manager.satisfy_need(NeedType.AUTONOMY, 0.3)
    wellbeing = manager.get_wellbeing()
    print(f"   Wellbeing after satisfying autonomy: {wellbeing:.2f}")
    print()

    # 5. Add Goals
    print("5. ADD GOALS:")
    print("-" * 40)

    main_goal = manager.add_goal(
        name="Learn New Skill",
        description="Master a new programming language",
        priority=GoalPriority.HIGH,
        associated_drives=[DriveType.CURIOSITY, DriveType.COMPETENCE],
        associated_needs=[NeedType.COMPETENCE, NeedType.AUTONOMY],
        reward_value=1.5
    )

    sub_goal1 = manager.add_goal(
        name="Complete Tutorial",
        description="Finish the beginner tutorial",
        priority=GoalPriority.MEDIUM,
        parent_goal=main_goal.goal_id,
        reward_value=0.5
    )

    sub_goal2 = manager.add_goal(
        name="Build Project",
        description="Build a small project",
        priority=GoalPriority.MEDIUM,
        parent_goal=main_goal.goal_id,
        reward_value=0.8
    )

    active_goals = manager.get_active_goals()
    print(f"   Active goals: {len(active_goals)}")
    for goal in active_goals:
        print(f"     - {goal.name} ({goal.priority.value})")
    print()

    # 6. Goal Progress
    print("6. GOAL PROGRESS:")
    print("-" * 40)

    manager.update_goal_progress(sub_goal1.goal_id, 0.5)
    print(f"   '{sub_goal1.name}' progress: 50%")

    manager.update_goal_progress(sub_goal1.goal_id, 1.0)
    goal = manager.get_goal(sub_goal1.goal_id)
    print(f"   '{sub_goal1.name}' status: {goal.status.value}")
    print()

    # 7. Incentives
    print("7. INCENTIVES:")
    print("-" * 40)

    incentive = manager.create_incentive(
        incentive_type=IncentiveType.ACHIEVEMENT,
        value=2.0,
        source="system",
        conditions={"complete_project": True}
    )

    print(f"   Created incentive: {incentive.incentive_type.value}")
    print(f"   Value: {incentive.value}")

    pending = manager.get_pending_incentives()
    print(f"   Pending incentives: {len(pending)}")
    print(f"   Total pending value: {manager.get_total_pending_incentive_value()}")
    print()

    # 8. Claim Incentive
    print("8. CLAIM INCENTIVE:")
    print("-" * 40)

    claimed_value = manager.claim_incentive(incentive.incentive_id)
    print(f"   Claimed value: {claimed_value}")
    print(f"   Remaining pending: {len(manager.get_pending_incentives())}")
    print()

    # 9. Updated State
    print("9. UPDATED STATE:")
    print("-" * 40)

    state = manager.compute_motivation_state()
    print(f"   Overall motivation: {state.overall_motivation:.1%}")
    print(f"   Dominant drive: {state.dominant_drive.value if state.dominant_drive else 'None'}")
    print(f"   Active goals: {len(state.active_goals)}")
    print(f"   Unsatisfied needs: {[n.value for n in state.unsatisfied_needs]}")
    print()

    # 10. Motivation Dynamics
    print("10. MOTIVATION DYNAMICS:")
    print("-" * 40)

    # Record a few more states
    for _ in range(5):
        manager.increase_drive(DriveType.ACHIEVEMENT, random.uniform(0.05, 0.1))
        manager.update()

    momentum = manager.get_motivation_momentum()
    volatility = manager.get_motivation_volatility()
    predicted = manager.predict_motivation(3)

    print(f"   Momentum: {momentum:+.3f}")
    print(f"   Volatility: {volatility:.3f}")
    print(f"   Predicted (3 steps): {predicted:.2f}")
    print()

    # 11. Recent Events
    print("11. RECENT EVENTS:")
    print("-" * 40)

    events = manager.get_recent_events(5)
    for event in events:
        print(f"   {event.event_type}: impact={event.impact:+.2f}")
    print()

    # 12. Goal Value
    print("12. GOAL VALUE COMPUTATION:")
    print("-" * 40)

    for goal in manager.get_active_goals()[:3]:
        value = manager.compute_goal_value(goal.goal_id)
        print(f"   {goal.name}: {value:.2f}")
    print()

    # 13. Satisfy Drive
    print("13. SATISFY CURIOSITY DRIVE:")
    print("-" * 40)

    before = manager.get_drive(DriveType.CURIOSITY).intensity
    manager.satisfy_drive(DriveType.CURIOSITY, 0.4)
    after = manager.get_drive(DriveType.CURIOSITY).intensity

    print(f"   Before: {before:.2f}")
    print(f"   After: {after:.2f}")
    print()

    # 14. Final State
    print("14. FINAL STATE:")
    print("-" * 40)

    final_state = manager.update()
    print(f"   Overall motivation: {final_state.overall_motivation:.1%}")
    print(f"   Wellbeing: {manager.get_wellbeing():.1%}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Motivation Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
