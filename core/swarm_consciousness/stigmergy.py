"""
⚡ STIGMERGY SYSTEM ⚡
=====================
Indirect coordination through environmental modification.

Stigmergy enables:
- Decentralized coordination without direct communication
- Persistent environmental memory
- Emergent pathways and structures
- Self-reinforcing solutions
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid


@dataclass
class Pheromone:
    """A single pheromone deposit"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pheromone_type: str = "default"
    position: np.ndarray = None
    intensity: float = 1.0
    decay_rate: float = 0.01
    spread_rate: float = 0.0
    creation_time: datetime = field(default_factory=datetime.now)
    creator_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def decay(self, dt: float = 1.0) -> bool:
        """Apply decay, returns True if still active"""
        self.intensity *= (1 - self.decay_rate * dt)
        return self.intensity > 0.001

    def spread(self, positions: List[np.ndarray]) -> List['Pheromone']:
        """Create spread deposits at nearby positions"""
        if self.spread_rate <= 0:
            return []

        spread_deposits = []
        spread_intensity = self.intensity * self.spread_rate

        for pos in positions:
            spread_pheromone = Pheromone(
                pheromone_type=self.pheromone_type,
                position=pos,
                intensity=spread_intensity,
                decay_rate=self.decay_rate * 2,  # Faster decay for spread
                spread_rate=0,  # No recursive spreading
                creator_id=self.creator_id
            )
            spread_deposits.append(spread_pheromone)

        return spread_deposits


class PheromoneType(Enum):
    """Standard pheromone types"""
    TRAIL = auto()      # Path marking
    FOOD = auto()       # Resource found
    DANGER = auto()     # Hazard warning
    HOME = auto()       # Return path
    EXPLORE = auto()    # Explored area
    SUCCESS = auto()    # Solution found
    FAILURE = auto()    # Dead end


@dataclass
class PheromoneConfig:
    """Configuration for pheromone system"""
    initial_intensity: float = 1.0
    decay_rate: float = 0.05
    min_intensity: float = 0.001
    max_intensity: float = 100.0
    spread_radius: float = 0.5
    diffusion_rate: float = 0.1
    evaporation_rate: float = 0.02


