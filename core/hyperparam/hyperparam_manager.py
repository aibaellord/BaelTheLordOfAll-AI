#!/usr/bin/env python3
"""
BAEL - Hyperparameter Manager
Comprehensive hyperparameter search and optimization.

Features:
- Grid search
- Random search
- Bayesian optimization
- Early stopping
- Results tracking
- Best configuration selection
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SearchStrategy(Enum):
    """Hyperparameter search strategies."""
    GRID = "grid"
    RANDOM = "random"
    BAYESIAN = "bayesian"
    EVOLUTIONARY = "evolutionary"
    SUCCESSIVE_HALVING = "successive_halving"


class ParameterType(Enum):
    """Parameter types."""
    INTEGER = "integer"
    FLOAT = "float"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    LOG_FLOAT = "log_float"
    LOG_INTEGER = "log_integer"


class OptimizationDirection(Enum):
    """Optimization direction."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class TrialStatus(Enum):
    """Trial status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PRUNED = "pruned"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ParameterSpace:
    """Definition of a parameter space."""
    name: str = ""
    param_type: ParameterType = ParameterType.FLOAT
    low: Optional[float] = None
    high: Optional[float] = None
    choices: Optional[List[Any]] = None
    default: Optional[Any] = None
    step: Optional[float] = None

    def sample(self) -> Any:
        """Sample a value from this space."""
        if self.param_type == ParameterType.CATEGORICAL:
            return random.choice(self.choices)

        elif self.param_type == ParameterType.BOOLEAN:
            return random.choice([True, False])

        elif self.param_type == ParameterType.INTEGER:
            if self.step:
                values = list(range(int(self.low), int(self.high) + 1, int(self.step)))
                return random.choice(values)
            return random.randint(int(self.low), int(self.high))

        elif self.param_type == ParameterType.FLOAT:
            return random.uniform(self.low, self.high)

        elif self.param_type == ParameterType.LOG_FLOAT:
            log_low = math.log(self.low)
            log_high = math.log(self.high)
            return math.exp(random.uniform(log_low, log_high))

        elif self.param_type == ParameterType.LOG_INTEGER:
            log_low = math.log(self.low)
            log_high = math.log(self.high)
            return int(math.exp(random.uniform(log_low, log_high)))

        return self.default

    def grid_values(self, n_points: int = 10) -> List[Any]:
        """Get grid values for this parameter."""
        if self.param_type == ParameterType.CATEGORICAL:
            return list(self.choices)

        elif self.param_type == ParameterType.BOOLEAN:
            return [True, False]

        elif self.param_type == ParameterType.INTEGER:
            if self.step:
                return list(range(int(self.low), int(self.high) + 1, int(self.step)))
            step = max(1, (int(self.high) - int(self.low)) // n_points)
            return list(range(int(self.low), int(self.high) + 1, step))

        elif self.param_type == ParameterType.FLOAT:
            step = (self.high - self.low) / (n_points - 1)
            return [self.low + i * step for i in range(n_points)]

        elif self.param_type == ParameterType.LOG_FLOAT:
            log_low = math.log(self.low)
            log_high = math.log(self.high)
            step = (log_high - log_low) / (n_points - 1)
            return [math.exp(log_low + i * step) for i in range(n_points)]

        elif self.param_type == ParameterType.LOG_INTEGER:
            log_low = math.log(self.low)
            log_high = math.log(self.high)
            step = (log_high - log_low) / (n_points - 1)
            return [int(math.exp(log_low + i * step)) for i in range(n_points)]

        return [self.default]


@dataclass
class SearchSpace:
    """Collection of parameter spaces."""
    parameters: Dict[str, ParameterSpace] = field(default_factory=dict)

    def add(
        self,
        name: str,
        param_type: ParameterType,
        low: Optional[float] = None,
        high: Optional[float] = None,
        choices: Optional[List[Any]] = None,
        default: Optional[Any] = None,
        step: Optional[float] = None
    ) -> "SearchSpace":
        """Add a parameter to the space."""
        self.parameters[name] = ParameterSpace(
            name=name,
            param_type=param_type,
            low=low,
            high=high,
            choices=choices,
            default=default,
            step=step
        )
        return self

    def sample(self) -> Dict[str, Any]:
        """Sample a configuration from the space."""
        return {name: param.sample() for name, param in self.parameters.items()}

    def add_float(
        self,
        name: str,
        low: float,
        high: float,
        default: Optional[float] = None
    ) -> "SearchSpace":
        """Add a float parameter."""
        return self.add(name, ParameterType.FLOAT, low=low, high=high, default=default)

    def add_int(
        self,
        name: str,
        low: int,
        high: int,
        step: Optional[int] = None,
        default: Optional[int] = None
    ) -> "SearchSpace":
        """Add an integer parameter."""
        return self.add(name, ParameterType.INTEGER, low=low, high=high, step=step, default=default)

    def add_categorical(
        self,
        name: str,
        choices: List[Any],
        default: Optional[Any] = None
    ) -> "SearchSpace":
        """Add a categorical parameter."""
        return self.add(name, ParameterType.CATEGORICAL, choices=choices, default=default)

    def add_log_float(
        self,
        name: str,
        low: float,
        high: float,
        default: Optional[float] = None
    ) -> "SearchSpace":
        """Add a log-scale float parameter."""
        return self.add(name, ParameterType.LOG_FLOAT, low=low, high=high, default=default)


@dataclass
class Trial:
    """A single hyperparameter trial."""
    trial_id: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    status: TrialStatus = TrialStatus.PENDING
    objective: Optional[float] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    iteration: int = 0

    def __post_init__(self):
        if not self.trial_id:
            self.trial_id = str(uuid.uuid4())[:8]

    def start(self) -> None:
        """Mark trial as started."""
        self.status = TrialStatus.RUNNING
        self.start_time = datetime.now()

    def complete(self, objective: float, metrics: Optional[Dict[str, float]] = None) -> None:
        """Mark trial as completed."""
        self.status = TrialStatus.COMPLETED
        self.objective = objective
        self.metrics = metrics or {}
        self.end_time = datetime.now()

        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def fail(self, error: Optional[str] = None) -> None:
        """Mark trial as failed."""
        self.status = TrialStatus.FAILED
        self.end_time = datetime.now()

        if error:
            self.metrics["error"] = error

    def prune(self) -> None:
        """Mark trial as pruned."""
        self.status = TrialStatus.PRUNED
        self.end_time = datetime.now()


@dataclass
class SearchConfig:
    """Search configuration."""
    strategy: SearchStrategy = SearchStrategy.RANDOM
    direction: OptimizationDirection = OptimizationDirection.MINIMIZE
    n_trials: int = 100
    timeout: Optional[float] = None
    early_stopping: bool = True
    patience: int = 10
    min_improvement: float = 1e-4
    seed: Optional[int] = None


@dataclass
class SearchResult:
    """Search result."""
    best_trial: Optional[Trial] = None
    best_config: Dict[str, Any] = field(default_factory=dict)
    best_objective: Optional[float] = None
    all_trials: List[Trial] = field(default_factory=list)
    n_completed: int = 0
    n_failed: int = 0
    n_pruned: int = 0
    total_time: float = 0.0


# =============================================================================
# BASE SEARCHER
# =============================================================================

class BaseSearcher(ABC):
    """Base class for hyperparameter searchers."""

    def __init__(self, search_space: SearchSpace, config: SearchConfig):
        self._search_space = search_space
        self._config = config
        self._trials: List[Trial] = []
        self._best_trial: Optional[Trial] = None

        if config.seed is not None:
            random.seed(config.seed)

    @abstractmethod
    def suggest(self) -> Dict[str, Any]:
        """Suggest the next configuration to try."""
        pass

    def observe(self, trial: Trial) -> None:
        """Record a completed trial."""
        self._trials.append(trial)

        if trial.status != TrialStatus.COMPLETED:
            return

        if self._best_trial is None:
            self._best_trial = trial
        elif self._config.direction == OptimizationDirection.MINIMIZE:
            if trial.objective < self._best_trial.objective:
                self._best_trial = trial
        else:
            if trial.objective > self._best_trial.objective:
                self._best_trial = trial

    def should_stop(self) -> bool:
        """Check if search should stop early."""
        if not self._config.early_stopping:
            return False

        if len(self._trials) < self._config.patience:
            return False

        recent = [t for t in self._trials[-self._config.patience:] if t.status == TrialStatus.COMPLETED]

        if not recent or not self._best_trial:
            return False

        for trial in recent:
            diff = abs(trial.objective - self._best_trial.objective)
            if diff > self._config.min_improvement:
                return False

        return True


# =============================================================================
# SEARCHER IMPLEMENTATIONS
# =============================================================================

class GridSearcher(BaseSearcher):
    """Grid search over hyperparameters."""

    def __init__(self, search_space: SearchSpace, config: SearchConfig):
        super().__init__(search_space, config)
        self._grid = self._build_grid()
        self._index = 0

    def _build_grid(self) -> List[Dict[str, Any]]:
        """Build the parameter grid."""
        from itertools import product

        param_names = list(self._search_space.parameters.keys())
        param_values = [
            self._search_space.parameters[name].grid_values()
            for name in param_names
        ]

        grid = []
        for values in product(*param_values):
            config = dict(zip(param_names, values))
            grid.append(config)

        return grid

    def suggest(self) -> Dict[str, Any]:
        """Get next grid configuration."""
        if self._index >= len(self._grid):
            self._index = 0

        config = self._grid[self._index]
        self._index += 1
        return config


class RandomSearcher(BaseSearcher):
    """Random search over hyperparameters."""

    def suggest(self) -> Dict[str, Any]:
        """Sample a random configuration."""
        return self._search_space.sample()


class BayesianSearcher(BaseSearcher):
    """
    Simplified Bayesian optimization searcher.
    Uses a basic surrogate model approach.
    """

    def __init__(self, search_space: SearchSpace, config: SearchConfig):
        super().__init__(search_space, config)
        self._n_initial = 10
        self._exploration_rate = 0.3

    def suggest(self) -> Dict[str, Any]:
        """Suggest configuration using Bayesian approach."""
        if len(self._trials) < self._n_initial:
            return self._search_space.sample()

        if random.random() < self._exploration_rate:
            return self._search_space.sample()

        return self._exploit()

    def _exploit(self) -> Dict[str, Any]:
        """Exploit based on best observed trials."""
        completed = [t for t in self._trials if t.status == TrialStatus.COMPLETED]

        if not completed:
            return self._search_space.sample()

        sorted_trials = sorted(
            completed,
            key=lambda t: t.objective,
            reverse=(self._config.direction == OptimizationDirection.MAXIMIZE)
        )

        top_k = min(5, len(sorted_trials))
        top_trials = sorted_trials[:top_k]

        config = {}
        for name, param in self._search_space.parameters.items():
            values = [t.config[name] for t in top_trials]

            if param.param_type == ParameterType.CATEGORICAL:
                config[name] = random.choice(values)

            elif param.param_type == ParameterType.BOOLEAN:
                config[name] = random.choice(values)

            elif param.param_type in (ParameterType.INTEGER, ParameterType.LOG_INTEGER):
                mean = sum(values) / len(values)
                std = max(1, (param.high - param.low) * 0.1)
                value = int(random.gauss(mean, std))
                value = max(int(param.low), min(int(param.high), value))
                config[name] = value

            else:
                mean = sum(values) / len(values)
                std = (param.high - param.low) * 0.1
                value = random.gauss(mean, std)
                value = max(param.low, min(param.high, value))
                config[name] = value

        return config


class EvolutionarySearcher(BaseSearcher):
    """Evolutionary algorithm based searcher."""

    def __init__(self, search_space: SearchSpace, config: SearchConfig):
        super().__init__(search_space, config)
        self._population_size = 20
        self._mutation_rate = 0.2
        self._crossover_rate = 0.7

    def suggest(self) -> Dict[str, Any]:
        """Suggest configuration using evolutionary strategy."""
        if len(self._trials) < self._population_size:
            return self._search_space.sample()

        completed = [t for t in self._trials if t.status == TrialStatus.COMPLETED]

        if len(completed) < 2:
            return self._search_space.sample()

        sorted_trials = sorted(
            completed,
            key=lambda t: t.objective,
            reverse=(self._config.direction == OptimizationDirection.MAXIMIZE)
        )

        parent1 = random.choice(sorted_trials[:max(2, len(sorted_trials) // 2)])
        parent2 = random.choice(sorted_trials[:max(2, len(sorted_trials) // 2)])

        child = self._crossover(parent1.config, parent2.config)
        child = self._mutate(child)

        return child

    def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
        """Perform crossover between two parents."""
        child = {}

        for name in parent1:
            if random.random() < self._crossover_rate:
                child[name] = parent1[name]
            else:
                child[name] = parent2[name]

        return child

    def _mutate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate a configuration."""
        mutated = config.copy()

        for name, param in self._search_space.parameters.items():
            if random.random() < self._mutation_rate:
                mutated[name] = param.sample()

        return mutated


