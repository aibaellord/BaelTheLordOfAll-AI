"""
BAEL AG-UI Message Types
=========================

Standard message type definitions for AG-UI protocol.
Provides structured data models for agent-UI communication.

Features:
- Type-safe message definitions
- Serialization/deserialization
- Message validation
- Role support
- Tool call integration
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MessageRole(Enum):
    """Message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ContentType(Enum):
    """Content types."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    CODE = "code"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


@dataclass
class MessageContent:
    """Message content block."""
    type: ContentType
    text: Optional[str] = None
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    language: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"type": self.type.value}

        if self.text is not None:
            result["text"] = self.text
        if self.image_url is not None:
            result["image_url"] = self.image_url
        if self.file_url is not None:
            result["file_url"] = self.file_url
        if self.language is not None:
            result["language"] = self.language
        if self.data is not None:
            result["data"] = self.data

        return result


@dataclass
class BaseMessage:
    """Base message class."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.ASSISTANT
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "role": self.role.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class UserMessage(BaseMessage):
    """User message."""
    role: MessageRole = field(default=MessageRole.USER)
    content: str = ""
    attachments: List[MessageContent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result["content"] = self.content
        if self.attachments:
            result["attachments"] = [a.to_dict() for a in self.attachments]
        return result


@dataclass
class AgentMessage(BaseMessage):
    """Agent/assistant message."""
    role: MessageRole = field(default=MessageRole.ASSISTANT)
    content: str = ""
    tool_calls: List["ToolCall"] = field(default_factory=list)
    model: Optional[str] = None
    provider: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result["content"] = self.content
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.model:
            result["model"] = self.model
        if self.provider:
            result["provider"] = self.provider
        return result


@dataclass
class SystemMessage(BaseMessage):
    """System message."""
    role: MessageRole = field(default=MessageRole.SYSTEM)
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result["content"] = self.content
        return result


@dataclass
class ToolCall:
    """Tool call definition."""
    id: str = field(default_factory=lambda: f"tool_{uuid.uuid4().hex[:8]}")
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    arguments_str: str = ""  # Raw arguments string

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        """Create from dictionary."""
        return cls(
            id=data.get("id", f"tool_{uuid.uuid4().hex[:8]}"),
            name=data.get("name", ""),
            arguments=data.get("arguments", {}),
        )


@dataclass
class ToolResult:
    """Tool execution result."""
    tool_call_id: str
    name: str
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class StreamChunk:
    """Streaming content chunk."""
    message_id: str
    delta: str
    chunk_index: int = 0
    is_final: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "delta": self.delta,
            "chunk_index": self.chunk_index,
            "is_final": self.is_final,
        }


@dataclass
class StateUpdate:
    """Agent state update."""
    operation: str  # "add", "remove", "replace"
    path: str
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (JSON Patch format)."""
        result = {
            "op": self.operation,
            "path": self.path,
        }
        if self.value is not None:
            result["value"] = self.value
        return result


# Type alias for any message type
Message = Union[UserMessage, AgentMessage, SystemMessage]


def create_message(role: str, content: str, **kwargs) -> Message:
    """Factory function to create messages."""
    role_enum = MessageRole(role)

    if role_enum == MessageRole.USER:
        return UserMessage(content=content, **kwargs)
    elif role_enum == MessageRole.ASSISTANT:
        return AgentMessage(content=content, **kwargs)
    elif role_enum == MessageRole.SYSTEM:
        return SystemMessage(content=content, **kwargs)
    else:
        raise ValueError(f"Unknown role: {role}")


def parse_message(data: Dict[str, Any]) -> Message:
    """Parse message from dictionary."""
    role = data.get("role", "assistant")
    content = data.get("content", "")

    return create_message(role, content, **{
        k: v for k, v in data.items()
        if k not in ("role", "content")
    })


def demo():
    """Demonstrate message types."""
    print("=" * 60)
    print("BAEL AG-UI Message Types Demo")
    print("=" * 60)

    # Create user message
    user_msg = UserMessage(content="Write a Python function")
    print(f"\nUser message: {user_msg.to_dict()}")

    # Create agent message with tool call
    tool_call = ToolCall(
        name="execute_code",
        arguments={"code": "print('Hello')"},
    )

    agent_msg = AgentMessage(
        content="I'll run this code for you.",
        tool_calls=[tool_call],
        model="gpt-4o",
    )
    print(f"\nAgent message: {agent_msg.to_dict()}")

    # Create tool result
    result = ToolResult(
        tool_call_id=tool_call.id,
        name="execute_code",
        result="Hello",
        execution_time_ms=15.5,
    )
    print(f"\nTool result: {result.to_dict()}")


if __name__ == "__main__":
    demo()
