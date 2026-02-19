"""
BAEL Universal Messaging Hub
=============================

Multi-platform messaging integration for BAEL.
Enables communication across all major platforms.

Features:
- Telegram integration
- Discord integration
- Slack integration
- Webhook management
- Unified notification routing
"""

from .discord_bot import DiscordBot, DiscordConfig, DiscordMessage
from .notification_router import (Notification, NotificationChannel,
                                  NotificationRouter, RoutingRule)
from .slack_bot import SlackBot, SlackConfig, SlackMessage
from .telegram_bot import TelegramBot, TelegramConfig, TelegramMessage
from .webhook_manager import (Webhook, WebhookConfig, WebhookEvent,
                              WebhookManager)

__all__ = [
    # Telegram
    "TelegramBot",
    "TelegramMessage",
    "TelegramConfig",
    # Discord
    "DiscordBot",
    "DiscordMessage",
    "DiscordConfig",
    # Slack
    "SlackBot",
    "SlackMessage",
    "SlackConfig",
    # Webhooks
    "WebhookManager",
    "Webhook",
    "WebhookEvent",
    "WebhookConfig",
    # Router
    "NotificationRouter",
    "Notification",
    "NotificationChannel",
    "RoutingRule",
]
