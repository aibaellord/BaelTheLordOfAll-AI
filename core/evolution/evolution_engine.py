#!/usr/bin/env python3
"""
BAEL - Evolution Engine
Self-improvement and continuous evolution system.

"An agent that evolves everything we do, knows, and creates"

This module implements:
- Self-improvement loops
- Performance-driven evolution
- Code self-modification
- Knowledge evolution
- Strategy adaptation
- Capability expansion
- Fitness evaluation
- Generational improvement
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
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class EvolutionType(Enum):
    """Types of evolution."""
    PERFORMANCE = "performance"
    CAPABILITY = "capability"
    KNOWLEDGE = "knowledge"
    STRATEGY = "strategy"
    CODE = "code"
    ARCHITECTURE = "architecture"
    BEHAVIOR = "behavior"


class FitnessMetric(Enum):
    """Metrics for measuring fitness."""
    SUCCESS_RATE = "success_rate"
    EFFICIENCY = "efficiency"
    SPEED = "speed"
    ACCURACY = "accuracy"
    RESOURCE_USAGE = "resource_usage"
    ADAPTABILITY = "adaptability"
    INNOVATION = "innovation"
    COST = "cost"


class MutationType(Enum):
    """Types of mutations."""
    PARAMETER_TWEAK = "parameter_tweak"
    COMPONENT_SWAP = "component_swap"
    STRUCTURE_CHANGE = "structure_change"
    BEHAVIOR_MODIFY = "behavior_modify"
    CAPABILITY_ADD = "capability_add"
    CAPABILITY_REMOVE = "capability_remove"
    HYBRID_MERGE = "hybrid_merge"


class SelectionStrategy(Enum):
    """Selection strategies for evolution."""
    ELITISM = "elitism"
    TOURNAMENT = "tournament"
    ROULETTE = "roulette"
    RANK_BASED = "rank_based"
    STEADY_STATE = "steady_state"


class EvolutionPhase(Enum):
    """Phases of evolution."""
    EVALUATION = "evaluation"
    SELECTION = "selection"
    MUTATION = "mutation"
    CROSSOVER = "crossover"
    VALIDATION = "validation"
    INTEGRATION = "integration"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Gene:
    """A single gene representing a component or parameter."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    value: Any = None
    gene_type: str = "parameter"
    mutable: bool = True
    mutation_range: Tuple[float, float] = (0.8, 1.2)
    constraints: Dict[str, Any] = field(default_factory=dict)

    def mutate(self, rate: float = 0.1) -> "Gene":
        """Create a mutated copy of this gene."""
        if not self.mutable or random.random() > rate:
            return copy.deepcopy(self)

        mutated = copy.deepcopy(self)

        if isinstance(self.value, (int, float)):
            factor = random.uniform(*self.mutation_range)
            mutated.value = self.value * factor

            # Apply constraints
            if "min" in self.constraints:
                mutated.value = max(mutated.value, self.constraints["min"])
            if "max" in self.constraints:
                mutated.value = min(mutated.value, self.constraints["max"])

        elif isinstance(self.value, bool):
            mutated.value = not self.value

        elif isinstance(self.value, str) and "options" in self.constraints:
            options = self.constraints["options"]
            mutated.value = random.choice(options)

        return mutated


