#!/usr/bin/env python3
"""
BAEL - WebSocket Client Manager
Comprehensive WebSocket client for real-time communication.

Features:
- Auto-reconnection
- Heartbeat/ping-pong
- Message queuing
- Event handlers
- Binary and text messages
- Connection pooling
- Backoff strategies
- Metrics and monitoring
- Subscription management
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import random
import struct
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
from typing import (Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple,
                    TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"


class MessageType(Enum):
    """Message types."""
    TEXT = "text"
    BINARY = "binary"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"


class CloseCode(IntEnum):
    """WebSocket close codes."""
    NORMAL = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED = 1003
    NO_STATUS = 1005
    ABNORMAL = 1006
    INVALID_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    EXTENSION_REQUIRED = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN = 1013
    BAD_GATEWAY = 1014


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class WebSocketConfig:
    """WebSocket configuration."""
    url: str = ""
    auto_reconnect: bool = True
    reconnect_interval: float = 1.0
    max_reconnect_attempts: int = 10
    backoff_multiplier: float = 2.0
    max_backoff: float = 60.0
    ping_interval: float = 30.0
    ping_timeout: float = 10.0
    message_queue_size: int = 1000
    connect_timeout: float = 30.0
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class WebSocketMessage:
    """WebSocket message."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    message_type: MessageType = MessageType.TEXT
    data: Union[str, bytes] = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionStats:
    """Connection statistics."""
    connect_time: Optional[float] = None
    disconnect_time: Optional[float] = None
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    reconnect_count: int = 0
    ping_count: int = 0
    pong_count: int = 0
    last_ping: Optional[float] = None
    last_pong: Optional[float] = None
    latency: float = 0.0

    @property
    def uptime(self) -> float:
        if not self.connect_time:
            return 0.0
        end = self.disconnect_time or time.time()
        return end - self.connect_time


# =============================================================================
# BACKOFF STRATEGIES
# =============================================================================

class BackoffStrategy(ABC):
    """Abstract backoff strategy."""

    @abstractmethod
    def next_delay(self, attempt: int) -> float:
        """Get next delay in seconds."""
        pass

    def reset(self) -> None:
        """Reset the strategy."""
        pass


class ExponentialBackoff(BackoffStrategy):
    """Exponential backoff strategy."""

    def __init__(
        self,
        initial: float = 1.0,
        multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: float = 0.1
    ):
        self.initial = initial
        self.multiplier = multiplier
        self.max_delay = max_delay
        self.jitter = jitter

    def next_delay(self, attempt: int) -> float:
        delay = self.initial * (self.multiplier ** attempt)
        delay = min(delay, self.max_delay)

        # Add jitter
        jitter_amount = delay * self.jitter
        delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)


class LinearBackoff(BackoffStrategy):
    """Linear backoff strategy."""

    def __init__(
        self,
        initial: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 30.0
    ):
        self.initial = initial
        self.increment = increment
        self.max_delay = max_delay

    def next_delay(self, attempt: int) -> float:
        delay = self.initial + (self.increment * attempt)
        return min(delay, self.max_delay)


class ConstantBackoff(BackoffStrategy):
    """Constant backoff strategy."""

    def __init__(self, delay: float = 5.0):
        self.delay = delay

    def next_delay(self, attempt: int) -> float:
        return self.delay


# =============================================================================
# MESSAGE HANDLERS
# =============================================================================

MessageHandler = Callable[[WebSocketMessage], Awaitable[None]]
EventHandler = Callable[[str, Any], Awaitable[None]]


# =============================================================================
# SIMULATED WEBSOCKET
# =============================================================================

