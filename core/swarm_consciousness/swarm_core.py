"""
⚡ SWARM CORE ⚡
===============
Foundation for swarm intelligence systems.

Provides base abstractions for:
- Swarm agents with local behavior
- Message passing between agents
- Environment for agent interaction
- Emergent behavior detection
"""

import math
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union, TypeVar, Generic
)
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading


class AgentState(Enum):
    """Agent lifecycle states"""
    IDLE = auto()
    EXPLORING = auto()
    EXPLOITING = auto()
    COMMUNICATING = auto()
    CONVERGING = auto()
    TERMINATED = auto()


@dataclass
class Position:
    """N-dimensional position in search space"""
    coordinates: np.ndarray

    @classmethod
    def random(cls, dimensions: int, bounds: Tuple[float, float] = (-1, 1)) -> 'Position':
        """Create random position"""
        coords = np.random.uniform(bounds[0], bounds[1], dimensions)
        return cls(coordinates=coords)

    def distance(self, other: 'Position') -> float:
        """Euclidean distance to another position"""
        return float(np.linalg.norm(self.coordinates - other.coordinates))

    def __add__(self, other: 'Position') -> 'Position':
        return Position(coordinates=self.coordinates + other.coordinates)

    def __sub__(self, other: 'Position') -> 'Position':
        return Position(coordinates=self.coordinates - other.coordinates)

    def __mul__(self, scalar: float) -> 'Position':
        return Position(coordinates=self.coordinates * scalar)


