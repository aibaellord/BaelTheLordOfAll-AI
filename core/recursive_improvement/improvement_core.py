"""
🔄 IMPROVEMENT CORE 🔄
======================
Self-assessment and goals.

Features:
- Capability measurement
- Performance tracking
- Goal definition
"""

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid


class CapabilityLevel(Enum):
    """Capability proficiency levels"""
    NONE = 0
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    MASTER = 6
    TRANSCENDENT = 7


@dataclass
class Capability:
    """A system capability"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Current level
    level: CapabilityLevel = CapabilityLevel.NONE

    # Numerical proficiency (0.0 - 1.0)
    proficiency: float = 0.0

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Category
    category: str = ""

    # Metadata
    acquired_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

    def update_level(self):
        """Update level based on proficiency"""
        if self.proficiency >= 0.95:
            self.level = CapabilityLevel.TRANSCENDENT
        elif self.proficiency >= 0.85:
            self.level = CapabilityLevel.MASTER
        elif self.proficiency >= 0.75:
            self.level = CapabilityLevel.EXPERT
        elif self.proficiency >= 0.60:
            self.level = CapabilityLevel.ADVANCED
        elif self.proficiency >= 0.45:
            self.level = CapabilityLevel.INTERMEDIATE
        elif self.proficiency >= 0.30:
            self.level = CapabilityLevel.BEGINNER
        elif self.proficiency >= 0.15:
            self.level = CapabilityLevel.NOVICE
        else:
            self.level = CapabilityLevel.NONE

    def use(self):
        """Record capability usage"""
        self.usage_count += 1
        self.last_used = datetime.now()


@dataclass
class PerformanceMetric:
    """A performance metric"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Current value
    value: float = 0.0

    # Target
    target: float = 1.0

    # Historical values
    history: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)

    # Bounds
    min_value: float = 0.0
    max_value: float = 1.0

    # Higher is better?
    higher_is_better: bool = True

    def record(self, value: float):
        """Record new value"""
        self.history.append(value)
        self.timestamps.append(datetime.now())
        self.value = value

    def get_trend(self, window: int = 10) -> float:
        """Get trend direction (-1 to 1)"""
        if len(self.history) < 2:
            return 0.0

        recent = self.history[-window:] if len(self.history) >= window else self.history

        if len(recent) < 2:
            return 0.0

        # Calculate trend using linear regression slope
        n = len(recent)
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Normalize to -1 to 1
        return max(-1.0, min(1.0, slope * 10))

    def progress(self) -> float:
        """Progress toward target (0.0 to 1.0)"""
        if self.higher_is_better:
            return min(1.0, self.value / self.target) if self.target != 0 else 0.0
        else:
            return min(1.0, self.target / self.value) if self.value != 0 else 0.0


@dataclass
class ImprovementGoal:
    """An improvement goal"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Target capability or metric
    target_type: str = ""  # "capability" or "metric"
    target_id: str = ""

    # Current and target values
    current_value: float = 0.0
    target_value: float = 1.0

    # Priority (1-10)
    priority: int = 5

    # Timeline
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None

    # Status
    is_complete: bool = False
    progress: float = 0.0

    # Sub-goals
    sub_goals: List['ImprovementGoal'] = field(default_factory=list)

    def update_progress(self):
        """Update progress"""
        if self.sub_goals:
            self.progress = sum(g.progress for g in self.sub_goals) / len(self.sub_goals)
        else:
            diff = self.target_value - self.current_value
            if diff == 0:
                self.progress = 1.0
            else:
                self.progress = min(1.0, max(0.0,
                    (self.current_value / self.target_value) if self.target_value != 0 else 0
                ))

        self.is_complete = self.progress >= 1.0


@dataclass
class CapabilityAssessment:
    """Full capability assessment"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

    # Assessed capabilities
    capabilities: Dict[str, Capability] = field(default_factory=dict)

    # Metrics
    metrics: Dict[str, PerformanceMetric] = field(default_factory=dict)

    # Overall scores
    overall_proficiency: float = 0.0
    overall_health: float = 1.0

    # Strengths and weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def calculate_overall(self):
        """Calculate overall scores"""
        if self.capabilities:
            self.overall_proficiency = sum(
                c.proficiency for c in self.capabilities.values()
            ) / len(self.capabilities)

        if self.metrics:
            self.overall_health = sum(
                m.progress() for m in self.metrics.values()
            ) / len(self.metrics)

        # Identify strengths (top 20%)
        sorted_caps = sorted(
            self.capabilities.values(),
            key=lambda c: c.proficiency,
            reverse=True
        )
        threshold = int(len(sorted_caps) * 0.2) or 1
        self.strengths = [c.name for c in sorted_caps[:threshold]]

        # Identify weaknesses (bottom 20%)
        self.weaknesses = [c.name for c in sorted_caps[-threshold:]]


