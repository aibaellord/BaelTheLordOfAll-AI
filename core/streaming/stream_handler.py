"""
BAEL - Advanced Streaming Response Handler
Real-time streaming for LLM responses and data.

Features:
- SSE (Server-Sent Events)
- WebSocket streaming
- Token-by-token streaming
- Progress tracking
- Buffering and backpressure
- Multi-client broadcast
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, AsyncGenerator, AsyncIterator, Callable, Dict, List,
                    Optional, Set, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class StreamType(Enum):
    """Types of streams."""
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    SSE = "sse"
    WEBSOCKET = "websocket"


class StreamState(Enum):
    """Stream states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StreamChunk:
    """A chunk of streamed data."""
    id: str
    sequence: int
    data: Any
    type: StreamType = StreamType.TEXT
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    final: bool = False

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        lines = [f"id: {self.id}"]

        if "event" in self.metadata:
            lines.append(f"event: {self.metadata['event']}")

        data = self.data if isinstance(self.data, str) else json.dumps(self.data)
        for line in data.split("\n"):
            lines.append(f"data: {line}")

        return "\n".join(lines) + "\n\n"

    def to_json(self) -> str:
        """Format as JSON."""
        return json.dumps({
            "id": self.id,
            "sequence": self.sequence,
            "data": self.data,
            "type": self.type.value,
            "final": self.final,
            "metadata": self.metadata
        })


