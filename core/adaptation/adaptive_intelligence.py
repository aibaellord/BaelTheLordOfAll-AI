#!/usr/bin/env python3
"""
BAEL - Adaptive Intelligence System
Dynamic adaptation and self-modification capabilities.

Features:
- Neural architecture search
- Hyperparameter optimization
- Strategy adaptation
- Behavior modification
- Performance-driven evolution
- Context-aware reconfiguration
"""

import asyncio
import hashlib
import json
import logging
import math
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class AdaptationType(Enum):
    """Types of adaptation."""
    STRUCTURAL = "structural"         # Architecture changes
    PARAMETRIC = "parametric"         # Parameter tuning
    STRATEGIC = "strategic"           # Strategy selection
    BEHAVIORAL = "behavioral"         # Behavior modification
    CONTEXTUAL = "contextual"         # Context-based adaptation


class OptimizationMethod(Enum):
    """Optimization methods."""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    EVOLUTIONARY = "evolutionary"
    REINFORCEMENT = "reinforcement"


class AdaptationTrigger(Enum):
    """Triggers for adaptation."""
    PERFORMANCE_DROP = "performance_drop"
    CONTEXT_CHANGE = "context_change"
    RESOURCE_CONSTRAINT = "resource_constraint"
    USER_FEEDBACK = "user_feedback"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


@dataclass
class AdaptationConfig:
    """Configuration for adaptation."""
    name: str
    parameter_space: Dict[str, Any]
    optimization_method: OptimizationMethod = OptimizationMethod.BAYESIAN
    evaluation_metric: str = "accuracy"
    max_iterations: int = 100
    early_stopping_patience: int = 10
    min_improvement: float = 0.001


@dataclass
class AdaptationResult:
    """Result of an adaptation."""
    id: str
    adaptation_type: AdaptationType
    trigger: AdaptationTrigger
    before_config: Dict[str, Any]
    after_config: Dict[str, Any]
    before_performance: float
    after_performance: float
    improvement: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HyperParameter:
    """Hyperparameter definition."""
    name: str
    value_type: str  # "int", "float", "categorical", "bool"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: List[Any] = field(default_factory=list)
    default: Any = None
    log_scale: bool = False

    def sample(self) -> Any:
        """Sample a random value."""
        if self.value_type == "int":
            if self.log_scale:
                log_min = math.log(max(1, self.min_value))
                log_max = math.log(self.max_value)
                return int(math.exp(random.uniform(log_min, log_max)))
            return random.randint(int(self.min_value), int(self.max_value))
        elif self.value_type == "float":
            if self.log_scale:
                log_min = math.log(max(1e-10, self.min_value))
                log_max = math.log(self.max_value)
                return math.exp(random.uniform(log_min, log_max))
            return random.uniform(self.min_value, self.max_value)
        elif self.value_type == "categorical":
            return random.choice(self.choices)
        elif self.value_type == "bool":
            return random.choice([True, False])
        return self.default


# =============================================================================
# SEARCH SPACE
# =============================================================================

class SearchSpace:
    """Search space for optimization."""

    def __init__(self):
        self.parameters: Dict[str, HyperParameter] = {}

    def add_int(
        self,
        name: str,
        min_value: int,
        max_value: int,
        default: int = None,
        log_scale: bool = False
    ) -> 'SearchSpace':
        """Add integer parameter."""
        self.parameters[name] = HyperParameter(
            name=name,
            value_type="int",
            min_value=min_value,
            max_value=max_value,
            default=default or min_value,
            log_scale=log_scale
        )
        return self

    def add_float(
        self,
        name: str,
        min_value: float,
        max_value: float,
        default: float = None,
        log_scale: bool = False
    ) -> 'SearchSpace':
        """Add float parameter."""
        self.parameters[name] = HyperParameter(
            name=name,
            value_type="float",
            min_value=min_value,
            max_value=max_value,
            default=default or min_value,
            log_scale=log_scale
        )
        return self

    def add_categorical(
        self,
        name: str,
        choices: List[Any],
        default: Any = None
    ) -> 'SearchSpace':
        """Add categorical parameter."""
        self.parameters[name] = HyperParameter(
            name=name,
            value_type="categorical",
            choices=choices,
            default=default or choices[0]
        )
        return self

    def add_bool(
        self,
        name: str,
        default: bool = False
    ) -> 'SearchSpace':
        """Add boolean parameter."""
        self.parameters[name] = HyperParameter(
            name=name,
            value_type="bool",
            default=default
        )
        return self

    def sample(self) -> Dict[str, Any]:
        """Sample a configuration."""
        return {
            name: param.sample()
            for name, param in self.parameters.items()
        }

    def get_default(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            name: param.default
            for name, param in self.parameters.items()
        }


