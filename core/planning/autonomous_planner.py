"""
BAEL - Autonomous Task Planner
Long-horizon planning with goal decomposition and execution.

Features:
- Hierarchical goal decomposition
- Plan generation and optimization
- Dynamic replanning
- Resource management
- Progress tracking
- Plan verification
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class GoalStatus(Enum):
    """Status of a goal."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class PlanStatus(Enum):
    """Status of a plan."""
    DRAFT = "draft"
    VALIDATED = "validated"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    REPLANNING = "replanning"


class ActionType(Enum):
    """Types of actions."""
    THINK = "think"
    EXECUTE = "execute"
    DELEGATE = "delegate"
    VERIFY = "verify"
    WAIT = "wait"
    DECISION = "decision"
    LOOP = "loop"


class ResourceType(Enum):
    """Types of resources."""
    TIME = "time"
    COMPUTE = "compute"
    MEMORY = "memory"
    API_CALLS = "api_calls"
    TOKENS = "tokens"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Goal:
    """A goal to be achieved."""
    id: str
    description: str
    success_criteria: List[str]
    priority: int = 5  # 1-10
    deadline: Optional[datetime] = None
    parent_id: Optional[str] = None
    subgoals: List[str] = field(default_factory=list)
    status: GoalStatus = GoalStatus.PENDING
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_terminal(self) -> bool:
        return len(self.subgoals) == 0

    def add_subgoal(self, subgoal_id: str) -> None:
        if subgoal_id not in self.subgoals:
            self.subgoals.append(subgoal_id)


@dataclass
class Action:
    """A single action in a plan."""
    id: str
    type: ActionType
    description: str
    tool: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0  # seconds
    actual_duration: float = 0.0
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def can_execute(self, achieved_effects: Set[str]) -> bool:
        """Check if action can be executed given achieved effects."""
        return all(pre in achieved_effects for pre in self.preconditions)


@dataclass
class Plan:
    """A plan to achieve a goal."""
    id: str
    goal_id: str
    actions: List[Action]
    status: PlanStatus = PlanStatus.DRAFT
    current_action_index: int = 0
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    resource_budget: Dict[str, float] = field(default_factory=dict)
    resource_used: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def current_action(self) -> Optional[Action]:
        if 0 <= self.current_action_index < len(self.actions):
            return self.actions[self.current_action_index]
        return None

    @property
    def progress(self) -> float:
        if not self.actions:
            return 0.0
        completed = sum(1 for a in self.actions if a.status == "completed")
        return completed / len(self.actions)

    def get_next_executable_actions(
        self,
        achieved_effects: Set[str]
    ) -> List[Action]:
        """Get actions that can be executed next."""
        return [
            a for a in self.actions
            if a.status == "pending" and a.can_execute(achieved_effects)
        ]


@dataclass
class Resource:
    """A resource that can be consumed."""
    type: ResourceType
    total: float
    used: float = 0.0
    reserved: float = 0.0

    @property
    def available(self) -> float:
        return self.total - self.used - self.reserved

    def consume(self, amount: float) -> bool:
        if amount <= self.available + self.reserved:
            self.used += amount
            self.reserved = max(0, self.reserved - amount)
            return True
        return False

    def reserve(self, amount: float) -> bool:
        if amount <= self.available:
            self.reserved += amount
            return True
        return False


# =============================================================================
# GOAL MANAGER
# =============================================================================

