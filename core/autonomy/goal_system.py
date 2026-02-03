#!/usr/bin/env python3
"""
BAEL - Autonomous Goal System
Self-directed goal management and achievement.

Features:
- Goal hierarchy management
- Automatic sub-goal generation
- Progress tracking
- Adaptive replanning
- Resource allocation
- Motivation and priority systems
"""

import asyncio
import heapq
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class GoalStatus(Enum):
    """Goal completion status."""
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalPriority(Enum):
    """Goal priority levels."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1


class GoalType(Enum):
    """Types of goals."""
    ACHIEVEMENT = "achievement"  # One-time accomplishment
    MAINTENANCE = "maintenance"  # Ongoing requirement
    LEARNING = "learning"  # Skill acquisition
    EXPLORATION = "exploration"  # Discovery
    OPTIMIZATION = "optimization"  # Improvement


@dataclass
class Resource:
    """Resource for goal execution."""
    name: str
    capacity: float
    used: float = 0.0
    renewable: bool = True
    recharge_rate: float = 0.0  # Per hour

    @property
    def available(self) -> float:
        return self.capacity - self.used

    def allocate(self, amount: float) -> bool:
        if amount <= self.available:
            self.used += amount
            return True
        return False

    def release(self, amount: float) -> None:
        self.used = max(0, self.used - amount)


@dataclass
class Goal:
    """Goal definition."""
    id: str
    name: str
    description: str
    goal_type: GoalType = GoalType.ACHIEVEMENT
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PENDING
    progress: float = 0.0  # 0-1
    parent_id: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    required_resources: Dict[str, float] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    success_criteria: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def priority_value(self) -> int:
        return self.priority.value

    @property
    def is_terminal(self) -> bool:
        return self.status in [GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.CANCELLED]

    @property
    def is_actionable(self) -> bool:
        return self.status in [GoalStatus.PENDING, GoalStatus.ACTIVE]


@dataclass
class GoalProgress:
    """Progress update for a goal."""
    goal_id: str
    progress: float
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    """Step in a goal execution plan."""
    id: str
    description: str
    goal_id: str
    order: int
    estimated_duration: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    resources_needed: Dict[str, float] = field(default_factory=dict)
    completed: bool = False
    result: Optional[Any] = None


# =============================================================================
# GOAL HIERARCHY
# =============================================================================

class GoalHierarchy:
    """Manage goal hierarchy."""

    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.root_goals: Set[str] = set()

    def add_goal(self, goal: Goal) -> None:
        """Add goal to hierarchy."""
        self.goals[goal.id] = goal

        if goal.parent_id:
            parent = self.goals.get(goal.parent_id)
            if parent and goal.id not in parent.sub_goals:
                parent.sub_goals.append(goal.id)
        else:
            self.root_goals.add(goal.id)

    def remove_goal(self, goal_id: str) -> Optional[Goal]:
        """Remove goal from hierarchy."""
        if goal_id not in self.goals:
            return None

        goal = self.goals.pop(goal_id)

        # Remove from parent
        if goal.parent_id:
            parent = self.goals.get(goal.parent_id)
            if parent and goal_id in parent.sub_goals:
                parent.sub_goals.remove(goal_id)
        else:
            self.root_goals.discard(goal_id)

        # Handle sub-goals
        for sub_id in goal.sub_goals:
            sub_goal = self.goals.get(sub_id)
            if sub_goal:
                sub_goal.parent_id = goal.parent_id
                if goal.parent_id:
                    parent = self.goals.get(goal.parent_id)
                    if parent:
                        parent.sub_goals.append(sub_id)
                else:
                    self.root_goals.add(sub_id)

        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get goal by ID."""
        return self.goals.get(goal_id)

    def get_sub_goals(self, goal_id: str) -> List[Goal]:
        """Get direct sub-goals."""
        goal = self.goals.get(goal_id)
        if not goal:
            return []
        return [self.goals[sid] for sid in goal.sub_goals if sid in self.goals]

    def get_all_descendants(self, goal_id: str) -> List[Goal]:
        """Get all descendant goals."""
        descendants = []
        to_visit = [goal_id]

        while to_visit:
            current_id = to_visit.pop()
            goal = self.goals.get(current_id)
            if goal:
                for sub_id in goal.sub_goals:
                    if sub_id in self.goals:
                        descendants.append(self.goals[sub_id])
                        to_visit.append(sub_id)

        return descendants

    def get_ancestors(self, goal_id: str) -> List[Goal]:
        """Get all ancestor goals."""
        ancestors = []
        goal = self.goals.get(goal_id)

        while goal and goal.parent_id:
            parent = self.goals.get(goal.parent_id)
            if parent:
                ancestors.append(parent)
                goal = parent
            else:
                break

        return ancestors

    def calculate_aggregate_progress(self, goal_id: str) -> float:
        """Calculate aggregate progress including sub-goals."""
        goal = self.goals.get(goal_id)
        if not goal:
            return 0.0

        if not goal.sub_goals:
            return goal.progress

        sub_progresses = [
            self.calculate_aggregate_progress(sid)
            for sid in goal.sub_goals
            if sid in self.goals
        ]

        if not sub_progresses:
            return goal.progress

        return sum(sub_progresses) / len(sub_progresses)

    def to_tree(self, goal_id: str = None, depth: int = 0) -> str:
        """Generate tree representation."""
        lines = []

        if goal_id is None:
            for root_id in sorted(self.root_goals):
                lines.append(self.to_tree(root_id, 0))
        else:
            goal = self.goals.get(goal_id)
            if goal:
                prefix = "  " * depth + ("├── " if depth > 0 else "")
                status_icon = {
                    GoalStatus.PENDING: "⏳",
                    GoalStatus.ACTIVE: "🔄",
                    GoalStatus.BLOCKED: "🚫",
                    GoalStatus.COMPLETED: "✅",
                    GoalStatus.FAILED: "❌",
                    GoalStatus.CANCELLED: "🚫"
                }.get(goal.status, "")

                lines.append(f"{prefix}{status_icon} {goal.name} ({goal.progress:.0%})")

                for sub_id in goal.sub_goals:
                    lines.append(self.to_tree(sub_id, depth + 1))

        return "\n".join(lines)


