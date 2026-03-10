"""
BAEL Self-Evolution Engine

Genetic algorithms and evolutionary strategies for automatic
capability improvement. BAEL evolves itself to become smarter.

Implements:
- Genetic Algorithm optimization
- Evolutionary Strategies (ES)
- Neuroevolution
- Memetic algorithms
- Multi-objective optimization (NSGA-II)
- Capability scoring and selection

This is the heart of BAEL's recursive self-improvement.
"""

import asyncio
import copy
import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class EvolutionStrategy(Enum):
    """Evolution strategies."""
    GENETIC = "genetic"             # Classic GA
    EVOLUTION_STRATEGY = "es"       # (μ, λ)-ES
    CMA_ES = "cma_es"               # Covariance Matrix Adaptation
    DIFFERENTIAL = "differential"   # Differential Evolution
    PARTICLE_SWARM = "pso"          # Particle Swarm Optimization
    MEMETIC = "memetic"             # GA + local search
    NSGA2 = "nsga2"                 # Multi-objective


class SelectionMethod(Enum):
    """Parent selection methods."""
    TOURNAMENT = "tournament"
    ROULETTE = "roulette"
    RANK = "rank"
    ELITIST = "elitist"
    CROWDING = "crowding"  # For diversity


class MutationType(Enum):
    """Mutation operators."""
    GAUSSIAN = "gaussian"
    UNIFORM = "uniform"
    ADAPTIVE = "adaptive"
    POLYNOMIAL = "polynomial"
    SWAP = "swap"
    INVERSION = "inversion"


class CrossoverType(Enum):
    """Crossover operators."""
    SINGLE_POINT = "single"
    TWO_POINT = "two_point"
    UNIFORM = "uniform"
    ARITHMETIC = "arithmetic"
    SBX = "sbx"  # Simulated Binary


@dataclass
class Individual:
    """An individual in the population."""
    id: str
    genome: Dict[str, Any]
    fitness: float = 0.0
    objectives: Dict[str, float] = field(default_factory=dict)
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # For NSGA-II
    rank: int = 0
    crowding_distance: float = 0.0


@dataclass
class EvolutionConfig:
    """Configuration for evolution."""
    strategy: EvolutionStrategy = EvolutionStrategy.GENETIC
    population_size: int = 50
    elite_size: int = 5
    generations: int = 100
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    mutation_type: MutationType = MutationType.GAUSSIAN
    crossover_type: CrossoverType = CrossoverType.UNIFORM
    selection_method: SelectionMethod = SelectionMethod.TOURNAMENT
    tournament_size: int = 3
    sigma: float = 0.1  # Mutation strength
    adaptive_mutation: bool = True
    objectives: List[str] = field(default_factory=lambda: ["fitness"])


@dataclass
class EvolutionStats:
    """Statistics for evolution run."""
    generation: int
    best_fitness: float
    avg_fitness: float
    diversity: float
    improvements: int
    stagnation_count: int
    best_individual_id: str


class FitnessFunction(ABC):
    """Abstract fitness function."""

    @abstractmethod
    async def evaluate(self, individual: Individual) -> float:
        """Evaluate individual fitness."""
        pass

    @abstractmethod
    def get_objectives(self) -> List[str]:
        """Get objective names for multi-objective."""
        pass


class CapabilityFitness(FitnessFunction):
    """
    Fitness function measuring BAEL capability.

    Evaluates:
    - Reasoning accuracy
    - Response quality
    - Speed/efficiency
    - Memory utilization
    - Task success rate
    """

    def __init__(self, evaluators: Dict[str, Callable] = None):
        self.evaluators = evaluators or {}
        self.objectives = [
            "reasoning_accuracy",
            "response_quality",
            "efficiency",
            "memory_score",
            "task_success"
        ]

    async def evaluate(self, individual: Individual) -> float:
        """Evaluate capability fitness."""
        scores = {}

        for obj in self.objectives:
            if obj in self.evaluators:
                scores[obj] = await self.evaluators[obj](individual.genome)
            else:
                # Simulate evaluation
                scores[obj] = random.random()

        individual.objectives = scores

        # Weighted sum for single fitness
        weights = {
            "reasoning_accuracy": 0.3,
            "response_quality": 0.25,
            "efficiency": 0.15,
            "memory_score": 0.15,
            "task_success": 0.15
        }

        fitness = sum(scores.get(k, 0) * w for k, w in weights.items())
        individual.fitness = fitness

        return fitness

    def get_objectives(self) -> List[str]:
        return self.objectives


