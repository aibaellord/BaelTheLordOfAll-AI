"""
BAEL AG-UI Agent Session
=========================

Session management for AG-UI protocol.
Handles agent lifecycle and state management.

Features:
- Session creation and management
- Message history tracking
- State persistence
- Thread management
- Run lifecycle
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_FOR_INPUT = "waiting_for_input"
    WAITING_FOR_TOOL = "waiting_for_tool"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class RunState(Enum):
    """Run states."""
    PENDING = "pending"
    RUNNING = "running"
    STREAMING = "streaming"
    TOOL_EXECUTION = "tool_execution"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SessionConfig:
    """Session configuration."""
    # Timeouts
    idle_timeout_seconds: int = 3600
    run_timeout_seconds: int = 300
    tool_timeout_seconds: int = 60

    # Limits
    max_messages: int = 1000
    max_tool_calls_per_run: int = 50
    max_concurrent_runs: int = 1

    # Features
    enable_streaming: bool = True
    enable_state_sync: bool = True
    persist_history: bool = True

    # State
    initial_state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Run:
    """A single run within a session."""
    id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    state: RunState = RunState.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None

    # Tracking
    input_message_id: Optional[str] = None
    output_message_ids: List[str] = field(default_factory=list)
    tool_call_count: int = 0
    token_count: int = 0

    def start(self) -> None:
        """Start the run."""
        self.state = RunState.RUNNING
        self.started_at = datetime.now()

    def complete(self) -> None:
        """Complete the run."""
        self.state = RunState.COMPLETED
        self.finished_at = datetime.now()

    def fail(self, error: str) -> None:
        """Mark run as failed."""
        self.state = RunState.ERROR
        self.error = error
        self.finished_at = datetime.now()

    @property
    def duration_ms(self) -> Optional[float]:
        """Get run duration in milliseconds."""
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return delta.total_seconds() * 1000
        return None


@dataclass
class Thread:
    """A conversation thread."""
    id: str = field(default_factory=lambda: f"thread_{uuid.uuid4().hex[:12]}")
    created_at: datetime = field(default_factory=datetime.now)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Dict[str, Any]) -> None:
        """Add message to thread."""
        self.messages.append(message)

    def get_context(self, max_messages: int = 50) -> List[Dict[str, Any]]:
        """Get context window of messages."""
        return self.messages[-max_messages:]


class AgentSession:
    """
    Manages an agent session for AG-UI protocol.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        config: Optional[SessionConfig] = None,
    ):
        self.id = session_id or f"session_{uuid.uuid4().hex[:12]}"
        self.config = config or SessionConfig()

        # State
        self.state = SessionState.CREATED
        self.agent_state: Dict[str, Any] = dict(self.config.initial_state)

        # Timing
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

        # Threads and runs
        self.threads: Dict[str, Thread] = {}
        self.current_thread_id: Optional[str] = None
        self.runs: List[Run] = []
        self.current_run: Optional[Run] = None

        # Callbacks
        self.state_change_callbacks: List[Callable[[SessionState, SessionState], None]] = []
        self.message_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def create_thread(self, thread_id: Optional[str] = None) -> Thread:
        """Create a new conversation thread."""
        thread = Thread(id=thread_id) if thread_id else Thread()
        self.threads[thread.id] = thread
        self.current_thread_id = thread.id
        return thread

    def get_thread(self, thread_id: Optional[str] = None) -> Optional[Thread]:
        """Get a thread by ID."""
        thread_id = thread_id or self.current_thread_id
        if thread_id:
            return self.threads.get(thread_id)
        return None

    def add_message(
        self,
        role: str,
        content: str,
        thread_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Add a message to a thread."""
        thread_id = thread_id or self.current_thread_id

        if not thread_id:
            thread = self.create_thread()
            thread_id = thread.id

        thread = self.threads.get(thread_id)
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")

        message = {
            "id": f"msg_{uuid.uuid4().hex[:12]}",
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }

        thread.add_message(message)
        self.last_activity = datetime.now()

        # Notify callbacks
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Message callback error: {e}")

        return message

    def start_run(self, input_message_id: Optional[str] = None) -> Run:
        """Start a new run."""
        if self.current_run and self.current_run.state == RunState.RUNNING:
            if self.config.max_concurrent_runs <= 1:
                raise RuntimeError("A run is already in progress")

        run = Run(input_message_id=input_message_id)
        run.start()

        self.runs.append(run)
        self.current_run = run
        self._set_state(SessionState.RUNNING)

        return run

    def finish_run(self, error: Optional[str] = None) -> None:
        """Finish the current run."""
        if not self.current_run:
            return

        if error:
            self.current_run.fail(error)
            self._set_state(SessionState.ERROR)
        else:
            self.current_run.complete()
            self._set_state(SessionState.COMPLETED)

        self.current_run = None

    def update_state(
        self,
        updates: Dict[str, Any],
        merge: bool = True,
    ) -> Dict[str, Any]:
        """Update agent state."""
        if merge:
            self.agent_state.update(updates)
        else:
            self.agent_state = updates

        return self.agent_state

    def get_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        return dict(self.agent_state)

    def _set_state(self, new_state: SessionState) -> None:
        """Set session state with callbacks."""
        old_state = self.state
        self.state = new_state

        for callback in self.state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

    def on_state_change(
        self,
        callback: Callable[[SessionState, SessionState], None],
    ) -> None:
        """Register state change callback."""
        self.state_change_callbacks.append(callback)

    def on_message(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Register message callback."""
        self.message_callbacks.append(callback)

    def is_expired(self) -> bool:
        """Check if session has expired."""
        idle_time = datetime.now() - self.last_activity
        return idle_time.total_seconds() > self.config.idle_timeout_seconds

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        return {
            "id": self.id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "threads": len(self.threads),
            "total_runs": len(self.runs),
            "total_messages": sum(len(t.messages) for t in self.threads.values()),
            "agent_state_keys": list(self.agent_state.keys()),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            "id": self.id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "agent_state": self.agent_state,
            "threads": {
                tid: {
                    "id": t.id,
                    "created_at": t.created_at.isoformat(),
                    "messages": t.messages,
                    "metadata": t.metadata,
                }
                for tid, t in self.threads.items()
            },
            "current_thread_id": self.current_thread_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSession":
        """Deserialize session from dictionary."""
        session = cls(session_id=data["id"])
        session.state = SessionState(data["state"])
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.agent_state = data.get("agent_state", {})
        session.current_thread_id = data.get("current_thread_id")

        for tid, tdata in data.get("threads", {}).items():
            thread = Thread(
                id=tdata["id"],
                created_at=datetime.fromisoformat(tdata["created_at"]),
                messages=tdata.get("messages", []),
                metadata=tdata.get("metadata", {}),
            )
            session.threads[tid] = thread

        return session


def demo():
    """Demonstrate agent session."""
    print("=" * 60)
    print("BAEL AG-UI Agent Session Demo")
    print("=" * 60)

    session = AgentSession()

    # Register callbacks
    def on_state_change(old, new):
        print(f"  State: {old.value} -> {new.value}")

    session.on_state_change(on_state_change)

    # Create thread
    thread = session.create_thread()
    print(f"\nCreated thread: {thread.id}")

    # Add messages
    session.add_message("user", "Hello, how are you?")
    session.add_message("assistant", "I'm doing well, thank you!")

    # Start a run
    run = session.start_run()
    print(f"\nStarted run: {run.id}")

    # Update state
    session.update_state({"current_task": "greeting"})

    # Finish run
    session.finish_run()

    # Show summary
    print(f"\nSession summary: {session.get_summary()}")


if __name__ == "__main__":
    demo()
