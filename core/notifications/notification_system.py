"""
BAEL - Notification System
Multi-channel notification and alerting system.

Features:
- Multi-channel delivery (email, Slack, SMS, push)
- Notification templates
- Priority-based routing
- Rate limiting
- Delivery tracking
- User preferences
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class NotificationChannel(Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    CONSOLE = "console"


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
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    READ = "read"


class NotificationType(Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"
    TASK = "task"
    REMINDER = "reminder"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NotificationRecipient:
    """Notification recipient."""
    id: str
    name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    slack_id: Optional[str] = None
    discord_id: Optional[str] = None
    push_token: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationAttachment:
    """Notification attachment."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    url: Optional[str] = None


@dataclass
class Notification:
    """Notification object."""
    id: str
    title: str
    body: str
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[NotificationChannel] = field(default_factory=list)
    recipients: List[NotificationRecipient] = field(default_factory=list)
    attachments: List[NotificationAttachment] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[str] = None
    template_vars: Dict[str, Any] = field(default_factory=dict)
    schedule_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: NotificationStatus = NotificationStatus.PENDING

    def __post_init__(self):
        if not self.channels:
            self.channels = [NotificationChannel.IN_APP]


@dataclass
class DeliveryResult:
    """Result of notification delivery."""
    notification_id: str
    channel: NotificationChannel
    recipient_id: str
    success: bool
    status: NotificationStatus
    message_id: Optional[str] = None
    error: Optional[str] = None
    delivered_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationTemplate:
    """Notification template."""
    id: str
    name: str
    title_template: str
    body_template: str
    channels: List[NotificationChannel] = field(default_factory=list)
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self, variables: Dict[str, Any]) -> tuple:
        """Render template with variables."""
        title = self.title_template
        body = self.body_template

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            title = title.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        return title, body


# =============================================================================
# NOTIFICATION PROVIDERS
# =============================================================================

class NotificationProvider(ABC):
    """Abstract notification provider."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        pass

    @abstractmethod
    async def send(
        self,
        notification: Notification,
        recipient: NotificationRecipient
    ) -> DeliveryResult:
        pass

    async def send_batch(
        self,
        notification: Notification,
        recipients: List[NotificationRecipient]
    ) -> List[DeliveryResult]:
        """Send to multiple recipients."""
        tasks = [
            self.send(notification, recipient)
            for recipient in recipients
        ]
        return await asyncio.gather(*tasks)


class ConsoleProvider(NotificationProvider):
    """Console/log notification provider."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.CONSOLE

    async def send(
        self,
        notification: Notification,
        recipient: NotificationRecipient
    ) -> DeliveryResult:
        """Print notification to console."""
        priority_icons = {
            NotificationPriority.LOW: "ℹ️",
            NotificationPriority.NORMAL: "📌",
            NotificationPriority.HIGH: "⚠️",
            NotificationPriority.URGENT: "🚨",
            NotificationPriority.CRITICAL: "🔴"
        }

        icon = priority_icons.get(notification.priority, "📌")

        print(f"\n{icon} [{notification.type.value.upper()}] {notification.title}")
        print(f"   To: {recipient.name or recipient.id}")
        print(f"   {notification.body}")

        return DeliveryResult(
            notification_id=notification.id,
            channel=self.channel,
            recipient_id=recipient.id,
            success=True,
            status=NotificationStatus.DELIVERED,
            delivered_at=datetime.now()
        )