# =============================================================================
# GOAL GENERATOR
# =============================================================================

class GoalDecomposer:
    """Decompose goals into sub-goals."""

    def __init__(self):
        self.templates: Dict[GoalType, List[Dict[str, Any]]] = {
            GoalType.ACHIEVEMENT: [
                {"pattern": "understand_{topic}", "weight": 0.2},
                {"pattern": "plan_{topic}", "weight": 0.2},
                {"pattern": "execute_{topic}", "weight": 0.5},
                {"pattern": "verify_{topic}", "weight": 0.1}
            ],
            GoalType.LEARNING: [
                {"pattern": "research_{topic}", "weight": 0.2},
                {"pattern": "study_{topic}", "weight": 0.3},
                {"pattern": "practice_{topic}", "weight": 0.3},
                {"pattern": "apply_{topic}", "weight": 0.2}
            ],
            GoalType.OPTIMIZATION: [
                {"pattern": "measure_{topic}", "weight": 0.2},
                {"pattern": "analyze_{topic}", "weight": 0.3},
                {"pattern": "optimize_{topic}", "weight": 0.3},
                {"pattern": "validate_{topic}", "weight": 0.2}
            ]
        }

    async def decompose(
        self,
        goal: Goal,
        context: Dict[str, Any] = None
    ) -> List[Goal]:
        """Decompose goal into sub-goals."""
        context = context or {}
        sub_goals = []

        templates = self.templates.get(goal.goal_type, [])

        topic = goal.name.lower().replace(" ", "_")

        for i, template in enumerate(templates):
            pattern = template["pattern"]
            weight = template["weight"]

            sub_name = pattern.format(topic=topic).replace("_", " ").title()

            sub_goal = Goal(
                id=str(uuid4()),
                name=sub_name,
                description=f"Sub-goal of {goal.name}: {sub_name}",
                goal_type=goal.goal_type,
                priority=goal.priority,
                parent_id=goal.id,
                metadata={"weight": weight, "order": i}
            )

            # Set dependencies
            if i > 0 and sub_goals:
                sub_goal.dependencies.append(sub_goals[-1].id)

            sub_goals.append(sub_goal)

        return sub_goals

    async def suggest_goals(
        self,
        context: Dict[str, Any]
    ) -> List[Goal]:
        """Suggest new goals based on context."""
        suggestions = []

        # Analyze context for opportunities
        if context.get("knowledge_gaps"):
            for gap in context["knowledge_gaps"][:3]:
                suggestions.append(Goal(
                    id=str(uuid4()),
                    name=f"Learn {gap}",
                    description=f"Fill knowledge gap: {gap}",
                    goal_type=GoalType.LEARNING,
                    priority=GoalPriority.MEDIUM
                ))

        if context.get("performance_issues"):
            for issue in context["performance_issues"][:3]:
                suggestions.append(Goal(
                    id=str(uuid4()),
                    name=f"Improve {issue}",
                    description=f"Address performance issue: {issue}",
                    goal_type=GoalType.OPTIMIZATION,
                    priority=GoalPriority.HIGH
                ))

        if context.get("opportunities"):
            for opp in context["opportunities"][:3]:
                suggestions.append(Goal(
                    id=str(uuid4()),
                    name=f"Explore {opp}",
                    description=f"Investigate opportunity: {opp}",
                    goal_type=GoalType.EXPLORATION,
                    priority=GoalPriority.LOW
                ))

        return suggestions


