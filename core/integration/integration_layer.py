#!/usr/bin/env python3
"""
BAEL - Integration Layer
Universal integration and communication system for BAEL.

This module provides the central nervous system for BAEL,
enabling all components to communicate, share state, and
coordinate activities through a unified integration layer.

Features:
- Event bus for pub/sub messaging
- State synchronization across components
- Message routing and transformation
- Protocol adapters (HTTP, WebSocket, gRPC, MCP)
- Service discovery and registration
- Circuit breaker for fault tolerance
- Rate limiting and throttling
- Message queuing and prioritization
- Cross-module data sharing
- Integration health monitoring
"""

import asyncio
import hashlib
import json
import logging
import time
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, TypeVar, Union)
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class MessageType(Enum):
    """Types of messages."""
    EVENT = "event"
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"


class ServiceStatus(Enum):
    """Status of a registered service."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ProtocolType(Enum):
    """Communication protocol types."""
    INTERNAL = "internal"
    HTTP = "http"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    MCP = "mcp"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Message:
    """A message in the integration layer."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: MessageType = MessageType.EVENT
    topic: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    source: str = ""
    target: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "topic": self.topic,
            "payload": self.payload,
            "priority": self.priority.value,
            "source": self.source,
            "target": self.target,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "headers": self.headers,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())),
            type=MessageType(data.get("type", "event")),
            topic=data.get("topic", ""),
            payload=data.get("payload", {}),
            priority=MessagePriority(data.get("priority", 3)),
            source=data.get("source", ""),
            target=data.get("target"),
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            headers=data.get("headers", {}),
            metadata=data.get("metadata", {})
        )


@dataclass
class ServiceInfo:
    """Information about a registered service."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    protocol: ProtocolType = ProtocolType.INTERNAL
    endpoint: str = ""
    status: ServiceStatus = ServiceStatus.UNKNOWN
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_check_interval: float = 30.0
    last_health_check: Optional[datetime] = None
    registered_at: datetime = field(default_factory=datetime.now)


@dataclass
class Subscription:
    """A topic subscription."""
    id: str = field(default_factory=lambda: str(uuid4()))
    subscriber_id: str = ""
    topic_pattern: str = ""
    handler: Callable[[Message], Awaitable[None]] = None
    filter_func: Optional[Callable[[Message], bool]] = None
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 100.0
    burst_size: int = 10
    window_seconds: float = 1.0


# =============================================================================
# EVENT BUS
# =============================================================================

class EventBus:
    """
    Central event bus for pub/sub messaging.

    Provides topic-based message routing with pattern matching,
    message filtering, and priority handling.
    """

    def __init__(self):
        self.subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self.message_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.processing = False
        self.message_history: List[Message] = []
        self.max_history_size = 1000
        self.dead_letter_queue: List[Message] = []
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        topic_pattern: str,
        handler: Callable[[Message], Awaitable[None]],
        subscriber_id: str = "",
        filter_func: Optional[Callable[[Message], bool]] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """Subscribe to a topic pattern."""
        subscription = Subscription(
            subscriber_id=subscriber_id or str(uuid4()),
            topic_pattern=topic_pattern,
            handler=handler,
            filter_func=filter_func,
            priority=priority
        )

        async with self._lock:
            self.subscriptions[topic_pattern].append(subscription)

        logger.debug(f"Subscription created: {subscription.id} for {topic_pattern}")
        return subscription.id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        async with self._lock:
            for topic, subs in self.subscriptions.items():
                for sub in subs:
                    if sub.id == subscription_id:
                        subs.remove(sub)
                        logger.debug(f"Subscription removed: {subscription_id}")
                        return True
        return False

    async def publish(self, message: Message) -> None:
        """Publish a message to the bus."""
        # Add to queue with priority
        await self.message_queue.put((
            message.priority.value,
            message.timestamp.timestamp(),
            message
        ))

        # Process immediately if not batch processing
        if not self.processing:
            await self._process_single_message(message)

    async def _process_single_message(self, message: Message) -> None:
        """Process a single message."""
        matching_subs = self._find_matching_subscriptions(message.topic)

        for sub in matching_subs:
            # Apply filter if present
            if sub.filter_func and not sub.filter_func(message):
                continue

            try:
                await sub.handler(message)
            except Exception as e:
                logger.error(f"Handler error for {sub.id}: {e}")
                self.dead_letter_queue.append(message)

        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size:]

    def _find_matching_subscriptions(self, topic: str) -> List[Subscription]:
        """Find all subscriptions matching a topic."""
        matching = []

        for pattern, subs in self.subscriptions.items():
            if self._topic_matches(topic, pattern):
                matching.extend(subs)

        # Sort by priority
        matching.sort(key=lambda s: s.priority.value)
        return matching

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports wildcards)."""
        if pattern == "#":
            return True

        topic_parts = topic.split(".")
        pattern_parts = pattern.split(".")

        i = 0
        j = 0

        while i < len(topic_parts) and j < len(pattern_parts):
            if pattern_parts[j] == "#":
                return True
            elif pattern_parts[j] == "*":
                i += 1
                j += 1
            elif topic_parts[i] == pattern_parts[j]:
                i += 1
                j += 1
            else:
                return False

        return i == len(topic_parts) and j == len(pattern_parts)

    async def start_processing(self) -> None:
        """Start batch message processing."""
        self.processing = True
        while self.processing:
            try:
                priority, timestamp, message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=0.1
                )
                await self._process_single_message(message)
            except asyncio.TimeoutError:
                continue

    async def stop_processing(self) -> None:
        """Stop batch processing."""
        self.processing = False


