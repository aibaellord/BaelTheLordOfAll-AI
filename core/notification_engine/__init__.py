"""
BAEL Notification Engine
=========================

Multi-channel notifications with templates.

"Ba'el's voice reaches all realms." — Ba'el
"""

from core.notification_engine.notification_engine import (
    # Enums
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    DeliveryStatus,

    # Data structures
    NotificationTemplate,
    Notification,
    NotificationResult,
    ChannelConfig,
    NotificationConfig,

    # Classes
    NotificationEngine,
    ChannelProvider,
    EmailProvider,
    SMSProvider,
    PushProvider,
    WebhookProvider,
    SlackProvider,
    TemplateRenderer,
    NotificationQueue,

    # Instance
    notification_engine
)

__all__ = [
    # Enums
    'NotificationChannel',
    'NotificationPriority',
    'NotificationStatus',
    'DeliveryStatus',

    # Data structures
    'NotificationTemplate',
    'Notification',
    'NotificationResult',
    'ChannelConfig',
    'NotificationConfig',

    # Classes
    'NotificationEngine',
    'ChannelProvider',
    'EmailProvider',
    'SMSProvider',
    'PushProvider',
    'WebhookProvider',
    'SlackProvider',
    'TemplateRenderer',
    'NotificationQueue',

    # Instance
    'notification_engine'
]
