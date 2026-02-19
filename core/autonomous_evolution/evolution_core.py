"""
⚡ EVOLUTION CORE ⚡
===================
Core evolutionary structures.

Features:
- Genes, chromosomes, genomes
- Individuals and populations
- Evolution engine
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
import uuid
import hashlib
from copy import deepcopy


@dataclass
class Gene:
    """A single gene"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Value
    value: Any = None
    value_type: str = "float"  # float, int, binary, categorical

    # Bounds (for numeric)
    min_value: float = 0.0
    max_value: float = 1.0

    # Categories (for categorical)
    categories: List[Any] = field(default_factory=list)

    # Mutation properties
    mutation_rate: float = 0.1
    mutation_strength: float = 0.1

    def mutate(self) -> 'Gene':
        """Create mutated copy"""
        mutated = deepcopy(self)

        if np.random.random() > self.mutation_rate:
            return mutated

        if self.value_type == "float":
            delta = np.random.normal(0, self.mutation_strength * (self.max_value - self.min_value))
            mutated.value = np.clip(mutated.value + delta, self.min_value, self.max_value)

        elif self.value_type == "int":
            delta = int(np.random.normal(0, self.mutation_strength * (self.max_value - self.min_value)))
            mutated.value = int(np.clip(mutated.value + delta, self.min_value, self.max_value))

        elif self.value_type == "binary":
            mutated.value = 1 - mutated.value

        elif self.value_type == "categorical" and self.categories:
            mutated.value = np.random.choice(self.categories)

        return mutated

    def crossover(self, other: 'Gene') -> Tuple['Gene', 'Gene']:
        """Crossover with another gene"""
        child1 = deepcopy(self)
        child2 = deepcopy(other)

        if self.value_type in ["float", "int"]:
            # Blend crossover
            alpha = np.random.random()
            val1 = alpha * self.value + (1 - alpha) * other.value
            val2 = (1 - alpha) * self.value + alpha * other.value

            if self.value_type == "int":
                val1, val2 = int(val1), int(val2)

            child1.value = val1
            child2.value = val2
        else:
            # Swap with 50% probability
            if np.random.random() < 0.5:
                child1.value, child2.value = child2.value, child1.value

        return child1, child2


@dataclass
class Chromosome:
    """A chromosome containing multiple genes"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    genes: List[Gene] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.genes)

    def __getitem__(self, idx: int) -> Gene:
        return self.genes[idx]

    def to_vector(self) -> np.ndarray:
        """Convert to numerical vector"""
        return np.array([g.value for g in self.genes])

    def from_vector(self, vector: np.ndarray):
        """Update from numerical vector"""
        for i, val in enumerate(vector):
            if i < len(self.genes):
                self.genes[i].value = val

    def mutate(self) -> 'Chromosome':
        """Create mutated copy"""
        mutated = Chromosome(name=self.name)
        mutated.genes = [gene.mutate() for gene in self.genes]
        return mutated

    def crossover(self, other: 'Chromosome') -> Tuple['Chromosome', 'Chromosome']:
        """Crossover with another chromosome"""
        child1 = Chromosome(name=self.name)
        child2 = Chromosome(name=other.name)

        min_len = min(len(self.genes), len(other.genes))

        for i in range(min_len):
            g1, g2 = self.genes[i].crossover(other.genes[i])
            child1.genes.append(g1)
            child2.genes.append(g2)

        return child1, child2


@dataclass
class Genome:
    """Complete genome with multiple chromosomes"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    chromosomes: Dict[str, Chromosome] = field(default_factory=dict)

    # Metadata
    generation: int = 0
    lineage: List[str] = field(default_factory=list)

    def add_chromosome(self, name: str, chromosome: Chromosome):
        """Add chromosome to genome"""
        chromosome.name = name
        self.chromosomes[name] = chromosome

    def to_dict(self) -> Dict[str, np.ndarray]:
        """Convert to dictionary of vectors"""
        return {name: chrom.to_vector() for name, chrom in self.chromosomes.items()}

    def get_hash(self) -> str:
        """Get unique hash of genome"""
        data = str(self.to_dict())
        return hashlib.md5(data.encode()).hexdigest()

    def mutate(self) -> 'Genome':
        """Create mutated copy"""
        mutated = Genome(generation=self.generation + 1)
        mutated.lineage = self.lineage + [self.id]

        for name, chrom in self.chromosomes.items():
            mutated.add_chromosome(name, chrom.mutate())

        return mutated

    def crossover(self, other: 'Genome') -> Tuple['Genome', 'Genome']:
        """Crossover with another genome"""
        child1 = Genome(generation=max(self.generation, other.generation) + 1)
        child2 = Genome(generation=max(self.generation, other.generation) + 1)

        child1.lineage = [self.id, other.id]
        child2.lineage = [other.id, self.id]

        common_chroms = set(self.chromosomes.keys()) & set(other.chromosomes.keys())

        for name in common_chroms:
            c1, c2 = self.chromosomes[name].crossover(other.chromosomes[name])
            child1.add_chromosome(name, c1)
            child2.add_chromosome(name, c2)

        return child1, child2


