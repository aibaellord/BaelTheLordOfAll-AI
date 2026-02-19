"""
BAEL Message Queue
==================

Comprehensive message queue system with:
- Multiple exchange types (direct, topic, fanout, headers)
- Persistent and transient messages
- Priority queues
- Dead letter queues
- Consumer groups
- Message acknowledgments

"Every message finds its destination." — Ba'el
"""

import asyncio
import logging
import json
import time
import heapq
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict, deque
import threading
import uuid
import re
import fnmatch

logger = logging.getLogger("BAEL.MessageQueue")


# ============================================================================
# ENUMS
# ============================================================================

class ExchangeType(Enum):
    """Types of message exchanges."""
    DIRECT = "direct"   # Route by exact routing key
    TOPIC = "topic"     # Route by pattern matching
    FANOUT = "fanout"   # Broadcast to all
    HEADERS = "headers" # Route by message headers


class DeliveryMode(Enum):
    """Message delivery modes."""
    TRANSIENT = 1   # In-memory only
    PERSISTENT = 2  # Persisted to storage


class MessageStatus(Enum):
    """Status of a message."""
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    REQUEUED = "requeued"
    DEAD_LETTERED = "dead_lettered"


class AckMode(Enum):
    """Message acknowledgment modes."""
    AUTO = "auto"       # Automatic acknowledgment
    MANUAL = "manual"   # Manual acknowledgment required
    NONE = "none"       # No acknowledgment


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Message:
    """A queue message."""
    id: str
    body: Any
    routing_key: str = ""

    # Properties
    headers: Dict[str, Any] = field(default_factory=dict)
    content_type: str = "application/json"
    priority: int = 0
    delivery_mode: DeliveryMode = DeliveryMode.TRANSIENT

    # Tracking
    status: MessageStatus = MessageStatus.PENDING
    delivery_count: int = 0
    max_retries: int = 3

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Correlation
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'body': self.body,
            'routing_key': self.routing_key,
            'headers': self.headers,
            'priority': self.priority,
            'status': self.status.value,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class QueueConfig:
    """Configuration for a queue."""
    durable: bool = False           # Survive broker restart
    exclusive: bool = False         # Single consumer only
    auto_delete: bool = False       # Delete when unused
    max_length: int = 0             # Max messages (0 = unlimited)
    max_length_bytes: int = 0       # Max size in bytes
    message_ttl: int = 0            # Default message TTL in seconds
    dead_letter_exchange: str = ""  # DLX for rejected messages
    dead_letter_routing_key: str = ""
    max_priority: int = 10          # Max priority level
    ack_mode: AckMode = AckMode.MANUAL


@dataclass
class Queue:
    """A message queue."""
    name: str
    config: QueueConfig = field(default_factory=QueueConfig)

    # State
    messages: List[Message] = field(default_factory=list)
    unacked: Dict[str, Message] = field(default_factory=dict)

    # Stats
    message_count: int = 0
    consumer_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self._priority_queue = []  # heapq for priority ordering

    @property
    def is_empty(self) -> bool:
        return len(self.messages) == 0

    def enqueue(self, message: Message) -> bool:
        """Add a message to the queue."""
        if self.config.max_length > 0 and len(self.messages) >= self.config.max_length:
            return False

        # Apply default TTL
        if self.config.message_ttl > 0 and message.expires_at is None:
            message.expires_at = datetime.now() + timedelta(seconds=self.config.message_ttl)

        # Priority queue ordering (negated for max-heap behavior)
        heapq.heappush(self._priority_queue, (-message.priority, message.created_at.timestamp(), message))
        self.messages.append(message)
        self.message_count += 1
        return True

    def dequeue(self) -> Optional[Message]:
        """Get the next message from the queue."""
        # Clean expired messages
        while self._priority_queue:
            _, _, msg = self._priority_queue[0]
            if msg.is_expired:
                heapq.heappop(self._priority_queue)
                if msg in self.messages:
                    self.messages.remove(msg)
                continue
            break

        if not self._priority_queue:
            return None

        _, _, message = heapq.heappop(self._priority_queue)
        if message in self.messages:
            self.messages.remove(message)

        message.status = MessageStatus.DELIVERED
        message.delivered_at = datetime.now()
        message.delivery_count += 1

        # Track unacked
        if self.config.ack_mode == AckMode.MANUAL:
            self.unacked[message.id] = message

        return message

    def ack(self, message_id: str) -> bool:
        """Acknowledge a message."""
        if message_id in self.unacked:
            message = self.unacked.pop(message_id)
            message.status = MessageStatus.ACKNOWLEDGED
            message.acknowledged_at = datetime.now()
            return True
        return False

    def nack(self, message_id: str, requeue: bool = True) -> Optional[Message]:
        """Negative acknowledge a message."""
        if message_id in self.unacked:
            message = self.unacked.pop(message_id)

            if requeue and message.delivery_count < message.max_retries:
                message.status = MessageStatus.REQUEUED
                self.enqueue(message)
                return None
            else:
                message.status = MessageStatus.REJECTED
                return message  # Return for dead lettering

        return None


