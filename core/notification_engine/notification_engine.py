"""
BAEL Notification Engine
=========================

Multi-channel notification system with:
- Email, SMS, Push, Webhook, Slack
- Template rendering with variables
- Priority queuing
- Delivery tracking
- Rate limiting
- Retry logic

"Ba'el's commands reach every corner of existence." — Ba'el
"""

import asyncio
import logging
import re
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import threading
import uuid
import aiohttp

logger = logging.getLogger("BAEL.Notification")


# ============================================================================
# ENUMS
# ============================================================================

class NotificationChannel(Enum):
    """Notification channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    """Notification priorities."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(Enum):
    """Notification status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryStatus(Enum):
    """Delivery attempt status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    BOUNCED = "bounced"
    REJECTED = "rejected"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class NotificationTemplate:
    """Notification template."""
    id: str
    name: str
    channel: NotificationChannel

    # Content
    subject: str = ""  # For email
    body: str = ""
    html_body: str = ""  # For email HTML

    # Variables
    variables: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Notification:
    """A notification to send."""
    id: str
    channel: NotificationChannel

    # Recipient
    recipient: str  # Email, phone, user_id, webhook URL

    # Content
    subject: str = ""
    body: str = ""
    html_body: str = ""

    # Data
    data: Dict[str, Any] = field(default_factory=dict)

    # Priority
    priority: NotificationPriority = NotificationPriority.NORMAL

    # Status
    status: NotificationStatus = NotificationStatus.PENDING

    # Scheduling
    scheduled_at: Optional[datetime] = None

    # Tracking
    template_id: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'channel': self.channel.value,
            'recipient': self.recipient,
            'subject': self.subject,
            'status': self.status.value,
            'priority': self.priority.value,
            'attempts': self.attempts,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class NotificationResult:
    """Result of sending a notification."""
    notification_id: str
    status: DeliveryStatus
    channel: NotificationChannel

    # Details
    message: str = ""
    provider_response: Dict[str, Any] = field(default_factory=dict)

    # Timing
    sent_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'notification_id': self.notification_id,
            'status': self.status.value,
            'channel': self.channel.value,
            'message': self.message,
            'sent_at': self.sent_at.isoformat()
        }


@dataclass
class ChannelConfig:
    """Configuration for a notification channel."""
    channel: NotificationChannel
    enabled: bool = True

    # Rate limiting
    rate_limit: int = 100  # per minute

    # Retry
    retry_attempts: int = 3
    retry_delay_seconds: int = 60

    # Provider settings
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Notification engine configuration."""
    # Default priority
    default_priority: NotificationPriority = NotificationPriority.NORMAL

    # Queue settings
    queue_size: int = 10000
    batch_size: int = 50

    # Worker settings
    worker_count: int = 4

    # History
    retain_history_days: int = 30


# ============================================================================
# TEMPLATE RENDERER
# ============================================================================

class TemplateRenderer:
    """
    Renders notification templates with variables.
    """

    def __init__(self):
        """Initialize template renderer."""
        self._templates: Dict[str, NotificationTemplate] = {}

    def register(self, template: NotificationTemplate) -> None:
        """Register a template."""
        self._templates[template.id] = template

    def get(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get a template."""
        return self._templates.get(template_id)

    def render(
        self,
        template: NotificationTemplate,
        variables: Dict[str, Any]
    ) -> Tuple[str, str, str]:
        """Render a template with variables."""
        subject = self._render_string(template.subject, variables)
        body = self._render_string(template.body, variables)
        html_body = self._render_string(template.html_body, variables)

        return subject, body, html_body

    def _render_string(self, text: str, variables: Dict[str, Any]) -> str:
        """Render a string with variables."""
        if not text:
            return ""

        # Replace {{variable}} patterns
        def replace_var(match):
            var_name = match.group(1).strip()
            value = variables.get(var_name, match.group(0))
            return str(value)

        return re.sub(r'\{\{(\s*\w+\s*)\}\}', replace_var, text)


# ============================================================================
# CHANNEL PROVIDERS
# ============================================================================

class ChannelProvider(ABC):
    """Base class for notification channel providers."""

    def __init__(self, config: ChannelConfig):
        """Initialize provider."""
        self.config = config

    @abstractmethod
    async def send(self, notification: Notification) -> NotificationResult:
        """Send a notification."""
        pass

    @abstractmethod
    def validate(self, notification: Notification) -> bool:
        """Validate notification data."""
        pass