class SimulatedWebSocket:
    """Simulated WebSocket for demo purposes."""

    def __init__(self, url: str):
        self.url = url
        self.connected = False
        self.incoming: asyncio.Queue = asyncio.Queue()
        self.outgoing: List[str] = []
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Simulate connection."""
        await asyncio.sleep(0.1)
        self.connected = True

        # Start simulated message generator
        self._receive_task = asyncio.create_task(self._generate_messages())

    async def _generate_messages(self) -> None:
        """Generate simulated incoming messages."""
        counter = 0
        while self.connected:
            await asyncio.sleep(2.0)
            counter += 1

            if self.connected:
                message = json.dumps({
                    "type": "server_message",
                    "id": counter,
                    "timestamp": time.time()
                })
                await self.incoming.put(message)

    async def send(self, data: str) -> None:
        """Send a message."""
        if not self.connected:
            raise ConnectionError("Not connected")

        self.outgoing.append(data)
        await asyncio.sleep(0.01)

    async def receive(self) -> str:
        """Receive a message."""
        if not self.connected:
            raise ConnectionError("Not connected")

        try:
            return await asyncio.wait_for(self.incoming.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return ""

    async def close(self) -> None:
        """Close connection."""
        self.connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

    async def ping(self) -> None:
        """Send ping."""
        await asyncio.sleep(0.01)


# =============================================================================
# WEBSOCKET CLIENT
# =============================================================================

class WebSocketClient:
    """
    WebSocket client with auto-reconnection and event handling.
    """

    def __init__(self, config: WebSocketConfig = None):
        self.config = config or WebSocketConfig()

        self._state = ConnectionState.DISCONNECTED
        self._socket: Optional[SimulatedWebSocket] = None
        self._stats = ConnectionStats()

        # Message queue
        self._send_queue: deque = deque(maxlen=self.config.message_queue_size)

        # Handlers
        self._message_handlers: List[MessageHandler] = []
        self._event_handlers: Dict[str, List[EventHandler]] = defaultdict(list)

        # Tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._send_task: Optional[asyncio.Task] = None

        # Backoff
        self._backoff = ExponentialBackoff(
            initial=self.config.reconnect_interval,
            multiplier=self.config.backoff_multiplier,
            max_delay=self.config.max_backoff
        )
        self._reconnect_attempts = 0

        # Control
        self._running = False
        self._lock = asyncio.Lock()

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def stats(self) -> ConnectionStats:
        return self._stats

    async def _emit_event(self, event: str, data: Any = None) -> None:
        """Emit event to handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                await handler(event, data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def on(self, event: str, handler: EventHandler) -> None:
        """Register event handler."""
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: EventHandler = None) -> None:
        """Remove event handler."""
        if handler:
            handlers = self._event_handlers.get(event, [])
            if handler in handlers:
                handlers.remove(handler)
        else:
            self._event_handlers[event].clear()

    def on_message(self, handler: MessageHandler) -> None:
        """Register message handler."""
        self._message_handlers.append(handler)

    async def connect(self) -> bool:
        """Connect to WebSocket server."""
        async with self._lock:
            if self._state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
                return True

            self._state = ConnectionState.CONNECTING
            await self._emit_event("connecting")

            try:
                self._socket = SimulatedWebSocket(self.config.url)
                await asyncio.wait_for(
                    self._socket.connect(),
                    timeout=self.config.connect_timeout
                )

                self._state = ConnectionState.CONNECTED
                self._stats.connect_time = time.time()
                self._reconnect_attempts = 0
                self._running = True

                # Start background tasks
                self._receive_task = asyncio.create_task(self._receive_loop())
                self._send_task = asyncio.create_task(self._send_loop())

                if self.config.ping_interval > 0:
                    self._ping_task = asyncio.create_task(self._ping_loop())

                await self._emit_event("connected")
                logger.info(f"Connected to {self.config.url}")

                return True

            except asyncio.TimeoutError:
                self._state = ConnectionState.DISCONNECTED
                await self._emit_event("error", {"error": "Connection timeout"})
                return False

            except Exception as e:
                self._state = ConnectionState.DISCONNECTED
                await self._emit_event("error", {"error": str(e)})
                return False

    async def disconnect(self, code: CloseCode = CloseCode.NORMAL) -> None:
        """Disconnect from server."""
        async with self._lock:
            self._running = False
            self._state = ConnectionState.CLOSING

            # Cancel tasks
            for task in [self._receive_task, self._ping_task, self._send_task]:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            if self._socket:
                await self._socket.close()
                self._socket = None

            self._state = ConnectionState.CLOSED
            self._stats.disconnect_time = time.time()

            await self._emit_event("disconnected", {"code": code})

    async def _reconnect(self) -> None:
        """Attempt to reconnect."""
        if not self.config.auto_reconnect:
            return

        if self._reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            await self._emit_event("reconnect_failed")
            return

        self._state = ConnectionState.RECONNECTING
        self._reconnect_attempts += 1
        self._stats.reconnect_count += 1

        delay = self._backoff.next_delay(self._reconnect_attempts)

        await self._emit_event("reconnecting", {
            "attempt": self._reconnect_attempts,
            "delay": delay
        })

        logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts})")

        await asyncio.sleep(delay)

        if await self.connect():
            logger.info("Reconnected successfully")
        else:
            await self._reconnect()

    async def _receive_loop(self) -> None:
        """Receive messages loop."""
        while self._running and self._socket:
            try:
                data = await self._socket.receive()

                if not data:
                    continue

                message = WebSocketMessage(
                    message_type=MessageType.TEXT,
                    data=data
                )

                self._stats.messages_received += 1
                self._stats.bytes_received += len(data)

                await self._emit_event("message", message)

                for handler in self._message_handlers:
                    try:
                        await handler(message)
                    except Exception as e:
                        logger.error(f"Message handler error: {e}")

            except asyncio.CancelledError:
                break
            except ConnectionError:
                if self._running:
                    await self._reconnect()
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")
                if self._running:
                    await self._reconnect()
                break

    async def _send_loop(self) -> None:
        """Send queued messages loop."""
        while self._running:
            try:
                if self._send_queue and self._socket and self._socket.connected:
                    message = self._send_queue.popleft()

                    if message.message_type == MessageType.TEXT:
                        await self._socket.send(str(message.data))
                    elif message.message_type == MessageType.BINARY:
                        await self._socket.send(message.data)

                    self._stats.messages_sent += 1
                    self._stats.bytes_sent += len(message.data)

                    await self._emit_event("sent", message)
                else:
                    await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Send error: {e}")

    async def _ping_loop(self) -> None:
        """Ping/heartbeat loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.ping_interval)

                if self._socket and self._socket.connected:
                    self._stats.last_ping = time.time()
                    await self._socket.ping()
                    self._stats.ping_count += 1

                    # Simulate pong
                    await asyncio.sleep(0.05)
                    self._stats.last_pong = time.time()
                    self._stats.pong_count += 1
                    self._stats.latency = self._stats.last_pong - self._stats.last_ping

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ping error: {e}")

    async def send(
        self,
        data: Union[str, bytes, Dict],
        message_type: MessageType = MessageType.TEXT,
        immediate: bool = False
    ) -> bool:
        """Send a message."""
        if isinstance(data, dict):
            data = json.dumps(data)

        message = WebSocketMessage(
            message_type=message_type,
            data=data
        )

        if immediate and self._socket and self._socket.connected:
            try:
                await self._socket.send(str(data))
                self._stats.messages_sent += 1
                self._stats.bytes_sent += len(data)
                await self._emit_event("sent", message)
                return True
            except Exception as e:
                logger.error(f"Send error: {e}")
                return False

        if len(self._send_queue) < self.config.message_queue_size:
            self._send_queue.append(message)
            return True

        return False

    async def send_json(self, data: Dict, immediate: bool = False) -> bool:
        """Send JSON message."""
        return await self.send(json.dumps(data), MessageType.TEXT, immediate)


# =============================================================================
# CONNECTION POOL
# =============================================================================

class WebSocketPool:
    """Pool of WebSocket connections."""

    def __init__(self, size: int = 5):
        self.size = size
        self.clients: Dict[str, WebSocketClient] = {}
        self._lock = asyncio.Lock()

    async def get_client(self, url: str) -> WebSocketClient:
        """Get or create a client for URL."""
        async with self._lock:
            if url not in self.clients:
                if len(self.clients) >= self.size:
                    # Remove oldest
                    oldest_url = next(iter(self.clients))
                    await self.clients[oldest_url].disconnect()
                    del self.clients[oldest_url]

                config = WebSocketConfig(url=url)
                client = WebSocketClient(config)
                await client.connect()
                self.clients[url] = client

            return self.clients[url]

    async def close_all(self) -> None:
        """Close all connections."""
        async with self._lock:
            for client in self.clients.values():
                await client.disconnect()
            self.clients.clear()


# =============================================================================
# SUBSCRIPTION MANAGER
# =============================================================================

class SubscriptionManager:
    """Manages topic subscriptions."""

    def __init__(self, client: WebSocketClient):
        self.client = client
        self.subscriptions: Dict[str, Set[Callable]] = defaultdict(set)

    async def subscribe(
        self,
        topic: str,
        handler: Callable[[str, Any], Awaitable[None]]
    ) -> bool:
        """Subscribe to a topic."""
        self.subscriptions[topic].add(handler)

        # Send subscription message
        await self.client.send_json({
            "action": "subscribe",
            "topic": topic
        })

        return True

    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic."""
        if topic in self.subscriptions:
            del self.subscriptions[topic]

            await self.client.send_json({
                "action": "unsubscribe",
                "topic": topic
            })

            return True
        return False

    async def handle_message(self, message: WebSocketMessage) -> None:
        """Route message to subscribers."""
        try:
            if isinstance(message.data, str):
                data = json.loads(message.data)
            else:
                data = message.data

            topic = data.get("topic", "")

            if topic in self.subscriptions:
                for handler in self.subscriptions[topic]:
                    await handler(topic, data)

        except json.JSONDecodeError:
            pass