@dataclass
class Exchange:
    """A message exchange."""
    name: str
    exchange_type: ExchangeType = ExchangeType.DIRECT
    durable: bool = False
    auto_delete: bool = False

    # Bindings
    bindings: Dict[str, List['Binding']] = field(default_factory=lambda: defaultdict(list))

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Binding:
    """A binding between an exchange and a queue."""
    exchange: str
    queue: str
    routing_key: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Consumer:
    """A message consumer."""
    id: str
    queue: str
    callback: Callable[[Message], None]
    tag: str = ""
    ack_mode: AckMode = AckMode.MANUAL
    prefetch_count: int = 1

    # State
    active: bool = True
    messages_consumed: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MessageQueueConfig:
    """Configuration for the message queue engine."""
    default_exchange: str = ""
    enable_persistence: bool = False
    persistence_path: str = "./mq_data"
    max_message_size: int = 1024 * 1024  # 1MB
    message_ttl: int = 86400  # 24 hours
    dead_letter_exchange: str = "dlx"
    enable_metrics: bool = True


# ============================================================================
# QUEUE MANAGER
# ============================================================================

class QueueManager:
    """
    Manages message queues.
    """

    def __init__(self):
        """Initialize queue manager."""
        self._queues: Dict[str, Queue] = {}
        self._lock = threading.RLock()

    def declare(
        self,
        name: str,
        config: Optional[QueueConfig] = None
    ) -> Queue:
        """Declare a queue."""
        with self._lock:
            if name in self._queues:
                return self._queues[name]

            queue = Queue(
                name=name,
                config=config or QueueConfig()
            )
            self._queues[name] = queue
            logger.info(f"Declared queue: {name}")
            return queue

    def get(self, name: str) -> Optional[Queue]:
        """Get a queue by name."""
        return self._queues.get(name)

    def delete(self, name: str, if_empty: bool = False) -> bool:
        """Delete a queue."""
        with self._lock:
            if name not in self._queues:
                return False

            queue = self._queues[name]

            if if_empty and not queue.is_empty:
                return False

            del self._queues[name]
            logger.info(f"Deleted queue: {name}")
            return True

    def purge(self, name: str) -> int:
        """Remove all messages from a queue."""
        with self._lock:
            queue = self._queues.get(name)
            if not queue:
                return 0

            count = len(queue.messages)
            queue.messages.clear()
            queue._priority_queue.clear()
            return count

    def list(self) -> List[Queue]:
        """List all queues."""
        return list(self._queues.values())


# ============================================================================
# EXCHANGE MANAGER
# ============================================================================

