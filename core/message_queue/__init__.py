"""
BAEL Message Queue Engine
=========================

RabbitMQ-like message queue with:
- Topics and exchanges
- Dead letter queues
- Priority queues
- Acknowledgments
- Consumer groups

"Messages flow like rivers of thought." — Ba'el
"""

from .message_queue import (
    # Enums
    ExchangeType,
    DeliveryMode,
    MessageStatus,
    AckMode,

    # Data structures
    Message,
    Queue,
    Exchange,
    Binding,
    Consumer,
    QueueConfig,
    MessageQueueConfig,

    # Classes
    MessageQueueEngine,
    QueueManager,
    ExchangeManager,
    MessageBroker,
    DeadLetterQueue,

    # Instance
    message_queue,
)

__all__ = [
    # Enums
    'ExchangeType',
    'DeliveryMode',
    'MessageStatus',
    'AckMode',

    # Data structures
    'Message',
    'Queue',
    'Exchange',
    'Binding',
    'Consumer',
    'QueueConfig',
    'MessageQueueConfig',

    # Classes
    'MessageQueueEngine',
    'QueueManager',
    'ExchangeManager',
    'MessageBroker',
    'DeadLetterQueue',

    # Instance
    'message_queue',
]
