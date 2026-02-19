"""
BAEL Attention Schema Engine
============================

Model of attention as the brain models attention.

"Ba'el models its own attention." — Ba'el
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

logger = logging.getLogger("BAEL.AttentionSchema")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class AttentionMode(Enum):
    """Modes of attention."""
    OVERT = auto()      # Observable attention (e.g., eye movements)
    COVERT = auto()     # Internal attention shift
    EXECUTIVE = auto()  # Top-down control
    REFLEXIVE = auto()  # Bottom-up capture
    SUSTAINED = auto()  # Maintained focus
    SELECTIVE = auto()  # Filtering


class AttentionState(Enum):
    """States of attention."""
    ALERT = auto()
    FOCUSED = auto()
    DIFFUSE = auto()
    DISTRACTED = auto()
    FATIGUED = auto()


@dataclass
class AttentionTarget:
    """Target of attention."""
    id: str
    content: Any
    location: Optional[Tuple[float, float, float]] = None
    salience: float = 0.5
    priority: float = 0.5
    novelty: float = 0.5
    relevance: float = 0.5
    timestamp: float = field(default_factory=time.time)

    @property
    def combined_weight(self) -> float:
        """Combined attention weight."""
        return (
            self.salience * 0.3 +
            self.priority * 0.3 +
            self.novelty * 0.2 +
            self.relevance * 0.2
        )


@dataclass
class AttentionShift:
    """Record of attention shift."""
    from_target: Optional[str]
    to_target: str
    mode: AttentionMode
    timestamp: float = field(default_factory=time.time)
    cause: str = "unknown"
    successful: bool = True


# ============================================================================
# ATTENTION SCHEMA
# ============================================================================

class AttentionSchema:
    """
    Internal model of attention itself.

    "Ba'el models how it attends." — Ba'el
    """

    def __init__(self):
        """Initialize attention schema."""
        self._current_target: Optional[AttentionTarget] = None
        self._state = AttentionState.ALERT
        self._mode = AttentionMode.COVERT
        self._capacity = 1.0        # Current capacity (0-1)
        self._fatigue = 0.0         # Accumulated fatigue
        self._focus_duration = 0.0  # Time on current target
        self._shift_history: List[AttentionShift] = []
        self._lock = threading.RLock()

    def model_attention(self) -> Dict[str, Any]:
        """
        Generate model of current attention state.

        This is the 'schema' - the brain's model of its own attention.
        """
        with self._lock:
            return {
                'attending': self._current_target is not None,
                'target': self._current_target.id if self._current_target else None,
                'state': self._state.name,
                'mode': self._mode.name,
                'capacity': self._capacity,
                'fatigue': self._fatigue,
                'focus_duration': self._focus_duration,
                'can_shift': self._can_shift(),
                'recent_shifts': len(self._shift_history[-10:])
            }

    def _can_shift(self) -> bool:
        """Model whether attention can shift."""
        # Fatigued attention is harder to shift
        if self._fatigue > 0.8:
            return random.random() < 0.3

        # Deep focus is harder to break
        if self._focus_duration > 60:  # seconds
            return random.random() < 0.5

        return True

    def shift_to(
        self,
        target: AttentionTarget,
        mode: AttentionMode = AttentionMode.COVERT,
        cause: str = "voluntary"
    ) -> bool:
        """Shift attention to new target."""
        with self._lock:
            if not self._can_shift():
                shift = AttentionShift(
                    from_target=self._current_target.id if self._current_target else None,
                    to_target=target.id,
                    mode=mode,
                    cause=cause,
                    successful=False
                )
                self._shift_history.append(shift)
                return False

            # Record shift
            shift = AttentionShift(
                from_target=self._current_target.id if self._current_target else None,
                to_target=target.id,
                mode=mode,
                cause=cause,
                successful=True
            )
            self._shift_history.append(shift)

            # Update state
            self._current_target = target
            self._mode = mode
            self._focus_duration = 0.0
            self._state = AttentionState.FOCUSED

            return True

    def disengage(self) -> None:
        """Disengage attention."""
        with self._lock:
            self._current_target = None
            self._state = AttentionState.DIFFUSE
            self._focus_duration = 0.0

    def tick(self, elapsed: float = 1.0) -> None:
        """Update attention state over time."""
        with self._lock:
            if self._current_target:
                self._focus_duration += elapsed

                # Fatigue accumulates with sustained attention
                self._fatigue = min(1.0, self._fatigue + elapsed * 0.01)

                # Capacity depletes
                self._capacity = max(0.2, self._capacity - elapsed * 0.005)
            else:
                # Recovery when not focused
                self._fatigue = max(0, self._fatigue - elapsed * 0.02)
                self._capacity = min(1.0, self._capacity + elapsed * 0.01)

            # Update state based on fatigue
            if self._fatigue > 0.8:
                self._state = AttentionState.FATIGUED

    def refresh(self) -> None:
        """Refresh attention capacity."""
        with self._lock:
            self._fatigue = 0.0
            self._capacity = 1.0
            self._state = AttentionState.ALERT

    @property
    def is_attending(self) -> bool:
        """Check if currently attending to something."""
        return self._current_target is not None

    @property
    def current_target(self) -> Optional[AttentionTarget]:
        """Get current attention target."""
        return self._current_target


# ============================================================================
# SALIENCE MAP
# ============================================================================

class SalienceMap:
    """
    Map of salience across attention space.

    "Ba'el knows what stands out." — Ba'el
    """

    def __init__(self, dimensions: Tuple[int, int] = (100, 100)):
        """Initialize salience map."""
        self._width, self._height = dimensions
        self._map = [[0.0 for _ in range(self._width)] for _ in range(self._height)]
        self._objects: Dict[str, Tuple[int, int, float]] = {}  # id -> (x, y, salience)
        self._lock = threading.RLock()

    def add_object(
        self,
        obj_id: str,
        x: int,
        y: int,
        salience: float
    ) -> None:
        """Add salient object to map."""
        with self._lock:
            x = max(0, min(self._width - 1, x))
            y = max(0, min(self._height - 1, y))

            self._objects[obj_id] = (x, y, salience)

            # Update map with gaussian spread
            self._update_map()

    def _update_map(self) -> None:
        """Update salience map from objects."""
        # Reset
        self._map = [[0.0 for _ in range(self._width)] for _ in range(self._height)]

        # Add gaussian for each object
        for obj_id, (ox, oy, salience) in self._objects.items():
            sigma = 10.0  # Spread

            for y in range(max(0, oy - 30), min(self._height, oy + 30)):
                for x in range(max(0, ox - 30), min(self._width, ox + 30)):
                    dist_sq = (x - ox) ** 2 + (y - oy) ** 2
                    value = salience * math.exp(-dist_sq / (2 * sigma ** 2))
                    self._map[y][x] = min(1.0, self._map[y][x] + value)

    def get_peak(self) -> Optional[Tuple[int, int, float]]:
        """Get peak salience location."""
        with self._lock:
            max_val = 0.0
            max_loc = None

            for y in range(self._height):
                for x in range(self._width):
                    if self._map[y][x] > max_val:
                        max_val = self._map[y][x]
                        max_loc = (x, y)

            if max_loc:
                return (max_loc[0], max_loc[1], max_val)
            return None

    def get_at(self, x: int, y: int) -> float:
        """Get salience at location."""
        with self._lock:
            if 0 <= x < self._width and 0 <= y < self._height:
                return self._map[y][x]
            return 0.0

    def inhibit_location(self, x: int, y: int, radius: int = 10) -> None:
        """Inhibit location (inhibition of return)."""
        with self._lock:
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self._width and 0 <= ny < self._height:
                        self._map[ny][nx] *= 0.5

    def decay(self, rate: float = 0.95) -> None:
        """Apply decay to salience map."""
        with self._lock:
            for y in range(self._height):
                for x in range(self._width):
                    self._map[y][x] *= rate


# ============================================================================
# PRIORITY MAP
# ============================================================================

class PriorityMap:
    """
    Map combining bottom-up salience and top-down priority.

    "Ba'el balances what's salient and what's important." — Ba'el
    """

    def __init__(self, salience_map: SalienceMap):
        """Initialize priority map."""
        self._salience = salience_map
        self._goals: Dict[str, float] = {}      # goal -> weight
        self._task_relevance: Dict[str, float] = {}  # object -> relevance
        self._lock = threading.RLock()

    def set_goal(self, goal_id: str, weight: float) -> None:
        """Set goal priority."""
        with self._lock:
            self._goals[goal_id] = max(0, min(1, weight))

    def set_relevance(self, obj_id: str, relevance: float) -> None:
        """Set task relevance for object."""
        with self._lock:
            self._task_relevance[obj_id] = max(0, min(1, relevance))

    def compute_priority(self, obj_id: str) -> float:
        """Compute combined priority for object."""
        with self._lock:
            # Bottom-up salience
            obj_data = self._salience._objects.get(obj_id)
            if not obj_data:
                return 0.0

            salience = obj_data[2]

            # Top-down relevance
            relevance = self._task_relevance.get(obj_id, 0.5)

            # Combine
            return salience * 0.4 + relevance * 0.6

    def get_highest_priority(self) -> Optional[str]:
        """Get object with highest priority."""
        with self._lock:
            if not self._salience._objects:
                return None

            priorities = {
                obj_id: self.compute_priority(obj_id)
                for obj_id in self._salience._objects
            }

            return max(priorities, key=priorities.get)


# ============================================================================
# ATTENTION CONTROLLER
# ============================================================================

class AttentionController:
    """
    Controls attention based on schema.

    "Ba'el controls where it looks." — Ba'el
    """

    def __init__(self, schema: AttentionSchema):
        """Initialize controller."""
        self._schema = schema
        self._salience = SalienceMap()
        self._priority = PriorityMap(self._salience)
        self._targets: Dict[str, AttentionTarget] = {}
        self._inhibited: Set[str] = set()
        self._lock = threading.RLock()

    def add_target(self, target: AttentionTarget) -> None:
        """Add potential attention target."""
        with self._lock:
            self._targets[target.id] = target

            if target.location:
                x, y, _ = target.location
                self._salience.add_object(
                    target.id,
                    int(x * 100),
                    int(y * 100),
                    target.salience
                )

    def remove_target(self, target_id: str) -> None:
        """Remove target."""
        with self._lock:
            if target_id in self._targets:
                del self._targets[target_id]

    def set_task_relevance(self, target_id: str, relevance: float) -> None:
        """Set task relevance for target."""
        self._priority.set_relevance(target_id, relevance)

    def select_next_target(self) -> Optional[AttentionTarget]:
        """Select next attention target."""
        with self._lock:
            if not self._targets:
                return None

            # Get highest priority not inhibited
            candidates = [
                t for t in self._targets.values()
                if t.id not in self._inhibited
            ]

            if not candidates:
                # All inhibited, clear inhibition
                self._inhibited.clear()
                candidates = list(self._targets.values())

            # Score candidates
            scored = [
                (t, self._priority.compute_priority(t.id))
                for t in candidates
            ]

            # Probabilistic selection based on priority
            total = sum(s for _, s in scored)
            if total == 0:
                return random.choice(candidates)

            r = random.random() * total
            cumsum = 0
            for target, score in scored:
                cumsum += score
                if r < cumsum:
                    return target

            return scored[-1][0]

    def attend(self, target: AttentionTarget) -> bool:
        """Attend to target."""
        with self._lock:
            success = self._schema.shift_to(
                target,
                mode=AttentionMode.COVERT,
                cause="controller"
            )

            if success:
                # Inhibit previous location
                if target.location:
                    x, y, _ = target.location
                    self._salience.inhibit_location(int(x * 100), int(y * 100))

            return success

    def auto_attend(self) -> Optional[AttentionTarget]:
        """Automatically select and attend to target."""
        target = self.select_next_target()

        if target and self.attend(target):
            return target

        return None

    def step(self, elapsed: float = 1.0) -> None:
        """Update attention state."""
        with self._lock:
            self._schema.tick(elapsed)
            self._salience.decay(0.98)


# ============================================================================
# AWARENESS MODEL
# ============================================================================

class AwarenessModel:
    """
    Model of awareness based on attention schema.

    "Ba'el is aware of what it attends to." — Ba'el
    """

    def __init__(self, schema: AttentionSchema):
        """Initialize awareness model."""
        self._schema = schema
        self._awareness_history: List[Dict] = []
        self._meta_awareness = True  # Awareness of being aware
        self._lock = threading.RLock()

    def update(self) -> Dict[str, Any]:
        """Update awareness model."""
        with self._lock:
            attention_model = self._schema.model_attention()

            awareness = {
                'timestamp': time.time(),
                'aware_of': attention_model['target'],
                'attending': attention_model['attending'],
                'attention_state': attention_model['state'],
                'meta_aware': self._meta_awareness,
                'capacity': attention_model['capacity']
            }

            self._awareness_history.append(awareness)

            # Keep bounded
            if len(self._awareness_history) > 1000:
                self._awareness_history = self._awareness_history[-500:]

            return awareness

    def report_awareness(self) -> str:
        """Generate awareness report (like what the system 'says' about its awareness)."""
        with self._lock:
            attention = self._schema.model_attention()

            if not attention['attending']:
                return "I am not focused on anything specific."

            state = attention['state'].lower()
            target = attention['target']

            return f"I am {state} and attending to {target}."

    @property
    def is_aware(self) -> bool:
        """Check if currently aware."""
        return self._schema.is_attending


# ============================================================================
# ATTENTION SCHEMA ENGINE
# ============================================================================

class AttentionSchemaEngine:
    """
    Complete Attention Schema Theory engine.

    "Ba'el implements awareness through attention modeling." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._schema = AttentionSchema()
        self._controller = AttentionController(self._schema)
        self._awareness = AwarenessModel(self._schema)
        self._lock = threading.RLock()

    def add_target(
        self,
        target_id: str,
        content: Any,
        location: Optional[Tuple[float, float, float]] = None,
        salience: float = 0.5,
        priority: float = 0.5
    ) -> AttentionTarget:
        """Add attention target."""
        target = AttentionTarget(
            id=target_id,
            content=content,
            location=location,
            salience=salience,
            priority=priority
        )
        self._controller.add_target(target)
        return target

    def remove_target(self, target_id: str) -> None:
        """Remove target."""
        self._controller.remove_target(target_id)

    def focus(self, target_id: str) -> bool:
        """Focus on specific target."""
        with self._lock:
            if target_id not in self._controller._targets:
                return False

            target = self._controller._targets[target_id]
            return self._controller.attend(target)

    def unfocus(self) -> None:
        """Unfocus attention."""
        self._schema.disengage()

    def auto_focus(self) -> Optional[str]:
        """Automatically select focus."""
        target = self._controller.auto_attend()
        return target.id if target else None

    def set_relevance(self, target_id: str, relevance: float) -> None:
        """Set task relevance."""
        self._controller.set_task_relevance(target_id, relevance)

    def step(self, elapsed: float = 1.0) -> Dict[str, Any]:
        """Execute one step."""
        with self._lock:
            self._controller.step(elapsed)
            awareness = self._awareness.update()

            return {
                'attention': self._schema.model_attention(),
                'awareness': awareness
            }

    def run(self, steps: int = 100, step_time: float = 1.0) -> List[Dict]:
        """Run for multiple steps."""
        results = []
        for _ in range(steps):
            result = self.step(step_time)
            results.append(result)
        return results

    def report(self) -> str:
        """Get awareness report."""
        return self._awareness.report_awareness()

    def refresh(self) -> None:
        """Refresh attention resources."""
        self._schema.refresh()

    def get_current_focus(self) -> Optional[AttentionTarget]:
        """Get current focus target."""
        return self._schema.current_target

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'schema': self._schema.model_attention(),
            'targets': len(self._controller._targets),
            'aware': self._awareness.is_aware
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_attention_schema_engine() -> AttentionSchemaEngine:
    """Create attention schema engine."""
    return AttentionSchemaEngine()


def create_attention_schema() -> AttentionSchema:
    """Create attention schema."""
    return AttentionSchema()


def create_salience_map(dimensions: Tuple[int, int] = (100, 100)) -> SalienceMap:
    """Create salience map."""
    return SalienceMap(dimensions)


def create_attention_target(
    target_id: str,
    content: Any,
    salience: float = 0.5
) -> AttentionTarget:
    """Create attention target."""
    return AttentionTarget(
        id=target_id,
        content=content,
        salience=salience
    )
