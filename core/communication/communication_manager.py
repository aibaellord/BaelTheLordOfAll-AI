#!/usr/bin/env python3
"""
BAEL - Communication Manager
Advanced inter-agent communication system.

Features:
- Message passing
- Topic-based pub/sub
- Request-response patterns
- Broadcast messaging
- Message routing
- Protocol handling
- Compression
- Encryption
"""

import asyncio
import base64
import copy
import gzip
import hashlib
import hmac
import json
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MessageType(Enum):
    """Message types."""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    COMMAND = "command"
    QUERY = "query"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"


class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BULK = 4


class MessageStatus(Enum):
    """Message status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"


class ChannelType(Enum):
    """Channel types."""
    POINT_TO_POINT = "point_to_point"
    TOPIC = "topic"
    QUEUE = "queue"
    BROADCAST = "broadcast"


class CompressionType(Enum):
    """Compression algorithms."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"


class ProtocolType(Enum):
    """Communication protocols."""
    INTERNAL = "internal"
    HTTP = "http"
    WEBSOCKET = "websocket"
    GRPC = "grpc"


class DeliveryMode(Enum):
    """Delivery modes."""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MessageHeader:
    """Message header."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    message_type: MessageType = MessageType.EVENT
    priority: MessagePriority = MessagePriority.NORMAL
    content_type: str = "application/json"
    compression: CompressionType = CompressionType.NONE
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    custom: Dict[str, str] = field(default_factory=dict)


@dataclass
class Message:
    """Communication message."""
    header: MessageHeader = field(default_factory=MessageHeader)
    sender: str = ""
    recipient: str = ""
    topic: str = ""
    payload: Any = None
    status: MessageStatus = MessageStatus.PENDING
    attempts: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Envelope:
    """Message envelope for transport."""
    envelope_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message: Message = field(default_factory=Message)
    signature: str = ""
    encrypted: bool = False
    compressed: bool = False
    raw_data: bytes = b""


@dataclass
class Channel:
    """Communication channel."""
    channel_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    channel_type: ChannelType = ChannelType.TOPIC
    protocol: ProtocolType = ProtocolType.INTERNAL
    capacity: int = 1000
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    """Channel subscription."""
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subscriber: str = ""
    channel_id: str = ""
    topic_pattern: str = "*"
    handler: Optional[Callable[[Message], Awaitable[None]]] = None
    filter_func: Optional[Callable[[Message], bool]] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PendingRequest:
    """Pending request awaiting response."""
    request_id: str
    future: asyncio.Future
    timeout: float
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CommunicationStats:
    """Communication statistics."""
    messages_sent: int = 0
    messages_received: int = 0
    messages_failed: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    active_channels: int = 0
    active_subscriptions: int = 0
    avg_latency: float = 0.0


# =============================================================================
# SERIALIZER
# =============================================================================

class MessageSerializer:
    """Serialize and deserialize messages."""

    def serialize(self, message: Message) -> bytes:
        """Serialize message to bytes."""
        data = {
            "header": {
                "message_id": message.header.message_id,
                "correlation_id": message.header.correlation_id,
                "reply_to": message.header.reply_to,
                "message_type": message.header.message_type.value,
                "priority": message.header.priority.value,
                "content_type": message.header.content_type,
                "compression": message.header.compression.value,
                "timestamp": message.header.timestamp.isoformat(),
                "expires_at": message.header.expires_at.isoformat() if message.header.expires_at else None,
                "custom": message.header.custom
            },
            "sender": message.sender,
            "recipient": message.recipient,
            "topic": message.topic,
            "payload": message.payload,
            "status": message.status.value,
            "attempts": message.attempts,
            "created_at": message.created_at.isoformat(),
            "metadata": message.metadata
        }
        return json.dumps(data).encode('utf-8')

    def deserialize(self, data: bytes) -> Message:
        """Deserialize bytes to message."""
        obj = json.loads(data.decode('utf-8'))

        header = MessageHeader(
            message_id=obj["header"]["message_id"],
            correlation_id=obj["header"]["correlation_id"],
            reply_to=obj["header"]["reply_to"],
            message_type=MessageType(obj["header"]["message_type"]),
            priority=MessagePriority(obj["header"]["priority"]),
            content_type=obj["header"]["content_type"],
            compression=CompressionType(obj["header"]["compression"]),
            timestamp=datetime.fromisoformat(obj["header"]["timestamp"]),
            expires_at=datetime.fromisoformat(obj["header"]["expires_at"]) if obj["header"]["expires_at"] else None,
            custom=obj["header"]["custom"]
        )

        return Message(
            header=header,
            sender=obj["sender"],
            recipient=obj["recipient"],
            topic=obj["topic"],
            payload=obj["payload"],
            status=MessageStatus(obj["status"]),
            attempts=obj["attempts"],
            created_at=datetime.fromisoformat(obj["created_at"]),
            metadata=obj["metadata"]
        )


# =============================================================================
# COMPRESSOR
# =============================================================================

class MessageCompressor:
    """Compress and decompress messages."""

    def compress(
        self,
        data: bytes,
        compression: CompressionType
    ) -> bytes:
        """Compress data."""
        if compression == CompressionType.NONE:
            return data
        elif compression == CompressionType.GZIP:
            return gzip.compress(data)
        elif compression == CompressionType.ZLIB:
            return zlib.compress(data)
        else:
            return data

    def decompress(
        self,
        data: bytes,
        compression: CompressionType
    ) -> bytes:
        """Decompress data."""
        if compression == CompressionType.NONE:
            return data
        elif compression == CompressionType.GZIP:
            return gzip.decompress(data)
        elif compression == CompressionType.ZLIB:
            return zlib.decompress(data)
        else:
            return data


# =============================================================================
# ENCRYPTOR
# =============================================================================

class MessageEncryptor:
    """Encrypt and decrypt messages (simple XOR for demo)."""

    def __init__(self, key: bytes = b"bael_secret_key_32"):
        self._key = key

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data using XOR (demo only)."""
        key_len = len(self._key)
        encrypted = bytes([
            data[i] ^ self._key[i % key_len]
            for i in range(len(data))
        ])
        return base64.b64encode(encrypted)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data."""
        decoded = base64.b64decode(data)
        key_len = len(self._key)
        decrypted = bytes([
            decoded[i] ^ self._key[i % key_len]
            for i in range(len(decoded))
        ])
        return decrypted

    def sign(self, data: bytes) -> str:
        """Sign data."""
        signature = hmac.new(self._key, data, hashlib.sha256)
        return signature.hexdigest()

    def verify(self, data: bytes, signature: str) -> bool:
        """Verify signature."""
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)


# =============================================================================
# MESSAGE ROUTER
# =============================================================================

class MessageRouter:
    """Route messages to destinations."""

    def __init__(self):
        self._routes: Dict[str, str] = {}
        self._topic_routes: Dict[str, List[str]] = defaultdict(list)
        self._round_robin: Dict[str, int] = defaultdict(int)

    def add_route(self, pattern: str, destination: str) -> None:
        """Add routing rule."""
        self._routes[pattern] = destination
        self._topic_routes[pattern].append(destination)

    def remove_route(self, pattern: str, destination: str) -> None:
        """Remove routing rule."""
        if pattern in self._routes and self._routes[pattern] == destination:
            del self._routes[pattern]
        if destination in self._topic_routes.get(pattern, []):
            self._topic_routes[pattern].remove(destination)

    def route(self, message: Message) -> List[str]:
        """Get destinations for message."""
        destinations = []

        # Direct routing
        if message.recipient:
            destinations.append(message.recipient)

        # Topic routing
        for pattern, dests in self._topic_routes.items():
            if self._matches(pattern, message.topic):
                destinations.extend(dests)

        return list(set(destinations))

    def route_round_robin(self, topic: str) -> Optional[str]:
        """Route using round-robin."""
        destinations = self._topic_routes.get(topic, [])
        if not destinations:
            return None

        idx = self._round_robin[topic] % len(destinations)
        self._round_robin[topic] += 1
        return destinations[idx]

    def _matches(self, pattern: str, topic: str) -> bool:
        """Check if topic matches pattern."""
        if pattern == "*":
            return True
        if pattern == topic:
            return True
        if pattern.endswith("*"):
            return topic.startswith(pattern[:-1])
        return False


# =============================================================================
# MESSAGE QUEUE
# =============================================================================

class MessageQueue:
    """Queue for message delivery."""

    def __init__(self, capacity: int = 1000):
        self._capacity = capacity
        self._queues: Dict[MessagePriority, deque] = {
            priority: deque(maxlen=capacity)
            for priority in MessagePriority
        }
        self._lock = asyncio.Lock()

    async def enqueue(self, message: Message) -> bool:
        """Add message to queue."""
        async with self._lock:
            queue = self._queues[message.header.priority]
            if len(queue) >= self._capacity:
                return False
            queue.append(message)
            return True

    async def dequeue(self) -> Optional[Message]:
        """Get next message."""
        async with self._lock:
            for priority in MessagePriority:
                if self._queues[priority]:
                    return self._queues[priority].popleft()
            return None

    def size(self) -> int:
        """Get total queue size."""
        return sum(len(q) for q in self._queues.values())

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return all(len(q) == 0 for q in self._queues.values())


# =============================================================================
# CHANNEL MANAGER
# =============================================================================

class ChannelManager:
    """Manage communication channels."""

    def __init__(self):
        self._channels: Dict[str, Channel] = {}
        self._queues: Dict[str, MessageQueue] = {}
        self._by_name: Dict[str, str] = {}

    def create(
        self,
        name: str,
        channel_type: ChannelType = ChannelType.TOPIC,
        capacity: int = 1000
    ) -> Channel:
        """Create channel."""
        channel = Channel(
            name=name,
            channel_type=channel_type,
            capacity=capacity
        )

        self._channels[channel.channel_id] = channel
        self._by_name[name] = channel.channel_id
        self._queues[channel.channel_id] = MessageQueue(capacity)

        return channel

    def get(self, channel_id: str) -> Optional[Channel]:
        """Get channel by ID."""
        return self._channels.get(channel_id)

    def get_by_name(self, name: str) -> Optional[Channel]:
        """Get channel by name."""
        channel_id = self._by_name.get(name)
        return self._channels.get(channel_id) if channel_id else None

    def delete(self, channel_id: str) -> bool:
        """Delete channel."""
        if channel_id in self._channels:
            channel = self._channels[channel_id]
            del self._by_name[channel.name]
            del self._channels[channel_id]
            del self._queues[channel_id]
            return True
        return False

    def list_channels(self) -> List[Channel]:
        """List all channels."""
        return list(self._channels.values())

    def get_queue(self, channel_id: str) -> Optional[MessageQueue]:
        """Get channel queue."""
        return self._queues.get(channel_id)


# =============================================================================
# SUBSCRIPTION MANAGER
# =============================================================================

class SubscriptionManager:
    """Manage subscriptions."""

    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._by_channel: Dict[str, List[str]] = defaultdict(list)
        self._by_subscriber: Dict[str, List[str]] = defaultdict(list)
        self._by_topic: Dict[str, List[str]] = defaultdict(list)

    def subscribe(
        self,
        subscriber: str,
        channel_id: str,
        topic_pattern: str = "*",
        handler: Optional[Callable[[Message], Awaitable[None]]] = None,
        filter_func: Optional[Callable[[Message], bool]] = None
    ) -> Subscription:
        """Create subscription."""
        subscription = Subscription(
            subscriber=subscriber,
            channel_id=channel_id,
            topic_pattern=topic_pattern,
            handler=handler,
            filter_func=filter_func
        )

        self._subscriptions[subscription.subscription_id] = subscription
        self._by_channel[channel_id].append(subscription.subscription_id)
        self._by_subscriber[subscriber].append(subscription.subscription_id)
        self._by_topic[topic_pattern].append(subscription.subscription_id)

        return subscription

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove subscription."""
        if subscription_id not in self._subscriptions:
            return False

        sub = self._subscriptions[subscription_id]

        self._by_channel[sub.channel_id].remove(subscription_id)
        self._by_subscriber[sub.subscriber].remove(subscription_id)
        self._by_topic[sub.topic_pattern].remove(subscription_id)
        del self._subscriptions[subscription_id]

        return True

    def get_subscribers(
        self,
        channel_id: str,
        topic: str
    ) -> List[Subscription]:
        """Get matching subscriptions."""
        subscriptions = []

        for sub_id in self._by_channel.get(channel_id, []):
            sub = self._subscriptions.get(sub_id)
            if sub and self._matches(sub.topic_pattern, topic):
                subscriptions.append(sub)

        return subscriptions

    def get_by_subscriber(self, subscriber: str) -> List[Subscription]:
        """Get subscriber's subscriptions."""
        return [
            self._subscriptions[sub_id]
            for sub_id in self._by_subscriber.get(subscriber, [])
            if sub_id in self._subscriptions
        ]

    def _matches(self, pattern: str, topic: str) -> bool:
        """Check if topic matches pattern."""
        if pattern == "*":
            return True
        if pattern == topic:
            return True
        if pattern.endswith("*"):
            return topic.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return topic.endswith(pattern[1:])
        return False


