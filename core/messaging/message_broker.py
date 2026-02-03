#!/usr/bin/env python3
"""
BAEL - Message Broker System
Comprehensive message broker for async communication.

Features:
- Topic-based pub/sub
- Queue management
- Message persistence
- Dead letter queues
- Message acknowledgment
- Retry policies
- Message filtering
- Priority queues
- Message TTL
- Consumer groups
"""

import asyncio
import hashlib
import heapq
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class MessageStatus(Enum):
    """Message status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    EXPIRED = "expired"
    DEAD_LETTERED = "dead_lettered"


class DeliveryMode(Enum):
    """Delivery mode."""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class MessagePriority(Enum):
    """Message priority."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class AckMode(Enum):
    """Acknowledgment mode."""
    AUTO = "auto"
    MANUAL = "manual"
    CLIENT = "client"


class SubscriptionType(Enum):
    """Subscription types."""
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    FAILOVER = "failover"
    KEY_SHARED = "key_shared"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Message:
    """Message structure."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    key: str = ""
    payload: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    created_at: float = field(default_factory=time.time)
    ttl: float = 0.0  # 0 = no expiry
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: str = ""
    reply_to: str = ""

    @property
    def is_expired(self) -> bool:
        if self.ttl == 0:
            return False
        return time.time() > self.created_at + self.ttl

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def __lt__(self, other: 'Message') -> bool:
        # Higher priority first, then older first
        if self.priority != other.priority:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


@dataclass
class Subscription:
    """Subscription configuration."""
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    consumer_group: str = "default"
    sub_type: SubscriptionType = SubscriptionType.SHARED
    ack_mode: AckMode = AckMode.MANUAL
    filter_expression: str = ""
    max_redelivery: int = 3
    ack_timeout: float = 30.0
    created_at: float = field(default_factory=time.time)


@dataclass
class Consumer:
    """Consumer info."""
    consumer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subscription_id: str = ""
    handler: Callable[[Message], Awaitable[bool]] = None
    active: bool = True
    messages_received: int = 0
    messages_acked: int = 0
    messages_rejected: int = 0
    last_activity: float = field(default_factory=time.time)


@dataclass
class QueueStats:
    """Queue statistics."""
    topic: str = ""
    messages_pending: int = 0
    messages_delivered: int = 0
    messages_acknowledged: int = 0
    messages_dead_lettered: int = 0
    consumers: int = 0
    throughput_per_second: float = 0.0


@dataclass
class DeadLetterEntry:
    """Dead letter queue entry."""
    message: Message
    reason: str = ""
    original_topic: str = ""
    dead_lettered_at: float = field(default_factory=time.time)


# =============================================================================
# MESSAGE STORE
# =============================================================================

class MessageStore:
    """In-memory message store."""

    def __init__(self, max_messages_per_topic: int = 100000):
        self._messages: Dict[str, Dict[str, Message]] = defaultdict(dict)
        self._pending: Dict[str, List[Message]] = defaultdict(list)
        self._max_per_topic = max_messages_per_topic

    def store(self, message: Message) -> bool:
        """Store a message."""
        topic = message.topic

        if len(self._messages[topic]) >= self._max_per_topic:
            return False

        self._messages[topic][message.message_id] = message
        heapq.heappush(self._pending[topic], message)

        return True

    def get(self, topic: str, message_id: str) -> Optional[Message]:
        """Get a message."""
        return self._messages.get(topic, {}).get(message_id)

    def get_pending(self, topic: str, count: int = 1) -> List[Message]:
        """Get pending messages."""
        result = []

        while self._pending.get(topic) and len(result) < count:
            message = heapq.heappop(self._pending[topic])

            if message.is_expired:
                message.status = MessageStatus.EXPIRED
                continue

            if message.status == MessageStatus.PENDING:
                result.append(message)

        return result

    def update_status(
        self,
        topic: str,
        message_id: str,
        status: MessageStatus
    ) -> bool:
        """Update message status."""
        message = self.get(topic, message_id)

        if message:
            message.status = status
            return True

        return False

    def requeue(self, message: Message) -> None:
        """Requeue a message."""
        message.retry_count += 1
        message.status = MessageStatus.PENDING
        heapq.heappush(self._pending[message.topic], message)

    def get_stats(self, topic: str) -> Dict[str, int]:
        """Get topic stats."""
        messages = self._messages.get(topic, {})

        stats = {
            "total": len(messages),
            "pending": 0,
            "delivered": 0,
            "acknowledged": 0,
            "rejected": 0,
            "expired": 0
        }

        for msg in messages.values():
            stats[msg.status.value] = stats.get(msg.status.value, 0) + 1

        return stats

    def cleanup_expired(self, topic: str) -> int:
        """Clean up expired messages."""
        count = 0
        messages = self._messages.get(topic, {})

        expired_ids = [
            mid for mid, msg in messages.items()
            if msg.is_expired
        ]

        for mid in expired_ids:
            del messages[mid]
            count += 1

        return count


# =============================================================================
# DEAD LETTER QUEUE
# =============================================================================

class DeadLetterQueue:
    """Dead letter queue for failed messages."""

    def __init__(self, max_size: int = 10000):
        self._entries: Dict[str, DeadLetterEntry] = {}
        self._max_size = max_size

    def add(self, message: Message, reason: str) -> DeadLetterEntry:
        """Add message to DLQ."""
        entry = DeadLetterEntry(
            message=message,
            reason=reason,
            original_topic=message.topic
        )

        message.status = MessageStatus.DEAD_LETTERED
        self._entries[message.message_id] = entry

        # Cleanup if over limit
        if len(self._entries) > self._max_size:
            oldest = min(
                self._entries.keys(),
                key=lambda k: self._entries[k].dead_lettered_at
            )
            del self._entries[oldest]

        return entry

    def get(self, message_id: str) -> Optional[DeadLetterEntry]:
        """Get DLQ entry."""
        return self._entries.get(message_id)

    def remove(self, message_id: str) -> bool:
        """Remove from DLQ."""
        if message_id in self._entries:
            del self._entries[message_id]
            return True
        return False

    def reprocess(self, message_id: str) -> Optional[Message]:
        """Get message for reprocessing."""
        entry = self._entries.get(message_id)

        if entry:
            message = entry.message
            message.status = MessageStatus.PENDING
            message.retry_count = 0
            del self._entries[message_id]
            return message

        return None

    def list_entries(
        self,
        topic: str = None,
        limit: int = 100
    ) -> List[DeadLetterEntry]:
        """List DLQ entries."""
        entries = list(self._entries.values())

        if topic:
            entries = [e for e in entries if e.original_topic == topic]

        return entries[:limit]

    @property
    def size(self) -> int:
        return len(self._entries)


# =============================================================================
# TOPIC MANAGER
# =============================================================================

class TopicManager:
    """Manages topics and partitions."""

    def __init__(self):
        self._topics: Dict[str, Dict[str, Any]] = {}
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)

    def create_topic(
        self,
        name: str,
        partitions: int = 1,
        retention_hours: int = 24,
        max_message_size: int = 1024 * 1024
    ) -> bool:
        """Create a topic."""
        if name in self._topics:
            return False

        self._topics[name] = {
            "name": name,
            "partitions": partitions,
            "retention_hours": retention_hours,
            "max_message_size": max_message_size,
            "created_at": time.time()
        }

        return True

    def delete_topic(self, name: str) -> bool:
        """Delete a topic."""
        if name in self._topics:
            del self._topics[name]
            if name in self._subscriptions:
                del self._subscriptions[name]
            return True
        return False

    def get_topic(self, name: str) -> Optional[Dict[str, Any]]:
        """Get topic info."""
        return self._topics.get(name)

    def list_topics(self) -> List[str]:
        """List all topics."""
        return list(self._topics.keys())

    def topic_exists(self, name: str) -> bool:
        """Check if topic exists."""
        return name in self._topics

    def add_subscription(self, subscription: Subscription) -> str:
        """Add subscription to topic."""
        self._subscriptions[subscription.topic].append(subscription)
        return subscription.subscription_id

    def get_subscriptions(self, topic: str) -> List[Subscription]:
        """Get subscriptions for topic."""
        return self._subscriptions.get(topic, [])

    def remove_subscription(self, topic: str, subscription_id: str) -> bool:
        """Remove subscription."""
        subs = self._subscriptions.get(topic, [])

        for i, sub in enumerate(subs):
            if sub.subscription_id == subscription_id:
                subs.pop(i)
                return True

        return False


# =============================================================================
# CONSUMER GROUP MANAGER
# =============================================================================

class ConsumerGroupManager:
    """Manages consumer groups."""

    def __init__(self):
        self._groups: Dict[str, Dict[str, Consumer]] = defaultdict(dict)
        self._assignments: Dict[str, str] = {}  # consumer_id -> subscription_id

    def register_consumer(
        self,
        subscription: Subscription,
        handler: Callable[[Message], Awaitable[bool]]
    ) -> Consumer:
        """Register a consumer."""
        consumer = Consumer(
            subscription_id=subscription.subscription_id,
            handler=handler
        )

        group_key = f"{subscription.topic}:{subscription.consumer_group}"
        self._groups[group_key][consumer.consumer_id] = consumer
        self._assignments[consumer.consumer_id] = subscription.subscription_id

        return consumer

    def unregister_consumer(self, consumer_id: str) -> bool:
        """Unregister a consumer."""
        for group_key, consumers in self._groups.items():
            if consumer_id in consumers:
                del consumers[consumer_id]
                if consumer_id in self._assignments:
                    del self._assignments[consumer_id]
                return True
        return False

    def get_consumers(
        self,
        topic: str,
        group: str = "default"
    ) -> List[Consumer]:
        """Get consumers for group."""
        group_key = f"{topic}:{group}"
        return list(self._groups.get(group_key, {}).values())

    def get_active_consumer(
        self,
        topic: str,
        group: str = "default",
        key: str = None
    ) -> Optional[Consumer]:
        """Get an active consumer."""
        consumers = [c for c in self.get_consumers(topic, group) if c.active]

        if not consumers:
            return None

        if key:
            # Consistent hashing for key-based routing
            hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
            index = hash_val % len(consumers)
            return consumers[index]

        # Round-robin (simple)
        return min(consumers, key=lambda c: c.messages_received)

    def update_consumer_stats(
        self,
        consumer_id: str,
        received: int = 0,
        acked: int = 0,
        rejected: int = 0
    ) -> None:
        """Update consumer statistics."""
        for consumers in self._groups.values():
            if consumer_id in consumers:
                consumer = consumers[consumer_id]
                consumer.messages_received += received
                consumer.messages_acked += acked
                consumer.messages_rejected += rejected
                consumer.last_activity = time.time()
                break


# =============================================================================
# MESSAGE ROUTER
# =============================================================================

class MessageRouter:
    """Routes messages to consumers."""

    def __init__(
        self,
        topic_manager: TopicManager,
        consumer_manager: ConsumerGroupManager,
        message_store: MessageStore,
        dead_letter_queue: DeadLetterQueue
    ):
        self._topics = topic_manager
        self._consumers = consumer_manager
        self._store = message_store
        self._dlq = dead_letter_queue

    async def route(self, message: Message) -> bool:
        """Route message to consumers."""
        subscriptions = self._topics.get_subscriptions(message.topic)

        if not subscriptions:
            return False

        success = False

        for subscription in subscriptions:
            # Filter message
            if not self._matches_filter(message, subscription):
                continue

            consumer = self._consumers.get_active_consumer(
                message.topic,
                subscription.consumer_group,
                message.key
            )

            if not consumer:
                continue

            # Deliver message
            delivered = await self._deliver(message, consumer, subscription)

            if delivered:
                success = True

        return success

    def _matches_filter(
        self,
        message: Message,
        subscription: Subscription
    ) -> bool:
        """Check if message matches filter."""
        if not subscription.filter_expression:
            return True

        # Simple header-based filtering
        # Format: "header.key=value"
        if subscription.filter_expression.startswith("header."):
            parts = subscription.filter_expression[7:].split("=")

            if len(parts) == 2:
                key, value = parts
                return message.headers.get(key) == value

        return True

    async def _deliver(
        self,
        message: Message,
        consumer: Consumer,
        subscription: Subscription
    ) -> bool:
        """Deliver message to consumer."""
        message.status = MessageStatus.DELIVERED
        self._consumers.update_consumer_stats(consumer.consumer_id, received=1)

        try:
            if subscription.ack_mode == AckMode.AUTO:
                # Auto-ack before delivery
                success = await consumer.handler(message)

                if success:
                    message.status = MessageStatus.ACKNOWLEDGED
                    self._consumers.update_consumer_stats(
                        consumer.consumer_id, acked=1
                    )
                else:
                    await self._handle_rejection(message, consumer, subscription)

                return success
            else:
                # Manual ack - just deliver
                success = await consumer.handler(message)
                return success

        except Exception as e:
            logger.error(f"Delivery error: {e}")
            await self._handle_rejection(message, consumer, subscription)
            return False

    async def _handle_rejection(
        self,
        message: Message,
        consumer: Consumer,
        subscription: Subscription
    ) -> None:
        """Handle rejected message."""
        self._consumers.update_consumer_stats(consumer.consumer_id, rejected=1)

        if message.retry_count >= subscription.max_redelivery:
            self._dlq.add(message, "Max retries exceeded")
        else:
            self._store.requeue(message)


# =============================================================================
# MESSAGE BROKER
# =============================================================================

class MessageBroker:
    """
    Comprehensive Message Broker for BAEL.
    """

    def __init__(self, delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE):
        self.delivery_mode = delivery_mode

        self._topic_manager = TopicManager()
        self._consumer_manager = ConsumerGroupManager()
        self._message_store = MessageStore()
        self._dead_letter_queue = DeadLetterQueue()

        self._router = MessageRouter(
            self._topic_manager,
            self._consumer_manager,
            self._message_store,
            self._dead_letter_queue
        )

        self._running = False
        self._dispatcher_task: Optional[asyncio.Task] = None
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # TOPIC MANAGEMENT
    # -------------------------------------------------------------------------

    def create_topic(
        self,
        name: str,
        partitions: int = 1,
        retention_hours: int = 24
    ) -> bool:
        """Create a topic."""
        return self._topic_manager.create_topic(
            name, partitions, retention_hours
        )

    def delete_topic(self, name: str) -> bool:
        """Delete a topic."""
        return self._topic_manager.delete_topic(name)

    def list_topics(self) -> List[str]:
        """List all topics."""
        return self._topic_manager.list_topics()

    # -------------------------------------------------------------------------
    # PUBLISHING
    # -------------------------------------------------------------------------

    async def publish(
        self,
        topic: str,
        payload: Any,
        key: str = "",
        headers: Dict[str, str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl: float = 0.0,
        correlation_id: str = "",
        reply_to: str = ""
    ) -> Optional[str]:
        """Publish a message."""
        # Auto-create topic if needed
        if not self._topic_manager.topic_exists(topic):
            self.create_topic(topic)

        message = Message(
            topic=topic,
            key=key,
            payload=payload,
            headers=headers or {},
            priority=priority,
            ttl=ttl,
            correlation_id=correlation_id,
            reply_to=reply_to
        )

        if not self._message_store.store(message):
            return None

        self._stats["published"] += 1

        # Immediate routing for at-most-once
        if self.delivery_mode == DeliveryMode.AT_MOST_ONCE:
            await self._router.route(message)

        return message.message_id

    async def publish_batch(
        self,
        topic: str,
        messages: List[Dict[str, Any]]
    ) -> List[str]:
        """Publish multiple messages."""
        message_ids = []

        for msg_data in messages:
            msg_id = await self.publish(
                topic=topic,
                payload=msg_data.get("payload"),
                key=msg_data.get("key", ""),
                headers=msg_data.get("headers"),
                priority=msg_data.get("priority", MessagePriority.NORMAL),
                ttl=msg_data.get("ttl", 0.0)
            )

            if msg_id:
                message_ids.append(msg_id)

        return message_ids

    # -------------------------------------------------------------------------
    # SUBSCRIBING
    # -------------------------------------------------------------------------

    def subscribe(
        self,
        topic: str,
        handler: Callable[[Message], Awaitable[bool]],
        group: str = "default",
        sub_type: SubscriptionType = SubscriptionType.SHARED,
        ack_mode: AckMode = AckMode.AUTO,
        filter_expression: str = ""
    ) -> Tuple[str, str]:
        """Subscribe to a topic."""
        # Auto-create topic if needed
        if not self._topic_manager.topic_exists(topic):
            self.create_topic(topic)

        subscription = Subscription(
            topic=topic,
            consumer_group=group,
            sub_type=sub_type,
            ack_mode=ack_mode,
            filter_expression=filter_expression
        )

        self._topic_manager.add_subscription(subscription)
        consumer = self._consumer_manager.register_consumer(subscription, handler)

        return subscription.subscription_id, consumer.consumer_id

    def unsubscribe(
        self,
        topic: str,
        subscription_id: str,
        consumer_id: str
    ) -> bool:
        """Unsubscribe from a topic."""
        self._topic_manager.remove_subscription(topic, subscription_id)
        return self._consumer_manager.unregister_consumer(consumer_id)

    # -------------------------------------------------------------------------
    # ACKNOWLEDGMENT
    # -------------------------------------------------------------------------

    def ack(self, topic: str, message_id: str) -> bool:
        """Acknowledge a message."""
        result = self._message_store.update_status(
            topic, message_id, MessageStatus.ACKNOWLEDGED
        )

        if result:
            self._stats["acknowledged"] += 1

        return result

    def nack(
        self,
        topic: str,
        message_id: str,
        requeue: bool = True
    ) -> bool:
        """Negative acknowledge a message."""
        message = self._message_store.get(topic, message_id)

        if not message:
            return False

        if requeue and message.retry_count < message.max_retries:
            self._message_store.requeue(message)
        else:
            self._dead_letter_queue.add(message, "Negative acknowledgment")

        self._stats["rejected"] += 1

        return True

    # -------------------------------------------------------------------------
    # DISPATCHER
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the message dispatcher."""
        self._running = True
        self._dispatcher_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        """Stop the message dispatcher."""
        self._running = False

        if self._dispatcher_task:
            self._dispatcher_task.cancel()

            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass

    async def _dispatch_loop(self) -> None:
        """Main dispatch loop."""
        while self._running:
            try:
                for topic in self._topic_manager.list_topics():
                    messages = self._message_store.get_pending(topic, count=10)

                    for message in messages:
                        await self._router.route(message)
                        self._stats["delivered"] += 1

                await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"Dispatch error: {e}")
                await asyncio.sleep(1.0)

    # -------------------------------------------------------------------------
    # DEAD LETTER QUEUE
    # -------------------------------------------------------------------------

    def get_dead_letters(
        self,
        topic: str = None,
        limit: int = 100
    ) -> List[DeadLetterEntry]:
        """Get dead letter entries."""
        return self._dead_letter_queue.list_entries(topic, limit)

    async def reprocess_dead_letter(self, message_id: str) -> bool:
        """Reprocess a dead letter."""
        message = self._dead_letter_queue.reprocess(message_id)

        if message:
            self._message_store.store(message)
            return True

        return False

    def purge_dead_letters(self, topic: str = None) -> int:
        """Purge dead letters."""
        entries = self._dead_letter_queue.list_entries(topic)

        count = 0
        for entry in entries:
            if self._dead_letter_queue.remove(entry.message.message_id):
                count += 1

        return count

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_topic_stats(self, topic: str) -> QueueStats:
        """Get statistics for a topic."""
        store_stats = self._message_store.get_stats(topic)
        consumers = self._consumer_manager.get_consumers(topic)

        return QueueStats(
            topic=topic,
            messages_pending=store_stats.get("pending", 0),
            messages_delivered=store_stats.get("delivered", 0),
            messages_acknowledged=store_stats.get("acknowledged", 0),
            messages_dead_lettered=store_stats.get("dead_lettered", 0),
            consumers=len(consumers)
        )

    def get_broker_stats(self) -> Dict[str, Any]:
        """Get overall broker statistics."""
        return {
            "topics": len(self._topic_manager.list_topics()),
            "dead_letters": self._dead_letter_queue.size,
            "published": self._stats["published"],
            "delivered": self._stats["delivered"],
            "acknowledged": self._stats["acknowledged"],
            "rejected": self._stats["rejected"]
        }

    # -------------------------------------------------------------------------
    # REQUEST-REPLY
    # -------------------------------------------------------------------------

    async def request(
        self,
        topic: str,
        payload: Any,
        timeout: float = 30.0
    ) -> Optional[Message]:
        """Send request and wait for reply."""
        correlation_id = str(uuid.uuid4())
        reply_topic = f"_reply_{correlation_id}"

        response_future: asyncio.Future = asyncio.Future()

        async def response_handler(msg: Message) -> bool:
            if msg.correlation_id == correlation_id:
                response_future.set_result(msg)
            return True

        # Subscribe to reply topic
        self.create_topic(reply_topic)
        sub_id, consumer_id = self.subscribe(reply_topic, response_handler)

        try:
            # Publish request
            await self.publish(
                topic=topic,
                payload=payload,
                correlation_id=correlation_id,
                reply_to=reply_topic
            )

            # Wait for response
            response = await asyncio.wait_for(
                response_future,
                timeout=timeout
            )

            return response

        except asyncio.TimeoutError:
            return None

        finally:
            self.unsubscribe(reply_topic, sub_id, consumer_id)
            self.delete_topic(reply_topic)

    async def reply(
        self,
        original: Message,
        payload: Any
    ) -> Optional[str]:
        """Reply to a request."""
        if not original.reply_to:
            return None

        return await self.publish(
            topic=original.reply_to,
            payload=payload,
            correlation_id=original.correlation_id
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Message Broker System."""
    print("=" * 70)
    print("BAEL - MESSAGE BROKER SYSTEM DEMO")
    print("Comprehensive Message Broker")
    print("=" * 70)
    print()

    broker = MessageBroker(DeliveryMode.AT_LEAST_ONCE)

    # 1. Create Topics
    print("1. CREATE TOPICS:")
    print("-" * 40)

    broker.create_topic("orders", partitions=3)
    broker.create_topic("notifications", partitions=1)
    broker.create_topic("events", partitions=2)

    for topic in broker.list_topics():
        print(f"   Created topic: {topic}")
    print()

    # 2. Subscribe to Topics
    print("2. SUBSCRIBE TO TOPICS:")
    print("-" * 40)

    received_messages = []

    async def order_handler(msg: Message) -> bool:
        received_messages.append(msg)
        print(f"   [ORDER] Received: {msg.payload}")
        return True

    async def notification_handler(msg: Message) -> bool:
        print(f"   [NOTIFY] Received: {msg.payload}")
        return True

    sub1_id, consumer1_id = broker.subscribe(
        "orders",
        order_handler,
        group="order-processors"
    )
    print(f"   Subscribed to orders: {sub1_id[:8]}...")

    sub2_id, consumer2_id = broker.subscribe(
        "notifications",
        notification_handler,
        group="notifiers"
    )
    print(f"   Subscribed to notifications: {sub2_id[:8]}...")
    print()

    # 3. Start Broker
    print("3. START BROKER:")
    print("-" * 40)
    await broker.start()
    print("   Broker started")
    print()

    # 4. Publish Messages
    print("4. PUBLISH MESSAGES:")
    print("-" * 40)

    msg_id1 = await broker.publish(
        "orders",
        {"order_id": "ORD-001", "amount": 99.99},
        key="customer-123",
        priority=MessagePriority.HIGH
    )
    print(f"   Published order 1: {msg_id1[:8]}...")

    msg_id2 = await broker.publish(
        "orders",
        {"order_id": "ORD-002", "amount": 149.99},
        key="customer-456",
        headers={"type": "premium"}
    )
    print(f"   Published order 2: {msg_id2[:8]}...")

    msg_id3 = await broker.publish(
        "notifications",
        {"user": "john", "message": "Order shipped!"}
    )
    print(f"   Published notification: {msg_id3[:8]}...")
    print()

    # Wait for processing
    await asyncio.sleep(0.2)

    # 5. Batch Publish
    print("5. BATCH PUBLISH:")
    print("-" * 40)

    batch_ids = await broker.publish_batch("events", [
        {"payload": {"event": "click", "page": "/home"}},
        {"payload": {"event": "scroll", "page": "/products"}},
        {"payload": {"event": "click", "page": "/checkout"}}
    ])
    print(f"   Published {len(batch_ids)} events")
    print()

    # 6. Message with TTL
    print("6. MESSAGE WITH TTL:")
    print("-" * 40)

    msg_id = await broker.publish(
        "notifications",
        {"alert": "Flash sale!"},
        ttl=60.0  # 1 minute
    )
    print(f"   Published with 60s TTL: {msg_id[:8]}...")
    print()

    # Wait for processing
    await asyncio.sleep(0.2)

    # 7. Topic Stats
    print("7. TOPIC STATS:")
    print("-" * 40)

    stats = broker.get_topic_stats("orders")
    print(f"   Topic: {stats.topic}")
    print(f"   Consumers: {stats.consumers}")
    print(f"   Messages delivered: {stats.messages_delivered}")
    print()

    # 8. Broker Stats
    print("8. BROKER STATS:")
    print("-" * 40)

    broker_stats = broker.get_broker_stats()
    print(f"   Topics: {broker_stats['topics']}")
    print(f"   Published: {broker_stats['published']}")
    print(f"   Delivered: {broker_stats['delivered']}")
    print()

    # 9. Filter Subscription
    print("9. FILTER SUBSCRIPTION:")
    print("-" * 40)

    async def premium_handler(msg: Message) -> bool:
        print(f"   [PREMIUM] Received: {msg.payload}")
        return True

    sub3_id, consumer3_id = broker.subscribe(
        "orders",
        premium_handler,
        group="premium-processors",
        filter_expression="header.type=premium"
    )
    print("   Subscribed with filter: header.type=premium")
    print()

    # 10. Priority Messages
    print("10. PRIORITY MESSAGES:")
    print("-" * 40)

    await broker.publish(
        "orders",
        {"priority_order": "LOW"},
        priority=MessagePriority.LOW
    )

    await broker.publish(
        "orders",
        {"priority_order": "URGENT"},
        priority=MessagePriority.URGENT
    )

    await broker.publish(
        "orders",
        {"priority_order": "NORMAL"},
        priority=MessagePriority.NORMAL
    )

    print("   Published messages with different priorities")

    await asyncio.sleep(0.2)
    print()

    # 11. Dead Letter Queue
    print("11. DEAD LETTER QUEUE:")
    print("-" * 40)

    # Simulate a failing handler
    async def failing_handler(msg: Message) -> bool:
        return False  # Always fail

    sub4_id, consumer4_id = broker.subscribe(
        "fail-topic",
        failing_handler,
        ack_mode=AckMode.AUTO
    )

    await broker.publish("fail-topic", {"will_fail": True})
    await asyncio.sleep(0.2)

    dead_letters = broker.get_dead_letters()
    print(f"   Dead letters count: {len(dead_letters)}")
    print()

    # 12. Unsubscribe
    print("12. UNSUBSCRIBE:")
    print("-" * 40)

    broker.unsubscribe("orders", sub1_id, consumer1_id)
    print("   Unsubscribed from orders")
    print()

    # Stop broker
    await broker.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Message Broker System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
