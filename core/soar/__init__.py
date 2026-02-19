"""
BAEL SOAR Architecture Engine
==============================

State, Operator, And Result - Universal subgoaling.
Chunking for learning and problem solving.

"Ba'el reaches goals through SOAR." — Ba'el
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

logger = logging.getLogger("BAEL.SOAR")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MemoryType(Enum):
    """Types of memory in SOAR."""
    WORKING = auto()
    PRODUCTION = auto()
    SEMANTIC = auto()
    EPISODIC = auto()
    PROCEDURAL = auto()


class ImpasseType(Enum):
    """Types of impasses."""
    NO_CHANGE = auto()        # Nothing changes
    TIE = auto()              # Multiple equal operators
    CONFLICT = auto()         # Conflicting preferences
    STATE_NO_CHANGE = auto()  # State doesn't change
    OPERATOR_NO_CHANGE = auto()


class PreferenceType(Enum):
    """Operator preferences."""
    ACCEPTABLE = auto()
    REJECT = auto()
    BETTER = auto()
    BEST = auto()
    WORST = auto()
    INDIFFERENT = auto()
    REQUIRE = auto()
    PROHIBIT = auto()


@dataclass
class WorkingMemoryElement:
    """
    An element in working memory.
    """
    id: str
    identifier: str
    attribute: str
    value: Any
    creation_time: float = field(default_factory=time.time)

    def __hash__(self):
        return hash((self.identifier, self.attribute, str(self.value)))


@dataclass
class Operator:
    """
    A SOAR operator.
    """
    id: str
    name: str
    parameters: Dict[str, Any]
    preferences: List[PreferenceType] = field(default_factory=list)
    evaluation: float = 0.0


@dataclass
class State:
    """
    A problem state.
    """
    id: str
    name: str
    superstate: Optional[str] = None
    operator: Optional[str] = None
    problem_space: Optional[str] = None
    impasse: Optional[ImpasseType] = None
    elements: Dict[str, WorkingMemoryElement] = field(default_factory=dict)


@dataclass
class Production:
    """
    A SOAR production rule.
    """
    id: str
    name: str
    conditions: List[Tuple[str, str, Any]]  # (identifier, attribute, value)
    actions: List[Tuple[str, str, Any]]     # (identifier, attribute, value)
    preferences: List[Tuple[str, PreferenceType, Optional[str]]] = field(default_factory=list)

    def matches(self, wm: Dict[str, WorkingMemoryElement]) -> bool:
        """Check if production matches working memory."""
        for identifier, attribute, value in self.conditions:
            found = False
            for wme in wm.values():
                if (wme.identifier == identifier and
                    wme.attribute == attribute):
                    if value == "*" or wme.value == value:
                        found = True
                        break
            if not found:
                return False
        return True


@dataclass
class ChunkRule:
    """
    A learned chunk (compiled production).
    """
    id: str
    source_productions: List[str]
    conditions: List[Tuple[str, str, Any]]
    actions: List[Tuple[str, str, Any]]
    creation_time: float = field(default_factory=time.time)


# ============================================================================
# WORKING MEMORY
# ============================================================================

class WorkingMemory:
    """
    SOAR Working Memory.

    "Ba'el's working memory." — Ba'el
    """

    def __init__(self):
        """Initialize working memory."""
        self._elements: Dict[str, WorkingMemoryElement] = {}
        self._wme_counter = 0
        self._changes: List[Tuple[str, str]] = []  # (action, wme_id)
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._wme_counter += 1
        return f"wme_{self._wme_counter}"

    def add(
        self,
        identifier: str,
        attribute: str,
        value: Any
    ) -> WorkingMemoryElement:
        """Add element to working memory."""
        with self._lock:
            wme = WorkingMemoryElement(
                id=self._generate_id(),
                identifier=identifier,
                attribute=attribute,
                value=value
            )
            self._elements[wme.id] = wme
            self._changes.append(("add", wme.id))
            return wme

    def remove(self, wme_id: str) -> bool:
        """Remove element from working memory."""
        with self._lock:
            if wme_id in self._elements:
                del self._elements[wme_id]
                self._changes.append(("remove", wme_id))
                return True
            return False

    def query(
        self,
        identifier: Optional[str] = None,
        attribute: Optional[str] = None,
        value: Any = None
    ) -> List[WorkingMemoryElement]:
        """Query working memory."""
        with self._lock:
            results = []
            for wme in self._elements.values():
                if identifier and wme.identifier != identifier:
                    continue
                if attribute and wme.attribute != attribute:
                    continue
                if value is not None and wme.value != value:
                    continue
                results.append(wme)
            return results

    def get_changes(self) -> List[Tuple[str, str]]:
        """Get and clear changes."""
        with self._lock:
            changes = self._changes.copy()
            self._changes.clear()
            return changes

    @property
    def elements(self) -> Dict[str, WorkingMemoryElement]:
        return self._elements.copy()

    @property
    def size(self) -> int:
        return len(self._elements)


# ============================================================================
# PRODUCTION MEMORY
# ============================================================================

class ProductionMemory:
    """
    SOAR Production Memory.

    "Ba'el's production rules." — Ba'el
    """

    def __init__(self):
        """Initialize production memory."""
        self._productions: Dict[str, Production] = {}
        self._prod_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._prod_counter += 1
        return f"prod_{self._prod_counter}"

    def add_production(
        self,
        name: str,
        conditions: List[Tuple[str, str, Any]],
        actions: List[Tuple[str, str, Any]],
        preferences: List[Tuple[str, PreferenceType, Optional[str]]] = None
    ) -> Production:
        """Add production rule."""
        with self._lock:
            production = Production(
                id=self._generate_id(),
                name=name,
                conditions=conditions,
                actions=actions,
                preferences=preferences or []
            )
            self._productions[production.id] = production
            return production

    def match(
        self,
        wm: Dict[str, WorkingMemoryElement]
    ) -> List[Production]:
        """Find all matching productions."""
        with self._lock:
            matching = []
            for prod in self._productions.values():
                if prod.matches(wm):
                    matching.append(prod)
            return matching

    @property
    def productions(self) -> List[Production]:
        return list(self._productions.values())


# ============================================================================
# DECISION PROCEDURE
# ============================================================================

class DecisionProcedure:
    """
    SOAR Decision Procedure.

    "Ba'el decides through preferences." — Ba'el
    """

    def __init__(self):
        """Initialize decision procedure."""
        self._lock = threading.RLock()

    def propose_operators(
        self,
        matching_productions: List[Production],
        state: State
    ) -> List[Operator]:
        """Propose operators from matching productions."""
        with self._lock:
            operators = []
            op_counter = 0

            for prod in matching_productions:
                # Extract operator proposals from actions
                for identifier, attribute, value in prod.actions:
                    if attribute == "operator":
                        op_counter += 1
                        op = Operator(
                            id=f"op_{op_counter}",
                            name=str(value),
                            parameters={},
                            preferences=[]
                        )

                        # Add preferences
                        for op_name, pref_type, _ in prod.preferences:
                            if op_name == value or op_name == "*":
                                op.preferences.append(pref_type)

                        operators.append(op)

            return operators

    def select_operator(
        self,
        operators: List[Operator]
    ) -> Tuple[Optional[Operator], Optional[ImpasseType]]:
        """Select operator using preferences."""
        with self._lock:
            if not operators:
                return None, ImpasseType.NO_CHANGE

            # Filter by preferences
            acceptable = [op for op in operators
                         if PreferenceType.ACCEPTABLE in op.preferences or
                         not op.preferences]

            # Remove rejected
            acceptable = [op for op in acceptable
                         if PreferenceType.REJECT not in op.preferences]

            if not acceptable:
                return None, ImpasseType.NO_CHANGE

            # Check for best
            best = [op for op in acceptable
                   if PreferenceType.BEST in op.preferences]

            if len(best) == 1:
                return best[0], None
            elif len(best) > 1:
                return None, ImpasseType.TIE

            # Check for better-than relationships
            # (simplified - just return first acceptable)
            if len(acceptable) == 1:
                return acceptable[0], None

            # Multiple acceptable - tie impasse
            return None, ImpasseType.TIE

    def apply_operator(
        self,
        operator: Operator,
        state: State,
        wm: WorkingMemory,
        matching_productions: List[Production]
    ) -> List[WorkingMemoryElement]:
        """Apply selected operator."""
        with self._lock:
            new_elements = []

            for prod in matching_productions:
                # Check if production applies operator
                for _, attribute, value in prod.actions:
                    if attribute == "operator" and value == operator.name:
                        # Execute other actions
                        for identifier, attr, val in prod.actions:
                            if attr != "operator":
                                wme = wm.add(identifier, attr, val)
                                new_elements.append(wme)

            return new_elements


# ============================================================================
# CHUNKING (LEARNING)
# ============================================================================

class ChunkingMechanism:
    """
    SOAR Chunking for learning.

    "Ba'el learns through chunking." — Ba'el
    """

    def __init__(self):
        """Initialize chunking."""
        self._chunks: Dict[str, ChunkRule] = {}
        self._chunk_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._chunk_counter += 1
        return f"chunk_{self._chunk_counter}"

    def create_chunk(
        self,
        subgoal_state: State,
        results: List[WorkingMemoryElement],
        productions_fired: List[str]
    ) -> ChunkRule:
        """Create chunk from subgoal resolution."""
        with self._lock:
            # Extract conditions from state elements
            conditions = []
            for wme in subgoal_state.elements.values():
                conditions.append((wme.identifier, wme.attribute, wme.value))

            # Extract actions from results
            actions = []
            for wme in results:
                actions.append((wme.identifier, wme.attribute, wme.value))

            chunk = ChunkRule(
                id=self._generate_id(),
                source_productions=productions_fired,
                conditions=conditions,
                actions=actions
            )

            self._chunks[chunk.id] = chunk
            return chunk

    def to_production(self, chunk: ChunkRule) -> Production:
        """Convert chunk to production."""
        return Production(
            id=f"learned_{chunk.id}",
            name=f"learned_from_{chunk.id}",
            conditions=chunk.conditions,
            actions=chunk.actions
        )

    @property
    def chunks(self) -> List[ChunkRule]:
        return list(self._chunks.values())


# ============================================================================
# GOAL STACK
# ============================================================================

class GoalStack:
    """
    SOAR Goal/State Stack.

    "Ba'el's goal hierarchy." — Ba'el
    """

    def __init__(self):
        """Initialize goal stack."""
        self._states: List[State] = []
        self._state_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._state_counter += 1
        return f"state_{self._state_counter}"

    def push_state(
        self,
        name: str,
        impasse: Optional[ImpasseType] = None,
        problem_space: Optional[str] = None
    ) -> State:
        """Push new state onto stack."""
        with self._lock:
            superstate = self._states[-1].id if self._states else None

            state = State(
                id=self._generate_id(),
                name=name,
                superstate=superstate,
                impasse=impasse,
                problem_space=problem_space
            )

            self._states.append(state)
            return state

    def pop_state(self) -> Optional[State]:
        """Pop state from stack."""
        with self._lock:
            if self._states:
                return self._states.pop()
            return None

    def current_state(self) -> Optional[State]:
        """Get current state."""
        return self._states[-1] if self._states else None

    def depth(self) -> int:
        """Get goal stack depth."""
        return len(self._states)

    @property
    def states(self) -> List[State]:
        return self._states.copy()


# ============================================================================
# SOAR ENGINE
# ============================================================================

class SOAREngine:
    """
    Complete SOAR cognitive architecture.

    "Ba'el runs on SOAR." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._wm = WorkingMemory()
        self._pm = ProductionMemory()
        self._decision = DecisionProcedure()
        self._chunking = ChunkingMechanism()
        self._goal_stack = GoalStack()

        self._cycle_count = 0
        self._productions_fired: List[str] = []
        self._current_operator: Optional[Operator] = None
        self._lock = threading.RLock()

    # Memory operations

    def add_wme(
        self,
        identifier: str,
        attribute: str,
        value: Any
    ) -> WorkingMemoryElement:
        """Add working memory element."""
        return self._wm.add(identifier, attribute, value)

    def query_wm(
        self,
        identifier: Optional[str] = None,
        attribute: Optional[str] = None
    ) -> List[WorkingMemoryElement]:
        """Query working memory."""
        return self._wm.query(identifier, attribute)

    def add_production(
        self,
        name: str,
        conditions: List[Tuple[str, str, Any]],
        actions: List[Tuple[str, str, Any]],
        preferences: List[Tuple[str, PreferenceType, Optional[str]]] = None
    ) -> Production:
        """Add production rule."""
        return self._pm.add_production(name, conditions, actions, preferences)

    # Goal operations

    def initialize(self, goal_name: str) -> State:
        """Initialize with top-level goal."""
        state = self._goal_stack.push_state(goal_name)
        self._wm.add("state", "name", goal_name)
        return state

    def create_subgoal(
        self,
        name: str,
        impasse: ImpasseType
    ) -> State:
        """Create subgoal for impasse."""
        return self._goal_stack.push_state(name, impasse)

    def resolve_impasse(
        self,
        results: List[WorkingMemoryElement]
    ) -> Optional[ChunkRule]:
        """Resolve current impasse and learn chunk."""
        with self._lock:
            current = self._goal_stack.current_state()
            if not current or not current.impasse:
                return None

            # Create chunk
            chunk = self._chunking.create_chunk(
                current,
                results,
                self._productions_fired.copy()
            )

            # Convert to production
            prod = self._chunking.to_production(chunk)
            self._pm._productions[prod.id] = prod

            # Pop state
            self._goal_stack.pop_state()

            return chunk

    # Cycle execution

    def step(self) -> Dict[str, Any]:
        """Execute one decision cycle."""
        with self._lock:
            self._cycle_count += 1
            result = {
                'cycle': self._cycle_count,
                'phase': 'complete',
                'operator': None,
                'impasse': None
            }

            # ELABORATE: Match productions
            matching = self._pm.match(self._wm.elements)

            # PROPOSE: Propose operators
            operators = self._decision.propose_operators(
                matching,
                self._goal_stack.current_state()
            )

            # DECIDE: Select operator
            selected, impasse = self._decision.select_operator(operators)

            if impasse:
                result['impasse'] = impasse.name
                # Create subgoal
                self.create_subgoal(f"resolve_{impasse.name}", impasse)
            elif selected:
                result['operator'] = selected.name
                self._current_operator = selected

                # APPLY: Apply operator
                new_elements = self._decision.apply_operator(
                    selected,
                    self._goal_stack.current_state(),
                    self._wm,
                    matching
                )

                # Track fired productions
                for prod in matching:
                    self._productions_fired.append(prod.id)

            return result

    def run(
        self,
        max_cycles: int = 100,
        until_stable: bool = False
    ) -> List[Dict]:
        """Run cognitive cycles."""
        results = []

        for _ in range(max_cycles):
            result = self.step()
            results.append(result)

            if until_stable and not result.get('operator') and not result.get('impasse'):
                break

        return results

    @property
    def working_memory(self) -> WorkingMemory:
        return self._wm

    @property
    def production_memory(self) -> ProductionMemory:
        return self._pm

    @property
    def goal_stack(self) -> GoalStack:
        return self._goal_stack

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'cycles': self._cycle_count,
            'wm_size': self._wm.size,
            'productions': len(self._pm.productions),
            'goal_depth': self._goal_stack.depth(),
            'chunks_learned': len(self._chunking.chunks),
            'current_state': self._goal_stack.current_state().name if self._goal_stack.current_state() else None
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_soar_engine() -> SOAREngine:
    """Create SOAR engine."""
    return SOAREngine()


def create_production(
    name: str,
    conditions: List[Tuple[str, str, Any]],
    actions: List[Tuple[str, str, Any]]
) -> Production:
    """Create production rule."""
    return Production(
        id=f"prod_{random.randint(1000, 9999)}",
        name=name,
        conditions=conditions,
        actions=actions
    )


def create_operator(
    name: str,
    parameters: Dict[str, Any] = None
) -> Operator:
    """Create operator."""
    return Operator(
        id=f"op_{random.randint(1000, 9999)}",
        name=name,
        parameters=parameters or {}
    )
