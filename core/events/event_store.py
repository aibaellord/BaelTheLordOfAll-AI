#!/usr/bin/env python3
"""
BAEL - Event Store
Comprehensive event sourcing storage system.

This module provides a complete event store for
persisting and replaying domain events.

Features:
- Event persistence
- Event streams
- Snapshots
- Event replay
- Stream projections
- Optimistic concurrency
- Event subscriptions
- Aggregate reconstruction
- Event versioning
- Full audit trail
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
E = TypeVar('E', bound='Event')


# =============================================================================
# ENUMS
# =============================================================================

class EventType(Enum):
    """Event types."""
    DOMAIN = "domain"
    SYSTEM = "system"
    INTEGRATION = "integration"


class StreamPosition(Enum):
    """Stream position markers."""
    START = "start"
    END = "end"


class SubscriptionPosition(Enum):
    """Subscription starting position."""
    BEGINNING = "beginning"
    END = "end"
    POSITION = "position"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class EventMetadata:
    """Event metadata."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    version: int = 1
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "user_id": self.user_id,
            "version": self.version,
            "custom": self.custom
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventMetadata':
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            user_id=data.get("user_id"),
            version=data.get("version", 1),
            custom=data.get("custom", {})
        )


@dataclass
class Event:
    """Base event class."""
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: EventMetadata = field(default_factory=EventMetadata)
    stream_id: Optional[str] = None
    position: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "metadata": self.metadata.to_dict(),
            "stream_id": self.stream_id,
            "position": self.position
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        return cls(
            event_type=data.get("event_type", ""),
            data=data.get("data", {}),
            metadata=EventMetadata.from_dict(data.get("metadata", {})),
            stream_id=data.get("stream_id"),
            position=data.get("position", 0)
        )


@dataclass
class StoredEvent:
    """Event as stored in the event store."""
    global_position: int
    stream_id: str
    stream_position: int
    event_type: str
    data: bytes
    metadata: bytes
    timestamp: float = field(default_factory=time.time)

    def to_event(self) -> Event:
        """Convert to Event."""
        return Event(
            event_type=self.event_type,
            data=json.loads(self.data.decode()),
            metadata=EventMetadata.from_dict(json.loads(self.metadata.decode())),
            stream_id=self.stream_id,
            position=self.stream_position
        )


@dataclass
class Snapshot:
    """Aggregate snapshot."""
    stream_id: str
    position: int
    state: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class StreamInfo:
    """Information about a stream."""
    stream_id: str
    created_at: float
    last_event_at: float
    event_count: int
    last_position: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubscriptionInfo:
    """Subscription information."""
    subscription_id: str
    stream_pattern: str
    position: int
    created_at: float = field(default_factory=time.time)
    last_processed_at: Optional[float] = None


# =============================================================================
# EVENT STREAM
# =============================================================================

class EventStream:
    """
    An event stream for a specific aggregate.
    """

    def __init__(self, stream_id: str):
        self.stream_id = stream_id
        self.events: List[StoredEvent] = []
        self.version = -1
        self.created_at = time.time()
        self.last_event_at = time.time()
        self.metadata: Dict[str, Any] = {}

    def append(self, event: StoredEvent) -> None:
        """Append event to stream."""
        self.events.append(event)
        self.version = event.stream_position
        self.last_event_at = event.timestamp

    def read(
        self,
        start: int = 0,
        count: int = None
    ) -> List[StoredEvent]:
        """Read events from stream."""
        events = self.events[start:]
        if count is not None:
            events = events[:count]
        return events

    def get_info(self) -> StreamInfo:
        """Get stream info."""
        return StreamInfo(
            stream_id=self.stream_id,
            created_at=self.created_at,
            last_event_at=self.last_event_at,
            event_count=len(self.events),
            last_position=self.version,
            metadata=self.metadata
        )


# =============================================================================
# EVENT STORE BACKEND
# =============================================================================

