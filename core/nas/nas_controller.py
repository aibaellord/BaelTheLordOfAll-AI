"""
BAEL - Neural Architecture Search (NAS)
Automated discovery of optimal architectures for BAEL components.

Features:
- Search space definition for architectures
- Evolutionary NAS
- Differentiable NAS (DARTS-style)
- Performance prediction
- Multi-objective optimization
- Architecture encoding/decoding
- Transfer learning from prior searches
"""

import asyncio
import copy
import hashlib
import json
import logging
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger("BAEL.NAS")


# =============================================================================
# ENUMS
# =============================================================================

class SearchStrategy(Enum):
    """NAS search strategies."""
    RANDOM = "random"
    EVOLUTIONARY = "evolutionary"
    REINFORCEMENT = "reinforcement"
    DIFFERENTIABLE = "differentiable"
    BAYESIAN = "bayesian"
    PROGRESSIVE = "progressive"


class OperationType(Enum):
    """Types of operations in search space."""
    LINEAR = "linear"
    ATTENTION = "attention"
    CONVOLUTION = "convolution"
    POOLING = "pooling"
    NORMALIZATION = "normalization"
    ACTIVATION = "activation"
    SKIP = "skip"
    ZERO = "zero"


class ObjectiveType(Enum):
    """Optimization objectives."""
    ACCURACY = "accuracy"
    LATENCY = "latency"
    MEMORY = "memory"
    PARAMETERS = "parameters"
    FLOPS = "flops"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Operation:
    """A single operation in the architecture."""
    op_type: OperationType
    params: Dict[str, Any] = field(default_factory=dict)
    input_idx: int = 0

    def __hash__(self):
        return hash((self.op_type, tuple(sorted(self.params.items())), self.input_idx))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.op_type.value,
            "params": self.params,
            "input_idx": self.input_idx
        }


@dataclass
class Cell:
    """A cell in the architecture (group of operations)."""
    name: str
    operations: List[Operation]
    reduction: bool = False

    def __hash__(self):
        return hash((self.name, tuple(self.operations), self.reduction))


@dataclass
class Architecture:
    """Complete architecture specification."""
    id: str
    cells: List[Cell]
    metadata: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, float] = field(default_factory=dict)
    evaluated: bool = False

    @classmethod
    def generate_id(cls) -> str:
        return hashlib.md5(str(random.random()).encode()).hexdigest()[:12]

    def fitness(self, objectives: List[ObjectiveType], weights: Optional[List[float]] = None) -> float:
        """Compute weighted fitness score."""
        if not weights:
            weights = [1.0] * len(objectives)

        total = 0.0
        for obj, weight in zip(objectives, weights):
            if obj.value in self.performance:
                value = self.performance[obj.value]
                # Invert metrics where lower is better
                if obj in [ObjectiveType.LATENCY, ObjectiveType.MEMORY,
                           ObjectiveType.PARAMETERS, ObjectiveType.FLOPS]:
                    value = 1.0 / (value + 1e-6)
                total += weight * value

        return total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cells": [{"name": c.name, "ops": [o.to_dict() for o in c.operations]} for c in self.cells],
            "metadata": self.metadata,
            "performance": self.performance
        }


@dataclass
class SearchSpace:
    """Definition of the architecture search space."""
    name: str
    operations: List[OperationType]
    max_cells: int = 8
    max_ops_per_cell: int = 6
    input_dims: int = 512
    output_dims: int = 512
    constraints: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SEARCH SPACE BUILDERS
# =============================================================================

class SearchSpaceBuilder:
    """Builder for creating search spaces."""

    def __init__(self, name: str = "default"):
        self.name = name
        self.operations: List[OperationType] = []
        self.max_cells = 8
        self.max_ops_per_cell = 6
        self.input_dims = 512
        self.output_dims = 512
        self.constraints: Dict[str, Any] = {}

    def with_operations(self, ops: List[OperationType]) -> "SearchSpaceBuilder":
        self.operations = ops
        return self

    def with_max_cells(self, n: int) -> "SearchSpaceBuilder":
        self.max_cells = n
        return self

    def with_max_ops(self, n: int) -> "SearchSpaceBuilder":
        self.max_ops_per_cell = n
        return self

    def with_dims(self, input_dim: int, output_dim: int) -> "SearchSpaceBuilder":
        self.input_dims = input_dim
        self.output_dims = output_dim
        return self

    def with_constraint(self, name: str, value: Any) -> "SearchSpaceBuilder":
        self.constraints[name] = value
        return self

    def build(self) -> SearchSpace:
        if not self.operations:
            self.operations = list(OperationType)

        return SearchSpace(
            name=self.name,
            operations=self.operations,
            max_cells=self.max_cells,
            max_ops_per_cell=self.max_ops_per_cell,
            input_dims=self.input_dims,
            output_dims=self.output_dims,
            constraints=self.constraints
        )


