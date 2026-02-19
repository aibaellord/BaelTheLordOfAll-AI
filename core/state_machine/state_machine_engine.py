"""
BAEL State Machine Engine
=========================

Finite State Machine implementation with:
- State transitions
- Guards and actions
- Hierarchical states
- Parallel states
- Event handling

"Ba'el governs all transitions of reality." — Ba'el
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict, deque
import threading
import uuid
import copy

logger = logging.getLogger("BAEL.StateMachine")


# ============================================================================
# ENUMS
# ============================================================================

class StateType(Enum):
    """State types."""
    ATOMIC = "atomic"           # Simple state
    COMPOUND = "compound"       # Has child states
    PARALLEL = "parallel"       # Parallel regions
    INITIAL = "initial"         # Initial pseudo-state
    FINAL = "final"             # Final state
    HISTORY = "history"         # History pseudo-state
    DEEP_HISTORY = "deep_history"


class TransitionType(Enum):
    """Transition types."""
    EXTERNAL = "external"       # Exit and re-enter
    INTERNAL = "internal"       # Stay in state
    LOCAL = "local"             # Like external but don't exit if target is child


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MachineStatus(Enum):
    """Machine status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATED = "terminated"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class State:
    """A state in the state machine."""
    id: str
    name: str

    # Type
    state_type: StateType = StateType.ATOMIC

    # Parent/children for hierarchy
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    initial_child: Optional[str] = None

    # Actions
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None
    on_do: Optional[Callable] = None  # Activity while in state

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # History
    history_state: Optional[str] = None

    def __hash__(self):
        return hash(self.id)


@dataclass
class Transition:
    """A transition between states."""
    id: str

    # Source and target
    source_id: str
    target_id: str

    # Event trigger
    event: Optional[str] = None

    # Guard condition
    guard: Optional[Callable[[Dict], bool]] = None

    # Actions
    actions: List[Callable] = field(default_factory=list)

    # Type
    transition_type: TransitionType = TransitionType.EXTERNAL

    # Priority
    priority: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """An event to be processed."""
    id: str
    name: str

    # Data
    data: Dict[str, Any] = field(default_factory=dict)

    # Priority
    priority: EventPriority = EventPriority.NORMAL

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    # Deferred
    deferred: bool = False


@dataclass
class MachineContext:
    """Context data for the state machine."""
    data: Dict[str, Any] = field(default_factory=dict)

    # Current state(s)
    active_states: Set[str] = field(default_factory=set)

    # History
    state_history: List[str] = field(default_factory=list)
    transition_history: List[str] = field(default_factory=list)

    # Event processing
    current_event: Optional[Event] = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, data: Dict[str, Any]) -> None:
        self.data.update(data)


@dataclass
class StateMachineConfig:
    """State machine configuration."""
    name: str = "default"

    # Initial state
    initial_state: Optional[str] = None

    # Options
    auto_start: bool = True
    history_size: int = 100
    max_transitions_per_event: int = 100  # Prevent infinite loops

    # Parallel
    parallel_execution: bool = False


# ============================================================================
# STATE REGISTRY
# ============================================================================

