#!/usr/bin/env python3
"""
BAEL - Swarm Intelligence System
Advanced multi-agent swarm coordination and collective intelligence.

This module implements sophisticated swarm intelligence algorithms
for coordinating large numbers of agents to solve complex problems
through emergent collective behavior.

Features:
- Swarm topology management
- Pheromone-based communication
- Particle swarm optimization
- Ant colony optimization
- Bee algorithm implementation
- Stigmergy-based coordination
- Collective decision making
- Self-organizing behavior
- Dynamic swarm scaling
- Emergent problem solving
- Swarm health monitoring
- Role-based specialization
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SwarmRole(Enum):
    """Roles within a swarm."""
    SCOUT = "scout"          # Explores new solutions
    WORKER = "worker"        # Exploits known solutions
    QUEEN = "queen"          # Coordinates and spawns
    SOLDIER = "soldier"      # Defends and validates
    NURSE = "nurse"          # Maintains and heals
    FORAGER = "forager"      # Gathers resources
    MESSENGER = "messenger"  # Spreads information


class SwarmState(Enum):
    """State of the swarm."""
    IDLE = "idle"
    EXPLORING = "exploring"
    EXPLOITING = "exploiting"
    CONVERGING = "converging"
    STALLED = "stalled"
    EMERGENCY = "emergency"


class AgentState(Enum):
    """State of an individual agent."""
    IDLE = "idle"
    SEARCHING = "searching"
    WORKING = "working"
    RESTING = "resting"
    COMMUNICATING = "communicating"
    DYING = "dying"


class SignalType(Enum):
    """Types of swarm signals."""
    PHEROMONE = "pheromone"
    DANCE = "dance"
    SOUND = "sound"
    CHEMICAL = "chemical"
    VISUAL = "visual"


class OptimizationType(Enum):
    """Types of optimization problems."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Position:
    """A position in the solution space."""
    dimensions: List[float] = field(default_factory=list)

    def distance_to(self, other: "Position") -> float:
        """Calculate Euclidean distance to another position."""
        if len(self.dimensions) != len(other.dimensions):
            raise ValueError("Dimension mismatch")
        return math.sqrt(sum(
            (a - b) ** 2 for a, b in zip(self.dimensions, other.dimensions)
        ))

    def copy(self) -> "Position":
        """Create a copy of this position."""
        return Position(dimensions=list(self.dimensions))

    def __add__(self, other: "Position") -> "Position":
        """Add positions element-wise."""
        return Position(dimensions=[
            a + b for a, b in zip(self.dimensions, other.dimensions)
        ])

    def __sub__(self, other: "Position") -> "Position":
        """Subtract positions element-wise."""
        return Position(dimensions=[
            a - b for a, b in zip(self.dimensions, other.dimensions)
        ])

    def __mul__(self, scalar: float) -> "Position":
        """Multiply position by scalar."""
        return Position(dimensions=[d * scalar for d in self.dimensions])


@dataclass
class Velocity:
    """Velocity vector for particle movement."""
    components: List[float] = field(default_factory=list)

    def clamp(self, max_velocity: float) -> "Velocity":
        """Clamp velocity to maximum magnitude."""
        magnitude = math.sqrt(sum(c ** 2 for c in self.components))
        if magnitude > max_velocity and magnitude > 0:
            factor = max_velocity / magnitude
            return Velocity(components=[c * factor for c in self.components])
        return self


@dataclass
class Pheromone:
    """A pheromone signal in the environment."""
    id: str = field(default_factory=lambda: str(uuid4()))
    position: Position = field(default_factory=Position)
    intensity: float = 1.0
    decay_rate: float = 0.1
    type: str = "trail"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def decay(self, time_delta: float) -> None:
        """Apply decay to the pheromone."""
        self.intensity *= (1 - self.decay_rate * time_delta)

    @property
    def is_expired(self) -> bool:
        """Check if pheromone has decayed."""
        return self.intensity < 0.01


