#!/usr/bin/env python3
"""
BAEL - Communication Engine
Agent communication and messaging.

Features:
- Message routing
- Protocol handlers
- Channel management
- Broadcasting
- Conversation tracking
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MessageType(Enum):
    """Message types."""
    INFORM = "inform"
    REQUEST = "request"
    QUERY = "query"
    RESPONSE = "response"
    PROPOSE = "propose"
    ACCEPT = "accept"
    REJECT = "reject"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    BROADCAST = "broadcast"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class ChannelType(Enum):
    """Channel types."""
    DIRECT = "direct"
    GROUP = "group"
    BROADCAST = "broadcast"
    TOPIC = "topic"
    QUEUE = "queue"


class DeliveryStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ProtocolType(Enum):
    """Communication protocol types."""
    FIPA_REQUEST = "fipa_request"
    FIPA_CONTRACT = "fipa_contract"
    FIPA_QUERY = "fipa_query"
    CUSTOM = "custom"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Message:
    """A communication message."""
    message_id: str = ""
    sender: str = ""
    receiver: str = ""
    message_type: MessageType = MessageType.INFORM
    priority: MessagePriority = MessagePriority.NORMAL
    content: Any = None
    reply_to: Optional[str] = None
    conversation_id: Optional[str] = None
    protocol: Optional[str] = None
    language: str = "json"
    encoding: str = "utf-8"
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: DeliveryStatus = DeliveryStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())[:8]


@dataclass
class Channel:
    """A communication channel."""
    channel_id: str = ""
    name: str = ""
    channel_type: ChannelType = ChannelType.DIRECT
    participants: Set[str] = field(default_factory=set)
    topic: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.channel_id:
            self.channel_id = str(uuid.uuid4())[:8]


@dataclass
class Conversation:
    """A conversation thread."""
    conversation_id: str = ""
    participants: Set[str] = field(default_factory=set)
    messages: List[str] = field(default_factory=list)
    topic: str = ""
    protocol: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())[:8]


@dataclass
class Subscription:
    """Channel subscription."""
    subscription_id: str = ""
    subscriber: str = ""
    channel_id: str = ""
    filter_pattern: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.subscription_id:
            self.subscription_id = str(uuid.uuid4())[:8]


@dataclass
class CommunicationStats:
    """Communication statistics."""
    messages_sent: int = 0
    messages_received: int = 0
    messages_failed: int = 0
    avg_latency_ms: float = 0.0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_channel: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# MESSAGE STORE
# =============================================================================

class MessageStore:
    """Store for messages."""

    def __init__(self, capacity: int = 10000):
        self._capacity = capacity
        self._messages: Dict[str, Message] = {}
        self._by_sender: Dict[str, List[str]] = defaultdict(list)
        self._by_receiver: Dict[str, List[str]] = defaultdict(list)
        self._by_conversation: Dict[str, List[str]] = defaultdict(list)
        self._queue: deque = deque(maxlen=capacity)

    def store(self, message: Message) -> None:
        """Store a message."""
        if len(self._queue) >= self._capacity:
            old_id = self._queue[0]
            self._remove(old_id)

        self._messages[message.message_id] = message
        self._by_sender[message.sender].append(message.message_id)
        self._by_receiver[message.receiver].append(message.message_id)

        if message.conversation_id:
            self._by_conversation[message.conversation_id].append(message.message_id)

        self._queue.append(message.message_id)

    def get(self, message_id: str) -> Optional[Message]:
        """Get a message."""
        return self._messages.get(message_id)

    def by_sender(self, sender: str) -> List[Message]:
        """Get messages by sender."""
        ids = self._by_sender.get(sender, [])
        return [self._messages[mid] for mid in ids if mid in self._messages]

    def by_receiver(self, receiver: str) -> List[Message]:
        """Get messages by receiver."""
        ids = self._by_receiver.get(receiver, [])
        return [self._messages[mid] for mid in ids if mid in self._messages]

    def by_conversation(self, conversation_id: str) -> List[Message]:
        """Get messages by conversation."""
        ids = self._by_conversation.get(conversation_id, [])
        return [self._messages[mid] for mid in ids if mid in self._messages]

    def _remove(self, message_id: str) -> None:
        """Remove a message."""
        message = self._messages.pop(message_id, None)
        if message:
            if message.message_id in self._by_sender.get(message.sender, []):
                self._by_sender[message.sender].remove(message.message_id)
            if message.message_id in self._by_receiver.get(message.receiver, []):
                self._by_receiver[message.receiver].remove(message.message_id)

    @property
    def count(self) -> int:
        return len(self._messages)


# =============================================================================
# CHANNEL MANAGER
# =============================================================================

class ChannelManager:
    """Manage communication channels."""

    def __init__(self):
        self._channels: Dict[str, Channel] = {}
        self._by_type: Dict[ChannelType, Set[str]] = defaultdict(set)
        self._by_participant: Dict[str, Set[str]] = defaultdict(set)

    def create(
        self,
        name: str,
        channel_type: ChannelType = ChannelType.DIRECT,
        participants: Optional[Set[str]] = None,
        topic: str = ""
    ) -> Channel:
        """Create a channel."""
        channel = Channel(
            name=name,
            channel_type=channel_type,
            participants=participants or set(),
            topic=topic
        )

        self._channels[channel.channel_id] = channel
        self._by_type[channel_type].add(channel.channel_id)

        for participant in channel.participants:
            self._by_participant[participant].add(channel.channel_id)

        return channel

    def delete(self, channel_id: str) -> Optional[Channel]:
        """Delete a channel."""
        channel = self._channels.pop(channel_id, None)

        if channel:
            self._by_type[channel.channel_type].discard(channel_id)
            for participant in channel.participants:
                self._by_participant[participant].discard(channel_id)

        return channel

    def get(self, channel_id: str) -> Optional[Channel]:
        """Get a channel."""
        return self._channels.get(channel_id)

    def add_participant(self, channel_id: str, participant: str) -> bool:
        """Add participant to channel."""
        channel = self._channels.get(channel_id)
        if not channel:
            return False

        channel.participants.add(participant)
        self._by_participant[participant].add(channel_id)

        return True

    def remove_participant(self, channel_id: str, participant: str) -> bool:
        """Remove participant from channel."""
        channel = self._channels.get(channel_id)
        if not channel:
            return False

        channel.participants.discard(participant)
        self._by_participant[participant].discard(channel_id)

        return True

    def get_by_type(self, channel_type: ChannelType) -> List[Channel]:
        """Get channels by type."""
        ids = self._by_type.get(channel_type, set())
        return [self._channels[cid] for cid in ids if cid in self._channels]

    def get_by_participant(self, participant: str) -> List[Channel]:
        """Get channels by participant."""
        ids = self._by_participant.get(participant, set())
        return [self._channels[cid] for cid in ids if cid in self._channels]

    def find_direct_channel(self, agent1: str, agent2: str) -> Optional[Channel]:
        """Find direct channel between two agents."""
        channels1 = self._by_participant.get(agent1, set())
        channels2 = self._by_participant.get(agent2, set())

        common = channels1 & channels2

        for cid in common:
            channel = self._channels.get(cid)
            if channel and channel.channel_type == ChannelType.DIRECT:
                if len(channel.participants) == 2:
                    return channel

        return None


# =============================================================================
# MESSAGE ROUTER
# =============================================================================

class MessageRouter:
    """Route messages to recipients."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._filters: List[Callable[[Message], bool]] = []
        self._queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

    def register_handler(
        self,
        agent_id: str,
        handler: Callable[[Message], None]
    ) -> None:
        """Register a message handler."""
        self._handlers[agent_id].append(handler)

    def unregister_handler(self, agent_id: str) -> None:
        """Unregister handlers for an agent."""
        self._handlers.pop(agent_id, None)

    def add_filter(self, filter_fn: Callable[[Message], bool]) -> None:
        """Add a message filter."""
        self._filters.append(filter_fn)

    async def route(self, message: Message) -> bool:
        """Route a message to its recipient."""
        for filter_fn in self._filters:
            if not filter_fn(message):
                message.status = DeliveryStatus.FAILED
                return False

        if message.receiver == "*":
            for agent_id, handlers in self._handlers.items():
                if agent_id != message.sender:
                    for handler in handlers:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
            message.status = DeliveryStatus.DELIVERED
            return True

        handlers = self._handlers.get(message.receiver, [])

        if not handlers:
            self._queues[message.receiver].append(message)
            message.status = DeliveryStatus.PENDING
            return True

        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)

        message.status = DeliveryStatus.DELIVERED
        return True

    def get_queued_messages(self, agent_id: str) -> List[Message]:
        """Get queued messages for an agent."""
        queue = self._queues.get(agent_id, deque())
        messages = list(queue)
        queue.clear()
        return messages


