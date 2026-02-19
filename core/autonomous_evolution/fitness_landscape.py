"""
⚡ FITNESS LANDSCAPE ⚡
======================
Fitness landscape analysis.

Features:
- Fitness functions
- Landscape topology
- NK landscapes
- Ruggedness analysis
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
import uuid


@dataclass
class FitnessFunction:
    """A fitness function"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Function
    function: Callable = None

    # Bounds
    bounds: List[Tuple[float, float]] = field(default_factory=list)

    # Properties
    is_maximization: bool = True
    optimal_value: Optional[float] = None
    optimal_solution: Optional[np.ndarray] = None

    def __call__(self, x: np.ndarray) -> float:
        if self.function is None:
            return 0.0
        return self.function(x)

    @staticmethod
    def sphere(x: np.ndarray) -> float:
        """Sphere function (minimize)"""
        return -np.sum(x ** 2)

    @staticmethod
    def rastrigin(x: np.ndarray) -> float:
        """Rastrigin function (minimize)"""
        n = len(x)
        return -(10 * n + np.sum(x**2 - 10 * np.cos(2 * np.pi * x)))

    @staticmethod
    def rosenbrock(x: np.ndarray) -> float:
        """Rosenbrock function (minimize)"""
        result = 0.0
        for i in range(len(x) - 1):
            result += 100 * (x[i+1] - x[i]**2)**2 + (1 - x[i])**2
        return -result

    @staticmethod
    def ackley(x: np.ndarray) -> float:
        """Ackley function (minimize)"""
        n = len(x)
        sum1 = np.sum(x**2)
        sum2 = np.sum(np.cos(2 * np.pi * x))
        term1 = -20 * np.exp(-0.2 * np.sqrt(sum1 / n))
        term2 = -np.exp(sum2 / n)
        return -(term1 + term2 + 20 + np.e)


@dataclass
class MultiObjectiveFitness:
    """Multi-objective fitness"""
    objectives: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)

    def add_objective(self, name: str, value: float, weight: float = 1.0):
        """Add objective"""
        self.objectives[name] = value
        self.weights[name] = weight

    def get_weighted_sum(self) -> float:
        """Get weighted sum"""
        total = 0.0
        for name, value in self.objectives.items():
            total += self.weights.get(name, 1.0) * value
        return total

    def dominates(self, other: 'MultiObjectiveFitness') -> bool:
        """Check if this dominates other"""
        better_in_one = False

        for name in self.objectives:
            if name not in other.objectives:
                continue

            if self.objectives[name] < other.objectives[name]:
                return False
            if self.objectives[name] > other.objectives[name]:
                better_in_one = True

        return better_in_one


class FitnessLandscape:
    """
    Fitness landscape representation.
    """

    def __init__(
        self,
        fitness_function: Callable[[np.ndarray], float],
        dimensions: int = 2,
        bounds: Tuple[float, float] = (-5, 5)
    ):
        self.fitness_function = fitness_function
        self.dimensions = dimensions
        self.bounds = bounds

        # Cached landscape
        self.grid: np.ndarray = None
        self.fitness_grid: np.ndarray = None
        self.resolution: int = 50

    def evaluate(self, x: np.ndarray) -> float:
        """Evaluate fitness at point"""
        return self.fitness_function(x)

    def build_grid(self, resolution: int = 50):
        """Build fitness grid (for 2D visualization)"""
        self.resolution = resolution

        x = np.linspace(self.bounds[0], self.bounds[1], resolution)
        y = np.linspace(self.bounds[0], self.bounds[1], resolution)

        self.grid = np.meshgrid(x, y)
        self.fitness_grid = np.zeros((resolution, resolution))

        for i in range(resolution):
            for j in range(resolution):
                point = np.array([self.grid[0][i, j], self.grid[1][i, j]])
                self.fitness_grid[i, j] = self.fitness_function(point)

    def find_local_optima(self, n_starts: int = 10) -> List[Tuple[np.ndarray, float]]:
        """Find local optima using random restarts"""
        optima = []

        for _ in range(n_starts):
            # Random start
            x = np.random.uniform(self.bounds[0], self.bounds[1], self.dimensions)

            # Simple hill climbing
            step_size = 0.1
            for _ in range(100):
                current_fitness = self.fitness_function(x)

                # Try neighbors
                improved = False
                for d in range(self.dimensions):
                    for direction in [-1, 1]:
                        neighbor = x.copy()
                        neighbor[d] += direction * step_size
                        neighbor = np.clip(neighbor, self.bounds[0], self.bounds[1])

                        neighbor_fitness = self.fitness_function(neighbor)
                        if neighbor_fitness > current_fitness:
                            x = neighbor
                            current_fitness = neighbor_fitness
                            improved = True
                            break
                    if improved:
                        break

                if not improved:
                    step_size *= 0.9
                    if step_size < 0.001:
                        break

            optima.append((x.copy(), self.fitness_function(x)))

        # Remove duplicates
        unique_optima = []
        for opt, fit in optima:
            is_duplicate = False
            for existing_opt, _ in unique_optima:
                if np.linalg.norm(opt - existing_opt) < 0.1:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_optima.append((opt, fit))

        return sorted(unique_optima, key=lambda x: x[1], reverse=True)

    def estimate_global_optimum(self, n_samples: int = 1000) -> Tuple[np.ndarray, float]:
        """Estimate global optimum using random sampling + local search"""
        best_x = None
        best_fitness = float('-inf')

        for _ in range(n_samples):
            x = np.random.uniform(self.bounds[0], self.bounds[1], self.dimensions)
            fitness = self.fitness_function(x)

            if fitness > best_fitness:
                best_fitness = fitness
                best_x = x.copy()

        return best_x, best_fitness


