#!/usr/bin/env python3
"""
BAEL - Notification Engine
Notification management for agents.

Features:
- Multi-channel notifications
- Priority levels
- Templates
- Delivery tracking
- Rate limiting
"""

import asyncio
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

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
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    IN_APP = "in_app"
    LOG = "log"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationStatus(Enum):
    """Notification status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationType(Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Recipient:
    """Notification recipient."""
    recipient_id: str = ""
    name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    channels: List[NotificationChannel] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.recipient_id:
            self.recipient_id = str(uuid.uuid4())[:8]


@dataclass
class Notification:
    """A notification."""
    notification_id: str = ""
    title: str = ""
    body: str = ""
    channel: NotificationChannel = NotificationChannel.IN_APP
    priority: NotificationPriority = NotificationPriority.NORMAL
    notification_type: NotificationType = NotificationType.INFO
    recipient_id: Optional[str] = None
    status: NotificationStatus = NotificationStatus.PENDING
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self):
        if not self.notification_id:
            self.notification_id = str(uuid.uuid4())[:8]


@dataclass
class NotificationTemplate:
    """Notification template."""
    template_id: str = ""
    name: str = ""
    title_template: str = ""
    body_template: str = ""
    channel: NotificationChannel = NotificationChannel.IN_APP
    variables: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.template_id:
            self.template_id = str(uuid.uuid4())[:8]


@dataclass
class DeliveryResult:
    """Delivery result."""
    notification_id: str = ""
    success: bool = False
    channel: NotificationChannel = NotificationChannel.IN_APP
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    response: Optional[Dict[str, Any]] = None


@dataclass
class NotificationConfig:
    """Notification engine configuration."""
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    rate_limit_per_minute: int = 60
    default_channel: NotificationChannel = NotificationChannel.IN_APP
    default_priority: NotificationPriority = NotificationPriority.NORMAL


# =============================================================================
# CHANNEL PROVIDER INTERFACE
# =============================================================================

class ChannelProvider(ABC):
    """Base interface for channel providers."""

    @abstractmethod
    async def send(
        self,
        notification: Notification,
        recipient: Optional[Recipient] = None
    ) -> DeliveryResult:
        """Send notification."""
        pass

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Get channel type."""
        pass


# =============================================================================
# LOG PROVIDER
# =============================================================================

class LogProvider(ChannelProvider):
    """Log notification provider (for testing/demo)."""

    def __init__(self):
        self._log: List[Notification] = []

    async def send(
        self,
        notification: Notification,
        recipient: Optional[Recipient] = None
    ) -> DeliveryResult:
        """Log the notification."""
        self._log.append(notification)

        return DeliveryResult(
            notification_id=notification.notification_id,
            success=True,
            channel=self.channel,
            response={"logged": True}
        )

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.LOG

    def get_log(self) -> List[Notification]:
        """Get logged notifications."""
        return list(self._log)


# =============================================================================
# IN-APP PROVIDER
# =============================================================================

class InAppProvider(ChannelProvider):
    """In-app notification provider."""

    def __init__(self):
        self._notifications: Dict[str, List[Notification]] = defaultdict(list)

    async def send(
        self,
        notification: Notification,
        recipient: Optional[Recipient] = None
    ) -> DeliveryResult:
        """Store in-app notification."""
        recipient_id = recipient.recipient_id if recipient else "global"
        self._notifications[recipient_id].append(notification)

        return DeliveryResult(
            notification_id=notification.notification_id,
            success=True,
            channel=self.channel,
            response={"stored": True, "recipient": recipient_id}
        )

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.IN_APP

    def get_notifications(self, recipient_id: str) -> List[Notification]:
        """Get notifications for recipient."""
        return self._notifications.get(recipient_id, [])

    def clear(self, recipient_id: str) -> int:
        """Clear notifications for recipient."""
        count = len(self._notifications.get(recipient_id, []))
        self._notifications[recipient_id] = []
        return count


