#!/usr/bin/env python3
"""
BAEL - Notification System
Comprehensive multi-channel notification infrastructure.

Features:
- Multiple channels (Email, SMS, Push, Webhook, etc.)
- Template-based messages
- Priority levels
- Delivery tracking
- Retry mechanisms
- Rate limiting
- Scheduling
- Batching
- Preferences management
- Event-driven notifications
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from typing import (Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class NotificationChannel(Enum):
    """Notification channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    CLICKED = "clicked"
    OPENED = "opened"


class TemplateType(Enum):
    """Template types."""
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Recipient:
    """Notification recipient."""
    recipient_id: str
    name: str = ""
    email: str = ""
    phone: str = ""
    device_tokens: List[str] = field(default_factory=list)
    preferences: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationTemplate:
    """Notification template."""
    template_id: str
    name: str
    channel: NotificationChannel
    template_type: TemplateType = TemplateType.TEXT
    subject: str = ""
    body: str = ""
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self, context: Dict[str, Any]) -> str:
        """Render template with context."""
        result = self.body

        for var in self.variables:
            placeholder = f"{{{{{var}}}}}"
            value = str(context.get(var, ""))
            result = result.replace(placeholder, value)

        return result

    def render_subject(self, context: Dict[str, Any]) -> str:
        """Render subject with context."""
        result = self.subject

        for var in self.variables:
            placeholder = f"{{{{{var}}}}}"
            value = str(context.get(var, ""))
            result = result.replace(placeholder, value)

        return result


@dataclass
class Notification:
    """Notification message."""
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: NotificationChannel = NotificationChannel.EMAIL
    recipient: Optional[Recipient] = None
    recipient_id: str = ""
    subject: str = ""
    body: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    status: NotificationStatus = NotificationStatus.PENDING
    template_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    scheduled_at: Optional[float] = None
    sent_at: Optional[float] = None
    delivered_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: str = ""


@dataclass
class DeliveryResult:
    """Delivery result."""
    success: bool
    notification_id: str = ""
    channel: NotificationChannel = NotificationChannel.EMAIL
    status: NotificationStatus = NotificationStatus.PENDING
    message: str = ""
    external_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class NotificationStats:
    """Notification statistics."""
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_pending: int = 0
    by_channel: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_priority: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_status: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avg_delivery_time: float = 0.0


# =============================================================================
# CHANNEL HANDLERS
# =============================================================================

class ChannelHandler(ABC):
    """Abstract channel handler."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Get channel type."""
        pass

    @abstractmethod
    async def send(self, notification: Notification) -> DeliveryResult:
        """Send notification."""
        pass

    async def validate(self, notification: Notification) -> bool:
        """Validate notification for this channel."""
        return True


class EmailHandler(ChannelHandler):
    """Email channel handler."""

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        from_email: str = "noreply@bael.ai"
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send email notification (simulated)."""
        recipient = notification.recipient

        if not recipient or not recipient.email:
            return DeliveryResult(
                success=False,
                notification_id=notification.notification_id,
                channel=self.channel,
                status=NotificationStatus.FAILED,
                message="No email address"
            )

        # Simulate sending
        await asyncio.sleep(0.1)

        logger.info(f"Email sent to {recipient.email}: {notification.subject}")

        return DeliveryResult(
            success=True,
            notification_id=notification.notification_id,
            channel=self.channel,
            status=NotificationStatus.DELIVERED,
            message="Email delivered",
            external_id=f"email_{uuid.uuid4().hex[:8]}"
        )

    async def validate(self, notification: Notification) -> bool:
        if not notification.recipient:
            return False

        email = notification.recipient.email
        if not email:
            return False

        # Basic email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


class SMSHandler(ChannelHandler):
    """SMS channel handler."""

    def __init__(
        self,
        api_key: str = "",
        sender_id: str = "BAEL"
    ):
        self.api_key = api_key
        self.sender_id = sender_id

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SMS

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send SMS notification (simulated)."""
        recipient = notification.recipient

        if not recipient or not recipient.phone:
            return DeliveryResult(
                success=False,
                notification_id=notification.notification_id,
                channel=self.channel,
                status=NotificationStatus.FAILED,
                message="No phone number"
            )

        await asyncio.sleep(0.05)

        logger.info(f"SMS sent to {recipient.phone}: {notification.body[:50]}...")

        return DeliveryResult(
            success=True,
            notification_id=notification.notification_id,
            channel=self.channel,
            status=NotificationStatus.DELIVERED,
            message="SMS delivered",
            external_id=f"sms_{uuid.uuid4().hex[:8]}"
        )