@dataclass
class SwarmMessage:
    """Message for agent communication"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    message_type: str = "info"
    content: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    ttl: int = 10  # Time to live (hops)
    priority: float = 0.5

    def decay(self) -> bool:
        """Decay TTL, returns True if still alive"""
        self.ttl -= 1
        return self.ttl > 0


@dataclass
class SwarmAgentConfig:
    """Configuration for swarm agent"""
    exploration_rate: float = 0.3
    communication_range: float = 1.0
    memory_size: int = 100
    learning_rate: float = 0.1
    inertia: float = 0.7
    social_weight: float = 1.5
    cognitive_weight: float = 1.5


class SwarmAgent(ABC):
    """
    Base class for swarm agents.

    Each agent has:
    - Position in search space
    - Local memory
    - Communication capability
    - Behavior rules
    """

    def __init__(
        self,
        agent_id: str,
        dimensions: int,
        config: SwarmAgentConfig = None
    ):
        self.id = agent_id
        self.dimensions = dimensions
        self.config = config or SwarmAgentConfig()

        self.position = Position.random(dimensions)
        self.velocity = Position(np.zeros(dimensions))
        self.state = AgentState.IDLE

        # Personal best
        self.best_position = self.position
        self.best_fitness = float('-inf')

        # Memory
        self.memory: List[Any] = []
        self.inbox: List[SwarmMessage] = []
        self.outbox: List[SwarmMessage] = []

        # Neighbors
        self.neighbors: Set[str] = set()

        # Statistics
        self.steps = 0
        self.evaluations = 0

    @abstractmethod
    def evaluate_fitness(self, position: Position) -> float:
        """Evaluate fitness at position"""
        pass

    @abstractmethod
    def update(self, environment: 'SwarmEnvironment'):
        """Update agent state based on environment"""
        pass

    def move(self, new_position: Position):
        """Move to new position"""
        self.position = new_position
        fitness = self.evaluate_fitness(new_position)
        self.evaluations += 1

        if fitness > self.best_fitness:
            self.best_fitness = fitness
            self.best_position = new_position

        return fitness

    def send_message(
        self,
        message_type: str,
        content: Any,
        priority: float = 0.5
    ):
        """Queue message for sending"""
        msg = SwarmMessage(
            sender_id=self.id,
            message_type=message_type,
            content=content,
            priority=priority
        )
        self.outbox.append(msg)

    def receive_message(self, message: SwarmMessage):
        """Receive incoming message"""
        self.inbox.append(message)

    def process_messages(self):
        """Process inbox"""
        messages = sorted(self.inbox, key=lambda m: -m.priority)
        self.inbox.clear()
        return messages

    def remember(self, item: Any):
        """Add to memory with LRU eviction"""
        self.memory.append(item)
        if len(self.memory) > self.config.memory_size:
            self.memory.pop(0)

    def step(self, environment: 'SwarmEnvironment'):
        """Execute one step"""
        self.steps += 1
        self.update(environment)


@dataclass
class EnvironmentCell:
    """Cell in environment grid"""
    position: Tuple[int, ...]
    pheromones: Dict[str, float] = field(default_factory=dict)
    occupants: Set[str] = field(default_factory=set)
    resources: Dict[str, float] = field(default_factory=dict)


class SwarmEnvironment:
    """
    Environment for swarm agents.

    Provides:
    - Spatial structure
    - Pheromone deposition
    - Agent localization
    - Resource management
    """

    def __init__(
        self,
        dimensions: int,
        bounds: Tuple[float, float] = (-10, 10),
        resolution: int = 100
    ):
        self.dimensions = dimensions
        self.bounds = bounds
        self.resolution = resolution

        # Grid for discrete environment
        self.cell_size = (bounds[1] - bounds[0]) / resolution
        self.grid: Dict[Tuple[int, ...], EnvironmentCell] = {}

        # Agents
        self.agents: Dict[str, SwarmAgent] = {}

        # Global best
        self.global_best_position: Optional[Position] = None
        self.global_best_fitness = float('-inf')

        # Pheromone evaporation
        self.evaporation_rate = 0.1

        # Message queue
        self.message_queue: List[SwarmMessage] = []

    def position_to_cell(self, position: Position) -> Tuple[int, ...]:
        """Convert continuous position to grid cell"""
        cell_idx = tuple(
            int((coord - self.bounds[0]) / self.cell_size)
            for coord in position.coordinates
        )
        return cell_idx

    def get_cell(self, position: Position) -> EnvironmentCell:
        """Get or create cell at position"""
        cell_idx = self.position_to_cell(position)
        if cell_idx not in self.grid:
            self.grid[cell_idx] = EnvironmentCell(position=cell_idx)
        return self.grid[cell_idx]

    def add_agent(self, agent: SwarmAgent):
        """Add agent to environment"""
        self.agents[agent.id] = agent
        cell = self.get_cell(agent.position)
        cell.occupants.add(agent.id)

    def remove_agent(self, agent_id: str):
        """Remove agent from environment"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            cell = self.get_cell(agent.position)
            cell.occupants.discard(agent_id)
            del self.agents[agent_id]

    def move_agent(self, agent: SwarmAgent, new_position: Position):
        """Move agent to new position"""
        old_cell = self.get_cell(agent.position)
        old_cell.occupants.discard(agent.id)

        new_cell = self.get_cell(new_position)
        new_cell.occupants.add(agent.id)

        fitness = agent.move(new_position)

        if fitness > self.global_best_fitness:
            self.global_best_fitness = fitness
            self.global_best_position = new_position

        return fitness

    def deposit_pheromone(
        self,
        position: Position,
        pheromone_type: str,
        amount: float
    ):
        """Deposit pheromone at position"""
        cell = self.get_cell(position)
        cell.pheromones[pheromone_type] = (
            cell.pheromones.get(pheromone_type, 0) + amount
        )

    def sense_pheromone(
        self,
        position: Position,
        pheromone_type: str,
        radius: float = 1.0
    ) -> float:
        """Sense pheromone level around position"""
        total = 0.0
        center_cell = self.position_to_cell(position)

        # Check nearby cells
        cell_radius = int(radius / self.cell_size) + 1

        for offset in self._get_neighbor_offsets(cell_radius):
            cell_idx = tuple(c + o for c, o in zip(center_cell, offset))
            if cell_idx in self.grid:
                cell = self.grid[cell_idx]
                distance = sum((a - b) ** 2 for a, b in zip(center_cell, cell_idx)) ** 0.5
                decay = 1.0 / (1.0 + distance)
                total += cell.pheromones.get(pheromone_type, 0) * decay

        return total

    def _get_neighbor_offsets(self, radius: int) -> List[Tuple[int, ...]]:
        """Get all neighbor offsets within radius"""
        if self.dimensions == 1:
            return [(i,) for i in range(-radius, radius + 1)]
        elif self.dimensions == 2:
            offsets = []
            for i in range(-radius, radius + 1):
                for j in range(-radius, radius + 1):
                    offsets.append((i, j))
            return offsets
        else:
            # General case - limit search for high dimensions
            offsets = [(0,) * self.dimensions]
            for d in range(self.dimensions):
                for i in [-1, 0, 1]:
                    offset = [0] * self.dimensions
                    offset[d] = i
                    offsets.append(tuple(offset))
            return offsets

    def evaporate_pheromones(self):
        """Apply evaporation to all pheromones"""
        for cell in self.grid.values():
            for ptype in list(cell.pheromones.keys()):
                cell.pheromones[ptype] *= (1 - self.evaporation_rate)
                if cell.pheromones[ptype] < 0.001:
                    del cell.pheromones[ptype]

    def get_neighbors(
        self,
        agent: SwarmAgent,
        radius: float
    ) -> List[SwarmAgent]:
        """Get agents within radius"""
        neighbors = []
        for other_id, other in self.agents.items():
            if other_id != agent.id:
                dist = agent.position.distance(other.position)
                if dist <= radius:
                    neighbors.append(other)
        return neighbors

    def broadcast_message(self, message: SwarmMessage):
        """Broadcast message to all agents"""
        for agent in self.agents.values():
            if agent.id != message.sender_id:
                agent.receive_message(message)

    def route_messages(self):
        """Route messages between agents based on proximity"""
        for agent in self.agents.values():
            for msg in agent.outbox:
                neighbors = self.get_neighbors(
                    agent, agent.config.communication_range
                )
                for neighbor in neighbors:
                    if msg.decay():
                        neighbor.receive_message(msg)
            agent.outbox.clear()

    def step(self):
        """Execute one environment step"""
        # Update all agents
        for agent in self.agents.values():
            agent.step(self)

        # Route messages
        self.route_messages()

        # Evaporate pheromones
        self.evaporate_pheromones()