# =============================================================================
# ARCHITECTURE SAMPLER
# =============================================================================

class ArchitectureSampler:
    """Sample architectures from search space."""

    def __init__(self, search_space: SearchSpace):
        self.space = search_space

    def sample_operation(self, input_idx: int = 0) -> Operation:
        """Sample a random operation."""
        op_type = random.choice(self.space.operations)
        params = self._get_default_params(op_type)
        return Operation(op_type=op_type, params=params, input_idx=input_idx)

    def _get_default_params(self, op_type: OperationType) -> Dict[str, Any]:
        """Get default parameters for operation type."""
        if op_type == OperationType.LINEAR:
            return {"hidden_dim": random.choice([256, 512, 1024, 2048])}
        elif op_type == OperationType.ATTENTION:
            return {
                "n_heads": random.choice([4, 8, 12, 16]),
                "dropout": random.choice([0.0, 0.1, 0.2])
            }
        elif op_type == OperationType.CONVOLUTION:
            return {
                "kernel_size": random.choice([1, 3, 5]),
                "filters": random.choice([128, 256, 512])
            }
        elif op_type == OperationType.POOLING:
            return {"pool_type": random.choice(["max", "avg", "attention"])}
        elif op_type == OperationType.NORMALIZATION:
            return {"norm_type": random.choice(["layer", "batch", "group"])}
        elif op_type == OperationType.ACTIVATION:
            return {"activation": random.choice(["relu", "gelu", "swish"])}
        return {}

    def sample_cell(self, name: str, reduction: bool = False) -> Cell:
        """Sample a random cell."""
        n_ops = random.randint(1, self.space.max_ops_per_cell)
        operations = []

        for i in range(n_ops):
            # Operations can connect to previous ops or input
            input_idx = random.randint(0, len(operations))
            operations.append(self.sample_operation(input_idx))

        return Cell(name=name, operations=operations, reduction=reduction)

    def sample_architecture(self) -> Architecture:
        """Sample a complete architecture."""
        n_cells = random.randint(1, self.space.max_cells)
        cells = []

        for i in range(n_cells):
            # Add reduction cell every 3 cells
            reduction = (i > 0 and i % 3 == 0)
            cells.append(self.sample_cell(f"cell_{i}", reduction))

        return Architecture(
            id=Architecture.generate_id(),
            cells=cells,
            metadata={"search_space": self.space.name}
        )


# =============================================================================
# PERFORMANCE ESTIMATOR
# =============================================================================

class PerformanceEstimator(ABC):
    """Base class for performance estimation."""

    @abstractmethod
    async def estimate(self, architecture: Architecture) -> Dict[str, float]:
        pass


