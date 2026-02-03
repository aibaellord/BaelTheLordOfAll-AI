#!/usr/bin/env python3
"""
BAEL - Event Bus System
Comprehensive event-driven architecture with pub/sub, event sourcing, and CQRS support.

Features:
- Publish/Subscribe pattern
- Event topics and channels
- Event filtering
- Dead letter handling
- Event replay
- Event persistence
- Priority queues
- Async event processing
- Event correlation
- Saga support
"""

import asyncio
import hashlib
import heapq
import json
import logging
import re
import time
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Pattern, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')
E = TypeVar('E', bound='Event')


# =============================================================================
# ENUMS
# =============================================================================

class EventPriority(Enum):
    """Event priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class EventStatus(Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    RETRY = "retry"


class DeliveryMode(Enum):
    """Event delivery modes."""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class SubscriptionType(Enum):
    """Subscription types."""
    SYNC = "sync"
    ASYNC = "async"
    QUEUE = "queue"
    BROADCAST = "broadcast"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Event:
    """Base event class."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    topic: str = ""
    payload: Any = None
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = ""
    causation_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: 'Event') -> bool:
        # For priority queue ordering
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "topic": self.topic,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=data.get("event_type", ""),
            topic=data.get("topic", ""),
            payload=data.get("payload"),
            priority=EventPriority(data.get("priority", 2)),
            timestamp=data.get("timestamp", time.time()),
            correlation_id=data.get("correlation_id", ""),
            causation_id=data.get("causation_id", ""),
            metadata=data.get("metadata", {})
        )


@dataclass
class Subscription:
    """Event subscription."""
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    event_types: Set[str] = field(default_factory=set)
    handler: Callable[[Event], Awaitable[None]] = None
    filter_fn: Callable[[Event], bool] = None
    subscription_type: SubscriptionType = SubscriptionType.ASYNC
    priority: int = 0
    active: bool = True
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeadLetterEntry:
    """Dead letter queue entry."""
    event: Event
    error: str
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    last_attempt: float = field(default_factory=time.time)


@dataclass
class EventStats:
    """Event bus statistics."""
    total_published: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_retried: int = 0
    dead_letter_count: int = 0
    events_by_topic: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


# =============================================================================
# EVENT HANDLERS
# =============================================================================

