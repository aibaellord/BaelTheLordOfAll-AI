"""
⚡ GENETIC ALGORITHMS ⚡
=======================
Advanced genetic algorithms.

Features:
- Multiple selection methods
- Crossover operators
- Mutation operators
- Multi-objective optimization
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple
from copy import deepcopy
import uuid

from .evolution_core import Individual, Population, Genome


class SelectionMethod(Enum):
    """Selection methods"""
    TOURNAMENT = auto()
    ROULETTE = auto()
    RANK = auto()
    TRUNCATION = auto()
    BOLTZMANN = auto()


class CrossoverMethod(Enum):
    """Crossover methods"""
    SINGLE_POINT = auto()
    TWO_POINT = auto()
    UNIFORM = auto()
    BLEND = auto()
    SBX = auto()  # Simulated Binary Crossover


class MutationMethod(Enum):
    """Mutation methods"""
    GAUSSIAN = auto()
    UNIFORM = auto()
    POLYNOMIAL = auto()
    ADAPTIVE = auto()


@dataclass
class GeneticOperator:
    """Base genetic operator"""
    name: str = ""

    def apply(self, *args, **kwargs):
        raise NotImplementedError


class Selector(GeneticOperator):
    """Selection operator"""

    def __init__(self, method: SelectionMethod = SelectionMethod.TOURNAMENT):
        self.method = method
        self.tournament_size = 3
        self.temperature = 1.0  # For Boltzmann

    def apply(self, population: Population, n: int = 2) -> List[Individual]:
        """Select n individuals"""
        if self.method == SelectionMethod.TOURNAMENT:
            return self._tournament(population, n)
        elif self.method == SelectionMethod.ROULETTE:
            return self._roulette(population, n)
        elif self.method == SelectionMethod.RANK:
            return self._rank(population, n)
        elif self.method == SelectionMethod.TRUNCATION:
            return self._truncation(population, n)
        elif self.method == SelectionMethod.BOLTZMANN:
            return self._boltzmann(population, n)
        return []

    def _tournament(self, population: Population, n: int) -> List[Individual]:
        selected = []
        for _ in range(n):
            candidates = np.random.choice(
                population.individuals,
                size=min(self.tournament_size, len(population.individuals)),
                replace=False
            )
            winner = max(candidates, key=lambda x: x.fitness)
            selected.append(winner)
        return selected

    def _roulette(self, population: Population, n: int) -> List[Individual]:
        fitnesses = np.array([ind.fitness for ind in population.individuals])
        fitnesses = fitnesses - fitnesses.min() + 1e-10
        probs = fitnesses / fitnesses.sum()

        indices = np.random.choice(
            len(population.individuals),
            size=n,
            replace=True,
            p=probs
        )

        return [population.individuals[i] for i in indices]

    def _rank(self, population: Population, n: int) -> List[Individual]:
        sorted_pop = sorted(population.individuals, key=lambda x: x.fitness)
        ranks = np.arange(1, len(sorted_pop) + 1)
        probs = ranks / ranks.sum()

        indices = np.random.choice(len(sorted_pop), size=n, replace=True, p=probs)
        return [sorted_pop[i] for i in indices]

    def _truncation(self, population: Population, n: int) -> List[Individual]:
        sorted_pop = sorted(population.individuals, key=lambda x: x.fitness, reverse=True)
        top_half = sorted_pop[:len(sorted_pop) // 2]
        return list(np.random.choice(top_half, size=n, replace=True))

    def _boltzmann(self, population: Population, n: int) -> List[Individual]:
        fitnesses = np.array([ind.fitness for ind in population.individuals])
        exp_values = np.exp((fitnesses - fitnesses.max()) / self.temperature)
        probs = exp_values / exp_values.sum()

        indices = np.random.choice(len(population.individuals), size=n, replace=True, p=probs)
        return [population.individuals[i] for i in indices]


class Crossover(GeneticOperator):
    """Crossover operator"""

    def __init__(self, method: CrossoverMethod = CrossoverMethod.UNIFORM):
        self.method = method
        self.eta = 20  # Distribution index for SBX

    def apply(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Apply crossover to produce offspring"""
        if not parent1.genome or not parent2.genome:
            return deepcopy(parent1), deepcopy(parent2)

        child1_genome = Genome()
        child2_genome = Genome()

        for chrom_name in parent1.genome.chromosomes:
            if chrom_name not in parent2.genome.chromosomes:
                continue

            chrom1 = parent1.genome.chromosomes[chrom_name]
            chrom2 = parent2.genome.chromosomes[chrom_name]

            vec1 = chrom1.to_vector()
            vec2 = chrom2.to_vector()

            if self.method == CrossoverMethod.SINGLE_POINT:
                c1, c2 = self._single_point(vec1, vec2)
            elif self.method == CrossoverMethod.TWO_POINT:
                c1, c2 = self._two_point(vec1, vec2)
            elif self.method == CrossoverMethod.UNIFORM:
                c1, c2 = self._uniform(vec1, vec2)
            elif self.method == CrossoverMethod.BLEND:
                c1, c2 = self._blend(vec1, vec2)
            elif self.method == CrossoverMethod.SBX:
                c1, c2 = self._sbx(vec1, vec2)
            else:
                c1, c2 = vec1.copy(), vec2.copy()

            new_chrom1 = deepcopy(chrom1)
            new_chrom2 = deepcopy(chrom2)
            new_chrom1.from_vector(c1)
            new_chrom2.from_vector(c2)

            child1_genome.add_chromosome(chrom_name, new_chrom1)
            child2_genome.add_chromosome(chrom_name, new_chrom2)

        return Individual(genome=child1_genome), Individual(genome=child2_genome)

    def _single_point(self, v1: np.ndarray, v2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        point = np.random.randint(1, len(v1))
        c1 = np.concatenate([v1[:point], v2[point:]])
        c2 = np.concatenate([v2[:point], v1[point:]])
        return c1, c2

    def _two_point(self, v1: np.ndarray, v2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        points = sorted(np.random.choice(len(v1), 2, replace=False))
        c1 = np.concatenate([v1[:points[0]], v2[points[0]:points[1]], v1[points[1]:]])
        c2 = np.concatenate([v2[:points[0]], v1[points[0]:points[1]], v2[points[1]:]])
        return c1, c2

    def _uniform(self, v1: np.ndarray, v2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mask = np.random.random(len(v1)) < 0.5
        c1 = np.where(mask, v1, v2)
        c2 = np.where(mask, v2, v1)
        return c1, c2

    def _blend(self, v1: np.ndarray, v2: np.ndarray, alpha: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        diff = np.abs(v1 - v2)
        low = np.minimum(v1, v2) - alpha * diff
        high = np.maximum(v1, v2) + alpha * diff

        c1 = np.random.uniform(low, high)
        c2 = np.random.uniform(low, high)
        return c1, c2

    def _sbx(self, v1: np.ndarray, v2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Simulated Binary Crossover"""
        c1, c2 = v1.copy(), v2.copy()

        for i in range(len(v1)):
            if np.random.random() < 0.5:
                if abs(v1[i] - v2[i]) > 1e-14:
                    u = np.random.random()

                    if u <= 0.5:
                        beta = (2 * u) ** (1.0 / (self.eta + 1))
                    else:
                        beta = (1.0 / (2 * (1 - u))) ** (1.0 / (self.eta + 1))

                    c1[i] = 0.5 * ((1 + beta) * v1[i] + (1 - beta) * v2[i])
                    c2[i] = 0.5 * ((1 - beta) * v1[i] + (1 + beta) * v2[i])

        return c1, c2


class Mutation(GeneticOperator):
    """Mutation operator"""

    def __init__(
        self,
        method: MutationMethod = MutationMethod.GAUSSIAN,
        rate: float = 0.1,
        strength: float = 0.1
    ):
        self.method = method
        self.rate = rate
        self.strength = strength
        self.eta = 20  # For polynomial mutation

    def apply(self, individual: Individual) -> Individual:
        """Apply mutation to individual"""
        mutated = deepcopy(individual)

        if not mutated.genome:
            return mutated

        for chrom in mutated.genome.chromosomes.values():
            vec = chrom.to_vector()

            if self.method == MutationMethod.GAUSSIAN:
                mutated_vec = self._gaussian(vec)
            elif self.method == MutationMethod.UNIFORM:
                mutated_vec = self._uniform(vec)
            elif self.method == MutationMethod.POLYNOMIAL:
                mutated_vec = self._polynomial(vec)
            elif self.method == MutationMethod.ADAPTIVE:
                mutated_vec = self._adaptive(vec, individual)
            else:
                mutated_vec = vec

            chrom.from_vector(mutated_vec)

        mutated.is_evaluated = False
        return mutated

    def _gaussian(self, vec: np.ndarray) -> np.ndarray:
        mutated = vec.copy()
        for i in range(len(mutated)):
            if np.random.random() < self.rate:
                mutated[i] += np.random.normal(0, self.strength)
        return mutated

    def _uniform(self, vec: np.ndarray) -> np.ndarray:
        mutated = vec.copy()
        for i in range(len(mutated)):
            if np.random.random() < self.rate:
                mutated[i] += np.random.uniform(-self.strength, self.strength)
        return mutated

    def _polynomial(self, vec: np.ndarray) -> np.ndarray:
        mutated = vec.copy()
        for i in range(len(mutated)):
            if np.random.random() < self.rate:
                u = np.random.random()
                if u < 0.5:
                    delta = (2 * u) ** (1.0 / (self.eta + 1)) - 1
                else:
                    delta = 1 - (2 * (1 - u)) ** (1.0 / (self.eta + 1))
                mutated[i] += delta * self.strength
        return mutated

    def _adaptive(self, vec: np.ndarray, individual: Individual) -> np.ndarray:
        # Adapt strength based on fitness
        adaptive_strength = self.strength * (1.0 / (1.0 + individual.fitness * 0.1))

        mutated = vec.copy()
        for i in range(len(mutated)):
            if np.random.random() < self.rate:
                mutated[i] += np.random.normal(0, adaptive_strength)
        return mutated


class GeneticAlgorithm:
    """
    Standard Genetic Algorithm.
    """

    def __init__(
        self,
        fitness_function: Callable[[Individual], float],
        population_size: int = 100,
        selection: SelectionMethod = SelectionMethod.TOURNAMENT,
        crossover: CrossoverMethod = CrossoverMethod.UNIFORM,
        mutation: MutationMethod = MutationMethod.GAUSSIAN
    ):
        self.fitness_function = fitness_function
        self.population_size = population_size

        self.selector = Selector(selection)
        self.crossover_op = Crossover(crossover)
        self.mutation_op = Mutation(mutation)

        self.population = Population(size=population_size)
        self.elite_size = max(1, population_size // 20)
        self.crossover_rate = 0.8

    def initialize(self, genome_template: Genome):
        """Initialize population"""
        for _ in range(self.population_size):
            genome = deepcopy(genome_template)

            for chrom in genome.chromosomes.values():
                for gene in chrom.genes:
                    if gene.value_type == "float":
                        gene.value = np.random.uniform(gene.min_value, gene.max_value)

            self.population.add(Individual(genome=genome))

    def evaluate_population(self):
        """Evaluate all individuals"""
        for ind in self.population.individuals:
            if not ind.is_evaluated:
                ind.fitness = self.fitness_function(ind)
                ind.is_evaluated = True

    def evolve_generation(self) -> Dict[str, float]:
        """Evolve one generation"""
        self.evaluate_population()

        # Get elites
        elites = self.population.get_best(self.elite_size)

        # Create new population
        new_pop = [deepcopy(e) for e in elites]

        while len(new_pop) < self.population_size:
            # Select parents
            parents = self.selector.apply(self.population, 2)

            # Crossover
            if np.random.random() < self.crossover_rate:
                child1, child2 = self.crossover_op.apply(parents[0], parents[1])
            else:
                child1, child2 = deepcopy(parents[0]), deepcopy(parents[1])

            # Mutate
            child1 = self.mutation_op.apply(child1)
            child2 = self.mutation_op.apply(child2)

            new_pop.extend([child1, child2])

        self.population.individuals = new_pop[:self.population_size]
        self.population.generation += 1
        self.population.update_hall_of_fame()

        return self.population.get_statistics()

    def run(self, generations: int = 100) -> Individual:
        """Run GA for specified generations"""
        for _ in range(generations):
            self.evolve_generation()

        return self.population.get_best(1)[0]


class NSGA2:
    """
    NSGA-II Multi-Objective Genetic Algorithm.
    """

    def __init__(
        self,
        fitness_functions: List[Callable[[Individual], float]],
        population_size: int = 100
    ):
        self.fitness_functions = fitness_functions
        self.population_size = population_size

        self.population = Population(size=population_size)
        self.crossover_op = Crossover(CrossoverMethod.SBX)
        self.mutation_op = Mutation(MutationMethod.POLYNOMIAL)

    def evaluate(self, individual: Individual):
        """Evaluate on all objectives"""
        individual.fitness_components = {}
        for i, func in enumerate(self.fitness_functions):
            individual.fitness_components[f"obj_{i}"] = func(individual)
        individual.is_evaluated = True

    def fast_nondominated_sort(self) -> List[List[Individual]]:
        """Fast non-dominated sorting"""
        fronts = [[]]

        domination_count = {}
        dominated_set = {ind.id: [] for ind in self.population.individuals}

        for p in self.population.individuals:
            domination_count[p.id] = 0

            for q in self.population.individuals:
                if p.id == q.id:
                    continue

                if p.dominates(q):
                    dominated_set[p.id].append(q)
                elif q.dominates(p):
                    domination_count[p.id] += 1

            if domination_count[p.id] == 0:
                p.rank = 0
                fronts[0].append(p)

        i = 0
        while fronts[i]:
            next_front = []
            for p in fronts[i]:
                for q in dominated_set[p.id]:
                    domination_count[q.id] -= 1
                    if domination_count[q.id] == 0:
                        q.rank = i + 1
                        next_front.append(q)
            i += 1
            fronts.append(next_front)

        return fronts[:-1]  # Remove empty last front

    def crowding_distance(self, front: List[Individual]):
        """Calculate crowding distance"""
        if len(front) == 0:
            return

        for ind in front:
            ind.crowding_distance = 0.0

        n_objectives = len(self.fitness_functions)

        for m in range(n_objectives):
            obj_name = f"obj_{m}"

            # Sort by objective
            front.sort(key=lambda x: x.fitness_components.get(obj_name, 0))

            # Boundary points
            front[0].crowding_distance = float('inf')
            front[-1].crowding_distance = float('inf')

            obj_range = (
                front[-1].fitness_components.get(obj_name, 0) -
                front[0].fitness_components.get(obj_name, 0)
            )

            if obj_range == 0:
                continue

            for i in range(1, len(front) - 1):
                front[i].crowding_distance += (
                    (front[i+1].fitness_components.get(obj_name, 0) -
                     front[i-1].fitness_components.get(obj_name, 0)) / obj_range
                )

    def evolve_generation(self):
        """Evolve one generation"""
        # Evaluate
        for ind in self.population.individuals:
            if not ind.is_evaluated:
                self.evaluate(ind)

        # Non-dominated sorting
        fronts = self.fast_nondominated_sort()

        # Crowding distance
        for front in fronts:
            self.crowding_distance(front)

        # Create offspring
        offspring = []
        while len(offspring) < self.population_size:
            # Binary tournament
            parents = []
            for _ in range(2):
                a, b = np.random.choice(self.population.individuals, 2, replace=False)
                if a.rank < b.rank or (a.rank == b.rank and a.crowding_distance > b.crowding_distance):
                    parents.append(a)
                else:
                    parents.append(b)

            child1, child2 = self.crossover_op.apply(parents[0], parents[1])
            offspring.extend([
                self.mutation_op.apply(child1),
                self.mutation_op.apply(child2)
            ])

        # Combine populations
        combined = self.population.individuals + offspring

        # Re-sort combined population
        temp_pop = Population()
        temp_pop.individuals = combined
        self.population.individuals = temp_pop.individuals

        for ind in combined:
            if not ind.is_evaluated:
                self.evaluate(ind)

        fronts = self.fast_nondominated_sort()

        # Select next generation
        new_pop = []
        for front in fronts:
            self.crowding_distance(front)
            if len(new_pop) + len(front) <= self.population_size:
                new_pop.extend(front)
            else:
                # Fill remaining with best crowding distance
                front.sort(key=lambda x: x.crowding_distance, reverse=True)
                new_pop.extend(front[:self.population_size - len(new_pop)])
                break

        self.population.individuals = new_pop
        self.population.generation += 1

    def get_pareto_front(self) -> List[Individual]:
        """Get current Pareto front"""
        return [ind for ind in self.population.individuals if ind.rank == 0]


class DifferentialEvolution:
    """
    Differential Evolution optimizer.
    """

    def __init__(
        self,
        fitness_function: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
        population_size: int = 50
    ):
        self.fitness_function = fitness_function
        self.bounds = np.array(bounds)
        self.population_size = population_size

        self.F = 0.8  # Differential weight
        self.CR = 0.9  # Crossover probability

        self.population: np.ndarray = None
        self.fitness: np.ndarray = None

    def initialize(self):
        """Initialize population"""
        n_dims = len(self.bounds)
        self.population = np.random.uniform(
            self.bounds[:, 0],
            self.bounds[:, 1],
            size=(self.population_size, n_dims)
        )

        self.fitness = np.array([
            self.fitness_function(ind) for ind in self.population
        ])

    def evolve_generation(self):
        """Evolve one generation"""
        n_dims = len(self.bounds)

        for i in range(self.population_size):
            # Select three random individuals
            candidates = [j for j in range(self.population_size) if j != i]
            a, b, c = np.random.choice(candidates, 3, replace=False)

            # Mutation
            mutant = self.population[a] + self.F * (self.population[b] - self.population[c])
            mutant = np.clip(mutant, self.bounds[:, 0], self.bounds[:, 1])

            # Crossover
            trial = np.zeros(n_dims)
            j_rand = np.random.randint(n_dims)

            for j in range(n_dims):
                if np.random.random() < self.CR or j == j_rand:
                    trial[j] = mutant[j]
                else:
                    trial[j] = self.population[i, j]

            # Selection
            trial_fitness = self.fitness_function(trial)

            if trial_fitness > self.fitness[i]:
                self.population[i] = trial
                self.fitness[i] = trial_fitness

    def run(self, generations: int = 100) -> Tuple[np.ndarray, float]:
        """Run DE optimization"""
        self.initialize()

        for _ in range(generations):
            self.evolve_generation()

        best_idx = np.argmax(self.fitness)
        return self.population[best_idx], self.fitness[best_idx]


# Export all
__all__ = [
    'SelectionMethod',
    'CrossoverMethod',
    'MutationMethod',
    'GeneticOperator',
    'Selector',
    'Crossover',
    'Mutation',
    'GeneticAlgorithm',
    'NSGA2',
    'DifferentialEvolution',
]
