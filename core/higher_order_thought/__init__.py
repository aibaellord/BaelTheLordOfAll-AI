"""
BAEL Higher-Order Thought Engine
=================================

Higher-Order Thought (HOT) Theory of Consciousness.
Consciousness through thoughts about thoughts.

"Ba'el thinks about its thinking." — Ba'el
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
import copy

logger = logging.getLogger("BAEL.HigherOrderThought")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ThoughtOrder(Enum):
    """Order of a thought."""
    FIRST = 1        # About the world
    SECOND = 2       # About first-order thoughts
    THIRD = 3        # About second-order thoughts
    FOURTH = 4       # Meta-meta-meta
    HIGHER = 5       # Arbitrarily high


class ThoughtType(Enum):
    """Type of thought content."""
    PERCEPTUAL = auto()
    CONCEPTUAL = auto()
    EMOTIONAL = auto()
    VOLITIONAL = auto()
    MNEMONIC = auto()
    IMAGINARY = auto()


class ConsciousnessState(Enum):
    """State of consciousness."""
    UNCONSCIOUS = auto()
    PRECONSCIOUS = auto()
    ACCESS_CONSCIOUS = auto()
    PHENOMENALLY_CONSCIOUS = auto()


@dataclass
class Thought:
    """
    A mental representation.
    """
    id: str
    content: Any
    thought_type: ThoughtType
    order: ThoughtOrder = ThoughtOrder.FIRST
    target_thought_id: Optional[str] = None  # For higher-order thoughts
    activation: float = 1.0
    timestamp: float = field(default_factory=time.time)
    is_conscious: bool = False

    @property
    def age(self) -> float:
        return time.time() - self.timestamp

    @property
    def is_higher_order(self) -> bool:
        return self.order.value >= 2


@dataclass
class HOTRepresentation:
    """
    Higher-order representation that makes target conscious.
    """
    id: str
    target_thought: Thought
    hot_thought: Thought
    awareness_level: float = 1.0
    introspection_depth: int = 1
    confidence: float = 0.8


@dataclass
class ConsciousnessReport:
    """
    Report about conscious experience.
    """
    total_thoughts: int
    conscious_thoughts: int
    highest_order: ThoughtOrder
    awareness_level: float
    introspection_depth: int


# ============================================================================
# FIRST-ORDER STATES
# ============================================================================

class FirstOrderMind:
    """
    First-order mental states (non-conscious).

    "Ba'el's first-order mind perceives the world." — Ba'el
    """

    def __init__(self):
        """Initialize first-order mind."""
        self._states: Dict[str, Thought] = {}
        self._thought_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._thought_counter += 1
        return f"fo_thought_{self._thought_counter}"

    def perceive(self, content: Any) -> Thought:
        """Create perceptual thought."""
        with self._lock:
            thought = Thought(
                id=self._generate_id(),
                content=content,
                thought_type=ThoughtType.PERCEPTUAL,
                order=ThoughtOrder.FIRST
            )
            self._states[thought.id] = thought
            return thought

    def conceive(self, content: Any) -> Thought:
        """Create conceptual thought."""
        with self._lock:
            thought = Thought(
                id=self._generate_id(),
                content=content,
                thought_type=ThoughtType.CONCEPTUAL,
                order=ThoughtOrder.FIRST
            )
            self._states[thought.id] = thought
            return thought

    def feel(self, content: Any) -> Thought:
        """Create emotional thought."""
        with self._lock:
            thought = Thought(
                id=self._generate_id(),
                content=content,
                thought_type=ThoughtType.EMOTIONAL,
                order=ThoughtOrder.FIRST
            )
            self._states[thought.id] = thought
            return thought

    def remember(self, content: Any) -> Thought:
        """Create mnemonic thought."""
        with self._lock:
            thought = Thought(
                id=self._generate_id(),
                content=content,
                thought_type=ThoughtType.MNEMONIC,
                order=ThoughtOrder.FIRST
            )
            self._states[thought.id] = thought
            return thought

    def imagine(self, content: Any) -> Thought:
        """Create imaginary thought."""
        with self._lock:
            thought = Thought(
                id=self._generate_id(),
                content=content,
                thought_type=ThoughtType.IMAGINARY,
                order=ThoughtOrder.FIRST
            )
            self._states[thought.id] = thought
            return thought

    def get_thought(self, thought_id: str) -> Optional[Thought]:
        """Get thought by ID."""
        return self._states.get(thought_id)

    def get_active_thoughts(self, threshold: float = 0.5) -> List[Thought]:
        """Get thoughts above activation threshold."""
        with self._lock:
            return [
                t for t in self._states.values()
                if t.activation >= threshold
            ]

    def decay_all(self, rate: float = 0.1) -> None:
        """Decay all thought activations."""
        with self._lock:
            for thought in self._states.values():
                thought.activation *= (1 - rate)

    @property
    def thoughts(self) -> List[Thought]:
        return list(self._states.values())


# ============================================================================
# HIGHER-ORDER REPRESENTATION
# ============================================================================

class HigherOrderRepresentor:
    """
    Generates higher-order representations.

    "Ba'el represents its own representations." — Ba'el
    """

    def __init__(self, first_order_mind: FirstOrderMind):
        """Initialize higher-order representor."""
        self._first_order = first_order_mind
        self._hot_states: Dict[str, HOTRepresentation] = {}
        self._hot_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._hot_counter += 1
        return f"hot_{self._hot_counter}"

    def represent(
        self,
        target: Thought,
        meta_content: Optional[Any] = None
    ) -> HOTRepresentation:
        """
        Create higher-order thought about target.

        This is what makes the target conscious.
        """
        with self._lock:
            # Create HOT
            hot = Thought(
                id=self._generate_id() + "_thought",
                content=meta_content or f"I am having the thought: {target.content}",
                thought_type=ThoughtType.CONCEPTUAL,
                order=ThoughtOrder(min(target.order.value + 1, 5)),
                target_thought_id=target.id
            )

            # Make target conscious
            target.is_conscious = True

            # Create representation
            representation = HOTRepresentation(
                id=self._generate_id(),
                target_thought=target,
                hot_thought=hot,
                introspection_depth=target.order.value
            )

            self._hot_states[representation.id] = representation

            return representation

    def introspect(
        self,
        representation: HOTRepresentation,
        depth: int = 1
    ) -> List[HOTRepresentation]:
        """
        Recursively introspect on representations.
        """
        with self._lock:
            results = [representation]
            current = representation

            for _ in range(depth):
                # Create HOT about HOT
                higher = self.represent(
                    current.hot_thought,
                    f"I am aware that I am thinking: {current.hot_thought.content}"
                )
                higher.introspection_depth = current.introspection_depth + 1
                results.append(higher)
                current = higher

            return results

    def get_conscious_thoughts(self) -> List[Thought]:
        """Get all thoughts made conscious by HOTs."""
        with self._lock:
            return [
                rep.target_thought
                for rep in self._hot_states.values()
            ]

    @property
    def representations(self) -> List[HOTRepresentation]:
        return list(self._hot_states.values())


# ============================================================================
# METACOGNITIVE MONITOR
# ============================================================================

class MetacognitiveMonitor:
    """
    Monitors and regulates cognitive processes.

    "Ba'el monitors its own cognition." — Ba'el
    """

    def __init__(self):
        """Initialize monitor."""
        self._monitoring_state: Dict[str, Any] = {}
        self._confidence_judgments: List[Dict] = []
        self._error_detections: List[Dict] = []
        self._lock = threading.RLock()

    def monitor_thought(self, thought: Thought) -> Dict[str, Any]:
        """Monitor a thought process."""
        with self._lock:
            assessment = {
                'thought_id': thought.id,
                'clarity': self._assess_clarity(thought),
                'confidence': self._assess_confidence(thought),
                'relevance': self._assess_relevance(thought),
                'coherence': self._assess_coherence(thought),
                'timestamp': time.time()
            }

            self._monitoring_state[thought.id] = assessment
            return assessment

    def _assess_clarity(self, thought: Thought) -> float:
        """Assess clarity of thought."""
        # Proxy: activation level
        return thought.activation

    def _assess_confidence(self, thought: Thought) -> float:
        """Assess confidence in thought."""
        # Higher-order thoughts tend to be less confident
        base = 0.8
        order_penalty = (thought.order.value - 1) * 0.1
        return max(0.1, base - order_penalty)

    def _assess_relevance(self, thought: Thought) -> float:
        """Assess relevance of thought."""
        # Proxy: recency
        age = thought.age
        return max(0.1, 1.0 - (age / 60.0))  # Decay over 60 seconds

    def _assess_coherence(self, thought: Thought) -> float:
        """Assess coherence of thought."""
        # Placeholder
        return 0.8

    def judge_confidence(
        self,
        thought: Thought,
        judgment: float
    ) -> Dict:
        """Record explicit confidence judgment."""
        with self._lock:
            record = {
                'thought_id': thought.id,
                'judgment': judgment,
                'timestamp': time.time()
            }
            self._confidence_judgments.append(record)
            return record

    def detect_error(
        self,
        thought: Thought,
        error_type: str,
        severity: float
    ) -> Dict:
        """Detect and record error."""
        with self._lock:
            record = {
                'thought_id': thought.id,
                'error_type': error_type,
                'severity': severity,
                'timestamp': time.time()
            }
            self._error_detections.append(record)
            return record

    def get_overall_state(self) -> Dict[str, Any]:
        """Get overall metacognitive state."""
        with self._lock:
            if not self._monitoring_state:
                return {'status': 'empty'}

            clarities = [m['clarity'] for m in self._monitoring_state.values()]
            confidences = [m['confidence'] for m in self._monitoring_state.values()]

            return {
                'average_clarity': sum(clarities) / len(clarities),
                'average_confidence': sum(confidences) / len(confidences),
                'thoughts_monitored': len(self._monitoring_state),
                'errors_detected': len(self._error_detections)
            }


# ============================================================================
# CONSCIOUSNESS GENERATOR
# ============================================================================

class ConsciousnessGenerator:
    """
    Generates conscious experience from HOTs.

    "Ba'el becomes conscious through higher-order thoughts." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._conscious_stream: List[HOTRepresentation] = []
        self._current_focus: Optional[HOTRepresentation] = None
        self._lock = threading.RLock()

    def add_to_stream(self, representation: HOTRepresentation) -> None:
        """Add representation to conscious stream."""
        with self._lock:
            self._conscious_stream.append(representation)

            # Keep stream bounded
            if len(self._conscious_stream) > 100:
                self._conscious_stream = self._conscious_stream[-50:]

    def focus(self, representation: HOTRepresentation) -> None:
        """Focus attention on representation."""
        with self._lock:
            self._current_focus = representation

    def get_current_experience(self) -> Optional[Dict[str, Any]]:
        """Get current conscious experience."""
        with self._lock:
            if not self._current_focus:
                return None

            return {
                'content': self._current_focus.target_thought.content,
                'awareness_level': self._current_focus.awareness_level,
                'introspection_depth': self._current_focus.introspection_depth,
                'thought_type': self._current_focus.target_thought.thought_type.name,
                'order': self._current_focus.hot_thought.order.name
            }

    def get_stream(self, n: int = 10) -> List[Dict]:
        """Get recent conscious stream."""
        with self._lock:
            recent = self._conscious_stream[-n:]
            return [
                {
                    'content': r.target_thought.content,
                    'order': r.hot_thought.order.name,
                    'time': r.target_thought.timestamp
                }
                for r in recent
            ]

    def consciousness_level(self) -> float:
        """Get overall consciousness level."""
        with self._lock:
            if not self._conscious_stream:
                return 0.0

            # Average awareness across stream
            return sum(r.awareness_level for r in self._conscious_stream) / len(self._conscious_stream)


