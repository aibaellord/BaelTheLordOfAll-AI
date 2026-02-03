#!/usr/bin/env python3
"""
BAEL - Goal Manager
Advanced goal management and tracking for AI agents.

Features:
- Goal hierarchy
- Goal decomposition
- Progress tracking
- Goal prioritization
- Conflict resolution
- Goal achievement
- Temporal goals
- Metric-based goals
"""

import asyncio
import copy
import hashlib
import json
import math
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class GoalStatus(Enum):
    """Goal status."""
    PENDING = "pending"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    ACHIEVED = "achieved"
    FAILED = "failed"
    ABANDONED = "abandoned"


class GoalPriority(Enum):
    """Goal priority."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1


class GoalType(Enum):
    """Goal type."""
    ACHIEVEMENT = "achievement"
    MAINTENANCE = "maintenance"
    TEMPORAL = "temporal"
    METRIC = "metric"
    COMPOSITE = "composite"


class ConflictType(Enum):
    """Goal conflict type."""
    RESOURCE = "resource"
    TEMPORAL = "temporal"
    LOGICAL = "logical"
    PRIORITY = "priority"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class GoalCondition:
    """Goal condition."""
    condition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    check: Optional[Callable[[], bool]] = None
    satisfied: bool = False


@dataclass
class GoalMetric:
    """Goal metric."""
    name: str = ""
    target_value: float = 0.0
    current_value: float = 0.0
    unit: str = ""
    higher_is_better: bool = True


@dataclass
class Goal:
    """Agent goal."""
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    goal_type: GoalType = GoalType.ACHIEVEMENT
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PENDING
    parent_id: Optional[str] = None
    subgoals: List[str] = field(default_factory=list)
    preconditions: List[GoalCondition] = field(default_factory=list)
    postconditions: List[GoalCondition] = field(default_factory=list)
    metrics: List[GoalMetric] = field(default_factory=list)
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalConflict:
    """Goal conflict."""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal1_id: str = ""
    goal2_id: str = ""
    conflict_type: ConflictType = ConflictType.RESOURCE
    description: str = ""
    resolved: bool = False


@dataclass
class GoalPlan:
    """Plan to achieve goal."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str = ""
    steps: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    resources: List[str] = field(default_factory=list)


@dataclass
class GoalStats:
    """Goal statistics."""
    total_goals: int = 0
    active_goals: int = 0
    achieved_goals: int = 0
    failed_goals: int = 0
    avg_completion_time: float = 0.0


# =============================================================================
# GOAL FACTORY
# =============================================================================

class GoalFactory:
    """Factory for creating goals."""

    @staticmethod
    def create_achievement_goal(
        name: str,
        description: str = "",
        priority: GoalPriority = GoalPriority.MEDIUM
    ) -> Goal:
        """Create achievement goal."""
        return Goal(
            name=name,
            description=description,
            goal_type=GoalType.ACHIEVEMENT,
            priority=priority
        )

    @staticmethod
    def create_metric_goal(
        name: str,
        metric_name: str,
        target_value: float,
        unit: str = "",
        higher_is_better: bool = True
    ) -> Goal:
        """Create metric goal."""
        goal = Goal(
            name=name,
            goal_type=GoalType.METRIC
        )

        goal.metrics.append(GoalMetric(
            name=metric_name,
            target_value=target_value,
            unit=unit,
            higher_is_better=higher_is_better
        ))

        return goal

    @staticmethod
    def create_temporal_goal(
        name: str,
        deadline: datetime,
        priority: GoalPriority = GoalPriority.HIGH
    ) -> Goal:
        """Create temporal goal."""
        return Goal(
            name=name,
            goal_type=GoalType.TEMPORAL,
            priority=priority,
            deadline=deadline
        )

    @staticmethod
    def create_maintenance_goal(
        name: str,
        check_condition: Callable[[], bool]
    ) -> Goal:
        """Create maintenance goal."""
        goal = Goal(
            name=name,
            goal_type=GoalType.MAINTENANCE
        )

        goal.postconditions.append(GoalCondition(
            name="maintenance_check",
            check=check_condition
        ))

        return goal


# =============================================================================
# GOAL HIERARCHY
# =============================================================================

