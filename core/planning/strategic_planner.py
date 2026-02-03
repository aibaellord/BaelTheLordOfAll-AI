#!/usr/bin/env python3
"""
BAEL - Strategic Planner
Long-term goal planning and strategy formulation.

This module implements sophisticated strategic planning
for formulating, tracking, and achieving long-term goals
with adaptive strategy adjustment.

Features:
- Vision and mission definition
- Strategic goal hierarchy
- Strategy formulation
- Resource allocation planning
- Milestone tracking
- Risk assessment
- Adaptive replanning
- Multi-horizon planning
- Competitive analysis
- Success metrics
- Strategy execution monitoring
- Scenario planning
"""

import asyncio
import logging
import math
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class StrategicHorizon(Enum):
    """Time horizons for strategic planning."""
    IMMEDIATE = "immediate"      # Hours to days
    SHORT_TERM = "short_term"    # Days to weeks
    MEDIUM_TERM = "medium_term"  # Weeks to months
    LONG_TERM = "long_term"      # Months to years
    VISIONARY = "visionary"      # Years to decades


class GoalState(Enum):
    """State of a strategic goal."""
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    DEFERRED = "deferred"


class StrategyType(Enum):
    """Types of strategies."""
    GROWTH = "growth"
    OPTIMIZATION = "optimization"
    DEFENSIVE = "defensive"
    EXPLORATORY = "exploratory"
    TRANSFORMATIONAL = "transformational"
    MAINTENANCE = "maintenance"


class RiskLevel(Enum):
    """Risk levels for strategic decisions."""
    MINIMAL = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    CRITICAL = 5


class ResourcePriority(Enum):
    """Priority levels for resource allocation."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPPORTUNISTIC = "opportunistic"


class MilestoneType(Enum):
    """Types of milestones."""
    DELIVERABLE = "deliverable"
    METRIC = "metric"
    CAPABILITY = "capability"
    DECISION = "decision"
    EXTERNAL = "external"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class StrategicVision:
    """The overarching vision."""
    statement: str = ""
    core_values: List[str] = field(default_factory=list)
    purpose: str = ""
    aspirations: List[str] = field(default_factory=list)
    timeframe_years: int = 5


@dataclass
class SuccessMetric:
    """A metric for measuring success."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    current_value: float = 0.0
    target_value: float = 0.0
    unit: str = ""
    measurement_frequency: str = "daily"
    trend: List[float] = field(default_factory=list)

    @property
    def progress(self) -> float:
        """Calculate progress toward target."""
        if self.target_value == 0:
            return 0.0
        return min(1.0, self.current_value / self.target_value)


@dataclass
class Risk:
    """A strategic risk."""
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    level: RiskLevel = RiskLevel.MODERATE
    probability: float = 0.5  # 0.0 to 1.0
    impact: float = 0.5  # 0.0 to 1.0
    mitigations: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    status: str = "monitoring"

    @property
    def risk_score(self) -> float:
        """Calculate overall risk score."""
        return self.probability * self.impact * self.level.value


@dataclass
class Milestone:
    """A strategic milestone."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    type: MilestoneType = MilestoneType.DELIVERABLE
    target_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    progress: float = 0.0

    @property
    def is_complete(self) -> bool:
        return self.progress >= 1.0


@dataclass
class ResourceAllocation:
    """Resource allocation for a goal."""
    resource_type: str = ""
    allocated_amount: float = 0.0
    consumed_amount: float = 0.0
    priority: ResourcePriority = ResourcePriority.MEDIUM
    constraints: List[str] = field(default_factory=list)

    @property
    def remaining(self) -> float:
        return max(0, self.allocated_amount - self.consumed_amount)


@dataclass
class StrategicGoal:
    """A strategic goal."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    horizon: StrategicHorizon = StrategicHorizon.MEDIUM_TERM
    state: GoalState = GoalState.DRAFT
    parent_id: Optional[str] = None
    sub_goal_ids: List[str] = field(default_factory=list)
    metrics: List[SuccessMetric] = field(default_factory=list)
    milestones: List[Milestone] = field(default_factory=list)
    resources: List[ResourceAllocation] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10 scale
    confidence: float = 0.5  # Confidence in achieving
    created_at: datetime = field(default_factory=datetime.now)
    target_date: Optional[datetime] = None

    @property
    def overall_progress(self) -> float:
        """Calculate overall progress."""
        if not self.milestones and not self.metrics:
            return 0.0

        milestone_progress = (
            sum(m.progress for m in self.milestones) / len(self.milestones)
            if self.milestones else 0.0
        )
        metric_progress = (
            sum(m.progress for m in self.metrics) / len(self.metrics)
            if self.metrics else 0.0
        )

        if self.milestones and self.metrics:
            return (milestone_progress + metric_progress) / 2
        return milestone_progress or metric_progress

    @property
    def risk_exposure(self) -> float:
        """Calculate overall risk exposure."""
        if not self.risks:
            return 0.0
        return sum(r.risk_score for r in self.risks) / len(self.risks)


