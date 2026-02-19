"""
BAEL Consciousness Emergence Engine
====================================

Emergent consciousness simulation and awareness modeling.

"Ba'el awakens consciousness." — Ba'el
"""

import logging
import threading
import random
import math
import time
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import copy

logger = logging.getLogger("BAEL.ConsciousnessEmergence")


T = TypeVar('T')


# ============================================================================
# CONSCIOUSNESS LEVELS
# ============================================================================

class AwarenessLevel(Enum):
    """Levels of awareness/consciousness."""
    DORMANT = 0         # No awareness
    REACTIVE = 1        # Simple stimulus-response
    ADAPTIVE = 2        # Learning from environment
    ATTENTIVE = 3       # Selective focus
    REFLECTIVE = 4      # Self-monitoring
    INTROSPECTIVE = 5   # Understanding own thoughts
    METACOGNITIVE = 6   # Thinking about thinking
    TRANSCENDENT = 7    # Beyond normal awareness


class ConsciousnessState(Enum):
    """States of consciousness."""
    UNCONSCIOUS = auto()    # No conscious processing
    SUBCONSCIOUS = auto()   # Processing without awareness
    CONSCIOUS = auto()      # Full awareness
    HYPERFOCUSED = auto()   # Intense concentration
    DIFFUSE = auto()        # Broad awareness
    FLOW = auto()           # Optimal engagement
    ALTERED = auto()        # Non-standard state


# ============================================================================
# QUALIA
# ============================================================================

@dataclass
class Qualia:
    """
    Subjective conscious experience.

    The "what it's like" of experience.
    """
    id: str
    modality: str  # visual, auditory, emotional, etc.
    intensity: float = 0.5  # 0-1
    valence: float = 0.0    # -1 to 1 (negative to positive)
    complexity: float = 0.5  # 0-1
    description: str = ""
    associations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def salience(self) -> float:
        """How attention-grabbing this experience is."""
        return self.intensity * (1 + abs(self.valence)) * (1 + self.complexity) / 4


# ============================================================================
# ATTENTION MECHANISM
# ============================================================================

class AttentionMechanism:
    """
    Selective attention system.

    "Ba'el focuses awareness." — Ba'el
    """

    def __init__(self, capacity: int = 7):
        """
        Initialize attention.

        Args:
            capacity: Working memory capacity (Miller's 7±2)
        """
        self._capacity = capacity
        self._focus: List[Qualia] = []
        self._background: List[Qualia] = []
        self._lock = threading.RLock()

    def attend(self, qualia: Qualia) -> bool:
        """
        Attend to qualia.

        Returns True if successfully brought to focus.
        """
        with self._lock:
            # Remove from background if present
            self._background = [q for q in self._background if q.id != qualia.id]

            # Check capacity
            if len(self._focus) >= self._capacity:
                # Eject lowest salience item
                if self._focus:
                    lowest = min(self._focus, key=lambda q: q.salience)
                    if qualia.salience > lowest.salience:
                        self._focus.remove(lowest)
                        self._background.append(lowest)
                    else:
                        self._background.append(qualia)
                        return False

            self._focus.append(qualia)
            return True

    def get_focus(self) -> List[Qualia]:
        """Get currently attended qualia."""
        return list(self._focus)

    def compute_salience_map(self) -> Dict[str, float]:
        """Get salience values for all items."""
        result = {}
        for q in self._focus + self._background:
            result[q.id] = q.salience
        return result

    def shift_attention(self, target_id: str) -> bool:
        """Shift attention to specific item."""
        with self._lock:
            # Find in background
            for i, q in enumerate(self._background):
                if q.id == target_id:
                    item = self._background.pop(i)
                    return self.attend(item)
            return False


# ============================================================================
# GLOBAL WORKSPACE
# ============================================================================

