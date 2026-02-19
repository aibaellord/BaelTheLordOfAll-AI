"""
BAEL Event Sourcing Engine Implementation
==========================================

Complete event sourcing system for capturing all state changes.

"Ba'el captures the essence of every change in reality." — Ba'el
"""

import asyncio
import hashlib
import json
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.EventSourcing")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class EventType(Enum):
    """Event types."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    COMMAND = "command"
    DOMAIN = "domain"
    INTEGRATION = "integration"
    SYSTEM = "system"


class AggregateState(Enum):
    """Aggregate states."""
    NEW = "new"
    ACTIVE = "active"
    DELETED = "deleted"
    ARCHIVED = "archived"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Event:
    """
    Domain event.

    Captures something that happened in the system.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Type info
    event_type: str = ""
    aggregate_type: str = ""
    aggregate_id: str = ""

    # Data
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Versioning
    version: int = 1
    sequence: int = 0

    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)

    # Causation
    causation_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'aggregate_type': self.aggregate_type,
            'aggregate_id': self.aggregate_id,
            'data': self.data,
            'metadata': self.metadata,
            'version': self.version,
            'sequence': self.sequence,
            'timestamp': self.timestamp.isoformat(),
            'causation_id': self.causation_id,
            'correlation_id': self.correlation_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create from dictionary."""
        data = data.copy()
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

    def hash(self) -> str:
        """Get event hash for integrity."""
        content = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class Snapshot:
    """
    Aggregate snapshot for performance optimization.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Aggregate info
    aggregate_type: str = ""
    aggregate_id: str = ""

    # State
    state: Dict[str, Any] = field(default_factory=dict)
    version: int = 0

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    event_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'aggregate_type': self.aggregate_type,
            'aggregate_id': self.aggregate_id,
            'state': self.state,
            'version': self.version,
            'timestamp': self.timestamp.isoformat(),
            'event_count': self.event_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Snapshot':
        """Create from dictionary."""
        data = data.copy()
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class EventStream:
    """
    Stream of events for an aggregate.
    """
    aggregate_type: str
    aggregate_id: str
    events: List[Event] = field(default_factory=list)
    version: int = 0
    snapshot: Optional[Snapshot] = None

    def append(self, event: Event) -> None:
        """Append event to stream."""
        event.sequence = len(self.events) + 1
        self.events.append(event)
        self.version = event.sequence

    def get_events_since(self, version: int) -> List[Event]:
        """Get events since a version."""
        return [e for e in self.events if e.sequence > version]


# ============================================================================
# AGGREGATE ROOT
# ============================================================================

