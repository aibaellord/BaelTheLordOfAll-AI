"""
BAEL Communications Engine
==========================

Multi-channel messaging and notification system with:
- Multiple channel support (email, SMS, webhooks, etc.)
- Message queuing and retry
- Template-based messaging
- Event-driven notifications
- Delivery tracking

"Communicate across all dimensions." — Ba'el
"""

import asyncio
import hashlib
import json
import logging
import queue
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("BAEL.Communications")


# =============================================================================
# ENUMS
# =============================================================================

class ChannelType(Enum):
    """Communication channel types."""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    CONSOLE = "console"
    FILE = "file"
    PUSH = "push"
    INTERNAL = "internal"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class DeliveryStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    REJECTED = "rejected"


class NotificationType(Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"
    REMINDER = "reminder"
    UPDATE = "update"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Message:
    """A message to be sent."""
    id: str
    channel: ChannelType
    recipient: str
    subject: Optional[str] = None
    body: str = ""
    html_body: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel.value,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Notification:
    """A notification event."""
    id: str
    type: NotificationType
    title: str
    message: str
    source: str = "system"
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    read: bool = False
    dismissed: bool = False


@dataclass
class Channel:
    """A communication channel configuration."""
    name: str
    channel_type: ChannelType
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    rate_limit: Optional[int] = None  # messages per minute
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class DeliveryResult:
    """Result of a message delivery attempt."""
    message_id: str
    status: DeliveryStatus
    channel: ChannelType
    recipient: str
    timestamp: datetime = field(default_factory=datetime.now)
    attempts: int = 1
    error: Optional[str] = None
    response: Optional[Dict[str, Any]] = None


@dataclass
class CommunicationConfig:
    """Configuration for the communications engine."""
    queue_size: int = 10000
    batch_size: int = 100
    worker_count: int = 4
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    rate_limit_enabled: bool = True
    default_rate_limit: int = 60  # per minute
    storage_path: Path = field(default_factory=lambda: Path("data/communications"))


# =============================================================================
# TEMPLATE ENGINE
# =============================================================================

class TemplateEngine:
    """Simple template rendering engine."""

    def __init__(self):
        self._templates: Dict[str, str] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default templates."""
        self._templates = {
            "notification_email": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #333; color: white; padding: 10px; }
        .content { padding: 20px; }
        .footer { font-size: 12px; color: #666; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{title}}</h1>
    </div>
    <div class="content">
        <p>{{message}}</p>
        {{#if details}}
        <div class="details">
            <h3>Details:</h3>
            <pre>{{details}}</pre>
        </div>
        {{/if}}
    </div>
    <div class="footer">
        <p>This is an automated notification from BAEL.</p>
        <p>Sent at: {{timestamp}}</p>
    </div>
</body>
</html>
""",
            "alert_email": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .alert { background: #ff4444; color: white; padding: 15px; border-radius: 5px; }
        .content { padding: 20px; }
    </style>
</head>
<body>
    <div class="alert">
        <h1>⚠️ Alert: {{title}}</h1>
    </div>
    <div class="content">
        <p><strong>Severity:</strong> {{severity}}</p>
        <p><strong>Message:</strong> {{message}}</p>
        <p><strong>Time:</strong> {{timestamp}}</p>
    </div>
</body>
</html>
""",
            "slack_message": """
{
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "{{title}}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "{{message}}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Sent by BAEL at {{timestamp}}"
                }
            ]
        }
    ]
}
""",
            "simple_text": "{{title}}\n\n{{message}}\n\nSent at: {{timestamp}}"
        }

    def register(self, name: str, template: str):
        """Register a template."""
        self._templates[name] = template

    def get(self, name: str) -> Optional[str]:
        """Get a template by name."""
        return self._templates.get(name)

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with context."""
        template = self._templates.get(template_name, "{{message}}")
        return self._render_template(template, context)

    def render_string(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template string with context."""
        return self._render_template(template, context)

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context."""
        result = template

        # Simple variable substitution
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                result = result.replace(f"{{{{{key}}}}}", str(value))

        # Handle simple conditionals
        # {{#if variable}}...{{/if}}
        if_pattern = re.compile(r'\{\{#if (\w+)\}\}(.*?)\{\{/if\}\}', re.DOTALL)

        def replace_if(match):
            var_name = match.group(1)
            content = match.group(2)
            if context.get(var_name):
                return self._render_template(content, context)
            return ""

        result = if_pattern.sub(replace_if, result)

        return result

    def list_templates(self) -> List[str]:
        """List all template names."""
        return list(self._templates.keys())


# =============================================================================
# MESSAGE QUEUE
# =============================================================================

class MessageQueue:
    """Priority message queue."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_size)
        self._pending: Dict[str, Message] = {}
        self._lock = threading.Lock()

    def put(self, message: Message):
        """Add message to queue."""
        # Priority is inverted (higher priority = lower number)
        priority = -message.priority.value

        with self._lock:
            self._pending[message.id] = message

        self._queue.put((priority, message.created_at, message.id))

    def get(self, timeout: float = 1.0) -> Optional[Message]:
        """Get next message from queue."""
        try:
            _, _, message_id = self._queue.get(timeout=timeout)

            with self._lock:
                message = self._pending.pop(message_id, None)

            return message
        except queue.Empty:
            return None

    def size(self) -> int:
        """Get queue size."""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def clear(self):
        """Clear the queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        with self._lock:
            self._pending.clear()


# =============================================================================
# CHANNEL HANDLERS
# =============================================================================

class ChannelHandler:
    """Base class for channel handlers."""

    def __init__(self, channel: Channel):
        self.channel = channel
        self._last_send = 0.0
        self._send_count = 0

    async def send(self, message: Message) -> DeliveryResult:
        """Send a message. Override in subclasses."""
        raise NotImplementedError

    def _rate_limit(self):
        """Check and apply rate limiting."""
        if self.channel.rate_limit:
            now = time.time()
            if now - self._last_send < 60:
                if self._send_count >= self.channel.rate_limit:
                    time.sleep(1)
            else:
                self._send_count = 0

            self._last_send = now
            self._send_count += 1


class ConsoleChannelHandler(ChannelHandler):
    """Console output handler."""

    async def send(self, message: Message) -> DeliveryResult:
        self._rate_limit()

        print(f"\n{'='*60}")
        print(f"[{message.channel.value.upper()}] To: {message.recipient}")
        if message.subject:
            print(f"Subject: {message.subject}")
        print(f"Priority: {message.priority.name}")
        print("-" * 60)
        print(message.body)
        print("=" * 60)

        return DeliveryResult(
            message_id=message.id,
            status=DeliveryStatus.DELIVERED,
            channel=message.channel,
            recipient=message.recipient
        )


class FileChannelHandler(ChannelHandler):
    """File output handler."""

    async def send(self, message: Message) -> DeliveryResult:
        self._rate_limit()

        output_path = Path(self.channel.config.get("output_path", "data/messages"))
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{message.id}_{int(time.time())}.json"
        filepath = output_path / filename

        data = {
            **message.to_dict(),
            "html_body": message.html_body,
            "attachments": message.attachments
        }

        filepath.write_text(json.dumps(data, indent=2))

        return DeliveryResult(
            message_id=message.id,
            status=DeliveryStatus.DELIVERED,
            channel=message.channel,
            recipient=message.recipient,
            response={"file": str(filepath)}
        )


class EmailChannelHandler(ChannelHandler):
    """Email channel handler."""

    async def send(self, message: Message) -> DeliveryResult:
        self._rate_limit()

        try:
            # Get SMTP configuration
            smtp_host = self.channel.config.get("smtp_host", "localhost")
            smtp_port = self.channel.config.get("smtp_port", 587)
            smtp_user = self.channel.config.get("smtp_user")
            smtp_pass = self.channel.config.get("smtp_pass")
            from_addr = self.channel.config.get("from_address", "bael@localhost")

            # Create message
            if message.html_body:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(message.body, "plain"))
                msg.attach(MIMEText(message.html_body, "html"))
            else:
                msg = MIMEText(message.body, "plain")

            msg["Subject"] = message.subject or "BAEL Notification"
            msg["From"] = from_addr
            msg["To"] = message.recipient

            # Send (simulated in demo mode)
            if self.channel.config.get("demo_mode", True):
                logger.info(f"[DEMO] Would send email to {message.recipient}: {message.subject}")
                return DeliveryResult(
                    message_id=message.id,
                    status=DeliveryStatus.DELIVERED,
                    channel=message.channel,
                    recipient=message.recipient,
                    response={"demo": True}
                )

            # Real SMTP sending
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_user and smtp_pass:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [message.recipient], msg.as_string())

            return DeliveryResult(
                message_id=message.id,
                status=DeliveryStatus.DELIVERED,
                channel=message.channel,
                recipient=message.recipient
            )

        except Exception as e:
            return DeliveryResult(
                message_id=message.id,
                status=DeliveryStatus.FAILED,
                channel=message.channel,
                recipient=message.recipient,
                error=str(e)
            )


