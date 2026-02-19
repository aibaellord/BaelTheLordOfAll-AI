"""
🧬 COGNITIVE CONTROL 🧬
=======================
Executive function and control.

Features:
- Goal management
- Planning
- Meta-cognition
- Scheduling
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid
import heapq


class GoalStatus(Enum):
    """Goal status"""
    PENDING = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    COMPLETED = auto()
    FAILED = auto()
    ABANDONED = auto()


class GoalPriority(Enum):
    """Goal priority levels"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Goal:
    """A goal to achieve"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Goal definition
    name: str = ""
    description: str = ""

    # Status
    status: GoalStatus = GoalStatus.PENDING
    priority: GoalPriority = GoalPriority.MEDIUM

    # Success criteria
    success_condition: Optional[Callable[[], bool]] = None

    # Progress
    progress: float = 0.0

    # Hierarchy
    parent_goal_id: Optional[str] = None
    subgoal_ids: List[str] = field(default_factory=list)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None

    # Resources
    required_resources: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Check if goal is complete"""
        if self.success_condition:
            return self.success_condition()
        return self.progress >= 1.0

    def update_progress(self, progress: float):
        """Update progress"""
        self.progress = min(1.0, max(0.0, progress))
        if self.progress >= 1.0:
            self.status = GoalStatus.COMPLETED

    def __lt__(self, other):
        """For priority queue comparison"""
        return self.priority.value < other.priority.value


@dataclass
class PlanStep:
    """A step in a plan"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    action: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Dependencies
    preconditions: List[str] = field(default_factory=list)

    # Status
    completed: bool = False
    result: Any = None


@dataclass
class Plan:
    """A plan to achieve a goal"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    goal_id: str = ""

    # Steps
    steps: List[PlanStep] = field(default_factory=list)
    current_step: int = 0

    # Quality
    estimated_cost: float = 0.0
    estimated_time: float = 0.0

    # Status
    is_valid: bool = True

    def get_next_step(self) -> Optional[PlanStep]:
        """Get next step to execute"""
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def advance(self):
        """Advance to next step"""
        if self.current_step < len(self.steps):
            self.current_step += 1

    def is_complete(self) -> bool:
        """Check if plan is complete"""
        return self.current_step >= len(self.steps)


