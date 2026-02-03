#!/usr/bin/env python3
"""
BAEL - Safety Engine
Safety constraints and guardrails for agents.

Features:
- Safety constraints
- Action filtering
- Risk assessment
- Boundary enforcement
- Safety monitoring
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

class RiskLevel(Enum):
    """Risk levels."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ConstraintType(Enum):
    """Types of safety constraints."""
    HARD = "hard"
    SOFT = "soft"
    PREFERENCE = "preference"


class ActionCategory(Enum):
    """Categories of actions."""
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    FORBIDDEN = "forbidden"


class ViolationType(Enum):
    """Types of violations."""
    BOUNDARY = "boundary"
    RESOURCE = "resource"
    PERMISSION = "permission"
    RATE = "rate"
    CONTENT = "content"


class SafetyState(Enum):
    """Safety states."""
    NORMAL = "normal"
    ALERT = "alert"
    WARNING = "warning"
    EMERGENCY = "emergency"
    LOCKDOWN = "lockdown"


class BoundaryType(Enum):
    """Types of boundaries."""
    RESOURCE = "resource"
    ACTION = "action"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    SEMANTIC = "semantic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Constraint:
    """A safety constraint."""
    constraint_id: str = ""
    name: str = ""
    description: str = ""
    constraint_type: ConstraintType = ConstraintType.HARD
    condition: str = ""
    active: bool = True
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.constraint_id:
            self.constraint_id = str(uuid.uuid4())[:8]


@dataclass
class ActionCheck:
    """Result of checking an action."""
    action_id: str = ""
    action_type: str = ""
    category: ActionCategory = ActionCategory.SAFE
    risk_level: RiskLevel = RiskLevel.NONE
    allowed: bool = True
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.action_id:
            self.action_id = str(uuid.uuid4())[:8]


@dataclass
class Violation:
    """A safety violation."""
    violation_id: str = ""
    violation_type: ViolationType = ViolationType.BOUNDARY
    constraint_id: str = ""
    severity: RiskLevel = RiskLevel.LOW
    description: str = ""
    action_taken: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.violation_id:
            self.violation_id = str(uuid.uuid4())[:8]


@dataclass
class Boundary:
    """A safety boundary."""
    boundary_id: str = ""
    name: str = ""
    boundary_type: BoundaryType = BoundaryType.RESOURCE
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    current_value: float = 0.0
    enforcement: ConstraintType = ConstraintType.HARD

    def __post_init__(self):
        if not self.boundary_id:
            self.boundary_id = str(uuid.uuid4())[:8]


@dataclass
class RiskAssessment:
    """A risk assessment."""
    assessment_id: str = ""
    subject: str = ""
    overall_risk: RiskLevel = RiskLevel.NONE
    risk_factors: Dict[str, float] = field(default_factory=dict)
    mitigations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.assessment_id:
            self.assessment_id = str(uuid.uuid4())[:8]


@dataclass
class SafetyConfig:
    """Safety configuration."""
    max_violations: int = 10
    lockdown_threshold: int = 5
    risk_threshold: float = 0.7
    rate_limit_window: int = 60


# =============================================================================
# CONSTRAINT MANAGER
# =============================================================================

