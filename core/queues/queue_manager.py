#!/usr/bin/env python3
"""
BAEL - Queue Manager
Advanced queue management for AI agent operations.

Features:
- Priority queues
- Delayed queues
- Dead letter queues
- Queue consumers
- Message acknowledgment
- Message expiry
- Queue metrics
- Batch operations
- Poison message handling
- Queue persistence
"""

import asyncio
import heapq
import json
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
M = TypeVar('M')


# =============================================================================
# ENUMS
# =============================================================================

class QueueType(Enum):
    """Queue types."""
    FIFO = "fifo"
    LIFO = "lifo"
    PRIORITY = "priority"
    DELAYED = "delayed"


class MessageState(Enum):
    """Message states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    DEAD = "dead"


class AckMode(Enum):
    """Acknowledgment modes."""
    AUTO = "auto"
    MANUAL = "manual"
    BATCH = "batch"


class ConsumerState(Enum):
    """Consumer states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass(order=True)
class Message:
    """Queue message."""
    priority: int = field(default=0, compare=True)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    payload: Any = field(default=None, compare=False)
    headers: Dict[str, Any] = field(default_factory=dict, compare=False)
    created_at: datetime = field(default_factory=datetime.utcnow, compare=False)
    scheduled_at: Optional[datetime] = field(default=None, compare=False)
    expires_at: Optional[datetime] = field(default=None, compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    state: MessageState = field(default=MessageState.PENDING, compare=False)
    correlation_id: Optional[str] = field(default=None, compare=False)
    reply_to: Optional[str] = field(default=None, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "priority": self.priority,
            "payload": self.payload,
            "headers": self.headers,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "state": self.state.value,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            priority=data.get("priority", 0),
            payload=data.get("payload"),
            headers=data.get("headers", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            state=MessageState(data.get("state", "pending")),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to")
        )


@dataclass
class QueueConfig:
    """Queue configuration."""
    name: str = "default"
    queue_type: QueueType = QueueType.FIFO
    max_size: int = 0  # 0 = unlimited
    default_ttl: Optional[timedelta] = None
    dead_letter_queue: Optional[str] = None
    max_retries: int = 3
    visibility_timeout: float = 30.0
    ack_mode: AckMode = AckMode.AUTO


@dataclass
class QueueStats:
    """Queue statistics."""
    name: str = ""
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    dead: int = 0
    total_enqueued: int = 0
    total_dequeued: int = 0
    average_wait_time: float = 0.0
    average_process_time: float = 0.0


@dataclass
class ConsumerConfig:
    """Consumer configuration."""
    consumer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    queue_name: str = ""
    batch_size: int = 1
    poll_interval: float = 0.1
    max_concurrent: int = 1


# =============================================================================
# QUEUE IMPLEMENTATIONS
# =============================================================================

class BaseQueue(ABC, Generic[T]):
    """Base queue interface."""

    @abstractmethod
    def push(self, item: T) -> None:
        """Push item to queue."""
        pass

    @abstractmethod
    def pop(self) -> Optional[T]:
        """Pop item from queue."""
        pass

    @abstractmethod
    def peek(self) -> Optional[T]:
        """Peek at front item."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get queue size."""
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        """Check if empty."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear queue."""
        pass


class FIFOQueue(BaseQueue[T]):
    """First-in-first-out queue."""

    def __init__(self, max_size: int = 0):
        self.max_size = max_size
        self._items: List[T] = []
        self._lock = threading.RLock()

    def push(self, item: T) -> None:
        with self._lock:
            if self.max_size > 0 and len(self._items) >= self.max_size:
                raise QueueFullError("Queue is full")
            self._items.append(item)

    def pop(self) -> Optional[T]:
        with self._lock:
            if self._items:
                return self._items.pop(0)
            return None

    def peek(self) -> Optional[T]:
        with self._lock:
            return self._items[0] if self._items else None

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._items) == 0

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class LIFOQueue(BaseQueue[T]):
    """Last-in-first-out queue (stack)."""

    def __init__(self, max_size: int = 0):
        self.max_size = max_size
        self._items: List[T] = []
        self._lock = threading.RLock()

    def push(self, item: T) -> None:
        with self._lock:
            if self.max_size > 0 and len(self._items) >= self.max_size:
                raise QueueFullError("Queue is full")
            self._items.append(item)

    def pop(self) -> Optional[T]:
        with self._lock:
            if self._items:
                return self._items.pop()
            return None

    def peek(self) -> Optional[T]:
        with self._lock:
            return self._items[-1] if self._items else None

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._items) == 0

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class PriorityQueue(BaseQueue[T]):
    """Priority queue using heap."""

    def __init__(self, max_size: int = 0):
        self.max_size = max_size
        self._heap: List[T] = []
        self._lock = threading.RLock()

    def push(self, item: T) -> None:
        with self._lock:
            if self.max_size > 0 and len(self._heap) >= self.max_size:
                raise QueueFullError("Queue is full")
            heapq.heappush(self._heap, item)

    def pop(self) -> Optional[T]:
        with self._lock:
            if self._heap:
                return heapq.heappop(self._heap)
            return None

    def peek(self) -> Optional[T]:
        with self._lock:
            return self._heap[0] if self._heap else None

    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._heap) == 0

    def clear(self) -> None:
        with self._lock:
            self._heap.clear()


