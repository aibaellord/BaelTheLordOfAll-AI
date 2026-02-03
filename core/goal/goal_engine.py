#!/usr/bin/env python3
"""
BAEL - Goal Engine
Agent goal management and prioritization.

Features:
- Goal hierarchy
- Goal decomposition
- Priority management
- Achievement tracking
- Conflict detection
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

class GoalStatus(Enum):
    """Goal status."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PURSUING = "pursuing"
    SUSPENDED = "suspended"
    ACHIEVED = "achieved"
    FAILED = "failed"
    ABANDONED = "abandoned"


class GoalType(Enum):
    """Goal types."""
    ACHIEVEMENT = "achievement"
    MAINTENANCE = "maintenance"
    PERFORMANCE = "performance"
    AVOIDANCE = "avoidance"
    LEARNING = "learning"
    EXPLORATORY = "exploratory"


class GoalPriority(Enum):
    """Goal priority levels."""
    CRITICAL = 10
    VERY_HIGH = 8
    HIGH = 6
    MEDIUM = 4
    LOW = 2
    TRIVIAL = 1


class GoalRelation(Enum):
    """Goal relations."""
    ENABLES = "enables"
    DISABLES = "disables"
    CONFLICTS = "conflicts"
    SUBSUMES = "subsumes"
    SUPPORTS = "supports"
    NEUTRAL = "neutral"


class DecompositionStrategy(Enum):
    """Goal decomposition strategies."""
    AND = "and"
    OR = "or"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Goal:
    """A goal."""
    goal_id: str = ""
    name: str = ""
    description: str = ""
    goal_type: GoalType = GoalType.ACHIEVEMENT
    status: GoalStatus = GoalStatus.INACTIVE
    priority: GoalPriority = GoalPriority.MEDIUM
    importance: float = 0.5
    urgency: float = 0.5
    parent_id: Optional[str] = None
    subgoal_ids: List[str] = field(default_factory=list)
    decomposition: DecompositionStrategy = DecompositionStrategy.AND
    preconditions: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    failure_criteria: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.goal_id:
            self.goal_id = str(uuid.uuid4())[:8]

    def __hash__(self):
        return hash(self.goal_id)

    def __eq__(self, other):
        if isinstance(other, Goal):
            return self.goal_id == other.goal_id
        return False

    @property
    def score(self) -> float:
        """Calculate goal score."""
        return (
            self.priority.value * 0.4 +
            self.importance * 10 * 0.3 +
            self.urgency * 10 * 0.3
        )


@dataclass
class GoalRelationship:
    """Relationship between goals."""
    source_id: str
    target_id: str
    relation: GoalRelation
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalContext:
    """Context for goal evaluation."""
    current_state: Dict[str, Any] = field(default_factory=dict)
    available_resources: Dict[str, float] = field(default_factory=dict)
    active_constraints: List[str] = field(default_factory=list)
    external_factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalProgress:
    """Goal progress tracking."""
    goal_id: str
    progress: float = 0.0
    milestones_completed: List[str] = field(default_factory=list)
    milestones_total: int = 0
    estimated_completion: Optional[datetime] = None
    blockers: List[str] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class GoalStats:
    """Goal statistics."""
    total_goals: int = 0
    active_goals: int = 0
    achieved_goals: int = 0
    failed_goals: int = 0
    avg_completion_time: float = 0.0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# GOAL STORE
# =============================================================================

