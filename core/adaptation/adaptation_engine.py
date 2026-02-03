#!/usr/bin/env python3
"""
BAEL - Adaptation Engine
Dynamic adaptation and self-modification system.

Features:
- Behavioral adaptation
- Parameter optimization
- Strategy evolution
- Performance-driven learning
- Context-sensitive adjustment
- Self-modification protocols
- Adaptation policies
- Continuous improvement
"""

import asyncio
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AdaptationType(Enum):
    """Types of adaptation."""
    BEHAVIORAL = "behavioral"
    PARAMETRIC = "parametric"
    STRUCTURAL = "structural"
    STRATEGIC = "strategic"
    CONTEXTUAL = "contextual"


class AdaptationTrigger(Enum):
    """Triggers for adaptation."""
    PERFORMANCE_DECLINE = "performance_decline"
    CONTEXT_CHANGE = "context_change"
    GOAL_CHANGE = "goal_change"
    FEEDBACK = "feedback"
    TIME_BASED = "time_based"
    RESOURCE_CHANGE = "resource_change"


class AdaptationSpeed(Enum):
    """Speed of adaptation."""
    IMMEDIATE = "immediate"
    FAST = "fast"
    GRADUAL = "gradual"
    SLOW = "slow"


class AdaptationStatus(Enum):
    """Status of adaptation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVERTED = "reverted"
    FAILED = "failed"


class OptimizationMethod(Enum):
    """Optimization methods."""
    GRADIENT = "gradient"
    EVOLUTIONARY = "evolutionary"
    BAYESIAN = "bayesian"
    RANDOM_SEARCH = "random_search"
    GRID_SEARCH = "grid_search"


class PolicyType(Enum):
    """Adaptation policy types."""
    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    CONSERVATIVE = "conservative"
    REACTIVE = "reactive"
    PROACTIVE = "proactive"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Parameter:
    """Adaptable parameter."""
    param_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    value: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    step: float = 0.01
    is_discrete: bool = False
    description: str = ""


@dataclass
class ParameterState:
    """State of parameters at a point in time."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameters: Dict[str, float] = field(default_factory=dict)
    performance: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AdaptationContext:
    """Context for adaptation."""
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    environment: Dict[str, Any] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    constraints: Dict[str, float] = field(default_factory=dict)
    resources: Dict[str, float] = field(default_factory=dict)


