#!/usr/bin/env python3
"""
BAEL - Intention Engine
Agent intention and commitment management.

Features:
- BDI intentions
- Commitment strategies
- Intention adoption/drop
- Plan binding
- Execution monitoring
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

class IntentionStatus(Enum):
    """Intention status."""
    PENDING = "pending"
    ACTIVE = "active"
    EXECUTING = "executing"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    DROPPED = "dropped"


class IntentionType(Enum):
    """Intention types."""
    ACHIEVE = "achieve"
    MAINTAIN = "maintain"
    PERFORM = "perform"
    AVOID = "avoid"
    QUERY = "query"


class CommitmentLevel(Enum):
    """Commitment levels."""
    TENTATIVE = 1
    WEAK = 2
    MODERATE = 3
    STRONG = 4
    ABSOLUTE = 5


class CommitmentStrategy(Enum):
    """Commitment strategies."""
    BLIND = "blind"
    SINGLE_MINDED = "single_minded"
    OPEN_MINDED = "open_minded"


class DropReason(Enum):
    """Reasons for dropping intention."""
    ACHIEVED = "achieved"
    IMPOSSIBLE = "impossible"
    SUPERSEDED = "superseded"
    TIMEOUT = "timeout"
    CONFLICT = "conflict"
    MANUAL = "manual"


class ExecutionPhase(Enum):
    """Execution phases."""
    PLANNING = "planning"
    INITIALIZING = "initializing"
    RUNNING = "running"
    MONITORING = "monitoring"
    COMPLETING = "completing"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Intention:
    """An intention."""
    intention_id: str = ""
    content: str = ""
    intention_type: IntentionType = IntentionType.ACHIEVE
    status: IntentionStatus = IntentionStatus.PENDING
    commitment: CommitmentLevel = CommitmentLevel.MODERATE
    priority: int = 5
    desire_id: Optional[str] = None
    plan_id: Optional[str] = None
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    drop_reason: Optional[DropReason] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.intention_id:
            self.intention_id = str(uuid.uuid4())[:8]

    def __hash__(self):
        return hash(self.intention_id)

    def __lt__(self, other: "Intention") -> bool:
        return self.priority > other.priority


@dataclass
class Plan:
    """A plan for achieving an intention."""
    plan_id: str = ""
    intention_id: str = ""
    name: str = ""
    steps: List[str] = field(default_factory=list)
    current_step: int = 0
    context_conditions: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    is_applicable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())[:8]


@dataclass
class IntentionStack:
    """Stack of intentions for an agent."""
    agent_id: str = ""
    intentions: List[str] = field(default_factory=list)
    capacity: int = 10

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = str(uuid.uuid4())[:8]

    def push(self, intention_id: str) -> bool:
        if len(self.intentions) >= self.capacity:
            return False
        self.intentions.append(intention_id)
        return True

    def pop(self) -> Optional[str]:
        if self.intentions:
            return self.intentions.pop()
        return None

    def top(self) -> Optional[str]:
        if self.intentions:
            return self.intentions[-1]
        return None

    @property
    def size(self) -> int:
        return len(self.intentions)

    @property
    def is_empty(self) -> bool:
        return len(self.intentions) == 0

    @property
    def is_full(self) -> bool:
        return len(self.intentions) >= self.capacity


@dataclass
class ExecutionContext:
    """Execution context for an intention."""
    intention_id: str = ""
    plan_id: str = ""
    phase: ExecutionPhase = ExecutionPhase.PLANNING
    step_results: List[Any] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class IntentionStats:
    """Intention statistics."""
    total_intentions: int = 0
    active_intentions: int = 0
    completed_intentions: int = 0
    failed_intentions: int = 0
    dropped_intentions: int = 0
    avg_completion_time: float = 0.0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# INTENTION MANAGER
# =============================================================================

class IntentionManager:
    """Manage intentions."""

    def __init__(self):
        self._intentions: Dict[str, Intention] = {}
        self._by_status: Dict[IntentionStatus, Set[str]] = defaultdict(set)
        self._by_type: Dict[IntentionType, Set[str]] = defaultdict(set)

    def add(self, intention: Intention) -> bool:
        """Add an intention."""
        if intention.intention_id in self._intentions:
            return False

        self._intentions[intention.intention_id] = intention
        self._by_status[intention.status].add(intention.intention_id)
        self._by_type[intention.intention_type].add(intention.intention_id)

        return True

    def remove(self, intention_id: str) -> Optional[Intention]:
        """Remove an intention."""
        intention = self._intentions.pop(intention_id, None)

        if intention:
            self._by_status[intention.status].discard(intention_id)
            self._by_type[intention.intention_type].discard(intention_id)

        return intention

    def get(self, intention_id: str) -> Optional[Intention]:
        """Get an intention."""
        return self._intentions.get(intention_id)

    def update_status(
        self,
        intention_id: str,
        new_status: IntentionStatus
    ) -> bool:
        """Update intention status."""
        intention = self._intentions.get(intention_id)
        if not intention:
            return False

        old_status = intention.status

        self._by_status[old_status].discard(intention_id)
        self._by_status[new_status].add(intention_id)

        intention.status = new_status

        if new_status == IntentionStatus.ACTIVE:
            intention.started_at = datetime.now()
        elif new_status in [IntentionStatus.COMPLETED, IntentionStatus.FAILED, IntentionStatus.DROPPED]:
            intention.completed_at = datetime.now()

        return True

    def by_status(self, status: IntentionStatus) -> List[Intention]:
        """Get intentions by status."""
        ids = self._by_status.get(status, set())
        return [self._intentions[iid] for iid in ids if iid in self._intentions]

    def by_type(self, intention_type: IntentionType) -> List[Intention]:
        """Get intentions by type."""
        ids = self._by_type.get(intention_type, set())
        return [self._intentions[iid] for iid in ids if iid in self._intentions]

    def active(self) -> List[Intention]:
        """Get active intentions."""
        return self.by_status(IntentionStatus.ACTIVE)

    def pending(self) -> List[Intention]:
        """Get pending intentions."""
        return self.by_status(IntentionStatus.PENDING)

    def all(self) -> List[Intention]:
        """Get all intentions."""
        return list(self._intentions.values())

    def count(self) -> int:
        """Count intentions."""
        return len(self._intentions)


# =============================================================================
# PLAN LIBRARY
# =============================================================================

class PlanLibrary:
    """Library of plans."""

    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._by_intention: Dict[str, List[str]] = defaultdict(list)
        self._templates: Dict[str, Callable[[Intention], Plan]] = {}

    def add_plan(self, plan: Plan) -> None:
        """Add a plan."""
        self._plans[plan.plan_id] = plan
        self._by_intention[plan.intention_id].append(plan.plan_id)

    def remove_plan(self, plan_id: str) -> Optional[Plan]:
        """Remove a plan."""
        plan = self._plans.pop(plan_id, None)

        if plan:
            self._by_intention[plan.intention_id].remove(plan_id)

        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan."""
        return self._plans.get(plan_id)

    def plans_for_intention(self, intention_id: str) -> List[Plan]:
        """Get plans for an intention."""
        plan_ids = self._by_intention.get(intention_id, [])
        return [self._plans[pid] for pid in plan_ids if pid in self._plans]

    def register_template(
        self,
        name: str,
        template: Callable[[Intention], Plan]
    ) -> None:
        """Register a plan template."""
        self._templates[name] = template

    def create_from_template(
        self,
        template_name: str,
        intention: Intention
    ) -> Optional[Plan]:
        """Create a plan from template."""
        template = self._templates.get(template_name)
        if template:
            plan = template(intention)
            self.add_plan(plan)
            return plan
        return None

    def applicable_plans(
        self,
        intention: Intention,
        context: Dict[str, Any]
    ) -> List[Plan]:
        """Get applicable plans for intention."""
        plans = self.plans_for_intention(intention.intention_id)

        applicable = []

        for plan in plans:
            if not plan.is_applicable:
                continue

            conditions_met = True

            for condition in plan.context_conditions:
                if condition not in context or not context[condition]:
                    conditions_met = False
                    break

            if conditions_met:
                applicable.append(plan)

        return applicable