class ExchangeManager:
    """
    Manages message exchanges.
    """

    def __init__(self):
        """Initialize exchange manager."""
        self._exchanges: Dict[str, Exchange] = {}
        self._lock = threading.RLock()

        # Default exchange
        self._exchanges[""] = Exchange(name="", exchange_type=ExchangeType.DIRECT)

    def declare(
        self,
        name: str,
        exchange_type: ExchangeType = ExchangeType.DIRECT,
        durable: bool = False,
        auto_delete: bool = False
    ) -> Exchange:
        """Declare an exchange."""
        with self._lock:
            if name in self._exchanges:
                return self._exchanges[name]

            exchange = Exchange(
                name=name,
                exchange_type=exchange_type,
                durable=durable,
                auto_delete=auto_delete
            )
            self._exchanges[name] = exchange
            logger.info(f"Declared exchange: {name} ({exchange_type.value})")
            return exchange

    def get(self, name: str) -> Optional[Exchange]:
        """Get an exchange by name."""
        return self._exchanges.get(name)

    def delete(self, name: str) -> bool:
        """Delete an exchange."""
        with self._lock:
            if name not in self._exchanges or name == "":
                return False

            del self._exchanges[name]
            logger.info(f"Deleted exchange: {name}")
            return True

    def bind(
        self,
        exchange: str,
        queue: str,
        routing_key: str = "",
        arguments: Optional[Dict[str, Any]] = None
    ) -> Binding:
        """Bind a queue to an exchange."""
        with self._lock:
            ex = self._exchanges.get(exchange)
            if not ex:
                raise ValueError(f"Exchange not found: {exchange}")

            binding = Binding(
                exchange=exchange,
                queue=queue,
                routing_key=routing_key,
                arguments=arguments or {}
            )

            ex.bindings[routing_key].append(binding)
            logger.info(f"Bound queue {queue} to exchange {exchange} with key '{routing_key}'")
            return binding

    def unbind(
        self,
        exchange: str,
        queue: str,
        routing_key: str = ""
    ) -> bool:
        """Unbind a queue from an exchange."""
        with self._lock:
            ex = self._exchanges.get(exchange)
            if not ex:
                return False

            if routing_key not in ex.bindings:
                return False

            ex.bindings[routing_key] = [
                b for b in ex.bindings[routing_key]
                if b.queue != queue
            ]
            return True

    def list(self) -> List[Exchange]:
        """List all exchanges."""
        return list(self._exchanges.values())

    def route(
        self,
        exchange: str,
        routing_key: str,
        headers: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Get queues for a routing key."""
        ex = self._exchanges.get(exchange)
        if not ex:
            return []

        queues = set()

        if ex.exchange_type == ExchangeType.DIRECT:
            for binding in ex.bindings.get(routing_key, []):
                queues.add(binding.queue)

        elif ex.exchange_type == ExchangeType.TOPIC:
            for pattern, bindings in ex.bindings.items():
                if self._topic_match(pattern, routing_key):
                    for binding in bindings:
                        queues.add(binding.queue)

        elif ex.exchange_type == ExchangeType.FANOUT:
            for bindings in ex.bindings.values():
                for binding in bindings:
                    queues.add(binding.queue)

        elif ex.exchange_type == ExchangeType.HEADERS:
            if headers:
                for pattern, bindings in ex.bindings.items():
                    for binding in bindings:
                        if self._headers_match(binding.arguments, headers):
                            queues.add(binding.queue)

        return list(queues)

    def _topic_match(self, pattern: str, routing_key: str) -> bool:
        """Match a topic pattern against a routing key."""
        # Convert AMQP pattern to regex
        # * matches one word
        # # matches zero or more words
        regex = pattern.replace('.', r'\.').replace('*', r'[^.]+').replace('#', r'.*')
        return bool(re.match(f'^{regex}$', routing_key))

    def _headers_match(
        self,
        binding_args: Dict[str, Any],
        headers: Dict[str, Any]
    ) -> bool:
        """Match headers against binding arguments."""
        match_type = binding_args.get('x-match', 'all')

        if match_type == 'all':
            for key, value in binding_args.items():
                if key.startswith('x-'):
                    continue
                if headers.get(key) != value:
                    return False
            return True

        elif match_type == 'any':
            for key, value in binding_args.items():
                if key.startswith('x-'):
                    continue
                if headers.get(key) == value:
                    return True
            return False

        return False


# ============================================================================
# DEAD LETTER QUEUE
# ============================================================================

class DeadLetterQueue:
    """
    Handles dead-lettered messages.
    """

    def __init__(self, queue_manager: QueueManager):
        """Initialize dead letter queue."""
        self._queue_manager = queue_manager
        self._dlq_name = "dead_letter_queue"

        # Create DLQ
        self._queue_manager.declare(
            self._dlq_name,
            QueueConfig(durable=True, max_length=10000)
        )

    def dead_letter(
        self,
        message: Message,
        reason: str = "rejected"
    ) -> bool:
        """Send a message to the dead letter queue."""
        message.status = MessageStatus.DEAD_LETTERED
        message.headers['x-death-reason'] = reason
        message.headers['x-death-time'] = datetime.now().isoformat()
        message.headers['x-original-routing-key'] = message.routing_key

        dlq = self._queue_manager.get(self._dlq_name)
        if dlq:
            return dlq.enqueue(message)
        return False

    def get_dead_letters(self, limit: int = 100) -> List[Message]:
        """Get dead-lettered messages."""
        dlq = self._queue_manager.get(self._dlq_name)
        if dlq:
            return dlq.messages[:limit]
        return []

    def requeue(self, message_id: str) -> bool:
        """Requeue a dead-lettered message."""
        dlq = self._queue_manager.get(self._dlq_name)
        if not dlq:
            return False

        for msg in dlq.messages:
            if msg.id == message_id:
                dlq.messages.remove(msg)
                msg.status = MessageStatus.PENDING
                msg.delivery_count = 0
                msg.headers.pop('x-death-reason', None)
                msg.headers.pop('x-death-time', None)
                return True

        return False


# ============================================================================
# MESSAGE BROKER
# ============================================================================

class MessageBroker:
    """
    Routes messages between exchanges and queues.
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        exchange_manager: ExchangeManager,
        dead_letter_queue: DeadLetterQueue
    ):
        """Initialize message broker."""
        self._queue_manager = queue_manager
        self._exchange_manager = exchange_manager
        self._dlq = dead_letter_queue

        # Consumers
        self._consumers: Dict[str, List[Consumer]] = defaultdict(list)
        self._consumer_tasks: Dict[str, asyncio.Task] = {}

        # Statistics
        self._stats = {
            'messages_published': 0,
            'messages_delivered': 0,
            'messages_acknowledged': 0,
            'messages_dead_lettered': 0
        }

    async def publish(
        self,
        exchange: str,
        routing_key: str,
        body: Any,
        headers: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        delivery_mode: DeliveryMode = DeliveryMode.TRANSIENT,
        ttl: Optional[int] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """Publish a message to an exchange."""
        message = Message(
            id=str(uuid.uuid4()),
            body=body,
            routing_key=routing_key,
            headers=headers or {},
            priority=priority,
            delivery_mode=delivery_mode,
            correlation_id=correlation_id,
            reply_to=reply_to
        )

        if ttl:
            message.expires_at = datetime.now() + timedelta(seconds=ttl)

        # Route message
        queue_names = self._exchange_manager.route(exchange, routing_key, headers)

        if not queue_names:
            # Default exchange routes by queue name
            if exchange == "":
                queue_names = [routing_key]

        delivered = False
        for queue_name in queue_names:
            queue = self._queue_manager.get(queue_name)
            if queue:
                if queue.enqueue(message):
                    delivered = True
                    logger.debug(f"Message {message.id} delivered to queue {queue_name}")

        if delivered:
            self._stats['messages_published'] += 1

        return delivered

    async def consume(
        self,
        queue_name: str,
        callback: Callable[[Message], None],
        ack_mode: AckMode = AckMode.MANUAL,
        prefetch_count: int = 1
    ) -> Consumer:
        """Start consuming from a queue."""
        consumer = Consumer(
            id=str(uuid.uuid4()),
            queue=queue_name,
            callback=callback,
            tag=f"consumer-{uuid.uuid4().hex[:8]}",
            ack_mode=ack_mode,
            prefetch_count=prefetch_count
        )

        self._consumers[queue_name].append(consumer)

        queue = self._queue_manager.get(queue_name)
        if queue:
            queue.consumer_count += 1

        # Start consumer task
        task = asyncio.create_task(self._consume_loop(consumer))
        self._consumer_tasks[consumer.id] = task

        logger.info(f"Started consumer {consumer.tag} for queue {queue_name}")
        return consumer

    async def _consume_loop(self, consumer: Consumer) -> None:
        """Consumer loop."""
        while consumer.active:
            queue = self._queue_manager.get(consumer.queue)
            if not queue:
                await asyncio.sleep(0.1)
                continue

            # Check unacked limit
            if len(queue.unacked) >= consumer.prefetch_count:
                await asyncio.sleep(0.01)
                continue

            message = queue.dequeue()
            if message:
                try:
                    if asyncio.iscoroutinefunction(consumer.callback):
                        await consumer.callback(message)
                    else:
                        consumer.callback(message)

                    consumer.messages_consumed += 1
                    self._stats['messages_delivered'] += 1

                    # Auto-ack
                    if consumer.ack_mode == AckMode.AUTO:
                        queue.ack(message.id)
                        self._stats['messages_acknowledged'] += 1

                except Exception as e:
                    logger.error(f"Consumer error: {e}")
                    rejected = queue.nack(message.id, requeue=True)
                    if rejected:
                        self._dlq.dead_letter(rejected, f"consumer_error: {e}")
                        self._stats['messages_dead_lettered'] += 1
            else:
                await asyncio.sleep(0.01)

    async def cancel(self, consumer_id: str) -> bool:
        """Cancel a consumer."""
        for queue_name, consumers in self._consumers.items():
            for consumer in consumers:
                if consumer.id == consumer_id:
                    consumer.active = False

                    if consumer_id in self._consumer_tasks:
                        self._consumer_tasks[consumer_id].cancel()
                        del self._consumer_tasks[consumer_id]

                    consumers.remove(consumer)

                    queue = self._queue_manager.get(queue_name)
                    if queue:
                        queue.consumer_count -= 1

                    logger.info(f"Cancelled consumer {consumer.tag}")
                    return True

        return False

    def ack(self, queue_name: str, message_id: str) -> bool:
        """Acknowledge a message."""
        queue = self._queue_manager.get(queue_name)
        if queue:
            if queue.ack(message_id):
                self._stats['messages_acknowledged'] += 1
                return True
        return False

    def nack(
        self,
        queue_name: str,
        message_id: str,
        requeue: bool = True
    ) -> bool:
        """Negative acknowledge a message."""
        queue = self._queue_manager.get(queue_name)
        if queue:
            rejected = queue.nack(message_id, requeue)
            if rejected:
                self._dlq.dead_letter(rejected, "nacked")
                self._stats['messages_dead_lettered'] += 1
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics."""
        return self._stats.copy()


# ============================================================================
# MAIN MESSAGE QUEUE ENGINE
# ============================================================================

class MessageQueueEngine:
    """
    Main message queue engine.

    Features:
    - Exchanges and queues
    - Topic routing
    - Dead letter handling
    - Consumer groups
    - Message acknowledgments

    "Ba'el's messages traverse realms." — Ba'el
    """

    def __init__(self, config: Optional[MessageQueueConfig] = None):
        """Initialize message queue engine."""
        self.config = config or MessageQueueConfig()

        # Components
        self.queues = QueueManager()
        self.exchanges = ExchangeManager()
        self.dead_letters = DeadLetterQueue(self.queues)
        self.broker = MessageBroker(self.queues, self.exchanges, self.dead_letters)

        # Default DLX exchange
        self.exchanges.declare(
            self.config.dead_letter_exchange,
            ExchangeType.DIRECT
        )

        logger.info("MessageQueueEngine initialized")

    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================

    def declare_queue(
        self,
        name: str,
        durable: bool = False,
        max_length: int = 0,
        message_ttl: int = 0,
        dead_letter_exchange: str = ""
    ) -> Queue:
        """Declare a queue with common options."""
        config = QueueConfig(
            durable=durable,
            max_length=max_length,
            message_ttl=message_ttl,
            dead_letter_exchange=dead_letter_exchange or self.config.dead_letter_exchange
        )
        return self.queues.declare(name, config)

    def declare_exchange(
        self,
        name: str,
        exchange_type: ExchangeType = ExchangeType.DIRECT,
        durable: bool = False
    ) -> Exchange:
        """Declare an exchange."""
        return self.exchanges.declare(name, exchange_type, durable)

    def bind(
        self,
        queue: str,
        exchange: str,
        routing_key: str = ""
    ) -> Binding:
        """Bind a queue to an exchange."""
        return self.exchanges.bind(exchange, queue, routing_key)

    async def publish(
        self,
        routing_key: str,
        body: Any,
        exchange: str = "",
        headers: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        ttl: Optional[int] = None
    ) -> bool:
        """Publish a message."""
        return await self.broker.publish(
            exchange=exchange,
            routing_key=routing_key,
            body=body,
            headers=headers,
            priority=priority,
            ttl=ttl
        )

    async def subscribe(
        self,
        queue: str,
        callback: Callable[[Message], None],
        ack_mode: AckMode = AckMode.MANUAL
    ) -> Consumer:
        """Subscribe to a queue."""
        return await self.broker.consume(queue, callback, ack_mode)

    def ack(self, queue: str, message_id: str) -> bool:
        """Acknowledge a message."""
        return self.broker.ack(queue, message_id)

    def nack(self, queue: str, message_id: str, requeue: bool = True) -> bool:
        """Negative acknowledge a message."""
        return self.broker.nack(queue, message_id, requeue)

    # ========================================================================
    # DECORATORS
    # ========================================================================

    def listener(
        self,
        queue: str,
        ack_mode: AckMode = AckMode.AUTO
    ) -> Callable:
        """Decorator to register a queue listener."""
        def decorator(func: Callable) -> Callable:
            async def start_listener():
                await self.subscribe(queue, func, ack_mode)

            # Store for later initialization
            if not hasattr(self, '_pending_listeners'):
                self._pending_listeners = []
            self._pending_listeners.append(start_listener)

            return func
        return decorator

    async def start_listeners(self) -> None:
        """Start all registered listeners."""
        if hasattr(self, '_pending_listeners'):
            for start_listener in self._pending_listeners:
                await start_listener()

    # ========================================================================
    # RPC PATTERN
    # ========================================================================

    async def call(
        self,
        routing_key: str,
        body: Any,
        exchange: str = "",
        timeout: float = 30.0
    ) -> Any:
        """RPC call pattern."""
        correlation_id = str(uuid.uuid4())
        reply_queue = f"rpc.reply.{correlation_id}"

        # Create reply queue
        self.queues.declare(reply_queue, QueueConfig(exclusive=True, auto_delete=True))

        # Publish with reply_to
        await self.broker.publish(
            exchange=exchange,
            routing_key=routing_key,
            body=body,
            correlation_id=correlation_id
        )

        # Wait for response
        result = asyncio.Future()

        async def on_response(message: Message):
            if message.correlation_id == correlation_id:
                result.set_result(message.body)

        consumer = await self.subscribe(reply_queue, on_response, AckMode.AUTO)

        try:
            return await asyncio.wait_for(result, timeout)
        finally:
            await self.broker.cancel(consumer.id)
            self.queues.delete(reply_queue)

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'queues': [
                {
                    'name': q.name,
                    'messages': len(q.messages),
                    'consumers': q.consumer_count
                }
                for q in self.queues.list()
            ],
            'exchanges': [
                {
                    'name': e.name,
                    'type': e.exchange_type.value,
                    'bindings': sum(len(b) for b in e.bindings.values())
                }
                for e in self.exchanges.list()
            ],
            'statistics': self.broker.get_stats()
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

message_queue = MessageQueueEngine()