class PushHandler(ChannelHandler):
    """Push notification handler."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.PUSH

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send push notification (simulated)."""
        recipient = notification.recipient

        if not recipient or not recipient.device_tokens:
            return DeliveryResult(
                success=False,
                notification_id=notification.notification_id,
                channel=self.channel,
                status=NotificationStatus.FAILED,
                message="No device tokens"
            )

        await asyncio.sleep(0.02)

        logger.info(f"Push sent to {len(recipient.device_tokens)} devices")

        return DeliveryResult(
            success=True,
            notification_id=notification.notification_id,
            channel=self.channel,
            status=NotificationStatus.DELIVERED,
            message=f"Push delivered to {len(recipient.device_tokens)} devices"
        )


class WebhookHandler(ChannelHandler):
    """Webhook channel handler."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WEBHOOK

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send webhook notification (simulated)."""
        url = notification.metadata.get("webhook_url")

        if not url:
            return DeliveryResult(
                success=False,
                notification_id=notification.notification_id,
                channel=self.channel,
                status=NotificationStatus.FAILED,
                message="No webhook URL"
            )

        await asyncio.sleep(0.05)

        logger.info(f"Webhook sent to {url}")

        return DeliveryResult(
            success=True,
            notification_id=notification.notification_id,
            channel=self.channel,
            status=NotificationStatus.DELIVERED,
            message="Webhook delivered"
        )


class InAppHandler(ChannelHandler):
    """In-app notification handler."""

    def __init__(self):
        self.notifications: Dict[str, List[Notification]] = defaultdict(list)

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.IN_APP

    async def send(self, notification: Notification) -> DeliveryResult:
        """Store in-app notification."""
        recipient_id = notification.recipient_id

        if notification.recipient:
            recipient_id = notification.recipient.recipient_id

        self.notifications[recipient_id].append(notification)

        return DeliveryResult(
            success=True,
            notification_id=notification.notification_id,
            channel=self.channel,
            status=NotificationStatus.DELIVERED,
            message="In-app notification stored"
        )

    def get_user_notifications(self, user_id: str) -> List[Notification]:
        """Get notifications for a user."""
        return self.notifications.get(user_id, [])


class SlackHandler(ChannelHandler):
    """Slack channel handler."""

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SLACK

    async def send(self, notification: Notification) -> DeliveryResult:
        """Send Slack notification (simulated)."""
        channel_id = notification.metadata.get("slack_channel", "#general")

        await asyncio.sleep(0.03)

        logger.info(f"Slack message sent to {channel_id}")

        return DeliveryResult(
            success=True,
            notification_id=notification.notification_id,
            channel=self.channel,
            status=NotificationStatus.DELIVERED,
            message=f"Slack message delivered to {channel_id}"
        )


# =============================================================================
# NOTIFICATION QUEUE
# =============================================================================