class GoalHierarchy:
    """Goal hierarchy manager."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._children: Dict[str, List[str]] = defaultdict(list)
        self._root_goals: Set[str] = set()

    def add_goal(self, goal: Goal) -> str:
        """Add goal."""
        self._goals[goal.goal_id] = goal

        if goal.parent_id:
            self._children[goal.parent_id].append(goal.goal_id)
            if goal.parent_id in self._goals:
                self._goals[goal.parent_id].subgoals.append(goal.goal_id)
        else:
            self._root_goals.add(goal.goal_id)

        return goal.goal_id

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get goal."""
        return self._goals.get(goal_id)

    def set_parent(self, goal_id: str, parent_id: str) -> bool:
        """Set goal parent."""
        goal = self._goals.get(goal_id)
        parent = self._goals.get(parent_id)

        if not goal or not parent:
            return False

        # Remove from old parent
        if goal.parent_id:
            self._children[goal.parent_id].remove(goal_id)
        else:
            self._root_goals.discard(goal_id)

        # Set new parent
        goal.parent_id = parent_id
        self._children[parent_id].append(goal_id)
        parent.subgoals.append(goal_id)

        return True

    def get_children(self, goal_id: str) -> List[Goal]:
        """Get child goals."""
        child_ids = self._children.get(goal_id, [])
        return [self._goals[cid] for cid in child_ids if cid in self._goals]

    def get_ancestors(self, goal_id: str) -> List[Goal]:
        """Get ancestor goals."""
        ancestors = []
        goal = self._goals.get(goal_id)

        while goal and goal.parent_id:
            parent = self._goals.get(goal.parent_id)
            if parent:
                ancestors.append(parent)
                goal = parent
            else:
                break

        return ancestors

    def get_root_goals(self) -> List[Goal]:
        """Get root goals."""
        return [self._goals[gid] for gid in self._root_goals if gid in self._goals]

    def get_all_descendants(self, goal_id: str) -> List[Goal]:
        """Get all descendant goals."""
        descendants = []

        def collect(gid: str) -> None:
            for child_id in self._children.get(gid, []):
                if child_id in self._goals:
                    descendants.append(self._goals[child_id])
                    collect(child_id)

        collect(goal_id)
        return descendants


# =============================================================================
# GOAL TRACKER
# =============================================================================

