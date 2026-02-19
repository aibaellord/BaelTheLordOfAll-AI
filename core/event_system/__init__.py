"""
BAEL Event System
=================

Powerful event-driven architecture with pub/sub, event sourcing,
and distributed event handling.

"All actions ripple through Ba'el's consciousness." — Ba'el
"""

from .event_bus import (
    # Enums
    EventPriority,
    EventStatus,
    DeliveryMode,
    SubscriptionType,

    # Data structures
    Event,
    EventHandler,
    Subscription,
    EventFilter,
    EventBusConfig,

    # Classes
    EventBus,
    EventStore,
    EventDispatcher,
    EventRouter,
    EventAggregator,

    # Instance
    event_bus
)

__all__ = [
    # Enums
    "EventPriority",
    "EventStatus",
    "DeliveryMode",
    "SubscriptionType",

    # Data structures
    "Event",
    "EventHandler",
    "Subscription",
    "EventFilter",
    "EventBusConfig",

    # Classes
    "EventBus",
    "EventStore",
    "EventDispatcher",
    "EventRouter",
    "EventAggregator",

    # Instance
    "event_bus"
]
