"""
BAEL Event Bus System
=====================

Comprehensive event-driven architecture supporting:
- Publish/Subscribe patterns
- Event sourcing and replay
- Distributed event handling
- Event filtering and routing
- Dead letter queues
- Event aggregation

"Every action echoes through the infinite." — Ba'el
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Awaitable, Pattern, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import uuid
import traceback
import json
import weakref
import time

logger = logging.getLogger("BAEL.EventBus")


# ============================================================================
# ENUMS
# ============================================================================

class EventPriority(Enum):
    """Priority levels for events."""
    CRITICAL = 1     # System-critical, immediate processing
    HIGH = 2         # Important, process quickly
    NORMAL = 3       # Standard priority
    LOW = 4          # Background processing
    IDLE = 5         # Process when nothing else


class EventStatus(Enum):
    """Status of an event in the system."""
    PENDING = "pending"
    DISPATCHING = "dispatching"
    DELIVERED = "delivered"
    PARTIALLY_DELIVERED = "partially_delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    EXPIRED = "expired"


class DeliveryMode(Enum):
    """How events are delivered to handlers."""
    BROADCAST = "broadcast"       # All handlers receive
    LOAD_BALANCE = "load_balance" # One handler receives (round-robin)
    RANDOM = "random"             # One random handler receives
    FIRST = "first"               # First available handler


class SubscriptionType(Enum):
    """Types of subscriptions."""
    PERSISTENT = "persistent"     # Survives restarts
    TEMPORARY = "temporary"       # Lost on restart
    DURABLE = "durable"           # Guaranteed delivery
    ONCE = "once"                 # Single delivery then unsubscribe


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Event:
    """An event in the system."""
    type: str                     # Event type/topic
    data: Any                     # Event payload

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "unknown"       # Source of the event

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Metadata
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None  # For tracking related events
    causation_id: Optional[str] = None    # Event that caused this one
    version: int = 1

    # State
    status: EventStatus = EventStatus.PENDING
    delivery_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the event has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'id': self.id,
            'type': self.type,
            'data': self.data,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'priority': self.priority.value,
            'correlation_id': self.correlation_id,
            'causation_id': self.causation_id,
            'version': self.version,
            'status': self.status.value,
            'delivery_count': self.delivery_count,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        event = cls(
            type=data['type'],
            data=data['data'],
            id=data.get('id', str(uuid.uuid4())),
            source=data.get('source', 'unknown')
        )

        if data.get('timestamp'):
            event.timestamp = datetime.fromisoformat(data['timestamp'])
        if data.get('expires_at'):
            event.expires_at = datetime.fromisoformat(data['expires_at'])
        if data.get('priority'):
            event.priority = EventPriority(data['priority'])

        event.correlation_id = data.get('correlation_id')
        event.causation_id = data.get('causation_id')
        event.version = data.get('version', 1)
        event.metadata = data.get('metadata', {})

        return event


@dataclass
class EventFilter:
    """Filter for matching events."""
    event_types: Optional[List[str]] = None  # Match any of these types
    type_pattern: Optional[str] = None       # Regex pattern for type
    sources: Optional[List[str]] = None      # Match any of these sources
    min_priority: Optional[EventPriority] = None
    metadata_match: Optional[Dict[str, Any]] = None

    _type_regex: Optional[Pattern] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.type_pattern:
            self._type_regex = re.compile(self.type_pattern)

    def matches(self, event: Event) -> bool:
        """Check if an event matches this filter."""
        # Check event types
        if self.event_types and event.type not in self.event_types:
            return False

        # Check type pattern
        if self._type_regex and not self._type_regex.match(event.type):
            return False

        # Check sources
        if self.sources and event.source not in self.sources:
            return False

        # Check priority
        if self.min_priority and event.priority.value > self.min_priority.value:
            return False

        # Check metadata
        if self.metadata_match:
            for key, value in self.metadata_match.items():
                if event.metadata.get(key) != value:
                    return False

        return True


@dataclass
class EventHandler:
    """An event handler definition."""
    id: str
    callback: Callable[[Event], Awaitable[None]]
    filter: Optional[EventFilter] = None
    priority: int = 0               # Handler priority (lower = first)
    max_concurrent: int = 10        # Max concurrent executions
    timeout_seconds: float = 30.0   # Handler timeout
    retry_count: int = 0            # Number of retries

    # State
    invocation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_invoked: Optional[datetime] = None

    _semaphore: asyncio.Semaphore = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self):
        self._semaphore = asyncio.Semaphore(self.max_concurrent)


@dataclass
class Subscription:
    """A subscription to events."""
    id: str
    handler: EventHandler
    event_types: List[str]          # Types subscribed to (wildcards supported)
    subscription_type: SubscriptionType = SubscriptionType.TEMPORARY
    group: Optional[str] = None     # Consumer group for load balancing

    # State
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    events_received: int = 0

    def matches_type(self, event_type: str) -> bool:
        """Check if this subscription matches an event type."""
        for pattern in self.event_types:
            if pattern == '*':
                return True
            if pattern.endswith('.*'):
                prefix = pattern[:-2]
                if event_type.startswith(prefix):
                    return True
            elif pattern == event_type:
                return True
        return False


@dataclass
class EventBusConfig:
    """Configuration for the event bus."""
    max_queue_size: int = 10000
    enable_event_store: bool = True
    store_retention_hours: int = 24
    enable_dead_letter: bool = True
    dead_letter_max_size: int = 1000
    dispatch_batch_size: int = 100
    dispatch_interval_ms: int = 10
    enable_metrics: bool = True


# ============================================================================
# EVENT STORE
# ============================================================================

class EventStore:
    """
    Persistent event storage with replay capability.

    Supports:
    - Event persistence
    - Time-based queries
    - Event replay
    - Snapshotting
    """

    def __init__(self, retention_hours: int = 24):
        """Initialize event store."""
        self.retention_hours = retention_hours
        self._events: Dict[str, Event] = {}
        self._events_by_type: Dict[str, List[str]] = defaultdict(list)
        self._events_by_source: Dict[str, List[str]] = defaultdict(list)
        self._events_by_correlation: Dict[str, List[str]] = defaultdict(list)
        self._sequence: List[str] = []

    def store(self, event: Event) -> None:
        """Store an event."""
        self._events[event.id] = event
        self._events_by_type[event.type].append(event.id)
        self._events_by_source[event.source].append(event.id)
        if event.correlation_id:
            self._events_by_correlation[event.correlation_id].append(event.id)
        self._sequence.append(event.id)

        # Cleanup old events
        self._cleanup()

    def get(self, event_id: str) -> Optional[Event]:
        """Get an event by ID."""
        return self._events.get(event_id)

    def get_by_type(self, event_type: str, limit: int = 100) -> List[Event]:
        """Get events by type."""
        event_ids = self._events_by_type.get(event_type, [])[-limit:]
        return [self._events[eid] for eid in event_ids if eid in self._events]

    def get_by_source(self, source: str, limit: int = 100) -> List[Event]:
        """Get events by source."""
        event_ids = self._events_by_source.get(source, [])[-limit:]
        return [self._events[eid] for eid in event_ids if eid in self._events]

    def get_by_correlation(self, correlation_id: str) -> List[Event]:
        """Get all events with a correlation ID."""
        event_ids = self._events_by_correlation.get(correlation_id, [])
        return [self._events[eid] for eid in event_ids if eid in self._events]

    def get_since(self, since: datetime, limit: int = 1000) -> List[Event]:
        """Get events since a timestamp."""
        events = [
            e for e in self._events.values()
            if e.timestamp >= since
        ]
        events.sort(key=lambda e: e.timestamp)
        return events[:limit]

    def get_range(
        self,
        start: datetime,
        end: datetime,
        event_type: Optional[str] = None
    ) -> List[Event]:
        """Get events in a time range."""
        events = []
        for event in self._events.values():
            if start <= event.timestamp <= end:
                if event_type is None or event.type == event_type:
                    events.append(event)
        events.sort(key=lambda e: e.timestamp)
        return events

    def replay(
        self,
        handler: Callable[[Event], Awaitable[None]],
        since: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> int:
        """Replay stored events to a handler."""
        if since:
            events = self.get_since(since)
        else:
            events = list(self._events.values())

        if event_type:
            events = [e for e in events if e.type == event_type]

        count = 0
        for event in events:
            asyncio.create_task(handler(event))
            count += 1

        return count

    def _cleanup(self) -> None:
        """Remove expired events."""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)

        # Find expired events
        expired = [
            eid for eid, event in self._events.items()
            if event.timestamp < cutoff
        ]

        # Remove from all indexes
        for event_id in expired:
            event = self._events.pop(event_id, None)
            if event:
                if event_id in self._events_by_type.get(event.type, []):
                    self._events_by_type[event.type].remove(event_id)
                if event_id in self._events_by_source.get(event.source, []):
                    self._events_by_source[event.source].remove(event_id)
                if event.correlation_id and event_id in self._events_by_correlation.get(event.correlation_id, []):
                    self._events_by_correlation[event.correlation_id].remove(event_id)

        self._sequence = [eid for eid in self._sequence if eid in self._events]

    def get_statistics(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            'total_events': len(self._events),
            'event_types': len(self._events_by_type),
            'sources': len(self._events_by_source),
            'correlations': len(self._events_by_correlation)
        }


# ============================================================================
# EVENT DISPATCHER
# ============================================================================

class EventDispatcher:
    """
    Dispatches events to handlers with priority and load balancing.
    """

    def __init__(self, config: EventBusConfig):
        """Initialize dispatcher."""
        self.config = config
        self._handlers: Dict[str, EventHandler] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._consumer_groups: Dict[str, List[str]] = defaultdict(list)  # group -> subscription_ids
        self._round_robin_index: Dict[str, int] = defaultdict(int)

        # Dead letter queue
        self._dead_letters: List[Tuple[Event, str]] = []

        # Statistics
        self._stats = {
            'events_dispatched': 0,
            'events_delivered': 0,
            'events_failed': 0,
            'dead_letters': 0
        }

    def add_handler(self, handler: EventHandler) -> None:
        """Add an event handler."""
        self._handlers[handler.id] = handler

    def remove_handler(self, handler_id: str) -> bool:
        """Remove an event handler."""
        if handler_id in self._handlers:
            del self._handlers[handler_id]
            # Remove from subscriptions
            for sub in list(self._subscriptions.values()):
                if sub.handler.id == handler_id:
                    self.unsubscribe(sub.id)
            return True
        return False

    def subscribe(self, subscription: Subscription) -> None:
        """Add a subscription."""
        self._subscriptions[subscription.id] = subscription
        if subscription.group:
            self._consumer_groups[subscription.group].append(subscription.id)

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        if subscription_id in self._subscriptions:
            sub = self._subscriptions.pop(subscription_id)
            if sub.group and subscription_id in self._consumer_groups.get(sub.group, []):
                self._consumer_groups[sub.group].remove(subscription_id)
            return True
        return False

    async def dispatch(
        self,
        event: Event,
        delivery_mode: DeliveryMode = DeliveryMode.BROADCAST
    ) -> int:
        """Dispatch an event to matching subscribers."""
        self._stats['events_dispatched'] += 1
        event.status = EventStatus.DISPATCHING

        # Find matching subscriptions
        matching = self._find_matching_subscriptions(event)

        if not matching:
            event.status = EventStatus.DELIVERED
            return 0

        # Apply delivery mode
        if delivery_mode == DeliveryMode.BROADCAST:
            targets = matching
        elif delivery_mode == DeliveryMode.LOAD_BALANCE:
            targets = [self._select_round_robin(matching)]
        elif delivery_mode == DeliveryMode.RANDOM:
            import random
            targets = [random.choice(matching)]
        elif delivery_mode == DeliveryMode.FIRST:
            targets = [matching[0]]
        else:
            targets = matching

        # Dispatch to targets
        delivered = 0
        failed = 0

        tasks = []
        for sub in targets:
            task = asyncio.create_task(self._deliver_to_subscription(event, sub))
            tasks.append((sub, task))

        for sub, task in tasks:
            try:
                result = await task
                if result:
                    delivered += 1
                    sub.events_received += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Delivery failed: {e}")

        # Update event status
        event.delivery_count = delivered
        if delivered == len(targets):
            event.status = EventStatus.DELIVERED
            self._stats['events_delivered'] += 1
        elif delivered > 0:
            event.status = EventStatus.PARTIALLY_DELIVERED
            self._stats['events_delivered'] += 1
        else:
            event.status = EventStatus.FAILED
            self._stats['events_failed'] += 1
            if self.config.enable_dead_letter:
                self._add_to_dead_letter(event, "All deliveries failed")

        # Handle ONCE subscriptions
        for sub in targets:
            if sub.subscription_type == SubscriptionType.ONCE:
                self.unsubscribe(sub.id)

        return delivered

    def _find_matching_subscriptions(self, event: Event) -> List[Subscription]:
        """Find subscriptions that match an event."""
        matching = []

        for sub in self._subscriptions.values():
            if not sub.active:
                continue

            if not sub.matches_type(event.type):
                continue

            if sub.handler.filter and not sub.handler.filter.matches(event):
                continue

            matching.append(sub)

        # Sort by handler priority
        matching.sort(key=lambda s: s.handler.priority)
        return matching

    def _select_round_robin(self, subscriptions: List[Subscription]) -> Subscription:
        """Select a subscription using round-robin."""
        groups = set(s.group for s in subscriptions if s.group)

        if groups:
            # Group-aware round-robin
            group = list(groups)[0]
            members = self._consumer_groups.get(group, [])
            if members:
                index = self._round_robin_index[group]
                self._round_robin_index[group] = (index + 1) % len(members)
                sub_id = members[index]
                return self._subscriptions.get(sub_id, subscriptions[0])

        return subscriptions[0]

    async def _deliver_to_subscription(
        self,
        event: Event,
        subscription: Subscription
    ) -> bool:
        """Deliver an event to a subscription."""
        handler = subscription.handler

        async with handler._semaphore:
            handler.invocation_count += 1
            handler.last_invoked = datetime.now()

            for attempt in range(handler.retry_count + 1):
                try:
                    await asyncio.wait_for(
                        handler.callback(event),
                        timeout=handler.timeout_seconds
                    )
                    handler.success_count += 1
                    return True
                except asyncio.TimeoutError:
                    logger.warning(f"Handler {handler.id} timed out on event {event.id}")
                except Exception as e:
                    logger.error(f"Handler {handler.id} failed: {e}")
                    if attempt < handler.retry_count:
                        await asyncio.sleep(0.1 * (attempt + 1))

            handler.failure_count += 1
            return False

    def _add_to_dead_letter(self, event: Event, reason: str) -> None:
        """Add an event to the dead letter queue."""
        event.status = EventStatus.DEAD_LETTER
        self._dead_letters.append((event, reason))
        self._stats['dead_letters'] += 1

        # Trim if too large
        while len(self._dead_letters) > self.config.dead_letter_max_size:
            self._dead_letters.pop(0)

    def get_dead_letters(self) -> List[Tuple[Event, str]]:
        """Get dead letter queue contents."""
        return self._dead_letters.copy()

    def clear_dead_letters(self) -> int:
        """Clear dead letter queue."""
        count = len(self._dead_letters)
        self._dead_letters.clear()
        return count

    def get_statistics(self) -> Dict[str, Any]:
        """Get dispatcher statistics."""
        return {
            **self._stats,
            'handlers': len(self._handlers),
            'subscriptions': len(self._subscriptions),
            'consumer_groups': len(self._consumer_groups)
        }


# ============================================================================
# EVENT ROUTER
# ============================================================================

class EventRouter:
    """
    Route events based on content and rules.
    """

    def __init__(self):
        """Initialize router."""
        self._routes: List[Tuple[EventFilter, str]] = []  # (filter, destination)
        self._transforms: Dict[str, Callable[[Event], Event]] = {}

    def add_route(
        self,
        filter: EventFilter,
        destination: str
    ) -> None:
        """Add a routing rule."""
        self._routes.append((filter, destination))

    def add_transform(
        self,
        source_type: str,
        target_type: str,
        transform: Callable[[Event], Event]
    ) -> None:
        """Add an event transform."""
        key = f"{source_type}:{target_type}"
        self._transforms[key] = transform

    def route(self, event: Event) -> List[str]:
        """Determine destinations for an event."""
        destinations = []
        for filter, dest in self._routes:
            if filter.matches(event):
                destinations.append(dest)
        return destinations

    def transform(self, event: Event, target_type: str) -> Optional[Event]:
        """Transform an event to a different type."""
        key = f"{event.type}:{target_type}"
        if key in self._transforms:
            return self._transforms[key](event)
        return None


# ============================================================================
# EVENT AGGREGATOR
# ============================================================================

class EventAggregator:
    """
    Aggregate multiple events into a single event.

    Useful for:
    - Batch processing
    - Deduplication
    - Rate limiting
    """

    def __init__(self):
        """Initialize aggregator."""
        self._buffers: Dict[str, List[Event]] = defaultdict(list)
        self._timers: Dict[str, asyncio.Task] = {}
        self._handlers: Dict[str, Callable[[List[Event]], Awaitable[Event]]] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        event_type: str,
        aggregator: Callable[[List[Event]], Awaitable[Event]],
        batch_size: int = 10,
        timeout_seconds: float = 5.0
    ) -> None:
        """Register an aggregation handler."""
        self._handlers[event_type] = aggregator
        self._configs[event_type] = {
            'batch_size': batch_size,
            'timeout': timeout_seconds
        }

    async def add(self, event: Event) -> Optional[Event]:
        """Add an event to the aggregation buffer."""
        event_type = event.type

        if event_type not in self._handlers:
            return None

        self._buffers[event_type].append(event)
        config = self._configs[event_type]

        # Check batch size
        if len(self._buffers[event_type]) >= config['batch_size']:
            return await self._flush(event_type)

        # Start timeout timer if not running
        if event_type not in self._timers or self._timers[event_type].done():
            self._timers[event_type] = asyncio.create_task(
                self._timeout_flush(event_type, config['timeout'])
            )

        return None

    async def _timeout_flush(self, event_type: str, timeout: float) -> None:
        """Flush buffer after timeout."""
        await asyncio.sleep(timeout)
        await self._flush(event_type)

    async def _flush(self, event_type: str) -> Optional[Event]:
        """Flush and aggregate buffered events."""
        events = self._buffers[event_type]
        self._buffers[event_type] = []

        if event_type in self._timers:
            self._timers[event_type].cancel()

        if not events:
            return None

        handler = self._handlers.get(event_type)
        if handler:
            return await handler(events)

        return None


# ============================================================================
# MAIN EVENT BUS
# ============================================================================

class EventBus:
    """
    Main event bus system.

    Features:
    - Publish/Subscribe pattern
    - Event sourcing with replay
    - Dead letter queue
    - Event aggregation
    - Content-based routing
    - Consumer groups
    - Metrics and monitoring

    "Through Ba'el, all events flow." — Ba'el
    """

    def __init__(self, config: Optional[EventBusConfig] = None):
        """Initialize event bus."""
        self.config = config or EventBusConfig()

        # Components
        self.dispatcher = EventDispatcher(self.config)
        self.router = EventRouter()
        self.aggregator = EventAggregator()

        if self.config.enable_event_store:
            self.store = EventStore(self.config.store_retention_hours)
        else:
            self.store = None

        # Event queue
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_queue_size)

        # State
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None

        # Metrics
        self._metrics = {
            'events_published': 0,
            'events_queued': 0,
            'queue_overflows': 0
        }

        logger.info("EventBus initialized")

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    async def start(self) -> None:
        """Start the event bus."""
        if self._running:
            return

        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("EventBus started")

    async def stop(self) -> None:
        """Stop the event bus."""
        if not self._running:
            return

        self._running = False

        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        logger.info("EventBus stopped")

    async def _dispatch_loop(self) -> None:
        """Main dispatch loop."""
        while self._running:
            try:
                # Batch dispatch
                events = []
                try:
                    while len(events) < self.config.dispatch_batch_size:
                        event = self._queue.get_nowait()
                        events.append(event)
                except asyncio.QueueEmpty:
                    pass

                for event in events:
                    await self.dispatcher.dispatch(event)

                if not events:
                    await asyncio.sleep(self.config.dispatch_interval_ms / 1000)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dispatch loop error: {e}")

    # ========================================================================
    # PUBLISHING
    # ========================================================================

    async def publish(
        self,
        event_type: str,
        data: Any,
        source: str = "unknown",
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        expires_in_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Publish an event."""
        event = Event(
            type=event_type,
            data=data,
            source=source,
            priority=priority,
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=metadata or {}
        )

        if expires_in_seconds:
            event.expires_at = datetime.now() + timedelta(seconds=expires_in_seconds)

        return await self.emit(event)

    async def emit(self, event: Event) -> Event:
        """Emit a pre-constructed event."""
        self._metrics['events_published'] += 1

        # Check expiration
        if event.is_expired():
            event.status = EventStatus.EXPIRED
            return event

        # Store event
        if self.store:
            self.store.store(event)

        # Queue for dispatch
        try:
            self._queue.put_nowait(event)
            self._metrics['events_queued'] += 1
        except asyncio.QueueFull:
            self._metrics['queue_overflows'] += 1
            logger.warning(f"Event queue full, dispatching immediately: {event.id}")
            await self.dispatcher.dispatch(event)

        return event

    def emit_sync(self, event: Event) -> None:
        """Emit an event synchronously (fire and forget)."""
        asyncio.create_task(self.emit(event))

    # ========================================================================
    # SUBSCRIBING
    # ========================================================================

    def subscribe(
        self,
        event_types: Union[str, List[str]],
        handler: Callable[[Event], Awaitable[None]],
        handler_id: Optional[str] = None,
        filter: Optional[EventFilter] = None,
        group: Optional[str] = None,
        subscription_type: SubscriptionType = SubscriptionType.TEMPORARY,
        priority: int = 0,
        max_concurrent: int = 10,
        timeout_seconds: float = 30.0,
        retry_count: int = 0
    ) -> str:
        """Subscribe to events."""
        if isinstance(event_types, str):
            event_types = [event_types]

        handler_obj = EventHandler(
            id=handler_id or str(uuid.uuid4()),
            callback=handler,
            filter=filter,
            priority=priority,
            max_concurrent=max_concurrent,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count
        )

        subscription = Subscription(
            id=str(uuid.uuid4()),
            handler=handler_obj,
            event_types=event_types,
            subscription_type=subscription_type,
            group=group
        )

        self.dispatcher.add_handler(handler_obj)
        self.dispatcher.subscribe(subscription)

        logger.info(f"Subscribed to {event_types}: {subscription.id}")
        return subscription.id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        return self.dispatcher.unsubscribe(subscription_id)

    def on(
        self,
        event_type: str,
        **kwargs
    ) -> Callable:
        """Decorator to subscribe to an event type."""
        def decorator(func: Callable[[Event], Awaitable[None]]) -> Callable:
            self.subscribe(event_type, func, **kwargs)
            return func
        return decorator

    def once(
        self,
        event_type: str,
        **kwargs
    ) -> Callable:
        """Decorator for one-time subscription."""
        def decorator(func: Callable[[Event], Awaitable[None]]) -> Callable:
            self.subscribe(
                event_type, func,
                subscription_type=SubscriptionType.ONCE,
                **kwargs
            )
            return func
        return decorator

    # ========================================================================
    # QUERYING
    # ========================================================================

    def get_events(
        self,
        since: Optional[datetime] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get stored events."""
        if not self.store:
            return []

        if since:
            events = self.store.get_since(since, limit)
        else:
            events = list(self.store._events.values())[:limit]

        if event_type:
            events = [e for e in events if e.type == event_type]

        return events

    def get_event(self, event_id: str) -> Optional[Event]:
        """Get a specific event."""
        if self.store:
            return self.store.get(event_id)
        return None

    async def replay(
        self,
        handler: Callable[[Event], Awaitable[None]],
        since: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> int:
        """Replay stored events."""
        if not self.store:
            return 0
        return self.store.replay(handler, since, event_type)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    async def wait_for(
        self,
        event_type: str,
        timeout: float = 30.0,
        filter: Optional[EventFilter] = None
    ) -> Optional[Event]:
        """Wait for a specific event."""
        result: List[Event] = []
        event_received = asyncio.Event()

        async def handler(event: Event) -> None:
            result.append(event)
            event_received.set()

        sub_id = self.subscribe(
            event_type,
            handler,
            filter=filter,
            subscription_type=SubscriptionType.ONCE
        )

        try:
            await asyncio.wait_for(event_received.wait(), timeout=timeout)
            return result[0] if result else None
        except asyncio.TimeoutError:
            self.unsubscribe(sub_id)
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._metrics,
            'queue_size': self._queue.qsize(),
            'dispatcher': self.dispatcher.get_statistics(),
            'store': self.store.get_statistics() if self.store else {}
        }

    def get_status(self) -> Dict[str, Any]:
        """Get event bus status."""
        return {
            'running': self._running,
            'statistics': self.get_statistics(),
            'dead_letters': len(self.dispatcher.get_dead_letters())
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

event_bus = EventBus()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def publish(event_type: str, data: Any, **kwargs) -> Event:
    """Publish an event using the default bus."""
    return await event_bus.publish(event_type, data, **kwargs)


def subscribe(event_type: str, handler: Callable[[Event], Awaitable[None]], **kwargs) -> str:
    """Subscribe using the default bus."""
    return event_bus.subscribe(event_type, handler, **kwargs)


def on(event_type: str, **kwargs) -> Callable:
    """Decorator to subscribe using the default bus."""
    return event_bus.on(event_type, **kwargs)