# =============================================================================
# PROTOCOL HANDLER
# =============================================================================

class ProtocolHandler(ABC):
    """Base class for protocol handlers."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    async def handle(
        self,
        message: Message,
        context: Dict[str, Any]
    ) -> Optional[Message]:
        """Handle a protocol message."""
        pass


class FIPARequestProtocol(ProtocolHandler):
    """FIPA Request Protocol handler."""

    def __init__(self):
        super().__init__("fipa_request")
        self._pending_requests: Dict[str, Message] = {}

    async def handle(
        self,
        message: Message,
        context: Dict[str, Any]
    ) -> Optional[Message]:
        """Handle request protocol message."""
        if message.message_type == MessageType.REQUEST:
            self._pending_requests[message.message_id] = message

        elif message.message_type == MessageType.ACCEPT:
            original = self._pending_requests.get(message.reply_to)
            if original:
                return Message(
                    sender=message.receiver,
                    receiver=message.sender,
                    message_type=MessageType.INFORM,
                    content={"status": "executing"},
                    reply_to=message.message_id,
                    conversation_id=message.conversation_id,
                    protocol=self._name
                )

        elif message.message_type == MessageType.REJECT:
            self._pending_requests.pop(message.reply_to, None)

        elif message.message_type == MessageType.INFORM:
            self._pending_requests.pop(message.reply_to, None)

        return None


class FIPAContractProtocol(ProtocolHandler):
    """FIPA Contract Net Protocol handler."""

    def __init__(self):
        super().__init__("fipa_contract")
        self._cfps: Dict[str, Message] = {}
        self._proposals: Dict[str, List[Message]] = defaultdict(list)

    async def handle(
        self,
        message: Message,
        context: Dict[str, Any]
    ) -> Optional[Message]:
        """Handle contract net protocol message."""
        if message.message_type == MessageType.REQUEST:
            self._cfps[message.message_id] = message

        elif message.message_type == MessageType.PROPOSE:
            if message.reply_to:
                self._proposals[message.reply_to].append(message)

        elif message.message_type == MessageType.ACCEPT:
            proposals = self._proposals.get(message.reply_to, [])
            for proposal in proposals:
                if proposal.sender == message.receiver:
                    return Message(
                        sender=proposal.sender,
                        receiver=message.sender,
                        message_type=MessageType.INFORM,
                        content={"status": "contract_awarded"},
                        reply_to=message.message_id,
                        conversation_id=message.conversation_id,
                        protocol=self._name
                    )

        return None


# =============================================================================
# CONVERSATION MANAGER
# =============================================================================

class ConversationManager:
    """Manage conversation threads."""

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._by_participant: Dict[str, Set[str]] = defaultdict(set)

    def create(
        self,
        participants: Set[str],
        topic: str = "",
        protocol: Optional[str] = None
    ) -> Conversation:
        """Create a conversation."""
        conversation = Conversation(
            participants=participants,
            topic=topic,
            protocol=protocol
        )

        self._conversations[conversation.conversation_id] = conversation

        for participant in participants:
            self._by_participant[participant].add(conversation.conversation_id)

        return conversation

    def get(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation."""
        return self._conversations.get(conversation_id)

    def add_message(self, conversation_id: str, message_id: str) -> bool:
        """Add message to conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return False

        conversation.messages.append(message_id)
        return True

    def end_conversation(self, conversation_id: str) -> bool:
        """End a conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return False

        conversation.ended_at = datetime.now()
        conversation.status = "ended"
        return True

    def get_by_participant(self, participant: str) -> List[Conversation]:
        """Get conversations by participant."""
        ids = self._by_participant.get(participant, set())
        return [self._conversations[cid] for cid in ids if cid in self._conversations]

    def get_active(self) -> List[Conversation]:
        """Get active conversations."""
        return [c for c in self._conversations.values() if c.status == "active"]