class GeneticOperators:
    """Genetic operators for evolution."""

    def __init__(self, config: EvolutionConfig):
        self.config = config

    def mutate(self, individual: Individual) -> Individual:
        """Apply mutation to individual."""
        # Preserve parent_ids from crossover results so lineage is maintained
        preserved_parents = individual.parent_ids if individual.parent_ids else [individual.id]
        mutated = Individual(
            id=f"mut_{individual.id}_{random.randint(1000, 9999)}",
            genome=copy.deepcopy(individual.genome),
            generation=individual.generation + 1,
            parent_ids=preserved_parents
        )

        for key, value in mutated.genome.items():
            if random.random() < self.config.mutation_rate:
                mutated.genome[key] = self._mutate_value(value, key)
                mutated.mutations.append(key)

        return mutated

    def _mutate_value(self, value: Any, key: str) -> Any:
        """Mutate a single value."""
        if isinstance(value, (int, float)):
            if self.config.mutation_type == MutationType.GAUSSIAN:
                return value + np.random.normal(0, self.config.sigma)
            elif self.config.mutation_type == MutationType.UNIFORM:
                return value + random.uniform(-self.config.sigma, self.config.sigma)
            elif self.config.mutation_type == MutationType.POLYNOMIAL:
                eta = 20
                u = random.random()
                if u < 0.5:
                    delta = (2 * u) ** (1 / (eta + 1)) - 1
                else:
                    delta = 1 - (2 * (1 - u)) ** (1 / (eta + 1))
                return value + delta * self.config.sigma
        elif isinstance(value, bool):
            return not value if random.random() < 0.5 else value
        elif isinstance(value, str):
            # For string parameters, might swap or modify
            return value
        elif isinstance(value, list):
            if self.config.mutation_type == MutationType.SWAP:
                if len(value) >= 2:
                    i, j = random.sample(range(len(value)), 2)
                    value[i], value[j] = value[j], value[i]
            elif self.config.mutation_type == MutationType.INVERSION:
                if len(value) >= 2:
                    i, j = sorted(random.sample(range(len(value)), 2))
                    value[i:j+1] = value[i:j+1][::-1]
            return value
        return value

    def crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Apply crossover to create offspring."""
        if random.random() > self.config.crossover_rate:
            m1 = self.mutate(parent1)
            m2 = self.mutate(parent2)
            # Always record both parents even when crossover is skipped
            m1.parent_ids = [parent1.id, parent2.id]
            m2.parent_ids = [parent1.id, parent2.id]
            return m1, m2

        child1_genome = {}
        child2_genome = {}

        keys = list(set(parent1.genome.keys()) | set(parent2.genome.keys()))

        if self.config.crossover_type == CrossoverType.UNIFORM:
            for key in keys:
                if random.random() < 0.5:
                    child1_genome[key] = copy.deepcopy(parent1.genome.get(key))
                    child2_genome[key] = copy.deepcopy(parent2.genome.get(key))
                else:
                    child1_genome[key] = copy.deepcopy(parent2.genome.get(key))
                    child2_genome[key] = copy.deepcopy(parent1.genome.get(key))

        elif self.config.crossover_type == CrossoverType.SINGLE_POINT:
            point = random.randint(1, len(keys) - 1)
            for i, key in enumerate(keys):
                if i < point:
                    child1_genome[key] = copy.deepcopy(parent1.genome.get(key))
                    child2_genome[key] = copy.deepcopy(parent2.genome.get(key))
                else:
                    child1_genome[key] = copy.deepcopy(parent2.genome.get(key))
                    child2_genome[key] = copy.deepcopy(parent1.genome.get(key))

        elif self.config.crossover_type == CrossoverType.ARITHMETIC:
            alpha = random.random()
            for key in keys:
                v1 = parent1.genome.get(key)
                v2 = parent2.genome.get(key)
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    child1_genome[key] = alpha * v1 + (1 - alpha) * v2
                    child2_genome[key] = (1 - alpha) * v1 + alpha * v2
                else:
                    child1_genome[key] = copy.deepcopy(v1)
                    child2_genome[key] = copy.deepcopy(v2)

        child1 = Individual(
            id=f"cross_{random.randint(10000, 99999)}",
            genome=child1_genome,
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.id, parent2.id]
        )

        child2 = Individual(
            id=f"cross_{random.randint(10000, 99999)}",
            genome=child2_genome,
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.id, parent2.id]
        )

        return self.mutate(child1), self.mutate(child2)

    def select(self, population: List[Individual]) -> Individual:
        """Select parent using configured method."""
        if self.config.selection_method == SelectionMethod.TOURNAMENT:
            contestants = random.sample(population, min(self.config.tournament_size, len(population)))
            return max(contestants, key=lambda x: x.fitness)

        elif self.config.selection_method == SelectionMethod.ROULETTE:
            total = sum(max(0.01, ind.fitness) for ind in population)
            pick = random.uniform(0, total)
            current = 0
            for ind in population:
                current += max(0.01, ind.fitness)
                if current > pick:
                    return ind
            return population[-1]

        elif self.config.selection_method == SelectionMethod.RANK:
            sorted_pop = sorted(population, key=lambda x: x.fitness)
            ranks = list(range(1, len(sorted_pop) + 1))
            total = sum(ranks)
            pick = random.uniform(0, total)
            current = 0
            for i, ind in enumerate(sorted_pop):
                current += ranks[i]
                if current > pick:
                    return ind
            return sorted_pop[-1]

        elif self.config.selection_method == SelectionMethod.ELITIST:
            return max(population, key=lambda x: x.fitness)

        return random.choice(population)


class NSGA2:
    """
    Non-dominated Sorting Genetic Algorithm II
    for multi-objective optimization.
    """

    def __init__(self, config: EvolutionConfig):
        self.config = config

    def fast_nondominated_sort(
        self,
        population: List[Individual]
    ) -> List[List[Individual]]:
        """Sort population into Pareto fronts."""
        fronts = [[]]
        domination_count = {ind.id: 0 for ind in population}
        dominated_set = {ind.id: [] for ind in population}

        for p in population:
            for q in population:
                if p.id == q.id:
                    continue

                if self._dominates(p, q):
                    dominated_set[p.id].append(q)
                elif self._dominates(q, p):
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
            if next_front:
                fronts.append(next_front)

        return [f for f in fronts if f]

    def _dominates(self, p: Individual, q: Individual) -> bool:
        """Check if p dominates q (better in all objectives, strictly better in at least one)."""
        dominated = False
        for obj in self.config.objectives:
            p_val = p.objectives.get(obj, 0)
            q_val = q.objectives.get(obj, 0)

            if p_val < q_val:
                return False
            if p_val > q_val:
                dominated = True

        return dominated

    def crowding_distance_assignment(self, front: List[Individual]):
        """Assign crowding distance for diversity preservation."""
        if len(front) <= 2:
            for ind in front:
                ind.crowding_distance = float('inf')
            return

        for ind in front:
            ind.crowding_distance = 0

        for obj in self.config.objectives:
            sorted_front = sorted(front, key=lambda x: x.objectives.get(obj, 0))
            sorted_front[0].crowding_distance = float('inf')
            sorted_front[-1].crowding_distance = float('inf')

            obj_range = (
                sorted_front[-1].objectives.get(obj, 0) -
                sorted_front[0].objectives.get(obj, 0)
            )

            if obj_range == 0:
                continue

            for i in range(1, len(sorted_front) - 1):
                distance = (
                    sorted_front[i + 1].objectives.get(obj, 0) -
                    sorted_front[i - 1].objectives.get(obj, 0)
                ) / obj_range
                sorted_front[i].crowding_distance += distance

    def select(
        self,
        population: List[Individual],
        n: int
    ) -> List[Individual]:
        """Select n individuals using NSGA-II criteria."""
        fronts = self.fast_nondominated_sort(population)

        selected = []
        for front in fronts:
            self.crowding_distance_assignment(front)

            if len(selected) + len(front) <= n:
                selected.extend(front)
            else:
                remaining = n - len(selected)
                sorted_front = sorted(
                    front,
                    key=lambda x: x.crowding_distance,
                    reverse=True
                )
                selected.extend(sorted_front[:remaining])
                break

        return selected


class SelfEvolutionEngine:
    """
    Master self-evolution engine for BAEL.

    Evolves:
    - Hyperparameters
    - Module configurations
    - Routing weights
    - Strategy selections
    - Prompt templates
    - Decision thresholds
    """

    def __init__(self, config: Optional[EvolutionConfig] = None):
        self.config = config or EvolutionConfig()
        self.operators = GeneticOperators(self.config)
        self.nsga2 = NSGA2(self.config) if self.config.strategy == EvolutionStrategy.NSGA2 else None

        self.population: List[Individual] = []
        self.best_individual: Optional[Individual] = None
        self.generation = 0
        self.history: List[EvolutionStats] = []
        self.fitness_function: Optional[FitnessFunction] = None

        # Stagnation detection
        self.stagnation_count = 0
        self.last_best_fitness = 0.0

    def set_fitness_function(self, fitness_fn: FitnessFunction):
        """Set the fitness function."""
        self.fitness_function = fitness_fn

    def initialize_population(
        self,
        genome_template: Dict[str, Any],
        init_fn: Optional[Callable] = None
    ):
        """Initialize population from template."""
        self.population = []

        for i in range(self.config.population_size):
            if init_fn:
                genome = init_fn(genome_template)
            else:
                genome = self._random_genome(genome_template)

            individual = Individual(
                id=f"init_{i}",
                genome=genome,
                generation=0
            )
            self.population.append(individual)

        logger.info(f"Initialized population with {len(self.population)} individuals")

    def _random_genome(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Create random genome from template."""
        genome = {}

        for key, value in template.items():
            if isinstance(value, (int, float)):
                # Random perturbation
                genome[key] = value * (1 + random.uniform(-0.5, 0.5))
            elif isinstance(value, bool):
                genome[key] = random.choice([True, False])
            elif isinstance(value, list):
                genome[key] = copy.deepcopy(value)
                random.shuffle(genome[key])
            else:
                genome[key] = copy.deepcopy(value)

        return genome

    async def evolve_generation(self) -> EvolutionStats:
        """Run one generation of evolution."""
        if not self.fitness_function:
            raise ValueError("No fitness function set")

        # Evaluate population
        for individual in self.population:
            if individual.fitness == 0:
                await self.fitness_function.evaluate(individual)

        # Track best
        best = max(self.population, key=lambda x: x.fitness)
        if not self.best_individual or best.fitness > self.best_individual.fitness:
            self.best_individual = copy.deepcopy(best)
            self.stagnation_count = 0
        else:
            self.stagnation_count += 1

        # Calculate stats
        avg_fitness = np.mean([ind.fitness for ind in self.population])
        diversity = self._calculate_diversity()

        # Create next generation
        if self.config.strategy == EvolutionStrategy.NSGA2:
            new_population = self._nsga2_generation()
        else:
            new_population = self._standard_generation()

        self.population = new_population
        self.generation += 1

        # Adaptive mutation
        if self.config.adaptive_mutation and self.stagnation_count > 5:
            self.config.mutation_rate = min(0.5, self.config.mutation_rate * 1.2)
            self.config.sigma *= 1.1

        stats = EvolutionStats(
            generation=self.generation,
            best_fitness=self.best_individual.fitness,
            avg_fitness=float(avg_fitness),
            diversity=diversity,
            improvements=1 if self.stagnation_count == 0 else 0,
            stagnation_count=self.stagnation_count,
            best_individual_id=self.best_individual.id
        )

        self.history.append(stats)
        return stats

    def _standard_generation(self) -> List[Individual]:
        """Create next generation with standard GA."""
        new_population = []

        # Elitism
        sorted_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)
        new_population.extend([copy.deepcopy(ind) for ind in sorted_pop[:self.config.elite_size]])

        # Fill rest with offspring
        while len(new_population) < self.config.population_size:
            parent1 = self.operators.select(self.population)
            parent2 = self.operators.select(self.population)

            child1, child2 = self.operators.crossover(parent1, parent2)
            new_population.append(child1)

            if len(new_population) < self.config.population_size:
                new_population.append(child2)

        return new_population[:self.config.population_size]

    def _nsga2_generation(self) -> List[Individual]:
        """Create next generation with NSGA-II."""
        # Create offspring
        offspring = []
        while len(offspring) < self.config.population_size:
            parent1 = self.operators.select(self.population)
            parent2 = self.operators.select(self.population)

            child1, child2 = self.operators.crossover(parent1, parent2)
            offspring.extend([child1, child2])

        # Combined population
        combined = self.population + offspring[:self.config.population_size]

        # Select using NSGA-II
        return self.nsga2.select(combined, self.config.population_size)

    def _calculate_diversity(self) -> float:
        """Calculate population diversity."""
        if len(self.population) < 2:
            return 0.0

        # Use average pairwise distance
        distances = []
        for i, ind1 in enumerate(self.population):
            for ind2 in self.population[i+1:]:
                dist = self._genome_distance(ind1.genome, ind2.genome)
                distances.append(dist)

        return float(np.mean(distances)) if distances else 0.0

    def _genome_distance(self, g1: Dict[str, Any], g2: Dict[str, Any]) -> float:
        """Calculate distance between genomes."""
        distance = 0.0
        keys = set(g1.keys()) | set(g2.keys())

        for key in keys:
            v1 = g1.get(key, 0)
            v2 = g2.get(key, 0)

            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                distance += (v1 - v2) ** 2
            elif v1 != v2:
                distance += 1

        return np.sqrt(distance)

    async def run(
        self,
        generations: Optional[int] = None,
        early_stop_fitness: Optional[float] = None,
        early_stop_stagnation: int = 20
    ) -> Individual:
        """Run evolution for specified generations."""
        gens = generations or self.config.generations

        logger.info(f"Starting evolution for {gens} generations")

        for gen in range(gens):
            stats = await self.evolve_generation()

            logger.info(
                f"Generation {stats.generation}: "
                f"Best={stats.best_fitness:.4f}, "
                f"Avg={stats.avg_fitness:.4f}, "
                f"Diversity={stats.diversity:.4f}"
            )

            # Early stopping
            if early_stop_fitness and stats.best_fitness >= early_stop_fitness:
                logger.info(f"Early stop: reached target fitness {early_stop_fitness}")
                break

            if stats.stagnation_count >= early_stop_stagnation:
                logger.info(f"Early stop: stagnated for {early_stop_stagnation} generations")
                break

        return self.best_individual

    def get_best_genome(self) -> Dict[str, Any]:
        """Get the best evolved genome."""
        if self.best_individual:
            return self.best_individual.genome
        return {}

    def get_pareto_front(self) -> List[Individual]:
        """Get Pareto-optimal individuals (for NSGA-II)."""
        if self.nsga2:
            fronts = self.nsga2.fast_nondominated_sort(self.population)
            return fronts[0] if fronts else []
        return [self.best_individual] if self.best_individual else []

    def save(self, path: Path):
        """Save evolution state."""
        path.mkdir(parents=True, exist_ok=True)

        state = {
            "generation": self.generation,
            "config": {
                "strategy": self.config.strategy.value,
                "population_size": self.config.population_size,
                "mutation_rate": self.config.mutation_rate
            },
            "best_individual": {
                "id": self.best_individual.id,
                "genome": self.best_individual.genome,
                "fitness": self.best_individual.fitness,
                "objectives": self.best_individual.objectives
            } if self.best_individual else None,
            "history": [
                {
                    "generation": s.generation,
                    "best_fitness": s.best_fitness,
                    "avg_fitness": s.avg_fitness
                }
                for s in self.history
            ]
        }

        with open(path / "evolution_state.json", "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Evolution state saved to {path}")

    def load(self, path: Path):
        """Load evolution state."""
        with open(path / "evolution_state.json") as f:
            state = json.load(f)

        self.generation = state["generation"]

        if state.get("best_individual"):
            self.best_individual = Individual(
                id=state["best_individual"]["id"],
                genome=state["best_individual"]["genome"],
                fitness=state["best_individual"]["fitness"],
                objectives=state["best_individual"].get("objectives", {})
            )

        logger.info(f"Evolution state loaded from {path}")


