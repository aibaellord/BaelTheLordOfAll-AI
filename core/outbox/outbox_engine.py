"""
BAEL Outbox Pattern Engine Implementation
==========================================

Transactional outbox for guaranteed message delivery.

"Ba'el's outbox ensures every message reaches its destination." — Ba'el
"""

import asyncio
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.Outbox")


# ============================================================================
# ENUMS
# ============================================================================

class OutboxStatus(Enum):
    """Message status in outbox."""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class MessagePriority(Enum):
    """Message priority levels."""
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4
    CRITICAL = 5


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class OutboxMessage:
    """
    Message in the outbox.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Routing
    destination: str = ""
    topic: str = ""
    routing_key: Optional[str] = None

    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    # Status
    status: OutboxStatus = OutboxStatus.PENDING

    # Priority & ordering
    priority: MessagePriority = MessagePriority.NORMAL
    sequence: int = 0

    # Retry info
    attempts: int = 0
    max_attempts: int = 3
    next_retry: Optional[datetime] = None
    last_error: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Correlation
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

    # Transaction
    transaction_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'destination': self.destination,
            'topic': self.topic,
            'routing_key': self.routing_key,
            'payload': self.payload,
            'headers': self.headers,
            'status': self.status.value,
            'priority': self.priority.value,
            'attempts': self.attempts,
            'max_attempts': self.max_attempts,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'correlation_id': self.correlation_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OutboxMessage':
        """Create from dictionary."""
        data = data.copy()

        if 'status' in data:
            data['status'] = OutboxStatus(data['status'])
        if 'priority' in data:
            data['priority'] = MessagePriority(data['priority'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'processed_at' in data and isinstance(data['processed_at'], str):
            data['processed_at'] = datetime.fromisoformat(data['processed_at'])

        return cls(**data)

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def can_retry(self) -> bool:
        """Check if message can be retried."""
        if self.attempts >= self.max_attempts:
            return False
        if self.next_retry and datetime.now() < self.next_retry:
            return False
        return True


@dataclass
class OutboxConfig:
    """Configuration for outbox processor."""
    # Processing
    poll_interval_seconds: float = 1.0
    batch_size: int = 100
    max_concurrent: int = 10

    # Retry
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    retry_backoff_multiplier: float = 2.0

    # Cleanup
    retain_sent_hours: int = 24
    dead_letter_enabled: bool = True

    # Ordering
    preserve_order: bool = True


# ============================================================================
# OUTBOX PROCESSOR
# ============================================================================

class OutboxProcessor:
    """
    Outbox pattern processor.

    Features:
    - Transactional message publishing
    - Guaranteed delivery
    - Automatic retries
    - Dead letter handling
    - Priority ordering
    - Batch processing

    "Ba'el processes the outbox with divine efficiency." — Ba'el
    """

    def __init__(self, config: Optional[OutboxConfig] = None):
        """Initialize processor."""
        self.config = config or OutboxConfig()

        # Message store
        self._messages: Dict[str, OutboxMessage] = {}
        self._sequence = 0

        # Handlers
        self._handlers: Dict[str, Callable[[OutboxMessage], bool]] = {}
        self._default_handler: Optional[Callable[[OutboxMessage], bool]] = None

        # Dead letter
        self._dead_letters: List[OutboxMessage] = []

        # Processing state
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

        # Stats
        self._stats = {
            'sent': 0,
            'failed': 0,
            'retried': 0,
            'dead_lettered': 0
        }

        self._lock = threading.RLock()

        logger.info("Outbox Processor initialized")

    # ========================================================================
    # MESSAGE CREATION
    # ========================================================================

    def add(
        self,
        destination: str,
        payload: Dict[str, Any],
        topic: str = "",
        priority: MessagePriority = MessagePriority.NORMAL,
        headers: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> OutboxMessage:
        """
        Add message to outbox.

        Args:
            destination: Target destination/service
            payload: Message payload
            topic: Optional topic
            priority: Message priority
            headers: Optional headers
            correlation_id: Optional correlation ID
            transaction_id: Optional transaction ID
            ttl_seconds: Time-to-live in seconds

        Returns:
            Created message
        """
        with self._lock:
            self._sequence += 1

            message = OutboxMessage(
                destination=destination,
                topic=topic,
                payload=payload,
                headers=headers or {},
                priority=priority,
                sequence=self._sequence,
                correlation_id=correlation_id,
                transaction_id=transaction_id,
                max_attempts=self.config.max_retries
            )

            if ttl_seconds:
                message.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

            self._messages[message.id] = message

        logger.debug(f"Added message to outbox: {message.id}")

        return message

    def add_batch(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[OutboxMessage]:
        """Add multiple messages."""
        result = []

        for msg_data in messages:
            message = self.add(**msg_data)
            result.append(message)

        return result

    # ========================================================================
    # HANDLER REGISTRATION
    # ========================================================================

    def register_handler(
        self,
        destination: str,
        handler: Callable[[OutboxMessage], bool]
    ) -> None:
        """
        Register handler for destination.

        Handler should return True on success, False on failure.
        """
        with self._lock:
            self._handlers[destination] = handler

        logger.debug(f"Registered handler for: {destination}")

    def set_default_handler(
        self,
        handler: Callable[[OutboxMessage], bool]
    ) -> None:
        """Set default handler for unrouted messages."""
        self._default_handler = handler

    # ========================================================================
    # PROCESSING
    # ========================================================================

    async def start(self) -> None:
        """Start background processing."""
        if self._running:
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_loop())

        logger.info("Outbox processor started")

    async def stop(self) -> None:
        """Stop background processing."""
        self._running = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Outbox processor stopped")

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                await self.process_batch()
                await asyncio.sleep(self.config.poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                await asyncio.sleep(1.0)

    async def process_batch(self) -> int:
        """Process a batch of pending messages."""
        # Get pending messages
        messages = self._get_pending_messages()

        if not messages:
            return 0

        processed = 0

        # Process based on concurrency setting
        if self.config.max_concurrent > 1 and not self.config.preserve_order:
            # Parallel processing
            semaphore = asyncio.Semaphore(self.config.max_concurrent)

            async def process_with_semaphore(msg):
                async with semaphore:
                    return await self._process_message(msg)

            tasks = [process_with_semaphore(m) for m in messages]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processed = sum(1 for r in results if r is True)
        else:
            # Sequential processing
            for message in messages:
                success = await self._process_message(message)
                if success:
                    processed += 1

        # Cleanup expired messages
        self._cleanup_expired()

        return processed

    async def _process_message(self, message: OutboxMessage) -> bool:
        """Process a single message."""
        # Check if expired
        if message.is_expired():
            message.status = OutboxStatus.DEAD_LETTER
            self._move_to_dead_letter(message)
            return False

        # Mark as processing
        message.status = OutboxStatus.PROCESSING
        message.attempts += 1

        try:
            # Get handler
            handler = self._handlers.get(message.destination) or self._default_handler

            if not handler:
                logger.warning(f"No handler for destination: {message.destination}")
                message.status = OutboxStatus.PENDING
                return False

            # Execute handler
            loop = asyncio.get_event_loop()

            if asyncio.iscoroutinefunction(handler):
                success = await handler(message)
            else:
                success = await loop.run_in_executor(
                    None,
                    lambda: handler(message)
                )

            if success:
                message.status = OutboxStatus.SENT
                message.processed_at = datetime.now()
                self._stats['sent'] += 1

                logger.debug(f"Message sent: {message.id}")
                return True
            else:
                raise Exception("Handler returned False")

        except Exception as e:
            message.last_error = str(e)

            if message.can_retry():
                # Schedule retry
                delay = self.config.retry_delay_seconds * (
                    self.config.retry_backoff_multiplier ** (message.attempts - 1)
                )
                message.next_retry = datetime.now() + timedelta(seconds=delay)
                message.status = OutboxStatus.PENDING
                self._stats['retried'] += 1

                logger.debug(
                    f"Message {message.id} scheduled for retry "
                    f"(attempt {message.attempts})"
                )
            else:
                # Move to dead letter
                message.status = OutboxStatus.DEAD_LETTER
                self._move_to_dead_letter(message)
                self._stats['failed'] += 1

            return False

    def _get_pending_messages(self) -> List[OutboxMessage]:
        """Get pending messages for processing."""
        with self._lock:
            messages = [
                m for m in self._messages.values()
                if m.status == OutboxStatus.PENDING and m.can_retry()
            ]

        # Sort by priority (descending) and sequence (ascending)
        messages.sort(
            key=lambda m: (-m.priority.value, m.sequence)
        )

        return messages[:self.config.batch_size]

    def _move_to_dead_letter(self, message: OutboxMessage) -> None:
        """Move message to dead letter queue."""
        if self.config.dead_letter_enabled:
            self._dead_letters.append(message)
            self._stats['dead_lettered'] += 1

            logger.warning(
                f"Message moved to dead letter: {message.id} - {message.last_error}"
            )

    def _cleanup_expired(self) -> None:
        """Clean up old sent messages."""
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=self.config.retain_sent_hours)

            to_remove = [
                msg_id for msg_id, msg in self._messages.items()
                if msg.status == OutboxStatus.SENT and msg.processed_at < cutoff
            ]

            for msg_id in to_remove:
                del self._messages[msg_id]

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_message(self, message_id: str) -> Optional[OutboxMessage]:
        """Get message by ID."""
        return self._messages.get(message_id)

    def get_pending(self) -> List[OutboxMessage]:
        """Get all pending messages."""
        with self._lock:
            return [
                m for m in self._messages.values()
                if m.status == OutboxStatus.PENDING
            ]

    def get_dead_letters(self) -> List[OutboxMessage]:
        """Get dead letter messages."""
        return self._dead_letters.copy()

    def retry_dead_letter(self, message_id: str) -> bool:
        """Retry a dead letter message."""
        for i, msg in enumerate(self._dead_letters):
            if msg.id == message_id:
                msg.status = OutboxStatus.PENDING
                msg.attempts = 0
                msg.next_retry = None

                with self._lock:
                    self._messages[msg.id] = msg

                del self._dead_letters[i]
                return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        with self._lock:
            pending = sum(
                1 for m in self._messages.values()
                if m.status == OutboxStatus.PENDING
            )
            processing = sum(
                1 for m in self._messages.values()
                if m.status == OutboxStatus.PROCESSING
            )

        return {
            'total_messages': len(self._messages),
            'pending': pending,
            'processing': processing,
            'sent': self._stats['sent'],
            'failed': self._stats['failed'],
            'retried': self._stats['retried'],
            'dead_letters': len(self._dead_letters),
            'running': self._running
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

outbox = OutboxProcessor()
