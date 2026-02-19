"""
BAEL Objective Tracker
=======================

Track objectives, goals, and milestones for missions.
Provides real-time visibility into mission progress.

Features:
- Objective management
- Milestone tracking
- Dependency resolution
- Progress calculation
- Success criteria validation
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ObjectiveStatus(Enum):
    """Objective status."""
    NOT_STARTED = "not_started"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ObjectiveType(Enum):
    """Objective types."""
    PRIMARY = "primary"       # Main objectives
    SECONDARY = "secondary"   # Supporting objectives
    OPTIONAL = "optional"     # Nice-to-have
    STRETCH = "stretch"       # Ambitious goals


@dataclass
class SuccessCriterion:
    """Success criterion for objective."""
    name: str
    description: str
    validator: Optional[Callable[[Any], bool]] = None
    is_met: bool = False
    validated_at: Optional[datetime] = None

    def validate(self, data: Any) -> bool:
        """Validate criterion."""
        if self.validator:
            try:
                self.is_met = self.validator(data)
            except Exception as e:
                logger.error(f"Validation error: {e}")
                self.is_met = False
        else:
            self.is_met = True

        if self.is_met:
            self.validated_at = datetime.now()

        return self.is_met


@dataclass
class Milestone:
    """Milestone within an objective."""
    id: str
    name: str
    description: str = ""

    # Target
    target_value: Any = None
    current_value: Any = None

    # Status
    status: ObjectiveStatus = ObjectiveStatus.NOT_STARTED

    # Timing
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        return self.status == ObjectiveStatus.COMPLETED

    @property
    def progress(self) -> float:
        if self.is_complete:
            return 1.0
        if self.target_value and self.current_value:
            try:
                return min(1.0, float(self.current_value) / float(self.target_value))
            except:
                pass
        return 0.0


@dataclass
class Objective:
    """An objective to be tracked."""
    id: str
    name: str
    description: str = ""

    # Classification
    type: ObjectiveType = ObjectiveType.PRIMARY
    weight: float = 1.0  # Weight for progress calculation

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)

    # Milestones
    milestones: List[Milestone] = field(default_factory=list)

    # Success criteria
    success_criteria: List[SuccessCriterion] = field(default_factory=list)

    # Status
    status: ObjectiveStatus = ObjectiveStatus.NOT_STARTED
    progress: float = 0.0

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

    # Results
    outputs: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.status == ObjectiveStatus.IN_PROGRESS

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.FAILED,
            ObjectiveStatus.SKIPPED,
        }

    @property
    def is_overdue(self) -> bool:
        if self.deadline and not self.is_terminal:
            return datetime.now() > self.deadline
        return False

    def calculate_progress(self) -> float:
        """Calculate progress from milestones."""
        if not self.milestones:
            return self.progress

        total_progress = sum(m.progress for m in self.milestones)
        return total_progress / len(self.milestones)


class ObjectiveTracker:
    """
    Objective tracking system for BAEL missions.
    """

    def __init__(self):
        # Storage
        self.objectives: Dict[str, Objective] = {}
        self.mission_objectives: Dict[str, Set[str]] = {}  # mission_id -> objective_ids

        # Dependency graph
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._reverse_graph: Dict[str, Set[str]] = {}

        # Callbacks
        self._on_complete: List[Callable[[Objective], None]] = []
        self._on_progress: List[Callable[[Objective, float], None]] = []

        # Stats
        self.stats = {
            "objectives_created": 0,
            "objectives_completed": 0,
            "objectives_failed": 0,
            "milestones_completed": 0,
        }

    def create_objective(
        self,
        id: str,
        name: str,
        mission_id: Optional[str] = None,
        **kwargs,
    ) -> Objective:
        """
        Create a new objective.

        Args:
            id: Objective ID
            name: Objective name
            mission_id: Associated mission ID
            **kwargs: Additional objective attributes

        Returns:
            Created Objective
        """
        self.stats["objectives_created"] += 1

        objective = Objective(id=id, name=name, **kwargs)
        self.objectives[id] = objective

        # Associate with mission
        if mission_id:
            if mission_id not in self.mission_objectives:
                self.mission_objectives[mission_id] = set()
            self.mission_objectives[mission_id].add(id)

        # Update dependency graph
        self._update_dependency_graph(objective)

        logger.info(f"Created objective: {name} ({id})")

        return objective

    def _update_dependency_graph(self, objective: Objective) -> None:
        """Update dependency tracking."""
        self._dependency_graph[objective.id] = set(objective.depends_on)

        for dep in objective.depends_on:
            if dep not in self._reverse_graph:
                self._reverse_graph[dep] = set()
            self._reverse_graph[dep].add(objective.id)

    def add_milestone(
        self,
        objective_id: str,
        milestone: Milestone,
    ) -> bool:
        """Add milestone to objective."""
        objective = self.objectives.get(objective_id)
        if not objective:
            return False

        objective.milestones.append(milestone)
        return True

    def update_milestone(
        self,
        objective_id: str,
        milestone_id: str,
        current_value: Any = None,
        status: Optional[ObjectiveStatus] = None,
    ) -> bool:
        """Update milestone progress."""
        objective = self.objectives.get(objective_id)
        if not objective:
            return False

        for milestone in objective.milestones:
            if milestone.id == milestone_id:
                if current_value is not None:
                    milestone.current_value = current_value

                if status:
                    milestone.status = status
                    if status == ObjectiveStatus.COMPLETED:
                        milestone.completed_at = datetime.now()
                        self.stats["milestones_completed"] += 1

                # Recalculate objective progress
                self._update_objective_progress(objective)

                return True

        return False

    def _update_objective_progress(self, objective: Objective) -> None:
        """Update objective progress based on milestones."""
        old_progress = objective.progress
        objective.progress = objective.calculate_progress()

        # Notify if progress changed
        if objective.progress != old_progress:
            for callback in self._on_progress:
                try:
                    callback(objective, objective.progress)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")

        # Check for completion
        if objective.progress >= 1.0 and objective.status != ObjectiveStatus.COMPLETED:
            self._check_completion(objective)

    def _check_completion(self, objective: Objective) -> bool:
        """Check if objective meets completion criteria."""
        # Check all milestones complete
        if objective.milestones:
            all_complete = all(m.is_complete for m in objective.milestones)
            if not all_complete:
                return False

        # Check success criteria
        for criterion in objective.success_criteria:
            if not criterion.is_met:
                return False

        # Mark complete
        self.complete_objective(objective.id)
        return True

    def start_objective(self, objective_id: str) -> bool:
        """Start tracking an objective."""
        objective = self.objectives.get(objective_id)
        if not objective:
            return False

        # Check dependencies
        if not self._can_start(objective):
            objective.status = ObjectiveStatus.BLOCKED
            return False

        objective.status = ObjectiveStatus.IN_PROGRESS
        objective.started_at = datetime.now()

        logger.info(f"Started objective: {objective.name}")

        return True

    def _can_start(self, objective: Objective) -> bool:
        """Check if objective can start (dependencies met)."""
        for dep_id in objective.depends_on:
            dep = self.objectives.get(dep_id)
            if not dep or dep.status != ObjectiveStatus.COMPLETED:
                return False
        return True

    def complete_objective(
        self,
        objective_id: str,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark objective as completed."""
        objective = self.objectives.get(objective_id)
        if not objective:
            return False

        objective.status = ObjectiveStatus.COMPLETED
        objective.completed_at = datetime.now()
        objective.progress = 1.0

        if outputs:
            objective.outputs.update(outputs)

        self.stats["objectives_completed"] += 1

        # Notify callbacks
        for callback in self._on_complete:
            try:
                callback(objective)
            except Exception as e:
                logger.error(f"Completion callback error: {e}")

        # Unblock dependents
        self._unblock_dependents(objective_id)

        logger.info(f"Completed objective: {objective.name}")

        return True

    def fail_objective(
        self,
        objective_id: str,
        reason: str = "",
    ) -> bool:
        """Mark objective as failed."""
        objective = self.objectives.get(objective_id)
        if not objective:
            return False

        objective.status = ObjectiveStatus.FAILED
        objective.notes.append(f"Failed: {reason}")

        self.stats["objectives_failed"] += 1

        logger.warning(f"Failed objective: {objective.name} - {reason}")

        return True

    def _unblock_dependents(self, objective_id: str) -> None:
        """Unblock objectives that depend on completed objective."""
        dependents = self._reverse_graph.get(objective_id, set())

        for dep_id in dependents:
            dep = self.objectives.get(dep_id)
            if dep and dep.status == ObjectiveStatus.BLOCKED:
                if self._can_start(dep):
                    dep.status = ObjectiveStatus.NOT_STARTED

    def get_ready_objectives(self, mission_id: Optional[str] = None) -> List[Objective]:
        """Get objectives ready to start."""
        if mission_id:
            obj_ids = self.mission_objectives.get(mission_id, set())
            objectives = [self.objectives[id] for id in obj_ids if id in self.objectives]
        else:
            objectives = list(self.objectives.values())

        ready = []
        for obj in objectives:
            if obj.status == ObjectiveStatus.NOT_STARTED and self._can_start(obj):
                ready.append(obj)

        return ready

    def get_blocked_objectives(self, mission_id: Optional[str] = None) -> List[Objective]:
        """Get blocked objectives."""
        if mission_id:
            obj_ids = self.mission_objectives.get(mission_id, set())
            objectives = [self.objectives[id] for id in obj_ids if id in self.objectives]
        else:
            objectives = list(self.objectives.values())

        return [obj for obj in objectives if obj.status == ObjectiveStatus.BLOCKED]

    def get_mission_progress(self, mission_id: str) -> float:
        """Calculate overall mission progress."""
        obj_ids = self.mission_objectives.get(mission_id, set())
        if not obj_ids:
            return 0.0

        total_weight = 0.0
        weighted_progress = 0.0

        for obj_id in obj_ids:
            obj = self.objectives.get(obj_id)
            if obj:
                total_weight += obj.weight
                weighted_progress += obj.progress * obj.weight

        if total_weight == 0:
            return 0.0

        return weighted_progress / total_weight

    def get_mission_summary(self, mission_id: str) -> Dict[str, Any]:
        """Get summary of mission objectives."""
        obj_ids = self.mission_objectives.get(mission_id, set())

        summary = {
            "total": len(obj_ids),
            "completed": 0,
            "in_progress": 0,
            "blocked": 0,
            "not_started": 0,
            "failed": 0,
            "progress": 0.0,
        }

        for obj_id in obj_ids:
            obj = self.objectives.get(obj_id)
            if obj:
                status_key = obj.status.value
                if status_key in summary:
                    summary[status_key] += 1
                elif obj.status == ObjectiveStatus.IN_PROGRESS:
                    summary["in_progress"] += 1

        summary["progress"] = self.get_mission_progress(mission_id)

        return summary

    def on_complete(self, callback: Callable[[Objective], None]) -> None:
        """Register completion callback."""
        self._on_complete.append(callback)

    def on_progress(self, callback: Callable[[Objective, float], None]) -> None:
        """Register progress callback."""
        self._on_progress.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        return {
            **self.stats,
            "total_objectives": len(self.objectives),
            "total_missions": len(self.mission_objectives),
        }


