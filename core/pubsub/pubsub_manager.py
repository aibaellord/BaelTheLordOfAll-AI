#!/usr/bin/env python3
"""
BAEL - Pub/Sub Manager
Advanced publish/subscribe messaging for AI agent operations.

Features:
- Topic management
- Subscriptions
- Message filtering
- Dead letter queues
- Message ordering
- Acknowledgments
- Retry policies
- Message persistence
- Broadcast/multicast
- Pattern matching
"""

import asyncio
import copy
import fnmatch
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Pattern, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class MessageStatus(Enum):
    """Message status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"


class AckMode(Enum):
    """Acknowledgment mode."""
    AUTO = "auto"
    MANUAL = "manual"
    BATCH = "batch"


class DeliveryMode(Enum):
    """Delivery mode."""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class SubscriptionType(Enum):
    """Subscription type."""
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    FAILOVER = "failover"


class FilterType(Enum):
    """Filter type."""
    NONE = "none"
    EXACT = "exact"
    PREFIX = "prefix"
    PATTERN = "pattern"
    REGEX = "regex"
    CUSTOM = "custom"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PubSubConfig:
    """Pub/Sub configuration."""
    max_message_size: int = 1024 * 1024  # 1MB
    max_messages_per_topic: int = 10000
    message_ttl_seconds: int = 3600
    ack_timeout_seconds: int = 30
    max_retries: int = 3
    enable_dead_letter: bool = True


@dataclass
class Message:
    """Pub/Sub message."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    payload: Any = None
    attributes: Dict[str, str] = field(default_factory=dict)
    status: MessageStatus = MessageStatus.PENDING
    publish_time: datetime = field(default_factory=datetime.utcnow)
    ordering_key: Optional[str] = None
    delivery_attempts: int = 0
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryResult:
    """Message delivery result."""
    message_id: str = ""
    subscription_id: str = ""
    success: bool = False
    error: Optional[str] = None
    delivered_at: datetime = field(default_factory=datetime.utcnow)
    latency_ms: float = 0.0


@dataclass
class TopicStats:
    """Topic statistics."""
    message_count: int = 0
    subscriber_count: int = 0
    publish_count: int = 0
    delivery_count: int = 0
    dead_letter_count: int = 0
    average_latency_ms: float = 0.0


@dataclass
class SubscriptionStats:
    """Subscription statistics."""
    messages_received: int = 0
    messages_acknowledged: int = 0
    messages_failed: int = 0
    average_latency_ms: float = 0.0
    pending_messages: int = 0


# =============================================================================
# MESSAGE FILTER
# =============================================================================

class MessageFilter(ABC):
    """Abstract message filter."""

    @property
    @abstractmethod
    def filter_type(self) -> FilterType:
        """Get filter type."""
        pass

    @abstractmethod
    def matches(self, message: Message) -> bool:
        """Check if message matches filter."""
        pass


class NoFilter(MessageFilter):
    """No filtering - accepts all messages."""

    @property
    def filter_type(self) -> FilterType:
        return FilterType.NONE

    def matches(self, message: Message) -> bool:
        return True


class ExactFilter(MessageFilter):
    """Exact attribute matching."""

    def __init__(self, attributes: Dict[str, str]):
        self._attributes = attributes

    @property
    def filter_type(self) -> FilterType:
        return FilterType.EXACT

    def matches(self, message: Message) -> bool:
        for key, value in self._attributes.items():
            if message.attributes.get(key) != value:
                return False
        return True


class PrefixFilter(MessageFilter):
    """Topic prefix matching."""

    def __init__(self, prefix: str):
        self._prefix = prefix

    @property
    def filter_type(self) -> FilterType:
        return FilterType.PREFIX

    def matches(self, message: Message) -> bool:
        return message.topic.startswith(self._prefix)


class PatternFilter(MessageFilter):
    """Glob pattern matching."""

    def __init__(self, pattern: str):
        self._pattern = pattern

    @property
    def filter_type(self) -> FilterType:
        return FilterType.PATTERN

    def matches(self, message: Message) -> bool:
        return fnmatch.fnmatch(message.topic, self._pattern)


class RegexFilter(MessageFilter):
    """Regex matching."""

    def __init__(self, pattern: str):
        self._regex = re.compile(pattern)

    @property
    def filter_type(self) -> FilterType:
        return FilterType.REGEX

    def matches(self, message: Message) -> bool:
        return bool(self._regex.match(message.topic))