# =============================================================================
# COMMITMENT HANDLER
# =============================================================================

class CommitmentHandler:
    """Handle commitment strategies."""

    def __init__(self, strategy: CommitmentStrategy = CommitmentStrategy.OPEN_MINDED):
        self._strategy = strategy

    @property
    def strategy(self) -> CommitmentStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, value: CommitmentStrategy) -> None:
        self._strategy = value

    def should_drop(
        self,
        intention: Intention,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[DropReason]]:
        """Check if intention should be dropped."""
        if intention.deadline:
            if datetime.now() > intention.deadline:
                return True, DropReason.TIMEOUT

        if context.get("achieved", False):
            return True, DropReason.ACHIEVED

        if context.get("impossible", False):
            return True, DropReason.IMPOSSIBLE

        if self._strategy == CommitmentStrategy.BLIND:
            return False, None

        if self._strategy == CommitmentStrategy.SINGLE_MINDED:
            if context.get("achieved", False):
                return True, DropReason.ACHIEVED
            return False, None

        if self._strategy == CommitmentStrategy.OPEN_MINDED:
            if context.get("better_alternative", False):
                return True, DropReason.SUPERSEDED

            if context.get("desire_dropped", False):
                return True, DropReason.MANUAL

            if context.get("conflict_detected", False):
                if intention.commitment.value < CommitmentLevel.STRONG.value:
                    return True, DropReason.CONFLICT

        return False, None

    def should_reconsider(
        self,
        intention: Intention,
        context: Dict[str, Any]
    ) -> bool:
        """Check if intention should be reconsidered."""
        if self._strategy == CommitmentStrategy.BLIND:
            return False

        if context.get("new_opportunity", False):
            return True

        if context.get("resource_scarcity", False):
            if intention.commitment.value < CommitmentLevel.ABSOLUTE.value:
                return True

        return False