class LandscapeAnalyzer:
    """
    Analyze fitness landscape properties.
    """

    def __init__(self, landscape: FitnessLandscape):
        self.landscape = landscape

    def estimate_ruggedness(self, n_walks: int = 10, walk_length: int = 100) -> float:
        """
        Estimate landscape ruggedness using autocorrelation.
        Lower autocorrelation = more rugged.
        """
        autocorrelations = []

        for _ in range(n_walks):
            # Random walk
            x = np.random.uniform(
                self.landscape.bounds[0],
                self.landscape.bounds[1],
                self.landscape.dimensions
            )

            fitness_sequence = []
            step_size = (self.landscape.bounds[1] - self.landscape.bounds[0]) * 0.01

            for _ in range(walk_length):
                fitness_sequence.append(self.landscape.evaluate(x))

                # Random step
                direction = np.random.randn(self.landscape.dimensions)
                direction = direction / np.linalg.norm(direction)
                x = x + step_size * direction
                x = np.clip(x, self.landscape.bounds[0], self.landscape.bounds[1])

            # Compute autocorrelation at lag 1
            if len(fitness_sequence) > 1:
                mean = np.mean(fitness_sequence)
                var = np.var(fitness_sequence)

                if var > 0:
                    autocorr = np.sum(
                        (np.array(fitness_sequence[:-1]) - mean) *
                        (np.array(fitness_sequence[1:]) - mean)
                    ) / ((len(fitness_sequence) - 1) * var)
                    autocorrelations.append(autocorr)

        if autocorrelations:
            return 1 - np.mean(autocorrelations)  # Higher = more rugged
        return 0.5

    def estimate_modality(self, n_restarts: int = 20) -> int:
        """Estimate number of local optima (modality)"""
        optima = self.landscape.find_local_optima(n_restarts)
        return len(optima)

    def estimate_neutrality(self, n_samples: int = 1000, epsilon: float = 0.01) -> float:
        """
        Estimate landscape neutrality.
        Neutrality = fraction of neighbors with similar fitness.
        """
        neutral_neighbors = 0
        total_neighbors = 0

        for _ in range(n_samples):
            x = np.random.uniform(
                self.landscape.bounds[0],
                self.landscape.bounds[1],
                self.landscape.dimensions
            )
            base_fitness = self.landscape.evaluate(x)

            # Check neighbors
            step = (self.landscape.bounds[1] - self.landscape.bounds[0]) * 0.01

            for d in range(self.landscape.dimensions):
                for direction in [-1, 1]:
                    neighbor = x.copy()
                    neighbor[d] += direction * step
                    neighbor = np.clip(neighbor, self.landscape.bounds[0], self.landscape.bounds[1])

                    neighbor_fitness = self.landscape.evaluate(neighbor)

                    if abs(neighbor_fitness - base_fitness) < epsilon * abs(base_fitness + 1e-10):
                        neutral_neighbors += 1
                    total_neighbors += 1

        return neutral_neighbors / total_neighbors if total_neighbors > 0 else 0.0

    def estimate_fitness_distance_correlation(self, n_samples: int = 1000) -> float:
        """
        Estimate correlation between fitness and distance to optimum.
        Higher correlation = easier landscape.
        """
        # First estimate global optimum
        best_x, best_fitness = self.landscape.estimate_global_optimum()

        distances = []
        fitnesses = []

        for _ in range(n_samples):
            x = np.random.uniform(
                self.landscape.bounds[0],
                self.landscape.bounds[1],
                self.landscape.dimensions
            )

            distance = np.linalg.norm(x - best_x)
            fitness = self.landscape.evaluate(x)

            distances.append(distance)
            fitnesses.append(fitness)

        distances = np.array(distances)
        fitnesses = np.array(fitnesses)

        # Correlation
        if np.std(distances) > 0 and np.std(fitnesses) > 0:
            correlation = np.corrcoef(distances, fitnesses)[0, 1]
            return -correlation  # Negative because smaller distance should mean higher fitness
        return 0.0

    def get_landscape_features(self) -> Dict[str, float]:
        """Get comprehensive landscape features"""
        return {
            'ruggedness': self.estimate_ruggedness(),
            'modality': self.estimate_modality(),
            'neutrality': self.estimate_neutrality(),
            'fdc': self.estimate_fitness_distance_correlation(),
            'dimensions': self.landscape.dimensions
        }


