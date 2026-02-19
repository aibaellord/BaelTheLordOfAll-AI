"""
⚡ PARTICLE SWARM OPTIMIZATION ⚡
=================================
Continuous optimization inspired by bird flocking.

Implements:
- Standard PSO
- Adaptive PSO (with inertia adaptation)
- Quantum PSO
- Multi-Objective PSO (MOPSO)
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

from .swarm_core import (
    SwarmAgent,
    SwarmAgentConfig,
    SwarmEnvironment,
    Position,
    AgentState,
)


@dataclass
class PSOConfig:
    """Configuration for PSO"""
    inertia: float = 0.7        # Inertia weight
    cognitive: float = 1.5      # Cognitive (personal best) coefficient
    social: float = 1.5         # Social (global best) coefficient
    v_max: float = 1.0          # Maximum velocity
    v_min: float = -1.0         # Minimum velocity
    bounds: Tuple[float, float] = (-10.0, 10.0)


@dataclass
class Particle:
    """Particle in PSO"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    position: np.ndarray = None
    velocity: np.ndarray = None
    personal_best_position: np.ndarray = None
    personal_best_fitness: float = float('-inf')
    fitness: float = float('-inf')

    @classmethod
    def create(
        cls,
        dimensions: int,
        bounds: Tuple[float, float] = (-10, 10)
    ) -> 'Particle':
        """Create random particle"""
        position = np.random.uniform(bounds[0], bounds[1], dimensions)
        velocity = np.random.uniform(-1, 1, dimensions)

        return cls(
            position=position,
            velocity=velocity,
            personal_best_position=position.copy(),
        )


class ParticleSwarm:
    """
    Collection of particles forming a swarm.
    """

    def __init__(
        self,
        n_particles: int,
        dimensions: int,
        config: PSOConfig = None
    ):
        self.n_particles = n_particles
        self.dimensions = dimensions
        self.config = config or PSOConfig()

        # Create particles
        self.particles = [
            Particle.create(dimensions, self.config.bounds)
            for _ in range(n_particles)
        ]

        # Global best
        self.global_best_position: np.ndarray = None
        self.global_best_fitness = float('-inf')

        # Statistics
        self.iteration = 0
        self.history: List[float] = []

    def update(
        self,
        fitness_fn: Callable[[np.ndarray], float]
    ):
        """Update all particles"""
        for particle in self.particles:
            # Evaluate fitness
            particle.fitness = fitness_fn(particle.position)

            # Update personal best
            if particle.fitness > particle.personal_best_fitness:
                particle.personal_best_fitness = particle.fitness
                particle.personal_best_position = particle.position.copy()

            # Update global best
            if particle.fitness > self.global_best_fitness:
                self.global_best_fitness = particle.fitness
                self.global_best_position = particle.position.copy()

        # Update velocities and positions
        for particle in self.particles:
            self._update_velocity(particle)
            self._update_position(particle)

        self.iteration += 1
        self.history.append(self.global_best_fitness)

    def _update_velocity(self, particle: Particle):
        """Update particle velocity"""
        r1 = np.random.random(self.dimensions)
        r2 = np.random.random(self.dimensions)

        # Cognitive component
        cognitive = self.config.cognitive * r1 * (
            particle.personal_best_position - particle.position
        )

        # Social component
        social = self.config.social * r2 * (
            self.global_best_position - particle.position
        )

        # Update velocity
        particle.velocity = (
            self.config.inertia * particle.velocity +
            cognitive + social
        )

        # Clamp velocity
        particle.velocity = np.clip(
            particle.velocity,
            self.config.v_min,
            self.config.v_max
        )

    def _update_position(self, particle: Particle):
        """Update particle position"""
        particle.position = particle.position + particle.velocity

        # Enforce bounds
        particle.position = np.clip(
            particle.position,
            self.config.bounds[0],
            self.config.bounds[1]
        )


