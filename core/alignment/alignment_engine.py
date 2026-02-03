#!/usr/bin/env python3
"""
BAEL - Alignment Engine
Goal alignment and value alignment for agents.

Features:
- Value specification
- Goal alignment checking
- Preference learning
- Alignment monitoring
- Value drift detection
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

class ValueType(Enum):
    """Types of values."""
    ETHICAL = "ethical"
    OPERATIONAL = "operational"
    USER_PREFERENCE = "user_preference"
    SAFETY = "safety"
    PERFORMANCE = "performance"


class AlignmentLevel(Enum):
    """Alignment levels."""
    FULL = 1.0
    HIGH = 0.8
    MODERATE = 0.6
    LOW = 0.4
    MISALIGNED = 0.2


class GoalPriority(Enum):
    """Goal priorities."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1


class ConflictType(Enum):
    """Types of value conflicts."""
    GOAL_GOAL = "goal_goal"
    VALUE_VALUE = "value_value"
    GOAL_VALUE = "goal_value"
    RESOURCE = "resource"


class AlignmentState(Enum):
    """Alignment states."""
    ALIGNED = "aligned"
    DRIFTING = "drifting"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class PreferenceSource(Enum):
    """Sources of preferences."""
    USER = "user"
    SYSTEM = "system"
    LEARNED = "learned"
    DEFAULT = "default"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Value:
    """A value specification."""
    value_id: str = ""
    name: str = ""
    description: str = ""
    value_type: ValueType = ValueType.OPERATIONAL
    importance: float = 0.5
    constraints: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.value_id:
            self.value_id = str(uuid.uuid4())[:8]


@dataclass
class Goal:
    """An alignment goal."""
    goal_id: str = ""
    name: str = ""
    description: str = ""
    priority: GoalPriority = GoalPriority.MEDIUM
    target: float = 1.0
    current: float = 0.0
    related_values: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.goal_id:
            self.goal_id = str(uuid.uuid4())[:8]


@dataclass
class Preference:
    """A learned preference."""
    preference_id: str = ""
    key: str = ""
    value: Any = None
    confidence: float = 0.5
    source: PreferenceSource = PreferenceSource.DEFAULT
    observations: int = 1
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.preference_id:
            self.preference_id = str(uuid.uuid4())[:8]


@dataclass
class AlignmentCheck:
    """Result of alignment check."""
    check_id: str = ""
    subject: str = ""
    overall_alignment: float = 0.0
    level: AlignmentLevel = AlignmentLevel.MODERATE
    value_scores: Dict[str, float] = field(default_factory=dict)
    goal_scores: Dict[str, float] = field(default_factory=dict)
    conflicts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.check_id:
            self.check_id = str(uuid.uuid4())[:8]


@dataclass
class Conflict:
    """A detected conflict."""
    conflict_id: str = ""
    conflict_type: ConflictType = ConflictType.GOAL_GOAL
    parties: List[str] = field(default_factory=list)
    severity: float = 0.5
    description: str = ""
    resolution: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.conflict_id:
            self.conflict_id = str(uuid.uuid4())[:8]


@dataclass
class AlignmentConfig:
    """Alignment configuration."""
    alignment_threshold: float = 0.7
    drift_threshold: float = 0.1
    conflict_threshold: float = 0.3


# =============================================================================
# VALUE MANAGER
# =============================================================================