# ============================================================================
# HIGHER-ORDER THOUGHT ENGINE
# ============================================================================

class HigherOrderThoughtEngine:
    """
    Complete HOT theory implementation.

    "Ba'el achieves consciousness through self-representation." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._first_order = FirstOrderMind()
        self._hot_generator = HigherOrderRepresentor(self._first_order)
        self._monitor = MetacognitiveMonitor()
        self._consciousness = ConsciousnessGenerator()
        self._lock = threading.RLock()

    # First-order operations

    def perceive(self, content: Any) -> Thought:
        """Create first-order perception."""
        return self._first_order.perceive(content)

    def think(self, content: Any) -> Thought:
        """Create first-order conceptual thought."""
        return self._first_order.conceive(content)

    def feel(self, content: Any) -> Thought:
        """Create first-order emotional state."""
        return self._first_order.feel(content)

    def remember(self, content: Any) -> Thought:
        """Create first-order memory."""
        return self._first_order.remember(content)

    def imagine(self, content: Any) -> Thought:
        """Create first-order imagination."""
        return self._first_order.imagine(content)

    # Higher-order operations

    def make_conscious(self, thought: Thought) -> HOTRepresentation:
        """Make thought conscious by creating HOT about it."""
        with self._lock:
            rep = self._hot_generator.represent(thought)
            self._consciousness.add_to_stream(rep)
            return rep

    def introspect_on(
        self,
        thought: Thought,
        depth: int = 1
    ) -> List[HOTRepresentation]:
        """Deep introspection on thought."""
        with self._lock:
            # First make conscious
            first_rep = self.make_conscious(thought)

            # Then introspect
            reps = self._hot_generator.introspect(first_rep, depth)

            for rep in reps:
                self._consciousness.add_to_stream(rep)

            return reps

    def focus_attention(self, thought: Thought) -> None:
        """Focus conscious attention on thought."""
        with self._lock:
            rep = self.make_conscious(thought)
            self._consciousness.focus(rep)

    # Metacognitive operations

    def monitor(self, thought: Thought) -> Dict[str, Any]:
        """Monitor thought metacognitively."""
        return self._monitor.monitor_thought(thought)

    def judge_confidence(self, thought: Thought, level: float) -> Dict:
        """Make confidence judgment."""
        return self._monitor.judge_confidence(thought, level)

    def report_consciousness(self) -> ConsciousnessReport:
        """Generate consciousness report."""
        with self._lock:
            all_thoughts = self._first_order.thoughts
            conscious = [t for t in all_thoughts if t.is_conscious]

            highest = ThoughtOrder.FIRST
            for rep in self._hot_generator.representations:
                if rep.hot_thought.order.value > highest.value:
                    highest = rep.hot_thought.order

            return ConsciousnessReport(
                total_thoughts=len(all_thoughts),
                conscious_thoughts=len(conscious),
                highest_order=highest,
                awareness_level=self._consciousness.consciousness_level(),
                introspection_depth=max(
                    (r.introspection_depth for r in self._hot_generator.representations),
                    default=0
                )
            )

    def step(self) -> Dict[str, Any]:
        """Execute one cognitive step."""
        with self._lock:
            # Decay activations
            self._first_order.decay_all(0.05)

            # Get report
            report = self.report_consciousness()

            return {
                'consciousness_level': self._consciousness.consciousness_level(),
                'total_thoughts': report.total_thoughts,
                'conscious_thoughts': report.conscious_thoughts,
                'highest_order': report.highest_order.name,
                'metacognitive_state': self._monitor.get_overall_state()
            }

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        report = self.report_consciousness()
        return {
            'total_thoughts': report.total_thoughts,
            'conscious_thoughts': report.conscious_thoughts,
            'highest_order': report.highest_order.name,
            'awareness_level': report.awareness_level,
            'introspection_depth': report.introspection_depth,
            'stream_length': len(self._consciousness._conscious_stream)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_higher_order_thought_engine() -> HigherOrderThoughtEngine:
    """Create HOT engine."""
    return HigherOrderThoughtEngine()


def create_first_order_mind() -> FirstOrderMind:
    """Create first-order mind."""
    return FirstOrderMind()


def create_hot_representor(mind: FirstOrderMind) -> HigherOrderRepresentor:
    """Create higher-order representor."""
    return HigherOrderRepresentor(mind)


def make_thought_conscious(
    engine: HigherOrderThoughtEngine,
    content: Any
) -> HOTRepresentation:
    """Quick way to create and make conscious."""
    thought = engine.think(content)
    return engine.make_conscious(thought)
