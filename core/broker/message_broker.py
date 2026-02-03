#!/usr/bin/env python3
"""
BAEL - Message Broker
Comprehensive message broker and pub/sub system.

Features:
- Topic-based publish/subscribe
- Message queues
- Request/reply patterns
- Message routing
- Dead letter queues
- Message persistence
- Acknowledgment handling
- Consumer groups
- Message filtering
- Priority queues
- TTL support
- Retry policies
"""

import asyncio
import heapq
import json
import logging
import time
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

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
    DEAD_LETTER = "dead_letter"


class DeliveryMode(Enum):
    """Message delivery mode."""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class AckMode(Enum):
    """Acknowledgment mode."""
    AUTO = "auto"
    MANUAL = "manual"
    NONE = "none"


class SubscriptionType(Enum):
    """Subscription type."""
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    FAILOVER = "failover"
    KEY_SHARED = "key_shared"


class RetryPolicy(Enum):
    """Retry policy."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Message:
    """Message in the broker."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 0-9, higher = more priority
    timestamp: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None  # seconds
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None
    delivery_count: int = 0
    status: MessageStatus = MessageStatus.PENDING

    def is_expired(self) -> bool:
        """Check if message is expired."""
        if self.ttl is None:
            return False
        expiry = self.timestamp + timedelta(seconds=self.ttl)
        return datetime.now() > expiry

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "topic": self.topic,
            "body": self.body,
            "headers": self.headers,
            "properties": self.properties,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
            "reply_to": self.reply_to,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        """Create from dictionary."""
        msg = cls(
            id=data.get("id", str(uuid.uuid4())),
            topic=data.get("topic", ""),
            body=data.get("body"),
            headers=data.get("headers", {}),
            properties=data.get("properties", {}),
            priority=data.get("priority", 5),
            ttl=data.get("ttl"),
            reply_to=data.get("reply_to"),
            correlation_id=data.get("correlation_id"),
        )
        if "timestamp" in data:
            msg.timestamp = datetime.fromisoformat(data["timestamp"])
        return msg


@dataclass
class Subscription:
    """Topic subscription."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    consumer_id: str = ""
    filter_expression: Optional[str] = None
    subscription_type: SubscriptionType = SubscriptionType.SHARED
    ack_mode: AckMode = AckMode.AUTO
    max_redeliveries: int = 3
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Consumer:
    """Message consumer."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    handler: Optional[Callable] = None
    active: bool = True
    subscriptions: List[str] = field(default_factory=list)
    messages_received: int = 0
    messages_acknowledged: int = 0


@dataclass
class Queue:
    """Message queue."""
    name: str
    max_size: int = 10000
    dead_letter_queue: Optional[str] = None
    retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds


@dataclass
class BrokerStats:
    """Broker statistics."""
    topics: int = 0
    queues: int = 0
    consumers: int = 0
    subscriptions: int = 0
    messages_published: int = 0
    messages_delivered: int = 0
    messages_acknowledged: int = 0
    messages_dead_lettered: int = 0
    pending_messages: int = 0


# =============================================================================
# TOPIC
# =============================================================================

class Topic:
    """Topic for publish/subscribe."""

    def __init__(self, name: str):
        self.name = name
        self.subscriptions: Dict[str, Subscription] = {}
        self.messages: deque = deque(maxlen=10000)
        self.message_count = 0
        self.created_at = datetime.now()

    def add_subscription(self, subscription: Subscription) -> None:
        """Add subscription."""
        self.subscriptions[subscription.id] = subscription

    def remove_subscription(self, subscription_id: str) -> bool:
        """Remove subscription."""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            return True
        return False

    def publish(self, message: Message) -> None:
        """Publish message to topic."""
        message.topic = self.name
        self.messages.append(message)
        self.message_count += 1


# =============================================================================
# MESSAGE QUEUE
# =============================================================================