class EventStoreBackend(ABC):
    """Abstract event store backend."""

    @abstractmethod
    async def append(
        self,
        stream_id: str,
        events: List[Event],
        expected_version: int = -1
    ) -> List[StoredEvent]:
        pass

    @abstractmethod
    async def read_stream(
        self,
        stream_id: str,
        start: int = 0,
        count: int = None
    ) -> List[StoredEvent]:
        pass

    @abstractmethod
    async def read_all(
        self,
        start: int = 0,
        count: int = None
    ) -> List[StoredEvent]:
        pass

    @abstractmethod
    async def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        pass

    @abstractmethod
    async def save_snapshot(self, snapshot: Snapshot) -> None:
        pass

    @abstractmethod
    async def get_snapshot(self, stream_id: str) -> Optional[Snapshot]:
        pass


class InMemoryEventStoreBackend(EventStoreBackend):
    """In-memory event store implementation."""

    def __init__(self):
        self.streams: Dict[str, EventStream] = {}
        self.all_events: List[StoredEvent] = []
        self.snapshots: Dict[str, Snapshot] = {}
        self.global_position = 0
        self._lock = asyncio.Lock()

    async def append(
        self,
        stream_id: str,
        events: List[Event],
        expected_version: int = -1
    ) -> List[StoredEvent]:
        async with self._lock:
            # Get or create stream
            if stream_id not in self.streams:
                self.streams[stream_id] = EventStream(stream_id)

            stream = self.streams[stream_id]

            # Optimistic concurrency check
            if expected_version >= 0 and stream.version != expected_version:
                raise ConcurrencyError(
                    f"Expected version {expected_version}, "
                    f"but stream is at version {stream.version}"
                )

            stored_events = []

            for event in events:
                stream_position = stream.version + 1
                self.global_position += 1

                stored = StoredEvent(
                    global_position=self.global_position,
                    stream_id=stream_id,
                    stream_position=stream_position,
                    event_type=event.event_type,
                    data=json.dumps(event.data).encode(),
                    metadata=json.dumps(event.metadata.to_dict()).encode(),
                    timestamp=event.metadata.timestamp
                )

                stream.append(stored)
                self.all_events.append(stored)
                stored_events.append(stored)

            return stored_events

    async def read_stream(
        self,
        stream_id: str,
        start: int = 0,
        count: int = None
    ) -> List[StoredEvent]:
        stream = self.streams.get(stream_id)
        if not stream:
            return []

        return stream.read(start, count)

    async def read_all(
        self,
        start: int = 0,
        count: int = None
    ) -> List[StoredEvent]:
        events = [e for e in self.all_events if e.global_position >= start]
        if count is not None:
            events = events[:count]
        return events

    async def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        stream = self.streams.get(stream_id)
        if not stream:
            return None
        return stream.get_info()

    async def save_snapshot(self, snapshot: Snapshot) -> None:
        self.snapshots[snapshot.stream_id] = snapshot

    async def get_snapshot(self, stream_id: str) -> Optional[Snapshot]:
        return self.snapshots.get(stream_id)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class EventStoreError(Exception):
    """Base event store error."""
    pass


class ConcurrencyError(EventStoreError):
    """Concurrency conflict error."""
    pass


class StreamNotFoundError(EventStoreError):
    """Stream not found error."""
    pass


# =============================================================================
# EVENT STORE
# =============================================================================