class NKLandscape:
    """
    NK Landscape model.

    N = number of genes
    K = epistasis (number of other genes affecting each gene's fitness)
    """

    def __init__(self, n: int = 10, k: int = 2, seed: int = None):
        self.n = n
        self.k = min(k, n - 1)

        if seed is not None:
            np.random.seed(seed)

        # Generate random epistasis structure
        self.neighbors: List[List[int]] = []
        for i in range(n):
            others = [j for j in range(n) if j != i]
            neighbors = list(np.random.choice(others, self.k, replace=False))
            self.neighbors.append(neighbors)

        # Generate random fitness contributions
        self.fitness_tables: List[Dict[tuple, float]] = []
        for i in range(n):
            table = {}
            # 2^(K+1) possible combinations
            for bits in range(2 ** (self.k + 1)):
                table[bits] = np.random.random()
            self.fitness_tables.append(table)

    def evaluate(self, genotype: np.ndarray) -> float:
        """Evaluate fitness of binary genotype"""
        genotype = np.array(genotype, dtype=int)

        total_fitness = 0.0

        for i in range(self.n):
            # Get relevant bits
            bits = [genotype[i]]
            for j in self.neighbors[i]:
                bits.append(genotype[j])

            # Convert to index
            index = sum(b << pos for pos, b in enumerate(bits))

            total_fitness += self.fitness_tables[i][index]

        return total_fitness / self.n

    def get_neighbors(self, genotype: np.ndarray) -> List[np.ndarray]:
        """Get all 1-bit mutant neighbors"""
        neighbors = []
        for i in range(self.n):
            neighbor = genotype.copy()
            neighbor[i] = 1 - neighbor[i]
            neighbors.append(neighbor)
        return neighbors

    def local_search(self, start: np.ndarray = None) -> Tuple[np.ndarray, float]:
        """Perform local search from starting point"""
        if start is None:
            current = np.random.randint(0, 2, self.n)
        else:
            current = start.copy()

        current_fitness = self.evaluate(current)

        improved = True
        while improved:
            improved = False

            for neighbor in self.get_neighbors(current):
                neighbor_fitness = self.evaluate(neighbor)
                if neighbor_fitness > current_fitness:
                    current = neighbor
                    current_fitness = neighbor_fitness
                    improved = True
                    break

        return current, current_fitness

    def estimate_global_optimum(self, n_restarts: int = 100) -> Tuple[np.ndarray, float]:
        """Estimate global optimum"""
        best_genotype = None
        best_fitness = float('-inf')

        for _ in range(n_restarts):
            genotype, fitness = self.local_search()
            if fitness > best_fitness:
                best_fitness = fitness
                best_genotype = genotype.copy()

        return best_genotype, best_fitness


# Export all
__all__ = [
    'FitnessFunction',
    'MultiObjectiveFitness',
    'FitnessLandscape',
    'LandscapeAnalyzer',
    'NKLandscape',
]
