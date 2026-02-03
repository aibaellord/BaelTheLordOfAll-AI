#!/usr/bin/env python3
"""
BAEL - Emergent Behavior System
Self-organizing and emergent intelligence capabilities.

Features:
- Swarm intelligence patterns
- Cellular automata
- Emergent goal formation
- Self-organization
- Collective decision making
- Pattern emergence detection
"""

import asyncio
import hashlib
import json
import logging
import math
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class EmergentPattern(Enum):
    """Types of emergent patterns."""
    CLUSTERING = "clustering"
    OSCILLATION = "oscillation"
    HIERARCHY = "hierarchy"
    SYNCHRONIZATION = "synchronization"
    CASCADE = "cascade"
    ATTRACTOR = "attractor"
    BIFURCATION = "bifurcation"


class AgentState(Enum):
    """States for emergent agents."""
    IDLE = "idle"
    EXPLORING = "exploring"
    EXPLOITING = "exploiting"
    COMMUNICATING = "communicating"
    ADAPTING = "adapting"


class InteractionType(Enum):
    """Types of agent interactions."""
    COOPERATION = "cooperation"
    COMPETITION = "competition"
    NEUTRAL = "neutral"
    ATTRACTION = "attraction"
    REPULSION = "repulsion"


@dataclass
class Position:
    """Position in abstract space."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def move_towards(self, target: 'Position', speed: float) -> 'Position':
        """Move towards target position."""
        dist = self.distance_to(target)
        if dist == 0:
            return Position(self.x, self.y, self.z)

        ratio = min(1.0, speed / dist)
        return Position(
            self.x + (target.x - self.x) * ratio,
            self.y + (target.y - self.y) * ratio,
            self.z + (target.z - self.z) * ratio
        )


@dataclass
class EmergentAgent:
    """Agent in emergent system."""
    id: str
    position: Position
    velocity: Position = field(default_factory=Position)
    state: AgentState = AgentState.IDLE
    energy: float = 1.0
    fitness: float = 0.0
    neighbors: List[str] = field(default_factory=list)
    memory: List[Dict[str, Any]] = field(default_factory=list)
    beliefs: Dict[str, float] = field(default_factory=dict)

    def update_velocity(self, acceleration: Position, max_speed: float = 1.0):
        """Update velocity with acceleration."""
        self.velocity.x += acceleration.x
        self.velocity.y += acceleration.y
        self.velocity.z += acceleration.z

        # Limit speed
        speed = math.sqrt(
            self.velocity.x ** 2 +
            self.velocity.y ** 2 +
            self.velocity.z ** 2
        )
        if speed > max_speed:
            factor = max_speed / speed
            self.velocity.x *= factor
            self.velocity.y *= factor
            self.velocity.z *= factor

    def move(self):
        """Move based on velocity."""
        self.position.x += self.velocity.x
        self.position.y += self.velocity.y
        self.position.z += self.velocity.z


@dataclass
class PatternObservation:
    """Observation of emergent pattern."""
    pattern_type: EmergentPattern
    strength: float
    agents_involved: List[str]
    center: Position
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SWARM INTELLIGENCE
# =============================================================================

class SwarmBehavior(ABC):
    """Abstract swarm behavior."""

    @abstractmethod
    def compute_force(
        self,
        agent: EmergentAgent,
        neighbors: List[EmergentAgent]
    ) -> Position:
        """Compute force on agent from neighbors."""
        pass


class SeparationBehavior(SwarmBehavior):
    """Separation - avoid crowding neighbors."""

    def __init__(self, radius: float = 1.0, strength: float = 1.0):
        self.radius = radius
        self.strength = strength

    def compute_force(
        self,
        agent: EmergentAgent,
        neighbors: List[EmergentAgent]
    ) -> Position:
        force = Position()
        count = 0

        for neighbor in neighbors:
            dist = agent.position.distance_to(neighbor.position)
            if 0 < dist < self.radius:
                # Repel
                dx = agent.position.x - neighbor.position.x
                dy = agent.position.y - neighbor.position.y
                dz = agent.position.z - neighbor.position.z

                factor = self.strength * (1 - dist / self.radius) / dist
                force.x += dx * factor
                force.y += dy * factor
                force.z += dz * factor
                count += 1

        if count > 0:
            force.x /= count
            force.y /= count
            force.z /= count

        return force


class AlignmentBehavior(SwarmBehavior):
    """Alignment - steer towards average heading of neighbors."""

    def __init__(self, radius: float = 2.0, strength: float = 1.0):
        self.radius = radius
        self.strength = strength

    def compute_force(
        self,
        agent: EmergentAgent,
        neighbors: List[EmergentAgent]
    ) -> Position:
        avg_velocity = Position()
        count = 0

        for neighbor in neighbors:
            dist = agent.position.distance_to(neighbor.position)
            if dist < self.radius:
                avg_velocity.x += neighbor.velocity.x
                avg_velocity.y += neighbor.velocity.y
                avg_velocity.z += neighbor.velocity.z
                count += 1

        if count > 0:
            avg_velocity.x /= count
            avg_velocity.y /= count
            avg_velocity.z /= count

            # Steer towards average
            return Position(
                (avg_velocity.x - agent.velocity.x) * self.strength,
                (avg_velocity.y - agent.velocity.y) * self.strength,
                (avg_velocity.z - agent.velocity.z) * self.strength
            )

        return Position()


class CohesionBehavior(SwarmBehavior):
    """Cohesion - steer towards average position of neighbors."""

    def __init__(self, radius: float = 3.0, strength: float = 1.0):
        self.radius = radius
        self.strength = strength

    def compute_force(
        self,
        agent: EmergentAgent,
        neighbors: List[EmergentAgent]
    ) -> Position:
        center = Position()
        count = 0

        for neighbor in neighbors:
            dist = agent.position.distance_to(neighbor.position)
            if dist < self.radius:
                center.x += neighbor.position.x
                center.y += neighbor.position.y
                center.z += neighbor.position.z
                count += 1

        if count > 0:
            center.x /= count
            center.y /= count
            center.z /= count

            # Steer towards center
            return Position(
                (center.x - agent.position.x) * self.strength,
                (center.y - agent.position.y) * self.strength,
                (center.z - agent.position.z) * self.strength
            )

        return Position()


class SwarmSimulator:
    """Simulate swarm behaviors."""

    def __init__(
        self,
        behaviors: List[SwarmBehavior] = None,
        max_speed: float = 1.0
    ):
        self.behaviors = behaviors or [
            SeparationBehavior(radius=1.0, strength=1.5),
            AlignmentBehavior(radius=2.5, strength=1.0),
            CohesionBehavior(radius=5.0, strength=0.8)
        ]
        self.max_speed = max_speed
        self.agents: Dict[str, EmergentAgent] = {}

    def add_agent(self, agent: EmergentAgent) -> None:
        """Add agent to swarm."""
        self.agents[agent.id] = agent

    def remove_agent(self, agent_id: str) -> None:
        """Remove agent from swarm."""
        if agent_id in self.agents:
            del self.agents[agent_id]

    def get_neighbors(
        self,
        agent: EmergentAgent,
        radius: float = 10.0
    ) -> List[EmergentAgent]:
        """Get neighbors within radius."""
        neighbors = []
        for other in self.agents.values():
            if other.id != agent.id:
                if agent.position.distance_to(other.position) < radius:
                    neighbors.append(other)
        return neighbors

    def step(self) -> None:
        """Execute one simulation step."""
        # Compute forces for all agents
        forces: Dict[str, Position] = {}

        for agent_id, agent in self.agents.items():
            neighbors = self.get_neighbors(agent)
            total_force = Position()

            for behavior in self.behaviors:
                force = behavior.compute_force(agent, neighbors)
                total_force.x += force.x
                total_force.y += force.y
                total_force.z += force.z

            forces[agent_id] = total_force

        # Apply forces
        for agent_id, force in forces.items():
            agent = self.agents[agent_id]
            agent.update_velocity(force, self.max_speed)
            agent.move()

    def get_swarm_center(self) -> Position:
        """Get center of swarm."""
        if not self.agents:
            return Position()

        center = Position()
        for agent in self.agents.values():
            center.x += agent.position.x
            center.y += agent.position.y
            center.z += agent.position.z

        n = len(self.agents)
        center.x /= n
        center.y /= n
        center.z /= n

        return center

    def get_swarm_spread(self) -> float:
        """Get spread of swarm (avg distance from center)."""
        if not self.agents:
            return 0.0

        center = self.get_swarm_center()
        total_dist = sum(
            agent.position.distance_to(center)
            for agent in self.agents.values()
        )

        return total_dist / len(self.agents)


# =============================================================================
# CELLULAR AUTOMATA
# =============================================================================

class CellularAutomaton:
    """Cellular automaton for emergent patterns."""

    def __init__(
        self,
        width: int = 50,
        height: int = 50,
        rule: Callable = None
    ):
        self.width = width
        self.height = height
        self.rule = rule or self._default_rule
        self.grid = [[0 for _ in range(width)] for _ in range(height)]
        self.generation = 0

    def _default_rule(
        self,
        cell: int,
        neighbors: List[int]
    ) -> int:
        """Default rule (Game of Life)."""
        alive_neighbors = sum(neighbors)

        if cell == 1:
            # Survival
            return 1 if alive_neighbors in [2, 3] else 0
        else:
            # Birth
            return 1 if alive_neighbors == 3 else 0

    def get_neighbors(self, x: int, y: int) -> List[int]:
        """Get Moore neighborhood."""
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx = (x + dx) % self.width
                ny = (y + dy) % self.height
                neighbors.append(self.grid[ny][nx])
        return neighbors

    def step(self) -> None:
        """Execute one generation."""
        new_grid = [[0 for _ in range(self.width)] for _ in range(self.height)]

        for y in range(self.height):
            for x in range(self.width):
                neighbors = self.get_neighbors(x, y)
                new_grid[y][x] = self.rule(self.grid[y][x], neighbors)

        self.grid = new_grid
        self.generation += 1

    def randomize(self, density: float = 0.3) -> None:
        """Randomize grid."""
        for y in range(self.height):
            for x in range(self.width):
                self.grid[y][x] = 1 if random.random() < density else 0

    def set_pattern(self, pattern: List[Tuple[int, int]]) -> None:
        """Set specific pattern."""
        # Clear grid
        self.grid = [[0 for _ in range(self.width)] for _ in range(self.height)]

        for x, y in pattern:
            if 0 <= x < self.width and 0 <= y < self.height:
                self.grid[y][x] = 1

    def get_population(self) -> int:
        """Get number of alive cells."""
        return sum(sum(row) for row in self.grid)

    def get_density(self) -> float:
        """Get population density."""
        return self.get_population() / (self.width * self.height)

    def get_entropy(self) -> float:
        """Get grid entropy."""
        total = self.width * self.height
        alive = self.get_population()
        dead = total - alive

        if alive == 0 or dead == 0:
            return 0.0

        p_alive = alive / total
        p_dead = dead / total

        return -(p_alive * math.log2(p_alive) + p_dead * math.log2(p_dead))


# =============================================================================
# EMERGENT GOAL FORMATION
# =============================================================================

class EmergentGoal:
    """Goal that emerges from agent behaviors."""

    def __init__(
        self,
        id: str,
        description: str,
        threshold: float = 0.5
    ):
        self.id = id
        self.description = description
        self.threshold = threshold
        self.support: Dict[str, float] = {}  # agent_id -> support level
        self.emerged = False
        self.emergence_time: Optional[datetime] = None

    def add_support(self, agent_id: str, level: float) -> None:
        """Add agent support for goal."""
        self.support[agent_id] = level
        self._check_emergence()

    def remove_support(self, agent_id: str) -> None:
        """Remove agent support."""
        if agent_id in self.support:
            del self.support[agent_id]
        self._check_emergence()

    def _check_emergence(self) -> None:
        """Check if goal has emerged."""
        if not self.support:
            self.emerged = False
            return

        avg_support = sum(self.support.values()) / len(self.support)
        participation = len(self.support) / 10  # Assume 10 agents minimum

        # Goal emerges if enough support and participation
        if avg_support >= self.threshold and participation >= 0.3:
            if not self.emerged:
                self.emerged = True
                self.emergence_time = datetime.now()
        else:
            self.emerged = False

    def get_consensus(self) -> float:
        """Get consensus level."""
        if not self.support:
            return 0.0

        values = list(self.support.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)

        # High mean, low variance = high consensus
        return mean * (1 - math.sqrt(variance))


class GoalEmergenceSystem:
    """System for emergent goal formation."""

    def __init__(self):
        self.potential_goals: Dict[str, EmergentGoal] = {}
        self.emerged_goals: List[EmergentGoal] = []
        self.agent_preferences: Dict[str, Dict[str, float]] = defaultdict(dict)

    def propose_goal(
        self,
        description: str,
        proposer_id: str,
        initial_support: float = 0.8
    ) -> str:
        """Propose new potential goal."""
        goal_id = str(uuid4())
        goal = EmergentGoal(
            id=goal_id,
            description=description
        )
        goal.add_support(proposer_id, initial_support)

        self.potential_goals[goal_id] = goal
        self.agent_preferences[proposer_id][goal_id] = initial_support

        return goal_id

    def vote_for_goal(
        self,
        goal_id: str,
        agent_id: str,
        support: float
    ) -> None:
        """Vote for/against goal."""
        if goal_id in self.potential_goals:
            self.potential_goals[goal_id].add_support(agent_id, support)
            self.agent_preferences[agent_id][goal_id] = support

            # Check emergence
            goal = self.potential_goals[goal_id]
            if goal.emerged and goal not in self.emerged_goals:
                self.emerged_goals.append(goal)
                logger.info(f"Goal emerged: {goal.description}")

    def get_active_goals(self) -> List[EmergentGoal]:
        """Get currently emerged goals."""
        return [g for g in self.emerged_goals if g.emerged]

    def propagate_influence(
        self,
        agents: Dict[str, EmergentAgent]
    ) -> None:
        """Propagate goal preferences through social network."""
        for agent_id, agent in agents.items():
            for neighbor_id in agent.neighbors:
                if neighbor_id in self.agent_preferences:
                    neighbor_prefs = self.agent_preferences[neighbor_id]

                    # Influence towards neighbor's preferences
                    for goal_id, support in neighbor_prefs.items():
                        current = self.agent_preferences[agent_id].get(goal_id, 0.5)
                        # Move slightly towards neighbor
                        new_support = current + 0.1 * (support - current)

                        if goal_id in self.potential_goals:
                            self.vote_for_goal(goal_id, agent_id, new_support)


# =============================================================================
# PATTERN EMERGENCE DETECTION
# =============================================================================

class PatternDetector:
    """Detect emergent patterns in system."""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.detected_patterns: List[PatternObservation] = []

    def record_state(self, state: Dict[str, Any]) -> None:
        """Record system state."""
        self.history.append({
            "timestamp": datetime.now(),
            "state": state
        })

        # Keep limited history
        if len(self.history) > 1000:
            self.history = self.history[-500:]

    def detect_clustering(
        self,
        agents: Dict[str, EmergentAgent],
        threshold: float = 2.0
    ) -> List[PatternObservation]:
        """Detect clustering patterns."""
        patterns = []

        # Find clusters using simple distance-based approach
        visited = set()

        for agent_id, agent in agents.items():
            if agent_id in visited:
                continue

            cluster = [agent_id]
            visited.add(agent_id)

            # Find all connected agents
            queue = [agent]
            while queue:
                current = queue.pop(0)

                for other_id, other in agents.items():
                    if other_id not in visited:
                        if current.position.distance_to(other.position) < threshold:
                            cluster.append(other_id)
                            visited.add(other_id)
                            queue.append(other)

            if len(cluster) >= 3:
                # Calculate cluster center
                center = Position()
                for cid in cluster:
                    center.x += agents[cid].position.x
                    center.y += agents[cid].position.y
                    center.z += agents[cid].position.z
                n = len(cluster)
                center.x /= n
                center.y /= n
                center.z /= n

                patterns.append(PatternObservation(
                    pattern_type=EmergentPattern.CLUSTERING,
                    strength=len(cluster) / len(agents),
                    agents_involved=cluster,
                    center=center,
                    metadata={"cluster_size": len(cluster)}
                ))

        return patterns

    def detect_synchronization(
        self,
        agents: Dict[str, EmergentAgent],
        threshold: float = 0.8
    ) -> Optional[PatternObservation]:
        """Detect velocity synchronization."""
        if len(agents) < 2:
            return None

        # Calculate average velocity
        avg_vx = sum(a.velocity.x for a in agents.values()) / len(agents)
        avg_vy = sum(a.velocity.y for a in agents.values()) / len(agents)
        avg_vz = sum(a.velocity.z for a in agents.values()) / len(agents)

        # Calculate alignment with average
        aligned = []
        for agent_id, agent in agents.items():
            dot = (
                agent.velocity.x * avg_vx +
                agent.velocity.y * avg_vy +
                agent.velocity.z * avg_vz
            )

            agent_speed = math.sqrt(
                agent.velocity.x ** 2 +
                agent.velocity.y ** 2 +
                agent.velocity.z ** 2
            )
            avg_speed = math.sqrt(avg_vx ** 2 + avg_vy ** 2 + avg_vz ** 2)

            if agent_speed > 0 and avg_speed > 0:
                alignment = dot / (agent_speed * avg_speed)
                if alignment > threshold:
                    aligned.append(agent_id)

        if len(aligned) > len(agents) * 0.5:
            return PatternObservation(
                pattern_type=EmergentPattern.SYNCHRONIZATION,
                strength=len(aligned) / len(agents),
                agents_involved=aligned,
                center=Position(avg_vx, avg_vy, avg_vz),
                metadata={"alignment_threshold": threshold}
            )

        return None

    def detect_oscillation(
        self,
        metric_history: List[float],
        min_period: int = 5
    ) -> Optional[PatternObservation]:
        """Detect oscillation in metric history."""
        if len(metric_history) < min_period * 3:
            return None

        # Simple peak detection
        peaks = []
        for i in range(1, len(metric_history) - 1):
            if (metric_history[i] > metric_history[i-1] and
                metric_history[i] > metric_history[i+1]):
                peaks.append(i)

        if len(peaks) >= 2:
            # Calculate average period
            periods = [peaks[i+1] - peaks[i] for i in range(len(peaks)-1)]
            avg_period = sum(periods) / len(periods)

            # Calculate regularity
            variance = sum((p - avg_period) ** 2 for p in periods) / len(periods)
            regularity = 1 / (1 + variance)

            if regularity > 0.5:
                return PatternObservation(
                    pattern_type=EmergentPattern.OSCILLATION,
                    strength=regularity,
                    agents_involved=[],
                    center=Position(),
                    metadata={
                        "period": avg_period,
                        "num_peaks": len(peaks)
                    }
                )

        return None

    def detect_all(
        self,
        agents: Dict[str, EmergentAgent],
        metric_history: List[float] = None
    ) -> List[PatternObservation]:
        """Detect all patterns."""
        patterns = []

        # Clustering
        patterns.extend(self.detect_clustering(agents))

        # Synchronization
        sync = self.detect_synchronization(agents)
        if sync:
            patterns.append(sync)

        # Oscillation
        if metric_history:
            osc = self.detect_oscillation(metric_history)
            if osc:
                patterns.append(osc)

        self.detected_patterns.extend(patterns)

        return patterns


# =============================================================================
# COLLECTIVE DECISION MAKING
# =============================================================================

class CollectiveDecision:
    """Collective decision-making mechanism."""

    def __init__(self, options: List[str]):
        self.options = options
        self.votes: Dict[str, Dict[str, float]] = defaultdict(dict)  # agent -> option -> weight
        self.commitment: Dict[str, float] = {opt: 0.0 for opt in options}

    def cast_vote(
        self,
        agent_id: str,
        preferences: Dict[str, float]
    ) -> None:
        """Cast weighted vote."""
        # Normalize preferences
        total = sum(preferences.values())
        if total > 0:
            self.votes[agent_id] = {
                opt: w / total for opt, w in preferences.items()
            }
        else:
            self.votes[agent_id] = preferences

    def get_results(self) -> Dict[str, float]:
        """Get voting results."""
        results = {opt: 0.0 for opt in self.options}

        for agent_votes in self.votes.values():
            for option, weight in agent_votes.items():
                if option in results:
                    results[option] += weight

        # Normalize
        total = sum(results.values())
        if total > 0:
            results = {opt: w / total for opt, w in results.items()}

        return results

    def get_winner(self, method: str = "plurality") -> Optional[str]:
        """Get winning option."""
        results = self.get_results()

        if method == "plurality":
            return max(results.items(), key=lambda x: x[1])[0] if results else None
        elif method == "threshold":
            # Need > 50% support
            for opt, weight in results.items():
                if weight > 0.5:
                    return opt
            return None
        elif method == "quorum":
            # Need enough participation
            participation = len(self.votes) / 10  # Assume 10 agents minimum
            if participation < 0.5:
                return None
            return max(results.items(), key=lambda x: x[1])[0]

        return None

    def propagate_opinions(
        self,
        agents: Dict[str, EmergentAgent],
        influence_rate: float = 0.1
    ) -> None:
        """Propagate opinions through network."""
        new_votes = {}

        for agent_id, agent in agents.items():
            if agent_id not in self.votes:
                continue

            current_prefs = dict(self.votes[agent_id])

            # Average with neighbors
            for neighbor_id in agent.neighbors:
                if neighbor_id in self.votes:
                    neighbor_prefs = self.votes[neighbor_id]
                    for opt in self.options:
                        current = current_prefs.get(opt, 0.0)
                        neighbor = neighbor_prefs.get(opt, 0.0)
                        current_prefs[opt] = current + influence_rate * (neighbor - current)

            new_votes[agent_id] = current_prefs

        # Update votes
        for agent_id, prefs in new_votes.items():
            self.cast_vote(agent_id, prefs)


# =============================================================================
# EMERGENT BEHAVIOR SYSTEM
# =============================================================================

class EmergentBehaviorSystem:
    """Main emergent behavior orchestrator."""

    def __init__(
        self,
        num_agents: int = 50,
        world_size: float = 100.0
    ):
        self.num_agents = num_agents
        self.world_size = world_size

        # Components
        self.swarm = SwarmSimulator()
        self.automaton = CellularAutomaton(50, 50)
        self.goal_system = GoalEmergenceSystem()
        self.pattern_detector = PatternDetector()

        # State
        self.agents: Dict[str, EmergentAgent] = {}
        self.metric_history: List[float] = []
        self.step_count = 0

        # Initialize
        self._init_agents()

    def _init_agents(self) -> None:
        """Initialize agent population."""
        for i in range(self.num_agents):
            agent = EmergentAgent(
                id=f"agent_{i}",
                position=Position(
                    random.uniform(0, self.world_size),
                    random.uniform(0, self.world_size),
                    random.uniform(0, self.world_size)
                ),
                velocity=Position(
                    random.uniform(-1, 1),
                    random.uniform(-1, 1),
                    random.uniform(-1, 1)
                )
            )

            self.agents[agent.id] = agent
            self.swarm.add_agent(agent)

        # Setup neighbor relationships
        self._update_neighbors()

    def _update_neighbors(self, radius: float = 10.0) -> None:
        """Update neighbor relationships."""
        for agent_id, agent in self.agents.items():
            neighbors = []
            for other_id, other in self.agents.items():
                if other_id != agent_id:
                    if agent.position.distance_to(other.position) < radius:
                        neighbors.append(other_id)
            agent.neighbors = neighbors[:10]  # Limit neighbors

    async def step(self) -> Dict[str, Any]:
        """Execute one simulation step."""
        self.step_count += 1

        # 1. Update swarm
        self.swarm.step()

        # 2. Update cellular automaton
        self.automaton.step()

        # 3. Update neighbor relationships
        self._update_neighbors()

        # 4. Propagate goal preferences
        self.goal_system.propagate_influence(self.agents)

        # 5. Record metrics
        spread = self.swarm.get_swarm_spread()
        self.metric_history.append(spread)

        # 6. Detect patterns
        patterns = self.pattern_detector.detect_all(
            self.agents,
            self.metric_history
        )

        return {
            "step": self.step_count,
            "swarm_spread": spread,
            "automaton_density": self.automaton.get_density(),
            "emerged_goals": len(self.goal_system.get_active_goals()),
            "patterns_detected": len(patterns),
            "patterns": [
                {
                    "type": p.pattern_type.value,
                    "strength": p.strength,
                    "agents": len(p.agents_involved)
                }
                for p in patterns
            ]
        }

    async def run(
        self,
        steps: int = 100,
        callback: Callable = None
    ) -> Dict[str, Any]:
        """Run simulation for multiple steps."""
        results = []

        for i in range(steps):
            result = await self.step()
            results.append(result)

            if callback:
                await callback(i, result)

        return {
            "total_steps": steps,
            "final_spread": self.swarm.get_swarm_spread(),
            "final_density": self.automaton.get_density(),
            "total_patterns": len(self.pattern_detector.detected_patterns),
            "emerged_goals": [
                g.description for g in self.goal_system.get_active_goals()
            ]
        }

    def propose_goal(self, description: str, proposer_id: str) -> str:
        """Propose a goal for collective consideration."""
        return self.goal_system.propose_goal(description, proposer_id)

    def vote_for_goal(
        self,
        goal_id: str,
        agent_id: str,
        support: float
    ) -> None:
        """Vote for a goal."""
        self.goal_system.vote_for_goal(goal_id, agent_id, support)

    def get_patterns(self) -> List[PatternObservation]:
        """Get detected patterns."""
        return self.pattern_detector.detected_patterns

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "agents": len(self.agents),
            "step": self.step_count,
            "swarm_center": {
                "x": self.swarm.get_swarm_center().x,
                "y": self.swarm.get_swarm_center().y,
                "z": self.swarm.get_swarm_center().z
            },
            "swarm_spread": self.swarm.get_swarm_spread(),
            "automaton": {
                "generation": self.automaton.generation,
                "population": self.automaton.get_population(),
                "entropy": self.automaton.get_entropy()
            },
            "goals": {
                "potential": len(self.goal_system.potential_goals),
                "emerged": len(self.goal_system.emerged_goals)
            },
            "patterns": {
                "total_detected": len(self.pattern_detector.detected_patterns),
                "types": list(set(
                    p.pattern_type.value
                    for p in self.pattern_detector.detected_patterns
                ))
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo emergent behavior system."""
    print("=== Emergent Behavior System Demo ===\n")

    # Create system
    system = EmergentBehaviorSystem(num_agents=30, world_size=50.0)

    # 1. Initial state
    print("1. Initial State:")
    status = system.get_status()
    print(f"   Agents: {status['agents']}")
    print(f"   Swarm spread: {status['swarm_spread']:.2f}")
    print(f"   Automaton population: {status['automaton']['population']}")

    # 2. Propose some goals
    print("\n2. Proposing Goals:")
    goal1 = system.propose_goal("Explore the environment", "agent_0")
    goal2 = system.propose_goal("Find resources", "agent_5")
    goal3 = system.propose_goal("Form defensive clusters", "agent_10")

    print(f"   Proposed: 'Explore the environment'")
    print(f"   Proposed: 'Find resources'")
    print(f"   Proposed: 'Form defensive clusters'")

    # 3. Agents vote for goals
    print("\n3. Voting for Goals:")
    for i in range(20):
        agent_id = f"agent_{i}"
        # Random voting preferences
        system.vote_for_goal(goal1, agent_id, random.uniform(0.3, 0.9))
        system.vote_for_goal(goal2, agent_id, random.uniform(0.2, 0.8))
        system.vote_for_goal(goal3, agent_id, random.uniform(0.4, 1.0))

    emerged = system.goal_system.get_active_goals()
    print(f"   Emerged goals: {len(emerged)}")
    for g in emerged:
        print(f"     - {g.description} (consensus: {g.get_consensus():.2%})")

    # 4. Run simulation
    print("\n4. Running Simulation (50 steps):")

    step_reports = []
    async def report_callback(step, result):
        if step % 10 == 0:
            step_reports.append(result)

    results = await system.run(steps=50, callback=report_callback)

    for report in step_reports:
        print(f"   Step {report['step']}: spread={report['swarm_spread']:.2f}, "
              f"patterns={report['patterns_detected']}")

    # 5. Pattern analysis
    print("\n5. Detected Patterns:")
    patterns = system.get_patterns()

    pattern_counts = defaultdict(int)
    for p in patterns:
        pattern_counts[p.pattern_type.value] += 1

    for ptype, count in pattern_counts.items():
        print(f"   {ptype}: {count} occurrences")

    # 6. Final state
    print("\n6. Final State:")
    status = system.get_status()
    print(f"   Total steps: {status['step']}")
    print(f"   Swarm spread: {status['swarm_spread']:.2f}")
    print(f"   Automaton entropy: {status['automaton']['entropy']:.4f}")
    print(f"   Emerged goals: {status['goals']['emerged']}")

    # 7. Cellular automaton demo
    print("\n7. Cellular Automaton Patterns:")

    # Set glider pattern
    glider = [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]
    system.automaton.set_pattern(glider)
    print(f"   Set glider pattern")
    print(f"   Initial population: {system.automaton.get_population()}")

    for i in range(20):
        system.automaton.step()

    print(f"   After 20 generations: {system.automaton.get_population()}")

    # 8. Collective decision
    print("\n8. Collective Decision Making:")

    decision = CollectiveDecision(["option_A", "option_B", "option_C"])

    for i in range(15):
        agent_id = f"agent_{i}"
        prefs = {
            "option_A": random.uniform(0, 1),
            "option_B": random.uniform(0, 1),
            "option_C": random.uniform(0, 1)
        }
        decision.cast_vote(agent_id, prefs)

    results = decision.get_results()
    print(f"   Results: {', '.join(f'{k}={v:.2%}' for k, v in results.items())}")
    print(f"   Winner (plurality): {decision.get_winner('plurality')}")

    # Propagate opinions
    decision.propagate_opinions(system.agents, influence_rate=0.2)
    results_after = decision.get_results()
    print(f"   After propagation: {', '.join(f'{k}={v:.2%}' for k, v in results_after.items())}")


if __name__ == "__main__":
    asyncio.run(demo())