@dataclass
class SwarmAgent:
    """An individual agent in the swarm."""
    id: str = field(default_factory=lambda: str(uuid4()))
    role: SwarmRole = SwarmRole.WORKER
    state: AgentState = AgentState.IDLE
    position: Position = field(default_factory=Position)
    velocity: Velocity = field(default_factory=Velocity)
    personal_best_position: Optional[Position] = None
    personal_best_fitness: float = float('inf')
    energy: float = 100.0
    age: int = 0
    neighbors: List[str] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmConfig:
    """Configuration for a swarm."""
    size: int = 50
    dimensions: int = 2
    bounds: List[Tuple[float, float]] = None
    max_velocity: float = 1.0
    inertia_weight: float = 0.7
    cognitive_weight: float = 1.5  # Personal best attraction
    social_weight: float = 1.5    # Global best attraction
    pheromone_decay: float = 0.1
    evaporation_rate: float = 0.05
    exploration_rate: float = 0.3
    communication_range: float = 10.0
    energy_decay: float = 0.01
    max_age: int = 1000


@dataclass
class Solution:
    """A solution found by the swarm."""
    id: str = field(default_factory=lambda: str(uuid4()))
    position: Position = field(default_factory=Position)
    fitness: float = float('inf')
    found_by: str = ""
    iteration: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SwarmMetrics:
    """Metrics about swarm behavior."""
    iteration: int = 0
    global_best_fitness: float = float('inf')
    average_fitness: float = float('inf')
    diversity: float = 0.0
    convergence_rate: float = 0.0
    exploration_ratio: float = 0.0
    active_agents: int = 0
    total_agents: int = 0


# =============================================================================
# FITNESS FUNCTIONS
# =============================================================================

class FitnessFunction(ABC):
    """Abstract fitness function for optimization."""

    @abstractmethod
    def evaluate(self, position: Position) -> float:
        """Evaluate fitness at a position."""
        pass

    @property
    def optimization_type(self) -> OptimizationType:
        """Return optimization type."""
        return OptimizationType.MINIMIZE


class SphereFitness(FitnessFunction):
    """Sphere function - simple unimodal test function."""

    def evaluate(self, position: Position) -> float:
        return sum(d ** 2 for d in position.dimensions)


class RastriginFitness(FitnessFunction):
    """Rastrigin function - multimodal test function."""

    def evaluate(self, position: Position) -> float:
        n = len(position.dimensions)
        return 10 * n + sum(
            d ** 2 - 10 * math.cos(2 * math.pi * d)
            for d in position.dimensions
        )


class AckleyFitness(FitnessFunction):
    """Ackley function - multimodal test function."""

    def evaluate(self, position: Position) -> float:
        n = len(position.dimensions)
        sum1 = sum(d ** 2 for d in position.dimensions)
        sum2 = sum(math.cos(2 * math.pi * d) for d in position.dimensions)

        return (
            -20 * math.exp(-0.2 * math.sqrt(sum1 / n)) -
            math.exp(sum2 / n) + 20 + math.e
        )


class TaskFitness(FitnessFunction):
    """Fitness function for task-based optimization."""

    def __init__(self, task_evaluator: Callable[[Position], float]):
        self.task_evaluator = task_evaluator

    def evaluate(self, position: Position) -> float:
        return self.task_evaluator(position)


# =============================================================================
# SWARM ALGORITHMS
# =============================================================================

