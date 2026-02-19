"""
BAEL Hyperparameter Optimizer
==============================

Automated hyperparameter optimization.
Finds optimal training configurations.

Features:
- Multiple search algorithms
- Search space definition
- Trial management
- Pruning strategies
- Results analysis
"""

import hashlib
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class SearchAlgorithm(Enum):
    """Hyperparameter search algorithms."""
    GRID = "grid"
    RANDOM = "random"
    BAYESIAN = "bayesian"
    TPE = "tpe"  # Tree-structured Parzen Estimator
    HYPERBAND = "hyperband"


class ParameterType(Enum):
    """Types of hyperparameters."""
    FLOAT = "float"
    INT = "int"
    CATEGORICAL = "categorical"
    LOG_FLOAT = "log_float"


@dataclass
class Parameter:
    """A hyperparameter definition."""
    name: str
    param_type: ParameterType

    # Range (for numeric)
    low: Optional[float] = None
    high: Optional[float] = None

    # Choices (for categorical)
    choices: Optional[List[Any]] = None

    # Step (for grid search)
    step: Optional[float] = None

    def sample(self) -> Any:
        """Sample a random value."""
        if self.param_type == ParameterType.FLOAT:
            return random.uniform(self.low, self.high)
        elif self.param_type == ParameterType.LOG_FLOAT:
            log_low = math.log(self.low)
            log_high = math.log(self.high)
            return math.exp(random.uniform(log_low, log_high))
        elif self.param_type == ParameterType.INT:
            return random.randint(int(self.low), int(self.high))
        elif self.param_type == ParameterType.CATEGORICAL:
            return random.choice(self.choices)
        return None

    def grid_values(self, num_points: int = 5) -> List[Any]:
        """Generate grid values."""
        if self.param_type == ParameterType.CATEGORICAL:
            return list(self.choices)

        if self.step:
            values = []
            current = self.low
            while current <= self.high:
                values.append(current if self.param_type == ParameterType.FLOAT else int(current))
                current += self.step
            return values

        if self.param_type == ParameterType.INT:
            return list(range(int(self.low), int(self.high) + 1))

        if self.param_type == ParameterType.LOG_FLOAT:
            log_low = math.log(self.low)
            log_high = math.log(self.high)
            return [math.exp(log_low + i * (log_high - log_low) / (num_points - 1))
                   for i in range(num_points)]

        return [self.low + i * (self.high - self.low) / (num_points - 1)
               for i in range(num_points)]


@dataclass
class SearchSpace:
    """Search space for hyperparameter optimization."""
    name: str
    parameters: Dict[str, Parameter] = field(default_factory=dict)

    def add_float(
        self,
        name: str,
        low: float,
        high: float,
        log: bool = False,
    ) -> "SearchSpace":
        """Add a float parameter."""
        self.parameters[name] = Parameter(
            name=name,
            param_type=ParameterType.LOG_FLOAT if log else ParameterType.FLOAT,
            low=low,
            high=high,
        )
        return self

    def add_int(
        self,
        name: str,
        low: int,
        high: int,
    ) -> "SearchSpace":
        """Add an integer parameter."""
        self.parameters[name] = Parameter(
            name=name,
            param_type=ParameterType.INT,
            low=low,
            high=high,
        )
        return self

    def add_categorical(
        self,
        name: str,
        choices: List[Any],
    ) -> "SearchSpace":
        """Add a categorical parameter."""
        self.parameters[name] = Parameter(
            name=name,
            param_type=ParameterType.CATEGORICAL,
            choices=choices,
        )
        return self

    def sample(self) -> Dict[str, Any]:
        """Sample random configuration."""
        return {name: param.sample() for name, param in self.parameters.items()}


@dataclass
class Trial:
    """A single trial in the optimization."""
    id: str
    number: int

    # Configuration
    params: Dict[str, Any] = field(default_factory=dict)

    # Results
    value: Optional[float] = None  # Objective value
    intermediate_values: Dict[int, float] = field(default_factory=dict)

    # Status
    state: str = "running"  # "running", "completed", "pruned", "failed"

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Metadata
    user_attrs: Dict[str, Any] = field(default_factory=dict)

    def report(self, value: float, step: int) -> None:
        """Report intermediate value."""
        self.intermediate_values[step] = value

    def complete(self, value: float) -> None:
        """Mark trial as complete."""
        self.value = value
        self.state = "completed"
        self.completed_at = datetime.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def prune(self) -> None:
        """Mark trial as pruned."""
        self.state = "pruned"
        self.completed_at = datetime.now()