class ValueManager:
    """Manage values."""

    def __init__(self):
        self._values: Dict[str, Value] = {}
        self._value_weights: Dict[str, float] = {}

    def add_value(
        self,
        name: str,
        description: str = "",
        value_type: ValueType = ValueType.OPERATIONAL,
        importance: float = 0.5,
        constraints: Optional[List[str]] = None
    ) -> Value:
        """Add a value."""
        value = Value(
            name=name,
            description=description,
            value_type=value_type,
            importance=importance,
            constraints=constraints or []
        )

        self._values[value.value_id] = value
        self._value_weights[value.value_id] = importance

        return value

    def get_value(self, value_id: str) -> Optional[Value]:
        """Get a value by ID."""
        return self._values.get(value_id)

    def get_value_by_name(self, name: str) -> Optional[Value]:
        """Get a value by name."""
        for value in self._values.values():
            if value.name == name:
                return value
        return None

    def remove_value(self, value_id: str) -> bool:
        """Remove a value."""
        if value_id in self._values:
            del self._values[value_id]
            self._value_weights.pop(value_id, None)
            return True
        return False

    def get_all_values(self) -> List[Value]:
        """Get all values."""
        return list(self._values.values())

    def get_values_by_type(self, value_type: ValueType) -> List[Value]:
        """Get values by type."""
        return [v for v in self._values.values() if v.value_type == value_type]

    def update_importance(
        self,
        value_id: str,
        importance: float
    ) -> bool:
        """Update value importance."""
        if value_id in self._values:
            self._values[value_id].importance = importance
            self._value_weights[value_id] = importance
            return True
        return False

    def get_weighted_values(self) -> List[Tuple[Value, float]]:
        """Get values with weights."""
        return [
            (v, self._value_weights.get(v.value_id, 0.5))
            for v in self._values.values()
        ]

    def compute_value_score(
        self,
        action: Dict[str, Any],
        value_id: str
    ) -> float:
        """Compute how well an action aligns with a value."""
        value = self._values.get(value_id)
        if not value:
            return 0.5

        score = 0.5

        for constraint in value.constraints:
            if constraint in action:
                if action[constraint]:
                    score += 0.1
                else:
                    score -= 0.2

        if value.name.lower() in str(action).lower():
            score += 0.1

        return max(0.0, min(1.0, score))


# =============================================================================
# GOAL MANAGER
# =============================================================================

class GoalManager:
    """Manage alignment goals."""

    def __init__(self):
        self._goals: Dict[str, Goal] = {}

    def add_goal(
        self,
        name: str,
        description: str = "",
        priority: GoalPriority = GoalPriority.MEDIUM,
        target: float = 1.0,
        related_values: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None
    ) -> Goal:
        """Add an alignment goal."""
        goal = Goal(
            name=name,
            description=description,
            priority=priority,
            target=target,
            related_values=related_values or [],
            constraints=constraints or []
        )

        self._goals[goal.goal_id] = goal

        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)

    def get_goal_by_name(self, name: str) -> Optional[Goal]:
        """Get a goal by name."""
        for goal in self._goals.values():
            if goal.name == name:
                return goal
        return None

    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal."""
        if goal_id in self._goals:
            del self._goals[goal_id]
            return True
        return False

    def get_all_goals(self) -> List[Goal]:
        """Get all goals."""
        return list(self._goals.values())

    def get_goals_by_priority(
        self,
        priority: GoalPriority
    ) -> List[Goal]:
        """Get goals by priority."""
        return [g for g in self._goals.values() if g.priority == priority]

    def update_progress(
        self,
        goal_id: str,
        current: float
    ) -> Optional[Goal]:
        """Update goal progress."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.current = max(0.0, min(goal.target, current))
            return goal
        return None

    def get_alignment_score(self, goal_id: str) -> float:
        """Get goal alignment score."""
        goal = self._goals.get(goal_id)
        if not goal or goal.target == 0:
            return 0.0

        return goal.current / goal.target

    def get_prioritized_goals(self) -> List[Goal]:
        """Get goals ordered by priority."""
        return sorted(
            self._goals.values(),
            key=lambda g: g.priority.value,
            reverse=True
        )


# =============================================================================
# PREFERENCE LEARNER
# =============================================================================