class MessageQueue:
    """Priority message queue."""

    def __init__(self, config: Queue):
        self.config = config
        self._queue: List[Tuple[int, float, Message]] = []  # (priority, timestamp, message)
        self._pending: Dict[str, Message] = {}  # message_id -> message
        self._counter = 0

    def push(self, message: Message) -> bool:
        """Push message to queue."""
        if len(self._queue) >= self.config.max_size:
            return False

        # Priority queue: lower number = higher priority
        # Negate priority so higher priority comes first
        priority = -message.priority
        timestamp = time.time()

        heapq.heappush(self._queue, (priority, timestamp, message))
        self._counter += 1

        return True

    def pop(self) -> Optional[Message]:
        """Pop highest priority message."""
        while self._queue:
            _, _, message = heapq.heappop(self._queue)

            if message.is_expired():
                message.status = MessageStatus.EXPIRED
                continue

            message.delivery_count += 1
            message.status = MessageStatus.DELIVERED
            self._pending[message.id] = message

            return message

        return None

    def peek(self) -> Optional[Message]:
        """Peek at highest priority message."""
        if not self._queue:
            return None

        _, _, message = self._queue[0]
        return message

    def acknowledge(self, message_id: str) -> bool:
        """Acknowledge message."""
        if message_id in self._pending:
            message = self._pending.pop(message_id)
            message.status = MessageStatus.ACKNOWLEDGED
            return True
        return False

    def reject(self, message_id: str, requeue: bool = True) -> bool:
        """Reject message."""
        if message_id not in self._pending:
            return False

        message = self._pending.pop(message_id)
        message.status = MessageStatus.REJECTED

        if requeue and message.delivery_count < self.config.max_retries:
            self.push(message)
        else:
            # Send to dead letter queue
            message.status = MessageStatus.DEAD_LETTER

        return True

    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)

    def pending_count(self) -> int:
        """Get pending message count."""
        return len(self._pending)


# =============================================================================
# FILTER
# =============================================================================

class MessageFilter:
    """Message filter using simple expressions."""

    def __init__(self, expression: str):
        self.expression = expression
        self._parsed = self._parse(expression)

    def _parse(self, expression: str) -> List[Tuple[str, str, Any]]:
        """Parse filter expression."""
        conditions = []

        if not expression:
            return conditions

        # Simple format: "key=value AND key2>value2"
        parts = expression.split(" AND ")

        for part in parts:
            part = part.strip()

            for op in [">=", "<=", "!=", "=", ">", "<"]:
                if op in part:
                    key, value = part.split(op, 1)
                    conditions.append((key.strip(), op, value.strip()))
                    break

        return conditions

    def matches(self, message: Message) -> bool:
        """Check if message matches filter."""
        if not self._parsed:
            return True

        for key, op, value in self._parsed:
            # Check headers first, then properties
            msg_value = message.headers.get(key)
            if msg_value is None:
                msg_value = message.properties.get(key)

            if msg_value is None:
                return False

            # Type conversion
            try:
                if isinstance(msg_value, (int, float)):
                    value = type(msg_value)(value)
            except:
                pass

            if op == "=" and msg_value != value:
                return False
            elif op == "!=" and msg_value == value:
                return False
            elif op == ">" and not (msg_value > value):
                return False
            elif op == "<" and not (msg_value < value):
                return False
            elif op == ">=" and not (msg_value >= value):
                return False
            elif op == "<=" and not (msg_value <= value):
                return False

        return True


# =============================================================================
# CONSUMER GROUP
# =============================================================================

