"""
BAEL Visuospatial Sketchpad Engine
===================================

Baddeley's visuospatial sketchpad component.
Visual and spatial short-term memory.

"Ba'el sees in the mind's eye." — Ba'el
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
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.VisuospatialSketchpad")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class VisualFeature(Enum):
    """Visual features."""
    COLOR = auto()
    SHAPE = auto()
    SIZE = auto()
    ORIENTATION = auto()
    TEXTURE = auto()


class SpatialFeature(Enum):
    """Spatial features."""
    LOCATION = auto()
    DISTANCE = auto()
    DIRECTION = auto()
    PATH = auto()
    ARRANGEMENT = auto()


class SketchpadMode(Enum):
    """Mode of operation."""
    VISUAL = auto()        # Object properties (Logie's visual cache)
    SPATIAL = auto()       # Location/movement (Logie's inner scribe)
    COMBINED = auto()      # Both together


class InterferenceType(Enum):
    """Types of interference."""
    VISUAL_NOISE = auto()      # Random visual patterns
    SPATIAL_TAPPING = auto()   # Sequential spatial task
    TRACKING = auto()          # Pursuit tracking
    MENTAL_ROTATION = auto()   # Rotation task


@dataclass
class Position:
    """
    A 2D position.
    """
    x: float
    y: float

    def distance_to(self, other: 'Position') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)


@dataclass
class VisualObject:
    """
    A visual object representation.
    """
    id: str
    shape: str
    color: str
    size: float
    position: Position
    orientation: float = 0.0
    entry_time: float = field(default_factory=time.time)
    decay_progress: float = 0.0


@dataclass
class SpatialSequence:
    """
    A sequence of spatial locations.
    """
    id: str
    positions: List[Position]
    entry_time: float
    decay_progress: float = 0.0


@dataclass
class VisualSpanTest:
    """
    A visual span test trial.
    """
    objects: List[VisualObject]
    probe_feature: VisualFeature
    correct: bool
    span_length: int


@dataclass
class SpatialSpanTest:
    """
    A spatial span test (Corsi blocks style).
    """
    sequence: List[Position]
    recalled: List[Position]
    correct: bool
    span_length: int


@dataclass
class VisuospatialMetrics:
    """
    Visuospatial metrics.
    """
    visual_capacity: int
    spatial_span: int
    binding_accuracy: float
    interference_susceptibility: float


# ============================================================================
# VISUAL CACHE
# ============================================================================

class VisualCache:
    """
    Visual cache (Logie's inner eye).

    "Ba'el holds images." — Ba'el
    """

    def __init__(
        self,
        capacity: int = 4,
        decay_time_ms: int = 3000
    ):
        """Initialize cache."""
        self._objects: Dict[str, VisualObject] = {}
        self._capacity = capacity
        self._decay_time = decay_time_ms
        self._object_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._object_counter += 1
        return f"obj_{self._object_counter}"

    def store_object(
        self,
        shape: str,
        color: str,
        size: float,
        position: Position,
        orientation: float = 0.0
    ) -> VisualObject:
        """Store a visual object."""
        # Check capacity
        if len(self._objects) >= self._capacity:
            # Remove oldest
            oldest = min(
                self._objects.values(),
                key=lambda o: o.entry_time
            )
            del self._objects[oldest.id]

        obj = VisualObject(
            id=self._generate_id(),
            shape=shape,
            color=color,
            size=size,
            position=position,
            orientation=orientation
        )

        self._objects[obj.id] = obj
        return obj

    def get_objects(self) -> List[VisualObject]:
        """Get all stored objects."""
        return list(self._objects.values())

    def apply_decay(
        self,
        elapsed_ms: int
    ) -> List[str]:
        """Apply decay to objects."""
        lost = []

        for obj_id, obj in list(self._objects.items()):
            obj.decay_progress += elapsed_ms / self._decay_time

            if obj.decay_progress >= 1.0:
                lost.append(obj_id)
                del self._objects[obj_id]

        return lost

    def refresh(
        self,
        object_id: str
    ) -> bool:
        """Refresh an object through attention."""
        if object_id in self._objects:
            self._objects[object_id].decay_progress = 0.0
            self._objects[object_id].entry_time = time.time()
            return True
        return False

    def clear(self) -> None:
        """Clear cache."""
        self._objects.clear()

    @property
    def count(self) -> int:
        return len(self._objects)


# ============================================================================
# INNER SCRIBE
# ============================================================================

class InnerScribe:
    """
    Inner scribe for spatial sequences.

    "Ba'el traces paths." — Ba'el
    """

    def __init__(
        self,
        capacity: int = 7,
        decay_time_ms: int = 4000
    ):
        """Initialize inner scribe."""
        self._sequences: Dict[str, SpatialSequence] = {}
        self._capacity = capacity
        self._decay_time = decay_time_ms
        self._seq_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._seq_counter += 1
        return f"seq_{self._seq_counter}"

    def store_sequence(
        self,
        positions: List[Position]
    ) -> SpatialSequence:
        """Store a spatial sequence."""
        # Truncate if exceeds capacity
        stored_positions = positions[:self._capacity]

        seq = SpatialSequence(
            id=self._generate_id(),
            positions=stored_positions,
            entry_time=time.time()
        )

        self._sequences[seq.id] = seq
        return seq

    def rehearse_sequence(
        self,
        sequence_id: str
    ) -> bool:
        """Rehearse a sequence through inner movement."""
        if sequence_id in self._sequences:
            seq = self._sequences[sequence_id]
            seq.decay_progress = 0.0
            seq.entry_time = time.time()
            return True
        return False

    def get_sequences(self) -> List[SpatialSequence]:
        """Get all sequences."""
        return list(self._sequences.values())

    def apply_decay(
        self,
        elapsed_ms: int
    ) -> List[str]:
        """Apply decay."""
        lost = []

        for seq_id, seq in list(self._sequences.items()):
            seq.decay_progress += elapsed_ms / self._decay_time

            if seq.decay_progress >= 1.0:
                lost.append(seq_id)
                del self._sequences[seq_id]

        return lost

    def clear(self) -> None:
        """Clear sequences."""
        self._sequences.clear()


# ============================================================================
# INTERFERENCE MANAGER
# ============================================================================

class InterferenceManager:
    """
    Manage interference effects.

    "Ba'el resists distraction." — Ba'el
    """

    def __init__(self):
        """Initialize manager."""
        self._active_interference: Optional[InterferenceType] = None
        self._lock = threading.RLock()

    def set_interference(
        self,
        interference: InterferenceType
    ) -> None:
        """Set active interference."""
        self._active_interference = interference

    def clear_interference(self) -> None:
        """Clear interference."""
        self._active_interference = None

    def get_visual_disruption(self) -> float:
        """Get visual disruption level (0-1)."""
        if self._active_interference is None:
            return 0.0

        disruption = {
            InterferenceType.VISUAL_NOISE: 0.7,
            InterferenceType.SPATIAL_TAPPING: 0.2,
            InterferenceType.TRACKING: 0.3,
            InterferenceType.MENTAL_ROTATION: 0.5
        }

        return disruption.get(self._active_interference, 0.0)

    def get_spatial_disruption(self) -> float:
        """Get spatial disruption level (0-1)."""
        if self._active_interference is None:
            return 0.0

        disruption = {
            InterferenceType.VISUAL_NOISE: 0.2,
            InterferenceType.SPATIAL_TAPPING: 0.8,
            InterferenceType.TRACKING: 0.7,
            InterferenceType.MENTAL_ROTATION: 0.6
        }

        return disruption.get(self._active_interference, 0.0)


# ============================================================================
# VISUOSPATIAL SKETCHPAD ENGINE
# ============================================================================

class VisuospatialSketchpadEngine:
    """
    Complete visuospatial sketchpad engine.

    "Ba'el's mental canvas." — Ba'el
    """

    def __init__(
        self,
        visual_capacity: int = 4,
        spatial_capacity: int = 7
    ):
        """Initialize engine."""
        self._visual_cache = VisualCache(visual_capacity)
        self._inner_scribe = InnerScribe(spatial_capacity)
        self._interference = InterferenceManager()

        self._visual_tests: List[VisualSpanTest] = []
        self._spatial_tests: List[SpatialSpanTest] = []

        self._lock = threading.RLock()

    # Visual operations

    def store_visual(
        self,
        shape: str,
        color: str,
        position: Tuple[float, float],
        size: float = 1.0
    ) -> VisualObject:
        """Store a visual object."""
        pos = Position(position[0], position[1])
        return self._visual_cache.store_object(shape, color, size, pos)

    def store_visual_array(
        self,
        objects: List[Dict[str, Any]]
    ) -> List[VisualObject]:
        """Store multiple visual objects."""
        stored = []
        for obj in objects:
            result = self.store_visual(
                shape=obj.get('shape', 'square'),
                color=obj.get('color', 'red'),
                position=obj.get('position', (0, 0)),
                size=obj.get('size', 1.0)
            )
            stored.append(result)
        return stored

    # Spatial operations

    def store_path(
        self,
        positions: List[Tuple[float, float]]
    ) -> SpatialSequence:
        """Store a spatial path."""
        pos_list = [Position(p[0], p[1]) for p in positions]
        return self._inner_scribe.store_sequence(pos_list)

    def rehearse_path(
        self,
        sequence_id: str
    ) -> bool:
        """Rehearse a spatial path."""
        return self._inner_scribe.rehearse_sequence(sequence_id)

    # Span tests

    def visual_span_test(
        self,
        array_size: int
    ) -> VisualSpanTest:
        """Run visual span test (change detection)."""
        self._visual_cache.clear()

        # Generate random array
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange']
        shapes = ['square', 'circle', 'triangle']

        objects = []
        for i in range(array_size):
            obj = self.store_visual(
                shape=random.choice(shapes),
                color=random.choice(colors),
                position=(random.uniform(0, 10), random.uniform(0, 10))
            )
            objects.append(obj)

        # Simulate retention and test
        disruption = self._interference.get_visual_disruption()
        capacity_limit = 4 * (1 - disruption)

        # Accuracy based on array size vs capacity
        correct = array_size <= capacity_limit and random.random() > 0.2

        test = VisualSpanTest(
            objects=objects,
            probe_feature=VisualFeature.COLOR,
            correct=correct,
            span_length=array_size
        )

        self._visual_tests.append(test)
        return test

    def corsi_block_test(
        self,
        sequence_length: int
    ) -> SpatialSpanTest:
        """Run Corsi block test."""
        self._inner_scribe.clear()

        # Generate random sequence
        positions = [
            (random.uniform(0, 10), random.uniform(0, 10))
            for _ in range(sequence_length)
        ]

        # Store and recall
        self.store_path(positions)

        # Simulate recall
        disruption = self._interference.get_spatial_disruption()
        effective_capacity = 7 * (1 - disruption)

        # Recall accuracy
        if sequence_length <= effective_capacity:
            recalled_positions = positions[:]
            correct = True
        else:
            # Partial recall
            recalled_positions = positions[:int(effective_capacity)]
            correct = False

        recalled = [Position(p[0], p[1]) for p in recalled_positions]
        original = [Position(p[0], p[1]) for p in positions]

        test = SpatialSpanTest(
            sequence=original,
            recalled=recalled,
            correct=correct,
            span_length=sequence_length
        )

        self._spatial_tests.append(test)
        return test

    def measure_visual_span(self) -> int:
        """Measure visual span through increasing array sizes."""
        span = 0

        for size in range(1, 9):
            test = self.visual_span_test(size)
            if test.correct:
                span = size
            else:
                break

        return span

    def measure_spatial_span(self) -> int:
        """Measure spatial span (Corsi span)."""
        span = 0

        for length in range(2, 10):
            test = self.corsi_block_test(length)
            if test.correct:
                span = length
            else:
                break

        return span

    # Interference

    def set_interference(
        self,
        interference: InterferenceType
    ) -> None:
        """Set active interference task."""
        self._interference.set_interference(interference)

    def clear_interference(self) -> None:
        """Clear interference."""
        self._interference.clear_interference()

    # Mental rotation

    def mental_rotation(
        self,
        angle: float
    ) -> float:
        """Simulate mental rotation (returns RT)."""
        # RT increases linearly with angle (Shepard & Metzler)
        base_rt = 0.5
        rt_per_degree = 0.003

        rotation_rt = base_rt + abs(angle) * rt_per_degree
        return rotation_rt + random.uniform(-0.1, 0.2)

    # Binding

    def test_feature_binding(
        self,
        array_size: int
    ) -> float:
        """Test feature-location binding."""
        # Binding is more demanding than single features
        capacity = 4 * (1 - self._interference.get_visual_disruption())

        if array_size <= capacity:
            accuracy = 0.85 + random.uniform(-0.1, 0.1)
        else:
            excess = array_size - capacity
            accuracy = max(0.3, 0.85 - excess * 0.15)

        return accuracy

    # Metrics

    def get_metrics(self) -> VisuospatialMetrics:
        """Get visuospatial metrics."""
        # Visual span from tests
        successful_visual = [
            t.span_length for t in self._visual_tests if t.correct
        ]
        visual_capacity = max(successful_visual) if successful_visual else 4

        # Spatial span from tests
        successful_spatial = [
            t.span_length for t in self._spatial_tests if t.correct
        ]
        spatial_span = max(successful_spatial) if successful_spatial else 7

        # Binding accuracy estimate
        binding = 0.8  # Default

        # Interference susceptibility
        susceptibility = (
            self._interference.get_visual_disruption() +
            self._interference.get_spatial_disruption()
        ) / 2

        return VisuospatialMetrics(
            visual_capacity=visual_capacity,
            spatial_span=spatial_span,
            binding_accuracy=binding,
            interference_susceptibility=susceptibility
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'visual_objects': self._visual_cache.count,
            'spatial_sequences': len(self._inner_scribe.get_sequences()),
            'visual_tests': len(self._visual_tests),
            'spatial_tests': len(self._spatial_tests)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_visuospatial_sketchpad_engine(
    visual_capacity: int = 4,
    spatial_capacity: int = 7
) -> VisuospatialSketchpadEngine:
    """Create visuospatial sketchpad engine."""
    return VisuospatialSketchpadEngine(visual_capacity, spatial_capacity)


def demonstrate_visuospatial_sketchpad() -> Dict[str, Any]:
    """Demonstrate visuospatial sketchpad."""
    engine = create_visuospatial_sketchpad_engine()

    # Measure spans
    visual_span = engine.measure_visual_span()
    spatial_span = engine.measure_spatial_span()

    # Test mental rotation
    rotation_rt = engine.mental_rotation(90)

    # Test binding
    binding = engine.test_feature_binding(4)

    return {
        'visual_span': visual_span,
        'spatial_span': spatial_span,
        'rotation_rt_90deg': rotation_rt,
        'binding_accuracy': binding,
        'interpretation': (
            f'Visual span: ~{visual_span} objects, '
            f'Spatial span: ~{spatial_span} locations'
        )
    }


def get_visuospatial_facts() -> Dict[str, str]:
    """Get facts about visuospatial sketchpad."""
    return {
        'baddeley_1986': 'Visuospatial sketchpad proposed',
        'logie_1995': 'Visual cache + Inner scribe distinction',
        'visual_capacity': '~3-4 objects (Luck & Vogel)',
        'spatial_span': '~6-7 locations (Corsi blocks)',
        'binding': 'Feature-location binding is capacity limited',
        'mental_rotation': 'Shepard & Metzler - RT linear with angle',
        'selective_interference': 'Visual and spatial have separate resources',
        'inner_scribe': 'Rehearses spatial sequences through movement'
    }