class EventHandler(ABC):
    """Abstract event handler."""

    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle an event."""
        pass

    def can_handle(self, event: Event) -> bool:
        """Check if handler can process event."""
        return True


class FunctionEventHandler(EventHandler):
    """Function-based event handler."""

    def __init__(self, func: Callable[[Event], Awaitable[None]]):
        self.func = func

    async def handle(self, event: Event) -> None:
        await self.func(event)


class TypedEventHandler(EventHandler, Generic[E]):
    """Typed event handler for specific event types."""

    def __init__(
        self,
        event_type: str,
        handler: Callable[[E], Awaitable[None]]
    ):
        self.event_type = event_type
        self.handler = handler

    async def handle(self, event: Event) -> None:
        if event.event_type == self.event_type:
            await self.handler(event)

    def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


# =============================================================================
# EVENT FILTERS
# =============================================================================

class EventFilter(ABC):
    """Abstract event filter."""

    @abstractmethod
    def matches(self, event: Event) -> bool:
        """Check if event matches filter."""
        pass


class TopicFilter(EventFilter):
    """Topic-based filter."""

    def __init__(self, pattern: str):
        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace(".", "\\.").replace("*", "[^.]+").replace("#", ".*")
        self.pattern = re.compile(f"^{regex_pattern}$")

    def matches(self, event: Event) -> bool:
        return bool(self.pattern.match(event.topic))


class TypeFilter(EventFilter):
    """Event type filter."""

    def __init__(self, event_types: Set[str]):
        self.event_types = event_types

    def matches(self, event: Event) -> bool:
        return event.event_type in self.event_types


class PayloadFilter(EventFilter):
    """Payload-based filter."""

    def __init__(self, predicate: Callable[[Any], bool]):
        self.predicate = predicate

    def matches(self, event: Event) -> bool:
        return self.predicate(event.payload)


class CompositeFilter(EventFilter):
    """Composite filter with AND/OR logic."""

    def __init__(
        self,
        filters: List[EventFilter],
        match_all: bool = True
    ):
        self.filters = filters
        self.match_all = match_all

    def matches(self, event: Event) -> bool:
        if self.match_all:
            return all(f.matches(event) for f in self.filters)
        return any(f.matches(event) for f in self.filters)


# =============================================================================
# EVENT STORE
# =============================================================================

class EventStore(ABC):
    """Abstract event store."""

    @abstractmethod
    async def append(self, event: Event) -> None:
        """Append event to store."""
        pass

    @abstractmethod
    async def get_events(
        self,
        topic: str = None,
        event_type: str = None,
        after: float = None,
        before: float = None,
        limit: int = 100
    ) -> List[Event]:
        """Get events from store."""
        pass

    @abstractmethod
    async def get_by_correlation(
        self,
        correlation_id: str
    ) -> List[Event]:
        """Get events by correlation ID."""
        pass


class InMemoryEventStore(EventStore):
    """In-memory event store."""

    def __init__(self, max_events: int = 10000):
        self.events: List[Event] = []
        self.max_events = max_events
        self.by_correlation: Dict[str, List[Event]] = defaultdict(list)
        self.by_topic: Dict[str, List[Event]] = defaultdict(list)

    async def append(self, event: Event) -> None:
        self.events.append(event)

        if event.correlation_id:
            self.by_correlation[event.correlation_id].append(event)

        self.by_topic[event.topic].append(event)

        # Trim if needed
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    async def get_events(
        self,
        topic: str = None,
        event_type: str = None,
        after: float = None,
        before: float = None,
        limit: int = 100
    ) -> List[Event]:
        results = self.events

        if topic:
            results = [e for e in results if e.topic == topic]

        if event_type:
            results = [e for e in results if e.event_type == event_type]

        if after:
            results = [e for e in results if e.timestamp > after]

        if before:
            results = [e for e in results if e.timestamp < before]

        return results[-limit:]

    async def get_by_correlation(
        self,
        correlation_id: str
    ) -> List[Event]:
        return self.by_correlation.get(correlation_id, [])


# =============================================================================
# DEAD LETTER QUEUE
# =============================================================================

class DeadLetterQueue:
    """Dead letter queue for failed events."""

    def __init__(self, max_size: int = 1000):
        self.entries: List[DeadLetterEntry] = []
        self.max_size = max_size

    def add(
        self,
        event: Event,
        error: str,
        max_retries: int = 3
    ) -> None:
        entry = DeadLetterEntry(
            event=event,
            error=error,
            max_retries=max_retries
        )

        self.entries.append(entry)

        if len(self.entries) > self.max_size:
            self.entries = self.entries[-self.max_size:]

    def get_retriable(self) -> List[DeadLetterEntry]:
        """Get entries that can be retried."""
        return [
            e for e in self.entries
            if e.retry_count < e.max_retries
        ]

    def retry(self, event_id: str) -> Optional[Event]:
        """Mark entry for retry."""
        for entry in self.entries:
            if entry.event.event_id == event_id:
                if entry.retry_count < entry.max_retries:
                    entry.retry_count += 1
                    entry.last_attempt = time.time()
                    return entry.event
        return None

    def remove(self, event_id: str) -> bool:
        """Remove entry from DLQ."""
        for i, entry in enumerate(self.entries):
            if entry.event.event_id == event_id:
                self.entries.pop(i)
                return True
        return False

    def get_all(self) -> List[DeadLetterEntry]:
        return self.entries.copy()


# =============================================================================
# EVENT CHANNEL
# =============================================================================

class EventChannel:
    """Event channel for topic-based messaging."""

    def __init__(self, name: str):
        self.name = name
        self.subscriptions: List[Subscription] = []
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self._worker_task: Optional[asyncio.Task] = None

    def subscribe(self, subscription: Subscription) -> None:
        """Add subscription to channel."""
        self.subscriptions.append(subscription)
        self.subscriptions.sort(key=lambda s: s.priority)

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove subscription."""
        for i, sub in enumerate(self.subscriptions):
            if sub.subscription_id == subscription_id:
                self.subscriptions.pop(i)
                return True
        return False

    async def publish(self, event: Event) -> None:
        """Publish event to channel."""
        await self.queue.put(event)

    async def start(self) -> None:
        """Start channel worker."""
        if self.running:
            return

        self.running = True
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        """Stop channel worker."""
        self.running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def _worker(self) -> None:
        """Process events from queue."""
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                await self._dispatch(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.exception(f"Channel worker error: {e}")

    async def _dispatch(self, event: Event) -> None:
        """Dispatch event to subscribers."""
        tasks = []

        for sub in self.subscriptions:
            if not sub.active:
                continue

            # Check event type filter
            if sub.event_types and event.event_type not in sub.event_types:
                continue

            # Check custom filter
            if sub.filter_fn and not sub.filter_fn(event):
                continue

            if sub.handler:
                tasks.append(sub.handler(event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# =============================================================================
# EVENT BUS
# =============================================================================

class EventBus:
    """
    Comprehensive Event Bus for BAEL.
    """

    def __init__(
        self,
        event_store: EventStore = None,
        delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE
    ):
        self.channels: Dict[str, EventChannel] = {}
        self.global_subscriptions: List[Subscription] = []
        self.event_store = event_store or InMemoryEventStore()
        self.dead_letter_queue = DeadLetterQueue()
        self.delivery_mode = delivery_mode
        self.stats = EventStats()
        self._running = False
        self._priority_queue: List[Event] = []
        self._interceptors: List[Callable[[Event], Awaitable[Optional[Event]]]] = []

    # -------------------------------------------------------------------------
    # CHANNEL MANAGEMENT
    # -------------------------------------------------------------------------

    def create_channel(self, name: str) -> EventChannel:
        """Create a new event channel."""
        if name not in self.channels:
            self.channels[name] = EventChannel(name)
        return self.channels[name]

    def get_channel(self, name: str) -> Optional[EventChannel]:
        """Get channel by name."""
        return self.channels.get(name)

    def delete_channel(self, name: str) -> bool:
        """Delete a channel."""
        if name in self.channels:
            del self.channels[name]
            return True
        return False

    # -------------------------------------------------------------------------
    # SUBSCRIPTIONS
    # -------------------------------------------------------------------------

    def subscribe(
        self,
        topic: str,
        handler: Callable[[Event], Awaitable[None]],
        event_types: Set[str] = None,
        filter_fn: Callable[[Event], bool] = None,
        priority: int = 0
    ) -> str:
        """Subscribe to events on a topic."""
        subscription = Subscription(
            topic=topic,
            handler=handler,
            event_types=event_types or set(),
            filter_fn=filter_fn,
            priority=priority
        )

        # Match topic to channel
        matched = False
        for channel_name, channel in self.channels.items():
            if self._topic_matches(topic, channel_name):
                channel.subscribe(subscription)
                matched = True

        # Also add to global subscriptions for wildcard matching
        self.global_subscriptions.append(subscription)

        return subscription.subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        # Remove from channels
        for channel in self.channels.values():
            channel.unsubscribe(subscription_id)

        # Remove from global
        for i, sub in enumerate(self.global_subscriptions):
            if sub.subscription_id == subscription_id:
                self.global_subscriptions.pop(i)
                return True

        return False

    def on(
        self,
        topic: str,
        event_types: Set[str] = None
    ) -> Callable:
        """Decorator for subscribing to events."""
        def decorator(func: Callable[[Event], Awaitable[None]]) -> Callable:
            self.subscribe(topic, func, event_types)
            return func
        return decorator

    # -------------------------------------------------------------------------
    # PUBLISHING
    # -------------------------------------------------------------------------

    async def publish(
        self,
        event: Event,
        wait: bool = False
    ) -> str:
        """Publish an event."""
        # Run interceptors
        for interceptor in self._interceptors:
            event = await interceptor(event)
            if event is None:
                return ""

        # Store event
        await self.event_store.append(event)

        # Update stats
        self.stats.total_published += 1
        self.stats.events_by_topic[event.topic] += 1
        self.stats.events_by_type[event.event_type] += 1

        # Dispatch to matching channels
        tasks = []

        for channel_name, channel in self.channels.items():
            if self._topic_matches(event.topic, channel_name):
                tasks.append(channel.publish(event))

        # Also dispatch to global subscriptions
        for sub in self.global_subscriptions:
            if not sub.active:
                continue

            if self._topic_matches(event.topic, sub.topic):
                if sub.event_types and event.event_type not in sub.event_types:
                    continue

                if sub.filter_fn and not sub.filter_fn(event):
                    continue

                if sub.handler:
                    tasks.append(self._safe_dispatch(sub, event))

        if wait:
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for task in tasks:
                asyncio.create_task(task)

        self.stats.total_delivered += 1

        return event.event_id

    async def _safe_dispatch(
        self,
        subscription: Subscription,
        event: Event
    ) -> None:
        """Safely dispatch event to handler."""
        try:
            await subscription.handler(event)
        except Exception as e:
            self.stats.total_failed += 1

            self.dead_letter_queue.add(
                event,
                str(e)
            )
            self.stats.dead_letter_count += 1

            logger.exception(f"Event dispatch failed: {e}")

    async def emit(
        self,
        event_type: str,
        topic: str,
        payload: Any = None,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: str = "",
        metadata: Dict[str, Any] = None
    ) -> str:
        """Emit a new event."""
        event = Event(
            event_type=event_type,
            topic=topic,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
            metadata=metadata or {}
        )

        return await self.publish(event)

    # -------------------------------------------------------------------------
    # INTERCEPTORS
    # -------------------------------------------------------------------------

    def add_interceptor(
        self,
        interceptor: Callable[[Event], Awaitable[Optional[Event]]]
    ) -> None:
        """Add event interceptor."""
        self._interceptors.append(interceptor)

    def remove_interceptor(
        self,
        interceptor: Callable[[Event], Awaitable[Optional[Event]]]
    ) -> bool:
        """Remove event interceptor."""
        try:
            self._interceptors.remove(interceptor)
            return True
        except ValueError:
            return False

    # -------------------------------------------------------------------------
    # REPLAY & RECOVERY
    # -------------------------------------------------------------------------

    async def replay(
        self,
        topic: str = None,
        event_type: str = None,
        after: float = None,
        before: float = None,
        limit: int = 100
    ) -> int:
        """Replay events from store."""
        events = await self.event_store.get_events(
            topic=topic,
            event_type=event_type,
            after=after,
            before=before,
            limit=limit
        )

        for event in events:
            await self.publish(event)

        return len(events)

    async def retry_dead_letter(
        self,
        event_id: str = None
    ) -> int:
        """Retry dead letter events."""
        retried = 0

        if event_id:
            event = self.dead_letter_queue.retry(event_id)
            if event:
                await self.publish(event)
                self.dead_letter_queue.remove(event_id)
                retried = 1
        else:
            for entry in self.dead_letter_queue.get_retriable():
                event = self.dead_letter_queue.retry(entry.event.event_id)
                if event:
                    await self.publish(event)
                    self.dead_letter_queue.remove(entry.event.event_id)
                    retried += 1

        self.stats.total_retried += retried
        return retried

    # -------------------------------------------------------------------------
    # CORRELATION
    # -------------------------------------------------------------------------

    async def get_correlated_events(
        self,
        correlation_id: str
    ) -> List[Event]:
        """Get all events with correlation ID."""
        return await self.event_store.get_by_correlation(correlation_id)

    def create_correlation_id(self) -> str:
        """Create a new correlation ID."""
        return str(uuid.uuid4())

    # -------------------------------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the event bus."""
        if self._running:
            return

        self._running = True

        for channel in self.channels.values():
            await channel.start()

    async def stop(self) -> None:
        """Stop the event bus."""
        self._running = False

        for channel in self.channels.values():
            await channel.stop()

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern."""
        if pattern == "#" or pattern == "*":
            return True

        if pattern == topic:
            return True

        # Handle wildcards
        pattern_parts = pattern.split(".")
        topic_parts = topic.split(".")

        i = 0
        j = 0

        while i < len(pattern_parts) and j < len(topic_parts):
            if pattern_parts[i] == "#":
                return True

            if pattern_parts[i] == "*":
                i += 1
                j += 1
                continue

            if pattern_parts[i] != topic_parts[j]:
                return False

            i += 1
            j += 1

        return i == len(pattern_parts) and j == len(topic_parts)

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "total_published": self.stats.total_published,
            "total_delivered": self.stats.total_delivered,
            "total_failed": self.stats.total_failed,
            "total_retried": self.stats.total_retried,
            "dead_letter_count": self.stats.dead_letter_count,
            "channels": len(self.channels),
            "subscriptions": len(self.global_subscriptions),
            "events_by_topic": dict(self.stats.events_by_topic),
            "events_by_type": dict(self.stats.events_by_type)
        }

    def get_dead_letters(self) -> List[Dict[str, Any]]:
        """Get dead letter entries."""
        return [
            {
                "event": entry.event.to_dict(),
                "error": entry.error,
                "retry_count": entry.retry_count,
                "max_retries": entry.max_retries
            }
            for entry in self.dead_letter_queue.get_all()
        ]


# =============================================================================
# EVENT BUS BUILDER
# =============================================================================

class EventBusBuilder:
    """Fluent event bus builder."""

    def __init__(self):
        self.event_store: EventStore = None
        self.delivery_mode = DeliveryMode.AT_LEAST_ONCE
        self.channels: List[str] = []
        self.interceptors: List[Callable] = []

    def with_event_store(self, store: EventStore) -> 'EventBusBuilder':
        self.event_store = store
        return self

    def with_delivery_mode(self, mode: DeliveryMode) -> 'EventBusBuilder':
        self.delivery_mode = mode
        return self

    def with_channel(self, name: str) -> 'EventBusBuilder':
        self.channels.append(name)
        return self

    def with_interceptor(
        self,
        interceptor: Callable[[Event], Awaitable[Optional[Event]]]
    ) -> 'EventBusBuilder':
        self.interceptors.append(interceptor)
        return self

    def build(self) -> EventBus:
        bus = EventBus(
            event_store=self.event_store,
            delivery_mode=self.delivery_mode
        )

        for channel in self.channels:
            bus.create_channel(channel)

        for interceptor in self.interceptors:
            bus.add_interceptor(interceptor)

        return bus


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Event Bus System."""
    print("=" * 70)
    print("BAEL - EVENT BUS SYSTEM DEMO")
    print("Comprehensive Event-Driven Architecture")
    print("=" * 70)
    print()

    # 1. Create Event Bus
    print("1. CREATE EVENT BUS:")
    print("-" * 40)

    bus = (
        EventBusBuilder()
        .with_channel("users")
        .with_channel("orders")
        .with_channel("notifications")
        .build()
    )

    await bus.start()

    print(f"   Channels: {len(bus.channels)}")
    print(f"   Delivery mode: {bus.delivery_mode.value}")
    print()

    # 2. Subscribe to Events
    print("2. SUBSCRIBE TO EVENTS:")
    print("-" * 40)

    received_events = []

    async def user_handler(event: Event) -> None:
        received_events.append(event)
        print(f"      [User Handler] {event.event_type}: {event.payload}")

    async def order_handler(event: Event) -> None:
        received_events.append(event)
        print(f"      [Order Handler] {event.event_type}: {event.payload}")

    sub1 = bus.subscribe("users.*", user_handler)
    sub2 = bus.subscribe("orders.*", order_handler)

    print(f"   Subscription 1: {sub1[:8]}...")
    print(f"   Subscription 2: {sub2[:8]}...")
    print()

    # 3. Publish Events
    print("3. PUBLISH EVENTS:")
    print("-" * 40)

    await bus.emit(
        event_type="user.created",
        topic="users.create",
        payload={"user_id": "u1", "name": "Alice"}
    )

    await bus.emit(
        event_type="order.placed",
        topic="orders.create",
        payload={"order_id": "o1", "amount": 99.99}
    )

    await asyncio.sleep(0.1)  # Let events process

    print(f"   Events published: {bus.stats.total_published}")
    print(f"   Events received: {len(received_events)}")
    print()

    # 4. Event Filtering
    print("4. EVENT FILTERING:")
    print("-" * 40)

    filtered_events = []

    async def high_value_handler(event: Event) -> None:
        filtered_events.append(event)
        print(f"      [High Value] Order: {event.payload}")

    bus.subscribe(
        "orders.*",
        high_value_handler,
        filter_fn=lambda e: e.payload.get("amount", 0) > 50
    )

    await bus.emit(
        event_type="order.placed",
        topic="orders.create",
        payload={"order_id": "o2", "amount": 25.00}
    )

    await bus.emit(
        event_type="order.placed",
        topic="orders.create",
        payload={"order_id": "o3", "amount": 150.00}
    )

    await asyncio.sleep(0.1)

    print(f"   High value orders: {len(filtered_events)}")
    print()

    # 5. Decorator Subscription
    print("5. DECORATOR SUBSCRIPTION:")
    print("-" * 40)

    @bus.on("notifications.*")
    async def notification_handler(event: Event) -> None:
        print(f"      [Notification] {event.payload}")

    await bus.emit(
        event_type="notification.sent",
        topic="notifications.email",
        payload={"to": "alice@example.com", "subject": "Hello"}
    )

    await asyncio.sleep(0.1)
    print()

    # 6. Event Correlation
    print("6. EVENT CORRELATION:")
    print("-" * 40)

    correlation_id = bus.create_correlation_id()
    print(f"   Correlation ID: {correlation_id[:8]}...")

    await bus.emit(
        event_type="saga.started",
        topic="orders.saga",
        payload={"step": 1},
        correlation_id=correlation_id
    )

    await bus.emit(
        event_type="saga.step",
        topic="orders.saga",
        payload={"step": 2},
        correlation_id=correlation_id
    )

    await bus.emit(
        event_type="saga.completed",
        topic="orders.saga",
        payload={"step": 3},
        correlation_id=correlation_id
    )

    correlated = await bus.get_correlated_events(correlation_id)
    print(f"   Correlated events: {len(correlated)}")
    print()

    # 7. Event Priority
    print("7. EVENT PRIORITY:")
    print("-" * 40)

    priority_order = []

    async def priority_handler(event: Event) -> None:
        priority_order.append(event.priority.name)

    bus.subscribe("priority.*", priority_handler)

    await bus.emit(
        event_type="test",
        topic="priority.low",
        payload={},
        priority=EventPriority.LOW
    )

    await bus.emit(
        event_type="test",
        topic="priority.critical",
        payload={},
        priority=EventPriority.CRITICAL
    )

    await bus.emit(
        event_type="test",
        topic="priority.normal",
        payload={},
        priority=EventPriority.NORMAL
    )

    await asyncio.sleep(0.1)

    print(f"   Priority order: {priority_order}")
    print()

    # 8. Interceptors
    print("8. EVENT INTERCEPTORS:")
    print("-" * 40)

    intercepted_count = 0

    async def logging_interceptor(event: Event) -> Event:
        nonlocal intercepted_count
        intercepted_count += 1
        event.metadata["intercepted"] = True
        event.metadata["intercepted_at"] = time.time()
        return event

    bus.add_interceptor(logging_interceptor)

    await bus.emit(
        event_type="test.intercepted",
        topic="users.test",
        payload={"data": "test"}
    )

    await asyncio.sleep(0.1)

    print(f"   Intercepted events: {intercepted_count}")
    print()

    # 9. Event Replay
    print("9. EVENT REPLAY:")
    print("-" * 40)

    replay_count = await bus.replay(
        topic="users.create",
        limit=5
    )

    print(f"   Replayed events: {replay_count}")
    print()

    # 10. Dead Letter Queue
    print("10. DEAD LETTER QUEUE:")
    print("-" * 40)

    async def failing_handler(event: Event) -> None:
        raise Exception("Simulated failure")

    bus.subscribe("failing.*", failing_handler)

    await bus.emit(
        event_type="test.fail",
        topic="failing.test",
        payload={"will": "fail"}
    )

    await asyncio.sleep(0.1)

    dead_letters = bus.get_dead_letters()
    print(f"   Dead letter entries: {len(dead_letters)}")

    if dead_letters:
        print(f"   First error: {dead_letters[0]['error']}")
    print()

    # 11. Unsubscribe
    print("11. UNSUBSCRIBE:")
    print("-" * 40)

    before = len(bus.global_subscriptions)
    bus.unsubscribe(sub1)
    after = len(bus.global_subscriptions)

    print(f"   Before: {before} subscriptions")
    print(f"   After: {after} subscriptions")
    print()

    # 12. Statistics
    print("12. EVENT BUS STATISTICS:")
    print("-" * 40)

    stats = bus.get_stats()

    print(f"   Total published: {stats['total_published']}")
    print(f"   Total delivered: {stats['total_delivered']}")
    print(f"   Total failed: {stats['total_failed']}")
    print(f"   Dead letters: {stats['dead_letter_count']}")
    print(f"   Active channels: {stats['channels']}")
    print()

    # Cleanup
    await bus.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Event Bus System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