class GoalManager:
    """Manages goals and their hierarchy."""

    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.root_goals: Set[str] = set()

    def create_goal(
        self,
        description: str,
        success_criteria: List[str],
        priority: int = 5,
        deadline: Optional[datetime] = None,
        parent_id: Optional[str] = None
    ) -> Goal:
        """Create a new goal."""
        goal_id = hashlib.md5(
            f"{description}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        goal = Goal(
            id=goal_id,
            description=description,
            success_criteria=success_criteria,
            priority=priority,
            deadline=deadline,
            parent_id=parent_id
        )

        self.goals[goal_id] = goal

        if parent_id:
            if parent_id in self.goals:
                self.goals[parent_id].add_subgoal(goal_id)
        else:
            self.root_goals.add(goal_id)

        logger.info(f"Created goal: {goal_id} - {description}")
        return goal

    def decompose_goal(
        self,
        goal_id: str,
        subgoal_descriptions: List[Tuple[str, List[str]]]
    ) -> List[Goal]:
        """Decompose a goal into subgoals."""
        parent = self.goals.get(goal_id)
        if not parent:
            raise ValueError(f"Goal not found: {goal_id}")

        subgoals = []
        for desc, criteria in subgoal_descriptions:
            subgoal = self.create_goal(
                description=desc,
                success_criteria=criteria,
                priority=parent.priority,
                deadline=parent.deadline,
                parent_id=goal_id
            )
            subgoals.append(subgoal)

        return subgoals

    def update_goal_status(
        self,
        goal_id: str,
        status: GoalStatus,
        progress: Optional[float] = None
    ) -> None:
        """Update goal status."""
        goal = self.goals.get(goal_id)
        if goal:
            goal.status = status
            if progress is not None:
                goal.progress = progress

            # Propagate to parent
            if goal.parent_id:
                self._update_parent_progress(goal.parent_id)

    def _update_parent_progress(self, parent_id: str) -> None:
        """Update parent goal progress based on subgoals."""
        parent = self.goals.get(parent_id)
        if not parent or not parent.subgoals:
            return

        total_progress = 0.0
        for subgoal_id in parent.subgoals:
            subgoal = self.goals.get(subgoal_id)
            if subgoal:
                total_progress += subgoal.progress

        parent.progress = total_progress / len(parent.subgoals)

        # Check if all subgoals achieved
        all_achieved = all(
            self.goals[sg].status == GoalStatus.ACHIEVED
            for sg in parent.subgoals
            if sg in self.goals
        )

        if all_achieved:
            parent.status = GoalStatus.ACHIEVED
            parent.progress = 1.0

    def get_active_goals(self) -> List[Goal]:
        """Get all active (in-progress) goals."""
        return [
            g for g in self.goals.values()
            if g.status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]
        ]

    def get_goal_tree(self, goal_id: str) -> Dict[str, Any]:
        """Get goal and all descendants as a tree."""
        goal = self.goals.get(goal_id)
        if not goal:
            return {}

        tree = {
            "id": goal.id,
            "description": goal.description,
            "status": goal.status.value,
            "progress": goal.progress,
            "subgoals": []
        }

        for subgoal_id in goal.subgoals:
            tree["subgoals"].append(self.get_goal_tree(subgoal_id))

        return tree


# =============================================================================
# PLAN GENERATOR
# =============================================================================

class PlanGenerator:
    """Generates plans to achieve goals."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client
        self.action_templates: Dict[str, Dict[str, Any]] = {}
        self._load_action_templates()

    def _load_action_templates(self) -> None:
        """Load common action templates."""
        self.action_templates = {
            "research": {
                "type": ActionType.EXECUTE,
                "tool": "web_search",
                "estimated_duration": 30.0
            },
            "code": {
                "type": ActionType.EXECUTE,
                "tool": "code_generator",
                "estimated_duration": 60.0
            },
            "analyze": {
                "type": ActionType.THINK,
                "estimated_duration": 20.0
            },
            "verify": {
                "type": ActionType.VERIFY,
                "estimated_duration": 15.0
            },
            "file_operation": {
                "type": ActionType.EXECUTE,
                "tool": "file_system",
                "estimated_duration": 5.0
            }
        }

    async def generate_plan(
        self,
        goal: Goal,
        context: Dict[str, Any]
    ) -> Plan:
        """Generate a plan for a goal."""
        plan_id = hashlib.md5(
            f"{goal.id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Generate actions
        if self.llm_client:
            actions = await self._generate_actions_with_llm(goal, context)
        else:
            actions = self._generate_actions_heuristic(goal, context)

        # Calculate estimated duration
        total_duration = sum(a.estimated_duration for a in actions)

        plan = Plan(
            id=plan_id,
            goal_id=goal.id,
            actions=actions,
            estimated_duration=total_duration
        )

        logger.info(f"Generated plan {plan_id} with {len(actions)} actions")
        return plan

    async def _generate_actions_with_llm(
        self,
        goal: Goal,
        context: Dict[str, Any]
    ) -> List[Action]:
        """Generate actions using LLM."""
        prompt = f"""Generate a step-by-step plan to achieve the following goal:

