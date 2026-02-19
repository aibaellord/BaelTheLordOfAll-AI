"""
BAEL Evolution Orchestrator
============================

Orchestrates the evolution process.
Coordinates all evolution components.

Features:
- Evolution configuration
- Multi-objective optimization
- Convergence detection
- Checkpoint management
- Evolution visualization
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .code_genome import CodeGenome, GenomeEncoder
from .fitness_evaluator import FitnessCriteria, FitnessEvaluator, FitnessMetric
from .mutation_engine import MutationEngine, MutationStrategy
from .population_manager import (Individual, Population, PopulationManager,
                                 SelectionMethod)

logger = logging.getLogger(__name__)


class StopCondition(Enum):
    """Evolution stop conditions."""
    MAX_GENERATIONS = "max_generations"
    FITNESS_THRESHOLD = "fitness_threshold"
    CONVERGENCE = "convergence"
    TIME_LIMIT = "time_limit"
    MANUAL = "manual"


@dataclass
class EvolutionConfig:
    """Configuration for evolution."""
    # Population
    population_size: int = 50
    elite_count: int = 2

    # Selection
    selection_method: SelectionMethod = SelectionMethod.TOURNAMENT
    tournament_size: int = 5

    # Genetic operators
    crossover_rate: float = 0.7
    mutation_rate: float = 0.1
    mutation_strategy: MutationStrategy = MutationStrategy.CONSERVATIVE

    # Stop conditions
    max_generations: int = 100
    fitness_threshold: float = 0.95
    convergence_generations: int = 10
    time_limit_seconds: float = 3600.0

    # Fitness
    fitness_criteria: FitnessCriteria = field(default_factory=FitnessCriteria)

    # Checkpointing
    checkpoint_interval: int = 10
    checkpoint_dir: str = "./checkpoints"


@dataclass
class GenerationStats:
    """Statistics for a generation."""
    generation: int

    # Fitness
    best_fitness: float = 0.0
    avg_fitness: float = 0.0
    worst_fitness: float = 0.0

    # Diversity
    diversity: float = 0.0

    # Performance
    evaluation_time_ms: float = 0.0

    # Improvements
    improvement: float = 0.0
    stagnant_generations: int = 0


@dataclass
class EvolutionResult:
    """Result of evolution run."""
    run_id: str

    # Best solution
    best_genome: Optional[CodeGenome] = None
    best_fitness: float = 0.0
    best_code: str = ""

    # Stop condition
    stop_condition: StopCondition = StopCondition.MAX_GENERATIONS

    # Stats
    total_generations: int = 0
    total_time_seconds: float = 0.0
    evaluations_performed: int = 0

    # History
    generation_stats: List[GenerationStats] = field(default_factory=list)
    fitness_history: List[float] = field(default_factory=list)

    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class EvolutionOrchestrator:
    """
    Evolution orchestrator for BAEL.

    Coordinates the genetic programming process.
    """

    def __init__(
        self,
        config: Optional[EvolutionConfig] = None,
    ):
        self.config = config or EvolutionConfig()

        # Components
        self.encoder = GenomeEncoder()
        self.mutator = MutationEngine(
            mutation_rate=self.config.mutation_rate,
            strategy=self.config.mutation_strategy,
        )
        self.evaluator = FitnessEvaluator(
            criteria=self.config.fitness_criteria,
        )
        self.population_manager = PopulationManager(
            population_size=self.config.population_size,
            selection_method=self.config.selection_method,
            tournament_size=self.config.tournament_size,
            elite_count=self.config.elite_count,
            crossover_rate=self.config.crossover_rate,
            mutation_rate=self.config.mutation_rate,
        )
        self.population_manager.evaluator = self.evaluator

        # State
        self._running = False
        self._current_result: Optional[EvolutionResult] = None

        # Callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            "on_generation": [],
            "on_improvement": [],
            "on_complete": [],
        }

        # Stats
        self.stats = {
            "evolution_runs": 0,
            "total_generations": 0,
            "solutions_found": 0,
        }

    def add_test_case(
        self,
        name: str,
        inputs: Dict[str, Any],
        expected: Any,
    ) -> None:
        """Add a test case for fitness evaluation."""
        self.evaluator.add_test_case(name, inputs, expected)

    def register_callback(
        self,
        event: str,
        callback: Callable,
    ) -> None:
        """Register a callback for an event."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Callback error: {e}")

    def evolve(
        self,
        seed_code: str,
        function_name: Optional[str] = None,
    ) -> EvolutionResult:
        """
        Run evolution.

        Args:
            seed_code: Initial code to evolve
            function_name: Name of function to optimize

        Returns:
            Evolution result
        """
        run_id = hashlib.md5(
            f"{seed_code[:50]}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        result = EvolutionResult(run_id=run_id)
        self._current_result = result
        self._running = True

        start_time = time.time()

        try:
            # Initialize population
            population = self.population_manager.initialize(seed_code)

            # Initial evaluation
            self.population_manager.evaluate_population(
                function_name=function_name,
            )

            result.fitness_history.append(population.best_fitness)

            stagnant_count = 0
            prev_best = 0.0

            # Evolution loop
            while self._running:
                gen_start = time.time()

                # Check stop conditions
                stop = self._check_stop_conditions(
                    population, result, start_time, stagnant_count
                )
                if stop:
                    result.stop_condition = stop
                    break

                # Evolve generation
                self.population_manager.evolve_generation(
                    function_name=function_name,
                )

                # Record stats
                gen_time = (time.time() - gen_start) * 1000
                improvement = population.best_fitness - prev_best

                if improvement <= 0.001:
                    stagnant_count += 1
                else:
                    stagnant_count = 0

                gen_stats = GenerationStats(
                    generation=population.generation,
                    best_fitness=population.best_fitness,
                    avg_fitness=population.avg_fitness,
                    worst_fitness=min(i.fitness for i in population.individuals),
                    diversity=population.diversity,
                    evaluation_time_ms=gen_time,
                    improvement=improvement,
                    stagnant_generations=stagnant_count,
                )

                result.generation_stats.append(gen_stats)
                result.fitness_history.append(population.best_fitness)
                result.total_generations = population.generation

                # Emit events
                self._emit("on_generation", gen_stats)

                if improvement > 0.01:
                    self._emit("on_improvement", population.best_individual)

                prev_best = population.best_fitness

                # Checkpoint
                if (population.generation % self.config.checkpoint_interval == 0):
                    self._save_checkpoint(population, result)

            # Finalize result
            best = self.population_manager.get_best(n=1)
            if best:
                result.best_genome = best[0].genome
                result.best_fitness = best[0].fitness
                result.best_code = self.encoder.decode(best[0].genome)

            result.total_time_seconds = time.time() - start_time
            result.completed_at = datetime.now()
            result.evaluations_performed = self.evaluator.stats["evaluations_performed"]

            self._emit("on_complete", result)

        except Exception as e:
            logger.error(f"Evolution error: {e}")
            result.stop_condition = StopCondition.MANUAL

        finally:
            self._running = False

        self.stats["evolution_runs"] += 1
        self.stats["total_generations"] += result.total_generations
        if result.best_fitness >= self.config.fitness_threshold:
            self.stats["solutions_found"] += 1

        return result

    def _check_stop_conditions(
        self,
        population: Population,
        result: EvolutionResult,
        start_time: float,
        stagnant_count: int,
    ) -> Optional[StopCondition]:
        """Check if evolution should stop."""
        # Max generations
        if population.generation >= self.config.max_generations:
            return StopCondition.MAX_GENERATIONS

        # Fitness threshold
        if population.best_fitness >= self.config.fitness_threshold:
            return StopCondition.FITNESS_THRESHOLD

        # Convergence (stagnation)
        if stagnant_count >= self.config.convergence_generations:
            return StopCondition.CONVERGENCE

        # Time limit
        elapsed = time.time() - start_time
        if elapsed >= self.config.time_limit_seconds:
            return StopCondition.TIME_LIMIT

        return None

    def _save_checkpoint(
        self,
        population: Population,
        result: EvolutionResult,
    ) -> None:
        """Save evolution checkpoint."""
        try:
            checkpoint_dir = Path(self.config.checkpoint_dir)
            checkpoint_dir.mkdir(parents=True, exist_ok=True)

            checkpoint = {
                "run_id": result.run_id,
                "generation": population.generation,
                "best_fitness": population.best_fitness,
                "fitness_history": result.fitness_history,
                "best_code": self.encoder.decode(
                    population.best_individual.genome
                ) if population.best_individual else "",
                "timestamp": datetime.now().isoformat(),
            }

            path = checkpoint_dir / f"checkpoint_{result.run_id}_{population.generation}.json"
            with open(path, 'w') as f:
                json.dump(checkpoint, f, indent=2)

            logger.info(f"Saved checkpoint: {path}")

        except Exception as e:
            logger.warning(f"Checkpoint save failed: {e}")

    def stop(self) -> None:
        """Stop evolution."""
        self._running = False

    def get_progress(self) -> Dict[str, Any]:
        """Get current evolution progress."""
        if not self._current_result:
            return {"status": "idle"}

        return {
            "status": "running" if self._running else "complete",
            "run_id": self._current_result.run_id,
            "generation": self._current_result.total_generations,
            "best_fitness": max(self._current_result.fitness_history) if self._current_result.fitness_history else 0,
            "elapsed_seconds": (
                datetime.now() - self._current_result.started_at
            ).total_seconds(),
        }

    def visualize_progress(
        self,
        result: EvolutionResult,
    ) -> str:
        """Generate ASCII visualization of evolution progress."""
        if not result.fitness_history:
            return "No data to visualize"

        lines = []
        lines.append("Evolution Progress")
        lines.append("=" * 50)

        # Fitness graph
        max_fitness = max(result.fitness_history)
        min_fitness = min(result.fitness_history)
        range_fitness = max(max_fitness - min_fitness, 0.01)

        graph_height = 10
        graph_width = min(50, len(result.fitness_history))

        # Sample points
        step = max(1, len(result.fitness_history) // graph_width)
        sampled = result.fitness_history[::step][:graph_width]

        for row in range(graph_height, -1, -1):
            threshold = min_fitness + (range_fitness * row / graph_height)
            line = f"{threshold:5.1%} |"

            for fitness in sampled:
                if fitness >= threshold:
                    line += "█"
                else:
                    line += " "

            lines.append(line)

        lines.append("       " + "-" * len(sampled))
        lines.append(f"       Gen 0 to {len(result.fitness_history)-1}")

        # Stats
        lines.append("")
        lines.append(f"Best Fitness: {result.best_fitness:.2%}")
        lines.append(f"Generations: {result.total_generations}")
        lines.append(f"Time: {result.total_time_seconds:.1f}s")
        lines.append(f"Stop: {result.stop_condition.value}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            **self.stats,
            "evaluator_stats": self.evaluator.get_stats(),
            "mutator_stats": self.mutator.get_stats(),
            "population_stats": self.population_manager.get_stats(),
        }


def demo():
    """Demonstrate evolution orchestrator."""
    print("=" * 60)
    print("BAEL Evolution Orchestrator Demo")
    print("=" * 60)

    # Configuration
    config = EvolutionConfig(
        population_size=10,
        max_generations=20,
        fitness_threshold=0.9,
        convergence_generations=5,
        crossover_rate=0.7,
        mutation_rate=0.2,
    )

    orchestrator = EvolutionOrchestrator(config)

    # Add test cases
    orchestrator.add_test_case("zero", {"n": 0}, 0)
    orchestrator.add_test_case("one", {"n": 1}, 1)
    orchestrator.add_test_case("five", {"n": 5}, 5)
    orchestrator.add_test_case("ten", {"n": 10}, 55)

    # Register callback
    def on_generation(stats):
        print(f"  Gen {stats.generation}: "
              f"Best={stats.best_fitness:.1%}, "
              f"Avg={stats.avg_fitness:.1%}")

    orchestrator.register_callback("on_generation", on_generation)

    # Seed code (intentionally suboptimal)
    seed_code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''

    print("\nEvolution Configuration:")
    print(f"  Population: {config.population_size}")
    print(f"  Max generations: {config.max_generations}")
    print(f"  Fitness threshold: {config.fitness_threshold:.0%}")
    print(f"  Test cases: 4")

    print("\nStarting evolution...")
    result = orchestrator.evolve(seed_code, function_name="fibonacci")

    print(f"\n{'=' * 50}")
    print("Evolution Complete!")
    print(f"  Stop condition: {result.stop_condition.value}")
    print(f"  Generations: {result.total_generations}")
    print(f"  Best fitness: {result.best_fitness:.2%}")
    print(f"  Total time: {result.total_time_seconds:.2f}s")

    if result.best_code:
        print(f"\nBest solution:")
        print(result.best_code)

    # Visualization
    print("\n" + orchestrator.visualize_progress(result))

    print(f"\nStats: {orchestrator.get_stats()}")


if __name__ == "__main__":
    demo()
