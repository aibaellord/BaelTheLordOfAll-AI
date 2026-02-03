"""
BAEL - State Machine Engine
Powerful state machine for agent behavior and workflow management.

Features:
- Hierarchical state machines
- Guard conditions
- Actions and side effects
- History states
- Parallel regions
- Event queue
- State persistence
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class StateType(Enum):
    """Types of states."""
    SIMPLE = "simple"
    COMPOSITE = "composite"
    PARALLEL = "parallel"
    INITIAL = "initial"
    FINAL = "final"
    HISTORY = "history"
    DEEP_HISTORY = "deep_history"


class TransitionType(Enum):
    """Types of transitions."""
    EXTERNAL = "external"   # Exits and re-enters states
    INTERNAL = "internal"   # Stays in current state
    LOCAL = "local"         # Doesn't exit composite state


class EventType(Enum):
    """Types of events."""
    SIGNAL = "signal"       # Named event
    CHANGE = "change"       # Condition change
    TIME = "time"           # After delay
    COMPLETION = "completion"  # State completed


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Event:
    """An event that triggers transitions."""
    name: str
    type: EventType = EventType.SIGNAL
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def signal(cls, name: str, **data) -> "Event":
        return cls(name=name, type=EventType.SIGNAL, data=data)

    @classmethod
    def after(cls, delay_ms: int) -> "Event":
        return cls(name=f"after_{delay_ms}ms", type=EventType.TIME, data={"delay": delay_ms})


@dataclass
class StateContext:
    """Context passed through state machine."""
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, **kwargs) -> None:
        self.data.update(kwargs)


# =============================================================================
# STATE
# =============================================================================

class State:
    """A state in the state machine."""

    def __init__(
        self,
        name: str,
        state_type: StateType = StateType.SIMPLE,
        parent: Optional["State"] = None
    ):
        self.name = name
        self.type = state_type
        self.parent = parent
        self.children: Dict[str, "State"] = {}
        self.initial_state: Optional[str] = None

        # Callbacks
        self._on_enter: Optional[Callable] = None
        self._on_exit: Optional[Callable] = None
        self._on_update: Optional[Callable] = None

        # Activities
        self._activities: List[Callable] = []

        # History
        self._history_state: Optional[str] = None

    @property
    def full_name(self) -> str:
        """Get fully qualified state name."""
        if self.parent:
            return f"{self.parent.full_name}.{self.name}"
        return self.name

    def on_enter(self, handler: Callable) -> "State":
        """Set enter handler."""
        self._on_enter = handler
        return self

    def on_exit(self, handler: Callable) -> "State":
        """Set exit handler."""
        self._on_exit = handler
        return self

    def on_update(self, handler: Callable) -> "State":
        """Set update handler."""
        self._on_update = handler
        return self

    def add_activity(self, activity: Callable) -> "State":
        """Add an activity (runs while in state)."""
        self._activities.append(activity)
        return self

    def add_child(self, child: "State") -> "State":
        """Add a child state."""
        child.parent = self
        self.children[child.name] = child

        if self.type == StateType.SIMPLE:
            self.type = StateType.COMPOSITE

        return self

    def set_initial(self, state_name: str) -> "State":
        """Set initial child state."""
        self.initial_state = state_name
        return self

    async def enter(self, context: StateContext, event: Optional[Event] = None) -> None:
        """Execute enter actions."""
        logger.debug(f"Entering state: {self.full_name}")
        context.history.append(f"enter:{self.full_name}")

        if self._on_enter:
            if asyncio.iscoroutinefunction(self._on_enter):
                await self._on_enter(context, event)
            else:
                self._on_enter(context, event)

    async def exit(self, context: StateContext, event: Optional[Event] = None) -> None:
        """Execute exit actions."""
        logger.debug(f"Exiting state: {self.full_name}")
        context.history.append(f"exit:{self.full_name}")

        if self._on_exit:
            if asyncio.iscoroutinefunction(self._on_exit):
                await self._on_exit(context, event)
            else:
                self._on_exit(context, event)

    async def update(self, context: StateContext) -> None:
        """Execute update logic."""
        if self._on_update:
            if asyncio.iscoroutinefunction(self._on_update):
                await self._on_update(context)
            else:
                self._on_update(context)

    def get_child(self, name: str) -> Optional["State"]:
        """Get a child state by name."""
        return self.children.get(name)

    def get_descendant(self, path: str) -> Optional["State"]:
        """Get a descendant state by path (e.g., 'child.grandchild')."""
        parts = path.split(".")
        current = self

        for part in parts:
            current = current.children.get(part)
            if current is None:
                return None

        return current


# =============================================================================
# TRANSITION
# =============================================================================

@dataclass
class Transition:
    """A transition between states."""
    source: str
    target: str
    event: Optional[str] = None
    guard: Optional[Callable[[StateContext, Event], bool]] = None
    action: Optional[Callable[[StateContext, Event], None]] = None
    type: TransitionType = TransitionType.EXTERNAL

    async def can_fire(self, context: StateContext, event: Event) -> bool:
        """Check if transition can fire."""
        # Check event match
        if self.event and event.name != self.event:
            return False

        # Check guard
        if self.guard:
            if asyncio.iscoroutinefunction(self.guard):
                return await self.guard(context, event)
            return self.guard(context, event)

        return True

    async def execute(self, context: StateContext, event: Event) -> None:
        """Execute transition action."""
        if self.action:
            if asyncio.iscoroutinefunction(self.action):
                await self.action(context, event)
            else:
                self.action(context, event)


# =============================================================================
# STATE MACHINE
# =============================================================================

class StateMachine:
    """Hierarchical finite state machine."""

    def __init__(self, name: str):
        self.name = name
        self.root = State(name, StateType.COMPOSITE)
        self.current_states: Set[str] = set()
        self.transitions: List[Transition] = []
        self.context = StateContext()

        self._event_queue: deque = deque()
        self._running = False
        self._history: Dict[str, str] = {}  # composite_state -> last_active_state

    def add_state(self, name: str, parent: Optional[str] = None) -> State:
        """Add a state to the machine."""
        state = State(name)

        if parent:
            parent_state = self.get_state(parent)
            if parent_state:
                parent_state.add_child(state)
        else:
            self.root.add_child(state)

        return state

    def add_transition(
        self,
        source: str,
        target: str,
        event: Optional[str] = None,
        guard: Optional[Callable] = None,
        action: Optional[Callable] = None,
        transition_type: TransitionType = TransitionType.EXTERNAL
    ) -> Transition:
        """Add a transition."""
        transition = Transition(
            source=source,
            target=target,
            event=event,
            guard=guard,
            action=action,
            type=transition_type
        )
        self.transitions.append(transition)
        return transition

    def get_state(self, name: str) -> Optional[State]:
        """Get a state by name or path."""
        if name == self.root.name:
            return self.root

        # Try direct child
        state = self.root.children.get(name)
        if state:
            return state

        # Try path
        return self.root.get_descendant(name)

    def set_initial(self, state_name: str) -> None:
        """Set the initial state."""
        self.root.initial_state = state_name

    async def start(self) -> None:
        """Start the state machine."""
        self._running = True

        # Enter initial state
        if self.root.initial_state:
            initial = self.get_state(self.root.initial_state)
            if initial:
                await self._enter_state(initial, None)

    async def stop(self) -> None:
        """Stop the state machine."""
        self._running = False

        # Exit all current states
        for state_name in list(self.current_states):
            state = self.get_state(state_name)
            if state:
                await self._exit_state(state, None)

    def send(self, event: Union[str, Event]) -> None:
        """Queue an event for processing."""
        if isinstance(event, str):
            event = Event.signal(event)
        self._event_queue.append(event)

    async def process(self) -> None:
        """Process queued events."""
        while self._event_queue and self._running:
            event = self._event_queue.popleft()
            await self._handle_event(event)

    async def step(self) -> bool:
        """Process one event."""
        if self._event_queue:
            event = self._event_queue.popleft()
            await self._handle_event(event)
            return True
        return False

    async def _handle_event(self, event: Event) -> None:
        """Handle an event."""
        logger.debug(f"Handling event: {event.name}")

        # Find matching transition from current states
        for state_name in list(self.current_states):
            for transition in self.transitions:
                if transition.source == state_name:
                    if await transition.can_fire(self.context, event):
                        await self._fire_transition(transition, event)
                        return

    async def _fire_transition(self, transition: Transition, event: Event) -> None:
        """Execute a transition."""
        logger.debug(f"Firing transition: {transition.source} -> {transition.target}")

        source = self.get_state(transition.source)
        target = self.get_state(transition.target)

        if not source or not target:
            return

        if transition.type == TransitionType.EXTERNAL:
            # Find common ancestor and exit/enter states
            exit_path = self._get_exit_path(source, target)
            enter_path = self._get_enter_path(source, target)

            for state in exit_path:
                await self._exit_state(state, event)

            # Execute transition action
            await transition.execute(self.context, event)

            for state in enter_path:
                await self._enter_state(state, event)

        elif transition.type == TransitionType.INTERNAL:
            # Just execute action, no state change
            await transition.execute(self.context, event)

    async def _enter_state(self, state: State, event: Optional[Event]) -> None:
        """Enter a state."""
        await state.enter(self.context, event)
        self.current_states.add(state.name)

        # Enter initial child if composite
        if state.type == StateType.COMPOSITE and state.initial_state:
            child = state.get_child(state.initial_state)
            if child:
                await self._enter_state(child, event)

        # Handle history states
        if state.type in [StateType.HISTORY, StateType.DEEP_HISTORY]:
            if state.parent and state.parent.full_name in self._history:
                history_target = self._history[state.parent.full_name]
                history_state = self.get_state(history_target)
                if history_state:
                    await self._enter_state(history_state, event)

    async def _exit_state(self, state: State, event: Optional[Event]) -> None:
        """Exit a state."""
        # Exit children first
        for child in state.children.values():
            if child.name in self.current_states:
                await self._exit_state(child, event)

        # Save history
        if state.parent and state.parent.type == StateType.COMPOSITE:
            self._history[state.parent.full_name] = state.name

        await state.exit(self.context, event)
        self.current_states.discard(state.name)

    def _get_exit_path(self, source: State, target: State) -> List[State]:
        """Get states to exit when transitioning."""
        # Simplified: exit source
        return [source]

    def _get_enter_path(self, source: State, target: State) -> List[State]:
        """Get states to enter when transitioning."""
        # Simplified: enter target
        return [target]

    def is_in_state(self, state_name: str) -> bool:
        """Check if machine is in a state."""
        return state_name in self.current_states

    def get_current_state_names(self) -> List[str]:
        """Get names of current states."""
        return list(self.current_states)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state machine."""
        return {
            "name": self.name,
            "current_states": list(self.current_states),
            "context": self.context.data,
            "history": self._history
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateMachine":
        """Deserialize state machine (partial)."""
        sm = cls(data["name"])
        sm.current_states = set(data["current_states"])
        sm.context.data = data["context"]
        sm._history = data["history"]
        return sm


# =============================================================================
# STATE MACHINE BUILDER
# =============================================================================

class StateMachineBuilder:
    """Fluent builder for state machines."""

    def __init__(self, name: str):
        self.machine = StateMachine(name)
        self._current_state: Optional[str] = None

    def state(self, name: str, parent: Optional[str] = None) -> "StateMachineBuilder":
        """Add a state."""
        self.machine.add_state(name, parent)
        self._current_state = name
        return self

    def initial(self, state_name: str) -> "StateMachineBuilder":
        """Set initial state."""
        self.machine.set_initial(state_name)
        return self

    def on_enter(self, handler: Callable) -> "StateMachineBuilder":
        """Set enter handler for current state."""
        if self._current_state:
            state = self.machine.get_state(self._current_state)
            if state:
                state.on_enter(handler)
        return self

    def on_exit(self, handler: Callable) -> "StateMachineBuilder":
        """Set exit handler for current state."""
        if self._current_state:
            state = self.machine.get_state(self._current_state)
            if state:
                state.on_exit(handler)
        return self

    def transition(
        self,
        source: str,
        target: str,
        event: Optional[str] = None,
        guard: Optional[Callable] = None,
        action: Optional[Callable] = None
    ) -> "StateMachineBuilder":
        """Add a transition."""
        self.machine.add_transition(source, target, event, guard, action)
        return self

    def build(self) -> StateMachine:
        """Build and return the state machine."""
        return self.machine


# =============================================================================
# AGENT BEHAVIOR STATE MACHINE
# =============================================================================

class AgentBehaviorMachine(StateMachine):
    """State machine specialized for agent behaviors."""

    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    DONE = "done"

    def __init__(self, name: str = "agent"):
        super().__init__(name)
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """Set up agent behavior states."""
        # Main states
        idle = self.add_state(self.IDLE)
        idle.on_enter(lambda ctx, e: ctx.set("status", "idle"))

        thinking = self.add_state(self.THINKING)
        thinking.on_enter(lambda ctx, e: ctx.set("status", "thinking"))

        planning = self.add_state(self.PLANNING)
        planning.on_enter(lambda ctx, e: ctx.set("status", "planning"))

        executing = self.add_state(self.EXECUTING)
        executing.on_enter(lambda ctx, e: ctx.set("status", "executing"))

        waiting = self.add_state(self.WAITING)
        waiting.on_enter(lambda ctx, e: ctx.set("status", "waiting"))

        error = self.add_state(self.ERROR)
        error.on_enter(lambda ctx, e: ctx.set("status", "error"))

        done = self.add_state(self.DONE)
        done.on_enter(lambda ctx, e: ctx.set("status", "done"))

        self.set_initial(self.IDLE)

    def _setup_transitions(self) -> None:
        """Set up behavior transitions."""
        # From idle
        self.add_transition(self.IDLE, self.THINKING, "task_received")
        self.add_transition(self.IDLE, self.DONE, "shutdown")

        # From thinking
        self.add_transition(self.THINKING, self.PLANNING, "analysis_complete")
        self.add_transition(self.THINKING, self.ERROR, "error")

        # From planning
        self.add_transition(self.PLANNING, self.EXECUTING, "plan_ready")
        self.add_transition(self.PLANNING, self.THINKING, "need_more_info")
        self.add_transition(self.PLANNING, self.ERROR, "error")

        # From executing
        self.add_transition(self.EXECUTING, self.WAITING, "waiting_for_input")
        self.add_transition(self.EXECUTING, self.IDLE, "task_complete")
        self.add_transition(self.EXECUTING, self.THINKING, "replanning_needed")
        self.add_transition(self.EXECUTING, self.ERROR, "error")

        # From waiting
        self.add_transition(self.WAITING, self.EXECUTING, "input_received")
        self.add_transition(self.WAITING, self.IDLE, "timeout")

        # From error
        self.add_transition(self.ERROR, self.IDLE, "reset")
        self.add_transition(self.ERROR, self.THINKING, "retry")


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_state_machine():
    """Demonstrate state machine capabilities."""

    # Using builder
    machine = (
        StateMachineBuilder("workflow")
        .state("start")
        .on_enter(lambda ctx, e: print("Starting..."))
        .state("processing")
        .on_enter(lambda ctx, e: print("Processing..."))
        .state("complete")
        .on_enter(lambda ctx, e: print("Complete!"))
        .initial("start")
        .transition("start", "processing", "begin")
        .transition("processing", "complete", "done")
        .transition("complete", "start", "restart")
        .build()
    )

    await machine.start()
    print(f"Current: {machine.get_current_state_names()}")

    machine.send("begin")
    await machine.process()
    print(f"Current: {machine.get_current_state_names()}")

    machine.send("done")
    await machine.process()
    print(f"Current: {machine.get_current_state_names()}")

    # Agent behavior machine
    print("\n--- Agent Behavior Machine ---")
    agent = AgentBehaviorMachine()
    await agent.start()
    print(f"Agent state: {agent.context.get('status')}")

    agent.send("task_received")
    await agent.process()
    print(f"Agent state: {agent.context.get('status')}")

    agent.send("analysis_complete")
    await agent.process()
    print(f"Agent state: {agent.context.get('status')}")


if __name__ == "__main__":
    asyncio.run(example_state_machine())