class SwarmAlgorithm(ABC):
    """Base class for swarm algorithms."""

    def __init__(self, config: SwarmConfig, fitness: FitnessFunction):
        self.config = config
        self.fitness = fitness
        self.agents: List[SwarmAgent] = []
        self.global_best_position: Optional[Position] = None
        self.global_best_fitness: float = float('inf')
        self.iteration = 0
        self.history: List[SwarmMetrics] = []

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the swarm."""
        pass

    @abstractmethod
    async def step(self) -> SwarmMetrics:
        """Execute one iteration of the algorithm."""
        pass

    def _random_position(self) -> Position:
        """Generate a random position within bounds."""
        bounds = self.config.bounds or [(-10, 10)] * self.config.dimensions
        return Position(dimensions=[
            random.uniform(low, high) for low, high in bounds
        ])

    def _clamp_position(self, position: Position) -> Position:
        """Clamp position to bounds."""
        bounds = self.config.bounds or [(-10, 10)] * self.config.dimensions
        return Position(dimensions=[
            max(low, min(high, d))
            for d, (low, high) in zip(position.dimensions, bounds)
        ])

    def _calculate_diversity(self) -> float:
        """Calculate swarm diversity."""
        if len(self.agents) < 2:
            return 0.0

        # Calculate centroid
        n = len(self.agents)
        dims = len(self.agents[0].position.dimensions)
        centroid = [0.0] * dims

        for agent in self.agents:
            for i, d in enumerate(agent.position.dimensions):
                centroid[i] += d / n

        # Calculate average distance from centroid
        total_distance = 0.0
        for agent in self.agents:
            distance = math.sqrt(sum(
                (a - c) ** 2
                for a, c in zip(agent.position.dimensions, centroid)
            ))
            total_distance += distance

        return total_distance / n


class ParticleSwarmOptimization(SwarmAlgorithm):
    """
    Particle Swarm Optimization (PSO) algorithm.

    Particles move through the solution space, influenced by
    their own best known position and the swarm's best known position.
    """

    async def initialize(self) -> None:
        """Initialize the particle swarm."""
        self.agents = []

        for i in range(self.config.size):
            position = self._random_position()
            velocity = Velocity(components=[
                random.uniform(-1, 1) for _ in range(self.config.dimensions)
            ])

            fitness = self.fitness.evaluate(position)

            agent = SwarmAgent(
                role=SwarmRole.WORKER,
                position=position,
                velocity=velocity,
                personal_best_position=position.copy(),
                personal_best_fitness=fitness
            )

            self.agents.append(agent)

            # Update global best
            if fitness < self.global_best_fitness:
                self.global_best_fitness = fitness
                self.global_best_position = position.copy()

    async def step(self) -> SwarmMetrics:
        """Execute one PSO iteration."""
        self.iteration += 1
        total_fitness = 0.0

        for agent in self.agents:
            # Update velocity
            r1, r2 = random.random(), random.random()

            cognitive = [
                self.config.cognitive_weight * r1 * (pb - p)
                for pb, p in zip(
                    agent.personal_best_position.dimensions,
                    agent.position.dimensions
                )
            ]

            social = [
                self.config.social_weight * r2 * (gb - p)
                for gb, p in zip(
                    self.global_best_position.dimensions,
                    agent.position.dimensions
                )
            ]

            new_velocity = Velocity(components=[
                self.config.inertia_weight * v + c + s
                for v, c, s in zip(agent.velocity.components, cognitive, social)
            ]).clamp(self.config.max_velocity)

            agent.velocity = new_velocity

            # Update position
            new_position = Position(dimensions=[
                p + v for p, v in zip(
                    agent.position.dimensions,
                    agent.velocity.components
                )
            ])
            agent.position = self._clamp_position(new_position)

            # Evaluate fitness
            fitness = self.fitness.evaluate(agent.position)
            total_fitness += fitness

            # Update personal best
            if fitness < agent.personal_best_fitness:
                agent.personal_best_fitness = fitness
                agent.personal_best_position = agent.position.copy()

                # Update global best
                if fitness < self.global_best_fitness:
                    self.global_best_fitness = fitness
                    self.global_best_position = agent.position.copy()

            agent.age += 1

        metrics = SwarmMetrics(
            iteration=self.iteration,
            global_best_fitness=self.global_best_fitness,
            average_fitness=total_fitness / len(self.agents),
            diversity=self._calculate_diversity(),
            active_agents=len(self.agents),
            total_agents=len(self.agents)
        )

        self.history.append(metrics)
        return metrics


class AntColonyOptimization(SwarmAlgorithm):
    """
    Ant Colony Optimization (ACO) algorithm.

    Ants deposit pheromones on paths, influencing other ants
    to follow successful routes.
    """

    def __init__(self, config: SwarmConfig, fitness: FitnessFunction):
        super().__init__(config, fitness)
        self.pheromones: Dict[str, Pheromone] = {}
        self.alpha = 1.0  # Pheromone influence
        self.beta = 2.0   # Heuristic influence

    async def initialize(self) -> None:
        """Initialize the ant colony."""
        self.agents = []

        for i in range(self.config.size):
            position = self._random_position()

            agent = SwarmAgent(
                role=SwarmRole.FORAGER,
                position=position
            )

            self.agents.append(agent)

    async def step(self) -> SwarmMetrics:
        """Execute one ACO iteration."""
        self.iteration += 1

        # Move ants
        for agent in self.agents:
            # Find nearby pheromones
            nearby_pheromones = self._get_nearby_pheromones(
                agent.position,
                self.config.communication_range
            )

            if nearby_pheromones and random.random() > self.config.exploration_rate:
                # Follow pheromones (exploitation)
                target = self._select_by_pheromone(nearby_pheromones)
                direction = target.position - agent.position
                magnitude = math.sqrt(sum(d ** 2 for d in direction.dimensions))
                if magnitude > 0:
                    move = Position(dimensions=[
                        d / magnitude * self.config.max_velocity
                        for d in direction.dimensions
                    ])
                    agent.position = self._clamp_position(agent.position + move)
            else:
                # Random walk (exploration)
                move = Position(dimensions=[
                    random.uniform(-1, 1) * self.config.max_velocity
                    for _ in range(self.config.dimensions)
                ])
                agent.position = self._clamp_position(agent.position + move)

            # Evaluate and deposit pheromone
            fitness = self.fitness.evaluate(agent.position)

            if fitness < agent.personal_best_fitness:
                agent.personal_best_fitness = fitness

                # Deposit pheromone (stronger for better solutions)
                intensity = 1.0 / (1.0 + fitness)
                self._deposit_pheromone(agent.position, intensity)

                # Update global best
                if fitness < self.global_best_fitness:
                    self.global_best_fitness = fitness
                    self.global_best_position = agent.position.copy()

            agent.age += 1

        # Evaporate pheromones
        self._evaporate_pheromones()

        return SwarmMetrics(
            iteration=self.iteration,
            global_best_fitness=self.global_best_fitness,
            diversity=self._calculate_diversity(),
            active_agents=len(self.agents),
            total_agents=len(self.agents)
        )

    def _get_nearby_pheromones(
        self,
        position: Position,
        range_dist: float
    ) -> List[Pheromone]:
        """Get pheromones within range."""
        nearby = []
        for pheromone in self.pheromones.values():
            if position.distance_to(pheromone.position) <= range_dist:
                nearby.append(pheromone)
        return nearby

    def _select_by_pheromone(self, pheromones: List[Pheromone]) -> Pheromone:
        """Select pheromone using roulette wheel selection."""
        total = sum(p.intensity ** self.alpha for p in pheromones)
        threshold = random.random() * total

        cumulative = 0
        for p in pheromones:
            cumulative += p.intensity ** self.alpha
            if cumulative >= threshold:
                return p

        return pheromones[-1]

    def _deposit_pheromone(self, position: Position, intensity: float) -> None:
        """Deposit a pheromone at position."""
        pheromone = Pheromone(
            position=position.copy(),
            intensity=intensity,
            decay_rate=self.config.pheromone_decay
        )
        self.pheromones[pheromone.id] = pheromone

    def _evaporate_pheromones(self) -> None:
        """Apply evaporation to all pheromones."""
        expired = []
        for pid, pheromone in self.pheromones.items():
            pheromone.decay(self.config.evaporation_rate)
            if pheromone.is_expired:
                expired.append(pid)

        for pid in expired:
            del self.pheromones[pid]


class BeeAlgorithm(SwarmAlgorithm):
    """
    Artificial Bee Colony (ABC) algorithm.

    Employs different bee types: employed bees, onlooker bees,
    and scout bees for balanced exploration and exploitation.
    """

    def __init__(self, config: SwarmConfig, fitness: FitnessFunction):
        super().__init__(config, fitness)
        self.limit = config.size  # Abandon limit
        self.trials: Dict[str, int] = {}

    async def initialize(self) -> None:
        """Initialize the bee colony."""
        self.agents = []

        # Half employed, half onlookers
        employed_count = self.config.size // 2

        for i in range(self.config.size):
            position = self._random_position()
            fitness = self.fitness.evaluate(position)

            role = SwarmRole.FORAGER if i < employed_count else SwarmRole.WORKER

            agent = SwarmAgent(
                role=role,
                position=position,
                personal_best_position=position.copy(),
                personal_best_fitness=fitness
            )

            self.agents.append(agent)
            self.trials[agent.id] = 0

            if fitness < self.global_best_fitness:
                self.global_best_fitness = fitness
                self.global_best_position = position.copy()

    async def step(self) -> SwarmMetrics:
        """Execute one ABC iteration."""
        self.iteration += 1

        employed_bees = [a for a in self.agents if a.role == SwarmRole.FORAGER]
        onlooker_bees = [a for a in self.agents if a.role == SwarmRole.WORKER]

        # Employed bee phase
        for bee in employed_bees:
            new_position = self._local_search(bee)
            new_fitness = self.fitness.evaluate(new_position)

            if new_fitness < bee.personal_best_fitness:
                bee.position = new_position
                bee.personal_best_position = new_position.copy()
                bee.personal_best_fitness = new_fitness
                self.trials[bee.id] = 0

                if new_fitness < self.global_best_fitness:
                    self.global_best_fitness = new_fitness
                    self.global_best_position = new_position.copy()
            else:
                self.trials[bee.id] += 1

        # Calculate probabilities for onlooker phase
        max_fitness = max(b.personal_best_fitness for b in employed_bees)
        probabilities = []
        for bee in employed_bees:
            prob = 1 - (bee.personal_best_fitness / (max_fitness + 1e-10))
            probabilities.append(prob)

        total_prob = sum(probabilities)
        if total_prob > 0:
            probabilities = [p / total_prob for p in probabilities]

        # Onlooker bee phase
        for bee in onlooker_bees:
            # Select food source based on probability
            selected_idx = self._roulette_select(probabilities)
            selected_bee = employed_bees[selected_idx]

            new_position = self._local_search(selected_bee)
            new_fitness = self.fitness.evaluate(new_position)

            if new_fitness < selected_bee.personal_best_fitness:
                selected_bee.position = new_position
                selected_bee.personal_best_position = new_position.copy()
                selected_bee.personal_best_fitness = new_fitness
                self.trials[selected_bee.id] = 0

                if new_fitness < self.global_best_fitness:
                    self.global_best_fitness = new_fitness
                    self.global_best_position = new_position.copy()
            else:
                self.trials[selected_bee.id] += 1

        # Scout bee phase
        for bee in employed_bees:
            if self.trials.get(bee.id, 0) > self.limit:
                bee.position = self._random_position()
                bee.personal_best_position = bee.position.copy()
                bee.personal_best_fitness = self.fitness.evaluate(bee.position)
                self.trials[bee.id] = 0

        return SwarmMetrics(
            iteration=self.iteration,
            global_best_fitness=self.global_best_fitness,
            diversity=self._calculate_diversity(),
            active_agents=len(self.agents),
            total_agents=len(self.agents)
        )

    def _local_search(self, bee: SwarmAgent) -> Position:
        """Perform local search around a bee's position."""
        # Select random dimension
        dim = random.randint(0, self.config.dimensions - 1)

        # Select random partner
        partner = random.choice([a for a in self.agents if a.id != bee.id])

        # Generate new position
        phi = random.uniform(-1, 1)
        new_dims = list(bee.position.dimensions)
        new_dims[dim] = bee.position.dimensions[dim] + phi * (
            bee.position.dimensions[dim] - partner.position.dimensions[dim]
        )

        return self._clamp_position(Position(dimensions=new_dims))

    def _roulette_select(self, probabilities: List[float]) -> int:
        """Roulette wheel selection."""
        r = random.random()
        cumulative = 0
        for i, prob in enumerate(probabilities):
            cumulative += prob
            if r <= cumulative:
                return i
        return len(probabilities) - 1


