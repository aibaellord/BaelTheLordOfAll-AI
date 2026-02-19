"""
🔄 META OPTIMIZER 🔄
====================
Meta-level optimization.

Features:
- Hyperparameter tuning
- Architecture search
- Strategy optimization
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
import uuid
import math
import random


class OptimizationStrategy(Enum):
    """Meta-optimization strategies"""
    GRID_SEARCH = auto()
    RANDOM_SEARCH = auto()
    BAYESIAN = auto()
    EVOLUTIONARY = auto()
    GRADIENT_FREE = auto()
    NEURAL_ARCHITECTURE_SEARCH = auto()


@dataclass
class MetaParameter:
    """A meta-level parameter"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Current value
    value: Any = None

    # Type
    param_type: str = ""  # float, int, categorical, bool

    # Bounds
    min_value: float = 0.0
    max_value: float = 1.0

    # Categorical options
    options: List[Any] = field(default_factory=list)

    # Importance (how much it affects performance)
    importance: float = 0.5

    # History
    value_history: List[Tuple[Any, float]] = field(default_factory=list)

    def sample_random(self) -> Any:
        """Sample random value"""
        if self.param_type == "float":
            return random.uniform(self.min_value, self.max_value)
        elif self.param_type == "int":
            return random.randint(int(self.min_value), int(self.max_value))
        elif self.param_type == "categorical":
            return random.choice(self.options) if self.options else None
        elif self.param_type == "bool":
            return random.choice([True, False])
        return self.value

    def record(self, value: Any, score: float):
        """Record value and its score"""
        self.value_history.append((value, score))