class GoalStore:
    """Store and index goals."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}
        self._by_status: Dict[GoalStatus, Set[str]] = defaultdict(set)
        self._by_type: Dict[GoalType, Set[str]] = defaultdict(set)
        self._by_priority: Dict[GoalPriority, Set[str]] = defaultdict(set)
        self._children: Dict[str, Set[str]] = defaultdict(set)

    def add(self, goal: Goal) -> bool:
        """Add a goal."""
        if goal.goal_id in self._goals:
            return False

        self._goals[goal.goal_id] = goal
        self._by_status[goal.status].add(goal.goal_id)
        self._by_type[goal.goal_type].add(goal.goal_id)
        self._by_priority[goal.priority].add(goal.goal_id)

        if goal.parent_id:
            self._children[goal.parent_id].add(goal.goal_id)

        return True

    def remove(self, goal_id: str) -> Optional[Goal]:
        """Remove a goal."""
        goal = self._goals.pop(goal_id, None)

        if goal:
            self._by_status[goal.status].discard(goal_id)
            self._by_type[goal.goal_type].discard(goal_id)
            self._by_priority[goal.priority].discard(goal_id)

            if goal.parent_id:
                self._children[goal.parent_id].discard(goal_id)

            for child_id in list(self._children.get(goal_id, [])):
                child = self._goals.get(child_id)
                if child:
                    child.parent_id = None
                self._children[goal_id].discard(child_id)

        return goal

    def get(self, goal_id: str) -> Optional[Goal]:
        """Get a goal."""
        return self._goals.get(goal_id)

    def update_status(self, goal_id: str, new_status: GoalStatus) -> bool:
        """Update goal status."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False

        old_status = goal.status

        self._by_status[old_status].discard(goal_id)
        self._by_status[new_status].add(goal_id)

        goal.status = new_status

        if new_status == GoalStatus.ACTIVE:
            goal.activated_at = datetime.now()
        elif new_status in [GoalStatus.ACHIEVED, GoalStatus.FAILED, GoalStatus.ABANDONED]:
            goal.completed_at = datetime.now()

        return True

    def by_status(self, status: GoalStatus) -> List[Goal]:
        """Get goals by status."""
        ids = self._by_status.get(status, set())
        return [self._goals[gid] for gid in ids if gid in self._goals]

    def by_type(self, goal_type: GoalType) -> List[Goal]:
        """Get goals by type."""
        ids = self._by_type.get(goal_type, set())
        return [self._goals[gid] for gid in ids if gid in self._goals]

    def by_priority(self, priority: GoalPriority) -> List[Goal]:
        """Get goals by priority."""
        ids = self._by_priority.get(priority, set())
        return [self._goals[gid] for gid in ids if gid in self._goals]

    def children(self, parent_id: str) -> List[Goal]:
        """Get child goals."""
        ids = self._children.get(parent_id, set())
        return [self._goals[gid] for gid in ids if gid in self._goals]

    def root_goals(self) -> List[Goal]:
        """Get root goals (no parent)."""
        return [g for g in self._goals.values() if g.parent_id is None]

    def all(self) -> List[Goal]:
        """Get all goals."""
        return list(self._goals.values())

    def count(self) -> int:
        """Count goals."""
        return len(self._goals)


# =============================================================================
# GOAL HIERARCHY
# =============================================================================

class GoalHierarchy:
    """Manage goal hierarchies."""

    def __init__(self, store: GoalStore):
        self._store = store

    def add_subgoal(
        self,
        parent_id: str,
        subgoal: Goal
    ) -> bool:
        """Add a subgoal to a parent."""
        parent = self._store.get(parent_id)
        if not parent:
            return False

        subgoal.parent_id = parent_id

        if self._store.add(subgoal):
            parent.subgoal_ids.append(subgoal.goal_id)
            return True

        return False

    def remove_subgoal(
        self,
        parent_id: str,
        subgoal_id: str
    ) -> bool:
        """Remove a subgoal from parent."""
        parent = self._store.get(parent_id)
        if not parent:
            return False

        if subgoal_id in parent.subgoal_ids:
            parent.subgoal_ids.remove(subgoal_id)

        subgoal = self._store.get(subgoal_id)
        if subgoal:
            subgoal.parent_id = None

        return True

    def get_ancestors(self, goal_id: str) -> List[Goal]:
        """Get all ancestors of a goal."""
        ancestors = []

        current = self._store.get(goal_id)

        while current and current.parent_id:
            parent = self._store.get(current.parent_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break

        return ancestors

    def get_descendants(self, goal_id: str) -> List[Goal]:
        """Get all descendants of a goal."""
        descendants = []

        goal = self._store.get(goal_id)
        if not goal:
            return descendants

        queue = list(goal.subgoal_ids)

        while queue:
            child_id = queue.pop(0)
            child = self._store.get(child_id)

            if child:
                descendants.append(child)
                queue.extend(child.subgoal_ids)

        return descendants

    def get_depth(self, goal_id: str) -> int:
        """Get depth of goal in hierarchy."""
        return len(self.get_ancestors(goal_id))

    def get_leaves(self, goal_id: str) -> List[Goal]:
        """Get leaf goals under this goal."""
        goal = self._store.get(goal_id)
        if not goal:
            return []

        if not goal.subgoal_ids:
            return [goal]

        leaves = []

        for child in self.get_descendants(goal_id):
            if not child.subgoal_ids:
                leaves.append(child)

        return leaves


# =============================================================================
# GOAL RELATIONS
# =============================================================================

class GoalRelations:
    """Manage goal relationships."""

    def __init__(self):
        self._relations: List[GoalRelationship] = []
        self._by_source: Dict[str, List[int]] = defaultdict(list)
        self._by_target: Dict[str, List[int]] = defaultdict(list)

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation: GoalRelation,
        strength: float = 1.0
    ) -> GoalRelationship:
        """Add a relationship between goals."""
        rel = GoalRelationship(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            strength=strength
        )

        idx = len(self._relations)
        self._relations.append(rel)

        self._by_source[source_id].append(idx)
        self._by_target[target_id].append(idx)

        return rel

    def get_relations_from(self, source_id: str) -> List[GoalRelationship]:
        """Get relations from a source goal."""
        indices = self._by_source.get(source_id, [])
        return [self._relations[i] for i in indices]

    def get_relations_to(self, target_id: str) -> List[GoalRelationship]:
        """Get relations to a target goal."""
        indices = self._by_target.get(target_id, [])
        return [self._relations[i] for i in indices]

    def find_conflicts(self, goal_id: str) -> List[str]:
        """Find conflicting goals."""
        conflicts = []

        for rel in self.get_relations_from(goal_id):
            if rel.relation == GoalRelation.CONFLICTS:
                conflicts.append(rel.target_id)

        for rel in self.get_relations_to(goal_id):
            if rel.relation == GoalRelation.CONFLICTS:
                conflicts.append(rel.source_id)

        return conflicts

    def find_supporters(self, goal_id: str) -> List[str]:
        """Find supporting goals."""
        supporters = []

        for rel in self.get_relations_to(goal_id):
            if rel.relation in [GoalRelation.ENABLES, GoalRelation.SUPPORTS]:
                supporters.append(rel.source_id)

        return supporters

    def find_dependents(self, goal_id: str) -> List[str]:
        """Find dependent goals."""
        dependents = []

        for rel in self.get_relations_from(goal_id):
            if rel.relation in [GoalRelation.ENABLES, GoalRelation.SUPPORTS]:
                dependents.append(rel.target_id)

        return dependents