class WebhookChannelHandler(ChannelHandler):
    """Webhook channel handler."""

    async def send(self, message: Message) -> DeliveryResult:
        self._rate_limit()

        try:
            import urllib.request
            import urllib.error

            webhook_url = message.recipient  # URL is the recipient

            payload = {
                "id": message.id,
                "subject": message.subject,
                "body": message.body,
                "priority": message.priority.value,
                "timestamp": message.created_at.isoformat(),
                "metadata": message.metadata
            }

            # Demo mode
            if self.channel.config.get("demo_mode", True):
                logger.info(f"[DEMO] Would POST to webhook {webhook_url}")
                return DeliveryResult(
                    message_id=message.id,
                    status=DeliveryStatus.DELIVERED,
                    channel=message.channel,
                    recipient=message.recipient,
                    response={"demo": True}
                )

            # Real webhook call
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                status_code = response.status

            if 200 <= status_code < 300:
                return DeliveryResult(
                    message_id=message.id,
                    status=DeliveryStatus.DELIVERED,
                    channel=message.channel,
                    recipient=message.recipient
                )
            else:
                return DeliveryResult(
                    message_id=message.id,
                    status=DeliveryStatus.FAILED,
                    channel=message.channel,
                    recipient=message.recipient,
                    error=f"HTTP {status_code}"
                )

        except Exception as e:
            return DeliveryResult(
                message_id=message.id,
                status=DeliveryStatus.FAILED,
                channel=message.channel,
                recipient=message.recipient,
                error=str(e)
            )