# =============================================================================
# OPTIMIZATION STRATEGIES
# =============================================================================

class Optimizer(ABC):
    """Abstract optimizer."""

    @abstractmethod
    async def suggest(self) -> Dict[str, Any]:
        """Suggest next configuration."""
        pass

    @abstractmethod
    def update(self, config: Dict[str, Any], score: float) -> None:
        """Update with evaluation result."""
        pass

    @abstractmethod
    def get_best(self) -> Tuple[Dict[str, Any], float]:
        """Get best configuration found."""
        pass


class RandomSearchOptimizer(Optimizer):
    """Random search optimizer."""

    def __init__(self, search_space: SearchSpace):
        self.search_space = search_space
        self.history: List[Tuple[Dict[str, Any], float]] = []

    async def suggest(self) -> Dict[str, Any]:
        """Suggest random configuration."""
        return self.search_space.sample()

    def update(self, config: Dict[str, Any], score: float) -> None:
        """Record evaluation result."""
        self.history.append((config, score))

    def get_best(self) -> Tuple[Dict[str, Any], float]:
        """Get best configuration."""
        if not self.history:
            return self.search_space.get_default(), 0.0
        return max(self.history, key=lambda x: x[1])


class BayesianOptimizer(Optimizer):
    """Bayesian optimization with Gaussian Process surrogate."""

    def __init__(
        self,
        search_space: SearchSpace,
        exploration_weight: float = 1.0
    ):
        self.search_space = search_space
        self.exploration_weight = exploration_weight
        self.history: List[Tuple[Dict[str, Any], float]] = []

    async def suggest(self) -> Dict[str, Any]:
        """Suggest next configuration using acquisition function."""
        if len(self.history) < 5:
            # Initial random exploration
            return self.search_space.sample()

        # Generate candidates
        candidates = [self.search_space.sample() for _ in range(100)]

        # Score candidates using Expected Improvement
        scored = []
        for candidate in candidates:
            ei = self._expected_improvement(candidate)
            scored.append((candidate, ei))

        # Return best candidate
        return max(scored, key=lambda x: x[1])[0]

    def _expected_improvement(self, config: Dict[str, Any]) -> float:
        """Compute expected improvement."""
        if not self.history:
            return 0.0

        # Simple approximation using nearest neighbors
        distances = []
        for hist_config, hist_score in self.history:
            dist = self._config_distance(config, hist_config)
            distances.append((dist, hist_score))

        # Weight by distance
        distances.sort(key=lambda x: x[0])
        k = min(3, len(distances))

        mean = sum(d[1] for d in distances[:k]) / k
        std = math.sqrt(sum((d[1] - mean) ** 2 for d in distances[:k]) / k) + 0.01

        best_score = max(score for _, score in self.history)

        # Expected improvement
        z = (mean - best_score) / std
        ei = std * (z * self._cdf(z) + self._pdf(z))

        return ei + self.exploration_weight * std

    def _config_distance(
        self,
        c1: Dict[str, Any],
        c2: Dict[str, Any]
    ) -> float:
        """Compute distance between configurations."""
        dist = 0.0
        for name, param in self.search_space.parameters.items():
            v1 = c1.get(name, param.default)
            v2 = c2.get(name, param.default)

            if param.value_type in ["int", "float"]:
                range_size = param.max_value - param.min_value
                if range_size > 0:
                    dist += ((v1 - v2) / range_size) ** 2
            elif param.value_type == "categorical":
                dist += 0 if v1 == v2 else 1
            elif param.value_type == "bool":
                dist += 0 if v1 == v2 else 1

        return math.sqrt(dist)

    def _pdf(self, x: float) -> float:
        """Standard normal PDF."""
        return math.exp(-x*x/2) / math.sqrt(2 * math.pi)

    def _cdf(self, x: float) -> float:
        """Standard normal CDF approximation."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def update(self, config: Dict[str, Any], score: float) -> None:
        """Update with evaluation result."""
        self.history.append((config, score))

    def get_best(self) -> Tuple[Dict[str, Any], float]:
        """Get best configuration."""
        if not self.history:
            return self.search_space.get_default(), 0.0
        return max(self.history, key=lambda x: x[1])


class EvolutionaryOptimizer(Optimizer):
    """Evolutionary optimization."""

    def __init__(
        self,
        search_space: SearchSpace,
        population_size: int = 20,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7
    ):
        self.search_space = search_space
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate

        self.population: List[Tuple[Dict[str, Any], float]] = []
        self.generation = 0

    async def suggest(self) -> Dict[str, Any]:
        """Suggest next configuration using evolution."""
        if len(self.population) < self.population_size:
            return self.search_space.sample()

        # Selection
        parents = self._tournament_selection(2)

        # Crossover
        if random.random() < self.crossover_rate:
            child = self._crossover(parents[0][0], parents[1][0])
        else:
            child = parents[0][0].copy()

        # Mutation
        child = self._mutate(child)

        return child

    def _tournament_selection(
        self,
        n: int,
        tournament_size: int = 3
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Tournament selection."""
        selected = []
        for _ in range(n):
            tournament = random.sample(self.population, min(tournament_size, len(self.population)))
            winner = max(tournament, key=lambda x: x[1])
            selected.append(winner)
        return selected

    def _crossover(
        self,
        parent1: Dict[str, Any],
        parent2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Uniform crossover."""
        child = {}
        for name in self.search_space.parameters:
            if random.random() < 0.5:
                child[name] = parent1.get(name)
            else:
                child[name] = parent2.get(name)
        return child

    def _mutate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate configuration."""
        result = config.copy()

        for name, param in self.search_space.parameters.items():
            if random.random() < self.mutation_rate:
                result[name] = param.sample()

        return result

    def update(self, config: Dict[str, Any], score: float) -> None:
        """Update population."""
        self.population.append((config, score))

        # Keep best individuals
        if len(self.population) > self.population_size * 2:
            self.population.sort(key=lambda x: x[1], reverse=True)
            self.population = self.population[:self.population_size]
            self.generation += 1

    def get_best(self) -> Tuple[Dict[str, Any], float]:
        """Get best configuration."""
        if not self.population:
            return self.search_space.get_default(), 0.0
        return max(self.population, key=lambda x: x[1])


# =============================================================================
# STRATEGY ADAPTATION
# =============================================================================

class Strategy:
    """Execution strategy."""

    def __init__(
        self,
        name: str,
        config: Dict[str, Any] = None,
        conditions: List[Callable] = None
    ):
        self.name = name
        self.config = config or {}
        self.conditions = conditions or []
        self.usage_count = 0
        self.success_rate = 0.5
        self.avg_performance = 0.5

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if strategy matches context."""
        return all(cond(context) for cond in self.conditions)

    def update_stats(self, success: bool, performance: float) -> None:
        """Update strategy statistics."""
        self.usage_count += 1
        alpha = 0.1  # Learning rate
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1 if success else 0)
        self.avg_performance = (1 - alpha) * self.avg_performance + alpha * performance


class StrategySelector:
    """Select best strategy for context."""

    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.selection_history: List[Dict[str, Any]] = []

    def register(self, strategy: Strategy) -> None:
        """Register a strategy."""
        self.strategies[strategy.name] = strategy

    def select(
        self,
        context: Dict[str, Any],
        exploration_rate: float = 0.1
    ) -> Optional[Strategy]:
        """Select best strategy for context."""
        # Find matching strategies
        matching = [
            s for s in self.strategies.values()
            if s.matches(context)
        ]

        if not matching:
            matching = list(self.strategies.values())

        if not matching:
            return None

        # Epsilon-greedy selection
        if random.random() < exploration_rate:
            selected = random.choice(matching)
        else:
            # Select by expected value (UCB-like)
            scored = []
            for s in matching:
                exploration_bonus = math.sqrt(2 * math.log(sum(
                    st.usage_count for st in matching
                ) + 1) / (s.usage_count + 1))
                score = s.avg_performance + exploration_bonus
                scored.append((s, score))

            selected = max(scored, key=lambda x: x[1])[0]

        self.selection_history.append({
            "context": context,
            "selected": selected.name,
            "timestamp": datetime.now().isoformat()
        })

        return selected

    def update(
        self,
        strategy_name: str,
        success: bool,
        performance: float
    ) -> None:
        """Update strategy statistics."""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].update_stats(success, performance)

    def get_ranking(self) -> List[Dict[str, Any]]:
        """Get strategy ranking."""
        ranked = sorted(
            self.strategies.values(),
            key=lambda s: s.avg_performance * s.success_rate,
            reverse=True
        )

        return [
            {
                "name": s.name,
                "usage": s.usage_count,
                "success_rate": s.success_rate,
                "avg_performance": s.avg_performance,
                "score": s.avg_performance * s.success_rate
            }
            for s in ranked
        ]


# =============================================================================
# BEHAVIOR MODIFICATION
# =============================================================================

@dataclass
class Behavior:
    """Modifiable behavior."""
    name: str
    handler: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 0


class BehaviorManager:
    """Manage and modify behaviors."""

    def __init__(self):
        self.behaviors: Dict[str, Behavior] = {}
        self.behavior_chains: Dict[str, List[str]] = {}
        self.modification_history: List[Dict[str, Any]] = []

    def register(
        self,
        name: str,
        handler: Callable,
        parameters: Dict[str, Any] = None,
        priority: int = 0
    ) -> None:
        """Register a behavior."""
        self.behaviors[name] = Behavior(
            name=name,
            handler=handler,
            parameters=parameters or {},
            priority=priority
        )

    def modify(
        self,
        name: str,
        parameter: str,
        value: Any
    ) -> None:
        """Modify behavior parameter."""
        if name in self.behaviors:
            old_value = self.behaviors[name].parameters.get(parameter)
            self.behaviors[name].parameters[parameter] = value

            self.modification_history.append({
                "behavior": name,
                "parameter": parameter,
                "old_value": old_value,
                "new_value": value,
                "timestamp": datetime.now().isoformat()
            })

    def enable(self, name: str) -> None:
        """Enable a behavior."""
        if name in self.behaviors:
            self.behaviors[name].enabled = True

    def disable(self, name: str) -> None:
        """Disable a behavior."""
        if name in self.behaviors:
            self.behaviors[name].enabled = False

    def set_chain(self, name: str, chain: List[str]) -> None:
        """Set a behavior chain."""
        self.behavior_chains[name] = chain

    async def execute(
        self,
        name: str,
        context: Dict[str, Any]
    ) -> Any:
        """Execute a behavior."""
        behavior = self.behaviors.get(name)
        if not behavior or not behavior.enabled:
            return None

        return await behavior.handler(context, behavior.parameters)

    async def execute_chain(
        self,
        chain_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a behavior chain."""
        chain = self.behavior_chains.get(chain_name, [])
        results = {}

        for behavior_name in chain:
            result = await self.execute(behavior_name, context)
            results[behavior_name] = result
            context[f"_result_{behavior_name}"] = result

        return results

    def get_active_behaviors(self) -> List[str]:
        """Get list of active behaviors."""
        return [
            name for name, b in self.behaviors.items()
            if b.enabled
        ]


# =============================================================================
# ADAPTIVE INTELLIGENCE SYSTEM
# =============================================================================

class AdaptiveIntelligence:
    """Main adaptive intelligence system."""

    def __init__(self):
        # Optimization
        self.search_spaces: Dict[str, SearchSpace] = {}
        self.optimizers: Dict[str, Optimizer] = {}

        # Strategy
        self.strategy_selector = StrategySelector()

        # Behavior
        self.behavior_manager = BehaviorManager()

        # Tracking
        self.adaptation_history: List[AdaptationResult] = []
        self.performance_history: List[float] = []
        self.current_config: Dict[str, Any] = {}

    def define_search_space(
        self,
        name: str,
        space: SearchSpace
    ) -> None:
        """Define a search space."""
        self.search_spaces[name] = space

    def create_optimizer(
        self,
        name: str,
        method: OptimizationMethod = OptimizationMethod.BAYESIAN
    ) -> Optimizer:
        """Create optimizer for search space."""
        if name not in self.search_spaces:
            raise ValueError(f"Unknown search space: {name}")

        space = self.search_spaces[name]

        if method == OptimizationMethod.RANDOM_SEARCH:
            optimizer = RandomSearchOptimizer(space)
        elif method == OptimizationMethod.BAYESIAN:
            optimizer = BayesianOptimizer(space)
        elif method == OptimizationMethod.EVOLUTIONARY:
            optimizer = EvolutionaryOptimizer(space)
        else:
            optimizer = RandomSearchOptimizer(space)

        self.optimizers[name] = optimizer
        return optimizer

    async def optimize(
        self,
        space_name: str,
        evaluate: Callable,
        max_iterations: int = 50,
        early_stopping_patience: int = 10,
        min_improvement: float = 0.001,
        callback: Callable = None
    ) -> Dict[str, Any]:
        """Run optimization."""
        if space_name not in self.optimizers:
            self.create_optimizer(space_name)

        optimizer = self.optimizers[space_name]

        best_score = float('-inf')
        patience_counter = 0

        for i in range(max_iterations):
            # Suggest configuration
            config = await optimizer.suggest()

            # Evaluate
            score = await evaluate(config)

            # Update optimizer
            optimizer.update(config, score)

            # Track progress
            self.performance_history.append(score)

            if callback:
                await callback(i, config, score)

            # Check improvement
            if score > best_score + min_improvement:
                best_score = score
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= early_stopping_patience:
                logger.info(f"Early stopping at iteration {i}")
                break

        best_config, best_score = optimizer.get_best()
        self.current_config = best_config

        return {
            "best_config": best_config,
            "best_score": best_score,
            "iterations": i + 1
        }

    async def adapt(
        self,
        trigger: AdaptationTrigger,
        context: Dict[str, Any],
        evaluate: Callable
    ) -> AdaptationResult:
        """Perform adaptation based on trigger."""
        before_config = self.current_config.copy()
        before_performance = await evaluate(before_config) if before_config else 0.0

        # Determine adaptation type
        if trigger == AdaptationTrigger.PERFORMANCE_DROP:
            adaptation_type = AdaptationType.PARAMETRIC
        elif trigger == AdaptationTrigger.CONTEXT_CHANGE:
            adaptation_type = AdaptationType.CONTEXTUAL
        elif trigger == AdaptationTrigger.RESOURCE_CONSTRAINT:
            adaptation_type = AdaptationType.STRUCTURAL
        else:
            adaptation_type = AdaptationType.BEHAVIORAL

        # Perform adaptation
        logger.info(f"Adapting due to {trigger.value}...")

        # Quick optimization
        for space_name, optimizer in self.optimizers.items():
            for _ in range(10):
                config = await optimizer.suggest()
                score = await evaluate(config)
                optimizer.update(config, score)

        best_config, _ = optimizer.get_best() if optimizer else (before_config, 0)
        self.current_config = best_config

        after_performance = await evaluate(best_config)

        result = AdaptationResult(
            id=str(uuid4()),
            adaptation_type=adaptation_type,
            trigger=trigger,
            before_config=before_config,
            after_config=best_config,
            before_performance=before_performance,
            after_performance=after_performance,
            improvement=after_performance - before_performance
        )

        self.adaptation_history.append(result)

        return result

    def register_strategy(
        self,
        name: str,
        config: Dict[str, Any],
        conditions: List[Callable] = None
    ) -> None:
        """Register a strategy."""
        strategy = Strategy(
            name=name,
            config=config,
            conditions=conditions or []
        )
        self.strategy_selector.register(strategy)

    def select_strategy(
        self,
        context: Dict[str, Any]
    ) -> Optional[Strategy]:
        """Select best strategy for context."""
        return self.strategy_selector.select(context)

    def register_behavior(
        self,
        name: str,
        handler: Callable,
        parameters: Dict[str, Any] = None
    ) -> None:
        """Register a behavior."""
        self.behavior_manager.register(name, handler, parameters)

    def modify_behavior(
        self,
        name: str,
        parameter: str,
        value: Any
    ) -> None:
        """Modify a behavior."""
        self.behavior_manager.modify(name, parameter, value)

    def get_status(self) -> Dict[str, Any]:
        """Get adaptation status."""
        return {
            "search_spaces": list(self.search_spaces.keys()),
            "optimizers": list(self.optimizers.keys()),
            "strategies": len(self.strategy_selector.strategies),
            "behaviors": len(self.behavior_manager.behaviors),
            "adaptations": len(self.adaptation_history),
            "current_config": self.current_config,
            "performance_trend": self.performance_history[-10:] if self.performance_history else []
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo adaptive intelligence system."""
    print("=== Adaptive Intelligence System Demo ===\n")

    # Create system
    ai = AdaptiveIntelligence()

    # 1. Define search space
    print("1. Defining Search Space:")
    space = SearchSpace()
    space.add_float("learning_rate", 0.0001, 0.1, log_scale=True)
    space.add_int("hidden_size", 32, 512)
    space.add_int("num_layers", 1, 8)
    space.add_categorical("activation", ["relu", "gelu", "tanh"])
    space.add_float("dropout", 0.0, 0.5)
    space.add_bool("use_batch_norm")

    ai.define_search_space("neural_network", space)
    print(f"   Defined space with {len(space.parameters)} parameters")

    # 2. Create optimizer
    print("\n2. Creating Optimizers:")
    ai.create_optimizer("neural_network", OptimizationMethod.BAYESIAN)
    print("   Created Bayesian optimizer")

    # 3. Run optimization
    print("\n3. Running Optimization:")

    # Mock evaluation function
    async def evaluate(config):
        # Simulated performance based on config
        score = 0.5

        # Learning rate sweet spot
        lr = config.get("learning_rate", 0.01)
        score += 0.1 * math.exp(-10 * (lr - 0.01) ** 2)

        # Hidden size
        hs = config.get("hidden_size", 128)
        score += 0.1 * (1 - abs(hs - 256) / 256)

        # Layers
        layers = config.get("num_layers", 3)
        score += 0.05 * (1 - abs(layers - 4) / 4)

        # Activation
        if config.get("activation") == "gelu":
            score += 0.05

        # Add noise
        score += random.gauss(0, 0.05)

        return max(0, min(1, score))

    results = await ai.optimize(
        "neural_network",
        evaluate,
        max_iterations=30,
        early_stopping_patience=10
    )

    print(f"   Best score: {results['best_score']:.4f}")
    print(f"   Iterations: {results['iterations']}")
    print(f"   Best config:")
    for key, value in results['best_config'].items():
        print(f"      {key}: {value}")

    # 4. Strategy adaptation
    print("\n4. Strategy Adaptation:")

    ai.register_strategy(
        "fast_inference",
        {"batch_size": 32, "use_cache": True},
        conditions=[lambda ctx: ctx.get("latency_critical", False)]
    )

    ai.register_strategy(
        "high_accuracy",
        {"batch_size": 1, "ensemble": True},
        conditions=[lambda ctx: ctx.get("accuracy_critical", False)]
    )

    ai.register_strategy(
        "balanced",
        {"batch_size": 16, "use_cache": False}
    )

    contexts = [
        {"latency_critical": True, "task": "realtime"},
        {"accuracy_critical": True, "task": "analysis"},
        {"task": "general"}
    ]

    for ctx in contexts:
        strategy = ai.select_strategy(ctx)
        print(f"   Context: {ctx.get('task')} -> Strategy: {strategy.name if strategy else 'None'}")

        # Simulate execution
        if strategy:
            success = random.random() > 0.2
            performance = random.uniform(0.6, 0.9)
            ai.strategy_selector.update(strategy.name, success, performance)

    print("\n   Strategy Ranking:")
    for rank in ai.strategy_selector.get_ranking():
        print(f"      {rank['name']}: score={rank['score']:.3f}, usage={rank['usage']}")

    # 5. Behavior modification
    print("\n5. Behavior Modification:")

    async def logging_behavior(ctx, params):
        level = params.get("level", "INFO")
        return f"Logged at {level}: {ctx.get('message', '')}"

    async def processing_behavior(ctx, params):
        speed = params.get("speed", "normal")
        return f"Processed with {speed} speed"

    ai.register_behavior("logging", logging_behavior, {"level": "INFO"})
    ai.register_behavior("processing", processing_behavior, {"speed": "normal"})

    print("   Registered behaviors: logging, processing")

    # Modify behavior
    ai.modify_behavior("logging", "level", "DEBUG")
    ai.modify_behavior("processing", "speed", "fast")

    print("   Modified: logging.level = DEBUG")
    print("   Modified: processing.speed = fast")

    # Execute behaviors
    result = await ai.behavior_manager.execute(
        "logging",
        {"message": "Test message"}
    )
    print(f"   Executed: {result}")

    # 6. Trigger adaptation
    print("\n6. Triggering Adaptation:")

    result = await ai.adapt(
        AdaptationTrigger.PERFORMANCE_DROP,
        {"current_performance": 0.6},
        evaluate
    )

    print(f"   Trigger: {result.trigger.value}")
    print(f"   Type: {result.adaptation_type.value}")
    print(f"   Before: {result.before_performance:.4f}")
    print(f"   After: {result.after_performance:.4f}")
    print(f"   Improvement: {result.improvement:+.4f}")

    # 7. Status
    print("\n7. System Status:")
    status = ai.get_status()
    for key, value in status.items():
        if isinstance(value, list) and len(value) > 5:
            print(f"   {key}: [{len(value)} items]")
        else:
            print(f"   {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
