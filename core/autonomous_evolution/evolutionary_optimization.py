"""
⚡ EVOLUTIONARY OPTIMIZATION ⚡
==============================
Advanced evolution strategies.

Features:
- CMA-ES
- Natural Evolution Strategies
- Coevolution
- Self-adaptation
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from copy import deepcopy
import uuid


class EvolutionStrategy:
    """
    Basic (μ, λ) and (μ + λ) Evolution Strategy.
    """

    def __init__(
        self,
        fitness_function: Callable[[np.ndarray], float],
        dimensions: int,
        mu: int = 10,  # Parent population size
        lambda_: int = 50,  # Offspring population size
        plus_selection: bool = False  # (μ + λ) vs (μ, λ)
    ):
        self.fitness_function = fitness_function
        self.dimensions = dimensions
        self.mu = mu
        self.lambda_ = lambda_
        self.plus_selection = plus_selection

        # Population
        self.population: np.ndarray = None
        self.sigma: np.ndarray = None  # Step sizes
        self.fitness: np.ndarray = None

        # Bounds
        self.bounds = (-5.0, 5.0)

    def initialize(self, bounds: Tuple[float, float] = None):
        """Initialize population"""
        if bounds:
            self.bounds = bounds

        self.population = np.random.uniform(
            self.bounds[0], self.bounds[1],
            (self.mu, self.dimensions)
        )
        self.sigma = np.ones((self.mu, self.dimensions)) * 0.5
        self.fitness = np.array([self.fitness_function(x) for x in self.population])

    def evolve_generation(self) -> float:
        """Evolve one generation"""
        # Generate offspring
        offspring = []
        offspring_sigma = []

        for _ in range(self.lambda_):
            # Select parent uniformly
            parent_idx = np.random.randint(self.mu)
            parent = self.population[parent_idx]
            parent_sigma = self.sigma[parent_idx]

            # Mutate sigma (self-adaptation)
            tau = 1 / np.sqrt(2 * self.dimensions)
            tau_prime = 1 / np.sqrt(2 * np.sqrt(self.dimensions))

            new_sigma = parent_sigma * np.exp(
                tau_prime * np.random.randn() +
                tau * np.random.randn(self.dimensions)
            )
            new_sigma = np.maximum(new_sigma, 1e-8)

            # Mutate individual
            new_x = parent + new_sigma * np.random.randn(self.dimensions)
            new_x = np.clip(new_x, self.bounds[0], self.bounds[1])

            offspring.append(new_x)
            offspring_sigma.append(new_sigma)

        offspring = np.array(offspring)
        offspring_sigma = np.array(offspring_sigma)
        offspring_fitness = np.array([self.fitness_function(x) for x in offspring])

        # Selection
        if self.plus_selection:
            # (μ + λ) selection
            combined = np.vstack([self.population, offspring])
            combined_sigma = np.vstack([self.sigma, offspring_sigma])
            combined_fitness = np.concatenate([self.fitness, offspring_fitness])
        else:
            # (μ, λ) selection
            combined = offspring
            combined_sigma = offspring_sigma
            combined_fitness = offspring_fitness

        # Select best μ
        best_indices = np.argsort(combined_fitness)[-self.mu:]
        self.population = combined[best_indices]
        self.sigma = combined_sigma[best_indices]
        self.fitness = combined_fitness[best_indices]

        return np.max(self.fitness)

    def run(self, generations: int = 100) -> Tuple[np.ndarray, float]:
        """Run evolution strategy"""
        self.initialize()

        for _ in range(generations):
            self.evolve_generation()

        best_idx = np.argmax(self.fitness)
        return self.population[best_idx], self.fitness[best_idx]


class CMAEvolutionStrategy:
    """
    Covariance Matrix Adaptation Evolution Strategy.

    State-of-the-art derivative-free optimization.
    """

    def __init__(
        self,
        fitness_function: Callable[[np.ndarray], float],
        dimensions: int,
        population_size: int = None
    ):
        self.fitness_function = fitness_function
        self.n = dimensions

        # Population size
        self.lambda_ = population_size or 4 + int(3 * np.log(dimensions))
        self.mu = self.lambda_ // 2

        # Weights for recombination
        weights = np.log(self.mu + 0.5) - np.log(np.arange(1, self.mu + 1))
        self.weights = weights / weights.sum()
        self.mu_eff = 1 / np.sum(self.weights ** 2)

        # Learning rates
        self.c_sigma = (self.mu_eff + 2) / (self.n + self.mu_eff + 5)
        self.d_sigma = 1 + 2 * max(0, np.sqrt((self.mu_eff - 1) / (self.n + 1)) - 1) + self.c_sigma

        self.c_c = (4 + self.mu_eff / self.n) / (self.n + 4 + 2 * self.mu_eff / self.n)
        self.c_1 = 2 / ((self.n + 1.3) ** 2 + self.mu_eff)
        self.c_mu = min(
            1 - self.c_1,
            2 * (self.mu_eff - 2 + 1 / self.mu_eff) / ((self.n + 2) ** 2 + self.mu_eff)
        )

        # Expected norm of N(0, I)
        self.chi_n = np.sqrt(self.n) * (1 - 1 / (4 * self.n) + 1 / (21 * self.n ** 2))

        # State variables
        self.mean = None
        self.sigma = None
        self.C = None
        self.p_sigma = None
        self.p_c = None
        self.B = None
        self.D = None

        self.generation = 0
        self.best_solution = None
        self.best_fitness = float('-inf')

    def initialize(self, x0: np.ndarray = None, sigma0: float = 0.5):
        """Initialize CMA-ES"""
        self.mean = x0 if x0 is not None else np.zeros(self.n)
        self.sigma = sigma0
        self.C = np.eye(self.n)
        self.p_sigma = np.zeros(self.n)
        self.p_c = np.zeros(self.n)
        self.B = np.eye(self.n)
        self.D = np.ones(self.n)
        self.generation = 0

    def _update_eigensystem(self):
        """Update eigendecomposition of C"""
        self.C = np.triu(self.C) + np.triu(self.C, 1).T
        D, B = np.linalg.eigh(self.C)
        D = np.sqrt(np.maximum(D, 1e-20))
        self.D = D
        self.B = B

    def evolve_generation(self) -> float:
        """Evolve one generation"""
        # Sample offspring
        offspring = []
        for _ in range(self.lambda_):
            z = np.random.randn(self.n)
            y = self.B @ (self.D * z)
            x = self.mean + self.sigma * y
            offspring.append(x)

        offspring = np.array(offspring)

        # Evaluate
        fitness = np.array([self.fitness_function(x) for x in offspring])

        # Sort by fitness (descending for maximization)
        indices = np.argsort(fitness)[::-1]

        # Update best
        if fitness[indices[0]] > self.best_fitness:
            self.best_fitness = fitness[indices[0]]
            self.best_solution = offspring[indices[0]].copy()

        # Selection and recombination
        selected = offspring[indices[:self.mu]]

        old_mean = self.mean.copy()
        self.mean = np.sum(self.weights[:, np.newaxis] * selected, axis=0)

        # Update evolution paths
        y = (self.mean - old_mean) / self.sigma

        C_inv_sqrt = self.B @ np.diag(1 / self.D) @ self.B.T

        self.p_sigma = (
            (1 - self.c_sigma) * self.p_sigma +
            np.sqrt(self.c_sigma * (2 - self.c_sigma) * self.mu_eff) * (C_inv_sqrt @ y)
        )

        h_sigma = (
            np.linalg.norm(self.p_sigma) /
            np.sqrt(1 - (1 - self.c_sigma) ** (2 * (self.generation + 1)))
            < (1.4 + 2 / (self.n + 1)) * self.chi_n
        )

        self.p_c = (
            (1 - self.c_c) * self.p_c +
            h_sigma * np.sqrt(self.c_c * (2 - self.c_c) * self.mu_eff) * y
        )

        # Update covariance matrix
        artmp = (selected - old_mean) / self.sigma

        self.C = (
            (1 - self.c_1 - self.c_mu) * self.C +
            self.c_1 * (
                np.outer(self.p_c, self.p_c) +
                (1 - h_sigma) * self.c_c * (2 - self.c_c) * self.C
            ) +
            self.c_mu * np.sum([
                self.weights[i] * np.outer(artmp[i], artmp[i])
                for i in range(self.mu)
            ], axis=0)
        )

        # Update step size
        self.sigma = self.sigma * np.exp(
            (self.c_sigma / self.d_sigma) *
            (np.linalg.norm(self.p_sigma) / self.chi_n - 1)
        )

        # Update eigensystem
        if self.generation % (self.n // 10 + 1) == 0:
            self._update_eigensystem()

        self.generation += 1

        return self.best_fitness

    def run(self, generations: int = 100) -> Tuple[np.ndarray, float]:
        """Run CMA-ES"""
        if self.mean is None:
            self.initialize()

        for _ in range(generations):
            self.evolve_generation()

        return self.best_solution, self.best_fitness


class NaturalEvolutionStrategy:
    """
    Natural Evolution Strategy using natural gradients.
    """

    def __init__(
        self,
        fitness_function: Callable[[np.ndarray], float],
        dimensions: int,
        population_size: int = 50,
        learning_rate: float = 0.1
    ):
        self.fitness_function = fitness_function
        self.n = dimensions
        self.population_size = population_size
        self.learning_rate = learning_rate

        # Parameters
        self.mean = None
        self.sigma = None

        self.generation = 0

    def initialize(self, x0: np.ndarray = None, sigma0: float = 1.0):
        """Initialize NES"""
        self.mean = x0 if x0 is not None else np.zeros(self.n)
        self.sigma = sigma0
        self.generation = 0

    def evolve_generation(self) -> float:
        """Evolve one generation using natural gradients"""
        # Sample perturbations
        epsilon = np.random.randn(self.population_size, self.n)

        # Evaluate in both directions (antithetic sampling)
        fitness_plus = np.array([
            self.fitness_function(self.mean + self.sigma * eps)
            for eps in epsilon
        ])
        fitness_minus = np.array([
            self.fitness_function(self.mean - self.sigma * eps)
            for eps in epsilon
        ])

        # Fitness shaping (rank-based)
        all_fitness = np.concatenate([fitness_plus, fitness_minus])
        ranks = np.argsort(np.argsort(all_fitness))
        shaped = np.maximum(0, np.log(len(all_fitness) / 2 + 1) - np.log(ranks + 1))
        shaped = shaped / (shaped.sum() + 1e-10) - 1 / len(all_fitness)

        shaped_plus = shaped[:self.population_size]
        shaped_minus = shaped[self.population_size:]

        # Natural gradient for mean
        gradient_mean = np.sum(
            (shaped_plus[:, np.newaxis] - shaped_minus[:, np.newaxis]) * epsilon,
            axis=0
        ) / (2 * self.population_size)

        # Natural gradient for sigma (simplified)
        gradient_sigma = np.sum(
            (shaped_plus + shaped_minus) * (np.linalg.norm(epsilon, axis=1) ** 2 - self.n)
        ) / (2 * self.population_size * self.n)

        # Update parameters
        self.mean = self.mean + self.learning_rate * self.sigma * gradient_mean
        self.sigma = self.sigma * np.exp(self.learning_rate / 2 * gradient_sigma)
        self.sigma = max(self.sigma, 1e-8)

        self.generation += 1

        return np.max(all_fitness)

    def run(self, generations: int = 100) -> Tuple[np.ndarray, float]:
        """Run NES"""
        if self.mean is None:
            self.initialize()

        best_x = self.mean.copy()
        best_fitness = self.fitness_function(self.mean)

        for _ in range(generations):
            current_best = self.evolve_generation()
            if current_best > best_fitness:
                best_fitness = current_best
                best_x = self.mean.copy()

        return best_x, best_fitness


class CoevolutionEngine:
    """
    Coevolutionary optimization with multiple populations.
    """

    def __init__(
        self,
        n_populations: int = 2,
        population_size: int = 50,
        dimensions: int = 10
    ):
        self.n_populations = n_populations
        self.population_size = population_size
        self.dimensions = dimensions

        # Populations
        self.populations: List[np.ndarray] = []
        self.fitness: List[np.ndarray] = []

        # Fitness functions (can depend on other populations)
        self.fitness_functions: List[Callable] = []

        self.generation = 0

    def initialize(self, bounds: Tuple[float, float] = (-5, 5)):
        """Initialize all populations"""
        self.populations = []
        self.fitness = []

        for _ in range(self.n_populations):
            pop = np.random.uniform(
                bounds[0], bounds[1],
                (self.population_size, self.dimensions)
            )
            self.populations.append(pop)
            self.fitness.append(np.zeros(self.population_size))

    def set_fitness_function(self, pop_idx: int, func: Callable):
        """Set fitness function for a population"""
        while len(self.fitness_functions) <= pop_idx:
            self.fitness_functions.append(None)
        self.fitness_functions[pop_idx] = func

    def evaluate_population(self, pop_idx: int):
        """Evaluate a population"""
        if pop_idx >= len(self.fitness_functions) or self.fitness_functions[pop_idx] is None:
            return

        for i, individual in enumerate(self.populations[pop_idx]):
            # Pass other populations as context
            other_pops = [
                self.populations[j]
                for j in range(self.n_populations)
                if j != pop_idx
            ]
            self.fitness[pop_idx][i] = self.fitness_functions[pop_idx](individual, other_pops)

    def evolve_population(self, pop_idx: int, mutation_rate: float = 0.1):
        """Evolve a single population"""
        pop = self.populations[pop_idx]
        fit = self.fitness[pop_idx]

        # Tournament selection
        new_pop = []
        for _ in range(self.population_size):
            # Tournament
            candidates = np.random.choice(self.population_size, 3, replace=False)
            winner = candidates[np.argmax(fit[candidates])]

            # Clone and mutate
            child = pop[winner].copy()
            if np.random.random() < mutation_rate:
                child += np.random.randn(self.dimensions) * 0.1

            new_pop.append(child)

        self.populations[pop_idx] = np.array(new_pop)

    def evolve_generation(self):
        """Evolve all populations"""
        # Evaluate all
        for i in range(self.n_populations):
            self.evaluate_population(i)

        # Evolve all
        for i in range(self.n_populations):
            self.evolve_population(i)

        self.generation += 1

    def run(self, generations: int = 100) -> List[Tuple[np.ndarray, float]]:
        """Run coevolution"""
        for _ in range(generations):
            self.evolve_generation()

        results = []
        for i in range(self.n_populations):
            best_idx = np.argmax(self.fitness[i])
            results.append((
                self.populations[i][best_idx],
                self.fitness[i][best_idx]
            ))

        return results


class SelfAdaptingEvolver:
    """
    Self-adapting evolutionary optimizer.

    Automatically adapts:
    - Mutation rates
    - Step sizes
    - Population size
    - Selection pressure
    """

    def __init__(
        self,
        fitness_function: Callable[[np.ndarray], float],
        dimensions: int
    ):
        self.fitness_function = fitness_function
        self.n = dimensions

        # Adaptive parameters
        self.mutation_rate = 0.1
        self.mutation_strength = 0.1
        self.population_size = 50
        self.elite_ratio = 0.1

        # History for adaptation
        self.fitness_history: List[float] = []
        self.improvement_history: List[bool] = []
        self.adaptation_window = 20

        # Population
        self.population = None
        self.fitness = None

        self.generation = 0

    def initialize(self, bounds: Tuple[float, float] = (-5, 5)):
        """Initialize population"""
        self.population = np.random.uniform(
            bounds[0], bounds[1],
            (self.population_size, self.n)
        )
        self.fitness = np.array([
            self.fitness_function(x) for x in self.population
        ])

    def adapt_parameters(self):
        """Adapt parameters based on history"""
        if len(self.fitness_history) < self.adaptation_window:
            return

        recent_fitness = self.fitness_history[-self.adaptation_window:]
        recent_improvements = self.improvement_history[-self.adaptation_window:]

        improvement_rate = sum(recent_improvements) / len(recent_improvements)

        # Adapt mutation rate
        if improvement_rate < 0.1:
            # Too few improvements - increase exploration
            self.mutation_rate = min(0.5, self.mutation_rate * 1.2)
            self.mutation_strength = min(1.0, self.mutation_strength * 1.1)
        elif improvement_rate > 0.3:
            # Many improvements - decrease exploration (refine)
            self.mutation_rate = max(0.01, self.mutation_rate * 0.9)
            self.mutation_strength = max(0.01, self.mutation_strength * 0.95)

        # Adapt population size
        fitness_variance = np.var(recent_fitness)
        if fitness_variance < 1e-6:
            # Population converged - may need more diversity
            self.population_size = min(200, self.population_size + 10)
        elif fitness_variance > 1:
            # High variance - may need more selection
            self.elite_ratio = min(0.3, self.elite_ratio * 1.1)

    def evolve_generation(self) -> float:
        """Evolve one generation"""
        # Sort by fitness
        indices = np.argsort(self.fitness)[::-1]
        self.population = self.population[indices]
        self.fitness = self.fitness[indices]

        best_fitness_before = self.fitness[0]

        # Elite selection
        n_elite = max(1, int(self.population_size * self.elite_ratio))
        new_pop = list(self.population[:n_elite])
        new_fitness = list(self.fitness[:n_elite])

        # Generate offspring
        while len(new_pop) < self.population_size:
            # Tournament selection
            candidates = np.random.choice(len(self.population), 3, replace=False)
            parent_idx = candidates[np.argmax(self.fitness[candidates])]
            parent = self.population[parent_idx]

            # Mutation
            child = parent.copy()
            for i in range(self.n):
                if np.random.random() < self.mutation_rate:
                    child[i] += np.random.normal(0, self.mutation_strength)

            child_fitness = self.fitness_function(child)
            new_pop.append(child)
            new_fitness.append(child_fitness)

        self.population = np.array(new_pop)
        self.fitness = np.array(new_fitness)

        # Track history
        best_fitness = np.max(self.fitness)
        self.fitness_history.append(best_fitness)
        self.improvement_history.append(best_fitness > best_fitness_before)

        # Adapt
        self.adapt_parameters()

        self.generation += 1

        return best_fitness

    def run(self, generations: int = 100) -> Tuple[np.ndarray, float]:
        """Run self-adapting evolution"""
        if self.population is None:
            self.initialize()

        for _ in range(generations):
            self.evolve_generation()

        best_idx = np.argmax(self.fitness)
        return self.population[best_idx], self.fitness[best_idx]

    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get adaptation statistics"""
        return {
            'mutation_rate': self.mutation_rate,
            'mutation_strength': self.mutation_strength,
            'population_size': self.population_size,
            'elite_ratio': self.elite_ratio,
            'generation': self.generation,
            'final_best_fitness': np.max(self.fitness) if self.fitness is not None else None
        }


# Export all
__all__ = [
    'EvolutionStrategy',
    'CMAEvolutionStrategy',
    'NaturalEvolutionStrategy',
    'CoevolutionEngine',
    'SelfAdaptingEvolver',
]
