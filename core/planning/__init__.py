"""
BAEL - Planning System
Strategic, autonomous, and hierarchical task planning.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.Planning")


class PlanStatus(Enum):
    """Plan execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanPriority(Enum):
    """Plan priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PlanStep:
    """A single step in a plan."""
    id: str
    name: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    result: Optional[Any] = None


@dataclass
class Plan:
    """A complete execution plan."""
    id: str
    name: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    priority: PlanPriority = PlanPriority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)


class Planner:
    """
    BAEL's unified planning system.

    Combines:
    - Strategic planning for high-level goals
    - Task planning for execution steps
    - Hierarchical planning for complex decomposition
    """

    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._strategic_planner = None
        self._task_planner = None

    def _ensure_planners(self):
        """Lazy load specialized planners."""
        if self._strategic_planner is None:
            try:
                from core.planning.strategic_planner import StrategicPlanner
                self._strategic_planner = StrategicPlanner()
            except ImportError:
                logger.warning("Strategic planner not available")

        if self._task_planner is None:
            try:
                from core.planning.autonomous_planner import TaskPlanner
                self._task_planner = TaskPlanner()
            except ImportError:
                logger.warning("Task planner not available")

    async def create_plan(
        self,
        goal: str,
        context: Dict[str, Any] = None,
        max_steps: int = 10
    ) -> Plan:
        """
        Create a plan to achieve a goal.

        Args:
            goal: The goal to achieve
            context: Additional context for planning
            max_steps: Maximum number of steps

        Returns:
            A Plan object with steps to achieve the goal
        """
        import uuid

        self._ensure_planners()

        plan_id = str(uuid.uuid4())[:8]

        # Decompose goal into steps
        steps = await self._decompose_goal(goal, context or {}, max_steps)

        plan = Plan(
            id=plan_id,
            name=f"Plan for: {goal[:50]}",
            goal=goal,
            steps=steps
        )

        self._plans[plan_id] = plan
        logger.info(f"Created plan {plan_id} with {len(steps)} steps")

        return plan

    async def _decompose_goal(
        self,
        goal: str,
        context: Dict[str, Any],
        max_steps: int
    ) -> List[PlanStep]:
        """Decompose a goal into executable steps."""
        # Default decomposition strategy
        steps = []

        # Analyze goal
        steps.append(PlanStep(
            id="analyze",
            name="Analyze Goal",
            description=f"Understand requirements for: {goal[:100]}",
            action="analyze"
        ))

        # Research if needed
        if any(word in goal.lower() for word in ["find", "search", "research", "learn"]):
            steps.append(PlanStep(
                id="research",
                name="Research",
                description="Gather relevant information",
                action="research",
                dependencies=["analyze"]
            ))

        # Plan execution
        steps.append(PlanStep(
            id="execute",
            name="Execute",
            description="Perform main action",
            action="execute",
            dependencies=["analyze"]
        ))

        # Validate results
        steps.append(PlanStep(
            id="validate",
            name="Validate",
            description="Verify results meet goal",
            action="validate",
            dependencies=["execute"]
        ))

        return steps[:max_steps]

    async def execute_plan(self, plan: Plan) -> Dict[str, Any]:
        """
        Execute a plan.

        Args:
            plan: The plan to execute

        Returns:
            Execution results
        """
        plan.status = PlanStatus.IN_PROGRESS
        results = {}

        for step in plan.steps:
            # Check dependencies
            deps_met = all(
                plan.steps[i].status == PlanStatus.COMPLETED
                for i, s in enumerate(plan.steps)
                if s.id in step.dependencies
            )

            if not deps_met:
                continue

            try:
                step.status = PlanStatus.IN_PROGRESS
                result = await self._execute_step(step)
                step.result = result
                step.status = PlanStatus.COMPLETED
                results[step.id] = result
            except Exception as e:
                step.status = PlanStatus.FAILED
                results[step.id] = {"error": str(e)}
                logger.error(f"Step {step.id} failed: {e}")

        # Check overall status
        if all(s.status == PlanStatus.COMPLETED for s in plan.steps):
            plan.status = PlanStatus.COMPLETED
        elif any(s.status == PlanStatus.FAILED for s in plan.steps):
            plan.status = PlanStatus.FAILED

        return results

    async def _execute_step(self, step: PlanStep) -> Any:
        """Execute a single step."""
        logger.info(f"Executing step: {step.name}")

        # Placeholder execution - in real implementation would dispatch to tools
        return {
            "step": step.id,
            "action": step.action,
            "status": "completed"
        }

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self) -> List[Plan]:
        """List all plans."""
        return list(self._plans.values())


# Global planner instance
planner = Planner()


# Convenience exports
async def create_plan(goal: str, **kwargs) -> Plan:
    """Create a plan to achieve a goal."""
    return await planner.create_plan(goal, **kwargs)


async def execute_plan(plan: Plan) -> Dict[str, Any]:
    """Execute a plan."""
    return await planner.execute_plan(plan)


__all__ = [
    "Planner",
    "Plan",
    "PlanStep",
    "PlanStatus",
    "PlanPriority",
    "planner",
    "create_plan",
    "execute_plan"
]