Goal: {goal.description}

Success Criteria:
{chr(10).join(f"- {c}" for c in goal.success_criteria)}

Context:
{json.dumps(context, indent=2)}

For each step, provide:
1. Action type (think/execute/verify/delegate/wait/decision)
2. Description
3. Tool to use (if execute)
4. Preconditions (what must be true before this action)
5. Effects (what becomes true after this action)
6. Estimated duration in seconds

Format as JSON array."""

        # This would call the LLM
        # For now, fallback to heuristic
        return self._generate_actions_heuristic(goal, context)

    def _generate_actions_heuristic(
        self,
        goal: Goal,
        context: Dict[str, Any]
    ) -> List[Action]:
        """Generate actions using heuristics."""
        actions = []
        action_num = 0

        def create_action(
            type: ActionType,
            description: str,
            tool: Optional[str] = None,
            duration: float = 10.0,
            preconditions: Optional[List[str]] = None,
            effects: Optional[List[str]] = None
        ) -> Action:
            nonlocal action_num
            action_num += 1
            return Action(
                id=f"{goal.id}_action_{action_num}",
                type=type,
                description=description,
                tool=tool,
                estimated_duration=duration,
                preconditions=preconditions or [],
                effects=effects or [f"effect_{action_num}"]
            )

        # Analyze the goal
        goal_lower = goal.description.lower()

        # Planning action
        actions.append(create_action(
            ActionType.THINK,
            f"Analyze goal and create approach: {goal.description}",
            duration=15.0,
            effects=["analysis_complete"]
        ))

        # Research if needed
        if any(kw in goal_lower for kw in ["learn", "research", "find", "discover"]):
            actions.append(create_action(
                ActionType.EXECUTE,
                "Conduct research on the topic",
                tool="web_search",
                duration=30.0,
                preconditions=["analysis_complete"],
                effects=["research_complete"]
            ))

        # Code if needed
        if any(kw in goal_lower for kw in ["code", "implement", "build", "create", "develop"]):
            actions.append(create_action(
                ActionType.EXECUTE,
                "Generate implementation",
                tool="code_generator",
                duration=60.0,
                preconditions=["analysis_complete"],
                effects=["implementation_complete"]
            ))

        # File operations if needed
        if any(kw in goal_lower for kw in ["file", "write", "save", "read"]):
            actions.append(create_action(
                ActionType.EXECUTE,
                "Perform file operations",
                tool="file_system",
                duration=5.0,
                effects=["files_processed"]
            ))

        # Verification
        for i, criterion in enumerate(goal.success_criteria):
            actions.append(create_action(
                ActionType.VERIFY,
                f"Verify: {criterion}",
                duration=10.0,
                effects=[f"criterion_{i}_verified"]
            ))

        # Summary
        actions.append(create_action(
            ActionType.THINK,
            "Summarize results and prepare output",
            duration=10.0,
            effects=["goal_complete"]
        ))

        return actions


# =============================================================================
# PLAN EXECUTOR
# =============================================================================

class PlanExecutor:
    """Executes plans and manages their lifecycle."""

    def __init__(
        self,
        tool_executor: Optional[Any] = None,
        llm_client: Optional[Any] = None
    ):
        self.tool_executor = tool_executor
        self.llm_client = llm_client
        self.achieved_effects: Set[str] = set()
        self.execution_log: List[Dict[str, Any]] = []

    async def execute_plan(
        self,
        plan: Plan,
        on_action_complete: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute a plan."""
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now()

        results = []

        try:
            while True:
                # Get next executable actions
                executable = plan.get_next_executable_actions(self.achieved_effects)

                if not executable:
                    # Check if all done
                    pending = [a for a in plan.actions if a.status == "pending"]
                    if not pending:
                        break
                    else:
                        # Blocked - some actions can't execute
                        logger.warning("Plan blocked - no executable actions")
                        plan.status = PlanStatus.FAILED
                        break

                # Execute actions (could be parallel for independent actions)
                for action in executable:
                    result = await self._execute_action(action)
                    results.append(result)

                    if on_action_complete:
                        await on_action_complete(action, result)

                    if not result.get("success", False):
                        if action.retry_count < action.max_retries:
                            action.retry_count += 1
                            action.status = "pending"
                        else:
                            action.status = "failed"
                            plan.status = PlanStatus.FAILED
                            break
                    else:
                        action.status = "completed"
                        self.achieved_effects.update(action.effects)

                if plan.status == PlanStatus.FAILED:
                    break

            if plan.status != PlanStatus.FAILED:
                plan.status = PlanStatus.COMPLETED

        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            plan.status = PlanStatus.FAILED

        plan.completed_at = datetime.now()
        plan.actual_duration = (
            plan.completed_at - plan.started_at
        ).total_seconds()

        return {
            "plan_id": plan.id,
            "status": plan.status.value,
            "actions_completed": sum(1 for a in plan.actions if a.status == "completed"),
            "actions_total": len(plan.actions),
            "duration": plan.actual_duration,
            "results": results
        }

    async def _execute_action(self, action: Action) -> Dict[str, Any]:
        """Execute a single action."""
        start_time = datetime.now()
        action.status = "running"

        try:
            if action.type == ActionType.THINK:
                result = await self._execute_think(action)
            elif action.type == ActionType.EXECUTE:
                result = await self._execute_tool(action)
            elif action.type == ActionType.VERIFY:
                result = await self._execute_verify(action)
            elif action.type == ActionType.WAIT:
                result = await self._execute_wait(action)
            elif action.type == ActionType.DECISION:
                result = await self._execute_decision(action)
            else:
                result = {"success": True, "output": "Action completed"}

            action.actual_duration = (datetime.now() - start_time).total_seconds()
            action.result = result

            self.execution_log.append({
                "action_id": action.id,
                "type": action.type.value,
                "description": action.description,
                "result": result,
                "duration": action.actual_duration,
                "timestamp": datetime.now().isoformat()
            })

            return result

        except Exception as e:
            action.error = str(e)
            action.actual_duration = (datetime.now() - start_time).total_seconds()
            return {"success": False, "error": str(e)}

    async def _execute_think(self, action: Action) -> Dict[str, Any]:
        """Execute a thinking action."""
        if self.llm_client:
            response = await self.llm_client.complete(
                messages=[{"role": "user", "content": action.description}]
            )
            return {
                "success": True,
                "output": response.get("content", "")
            }
        return {"success": True, "output": f"Thought about: {action.description}"}

    async def _execute_tool(self, action: Action) -> Dict[str, Any]:
        """Execute a tool action."""
        if self.tool_executor and action.tool:
            result = await self.tool_executor.execute_tool(
                action.tool,
                action.parameters
            )
            return {
                "success": result.success,
                "output": result.output,
                "error": result.error
            }
        return {"success": True, "output": f"Executed: {action.description}"}

    async def _execute_verify(self, action: Action) -> Dict[str, Any]:
        """Execute a verification action."""
        # In real implementation, would actually verify
        return {"success": True, "verified": True}

    async def _execute_wait(self, action: Action) -> Dict[str, Any]:
        """Execute a wait action."""
        duration = action.parameters.get("duration", action.estimated_duration)
        await asyncio.sleep(min(duration, 1.0))  # Cap for demo
        return {"success": True, "waited": duration}

    async def _execute_decision(self, action: Action) -> Dict[str, Any]:
        """Execute a decision action."""
        # Would use LLM to make decision
        return {"success": True, "decision": action.parameters.get("default", True)}


