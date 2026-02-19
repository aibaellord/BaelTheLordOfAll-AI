"""
BAEL Dead Letter Queue Engine Implementation
=============================================

Dead letter queue for handling unprocessable messages.

"Ba'el resurrects failed messages from the void." — Ba'el
"""

import asyncio
import json
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.DLQ")


# ============================================================================
# ENUMS
# ============================================================================

class DLQReason(Enum):
    """Reasons for dead-lettering."""
    MAX_RETRIES = "max_retries"
    EXPIRED = "expired"
    POISON = "poison"           # Causes consumer crash
    MALFORMED = "malformed"     # Invalid format
    REJECTED = "rejected"       # Business logic rejection
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class RetryPolicy(Enum):
    """Retry policies for dead letters."""
    NONE = "none"               # No retry
    IMMEDIATE = "immediate"     # Retry immediately
    DELAYED = "delayed"         # Retry after delay
    EXPONENTIAL = "exponential"  # Exponential backoff
    MANUAL = "manual"           # Manual retry only


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DeadLetter:
    """
    Dead letter message.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Original message
    original_queue: str = ""
    original_message_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    # DLQ info
    reason: DLQReason = DLQReason.UNKNOWN
    error_message: Optional[str] = None
    error_stack: Optional[str] = None

    # Retry info
    attempt_count: int = 0
    max_attempts: int = 3
    retry_policy: RetryPolicy = RetryPolicy.DELAYED
    next_retry: Optional[datetime] = None
    retry_count: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_retry_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Metadata
    correlation_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'original_queue': self.original_queue,
            'original_message_id': self.original_message_id,
            'payload': self.payload,
            'headers': self.headers,
            'reason': self.reason.value,
            'error_message': self.error_message,
            'attempt_count': self.attempt_count,
            'retry_count': self.retry_count,
            'retry_policy': self.retry_policy.value,
            'created_at': self.created_at.isoformat(),
            'last_retry_at': self.last_retry_at.isoformat() if self.last_retry_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeadLetter':
        """Create from dictionary."""
        data = data.copy()

        if 'reason' in data:
            data['reason'] = DLQReason(data['reason'])
        if 'retry_policy' in data:
            data['retry_policy'] = RetryPolicy(data['retry_policy'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])

        return cls(**data)

    def can_retry(self) -> bool:
        """Check if message can be retried."""
        if self.retry_policy == RetryPolicy.NONE:
            return False
        if self.retry_policy == RetryPolicy.MANUAL:
            return True
        if self.retry_count >= self.max_attempts:
            return False
        if self.next_retry and datetime.now() < self.next_retry:
            return False
        return True

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at


@dataclass
class DLQStats:
    """Dead letter queue statistics."""
    total_messages: int = 0
    pending_retry: int = 0
    retried: int = 0
    expired: int = 0

    by_reason: Dict[str, int] = field(default_factory=dict)
    by_queue: Dict[str, int] = field(default_factory=dict)

    oldest_message: Optional[datetime] = None
    newest_message: Optional[datetime] = None


# ============================================================================
# DEAD LETTER QUEUE
# ============================================================================

class DeadLetterQueue:
    """
    Dead letter queue manager.

    Features:
    - Multiple DLQ storage
    - Retry policies
    - Automatic processing
    - Expiration handling
    - Statistics

    "Ba'el manages the queue of unredeemed messages." — Ba'el
    """

    def __init__(
        self,
        default_retry_policy: RetryPolicy = RetryPolicy.DELAYED,
        default_retry_delay_seconds: float = 60.0,
        default_max_retries: int = 3
    ):
        """Initialize DLQ."""
        self.default_retry_policy = default_retry_policy
        self.default_retry_delay = default_retry_delay_seconds
        self.default_max_retries = default_max_retries

        # Dead letters: id -> DeadLetter
        self._letters: Dict[str, DeadLetter] = {}

        # Retry handlers: queue -> handler
        self._retry_handlers: Dict[str, Callable[[DeadLetter], bool]] = {}

        # Processing state
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

        # Stats
        self._stats = DLQStats()

        self._lock = threading.RLock()

        logger.info("Dead Letter Queue initialized")

    # ========================================================================
    # MESSAGE HANDLING
    # ========================================================================

    def add(
        self,
        payload: Dict[str, Any],
        original_queue: str,
        reason: DLQReason,
        error_message: Optional[str] = None,
        original_message_id: Optional[str] = None,
        attempt_count: int = 1,
        headers: Optional[Dict[str, str]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        ttl_hours: Optional[int] = None
    ) -> DeadLetter:
        """
        Add a message to the dead letter queue.

        Args:
            payload: Original message payload
            original_queue: Source queue name
            reason: Reason for dead-lettering
            error_message: Error description
            original_message_id: Original message ID
            attempt_count: Number of processing attempts
            headers: Message headers
            retry_policy: Retry policy override
            ttl_hours: Time-to-live in hours

        Returns:
            Created dead letter
        """
        policy = retry_policy or self.default_retry_policy

        letter = DeadLetter(
            payload=payload,
            original_queue=original_queue,
            original_message_id=original_message_id,
            reason=reason,
            error_message=error_message,
            attempt_count=attempt_count,
            headers=headers or {},
            retry_policy=policy,
            max_attempts=self.default_max_retries
        )

        # Calculate next retry
        if policy in [RetryPolicy.DELAYED, RetryPolicy.EXPONENTIAL]:
            letter.next_retry = datetime.now() + timedelta(
                seconds=self.default_retry_delay
            )

        # Set expiration
        if ttl_hours:
            letter.expires_at = datetime.now() + timedelta(hours=ttl_hours)

        with self._lock:
            self._letters[letter.id] = letter

            # Update stats
            self._stats.total_messages += 1
            self._stats.by_reason[reason.value] = \
                self._stats.by_reason.get(reason.value, 0) + 1
            self._stats.by_queue[original_queue] = \
                self._stats.by_queue.get(original_queue, 0) + 1

            if not self._stats.oldest_message:
                self._stats.oldest_message = letter.created_at
            self._stats.newest_message = letter.created_at

        logger.info(
            f"Added dead letter: {letter.id} from {original_queue} "
            f"(reason: {reason.value})"
        )

        return letter

    def get(self, letter_id: str) -> Optional[DeadLetter]:
        """Get dead letter by ID."""
        return self._letters.get(letter_id)

    def remove(self, letter_id: str) -> bool:
        """Remove dead letter."""
        with self._lock:
            if letter_id in self._letters:
                del self._letters[letter_id]
                return True
        return False

    def list(
        self,
        queue: Optional[str] = None,
        reason: Optional[DLQReason] = None,
        can_retry: Optional[bool] = None,
        limit: int = 100
    ) -> List[DeadLetter]:
        """List dead letters with optional filters."""
        letters = list(self._letters.values())

        if queue:
            letters = [l for l in letters if l.original_queue == queue]

        if reason:
            letters = [l for l in letters if l.reason == reason]

        if can_retry is not None:
            letters = [l for l in letters if l.can_retry() == can_retry]

        # Sort by creation time (oldest first)
        letters.sort(key=lambda l: l.created_at)

        return letters[:limit]

    # ========================================================================
    # RETRY HANDLING
    # ========================================================================

    def register_retry_handler(
        self,
        queue: str,
        handler: Callable[[DeadLetter], bool]
    ) -> None:
        """
        Register retry handler for a queue.

        Handler should return True on success, False on failure.
        """
        with self._lock:
            self._retry_handlers[queue] = handler

        logger.debug(f"Registered retry handler for: {queue}")

    async def retry(self, letter_id: str) -> bool:
        """
        Retry a dead letter.

        Args:
            letter_id: Dead letter ID

        Returns:
            True if retry succeeded
        """
        letter = self._letters.get(letter_id)
        if not letter:
            return False

        if not letter.can_retry():
            logger.warning(f"Dead letter {letter_id} cannot be retried")
            return False

        handler = self._retry_handlers.get(letter.original_queue)
        if not handler:
            logger.warning(f"No retry handler for queue: {letter.original_queue}")
            return False

        letter.retry_count += 1
        letter.last_retry_at = datetime.now()

        try:
            loop = asyncio.get_event_loop()

            if asyncio.iscoroutinefunction(handler):
                success = await handler(letter)
            else:
                success = await loop.run_in_executor(
                    None,
                    lambda: handler(letter)
                )

            if success:
                # Remove from DLQ
                self.remove(letter_id)
                self._stats.retried += 1

                logger.info(f"Dead letter {letter_id} retried successfully")
                return True
            else:
                # Update next retry
                self._schedule_next_retry(letter)
                return False

        except Exception as e:
            letter.error_message = str(e)
            self._schedule_next_retry(letter)

            logger.error(f"Retry failed for {letter_id}: {e}")
            return False

    def _schedule_next_retry(self, letter: DeadLetter) -> None:
        """Schedule next retry based on policy."""
        if letter.retry_policy == RetryPolicy.IMMEDIATE:
            letter.next_retry = datetime.now()

        elif letter.retry_policy == RetryPolicy.DELAYED:
            letter.next_retry = datetime.now() + timedelta(
                seconds=self.default_retry_delay
            )

        elif letter.retry_policy == RetryPolicy.EXPONENTIAL:
            delay = self.default_retry_delay * (2 ** letter.retry_count)
            letter.next_retry = datetime.now() + timedelta(seconds=delay)

    async def retry_all(
        self,
        queue: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, bool]:
        """Retry all eligible dead letters."""
        letters = self.list(queue=queue, can_retry=True, limit=limit)
        results = {}

        for letter in letters:
            results[letter.id] = await self.retry(letter.id)

        return results

    # ========================================================================
    # BACKGROUND PROCESSING
    # ========================================================================

    async def start_processor(
        self,
        interval_seconds: float = 60.0
    ) -> None:
        """Start background retry processor."""
        if self._running:
            return

        self._running = True
        self._processor_task = asyncio.create_task(
            self._process_loop(interval_seconds)
        )

        logger.info("DLQ processor started")

    async def stop_processor(self) -> None:
        """Stop background processor."""
        self._running = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("DLQ processor stopped")

    async def _process_loop(self, interval: float) -> None:
        """Background processing loop."""
        while self._running:
            try:
                # Process retries
                letters = self.list(can_retry=True, limit=50)

                for letter in letters:
                    if letter.can_retry():
                        await self.retry(letter.id)

                # Cleanup expired
                self._cleanup_expired()

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"DLQ processing error: {e}")
                await asyncio.sleep(5.0)

    def _cleanup_expired(self) -> None:
        """Remove expired dead letters."""
        with self._lock:
            expired = [
                lid for lid, letter in self._letters.items()
                if letter.is_expired()
            ]

            for lid in expired:
                del self._letters[lid]
                self._stats.expired += 1

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_stats(self) -> DLQStats:
        """Get queue statistics."""
        with self._lock:
            stats = DLQStats(
                total_messages=len(self._letters),
                pending_retry=sum(1 for l in self._letters.values() if l.can_retry()),
                retried=self._stats.retried,
                expired=self._stats.expired,
                by_reason=self._stats.by_reason.copy(),
                by_queue=self._stats.by_queue.copy(),
                oldest_message=self._stats.oldest_message,
                newest_message=self._stats.newest_message
            )
        return stats

    def get_status(self) -> Dict[str, Any]:
        """Get queue status."""
        stats = self.get_stats()
        return {
            'total': stats.total_messages,
            'pending_retry': stats.pending_retry,
            'retried': stats.retried,
            'expired': stats.expired,
            'by_reason': stats.by_reason,
            'by_queue': stats.by_queue,
            'handlers': list(self._retry_handlers.keys()),
            'running': self._running
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

dlq = DeadLetterQueue()