class AggregateRoot(ABC):
    """
    Base class for aggregate roots.

    Aggregates track uncommitted events and apply them to state.
    """

    def __init__(self, aggregate_id: Optional[str] = None):
        self._id = aggregate_id or str(uuid.uuid4())
        self._version = 0
        self._uncommitted_events: List[Event] = []
        self._state = AggregateState.NEW

    @property
    def id(self) -> str:
        return self._id

    @property
    def version(self) -> int:
        return self._version

    @property
    def state(self) -> AggregateState:
        return self._state

    @property
    def uncommitted_events(self) -> List[Event]:
        return self._uncommitted_events.copy()

    def clear_uncommitted_events(self) -> None:
        """Clear uncommitted events after persistence."""
        self._uncommitted_events.clear()

    def raise_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Raise a new domain event."""
        event = Event(
            event_type=event_type,
            aggregate_type=self.__class__.__name__,
            aggregate_id=self._id,
            data=data,
            version=self._version + 1
        )

        self._apply(event)
        self._uncommitted_events.append(event)

    def load_from_history(self, events: List[Event]) -> None:
        """Rebuild state from event history."""
        for event in events:
            self._apply(event)

    def load_from_snapshot(self, snapshot: Snapshot) -> None:
        """Restore from snapshot."""
        self._restore_state(snapshot.state)
        self._version = snapshot.version
        self._state = AggregateState.ACTIVE

    def _apply(self, event: Event) -> None:
        """Apply an event to the aggregate."""
        self._version = event.version
        self._state = AggregateState.ACTIVE

        # Call specific handler if exists
        handler_name = f'_apply_{event.event_type}'
        handler = getattr(self, handler_name, None)

        if handler:
            handler(event)
        else:
            self._on_event(event)

    @abstractmethod
    def _on_event(self, event: Event) -> None:
        """Default event handler - override in subclass."""
        pass

    def _restore_state(self, state: Dict[str, Any]) -> None:
        """Restore state from snapshot - override for custom restore."""
        for key, value in state.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def _get_state(self) -> Dict[str, Any]:
        """Get current state for snapshot - override for custom state."""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

    def create_snapshot(self) -> Snapshot:
        """Create a snapshot of current state."""
        return Snapshot(
            aggregate_type=self.__class__.__name__,
            aggregate_id=self._id,
            state=self._get_state(),
            version=self._version
        )


# ============================================================================
# EVENT STORE
# ============================================================================

class EventStore:
    """
    Event store for persisting events.

    In-memory implementation - extend for database backing.
    """

    def __init__(self):
        # Streams: (aggregate_type, aggregate_id) -> EventStream
        self._streams: Dict[tuple, EventStream] = {}

        # Snapshots: (aggregate_type, aggregate_id) -> Snapshot
        self._snapshots: Dict[tuple, Snapshot] = {}

        # All events for projections
        self._all_events: List[Event] = []

        # Event handlers
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}

        self._lock = threading.RLock()

        logger.info("Event store initialized")

    def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        events: List[Event],
        expected_version: Optional[int] = None
    ) -> None:
        """
        Append events to stream.

        Args:
            aggregate_type: Type of aggregate
            aggregate_id: Aggregate ID
            events: Events to append
            expected_version: Expected current version (for optimistic locking)
        """
        with self._lock:
            key = (aggregate_type, aggregate_id)

            if key not in self._streams:
                self._streams[key] = EventStream(aggregate_type, aggregate_id)

            stream = self._streams[key]

            # Check version for optimistic concurrency
            if expected_version is not None:
                if stream.version != expected_version:
                    raise ValueError(
                        f"Concurrency conflict: expected {expected_version}, "
                        f"actual {stream.version}"
                    )

            # Append events
            for event in events:
                stream.append(event)
                self._all_events.append(event)

                # Dispatch to handlers
                self._dispatch(event)

        logger.debug(
            f"Appended {len(events)} events to {aggregate_type}/{aggregate_id}"
        )

    def load(
        self,
        aggregate_type: str,
        aggregate_id: str,
        from_version: int = 0
    ) -> List[Event]:
        """Load events for an aggregate."""
        with self._lock:
            key = (aggregate_type, aggregate_id)
            stream = self._streams.get(key)

            if not stream:
                return []

            return stream.get_events_since(from_version)

    def load_stream(
        self,
        aggregate_type: str,
        aggregate_id: str
    ) -> Optional[EventStream]:
        """Load event stream."""
        with self._lock:
            key = (aggregate_type, aggregate_id)
            return self._streams.get(key)

    def save_snapshot(self, snapshot: Snapshot) -> None:
        """Save a snapshot."""
        with self._lock:
            key = (snapshot.aggregate_type, snapshot.aggregate_id)
            self._snapshots[key] = snapshot

        logger.debug(
            f"Saved snapshot for {snapshot.aggregate_type}/{snapshot.aggregate_id}"
        )

    def load_snapshot(
        self,
        aggregate_type: str,
        aggregate_id: str
    ) -> Optional[Snapshot]:
        """Load latest snapshot."""
        with self._lock:
            key = (aggregate_type, aggregate_id)
            return self._snapshots.get(key)

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Event], None]
    ) -> None:
        """Subscribe to event type."""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[[Event], None]
    ) -> None:
        """Unsubscribe from event type."""
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type].remove(handler)

    def _dispatch(self, event: Event) -> None:
        """Dispatch event to handlers."""
        handlers = self._handlers.get(event.event_type, [])
        handlers.extend(self._handlers.get('*', []))  # Wildcard handlers

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def get_all_events(
        self,
        from_sequence: int = 0,
        event_types: Optional[List[str]] = None
    ) -> List[Event]:
        """Get all events for projection rebuilding."""
        with self._lock:
            events = self._all_events[from_sequence:]

            if event_types:
                events = [e for e in events if e.event_type in event_types]

            return events

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        with self._lock:
            return {
                'streams': len(self._streams),
                'total_events': len(self._all_events),
                'snapshots': len(self._snapshots),
                'handlers': sum(len(h) for h in self._handlers.values())
            }


# ============================================================================
# EVENT SOURCING ENGINE
# ============================================================================

class EventSourcingEngine:
    """
    High-level event sourcing engine.

    Features:
    - Aggregate lifecycle management
    - Automatic snapshotting
    - Projections
    - Event replay

    "Ba'el orchestrates the flow of events through time." — Ba'el
    """

    def __init__(
        self,
        store: Optional[EventStore] = None,
        snapshot_frequency: int = 100
    ):
        """
        Initialize engine.

        Args:
            store: Event store instance
            snapshot_frequency: How often to create snapshots
        """
        self.store = store or EventStore()
        self.snapshot_frequency = snapshot_frequency

        # Aggregate registry
        self._aggregate_types: Dict[str, Type[AggregateRoot]] = {}

        # Projections
        self._projections: Dict[str, Callable[[Event], None]] = {}

        self._lock = threading.RLock()

        logger.info("Event Sourcing Engine initialized")

    # ========================================================================
    # AGGREGATE REGISTRATION
    # ========================================================================

    def register_aggregate(self, aggregate_type: Type[AggregateRoot]) -> None:
        """Register an aggregate type."""
        with self._lock:
            self._aggregate_types[aggregate_type.__name__] = aggregate_type

        logger.debug(f"Registered aggregate: {aggregate_type.__name__}")

    # ========================================================================
    # AGGREGATE OPERATIONS
    # ========================================================================

    def create(self, aggregate_type: Type[T], *args, **kwargs) -> T:
        """Create a new aggregate."""
        return aggregate_type(*args, **kwargs)

    def load(
        self,
        aggregate_type: Type[T],
        aggregate_id: str
    ) -> Optional[T]:
        """Load an aggregate from event history."""
        type_name = aggregate_type.__name__

        # Try to load snapshot first
        snapshot = self.store.load_snapshot(type_name, aggregate_id)

        if snapshot:
            aggregate = aggregate_type(aggregate_id)
            aggregate.load_from_snapshot(snapshot)

            # Load events since snapshot
            events = self.store.load(type_name, aggregate_id, snapshot.version)
            aggregate.load_from_history(events)
        else:
            # Load all events
            events = self.store.load(type_name, aggregate_id)

            if not events:
                return None

            aggregate = aggregate_type(aggregate_id)
            aggregate.load_from_history(events)

        return aggregate

    def save(self, aggregate: AggregateRoot) -> None:
        """Save aggregate changes."""
        events = aggregate.uncommitted_events

        if not events:
            return

        # Calculate expected version
        expected_version = aggregate.version - len(events)

        # Append events
        self.store.append(
            aggregate.__class__.__name__,
            aggregate.id,
            events,
            expected_version
        )

        aggregate.clear_uncommitted_events()

        # Check if snapshot needed
        if aggregate.version % self.snapshot_frequency == 0:
            self._create_snapshot(aggregate)

    def _create_snapshot(self, aggregate: AggregateRoot) -> None:
        """Create and save aggregate snapshot."""
        snapshot = aggregate.create_snapshot()
        snapshot.event_count = aggregate.version
        self.store.save_snapshot(snapshot)

    # ========================================================================
    # ASYNC OPERATIONS
    # ========================================================================

    async def load_async(
        self,
        aggregate_type: Type[T],
        aggregate_id: str
    ) -> Optional[T]:
        """Load aggregate asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.load(aggregate_type, aggregate_id)
        )

    async def save_async(self, aggregate: AggregateRoot) -> None:
        """Save aggregate asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.save(aggregate))

    # ========================================================================
    # PROJECTIONS
    # ========================================================================

    def register_projection(
        self,
        name: str,
        handler: Callable[[Event], None],
        event_types: Optional[List[str]] = None
    ) -> None:
        """Register a projection handler."""
        self._projections[name] = handler

        # Subscribe to events
        if event_types:
            for event_type in event_types:
                self.store.subscribe(event_type, handler)
        else:
            self.store.subscribe('*', handler)

        logger.debug(f"Registered projection: {name}")

    def rebuild_projection(
        self,
        name: str,
        event_types: Optional[List[str]] = None
    ) -> None:
        """Rebuild a projection from scratch."""
        handler = self._projections.get(name)

        if not handler:
            raise KeyError(f"Projection not found: {name}")

        events = self.store.get_all_events(event_types=event_types)

        for event in events:
            handler(event)

        logger.info(f"Rebuilt projection {name} with {len(events)} events")

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'store': self.store.get_stats(),
            'aggregates': list(self._aggregate_types.keys()),
            'projections': list(self._projections.keys()),
            'snapshot_frequency': self.snapshot_frequency
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

event_store = EventStore()
event_engine = EventSourcingEngine(event_store)
