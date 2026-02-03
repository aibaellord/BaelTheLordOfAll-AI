#!/usr/bin/env python3
"""
BAEL - Autonomy Engine
Autonomous agent operation.

Features:
- Self-governance
- Decision autonomy
- Goal autonomy
- Operational independence
- Self-monitoring
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

class AutonomyLevel(Enum):
    """Autonomy levels."""
    NONE = 0
    ASSISTED = 1
    PARTIAL = 2
    CONDITIONAL = 3
    HIGH = 4
    FULL = 5


class OperationMode(Enum):
    """Operation modes."""
    SUPERVISED = "supervised"
    SEMI_AUTONOMOUS = "semi_autonomous"
    AUTONOMOUS = "autonomous"
    EMERGENCY = "emergency"


class DecisionType(Enum):
    """Decision types."""
    ROUTINE = "routine"
    TACTICAL = "tactical"
    STRATEGIC = "strategic"
    EMERGENCY = "emergency"


class GovernanceType(Enum):
    """Governance types."""
    RULE_BASED = "rule_based"
    POLICY_BASED = "policy_based"
    VALUE_BASED = "value_based"
    HYBRID = "hybrid"


class MonitorState(Enum):
    """Monitor states."""
    NOMINAL = "nominal"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILURE = "failure"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AutonomyPolicy:
    """An autonomy policy."""
    policy_id: str = ""
    name: str = ""
    autonomy_level: AutonomyLevel = AutonomyLevel.PARTIAL
    allowed_decisions: Set[DecisionType] = field(default_factory=set)
    constraints: Dict[str, Any] = field(default_factory=dict)
    requires_approval: Set[str] = field(default_factory=set)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.policy_id:
            self.policy_id = str(uuid.uuid4())[:8]


@dataclass
class AutonomousDecision:
    """An autonomous decision."""
    decision_id: str = ""
    decision_type: DecisionType = DecisionType.ROUTINE
    description: str = ""
    options: List[str] = field(default_factory=list)
    selected_option: Optional[str] = None
    confidence: float = 0.0
    rationale: str = ""
    requires_approval: bool = False
    approved: Optional[bool] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.decision_id:
            self.decision_id = str(uuid.uuid4())[:8]


@dataclass
class GovernanceRule:
    """A governance rule."""
    rule_id: str = ""
    name: str = ""
    condition: str = ""
    action: str = ""
    priority: int = 0
    active: bool = True

    def __post_init__(self):
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())[:8]


@dataclass
class MonitorMetric:
    """A monitor metric."""
    metric_id: str = ""
    name: str = ""
    current_value: float = 0.0
    threshold_warning: float = 0.7
    threshold_critical: float = 0.9
    state: MonitorState = MonitorState.NOMINAL
    history: List[Tuple[datetime, float]] = field(default_factory=list)

    def __post_init__(self):
        if not self.metric_id:
            self.metric_id = str(uuid.uuid4())[:8]


@dataclass
class AutonomousGoal:
    """An autonomous goal."""
    goal_id: str = ""
    name: str = ""
    description: str = ""
    priority: float = 0.5
    self_generated: bool = False
    parent_goal: Optional[str] = None
    progress: float = 0.0
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.goal_id:
            self.goal_id = str(uuid.uuid4())[:8]


@dataclass
class OperationContext:
    """Operation context."""
    context_id: str = ""
    mode: OperationMode = OperationMode.SUPERVISED
    autonomy_level: AutonomyLevel = AutonomyLevel.PARTIAL
    active_policies: Set[str] = field(default_factory=set)
    constraints: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.context_id:
            self.context_id = str(uuid.uuid4())[:8]


@dataclass
class AutonomyStats:
    """Autonomy statistics."""
    decisions_made: int = 0
    decisions_approved: int = 0
    decisions_rejected: int = 0
    goals_generated: int = 0
    goals_completed: int = 0
    avg_confidence: float = 0.0
    autonomy_score: float = 0.0


# =============================================================================
# POLICY MANAGER
# =============================================================================

class PolicyManager:
    """Manage autonomy policies."""

    def __init__(self):
        self._policies: Dict[str, AutonomyPolicy] = {}
        self._active_policies: Set[str] = set()

    def create(
        self,
        name: str,
        autonomy_level: AutonomyLevel = AutonomyLevel.PARTIAL,
        allowed_decisions: Optional[Set[DecisionType]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        requires_approval: Optional[Set[str]] = None
    ) -> AutonomyPolicy:
        """Create a policy."""
        policy = AutonomyPolicy(
            name=name,
            autonomy_level=autonomy_level,
            allowed_decisions=allowed_decisions or {DecisionType.ROUTINE},
            constraints=constraints or {},
            requires_approval=requires_approval or set()
        )

        self._policies[policy.policy_id] = policy

        return policy

    def activate(self, policy_id: str) -> bool:
        """Activate a policy."""
        if policy_id in self._policies:
            self._policies[policy_id].active = True
            self._active_policies.add(policy_id)
            return True
        return False

    def deactivate(self, policy_id: str) -> bool:
        """Deactivate a policy."""
        if policy_id in self._policies:
            self._policies[policy_id].active = False
            self._active_policies.discard(policy_id)
            return True
        return False

    def get(self, policy_id: str) -> Optional[AutonomyPolicy]:
        """Get a policy."""
        return self._policies.get(policy_id)

    def get_active(self) -> List[AutonomyPolicy]:
        """Get active policies."""
        return [self._policies[pid] for pid in self._active_policies if pid in self._policies]

    def get_max_autonomy_level(self) -> AutonomyLevel:
        """Get maximum autonomy level from active policies."""
        active = self.get_active()
        if not active:
            return AutonomyLevel.NONE

        return max(p.autonomy_level for p in active)

    def is_decision_allowed(
        self,
        decision_type: DecisionType
    ) -> bool:
        """Check if a decision type is allowed."""
        active = self.get_active()

        for policy in active:
            if decision_type in policy.allowed_decisions:
                return True

        return False

    def requires_approval(self, action: str) -> bool:
        """Check if an action requires approval."""
        active = self.get_active()

        for policy in active:
            if action in policy.requires_approval:
                return True

        return False


# =============================================================================
# DECISION ENGINE
# =============================================================================

class DecisionEngine:
    """Make autonomous decisions."""

    def __init__(self, policy_manager: PolicyManager):
        self._policy_manager = policy_manager
        self._decisions: Dict[str, AutonomousDecision] = {}
        self._pending_approval: Dict[str, AutonomousDecision] = {}
        self._confidence_history: List[float] = []

    def make_decision(
        self,
        decision_type: DecisionType,
        description: str,
        options: List[str],
        evaluator: Optional[Callable[[str], float]] = None
    ) -> Optional[AutonomousDecision]:
        """Make an autonomous decision."""
        if not self._policy_manager.is_decision_allowed(decision_type):
            return None

        if not options:
            return None

        scores = {}
        for option in options:
            if evaluator:
                scores[option] = evaluator(option)
            else:
                scores[option] = random.random()

        best_option = max(scores.keys(), key=lambda x: scores[x])
        confidence = scores[best_option]

        requires_approval = (
            decision_type in {DecisionType.STRATEGIC, DecisionType.EMERGENCY} or
            self._policy_manager.requires_approval(description)
        )

        decision = AutonomousDecision(
            decision_type=decision_type,
            description=description,
            options=options,
            selected_option=best_option,
            confidence=confidence,
            rationale=f"Selected based on evaluation score: {confidence:.2f}",
            requires_approval=requires_approval
        )

        self._decisions[decision.decision_id] = decision
        self._confidence_history.append(confidence)

        if requires_approval:
            self._pending_approval[decision.decision_id] = decision

        return decision

    def approve_decision(self, decision_id: str) -> bool:
        """Approve a pending decision."""
        decision = self._pending_approval.pop(decision_id, None)
        if decision:
            decision.approved = True
            return True
        return False

    def reject_decision(self, decision_id: str) -> bool:
        """Reject a pending decision."""
        decision = self._pending_approval.pop(decision_id, None)
        if decision:
            decision.approved = False
            return True
        return False

    def get_decision(self, decision_id: str) -> Optional[AutonomousDecision]:
        """Get a decision."""
        return self._decisions.get(decision_id)

    def get_pending(self) -> List[AutonomousDecision]:
        """Get pending decisions."""
        return list(self._pending_approval.values())

    @property
    def avg_confidence(self) -> float:
        """Get average decision confidence."""
        if not self._confidence_history:
            return 0.0
        return sum(self._confidence_history) / len(self._confidence_history)


# =============================================================================
# GOVERNANCE ENGINE
# =============================================================================

class GovernanceEngine:
    """Self-governance system."""

    def __init__(self, governance_type: GovernanceType = GovernanceType.RULE_BASED):
        self._governance_type = governance_type
        self._rules: Dict[str, GovernanceRule] = {}
        self._values: Dict[str, float] = {}
        self._violations: List[Dict[str, Any]] = []

    def add_rule(
        self,
        name: str,
        condition: str,
        action: str,
        priority: int = 0
    ) -> GovernanceRule:
        """Add a governance rule."""
        rule = GovernanceRule(
            name=name,
            condition=condition,
            action=action,
            priority=priority
        )

        self._rules[rule.rule_id] = rule

        return rule

    def set_value(self, name: str, weight: float) -> None:
        """Set a governance value."""
        self._values[name] = max(0.0, min(1.0, weight))

    def get_value(self, name: str) -> float:
        """Get a governance value."""
        return self._values.get(name, 0.0)

    def evaluate(self, context: Dict[str, Any]) -> List[str]:
        """Evaluate rules against context."""
        actions = []

        sorted_rules = sorted(
            self._rules.values(),
            key=lambda r: r.priority,
            reverse=True
        )

        for rule in sorted_rules:
            if not rule.active:
                continue

            if self._check_condition(rule.condition, context):
                actions.append(rule.action)

        return actions

    def _check_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """Check if a condition is met."""
        for key, value in context.items():
            condition = condition.replace(f"${key}", str(value))

        try:
            return eval(condition, {"__builtins__": {}}, {})
        except:
            return False

    def record_violation(
        self,
        rule_id: str,
        context: Dict[str, Any],
        severity: str = "minor"
    ) -> None:
        """Record a rule violation."""
        self._violations.append({
            "rule_id": rule_id,
            "context": context,
            "severity": severity,
            "timestamp": datetime.now()
        })

    def get_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recorded violations."""
        return self._violations[-limit:]

    @property
    def governance_type(self) -> GovernanceType:
        return self._governance_type


