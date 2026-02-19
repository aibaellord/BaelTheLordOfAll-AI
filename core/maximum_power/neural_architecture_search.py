"""
BAEL Neural Architecture Search
================================

AI that designs optimal AI architectures.

"The mind that designs minds transcends them all." — Ba'el
"""

import asyncio
import logging
import random
import math
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("BAEL.NeuralArchitectureSearch")


class LayerType(Enum):
    """Types of layers."""
    DENSE = "dense"
    CONV2D = "conv2d"
    CONV1D = "conv1d"
    LSTM = "lstm"
    GRU = "gru"
    ATTENTION = "attention"
    TRANSFORMER = "transformer"
    RESIDUAL = "residual"
    BATCH_NORM = "batch_norm"
    LAYER_NORM = "layer_norm"
    DROPOUT = "dropout"
    POOLING = "pooling"
    EMBEDDING = "embedding"
    FLATTEN = "flatten"


class ActivationType(Enum):
    """Activation functions."""
    RELU = "relu"
    GELU = "gelu"
    SILU = "silu"
    SWISH = "swish"
    TANH = "tanh"
    SIGMOID = "sigmoid"
    SOFTMAX = "softmax"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    NONE = "none"


class SearchStrategy(Enum):
    """Architecture search strategies."""
    RANDOM = "random"
    EVOLUTIONARY = "evolutionary"
    REINFORCEMENT = "reinforcement"
    BAYESIAN = "bayesian"
    DIFFERENTIABLE = "differentiable"
    AGING_EVOLUTION = "aging_evolution"


