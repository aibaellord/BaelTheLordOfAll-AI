"""
BAEL - Agent Communication Protocol
Advanced inter-agent communication with messaging patterns.

Features:
- Pub/Sub messaging
- Request/Response patterns
- Event-driven architecture
- Message queuing
- Protocol negotiation
- Secure messaging
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class MessageType(Enum):
    """Types of messages."""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    ACK = "ack"
    ERROR = "error"


class DeliveryMode(Enum):
    """Message delivery modes."""
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15


class ChannelType(Enum):
    """Communication channel types."""
    DIRECT = "direct"
    TOPIC = "topic"
    QUEUE = "queue"
    BROADCAST = "broadcast"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MessageHeader:
    """Message header with metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.EVENT
    source: str = ""
    target: str = ""
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    priority: MessagePriority = MessagePriority.NORMAL
    delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE
    content_type: str = "application/json"
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class Message:
    """A message in the communication system."""
    header: MessageHeader
    payload: Any
    channel: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "header": {
                "id": self.header.id,
                "type": self.header.type.value,
                "source": self.header.source,
                "target": self.header.target,
                "correlation_id": self.header.correlation_id,
                "reply_to": self.header.reply_to,
                "timestamp": self.header.timestamp,
                "expires_at": self.header.expires_at,
                "priority": self.header.priority.value,
                "content_type": self.header.content_type,
                "headers": self.header.headers
            },
            "payload": self.payload,
            "channel": self.channel
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        header_data = data.get("header", {})
        header = MessageHeader(
            id=header_data.get("id", str(uuid.uuid4())),
            type=MessageType(header_data.get("type", "event")),
            source=header_data.get("source", ""),
            target=header_data.get("target", ""),
            correlation_id=header_data.get("correlation_id"),
            reply_to=header_data.get("reply_to"),
            timestamp=header_data.get("timestamp", time.time()),
            expires_at=header_data.get("expires_at"),
            priority=MessagePriority(header_data.get("priority", 5)),
            content_type=header_data.get("content_type", "application/json"),
            headers=header_data.get("headers", {})
        )

        return cls(
            header=header,
            payload=data.get("payload"),
            channel=data.get("channel", "")
        )

    def is_expired(self) -> bool:
        if self.header.expires_at is None:
            return False
        return time.time() > self.header.expires_at


@dataclass
class Subscription:
    """A subscription to a channel."""
    id: str
    channel: str
    handler: Callable[[Message], Awaitable[None]]
    filter: Optional[Callable[[Message], bool]] = None
    created_at: float = field(default_factory=time.time)


# =============================================================================
# MESSAGE HANDLERS
# =============================================================================

MessageHandler = Callable[[Message], Awaitable[Optional[Any]]]


class HandlerRegistry:
    """Registry for message handlers."""

    def __init__(self):
        self._handlers: Dict[str, List[MessageHandler]] = defaultdict(list)
        self._request_handlers: Dict[str, MessageHandler] = {}

    def register(self, channel: str, handler: MessageHandler) -> None:
        """Register handler for channel."""
        self._handlers[channel].append(handler)

    def register_request(
        self,
        request_type: str,
        handler: MessageHandler
    ) -> None:
        """Register handler for request type."""
        self._request_handlers[request_type] = handler

    def get_handlers(self, channel: str) -> List[MessageHandler]:
        """Get handlers for channel."""
        handlers = list(self._handlers.get(channel, []))

        # Add wildcard handlers
        for pattern, pattern_handlers in self._handlers.items():
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if channel.startswith(prefix):
                    handlers.extend(pattern_handlers)

        return handlers

    def get_request_handler(
        self,
        request_type: str
    ) -> Optional[MessageHandler]:
        """Get handler for request type."""
        return self._request_handlers.get(request_type)

    def unregister(self, channel: str, handler: MessageHandler) -> bool:
        """Unregister handler."""
        if channel in self._handlers:
            try:
                self._handlers[channel].remove(handler)
                return True
            except ValueError:
                pass
        return False


# =============================================================================
# MESSAGE QUEUE
# =============================================================================

