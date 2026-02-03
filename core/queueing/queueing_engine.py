#!/usr/bin/env python3
"""
BAEL - Queueing Engine
Message queueing for agents.

Features:
- Multiple queue types
- Priority queuing
- Dead letter queues
- Message acknowledgment
- Consumer groups
"""

import asyncio
import hashlib
import heapq
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, Iterator, List, Optional, Set, Tuple,
    Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class QueueType(Enum):
    """Queue types."""
    FIFO = "fifo"
    LIFO = "lifo"
    PRIORITY = "priority"
    DELAY = "delay"


class MessageStatus(Enum):
    """Message statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    DEAD = "dead"
    EXPIRED = "expired"


class MessagePriority(Enum):
    """Message priorities."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
    CRITICAL = 4


class DeliveryMode(Enum):
    """Delivery modes."""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class AckMode(Enum):
    """Acknowledgment modes."""
    AUTO = "auto"
    MANUAL = "manual"
    BATCH = "batch"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Message:
    """A queue message."""
    message_id: str = ""
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    delay_until: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    consumer_id: Optional[str] = None
    delivery_tag: str = ""
    correlation_id: str = ""
    reply_to: str = ""
    
    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())[:12]
        if not self.delivery_tag:
            self.delivery_tag = str(uuid.uuid4())[:8]
    
    def __lt__(self, other: "Message") -> bool:
        """Compare for priority queue."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at
    
    def is_expired(self) -> bool:
        """Check if message is expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False
    
    def is_ready(self) -> bool:
        """Check if message is ready for delivery."""
        if self.delay_until:
            return datetime.now() >= self.delay_until
        return True


@dataclass
class QueueStats:
    """Queue statistics."""
    queue_name: str = ""
    message_count: int = 0
    pending_count: int = 0
    processing_count: int = 0
    acknowledged_count: int = 0
    rejected_count: int = 0
    dead_count: int = 0
    consumer_count: int = 0


@dataclass
class ConsumerInfo:
    """Consumer information."""
    consumer_id: str = ""
    queue_name: str = ""
    group_id: str = ""
    callback: Optional[Callable] = None
    active: bool = True
    messages_consumed: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.consumer_id:
            self.consumer_id = str(uuid.uuid4())[:8]


@dataclass
class QueueConfig:
    """Queue configuration."""
    max_size: int = 10000
    max_retries: int = 3
    message_ttl_seconds: Optional[float] = None
    dead_letter_queue: Optional[str] = None
    delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE
    ack_mode: AckMode = AckMode.MANUAL


@dataclass
class QueueingConfig:
    """Queueing engine configuration."""
    default_queue_config: QueueConfig = field(default_factory=QueueConfig)
    enable_dead_letter: bool = True
    default_message_ttl: Optional[float] = None


# =============================================================================
# BASE QUEUE
# =============================================================================

class BaseQueue(ABC):
    """Base queue interface."""
    
    @abstractmethod
    def enqueue(self, message: Message) -> str:
        """Enqueue a message."""
        pass
    
    @abstractmethod
    def dequeue(self) -> Optional[Message]:
        """Dequeue a message."""
        pass
    
    @abstractmethod
    def peek(self) -> Optional[Message]:
        """Peek at next message."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get queue size."""
        pass
    
    @abstractmethod
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """Clear the queue."""
        pass


