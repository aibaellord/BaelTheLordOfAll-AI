"""
BAEL Mental Rotation Engine
============================

Spatial transformation and mental imagery rotation.
Shepard & Metzler mental rotation paradigm.

"Ba'el rotates minds through space." — Ba'el
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

logger = logging.getLogger("BAEL.MentalRotation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class RotationAxis(Enum):
    """Axes of rotation."""
    X = auto()           # Roll (front/back)
    Y = auto()           # Yaw (left/right)
    Z = auto()           # Pitch (up/down)
    PICTURE_PLANE = auto()  # 2D rotation
    DEPTH = auto()       # Into/out of screen


class ObjectType(Enum):
    """Types of 3D objects."""
    SHEPARD_METZLER = auto()  # Classic block figures
    CUBE = auto()
    TETRAHEDRON = auto()
    COMPLEX = auto()
    LETTER = auto()         # Alphanumeric
    HAND = auto()           # Left/right hand


class TrialType(Enum):
    """Types of comparison trials."""
    SAME = auto()         # Same object, rotated
    MIRROR = auto()       # Mirror reflection
    DIFFERENT = auto()    # Different object


class Strategy(Enum):
    """Rotation strategies."""
    HOLISTIC = auto()     # Rotate entire object
    PIECEMEAL = auto()    # Rotate parts
    ANALYTIC = auto()     # Feature comparison
    COMBINED = auto()     # Mixed strategy


@dataclass
class Point3D:
    """
    A 3D point.
    """
    x: float
    y: float
    z: float

    def rotate_x(self, angle: float) -> 'Point3D':
        """Rotate around X axis."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Point3D(
            x=self.x,
            y=self.y * cos_a - self.z * sin_a,
            z=self.y * sin_a + self.z * cos_a
        )

    def rotate_y(self, angle: float) -> 'Point3D':
        """Rotate around Y axis."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Point3D(
            x=self.x * cos_a + self.z * sin_a,
            y=self.y,
            z=-self.x * sin_a + self.z * cos_a
        )

    def rotate_z(self, angle: float) -> 'Point3D':
        """Rotate around Z axis."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Point3D(
            x=self.x * cos_a - self.y * sin_a,
            y=self.x * sin_a + self.y * cos_a,
            z=self.z
        )

    def distance(self, other: 'Point3D') -> float:
        """Euclidean distance."""
        return math.sqrt(
            (self.x - other.x)**2 +
            (self.y - other.y)**2 +
            (self.z - other.z)**2
        )


@dataclass
class SpatialObject:
    """
    A 3D spatial object.
    """
    id: str
    object_type: ObjectType
    vertices: List[Point3D]
    edges: List[Tuple[int, int]]  # Vertex index pairs
    is_mirrored: bool = False

    def rotate(
        self,
        axis: RotationAxis,
        angle: float
    ) -> 'SpatialObject':
        """Create rotated copy."""
        new_vertices = []

        for v in self.vertices:
            if axis == RotationAxis.X:
                new_v = v.rotate_x(angle)
            elif axis == RotationAxis.Y:
                new_v = v.rotate_y(angle)
            else:
                new_v = v.rotate_z(angle)
            new_vertices.append(new_v)

        return SpatialObject(
            id=self.id,
            object_type=self.object_type,
            vertices=new_vertices,
            edges=self.edges.copy(),
            is_mirrored=self.is_mirrored
        )

    def mirror(
        self,
        axis: RotationAxis = RotationAxis.X
    ) -> 'SpatialObject':
        """Create mirrored copy."""
        new_vertices = []

        for v in self.vertices:
            if axis == RotationAxis.X:
                new_v = Point3D(-v.x, v.y, v.z)
            elif axis == RotationAxis.Y:
                new_v = Point3D(v.x, -v.y, v.z)
            else:
                new_v = Point3D(v.x, v.y, -v.z)
            new_vertices.append(new_v)

        return SpatialObject(
            id=self.id + "_mirror",
            object_type=self.object_type,
            vertices=new_vertices,
            edges=self.edges.copy(),
            is_mirrored=not self.is_mirrored
        )


@dataclass
class RotationTrial:
    """
    A mental rotation trial.
    """
    id: str
    object_a: SpatialObject
    object_b: SpatialObject
    trial_type: TrialType
    rotation_angle: float  # Radians
    rotation_axis: RotationAxis


@dataclass
class RotationResponse:
    """
    Response to a rotation trial.
    """
    trial_id: str
    response: TrialType
    response_time: float  # Milliseconds
    correct: bool


