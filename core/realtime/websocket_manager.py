#!/usr/bin/env python3
"""
BAEL - WebSocket Manager
Real-time streaming and live updates via WebSocket.

Enables:
- Token-by-token streaming of LLM responses
- Live council deliberation updates
- Task execution progress
- Memory events
- Multi-terminal output streaming
"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.WebSocket")


class MessageType(Enum):
    """WebSocket message types."""
    # Connection
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # Chat streaming
    CHAT_START = "chat_start"
    CHAT_TOKEN = "chat_token"
    CHAT_COMPLETE = "chat_complete"
    CHAT_ERROR = "chat_error"

    # Council
    COUNCIL_START = "council_start"
    COUNCIL_OPINION = "council_opinion"
    COUNCIL_VOTE = "council_vote"
    COUNCIL_COMPLETE = "council_complete"

    # Tasks/Agents
    TASK_START = "task_start"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_ERROR = "task_error"

    # Memory
    MEMORY_ADDED = "memory_added"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_CONSOLIDATED = "memory_consolidated"

    # Terminal
    TERMINAL_OUTPUT = "terminal_output"
    TERMINAL_COMMAND = "terminal_command"

    # System
    SYSTEM_STATUS = "system_status"
    SYSTEM_NOTIFICATION = "system_notification"


@dataclass
class WebSocketMessage:
    """A message to/from WebSocket."""
    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    timestamp: float = 0.0
    channel: str = "default"

    def __post_init__(self):
        if not self.id:
            self.id = f"msg-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "channel": self.channel
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WebSocketMessage":
        return cls(
            id=d.get("id", ""),
            type=MessageType(d.get("type", "error")),
            data=d.get("data", {}),
            timestamp=d.get("timestamp", 0.0),
            channel=d.get("channel", "default")
        )

    @classmethod
    def from_json(cls, s: str) -> "WebSocketMessage":
        return cls.from_dict(json.loads(s))


@dataclass
class WebSocketClient:
    """Represents a connected WebSocket client."""
    id: str
    websocket: Any  # The actual WebSocket connection
    subscriptions: Set[str] = field(default_factory=set)  # Channels subscribed to
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.
    """

    def __init__(self):
        self.clients: Dict[str, WebSocketClient] = {}
        self.channels: Dict[str, Set[str]] = {}  # channel -> client_ids
        self._lock = asyncio.Lock()

        # Message handlers
        self.handlers: Dict[MessageType, List[Callable]] = {}

        # Stats
        self.messages_sent = 0
        self.messages_received = 0

    async def register(self, websocket: Any, client_id: Optional[str] = None) -> str:
        """Register a new WebSocket connection."""
        async with self._lock:
            cid = client_id or f"client-{uuid.uuid4().hex[:8]}"
            client = WebSocketClient(id=cid, websocket=websocket)
            self.clients[cid] = client

            # Subscribe to default channel
            await self._subscribe_internal(cid, "default")

            logger.info(f"WebSocket client registered: {cid}")

            # Send welcome message
            await self.send_to_client(cid, WebSocketMessage(
                type=MessageType.CONNECT,
                data={"client_id": cid, "message": "Connected to BAEL"}
            ))

            return cid

    async def unregister(self, client_id: str):
        """Unregister a WebSocket connection."""
        async with self._lock:
            if client_id in self.clients:
                # Remove from all channels
                for channel, clients in self.channels.items():
                    clients.discard(client_id)

                del self.clients[client_id]
                logger.info(f"WebSocket client unregistered: {client_id}")

    async def _subscribe_internal(self, client_id: str, channel: str):
        """Subscribe client to channel (internal, lock held)."""
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(client_id)
        self.clients[client_id].subscriptions.add(channel)

    async def subscribe(self, client_id: str, channel: str):
        """Subscribe client to a channel."""
        async with self._lock:
            if client_id in self.clients:
                await self._subscribe_internal(client_id, channel)
                logger.debug(f"Client {client_id} subscribed to {channel}")

    async def unsubscribe(self, client_id: str, channel: str):
        """Unsubscribe client from a channel."""
        async with self._lock:
            if channel in self.channels:
                self.channels[channel].discard(client_id)
            if client_id in self.clients:
                self.clients[client_id].subscriptions.discard(channel)

    async def send_to_client(self, client_id: str, message: WebSocketMessage) -> bool:
        """Send a message to a specific client."""
        client = self.clients.get(client_id)
        if not client:
            return False

        try:
            await client.websocket.send_text(message.to_json())
            self.messages_sent += 1
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client {client_id}: {e}")
            # Client may be disconnected
            await self.unregister(client_id)
            return False

    async def broadcast(self, message: WebSocketMessage, channel: str = "default"):
        """Broadcast a message to all clients in a channel."""
        message.channel = channel
        client_ids = self.channels.get(channel, set()).copy()

        for client_id in client_ids:
            await self.send_to_client(client_id, message)

    async def broadcast_all(self, message: WebSocketMessage):
        """Broadcast to all connected clients."""
        for client_id in list(self.clients.keys()):
            await self.send_to_client(client_id, message)

    def on_message(self, message_type: MessageType, handler: Callable):
        """Register a handler for a message type."""
        if message_type not in self.handlers:
            self.handlers[message_type] = []
        self.handlers[message_type].append(handler)

    async def handle_message(self, client_id: str, raw_message: str):
        """Handle an incoming message from a client."""
        self.messages_received += 1

        try:
            message = WebSocketMessage.from_json(raw_message)

            # Built-in handlers
            if message.type == MessageType.PING:
                await self.send_to_client(client_id, WebSocketMessage(
                    type=MessageType.PONG,
                    data={"timestamp": time.time()}
                ))
                if client_id in self.clients:
                    self.clients[client_id].last_ping = time.time()
                return

            # Custom handlers
            handlers = self.handlers.get(message.type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(client_id, message)
                    else:
                        handler(client_id, message)
                except Exception as e:
                    logger.error(f"Handler error: {e}")

        except Exception as e:
            logger.error(f"Failed to handle message: {e}")
            await self.send_to_client(client_id, WebSocketMessage(
                type=MessageType.ERROR,
                data={"error": str(e)}
            ))

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        return {
            "clients_connected": len(self.clients),
            "channels": list(self.channels.keys()),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received
        }


# =============================================================================
# STREAMING HELPERS
# =============================================================================

class StreamingChat:
    """Helper for streaming chat responses token by token."""

    def __init__(self, ws_manager: WebSocketManager, channel: str = "chat"):
        self.ws = ws_manager
        self.channel = channel

    async def start_stream(self, request_id: str, model: str, prompt: str):
        """Signal start of streaming response."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.CHAT_START,
            data={
                "request_id": request_id,
                "model": model,
                "prompt_preview": prompt[:100]
            }
        ), channel=self.channel)

    async def stream_token(self, request_id: str, token: str, index: int = 0):
        """Stream a single token."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.CHAT_TOKEN,
            data={
                "request_id": request_id,
                "token": token,
                "index": index
            }
        ), channel=self.channel)

    async def complete_stream(
        self,
        request_id: str,
        full_response: str,
        tokens_used: int = 0,
        duration_ms: float = 0.0
    ):
        """Signal completion of streaming response."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.CHAT_COMPLETE,
            data={
                "request_id": request_id,
                "response": full_response,
                "tokens_used": tokens_used,
                "duration_ms": duration_ms
            }
        ), channel=self.channel)

    async def error(self, request_id: str, error: str):
        """Signal an error during streaming."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.CHAT_ERROR,
            data={
                "request_id": request_id,
                "error": error
            }
        ), channel=self.channel)