@dataclass
class StreamProgress:
    """Progress of a stream."""
    stream_id: str
    total_chunks: int = 0
    processed_chunks: int = 0
    bytes_sent: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def progress_percent(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100

    @property
    def duration_seconds(self) -> float:
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def chunks_per_second(self) -> float:
        duration = self.duration_seconds
        return self.processed_chunks / duration if duration > 0 else 0


@dataclass
class StreamMetrics:
    """Metrics for streaming operations."""
    total_streams: int = 0
    active_streams: int = 0
    completed_streams: int = 0
    failed_streams: int = 0
    total_chunks: int = 0
    total_bytes: int = 0
    avg_chunk_size: float = 0.0
    avg_latency_ms: float = 0.0


# =============================================================================
# STREAM BUFFER
# =============================================================================

class StreamBuffer:
    """Buffer for stream chunks with backpressure support."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._buffer: asyncio.Queue[StreamChunk] = asyncio.Queue(maxsize=max_size)
        self._overflow: List[StreamChunk] = []
        self._closed = False

    async def put(self, chunk: StreamChunk) -> bool:
        """Add a chunk to the buffer."""
        if self._closed:
            return False

        try:
            self._buffer.put_nowait(chunk)
            return True
        except asyncio.QueueFull:
            # Overflow handling
            self._overflow.append(chunk)
            return False

    async def get(self) -> Optional[StreamChunk]:
        """Get a chunk from the buffer."""
        if self._overflow:
            return self._overflow.pop(0)

        if self._closed and self._buffer.empty():
            return None

        try:
            return await asyncio.wait_for(self._buffer.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    async def drain(self) -> List[StreamChunk]:
        """Drain all chunks from buffer."""
        chunks = []

        while not self._buffer.empty():
            chunks.append(self._buffer.get_nowait())

        chunks.extend(self._overflow)
        self._overflow.clear()

        return chunks

    def close(self) -> None:
        """Close the buffer."""
        self._closed = True

    @property
    def size(self) -> int:
        return self._buffer.qsize() + len(self._overflow)

    @property
    def is_full(self) -> bool:
        return self.size >= self.max_size


# =============================================================================
# STREAM
# =============================================================================

class Stream:
    """A single stream of data."""

    def __init__(
        self,
        stream_id: str,
        stream_type: StreamType = StreamType.TEXT,
        buffer_size: int = 100
    ):
        self.id = stream_id
        self.type = stream_type
        self.state = StreamState.INITIALIZING
        self.buffer = StreamBuffer(buffer_size)
        self.progress = StreamProgress(stream_id=stream_id)

        self._sequence = 0
        self._subscribers: Set[Callable] = set()
        self._on_complete: List[Callable] = []
        self._on_error: List[Callable] = []

    async def write(self, data: Any, final: bool = False, **metadata) -> StreamChunk:
        """Write data to the stream."""
        chunk = StreamChunk(
            id=f"{self.id}_{self._sequence}",
            sequence=self._sequence,
            data=data,
            type=self.type,
            final=final,
            metadata=metadata
        )

        self._sequence += 1

        # Buffer the chunk
        await self.buffer.put(chunk)

        # Update progress
        self.progress.total_chunks = self._sequence
        data_size = len(str(data).encode())
        self.progress.bytes_sent += data_size

        # Notify subscribers
        await self._notify_subscribers(chunk)

        if final:
            await self.complete()

        return chunk

    async def read(self) -> AsyncGenerator[StreamChunk, None]:
        """Read chunks from the stream."""
        while self.state in [StreamState.INITIALIZING, StreamState.ACTIVE]:
            chunk = await self.buffer.get()

            if chunk:
                self.progress.processed_chunks += 1
                yield chunk

                if chunk.final:
                    break
            elif self.state == StreamState.COMPLETED:
                break

    async def start(self) -> None:
        """Start the stream."""
        self.state = StreamState.ACTIVE
        self.progress.start_time = datetime.now()
        logger.debug(f"Stream {self.id} started")

    async def pause(self) -> None:
        """Pause the stream."""
        self.state = StreamState.PAUSED

    async def resume(self) -> None:
        """Resume the stream."""
        self.state = StreamState.ACTIVE

    async def complete(self) -> None:
        """Complete the stream."""
        self.state = StreamState.COMPLETED
        self.progress.end_time = datetime.now()
        self.buffer.close()

        for callback in self._on_complete:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self)
                else:
                    callback(self)
            except Exception as e:
                logger.error(f"Complete callback error: {e}")

        logger.debug(f"Stream {self.id} completed")

    async def error(self, error: Exception) -> None:
        """Mark stream as errored."""
        self.state = StreamState.ERROR
        self.progress.end_time = datetime.now()
        self.buffer.close()

        for callback in self._on_error:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self, error)
                else:
                    callback(self, error)
            except Exception as e:
                logger.error(f"Error callback error: {e}")

    async def cancel(self) -> None:
        """Cancel the stream."""
        self.state = StreamState.CANCELLED
        self.progress.end_time = datetime.now()
        self.buffer.close()

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to stream updates."""
        self._subscribers.add(callback)

    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from stream updates."""
        self._subscribers.discard(callback)

    def on_complete(self, callback: Callable) -> None:
        """Add completion callback."""
        self._on_complete.append(callback)

    def on_error(self, callback: Callable) -> None:
        """Add error callback."""
        self._on_error.append(callback)

    async def _notify_subscribers(self, chunk: StreamChunk) -> None:
        """Notify all subscribers of new chunk."""
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(chunk)
                else:
                    subscriber(chunk)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")


# =============================================================================
# STREAM MANAGER
# =============================================================================

class StreamManager:
    """Manages multiple streams."""

    def __init__(self):
        self._streams: Dict[str, Stream] = {}
        self._metrics = StreamMetrics()

    def create_stream(
        self,
        stream_type: StreamType = StreamType.TEXT,
        stream_id: Optional[str] = None,
        buffer_size: int = 100
    ) -> Stream:
        """Create a new stream."""
        if not stream_id:
            stream_id = hashlib.md5(
                f"stream_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]

        stream = Stream(stream_id, stream_type, buffer_size)
        self._streams[stream_id] = stream

        self._metrics.total_streams += 1
        self._metrics.active_streams += 1

        # Track completion
        def on_complete(_):
            self._metrics.active_streams -= 1
            self._metrics.completed_streams += 1

        def on_error(_, __):
            self._metrics.active_streams -= 1
            self._metrics.failed_streams += 1

        stream.on_complete(on_complete)
        stream.on_error(on_error)

        return stream

    def get_stream(self, stream_id: str) -> Optional[Stream]:
        """Get a stream by ID."""
        return self._streams.get(stream_id)

    def list_streams(
        self,
        state: Optional[StreamState] = None
    ) -> List[Stream]:
        """List streams with optional filter."""
        streams = list(self._streams.values())
        if state:
            streams = [s for s in streams if s.state == state]
        return streams

    async def close_stream(self, stream_id: str) -> bool:
        """Close and remove a stream."""
        stream = self._streams.pop(stream_id, None)
        if stream:
            if stream.state == StreamState.ACTIVE:
                await stream.cancel()
            return True
        return False

    async def close_all(self) -> int:
        """Close all streams."""
        count = 0
        for stream_id in list(self._streams.keys()):
            await self.close_stream(stream_id)
            count += 1
        return count

    def get_metrics(self) -> StreamMetrics:
        """Get streaming metrics."""
        return self._metrics


# =============================================================================
# LLM RESPONSE STREAMER
# =============================================================================

class LLMResponseStreamer:
    """Stream LLM responses token by token."""

    def __init__(self, stream_manager: StreamManager):
        self.stream_manager = stream_manager

    async def stream_completion(
        self,
        generator: AsyncIterator[str],
        on_token: Optional[Callable[[str], None]] = None
    ) -> Stream:
        """Stream completion from an async generator."""
        stream = self.stream_manager.create_stream(StreamType.TEXT)
        await stream.start()

        async def process():
            full_text = ""
            try:
                async for token in generator:
                    full_text += token
                    await stream.write(token)

                    if on_token:
                        on_token(token)

                await stream.write(full_text, final=True, type="complete")

            except Exception as e:
                await stream.error(e)
                raise

        asyncio.create_task(process())
        return stream

    async def stream_with_thinking(
        self,
        generator: AsyncIterator[Dict[str, Any]]
    ) -> Stream:
        """Stream response with thinking/reasoning steps."""
        stream = self.stream_manager.create_stream(StreamType.JSON)
        await stream.start()

        async def process():
            try:
                async for item in generator:
                    chunk_type = item.get("type", "text")

                    if chunk_type == "thinking":
                        await stream.write(
                            item.get("content", ""),
                            event="thinking"
                        )
                    elif chunk_type == "text":
                        await stream.write(
                            item.get("content", ""),
                            event="text"
                        )
                    elif chunk_type == "tool_call":
                        await stream.write(
                            item,
                            event="tool_call"
                        )
                    elif chunk_type == "done":
                        await stream.write(
                            item.get("content", ""),
                            final=True,
                            event="done"
                        )
                        break

            except Exception as e:
                await stream.error(e)
                raise

        asyncio.create_task(process())
        return stream


# =============================================================================
# SSE HANDLER
# =============================================================================

class SSEHandler:
    """Server-Sent Events handler."""

    def __init__(self, stream: Stream):
        self.stream = stream
        self._keep_alive_interval = 30  # seconds

    async def generate(self) -> AsyncGenerator[str, None]:
        """Generate SSE formatted events."""
        # Send initial event
        yield self._format_event("connected", {"stream_id": self.stream.id})

        # Start keep-alive
        keep_alive_task = asyncio.create_task(self._keep_alive())

        try:
            async for chunk in self.stream.read():
                yield chunk.to_sse()

            # Send completion event
            yield self._format_event("complete", {
                "total_chunks": self.stream.progress.total_chunks,
                "duration": self.stream.progress.duration_seconds
            })

        except Exception as e:
            yield self._format_event("error", {"message": str(e)})

        finally:
            keep_alive_task.cancel()

    async def _keep_alive(self) -> None:
        """Send keep-alive pings."""
        while True:
            await asyncio.sleep(self._keep_alive_interval)
            # Keep-alive comment (not an event)
            # Would need to yield from main loop

    def _format_event(self, event: str, data: Any) -> str:
        """Format as SSE event."""
        lines = [f"event: {event}"]
        data_str = json.dumps(data) if not isinstance(data, str) else data
        lines.append(f"data: {data_str}")
        return "\n".join(lines) + "\n\n"


# =============================================================================
# WEBSOCKET HANDLER
# =============================================================================

class WebSocketHandler:
    """WebSocket streaming handler."""

    def __init__(self, stream: Stream):
        self.stream = stream
        self._websocket = None

    async def handle(self, websocket: Any) -> None:
        """Handle WebSocket connection."""
        self._websocket = websocket

        try:
            # Send connected message
            await websocket.send_json({
                "type": "connected",
                "stream_id": self.stream.id
            })

            # Stream chunks
            async for chunk in self.stream.read():
                await websocket.send_json({
                    "type": "chunk",
                    "data": chunk.data,
                    "sequence": chunk.sequence,
                    "final": chunk.final
                })

            # Send completion
            await websocket.send_json({
                "type": "complete",
                "total_chunks": self.stream.progress.total_chunks
            })

        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })


# =============================================================================
# TEXT ACCUMULATOR
# =============================================================================

class TextAccumulator:
    """Accumulates streamed text with word/sentence awareness."""

    def __init__(self):
        self._buffer = ""
        self._words: List[str] = []
        self._sentences: List[str] = []

    def add(self, text: str) -> None:
        """Add text to accumulator."""
        self._buffer += text
        self._extract_words()
        self._extract_sentences()

    def _extract_words(self) -> None:
        """Extract complete words."""
        while " " in self._buffer:
            idx = self._buffer.index(" ")
            word = self._buffer[:idx]
            self._buffer = self._buffer[idx + 1:]
            if word:
                self._words.append(word)

    def _extract_sentences(self) -> None:
        """Extract complete sentences."""
        import re

        while True:
            match = re.search(r'[.!?]\s*', self._buffer)
            if match:
                sentence = self._buffer[:match.end()]
                self._buffer = self._buffer[match.end():]
                self._sentences.append(sentence.strip())
            else:
                break

    def get_words(self) -> List[str]:
        """Get accumulated words."""
        return self._words.copy()

    def get_sentences(self) -> List[str]:
        """Get accumulated sentences."""
        return self._sentences.copy()

    def get_text(self) -> str:
        """Get full accumulated text."""
        words = " ".join(self._words)
        return f"{words} {self._buffer}".strip()

    def finalize(self) -> str:
        """Finalize and get all text."""
        if self._buffer:
            self._words.append(self._buffer)
            self._buffer = ""
        return " ".join(self._words)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_streaming():
    """Demonstrate streaming capabilities."""
    manager = StreamManager()

    # Create a text stream
    stream = manager.create_stream(StreamType.TEXT)
    await stream.start()

    # Simulate streaming
    async def writer():
        message = "Hello, this is a streaming message from BAEL!"
        for word in message.split():
            await stream.write(word + " ")
            await asyncio.sleep(0.1)
        await stream.write("", final=True)

    # Start writing
    asyncio.create_task(writer())

    # Read stream
    print("Streaming: ", end="", flush=True)
    accumulator = TextAccumulator()

    async for chunk in stream.read():
        print(chunk.data, end="", flush=True)
        accumulator.add(str(chunk.data))

    print()
    print(f"Complete text: {accumulator.finalize()}")

    # Get metrics
    metrics = manager.get_metrics()
    print(f"Total streams: {metrics.total_streams}")
    print(f"Completed: {metrics.completed_streams}")


if __name__ == "__main__":
    asyncio.run(example_streaming())
