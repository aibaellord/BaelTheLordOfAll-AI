"""
BAEL Ultimate Swarm Intelligence
=================================

Bio-inspired multi-agent optimization and coordination.

"A thousand minds as one, each contributing to the collective wisdom." — Ba'el
"""

import asyncio
import logging
import random
import math
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import heapq

logger = logging.getLogger("BAEL.SwarmIntelligence")


class SwarmAlgorithm(Enum):
    """Swarm optimization algorithms."""
    PARTICLE_SWARM = "particle_swarm"
    ANT_COLONY = "ant_colony"
    BEE_ALGORITHM = "bee_algorithm"
    FIREFLY = "firefly"
    CUCKOO_SEARCH = "cuckoo_search"
    BAT_ALGORITHM = "bat_algorithm"
    WOLF_PACK = "wolf_pack"
    FISH_SCHOOL = "fish_school"


class AgentRole(Enum):
    """Roles in swarm."""
    SCOUT = "scout"           # Explores new areas
    WORKER = "worker"         # Exploits good areas
    LEADER = "leader"         # Guides others
    MESSENGER = "messenger"   # Spreads information
    GUARDIAN = "guardian"     # Protects solutions
    INNOVATOR = "innovator"   # Tries random jumps


class CommunicationType(Enum):
    """Communication methods."""
    PHEROMONE = "pheromone"       # Trail-based
    BROADCAST = "broadcast"       # All agents
    NEIGHBOR = "neighbor"         # Local communication
    LEADER = "leader"             # Hierarchical
    STIGMERGY = "stigmergy"       # Environment modification