class StreamingCouncil:
    """Helper for streaming council deliberation updates."""

    def __init__(self, ws_manager: WebSocketManager, channel: str = "council"):
        self.ws = ws_manager
        self.channel = channel

    async def start_deliberation(self, deliberation_id: str, topic: str, members: List[str]):
        """Signal start of council deliberation."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.COUNCIL_START,
            data={
                "deliberation_id": deliberation_id,
                "topic": topic,
                "members": members
            }
        ), channel=self.channel)

    async def member_opinion(
        self,
        deliberation_id: str,
        member: str,
        opinion: str,
        phase: str = "initial"
    ):
        """Stream a council member's opinion."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.COUNCIL_OPINION,
            data={
                "deliberation_id": deliberation_id,
                "member": member,
                "opinion": opinion,
                "phase": phase
            }
        ), channel=self.channel)

    async def member_vote(
        self,
        deliberation_id: str,
        member: str,
        vote: str,
        reasoning: str
    ):
        """Stream a council member's vote."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.COUNCIL_VOTE,
            data={
                "deliberation_id": deliberation_id,
                "member": member,
                "vote": vote,
                "reasoning": reasoning
            }
        ), channel=self.channel)

    async def complete_deliberation(
        self,
        deliberation_id: str,
        decision: str,
        consensus: float,
        summary: str
    ):
        """Signal completion of council deliberation."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.COUNCIL_COMPLETE,
            data={
                "deliberation_id": deliberation_id,
                "decision": decision,
                "consensus": consensus,
                "summary": summary
            }
        ), channel=self.channel)