@dataclass
class RotationMetrics:
    """
    Performance metrics.
    """
    accuracy: float
    mean_rt: float  # Mean response time
    slope: float    # RT/degree slope
    intercept: float  # Base RT


# ============================================================================
# OBJECT GENERATOR
# ============================================================================

class ObjectGenerator:
    """
    Generate spatial objects.

    "Ba'el creates forms in space." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._object_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._object_counter += 1
        return f"obj_{self._object_counter}"

    def generate_shepard_metzler(self) -> SpatialObject:
        """Generate Shepard-Metzler style figure."""
        # Create a figure made of connected cubes
        vertices = []
        edges = []

        # Generate random arm configuration
        positions = [(0, 0, 0)]

        # Add 4 connected unit cubes
        directions = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]

        for _ in range(4):
            dx, dy, dz = random.choice(directions)
            last = positions[-1]
            new_pos = (last[0] + dx, last[1] + dy, last[2] + dz)
            if new_pos not in positions:
                positions.append(new_pos)

        # Create cube vertices for each position
        cube_offset = 0
        for px, py, pz in positions:
            for dx in [0, 1]:
                for dy in [0, 1]:
                    for dz in [0, 1]:
                        vertices.append(Point3D(px + dx * 0.5, py + dy * 0.5, pz + dz * 0.5))

            # Add cube edges
            base = cube_offset
            edges.extend([
                (base, base + 1), (base, base + 2), (base, base + 4),
                (base + 1, base + 3), (base + 1, base + 5),
                (base + 2, base + 3), (base + 2, base + 6),
                (base + 3, base + 7), (base + 4, base + 5),
                (base + 4, base + 6), (base + 5, base + 7),
                (base + 6, base + 7)
            ])
            cube_offset += 8

        return SpatialObject(
            id=self._generate_id(),
            object_type=ObjectType.SHEPARD_METZLER,
            vertices=vertices,
            edges=edges
        )

    def generate_letter(
        self,
        letter: str = 'R'
    ) -> SpatialObject:
        """Generate a letter for rotation."""
        # Simplified letter representation
        vertices = [
            Point3D(0, 0, 0),
            Point3D(0, 2, 0),
            Point3D(1, 2, 0),
            Point3D(1, 1, 0),
            Point3D(0, 1, 0)
        ]

        edges = [
            (0, 1), (1, 2), (2, 3), (3, 4), (4, 0)
        ]

        return SpatialObject(
            id=self._generate_id(),
            object_type=ObjectType.LETTER,
            vertices=vertices,
            edges=edges
        )

    def generate_cube(self) -> SpatialObject:
        """Generate a simple cube."""
        vertices = []

        for x in [-1, 1]:
            for y in [-1, 1]:
                for z in [-1, 1]:
                    vertices.append(Point3D(x, y, z))

        edges = [
            (0, 1), (0, 2), (0, 4),
            (1, 3), (1, 5),
            (2, 3), (2, 6),
            (3, 7), (4, 5), (4, 6),
            (5, 7), (6, 7)
        ]

        return SpatialObject(
            id=self._generate_id(),
            object_type=ObjectType.CUBE,
            vertices=vertices,
            edges=edges
        )


# ============================================================================
# ROTATION PROCESSOR
# ============================================================================

class RotationProcessor:
    """
    Mental rotation processing.

    "Ba'el rotates in mental space." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._rotation_rate = 50.0  # Degrees per second
        self._base_time = 400.0     # Base processing time (ms)
        self._strategy = Strategy.HOLISTIC

        self._lock = threading.RLock()

    def set_strategy(
        self,
        strategy: Strategy
    ) -> None:
        """Set rotation strategy."""
        self._strategy = strategy

    def rotate_mentally(
        self,
        obj: SpatialObject,
        axis: RotationAxis,
        angle: float
    ) -> Tuple[SpatialObject, float]:
        """
        Mentally rotate object.
        Returns (rotated_object, time_ms).
        """
        # Calculate rotation time (linear with angle)
        angle_degrees = abs(math.degrees(angle))

        # Shepard & Metzler finding: RT increases linearly with angle
        rotation_time = self._base_time + (angle_degrees / self._rotation_rate * 1000)

        # Add noise
        rotation_time += random.gauss(0, 50)
        rotation_time = max(self._base_time, rotation_time)

        # Actually rotate
        rotated = obj.rotate(axis, angle)

        return rotated, rotation_time

    def compare_objects(
        self,
        obj_a: SpatialObject,
        obj_b: SpatialObject
    ) -> Tuple[bool, float]:
        """
        Compare two objects for match.
        Returns (same_object, confidence).
        """
        # Compare vertices after normalization
        if len(obj_a.vertices) != len(obj_b.vertices):
            return False, 0.9

        # Check if one is mirrored
        if obj_a.is_mirrored != obj_b.is_mirrored:
            return False, 0.85

        # Compare structure (simplified)
        total_dist = 0.0
        for va, vb in zip(obj_a.vertices, obj_b.vertices):
            total_dist += va.distance(vb)

        avg_dist = total_dist / len(obj_a.vertices)

        if avg_dist < 0.5:
            return True, 0.9
        else:
            return False, 0.7

    def estimate_rotation_angle(
        self,
        obj_a: SpatialObject,
        obj_b: SpatialObject
    ) -> float:
        """Estimate rotation angle between objects."""
        # Simplified: use centroid difference
        centroid_a = Point3D(
            sum(v.x for v in obj_a.vertices) / len(obj_a.vertices),
            sum(v.y for v in obj_a.vertices) / len(obj_a.vertices),
            sum(v.z for v in obj_a.vertices) / len(obj_a.vertices)
        )

        centroid_b = Point3D(
            sum(v.x for v in obj_b.vertices) / len(obj_b.vertices),
            sum(v.y for v in obj_b.vertices) / len(obj_b.vertices),
            sum(v.z for v in obj_b.vertices) / len(obj_b.vertices)
        )

        # Estimate angle from vertex positions
        dist = centroid_a.distance(centroid_b)
        angle = math.atan2(dist, 1.0)

        return angle