@dataclass
class OptimizationResult:
    """Result of hyperparameter optimization."""
    study_id: str

    # Best result
    best_params: Dict[str, Any] = field(default_factory=dict)
    best_value: float = float('inf')
    best_trial_id: str = ""

    # All trials
    trials: List[Trial] = field(default_factory=list)

    # Stats
    total_trials: int = 0
    completed_trials: int = 0
    pruned_trials: int = 0

    # Timing
    total_time_seconds: float = 0.0

    def get_best_trial(self) -> Optional[Trial]:
        """Get the best trial."""
        completed = [t for t in self.trials if t.state == "completed"]
        if not completed:
            return None
        return min(completed, key=lambda t: t.value or float('inf'))


class HyperparameterOptimizer:
    """
    Hyperparameter optimizer for BAEL.

    Finds optimal training configurations.
    """

    def __init__(
        self,
        search_space: SearchSpace,
        algorithm: SearchAlgorithm = SearchAlgorithm.RANDOM,
        n_trials: int = 20,
        direction: str = "minimize",  # "minimize" or "maximize"
    ):
        self.search_space = search_space
        self.algorithm = algorithm
        self.n_trials = n_trials
        self.direction = direction

        # Trials
        self._trials: List[Trial] = []
        self._trial_counter = 0

        # Bayesian optimization state
        self._observations: List[Tuple[Dict[str, Any], float]] = []

        # Stats
        self.stats = {
            "studies_run": 0,
            "total_trials": 0,
        }

    def optimize(
        self,
        objective: Callable[[Dict[str, Any]], float],
        callbacks: Optional[List[Callable[[Trial], None]]] = None,
    ) -> OptimizationResult:
        """
        Run optimization.

        Args:
            objective: Function that takes params and returns metric
            callbacks: Optional callbacks per trial

        Returns:
            Optimization result
        """
        study_id = hashlib.md5(
            f"{self.search_space.name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        result = OptimizationResult(study_id=study_id)
        start_time = datetime.now()

        # Generate trial configs
        if self.algorithm == SearchAlgorithm.GRID:
            configs = self._generate_grid_configs()
        else:
            configs = [self.search_space.sample() for _ in range(self.n_trials)]

        # Run trials
        for i, params in enumerate(configs):
            trial = self._create_trial(params)

            try:
                # Run objective
                value = objective(params)

                trial.complete(value)
                result.completed_trials += 1

                # Update best
                is_better = (
                    value < result.best_value if self.direction == "minimize"
                    else value > result.best_value
                )

                if is_better:
                    result.best_value = value
                    result.best_params = params.copy()
                    result.best_trial_id = trial.id

                # Store for Bayesian
                self._observations.append((params, value))

            except Exception as e:
                trial.state = "failed"
                logger.warning(f"Trial {trial.id} failed: {e}")

            result.trials.append(trial)
            result.total_trials += 1

            # Callbacks
            if callbacks:
                for callback in callbacks:
                    callback(trial)

            logger.info(
                f"Trial {i+1}/{len(configs)}: "
                f"value={trial.value}, best={result.best_value}"
            )

        result.total_time_seconds = (datetime.now() - start_time).total_seconds()

        self.stats["studies_run"] += 1
        self.stats["total_trials"] += result.total_trials

        return result

    def _create_trial(self, params: Dict[str, Any]) -> Trial:
        """Create a new trial."""
        self._trial_counter += 1

        trial_id = hashlib.md5(
            f"trial:{self._trial_counter}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        trial = Trial(
            id=trial_id,
            number=self._trial_counter,
            params=params,
        )

        self._trials.append(trial)

        return trial

    def _generate_grid_configs(self) -> List[Dict[str, Any]]:
        """Generate all grid configurations."""
        from itertools import product

        param_values = {}
        for name, param in self.search_space.parameters.items():
            param_values[name] = param.grid_values()

        configs = []
        keys = list(param_values.keys())

        for values in product(*param_values.values()):
            configs.append(dict(zip(keys, values)))

        return configs

    def suggest_next(self) -> Dict[str, Any]:
        """Suggest next configuration (for Bayesian)."""
        if self.algorithm == SearchAlgorithm.RANDOM:
            return self.search_space.sample()

        if len(self._observations) < 5:
            return self.search_space.sample()

        # Simple Bayesian-like: sample around best with noise
        best_idx = (
            min(range(len(self._observations)), key=lambda i: self._observations[i][1])
            if self.direction == "minimize"
            else max(range(len(self._observations)), key=lambda i: self._observations[i][1])
        )
        best_params = self._observations[best_idx][0]

        new_params = {}
        for name, param in self.search_space.parameters.items():
            if param.param_type == ParameterType.CATEGORICAL:
                # Sometimes explore, sometimes exploit
                if random.random() < 0.3:
                    new_params[name] = param.sample()
                else:
                    new_params[name] = best_params[name]
            else:
                # Add noise to best
                base_value = best_params[name]
                if param.param_type == ParameterType.LOG_FLOAT:
                    noise = random.gauss(0, 0.2)
                    new_value = base_value * math.exp(noise)
                else:
                    range_size = param.high - param.low
                    noise = random.gauss(0, range_size * 0.1)
                    new_value = base_value + noise

                new_value = max(param.low, min(param.high, new_value))
                if param.param_type == ParameterType.INT:
                    new_value = int(round(new_value))

                new_params[name] = new_value

        return new_params

    def get_importance(self) -> Dict[str, float]:
        """Calculate parameter importance."""
        if not self._observations:
            return {}

        importance = {}

        for name in self.search_space.parameters:
            # Simple correlation-based importance
            values = [obs[0][name] for obs in self._observations]
            scores = [obs[1] for obs in self._observations]

            if len(set(values)) <= 1:
                importance[name] = 0.0
                continue

            # Convert categorical to numeric
            if isinstance(values[0], str):
                unique = list(set(values))
                values = [unique.index(v) for v in values]

            # Calculate correlation
            n = len(values)
            mean_v = sum(values) / n
            mean_s = sum(scores) / n

            cov = sum((v - mean_v) * (s - mean_s) for v, s in zip(values, scores)) / n
            std_v = math.sqrt(sum((v - mean_v) ** 2 for v in values) / n)
            std_s = math.sqrt(sum((s - mean_s) ** 2 for s in scores) / n)

            if std_v > 0 and std_s > 0:
                importance[name] = abs(cov / (std_v * std_s))
            else:
                importance[name] = 0.0

        # Normalize
        total = sum(importance.values())
        if total > 0:
            importance = {k: v / total for k, v in importance.items()}

        return importance

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            **self.stats,
            "algorithm": self.algorithm.value,
            "n_trials": self.n_trials,
            "observations": len(self._observations),
        }