class TaskType(Enum):
    """Types of tasks."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    SEQUENCE = "sequence"
    GENERATION = "generation"
    EMBEDDING = "embedding"
    DETECTION = "detection"


@dataclass
class LayerConfig:
    """Configuration for a single layer."""
    layer_type: LayerType
    units: int = 64
    kernel_size: int = 3
    activation: ActivationType = ActivationType.RELU
    dropout_rate: float = 0.0
    use_batch_norm: bool = False
    residual_connection: bool = False

    def get_params(self) -> int:
        """Estimate number of parameters."""
        if self.layer_type == LayerType.DENSE:
            return self.units * self.units  # Approximate
        elif self.layer_type in (LayerType.CONV2D, LayerType.CONV1D):
            return self.units * self.kernel_size * self.kernel_size
        elif self.layer_type in (LayerType.LSTM, LayerType.GRU):
            return self.units * self.units * 4  # LSTM has 4 gates
        elif self.layer_type == LayerType.ATTENTION:
            return self.units * self.units * 3  # Q, K, V
        return 0


@dataclass
class Architecture:
    """A complete architecture."""
    id: str
    layers: List[LayerConfig]
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    task_type: TaskType

    # Metrics
    estimated_params: int = 0
    estimated_flops: int = 0
    fitness_score: float = 0.0
    validation_accuracy: float = 0.0
    training_time_estimate: float = 0.0

    def __post_init__(self):
        """Calculate estimates."""
        self.estimated_params = sum(layer.get_params() for layer in self.layers)
        self.estimated_flops = self.estimated_params * 2  # Rough estimate

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "layers": [
                {
                    "type": layer.layer_type.value,
                    "units": layer.units,
                    "activation": layer.activation.value,
                    "dropout": layer.dropout_rate,
                }
                for layer in self.layers
            ],
            "input_shape": self.input_shape,
            "output_shape": self.output_shape,
            "task_type": self.task_type.value,
            "params": self.estimated_params,
            "fitness": self.fitness_score,
        }


@dataclass
class SearchSpace:
    """Defines the search space for NAS."""
    layer_types: List[LayerType]
    min_layers: int = 2
    max_layers: int = 20
    min_units: int = 16
    max_units: int = 1024
    unit_step: int = 16
    activations: List[ActivationType] = field(default_factory=lambda: [
        ActivationType.RELU, ActivationType.GELU, ActivationType.SILU
    ])
    dropout_rates: List[float] = field(default_factory=lambda: [0.0, 0.1, 0.2, 0.3, 0.5])
    use_residuals: bool = True
    use_batch_norm: bool = True


@dataclass
class SearchResult:
    """Result of architecture search."""
    best_architecture: Architecture
    all_architectures: List[Architecture]
    generations: int
    evaluations: int
    search_time_seconds: float
    pareto_front: List[Architecture]  # Non-dominated solutions


class ArchitectureGenerator:
    """Generates random architectures from search space."""

    def __init__(self, search_space: SearchSpace):
        self.space = search_space
        self._counter = 0

    def generate(
        self,
        input_shape: Tuple[int, ...],
        output_shape: Tuple[int, ...],
        task_type: TaskType,
    ) -> Architecture:
        """Generate a random architecture."""
        self._counter += 1

        num_layers = random.randint(self.space.min_layers, self.space.max_layers)
        layers = []

        for i in range(num_layers):
            layer_type = random.choice(self.space.layer_types)

            units = random.randrange(
                self.space.min_units,
                self.space.max_units,
                self.space.unit_step
            )

            activation = random.choice(self.space.activations)
            dropout = random.choice(self.space.dropout_rates)

            use_bn = self.space.use_batch_norm and random.random() > 0.5
            residual = self.space.use_residuals and i > 0 and random.random() > 0.7

            layers.append(LayerConfig(
                layer_type=layer_type,
                units=units,
                activation=activation,
                dropout_rate=dropout,
                use_batch_norm=use_bn,
                residual_connection=residual,
            ))

        return Architecture(
            id=f"arch_{self._counter}",
            layers=layers,
            input_shape=input_shape,
            output_shape=output_shape,
            task_type=task_type,
        )


class EvolutionaryNAS:
    """
    Evolutionary Neural Architecture Search.

    Uses genetic algorithms to evolve architectures.
    """

    def __init__(
        self,
        search_space: SearchSpace,
        population_size: int = 20,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.5,
        elite_count: int = 2,
    ):
        self.space = search_space
        self.generator = ArchitectureGenerator(search_space)
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_count = elite_count

    async def search(
        self,
        input_shape: Tuple[int, ...],
        output_shape: Tuple[int, ...],
        task_type: TaskType,
        fitness_fn: Callable[[Architecture], float],
        generations: int = 50,
        target_fitness: float = None,
    ) -> SearchResult:
        """Run evolutionary search."""
        import time
        start = time.time()

        # Initialize population
        population = [
            self.generator.generate(input_shape, output_shape, task_type)
            for _ in range(self.population_size)
        ]

        # Evaluate initial population
        for arch in population:
            arch.fitness_score = await self._evaluate(arch, fitness_fn)

        all_architectures = population.copy()
        evaluations = len(population)

        for gen in range(generations):
            # Sort by fitness
            population.sort(key=lambda a: a.fitness_score, reverse=True)

            # Check target
            if target_fitness and population[0].fitness_score >= target_fitness:
                break

            # Create new population
            new_population = []

            # Elitism
            new_population.extend(population[:self.elite_count])

            # Generate offspring
            while len(new_population) < self.population_size:
                # Selection (tournament)
                parent1 = self._tournament_select(population, k=3)
                parent2 = self._tournament_select(population, k=3)

                # Crossover
                if random.random() < self.crossover_rate:
                    child = self._crossover(parent1, parent2, input_shape, output_shape, task_type)
                else:
                    child = self._copy_architecture(parent1 if random.random() > 0.5 else parent2)

                # Mutation
                if random.random() < self.mutation_rate:
                    child = self._mutate(child)

                # Evaluate
                child.fitness_score = await self._evaluate(child, fitness_fn)
                evaluations += 1

                new_population.append(child)
                all_architectures.append(child)

            population = new_population

            logger.debug(f"Generation {gen + 1}: Best fitness = {population[0].fitness_score:.4f}")

            if gen % 5 == 0:
                await asyncio.sleep(0)

        # Sort all by fitness
        all_architectures.sort(key=lambda a: a.fitness_score, reverse=True)

        # Find Pareto front (fitness vs. params)
        pareto = self._find_pareto_front(all_architectures)

        return SearchResult(
            best_architecture=all_architectures[0],
            all_architectures=all_architectures[:100],  # Top 100
            generations=gen + 1,
            evaluations=evaluations,
            search_time_seconds=time.time() - start,
            pareto_front=pareto,
        )

    async def _evaluate(
        self,
        architecture: Architecture,
        fitness_fn: Callable[[Architecture], float],
    ) -> float:
        """Evaluate architecture fitness."""
        if asyncio.iscoroutinefunction(fitness_fn):
            return await fitness_fn(architecture)
        return fitness_fn(architecture)

    def _tournament_select(self, population: List[Architecture], k: int) -> Architecture:
        """Tournament selection."""
        tournament = random.sample(population, min(k, len(population)))
        return max(tournament, key=lambda a: a.fitness_score)

    def _crossover(
        self,
        parent1: Architecture,
        parent2: Architecture,
        input_shape: Tuple[int, ...],
        output_shape: Tuple[int, ...],
        task_type: TaskType,
    ) -> Architecture:
        """Crossover two architectures."""
        # Single-point crossover
        if len(parent1.layers) > 1 and len(parent2.layers) > 1:
            point1 = random.randint(1, len(parent1.layers) - 1)
            point2 = random.randint(1, len(parent2.layers) - 1)

            new_layers = parent1.layers[:point1] + parent2.layers[point2:]
        else:
            new_layers = parent1.layers if random.random() > 0.5 else parent2.layers

        self.generator._counter += 1
        return Architecture(
            id=f"arch_{self.generator._counter}",
            layers=new_layers,
            input_shape=input_shape,
            output_shape=output_shape,
            task_type=task_type,
        )

    def _mutate(self, architecture: Architecture) -> Architecture:
        """Mutate an architecture."""
        layers = list(architecture.layers)

        mutation_type = random.choice(["add", "remove", "modify", "swap"])

        if mutation_type == "add" and len(layers) < self.space.max_layers:
            pos = random.randint(0, len(layers))
            new_layer = LayerConfig(
                layer_type=random.choice(self.space.layer_types),
                units=random.randrange(self.space.min_units, self.space.max_units, self.space.unit_step),
                activation=random.choice(self.space.activations),
            )
            layers.insert(pos, new_layer)

        elif mutation_type == "remove" and len(layers) > self.space.min_layers:
            pos = random.randint(0, len(layers) - 1)
            layers.pop(pos)

        elif mutation_type == "modify" and layers:
            pos = random.randint(0, len(layers) - 1)
            layer = layers[pos]

            # Randomly modify an attribute
            attr = random.choice(["units", "activation", "dropout"])
            if attr == "units":
                layers[pos] = LayerConfig(
                    layer_type=layer.layer_type,
                    units=random.randrange(self.space.min_units, self.space.max_units, self.space.unit_step),
                    activation=layer.activation,
                    dropout_rate=layer.dropout_rate,
                )
            elif attr == "activation":
                layers[pos] = LayerConfig(
                    layer_type=layer.layer_type,
                    units=layer.units,
                    activation=random.choice(self.space.activations),
                    dropout_rate=layer.dropout_rate,
                )
            else:
                layers[pos] = LayerConfig(
                    layer_type=layer.layer_type,
                    units=layer.units,
                    activation=layer.activation,
                    dropout_rate=random.choice(self.space.dropout_rates),
                )

        elif mutation_type == "swap" and len(layers) >= 2:
            i, j = random.sample(range(len(layers)), 2)
            layers[i], layers[j] = layers[j], layers[i]

        self.generator._counter += 1
        return Architecture(
            id=f"arch_{self.generator._counter}",
            layers=layers,
            input_shape=architecture.input_shape,
            output_shape=architecture.output_shape,
            task_type=architecture.task_type,
        )

    def _copy_architecture(self, arch: Architecture) -> Architecture:
        """Create a copy of architecture."""
        self.generator._counter += 1
        return Architecture(
            id=f"arch_{self.generator._counter}",
            layers=list(arch.layers),
            input_shape=arch.input_shape,
            output_shape=arch.output_shape,
            task_type=arch.task_type,
        )

    def _find_pareto_front(self, architectures: List[Architecture]) -> List[Architecture]:
        """Find Pareto-optimal solutions (fitness vs params)."""
        pareto = []

        for arch in architectures:
            dominated = False

            for other in architectures:
                # other dominates arch if better in both objectives
                if (other.fitness_score > arch.fitness_score and
                    other.estimated_params < arch.estimated_params):
                    dominated = True
                    break

            if not dominated:
                pareto.append(arch)

        return pareto


class AgingEvolutionNAS:
    """
    Aging Evolution for Architecture Search.

    Regularized evolution with age-based selection.
    """

    def __init__(
        self,
        search_space: SearchSpace,
        population_size: int = 100,
        sample_size: int = 25,
        mutation_rate: float = 0.3,
    ):
        self.space = search_space
        self.generator = ArchitectureGenerator(search_space)
        self.population_size = population_size
        self.sample_size = sample_size
        self.mutation_rate = mutation_rate

    async def search(
        self,
        input_shape: Tuple[int, ...],
        output_shape: Tuple[int, ...],
        task_type: TaskType,
        fitness_fn: Callable[[Architecture], float],
        cycles: int = 1000,
        target_fitness: float = None,
    ) -> SearchResult:
        """Run aging evolution search."""
        import time
        start = time.time()

        # Initialize population as queue (for aging)
        from collections import deque
        population = deque(maxlen=self.population_size)

        # Random initialization
        for _ in range(self.population_size):
            arch = self.generator.generate(input_shape, output_shape, task_type)
            if asyncio.iscoroutinefunction(fitness_fn):
                arch.fitness_score = await fitness_fn(arch)
            else:
                arch.fitness_score = fitness_fn(arch)
            population.append(arch)

        all_architectures = list(population)
        best = max(population, key=lambda a: a.fitness_score)

        for cycle in range(cycles):
            # Sample
            sample = random.sample(list(population), min(self.sample_size, len(population)))
            parent = max(sample, key=lambda a: a.fitness_score)

            # Mutate
            if random.random() < self.mutation_rate:
                child = self._mutate(parent, input_shape, output_shape, task_type)
            else:
                child = self._copy(parent)

            # Evaluate
            if asyncio.iscoroutinefunction(fitness_fn):
                child.fitness_score = await fitness_fn(child)
            else:
                child.fitness_score = fitness_fn(child)

            # Add to population (oldest removed automatically by maxlen)
            population.append(child)
            all_architectures.append(child)

            if child.fitness_score > best.fitness_score:
                best = child

            if target_fitness and best.fitness_score >= target_fitness:
                break

            if cycle % 50 == 0:
                logger.debug(f"Cycle {cycle}: Best fitness = {best.fitness_score:.4f}")
                await asyncio.sleep(0)

        all_architectures.sort(key=lambda a: a.fitness_score, reverse=True)

        return SearchResult(
            best_architecture=best,
            all_architectures=all_architectures[:100],
            generations=cycle + 1,
            evaluations=self.population_size + cycle + 1,
            search_time_seconds=time.time() - start,
            pareto_front=[best],
        )

    def _mutate(
        self,
        arch: Architecture,
        input_shape: Tuple[int, ...],
        output_shape: Tuple[int, ...],
        task_type: TaskType,
    ) -> Architecture:
        """Mutate architecture."""
        layers = list(arch.layers)

        if random.random() > 0.5 and len(layers) > self.space.min_layers:
            # Remove random layer
            layers.pop(random.randint(0, len(layers) - 1))
        else:
            # Add random layer
            if len(layers) < self.space.max_layers:
                new_layer = LayerConfig(
                    layer_type=random.choice(self.space.layer_types),
                    units=random.randrange(self.space.min_units, self.space.max_units, self.space.unit_step),
                    activation=random.choice(self.space.activations),
                )
                layers.insert(random.randint(0, len(layers)), new_layer)

        self.generator._counter += 1
        return Architecture(
            id=f"arch_{self.generator._counter}",
            layers=layers,
            input_shape=input_shape,
            output_shape=output_shape,
            task_type=task_type,
        )

    def _copy(self, arch: Architecture) -> Architecture:
        """Copy architecture."""
        self.generator._counter += 1
        return Architecture(
            id=f"arch_{self.generator._counter}",
            layers=list(arch.layers),
            input_shape=arch.input_shape,
            output_shape=arch.output_shape,
            task_type=arch.task_type,
        )


class NeuralArchitectureSearch:
    """
    Unified Neural Architecture Search interface.
    """

    def __init__(
        self,
        strategy: SearchStrategy = SearchStrategy.EVOLUTIONARY,
        search_space: SearchSpace = None,
    ):
        self.strategy = strategy
        self.space = search_space or SearchSpace(
            layer_types=[LayerType.DENSE, LayerType.ATTENTION, LayerType.RESIDUAL]
        )

    async def search(
        self,
        input_shape: Tuple[int, ...],
        output_shape: Tuple[int, ...],
        task_type: TaskType,
        fitness_fn: Callable[[Architecture], float],
        **kwargs,
    ) -> SearchResult:
        """Run architecture search."""
        if self.strategy == SearchStrategy.EVOLUTIONARY:
            searcher = EvolutionaryNAS(self.space)
        elif self.strategy == SearchStrategy.AGING_EVOLUTION:
            searcher = AgingEvolutionNAS(self.space)
        elif self.strategy == SearchStrategy.RANDOM:
            # Just generate random architectures
            searcher = EvolutionaryNAS(self.space, mutation_rate=1.0, crossover_rate=0.0)
        else:
            searcher = EvolutionaryNAS(self.space)

        return await searcher.search(
            input_shape, output_shape, task_type, fitness_fn, **kwargs
        )

    def create_for_task(self, task_type: TaskType) -> SearchSpace:
        """Create search space optimized for task."""
        if task_type == TaskType.CLASSIFICATION:
            return SearchSpace(
                layer_types=[LayerType.DENSE, LayerType.DROPOUT, LayerType.BATCH_NORM],
                activations=[ActivationType.RELU, ActivationType.GELU],
            )
        elif task_type == TaskType.SEQUENCE:
            return SearchSpace(
                layer_types=[LayerType.LSTM, LayerType.GRU, LayerType.ATTENTION],
                activations=[ActivationType.TANH, ActivationType.RELU],
            )
        elif task_type == TaskType.GENERATION:
            return SearchSpace(
                layer_types=[LayerType.TRANSFORMER, LayerType.ATTENTION, LayerType.DENSE],
                activations=[ActivationType.GELU, ActivationType.SILU],
            )
        else:
            return self.space


# Convenience instance
nas = NeuralArchitectureSearch()