class EmailProvider(ChannelProvider):
    """Email notification provider."""

    async def send(self, notification: Notification) -> NotificationResult:
        """Send email notification."""
        try:
            settings = self.config.settings

            smtp_server = settings.get('smtp_server', 'localhost')
            smtp_port = settings.get('smtp_port', 587)
            smtp_user = settings.get('smtp_user', '')
            smtp_password = settings.get('smtp_password', '')
            from_email = settings.get('from_email', 'noreply@bael.ai')
            use_tls = settings.get('use_tls', True)

            # Create message
            if notification.html_body:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(notification.body, 'plain'))
                msg.attach(MIMEText(notification.html_body, 'html'))
            else:
                msg = MIMEText(notification.body, 'plain')

            msg['Subject'] = notification.subject
            msg['From'] = from_email
            msg['To'] = notification.recipient

            # Send
            # In production, use aiosmtplib for async
            # This is a simplified synchronous version
            context = ssl.create_default_context() if use_tls else None

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls(context=context)
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)

            return NotificationResult(
                notification_id=notification.id,
                status=DeliveryStatus.SUCCESS,
                channel=NotificationChannel.EMAIL,
                message="Email sent successfully"
            )

        except Exception as e:
            return NotificationResult(
                notification_id=notification.id,
                status=DeliveryStatus.FAILURE,
                channel=NotificationChannel.EMAIL,
                message=str(e)
            )

    def validate(self, notification: Notification) -> bool:
        """Validate email notification."""
        # Simple email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, notification.recipient))


class SMSProvider(ChannelProvider):
    """SMS notification provider."""

    async def send(self, notification: Notification) -> NotificationResult:
        """Send SMS notification."""
        try:
            settings = self.config.settings

            api_url = settings.get('api_url', '')
            api_key = settings.get('api_key', '')
            from_number = settings.get('from_number', '')

            if not api_url:
                # Simulate SMS sending
                logger.info(f"SMS to {notification.recipient}: {notification.body}")
                return NotificationResult(
                    notification_id=notification.id,
                    status=DeliveryStatus.SUCCESS,
                    channel=NotificationChannel.SMS,
                    message="SMS simulated (no provider configured)"
                )

            # Send via API
            async with aiohttp.ClientSession() as session:
                payload = {
                    'to': notification.recipient,
                    'from': from_number,
                    'body': notification.body
                }
                headers = {'Authorization': f'Bearer {api_key}'}

                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return NotificationResult(
                            notification_id=notification.id,
                            status=DeliveryStatus.SUCCESS,
                            channel=NotificationChannel.SMS,
                            message="SMS sent"
                        )
                    else:
                        return NotificationResult(
                            notification_id=notification.id,
                            status=DeliveryStatus.FAILURE,
                            channel=NotificationChannel.SMS,
                            message=f"API error: {resp.status}"
                        )

        except Exception as e:
            return NotificationResult(
                notification_id=notification.id,
                status=DeliveryStatus.FAILURE,
                channel=NotificationChannel.SMS,
                message=str(e)
            )

    def validate(self, notification: Notification) -> bool:
        """Validate SMS notification."""
        # Simple phone number validation
        phone_pattern = r'^\+?[1-9]\d{6,14}$'
        return bool(re.match(phone_pattern, notification.recipient.replace(' ', '')))