# =============================================================================
# WEBHOOK PROVIDER
# =============================================================================

class WebhookProvider(ChannelProvider):
    """Webhook notification provider (mock)."""

    def __init__(self, webhook_url: str = ""):
        self._webhook_url = webhook_url
        self._sent: List[Dict[str, Any]] = []

    async def send(
        self,
        notification: Notification,
        recipient: Optional[Recipient] = None
    ) -> DeliveryResult:
        """Send webhook notification (mock)."""
        payload = {
            "id": notification.notification_id,
            "title": notification.title,
            "body": notification.body,
            "priority": notification.priority.value,
            "type": notification.notification_type.value,
            "timestamp": notification.created_at.isoformat()
        }

        self._sent.append(payload)

        return DeliveryResult(
            notification_id=notification.notification_id,
            success=True,
            channel=self.channel,
            response={"webhook": self._webhook_url, "payload": payload}
        )

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WEBHOOK

    def get_sent(self) -> List[Dict[str, Any]]:
        """Get sent webhooks."""
        return list(self._sent)


# =============================================================================
# EMAIL PROVIDER (Mock)
# =============================================================================

class EmailProvider(ChannelProvider):
    """Email notification provider (mock)."""

    def __init__(self):
        self._sent: List[Dict[str, Any]] = []

    async def send(
        self,
        notification: Notification,
        recipient: Optional[Recipient] = None
    ) -> DeliveryResult:
        """Send email notification (mock)."""
        email = recipient.email if recipient else None

        if not email:
            return DeliveryResult(
                notification_id=notification.notification_id,
                success=False,
                channel=self.channel,
                error="No email address provided"
            )

        email_data = {
            "to": email,
            "subject": notification.title,
            "body": notification.body,
            "priority": notification.priority.value
        }

        self._sent.append(email_data)

        return DeliveryResult(
            notification_id=notification.notification_id,
            success=True,
            channel=self.channel,
            response=email_data
        )

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL


# =============================================================================
# TEMPLATE MANAGER
# =============================================================================