# =============================================================================
# SWARM CONTROLLER
# =============================================================================

class SwarmController:
    """
    Controller for managing swarm behavior.

    Provides high-level swarm management including
    algorithm selection, monitoring, and adaptation.
    """

    def __init__(self):
        self.swarms: Dict[str, SwarmAlgorithm] = {}
        self.running: Dict[str, bool] = {}
        self.results: Dict[str, List[Solution]] = defaultdict(list)

    async def create_swarm(
        self,
        name: str,
        algorithm: str,
        config: SwarmConfig,
        fitness: FitnessFunction
    ) -> str:
        """Create a new swarm."""
        swarm_id = f"{name}_{uuid4().hex[:8]}"

        if algorithm == "pso":
            swarm = ParticleSwarmOptimization(config, fitness)
        elif algorithm == "aco":
            swarm = AntColonyOptimization(config, fitness)
        elif algorithm == "abc":
            swarm = BeeAlgorithm(config, fitness)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        await swarm.initialize()
        self.swarms[swarm_id] = swarm
        self.running[swarm_id] = False

        logger.info(f"Created swarm: {swarm_id} using {algorithm}")
        return swarm_id

    async def run_swarm(
        self,
        swarm_id: str,
        max_iterations: int = 100,
        target_fitness: Optional[float] = None,
        callback: Optional[Callable[[SwarmMetrics], None]] = None
    ) -> Solution:
        """Run a swarm for specified iterations."""
        swarm = self.swarms.get(swarm_id)
        if not swarm:
            raise ValueError(f"Unknown swarm: {swarm_id}")

        self.running[swarm_id] = True

        for i in range(max_iterations):
            if not self.running.get(swarm_id, False):
                break

            metrics = await swarm.step()

            if callback:
                callback(metrics)

            # Check convergence
            if target_fitness is not None:
                if metrics.global_best_fitness <= target_fitness:
                    logger.info(f"Target fitness reached at iteration {i}")
                    break

            # Small delay to prevent blocking
            await asyncio.sleep(0)

        self.running[swarm_id] = False

        # Create solution
        solution = Solution(
            position=swarm.global_best_position.copy(),
            fitness=swarm.global_best_fitness,
            iteration=swarm.iteration
        )

        self.results[swarm_id].append(solution)
        return solution

    async def stop_swarm(self, swarm_id: str) -> bool:
        """Stop a running swarm."""
        if swarm_id in self.running:
            self.running[swarm_id] = False
            return True
        return False

    def get_swarm_status(self, swarm_id: str) -> Dict[str, Any]:
        """Get status of a swarm."""
        swarm = self.swarms.get(swarm_id)
        if not swarm:
            return {}

        return {
            "id": swarm_id,
            "running": self.running.get(swarm_id, False),
            "iteration": swarm.iteration,
            "agents": len(swarm.agents),
            "global_best_fitness": swarm.global_best_fitness,
            "diversity": swarm._calculate_diversity() if swarm.agents else 0,
            "history_length": len(swarm.history)
        }