class StateRegistry:
    """
    Registry for states and transitions.
    """

    def __init__(self):
        """Initialize registry."""
        self._states: Dict[str, State] = {}
        self._transitions: Dict[str, Transition] = {}
        self._transitions_by_source: Dict[str, List[Transition]] = defaultdict(list)
        self._transitions_by_event: Dict[str, List[Transition]] = defaultdict(list)
        self._lock = threading.RLock()

    def register_state(self, state: State) -> None:
        """Register a state."""
        with self._lock:
            self._states[state.id] = state

            # Update parent's children
            if state.parent_id:
                parent = self._states.get(state.parent_id)
                if parent and state.id not in parent.children:
                    parent.children.append(state.id)

    def get_state(self, state_id: str) -> Optional[State]:
        """Get a state by ID."""
        return self._states.get(state_id)

    def get_all_states(self) -> List[State]:
        """Get all states."""
        return list(self._states.values())

    def register_transition(self, transition: Transition) -> None:
        """Register a transition."""
        with self._lock:
            self._transitions[transition.id] = transition
            self._transitions_by_source[transition.source_id].append(transition)

            if transition.event:
                self._transitions_by_event[transition.event].append(transition)

    def get_transition(self, transition_id: str) -> Optional[Transition]:
        """Get a transition by ID."""
        return self._transitions.get(transition_id)

    def get_transitions_from(self, source_id: str) -> List[Transition]:
        """Get transitions from a source state."""
        return self._transitions_by_source.get(source_id, [])

    def get_transitions_for_event(self, event_name: str) -> List[Transition]:
        """Get transitions for an event."""
        return self._transitions_by_event.get(event_name, [])

    def get_ancestors(self, state_id: str) -> List[str]:
        """Get ancestor states."""
        ancestors = []
        state = self._states.get(state_id)

        while state and state.parent_id:
            ancestors.append(state.parent_id)
            state = self._states.get(state.parent_id)

        return ancestors

    def get_descendants(self, state_id: str) -> List[str]:
        """Get descendant states."""
        descendants = []
        state = self._states.get(state_id)

        if state:
            for child_id in state.children:
                descendants.append(child_id)
                descendants.extend(self.get_descendants(child_id))

        return descendants

    def is_ancestor(self, ancestor_id: str, descendant_id: str) -> bool:
        """Check if state is ancestor of another."""
        return ancestor_id in self.get_ancestors(descendant_id)

    def get_lca(self, state1_id: str, state2_id: str) -> Optional[str]:
        """Get lowest common ancestor of two states."""
        ancestors1 = set([state1_id] + self.get_ancestors(state1_id))

        current = state2_id
        while current:
            if current in ancestors1:
                return current
            state = self._states.get(current)
            current = state.parent_id if state else None

        return None


# ============================================================================
# EVENT QUEUE
# ============================================================================

class EventQueue:
    """
    Priority event queue.
    """

    def __init__(self):
        """Initialize queue."""
        self._queues: Dict[EventPriority, deque] = {
            p: deque() for p in EventPriority
        }
        self._lock = threading.RLock()

    def enqueue(self, event: Event) -> None:
        """Add event to queue."""
        with self._lock:
            self._queues[event.priority].append(event)

    def dequeue(self) -> Optional[Event]:
        """Get next event."""
        with self._lock:
            # Check from highest to lowest priority
            for priority in sorted(EventPriority, key=lambda p: p.value, reverse=True):
                if self._queues[priority]:
                    return self._queues[priority].popleft()
        return None

    def peek(self) -> Optional[Event]:
        """Peek at next event without removing."""
        with self._lock:
            for priority in sorted(EventPriority, key=lambda p: p.value, reverse=True):
                if self._queues[priority]:
                    return self._queues[priority][0]
        return None

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return all(len(q) == 0 for q in self._queues.values())

    def size(self) -> int:
        """Get total queue size."""
        with self._lock:
            return sum(len(q) for q in self._queues.values())

    def clear(self) -> None:
        """Clear all events."""
        with self._lock:
            for q in self._queues.values():
                q.clear()


# ============================================================================
# TRANSITION HANDLER
# ============================================================================