# ============================================================================
# TRIAL GENERATOR
# ============================================================================

class TrialGenerator:
    """
    Generate rotation trials.

    "Ba'el creates spatial challenges." — Ba'el
    """

    def __init__(
        self,
        object_generator: ObjectGenerator
    ):
        """Initialize generator."""
        self._object_gen = object_generator
        self._trial_counter = 0
        self._lock = threading.RLock()

    def _generate_trial_id(self) -> str:
        self._trial_counter += 1
        return f"trial_{self._trial_counter}"

    def generate_trial(
        self,
        trial_type: TrialType = TrialType.SAME,
        rotation_angle: float = None,
        rotation_axis: RotationAxis = RotationAxis.Y
    ) -> RotationTrial:
        """Generate a rotation trial."""
        with self._lock:
            # Generate base object
            obj_a = self._object_gen.generate_shepard_metzler()

            if rotation_angle is None:
                rotation_angle = random.uniform(0, math.pi)

            if trial_type == TrialType.SAME:
                # Same object, rotated
                obj_b = obj_a.rotate(rotation_axis, rotation_angle)
            elif trial_type == TrialType.MIRROR:
                # Mirror, then rotate
                obj_b = obj_a.mirror().rotate(rotation_axis, rotation_angle)
            else:
                # Different object
                obj_b = self._object_gen.generate_shepard_metzler()

            return RotationTrial(
                id=self._generate_trial_id(),
                object_a=obj_a,
                object_b=obj_b,
                trial_type=trial_type,
                rotation_angle=rotation_angle,
                rotation_axis=rotation_axis
            )

    def generate_experiment(
        self,
        n_same: int = 20,
        n_mirror: int = 20,
        angles: List[float] = None
    ) -> List[RotationTrial]:
        """Generate a full experiment."""
        if angles is None:
            angles = [0, 20, 40, 60, 80, 100, 120, 140, 160, 180]
            angles = [math.radians(a) for a in angles]

        trials = []

        for _ in range(n_same):
            angle = random.choice(angles)
            trials.append(self.generate_trial(TrialType.SAME, angle))

        for _ in range(n_mirror):
            angle = random.choice(angles)
            trials.append(self.generate_trial(TrialType.MIRROR, angle))

        random.shuffle(trials)
        return trials


# ============================================================================
# MENTAL ROTATION ENGINE
# ============================================================================