class CustomFilter(MessageFilter):
    """Custom filter function."""

    def __init__(self, func: Callable[[Message], bool]):
        self._func = func

    @property
    def filter_type(self) -> FilterType:
        return FilterType.CUSTOM

    def matches(self, message: Message) -> bool:
        return self._func(message)


# =============================================================================
# TOPIC
# =============================================================================

class Topic:
    """Pub/Sub topic."""

    def __init__(
        self,
        name: str,
        config: PubSubConfig,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.config = config
        self.metadata = metadata or {}

        self._messages: Dict[str, Message] = {}
        self._message_order: List[str] = []
        self._subscriptions: Dict[str, 'Subscription'] = {}
        self._dead_letter: List[Message] = []

        self._stats = TopicStats()
        self._created_at = datetime.utcnow()
        self._lock = asyncio.Lock()

    async def publish(
        self,
        payload: Any,
        attributes: Optional[Dict[str, str]] = None,
        ordering_key: Optional[str] = None
    ) -> Message:
        """Publish message to topic."""
        async with self._lock:
            message = Message(
                topic=self.name,
                payload=payload,
                attributes=attributes or {},
                ordering_key=ordering_key,
                expires_at=datetime.utcnow() + timedelta(
                    seconds=self.config.message_ttl_seconds
                )
            )

            # Enforce max messages
            while len(self._messages) >= self.config.max_messages_per_topic:
                oldest_id = self._message_order.pop(0)
                del self._messages[oldest_id]

            self._messages[message.message_id] = message
            self._message_order.append(message.message_id)
            self._stats.message_count += 1
            self._stats.publish_count += 1

            return message

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get message by ID."""
        async with self._lock:
            return self._messages.get(message_id)

    async def add_subscription(
        self,
        subscription: 'Subscription'
    ) -> bool:
        """Add subscription."""
        async with self._lock:
            if subscription.subscription_id in self._subscriptions:
                return False
            self._subscriptions[subscription.subscription_id] = subscription
            self._stats.subscriber_count += 1
            return True

    async def remove_subscription(
        self,
        subscription_id: str
    ) -> bool:
        """Remove subscription."""
        async with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                self._stats.subscriber_count -= 1
                return True
            return False

    async def get_subscriptions(self) -> List['Subscription']:
        """Get all subscriptions."""
        async with self._lock:
            return list(self._subscriptions.values())

    async def add_to_dead_letter(self, message: Message) -> None:
        """Add message to dead letter queue."""
        async with self._lock:
            message.status = MessageStatus.DEAD_LETTER
            self._dead_letter.append(message)
            self._stats.dead_letter_count += 1

    async def get_dead_letters(
        self,
        limit: int = 100
    ) -> List[Message]:
        """Get dead letter messages."""
        async with self._lock:
            return self._dead_letter[:limit]

    async def clear_dead_letters(self) -> int:
        """Clear dead letter queue."""
        async with self._lock:
            count = len(self._dead_letter)
            self._dead_letter.clear()
            return count

    async def stats(self) -> TopicStats:
        """Get topic stats."""
        async with self._lock:
            return copy.copy(self._stats)

    async def cleanup_expired(self) -> int:
        """Clean up expired messages."""
        now = datetime.utcnow()
        expired = []

        async with self._lock:
            for msg_id, message in self._messages.items():
                if message.expires_at and message.expires_at < now:
                    expired.append(msg_id)

            for msg_id in expired:
                del self._messages[msg_id]
                self._message_order.remove(msg_id)

        return len(expired)


# =============================================================================
# SUBSCRIPTION
# =============================================================================

class Subscription:
    """Topic subscription."""

    def __init__(
        self,
        subscription_id: Optional[str] = None,
        topic_name: str = "",
        handler: Optional[Callable[[Message], Awaitable[bool]]] = None,
        subscription_type: SubscriptionType = SubscriptionType.SHARED,
        ack_mode: AckMode = AckMode.AUTO,
        delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE,
        message_filter: Optional[MessageFilter] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.subscription_id = subscription_id or str(uuid.uuid4())
        self.topic_name = topic_name
        self.handler = handler
        self.subscription_type = subscription_type
        self.ack_mode = ack_mode
        self.delivery_mode = delivery_mode
        self.message_filter = message_filter or NoFilter()
        self.metadata = metadata or {}

        self._pending: Dict[str, Message] = {}
        self._stats = SubscriptionStats()
        self._created_at = datetime.utcnow()
        self._active = True
        self._lock = asyncio.Lock()

    async def deliver(
        self,
        message: Message,
        config: PubSubConfig
    ) -> DeliveryResult:
        """Deliver message to subscription."""
        start_time = time.time()

        result = DeliveryResult(
            message_id=message.message_id,
            subscription_id=self.subscription_id
        )

        # Check filter
        if not self.message_filter.matches(message):
            return result

        # Track pending for manual ack
        if self.ack_mode == AckMode.MANUAL:
            async with self._lock:
                self._pending[message.message_id] = message

        try:
            if self.handler:
                success = await self.handler(message)
                result.success = success

                if success:
                    message.status = MessageStatus.DELIVERED
                    self._stats.messages_received += 1

                    if self.ack_mode == AckMode.AUTO:
                        await self.acknowledge(message.message_id)
                else:
                    message.delivery_attempts += 1
                    result.error = "Handler returned False"
            else:
                result.success = True
                message.status = MessageStatus.DELIVERED
        except Exception as e:
            message.delivery_attempts += 1
            result.error = str(e)
            result.success = False

        result.latency_ms = (time.time() - start_time) * 1000

        # Update stats
        async with self._lock:
            total = (
                self._stats.messages_received +
                self._stats.messages_failed
            )
            if total > 0:
                self._stats.average_latency_ms = (
                    (self._stats.average_latency_ms * (total - 1) +
                     result.latency_ms) / total
                )
            self._stats.pending_messages = len(self._pending)

        return result

    async def acknowledge(self, message_id: str) -> bool:
        """Acknowledge message."""
        async with self._lock:
            if message_id in self._pending:
                del self._pending[message_id]
                self._stats.messages_acknowledged += 1
                self._stats.pending_messages = len(self._pending)
                return True
            return False

    async def negative_acknowledge(self, message_id: str) -> Optional[Message]:
        """Negative acknowledge - requeue message."""
        async with self._lock:
            if message_id in self._pending:
                message = self._pending.pop(message_id)
                self._stats.messages_failed += 1
                self._stats.pending_messages = len(self._pending)
                return message
            return None

    async def get_pending(self) -> List[Message]:
        """Get pending messages."""
        async with self._lock:
            return list(self._pending.values())

    async def stats(self) -> SubscriptionStats:
        """Get subscription stats."""
        async with self._lock:
            return copy.copy(self._stats)

    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self._active

    def deactivate(self) -> None:
        """Deactivate subscription."""
        self._active = False

    def activate(self) -> None:
        """Activate subscription."""
        self._active = True


# =============================================================================
# PUB/SUB MANAGER
# =============================================================================

class PubSubManager:
    """
    Pub/Sub Manager for BAEL.

    Advanced publish/subscribe messaging.
    """

    def __init__(self, config: Optional[PubSubConfig] = None):
        self.config = config or PubSubConfig()

        self._topics: Dict[str, Topic] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._topic_subscriptions: Dict[str, Set[str]] = defaultdict(set)

        self._running = False
        self._delivery_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # TOPIC MANAGEMENT
    # -------------------------------------------------------------------------

    async def create_topic(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Topic:
        """Create topic."""
        async with self._lock:
            if name in self._topics:
                return self._topics[name]

            topic = Topic(name, self.config, metadata)
            self._topics[name] = topic
            return topic

    async def get_topic(self, name: str) -> Optional[Topic]:
        """Get topic by name."""
        async with self._lock:
            return self._topics.get(name)

    async def delete_topic(self, name: str) -> bool:
        """Delete topic."""
        async with self._lock:
            if name in self._topics:
                # Remove all subscriptions
                for sub_id in list(self._topic_subscriptions.get(name, set())):
                    if sub_id in self._subscriptions:
                        del self._subscriptions[sub_id]

                if name in self._topic_subscriptions:
                    del self._topic_subscriptions[name]

                del self._topics[name]
                return True
            return False

    async def list_topics(self) -> List[str]:
        """List all topic names."""
        async with self._lock:
            return list(self._topics.keys())

    # -------------------------------------------------------------------------
    # PUBLISHING
    # -------------------------------------------------------------------------

    async def publish(
        self,
        topic_name: str,
        payload: Any,
        attributes: Optional[Dict[str, str]] = None,
        ordering_key: Optional[str] = None
    ) -> Optional[Message]:
        """Publish message to topic."""
        topic = await self.get_topic(topic_name)
        if not topic:
            # Auto-create topic
            topic = await self.create_topic(topic_name)

        message = await topic.publish(payload, attributes, ordering_key)

        # Deliver to subscribers
        await self._deliver_message(topic, message)

        return message

    async def publish_batch(
        self,
        topic_name: str,
        payloads: List[Any],
        attributes: Optional[Dict[str, str]] = None
    ) -> List[Message]:
        """Publish multiple messages."""
        messages = []
        for payload in payloads:
            message = await self.publish(topic_name, payload, attributes)
            if message:
                messages.append(message)
        return messages

    async def _deliver_message(
        self,
        topic: Topic,
        message: Message
    ) -> List[DeliveryResult]:
        """Deliver message to all subscribers."""
        results = []
        subscriptions = await topic.get_subscriptions()

        for subscription in subscriptions:
            if not subscription.is_active():
                continue

            result = await subscription.deliver(message, self.config)
            results.append(result)

            # Handle failed delivery
            if not result.success:
                if message.delivery_attempts >= self.config.max_retries:
                    if self.config.enable_dead_letter:
                        await topic.add_to_dead_letter(message)

        topic._stats.delivery_count += len(results)
        return results

    # -------------------------------------------------------------------------
    # SUBSCRIPTIONS
    # -------------------------------------------------------------------------

    async def subscribe(
        self,
        topic_name: str,
        handler: Callable[[Message], Awaitable[bool]],
        subscription_id: Optional[str] = None,
        subscription_type: SubscriptionType = SubscriptionType.SHARED,
        ack_mode: AckMode = AckMode.AUTO,
        delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE,
        message_filter: Optional[MessageFilter] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Subscription:
        """Subscribe to topic."""
        # Ensure topic exists
        topic = await self.get_topic(topic_name)
        if not topic:
            topic = await self.create_topic(topic_name)

        subscription = Subscription(
            subscription_id=subscription_id,
            topic_name=topic_name,
            handler=handler,
            subscription_type=subscription_type,
            ack_mode=ack_mode,
            delivery_mode=delivery_mode,
            message_filter=message_filter,
            metadata=metadata
        )

        async with self._lock:
            self._subscriptions[subscription.subscription_id] = subscription
            self._topic_subscriptions[topic_name].add(subscription.subscription_id)

        await topic.add_subscription(subscription)
        return subscription

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe."""
        async with self._lock:
            if subscription_id not in self._subscriptions:
                return False

            subscription = self._subscriptions[subscription_id]
            topic_name = subscription.topic_name

            # Remove from topic
            topic = self._topics.get(topic_name)
            if topic:
                await topic.remove_subscription(subscription_id)

            # Clean up
            del self._subscriptions[subscription_id]
            if topic_name in self._topic_subscriptions:
                self._topic_subscriptions[topic_name].discard(subscription_id)

            return True

    async def get_subscription(
        self,
        subscription_id: str
    ) -> Optional[Subscription]:
        """Get subscription by ID."""
        async with self._lock:
            return self._subscriptions.get(subscription_id)

    async def list_subscriptions(
        self,
        topic_name: Optional[str] = None
    ) -> List[Subscription]:
        """List subscriptions."""
        async with self._lock:
            if topic_name:
                sub_ids = self._topic_subscriptions.get(topic_name, set())
                return [
                    self._subscriptions[sid]
                    for sid in sub_ids
                    if sid in self._subscriptions
                ]
            return list(self._subscriptions.values())

    # -------------------------------------------------------------------------
    # ACKNOWLEDGMENTS
    # -------------------------------------------------------------------------

    async def acknowledge(
        self,
        subscription_id: str,
        message_id: str
    ) -> bool:
        """Acknowledge message."""
        subscription = await self.get_subscription(subscription_id)
        if subscription:
            return await subscription.acknowledge(message_id)
        return False

    async def negative_acknowledge(
        self,
        subscription_id: str,
        message_id: str
    ) -> bool:
        """Negative acknowledge - requeue message."""
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            return False

        message = await subscription.negative_acknowledge(message_id)
        if message:
            topic = await self.get_topic(subscription.topic_name)
            if topic:
                await self._deliver_message(topic, message)
            return True
        return False

    # -------------------------------------------------------------------------
    # PATTERN SUBSCRIPTIONS
    # -------------------------------------------------------------------------

    async def subscribe_pattern(
        self,
        pattern: str,
        handler: Callable[[Message], Awaitable[bool]],
        **kwargs
    ) -> List[Subscription]:
        """Subscribe to topics matching pattern."""
        topics = await self.list_topics()
        subscriptions = []

        for topic_name in topics:
            if fnmatch.fnmatch(topic_name, pattern):
                subscription = await self.subscribe(
                    topic_name,
                    handler,
                    **kwargs
                )
                subscriptions.append(subscription)

        return subscriptions

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    async def topic_stats(self, topic_name: str) -> Optional[TopicStats]:
        """Get topic stats."""
        topic = await self.get_topic(topic_name)
        if topic:
            return await topic.stats()
        return None

    async def subscription_stats(
        self,
        subscription_id: str
    ) -> Optional[SubscriptionStats]:
        """Get subscription stats."""
        subscription = await self.get_subscription(subscription_id)
        if subscription:
            return await subscription.stats()
        return None

    async def topic_count(self) -> int:
        """Get topic count."""
        async with self._lock:
            return len(self._topics)

    async def subscription_count(self) -> int:
        """Get subscription count."""
        async with self._lock:
            return len(self._subscriptions)

    # -------------------------------------------------------------------------
    # DEAD LETTER
    # -------------------------------------------------------------------------

    async def get_dead_letters(
        self,
        topic_name: str,
        limit: int = 100
    ) -> List[Message]:
        """Get dead letter messages."""
        topic = await self.get_topic(topic_name)
        if topic:
            return await topic.get_dead_letters(limit)
        return []

    async def clear_dead_letters(
        self,
        topic_name: str
    ) -> int:
        """Clear dead letter queue."""
        topic = await self.get_topic(topic_name)
        if topic:
            return await topic.clear_dead_letters()
        return 0

    async def replay_dead_letters(
        self,
        topic_name: str,
        limit: int = 100
    ) -> int:
        """Replay dead letter messages."""
        topic = await self.get_topic(topic_name)
        if not topic:
            return 0

        messages = await topic.get_dead_letters(limit)
        replayed = 0

        for message in messages:
            message.status = MessageStatus.PENDING
            message.delivery_attempts = 0
            await self._deliver_message(topic, message)
            replayed += 1

        await topic.clear_dead_letters()
        return replayed

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------

    async def cleanup_expired(self) -> Dict[str, int]:
        """Clean up expired messages from all topics."""
        results = {}

        async with self._lock:
            topics = list(self._topics.values())

        for topic in topics:
            count = await topic.cleanup_expired()
            if count > 0:
                results[topic.name] = count

        return results


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Pub/Sub Manager."""
    print("=" * 70)
    print("BAEL - PUB/SUB MANAGER DEMO")
    print("Advanced Publish/Subscribe Messaging for AI Agents")
    print("=" * 70)
    print()

    manager = PubSubManager(PubSubConfig(
        message_ttl_seconds=60,
        max_retries=2
    ))

    # Message tracking
    received_messages: List[Message] = []

    # 1. Create Topic
    print("1. CREATE TOPIC:")
    print("-" * 40)

    topic = await manager.create_topic("events")
    print(f"   Topic: {topic.name}")
    print(f"   Created: {topic._created_at}")
    print()

    # 2. Subscribe to Topic
    print("2. SUBSCRIBE TO TOPIC:")
    print("-" * 40)

    async def message_handler(message: Message) -> bool:
        received_messages.append(message)
        return True

    subscription = await manager.subscribe(
        "events",
        message_handler,
        subscription_type=SubscriptionType.SHARED,
        ack_mode=AckMode.AUTO
    )

    print(f"   Subscription ID: {subscription.subscription_id[:8]}...")
    print(f"   Type: {subscription.subscription_type.value}")
    print(f"   Ack Mode: {subscription.ack_mode.value}")
    print()

    # 3. Publish Message
    print("3. PUBLISH MESSAGE:")
    print("-" * 40)

    message = await manager.publish(
        "events",
        {"action": "user_login", "user": "test"},
        attributes={"priority": "high"}
    )

    print(f"   Message ID: {message.message_id[:8] if message else 'None'}...")
    print(f"   Received: {len(received_messages)}")
    print()

    # 4. Publish Batch
    print("4. PUBLISH BATCH:")
    print("-" * 40)

    messages = await manager.publish_batch(
        "events",
        [{"event": i} for i in range(5)]
    )

    print(f"   Published: {len(messages)}")
    print(f"   Total received: {len(received_messages)}")
    print()

    # 5. Subscribe With Filter
    print("5. SUBSCRIBE WITH FILTER:")
    print("-" * 40)

    filtered_messages: List[Message] = []

    async def filtered_handler(message: Message) -> bool:
        filtered_messages.append(message)
        return True

    filter_sub = await manager.subscribe(
        "events",
        filtered_handler,
        message_filter=ExactFilter({"priority": "high"})
    )

    await manager.publish("events", {"data": "low"}, {"priority": "low"})
    await manager.publish("events", {"data": "high"}, {"priority": "high"})

    print(f"   Filtered received: {len(filtered_messages)}")
    print()

    # 6. Manual Acknowledgment
    print("6. MANUAL ACKNOWLEDGMENT:")
    print("-" * 40)

    manual_messages: List[Message] = []

    async def manual_handler(message: Message) -> bool:
        manual_messages.append(message)
        return True

    manual_sub = await manager.subscribe(
        "events",
        manual_handler,
        ack_mode=AckMode.MANUAL
    )

    msg = await manager.publish("events", {"manual": True})

    pending = await manual_sub.get_pending()
    print(f"   Pending before ack: {len(pending)}")

    if msg:
        await manager.acknowledge(manual_sub.subscription_id, msg.message_id)

    pending = await manual_sub.get_pending()
    print(f"   Pending after ack: {len(pending)}")
    print()

    # 7. Topic Stats
    print("7. TOPIC STATS:")
    print("-" * 40)

    stats = await manager.topic_stats("events")
    if stats:
        print(f"   Messages: {stats.message_count}")
        print(f"   Subscribers: {stats.subscriber_count}")
        print(f"   Publish count: {stats.publish_count}")
        print(f"   Delivery count: {stats.delivery_count}")
    print()

    # 8. Subscription Stats
    print("8. SUBSCRIPTION STATS:")
    print("-" * 40)

    sub_stats = await manager.subscription_stats(subscription.subscription_id)
    if sub_stats:
        print(f"   Received: {sub_stats.messages_received}")
        print(f"   Acknowledged: {sub_stats.messages_acknowledged}")
        print(f"   Avg latency: {sub_stats.average_latency_ms:.2f}ms")
    print()

    # 9. List Topics
    print("9. LIST TOPICS:")
    print("-" * 40)

    topics = await manager.list_topics()
    print(f"   Topics: {topics}")
    print()

    # 10. List Subscriptions
    print("10. LIST SUBSCRIPTIONS:")
    print("-" * 40)

    subscriptions = await manager.list_subscriptions("events")
    print(f"   Subscription count: {len(subscriptions)}")
    print()

    # 11. Pattern Subscription
    print("11. PATTERN SUBSCRIPTION:")
    print("-" * 40)

    await manager.create_topic("logs.app")
    await manager.create_topic("logs.system")

    pattern_messages: List[Message] = []

    async def pattern_handler(message: Message) -> bool:
        pattern_messages.append(message)
        return True

    pattern_subs = await manager.subscribe_pattern("logs.*", pattern_handler)
    print(f"   Matching subscriptions: {len(pattern_subs)}")

    await manager.publish("logs.app", {"log": "app"})
    await manager.publish("logs.system", {"log": "system"})

    print(f"   Pattern received: {len(pattern_messages)}")
    print()

    # 12. Dead Letter
    print("12. DEAD LETTER:")
    print("-" * 40)

    async def failing_handler(message: Message) -> bool:
        return False  # Always fail

    fail_sub = await manager.subscribe("events", failing_handler)

    await manager.publish("events", {"will_fail": True})

    dead_letters = await manager.get_dead_letters("events")
    print(f"   Dead letters: {len(dead_letters)}")
    print()

    # 13. Unsubscribe
    print("13. UNSUBSCRIBE:")
    print("-" * 40)

    count_before = await manager.subscription_count()
    await manager.unsubscribe(filter_sub.subscription_id)
    count_after = await manager.subscription_count()

    print(f"   Before: {count_before}")
    print(f"   After: {count_after}")
    print()

    # 14. Cleanup Expired
    print("14. CLEANUP EXPIRED:")
    print("-" * 40)

    cleaned = await manager.cleanup_expired()
    print(f"   Cleaned topics: {len(cleaned)}")
    print()

    # 15. Delete Topic
    print("15. DELETE TOPIC:")
    print("-" * 40)

    deleted = await manager.delete_topic("logs.app")
    print(f"   Deleted: {deleted}")
    print(f"   Topic count: {await manager.topic_count()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Pub/Sub Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