class TransitionHandler:
    """
    Handles state transitions.
    """

    def __init__(self, registry: StateRegistry, config: StateMachineConfig):
        """Initialize handler."""
        self.registry = registry
        self.config = config

    def find_transitions(
        self,
        event: Event,
        context: MachineContext
    ) -> List[Transition]:
        """Find applicable transitions for event."""
        candidates = []

        for state_id in context.active_states:
            # Get transitions from this state and ancestors
            state_ids = [state_id] + self.registry.get_ancestors(state_id)

            for sid in state_ids:
                transitions = self.registry.get_transitions_from(sid)

                for trans in transitions:
                    # Check event match
                    if trans.event and trans.event != event.name:
                        continue

                    # Check guard
                    if trans.guard:
                        try:
                            if not trans.guard(context.data):
                                continue
                        except Exception as e:
                            logger.warning(f"Guard failed: {e}")
                            continue

                    candidates.append(trans)

        # Sort by priority
        candidates.sort(key=lambda t: t.priority, reverse=True)

        return candidates

    def compute_exit_set(
        self,
        transition: Transition,
        context: MachineContext
    ) -> List[str]:
        """Compute states to exit."""
        source = self.registry.get_state(transition.source_id)
        target = self.registry.get_state(transition.target_id)

        if not source or not target:
            return []

        if transition.transition_type == TransitionType.INTERNAL:
            return []

        # Find LCA
        lca = self.registry.get_lca(source.id, target.id)

        # Exit all active states up to LCA
        exit_set = []

        for state_id in list(context.active_states):
            state = self.registry.get_state(state_id)
            if state:
                ancestors = [state_id] + self.registry.get_ancestors(state_id)

                # Check if state is below LCA
                if lca and lca in ancestors:
                    lca_index = ancestors.index(lca)
                    exit_set.extend(ancestors[:lca_index])

        # Sort for proper exit order (children before parents)
        def exit_order(sid):
            return -len(self.registry.get_ancestors(sid))

        exit_set = list(set(exit_set))
        exit_set.sort(key=exit_order)

        return exit_set

    def compute_entry_set(
        self,
        transition: Transition,
        context: MachineContext
    ) -> List[str]:
        """Compute states to enter."""
        source = self.registry.get_state(transition.source_id)
        target = self.registry.get_state(transition.target_id)

        if not source or not target:
            return []

        if transition.transition_type == TransitionType.INTERNAL:
            return []

        # Find LCA
        lca = self.registry.get_lca(source.id, target.id)

        # Enter states from LCA to target
        entry_set = []

        ancestors = self.registry.get_ancestors(target.id)

        if lca:
            if lca in ancestors:
                lca_index = ancestors.index(lca)
                entry_set = ancestors[:lca_index]
            else:
                entry_set = ancestors
        else:
            entry_set = ancestors

        entry_set.append(target.id)

        # Reverse for proper entry order (parents before children)
        entry_set.reverse()

        # Add initial states for compound states
        final_entry_set = []

        for state_id in entry_set:
            final_entry_set.append(state_id)
            state = self.registry.get_state(state_id)

            if state and state.state_type == StateType.COMPOUND:
                # Enter initial child
                if state.initial_child:
                    final_entry_set.append(state.initial_child)

        return final_entry_set

    async def execute_transition(
        self,
        transition: Transition,
        context: MachineContext
    ) -> bool:
        """Execute a transition."""
        try:
            # Compute exit and entry sets
            exit_set = self.compute_exit_set(transition, context)
            entry_set = self.compute_entry_set(transition, context)

            # Execute exits
            for state_id in exit_set:
                await self._exit_state(state_id, context)

            # Execute transition actions
            for action in transition.actions:
                if asyncio.iscoroutinefunction(action):
                    await action(context)
                else:
                    action(context)

            # Execute entries
            for state_id in entry_set:
                await self._enter_state(state_id, context)

            # Record history
            context.transition_history.append(transition.id)
            if len(context.transition_history) > self.config.history_size:
                context.transition_history.pop(0)

            return True

        except Exception as e:
            logger.error(f"Transition failed: {e}")
            return False

    async def _enter_state(self, state_id: str, context: MachineContext) -> None:
        """Enter a state."""
        state = self.registry.get_state(state_id)
        if not state:
            return

        context.active_states.add(state_id)
        context.state_history.append(state_id)

        if len(context.state_history) > self.config.history_size:
            context.state_history.pop(0)

        # Execute on_enter
        if state.on_enter:
            if asyncio.iscoroutinefunction(state.on_enter):
                await state.on_enter(context)
            else:
                state.on_enter(context)

        logger.debug(f"Entered state: {state.name}")

    async def _exit_state(self, state_id: str, context: MachineContext) -> None:
        """Exit a state."""
        state = self.registry.get_state(state_id)
        if not state:
            return

        # Execute on_exit
        if state.on_exit:
            if asyncio.iscoroutinefunction(state.on_exit):
                await state.on_exit(context)
            else:
                state.on_exit(context)

        context.active_states.discard(state_id)

        # Save history for parent
        parent = self.registry.get_state(state.parent_id) if state.parent_id else None
        if parent and parent.state_type in (StateType.HISTORY, StateType.DEEP_HISTORY):
            parent.history_state = state_id

        logger.debug(f"Exited state: {state.name}")