# =============================================================================
# GOAL PRIORITIZER
# =============================================================================

class GoalPrioritizer:
    """Prioritize goals."""

    def __init__(self):
        self._weight_priority = 0.4
        self._weight_importance = 0.3
        self._weight_urgency = 0.3
        self._custom_factors: Dict[str, Callable[[Goal], float]] = {}

    def set_weights(
        self,
        priority: float = 0.4,
        importance: float = 0.3,
        urgency: float = 0.3
    ) -> None:
        """Set scoring weights."""
        total = priority + importance + urgency
        self._weight_priority = priority / total
        self._weight_importance = importance / total
        self._weight_urgency = urgency / total

    def add_factor(
        self,
        name: str,
        factor: Callable[[Goal], float]
    ) -> None:
        """Add custom scoring factor."""
        self._custom_factors[name] = factor

    def score(self, goal: Goal) -> float:
        """Calculate goal score."""
        base_score = (
            goal.priority.value * self._weight_priority +
            goal.importance * 10 * self._weight_importance +
            goal.urgency * 10 * self._weight_urgency
        )

        custom_score = 0.0
        if self._custom_factors:
            for factor in self._custom_factors.values():
                custom_score += factor(goal)
            custom_score /= len(self._custom_factors)

        if custom_score > 0:
            return (base_score + custom_score) / 2

        return base_score

    def rank(self, goals: List[Goal]) -> List[Goal]:
        """Rank goals by score."""
        scored = [(g, self.score(g)) for g in goals]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [g for g, _ in scored]

    def select_top(
        self,
        goals: List[Goal],
        count: int = 1
    ) -> List[Goal]:
        """Select top goals."""
        ranked = self.rank(goals)
        return ranked[:count]

    def urgency_factor(self) -> Callable[[Goal], float]:
        """Create deadline-based urgency factor."""
        def _factor(goal: Goal) -> float:
            if not goal.deadline:
                return 0.0

            remaining = (goal.deadline - datetime.now()).total_seconds()

            if remaining <= 0:
                return 10.0

            hours_remaining = remaining / 3600

            if hours_remaining < 1:
                return 8.0
            elif hours_remaining < 24:
                return 6.0
            elif hours_remaining < 168:
                return 4.0
            else:
                return 2.0

        return _factor


# =============================================================================
# GOAL DECOMPOSER
# =============================================================================