class DelayedQueue(BaseQueue[T]):
    """Delayed queue with scheduled delivery."""

    def __init__(self, max_size: int = 0):
        self.max_size = max_size
        self._items: List[Tuple[datetime, T]] = []
        self._lock = threading.RLock()

    def push(self, item: T, delay: Optional[timedelta] = None) -> None:
        with self._lock:
            if self.max_size > 0 and len(self._items) >= self.max_size:
                raise QueueFullError("Queue is full")

            scheduled = datetime.utcnow()
            if delay:
                scheduled += delay

            self._items.append((scheduled, item))
            self._items.sort(key=lambda x: x[0])

    def pop(self) -> Optional[T]:
        with self._lock:
            now = datetime.utcnow()
            for i, (scheduled, item) in enumerate(self._items):
                if scheduled <= now:
                    del self._items[i]
                    return item
            return None

    def peek(self) -> Optional[T]:
        with self._lock:
            now = datetime.utcnow()
            for scheduled, item in self._items:
                if scheduled <= now:
                    return item
            return None

    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def ready_count(self) -> int:
        """Count of ready items."""
        with self._lock:
            now = datetime.utcnow()
            return sum(1 for s, _ in self._items if s <= now)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._items) == 0

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class QueueFullError(Exception):
    """Queue is full."""
    pass


# =============================================================================
# MESSAGE QUEUE
# =============================================================================