# =============================================================================
# HYPERPARAMETER MANAGER
# =============================================================================

class HyperparameterManager:
    """
    Hyperparameter Manager for BAEL.

    Comprehensive hyperparameter search and optimization.
    """

    def __init__(self):
        self._searchers: Dict[str, BaseSearcher] = {}
        self._results: Dict[str, SearchResult] = {}

    def create_search_space(self) -> SearchSpace:
        """Create a new search space."""
        return SearchSpace()

    def create_searcher(
        self,
        name: str,
        search_space: SearchSpace,
        strategy: SearchStrategy = SearchStrategy.RANDOM,
        direction: OptimizationDirection = OptimizationDirection.MINIMIZE,
        n_trials: int = 100,
        **kwargs
    ) -> BaseSearcher:
        """Create a searcher."""
        config = SearchConfig(
            strategy=strategy,
            direction=direction,
            n_trials=n_trials,
            **kwargs
        )

        if strategy == SearchStrategy.GRID:
            searcher = GridSearcher(search_space, config)
        elif strategy == SearchStrategy.RANDOM:
            searcher = RandomSearcher(search_space, config)
        elif strategy == SearchStrategy.BAYESIAN:
            searcher = BayesianSearcher(search_space, config)
        elif strategy == SearchStrategy.EVOLUTIONARY:
            searcher = EvolutionarySearcher(search_space, config)
        else:
            searcher = RandomSearcher(search_space, config)

        self._searchers[name] = searcher
        return searcher

    async def run_search(
        self,
        name: str,
        objective_fn: Callable[[Dict[str, Any]], float],
        search_space: SearchSpace,
        strategy: SearchStrategy = SearchStrategy.RANDOM,
        direction: OptimizationDirection = OptimizationDirection.MINIMIZE,
        n_trials: int = 100,
        **kwargs
    ) -> SearchResult:
        """Run a hyperparameter search."""
        searcher = self.create_searcher(
            name, search_space, strategy, direction, n_trials, **kwargs
        )

        result = SearchResult()
        start_time = time.time()

        for i in range(n_trials):
            if searcher.should_stop():
                break

            config = searcher.suggest()

            trial = Trial(config=config, iteration=i)
            trial.start()

            try:
                objective = objective_fn(config)
                trial.complete(objective)

                if result.best_trial is None:
                    result.best_trial = trial
                    result.best_config = config
                    result.best_objective = objective
                elif direction == OptimizationDirection.MINIMIZE:
                    if objective < result.best_objective:
                        result.best_trial = trial
                        result.best_config = config
                        result.best_objective = objective
                else:
                    if objective > result.best_objective:
                        result.best_trial = trial
                        result.best_config = config
                        result.best_objective = objective

                result.n_completed += 1

            except Exception as e:
                trial.fail(str(e))
                result.n_failed += 1

            result.all_trials.append(trial)
            searcher.observe(trial)

        result.total_time = time.time() - start_time
        self._results[name] = result

        return result

    def get_result(self, name: str) -> Optional[SearchResult]:
        """Get search result."""
        return self._results.get(name)

    def summary(self) -> Dict[str, Any]:
        """Get manager summary."""
        return {
            "active_searchers": len(self._searchers),
            "completed_searches": len(self._results),
            "searches": {
                name: {
                    "n_trials": len(result.all_trials),
                    "best_objective": result.best_objective
                }
                for name, result in self._results.items()
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Hyperparameter Manager."""
    print("=" * 70)
    print("BAEL - HYPERPARAMETER MANAGER DEMO")
    print("Hyperparameter Search and Optimization")
    print("=" * 70)
    print()

    manager = HyperparameterManager()

    # 1. Define Search Space
    print("1. DEFINE SEARCH SPACE:")
    print("-" * 40)

    space = manager.create_search_space()
    space.add_log_float("learning_rate", 1e-5, 1e-1)
    space.add_int("batch_size", 16, 128, step=16)
    space.add_int("hidden_units", 64, 512, step=64)
    space.add_float("dropout", 0.1, 0.5)
    space.add_categorical("optimizer", ["sgd", "adam", "adamw"])

    for name, param in space.parameters.items():
        print(f"   {name}: {param.param_type.value}")
    print()

    # 2. Sample from Space
    print("2. SAMPLE CONFIGURATIONS:")
    print("-" * 40)

    for i in range(3):
        sample = space.sample()
        print(f"   Sample {i+1}:")
        for k, v in sample.items():
            if isinstance(v, float):
                print(f"      {k}: {v:.6f}")
            else:
                print(f"      {k}: {v}")
    print()

    # 3. Define Objective Function
    print("3. OBJECTIVE FUNCTION:")
    print("-" * 40)

    def objective(config: Dict[str, Any]) -> float:
        """Simulated objective function."""
        lr = config["learning_rate"]
        bs = config["batch_size"]
        hidden = config["hidden_units"]
        dropout = config["dropout"]
        optimizer = config["optimizer"]

        opt_bonus = {"adam": 0.1, "adamw": 0.15, "sgd": 0.0}

        score = (
            -math.log10(lr) * 0.3 +
            (bs / 128) * 0.2 +
            (hidden / 512) * 0.3 +
            (1 - dropout) * 0.1 +
            opt_bonus[optimizer]
        )

        noise = random.gauss(0, 0.05)

        return score + noise

    print("   Defined: score = f(lr, batch_size, hidden, dropout, optimizer)")
    print()

    # 4. Run Random Search
    print("4. RUN RANDOM SEARCH:")
    print("-" * 40)

    result = await manager.run_search(
        name="random_search",
        objective_fn=objective,
        search_space=space,
        strategy=SearchStrategy.RANDOM,
        direction=OptimizationDirection.MAXIMIZE,
        n_trials=20
    )

    print(f"   Trials completed: {result.n_completed}")
    print(f"   Best objective: {result.best_objective:.4f}")
    print(f"   Best config:")
    for k, v in result.best_config.items():
        if isinstance(v, float):
            print(f"      {k}: {v:.6f}")
        else:
            print(f"      {k}: {v}")
    print(f"   Total time: {result.total_time:.2f}s")
    print()

    # 5. Run Bayesian Search
    print("5. RUN BAYESIAN SEARCH:")
    print("-" * 40)

    result2 = await manager.run_search(
        name="bayesian_search",
        objective_fn=objective,
        search_space=space,
        strategy=SearchStrategy.BAYESIAN,
        direction=OptimizationDirection.MAXIMIZE,
        n_trials=20
    )

    print(f"   Trials completed: {result2.n_completed}")
    print(f"   Best objective: {result2.best_objective:.4f}")
    print(f"   Best config:")
    for k, v in result2.best_config.items():
        if isinstance(v, float):
            print(f"      {k}: {v:.6f}")
        else:
            print(f"      {k}: {v}")
    print()

    # 6. Run Evolutionary Search
    print("6. RUN EVOLUTIONARY SEARCH:")
    print("-" * 40)

    result3 = await manager.run_search(
        name="evolutionary_search",
        objective_fn=objective,
        search_space=space,
        strategy=SearchStrategy.EVOLUTIONARY,
        direction=OptimizationDirection.MAXIMIZE,
        n_trials=30
    )

    print(f"   Trials completed: {result3.n_completed}")
    print(f"   Best objective: {result3.best_objective:.4f}")
    print()

    # 7. Compare Results
    print("7. COMPARE RESULTS:")
    print("-" * 40)

    strategies = ["random_search", "bayesian_search", "evolutionary_search"]

    for name in strategies:
        r = manager.get_result(name)
        print(f"   {name}: best={r.best_objective:.4f}")
    print()

    # 8. Grid Search
    print("8. GRID SEARCH (SMALL SPACE):")
    print("-" * 40)

    small_space = SearchSpace()
    small_space.add_categorical("optimizer", ["adam", "sgd"])
    small_space.add_int("batch_size", 32, 64, step=32)

    grid_result = await manager.run_search(
        name="grid_search",
        objective_fn=objective,
        search_space=small_space,
        strategy=SearchStrategy.GRID,
        direction=OptimizationDirection.MAXIMIZE,
        n_trials=100
    )

    print(f"   Trials completed: {grid_result.n_completed}")
    print(f"   Best config: {grid_result.best_config}")
    print()

    # 9. Manager Summary
    print("9. MANAGER SUMMARY:")
    print("-" * 40)

    summary = manager.summary()

    print(f"   Completed searches: {summary['completed_searches']}")
    for name, data in summary['searches'].items():
        print(f"      {name}: {data['n_trials']} trials, best={data['best_objective']:.4f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Hyperparameter Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