class ExecutiveController:
    """
    Executive control function.
    """

    def __init__(self):
        # Goals
        self.goals: Dict[str, Goal] = {}
        self.active_goal_id: Optional[str] = None

        # Goal stack
        self.goal_stack: List[str] = []

        # Plans
        self.plans: Dict[str, Plan] = {}

        # Conflict resolution
        self.conflict_resolver: Optional[Callable[[List[Goal]], Goal]] = None

    def add_goal(self, goal: Goal):
        """Add new goal"""
        self.goals[goal.id] = goal

        # Add to parent if specified
        if goal.parent_goal_id and goal.parent_goal_id in self.goals:
            self.goals[goal.parent_goal_id].subgoal_ids.append(goal.id)

    def activate_goal(self, goal_id: str):
        """Activate a goal"""
        if goal_id in self.goals:
            self.goals[goal_id].status = GoalStatus.ACTIVE
            self.active_goal_id = goal_id

            if goal_id not in self.goal_stack:
                self.goal_stack.append(goal_id)

    def suspend_goal(self, goal_id: str):
        """Suspend a goal"""
        if goal_id in self.goals:
            self.goals[goal_id].status = GoalStatus.SUSPENDED

            if goal_id == self.active_goal_id:
                self.active_goal_id = None

    def complete_goal(self, goal_id: str):
        """Mark goal as complete"""
        if goal_id in self.goals:
            self.goals[goal_id].status = GoalStatus.COMPLETED
            self.goals[goal_id].progress = 1.0

            if goal_id in self.goal_stack:
                self.goal_stack.remove(goal_id)

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals"""
        return [g for g in self.goals.values() if g.status == GoalStatus.ACTIVE]

    def select_goal(self) -> Optional[Goal]:
        """Select highest priority goal"""
        active = self.get_active_goals()

        if not active:
            return None

        if self.conflict_resolver and len(active) > 1:
            return self.conflict_resolver(active)

        # Default: highest priority
        return min(active, key=lambda g: g.priority.value)

    def add_plan(self, plan: Plan):
        """Add plan for goal"""
        self.plans[plan.goal_id] = plan

    def get_plan(self, goal_id: str) -> Optional[Plan]:
        """Get plan for goal"""
        return self.plans.get(goal_id)

    def execute_step(self, plan: Plan, executor: Callable[[PlanStep], Any]) -> Any:
        """Execute next plan step"""
        step = plan.get_next_step()

        if not step:
            return None

        result = executor(step)
        step.result = result
        step.completed = True
        plan.advance()

        return result


class MetaCognition:
    """
    Meta-cognitive monitoring and control.
    """

    def __init__(self):
        # Self-model
        self.beliefs: Dict[str, float] = {}  # belief -> confidence

        # Performance monitoring
        self.performance_history: List[Dict[str, Any]] = []

        # Learning from experience
        self.lessons: List[str] = []

        # Current confidence
        self.confidence: float = 0.5

    def update_belief(self, belief: str, confidence: float):
        """Update belief confidence"""
        self.beliefs[belief] = min(1.0, max(0.0, confidence))

    def get_confidence(self, belief: str) -> float:
        """Get belief confidence"""
        return self.beliefs.get(belief, 0.5)

    def monitor_performance(
        self,
        task: str,
        success: bool,
        difficulty: float = 0.5
    ):
        """Monitor task performance"""
        entry = {
            'task': task,
            'success': success,
            'difficulty': difficulty,
            'timestamp': datetime.now()
        }
        self.performance_history.append(entry)

        # Update confidence
        self._update_confidence()

    def _update_confidence(self):
        """Update overall confidence based on performance"""
        if not self.performance_history:
            return

        # Recent performance weighted average
        recent = self.performance_history[-10:]

        successes = sum(1 for p in recent if p['success'])
        self.confidence = successes / len(recent)

    def should_seek_help(self, difficulty: float) -> bool:
        """Determine if help should be sought"""
        # Low confidence + high difficulty = seek help
        return self.confidence < 0.5 and difficulty > 0.7

    def should_proceed(self, difficulty: float) -> bool:
        """Determine if task should proceed"""
        # High confidence or low difficulty = proceed
        return self.confidence > 0.6 or difficulty < 0.3

    def add_lesson(self, lesson: str):
        """Add learned lesson"""
        self.lessons.append(lesson)

    def reflect(self) -> Dict[str, Any]:
        """Reflect on performance"""
        if not self.performance_history:
            return {'status': 'no_data'}

        recent = self.performance_history[-20:]

        success_rate = sum(1 for p in recent if p['success']) / len(recent)
        avg_difficulty = sum(p['difficulty'] for p in recent) / len(recent)

        return {
            'success_rate': success_rate,
            'avg_difficulty': avg_difficulty,
            'confidence': self.confidence,
            'lessons_learned': len(self.lessons),
            'recommendation': self._get_recommendation(success_rate, avg_difficulty)
        }

    def _get_recommendation(self, success_rate: float, avg_difficulty: float) -> str:
        """Get meta-cognitive recommendation"""
        if success_rate < 0.3:
            return "Consider simpler approaches or seek assistance"
        elif success_rate < 0.6:
            return "Review strategies and adjust approach"
        elif avg_difficulty > 0.8:
            return "High difficulty managed well - continue current approach"
        else:
            return "Performance good - ready for more challenging tasks"


class CognitiveScheduler:
    """
    Schedules cognitive processes.
    """

    def __init__(self):
        # Task queue (priority queue)
        self.task_queue: List[tuple] = []  # (priority, timestamp, task)

        # Resource limits
        self.resource_limits: Dict[str, float] = {
            'attention': 1.0,
            'memory': 1.0,
            'reasoning': 1.0
        }

        # Current allocations
        self.allocations: Dict[str, float] = {}

        # Task counter for tie-breaking
        self.task_counter = 0

    def schedule(
        self,
        task: Any,
        priority: int,
        resources: Dict[str, float] = None
    ):
        """Schedule a task"""
        self.task_counter += 1
        heapq.heappush(
            self.task_queue,
            (priority, self.task_counter, task, resources or {})
        )

    def get_next_task(self) -> Optional[Any]:
        """Get next task to execute"""
        while self.task_queue:
            priority, _, task, resources = heapq.heappop(self.task_queue)

            # Check resource availability
            if self._can_allocate(resources):
                self._allocate(resources)
                return task

        return None

    def _can_allocate(self, resources: Dict[str, float]) -> bool:
        """Check if resources can be allocated"""
        for resource, amount in resources.items():
            current = self.allocations.get(resource, 0.0)
            limit = self.resource_limits.get(resource, 1.0)

            if current + amount > limit:
                return False

        return True

    def _allocate(self, resources: Dict[str, float]):
        """Allocate resources"""
        for resource, amount in resources.items():
            self.allocations[resource] = self.allocations.get(resource, 0.0) + amount

    def release(self, resources: Dict[str, float]):
        """Release resources"""
        for resource, amount in resources.items():
            self.allocations[resource] = max(
                0.0,
                self.allocations.get(resource, 0.0) - amount
            )

    def get_load(self) -> Dict[str, float]:
        """Get current resource load"""
        return {
            resource: self.allocations.get(resource, 0.0) / limit
            for resource, limit in self.resource_limits.items()
        }

    def is_overloaded(self, threshold: float = 0.9) -> bool:
        """Check if system is overloaded"""
        load = self.get_load()
        return any(l > threshold for l in load.values())


# Export all
__all__ = [
    'GoalStatus',
    'GoalPriority',
    'Goal',
    'PlanStep',
    'Plan',
    'ExecutiveController',
    'MetaCognition',
    'CognitiveScheduler',
]
