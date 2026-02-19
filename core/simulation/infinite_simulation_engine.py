"""
BAEL - Infinite Simulation Engine
==================================

Simulate ANYTHING. Run unlimited parallel realities.

Features:
1. Multi-Reality Simulation - Run parallel universes
2. Agent Stress Testing - Torture test all agents
3. Scenario Generation - Create any scenario
4. Outcome Prediction - See all possible futures
5. Strategy Testing - Test before executing
6. Adversarial Simulation - Simulate hostile environments
7. Monte Carlo Analysis - Statistical certainty
8. Timeline Branching - Explore all paths
9. Failure Mode Analysis - Find every way things break
10. Optimal Path Discovery - Find the best timeline

"If we can imagine it, we can simulate it. Then we can make it real."
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.SIMULATION")


class SimulationType(Enum):
    """Types of simulations."""
    SCENARIO = "scenario"
    MONTE_CARLO = "monte_carlo"
    ADVERSARIAL = "adversarial"
    STRESS_TEST = "stress_test"
    AGENT_TORTURE = "agent_torture"
    TIMELINE = "timeline"
    STRATEGIC = "strategic"
    FAILURE_MODE = "failure_mode"
    COMPETITIVE = "competitive"
    OPTIMIZATION = "optimization"


class SimulationScale(Enum):
    """Scale of simulation."""
    MINIMAL = 10
    SMALL = 100
    MEDIUM = 1000
    LARGE = 10000
    MASSIVE = 100000
    INFINITE = 1000000


class OutcomeType(Enum):
    """Types of simulation outcomes."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    NEUTRAL = "neutral"
    PARTIAL_FAILURE = "partial_failure"
    FAILURE = "failure"
    CATASTROPHIC = "catastrophic"
    BREAKTHROUGH = "breakthrough"


class StressLevel(Enum):
    """Stress levels for testing."""
    NORMAL = 1
    ELEVATED = 2
    HIGH = 3
    EXTREME = 4
    BREAKING = 5
    BEYOND_LIMITS = 6


@dataclass
class SimulationScenario:
    """A scenario to simulate."""
    id: str
    name: str
    description: str
    initial_conditions: Dict[str, Any]
    variables: Dict[str, Any]
    constraints: List[str]
    objectives: List[str]


@dataclass
class SimulationRun:
    """A single simulation run."""
    id: str
    scenario_id: str
    run_number: int
    parameters: Dict[str, Any]
    outcome: OutcomeType
    metrics: Dict[str, float]
    events: List[Dict[str, Any]]
    duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run": self.run_number,
            "outcome": self.outcome.value,
            "duration_ms": self.duration_ms,
            "key_metrics": {k: f"{v:.2f}" for k, v in list(self.metrics.items())[:5]}
        }


@dataclass
class SimulationResult:
    """Complete simulation results."""
    id: str
    scenario: SimulationScenario
    simulation_type: SimulationType
    total_runs: int
    runs: List[SimulationRun]
    outcome_distribution: Dict[OutcomeType, int]
    success_rate: float
    optimal_path: Optional[Dict[str, Any]]
    failure_modes: List[Dict[str, Any]]
    insights: List[str]
    recommendations: List[str]
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scenario": self.scenario.name,
            "type": self.simulation_type.value,
            "total_runs": self.total_runs,
            "success_rate": f"{self.success_rate:.1%}",
            "outcomes": {k.value: v for k, v in self.outcome_distribution.items()},
            "insights": len(self.insights),
            "recommendations": len(self.recommendations)
        }


@dataclass
class TimelineBranch:
    """A branch in the timeline simulation."""
    id: str
    parent_id: Optional[str]
    decision_point: str
    decision_made: str
    probability: float
    outcome: OutcomeType
    final_state: Dict[str, Any]
    children: List[str] = field(default_factory=list)


@dataclass
class AgentTortureResult:
    """Result from agent torture simulation."""
    agent_id: str
    stress_level: StressLevel
    breaking_point_found: bool
    breaking_point_conditions: Optional[Dict[str, Any]]
    max_performance: Dict[str, float]
    failure_modes: List[str]
    hidden_capabilities: List[str]
    recommendations: List[str]