class SelfAssessor:
    """
    Self-assessment engine.
    """

    def __init__(self):
        self.capabilities: Dict[str, Capability] = {}
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.goals: Dict[str, ImprovementGoal] = {}

        self.assessments: List[CapabilityAssessment] = []

        # Assessment functions
        self.capability_tests: Dict[str, Callable[[], float]] = {}

    def register_capability(self, capability: Capability):
        """Register a capability"""
        self.capabilities[capability.id] = capability

    def register_metric(self, metric: PerformanceMetric):
        """Register a metric"""
        self.metrics[metric.id] = metric

    def register_test(self, capability_id: str, test: Callable[[], float]):
        """Register capability test"""
        self.capability_tests[capability_id] = test

    def assess_capability(self, capability_id: str) -> float:
        """Assess single capability"""
        if capability_id not in self.capabilities:
            return 0.0

        cap = self.capabilities[capability_id]

        # Run test if available
        if capability_id in self.capability_tests:
            try:
                score = self.capability_tests[capability_id]()
                cap.proficiency = max(0.0, min(1.0, score))
                cap.update_level()
            except Exception:
                pass

        return cap.proficiency

    def full_assessment(self) -> CapabilityAssessment:
        """Perform full self-assessment"""
        assessment = CapabilityAssessment()

        # Assess all capabilities
        for cap_id, cap in self.capabilities.items():
            self.assess_capability(cap_id)
            assessment.capabilities[cap_id] = cap

        # Copy metrics
        assessment.metrics = self.metrics.copy()

        # Calculate overall scores
        assessment.calculate_overall()

        # Generate recommendations
        assessment.recommendations = self._generate_recommendations(assessment)

        self.assessments.append(assessment)
        return assessment

    def _generate_recommendations(
        self,
        assessment: CapabilityAssessment
    ) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        # Recommend improving weaknesses
        for weakness in assessment.weaknesses:
            recommendations.append(f"Improve {weakness} capability")

        # Recommend based on metrics
        for metric_id, metric in assessment.metrics.items():
            if metric.progress() < 0.5:
                recommendations.append(f"Focus on improving {metric.name}")
            elif metric.get_trend() < 0:
                recommendations.append(f"Reverse declining trend in {metric.name}")

        # Recommend leveraging strengths
        for strength in assessment.strengths[:2]:
            recommendations.append(f"Leverage {strength} for complex tasks")

        return recommendations

    def set_goal(self, goal: ImprovementGoal):
        """Set improvement goal"""
        self.goals[goal.id] = goal

    def update_goals(self):
        """Update all goal progress"""
        for goal in self.goals.values():
            if goal.target_type == "capability" and goal.target_id in self.capabilities:
                goal.current_value = self.capabilities[goal.target_id].proficiency
            elif goal.target_type == "metric" and goal.target_id in self.metrics:
                goal.current_value = self.metrics[goal.target_id].value

            goal.update_progress()

    def get_priority_goals(self, n: int = 5) -> List[ImprovementGoal]:
        """Get top priority goals"""
        active_goals = [g for g in self.goals.values() if not g.is_complete]
        return sorted(active_goals, key=lambda g: g.priority, reverse=True)[:n]

    def get_improvement_plan(self) -> Dict[str, Any]:
        """Generate improvement plan"""
        assessment = self.full_assessment()

        return {
            'current_state': {
                'overall_proficiency': assessment.overall_proficiency,
                'overall_health': assessment.overall_health,
                'strengths': assessment.strengths,
                'weaknesses': assessment.weaknesses,
            },
            'goals': [
                {
                    'name': g.name,
                    'progress': g.progress,
                    'priority': g.priority
                }
                for g in self.get_priority_goals()
            ],
            'recommendations': assessment.recommendations,
            'next_actions': self._prioritize_actions(assessment)
        }

    def _prioritize_actions(
        self,
        assessment: CapabilityAssessment
    ) -> List[Dict[str, Any]]:
        """Prioritize improvement actions"""
        actions = []

        # High-priority goal actions
        for goal in self.get_priority_goals(3):
            actions.append({
                'action': f"Work toward: {goal.name}",
                'priority': 'high',
                'expected_impact': goal.priority / 10
            })

        # Address weaknesses
        for weakness in assessment.weaknesses[:2]:
            actions.append({
                'action': f"Train {weakness} capability",
                'priority': 'medium',
                'expected_impact': 0.3
            })

        return actions


# Export all
__all__ = [
    'CapabilityLevel',
    'Capability',
    'PerformanceMetric',
    'ImprovementGoal',
    'CapabilityAssessment',
    'SelfAssessor',
]