# =============================================================================
# GOAL SCHEDULER
# =============================================================================

class GoalScheduler:
    """Schedule goals for execution."""

    def __init__(self):
        self.queue: List[Tuple[int, str, str]] = []  # (priority, timestamp, goal_id)
        self.resources: Dict[str, Resource] = {}

    def add_resource(self, resource: Resource) -> None:
        """Add available resource."""
        self.resources[resource.name] = resource

    def schedule(
        self,
        goals: List[Goal],
        hierarchy: GoalHierarchy
    ) -> List[str]:
        """Schedule goals for execution, return ordered list."""
        # Clear queue
        self.queue = []

        # Filter actionable goals
        actionable = [g for g in goals if g.is_actionable]

        for goal in actionable:
            # Check dependencies
            deps_satisfied = all(
                hierarchy.get_goal(dep_id) and
                hierarchy.get_goal(dep_id).status == GoalStatus.COMPLETED
                for dep_id in goal.dependencies
            )

            if not deps_satisfied:
                continue

            # Check resources
            resources_available = all(
                self.resources.get(res) and
                self.resources[res].available >= amount
                for res, amount in goal.required_resources.items()
            )

            if not resources_available:
                goal.status = GoalStatus.BLOCKED
                continue

            # Calculate priority score
            priority_score = self._calculate_priority(goal)

            # Add to heap (negative for max-heap behavior)
            heapq.heappush(
                self.queue,
                (-priority_score, goal.created_at.isoformat(), goal.id)
            )

        # Extract ordered list
        scheduled = []
        while self.queue:
            _, _, goal_id = heapq.heappop(self.queue)
            scheduled.append(goal_id)

        return scheduled

    def _calculate_priority(self, goal: Goal) -> float:
        """Calculate dynamic priority score."""
        score = goal.priority_value * 10

        # Urgency from deadline
        if goal.deadline:
            time_remaining = (goal.deadline - datetime.now()).total_seconds()
            if time_remaining > 0:
                urgency = max(0, 1 - (time_remaining / (7 * 24 * 3600)))  # 1 week scale
                score += urgency * 20
            else:
                score += 50  # Overdue

        # Progress bonus (momentum)
        if 0 < goal.progress < 1:
            score += goal.progress * 5

        return score


# =============================================================================
# GOAL EXECUTOR
# =============================================================================