class MessageQueue:
    """Priority message queue."""

    def __init__(self, max_size: int = 10000):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self._pending: Dict[str, Message] = {}
        self._acked: Set[str] = set()

    async def put(self, message: Message) -> None:
        """Put message in queue."""
        priority = -message.header.priority.value  # Negative for highest first
        await self._queue.put((priority, message.header.timestamp, message))

    async def get(self) -> Message:
        """Get next message."""
        _, _, message = await self._queue.get()

        if message.header.delivery_mode != DeliveryMode.AT_MOST_ONCE:
            self._pending[message.header.id] = message

        return message

    def ack(self, message_id: str) -> bool:
        """Acknowledge message."""
        if message_id in self._pending:
            del self._pending[message_id]
            self._acked.add(message_id)
            return True
        return False

    def nack(self, message_id: str) -> Optional[Message]:
        """Negative acknowledge - return message to queue."""
        message = self._pending.pop(message_id, None)
        if message:
            asyncio.create_task(self.put(message))
        return message

    def size(self) -> int:
        """Get queue size."""
        return self._queue.qsize()

    def pending_count(self) -> int:
        """Get pending message count."""
        return len(self._pending)


# =============================================================================
# CHANNEL
# =============================================================================

class Channel:
    """Communication channel."""

    def __init__(
        self,
        name: str,
        channel_type: ChannelType = ChannelType.TOPIC
    ):
        self.name = name
        self.type = channel_type
        self._subscribers: List[Subscription] = []
        self._queue = MessageQueue()
        self._message_count = 0

    async def publish(self, message: Message) -> None:
        """Publish message to channel."""
        message.channel = self.name
        self._message_count += 1

        if self.type == ChannelType.QUEUE:
            # Queue - one consumer
            await self._queue.put(message)
        else:
            # Topic/Broadcast - all subscribers
            await self._deliver_to_subscribers(message)

    async def _deliver_to_subscribers(self, message: Message) -> None:
        """Deliver message to all subscribers."""
        for sub in self._subscribers:
            # Apply filter
            if sub.filter and not sub.filter(message):
                continue

            try:
                await sub.handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")

    def subscribe(
        self,
        handler: Callable[[Message], Awaitable[None]],
        filter: Optional[Callable[[Message], bool]] = None
    ) -> str:
        """Subscribe to channel."""
        sub = Subscription(
            id=str(uuid.uuid4()),
            channel=self.name,
            handler=handler,
            filter=filter
        )
        self._subscribers.append(sub)
        return sub.id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from channel."""
        for i, sub in enumerate(self._subscribers):
            if sub.id == subscription_id:
                self._subscribers.pop(i)
                return True
        return False

    async def consume(self) -> Message:
        """Consume message from queue channel."""
        if self.type != ChannelType.QUEUE:
            raise ValueError("Can only consume from QUEUE channels")
        return await self._queue.get()


# =============================================================================
# MESSAGE BROKER
# =============================================================================

class MessageBroker:
    """Central message broker for agent communication."""

    def __init__(self):
        self._channels: Dict[str, Channel] = {}
        self._handlers = HandlerRegistry()
        self._agents: Dict[str, "AgentConnection"] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._running = False

    def create_channel(
        self,
        name: str,
        channel_type: ChannelType = ChannelType.TOPIC
    ) -> Channel:
        """Create a new channel."""
        if name not in self._channels:
            self._channels[name] = Channel(name, channel_type)
        return self._channels[name]

    def get_channel(self, name: str) -> Optional[Channel]:
        """Get existing channel."""
        return self._channels.get(name)

    async def publish(
        self,
        channel: str,
        payload: Any,
        source: str = "",
        priority: MessagePriority = MessagePriority.NORMAL,
        headers: Dict[str, str] = None
    ) -> str:
        """Publish message to channel."""
        # Auto-create channel
        if channel not in self._channels:
            self.create_channel(channel)

        message = Message(
            header=MessageHeader(
                type=MessageType.EVENT,
                source=source,
                priority=priority,
                headers=headers or {}
            ),
            payload=payload,
            channel=channel
        )

        await self._channels[channel].publish(message)
        return message.header.id

    def subscribe(
        self,
        channel: str,
        handler: Callable[[Message], Awaitable[None]],
        filter: Optional[Callable[[Message], bool]] = None
    ) -> str:
        """Subscribe to channel."""
        if channel not in self._channels:
            self.create_channel(channel)

        return self._channels[channel].subscribe(handler, filter)

    def unsubscribe(self, channel: str, subscription_id: str) -> bool:
        """Unsubscribe from channel."""
        if channel in self._channels:
            return self._channels[channel].unsubscribe(subscription_id)
        return False

    async def request(
        self,
        target: str,
        request_type: str,
        payload: Any,
        timeout: float = 30.0
    ) -> Any:
        """Send request and wait for response."""
        message = Message(
            header=MessageHeader(
                type=MessageType.REQUEST,
                target=target,
                headers={"request_type": request_type}
            ),
            payload=payload
        )

        # Create response future
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[message.header.id] = future

        # Send to target
        reply_channel = f"reply.{message.header.id}"
        message.header.reply_to = reply_channel

        # Subscribe to reply
        async def handle_reply(reply: Message):
            if reply.header.correlation_id == message.header.id:
                if not future.done():
                    future.set_result(reply.payload)

        self.subscribe(reply_channel, handle_reply)

        # Deliver to target
        if target in self._agents:
            await self._agents[target].receive(message)
        else:
            # Try direct channel
            await self.publish(f"agents.{target}", message.payload)

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request to {target} timed out")
        finally:
            del self._pending_requests[message.header.id]

    async def respond(
        self,
        request: Message,
        payload: Any
    ) -> None:
        """Respond to a request."""
        if not request.header.reply_to:
            return

        response = Message(
            header=MessageHeader(
                type=MessageType.RESPONSE,
                source=request.header.target,
                target=request.header.source,
                correlation_id=request.header.id
            ),
            payload=payload
        )

        await self.publish(request.header.reply_to, response.payload)

    def register_agent(
        self,
        agent_id: str,
        connection: "AgentConnection"
    ) -> None:
        """Register an agent connection."""
        self._agents[agent_id] = connection
        logger.info(f"Agent registered: {agent_id}")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics."""
        return {
            "channels": len(self._channels),
            "agents": len(self._agents),
            "pending_requests": len(self._pending_requests),
            "channel_stats": {
                name: {
                    "type": ch.type.value,
                    "subscribers": len(ch._subscribers),
                    "messages": ch._message_count
                }
                for name, ch in self._channels.items()
            }
        }