# =============================================================================
# SWARM INTELLIGENCE SYSTEM
# =============================================================================

class SwarmIntelligence:
    """
    The master swarm intelligence system for BAEL.

    Provides unified access to swarm algorithms and
    collective problem-solving capabilities.
    """

    def __init__(self):
        self.controller = SwarmController()
        self.active_optimizations: Dict[str, asyncio.Task] = {}

    async def optimize(
        self,
        problem: Callable[[List[float]], float],
        dimensions: int = 2,
        bounds: List[Tuple[float, float]] = None,
        algorithm: str = "pso",
        population: int = 50,
        max_iterations: int = 100,
        target_fitness: Optional[float] = None
    ) -> Tuple[List[float], float]:
        """
        Optimize a problem using swarm intelligence.

        Args:
            problem: Fitness function taking position and returning fitness
            dimensions: Number of dimensions
            bounds: Bounds for each dimension
            algorithm: Algorithm to use (pso, aco, abc)
            population: Swarm size
            max_iterations: Maximum iterations
            target_fitness: Stop when reached

        Returns:
            Tuple of (best_position, best_fitness)
        """
        config = SwarmConfig(
            size=population,
            dimensions=dimensions,
            bounds=bounds or [(-10, 10)] * dimensions
        )

        fitness = TaskFitness(lambda p: problem(p.dimensions))

        swarm_id = await self.controller.create_swarm(
            "optimization",
            algorithm,
            config,
            fitness
        )

        solution = await self.controller.run_swarm(
            swarm_id,
            max_iterations=max_iterations,
            target_fitness=target_fitness
        )

        return solution.position.dimensions, solution.fitness

    async def parallel_optimize(
        self,
        problem: Callable[[List[float]], float],
        dimensions: int = 2,
        bounds: List[Tuple[float, float]] = None,
        algorithms: List[str] = None,
        population_per_swarm: int = 30,
        max_iterations: int = 100
    ) -> Tuple[List[float], float]:
        """
        Run multiple swarm algorithms in parallel.

        Combines results from different algorithms for
        better global search.
        """
        algorithms = algorithms or ["pso", "aco", "abc"]

        async def run_single(algo: str) -> Tuple[List[float], float]:
            return await self.optimize(
                problem,
                dimensions,
                bounds,
                algo,
                population_per_swarm,
                max_iterations
            )

        tasks = [run_single(algo) for algo in algorithms]
        results = await asyncio.gather(*tasks)

        # Return best result
        best_result = min(results, key=lambda x: x[1])
        return best_result

    async def solve_assignment(
        self,
        cost_matrix: List[List[float]],
        max_iterations: int = 200
    ) -> Tuple[List[int], float]:
        """
        Solve assignment problem using swarm optimization.

        Args:
            cost_matrix: NxN matrix of costs
            max_iterations: Maximum iterations

        Returns:
            Tuple of (assignment, total_cost)
        """
        n = len(cost_matrix)

        def assignment_fitness(position: List[float]) -> float:
            # Convert continuous position to discrete assignment
            indices = sorted(range(n), key=lambda i: position[i])
            total_cost = sum(cost_matrix[i][indices[i]] for i in range(n))
            return total_cost

        best_pos, best_fitness = await self.optimize(
            assignment_fitness,
            dimensions=n,
            bounds=[(0, 1)] * n,
            algorithm="pso",
            population=100,
            max_iterations=max_iterations
        )

        assignment = sorted(range(n), key=lambda i: best_pos[i])
        return assignment, best_fitness

    async def cluster_data(
        self,
        data: List[List[float]],
        k: int,
        max_iterations: int = 100
    ) -> Tuple[List[int], List[List[float]]]:
        """
        Cluster data using swarm optimization.

        Args:
            data: List of data points
            k: Number of clusters
            max_iterations: Maximum iterations

        Returns:
            Tuple of (cluster_assignments, centroids)
        """
        n_points = len(data)
        n_dims = len(data[0])

        def clustering_fitness(centroids_flat: List[float]) -> float:
            # Reshape centroids
            centroids = [
                centroids_flat[i*n_dims:(i+1)*n_dims]
                for i in range(k)
            ]

            # Assign points to nearest centroid
            total_distance = 0
            for point in data:
                min_dist = float('inf')
                for centroid in centroids:
                    dist = math.sqrt(sum(
                        (p - c) ** 2 for p, c in zip(point, centroid)
                    ))
                    min_dist = min(min_dist, dist)
                total_distance += min_dist

            return total_distance

        # Determine bounds from data
        mins = [min(p[d] for p in data) for d in range(n_dims)]
        maxs = [max(p[d] for p in data) for d in range(n_dims)]
        bounds = [(mins[d % n_dims], maxs[d % n_dims]) for d in range(k * n_dims)]

        best_pos, _ = await self.optimize(
            clustering_fitness,
            dimensions=k * n_dims,
            bounds=bounds,
            algorithm="pso",
            population=50,
            max_iterations=max_iterations
        )

        # Extract centroids and assignments
        centroids = [best_pos[i*n_dims:(i+1)*n_dims] for i in range(k)]

        assignments = []
        for point in data:
            min_dist = float('inf')
            min_cluster = 0
            for i, centroid in enumerate(centroids):
                dist = math.sqrt(sum((p - c) ** 2 for p, c in zip(point, centroid)))
                if dist < min_dist:
                    min_dist = dist
                    min_cluster = i
            assignments.append(min_cluster)

        return assignments, centroids


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Swarm Intelligence System."""
    print("=" * 70)
    print("BAEL - SWARM INTELLIGENCE DEMO")
    print("Collective Problem Solving")
    print("=" * 70)
    print()

    # Create swarm intelligence
    swarm = SwarmIntelligence()

    # 1. Basic Optimization
    print("1. BASIC OPTIMIZATION (Sphere Function):")
    print("-" * 40)

    def sphere(x: List[float]) -> float:
        return sum(xi ** 2 for xi in x)

    best_pos, best_fitness = await swarm.optimize(
        sphere,
        dimensions=5,
        bounds=[(-10, 10)] * 5,
        algorithm="pso",
        population=30,
        max_iterations=50
    )

    print(f"   Best Position: [{', '.join(f'{x:.4f}' for x in best_pos)}]")
    print(f"   Best Fitness: {best_fitness:.6f}")
    print(f"   Optimal: 0.0 (at origin)")
    print()

    # 2. Multimodal Optimization
    print("2. MULTIMODAL OPTIMIZATION (Rastrigin Function):")
    print("-" * 40)

    def rastrigin(x: List[float]) -> float:
        n = len(x)
        return 10 * n + sum(xi ** 2 - 10 * math.cos(2 * math.pi * xi) for xi in x)

    best_pos, best_fitness = await swarm.optimize(
        rastrigin,
        dimensions=3,
        bounds=[(-5.12, 5.12)] * 3,
        algorithm="pso",
        population=50,
        max_iterations=100
    )

    print(f"   Best Fitness: {best_fitness:.4f}")
    print(f"   Optimal: 0.0")
    print()

    # 3. Parallel Optimization
    print("3. PARALLEL OPTIMIZATION (All Algorithms):")
    print("-" * 40)

    best_pos, best_fitness = await swarm.parallel_optimize(
        sphere,
        dimensions=4,
        bounds=[(-5, 5)] * 4,
        algorithms=["pso", "abc"],
        max_iterations=30
    )

    print(f"   Best (combined): {best_fitness:.6f}")
    print()

    # 4. Clustering Demo
    print("4. DATA CLUSTERING:")
    print("-" * 40)

    # Generate sample data (3 clusters)
    data = []
    for _ in range(20):
        data.append([random.gauss(0, 1), random.gauss(0, 1)])
    for _ in range(20):
        data.append([random.gauss(5, 1), random.gauss(5, 1)])
    for _ in range(20):
        data.append([random.gauss(0, 1), random.gauss(5, 1)])

    assignments, centroids = await swarm.cluster_data(data, k=3, max_iterations=50)

    cluster_counts = [assignments.count(i) for i in range(3)]
    print(f"   Cluster sizes: {cluster_counts}")
    print(f"   Centroids:")
    for i, c in enumerate(centroids):
        print(f"     Cluster {i}: [{c[0]:.2f}, {c[1]:.2f}]")
    print()

    # 5. Assignment Problem
    print("5. ASSIGNMENT PROBLEM:")
    print("-" * 40)

    cost_matrix = [
        [10, 5, 13, 15],
        [3, 9, 18, 13],
        [10, 7, 3, 2],
        [5, 11, 9, 7]
    ]

    assignment, total_cost = await swarm.solve_assignment(cost_matrix, max_iterations=100)
    print(f"   Assignment: {assignment}")
    print(f"   Total Cost: {total_cost:.2f}")
    print()

    # 6. Swarm Controller Demo
    print("6. SWARM CONTROLLER:")
    print("-" * 40)

    controller = SwarmController()

    config = SwarmConfig(size=20, dimensions=2, bounds=[(-5, 5), (-5, 5)])
    swarm_id = await controller.create_swarm(
        "demo_swarm",
        "pso",
        config,
        SphereFitness()
    )

    status = controller.get_swarm_status(swarm_id)
    print(f"   Swarm ID: {swarm_id}")
    print(f"   Agents: {status['agents']}")

    solution = await controller.run_swarm(swarm_id, max_iterations=20)
    print(f"   Solution Fitness: {solution.fitness:.6f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Swarm Intelligence Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
