"""
⚡ ANT COLONY OPTIMIZATION ⚡
============================
Nature-inspired optimization using ant behavior.

Implements:
- Ant System (AS)
- Ant Colony System (ACS)
- Max-Min Ant System (MMAS)
- Continuous Ant Colony Optimization

Applications:
- Pathfinding (TSP, routing)
- Combinatorial optimization
- Graph search
- Scheduling
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
from .stigmergy import PheromoneField, PheromoneConfig


@dataclass
class AntConfig:
    """Configuration for ant agents"""
    alpha: float = 1.0      # Pheromone importance
    beta: float = 2.0       # Heuristic importance
    rho: float = 0.1        # Evaporation rate
    q: float = 100.0        # Pheromone deposit factor
    q0: float = 0.9         # Exploitation vs exploration (ACS)
    local_decay: float = 0.1  # Local pheromone decay (ACS)


class Ant(SwarmAgent):
    """
    Ant agent for ACO algorithms.
    """

    def __init__(
        self,
        agent_id: str,
        graph_size: int,
        ant_config: AntConfig = None
    ):
        # Initialize with graph size as dimension
        super().__init__(agent_id, graph_size)
        self.ant_config = ant_config or AntConfig()

        # Tour state
        self.current_node: int = 0
        self.visited: Set[int] = set()
        self.tour: List[int] = []
        self.tour_length: float = 0.0

        # Reset for new tour
        self.reset()

    def reset(self, start_node: int = None):
        """Reset ant for new tour"""
        if start_node is None:
            start_node = np.random.randint(0, self.dimensions)

        self.current_node = start_node
        self.visited = {start_node}
        self.tour = [start_node]
        self.tour_length = 0.0
        self.state = AgentState.EXPLORING

    def evaluate_fitness(self, position: Position) -> float:
        """Fitness is negative tour length (shorter is better)"""
        return -self.tour_length

    def update(self, environment: SwarmEnvironment):
        """Update called by environment - not used for ACO"""
        pass

    def select_next_node(
        self,
        pheromone_matrix: np.ndarray,
        distance_matrix: np.ndarray,
        available_nodes: List[int]
    ) -> int:
        """Select next node using pheromone and heuristic"""
        if not available_nodes:
            return self.tour[0]  # Return to start

        current = self.current_node

        # Calculate probabilities
        pheromones = pheromone_matrix[current, available_nodes]
        distances = distance_matrix[current, available_nodes]

        # Avoid division by zero
        distances = np.maximum(distances, 1e-10)

        # Heuristic: inverse distance
        heuristics = 1.0 / distances

        # Combined attractiveness
        attractiveness = (
            (pheromones ** self.ant_config.alpha) *
            (heuristics ** self.ant_config.beta)
        )

        # Normalize to probabilities
        total = np.sum(attractiveness)
        if total > 0:
            probabilities = attractiveness / total
        else:
            probabilities = np.ones(len(available_nodes)) / len(available_nodes)

        # Roulette wheel selection
        choice_idx = np.random.choice(len(available_nodes), p=probabilities)
        return available_nodes[choice_idx]

    def move_to(
        self,
        next_node: int,
        distance_matrix: np.ndarray
    ):
        """Move to next node"""
        distance = distance_matrix[self.current_node, next_node]
        self.tour_length += distance
        self.current_node = next_node
        self.visited.add(next_node)
        self.tour.append(next_node)

    def complete_tour(
        self,
        distance_matrix: np.ndarray
    ):
        """Complete tour by returning to start"""
        if len(self.tour) > 1 and self.tour[0] != self.tour[-1]:
            distance = distance_matrix[self.current_node, self.tour[0]]
            self.tour_length += distance
            self.tour.append(self.tour[0])
        self.state = AgentState.CONVERGING

    def get_pheromone_deposit(self) -> float:
        """Calculate pheromone to deposit"""
        if self.tour_length > 0:
            return self.ant_config.q / self.tour_length
        return 0


class AntColony:
    """
    Colony of ants for optimization.
    """

    def __init__(
        self,
        n_ants: int,
        graph_size: int,
        config: AntConfig = None
    ):
        self.n_ants = n_ants
        self.graph_size = graph_size
        self.config = config or AntConfig()

        # Create ants
        self.ants = [
            Ant(f"ant_{i}", graph_size, config)
            for i in range(n_ants)
        ]

        # Initialize pheromone matrix
        self.pheromone = np.ones((graph_size, graph_size))

        # Best solution tracking
        self.best_tour: List[int] = []
        self.best_length = float('inf')

        # Statistics
        self.iteration = 0
        self.history: List[float] = []

    def construct_solutions(
        self,
        distance_matrix: np.ndarray
    ):
        """Have all ants construct solutions"""
        for ant in self.ants:
            # Start from random node
            ant.reset(np.random.randint(0, self.graph_size))

            # Build tour
            while len(ant.visited) < self.graph_size:
                available = [
                    i for i in range(self.graph_size)
                    if i not in ant.visited
                ]

                if not available:
                    break

                next_node = ant.select_next_node(
                    self.pheromone,
                    distance_matrix,
                    available
                )
                ant.move_to(next_node, distance_matrix)

            # Complete tour
            ant.complete_tour(distance_matrix)

            # Update best
            if ant.tour_length < self.best_length:
                self.best_length = ant.tour_length
                self.best_tour = ant.tour.copy()

    def update_pheromones(self):
        """Update pheromone trails"""
        # Evaporation
        self.pheromone *= (1 - self.config.rho)

        # Deposit by all ants
        for ant in self.ants:
            deposit = ant.get_pheromone_deposit()
            for i in range(len(ant.tour) - 1):
                from_node = ant.tour[i]
                to_node = ant.tour[i + 1]
                self.pheromone[from_node, to_node] += deposit
                self.pheromone[to_node, from_node] += deposit

    def step(self, distance_matrix: np.ndarray):
        """Execute one iteration"""
        self.construct_solutions(distance_matrix)
        self.update_pheromones()
        self.iteration += 1
        self.history.append(self.best_length)


class ACOPathfinder:
    """
    ACO for shortest path finding.
    """

    def __init__(
        self,
        graph: Dict[int, List[Tuple[int, float]]],
        n_ants: int = 20,
        config: AntConfig = None
    ):
        self.graph = graph
        self.n_nodes = len(graph)
        self.n_ants = n_ants
        self.config = config or AntConfig()

        # Build distance matrix
        self.distance_matrix = self._build_distance_matrix()

        # Pheromone matrix
        self.pheromone = np.ones((self.n_nodes, self.n_nodes))

        # Path tracking
        self.best_path: List[int] = []
        self.best_distance = float('inf')

    def _build_distance_matrix(self) -> np.ndarray:
        """Build adjacency matrix from graph"""
        matrix = np.full((self.n_nodes, self.n_nodes), np.inf)
        np.fill_diagonal(matrix, 0)

        for node, edges in self.graph.items():
            for neighbor, distance in edges:
                matrix[node, neighbor] = distance

        return matrix

    def find_path(
        self,
        start: int,
        end: int,
        max_iterations: int = 100
    ) -> Tuple[List[int], float]:
        """Find shortest path from start to end"""
        for iteration in range(max_iterations):
            # Each ant builds a path
            for _ in range(self.n_ants):
                path, distance = self._build_path(start, end)

                if path and distance < self.best_distance:
                    self.best_distance = distance
                    self.best_path = path

            # Update pheromones
            self._update_pheromones()

        return self.best_path, self.best_distance

    def _build_path(
        self,
        start: int,
        end: int
    ) -> Tuple[List[int], float]:
        """Build single path from start to end"""
        current = start
        path = [current]
        visited = {current}
        total_distance = 0.0

        while current != end:
            # Get available neighbors
            neighbors = []
            for neighbor, dist in self.graph.get(current, []):
                if neighbor not in visited:
                    neighbors.append((neighbor, dist))

            if not neighbors:
                return [], float('inf')  # Dead end

            # Calculate selection probabilities
            probs = []
            for neighbor, dist in neighbors:
                pheromone = self.pheromone[current, neighbor]
                heuristic = 1.0 / max(dist, 1e-10)
                attractiveness = (
                    (pheromone ** self.config.alpha) *
                    (heuristic ** self.config.beta)
                )
                probs.append(attractiveness)

            # Normalize
            total_prob = sum(probs)
            probs = [p / total_prob for p in probs]

            # Select next
            idx = np.random.choice(len(neighbors), p=probs)
            next_node, dist = neighbors[idx]

            path.append(next_node)
            visited.add(next_node)
            total_distance += dist
            current = next_node

        return path, total_distance

    def _update_pheromones(self):
        """Update pheromone matrix"""
        # Evaporation
        self.pheromone *= (1 - self.config.rho)

        # Deposit on best path
        if self.best_path:
            deposit = self.config.q / self.best_distance
            for i in range(len(self.best_path) - 1):
                from_node = self.best_path[i]
                to_node = self.best_path[i + 1]
                self.pheromone[from_node, to_node] += deposit


class ACOOptimizer:
    """
    General-purpose ACO optimizer.
    """

    def __init__(
        self,
        objective_fn: Callable[[List[int]], float],
        n_items: int,
        n_ants: int = 30,
        config: AntConfig = None
    ):
        self.objective_fn = objective_fn
        self.n_items = n_items
        self.n_ants = n_ants
        self.config = config or AntConfig()

        # Pheromone matrix (item x position)
        self.pheromone = np.ones((n_items, n_items))

        # Best solution
        self.best_solution: List[int] = []
        self.best_fitness = float('-inf')

        # History
        self.history: List[float] = []

    def optimize(
        self,
        n_iterations: int = 100
    ) -> Tuple[List[int], float]:
        """Run optimization"""
        for iteration in range(n_iterations):
            solutions = []
            fitnesses = []

            # Construct solutions
            for _ in range(self.n_ants):
                solution = self._construct_solution()
                fitness = self.objective_fn(solution)
                solutions.append(solution)
                fitnesses.append(fitness)

                if fitness > self.best_fitness:
                    self.best_fitness = fitness
                    self.best_solution = solution.copy()

            # Update pheromones
            self._update_pheromones(solutions, fitnesses)
            self.history.append(self.best_fitness)

        return self.best_solution, self.best_fitness

    def _construct_solution(self) -> List[int]:
        """Construct solution using pheromone"""
        solution = []
        available = list(range(self.n_items))

        for position in range(self.n_items):
            if not available:
                break

            # Calculate probabilities
            pheromones = np.array([
                self.pheromone[item, position]
                for item in available
            ])

            probs = pheromones ** self.config.alpha
            probs /= probs.sum()

            # Select item
            idx = np.random.choice(len(available), p=probs)
            item = available.pop(idx)
            solution.append(item)

        return solution

    def _update_pheromones(
        self,
        solutions: List[List[int]],
        fitnesses: List[float]
    ):
        """Update pheromone matrix"""
        # Evaporation
        self.pheromone *= (1 - self.config.rho)

        # Deposit proportional to fitness
        min_fit = min(fitnesses)
        max_fit = max(fitnesses)
        range_fit = max_fit - min_fit + 1e-10

        for solution, fitness in zip(solutions, fitnesses):
            # Normalize fitness for deposit
            normalized = (fitness - min_fit) / range_fit
            deposit = self.config.q * normalized

            for position, item in enumerate(solution):
                self.pheromone[item, position] += deposit


class MaxMinAntSystem(AntColony):
    """
    Max-Min Ant System (MMAS).

    Features:
    - Only best ant deposits pheromone
    - Pheromone bounded between min and max
    - Pheromone smoothing
    """

    def __init__(
        self,
        n_ants: int,
        graph_size: int,
        config: AntConfig = None,
        tau_min: float = 0.01,
        tau_max: float = 10.0
    ):
        super().__init__(n_ants, graph_size, config)
        self.tau_min = tau_min
        self.tau_max = tau_max

        # Initialize at max
        self.pheromone.fill(tau_max)

        # Best-so-far and iteration-best
        self.iteration_best_tour: List[int] = []
        self.iteration_best_length = float('inf')

    def update_pheromones(self):
        """MMAS pheromone update"""
        # Evaporation
        self.pheromone *= (1 - self.config.rho)

        # Find iteration best
        self.iteration_best_length = float('inf')
        self.iteration_best_tour = []

        for ant in self.ants:
            if ant.tour_length < self.iteration_best_length:
                self.iteration_best_length = ant.tour_length
                self.iteration_best_tour = ant.tour.copy()

        # Deposit by best (alternate between iteration and global best)
        if np.random.random() < 0.5 or not self.best_tour:
            best_tour = self.iteration_best_tour
            best_length = self.iteration_best_length
        else:
            best_tour = self.best_tour
            best_length = self.best_length

        if best_length < float('inf'):
            deposit = self.config.q / best_length
            for i in range(len(best_tour) - 1):
                from_node = best_tour[i]
                to_node = best_tour[i + 1]
                self.pheromone[from_node, to_node] += deposit
                self.pheromone[to_node, from_node] += deposit

        # Bound pheromones
        self.pheromone = np.clip(self.pheromone, self.tau_min, self.tau_max)


class AntColonySystem(AntColony):
    """
    Ant Colony System (ACS).

    Features:
    - Pseudo-random proportional rule
    - Local pheromone update
    - Global pheromone update by best ant only
    """

    def __init__(
        self,
        n_ants: int,
        graph_size: int,
        config: AntConfig = None
    ):
        super().__init__(n_ants, graph_size, config)
        self.initial_pheromone = 1.0 / graph_size
        self.pheromone.fill(self.initial_pheromone)

    def construct_solutions(
        self,
        distance_matrix: np.ndarray
    ):
        """ACS solution construction with local update"""
        for ant in self.ants:
            ant.reset(np.random.randint(0, self.graph_size))

            while len(ant.visited) < self.graph_size:
                available = [
                    i for i in range(self.graph_size)
                    if i not in ant.visited
                ]

                if not available:
                    break

                # Pseudo-random proportional rule
                if np.random.random() < self.config.q0:
                    # Exploitation: choose best
                    next_node = self._choose_best(
                        ant.current_node,
                        available,
                        distance_matrix
                    )
                else:
                    # Exploration: probabilistic
                    next_node = ant.select_next_node(
                        self.pheromone,
                        distance_matrix,
                        available
                    )

                # Local pheromone update
                self._local_update(ant.current_node, next_node)

                ant.move_to(next_node, distance_matrix)

            ant.complete_tour(distance_matrix)

            if ant.tour_length < self.best_length:
                self.best_length = ant.tour_length
                self.best_tour = ant.tour.copy()

    def _choose_best(
        self,
        current: int,
        available: List[int],
        distance_matrix: np.ndarray
    ) -> int:
        """Choose best node (exploitation)"""
        best_node = available[0]
        best_value = -1

        for node in available:
            pheromone = self.pheromone[current, node]
            distance = distance_matrix[current, node]
            heuristic = 1.0 / max(distance, 1e-10)

            value = pheromone * (heuristic ** self.config.beta)
            if value > best_value:
                best_value = value
                best_node = node

        return best_node

    def _local_update(self, from_node: int, to_node: int):
        """Local pheromone update"""
        decay = self.config.local_decay
        self.pheromone[from_node, to_node] = (
            (1 - decay) * self.pheromone[from_node, to_node] +
            decay * self.initial_pheromone
        )
        self.pheromone[to_node, from_node] = self.pheromone[from_node, to_node]

    def update_pheromones(self):
        """ACS global pheromone update - best ant only"""
        if not self.best_tour or self.best_length >= float('inf'):
            return

        deposit = self.config.q / self.best_length

        for i in range(len(self.best_tour) - 1):
            from_node = self.best_tour[i]
            to_node = self.best_tour[i + 1]

            # Update
            self.pheromone[from_node, to_node] = (
                (1 - self.config.rho) * self.pheromone[from_node, to_node] +
                self.config.rho * deposit
            )
            self.pheromone[to_node, from_node] = self.pheromone[from_node, to_node]


# Export all
__all__ = [
    'AntConfig',
    'Ant',
    'AntColony',
    'ACOPathfinder',
    'ACOOptimizer',
    'MaxMinAntSystem',
    'AntColonySystem',
]