@dataclass
class Individual:
    """An individual in a population"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    genome: Genome = None

    # Fitness
    fitness: float = 0.0
    fitness_components: Dict[str, float] = field(default_factory=dict)

    # Evaluation status
    is_evaluated: bool = False
    evaluation_count: int = 0

    # Metadata
    birth_generation: int = 0
    age: int = 0

    # Pareto ranking (for multi-objective)
    rank: int = 0
    crowding_distance: float = 0.0

    def __lt__(self, other: 'Individual') -> bool:
        return self.fitness < other.fitness

    def dominates(self, other: 'Individual') -> bool:
        """Check if this individual dominates another (Pareto)"""
        if not self.fitness_components or not other.fitness_components:
            return self.fitness > other.fitness

        at_least_one_better = False

        for key in self.fitness_components:
            if key not in other.fitness_components:
                continue

            if self.fitness_components[key] < other.fitness_components[key]:
                return False

            if self.fitness_components[key] > other.fitness_components[key]:
                at_least_one_better = True

        return at_least_one_better


class Population:
    """A population of individuals"""

    def __init__(self, size: int = 100):
        self.size = size
        self.individuals: List[Individual] = []
        self.generation: int = 0

        # Archive
        self.hall_of_fame: List[Individual] = []
        self.hof_size: int = 10

        # Statistics
        self.stats_history: List[Dict[str, float]] = []

    def add(self, individual: Individual):
        """Add individual to population"""
        individual.birth_generation = self.generation
        self.individuals.append(individual)

    def remove(self, individual: Individual):
        """Remove individual from population"""
        if individual in self.individuals:
            self.individuals.remove(individual)

    def get_best(self, n: int = 1) -> List[Individual]:
        """Get n best individuals"""
        sorted_pop = sorted(self.individuals, key=lambda x: x.fitness, reverse=True)
        return sorted_pop[:n]

    def get_statistics(self) -> Dict[str, float]:
        """Get population statistics"""
        if not self.individuals:
            return {}

        fitnesses = [ind.fitness for ind in self.individuals]

        return {
            'mean_fitness': np.mean(fitnesses),
            'max_fitness': np.max(fitnesses),
            'min_fitness': np.min(fitnesses),
            'std_fitness': np.std(fitnesses),
            'population_size': len(self.individuals),
            'generation': self.generation
        }

    def update_hall_of_fame(self):
        """Update hall of fame with best individuals"""
        candidates = self.hall_of_fame + self.get_best(self.hof_size)
        candidates = sorted(candidates, key=lambda x: x.fitness, reverse=True)

        # Remove duplicates
        seen = set()
        unique = []
        for ind in candidates:
            hash_val = ind.genome.get_hash() if ind.genome else ind.id
            if hash_val not in seen:
                seen.add(hash_val)
                unique.append(ind)

        self.hall_of_fame = unique[:self.hof_size]

    def age_population(self):
        """Increase age of all individuals"""
        for ind in self.individuals:
            ind.age += 1

    def compute_diversity(self) -> float:
        """Compute population diversity"""
        if len(self.individuals) < 2:
            return 0.0

        # Genome-based diversity
        genomes = []
        for ind in self.individuals:
            if ind.genome:
                for chrom in ind.genome.chromosomes.values():
                    genomes.append(chrom.to_vector())

        if not genomes:
            return 0.0

        genomes = np.array(genomes)

        # Average pairwise distance
        n = len(genomes)
        total_dist = 0.0
        count = 0

        for i in range(min(n, 50)):  # Sample for efficiency
            for j in range(i + 1, min(n, 50)):
                total_dist += np.linalg.norm(genomes[i] - genomes[j])
                count += 1

        return total_dist / count if count > 0 else 0.0


class EvolutionEngine:
    """
    Core evolution engine.
    """

    def __init__(
        self,
        fitness_function: Callable[[Individual], float] = None,
        population_size: int = 100
    ):
        self.fitness_function = fitness_function
        self.population = Population(size=population_size)

        # Evolution parameters
        self.mutation_rate: float = 0.1
        self.crossover_rate: float = 0.7
        self.elite_size: int = 5

        # Callbacks
        self.on_generation: List[Callable] = []
        self.on_improvement: List[Callable] = []

    def initialize(self, genome_template: Genome):
        """Initialize population with random individuals"""
        for _ in range(self.population.size):
            genome = deepcopy(genome_template)

            # Randomize genes
            for chrom in genome.chromosomes.values():
                for gene in chrom.genes:
                    if gene.value_type == "float":
                        gene.value = np.random.uniform(gene.min_value, gene.max_value)
                    elif gene.value_type == "int":
                        gene.value = np.random.randint(int(gene.min_value), int(gene.max_value) + 1)
                    elif gene.value_type == "binary":
                        gene.value = np.random.randint(0, 2)
                    elif gene.value_type == "categorical" and gene.categories:
                        gene.value = np.random.choice(gene.categories)

            individual = Individual(genome=genome)
            self.population.add(individual)

    def evaluate(self, individual: Individual) -> float:
        """Evaluate individual fitness"""
        if self.fitness_function is None:
            return 0.0

        fitness = self.fitness_function(individual)
        individual.fitness = fitness
        individual.is_evaluated = True
        individual.evaluation_count += 1

        return fitness

    def evaluate_population(self):
        """Evaluate entire population"""
        for individual in self.population.individuals:
            if not individual.is_evaluated:
                self.evaluate(individual)

    def select_parents(self, n: int = 2) -> List[Individual]:
        """Tournament selection"""
        tournament_size = 3
        parents = []

        for _ in range(n):
            candidates = np.random.choice(
                self.population.individuals,
                size=min(tournament_size, len(self.population.individuals)),
                replace=False
            )
            winner = max(candidates, key=lambda x: x.fitness)
            parents.append(winner)

        return parents

    def create_offspring(self, parent1: Individual, parent2: Individual) -> Individual:
        """Create offspring from two parents"""
        if np.random.random() < self.crossover_rate and parent1.genome and parent2.genome:
            child_genome, _ = parent1.genome.crossover(parent2.genome)
        else:
            child_genome = deepcopy(parent1.genome)

        # Mutate
        if child_genome:
            child_genome = child_genome.mutate()

        return Individual(genome=child_genome)

    def evolve_generation(self):
        """Evolve one generation"""
        # Evaluate
        self.evaluate_population()

        # Get statistics
        stats = self.population.get_statistics()
        self.population.stats_history.append(stats)

        # Update hall of fame
        self.population.update_hall_of_fame()

        # Select elites
        elites = self.population.get_best(self.elite_size)

        # Create new generation
        new_individuals = []

        # Keep elites
        for elite in elites:
            new_individual = Individual(genome=deepcopy(elite.genome))
            new_individuals.append(new_individual)

        # Create offspring
        while len(new_individuals) < self.population.size:
            parents = self.select_parents(2)
            offspring = self.create_offspring(parents[0], parents[1])
            new_individuals.append(offspring)

        # Replace population
        self.population.individuals = new_individuals[:self.population.size]
        self.population.generation += 1
        self.population.age_population()

        # Callbacks
        for callback in self.on_generation:
            callback(self.population)

        return stats

    def run(self, generations: int = 100) -> Individual:
        """Run evolution for specified generations"""
        best_ever = None
        best_fitness = float('-inf')

        for gen in range(generations):
            stats = self.evolve_generation()

            current_best = self.population.get_best(1)[0]

            if current_best.fitness > best_fitness:
                best_fitness = current_best.fitness
                best_ever = deepcopy(current_best)

                for callback in self.on_improvement:
                    callback(best_ever)

        return best_ever


# Export all
__all__ = [
    'Gene',
    'Chromosome',
    'Genome',
    'Individual',
    'Population',
    'EvolutionEngine',
]