class PheromoneField:
    """
    Continuous pheromone field in N-dimensional space.

    Uses spatial hashing for efficient queries.
    """

    def __init__(
        self,
        dimensions: int,
        config: PheromoneConfig = None,
        cell_size: float = 1.0
    ):
        self.dimensions = dimensions
        self.config = config or PheromoneConfig()
        self.cell_size = cell_size

        # Spatial hash map: cell_key -> pheromone_type -> intensity
        self.field: Dict[Tuple[int, ...], Dict[str, float]] = {}

        # Active pheromone deposits
        self.deposits: List[Pheromone] = []

        # Statistics
        self.total_deposits = 0
        self.total_evaporated = 0

    def _position_to_cell(self, position: np.ndarray) -> Tuple[int, ...]:
        """Convert position to cell key"""
        return tuple(int(p / self.cell_size) for p in position)

    def _cell_to_position(self, cell: Tuple[int, ...]) -> np.ndarray:
        """Get center position of cell"""
        return np.array([c * self.cell_size + self.cell_size / 2 for c in cell])

    def deposit(
        self,
        position: np.ndarray,
        pheromone_type: str,
        intensity: float = None,
        creator_id: str = ""
    ):
        """Deposit pheromone at position"""
        if intensity is None:
            intensity = self.config.initial_intensity

        cell = self._position_to_cell(position)

        if cell not in self.field:
            self.field[cell] = {}

        current = self.field[cell].get(pheromone_type, 0)
        new_intensity = min(
            current + intensity,
            self.config.max_intensity
        )
        self.field[cell][pheromone_type] = new_intensity

        # Track deposit
        deposit = Pheromone(
            pheromone_type=pheromone_type,
            position=position,
            intensity=intensity,
            decay_rate=self.config.decay_rate,
            creator_id=creator_id
        )
        self.deposits.append(deposit)
        self.total_deposits += 1

    def sense(
        self,
        position: np.ndarray,
        pheromone_type: str,
        radius: float = None
    ) -> float:
        """Sense pheromone intensity at position"""
        if radius is None:
            radius = self.cell_size

        cell = self._position_to_cell(position)
        total_intensity = 0.0

        # Check cells within radius
        cell_radius = int(radius / self.cell_size) + 1

        for offset in self._get_neighbor_offsets(cell_radius):
            neighbor_cell = tuple(c + o for c, o in zip(cell, offset))

            if neighbor_cell in self.field:
                intensity = self.field[neighbor_cell].get(pheromone_type, 0)

                # Distance-based attenuation
                cell_center = self._cell_to_position(neighbor_cell)
                distance = np.linalg.norm(position - cell_center)
                attenuation = 1.0 / (1.0 + distance / self.cell_size)

                total_intensity += intensity * attenuation

        return total_intensity

    def sense_gradient(
        self,
        position: np.ndarray,
        pheromone_type: str,
        step_size: float = 0.1
    ) -> np.ndarray:
        """Compute gradient of pheromone field"""
        gradient = np.zeros(self.dimensions)

        current_intensity = self.sense(position, pheromone_type)

        for d in range(self.dimensions):
            # Forward difference
            pos_plus = position.copy()
            pos_plus[d] += step_size
            intensity_plus = self.sense(pos_plus, pheromone_type)

            # Backward difference
            pos_minus = position.copy()
            pos_minus[d] -= step_size
            intensity_minus = self.sense(pos_minus, pheromone_type)

            # Central difference
            gradient[d] = (intensity_plus - intensity_minus) / (2 * step_size)

        return gradient

    def _get_neighbor_offsets(self, radius: int) -> List[Tuple[int, ...]]:
        """Get neighbor cell offsets within radius"""
        if self.dimensions == 1:
            return [(i,) for i in range(-radius, radius + 1)]
        elif self.dimensions == 2:
            offsets = []
            for i in range(-radius, radius + 1):
                for j in range(-radius, radius + 1):
                    if i*i + j*j <= radius*radius:
                        offsets.append((i, j))
            return offsets
        else:
            # For higher dimensions, use Manhattan distance approximation
            offsets = []
            for d in range(self.dimensions):
                for i in range(-radius, radius + 1):
                    offset = [0] * self.dimensions
                    offset[d] = i
                    offsets.append(tuple(offset))
            return list(set(offsets))

    def evaporate(self, dt: float = 1.0):
        """Apply evaporation to entire field"""
        decay_factor = 1 - self.config.evaporation_rate * dt

        cells_to_remove = []

        for cell in self.field:
            types_to_remove = []

            for ptype in self.field[cell]:
                self.field[cell][ptype] *= decay_factor

                if self.field[cell][ptype] < self.config.min_intensity:
                    types_to_remove.append(ptype)
                    self.total_evaporated += 1

            for ptype in types_to_remove:
                del self.field[cell][ptype]

            if not self.field[cell]:
                cells_to_remove.append(cell)

        for cell in cells_to_remove:
            del self.field[cell]

    def diffuse(self, dt: float = 1.0):
        """Apply diffusion to spread pheromones"""
        if self.config.diffusion_rate <= 0:
            return

        diffusion_amount = self.config.diffusion_rate * dt
        new_field: Dict[Tuple[int, ...], Dict[str, float]] = {}

        for cell, pheromones in self.field.items():
            for ptype, intensity in pheromones.items():
                # Keep some in original cell
                keep = intensity * (1 - diffusion_amount)
                spread = intensity * diffusion_amount / (2 * self.dimensions)

                # Add to original
                if cell not in new_field:
                    new_field[cell] = {}
                new_field[cell][ptype] = new_field[cell].get(ptype, 0) + keep

                # Spread to neighbors
                for d in range(self.dimensions):
                    for delta in [-1, 1]:
                        neighbor = list(cell)
                        neighbor[d] += delta
                        neighbor = tuple(neighbor)

                        if neighbor not in new_field:
                            new_field[neighbor] = {}
                        new_field[neighbor][ptype] = (
                            new_field[neighbor].get(ptype, 0) + spread
                        )

        self.field = new_field

    def step(self, dt: float = 1.0):
        """Execute one time step"""
        self.evaporate(dt)
        self.diffuse(dt)

    def get_hotspots(
        self,
        pheromone_type: str,
        threshold: float = 0.5
    ) -> List[Tuple[np.ndarray, float]]:
        """Find high-intensity regions"""
        hotspots = []

        for cell, pheromones in self.field.items():
            intensity = pheromones.get(pheromone_type, 0)
            if intensity >= threshold:
                position = self._cell_to_position(cell)
                hotspots.append((position, intensity))

        # Sort by intensity
        hotspots.sort(key=lambda x: -x[1])
        return hotspots


