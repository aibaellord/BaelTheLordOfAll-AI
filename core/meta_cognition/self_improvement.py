"""
⚡ SELF-IMPROVEMENT ⚡
=====================
Mechanisms for continuous self-improvement.

Components:
- Learning opportunity detection
- Skill gap analysis
- Improvement planning
- Meta-learning
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class LearningType(Enum):
    """Types of learning"""
    REINFORCEMENT = auto()   # Learn from rewards
    SUPERVISED = auto()      # Learn from examples
    UNSUPERVISED = auto()    # Learn patterns
    TRANSFER = auto()        # Apply existing knowledge
    META = auto()            # Learn how to learn


@dataclass
class LearningOpportunity:
    """An opportunity to learn something new"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill: str = ""
    domain: str = ""
    learning_type: LearningType = LearningType.REINFORCEMENT
    difficulty: float = 0.5
    expected_value: float = 0.5
    prerequisites: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SkillGap:
    """Identified gap in skills"""
    skill: str
    current_level: float
    required_level: float
    gap_size: float = 0.0
    priority: float = 0.5
    blocking_tasks: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.gap_size = max(0, self.required_level - self.current_level)


@dataclass
class LearningGoal:
    """A goal for learning"""
    skill: str
    target_level: float
    deadline: Optional[datetime] = None
    priority: float = 0.5
    progress: float = 0.0