class EmailProvider(NotificationProvider):
    """Email notification provider."""

    def __init__(
        self,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        username: str = "",
        password: str = ""
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    async def send(
        self,
        notification: Notification,
        recipient: NotificationRecipient
    ) -> DeliveryResult:
        """Send email notification."""
        if not recipient.email:
            return DeliveryResult(
                notification_id=notification.id,
                channel=self.channel,
                recipient_id=recipient.id,
                success=False,
                status=NotificationStatus.FAILED,
                error="No email address"
            )

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["From"] = self.username
            msg["To"] = recipient.email
            msg["Subject"] = notification.title

            # Create HTML body
            html_body = f"""
            <html>
            <body>
                <h2>{notification.title}</h2>
                <p>{notification.body}</p>
                <hr>
                <small>Sent by BAEL Notification System</small>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_body, "html"))

            # Add attachments
            for attachment in notification.attachments:
                from email import encoders
                from email.mime.base import MIMEBase

                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment.filename}"
                )
                msg.attach(part)

            # Send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return DeliveryResult(
                notification_id=notification.id,
                channel=self.channel,
                recipient_id=recipient.id,
                success=True,
                status=NotificationStatus.SENT,
                message_id=msg["Message-ID"],
                delivered_at=datetime.now()
            )

        except Exception as e:
            return DeliveryResult(
                notification_id=notification.id,
                channel=self.channel,
                recipient_id=recipient.id,
                success=False,
                status=NotificationStatus.FAILED,
                error=str(e)
            )


class SlackProvider(NotificationProvider):
    """Slack notification provider."""

    def __init__(self, token: str):
        self.token = token
        self._base_url = "https://slack.com/api"

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SLACK

    async def send(
        self,
        notification: Notification,
        recipient: NotificationRecipient
    ) -> DeliveryResult:
        """Send Slack notification."""
        channel_id = recipient.slack_id

        if not channel_id:
            return DeliveryResult(
                notification_id=notification.id,
                channel=self.channel,
                recipient_id=recipient.id,
                success=False,
                status=NotificationStatus.FAILED,
                error="No Slack ID"
            )

        try:
            import httpx

            # Build message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": notification.title}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": notification.body}
                }
            ]

            # Add priority indicator
            if notification.priority >= NotificationPriority.HIGH:
                blocks.insert(0, {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🚨 *{notification.priority.name} PRIORITY*"
                    }
                })

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": channel_id,
                        "text": notification.title,
                        "blocks": blocks
                    }
                )

                result = response.json()

                if result.get("ok"):
                    return DeliveryResult(
                        notification_id=notification.id,
                        channel=self.channel,
                        recipient_id=recipient.id,
                        success=True,
                        status=NotificationStatus.DELIVERED,
                        message_id=result.get("ts"),
                        delivered_at=datetime.now()
                    )
                else:
                    return DeliveryResult(
                        notification_id=notification.id,
                        channel=self.channel,
                        recipient_id=recipient.id,
                        success=False,
                        status=NotificationStatus.FAILED,
                        error=result.get("error")
                    )

        except Exception as e:
            return DeliveryResult(
                notification_id=notification.id,
                channel=self.channel,
                recipient_id=recipient.id,
                success=False,
                status=NotificationStatus.FAILED,
                error=str(e)
            )


class WebhookProvider(NotificationProvider):
    """Webhook notification provider."""

    def __init__(self, url: str, headers: Dict[str, str] = None):
        self.url = url
        self.headers = headers or {}

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WEBHOOK

    async def send(
        self,
        notification: Notification,
        recipient: NotificationRecipient
    ) -> DeliveryResult:
        """Send webhook notification."""
        try:
            import httpx

            payload = {
                "id": notification.id,
                "title": notification.title,
                "body": notification.body,
                "type": notification.type.value,
                "priority": notification.priority.value,
                "recipient": {
                    "id": recipient.id,
                    "name": recipient.name
                },
                "data": notification.data,
                "timestamp": datetime.now().isoformat()
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url,
                    headers={
                        "Content-Type": "application/json",
                        **self.headers
                    },
                    json=payload
                )

                return DeliveryResult(
                    notification_id=notification.id,
                    channel=self.channel,
                    recipient_id=recipient.id,
                    success=response.status_code < 400,
                    status=NotificationStatus.DELIVERED if response.status_code < 400 else NotificationStatus.FAILED,
                    metadata={"status_code": response.status_code}
                )

        except Exception as e:
            return DeliveryResult(
                notification_id=notification.id,
                channel=self.channel,
                recipient_id=recipient.id,
                success=False,
                status=NotificationStatus.FAILED,
                error=str(e)
            )


class InAppProvider(NotificationProvider):
    """In-app notification provider (stores for later retrieval)."""

    def __init__(self):
        self._notifications: Dict[str, List[Dict]] = {}  # user_id -> notifications

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.IN_APP

    async def send(
        self,
        notification: Notification,
        recipient: NotificationRecipient
    ) -> DeliveryResult:
        """Store in-app notification."""
        if recipient.id not in self._notifications:
            self._notifications[recipient.id] = []

        self._notifications[recipient.id].append({
            "id": notification.id,
            "title": notification.title,
            "body": notification.body,
            "type": notification.type.value,
            "priority": notification.priority.value,
            "data": notification.data,
            "read": False,
            "created_at": datetime.now().isoformat()
        })

        return DeliveryResult(
            notification_id=notification.id,
            channel=self.channel,
            recipient_id=recipient.id,
            success=True,
            status=NotificationStatus.DELIVERED,
            delivered_at=datetime.now()
        )

    def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False
    ) -> List[Dict]:
        """Get user notifications."""
        notifications = self._notifications.get(user_id, [])

        if unread_only:
            return [n for n in notifications if not n.get("read")]

        return notifications

    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark notification as read."""
        notifications = self._notifications.get(user_id, [])

        for n in notifications:
            if n["id"] == notification_id:
                n["read"] = True
                return True

        return False


# =============================================================================
# RATE LIMITER
# =============================================================================

class NotificationRateLimiter:
    """Rate limiter for notifications."""

    def __init__(
        self,
        max_per_minute: int = 60,
        max_per_hour: int = 500,
        max_per_day: int = 5000
    ):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        self._counts: Dict[str, List[float]] = {}

    def check(
        self,
        key: str,
        channel: Optional[NotificationChannel] = None
    ) -> bool:
        """Check if notification is allowed."""
        now = time.time()
        rate_key = f"{key}:{channel.value if channel else 'all'}"

        if rate_key not in self._counts:
            self._counts[rate_key] = []

        # Clean old entries
        minute_ago = now - 60
        hour_ago = now - 3600
        day_ago = now - 86400

        self._counts[rate_key] = [
            t for t in self._counts[rate_key]
            if t > day_ago
        ]

        # Check limits
        minute_count = sum(1 for t in self._counts[rate_key] if t > minute_ago)
        hour_count = sum(1 for t in self._counts[rate_key] if t > hour_ago)
        day_count = len(self._counts[rate_key])

        if minute_count >= self.max_per_minute:
            logger.warning(f"Rate limit reached (minute): {rate_key}")
            return False

        if hour_count >= self.max_per_hour:
            logger.warning(f"Rate limit reached (hour): {rate_key}")
            return False

        if day_count >= self.max_per_day:
            logger.warning(f"Rate limit reached (day): {rate_key}")
            return False

        return True

    def record(
        self,
        key: str,
        channel: Optional[NotificationChannel] = None
    ) -> None:
        """Record a notification."""
        rate_key = f"{key}:{channel.value if channel else 'all'}"

        if rate_key not in self._counts:
            self._counts[rate_key] = []

        self._counts[rate_key].append(time.time())


# =============================================================================
# TEMPLATE MANAGER
# =============================================================================

class TemplateManager:
    """Notification template manager."""

    def __init__(self):
        self._templates: Dict[str, NotificationTemplate] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default templates."""
        defaults = [
            NotificationTemplate(
                id="welcome",
                name="Welcome",
                title_template="Welcome to BAEL, {{name}}!",
                body_template="Hello {{name}}, welcome to BAEL - The Lord of All AI Agents. Your account has been created successfully.",
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
                type=NotificationType.SUCCESS
            ),
            NotificationTemplate(
                id="task_complete",
                name="Task Complete",
                title_template="Task Completed: {{task_name}}",
                body_template="Your task '{{task_name}}' has been completed successfully.\n\nDuration: {{duration}}\nResult: {{result}}",
                channels=[NotificationChannel.IN_APP, NotificationChannel.SLACK],
                type=NotificationType.SUCCESS
            ),
            NotificationTemplate(
                id="error_alert",
                name="Error Alert",
                title_template="🚨 Error: {{error_type}}",
                body_template="An error occurred in {{component}}:\n\n{{error_message}}\n\nTimestamp: {{timestamp}}",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                type=NotificationType.ERROR,
                priority=NotificationPriority.HIGH
            ),
            NotificationTemplate(
                id="daily_summary",
                name="Daily Summary",
                title_template="Daily Summary - {{date}}",
                body_template="Here's your daily summary:\n\n• Tasks completed: {{tasks_completed}}\n• Agents active: {{agents_active}}\n• Messages processed: {{messages_processed}}",
                channels=[NotificationChannel.EMAIL],
                type=NotificationType.INFO
            ),
            NotificationTemplate(
                id="security_alert",
                name="Security Alert",
                title_template="🔐 Security Alert: {{alert_type}}",
                body_template="A security event has been detected:\n\n{{description}}\n\nIP: {{ip_address}}\nTime: {{timestamp}}\n\nPlease review immediately.",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.SMS],
                type=NotificationType.ALERT,
                priority=NotificationPriority.CRITICAL
            )
        ]

        for template in defaults:
            self._templates[template.id] = template

    def register(self, template: NotificationTemplate) -> None:
        """Register a template."""
        self._templates[template.id] = template

    def get(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> List[NotificationTemplate]:
        """List all templates."""
        return list(self._templates.values())

    def create_notification(
        self,
        template_id: str,
        variables: Dict[str, Any],
        recipients: List[NotificationRecipient],
        **overrides
    ) -> Optional[Notification]:
        """Create notification from template."""
        template = self.get(template_id)

        if not template:
            return None

        title, body = template.render(variables)

        return Notification(
            id=hashlib.md5(f"{template_id}:{time.time()}".encode()).hexdigest()[:16],
            title=title,
            body=body,
            type=overrides.get("type", template.type),
            priority=overrides.get("priority", template.priority),
            channels=overrides.get("channels", template.channels.copy()),
            recipients=recipients,
            template_id=template_id,
            template_vars=variables,
            **{k: v for k, v in overrides.items() if k not in ("type", "priority", "channels")}
        )


# =============================================================================
# NOTIFICATION SERVICE
# =============================================================================

class NotificationService:
    """Main notification service."""

    def __init__(self):
        self._providers: Dict[NotificationChannel, NotificationProvider] = {}
        self._queue: List[Notification] = []
        self._history: List[DeliveryResult] = []
        self._running = False

        self.rate_limiter = NotificationRateLimiter()
        self.templates = TemplateManager()

        # Register default providers
        self.register_provider(ConsoleProvider())
        self.register_provider(InAppProvider())

    def register_provider(self, provider: NotificationProvider) -> None:
        """Register notification provider."""
        self._providers[provider.channel] = provider
        logger.info(f"Registered provider: {provider.channel.value}")

    def get_provider(self, channel: NotificationChannel) -> Optional[NotificationProvider]:
        """Get provider for channel."""
        return self._providers.get(channel)

    async def send(
        self,
        notification: Notification,
        immediate: bool = True
    ) -> List[DeliveryResult]:
        """Send notification."""
        results = []

        for channel in notification.channels:
            provider = self._providers.get(channel)

            if not provider:
                logger.warning(f"No provider for channel: {channel.value}")
                continue

            for recipient in notification.recipients:
                # Check rate limit
                if not self.rate_limiter.check(recipient.id, channel):
                    results.append(DeliveryResult(
                        notification_id=notification.id,
                        channel=channel,
                        recipient_id=recipient.id,
                        success=False,
                        status=NotificationStatus.FAILED,
                        error="Rate limit exceeded"
                    ))
                    continue

                # Check user preferences
                if not self._check_preferences(recipient, channel, notification):
                    continue

                if immediate:
                    result = await provider.send(notification, recipient)
                    results.append(result)

                    if result.success:
                        self.rate_limiter.record(recipient.id, channel)
                else:
                    self._queue.append(notification)

        # Store history
        self._history.extend(results)

        return results

    async def send_from_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        recipients: List[NotificationRecipient],
        **overrides
    ) -> List[DeliveryResult]:
        """Send notification from template."""
        notification = self.templates.create_notification(
            template_id,
            variables,
            recipients,
            **overrides
        )

        if not notification:
            return []

        return await self.send(notification)

    def _check_preferences(
        self,
        recipient: NotificationRecipient,
        channel: NotificationChannel,
        notification: Notification
    ) -> bool:
        """Check if recipient wants this notification."""
        prefs = recipient.preferences

        # Check channel preference
        disabled_channels = prefs.get("disabled_channels", [])
        if channel.value in disabled_channels:
            return False

        # Check type preference
        disabled_types = prefs.get("disabled_types", [])
        if notification.type.value in disabled_types:
            return False

        # Check priority threshold
        min_priority = prefs.get("min_priority", 1)
        if notification.priority.value < min_priority:
            return False

        # Check quiet hours
        quiet_hours = prefs.get("quiet_hours")
        if quiet_hours:
            now = datetime.now()
            start = quiet_hours.get("start", 22)
            end = quiet_hours.get("end", 7)

            current_hour = now.hour
            if start <= current_hour or current_hour < end:
                # In quiet hours, only allow critical
                if notification.priority != NotificationPriority.CRITICAL:
                    return False

        return True

    async def process_queue(self) -> List[DeliveryResult]:
        """Process queued notifications."""
        results = []

        while self._queue:
            notification = self._queue.pop(0)

            # Check scheduled time
            if notification.schedule_at and notification.schedule_at > datetime.now():
                self._queue.append(notification)
                continue

            # Check expiry
            if notification.expires_at and notification.expires_at < datetime.now():
                continue

            batch_results = await self.send(notification)
            results.extend(batch_results)

        return results

    async def start_processor(self, interval: float = 1.0) -> None:
        """Start queue processor."""
        self._running = True

        while self._running:
            await self.process_queue()
            await asyncio.sleep(interval)

    def stop_processor(self) -> None:
        """Stop queue processor."""
        self._running = False

    def get_history(
        self,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None
    ) -> List[DeliveryResult]:
        """Get notification history."""
        history = self._history[-limit:]

        if channel:
            history = [r for r in history if r.channel == channel]

        if status:
            history = [r for r in history if r.status == status]

        return history

    def get_in_app_notifications(
        self,
        user_id: str,
        unread_only: bool = False
    ) -> List[Dict]:
        """Get in-app notifications for user."""
        provider = self._providers.get(NotificationChannel.IN_APP)

        if isinstance(provider, InAppProvider):
            return provider.get_notifications(user_id, unread_only)

        return []


# =============================================================================
# QUICK NOTIFICATION FUNCTIONS
# =============================================================================

_default_service: Optional[NotificationService] = None


def get_service() -> NotificationService:
    """Get default notification service."""
    global _default_service

    if _default_service is None:
        _default_service = NotificationService()

    return _default_service


async def notify(
    title: str,
    body: str,
    recipients: List[Union[str, NotificationRecipient]],
    type: NotificationType = NotificationType.INFO,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    channels: List[NotificationChannel] = None
) -> List[DeliveryResult]:
    """Quick notification function."""
    service = get_service()

    # Convert string recipients
    recipient_objects = []
    for r in recipients:
        if isinstance(r, str):
            recipient_objects.append(NotificationRecipient(id=r, name=r))
        else:
            recipient_objects.append(r)

    notification = Notification(
        id=hashlib.md5(f"{title}:{time.time()}".encode()).hexdigest()[:16],
        title=title,
        body=body,
        type=type,
        priority=priority,
        channels=channels or [NotificationChannel.CONSOLE],
        recipients=recipient_objects
    )

    return await service.send(notification)


async def alert(
    message: str,
    recipients: List[Union[str, NotificationRecipient]],
    priority: NotificationPriority = NotificationPriority.HIGH
) -> List[DeliveryResult]:
    """Quick alert function."""
    return await notify(
        title="🚨 Alert",
        body=message,
        recipients=recipients,
        type=NotificationType.ALERT,
        priority=priority,
        channels=[NotificationChannel.CONSOLE, NotificationChannel.IN_APP]
    )


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def main():
    """Demonstrate notification system."""
    print("=== BAEL Notification System ===\n")

    service = NotificationService()

    # Create recipients
    recipients = [
        NotificationRecipient(
            id="user1",
            name="Alice",
            email="alice@example.com"
        ),
        NotificationRecipient(
            id="user2",
            name="Bob",
            slack_id="U12345"
        )
    ]

    # Show available templates
    print("--- Available Templates ---")
    for template in service.templates.list_templates():
        print(f"  - {template.id}: {template.name}")

    # Send direct notification
    print("\n--- Direct Notification ---")
    notification = Notification(
        id="notif_001",
        title="Task Completed",
        body="Your AI agent has finished processing the request.",
        type=NotificationType.SUCCESS,
        priority=NotificationPriority.NORMAL,
        channels=[NotificationChannel.CONSOLE],
        recipients=recipients
    )

    results = await service.send(notification)

    print(f"\nDelivery results:")
    for result in results:
        print(f"  - {result.recipient_id}: {result.status.value}")

    # Send from template
    print("\n--- Template Notification ---")
    template_results = await service.send_from_template(
        "task_complete",
        {
            "task_name": "Data Analysis",
            "duration": "5 minutes",
            "result": "Success"
        },
        recipients[:1],
        channels=[NotificationChannel.CONSOLE]
    )

    # Quick notification
    print("\n--- Quick Notification ---")
    await notify(
        "System Update",
        "BAEL has been updated to version 2.0",
        ["admin"],
        type=NotificationType.INFO
    )

    # Alert
    print("\n--- Alert ---")
    await alert(
        "High CPU usage detected on agent-001",
        ["ops-team"]
    )

    # Show history
    print("\n--- Notification History ---")
    history = service.get_history(limit=5)
    print(f"Last {len(history)} notifications:")
    for r in history:
        print(f"  - {r.notification_id[:8]}... -> {r.status.value}")

    print("\n=== Notification System ready ===")


if __name__ == "__main__":
    asyncio.run(main())