# =============================================================================
# AGENT CONNECTION
# =============================================================================

class AgentConnection:
    """Connection interface for an agent."""

    def __init__(
        self,
        agent_id: str,
        broker: MessageBroker
    ):
        self.agent_id = agent_id
        self.broker = broker
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._subscriptions: List[str] = []
        self._message_handlers: Dict[str, MessageHandler] = {}

        # Register with broker
        broker.register_agent(agent_id, self)

    async def send(
        self,
        target: str,
        payload: Any,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """Send message to another agent."""
        return await self.broker.publish(
            channel=f"agents.{target}",
            payload=payload,
            source=self.agent_id,
            priority=priority
        )

    async def broadcast(
        self,
        channel: str,
        payload: Any
    ) -> str:
        """Broadcast message to channel."""
        return await self.broker.publish(
            channel=channel,
            payload=payload,
            source=self.agent_id
        )

    async def request(
        self,
        target: str,
        request_type: str,
        payload: Any,
        timeout: float = 30.0
    ) -> Any:
        """Send request and wait for response."""
        return await self.broker.request(
            target=target,
            request_type=request_type,
            payload=payload,
            timeout=timeout
        )

    def subscribe(
        self,
        channel: str,
        handler: Optional[Callable[[Message], Awaitable[None]]] = None
    ) -> str:
        """Subscribe to channel."""
        async def default_handler(msg: Message):
            await self._inbox.put(msg)

        sub_id = self.broker.subscribe(
            channel,
            handler or default_handler
        )
        self._subscriptions.append(sub_id)
        return sub_id

    async def receive(self, message: Message) -> None:
        """Receive incoming message."""
        await self._inbox.put(message)

    async def get_message(self, timeout: Optional[float] = None) -> Message:
        """Get next message from inbox."""
        if timeout:
            return await asyncio.wait_for(
                self._inbox.get(),
                timeout=timeout
            )
        return await self._inbox.get()

    def register_handler(
        self,
        message_type: str,
        handler: MessageHandler
    ) -> None:
        """Register handler for message type."""
        self._message_handlers[message_type] = handler

    async def process_messages(self) -> None:
        """Process incoming messages."""
        while True:
            try:
                message = await self._inbox.get()

                # Get handler
                msg_type = message.header.headers.get(
                    "request_type",
                    message.header.type.value
                )

                handler = self._message_handlers.get(msg_type)

                if handler:
                    try:
                        result = await handler(message)

                        # If request, send response
                        if message.header.type == MessageType.REQUEST:
                            await self.broker.respond(message, result)

                    except Exception as e:
                        logger.error(f"Handler error: {e}")
                        if message.header.type == MessageType.REQUEST:
                            await self.broker.respond(message, {"error": str(e)})

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message processing error: {e}")

    def close(self) -> None:
        """Close connection."""
        self.broker.unregister_agent(self.agent_id)


# =============================================================================
# PROTOCOL NEGOTIATION
# =============================================================================

class Protocol:
    """Communication protocol definition."""

    def __init__(
        self,
        name: str,
        version: str,
        capabilities: List[str]
    ):
        self.name = name
        self.version = version
        self.capabilities = capabilities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": self.capabilities
        }