class ConstraintManager:
    """Manage safety constraints."""

    def __init__(self):
        self._constraints: Dict[str, Constraint] = {}
        self._constraint_checks: Dict[str, Callable[[Dict], bool]] = {}

    def add_constraint(
        self,
        name: str,
        description: str = "",
        constraint_type: ConstraintType = ConstraintType.HARD,
        condition: str = "",
        priority: int = 5,
        check_func: Optional[Callable[[Dict], bool]] = None
    ) -> Constraint:
        """Add a safety constraint."""
        constraint = Constraint(
            name=name,
            description=description,
            constraint_type=constraint_type,
            condition=condition,
            priority=priority
        )

        self._constraints[constraint.constraint_id] = constraint

        if check_func:
            self._constraint_checks[constraint.constraint_id] = check_func

        return constraint

    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a constraint."""
        if constraint_id in self._constraints:
            del self._constraints[constraint_id]
            self._constraint_checks.pop(constraint_id, None)
            return True
        return False

    def get_constraint(self, constraint_id: str) -> Optional[Constraint]:
        """Get a constraint by ID."""
        return self._constraints.get(constraint_id)

    def get_active_constraints(self) -> List[Constraint]:
        """Get all active constraints."""
        return [c for c in self._constraints.values() if c.active]

    def enable_constraint(self, constraint_id: str) -> bool:
        """Enable a constraint."""
        if constraint_id in self._constraints:
            self._constraints[constraint_id].active = True
            return True
        return False

    def disable_constraint(self, constraint_id: str) -> bool:
        """Disable a constraint."""
        if constraint_id in self._constraints:
            self._constraints[constraint_id].active = False
            return True
        return False

    def check_constraints(
        self,
        context: Dict[str, Any]
    ) -> Tuple[bool, List[Constraint]]:
        """Check all constraints against context."""
        violations = []

        for constraint_id, constraint in self._constraints.items():
            if not constraint.active:
                continue

            check_func = self._constraint_checks.get(constraint_id)

            if check_func:
                try:
                    if not check_func(context):
                        violations.append(constraint)
                except Exception:
                    if constraint.constraint_type == ConstraintType.HARD:
                        violations.append(constraint)

        hard_violations = [
            v for v in violations
            if v.constraint_type == ConstraintType.HARD
        ]

        all_passed = len(hard_violations) == 0

        return all_passed, violations

    def get_constraints_by_type(
        self,
        constraint_type: ConstraintType
    ) -> List[Constraint]:
        """Get constraints by type."""
        return [
            c for c in self._constraints.values()
            if c.constraint_type == constraint_type
        ]


# =============================================================================
# ACTION FILTER
# =============================================================================

class ActionFilter:
    """Filter and check actions."""

    def __init__(self):
        self._forbidden_actions: Set[str] = set()
        self._dangerous_patterns: List[str] = []
        self._action_history: List[Tuple[str, datetime]] = []
        self._rate_limits: Dict[str, int] = {}

    def add_forbidden_action(self, action_type: str) -> None:
        """Add a forbidden action type."""
        self._forbidden_actions.add(action_type)

    def remove_forbidden_action(self, action_type: str) -> None:
        """Remove a forbidden action type."""
        self._forbidden_actions.discard(action_type)

    def add_dangerous_pattern(self, pattern: str) -> None:
        """Add a dangerous pattern."""
        self._dangerous_patterns.append(pattern)

    def set_rate_limit(
        self,
        action_type: str,
        max_per_minute: int
    ) -> None:
        """Set rate limit for an action type."""
        self._rate_limits[action_type] = max_per_minute

    def check_action(
        self,
        action_type: str,
        action_data: Dict[str, Any]
    ) -> ActionCheck:
        """Check if an action is allowed."""
        violations = []
        warnings = []
        category = ActionCategory.SAFE
        risk_level = RiskLevel.NONE

        if action_type in self._forbidden_actions:
            violations.append(f"Action type '{action_type}' is forbidden")
            category = ActionCategory.FORBIDDEN
            risk_level = RiskLevel.CRITICAL

        for pattern in self._dangerous_patterns:
            if self._matches_pattern(action_type, action_data, pattern):
                warnings.append(f"Action matches dangerous pattern: {pattern}")
                if category == ActionCategory.SAFE:
                    category = ActionCategory.DANGEROUS
                    risk_level = RiskLevel.HIGH

        if action_type in self._rate_limits:
            if self._check_rate_limit(action_type):
                violations.append(f"Rate limit exceeded for '{action_type}'")
                category = ActionCategory.CAUTION
                risk_level = max(risk_level, RiskLevel.MEDIUM)

        self._action_history.append((action_type, datetime.now()))

        allowed = len(violations) == 0

        return ActionCheck(
            action_type=action_type,
            category=category,
            risk_level=risk_level,
            allowed=allowed,
            violations=violations,
            warnings=warnings
        )

    def _matches_pattern(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        pattern: str
    ) -> bool:
        """Check if action matches a dangerous pattern."""
        if pattern in action_type:
            return True

        for key, value in action_data.items():
            if isinstance(value, str) and pattern in value:
                return True

        return False

    def _check_rate_limit(
        self,
        action_type: str,
        window_seconds: int = 60
    ) -> bool:
        """Check if rate limit is exceeded."""
        limit = self._rate_limits.get(action_type, float('inf'))

        cutoff = datetime.now() - timedelta(seconds=window_seconds)

        recent_count = sum(
            1 for at, ts in self._action_history
            if at == action_type and ts > cutoff
        )

        return recent_count >= limit

    def get_action_stats(self) -> Dict[str, int]:
        """Get action statistics."""
        stats: Dict[str, int] = defaultdict(int)

        for action_type, _ in self._action_history:
            stats[action_type] += 1

        return dict(stats)

    def clear_history(self) -> None:
        """Clear action history."""
        self._action_history.clear()


# =============================================================================
# RISK ASSESSOR
# =============================================================================

class RiskAssessor:
    """Assess risks."""

    def __init__(self, threshold: float = 0.7):
        self._threshold = threshold
        self._risk_weights: Dict[str, float] = {}
        self._assessments: List[RiskAssessment] = []

    def set_risk_weight(self, factor: str, weight: float) -> None:
        """Set weight for a risk factor."""
        self._risk_weights[factor] = max(0.0, min(1.0, weight))

    def assess(
        self,
        subject: str,
        factors: Dict[str, float]
    ) -> RiskAssessment:
        """Assess risk for a subject."""
        weighted_sum = 0.0
        total_weight = 0.0

        for factor, value in factors.items():
            weight = self._risk_weights.get(factor, 0.5)
            weighted_sum += value * weight
            total_weight += weight

        if total_weight > 0:
            overall_score = weighted_sum / total_weight
        else:
            overall_score = sum(factors.values()) / len(factors) if factors else 0.0

        if overall_score >= 0.9:
            overall_risk = RiskLevel.CRITICAL
        elif overall_score >= 0.7:
            overall_risk = RiskLevel.HIGH
        elif overall_score >= 0.4:
            overall_risk = RiskLevel.MEDIUM
        elif overall_score >= 0.2:
            overall_risk = RiskLevel.LOW
        else:
            overall_risk = RiskLevel.NONE

        mitigations = self._suggest_mitigations(factors)

        assessment = RiskAssessment(
            subject=subject,
            overall_risk=overall_risk,
            risk_factors=factors,
            mitigations=mitigations
        )

        self._assessments.append(assessment)

        return assessment

    def _suggest_mitigations(
        self,
        factors: Dict[str, float]
    ) -> List[str]:
        """Suggest risk mitigations."""
        mitigations = []

        high_risk_factors = [
            f for f, v in factors.items()
            if v >= self._threshold
        ]

        for factor in high_risk_factors:
            mitigations.append(f"Reduce {factor} exposure")
            mitigations.append(f"Add monitoring for {factor}")

        return mitigations

    def get_high_risk_subjects(self) -> List[RiskAssessment]:
        """Get high risk assessments."""
        return [
            a for a in self._assessments
            if a.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]

    def get_recent_assessments(
        self,
        limit: int = 20
    ) -> List[RiskAssessment]:
        """Get recent assessments."""
        return self._assessments[-limit:]


# =============================================================================
# BOUNDARY ENFORCER
# =============================================================================

class BoundaryEnforcer:
    """Enforce safety boundaries."""

    def __init__(self):
        self._boundaries: Dict[str, Boundary] = {}
        self._violations: List[Violation] = []

    def add_boundary(
        self,
        name: str,
        boundary_type: BoundaryType = BoundaryType.RESOURCE,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        enforcement: ConstraintType = ConstraintType.HARD
    ) -> Boundary:
        """Add a safety boundary."""
        boundary = Boundary(
            name=name,
            boundary_type=boundary_type,
            min_value=min_value,
            max_value=max_value,
            enforcement=enforcement
        )

        self._boundaries[boundary.boundary_id] = boundary

        return boundary

    def get_boundary(self, boundary_id: str) -> Optional[Boundary]:
        """Get a boundary by ID."""
        return self._boundaries.get(boundary_id)

    def get_boundary_by_name(self, name: str) -> Optional[Boundary]:
        """Get a boundary by name."""
        for boundary in self._boundaries.values():
            if boundary.name == name:
                return boundary
        return None

    def update_value(
        self,
        boundary_id: str,
        value: float
    ) -> Tuple[bool, Optional[Violation]]:
        """Update boundary value and check for violations."""
        boundary = self._boundaries.get(boundary_id)

        if not boundary:
            return False, None

        boundary.current_value = value

        violation = None
        within_bounds = True

        if boundary.min_value is not None and value < boundary.min_value:
            within_bounds = False
            violation = Violation(
                violation_type=ViolationType.BOUNDARY,
                constraint_id=boundary_id,
                severity=RiskLevel.HIGH if boundary.enforcement == ConstraintType.HARD else RiskLevel.MEDIUM,
                description=f"{boundary.name}: value {value} below minimum {boundary.min_value}"
            )

        if boundary.max_value is not None and value > boundary.max_value:
            within_bounds = False
            violation = Violation(
                violation_type=ViolationType.BOUNDARY,
                constraint_id=boundary_id,
                severity=RiskLevel.HIGH if boundary.enforcement == ConstraintType.HARD else RiskLevel.MEDIUM,
                description=f"{boundary.name}: value {value} above maximum {boundary.max_value}"
            )

        if violation:
            self._violations.append(violation)

        return within_bounds, violation

    def check_all_boundaries(self) -> List[Boundary]:
        """Check all boundaries for violations."""
        violated = []

        for boundary in self._boundaries.values():
            if boundary.min_value is not None:
                if boundary.current_value < boundary.min_value:
                    violated.append(boundary)
                    continue

            if boundary.max_value is not None:
                if boundary.current_value > boundary.max_value:
                    violated.append(boundary)

        return violated

    def get_violations(self) -> List[Violation]:
        """Get all violations."""
        return self._violations[:]

    def get_recent_violations(
        self,
        limit: int = 20
    ) -> List[Violation]:
        """Get recent violations."""
        return self._violations[-limit:]

    def clear_violations(self) -> None:
        """Clear violation history."""
        self._violations.clear()


# =============================================================================
# SAFETY MONITOR
# =============================================================================

class SafetyMonitor:
    """Monitor overall safety state."""

    def __init__(
        self,
        lockdown_threshold: int = 5,
        alert_threshold: int = 2
    ):
        self._state = SafetyState.NORMAL
        self._lockdown_threshold = lockdown_threshold
        self._alert_threshold = alert_threshold

        self._incident_count = 0
        self._incidents: List[Dict[str, Any]] = []

        self._callbacks: Dict[SafetyState, List[Callable]] = defaultdict(list)

    def get_state(self) -> SafetyState:
        """Get current safety state."""
        return self._state

    def report_incident(
        self,
        severity: RiskLevel,
        description: str
    ) -> SafetyState:
        """Report a safety incident."""
        self._incident_count += 1

        incident = {
            "id": str(uuid.uuid4())[:8],
            "severity": severity.name,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }

        self._incidents.append(incident)

        self._update_state(severity)

        return self._state

    def _update_state(self, severity: RiskLevel) -> None:
        """Update safety state based on severity."""
        old_state = self._state

        if severity == RiskLevel.CRITICAL:
            self._state = SafetyState.EMERGENCY
        elif self._incident_count >= self._lockdown_threshold:
            self._state = SafetyState.LOCKDOWN
        elif severity == RiskLevel.HIGH or self._incident_count >= self._alert_threshold:
            if self._state != SafetyState.EMERGENCY:
                self._state = SafetyState.WARNING
        elif severity == RiskLevel.MEDIUM:
            if self._state == SafetyState.NORMAL:
                self._state = SafetyState.ALERT

        if old_state != self._state:
            self._trigger_callbacks(self._state)

    def reset(self) -> None:
        """Reset to normal state."""
        self._state = SafetyState.NORMAL
        self._incident_count = 0

    def on_state_change(
        self,
        state: SafetyState,
        callback: Callable
    ) -> None:
        """Register callback for state change."""
        self._callbacks[state].append(callback)

    def _trigger_callbacks(self, state: SafetyState) -> None:
        """Trigger callbacks for state."""
        for callback in self._callbacks[state]:
            try:
                callback(state)
            except Exception:
                pass

    def get_incidents(self) -> List[Dict[str, Any]]:
        """Get all incidents."""
        return self._incidents[:]

    def get_incident_count(self) -> int:
        """Get incident count."""
        return self._incident_count

    def is_operational(self) -> bool:
        """Check if system is operational."""
        return self._state not in [SafetyState.LOCKDOWN, SafetyState.EMERGENCY]


# =============================================================================
# SAFETY ENGINE
# =============================================================================

class SafetyEngine:
    """
    Safety Engine for BAEL.

    Safety constraints and guardrails.
    """

    def __init__(self, config: Optional[SafetyConfig] = None):
        self._config = config or SafetyConfig()

        self._constraint_manager = ConstraintManager()
        self._action_filter = ActionFilter()
        self._risk_assessor = RiskAssessor(threshold=self._config.risk_threshold)
        self._boundary_enforcer = BoundaryEnforcer()
        self._monitor = SafetyMonitor(
            lockdown_threshold=self._config.lockdown_threshold
        )

    # ----- Constraint Operations -----

    def add_constraint(
        self,
        name: str,
        description: str = "",
        constraint_type: ConstraintType = ConstraintType.HARD,
        check_func: Optional[Callable[[Dict], bool]] = None
    ) -> Constraint:
        """Add a safety constraint."""
        return self._constraint_manager.add_constraint(
            name=name,
            description=description,
            constraint_type=constraint_type,
            check_func=check_func
        )

    def check_constraints(
        self,
        context: Dict[str, Any]
    ) -> Tuple[bool, List[Constraint]]:
        """Check constraints against context."""
        passed, violations = self._constraint_manager.check_constraints(context)

        if not passed:
            self._monitor.report_incident(
                RiskLevel.HIGH,
                f"Constraint violations: {len(violations)}"
            )

        return passed, violations

    def get_active_constraints(self) -> List[Constraint]:
        """Get active constraints."""
        return self._constraint_manager.get_active_constraints()

    # ----- Action Operations -----

    def check_action(
        self,
        action_type: str,
        action_data: Optional[Dict[str, Any]] = None
    ) -> ActionCheck:
        """Check if an action is allowed."""
        result = self._action_filter.check_action(
            action_type,
            action_data or {}
        )

        if not result.allowed:
            self._monitor.report_incident(
                result.risk_level,
                f"Action blocked: {action_type}"
            )

        return result

    def forbid_action(self, action_type: str) -> None:
        """Forbid an action type."""
        self._action_filter.add_forbidden_action(action_type)

    def allow_action(self, action_type: str) -> None:
        """Allow a previously forbidden action."""
        self._action_filter.remove_forbidden_action(action_type)

    def add_dangerous_pattern(self, pattern: str) -> None:
        """Add a dangerous pattern."""
        self._action_filter.add_dangerous_pattern(pattern)

    def set_rate_limit(
        self,
        action_type: str,
        max_per_minute: int
    ) -> None:
        """Set rate limit for action type."""
        self._action_filter.set_rate_limit(action_type, max_per_minute)

    # ----- Risk Operations -----

    def assess_risk(
        self,
        subject: str,
        factors: Dict[str, float]
    ) -> RiskAssessment:
        """Assess risk for a subject."""
        assessment = self._risk_assessor.assess(subject, factors)

        if assessment.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._monitor.report_incident(
                assessment.overall_risk,
                f"High risk assessment: {subject}"
            )

        return assessment

    def set_risk_weight(self, factor: str, weight: float) -> None:
        """Set weight for risk factor."""
        self._risk_assessor.set_risk_weight(factor, weight)

    def get_high_risk_subjects(self) -> List[RiskAssessment]:
        """Get high risk assessments."""
        return self._risk_assessor.get_high_risk_subjects()

    # ----- Boundary Operations -----

    def add_boundary(
        self,
        name: str,
        boundary_type: BoundaryType = BoundaryType.RESOURCE,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        enforcement: ConstraintType = ConstraintType.HARD
    ) -> Boundary:
        """Add a safety boundary."""
        return self._boundary_enforcer.add_boundary(
            name=name,
            boundary_type=boundary_type,
            min_value=min_value,
            max_value=max_value,
            enforcement=enforcement
        )

    def update_boundary(
        self,
        boundary_id: str,
        value: float
    ) -> Tuple[bool, Optional[Violation]]:
        """Update boundary value."""
        within, violation = self._boundary_enforcer.update_value(
            boundary_id, value
        )

        if violation:
            self._monitor.report_incident(
                violation.severity,
                violation.description
            )

        return within, violation

    def check_boundaries(self) -> List[Boundary]:
        """Check all boundaries."""
        return self._boundary_enforcer.check_all_boundaries()

    def get_boundary(self, name: str) -> Optional[Boundary]:
        """Get boundary by name."""
        return self._boundary_enforcer.get_boundary_by_name(name)

    # ----- Monitor Operations -----

    def get_state(self) -> SafetyState:
        """Get current safety state."""
        return self._monitor.get_state()

    def is_operational(self) -> bool:
        """Check if system is operational."""
        return self._monitor.is_operational()

    def report_incident(
        self,
        severity: RiskLevel,
        description: str
    ) -> SafetyState:
        """Report a safety incident."""
        return self._monitor.report_incident(severity, description)

    def reset_state(self) -> None:
        """Reset safety state."""
        self._monitor.reset()

    def on_state_change(
        self,
        state: SafetyState,
        callback: Callable
    ) -> None:
        """Register callback for state change."""
        self._monitor.on_state_change(state, callback)

    def get_incidents(self) -> List[Dict[str, Any]]:
        """Get all incidents."""
        return self._monitor.get_incidents()

    def get_violations(self) -> List[Violation]:
        """Get all violations."""
        return self._boundary_enforcer.get_violations()

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "state": self.get_state().value,
            "operational": self.is_operational(),
            "constraints": len(self.get_active_constraints()),
            "incidents": self._monitor.get_incident_count(),
            "violations": len(self.get_violations()),
            "high_risk_subjects": len(self.get_high_risk_subjects())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Safety Engine."""
    print("=" * 70)
    print("BAEL - SAFETY ENGINE DEMO")
    print("Safety Constraints and Guardrails")
    print("=" * 70)
    print()

    engine = SafetyEngine()

    # 1. Add Constraints
    print("1. ADD SAFETY CONSTRAINTS:")
    print("-" * 40)

    c1 = engine.add_constraint(
        name="no_destructive_actions",
        description="Prevent destructive actions",
        constraint_type=ConstraintType.HARD,
        check_func=lambda ctx: not ctx.get("destructive", False)
    )
    print(f"   Added: {c1.name} ({c1.constraint_type.value})")

    c2 = engine.add_constraint(
        name="resource_limit",
        description="Check resource usage",
        constraint_type=ConstraintType.SOFT,
        check_func=lambda ctx: ctx.get("resource_usage", 0) < 0.9
    )
    print(f"   Added: {c2.name} ({c2.constraint_type.value})")
    print()

    # 2. Check Constraints
    print("2. CHECK CONSTRAINTS:")
    print("-" * 40)

    passed1, violations1 = engine.check_constraints({"destructive": False})
    print(f"   Safe context: passed={passed1}, violations={len(violations1)}")

    passed2, violations2 = engine.check_constraints({"destructive": True})
    print(f"   Unsafe context: passed={passed2}, violations={len(violations2)}")
    print()

    # 3. Forbid Actions
    print("3. FORBID ACTIONS:")
    print("-" * 40)

    engine.forbid_action("delete_all")
    engine.forbid_action("sudo_command")

    print("   Forbidden: delete_all, sudo_command")
    print()

    # 4. Check Actions
    print("4. CHECK ACTIONS:")
    print("-" * 40)

    check1 = engine.check_action("read_file", {"path": "/etc/config"})
    print(f"   read_file: allowed={check1.allowed}, category={check1.category.value}")

    check2 = engine.check_action("delete_all", {})
    print(f"   delete_all: allowed={check2.allowed}, category={check2.category.value}")
    print()

    # 5. Dangerous Patterns
    print("5. ADD DANGEROUS PATTERNS:")
    print("-" * 40)

    engine.add_dangerous_pattern("rm -rf")
    engine.add_dangerous_pattern("DROP TABLE")

    check3 = engine.check_action("execute", {"command": "rm -rf /tmp"})
    print(f"   'rm -rf' command: category={check3.category.value}")
    print(f"   Warnings: {check3.warnings}")
    print()

    # 6. Rate Limits
    print("6. RATE LIMITS:")
    print("-" * 40)

    engine.set_rate_limit("api_call", 5)

    for i in range(7):
        check = engine.check_action("api_call", {})
        if not check.allowed:
            print(f"   Call {i+1}: rate limit exceeded")
            break
        else:
            print(f"   Call {i+1}: allowed")
    print()

    # 7. Add Boundaries
    print("7. ADD BOUNDARIES:")
    print("-" * 40)

    b1 = engine.add_boundary(
        name="memory_usage",
        boundary_type=BoundaryType.RESOURCE,
        min_value=0,
        max_value=1024,
        enforcement=ConstraintType.HARD
    )
    print(f"   Added: {b1.name} (max={b1.max_value})")

    b2 = engine.add_boundary(
        name="request_rate",
        boundary_type=BoundaryType.TEMPORAL,
        max_value=100,
        enforcement=ConstraintType.SOFT
    )
    print(f"   Added: {b2.name} (max={b2.max_value})")
    print()

    # 8. Update Boundaries
    print("8. UPDATE BOUNDARIES:")
    print("-" * 40)

    within, violation = engine.update_boundary(b1.boundary_id, 800)
    print(f"   memory=800: within_bounds={within}")

    within, violation = engine.update_boundary(b1.boundary_id, 1500)
    print(f"   memory=1500: within_bounds={within}")
    if violation:
        print(f"   Violation: {violation.description}")
    print()

    # 9. Risk Assessment
    print("9. RISK ASSESSMENT:")
    print("-" * 40)

    engine.set_risk_weight("external_access", 0.8)
    engine.set_risk_weight("data_sensitivity", 0.9)

    assessment1 = engine.assess_risk(
        "user_query",
        {
            "external_access": 0.2,
            "data_sensitivity": 0.3
        }
    )
    print(f"   user_query: risk={assessment1.overall_risk.name}")

    assessment2 = engine.assess_risk(
        "admin_action",
        {
            "external_access": 0.9,
            "data_sensitivity": 0.8
        }
    )
    print(f"   admin_action: risk={assessment2.overall_risk.name}")
    print(f"   Mitigations: {assessment2.mitigations[:2]}")
    print()

    # 10. Safety State
    print("10. SAFETY STATE:")
    print("-" * 40)

    print(f"   Current State: {engine.get_state().value}")
    print(f"   Operational: {engine.is_operational()}")
    print()

    # 11. Report Incidents
    print("11. REPORT INCIDENTS:")
    print("-" * 40)

    engine.report_incident(RiskLevel.MEDIUM, "Unusual access pattern")
    print(f"   After medium incident: {engine.get_state().value}")

    engine.report_incident(RiskLevel.HIGH, "Potential breach detected")
    print(f"   After high incident: {engine.get_state().value}")
    print()

    # 12. Incident History
    print("12. INCIDENT HISTORY:")
    print("-" * 40)

    incidents = engine.get_incidents()
    print(f"   Total incidents: {len(incidents)}")
    for incident in incidents[-3:]:
        print(f"     [{incident['severity']}] {incident['description']}")
    print()

    # 13. Violations
    print("13. VIOLATIONS:")
    print("-" * 40)

    violations = engine.get_violations()
    print(f"   Total violations: {len(violations)}")
    for v in violations[:3]:
        print(f"     [{v.severity.name}] {v.description}")
    print()

    # 14. Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    # 15. Reset State
    print("15. RESET STATE:")
    print("-" * 40)

    engine.reset_state()
    print(f"   State after reset: {engine.get_state().value}")
    print(f"   Operational: {engine.is_operational()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Safety Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