class InternalChannelHandler(ChannelHandler):
    """Internal notification handler."""

    def __init__(self, channel: Channel, notification_manager: "NotificationManager"):
        super().__init__(channel)
        self.notification_manager = notification_manager

    async def send(self, message: Message) -> DeliveryResult:
        self._rate_limit()

        notification = Notification(
            id=message.id,
            type=NotificationType(message.metadata.get("notification_type", "info")),
            title=message.subject or "Notification",
            message=message.body,
            source=message.metadata.get("source", "system"),
            data=message.metadata
        )

        self.notification_manager.add(notification)

        return DeliveryResult(
            message_id=message.id,
            status=DeliveryStatus.DELIVERED,
            channel=message.channel,
            recipient=message.recipient
        )


# =============================================================================
# CHANNEL REGISTRY
# =============================================================================

class ChannelRegistry:
    """Registry for communication channels."""

    def __init__(self, notification_manager: "NotificationManager"):
        self._channels: Dict[str, Channel] = {}
        self._handlers: Dict[str, ChannelHandler] = {}
        self._notification_manager = notification_manager
        self._register_defaults()

    def _register_defaults(self):
        """Register default channels."""
        # Console channel
        console_channel = Channel(
            name="console",
            channel_type=ChannelType.CONSOLE
        )
        self.register(console_channel)

        # File channel
        file_channel = Channel(
            name="file",
            channel_type=ChannelType.FILE,
            config={"output_path": "data/messages"}
        )
        self.register(file_channel)

        # Internal channel
        internal_channel = Channel(
            name="internal",
            channel_type=ChannelType.INTERNAL
        )
        self.register(internal_channel)

        # Email channel (demo mode)
        email_channel = Channel(
            name="email",
            channel_type=ChannelType.EMAIL,
            config={"demo_mode": True}
        )
        self.register(email_channel)

        # Webhook channel (demo mode)
        webhook_channel = Channel(
            name="webhook",
            channel_type=ChannelType.WEBHOOK,
            config={"demo_mode": True}
        )
        self.register(webhook_channel)

    def register(self, channel: Channel):
        """Register a channel."""
        self._channels[channel.name] = channel

        # Create handler
        if channel.channel_type == ChannelType.CONSOLE:
            self._handlers[channel.name] = ConsoleChannelHandler(channel)
        elif channel.channel_type == ChannelType.FILE:
            self._handlers[channel.name] = FileChannelHandler(channel)
        elif channel.channel_type == ChannelType.EMAIL:
            self._handlers[channel.name] = EmailChannelHandler(channel)
        elif channel.channel_type == ChannelType.WEBHOOK:
            self._handlers[channel.name] = WebhookChannelHandler(channel)
        elif channel.channel_type == ChannelType.INTERNAL:
            self._handlers[channel.name] = InternalChannelHandler(
                channel, self._notification_manager
            )

    def get(self, name: str) -> Optional[Channel]:
        """Get a channel by name."""
        return self._channels.get(name)

    def get_handler(self, name: str) -> Optional[ChannelHandler]:
        """Get a channel handler by name."""
        return self._handlers.get(name)

    def list_channels(self) -> List[Channel]:
        """List all channels."""
        return list(self._channels.values())

    def get_by_type(self, channel_type: ChannelType) -> List[Channel]:
        """Get channels by type."""
        return [c for c in self._channels.values() if c.channel_type == channel_type]