class GoalDecomposer:
    """Decompose goals into subgoals."""

    def __init__(self):
        self._strategies: Dict[str, Callable[[Goal], List[Goal]]] = {}

    def register_strategy(
        self,
        goal_pattern: str,
        strategy: Callable[[Goal], List[Goal]]
    ) -> None:
        """Register a decomposition strategy."""
        self._strategies[goal_pattern] = strategy

    def decompose(
        self,
        goal: Goal,
        strategy: Optional[DecompositionStrategy] = None
    ) -> List[Goal]:
        """Decompose a goal into subgoals."""
        for pattern, decomposition_fn in self._strategies.items():
            if pattern.lower() in goal.name.lower():
                subgoals = decomposition_fn(goal)

                for subgoal in subgoals:
                    subgoal.parent_id = goal.goal_id

                goal.subgoal_ids = [sg.goal_id for sg in subgoals]
                goal.decomposition = strategy or goal.decomposition

                return subgoals

        return []

    def default_decomposition(
        self,
        goal: Goal,
        num_subgoals: int = 3
    ) -> List[Goal]:
        """Default goal decomposition."""
        subgoals = []

        for i in range(num_subgoals):
            subgoal = Goal(
                name=f"{goal.name} - Step {i+1}",
                description=f"Subgoal {i+1} of {goal.name}",
                goal_type=goal.goal_type,
                priority=goal.priority,
                parent_id=goal.goal_id
            )
            subgoals.append(subgoal)

        return subgoals


# =============================================================================
# PROGRESS TRACKER
# =============================================================================

class ProgressTracker:
    """Track goal progress."""

    def __init__(self, store: GoalStore, hierarchy: GoalHierarchy):
        self._store = store
        self._hierarchy = hierarchy
        self._progress: Dict[str, GoalProgress] = {}

    def update_progress(
        self,
        goal_id: str,
        progress: float,
        milestone: Optional[str] = None
    ) -> Optional[GoalProgress]:
        """Update goal progress."""
        goal = self._store.get(goal_id)
        if not goal:
            return None

        goal.progress = min(1.0, max(0.0, progress))

        if goal_id not in self._progress:
            self._progress[goal_id] = GoalProgress(goal_id=goal_id)

        gp = self._progress[goal_id]
        gp.progress = progress
        gp.last_update = datetime.now()

        if milestone:
            gp.milestones_completed.append(milestone)

        self._propagate_progress(goal_id)

        return gp

    def add_blocker(self, goal_id: str, blocker: str) -> None:
        """Add a blocker to goal."""
        if goal_id not in self._progress:
            self._progress[goal_id] = GoalProgress(goal_id=goal_id)

        self._progress[goal_id].blockers.append(blocker)

    def remove_blocker(self, goal_id: str, blocker: str) -> None:
        """Remove a blocker from goal."""
        if goal_id in self._progress:
            if blocker in self._progress[goal_id].blockers:
                self._progress[goal_id].blockers.remove(blocker)

    def get_progress(self, goal_id: str) -> Optional[GoalProgress]:
        """Get goal progress."""
        return self._progress.get(goal_id)

    def _propagate_progress(self, goal_id: str) -> None:
        """Propagate progress to parent."""
        goal = self._store.get(goal_id)
        if not goal or not goal.parent_id:
            return

        parent = self._store.get(goal.parent_id)
        if not parent or not parent.subgoal_ids:
            return

        total_progress = 0.0

        for subgoal_id in parent.subgoal_ids:
            subgoal = self._store.get(subgoal_id)
            if subgoal:
                total_progress += subgoal.progress

        if parent.decomposition == DecompositionStrategy.AND:
            parent.progress = total_progress / len(parent.subgoal_ids)
        elif parent.decomposition == DecompositionStrategy.OR:
            parent.progress = max(
                (self._store.get(sid).progress if self._store.get(sid) else 0)
                for sid in parent.subgoal_ids
            )
        else:
            parent.progress = total_progress / len(parent.subgoal_ids)

        if parent_id := parent.parent_id:
            self._propagate_progress(parent.goal_id)


# =============================================================================
# CONFLICT DETECTOR
# =============================================================================