class TemplateManager:
    """Manage notification templates."""

    def __init__(self):
        self._templates: Dict[str, NotificationTemplate] = {}

    def create(
        self,
        name: str,
        title_template: str,
        body_template: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
    ) -> NotificationTemplate:
        """Create a template."""
        variables = self._extract_variables(title_template + body_template)

        template = NotificationTemplate(
            name=name,
            title_template=title_template,
            body_template=body_template,
            channel=channel,
            variables=variables
        )

        self._templates[template.template_id] = template

        return template

    def _extract_variables(self, text: str) -> List[str]:
        """Extract template variables."""
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, text)))

    def get(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)

    def get_by_name(self, name: str) -> Optional[NotificationTemplate]:
        """Get template by name."""
        for template in self._templates.values():
            if template.name == name:
                return template
        return None

    def render(
        self,
        template: NotificationTemplate,
        variables: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Render template with variables."""
        title = template.title_template
        body = template.body_template

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            title = title.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        return title, body

    def list(self) -> List[NotificationTemplate]:
        """List all templates."""
        return list(self._templates.values())

    def delete(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False


# =============================================================================
# RECIPIENT MANAGER
# =============================================================================

class RecipientManager:
    """Manage notification recipients."""

    def __init__(self):
        self._recipients: Dict[str, Recipient] = {}

    def create(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Recipient:
        """Create a recipient."""
        recipient = Recipient(
            name=name,
            email=email,
            phone=phone,
            channels=channels or [NotificationChannel.IN_APP]
        )

        self._recipients[recipient.recipient_id] = recipient

        return recipient

    def get(self, recipient_id: str) -> Optional[Recipient]:
        """Get recipient by ID."""
        return self._recipients.get(recipient_id)

    def update_preferences(
        self,
        recipient_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update recipient preferences."""
        recipient = self._recipients.get(recipient_id)
        if recipient:
            recipient.preferences.update(preferences)
            return True
        return False

    def list(self) -> List[Recipient]:
        """List all recipients."""
        return list(self._recipients.values())

    def delete(self, recipient_id: str) -> bool:
        """Delete a recipient."""
        if recipient_id in self._recipients:
            del self._recipients[recipient_id]
            return True
        return False


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Rate limit notifications."""

    def __init__(self, max_per_minute: int = 60):
        self._max_per_minute = max_per_minute
        self._timestamps: List[float] = []

    def check(self) -> bool:
        """Check if rate limit allows sending."""
        now = time.time()
        cutoff = now - 60

        self._timestamps = [t for t in self._timestamps if t > cutoff]

        return len(self._timestamps) < self._max_per_minute

    def record(self) -> None:
        """Record a send."""
        self._timestamps.append(time.time())

    def remaining(self) -> int:
        """Get remaining quota."""
        now = time.time()
        cutoff = now - 60

        self._timestamps = [t for t in self._timestamps if t > cutoff]

        return max(0, self._max_per_minute - len(self._timestamps))


# =============================================================================
# NOTIFICATION STORE
# =============================================================================

class NotificationStore:
    """Store notifications."""

    def __init__(self):
        self._notifications: Dict[str, Notification] = {}
        self._by_recipient: Dict[str, List[str]] = defaultdict(list)
        self._by_status: Dict[NotificationStatus, List[str]] = defaultdict(list)

    def add(self, notification: Notification) -> str:
        """Add notification."""
        self._notifications[notification.notification_id] = notification

        if notification.recipient_id:
            self._by_recipient[notification.recipient_id].append(notification.notification_id)

        self._by_status[notification.status].append(notification.notification_id)

        return notification.notification_id

    def get(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID."""
        return self._notifications.get(notification_id)

    def update_status(
        self,
        notification_id: str,
        status: NotificationStatus,
        error: Optional[str] = None
    ) -> bool:
        """Update notification status."""
        notification = self._notifications.get(notification_id)

        if not notification:
            return False

        old_status = notification.status

        if notification_id in self._by_status.get(old_status, []):
            self._by_status[old_status].remove(notification_id)

        notification.status = status
        notification.error = error

        if status == NotificationStatus.SENT:
            notification.sent_at = datetime.now()
        elif status == NotificationStatus.DELIVERED:
            notification.delivered_at = datetime.now()

        self._by_status[status].append(notification_id)

        return True

    def get_by_recipient(
        self,
        recipient_id: str,
        limit: int = 100
    ) -> List[Notification]:
        """Get notifications for recipient."""
        ids = self._by_recipient.get(recipient_id, [])
        return [self._notifications[id] for id in ids[-limit:]]

    def get_by_status(
        self,
        status: NotificationStatus,
        limit: int = 100
    ) -> List[Notification]:
        """Get notifications by status."""
        ids = self._by_status.get(status, [])
        return [self._notifications[id] for id in ids[-limit:]]

    def count(self) -> int:
        """Count notifications."""
        return len(self._notifications)

    def count_by_status(self) -> Dict[str, int]:
        """Count by status."""
        return {s.value: len(ids) for s, ids in self._by_status.items()}


# =============================================================================
# NOTIFICATION ENGINE
# =============================================================================

class NotificationEngine:
    """
    Notification Engine for BAEL.

    Multi-channel notification management.
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self._config = config or NotificationConfig()

        self._providers: Dict[NotificationChannel, ChannelProvider] = {}
        self._templates = TemplateManager()
        self._recipients = RecipientManager()
        self._store = NotificationStore()
        self._rate_limiter = RateLimiter(self._config.rate_limit_per_minute)

        self._register_default_providers()

    def _register_default_providers(self) -> None:
        """Register default providers."""
        self.register_provider(LogProvider())
        self.register_provider(InAppProvider())
        self.register_provider(WebhookProvider())
        self.register_provider(EmailProvider())

    # ----- Provider Management -----

    def register_provider(self, provider: ChannelProvider) -> None:
        """Register a channel provider."""
        self._providers[provider.channel] = provider

    def get_provider(self, channel: NotificationChannel) -> Optional[ChannelProvider]:
        """Get provider for channel."""
        return self._providers.get(channel)

    def available_channels(self) -> List[NotificationChannel]:
        """List available channels."""
        return list(self._providers.keys())

    # ----- Send Notifications -----

    async def send(
        self,
        title: str,
        body: str,
        channel: Optional[NotificationChannel] = None,
        priority: Optional[NotificationPriority] = None,
        notification_type: NotificationType = NotificationType.INFO,
        recipient_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """Send a notification."""
        if not self._rate_limiter.check():
            return DeliveryResult(
                notification_id="",
                success=False,
                channel=channel or self._config.default_channel,
                error="Rate limit exceeded"
            )

        ch = channel or self._config.default_channel
        pr = priority or self._config.default_priority

        notification = Notification(
            title=title,
            body=body,
            channel=ch,
            priority=pr,
            notification_type=notification_type,
            recipient_id=recipient_id,
            data=data or {}
        )

        self._store.add(notification)

        provider = self._providers.get(ch)

        if not provider:
            self._store.update_status(
                notification.notification_id,
                NotificationStatus.FAILED,
                f"No provider for channel: {ch.value}"
            )
            return DeliveryResult(
                notification_id=notification.notification_id,
                success=False,
                channel=ch,
                error=f"No provider for channel: {ch.value}"
            )

        recipient = None
        if recipient_id:
            recipient = self._recipients.get(recipient_id)

        self._store.update_status(
            notification.notification_id,
            NotificationStatus.SENDING
        )

        result = await provider.send(notification, recipient)

        self._rate_limiter.record()

        if result.success:
            self._store.update_status(
                notification.notification_id,
                NotificationStatus.SENT
            )
        else:
            self._store.update_status(
                notification.notification_id,
                NotificationStatus.FAILED,
                result.error
            )

        return result

    async def send_template(
        self,
        template_name: str,
        variables: Dict[str, Any],
        channel: Optional[NotificationChannel] = None,
        recipient_id: Optional[str] = None
    ) -> DeliveryResult:
        """Send notification from template."""
        template = self._templates.get_by_name(template_name)

        if not template:
            return DeliveryResult(
                notification_id="",
                success=False,
                channel=channel or self._config.default_channel,
                error=f"Template not found: {template_name}"
            )

        title, body = self._templates.render(template, variables)

        return await self.send(
            title=title,
            body=body,
            channel=channel or template.channel,
            recipient_id=recipient_id
        )

    async def broadcast(
        self,
        title: str,
        body: str,
        channel: Optional[NotificationChannel] = None,
        recipient_ids: Optional[List[str]] = None
    ) -> List[DeliveryResult]:
        """Broadcast to multiple recipients."""
        results = []

        if recipient_ids:
            for recipient_id in recipient_ids:
                result = await self.send(
                    title=title,
                    body=body,
                    channel=channel,
                    recipient_id=recipient_id
                )
                results.append(result)
        else:
            result = await self.send(
                title=title,
                body=body,
                channel=channel
            )
            results.append(result)

        return results

    # ----- Template Management -----

    def create_template(
        self,
        name: str,
        title_template: str,
        body_template: str,
        channel: NotificationChannel = NotificationChannel.IN_APP
    ) -> NotificationTemplate:
        """Create a notification template."""
        return self._templates.create(name, title_template, body_template, channel)

    def get_template(self, name: str) -> Optional[NotificationTemplate]:
        """Get template by name."""
        return self._templates.get_by_name(name)

    def list_templates(self) -> List[NotificationTemplate]:
        """List all templates."""
        return self._templates.list()

    # ----- Recipient Management -----

    def create_recipient(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Recipient:
        """Create a recipient."""
        return self._recipients.create(name, email, phone, channels)

    def get_recipient(self, recipient_id: str) -> Optional[Recipient]:
        """Get recipient by ID."""
        return self._recipients.get(recipient_id)

    def list_recipients(self) -> List[Recipient]:
        """List all recipients."""
        return self._recipients.list()

    # ----- Notification History -----

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID."""
        return self._store.get(notification_id)

    def get_notifications_for_recipient(
        self,
        recipient_id: str,
        limit: int = 100
    ) -> List[Notification]:
        """Get notifications for recipient."""
        return self._store.get_by_recipient(recipient_id, limit)

    def get_pending(self, limit: int = 100) -> List[Notification]:
        """Get pending notifications."""
        return self._store.get_by_status(NotificationStatus.PENDING, limit)

    def get_failed(self, limit: int = 100) -> List[Notification]:
        """Get failed notifications."""
        return self._store.get_by_status(NotificationStatus.FAILED, limit)

    # ----- Rate Limiting -----

    def rate_limit_remaining(self) -> int:
        """Get remaining rate limit quota."""
        return self._rate_limiter.remaining()

    # ----- Info -----

    def stats(self) -> Dict[str, Any]:
        """Get notification stats."""
        return {
            "total_notifications": self._store.count(),
            "by_status": self._store.count_by_status(),
            "templates": len(self._templates.list()),
            "recipients": len(self._recipients.list()),
            "channels": [c.value for c in self.available_channels()],
            "rate_limit_remaining": self._rate_limiter.remaining()
        }

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_notifications": self._store.count(),
            "available_channels": [c.value for c in self.available_channels()],
            "templates": len(self._templates.list()),
            "recipients": len(self._recipients.list()),
            "default_channel": self._config.default_channel.value,
            "rate_limit": self._config.rate_limit_per_minute
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Notification Engine."""
    print("=" * 70)
    print("BAEL - NOTIFICATION ENGINE DEMO")
    print("Multi-Channel Notifications")
    print("=" * 70)
    print()

    engine = NotificationEngine()

    # 1. Available Channels
    print("1. AVAILABLE CHANNELS:")
    print("-" * 40)

    for channel in engine.available_channels():
        print(f"   - {channel.value}")
    print()

    # 2. Create Recipients
    print("2. CREATE RECIPIENTS:")
    print("-" * 40)

    user1 = engine.create_recipient(
        name="Alice",
        email="alice@example.com",
        channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
    )
    print(f"   Created: {user1.name} ({user1.recipient_id})")

    user2 = engine.create_recipient(
        name="Bob",
        email="bob@example.com"
    )
    print(f"   Created: {user2.name} ({user2.recipient_id})")
    print()

    # 3. Send Basic Notification
    print("3. SEND BASIC NOTIFICATION:")
    print("-" * 40)

    result = await engine.send(
        title="Welcome to BAEL",
        body="Your AI agent system is ready.",
        channel=NotificationChannel.LOG
    )
    print(f"   Sent: {result.success}")
    print(f"   Notification ID: {result.notification_id}")
    print()

    # 4. Send to Recipient
    print("4. SEND TO RECIPIENT:")
    print("-" * 40)

    result = await engine.send(
        title="Hello Alice",
        body="This is a personalized message.",
        channel=NotificationChannel.IN_APP,
        recipient_id=user1.recipient_id
    )
    print(f"   Sent to: {user1.name}")
    print(f"   Success: {result.success}")
    print()

    # 5. Priority Levels
    print("5. PRIORITY LEVELS:")
    print("-" * 40)

    for priority in NotificationPriority:
        result = await engine.send(
            title=f"{priority.value.upper()} Alert",
            body=f"This is a {priority.value} priority message.",
            priority=priority,
            channel=NotificationChannel.LOG
        )
        print(f"   {priority.value}: sent={result.success}")
    print()

    # 6. Notification Types
    print("6. NOTIFICATION TYPES:")
    print("-" * 40)

    for ntype in NotificationType:
        result = await engine.send(
            title=f"{ntype.value.upper()} Notification",
            body=f"This is a {ntype.value} notification.",
            notification_type=ntype,
            channel=NotificationChannel.LOG
        )
        print(f"   {ntype.value}: sent={result.success}")
    print()

    # 7. Create Template
    print("7. CREATE TEMPLATE:")
    print("-" * 40)

    template = engine.create_template(
        name="welcome_email",
        title_template="Welcome {{name}}!",
        body_template="Hello {{name}}, your account was created on {{date}}. Your ID is {{id}}.",
        channel=NotificationChannel.EMAIL
    )
    print(f"   Template: {template.name}")
    print(f"   Variables: {template.variables}")
    print()

    # 8. Send from Template
    print("8. SEND FROM TEMPLATE:")
    print("-" * 40)

    result = await engine.send_template(
        template_name="welcome_email",
        variables={
            "name": "Charlie",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "id": "USR-12345"
        },
        recipient_id=user1.recipient_id
    )
    print(f"   Sent from template: {result.success}")
    print()

    # 9. Broadcast
    print("9. BROADCAST:")
    print("-" * 40)

    results = await engine.broadcast(
        title="System Announcement",
        body="Scheduled maintenance tonight at midnight.",
        channel=NotificationChannel.IN_APP,
        recipient_ids=[user1.recipient_id, user2.recipient_id]
    )
    print(f"   Broadcast to {len(results)} recipients")
    for r in results:
        print(f"   - {r.notification_id}: success={r.success}")
    print()

    # 10. Get Notification History
    print("10. NOTIFICATION HISTORY:")
    print("-" * 40)

    notifications = engine.get_notifications_for_recipient(user1.recipient_id)
    print(f"   Notifications for {user1.name}: {len(notifications)}")
    for n in notifications[:3]:
        print(f"   - {n.title} ({n.status.value})")
    print()

    # 11. Webhook Notification
    print("11. WEBHOOK NOTIFICATION:")
    print("-" * 40)

    result = await engine.send(
        title="Webhook Test",
        body="Testing webhook notification delivery.",
        channel=NotificationChannel.WEBHOOK,
        data={"custom_field": "custom_value"}
    )
    print(f"   Webhook sent: {result.success}")
    if result.response:
        print(f"   Response: {json.dumps(result.response, indent=2)[:100]}...")
    print()

    # 12. Email Notification
    print("12. EMAIL NOTIFICATION:")
    print("-" * 40)

    result = await engine.send(
        title="Important Update",
        body="Please review the latest changes.",
        channel=NotificationChannel.EMAIL,
        recipient_id=user1.recipient_id
    )
    print(f"   Email sent: {result.success}")
    print()

    # 13. Rate Limiting
    print("13. RATE LIMITING:")
    print("-" * 40)

    remaining = engine.rate_limit_remaining()
    print(f"   Rate limit remaining: {remaining}/minute")
    print()

    # 14. Failed Notifications
    print("14. FAILED NOTIFICATIONS:")
    print("-" * 40)

    failed = engine.get_failed()
    print(f"   Failed notifications: {len(failed)}")
    for n in failed[:3]:
        print(f"   - {n.title}: {n.error}")
    print()

    # 15. Statistics
    print("15. NOTIFICATION STATISTICS:")
    print("-" * 40)

    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 16. List Templates
    print("16. LIST TEMPLATES:")
    print("-" * 40)

    templates = engine.list_templates()
    for t in templates:
        print(f"   - {t.name} ({t.channel.value})")
        print(f"     Variables: {t.variables}")
    print()

    # 17. List Recipients
    print("17. LIST RECIPIENTS:")
    print("-" * 40)

    recipients = engine.list_recipients()
    for r in recipients:
        print(f"   - {r.name}: {r.email}")
        print(f"     Channels: {[c.value for c in r.channels]}")
    print()

    # 18. Summary
    print("18. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Notification Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