class GoalTracker:
    """Track goal progress."""

    def __init__(self, hierarchy: GoalHierarchy):
        self._hierarchy = hierarchy
        self._progress_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)

    def update_progress(self, goal_id: str, progress: float) -> bool:
        """Update goal progress."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return False

        goal.progress = max(0.0, min(1.0, progress))
        self._progress_history[goal_id].append((datetime.now(), goal.progress))

        # Update parent progress
        if goal.parent_id:
            self._update_parent_progress(goal.parent_id)

        # Check completion
        if goal.progress >= 1.0:
            self._check_completion(goal_id)

        return True

    def _update_parent_progress(self, parent_id: str) -> None:
        """Update parent goal progress."""
        children = self._hierarchy.get_children(parent_id)

        if not children:
            return

        avg_progress = sum(c.progress for c in children) / len(children)

        parent = self._hierarchy.get_goal(parent_id)
        if parent:
            parent.progress = avg_progress

    def _check_completion(self, goal_id: str) -> None:
        """Check if goal is completed."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return

        if goal.goal_type == GoalType.ACHIEVEMENT:
            if goal.progress >= 1.0:
                goal.status = GoalStatus.ACHIEVED
                goal.completed_at = datetime.now()

        elif goal.goal_type == GoalType.METRIC:
            if self._check_metrics(goal):
                goal.status = GoalStatus.ACHIEVED
                goal.completed_at = datetime.now()

    def _check_metrics(self, goal: Goal) -> bool:
        """Check metric goals."""
        for metric in goal.metrics:
            if metric.higher_is_better:
                if metric.current_value < metric.target_value:
                    return False
            else:
                if metric.current_value > metric.target_value:
                    return False
        return True

    def update_metric(
        self,
        goal_id: str,
        metric_name: str,
        value: float
    ) -> bool:
        """Update metric value."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return False

        for metric in goal.metrics:
            if metric.name == metric_name:
                metric.current_value = value

                # Update progress
                if metric.higher_is_better:
                    progress = min(1.0, value / metric.target_value) if metric.target_value > 0 else 0
                else:
                    progress = min(1.0, metric.target_value / value) if value > 0 else 0

                goal.progress = progress
                self._check_completion(goal_id)
                return True

        return False

    def get_progress_history(
        self,
        goal_id: str,
        limit: int = 100
    ) -> List[Tuple[datetime, float]]:
        """Get progress history."""
        history = self._progress_history.get(goal_id, [])
        return history[-limit:]


# =============================================================================
# GOAL PRIORITIZER
# =============================================================================

class GoalPrioritizer:
    """Prioritize goals."""

    def __init__(self, hierarchy: GoalHierarchy):
        self._hierarchy = hierarchy

    def prioritize(self, goals: List[Goal]) -> List[Goal]:
        """Prioritize goals."""
        return sorted(
            goals,
            key=lambda g: self._calculate_priority_score(g),
            reverse=True
        )

    def _calculate_priority_score(self, goal: Goal) -> float:
        """Calculate priority score."""
        score = goal.priority.value * 10

        # Deadline urgency
        if goal.deadline:
            time_left = (goal.deadline - datetime.now()).total_seconds()
            if time_left < 0:
                score += 50  # Overdue
            elif time_left < 3600:  # Less than 1 hour
                score += 30
            elif time_left < 86400:  # Less than 1 day
                score += 20

        # Progress factor (favor goals close to completion)
        if 0.5 <= goal.progress < 1.0:
            score += 10 * goal.progress

        # Blocked penalty
        if goal.status == GoalStatus.BLOCKED:
            score -= 20

        return score

    def get_most_urgent(self) -> Optional[Goal]:
        """Get most urgent goal."""
        active_goals = [
            g for g in self._hierarchy._goals.values()
            if g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS)
        ]

        prioritized = self.prioritize(active_goals)
        return prioritized[0] if prioritized else None


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver:
    """Resolve goal conflicts."""

    def __init__(self, hierarchy: GoalHierarchy):
        self._hierarchy = hierarchy
        self._conflicts: Dict[str, GoalConflict] = {}

    def detect_conflicts(self, goals: List[Goal]) -> List[GoalConflict]:
        """Detect conflicts between goals."""
        conflicts = []

        for i, goal1 in enumerate(goals):
            for goal2 in goals[i+1:]:
                conflict = self._check_conflict(goal1, goal2)
                if conflict:
                    conflicts.append(conflict)
                    self._conflicts[conflict.conflict_id] = conflict

        return conflicts

    def _check_conflict(
        self,
        goal1: Goal,
        goal2: Goal
    ) -> Optional[GoalConflict]:
        """Check if two goals conflict."""
        # Temporal conflict
        if goal1.deadline and goal2.deadline:
            if abs((goal1.deadline - goal2.deadline).total_seconds()) < 3600:
                return GoalConflict(
                    goal1_id=goal1.goal_id,
                    goal2_id=goal2.goal_id,
                    conflict_type=ConflictType.TEMPORAL,
                    description="Deadline overlap"
                )

        # Resource conflict (check metadata)
        resources1 = set(goal1.metadata.get("resources", []))
        resources2 = set(goal2.metadata.get("resources", []))

        if resources1 & resources2:
            return GoalConflict(
                goal1_id=goal1.goal_id,
                goal2_id=goal2.goal_id,
                conflict_type=ConflictType.RESOURCE,
                description=f"Shared resources: {resources1 & resources2}"
            )

        return None

    def resolve_by_priority(
        self,
        conflict: GoalConflict
    ) -> Optional[str]:
        """Resolve conflict by priority."""
        goal1 = self._hierarchy.get_goal(conflict.goal1_id)
        goal2 = self._hierarchy.get_goal(conflict.goal2_id)

        if not goal1 or not goal2:
            return None

        # Higher priority wins
        if goal1.priority.value > goal2.priority.value:
            goal2.status = GoalStatus.BLOCKED
            conflict.resolved = True
            return goal1.goal_id
        elif goal2.priority.value > goal1.priority.value:
            goal1.status = GoalStatus.BLOCKED
            conflict.resolved = True
            return goal2.goal_id

        return None


# =============================================================================
# GOAL PLANNER
# =============================================================================

class GoalPlanner:
    """Plan goal achievement."""

    def __init__(self, hierarchy: GoalHierarchy):
        self._hierarchy = hierarchy
        self._plans: Dict[str, GoalPlan] = {}

    def create_plan(
        self,
        goal_id: str,
        steps: List[str],
        estimated_duration: float = 0.0,
        resources: Optional[List[str]] = None
    ) -> GoalPlan:
        """Create plan for goal."""
        plan = GoalPlan(
            goal_id=goal_id,
            steps=steps,
            estimated_duration=estimated_duration,
            resources=resources or []
        )

        self._plans[goal_id] = plan
        return plan

    def get_plan(self, goal_id: str) -> Optional[GoalPlan]:
        """Get goal plan."""
        return self._plans.get(goal_id)

    def decompose_goal(
        self,
        goal_id: str,
        subgoal_names: List[str]
    ) -> List[Goal]:
        """Decompose goal into subgoals."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return []

        subgoals = []

        for name in subgoal_names:
            subgoal = Goal(
                name=name,
                goal_type=goal.goal_type,
                priority=goal.priority,
                parent_id=goal_id
            )

            self._hierarchy.add_goal(subgoal)
            subgoals.append(subgoal)

        goal.goal_type = GoalType.COMPOSITE
        return subgoals