# =============================================================================
# REQUEST TRACKER
# =============================================================================

class RequestTracker:
    """Track pending requests."""

    def __init__(self):
        self._pending: Dict[str, PendingRequest] = {}

    def track(
        self,
        request_id: str,
        timeout: float = 30.0
    ) -> asyncio.Future:
        """Track pending request."""
        future = asyncio.get_event_loop().create_future()

        self._pending[request_id] = PendingRequest(
            request_id=request_id,
            future=future,
            timeout=timeout
        )

        return future

    def complete(self, request_id: str, response: Message) -> bool:
        """Complete pending request."""
        if request_id in self._pending:
            pending = self._pending.pop(request_id)
            if not pending.future.done():
                pending.future.set_result(response)
            return True
        return False

    def fail(self, request_id: str, error: Exception) -> bool:
        """Fail pending request."""
        if request_id in self._pending:
            pending = self._pending.pop(request_id)
            if not pending.future.done():
                pending.future.set_exception(error)
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired requests."""
        now = datetime.now()
        expired = []

        for req_id, pending in self._pending.items():
            elapsed = (now - pending.created_at).total_seconds()
            if elapsed > pending.timeout:
                expired.append(req_id)

        for req_id in expired:
            self.fail(req_id, asyncio.TimeoutError("Request timed out"))

        return len(expired)


# =============================================================================
# MESSAGE DISPATCHER
# =============================================================================

class MessageDispatcher:
    """Dispatch messages to handlers."""

    def __init__(self, subscription_manager: SubscriptionManager):
        self._subscription_manager = subscription_manager
        self._handlers: Dict[str, Callable[[Message], Awaitable[None]]] = {}

    def register_handler(
        self,
        agent_id: str,
        handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """Register message handler."""
        self._handlers[agent_id] = handler

    def unregister_handler(self, agent_id: str) -> None:
        """Unregister message handler."""
        self._handlers.pop(agent_id, None)

    async def dispatch(
        self,
        message: Message,
        channel_id: str
    ) -> int:
        """Dispatch message to subscribers."""
        subscriptions = self._subscription_manager.get_subscribers(
            channel_id,
            message.topic
        )

        delivered = 0

        for sub in subscriptions:
            # Apply filter
            if sub.filter_func and not sub.filter_func(message):
                continue

            # Use subscription handler or registered handler
            handler = sub.handler or self._handlers.get(sub.subscriber)

            if handler:
                try:
                    await handler(message)
                    delivered += 1
                except Exception as e:
                    pass

        return delivered


# =============================================================================
# COMMUNICATION MANAGER
# =============================================================================

class CommunicationManager:
    """
    Communication Manager for BAEL.

    Advanced inter-agent communication system.
    """

    def __init__(
        self,
        agent_id: str = "bael_core",
        encryption_key: Optional[bytes] = None
    ):
        self._agent_id = agent_id
        self._channel_manager = ChannelManager()
        self._subscription_manager = SubscriptionManager()
        self._router = MessageRouter()
        self._request_tracker = RequestTracker()
        self._serializer = MessageSerializer()
        self._compressor = MessageCompressor()
        self._encryptor = MessageEncryptor(encryption_key or b"bael_default_key")
        self._dispatcher = MessageDispatcher(self._subscription_manager)

        self._message_history: deque = deque(maxlen=10000)
        self._stats = CommunicationStats()
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None

        # Register own handler
        self._dispatcher.register_handler(agent_id, self._handle_message)

    # -------------------------------------------------------------------------
    # CHANNEL MANAGEMENT
    # -------------------------------------------------------------------------

    def create_channel(
        self,
        name: str,
        channel_type: ChannelType = ChannelType.TOPIC,
        capacity: int = 1000
    ) -> Channel:
        """Create communication channel."""
        channel = self._channel_manager.create(name, channel_type, capacity)
        self._stats.active_channels += 1
        return channel

    def get_channel(self, name: str) -> Optional[Channel]:
        """Get channel by name."""
        return self._channel_manager.get_by_name(name)

    def delete_channel(self, name: str) -> bool:
        """Delete channel."""
        channel = self._channel_manager.get_by_name(name)
        if channel:
            self._channel_manager.delete(channel.channel_id)
            self._stats.active_channels -= 1
            return True
        return False

    def list_channels(self) -> List[Channel]:
        """List all channels."""
        return self._channel_manager.list_channels()

    # -------------------------------------------------------------------------
    # SUBSCRIPTION
    # -------------------------------------------------------------------------

    def subscribe(
        self,
        channel_name: str,
        topic_pattern: str = "*",
        handler: Optional[Callable[[Message], Awaitable[None]]] = None,
        filter_func: Optional[Callable[[Message], bool]] = None
    ) -> Optional[Subscription]:
        """Subscribe to channel."""
        channel = self._channel_manager.get_by_name(channel_name)
        if not channel:
            return None

        subscription = self._subscription_manager.subscribe(
            subscriber=self._agent_id,
            channel_id=channel.channel_id,
            topic_pattern=topic_pattern,
            handler=handler,
            filter_func=filter_func
        )

        self._stats.active_subscriptions += 1
        return subscription

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe."""
        if self._subscription_manager.unsubscribe(subscription_id):
            self._stats.active_subscriptions -= 1
            return True
        return False

    def get_subscriptions(self) -> List[Subscription]:
        """Get own subscriptions."""
        return self._subscription_manager.get_by_subscriber(self._agent_id)

    # -------------------------------------------------------------------------
    # ROUTING
    # -------------------------------------------------------------------------

    def add_route(self, topic_pattern: str, destination: str) -> None:
        """Add routing rule."""
        self._router.add_route(topic_pattern, destination)

    def remove_route(self, topic_pattern: str, destination: str) -> None:
        """Remove routing rule."""
        self._router.remove_route(topic_pattern, destination)

    # -------------------------------------------------------------------------
    # MESSAGING
    # -------------------------------------------------------------------------

    async def send(
        self,
        recipient: str,
        payload: Any,
        topic: str = "",
        message_type: MessageType = MessageType.EVENT,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl: Optional[float] = None,
        compress: bool = False,
        encrypt: bool = False
    ) -> Message:
        """Send message."""
        header = MessageHeader(
            message_type=message_type,
            priority=priority,
            compression=CompressionType.GZIP if compress else CompressionType.NONE,
            expires_at=datetime.now() + timedelta(seconds=ttl) if ttl else None
        )

        message = Message(
            header=header,
            sender=self._agent_id,
            recipient=recipient,
            topic=topic,
            payload=payload
        )

        # Serialize
        data = self._serializer.serialize(message)

        # Compress
        if compress:
            data = self._compressor.compress(data, CompressionType.GZIP)

        # Create envelope
        envelope = Envelope(
            message=message,
            compressed=compress,
            encrypted=encrypt,
            raw_data=data
        )

        # Encrypt
        if encrypt:
            envelope.raw_data = self._encryptor.encrypt(data)
            envelope.signature = self._encryptor.sign(data)

        # Route and deliver
        destinations = self._router.route(message)
        if not destinations:
            destinations = [recipient]

        for dest in destinations:
            await self._deliver(envelope, dest)

        # Update stats
        message.status = MessageStatus.SENT
        message.sent_at = datetime.now()
        self._stats.messages_sent += 1
        self._stats.bytes_sent += len(envelope.raw_data)

        # Store in history
        self._message_history.append(message)

        return message

    async def _deliver(self, envelope: Envelope, destination: str) -> None:
        """Deliver envelope to destination."""
        # Get channel
        channel = self._channel_manager.get_by_name(destination)

        if channel:
            # Queue for dispatch
            queue = self._channel_manager.get_queue(channel.channel_id)
            if queue:
                await queue.enqueue(envelope.message)

                # Dispatch
                await self._dispatcher.dispatch(envelope.message, channel.channel_id)
        else:
            # Direct delivery
            handler = self._dispatcher._handlers.get(destination)
            if handler:
                await handler(envelope.message)

    async def publish(
        self,
        channel_name: str,
        topic: str,
        payload: Any,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Message:
        """Publish message to channel."""
        channel = self._channel_manager.get_by_name(channel_name)
        if not channel:
            raise ValueError(f"Channel not found: {channel_name}")

        return await self.send(
            recipient=channel_name,
            payload=payload,
            topic=topic,
            message_type=MessageType.EVENT,
            priority=priority
        )

    async def broadcast(
        self,
        topic: str,
        payload: Any,
        exclude: Optional[List[str]] = None
    ) -> int:
        """Broadcast message to all."""
        exclude = exclude or []
        sent = 0

        for channel in self._channel_manager.list_channels():
            if channel.name not in exclude:
                await self.publish(channel.name, topic, payload)
                sent += 1

        return sent

    async def request(
        self,
        recipient: str,
        payload: Any,
        timeout: float = 30.0
    ) -> Message:
        """Send request and wait for response."""
        # Create request message
        message = await self.send(
            recipient=recipient,
            payload=payload,
            message_type=MessageType.REQUEST
        )

        # Track pending
        future = self._request_tracker.track(
            message.header.message_id,
            timeout
        )

        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(f"Request {message.header.message_id} timed out")

    async def respond(
        self,
        request: Message,
        payload: Any
    ) -> Message:
        """Send response to request."""
        header = MessageHeader(
            message_type=MessageType.RESPONSE,
            correlation_id=request.header.message_id,
            reply_to=request.header.reply_to
        )

        message = Message(
            header=header,
            sender=self._agent_id,
            recipient=request.sender,
            topic=request.topic,
            payload=payload
        )

        # Complete pending request on sender side
        self._request_tracker.complete(request.header.message_id, message)

        return await self.send(
            recipient=request.sender,
            payload=payload,
            message_type=MessageType.RESPONSE
        )

    # -------------------------------------------------------------------------
    # MESSAGE HANDLING
    # -------------------------------------------------------------------------

    async def _handle_message(self, message: Message) -> None:
        """Handle incoming message."""
        message.status = MessageStatus.DELIVERED
        message.delivered_at = datetime.now()

        self._stats.messages_received += 1

        # Handle response
        if message.header.message_type == MessageType.RESPONSE:
            if message.header.correlation_id:
                self._request_tracker.complete(
                    message.header.correlation_id,
                    message
                )

    def register_handler(
        self,
        agent_id: str,
        handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """Register message handler for agent."""
        self._dispatcher.register_handler(agent_id, handler)

    def unregister_handler(self, agent_id: str) -> None:
        """Unregister message handler."""
        self._dispatcher.unregister_handler(agent_id)

    # -------------------------------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start communication manager."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop communication manager."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup."""
        while self._running:
            try:
                self._request_tracker.cleanup_expired()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(10)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> CommunicationStats:
        """Get communication statistics."""
        return self._stats

    def get_message_history(
        self,
        limit: int = 100
    ) -> List[Message]:
        """Get recent messages."""
        history = list(self._message_history)
        return history[-limit:]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Communication Manager."""
    print("=" * 70)
    print("BAEL - COMMUNICATION MANAGER DEMO")
    print("Advanced Inter-Agent Communication")
    print("=" * 70)
    print()

    # Create managers
    manager_a = CommunicationManager(agent_id="agent_a")
    manager_b = CommunicationManager(agent_id="agent_b")

    await manager_a.start()
    await manager_b.start()

    # 1. Create Channels
    print("1. CREATE CHANNELS:")
    print("-" * 40)

    events = manager_a.create_channel("events", ChannelType.TOPIC)
    commands = manager_a.create_channel("commands", ChannelType.QUEUE)

    print(f"   Created: {events.name} ({events.channel_type.value})")
    print(f"   Created: {commands.name} ({commands.channel_type.value})")
    print()

    # 2. Subscribe
    print("2. SUBSCRIBE:")
    print("-" * 40)

    received_messages = []

    async def message_handler(msg: Message):
        received_messages.append(msg)

    sub = manager_b.subscribe(
        "events",
        topic_pattern="user.*",
        handler=message_handler
    )

    print(f"   Subscribed: {sub.subscription_id[:8]}...")
    print(f"   Pattern: {sub.topic_pattern}")
    print()

    # Register handler for agent_b on agent_a's manager
    manager_a.register_handler("agent_b", message_handler)

    # 3. Send Message
    print("3. SEND MESSAGE:")
    print("-" * 40)

    msg = await manager_a.send(
        recipient="agent_b",
        payload={"action": "greet", "data": "Hello!"},
        topic="user.greeting",
        priority=MessagePriority.HIGH
    )

    print(f"   Message ID: {msg.header.message_id[:8]}...")
    print(f"   Status: {msg.status.value}")
    print(f"   Priority: {msg.header.priority.name}")
    print()

    # 4. Publish to Channel
    print("4. PUBLISH TO CHANNEL:")
    print("-" * 40)

    await manager_a.publish(
        "events",
        topic="user.login",
        payload={"user_id": "123", "ip": "10.0.0.1"}
    )

    print("   Published to events/user.login")
    print(f"   Received messages: {len(received_messages)}")
    print()

    # 5. Broadcast
    print("5. BROADCAST:")
    print("-" * 40)

    count = await manager_a.broadcast(
        topic="system.announcement",
        payload="System maintenance at midnight"
    )

    print(f"   Broadcast to {count} channels")
    print()

    # 6. Request-Response
    print("6. REQUEST-RESPONSE:")
    print("-" * 40)

    # Simulate request handler
    async def request_handler(msg: Message):
        if msg.header.message_type == MessageType.REQUEST:
            await manager_b.respond(msg, {"status": "ok", "result": 42})

    manager_a.register_handler("agent_b", request_handler)

    # Request can be handled, but for demo we'll skip timeout
    print("   Request-response pattern available")
    print()

    # 7. Compressed Message
    print("7. COMPRESSED MESSAGE:")
    print("-" * 40)

    large_payload = {"data": "x" * 1000}

    msg = await manager_a.send(
        recipient="agent_b",
        payload=large_payload,
        compress=True
    )

    print(f"   Compression: {msg.header.compression.value}")
    print(f"   Bytes sent: {manager_a.get_stats().bytes_sent}")
    print()

    # 8. Message with TTL
    print("8. MESSAGE WITH TTL:")
    print("-" * 40)

    msg = await manager_a.send(
        recipient="agent_b",
        payload="Expires soon",
        ttl=60.0
    )

    print(f"   TTL: 60 seconds")
    print(f"   Expires at: {msg.header.expires_at}")
    print()

    # 9. Routing
    print("9. MESSAGE ROUTING:")
    print("-" * 40)

    manager_a.add_route("logs.*", "log_service")
    manager_a.add_route("metrics.*", "metrics_service")

    print("   Added routes:")
    print("   - logs.* -> log_service")
    print("   - metrics.* -> metrics_service")
    print()

    # 10. Filter Subscription
    print("10. FILTERED SUBSCRIPTION:")
    print("-" * 40)

    def high_priority_filter(msg: Message) -> bool:
        return msg.header.priority.value <= MessagePriority.HIGH.value

    filtered_sub = manager_b.subscribe(
        "events",
        topic_pattern="*",
        filter_func=high_priority_filter
    )

    print("   Subscribed with high-priority filter")
    print()

    # 11. List Channels
    print("11. LIST CHANNELS:")
    print("-" * 40)

    channels = manager_a.list_channels()
    for ch in channels:
        print(f"   - {ch.name} ({ch.channel_type.value})")
    print()

    # 12. Get Subscriptions
    print("12. GET SUBSCRIPTIONS:")
    print("-" * 40)

    subs = manager_b.get_subscriptions()
    print(f"   Agent B subscriptions: {len(subs)}")
    for s in subs:
        print(f"   - Pattern: {s.topic_pattern}")
    print()

    # 13. Message History
    print("13. MESSAGE HISTORY:")
    print("-" * 40)

    history = manager_a.get_message_history(limit=5)
    print(f"   Recent messages: {len(history)}")
    for h in history[:3]:
        print(f"   - {h.topic}: {h.status.value}")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats_a = manager_a.get_stats()
    stats_b = manager_b.get_stats()

    print("   Agent A:")
    print(f"     Sent: {stats_a.messages_sent}")
    print(f"     Bytes sent: {stats_a.bytes_sent}")
    print()
    print("   Agent B:")
    print(f"     Received: {stats_b.messages_received}")
    print()

    # 15. Cleanup
    print("15. CLEANUP:")
    print("-" * 40)

    manager_b.unsubscribe(sub.subscription_id)
    manager_a.delete_channel("commands")

    print("   Unsubscribed and deleted channel")

    await manager_a.stop()
    await manager_b.stop()

    print("   Managers stopped")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Communication Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