class StigmergicMemory:
    """
    Memory system based on pheromone trails.

    Uses pheromone patterns to store and retrieve information.
    """

    def __init__(self, dimensions: int = 10):
        self.dimensions = dimensions
        self.field = PheromoneField(dimensions)

        # Type for different memory categories
        self.memory_types = {
            'knowledge': 'mem_knowledge',
            'experience': 'mem_experience',
            'skill': 'mem_skill',
            'association': 'mem_association'
        }

    def encode(self, key: str) -> np.ndarray:
        """Encode key as position"""
        # Hash key to position
        np.random.seed(hash(key) % (2**31))
        return np.random.uniform(-10, 10, self.dimensions)

    def store(
        self,
        key: str,
        value: Any,
        memory_type: str = 'knowledge',
        strength: float = 1.0
    ):
        """Store memory at encoded position"""
        position = self.encode(key)
        ptype = self.memory_types.get(memory_type, memory_type)

        # Store value hash in metadata
        value_position = self.encode(str(value))

        # Create trail from key to value
        steps = 10
        for i in range(steps + 1):
            t = i / steps
            intermediate = position * (1 - t) + value_position * t
            self.field.deposit(intermediate, ptype, strength / steps)

    def recall(
        self,
        key: str,
        memory_type: str = 'knowledge'
    ) -> float:
        """Recall memory strength"""
        position = self.encode(key)
        ptype = self.memory_types.get(memory_type, memory_type)
        return self.field.sense(position, ptype)

    def associate(
        self,
        key1: str,
        key2: str,
        strength: float = 1.0
    ):
        """Create association between two memories"""
        pos1 = self.encode(key1)
        pos2 = self.encode(key2)

        # Trail between positions
        steps = 10
        for i in range(steps + 1):
            t = i / steps
            intermediate = pos1 * (1 - t) + pos2 * t
            self.field.deposit(intermediate, 'mem_association', strength / steps)

    def find_associations(
        self,
        key: str,
        threshold: float = 0.1
    ) -> List[Tuple[np.ndarray, float]]:
        """Find associated memories via gradient following"""
        position = self.encode(key)

        # Follow gradient to find peaks
        associations = []
        current = position.copy()

        for _ in range(100):
            gradient = self.field.sense_gradient(current, 'mem_association')

            if np.linalg.norm(gradient) < 0.01:
                break

            current = current + gradient * 0.1
            intensity = self.field.sense(current, 'mem_association')

            if intensity > threshold:
                associations.append((current.copy(), intensity))

        return associations

    def decay(self, dt: float = 1.0):
        """Apply memory decay"""
        self.field.step(dt)


