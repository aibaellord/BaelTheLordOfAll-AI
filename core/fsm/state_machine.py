#!/usr/bin/env python3
"""
BAEL - State Machine Engine
Comprehensive finite state machine implementation.

This module provides a complete state machine framework
for modeling complex state transitions and behaviors.

Features:
- Finite state machine
- Hierarchical states
- Guard conditions
- Actions and effects
- Transition hooks
- State persistence
- Event-driven transitions
- Parallel states
- History states
- Async execution
"""

import asyncio
import functools
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
TState = TypeVar('TState')
TEvent = TypeVar('TEvent')


# =============================================================================
# ENUMS
# =============================================================================

class StateType(Enum):
    """Types of states."""
    INITIAL = "initial"
    NORMAL = "normal"
    FINAL = "final"
    PARALLEL = "parallel"
    HISTORY = "history"


class TransitionType(Enum):
    """Types of transitions."""
    EXTERNAL = "external"
    INTERNAL = "internal"
    LOCAL = "local"


class HistoryType(Enum):
    """Types of history states."""
    SHALLOW = "shallow"
    DEEP = "deep"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class StateContext:
    """Context passed during state transitions."""
    machine_id: str
    current_state: str
    event: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class TransitionResult:
    """Result of a transition attempt."""
    success: bool
    from_state: str
    to_state: Optional[str]
    event: str
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class StateHistory:
    """Record of state transitions."""
    from_state: str
    to_state: str
    event: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateConfig:
    """Configuration for a state."""
    name: str
    state_type: StateType = StateType.NORMAL

    # Actions
    on_enter: Optional[Callable[[StateContext], Awaitable[None]]] = None
    on_exit: Optional[Callable[[StateContext], Awaitable[None]]] = None

    # Parent for hierarchical states
    parent: Optional[str] = None

    # Sub-states for parallel states
    substates: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransitionConfig:
    """Configuration for a transition."""
    from_state: str
    to_state: str
    event: str
    transition_type: TransitionType = TransitionType.EXTERNAL

    # Guard condition
    guard: Optional[Callable[[StateContext], bool]] = None

    # Action to execute
    action: Optional[Callable[[StateContext], Awaitable[None]]] = None

    # Priority for multiple matching transitions
    priority: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# STATE
# =============================================================================

class State:
    """
    Represents a state in the state machine.
    """

    def __init__(
        self,
        name: str,
        state_type: StateType = StateType.NORMAL,
        parent: 'State' = None
    ):
        self.name = name
        self.state_type = state_type
        self.parent = parent

        # Callbacks
        self.on_enter_callbacks: List[Callable] = []
        self.on_exit_callbacks: List[Callable] = []
        self.on_stay_callbacks: List[Callable] = []

        # Substates
        self.substates: Dict[str, 'State'] = {}
        self.initial_substate: Optional[str] = None

        # Metadata
        self.metadata: Dict[str, Any] = {}

    def add_substate(self, state: 'State') -> None:
        """Add a substate."""
        state.parent = self
        self.substates[state.name] = state

    def on_enter(self, callback: Callable) -> Callable:
        """Add enter callback (decorator)."""
        self.on_enter_callbacks.append(callback)
        return callback

    def on_exit(self, callback: Callable) -> Callable:
        """Add exit callback (decorator)."""
        self.on_exit_callbacks.append(callback)
        return callback

    async def enter(self, context: StateContext) -> None:
        """Execute enter actions."""
        for callback in self.on_enter_callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback(context)
            else:
                callback(context)

    async def exit(self, context: StateContext) -> None:
        """Execute exit actions."""
        for callback in self.on_exit_callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback(context)
            else:
                callback(context)

    def get_path(self) -> List['State']:
        """Get path from root to this state."""
        path = [self]
        current = self.parent

        while current:
            path.insert(0, current)
            current = current.parent

        return path

    def is_descendant_of(self, ancestor: 'State') -> bool:
        """Check if this state is descendant of another."""
        current = self.parent

        while current:
            if current == ancestor:
                return True
            current = current.parent

        return False


