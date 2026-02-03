#!/usr/bin/env python3
"""
BAEL - Message Queue System
Comprehensive message queue and pub/sub system.

This module provides a complete message queue implementation
for asynchronous communication between system components.

Features:
- Multiple queue types (FIFO, priority, delay)
- Pub/Sub messaging
- Message persistence
- Dead letter queues
- Message acknowledgment
- Retry policies
- Message routing
- Topic subscriptions
- Message filtering
- Batch processing
"""

import asyncio
import heapq
import json
import logging
import os
import pickle
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (Any, Callable, Coroutine, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MessageState(Enum):
    """Message processing state."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"
    DELAYED = "delayed"


class QueueType(Enum):
    """Queue types."""
    FIFO = "fifo"
    LIFO = "lifo"
    PRIORITY = "priority"
    DELAY = "delay"


class DeliveryMode(Enum):
    """Message delivery mode."""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class RoutingStrategy(Enum):
    """Message routing strategy."""
    DIRECT = "direct"
    FANOUT = "fanout"
    TOPIC = "topic"
    HEADER = "header"


class AcknowledgmentMode(Enum):
    """Acknowledgment modes."""
    AUTO = "auto"
    MANUAL = "manual"
    BATCH = "batch"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MessageHeaders:
    """Message headers."""
    content_type: str = "application/json"
    correlation_id: str = ""
    reply_to: str = ""
    expiration: Optional[datetime] = None
    priority: int = 0
    custom: Dict[str, str] = field(default_factory=dict)


@dataclass
class Message:
    """A queue message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    body: Any = None
    headers: MessageHeaders = field(default_factory=MessageHeaders)
    state: MessageState = MessageState.PENDING

    # Routing
    routing_key: str = ""
    exchange: str = ""

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None

    # Retry
    attempt: int = 0
    max_attempts: int = 3
    last_error: str = ""

    def __lt__(self, other: 'Message') -> bool:
        # For priority queue comparison
        return self.headers.priority > other.headers.priority

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "body": self.body,
            "headers": {
                "content_type": self.headers.content_type,
                "correlation_id": self.headers.correlation_id,
                "reply_to": self.headers.reply_to,
                "expiration": self.headers.expiration.isoformat() if self.headers.expiration else None,
                "priority": self.headers.priority,
                "custom": self.headers.custom
            },
            "state": self.state.value,
            "routing_key": self.routing_key,
            "exchange": self.exchange,
            "created_at": self.created_at.isoformat(),
            "attempt": self.attempt,
            "max_attempts": self.max_attempts
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary."""
        headers = MessageHeaders(
            content_type=data["headers"].get("content_type", "application/json"),
            correlation_id=data["headers"].get("correlation_id", ""),
            reply_to=data["headers"].get("reply_to", ""),
            expiration=datetime.fromisoformat(data["headers"]["expiration"]) if data["headers"].get("expiration") else None,
            priority=data["headers"].get("priority", 0),
            custom=data["headers"].get("custom", {})
        )

        return cls(
            id=data["id"],
            body=data["body"],
            headers=headers,
            state=MessageState(data["state"]),
            routing_key=data.get("routing_key", ""),
            exchange=data.get("exchange", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            attempt=data.get("attempt", 0),
            max_attempts=data.get("max_attempts", 3)
        )


@dataclass
class RetryPolicy:
    """Retry policy configuration."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [Exception])

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt."""
        delay = self.initial_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)


@dataclass
class QueueConfig:
    """Queue configuration."""
    name: str
    queue_type: QueueType = QueueType.FIFO
    max_size: int = 0  # 0 = unlimited
    delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE
    ack_mode: AcknowledgmentMode = AcknowledgmentMode.AUTO
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    dead_letter_queue: Optional[str] = None
    message_ttl: Optional[float] = None  # seconds
    prefetch_count: int = 1


@dataclass
class Subscription:
    """Topic subscription."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    pattern: str = ""  # For pattern matching
    handler: Optional[Callable] = None
    filter_func: Optional[Callable[[Message], bool]] = None
    active: bool = True


# =============================================================================
# QUEUE IMPLEMENTATIONS
# =============================================================================

class MessageQueue(ABC):
    """Abstract message queue."""

    @abstractmethod
    async def put(self, message: Message) -> bool:
        """Put a message in the queue."""
        pass

    @abstractmethod
    async def get(self, timeout: float = None) -> Optional[Message]:
        """Get a message from the queue."""
        pass

    @abstractmethod
    async def peek(self) -> Optional[Message]:
        """Peek at the next message without removing."""
        pass

    @abstractmethod
    async def size(self) -> int:
        """Get queue size."""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear the queue."""
        pass


class FIFOQueue(MessageQueue):
    """First-In-First-Out queue."""

    def __init__(self, config: QueueConfig):
        self.config = config
        self._queue: deque[Message] = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def put(self, message: Message) -> bool:
        async with self._lock:
            if self.config.max_size > 0 and len(self._queue) >= self.config.max_size:
                return False

            self._queue.append(message)
            self._not_empty.set()
            return True

    async def get(self, timeout: float = None) -> Optional[Message]:
        try:
            if timeout:
                await asyncio.wait_for(self._not_empty.wait(), timeout)
            else:
                await self._not_empty.wait()
        except asyncio.TimeoutError:
            return None

        async with self._lock:
            if not self._queue:
                self._not_empty.clear()
                return None

            message = self._queue.popleft()

            if not self._queue:
                self._not_empty.clear()

            return message

    async def peek(self) -> Optional[Message]:
        async with self._lock:
            return self._queue[0] if self._queue else None

    async def size(self) -> int:
        async with self._lock:
            return len(self._queue)

    async def clear(self) -> int:
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            self._not_empty.clear()
            return count


class PriorityQueue(MessageQueue):
    """Priority-based queue."""

    def __init__(self, config: QueueConfig):
        self.config = config
        self._heap: List[Tuple[int, int, Message]] = []
        self._counter = 0
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def put(self, message: Message) -> bool:
        async with self._lock:
            if self.config.max_size > 0 and len(self._heap) >= self.config.max_size:
                return False

            # Negate priority for max-heap behavior
            priority = -message.headers.priority
            heapq.heappush(self._heap, (priority, self._counter, message))
            self._counter += 1
            self._not_empty.set()
            return True

    async def get(self, timeout: float = None) -> Optional[Message]:
        try:
            if timeout:
                await asyncio.wait_for(self._not_empty.wait(), timeout)
            else:
                await self._not_empty.wait()
        except asyncio.TimeoutError:
            return None

        async with self._lock:
            if not self._heap:
                self._not_empty.clear()
                return None

            _, _, message = heapq.heappop(self._heap)

            if not self._heap:
                self._not_empty.clear()

            return message

    async def peek(self) -> Optional[Message]:
        async with self._lock:
            return self._heap[0][2] if self._heap else None

    async def size(self) -> int:
        async with self._lock:
            return len(self._heap)

    async def clear(self) -> int:
        async with self._lock:
            count = len(self._heap)
            self._heap.clear()
            self._not_empty.clear()
            return count


class DelayQueue(MessageQueue):
    """Delay queue for scheduled messages."""

    def __init__(self, config: QueueConfig):
        self.config = config
        self._heap: List[Tuple[float, int, Message]] = []
        self._counter = 0
        self._lock = asyncio.Lock()

    async def put(self, message: Message, delay: float = 0) -> bool:
        async with self._lock:
            if self.config.max_size > 0 and len(self._heap) >= self.config.max_size:
                return False

            deliver_at = time.time() + delay
            message.scheduled_at = datetime.now() + timedelta(seconds=delay)
            message.state = MessageState.DELAYED

            heapq.heappush(self._heap, (deliver_at, self._counter, message))
            self._counter += 1
            return True

    async def get(self, timeout: float = None) -> Optional[Message]:
        start_time = time.time()

        while True:
            async with self._lock:
                if not self._heap:
                    if timeout and (time.time() - start_time) >= timeout:
                        return None
                    await asyncio.sleep(0.1)
                    continue

                deliver_at, _, _ = self._heap[0]
                now = time.time()

                if deliver_at <= now:
                    _, _, message = heapq.heappop(self._heap)
                    message.state = MessageState.PENDING
                    return message

                # Wait for message or timeout
                wait_time = deliver_at - now
                if timeout:
                    remaining = timeout - (now - start_time)
                    if remaining <= 0:
                        return None
                    wait_time = min(wait_time, remaining)

            await asyncio.sleep(min(wait_time, 0.5))

    async def peek(self) -> Optional[Message]:
        async with self._lock:
            if not self._heap:
                return None
            deliver_at, _, message = self._heap[0]
            if deliver_at <= time.time():
                return message
            return None

    async def size(self) -> int:
        async with self._lock:
            return len(self._heap)

    async def clear(self) -> int:
        async with self._lock:
            count = len(self._heap)
            self._heap.clear()
            return count


# =============================================================================
# EXCHANGE
# =============================================================================

class Exchange:
    """Message exchange for routing."""

    def __init__(
        self,
        name: str,
        routing_strategy: RoutingStrategy = RoutingStrategy.DIRECT
    ):
        self.name = name
        self.routing_strategy = routing_strategy
        self.bindings: Dict[str, Set[str]] = defaultdict(set)  # routing_key -> queue_names

    def bind(self, queue_name: str, routing_key: str = "") -> None:
        """Bind a queue to the exchange."""
        self.bindings[routing_key].add(queue_name)

    def unbind(self, queue_name: str, routing_key: str = "") -> None:
        """Unbind a queue from the exchange."""
        if routing_key in self.bindings:
            self.bindings[routing_key].discard(queue_name)

    def route(self, message: Message) -> Set[str]:
        """Route message to queues."""
        if self.routing_strategy == RoutingStrategy.DIRECT:
            return self.bindings.get(message.routing_key, set())

        elif self.routing_strategy == RoutingStrategy.FANOUT:
            # Send to all bound queues
            all_queues: Set[str] = set()
            for queues in self.bindings.values():
                all_queues.update(queues)
            return all_queues

        elif self.routing_strategy == RoutingStrategy.TOPIC:
            # Pattern matching
            matched: Set[str] = set()
            for pattern, queues in self.bindings.items():
                if self._match_topic(message.routing_key, pattern):
                    matched.update(queues)
            return matched

        return set()

    def _match_topic(self, key: str, pattern: str) -> bool:
        """Match routing key against pattern."""
        key_parts = key.split('.')
        pattern_parts = pattern.split('.')

        i, j = 0, 0
        while i < len(key_parts) and j < len(pattern_parts):
            if pattern_parts[j] == '#':
                if j == len(pattern_parts) - 1:
                    return True
                # Try to match remaining
                for k in range(i, len(key_parts)):
                    if self._match_topic('.'.join(key_parts[k:]), '.'.join(pattern_parts[j + 1:])):
                        return True
                return False
            elif pattern_parts[j] == '*':
                i += 1
                j += 1
            elif pattern_parts[j] == key_parts[i]:
                i += 1
                j += 1
            else:
                return False

        return i == len(key_parts) and j == len(pattern_parts)


# =============================================================================
# CONSUMER
# =============================================================================

class Consumer:
    """Message consumer."""

    def __init__(
        self,
        queue_manager: 'QueueManager',
        queue_name: str,
        handler: Callable[[Message], Coroutine],
        prefetch: int = 1,
        ack_mode: AcknowledgmentMode = AcknowledgmentMode.AUTO
    ):
        self.queue_manager = queue_manager
        self.queue_name = queue_name
        self.handler = handler
        self.prefetch = prefetch
        self.ack_mode = ack_mode

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._pending: Dict[str, Message] = {}

    async def start(self) -> None:
        """Start consuming."""
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """Stop consuming."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _consume_loop(self) -> None:
        """Main consume loop."""
        while self._running:
            try:
                if len(self._pending) >= self.prefetch:
                    await asyncio.sleep(0.1)
                    continue

                message = await self.queue_manager.get(self.queue_name, timeout=1.0)

                if message:
                    self._pending[message.id] = message
                    await self._process_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, message: Message) -> None:
        """Process a message."""
        try:
            message.state = MessageState.PROCESSING
            await self.handler(message)

            if self.ack_mode == AcknowledgmentMode.AUTO:
                await self.ack(message.id)

        except Exception as e:
            logger.error(f"Handler error: {e}")
            message.last_error = str(e)
            await self.nack(message.id, requeue=True)

    async def ack(self, message_id: str) -> None:
        """Acknowledge a message."""
        if message_id in self._pending:
            message = self._pending.pop(message_id)
            message.state = MessageState.COMPLETED
            message.processed_at = datetime.now()

    async def nack(self, message_id: str, requeue: bool = True) -> None:
        """Negative acknowledge a message."""
        if message_id in self._pending:
            message = self._pending.pop(message_id)
            message.state = MessageState.FAILED
            message.attempt += 1

            if requeue and message.attempt < message.max_attempts:
                await self.queue_manager.put(self.queue_name, message)
            else:
                # Send to dead letter queue
                await self.queue_manager.send_to_dead_letter(self.queue_name, message)


