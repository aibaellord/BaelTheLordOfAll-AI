"""
BAEL ACT-R Architecture Engine
===============================

Adaptive Control of Thought - Rational.
Cognitive architecture for unified theory of cognition.

"Ba'el thinks with ACT-R." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict
import heapq
import copy

logger = logging.getLogger("BAEL.ACTR")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ModuleType(Enum):
    """ACT-R modules."""
    GOAL = auto()
    DECLARATIVE = auto()
    PROCEDURAL = auto()
    VISUAL = auto()
    MOTOR = auto()
    IMAGINAL = auto()


class BufferState(Enum):
    """Buffer states."""
    EMPTY = auto()
    BUSY = auto()
    FULL = auto()
    ERROR = auto()


class ChunkType(Enum):
    """Types of chunks."""
    FACT = auto()
    GOAL = auto()
    IMAGINAL = auto()
    VISUAL = auto()
    MOTOR = auto()


@dataclass
class Chunk:
    """
    A chunk in declarative memory.
    """
    id: str
    chunk_type: ChunkType
    slots: Dict[str, Any]
    base_level: float = 0.0
    creation_time: float = field(default_factory=time.time)
    access_times: List[float] = field(default_factory=list)

    def access(self) -> None:
        """Record chunk access."""
        self.access_times.append(time.time())

    @property
    def activation(self) -> float:
        """Calculate chunk activation."""
        # Base-level learning equation
        if not self.access_times:
            return self.base_level

        now = time.time()
        activation = 0.0
        d = 0.5  # Decay parameter

        for t in self.access_times:
            age = max(now - t, 0.001)
            activation += age ** (-d)

        return math.log(activation) if activation > 0 else self.base_level


@dataclass
class Production:
    """
    A production rule.
    """
    id: str
    name: str
    conditions: Dict[str, Dict[str, Any]]  # Buffer -> slot conditions
    actions: Dict[str, Dict[str, Any]]     # Buffer -> slot actions
    utility: float = 0.0
    cost: float = 0.05  # Default 50ms

    def matches(self, buffers: Dict[str, Optional['Chunk']]) -> bool:
        """Check if production matches current state."""
        for buffer_name, slot_conditions in self.conditions.items():
            buffer_chunk = buffers.get(buffer_name)

            if slot_conditions is None:
                # Condition requires empty buffer
                if buffer_chunk is not None:
                    return False
                continue

            if buffer_chunk is None:
                return False

            for slot, expected in slot_conditions.items():
                actual = buffer_chunk.slots.get(slot)
                if actual != expected:
                    return False

        return True


@dataclass
class Buffer:
    """
    A module buffer.
    """
    name: str
    chunk: Optional[Chunk] = None
    state: BufferState = BufferState.EMPTY

    def clear(self) -> None:
        """Clear buffer."""
        self.chunk = None
        self.state = BufferState.EMPTY

    def set(self, chunk: Chunk) -> None:
        """Set buffer contents."""
        self.chunk = chunk
        self.state = BufferState.FULL


# ============================================================================
# DECLARATIVE MEMORY
# ============================================================================

class DeclarativeMemory:
    """
    ACT-R Declarative Memory.

    "Ba'el's declarative memory." — Ba'el
    """

    def __init__(self):
        """Initialize memory."""
        self._chunks: Dict[str, Chunk] = {}
        self._chunk_counter = 0
        self._retrieval_threshold: float = -float('inf')
        self._latency_factor: float = 1.0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._chunk_counter += 1
        return f"chunk_{self._chunk_counter}"

    def add_chunk(
        self,
        chunk_type: ChunkType,
        slots: Dict[str, Any],
        base_level: float = 0.0
    ) -> Chunk:
        """Add chunk to memory."""
        with self._lock:
            chunk = Chunk(
                id=self._generate_id(),
                chunk_type=chunk_type,
                slots=slots,
                base_level=base_level
            )
            self._chunks[chunk.id] = chunk
            return chunk

    def retrieve(
        self,
        query: Dict[str, Any],
        chunk_type: Optional[ChunkType] = None
    ) -> Optional[Chunk]:
        """Retrieve chunk matching query."""
        with self._lock:
            candidates = []

            for chunk in self._chunks.values():
                if chunk_type and chunk.chunk_type != chunk_type:
                    continue

                # Check slot matches
                matches = True
                for slot, value in query.items():
                    if chunk.slots.get(slot) != value:
                        matches = False
                        break

                if matches:
                    activation = chunk.activation
                    if activation >= self._retrieval_threshold:
                        candidates.append((activation, chunk))

            if not candidates:
                return None

            # Return highest activation
            candidates.sort(key=lambda x: x[0], reverse=True)
            best = candidates[0][1]
            best.access()

            return best

    def get_retrieval_time(self, chunk: Chunk) -> float:
        """Calculate retrieval time."""
        activation = chunk.activation
        return self._latency_factor * math.exp(-activation)

    def set_threshold(self, threshold: float) -> None:
        """Set retrieval threshold."""
        self._retrieval_threshold = threshold

    @property
    def chunks(self) -> List[Chunk]:
        return list(self._chunks.values())


# ============================================================================
# PROCEDURAL MEMORY
# ============================================================================

class ProceduralMemory:
    """
    ACT-R Procedural Memory.

    "Ba'el's production rules." — Ba'el
    """

    def __init__(self):
        """Initialize procedural memory."""
        self._productions: Dict[str, Production] = {}
        self._production_counter = 0
        self._utility_noise: float = 0.0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._production_counter += 1
        return f"prod_{self._production_counter}"

    def add_production(
        self,
        name: str,
        conditions: Dict[str, Dict[str, Any]],
        actions: Dict[str, Dict[str, Any]],
        utility: float = 0.0
    ) -> Production:
        """Add production rule."""
        with self._lock:
            production = Production(
                id=self._generate_id(),
                name=name,
                conditions=conditions,
                actions=actions,
                utility=utility
            )
            self._productions[production.id] = production
            return production

    def conflict_resolution(
        self,
        buffers: Dict[str, Optional[Chunk]]
    ) -> Optional[Production]:
        """Select production to fire."""
        with self._lock:
            matching = []

            for production in self._productions.values():
                if production.matches(buffers):
                    # Add noise to utility
                    noisy_utility = production.utility
                    if self._utility_noise > 0:
                        noisy_utility += random.gauss(0, self._utility_noise)

                    matching.append((noisy_utility, production))

            if not matching:
                return None

            # Return highest utility
            matching.sort(key=lambda x: x[0], reverse=True)
            return matching[0][1]

    def update_utility(
        self,
        production_id: str,
        reward: float,
        learning_rate: float = 0.1
    ) -> None:
        """Update production utility."""
        with self._lock:
            if production_id in self._productions:
                prod = self._productions[production_id]
                prod.utility += learning_rate * (reward - prod.utility)

    def set_noise(self, noise: float) -> None:
        """Set utility noise."""
        self._utility_noise = noise

    @property
    def productions(self) -> List[Production]:
        return list(self._productions.values())


# ============================================================================
# GOAL MODULE
# ============================================================================

class GoalModule:
    """
    ACT-R Goal Module.

    "Ba'el's goals." — Ba'el
    """

    def __init__(self):
        """Initialize goal module."""
        self._buffer = Buffer("goal")
        self._goal_stack: List[Chunk] = []
        self._lock = threading.RLock()

    def set_goal(self, goal_chunk: Chunk) -> None:
        """Set current goal."""
        with self._lock:
            self._buffer.set(goal_chunk)

    def push_goal(self, goal_chunk: Chunk) -> None:
        """Push goal onto stack."""
        with self._lock:
            if self._buffer.chunk:
                self._goal_stack.append(self._buffer.chunk)
            self._buffer.set(goal_chunk)

    def pop_goal(self) -> Optional[Chunk]:
        """Pop goal from stack."""
        with self._lock:
            popped = self._buffer.chunk

            if self._goal_stack:
                self._buffer.set(self._goal_stack.pop())
            else:
                self._buffer.clear()

            return popped

    def modify(self, slot_updates: Dict[str, Any]) -> None:
        """Modify current goal."""
        with self._lock:
            if self._buffer.chunk:
                self._buffer.chunk.slots.update(slot_updates)

    @property
    def buffer(self) -> Buffer:
        return self._buffer

    @property
    def current_goal(self) -> Optional[Chunk]:
        return self._buffer.chunk


# ============================================================================
# IMAGINAL MODULE
# ============================================================================

class ImaginalModule:
    """
    ACT-R Imaginal Module.

    "Ba'el's problem representation." — Ba'el
    """

    def __init__(self):
        """Initialize imaginal module."""
        self._buffer = Buffer("imaginal")
        self._creation_time: float = 0.2  # 200ms
        self._modification_time: float = 0.2
        self._lock = threading.RLock()

    def create(self, chunk: Chunk) -> None:
        """Create imaginal representation."""
        with self._lock:
            self._buffer.state = BufferState.BUSY
            time.sleep(self._creation_time * 0.01)  # Simulated
            self._buffer.set(chunk)

    def modify(self, slot_updates: Dict[str, Any]) -> None:
        """Modify imaginal representation."""
        with self._lock:
            if self._buffer.chunk:
                self._buffer.state = BufferState.BUSY
                time.sleep(self._modification_time * 0.01)
                self._buffer.chunk.slots.update(slot_updates)
                self._buffer.state = BufferState.FULL

    def clear(self) -> Optional[Chunk]:
        """Clear and return imaginal contents."""
        with self._lock:
            chunk = self._buffer.chunk
            self._buffer.clear()
            return chunk

    @property
    def buffer(self) -> Buffer:
        return self._buffer


# ============================================================================
# ACT-R ENGINE
# ============================================================================

class ACTREngine:
    """
    Complete ACT-R cognitive architecture.

    "Ba'el runs on ACT-R." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._declarative = DeclarativeMemory()
        self._procedural = ProceduralMemory()
        self._goal = GoalModule()
        self._imaginal = ImaginalModule()

        self._buffers: Dict[str, Buffer] = {
            'goal': self._goal.buffer,
            'imaginal': self._imaginal.buffer,
            'retrieval': Buffer('retrieval')
        }

        self._current_time: float = 0.0
        self._cycle_time: float = 0.05  # 50ms
        self._firing_history: List[Tuple[float, str]] = []
        self._lock = threading.RLock()

    # Memory operations

    def add_fact(self, slots: Dict[str, Any]) -> Chunk:
        """Add fact to declarative memory."""
        return self._declarative.add_chunk(ChunkType.FACT, slots)

    def add_goal(self, slots: Dict[str, Any]) -> Chunk:
        """Create goal chunk."""
        return Chunk(
            id=f"goal_{time.time()}",
            chunk_type=ChunkType.GOAL,
            slots=slots
        )

    def retrieve(self, query: Dict[str, Any]) -> Optional[Chunk]:
        """Retrieve from declarative memory."""
        with self._lock:
            chunk = self._declarative.retrieve(query)
            if chunk:
                self._buffers['retrieval'].set(chunk)
            else:
                self._buffers['retrieval'].state = BufferState.ERROR
            return chunk

    # Production operations

    def add_production(
        self,
        name: str,
        conditions: Dict[str, Dict[str, Any]],
        actions: Dict[str, Dict[str, Any]],
        utility: float = 0.0
    ) -> Production:
        """Add production rule."""
        return self._procedural.add_production(name, conditions, actions, utility)

    # Goal operations

    def set_goal(self, slots: Dict[str, Any]) -> None:
        """Set current goal."""
        chunk = self.add_goal(slots)
        self._goal.set_goal(chunk)

    def push_goal(self, slots: Dict[str, Any]) -> None:
        """Push new goal."""
        chunk = self.add_goal(slots)
        self._goal.push_goal(chunk)

    def pop_goal(self) -> Optional[Chunk]:
        """Pop current goal."""
        return self._goal.pop_goal()

    # Cycle execution

    def step(self) -> Optional[Production]:
        """Execute one cognitive cycle."""
        with self._lock:
            # Get buffer contents
            buffer_chunks = {
                name: buffer.chunk
                for name, buffer in self._buffers.items()
            }

            # Conflict resolution
            production = self._procedural.conflict_resolution(buffer_chunks)

            if production:
                # Fire production
                self._fire_production(production)
                self._firing_history.append((self._current_time, production.id))

            # Advance time
            self._current_time += self._cycle_time

            return production

    def _fire_production(self, production: Production) -> None:
        """Fire a production."""
        for buffer_name, actions in production.actions.items():
            if actions is None:
                # Clear buffer
                if buffer_name in self._buffers:
                    self._buffers[buffer_name].clear()
            elif buffer_name == 'goal':
                # Modify goal
                self._goal.modify(actions)
            elif buffer_name == 'imaginal':
                # Modify imaginal
                self._imaginal.modify(actions)
            elif buffer_name == '+retrieval':
                # Request retrieval
                query = actions
                self.retrieve(query)

    def run(
        self,
        max_cycles: int = 100,
        until_goal_clear: bool = True
    ) -> List[Production]:
        """Run until completion."""
        productions_fired = []

        for _ in range(max_cycles):
            if until_goal_clear and self._goal.current_goal is None:
                break

            production = self.step()
            if production:
                productions_fired.append(production)
            else:
                # No production matched
                break

        return productions_fired

    def reward(
        self,
        production_id: str,
        reward: float
    ) -> None:
        """Reward production (utility learning)."""
        self._procedural.update_utility(production_id, reward)

    @property
    def declarative(self) -> DeclarativeMemory:
        return self._declarative

    @property
    def procedural(self) -> ProceduralMemory:
        return self._procedural

    @property
    def goal(self) -> GoalModule:
        return self._goal

    @property
    def imaginal(self) -> ImaginalModule:
        return self._imaginal

    @property
    def current_time(self) -> float:
        return self._current_time

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'time': self._current_time,
            'chunks': len(self._declarative.chunks),
            'productions': len(self._procedural.productions),
            'current_goal': self._goal.current_goal.slots if self._goal.current_goal else None,
            'firings': len(self._firing_history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_actr_engine() -> ACTREngine:
    """Create ACT-R engine."""
    return ACTREngine()


def create_chunk(
    chunk_type: ChunkType,
    slots: Dict[str, Any]
) -> Chunk:
    """Create a chunk."""
    return Chunk(
        id=f"chunk_{random.randint(1000, 9999)}",
        chunk_type=chunk_type,
        slots=slots
    )


def create_production(
    name: str,
    conditions: Dict[str, Dict[str, Any]],
    actions: Dict[str, Dict[str, Any]]
) -> Production:
    """Create a production."""
    return Production(
        id=f"prod_{random.randint(1000, 9999)}",
        name=name,
        conditions=conditions,
        actions=actions
    )