# =============================================================================
# GOAL GENERATOR
# =============================================================================

class GoalGenerator:
    """Generate autonomous goals."""

    def __init__(self):
        self._goals: Dict[str, AutonomousGoal] = {}
        self._templates: Dict[str, Dict[str, Any]] = {}

    def add_template(
        self,
        name: str,
        description_template: str,
        priority_range: Tuple[float, float] = (0.3, 0.7)
    ) -> None:
        """Add a goal template."""
        self._templates[name] = {
            "description": description_template,
            "priority_range": priority_range
        }

    def generate(
        self,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        parent_goal: Optional[str] = None
    ) -> Optional[AutonomousGoal]:
        """Generate a goal from template."""
        template = self._templates.get(template_name)
        if not template:
            return None

        description = template["description"]
        if context:
            for key, value in context.items():
                description = description.replace(f"{{{key}}}", str(value))

        priority_range = template["priority_range"]
        priority = random.uniform(priority_range[0], priority_range[1])

        goal = AutonomousGoal(
            name=template_name,
            description=description,
            priority=priority,
            self_generated=True,
            parent_goal=parent_goal
        )

        self._goals[goal.goal_id] = goal

        return goal

    def create_goal(
        self,
        name: str,
        description: str,
        priority: float = 0.5,
        parent_goal: Optional[str] = None
    ) -> AutonomousGoal:
        """Create a custom goal."""
        goal = AutonomousGoal(
            name=name,
            description=description,
            priority=priority,
            self_generated=True,
            parent_goal=parent_goal
        )

        self._goals[goal.goal_id] = goal

        return goal

    def update_progress(self, goal_id: str, progress: float) -> bool:
        """Update goal progress."""
        goal = self._goals.get(goal_id)
        if not goal:
            return False

        goal.progress = max(0.0, min(1.0, progress))

        if goal.progress >= 1.0:
            goal.status = "completed"

        return True

    def get_goal(self, goal_id: str) -> Optional[AutonomousGoal]:
        """Get a goal."""
        return self._goals.get(goal_id)

    def get_active(self) -> List[AutonomousGoal]:
        """Get active goals."""
        return [g for g in self._goals.values() if g.status == "active"]

    def get_by_priority(self) -> List[AutonomousGoal]:
        """Get goals sorted by priority."""
        active = self.get_active()
        return sorted(active, key=lambda g: g.priority, reverse=True)