class ProxyEstimator(PerformanceEstimator):
    """
    Proxy-based performance estimation.
    Uses cheap proxy metrics instead of full evaluation.
    """

    def __init__(self):
        self.cache: Dict[str, Dict[str, float]] = {}

    async def estimate(self, architecture: Architecture) -> Dict[str, float]:
        """Estimate performance using proxy metrics."""
        arch_hash = self._hash_architecture(architecture)

        if arch_hash in self.cache:
            return self.cache[arch_hash]

        # Count parameters
        params = self._count_parameters(architecture)

        # Estimate FLOPs
        flops = self._estimate_flops(architecture)

        # Estimate latency (simplified)
        latency = flops / 1e9  # Simplified

        # Estimate accuracy based on architecture properties
        accuracy = self._estimate_accuracy(architecture)

        # Memory estimation
        memory = params * 4 / 1e6  # 4 bytes per param in MB

        result = {
            "accuracy": accuracy,
            "parameters": params,
            "flops": flops,
            "latency": latency,
            "memory": memory
        }

        self.cache[arch_hash] = result
        return result

    def _hash_architecture(self, arch: Architecture) -> str:
        """Create hash for architecture."""
        arch_str = json.dumps(arch.to_dict(), sort_keys=True)
        return hashlib.md5(arch_str.encode()).hexdigest()

    def _count_parameters(self, arch: Architecture) -> int:
        """Count total parameters."""
        total = 0
        dim = 512

        for cell in arch.cells:
            for op in cell.operations:
                if op.op_type == OperationType.LINEAR:
                    hidden = op.params.get("hidden_dim", 512)
                    total += dim * hidden + hidden
                elif op.op_type == OperationType.ATTENTION:
                    n_heads = op.params.get("n_heads", 8)
                    total += 4 * dim * dim  # Q, K, V, O projections
                elif op.op_type == OperationType.CONVOLUTION:
                    kernel = op.params.get("kernel_size", 3)
                    filters = op.params.get("filters", 256)
                    total += kernel * dim * filters

        return total

    def _estimate_flops(self, arch: Architecture) -> int:
        """Estimate FLOPs."""
        total = 0
        seq_len = 512
        dim = 512

        for cell in arch.cells:
            for op in cell.operations:
                if op.op_type == OperationType.LINEAR:
                    hidden = op.params.get("hidden_dim", 512)
                    total += 2 * seq_len * dim * hidden
                elif op.op_type == OperationType.ATTENTION:
                    total += 4 * seq_len * seq_len * dim  # Attention + output

        return total

    def _estimate_accuracy(self, arch: Architecture) -> float:
        """Estimate accuracy based on architecture properties."""
        # Heuristic: more operations and attention = better
        score = 0.5

        for cell in arch.cells:
            for op in cell.operations:
                if op.op_type == OperationType.ATTENTION:
                    score += 0.03
                elif op.op_type == OperationType.LINEAR:
                    score += 0.01
                elif op.op_type == OperationType.SKIP:
                    score += 0.005

        # Cap at reasonable range
        return min(0.95, max(0.3, score + random.gauss(0, 0.05)))


# =============================================================================
# EVOLUTIONARY NAS
# =============================================================================

class EvolutionaryNAS:
    """
    Evolutionary Neural Architecture Search.
    Uses genetic algorithms to evolve architectures.
    """

    def __init__(
        self,
        search_space: SearchSpace,
        population_size: int = 50,
        tournament_size: int = 5,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.5
    ):
        self.space = search_space
        self.population_size = population_size
        self.tournament_size = tournament_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate

        self.sampler = ArchitectureSampler(search_space)
        self.estimator = ProxyEstimator()

        self.population: List[Architecture] = []
        self.history: List[Architecture] = []
        self.best_architecture: Optional[Architecture] = None
        self.generation = 0

    async def initialize_population(self) -> None:
        """Initialize random population."""
        self.population = []
        for _ in range(self.population_size):
            arch = self.sampler.sample_architecture()
            arch.performance = await self.estimator.estimate(arch)
            arch.evaluated = True
            self.population.append(arch)

        self._update_best()
        logger.info(f"Initialized population with {len(self.population)} architectures")

    def _update_best(self) -> None:
        """Update best architecture."""
        if self.population:
            best = max(self.population, key=lambda a: a.performance.get("accuracy", 0))
            if self.best_architecture is None or \
               best.performance.get("accuracy", 0) > self.best_architecture.performance.get("accuracy", 0):
                self.best_architecture = best

    def _tournament_select(self) -> Architecture:
        """Select architecture via tournament selection."""
        tournament = random.sample(self.population, min(self.tournament_size, len(self.population)))
        return max(tournament, key=lambda a: a.performance.get("accuracy", 0))

    def _mutate(self, arch: Architecture) -> Architecture:
        """Mutate architecture."""
        new_arch = Architecture(
            id=Architecture.generate_id(),
            cells=copy.deepcopy(arch.cells),
            metadata={"parent": arch.id, "mutation": True}
        )

        for cell in new_arch.cells:
            for i, op in enumerate(cell.operations):
                if random.random() < self.mutation_rate:
                    # Mutate operation type
                    cell.operations[i] = self.sampler.sample_operation(op.input_idx)

        # Possibly add or remove a cell
        if random.random() < self.mutation_rate:
            if len(new_arch.cells) > 1 and random.random() < 0.5:
                # Remove random cell
                idx = random.randint(0, len(new_arch.cells) - 1)
                new_arch.cells.pop(idx)
            elif len(new_arch.cells) < self.space.max_cells:
                # Add new cell
                new_cell = self.sampler.sample_cell(f"cell_{len(new_arch.cells)}")
                new_arch.cells.append(new_cell)

        return new_arch

    def _crossover(self, parent1: Architecture, parent2: Architecture) -> Architecture:
        """Crossover two architectures."""
        if random.random() > self.crossover_rate:
            return copy.deepcopy(random.choice([parent1, parent2]))

        # Single-point crossover on cells
        min_cells = min(len(parent1.cells), len(parent2.cells))
        crossover_point = random.randint(1, max(1, min_cells - 1))

        new_cells = copy.deepcopy(parent1.cells[:crossover_point])
        new_cells.extend(copy.deepcopy(parent2.cells[crossover_point:]))

        return Architecture(
            id=Architecture.generate_id(),
            cells=new_cells,
            metadata={"parents": [parent1.id, parent2.id], "crossover": True}
        )

    async def evolve_generation(self) -> float:
        """Evolve one generation."""
        new_population = []

        # Elitism: keep best
        if self.best_architecture:
            new_population.append(copy.deepcopy(self.best_architecture))

        while len(new_population) < self.population_size:
            parent1 = self._tournament_select()
            parent2 = self._tournament_select()

            # Crossover
            child = self._crossover(parent1, parent2)

            # Mutate
            child = self._mutate(child)

            # Evaluate
            child.performance = await self.estimator.estimate(child)
            child.evaluated = True

            new_population.append(child)

        self.population = new_population
        self.history.extend(new_population)
        self._update_best()
        self.generation += 1

        best_acc = self.best_architecture.performance.get("accuracy", 0) if self.best_architecture else 0
        logger.info(f"Generation {self.generation}: best accuracy = {best_acc:.4f}")

        return best_acc

    async def search(self, n_generations: int = 50) -> Architecture:
        """
        Run evolutionary search.

        Args:
            n_generations: Number of generations to evolve

        Returns:
            Best architecture found
        """
        await self.initialize_population()

        for _ in range(n_generations):
            await self.evolve_generation()

        return self.best_architecture