class PushProvider(ChannelProvider):
    """Push notification provider."""

    async def send(self, notification: Notification) -> NotificationResult:
        """Send push notification."""
        try:
            settings = self.config.settings

            fcm_api_url = settings.get('fcm_api_url', 'https://fcm.googleapis.com/fcm/send')
            fcm_key = settings.get('fcm_key', '')

            if not fcm_key:
                # Simulate push
                logger.info(f"Push to {notification.recipient}: {notification.body}")
                return NotificationResult(
                    notification_id=notification.id,
                    status=DeliveryStatus.SUCCESS,
                    channel=NotificationChannel.PUSH,
                    message="Push simulated (no provider configured)"
                )

            # Send via FCM
            async with aiohttp.ClientSession() as session:
                payload = {
                    'to': notification.recipient,
                    'notification': {
                        'title': notification.subject,
                        'body': notification.body
                    },
                    'data': notification.data
                }
                headers = {
                    'Authorization': f'key={fcm_key}',
                    'Content-Type': 'application/json'
                }

                async with session.post(fcm_api_url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return NotificationResult(
                            notification_id=notification.id,
                            status=DeliveryStatus.SUCCESS,
                            channel=NotificationChannel.PUSH,
                            message="Push sent"
                        )
                    else:
                        return NotificationResult(
                            notification_id=notification.id,
                            status=DeliveryStatus.FAILURE,
                            channel=NotificationChannel.PUSH,
                            message=f"FCM error: {resp.status}"
                        )

        except Exception as e:
            return NotificationResult(
                notification_id=notification.id,
                status=DeliveryStatus.FAILURE,
                channel=NotificationChannel.PUSH,
                message=str(e)
            )

    def validate(self, notification: Notification) -> bool:
        """Validate push notification."""
        return bool(notification.recipient)


class WebhookProvider(ChannelProvider):
    """Webhook notification provider."""

    async def send(self, notification: Notification) -> NotificationResult:
        """Send webhook notification."""
        try:
            settings = self.config.settings

            # notification.recipient is the webhook URL
            url = notification.recipient

            payload = {
                'id': notification.id,
                'subject': notification.subject,
                'body': notification.body,
                'data': notification.data,
                'timestamp': datetime.now().isoformat()
            }

            headers = {'Content-Type': 'application/json'}

            # Add custom headers
            if 'headers' in settings:
                headers.update(settings['headers'])

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status < 400:
                        return NotificationResult(
                            notification_id=notification.id,
                            status=DeliveryStatus.SUCCESS,
                            channel=NotificationChannel.WEBHOOK,
                            message=f"Webhook delivered: {resp.status}"
                        )
                    else:
                        return NotificationResult(
                            notification_id=notification.id,
                            status=DeliveryStatus.FAILURE,
                            channel=NotificationChannel.WEBHOOK,
                            message=f"Webhook error: {resp.status}"
                        )

        except Exception as e:
            return NotificationResult(
                notification_id=notification.id,
                status=DeliveryStatus.FAILURE,
                channel=NotificationChannel.WEBHOOK,
                message=str(e)
            )

    def validate(self, notification: Notification) -> bool:
        """Validate webhook notification."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, notification.recipient))


class SlackProvider(ChannelProvider):
    """Slack notification provider."""

    async def send(self, notification: Notification) -> NotificationResult:
        """Send Slack notification."""
        try:
            settings = self.config.settings

            # notification.recipient is channel or webhook URL
            webhook_url = notification.recipient

            if not webhook_url.startswith('http'):
                # Use Slack API
                bot_token = settings.get('bot_token', '')
                api_url = 'https://slack.com/api/chat.postMessage'

                payload = {
                    'channel': notification.recipient,
                    'text': notification.body
                }

                if notification.data.get('blocks'):
                    payload['blocks'] = notification.data['blocks']

                headers = {
                    'Authorization': f'Bearer {bot_token}',
                    'Content-Type': 'application/json'
                }
            else:
                # Use webhook
                api_url = webhook_url
                payload = {'text': notification.body}

                if notification.data.get('blocks'):
                    payload['blocks'] = notification.data['blocks']

                headers = {'Content-Type': 'application/json'}

            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return NotificationResult(
                            notification_id=notification.id,
                            status=DeliveryStatus.SUCCESS,
                            channel=NotificationChannel.SLACK,
                            message="Slack message sent"
                        )
                    else:
                        return NotificationResult(
                            notification_id=notification.id,
                            status=DeliveryStatus.FAILURE,
                            channel=NotificationChannel.SLACK,
                            message=f"Slack error: {resp.status}"
                        )

        except Exception as e:
            return NotificationResult(
                notification_id=notification.id,
                status=DeliveryStatus.FAILURE,
                channel=NotificationChannel.SLACK,
                message=str(e)
            )

    def validate(self, notification: Notification) -> bool:
        """Validate Slack notification."""
        return bool(notification.recipient)


# ============================================================================
# NOTIFICATION QUEUE
# ============================================================================

class NotificationQueue:
    """
    Priority queue for notifications.
    """

    def __init__(self, max_size: int = 10000):
        """Initialize notification queue."""
        self._max_size = max_size

        # Priority queues
        self._queues: Dict[NotificationPriority, deque] = {
            NotificationPriority.URGENT: deque(),
            NotificationPriority.HIGH: deque(),
            NotificationPriority.NORMAL: deque(),
            NotificationPriority.LOW: deque()
        }

        self._lock = threading.RLock()
        self._size = 0

    def enqueue(self, notification: Notification) -> bool:
        """Add notification to queue."""
        with self._lock:
            if self._size >= self._max_size:
                return False

            self._queues[notification.priority].append(notification)
            self._size += 1
            notification.status = NotificationStatus.QUEUED
            return True

    def dequeue(self) -> Optional[Notification]:
        """Get next notification from queue."""
        with self._lock:
            # Process by priority
            for priority in [
                NotificationPriority.URGENT,
                NotificationPriority.HIGH,
                NotificationPriority.NORMAL,
                NotificationPriority.LOW
            ]:
                if self._queues[priority]:
                    self._size -= 1
                    return self._queues[priority].popleft()

            return None

    def size(self) -> int:
        """Get queue size."""
        return self._size

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._size == 0

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        with self._lock:
            return {
                'total': self._size,
                'urgent': len(self._queues[NotificationPriority.URGENT]),
                'high': len(self._queues[NotificationPriority.HIGH]),
                'normal': len(self._queues[NotificationPriority.NORMAL]),
                'low': len(self._queues[NotificationPriority.LOW])
            }


# ============================================================================
# MAIN NOTIFICATION ENGINE
# ============================================================================

class NotificationEngine:
    """
    Main notification engine.

    Features:
    - Multi-channel delivery
    - Template rendering
    - Priority queuing
    - Rate limiting
    - Delivery tracking

    "Ba'el broadcasts across all channels." — Ba'el
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        """Initialize notification engine."""
        self.config = config or NotificationConfig()

        # Components
        self._queue = NotificationQueue(self.config.queue_size)
        self._templates = TemplateRenderer()

        # Providers
        self._providers: Dict[NotificationChannel, ChannelProvider] = {}

        # History
        self._history: Dict[str, Notification] = {}
        self._results: Dict[str, List[NotificationResult]] = defaultdict(list)

        # Rate limiting
        self._rate_counts: Dict[NotificationChannel, int] = defaultdict(int)
        self._rate_reset: datetime = datetime.now()

        # Worker control
        self._running = False
        self._workers: List[asyncio.Task] = []

        self._lock = threading.RLock()

        # Register default providers
        self._register_default_providers()

        logger.info("NotificationEngine initialized")

    def _register_default_providers(self) -> None:
        """Register default channel providers."""
        channels = [
            (NotificationChannel.EMAIL, EmailProvider),
            (NotificationChannel.SMS, SMSProvider),
            (NotificationChannel.PUSH, PushProvider),
            (NotificationChannel.WEBHOOK, WebhookProvider),
            (NotificationChannel.SLACK, SlackProvider)
        ]

        for channel, provider_class in channels:
            config = ChannelConfig(channel=channel)
            self._providers[channel] = provider_class(config)

    async def start(self) -> None:
        """Start the notification engine."""
        self._running = True

        # Start workers
        for i in range(self.config.worker_count):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)

        logger.info(f"NotificationEngine started with {self.config.worker_count} workers")

    async def stop(self) -> None:
        """Stop the notification engine."""
        self._running = False

        for task in self._workers:
            task.cancel()

        self._workers.clear()
        logger.info("NotificationEngine stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop for processing notifications."""
        while self._running:
            try:
                notification = self._queue.dequeue()

                if notification:
                    await self._process_notification(notification)
                else:
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

    async def _process_notification(self, notification: Notification) -> None:
        """Process a single notification."""
        channel = notification.channel
        provider = self._providers.get(channel)

        if not provider:
            notification.status = NotificationStatus.FAILED
            logger.error(f"No provider for channel: {channel}")
            return

        # Check rate limit
        if not self._check_rate_limit(channel):
            # Re-queue for later
            notification.attempts += 1
            if notification.attempts < notification.max_attempts:
                self._queue.enqueue(notification)
            else:
                notification.status = NotificationStatus.FAILED
            return

        # Validate
        if not provider.validate(notification):
            notification.status = NotificationStatus.FAILED
            logger.warning(f"Invalid notification: {notification.id}")
            return

        # Send
        notification.status = NotificationStatus.SENDING
        notification.attempts += 1

        result = await provider.send(notification)

        # Update status
        if result.status == DeliveryStatus.SUCCESS:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now()
        else:
            if notification.attempts < notification.max_attempts:
                # Retry
                notification.status = NotificationStatus.QUEUED
                self._queue.enqueue(notification)
            else:
                notification.status = NotificationStatus.FAILED

        # Record result
        with self._lock:
            self._results[notification.id].append(result)

    def _check_rate_limit(self, channel: NotificationChannel) -> bool:
        """Check rate limit for a channel."""
        with self._lock:
            now = datetime.now()

            # Reset counters every minute
            if (now - self._rate_reset).total_seconds() >= 60:
                self._rate_counts.clear()
                self._rate_reset = now

            provider = self._providers.get(channel)
            if not provider:
                return False

            limit = provider.config.rate_limit
            current = self._rate_counts[channel]

            if current >= limit:
                return False

            self._rate_counts[channel] += 1
            return True

    # ========================================================================
    # TEMPLATES
    # ========================================================================

    def register_template(self, template: NotificationTemplate) -> None:
        """Register a notification template."""
        self._templates.register(template)

    def create_template(
        self,
        name: str,
        channel: NotificationChannel,
        subject: str = "",
        body: str = "",
        html_body: str = ""
    ) -> NotificationTemplate:
        """Create and register a template."""
        template = NotificationTemplate(
            id=str(uuid.uuid4()),
            name=name,
            channel=channel,
            subject=subject,
            body=body,
            html_body=html_body
        )
        self._templates.register(template)
        return template

    # ========================================================================
    # SENDING
    # ========================================================================

    async def send(
        self,
        channel: NotificationChannel,
        recipient: str,
        subject: str = "",
        body: str = "",
        html_body: str = "",
        data: Optional[Dict[str, Any]] = None,
        priority: Optional[NotificationPriority] = None,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Send a notification."""
        # Render template if provided
        if template_id:
            template = self._templates.get(template_id)
            if template:
                subject, body, html_body = self._templates.render(
                    template,
                    variables or {}
                )

        # Create notification
        notification = Notification(
            id=str(uuid.uuid4()),
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            html_body=html_body,
            data=data or {},
            priority=priority or self.config.default_priority,
            template_id=template_id
        )

        # Store in history
        with self._lock:
            self._history[notification.id] = notification

        # Queue for delivery
        self._queue.enqueue(notification)

        return notification

    async def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        html_body: str = "",
        priority: Optional[NotificationPriority] = None
    ) -> Notification:
        """Send an email notification."""
        return await self.send(
            channel=NotificationChannel.EMAIL,
            recipient=recipient,
            subject=subject,
            body=body,
            html_body=html_body,
            priority=priority
        )

    async def send_sms(
        self,
        recipient: str,
        body: str,
        priority: Optional[NotificationPriority] = None
    ) -> Notification:
        """Send an SMS notification."""
        return await self.send(
            channel=NotificationChannel.SMS,
            recipient=recipient,
            body=body,
            priority=priority
        )

    async def send_push(
        self,
        recipient: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        priority: Optional[NotificationPriority] = None
    ) -> Notification:
        """Send a push notification."""
        return await self.send(
            channel=NotificationChannel.PUSH,
            recipient=recipient,
            subject=title,
            body=body,
            data=data,
            priority=priority
        )

    async def send_webhook(
        self,
        url: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        priority: Optional[NotificationPriority] = None
    ) -> Notification:
        """Send a webhook notification."""
        return await self.send(
            channel=NotificationChannel.WEBHOOK,
            recipient=url,
            body=body,
            data=data,
            priority=priority
        )

    async def send_slack(
        self,
        channel_or_webhook: str,
        message: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        priority: Optional[NotificationPriority] = None
    ) -> Notification:
        """Send a Slack notification."""
        return await self.send(
            channel=NotificationChannel.SLACK,
            recipient=channel_or_webhook,
            body=message,
            data={'blocks': blocks} if blocks else {},
            priority=priority
        )

    # ========================================================================
    # TRACKING
    # ========================================================================

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        return self._history.get(notification_id)

    def get_results(self, notification_id: str) -> List[NotificationResult]:
        """Get delivery results for a notification."""
        return self._results.get(notification_id, [])

    def get_recent(
        self,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None
    ) -> List[Notification]:
        """Get recent notifications."""
        notifications = list(self._history.values())

        if channel:
            notifications = [n for n in notifications if n.channel == channel]

        if status:
            notifications = [n for n in notifications if n.status == status]

        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications[:limit]

    # ========================================================================
    # CONFIGURATION
    # ========================================================================

    def configure_channel(
        self,
        channel: NotificationChannel,
        settings: Dict[str, Any]
    ) -> None:
        """Configure a notification channel."""
        provider = self._providers.get(channel)
        if provider:
            provider.config.settings.update(settings)

    def enable_channel(self, channel: NotificationChannel) -> None:
        """Enable a notification channel."""
        provider = self._providers.get(channel)
        if provider:
            provider.config.enabled = True

    def disable_channel(self, channel: NotificationChannel) -> None:
        """Disable a notification channel."""
        provider = self._providers.get(channel)
        if provider:
            provider.config.enabled = False

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'running': self._running,
            'workers': len(self._workers),
            'queue': self._queue.get_stats(),
            'history_count': len(self._history),
            'channels': {
                channel.value: {
                    'enabled': provider.config.enabled,
                    'rate_count': self._rate_counts.get(channel, 0)
                }
                for channel, provider in self._providers.items()
            }
        }


# ============================================================================
# CONVENIENCE INSTANCE
# ============================================================================

notification_engine = NotificationEngine()