@dataclass
class Strategy:
    """A strategic approach."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    type: StrategyType = StrategyType.GROWTH
    goal_ids: List[str] = field(default_factory=list)
    tactics: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    success_probability: float = 0.5
    resource_requirements: Dict[str, float] = field(default_factory=dict)
    timeline_weeks: int = 12
    active: bool = True


@dataclass
class Scenario:
    """A planning scenario."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    assumptions: Dict[str, Any] = field(default_factory=dict)
    probability: float = 0.33
    impact_assessment: Dict[str, float] = field(default_factory=dict)
    recommended_responses: List[str] = field(default_factory=list)


# =============================================================================
# GOAL HIERARCHY
# =============================================================================

class GoalHierarchy:
    """
    Manages hierarchical goal structure.

    Supports parent-child relationships and propagation.
    """

    def __init__(self):
        self.goals: Dict[str, StrategicGoal] = {}
        self.root_goals: List[str] = []

    def add_goal(
        self,
        goal: StrategicGoal,
        parent_id: Optional[str] = None
    ) -> None:
        """Add a goal to the hierarchy."""
        self.goals[goal.id] = goal

        if parent_id and parent_id in self.goals:
            goal.parent_id = parent_id
            self.goals[parent_id].sub_goal_ids.append(goal.id)
        else:
            self.root_goals.append(goal.id)

    def get_subtree(self, goal_id: str) -> List[StrategicGoal]:
        """Get all goals in subtree."""
        result = []
        goal = self.goals.get(goal_id)

        if goal:
            result.append(goal)
            for sub_id in goal.sub_goal_ids:
                result.extend(self.get_subtree(sub_id))

        return result

    def get_ancestors(self, goal_id: str) -> List[StrategicGoal]:
        """Get all ancestor goals."""
        result = []
        goal = self.goals.get(goal_id)

        while goal and goal.parent_id:
            parent = self.goals.get(goal.parent_id)
            if parent:
                result.append(parent)
                goal = parent
            else:
                break

        return result

    def propagate_progress(self, goal_id: str) -> None:
        """Propagate progress up the hierarchy."""
        goal = self.goals.get(goal_id)

        if not goal:
            return

        # If has sub-goals, calculate progress from them
        if goal.sub_goal_ids:
            sub_progress = []
            for sub_id in goal.sub_goal_ids:
                sub_goal = self.goals.get(sub_id)
                if sub_goal:
                    sub_progress.append(sub_goal.overall_progress)

            if sub_progress:
                avg_progress = sum(sub_progress) / len(sub_progress)
                # Update milestones based on sub-goal progress
                for milestone in goal.milestones:
                    milestone.progress = max(milestone.progress, avg_progress)

        # Propagate to parent
        if goal.parent_id:
            self.propagate_progress(goal.parent_id)

    def get_by_horizon(self, horizon: StrategicHorizon) -> List[StrategicGoal]:
        """Get goals by time horizon."""
        return [g for g in self.goals.values() if g.horizon == horizon]

    def get_blocked_goals(self) -> List[StrategicGoal]:
        """Get all blocked goals."""
        return [g for g in self.goals.values() if g.state == GoalState.BLOCKED]

    def get_active_goals(self) -> List[StrategicGoal]:
        """Get all active goals."""
        return [
            g for g in self.goals.values()
            if g.state in [GoalState.ACTIVE, GoalState.IN_PROGRESS]
        ]


# =============================================================================
# STRATEGY ANALYZER
# =============================================================================