# =============================================================================
# TRANSITION
# =============================================================================

class Transition:
    """
    Represents a state transition.
    """

    def __init__(
        self,
        from_state: str,
        to_state: str,
        event: str,
        transition_type: TransitionType = TransitionType.EXTERNAL
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.event = event
        self.transition_type = transition_type

        # Guard
        self._guard: Optional[Callable] = None

        # Actions
        self._actions: List[Callable] = []

        # Priority
        self.priority = 0

    def guard(self, func: Callable[[StateContext], bool]) -> 'Transition':
        """Set guard condition."""
        self._guard = func
        return self

    def action(self, func: Callable[[StateContext], Awaitable[None]]) -> 'Transition':
        """Add action to execute during transition."""
        self._actions.append(func)
        return self

    async def can_transition(self, context: StateContext) -> bool:
        """Check if transition is allowed."""
        if not self._guard:
            return True

        if asyncio.iscoroutinefunction(self._guard):
            return await self._guard(context)
        return self._guard(context)

    async def execute(self, context: StateContext) -> None:
        """Execute transition actions."""
        for action in self._actions:
            if asyncio.iscoroutinefunction(action):
                await action(context)
            else:
                action(context)


# =============================================================================
# STATE MACHINE
# =============================================================================

class FSMachine:
    """
    Core finite state machine implementation.
    """

    def __init__(
        self,
        name: str,
        initial_state: str = None
    ):
        self.name = name
        self.machine_id = str(uuid.uuid4())

        # States
        self.states: Dict[str, State] = {}
        self.initial_state = initial_state
        self._current_state: Optional[str] = None

        # Transitions
        self.transitions: Dict[str, List[Transition]] = defaultdict(list)

        # History
        self.history: deque = deque(maxlen=1000)
        self.state_history: Dict[str, str] = {}  # For history states

        # Context data
        self.context_data: Dict[str, Any] = {}

        # Callbacks
        self.on_transition_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []

        # Statistics
        self.transition_count = 0
        self.error_count = 0

    @property
    def current_state(self) -> Optional[str]:
        """Get current state."""
        return self._current_state

    @property
    def current_state_obj(self) -> Optional[State]:
        """Get current state object."""
        if self._current_state:
            return self.states.get(self._current_state)
        return None

    def add_state(
        self,
        name: str,
        state_type: StateType = StateType.NORMAL,
        is_initial: bool = False
    ) -> State:
        """Add a state to the machine."""
        state = State(name, state_type)
        self.states[name] = state

        if is_initial or state_type == StateType.INITIAL:
            self.initial_state = name

        return state

    def add_transition(
        self,
        from_state: str,
        to_state: str,
        event: str
    ) -> Transition:
        """Add a transition."""
        transition = Transition(from_state, to_state, event)
        self.transitions[event].append(transition)
        return transition

    def on(self, event: str) -> Callable:
        """Decorator to add transition for event."""
        def decorator(func: Callable) -> Callable:
            # Parse from function annotations or default
            from_state = getattr(func, '_from_state', '*')
            to_state = getattr(func, '_to_state', '*')

            transition = self.add_transition(from_state, to_state, event)
            transition.action(func)
            return func
        return decorator

    async def start(self) -> None:
        """Start the state machine."""
        if not self.initial_state:
            raise ValueError("No initial state defined")

        if self.initial_state not in self.states:
            raise ValueError(f"Initial state '{self.initial_state}' not found")

        self._current_state = self.initial_state

        # Execute enter action
        state = self.states[self.initial_state]
        context = self._create_context("__start__")
        await state.enter(context)

    async def trigger(
        self,
        event: str,
        data: Dict[str, Any] = None
    ) -> TransitionResult:
        """Trigger an event."""
        start_time = time.time()

        if not self._current_state:
            return TransitionResult(
                success=False,
                from_state="",
                to_state=None,
                event=event,
                error="State machine not started"
            )

        context = self._create_context(event, data)

        # Find matching transitions
        matching = self._find_transitions(event)

        if not matching:
            return TransitionResult(
                success=False,
                from_state=self._current_state,
                to_state=None,
                event=event,
                error=f"No transition for event '{event}' in state '{self._current_state}'"
            )

        # Try transitions in priority order
        for transition in sorted(matching, key=lambda t: -t.priority):
            try:
                if await transition.can_transition(context):
                    # Execute transition
                    result = await self._execute_transition(transition, context)
                    result.duration_ms = (time.time() - start_time) * 1000
                    return result
            except Exception as e:
                self.error_count += 1

                for callback in self.on_error_callbacks:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(context, e)
                    else:
                        callback(context, e)

                return TransitionResult(
                    success=False,
                    from_state=self._current_state,
                    to_state=None,
                    event=event,
                    error=str(e),
                    duration_ms=(time.time() - start_time) * 1000
                )

        return TransitionResult(
            success=False,
            from_state=self._current_state,
            to_state=None,
            event=event,
            error="No transition guard passed"
        )

    def _create_context(
        self,
        event: str,
        data: Dict[str, Any] = None
    ) -> StateContext:
        """Create state context."""
        return StateContext(
            machine_id=self.machine_id,
            current_state=self._current_state or "",
            event=event,
            data={**self.context_data, **(data or {})}
        )

    def _find_transitions(self, event: str) -> List[Transition]:
        """Find transitions matching current state and event."""
        matching = []

        for transition in self.transitions.get(event, []):
            if transition.from_state == self._current_state:
                matching.append(transition)
            elif transition.from_state == '*':
                matching.append(transition)

        return matching

    async def _execute_transition(
        self,
        transition: Transition,
        context: StateContext
    ) -> TransitionResult:
        """Execute a transition."""
        from_state = self._current_state
        to_state = transition.to_state

        # Get state objects
        current = self.states.get(from_state)
        target = self.states.get(to_state)

        if not target and to_state != '*':
            return TransitionResult(
                success=False,
                from_state=from_state,
                to_state=to_state,
                event=context.event,
                error=f"Target state '{to_state}' not found"
            )

        # Exit current state
        if current and transition.transition_type == TransitionType.EXTERNAL:
            await current.exit(context)

        # Execute transition action
        await transition.execute(context)

        # Enter new state
        if target and to_state != from_state:
            self._current_state = to_state
            await target.enter(context)

        # Record history
        history_entry = StateHistory(
            from_state=from_state,
            to_state=to_state,
            event=context.event,
            data=context.data
        )
        self.history.append(history_entry)
        self.state_history[from_state] = from_state

        self.transition_count += 1

        # Notify callbacks
        for callback in self.on_transition_callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback(history_entry)
            else:
                callback(history_entry)

        return TransitionResult(
            success=True,
            from_state=from_state,
            to_state=to_state,
            event=context.event
        )

    def can_trigger(self, event: str) -> bool:
        """Check if event can be triggered."""
        return len(self._find_transitions(event)) > 0

    def get_available_events(self) -> List[str]:
        """Get list of events that can be triggered."""
        available = []

        for event, transitions in self.transitions.items():
            for transition in transitions:
                if transition.from_state in (self._current_state, '*'):
                    available.append(event)
                    break

        return available

    def get_history(self, limit: int = 100) -> List[StateHistory]:
        """Get transition history."""
        return list(self.history)[-limit:]

    def reset(self) -> None:
        """Reset to initial state."""
        self._current_state = self.initial_state
        self.history.clear()
        self.context_data.clear()

    def set_data(self, key: str, value: Any) -> None:
        """Set context data."""
        self.context_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get context data."""
        return self.context_data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state machine."""
        return {
            "name": self.name,
            "machine_id": self.machine_id,
            "current_state": self._current_state,
            "initial_state": self.initial_state,
            "context_data": self.context_data,
            "states": list(self.states.keys()),
            "transition_count": self.transition_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FSMachine':
        """Deserialize state machine."""
        machine = cls(data["name"], data.get("initial_state"))
        machine.machine_id = data.get("machine_id", str(uuid.uuid4()))
        machine._current_state = data.get("current_state")
        machine.context_data = data.get("context_data", {})
        return machine


# =============================================================================
# HIERARCHICAL STATE MACHINE
# =============================================================================

class HierarchicalFSM(FSMachine):
    """
    State machine with hierarchical (nested) states.
    """

    def add_child_state(
        self,
        parent_name: str,
        child_name: str,
        is_initial: bool = False
    ) -> State:
        """Add a child state."""
        parent = self.states.get(parent_name)
        if not parent:
            raise ValueError(f"Parent state '{parent_name}' not found")

        child = State(child_name, parent=parent)
        parent.add_substate(child)
        self.states[child_name] = child

        if is_initial:
            parent.initial_substate = child_name

        return child

    async def _execute_transition(
        self,
        transition: Transition,
        context: StateContext
    ) -> TransitionResult:
        """Execute hierarchical transition."""
        from_state = self.states.get(self._current_state)
        to_state = self.states.get(transition.to_state)

        if not to_state:
            return TransitionResult(
                success=False,
                from_state=self._current_state,
                to_state=transition.to_state,
                event=context.event,
                error=f"Target state '{transition.to_state}' not found"
            )

        # Find common ancestor
        from_path = from_state.get_path() if from_state else []
        to_path = to_state.get_path()

        common_ancestor = None
        for s1, s2 in zip(from_path, to_path):
            if s1 == s2:
                common_ancestor = s1
            else:
                break

        # Exit states up to common ancestor
        if from_state:
            for state in reversed(from_path):
                if state == common_ancestor:
                    break
                await state.exit(context)

        # Execute action
        await transition.execute(context)

        # Enter states from common ancestor
        entering = False
        for state in to_path:
            if state == common_ancestor:
                entering = True
                continue
            if entering:
                await state.enter(context)

        # Update current state
        prev_state = self._current_state
        self._current_state = transition.to_state

        # Record history
        history_entry = StateHistory(
            from_state=prev_state,
            to_state=transition.to_state,
            event=context.event
        )
        self.history.append(history_entry)
        self.transition_count += 1

        return TransitionResult(
            success=True,
            from_state=prev_state,
            to_state=transition.to_state,
            event=context.event
        )


# =============================================================================
# STATE MACHINE BUILDER
# =============================================================================

class FSMBuilder:
    """
    Fluent builder for state machines.
    """

    def __init__(self, name: str):
        self.name = name
        self._states: List[Tuple[str, StateType, bool]] = []
        self._transitions: List[Tuple[str, str, str, Optional[Callable], Optional[Callable]]] = []
        self._hierarchical = False
        self._child_states: List[Tuple[str, str, bool]] = []

    def state(
        self,
        name: str,
        state_type: StateType = StateType.NORMAL,
        is_initial: bool = False
    ) -> 'FSMBuilder':
        """Add a state."""
        self._states.append((name, state_type, is_initial))
        return self

    def initial_state(self, name: str) -> 'FSMBuilder':
        """Add initial state."""
        self._states.append((name, StateType.INITIAL, True))
        return self

    def final_state(self, name: str) -> 'FSMBuilder':
        """Add final state."""
        self._states.append((name, StateType.FINAL, False))
        return self

    def transition(
        self,
        from_state: str,
        to_state: str,
        event: str,
        guard: Callable = None,
        action: Callable = None
    ) -> 'FSMBuilder':
        """Add a transition."""
        self._transitions.append((from_state, to_state, event, guard, action))
        return self

    def child_state(
        self,
        parent: str,
        child: str,
        is_initial: bool = False
    ) -> 'FSMBuilder':
        """Add hierarchical child state."""
        self._hierarchical = True
        self._child_states.append((parent, child, is_initial))
        return self

    def build(self) -> FSMachine:
        """Build the state machine."""
        if self._hierarchical:
            machine = HierarchicalFSM(self.name)
        else:
            machine = FSMachine(self.name)

        # Add states
        for name, state_type, is_initial in self._states:
            machine.add_state(name, state_type, is_initial)

        # Add child states
        if self._hierarchical:
            for parent, child, is_initial in self._child_states:
                machine.add_child_state(parent, child, is_initial)

        # Add transitions
        for from_state, to_state, event, guard, action in self._transitions:
            transition = machine.add_transition(from_state, to_state, event)
            if guard:
                transition.guard(guard)
            if action:
                transition.action(action)

        return machine


# =============================================================================
# STATE MACHINE MANAGER
# =============================================================================

class StateMachineManager:
    """
    Master state machine manager for BAEL.

    Manages multiple state machines and provides lifecycle control.
    """

    def __init__(self):
        self.machines: Dict[str, FSMachine] = {}
        self.templates: Dict[str, Callable[[], FSMachine]] = {}
        self.total_transitions = 0

    def create(
        self,
        name: str,
        initial_state: str = None
    ) -> FSMachine:
        """Create a new state machine."""
        machine = FSMachine(name, initial_state)
        self.machines[machine.machine_id] = machine
        return machine

    def create_hierarchical(
        self,
        name: str,
        initial_state: str = None
    ) -> HierarchicalFSM:
        """Create hierarchical state machine."""
        machine = HierarchicalFSM(name, initial_state)
        self.machines[machine.machine_id] = machine
        return machine

    def builder(self, name: str) -> FSMBuilder:
        """Get fluent builder."""
        return FSMBuilder(name)

    def register_template(
        self,
        name: str,
        factory: Callable[[], FSMachine]
    ) -> None:
        """Register a state machine template."""
        self.templates[name] = factory

    def create_from_template(self, template_name: str) -> Optional[FSMachine]:
        """Create machine from template."""
        factory = self.templates.get(template_name)
        if factory:
            machine = factory()
            self.machines[machine.machine_id] = machine
            return machine
        return None

    def get(self, machine_id: str) -> Optional[FSMachine]:
        """Get state machine by ID."""
        return self.machines.get(machine_id)

    def remove(self, machine_id: str) -> bool:
        """Remove a state machine."""
        if machine_id in self.machines:
            del self.machines[machine_id]
            return True
        return False

    async def trigger(
        self,
        machine_id: str,
        event: str,
        data: Dict[str, Any] = None
    ) -> TransitionResult:
        """Trigger event on specific machine."""
        machine = self.machines.get(machine_id)
        if not machine:
            return TransitionResult(
                success=False,
                from_state="",
                to_state=None,
                event=event,
                error=f"Machine '{machine_id}' not found"
            )

        result = await machine.trigger(event, data)
        if result.success:
            self.total_transitions += 1
        return result

    async def broadcast(
        self,
        event: str,
        data: Dict[str, Any] = None
    ) -> Dict[str, TransitionResult]:
        """Broadcast event to all machines."""
        results = {}

        for machine_id, machine in self.machines.items():
            if machine.can_trigger(event):
                result = await machine.trigger(event, data)
                results[machine_id] = result

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "machine_count": len(self.machines),
            "template_count": len(self.templates),
            "total_transitions": self.total_transitions,
            "machines": {
                mid: {
                    "name": m.name,
                    "current_state": m.current_state,
                    "transitions": m.transition_count
                }
                for mid, m in self.machines.items()
            }
        }

    def export_all(self) -> Dict[str, Dict]:
        """Export all machines."""
        return {
            mid: machine.to_dict()
            for mid, machine in self.machines.items()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the State Machine Engine."""
    print("=" * 70)
    print("BAEL - STATE MACHINE ENGINE DEMO")
    print("Finite State Machine Framework")
    print("=" * 70)
    print()

    manager = StateMachineManager()

    # 1. Basic State Machine
    print("1. BASIC STATE MACHINE:")
    print("-" * 40)

    traffic_light = manager.create("TrafficLight")

    traffic_light.add_state("red", is_initial=True)
    traffic_light.add_state("green")
    traffic_light.add_state("yellow")

    traffic_light.add_transition("red", "green", "timer")
    traffic_light.add_transition("green", "yellow", "timer")
    traffic_light.add_transition("yellow", "red", "timer")

    await traffic_light.start()
    print(f"   Initial state: {traffic_light.current_state}")

    result = await traffic_light.trigger("timer")
    print(f"   After timer: {traffic_light.current_state}")

    result = await traffic_light.trigger("timer")
    print(f"   After timer: {traffic_light.current_state}")

    result = await traffic_light.trigger("timer")
    print(f"   After timer: {traffic_light.current_state}")
    print()

    # 2. State Callbacks
    print("2. STATE CALLBACKS:")
    print("-" * 40)

    door = manager.create("Door", "closed")

    closed_state = door.add_state("closed", is_initial=True)
    open_state = door.add_state("open")
    locked_state = door.add_state("locked")

    callback_log: List[str] = []

    @closed_state.on_enter
    def on_closed_enter(ctx):
        callback_log.append("Entered closed state")

    @closed_state.on_exit
    def on_closed_exit(ctx):
        callback_log.append("Exited closed state")

    @open_state.on_enter
    def on_open_enter(ctx):
        callback_log.append("Entered open state")

    door.add_transition("closed", "open", "open")
    door.add_transition("open", "closed", "close")
    door.add_transition("closed", "locked", "lock")
    door.add_transition("locked", "closed", "unlock")

    await door.start()
    await door.trigger("open")
    await door.trigger("close")

    print(f"   Callbacks triggered:")
    for log in callback_log:
        print(f"     - {log}")
    print()

    # 3. Guard Conditions
    print("3. GUARD CONDITIONS:")
    print("-" * 40)

    vending = manager.create("VendingMachine", "idle")

    vending.add_state("idle", is_initial=True)
    vending.add_state("has_money")
    vending.add_state("dispensing")

    vending.set_data("balance", 0)

    # Transition with guard
    insert_coin = vending.add_transition("idle", "has_money", "insert_coin")
    insert_coin.action(lambda ctx: vending.set_data(
        "balance", vending.get_data("balance", 0) + ctx.data.get("amount", 0)
    ))

    select_item = vending.add_transition("has_money", "dispensing", "select_item")
    select_item.guard(lambda ctx: vending.get_data("balance", 0) >= ctx.data.get("price", 100))

    vending.add_transition("dispensing", "idle", "complete")

    await vending.start()
    print(f"   Initial state: {vending.current_state}")

    await vending.trigger("insert_coin", {"amount": 50})
    print(f"   After inserting 50: balance = {vending.get_data('balance')}")
    print(f"   State: {vending.current_state}")

    result = await vending.trigger("select_item", {"price": 100})
    print(f"   Select item (price=100): success = {result.success}")
    print(f"   Error: {result.error}")

    await vending.trigger("insert_coin", {"amount": 50})
    result = await vending.trigger("select_item", {"price": 100})
    print(f"   After adding more: success = {result.success}")
    print(f"   State: {vending.current_state}")
    print()

    # 4. Builder Pattern
    print("4. BUILDER PATTERN:")
    print("-" * 40)

    order_machine = (
        manager.builder("OrderStateMachine")
        .initial_state("created")
        .state("confirmed")
        .state("shipped")
        .state("delivered", StateType.FINAL)
        .state("cancelled", StateType.FINAL)
        .transition("created", "confirmed", "confirm")
        .transition("confirmed", "shipped", "ship")
        .transition("shipped", "delivered", "deliver")
        .transition("created", "cancelled", "cancel")
        .transition("confirmed", "cancelled", "cancel")
        .build()
    )

    await order_machine.start()
    print(f"   Order state: {order_machine.current_state}")

    await order_machine.trigger("confirm")
    print(f"   After confirm: {order_machine.current_state}")

    await order_machine.trigger("ship")
    print(f"   After ship: {order_machine.current_state}")

    await order_machine.trigger("deliver")
    print(f"   After deliver: {order_machine.current_state}")
    print()

    # 5. Event History
    print("5. EVENT HISTORY:")
    print("-" * 40)

    history = order_machine.get_history()
    for h in history:
        print(f"   {h.from_state} --[{h.event}]--> {h.to_state}")
    print()

    # 6. Available Events
    print("6. AVAILABLE EVENTS:")
    print("-" * 40)

    door.reset()
    await door.start()

    available = door.get_available_events()
    print(f"   Current state: {door.current_state}")
    print(f"   Available events: {available}")

    await door.trigger("open")
    available = door.get_available_events()
    print(f"   After open - Available: {available}")
    print()

    # 7. Hierarchical States
    print("7. HIERARCHICAL STATES:")
    print("-" * 40)

    game = manager.create_hierarchical("GameMachine", "menu")

    game.add_state("menu", is_initial=True)
    game.add_state("playing")
    game.add_state("paused")

    # Add child states for playing
    game.add_child_state("playing", "exploring", is_initial=True)
    game.add_child_state("playing", "combat")
    game.add_child_state("playing", "dialogue")

    game.add_transition("menu", "playing", "start_game")
    game.add_transition("playing", "menu", "quit")
    game.add_transition("playing", "paused", "pause")
    game.add_transition("paused", "playing", "resume")

    game.add_transition("exploring", "combat", "enemy_found")
    game.add_transition("combat", "exploring", "enemy_defeated")
    game.add_transition("exploring", "dialogue", "npc_interact")
    game.add_transition("dialogue", "exploring", "dialogue_end")

    await game.start()
    print(f"   Initial: {game.current_state}")

    await game.trigger("start_game")
    print(f"   After start: {game.current_state}")

    await game.trigger("enemy_found")
    print(f"   Enemy found: {game.current_state}")

    await game.trigger("enemy_defeated")
    print(f"   Enemy defeated: {game.current_state}")
    print()

    # 8. Templates
    print("8. STATE MACHINE TEMPLATES:")
    print("-" * 40)

    def create_workflow():
        return (
            FSMBuilder("Workflow")
            .initial_state("draft")
            .state("pending")
            .state("approved")
            .state("rejected")
            .transition("draft", "pending", "submit")
            .transition("pending", "approved", "approve")
            .transition("pending", "rejected", "reject")
            .transition("rejected", "draft", "revise")
            .build()
        )

    manager.register_template("workflow", create_workflow)

    workflow1 = manager.create_from_template("workflow")
    workflow2 = manager.create_from_template("workflow")

    await workflow1.start()
    await workflow2.start()

    await workflow1.trigger("submit")
    await workflow1.trigger("approve")

    await workflow2.trigger("submit")
    await workflow2.trigger("reject")

    print(f"   Workflow 1: {workflow1.current_state}")
    print(f"   Workflow 2: {workflow2.current_state}")
    print()

    # 9. Broadcast Events
    print("9. BROADCAST EVENTS:")
    print("-" * 40)

    # Reset workflow2 to draft
    workflow2.reset()
    await workflow2.start()

    # Broadcast submit to all workflows
    results = await manager.broadcast("submit")

    print(f"   Broadcast 'submit' results:")
    for mid, result in results.items():
        machine = manager.get(mid)
        if machine and machine.name == "Workflow":
            print(f"     {machine.name}: {result.success} -> {machine.current_state}")
    print()

    # 10. Statistics
    print("10. MANAGER STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"    Machines: {stats['machine_count']}")
    print(f"    Templates: {stats['template_count']}")
    print(f"    Total transitions: {stats['total_transitions']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - State Machine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
