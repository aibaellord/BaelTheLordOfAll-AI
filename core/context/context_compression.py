#!/usr/bin/env python3
"""
BAEL - Agent Context Compression
Intelligent context window management and compression.

Features:
- Token counting
- Context summarization
- Sliding window management
- Important content preservation
- Dynamic compression
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class MessageRole(Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ContentType(Enum):
    """Content types for prioritization."""
    INSTRUCTION = "instruction"
    CONTEXT = "context"
    CONVERSATION = "conversation"
    TOOL_OUTPUT = "tool_output"
    METADATA = "metadata"


class CompressionStrategy(Enum):
    """Compression strategies."""
    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    SLIDING_WINDOW = "sliding_window"
    SELECTIVE = "selective"
    HYBRID = "hybrid"


@dataclass
class Message:
    """Chat message."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    importance: float = 1.0
    content_type: ContentType = ContentType.CONVERSATION
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "role": self.role.value,
            "content": self.content
        }
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class ContextWindow:
    """Context window state."""
    messages: List[Message]
    total_tokens: int
    max_tokens: int
    reserved_tokens: int  # For response

    @property
    def available_tokens(self) -> int:
        return self.max_tokens - self.total_tokens - self.reserved_tokens

    @property
    def utilization(self) -> float:
        return self.total_tokens / self.max_tokens


@dataclass
class CompressionResult:
    """Result of compression."""
    messages: List[Message]
    original_tokens: int
    compressed_tokens: int
    removed_messages: int
    summarized_messages: int

    @property
    def compression_ratio(self) -> float:
        if self.original_tokens == 0:
            return 1.0
        return self.compressed_tokens / self.original_tokens


# =============================================================================
# TOKEN COUNTER
# =============================================================================

class TokenCounter(ABC):
    """Abstract token counter."""

    @abstractmethod
    def count(self, text: str) -> int:
        """Count tokens in text."""
        pass

    def count_messages(self, messages: List[Message]) -> int:
        """Count tokens in messages."""
        total = 0
        for msg in messages:
            # Role overhead
            total += 4  # Approximate
            total += self.count(msg.content)
            if msg.name:
                total += self.count(msg.name) + 1
        return total


class SimpleTokenCounter(TokenCounter):
    """Simple word-based token counter."""

    def count(self, text: str) -> int:
        # Approximate: 1 token ≈ 4 characters
        return len(text) // 4 + 1


class TiktokenCounter(TokenCounter):
    """Tiktoken-based counter for OpenAI models."""

    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            try:
                import tiktoken
                self._encoder = tiktoken.encoding_for_model(self.model)
            except:
                self._encoder = "simple"
        return self._encoder

    def count(self, text: str) -> int:
        encoder = self._get_encoder()
        if encoder == "simple":
            return len(text) // 4 + 1
        return len(encoder.encode(text))


# =============================================================================
# COMPRESSORS
# =============================================================================

class Compressor(ABC):
    """Abstract context compressor."""

    @abstractmethod
    async def compress(
        self,
        messages: List[Message],
        target_tokens: int
    ) -> CompressionResult:
        """Compress messages to target token count."""
        pass


class TruncateCompressor(Compressor):
    """Simple truncation compressor."""

    def __init__(self, token_counter: TokenCounter):
        self.token_counter = token_counter

    async def compress(
        self,
        messages: List[Message],
        target_tokens: int
    ) -> CompressionResult:
        original_tokens = self.token_counter.count_messages(messages)

        if original_tokens <= target_tokens:
            return CompressionResult(
                messages=messages,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                removed_messages=0,
                summarized_messages=0
            )

        # Keep system messages and most recent
        system_msgs = [m for m in messages if m.role == MessageRole.SYSTEM]
        other_msgs = [m for m in messages if m.role != MessageRole.SYSTEM]

        # Calculate tokens for system messages
        system_tokens = self.token_counter.count_messages(system_msgs)
        remaining_tokens = target_tokens - system_tokens

        # Take messages from the end
        kept = []
        current_tokens = 0

        for msg in reversed(other_msgs):
            msg_tokens = self.token_counter.count(msg.content) + 4
            if current_tokens + msg_tokens <= remaining_tokens:
                kept.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break

        result_messages = system_msgs + kept
        compressed_tokens = self.token_counter.count_messages(result_messages)

        return CompressionResult(
            messages=result_messages,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            removed_messages=len(messages) - len(result_messages),
            summarized_messages=0
        )


