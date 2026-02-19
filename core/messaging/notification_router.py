"""
BAEL Notification Router
=========================

Route notifications across multiple channels.
Unified notification system for BAEL.

Features:
- Multi-channel routing
- Priority-based delivery
- Template support
- Scheduling
- Delivery tracking
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification channels."""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationPriority(Enum):
    """Notification priority."""
    CRITICAL = 5
    HIGH = 4
    NORMAL = 3
    LOW = 2
    MINIMAL = 1


class NotificationStatus(Enum):
    """Notification status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SCHEDULED = "scheduled"


@dataclass
class NotificationTemplate:
    """Notification template."""
    id: str
    name: str

    # Content templates per channel
    templates: Dict[NotificationChannel, str] = field(default_factory=dict)

    # Default
    default_template: str = ""

    def render(
        self,
        channel: NotificationChannel,
        variables: Dict[str, Any],
    ) -> str:
        """Render template for channel."""
        template = self.templates.get(channel, self.default_template)

        # Simple variable substitution
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))

        return template


@dataclass
class Notification:
    """A notification."""
    id: str
    title: str
    message: str

    # Routing
    channels: List[NotificationChannel] = field(default_factory=list)
    recipients: Dict[NotificationChannel, List[str]] = field(default_factory=dict)

    # Priority
    priority: NotificationPriority = NotificationPriority.NORMAL

    # Status
    status: NotificationStatus = NotificationStatus.PENDING

    # Delivery
    delivery_results: Dict[NotificationChannel, bool] = field(default_factory=dict)

    # Scheduling
    scheduled_for: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None

    # Data
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingRule:
    """Notification routing rule."""
    id: str
    name: str

    # Conditions
    priority_min: NotificationPriority = NotificationPriority.MINIMAL
    keywords: List[str] = field(default_factory=list)

    # Routing
    channels: List[NotificationChannel] = field(default_factory=list)
    recipients: Dict[NotificationChannel, List[str]] = field(default_factory=dict)

    # Active
    enabled: bool = True


class NotificationRouter:
    """
    Notification routing for BAEL.

    Routes notifications to multiple channels.
    """

    def __init__(self):
        # Channel handlers
        self._handlers: Dict[NotificationChannel, Callable] = {}

        # Templates
        self._templates: Dict[str, NotificationTemplate] = {}

        # Routing rules
        self._rules: List[RoutingRule] = []

        # Queue
        self._queue: List[Notification] = []

        # History
        self._history: List[Notification] = []

        # Stats
        self.stats = {
            "notifications_sent": 0,
            "notifications_failed": 0,
            "by_channel": {},
        }

        # Register default templates
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """Register default templates."""
        self.add_template(NotificationTemplate(
            id="alert",
            name="Alert Template",
            default_template="🚨 {{title}}\n\n{{message}}",
            templates={
                NotificationChannel.TELEGRAM: "🚨 <b>{{title}}</b>\n\n{{message}}",
                NotificationChannel.DISCORD: "**🚨 {{title}}**\n\n{{message}}",
                NotificationChannel.SLACK: "*🚨 {{title}}*\n\n{{message}}",
            },
        ))

        self.add_template(NotificationTemplate(
            id="info",
            name="Info Template",
            default_template="ℹ️ {{title}}\n\n{{message}}",
            templates={
                NotificationChannel.TELEGRAM: "ℹ️ <b>{{title}}</b>\n\n{{message}}",
                NotificationChannel.DISCORD: "**ℹ️ {{title}}**\n\n{{message}}",
                NotificationChannel.SLACK: "*ℹ️ {{title}}*\n\n{{message}}",
            },
        ))

        self.add_template(NotificationTemplate(
            id="success",
            name="Success Template",
            default_template="✅ {{title}}\n\n{{message}}",
        ))

    def register_handler(
        self,
        channel: NotificationChannel,
        handler: Callable,
    ) -> None:
        """Register channel handler."""
        self._handlers[channel] = handler
        logger.info(f"Registered handler for {channel.value}")

    def add_template(self, template: NotificationTemplate) -> None:
        """Add notification template."""
        self._templates[template.id] = template

    def add_rule(self, rule: RoutingRule) -> None:
        """Add routing rule."""
        self._rules.append(rule)

    async def send(
        self,
        title: str,
        message: str,
        channels: Optional[List[NotificationChannel]] = None,
        recipients: Optional[Dict[NotificationChannel, List[str]]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        schedule_for: Optional[datetime] = None,
    ) -> Notification:
        """
        Send a notification.

        Args:
            title: Notification title
            message: Notification message
            channels: Target channels
            recipients: Channel-specific recipients
            priority: Priority level
            template_id: Template to use
            data: Additional data
            schedule_for: Schedule delivery

        Returns:
            Notification
        """
        notif_id = hashlib.md5(
            f"{title}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Apply routing rules
        if not channels:
            channels, recipients = self._apply_rules(title, message, priority)

        notification = Notification(
            id=notif_id,
            title=title,
            message=message,
            channels=channels or [NotificationChannel.WEBHOOK],
            recipients=recipients or {},
            priority=priority,
            data=data or {},
            scheduled_for=schedule_for,
        )

        # Apply template
        if template_id and template_id in self._templates:
            template = self._templates[template_id]
            variables = {
                "title": title,
                "message": message,
                **(data or {}),
            }

            for channel in notification.channels:
                rendered = template.render(channel, variables)
                # Store rendered message (simplified)
                notification.data[f"rendered_{channel.value}"] = rendered

        # Schedule or send immediately
        if schedule_for:
            notification.status = NotificationStatus.SCHEDULED
            self._queue.append(notification)
            logger.info(f"Scheduled notification {notif_id} for {schedule_for}")
        else:
            await self._deliver(notification)

        self._history.append(notification)

        return notification

    def _apply_rules(
        self,
        title: str,
        message: str,
        priority: NotificationPriority,
    ) -> tuple:
        """Apply routing rules."""
        channels = []
        recipients: Dict[NotificationChannel, List[str]] = {}

        content = f"{title} {message}".lower()

        for rule in self._rules:
            if not rule.enabled:
                continue

            # Check priority
            if priority.value < rule.priority_min.value:
                continue

            # Check keywords
            if rule.keywords:
                if not any(kw.lower() in content for kw in rule.keywords):
                    continue

            # Apply routing
            channels.extend(rule.channels)
            for channel, recips in rule.recipients.items():
                if channel not in recipients:
                    recipients[channel] = []
                recipients[channel].extend(recips)

        return list(set(channels)), recipients

    async def _deliver(self, notification: Notification) -> None:
        """Deliver notification to all channels."""
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now()

        for channel in notification.channels:
            success = await self._deliver_to_channel(notification, channel)
            notification.delivery_results[channel] = success

            # Update stats
            if channel.value not in self.stats["by_channel"]:
                self.stats["by_channel"][channel.value] = {"sent": 0, "failed": 0}

            if success:
                self.stats["by_channel"][channel.value]["sent"] += 1
            else:
                self.stats["by_channel"][channel.value]["failed"] += 1

        # Update overall status
        if all(notification.delivery_results.values()):
            notification.status = NotificationStatus.DELIVERED
            self.stats["notifications_sent"] += 1
        else:
            notification.status = NotificationStatus.FAILED
            self.stats["notifications_failed"] += 1

    async def _deliver_to_channel(
        self,
        notification: Notification,
        channel: NotificationChannel,
    ) -> bool:
        """Deliver to specific channel."""
        if channel in self._handlers:
            try:
                handler = self._handlers[channel]
                recipients = notification.recipients.get(channel, [])

                # Get rendered message if available
                message = notification.data.get(
                    f"rendered_{channel.value}",
                    f"{notification.title}\n\n{notification.message}",
                )

                await handler(message, recipients)

                logger.info(
                    f"[NOTIFY] Delivered to {channel.value}: "
                    f"{notification.title[:30]}"
                )

                return True

            except Exception as e:
                logger.error(f"Delivery to {channel.value} failed: {e}")
                return False

        # Default: log the notification
        logger.info(
            f"[NOTIFY] {channel.value}: {notification.title} - "
            f"{notification.message[:50]}"
        )
        return True

    async def process_queue(self) -> int:
        """Process scheduled notifications."""
        now = datetime.now()
        processed = 0

        for notification in self._queue[:]:
            if notification.scheduled_for and notification.scheduled_for <= now:
                await self._deliver(notification)
                self._queue.remove(notification)
                processed += 1

        return processed

    def get_history(
        self,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
    ) -> List[Notification]:
        """Get notification history."""
        history = self._history

        if channel:
            history = [n for n in history if channel in n.channels]

        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            **self.stats,
            "queue_size": len(self._queue),
            "templates": len(self._templates),
            "rules": len(self._rules),
        }


def demo():
    """Demonstrate notification router."""
    import asyncio

    print("=" * 60)
    print("BAEL Notification Router Demo")
    print("=" * 60)

    router = NotificationRouter()

    # Register handlers (simulated)
    async def telegram_handler(message: str, recipients: List[str]):
        print(f"  [Telegram] {message[:50]}... -> {recipients}")

    async def discord_handler(message: str, recipients: List[str]):
        print(f"  [Discord] {message[:50]}... -> {recipients}")

    router.register_handler(NotificationChannel.TELEGRAM, telegram_handler)
    router.register_handler(NotificationChannel.DISCORD, discord_handler)

    # Add routing rule
    router.add_rule(RoutingRule(
        id="alerts",
        name="Alert Routing",
        priority_min=NotificationPriority.HIGH,
        keywords=["alert", "error", "critical"],
        channels=[NotificationChannel.TELEGRAM, NotificationChannel.DISCORD],
        recipients={
            NotificationChannel.TELEGRAM: ["@admin"],
            NotificationChannel.DISCORD: ["#alerts"],
        },
    ))

    # Send notifications
    async def send_notifications():
        # Regular notification
        print("\nSending regular notification:")
        notif1 = await router.send(
            title="Task Completed",
            message="Your task has been completed successfully.",
            channels=[NotificationChannel.TELEGRAM],
            template_id="success",
        )

        print(f"  Status: {notif1.status.value}")

        # High priority alert (triggers rule)
        print("\nSending high priority alert:")
        notif2 = await router.send(
            title="Critical Alert",
            message="System error detected! Immediate attention required.",
            priority=NotificationPriority.CRITICAL,
            template_id="alert",
        )

        print(f"  Status: {notif2.status.value}")
        print(f"  Channels: {[c.value for c in notif2.channels]}")

        # Scheduled notification
        print("\nScheduling notification:")
        notif3 = await router.send(
            title="Reminder",
            message="Check your tasks",
            channels=[NotificationChannel.TELEGRAM],
            schedule_for=datetime.now() + timedelta(hours=1),
        )

        print(f"  Status: {notif3.status.value}")
        print(f"  Scheduled for: {notif3.scheduled_for}")

    asyncio.run(send_notifications())

    print(f"\nHistory: {len(router.get_history())} notifications")
    print(f"Stats: {router.get_stats()}")


if __name__ == "__main__":
    demo()