class NotificationQueue:
    """Priority-based notification queue."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.queues: Dict[NotificationPriority, deque] = {
            p: deque() for p in NotificationPriority
        }
        self._lock = asyncio.Lock()

    async def enqueue(self, notification: Notification) -> bool:
        """Add notification to queue."""
        async with self._lock:
            total = sum(len(q) for q in self.queues.values())

            if total >= self.max_size:
                return False

            self.queues[notification.priority].append(notification)
            notification.status = NotificationStatus.QUEUED
            return True

    async def dequeue(self) -> Optional[Notification]:
        """Get next notification (highest priority first)."""
        async with self._lock:
            # Process highest priority first
            for priority in sorted(NotificationPriority, key=lambda p: p.value, reverse=True):
                queue = self.queues[priority]
                if queue:
                    return queue.popleft()
            return None

    async def size(self) -> int:
        """Get total queue size."""
        async with self._lock:
            return sum(len(q) for q in self.queues.values())

    async def clear(self) -> int:
        """Clear all queues."""
        async with self._lock:
            count = sum(len(q) for q in self.queues.values())
            for q in self.queues.values():
                q.clear()
            return count


# =============================================================================
# RATE LIMITER
# =============================================================================

class NotificationRateLimiter:
    """Rate limiter for notifications."""

    def __init__(
        self,
        max_per_second: int = 100,
        max_per_minute: int = 1000,
        max_per_hour: int = 10000
    ):
        self.max_per_second = max_per_second
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour

        self.second_window: deque = deque()
        self.minute_window: deque = deque()
        self.hour_window: deque = deque()

        self._lock = asyncio.Lock()

    def _cleanup_window(
        self,
        window: deque,
        max_age: float
    ) -> None:
        """Remove old entries from window."""
        cutoff = time.time() - max_age
        while window and window[0] < cutoff:
            window.popleft()

    async def acquire(self) -> bool:
        """Try to acquire a rate limit slot."""
        async with self._lock:
            now = time.time()

            # Cleanup windows
            self._cleanup_window(self.second_window, 1.0)
            self._cleanup_window(self.minute_window, 60.0)
            self._cleanup_window(self.hour_window, 3600.0)

            # Check limits
            if len(self.second_window) >= self.max_per_second:
                return False

            if len(self.minute_window) >= self.max_per_minute:
                return False

            if len(self.hour_window) >= self.max_per_hour:
                return False

            # Record
            self.second_window.append(now)
            self.minute_window.append(now)
            self.hour_window.append(now)

            return True

    async def wait_for_slot(self, timeout: float = 10.0) -> bool:
        """Wait for a rate limit slot."""
        start = time.time()

        while time.time() - start < timeout:
            if await self.acquire():
                return True
            await asyncio.sleep(0.01)

        return False


# =============================================================================
# NOTIFICATION MANAGER
# =============================================================================

class NotificationManager:
    """
    Comprehensive notification manager for BAEL.
    """

    def __init__(
        self,
        workers: int = 4,
        queue_size: int = 10000
    ):
        self.workers = workers
        self.queue = NotificationQueue(queue_size)
        self.rate_limiter = NotificationRateLimiter()

        # Channel handlers
        self.handlers: Dict[NotificationChannel, ChannelHandler] = {}

        # Templates
        self.templates: Dict[str, NotificationTemplate] = {}

        # Recipients
        self.recipients: Dict[str, Recipient] = {}

        # History
        self.history: List[DeliveryResult] = []
        self.max_history = 10000

        # Statistics
        self._stats = NotificationStats()

        # Worker control
        self._running = False
        self._worker_tasks: List[asyncio.Task] = []

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default channel handlers."""
        self.register_handler(EmailHandler())
        self.register_handler(SMSHandler())
        self.register_handler(PushHandler())
        self.register_handler(WebhookHandler())
        self.register_handler(InAppHandler())
        self.register_handler(SlackHandler())

    def register_handler(self, handler: ChannelHandler) -> None:
        """Register a channel handler."""
        self.handlers[handler.channel] = handler

    def register_template(self, template: NotificationTemplate) -> None:
        """Register a notification template."""
        self.templates[template.template_id] = template

    def register_recipient(self, recipient: Recipient) -> None:
        """Register a recipient."""
        self.recipients[recipient.recipient_id] = recipient

    def get_recipient(self, recipient_id: str) -> Optional[Recipient]:
        """Get recipient by ID."""
        return self.recipients.get(recipient_id)

    async def create_notification(
        self,
        channel: NotificationChannel,
        recipient_id: str,
        subject: str = "",
        body: str = "",
        template_id: str = "",
        context: Dict[str, Any] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: float = None,
        metadata: Dict[str, Any] = None
    ) -> Notification:
        """Create a notification."""
        recipient = self.recipients.get(recipient_id)

        # Apply template
        if template_id:
            template = self.templates.get(template_id)
            if template:
                ctx = context or {}
                body = template.render(ctx)
                subject = template.render_subject(ctx)

        notification = Notification(
            channel=channel,
            recipient=recipient,
            recipient_id=recipient_id,
            subject=subject,
            body=body,
            priority=priority,
            template_id=template_id,
            context=context or {},
            scheduled_at=scheduled_at,
            metadata=metadata or {}
        )

        self._stats.total_pending += 1
        self._stats.by_channel[channel.value] += 1
        self._stats.by_priority[priority.name] += 1

        return notification

    async def send(
        self,
        notification: Notification,
        immediate: bool = False
    ) -> DeliveryResult:
        """Send a notification."""
        handler = self.handlers.get(notification.channel)

        if not handler:
            return DeliveryResult(
                success=False,
                notification_id=notification.notification_id,
                status=NotificationStatus.FAILED,
                message=f"No handler for channel {notification.channel.value}"
            )

        if immediate:
            return await self._send_now(notification, handler)

        # Queue for async sending
        if await self.queue.enqueue(notification):
            return DeliveryResult(
                success=True,
                notification_id=notification.notification_id,
                status=NotificationStatus.QUEUED,
                message="Notification queued"
            )

        return DeliveryResult(
            success=False,
            notification_id=notification.notification_id,
            status=NotificationStatus.FAILED,
            message="Queue is full"
        )

    async def _send_now(
        self,
        notification: Notification,
        handler: ChannelHandler
    ) -> DeliveryResult:
        """Send notification immediately."""
        # Rate limit
        if not await self.rate_limiter.acquire():
            return DeliveryResult(
                success=False,
                notification_id=notification.notification_id,
                status=NotificationStatus.FAILED,
                message="Rate limit exceeded"
            )

        notification.status = NotificationStatus.SENDING
        notification.sent_at = time.time()

        try:
            result = await handler.send(notification)

            if result.success:
                notification.status = NotificationStatus.DELIVERED
                notification.delivered_at = time.time()
                self._stats.total_delivered += 1
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = result.message
                self._stats.total_failed += 1

            self._stats.total_sent += 1
            self._stats.by_status[result.status.value] += 1

            # Update average delivery time
            if result.success and notification.sent_at:
                delivery_time = time.time() - notification.sent_at
                n = self._stats.total_delivered
                self._stats.avg_delivery_time = (
                    (self._stats.avg_delivery_time * (n - 1) + delivery_time) / n
                )

            # Store in history
            self.history.append(result)
            if len(self.history) > self.max_history:
                self.history.pop(0)

            return result

        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            self._stats.total_failed += 1

            return DeliveryResult(
                success=False,
                notification_id=notification.notification_id,
                status=NotificationStatus.FAILED,
                message=str(e)
            )

    async def _worker(self, worker_id: int) -> None:
        """Worker task for processing queue."""
        while self._running:
            notification = await self.queue.dequeue()

            if notification is None:
                await asyncio.sleep(0.01)
                continue

            handler = self.handlers.get(notification.channel)
            if handler:
                await self._send_now(notification, handler)

    async def start(self) -> None:
        """Start notification workers."""
        self._running = True

        for i in range(self.workers):
            task = asyncio.create_task(self._worker(i))
            self._worker_tasks.append(task)

        logger.info(f"Started {self.workers} notification workers")

    async def stop(self) -> None:
        """Stop notification workers."""
        self._running = False

        for task in self._worker_tasks:
            task.cancel()

        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

    async def send_to_multiple(
        self,
        channel: NotificationChannel,
        recipient_ids: List[str],
        subject: str = "",
        body: str = "",
        template_id: str = "",
        context: Dict[str, Any] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> List[DeliveryResult]:
        """Send to multiple recipients."""
        results = []

        for recipient_id in recipient_ids:
            notification = await self.create_notification(
                channel=channel,
                recipient_id=recipient_id,
                subject=subject,
                body=body,
                template_id=template_id,
                context=context,
                priority=priority
            )

            result = await self.send(notification)
            results.append(result)

        return results

    def get_stats(self) -> NotificationStats:
        """Get notification statistics."""
        return self._stats

    def get_history(
        self,
        channel: NotificationChannel = None,
        status: NotificationStatus = None,
        limit: int = 100
    ) -> List[DeliveryResult]:
        """Get notification history."""
        results = self.history

        if channel:
            results = [r for r in results if r.channel == channel]

        if status:
            results = [r for r in results if r.status == status]

        return results[-limit:]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Notification System."""
    print("=" * 70)
    print("BAEL - NOTIFICATION SYSTEM DEMO")
    print("Multi-Channel Notification Infrastructure")
    print("=" * 70)
    print()

    manager = NotificationManager()

    # 1. Register Recipients
    print("1. REGISTER RECIPIENTS:")
    print("-" * 40)

    users = [
        Recipient(
            recipient_id="user1",
            name="Alice Smith",
            email="alice@example.com",
            phone="+1234567890",
            device_tokens=["token_abc123"]
        ),
        Recipient(
            recipient_id="user2",
            name="Bob Jones",
            email="bob@example.com",
            phone="+0987654321"
        ),
        Recipient(
            recipient_id="user3",
            name="Charlie Brown",
            email="charlie@example.com"
        )
    ]

    for user in users:
        manager.register_recipient(user)
        print(f"   Registered: {user.name} ({user.email})")
    print()

    # 2. Register Templates
    print("2. REGISTER TEMPLATES:")
    print("-" * 40)

    templates = [
        NotificationTemplate(
            template_id="welcome",
            name="Welcome Email",
            channel=NotificationChannel.EMAIL,
            subject="Welcome to BAEL, {{name}}!",
            body="Hello {{name}},\n\nWelcome to BAEL, the Lord of All AI Agents!\n\nBest regards,\nThe BAEL Team",
            variables=["name"]
        ),
        NotificationTemplate(
            template_id="alert",
            name="Alert Notification",
            channel=NotificationChannel.PUSH,
            subject="Alert: {{title}}",
            body="{{message}}",
            variables=["title", "message"]
        ),
        NotificationTemplate(
            template_id="sms_code",
            name="SMS Verification",
            channel=NotificationChannel.SMS,
            body="Your BAEL verification code is: {{code}}",
            variables=["code"]
        )
    ]

    for template in templates:
        manager.register_template(template)
        print(f"   Registered: {template.name} ({template.channel.value})")
    print()

    # 3. Send Email
    print("3. SEND EMAIL:")
    print("-" * 40)

    notification = await manager.create_notification(
        channel=NotificationChannel.EMAIL,
        recipient_id="user1",
        template_id="welcome",
        context={"name": "Alice"}
    )

    result = await manager.send(notification, immediate=True)
    print(f"   Status: {result.status.value}")
    print(f"   Message: {result.message}")
    print()

    # 4. Send SMS
    print("4. SEND SMS:")
    print("-" * 40)

    notification = await manager.create_notification(
        channel=NotificationChannel.SMS,
        recipient_id="user1",
        template_id="sms_code",
        context={"code": "123456"}
    )

    result = await manager.send(notification, immediate=True)
    print(f"   Status: {result.status.value}")
    print(f"   Message: {result.message}")
    print()

    # 5. Send Push
    print("5. SEND PUSH NOTIFICATION:")
    print("-" * 40)

    notification = await manager.create_notification(
        channel=NotificationChannel.PUSH,
        recipient_id="user1",
        template_id="alert",
        context={"title": "New Message", "message": "You have a new message!"},
        priority=NotificationPriority.HIGH
    )

    result = await manager.send(notification, immediate=True)
    print(f"   Status: {result.status.value}")
    print(f"   Message: {result.message}")
    print()

    # 6. Send to Multiple
    print("6. SEND TO MULTIPLE RECIPIENTS:")
    print("-" * 40)

    results = await manager.send_to_multiple(
        channel=NotificationChannel.EMAIL,
        recipient_ids=["user1", "user2", "user3"],
        subject="Important Announcement",
        body="This is an important announcement to all users."
    )

    for r in results:
        print(f"   {r.notification_id[:8]}: {r.status.value}")
    print()

    # 7. In-App Notifications
    print("7. IN-APP NOTIFICATIONS:")
    print("-" * 40)

    in_app_handler = manager.handlers[NotificationChannel.IN_APP]

    notification = await manager.create_notification(
        channel=NotificationChannel.IN_APP,
        recipient_id="user1",
        subject="New Feature",
        body="Check out our new features!"
    )

    result = await manager.send(notification, immediate=True)
    print(f"   Status: {result.status.value}")

    # Get user notifications
    if isinstance(in_app_handler, InAppHandler):
        user_notifs = in_app_handler.get_user_notifications("user1")
        print(f"   User has {len(user_notifs)} in-app notification(s)")
    print()

    # 8. Priority Notifications
    print("8. PRIORITY NOTIFICATIONS:")
    print("-" * 40)

    priorities = [
        NotificationPriority.LOW,
        NotificationPriority.NORMAL,
        NotificationPriority.HIGH,
        NotificationPriority.URGENT,
        NotificationPriority.CRITICAL
    ]

    for priority in priorities:
        notification = await manager.create_notification(
            channel=NotificationChannel.EMAIL,
            recipient_id="user1",
            subject=f"{priority.name} Priority Message",
            body="This is a test message.",
            priority=priority
        )
        await manager.send(notification, immediate=True)
        print(f"   Sent {priority.name} priority notification")
    print()

    # 9. Webhook
    print("9. WEBHOOK NOTIFICATION:")
    print("-" * 40)

    notification = await manager.create_notification(
        channel=NotificationChannel.WEBHOOK,
        recipient_id="user1",
        body=json.dumps({"event": "user_action", "action": "login"}),
        metadata={"webhook_url": "https://example.com/webhook"}
    )

    result = await manager.send(notification, immediate=True)
    print(f"   Status: {result.status.value}")
    print()

    # 10. Slack
    print("10. SLACK NOTIFICATION:")
    print("-" * 40)

    notification = await manager.create_notification(
        channel=NotificationChannel.SLACK,
        recipient_id="user1",
        body="Hello from BAEL! :robot_face:",
        metadata={"slack_channel": "#bael-alerts"}
    )

    result = await manager.send(notification, immediate=True)
    print(f"   Status: {result.status.value}")
    print()

    # 11. Queue Workers
    print("11. QUEUE WORKERS:")
    print("-" * 40)

    await manager.start()
    print(f"   Started {manager.workers} workers")

    # Queue some notifications
    for i in range(5):
        notification = await manager.create_notification(
            channel=NotificationChannel.EMAIL,
            recipient_id="user1",
            subject=f"Queued Message {i+1}",
            body=f"This is queued message number {i+1}"
        )
        await manager.send(notification)

    queue_size = await manager.queue.size()
    print(f"   Queue size: {queue_size}")

    # Wait for processing
    await asyncio.sleep(1)

    queue_size = await manager.queue.size()
    print(f"   Queue size after processing: {queue_size}")

    await manager.stop()
    print("   Workers stopped")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total sent: {stats.total_sent}")
    print(f"   Total delivered: {stats.total_delivered}")
    print(f"   Total failed: {stats.total_failed}")
    print(f"   Avg delivery time: {stats.avg_delivery_time:.4f}s")
    print(f"   By channel: {dict(stats.by_channel)}")
    print(f"   By priority: {dict(stats.by_priority)}")
    print()

    # 13. History
    print("13. DELIVERY HISTORY:")
    print("-" * 40)

    history = manager.get_history(limit=5)
    for entry in history:
        print(f"   {entry.notification_id[:8]}: "
              f"{entry.channel.value} -> {entry.status.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Notification System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