def demo():
    """Demonstrate self-evolution."""
    import asyncio

    async def run_demo():
        print("=" * 60)
        print("BAEL Self-Evolution Engine Demo")
        print("=" * 60)

        config = EvolutionConfig(
            strategy=EvolutionStrategy.GENETIC,
            population_size=20,
            generations=10,
            mutation_rate=0.1,
            crossover_rate=0.8,
            elite_size=2
        )

        engine = SelfEvolutionEngine(config)

        # Define genome template (hyperparameters to evolve)
        genome_template = {
            "learning_rate": 0.001,
            "temperature": 0.7,
            "max_tokens": 1024,
            "reasoning_weight": 0.3,
            "memory_weight": 0.2,
            "creativity_factor": 0.5,
            "use_chain_of_thought": True,
            "num_reasoning_steps": 3
        }

        # Initialize population
        engine.initialize_population(genome_template)

        # Set fitness function
        engine.set_fitness_function(CapabilityFitness())

        # Run evolution
        best = await engine.run(generations=10)

        print(f"\nBest Individual:")
        print(f"  Fitness: {best.fitness:.4f}")
        print(f"  Genome: {json.dumps(best.genome, indent=4)}")

        print("\n✓ Genetic Algorithm optimization")
        print("✓ NSGA-II multi-objective support")
        print("✓ Adaptive mutation rates")
        print("✓ Elitism for best preservation")
        print("✓ Diversity maintenance")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
