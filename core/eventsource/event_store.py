#!/usr/bin/env python3
"""
BAEL - Event Store
Event sourcing system for BAEL.

Features:
- Event persistence
- Event replay
- Snapshots
- Aggregates
- Projections
- Subscriptions
- Event versioning
- Stream management
- Optimistic concurrency
- Event metadata
"""

import asyncio
import hashlib
import json
import logging
import pickle
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')
E = TypeVar('E', bound='DomainEvent')
A = TypeVar('A', bound='Aggregate')


# =============================================================================
# ENUMS
# =============================================================================

class EventState(Enum):
    """Event state."""
    PENDING = "pending"
    COMMITTED = "committed"
    ARCHIVED = "archived"


class SnapshotStrategy(Enum):
    """When to create snapshots."""
    NEVER = "never"
    EVERY_N_EVENTS = "every_n_events"
    EVERY_N_SECONDS = "every_n_seconds"
    ON_DEMAND = "on_demand"


class ProjectionState(Enum):
    """Projection state."""
    STOPPED = "stopped"
    RUNNING = "running"
    CATCHING_UP = "catching_up"
    LIVE = "live"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class EventMetadata:
    """Metadata for an event."""
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StoredEvent:
    """Event as stored in the event store."""
    event_id: str
    stream_id: str
    event_type: str
    data: Dict[str, Any]
    metadata: EventMetadata
    version: int
    position: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    state: EventState = EventState.COMMITTED


@dataclass
class StreamInfo:
    """Information about an event stream."""
    stream_id: str
    current_version: int = 0
    event_count: int = 0
    first_event_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Snapshot:
    """Aggregate snapshot."""
    aggregate_id: str
    aggregate_type: str
    version: int
    state: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppendResult:
    """Result of appending events."""
    success: bool
    stream_id: str
    start_version: int
    end_version: int
    events_appended: int
    position: int


# =============================================================================
# DOMAIN EVENT
# =============================================================================

class DomainEvent(ABC):
    """Base class for domain events."""

    def __init__(self):
        self.event_id = str(uuid.uuid4())
        self.occurred_at = datetime.utcnow()
        self._metadata = EventMetadata()

    @property
    def event_type(self) -> str:
        """Get event type name."""
        return self.__class__.__name__

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """Deserialize event from dictionary."""
        pass

    def with_metadata(self, metadata: EventMetadata) -> 'DomainEvent':
        """Set event metadata."""
        self._metadata = metadata
        return self


# =============================================================================
# AGGREGATE
# =============================================================================

class Aggregate(ABC, Generic[E]):
    """Base class for event-sourced aggregates."""

    def __init__(self, aggregate_id: str):
        self.aggregate_id = aggregate_id
        self._version = 0
        self._pending_events: List[DomainEvent] = []

    @property
    def version(self) -> int:
        return self._version

    @property
    def pending_events(self) -> List[DomainEvent]:
        return list(self._pending_events)

    def clear_pending_events(self) -> None:
        """Clear pending events after persistence."""
        self._pending_events.clear()

    def apply_event(self, event: DomainEvent) -> None:
        """Apply event to aggregate state."""
        self._apply(event)
        self._version += 1

    def raise_event(self, event: DomainEvent) -> None:
        """Raise a new domain event."""
        self._apply(event)
        self._pending_events.append(event)
        self._version += 1

    @abstractmethod
    def _apply(self, event: DomainEvent) -> None:
        """Apply event to state (override in subclass)."""
        pass

    @abstractmethod
    def to_snapshot(self) -> Dict[str, Any]:
        """Create snapshot of current state."""
        pass

    @classmethod
    @abstractmethod
    def from_snapshot(cls, aggregate_id: str, state: Dict[str, Any]) -> 'Aggregate':
        """Restore aggregate from snapshot."""
        pass


# =============================================================================
# EVENT REGISTRY
# =============================================================================