class MentalRotationEngine:
    """
    Complete mental rotation engine.

    "Ba'el's spatial transformation." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._object_gen = ObjectGenerator()
        self._processor = RotationProcessor()
        self._trial_gen = TrialGenerator(self._object_gen)

        self._responses: List[RotationResponse] = []

        self._lock = threading.RLock()

    # Object creation

    def create_object(
        self,
        object_type: ObjectType = ObjectType.SHEPARD_METZLER
    ) -> SpatialObject:
        """Create a spatial object."""
        if object_type == ObjectType.SHEPARD_METZLER:
            return self._object_gen.generate_shepard_metzler()
        elif object_type == ObjectType.CUBE:
            return self._object_gen.generate_cube()
        else:
            return self._object_gen.generate_letter()

    # Rotation

    def rotate_object(
        self,
        obj: SpatialObject,
        axis: RotationAxis,
        angle_degrees: float
    ) -> Tuple[SpatialObject, float]:
        """Rotate object and return time."""
        angle_rad = math.radians(angle_degrees)
        return self._processor.rotate_mentally(obj, axis, angle_rad)

    def mirror_object(
        self,
        obj: SpatialObject,
        axis: RotationAxis = RotationAxis.X
    ) -> SpatialObject:
        """Create mirrored object."""
        return obj.mirror(axis)

    # Comparison

    def compare_objects(
        self,
        obj_a: SpatialObject,
        obj_b: SpatialObject
    ) -> Tuple[bool, float]:
        """Compare if objects are same (ignoring rotation)."""
        return self._processor.compare_objects(obj_a, obj_b)

    # Trials

    def generate_trial(
        self,
        trial_type: TrialType = TrialType.SAME,
        angle_degrees: float = None
    ) -> RotationTrial:
        """Generate rotation trial."""
        angle_rad = math.radians(angle_degrees) if angle_degrees else None
        return self._trial_gen.generate_trial(trial_type, angle_rad)

    def respond_to_trial(
        self,
        trial: RotationTrial,
        response: TrialType = None
    ) -> RotationResponse:
        """Respond to a trial (simulated)."""
        # Simulate mental rotation response
        angle_degrees = math.degrees(trial.rotation_angle)

        # Calculate RT based on angle (Shepard & Metzler slope)
        rt = self._processor._base_time + (angle_degrees * 10)  # 10ms per degree
        rt += random.gauss(0, 50)
        rt = max(300, rt)

        # Determine response accuracy
        if response is None:
            # Simulate response with some error
            if trial.trial_type == TrialType.MIRROR:
                # Harder to detect mirror
                correct_prob = 0.85
            else:
                correct_prob = 0.95

            if random.random() < correct_prob:
                response = trial.trial_type
            else:
                response = random.choice(list(TrialType))

        correct = response == trial.trial_type

        resp = RotationResponse(
            trial_id=trial.id,
            response=response,
            response_time=rt,
            correct=correct
        )

        self._responses.append(resp)
        return resp

    # Experiment

    def run_experiment(
        self,
        n_trials: int = 40,
        angles: List[float] = None
    ) -> List[RotationResponse]:
        """Run full experiment."""
        if angles is None:
            angles = [0, 45, 90, 135, 180]

        trials = self._trial_gen.generate_experiment(
            n_same=n_trials // 2,
            n_mirror=n_trials // 2,
            angles=[math.radians(a) for a in angles]
        )

        responses = []
        for trial in trials:
            resp = self.respond_to_trial(trial)
            responses.append(resp)

        return responses

    # Analysis

    def get_metrics(self) -> RotationMetrics:
        """Get performance metrics."""
        if not self._responses:
            return RotationMetrics(
                accuracy=0.0,
                mean_rt=0.0,
                slope=0.0,
                intercept=0.0
            )

        accuracy = sum(1 for r in self._responses if r.correct) / len(self._responses)
        mean_rt = sum(r.response_time for r in self._responses) / len(self._responses)

        # Slope would be calculated from angle-RT regression
        slope = 10.0  # ms per degree (typical)
        intercept = 400.0

        return RotationMetrics(
            accuracy=accuracy,
            mean_rt=mean_rt,
            slope=slope,
            intercept=intercept
        )

    def get_rt_by_angle(self) -> Dict[float, float]:
        """Get mean RT by rotation angle."""
        # Would need trial info linked to responses
        return {}

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'total_trials': len(self._responses),
            'accuracy': self.get_metrics().accuracy
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mental_rotation_engine() -> MentalRotationEngine:
    """Create mental rotation engine."""
    return MentalRotationEngine()


def run_shepard_metzler_experiment(
    n_trials: int = 40
) -> Dict[str, Any]:
    """Run a Shepard & Metzler style experiment."""
    engine = create_mental_rotation_engine()

    responses = engine.run_experiment(n_trials=n_trials)
    metrics = engine.get_metrics()

    return {
        'n_trials': n_trials,
        'accuracy': metrics.accuracy,
        'mean_rt': metrics.mean_rt,
        'slope': metrics.slope,
        'responses': responses
    }


def get_rotation_facts() -> Dict[str, str]:
    """Get facts about mental rotation."""
    return {
        'linear_increase': 'RT increases linearly with rotation angle (Shepard & Metzler, 1971)',
        'rate': 'Typical rotation rate is about 60° per second',
        'gender': 'Males often show small advantage, but varies by training',
        'training': 'Mental rotation ability can be improved with practice',
        'handedness': 'Hands are rotated using similar processes'
    }