# =============================================================================
# WEBSOCKET MANAGER
# =============================================================================

class WebSocketManager:
    """
    WebSocket Client Manager for BAEL.
    """

    def __init__(self):
        self.clients: Dict[str, WebSocketClient] = {}
        self.pool = WebSocketPool()

    def create_client(
        self,
        name: str,
        url: str,
        config: WebSocketConfig = None
    ) -> WebSocketClient:
        """Create a named WebSocket client."""
        if config is None:
            config = WebSocketConfig(url=url)
        else:
            config.url = url

        client = WebSocketClient(config)
        self.clients[name] = client
        return client

    def get_client(self, name: str) -> Optional[WebSocketClient]:
        """Get client by name."""
        return self.clients.get(name)

    async def connect_all(self) -> Dict[str, bool]:
        """Connect all clients."""
        results = {}

        for name, client in self.clients.items():
            results[name] = await client.connect()

        return results

    async def disconnect_all(self) -> None:
        """Disconnect all clients."""
        for client in self.clients.values():
            await client.disconnect()

        await self.pool.close_all()

    def get_all_stats(self) -> Dict[str, ConnectionStats]:
        """Get stats for all clients."""
        return {
            name: client.stats
            for name, client in self.clients.items()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the WebSocket Client System."""
    print("=" * 70)
    print("BAEL - WEBSOCKET CLIENT SYSTEM DEMO")
    print("Real-time Communication Infrastructure")
    print("=" * 70)
    print()

    manager = WebSocketManager()

    # 1. Create Client
    print("1. CREATE CLIENT:")
    print("-" * 40)

    config = WebSocketConfig(
        url="wss://echo.websocket.org",
        auto_reconnect=True,
        ping_interval=10.0
    )

    client = manager.create_client("main", "wss://demo.server", config)
    print(f"   Created client 'main'")
    print(f"   URL: {config.url}")
    print(f"   Auto-reconnect: {config.auto_reconnect}")
    print()

    # 2. Event Handlers
    print("2. EVENT HANDLERS:")
    print("-" * 40)

    events_received = []

    async def on_connect(event: str, data: Any):
        events_received.append(event)
        print(f"   Event: {event}")

    async def on_disconnect(event: str, data: Any):
        events_received.append(event)
        print(f"   Event: {event} (code: {data.get('code', 'N/A')})")

    async def on_message(event: str, data: WebSocketMessage):
        events_received.append(event)
        print(f"   Event: {event} - {str(data.data)[:50]}...")

    client.on("connecting", on_connect)
    client.on("connected", on_connect)
    client.on("disconnected", on_disconnect)
    client.on("message", on_message)

    print("   Registered event handlers")
    print()

    # 3. Message Handler
    print("3. MESSAGE HANDLER:")
    print("-" * 40)

    messages_received = []

    async def message_handler(message: WebSocketMessage):
        messages_received.append(message)

    client.on_message(message_handler)
    print("   Registered message handler")
    print()

    # 4. Connect
    print("4. CONNECT:")
    print("-" * 40)

    connected = await client.connect()
    print(f"   Connected: {connected}")
    print(f"   State: {client.state.value}")
    print()

    # 5. Send Messages
    print("5. SEND MESSAGES:")
    print("-" * 40)

    # Send text
    await client.send("Hello, WebSocket!")
    print("   Sent: text message")

    # Send JSON
    await client.send_json({
        "type": "greeting",
        "message": "Hello from BAEL!"
    })
    print("   Sent: JSON message")

    # Queue messages
    for i in range(5):
        await client.send(f"Message {i+1}")

    print("   Queued: 5 messages")
    print()

    # 6. Wait for Responses
    print("6. WAIT FOR RESPONSES:")
    print("-" * 40)

    await asyncio.sleep(3)

    print(f"   Messages received: {len(messages_received)}")
    print(f"   Events received: {len(events_received)}")
    print()

    # 7. Statistics
    print("7. CONNECTION STATISTICS:")
    print("-" * 40)

    stats = client.stats
    print(f"   Uptime: {stats.uptime:.2f}s")
    print(f"   Messages sent: {stats.messages_sent}")
    print(f"   Messages received: {stats.messages_received}")
    print(f"   Bytes sent: {stats.bytes_sent}")
    print(f"   Bytes received: {stats.bytes_received}")
    print(f"   Ping count: {stats.ping_count}")
    print(f"   Latency: {stats.latency*1000:.1f}ms")
    print()

    # 8. Backoff Strategies
    print("8. BACKOFF STRATEGIES:")
    print("-" * 40)

    exp_backoff = ExponentialBackoff(initial=1.0, multiplier=2.0, max_delay=30.0)
    print("   Exponential backoff delays:")
    for i in range(5):
        print(f"      Attempt {i+1}: {exp_backoff.next_delay(i):.2f}s")

    linear_backoff = LinearBackoff(initial=1.0, increment=2.0)
    print("   Linear backoff delays:")
    for i in range(5):
        print(f"      Attempt {i+1}: {linear_backoff.next_delay(i):.2f}s")
    print()

    # 9. Subscription Manager
    print("9. SUBSCRIPTION MANAGER:")
    print("-" * 40)

    subscriptions = SubscriptionManager(client)

    topic_messages = []

    async def topic_handler(topic: str, data: Any):
        topic_messages.append((topic, data))

    await subscriptions.subscribe("updates", topic_handler)
    await subscriptions.subscribe("alerts", topic_handler)

    print("   Subscribed to: updates, alerts")
    print(f"   Active subscriptions: {len(subscriptions.subscriptions)}")

    await subscriptions.unsubscribe("alerts")
    print(f"   After unsubscribe: {len(subscriptions.subscriptions)}")
    print()

    # 10. Connection Pool
    print("10. CONNECTION POOL:")
    print("-" * 40)

    pool = WebSocketPool(size=3)

    # Get clients from pool
    client1 = await pool.get_client("wss://server1.example.com")
    client2 = await pool.get_client("wss://server2.example.com")

    print(f"   Pool size: {len(pool.clients)}")
    print(f"   Connections: {list(pool.clients.keys())[:2]}...")

    await pool.close_all()
    print("   Pool closed")
    print()

    # 11. Multiple Clients
    print("11. MULTIPLE CLIENTS:")
    print("-" * 40)

    manager.create_client("chat", "wss://chat.example.com")
    manager.create_client("data", "wss://data.example.com")

    print(f"   Total clients: {len(manager.clients)}")

    all_stats = manager.get_all_stats()
    for name, s in all_stats.items():
        print(f"   {name}: {s.messages_sent} sent, {s.messages_received} received")
    print()

    # 12. Disconnect
    print("12. DISCONNECT:")
    print("-" * 40)

    await client.disconnect()
    print(f"   State: {client.state.value}")
    print(f"   Final uptime: {client.stats.uptime:.2f}s")

    await manager.disconnect_all()
    print("   All clients disconnected")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - WebSocket Client System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