# ============================================================================
# MAIN STATE MACHINE
# ============================================================================

class StateMachine:
    """
    Main state machine engine.

    Features:
    - Hierarchical states
    - Guards and actions
    - Event processing
    - History states

    "Ba'el transitions between states of existence." — Ba'el
    """

    def __init__(self, config: Optional[StateMachineConfig] = None):
        """Initialize state machine."""
        self.config = config or StateMachineConfig()

        # Components
        self.registry = StateRegistry()
        self.event_queue = EventQueue()
        self.handler = TransitionHandler(self.registry, self.config)

        # Context
        self.context = MachineContext()

        # Status
        self._status = MachineStatus.IDLE
        self._running = False

        self._lock = threading.RLock()

        logger.info(f"StateMachine '{self.config.name}' initialized")

    @property
    def status(self) -> MachineStatus:
        return self._status

    @property
    def current_states(self) -> Set[str]:
        return self.context.active_states.copy()

    def add_state(
        self,
        name: str,
        state_type: StateType = StateType.ATOMIC,
        parent: Optional[str] = None,
        initial: bool = False,
        on_enter: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
        **metadata
    ) -> State:
        """Add a state."""
        state = State(
            id=str(uuid.uuid4()),
            name=name,
            state_type=state_type,
            parent_id=parent,
            on_enter=on_enter,
            on_exit=on_exit,
            metadata=metadata
        )

        self.registry.register_state(state)

        if initial or (not self.config.initial_state and parent is None):
            self.config.initial_state = state.id

            # Set as initial child of parent
            if parent:
                parent_state = self.registry.get_state(parent)
                if parent_state:
                    parent_state.initial_child = state.id

        return state

    def add_transition(
        self,
        source: str,
        target: str,
        event: Optional[str] = None,
        guard: Optional[Callable[[Dict], bool]] = None,
        action: Optional[Callable] = None,
        actions: Optional[List[Callable]] = None,
        transition_type: TransitionType = TransitionType.EXTERNAL,
        priority: int = 0
    ) -> Transition:
        """Add a transition."""
        # Find state IDs by name if needed
        source_id = self._resolve_state(source)
        target_id = self._resolve_state(target)

        if not source_id or not target_id:
            raise ValueError(f"Invalid state: {source} or {target}")

        all_actions = []
        if action:
            all_actions.append(action)
        if actions:
            all_actions.extend(actions)

        transition = Transition(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            event=event,
            guard=guard,
            actions=all_actions,
            transition_type=transition_type,
            priority=priority
        )

        self.registry.register_transition(transition)

        return transition

    def _resolve_state(self, state_ref: str) -> Optional[str]:
        """Resolve state name or ID."""
        # Check if it's already an ID
        state = self.registry.get_state(state_ref)
        if state:
            return state.id

        # Search by name
        for s in self.registry.get_all_states():
            if s.name == state_ref:
                return s.id

        return None

    async def start(self) -> None:
        """Start the state machine."""
        if self._status != MachineStatus.IDLE:
            return

        self._status = MachineStatus.RUNNING
        self._running = True

        # Enter initial state
        if self.config.initial_state:
            await self.handler._enter_state(self.config.initial_state, self.context)

        # Start event loop if auto_start
        if self.config.auto_start:
            asyncio.create_task(self._event_loop())

        logger.info(f"StateMachine '{self.config.name}' started")

    async def stop(self) -> None:
        """Stop the state machine."""
        self._running = False

        # Exit all active states
        for state_id in list(self.context.active_states):
            await self.handler._exit_state(state_id, self.context)

        self._status = MachineStatus.TERMINATED

        logger.info(f"StateMachine '{self.config.name}' stopped")

    async def pause(self) -> None:
        """Pause event processing."""
        self._status = MachineStatus.PAUSED

    async def resume(self) -> None:
        """Resume event processing."""
        if self._status == MachineStatus.PAUSED:
            self._status = MachineStatus.RUNNING

    def send(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL
    ) -> Event:
        """Send an event to the machine."""
        event = Event(
            id=str(uuid.uuid4()),
            name=event_name,
            data=data or {},
            priority=priority
        )

        self.event_queue.enqueue(event)

        return event

    async def send_and_wait(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        timeout: float = 5.0
    ) -> bool:
        """Send event and wait for processing."""
        event = self.send(event_name, data, priority)

        # Wait for event to be processed
        start = datetime.now()

        while (datetime.now() - start).total_seconds() < timeout:
            # Check if event was processed
            if event.id in [e.id for e in self.context.transition_history]:
                return True
            await asyncio.sleep(0.01)

        return False

    async def process_event(self, event: Event) -> bool:
        """Process a single event."""
        if self._status != MachineStatus.RUNNING:
            return False

        self.context.current_event = event

        try:
            # Find applicable transitions
            transitions = self.handler.find_transitions(event, self.context)

            if not transitions:
                logger.debug(f"No transitions for event: {event.name}")
                return False

            # Execute first applicable transition
            transition = transitions[0]
            success = await self.handler.execute_transition(transition, self.context)

            return success

        finally:
            self.context.current_event = None

    async def _event_loop(self) -> None:
        """Event processing loop."""
        while self._running:
            if self._status != MachineStatus.RUNNING:
                await asyncio.sleep(0.01)
                continue

            event = self.event_queue.dequeue()

            if event:
                await self.process_event(event)
            else:
                await asyncio.sleep(0.01)

    def is_in_state(self, state_ref: str) -> bool:
        """Check if machine is in a state."""
        state_id = self._resolve_state(state_ref)
        if not state_id:
            return False

        # Check direct match
        if state_id in self.context.active_states:
            return True

        # Check if active states are descendants
        for active_id in self.context.active_states:
            if self.registry.is_ancestor(state_id, active_id):
                return True

        return False

    def get_context(self) -> MachineContext:
        """Get current context."""
        return self.context

    def set_context_data(self, key: str, value: Any) -> None:
        """Set context data."""
        self.context.set(key, value)

    def get_context_data(self, key: str, default: Any = None) -> Any:
        """Get context data."""
        return self.context.get(key, default)

    def get_status(self) -> Dict[str, Any]:
        """Get machine status."""
        return {
            'name': self.config.name,
            'status': self._status.value,
            'active_states': [
                self.registry.get_state(s).name
                for s in self.context.active_states
                if self.registry.get_state(s)
            ],
            'pending_events': self.event_queue.size(),
            'transition_count': len(self.context.transition_history)
        }


# ============================================================================
# STATE MACHINE ENGINE (Factory)
# ============================================================================

class StateMachineEngine:
    """
    Factory for creating and managing state machines.
    """

    def __init__(self):
        """Initialize engine."""
        self._machines: Dict[str, StateMachine] = {}
        self._lock = threading.RLock()

    def create(
        self,
        name: str,
        config: Optional[StateMachineConfig] = None
    ) -> StateMachine:
        """Create a new state machine."""
        if config is None:
            config = StateMachineConfig(name=name)
        else:
            config.name = name

        machine = StateMachine(config)

        with self._lock:
            self._machines[name] = machine

        return machine

    def get(self, name: str) -> Optional[StateMachine]:
        """Get a state machine by name."""
        return self._machines.get(name)

    def list_machines(self) -> List[str]:
        """List all machines."""
        return list(self._machines.keys())

    async def start_all(self) -> None:
        """Start all machines."""
        for machine in self._machines.values():
            await machine.start()

    async def stop_all(self) -> None:
        """Stop all machines."""
        for machine in self._machines.values():
            await machine.stop()


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

state_machine_engine = StateMachineEngine()