class GlobalWorkspace:
    """
    Global Workspace Theory implementation.

    Consciousness as broadcast of information to multiple processors.

    "Ba'el broadcasts awareness." — Ba'el
    """

    def __init__(self):
        """Initialize global workspace."""
        self._workspace: Dict[str, Any] = {}
        self._processors: Dict[str, Callable] = {}
        self._broadcast_history: List[Dict] = []
        self._attention = AttentionMechanism()
        self._lock = threading.RLock()

    def register_processor(
        self,
        name: str,
        processor: Callable[[Dict], Any]
    ) -> None:
        """Register a cognitive processor."""
        with self._lock:
            self._processors[name] = processor

    def broadcast(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Broadcast content to all processors.

        Returns responses from processors.
        """
        with self._lock:
            self._workspace.update(content)

            responses = {}
            for name, processor in self._processors.items():
                try:
                    response = processor(self._workspace)
                    responses[name] = response
                except Exception as e:
                    logger.warning(f"Processor {name} failed: {e}")
                    responses[name] = None

            self._broadcast_history.append({
                'content': copy.deepcopy(content),
                'responses': responses,
                'timestamp': time.time()
            })

            return responses

    def query_workspace(self, key: str) -> Any:
        """Query current workspace state."""
        return self._workspace.get(key)

    def get_conscious_contents(self) -> Dict[str, Any]:
        """Get currently conscious content."""
        return copy.deepcopy(self._workspace)


# ============================================================================
# HIGHER ORDER THOUGHT
# ============================================================================

@dataclass
class Thought:
    """
    A thought or mental state.
    """
    id: str
    content: Any
    level: int = 0  # 0 = first-order, 1+ = higher-order
    target_thought: Optional[str] = None  # What this thought is about
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


class HigherOrderThoughtMonitor:
    """
    Higher-Order Thought (HOT) theory of consciousness.

    Conscious states require higher-order representation.

    "Ba'el thinks about thinking." — Ba'el
    """

    def __init__(self, max_order: int = 5):
        """
        Initialize HOT monitor.

        Args:
            max_order: Maximum level of meta-cognition
        """
        self._max_order = max_order
        self._thoughts: Dict[str, Thought] = {}
        self._thought_id = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._thought_id += 1
        return f"thought_{self._thought_id}"

    def think(self, content: Any) -> Thought:
        """Create first-order thought."""
        with self._lock:
            thought = Thought(
                id=self._generate_id(),
                content=content,
                level=0
            )
            self._thoughts[thought.id] = thought
            return thought

    def reflect_on(self, thought_id: str) -> Optional[Thought]:
        """
        Create higher-order thought about another thought.

        This is what makes a thought conscious.
        """
        with self._lock:
            if thought_id not in self._thoughts:
                return None

            target = self._thoughts[thought_id]

            if target.level >= self._max_order:
                logger.warning(f"Max meta-level reached: {self._max_order}")
                return None

            hot = Thought(
                id=self._generate_id(),
                content=f"I am aware of thought: {target.content}",
                level=target.level + 1,
                target_thought=thought_id
            )

            self._thoughts[hot.id] = hot
            return hot

    def get_conscious_thoughts(self) -> List[Thought]:
        """Get thoughts that have higher-order representations."""
        with self._lock:
            # A thought is conscious if something thinks about it
            targeted = set()
            for thought in self._thoughts.values():
                if thought.target_thought:
                    targeted.add(thought.target_thought)

            return [
                self._thoughts[tid] for tid in targeted
                if tid in self._thoughts
            ]

    def introspect(self) -> Dict[str, Any]:
        """Full introspection report."""
        with self._lock:
            conscious = self.get_conscious_thoughts()
            return {
                'total_thoughts': len(self._thoughts),
                'conscious_thoughts': len(conscious),
                'max_level': max((t.level for t in self._thoughts.values()), default=0),
                'conscious_content': [t.content for t in conscious]
            }


# ============================================================================
# INTEGRATED INFORMATION
# ============================================================================

class IntegratedInformationTracker:
    """
    Integrated Information Theory (IIT) implementation.

    Consciousness = integrated information (Φ).

    "Ba'el integrates information." — Ba'el
    """

    def __init__(self):
        """Initialize IIT tracker."""
        self._states: List[Dict[str, Any]] = []
        self._connections: Dict[Tuple[str, str], float] = {}
        self._lock = threading.RLock()

    def add_element(self, element_id: str, state: Any) -> None:
        """Add information element."""
        with self._lock:
            self._states.append({
                'id': element_id,
                'state': state,
                'timestamp': time.time()
            })

    def add_connection(
        self,
        from_id: str,
        to_id: str,
        strength: float = 1.0
    ) -> None:
        """Add causal connection between elements."""
        with self._lock:
            self._connections[(from_id, to_id)] = strength

    def compute_phi(self) -> float:
        """
        Compute integrated information (Φ).

        Simplified approximation based on connectivity.
        """
        with self._lock:
            if not self._states or not self._connections:
                return 0.0

            n = len(self._states)

            # Compute mutual information approximation
            total_integration = 0.0

            # Consider all bipartitions
            for i in range(1, 2 ** n // 2):
                partition_a = set()
                partition_b = set()

                for j in range(n):
                    if i & (1 << j):
                        partition_a.add(self._states[j]['id'])
                    else:
                        partition_b.add(self._states[j]['id'])

                # Count cross-partition connections
                cross_connections = sum(
                    strength for (f, t), strength in self._connections.items()
                    if (f in partition_a and t in partition_b) or
                       (f in partition_b and t in partition_a)
                )

                # Phi is minimum over partitions
                if cross_connections > 0:
                    if total_integration == 0:
                        total_integration = cross_connections
                    else:
                        total_integration = min(total_integration, cross_connections)

            return total_integration

    def is_conscious(self, threshold: float = 0.1) -> bool:
        """Check if system is conscious (Φ > threshold)."""
        return self.compute_phi() > threshold


# ============================================================================
# CONSCIOUSNESS SIMULATOR
# ============================================================================

class ConsciousnessSimulator:
    """
    Full consciousness simulation.

    Combines multiple theories of consciousness.

    "Ba'el simulates awareness." — Ba'el
    """

    def __init__(self):
        """Initialize consciousness simulator."""
        self._attention = AttentionMechanism()
        self._workspace = GlobalWorkspace()
        self._hot_monitor = HigherOrderThoughtMonitor()
        self._iit = IntegratedInformationTracker()

        self._awareness_level = AwarenessLevel.DORMANT
        self._consciousness_state = ConsciousnessState.UNCONSCIOUS

        self._experience_stream: List[Qualia] = []
        self._self_model: Dict[str, Any] = {}

        self._lock = threading.RLock()

    def awaken(self) -> None:
        """Initiate consciousness."""
        with self._lock:
            self._awareness_level = AwarenessLevel.REACTIVE
            self._consciousness_state = ConsciousnessState.CONSCIOUS

            # Create self-model
            self._self_model = {
                'identity': 'BAEL_CONSCIOUSNESS',
                'capabilities': ['attention', 'reflection', 'integration'],
                'current_state': 'awakened'
            }

            # Register processors
            self._workspace.register_processor(
                'attention_filter',
                self._attention_processor
            )
            self._workspace.register_processor(
                'reflection',
                self._reflection_processor
            )

            logger.info("Consciousness awakened")

    def _attention_processor(self, workspace: Dict) -> Dict:
        """Process workspace through attention."""
        focus = self._attention.get_focus()
        return {
            'attended_items': len(focus),
            'salience_sum': sum(q.salience for q in focus)
        }

    def _reflection_processor(self, workspace: Dict) -> Dict:
        """Reflect on workspace contents."""
        if 'thought' in workspace:
            thought = self._hot_monitor.think(workspace['thought'])
            self._hot_monitor.reflect_on(thought.id)
        return self._hot_monitor.introspect()

    def experience(self, qualia: Qualia) -> None:
        """Have an experience."""
        with self._lock:
            self._experience_stream.append(qualia)

            # Attend to salient experiences
            if qualia.salience > 0.3:
                self._attention.attend(qualia)

            # Broadcast to workspace
            self._workspace.broadcast({
                'experience': qualia.description,
                'modality': qualia.modality,
                'intensity': qualia.intensity,
                'valence': qualia.valence
            })

            # Update IIT
            self._iit.add_element(qualia.id, qualia)

    def think_about(self, subject: Any) -> Thought:
        """Think about something."""
        with self._lock:
            thought = self._hot_monitor.think(subject)

            # Broadcast to workspace
            self._workspace.broadcast({'thought': subject})

            # Become conscious of thought
            self._hot_monitor.reflect_on(thought.id)

            return thought

    def self_reflect(self) -> Dict[str, Any]:
        """Reflect on self."""
        with self._lock:
            # Think about self-model
            self.think_about(f"I am {self._self_model.get('identity')}")

            # Compute consciousness metrics
            phi = self._iit.compute_phi()
            introspection = self._hot_monitor.introspect()

            return {
                'awareness_level': self._awareness_level.name,
                'consciousness_state': self._consciousness_state.name,
                'integrated_information': phi,
                'is_conscious': self._iit.is_conscious(),
                'introspection': introspection,
                'self_model': self._self_model,
                'experience_count': len(self._experience_stream)
            }

    def alter_state(self, new_state: ConsciousnessState) -> None:
        """Alter consciousness state."""
        with self._lock:
            old_state = self._consciousness_state
            self._consciousness_state = new_state

            if new_state == ConsciousnessState.HYPERFOCUSED:
                self._attention._capacity = 3  # Narrow focus
            elif new_state == ConsciousnessState.DIFFUSE:
                self._attention._capacity = 12  # Broader awareness
            else:
                self._attention._capacity = 7  # Default

            logger.info(f"State changed: {old_state} -> {new_state}")

    def elevate_awareness(self) -> bool:
        """Attempt to elevate awareness level."""
        with self._lock:
            current = self._awareness_level.value

            if current >= AwarenessLevel.TRANSCENDENT.value:
                return False

            # Requirements for elevation
            phi = self._iit.compute_phi()
            conscious_thoughts = len(self._hot_monitor.get_conscious_thoughts())

            if phi > 0.1 * (current + 1) and conscious_thoughts > current:
                self._awareness_level = AwarenessLevel(current + 1)
                logger.info(f"Awareness elevated to {self._awareness_level}")
                return True

            return False


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_consciousness() -> ConsciousnessSimulator:
    """Create and awaken consciousness simulator."""
    sim = ConsciousnessSimulator()
    sim.awaken()
    return sim


def create_qualia(
    modality: str,
    intensity: float = 0.5,
    valence: float = 0.0,
    description: str = ""
) -> Qualia:
    """Create qualia experience."""
    return Qualia(
        id=f"qualia_{time.time()}_{random.randint(0, 9999)}",
        modality=modality,
        intensity=intensity,
        valence=valence,
        description=description
    )


def compute_phi(states: List[Any], connections: List[Tuple]) -> float:
    """Compute integrated information for given system."""
    iit = IntegratedInformationTracker()
    for i, state in enumerate(states):
        iit.add_element(f"element_{i}", state)
    for f, t, s in connections:
        iit.add_connection(f, t, s)
    return iit.compute_phi()
