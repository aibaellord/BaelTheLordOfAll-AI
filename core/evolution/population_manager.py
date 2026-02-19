"""
BAEL Population Manager
========================

Manages populations for genetic programming.
Handles selection, breeding, and survival.

Features:
- Population initialization
- Selection methods
- Breeding strategies
- Elitism
- Population diversity
"""

import copy
import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .code_genome import CodeGenome, GenomeEncoder
from .fitness_evaluator import FitnessEvaluator, FitnessResult
from .mutation_engine import MutationEngine, MutationStrategy

logger = logging.getLogger(__name__)


class SelectionMethod(Enum):
    """Selection methods for breeding."""
    TOURNAMENT = "tournament"  # Tournament selection
    ROULETTE = "roulette"  # Roulette wheel selection
    RANK = "rank"  # Rank-based selection
    TRUNCATION = "truncation"  # Keep top N
    ELITISM = "elitism"  # Keep best + random


@dataclass
class Individual:
    """An individual in the population."""
    genome: CodeGenome
    fitness: float = 0.0

    # Evaluation
    fitness_result: Optional[FitnessResult] = None

    # Lineage
    parents: List[str] = field(default_factory=list)
    generation: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Population:
    """A population of individuals."""
    id: str

    # Individuals
    individuals: List[Individual] = field(default_factory=list)

    # Stats
    generation: int = 0
    best_fitness: float = 0.0
    avg_fitness: float = 0.0
    diversity: float = 0.0

    # History
    best_individual: Optional[Individual] = None
    fitness_history: List[float] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def size(self) -> int:
        return len(self.individuals)


