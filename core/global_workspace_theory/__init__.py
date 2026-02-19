"""
BAEL Global Workspace Theory Engine
====================================

Global Workspace Theory (Baars/Dehaene).
Conscious broadcast across modular processors.

"Ba'el broadcasts to all." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import deque
import copy

logger = logging.getLogger("BAEL.GlobalWorkspace")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProcessorType(Enum):
    """Types of specialist processors."""
    PERCEPTION = auto()
    LANGUAGE = auto()
    MOTOR = auto()
    MEMORY = auto()
    EMOTION = auto()
    ATTENTION = auto()
    REASONING = auto()
    PLANNING = auto()
    METACOGNITION = auto()


class ContentType(Enum):
    """Types of workspace content."""
    PERCEPT = auto()
    THOUGHT = auto()
    MEMORY = auto()
    PLAN = auto()
    EMOTION = auto()
    GOAL = auto()
    DECISION = auto()


class AccessState(Enum):
    """Content access states."""
    UNCONSCIOUS = auto()
    PRECONSCIOUS = auto()
    CONSCIOUS = auto()
    BROADCAST = auto()


@dataclass
class WorkspaceContent:
    """
    Content that can occupy the global workspace.
    """
    id: str
    content_type: ContentType
    data: Any
    source_processor: ProcessorType
    activation: float = 0.0
    salience: float = 0.5
    state: AccessState = AccessState.UNCONSCIOUS
    timestamp: float = field(default_factory=time.time)
    broadcast_count: int = 0

    @property
    def age(self) -> float:
        return time.time() - self.timestamp

    def compete(self, other: 'WorkspaceContent') -> bool:
        """Compare for workspace access."""
        return (self.activation * self.salience) > (other.activation * other.salience)


@dataclass
class Coalition:
    """
    A coalition of content competing for access.
    """
    id: str
    members: List[WorkspaceContent]
    combined_activation: float

    @property
    def strength(self) -> float:
        if not self.members:
            return 0.0
        return sum(m.activation * m.salience for m in self.members)


@dataclass
class BroadcastEvent:
    """
    A broadcast event from the workspace.
    """
    id: str
    content: WorkspaceContent
    recipients: List[str]
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# SPECIALIST PROCESSOR
# ============================================================================

class SpecialistProcessor(ABC):
    """
    Abstract specialist processor.

    "Ba'el's specialized modules." — Ba'el
    """

    def __init__(
        self,
        processor_id: str,
        processor_type: ProcessorType
    ):
        """Initialize processor."""
        self._id = processor_id
        self._type = processor_type
        self._inbox: deque = deque(maxlen=100)
        self._outbox: List[WorkspaceContent] = []
        self._active = True
        self._lock = threading.RLock()

    @property
    def id(self) -> str:
        return self._id

    @property
    def processor_type(self) -> ProcessorType:
        return self._type

    def receive_broadcast(self, content: WorkspaceContent) -> None:
        """Receive broadcast content."""
        with self._lock:
            self._inbox.append(content)

    def get_candidates(self) -> List[WorkspaceContent]:
        """Get content candidates for workspace."""
        with self._lock:
            candidates = self._outbox.copy()
            self._outbox.clear()
            return candidates

    @abstractmethod
    def process(self) -> None:
        """Process incoming broadcasts and generate outputs."""
        pass

    def propose(self, content: WorkspaceContent) -> None:
        """Propose content for workspace."""
        with self._lock:
            content.source_processor = self._type
            self._outbox.append(content)


class PerceptionProcessor(SpecialistProcessor):
    """Perception specialist."""

    def __init__(self, processor_id: str):
        super().__init__(processor_id, ProcessorType.PERCEPTION)
        self._content_counter = 0

    def perceive(self, data: Any, salience: float = 0.5) -> WorkspaceContent:
        """Create percept."""
        self._content_counter += 1
        content = WorkspaceContent(
            id=f"percept_{self._content_counter}",
            content_type=ContentType.PERCEPT,
            data=data,
            source_processor=self._type,
            activation=salience,
            salience=salience
        )
        self.propose(content)
        return content

    def process(self) -> None:
        """Process broadcasts."""
        with self._lock:
            while self._inbox:
                _ = self._inbox.popleft()
                # Perception responds to broadcasts by updating attention


class MemoryProcessor(SpecialistProcessor):
    """Memory specialist."""

    def __init__(self, processor_id: str):
        super().__init__(processor_id, ProcessorType.MEMORY)
        self._memories: Dict[str, Any] = {}
        self._content_counter = 0

    def store(self, key: str, data: Any) -> None:
        """Store in memory."""
        self._memories[key] = data

    def recall(self, cue: Any) -> Optional[WorkspaceContent]:
        """Recall from memory."""
        self._content_counter += 1

        # Simple cue matching
        cue_str = str(cue).lower()
        for key, data in self._memories.items():
            if cue_str in key.lower() or cue_str in str(data).lower():
                content = WorkspaceContent(
                    id=f"memory_{self._content_counter}",
                    content_type=ContentType.MEMORY,
                    data=data,
                    source_processor=self._type,
                    activation=0.6,
                    salience=0.5
                )
                self.propose(content)
                return content
        return None

    def process(self) -> None:
        """Process broadcasts."""
        with self._lock:
            while self._inbox:
                broadcast = self._inbox.popleft()
                # Store broadcast in memory
                self._memories[broadcast.id] = broadcast.data


class ReasoningProcessor(SpecialistProcessor):
    """Reasoning specialist."""

    def __init__(self, processor_id: str):
        super().__init__(processor_id, ProcessorType.REASONING)
        self._content_counter = 0

    def reason(self, premises: List[Any]) -> WorkspaceContent:
        """Perform reasoning."""
        self._content_counter += 1

        # Simple reasoning placeholder
        conclusion = f"Conclusion from {len(premises)} premises"

        content = WorkspaceContent(
            id=f"thought_{self._content_counter}",
            content_type=ContentType.THOUGHT,
            data={"premises": premises, "conclusion": conclusion},
            source_processor=self._type,
            activation=0.7,
            salience=0.6
        )
        self.propose(content)
        return content

    def process(self) -> None:
        """Process broadcasts."""
        with self._lock:
            premises = []
            while self._inbox:
                broadcast = self._inbox.popleft()
                premises.append(broadcast.data)

            if premises:
                self.reason(premises)


# ============================================================================
# GLOBAL WORKSPACE
# ============================================================================

class GlobalWorkspace:
    """
    The global workspace for conscious broadcast.

    "Ba'el's theater of consciousness." — Ba'el
    """

    def __init__(
        self,
        capacity: int = 1,
        broadcast_threshold: float = 0.5
    ):
        """Initialize workspace."""
        self._capacity = capacity
        self._broadcast_threshold = broadcast_threshold
        self._current_content: Optional[WorkspaceContent] = None
        self._processors: Dict[str, SpecialistProcessor] = {}
        self._competition_queue: List[WorkspaceContent] = []
        self._broadcast_history: List[BroadcastEvent] = []
        self._broadcast_counter = 0
        self._lock = threading.RLock()

    def register_processor(self, processor: SpecialistProcessor) -> None:
        """Register specialist processor."""
        with self._lock:
            self._processors[processor.id] = processor

    def compete(self) -> Optional[WorkspaceContent]:
        """Run competition for workspace access."""
        with self._lock:
            # Collect candidates from all processors
            candidates = []
            for processor in self._processors.values():
                candidates.extend(processor.get_candidates())

            # Add queued content
            candidates.extend(self._competition_queue)
            self._competition_queue.clear()

            if not candidates:
                return None

            # Simple winner-take-all competition
            winner = max(candidates, key=lambda c: c.activation * c.salience)

            if winner.activation * winner.salience >= self._broadcast_threshold:
                winner.state = AccessState.CONSCIOUS
                self._current_content = winner
                return winner

            return None

    def broadcast(self) -> Optional[BroadcastEvent]:
        """Broadcast current content to all processors."""
        with self._lock:
            if not self._current_content:
                return None

            self._current_content.state = AccessState.BROADCAST
            self._current_content.broadcast_count += 1

            recipients = []
            for processor_id, processor in self._processors.items():
                processor.receive_broadcast(self._current_content)
                recipients.append(processor_id)

            self._broadcast_counter += 1
            event = BroadcastEvent(
                id=f"broadcast_{self._broadcast_counter}",
                content=self._current_content,
                recipients=recipients
            )

            self._broadcast_history.append(event)

            # Clear workspace
            self._current_content = None

            return event

    def cycle(self) -> Optional[BroadcastEvent]:
        """Run one workspace cycle."""
        with self._lock:
            # 1. Run processors
            for processor in self._processors.values():
                processor.process()

            # 2. Competition
            winner = self.compete()

            # 3. Broadcast if winner
            if winner:
                return self.broadcast()

            return None

    def inject(
        self,
        content: WorkspaceContent,
        priority: float = 1.0
    ) -> None:
        """Inject content directly into competition."""
        with self._lock:
            content.activation *= priority
            self._competition_queue.append(content)

    @property
    def current(self) -> Optional[WorkspaceContent]:
        return self._current_content

    @property
    def processors(self) -> Dict[str, SpecialistProcessor]:
        return self._processors.copy()

    @property
    def broadcast_history(self) -> List[BroadcastEvent]:
        return self._broadcast_history.copy()


# ============================================================================
# ATTENTION MECHANISM
# ============================================================================

class AttentionController:
    """
    Control attention and salience.

    "Ba'el directs attention." — Ba'el
    """

    def __init__(self, workspace: GlobalWorkspace):
        """Initialize attention controller."""
        self._workspace = workspace
        self._focus: Set[ProcessorType] = set()
        self._inhibited: Set[ProcessorType] = set()
        self._bias_weights: Dict[ContentType, float] = {}
        self._lock = threading.RLock()

    def focus_on(self, processor_type: ProcessorType) -> None:
        """Focus attention on processor type."""
        with self._lock:
            self._focus.add(processor_type)
            self._inhibited.discard(processor_type)

    def inhibit(self, processor_type: ProcessorType) -> None:
        """Inhibit processor type."""
        with self._lock:
            self._inhibited.add(processor_type)
            self._focus.discard(processor_type)

    def set_content_bias(self, content_type: ContentType, weight: float) -> None:
        """Set bias for content type."""
        with self._lock:
            self._bias_weights[content_type] = weight

    def modulate(self, content: WorkspaceContent) -> WorkspaceContent:
        """Modulate content based on attention."""
        with self._lock:
            modified = copy.deepcopy(content)

            # Check processor focus
            if content.source_processor in self._focus:
                modified.activation *= 1.5
            elif content.source_processor in self._inhibited:
                modified.activation *= 0.5

            # Check content type bias
            if content.content_type in self._bias_weights:
                modified.activation *= self._bias_weights[content.content_type]

            return modified

    def clear(self) -> None:
        """Clear all attention modulations."""
        with self._lock:
            self._focus.clear()
            self._inhibited.clear()
            self._bias_weights.clear()


# ============================================================================
# GLOBAL WORKSPACE ENGINE
# ============================================================================

class GlobalWorkspaceEngine:
    """
    Complete Global Workspace Theory implementation.

    "Ba'el's conscious workspace." — Ba'el
    """

    def __init__(self, broadcast_threshold: float = 0.5):
        """Initialize engine."""
        self._workspace = GlobalWorkspace(broadcast_threshold=broadcast_threshold)
        self._attention = AttentionController(self._workspace)

        # Create default processors
        self._perception = PerceptionProcessor("perception")
        self._memory = MemoryProcessor("memory")
        self._reasoning = ReasoningProcessor("reasoning")

        self._workspace.register_processor(self._perception)
        self._workspace.register_processor(self._memory)
        self._workspace.register_processor(self._reasoning)

        self._content_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self, prefix: str) -> str:
        self._content_counter += 1
        return f"{prefix}_{self._content_counter}"

    # Input operations

    def perceive(self, data: Any, salience: float = 0.5) -> WorkspaceContent:
        """Input perception."""
        return self._perception.perceive(data, salience)

    def recall(self, cue: Any) -> Optional[WorkspaceContent]:
        """Recall from memory."""
        return self._memory.recall(cue)

    def think(self, premises: List[Any]) -> WorkspaceContent:
        """Generate thought."""
        return self._reasoning.reason(premises)

    def inject(
        self,
        content_type: ContentType,
        data: Any,
        activation: float = 0.7
    ) -> WorkspaceContent:
        """Inject content into workspace."""
        content = WorkspaceContent(
            id=self._generate_id("injected"),
            content_type=content_type,
            data=data,
            source_processor=ProcessorType.METACOGNITION,
            activation=activation,
            salience=0.6
        )
        self._workspace.inject(content)
        return content

    # Attention

    def focus(self, processor_type: ProcessorType) -> None:
        """Focus attention."""
        self._attention.focus_on(processor_type)

    def inhibit(self, processor_type: ProcessorType) -> None:
        """Inhibit processor."""
        self._attention.inhibit(processor_type)

    def bias_toward(self, content_type: ContentType, weight: float = 1.5) -> None:
        """Bias toward content type."""
        self._attention.set_content_bias(content_type, weight)

    # Workspace operations

    def cycle(self) -> Optional[BroadcastEvent]:
        """Run one workspace cycle."""
        return self._workspace.cycle()

    def run(
        self,
        cycles: int = 10,
        until_broadcast: bool = False
    ) -> List[BroadcastEvent]:
        """Run multiple cycles."""
        events = []

        for _ in range(cycles):
            event = self.cycle()
            if event:
                events.append(event)
                if until_broadcast:
                    break

        return events

    def store_memory(self, key: str, data: Any) -> None:
        """Store in memory."""
        self._memory.store(key, data)

    @property
    def workspace(self) -> GlobalWorkspace:
        return self._workspace

    @property
    def current_content(self) -> Optional[WorkspaceContent]:
        return self._workspace.current

    @property
    def broadcast_history(self) -> List[BroadcastEvent]:
        return self._workspace.broadcast_history

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'processors': len(self._workspace.processors),
            'broadcasts': len(self._workspace.broadcast_history),
            'current': self._workspace.current.id if self._workspace.current else None,
            'memories': len(self._memory._memories)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_global_workspace_engine(
    broadcast_threshold: float = 0.5
) -> GlobalWorkspaceEngine:
    """Create global workspace engine."""
    return GlobalWorkspaceEngine(broadcast_threshold)


def create_workspace_content(
    content_type: ContentType,
    data: Any,
    activation: float = 0.5,
    salience: float = 0.5
) -> WorkspaceContent:
    """Create workspace content."""
    return WorkspaceContent(
        id=f"content_{random.randint(1000, 9999)}",
        content_type=content_type,
        data=data,
        source_processor=ProcessorType.METACOGNITION,
        activation=activation,
        salience=salience
    )