class EventRegistry:
    """Registry for event types."""

    def __init__(self):
        self._types: Dict[str, Type[DomainEvent]] = {}
        self._upcasters: Dict[str, List[Callable]] = {}

    def register(self, event_type: Type[DomainEvent]) -> None:
        """Register an event type."""
        self._types[event_type.__name__] = event_type

    def get(self, type_name: str) -> Optional[Type[DomainEvent]]:
        """Get event type by name."""
        return self._types.get(type_name)

    def deserialize(self, type_name: str, data: Dict[str, Any]) -> Optional[DomainEvent]:
        """Deserialize event by type name."""
        event_type = self._types.get(type_name)
        if event_type:
            # Apply upcasters
            data = self._upcast(type_name, data)
            return event_type.from_dict(data)
        return None

    def register_upcaster(
        self,
        type_name: str,
        upcaster: Callable[[Dict], Dict]
    ) -> None:
        """Register an event upcaster."""
        if type_name not in self._upcasters:
            self._upcasters[type_name] = []
        self._upcasters[type_name].append(upcaster)

    def _upcast(self, type_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply upcasters to event data."""
        upcasters = self._upcasters.get(type_name, [])
        for upcaster in upcasters:
            data = upcaster(data)
        return data


# =============================================================================
# EVENT STORE
# =============================================================================

class EventStore:
    """
    Event Store for BAEL.

    Stores and retrieves domain events with support for
    streams, snapshots, and subscriptions.
    """

    def __init__(self, registry: Optional[EventRegistry] = None):
        self._registry = registry or EventRegistry()
        self._events: Dict[str, List[StoredEvent]] = {}  # stream_id -> events
        self._streams: Dict[str, StreamInfo] = {}
        self._snapshots: Dict[str, List[Snapshot]] = {}  # aggregate_id -> snapshots
        self._global_position = 0
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # STREAM MANAGEMENT
    # -------------------------------------------------------------------------

    async def create_stream(
        self,
        stream_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StreamInfo:
        """Create a new event stream."""
        async with self._lock:
            if stream_id in self._streams:
                raise ValueError(f"Stream already exists: {stream_id}")

            info = StreamInfo(
                stream_id=stream_id,
                metadata=metadata or {}
            )

            self._streams[stream_id] = info
            self._events[stream_id] = []

            return info

    async def get_stream(self, stream_id: str) -> Optional[StreamInfo]:
        """Get stream information."""
        return self._streams.get(stream_id)

    async def delete_stream(self, stream_id: str) -> bool:
        """Delete a stream and all its events."""
        async with self._lock:
            if stream_id in self._streams:
                del self._streams[stream_id]
                if stream_id in self._events:
                    del self._events[stream_id]
                return True
            return False

    async def list_streams(self) -> List[StreamInfo]:
        """List all streams."""
        return list(self._streams.values())

    # -------------------------------------------------------------------------
    # EVENT APPENDING
    # -------------------------------------------------------------------------

    async def append(
        self,
        stream_id: str,
        events: List[DomainEvent],
        expected_version: Optional[int] = None
    ) -> AppendResult:
        """Append events to a stream."""
        async with self._lock:
            # Ensure stream exists
            if stream_id not in self._streams:
                await self.create_stream(stream_id)

            stream = self._streams[stream_id]
            stream_events = self._events[stream_id]

            # Optimistic concurrency check
            if expected_version is not None:
                if stream.current_version != expected_version:
                    raise ConcurrencyException(
                        f"Expected version {expected_version}, got {stream.current_version}"
                    )

            start_version = stream.current_version + 1
            stored_events = []

            for i, event in enumerate(events):
                self._global_position += 1
                version = start_version + i

                stored = StoredEvent(
                    event_id=event.event_id,
                    stream_id=stream_id,
                    event_type=event.event_type,
                    data=event.to_dict(),
                    metadata=event._metadata,
                    version=version,
                    position=self._global_position
                )

                stream_events.append(stored)
                stored_events.append(stored)

            # Update stream info
            stream.current_version = start_version + len(events) - 1
            stream.event_count += len(events)
            stream.last_event_at = datetime.utcnow()

            if stream.first_event_at is None:
                stream.first_event_at = stream.last_event_at

            # Notify subscribers
            await self._notify_subscribers(stream_id, stored_events)

            return AppendResult(
                success=True,
                stream_id=stream_id,
                start_version=start_version,
                end_version=stream.current_version,
                events_appended=len(events),
                position=self._global_position
            )

    async def append_aggregate_events(
        self,
        aggregate: Aggregate
    ) -> AppendResult:
        """Append pending events from aggregate."""
        events = aggregate.pending_events
        if not events:
            return AppendResult(
                success=True,
                stream_id=aggregate.aggregate_id,
                start_version=aggregate.version,
                end_version=aggregate.version,
                events_appended=0,
                position=self._global_position
            )

        expected_version = aggregate.version - len(events)
        result = await self.append(aggregate.aggregate_id, events, expected_version)

        if result.success:
            aggregate.clear_pending_events()

        return result

    # -------------------------------------------------------------------------
    # EVENT READING
    # -------------------------------------------------------------------------

    async def read_stream(
        self,
        stream_id: str,
        start_version: int = 1,
        count: Optional[int] = None,
        direction: str = "forward"
    ) -> List[StoredEvent]:
        """Read events from a stream."""
        if stream_id not in self._events:
            return []

        events = self._events[stream_id]

        # Filter by version
        filtered = [e for e in events if e.version >= start_version]

        if direction == "backward":
            filtered = list(reversed(filtered))

        if count:
            filtered = filtered[:count]

        return filtered

    async def read_all(
        self,
        from_position: int = 0,
        count: Optional[int] = None
    ) -> List[StoredEvent]:
        """Read all events across all streams."""
        all_events = []

        for stream_events in self._events.values():
            for event in stream_events:
                if event.position > from_position:
                    all_events.append(event)

        # Sort by position
        all_events.sort(key=lambda e: e.position)

        if count:
            all_events = all_events[:count]

        return all_events

    async def get_event(
        self,
        stream_id: str,
        version: int
    ) -> Optional[StoredEvent]:
        """Get a specific event by version."""
        if stream_id not in self._events:
            return None

        for event in self._events[stream_id]:
            if event.version == version:
                return event

        return None

    # -------------------------------------------------------------------------
    # AGGREGATE LOADING
    # -------------------------------------------------------------------------

    async def load_aggregate(
        self,
        aggregate_type: Type[A],
        aggregate_id: str
    ) -> Optional[A]:
        """Load aggregate from events."""
        # Try to load from snapshot first
        snapshot = await self._get_latest_snapshot(aggregate_id)

        if snapshot:
            aggregate = aggregate_type.from_snapshot(aggregate_id, snapshot.state)
            aggregate._version = snapshot.version
            start_version = snapshot.version + 1
        else:
            # No snapshot, start from beginning
            events = await self.read_stream(aggregate_id)
            if not events:
                return None

            # Create aggregate and apply first event
            aggregate = aggregate_type(aggregate_id)
            start_version = 1

        # Apply events since snapshot
        events = await self.read_stream(aggregate_id, start_version)

        for stored in events:
            domain_event = self._registry.deserialize(stored.event_type, stored.data)
            if domain_event:
                aggregate.apply_event(domain_event)

        return aggregate

    # -------------------------------------------------------------------------
    # SNAPSHOTS
    # -------------------------------------------------------------------------

    async def save_snapshot(
        self,
        aggregate: Aggregate,
        aggregate_type_name: str
    ) -> Snapshot:
        """Save aggregate snapshot."""
        async with self._lock:
            snapshot = Snapshot(
                aggregate_id=aggregate.aggregate_id,
                aggregate_type=aggregate_type_name,
                version=aggregate.version,
                state=aggregate.to_snapshot()
            )

            if aggregate.aggregate_id not in self._snapshots:
                self._snapshots[aggregate.aggregate_id] = []

            self._snapshots[aggregate.aggregate_id].append(snapshot)

            return snapshot

    async def _get_latest_snapshot(
        self,
        aggregate_id: str
    ) -> Optional[Snapshot]:
        """Get latest snapshot for aggregate."""
        snapshots = self._snapshots.get(aggregate_id, [])
        if snapshots:
            return max(snapshots, key=lambda s: s.version)
        return None

    async def delete_old_snapshots(
        self,
        aggregate_id: str,
        keep_count: int = 1
    ) -> int:
        """Delete old snapshots, keeping the latest N."""
        if aggregate_id not in self._snapshots:
            return 0

        snapshots = self._snapshots[aggregate_id]
        if len(snapshots) <= keep_count:
            return 0

        # Sort by version, keep latest
        snapshots.sort(key=lambda s: s.version, reverse=True)
        to_keep = snapshots[:keep_count]
        deleted = len(snapshots) - keep_count

        self._snapshots[aggregate_id] = to_keep

        return deleted

    # -------------------------------------------------------------------------
    # SUBSCRIPTIONS
    # -------------------------------------------------------------------------

    async def subscribe(
        self,
        stream_id: str,
        callback: Callable[[StoredEvent], Awaitable[None]]
    ) -> str:
        """Subscribe to stream events."""
        sub_id = str(uuid.uuid4())

        if stream_id not in self._subscriptions:
            self._subscriptions[stream_id] = []

        self._subscriptions[stream_id].append((sub_id, callback))

        return sub_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        for stream_id, subs in self._subscriptions.items():
            for i, (sub_id, _) in enumerate(subs):
                if sub_id == subscription_id:
                    del subs[i]
                    return True
        return False

    async def _notify_subscribers(
        self,
        stream_id: str,
        events: List[StoredEvent]
    ) -> None:
        """Notify subscribers of new events."""
        # Stream-specific subscribers
        subs = self._subscriptions.get(stream_id, [])

        for event in events:
            for _, callback in subs:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Subscription callback error: {e}")

        # All-stream subscribers
        all_subs = self._subscriptions.get("*", [])
        for event in events:
            for _, callback in all_subs:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Subscription callback error: {e}")

    # -------------------------------------------------------------------------
    # PROJECTIONS
    # -------------------------------------------------------------------------

    def get_registry(self) -> EventRegistry:
        """Get the event registry."""
        return self._registry

    def get_global_position(self) -> int:
        """Get current global position."""
        return self._global_position


# =============================================================================
# PROJECTIONS
# =============================================================================

class Projection(ABC, Generic[T]):
    """Base class for event projections."""

    def __init__(self):
        self.state: T = self._initial_state()
        self.last_position: int = 0
        self._handlers: Dict[str, Callable] = {}
        self._setup_handlers()

    @abstractmethod
    def _initial_state(self) -> T:
        """Return initial projection state."""
        pass

    def _setup_handlers(self) -> None:
        """Setup event handlers (override in subclass)."""
        pass

    def handles(self, event_type: str) -> Callable:
        """Decorator to register event handler."""
        def decorator(func):
            self._handlers[event_type] = func
            return func
        return decorator

    async def apply(self, event: StoredEvent) -> None:
        """Apply event to projection."""
        handler = self._handlers.get(event.event_type)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                await handler(event, self.state)
            else:
                handler(event, self.state)

        self.last_position = event.position

    async def rebuild(self, events: List[StoredEvent]) -> None:
        """Rebuild projection from events."""
        self.state = self._initial_state()
        self.last_position = 0

        for event in events:
            await self.apply(event)


class ProjectionManager:
    """Manages projections."""

    def __init__(self, event_store: EventStore):
        self._store = event_store
        self._projections: Dict[str, Projection] = {}
        self._running: Set[str] = set()

    def register(self, name: str, projection: Projection) -> None:
        """Register a projection."""
        self._projections[name] = projection

    def get(self, name: str) -> Optional[Projection]:
        """Get projection by name."""
        return self._projections.get(name)

    async def catch_up(self, name: str) -> None:
        """Catch up projection to current events."""
        projection = self._projections.get(name)
        if not projection:
            return

        events = await self._store.read_all(projection.last_position)

        for event in events:
            await projection.apply(event)

    async def rebuild(self, name: str) -> None:
        """Rebuild projection from scratch."""
        projection = self._projections.get(name)
        if not projection:
            return

        events = await self._store.read_all()
        await projection.rebuild(events)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ConcurrencyException(Exception):
    """Raised on concurrent modification."""
    pass


class EventNotFoundException(Exception):
    """Raised when event not found."""
    pass


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Event Store."""
    print("=" * 70)
    print("BAEL - EVENT STORE DEMO")
    print("Event Sourcing System")
    print("=" * 70)
    print()

    # Create registry and store
    registry = EventRegistry()
    store = EventStore(registry)

    # 1. Define Domain Events
    print("1. DOMAIN EVENT DEFINITION:")
    print("-" * 40)

    class AccountCreated(DomainEvent):
        def __init__(self, account_id: str, owner: str):
            super().__init__()
            self.account_id = account_id
            self.owner = owner

        def to_dict(self) -> Dict[str, Any]:
            return {"account_id": self.account_id, "owner": self.owner}

        @classmethod
        def from_dict(cls, data: Dict) -> 'AccountCreated':
            return cls(data["account_id"], data["owner"])

    class MoneyDeposited(DomainEvent):
        def __init__(self, amount: float):
            super().__init__()
            self.amount = amount

        def to_dict(self) -> Dict:
            return {"amount": self.amount}

        @classmethod
        def from_dict(cls, data: Dict) -> 'MoneyDeposited':
            return cls(data["amount"])

    class MoneyWithdrawn(DomainEvent):
        def __init__(self, amount: float):
            super().__init__()
            self.amount = amount

        def to_dict(self) -> Dict:
            return {"amount": self.amount}

        @classmethod
        def from_dict(cls, data: Dict) -> 'MoneyWithdrawn':
            return cls(data["amount"])

    # Register events
    registry.register(AccountCreated)
    registry.register(MoneyDeposited)
    registry.register(MoneyWithdrawn)

    print("   Registered events: AccountCreated, MoneyDeposited, MoneyWithdrawn")
    print()

    # 2. Define Aggregate
    print("2. AGGREGATE DEFINITION:")
    print("-" * 40)

    class BankAccount(Aggregate):
        def __init__(self, account_id: str):
            super().__init__(account_id)
            self.owner: str = ""
            self.balance: float = 0.0

        def create(self, owner: str) -> None:
            self.raise_event(AccountCreated(self.aggregate_id, owner))

        def deposit(self, amount: float) -> None:
            if amount <= 0:
                raise ValueError("Amount must be positive")
            self.raise_event(MoneyDeposited(amount))

        def withdraw(self, amount: float) -> None:
            if amount > self.balance:
                raise ValueError("Insufficient funds")
            self.raise_event(MoneyWithdrawn(amount))

        def _apply(self, event: DomainEvent) -> None:
            if isinstance(event, AccountCreated):
                self.owner = event.owner
            elif isinstance(event, MoneyDeposited):
                self.balance += event.amount
            elif isinstance(event, MoneyWithdrawn):
                self.balance -= event.amount

        def to_snapshot(self) -> Dict:
            return {"owner": self.owner, "balance": self.balance}

        @classmethod
        def from_snapshot(cls, aggregate_id: str, state: Dict) -> 'BankAccount':
            account = cls(aggregate_id)
            account.owner = state["owner"]
            account.balance = state["balance"]
            return account

    print("   BankAccount aggregate defined with create, deposit, withdraw")
    print()

    # 3. Append Events
    print("3. APPEND EVENTS:")
    print("-" * 40)

    account = BankAccount("ACC-001")
    account.create("John Doe")
    account.deposit(100.0)
    account.deposit(50.0)
    account.withdraw(30.0)

    print(f"   Pending events: {len(account.pending_events)}")
    print(f"   Current balance: ${account.balance:.2f}")

    result = await store.append_aggregate_events(account)

    print(f"   Appended {result.events_appended} events")
    print(f"   Stream version: {result.end_version}")
    print()

    # 4. Read Events
    print("4. READ EVENTS:")
    print("-" * 40)

    events = await store.read_stream("ACC-001")

    for event in events:
        print(f"   v{event.version}: {event.event_type} - {event.data}")
    print()

    # 5. Load Aggregate
    print("5. LOAD AGGREGATE FROM EVENTS:")
    print("-" * 40)

    loaded_account = await store.load_aggregate(BankAccount, "ACC-001")

    if loaded_account:
        print(f"   Owner: {loaded_account.owner}")
        print(f"   Balance: ${loaded_account.balance:.2f}")
        print(f"   Version: {loaded_account.version}")
    print()

    # 6. Snapshots
    print("6. SNAPSHOTS:")
    print("-" * 40)

    snapshot = await store.save_snapshot(loaded_account, "BankAccount")

    print(f"   Snapshot saved at version: {snapshot.version}")
    print(f"   State: {snapshot.state}")

    # Add more events
    loaded_account.deposit(200.0)
    await store.append_aggregate_events(loaded_account)

    # Load again (uses snapshot)
    reloaded = await store.load_aggregate(BankAccount, "ACC-001")

    if reloaded:
        print(f"   After reload: Balance = ${reloaded.balance:.2f}")
    print()

    # 7. Optimistic Concurrency
    print("7. OPTIMISTIC CONCURRENCY:")
    print("-" * 40)

    try:
        # Try to append with wrong expected version
        event = MoneyDeposited(100.0)
        await store.append("ACC-001", [event], expected_version=1)
        print("   Should have raised exception!")
    except ConcurrencyException as e:
        print(f"   Caught concurrency exception: {e}")
    print()

    # 8. Subscriptions
    print("8. EVENT SUBSCRIPTIONS:")
    print("-" * 40)

    received_events = []

    async def on_event(event: StoredEvent):
        received_events.append(event.event_type)

    sub_id = await store.subscribe("ACC-002", on_event)

    # Create new account
    account2 = BankAccount("ACC-002")
    account2.create("Jane Doe")
    account2.deposit(500.0)

    await store.append_aggregate_events(account2)

    print(f"   Subscription ID: {sub_id[:8]}...")
    print(f"   Received events: {received_events}")
    print()

    # 9. Projections
    print("9. PROJECTIONS:")
    print("-" * 40)

    class AccountBalanceProjection(Projection[Dict[str, float]]):
        def _initial_state(self) -> Dict[str, float]:
            return {}

        def _setup_handlers(self):
            self._handlers["AccountCreated"] = self._on_created
            self._handlers["MoneyDeposited"] = self._on_deposited
            self._handlers["MoneyWithdrawn"] = self._on_withdrawn

        def _on_created(self, event: StoredEvent, state: Dict):
            state[event.stream_id] = 0.0

        def _on_deposited(self, event: StoredEvent, state: Dict):
            if event.stream_id in state:
                state[event.stream_id] += event.data["amount"]

        def _on_withdrawn(self, event: StoredEvent, state: Dict):
            if event.stream_id in state:
                state[event.stream_id] -= event.data["amount"]

    projection = AccountBalanceProjection()

    manager = ProjectionManager(store)
    manager.register("balances", projection)

    await manager.rebuild("balances")

    print(f"   Projection state: {projection.state}")
    print(f"   Last position: {projection.last_position}")
    print()

    # 10. Stream Management
    print("10. STREAM MANAGEMENT:")
    print("-" * 40)

    streams = await store.list_streams()

    for stream in streams:
        print(f"   Stream: {stream.stream_id}")
        print(f"     Events: {stream.event_count}")
        print(f"     Version: {stream.current_version}")
    print()

    # 11. Read All Events
    print("11. READ ALL EVENTS (global):")
    print("-" * 40)

    all_events = await store.read_all()

    print(f"   Total events in store: {len(all_events)}")
    print(f"   Global position: {store.get_global_position()}")

    for event in all_events[:5]:
        print(f"   [{event.position}] {event.stream_id}: {event.event_type}")
    print()

    # 12. Event Upcasting
    print("12. EVENT UPCASTING:")
    print("-" * 40)

    def upgrade_v1_to_v2(data: Dict) -> Dict:
        """Add new field to old events."""
        if "currency" not in data:
            data["currency"] = "USD"
        return data

    registry.register_upcaster("MoneyDeposited", upgrade_v1_to_v2)

    # Deserialize old event
    old_data = {"amount": 100.0}
    upgraded = registry.deserialize("MoneyDeposited", old_data)

    print(f"   Original data: {old_data}")
    print(f"   After upcasting: currency field added")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Event Store Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