# =============================================================================
# STATE MANAGER
# =============================================================================

class StateManager:
    """
    Manages shared state across components.

    Provides synchronized state access with change notifications,
    versioning, and conflict resolution.
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.state: Dict[str, Any] = {}
        self.versions: Dict[str, int] = defaultdict(int)
        self.watchers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self.state.get(key, default)

    async def set(
        self,
        key: str,
        value: Any,
        source: str = "",
        publish_change: bool = True
    ) -> int:
        """Set a state value and return new version."""
        async with self._lock:
            old_value = self.state.get(key)
            self.state[key] = value
            self.versions[key] += 1
            version = self.versions[key]

        # Notify watchers
        for watcher in self.watchers.get(key, []):
            try:
                if asyncio.iscoroutinefunction(watcher):
                    await watcher(key, value, old_value)
                else:
                    watcher(key, value, old_value)
            except Exception as e:
                logger.error(f"Watcher error: {e}")

        # Publish change event
        if publish_change:
            await self.event_bus.publish(Message(
                type=MessageType.EVENT,
                topic="state.changed",
                payload={"key": key, "value": value, "version": version},
                source=source
            ))

        return version

    async def delete(self, key: str, source: str = "") -> bool:
        """Delete a state value."""
        async with self._lock:
            if key in self.state:
                del self.state[key]
                if key in self.versions:
                    del self.versions[key]

                await self.event_bus.publish(Message(
                    type=MessageType.EVENT,
                    topic="state.deleted",
                    payload={"key": key},
                    source=source
                ))
                return True
        return False

    async def watch(
        self,
        key: str,
        callback: Callable[[str, Any, Any], Any]
    ) -> str:
        """Watch a state key for changes."""
        watcher_id = str(uuid4())
        self.watchers[key].append(callback)
        return watcher_id

    async def get_version(self, key: str) -> int:
        """Get current version of a key."""
        return self.versions.get(key, 0)

    async def compare_and_set(
        self,
        key: str,
        expected_version: int,
        value: Any,
        source: str = ""
    ) -> Tuple[bool, int]:
        """Set value only if version matches (optimistic locking)."""
        async with self._lock:
            current_version = self.versions.get(key, 0)
            if current_version != expected_version:
                return False, current_version

            self.state[key] = value
            self.versions[key] = current_version + 1
            return True, self.versions[key]

    def get_all_state(self) -> Dict[str, Any]:
        """Get snapshot of all state."""
        return dict(self.state)


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

class ServiceRegistry:
    """
    Service discovery and registration.

    Manages registration of services and their endpoints,
    with health checking and load balancing support.
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.services: Dict[str, ServiceInfo] = {}
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def register(self, service: ServiceInfo) -> str:
        """Register a service."""
        async with self._lock:
            self.services[service.id] = service

        await self.event_bus.publish(Message(
            type=MessageType.EVENT,
            topic="service.registered",
            payload={"service_id": service.id, "name": service.name}
        ))

        # Start health check
        if service.health_check_interval > 0:
            self.health_check_tasks[service.id] = asyncio.create_task(
                self._health_check_loop(service.id)
            )

        logger.info(f"Service registered: {service.name} ({service.id})")
        return service.id

    async def deregister(self, service_id: str) -> bool:
        """Deregister a service."""
        async with self._lock:
            if service_id in self.services:
                del self.services[service_id]

                # Cancel health check
                if service_id in self.health_check_tasks:
                    self.health_check_tasks[service_id].cancel()
                    del self.health_check_tasks[service_id]

                await self.event_bus.publish(Message(
                    type=MessageType.EVENT,
                    topic="service.deregistered",
                    payload={"service_id": service_id}
                ))

                return True
        return False

    async def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        """Get service by ID."""
        return self.services.get(service_id)

    async def find_services(
        self,
        name: Optional[str] = None,
        capability: Optional[str] = None,
        status: Optional[ServiceStatus] = None
    ) -> List[ServiceInfo]:
        """Find services by criteria."""
        results = []

        for service in self.services.values():
            if name and service.name != name:
                continue
            if capability and capability not in service.capabilities:
                continue
            if status and service.status != status:
                continue
            results.append(service)

        return results

    async def _health_check_loop(self, service_id: str) -> None:
        """Health check loop for a service."""
        while True:
            service = self.services.get(service_id)
            if not service:
                break

            try:
                await asyncio.sleep(service.health_check_interval)

                # Perform health check (protocol-specific)
                new_status = await self._check_health(service)

                async with self._lock:
                    if service_id in self.services:
                        old_status = self.services[service_id].status
                        self.services[service_id].status = new_status
                        self.services[service_id].last_health_check = datetime.now()

                        if old_status != new_status:
                            await self.event_bus.publish(Message(
                                type=MessageType.EVENT,
                                topic="service.status_changed",
                                payload={
                                    "service_id": service_id,
                                    "old_status": old_status.value,
                                    "new_status": new_status.value
                                }
                            ))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error for {service_id}: {e}")

    async def _check_health(self, service: ServiceInfo) -> ServiceStatus:
        """Check health of a service."""
        # For internal services, assume healthy
        if service.protocol == ProtocolType.INTERNAL:
            return ServiceStatus.HEALTHY

        # TODO: Implement protocol-specific health checks
        return ServiceStatus.HEALTHY


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.

    Prevents cascading failures by opening the circuit
    when too many failures occur.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Check if execution is allowed."""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if self.last_failure_time:
                    elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                    if elapsed >= self.config.timeout_seconds:
                        self.state = CircuitState.HALF_OPEN
                        self.half_open_calls = 0
                        return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False

        return False

    async def record_success(self) -> None:
        """Record a successful execution."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    async def record_failure(self) -> None:
        """Record a failed execution."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.failure_count = 0
                self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Execute function with circuit breaker protection."""
        if not await self.can_execute():
            raise Exception(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure()
            raise


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """
    Rate limiter using token bucket algorithm.

    Controls the rate of operations to prevent overload.
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.tokens = self.config.burst_size
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens
            self.tokens = min(
                self.config.burst_size,
                self.tokens + elapsed * self.config.requests_per_second
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def wait_for_token(self, tokens: int = 1) -> float:
        """Wait until tokens are available. Returns wait time."""
        start_time = time.time()

        while True:
            if await self.acquire(tokens):
                return time.time() - start_time
            await asyncio.sleep(0.01)


# =============================================================================
# MESSAGE ROUTER
# =============================================================================

class MessageRouter:
    """
    Routes messages between components.

    Provides request-response patterns, message transformation,
    and protocol adaptation.
    """

    def __init__(self, event_bus: EventBus, service_registry: ServiceRegistry):
        self.event_bus = event_bus
        self.service_registry = service_registry
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.transformers: Dict[str, Callable] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}

        # Subscribe to response messages
        asyncio.create_task(self._subscribe_responses())

    async def _subscribe_responses(self) -> None:
        """Subscribe to response messages."""
        await self.event_bus.subscribe(
            "response.#",
            self._handle_response,
            "message_router"
        )

    async def _handle_response(self, message: Message) -> None:
        """Handle response messages."""
        if message.correlation_id and message.correlation_id in self.pending_responses:
            future = self.pending_responses.pop(message.correlation_id)
            if not future.done():
                future.set_result(message)

    async def send(
        self,
        target: str,
        message: Message,
        timeout: float = 30.0
    ) -> Optional[Message]:
        """Send a message and wait for response."""
        # Get target service
        services = await self.service_registry.find_services(name=target)
        if not services:
            raise ValueError(f"Service not found: {target}")

        service = services[0]

        # Apply rate limiting
        if target in self.rate_limiters:
            await self.rate_limiters[target].wait_for_token()

        # Create response future
        message.target = target
        message.correlation_id = message.id

        response_future = asyncio.get_event_loop().create_future()
        self.pending_responses[message.id] = response_future

        try:
            # Apply circuit breaker
            if target in self.circuit_breakers:
                await self.circuit_breakers[target].execute(
                    self.event_bus.publish, message
                )
            else:
                await self.event_bus.publish(message)

            # Wait for response
            if message.type == MessageType.COMMAND or message.type == MessageType.QUERY:
                response = await asyncio.wait_for(response_future, timeout=timeout)
                return response

            return None

        except asyncio.TimeoutError:
            self.pending_responses.pop(message.id, None)
            raise TimeoutError(f"Request to {target} timed out")

    async def broadcast(self, message: Message) -> int:
        """Broadcast message to all matching services."""
        message.type = MessageType.BROADCAST
        await self.event_bus.publish(message)
        return len(self.event_bus._find_matching_subscriptions(message.topic))

    def add_circuit_breaker(
        self,
        service_name: str,
        config: CircuitBreakerConfig = None
    ) -> None:
        """Add circuit breaker for a service."""
        self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)

    def add_rate_limiter(
        self,
        service_name: str,
        config: RateLimitConfig = None
    ) -> None:
        """Add rate limiter for a service."""
        self.rate_limiters[service_name] = RateLimiter(config)


# =============================================================================
# PROTOCOL ADAPTER
# =============================================================================

class ProtocolAdapter(ABC):
    """Base class for protocol adapters."""

    @abstractmethod
    async def send(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to endpoint."""
        pass

    @abstractmethod
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive data."""
        pass


class InternalAdapter(ProtocolAdapter):
    """Adapter for internal communication."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def send(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send via event bus."""
        message = Message(
            topic=endpoint,
            payload=data
        )
        await self.event_bus.publish(message)
        return {"sent": True}

    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive not needed for internal."""
        return None


class HTTPAdapter(ProtocolAdapter):
    """Adapter for HTTP communication."""

    def __init__(self):
        self.session = None  # aiohttp session

    async def send(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send HTTP request."""
        # Placeholder - would use aiohttp
        logger.debug(f"HTTP send to {endpoint}")
        return {"status": "ok"}

    async def receive(self) -> Optional[Dict[str, Any]]:
        """HTTP is request-response, no continuous receive."""
        return None


# =============================================================================
# INTEGRATION LAYER
# =============================================================================

class IntegrationLayer:
    """
    The master integration layer for BAEL.

    Provides unified access to all integration capabilities
    including messaging, state, services, and protocols.
    """

    def __init__(self):
        self.event_bus = EventBus()
        self.state_manager = StateManager(self.event_bus)
        self.service_registry = ServiceRegistry(self.event_bus)
        self.message_router = MessageRouter(self.event_bus, self.service_registry)
        self.protocol_adapters: Dict[ProtocolType, ProtocolAdapter] = {
            ProtocolType.INTERNAL: InternalAdapter(self.event_bus)
        }
        self.component_handlers: Dict[str, Callable] = {}
        self.running = False

    async def start(self) -> None:
        """Start the integration layer."""
        self.running = True
        asyncio.create_task(self.event_bus.start_processing())
        logger.info("Integration Layer started")

    async def stop(self) -> None:
        """Stop the integration layer."""
        self.running = False
        await self.event_bus.stop_processing()
        logger.info("Integration Layer stopped")

    # Messaging
    async def publish(self, topic: str, payload: Dict[str, Any], source: str = "") -> None:
        """Publish an event."""
        await self.event_bus.publish(Message(
            type=MessageType.EVENT,
            topic=topic,
            payload=payload,
            source=source
        ))

    async def subscribe(
        self,
        topic: str,
        handler: Callable[[Message], Awaitable[None]],
        subscriber_id: str = ""
    ) -> str:
        """Subscribe to events."""
        return await self.event_bus.subscribe(topic, handler, subscriber_id)

    async def request(
        self,
        target: str,
        action: str,
        params: Dict[str, Any] = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """Send request and wait for response."""
        message = Message(
            type=MessageType.COMMAND,
            topic=f"{target}.{action}",
            payload=params or {}
        )
        response = await self.message_router.send(target, message, timeout)
        return response.payload if response else None

    async def query(
        self,
        target: str,
        query_name: str,
        params: Dict[str, Any] = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """Query data from a service."""
        message = Message(
            type=MessageType.QUERY,
            topic=f"{target}.query.{query_name}",
            payload=params or {}
        )
        response = await self.message_router.send(target, message, timeout)
        return response.payload if response else None

    # State
    async def get_state(self, key: str, default: Any = None) -> Any:
        """Get shared state."""
        return await self.state_manager.get(key, default)

    async def set_state(self, key: str, value: Any, source: str = "") -> int:
        """Set shared state."""
        return await self.state_manager.set(key, value, source)

    async def watch_state(
        self,
        key: str,
        callback: Callable[[str, Any, Any], Any]
    ) -> str:
        """Watch state changes."""
        return await self.state_manager.watch(key, callback)

    # Services
    async def register_service(self, service: ServiceInfo) -> str:
        """Register a service."""
        return await self.service_registry.register(service)

    async def find_service(self, name: str) -> Optional[ServiceInfo]:
        """Find a service by name."""
        services = await self.service_registry.find_services(name=name)
        return services[0] if services else None

    async def get_services(
        self,
        capability: Optional[str] = None,
        status: Optional[ServiceStatus] = None
    ) -> List[ServiceInfo]:
        """Get services matching criteria."""
        return await self.service_registry.find_services(
            capability=capability,
            status=status
        )

    # Component registration
    def register_component(
        self,
        name: str,
        handler: Callable[[Message], Awaitable[Message]],
        capabilities: List[str] = None
    ) -> None:
        """Register a component as a service."""
        self.component_handlers[name] = handler

        asyncio.create_task(self.service_registry.register(ServiceInfo(
            name=name,
            protocol=ProtocolType.INTERNAL,
            capabilities=capabilities or []
        )))

        # Subscribe to component messages
        asyncio.create_task(self.event_bus.subscribe(
            f"{name}.#",
            self._create_component_wrapper(name, handler),
            name
        ))

    def _create_component_wrapper(
        self,
        name: str,
        handler: Callable[[Message], Awaitable[Message]]
    ) -> Callable[[Message], Awaitable[None]]:
        """Create wrapper for component handler."""
        async def wrapper(message: Message) -> None:
            try:
                response = await handler(message)
                if message.correlation_id:
                    response.topic = f"response.{name}"
                    response.correlation_id = message.correlation_id
                    await self.event_bus.publish(response)
            except Exception as e:
                logger.error(f"Component {name} error: {e}")
                if message.correlation_id:
                    error_response = Message(
                        type=MessageType.RESPONSE,
                        topic=f"response.{name}",
                        payload={"error": str(e)},
                        correlation_id=message.correlation_id
                    )
                    await self.event_bus.publish(error_response)

        return wrapper

    # Health and monitoring
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        services = list(self.service_registry.services.values())

        healthy_count = sum(1 for s in services if s.status == ServiceStatus.HEALTHY)
        unhealthy_count = sum(1 for s in services if s.status == ServiceStatus.UNHEALTHY)

        return {
            "status": "healthy" if unhealthy_count == 0 else "degraded",
            "services": {
                "total": len(services),
                "healthy": healthy_count,
                "unhealthy": unhealthy_count
            },
            "event_bus": {
                "subscriptions": sum(len(s) for s in self.event_bus.subscriptions.values()),
                "pending_messages": self.event_bus.message_queue.qsize(),
                "dead_letters": len(self.event_bus.dead_letter_queue)
            },
            "circuit_breakers": {
                name: cb.state.value
                for name, cb in self.message_router.circuit_breakers.items()
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Integration Layer."""
    print("=" * 70)
    print("BAEL - INTEGRATION LAYER DEMO")
    print("Universal Communication & Integration")
    print("=" * 70)
    print()

    # Create integration layer
    integration = IntegrationLayer()
    await integration.start()

    # 1. Event Bus Demo
    print("1. EVENT BUS:")
    print("-" * 40)

    received_events = []

    async def event_handler(message: Message):
        received_events.append(message)
        print(f"   Received: {message.topic} - {message.payload}")

    # Subscribe to events
    sub_id = await integration.subscribe("test.*", event_handler, "demo_subscriber")
    print(f"   Subscribed: {sub_id[:8]}...")

    # Publish events
    await integration.publish("test.hello", {"message": "Hello BAEL!"}, "demo")
    await integration.publish("test.data", {"value": 42}, "demo")
    await asyncio.sleep(0.1)

    print(f"   Events received: {len(received_events)}")
    print()

    # 2. State Management Demo
    print("2. STATE MANAGEMENT:")
    print("-" * 40)

    # Set state
    version = await integration.set_state("system.mode", "active", "demo")
    print(f"   Set state: system.mode = 'active' (v{version})")

    # Get state
    mode = await integration.get_state("system.mode")
    print(f"   Get state: system.mode = '{mode}'")

    # Watch state changes
    changes = []

    async def state_watcher(key, new_val, old_val):
        changes.append((key, new_val, old_val))

    await integration.watch_state("system.mode", state_watcher)
    await integration.set_state("system.mode", "processing", "demo")
    await asyncio.sleep(0.1)

    print(f"   State changes detected: {len(changes)}")
    print()

    # 3. Service Registry Demo
    print("3. SERVICE REGISTRY:")
    print("-" * 40)

    # Register services
    service1 = ServiceInfo(
        name="reasoning_engine",
        capabilities=["analyze", "plan", "execute"]
    )
    service2 = ServiceInfo(
        name="memory_engine",
        capabilities=["store", "retrieve", "search"]
    )

    await integration.register_service(service1)
    await integration.register_service(service2)

    # Find services
    reasoning = await integration.find_service("reasoning_engine")
    print(f"   Found: {reasoning.name} with {len(reasoning.capabilities)} capabilities")

    all_services = await integration.get_services()
    print(f"   Total services: {len(all_services)}")
    print()

    # 4. Component Registration Demo
    print("4. COMPONENT REGISTRATION:")
    print("-" * 40)

    async def calculator_handler(message: Message) -> Message:
        a = message.payload.get("a", 0)
        b = message.payload.get("b", 0)
        op = message.payload.get("op", "add")

        if op == "add":
            result = a + b
        elif op == "multiply":
            result = a * b
        else:
            result = 0

        return Message(
            type=MessageType.RESPONSE,
            payload={"result": result}
        )

    integration.register_component("calculator", calculator_handler, ["math", "compute"])
    await asyncio.sleep(0.1)
    print("   Registered: calculator component")
    print()

    # 5. Health Status Demo
    print("5. HEALTH STATUS:")
    print("-" * 40)

    health = await integration.get_health_status()
    print(f"   Status: {health['status']}")
    print(f"   Services: {health['services']['total']} total, {health['services']['healthy']} healthy")
    print(f"   Subscriptions: {health['event_bus']['subscriptions']}")
    print()

    # 6. Circuit Breaker Demo
    print("6. CIRCUIT BREAKER:")
    print("-" * 40)

    cb = CircuitBreaker("test_service", CircuitBreakerConfig(failure_threshold=2))

    # Simulate failures
    for i in range(3):
        try:
            async def failing_func():
                raise Exception("Simulated failure")

            await cb.execute(failing_func)
        except Exception as e:
            print(f"   Attempt {i+1}: Failed - {e}")

    print(f"   Circuit state: {cb.state.value}")
    print()

    # 7. Rate Limiter Demo
    print("7. RATE LIMITER:")
    print("-" * 40)

    rl = RateLimiter(RateLimitConfig(requests_per_second=5, burst_size=2))

    acquired = 0
    for i in range(5):
        if await rl.acquire():
            acquired += 1

    print(f"   Acquired {acquired}/5 tokens immediately (burst size: 2)")
    print()

    # Stop integration layer
    await integration.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Integration Layer Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