class SummarizeCompressor(Compressor):
    """Compressor that summarizes old messages."""

    def __init__(
        self,
        token_counter: TokenCounter,
        llm_provider: Callable
    ):
        self.token_counter = token_counter
        self.llm_provider = llm_provider

    async def compress(
        self,
        messages: List[Message],
        target_tokens: int
    ) -> CompressionResult:
        original_tokens = self.token_counter.count_messages(messages)

        if original_tokens <= target_tokens:
            return CompressionResult(
                messages=messages,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                removed_messages=0,
                summarized_messages=0
            )

        # Separate messages
        system_msgs = [m for m in messages if m.role == MessageRole.SYSTEM]
        other_msgs = [m for m in messages if m.role != MessageRole.SYSTEM]

        # Keep recent messages (last 20% of tokens)
        keep_tokens = int(target_tokens * 0.3)
        to_summarize = []
        to_keep = []
        current_tokens = 0

        for msg in reversed(other_msgs):
            msg_tokens = self.token_counter.count(msg.content) + 4
            if current_tokens + msg_tokens <= keep_tokens:
                to_keep.insert(0, msg)
                current_tokens += msg_tokens
            else:
                to_summarize.insert(0, msg)

        # Summarize old messages
        if to_summarize:
            summary = await self._summarize_messages(to_summarize)
            summary_msg = Message(
                role=MessageRole.SYSTEM,
                content=f"[Previous conversation summary]\n{summary}",
                content_type=ContentType.CONTEXT
            )
            summary_msg.token_count = self.token_counter.count(summary_msg.content)

            result_messages = system_msgs + [summary_msg] + to_keep
        else:
            result_messages = system_msgs + to_keep

        compressed_tokens = self.token_counter.count_messages(result_messages)

        return CompressionResult(
            messages=result_messages,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            removed_messages=0,
            summarized_messages=len(to_summarize)
        )

    async def _summarize_messages(self, messages: List[Message]) -> str:
        """Summarize a list of messages."""
        conversation = "\n".join([
            f"{m.role.value}: {m.content}"
            for m in messages
        ])

        prompt = f"""Summarize this conversation in 2-3 sentences, preserving key facts and decisions:

{conversation}

Summary:"""

        try:
            return await self.llm_provider(prompt)
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return "Previous conversation covered various topics."