class GoalExecutor:
    """Execute goals and track progress."""

    def __init__(self):
        self.action_handlers: Dict[str, Callable] = {}
        self.progress_callbacks: List[Callable] = []

    def register_action(
        self,
        action_type: str,
        handler: Callable
    ) -> None:
        """Register action handler."""
        self.action_handlers[action_type] = handler

    def on_progress(self, callback: Callable) -> None:
        """Register progress callback."""
        self.progress_callbacks.append(callback)

    async def execute(
        self,
        goal: Goal,
        plan: List[PlanStep]
    ) -> GoalProgress:
        """Execute goal plan."""
        goal.status = GoalStatus.ACTIVE
        goal.started_at = datetime.now()

        completed_steps = 0
        total_steps = len(plan)

        for step in sorted(plan, key=lambda s: s.order):
            try:
                # Find matching handler
                handler = None
                for action_type, h in self.action_handlers.items():
                    if action_type.lower() in step.description.lower():
                        handler = h
                        break

                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(step)
                    else:
                        result = handler(step)
                    step.result = result

                step.completed = True
                completed_steps += 1

                # Update progress
                goal.progress = completed_steps / total_steps

                # Notify callbacks
                progress = GoalProgress(
                    goal_id=goal.id,
                    progress=goal.progress,
                    message=f"Completed: {step.description}"
                )

                for callback in self.progress_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(progress)
                        else:
                            callback(progress)
                    except Exception as e:
                        logger.error(f"Progress callback error: {e}")

            except Exception as e:
                logger.error(f"Step execution failed: {e}")
                goal.status = GoalStatus.FAILED
                return GoalProgress(
                    goal_id=goal.id,
                    progress=goal.progress,
                    message=f"Failed at: {step.description}. Error: {str(e)}"
                )

        # Mark completed
        goal.status = GoalStatus.COMPLETED
        goal.progress = 1.0
        goal.completed_at = datetime.now()

        return GoalProgress(
            goal_id=goal.id,
            progress=1.0,
            message="Goal completed successfully"
        )


# =============================================================================
# GOAL REPLANNER
# =============================================================================