class PopulationManager:
    """
    Population manager for BAEL.

    Manages genetic programming populations.
    """

    def __init__(
        self,
        population_size: int = 50,
        selection_method: SelectionMethod = SelectionMethod.TOURNAMENT,
        tournament_size: int = 5,
        elite_count: int = 2,
        crossover_rate: float = 0.7,
        mutation_rate: float = 0.1,
    ):
        self.population_size = population_size
        self.selection_method = selection_method
        self.tournament_size = tournament_size
        self.elite_count = elite_count
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate

        # Components
        self.encoder = GenomeEncoder()
        self.mutator = MutationEngine(
            mutation_rate=mutation_rate,
            strategy=MutationStrategy.CONSERVATIVE,
        )
        self.evaluator: Optional[FitnessEvaluator] = None

        # Active population
        self._population: Optional[Population] = None

        # Stats
        self.stats = {
            "populations_created": 0,
            "generations_evolved": 0,
            "individuals_created": 0,
        }

    def initialize(
        self,
        seed_code: str,
        variations: int = 0,
    ) -> Population:
        """
        Initialize a population.

        Args:
            seed_code: Initial code to seed population
            variations: Number of variations to create

        Returns:
            Initialized population
        """
        pop_id = hashlib.md5(
            f"{seed_code[:50]}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        population = Population(id=pop_id)

        # Create seed individual
        seed_genome = self.encoder.encode(seed_code)
        seed_individual = Individual(genome=seed_genome)
        population.individuals.append(seed_individual)

        # Create variations
        target_size = max(self.population_size, variations + 1)

        while len(population.individuals) < target_size:
            # Clone and mutate
            parent = random.choice(population.individuals)
            mutated_genome, _ = self.mutator.mutate(
                parent.genome,
                num_mutations=random.randint(1, 3),
            )

            individual = Individual(
                genome=mutated_genome,
                parents=[parent.genome.id],
            )
            population.individuals.append(individual)
            self.stats["individuals_created"] += 1

        self._population = population
        self.stats["populations_created"] += 1

        return population

    def evaluate_population(
        self,
        population: Optional[Population] = None,
        function_name: Optional[str] = None,
    ) -> None:
        """
        Evaluate all individuals in population.

        Args:
            population: Population to evaluate (uses active if None)
            function_name: Function to test
        """
        population = population or self._population
        if not population:
            return

        if not self.evaluator:
            logger.warning("No evaluator set")
            return

        total_fitness = 0.0

        for individual in population.individuals:
            result = self.evaluator.evaluate(
                individual.genome,
                function_name=function_name,
            )
            individual.fitness = result.fitness
            individual.fitness_result = result
            total_fitness += result.fitness

        # Update population stats
        population.avg_fitness = total_fitness / max(len(population.individuals), 1)
        population.best_fitness = max(i.fitness for i in population.individuals)
        population.fitness_history.append(population.best_fitness)

        # Track best individual
        best = max(population.individuals, key=lambda i: i.fitness)
        if not population.best_individual or best.fitness > population.best_individual.fitness:
            population.best_individual = copy.deepcopy(best)

        # Calculate diversity
        population.diversity = self._calculate_diversity(population)

    def _calculate_diversity(self, population: Population) -> float:
        """Calculate population diversity."""
        if len(population.individuals) < 2:
            return 0.0

        # Simple diversity: variance of fitness
        fitnesses = [i.fitness for i in population.individuals]
        mean = sum(fitnesses) / len(fitnesses)
        variance = sum((f - mean) ** 2 for f in fitnesses) / len(fitnesses)

        # Normalize to 0-1 (assuming fitness is 0-1)
        return min(1.0, variance * 4)  # Scale factor

    def select_parents(
        self,
        population: Optional[Population] = None,
        count: int = 2,
    ) -> List[Individual]:
        """
        Select parents for breeding.

        Args:
            population: Population to select from
            count: Number of parents to select

        Returns:
            Selected individuals
        """
        population = population or self._population
        if not population or not population.individuals:
            return []

        if self.selection_method == SelectionMethod.TOURNAMENT:
            return self._tournament_select(population, count)
        elif self.selection_method == SelectionMethod.ROULETTE:
            return self._roulette_select(population, count)
        elif self.selection_method == SelectionMethod.RANK:
            return self._rank_select(population, count)
        elif self.selection_method == SelectionMethod.TRUNCATION:
            return self._truncation_select(population, count)
        else:
            return self._elitism_select(population, count)

    def _tournament_select(
        self,
        population: Population,
        count: int,
    ) -> List[Individual]:
        """Tournament selection."""
        selected = []

        for _ in range(count):
            tournament = random.sample(
                population.individuals,
                min(self.tournament_size, len(population.individuals)),
            )
            winner = max(tournament, key=lambda i: i.fitness)
            selected.append(winner)

        return selected

    def _roulette_select(
        self,
        population: Population,
        count: int,
    ) -> List[Individual]:
        """Roulette wheel selection."""
        total_fitness = sum(i.fitness for i in population.individuals)
        if total_fitness == 0:
            return random.sample(population.individuals, min(count, len(population.individuals)))

        selected = []

        for _ in range(count):
            spin = random.random() * total_fitness
            cumulative = 0.0

            for individual in population.individuals:
                cumulative += individual.fitness
                if cumulative >= spin:
                    selected.append(individual)
                    break

        return selected

    def _rank_select(
        self,
        population: Population,
        count: int,
    ) -> List[Individual]:
        """Rank-based selection."""
        sorted_pop = sorted(population.individuals, key=lambda i: i.fitness)

        # Assign ranks
        ranks = list(range(1, len(sorted_pop) + 1))
        total_rank = sum(ranks)

        selected = []

        for _ in range(count):
            spin = random.random() * total_rank
            cumulative = 0

            for i, individual in enumerate(sorted_pop):
                cumulative += ranks[i]
                if cumulative >= spin:
                    selected.append(individual)
                    break

        return selected

    def _truncation_select(
        self,
        population: Population,
        count: int,
    ) -> List[Individual]:
        """Truncation selection (top N)."""
        sorted_pop = sorted(
            population.individuals,
            key=lambda i: i.fitness,
            reverse=True,
        )

        top = sorted_pop[:max(count * 2, self.population_size // 2)]
        return random.sample(top, min(count, len(top)))

    def _elitism_select(
        self,
        population: Population,
        count: int,
    ) -> List[Individual]:
        """Elitism selection."""
        sorted_pop = sorted(
            population.individuals,
            key=lambda i: i.fitness,
            reverse=True,
        )

        # Always include elite
        elite = sorted_pop[:min(self.elite_count, len(sorted_pop))]

        if count <= len(elite):
            return elite[:count]

        # Add random from rest
        rest = sorted_pop[self.elite_count:]
        additional = random.sample(rest, min(count - len(elite), len(rest)))

        return elite + additional

    def breed(
        self,
        parent1: Individual,
        parent2: Individual,
    ) -> Individual:
        """
        Breed two parents to create offspring.

        Args:
            parent1: First parent
            parent2: Second parent

        Returns:
            Offspring individual
        """
        # Crossover
        if random.random() < self.crossover_rate:
            child_genome = self.encoder.crossover(
                parent1.genome,
                parent2.genome,
            )
        else:
            # Clone better parent
            child_genome = (
                parent1.genome.clone() if parent1.fitness >= parent2.fitness
                else parent2.genome.clone()
            )

        # Mutation
        if random.random() < self.mutation_rate:
            child_genome, _ = self.mutator.mutate(child_genome, num_mutations=1)

        child = Individual(
            genome=child_genome,
            parents=[parent1.genome.id, parent2.genome.id],
            generation=max(parent1.generation, parent2.generation) + 1,
        )

        self.stats["individuals_created"] += 1

        return child

    def evolve_generation(
        self,
        population: Optional[Population] = None,
        function_name: Optional[str] = None,
    ) -> Population:
        """
        Evolve population to next generation.

        Args:
            population: Population to evolve
            function_name: Function to test

        Returns:
            Evolved population
        """
        population = population or self._population
        if not population:
            raise ValueError("No population to evolve")

        # Ensure population is evaluated
        if not all(i.fitness_result for i in population.individuals):
            self.evaluate_population(population, function_name)

        new_individuals = []

        # Elitism: keep best individuals
        sorted_pop = sorted(
            population.individuals,
            key=lambda i: i.fitness,
            reverse=True,
        )

        for elite in sorted_pop[:self.elite_count]:
            elite_copy = Individual(
                genome=elite.genome.clone(),
                fitness=elite.fitness,
                fitness_result=elite.fitness_result,
                parents=[elite.genome.id],
                generation=population.generation + 1,
            )
            new_individuals.append(elite_copy)

        # Breed rest
        while len(new_individuals) < self.population_size:
            parents = self.select_parents(population, count=2)
            if len(parents) >= 2:
                child = self.breed(parents[0], parents[1])
                child.generation = population.generation + 1
                new_individuals.append(child)
            elif parents:
                # Clone and mutate single parent
                child_genome, _ = self.mutator.mutate(parents[0].genome)
                child = Individual(
                    genome=child_genome,
                    parents=[parents[0].genome.id],
                    generation=population.generation + 1,
                )
                new_individuals.append(child)

        # Update population
        population.individuals = new_individuals
        population.generation += 1

        # Evaluate new generation
        self.evaluate_population(population, function_name)

        self.stats["generations_evolved"] += 1

        return population

    def get_best(
        self,
        population: Optional[Population] = None,
        n: int = 1,
    ) -> List[Individual]:
        """Get best individuals."""
        population = population or self._population
        if not population:
            return []

        sorted_pop = sorted(
            population.individuals,
            key=lambda i: i.fitness,
            reverse=True,
        )

        return sorted_pop[:n]

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        pop_stats = {}
        if self._population:
            pop_stats = {
                "population_size": self._population.size(),
                "current_generation": self._population.generation,
                "best_fitness": self._population.best_fitness,
                "avg_fitness": self._population.avg_fitness,
                "diversity": self._population.diversity,
            }

        return {
            **self.stats,
            **pop_stats,
        }


def demo():
    """Demonstrate population manager."""
    print("=" * 60)
    print("BAEL Population Manager Demo")
    print("=" * 60)

    from .fitness_evaluator import FitnessEvaluator

    # Setup
    manager = PopulationManager(
        population_size=10,
        selection_method=SelectionMethod.TOURNAMENT,
        tournament_size=3,
        elite_count=2,
        crossover_rate=0.7,
        mutation_rate=0.3,
    )

    evaluator = FitnessEvaluator()
    evaluator.add_test_case("zero", {"n": 0}, 0)
    evaluator.add_test_case("one", {"n": 1}, 1)
    evaluator.add_test_case("ten", {"n": 10}, 55)

    manager.evaluator = evaluator

    # Seed code
    seed_code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''

    print("\nInitializing population...")
    population = manager.initialize(seed_code, variations=9)
    print(f"  Population size: {population.size()}")
    print(f"  Generation: {population.generation}")

    # Evaluate
    print("\nEvaluating population...")
    manager.evaluate_population(function_name="fibonacci")
    print(f"  Best fitness: {population.best_fitness:.2%}")
    print(f"  Avg fitness: {population.avg_fitness:.2%}")
    print(f"  Diversity: {population.diversity:.2f}")

    # Evolve
    print("\nEvolving for 3 generations...")
    for i in range(3):
        manager.evolve_generation(function_name="fibonacci")
        print(f"  Gen {population.generation}: "
              f"Best={population.best_fitness:.2%}, "
              f"Avg={population.avg_fitness:.2%}")

    # Best individual
    best = manager.get_best(n=1)
    if best:
        print(f"\nBest individual:")
        print(f"  Fitness: {best[0].fitness:.2%}")
        print(f"  Generation: {best[0].generation}")

    print(f"\nStats: {manager.get_stats()}")


if __name__ == "__main__":
    demo()
