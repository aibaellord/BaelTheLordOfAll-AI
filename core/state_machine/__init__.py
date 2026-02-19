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

from .state_machine_engine import (
    # Enums
    StateType,
    TransitionType,
    EventPriority,
    MachineStatus,

    # Data structures
    State,
    Transition,
    Event,
    StateMachineConfig,
    MachineContext,

    # Classes
    StateMachine,
    StateRegistry,
    EventQueue,
    TransitionHandler,

    # Instance
    state_machine_engine
)

__all__ = [
    'StateType',
    'TransitionType',
    'EventPriority',
    'MachineStatus',
    'State',
    'Transition',
    'Event',
    'StateMachineConfig',
    'MachineContext',
    'StateMachine',
    'StateRegistry',
    'EventQueue',
    'TransitionHandler',
    'state_machine_engine'
]