class StrategyAnalyzer:
    """
    Analyzes and evaluates strategies.

    Provides SWOT analysis and strategy scoring.
    """

    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}

    def add_strategy(self, strategy: Strategy) -> None:
        """Add a strategy for analysis."""
        self.strategies[strategy.id] = strategy

    def analyze_swot(
        self,
        strategy: Strategy,
        context: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Perform SWOT analysis on a strategy."""
        swot = {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": []
        }

        # Analyze strengths
        if strategy.success_probability > 0.7:
            swot["strengths"].append("High probability of success")
        if len(strategy.tactics) > 5:
            swot["strengths"].append("Comprehensive tactical plan")
        if strategy.resource_requirements:
            swot["strengths"].append("Clear resource requirements defined")

        # Analyze weaknesses
        if len(strategy.assumptions) > 3:
            swot["weaknesses"].append("Many assumptions required")
        if strategy.timeline_weeks > 24:
            swot["weaknesses"].append("Extended timeline increases uncertainty")
        if len(strategy.constraints) > 3:
            swot["weaknesses"].append("Multiple constraints limit flexibility")

        # Analyze opportunities (from context)
        if context.get("market_growth", 0) > 0.1:
            swot["opportunities"].append("Growing market conditions")
        if context.get("resource_availability", 0) > 0.7:
            swot["opportunities"].append("Resources available")
        if context.get("competitive_weakness", False):
            swot["opportunities"].append("Competitor vulnerabilities")

        # Analyze threats
        if context.get("market_volatility", 0) > 0.5:
            swot["threats"].append("Market volatility risk")
        if context.get("resource_scarcity", False):
            swot["threats"].append("Resource scarcity")
        if context.get("competitive_pressure", 0) > 0.7:
            swot["threats"].append("Intense competition")

        return swot

    def score_strategy(
        self,
        strategy: Strategy,
        goals: List[StrategicGoal]
    ) -> Dict[str, float]:
        """Score a strategy against goals."""
        scores = {
            "alignment": 0.0,
            "feasibility": 0.0,
            "impact": 0.0,
            "efficiency": 0.0,
            "risk_adjusted": 0.0,
            "overall": 0.0
        }

        # Alignment score - how well does it serve goals
        aligned_goals = [g for g in goals if g.id in strategy.goal_ids]
        if goals:
            scores["alignment"] = len(aligned_goals) / len(goals)

        # Feasibility score
        constraint_penalty = len(strategy.constraints) * 0.05
        assumption_penalty = len(strategy.assumptions) * 0.03
        scores["feasibility"] = max(0, strategy.success_probability - constraint_penalty - assumption_penalty)

        # Impact score - based on goal priorities
        if aligned_goals:
            avg_priority = sum(g.priority for g in aligned_goals) / len(aligned_goals)
            scores["impact"] = avg_priority / 10

        # Efficiency score - tactics per resource unit
        total_resources = sum(strategy.resource_requirements.values())
        if total_resources > 0:
            scores["efficiency"] = min(1.0, len(strategy.tactics) / total_resources)

        # Risk-adjusted score
        goal_risks = []
        for goal in aligned_goals:
            goal_risks.extend(r.risk_score for r in goal.risks)
        avg_risk = sum(goal_risks) / len(goal_risks) if goal_risks else 0.5
        scores["risk_adjusted"] = scores["feasibility"] * (1 - avg_risk * 0.1)

        # Overall score
        weights = {
            "alignment": 0.25,
            "feasibility": 0.20,
            "impact": 0.25,
            "efficiency": 0.15,
            "risk_adjusted": 0.15
        }
        scores["overall"] = sum(
            scores[k] * w for k, w in weights.items()
        )

        return scores

    def recommend_strategy_type(
        self,
        goals: List[StrategicGoal],
        context: Dict[str, Any]
    ) -> StrategyType:
        """Recommend best strategy type for current situation."""
        # Analyze current state
        avg_progress = sum(g.overall_progress for g in goals) / len(goals) if goals else 0
        avg_risk = sum(g.risk_exposure for g in goals) / len(goals) if goals else 0

        market_growth = context.get("market_growth", 0)
        resources_available = context.get("resource_availability", 0.5)
        competitive_pressure = context.get("competitive_pressure", 0.5)

        # Decision logic
        if avg_risk > 0.7:
            return StrategyType.DEFENSIVE
        elif avg_progress > 0.8 and resources_available > 0.6:
            return StrategyType.GROWTH
        elif competitive_pressure > 0.7:
            return StrategyType.DEFENSIVE
        elif market_growth > 0.2 and resources_available > 0.7:
            return StrategyType.GROWTH
        elif avg_progress < 0.3:
            return StrategyType.TRANSFORMATIONAL
        elif resources_available < 0.3:
            return StrategyType.OPTIMIZATION
        else:
            return StrategyType.EXPLORATORY


# =============================================================================
# SCENARIO PLANNER
# =============================================================================

class ScenarioPlanner:
    """
    Plans for multiple possible futures.

    Creates and analyzes strategic scenarios.
    """

    def __init__(self):
        self.scenarios: Dict[str, Scenario] = {}
        self.base_assumptions: Dict[str, Any] = {}

    def create_scenario(
        self,
        name: str,
        assumption_changes: Dict[str, Any],
        probability: float = 0.33
    ) -> Scenario:
        """Create a new scenario."""
        # Merge base assumptions with changes
        assumptions = dict(self.base_assumptions)
        assumptions.update(assumption_changes)

        scenario = Scenario(
            name=name,
            assumptions=assumptions,
            probability=probability
        )

        self.scenarios[scenario.id] = scenario
        return scenario

    def generate_scenarios(self, num_scenarios: int = 3) -> List[Scenario]:
        """Generate diverse scenarios."""
        scenarios = []

        # Best case scenario
        best = self.create_scenario(
            "Best Case",
            {
                "market_growth": 0.3,
                "resource_availability": 0.9,
                "competitive_pressure": 0.2,
                "success_rate": 0.9
            },
            probability=0.2
        )
        scenarios.append(best)

        # Base case scenario
        base = self.create_scenario(
            "Base Case",
            {
                "market_growth": 0.1,
                "resource_availability": 0.6,
                "competitive_pressure": 0.5,
                "success_rate": 0.6
            },
            probability=0.5
        )
        scenarios.append(base)

        # Worst case scenario
        worst = self.create_scenario(
            "Worst Case",
            {
                "market_growth": -0.1,
                "resource_availability": 0.3,
                "competitive_pressure": 0.8,
                "success_rate": 0.3
            },
            probability=0.3
        )
        scenarios.append(worst)

        return scenarios

    def assess_goal_under_scenarios(
        self,
        goal: StrategicGoal,
        scenarios: List[Scenario]
    ) -> Dict[str, Dict[str, float]]:
        """Assess goal achievement under different scenarios."""
        assessments = {}

        for scenario in scenarios:
            success_rate = scenario.assumptions.get("success_rate", 0.5)
            resource_factor = scenario.assumptions.get("resource_availability", 0.5)

            # Calculate adjusted probability
            base_confidence = goal.confidence
            adjusted_confidence = base_confidence * success_rate * resource_factor

            # Calculate expected progress
            expected_progress = goal.overall_progress + (
                (1 - goal.overall_progress) * adjusted_confidence
            )

            # Risk adjustment
            risk_factor = 1 - (goal.risk_exposure * (1 - success_rate))
            final_expected = expected_progress * risk_factor

            assessments[scenario.name] = {
                "probability": scenario.probability,
                "expected_progress": final_expected,
                "confidence": adjusted_confidence,
                "risk_adjusted": final_expected * scenario.probability
            }

        return assessments

    def expected_value(
        self,
        goal: StrategicGoal,
        scenarios: List[Scenario]
    ) -> float:
        """Calculate expected value across scenarios."""
        assessments = self.assess_goal_under_scenarios(goal, scenarios)

        ev = sum(
            a["expected_progress"] * a["probability"]
            for a in assessments.values()
        )

        return ev


# =============================================================================
# RESOURCE ALLOCATOR
# =============================================================================

class StrategicResourceAllocator:
    """
    Allocates resources to strategic goals.

    Optimizes resource distribution for maximum impact.
    """

    def __init__(self, available_resources: Dict[str, float] = None):
        self.available = available_resources or {}
        self.allocations: Dict[str, List[ResourceAllocation]] = {}

    def set_available_resources(self, resources: Dict[str, float]) -> None:
        """Set available resources."""
        self.available = resources

    def allocate(
        self,
        goals: List[StrategicGoal],
        strategy: str = "priority_weighted"
    ) -> Dict[str, List[ResourceAllocation]]:
        """Allocate resources to goals."""
        if strategy == "priority_weighted":
            return self._priority_weighted_allocation(goals)
        elif strategy == "equal":
            return self._equal_allocation(goals)
        elif strategy == "progress_based":
            return self._progress_based_allocation(goals)
        else:
            return self._priority_weighted_allocation(goals)

    def _priority_weighted_allocation(
        self,
        goals: List[StrategicGoal]
    ) -> Dict[str, List[ResourceAllocation]]:
        """Allocate based on goal priority."""
        allocations = {}

        # Calculate priority weights
        total_priority = sum(g.priority for g in goals)
        if total_priority == 0:
            return allocations

        for goal in goals:
            weight = goal.priority / total_priority
            goal_allocations = []

            for resource_type, amount in self.available.items():
                allocation = ResourceAllocation(
                    resource_type=resource_type,
                    allocated_amount=amount * weight,
                    priority=self._map_priority(goal.priority)
                )
                goal_allocations.append(allocation)

            allocations[goal.id] = goal_allocations

        return allocations

    def _equal_allocation(
        self,
        goals: List[StrategicGoal]
    ) -> Dict[str, List[ResourceAllocation]]:
        """Allocate equally among goals."""
        allocations = {}

        if not goals:
            return allocations

        weight = 1.0 / len(goals)

        for goal in goals:
            goal_allocations = []

            for resource_type, amount in self.available.items():
                allocation = ResourceAllocation(
                    resource_type=resource_type,
                    allocated_amount=amount * weight,
                    priority=ResourcePriority.MEDIUM
                )
                goal_allocations.append(allocation)

            allocations[goal.id] = goal_allocations

        return allocations

    def _progress_based_allocation(
        self,
        goals: List[StrategicGoal]
    ) -> Dict[str, List[ResourceAllocation]]:
        """Allocate more to goals with less progress."""
        allocations = {}

        # Calculate inverse progress weights (less progress = more resources)
        weights = []
        for goal in goals:
            inverse_progress = 1 - goal.overall_progress
            weights.append(inverse_progress)

        total_weight = sum(weights) or 1

        for goal, weight in zip(goals, weights):
            normalized_weight = weight / total_weight
            goal_allocations = []

            for resource_type, amount in self.available.items():
                allocation = ResourceAllocation(
                    resource_type=resource_type,
                    allocated_amount=amount * normalized_weight,
                    priority=self._map_priority(goal.priority)
                )
                goal_allocations.append(allocation)

            allocations[goal.id] = goal_allocations

        return allocations

    def _map_priority(self, priority_value: int) -> ResourcePriority:
        """Map numeric priority to ResourcePriority enum."""
        if priority_value >= 9:
            return ResourcePriority.CRITICAL
        elif priority_value >= 7:
            return ResourcePriority.HIGH
        elif priority_value >= 4:
            return ResourcePriority.MEDIUM
        elif priority_value >= 2:
            return ResourcePriority.LOW
        else:
            return ResourcePriority.OPPORTUNISTIC


# =============================================================================
# STRATEGIC PLANNER
# =============================================================================

class StrategicPlanner:
    """
    The master strategic planner for BAEL.

    Provides comprehensive strategic planning with
    goal management, strategy formulation, and execution tracking.
    """

    def __init__(self):
        self.vision: Optional[StrategicVision] = None
        self.hierarchy = GoalHierarchy()
        self.analyzer = StrategyAnalyzer()
        self.scenario_planner = ScenarioPlanner()
        self.resource_allocator = StrategicResourceAllocator()
        self.strategies: Dict[str, Strategy] = {}
        self.planning_context: Dict[str, Any] = {}

    def set_vision(
        self,
        statement: str,
        core_values: List[str],
        purpose: str = "",
        aspirations: List[str] = None,
        timeframe_years: int = 5
    ) -> StrategicVision:
        """Set the strategic vision."""
        self.vision = StrategicVision(
            statement=statement,
            core_values=core_values,
            purpose=purpose,
            aspirations=aspirations or [],
            timeframe_years=timeframe_years
        )
        return self.vision

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set planning context."""
        self.planning_context = context
        self.scenario_planner.base_assumptions = context

    async def create_goal(
        self,
        name: str,
        description: str = "",
        horizon: StrategicHorizon = StrategicHorizon.MEDIUM_TERM,
        priority: int = 5,
        parent_id: Optional[str] = None,
        target_date: Optional[datetime] = None
    ) -> StrategicGoal:
        """Create a new strategic goal."""
        goal = StrategicGoal(
            name=name,
            description=description,
            horizon=horizon,
            priority=priority,
            target_date=target_date
        )

        self.hierarchy.add_goal(goal, parent_id)

        return goal

    def add_milestone(
        self,
        goal_id: str,
        name: str,
        description: str = "",
        target_date: Optional[datetime] = None,
        milestone_type: MilestoneType = MilestoneType.DELIVERABLE
    ) -> Optional[Milestone]:
        """Add a milestone to a goal."""
        goal = self.hierarchy.goals.get(goal_id)
        if not goal:
            return None

        milestone = Milestone(
            name=name,
            description=description,
            type=milestone_type,
            target_date=target_date
        )

        goal.milestones.append(milestone)
        return milestone

    def add_metric(
        self,
        goal_id: str,
        name: str,
        target_value: float,
        current_value: float = 0.0,
        unit: str = ""
    ) -> Optional[SuccessMetric]:
        """Add a success metric to a goal."""
        goal = self.hierarchy.goals.get(goal_id)
        if not goal:
            return None

        metric = SuccessMetric(
            name=name,
            target_value=target_value,
            current_value=current_value,
            unit=unit
        )

        goal.metrics.append(metric)
        return metric

    def add_risk(
        self,
        goal_id: str,
        description: str,
        level: RiskLevel = RiskLevel.MODERATE,
        probability: float = 0.5,
        impact: float = 0.5
    ) -> Optional[Risk]:
        """Add a risk to a goal."""
        goal = self.hierarchy.goals.get(goal_id)
        if not goal:
            return None

        risk = Risk(
            description=description,
            level=level,
            probability=probability,
            impact=impact
        )

        goal.risks.append(risk)
        return risk

    async def formulate_strategy(
        self,
        name: str,
        goal_ids: List[str],
        strategy_type: Optional[StrategyType] = None,
        tactics: List[str] = None
    ) -> Strategy:
        """Formulate a strategy for goals."""
        goals = [
            self.hierarchy.goals[gid]
            for gid in goal_ids
            if gid in self.hierarchy.goals
        ]

        # Recommend strategy type if not specified
        if strategy_type is None:
            strategy_type = self.analyzer.recommend_strategy_type(
                goals, self.planning_context
            )

        strategy = Strategy(
            name=name,
            type=strategy_type,
            goal_ids=goal_ids,
            tactics=tactics or []
        )

        # Calculate success probability
        if goals:
            avg_confidence = sum(g.confidence for g in goals) / len(goals)
            avg_risk = sum(g.risk_exposure for g in goals) / len(goals)
            strategy.success_probability = avg_confidence * (1 - avg_risk * 0.5)

        self.strategies[strategy.id] = strategy
        self.analyzer.add_strategy(strategy)

        return strategy

    async def analyze_strategy(
        self,
        strategy_id: str
    ) -> Dict[str, Any]:
        """Analyze a strategy."""
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return {"error": "Strategy not found"}

        goals = [
            self.hierarchy.goals[gid]
            for gid in strategy.goal_ids
            if gid in self.hierarchy.goals
        ]

        swot = self.analyzer.analyze_swot(strategy, self.planning_context)
        scores = self.analyzer.score_strategy(strategy, goals)

        return {
            "strategy": strategy,
            "swot": swot,
            "scores": scores
        }

    async def plan_scenarios(
        self,
        goal_id: str,
        num_scenarios: int = 3
    ) -> Dict[str, Any]:
        """Plan for multiple scenarios."""
        goal = self.hierarchy.goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        scenarios = self.scenario_planner.generate_scenarios(num_scenarios)
        assessments = self.scenario_planner.assess_goal_under_scenarios(goal, scenarios)
        expected_value = self.scenario_planner.expected_value(goal, scenarios)

        return {
            "goal": goal,
            "scenarios": scenarios,
            "assessments": assessments,
            "expected_value": expected_value
        }

    def allocate_resources(
        self,
        available_resources: Dict[str, float],
        strategy: str = "priority_weighted"
    ) -> Dict[str, List[ResourceAllocation]]:
        """Allocate resources to active goals."""
        self.resource_allocator.set_available_resources(available_resources)

        active_goals = self.hierarchy.get_active_goals()
        allocations = self.resource_allocator.allocate(active_goals, strategy)

        # Apply allocations to goals
        for goal_id, goal_allocations in allocations.items():
            goal = self.hierarchy.goals.get(goal_id)
            if goal:
                goal.resources = goal_allocations

        return allocations

    def update_progress(
        self,
        goal_id: str,
        milestone_id: Optional[str] = None,
        metric_id: Optional[str] = None,
        progress: Optional[float] = None,
        value: Optional[float] = None
    ) -> bool:
        """Update progress on a goal."""
        goal = self.hierarchy.goals.get(goal_id)
        if not goal:
            return False

        if milestone_id and progress is not None:
            for milestone in goal.milestones:
                if milestone.id == milestone_id:
                    milestone.progress = min(1.0, max(0.0, progress))
                    if milestone.progress >= 1.0:
                        milestone.completed_date = datetime.now()
                    break

        if metric_id and value is not None:
            for metric in goal.metrics:
                if metric.id == metric_id:
                    metric.current_value = value
                    metric.trend.append(value)
                    break

        # Propagate progress up hierarchy
        self.hierarchy.propagate_progress(goal_id)

        # Update goal state based on progress
        if goal.overall_progress >= 1.0:
            goal.state = GoalState.ACHIEVED
        elif goal.overall_progress > 0:
            goal.state = GoalState.IN_PROGRESS

        return True

    def get_dashboard(self) -> Dict[str, Any]:
        """Get strategic dashboard."""
        all_goals = list(self.hierarchy.goals.values())
        active_goals = self.hierarchy.get_active_goals()
        blocked_goals = self.hierarchy.get_blocked_goals()

        # Progress summary
        if all_goals:
            avg_progress = sum(g.overall_progress for g in all_goals) / len(all_goals)
            avg_risk = sum(g.risk_exposure for g in all_goals) / len(all_goals)
        else:
            avg_progress = 0
            avg_risk = 0

        # Goals by horizon
        by_horizon = {}
        for horizon in StrategicHorizon:
            by_horizon[horizon.value] = len(self.hierarchy.get_by_horizon(horizon))

        return {
            "vision": self.vision.statement if self.vision else None,
            "summary": {
                "total_goals": len(all_goals),
                "active_goals": len(active_goals),
                "blocked_goals": len(blocked_goals),
                "total_strategies": len(self.strategies),
                "avg_progress": avg_progress,
                "avg_risk_exposure": avg_risk
            },
            "by_horizon": by_horizon,
            "top_priorities": sorted(
                active_goals,
                key=lambda g: g.priority,
                reverse=True
            )[:5]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Strategic Planner."""
    print("=" * 70)
    print("BAEL - STRATEGIC PLANNER DEMO")
    print("Long-term Goal Planning")
    print("=" * 70)
    print()

    # Create planner
    planner = StrategicPlanner()

    # 1. Set Vision
    print("1. SETTING VISION:")
    print("-" * 40)

    vision = planner.set_vision(
        statement="Become the most advanced AI agent system ever created",
        core_values=["Excellence", "Innovation", "Efficiency", "Zero-Cost"],
        purpose="Enable superhuman AI capabilities through intelligent orchestration",
        aspirations=[
            "Full AGI-level capabilities",
            "Self-evolving architecture",
            "Infinite scalability"
        ],
        timeframe_years=3
    )

    print(f"   Vision: {vision.statement}")
    print(f"   Core Values: {', '.join(vision.core_values)}")
    print()

    # 2. Set Context
    print("2. SETTING CONTEXT:")
    print("-" * 40)

    planner.set_context({
        "market_growth": 0.25,
        "resource_availability": 0.8,
        "competitive_pressure": 0.3,
        "technology_readiness": 0.7
    })
    print("   Context set with market and resource conditions")
    print()

    # 3. Create Goals
    print("3. CREATING STRATEGIC GOALS:")
    print("-" * 40)

    # Parent goal
    main_goal = await planner.create_goal(
        name="Achieve Full System Deployment",
        description="Complete deployment of all BAEL subsystems",
        horizon=StrategicHorizon.MEDIUM_TERM,
        priority=10
    )
    print(f"   Created: {main_goal.name} (Priority: {main_goal.priority})")

    # Sub-goals
    council_goal = await planner.create_goal(
        name="Complete Council Architecture",
        description="All councils fully operational",
        horizon=StrategicHorizon.SHORT_TERM,
        priority=9,
        parent_id=main_goal.id
    )

    engine_goal = await planner.create_goal(
        name="Deploy Engine Matrix",
        description="All engines integrated and running",
        horizon=StrategicHorizon.SHORT_TERM,
        priority=8,
        parent_id=main_goal.id
    )

    print(f"   Created: {council_goal.name}")
    print(f"   Created: {engine_goal.name}")
    print()

    # 4. Add Milestones and Metrics
    print("4. ADDING MILESTONES AND METRICS:")
    print("-" * 40)

    planner.add_milestone(
        main_goal.id,
        "Alpha Release",
        "First working version",
        target_date=datetime.now() + timedelta(days=30)
    )

    planner.add_milestone(
        main_goal.id,
        "Beta Release",
        "Feature complete version",
        target_date=datetime.now() + timedelta(days=60)
    )

    planner.add_metric(
        main_goal.id,
        "Code Coverage",
        target_value=80,
        current_value=45,
        unit="%"
    )

    planner.add_metric(
        main_goal.id,
        "Components Deployed",
        target_value=50,
        current_value=15,
        unit="count"
    )

    print(f"   Added 2 milestones and 2 metrics to {main_goal.name}")
    print()

    # 5. Add Risks
    print("5. RISK ASSESSMENT:")
    print("-" * 40)

    planner.add_risk(
        main_goal.id,
        "Technical complexity may cause delays",
        level=RiskLevel.MODERATE,
        probability=0.4,
        impact=0.6
    )

    planner.add_risk(
        main_goal.id,
        "Resource constraints on free tiers",
        level=RiskLevel.LOW,
        probability=0.3,
        impact=0.4
    )

    print(f"   Added risks to {main_goal.name}")
    print(f"   Risk Exposure: {main_goal.risk_exposure:.2f}")
    print()

    # 6. Formulate Strategy
    print("6. STRATEGY FORMULATION:")
    print("-" * 40)

    strategy = await planner.formulate_strategy(
        "Rapid Development Strategy",
        [main_goal.id, council_goal.id, engine_goal.id],
        strategy_type=StrategyType.GROWTH,
        tactics=[
            "Parallel development of components",
            "Continuous integration",
            "Daily progress reviews",
            "Modular architecture",
            "Automated testing"
        ]
    )

    print(f"   Strategy: {strategy.name}")
    print(f"   Type: {strategy.type.value}")
    print(f"   Success Probability: {strategy.success_probability:.2%}")
    print()

    # 7. Analyze Strategy
    print("7. STRATEGY ANALYSIS:")
    print("-" * 40)

    analysis = await planner.analyze_strategy(strategy.id)

    print("   SWOT Analysis:")
    for category, items in analysis["swot"].items():
        if items:
            print(f"   {category.upper()}: {', '.join(items[:2])}")

    print(f"\n   Scores:")
    for score_name, value in analysis["scores"].items():
        print(f"   - {score_name}: {value:.2f}")
    print()

    # 8. Scenario Planning
    print("8. SCENARIO PLANNING:")
    print("-" * 40)

    scenario_analysis = await planner.plan_scenarios(main_goal.id)

    print("   Scenario Assessments:")
    for name, assessment in scenario_analysis["assessments"].items():
        print(f"   {name}:")
        print(f"     - Probability: {assessment['probability']:.0%}")
        print(f"     - Expected Progress: {assessment['expected_progress']:.2f}")

    print(f"\n   Expected Value: {scenario_analysis['expected_value']:.2f}")
    print()

    # 9. Resource Allocation
    print("9. RESOURCE ALLOCATION:")
    print("-" * 40)

    allocations = planner.allocate_resources({
        "compute": 100.0,
        "memory": 256.0,
        "bandwidth": 500.0
    }, strategy="priority_weighted")

    for goal_id, allocs in list(allocations.items())[:2]:
        goal = planner.hierarchy.goals[goal_id]
        print(f"   {goal.name}:")
        for alloc in allocs[:2]:
            print(f"     - {alloc.resource_type}: {alloc.allocated_amount:.1f}")
    print()

    # 10. Update Progress
    print("10. PROGRESS UPDATE:")
    print("-" * 40)

    # Update milestone progress
    milestone = main_goal.milestones[0]
    planner.update_progress(main_goal.id, milestone_id=milestone.id, progress=0.6)
    print(f"   Updated '{milestone.name}' progress to 60%")

    # Update metric
    metric = main_goal.metrics[0]
    planner.update_progress(main_goal.id, metric_id=metric.id, value=55)
    print(f"   Updated '{metric.name}' to {metric.current_value}%")
    print()

    # 11. Dashboard
    print("11. STRATEGIC DASHBOARD:")
    print("-" * 40)

    dashboard = planner.get_dashboard()

    print(f"   Vision: {dashboard['vision'][:50]}...")
    print(f"   Total Goals: {dashboard['summary']['total_goals']}")
    print(f"   Active Goals: {dashboard['summary']['active_goals']}")
    print(f"   Strategies: {dashboard['summary']['total_strategies']}")
    print(f"   Avg Progress: {dashboard['summary']['avg_progress']:.1%}")
    print(f"   Avg Risk: {dashboard['summary']['avg_risk_exposure']:.2f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Strategic Planner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
