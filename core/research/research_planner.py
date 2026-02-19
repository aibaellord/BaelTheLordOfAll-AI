"""
BAEL Research Planner
======================

Plans and orchestrates research strategies.
Decomposes research goals into actionable steps.

Features:
- Goal decomposition
- Strategy selection
- Resource planning
- Progress tracking
- Adaptive replanning
"""

import hashlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ResearchMethod(Enum):
    """Research methods."""
    WEB_SEARCH = "web_search"
    PAPER_REVIEW = "paper_review"
    DATA_ANALYSIS = "data_analysis"
    EXPERT_CONSULTATION = "expert_consultation"
    EXPERIMENTATION = "experimentation"
    SURVEY = "survey"
    CASE_STUDY = "case_study"


class StepStatus(Enum):
    """Status of a research step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    FAILED = "failed"


class PlanStatus(Enum):
    """Status of a research plan."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class ResearchGoal:
    """A research goal."""
    id: str
    description: str

    # Scope
    questions: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # Priority
    priority: int = 5  # 1-10

    # Constraints
    time_limit_hours: Optional[float] = None
    max_sources: int = 20

    # Success criteria
    success_criteria: List[str] = field(default_factory=list)


@dataclass
class ResearchStep:
    """A step in the research plan."""
    id: str
    description: str

    # Method
    method: ResearchMethod

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # Status
    status: StepStatus = StepStatus.PENDING

    # Resources
    estimated_time_minutes: int = 30
    actual_time_minutes: int = 0

    # Results
    output: Optional[str] = None
    findings_count: int = 0

    # Metadata
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ResearchPlan:
    """A research plan."""
    id: str
    goal: ResearchGoal

    # Steps
    steps: List[ResearchStep] = field(default_factory=list)

    # Status
    status: PlanStatus = PlanStatus.DRAFT

    # Progress
    progress: float = 0.0  # 0-1

    # Timeline
    estimated_total_minutes: int = 0
    actual_total_minutes: int = 0

    # Results
    findings_count: int = 0
    sources_used: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ResearchPlanner:
    """
    Research planner for BAEL.

    Plans and manages research activities.
    """

    # Default step templates by goal type
    TEMPLATES = {
        "general": [
            (ResearchMethod.WEB_SEARCH, "Search for overview information", 15),
            (ResearchMethod.WEB_SEARCH, "Find specific sources", 20),
            (ResearchMethod.PAPER_REVIEW, "Review academic papers", 45),
            (ResearchMethod.DATA_ANALYSIS, "Analyze collected information", 30),
        ],
        "technical": [
            (ResearchMethod.WEB_SEARCH, "Search technical documentation", 15),
            (ResearchMethod.WEB_SEARCH, "Find code examples", 20),
            (ResearchMethod.PAPER_REVIEW, "Review technical papers", 30),
            (ResearchMethod.EXPERIMENTATION, "Test implementations", 45),
            (ResearchMethod.DATA_ANALYSIS, "Compare solutions", 30),
        ],
        "academic": [
            (ResearchMethod.PAPER_REVIEW, "Review foundational papers", 45),
            (ResearchMethod.PAPER_REVIEW, "Review recent papers", 45),
            (ResearchMethod.WEB_SEARCH, "Search for related work", 20),
            (ResearchMethod.DATA_ANALYSIS, "Analyze findings", 40),
            (ResearchMethod.DATA_ANALYSIS, "Synthesize conclusions", 30),
        ],
    }

    def __init__(self):
        # Plans
        self._plans: Dict[str, ResearchPlan] = {}

        # Active plan
        self._active_plan: Optional[str] = None

        # Stats
        self.stats = {
            "plans_created": 0,
            "steps_completed": 0,
            "total_research_minutes": 0,
        }

    def create_plan(
        self,
        goal: ResearchGoal,
        template: str = "general",
    ) -> ResearchPlan:
        """
        Create a research plan.

        Args:
            goal: Research goal
            template: Plan template to use

        Returns:
            Research plan
        """
        plan_id = hashlib.md5(
            f"{goal.description}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        plan = ResearchPlan(
            id=plan_id,
            goal=goal,
        )

        # Generate steps from template
        template_steps = self.TEMPLATES.get(template, self.TEMPLATES["general"])

        for i, (method, description, time_est) in enumerate(template_steps):
            step_id = f"{plan_id}_step_{i+1}"

            step = ResearchStep(
                id=step_id,
                description=description,
                method=method,
                estimated_time_minutes=time_est,
            )

            # Add dependency on previous step
            if i > 0:
                step.depends_on = [f"{plan_id}_step_{i}"]

            plan.steps.append(step)

        # Calculate total time
        plan.estimated_total_minutes = sum(s.estimated_time_minutes for s in plan.steps)

        self._plans[plan_id] = plan
        self.stats["plans_created"] += 1

        return plan

    def decompose_goal(
        self,
        goal: ResearchGoal,
    ) -> List[ResearchStep]:
        """
        Decompose a goal into research steps.

        Args:
            goal: Research goal

        Returns:
            List of research steps
        """
        steps = []

        # Determine research type from keywords
        keywords_lower = [k.lower() for k in goal.keywords]
        description_lower = goal.description.lower()

        # Technical indicators
        tech_keywords = ["code", "implementation", "api", "library", "framework", "programming"]
        is_technical = any(k in description_lower or k in keywords_lower for k in tech_keywords)

        # Academic indicators
        academic_keywords = ["research", "study", "paper", "literature", "theory"]
        is_academic = any(k in description_lower or k in keywords_lower for k in academic_keywords)

        # Generate steps based on questions
        for i, question in enumerate(goal.questions):
            question_lower = question.lower()

            # Determine method based on question
            if any(w in question_lower for w in ["how", "implement", "code"]):
                method = ResearchMethod.EXPERIMENTATION if is_technical else ResearchMethod.WEB_SEARCH
            elif any(w in question_lower for w in ["why", "theory", "explain"]):
                method = ResearchMethod.PAPER_REVIEW if is_academic else ResearchMethod.WEB_SEARCH
            elif any(w in question_lower for w in ["what", "define", "describe"]):
                method = ResearchMethod.WEB_SEARCH
            elif any(w in question_lower for w in ["compare", "analyze", "evaluate"]):
                method = ResearchMethod.DATA_ANALYSIS
            else:
                method = ResearchMethod.WEB_SEARCH

            step = ResearchStep(
                id=f"step_{i+1}",
                description=f"Research: {question}",
                method=method,
                estimated_time_minutes=20 + len(question.split()) * 2,
            )

            steps.append(step)

        # Add synthesis step
        if steps:
            synthesis = ResearchStep(
                id=f"step_{len(steps)+1}",
                description="Synthesize findings and draw conclusions",
                method=ResearchMethod.DATA_ANALYSIS,
                depends_on=[s.id for s in steps],
                estimated_time_minutes=30,
            )
            steps.append(synthesis)

        return steps

    def start_plan(self, plan_id: str) -> bool:
        """Start executing a plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return False

        plan.status = PlanStatus.ACTIVE
        plan.started_at = datetime.now()
        self._active_plan = plan_id

        # Start first step
        if plan.steps:
            plan.steps[0].status = StepStatus.IN_PROGRESS
            plan.steps[0].started_at = datetime.now()

        return True

    def complete_step(
        self,
        plan_id: str,
        step_id: str,
        output: Optional[str] = None,
        findings_count: int = 0,
    ) -> Optional[ResearchStep]:
        """
        Complete a research step.

        Args:
            plan_id: Plan ID
            step_id: Step ID
            output: Step output
            findings_count: Number of findings

        Returns:
            Next step or None
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        # Find and complete step
        step = None
        step_index = -1
        for i, s in enumerate(plan.steps):
            if s.id == step_id:
                step = s
                step_index = i
                break

        if not step:
            return None

        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.now()
        step.output = output
        step.findings_count = findings_count

        if step.started_at:
            step.actual_time_minutes = int(
                (step.completed_at - step.started_at).total_seconds() / 60
            )

        plan.findings_count += findings_count
        plan.actual_total_minutes += step.actual_time_minutes

        self.stats["steps_completed"] += 1
        self.stats["total_research_minutes"] += step.actual_time_minutes

        # Update progress
        completed = sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED)
        plan.progress = completed / len(plan.steps)

        # Find next step
        next_step = self._get_next_step(plan)

        if next_step:
            next_step.status = StepStatus.IN_PROGRESS
            next_step.started_at = datetime.now()
            return next_step

        # All steps complete
        if all(s.status == StepStatus.COMPLETED for s in plan.steps):
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now()

        return None

    def _get_next_step(self, plan: ResearchPlan) -> Optional[ResearchStep]:
        """Get the next available step."""
        for step in plan.steps:
            if step.status != StepStatus.PENDING:
                continue

            # Check dependencies
            deps_complete = all(
                any(s.id == dep and s.status == StepStatus.COMPLETED for s in plan.steps)
                for dep in step.depends_on
            )

            if deps_complete:
                return step

        return None

    def replan(self, plan_id: str) -> ResearchPlan:
        """
        Replan based on current progress.

        Args:
            plan_id: Plan ID

        Returns:
            Updated plan
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        # Check if we need more steps
        if plan.progress > 0.5 and plan.findings_count < 5:
            # Add more search steps
            new_step = ResearchStep(
                id=f"{plan_id}_additional_{len(plan.steps)+1}",
                description="Extended search for additional sources",
                method=ResearchMethod.WEB_SEARCH,
                estimated_time_minutes=30,
            )
            plan.steps.append(new_step)
            plan.estimated_total_minutes += new_step.estimated_time_minutes

        # Skip blocked steps
        for step in plan.steps:
            if step.status == StepStatus.BLOCKED:
                step.status = StepStatus.SKIPPED

        # Recalculate progress
        completed = sum(1 for s in plan.steps if s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED])
        plan.progress = completed / len(plan.steps)

        return plan

    def get_plan(self, plan_id: str) -> Optional[ResearchPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def get_active_plan(self) -> Optional[ResearchPlan]:
        """Get the currently active plan."""
        if self._active_plan:
            return self._plans.get(self._active_plan)
        return None

    def estimate_completion(self, plan_id: str) -> Optional[datetime]:
        """Estimate plan completion time."""
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        remaining_minutes = sum(
            s.estimated_time_minutes for s in plan.steps
            if s.status in [StepStatus.PENDING, StepStatus.IN_PROGRESS]
        )

        return datetime.now() + timedelta(minutes=remaining_minutes)

    def get_plan_summary(self, plan_id: str) -> Dict[str, Any]:
        """Get plan summary."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {}

        return {
            "id": plan.id,
            "goal": plan.goal.description,
            "status": plan.status.value,
            "progress": f"{plan.progress:.0%}",
            "steps_total": len(plan.steps),
            "steps_completed": sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED),
            "findings": plan.findings_count,
            "estimated_minutes": plan.estimated_total_minutes,
            "actual_minutes": plan.actual_total_minutes,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get planner statistics."""
        return {
            **self.stats,
            "active_plans": sum(1 for p in self._plans.values() if p.status == PlanStatus.ACTIVE),
            "completed_plans": sum(1 for p in self._plans.values() if p.status == PlanStatus.COMPLETED),
        }


def demo():
    """Demonstrate research planner."""
    print("=" * 60)
    print("BAEL Research Planner Demo")
    print("=" * 60)

    planner = ResearchPlanner()

    # Create research goal
    goal = ResearchGoal(
        id="goal_1",
        description="Understand transformer architectures in NLP",
        questions=[
            "What is the attention mechanism?",
            "How do transformers compare to RNNs?",
            "What are common transformer variants?",
        ],
        keywords=["transformer", "attention", "NLP", "deep learning"],
        priority=8,
        time_limit_hours=2.0,
        success_criteria=[
            "Understand attention mechanism",
            "Compare at least 3 architectures",
            "Identify key papers",
        ],
    )

    print(f"\nResearch Goal: {goal.description}")
    print(f"Questions: {len(goal.questions)}")

    # Create plan
    print("\nCreating research plan...")
    plan = planner.create_plan(goal, template="academic")

    print(f"\nPlan created: {plan.id}")
    print(f"Steps: {len(plan.steps)}")
    print(f"Estimated time: {plan.estimated_total_minutes} minutes")

    print("\nSteps:")
    for step in plan.steps:
        print(f"  - {step.description}")
        print(f"    Method: {step.method.value}")
        print(f"    Time: {step.estimated_time_minutes} min")

    # Start plan
    print("\nStarting plan...")
    planner.start_plan(plan.id)

    # Simulate completing steps
    print("\nSimulating step completion...")

    for step in plan.steps:
        if step.status == StepStatus.IN_PROGRESS:
            next_step = planner.complete_step(
                plan.id,
                step.id,
                output=f"Completed: {step.description}",
                findings_count=3,
            )

            print(f"  Completed: {step.description[:40]}...")

            if next_step:
                print(f"  Next: {next_step.description[:40]}...")

    # Get summary
    print("\nPlan Summary:")
    summary = planner.get_plan_summary(plan.id)
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # Estimate completion
    if plan.status != PlanStatus.COMPLETED:
        est = planner.estimate_completion(plan.id)
        if est:
            print(f"\nEstimated completion: {est}")

    print(f"\nStats: {planner.get_stats()}")


if __name__ == "__main__":
    demo()
