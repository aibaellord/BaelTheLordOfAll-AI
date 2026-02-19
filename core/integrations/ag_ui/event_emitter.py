"""
BAEL AG-UI Event Emitter
=========================

Server-Sent Events (SSE) implementation for real-time streaming.
Enables efficient one-way communication from agent to frontend.

Features:
- SSE standard compliance
- Event type filtering
- Automatic reconnection support
- Event ID tracking
- Backpressure handling
- Connection keep-alive
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Standard AG-UI event types."""
    # Lifecycle events
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"

    # Message events
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"

    # Tool events
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"

    # State events
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"
    MESSAGES_SNAPSHOT = "MESSAGES_SNAPSHOT"

    # Step events
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"

    # Raw events
    RAW = "RAW"
    CUSTOM = "CUSTOM"


@dataclass
class ServerSentEvent:
    """A server-sent event."""
    event: EventType
    data: Any
    id: Optional[str] = None
    retry: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def serialize(self) -> str:
        """Serialize to SSE format."""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        lines.append(f"event: {self.event.value}")

        if isinstance(self.data, dict):
            data_str = json.dumps(self.data)
        else:
            data_str = str(self.data)

        # Handle multi-line data
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")

        if self.retry:
            lines.append(f"retry: {self.retry}")

        return "\n".join(lines) + "\n\n"