class StreamingTasks:
    """Helper for streaming task execution updates."""

    def __init__(self, ws_manager: WebSocketManager, channel: str = "tasks"):
        self.ws = ws_manager
        self.channel = channel

    async def task_started(self, task_id: str, name: str, description: str):
        """Signal task started."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.TASK_START,
            data={
                "task_id": task_id,
                "name": name,
                "description": description
            }
        ), channel=self.channel)

    async def task_progress(
        self,
        task_id: str,
        progress: float,
        status: str,
        details: Optional[Dict] = None
    ):
        """Send task progress update."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.TASK_PROGRESS,
            data={
                "task_id": task_id,
                "progress": progress,
                "status": status,
                "details": details or {}
            }
        ), channel=self.channel)

    async def task_completed(
        self,
        task_id: str,
        result: Any,
        duration_ms: float
    ):
        """Signal task completed."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.TASK_COMPLETE,
            data={
                "task_id": task_id,
                "result": result,
                "duration_ms": duration_ms
            }
        ), channel=self.channel)

    async def task_failed(self, task_id: str, error: str):
        """Signal task failed."""
        await self.ws.broadcast(WebSocketMessage(
            type=MessageType.TASK_ERROR,
            data={
                "task_id": task_id,
                "error": error
            }
        ), channel=self.channel)


# =============================================================================
# FASTAPI INTEGRATION
# =============================================================================

def create_websocket_endpoint(manager: WebSocketManager):
    """Create a FastAPI WebSocket endpoint."""
    from fastapi import WebSocket, WebSocketDisconnect

    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        client_id = await manager.register(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                await manager.handle_message(client_id, data)
        except WebSocketDisconnect:
            await manager.unregister(client_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await manager.unregister(client_id)

    return websocket_endpoint


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


# =============================================================================
# INTEGRATION WITH EXISTING SYSTEMS
# =============================================================================

async def wire_to_llm_executor():
    """Wire WebSocket streaming to LLM executor."""
    try:
        from core.wiring import LLMExecutor

        ws = get_ws_manager()
        streaming = StreamingChat(ws)

        # Monkey-patch the execute method to stream
        original_execute = LLMExecutor.execute

        async def streaming_execute(self, prompt: str, **kwargs):
            request_id = f"req-{uuid.uuid4().hex[:8]}"
            await streaming.start_stream(request_id, self.model, prompt)

            try:
                # Call original (which may stream internally)
                result = await original_execute(self, prompt, **kwargs)

                # Send complete message
                await streaming.complete_stream(
                    request_id,
                    result.get("content", ""),
                    result.get("tokens_used", 0),
                    result.get("duration_ms", 0)
                )

                return result
            except Exception as e:
                await streaming.error(request_id, str(e))
                raise

        # Apply patch
        LLMExecutor.execute = streaming_execute
        logger.info("Wired WebSocket streaming to LLM executor")

    except ImportError:
        logger.warning("LLM executor not available for WebSocket wiring")


async def wire_to_agent_engine():
    """Wire WebSocket updates to agent execution engine."""
    try:
        from core.agents.execution_engine import get_engine

        ws = get_ws_manager()
        streaming = StreamingTasks(ws)

        engine = await get_engine()

        # Set callbacks
        engine.on_task_start = lambda t: asyncio.create_task(
            streaming.task_started(t.id, t.name, t.description)
        )
        engine.on_task_complete = lambda t, r: asyncio.create_task(
            streaming.task_completed(t.id, r.output, r.duration_ms)
        )
        engine.on_task_failed = lambda t, e: asyncio.create_task(
            streaming.task_failed(t.id, e)
        )

        logger.info("Wired WebSocket updates to agent engine")

    except ImportError:
        logger.warning("Agent engine not available for WebSocket wiring")