# =============================================================================
# SELF MONITOR
# =============================================================================

class SelfMonitor:
    """Self-monitoring system."""

    def __init__(self):
        self._metrics: Dict[str, MonitorMetric] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._handlers: Dict[MonitorState, List[Callable]] = defaultdict(list)

    def register_metric(
        self,
        name: str,
        threshold_warning: float = 0.7,
        threshold_critical: float = 0.9
    ) -> MonitorMetric:
        """Register a metric."""
        metric = MonitorMetric(
            name=name,
            threshold_warning=threshold_warning,
            threshold_critical=threshold_critical
        )

        self._metrics[metric.metric_id] = metric

        return metric

    def update_metric(self, metric_id: str, value: float) -> MonitorState:
        """Update a metric value."""
        metric = self._metrics.get(metric_id)
        if not metric:
            return MonitorState.NOMINAL

        old_state = metric.state
        metric.current_value = value
        metric.history.append((datetime.now(), value))

        if len(metric.history) > 100:
            metric.history = metric.history[-100:]

        if value >= metric.threshold_critical:
            metric.state = MonitorState.CRITICAL
        elif value >= metric.threshold_warning:
            metric.state = MonitorState.WARNING
        else:
            metric.state = MonitorState.NOMINAL

        if metric.state != old_state:
            self._trigger_handlers(metric)

            if metric.state in {MonitorState.WARNING, MonitorState.CRITICAL}:
                self._alerts.append({
                    "metric_id": metric_id,
                    "metric_name": metric.name,
                    "value": value,
                    "state": metric.state.value,
                    "timestamp": datetime.now()
                })

        return metric.state

    def register_handler(
        self,
        state: MonitorState,
        handler: Callable[[MonitorMetric], None]
    ) -> None:
        """Register a state handler."""
        self._handlers[state].append(handler)

    def _trigger_handlers(self, metric: MonitorMetric) -> None:
        """Trigger handlers for a state."""
        handlers = self._handlers.get(metric.state, [])
        for handler in handlers:
            try:
                handler(metric)
            except Exception:
                pass

    def get_metric(self, metric_id: str) -> Optional[MonitorMetric]:
        """Get a metric."""
        return self._metrics.get(metric_id)

    def get_all_metrics(self) -> List[MonitorMetric]:
        """Get all metrics."""
        return list(self._metrics.values())

    def get_status(self) -> Dict[str, MonitorState]:
        """Get status of all metrics."""
        return {m.name: m.state for m in self._metrics.values()}

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self._alerts[-limit:]

    def get_overall_state(self) -> MonitorState:
        """Get overall system state."""
        states = [m.state for m in self._metrics.values()]

        if not states:
            return MonitorState.NOMINAL

        if MonitorState.FAILURE in states:
            return MonitorState.FAILURE
        if MonitorState.CRITICAL in states:
            return MonitorState.CRITICAL
        if MonitorState.WARNING in states:
            return MonitorState.WARNING

        return MonitorState.NOMINAL