# =============================================================================
# INTENTION EXECUTOR
# =============================================================================

class IntentionExecutor:
    """Execute intentions with plans."""

    def __init__(self):
        self._contexts: Dict[str, ExecutionContext] = {}
        self._step_handlers: Dict[str, Callable] = {}

    def register_step_handler(
        self,
        step_type: str,
        handler: Callable
    ) -> None:
        """Register a step handler."""
        self._step_handlers[step_type] = handler

    def start_execution(
        self,
        intention: Intention,
        plan: Plan
    ) -> ExecutionContext:
        """Start intention execution."""
        context = ExecutionContext(
            intention_id=intention.intention_id,
            plan_id=plan.plan_id,
            phase=ExecutionPhase.INITIALIZING
        )

        self._contexts[intention.intention_id] = context

        return context

    async def execute_step(
        self,
        plan: Plan,
        context: ExecutionContext
    ) -> Tuple[bool, Any]:
        """Execute current step."""
        if plan.current_step >= len(plan.steps):
            return False, None

        step = plan.steps[plan.current_step]

        handler = self._step_handlers.get(step)

        if handler:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(context.variables)
            else:
                result = handler(context.variables)
        else:
            await asyncio.sleep(0.01)
            result = {"step": step, "executed": True}

        context.step_results.append(result)
        context.last_update = datetime.now()

        plan.current_step += 1

        return True, result

    async def execute_plan(
        self,
        intention: Intention,
        plan: Plan
    ) -> Tuple[bool, List[Any]]:
        """Execute entire plan."""
        context = self.start_execution(intention, plan)
        context.phase = ExecutionPhase.RUNNING

        results = []

        while plan.current_step < len(plan.steps):
            success, result = await self.execute_step(plan, context)

            if not success:
                break

            results.append(result)

        context.phase = ExecutionPhase.COMPLETING

        return plan.current_step == len(plan.steps), results

    def get_context(self, intention_id: str) -> Optional[ExecutionContext]:
        """Get execution context."""
        return self._contexts.get(intention_id)

    def get_progress(self, intention_id: str, plan: Plan) -> float:
        """Get execution progress."""
        if not plan.steps:
            return 1.0

        return plan.current_step / len(plan.steps)


# =============================================================================
# INTENTION FILTER
# =============================================================================

class IntentionFilter:
    """Filter and select intentions."""

    def __init__(self):
        self._rules: List[Callable[[Intention], bool]] = []
        self._scorers: List[Callable[[Intention], float]] = []

    def add_filter_rule(
        self,
        rule: Callable[[Intention], bool]
    ) -> None:
        """Add a filter rule."""
        self._rules.append(rule)

    def add_scorer(
        self,
        scorer: Callable[[Intention], float]
    ) -> None:
        """Add a scorer."""
        self._scorers.append(scorer)

    def filter(self, intentions: List[Intention]) -> List[Intention]:
        """Filter intentions."""
        filtered = intentions

        for rule in self._rules:
            filtered = [i for i in filtered if rule(i)]

        return filtered

    def score(self, intention: Intention) -> float:
        """Score an intention."""
        if not self._scorers:
            return float(intention.priority)

        total = 0.0

        for scorer in self._scorers:
            total += scorer(intention)

        return total / len(self._scorers)

    def rank(self, intentions: List[Intention]) -> List[Intention]:
        """Rank intentions by score."""
        scored = [(i, self.score(i)) for i in intentions]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [i for i, _ in scored]

    def select_best(
        self,
        intentions: List[Intention],
        count: int = 1
    ) -> List[Intention]:
        """Select best intentions."""
        filtered = self.filter(intentions)
        ranked = self.rank(filtered)
        return ranked[:count]


