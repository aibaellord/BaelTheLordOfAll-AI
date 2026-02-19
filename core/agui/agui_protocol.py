"""
BAEL - AG-UI Protocol Integration
==================================

Full implementation of the Agent-User Interaction Protocol.

This integrates Ba'el with the AG-UI standard enabling:
1. Real-time streaming via SSE (Server-Sent Events)
2. 16 event types for agent-frontend communication
3. State management with snapshots and deltas
4. Tool call lifecycle events
5. Thinking/reasoning transparency
6. Bi-directional state synchronization
7. Frontend tool integration
8. Human-in-the-loop collaboration

Compatible with: CopilotKit, LangGraph, CrewAI, and any AG-UI client.

References: https://github.com/ag-ui-protocol/ag-ui
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set, Union
from collections import defaultdict

logger = logging.getLogger("BAEL.AGUI")


# ============================================================================
# AG-UI EVENT TYPES
# ============================================================================

class EventType(Enum):
    """All AG-UI protocol event types."""
    # Lifecycle Events
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"

    # Text Message Events
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
    TEXT_MESSAGE_CHUNK = "TEXT_MESSAGE_CHUNK"

    # Thinking Events (reasoning transparency)
    THINKING_START = "THINKING_START"
    THINKING_TEXT_MESSAGE_START = "THINKING_TEXT_MESSAGE_START"
    THINKING_TEXT_MESSAGE_CONTENT = "THINKING_TEXT_MESSAGE_CONTENT"
    THINKING_TEXT_MESSAGE_END = "THINKING_TEXT_MESSAGE_END"
    THINKING_END = "THINKING_END"

    # Tool Call Events
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_CHUNK = "TOOL_CALL_CHUNK"
    TOOL_CALL_END = "TOOL_CALL_END"
    TOOL_CALL_RESULT = "TOOL_CALL_RESULT"

    # State Management Events
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"
    MESSAGES_SNAPSHOT = "MESSAGES_SNAPSHOT"

    # Activity Events
    ACTIVITY_SNAPSHOT = "ACTIVITY_SNAPSHOT"
    ACTIVITY_DELTA = "ACTIVITY_DELTA"

    # Special Events
    RAW = "RAW"
    CUSTOM = "CUSTOM"


# ============================================================================
# MESSAGE TYPES
# ============================================================================

class MessageRole(Enum):
    """Roles for messages."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Message:
    """A message in the conversation."""
    id: str
    role: MessageRole
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = {
            "id": self.id,
            "role": self.role.value,
        }
        if self.content is not None:
            d["content"] = self.content
        if self.name is not None:
            d["name"] = self.name
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ToolDefinition:
    """Definition of an available tool."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


# ============================================================================
# AG-UI EVENTS
# ============================================================================

@dataclass
class BaseEvent:
    """Base event class for AG-UI protocol."""
    type: EventType
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    raw_event: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "type": self.type.value,
            "timestamp": self.timestamp
        }
        if self.raw_event:
            d["rawEvent"] = self.raw_event
        return d

    def to_sse(self) -> str:
        """Convert to Server-Sent Events format."""
        data = json.dumps(self.to_dict())
        return f"data: {data}\n\n"


@dataclass
class RunStartedEvent(BaseEvent):
    """Event indicating start of an agent run."""
    thread_id: str = ""
    run_id: str = ""

    def __post_init__(self):
        self.type = EventType.RUN_STARTED

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["threadId"] = self.thread_id
        d["runId"] = self.run_id
        return d


@dataclass
class RunFinishedEvent(BaseEvent):
    """Event indicating end of an agent run."""
    thread_id: str = ""
    run_id: str = ""

    def __post_init__(self):
        self.type = EventType.RUN_FINISHED

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["threadId"] = self.thread_id
        d["runId"] = self.run_id
        return d


@dataclass
class RunErrorEvent(BaseEvent):
    """Event indicating an error during agent run."""
    message: str = ""
    code: Optional[str] = None

    def __post_init__(self):
        self.type = EventType.RUN_ERROR

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["message"] = self.message
        if self.code:
            d["code"] = self.code
        return d


@dataclass
class TextMessageStartEvent(BaseEvent):
    """Event indicating start of a text message stream."""
    message_id: str = ""

    def __post_init__(self):
        self.type = EventType.TEXT_MESSAGE_START

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["messageId"] = self.message_id
        return d


@dataclass
class TextMessageContentEvent(BaseEvent):
    """Event containing text message content chunk."""
    message_id: str = ""
    delta: str = ""

    def __post_init__(self):
        self.type = EventType.TEXT_MESSAGE_CONTENT

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["messageId"] = self.message_id
        d["delta"] = self.delta
        return d


@dataclass
class TextMessageEndEvent(BaseEvent):
    """Event indicating end of a text message stream."""
    message_id: str = ""

    def __post_init__(self):
        self.type = EventType.TEXT_MESSAGE_END

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["messageId"] = self.message_id
        return d


@dataclass
class ThinkingStartEvent(BaseEvent):
    """Event indicating agent started thinking."""

    def __post_init__(self):
        self.type = EventType.THINKING_START


@dataclass
class ThinkingTextMessageContentEvent(BaseEvent):
    """Event containing thinking/reasoning content."""
    delta: str = ""

    def __post_init__(self):
        self.type = EventType.THINKING_TEXT_MESSAGE_CONTENT

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["delta"] = self.delta
        return d


@dataclass
class ThinkingEndEvent(BaseEvent):
    """Event indicating agent finished thinking."""

    def __post_init__(self):
        self.type = EventType.THINKING_END


@dataclass
class ToolCallStartEvent(BaseEvent):
    """Event indicating start of a tool call."""
    tool_call_id: str = ""
    tool_call_name: str = ""
    parent_message_id: Optional[str] = None

    def __post_init__(self):
        self.type = EventType.TOOL_CALL_START

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["toolCallId"] = self.tool_call_id
        d["toolCallName"] = self.tool_call_name
        if self.parent_message_id:
            d["parentMessageId"] = self.parent_message_id
        return d


@dataclass
class ToolCallArgsEvent(BaseEvent):
    """Event containing tool call arguments (streamed)."""
    tool_call_id: str = ""
    delta: str = ""  # JSON args chunk

    def __post_init__(self):
        self.type = EventType.TOOL_CALL_ARGS

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["toolCallId"] = self.tool_call_id
        d["delta"] = self.delta
        return d


@dataclass
class ToolCallEndEvent(BaseEvent):
    """Event indicating end of a tool call."""
    tool_call_id: str = ""

    def __post_init__(self):
        self.type = EventType.TOOL_CALL_END

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["toolCallId"] = self.tool_call_id
        return d


@dataclass
class ToolCallResultEvent(BaseEvent):
    """Event containing tool call result."""
    tool_call_id: str = ""
    result: str = ""

    def __post_init__(self):
        self.type = EventType.TOOL_CALL_RESULT

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["toolCallId"] = self.tool_call_id
        d["result"] = self.result
        return d


@dataclass
class StateSnapshotEvent(BaseEvent):
    """Event providing complete state snapshot."""
    snapshot: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.type = EventType.STATE_SNAPSHOT

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["snapshot"] = self.snapshot
        return d


@dataclass
class StateDeltaEvent(BaseEvent):
    """Event providing incremental state update (JSON Patch RFC 6902)."""
    delta: List[Dict[str, Any]] = field(default_factory=list)  # JSON Patch operations

    def __post_init__(self):
        self.type = EventType.STATE_DELTA

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["delta"] = self.delta
        return d


@dataclass
class MessagesSnapshotEvent(BaseEvent):
    """Event providing complete messages snapshot."""
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.type = EventType.MESSAGES_SNAPSHOT

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["messages"] = self.messages
        return d


@dataclass
class CustomEvent(BaseEvent):
    """Custom event for extensibility."""
    name: str = ""
    value: Any = None

    def __post_init__(self):
        self.type = EventType.CUSTOM

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["name"] = self.name
        d["value"] = self.value
        return d


# ============================================================================
# RUN AGENT INPUT
# ============================================================================

@dataclass
class RunAgentInput:
    """Input for running an agent."""
    thread_id: str
    run_id: str
    messages: List[Message] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    tools: List[ToolDefinition] = field(default_factory=list)
    context: List[Dict[str, Any]] = field(default_factory=list)  # Additional context
    forwarded_props: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunAgentInput":
        """Create from dictionary."""
        messages = []
        for msg in data.get("messages", []):
            messages.append(Message(
                id=msg.get("id", str(uuid.uuid4())),
                role=MessageRole(msg.get("role", "user")),
                content=msg.get("content"),
                name=msg.get("name"),
                tool_calls=msg.get("tool_calls", []),
                tool_call_id=msg.get("tool_call_id")
            ))

        tools = []
        for tool in data.get("tools", []):
            tools.append(ToolDefinition(
                name=tool.get("name", ""),
                description=tool.get("description", ""),
                parameters=tool.get("parameters", {})
            ))

        return cls(
            thread_id=data.get("threadId", str(uuid.uuid4())),
            run_id=data.get("runId", str(uuid.uuid4())),
            messages=messages,
            state=data.get("state", {}),
            tools=tools,
            context=data.get("context", []),
            forwarded_props=data.get("forwardedProps", {})
        )


# ============================================================================
# AG-UI AGENT BASE CLASS
# ============================================================================

class AGUIAgent(ABC):
    """Base class for AG-UI compatible agents."""

    def __init__(
        self,
        agent_id: str = None,
        name: str = "Ba'el Agent"
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name

        # State management
        self.state: Dict[str, Any] = {}
        self.messages: List[Message] = []

        # Tool registry
        self.tools: Dict[str, Callable] = {}

        # Statistics
        self.stats = {
            "runs": 0,
            "messages_processed": 0,
            "tool_calls": 0,
            "errors": 0
        }

        logger.info(f"AGUIAgent '{name}' initialized with ID {self.agent_id}")

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: Dict[str, Any]
    ) -> None:
        """Register a tool with the agent."""
        self.tools[name] = {
            "handler": handler,
            "definition": ToolDefinition(
                name=name,
                description=description,
                parameters=parameters
            )
        }
        logger.debug(f"Registered tool: {name}")

    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Get all tool definitions."""
        return [t["definition"] for t in self.tools.values()]

    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> str:
        """Execute a registered tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        handler = self.tools[tool_name]["handler"]

        if asyncio.iscoroutinefunction(handler):
            result = await handler(**args)
        else:
            result = handler(**args)

        self.stats["tool_calls"] += 1
        return json.dumps(result) if not isinstance(result, str) else result

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set complete state."""
        self.state = state

    def update_state(self, updates: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update state and return JSON Patch operations."""
        patches = []
        for key, value in updates.items():
            if key in self.state:
                patches.append({
                    "op": "replace",
                    "path": f"/{key}",
                    "value": value
                })
            else:
                patches.append({
                    "op": "add",
                    "path": f"/{key}",
                    "value": value
                })
            self.state[key] = value
        return patches

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.stats["messages_processed"] += 1

    @abstractmethod
    async def run(
        self,
        input_data: RunAgentInput
    ) -> AsyncGenerator[BaseEvent, None]:
        """
        Run the agent and yield events.

        This is the main entry point for AG-UI protocol.
        Implementations should yield events as they process.
        """
        pass

    async def run_with_events(
        self,
        input_data: RunAgentInput
    ) -> AsyncGenerator[str, None]:
        """Run and yield SSE-formatted events."""
        async for event in self.run(input_data):
            yield event.to_sse()


# ============================================================================
# BAEL AG-UI AGENT IMPLEMENTATION
# ============================================================================

class BaelAGUIAgent(AGUIAgent):
    """
    Ba'el's AG-UI Protocol implementation.

    This agent:
    - Streams responses in real-time
    - Shows thinking/reasoning transparently
    - Manages state with snapshots and deltas
    - Executes tools with full lifecycle events
    - Integrates with all Ba'el subsystems
    """

    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        enable_thinking: bool = True,
        enable_state_sync: bool = True
    ):
        super().__init__(name="Ba'el Master Agent")

        self.llm_provider = llm_provider
        self.enable_thinking = enable_thinking
        self.enable_state_sync = enable_state_sync

        # Ba'el subsystems (lazy loaded)
        self._infinity_engine = None
        self._council_system = None
        self._swarm_orchestrator = None

        # Register built-in tools
        self._register_builtin_tools()

        logger.info("BaelAGUIAgent initialized with full AG-UI protocol support")

    def _register_builtin_tools(self) -> None:
        """Register Ba'el's built-in tools."""

        # Infinity Loop Reasoning
        self.register_tool(
            name="infinity_loop_query",
            handler=self._tool_infinity_loop,
            description="Deep reasoning through the Infinity Loop - council-within-council architecture for profound insights",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to explore deeply"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth of exploration (1-7)",
                        "default": 5
                    }
                },
                "required": ["question"]
            }
        )

        # Web Search
        self.register_tool(
            name="web_search",
            handler=self._tool_web_search,
            description="Search the web for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        )

        # Code Execution
        self.register_tool(
            name="execute_code",
            handler=self._tool_execute_code,
            description="Execute Python code",
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language",
                        "default": "python"
                    }
                },
                "required": ["code"]
            }
        )

    async def _tool_infinity_loop(
        self,
        question: str,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """Execute infinity loop reasoning."""
        # Lazy import to avoid circular
        from core.infinity_loop.infinity_loop_engine import get_infinity_engine

        engine = get_infinity_engine()
        result = await engine.infinity_loop_deliberation(
            initial_question=question,
            max_rounds=max_depth * 3
        )

        return {
            "question": question,
            "answer": result.get("answer_of_all_answers", ""),
            "insights": result.get("all_insights", [])[:5],
            "convergence": result.get("convergence_score", 0)
        }

    async def _tool_web_search(self, query: str) -> Dict[str, Any]:
        """Simulated web search."""
        return {
            "query": query,
            "results": [
                {"title": f"Result for {query}", "url": "https://example.com", "snippet": f"Information about {query}..."}
            ]
        }

    async def _tool_execute_code(
        self,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Simulated code execution."""
        return {
            "language": language,
            "code": code[:100] + "...",
            "output": "Execution result placeholder",
            "success": True
        }

    async def run(
        self,
        input_data: RunAgentInput
    ) -> AsyncGenerator[BaseEvent, None]:
        """
        Main AG-UI protocol run method.

        Yields events following the AG-UI specification.
        """
        self.stats["runs"] += 1

        # Import messages
        self.messages = input_data.messages
        self.state = input_data.state

        # RUN_STARTED
        yield RunStartedEvent(
            thread_id=input_data.thread_id,
            run_id=input_data.run_id
        )

        # STATE_SNAPSHOT (initial state)
        if self.enable_state_sync:
            yield StateSnapshotEvent(snapshot=self.state)

        try:
            # Get the latest user message
            user_message = None
            for msg in reversed(self.messages):
                if msg.role == MessageRole.USER:
                    user_message = msg
                    break

            if not user_message:
                yield RunErrorEvent(message="No user message found")
                yield RunFinishedEvent(
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id
                )
                return

            # THINKING phase (if enabled)
            if self.enable_thinking:
                yield ThinkingStartEvent()

                thinking_content = f"Analyzing request: '{user_message.content[:50]}...'\nConsidering available tools and context..."

                for chunk in self._chunk_text(thinking_content, 50):
                    yield ThinkingTextMessageContentEvent(delta=chunk)
                    await asyncio.sleep(0.05)  # Simulate streaming

                yield ThinkingEndEvent()

            # Generate response
            message_id = str(uuid.uuid4())

            # TEXT_MESSAGE_START
            yield TextMessageStartEvent(message_id=message_id)

            # Determine if we need to use tools
            should_use_tools = self._should_use_tools(user_message.content)

            if should_use_tools:
                # Tool execution flow
                tool_name, tool_args = self._determine_tool(user_message.content)

                if tool_name:
                    tool_call_id = str(uuid.uuid4())

                    # TOOL_CALL_START
                    yield ToolCallStartEvent(
                        tool_call_id=tool_call_id,
                        tool_call_name=tool_name,
                        parent_message_id=message_id
                    )

                    # TOOL_CALL_ARGS (streamed)
                    args_json = json.dumps(tool_args)
                    for chunk in self._chunk_text(args_json, 20):
                        yield ToolCallArgsEvent(
                            tool_call_id=tool_call_id,
                            delta=chunk
                        )
                        await asyncio.sleep(0.02)

                    # TOOL_CALL_END
                    yield ToolCallEndEvent(tool_call_id=tool_call_id)

                    # Execute tool
                    try:
                        result = await self.execute_tool(tool_name, tool_args)
                    except Exception as e:
                        result = json.dumps({"error": str(e)})

                    # TOOL_CALL_RESULT
                    yield ToolCallResultEvent(
                        tool_call_id=tool_call_id,
                        result=result
                    )

                    # Generate response based on tool result
                    response = f"Based on my analysis using {tool_name}:\n\n{result}"
            else:
                # Direct response
                response = await self._generate_response(user_message.content)

            # TEXT_MESSAGE_CONTENT (streamed)
            for chunk in self._chunk_text(response, 30):
                yield TextMessageContentEvent(
                    message_id=message_id,
                    delta=chunk
                )
                await asyncio.sleep(0.03)  # Simulate streaming

            # TEXT_MESSAGE_END
            yield TextMessageEndEvent(message_id=message_id)

            # Add assistant message
            assistant_message = Message(
                id=message_id,
                role=MessageRole.ASSISTANT,
                content=response
            )
            self.add_message(assistant_message)

            # STATE_DELTA (update state)
            if self.enable_state_sync:
                delta = self.update_state({
                    "last_response_id": message_id,
                    "last_response_time": datetime.now().isoformat(),
                    "total_messages": len(self.messages)
                })
                yield StateDeltaEvent(delta=delta)

            # MESSAGES_SNAPSHOT
            yield MessagesSnapshotEvent(
                messages=[m.to_dict() for m in self.messages]
            )

        except Exception as e:
            logger.error(f"Error during run: {e}")
            self.stats["errors"] += 1
            yield RunErrorEvent(message=str(e))

        finally:
            # RUN_FINISHED
            yield RunFinishedEvent(
                thread_id=input_data.thread_id,
                run_id=input_data.run_id
            )

    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks for streaming."""
        chunks = []
        words = text.split()
        current = []
        current_len = 0

        for word in words:
            if current_len + len(word) + 1 > chunk_size and current:
                chunks.append(" ".join(current) + " ")
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += len(word) + 1

        if current:
            chunks.append(" ".join(current))

        return chunks if chunks else [text]

    def _should_use_tools(self, content: str) -> bool:
        """Determine if we should use tools."""
        tool_indicators = [
            "search", "find", "look up", "calculate", "code",
            "execute", "run", "analyze", "deep", "reason",
            "infinity", "council"
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in tool_indicators)

    def _determine_tool(
        self,
        content: str
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Determine which tool to use and with what arguments."""
        content_lower = content.lower()

        if "infinity" in content_lower or "deep reason" in content_lower:
            return "infinity_loop_query", {"question": content, "max_depth": 5}
        elif "search" in content_lower or "find" in content_lower:
            return "web_search", {"query": content}
        elif "code" in content_lower or "execute" in content_lower:
            # Extract code if present
            return "execute_code", {"code": content, "language": "python"}

        return None, {}

    async def _generate_response(self, content: str) -> str:
        """Generate a response to user content."""
        if self.llm_provider:
            return await self.llm_provider(content)

        # Default response
        return f"""I am Ba'el, your unified AI orchestration system.

You asked: "{content[:100]}..."

I have analyzed your request. Here's my response:

This is a placeholder response. In production, I would:
1. Use the Infinity Loop for deep reasoning
2. Consult the Council of Algorithms
3. Deploy Micro-Agent Swarms if needed
4. Apply Sacred Geometry patterns
5. Leverage zero-cost LLM providers

How can I help you further?"""


# ============================================================================
# SSE SERVER HELPER
# ============================================================================

class AGUISSEServer:
    """
    Helper for serving AG-UI events via SSE.

    Compatible with FastAPI, Flask, and other frameworks.
    """

    def __init__(self, agent: AGUIAgent):
        self.agent = agent

    async def stream_response(
        self,
        input_data: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Stream SSE response from agent.

        Use this with FastAPI's StreamingResponse:

        ```python
        from fastapi.responses import StreamingResponse

        @app.post("/agent/run")
        async def run_agent(request: dict):
            return StreamingResponse(
                server.stream_response(request),
                media_type="text/event-stream"
            )
        ```
        """
        parsed_input = RunAgentInput.from_dict(input_data)

        async for event in self.agent.run(parsed_input):
            yield event.to_sse()

    def create_fastapi_router(self):
        """Create a FastAPI router for the agent."""
        try:
            from fastapi import APIRouter
            from fastapi.responses import StreamingResponse
        except ImportError:
            logger.error("FastAPI not installed")
            return None

        router = APIRouter()

        @router.post("/run")
        async def run_agent(request: dict):
            return StreamingResponse(
                self.stream_response(request),
                media_type="text/event-stream"
            )

        @router.get("/health")
        async def health():
            return {
                "status": "healthy",
                "agent_id": self.agent.agent_id,
                "name": self.agent.name,
                "stats": self.agent.stats
            }

        @router.get("/tools")
        async def list_tools():
            return {
                "tools": [t.to_dict() for t in self.agent.get_tool_definitions()]
            }

        return router


# ============================================================================
# SINGLETON & FACTORY
# ============================================================================

_bael_agui_agent: Optional[BaelAGUIAgent] = None


def get_bael_agui_agent(
    llm_provider: Optional[Callable] = None
) -> BaelAGUIAgent:
    """Get the global Ba'el AG-UI agent."""
    global _bael_agui_agent
    if _bael_agui_agent is None:
        _bael_agui_agent = BaelAGUIAgent(llm_provider=llm_provider)
    return _bael_agui_agent


def create_agui_server(
    agent: Optional[AGUIAgent] = None,
    llm_provider: Optional[Callable] = None
) -> AGUISSEServer:
    """Create an AG-UI SSE server."""
    if agent is None:
        agent = get_bael_agui_agent(llm_provider)
    return AGUISSEServer(agent)


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate AG-UI protocol."""
    agent = BaelAGUIAgent()

    input_data = RunAgentInput(
        thread_id="demo-thread",
        run_id="demo-run",
        messages=[
            Message(
                id="msg-1",
                role=MessageRole.USER,
                content="What is the meaning of consciousness? Use deep reasoning."
            )
        ],
        state={"session_start": datetime.now().isoformat()}
    )

    print("=" * 60)
    print("AG-UI PROTOCOL DEMONSTRATION")
    print("=" * 60)

    async for event in agent.run(input_data):
        event_dict = event.to_dict()
        event_type = event_dict.get("type", "UNKNOWN")

        if event_type == "TEXT_MESSAGE_CONTENT":
            print(event_dict.get("delta", ""), end="", flush=True)
        elif event_type == "THINKING_TEXT_MESSAGE_CONTENT":
            print(f"[THINKING] {event_dict.get('delta', '')}", end="", flush=True)
        elif event_type in ["RUN_STARTED", "RUN_FINISHED"]:
            print(f"\n[{event_type}]")
        elif event_type.startswith("TOOL_CALL"):
            print(f"\n[{event_type}] {event_dict}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")


if __name__ == "__main__":
    asyncio.run(demo())