class HyperparameterTuner:
    """
    Hyperparameter optimization.
    """

    def __init__(self):
        self.parameters: Dict[str, MetaParameter] = {}
        self.best_config: Dict[str, Any] = {}
        self.best_score: float = float('-inf')

        # History
        self.trials: List[Dict[str, Any]] = []

        # Strategy
        self.strategy: OptimizationStrategy = OptimizationStrategy.BAYESIAN

        # Settings
        self.n_trials: int = 100

    def add_parameter(self, param: MetaParameter):
        """Add parameter to tune"""
        self.parameters[param.name] = param

    def _sample_config(self) -> Dict[str, Any]:
        """Sample configuration"""
        config = {}
        for name, param in self.parameters.items():
            config[name] = param.sample_random()
        return config

    def _grid_configs(self, n_per_param: int = 5) -> List[Dict[str, Any]]:
        """Generate grid configurations"""
        import itertools

        param_values = {}
        for name, param in self.parameters.items():
            if param.param_type == "float":
                param_values[name] = [
                    param.min_value + i * (param.max_value - param.min_value) / (n_per_param - 1)
                    for i in range(n_per_param)
                ]
            elif param.param_type == "int":
                step = max(1, (int(param.max_value) - int(param.min_value)) // (n_per_param - 1))
                param_values[name] = list(range(int(param.min_value), int(param.max_value) + 1, step))
            elif param.param_type == "categorical":
                param_values[name] = param.options
            elif param.param_type == "bool":
                param_values[name] = [True, False]

        # Cartesian product
        keys = list(param_values.keys())
        values = [param_values[k] for k in keys]

        configs = []
        for combo in itertools.product(*values):
            configs.append(dict(zip(keys, combo)))

        return configs

    def optimize(
        self,
        objective: Callable[[Dict[str, Any]], float],
        n_trials: int = None
    ) -> Dict[str, Any]:
        """Run optimization"""
        n_trials = n_trials or self.n_trials

        if self.strategy == OptimizationStrategy.GRID_SEARCH:
            configs = self._grid_configs()[:n_trials]
        else:
            configs = [self._sample_config() for _ in range(n_trials)]

        for config in configs:
            try:
                score = objective(config)

                self.trials.append({
                    'config': config,
                    'score': score,
                    'timestamp': datetime.now().isoformat()
                })

                # Record in parameters
                for name, value in config.items():
                    if name in self.parameters:
                        self.parameters[name].record(value, score)

                # Update best
                if score > self.best_score:
                    self.best_score = score
                    self.best_config = config.copy()

            except Exception:
                pass

        return self.best_config

    def get_importance(self) -> Dict[str, float]:
        """Estimate parameter importance"""
        importance = {}

        for name, param in self.parameters.items():
            if len(param.value_history) < 2:
                importance[name] = 0.0
                continue

            # Calculate variance in scores for different values
            values = [v for v, s in param.value_history]
            scores = [s for v, s in param.value_history]

            if len(set(values)) == 1:
                importance[name] = 0.0
            else:
                # Correlation between value and score
                score_variance = max(scores) - min(scores)
                importance[name] = min(1.0, score_variance)

        return importance


@dataclass
class ArchitectureConfig:
    """Neural architecture configuration"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Layers
    n_layers: int = 3
    layer_sizes: List[int] = field(default_factory=lambda: [64, 128, 64])

    # Activation
    activation: str = "relu"

    # Regularization
    dropout: float = 0.1

    # Connections
    skip_connections: bool = False
    attention: bool = False

    # Performance
    score: float = 0.0
    params_count: int = 0


class ArchitectureSearcher:
    """
    Neural architecture search.
    """

    def __init__(self):
        self.architectures: List[ArchitectureConfig] = []
        self.best_architecture: Optional[ArchitectureConfig] = None

        # Search space
        self.min_layers: int = 1
        self.max_layers: int = 10
        self.layer_size_options: List[int] = [32, 64, 128, 256, 512]
        self.activation_options: List[str] = ["relu", "gelu", "tanh", "silu"]

    def random_architecture(self) -> ArchitectureConfig:
        """Generate random architecture"""
        n_layers = random.randint(self.min_layers, self.max_layers)

        return ArchitectureConfig(
            n_layers=n_layers,
            layer_sizes=[random.choice(self.layer_size_options) for _ in range(n_layers)],
            activation=random.choice(self.activation_options),
            dropout=random.uniform(0.0, 0.5),
            skip_connections=random.choice([True, False]),
            attention=random.choice([True, False])
        )

    def mutate(self, arch: ArchitectureConfig) -> ArchitectureConfig:
        """Mutate architecture"""
        new_arch = ArchitectureConfig(
            n_layers=arch.n_layers,
            layer_sizes=arch.layer_sizes.copy(),
            activation=arch.activation,
            dropout=arch.dropout,
            skip_connections=arch.skip_connections,
            attention=arch.attention
        )

        # Random mutation
        mutation_type = random.choice([
            "add_layer", "remove_layer", "change_size",
            "change_activation", "change_dropout", "toggle_skip", "toggle_attention"
        ])

        if mutation_type == "add_layer" and new_arch.n_layers < self.max_layers:
            new_arch.n_layers += 1
            new_arch.layer_sizes.append(random.choice(self.layer_size_options))
        elif mutation_type == "remove_layer" and new_arch.n_layers > self.min_layers:
            new_arch.n_layers -= 1
            new_arch.layer_sizes.pop()
        elif mutation_type == "change_size" and new_arch.layer_sizes:
            idx = random.randint(0, len(new_arch.layer_sizes) - 1)
            new_arch.layer_sizes[idx] = random.choice(self.layer_size_options)
        elif mutation_type == "change_activation":
            new_arch.activation = random.choice(self.activation_options)
        elif mutation_type == "change_dropout":
            new_arch.dropout = random.uniform(0.0, 0.5)
        elif mutation_type == "toggle_skip":
            new_arch.skip_connections = not new_arch.skip_connections
        elif mutation_type == "toggle_attention":
            new_arch.attention = not new_arch.attention

        return new_arch

    def search(
        self,
        evaluate: Callable[[ArchitectureConfig], float],
        n_generations: int = 50,
        population_size: int = 20
    ) -> ArchitectureConfig:
        """Evolutionary architecture search"""
        # Initialize population
        population = [self.random_architecture() for _ in range(population_size)]

        for gen in range(n_generations):
            # Evaluate
            for arch in population:
                if arch.score == 0.0:
                    try:
                        arch.score = evaluate(arch)
                    except Exception:
                        arch.score = float('-inf')

            # Sort by score
            population.sort(key=lambda a: a.score, reverse=True)

            # Update best
            if not self.best_architecture or population[0].score > self.best_architecture.score:
                self.best_architecture = population[0]

            # Selection (top 50%)
            survivors = population[:population_size // 2]

            # Reproduction
            children = []
            while len(children) < population_size - len(survivors):
                parent = random.choice(survivors)
                child = self.mutate(parent)
                children.append(child)

            population = survivors + children

            self.architectures.extend(population)

        return self.best_architecture


class MetaOptimizer:
    """
    Complete meta-optimization system.
    """

    def __init__(self):
        self.hyperparam_tuner = HyperparameterTuner()
        self.arch_searcher = ArchitectureSearcher()

        # Meta-meta parameters
        self.learning_rate_schedule: str = "cosine"
        self.warmup_steps: int = 100

        # Optimization history
        self.optimization_runs: List[Dict[str, Any]] = []

    def optimize_hyperparameters(
        self,
        objective: Callable[[Dict[str, Any]], float],
        param_space: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Optimize hyperparameters"""
        # Define parameters
        for name, spec in param_space.items():
            param = MetaParameter(
                name=name,
                param_type=spec.get('type', 'float'),
                min_value=spec.get('min', 0.0),
                max_value=spec.get('max', 1.0),
                options=spec.get('options', [])
            )
            self.hyperparam_tuner.add_parameter(param)

        # Run optimization
        best = self.hyperparam_tuner.optimize(objective)

        self.optimization_runs.append({
            'type': 'hyperparameter',
            'best_config': best,
            'best_score': self.hyperparam_tuner.best_score,
            'n_trials': len(self.hyperparam_tuner.trials),
            'timestamp': datetime.now().isoformat()
        })

        return best

    def optimize_architecture(
        self,
        evaluate: Callable[[ArchitectureConfig], float]
    ) -> ArchitectureConfig:
        """Optimize architecture"""
        best = self.arch_searcher.search(evaluate)

        self.optimization_runs.append({
            'type': 'architecture',
            'best_config': {
                'n_layers': best.n_layers,
                'layer_sizes': best.layer_sizes,
                'activation': best.activation
            },
            'best_score': best.score,
            'n_architectures': len(self.arch_searcher.architectures),
            'timestamp': datetime.now().isoformat()
        })

        return best

    def get_optimization_report(self) -> Dict[str, Any]:
        """Get optimization report"""
        return {
            'total_runs': len(self.optimization_runs),
            'hyperparam_runs': len([r for r in self.optimization_runs if r['type'] == 'hyperparameter']),
            'architecture_runs': len([r for r in self.optimization_runs if r['type'] == 'architecture']),
            'best_hyperparam_score': max(
                (r['best_score'] for r in self.optimization_runs if r['type'] == 'hyperparameter'),
                default=0
            ),
            'best_architecture_score': max(
                (r['best_score'] for r in self.optimization_runs if r['type'] == 'architecture'),
                default=0
            ),
            'param_importance': self.hyperparam_tuner.get_importance()
        }


# Export all
__all__ = [
    'OptimizationStrategy',
    'MetaParameter',
    'ArchitectureConfig',
    'HyperparameterTuner',
    'ArchitectureSearcher',
    'MetaOptimizer',
]