# =============================================================================
# INTENTION ENGINE
# =============================================================================

class IntentionEngine:
    """
    Intention Engine for BAEL.

    Agent intention and commitment management.
    """

    def __init__(self, strategy: CommitmentStrategy = CommitmentStrategy.OPEN_MINDED):
        self._manager = IntentionManager()
        self._library = PlanLibrary()
        self._commitment = CommitmentHandler(strategy)
        self._executor = IntentionExecutor()
        self._filter = IntentionFilter()

        self._stacks: Dict[str, IntentionStack] = {}

        self._stats = IntentionStats()

    def adopt_intention(
        self,
        content: str,
        intention_type: IntentionType = IntentionType.ACHIEVE,
        commitment: CommitmentLevel = CommitmentLevel.MODERATE,
        priority: int = 5,
        desire_id: Optional[str] = None,
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
        deadline: Optional[datetime] = None
    ) -> Intention:
        """Adopt a new intention."""
        intention = Intention(
            content=content,
            intention_type=intention_type,
            commitment=commitment,
            priority=priority,
            desire_id=desire_id,
            preconditions=preconditions or [],
            postconditions=postconditions or [],
            deadline=deadline
        )

        self._manager.add(intention)

        self._update_stats()

        return intention

    def drop_intention(
        self,
        intention_id: str,
        reason: DropReason = DropReason.MANUAL
    ) -> bool:
        """Drop an intention."""
        intention = self._manager.get(intention_id)
        if not intention:
            return False

        intention.drop_reason = reason
        self._manager.update_status(intention_id, IntentionStatus.DROPPED)

        self._update_stats()

        return True

    def activate_intention(self, intention_id: str) -> bool:
        """Activate an intention."""
        return self._manager.update_status(intention_id, IntentionStatus.ACTIVE)

    def suspend_intention(self, intention_id: str) -> bool:
        """Suspend an intention."""
        return self._manager.update_status(intention_id, IntentionStatus.SUSPENDED)

    def complete_intention(self, intention_id: str) -> bool:
        """Mark intention as completed."""
        success = self._manager.update_status(intention_id, IntentionStatus.COMPLETED)

        if success:
            self._update_stats()

        return success

    def fail_intention(self, intention_id: str) -> bool:
        """Mark intention as failed."""
        success = self._manager.update_status(intention_id, IntentionStatus.FAILED)

        if success:
            self._update_stats()

        return success

    def add_plan(
        self,
        intention_id: str,
        name: str,
        steps: List[str],
        context_conditions: Optional[List[str]] = None
    ) -> Optional[Plan]:
        """Add a plan for an intention."""
        intention = self._manager.get(intention_id)
        if not intention:
            return None

        plan = Plan(
            intention_id=intention_id,
            name=name,
            steps=steps,
            context_conditions=context_conditions or []
        )

        self._library.add_plan(plan)

        return plan

    def get_plans(self, intention_id: str) -> List[Plan]:
        """Get plans for an intention."""
        return self._library.plans_for_intention(intention_id)

    def select_plan(
        self,
        intention_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Plan]:
        """Select applicable plan for intention."""
        intention = self._manager.get(intention_id)
        if not intention:
            return None

        plans = self._library.applicable_plans(intention, context or {})

        if plans:
            return plans[0]

        return None

    def bind_plan(self, intention_id: str, plan_id: str) -> bool:
        """Bind a plan to an intention."""
        intention = self._manager.get(intention_id)
        plan = self._library.get_plan(plan_id)

        if not intention or not plan:
            return False

        intention.plan_id = plan_id

        return True

    async def execute_intention(
        self,
        intention_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[Any]]:
        """Execute an intention's plan."""
        intention = self._manager.get(intention_id)
        if not intention:
            return False, []

        plan = None

        if intention.plan_id:
            plan = self._library.get_plan(intention.plan_id)

        if not plan:
            plan = self.select_plan(intention_id, context)

        if not plan:
            return False, []

        self._manager.update_status(intention_id, IntentionStatus.EXECUTING)

        success, results = await self._executor.execute_plan(intention, plan)

        if success:
            self.complete_intention(intention_id)
        else:
            self.fail_intention(intention_id)

        return success, results

    def register_step_handler(
        self,
        step_type: str,
        handler: Callable
    ) -> None:
        """Register a step handler."""
        self._executor.register_step_handler(step_type, handler)

    def register_plan_template(
        self,
        name: str,
        template: Callable[[Intention], Plan]
    ) -> None:
        """Register a plan template."""
        self._library.register_template(name, template)

    def create_agent_stack(
        self,
        agent_id: str,
        capacity: int = 10
    ) -> IntentionStack:
        """Create intention stack for an agent."""
        stack = IntentionStack(agent_id=agent_id, capacity=capacity)
        self._stacks[agent_id] = stack
        return stack

    def push_to_stack(self, agent_id: str, intention_id: str) -> bool:
        """Push intention to agent's stack."""
        stack = self._stacks.get(agent_id)
        if not stack:
            return False

        return stack.push(intention_id)

    def pop_from_stack(self, agent_id: str) -> Optional[str]:
        """Pop intention from agent's stack."""
        stack = self._stacks.get(agent_id)
        if not stack:
            return None

        return stack.pop()

    def get_top_intention(self, agent_id: str) -> Optional[Intention]:
        """Get top intention for agent."""
        stack = self._stacks.get(agent_id)
        if not stack:
            return None

        top_id = stack.top()
        if top_id:
            return self._manager.get(top_id)

        return None

    def check_commitment(
        self,
        intention_id: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[DropReason]]:
        """Check if intention should be dropped."""
        intention = self._manager.get(intention_id)
        if not intention:
            return False, None

        return self._commitment.should_drop(intention, context)

    def reconsider_intentions(
        self,
        context: Dict[str, Any]
    ) -> List[str]:
        """Reconsider active intentions."""
        to_reconsider = []

        for intention in self._manager.active():
            if self._commitment.should_reconsider(intention, context):
                to_reconsider.append(intention.intention_id)

        return to_reconsider

    def add_filter_rule(
        self,
        rule: Callable[[Intention], bool]
    ) -> None:
        """Add intention filter rule."""
        self._filter.add_filter_rule(rule)

    def add_scorer(
        self,
        scorer: Callable[[Intention], float]
    ) -> None:
        """Add intention scorer."""
        self._filter.add_scorer(scorer)

    def select_intentions(self, count: int = 1) -> List[Intention]:
        """Select best intentions to pursue."""
        pending = self._manager.pending()
        return self._filter.select_best(pending, count)

    def get_intention(self, intention_id: str) -> Optional[Intention]:
        """Get an intention."""
        return self._manager.get(intention_id)

    def get_active(self) -> List[Intention]:
        """Get active intentions."""
        return self._manager.active()

    def get_pending(self) -> List[Intention]:
        """Get pending intentions."""
        return self._manager.pending()

    def get_by_type(self, intention_type: IntentionType) -> List[Intention]:
        """Get intentions by type."""
        return self._manager.by_type(intention_type)

    def set_commitment_strategy(self, strategy: CommitmentStrategy) -> None:
        """Set commitment strategy."""
        self._commitment.strategy = strategy

    def get_execution_context(
        self,
        intention_id: str
    ) -> Optional[ExecutionContext]:
        """Get execution context."""
        return self._executor.get_context(intention_id)

    def get_progress(self, intention_id: str) -> float:
        """Get intention execution progress."""
        intention = self._manager.get(intention_id)
        if not intention or not intention.plan_id:
            return 0.0

        plan = self._library.get_plan(intention.plan_id)
        if not plan:
            return 0.0

        return self._executor.get_progress(intention_id, plan)

    def _update_stats(self) -> None:
        """Update statistics."""
        all_intentions = self._manager.all()

        self._stats.total_intentions = len(all_intentions)
        self._stats.active_intentions = len(self._manager.active())

        self._stats.completed_intentions = len(
            self._manager.by_status(IntentionStatus.COMPLETED)
        )
        self._stats.failed_intentions = len(
            self._manager.by_status(IntentionStatus.FAILED)
        )
        self._stats.dropped_intentions = len(
            self._manager.by_status(IntentionStatus.DROPPED)
        )

        self._stats.by_type = {}
        for intention in all_intentions:
            key = intention.intention_type.value
            self._stats.by_type[key] = self._stats.by_type.get(key, 0) + 1

        self._stats.by_status = {}
        for intention in all_intentions:
            key = intention.status.value
            self._stats.by_status[key] = self._stats.by_status.get(key, 0) + 1

        completed = self._manager.by_status(IntentionStatus.COMPLETED)
        if completed:
            total_time = sum(
                (i.completed_at - i.started_at).total_seconds()
                for i in completed
                if i.started_at and i.completed_at
            )
            self._stats.avg_completion_time = total_time / len(completed)

    @property
    def stats(self) -> IntentionStats:
        """Get statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_intentions": self._stats.total_intentions,
            "active": self._stats.active_intentions,
            "completed": self._stats.completed_intentions,
            "failed": self._stats.failed_intentions,
            "dropped": self._stats.dropped_intentions,
            "plans": len(self._library._plans),
            "agent_stacks": len(self._stacks),
            "by_type": self._stats.by_type,
            "by_status": self._stats.by_status
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Intention Engine."""
    print("=" * 70)
    print("BAEL - INTENTION ENGINE DEMO")
    print("Agent Intention and Commitment Management")
    print("=" * 70)
    print()

    engine = IntentionEngine(strategy=CommitmentStrategy.OPEN_MINDED)

    # 1. Adopt Intentions
    print("1. ADOPT INTENTIONS:")
    print("-" * 40)

    i1 = engine.adopt_intention(
        content="Collect user requirements",
        intention_type=IntentionType.ACHIEVE,
        commitment=CommitmentLevel.STRONG,
        priority=8
    )

    i2 = engine.adopt_intention(
        content="Monitor system health",
        intention_type=IntentionType.MAINTAIN,
        commitment=CommitmentLevel.MODERATE,
        priority=6
    )

    i3 = engine.adopt_intention(
        content="Generate report",
        intention_type=IntentionType.PERFORM,
        commitment=CommitmentLevel.WEAK,
        priority=4
    )

    print(f"   {i1.intention_id}: {i1.content} ({i1.intention_type.value})")
    print(f"   {i2.intention_id}: {i2.content} ({i2.intention_type.value})")
    print(f"   {i3.intention_id}: {i3.content} ({i3.intention_type.value})")
    print()

    # 2. Add Plans
    print("2. ADD PLANS:")
    print("-" * 40)

    plan1 = engine.add_plan(
        i1.intention_id,
        name="Requirements Collection Plan",
        steps=["identify_stakeholders", "schedule_interviews", "conduct_interviews", "document_requirements"],
        context_conditions=["stakeholders_available"]
    )

    plan2 = engine.add_plan(
        i1.intention_id,
        name="Survey-based Collection",
        steps=["design_survey", "distribute_survey", "collect_responses", "analyze_results"],
        context_conditions=["survey_tool_available"]
    )

    print(f"   Plan 1: {plan1.name} ({len(plan1.steps)} steps)")
    print(f"   Plan 2: {plan2.name} ({len(plan2.steps)} steps)")
    print()

    # 3. Select and Bind Plan
    print("3. SELECT AND BIND PLAN:")
    print("-" * 40)

    context = {"stakeholders_available": True, "survey_tool_available": False}

    selected = engine.select_plan(i1.intention_id, context)

    if selected:
        engine.bind_plan(i1.intention_id, selected.plan_id)
        print(f"   Selected: {selected.name}")
        print(f"   Bound to intention: {i1.intention_id}")
    print()

    # 4. Intention Stack
    print("4. INTENTION STACK:")
    print("-" * 40)

    stack = engine.create_agent_stack("agent_1", capacity=5)

    engine.push_to_stack("agent_1", i1.intention_id)
    engine.push_to_stack("agent_1", i2.intention_id)
    engine.push_to_stack("agent_1", i3.intention_id)

    print(f"   Stack size: {stack.size}")

    top = engine.get_top_intention("agent_1")
    if top:
        print(f"   Top intention: {top.content}")
    print()

    # 5. Execute Intention
    print("5. EXECUTE INTENTION:")
    print("-" * 40)

    async def identify_stakeholders(variables: Dict) -> Dict:
        await asyncio.sleep(0.01)
        return {"stakeholders": ["user", "admin", "manager"]}

    async def schedule_interviews(variables: Dict) -> Dict:
        await asyncio.sleep(0.01)
        return {"scheduled": True, "count": 3}

    async def conduct_interviews(variables: Dict) -> Dict:
        await asyncio.sleep(0.02)
        return {"completed": 3, "notes": "Good feedback"}

    async def document_requirements(variables: Dict) -> Dict:
        await asyncio.sleep(0.01)
        return {"document": "requirements.md"}

    engine.register_step_handler("identify_stakeholders", identify_stakeholders)
    engine.register_step_handler("schedule_interviews", schedule_interviews)
    engine.register_step_handler("conduct_interviews", conduct_interviews)
    engine.register_step_handler("document_requirements", document_requirements)

    engine.activate_intention(i1.intention_id)

    success, results = await engine.execute_intention(i1.intention_id, context)

    print(f"   Intention: {i1.content}")
    print(f"   Success: {success}")
    print(f"   Steps Completed: {len(results)}")
    for i, result in enumerate(results):
        print(f"      Step {i+1}: {result}")
    print()

    # 6. Commitment Checking
    print("6. COMMITMENT CHECKING:")
    print("-" * 40)

    check_context = {"achieved": False, "impossible": False}

    should_drop, reason = engine.check_commitment(i2.intention_id, check_context)

    print(f"   Intention: {i2.content}")
    print(f"   Should Drop: {should_drop}")
    print(f"   Reason: {reason}")

    check_context2 = {"achieved": False, "better_alternative": True}

    should_drop2, reason2 = engine.check_commitment(i3.intention_id, check_context2)

    print(f"   Intention: {i3.content}")
    print(f"   Should Drop: {should_drop2}")
    print(f"   Reason: {reason2.value if reason2 else None}")
    print()

    # 7. Intention Filtering
    print("7. INTENTION FILTERING:")
    print("-" * 40)

    i4 = engine.adopt_intention(
        content="Process data batch",
        priority=9
    )

    i5 = engine.adopt_intention(
        content="Clean up temp files",
        priority=2
    )

    engine.add_filter_rule(lambda i: i.priority > 3)

    selected = engine.select_intentions(count=2)

    print(f"   Pending intentions: {len(engine.get_pending())}")
    print(f"   Selected (priority > 3):")
    for intention in selected:
        print(f"      {intention.content} (priority: {intention.priority})")
    print()

    # 8. Plan Templates
    print("8. PLAN TEMPLATES:")
    print("-" * 40)

    def data_processing_template(intention: Intention) -> Plan:
        return Plan(
            intention_id=intention.intention_id,
            name="Standard Data Processing",
            steps=["load_data", "validate_data", "transform_data", "save_data"]
        )

    engine.register_plan_template("data_processing", data_processing_template)

    plan = engine._library.create_from_template("data_processing", i4)

    if plan:
        print(f"   Created from template: {plan.name}")
        print(f"   Steps: {plan.steps}")
    print()

    # 9. Drop Intention
    print("9. DROP INTENTION:")
    print("-" * 40)

    engine.drop_intention(i5.intention_id, DropReason.SUPERSEDED)

    dropped = engine.get_intention(i5.intention_id)

    print(f"   Intention: {dropped.content}")
    print(f"   Status: {dropped.status.value}")
    print(f"   Drop Reason: {dropped.drop_reason.value}")
    print()

    # 10. Reconsider Intentions
    print("10. RECONSIDER INTENTIONS:")
    print("-" * 40)

    engine.activate_intention(i2.intention_id)

    recon_context = {"new_opportunity": True, "resource_scarcity": False}

    to_reconsider = engine.reconsider_intentions(recon_context)

    print(f"   Context: {recon_context}")
    print(f"   To Reconsider: {len(to_reconsider)}")
    for iid in to_reconsider:
        intention = engine.get_intention(iid)
        if intention:
            print(f"      {intention.content}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Intentions: {stats.total_intentions}")
    print(f"   Active: {stats.active_intentions}")
    print(f"   Completed: {stats.completed_intentions}")
    print(f"   Failed: {stats.failed_intentions}")
    print(f"   Dropped: {stats.dropped_intentions}")
    print(f"   By Type: {stats.by_type}")
    print(f"   By Status: {stats.by_status}")
    print()

    # 12. Engine Summary
    print("12. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Total: {summary['total_intentions']}")
    print(f"   Plans: {summary['plans']}")
    print(f"   Agent Stacks: {summary['agent_stacks']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Intention Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