class GoalReplanner:
    """Adapt plans when obstacles arise."""

    def __init__(self):
        self.strategies: Dict[str, Callable] = {
            "retry": self._retry_strategy,
            "alternative": self._alternative_strategy,
            "decompose": self._decompose_strategy,
            "escalate": self._escalate_strategy,
            "defer": self._defer_strategy
        }

    async def replan(
        self,
        goal: Goal,
        failure_reason: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create new plan after failure."""
        context = context or {}

        # Analyze failure
        analysis = self._analyze_failure(failure_reason, context)

        # Select strategy
        strategy_name = self._select_strategy(analysis)
        strategy = self.strategies.get(strategy_name)

        if strategy:
            return await strategy(goal, analysis, context)

        return {"action": "abort", "reason": "No viable strategy"}

    def _analyze_failure(
        self,
        reason: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze failure to determine approach."""
        reason_lower = reason.lower()

        return {
            "is_temporary": any(w in reason_lower for w in ["timeout", "busy", "rate"]),
            "is_resource": any(w in reason_lower for w in ["resource", "memory", "quota"]),
            "is_dependency": any(w in reason_lower for w in ["dependency", "requires", "missing"]),
            "is_capability": any(w in reason_lower for w in ["cannot", "unable", "unsupported"]),
            "attempt_count": context.get("attempt_count", 0),
            "original_reason": reason
        }

    def _select_strategy(self, analysis: Dict[str, Any]) -> str:
        """Select replanning strategy."""
        if analysis["is_temporary"] and analysis["attempt_count"] < 3:
            return "retry"
        if analysis["is_resource"]:
            return "defer"
        if analysis["is_dependency"]:
            return "decompose"
        if analysis["is_capability"]:
            return "alternative"
        if analysis["attempt_count"] >= 3:
            return "escalate"
        return "retry"

    async def _retry_strategy(
        self,
        goal: Goal,
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retry with backoff."""
        wait_time = 2 ** analysis["attempt_count"]
        return {
            "action": "retry",
            "wait_seconds": wait_time,
            "max_attempts": 3
        }

    async def _alternative_strategy(
        self,
        goal: Goal,
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find alternative approach."""
        return {
            "action": "alternative",
            "suggestion": f"Find alternative approach for: {goal.name}",
            "original_blocked": True
        }

    async def _decompose_strategy(
        self,
        goal: Goal,
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Break goal into smaller parts."""
        return {
            "action": "decompose",
            "suggestion": "Break goal into smaller achievable parts",
            "focus_on_dependencies": True
        }

    async def _escalate_strategy(
        self,
        goal: Goal,
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Escalate to higher level."""
        return {
            "action": "escalate",
            "reason": "Multiple attempts failed",
            "requires_human": True
        }

    async def _defer_strategy(
        self,
        goal: Goal,
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Defer goal for later."""
        return {
            "action": "defer",
            "wait_until": (datetime.now() + timedelta(hours=1)).isoformat(),
            "reason": "Resource constraints"
        }


# =============================================================================
# AUTONOMOUS GOAL MANAGER
# =============================================================================

class AutonomousGoalManager:
    """Main autonomous goal management system."""

    def __init__(self):
        self.hierarchy = GoalHierarchy()
        self.decomposer = GoalDecomposer()
        self.scheduler = GoalScheduler()
        self.executor = GoalExecutor()
        self.replanner = GoalReplanner()
        self.active_goal: Optional[str] = None

    async def create_goal(
        self,
        name: str,
        description: str,
        goal_type: GoalType = GoalType.ACHIEVEMENT,
        priority: GoalPriority = GoalPriority.MEDIUM,
        parent_id: str = None,
        auto_decompose: bool = True
    ) -> Goal:
        """Create a new goal."""
        goal = Goal(
            id=str(uuid4()),
            name=name,
            description=description,
            goal_type=goal_type,
            priority=priority,
            parent_id=parent_id
        )

        self.hierarchy.add_goal(goal)

        if auto_decompose:
            sub_goals = await self.decomposer.decompose(goal)
            for sub in sub_goals:
                self.hierarchy.add_goal(sub)

        logger.info(f"Created goal: {name}")
        return goal

    async def pursue_goals(self) -> List[GoalProgress]:
        """Pursue scheduled goals."""
        all_goals = list(self.hierarchy.goals.values())
        scheduled = self.scheduler.schedule(all_goals, self.hierarchy)

        progress_list = []

        for goal_id in scheduled[:5]:  # Limit concurrent goals
            goal = self.hierarchy.get_goal(goal_id)
            if not goal:
                continue

            self.active_goal = goal_id

            # Generate plan
            plan = await self._generate_plan(goal)

            # Execute
            try:
                progress = await self.executor.execute(goal, plan)
                progress_list.append(progress)

                # Update parent progress
                if goal.parent_id:
                    parent = self.hierarchy.get_goal(goal.parent_id)
                    if parent:
                        parent.progress = self.hierarchy.calculate_aggregate_progress(parent.id)

            except Exception as e:
                logger.error(f"Goal execution failed: {e}")

                # Attempt replan
                replan = await self.replanner.replan(goal, str(e))

                if replan["action"] == "defer":
                    goal.status = GoalStatus.BLOCKED
                elif replan["action"] == "escalate":
                    goal.status = GoalStatus.BLOCKED
                    goal.metadata["escalated"] = True

        self.active_goal = None
        return progress_list

    async def _generate_plan(self, goal: Goal) -> List[PlanStep]:
        """Generate execution plan for goal."""
        steps = []

        # Get sub-goals
        sub_goals = self.hierarchy.get_sub_goals(goal.id)

        if sub_goals:
            for i, sub in enumerate(sorted(sub_goals, key=lambda g: g.metadata.get("order", 0))):
                steps.append(PlanStep(
                    id=str(uuid4()),
                    description=f"Complete: {sub.name}",
                    goal_id=goal.id,
                    order=i
                ))
        else:
            # Default steps for leaf goals
            steps = [
                PlanStep(
                    id=str(uuid4()),
                    description=f"Analyze: {goal.name}",
                    goal_id=goal.id,
                    order=0
                ),
                PlanStep(
                    id=str(uuid4()),
                    description=f"Execute: {goal.name}",
                    goal_id=goal.id,
                    order=1
                ),
                PlanStep(
                    id=str(uuid4()),
                    description=f"Verify: {goal.name}",
                    goal_id=goal.id,
                    order=2
                )
            ]

        return steps

    def get_status(self) -> Dict[str, Any]:
        """Get goal system status."""
        goals = list(self.hierarchy.goals.values())

        by_status = defaultdict(int)
        for g in goals:
            by_status[g.status.value] += 1

        by_priority = defaultdict(int)
        for g in goals:
            by_priority[g.priority.value] += 1

        return {
            "total_goals": len(goals),
            "root_goals": len(self.hierarchy.root_goals),
            "by_status": dict(by_status),
            "by_priority": dict(by_priority),
            "active_goal": self.active_goal,
            "completed_count": by_status.get("completed", 0),
            "completion_rate": by_status.get("completed", 0) / len(goals) if goals else 0
        }

    def visualize(self) -> str:
        """Visualize goal hierarchy."""
        return self.hierarchy.to_tree()

    async def suggest_next_goals(
        self,
        context: Dict[str, Any] = None
    ) -> List[Goal]:
        """Suggest new goals based on context."""
        return await self.decomposer.suggest_goals(context or {})


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo autonomous goal system."""
    manager = AutonomousGoalManager()

    print("=== Autonomous Goal System Demo ===\n")

    # Register action handler
    async def execute_handler(step: PlanStep):
        await asyncio.sleep(0.1)  # Simulate work
        return f"Completed: {step.description}"

    manager.executor.register_action("execute", execute_handler)
    manager.executor.register_action("analyze", execute_handler)
    manager.executor.register_action("verify", execute_handler)
    manager.executor.register_action("complete", execute_handler)

    # Progress callback
    def on_progress(progress: GoalProgress):
        print(f"  Progress: {progress.progress:.0%} - {progress.message}")

    manager.executor.on_progress(on_progress)

    # 1. Create main goal
    print("1. Creating goals...")
    main_goal = await manager.create_goal(
        name="Build AI Agent",
        description="Create a fully autonomous AI agent",
        goal_type=GoalType.ACHIEVEMENT,
        priority=GoalPriority.HIGH
    )
    print(f"   Created: {main_goal.name}")
    print(f"   Sub-goals: {len(main_goal.sub_goals)}")

    # Create additional goals
    learning_goal = await manager.create_goal(
        name="Learn Python",
        description="Master Python programming",
        goal_type=GoalType.LEARNING,
        priority=GoalPriority.MEDIUM
    )

    # 2. Visualize hierarchy
    print("\n2. Goal Hierarchy:")
    print(manager.visualize())

    # 3. Get status
    print("\n3. Goal System Status:")
    status = manager.get_status()
    print(f"   Total goals: {status['total_goals']}")
    print(f"   By status: {status['by_status']}")

    # 4. Pursue goals
    print("\n4. Pursuing goals...")
    progress_list = await manager.pursue_goals()

    for progress in progress_list:
        goal = manager.hierarchy.get_goal(progress.goal_id)
        if goal:
            print(f"   {goal.name}: {progress.progress:.0%}")

    # 5. Updated hierarchy
    print("\n5. Updated Hierarchy:")
    print(manager.visualize())

    # 6. Final status
    print("\n6. Final Status:")
    status = manager.get_status()
    print(f"   Completed: {status['completed_count']}")
    print(f"   Completion rate: {status['completion_rate']:.0%}")

    # 7. Suggest new goals
    print("\n7. Suggested Goals:")
    suggestions = await manager.suggest_next_goals({
        "knowledge_gaps": ["machine learning", "deployment"],
        "opportunities": ["cloud integration"]
    })
    for s in suggestions[:3]:
        print(f"   - {s.name} ({s.goal_type.value})")


if __name__ == "__main__":
    asyncio.run(demo())