@dataclass
class Genome:
    """A complete genome representing a system configuration."""
    id: str = field(default_factory=lambda: str(uuid4()))
    genes: Dict[str, Gene] = field(default_factory=dict)
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_gene(self, gene: Gene) -> None:
        """Add a gene to the genome."""
        self.genes[gene.name] = gene

    def get_gene(self, name: str) -> Optional[Gene]:
        """Get a gene by name."""
        return self.genes.get(name)

    def mutate(self, mutation_rate: float = 0.1) -> "Genome":
        """Create a mutated copy of this genome."""
        mutated = Genome(
            generation=self.generation + 1,
            parent_ids=[self.id]
        )

        for name, gene in self.genes.items():
            mutated.genes[name] = gene.mutate(mutation_rate)

        return mutated

    @staticmethod
    def crossover(genome1: "Genome", genome2: "Genome") -> "Genome":
        """Create offspring from two parent genomes."""
        offspring = Genome(
            generation=max(genome1.generation, genome2.generation) + 1,
            parent_ids=[genome1.id, genome2.id]
        )

        # Combine genes from both parents
        all_genes = set(genome1.genes.keys()) | set(genome2.genes.keys())

        for name in all_genes:
            gene1 = genome1.genes.get(name)
            gene2 = genome2.genes.get(name)

            if gene1 and gene2:
                # Both parents have this gene - random selection
                offspring.genes[name] = copy.deepcopy(
                    random.choice([gene1, gene2])
                )
            elif gene1:
                offspring.genes[name] = copy.deepcopy(gene1)
            elif gene2:
                offspring.genes[name] = copy.deepcopy(gene2)

        return offspring

    def get_hash(self) -> str:
        """Get a hash representing this genome."""
        gene_data = {name: str(gene.value) for name, gene in self.genes.items()}
        return hashlib.md5(json.dumps(gene_data, sort_keys=True).encode()).hexdigest()[:12]


@dataclass
class FitnessScore:
    """Fitness scores for an individual."""
    overall: float = 0.0
    metrics: Dict[FitnessMetric, float] = field(default_factory=dict)
    weights: Dict[FitnessMetric, float] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.now)

    def calculate_overall(self) -> float:
        """Calculate overall fitness from weighted metrics."""
        if not self.metrics:
            return 0.0

        total_weight = sum(self.weights.get(m, 1.0) for m in self.metrics)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(
            score * self.weights.get(metric, 1.0)
            for metric, score in self.metrics.items()
        )

        self.overall = weighted_sum / total_weight
        return self.overall


@dataclass
class Individual:
    """An individual in the evolutionary population."""
    id: str = field(default_factory=lambda: str(uuid4()))
    genome: Genome = field(default_factory=Genome)
    fitness: FitnessScore = field(default_factory=FitnessScore)
    is_elite: bool = False
    survived_generations: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def __lt__(self, other: "Individual") -> bool:
        return self.fitness.overall < other.fitness.overall


@dataclass
class EvolutionConfig:
    """Configuration for evolution."""
    population_size: int = 50
    elite_size: int = 5
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    selection_strategy: SelectionStrategy = SelectionStrategy.TOURNAMENT
    tournament_size: int = 5
    max_generations: int = 100
    target_fitness: float = 0.95
    stagnation_threshold: int = 10
    diversity_threshold: float = 0.3
    fitness_weights: Dict[FitnessMetric, float] = field(default_factory=dict)


@dataclass
class EvolutionState:
    """Current state of evolution."""
    generation: int = 0
    best_fitness: float = 0.0
    average_fitness: float = 0.0
    diversity: float = 1.0
    stagnation_count: int = 0
    improvements: List[Dict[str, Any]] = field(default_factory=list)
    phase: EvolutionPhase = EvolutionPhase.EVALUATION


@dataclass
class EvolutionResult:
    """Result of evolution."""
    best_individual: Optional[Individual] = None
    final_generation: int = 0
    improvements_made: int = 0
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    total_evaluations: int = 0
    convergence_reason: str = ""


# =============================================================================
# FITNESS EVALUATORS
# =============================================================================

class FitnessEvaluator(ABC):
    """Base class for fitness evaluation."""

    @abstractmethod
    async def evaluate(self, individual: Individual) -> FitnessScore:
        """Evaluate an individual's fitness."""
        pass


