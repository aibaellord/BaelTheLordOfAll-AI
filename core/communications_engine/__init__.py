"""
BAEL Communications Engine
==========================

Multi-channel messaging and notification system.
"""

from .communications import (
    # Enums
    ChannelType,
    MessagePriority,
    DeliveryStatus,
    NotificationType,

    # Dataclasses
    Message,
    Notification,
    Channel,
    DeliveryResult,
    CommunicationConfig,

    # Classes
    CommunicationsEngine,
    MessageQueue,
    NotificationManager,
    ChannelRegistry,
    TemplateEngine,

    # Instance
    comms_engine
)

__all__ = [
    "ChannelType",
    "MessagePriority",
    "DeliveryStatus",
    "NotificationType",
    "Message",
    "Notification",
    "Channel",
    "DeliveryResult",
    "CommunicationConfig",
    "CommunicationsEngine",
    "MessageQueue",
    "NotificationManager",
    "ChannelRegistry",
    "TemplateEngine",
    "comms_engine"
]
