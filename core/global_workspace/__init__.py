"""
BAEL Global Workspace Theory Engine
=====================================

Unified conscious access and broadcasting.

"Ba'el broadcasts to all." — Ba'el
"""

import logging
import threading
import time
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import deque
import heapq

logger = logging.getLogger("BAEL.GlobalWorkspace")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProcessorType(Enum):
    """Types of specialist processors."""
    PERCEPTUAL = auto()
    MEMORY = auto()
    LANGUAGE = auto()
    MOTOR = auto()
    EMOTIONAL = auto()
    REASONING = auto()
    ATTENTION = auto()
    EXECUTIVE = auto()


class BroadcastPriority(Enum):
    """Priority levels for broadcasts."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class WorkspaceContent:
    """
    Content that can occupy the global workspace.
    """
    id: str
    content: Any
    source_processor: str
    activation: float = 0.0
    timestamp: float = field(default_factory=time.time)
    priority: BroadcastPriority = BroadcastPriority.NORMAL
    associations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: 'WorkspaceContent') -> bool:
        """For heap comparison."""
        return self.activation > other.activation  # Higher activation = higher priority


@dataclass
class Broadcast:
    """
    A broadcast from the global workspace.
    """
    id: str
    content: WorkspaceContent
    timestamp: float = field(default_factory=time.time)
    recipients: List[str] = field(default_factory=list)
    acknowledged_by: List[str] = field(default_factory=list)


# ============================================================================
# SPECIALIST PROCESSOR
# ============================================================================

class SpecialistProcessor(ABC):
    """
    A specialist processor that can contribute to and receive from workspace.

    "Ba'el has many specialists." — Ba'el
    """

    def __init__(self, name: str, processor_type: ProcessorType):
        """Initialize processor."""
        self._name = name
        self._type = processor_type
        self._active = True
        self._inbox: deque = deque(maxlen=100)
        self._proposals: List[WorkspaceContent] = []
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def processor_type(self) -> ProcessorType:
        return self._type

    def receive_broadcast(self, broadcast: Broadcast) -> bool:
        """Receive a broadcast from workspace."""
        with self._lock:
            if not self._active:
                return False

            self._inbox.append(broadcast)
            self._process_broadcast(broadcast)
            return True

    @abstractmethod
    def _process_broadcast(self, broadcast: Broadcast) -> None:
        """Process received broadcast."""
        pass

    @abstractmethod
    def generate_proposal(self) -> Optional[WorkspaceContent]:
        """Generate content proposal for workspace."""
        pass

    def get_proposals(self) -> List[WorkspaceContent]:
        """Get pending proposals."""
        with self._lock:
            proposals = self._proposals.copy()
            self._proposals = []
            return proposals

    def activate(self) -> None:
        """Activate processor."""
        self._active = True

    def deactivate(self) -> None:
        """Deactivate processor."""
        self._active = False


class GenericProcessor(SpecialistProcessor):
    """Generic implementation of specialist processor."""

    def __init__(
        self,
        name: str,
        processor_type: ProcessorType,
        content_generator: Optional[Callable[[], Any]] = None
    ):
        super().__init__(name, processor_type)
        self._content_generator = content_generator
        self._received_count = 0

    def _process_broadcast(self, broadcast: Broadcast) -> None:
        """Process received broadcast."""
        self._received_count += 1

        # May generate response based on content
        if self._content_generator:
            response_content = self._content_generator()
            if response_content:
                proposal = WorkspaceContent(
                    id=f"{self._name}_response_{time.time()}",
                    content=response_content,
                    source_processor=self._name,
                    activation=0.5
                )
                self._proposals.append(proposal)

    def generate_proposal(self) -> Optional[WorkspaceContent]:
        """Generate content proposal."""
        if not self._content_generator:
            return None

        content = self._content_generator()
        if content:
            return WorkspaceContent(
                id=f"{self._name}_proposal_{time.time()}",
                content=content,
                source_processor=self._name,
                activation=random.uniform(0.3, 0.8)
            )
        return None


# ============================================================================
# GLOBAL WORKSPACE
# ============================================================================

class GlobalWorkspace:
    """
    The global workspace for conscious access.

    "Ba'el's workspace unifies all." — Ba'el
    """

    def __init__(self, capacity: int = 7):
        """
        Initialize global workspace.

        capacity: Approximate capacity (7 +/- 2 items)
        """
        self._capacity = capacity
        self._contents: List[WorkspaceContent] = []
        self._processors: Dict[str, SpecialistProcessor] = {}
        self._broadcast_history: deque = deque(maxlen=1000)
        self._competition_threshold = 0.5
        self._lock = threading.RLock()

    def register_processor(self, processor: SpecialistProcessor) -> None:
        """Register a specialist processor."""
        with self._lock:
            self._processors[processor.name] = processor

    def unregister_processor(self, name: str) -> None:
        """Unregister a processor."""
        with self._lock:
            if name in self._processors:
                del self._processors[name]

    def submit(self, content: WorkspaceContent) -> bool:
        """Submit content for consideration."""
        with self._lock:
            # Add to competition pool
            heapq.heappush(self._contents, content)

            # Trim if over capacity
            while len(self._contents) > self._capacity * 2:
                heapq.heappop(self._contents)

            return True

    def collect_proposals(self) -> List[WorkspaceContent]:
        """Collect proposals from all processors."""
        with self._lock:
            proposals = []

            for processor in self._processors.values():
                # Generate new proposals
                proposal = processor.generate_proposal()
                if proposal:
                    proposals.append(proposal)

                # Collect pending proposals
                pending = processor.get_proposals()
                proposals.extend(pending)

            return proposals

    def competition_cycle(self) -> Optional[WorkspaceContent]:
        """
        Run competition cycle to select winning content.

        Returns winning content that gets broadcast.
        """
        with self._lock:
            # Collect new proposals
            proposals = self.collect_proposals()
            for proposal in proposals:
                self.submit(proposal)

            if not self._contents:
                return None

            # Apply activation decay
            for content in self._contents:
                content.activation *= 0.95

            # Competition: highest activation wins
            # Use coalition formation (associated contents boost each other)
            for content in self._contents:
                for other in self._contents:
                    if other.id in content.associations:
                        content.activation += 0.1 * other.activation

            # Normalize
            max_activation = max(c.activation for c in self._contents)
            if max_activation > 0:
                for content in self._contents:
                    content.activation /= max_activation

            # Winner takes all if above threshold
            winner = max(self._contents, key=lambda c: c.activation)

            if winner.activation >= self._competition_threshold:
                # Remove winner from pool (it will be broadcast)
                self._contents = [c for c in self._contents if c.id != winner.id]
                heapq.heapify(self._contents)

                return winner

            return None

    def broadcast(self, content: WorkspaceContent) -> Broadcast:
        """Broadcast winning content to all processors."""
        with self._lock:
            broadcast = Broadcast(
                id=f"broadcast_{time.time()}",
                content=content,
                recipients=list(self._processors.keys())
            )

            # Send to all processors
            for name, processor in self._processors.items():
                if processor.receive_broadcast(broadcast):
                    broadcast.acknowledged_by.append(name)

            self._broadcast_history.append(broadcast)

            return broadcast

    def step(self) -> Optional[Broadcast]:
        """Execute one workspace step."""
        winner = self.competition_cycle()

        if winner:
            return self.broadcast(winner)

        return None

    def run(self, steps: int = 100, delay: float = 0.0) -> List[Broadcast]:
        """Run workspace for multiple steps."""
        broadcasts = []

        for _ in range(steps):
            broadcast = self.step()
            if broadcast:
                broadcasts.append(broadcast)

            if delay > 0:
                time.sleep(delay)

        return broadcasts

    @property
    def current_contents(self) -> List[WorkspaceContent]:
        """Get current workspace contents."""
        with self._lock:
            return sorted(
                self._contents.copy(),
                key=lambda c: c.activation,
                reverse=True
            )

    @property
    def state(self) -> Dict[str, Any]:
        """Get workspace state."""
        with self._lock:
            return {
                'content_count': len(self._contents),
                'processor_count': len(self._processors),
                'broadcast_count': len(self._broadcast_history),
                'capacity': self._capacity,
                'top_contents': [
                    {'id': c.id, 'activation': c.activation, 'source': c.source_processor}
                    for c in sorted(self._contents, key=lambda x: x.activation, reverse=True)[:3]
                ]
            }


# ============================================================================
# CONSCIOUS ACCESS
# ============================================================================

class ConsciousAccess:
    """
    Interface for conscious access to workspace.

    "Ba'el is conscious of what enters the workspace." — Ba'el
    """

    def __init__(self, workspace: GlobalWorkspace):
        """Initialize conscious access."""
        self._workspace = workspace
        self._focus: Optional[WorkspaceContent] = None
        self._access_log: deque = deque(maxlen=100)
        self._lock = threading.RLock()

    def focus_on(self, content: WorkspaceContent) -> None:
        """Focus attention on specific content."""
        with self._lock:
            self._focus = content
            content.activation *= 1.5  # Boost focused content
            self._access_log.append({
                'type': 'focus',
                'content_id': content.id,
                'timestamp': time.time()
            })

    def broadcast_focus(self) -> Optional[Broadcast]:
        """Broadcast focused content."""
        with self._lock:
            if self._focus:
                return self._workspace.broadcast(self._focus)
            return None

    def query(self, query_fn: Callable[[WorkspaceContent], bool]) -> List[WorkspaceContent]:
        """Query workspace contents."""
        with self._lock:
            return [c for c in self._workspace.current_contents if query_fn(c)]

    def inject(self, content: Any, source: str = "conscious") -> WorkspaceContent:
        """Inject content directly into workspace."""
        with self._lock:
            ws_content = WorkspaceContent(
                id=f"injected_{time.time()}",
                content=content,
                source_processor=source,
                activation=0.8,  # High initial activation
                priority=BroadcastPriority.HIGH
            )
            self._workspace.submit(ws_content)
            self._access_log.append({
                'type': 'inject',
                'content_id': ws_content.id,
                'timestamp': time.time()
            })
            return ws_content

    def get_recent(self, n: int = 5) -> List[Broadcast]:
        """Get recent broadcasts."""
        return list(self._workspace._broadcast_history)[-n:]

    @property
    def is_focused(self) -> bool:
        """Check if attention is focused."""
        return self._focus is not None


# ============================================================================
# ATTENTION CONTROLLER
# ============================================================================

class AttentionController:
    """
    Controls attention for workspace access.

    "Ba'el directs attention." — Ba'el
    """

    def __init__(self, workspace: GlobalWorkspace):
        """Initialize attention controller."""
        self._workspace = workspace
        self._attention_bias: Dict[str, float] = {}
        self._processor_bias: Dict[str, float] = {}
        self._novelty_bias = 0.5
        self._lock = threading.RLock()

    def set_topic_bias(self, topic: str, weight: float) -> None:
        """Set attention bias for topic."""
        with self._lock:
            self._attention_bias[topic] = max(0, min(2, weight))

    def set_processor_bias(self, processor_name: str, weight: float) -> None:
        """Set attention bias for processor."""
        with self._lock:
            self._processor_bias[processor_name] = max(0, min(2, weight))

    def set_novelty_bias(self, weight: float) -> None:
        """Set novelty bias."""
        with self._lock:
            self._novelty_bias = max(0, min(1, weight))

    def modulate_activations(self) -> None:
        """Apply attention biases to workspace contents."""
        with self._lock:
            for content in self._workspace._contents:
                # Apply topic bias
                for topic, weight in self._attention_bias.items():
                    if topic in str(content.content):
                        content.activation *= weight

                # Apply processor bias
                if content.source_processor in self._processor_bias:
                    content.activation *= self._processor_bias[content.source_processor]

                # Apply novelty bias (newer = higher activation)
                age = time.time() - content.timestamp
                novelty_factor = 1.0 / (1.0 + age * 0.1)
                content.activation += self._novelty_bias * novelty_factor

    def step(self) -> Optional[Broadcast]:
        """Attention-modulated workspace step."""
        self.modulate_activations()
        return self._workspace.step()


# ============================================================================
# GLOBAL WORKSPACE ENGINE
# ============================================================================

class GlobalWorkspaceEngine:
    """
    Complete Global Workspace Theory engine.

    "Ba'el implements consciousness through broadcasting." — Ba'el
    """

    def __init__(self, capacity: int = 7):
        """Initialize engine."""
        self._workspace = GlobalWorkspace(capacity)
        self._conscious_access = ConsciousAccess(self._workspace)
        self._attention = AttentionController(self._workspace)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    def add_processor(
        self,
        name: str,
        processor_type: ProcessorType,
        content_generator: Optional[Callable[[], Any]] = None
    ) -> SpecialistProcessor:
        """Add specialist processor."""
        processor = GenericProcessor(name, processor_type, content_generator)
        self._workspace.register_processor(processor)
        return processor

    def remove_processor(self, name: str) -> None:
        """Remove processor."""
        self._workspace.unregister_processor(name)

    def inject(self, content: Any, source: str = "external") -> WorkspaceContent:
        """Inject content into workspace."""
        return self._conscious_access.inject(content, source)

    def focus(self, content_id: str) -> bool:
        """Focus attention on content."""
        for content in self._workspace.current_contents:
            if content.id == content_id:
                self._conscious_access.focus_on(content)
                return True
        return False

    def set_attention_bias(self, topic: str, weight: float) -> None:
        """Set attention bias."""
        self._attention.set_topic_bias(topic, weight)

    def step(self) -> Optional[Broadcast]:
        """Execute one step."""
        return self._attention.step()

    def run_sync(self, steps: int = 100) -> List[Broadcast]:
        """Run synchronously for steps."""
        broadcasts = []
        for _ in range(steps):
            broadcast = self.step()
            if broadcast:
                broadcasts.append(broadcast)
        return broadcasts

    def start_async(self, step_delay: float = 0.1) -> None:
        """Start asynchronous operation."""
        with self._lock:
            if self._running:
                return

            self._running = True

            def run_loop():
                while self._running:
                    self.step()
                    time.sleep(step_delay)

            self._thread = threading.Thread(target=run_loop, daemon=True)
            self._thread.start()

    def stop_async(self) -> None:
        """Stop asynchronous operation."""
        with self._lock:
            self._running = False
            if self._thread:
                self._thread.join(timeout=1.0)
                self._thread = None

    def get_broadcasts(self, n: int = 10) -> List[Dict]:
        """Get recent broadcasts."""
        broadcasts = self._conscious_access.get_recent(n)
        return [
            {
                'id': b.id,
                'content': str(b.content.content)[:100],
                'source': b.content.source_processor,
                'recipients': len(b.recipients),
                'acknowledged': len(b.acknowledged_by)
            }
            for b in broadcasts
        ]

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'workspace': self._workspace.state,
            'running': self._running,
            'focused': self._conscious_access.is_focused
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_global_workspace_engine(capacity: int = 7) -> GlobalWorkspaceEngine:
    """Create global workspace engine."""
    return GlobalWorkspaceEngine(capacity)


def create_global_workspace(capacity: int = 7) -> GlobalWorkspace:
    """Create global workspace."""
    return GlobalWorkspace(capacity)


def create_processor(
    name: str,
    processor_type: ProcessorType,
    content_generator: Optional[Callable[[], Any]] = None
) -> GenericProcessor:
    """Create generic processor."""
    return GenericProcessor(name, processor_type, content_generator)


def create_workspace_content(
    content: Any,
    source: str = "external",
    activation: float = 0.5
) -> WorkspaceContent:
    """Create workspace content."""
    return WorkspaceContent(
        id=f"content_{time.time()}",
        content=content,
        source_processor=source,
        activation=activation
    )
