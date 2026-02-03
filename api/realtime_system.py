"""
Real-Time Communication System for BAEL

WebSocket server, pub/sub messaging, live streaming, collaborative features,
and real-time status updates.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class MessageType(Enum):
    """Types of real-time messages."""
    STATUS_UPDATE = "status_update"
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    STREAM = "stream"
    COLLABORATION = "collaboration"
    NOTIFICATION = "notification"


class ClientState(Enum):
    """Client connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class RealtimeMessage:
    """Message for real-time communication."""
    message_id: str
    message_type: MessageType
    content: Any
    timestamp: datetime
    sender_id: Optional[str] = None
    receiver_ids: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps({
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "sender_id": self.sender_id,
            "priority": self.priority,
            "metadata": self.metadata
        })


class Channel:
    """Pub/Sub channel for topic-based messaging."""

    def __init__(self, name: str):
        self.name = name
        self.subscribers: Set[str] = set()
        self.message_history: List[RealtimeMessage] = []
        self.max_history = 100

    def subscribe(self, subscriber_id: str) -> None:
        """Subscribe to channel."""
        self.subscribers.add(subscriber_id)

    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from channel."""
        self.subscribers.discard(subscriber_id)

    def publish(self, message: RealtimeMessage) -> None:
        """Publish message to channel."""
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

    def get_messages(self, since: Optional[datetime] = None) -> List[RealtimeMessage]:
        """Get messages since timestamp."""
        if since is None:
            return self.message_history

        return [m for m in self.message_history if m.timestamp >= since]

    def get_subscriber_count(self) -> int:
        """Get number of subscribers."""
        return len(self.subscribers)


class PubSubBroker:
    """Publish-Subscribe message broker."""

    def __init__(self):
        self.channels: Dict[str, Channel] = {}
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self.total_messages = 0

    def create_channel(self, name: str) -> Channel:
        """Create or get channel."""
        if name not in self.channels:
            self.channels[name] = Channel(name)
        return self.channels[name]

    def subscribe(self, channel_name: str, subscriber_id: str) -> None:
        """Subscribe to channel."""
        channel = self.create_channel(channel_name)
        channel.subscribe(subscriber_id)

    def unsubscribe(self, channel_name: str, subscriber_id: str) -> None:
        """Unsubscribe from channel."""
        if channel_name in self.channels:
            self.channels[channel_name].unsubscribe(subscriber_id)

    def publish(self, channel_name: str, message: RealtimeMessage) -> None:
        """Publish message to channel."""
        channel = self.create_channel(channel_name)
        channel.publish(message)
        self.total_messages += 1

        # Call registered handlers
        for handler in self.message_handlers[message.message_type]:
            try:
                handler(message)
            except Exception as e:
                print(f"Handler error: {e}")

    def register_handler(self, message_type: MessageType,
                        handler: Callable) -> None:
        """Register message handler."""
        self.message_handlers[message_type].append(handler)

    def get_channel_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "total_channels": len(self.channels),
            "total_messages": self.total_messages,
            "channels": {
                name: {
                    "subscribers": channel.get_subscriber_count(),
                    "message_count": len(channel.message_history)
                }
                for name, channel in self.channels.items()
            }
        }


class ClientConnection:
    """Represents a connected client."""

    def __init__(self, client_id: str, session_id: str):
        self.client_id = client_id
        self.session_id = session_id
        self.state = ClientState.CONNECTING
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.subscribed_channels: Set[str] = set()
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.send_callbacks: List[Callable] = []

    def mark_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    async def send_message(self, message: RealtimeMessage) -> None:
        """Queue message to send."""
        await self.message_queue.put(message)

        # Call send callbacks
        for callback in self.send_callbacks:
            try:
                await callback(message) if asyncio.iscoroutinefunction(callback) else callback(message)
            except Exception as e:
                print(f"Send callback error: {e}")

    def subscribe_channel(self, channel_name: str) -> None:
        """Subscribe to channel."""
        self.subscribed_channels.add(channel_name)

    def unsubscribe_channel(self, channel_name: str) -> None:
        """Unsubscribe from channel."""
        self.subscribed_channels.discard(channel_name)

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "client_id": self.client_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "subscribed_channels": list(self.subscribed_channels),
            "queue_size": self.message_queue.qsize()
        }


class StreamingResponse:
    """Handles streaming response data."""

    def __init__(self, response_id: str):
        self.response_id = response_id
        self.chunks: List[str] = []
        self.started_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None

    def add_chunk(self, chunk: str) -> None:
        """Add chunk to stream."""
        self.chunks.append(chunk)

    def complete(self) -> None:
        """Mark stream as complete."""
        self.completed_at = datetime.now()

    def set_error(self, error: str) -> None:
        """Set error on stream."""
        self.error = error
        self.completed_at = datetime.now()

    def get_content(self) -> str:
        """Get complete content."""
        return "".join(self.chunks)

    def get_stats(self) -> Dict[str, Any]:
        """Get stream statistics."""
        duration = (
            (self.completed_at or datetime.now()) - self.started_at
        ).total_seconds()

        return {
            "response_id": self.response_id,
            "chunk_count": len(self.chunks),
            "total_length": sum(len(c) for c in self.chunks),
            "duration_seconds": duration,
            "chunks_per_second": len(self.chunks) / max(0.1, duration),
            "complete": self.completed_at is not None,
            "error": self.error
        }


class CollaborationManager:
    """Manages collaborative features."""

    def __init__(self):
        self.workspaces: Dict[str, Dict[str, Any]] = {}
        self.shared_documents: Dict[str, Dict[str, Any]] = {}
        self.active_editors: Dict[str, Set[str]] = defaultdict(set)

    def create_workspace(self, workspace_id: str, name: str,
                        owner_id: str) -> Dict[str, Any]:
        """Create shared workspace."""
        workspace = {
            "id": workspace_id,
            "name": name,
            "owner_id": owner_id,
            "created_at": datetime.now().isoformat(),
            "members": {owner_id},
            "documents": {}
        }
        self.workspaces[workspace_id] = workspace
        return workspace

    def add_member(self, workspace_id: str, member_id: str) -> bool:
        """Add member to workspace."""
        if workspace_id in self.workspaces:
            self.workspaces[workspace_id]["members"].add(member_id)
            return True
        return False

    def create_shared_document(self, workspace_id: str, doc_id: str,
                              content: str) -> Dict[str, Any]:
        """Create shared document."""
        doc = {
            "id": doc_id,
            "workspace_id": workspace_id,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "revisions": [{"content": content, "timestamp": datetime.now().isoformat()}]
        }
        self.shared_documents[doc_id] = doc
        return doc

    def start_editing(self, doc_id: str, editor_id: str) -> None:
        """Mark user as editing document."""
        self.active_editors[doc_id].add(editor_id)

    def stop_editing(self, doc_id: str, editor_id: str) -> None:
        """Mark user as no longer editing document."""
        self.active_editors[doc_id].discard(editor_id)

    def get_active_editors(self, doc_id: str) -> Set[str]:
        """Get users currently editing document."""
        return self.active_editors.get(doc_id, set())

    def update_document(self, doc_id: str, content: str, editor_id: str) -> None:
        """Update shared document."""
        if doc_id in self.shared_documents:
            doc = self.shared_documents[doc_id]
            doc["content"] = content
            doc["revisions"].append({
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "editor_id": editor_id
            })


class RealtimeCommunicationSystem:
    """Main real-time communication orchestrator."""

    def __init__(self):
        self.broker = PubSubBroker()
        self.clients: Dict[str, ClientConnection] = {}
        self.streams: Dict[str, StreamingResponse] = {}
        self.collaboration = CollaborationManager()
        self.connected_count = 0

    def connect_client(self, client_id: str, session_id: str) -> ClientConnection:
        """Register client connection."""
        connection = ClientConnection(client_id, session_id)
        self.clients[client_id] = connection
        self.connected_count += 1
        return connection

    def disconnect_client(self, client_id: str) -> None:
        """Disconnect client."""
        if client_id in self.clients:
            del self.clients[client_id]
            self.connected_count -= 1

    def get_client(self, client_id: str) -> Optional[ClientConnection]:
        """Get client connection."""
        return self.clients.get(client_id)

    async def broadcast(self, channel: str, message: RealtimeMessage) -> None:
        """Broadcast message to channel."""
        self.broker.publish(channel, message)

        # Send to subscribed clients
        channel_obj = self.broker.channels.get(channel)
        if channel_obj:
            for client_id in channel_obj.subscribers:
                if client_id in self.clients:
                    await self.clients[client_id].send_message(message)

    async def stream_response(self, response_id: str, content_generator) -> StreamingResponse:
        """Stream response data."""
        stream = StreamingResponse(response_id)
        self.streams[response_id] = stream

        try:
            for chunk in content_generator:
                stream.add_chunk(chunk)
                await asyncio.sleep(0)  # Yield control

            stream.complete()
        except Exception as e:
            stream.set_error(str(e))

        return stream

    def create_session_workspace(self, session_id: str) -> str:
        """Create workspace for session."""
        workspace_id = f"ws_{session_id}"
        self.collaboration.create_workspace(workspace_id, f"Session {session_id}", "system")
        return workspace_id

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "connected_clients": self.connected_count,
            "total_clients": len(self.clients),
            "active_streams": len(self.streams),
            "workspaces": len(self.collaboration.workspaces),
            "channels": self.broker.get_channel_stats(),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
_realtime_system = None


def get_realtime_system() -> RealtimeCommunicationSystem:
    """Get or create global real-time system."""
    global _realtime_system
    if _realtime_system is None:
        _realtime_system = RealtimeCommunicationSystem()
    return _realtime_system