class PerformanceEvaluator(FitnessEvaluator):
    """Evaluate based on performance metrics."""

    def __init__(self):
        self.test_cases: List[Dict[str, Any]] = []
        self.benchmark_scores: Dict[str, float] = {}

    async def evaluate(self, individual: Individual) -> FitnessScore:
        """Evaluate performance fitness."""
        score = FitnessScore()

        # Evaluate success rate
        success_count = 0
        for test_case in self.test_cases:
            result = await self._run_test(individual, test_case)
            if result["success"]:
                success_count += 1

        if self.test_cases:
            score.metrics[FitnessMetric.SUCCESS_RATE] = success_count / len(self.test_cases)
        else:
            score.metrics[FitnessMetric.SUCCESS_RATE] = 0.5  # Default

        # Evaluate efficiency
        score.metrics[FitnessMetric.EFFICIENCY] = self._evaluate_efficiency(individual)

        # Evaluate speed
        score.metrics[FitnessMetric.SPEED] = self._evaluate_speed(individual)

        score.calculate_overall()
        return score

    async def _run_test(self, individual: Individual, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a test case."""
        # Simulate test execution
        return {"success": random.random() > 0.3}

    def _evaluate_efficiency(self, individual: Individual) -> float:
        """Evaluate efficiency."""
        efficiency_gene = individual.genome.get_gene("efficiency")
        if efficiency_gene:
            return min(1.0, max(0.0, efficiency_gene.value))
        return 0.5

    def _evaluate_speed(self, individual: Individual) -> float:
        """Evaluate speed."""
        speed_gene = individual.genome.get_gene("speed")
        if speed_gene:
            return min(1.0, max(0.0, speed_gene.value))
        return 0.5


class CostEvaluator(FitnessEvaluator):
    """Evaluate based on cost efficiency - ZERO COST IS MAXIMUM FITNESS."""

    async def evaluate(self, individual: Individual) -> FitnessScore:
        """Evaluate cost fitness - lower cost = higher fitness."""
        score = FitnessScore()

        # Cost gene - inverted (lower is better)
        cost_gene = individual.genome.get_gene("cost")
        if cost_gene and cost_gene.value is not None:
            # Zero cost = maximum fitness
            cost = float(cost_gene.value)
            score.metrics[FitnessMetric.COST] = 1.0 if cost == 0 else 1.0 / (1.0 + cost)
        else:
            score.metrics[FitnessMetric.COST] = 1.0  # Assume free

        # Resource usage
        resource_gene = individual.genome.get_gene("resource_usage")
        if resource_gene:
            score.metrics[FitnessMetric.RESOURCE_USAGE] = 1.0 - min(1.0, resource_gene.value)
        else:
            score.metrics[FitnessMetric.RESOURCE_USAGE] = 0.5

        score.calculate_overall()
        return score


class CapabilityEvaluator(FitnessEvaluator):
    """Evaluate based on capabilities."""

    def __init__(self):
        self.required_capabilities: List[str] = []
        self.desired_capabilities: List[str] = []

    async def evaluate(self, individual: Individual) -> FitnessScore:
        """Evaluate capability fitness."""
        score = FitnessScore()

        # Get capabilities from genome
        capabilities = set()
        cap_gene = individual.genome.get_gene("capabilities")
        if cap_gene and isinstance(cap_gene.value, list):
            capabilities = set(cap_gene.value)

        # Required capabilities (must have all)
        if self.required_capabilities:
            required_met = sum(1 for c in self.required_capabilities if c in capabilities)
            score.metrics[FitnessMetric.ACCURACY] = required_met / len(self.required_capabilities)
        else:
            score.metrics[FitnessMetric.ACCURACY] = 1.0

        # Desired capabilities (bonus)
        if self.desired_capabilities:
            desired_met = sum(1 for c in self.desired_capabilities if c in capabilities)
            score.metrics[FitnessMetric.ADAPTABILITY] = desired_met / len(self.desired_capabilities)
        else:
            score.metrics[FitnessMetric.ADAPTABILITY] = 0.5

        score.calculate_overall()
        return score


# =============================================================================
# SELECTION STRATEGIES
# =============================================================================

class Selector:
    """Selection strategy implementations."""

    @staticmethod
    def elitism(population: List[Individual], count: int) -> List[Individual]:
        """Select top individuals."""
        sorted_pop = sorted(population, reverse=True)
        return sorted_pop[:count]

    @staticmethod
    def tournament(
        population: List[Individual],
        count: int,
        tournament_size: int = 5
    ) -> List[Individual]:
        """Tournament selection."""
        selected = []
        for _ in range(count):
            tournament = random.sample(population, min(tournament_size, len(population)))
            winner = max(tournament, key=lambda x: x.fitness.overall)
            selected.append(winner)
        return selected

    @staticmethod
    def roulette(population: List[Individual], count: int) -> List[Individual]:
        """Roulette wheel selection."""
        total_fitness = sum(i.fitness.overall for i in population)
        if total_fitness == 0:
            return random.sample(population, min(count, len(population)))

        selected = []
        for _ in range(count):
            pick = random.uniform(0, total_fitness)
            current = 0
            for individual in population:
                current += individual.fitness.overall
                if current >= pick:
                    selected.append(individual)
                    break
        return selected

    @staticmethod
    def rank_based(population: List[Individual], count: int) -> List[Individual]:
        """Rank-based selection."""
        sorted_pop = sorted(population, key=lambda x: x.fitness.overall)
        n = len(sorted_pop)

        # Assign selection probabilities based on rank
        total_rank = n * (n + 1) / 2
        probabilities = [(i + 1) / total_rank for i in range(n)]

        selected = []
        for _ in range(count):
            r = random.random()
            cumulative = 0
            for i, prob in enumerate(probabilities):
                cumulative += prob
                if cumulative >= r:
                    selected.append(sorted_pop[i])
                    break
        return selected


# =============================================================================
# MUTATION OPERATORS
# =============================================================================

class MutationOperator:
    """Mutation operators for genome modification."""

    @staticmethod
    def parameter_tweak(genome: Genome, rate: float = 0.1) -> Genome:
        """Tweak numerical parameters."""
        return genome.mutate(rate)

    @staticmethod
    def component_swap(genome: Genome, options: Dict[str, List[Any]]) -> Genome:
        """Swap components with alternatives."""
        mutated = copy.deepcopy(genome)
        mutated.generation += 1
        mutated.parent_ids = [genome.id]

        for gene_name, alternatives in options.items():
            if gene_name in mutated.genes and random.random() < 0.3:
                mutated.genes[gene_name].value = random.choice(alternatives)

        return mutated

    @staticmethod
    def capability_add(genome: Genome, available: List[str]) -> Genome:
        """Add a new capability."""
        mutated = copy.deepcopy(genome)
        mutated.generation += 1
        mutated.parent_ids = [genome.id]

        cap_gene = mutated.get_gene("capabilities")
        if cap_gene and isinstance(cap_gene.value, list):
            # Find capabilities not yet present
            current = set(cap_gene.value)
            new_caps = [c for c in available if c not in current]
            if new_caps:
                cap_gene.value = list(current | {random.choice(new_caps)})
        else:
            # Create capabilities gene
            mutated.add_gene(Gene(
                name="capabilities",
                value=[random.choice(available)],
                gene_type="capability_list"
            ))

        return mutated

    @staticmethod
    def capability_remove(genome: Genome) -> Genome:
        """Remove a capability."""
        mutated = copy.deepcopy(genome)
        mutated.generation += 1
        mutated.parent_ids = [genome.id]

        cap_gene = mutated.get_gene("capabilities")
        if cap_gene and isinstance(cap_gene.value, list) and len(cap_gene.value) > 1:
            cap_gene.value.remove(random.choice(cap_gene.value))

        return mutated


# =============================================================================
# EVOLUTION ENGINE
# =============================================================================

class EvolutionEngine:
    """
    The main evolution engine for self-improvement.

    Implements genetic algorithms and evolutionary strategies
    for continuous improvement of BAEL systems.
    """

    def __init__(self, config: EvolutionConfig = None):
        self.config = config or EvolutionConfig()
        self.population: List[Individual] = []
        self.state = EvolutionState()
        self.evaluators: List[FitnessEvaluator] = []
        self.selector = Selector()
        self.history: List[Dict[str, Any]] = []
        self.best_ever: Optional[Individual] = None

    def add_evaluator(self, evaluator: FitnessEvaluator) -> None:
        """Add a fitness evaluator."""
        self.evaluators.append(evaluator)

    def initialize_population(self, template_genome: Genome = None) -> None:
        """Initialize the population."""
        self.population = []

        for _ in range(self.config.population_size):
            if template_genome:
                # Create variations of template
                genome = template_genome.mutate(0.3)
            else:
                genome = self._create_random_genome()

            individual = Individual(genome=genome)
            self.population.append(individual)

        self.state = EvolutionState()
        logger.info(f"Initialized population with {len(self.population)} individuals")

    def _create_random_genome(self) -> Genome:
        """Create a random genome."""
        genome = Genome()

        # Add standard genes
        genome.add_gene(Gene(
            name="efficiency",
            value=random.uniform(0.5, 1.0),
            mutation_range=(0.9, 1.1),
            constraints={"min": 0.0, "max": 1.0}
        ))

        genome.add_gene(Gene(
            name="speed",
            value=random.uniform(0.5, 1.0),
            mutation_range=(0.9, 1.1),
            constraints={"min": 0.0, "max": 1.0}
        ))

        genome.add_gene(Gene(
            name="cost",
            value=0.0,  # ZERO COST - always free
            mutable=False  # Cost should stay at zero
        ))

        genome.add_gene(Gene(
            name="resource_usage",
            value=random.uniform(0.1, 0.5),
            mutation_range=(0.8, 1.2),
            constraints={"min": 0.0, "max": 1.0}
        ))

        genome.add_gene(Gene(
            name="capabilities",
            value=["process", "analyze", "optimize"],
            gene_type="capability_list"
        ))

        return genome

    async def evaluate_population(self) -> None:
        """Evaluate fitness of all individuals."""
        self.state.phase = EvolutionPhase.EVALUATION

        for individual in self.population:
            combined_score = FitnessScore()
            combined_score.weights = self.config.fitness_weights.copy()

            for evaluator in self.evaluators:
                score = await evaluator.evaluate(individual)
                for metric, value in score.metrics.items():
                    if metric in combined_score.metrics:
                        combined_score.metrics[metric] = (combined_score.metrics[metric] + value) / 2
                    else:
                        combined_score.metrics[metric] = value

            combined_score.calculate_overall()
            individual.fitness = combined_score

        # Update state
        self.state.best_fitness = max(i.fitness.overall for i in self.population)
        self.state.average_fitness = sum(i.fitness.overall for i in self.population) / len(self.population)

        # Update best ever
        current_best = max(self.population, key=lambda x: x.fitness.overall)
        if self.best_ever is None or current_best.fitness.overall > self.best_ever.fitness.overall:
            self.best_ever = copy.deepcopy(current_best)
            self.state.stagnation_count = 0
        else:
            self.state.stagnation_count += 1

    def select_parents(self) -> List[Individual]:
        """Select parents for reproduction."""
        self.state.phase = EvolutionPhase.SELECTION

        strategy = self.config.selection_strategy
        count = self.config.population_size - self.config.elite_size

        if strategy == SelectionStrategy.ELITISM:
            return Selector.elitism(self.population, count)
        elif strategy == SelectionStrategy.TOURNAMENT:
            return Selector.tournament(self.population, count, self.config.tournament_size)
        elif strategy == SelectionStrategy.ROULETTE:
            return Selector.roulette(self.population, count)
        elif strategy == SelectionStrategy.RANK_BASED:
            return Selector.rank_based(self.population, count)
        else:
            return Selector.tournament(self.population, count)

    def create_offspring(self, parents: List[Individual]) -> List[Individual]:
        """Create offspring through crossover and mutation."""
        self.state.phase = EvolutionPhase.CROSSOVER
        offspring = []

        while len(offspring) < len(parents):
            # Select two parents
            if len(parents) >= 2:
                parent1, parent2 = random.sample(parents, 2)
            else:
                parent1 = parent2 = parents[0]

            # Crossover
            if random.random() < self.config.crossover_rate:
                child_genome = Genome.crossover(parent1.genome, parent2.genome)
            else:
                child_genome = copy.deepcopy(random.choice([parent1.genome, parent2.genome]))

            # Mutation
            self.state.phase = EvolutionPhase.MUTATION
            child_genome = child_genome.mutate(self.config.mutation_rate)

            child = Individual(genome=child_genome)
            offspring.append(child)

        return offspring

    def replace_population(self, offspring: List[Individual]) -> None:
        """Replace population with new generation."""
        # Keep elites
        elites = Selector.elitism(self.population, self.config.elite_size)
        for elite in elites:
            elite.is_elite = True
            elite.survived_generations += 1

        # New population = elites + offspring
        self.population = elites + offspring[:self.config.population_size - len(elites)]
        self.state.generation += 1

    def calculate_diversity(self) -> float:
        """Calculate population diversity."""
        if len(self.population) < 2:
            return 1.0

        # Use genome hashes to measure diversity
        hashes = set()
        for individual in self.population:
            hashes.add(individual.genome.get_hash())

        self.state.diversity = len(hashes) / len(self.population)
        return self.state.diversity

    async def evolve_generation(self) -> None:
        """Evolve one generation."""
        # Evaluate
        await self.evaluate_population()

        # Record history
        self.history.append({
            "generation": self.state.generation,
            "best_fitness": self.state.best_fitness,
            "average_fitness": self.state.average_fitness,
            "diversity": self.calculate_diversity(),
            "timestamp": datetime.now().isoformat()
        })

        # Select parents
        parents = self.select_parents()

        # Create offspring
        offspring = self.create_offspring(parents)

        # Validate offspring
        self.state.phase = EvolutionPhase.VALIDATION
        valid_offspring = [o for o in offspring if self._validate_individual(o)]

        # Replace population
        self.state.phase = EvolutionPhase.INTEGRATION
        self.replace_population(valid_offspring)

        logger.info(
            f"Generation {self.state.generation}: "
            f"Best={self.state.best_fitness:.4f}, "
            f"Avg={self.state.average_fitness:.4f}, "
            f"Diversity={self.state.diversity:.4f}"
        )

    def _validate_individual(self, individual: Individual) -> bool:
        """Validate an individual."""
        # Check for required genes
        if not individual.genome.get_gene("cost"):
            return False

        # Ensure cost stays at zero
        cost_gene = individual.genome.get_gene("cost")
        if cost_gene and cost_gene.value != 0:
            cost_gene.value = 0  # Force zero cost

        return True

    def should_stop(self) -> Tuple[bool, str]:
        """Check if evolution should stop."""
        if self.state.generation >= self.config.max_generations:
            return True, "max_generations_reached"

        if self.state.best_fitness >= self.config.target_fitness:
            return True, "target_fitness_achieved"

        if self.state.stagnation_count >= self.config.stagnation_threshold:
            return True, "stagnation_detected"

        if self.state.diversity < self.config.diversity_threshold:
            # Inject diversity
            self._inject_diversity()

        return False, ""

    def _inject_diversity(self) -> None:
        """Inject diversity into population."""
        # Replace worst individuals with random ones
        replace_count = self.config.population_size // 5
        sorted_pop = sorted(self.population, key=lambda x: x.fitness.overall)

        for i in range(replace_count):
            sorted_pop[i] = Individual(genome=self._create_random_genome())

        self.population = sorted_pop
        logger.info(f"Injected diversity: replaced {replace_count} individuals")

    async def evolve(
        self,
        template_genome: Genome = None,
        callback: Callable[[EvolutionState], None] = None
    ) -> EvolutionResult:
        """Run full evolution."""
        # Initialize
        self.initialize_population(template_genome)

        # Evolution loop
        while True:
            await self.evolve_generation()

            if callback:
                callback(self.state)

            should_stop, reason = self.should_stop()
            if should_stop:
                break

            # Allow other tasks
            await asyncio.sleep(0)

        # Compile result
        result = EvolutionResult(
            best_individual=self.best_ever,
            final_generation=self.state.generation,
            improvements_made=len(self.state.improvements),
            evolution_history=self.history,
            total_evaluations=self.state.generation * self.config.population_size,
            convergence_reason=reason
        )

        return result

    def get_best_individual(self) -> Optional[Individual]:
        """Get the best individual."""
        if not self.population:
            return None
        return max(self.population, key=lambda x: x.fitness.overall)

    def get_status(self) -> Dict[str, Any]:
        """Get evolution status."""
        return {
            "generation": self.state.generation,
            "population_size": len(self.population),
            "best_fitness": self.state.best_fitness,
            "average_fitness": self.state.average_fitness,
            "diversity": self.state.diversity,
            "stagnation": self.state.stagnation_count,
            "phase": self.state.phase.value,
            "best_ever": self.best_ever.fitness.overall if self.best_ever else 0
        }


# =============================================================================
# SELF-IMPROVEMENT SYSTEM
# =============================================================================

class SelfImprovementSystem:
    """
    System for continuous self-improvement of BAEL.

    Orchestrates evolution engines for different aspects
    of the system to achieve perpetual improvement.
    """

    def __init__(self):
        self.engines: Dict[EvolutionType, EvolutionEngine] = {}
        self.improvement_log: List[Dict[str, Any]] = []
        self.active = False
        self.improvement_cycle = 0

    def add_evolution_engine(
        self,
        evolution_type: EvolutionType,
        engine: EvolutionEngine
    ) -> None:
        """Add an evolution engine for a specific type."""
        self.engines[evolution_type] = engine

    async def run_improvement_cycle(self) -> Dict[str, Any]:
        """Run one improvement cycle across all engines."""
        self.improvement_cycle += 1
        results = {}

        for evo_type, engine in self.engines.items():
            logger.info(f"Running {evo_type.value} evolution...")
            result = await engine.evolve()
            results[evo_type.value] = {
                "final_generation": result.final_generation,
                "best_fitness": result.best_individual.fitness.overall if result.best_individual else 0,
                "reason": result.convergence_reason
            }

        # Log improvement
        self.improvement_log.append({
            "cycle": self.improvement_cycle,
            "results": results,
            "timestamp": datetime.now().isoformat()
        })

        return results

    async def continuous_improvement(
        self,
        interval_seconds: int = 3600,
        max_cycles: int = None
    ) -> None:
        """Run continuous improvement loop."""
        self.active = True
        cycles = 0

        while self.active:
            if max_cycles and cycles >= max_cycles:
                break

            await self.run_improvement_cycle()
            cycles += 1

            if self.active:
                await asyncio.sleep(interval_seconds)

        logger.info(f"Continuous improvement stopped after {cycles} cycles")

    def stop(self) -> None:
        """Stop continuous improvement."""
        self.active = False

    def get_improvement_summary(self) -> Dict[str, Any]:
        """Get summary of improvements."""
        return {
            "total_cycles": self.improvement_cycle,
            "engines": list(self.engines.keys()),
            "recent_improvements": self.improvement_log[-5:],
            "active": self.active
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Evolution Engine."""
    print("=" * 70)
    print("BAEL - EVOLUTION ENGINE DEMO")
    print("Self-Improvement Through Evolutionary Algorithms")
    print("=" * 70)
    print()

    # Create evolution engine with configuration
    config = EvolutionConfig(
        population_size=20,
        elite_size=3,
        mutation_rate=0.15,
        crossover_rate=0.8,
        max_generations=10,  # Short demo
        target_fitness=0.95,
        selection_strategy=SelectionStrategy.TOURNAMENT,
        fitness_weights={
            FitnessMetric.SUCCESS_RATE: 1.0,
            FitnessMetric.EFFICIENCY: 0.8,
            FitnessMetric.COST: 2.0  # Heavily weight cost (zero cost is critical)
        }
    )

    engine = EvolutionEngine(config)

    # Add evaluators
    print("1. ADDING FITNESS EVALUATORS:")
    print("-" * 40)

    engine.add_evaluator(PerformanceEvaluator())
    engine.add_evaluator(CostEvaluator())
    engine.add_evaluator(CapabilityEvaluator())

    print("   Added: PerformanceEvaluator")
    print("   Added: CostEvaluator (zero-cost optimized)")
    print("   Added: CapabilityEvaluator")
    print()

    # Run evolution
    print("2. RUNNING EVOLUTION:")
    print("-" * 40)

    def progress_callback(state: EvolutionState):
        print(f"   Gen {state.generation}: best={state.best_fitness:.4f}, avg={state.average_fitness:.4f}")

    result = await engine.evolve(callback=progress_callback)
    print()

    # Show results
    print("3. EVOLUTION RESULTS:")
    print("-" * 40)

    print(f"   Final generation: {result.final_generation}")
    print(f"   Convergence reason: {result.convergence_reason}")
    print(f"   Total evaluations: {result.total_evaluations}")

    if result.best_individual:
        best = result.best_individual
        print(f"\n   Best Individual:")
        print(f"   - Fitness: {best.fitness.overall:.4f}")
        print(f"   - Genes:")
        for name, gene in list(best.genome.genes.items())[:4]:
            print(f"     - {name}: {gene.value}")
    print()

    # Show evolution history
    print("4. EVOLUTION HISTORY:")
    print("-" * 40)

    for record in result.evolution_history[:5]:
        print(f"   Gen {record['generation']}: best={record['best_fitness']:.4f}, diversity={record['diversity']:.4f}")
    print()

    # Demonstrate self-improvement system
    print("5. SELF-IMPROVEMENT SYSTEM:")
    print("-" * 40)

    improvement_system = SelfImprovementSystem()

    # Add engines for different evolution types
    improvement_system.add_evolution_engine(
        EvolutionType.PERFORMANCE,
        EvolutionEngine(EvolutionConfig(population_size=10, max_generations=5))
    )
    improvement_system.add_evolution_engine(
        EvolutionType.CAPABILITY,
        EvolutionEngine(EvolutionConfig(population_size=10, max_generations=5))
    )

    # Add evaluators to these engines
    improvement_system.engines[EvolutionType.PERFORMANCE].add_evaluator(PerformanceEvaluator())
    improvement_system.engines[EvolutionType.CAPABILITY].add_evaluator(CapabilityEvaluator())

    print("   Running improvement cycle...")
    cycle_results = await improvement_system.run_improvement_cycle()

    for evo_type, result in cycle_results.items():
        print(f"   {evo_type}: gen={result['final_generation']}, fitness={result['best_fitness']:.4f}")
    print()

    # Summary
    print("6. IMPROVEMENT SUMMARY:")
    print("-" * 40)

    summary = improvement_system.get_improvement_summary()
    print(f"   Total cycles: {summary['total_cycles']}")
    print(f"   Active engines: {[e.value for e in summary['engines']]}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Evolution Engine Ready for Continuous Improvement")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
