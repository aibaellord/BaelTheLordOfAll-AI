"""
BAEL Python SDK
Official Python client library for BAEL - The Lord of All AI Agents.
"""

__version__ = "1.0.0"

from .bael_sdk import (  # Client classes; Types; Exceptions; Convenience functions
    APIError, AuthenticationError, BAELClient, BAELError, BAELSyncClient,
    ChatResponse, HealthStatus, Message, OperatingMode, RateLimitError, Task,
    quick_chat, quick_chat_sync)

__all__ = [
    # Client classes
    'BAELClient',
    'BAELSyncClient',

    # Types
    'Message',
    'ChatResponse',
    'Task',
    'HealthStatus',
    'OperatingMode',

    # Exceptions
    'BAELError',
    'APIError',
    'AuthenticationError',
    'RateLimitError',

    # Convenience functions
    'quick_chat',
    'quick_chat_sync'
]