class MessageQueue:
    """
    Message queue with full message lifecycle.
    """

    def __init__(self, config: Optional[QueueConfig] = None):
        self.config = config or QueueConfig()
        self._queue = self._create_queue()
        self._processing: Dict[str, Message] = {}
        self._dead_letters: List[Message] = []
        self._lock = threading.RLock()

        # Stats
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._completed = 0
        self._failed = 0
        self._wait_times: List[float] = []
        self._process_times: List[float] = []

    def _create_queue(self) -> BaseQueue[Message]:
        """Create underlying queue."""
        if self.config.queue_type == QueueType.FIFO:
            return FIFOQueue(self.config.max_size)
        elif self.config.queue_type == QueueType.LIFO:
            return LIFOQueue(self.config.max_size)
        elif self.config.queue_type == QueueType.PRIORITY:
            return PriorityQueue(self.config.max_size)
        elif self.config.queue_type == QueueType.DELAYED:
            return DelayedQueue(self.config.max_size)
        else:
            return FIFOQueue(self.config.max_size)

    def enqueue(
        self,
        payload: Any,
        priority: int = 0,
        delay: Optional[timedelta] = None,
        ttl: Optional[timedelta] = None,
        headers: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Message:
        """Enqueue a message."""
        message = Message(
            priority=-priority,  # Negative for max-heap behavior
            payload=payload,
            headers=headers or {},
            scheduled_at=datetime.utcnow() + delay if delay else None,
            expires_at=datetime.utcnow() + (ttl or self.config.default_ttl) if (ttl or self.config.default_ttl) else None,
            max_retries=self.config.max_retries,
            correlation_id=correlation_id,
            reply_to=reply_to
        )

        with self._lock:
            if isinstance(self._queue, DelayedQueue):
                self._queue.push(message, delay)
            else:
                self._queue.push(message)

            self._total_enqueued += 1

        return message

    def dequeue(self) -> Optional[Message]:
        """Dequeue a message."""
        with self._lock:
            message = self._queue.pop()

            if message:
                # Check expiry
                if message.expires_at and message.expires_at < datetime.utcnow():
                    message.state = MessageState.EXPIRED
                    return self.dequeue()

                message.state = MessageState.PROCESSING
                self._processing[message.message_id] = message
                self._total_dequeued += 1

                # Track wait time
                wait_time = (datetime.utcnow() - message.created_at).total_seconds()
                self._wait_times.append(wait_time)
                if len(self._wait_times) > 1000:
                    self._wait_times = self._wait_times[-1000:]

        return message

    def dequeue_batch(self, count: int) -> List[Message]:
        """Dequeue multiple messages."""
        messages = []
        for _ in range(count):
            msg = self.dequeue()
            if msg:
                messages.append(msg)
            else:
                break
        return messages

    def ack(self, message_id: str) -> bool:
        """Acknowledge message processing."""
        with self._lock:
            if message_id in self._processing:
                message = self._processing.pop(message_id)
                message.state = MessageState.COMPLETED
                self._completed += 1

                # Track process time
                proc_time = (datetime.utcnow() - message.created_at).total_seconds()
                self._process_times.append(proc_time)
                if len(self._process_times) > 1000:
                    self._process_times = self._process_times[-1000:]

                return True
        return False

    def nack(self, message_id: str, requeue: bool = True) -> bool:
        """Negative acknowledge - message processing failed."""
        with self._lock:
            if message_id in self._processing:
                message = self._processing.pop(message_id)
                message.retry_count += 1

                if requeue and message.retry_count < message.max_retries:
                    message.state = MessageState.PENDING
                    self._queue.push(message)
                else:
                    message.state = MessageState.DEAD
                    self._dead_letters.append(message)
                    self._failed += 1

                return True
        return False

    def reject(self, message_id: str) -> bool:
        """Reject message completely."""
        with self._lock:
            if message_id in self._processing:
                message = self._processing.pop(message_id)
                message.state = MessageState.FAILED
                self._failed += 1
                return True
        return False

    def peek(self) -> Optional[Message]:
        """Peek at next message."""
        with self._lock:
            return self._queue.peek()

    def size(self) -> int:
        """Get pending queue size."""
        with self._lock:
            return self._queue.size()

    def processing_count(self) -> int:
        """Get processing count."""
        with self._lock:
            return len(self._processing)

    def dead_letter_count(self) -> int:
        """Get dead letter count."""
        with self._lock:
            return len(self._dead_letters)

    def get_dead_letters(self) -> List[Message]:
        """Get dead letter messages."""
        with self._lock:
            return self._dead_letters.copy()

    def requeue_dead_letters(self) -> int:
        """Requeue all dead letters."""
        with self._lock:
            count = len(self._dead_letters)
            for msg in self._dead_letters:
                msg.state = MessageState.PENDING
                msg.retry_count = 0
                self._queue.push(msg)
            self._dead_letters.clear()
            return count

    def purge(self) -> int:
        """Purge all pending messages."""
        with self._lock:
            count = self._queue.size()
            self._queue.clear()
            return count

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        with self._lock:
            return QueueStats(
                name=self.config.name,
                pending=self._queue.size(),
                processing=len(self._processing),
                completed=self._completed,
                failed=self._failed,
                dead=len(self._dead_letters),
                total_enqueued=self._total_enqueued,
                total_dequeued=self._total_dequeued,
                average_wait_time=sum(self._wait_times) / len(self._wait_times) if self._wait_times else 0,
                average_process_time=sum(self._process_times) / len(self._process_times) if self._process_times else 0
            )


# =============================================================================
# CONSUMER
# =============================================================================

class Consumer:
    """
    Queue consumer.
    """

    def __init__(
        self,
        queue: MessageQueue,
        handler: Callable[[Message], Awaitable[bool]],
        config: Optional[ConsumerConfig] = None
    ):
        self.queue = queue
        self.handler = handler
        self.config = config or ConsumerConfig()
        self.state = ConsumerState.IDLE
        self._task: Optional[asyncio.Task] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._processed = 0
        self._errors = 0

    async def start(self) -> None:
        """Start consuming."""
        if self.state == ConsumerState.RUNNING:
            return

        self.state = ConsumerState.RUNNING
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """Stop consuming."""
        self.state = ConsumerState.STOPPED

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def pause(self) -> None:
        """Pause consuming."""
        self.state = ConsumerState.PAUSED

    async def resume(self) -> None:
        """Resume consuming."""
        if self.state == ConsumerState.PAUSED:
            self.state = ConsumerState.RUNNING

    async def _consume_loop(self) -> None:
        """Main consume loop."""
        while self.state != ConsumerState.STOPPED:
            if self.state == ConsumerState.PAUSED:
                await asyncio.sleep(self.config.poll_interval)
                continue

            # Get batch of messages
            messages = self.queue.dequeue_batch(self.config.batch_size)

            if not messages:
                await asyncio.sleep(self.config.poll_interval)
                continue

            # Process messages
            tasks = []
            for msg in messages:
                task = asyncio.create_task(
                    self._process_message(msg)
                )
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_message(self, message: Message) -> None:
        """Process a single message."""
        async with self._semaphore:
            try:
                success = await self.handler(message)

                if success:
                    self.queue.ack(message.message_id)
                    self._processed += 1
                else:
                    self.queue.nack(message.message_id)
                    self._errors += 1

            except Exception:
                self.queue.nack(message.message_id)
                self._errors += 1

    @property
    def processed_count(self) -> int:
        """Get processed count."""
        return self._processed

    @property
    def error_count(self) -> int:
        """Get error count."""
        return self._errors


# =============================================================================
# REQUEST-REPLY
# =============================================================================

class RequestReply:
    """
    Request-reply pattern implementation.
    """

    def __init__(self, queue_manager: 'QueueManager'):
        self.queue_manager = queue_manager
        self._pending: Dict[str, asyncio.Future] = {}
        self._reply_queue = queue_manager.create("_replies")
        self._consumer: Optional[Consumer] = None

    async def start(self) -> None:
        """Start reply consumer."""
        async def handle_reply(msg: Message) -> bool:
            correlation_id = msg.correlation_id
            if correlation_id and correlation_id in self._pending:
                future = self._pending.pop(correlation_id)
                future.set_result(msg.payload)
            return True

        self._consumer = Consumer(
            self._reply_queue,
            handle_reply
        )
        await self._consumer.start()

    async def stop(self) -> None:
        """Stop reply consumer."""
        if self._consumer:
            await self._consumer.stop()

    async def request(
        self,
        queue_name: str,
        payload: Any,
        timeout: float = 30.0
    ) -> Any:
        """Send request and wait for reply."""
        correlation_id = str(uuid.uuid4())

        # Create pending future
        future = asyncio.get_event_loop().create_future()
        self._pending[correlation_id] = future

        # Send request
        queue = self.queue_manager.get(queue_name)
        if queue:
            queue.enqueue(
                payload,
                correlation_id=correlation_id,
                reply_to="_replies"
            )

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(correlation_id, None)
            raise

    def reply(self, original: Message, response: Any) -> None:
        """Send reply to request."""
        if original.reply_to:
            queue = self.queue_manager.get(original.reply_to)
            if queue:
                queue.enqueue(
                    response,
                    correlation_id=original.correlation_id
                )


# =============================================================================
# QUEUE MANAGER
# =============================================================================

class QueueManager:
    """
    Queue Manager for BAEL.

    Advanced queue management.
    """

    def __init__(self):
        self._queues: Dict[str, MessageQueue] = {}
        self._consumers: Dict[str, Consumer] = {}
        self._request_reply: Optional[RequestReply] = None
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # QUEUE OPERATIONS
    # -------------------------------------------------------------------------

    def create(
        self,
        name: str,
        queue_type: QueueType = QueueType.FIFO,
        max_size: int = 0,
        dead_letter_queue: Optional[str] = None,
        max_retries: int = 3,
        **kwargs: Any
    ) -> MessageQueue:
        """Create a queue."""
        with self._lock:
            if name not in self._queues:
                config = QueueConfig(
                    name=name,
                    queue_type=queue_type,
                    max_size=max_size,
                    dead_letter_queue=dead_letter_queue,
                    max_retries=max_retries,
                    **kwargs
                )
                self._queues[name] = MessageQueue(config)
            return self._queues[name]

    def get(self, name: str) -> Optional[MessageQueue]:
        """Get queue by name."""
        with self._lock:
            return self._queues.get(name)

    def delete(self, name: str) -> bool:
        """Delete a queue."""
        with self._lock:
            if name in self._queues:
                del self._queues[name]
                return True
            return False

    def list_queues(self) -> List[str]:
        """List all queues."""
        with self._lock:
            return list(self._queues.keys())

    # -------------------------------------------------------------------------
    # MESSAGE OPERATIONS
    # -------------------------------------------------------------------------

    def enqueue(
        self,
        queue_name: str,
        payload: Any,
        priority: int = 0,
        delay: Optional[timedelta] = None,
        **kwargs: Any
    ) -> Optional[Message]:
        """Enqueue message to queue."""
        queue = self.get(queue_name)
        if queue:
            return queue.enqueue(payload, priority, delay, **kwargs)
        return None

    def dequeue(self, queue_name: str) -> Optional[Message]:
        """Dequeue message from queue."""
        queue = self.get(queue_name)
        if queue:
            return queue.dequeue()
        return None

    def ack(self, queue_name: str, message_id: str) -> bool:
        """Acknowledge message."""
        queue = self.get(queue_name)
        if queue:
            return queue.ack(message_id)
        return False

    def nack(self, queue_name: str, message_id: str, requeue: bool = True) -> bool:
        """Negative acknowledge message."""
        queue = self.get(queue_name)
        if queue:
            return queue.nack(message_id, requeue)
        return False

    # -------------------------------------------------------------------------
    # CONSUMER OPERATIONS
    # -------------------------------------------------------------------------

    async def consume(
        self,
        queue_name: str,
        handler: Callable[[Message], Awaitable[bool]],
        batch_size: int = 1,
        max_concurrent: int = 1
    ) -> str:
        """Start consuming from queue."""
        queue = self.get(queue_name)
        if not queue:
            queue = self.create(queue_name)

        config = ConsumerConfig(
            queue_name=queue_name,
            batch_size=batch_size,
            max_concurrent=max_concurrent
        )

        consumer = Consumer(queue, handler, config)
        await consumer.start()

        with self._lock:
            self._consumers[config.consumer_id] = consumer

        return config.consumer_id

    async def stop_consumer(self, consumer_id: str) -> None:
        """Stop a consumer."""
        with self._lock:
            consumer = self._consumers.get(consumer_id)

        if consumer:
            await consumer.stop()

            with self._lock:
                del self._consumers[consumer_id]

    async def pause_consumer(self, consumer_id: str) -> None:
        """Pause a consumer."""
        with self._lock:
            consumer = self._consumers.get(consumer_id)

        if consumer:
            await consumer.pause()

    async def resume_consumer(self, consumer_id: str) -> None:
        """Resume a consumer."""
        with self._lock:
            consumer = self._consumers.get(consumer_id)

        if consumer:
            await consumer.resume()

    def list_consumers(self) -> List[Dict[str, Any]]:
        """List all consumers."""
        with self._lock:
            return [
                {
                    "consumer_id": c.config.consumer_id,
                    "queue_name": c.config.queue_name,
                    "state": c.state.value,
                    "processed": c.processed_count,
                    "errors": c.error_count
                }
                for c in self._consumers.values()
            ]

    # -------------------------------------------------------------------------
    # REQUEST-REPLY
    # -------------------------------------------------------------------------

    async def enable_request_reply(self) -> RequestReply:
        """Enable request-reply pattern."""
        if not self._request_reply:
            self._request_reply = RequestReply(self)
            await self._request_reply.start()
        return self._request_reply

    async def request(
        self,
        queue_name: str,
        payload: Any,
        timeout: float = 30.0
    ) -> Any:
        """Send request and wait for reply."""
        if not self._request_reply:
            await self.enable_request_reply()
        return await self._request_reply.request(queue_name, payload, timeout)

    def reply(self, original: Message, response: Any) -> None:
        """Send reply."""
        if self._request_reply:
            self._request_reply.reply(original, response)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self, queue_name: str) -> Optional[QueueStats]:
        """Get queue statistics."""
        queue = self.get(queue_name)
        if queue:
            return queue.get_stats()
        return None

    def get_all_stats(self) -> Dict[str, QueueStats]:
        """Get stats for all queues."""
        with self._lock:
            return {
                name: queue.get_stats()
                for name, queue in self._queues.items()
            }

    # -------------------------------------------------------------------------
    # DEAD LETTERS
    # -------------------------------------------------------------------------

    def get_dead_letters(self, queue_name: str) -> List[Message]:
        """Get dead letter messages."""
        queue = self.get(queue_name)
        if queue:
            return queue.get_dead_letters()
        return []

    def requeue_dead_letters(self, queue_name: str) -> int:
        """Requeue dead letters."""
        queue = self.get(queue_name)
        if queue:
            return queue.requeue_dead_letters()
        return 0

    # -------------------------------------------------------------------------
    # PURGE
    # -------------------------------------------------------------------------

    def purge(self, queue_name: str) -> int:
        """Purge queue."""
        queue = self.get(queue_name)
        if queue:
            return queue.purge()
        return 0

    def purge_all(self) -> int:
        """Purge all queues."""
        total = 0
        with self._lock:
            for queue in self._queues.values():
                total += queue.purge()
        return total

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------

    async def shutdown(self) -> None:
        """Shutdown all consumers."""
        consumer_ids = list(self._consumers.keys())
        for cid in consumer_ids:
            await self.stop_consumer(cid)

        if self._request_reply:
            await self._request_reply.stop()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Queue Manager."""
    print("=" * 70)
    print("BAEL - QUEUE MANAGER DEMO")
    print("Advanced Queue Management for AI Agents")
    print("=" * 70)
    print()

    manager = QueueManager()

    # 1. Basic Queue
    print("1. BASIC QUEUE:")
    print("-" * 40)

    queue = manager.create("tasks", queue_type=QueueType.FIFO)

    # Enqueue
    msg1 = queue.enqueue({"action": "process", "id": 1})
    msg2 = queue.enqueue({"action": "process", "id": 2})
    msg3 = queue.enqueue({"action": "process", "id": 3})

    print(f"   Enqueued 3 messages")
    print(f"   Queue size: {queue.size()}")

    # Dequeue
    msg = queue.dequeue()
    if msg:
        print(f"   Dequeued: {msg.payload}")
        queue.ack(msg.message_id)
    print()

    # 2. Priority Queue
    print("2. PRIORITY QUEUE:")
    print("-" * 40)

    pqueue = manager.create("priority-tasks", queue_type=QueueType.PRIORITY)

    pqueue.enqueue({"task": "low"}, priority=1)
    pqueue.enqueue({"task": "high"}, priority=10)
    pqueue.enqueue({"task": "medium"}, priority=5)

    # Dequeue in priority order
    while pqueue.size() > 0:
        msg = pqueue.dequeue()
        if msg:
            print(f"   Priority {-msg.priority}: {msg.payload}")
            pqueue.ack(msg.message_id)
    print()

    # 3. Delayed Queue
    print("3. DELAYED QUEUE:")
    print("-" * 40)

    dqueue = manager.create("delayed", queue_type=QueueType.DELAYED)

    # Immediate
    dqueue.enqueue({"type": "immediate"})

    # Delayed
    dqueue.enqueue({"type": "delayed"}, delay=timedelta(seconds=0.5))

    msg = dqueue.dequeue()
    if msg:
        print(f"   Got: {msg.payload}")
        dqueue.ack(msg.message_id)

    msg2 = dqueue.dequeue()
    print(f"   Delayed (not ready yet): {msg2}")

    await asyncio.sleep(0.6)

    msg2 = dqueue.dequeue()
    if msg2:
        print(f"   After delay: {msg2.payload}")
        dqueue.ack(msg2.message_id)
    print()

    # 4. Consumer
    print("4. CONSUMER:")
    print("-" * 40)

    work_queue = manager.create("work")

    processed = []

    async def handler(msg: Message) -> bool:
        processed.append(msg.payload)
        return True

    # Enqueue work
    for i in range(5):
        work_queue.enqueue({"job": i})

    # Start consumer
    consumer_id = await manager.consume(
        "work",
        handler,
        batch_size=2
    )

    # Wait for processing
    await asyncio.sleep(0.5)

    print(f"   Processed: {processed}")

    await manager.stop_consumer(consumer_id)
    print()

    # 5. Dead Letters
    print("5. DEAD LETTERS:")
    print("-" * 40)

    dlq = manager.create("failing", max_retries=2)
    dlq.enqueue({"will": "fail"})

    msg = dlq.dequeue()
    if msg:
        # Fail it multiple times
        for _ in range(3):
            dlq.nack(msg.message_id)
            if dlq.size() > 0:
                msg = dlq.dequeue()

    dead = dlq.get_dead_letters()
    print(f"   Dead letters: {len(dead)}")

    requeued = dlq.requeue_dead_letters()
    print(f"   Requeued: {requeued}")
    print()

    # 6. Queue Statistics
    print("6. QUEUE STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats("work")
    if stats:
        print(f"   Queue: {stats.name}")
        print(f"   Total enqueued: {stats.total_enqueued}")
        print(f"   Total dequeued: {stats.total_dequeued}")
        print(f"   Completed: {stats.completed}")
    print()

    # 7. Message Headers
    print("7. MESSAGE HEADERS:")
    print("-" * 40)

    hqueue = manager.create("headers")
    msg = hqueue.enqueue(
        {"data": "value"},
        headers={
            "content-type": "application/json",
            "priority": "high",
            "source": "api"
        }
    )
    print(f"   Headers: {msg.headers}")
    print()

    # 8. Message Serialization
    print("8. MESSAGE SERIALIZATION:")
    print("-" * 40)

    msg_dict = msg.to_dict()
    print(f"   Serialized keys: {list(msg_dict.keys())}")

    restored = Message.from_dict(msg_dict)
    print(f"   Restored payload: {restored.payload}")
    print()

    # 9. Batch Operations
    print("9. BATCH OPERATIONS:")
    print("-" * 40)

    batch_queue = manager.create("batch")

    for i in range(10):
        batch_queue.enqueue({"item": i})

    batch = batch_queue.dequeue_batch(5)
    print(f"   Dequeued batch: {len(batch)}")

    for msg in batch:
        batch_queue.ack(msg.message_id)
    print(f"   Remaining: {batch_queue.size()}")
    print()

    # 10. Queue Types
    print("10. QUEUE TYPES:")
    print("-" * 40)

    # LIFO
    lifo = manager.create("stack", queue_type=QueueType.LIFO)
    lifo.enqueue("first")
    lifo.enqueue("second")
    lifo.enqueue("third")

    msg = lifo.dequeue()
    if msg:
        print(f"   LIFO (stack): {msg.payload}")
    print()

    # 11. All Stats
    print("11. ALL QUEUE STATS:")
    print("-" * 40)

    all_stats = manager.get_all_stats()
    for name, stats in all_stats.items():
        if not name.startswith("_"):
            print(f"   {name}: pending={stats.pending}, "
                  f"completed={stats.completed}")
    print()

    # 12. Consumer List
    print("12. CONSUMER LIST:")
    print("-" * 40)

    # Start a consumer
    test_queue = manager.create("test-consume")
    cid = await manager.consume("test-consume", handler)

    consumers = manager.list_consumers()
    for c in consumers:
        print(f"   Consumer {c['consumer_id'][:8]}...: {c['state']}")

    await manager.stop_consumer(cid)
    print()

    # 13. Purge
    print("13. PURGE:")
    print("-" * 40)

    purge_queue = manager.create("purge-me")
    for i in range(10):
        purge_queue.enqueue(f"item-{i}")

    print(f"   Before purge: {purge_queue.size()}")
    purged = manager.purge("purge-me")
    print(f"   Purged: {purged}")
    print(f"   After purge: {purge_queue.size()}")
    print()

    # Shutdown
    await manager.shutdown()

    print("=" * 70)
    print("DEMO COMPLETE - Queue Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