class ConflictDetector:
    """Detect goal conflicts."""

    def __init__(self, store: GoalStore, relations: GoalRelations):
        self._store = store
        self._relations = relations

    def detect_conflicts(
        self,
        goal_ids: Optional[List[str]] = None
    ) -> List[Tuple[str, str, str]]:
        """Detect conflicts between goals."""
        conflicts = []

        if goal_ids is None:
            goal_ids = [g.goal_id for g in self._store.all()]

        for i, gid1 in enumerate(goal_ids):
            for gid2 in goal_ids[i + 1:]:
                conflict_type = self._check_conflict(gid1, gid2)
                if conflict_type:
                    conflicts.append((gid1, gid2, conflict_type))

        return conflicts

    def _check_conflict(self, gid1: str, gid2: str) -> Optional[str]:
        """Check for conflict between two goals."""
        conflicting_ids = self._relations.find_conflicts(gid1)
        if gid2 in conflicting_ids:
            return "explicit"

        g1 = self._store.get(gid1)
        g2 = self._store.get(gid2)

        if not g1 or not g2:
            return None

        if g1.goal_type == GoalType.ACHIEVEMENT and g2.goal_type == GoalType.AVOIDANCE:
            if g1.name in g2.name or g2.name in g1.name:
                return "type_mismatch"

        return None

    def resolve_conflict(
        self,
        gid1: str,
        gid2: str
    ) -> Optional[str]:
        """Resolve conflict by suspending lower priority goal."""
        g1 = self._store.get(gid1)
        g2 = self._store.get(gid2)

        if not g1 or not g2:
            return None

        if g1.score >= g2.score:
            self._store.update_status(gid2, GoalStatus.SUSPENDED)
            return gid2
        else:
            self._store.update_status(gid1, GoalStatus.SUSPENDED)
            return gid1


# =============================================================================
# GOAL ENGINE
# =============================================================================