class SelectiveCompressor(Compressor):
    """Compressor that selectively keeps important messages."""

    def __init__(self, token_counter: TokenCounter):
        self.token_counter = token_counter

    async def compress(
        self,
        messages: List[Message],
        target_tokens: int
    ) -> CompressionResult:
        original_tokens = self.token_counter.count_messages(messages)

        if original_tokens <= target_tokens:
            return CompressionResult(
                messages=messages,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                removed_messages=0,
                summarized_messages=0
            )

        # Score messages by importance
        scored = []
        for i, msg in enumerate(messages):
            score = msg.importance

            # Boost system messages
            if msg.role == MessageRole.SYSTEM:
                score += 2.0

            # Boost recent messages
            recency_boost = i / len(messages)
            score += recency_boost

            # Boost messages with questions or key terms
            if "?" in msg.content:
                score += 0.5
            if any(kw in msg.content.lower() for kw in ["important", "must", "required", "error"]):
                score += 0.3

            scored.append((msg, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Select messages until we hit target
        selected = []
        current_tokens = 0

        for msg, score in scored:
            msg_tokens = self.token_counter.count(msg.content) + 4
            if current_tokens + msg_tokens <= target_tokens:
                selected.append(msg)
                current_tokens += msg_tokens

        # Restore original order
        selected.sort(key=lambda m: messages.index(m))

        return CompressionResult(
            messages=selected,
            original_tokens=original_tokens,
            compressed_tokens=current_tokens,
            removed_messages=len(messages) - len(selected),
            summarized_messages=0
        )


class HybridCompressor(Compressor):
    """Hybrid compressor using multiple strategies."""

    def __init__(
        self,
        token_counter: TokenCounter,
        llm_provider: Callable = None
    ):
        self.token_counter = token_counter
        self.llm_provider = llm_provider

        self.truncate = TruncateCompressor(token_counter)
        self.selective = SelectiveCompressor(token_counter)

        if llm_provider:
            self.summarize = SummarizeCompressor(token_counter, llm_provider)
        else:
            self.summarize = None

    async def compress(
        self,
        messages: List[Message],
        target_tokens: int
    ) -> CompressionResult:
        original_tokens = self.token_counter.count_messages(messages)

        if original_tokens <= target_tokens:
            return CompressionResult(
                messages=messages,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                removed_messages=0,
                summarized_messages=0
            )

        compression_ratio = target_tokens / original_tokens

        # Light compression: use selective
        if compression_ratio > 0.7:
            return await self.selective.compress(messages, target_tokens)

        # Medium compression: use summarization if available
        if compression_ratio > 0.3 and self.summarize:
            return await self.summarize.compress(messages, target_tokens)

        # Heavy compression: use truncation
        return await self.truncate.compress(messages, target_tokens)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """Manage context window for LLM calls."""

    def __init__(
        self,
        max_tokens: int = 8000,
        reserved_tokens: int = 1000,
        token_counter: TokenCounter = None,
        compressor: Compressor = None
    ):
        self.max_tokens = max_tokens
        self.reserved_tokens = reserved_tokens
        self.token_counter = token_counter or SimpleTokenCounter()
        self.compressor = compressor or TruncateCompressor(self.token_counter)

        self.messages: List[Message] = []
        self.total_tokens = 0

    def add_message(
        self,
        role: MessageRole,
        content: str,
        importance: float = 1.0,
        content_type: ContentType = ContentType.CONVERSATION,
        **metadata
    ) -> Message:
        """Add message to context."""
        msg = Message(
            role=role,
            content=content,
            importance=importance,
            content_type=content_type,
            metadata=metadata
        )
        msg.token_count = self.token_counter.count(content) + 4

        self.messages.append(msg)
        self.total_tokens += msg.token_count

        return msg

    def add_system(self, content: str, importance: float = 2.0) -> Message:
        """Add system message."""
        return self.add_message(
            MessageRole.SYSTEM,
            content,
            importance=importance,
            content_type=ContentType.INSTRUCTION
        )

    def add_user(self, content: str) -> Message:
        """Add user message."""
        return self.add_message(
            MessageRole.USER,
            content,
            importance=1.0
        )

    def add_assistant(self, content: str) -> Message:
        """Add assistant message."""
        return self.add_message(
            MessageRole.ASSISTANT,
            content,
            importance=0.8
        )

    def add_tool(self, content: str, name: str = None) -> Message:
        """Add tool output."""
        msg = self.add_message(
            MessageRole.TOOL,
            content,
            importance=0.6,
            content_type=ContentType.TOOL_OUTPUT
        )
        msg.name = name
        return msg

    def get_window(self) -> ContextWindow:
        """Get current context window state."""
        return ContextWindow(
            messages=list(self.messages),
            total_tokens=self.total_tokens,
            max_tokens=self.max_tokens,
            reserved_tokens=self.reserved_tokens
        )

    async def compress_if_needed(self) -> Optional[CompressionResult]:
        """Compress context if over limit."""
        target_tokens = self.max_tokens - self.reserved_tokens

        if self.total_tokens <= target_tokens:
            return None

        result = await self.compressor.compress(
            self.messages,
            target_tokens
        )

        self.messages = result.messages
        self.total_tokens = result.compressed_tokens

        logger.info(
            f"Compressed context: {result.original_tokens} -> {result.compressed_tokens} tokens "
            f"({result.compression_ratio:.0%})"
        )

        return result

    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """Get messages in API format."""
        return [msg.to_dict() for msg in self.messages]

    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []
        self.total_tokens = 0

    def set_importance(self, index: int, importance: float) -> None:
        """Set importance of a message."""
        if 0 <= index < len(self.messages):
            self.messages[index].importance = importance


# =============================================================================
# SMART CONTEXT
# =============================================================================

class SmartContext:
    """Smart context management with automatic optimization."""

    def __init__(
        self,
        max_tokens: int = 8000,
        llm_provider: Callable = None
    ):
        self.token_counter = SimpleTokenCounter()

        if llm_provider:
            self.compressor = HybridCompressor(self.token_counter, llm_provider)
        else:
            self.compressor = HybridCompressor(self.token_counter)

        self.context_manager = ContextManager(
            max_tokens=max_tokens,
            token_counter=self.token_counter,
            compressor=self.compressor
        )

        self.compression_history: List[CompressionResult] = []

    async def add(
        self,
        role: str,
        content: str,
        **kwargs
    ) -> Message:
        """Add message with automatic compression."""
        role_enum = MessageRole(role)
        msg = self.context_manager.add_message(role_enum, content, **kwargs)

        # Check and compress if needed
        result = await self.context_manager.compress_if_needed()
        if result:
            self.compression_history.append(result)

        return msg

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get messages for API call."""
        return self.context_manager.get_messages_for_api()

    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics."""
        window = self.context_manager.get_window()

        return {
            "message_count": len(window.messages),
            "total_tokens": window.total_tokens,
            "max_tokens": window.max_tokens,
            "utilization": f"{window.utilization:.0%}",
            "available_tokens": window.available_tokens,
            "compression_count": len(self.compression_history)
        }


# =============================================================================
# MAIN
# =============================================================================

async def demo():
    """Demo context compression."""
    # Create context manager
    counter = SimpleTokenCounter()
    compressor = HybridCompressor(counter)
    manager = ContextManager(
        max_tokens=200,  # Small for demo
        reserved_tokens=50,
        token_counter=counter,
        compressor=compressor
    )

    # Add messages
    manager.add_system("You are a helpful assistant.")
    manager.add_user("Hello! How are you?")
    manager.add_assistant("I'm doing well, thank you! How can I help you today?")
    manager.add_user("Can you tell me about Python programming?")
    manager.add_assistant("Python is a versatile programming language known for its readability and extensive ecosystem.")
    manager.add_user("What about machine learning?")
    manager.add_assistant("Machine learning is a subset of AI that enables systems to learn from data.")

    print(f"Initial context:")
    window = manager.get_window()
    print(f"  Messages: {len(window.messages)}")
    print(f"  Tokens: {window.total_tokens}/{window.max_tokens}")
    print(f"  Utilization: {window.utilization:.0%}")

    # Add more messages to trigger compression
    for i in range(5):
        manager.add_user(f"Question {i}: What is the meaning of life?")
        manager.add_assistant(f"Answer {i}: The meaning of life is a philosophical question...")

    print(f"\nAfter adding more messages:")
    window = manager.get_window()
    print(f"  Messages: {len(window.messages)}")
    print(f"  Tokens: {window.total_tokens}")

    # Compress
    result = await manager.compress_if_needed()

    if result:
        print(f"\nCompression result:")
        print(f"  Original tokens: {result.original_tokens}")
        print(f"  Compressed tokens: {result.compressed_tokens}")
        print(f"  Ratio: {result.compression_ratio:.0%}")
        print(f"  Removed messages: {result.removed_messages}")
        print(f"  Summarized messages: {result.summarized_messages}")

    print(f"\nFinal context:")
    window = manager.get_window()
    print(f"  Messages: {len(window.messages)}")
    print(f"  Tokens: {window.total_tokens}")

    # Show messages
    print(f"\nMessages:")
    for msg in manager.messages:
        preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
        print(f"  [{msg.role.value}] {preview}")


if __name__ == "__main__":
    asyncio.run(demo())
