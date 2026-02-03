"""
Predictive Planning System for BAEL Phase 2

Predicts outcomes and plans optimal strategies with resource optimization
and scenario analysis. Enables proactive decision-making and risk mitigation.

Key Components:
- Outcome prediction and forecasting
- Scenario planning and analysis
- Resource optimization
- Risk assessment and mitigation
- Goal decomposition
- Plan quality evaluation
"""

import json
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class PredictionType(str, Enum):
    """Types of predictions."""
    SUCCESS_PROBABILITY = "success_probability"
    EXECUTION_TIME = "execution_time"
    RESOURCE_USAGE = "resource_usage"
    COST_ESTIMATE = "cost_estimate"
    RISK_LEVEL = "risk_level"
    OUTCOME_QUALITY = "outcome_quality"


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    MINIMAL = "minimal"  # < 5% failure risk
    LOW = "low"  # 5-15% risk
    MODERATE = "moderate"  # 15-40% risk
    HIGH = "high"  # 40-70% risk
    CRITICAL = "critical"  # > 70% risk


class PlanQuality(str, Enum):
    """Plan quality assessment."""
    EXCELLENT = "excellent"  # Optimal solution
    GOOD = "good"  # Near-optimal
    ACCEPTABLE = "acceptable"  # Workable
    POOR = "poor"  # Suboptimal
    UNUSABLE = "unusable"  # Not feasible


@dataclass
class Prediction:
    """Single prediction about outcome."""
    prediction_type: PredictionType
    predicted_value: float
    confidence: float  # 0.0 to 1.0
    basis: str  # How this prediction was made
    lower_bound: float = 0.0
    upper_bound: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prediction_type": self.prediction_type.value,
            "predicted_value": self.predicted_value,
            "confidence": self.confidence,
            "basis": self.basis,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Scenario:
    """Hypothetical scenario for planning."""
    scenario_id: str
    name: str
    description: str
    assumptions: List[str]
    conditions: Dict[str, Any]
    probability: float  # 0.0 to 1.0
    predictions: Dict[str, Prediction] = field(default_factory=dict)
    resource_requirements: Dict[str, float] = field(default_factory=dict)
    outcome_estimate: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "assumptions": self.assumptions,
            "conditions": self.conditions,
            "probability": self.probability,
            "predictions": {k: v.to_dict() for k, v in self.predictions.items()},
            "resource_requirements": self.resource_requirements,
            "outcome_estimate": self.outcome_estimate,
        }


@dataclass
class Plan:
    """Action plan with predictions and risk mitigation."""
    plan_id: str
    goal: str
    description: str
    steps: List[Dict[str, Any]]
    resource_budget: Dict[str, float]
    time_estimate: float  # hours
    success_probability: float  # 0.0 to 1.0
    risk_level: RiskLevel
    mitigation_strategies: Dict[str, str] = field(default_factory=dict)
    contingency_plans: List[str] = field(default_factory=list)
    quality: PlanQuality = PlanQuality.ACCEPTABLE
    confidence: float = 0.75
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "description": self.description,
            "steps": self.steps,
            "resource_budget": self.resource_budget,
            "time_estimate": self.time_estimate,
            "success_probability": self.success_probability,
            "risk_level": self.risk_level.value,
            "mitigation_strategies": self.mitigation_strategies,
            "contingency_plans": self.contingency_plans,
            "quality": self.quality.value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