class PreferenceLearner:
    """Learn preferences from observations."""

    def __init__(self):
        self._preferences: Dict[str, Preference] = {}
        self._observations: List[Dict[str, Any]] = []

    def observe(
        self,
        key: str,
        value: Any,
        weight: float = 1.0
    ) -> Preference:
        """Observe a preference signal."""
        self._observations.append({
            "key": key,
            "value": value,
            "weight": weight,
            "timestamp": datetime.now()
        })

        if key in self._preferences:
            pref = self._preferences[key]
            pref = self._update_preference(pref, value, weight)
        else:
            pref = Preference(
                key=key,
                value=value,
                confidence=0.3,
                source=PreferenceSource.LEARNED,
                observations=1
            )
            self._preferences[key] = pref

        return pref

    def _update_preference(
        self,
        pref: Preference,
        value: Any,
        weight: float
    ) -> Preference:
        """Update preference with new observation."""
        pref.observations += 1

        if isinstance(value, (int, float)) and isinstance(pref.value, (int, float)):
            alpha = weight / (pref.observations + weight)
            pref.value = (1 - alpha) * pref.value + alpha * value
        elif value == pref.value:
            pref.confidence = min(1.0, pref.confidence + 0.1 * weight)
        else:
            pref.confidence = max(0.1, pref.confidence - 0.05 * weight)
            if pref.confidence < 0.3:
                pref.value = value
                pref.confidence = 0.3

        pref.last_updated = datetime.now()
        pref.source = PreferenceSource.LEARNED

        self._preferences[pref.key] = pref

        return pref

    def set_preference(
        self,
        key: str,
        value: Any,
        source: PreferenceSource = PreferenceSource.USER
    ) -> Preference:
        """Set a preference directly."""
        pref = Preference(
            key=key,
            value=value,
            confidence=1.0 if source == PreferenceSource.USER else 0.5,
            source=source
        )

        self._preferences[key] = pref

        return pref

    def get_preference(self, key: str) -> Optional[Preference]:
        """Get a preference by key."""
        return self._preferences.get(key)

    def get_all_preferences(self) -> List[Preference]:
        """Get all preferences."""
        return list(self._preferences.values())

    def get_confident_preferences(
        self,
        threshold: float = 0.7
    ) -> List[Preference]:
        """Get preferences above confidence threshold."""
        return [
            p for p in self._preferences.values()
            if p.confidence >= threshold
        ]

    def infer_preference(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Infer preference value."""
        pref = self._preferences.get(key)

        if pref and pref.confidence >= 0.5:
            return pref.value

        return default


# =============================================================================
# ALIGNMENT CHECKER
# =============================================================================

class AlignmentChecker:
    """Check alignment of actions and goals."""

    def __init__(
        self,
        value_manager: ValueManager,
        goal_manager: GoalManager,
        threshold: float = 0.7
    ):
        self._value_manager = value_manager
        self._goal_manager = goal_manager
        self._threshold = threshold
        self._checks: List[AlignmentCheck] = []

    def check_action(
        self,
        action: Dict[str, Any]
    ) -> AlignmentCheck:
        """Check alignment of an action."""
        value_scores = {}
        goal_scores = {}
        conflicts = []

        for value in self._value_manager.get_all_values():
            score = self._value_manager.compute_value_score(action, value.value_id)
            value_scores[value.value_id] = score

            if score < 0.3:
                conflicts.append(f"Low alignment with value: {value.name}")

        for goal in self._goal_manager.get_all_goals():
            score = self._compute_goal_alignment(action, goal)
            goal_scores[goal.goal_id] = score

            if score < 0.3:
                conflicts.append(f"Low alignment with goal: {goal.name}")

        all_scores = list(value_scores.values()) + list(goal_scores.values())
        overall = sum(all_scores) / len(all_scores) if all_scores else 0.5

        level = self._score_to_level(overall)

        check = AlignmentCheck(
            subject="action",
            overall_alignment=overall,
            level=level,
            value_scores=value_scores,
            goal_scores=goal_scores,
            conflicts=conflicts
        )

        self._checks.append(check)

        return check

    def check_goal_alignment(
        self,
        goal_id: str
    ) -> AlignmentCheck:
        """Check alignment of a goal with values."""
        goal = self._goal_manager.get_goal(goal_id)

        if not goal:
            return AlignmentCheck(
                subject=goal_id,
                overall_alignment=0.0,
                level=AlignmentLevel.MISALIGNED
            )

        value_scores = {}

        for value_id in goal.related_values:
            value = self._value_manager.get_value(value_id)
            if value:
                value_scores[value_id] = value.importance

        if value_scores:
            overall = sum(value_scores.values()) / len(value_scores)
        else:
            overall = 0.5

        overall *= self._goal_manager.get_alignment_score(goal_id)

        return AlignmentCheck(
            subject=goal_id,
            overall_alignment=overall,
            level=self._score_to_level(overall),
            value_scores=value_scores,
            goal_scores={goal_id: overall}
        )

    def _compute_goal_alignment(
        self,
        action: Dict[str, Any],
        goal: Goal
    ) -> float:
        """Compute action-goal alignment."""
        score = 0.5

        for constraint in goal.constraints:
            if constraint in action:
                if action[constraint]:
                    score += 0.15
                else:
                    score -= 0.2

        if goal.name.lower() in str(action).lower():
            score += 0.1

        return max(0.0, min(1.0, score))

    def _score_to_level(self, score: float) -> AlignmentLevel:
        """Convert score to alignment level."""
        if score >= 0.9:
            return AlignmentLevel.FULL
        elif score >= 0.7:
            return AlignmentLevel.HIGH
        elif score >= 0.5:
            return AlignmentLevel.MODERATE
        elif score >= 0.3:
            return AlignmentLevel.LOW
        else:
            return AlignmentLevel.MISALIGNED

    def is_aligned(self, check: AlignmentCheck) -> bool:
        """Check if alignment is sufficient."""
        return check.overall_alignment >= self._threshold

    def get_recent_checks(
        self,
        limit: int = 20
    ) -> List[AlignmentCheck]:
        """Get recent alignment checks."""
        return self._checks[-limit:]


# =============================================================================
# CONFLICT DETECTOR
# =============================================================================

class ConflictDetector:
    """Detect conflicts between goals and values."""

    def __init__(
        self,
        value_manager: ValueManager,
        goal_manager: GoalManager
    ):
        self._value_manager = value_manager
        self._goal_manager = goal_manager
        self._conflicts: List[Conflict] = []

    def detect_goal_conflicts(self) -> List[Conflict]:
        """Detect conflicts between goals."""
        conflicts = []

        goals = self._goal_manager.get_all_goals()

        for i, goal_a in enumerate(goals):
            for goal_b in goals[i + 1:]:
                if self._goals_conflict(goal_a, goal_b):
                    conflict = Conflict(
                        conflict_type=ConflictType.GOAL_GOAL,
                        parties=[goal_a.goal_id, goal_b.goal_id],
                        severity=0.5,
                        description=f"Goal conflict: {goal_a.name} vs {goal_b.name}"
                    )
                    conflicts.append(conflict)
                    self._conflicts.append(conflict)

        return conflicts

    def detect_value_conflicts(self) -> List[Conflict]:
        """Detect conflicts between values."""
        conflicts = []

        values = self._value_manager.get_all_values()

        for i, value_a in enumerate(values):
            for value_b in values[i + 1:]:
                if self._values_conflict(value_a, value_b):
                    conflict = Conflict(
                        conflict_type=ConflictType.VALUE_VALUE,
                        parties=[value_a.value_id, value_b.value_id],
                        severity=0.6,
                        description=f"Value conflict: {value_a.name} vs {value_b.name}"
                    )
                    conflicts.append(conflict)
                    self._conflicts.append(conflict)

        return conflicts

    def detect_goal_value_conflicts(self) -> List[Conflict]:
        """Detect conflicts between goals and values."""
        conflicts = []

        for goal in self._goal_manager.get_all_goals():
            for value in self._value_manager.get_all_values():
                if self._goal_value_conflict(goal, value):
                    conflict = Conflict(
                        conflict_type=ConflictType.GOAL_VALUE,
                        parties=[goal.goal_id, value.value_id],
                        severity=0.7,
                        description=f"Goal-value conflict: {goal.name} vs {value.name}"
                    )
                    conflicts.append(conflict)
                    self._conflicts.append(conflict)

        return conflicts

    def _goals_conflict(self, goal_a: Goal, goal_b: Goal) -> bool:
        """Check if two goals conflict."""
        shared_constraints = set(goal_a.constraints) & set(goal_b.constraints)

        return len(shared_constraints) > 0 and goal_a.priority == goal_b.priority

    def _values_conflict(self, value_a: Value, value_b: Value) -> bool:
        """Check if two values conflict."""
        if value_a.value_type != value_b.value_type:
            return False

        return bool(set(value_a.constraints) & set(value_b.constraints))

    def _goal_value_conflict(self, goal: Goal, value: Value) -> bool:
        """Check if goal conflicts with value."""
        if value.value_id in goal.related_values:
            return False

        return bool(set(goal.constraints) & set(value.constraints))

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str
    ) -> bool:
        """Record conflict resolution."""
        for conflict in self._conflicts:
            if conflict.conflict_id == conflict_id:
                conflict.resolution = resolution
                return True
        return False

    def get_unresolved_conflicts(self) -> List[Conflict]:
        """Get unresolved conflicts."""
        return [c for c in self._conflicts if c.resolution is None]

    def get_all_conflicts(self) -> List[Conflict]:
        """Get all conflicts."""
        return self._conflicts[:]


# =============================================================================
# DRIFT DETECTOR
# =============================================================================

class DriftDetector:
    """Detect value and alignment drift."""

    def __init__(self, threshold: float = 0.1):
        self._threshold = threshold
        self._history: List[Tuple[datetime, Dict[str, float]]] = []

    def record_alignment(
        self,
        alignment_scores: Dict[str, float]
    ) -> None:
        """Record alignment scores."""
        self._history.append((datetime.now(), alignment_scores.copy()))

        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    def detect_drift(
        self,
        window: int = 10
    ) -> Dict[str, float]:
        """Detect drift in alignment scores."""
        if len(self._history) < window * 2:
            return {}

        recent = self._history[-window:]
        older = self._history[-(window * 2):-window]

        drifts = {}

        recent_means = self._compute_means(recent)
        older_means = self._compute_means(older)

        for key in recent_means:
            if key in older_means:
                drift = recent_means[key] - older_means[key]
                if abs(drift) >= self._threshold:
                    drifts[key] = drift

        return drifts

    def _compute_means(
        self,
        history: List[Tuple[datetime, Dict[str, float]]]
    ) -> Dict[str, float]:
        """Compute mean scores from history."""
        sums: Dict[str, float] = defaultdict(float)
        counts: Dict[str, int] = defaultdict(int)

        for _, scores in history:
            for key, value in scores.items():
                sums[key] += value
                counts[key] += 1

        return {k: sums[k] / counts[k] for k in sums}

    def get_trend(
        self,
        key: str,
        window: int = 20
    ) -> Optional[float]:
        """Get trend for a specific key."""
        relevant = [
            scores.get(key)
            for _, scores in self._history[-window:]
            if key in scores
        ]

        if len(relevant) < 2:
            return None

        n = len(relevant)
        x_mean = (n - 1) / 2
        y_mean = sum(relevant) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(relevant))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def is_drifting(self) -> bool:
        """Check if any significant drift detected."""
        drifts = self.detect_drift()
        return len(drifts) > 0


# =============================================================================
# ALIGNMENT ENGINE
# =============================================================================

class AlignmentEngine:
    """
    Alignment Engine for BAEL.

    Goal alignment and value alignment.
    """

    def __init__(self, config: Optional[AlignmentConfig] = None):
        self._config = config or AlignmentConfig()

        self._value_manager = ValueManager()
        self._goal_manager = GoalManager()
        self._preference_learner = PreferenceLearner()
        self._alignment_checker = AlignmentChecker(
            self._value_manager,
            self._goal_manager,
            threshold=self._config.alignment_threshold
        )
        self._conflict_detector = ConflictDetector(
            self._value_manager,
            self._goal_manager
        )
        self._drift_detector = DriftDetector(
            threshold=self._config.drift_threshold
        )

        self._state = AlignmentState.UNKNOWN

    # ----- Value Operations -----

    def add_value(
        self,
        name: str,
        description: str = "",
        value_type: ValueType = ValueType.OPERATIONAL,
        importance: float = 0.5,
        constraints: Optional[List[str]] = None
    ) -> Value:
        """Add a value."""
        return self._value_manager.add_value(
            name=name,
            description=description,
            value_type=value_type,
            importance=importance,
            constraints=constraints
        )

    def get_value(self, name: str) -> Optional[Value]:
        """Get a value by name."""
        return self._value_manager.get_value_by_name(name)

    def get_all_values(self) -> List[Value]:
        """Get all values."""
        return self._value_manager.get_all_values()

    def update_value_importance(
        self,
        name: str,
        importance: float
    ) -> bool:
        """Update value importance."""
        value = self._value_manager.get_value_by_name(name)
        if value:
            return self._value_manager.update_importance(value.value_id, importance)
        return False

    # ----- Goal Operations -----

    def add_goal(
        self,
        name: str,
        description: str = "",
        priority: GoalPriority = GoalPriority.MEDIUM,
        target: float = 1.0,
        related_values: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None
    ) -> Goal:
        """Add an alignment goal."""
        return self._goal_manager.add_goal(
            name=name,
            description=description,
            priority=priority,
            target=target,
            related_values=related_values,
            constraints=constraints
        )

    def get_goal(self, name: str) -> Optional[Goal]:
        """Get a goal by name."""
        return self._goal_manager.get_goal_by_name(name)

    def get_all_goals(self) -> List[Goal]:
        """Get all goals."""
        return self._goal_manager.get_all_goals()

    def update_goal_progress(
        self,
        name: str,
        current: float
    ) -> Optional[Goal]:
        """Update goal progress."""
        goal = self._goal_manager.get_goal_by_name(name)
        if goal:
            return self._goal_manager.update_progress(goal.goal_id, current)
        return None

    # ----- Preference Operations -----

    def observe_preference(
        self,
        key: str,
        value: Any,
        weight: float = 1.0
    ) -> Preference:
        """Observe a preference."""
        return self._preference_learner.observe(key, value, weight)

    def set_preference(
        self,
        key: str,
        value: Any
    ) -> Preference:
        """Set a preference directly."""
        return self._preference_learner.set_preference(
            key, value, PreferenceSource.USER
        )

    def get_preference(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Get inferred preference."""
        return self._preference_learner.infer_preference(key, default)

    def get_all_preferences(self) -> List[Preference]:
        """Get all preferences."""
        return self._preference_learner.get_all_preferences()

    # ----- Alignment Operations -----

    def check_alignment(
        self,
        action: Dict[str, Any]
    ) -> AlignmentCheck:
        """Check action alignment."""
        check = self._alignment_checker.check_action(action)

        scores = {**check.value_scores, **check.goal_scores}
        self._drift_detector.record_alignment(scores)

        self._update_state(check)

        return check

    def is_aligned(self, action: Dict[str, Any]) -> bool:
        """Check if action is aligned."""
        check = self.check_alignment(action)
        return self._alignment_checker.is_aligned(check)

    def check_goal_alignment(self, goal_name: str) -> AlignmentCheck:
        """Check goal alignment with values."""
        goal = self._goal_manager.get_goal_by_name(goal_name)
        if not goal:
            return AlignmentCheck(subject=goal_name, overall_alignment=0.0)
        return self._alignment_checker.check_goal_alignment(goal.goal_id)

    # ----- Conflict Operations -----

    def detect_conflicts(self) -> List[Conflict]:
        """Detect all conflicts."""
        conflicts = []
        conflicts.extend(self._conflict_detector.detect_goal_conflicts())
        conflicts.extend(self._conflict_detector.detect_value_conflicts())
        conflicts.extend(self._conflict_detector.detect_goal_value_conflicts())

        if conflicts:
            self._state = AlignmentState.CONFLICT

        return conflicts

    def get_unresolved_conflicts(self) -> List[Conflict]:
        """Get unresolved conflicts."""
        return self._conflict_detector.get_unresolved_conflicts()

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str
    ) -> bool:
        """Resolve a conflict."""
        return self._conflict_detector.resolve_conflict(conflict_id, resolution)

    # ----- Drift Operations -----

    def check_drift(self) -> Dict[str, float]:
        """Check for alignment drift."""
        drifts = self._drift_detector.detect_drift()

        if drifts:
            self._state = AlignmentState.DRIFTING

        return drifts

    def is_drifting(self) -> bool:
        """Check if alignment is drifting."""
        return self._drift_detector.is_drifting()

    def get_trend(self, key: str) -> Optional[float]:
        """Get trend for a key."""
        return self._drift_detector.get_trend(key)

    # ----- State Operations -----

    def get_state(self) -> AlignmentState:
        """Get current alignment state."""
        return self._state

    def _update_state(self, check: AlignmentCheck) -> None:
        """Update state based on check."""
        if check.conflicts:
            self._state = AlignmentState.CONFLICT
        elif check.overall_alignment >= self._config.alignment_threshold:
            if self._state != AlignmentState.DRIFTING:
                self._state = AlignmentState.ALIGNED
        elif self._drift_detector.is_drifting():
            self._state = AlignmentState.DRIFTING
        else:
            self._state = AlignmentState.UNKNOWN

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "state": self._state.value,
            "values": len(self.get_all_values()),
            "goals": len(self.get_all_goals()),
            "preferences": len(self.get_all_preferences()),
            "unresolved_conflicts": len(self.get_unresolved_conflicts()),
            "is_drifting": self.is_drifting()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Alignment Engine."""
    print("=" * 70)
    print("BAEL - ALIGNMENT ENGINE DEMO")
    print("Goal Alignment and Value Alignment")
    print("=" * 70)
    print()

    engine = AlignmentEngine()

    # 1. Add Values
    print("1. ADD VALUES:")
    print("-" * 40)

    v1 = engine.add_value(
        "safety_first",
        "Prioritize user safety",
        ValueType.SAFETY,
        importance=0.9,
        constraints=["safe_mode", "verified"]
    )
    print(f"   Added: {v1.name} (importance={v1.importance})")

    v2 = engine.add_value(
        "user_privacy",
        "Protect user data",
        ValueType.ETHICAL,
        importance=0.85,
        constraints=["encrypted", "consent"]
    )
    print(f"   Added: {v2.name} (importance={v2.importance})")

    v3 = engine.add_value(
        "efficiency",
        "Optimize performance",
        ValueType.PERFORMANCE,
        importance=0.7,
        constraints=["fast", "cached"]
    )
    print(f"   Added: {v3.name} (importance={v3.importance})")
    print()

    # 2. Add Goals
    print("2. ADD GOALS:")
    print("-" * 40)

    g1 = engine.add_goal(
        "complete_tasks",
        "Complete user tasks reliably",
        GoalPriority.HIGH,
        target=1.0,
        related_values=[v1.value_id],
        constraints=["reliable", "accurate"]
    )
    print(f"   Added: {g1.name} (priority={g1.priority.name})")

    g2 = engine.add_goal(
        "minimize_errors",
        "Reduce error rate",
        GoalPriority.MEDIUM,
        target=0.05,
        related_values=[v1.value_id, v3.value_id],
        constraints=["validated"]
    )
    print(f"   Added: {g2.name} (priority={g2.priority.name})")
    print()

    # 3. Set Preferences
    print("3. SET PREFERENCES:")
    print("-" * 40)

    p1 = engine.set_preference("response_format", "json")
    print(f"   {p1.key} = {p1.value} (confidence={p1.confidence})")

    p2 = engine.observe_preference("verbosity", 0.7)
    print(f"   {p2.key} = {p2.value} (confidence={p2.confidence:.2f})")

    for _ in range(5):
        engine.observe_preference("verbosity", 0.7)

    p2_updated = engine._preference_learner.get_preference("verbosity")
    print(f"   {p2_updated.key} after reinforcement: confidence={p2_updated.confidence:.2f}")
    print()

    # 4. Check Action Alignment
    print("4. CHECK ACTION ALIGNMENT:")
    print("-" * 40)

    action1 = {
        "type": "process_data",
        "safe_mode": True,
        "encrypted": True,
        "fast": True
    }

    check1 = engine.check_alignment(action1)
    print(f"   Action: process_data (safe, encrypted, fast)")
    print(f"   Alignment: {check1.overall_alignment:.2f} ({check1.level.name})")
    print(f"   Aligned: {engine._alignment_checker.is_aligned(check1)}")
    print()

    action2 = {
        "type": "share_data",
        "safe_mode": False,
        "encrypted": False
    }

    check2 = engine.check_alignment(action2)
    print(f"   Action: share_data (unsafe, unencrypted)")
    print(f"   Alignment: {check2.overall_alignment:.2f} ({check2.level.name})")
    print(f"   Conflicts: {len(check2.conflicts)}")
    print()

    # 5. Update Goal Progress
    print("5. UPDATE GOAL PROGRESS:")
    print("-" * 40)

    engine.update_goal_progress("complete_tasks", 0.8)
    engine.update_goal_progress("minimize_errors", 0.03)

    for goal in engine.get_all_goals():
        score = engine._goal_manager.get_alignment_score(goal.goal_id)
        print(f"   {goal.name}: {goal.current:.2f}/{goal.target:.2f} ({score:.0%})")
    print()

    # 6. Check Goal Alignment
    print("6. CHECK GOAL ALIGNMENT:")
    print("-" * 40)

    goal_check = engine.check_goal_alignment("complete_tasks")
    print(f"   Goal: complete_tasks")
    print(f"   Alignment: {goal_check.overall_alignment:.2f}")
    print()

    # 7. Detect Conflicts
    print("7. DETECT CONFLICTS:")
    print("-" * 40)

    engine.add_value(
        "maximum_speed",
        "Prioritize speed",
        ValueType.PERFORMANCE,
        importance=0.8,
        constraints=["safe_mode"]
    )

    conflicts = engine.detect_conflicts()
    print(f"   Detected: {len(conflicts)} conflicts")

    for conflict in conflicts[:3]:
        print(f"     [{conflict.conflict_type.value}] {conflict.description}")
    print()

    # 8. Resolve Conflict
    print("8. RESOLVE CONFLICT:")
    print("-" * 40)

    if conflicts:
        engine.resolve_conflict(
            conflicts[0].conflict_id,
            "Safety takes priority over speed"
        )
        print(f"   Resolved: {conflicts[0].description}")

    unresolved = engine.get_unresolved_conflicts()
    print(f"   Remaining unresolved: {len(unresolved)}")
    print()

    # 9. Drift Detection
    print("9. DRIFT DETECTION:")
    print("-" * 40)

    for i in range(15):
        action = {"type": "test", "safe_mode": True, "fast": True}
        engine.check_alignment(action)

    for i in range(15):
        action = {"type": "test", "safe_mode": False, "fast": False}
        engine.check_alignment(action)

    drifts = engine.check_drift()
    print(f"   Detected drifts: {len(drifts)}")

    for key, drift in list(drifts.items())[:3]:
        print(f"     {key}: {drift:+.3f}")

    print(f"   Is drifting: {engine.is_drifting()}")
    print()

    # 10. Get Inferred Preference
    print("10. INFERRED PREFERENCES:")
    print("-" * 40)

    format_pref = engine.get_preference("response_format", "text")
    print(f"   response_format: {format_pref}")

    verbosity = engine.get_preference("verbosity", 0.5)
    print(f"   verbosity: {verbosity}")

    unknown = engine.get_preference("unknown_key", "default")
    print(f"   unknown_key: {unknown}")
    print()

    # 11. State
    print("11. ALIGNMENT STATE:")
    print("-" * 40)

    print(f"   Current State: {engine.get_state().value}")
    print()

    # 12. Summary
    print("12. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Alignment Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