# =============================================================================
# TASK PLANNER
# =============================================================================

class TaskPlanner:
    """High-level task planner combining all components."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        tool_executor: Optional[Any] = None
    ):
        self.goal_manager = GoalManager()
        self.plan_generator = PlanGenerator(llm_client)
        self.plan_executor = PlanExecutor(tool_executor, llm_client)
        self.active_plans: Dict[str, Plan] = {}
        self.resources: Dict[ResourceType, Resource] = {}

        # Initialize default resources
        self._init_resources()

    def _init_resources(self) -> None:
        """Initialize default resource limits."""
        self.resources = {
            ResourceType.TIME: Resource(ResourceType.TIME, 3600),  # 1 hour
            ResourceType.API_CALLS: Resource(ResourceType.API_CALLS, 1000),
            ResourceType.TOKENS: Resource(ResourceType.TOKENS, 100000)
        }

    async def plan_and_execute(
        self,
        task_description: str,
        success_criteria: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a goal, plan, and execute."""
        # Create goal
        goal = self.goal_manager.create_goal(
            description=task_description,
            success_criteria=success_criteria or [
                "Task completed successfully",
                "Output meets requirements"
            ]
        )

        # Generate plan
        plan = await self.plan_generator.generate_plan(
            goal,
            context or {}
        )

        self.active_plans[plan.id] = plan

        # Update goal status
        self.goal_manager.update_goal_status(
            goal.id,
            GoalStatus.IN_PROGRESS
        )

        # Execute plan
        result = await self.plan_executor.execute_plan(plan)

        # Update goal based on result
        if result["status"] == "completed":
            self.goal_manager.update_goal_status(
                goal.id,
                GoalStatus.ACHIEVED,
                progress=1.0
            )
        else:
            self.goal_manager.update_goal_status(
                goal.id,
                GoalStatus.FAILED
            )

        return {
            "goal": {
                "id": goal.id,
                "description": goal.description,
                "status": goal.status.value
            },
            "plan": {
                "id": plan.id,
                "actions_count": len(plan.actions),
                "status": plan.status.value
            },
            "execution": result
        }

    async def decompose_and_plan(
        self,
        complex_task: str,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """Decompose a complex task and create hierarchical plans."""
        # Create root goal
        root_goal = self.goal_manager.create_goal(
            description=complex_task,
            success_criteria=["All subtasks completed"]
        )

        # Decompose (simplified - would use LLM in real implementation)
        subtasks = self._decompose_task(complex_task)

        subgoals = self.goal_manager.decompose_goal(
            root_goal.id,
            [(st, ["Subtask completed"]) for st in subtasks]
        )

        # Generate plans for leaf goals
        plans = []
        for subgoal in subgoals:
            plan = await self.plan_generator.generate_plan(
                subgoal,
                {"parent_goal": root_goal.id}
            )
            self.active_plans[plan.id] = plan
            plans.append(plan)

        return {
            "root_goal": root_goal.id,
            "subgoals": [g.id for g in subgoals],
            "plans": [p.id for p in plans],
            "tree": self.goal_manager.get_goal_tree(root_goal.id)
        }

    def _decompose_task(self, task: str) -> List[str]:
        """Decompose a task into subtasks (heuristic)."""
        # Simple keyword-based decomposition
        subtasks = []

        if "and" in task.lower():
            parts = task.lower().split(" and ")
            subtasks.extend([p.strip().capitalize() for p in parts])
        else:
            # Generic decomposition
            subtasks = [
                f"Analyze: {task}",
                f"Plan approach for: {task}",
                f"Execute: {task}",
                f"Verify: {task}"
            ]

        return subtasks

    def get_progress_report(self) -> Dict[str, Any]:
        """Get progress report for all active work."""
        active_goals = self.goal_manager.get_active_goals()

        return {
            "active_goals": len(active_goals),
            "goals": [
                {
                    "id": g.id,
                    "description": g.description[:50],
                    "status": g.status.value,
                    "progress": g.progress
                }
                for g in active_goals
            ],
            "active_plans": len(self.active_plans),
            "resources": {
                rt.value: {
                    "total": r.total,
                    "used": r.used,
                    "available": r.available
                }
                for rt, r in self.resources.items()
            }
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_planning():
    """Demonstrate task planning capabilities."""
    planner = TaskPlanner()

    # Simple task
    result = await planner.plan_and_execute(
        "Write a Python function to calculate fibonacci numbers",
        success_criteria=[
            "Function is implemented correctly",
            "Code handles edge cases",
            "Function is documented"
        ]
    )

    print(f"Task result: {json.dumps(result, indent=2)}")

    # Complex task with decomposition
    decomposed = await planner.decompose_and_plan(
        "Build a REST API and deploy it to production"
    )

    print(f"\nDecomposed task: {json.dumps(decomposed, indent=2)}")

    # Progress report
    report = planner.get_progress_report()
    print(f"\nProgress report: {json.dumps(report, indent=2)}")


if __name__ == "__main__":
    asyncio.run(example_planning())