@dataclass
class AdaptationAction:
    """Adaptation action to be taken."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    adaptation_type: AdaptationType = AdaptationType.PARAMETRIC
    target: str = ""
    old_value: Any = None
    new_value: Any = None
    reason: str = ""
    priority: float = 0.5
    status: AdaptationStatus = AdaptationStatus.PENDING


@dataclass
class AdaptationResult:
    """Result of adaptation."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str = ""
    success: bool = False
    old_performance: float = 0.0
    new_performance: float = 0.0
    improvement: float = 0.0
    side_effects: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """Performance metrics for adaptation."""
    metrics_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    accuracy: float = 0.0
    efficiency: float = 0.0
    latency: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    resource_usage: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class AdaptationPolicy:
    """Policy governing adaptation."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    policy_type: PolicyType = PolicyType.MODERATE
    min_performance_threshold: float = 0.5
    max_change_rate: float = 0.1
    cooldown_period: float = 60.0  # seconds
    require_approval: bool = False
    rollback_on_failure: bool = True


@dataclass
class AdaptationHistory:
    """History of adaptations."""
    history_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    adaptations: List[AdaptationResult] = field(default_factory=list)
    total_improvements: float = 0.0
    total_regressions: float = 0.0
    success_rate: float = 0.0


# =============================================================================
# PARAMETER OPTIMIZER
# =============================================================================

class ParameterOptimizer:
    """Optimize parameters."""

    def __init__(self, method: OptimizationMethod = OptimizationMethod.EVOLUTIONARY):
        self._method = method
        self._parameters: Dict[str, Parameter] = {}
        self._history: List[ParameterState] = []
        self._best_state: Optional[ParameterState] = None

    def register_parameter(self, parameter: Parameter) -> None:
        """Register adaptable parameter."""
        self._parameters[parameter.name] = parameter

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """Get parameter by name."""
        return self._parameters.get(name)

    def get_current_values(self) -> Dict[str, float]:
        """Get current parameter values."""
        return {
            name: param.value
            for name, param in self._parameters.items()
        }

    def set_value(self, name: str, value: float) -> bool:
        """Set parameter value."""
        param = self._parameters.get(name)
        if not param:
            return False

        # Clamp to range
        value = max(param.min_value, min(param.max_value, value))

        # Discretize if needed
        if param.is_discrete:
            value = round(value / param.step) * param.step

        param.value = value
        return True

    def record_performance(self, performance: float) -> ParameterState:
        """Record performance for current parameter state."""
        state = ParameterState(
            parameters=self.get_current_values(),
            performance=performance
        )

        self._history.append(state)

        if self._best_state is None or performance > self._best_state.performance:
            self._best_state = state

        return state

    def optimize_step(
        self,
        objective_function: Optional[Callable[[Dict[str, float]], float]] = None
    ) -> Dict[str, float]:
        """Perform one optimization step."""
        if self._method == OptimizationMethod.RANDOM_SEARCH:
            return self._random_search_step()
        elif self._method == OptimizationMethod.EVOLUTIONARY:
            return self._evolutionary_step()
        elif self._method == OptimizationMethod.GRADIENT:
            return self._gradient_step(objective_function)
        elif self._method == OptimizationMethod.BAYESIAN:
            return self._bayesian_step()
        else:
            return self._grid_search_step()

    def _random_search_step(self) -> Dict[str, float]:
        """Random search step."""
        new_values = {}
        for name, param in self._parameters.items():
            new_values[name] = random.uniform(param.min_value, param.max_value)
            self.set_value(name, new_values[name])
        return new_values

    def _evolutionary_step(self) -> Dict[str, float]:
        """Evolutionary optimization step."""
        new_values = {}

        for name, param in self._parameters.items():
            # Mutation
            mutation = random.gauss(0, (param.max_value - param.min_value) * 0.1)
            new_value = param.value + mutation
            new_values[name] = new_value
            self.set_value(name, new_value)

        return new_values

    def _gradient_step(
        self,
        objective: Optional[Callable] = None,
        learning_rate: float = 0.01
    ) -> Dict[str, float]:
        """Gradient-based optimization step."""
        new_values = {}
        epsilon = 0.001

        for name, param in self._parameters.items():
            if objective:
                # Numerical gradient
                current = self.get_current_values()

                current_plus = dict(current)
                current_plus[name] = param.value + epsilon

                current_minus = dict(current)
                current_minus[name] = param.value - epsilon

                gradient = (objective(current_plus) - objective(current_minus)) / (2 * epsilon)

                new_value = param.value + learning_rate * gradient
            else:
                # Random perturbation
                new_value = param.value + random.gauss(0, 0.01)

            new_values[name] = new_value
            self.set_value(name, new_value)

        return new_values

    def _bayesian_step(self) -> Dict[str, float]:
        """Bayesian optimization step (simplified)."""
        # Use best known state with exploration
        new_values = {}

        if self._best_state:
            # Exploit best known with exploration
            for name, param in self._parameters.items():
                best_value = self._best_state.parameters.get(name, param.value)
                exploration = random.gauss(0, (param.max_value - param.min_value) * 0.05)
                new_value = best_value + exploration
                new_values[name] = new_value
                self.set_value(name, new_value)
        else:
            return self._random_search_step()

        return new_values

    def _grid_search_step(self) -> Dict[str, float]:
        """Grid search step (next point)."""
        new_values = {}

        for name, param in self._parameters.items():
            # Move to next grid point
            step = (param.max_value - param.min_value) / 10
            new_value = param.value + step
            if new_value > param.max_value:
                new_value = param.min_value
            new_values[name] = new_value
            self.set_value(name, new_value)

        return new_values

    def get_best_state(self) -> Optional[ParameterState]:
        """Get best parameter state found."""
        return self._best_state

    def restore_best(self) -> None:
        """Restore parameters to best known state."""
        if self._best_state:
            for name, value in self._best_state.parameters.items():
                self.set_value(name, value)


# =============================================================================
# BEHAVIORAL ADAPTER
# =============================================================================

class BehavioralAdapter:
    """Adapt behavioral patterns."""

    def __init__(self):
        self._behaviors: Dict[str, Dict[str, Any]] = {}
        self._behavior_performance: Dict[str, List[float]] = defaultdict(list)
        self._current_behavior: Optional[str] = None

    def register_behavior(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> None:
        """Register a behavior."""
        self._behaviors[name] = config

    def set_behavior(self, name: str) -> bool:
        """Set current behavior."""
        if name in self._behaviors:
            self._current_behavior = name
            return True
        return False

    def get_current_behavior(self) -> Optional[str]:
        """Get current behavior."""
        return self._current_behavior

    def record_performance(
        self,
        behavior: str,
        performance: float
    ) -> None:
        """Record performance for behavior."""
        self._behavior_performance[behavior].append(performance)

    def get_behavior_stats(
        self,
        behavior: str
    ) -> Dict[str, float]:
        """Get statistics for behavior."""
        performances = self._behavior_performance.get(behavior, [])

        if not performances:
            return {"mean": 0.0, "std": 0.0, "count": 0}

        mean = sum(performances) / len(performances)
        variance = sum((p - mean) ** 2 for p in performances) / len(performances)
        std = math.sqrt(variance)

        return {
            "mean": mean,
            "std": std,
            "count": len(performances),
            "min": min(performances),
            "max": max(performances)
        }

    def adapt(self, current_performance: float) -> Optional[str]:
        """Adapt behavior based on performance."""
        if not self._current_behavior:
            return None

        current_stats = self.get_behavior_stats(self._current_behavior)

        # Check if adaptation needed
        if current_performance >= current_stats.get("mean", 0.5):
            return None  # No change needed

        # Find better behavior
        best_behavior = self._current_behavior
        best_mean = current_stats.get("mean", 0.0)

        for name, _ in self._behaviors.items():
            if name != self._current_behavior:
                stats = self.get_behavior_stats(name)
                if stats.get("mean", 0.0) > best_mean:
                    best_mean = stats["mean"]
                    best_behavior = name

        if best_behavior != self._current_behavior:
            self._current_behavior = best_behavior
            return best_behavior

        return None


# =============================================================================
# CONTEXT ADAPTER
# =============================================================================

class ContextAdapter:
    """Adapt to context changes."""

    def __init__(self):
        self._context_history: List[AdaptationContext] = []
        self._context_profiles: Dict[str, Dict[str, Any]] = {}
        self._current_context: Optional[AdaptationContext] = None

    def register_context_profile(
        self,
        name: str,
        environment_patterns: Dict[str, Any],
        recommended_config: Dict[str, Any]
    ) -> None:
        """Register context profile."""
        self._context_profiles[name] = {
            "patterns": environment_patterns,
            "config": recommended_config
        }

    def detect_context(
        self,
        environment: Dict[str, Any]
    ) -> Optional[str]:
        """Detect current context."""
        best_match = None
        best_score = 0.0

        for name, profile in self._context_profiles.items():
            patterns = profile["patterns"]
            score = self._compute_match_score(environment, patterns)

            if score > best_score:
                best_score = score
                best_match = name

        return best_match if best_score > 0.5 else None

    def _compute_match_score(
        self,
        environment: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> float:
        """Compute match score between environment and patterns."""
        if not patterns:
            return 0.0

        matches = 0
        total = len(patterns)

        for key, pattern in patterns.items():
            env_value = environment.get(key)

            if env_value is None:
                continue

            if isinstance(pattern, dict):
                if "min" in pattern and "max" in pattern:
                    if pattern["min"] <= env_value <= pattern["max"]:
                        matches += 1
            elif env_value == pattern:
                matches += 1

        return matches / total

    def update_context(
        self,
        environment: Dict[str, Any],
        goals: List[str],
        constraints: Dict[str, float],
        resources: Dict[str, float]
    ) -> AdaptationContext:
        """Update current context."""
        context = AdaptationContext(
            environment=environment,
            goals=goals,
            constraints=constraints,
            resources=resources
        )

        self._current_context = context
        self._context_history.append(context)

        return context

    def get_context_recommendations(
        self,
        context_name: str
    ) -> Dict[str, Any]:
        """Get recommended config for context."""
        profile = self._context_profiles.get(context_name)
        if profile:
            return profile.get("config", {})
        return {}


# =============================================================================
# STRATEGY EVOLVER
# =============================================================================

@dataclass
class Strategy:
    """Evolvable strategy."""
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    genes: Dict[str, float] = field(default_factory=dict)
    fitness: float = 0.0
    generation: int = 0


class StrategyEvolver:
    """Evolve strategies using genetic algorithms."""

    def __init__(
        self,
        population_size: int = 10,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7
    ):
        self._population_size = population_size
        self._mutation_rate = mutation_rate
        self._crossover_rate = crossover_rate
        self._population: List[Strategy] = []
        self._generation = 0
        self._gene_specs: Dict[str, Tuple[float, float]] = {}

    def define_gene(
        self,
        name: str,
        min_value: float,
        max_value: float
    ) -> None:
        """Define a gene."""
        self._gene_specs[name] = (min_value, max_value)

    def initialize_population(self) -> List[Strategy]:
        """Initialize random population."""
        self._population = []

        for i in range(self._population_size):
            genes = {}
            for name, (min_val, max_val) in self._gene_specs.items():
                genes[name] = random.uniform(min_val, max_val)

            strategy = Strategy(
                name=f"strategy_{i}",
                genes=genes,
                generation=0
            )
            self._population.append(strategy)

        return self._population

    def evaluate_fitness(
        self,
        strategy: Strategy,
        fitness_function: Callable[[Dict[str, float]], float]
    ) -> float:
        """Evaluate strategy fitness."""
        strategy.fitness = fitness_function(strategy.genes)
        return strategy.fitness

    def evolve(
        self,
        fitness_function: Callable[[Dict[str, float]], float]
    ) -> List[Strategy]:
        """Evolve population one generation."""
        # Evaluate all
        for strategy in self._population:
            self.evaluate_fitness(strategy, fitness_function)

        # Sort by fitness
        self._population.sort(key=lambda s: s.fitness, reverse=True)

        # Selection (top half)
        survivors = self._population[:self._population_size // 2]

        # Create new population
        new_population = list(survivors)

        while len(new_population) < self._population_size:
            # Select parents
            parent1 = random.choice(survivors)
            parent2 = random.choice(survivors)

            # Crossover
            if random.random() < self._crossover_rate:
                child = self._crossover(parent1, parent2)
            else:
                child = Strategy(
                    name=f"strategy_{len(new_population)}",
                    genes=dict(parent1.genes),
                    generation=self._generation + 1
                )

            # Mutation
            child = self._mutate(child)

            new_population.append(child)

        self._population = new_population
        self._generation += 1

        return self._population

    def _crossover(
        self,
        parent1: Strategy,
        parent2: Strategy
    ) -> Strategy:
        """Crossover two parents."""
        genes = {}

        for name in self._gene_specs:
            if random.random() < 0.5:
                genes[name] = parent1.genes.get(name, 0.0)
            else:
                genes[name] = parent2.genes.get(name, 0.0)

        return Strategy(
            name=f"child_{self._generation}",
            genes=genes,
            generation=self._generation + 1
        )

    def _mutate(self, strategy: Strategy) -> Strategy:
        """Mutate a strategy."""
        for name, (min_val, max_val) in self._gene_specs.items():
            if random.random() < self._mutation_rate:
                mutation = random.gauss(0, (max_val - min_val) * 0.1)
                new_value = strategy.genes.get(name, 0.0) + mutation
                strategy.genes[name] = max(min_val, min(max_val, new_value))

        return strategy

    def get_best(self) -> Optional[Strategy]:
        """Get best strategy."""
        if not self._population:
            return None

        return max(self._population, key=lambda s: s.fitness)


# =============================================================================
# ADAPTATION POLICY MANAGER
# =============================================================================

class AdaptationPolicyManager:
    """Manage adaptation policies."""

    def __init__(self):
        self._policies: Dict[str, AdaptationPolicy] = {}
        self._active_policy: Optional[str] = None
        self._last_adaptation_time: Dict[str, datetime] = {}

    def register_policy(self, policy: AdaptationPolicy) -> None:
        """Register adaptation policy."""
        self._policies[policy.name] = policy

    def set_active_policy(self, name: str) -> bool:
        """Set active policy."""
        if name in self._policies:
            self._active_policy = name
            return True
        return False

    def get_active_policy(self) -> Optional[AdaptationPolicy]:
        """Get active policy."""
        if self._active_policy:
            return self._policies.get(self._active_policy)
        return None

    def can_adapt(
        self,
        target: str,
        current_performance: float
    ) -> Tuple[bool, str]:
        """Check if adaptation is allowed."""
        policy = self.get_active_policy()

        if not policy:
            return True, "No policy active"

        # Check performance threshold
        if current_performance >= policy.min_performance_threshold:
            return False, "Performance above threshold"

        # Check cooldown
        last_time = self._last_adaptation_time.get(target)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < policy.cooldown_period:
                return False, f"Cooldown active ({policy.cooldown_period - elapsed:.0f}s remaining)"

        return True, "Adaptation allowed"

    def record_adaptation(self, target: str) -> None:
        """Record adaptation timestamp."""
        self._last_adaptation_time[target] = datetime.now()


# =============================================================================
# ADAPTATION ENGINE
# =============================================================================

class AdaptationEngine:
    """
    Adaptation Engine for BAEL.

    Dynamic adaptation and self-modification system.
    """

    def __init__(self):
        self._parameter_optimizer = ParameterOptimizer()
        self._behavioral_adapter = BehavioralAdapter()
        self._context_adapter = ContextAdapter()
        self._strategy_evolver = StrategyEvolver()
        self._policy_manager = AdaptationPolicyManager()

        self._actions: List[AdaptationAction] = []
        self._results: List[AdaptationResult] = []
        self._history = AdaptationHistory()

    # -------------------------------------------------------------------------
    # PARAMETER OPTIMIZATION
    # -------------------------------------------------------------------------

    def register_parameter(
        self,
        name: str,
        value: float,
        min_value: float = 0.0,
        max_value: float = 1.0,
        step: float = 0.01,
        is_discrete: bool = False,
        description: str = ""
    ) -> Parameter:
        """Register adaptable parameter."""
        param = Parameter(
            name=name,
            value=value,
            min_value=min_value,
            max_value=max_value,
            step=step,
            is_discrete=is_discrete,
            description=description
        )

        self._parameter_optimizer.register_parameter(param)
        return param

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """Get parameter."""
        return self._parameter_optimizer.get_parameter(name)

    def set_parameter(self, name: str, value: float) -> bool:
        """Set parameter value."""
        return self._parameter_optimizer.set_value(name, value)

    def get_all_parameters(self) -> Dict[str, float]:
        """Get all parameter values."""
        return self._parameter_optimizer.get_current_values()

    def optimize_parameters(
        self,
        performance: float,
        objective_function: Optional[Callable] = None
    ) -> Dict[str, float]:
        """Optimize parameters based on performance."""
        # Record current performance
        self._parameter_optimizer.record_performance(performance)

        # Check if optimization allowed
        can_adapt, reason = self._policy_manager.can_adapt(
            "parameters",
            performance
        )

        if not can_adapt:
            return self._parameter_optimizer.get_current_values()

        # Perform optimization step
        old_values = self._parameter_optimizer.get_current_values()
        new_values = self._parameter_optimizer.optimize_step(objective_function)

        # Record action
        action = AdaptationAction(
            adaptation_type=AdaptationType.PARAMETRIC,
            target="parameters",
            old_value=old_values,
            new_value=new_values,
            reason="Performance optimization",
            status=AdaptationStatus.COMPLETED
        )
        self._actions.append(action)

        # Record in policy manager
        self._policy_manager.record_adaptation("parameters")

        return new_values

    def restore_best_parameters(self) -> None:
        """Restore best known parameters."""
        self._parameter_optimizer.restore_best()

    # -------------------------------------------------------------------------
    # BEHAVIORAL ADAPTATION
    # -------------------------------------------------------------------------

    def register_behavior(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> None:
        """Register behavior."""
        self._behavioral_adapter.register_behavior(name, config)

    def set_behavior(self, name: str) -> bool:
        """Set current behavior."""
        return self._behavioral_adapter.set_behavior(name)

    def get_current_behavior(self) -> Optional[str]:
        """Get current behavior."""
        return self._behavioral_adapter.get_current_behavior()

    def adapt_behavior(
        self,
        performance: float
    ) -> Optional[str]:
        """Adapt behavior based on performance."""
        current = self._behavioral_adapter.get_current_behavior()

        # Check policy
        can_adapt, _ = self._policy_manager.can_adapt(
            "behavior",
            performance
        )

        if not can_adapt:
            return current

        # Record performance
        if current:
            self._behavioral_adapter.record_performance(current, performance)

        # Adapt
        new_behavior = self._behavioral_adapter.adapt(performance)

        if new_behavior:
            action = AdaptationAction(
                adaptation_type=AdaptationType.BEHAVIORAL,
                target="behavior",
                old_value=current,
                new_value=new_behavior,
                reason="Performance-driven adaptation",
                status=AdaptationStatus.COMPLETED
            )
            self._actions.append(action)
            self._policy_manager.record_adaptation("behavior")

        return new_behavior

    def get_behavior_stats(
        self,
        behavior: str
    ) -> Dict[str, float]:
        """Get behavior statistics."""
        return self._behavioral_adapter.get_behavior_stats(behavior)

    # -------------------------------------------------------------------------
    # CONTEXT ADAPTATION
    # -------------------------------------------------------------------------

    def register_context_profile(
        self,
        name: str,
        environment_patterns: Dict[str, Any],
        recommended_config: Dict[str, Any]
    ) -> None:
        """Register context profile."""
        self._context_adapter.register_context_profile(
            name,
            environment_patterns,
            recommended_config
        )

    def update_context(
        self,
        environment: Dict[str, Any],
        goals: Optional[List[str]] = None,
        constraints: Optional[Dict[str, float]] = None,
        resources: Optional[Dict[str, float]] = None
    ) -> AdaptationContext:
        """Update current context."""
        return self._context_adapter.update_context(
            environment,
            goals or [],
            constraints or {},
            resources or {}
        )

    def detect_context(
        self,
        environment: Dict[str, Any]
    ) -> Optional[str]:
        """Detect context from environment."""
        return self._context_adapter.detect_context(environment)

    def get_context_config(
        self,
        context_name: str
    ) -> Dict[str, Any]:
        """Get recommended config for context."""
        return self._context_adapter.get_context_recommendations(context_name)

    def adapt_to_context(
        self,
        environment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt to detected context."""
        # Detect context
        context = self.detect_context(environment)

        if context:
            # Get recommendations
            config = self.get_context_config(context)

            # Apply parameter changes
            for name, value in config.items():
                if isinstance(value, (int, float)):
                    self.set_parameter(name, value)

            action = AdaptationAction(
                adaptation_type=AdaptationType.CONTEXTUAL,
                target="context",
                old_value=None,
                new_value=context,
                reason=f"Context detected: {context}",
                status=AdaptationStatus.COMPLETED
            )
            self._actions.append(action)

            return config

        return {}

    # -------------------------------------------------------------------------
    # STRATEGY EVOLUTION
    # -------------------------------------------------------------------------

    def define_strategy_gene(
        self,
        name: str,
        min_value: float,
        max_value: float
    ) -> None:
        """Define strategy gene."""
        self._strategy_evolver.define_gene(name, min_value, max_value)

    def initialize_strategies(self) -> List[Strategy]:
        """Initialize strategy population."""
        return self._strategy_evolver.initialize_population()

    def evolve_strategies(
        self,
        fitness_function: Callable[[Dict[str, float]], float]
    ) -> List[Strategy]:
        """Evolve strategies."""
        return self._strategy_evolver.evolve(fitness_function)

    def get_best_strategy(self) -> Optional[Strategy]:
        """Get best strategy."""
        return self._strategy_evolver.get_best()

    # -------------------------------------------------------------------------
    # POLICY MANAGEMENT
    # -------------------------------------------------------------------------

    def register_policy(
        self,
        name: str,
        policy_type: PolicyType = PolicyType.MODERATE,
        min_performance_threshold: float = 0.5,
        max_change_rate: float = 0.1,
        cooldown_period: float = 60.0,
        require_approval: bool = False,
        rollback_on_failure: bool = True
    ) -> AdaptationPolicy:
        """Register adaptation policy."""
        policy = AdaptationPolicy(
            name=name,
            policy_type=policy_type,
            min_performance_threshold=min_performance_threshold,
            max_change_rate=max_change_rate,
            cooldown_period=cooldown_period,
            require_approval=require_approval,
            rollback_on_failure=rollback_on_failure
        )

        self._policy_manager.register_policy(policy)
        return policy

    def set_active_policy(self, name: str) -> bool:
        """Set active policy."""
        return self._policy_manager.set_active_policy(name)

    def get_active_policy(self) -> Optional[AdaptationPolicy]:
        """Get active policy."""
        return self._policy_manager.get_active_policy()

    # -------------------------------------------------------------------------
    # HISTORY AND STATISTICS
    # -------------------------------------------------------------------------

    def get_adaptation_actions(
        self,
        adaptation_type: Optional[AdaptationType] = None
    ) -> List[AdaptationAction]:
        """Get adaptation actions."""
        actions = self._actions

        if adaptation_type:
            actions = [
                a for a in actions
                if a.adaptation_type == adaptation_type
            ]

        return actions

    def get_adaptation_history(self) -> AdaptationHistory:
        """Get adaptation history."""
        return self._history


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Adaptation Engine."""
    print("=" * 70)
    print("BAEL - ADAPTATION ENGINE DEMO")
    print("Dynamic Adaptation and Self-Modification System")
    print("=" * 70)
    print()

    engine = AdaptationEngine()

    # 1. Register Parameters
    print("1. REGISTER PARAMETERS:")
    print("-" * 40)

    engine.register_parameter(
        "learning_rate",
        value=0.01,
        min_value=0.0001,
        max_value=0.1,
        description="Learning rate for optimization"
    )

    engine.register_parameter(
        "exploration_rate",
        value=0.2,
        min_value=0.0,
        max_value=1.0,
        description="Exploration vs exploitation"
    )

    engine.register_parameter(
        "batch_size",
        value=32.0,
        min_value=1.0,
        max_value=256.0,
        step=1.0,
        is_discrete=True,
        description="Batch size for processing"
    )

    params = engine.get_all_parameters()
    for name, value in params.items():
        print(f"   {name}: {value:.4f}")
    print()

    # 2. Register Policy
    print("2. REGISTER POLICY:")
    print("-" * 40)

    policy = engine.register_policy(
        "moderate_adaptation",
        policy_type=PolicyType.MODERATE,
        min_performance_threshold=0.3,
        max_change_rate=0.1,
        cooldown_period=5.0,
        rollback_on_failure=True
    )

    engine.set_active_policy("moderate_adaptation")

    print(f"   Policy: {policy.name}")
    print(f"   Type: {policy.policy_type.value}")
    print(f"   Threshold: {policy.min_performance_threshold:.1%}")
    print()

    # 3. Parameter Optimization
    print("3. PARAMETER OPTIMIZATION:")
    print("-" * 40)

    for i in range(3):
        performance = 0.4 + random.uniform(-0.1, 0.2)
        new_params = engine.optimize_parameters(performance)
        print(f"   Iteration {i+1}: performance={performance:.2f}")
        for name, value in new_params.items():
            print(f"     {name}: {value:.4f}")
    print()

    # 4. Register Behaviors
    print("4. REGISTER BEHAVIORS:")
    print("-" * 40)

    engine.register_behavior("exploratory", {
        "exploration_rate": 0.8,
        "risk_tolerance": 0.7
    })

    engine.register_behavior("exploitative", {
        "exploration_rate": 0.2,
        "risk_tolerance": 0.3
    })

    engine.register_behavior("balanced", {
        "exploration_rate": 0.5,
        "risk_tolerance": 0.5
    })

    engine.set_behavior("balanced")
    print(f"   Current behavior: {engine.get_current_behavior()}")
    print()

    # 5. Behavioral Adaptation
    print("5. BEHAVIORAL ADAPTATION:")
    print("-" * 40)

    # Simulate performance history
    for i in range(5):
        perf = 0.3 + random.uniform(0, 0.4)
        adapted = engine.adapt_behavior(perf)
        if adapted:
            print(f"   Adapted to: {adapted}")
        else:
            print(f"   No change needed (perf={perf:.2f})")
    print()

    # 6. Context Profiles
    print("6. CONTEXT PROFILES:")
    print("-" * 40)

    engine.register_context_profile(
        "high_load",
        {"cpu_usage": {"min": 0.7, "max": 1.0}, "memory_usage": {"min": 0.7, "max": 1.0}},
        {"batch_size": 16, "learning_rate": 0.005}
    )

    engine.register_context_profile(
        "low_load",
        {"cpu_usage": {"min": 0.0, "max": 0.3}, "memory_usage": {"min": 0.0, "max": 0.3}},
        {"batch_size": 128, "learning_rate": 0.02}
    )

    # Detect context
    env = {"cpu_usage": 0.8, "memory_usage": 0.75}
    context = engine.detect_context(env)
    print(f"   Environment: {env}")
    print(f"   Detected context: {context}")
    print()

    # 7. Context Adaptation
    print("7. CONTEXT ADAPTATION:")
    print("-" * 40)

    config = engine.adapt_to_context(env)
    print(f"   Applied config: {config}")
    print()

    # 8. Strategy Evolution
    print("8. STRATEGY EVOLUTION:")
    print("-" * 40)

    engine.define_strategy_gene("aggression", 0.0, 1.0)
    engine.define_strategy_gene("patience", 0.0, 1.0)
    engine.define_strategy_gene("adaptability", 0.0, 1.0)

    population = engine.initialize_strategies()
    print(f"   Initialized {len(population)} strategies")

    # Define fitness function
    def fitness(genes: Dict[str, float]) -> float:
        return (genes.get("adaptability", 0) * 0.5 +
                genes.get("patience", 0) * 0.3 +
                (1 - genes.get("aggression", 0)) * 0.2)

    # Evolve for a few generations
    for gen in range(3):
        population = engine.evolve_strategies(fitness)
        best = engine.get_best_strategy()
        if best:
            print(f"   Gen {gen+1}: best fitness = {best.fitness:.3f}")
    print()

    # 9. Best Strategy
    print("9. BEST STRATEGY:")
    print("-" * 40)

    best = engine.get_best_strategy()
    if best:
        print(f"   Name: {best.name}")
        print(f"   Fitness: {best.fitness:.3f}")
        print("   Genes:")
        for gene, value in best.genes.items():
            print(f"     {gene}: {value:.3f}")
    print()

    # 10. Behavior Stats
    print("10. BEHAVIOR STATS:")
    print("-" * 40)

    current = engine.get_current_behavior()
    if current:
        stats = engine.get_behavior_stats(current)
        print(f"   Behavior: {current}")
        for key, value in stats.items():
            print(f"     {key}: {value:.3f}")
    print()

    # 11. Adaptation Actions
    print("11. ADAPTATION ACTIONS:")
    print("-" * 40)

    actions = engine.get_adaptation_actions()
    print(f"   Total actions: {len(actions)}")
    for action in actions[-5:]:
        print(f"     - {action.adaptation_type.value}: {action.target}")
    print()

    # 12. Policy Check
    print("12. POLICY CHECK:")
    print("-" * 40)

    policy = engine.get_active_policy()
    if policy:
        print(f"   Active policy: {policy.name}")
        print(f"   Cooldown: {policy.cooldown_period}s")
        print(f"   Rollback on failure: {policy.rollback_on_failure}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Adaptation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