# =============================================================================
# AUTONOMY ENGINE
# =============================================================================

class AutonomyEngine:
    """
    Autonomy Engine for BAEL.

    Autonomous agent operation.
    """

    def __init__(self, governance_type: GovernanceType = GovernanceType.HYBRID):
        self._policies = PolicyManager()
        self._decisions = DecisionEngine(self._policies)
        self._governance = GovernanceEngine(governance_type)
        self._goals = GoalGenerator()
        self._monitor = SelfMonitor()

        self._context = OperationContext()
        self._stats = AutonomyStats()

        self._setup_default_policies()
        self._setup_default_metrics()

    def _setup_default_policies(self) -> None:
        """Setup default autonomy policies."""
        routine_policy = self._policies.create(
            name="routine_operations",
            autonomy_level=AutonomyLevel.PARTIAL,
            allowed_decisions={DecisionType.ROUTINE},
            constraints={"max_actions_per_minute": 10}
        )
        self._policies.activate(routine_policy.policy_id)

    def _setup_default_metrics(self) -> None:
        """Setup default monitoring metrics."""
        self._monitor.register_metric("cpu_usage", 0.7, 0.9)
        self._monitor.register_metric("memory_usage", 0.75, 0.9)
        self._monitor.register_metric("error_rate", 0.1, 0.3)
        self._monitor.register_metric("decision_confidence", 0.3, 0.5)

    def create_policy(
        self,
        name: str,
        autonomy_level: AutonomyLevel = AutonomyLevel.PARTIAL,
        allowed_decisions: Optional[Set[DecisionType]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> AutonomyPolicy:
        """Create an autonomy policy."""
        return self._policies.create(
            name, autonomy_level, allowed_decisions, constraints
        )

    def activate_policy(self, policy_id: str) -> bool:
        """Activate a policy."""
        result = self._policies.activate(policy_id)
        if result:
            self._context.active_policies.add(policy_id)
            self._context.autonomy_level = self._policies.get_max_autonomy_level()
        return result

    def deactivate_policy(self, policy_id: str) -> bool:
        """Deactivate a policy."""
        result = self._policies.deactivate(policy_id)
        if result:
            self._context.active_policies.discard(policy_id)
            self._context.autonomy_level = self._policies.get_max_autonomy_level()
        return result

    def set_operation_mode(self, mode: OperationMode) -> None:
        """Set operation mode."""
        self._context.mode = mode

        if mode == OperationMode.AUTONOMOUS:
            self._context.autonomy_level = AutonomyLevel.FULL
        elif mode == OperationMode.SUPERVISED:
            self._context.autonomy_level = AutonomyLevel.ASSISTED
        elif mode == OperationMode.EMERGENCY:
            self._context.autonomy_level = AutonomyLevel.FULL

    def make_decision(
        self,
        decision_type: DecisionType,
        description: str,
        options: List[str],
        evaluator: Optional[Callable[[str], float]] = None
    ) -> Optional[AutonomousDecision]:
        """Make an autonomous decision."""
        decision = self._decisions.make_decision(
            decision_type, description, options, evaluator
        )

        if decision:
            self._stats.decisions_made += 1

        return decision

    def approve_decision(self, decision_id: str) -> bool:
        """Approve a pending decision."""
        result = self._decisions.approve_decision(decision_id)
        if result:
            self._stats.decisions_approved += 1
        return result

    def reject_decision(self, decision_id: str) -> bool:
        """Reject a pending decision."""
        result = self._decisions.reject_decision(decision_id)
        if result:
            self._stats.decisions_rejected += 1
        return result

    def get_pending_decisions(self) -> List[AutonomousDecision]:
        """Get pending decisions."""
        return self._decisions.get_pending()

    def add_governance_rule(
        self,
        name: str,
        condition: str,
        action: str,
        priority: int = 0
    ) -> GovernanceRule:
        """Add a governance rule."""
        return self._governance.add_rule(name, condition, action, priority)

    def set_governance_value(self, name: str, weight: float) -> None:
        """Set a governance value."""
        self._governance.set_value(name, weight)

    def evaluate_governance(
        self,
        context: Dict[str, Any]
    ) -> List[str]:
        """Evaluate governance rules."""
        return self._governance.evaluate(context)

    def add_goal_template(
        self,
        name: str,
        description_template: str,
        priority_range: Tuple[float, float] = (0.3, 0.7)
    ) -> None:
        """Add a goal template."""
        self._goals.add_template(name, description_template, priority_range)

    def generate_goal(
        self,
        template_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[AutonomousGoal]:
        """Generate an autonomous goal."""
        goal = self._goals.generate(template_name, context)
        if goal:
            self._stats.goals_generated += 1
        return goal

    def create_goal(
        self,
        name: str,
        description: str,
        priority: float = 0.5
    ) -> AutonomousGoal:
        """Create a custom goal."""
        goal = self._goals.create_goal(name, description, priority)
        self._stats.goals_generated += 1
        return goal

    def update_goal_progress(self, goal_id: str, progress: float) -> bool:
        """Update goal progress."""
        result = self._goals.update_progress(goal_id, progress)

        goal = self._goals.get_goal(goal_id)
        if goal and goal.status == "completed":
            self._stats.goals_completed += 1

        return result

    def get_active_goals(self) -> List[AutonomousGoal]:
        """Get active goals."""
        return self._goals.get_active()

    def get_prioritized_goals(self) -> List[AutonomousGoal]:
        """Get goals sorted by priority."""
        return self._goals.get_by_priority()

    def register_metric(
        self,
        name: str,
        threshold_warning: float = 0.7,
        threshold_critical: float = 0.9
    ) -> MonitorMetric:
        """Register a monitoring metric."""
        return self._monitor.register_metric(name, threshold_warning, threshold_critical)

    def update_metric(self, metric_id: str, value: float) -> MonitorState:
        """Update a metric value."""
        return self._monitor.update_metric(metric_id, value)

    def get_system_status(self) -> Dict[str, MonitorState]:
        """Get system status."""
        return self._monitor.get_status()

    def get_overall_state(self) -> MonitorState:
        """Get overall system state."""
        return self._monitor.get_overall_state()

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self._monitor.get_alerts(limit)

    def calculate_autonomy_score(self) -> float:
        """Calculate overall autonomy score."""
        factors = []

        level_score = self._context.autonomy_level.value / 5.0
        factors.append(level_score)

        if self._stats.decisions_made > 0:
            approval_rate = self._stats.decisions_approved / self._stats.decisions_made
            factors.append(approval_rate)

        confidence = self._decisions.avg_confidence
        factors.append(confidence)

        if self._stats.goals_generated > 0:
            goal_rate = self._stats.goals_completed / self._stats.goals_generated
            factors.append(goal_rate)

        state = self._monitor.get_overall_state()
        state_score = 1.0 if state == MonitorState.NOMINAL else 0.5
        factors.append(state_score)

        if factors:
            self._stats.autonomy_score = sum(factors) / len(factors)

        return self._stats.autonomy_score

    @property
    def context(self) -> OperationContext:
        """Get operation context."""
        return self._context

    @property
    def autonomy_level(self) -> AutonomyLevel:
        """Get current autonomy level."""
        return self._context.autonomy_level

    @property
    def operation_mode(self) -> OperationMode:
        """Get current operation mode."""
        return self._context.mode

    @property
    def stats(self) -> AutonomyStats:
        """Get autonomy statistics."""
        self._stats.avg_confidence = self._decisions.avg_confidence
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "operation_mode": self._context.mode.value,
            "autonomy_level": self._context.autonomy_level.value,
            "governance_type": self._governance.governance_type.value,
            "active_policies": len(self._context.active_policies),
            "decisions_made": self._stats.decisions_made,
            "decisions_approved": self._stats.decisions_approved,
            "decisions_rejected": self._stats.decisions_rejected,
            "pending_decisions": len(self._decisions.get_pending()),
            "goals_generated": self._stats.goals_generated,
            "goals_completed": self._stats.goals_completed,
            "active_goals": len(self._goals.get_active()),
            "avg_confidence": f"{self._stats.avg_confidence:.2f}",
            "system_state": self._monitor.get_overall_state().value,
            "autonomy_score": f"{self.calculate_autonomy_score():.2f}"
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Autonomy Engine."""
    print("=" * 70)
    print("BAEL - AUTONOMY ENGINE DEMO")
    print("Autonomous Agent Operation")
    print("=" * 70)
    print()

    engine = AutonomyEngine(governance_type=GovernanceType.HYBRID)

    # 1. Create Policies
    print("1. CREATE AUTONOMY POLICIES:")
    print("-" * 40)

    tactical_policy = engine.create_policy(
        name="tactical_operations",
        autonomy_level=AutonomyLevel.HIGH,
        allowed_decisions={DecisionType.ROUTINE, DecisionType.TACTICAL}
    )

    engine.activate_policy(tactical_policy.policy_id)

    print(f"   Policy: {tactical_policy.name}")
    print(f"   Autonomy Level: {tactical_policy.autonomy_level.value}")
    print(f"   Current Level: {engine.autonomy_level.value}")
    print()

    # 2. Set Operation Mode
    print("2. SET OPERATION MODE:")
    print("-" * 40)

    engine.set_operation_mode(OperationMode.SEMI_AUTONOMOUS)

    print(f"   Mode: {engine.operation_mode.value}")
    print(f"   Autonomy Level: {engine.autonomy_level.value}")
    print()

    # 3. Make Decisions
    print("3. MAKE AUTONOMOUS DECISIONS:")
    print("-" * 40)

    def evaluator(option: str) -> float:
        scores = {"optimize": 0.9, "wait": 0.6, "retry": 0.75}
        return scores.get(option, 0.5)

    decision1 = engine.make_decision(
        DecisionType.ROUTINE,
        "Handle resource allocation",
        ["optimize", "wait", "retry"],
        evaluator
    )

    print(f"   Decision: {decision1.description}")
    print(f"   Selected: {decision1.selected_option}")
    print(f"   Confidence: {decision1.confidence:.2f}")
    print(f"   Requires Approval: {decision1.requires_approval}")
    print()

    # 4. Strategic Decision (requires approval)
    print("4. STRATEGIC DECISION:")
    print("-" * 40)

    strategic_policy = engine.create_policy(
        name="strategic_operations",
        autonomy_level=AutonomyLevel.FULL,
        allowed_decisions={DecisionType.STRATEGIC}
    )
    engine.activate_policy(strategic_policy.policy_id)

    decision2 = engine.make_decision(
        DecisionType.STRATEGIC,
        "Major system upgrade",
        ["proceed", "delay", "cancel"]
    )

    print(f"   Decision: {decision2.description}")
    print(f"   Selected: {decision2.selected_option}")
    print(f"   Requires Approval: {decision2.requires_approval}")

    engine.approve_decision(decision2.decision_id)
    print(f"   Approved: {decision2.approved}")
    print()

    # 5. Add Governance Rules
    print("5. ADD GOVERNANCE RULES:")
    print("-" * 40)

    rule1 = engine.add_governance_rule(
        name="resource_limit",
        condition="$cpu_usage > 0.8",
        action="reduce_workload",
        priority=10
    )

    rule2 = engine.add_governance_rule(
        name="safety_check",
        condition="$error_rate > 0.1",
        action="pause_operations",
        priority=20
    )

    print(f"   Rule 1: {rule1.name} -> {rule1.action}")
    print(f"   Rule 2: {rule2.name} -> {rule2.action}")

    actions = engine.evaluate_governance({"cpu_usage": 0.85, "error_rate": 0.05})
    print(f"   Triggered actions: {actions}")
    print()

    # 6. Set Governance Values
    print("6. SET GOVERNANCE VALUES:")
    print("-" * 40)

    engine.set_governance_value("safety", 0.9)
    engine.set_governance_value("efficiency", 0.7)
    engine.set_governance_value("autonomy", 0.8)

    print("   safety: 0.9")
    print("   efficiency: 0.7")
    print("   autonomy: 0.8")
    print()

    # 7. Generate Goals
    print("7. GENERATE AUTONOMOUS GOALS:")
    print("-" * 40)

    engine.add_goal_template(
        "optimize_performance",
        "Optimize {metric} performance by {target}%",
        (0.5, 0.8)
    )

    goal1 = engine.generate_goal(
        "optimize_performance",
        {"metric": "response_time", "target": 20}
    )

    goal2 = engine.create_goal(
        "learn_patterns",
        "Learn and adapt to usage patterns",
        priority=0.7
    )

    print(f"   Goal 1: {goal1.description}")
    print(f"   Priority: {goal1.priority:.2f}")
    print(f"   Goal 2: {goal2.description}")
    print(f"   Priority: {goal2.priority:.2f}")
    print()

    # 8. Update Goal Progress
    print("8. UPDATE GOAL PROGRESS:")
    print("-" * 40)

    engine.update_goal_progress(goal1.goal_id, 0.5)
    engine.update_goal_progress(goal2.goal_id, 1.0)

    print(f"   Goal 1 progress: {goal1.progress:.0%}")
    print(f"   Goal 2 progress: {goal2.progress:.0%} ({goal2.status})")
    print()

    # 9. Monitor Metrics
    print("9. MONITOR METRICS:")
    print("-" * 40)

    metrics = engine._monitor.get_all_metrics()

    engine.update_metric(metrics[0].metric_id, 0.65)
    engine.update_metric(metrics[1].metric_id, 0.78)
    engine.update_metric(metrics[2].metric_id, 0.05)
    engine.update_metric(metrics[3].metric_id, 0.85)

    status = engine.get_system_status()
    for name, state in status.items():
        print(f"   {name}: {state.value}")
    print()

    # 10. System State
    print("10. SYSTEM STATE:")
    print("-" * 40)

    overall = engine.get_overall_state()
    print(f"   Overall State: {overall.value}")

    alerts = engine.get_alerts()
    print(f"   Alerts: {len(alerts)}")
    print()

    # 11. Autonomy Score
    print("11. AUTONOMY SCORE:")
    print("-" * 40)

    score = engine.calculate_autonomy_score()

    print(f"   Autonomy Score: {score:.2f}")
    print(f"   Level: {engine.autonomy_level.value}")
    print(f"   Mode: {engine.operation_mode.value}")
    print()

    # 12. Statistics
    print("12. AUTONOMY STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Decisions Made: {stats.decisions_made}")
    print(f"   Decisions Approved: {stats.decisions_approved}")
    print(f"   Decisions Rejected: {stats.decisions_rejected}")
    print(f"   Goals Generated: {stats.goals_generated}")
    print(f"   Goals Completed: {stats.goals_completed}")
    print(f"   Avg Confidence: {stats.avg_confidence:.2f}")
    print()

    # 13. Summary
    print("13. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Autonomy Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