def demo():
    """Demonstrate objective tracker."""
    print("=" * 60)
    print("BAEL Objective Tracker Demo")
    print("=" * 60)

    tracker = ObjectiveTracker()
    mission_id = "mission_001"

    # Create objectives with dependencies
    obj1 = tracker.create_objective(
        id="obj_1",
        name="Gather Data",
        mission_id=mission_id,
        type=ObjectiveType.PRIMARY,
    )

    obj2 = tracker.create_objective(
        id="obj_2",
        name="Analyze Data",
        mission_id=mission_id,
        depends_on=["obj_1"],
    )

    obj3 = tracker.create_objective(
        id="obj_3",
        name="Generate Report",
        mission_id=mission_id,
        depends_on=["obj_2"],
    )

    # Add milestones
    tracker.add_milestone("obj_1", Milestone(
        id="m1",
        name="Collect sources",
        target_value=10,
    ))

    print(f"\nCreated {len(tracker.objectives)} objectives")

    # Check ready objectives
    ready = tracker.get_ready_objectives(mission_id)
    print(f"Ready to start: {[o.name for o in ready]}")

    # Start first objective
    tracker.start_objective("obj_1")

    # Update milestone
    tracker.update_milestone("obj_1", "m1", current_value=5)
    print(f"Obj1 progress: {obj1.progress:.0%}")

    # Complete
    tracker.update_milestone("obj_1", "m1", current_value=10, status=ObjectiveStatus.COMPLETED)
    tracker.complete_objective("obj_1")

    # Check what's ready now
    ready = tracker.get_ready_objectives(mission_id)
    print(f"Now ready: {[o.name for o in ready]}")

    # Mission summary
    summary = tracker.get_mission_summary(mission_id)
    print(f"\nMission summary: {summary}")

    print(f"\nStats: {tracker.get_stats()}")


if __name__ == "__main__":
    demo()