class EventEmitter:
    """
    SSE-based event emitter for AG-UI protocol.
    """

    def __init__(
        self,
        keep_alive_interval: int = 15,
        max_queue_size: int = 1000,
        enable_compression: bool = False,
    ):
        self.keep_alive_interval = keep_alive_interval
        self.max_queue_size = max_queue_size
        self.enable_compression = enable_compression

        # Event tracking
        self.event_counter = 0
        self.last_event_id: Optional[str] = None

        # Queues for multiple subscribers
        self.subscribers: Dict[str, asyncio.Queue] = {}

        # Event history (for replay)
        self.event_history: List[ServerSentEvent] = []
        self.max_history_size = 100

        # Callbacks
        self.event_callbacks: Dict[EventType, List[Callable]] = {}

        # Running state
        self._running = False

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        self.event_counter += 1
        return f"evt_{int(time.time() * 1000)}_{self.event_counter}"

    async def emit(
        self,
        event_type: EventType,
        data: Any,
        event_id: Optional[str] = None,
    ) -> ServerSentEvent:
        """
        Emit an event to all subscribers.

        Args:
            event_type: Type of event
            data: Event data
            event_id: Optional custom event ID

        Returns:
            The emitted event
        """
        event_id = event_id or self._generate_event_id()

        event = ServerSentEvent(
            event=event_type,
            data=data,
            id=event_id,
        )

        self.last_event_id = event_id

        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)

        # Notify subscribers
        for subscriber_id, queue in list(self.subscribers.items()):
            try:
                if queue.qsize() < self.max_queue_size:
                    await queue.put(event)
                else:
                    logger.warning(f"Subscriber {subscriber_id} queue full, dropping event")
            except Exception as e:
                logger.error(f"Error sending to subscriber {subscriber_id}: {e}")

        # Fire callbacks
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

        return event

    async def emit_run_started(
        self,
        run_id: str,
        thread_id: Optional[str] = None,
    ) -> ServerSentEvent:
        """Emit run started event."""
        return await self.emit(
            EventType.RUN_STARTED,
            {
                "runId": run_id,
                "threadId": thread_id,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def emit_run_finished(
        self,
        run_id: str,
    ) -> ServerSentEvent:
        """Emit run finished event."""
        return await self.emit(
            EventType.RUN_FINISHED,
            {
                "runId": run_id,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def emit_run_error(
        self,
        run_id: str,
        error: str,
        code: Optional[str] = None,
    ) -> ServerSentEvent:
        """Emit run error event."""
        return await self.emit(
            EventType.RUN_ERROR,
            {
                "runId": run_id,
                "error": error,
                "code": code,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def emit_text_start(
        self,
        message_id: str,
        role: str = "assistant",
    ) -> ServerSentEvent:
        """Emit text message start."""
        return await self.emit(
            EventType.TEXT_MESSAGE_START,
            {
                "messageId": message_id,
                "role": role,
            },
        )

    async def emit_text_content(
        self,
        message_id: str,
        content: str,
    ) -> ServerSentEvent:
        """Emit text message content chunk."""
        return await self.emit(
            EventType.TEXT_MESSAGE_CONTENT,
            {
                "messageId": message_id,
                "delta": content,
            },
        )

    async def emit_text_end(
        self,
        message_id: str,
    ) -> ServerSentEvent:
        """Emit text message end."""
        return await self.emit(
            EventType.TEXT_MESSAGE_END,
            {
                "messageId": message_id,
            },
        )

    async def emit_tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        message_id: Optional[str] = None,
    ) -> ServerSentEvent:
        """Emit tool call start."""
        return await self.emit(
            EventType.TOOL_CALL_START,
            {
                "toolCallId": tool_call_id,
                "toolName": tool_name,
                "messageId": message_id,
            },
        )

    async def emit_tool_call_args(
        self,
        tool_call_id: str,
        args_delta: str,
    ) -> ServerSentEvent:
        """Emit tool call arguments chunk."""
        return await self.emit(
            EventType.TOOL_CALL_ARGS,
            {
                "toolCallId": tool_call_id,
                "delta": args_delta,
            },
        )

    async def emit_tool_call_end(
        self,
        tool_call_id: str,
    ) -> ServerSentEvent:
        """Emit tool call end."""
        return await self.emit(
            EventType.TOOL_CALL_END,
            {
                "toolCallId": tool_call_id,
            },
        )

    async def emit_state_snapshot(
        self,
        state: Dict[str, Any],
    ) -> ServerSentEvent:
        """Emit full state snapshot."""
        return await self.emit(
            EventType.STATE_SNAPSHOT,
            {
                "state": state,
            },
        )

    async def emit_state_delta(
        self,
        delta: List[Dict[str, Any]],
    ) -> ServerSentEvent:
        """Emit state delta (JSON Patch format)."""
        return await self.emit(
            EventType.STATE_DELTA,
            {
                "delta": delta,
            },
        )

    def subscribe(self, subscriber_id: Optional[str] = None) -> str:
        """
        Subscribe to events.

        Args:
            subscriber_id: Optional subscriber ID

        Returns:
            Subscriber ID
        """
        subscriber_id = subscriber_id or f"sub_{int(time.time() * 1000)}"
        self.subscribers[subscriber_id] = asyncio.Queue()
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> bool:
        """Unsubscribe from events."""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            return True
        return False

    async def stream(
        self,
        subscriber_id: str,
        last_event_id: Optional[str] = None,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """
        Stream events to a subscriber.

        Args:
            subscriber_id: Subscriber ID
            last_event_id: Last received event ID for replay

        Yields:
            ServerSentEvent objects
        """
        if subscriber_id not in self.subscribers:
            raise ValueError(f"Unknown subscriber: {subscriber_id}")

        queue = self.subscribers[subscriber_id]

        # Replay missed events if requested
        if last_event_id:
            replay = False
            for event in self.event_history:
                if event.id == last_event_id:
                    replay = True
                    continue
                if replay:
                    yield event

        # Stream new events
        while subscriber_id in self.subscribers:
            try:
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=self.keep_alive_interval,
                )
                yield event
            except asyncio.TimeoutError:
                # Send keep-alive comment
                yield ServerSentEvent(
                    event=EventType.RAW,
                    data=": keep-alive",
                )

    def on_event(
        self,
        event_type: EventType,
        callback: Callable,
    ) -> None:
        """Register callback for event type."""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get emitter statistics."""
        return {
            "total_events": self.event_counter,
            "subscribers": len(self.subscribers),
            "history_size": len(self.event_history),
            "last_event_id": self.last_event_id,
        }


def demo():
    """Demonstrate event emitter."""
    print("=" * 60)
    print("BAEL AG-UI Event Emitter Demo")
    print("=" * 60)

    emitter = EventEmitter()

    # Create a test event
    event = ServerSentEvent(
        event=EventType.TEXT_MESSAGE_CONTENT,
        data={"messageId": "msg-1", "delta": "Hello, "},
        id="evt-1",
    )

    print(f"\nSerialized event:")
    print(event.serialize())

    print(f"\nEmitter stats: {emitter.get_stats()}")


if __name__ == "__main__":
    demo()
