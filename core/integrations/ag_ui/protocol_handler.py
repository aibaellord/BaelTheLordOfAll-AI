"""
BAEL AG-UI Protocol Handler
============================

Main protocol handler for AG-UI integration.
Coordinates all AG-UI components for seamless agent-UI communication.

Features:
- Full AG-UI protocol implementation
- FastAPI/Starlette integration
- WebSocket support
- HTTP SSE endpoints
- Request/response handling
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

from .agent_session import AgentSession, Run, SessionConfig, SessionState
# Local imports
from .event_emitter import EventEmitter, EventType, ServerSentEvent
from .message_types import (AgentMessage, MessageRole, StreamChunk,
                            SystemMessage, ToolCall, ToolResult, UserMessage)
from .state_sync import OperationType, StateChange, StateSync, SyncStrategy


class ProtocolVersion(Enum):
    """AG-UI Protocol versions."""
    V1 = "1.0"
    V1_1 = "1.1"


@dataclass
class AGUIRequest:
    """Incoming AG-UI request."""
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    state: Optional[Dict[str, Any]] = None
    tools: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AGUIConfig:
    """AG-UI handler configuration."""
    version: ProtocolVersion = ProtocolVersion.V1_1

    # Streaming
    enable_streaming: bool = True
    chunk_size: int = 1  # Characters per chunk
    chunk_delay_ms: int = 10

    # State
    enable_state_sync: bool = True
    sync_strategy: SyncStrategy = SyncStrategy.DELTA

    # Session
    session_timeout: int = 3600
    max_sessions: int = 1000


class AGUIProtocolHandler:
    """
    Main AG-UI protocol handler.
    Integrates event emitting, sessions, and state sync.
    """

    def __init__(
        self,
        config: Optional[AGUIConfig] = None,
        agent_callback: Optional[Callable] = None,
    ):
        self.config = config or AGUIConfig()
        self.agent_callback = agent_callback

        # Sessions
        self.sessions: Dict[str, AgentSession] = {}

        # Event emitters per session
        self.emitters: Dict[str, EventEmitter] = {}

        # State sync per session
        self.state_syncs: Dict[str, StateSync] = {}

        # Tool handlers
        self.tool_handlers: Dict[str, Callable] = {}

    def _get_or_create_session(
        self,
        session_id: Optional[str] = None,
    ) -> AgentSession:
        """Get or create a session."""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        session = AgentSession(
            session_id=session_id,
            config=SessionConfig(
                idle_timeout_seconds=self.config.session_timeout,
            ),
        )

        self.sessions[session.id] = session
        self.emitters[session.id] = EventEmitter()
        self.state_syncs[session.id] = StateSync(
            strategy=self.config.sync_strategy,
        )

        return session

    def register_tool(
        self,
        name: str,
        handler: Callable,
    ) -> None:
        """Register a tool handler."""
        self.tool_handlers[name] = handler

    async def handle_request(
        self,
        request: AGUIRequest,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """
        Handle an AG-UI request and stream responses.

        Args:
            request: Incoming request

        Yields:
            ServerSentEvent objects
        """
        # Get or create session
        session = self._get_or_create_session()
        emitter = self.emitters[session.id]
        state_sync = self.state_syncs[session.id]

        # Create thread if needed
        thread_id = request.thread_id
        if not thread_id:
            thread = session.create_thread()
            thread_id = thread.id

        # Start run
        run = session.start_run()

        # Emit run started
        yield await emitter.emit_run_started(run.id, thread_id)

        # Add user messages to thread
        for msg in request.messages:
            if msg.get("role") == "user":
                session.add_message(
                    role="user",
                    content=msg.get("content", ""),
                    thread_id=thread_id,
                )

        # Sync initial state
        if request.state:
            state_sync.set_state(request.state, notify=False)
            yield await emitter.emit_state_snapshot(request.state)

        try:
            # Process with agent
            if self.agent_callback:
                async for event in self._process_with_agent(
                    session, run, request, emitter, state_sync
                ):
                    yield event
            else:
                # Demo mode: echo back
                async for event in self._demo_response(
                    session, run, request, emitter
                ):
                    yield event

            # Finish run
            session.finish_run()
            yield await emitter.emit_run_finished(run.id)

        except Exception as e:
            logger.error(f"Run error: {e}")
            session.finish_run(error=str(e))
            yield await emitter.emit_run_error(run.id, str(e))

    async def _process_with_agent(
        self,
        session: AgentSession,
        run: Run,
        request: AGUIRequest,
        emitter: EventEmitter,
        state_sync: StateSync,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Process request with agent callback."""

        # Get thread context
        thread = session.get_thread()
        messages = thread.get_context() if thread else request.messages

        # Call agent
        try:
            result = await self.agent_callback(
                messages=messages,
                tools=request.tools,
                config=request.config,
            )

            # Stream response
            if isinstance(result, str):
                # Simple string response
                message_id = f"msg_{uuid.uuid4().hex[:12]}"

                yield await emitter.emit_text_start(message_id, "assistant")

                # Stream chunks
                for i, char in enumerate(result):
                    yield await emitter.emit_text_content(message_id, char)
                    if self.config.chunk_delay_ms > 0:
                        await asyncio.sleep(self.config.chunk_delay_ms / 1000)

                yield await emitter.emit_text_end(message_id)

                # Add to session
                session.add_message("assistant", result)

            elif isinstance(result, dict):
                # Structured response with possible tool calls
                content = result.get("content", "")
                tool_calls = result.get("tool_calls", [])

                message_id = f"msg_{uuid.uuid4().hex[:12]}"

                # Stream content
                if content:
                    yield await emitter.emit_text_start(message_id, "assistant")

                    for char in content:
                        yield await emitter.emit_text_content(message_id, char)
                        if self.config.chunk_delay_ms > 0:
                            await asyncio.sleep(self.config.chunk_delay_ms / 1000)

                    yield await emitter.emit_text_end(message_id)

                # Handle tool calls
                for tc in tool_calls:
                    async for event in self._handle_tool_call(
                        tc, emitter, message_id
                    ):
                        yield event

        except Exception as e:
            logger.error(f"Agent callback error: {e}")
            raise

    async def _handle_tool_call(
        self,
        tool_call: Dict[str, Any],
        emitter: EventEmitter,
        message_id: str,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Handle a tool call."""
        tool_call_id = tool_call.get("id", f"tc_{uuid.uuid4().hex[:8]}")
        tool_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})

        # Emit tool call start
        yield await emitter.emit_tool_call_start(tool_call_id, tool_name, message_id)

        # Stream arguments
        args_str = json.dumps(arguments)
        for char in args_str:
            yield await emitter.emit_tool_call_args(tool_call_id, char)

        # Execute tool if handler exists
        if tool_name in self.tool_handlers:
            try:
                handler = self.tool_handlers[tool_name]
                result = await handler(**arguments)

                # Could emit tool result here if needed

            except Exception as e:
                logger.error(f"Tool execution error: {e}")

        yield await emitter.emit_tool_call_end(tool_call_id)

    async def _demo_response(
        self,
        session: AgentSession,
        run: Run,
        request: AGUIRequest,
        emitter: EventEmitter,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Demo response for testing."""
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        yield await emitter.emit_text_start(message_id, "assistant")

        demo_text = "Hello! I'm BAEL, your AI assistant. This is a demo response streaming via the AG-UI protocol."

        for char in demo_text:
            yield await emitter.emit_text_content(message_id, char)
            await asyncio.sleep(0.02)

        yield await emitter.emit_text_end(message_id)

        session.add_message("assistant", demo_text)

    async def stream_events(
        self,
        session_id: str,
        last_event_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream events as SSE format for HTTP endpoint.

        Args:
            session_id: Session ID
            last_event_id: Last received event ID

        Yields:
            SSE formatted strings
        """
        if session_id not in self.emitters:
            return

        emitter = self.emitters[session_id]
        subscriber_id = emitter.subscribe()

        try:
            async for event in emitter.stream(subscriber_id, last_event_id):
                yield event.serialize()
        finally:
            emitter.unsubscribe(subscriber_id)

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired()
        ]

        for sid in expired:
            del self.sessions[sid]
            if sid in self.emitters:
                del self.emitters[sid]
            if sid in self.state_syncs:
                del self.state_syncs[sid]

        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            "protocol_version": self.config.version.value,
            "active_sessions": len(self.sessions),
            "registered_tools": list(self.tool_handlers.keys()),
            "sessions": {
                sid: session.get_summary()
                for sid, session in self.sessions.items()
            },
        }


def demo():
    """Demonstrate AG-UI protocol handler."""
    print("=" * 60)
    print("BAEL AG-UI Protocol Handler Demo")
    print("=" * 60)

    handler = AGUIProtocolHandler()

    # Register a demo tool
    async def demo_tool(query: str):
        return f"Searched for: {query}"

    handler.register_tool("search", demo_tool)

    print(f"\nHandler stats: {handler.get_stats()}")

    # Create a session
    session = handler._get_or_create_session()
    print(f"\nCreated session: {session.id}")

    print(f"\nUpdated stats: {handler.get_stats()}")


if __name__ == "__main__":
    demo()