class SwarmCoordinator:
    """
    Coordinates swarm behavior.

    Provides:
    - Swarm initialization
    - Execution scheduling
    - Convergence detection
    - Result aggregation
    """

    def __init__(
        self,
        environment: SwarmEnvironment,
        max_iterations: int = 1000,
        convergence_threshold: float = 1e-6
    ):
        self.environment = environment
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold

        self.iteration = 0
        self.history: List[float] = []
        self.converged = False

    def run(self) -> Tuple[Position, float]:
        """Run swarm until convergence or max iterations"""
        prev_best = float('-inf')
        stagnation_count = 0

        for i in range(self.max_iterations):
            self.iteration = i
            self.environment.step()

            current_best = self.environment.global_best_fitness
            self.history.append(current_best)

            # Check convergence
            improvement = current_best - prev_best
            if improvement < self.convergence_threshold:
                stagnation_count += 1
                if stagnation_count > 50:
                    self.converged = True
                    break
            else:
                stagnation_count = 0

            prev_best = current_best

        return (
            self.environment.global_best_position,
            self.environment.global_best_fitness
        )

    async def run_async(self) -> Tuple[Position, float]:
        """Run swarm asynchronously"""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, self.run)
        return result


@dataclass
class EmergentBehavior:
    """Detected emergent behavior pattern"""
    name: str
    description: str
    agents_involved: List[str]
    strength: float  # 0-1
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmergentBehaviorDetector:
    """
    Detects emergent patterns in swarm behavior.
    """

    def __init__(self, environment: SwarmEnvironment):
        self.environment = environment
        self.detected_behaviors: List[EmergentBehavior] = []

    def detect_clustering(self, threshold: float = 2.0) -> List[EmergentBehavior]:
        """Detect agent clustering"""
        clusters = []
        visited = set()

        for agent in self.environment.agents.values():
            if agent.id in visited:
                continue

            cluster = [agent.id]
            visited.add(agent.id)

            # BFS to find cluster
            queue = [agent]
            while queue:
                current = queue.pop(0)
                neighbors = self.environment.get_neighbors(current, threshold)
                for neighbor in neighbors:
                    if neighbor.id not in visited:
                        visited.add(neighbor.id)
                        cluster.append(neighbor.id)
                        queue.append(neighbor)

            if len(cluster) > 1:
                clusters.append(cluster)

        # Create behavior objects
        behaviors = []
        for cluster in clusters:
            behavior = EmergentBehavior(
                name="clustering",
                description=f"Cluster of {len(cluster)} agents",
                agents_involved=cluster,
                strength=len(cluster) / len(self.environment.agents)
            )
            behaviors.append(behavior)

        self.detected_behaviors.extend(behaviors)
        return behaviors

    def detect_convergence(self, threshold: float = 0.1) -> Optional[EmergentBehavior]:
        """Detect swarm convergence"""
        if not self.environment.global_best_position:
            return None

        # Count agents near global best
        target = self.environment.global_best_position
        near_count = 0
        agents_near = []

        for agent in self.environment.agents.values():
            dist = agent.position.distance(target)
            if dist < threshold:
                near_count += 1
                agents_near.append(agent.id)

        if near_count > len(self.environment.agents) * 0.8:
            behavior = EmergentBehavior(
                name="convergence",
                description="Swarm has converged to optimum",
                agents_involved=agents_near,
                strength=near_count / len(self.environment.agents)
            )
            self.detected_behaviors.append(behavior)
            return behavior

        return None

    def detect_oscillation(
        self,
        history: List[float],
        window: int = 20
    ) -> Optional[EmergentBehavior]:
        """Detect oscillating behavior"""
        if len(history) < window * 2:
            return None

        recent = history[-window:]
        previous = history[-window*2:-window]

        # Check for alternating pattern
        ups = sum(1 for i in range(len(recent)-1) if recent[i+1] > recent[i])
        downs = sum(1 for i in range(len(recent)-1) if recent[i+1] < recent[i])

        if min(ups, downs) > window * 0.4:
            behavior = EmergentBehavior(
                name="oscillation",
                description="Swarm exhibiting oscillatory behavior",
                agents_involved=list(self.environment.agents.keys()),
                strength=min(ups, downs) / (window - 1)
            )
            self.detected_behaviors.append(behavior)
            return behavior

        return None


# Export all
__all__ = [
    'AgentState',
    'Position',
    'SwarmMessage',
    'SwarmAgentConfig',
    'SwarmAgent',
    'EnvironmentCell',
    'SwarmEnvironment',
    'SwarmCoordinator',
    'EmergentBehavior',
    'EmergentBehaviorDetector',
]