class FIFOQueue(BaseQueue):
    """First-In-First-Out queue."""
    
    def __init__(self):
        self._queue: deque = deque()
    
    def enqueue(self, message: Message) -> str:
        self._queue.append(message)
        return message.message_id
    
    def dequeue(self) -> Optional[Message]:
        if self._queue:
            return self._queue.popleft()
        return None
    
    def peek(self) -> Optional[Message]:
        if self._queue:
            return self._queue[0]
        return None
    
    def size(self) -> int:
        return len(self._queue)
    
    def is_empty(self) -> bool:
        return len(self._queue) == 0
    
    def clear(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        return count


class LIFOQueue(BaseQueue):
    """Last-In-First-Out queue (stack)."""
    
    def __init__(self):
        self._stack: List[Message] = []
    
    def enqueue(self, message: Message) -> str:
        self._stack.append(message)
        return message.message_id
    
    def dequeue(self) -> Optional[Message]:
        if self._stack:
            return self._stack.pop()
        return None
    
    def peek(self) -> Optional[Message]:
        if self._stack:
            return self._stack[-1]
        return None
    
    def size(self) -> int:
        return len(self._stack)
    
    def is_empty(self) -> bool:
        return len(self._stack) == 0
    
    def clear(self) -> int:
        count = len(self._stack)
        self._stack.clear()
        return count


class PriorityQueue(BaseQueue):
    """Priority queue."""
    
    def __init__(self):
        self._heap: List[Message] = []
    
    def enqueue(self, message: Message) -> str:
        heapq.heappush(self._heap, message)
        return message.message_id
    
    def dequeue(self) -> Optional[Message]:
        if self._heap:
            return heapq.heappop(self._heap)
        return None
    
    def peek(self) -> Optional[Message]:
        if self._heap:
            return self._heap[0]
        return None
    
    def size(self) -> int:
        return len(self._heap)
    
    def is_empty(self) -> bool:
        return len(self._heap) == 0
    
    def clear(self) -> int:
        count = len(self._heap)
        self._heap.clear()
        return count


class DelayQueue(BaseQueue):
    """Delay queue (messages delivered after delay)."""
    
    def __init__(self):
        self._messages: List[Message] = []
    
    def enqueue(self, message: Message) -> str:
        self._messages.append(message)
        self._messages.sort(key=lambda m: m.delay_until or m.created_at)
        return message.message_id
    
    def dequeue(self) -> Optional[Message]:
        now = datetime.now()
        
        for i, msg in enumerate(self._messages):
            if msg.is_ready():
                return self._messages.pop(i)
        
        return None
    
    def peek(self) -> Optional[Message]:
        for msg in self._messages:
            if msg.is_ready():
                return msg
        return None
    
    def size(self) -> int:
        return len(self._messages)
    
    def is_empty(self) -> bool:
        return len(self._messages) == 0
    
    def clear(self) -> int:
        count = len(self._messages)
        self._messages.clear()
        return count


# =============================================================================
# QUEUE FACTORY
# =============================================================================

class QueueFactory:
    """Create queues."""
    
    _registry: Dict[QueueType, Type[BaseQueue]] = {
        QueueType.FIFO: FIFOQueue,
        QueueType.LIFO: LIFOQueue,
        QueueType.PRIORITY: PriorityQueue,
        QueueType.DELAY: DelayQueue,
    }
    
    @classmethod
    def create(cls, queue_type: QueueType) -> BaseQueue:
        """Create a queue."""
        queue_class = cls._registry.get(queue_type, FIFOQueue)
        return queue_class()
    
    @classmethod
    def register(cls, queue_type: QueueType, queue_class: Type[BaseQueue]) -> None:
        """Register a queue type."""
        cls._registry[queue_type] = queue_class


# =============================================================================
# MESSAGE STORE
# =============================================================================

class MessageStore:
    """Store messages for tracking."""
    
    def __init__(self):
        self._messages: Dict[str, Message] = {}
        self._by_status: Dict[MessageStatus, Set[str]] = defaultdict(set)
    
    def add(self, message: Message) -> str:
        """Add a message."""
        self._messages[message.message_id] = message
        self._by_status[message.status].add(message.message_id)
        return message.message_id
    
    def get(self, message_id: str) -> Optional[Message]:
        """Get a message."""
        return self._messages.get(message_id)
    
    def update_status(self, message_id: str, status: MessageStatus) -> bool:
        """Update message status."""
        message = self._messages.get(message_id)
        
        if message:
            self._by_status[message.status].discard(message_id)
            message.status = status
            self._by_status[status].add(message_id)
            return True
        
        return False
    
    def remove(self, message_id: str) -> bool:
        """Remove a message."""
        message = self._messages.get(message_id)
        
        if message:
            self._by_status[message.status].discard(message_id)
            del self._messages[message_id]
            return True
        
        return False
    
    def get_by_status(self, status: MessageStatus) -> List[Message]:
        """Get messages by status."""
        return [
            self._messages[mid] for mid in self._by_status.get(status, set())
            if mid in self._messages
        ]
    
    def count(self) -> int:
        """Count messages."""
        return len(self._messages)
    
    def count_by_status(self) -> Dict[str, int]:
        """Count by status."""
        return {
            status.value: len(ids)
            for status, ids in self._by_status.items()
        }


# =============================================================================
# CONSUMER MANAGER
# =============================================================================

class ConsumerManager:
    """Manage consumers."""
    
    def __init__(self):
        self._consumers: Dict[str, ConsumerInfo] = {}
        self._by_queue: Dict[str, Set[str]] = defaultdict(set)
        self._by_group: Dict[str, Set[str]] = defaultdict(set)
    
    def register(self, consumer: ConsumerInfo) -> str:
        """Register a consumer."""
        self._consumers[consumer.consumer_id] = consumer
        self._by_queue[consumer.queue_name].add(consumer.consumer_id)
        
        if consumer.group_id:
            self._by_group[consumer.group_id].add(consumer.consumer_id)
        
        return consumer.consumer_id
    
    def unregister(self, consumer_id: str) -> bool:
        """Unregister a consumer."""
        consumer = self._consumers.get(consumer_id)
        
        if consumer:
            self._by_queue[consumer.queue_name].discard(consumer_id)
            
            if consumer.group_id:
                self._by_group[consumer.group_id].discard(consumer_id)
            
            del self._consumers[consumer_id]
            return True
        
        return False
    
    def get(self, consumer_id: str) -> Optional[ConsumerInfo]:
        """Get a consumer."""
        return self._consumers.get(consumer_id)
    
    def get_for_queue(self, queue_name: str) -> List[ConsumerInfo]:
        """Get consumers for queue."""
        return [
            self._consumers[cid] for cid in self._by_queue.get(queue_name, set())
            if cid in self._consumers
        ]
    
    def get_for_group(self, group_id: str) -> List[ConsumerInfo]:
        """Get consumers in group."""
        return [
            self._consumers[cid] for cid in self._by_group.get(group_id, set())
            if cid in self._consumers
        ]
    
    def count(self) -> int:
        """Count consumers."""
        return len(self._consumers)


# =============================================================================
# MANAGED QUEUE
# =============================================================================

class ManagedQueue:
    """A managed queue with full features."""
    
    def __init__(
        self,
        name: str,
        queue_type: QueueType = QueueType.FIFO,
        config: Optional[QueueConfig] = None
    ):
        self._name = name
        self._type = queue_type
        self._config = config or QueueConfig()
        
        self._queue = QueueFactory.create(queue_type)
        self._processing: Dict[str, Message] = {}
        self._dead_letter: List[Message] = []
        
        self._acknowledged_count = 0
        self._rejected_count = 0
    
    @property
    def name(self) -> str:
        return self._name
    
    def publish(self, message: Message) -> str:
        """Publish a message."""
        if self._config.message_ttl_seconds and not message.expires_at:
            message.expires_at = datetime.now() + timedelta(
                seconds=self._config.message_ttl_seconds
            )
        
        if message.max_retries == 0:
            message.max_retries = self._config.max_retries
        
        return self._queue.enqueue(message)
    
    def consume(self, consumer_id: str) -> Optional[Message]:
        """Consume a message."""
        while True:
            message = self._queue.dequeue()
            
            if message is None:
                return None
            
            if message.is_expired():
                message.status = MessageStatus.EXPIRED
                continue
            
            if not message.is_ready():
                self._queue.enqueue(message)
                return None
            
            message.status = MessageStatus.PROCESSING
            message.consumer_id = consumer_id
            self._processing[message.delivery_tag] = message
            
            if self._config.ack_mode == AckMode.AUTO:
                self.ack(message.delivery_tag)
            
            return message
    
    def ack(self, delivery_tag: str) -> bool:
        """Acknowledge a message."""
        message = self._processing.get(delivery_tag)
        
        if message:
            message.status = MessageStatus.ACKNOWLEDGED
            del self._processing[delivery_tag]
            self._acknowledged_count += 1
            return True
        
        return False
    
    def nack(self, delivery_tag: str, requeue: bool = True) -> bool:
        """Negative acknowledge (reject) a message."""
        message = self._processing.get(delivery_tag)
        
        if message:
            del self._processing[delivery_tag]
            
            if requeue and message.retry_count < message.max_retries:
                message.retry_count += 1
                message.status = MessageStatus.PENDING
                message.consumer_id = None
                self._queue.enqueue(message)
            else:
                message.status = MessageStatus.DEAD
                self._dead_letter.append(message)
                self._rejected_count += 1
            
            return True
        
        return False
    
    def reject(self, delivery_tag: str) -> bool:
        """Reject a message (no requeue)."""
        return self.nack(delivery_tag, requeue=False)
    
    def peek(self) -> Optional[Message]:
        """Peek at next message."""
        return self._queue.peek()
    
    def size(self) -> int:
        """Get total size."""
        return self._queue.size() + len(self._processing)
    
    def pending_size(self) -> int:
        """Get pending size."""
        return self._queue.size()
    
    def processing_size(self) -> int:
        """Get processing size."""
        return len(self._processing)
    
    def dead_letter_size(self) -> int:
        """Get dead letter size."""
        return len(self._dead_letter)
    
    def get_dead_letters(self) -> List[Message]:
        """Get dead letter messages."""
        return list(self._dead_letter)
    
    def requeue_dead_letters(self) -> int:
        """Requeue dead letter messages."""
        count = 0
        
        for message in self._dead_letter[:]:
            message.status = MessageStatus.PENDING
            message.retry_count = 0
            self._queue.enqueue(message)
            self._dead_letter.remove(message)
            count += 1
        
        return count
    
    def purge(self) -> int:
        """Purge all messages."""
        count = self._queue.clear()
        count += len(self._processing)
        self._processing.clear()
        return count
    
    def stats(self) -> QueueStats:
        """Get queue stats."""
        return QueueStats(
            queue_name=self._name,
            message_count=self.size(),
            pending_count=self.pending_size(),
            processing_count=self.processing_size(),
            acknowledged_count=self._acknowledged_count,
            rejected_count=self._rejected_count,
            dead_count=self.dead_letter_size()
        )


# =============================================================================
# QUEUEING ENGINE
# =============================================================================

class QueueingEngine:
    """
    Queueing Engine for BAEL.
    
    Message queueing with consumers and acknowledgments.
    """
    
    def __init__(self, config: Optional[QueueingConfig] = None):
        self._config = config or QueueingConfig()
        
        self._queues: Dict[str, ManagedQueue] = {}
        self._consumers = ConsumerManager()
        self._message_store = MessageStore()
        
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
    
    # ----- Queue Management -----
    
    def create_queue(
        self,
        name: str,
        queue_type: QueueType = QueueType.FIFO,
        config: Optional[QueueConfig] = None
    ) -> ManagedQueue:
        """Create a queue."""
        queue = ManagedQueue(
            name=name,
            queue_type=queue_type,
            config=config or self._config.default_queue_config
        )
        self._queues[name] = queue
        return queue
    
    def get_queue(self, name: str) -> Optional[ManagedQueue]:
        """Get a queue."""
        return self._queues.get(name)
    
    def delete_queue(self, name: str) -> bool:
        """Delete a queue."""
        if name in self._queues:
            del self._queues[name]
            return True
        return False
    
    def list_queues(self) -> List[str]:
        """List queue names."""
        return list(self._queues.keys())
    
    def queue_exists(self, name: str) -> bool:
        """Check if queue exists."""
        return name in self._queues
    
    # ----- Publishing -----
    
    def publish(
        self,
        queue_name: str,
        body: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        headers: Optional[Dict[str, str]] = None,
        delay_seconds: Optional[float] = None,
        ttl_seconds: Optional[float] = None,
        correlation_id: str = "",
        reply_to: str = ""
    ) -> Optional[str]:
        """Publish a message."""
        queue = self._queues.get(queue_name)
        
        if not queue:
            queue = self.create_queue(queue_name)
        
        message = Message(
            body=body,
            headers=headers or {},
            priority=priority,
            correlation_id=correlation_id,
            reply_to=reply_to
        )
        
        if delay_seconds:
            message.delay_until = datetime.now() + timedelta(seconds=delay_seconds)
        
        if ttl_seconds:
            message.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        
        message_id = queue.publish(message)
        self._message_store.add(message)
        
        return message_id
    
    def publish_batch(
        self,
        queue_name: str,
        bodies: List[Any],
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> List[str]:
        """Publish multiple messages."""
        message_ids = []
        
        for body in bodies:
            mid = self.publish(queue_name, body, priority)
            if mid:
                message_ids.append(mid)
        
        return message_ids
    
    # ----- Consuming -----
    
    def consume(
        self,
        queue_name: str,
        consumer_id: Optional[str] = None
    ) -> Optional[Message]:
        """Consume a message."""
        queue = self._queues.get(queue_name)
        
        if not queue:
            return None
        
        consumer_id = consumer_id or str(uuid.uuid4())[:8]
        message = queue.consume(consumer_id)
        
        if message:
            self._message_store.update_status(
                message.message_id,
                MessageStatus.PROCESSING
            )
        
        return message
    
    def consume_batch(
        self,
        queue_name: str,
        max_messages: int = 10,
        consumer_id: Optional[str] = None
    ) -> List[Message]:
        """Consume multiple messages."""
        messages = []
        
        for _ in range(max_messages):
            message = self.consume(queue_name, consumer_id)
            if message:
                messages.append(message)
            else:
                break
        
        return messages
    
    # ----- Acknowledgment -----
    
    def ack(self, queue_name: str, delivery_tag: str) -> bool:
        """Acknowledge a message."""
        queue = self._queues.get(queue_name)
        
        if queue:
            success = queue.ack(delivery_tag)
            if success:
                message = self._get_message_by_tag(delivery_tag)
                if message:
                    self._message_store.update_status(
                        message.message_id,
                        MessageStatus.ACKNOWLEDGED
                    )
            return success
        
        return False
    
    def nack(
        self,
        queue_name: str,
        delivery_tag: str,
        requeue: bool = True
    ) -> bool:
        """Negative acknowledge a message."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.nack(delivery_tag, requeue)
        
        return False
    
    def reject(self, queue_name: str, delivery_tag: str) -> bool:
        """Reject a message."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.reject(delivery_tag)
        
        return False
    
    def _get_message_by_tag(self, delivery_tag: str) -> Optional[Message]:
        """Get message by delivery tag."""
        for queue in self._queues.values():
            if delivery_tag in queue._processing:
                return queue._processing[delivery_tag]
        return None
    
    # ----- Consumer Management -----
    
    def register_consumer(
        self,
        queue_name: str,
        callback: Optional[Callable] = None,
        group_id: str = ""
    ) -> str:
        """Register a consumer."""
        consumer = ConsumerInfo(
            queue_name=queue_name,
            group_id=group_id,
            callback=callback
        )
        
        return self._consumers.register(consumer)
    
    def unregister_consumer(self, consumer_id: str) -> bool:
        """Unregister a consumer."""
        return self._consumers.unregister(consumer_id)
    
    def get_consumers(self, queue_name: str) -> List[ConsumerInfo]:
        """Get consumers for queue."""
        return self._consumers.get_for_queue(queue_name)
    
    # ----- Dead Letter -----
    
    def get_dead_letters(self, queue_name: str) -> List[Message]:
        """Get dead letter messages."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.get_dead_letters()
        
        return []
    
    def requeue_dead_letters(self, queue_name: str) -> int:
        """Requeue dead letter messages."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.requeue_dead_letters()
        
        return 0
    
    # ----- Queue Operations -----
    
    def peek(self, queue_name: str) -> Optional[Message]:
        """Peek at next message."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.peek()
        
        return None
    
    def purge(self, queue_name: str) -> int:
        """Purge a queue."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.purge()
        
        return 0
    
    def queue_size(self, queue_name: str) -> int:
        """Get queue size."""
        queue = self._queues.get(queue_name)
        
        if queue:
            return queue.size()
        
        return 0
    
    def queue_stats(self, queue_name: str) -> Optional[QueueStats]:
        """Get queue stats."""
        queue = self._queues.get(queue_name)
        
        if queue:
            stats = queue.stats()
            stats.consumer_count = len(self._consumers.get_for_queue(queue_name))
            return stats
        
        return None
    
    # ----- Callbacks -----
    
    def on_message(self, queue_name: str, callback: Callable) -> None:
        """Register message callback."""
        self._callbacks[queue_name].append(callback)
    
    # ----- Statistics -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_messages = 0
        total_pending = 0
        total_processing = 0
        total_dead = 0
        
        for queue in self._queues.values():
            stats = queue.stats()
            total_messages += stats.message_count
            total_pending += stats.pending_count
            total_processing += stats.processing_count
            total_dead += stats.dead_count
        
        return {
            "queue_count": len(self._queues),
            "consumer_count": self._consumers.count(),
            "total_messages": total_messages,
            "pending_messages": total_pending,
            "processing_messages": total_processing,
            "dead_letters": total_dead
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "queues": self.list_queues(),
            "consumers": self._consumers.count(),
            "messages": self._message_store.count()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Queueing Engine."""
    print("=" * 70)
    print("BAEL - QUEUEING ENGINE DEMO")
    print("Message Queueing & Consumers")
    print("=" * 70)
    print()
    
    engine = QueueingEngine()
    
    # 1. Create Queues
    print("1. CREATE QUEUES:")
    print("-" * 40)
    
    engine.create_queue("tasks", QueueType.FIFO)
    engine.create_queue("priority_tasks", QueueType.PRIORITY)
    engine.create_queue("delayed_tasks", QueueType.DELAY)
    
    print(f"   Created queues: {engine.list_queues()}")
    print()
    
    # 2. Publish Messages
    print("2. PUBLISH MESSAGES:")
    print("-" * 40)
    
    for i in range(5):
        mid = engine.publish("tasks", {"task": f"Task {i}", "value": i * 10})
        print(f"   Published: {mid}")
    print()
    
    # 3. Publish with Priority
    print("3. PUBLISH PRIORITY MESSAGES:")
    print("-" * 40)
    
    engine.publish("priority_tasks", {"type": "low"}, MessagePriority.LOW)
    engine.publish("priority_tasks", {"type": "critical"}, MessagePriority.CRITICAL)
    engine.publish("priority_tasks", {"type": "normal"}, MessagePriority.NORMAL)
    engine.publish("priority_tasks", {"type": "high"}, MessagePriority.HIGH)
    
    print(f"   Published 4 priority messages")
    print()
    
    # 4. Consume Messages
    print("4. CONSUME MESSAGES:")
    print("-" * 40)
    
    for i in range(3):
        msg = engine.consume("tasks")
        if msg:
            print(f"   Consumed: {msg.body}")
            engine.ack("tasks", msg.delivery_tag)
    print()
    
    # 5. Consume Priority Messages
    print("5. CONSUME PRIORITY MESSAGES (in order):")
    print("-" * 40)
    
    while True:
        msg = engine.consume("priority_tasks")
        if not msg:
            break
        print(f"   {msg.priority.name}: {msg.body}")
        engine.ack("priority_tasks", msg.delivery_tag)
    print()
    
    # 6. Delayed Messages
    print("6. DELAYED MESSAGES:")
    print("-" * 40)
    
    engine.publish(
        "delayed_tasks",
        {"type": "delayed"},
        delay_seconds=0.5
    )
    
    msg = engine.consume("delayed_tasks")
    print(f"   Immediate consume: {msg}")
    
    await asyncio.sleep(0.6)
    msg = engine.consume("delayed_tasks")
    print(f"   After delay: {msg.body if msg else None}")
    if msg:
        engine.ack("delayed_tasks", msg.delivery_tag)
    print()
    
    # 7. Message Rejection
    print("7. MESSAGE REJECTION:")
    print("-" * 40)
    
    engine.publish("tasks", {"type": "to_reject"})
    msg = engine.consume("tasks")
    
    if msg:
        print(f"   Consumed: {msg.body}")
        engine.nack("tasks", msg.delivery_tag, requeue=False)
        print(f"   Rejected message")
    
    dead = engine.get_dead_letters("tasks")
    print(f"   Dead letters: {len(dead)}")
    print()
    
    # 8. Requeue Dead Letters
    print("8. REQUEUE DEAD LETTERS:")
    print("-" * 40)
    
    count = engine.requeue_dead_letters("tasks")
    print(f"   Requeued: {count} messages")
    print()
    
    # 9. Batch Operations
    print("9. BATCH OPERATIONS:")
    print("-" * 40)
    
    batch_ids = engine.publish_batch(
        "tasks",
        [{"batch": i} for i in range(5)]
    )
    print(f"   Published batch: {len(batch_ids)} messages")
    
    batch_msgs = engine.consume_batch("tasks", max_messages=3)
    print(f"   Consumed batch: {len(batch_msgs)} messages")
    
    for msg in batch_msgs:
        engine.ack("tasks", msg.delivery_tag)
    print()
    
    # 10. Register Consumers
    print("10. REGISTER CONSUMERS:")
    print("-" * 40)
    
    consumer1 = engine.register_consumer("tasks", group_id="workers")
    consumer2 = engine.register_consumer("tasks", group_id="workers")
    
    print(f"   Consumer 1: {consumer1}")
    print(f"   Consumer 2: {consumer2}")
    
    consumers = engine.get_consumers("tasks")
    print(f"   Total consumers: {len(consumers)}")
    print()
    
    # 11. Message with TTL
    print("11. MESSAGE TTL:")
    print("-" * 40)
    
    engine.publish("tasks", {"type": "expiring"}, ttl_seconds=0.1)
    print(f"   Published message with 0.1s TTL")
    
    await asyncio.sleep(0.2)
    msg = engine.consume("tasks")
    print(f"   After TTL: consumed={msg is not None}")
    print()
    
    # 12. Queue Stats
    print("12. QUEUE STATS:")
    print("-" * 40)
    
    for queue_name in engine.list_queues():
        stats = engine.queue_stats(queue_name)
        if stats:
            print(f"   {queue_name}:")
            print(f"     Messages: {stats.message_count}")
            print(f"     Pending: {stats.pending_count}")
            print(f"     Consumers: {stats.consumer_count}")
    print()
    
    # 13. Peek Message
    print("13. PEEK MESSAGE:")
    print("-" * 40)
    
    engine.publish("tasks", {"type": "peek_test"})
    peeked = engine.peek("tasks")
    print(f"   Peeked: {peeked.body if peeked else None}")
    print(f"   Queue size: {engine.queue_size('tasks')}")
    print()
    
    # 14. Purge Queue
    print("14. PURGE QUEUE:")
    print("-" * 40)
    
    purged = engine.purge("tasks")
    print(f"   Purged: {purged} messages")
    print(f"   Queue size after: {engine.queue_size('tasks')}")
    print()
    
    # 15. Engine Statistics
    print("15. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 16. Engine Summary
    print("16. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Queueing Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