class PredictionModel:
    """Makes predictions based on historical data."""

    def __init__(self):
        """Initialize prediction model."""
        self.historical_data: List[Dict[str, Any]] = []
        self.models: Dict[PredictionType, Callable] = {}

    def add_data_point(self, data: Dict[str, Any]) -> None:
        """Add historical data point."""
        self.historical_data.append(data)

    def predict_success_probability(
        self,
        action_description: str,
        context: Dict[str, Any],
    ) -> Prediction:
        """Predict probability of success."""
        # Look for similar past actions
        similar = [
            d for d in self.historical_data
            if action_description.lower() in str(d).lower()
        ]

        if similar:
            success_count = sum(1 for d in similar if d.get("success"))
            probability = success_count / len(similar)
        else:
            probability = 0.6  # Default estimate

        return Prediction(
            prediction_type=PredictionType.SUCCESS_PROBABILITY,
            predicted_value=probability,
            confidence=0.7 if similar else 0.3,
            basis="Historical analysis" if similar else "Default estimate",
            lower_bound=max(0.0, probability - 0.2),
            upper_bound=min(1.0, probability + 0.2),
        )

    def predict_execution_time(
        self,
        action_description: str,
        complexity: float,
    ) -> Prediction:
        """Predict execution time (hours)."""
        # Base estimates
        base_times = {
            "simple": 0.5,
            "moderate": 2.0,
            "complex": 8.0,
            "very_complex": 24.0,
        }

        complexity_level = "simple" if complexity < 0.25 else (
            "moderate" if complexity < 0.5 else (
                "complex" if complexity < 0.75 else "very_complex"
            )
        )

        estimated_time = base_times[complexity_level]

        return Prediction(
            prediction_type=PredictionType.EXECUTION_TIME,
            predicted_value=estimated_time,
            confidence=0.6,
            basis=f"Complexity-based estimate ({complexity_level})",
            lower_bound=estimated_time * 0.5,
            upper_bound=estimated_time * 2.0,
        )

    def predict_resource_usage(
        self,
        action_type: str,
        scale: float,
    ) -> Prediction:
        """Predict resource usage (0-1 scale)."""
        # Simple scaling model
        base_usage = 0.4
        predicted = base_usage + (scale * 0.5)
        predicted = min(1.0, predicted)

        return Prediction(
            prediction_type=PredictionType.RESOURCE_USAGE,
            predicted_value=predicted,
            confidence=0.6,
            basis="Scale-based resource model",
            lower_bound=predicted * 0.7,
            upper_bound=predicted * 1.3,
        )

    def predict_cost(
        self,
        resources_needed: Dict[str, float],
        unit_costs: Dict[str, float],
    ) -> Prediction:
        """Predict total cost."""
        total_cost = sum(
            resources_needed.get(resource, 0) * unit_costs.get(resource, 1.0)
            for resource in unit_costs
        )

        return Prediction(
            prediction_type=PredictionType.COST_ESTIMATE,
            predicted_value=total_cost,
            confidence=0.75,
            basis="Resource-based cost calculation",
            lower_bound=total_cost * 0.8,
            upper_bound=total_cost * 1.2,
        )


class RiskAssessor:
    """Assesses risks in plans."""

    def __init__(self):
        """Initialize risk assessor."""
        self.risk_factors: Dict[str, float] = {}

    def assess_plan_risk(self, plan: Plan) -> RiskLevel:
        """Assess overall risk of plan."""
        # Base risk on success probability
        if plan.success_probability >= 0.95:
            return RiskLevel.MINIMAL
        elif plan.success_probability >= 0.85:
            return RiskLevel.LOW
        elif plan.success_probability >= 0.60:
            return RiskLevel.MODERATE
        elif plan.success_probability >= 0.30:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def identify_risks(self, plan: Plan) -> List[Tuple[str, RiskLevel, str]]:
        """Identify specific risks in plan."""
        risks = []

        # Check for resource constraints
        for resource, budget in plan.resource_budget.items():
            if budget > 100:  # High resource requirement
                risks.append((
                    f"High {resource} requirement",
                    RiskLevel.MODERATE,
                    f"Plan requires {budget} units of {resource}",
                ))

        # Check for tight timeline
        if plan.time_estimate < 1.0:  # Less than 1 hour
            risks.append((
                "Very tight timeline",
                RiskLevel.HIGH,
                f"Only {plan.time_estimate} hours allocated",
            ))

        # Check for low success probability
        if plan.success_probability < 0.7:
            risks.append((
                "Low success probability",
                RiskLevel.HIGH,
                f"Only {plan.success_probability:.0%} chance of success",
            ))

        return risks

    def suggest_mitigations(self, risks: List[Tuple[str, RiskLevel, str]]) -> Dict[str, str]:
        """Suggest mitigation strategies for risks."""
        mitigations = {}

        for risk_name, risk_level, description in risks:
            if "resource" in risk_name.lower():
                mitigations[risk_name] = "Consider parallel execution or resource pooling"
            elif "timeline" in risk_name.lower():
                mitigations[risk_name] = "Break task into smaller chunks or add buffer time"
            elif "probability" in risk_name.lower():
                mitigations[risk_name] = "Add validation steps and error recovery"
            else:
                mitigations[risk_name] = "Monitor progress closely and prepare contingencies"

        return mitigations