# =============================================================================
# QUEUE MANAGER
# =============================================================================

class QueueManager:
    """
    Master queue management system for BAEL.

    Manages queues, exchanges, and message routing.
    """

    def __init__(self):
        self.queues: Dict[str, MessageQueue] = {}
        self.configs: Dict[str, QueueConfig] = {}
        self.exchanges: Dict[str, Exchange] = {}
        self.consumers: Dict[str, List[Consumer]] = defaultdict(list)
        self.subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self.dead_letter_queues: Dict[str, MessageQueue] = {}

        # Statistics
        self.messages_published = 0
        self.messages_consumed = 0
        self.messages_dead_lettered = 0

    def create_queue(self, config: QueueConfig) -> MessageQueue:
        """Create a queue."""
        if config.queue_type == QueueType.FIFO:
            queue = FIFOQueue(config)
        elif config.queue_type == QueueType.PRIORITY:
            queue = PriorityQueue(config)
        elif config.queue_type == QueueType.DELAY:
            queue = DelayQueue(config)
        else:
            queue = FIFOQueue(config)

        self.queues[config.name] = queue
        self.configs[config.name] = config

        # Create dead letter queue if specified
        if config.dead_letter_queue:
            dlq_config = QueueConfig(
                name=config.dead_letter_queue,
                queue_type=QueueType.FIFO
            )
            self.dead_letter_queues[config.name] = FIFOQueue(dlq_config)

        return queue

    def create_exchange(
        self,
        name: str,
        routing_strategy: RoutingStrategy = RoutingStrategy.DIRECT
    ) -> Exchange:
        """Create an exchange."""
        exchange = Exchange(name, routing_strategy)
        self.exchanges[name] = exchange
        return exchange

    def bind_queue(
        self,
        exchange_name: str,
        queue_name: str,
        routing_key: str = ""
    ) -> None:
        """Bind a queue to an exchange."""
        if exchange_name in self.exchanges:
            self.exchanges[exchange_name].bind(queue_name, routing_key)

    async def publish(
        self,
        exchange_name: str,
        message: Message,
        routing_key: str = ""
    ) -> int:
        """Publish a message to an exchange."""
        message.exchange = exchange_name
        message.routing_key = routing_key

        if exchange_name not in self.exchanges:
            return 0

        exchange = self.exchanges[exchange_name]
        target_queues = exchange.route(message)

        published = 0
        for queue_name in target_queues:
            if await self.put(queue_name, message):
                published += 1

        return published

    async def put(
        self,
        queue_name: str,
        message: Message,
        delay: float = 0
    ) -> bool:
        """Put a message in a queue."""
        if queue_name not in self.queues:
            return False

        queue = self.queues[queue_name]

        if isinstance(queue, DelayQueue) and delay > 0:
            result = await queue.put(message, delay)
        else:
            result = await queue.put(message)

        if result:
            self.messages_published += 1

            # Notify topic subscribers
            await self._notify_subscribers(queue_name, message)

        return result

    async def get(
        self,
        queue_name: str,
        timeout: float = None
    ) -> Optional[Message]:
        """Get a message from a queue."""
        if queue_name not in self.queues:
            return None

        message = await self.queues[queue_name].get(timeout)

        if message:
            self.messages_consumed += 1

        return message

    async def peek(self, queue_name: str) -> Optional[Message]:
        """Peek at the next message."""
        if queue_name not in self.queues:
            return None

        return await self.queues[queue_name].peek()

    async def size(self, queue_name: str) -> int:
        """Get queue size."""
        if queue_name not in self.queues:
            return 0

        return await self.queues[queue_name].size()

    async def clear(self, queue_name: str) -> int:
        """Clear a queue."""
        if queue_name not in self.queues:
            return 0

        return await self.queues[queue_name].clear()

    async def send_to_dead_letter(
        self,
        queue_name: str,
        message: Message
    ) -> bool:
        """Send message to dead letter queue."""
        if queue_name not in self.dead_letter_queues:
            return False

        message.state = MessageState.DEAD
        result = await self.dead_letter_queues[queue_name].put(message)

        if result:
            self.messages_dead_lettered += 1

        return result

    # Pub/Sub
    def subscribe(
        self,
        topic: str,
        handler: Callable[[Message], Coroutine],
        filter_func: Callable[[Message], bool] = None
    ) -> Subscription:
        """Subscribe to a topic."""
        subscription = Subscription(
            topic=topic,
            handler=handler,
            filter_func=filter_func
        )

        self.subscriptions[topic].append(subscription)
        return subscription

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe."""
        for topic, subs in self.subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subs.remove(sub)
                    return True
        return False

    async def _notify_subscribers(
        self,
        topic: str,
        message: Message
    ) -> None:
        """Notify topic subscribers."""
        for sub in self.subscriptions.get(topic, []):
            if not sub.active:
                continue

            # Apply filter
            if sub.filter_func and not sub.filter_func(message):
                continue

            try:
                if sub.handler:
                    await sub.handler(message)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

    # Consumer management
    def create_consumer(
        self,
        queue_name: str,
        handler: Callable[[Message], Coroutine],
        prefetch: int = 1
    ) -> Consumer:
        """Create a consumer."""
        consumer = Consumer(self, queue_name, handler, prefetch)
        self.consumers[queue_name].append(consumer)
        return consumer

    async def start_consumers(self, queue_name: str = None) -> None:
        """Start consumers."""
        if queue_name:
            for consumer in self.consumers.get(queue_name, []):
                await consumer.start()
        else:
            for consumers in self.consumers.values():
                for consumer in consumers:
                    await consumer.start()

    async def stop_consumers(self, queue_name: str = None) -> None:
        """Stop consumers."""
        if queue_name:
            for consumer in self.consumers.get(queue_name, []):
                await consumer.stop()
        else:
            for consumers in self.consumers.values():
                for consumer in consumers:
                    await consumer.stop()

    # Utilities
    def get_queue_names(self) -> List[str]:
        """Get all queue names."""
        return list(self.queues.keys())

    def get_exchange_names(self) -> List[str]:
        """Get all exchange names."""
        return list(self.exchanges.keys())

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "queues": len(self.queues),
            "exchanges": len(self.exchanges),
            "consumers": sum(len(c) for c in self.consumers.values()),
            "subscriptions": sum(len(s) for s in self.subscriptions.values()),
            "messages_published": self.messages_published,
            "messages_consumed": self.messages_consumed,
            "messages_dead_lettered": self.messages_dead_lettered
        }

    async def get_all_queue_sizes(self) -> Dict[str, int]:
        """Get sizes of all queues."""
        sizes = {}
        for name in self.queues:
            sizes[name] = await self.size(name)
        return sizes


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Message Queue System."""
    print("=" * 70)
    print("BAEL - MESSAGE QUEUE SYSTEM DEMO")
    print("Async Message Queue and Pub/Sub")
    print("=" * 70)
    print()

    manager = QueueManager()

    # 1. FIFO Queue
    print("1. FIFO QUEUE:")
    print("-" * 40)

    manager.create_queue(QueueConfig(
        name="tasks",
        queue_type=QueueType.FIFO,
        max_size=100
    ))

    for i in range(5):
        msg = Message(body={"task": f"task_{i}"})
        await manager.put("tasks", msg)
        print(f"   Published: {msg.body}")

    print("   Consuming:")
    for _ in range(3):
        msg = await manager.get("tasks", timeout=1)
        if msg:
            print(f"   Consumed: {msg.body}")
    print()

    # 2. Priority Queue
    print("2. PRIORITY QUEUE:")
    print("-" * 40)

    manager.create_queue(QueueConfig(
        name="priority_tasks",
        queue_type=QueueType.PRIORITY
    ))

    priorities = [1, 5, 3, 10, 2]
    for p in priorities:
        msg = Message(
            body={"priority_task": p},
            headers=MessageHeaders(priority=p)
        )
        await manager.put("priority_tasks", msg)
        print(f"   Published priority {p}")

    print("   Consuming (highest priority first):")
    while True:
        msg = await manager.get("priority_tasks", timeout=0.1)
        if not msg:
            break
        print(f"   Consumed priority {msg.headers.priority}")
    print()

    # 3. Delay Queue
    print("3. DELAY QUEUE:")
    print("-" * 40)

    manager.create_queue(QueueConfig(
        name="scheduled",
        queue_type=QueueType.DELAY
    ))

    msg = Message(body={"delayed": True})
    await manager.put("scheduled", msg, delay=1.0)
    print("   Published message with 1 second delay")

    msg_now = await manager.get("scheduled", timeout=0.1)
    print(f"   Immediate get: {msg_now}")

    print("   Waiting 1 second...")
    await asyncio.sleep(1.1)

    msg_delayed = await manager.get("scheduled", timeout=0.1)
    print(f"   After delay: {msg_delayed.body if msg_delayed else None}")
    print()

    # 4. Exchange Routing
    print("4. EXCHANGE ROUTING:")
    print("-" * 40)

    manager.create_queue(QueueConfig(name="orders"))
    manager.create_queue(QueueConfig(name="payments"))

    exchange = manager.create_exchange("orders_exchange", RoutingStrategy.DIRECT)
    manager.bind_queue("orders_exchange", "orders", "order.created")
    manager.bind_queue("orders_exchange", "payments", "payment.processed")

    msg1 = Message(body={"order_id": 1})
    await manager.publish("orders_exchange", msg1, routing_key="order.created")
    print(f"   Published order.created")

    msg2 = Message(body={"payment_id": 1})
    await manager.publish("orders_exchange", msg2, routing_key="payment.processed")
    print(f"   Published payment.processed")

    orders_msg = await manager.get("orders", timeout=0.1)
    payments_msg = await manager.get("payments", timeout=0.1)
    print(f"   Orders queue got: {orders_msg.body if orders_msg else None}")
    print(f"   Payments queue got: {payments_msg.body if payments_msg else None}")
    print()

    # 5. Topic Routing
    print("5. TOPIC ROUTING:")
    print("-" * 40)

    manager.create_queue(QueueConfig(name="all_logs"))
    manager.create_queue(QueueConfig(name="error_logs"))

    topic_exchange = manager.create_exchange("logs_exchange", RoutingStrategy.TOPIC)
    manager.bind_queue("logs_exchange", "all_logs", "log.#")
    manager.bind_queue("logs_exchange", "error_logs", "log.error.*")

    await manager.publish("logs_exchange", Message(body="info log"), "log.info.app")
    await manager.publish("logs_exchange", Message(body="error log"), "log.error.app")

    all_size = await manager.size("all_logs")
    error_size = await manager.size("error_logs")
    print(f"   all_logs queue: {all_size} messages")
    print(f"   error_logs queue: {error_size} messages")
    print()

    # 6. Pub/Sub
    print("6. PUB/SUB:")
    print("-" * 40)

    received = []

    async def notification_handler(msg: Message):
        received.append(msg.body)

    sub = manager.subscribe("notifications", notification_handler)
    print(f"   Subscribed with ID: {sub.id[:8]}...")

    manager.create_queue(QueueConfig(name="notifications"))

    await manager.put("notifications", Message(body="Notification 1"))
    await manager.put("notifications", Message(body="Notification 2"))

    await asyncio.sleep(0.1)
    print(f"   Received: {received}")
    print()

    # 7. Consumer
    print("7. CONSUMER:")
    print("-" * 40)

    processed = []

    async def task_handler(msg: Message):
        processed.append(msg.body)

    consumer = manager.create_consumer("tasks", task_handler, prefetch=2)
    await consumer.start()

    # Add more tasks
    for i in range(3):
        await manager.put("tasks", Message(body=f"task_{i}"))

    await asyncio.sleep(0.5)
    await consumer.stop()

    print(f"   Processed tasks: {processed}")
    print()

    # 8. Queue Sizes
    print("8. QUEUE SIZES:")
    print("-" * 40)

    sizes = await manager.get_all_queue_sizes()
    for name, size in sizes.items():
        print(f"   {name}: {size}")
    print()

    # 9. Statistics
    print("9. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Message Queue System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
