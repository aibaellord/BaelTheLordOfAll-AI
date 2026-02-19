"""
BAEL Production System Engine
==============================

Cognitive architecture production rules.
Newell & Simon production systems.

"Ba'el executes cognitive rules." — Ba'el
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
from collections import defaultdict, deque
import copy
import re

logger = logging.getLogger("BAEL.ProductionSystem")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProductionState(Enum):
    """States of production."""
    INACTIVE = auto()      # Not matched
    MATCHED = auto()       # Condition matched
    SELECTED = auto()      # Selected for firing
    FIRING = auto()        # Currently executing
    FIRED = auto()         # Completed


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    FIRST_MATCH = auto()      # First matching production
    SPECIFICITY = auto()      # Most specific condition
    RECENCY = auto()          # Most recently added
    PRIORITY = auto()         # Explicit priority
    REFRACTORINESS = auto()   # Avoid re-firing same


class BufferType(Enum):
    """Types of buffers."""
    GOAL = auto()          # Current goal
    RETRIEVAL = auto()     # Retrieved from memory
    VISUAL = auto()        # Visual input
    MANUAL = auto()        # Motor output
    IMAGINAL = auto()      # Problem state


@dataclass
class Condition:
    """
    A condition in a production rule.
    """
    buffer: BufferType
    attribute: str
    operator: str  # =, !=, >, <, contains
    value: Any
    variable: Optional[str] = None  # For binding


@dataclass
class Action:
    """
    An action in a production rule.
    """
    buffer: BufferType
    operation: str  # modify, clear, request
    attribute: str
    value: Any


@dataclass
class Production:
    """
    A production rule.
    """
    id: str
    name: str
    conditions: List[Condition]
    actions: List[Action]
    priority: float = 0.5
    utility: float = 1.0
    firings: int = 0
    last_fired: float = 0.0


@dataclass
class Chunk:
    """
    A chunk in declarative memory.
    """
    id: str
    chunk_type: str
    slots: Dict[str, Any]
    activation: float = 0.0
    creation_time: float = 0.0


@dataclass
class BufferState:
    """
    State of a buffer.
    """
    buffer_type: BufferType
    chunk: Optional[Chunk] = None
    is_busy: bool = False
    last_modified: float = 0.0


@dataclass
class CycleResult:
    """
    Result of a production cycle.
    """
    cycle: int
    matched_productions: List[str]
    selected_production: Optional[str]
    fired: bool
    bindings: Dict[str, Any]
    actions_taken: List[str]


@dataclass
class SystemMetrics:
    """
    Production system metrics.
    """
    total_cycles: int
    total_firings: int
    productions_count: int
    average_match_time: float


# ============================================================================
# BUFFER SYSTEM
# ============================================================================

class BufferSystem:
    """
    Manage buffers in the production system.

    "Ba'el's working memory buffers." — Ba'el
    """

    def __init__(self):
        """Initialize buffer system."""
        self._buffers: Dict[BufferType, BufferState] = {
            bt: BufferState(buffer_type=bt) for bt in BufferType
        }

        self._lock = threading.RLock()

    def get_buffer(
        self,
        buffer_type: BufferType
    ) -> BufferState:
        """Get buffer state."""
        return self._buffers[buffer_type]

    def set_chunk(
        self,
        buffer_type: BufferType,
        chunk: Chunk
    ) -> None:
        """Set chunk in buffer."""
        with self._lock:
            self._buffers[buffer_type].chunk = chunk
            self._buffers[buffer_type].last_modified = time.time()

    def clear_buffer(
        self,
        buffer_type: BufferType
    ) -> None:
        """Clear a buffer."""
        with self._lock:
            self._buffers[buffer_type].chunk = None
            self._buffers[buffer_type].last_modified = time.time()

    def modify_chunk(
        self,
        buffer_type: BufferType,
        attribute: str,
        value: Any
    ) -> bool:
        """Modify chunk in buffer."""
        with self._lock:
            buffer = self._buffers[buffer_type]
            if buffer.chunk:
                buffer.chunk.slots[attribute] = value
                buffer.last_modified = time.time()
                return True
            return False

    def get_all_chunks(self) -> Dict[BufferType, Optional[Chunk]]:
        """Get all buffer chunks."""
        return {bt: bs.chunk for bt, bs in self._buffers.items()}


# ============================================================================
# PATTERN MATCHER
# ============================================================================

class PatternMatcher:
    """
    Match production conditions against buffers.

    "Ba'el matches patterns." — Ba'el
    """

    def __init__(self):
        """Initialize matcher."""
        self._lock = threading.RLock()

    def match(
        self,
        production: Production,
        buffers: BufferSystem
    ) -> Tuple[bool, Dict[str, Any]]:
        """Match production conditions against buffer contents."""
        bindings: Dict[str, Any] = {}

        for condition in production.conditions:
            buffer = buffers.get_buffer(condition.buffer)

            if buffer.chunk is None:
                return False, {}

            # Get value from chunk
            if condition.attribute not in buffer.chunk.slots:
                return False, {}

            actual_value = buffer.chunk.slots[condition.attribute]

            # Handle variable binding
            if condition.variable:
                if condition.variable in bindings:
                    if bindings[condition.variable] != actual_value:
                        return False, {}
                else:
                    bindings[condition.variable] = actual_value
                continue

            # Evaluate condition
            if not self._evaluate_condition(
                condition.operator,
                actual_value,
                condition.value
            ):
                return False, {}

        return True, bindings

    def _evaluate_condition(
        self,
        operator: str,
        actual: Any,
        expected: Any
    ) -> bool:
        """Evaluate a condition."""
        if operator == "=":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == ">":
            return actual > expected
        elif operator == "<":
            return actual < expected
        elif operator == ">=":
            return actual >= expected
        elif operator == "<=":
            return actual <= expected
        elif operator == "contains":
            return expected in str(actual)
        return False


# ============================================================================
# CONFLICT RESOLVER
# ============================================================================

class ConflictResolver:
    """
    Resolve conflicts between matched productions.

    "Ba'el chooses the best rule." — Ba'el
    """

    def __init__(
        self,
        strategy: ConflictResolution = ConflictResolution.PRIORITY
    ):
        """Initialize resolver."""
        self._strategy = strategy
        self._recently_fired: Set[str] = set()

        self._lock = threading.RLock()

    def resolve(
        self,
        matched: List[Production]
    ) -> Optional[Production]:
        """Resolve conflict among matched productions."""
        if not matched:
            return None

        if len(matched) == 1:
            return matched[0]

        if self._strategy == ConflictResolution.FIRST_MATCH:
            return matched[0]

        elif self._strategy == ConflictResolution.SPECIFICITY:
            # More conditions = more specific
            return max(matched, key=lambda p: len(p.conditions))

        elif self._strategy == ConflictResolution.RECENCY:
            # Most recently fired
            return max(matched, key=lambda p: p.last_fired)

        elif self._strategy == ConflictResolution.PRIORITY:
            # Highest priority
            return max(matched, key=lambda p: p.priority)

        elif self._strategy == ConflictResolution.REFRACTORINESS:
            # Avoid recently fired
            candidates = [p for p in matched if p.id not in self._recently_fired]
            if candidates:
                return max(candidates, key=lambda p: p.utility)
            return matched[0]

        return matched[0]

    def mark_fired(
        self,
        production_id: str
    ) -> None:
        """Mark production as recently fired."""
        self._recently_fired.add(production_id)

    def clear_refractory(self) -> None:
        """Clear refractory set."""
        self._recently_fired.clear()


# ============================================================================
# ACTION EXECUTOR
# ============================================================================

class ActionExecutor:
    """
    Execute production actions.

    "Ba'el takes action." — Ba'el
    """

    def __init__(
        self,
        buffers: BufferSystem
    ):
        """Initialize executor."""
        self._buffers = buffers
        self._chunk_counter = 0

        self._lock = threading.RLock()

    def _generate_chunk_id(self) -> str:
        self._chunk_counter += 1
        return f"chunk_{self._chunk_counter}"

    def execute(
        self,
        actions: List[Action],
        bindings: Dict[str, Any]
    ) -> List[str]:
        """Execute a list of actions."""
        results = []

        for action in actions:
            result = self._execute_action(action, bindings)
            results.append(result)

        return results

    def _execute_action(
        self,
        action: Action,
        bindings: Dict[str, Any]
    ) -> str:
        """Execute a single action."""
        # Resolve any variable references
        value = action.value
        if isinstance(value, str) and value.startswith("="):
            var_name = value[1:]
            if var_name in bindings:
                value = bindings[var_name]

        if action.operation == "modify":
            success = self._buffers.modify_chunk(
                action.buffer,
                action.attribute,
                value
            )
            return f"Modified {action.buffer.name}.{action.attribute} = {value}"

        elif action.operation == "clear":
            self._buffers.clear_buffer(action.buffer)
            return f"Cleared {action.buffer.name}"

        elif action.operation == "request":
            # Create new chunk
            chunk = Chunk(
                id=self._generate_chunk_id(),
                chunk_type=action.attribute,
                slots={action.attribute: value},
                creation_time=time.time()
            )
            self._buffers.set_chunk(action.buffer, chunk)
            return f"Requested {action.buffer.name}.{action.attribute} = {value}"

        return f"Unknown operation: {action.operation}"


# ============================================================================
# PRODUCTION SYSTEM ENGINE
# ============================================================================

class ProductionSystemEngine:
    """
    Complete production system engine.

    "Ba'el's cognitive architecture." — Ba'el
    """

    def __init__(
        self,
        conflict_strategy: ConflictResolution = ConflictResolution.PRIORITY
    ):
        """Initialize engine."""
        self._buffers = BufferSystem()
        self._matcher = PatternMatcher()
        self._resolver = ConflictResolver(conflict_strategy)
        self._executor = ActionExecutor(self._buffers)

        self._productions: Dict[str, Production] = {}
        self._cycle_count = 0
        self._total_firings = 0

        self._history: List[CycleResult] = []

        self._production_counter = 0
        self._chunk_counter = 0

        self._running = False
        self._max_cycles = 1000

        self._lock = threading.RLock()

    def _generate_production_id(self) -> str:
        self._production_counter += 1
        return f"prod_{self._production_counter}"

    def _generate_chunk_id(self) -> str:
        self._chunk_counter += 1
        return f"chunk_{self._chunk_counter}"

    # Production management

    def add_production(
        self,
        name: str,
        conditions: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        priority: float = 0.5
    ) -> Production:
        """Add a production rule."""
        conds = [
            Condition(
                buffer=BufferType[c.get('buffer', 'GOAL').upper()],
                attribute=c.get('attribute', ''),
                operator=c.get('operator', '='),
                value=c.get('value'),
                variable=c.get('variable')
            )
            for c in conditions
        ]

        acts = [
            Action(
                buffer=BufferType[a.get('buffer', 'GOAL').upper()],
                operation=a.get('operation', 'modify'),
                attribute=a.get('attribute', ''),
                value=a.get('value')
            )
            for a in actions
        ]

        production = Production(
            id=self._generate_production_id(),
            name=name,
            conditions=conds,
            actions=acts,
            priority=priority
        )

        self._productions[production.id] = production
        return production

    def remove_production(
        self,
        production_id: str
    ) -> bool:
        """Remove a production."""
        if production_id in self._productions:
            del self._productions[production_id]
            return True
        return False

    # Buffer management

    def set_goal(
        self,
        goal_type: str,
        slots: Dict[str, Any]
    ) -> Chunk:
        """Set the goal buffer."""
        chunk = Chunk(
            id=self._generate_chunk_id(),
            chunk_type=goal_type,
            slots=slots,
            creation_time=time.time()
        )

        self._buffers.set_chunk(BufferType.GOAL, chunk)
        return chunk

    def set_buffer(
        self,
        buffer_type: BufferType,
        chunk_type: str,
        slots: Dict[str, Any]
    ) -> Chunk:
        """Set a buffer."""
        chunk = Chunk(
            id=self._generate_chunk_id(),
            chunk_type=chunk_type,
            slots=slots,
            creation_time=time.time()
        )

        self._buffers.set_chunk(buffer_type, chunk)
        return chunk

    def get_buffer_contents(
        self,
        buffer_type: BufferType
    ) -> Optional[Dict[str, Any]]:
        """Get buffer contents."""
        buffer = self._buffers.get_buffer(buffer_type)
        if buffer.chunk:
            return buffer.chunk.slots
        return None

    # Execution

    def step(self) -> CycleResult:
        """Execute one recognize-act cycle."""
        self._cycle_count += 1

        # 1. Match phase
        matched = []
        bindings_map = {}

        for prod in self._productions.values():
            is_match, bindings = self._matcher.match(prod, self._buffers)
            if is_match:
                matched.append(prod)
                bindings_map[prod.id] = bindings

        # 2. Conflict resolution
        selected = self._resolver.resolve(matched)

        # 3. Act phase
        actions_taken = []
        fired = False

        if selected:
            bindings = bindings_map.get(selected.id, {})
            actions_taken = self._executor.execute(selected.actions, bindings)

            selected.firings += 1
            selected.last_fired = time.time()
            self._total_firings += 1
            fired = True

            self._resolver.mark_fired(selected.id)

        result = CycleResult(
            cycle=self._cycle_count,
            matched_productions=[p.name for p in matched],
            selected_production=selected.name if selected else None,
            fired=fired,
            bindings=bindings_map.get(selected.id, {}) if selected else {},
            actions_taken=actions_taken
        )

        self._history.append(result)
        return result

    def run(
        self,
        max_cycles: int = None
    ) -> List[CycleResult]:
        """Run until no productions fire or max cycles."""
        if max_cycles is None:
            max_cycles = self._max_cycles

        results = []
        self._running = True

        for _ in range(max_cycles):
            if not self._running:
                break

            result = self.step()
            results.append(result)

            if not result.fired:
                break

        return results

    def stop(self) -> None:
        """Stop execution."""
        self._running = False

    def reset(self) -> None:
        """Reset the system."""
        self._cycle_count = 0
        self._total_firings = 0
        self._history.clear()
        self._resolver.clear_refractory()

        # Clear all buffers
        for bt in BufferType:
            self._buffers.clear_buffer(bt)

    # Analysis

    def get_production_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each production."""
        stats = {}
        for prod in self._productions.values():
            stats[prod.name] = {
                'firings': prod.firings,
                'priority': prod.priority,
                'utility': prod.utility,
                'conditions': len(prod.conditions),
                'actions': len(prod.actions)
            }
        return stats

    # Metrics

    def get_metrics(self) -> SystemMetrics:
        """Get system metrics."""
        return SystemMetrics(
            total_cycles=self._cycle_count,
            total_firings=self._total_firings,
            productions_count=len(self._productions),
            average_match_time=0.0  # Would need timing
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'productions': len(self._productions),
            'cycles': self._cycle_count,
            'firings': self._total_firings
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_production_system_engine(
    strategy: str = "priority"
) -> ProductionSystemEngine:
    """Create production system engine."""
    strategies = {
        'first': ConflictResolution.FIRST_MATCH,
        'specificity': ConflictResolution.SPECIFICITY,
        'recency': ConflictResolution.RECENCY,
        'priority': ConflictResolution.PRIORITY,
        'refractory': ConflictResolution.REFRACTORINESS
    }
    return ProductionSystemEngine(strategies.get(strategy, ConflictResolution.PRIORITY))


def demonstrate_counting() -> Dict[str, Any]:
    """Demonstrate counting with production system."""
    engine = create_production_system_engine()

    # Add counting productions
    engine.add_production(
        name="start-counting",
        conditions=[
            {'buffer': 'goal', 'attribute': 'state', 'operator': '=', 'value': 'start'},
            {'buffer': 'goal', 'attribute': 'count', 'operator': '=', 'value': 0}
        ],
        actions=[
            {'buffer': 'goal', 'operation': 'modify', 'attribute': 'state', 'value': 'counting'},
            {'buffer': 'goal', 'operation': 'modify', 'attribute': 'count', 'value': 1}
        ],
        priority=0.8
    )

    engine.add_production(
        name="increment",
        conditions=[
            {'buffer': 'goal', 'attribute': 'state', 'operator': '=', 'value': 'counting'},
            {'buffer': 'goal', 'attribute': 'count', 'operator': '<', 'value': 5}
        ],
        actions=[
            {'buffer': 'goal', 'operation': 'modify', 'attribute': 'count', 'value': 'INCREMENT'}
        ],
        priority=0.6
    )

    engine.add_production(
        name="done",
        conditions=[
            {'buffer': 'goal', 'attribute': 'state', 'operator': '=', 'value': 'counting'},
            {'buffer': 'goal', 'attribute': 'count', 'operator': '>=', 'value': 5}
        ],
        actions=[
            {'buffer': 'goal', 'operation': 'modify', 'attribute': 'state', 'value': 'done'}
        ],
        priority=0.9
    )

    # Set initial goal
    engine.set_goal('counting-goal', {'state': 'start', 'count': 0})

    # Run
    results = engine.run(max_cycles=10)

    return {
        'cycles': len(results),
        'history': [
            {'cycle': r.cycle, 'fired': r.selected_production, 'actions': r.actions_taken}
            for r in results
        ],
        'final_state': engine.get_buffer_contents(BufferType.GOAL)
    }


def get_production_system_facts() -> Dict[str, str]:
    """Get facts about production systems."""
    return {
        'newell_simon_1972': 'Production systems introduced by Newell & Simon',
        'recognize_act': 'Basic cycle: match conditions, resolve conflicts, execute actions',
        'conflict_resolution': 'Multiple strategies: specificity, recency, priority',
        'act_r': 'ACT-R is a modern production system architecture',
        'soar': 'Soar is another cognitive architecture using productions',
        'working_memory': 'Buffers serve as limited capacity working memory',
        'declarative': 'Declarative memory stores facts as chunks',
        'procedural': 'Procedural memory stores knowledge as production rules'
    }