class GoalDecomposer:
    """Decomposes goals into actionable steps."""

    def decompose(self, goal: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Decompose goal into steps.

        Args:
            goal: High-level goal
            max_depth: Maximum decomposition depth

        Returns:
            List of action steps
        """
        steps = []

        # Simple decomposition (in practice, would use more sophisticated analysis)
        substeps = self._decompose_goal(goal, 0, max_depth)

        for i, substep in enumerate(substeps):
            steps.append({
                "order": i + 1,
                "description": substep,
                "estimated_effort": self._estimate_effort(substep),
                "dependencies": [],
            })

        return steps

    def _decompose_goal(self, goal: str, depth: int, max_depth: int) -> List[str]:
        """Recursively decompose goal."""
        if depth >= max_depth:
            return [goal]

        # Generic decomposition
        decompositions = {
            "analyze": ["gather information", "process data", "draw conclusions"],
            "create": ["plan design", "implement", "test and validate"],
            "optimize": ["measure baseline", "identify improvements", "apply and verify"],
            "integrate": ["understand requirements", "implement", "test integration"],
        }

        # Find matching decomposition
        for key, steps in decompositions.items():
            if key in goal.lower():
                return steps

        # Default decomposition
        return ["prepare", "execute", "validate"]

    def _estimate_effort(self, step: str) -> str:
        """Estimate effort for step."""
        if any(word in step.lower() for word in ["complex", "large", "comprehensive"]):
            return "high"
        elif any(word in step.lower() for word in ["simple", "small", "basic"]):
            return "low"
        else:
            return "medium"


class ScenarioPlanner:
    """Plans and analyzes scenarios."""

    def __init__(self, prediction_model: PredictionModel):
        """Initialize planner."""
        self.prediction_model = prediction_model
        self.scenarios: Dict[str, Scenario] = {}

    def create_scenarios(self, goal: str, num_scenarios: int = 3) -> List[Scenario]:
        """Create scenarios for goal."""
        scenarios = []

        scenario_types = [
            ("best_case", "Optimistic scenario where everything goes well", 0.3),
            ("nominal_case", "Expected scenario with normal challenges", 0.5),
            ("worst_case", "Pessimistic scenario with significant obstacles", 0.2),
        ]

        for i in range(min(num_scenarios, len(scenario_types))):
            name, description, probability = scenario_types[i]
            scenario = Scenario(
                scenario_id=f"scenario_{i}",
                name=name,
                description=description,
                assumptions=[f"Assumption for {name}"],
                conditions={"scenario_type": name},
                probability=probability,
            )

            # Add predictions for scenario
            scenario.predictions[PredictionType.SUCCESS_PROBABILITY.value] = (
                Prediction(
                    prediction_type=PredictionType.SUCCESS_PROBABILITY,
                    predicted_value=0.9 if i == 0 else (0.7 if i == 1 else 0.3),
                    confidence=0.8,
                    basis=f"{name} assessment",
                )
            )

            scenarios.append(scenario)
            self.scenarios[scenario.scenario_id] = scenario

        return scenarios

    def analyze_scenarios(
        self,
        scenarios: List[Scenario],
    ) -> Dict[str, Any]:
        """Analyze scenarios to recommend best approach."""
        analysis = {
            "scenarios": [s.to_dict() for s in scenarios],
            "expected_value": self._calculate_expected_value(scenarios),
            "variance": self._calculate_variance(scenarios),
            "recommended_scenario": max(
                scenarios,
                key=lambda s: s.probability,
            ).scenario_id if scenarios else None,
            "key_uncertainties": self._identify_uncertainties(scenarios),
        }

        return analysis

    def _calculate_expected_value(self, scenarios: List[Scenario]) -> float:
        """Calculate expected value across scenarios."""
        total = 0.0
        for scenario in scenarios:
            success_pred = scenario.predictions.get(
                PredictionType.SUCCESS_PROBABILITY.value
            )
            if success_pred:
                total += scenario.probability * success_pred.predicted_value

        return total

    def _calculate_variance(self, scenarios: List[Scenario]) -> float:
        """Calculate outcome variance."""
        if not scenarios:
            return 0.0

        values = [
            s.predictions.get(PredictionType.SUCCESS_PROBABILITY.value).predicted_value
            for s in scenarios
            if s.predictions.get(PredictionType.SUCCESS_PROBABILITY.value)
        ]

        if not values:
            return 0.0

        mean = statistics.mean(values)
        return statistics.variance(values) if len(values) > 1 else 0.0

    def _identify_uncertainties(self, scenarios: List[Scenario]) -> List[str]:
        """Identify key uncertainties."""
        uncertainties = []

        # Check for high variance
        if self._calculate_variance(scenarios) > 0.1:
            uncertainties.append("High outcome variance across scenarios")

        # Check for low confidence
        for scenario in scenarios:
            for pred in scenario.predictions.values():
                if pred.confidence < 0.6:
                    uncertainties.append(f"Low confidence in {pred.prediction_type.value}")

        return uncertainties


class PlanningEngine:
    """Main planning and prediction engine."""

    def __init__(self):
        """Initialize planning engine."""
        self.prediction_model = PredictionModel()
        self.risk_assessor = RiskAssessor()
        self.decomposer = GoalDecomposer()
        self.scenario_planner = ScenarioPlanner(self.prediction_model)
        self.plans: Dict[str, Plan] = {}

    def create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        resource_budget: Optional[Dict[str, float]] = None,
        create_scenarios: bool = True,
    ) -> Plan:
        """
        Create comprehensive plan for goal.

        Args:
            goal: Goal to plan for
            context: Contextual information
            resource_budget: Available resources
            create_scenarios: Whether to create scenarios

        Returns:
            Detailed plan
        """
        context = context or {}
        resource_budget = resource_budget or {"compute": 100.0, "memory": 100.0}

        # Decompose goal
        steps = self.decomposer.decompose(goal)

        # Make predictions
        success_prob = self.prediction_model.predict_success_probability(
            goal,
            context,
        )

        # Estimate time
        complexity = context.get("complexity", 0.5)
        time_pred = self.prediction_model.predict_execution_time(goal, complexity)

        # Create plan
        plan_id = f"plan_{len(self.plans)}_{datetime.now().timestamp()}"
        plan = Plan(
            plan_id=plan_id,
            goal=goal,
            description=f"Plan for: {goal}",
            steps=steps,
            resource_budget=resource_budget,
            time_estimate=time_pred.predicted_value,
            success_probability=success_prob.predicted_value,
            risk_level=self.risk_assessor.assess_plan_risk(
                Plan(
                    plan_id="temp",
                    goal=goal,
                    description="",
                    steps=[],
                    resource_budget=resource_budget,
                    time_estimate=time_pred.predicted_value,
                    success_probability=success_prob.predicted_value,
                    risk_level=RiskLevel.MODERATE,
                )
            ),
            confidence=success_prob.confidence,
        )

        # Assess risks
        risks = self.risk_assessor.identify_risks(plan)
        plan.mitigation_strategies = self.risk_assessor.suggest_mitigations(risks)

        # Create scenarios
        if create_scenarios:
            scenarios = self.scenario_planner.create_scenarios(goal)
            analysis = self.scenario_planner.analyze_scenarios(scenarios)
            plan.metadata["scenario_analysis"] = analysis

        # Assess quality
        plan.quality = self._assess_plan_quality(plan)

        # Store plan
        self.plans[plan_id] = plan
        return plan

    def _assess_plan_quality(self, plan: Plan) -> PlanQuality:
        """Assess overall plan quality."""
        if plan.success_probability >= 0.9 and plan.risk_level == RiskLevel.MINIMAL:
            return PlanQuality.EXCELLENT
        elif plan.success_probability >= 0.75:
            return PlanQuality.GOOD
        elif plan.success_probability >= 0.50:
            return PlanQuality.ACCEPTABLE
        elif plan.success_probability >= 0.25:
            return PlanQuality.POOR
        else:
            return PlanQuality.UNUSABLE

    def compare_plans(self, plan_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple plans."""
        plans = [self.plans[pid] for pid in plan_ids if pid in self.plans]

        if not plans:
            return {}

        comparison = {
            "plans": [p.to_dict() for p in plans],
            "best_success_rate": max(p.success_probability for p in plans),
            "lowest_risk": min(p.risk_level.value for p in plans),
            "recommendation": max(
                plans,
                key=lambda p: (p.quality.value, p.success_probability),
            ).plan_id,
        }

        return comparison

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get plan by ID."""
        return self.plans.get(plan_id)


# Global planning engine
_planning_engine = None


def get_planning_engine() -> PlanningEngine:
    """Get or create global planning engine."""
    global _planning_engine
    if _planning_engine is None:
        _planning_engine = PlanningEngine()
    return _planning_engine