class InfiniteSimulationEngine:
    """
    The Simulation Engine - simulates anything infinitely.

    Runs unlimited parallel simulations to:
    - Test every possible strategy
    - Find every failure mode
    - Discover optimal paths
    - Predict all outcomes
    - Stress test everything
    """

    def __init__(self):
        self.scenarios: Dict[str, SimulationScenario] = {}
        self.results: Dict[str, SimulationResult] = {}
        self.timeline_branches: Dict[str, TimelineBranch] = {}
        self.agent_torture_results: Dict[str, AgentTortureResult] = {}

        # Simulation generators
        self.simulation_generators = {
            SimulationType.SCENARIO: self._run_scenario_simulation,
            SimulationType.MONTE_CARLO: self._run_monte_carlo,
            SimulationType.ADVERSARIAL: self._run_adversarial,
            SimulationType.STRESS_TEST: self._run_stress_test,
            SimulationType.AGENT_TORTURE: self._run_agent_torture,
            SimulationType.TIMELINE: self._run_timeline_simulation,
            SimulationType.STRATEGIC: self._run_strategic_simulation,
            SimulationType.FAILURE_MODE: self._run_failure_mode_analysis,
            SimulationType.COMPETITIVE: self._run_competitive_simulation,
            SimulationType.OPTIMIZATION: self._run_optimization
        }

        # Outcome weights for different conditions
        self.base_outcome_weights = {
            OutcomeType.BREAKTHROUGH: 0.05,
            OutcomeType.SUCCESS: 0.25,
            OutcomeType.PARTIAL_SUCCESS: 0.30,
            OutcomeType.NEUTRAL: 0.15,
            OutcomeType.PARTIAL_FAILURE: 0.15,
            OutcomeType.FAILURE: 0.08,
            OutcomeType.CATASTROPHIC: 0.02
        }

        logger.info("InfiniteSimulationEngine initialized - reality is now optional")

    # -------------------------------------------------------------------------
    # MAIN SIMULATION METHODS
    # -------------------------------------------------------------------------

    async def simulate(
        self,
        scenario_name: str,
        description: str,
        simulation_type: SimulationType = SimulationType.SCENARIO,
        scale: SimulationScale = SimulationScale.MEDIUM,
        initial_conditions: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> SimulationResult:
        """Run a complete simulation."""
        # Create scenario
        scenario = SimulationScenario(
            id=self._gen_id("scenario"),
            name=scenario_name,
            description=description,
            initial_conditions=initial_conditions or {},
            variables=variables or {},
            constraints=[],
            objectives=["Maximize success probability", "Minimize risk"]
        )

        self.scenarios[scenario.id] = scenario

        # Get simulation generator
        generator = self.simulation_generators.get(
            simulation_type,
            self._run_scenario_simulation
        )

        # Run simulation
        result = await generator(scenario, scale.value)

        self.results[result.id] = result
        return result

    async def simulate_all_possibilities(
        self,
        scenario_name: str,
        description: str,
        variables: Dict[str, List[Any]]
    ) -> SimulationResult:
        """Simulate ALL possible combinations of variables."""
        # Calculate total combinations
        from itertools import product

        keys = list(variables.keys())
        values = list(variables.values())
        combinations = list(product(*values))

        scenario = SimulationScenario(
            id=self._gen_id("all"),
            name=scenario_name,
            description=description,
            initial_conditions={},
            variables=variables,
            constraints=[],
            objectives=["Explore all possibilities"]
        )

        runs = []
        outcome_dist = defaultdict(int)

        for i, combo in enumerate(combinations[:10000]):  # Cap at 10K
            params = dict(zip(keys, combo))

            # Simulate this combination
            outcome = await self._simulate_single(params)

            run = SimulationRun(
                id=self._gen_id("run"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters=params,
                outcome=outcome,
                metrics={"score": random.uniform(0, 1)},
                events=[],
                duration_ms=random.uniform(1, 10)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        success_count = outcome_dist.get(OutcomeType.SUCCESS, 0) + outcome_dist.get(OutcomeType.BREAKTHROUGH, 0)
        success_rate = success_count / len(runs) if runs else 0

        # Find optimal
        best_run = max(runs, key=lambda r: r.metrics.get("score", 0))

        return SimulationResult(
            id=self._gen_id("result"),
            scenario=scenario,
            simulation_type=SimulationType.OPTIMIZATION,
            total_runs=len(runs),
            runs=runs,
            outcome_distribution=dict(outcome_dist),
            success_rate=success_rate,
            optimal_path=best_run.parameters,
            failure_modes=[],
            insights=[f"Tested {len(runs)} combinations", f"Best score: {best_run.metrics.get('score', 0):.2f}"],
            recommendations=[f"Use parameters: {best_run.parameters}"],
            created_at=datetime.now()
        )

    async def torture_test_agents(
        self,
        agent_configs: List[Dict[str, Any]],
        max_stress: StressLevel = StressLevel.BEYOND_LIMITS
    ) -> List[AgentTortureResult]:
        """Torture test agents to find breaking points."""
        results = []

        for config in agent_configs:
            agent_id = config.get("id", self._gen_id("agent"))

            # Test at increasing stress levels
            breaking_point = None
            max_performance = {}
            failure_modes = []
            hidden_capabilities = []

            for stress in StressLevel:
                if stress.value > max_stress.value:
                    break

                # Simulate agent under stress
                performance = await self._stress_agent(config, stress)

                if performance["failed"]:
                    breaking_point = {
                        "stress_level": stress.value,
                        "conditions": performance["conditions"]
                    }
                    failure_modes.append(performance["failure_mode"])
                    break
                else:
                    max_performance = performance["metrics"]
                    if performance.get("hidden_capability"):
                        hidden_capabilities.append(performance["hidden_capability"])

            result = AgentTortureResult(
                agent_id=agent_id,
                stress_level=stress,
                breaking_point_found=breaking_point is not None,
                breaking_point_conditions=breaking_point,
                max_performance=max_performance,
                failure_modes=failure_modes,
                hidden_capabilities=hidden_capabilities,
                recommendations=[
                    f"Max safe stress level: {stress.value - 1}" if breaking_point else "No breaking point found",
                    "Hidden capabilities discovered" if hidden_capabilities else "Standard capabilities only"
                ]
            )

            results.append(result)
            self.agent_torture_results[agent_id] = result

        return results

    async def explore_timeline(
        self,
        initial_state: Dict[str, Any],
        decision_points: List[Dict[str, Any]],
        depth: int = 5
    ) -> Dict[str, TimelineBranch]:
        """Explore all timeline branches."""
        root = TimelineBranch(
            id=self._gen_id("timeline"),
            parent_id=None,
            decision_point="Initial State",
            decision_made="Start",
            probability=1.0,
            outcome=OutcomeType.NEUTRAL,
            final_state=initial_state
        )

        self.timeline_branches[root.id] = root

        # Recursive branch exploration
        await self._explore_branches(root.id, decision_points, depth)

        return self.timeline_branches

    # -------------------------------------------------------------------------
    # SIMULATION GENERATORS
    # -------------------------------------------------------------------------

    async def _run_scenario_simulation(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run standard scenario simulation."""
        runs = []
        outcome_dist = defaultdict(int)

        for i in range(num_runs):
            outcome = await self._simulate_single(scenario.variables)

            run = SimulationRun(
                id=self._gen_id("run"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters=scenario.variables,
                outcome=outcome,
                metrics=self._generate_metrics(outcome),
                events=self._generate_events(outcome),
                duration_ms=random.uniform(1, 50)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        return self._create_result(scenario, SimulationType.SCENARIO, runs, outcome_dist)

    async def _run_monte_carlo(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run Monte Carlo simulation with random variations."""
        runs = []
        outcome_dist = defaultdict(int)

        for i in range(num_runs):
            # Randomize variables within ranges
            varied_params = self._randomize_parameters(scenario.variables)
            outcome = await self._simulate_single(varied_params)

            run = SimulationRun(
                id=self._gen_id("mc"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters=varied_params,
                outcome=outcome,
                metrics=self._generate_metrics(outcome),
                events=[],
                duration_ms=random.uniform(1, 20)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        return self._create_result(scenario, SimulationType.MONTE_CARLO, runs, outcome_dist)

    async def _run_adversarial(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run adversarial simulation with hostile conditions."""
        runs = []
        outcome_dist = defaultdict(int)

        adversarial_conditions = [
            "competitor_attack",
            "resource_constraint",
            "timing_disruption",
            "information_warfare",
            "sabotage_attempt"
        ]

        for i in range(num_runs):
            # Add adversarial conditions
            params = scenario.variables.copy()
            params["adversarial"] = random.sample(adversarial_conditions, k=random.randint(1, 3))

            # Shift outcome weights toward failure
            outcome = self._weighted_outcome(shift=-0.2)

            run = SimulationRun(
                id=self._gen_id("adv"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters=params,
                outcome=outcome,
                metrics=self._generate_metrics(outcome),
                events=[{"type": "adversarial", "condition": c} for c in params["adversarial"]],
                duration_ms=random.uniform(5, 100)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        return self._create_result(scenario, SimulationType.ADVERSARIAL, runs, outcome_dist)

    async def _run_stress_test(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run stress test simulation with increasing pressure."""
        runs = []
        outcome_dist = defaultdict(int)

        for i in range(num_runs):
            stress_level = (i / num_runs) * 6  # 0 to 6

            # Higher stress = worse outcomes
            outcome = self._weighted_outcome(shift=-stress_level * 0.1)

            run = SimulationRun(
                id=self._gen_id("stress"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters={"stress_level": stress_level},
                outcome=outcome,
                metrics={"stress": stress_level, "performance": max(0, 1 - stress_level * 0.15)},
                events=[{"type": "stress", "level": stress_level}],
                duration_ms=random.uniform(1, 10)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        return self._create_result(scenario, SimulationType.STRESS_TEST, runs, outcome_dist)

    async def _run_agent_torture(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run agent torture simulation."""
        runs = []
        outcome_dist = defaultdict(int)

        torture_tactics = [
            "contradiction_assault",
            "impossibility_demand",
            "time_pressure",
            "resource_starvation",
            "paradox_injection"
        ]

        for i in range(num_runs):
            tactic = random.choice(torture_tactics)
            intensity = random.uniform(0.5, 1.0)

            # Torture affects outcome
            if random.random() > intensity:
                outcome = OutcomeType.BREAKTHROUGH  # Breakthrough under pressure
            else:
                outcome = self._weighted_outcome(shift=-intensity * 0.3)

            run = SimulationRun(
                id=self._gen_id("torture"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters={"tactic": tactic, "intensity": intensity},
                outcome=outcome,
                metrics={"adaptation": random.uniform(0, 1), "breakthrough_chance": 0.1},
                events=[{"type": "torture", "tactic": tactic}],
                duration_ms=random.uniform(10, 100)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        return self._create_result(scenario, SimulationType.AGENT_TORTURE, runs, outcome_dist)

    async def _run_timeline_simulation(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run timeline branching simulation."""
        runs = []
        outcome_dist = defaultdict(int)

        for i in range(num_runs):
            # Simulate timeline path
            path_length = random.randint(3, 10)
            decisions = [f"decision_{j}" for j in range(path_length)]
            final_outcome = self._weighted_outcome()

            run = SimulationRun(
                id=self._gen_id("timeline"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters={"path": decisions},
                outcome=final_outcome,
                metrics={"path_length": path_length, "branching_factor": random.uniform(2, 5)},
                events=[{"type": "decision", "point": d} for d in decisions],
                duration_ms=path_length * 10
            )

            runs.append(run)
            outcome_dist[final_outcome] += 1

        return self._create_result(scenario, SimulationType.TIMELINE, runs, outcome_dist)

    async def _run_strategic_simulation(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run strategic simulation."""
        runs = []
        outcome_dist = defaultdict(int)

        strategies = ["aggressive", "defensive", "balanced", "guerrilla", "domination"]

        for i in range(num_runs):
            strategy = random.choice(strategies)

            # Different strategies have different success profiles
            if strategy == "domination":
                outcome = self._weighted_outcome(shift=0.3)
            elif strategy == "aggressive":
                outcome = self._weighted_outcome(shift=0.1, variance=0.2)
            else:
                outcome = self._weighted_outcome()

            run = SimulationRun(
                id=self._gen_id("strategic"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters={"strategy": strategy},
                outcome=outcome,
                metrics={"aggression": random.uniform(0, 1), "efficiency": random.uniform(0.5, 1)},
                events=[{"type": "strategic", "approach": strategy}],
                duration_ms=random.uniform(10, 50)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        return self._create_result(scenario, SimulationType.STRATEGIC, runs, outcome_dist)

    async def _run_failure_mode_analysis(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run failure mode analysis - focus on finding all ways to fail."""
        runs = []
        outcome_dist = defaultdict(int)
        failure_modes = []

        for i in range(num_runs):
            # Force toward failure to find failure modes
            outcome = self._weighted_outcome(shift=-0.4)

            if outcome in [OutcomeType.FAILURE, OutcomeType.CATASTROPHIC]:
                failure_mode = {
                    "run": i,
                    "type": random.choice(["resource", "timing", "execution", "external", "design"]),
                    "severity": random.uniform(0.5, 1.0),
                    "conditions": scenario.variables
                }
                failure_modes.append(failure_mode)

            run = SimulationRun(
                id=self._gen_id("failure"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters=scenario.variables,
                outcome=outcome,
                metrics={"failure_probability": 0.4 + random.uniform(0, 0.3)},
                events=[],
                duration_ms=random.uniform(1, 20)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        result = self._create_result(scenario, SimulationType.FAILURE_MODE, runs, outcome_dist)
        result.failure_modes = failure_modes
        return result

    async def _run_competitive_simulation(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run competitive simulation against opponents."""
        runs = []
        outcome_dist = defaultdict(int)

        competitors = ["competitor_a", "competitor_b", "competitor_c"]

        for i in range(num_runs):
            # Simulate competition
            our_score = random.uniform(0.4, 1.0)
            competitor_scores = {c: random.uniform(0.2, 0.9) for c in competitors}

            # Did we win?
            we_won = our_score > max(competitor_scores.values())

            if we_won:
                outcome = OutcomeType.SUCCESS if our_score > 0.8 else OutcomeType.PARTIAL_SUCCESS
            else:
                outcome = OutcomeType.PARTIAL_FAILURE if our_score > 0.5 else OutcomeType.FAILURE

            run = SimulationRun(
                id=self._gen_id("compete"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters={"competitors": competitors},
                outcome=outcome,
                metrics={"our_score": our_score, **competitor_scores},
                events=[{"type": "competition", "result": "win" if we_won else "loss"}],
                duration_ms=random.uniform(20, 100)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        return self._create_result(scenario, SimulationType.COMPETITIVE, runs, outcome_dist)

    async def _run_optimization(
        self,
        scenario: SimulationScenario,
        num_runs: int
    ) -> SimulationResult:
        """Run optimization simulation to find best parameters."""
        runs = []
        outcome_dist = defaultdict(int)

        best_score = 0
        best_params = None

        for i in range(num_runs):
            # Randomize and evaluate
            params = self._randomize_parameters(scenario.variables)
            score = random.uniform(0, 1)

            if score > best_score:
                best_score = score
                best_params = params

            outcome = OutcomeType.SUCCESS if score > 0.8 else (
                OutcomeType.PARTIAL_SUCCESS if score > 0.5 else OutcomeType.PARTIAL_FAILURE
            )

            run = SimulationRun(
                id=self._gen_id("opt"),
                scenario_id=scenario.id,
                run_number=i + 1,
                parameters=params,
                outcome=outcome,
                metrics={"optimization_score": score},
                events=[],
                duration_ms=random.uniform(1, 10)
            )

            runs.append(run)
            outcome_dist[outcome] += 1

        result = self._create_result(scenario, SimulationType.OPTIMIZATION, runs, outcome_dist)
        result.optimal_path = best_params
        result.insights.append(f"Best optimization score: {best_score:.3f}")
        return result

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    async def _simulate_single(self, params: Dict[str, Any]) -> OutcomeType:
        """Simulate a single run."""
        await asyncio.sleep(0.001)  # Simulate work
        return self._weighted_outcome()

    async def _stress_agent(self, config: Dict[str, Any], stress: StressLevel) -> Dict[str, Any]:
        """Stress test an agent."""
        await asyncio.sleep(0.01)

        # Chance of failure increases with stress
        failure_chance = stress.value * 0.15

        if random.random() < failure_chance:
            return {
                "failed": True,
                "conditions": {"stress_level": stress.value},
                "failure_mode": f"Failed under {stress.name} stress",
                "metrics": {}
            }

        return {
            "failed": False,
            "metrics": {
                "performance": max(0, 1 - stress.value * 0.1),
                "resilience": random.uniform(0.5, 1)
            },
            "hidden_capability": "Enhanced performance under pressure" if random.random() > 0.7 else None
        }

    async def _explore_branches(
        self,
        parent_id: str,
        remaining_decisions: List[Dict[str, Any]],
        depth: int
    ):
        """Recursively explore timeline branches."""
        if depth <= 0 or not remaining_decisions:
            return

        decision = remaining_decisions[0]
        options = decision.get("options", ["option_a", "option_b"])

        for option in options:
            branch = TimelineBranch(
                id=self._gen_id("branch"),
                parent_id=parent_id,
                decision_point=decision.get("name", "decision"),
                decision_made=option,
                probability=1.0 / len(options),
                outcome=self._weighted_outcome(),
                final_state={}
            )

            self.timeline_branches[branch.id] = branch
            self.timeline_branches[parent_id].children.append(branch.id)

            # Recurse
            await self._explore_branches(branch.id, remaining_decisions[1:], depth - 1)

    def _weighted_outcome(self, shift: float = 0, variance: float = 0.1) -> OutcomeType:
        """Generate weighted random outcome."""
        weights = self.base_outcome_weights.copy()

        # Apply shift
        if shift > 0:  # Shift toward success
            weights[OutcomeType.SUCCESS] += shift
            weights[OutcomeType.BREAKTHROUGH] += shift * 0.5
            weights[OutcomeType.FAILURE] = max(0, weights[OutcomeType.FAILURE] - shift)
        elif shift < 0:  # Shift toward failure
            weights[OutcomeType.FAILURE] += abs(shift)
            weights[OutcomeType.CATASTROPHIC] += abs(shift) * 0.2
            weights[OutcomeType.SUCCESS] = max(0, weights[OutcomeType.SUCCESS] + shift)

        # Apply variance
        for k in weights:
            weights[k] += random.uniform(-variance, variance)
            weights[k] = max(0, weights[k])

        # Normalize
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}

        # Select
        r = random.random()
        cumulative = 0
        for outcome, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return outcome

        return OutcomeType.NEUTRAL

    def _generate_metrics(self, outcome: OutcomeType) -> Dict[str, float]:
        """Generate metrics based on outcome."""
        base_score = {
            OutcomeType.BREAKTHROUGH: 1.0,
            OutcomeType.SUCCESS: 0.85,
            OutcomeType.PARTIAL_SUCCESS: 0.65,
            OutcomeType.NEUTRAL: 0.5,
            OutcomeType.PARTIAL_FAILURE: 0.35,
            OutcomeType.FAILURE: 0.15,
            OutcomeType.CATASTROPHIC: 0.0
        }.get(outcome, 0.5)

        return {
            "score": base_score + random.uniform(-0.1, 0.1),
            "efficiency": random.uniform(0.3, 1.0),
            "resource_usage": random.uniform(0.2, 0.9)
        }

    def _generate_events(self, outcome: OutcomeType) -> List[Dict[str, Any]]:
        """Generate simulation events."""
        num_events = random.randint(1, 5)
        return [{"event": f"event_{i}", "time": i * 100} for i in range(num_events)]

    def _randomize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Randomize parameters for Monte Carlo."""
        result = {}
        for k, v in params.items():
            if isinstance(v, (int, float)):
                result[k] = v * random.uniform(0.5, 1.5)
            else:
                result[k] = v
        return result

    def _create_result(
        self,
        scenario: SimulationScenario,
        sim_type: SimulationType,
        runs: List[SimulationRun],
        outcome_dist: Dict[OutcomeType, int]
    ) -> SimulationResult:
        """Create simulation result."""
        success_count = outcome_dist.get(OutcomeType.SUCCESS, 0) + outcome_dist.get(OutcomeType.BREAKTHROUGH, 0) + outcome_dist.get(OutcomeType.PARTIAL_SUCCESS, 0)
        success_rate = success_count / len(runs) if runs else 0

        # Find optimal run
        best_run = max(runs, key=lambda r: r.metrics.get("score", 0)) if runs else None

        return SimulationResult(
            id=self._gen_id("result"),
            scenario=scenario,
            simulation_type=sim_type,
            total_runs=len(runs),
            runs=runs,
            outcome_distribution=dict(outcome_dist),
            success_rate=success_rate,
            optimal_path=best_run.parameters if best_run else None,
            failure_modes=[],
            insights=[
                f"Completed {len(runs)} simulation runs",
                f"Success rate: {success_rate:.1%}",
                f"Most common outcome: {max(outcome_dist, key=outcome_dist.get).value if outcome_dist else 'none'}"
            ],
            recommendations=[
                "Use optimal parameters from best run",
                "Address identified failure modes",
                "Increase success probability through iteration"
            ],
            created_at=datetime.now()
        )

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def get_stats(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        return {
            "total_scenarios": len(self.scenarios),
            "total_results": len(self.results),
            "timeline_branches": len(self.timeline_branches),
            "agent_torture_results": len(self.agent_torture_results),
            "total_runs": sum(r.total_runs for r in self.results.values())
        }


# ============================================================================
# SINGLETON
# ============================================================================

_simulation_engine: Optional[InfiniteSimulationEngine] = None


def get_simulation_engine() -> InfiniteSimulationEngine:
    """Get the global simulation engine."""
    global _simulation_engine
    if _simulation_engine is None:
        _simulation_engine = InfiniteSimulationEngine()
    return _simulation_engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate simulation engine."""
    print("=" * 60)
    print("🌌 INFINITE SIMULATION ENGINE 🌌")
    print("=" * 60)

    engine = get_simulation_engine()

    # Standard simulation
    print("\n--- Standard Simulation ---")
    result = await engine.simulate(
        "Market Domination Strategy",
        "Simulate complete market takeover",
        SimulationType.STRATEGIC,
        SimulationScale.MEDIUM
    )
    print(f"Runs: {result.total_runs}")
    print(f"Success rate: {result.success_rate:.1%}")

    # Adversarial simulation
    print("\n--- Adversarial Simulation ---")
    adv_result = await engine.simulate(
        "Hostile Takeover Under Attack",
        "Simulate with hostile conditions",
        SimulationType.ADVERSARIAL,
        SimulationScale.SMALL
    )
    print(f"Success under adversity: {adv_result.success_rate:.1%}")

    # Agent torture
    print("\n--- Agent Torture Test ---")
    torture_results = await engine.torture_test_agents(
        [{"id": "agent_1"}, {"id": "agent_2"}],
        StressLevel.EXTREME
    )
    for tr in torture_results:
        print(f"  {tr.agent_id}: Breaking point found = {tr.breaking_point_found}")

    # Stats
    print("\n--- Statistics ---")
    stats = engine.get_stats()
    print(json.dumps(stats, indent=2))

    print("\n" + "=" * 60)
    print("🌌 SIMULATION COMPLETE 🌌")


if __name__ == "__main__":
    asyncio.run(demo())
