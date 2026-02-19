"""
BAEL AG-UI Protocol Integration
================================

Implementation of the Agent-User Interaction (AG-UI) Protocol.
Enables real-time streaming communication between AI agents and frontend UIs.

Based on: https://github.com/ag-ui-protocol/ag-ui

Components:
- EventEmitter: Server-sent event streaming
- MessageTypes: Standard message type definitions
- AgentSession: Session management
- StateSync: Real-time state synchronization
- ToolExecution: Tool call streaming
"""

from .agent_session import AgentSession, SessionConfig, SessionState
from .event_emitter import EventEmitter, EventType, ServerSentEvent
from .message_types import (AgentMessage, StateUpdate, StreamChunk,
                            SystemMessage, ToolCall, ToolResult, UserMessage)
from .protocol_handler import AGUIProtocolHandler, ProtocolVersion
from .state_sync import StateChange, StateSync, SyncStrategy

__all__ = [
    # Event Emitter
    "EventEmitter",
    "ServerSentEvent",
    "EventType",
    # Message Types
    "AgentMessage",
    "UserMessage",
    "SystemMessage",
    "ToolCall",
    "ToolResult",
    "StreamChunk",
    "StateUpdate",
    # Session
    "AgentSession",
    "SessionState",
    "SessionConfig",
    # State Sync
    "StateSync",
    "SyncStrategy",
    "StateChange",
    # Protocol Handler
    "AGUIProtocolHandler",
    "ProtocolVersion",
]