# =============================================================================
# GOAL MANAGER
# =============================================================================

class GoalManager:
    """
    Goal Manager for BAEL.

    Advanced goal management and tracking.
    """

    def __init__(self):
        self._hierarchy = GoalHierarchy()
        self._tracker = GoalTracker(self._hierarchy)
        self._prioritizer = GoalPrioritizer(self._hierarchy)
        self._conflict_resolver = ConflictResolver(self._hierarchy)
        self._planner = GoalPlanner(self._hierarchy)
        self._factory = GoalFactory()

    # -------------------------------------------------------------------------
    # GOAL CREATION
    # -------------------------------------------------------------------------

    def create_goal(
        self,
        name: str,
        description: str = "",
        goal_type: str = "achievement",
        priority: str = "medium"
    ) -> Goal:
        """Create goal."""
        type_map = {
            "achievement": GoalType.ACHIEVEMENT,
            "maintenance": GoalType.MAINTENANCE,
            "temporal": GoalType.TEMPORAL,
            "metric": GoalType.METRIC,
            "composite": GoalType.COMPOSITE
        }

        priority_map = {
            "critical": GoalPriority.CRITICAL,
            "high": GoalPriority.HIGH,
            "medium": GoalPriority.MEDIUM,
            "low": GoalPriority.LOW,
            "optional": GoalPriority.OPTIONAL
        }

        goal = Goal(
            name=name,
            description=description,
            goal_type=type_map.get(goal_type.lower(), GoalType.ACHIEVEMENT),
            priority=priority_map.get(priority.lower(), GoalPriority.MEDIUM)
        )

        self._hierarchy.add_goal(goal)
        return goal

    def create_metric_goal(
        self,
        name: str,
        metric_name: str,
        target_value: float,
        unit: str = ""
    ) -> Goal:
        """Create metric goal."""
        goal = self._factory.create_metric_goal(
            name=name,
            metric_name=metric_name,
            target_value=target_value,
            unit=unit
        )

        self._hierarchy.add_goal(goal)
        return goal

    def create_deadline_goal(
        self,
        name: str,
        deadline: datetime,
        priority: str = "high"
    ) -> Goal:
        """Create deadline goal."""
        priority_map = {
            "critical": GoalPriority.CRITICAL,
            "high": GoalPriority.HIGH,
            "medium": GoalPriority.MEDIUM,
            "low": GoalPriority.LOW
        }

        goal = self._factory.create_temporal_goal(
            name=name,
            deadline=deadline,
            priority=priority_map.get(priority.lower(), GoalPriority.HIGH)
        )

        self._hierarchy.add_goal(goal)
        return goal

    # -------------------------------------------------------------------------
    # GOAL MANAGEMENT
    # -------------------------------------------------------------------------

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get goal."""
        return self._hierarchy.get_goal(goal_id)

    def activate_goal(self, goal_id: str) -> bool:
        """Activate goal."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return False

        goal.status = GoalStatus.ACTIVE
        goal.started_at = datetime.now()
        return True

    def start_goal(self, goal_id: str) -> bool:
        """Start working on goal."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return False

        goal.status = GoalStatus.IN_PROGRESS

        if not goal.started_at:
            goal.started_at = datetime.now()

        return True

    def complete_goal(self, goal_id: str) -> bool:
        """Mark goal as achieved."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return False

        goal.status = GoalStatus.ACHIEVED
        goal.completed_at = datetime.now()
        goal.progress = 1.0
        return True

    def fail_goal(self, goal_id: str, reason: str = "") -> bool:
        """Mark goal as failed."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return False

        goal.status = GoalStatus.FAILED
        goal.completed_at = datetime.now()
        goal.metadata["failure_reason"] = reason
        return True

    def abandon_goal(self, goal_id: str) -> bool:
        """Abandon goal."""
        goal = self._hierarchy.get_goal(goal_id)

        if not goal:
            return False

        goal.status = GoalStatus.ABANDONED
        goal.completed_at = datetime.now()
        return True

    # -------------------------------------------------------------------------
    # HIERARCHY
    # -------------------------------------------------------------------------

    def add_subgoal(
        self,
        parent_id: str,
        subgoal: Goal
    ) -> bool:
        """Add subgoal."""
        subgoal.parent_id = parent_id
        self._hierarchy.add_goal(subgoal)
        return True

    def decompose_goal(
        self,
        goal_id: str,
        subgoal_names: List[str]
    ) -> List[Goal]:
        """Decompose goal into subgoals."""
        return self._planner.decompose_goal(goal_id, subgoal_names)

    def get_subgoals(self, goal_id: str) -> List[Goal]:
        """Get subgoals."""
        return self._hierarchy.get_children(goal_id)

    def get_root_goals(self) -> List[Goal]:
        """Get root goals."""
        return self._hierarchy.get_root_goals()

    # -------------------------------------------------------------------------
    # PROGRESS
    # -------------------------------------------------------------------------

    def update_progress(self, goal_id: str, progress: float) -> bool:
        """Update goal progress."""
        return self._tracker.update_progress(goal_id, progress)

    def update_metric(
        self,
        goal_id: str,
        metric_name: str,
        value: float
    ) -> bool:
        """Update metric value."""
        return self._tracker.update_metric(goal_id, metric_name, value)

    def get_progress(self, goal_id: str) -> float:
        """Get goal progress."""
        goal = self._hierarchy.get_goal(goal_id)
        return goal.progress if goal else 0.0

    # -------------------------------------------------------------------------
    # PRIORITIZATION
    # -------------------------------------------------------------------------

    def prioritize_goals(self) -> List[Goal]:
        """Get prioritized goals."""
        active = [
            g for g in self._hierarchy._goals.values()
            if g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS)
        ]
        return self._prioritizer.prioritize(active)

    def get_most_urgent(self) -> Optional[Goal]:
        """Get most urgent goal."""
        return self._prioritizer.get_most_urgent()

    # -------------------------------------------------------------------------
    # CONFLICTS
    # -------------------------------------------------------------------------

    def detect_conflicts(self) -> List[GoalConflict]:
        """Detect goal conflicts."""
        active = [
            g for g in self._hierarchy._goals.values()
            if g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS, GoalStatus.PENDING)
        ]
        return self._conflict_resolver.detect_conflicts(active)

    def resolve_conflict(self, conflict: GoalConflict) -> Optional[str]:
        """Resolve conflict."""
        return self._conflict_resolver.resolve_by_priority(conflict)

    # -------------------------------------------------------------------------
    # PLANNING
    # -------------------------------------------------------------------------

    def create_plan(
        self,
        goal_id: str,
        steps: List[str],
        estimated_duration: float = 0.0
    ) -> GoalPlan:
        """Create goal plan."""
        return self._planner.create_plan(goal_id, steps, estimated_duration)

    def get_plan(self, goal_id: str) -> Optional[GoalPlan]:
        """Get goal plan."""
        return self._planner.get_plan(goal_id)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> GoalStats:
        """Get goal statistics."""
        goals = list(self._hierarchy._goals.values())

        achieved = [g for g in goals if g.status == GoalStatus.ACHIEVED]
        completion_times = [
            (g.completed_at - g.started_at).total_seconds()
            for g in achieved
            if g.started_at and g.completed_at
        ]

        return GoalStats(
            total_goals=len(goals),
            active_goals=sum(1 for g in goals if g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS)),
            achieved_goals=len(achieved),
            failed_goals=sum(1 for g in goals if g.status == GoalStatus.FAILED),
            avg_completion_time=sum(completion_times) / len(completion_times) if completion_times else 0.0
        )

    def get_goals_by_status(self, status: str) -> List[Goal]:
        """Get goals by status."""
        status_map = {
            "pending": GoalStatus.PENDING,
            "active": GoalStatus.ACTIVE,
            "in_progress": GoalStatus.IN_PROGRESS,
            "blocked": GoalStatus.BLOCKED,
            "achieved": GoalStatus.ACHIEVED,
            "failed": GoalStatus.FAILED,
            "abandoned": GoalStatus.ABANDONED
        }

        target_status = status_map.get(status.lower())

        if not target_status:
            return []

        return [
            g for g in self._hierarchy._goals.values()
            if g.status == target_status
        ]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Goal Manager."""
    print("=" * 70)
    print("BAEL - GOAL MANAGER DEMO")
    print("Advanced Goal Management and Tracking")
    print("=" * 70)
    print()

    manager = GoalManager()

    # 1. Create Goals
    print("1. CREATE GOALS:")
    print("-" * 40)

    main_goal = manager.create_goal(
        name="Build AI System",
        description="Create a complete AI agent system",
        goal_type="achievement",
        priority="high"
    )

    print(f"   Created: {main_goal.name}")
    print(f"   Type: {main_goal.goal_type.value}")
    print(f"   Priority: {main_goal.priority.value}")
    print()

    # 2. Metric Goal
    print("2. METRIC GOAL:")
    print("-" * 40)

    metric_goal = manager.create_metric_goal(
        name="Achieve 90% Accuracy",
        metric_name="accuracy",
        target_value=0.90,
        unit="percent"
    )

    print(f"   Created: {metric_goal.name}")
    print(f"   Target: {metric_goal.metrics[0].target_value}")
    print()

    # 3. Deadline Goal
    print("3. DEADLINE GOAL:")
    print("-" * 40)

    deadline_goal = manager.create_deadline_goal(
        name="Complete by Friday",
        deadline=datetime.now() + timedelta(days=5),
        priority="critical"
    )

    print(f"   Created: {deadline_goal.name}")
    print(f"   Deadline: {deadline_goal.deadline}")
    print()

    # 4. Goal Decomposition
    print("4. GOAL DECOMPOSITION:")
    print("-" * 40)

    subgoals = manager.decompose_goal(main_goal.goal_id, [
        "Design Architecture",
        "Implement Core",
        "Add Features",
        "Test System"
    ])

    print(f"   Parent: {main_goal.name}")
    print(f"   Subgoals:")
    for sg in subgoals:
        print(f"     - {sg.name}")
    print()

    # 5. Activate Goals
    print("5. ACTIVATE GOALS:")
    print("-" * 40)

    manager.activate_goal(main_goal.goal_id)
    for sg in subgoals:
        manager.activate_goal(sg.goal_id)

    print(f"   Activated: {main_goal.name}")
    print(f"   Status: {main_goal.status.value}")
    print()

    # 6. Update Progress
    print("6. UPDATE PROGRESS:")
    print("-" * 40)

    manager.start_goal(subgoals[0].goal_id)
    manager.update_progress(subgoals[0].goal_id, 0.5)

    print(f"   {subgoals[0].name}: {subgoals[0].progress*100:.0f}%")

    manager.update_progress(subgoals[0].goal_id, 1.0)

    print(f"   {subgoals[0].name}: {subgoals[0].progress*100:.0f}% (completed)")
    print(f"   Parent progress: {main_goal.progress*100:.0f}%")
    print()

    # 7. Metric Update
    print("7. METRIC UPDATE:")
    print("-" * 40)

    manager.activate_goal(metric_goal.goal_id)
    manager.update_metric(metric_goal.goal_id, "accuracy", 0.75)

    print(f"   Current accuracy: {metric_goal.metrics[0].current_value}")
    print(f"   Progress: {metric_goal.progress*100:.0f}%")

    manager.update_metric(metric_goal.goal_id, "accuracy", 0.92)

    print(f"   New accuracy: {metric_goal.metrics[0].current_value}")
    print(f"   Status: {metric_goal.status.value}")
    print()

    # 8. Prioritization
    print("8. PRIORITIZATION:")
    print("-" * 40)

    prioritized = manager.prioritize_goals()

    print(f"   Prioritized goals:")
    for i, goal in enumerate(prioritized[:5]):
        print(f"     {i+1}. {goal.name} (priority: {goal.priority.value})")
    print()

    # 9. Most Urgent
    print("9. MOST URGENT GOAL:")
    print("-" * 40)

    urgent = manager.get_most_urgent()

    if urgent:
        print(f"   Goal: {urgent.name}")
        print(f"   Priority: {urgent.priority.value}")
    print()

    # 10. Conflict Detection
    print("10. CONFLICT DETECTION:")
    print("-" * 40)

    # Create conflicting goals
    goal_a = manager.create_goal(
        name="Use GPU A",
        priority="high"
    )
    goal_a.metadata["resources"] = ["gpu_0"]
    manager.activate_goal(goal_a.goal_id)

    goal_b = manager.create_goal(
        name="Use GPU B",
        priority="medium"
    )
    goal_b.metadata["resources"] = ["gpu_0"]  # Same resource
    manager.activate_goal(goal_b.goal_id)

    conflicts = manager.detect_conflicts()

    print(f"   Detected conflicts: {len(conflicts)}")
    for conflict in conflicts:
        print(f"     {conflict.conflict_type.value}: {conflict.description}")
    print()

    # 11. Conflict Resolution
    print("11. CONFLICT RESOLUTION:")
    print("-" * 40)

    if conflicts:
        winner_id = manager.resolve_conflict(conflicts[0])
        winner = manager.get_goal(winner_id)

        if winner:
            print(f"   Winner: {winner.name}")
            print(f"   Loser status: blocked")
    print()

    # 12. Create Plan
    print("12. CREATE PLAN:")
    print("-" * 40)

    plan = manager.create_plan(
        main_goal.goal_id,
        steps=[
            "Requirements analysis",
            "System design",
            "Implementation",
            "Testing",
            "Deployment"
        ],
        estimated_duration=86400 * 5  # 5 days
    )

    print(f"   Plan for: {main_goal.name}")
    print(f"   Steps: {len(plan.steps)}")
    for i, step in enumerate(plan.steps):
        print(f"     {i+1}. {step}")
    print()

    # 13. Goal Statistics
    print("13. GOAL STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total goals: {stats.total_goals}")
    print(f"   Active: {stats.active_goals}")
    print(f"   Achieved: {stats.achieved_goals}")
    print(f"   Failed: {stats.failed_goals}")
    print()

    # 14. Goals by Status
    print("14. GOALS BY STATUS:")
    print("-" * 40)

    achieved = manager.get_goals_by_status("achieved")
    active = manager.get_goals_by_status("active")

    print(f"   Achieved goals: {len(achieved)}")
    print(f"   Active goals: {len(active)}")
    print()

    # 15. Complete and Fail Goals
    print("15. COMPLETE AND FAIL:")
    print("-" * 40)

    manager.complete_goal(subgoals[1].goal_id)
    manager.fail_goal(subgoals[2].goal_id, "Resource unavailable")

    print(f"   {subgoals[1].name}: {subgoals[1].status.value}")
    print(f"   {subgoals[2].name}: {subgoals[2].status.value}")
    print(f"   Failure reason: {subgoals[2].metadata.get('failure_reason')}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Goal Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