class ConsumerGroup:
    """Group of consumers for load balancing."""

    def __init__(self, name: str, subscription_type: SubscriptionType = SubscriptionType.SHARED):
        self.name = name
        self.subscription_type = subscription_type
        self.consumers: Dict[str, Consumer] = {}
        self._round_robin_index = 0
        self._key_assignments: Dict[str, str] = {}  # key -> consumer_id

    def add_consumer(self, consumer: Consumer) -> None:
        """Add consumer to group."""
        self.consumers[consumer.id] = consumer

    def remove_consumer(self, consumer_id: str) -> None:
        """Remove consumer from group."""
        if consumer_id in self.consumers:
            del self.consumers[consumer_id]
            # Reassign keys
            self._key_assignments = {k: v for k, v in self._key_assignments.items() if v != consumer_id}

    def get_consumer(self, message: Message) -> Optional[Consumer]:
        """Get consumer for message based on subscription type."""
        active_consumers = [c for c in self.consumers.values() if c.active]

        if not active_consumers:
            return None

        if self.subscription_type == SubscriptionType.EXCLUSIVE:
            return active_consumers[0] if active_consumers else None

        elif self.subscription_type == SubscriptionType.SHARED:
            # Round-robin
            self._round_robin_index = (self._round_robin_index + 1) % len(active_consumers)
            return active_consumers[self._round_robin_index]

        elif self.subscription_type == SubscriptionType.FAILOVER:
            return active_consumers[0]

        elif self.subscription_type == SubscriptionType.KEY_SHARED:
            # Use routing key from properties or message id
            key = message.properties.get("routing_key", message.id)

            if key not in self._key_assignments:
                # Assign to consumer with least keys
                min_count = float('inf')
                target = None

                for consumer in active_consumers:
                    count = sum(1 for v in self._key_assignments.values() if v == consumer.id)
                    if count < min_count:
                        min_count = count
                        target = consumer

                if target:
                    self._key_assignments[key] = target.id

            consumer_id = self._key_assignments.get(key)
            return self.consumers.get(consumer_id)

        return None


# =============================================================================
# MESSAGE BROKER
# =============================================================================