@dataclass
class ImprovementPlan:
    """Plan for self-improvement"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goals: List[LearningGoal] = field(default_factory=list)
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    current_phase: int = 0
    status: str = "active"
    created: datetime = field(default_factory=datetime.now)

    def add_goal(self, skill: str, target: float, priority: float = 0.5):
        """Add learning goal"""
        self.goals.append(LearningGoal(
            skill=skill,
            target_level=target,
            priority=priority
        ))

    def update_progress(self, skill: str, new_level: float):
        """Update progress for skill"""
        for goal in self.goals:
            if goal.skill == skill:
                goal.progress = min(new_level / goal.target_level, 1.0)

    def is_complete(self) -> bool:
        """Check if plan is complete"""
        return all(g.progress >= 1.0 for g in self.goals)


class SelfImprover:
    """
    Manages self-improvement processes.
    """

    def __init__(self):
        # Skill tracking
        self.skills: Dict[str, float] = {}  # skill -> level
        self.skill_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)

        # Learning tracking
        self.opportunities: List[LearningOpportunity] = []
        self.completed_learning: List[LearningOpportunity] = []

        # Improvement plans
        self.active_plan: Optional[ImprovementPlan] = None
        self.completed_plans: List[ImprovementPlan] = []

        # Skill gaps
        self.gaps: List[SkillGap] = []

    def set_skill_level(
        self,
        skill: str,
        level: float
    ):
        """Set current skill level"""
        level = max(0, min(1, level))
        self.skills[skill] = level
        self.skill_history[skill].append((datetime.now(), level))

    def get_skill_level(self, skill: str) -> float:
        """Get current skill level"""
        return self.skills.get(skill, 0.0)

    def update_skill(
        self,
        skill: str,
        delta: float,
        source: str = "practice"
    ):
        """Update skill level"""
        current = self.get_skill_level(skill)

        # Diminishing returns at high levels
        effective_delta = delta * (1 - current * 0.5)

        new_level = max(0, min(1, current + effective_delta))
        self.set_skill_level(skill, new_level)

        # Update active plan
        if self.active_plan:
            self.active_plan.update_progress(skill, new_level)

    def identify_gaps(
        self,
        required_skills: Dict[str, float]
    ) -> List[SkillGap]:
        """Identify skill gaps for required skills"""
        gaps = []

        for skill, required in required_skills.items():
            current = self.get_skill_level(skill)

            if current < required:
                gap = SkillGap(
                    skill=skill,
                    current_level=current,
                    required_level=required
                )
                gaps.append(gap)

        # Sort by gap size
        gaps.sort(key=lambda g: -g.gap_size)
        self.gaps = gaps

        return gaps

    def create_opportunity(
        self,
        skill: str,
        domain: str,
        learning_type: LearningType = LearningType.REINFORCEMENT,
        difficulty: float = 0.5
    ) -> LearningOpportunity:
        """Create learning opportunity"""
        # Calculate expected value based on skill gap
        current = self.get_skill_level(skill)
        expected_value = (1 - current) * (1 - abs(difficulty - current))

        opportunity = LearningOpportunity(
            skill=skill,
            domain=domain,
            learning_type=learning_type,
            difficulty=difficulty,
            expected_value=expected_value
        )

        self.opportunities.append(opportunity)
        return opportunity

    def get_best_opportunities(
        self,
        n: int = 5
    ) -> List[LearningOpportunity]:
        """Get best learning opportunities"""
        # Filter active opportunities
        active = [o for o in self.opportunities if o not in self.completed_learning]

        # Sort by expected value
        sorted_opps = sorted(active, key=lambda o: -o.expected_value)

        return sorted_opps[:n]

    def complete_learning(
        self,
        opportunity_id: str,
        success: bool,
        improvement: float = 0.0
    ):
        """Mark learning as complete"""
        for opp in self.opportunities:
            if opp.id == opportunity_id:
                self.completed_learning.append(opp)

                if success and improvement > 0:
                    self.update_skill(opp.skill, improvement, "learning")

                break

    def create_plan(
        self,
        target_skills: Dict[str, float]
    ) -> ImprovementPlan:
        """Create improvement plan for target skills"""
        plan = ImprovementPlan()

        for skill, target in target_skills.items():
            current = self.get_skill_level(skill)
            if target > current:
                priority = (target - current) / target
                plan.add_goal(skill, target, priority)

        # Sort goals by priority
        plan.goals.sort(key=lambda g: -g.priority)

        # Create milestones
        for i, goal in enumerate(plan.goals):
            plan.milestones.append({
                'phase': i,
                'skill': goal.skill,
                'target': goal.target_level,
                'status': 'pending'
            })

        self.active_plan = plan
        return plan

    def get_learning_velocity(
        self,
        skill: str,
        window_days: int = 30
    ) -> float:
        """Calculate learning velocity for skill"""
        history = self.skill_history.get(skill, [])

        if len(history) < 2:
            return 0.0

        # Filter to window
        now = datetime.now()
        cutoff = now.timestamp() - window_days * 86400

        recent = [
            (ts, level) for ts, level in history
            if ts.timestamp() > cutoff
        ]

        if len(recent) < 2:
            return 0.0

        # Calculate slope
        first_ts, first_level = recent[0]
        last_ts, last_level = recent[-1]

        time_delta = (last_ts - first_ts).total_seconds()
        if time_delta == 0:
            return 0.0

        level_delta = last_level - first_level

        # Velocity in level per day
        return level_delta / (time_delta / 86400)

    def estimate_time_to_goal(
        self,
        skill: str,
        target_level: float
    ) -> Optional[float]:
        """Estimate days to reach target level"""
        current = self.get_skill_level(skill)

        if current >= target_level:
            return 0.0

        velocity = self.get_learning_velocity(skill)

        if velocity <= 0:
            return None  # Cannot estimate

        gap = target_level - current
        return gap / velocity


@dataclass
class MetaLearningExperience:
    """Experience of learning something"""
    skill: str
    approach: str
    success: bool
    efficiency: float  # Learning speed
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class MetaLearner:
    """
    Learns how to learn better.

    Tracks which learning approaches work best
    for different types of skills.
    """

    def __init__(self):
        self.experiences: List[MetaLearningExperience] = []

        # Track approach effectiveness by skill type
        self.approach_success: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def record_experience(
        self,
        skill: str,
        approach: str,
        success: bool,
        efficiency: float,
        context: Dict[str, Any] = None
    ):
        """Record learning experience"""
        exp = MetaLearningExperience(
            skill=skill,
            approach=approach,
            success=success,
            efficiency=efficiency,
            context=context or {}
        )
        self.experiences.append(exp)

        # Update approach statistics
        skill_type = self._get_skill_type(skill)
        self.approach_success[skill_type][approach].append(efficiency if success else 0)

    def _get_skill_type(self, skill: str) -> str:
        """Categorize skill into type"""
        # Simplified categorization
        if any(kw in skill.lower() for kw in ['code', 'program', 'algorithm']):
            return 'technical'
        elif any(kw in skill.lower() for kw in ['communicate', 'social', 'write']):
            return 'social'
        elif any(kw in skill.lower() for kw in ['math', 'logic', 'analyze']):
            return 'analytical'
        elif any(kw in skill.lower() for kw in ['create', 'design', 'invent']):
            return 'creative'
        else:
            return 'general'

    def get_best_approach(
        self,
        skill: str
    ) -> Optional[str]:
        """Get best learning approach for skill"""
        skill_type = self._get_skill_type(skill)
        approaches = self.approach_success.get(skill_type, {})

        if not approaches:
            return None

        # Calculate average efficiency for each approach
        avg_efficiency = {}
        for approach, efficiencies in approaches.items():
            if efficiencies:
                avg_efficiency[approach] = np.mean(efficiencies)

        if not avg_efficiency:
            return None

        return max(avg_efficiency, key=avg_efficiency.get)

    def suggest_approach(
        self,
        skill: str,
        available_approaches: List[str]
    ) -> str:
        """Suggest learning approach"""
        if not available_approaches:
            return "practice"

        best = self.get_best_approach(skill)

        if best and best in available_approaches:
            return best

        # Default to exploration
        skill_type = self._get_skill_type(skill)
        approaches = self.approach_success.get(skill_type, {})

        # Try least-explored approach
        exploration_counts = {
            approach: len(approaches.get(approach, []))
            for approach in available_approaches
        }

        return min(exploration_counts, key=exploration_counts.get)

    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze learning patterns"""
        patterns = {
            'total_experiences': len(self.experiences),
            'skill_types': {},
            'best_approaches': {}
        }

        # By skill type
        for skill_type, approaches in self.approach_success.items():
            patterns['skill_types'][skill_type] = {
                'approaches_tried': len(approaches),
                'total_attempts': sum(len(v) for v in approaches.values())
            }

            # Find best approach for this type
            if approaches:
                avg_eff = {
                    app: np.mean(eff) if eff else 0
                    for app, eff in approaches.items()
                }
                if avg_eff:
                    patterns['best_approaches'][skill_type] = max(
                        avg_eff, key=avg_eff.get
                    )

        return patterns


# Export all
__all__ = [
    'LearningType',
    'LearningOpportunity',
    'SkillGap',
    'LearningGoal',
    'ImprovementPlan',
    'SelfImprover',
    'MetaLearningExperience',
    'MetaLearner',
]