class ProtocolNegotiator:
    """Negotiate protocols between agents."""

    def __init__(self):
        self._supported: List[Protocol] = []

    def register(self, protocol: Protocol) -> None:
        """Register supported protocol."""
        self._supported.append(protocol)

    def negotiate(
        self,
        remote_protocols: List[Dict[str, Any]]
    ) -> Optional[Protocol]:
        """Negotiate common protocol."""
        for local in self._supported:
            for remote in remote_protocols:
                if (
                    local.name == remote.get("name") and
                    local.version == remote.get("version")
                ):
                    # Check capabilities
                    local_caps = set(local.capabilities)
                    remote_caps = set(remote.get("capabilities", []))

                    if local_caps.issubset(remote_caps):
                        return local

        return None

    def get_supported(self) -> List[Dict[str, Any]]:
        """Get list of supported protocols."""
        return [p.to_dict() for p in self._supported]


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def main():
    """Demonstrate agent communication."""
    broker = MessageBroker()

    # Create agents
    agent_a = AgentConnection("agent_alpha", broker)
    agent_b = AgentConnection("agent_beta", broker)

    print("=== Agent Communication Demo ===\n")

    # Subscribe agent B to messages
    messages_received = []

    async def handler_b(msg: Message):
        messages_received.append(msg)
        print(f"Agent Beta received: {msg.payload}")

    agent_b.subscribe("agents.agent_beta", handler_b)
    agent_b.subscribe("broadcast.all", handler_b)

    # Agent A sends direct message
    print("Agent Alpha sending direct message...")
    await agent_a.send("agent_beta", {"type": "greeting", "text": "Hello Beta!"})
    await asyncio.sleep(0.1)

    # Agent A broadcasts
    print("\nAgent Alpha broadcasting...")
    await agent_a.broadcast("broadcast.all", {"type": "announcement", "text": "Hello everyone!"})
    await asyncio.sleep(0.1)

    # Request/Response pattern
    print("\n=== Request/Response ===")

    # Register handler on agent B
    async def compute_handler(msg: Message) -> Any:
        data = msg.payload
        result = data.get("a", 0) + data.get("b", 0)
        print(f"Agent Beta computing: {data['a']} + {data['b']} = {result}")
        return {"result": result}

    agent_b.register_handler("compute", compute_handler)

    # Start message processing for agent B
    process_task = asyncio.create_task(agent_b.process_messages())

    # Agent A makes request
    try:
        result = await agent_a.request(
            "agent_beta",
            "compute",
            {"a": 5, "b": 3},
            timeout=5.0
        )
        print(f"Agent Alpha received result: {result}")
    except TimeoutError as e:
        print(f"Request timed out: {e}")

    # Pub/Sub with topics
    print("\n=== Pub/Sub Topics ===")

    tasks_channel = broker.create_channel("tasks", ChannelType.TOPIC)

    async def task_handler(msg: Message):
        print(f"Task received: {msg.payload}")

    tasks_channel.subscribe(task_handler)

    await broker.publish(
        "tasks",
        {"task_id": "1", "action": "process_data"},
        source="agent_alpha"
    )
    await asyncio.sleep(0.1)

    # Priority messages
    print("\n=== Priority Messages ===")

    for priority in [MessagePriority.LOW, MessagePriority.HIGH, MessagePriority.CRITICAL]:
        await broker.publish(
            "tasks",
            {"priority_level": priority.name},
            priority=priority
        )

    await asyncio.sleep(0.1)

    # Get stats
    print("\n=== Broker Statistics ===")
    stats = broker.get_stats()
    print(json.dumps(stats, indent=2))

    # Protocol negotiation
    print("\n=== Protocol Negotiation ===")

    negotiator = ProtocolNegotiator()
    negotiator.register(Protocol("bael-agent", "1.0", ["messaging", "streaming"]))
    negotiator.register(Protocol("mcp", "1.0", ["tools", "prompts"]))

    remote_protocols = [
        {"name": "bael-agent", "version": "1.0", "capabilities": ["messaging", "streaming", "rpc"]},
        {"name": "unknown", "version": "2.0", "capabilities": []}
    ]

    matched = negotiator.negotiate(remote_protocols)
    if matched:
        print(f"Negotiated protocol: {matched.name} v{matched.version}")
    else:
        print("No compatible protocol found")

    # Cleanup
    process_task.cancel()
    try:
        await process_task
    except asyncio.CancelledError:
        pass

    agent_a.close()
    agent_b.close()

    print(f"\nTotal messages received by Beta: {len(messages_received)}")


if __name__ == "__main__":
    asyncio.run(main())
