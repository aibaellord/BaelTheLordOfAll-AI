"""
BAEL - Working Memory System
Active context and attention management for ongoing operations.

Working memory captures:
- Active goals and tasks
- Current context state
- Attention focus
- Temporary reasoning data
- Active variables and bindings
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("BAEL.Memory.Working")


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class AttentionLevel(Enum):
    """Attention priority levels."""
    BACKGROUND = 0  # Minimal attention
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4  # Immediate focus required


class ContextType(Enum):
    """Types of context items."""
    GOAL = "goal"
    TASK = "task"
    VARIABLE = "variable"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"
    OBSERVATION = "observation"
    INFERENCE = "inference"
    DECISION = "decision"
    PENDING = "pending"


@dataclass
class WorkingItem:
    """An item in working memory."""
    id: str
    context_type: ContextType
    content: Any
    attention: AttentionLevel
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)  # IDs of items this depends on
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "context_type": self.context_type.value,
            "content": self.content,
            "attention": self.attention.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "dependencies": self.dependencies,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkingItem":
        return cls(
            id=data["id"],
            context_type=ContextType(data["context_type"]),
            content=data["content"],
            attention=AttentionLevel(data["attention"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            dependencies=data.get("dependencies", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class FocusContext:
    """The current focus of attention."""
    primary_goal: Optional[str]
    active_task: Optional[str]
    attention_stack: List[str]  # Stack of item IDs being focused on
    context_variables: Dict[str, Any]
    constraints: List[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_goal": self.primary_goal,
            "active_task": self.active_task,
            "attention_stack": self.attention_stack,
            "context_variables": self.context_variables,
            "constraints": self.constraints,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ReasoningTrace:
    """A trace of reasoning steps."""
    id: str
    steps: List[Dict[str, Any]]
    start_time: datetime
    end_time: Optional[datetime]
    conclusion: Optional[str]
    confidence: float

    def add_step(self, step_type: str, content: str, details: Optional[Dict] = None) -> None:
        self.steps.append({
            "type": step_type,
            "content": content,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "steps": self.steps,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "conclusion": self.conclusion,
            "confidence": self.confidence
        }


# =============================================================================
# WORKING MEMORY STORE
# =============================================================================

class WorkingMemoryStore:
    """
    In-memory store for working memory with capacity limits.

    Implements:
    - Limited capacity (like human working memory)
    - Priority-based retention
    - Automatic expiration
    - Attention-based access
    """

    DEFAULT_CAPACITY = 50  # Maximum items in working memory

    def __init__(self, capacity: int = DEFAULT_CAPACITY):
        self.capacity = capacity
        self._items: OrderedDict[str, WorkingItem] = OrderedDict()
        self._focus: FocusContext = FocusContext(
            primary_goal=None,
            active_task=None,
            attention_stack=[],
            context_variables={},
            constraints=[],
            timestamp=datetime.now()
        )
        self._reasoning_traces: Dict[str, ReasoningTrace] = {}
        self._active_trace: Optional[str] = None
        self._lock = threading.Lock()
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()

    def _generate_id(self, content: str = "") -> str:
        """Generate unique item ID."""
        data = f"{content}{datetime.now().isoformat()}{len(self._items)}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    # -------------------------------------------------------------------------
    # Core Operations
    # -------------------------------------------------------------------------

    def store(
        self,
        content: Any,
        context_type: ContextType = ContextType.VARIABLE,
        attention: AttentionLevel = AttentionLevel.NORMAL,
        ttl_seconds: Optional[int] = None,
        item_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store an item in working memory."""
        with self._lock:
            self._maybe_cleanup()

            if item_id is None:
                item_id = self._generate_id(str(content))

            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

            item = WorkingItem(
                id=item_id,
                context_type=context_type,
                content=content,
                attention=attention,
                created_at=datetime.now(),
                expires_at=expires_at,
                dependencies=dependencies or [],
                metadata=metadata or {}
            )

            self._items[item_id] = item
            self._items.move_to_end(item_id)  # Most recent at end

            # Enforce capacity
            self._enforce_capacity()

            logger.debug(f"Stored working memory item: {item_id}")
            return item_id

    def retrieve(self, item_id: str) -> Optional[WorkingItem]:
        """Retrieve an item from working memory."""
        with self._lock:
            if item_id not in self._items:
                return None

            item = self._items[item_id]

            if item.is_expired():
                del self._items[item_id]
                return None

            # Update access tracking
            item.access_count += 1
            item.last_accessed = datetime.now()

            # Move to end (most recently accessed)
            self._items.move_to_end(item_id)

            return item

    def update(self, item_id: str, content: Any) -> bool:
        """Update an item's content."""
        with self._lock:
            if item_id not in self._items:
                return False

            self._items[item_id].content = content
            self._items[item_id].last_accessed = datetime.now()
            self._items.move_to_end(item_id)

            return True

    def delete(self, item_id: str) -> bool:
        """Delete an item from working memory."""
        with self._lock:
            if item_id in self._items:
                del self._items[item_id]
                # Remove from attention stack if present
                if item_id in self._focus.attention_stack:
                    self._focus.attention_stack.remove(item_id)
                return True
            return False

    def get_all(
        self,
        context_type: Optional[ContextType] = None,
        min_attention: AttentionLevel = AttentionLevel.BACKGROUND
    ) -> List[WorkingItem]:
        """Get all items, optionally filtered."""
        with self._lock:
            self._maybe_cleanup()

            items = []
            for item in self._items.values():
                if item.is_expired():
                    continue

                if context_type and item.context_type != context_type:
                    continue

                if item.attention.value < min_attention.value:
                    continue

                items.append(item)

            return items

    def clear(self, context_type: Optional[ContextType] = None) -> int:
        """Clear working memory items."""
        with self._lock:
            if context_type is None:
                count = len(self._items)
                self._items.clear()
                self._focus = FocusContext(
                    primary_goal=None,
                    active_task=None,
                    attention_stack=[],
                    context_variables={},
                    constraints=[],
                    timestamp=datetime.now()
                )
                return count
            else:
                to_delete = [
                    k for k, v in self._items.items()
                    if v.context_type == context_type
                ]
                for k in to_delete:
                    del self._items[k]
                return len(to_delete)

    # -------------------------------------------------------------------------
    # Focus Management
    # -------------------------------------------------------------------------

    def set_goal(self, goal: str, goal_id: Optional[str] = None) -> str:
        """Set the primary goal."""
        goal_id = self.store(
            content=goal,
            context_type=ContextType.GOAL,
            attention=AttentionLevel.HIGH,
            item_id=goal_id
        )
        self._focus.primary_goal = goal_id
        return goal_id

    def set_task(self, task: str, task_id: Optional[str] = None) -> str:
        """Set the active task."""
        task_id = self.store(
            content=task,
            context_type=ContextType.TASK,
            attention=AttentionLevel.HIGH,
            item_id=task_id
        )
        self._focus.active_task = task_id
        return task_id

    def push_attention(self, item_id: str) -> None:
        """Push an item onto the attention stack."""
        if item_id in self._items:
            self._focus.attention_stack.append(item_id)
            self._items[item_id].attention = AttentionLevel.HIGH

    def pop_attention(self) -> Optional[str]:
        """Pop the top item from attention stack."""
        if self._focus.attention_stack:
            item_id = self._focus.attention_stack.pop()
            if item_id in self._items:
                self._items[item_id].attention = AttentionLevel.NORMAL
            return item_id
        return None

    def get_focus(self) -> FocusContext:
        """Get current focus context."""
        self._focus.timestamp = datetime.now()
        return self._focus

    def set_variable(self, name: str, value: Any) -> None:
        """Set a context variable."""
        self._focus.context_variables[name] = value
        # Also store as item for tracking
        self.store(
            content={"name": name, "value": value},
            context_type=ContextType.VARIABLE,
            item_id=f"var_{name}"
        )

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self._focus.context_variables.get(name, default)

    def add_constraint(self, constraint: str) -> str:
        """Add a constraint to current context."""
        constraint_id = self.store(
            content=constraint,
            context_type=ContextType.CONSTRAINT,
            attention=AttentionLevel.HIGH
        )
        self._focus.constraints.append(constraint_id)
        return constraint_id

    def get_constraints(self) -> List[str]:
        """Get all active constraints."""
        constraints = []
        for cid in self._focus.constraints:
            item = self.retrieve(cid)
            if item:
                constraints.append(item.content)
        return constraints

    # -------------------------------------------------------------------------
    # Reasoning Traces
    # -------------------------------------------------------------------------

    def start_reasoning(self, goal: str) -> str:
        """Start a new reasoning trace."""
        trace_id = self._generate_id(goal)
        trace = ReasoningTrace(
            id=trace_id,
            steps=[],
            start_time=datetime.now(),
            end_time=None,
            conclusion=None,
            confidence=0.0
        )
        trace.add_step("start", goal)

        self._reasoning_traces[trace_id] = trace
        self._active_trace = trace_id

        return trace_id

    def add_reasoning_step(
        self,
        step_type: str,
        content: str,
        details: Optional[Dict] = None
    ) -> bool:
        """Add a step to the active reasoning trace."""
        if not self._active_trace:
            return False

        trace = self._reasoning_traces.get(self._active_trace)
        if not trace:
            return False

        trace.add_step(step_type, content, details)
        return True

    def complete_reasoning(
        self,
        conclusion: str,
        confidence: float = 0.7
    ) -> Optional[ReasoningTrace]:
        """Complete the active reasoning trace."""
        if not self._active_trace:
            return None

        trace = self._reasoning_traces.get(self._active_trace)
        if not trace:
            return None

        trace.add_step("conclusion", conclusion)
        trace.end_time = datetime.now()
        trace.conclusion = conclusion
        trace.confidence = confidence

        self._active_trace = None

        return trace

    def get_reasoning_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Get a reasoning trace."""
        return self._reasoning_traces.get(trace_id)

    # -------------------------------------------------------------------------
    # Capacity Management
    # -------------------------------------------------------------------------

    def _enforce_capacity(self) -> None:
        """Enforce capacity limits by evicting low-priority items."""
        while len(self._items) > self.capacity:
            # Find lowest priority item that's not in attention stack
            lowest_id = None
            lowest_priority = float('inf')

            for item_id, item in self._items.items():
                if item_id in self._focus.attention_stack:
                    continue
                if item_id == self._focus.primary_goal:
                    continue
                if item_id == self._focus.active_task:
                    continue

                # Priority score: attention + access frequency + recency
                priority = (
                    item.attention.value * 100 +
                    item.access_count * 10 +
                    (datetime.now() - item.created_at).seconds * -0.01
                )

                if priority < lowest_priority:
                    lowest_priority = priority
                    lowest_id = item_id

            if lowest_id:
                del self._items[lowest_id]
                logger.debug(f"Evicted working memory item: {lowest_id}")
            else:
                break  # Can't evict any more

    def _maybe_cleanup(self) -> None:
        """Periodically cleanup expired items."""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now

    def _cleanup_expired(self) -> None:
        """Remove expired items."""
        expired = [
            k for k, v in self._items.items()
            if v.is_expired()
        ]
        for k in expired:
            del self._items[k]

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired items")

    # -------------------------------------------------------------------------
    # Snapshot & Stats
    # -------------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of working memory state."""
        with self._lock:
            return {
                "items": [item.to_dict() for item in self._items.values()],
                "focus": self._focus.to_dict(),
                "active_trace": self._active_trace,
                "capacity": self.capacity,
                "current_size": len(self._items)
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics."""
        with self._lock:
            by_type = {}
            by_attention = {}

            for item in self._items.values():
                t = item.context_type.value
                by_type[t] = by_type.get(t, 0) + 1

                a = item.attention.name
                by_attention[a] = by_attention.get(a, 0) + 1

            return {
                "total_items": len(self._items),
                "capacity": self.capacity,
                "utilization": len(self._items) / self.capacity,
                "by_type": by_type,
                "by_attention": by_attention,
                "active_reasoning_traces": len(self._reasoning_traces),
                "has_goal": self._focus.primary_goal is not None,
                "has_task": self._focus.active_task is not None,
                "attention_stack_depth": len(self._focus.attention_stack)
            }


# =============================================================================
# WORKING MEMORY MANAGER
# =============================================================================

class WorkingMemoryManager:
    """
    High-level interface for working memory operations.

    Provides:
    - Context management
    - Attention control
    - Reasoning support
    - State snapshots
    """

    def __init__(
        self,
        store: Optional[WorkingMemoryStore] = None,
        capacity: int = 50
    ):
        self.store = store or WorkingMemoryStore(capacity=capacity)

    # -------------------------------------------------------------------------
    # Context Operations
    # -------------------------------------------------------------------------

    def enter_context(
        self,
        goal: str,
        task: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """Enter a new context with goal, task, and variables."""
        ids = {}

        # Set goal
        ids["goal"] = self.store.set_goal(goal)

        # Set task if provided
        if task:
            ids["task"] = self.store.set_task(task)

        # Set variables
        if variables:
            for name, value in variables.items():
                self.store.set_variable(name, value)

        # Add constraints
        if constraints:
            ids["constraints"] = []
            for constraint in constraints:
                cid = self.store.add_constraint(constraint)
                ids["constraints"].append(cid)

        return ids

    def exit_context(self) -> None:
        """Exit current context and clear working memory."""
        self.store.clear()

    def remember(
        self,
        content: Any,
        name: Optional[str] = None,
        attention: AttentionLevel = AttentionLevel.NORMAL,
        ttl: Optional[int] = None
    ) -> str:
        """Remember something in working memory."""
        item_id = name if name else None
        return self.store.store(
            content=content,
            context_type=ContextType.VARIABLE,
            attention=attention,
            ttl_seconds=ttl,
            item_id=item_id
        )

    def recall(self, name_or_id: str) -> Optional[Any]:
        """Recall something from working memory."""
        # Try as variable first
        value = self.store.get_variable(name_or_id)
        if value is not None:
            return value

        # Try as item ID
        item = self.store.retrieve(name_or_id)
        if item:
            return item.content

        return None

    def forget(self, name_or_id: str) -> bool:
        """Forget something from working memory."""
        return self.store.delete(name_or_id)

    # -------------------------------------------------------------------------
    # Attention Operations
    # -------------------------------------------------------------------------

    def focus_on(self, content: Any, name: Optional[str] = None) -> str:
        """Focus attention on something."""
        item_id = self.store.store(
            content=content,
            attention=AttentionLevel.HIGH,
            item_id=name
        )
        self.store.push_attention(item_id)
        return item_id

    def unfocus(self) -> Optional[Any]:
        """Remove focus from current item."""
        item_id = self.store.pop_attention()
        if item_id:
            item = self.store.retrieve(item_id)
            if item:
                return item.content
        return None

    def what_am_i_doing(self) -> Dict[str, Any]:
        """Get current focus summary."""
        focus = self.store.get_focus()

        result = {
            "goal": None,
            "task": None,
            "constraints": focus.constraints,
            "variables": focus.context_variables
        }

        if focus.primary_goal:
            goal_item = self.store.retrieve(focus.primary_goal)
            if goal_item:
                result["goal"] = goal_item.content

        if focus.active_task:
            task_item = self.store.retrieve(focus.active_task)
            if task_item:
                result["task"] = task_item.content

        return result

    # -------------------------------------------------------------------------
    # Reasoning Operations
    # -------------------------------------------------------------------------

    def start_thinking(self, about: str) -> str:
        """Start a reasoning process."""
        return self.store.start_reasoning(about)

    def think_step(self, thought: str, step_type: str = "reason") -> bool:
        """Add a thinking step."""
        return self.store.add_reasoning_step(step_type, thought)

    def conclude(self, conclusion: str, confidence: float = 0.7) -> Optional[Dict]:
        """Complete thinking with a conclusion."""
        trace = self.store.complete_reasoning(conclusion, confidence)
        if trace:
            return trace.to_dict()
        return None

    # -------------------------------------------------------------------------
    # Utility Operations
    # -------------------------------------------------------------------------

    def get_context_summary(self) -> str:
        """Get a text summary of current context."""
        focus = self.what_am_i_doing()

        parts = []

        if focus["goal"]:
            parts.append(f"Goal: {focus['goal']}")

        if focus["task"]:
            parts.append(f"Task: {focus['task']}")

        if focus["constraints"]:
            parts.append(f"Constraints: {len(focus['constraints'])} active")

        if focus["variables"]:
            parts.append(f"Variables: {list(focus['variables'].keys())}")

        if not parts:
            return "No active context"

        return " | ".join(parts)

    def dump_state(self) -> Dict[str, Any]:
        """Dump full working memory state."""
        return self.store.snapshot()

    def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics."""
        return self.store.get_stats()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "AttentionLevel",
    "ContextType",
    "WorkingItem",
    "FocusContext",
    "ReasoningTrace",
    "WorkingMemoryStore",
    "WorkingMemoryManager"
]