class MessageBroker:
    """
    Comprehensive Message Broker for BAEL.

    Provides publish/subscribe messaging with queues and consumer groups.
    """

    def __init__(self):
        self._topics: Dict[str, Topic] = {}
        self._queues: Dict[str, MessageQueue] = {}
        self._consumers: Dict[str, Consumer] = {}
        self._consumer_groups: Dict[str, ConsumerGroup] = {}
        self._dead_letter_queue: MessageQueue = MessageQueue(Queue("__dlq__", max_size=100000))

        self._handlers: Dict[str, List[Callable]] = defaultdict(list)  # topic -> handlers
        self._pending_replies: Dict[str, asyncio.Future] = {}

        self._stats = BrokerStats()
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None

    # -------------------------------------------------------------------------
    # TOPIC MANAGEMENT
    # -------------------------------------------------------------------------

    def create_topic(self, name: str) -> Topic:
        """Create a topic."""
        if name not in self._topics:
            self._topics[name] = Topic(name)
            self._stats.topics += 1
        return self._topics[name]

    def get_topic(self, name: str) -> Optional[Topic]:
        """Get a topic."""
        return self._topics.get(name)

    def delete_topic(self, name: str) -> bool:
        """Delete a topic."""
        if name in self._topics:
            del self._topics[name]
            self._stats.topics -= 1
            return True
        return False

    def list_topics(self) -> List[str]:
        """List all topics."""
        return list(self._topics.keys())

    # -------------------------------------------------------------------------
    # QUEUE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_queue(self, config: Queue) -> MessageQueue:
        """Create a queue."""
        if config.name not in self._queues:
            self._queues[config.name] = MessageQueue(config)
            self._stats.queues += 1
        return self._queues[config.name]

    def get_queue(self, name: str) -> Optional[MessageQueue]:
        """Get a queue."""
        return self._queues.get(name)

    def delete_queue(self, name: str) -> bool:
        """Delete a queue."""
        if name in self._queues:
            del self._queues[name]
            self._stats.queues -= 1
            return True
        return False

    # -------------------------------------------------------------------------
    # CONSUMER MANAGEMENT
    # -------------------------------------------------------------------------

    def create_consumer(
        self,
        name: str,
        handler: Optional[Callable] = None
    ) -> Consumer:
        """Create a consumer."""
        consumer = Consumer(name=name, handler=handler)
        self._consumers[consumer.id] = consumer
        self._stats.consumers += 1
        return consumer

    def remove_consumer(self, consumer_id: str) -> bool:
        """Remove a consumer."""
        if consumer_id in self._consumers:
            del self._consumers[consumer_id]
            self._stats.consumers -= 1
            return True
        return False

    # -------------------------------------------------------------------------
    # CONSUMER GROUPS
    # -------------------------------------------------------------------------

    def create_consumer_group(
        self,
        name: str,
        subscription_type: SubscriptionType = SubscriptionType.SHARED
    ) -> ConsumerGroup:
        """Create a consumer group."""
        if name not in self._consumer_groups:
            self._consumer_groups[name] = ConsumerGroup(name, subscription_type)
        return self._consumer_groups[name]

    def add_to_group(self, group_name: str, consumer: Consumer) -> None:
        """Add consumer to group."""
        if group_name in self._consumer_groups:
            self._consumer_groups[group_name].add_consumer(consumer)

    # -------------------------------------------------------------------------
    # SUBSCRIPTION
    # -------------------------------------------------------------------------

    def subscribe(
        self,
        topic_name: str,
        consumer_id: str,
        filter_expression: Optional[str] = None,
        subscription_type: SubscriptionType = SubscriptionType.SHARED,
        ack_mode: AckMode = AckMode.AUTO
    ) -> Subscription:
        """Subscribe to a topic."""
        topic = self.create_topic(topic_name)

        subscription = Subscription(
            topic=topic_name,
            consumer_id=consumer_id,
            filter_expression=filter_expression,
            subscription_type=subscription_type,
            ack_mode=ack_mode
        )

        topic.add_subscription(subscription)

        if consumer_id in self._consumers:
            self._consumers[consumer_id].subscriptions.append(subscription.id)

        self._stats.subscriptions += 1
        return subscription

    def unsubscribe(self, topic_name: str, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        topic = self._topics.get(topic_name)
        if topic:
            if topic.remove_subscription(subscription_id):
                self._stats.subscriptions -= 1
                return True
        return False

    # -------------------------------------------------------------------------
    # PUBLISHING
    # -------------------------------------------------------------------------

    async def publish(
        self,
        topic_name: str,
        body: Any,
        headers: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        ttl: Optional[int] = None
    ) -> Message:
        """Publish a message to a topic."""
        topic = self.create_topic(topic_name)

        message = Message(
            topic=topic_name,
            body=body,
            headers=headers or {},
            properties=properties or {},
            priority=priority,
            ttl=ttl
        )

        topic.publish(message)
        self._stats.messages_published += 1

        # Dispatch to subscribers
        await self._dispatch_message(topic, message)

        return message

    async def publish_to_queue(
        self,
        queue_name: str,
        body: Any,
        headers: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        ttl: Optional[int] = None
    ) -> Optional[Message]:
        """Publish message to a queue."""
        queue = self._queues.get(queue_name)
        if not queue:
            return None

        message = Message(
            body=body,
            headers=headers or {},
            properties=properties or {},
            priority=priority,
            ttl=ttl
        )

        if queue.push(message):
            self._stats.messages_published += 1
            return message

        return None

    # -------------------------------------------------------------------------
    # REQUEST/REPLY
    # -------------------------------------------------------------------------

    async def request(
        self,
        topic_name: str,
        body: Any,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Message]:
        """Send request and wait for reply."""
        # Create reply topic
        reply_topic = f"__reply__.{uuid.uuid4().hex[:8]}"
        correlation_id = str(uuid.uuid4())

        # Set up reply handler
        reply_future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_replies[correlation_id] = reply_future

        # Subscribe to reply topic
        async def reply_handler(message: Message):
            if message.correlation_id == correlation_id:
                if correlation_id in self._pending_replies:
                    self._pending_replies[correlation_id].set_result(message)

        self.on(reply_topic, reply_handler)

        try:
            # Publish request
            await self.publish(
                topic_name,
                body,
                headers=headers,
                properties={"reply_to": reply_topic, "correlation_id": correlation_id}
            )

            # Wait for reply
            reply = await asyncio.wait_for(reply_future, timeout=timeout)
            return reply

        except asyncio.TimeoutError:
            return None

        finally:
            # Cleanup
            self._pending_replies.pop(correlation_id, None)
            if reply_topic in self._handlers:
                self._handlers[reply_topic].remove(reply_handler)

    async def reply(self, original_message: Message, body: Any) -> Optional[Message]:
        """Reply to a request message."""
        reply_to = original_message.properties.get("reply_to")
        correlation_id = original_message.properties.get("correlation_id")

        if not reply_to:
            return None

        return await self.publish(
            reply_to,
            body,
            properties={"correlation_id": correlation_id}
        )

    # -------------------------------------------------------------------------
    # HANDLER REGISTRATION
    # -------------------------------------------------------------------------

    def on(self, topic_name: str, handler: Callable) -> None:
        """Register handler for topic."""
        self._handlers[topic_name].append(handler)

    def off(self, topic_name: str, handler: Callable) -> None:
        """Unregister handler for topic."""
        if topic_name in self._handlers:
            try:
                self._handlers[topic_name].remove(handler)
            except ValueError:
                pass

    # -------------------------------------------------------------------------
    # MESSAGE DISPATCH
    # -------------------------------------------------------------------------

    async def _dispatch_message(self, topic: Topic, message: Message) -> None:
        """Dispatch message to subscribers and handlers."""
        # Call registered handlers
        for handler in self._handlers.get(topic.name, []):
            try:
                result = handler(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Handler error for topic {topic.name}: {e}")

        # Dispatch to subscribed consumers
        for subscription in topic.subscriptions.values():
            # Apply filter
            if subscription.filter_expression:
                msg_filter = MessageFilter(subscription.filter_expression)
                if not msg_filter.matches(message):
                    continue

            consumer = self._consumers.get(subscription.consumer_id)
            if consumer and consumer.handler and consumer.active:
                try:
                    result = consumer.handler(message)
                    if asyncio.iscoroutine(result):
                        await result

                    consumer.messages_received += 1
                    self._stats.messages_delivered += 1

                    if subscription.ack_mode == AckMode.AUTO:
                        message.status = MessageStatus.ACKNOWLEDGED
                        consumer.messages_acknowledged += 1
                        self._stats.messages_acknowledged += 1

                except Exception as e:
                    logger.error(f"Consumer error: {e}")
                    if message.delivery_count >= subscription.max_redeliveries:
                        await self._send_to_dlq(message)

    async def _send_to_dlq(self, message: Message) -> None:
        """Send message to dead letter queue."""
        message.status = MessageStatus.DEAD_LETTER
        self._dead_letter_queue.push(message)
        self._stats.messages_dead_lettered += 1

    # -------------------------------------------------------------------------
    # CONSUMING
    # -------------------------------------------------------------------------

    async def consume(
        self,
        queue_name: str,
        handler: Callable,
        batch_size: int = 1,
        wait_timeout: float = 1.0
    ) -> None:
        """Consume messages from queue."""
        queue = self._queues.get(queue_name)
        if not queue:
            return

        while True:
            messages = []

            for _ in range(batch_size):
                message = queue.pop()
                if message:
                    messages.append(message)
                else:
                    break

            if messages:
                for message in messages:
                    try:
                        result = handler(message)
                        if asyncio.iscoroutine(result):
                            await result

                        queue.acknowledge(message.id)
                        self._stats.messages_delivered += 1
                        self._stats.messages_acknowledged += 1

                    except Exception as e:
                        logger.error(f"Consumer error: {e}")
                        queue.reject(message.id, requeue=True)
            else:
                await asyncio.sleep(wait_timeout)

    # -------------------------------------------------------------------------
    # ACKNOWLEDGMENT
    # -------------------------------------------------------------------------

    def acknowledge(self, queue_name: str, message_id: str) -> bool:
        """Manually acknowledge a message."""
        queue = self._queues.get(queue_name)
        if queue:
            if queue.acknowledge(message_id):
                self._stats.messages_acknowledged += 1
                return True
        return False

    def reject(
        self,
        queue_name: str,
        message_id: str,
        requeue: bool = True
    ) -> bool:
        """Reject a message."""
        queue = self._queues.get(queue_name)
        if queue:
            return queue.reject(message_id, requeue)
        return False

    # -------------------------------------------------------------------------
    # DEAD LETTER QUEUE
    # -------------------------------------------------------------------------

    def get_dead_letters(self, limit: int = 100) -> List[Message]:
        """Get messages from dead letter queue."""
        messages = []

        for _ in range(limit):
            message = self._dead_letter_queue.pop()
            if message:
                messages.append(message)
            else:
                break

        return messages

    def requeue_dead_letter(self, message_id: str, target_queue: str) -> bool:
        """Requeue a dead letter message."""
        # Find message in DLQ
        for priority, timestamp, message in self._dead_letter_queue._queue:
            if message.id == message_id:
                message.status = MessageStatus.PENDING
                message.delivery_count = 0

                queue = self._queues.get(target_queue)
                if queue:
                    return queue.push(message)

        return False

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> BrokerStats:
        """Get broker statistics."""
        self._stats.pending_messages = sum(
            q.size() + q.pending_count() for q in self._queues.values()
        )
        return self._stats

    def get_queue_stats(self, queue_name: str) -> Dict[str, int]:
        """Get queue statistics."""
        queue = self._queues.get(queue_name)
        if not queue:
            return {}

        return {
            "size": queue.size(),
            "pending": queue.pending_count(),
            "total": queue._counter
        }

    def get_topic_stats(self, topic_name: str) -> Dict[str, Any]:
        """Get topic statistics."""
        topic = self._topics.get(topic_name)
        if not topic:
            return {}

        return {
            "name": topic.name,
            "subscriptions": len(topic.subscriptions),
            "message_count": topic.message_count,
            "created_at": topic.created_at.isoformat()
        }

    # -------------------------------------------------------------------------
    # PERSISTENCE
    # -------------------------------------------------------------------------

    def export_state(self) -> str:
        """Export broker state to JSON."""
        state = {
            "topics": {},
            "queues": {}
        }

        for name, topic in self._topics.items():
            state["topics"][name] = {
                "message_count": topic.message_count,
                "messages": [m.to_dict() for m in list(topic.messages)[-100:]]  # Last 100
            }

        for name, queue in self._queues.items():
            state["queues"][name] = {
                "config": {
                    "name": queue.config.name,
                    "max_size": queue.config.max_size,
                    "max_retries": queue.config.max_retries
                },
                "size": queue.size()
            }

        return json.dumps(state, indent=2, default=str)

    def clear(self) -> None:
        """Clear all topics and queues."""
        self._topics.clear()
        self._queues.clear()
        self._consumers.clear()
        self._consumer_groups.clear()
        self._handlers.clear()
        self._stats = BrokerStats()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Message Broker."""
    print("=" * 70)
    print("BAEL - MESSAGE BROKER DEMO")
    print("Comprehensive Pub/Sub and Queue System")
    print("=" * 70)
    print()

    broker = MessageBroker()

    # 1. Basic Pub/Sub
    print("1. BASIC PUB/SUB:")
    print("-" * 40)

    received_messages = []

    async def message_handler(message: Message):
        received_messages.append(message)
        print(f"   Received: {message.body}")

    broker.on("events", message_handler)

    await broker.publish("events", {"type": "user_login", "user": "alice"})
    await broker.publish("events", {"type": "user_logout", "user": "bob"})

    print(f"   Published 2 messages, received {len(received_messages)}")
    print()

    # 2. Message Queues
    print("2. MESSAGE QUEUES:")
    print("-" * 40)

    queue_config = Queue(name="tasks", max_size=1000, max_retries=3)
    broker.create_queue(queue_config)

    await broker.publish_to_queue("tasks", {"task": "process_data", "id": 1}, priority=5)
    await broker.publish_to_queue("tasks", {"task": "urgent_task", "id": 2}, priority=9)
    await broker.publish_to_queue("tasks", {"task": "low_priority", "id": 3}, priority=1)

    queue = broker.get_queue("tasks")
    print(f"   Queue size: {queue.size()}")

    # Pop in priority order
    msg = queue.pop()
    print(f"   First pop (priority {msg.priority}): {msg.body}")
    queue.acknowledge(msg.id)

    msg = queue.pop()
    print(f"   Second pop (priority {msg.priority}): {msg.body}")
    queue.acknowledge(msg.id)
    print()

    # 3. Consumer Groups
    print("3. CONSUMER GROUPS:")
    print("-" * 40)

    group = broker.create_consumer_group("workers", SubscriptionType.SHARED)

    consumer1 = broker.create_consumer("worker-1")
    consumer2 = broker.create_consumer("worker-2")

    group.add_consumer(consumer1)
    group.add_consumer(consumer2)

    print(f"   Created consumer group 'workers' with 2 consumers")

    # Get consumers for messages (round-robin)
    for i in range(4):
        msg = Message(body=f"task-{i}")
        selected = group.get_consumer(msg)
        print(f"   Task {i} -> {selected.name}")
    print()

    # 4. Subscriptions with Filters
    print("4. FILTERED SUBSCRIPTIONS:")
    print("-" * 40)

    filtered_messages = []

    async def priority_handler(message: Message):
        filtered_messages.append(message)

    consumer3 = broker.create_consumer("priority-consumer", priority_handler)

    broker.subscribe(
        "orders",
        consumer3.id,
        filter_expression="priority>=5",
        ack_mode=AckMode.AUTO
    )

    await broker.publish("orders", {"order_id": 1}, properties={"priority": 3})
    await broker.publish("orders", {"order_id": 2}, properties={"priority": 7})
    await broker.publish("orders", {"order_id": 3}, properties={"priority": 9})

    print(f"   Published 3 orders, filtered consumer received: {len(filtered_messages)}")
    for msg in filtered_messages:
        print(f"     Order {msg.body['order_id']} (priority {msg.properties.get('priority')})")
    print()

    # 5. Priority Queue
    print("5. PRIORITY QUEUE:")
    print("-" * 40)

    priority_queue = broker.create_queue(Queue("priority_tasks"))

    for i, (task, priority) in enumerate([
        ("backup", 2),
        ("alert", 9),
        ("log", 1),
        ("process", 5),
        ("notify", 7)
    ]):
        await broker.publish_to_queue("priority_tasks", {"task": task}, priority=priority)

    print("   Processing in priority order:")
    while priority_queue.size() > 0:
        msg = priority_queue.pop()
        print(f"     Priority {msg.priority}: {msg.body['task']}")
        priority_queue.acknowledge(msg.id)
    print()

    # 6. Message TTL
    print("6. MESSAGE TTL:")
    print("-" * 40)

    await broker.publish("temporary", {"data": "expires soon"}, ttl=1)
    print("   Published message with 1 second TTL")

    await asyncio.sleep(1.1)

    topic = broker.get_topic("temporary")
    msg = list(topic.messages)[-1]
    print(f"   Message expired: {msg.is_expired()}")
    print()

    # 7. Dead Letter Queue
    print("7. DEAD LETTER QUEUE:")
    print("-" * 40)

    dlq_queue = broker.create_queue(Queue("dlq_test", max_retries=2))

    await broker.publish_to_queue("dlq_test", {"will_fail": True})

    for i in range(3):
        msg = dlq_queue.pop()
        if msg:
            dlq_queue.reject(msg.id, requeue=True)
            print(f"   Rejected (attempt {msg.delivery_count})")

    dead_letters = broker.get_dead_letters(10)
    print(f"   Dead letters: {len(dead_letters)}")
    print()

    # 8. Message Headers
    print("8. MESSAGE HEADERS:")
    print("-" * 40)

    await broker.publish(
        "api_events",
        {"action": "create"},
        headers={
            "Content-Type": "application/json",
            "X-Request-Id": "abc123",
            "Authorization": "Bearer token"
        }
    )

    topic = broker.get_topic("api_events")
    msg = list(topic.messages)[-1]
    print(f"   Headers: {msg.headers}")
    print()

    # 9. Multiple Topics
    print("9. MULTIPLE TOPICS:")
    print("-" * 40)

    topics = ["users", "orders", "payments", "notifications", "logs"]

    for topic_name in topics:
        broker.create_topic(topic_name)
        await broker.publish(topic_name, {"event": f"{topic_name}_event"})

    print(f"   Created {len(topics)} topics")
    print(f"   Topics: {broker.list_topics()}")
    print()

    # 10. Statistics
    print("10. BROKER STATISTICS:")
    print("-" * 40)

    stats = broker.get_stats()
    print(f"   Topics: {stats.topics}")
    print(f"   Queues: {stats.queues}")
    print(f"   Consumers: {stats.consumers}")
    print(f"   Messages published: {stats.messages_published}")
    print(f"   Messages delivered: {stats.messages_delivered}")
    print(f"   Messages acknowledged: {stats.messages_acknowledged}")
    print(f"   Dead letters: {stats.messages_dead_lettered}")
    print()

    # 11. Queue Statistics
    print("11. QUEUE STATISTICS:")
    print("-" * 40)

    broker.create_queue(Queue("test_queue"))
    for i in range(5):
        await broker.publish_to_queue("test_queue", {"item": i})

    queue_stats = broker.get_queue_stats("test_queue")
    print(f"   Queue 'test_queue': {queue_stats}")
    print()

    # 12. Topic Statistics
    print("12. TOPIC STATISTICS:")
    print("-" * 40)

    topic_stats = broker.get_topic_stats("events")
    print(f"   Topic 'events':")
    for key, value in topic_stats.items():
        print(f"     {key}: {value}")
    print()

    # 13. Export State
    print("13. EXPORT STATE:")
    print("-" * 40)

    state = broker.export_state()
    print(f"   Exported state ({len(state)} chars)")
    print(f"   Preview: {state[:100]}...")
    print()

    # 14. Unsubscribe
    print("14. UNSUBSCRIBE:")
    print("-" * 40)

    topic = broker.get_topic("orders")
    sub_count_before = len(topic.subscriptions)

    for sub_id in list(topic.subscriptions.keys()):
        broker.unsubscribe("orders", sub_id)

    print(f"   Subscriptions before: {sub_count_before}")
    print(f"   Subscriptions after: {len(topic.subscriptions)}")
    print()

    # 15. Cleanup
    print("15. CLEANUP:")
    print("-" * 40)

    broker.delete_topic("events")
    broker.delete_queue("tasks")
    broker.remove_consumer(consumer1.id)

    print("   Deleted topic 'events'")
    print("   Deleted queue 'tasks'")
    print("   Removed consumer 'worker-1'")

    final_stats = broker.get_stats()
    print(f"   Final topics: {final_stats.topics}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Message Broker Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