class EventStore:
    """
    Core event store.
    """

    def __init__(self, backend: EventStoreBackend = None):
        self.backend = backend or InMemoryEventStoreBackend()

        # Subscriptions
        self.subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self.catch_up_subscriptions: Dict[str, SubscriptionInfo] = {}

        # Statistics
        self.stats = {
            "events_appended": 0,
            "events_read": 0,
            "snapshots_saved": 0,
            "snapshots_loaded": 0
        }

    async def append_to_stream(
        self,
        stream_id: str,
        events: List[Event],
        expected_version: int = -1
    ) -> List[StoredEvent]:
        """Append events to a stream."""
        stored = await self.backend.append(stream_id, events, expected_version)

        self.stats["events_appended"] += len(stored)

        # Notify subscribers
        await self._notify_subscribers(stored)

        return stored

    async def append_event(
        self,
        stream_id: str,
        event_type: str,
        data: Dict[str, Any],
        metadata: EventMetadata = None,
        expected_version: int = -1
    ) -> StoredEvent:
        """Append a single event."""
        event = Event(
            event_type=event_type,
            data=data,
            metadata=metadata or EventMetadata()
        )

        stored = await self.append_to_stream(stream_id, [event], expected_version)
        return stored[0]

    async def read_stream(
        self,
        stream_id: str,
        start: int = 0,
        count: int = None
    ) -> List[Event]:
        """Read events from a stream."""
        stored = await self.backend.read_stream(stream_id, start, count)

        self.stats["events_read"] += len(stored)

        return [s.to_event() for s in stored]

    async def read_stream_backwards(
        self,
        stream_id: str,
        count: int = None
    ) -> List[Event]:
        """Read events from stream in reverse order."""
        stored = await self.backend.read_stream(stream_id)
        stored = list(reversed(stored))

        if count is not None:
            stored = stored[:count]

        return [s.to_event() for s in stored]

    async def read_all_events(
        self,
        start: int = 0,
        count: int = None
    ) -> List[Event]:
        """Read all events across all streams."""
        stored = await self.backend.read_all(start, count)

        self.stats["events_read"] += len(stored)

        return [s.to_event() for s in stored]

    async def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        """Get stream information."""
        return await self.backend.get_stream_info(stream_id)

    async def stream_exists(self, stream_id: str) -> bool:
        """Check if stream exists."""
        info = await self.get_stream_info(stream_id)
        return info is not None

    async def get_stream_version(self, stream_id: str) -> int:
        """Get current stream version."""
        info = await self.get_stream_info(stream_id)
        return info.last_position if info else -1

    # =========================================================================
    # SNAPSHOTS
    # =========================================================================

    async def save_snapshot(
        self,
        stream_id: str,
        state: Dict[str, Any],
        position: int
    ) -> None:
        """Save aggregate snapshot."""
        snapshot = Snapshot(
            stream_id=stream_id,
            position=position,
            state=state
        )

        await self.backend.save_snapshot(snapshot)
        self.stats["snapshots_saved"] += 1

    async def get_snapshot(self, stream_id: str) -> Optional[Snapshot]:
        """Get latest snapshot for stream."""
        snapshot = await self.backend.get_snapshot(stream_id)

        if snapshot:
            self.stats["snapshots_loaded"] += 1

        return snapshot

    async def load_aggregate(
        self,
        stream_id: str,
        apply_event: Callable[[Dict[str, Any], Event], Dict[str, Any]],
        initial_state: Dict[str, Any] = None
    ) -> Tuple[Dict[str, Any], int]:
        """Load aggregate state by replaying events."""
        state = initial_state or {}
        position = -1

        # Try to load from snapshot
        snapshot = await self.get_snapshot(stream_id)
        if snapshot:
            state = snapshot.state.copy()
            position = snapshot.position

        # Apply events after snapshot
        events = await self.read_stream(stream_id, start=position + 1)

        for event in events:
            state = apply_event(state, event)
            position = event.position

        return state, position

    # =========================================================================
    # SUBSCRIPTIONS
    # =========================================================================

    def subscribe(
        self,
        stream_pattern: str,
        handler: Callable[[Event], Awaitable[None]]
    ) -> str:
        """Subscribe to events."""
        subscription_id = str(uuid.uuid4())
        self.subscriptions[stream_pattern].append(handler)
        return subscription_id

    def subscribe_to_all(
        self,
        handler: Callable[[Event], Awaitable[None]]
    ) -> str:
        """Subscribe to all events."""
        return self.subscribe("*", handler)

    async def _notify_subscribers(self, events: List[StoredEvent]) -> None:
        """Notify subscribers of new events."""
        for stored in events:
            event = stored.to_event()

            # Notify stream-specific subscribers
            for handler in self.subscriptions.get(stored.stream_id, []):
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Subscription handler error: {e}")

            # Notify all-events subscribers
            for handler in self.subscriptions.get("*", []):
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Subscription handler error: {e}")

    async def create_catch_up_subscription(
        self,
        stream_id: str,
        handler: Callable[[Event], Awaitable[None]],
        start_position: int = 0
    ) -> str:
        """Create catch-up subscription that replays history."""
        subscription_id = str(uuid.uuid4())

        info = SubscriptionInfo(
            subscription_id=subscription_id,
            stream_pattern=stream_id,
            position=start_position
        )

        self.catch_up_subscriptions[subscription_id] = info

        # Replay historical events
        events = await self.read_stream(stream_id, start=start_position)

        for event in events:
            try:
                await handler(event)
                info.position = event.position
                info.last_processed_at = time.time()
            except Exception as e:
                logger.error(f"Catch-up subscription error: {e}")
                break

        # Subscribe to new events
        self.subscriptions[stream_id].append(handler)

        return subscription_id

    # =========================================================================
    # PROJECTIONS
    # =========================================================================

    async def project(
        self,
        stream_id: str,
        reducer: Callable[[Any, Event], Any],
        initial: Any = None
    ) -> Any:
        """Create a projection from stream events."""
        events = await self.read_stream(stream_id)

        result = initial
        for event in events:
            result = reducer(result, event)

        return result

    async def project_all(
        self,
        reducer: Callable[[Any, Event], Any],
        initial: Any = None,
        event_types: List[str] = None
    ) -> Any:
        """Create a projection from all events."""
        events = await self.read_all_events()

        if event_types:
            events = [e for e in events if e.event_type in event_types]

        result = initial
        for event in events:
            result = reducer(result, event)

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get event store statistics."""
        return self.stats.copy()


# =============================================================================
# AGGREGATE BASE
# =============================================================================

class AggregateRoot(ABC):
    """Base class for event-sourced aggregates."""

    def __init__(self, aggregate_id: str):
        self.aggregate_id = aggregate_id
        self._version = -1
        self._pending_events: List[Event] = []

    @property
    def version(self) -> int:
        return self._version

    @property
    def pending_events(self) -> List[Event]:
        return self._pending_events

    def clear_pending_events(self) -> List[Event]:
        """Clear and return pending events."""
        events = self._pending_events
        self._pending_events = []
        return events

    def apply_event(self, event: Event) -> None:
        """Apply an event to update state."""
        handler_name = f"_apply_{event.event_type}"
        handler = getattr(self, handler_name, None)

        if handler:
            handler(event.data)

        self._version = event.position

    def raise_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        metadata: EventMetadata = None
    ) -> None:
        """Raise a new domain event."""
        event = Event(
            event_type=event_type,
            data=data,
            metadata=metadata or EventMetadata(),
            stream_id=self.aggregate_id,
            position=self._version + len(self._pending_events) + 1
        )

        # Apply event to update state
        self.apply_event(event)

        # Store as pending
        self._pending_events.append(event)

    @classmethod
    def from_events(cls, aggregate_id: str, events: List[Event]) -> 'AggregateRoot':
        """Reconstruct aggregate from events."""
        aggregate = cls(aggregate_id)

        for event in events:
            aggregate.apply_event(event)

        return aggregate


# =============================================================================
# REPOSITORY
# =============================================================================

class EventSourcedRepository(Generic[T]):
    """Repository for event-sourced aggregates."""

    def __init__(
        self,
        store: EventStore,
        aggregate_class: Type[T]
    ):
        self.store = store
        self.aggregate_class = aggregate_class
        self.snapshot_frequency = 100  # Snapshot every 100 events

    async def get(self, aggregate_id: str) -> Optional[T]:
        """Get aggregate by ID."""
        events = await self.store.read_stream(aggregate_id)

        if not events:
            return None

        return self.aggregate_class.from_events(aggregate_id, events)

    async def save(self, aggregate: T) -> None:
        """Save aggregate changes."""
        pending = aggregate.clear_pending_events()

        if not pending:
            return

        expected_version = aggregate.version - len(pending)

        await self.store.append_to_stream(
            aggregate.aggregate_id,
            pending,
            expected_version
        )

        # Auto-snapshot
        if aggregate.version % self.snapshot_frequency == 0:
            await self._save_snapshot(aggregate)

    async def _save_snapshot(self, aggregate: T) -> None:
        """Save aggregate snapshot."""
        state = aggregate.__dict__.copy()

        # Remove internal fields
        state.pop('_pending_events', None)

        await self.store.save_snapshot(
            aggregate.aggregate_id,
            state,
            aggregate.version
        )


# =============================================================================
# EVENT STORE MANAGER
# =============================================================================

class EventStoreManager:
    """
    Master event store manager for BAEL.
    """

    def __init__(self, backend: EventStoreBackend = None):
        self.store = EventStore(backend)

    async def append(
        self,
        stream_id: str,
        event_type: str,
        data: Dict[str, Any],
        metadata: EventMetadata = None,
        expected_version: int = -1
    ) -> StoredEvent:
        """Append event to stream."""
        return await self.store.append_event(
            stream_id,
            event_type,
            data,
            metadata,
            expected_version
        )

    async def read(
        self,
        stream_id: str,
        start: int = 0,
        count: int = None
    ) -> List[Event]:
        """Read events from stream."""
        return await self.store.read_stream(stream_id, start, count)

    async def read_all(
        self,
        start: int = 0,
        count: int = None
    ) -> List[Event]:
        """Read all events."""
        return await self.store.read_all_events(start, count)

    def subscribe(
        self,
        stream_id: str,
        handler: Callable[[Event], Awaitable[None]]
    ) -> str:
        """Subscribe to stream events."""
        return self.store.subscribe(stream_id, handler)

    def subscribe_all(
        self,
        handler: Callable[[Event], Awaitable[None]]
    ) -> str:
        """Subscribe to all events."""
        return self.store.subscribe_to_all(handler)

    async def project(
        self,
        stream_id: str,
        reducer: Callable[[Any, Event], Any],
        initial: Any = None
    ) -> Any:
        """Create projection."""
        return await self.store.project(stream_id, reducer, initial)

    def create_repository(
        self,
        aggregate_class: Type[T]
    ) -> EventSourcedRepository[T]:
        """Create repository for aggregate."""
        return EventSourcedRepository(self.store, aggregate_class)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return self.store.get_statistics()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Event Store."""
    print("=" * 70)
    print("BAEL - EVENT STORE DEMO")
    print("Event Sourcing Storage System")
    print("=" * 70)
    print()

    manager = EventStoreManager()

    # 1. Append Events
    print("1. APPEND EVENTS:")
    print("-" * 40)

    await manager.append(
        "order-123",
        "OrderCreated",
        {"customer_id": "cust-1", "items": ["item-1", "item-2"]}
    )
    print("   ✓ OrderCreated event appended")

    await manager.append(
        "order-123",
        "OrderItemAdded",
        {"item_id": "item-3", "quantity": 2}
    )
    print("   ✓ OrderItemAdded event appended")

    await manager.append(
        "order-123",
        "OrderConfirmed",
        {"confirmed_at": time.time()}
    )
    print("   ✓ OrderConfirmed event appended")
    print()

    # 2. Read Stream
    print("2. READ STREAM:")
    print("-" * 40)

    events = await manager.read("order-123")
    print(f"   Found {len(events)} events:")
    for event in events:
        print(f"     [{event.position}] {event.event_type}")
    print()

    # 3. Multiple Streams
    print("3. MULTIPLE STREAMS:")
    print("-" * 40)

    await manager.append("user-1", "UserRegistered", {"email": "user1@example.com"})
    await manager.append("user-2", "UserRegistered", {"email": "user2@example.com"})
    await manager.append("user-1", "UserProfileUpdated", {"name": "John Doe"})

    user1_events = await manager.read("user-1")
    user2_events = await manager.read("user-2")

    print(f"   user-1 events: {len(user1_events)}")
    print(f"   user-2 events: {len(user2_events)}")
    print()

    # 4. Read All Events
    print("4. READ ALL EVENTS:")
    print("-" * 40)

    all_events = await manager.read_all()
    print(f"   Total events in store: {len(all_events)}")

    by_type = defaultdict(int)
    for event in all_events:
        by_type[event.event_type] += 1

    print("   By type:")
    for event_type, count in by_type.items():
        print(f"     {event_type}: {count}")
    print()

    # 5. Subscriptions
    print("5. SUBSCRIPTIONS:")
    print("-" * 40)

    received_events = []

    async def event_handler(event: Event):
        received_events.append(event)
        print(f"   Received: {event.event_type} on {event.stream_id}")

    manager.subscribe_all(event_handler)

    await manager.append("order-124", "OrderCreated", {"customer_id": "cust-2"})
    await manager.append("order-124", "OrderShipped", {"tracking": "TRACK123"})

    print(f"   Handler received {len(received_events)} events")
    print()

    # 6. Projections
    print("6. PROJECTIONS:")
    print("-" * 40)

    def order_projection(state: dict, event: Event) -> dict:
        if state is None:
            state = {"items": [], "status": "unknown"}

        if event.event_type == "OrderCreated":
            state["items"] = event.data.get("items", [])
            state["status"] = "created"
        elif event.event_type == "OrderItemAdded":
            state["items"].append(event.data.get("item_id"))
        elif event.event_type == "OrderConfirmed":
            state["status"] = "confirmed"

        return state

    order_state = await manager.project("order-123", order_projection, None)
    print(f"   Order state: {order_state}")
    print()

    # 7. Event Metadata
    print("7. EVENT METADATA:")
    print("-" * 40)

    metadata = EventMetadata(
        correlation_id="request-123",
        causation_id="command-456",
        user_id="admin"
    )

    await manager.append(
        "order-125",
        "OrderCreated",
        {"customer_id": "cust-3"},
        metadata
    )

    events = await manager.read("order-125")
    meta = events[0].metadata
    print(f"   Correlation ID: {meta.correlation_id}")
    print(f"   Causation ID: {meta.causation_id}")
    print(f"   User ID: {meta.user_id}")
    print()

    # 8. Aggregate Example
    print("8. AGGREGATE EXAMPLE:")
    print("-" * 40)

    class BankAccount(AggregateRoot):
        def __init__(self, account_id: str):
            super().__init__(account_id)
            self.balance = 0
            self.owner = None

        def open(self, owner: str, initial_deposit: float):
            self.raise_event("AccountOpened", {
                "owner": owner,
                "initial_deposit": initial_deposit
            })

        def deposit(self, amount: float):
            self.raise_event("MoneyDeposited", {"amount": amount})

        def withdraw(self, amount: float):
            if amount > self.balance:
                raise ValueError("Insufficient funds")
            self.raise_event("MoneyWithdrawn", {"amount": amount})

        def _apply_AccountOpened(self, data: dict):
            self.owner = data["owner"]
            self.balance = data["initial_deposit"]

        def _apply_MoneyDeposited(self, data: dict):
            self.balance += data["amount"]

        def _apply_MoneyWithdrawn(self, data: dict):
            self.balance -= data["amount"]

    # Create and use aggregate
    account = BankAccount("account-001")
    account.open("Alice", 100.0)
    account.deposit(50.0)
    account.withdraw(30.0)

    print(f"   Balance: ${account.balance}")
    print(f"   Pending events: {len(account.pending_events)}")

    # Save events
    events = account.clear_pending_events()
    for event in events:
        await manager.append(
            account.aggregate_id,
            event.event_type,
            event.data
        )

    print("   Events saved to store")

    # Reconstruct from events
    stored_events = await manager.read("account-001")
    reconstructed = BankAccount.from_events("account-001", stored_events)
    print(f"   Reconstructed balance: ${reconstructed.balance}")
    print()

    # 9. Optimistic Concurrency
    print("9. OPTIMISTIC CONCURRENCY:")
    print("-" * 40)

    await manager.append(
        "concurrent-stream",
        "FirstEvent",
        {},
        expected_version=-1
    )

    # This should fail due to version mismatch
    try:
        await manager.append(
            "concurrent-stream",
            "ConflictEvent",
            {},
            expected_version=-1  # Wrong version
        )
        print("   No conflict (unexpected)")
    except ConcurrencyError as e:
        print(f"   ✓ Concurrency error caught: {e}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"    Events appended: {stats['events_appended']}")
    print(f"    Events read: {stats['events_read']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Event Store Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