class DigitalPheromoneSystem:
    """
    Complete digital pheromone system for coordination.
    """

    def __init__(
        self,
        dimensions: int = 2,
        config: PheromoneConfig = None
    ):
        self.dimensions = dimensions
        self.config = config or PheromoneConfig()
        self.field = PheromoneField(dimensions, config)

        # Registered agents
        self.agents: Dict[str, np.ndarray] = {}

        # Pheromone types for coordination
        self.coordination_types = {
            'task': 'coord_task',
            'request': 'coord_request',
            'complete': 'coord_complete',
            'help': 'coord_help',
            'avoid': 'coord_avoid'
        }

    def register_agent(self, agent_id: str, position: np.ndarray):
        """Register agent in system"""
        self.agents[agent_id] = position.copy()

    def update_position(self, agent_id: str, position: np.ndarray):
        """Update agent position"""
        self.agents[agent_id] = position.copy()

    def signal_task(
        self,
        agent_id: str,
        task_intensity: float = 1.0
    ):
        """Signal task at current position"""
        if agent_id in self.agents:
            self.field.deposit(
                self.agents[agent_id],
                self.coordination_types['task'],
                task_intensity,
                agent_id
            )

    def signal_completion(
        self,
        agent_id: str,
        intensity: float = 1.0
    ):
        """Signal task completion"""
        if agent_id in self.agents:
            self.field.deposit(
                self.agents[agent_id],
                self.coordination_types['complete'],
                intensity,
                agent_id
            )

    def request_help(
        self,
        agent_id: str,
        urgency: float = 1.0
    ):
        """Request help at current position"""
        if agent_id in self.agents:
            self.field.deposit(
                self.agents[agent_id],
                self.coordination_types['help'],
                urgency,
                agent_id
            )

    def find_tasks(
        self,
        agent_id: str,
        radius: float = 5.0
    ) -> List[Tuple[np.ndarray, float]]:
        """Find nearby tasks"""
        if agent_id not in self.agents:
            return []

        position = self.agents[agent_id]
        return self.field.get_hotspots(
            self.coordination_types['task'],
            threshold=0.1
        )

    def find_help_requests(
        self,
        agent_id: str
    ) -> List[Tuple[np.ndarray, float]]:
        """Find nearby help requests"""
        if agent_id not in self.agents:
            return []

        return self.field.get_hotspots(
            self.coordination_types['help'],
            threshold=0.1
        )

    def step(self, dt: float = 1.0):
        """Update pheromone system"""
        self.field.step(dt)


class StigmergicCoordination:
    """
    High-level stigmergic coordination system.

    Coordinates multiple agents through pheromone-based communication.
    """

    def __init__(self, dimensions: int = 2):
        self.pheromone_system = DigitalPheromoneSystem(dimensions)
        self.task_queue: List[Dict[str, Any]] = []
        self.completed_tasks: List[Dict[str, Any]] = []

    def submit_task(
        self,
        task_id: str,
        position: np.ndarray,
        priority: float = 1.0
    ):
        """Submit task to coordination system"""
        task = {
            'id': task_id,
            'position': position,
            'priority': priority,
            'status': 'pending',
            'assigned_to': None
        }
        self.task_queue.append(task)

        # Deposit pheromone at task location
        self.pheromone_system.field.deposit(
            position,
            'coord_task',
            priority
        )

    def claim_task(
        self,
        agent_id: str,
        task_id: str
    ) -> bool:
        """Agent claims task"""
        for task in self.task_queue:
            if task['id'] == task_id and task['status'] == 'pending':
                task['status'] = 'claimed'
                task['assigned_to'] = agent_id
                return True
        return False

    def complete_task(
        self,
        agent_id: str,
        task_id: str
    ):
        """Mark task as complete"""
        for task in self.task_queue:
            if task['id'] == task_id and task['assigned_to'] == agent_id:
                task['status'] = 'completed'
                self.completed_tasks.append(task)

                # Deposit completion pheromone
                self.pheromone_system.field.deposit(
                    task['position'],
                    'coord_complete',
                    1.0,
                    agent_id
                )
                break

    def get_best_task(
        self,
        agent_id: str,
        agent_position: np.ndarray
    ) -> Optional[Dict[str, Any]]:
        """Get best task for agent based on pheromones and distance"""
        pending = [t for t in self.task_queue if t['status'] == 'pending']

        if not pending:
            return None

        # Score tasks by priority and proximity
        scored = []
        for task in pending:
            distance = np.linalg.norm(agent_position - task['position'])
            pheromone = self.pheromone_system.field.sense(
                task['position'], 'coord_task'
            )

            # Higher pheromone and closer distance = better
            score = task['priority'] * pheromone / (1 + distance)
            scored.append((score, task))

        scored.sort(key=lambda x: -x[0])
        return scored[0][1] if scored else None

    def step(self):
        """Update coordination system"""
        self.pheromone_system.step()

        # Remove completed tasks from queue
        self.task_queue = [
            t for t in self.task_queue if t['status'] != 'completed'
        ]


# Export all
__all__ = [
    'Pheromone',
    'PheromoneType',
    'PheromoneConfig',
    'PheromoneField',
    'StigmergicMemory',
    'DigitalPheromoneSystem',
    'StigmergicCoordination',
]