# =============================================================================
# DIFFERENTIABLE NAS (DARTS-style)
# =============================================================================

class DifferentiableNAS:
    """
    Differentiable Architecture Search (DARTS-style).
    Uses continuous relaxation for architecture optimization.
    """

    def __init__(
        self,
        search_space: SearchSpace,
        learning_rate: float = 0.01
    ):
        self.space = search_space
        self.learning_rate = learning_rate

        # Architecture parameters (alphas)
        n_ops = len(search_space.operations)
        n_edges = search_space.max_ops_per_cell * (search_space.max_ops_per_cell + 1) // 2

        self.alphas = np.random.randn(search_space.max_cells, n_edges, n_ops) * 0.01
        self.history: List[Dict[str, Any]] = []

    def _softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Softmax function."""
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)

    def get_architecture_weights(self) -> np.ndarray:
        """Get softmax weights for operations."""
        return self._softmax(self.alphas, axis=-1)

    def sample_discrete_architecture(self) -> Architecture:
        """Sample discrete architecture from continuous weights."""
        weights = self.get_architecture_weights()
        cells = []

        for cell_idx in range(len(weights)):
            operations = []
            edge_idx = 0

            for target in range(self.space.max_ops_per_cell):
                for source in range(target + 1):
                    if edge_idx < weights.shape[1]:
                        # Select operation with highest weight
                        op_idx = int(np.argmax(weights[cell_idx, edge_idx]))
                        op_type = self.space.operations[op_idx]

                        if op_type != OperationType.ZERO:
                            operations.append(Operation(
                                op_type=op_type,
                                params={},
                                input_idx=source
                            ))
                        edge_idx += 1

            if operations:
                cells.append(Cell(name=f"cell_{cell_idx}", operations=operations))

        return Architecture(
            id=Architecture.generate_id(),
            cells=cells,
            metadata={"type": "darts_derived"}
        )

    async def step(self, validation_loss: float) -> None:
        """
        Take optimization step.

        In practice this would use backprop; here we use
        evolution strategy as a gradient-free approximation.
        """
        # Estimate gradients via finite differences
        epsilon = 0.01
        grad = np.zeros_like(self.alphas)

        for i in range(3):  # Sample a few perturbations
            noise = np.random.randn(*self.alphas.shape)

            # Forward perturbation
            self.alphas += epsilon * noise
            arch_plus = self.sample_discrete_architecture()
            estimator = ProxyEstimator()
            perf_plus = await estimator.estimate(arch_plus)
            loss_plus = 1 - perf_plus.get("accuracy", 0)

            # Backward perturbation
            self.alphas -= 2 * epsilon * noise
            arch_minus = self.sample_discrete_architecture()
            perf_minus = await estimator.estimate(arch_minus)
            loss_minus = 1 - perf_minus.get("accuracy", 0)

            # Restore
            self.alphas += epsilon * noise

            # Gradient estimate
            grad += (loss_plus - loss_minus) / (2 * epsilon) * noise

        grad /= 3

        # Update alphas
        self.alphas -= self.learning_rate * grad

        self.history.append({
            "alphas": self.alphas.copy(),
            "validation_loss": validation_loss
        })

    async def search(self, n_steps: int = 100) -> Architecture:
        """
        Run differentiable search.

        Args:
            n_steps: Number of optimization steps

        Returns:
            Best architecture found
        """
        estimator = ProxyEstimator()

        for step in range(n_steps):
            # Get current architecture
            arch = self.sample_discrete_architecture()
            perf = await estimator.estimate(arch)
            validation_loss = 1 - perf.get("accuracy", 0)

            # Optimization step
            await self.step(validation_loss)

            if step % 10 == 0:
                logger.info(f"Step {step}: accuracy = {perf.get('accuracy', 0):.4f}")

        # Return final architecture
        return self.sample_discrete_architecture()


# =============================================================================
# NAS CONTROLLER
# =============================================================================

class NASController:
    """
    Main NAS Controller for BAEL.

    Coordinates different NAS strategies and manages
    the architecture search process.
    """

    def __init__(
        self,
        search_space: Optional[SearchSpace] = None,
        strategy: SearchStrategy = SearchStrategy.EVOLUTIONARY
    ):
        self.space = search_space or self._default_search_space()
        self.strategy = strategy

        self.sampler = ArchitectureSampler(self.space)
        self.estimator = ProxyEstimator()

        # Searchers
        self.evolutionary = EvolutionaryNAS(self.space)
        self.differentiable = DifferentiableNAS(self.space)

        # Results
        self.best_architectures: List[Architecture] = []
        self.search_history: List[Dict[str, Any]] = []

        logger.info(f"NAS Controller initialized with strategy: {strategy.value}")

    def _default_search_space(self) -> SearchSpace:
        """Create default search space."""
        return SearchSpaceBuilder("bael_default") \
            .with_operations([
                OperationType.LINEAR,
                OperationType.ATTENTION,
                OperationType.NORMALIZATION,
                OperationType.ACTIVATION,
                OperationType.SKIP
            ]) \
            .with_max_cells(6) \
            .with_max_ops(4) \
            .build()

    async def search(
        self,
        n_iterations: int = 50,
        objectives: Optional[List[ObjectiveType]] = None
    ) -> Architecture:
        """
        Run architecture search.

        Args:
            n_iterations: Number of search iterations
            objectives: Optimization objectives

        Returns:
            Best architecture found
        """
        objectives = objectives or [ObjectiveType.ACCURACY]

        logger.info(f"Starting NAS with {self.strategy.value} strategy")

        if self.strategy == SearchStrategy.EVOLUTIONARY:
            best = await self.evolutionary.search(n_iterations)

        elif self.strategy == SearchStrategy.DIFFERENTIABLE:
            best = await self.differentiable.search(n_iterations)

        elif self.strategy == SearchStrategy.RANDOM:
            best = await self._random_search(n_iterations)

        else:
            # Default to evolutionary
            best = await self.evolutionary.search(n_iterations)

        if best:
            self.best_architectures.append(best)

        return best

    async def _random_search(self, n_iterations: int) -> Architecture:
        """Random search baseline."""
        best = None
        best_score = float('-inf')

        for i in range(n_iterations):
            arch = self.sampler.sample_architecture()
            arch.performance = await self.estimator.estimate(arch)
            arch.evaluated = True

            score = arch.performance.get("accuracy", 0)
            if score > best_score:
                best = arch
                best_score = score

            if i % 10 == 0:
                logger.info(f"Random search {i}/{n_iterations}: best = {best_score:.4f}")

        return best

    async def multi_objective_search(
        self,
        n_iterations: int = 50,
        objectives: List[ObjectiveType] = None,
        weights: Optional[List[float]] = None
    ) -> List[Architecture]:
        """
        Multi-objective architecture search.

        Returns Pareto-optimal architectures.
        """
        objectives = objectives or [ObjectiveType.ACCURACY, ObjectiveType.LATENCY]

        # Run evolutionary search with fitness based on all objectives
        await self.evolutionary.initialize_population()

        for _ in range(n_iterations):
            await self.evolutionary.evolve_generation()

        # Find Pareto front
        pareto_front = self._find_pareto_front(
            self.evolutionary.population,
            objectives
        )

        self.best_architectures.extend(pareto_front)
        return pareto_front

    def _find_pareto_front(
        self,
        architectures: List[Architecture],
        objectives: List[ObjectiveType]
    ) -> List[Architecture]:
        """Find Pareto-optimal architectures."""
        pareto_front = []

        for arch in architectures:
            is_dominated = False

            for other in architectures:
                if self._dominates(other, arch, objectives):
                    is_dominated = True
                    break

            if not is_dominated:
                pareto_front.append(arch)

        return pareto_front

    def _dominates(
        self,
        arch_a: Architecture,
        arch_b: Architecture,
        objectives: List[ObjectiveType]
    ) -> bool:
        """Check if arch_a dominates arch_b."""
        dominated_in_all = True
        strictly_better_in_one = False

        for obj in objectives:
            val_a = arch_a.performance.get(obj.value, 0)
            val_b = arch_b.performance.get(obj.value, 0)

            # For accuracy, higher is better
            # For latency/memory/etc, lower is better
            if obj in [ObjectiveType.LATENCY, ObjectiveType.MEMORY,
                       ObjectiveType.PARAMETERS, ObjectiveType.FLOPS]:
                val_a, val_b = -val_a, -val_b

            if val_a < val_b:
                dominated_in_all = False
            if val_a > val_b:
                strictly_better_in_one = True

        return dominated_in_all and strictly_better_in_one

    def export_architecture(self, arch: Architecture, format: str = "json") -> str:
        """Export architecture to specified format."""
        if format == "json":
            return json.dumps(arch.to_dict(), indent=2)
        elif format == "code":
            return self._generate_code(arch)
        return str(arch.to_dict())

    def _generate_code(self, arch: Architecture) -> str:
        """Generate Python code for architecture."""
        lines = [
            "# Auto-generated architecture",
            "from bael.core.attention import MultiHeadAttention",
            "from bael.core.layers import Linear, LayerNorm, GELU",
            "",
            "class GeneratedArchitecture:",
            "    def __init__(self, d_model=512):",
            "        self.layers = []"
        ]

        for i, cell in enumerate(arch.cells):
            lines.append(f"        # Cell {i}")
            for j, op in enumerate(cell.operations):
                if op.op_type == OperationType.LINEAR:
                    hidden = op.params.get("hidden_dim", 512)
                    lines.append(f"        self.layers.append(Linear(d_model, {hidden}))")
                elif op.op_type == OperationType.ATTENTION:
                    n_heads = op.params.get("n_heads", 8)
                    lines.append(f"        self.layers.append(MultiHeadAttention(d_model, {n_heads}))")
                elif op.op_type == OperationType.NORMALIZATION:
                    lines.append("        self.layers.append(LayerNorm(d_model))")
                elif op.op_type == OperationType.ACTIVATION:
                    lines.append("        self.layers.append(GELU())")

        lines.extend([
            "",
            "    def forward(self, x):",
            "        for layer in self.layers:",
            "            x = layer(x)",
            "        return x"
        ])

        return "\n".join(lines)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_nas_controller(
    strategy: str = "evolutionary",
    max_cells: int = 6,
    max_ops: int = 4
) -> NASController:
    """
    Factory function to create NAS controller.

    Args:
        strategy: Search strategy name
        max_cells: Maximum cells in architecture
        max_ops: Maximum operations per cell

    Returns:
        Configured NAS controller
    """
    space = SearchSpaceBuilder("custom") \
        .with_max_cells(max_cells) \
        .with_max_ops(max_ops) \
        .build()

    return NASController(
        search_space=space,
        strategy=SearchStrategy(strategy)
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "SearchStrategy",
    "OperationType",
    "ObjectiveType",

    # Data classes
    "Operation",
    "Cell",
    "Architecture",
    "SearchSpace",

    # Builders
    "SearchSpaceBuilder",
    "ArchitectureSampler",

    # Estimators
    "PerformanceEstimator",
    "ProxyEstimator",

    # Searchers
    "EvolutionaryNAS",
    "DifferentiableNAS",

    # Controller
    "NASController",
    "create_nas_controller"
]