class GoalEngine:
    """
    Goal Engine for BAEL.

    Agent goal management and prioritization.
    """

    def __init__(self):
        self._store = GoalStore()
        self._hierarchy = GoalHierarchy(self._store)
        self._relations = GoalRelations()
        self._prioritizer = GoalPrioritizer()
        self._decomposer = GoalDecomposer()
        self._progress = ProgressTracker(self._store, self._hierarchy)
        self._conflicts = ConflictDetector(self._store, self._relations)

        self._stats = GoalStats()

    def create_goal(
        self,
        name: str,
        description: str = "",
        goal_type: GoalType = GoalType.ACHIEVEMENT,
        priority: GoalPriority = GoalPriority.MEDIUM,
        importance: float = 0.5,
        urgency: float = 0.5,
        deadline: Optional[datetime] = None,
        preconditions: Optional[List[str]] = None,
        success_criteria: Optional[List[str]] = None
    ) -> Goal:
        """Create a new goal."""
        goal = Goal(
            name=name,
            description=description,
            goal_type=goal_type,
            priority=priority,
            importance=importance,
            urgency=urgency,
            deadline=deadline,
            preconditions=preconditions or [],
            success_criteria=success_criteria or []
        )

        self._store.add(goal)

        self._update_stats()

        return goal

    def add_subgoal(
        self,
        parent_id: str,
        name: str,
        description: str = "",
        goal_type: Optional[GoalType] = None,
        priority: Optional[GoalPriority] = None
    ) -> Optional[Goal]:
        """Add a subgoal to a parent goal."""
        parent = self._store.get(parent_id)
        if not parent:
            return None

        subgoal = Goal(
            name=name,
            description=description,
            goal_type=goal_type or parent.goal_type,
            priority=priority or parent.priority
        )

        if self._hierarchy.add_subgoal(parent_id, subgoal):
            self._update_stats()
            return subgoal

        return None

    def activate_goal(self, goal_id: str) -> bool:
        """Activate a goal."""
        return self._store.update_status(goal_id, GoalStatus.ACTIVE)

    def pursue_goal(self, goal_id: str) -> bool:
        """Start pursuing a goal."""
        return self._store.update_status(goal_id, GoalStatus.PURSUING)

    def suspend_goal(self, goal_id: str) -> bool:
        """Suspend a goal."""
        return self._store.update_status(goal_id, GoalStatus.SUSPENDED)

    def achieve_goal(self, goal_id: str) -> bool:
        """Mark goal as achieved."""
        goal = self._store.get(goal_id)
        if goal:
            goal.progress = 1.0
            success = self._store.update_status(goal_id, GoalStatus.ACHIEVED)
            self._update_stats()
            return success
        return False

    def fail_goal(self, goal_id: str) -> bool:
        """Mark goal as failed."""
        success = self._store.update_status(goal_id, GoalStatus.FAILED)
        self._update_stats()
        return success

    def abandon_goal(self, goal_id: str) -> bool:
        """Abandon a goal."""
        success = self._store.update_status(goal_id, GoalStatus.ABANDONED)
        self._update_stats()
        return success

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation: GoalRelation,
        strength: float = 1.0
    ) -> Optional[GoalRelationship]:
        """Add a relationship between goals."""
        if not self._store.get(source_id) or not self._store.get(target_id):
            return None

        return self._relations.add_relation(source_id, target_id, relation, strength)

    def update_progress(
        self,
        goal_id: str,
        progress: float,
        milestone: Optional[str] = None
    ) -> Optional[GoalProgress]:
        """Update goal progress."""
        result = self._progress.update_progress(goal_id, progress, milestone)

        if progress >= 1.0:
            goal = self._store.get(goal_id)
            if goal and goal.status != GoalStatus.ACHIEVED:
                self.achieve_goal(goal_id)

        return result

    def add_blocker(self, goal_id: str, blocker: str) -> None:
        """Add a blocker to a goal."""
        self._progress.add_blocker(goal_id, blocker)

    def remove_blocker(self, goal_id: str, blocker: str) -> None:
        """Remove a blocker from a goal."""
        self._progress.remove_blocker(goal_id, blocker)

    def decompose_goal(
        self,
        goal_id: str,
        strategy: Optional[DecompositionStrategy] = None
    ) -> List[Goal]:
        """Decompose a goal into subgoals."""
        goal = self._store.get(goal_id)
        if not goal:
            return []

        subgoals = self._decomposer.decompose(goal, strategy)

        for subgoal in subgoals:
            self._store.add(subgoal)

        self._update_stats()

        return subgoals

    def register_decomposition(
        self,
        pattern: str,
        strategy: Callable[[Goal], List[Goal]]
    ) -> None:
        """Register a decomposition strategy."""
        self._decomposer.register_strategy(pattern, strategy)

    def prioritize_goals(
        self,
        goal_ids: Optional[List[str]] = None
    ) -> List[Goal]:
        """Prioritize goals."""
        if goal_ids:
            goals = [
                self._store.get(gid) for gid in goal_ids
                if self._store.get(gid)
            ]
        else:
            goals = self._store.by_status(GoalStatus.ACTIVE)

        return self._prioritizer.rank(goals)

    def select_top_goals(self, count: int = 1) -> List[Goal]:
        """Select top priority goals."""
        active = self._store.by_status(GoalStatus.ACTIVE)
        return self._prioritizer.select_top(active, count)

    def detect_conflicts(
        self,
        goal_ids: Optional[List[str]] = None
    ) -> List[Tuple[str, str, str]]:
        """Detect goal conflicts."""
        return self._conflicts.detect_conflicts(goal_ids)

    def resolve_conflict(self, gid1: str, gid2: str) -> Optional[str]:
        """Resolve a conflict between goals."""
        return self._conflicts.resolve_conflict(gid1, gid2)

    def find_conflicting(self, goal_id: str) -> List[str]:
        """Find goals conflicting with this goal."""
        return self._relations.find_conflicts(goal_id)

    def find_supporting(self, goal_id: str) -> List[str]:
        """Find goals supporting this goal."""
        return self._relations.find_supporters(goal_id)

    def find_dependent(self, goal_id: str) -> List[str]:
        """Find goals dependent on this goal."""
        return self._relations.find_dependents(goal_id)

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self._store.get(goal_id)

    def get_subgoals(self, goal_id: str) -> List[Goal]:
        """Get subgoals of a goal."""
        return self._store.children(goal_id)

    def get_ancestors(self, goal_id: str) -> List[Goal]:
        """Get ancestor goals."""
        return self._hierarchy.get_ancestors(goal_id)

    def get_descendants(self, goal_id: str) -> List[Goal]:
        """Get descendant goals."""
        return self._hierarchy.get_descendants(goal_id)

    def get_active_goals(self) -> List[Goal]:
        """Get active goals."""
        return self._store.by_status(GoalStatus.ACTIVE)

    def get_pursuing_goals(self) -> List[Goal]:
        """Get goals being pursued."""
        return self._store.by_status(GoalStatus.PURSUING)

    def get_root_goals(self) -> List[Goal]:
        """Get root goals."""
        return self._store.root_goals()

    def get_by_type(self, goal_type: GoalType) -> List[Goal]:
        """Get goals by type."""
        return self._store.by_type(goal_type)

    def get_progress(self, goal_id: str) -> Optional[GoalProgress]:
        """Get goal progress."""
        return self._progress.get_progress(goal_id)

    def set_prioritization_weights(
        self,
        priority: float = 0.4,
        importance: float = 0.3,
        urgency: float = 0.3
    ) -> None:
        """Set prioritization weights."""
        self._prioritizer.set_weights(priority, importance, urgency)

    def add_prioritization_factor(
        self,
        name: str,
        factor: Callable[[Goal], float]
    ) -> None:
        """Add custom prioritization factor."""
        self._prioritizer.add_factor(name, factor)

    def _update_stats(self) -> None:
        """Update statistics."""
        all_goals = self._store.all()

        self._stats.total_goals = len(all_goals)
        self._stats.active_goals = len(self._store.by_status(GoalStatus.ACTIVE))
        self._stats.achieved_goals = len(self._store.by_status(GoalStatus.ACHIEVED))
        self._stats.failed_goals = len(self._store.by_status(GoalStatus.FAILED))

        self._stats.by_type = {}
        for goal in all_goals:
            key = goal.goal_type.value
            self._stats.by_type[key] = self._stats.by_type.get(key, 0) + 1

        self._stats.by_status = {}
        for goal in all_goals:
            key = goal.status.value
            self._stats.by_status[key] = self._stats.by_status.get(key, 0) + 1

        self._stats.by_priority = {}
        for goal in all_goals:
            key = goal.priority.name
            self._stats.by_priority[key] = self._stats.by_priority.get(key, 0) + 1

    @property
    def stats(self) -> GoalStats:
        """Get statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_goals": self._stats.total_goals,
            "active": self._stats.active_goals,
            "achieved": self._stats.achieved_goals,
            "failed": self._stats.failed_goals,
            "root_goals": len(self._store.root_goals()),
            "by_type": self._stats.by_type,
            "by_status": self._stats.by_status,
            "by_priority": self._stats.by_priority
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Goal Engine."""
    print("=" * 70)
    print("BAEL - GOAL ENGINE DEMO")
    print("Agent Goal Management and Prioritization")
    print("=" * 70)
    print()

    engine = GoalEngine()

    # 1. Create Goals
    print("1. CREATE GOALS:")
    print("-" * 40)

    g1 = engine.create_goal(
        name="Build AI Agent System",
        description="Create a comprehensive AI agent platform",
        goal_type=GoalType.ACHIEVEMENT,
        priority=GoalPriority.CRITICAL,
        importance=0.9,
        urgency=0.7
    )

    g2 = engine.create_goal(
        name="Maintain System Stability",
        goal_type=GoalType.MAINTENANCE,
        priority=GoalPriority.HIGH,
        importance=0.8,
        urgency=0.5
    )

    g3 = engine.create_goal(
        name="Learn New Techniques",
        goal_type=GoalType.LEARNING,
        priority=GoalPriority.MEDIUM,
        importance=0.6,
        urgency=0.3
    )

    print(f"   {g1.goal_id}: {g1.name} (priority: {g1.priority.name})")
    print(f"   {g2.goal_id}: {g2.name} (priority: {g2.priority.name})")
    print(f"   {g3.goal_id}: {g3.name} (priority: {g3.priority.name})")
    print()

    # 2. Add Subgoals
    print("2. ADD SUBGOALS:")
    print("-" * 40)

    sg1 = engine.add_subgoal(
        g1.goal_id,
        name="Design Architecture",
        description="Design the system architecture"
    )

    sg2 = engine.add_subgoal(
        g1.goal_id,
        name="Implement Core Modules",
        description="Build the core functionality"
    )

    sg3 = engine.add_subgoal(
        g1.goal_id,
        name="Test and Deploy",
        description="Test and deploy the system"
    )

    print(f"   Parent: {g1.name}")
    print(f"   Subgoals: {len(g1.subgoal_ids)}")
    print(f"      - {sg1.name}")
    print(f"      - {sg2.name}")
    print(f"      - {sg3.name}")
    print()

    # 3. Goal Activation
    print("3. GOAL ACTIVATION:")
    print("-" * 40)

    engine.activate_goal(g1.goal_id)
    engine.activate_goal(g2.goal_id)
    engine.pursue_goal(sg1.goal_id)

    print(f"   {g1.name}: {g1.status.value}")
    print(f"   {g2.name}: {g2.status.value}")
    print(f"   {sg1.name}: {sg1.status.value}")
    print()

    # 4. Goal Relations
    print("4. GOAL RELATIONS:")
    print("-" * 40)

    engine.add_relation(sg1.goal_id, sg2.goal_id, GoalRelation.ENABLES)
    engine.add_relation(sg2.goal_id, sg3.goal_id, GoalRelation.ENABLES)
    engine.add_relation(g1.goal_id, g2.goal_id, GoalRelation.SUPPORTS)

    dependents = engine.find_dependent(sg1.goal_id)

    print(f"   {sg1.name} enables:")
    for dep_id in dependents:
        dep = engine.get_goal(dep_id)
        if dep:
            print(f"      - {dep.name}")
    print()

    # 5. Progress Tracking
    print("5. PROGRESS TRACKING:")
    print("-" * 40)

    engine.update_progress(sg1.goal_id, 0.5, "Design draft completed")
    engine.update_progress(sg1.goal_id, 0.8, "Review completed")
    engine.update_progress(sg1.goal_id, 1.0, "Final approval")

    progress = engine.get_progress(sg1.goal_id)

    print(f"   Goal: {sg1.name}")
    print(f"   Progress: {sg1.progress:.0%}")
    print(f"   Status: {sg1.status.value}")
    print(f"   Milestones: {progress.milestones_completed}")
    print(f"   Parent Progress: {g1.progress:.0%}")
    print()

    # 6. Goal Prioritization
    print("6. GOAL PRIORITIZATION:")
    print("-" * 40)

    engine.activate_goal(g3.goal_id)

    prioritized = engine.prioritize_goals()

    print("   Active goals by priority:")
    for i, goal in enumerate(prioritized, 1):
        print(f"      {i}. {goal.name} (score: {goal.score:.2f})")
    print()

    # 7. Conflict Detection
    print("7. CONFLICT DETECTION:")
    print("-" * 40)

    g4 = engine.create_goal(
        name="Minimize System Changes",
        goal_type=GoalType.AVOIDANCE,
        priority=GoalPriority.MEDIUM
    )

    engine.add_relation(g1.goal_id, g4.goal_id, GoalRelation.CONFLICTS)
    engine.activate_goal(g4.goal_id)

    conflicts = engine.detect_conflicts()

    print(f"   Conflicts detected: {len(conflicts)}")
    for c1, c2, ctype in conflicts:
        goal1 = engine.get_goal(c1)
        goal2 = engine.get_goal(c2)
        if goal1 and goal2:
            print(f"      {goal1.name} <-> {goal2.name} ({ctype})")
    print()

    # 8. Conflict Resolution
    print("8. CONFLICT RESOLUTION:")
    print("-" * 40)

    if conflicts:
        c1, c2, _ = conflicts[0]
        suspended = engine.resolve_conflict(c1, c2)

        if suspended:
            goal = engine.get_goal(suspended)
            if goal:
                print(f"   Suspended: {goal.name}")
                print(f"   Status: {goal.status.value}")
    print()

    # 9. Goal Hierarchy
    print("9. GOAL HIERARCHY:")
    print("-" * 40)

    descendants = engine.get_descendants(g1.goal_id)

    print(f"   Root: {g1.name}")
    print(f"   Descendants: {len(descendants)}")
    for desc in descendants:
        depth = len(engine.get_ancestors(desc.goal_id))
        indent = "   " * depth
        print(f"   {indent}- {desc.name} (depth: {depth})")
    print()

    # 10. Goal Decomposition
    print("10. GOAL DECOMPOSITION:")
    print("-" * 40)

    def research_decomposition(goal: Goal) -> List[Goal]:
        return [
            Goal(name="Literature Review", goal_type=GoalType.LEARNING),
            Goal(name="Prototype Development", goal_type=GoalType.ACHIEVEMENT),
            Goal(name="Evaluation", goal_type=GoalType.PERFORMANCE)
        ]

    engine.register_decomposition("Research", research_decomposition)

    g5 = engine.create_goal(
        name="Research New Algorithms",
        goal_type=GoalType.LEARNING
    )

    subgoals = engine.decompose_goal(g5.goal_id)

    print(f"   Goal: {g5.name}")
    print(f"   Decomposed into:")
    for sg in subgoals:
        print(f"      - {sg.name}")
    print()

    # 11. Custom Prioritization
    print("11. CUSTOM PRIORITIZATION:")
    print("-" * 40)

    engine.add_prioritization_factor(
        "deadline_urgency",
        engine._prioritizer.urgency_factor()
    )

    engine.set_prioritization_weights(
        priority=0.3,
        importance=0.4,
        urgency=0.3
    )

    top = engine.select_top_goals(count=3)

    print("   Top 3 goals with custom weights:")
    for i, goal in enumerate(top, 1):
        print(f"      {i}. {goal.name}")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Goals: {stats.total_goals}")
    print(f"   Active: {stats.active_goals}")
    print(f"   Achieved: {stats.achieved_goals}")
    print(f"   Failed: {stats.failed_goals}")
    print(f"   By Type: {stats.by_type}")
    print(f"   By Priority: {stats.by_priority}")
    print()

    # 13. Engine Summary
    print("13. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Total: {summary['total_goals']}")
    print(f"   Root Goals: {summary['root_goals']}")
    print(f"   By Status: {summary['by_status']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Goal Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
