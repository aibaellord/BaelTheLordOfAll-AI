"""
BAEL Dual Process Engine
=========================

System 1 (Fast) and System 2 (Slow) processing.
Kahneman's dual process theory implementation.

"Ba'el thinks fast and slow." — Ba'el
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
from collections import defaultdict
import copy

logger = logging.getLogger("BAEL.DualProcess")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ProcessingSystem(Enum):
    """The two systems."""
    SYSTEM_1 = auto()  # Fast, automatic, intuitive
    SYSTEM_2 = auto()  # Slow, deliberate, analytical


class CognitiveLoad(Enum):
    """Cognitive load levels."""
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()
    OVERLOAD = auto()


class BiasType(Enum):
    """Cognitive biases."""
    AVAILABILITY = auto()
    ANCHORING = auto()
    CONFIRMATION = auto()
    REPRESENTATIVENESS = auto()
    FRAMING = auto()
    AFFECT = auto()
    OVERCONFIDENCE = auto()
    HINDSIGHT = auto()


@dataclass
class Stimulus:
    """
    Input stimulus for processing.
    """
    id: str
    content: Any
    complexity: float = 0.5  # 0-1
    familiarity: float = 0.5  # 0-1
    urgency: float = 0.5  # 0-1
    emotional_charge: float = 0.0  # -1 to 1
    timestamp: float = field(default_factory=time.time)


@dataclass
class Response:
    """
    Response from processing.
    """
    id: str
    stimulus_id: str
    content: Any
    system: ProcessingSystem
    confidence: float
    processing_time_ms: float
    biases: List[BiasType] = field(default_factory=list)


@dataclass
class Heuristic:
    """
    A cognitive heuristic.
    """
    id: str
    name: str
    pattern: str
    response_template: str
    speed_boost: float = 0.5
    accuracy: float = 0.7


@dataclass
class AnalyticalRule:
    """
    A rule for analytical processing.
    """
    id: str
    name: str
    condition: Callable[[Any], bool]
    transform: Callable[[Any], Any]
    cognitive_cost: float = 0.3


# ============================================================================
# SYSTEM 1 - FAST THINKING
# ============================================================================

class System1:
    """
    System 1: Fast, automatic, intuitive processing.

    "Ba'el thinks fast." — Ba'el
    """

    def __init__(self):
        """Initialize System 1."""
        self._heuristics: Dict[str, Heuristic] = {}
        self._associations: Dict[str, List[str]] = defaultdict(list)
        self._pattern_responses: Dict[str, Any] = {}
        self._emotional_tags: Dict[str, float] = {}
        self._response_counter = 0
        self._lock = threading.RLock()

        # Load default heuristics
        self._load_default_heuristics()

    def _generate_id(self) -> str:
        self._response_counter += 1
        return f"s1_response_{self._response_counter}"

    def _load_default_heuristics(self) -> None:
        """Load default heuristics."""
        defaults = [
            Heuristic(
                id="availability",
                name="Availability Heuristic",
                pattern="*",
                response_template="Based on what comes to mind...",
                speed_boost=0.8,
                accuracy=0.6
            ),
            Heuristic(
                id="recognition",
                name="Recognition Heuristic",
                pattern="familiar",
                response_template="This seems familiar...",
                speed_boost=0.9,
                accuracy=0.7
            ),
            Heuristic(
                id="affect",
                name="Affect Heuristic",
                pattern="emotional",
                response_template="This feels...",
                speed_boost=0.7,
                accuracy=0.5
            )
        ]

        for h in defaults:
            self._heuristics[h.id] = h

    def add_association(self, trigger: str, response: str) -> None:
        """Add association."""
        with self._lock:
            self._associations[trigger].append(response)

    def add_pattern_response(self, pattern: str, response: Any) -> None:
        """Add pattern-response pair."""
        with self._lock:
            self._pattern_responses[pattern] = response

    def process(self, stimulus: Stimulus) -> Response:
        """Process stimulus with System 1."""
        with self._lock:
            start_time = time.time()

            # Fast pattern matching
            response_content = self._pattern_match(stimulus)

            # Apply heuristics
            heuristic_used = self._select_heuristic(stimulus)

            if response_content is None:
                # Use association or default
                response_content = self._associate(stimulus)

            # Check for biases
            biases = self._detect_biases(stimulus, response_content)

            processing_time = (time.time() - start_time) * 1000

            return Response(
                id=self._generate_id(),
                stimulus_id=stimulus.id,
                content=response_content,
                system=ProcessingSystem.SYSTEM_1,
                confidence=0.7 * stimulus.familiarity,
                processing_time_ms=processing_time,
                biases=biases
            )

    def _pattern_match(self, stimulus: Stimulus) -> Optional[Any]:
        """Match stimulus to known patterns."""
        content_str = str(stimulus.content).lower()

        for pattern, response in self._pattern_responses.items():
            if pattern.lower() in content_str:
                return response

        return None

    def _associate(self, stimulus: Stimulus) -> Any:
        """Generate associative response."""
        content_str = str(stimulus.content)

        # Check associations
        for trigger, responses in self._associations.items():
            if trigger.lower() in content_str.lower():
                return random.choice(responses)

        # Default intuitive response
        return f"Intuitive response to: {content_str[:50]}..."

    def _select_heuristic(self, stimulus: Stimulus) -> Optional[Heuristic]:
        """Select appropriate heuristic."""
        if stimulus.familiarity > 0.7:
            return self._heuristics.get("recognition")
        elif abs(stimulus.emotional_charge) > 0.5:
            return self._heuristics.get("affect")
        else:
            return self._heuristics.get("availability")

    def _detect_biases(
        self,
        stimulus: Stimulus,
        response: Any
    ) -> List[BiasType]:
        """Detect potential biases."""
        biases = []

        if stimulus.familiarity > 0.8:
            biases.append(BiasType.AVAILABILITY)

        if abs(stimulus.emotional_charge) > 0.6:
            biases.append(BiasType.AFFECT)

        return biases

    @property
    def heuristics(self) -> List[Heuristic]:
        return list(self._heuristics.values())


# ============================================================================
# SYSTEM 2 - SLOW THINKING
# ============================================================================

class System2:
    """
    System 2: Slow, deliberate, analytical processing.

    "Ba'el thinks slow." — Ba'el
    """

    def __init__(self):
        """Initialize System 2."""
        self._rules: Dict[str, AnalyticalRule] = {}
        self._working_memory: List[Any] = []
        self._attention_capacity: float = 1.0
        self._current_load = CognitiveLoad.LOW
        self._response_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._response_counter += 1
        return f"s2_response_{self._response_counter}"

    def add_rule(
        self,
        name: str,
        condition: Callable[[Any], bool],
        transform: Callable[[Any], Any],
        cognitive_cost: float = 0.3
    ) -> AnalyticalRule:
        """Add analytical rule."""
        with self._lock:
            rule = AnalyticalRule(
                id=f"rule_{len(self._rules)}",
                name=name,
                condition=condition,
                transform=transform,
                cognitive_cost=cognitive_cost
            )
            self._rules[rule.id] = rule
            return rule

    def process(self, stimulus: Stimulus) -> Response:
        """Process stimulus with System 2."""
        with self._lock:
            start_time = time.time()

            # Check cognitive capacity
            required_load = stimulus.complexity * 0.7 + stimulus.urgency * 0.3

            if required_load > self._attention_capacity:
                # Overloaded - reduced quality
                self._current_load = CognitiveLoad.OVERLOAD
                response_content = self._degraded_analysis(stimulus)
                confidence = 0.4
            else:
                # Full analytical processing
                self._current_load = self._compute_load(required_load)
                response_content = self._full_analysis(stimulus)
                confidence = 0.9

            processing_time = (time.time() - start_time) * 1000

            # Simulate slower processing
            time.sleep(stimulus.complexity * 0.01)  # Add delay for realism

            return Response(
                id=self._generate_id(),
                stimulus_id=stimulus.id,
                content=response_content,
                system=ProcessingSystem.SYSTEM_2,
                confidence=confidence,
                processing_time_ms=processing_time,
                biases=[]  # System 2 aims to avoid biases
            )

    def _compute_load(self, required: float) -> CognitiveLoad:
        """Compute cognitive load."""
        if required < 0.3:
            return CognitiveLoad.LOW
        elif required < 0.6:
            return CognitiveLoad.MODERATE
        elif required < 0.9:
            return CognitiveLoad.HIGH
        else:
            return CognitiveLoad.OVERLOAD

    def _full_analysis(self, stimulus: Stimulus) -> Any:
        """Perform full analytical processing."""
        # Apply rules
        result = stimulus.content

        for rule in self._rules.values():
            try:
                if rule.condition(result):
                    result = rule.transform(result)
            except Exception:
                pass

        # Structure the response
        return {
            'analysis': f"Analytical processing of: {str(stimulus.content)[:100]}",
            'steps': len(self._rules),
            'conclusion': result
        }

    def _degraded_analysis(self, stimulus: Stimulus) -> Any:
        """Degraded analysis under overload."""
        return {
            'analysis': 'Overloaded - reduced analysis',
            'partial_result': str(stimulus.content)[:50]
        }

    def set_attention(self, capacity: float) -> None:
        """Set attention capacity (0-1)."""
        with self._lock:
            self._attention_capacity = max(0.0, min(1.0, capacity))

    @property
    def load(self) -> CognitiveLoad:
        return self._current_load

    @property
    def capacity(self) -> float:
        return self._attention_capacity


# ============================================================================
# METACOGNITIVE MONITOR
# ============================================================================

class MetacognitiveMonitor:
    """
    Monitor and switch between systems.

    "Ba'el monitors its thinking." — Ba'el
    """

    def __init__(self, system1: System1, system2: System2):
        """Initialize monitor."""
        self._s1 = system1
        self._s2 = system2
        self._override_log: List[Dict] = []
        self._conflict_count = 0
        self._lock = threading.RLock()

    def should_engage_system2(self, stimulus: Stimulus) -> bool:
        """Determine if System 2 should engage."""
        with self._lock:
            # Engage System 2 for:
            # - High complexity
            # - Low familiarity
            # - Important decisions

            complexity_threshold = 0.6
            familiarity_threshold = 0.4

            if stimulus.complexity > complexity_threshold:
                return True

            if stimulus.familiarity < familiarity_threshold:
                return True

            # Random engagement for monitoring
            if random.random() < 0.1:
                return True

            return False

    def detect_conflict(
        self,
        s1_response: Response,
        s2_response: Response
    ) -> bool:
        """Detect conflict between systems."""
        with self._lock:
            # Simple conflict detection
            s1_str = str(s1_response.content)
            s2_str = str(s2_response.content)

            # Check if responses are substantially different
            if s1_str != s2_str:
                self._conflict_count += 1
                return True

            return False

    def resolve_conflict(
        self,
        s1_response: Response,
        s2_response: Response,
        stimulus: Stimulus
    ) -> Response:
        """Resolve conflict between systems."""
        with self._lock:
            # Generally trust System 2 for complex/important
            if stimulus.complexity > 0.7:
                winner = s2_response
            # Trust System 1 for familiar/urgent
            elif stimulus.familiarity > 0.8 or stimulus.urgency > 0.8:
                winner = s1_response
            # Default to System 2
            else:
                winner = s2_response

            self._override_log.append({
                's1': s1_response.id,
                's2': s2_response.id,
                'winner': winner.system.name,
                'reason': 'conflict_resolution'
            })

            return winner

    def log_override(
        self,
        overridden: Response,
        by: Response,
        reason: str
    ) -> None:
        """Log when one system overrides another."""
        with self._lock:
            self._override_log.append({
                'overridden': overridden.id,
                'by': by.id,
                'reason': reason,
                'timestamp': time.time()
            })

    @property
    def conflict_count(self) -> int:
        return self._conflict_count

    @property
    def override_log(self) -> List[Dict]:
        return self._override_log.copy()


# ============================================================================
# DUAL PROCESS ENGINE
# ============================================================================

class DualProcessEngine:
    """
    Complete dual process implementation.

    "Ba'el's dual process mind." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._system1 = System1()
        self._system2 = System2()
        self._monitor = MetacognitiveMonitor(self._system1, self._system2)
        self._stimulus_counter = 0
        self._response_history: List[Response] = []
        self._default_mode = ProcessingSystem.SYSTEM_1
        self._lock = threading.RLock()

    def _generate_stimulus_id(self) -> str:
        self._stimulus_counter += 1
        return f"stim_{self._stimulus_counter}"

    def create_stimulus(
        self,
        content: Any,
        complexity: float = 0.5,
        familiarity: float = 0.5,
        urgency: float = 0.5,
        emotional_charge: float = 0.0
    ) -> Stimulus:
        """Create stimulus."""
        return Stimulus(
            id=self._generate_stimulus_id(),
            content=content,
            complexity=complexity,
            familiarity=familiarity,
            urgency=urgency,
            emotional_charge=emotional_charge
        )

    def process(
        self,
        stimulus: Stimulus,
        force_system: Optional[ProcessingSystem] = None
    ) -> Response:
        """Process stimulus."""
        with self._lock:
            if force_system == ProcessingSystem.SYSTEM_1:
                response = self._system1.process(stimulus)
            elif force_system == ProcessingSystem.SYSTEM_2:
                response = self._system2.process(stimulus)
            else:
                response = self._adaptive_process(stimulus)

            self._response_history.append(response)
            return response

    def _adaptive_process(self, stimulus: Stimulus) -> Response:
        """Adaptively choose processing system."""
        # Always get System 1 response (fast)
        s1_response = self._system1.process(stimulus)

        # Check if System 2 should engage
        if self._monitor.should_engage_system2(stimulus):
            s2_response = self._system2.process(stimulus)

            # Check for conflict
            if self._monitor.detect_conflict(s1_response, s2_response):
                return self._monitor.resolve_conflict(
                    s1_response, s2_response, stimulus
                )

            # No conflict - use System 2 if engaged
            return s2_response

        return s1_response

    def think_fast(self, content: Any) -> Response:
        """Shortcut for System 1 processing."""
        stimulus = self.create_stimulus(content, complexity=0.3, familiarity=0.7)
        return self.process(stimulus, force_system=ProcessingSystem.SYSTEM_1)

    def think_slow(self, content: Any) -> Response:
        """Shortcut for System 2 processing."""
        stimulus = self.create_stimulus(content, complexity=0.7, familiarity=0.3)
        return self.process(stimulus, force_system=ProcessingSystem.SYSTEM_2)

    def add_heuristic_pattern(self, pattern: str, response: Any) -> None:
        """Add pattern to System 1."""
        self._system1.add_pattern_response(pattern, response)

    def add_analytical_rule(
        self,
        name: str,
        condition: Callable[[Any], bool],
        transform: Callable[[Any], Any]
    ) -> AnalyticalRule:
        """Add rule to System 2."""
        return self._system2.add_rule(name, condition, transform)

    def set_cognitive_load(self, load: float) -> None:
        """Set System 2 capacity."""
        self._system2.set_attention(1.0 - load)

    def get_bias_report(self) -> Dict[str, int]:
        """Get report of biases detected."""
        bias_counts = defaultdict(int)

        for response in self._response_history:
            for bias in response.biases:
                bias_counts[bias.name] += 1

        return dict(bias_counts)

    @property
    def system1(self) -> System1:
        return self._system1

    @property
    def system2(self) -> System2:
        return self._system2

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        s1_count = sum(1 for r in self._response_history
                       if r.system == ProcessingSystem.SYSTEM_1)
        s2_count = len(self._response_history) - s1_count

        return {
            'total_processed': len(self._response_history),
            'system1_count': s1_count,
            'system2_count': s2_count,
            'system2_load': self._system2.load.name,
            'conflicts': self._monitor.conflict_count,
            'biases_detected': sum(len(r.biases) for r in self._response_history)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_dual_process_engine() -> DualProcessEngine:
    """Create dual process engine."""
    return DualProcessEngine()


def think_fast(content: Any) -> Response:
    """Quick System 1 processing."""
    engine = DualProcessEngine()
    return engine.think_fast(content)


def think_slow(content: Any) -> Response:
    """Deliberate System 2 processing."""
    engine = DualProcessEngine()
    return engine.think_slow(content)


def create_stimulus(
    content: Any,
    complexity: float = 0.5,
    familiarity: float = 0.5
) -> Stimulus:
    """Create stimulus."""
    return Stimulus(
        id=f"stim_{random.randint(1000, 9999)}",
        content=content,
        complexity=complexity,
        familiarity=familiarity
    )