def demo():
    """Demonstrate hyperparameter optimizer."""
    print("=" * 60)
    print("BAEL Hyperparameter Optimizer Demo")
    print("=" * 60)

    # Define search space
    space = SearchSpace("training_params")
    space.add_float("learning_rate", 1e-6, 1e-3, log=True)
    space.add_int("batch_size", 4, 32)
    space.add_categorical("optimizer", ["adam", "adamw", "sgd"])
    space.add_float("weight_decay", 0.0, 0.1)

    print("\nSearch space:")
    for name, param in space.parameters.items():
        print(f"  {name}: {param.param_type.value}")

    # Sample configurations
    print("\nSample configurations:")
    for i in range(3):
        sample = space.sample()
        print(f"  {i+1}: {sample}")

    # Create optimizer
    optimizer = HyperparameterOptimizer(
        search_space=space,
        algorithm=SearchAlgorithm.RANDOM,
        n_trials=10,
        direction="minimize",
    )

    # Objective function (simulated)
    def objective(params: Dict[str, Any]) -> float:
        # Simulate training loss
        lr = params["learning_rate"]
        batch = params["batch_size"]
        wd = params["weight_decay"]

        # Best around lr=1e-4, batch=16, wd=0.01
        loss = (
            abs(math.log(lr) - math.log(1e-4)) * 0.5 +
            abs(batch - 16) * 0.01 +
            abs(wd - 0.01) * 2 +
            random.uniform(0, 0.1)
        )

        return loss

    # Run optimization
    print("\nRunning optimization...")
    result = optimizer.optimize(objective)

    print(f"\n{'=' * 50}")
    print("Optimization Complete!")
    print(f"  Total trials: {result.total_trials}")
    print(f"  Best value: {result.best_value:.4f}")
    print(f"  Best params: {result.best_params}")
    print(f"  Time: {result.total_time_seconds:.2f}s")

    # Parameter importance
    print("\nParameter importance:")
    importance = optimizer.get_importance()
    for name, imp in sorted(importance.items(), key=lambda x: -x[1]):
        bar = "█" * int(imp * 20)
        print(f"  {name}: {imp:.3f} {bar}")

    print(f"\nStats: {optimizer.get_stats()}")


if __name__ == "__main__":
    demo()