@dataclass
class Position:
    """Position in solution space."""
    coordinates: List[float]
    fitness: float = 0.0

    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance."""
        return math.sqrt(sum(
            (a - b) ** 2 for a, b in zip(self.coordinates, other.coordinates)
        ))

    def copy(self) -> 'Position':
        """Create a copy."""
        return Position(list(self.coordinates), self.fitness)


@dataclass
class SwarmAgent:
    """An agent in the swarm."""
    id: str
    role: AgentRole
    position: Position
    velocity: List[float] = field(default_factory=list)
    personal_best: Optional[Position] = None
    memory: List[Position] = field(default_factory=list)
    energy: float = 1.0

    def __post_init__(self):
        if not self.velocity:
            self.velocity = [0.0] * len(self.position.coordinates)
        if self.personal_best is None:
            self.personal_best = self.position.copy()


@dataclass
class Pheromone:
    """Pheromone trail."""
    position: Position
    strength: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SwarmState:
    """Current state of the swarm."""
    agents: List[SwarmAgent]
    global_best: Position
    pheromones: List[Pheromone]
    iteration: int
    convergence_history: List[float]


@dataclass
class SwarmResult:
    """Result of swarm optimization."""
    best_position: Position
    best_fitness: float
    iterations: int
    evaluations: int
    convergence_history: List[float]
    final_state: SwarmState
    algorithm: SwarmAlgorithm
    duration_seconds: float


class ParticleSwarmOptimization:
    """
    Particle Swarm Optimization (PSO).

    Particles fly through solution space, influenced by
    personal and global best positions.
    """

    def __init__(
        self,
        n_particles: int = 30,
        inertia: float = 0.7,
        cognitive: float = 1.5,
        social: float = 1.5,
        max_velocity: float = 1.0,
    ):
        self.n_particles = n_particles
        self.inertia = inertia
        self.cognitive = cognitive
        self.social = social
        self.max_velocity = max_velocity

    async def optimize(
        self,
        dimensions: int,
        bounds: List[Tuple[float, float]],
        fitness_fn: Callable[[List[float]], float],
        max_iterations: int = 100,
        target_fitness: float = None,
    ) -> SwarmResult:
        """Run PSO optimization."""
        import time
        start = time.time()

        # Initialize particles
        particles = []
        for i in range(self.n_particles):
            coords = [
                random.uniform(bounds[d][0], bounds[d][1])
                for d in range(dimensions)
            ]
            velocity = [
                random.uniform(-self.max_velocity, self.max_velocity)
                for _ in range(dimensions)
            ]

            pos = Position(coords)
            pos.fitness = await self._evaluate(fitness_fn, coords)

            particles.append(SwarmAgent(
                id=f"particle_{i}",
                role=AgentRole.WORKER,
                position=pos,
                velocity=velocity,
            ))

        # Find global best
        global_best = max(particles, key=lambda p: p.position.fitness).position.copy()

        convergence = [global_best.fitness]
        evaluations = self.n_particles

        for iteration in range(max_iterations):
            for particle in particles:
                # Update velocity
                for d in range(dimensions):
                    r1, r2 = random.random(), random.random()

                    cognitive_vel = self.cognitive * r1 * (
                        particle.personal_best.coordinates[d] - particle.position.coordinates[d]
                    )
                    social_vel = self.social * r2 * (
                        global_best.coordinates[d] - particle.position.coordinates[d]
                    )

                    particle.velocity[d] = (
                        self.inertia * particle.velocity[d] +
                        cognitive_vel + social_vel
                    )

                    # Clamp velocity
                    particle.velocity[d] = max(
                        -self.max_velocity,
                        min(self.max_velocity, particle.velocity[d])
                    )

                # Update position
                for d in range(dimensions):
                    particle.position.coordinates[d] += particle.velocity[d]
                    # Clamp to bounds
                    particle.position.coordinates[d] = max(
                        bounds[d][0],
                        min(bounds[d][1], particle.position.coordinates[d])
                    )

                # Evaluate
                particle.position.fitness = await self._evaluate(
                    fitness_fn, particle.position.coordinates
                )
                evaluations += 1

                # Update personal best
                if particle.position.fitness > particle.personal_best.fitness:
                    particle.personal_best = particle.position.copy()

                # Update global best
                if particle.position.fitness > global_best.fitness:
                    global_best = particle.position.copy()

            convergence.append(global_best.fitness)

            if target_fitness and global_best.fitness >= target_fitness:
                break

            if iteration % 10 == 0:
                await asyncio.sleep(0)

        return SwarmResult(
            best_position=global_best,
            best_fitness=global_best.fitness,
            iterations=iteration + 1,
            evaluations=evaluations,
            convergence_history=convergence,
            final_state=SwarmState(
                agents=particles,
                global_best=global_best,
                pheromones=[],
                iteration=iteration + 1,
                convergence_history=convergence,
            ),
            algorithm=SwarmAlgorithm.PARTICLE_SWARM,
            duration_seconds=time.time() - start,
        )

    async def _evaluate(
        self,
        fitness_fn: Callable[[List[float]], float],
        coords: List[float],
    ) -> float:
        """Evaluate fitness."""
        if asyncio.iscoroutinefunction(fitness_fn):
            return await fitness_fn(coords)
        return fitness_fn(coords)


class AntColonyOptimization:
    """
    Ant Colony Optimization (ACO).

    Ants build solutions incrementally, depositing pheromones
    on good paths.
    """

    def __init__(
        self,
        n_ants: int = 20,
        evaporation_rate: float = 0.5,
        alpha: float = 1.0,  # Pheromone importance
        beta: float = 2.0,   # Heuristic importance
        q: float = 100.0,    # Pheromone deposit constant
    ):
        self.n_ants = n_ants
        self.evaporation = evaporation_rate
        self.alpha = alpha
        self.beta = beta
        self.q = q

    async def optimize_tsp(
        self,
        distances: List[List[float]],
        max_iterations: int = 100,
    ) -> SwarmResult:
        """Optimize Traveling Salesman Problem."""
        import time
        start = time.time()

        n_cities = len(distances)

        # Initialize pheromones
        pheromones = [[1.0 for _ in range(n_cities)] for _ in range(n_cities)]

        # Heuristic (inverse distance)
        heuristic = [
            [1.0 / (distances[i][j] + 0.1) if i != j else 0.0 for j in range(n_cities)]
            for i in range(n_cities)
        ]

        best_tour = None
        best_length = float('inf')
        convergence = []
        evaluations = 0

        for iteration in range(max_iterations):
            all_tours = []
            all_lengths = []

            for ant in range(self.n_ants):
                # Construct tour
                tour = self._construct_tour(n_cities, pheromones, heuristic)
                length = self._calculate_tour_length(tour, distances)

                all_tours.append(tour)
                all_lengths.append(length)
                evaluations += 1

                if length < best_length:
                    best_length = length
                    best_tour = tour

            # Evaporate pheromones
            for i in range(n_cities):
                for j in range(n_cities):
                    pheromones[i][j] *= (1 - self.evaporation)

            # Deposit pheromones
            for tour, length in zip(all_tours, all_lengths):
                deposit = self.q / length
                for i in range(len(tour) - 1):
                    pheromones[tour[i]][tour[i + 1]] += deposit
                    pheromones[tour[i + 1]][tour[i]] += deposit

            convergence.append(best_length)

            if iteration % 10 == 0:
                await asyncio.sleep(0)

        return SwarmResult(
            best_position=Position(best_tour, -best_length),
            best_fitness=-best_length,
            iterations=iteration + 1,
            evaluations=evaluations,
            convergence_history=convergence,
            final_state=SwarmState(
                agents=[],
                global_best=Position(best_tour, -best_length),
                pheromones=[Pheromone(Position([i, j]), pheromones[i][j])
                           for i in range(n_cities) for j in range(n_cities)],
                iteration=iteration + 1,
                convergence_history=convergence,
            ),
            algorithm=SwarmAlgorithm.ANT_COLONY,
            duration_seconds=time.time() - start,
        )

    def _construct_tour(
        self,
        n_cities: int,
        pheromones: List[List[float]],
        heuristic: List[List[float]],
    ) -> List[int]:
        """Construct a tour for one ant."""
        tour = [random.randint(0, n_cities - 1)]
        visited = {tour[0]}

        while len(tour) < n_cities:
            current = tour[-1]

            # Calculate probabilities
            probs = []
            unvisited = []

            for j in range(n_cities):
                if j not in visited:
                    prob = (
                        (pheromones[current][j] ** self.alpha) *
                        (heuristic[current][j] ** self.beta)
                    )
                    probs.append(prob)
                    unvisited.append(j)

            if not unvisited:
                break

            # Normalize
            total = sum(probs)
            if total > 0:
                probs = [p / total for p in probs]
            else:
                probs = [1.0 / len(unvisited)] * len(unvisited)

            # Select next city
            r = random.random()
            cumsum = 0
            next_city = unvisited[-1]

            for city, prob in zip(unvisited, probs):
                cumsum += prob
                if r <= cumsum:
                    next_city = city
                    break

            tour.append(next_city)
            visited.add(next_city)

        return tour

    def _calculate_tour_length(
        self,
        tour: List[int],
        distances: List[List[float]],
    ) -> float:
        """Calculate total tour length."""
        length = 0.0
        for i in range(len(tour) - 1):
            length += distances[tour[i]][tour[i + 1]]
        # Return to start
        if len(tour) > 0:
            length += distances[tour[-1]][tour[0]]
        return length


class BeeAlgorithm:
    """
    Artificial Bee Colony (ABC) Algorithm.

    Employed bees exploit food sources,
    onlooker bees select based on quality,
    scout bees explore randomly.
    """

    def __init__(
        self,
        n_employed: int = 25,
        n_onlooker: int = 25,
        limit: int = 100,  # Abandonment limit
    ):
        self.n_employed = n_employed
        self.n_onlooker = n_onlooker
        self.limit = limit

    async def optimize(
        self,
        dimensions: int,
        bounds: List[Tuple[float, float]],
        fitness_fn: Callable[[List[float]], float],
        max_iterations: int = 100,
    ) -> SwarmResult:
        """Run bee algorithm optimization."""
        import time
        start = time.time()

        # Initialize food sources
        food_sources = []
        trials = []  # Abandonment counters

        for _ in range(self.n_employed):
            coords = [
                random.uniform(bounds[d][0], bounds[d][1])
                for d in range(dimensions)
            ]
            pos = Position(coords)
            pos.fitness = await self._evaluate(fitness_fn, coords)
            food_sources.append(pos)
            trials.append(0)

        best = max(food_sources, key=lambda p: p.fitness).copy()
        convergence = [best.fitness]
        evaluations = self.n_employed

        for iteration in range(max_iterations):
            # Employed bee phase
            for i, source in enumerate(food_sources):
                new_source = self._generate_neighbor(source, food_sources, bounds, dimensions)
                new_source.fitness = await self._evaluate(fitness_fn, new_source.coordinates)
                evaluations += 1

                if new_source.fitness > source.fitness:
                    food_sources[i] = new_source
                    trials[i] = 0
                else:
                    trials[i] += 1

            # Calculate probabilities
            fitnesses = [max(0, s.fitness) for s in food_sources]
            total_fitness = sum(fitnesses)
            probs = [f / total_fitness if total_fitness > 0 else 1.0 / len(food_sources)
                    for f in fitnesses]

            # Onlooker bee phase
            for _ in range(self.n_onlooker):
                # Select source based on probability
                selected_idx = self._roulette_select(probs)
                source = food_sources[selected_idx]

                new_source = self._generate_neighbor(source, food_sources, bounds, dimensions)
                new_source.fitness = await self._evaluate(fitness_fn, new_source.coordinates)
                evaluations += 1

                if new_source.fitness > source.fitness:
                    food_sources[selected_idx] = new_source
                    trials[selected_idx] = 0
                else:
                    trials[selected_idx] += 1

            # Scout bee phase
            for i, trial in enumerate(trials):
                if trial >= self.limit:
                    # Abandon and explore randomly
                    coords = [
                        random.uniform(bounds[d][0], bounds[d][1])
                        for d in range(dimensions)
                    ]
                    pos = Position(coords)
                    pos.fitness = await self._evaluate(fitness_fn, coords)
                    evaluations += 1
                    food_sources[i] = pos
                    trials[i] = 0

            # Update best
            current_best = max(food_sources, key=lambda p: p.fitness)
            if current_best.fitness > best.fitness:
                best = current_best.copy()

            convergence.append(best.fitness)

            if iteration % 10 == 0:
                await asyncio.sleep(0)

        return SwarmResult(
            best_position=best,
            best_fitness=best.fitness,
            iterations=iteration + 1,
            evaluations=evaluations,
            convergence_history=convergence,
            final_state=SwarmState(
                agents=[SwarmAgent(f"bee_{i}", AgentRole.WORKER, s) for i, s in enumerate(food_sources)],
                global_best=best,
                pheromones=[],
                iteration=iteration + 1,
                convergence_history=convergence,
            ),
            algorithm=SwarmAlgorithm.BEE_ALGORITHM,
            duration_seconds=time.time() - start,
        )

    def _generate_neighbor(
        self,
        source: Position,
        all_sources: List[Position],
        bounds: List[Tuple[float, float]],
        dimensions: int,
    ) -> Position:
        """Generate neighbor solution."""
        # Select random dimension
        d = random.randint(0, dimensions - 1)

        # Select random partner (different from source)
        partner = random.choice([s for s in all_sources if s != source])

        # Generate new position
        phi = random.uniform(-1, 1)
        new_coords = list(source.coordinates)
        new_coords[d] = source.coordinates[d] + phi * (
            source.coordinates[d] - partner.coordinates[d]
        )

        # Clamp to bounds
        new_coords[d] = max(bounds[d][0], min(bounds[d][1], new_coords[d]))

        return Position(new_coords)

    def _roulette_select(self, probs: List[float]) -> int:
        """Roulette wheel selection."""
        r = random.random()
        cumsum = 0
        for i, p in enumerate(probs):
            cumsum += p
            if r <= cumsum:
                return i
        return len(probs) - 1

    async def _evaluate(
        self,
        fitness_fn: Callable[[List[float]], float],
        coords: List[float],
    ) -> float:
        """Evaluate fitness."""
        if asyncio.iscoroutinefunction(fitness_fn):
            return await fitness_fn(coords)
        return fitness_fn(coords)


class SwarmCoordinator:
    """
    Unified swarm intelligence coordinator.

    Coordinates multiple swarm algorithms and agent types.
    """

    def __init__(self):
        self.pso = ParticleSwarmOptimization()
        self.aco = AntColonyOptimization()
        self.abc = BeeAlgorithm()

    async def optimize(
        self,
        algorithm: SwarmAlgorithm,
        **kwargs,
    ) -> SwarmResult:
        """Run optimization with specified algorithm."""
        if algorithm == SwarmAlgorithm.PARTICLE_SWARM:
            return await self.pso.optimize(**kwargs)
        elif algorithm == SwarmAlgorithm.ANT_COLONY:
            return await self.aco.optimize_tsp(**kwargs)
        elif algorithm == SwarmAlgorithm.BEE_ALGORITHM:
            return await self.abc.optimize(**kwargs)
        else:
            # Default to PSO
            return await self.pso.optimize(**kwargs)

    async def multi_swarm_optimize(
        self,
        algorithms: List[SwarmAlgorithm],
        **kwargs,
    ) -> SwarmResult:
        """Run multiple algorithms and return best."""
        results = []

        for algo in algorithms:
            try:
                result = await self.optimize(algo, **kwargs)
                results.append(result)
            except Exception as e:
                logger.warning(f"Algorithm {algo} failed: {e}")

        if not results:
            raise ValueError("All algorithms failed")

        return max(results, key=lambda r: r.best_fitness)

    async def adaptive_optimize(
        self,
        dimensions: int,
        bounds: List[Tuple[float, float]],
        fitness_fn: Callable[[List[float]], float],
        max_iterations: int = 100,
    ) -> SwarmResult:
        """
        Adaptively select and run algorithms.

        Starts with PSO, switches if not improving.
        """
        import time
        start = time.time()

        # Start with PSO
        result = await self.pso.optimize(
            dimensions=dimensions,
            bounds=bounds,
            fitness_fn=fitness_fn,
            max_iterations=max_iterations // 2,
        )

        # Check improvement rate
        history = result.convergence_history
        if len(history) >= 10:
            recent_improvement = history[-1] - history[-10]

            if recent_improvement < 0.001:
                # Try Bee Algorithm for exploration
                result2 = await self.abc.optimize(
                    dimensions=dimensions,
                    bounds=bounds,
                    fitness_fn=fitness_fn,
                    max_iterations=max_iterations // 2,
                )

                if result2.best_fitness > result.best_fitness:
                    result = result2

        result.duration_seconds = time.time() - start
        return result


# Convenience instance
swarm = SwarmCoordinator()
