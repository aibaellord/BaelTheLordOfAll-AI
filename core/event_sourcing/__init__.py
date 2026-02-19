"""
BAEL Event Sourcing Engine
==========================

Event sourcing for complete audit trails and state reconstruction.

"Ba'el remembers every moment in time." — Ba'el
"""

from .event_sourcing_engine import (
    # Enums
    EventType,
    AggregateState,

    # Data structures
    Event,
    Snapshot,
    EventStream,
    AggregateRoot,

    # Engine
    EventStore,
    EventSourcingEngine,

    # Convenience
    event_store,
    event_engine,
)

__all__ = [
    'EventType',
    'AggregateState',
    'Event',
    'Snapshot',
    'EventStream',
    'AggregateRoot',
    'EventStore',
    'EventSourcingEngine',
    'event_store',
    'event_engine',
]
