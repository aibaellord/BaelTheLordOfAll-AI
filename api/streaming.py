#!/usr/bin/env python3
"""
BAEL - Streaming Response Handler
Server-Sent Events (SSE) and streaming response utilities for the API.

Enables:
- Token-by-token LLM streaming
- Real-time progress updates
- Council deliberation streaming
- Task execution streaming
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from fastapi import Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger("BAEL.API.Streaming")


@dataclass
class StreamEvent:
    """A streaming event."""
    event: str
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None

    def to_sse(self) -> str:
        """Convert to SSE format."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        lines.append(f"event: {self.event}")
        lines.append(f"data: {json.dumps(self.data)}")
        lines.append("")  # End with blank line
        return "\n".join(lines) + "\n"


class StreamingChat:
    """
    Handles streaming chat responses from LLM.
    """

    def __init__(self):
        self._active_streams: Dict[str, asyncio.Event] = {}

    async def stream_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream LLM response token by token.
        """
        request_id = f"chat-{uuid.uuid4().hex[:8]}"
        self._active_streams[request_id] = asyncio.Event()

        # Yield start event
        yield StreamEvent(
            event="chat_start",
            data={
                "request_id": request_id,
                "model": model,
                "timestamp": datetime.now().isoformat()
            }
        )

        try:
            from core.wiring import LLMExecutor

            executor = LLMExecutor(model=model)
            full_response = ""
            token_count = 0
            start_time = time.time()

            # Try streaming if supported
            async for token in executor.stream(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                if self._active_streams.get(request_id, asyncio.Event()).is_set():
                    break  # Cancelled

                full_response += token
                token_count += 1

                yield StreamEvent(
                    event="chat_token",
                    data={
                        "request_id": request_id,
                        "token": token,
                        "index": token_count
                    }
                )

            # Yield completion
            yield StreamEvent(
                event="chat_complete",
                data={
                    "request_id": request_id,
                    "response": full_response,
                    "tokens": token_count,
                    "duration_ms": (time.time() - start_time) * 1000
                }
            )

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield StreamEvent(
                event="chat_error",
                data={
                    "request_id": request_id,
                    "error": str(e)
                }
            )

        finally:
            if request_id in self._active_streams:
                del self._active_streams[request_id]

    def cancel_stream(self, request_id: str) -> bool:
        """Cancel an active stream."""
        if request_id in self._active_streams:
            self._active_streams[request_id].set()
            return True
        return False


class StreamingCouncil:
    """
    Handles streaming council deliberation updates.
    """

    async def stream_deliberation(
        self,
        topic: str,
        context: Optional[Dict] = None,
        members: Optional[List[str]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream council deliberation in real-time.
        """
        deliberation_id = f"council-{uuid.uuid4().hex[:8]}"

        # Yield start
        yield StreamEvent(
            event="council_start",
            data={
                "deliberation_id": deliberation_id,
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
        )

        try:
            from core.council.llm_integration import CouncilLLMIntegration

            council = CouncilLLMIntegration()

            # Stream member introductions
            for member in council.personas:
                yield StreamEvent(
                    event="council_member",
                    data={
                        "deliberation_id": deliberation_id,
                        "member": member.name,
                        "role": member.role,
                        "perspective": member.perspective
                    }
                )
                await asyncio.sleep(0.1)

            # Stream opinions phase
            yield StreamEvent(
                event="council_phase",
                data={
                    "deliberation_id": deliberation_id,
                    "phase": "initial_opinions"
                }
            )

            # Run deliberation (this could be made more granular)
            result = await council.deliberate(topic, context)

            # Stream each member's opinion
            for msg in result.messages:
                if msg.phase == "initial":
                    yield StreamEvent(
                        event="council_opinion",
                        data={
                            "deliberation_id": deliberation_id,
                            "member": msg.member,
                            "opinion": msg.content,
                            "phase": msg.phase
                        }
                    )
                    await asyncio.sleep(0.2)

            # Stream discussion phase
            yield StreamEvent(
                event="council_phase",
                data={
                    "deliberation_id": deliberation_id,
                    "phase": "discussion"
                }
            )

            for msg in result.messages:
                if msg.phase == "discussion":
                    yield StreamEvent(
                        event="council_discussion",
                        data={
                            "deliberation_id": deliberation_id,
                            "member": msg.member,
                            "content": msg.content
                        }
                    )
                    await asyncio.sleep(0.2)

            # Stream votes
            yield StreamEvent(
                event="council_phase",
                data={
                    "deliberation_id": deliberation_id,
                    "phase": "voting"
                }
            )

            for vote in result.votes:
                yield StreamEvent(
                    event="council_vote",
                    data={
                        "deliberation_id": deliberation_id,
                        "member": vote["member"],
                        "vote": vote["vote"],
                        "reasoning": vote.get("reasoning", "")
                    }
                )
                await asyncio.sleep(0.1)

            # Final decision
            yield StreamEvent(
                event="council_complete",
                data={
                    "deliberation_id": deliberation_id,
                    "decision": result.final_decision,
                    "consensus": result.consensus_score,
                    "summary": result.summary
                }
            )

        except Exception as e:
            logger.error(f"Council streaming error: {e}")
            yield StreamEvent(
                event="council_error",
                data={
                    "deliberation_id": deliberation_id,
                    "error": str(e)
                }
            )


class StreamingTasks:
    """
    Handles streaming task execution updates.
    """

    async def stream_execution(
        self,
        goal: str,
        context: Optional[Dict] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream task execution progress.
        """
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"

        yield StreamEvent(
            event="execution_start",
            data={
                "execution_id": execution_id,
                "goal": goal,
                "timestamp": datetime.now().isoformat()
            }
        )

        try:
            from core.agents.execution_engine import AgentExecutionEngine, Task

            engine = AgentExecutionEngine()

            # Hook into callbacks
            task_updates = asyncio.Queue()

            original_start = engine.on_task_start
            original_complete = engine.on_task_complete
            original_failed = engine.on_task_failed

            async def on_start(task: Task):
                await task_updates.put(("start", task, None))
                if original_start:
                    original_start(task)

            async def on_complete(task: Task, result):
                await task_updates.put(("complete", task, result))
                if original_complete:
                    original_complete(task, result)

            async def on_failed(task: Task, error: str):
                await task_updates.put(("failed", task, error))
                if original_failed:
                    original_failed(task, error)

            engine.on_task_start = on_start
            engine.on_task_complete = on_complete
            engine.on_task_failed = on_failed

            # Start engine
            await engine.start()

            # Execute goal in background
            exec_task = asyncio.create_task(
                engine.execute_goal(goal, context)
            )

            # Stream updates
            while not exec_task.done():
                try:
                    update_type, task, data = await asyncio.wait_for(
                        task_updates.get(),
                        timeout=0.5
                    )

                    if update_type == "start":
                        yield StreamEvent(
                            event="task_start",
                            data={
                                "execution_id": execution_id,
                                "task_id": task.id,
                                "name": task.name,
                                "action": task.action
                            }
                        )
                    elif update_type == "complete":
                        yield StreamEvent(
                            event="task_complete",
                            data={
                                "execution_id": execution_id,
                                "task_id": task.id,
                                "result": str(data.output)[:500] if data else None,
                                "duration_ms": data.duration_ms if data else 0
                            }
                        )
                    elif update_type == "failed":
                        yield StreamEvent(
                            event="task_failed",
                            data={
                                "execution_id": execution_id,
                                "task_id": task.id,
                                "error": data
                            }
                        )

                except asyncio.TimeoutError:
                    continue

            # Get final results
            results = await exec_task
            await engine.stop()

            yield StreamEvent(
                event="execution_complete",
                data={
                    "execution_id": execution_id,
                    "task_count": len(results),
                    "success": all(r.success for r in results.values() if r)
                }
            )

        except Exception as e:
            logger.error(f"Execution streaming error: {e}")
            yield StreamEvent(
                event="execution_error",
                data={
                    "execution_id": execution_id,
                    "error": str(e)
                }
            )


# =============================================================================
# FASTAPI INTEGRATION
# =============================================================================

def create_sse_response(
    generator: AsyncGenerator[StreamEvent, None]
) -> EventSourceResponse:
    """Create an SSE response from an event generator."""

    async def event_generator():
        async for event in generator:
            yield {
                "event": event.event,
                "id": event.id or str(uuid.uuid4()),
                "data": json.dumps(event.data)
            }

    return EventSourceResponse(event_generator())


def create_streaming_response(
    generator: AsyncGenerator[StreamEvent, None],
    media_type: str = "text/event-stream"
) -> StreamingResponse:
    """Create a streaming response."""

    async def content_generator():
        async for event in generator:
            yield event.to_sse()

    return StreamingResponse(
        content_generator(),
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

_streaming_chat: Optional[StreamingChat] = None
_streaming_council: Optional[StreamingCouncil] = None
_streaming_tasks: Optional[StreamingTasks] = None


def get_streaming_chat() -> StreamingChat:
    global _streaming_chat
    if _streaming_chat is None:
        _streaming_chat = StreamingChat()
    return _streaming_chat


def get_streaming_council() -> StreamingCouncil:
    global _streaming_council
    if _streaming_council is None:
        _streaming_council = StreamingCouncil()
    return _streaming_council


def get_streaming_tasks() -> StreamingTasks:
    global _streaming_tasks
    if _streaming_tasks is None:
        _streaming_tasks = StreamingTasks()
    return _streaming_tasks


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    async def demo():
        print("🌊 BAEL Streaming Demo\n")

        # Demo streaming events
        events = [
            StreamEvent("start", {"message": "Beginning..."}),
            StreamEvent("token", {"text": "Hello"}),
            StreamEvent("token", {"text": " World"}),
            StreamEvent("complete", {"full": "Hello World"})
        ]

        for event in events:
            print(event.to_sse())
            await asyncio.sleep(0.2)

    asyncio.run(demo())