class PSOptimizer:
    """
    Standard Particle Swarm Optimizer.
    """

    def __init__(
        self,
        objective_fn: Callable[[np.ndarray], float],
        dimensions: int,
        n_particles: int = 30,
        config: PSOConfig = None
    ):
        self.objective_fn = objective_fn
        self.dimensions = dimensions
        self.n_particles = n_particles
        self.config = config or PSOConfig()

        self.swarm = ParticleSwarm(n_particles, dimensions, config)

        # Convergence tracking
        self.converged = False
        self.stagnation_count = 0

    def optimize(
        self,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Tuple[np.ndarray, float]:
        """Run optimization"""
        prev_best = float('-inf')

        for i in range(max_iterations):
            self.swarm.update(self.objective_fn)

            # Check convergence
            improvement = self.swarm.global_best_fitness - prev_best
            if improvement < tolerance:
                self.stagnation_count += 1
                if self.stagnation_count > 20:
                    self.converged = True
                    break
            else:
                self.stagnation_count = 0

            prev_best = self.swarm.global_best_fitness

        return (
            self.swarm.global_best_position,
            self.swarm.global_best_fitness
        )


class AdaptivePSO(PSOptimizer):
    """
    Adaptive PSO with self-adjusting parameters.

    Features:
    - Inertia weight adaptation
    - Velocity clamping adjustment
    - Cognitive/social coefficient balancing
    """

    def __init__(
        self,
        objective_fn: Callable[[np.ndarray], float],
        dimensions: int,
        n_particles: int = 30,
        config: PSOConfig = None,
        inertia_max: float = 0.9,
        inertia_min: float = 0.4
    ):
        super().__init__(objective_fn, dimensions, n_particles, config)
        self.inertia_max = inertia_max
        self.inertia_min = inertia_min

        # Success/failure tracking
        self.success_count = 0
        self.failure_count = 0

    def optimize(
        self,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Tuple[np.ndarray, float]:
        """Run adaptive optimization"""
        prev_best = float('-inf')

        for i in range(max_iterations):
            # Adapt inertia linearly
            progress = i / max_iterations
            self.swarm.config.inertia = (
                self.inertia_max -
                (self.inertia_max - self.inertia_min) * progress
            )

            # Update swarm
            old_best = self.swarm.global_best_fitness
            self.swarm.update(self.objective_fn)

            # Track success/failure
            if self.swarm.global_best_fitness > old_best:
                self.success_count += 1
                self.failure_count = 0
            else:
                self.failure_count += 1

            # Adapt coefficients based on success
            if self.failure_count > 5:
                # Increase exploration
                self.swarm.config.social *= 1.1
                self.swarm.config.cognitive *= 0.9
            elif self.success_count > 5:
                # Increase exploitation
                self.swarm.config.cognitive *= 1.1
                self.swarm.config.social *= 0.9

            # Check convergence
            improvement = self.swarm.global_best_fitness - prev_best
            if improvement < tolerance:
                self.stagnation_count += 1
                if self.stagnation_count > 20:
                    self.converged = True
                    break
            else:
                self.stagnation_count = 0

            prev_best = self.swarm.global_best_fitness

        return (
            self.swarm.global_best_position,
            self.swarm.global_best_fitness
        )


class QuantumPSO:
    """
    Quantum-behaved PSO.

    Uses quantum mechanical principles:
    - No velocity (position update based on attractor)
    - Stochastic nature of measurement
    - Contraction-expansion coefficient
    """

    def __init__(
        self,
        objective_fn: Callable[[np.ndarray], float],
        dimensions: int,
        n_particles: int = 30,
        bounds: Tuple[float, float] = (-10, 10),
        beta_max: float = 1.0,
        beta_min: float = 0.5
    ):
        self.objective_fn = objective_fn
        self.dimensions = dimensions
        self.n_particles = n_particles
        self.bounds = bounds
        self.beta_max = beta_max
        self.beta_min = beta_min

        # Particles (positions only, no velocity in QPSO)
        self.positions = np.random.uniform(
            bounds[0], bounds[1],
            (n_particles, dimensions)
        )
        self.personal_best = self.positions.copy()
        self.personal_best_fitness = np.full(n_particles, float('-inf'))

        # Global best
        self.global_best = None
        self.global_best_fitness = float('-inf')

        # Mean best position (mbest)
        self.mbest = np.mean(self.personal_best, axis=0)

        # History
        self.iteration = 0
        self.history: List[float] = []

    def _update_mbest(self):
        """Update mean best position"""
        self.mbest = np.mean(self.personal_best, axis=0)

    def _get_attractor(self, idx: int) -> np.ndarray:
        """Calculate attractor point for particle"""
        phi = np.random.random(self.dimensions)
        attractor = (
            phi * self.personal_best[idx] +
            (1 - phi) * self.global_best
        )
        return attractor

    def _update_position(
        self,
        idx: int,
        beta: float
    ):
        """Quantum position update"""
        attractor = self._get_attractor(idx)

        # Characteristic length
        L = beta * np.abs(self.mbest - self.positions[idx])

        # Quantum update
        u = np.random.random(self.dimensions)

        if np.random.random() < 0.5:
            self.positions[idx] = attractor + L * np.log(1 / u)
        else:
            self.positions[idx] = attractor - L * np.log(1 / u)

        # Enforce bounds
        self.positions[idx] = np.clip(
            self.positions[idx],
            self.bounds[0],
            self.bounds[1]
        )

    def optimize(
        self,
        max_iterations: int = 100
    ) -> Tuple[np.ndarray, float]:
        """Run quantum PSO"""
        # Initial evaluation
        for i in range(self.n_particles):
            fitness = self.objective_fn(self.positions[i])
            self.personal_best_fitness[i] = fitness

            if fitness > self.global_best_fitness:
                self.global_best_fitness = fitness
                self.global_best = self.positions[i].copy()

        for iteration in range(max_iterations):
            # Linearly decreasing beta
            beta = self.beta_max - (
                (self.beta_max - self.beta_min) * iteration / max_iterations
            )

            # Update mbest
            self._update_mbest()

            # Update each particle
            for i in range(self.n_particles):
                self._update_position(i, beta)

                # Evaluate
                fitness = self.objective_fn(self.positions[i])

                # Update personal best
                if fitness > self.personal_best_fitness[i]:
                    self.personal_best_fitness[i] = fitness
                    self.personal_best[i] = self.positions[i].copy()

                    # Update global best
                    if fitness > self.global_best_fitness:
                        self.global_best_fitness = fitness
                        self.global_best = self.positions[i].copy()

            self.iteration = iteration
            self.history.append(self.global_best_fitness)

        return self.global_best, self.global_best_fitness


@dataclass
class ParetoSolution:
    """Solution on Pareto front"""
    position: np.ndarray
    objectives: np.ndarray
    crowding_distance: float = 0.0


class MultiObjectivePSO:
    """
    Multi-Objective PSO (MOPSO).

    Uses Pareto dominance and crowding distance.
    """

    def __init__(
        self,
        objective_fns: List[Callable[[np.ndarray], float]],
        dimensions: int,
        n_particles: int = 50,
        archive_size: int = 100,
        bounds: Tuple[float, float] = (-10, 10)
    ):
        self.objective_fns = objective_fns
        self.n_objectives = len(objective_fns)
        self.dimensions = dimensions
        self.n_particles = n_particles
        self.archive_size = archive_size
        self.bounds = bounds

        # Initialize particles
        self.positions = np.random.uniform(
            bounds[0], bounds[1],
            (n_particles, dimensions)
        )
        self.velocities = np.random.uniform(-1, 1, (n_particles, dimensions))
        self.personal_best = self.positions.copy()

        # Archive (external Pareto set)
        self.archive: List[ParetoSolution] = []

        # PSO parameters
        self.inertia = 0.4
        self.cognitive = 1.5
        self.social = 1.5

        # History
        self.iteration = 0

    def _evaluate(self, position: np.ndarray) -> np.ndarray:
        """Evaluate all objectives"""
        return np.array([f(position) for f in self.objective_fns])

    def _dominates(self, a: np.ndarray, b: np.ndarray) -> bool:
        """Check if a dominates b (all objectives)"""
        return all(a >= b) and any(a > b)

    def _update_archive(self, position: np.ndarray, objectives: np.ndarray):
        """Update Pareto archive"""
        # Check if dominated by any archive member
        for sol in self.archive:
            if self._dominates(sol.objectives, objectives):
                return  # Dominated, don't add

        # Remove dominated solutions from archive
        self.archive = [
            sol for sol in self.archive
            if not self._dominates(objectives, sol.objectives)
        ]

        # Add new solution
        self.archive.append(ParetoSolution(
            position=position.copy(),
            objectives=objectives.copy()
        ))

        # Prune if too large
        if len(self.archive) > self.archive_size:
            self._prune_archive()

    def _prune_archive(self):
        """Prune archive using crowding distance"""
        self._calculate_crowding_distances()

        # Keep solutions with highest crowding distance
        self.archive.sort(key=lambda s: -s.crowding_distance)
        self.archive = self.archive[:self.archive_size]

    def _calculate_crowding_distances(self):
        """Calculate crowding distance for archive members"""
        n = len(self.archive)
        if n == 0:
            return

        for sol in self.archive:
            sol.crowding_distance = 0.0

        for m in range(self.n_objectives):
            # Sort by objective m
            sorted_archive = sorted(
                self.archive,
                key=lambda s: s.objectives[m]
            )

            # Boundary points get infinite distance
            sorted_archive[0].crowding_distance = float('inf')
            sorted_archive[-1].crowding_distance = float('inf')

            # Calculate for intermediate points
            obj_range = (
                sorted_archive[-1].objectives[m] -
                sorted_archive[0].objectives[m]
            )

            if obj_range == 0:
                continue

            for i in range(1, n - 1):
                sorted_archive[i].crowding_distance += (
                    sorted_archive[i + 1].objectives[m] -
                    sorted_archive[i - 1].objectives[m]
                ) / obj_range

    def _select_leader(self) -> np.ndarray:
        """Select leader from archive using crowding distance"""
        if not self.archive:
            return self.positions[0]

        # Roulette wheel based on crowding distance
        distances = [max(s.crowding_distance, 0.01) for s in self.archive]
        if any(d == float('inf') for d in distances):
            distances = [1 if d == float('inf') else 0.01 for d in distances]

        total = sum(distances)
        probs = [d / total for d in distances]

        idx = np.random.choice(len(self.archive), p=probs)
        return self.archive[idx].position

    def optimize(
        self,
        max_iterations: int = 100
    ) -> List[ParetoSolution]:
        """Run multi-objective optimization"""
        # Initial evaluation
        for i in range(self.n_particles):
            objectives = self._evaluate(self.positions[i])
            self._update_archive(self.positions[i], objectives)

        for iteration in range(max_iterations):
            for i in range(self.n_particles):
                # Select leader
                leader = self._select_leader()

                # Update velocity
                r1 = np.random.random(self.dimensions)
                r2 = np.random.random(self.dimensions)

                self.velocities[i] = (
                    self.inertia * self.velocities[i] +
                    self.cognitive * r1 * (self.personal_best[i] - self.positions[i]) +
                    self.social * r2 * (leader - self.positions[i])
                )

                # Update position
                self.positions[i] = self.positions[i] + self.velocities[i]
                self.positions[i] = np.clip(
                    self.positions[i],
                    self.bounds[0],
                    self.bounds[1]
                )

                # Evaluate
                objectives = self._evaluate(self.positions[i])

                # Update personal best (if dominates)
                pb_objectives = self._evaluate(self.personal_best[i])
                if self._dominates(objectives, pb_objectives):
                    self.personal_best[i] = self.positions[i].copy()

                # Update archive
                self._update_archive(self.positions[i], objectives)

            self.iteration = iteration

        return self.archive


# Export all
__all__ = [
    'PSOConfig',
    'Particle',
    'ParticleSwarm',
    'PSOptimizer',
    'AdaptivePSO',
    'QuantumPSO',
    'ParetoSolution',
    'MultiObjectivePSO',
]