# =============================================================================
# NOTIFICATION MANAGER
# =============================================================================

class NotificationManager:
    """Manages internal notifications."""

    def __init__(self, max_notifications: int = 1000):
        self.max_notifications = max_notifications
        self._notifications: List[Notification] = []
        self._subscribers: Dict[str, Callable[[Notification], None]] = {}
        self._lock = threading.Lock()

    def add(self, notification: Notification):
        """Add a notification."""
        with self._lock:
            self._notifications.insert(0, notification)

            # Trim if necessary
            if len(self._notifications) > self.max_notifications:
                self._notifications = self._notifications[:self.max_notifications]

        # Notify subscribers
        for callback in self._subscribers.values():
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"Notification callback error: {e}")

    def get(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        for n in self._notifications:
            if n.id == notification_id:
                return n
        return None

    def list(
        self,
        limit: int = 50,
        unread_only: bool = False,
        notification_type: Optional[NotificationType] = None
    ) -> List[Notification]:
        """List notifications."""
        result = self._notifications

        if unread_only:
            result = [n for n in result if not n.read]

        if notification_type:
            result = [n for n in result if n.type == notification_type]

        return result[:limit]

    def mark_read(self, notification_id: str):
        """Mark a notification as read."""
        notification = self.get(notification_id)
        if notification:
            notification.read = True

    def mark_all_read(self):
        """Mark all notifications as read."""
        for n in self._notifications:
            n.read = True

    def dismiss(self, notification_id: str):
        """Dismiss a notification."""
        notification = self.get(notification_id)
        if notification:
            notification.dismissed = True

    def clear_dismissed(self):
        """Clear dismissed notifications."""
        with self._lock:
            self._notifications = [n for n in self._notifications if not n.dismissed]

    def subscribe(self, name: str, callback: Callable[[Notification], None]):
        """Subscribe to notifications."""
        self._subscribers[name] = callback

    def unsubscribe(self, name: str):
        """Unsubscribe from notifications."""
        if name in self._subscribers:
            del self._subscribers[name]

    def count_unread(self) -> int:
        """Count unread notifications."""
        return sum(1 for n in self._notifications if not n.read)


# =============================================================================
# COMMUNICATIONS ENGINE
# =============================================================================

class CommunicationsEngine:
    """Main communications engine."""

    def __init__(self, config: Optional[CommunicationConfig] = None):
        self.config = config or CommunicationConfig()
        self.config.storage_path.mkdir(parents=True, exist_ok=True)

        self.templates = TemplateEngine()
        self.notifications = NotificationManager()
        self.channels = ChannelRegistry(self.notifications)
        self.queue = MessageQueue(self.config.queue_size)

        self._delivery_log: List[DeliveryResult] = []
        self._running = False
        self._workers: List[asyncio.Task] = []

    async def start(self):
        """Start the communications engine."""
        self._running = True

        # Start worker tasks
        for i in range(self.config.worker_count):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

        logger.info(f"Communications engine started with {self.config.worker_count} workers")

    async def stop(self):
        """Stop the communications engine."""
        self._running = False

        # Cancel workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        for worker in self._workers:
            try:
                await worker
            except asyncio.CancelledError:
                pass

        self._workers.clear()
        logger.info("Communications engine stopped")

    async def _worker_loop(self, worker_id: int):
        """Worker loop for processing messages."""
        while self._running:
            message = self.queue.get(timeout=0.1)

            if message:
                await self._process_message(message)
            else:
                await asyncio.sleep(0.1)

    async def _process_message(self, message: Message):
        """Process a single message."""
        # Find handler by channel type
        channel_name = message.channel.value
        handler = self.channels.get_handler(channel_name)

        if not handler:
            # Try to find by type
            channels = self.channels.get_by_type(message.channel)
            if channels:
                handler = self.channels.get_handler(channels[0].name)

        if not handler:
            logger.error(f"No handler for channel: {message.channel.value}")
            return

        # Send with retry
        attempts = 0
        result = None

        while attempts < self.config.max_retries:
            attempts += 1
            result = await handler.send(message)

            if result.status == DeliveryStatus.DELIVERED:
                break

            if self.config.retry_enabled and attempts < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay_seconds * attempts)

        if result:
            result.attempts = attempts
            self._delivery_log.append(result)

            # Trim delivery log
            if len(self._delivery_log) > 10000:
                self._delivery_log = self._delivery_log[-5000:]

    def send(
        self,
        channel: Union[ChannelType, str],
        recipient: str,
        body: str,
        subject: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs
    ) -> str:
        """Send a message."""
        if isinstance(channel, str):
            channel = ChannelType(channel)

        message_id = hashlib.md5(
            f"{recipient}{body}{time.time()}".encode()
        ).hexdigest()[:12]

        message = Message(
            id=message_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=priority,
            html_body=kwargs.get("html_body"),
            attachments=kwargs.get("attachments", []),
            metadata=kwargs.get("metadata", {}),
            scheduled_at=kwargs.get("scheduled_at"),
            expires_at=kwargs.get("expires_at")
        )

        self.queue.put(message)
        return message_id

    def send_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        **kwargs
    ) -> str:
        """Send an internal notification."""
        return self.send(
            channel=ChannelType.INTERNAL,
            recipient="internal",
            body=message,
            subject=title,
            metadata={
                "notification_type": notification_type.value,
                **kwargs.get("metadata", {})
            }
        )

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        **kwargs
    ) -> str:
        """Send an email."""
        return self.send(
            channel=ChannelType.EMAIL,
            recipient=to,
            body=body,
            subject=subject,
            html_body=html_body,
            **kwargs
        )

    def send_webhook(
        self,
        url: str,
        data: Dict[str, Any],
        **kwargs
    ) -> str:
        """Send a webhook."""
        return self.send(
            channel=ChannelType.WEBHOOK,
            recipient=url,
            body=json.dumps(data),
            metadata={"data": data, **kwargs.get("metadata", {})}
        )

    def send_templated(
        self,
        channel: ChannelType,
        recipient: str,
        template_name: str,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """Send a templated message."""
        body = self.templates.render(template_name, context)

        # Check for HTML templates
        html_body = None
        if "html" in template_name or "_email" in template_name:
            html_body = body
            body = self.templates.render("simple_text", context)

        return self.send(
            channel=channel,
            recipient=recipient,
            body=body,
            html_body=html_body,
            **kwargs
        )

    def get_delivery_status(self, message_id: str) -> Optional[DeliveryResult]:
        """Get delivery status for a message."""
        for result in reversed(self._delivery_log):
            if result.message_id == message_id:
                return result
        return None

    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics."""
        total = len(self._delivery_log)
        delivered = sum(1 for r in self._delivery_log if r.status == DeliveryStatus.DELIVERED)
        failed = sum(1 for r in self._delivery_log if r.status == DeliveryStatus.FAILED)

        by_channel = {}
        for result in self._delivery_log:
            channel = result.channel.value
            if channel not in by_channel:
                by_channel[channel] = {"total": 0, "delivered": 0, "failed": 0}
            by_channel[channel]["total"] += 1
            if result.status == DeliveryStatus.DELIVERED:
                by_channel[channel]["delivered"] += 1
            elif result.status == DeliveryStatus.FAILED:
                by_channel[channel]["failed"] += 1

        return {
            "total": total,
            "delivered": delivered,
            "failed": failed,
            "delivery_rate": delivered / total if total > 0 else 0,
            "queue_size": self.queue.size(),
            "by_channel": by_channel
        }


# =============================================================================
# CONVENIENCE INSTANCE
# =============================================================================

comms_engine = CommunicationsEngine()