# =============================================================================
# SUBSCRIPTION MANAGER
# =============================================================================

class SubscriptionManager:
    """Manage channel subscriptions."""

    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._by_subscriber: Dict[str, Set[str]] = defaultdict(set)
        self._by_channel: Dict[str, Set[str]] = defaultdict(set)

    def subscribe(
        self,
        subscriber: str,
        channel_id: str,
        filter_pattern: Optional[str] = None
    ) -> Subscription:
        """Subscribe to a channel."""
        subscription = Subscription(
            subscriber=subscriber,
            channel_id=channel_id,
            filter_pattern=filter_pattern
        )

        self._subscriptions[subscription.subscription_id] = subscription
        self._by_subscriber[subscriber].add(subscription.subscription_id)
        self._by_channel[channel_id].add(subscription.subscription_id)

        return subscription

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a channel."""
        subscription = self._subscriptions.pop(subscription_id, None)

        if subscription:
            self._by_subscriber[subscription.subscriber].discard(subscription_id)
            self._by_channel[subscription.channel_id].discard(subscription_id)
            return True

        return False

    def get_subscribers(self, channel_id: str) -> List[str]:
        """Get subscribers for a channel."""
        sub_ids = self._by_channel.get(channel_id, set())
        subscribers = []

        for sub_id in sub_ids:
            subscription = self._subscriptions.get(sub_id)
            if subscription:
                subscribers.append(subscription.subscriber)

        return subscribers

    def get_subscriptions(self, subscriber: str) -> List[Subscription]:
        """Get subscriptions for a subscriber."""
        sub_ids = self._by_subscriber.get(subscriber, set())
        return [self._subscriptions[sid] for sid in sub_ids if sid in self._subscriptions]


# =============================================================================
# COMMUNICATION ENGINE
# =============================================================================

class CommunicationEngine:
    """
    Communication Engine for BAEL.

    Agent communication and messaging.
    """

    def __init__(self):
        self._store = MessageStore()
        self._channels = ChannelManager()
        self._router = MessageRouter()
        self._conversations = ConversationManager()
        self._subscriptions = SubscriptionManager()

        self._protocols: Dict[str, ProtocolHandler] = {}

        self._stats = CommunicationStats()

        self._register_default_protocols()

    def _register_default_protocols(self) -> None:
        """Register default protocols."""
        self.register_protocol(FIPARequestProtocol())
        self.register_protocol(FIPAContractProtocol())

    def register_protocol(self, protocol: ProtocolHandler) -> None:
        """Register a protocol handler."""
        self._protocols[protocol.name] = protocol

    def register_handler(
        self,
        agent_id: str,
        handler: Callable[[Message], None]
    ) -> None:
        """Register a message handler for an agent."""
        self._router.register_handler(agent_id, handler)

    def unregister_handler(self, agent_id: str) -> None:
        """Unregister handlers for an agent."""
        self._router.unregister_handler(agent_id)

    async def send(
        self,
        sender: str,
        receiver: str,
        content: Any,
        message_type: MessageType = MessageType.INFORM,
        priority: MessagePriority = MessagePriority.NORMAL,
        reply_to: Optional[str] = None,
        conversation_id: Optional[str] = None,
        protocol: Optional[str] = None
    ) -> Message:
        """Send a message."""
        message = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
            priority=priority,
            reply_to=reply_to,
            conversation_id=conversation_id,
            protocol=protocol
        )

        self._store.store(message)

        if conversation_id:
            self._conversations.add_message(conversation_id, message.message_id)

        success = await self._router.route(message)

        self._stats.messages_sent += 1
        type_key = message_type.value
        self._stats.by_type[type_key] = self._stats.by_type.get(type_key, 0) + 1

        if not success:
            self._stats.messages_failed += 1

        if protocol and protocol in self._protocols:
            handler = self._protocols[protocol]
            response = await handler.handle(message, {})
            if response:
                await self.send(
                    sender=response.sender,
                    receiver=response.receiver,
                    content=response.content,
                    message_type=response.message_type,
                    reply_to=response.reply_to,
                    conversation_id=response.conversation_id,
                    protocol=response.protocol
                )

        return message

    async def reply(
        self,
        original_message: Message,
        content: Any,
        message_type: MessageType = MessageType.RESPONSE
    ) -> Message:
        """Reply to a message."""
        return await self.send(
            sender=original_message.receiver,
            receiver=original_message.sender,
            content=content,
            message_type=message_type,
            reply_to=original_message.message_id,
            conversation_id=original_message.conversation_id,
            protocol=original_message.protocol
        )

    async def broadcast(
        self,
        sender: str,
        content: Any,
        channel_id: Optional[str] = None,
        message_type: MessageType = MessageType.BROADCAST
    ) -> Message:
        """Broadcast a message."""
        if channel_id:
            channel = self._channels.get(channel_id)
            if channel:
                for participant in channel.participants:
                    if participant != sender:
                        await self.send(
                            sender=sender,
                            receiver=participant,
                            content=content,
                            message_type=message_type
                        )
                channel.message_count += 1

        return await self.send(
            sender=sender,
            receiver="*",
            content=content,
            message_type=message_type
        )

    async def request(
        self,
        sender: str,
        receiver: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        protocol: str = "fipa_request"
    ) -> Message:
        """Send a request message."""
        content = {
            "action": action,
            "params": params or {}
        }

        return await self.send(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=MessageType.REQUEST,
            protocol=protocol
        )

    async def query(
        self,
        sender: str,
        receiver: str,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Send a query message."""
        content = {
            "query": query,
            "params": params or {}
        }

        return await self.send(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=MessageType.QUERY
        )

    def create_channel(
        self,
        name: str,
        channel_type: ChannelType = ChannelType.DIRECT,
        participants: Optional[Set[str]] = None,
        topic: str = ""
    ) -> Channel:
        """Create a communication channel."""
        return self._channels.create(name, channel_type, participants, topic)

    def delete_channel(self, channel_id: str) -> Optional[Channel]:
        """Delete a channel."""
        return self._channels.delete(channel_id)

    def join_channel(self, channel_id: str, agent_id: str) -> bool:
        """Join a channel."""
        return self._channels.add_participant(channel_id, agent_id)

    def leave_channel(self, channel_id: str, agent_id: str) -> bool:
        """Leave a channel."""
        return self._channels.remove_participant(channel_id, agent_id)

    def get_channel(self, channel_id: str) -> Optional[Channel]:
        """Get a channel."""
        return self._channels.get(channel_id)

    def get_channels_for_agent(self, agent_id: str) -> List[Channel]:
        """Get channels for an agent."""
        return self._channels.get_by_participant(agent_id)

    def start_conversation(
        self,
        participants: Set[str],
        topic: str = "",
        protocol: Optional[str] = None
    ) -> Conversation:
        """Start a conversation."""
        return self._conversations.create(participants, topic, protocol)

    def end_conversation(self, conversation_id: str) -> bool:
        """End a conversation."""
        return self._conversations.end_conversation(conversation_id)

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation."""
        return self._conversations.get(conversation_id)

    def get_conversation_messages(
        self,
        conversation_id: str
    ) -> List[Message]:
        """Get messages in a conversation."""
        return self._store.by_conversation(conversation_id)

    def subscribe(
        self,
        subscriber: str,
        channel_id: str,
        filter_pattern: Optional[str] = None
    ) -> Subscription:
        """Subscribe to a channel."""
        return self._subscriptions.subscribe(subscriber, channel_id, filter_pattern)

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a channel."""
        return self._subscriptions.unsubscribe(subscription_id)

    def get_subscriptions(self, subscriber: str) -> List[Subscription]:
        """Get subscriptions for a subscriber."""
        return self._subscriptions.get_subscriptions(subscriber)

    def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message."""
        return self._store.get(message_id)

    def get_sent_messages(self, agent_id: str) -> List[Message]:
        """Get messages sent by an agent."""
        return self._store.by_sender(agent_id)

    def get_received_messages(self, agent_id: str) -> List[Message]:
        """Get messages received by an agent."""
        return self._store.by_receiver(agent_id)

    def get_queued_messages(self, agent_id: str) -> List[Message]:
        """Get queued messages for an agent."""
        messages = self._router.get_queued_messages(agent_id)
        self._stats.messages_received += len(messages)
        return messages

    def add_message_filter(
        self,
        filter_fn: Callable[[Message], bool]
    ) -> None:
        """Add a message filter."""
        self._router.add_filter(filter_fn)

    @property
    def stats(self) -> CommunicationStats:
        """Get communication statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "stored_messages": self._store.count,
            "channels": len(self._channels._channels),
            "active_conversations": len(self._conversations.get_active()),
            "protocols": list(self._protocols.keys()),
            "messages_sent": self._stats.messages_sent,
            "messages_received": self._stats.messages_received,
            "messages_failed": self._stats.messages_failed,
            "by_type": self._stats.by_type
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Communication Engine."""
    print("=" * 70)
    print("BAEL - COMMUNICATION ENGINE DEMO")
    print("Agent Communication and Messaging")
    print("=" * 70)
    print()

    engine = CommunicationEngine()

    # 1. Register Handlers
    print("1. REGISTER HANDLERS:")
    print("-" * 40)

    received_messages: Dict[str, List[Message]] = defaultdict(list)

    def create_handler(agent_id: str):
        def handler(message: Message):
            received_messages[agent_id].append(message)
            print(f"      [{agent_id}] received: {message.content}")
        return handler

    engine.register_handler("agent_1", create_handler("agent_1"))
    engine.register_handler("agent_2", create_handler("agent_2"))
    engine.register_handler("agent_3", create_handler("agent_3"))

    print("   Registered handlers for: agent_1, agent_2, agent_3")
    print()

    # 2. Send Direct Message
    print("2. SEND DIRECT MESSAGE:")
    print("-" * 40)

    msg = await engine.send(
        sender="agent_1",
        receiver="agent_2",
        content={"greeting": "Hello agent_2!"},
        message_type=MessageType.INFORM
    )

    print(f"   Sent: {msg.message_id}")
    print(f"   From: {msg.sender} -> {msg.receiver}")
    print(f"   Status: {msg.status.value}")
    print()

    # 3. Reply to Message
    print("3. REPLY TO MESSAGE:")
    print("-" * 40)

    reply = await engine.reply(
        msg,
        content={"response": "Hello agent_1!"},
        message_type=MessageType.RESPONSE
    )

    print(f"   Reply: {reply.message_id}")
    print(f"   Reply to: {reply.reply_to}")
    print()

    # 4. Create Channel
    print("4. CREATE CHANNEL:")
    print("-" * 40)

    channel = engine.create_channel(
        name="team_channel",
        channel_type=ChannelType.GROUP,
        participants={"agent_1", "agent_2", "agent_3"},
        topic="Team Collaboration"
    )

    print(f"   Channel: {channel.name}")
    print(f"   Type: {channel.channel_type.value}")
    print(f"   Participants: {channel.participants}")
    print()

    # 5. Broadcast to Channel
    print("5. BROADCAST TO CHANNEL:")
    print("-" * 40)

    broadcast = await engine.broadcast(
        sender="agent_1",
        content={"announcement": "Team meeting at 3pm"},
        channel_id=channel.channel_id
    )

    print(f"   Broadcast: {broadcast.message_id}")
    print(f"   Recipients: {len(channel.participants) - 1}")
    print()

    # 6. Start Conversation
    print("6. START CONVERSATION:")
    print("-" * 40)

    conversation = engine.start_conversation(
        participants={"agent_1", "agent_2"},
        topic="Task Discussion",
        protocol="fipa_request"
    )

    await engine.send(
        sender="agent_1",
        receiver="agent_2",
        content={"task": "Please process data"},
        message_type=MessageType.REQUEST,
        conversation_id=conversation.conversation_id
    )

    print(f"   Conversation: {conversation.conversation_id}")
    print(f"   Topic: {conversation.topic}")
    print(f"   Messages: {len(conversation.messages)}")
    print()

    # 7. Request Protocol
    print("7. REQUEST PROTOCOL:")
    print("-" * 40)

    request = await engine.request(
        sender="agent_1",
        receiver="agent_2",
        action="fetch_data",
        params={"source": "database"},
        protocol="fipa_request"
    )

    print(f"   Request: {request.message_id}")
    print(f"   Action: {request.content.get('action')}")
    print(f"   Protocol: {request.protocol}")
    print()

    # 8. Query Message
    print("8. QUERY MESSAGE:")
    print("-" * 40)

    query = await engine.query(
        sender="agent_2",
        receiver="agent_3",
        query="What is the system status?",
        params={"detailed": True}
    )

    print(f"   Query: {query.message_id}")
    print(f"   Type: {query.message_type.value}")
    print(f"   Content: {query.content}")
    print()

    # 9. Subscriptions
    print("9. CHANNEL SUBSCRIPTIONS:")
    print("-" * 40)

    topic_channel = engine.create_channel(
        name="alerts",
        channel_type=ChannelType.TOPIC,
        topic="System Alerts"
    )

    sub1 = engine.subscribe("agent_1", topic_channel.channel_id)
    sub2 = engine.subscribe("agent_2", topic_channel.channel_id, filter_pattern="critical")

    print(f"   Channel: {topic_channel.name}")
    print(f"   Subscribers: 2")

    subs = engine.get_subscriptions("agent_1")
    print(f"   agent_1 subscriptions: {len(subs)}")
    print()

    # 10. Message History
    print("10. MESSAGE HISTORY:")
    print("-" * 40)

    sent = engine.get_sent_messages("agent_1")
    received = engine.get_received_messages("agent_2")

    print(f"   agent_1 sent: {len(sent)} messages")
    print(f"   agent_2 received: {len(received)} messages")

    conv_msgs = engine.get_conversation_messages(conversation.conversation_id)
    print(f"   Conversation messages: {len(conv_msgs)}")
    print()

    # 11. Channel Management
    print("11. CHANNEL MANAGEMENT:")
    print("-" * 40)

    engine.join_channel(channel.channel_id, "agent_4")
    print(f"   agent_4 joined {channel.name}")

    engine.leave_channel(channel.channel_id, "agent_3")
    print(f"   agent_3 left {channel.name}")

    updated_channel = engine.get_channel(channel.channel_id)
    print(f"   Current participants: {updated_channel.participants}")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Messages Sent: {stats.messages_sent}")
    print(f"   Messages Received: {stats.messages_received}")
    print(f"   Messages Failed: {stats.messages_failed}")
    print(f"   By Type: {stats.by_type}")
    print()

    # 13. Engine Summary
    print("13. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Stored Messages: {summary['stored_messages']}")
    print(f"   Channels: {summary['channels']}")
    print(f"   Active Conversations: {summary['active_conversations']}")
    print(f"   Protocols: {summary['protocols']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Communication Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
