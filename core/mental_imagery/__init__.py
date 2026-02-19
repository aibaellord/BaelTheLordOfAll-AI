"""
BAEL Mental Imagery Engine
============================

Kosslyn's visual imagery theory.
Mental rotation and scanning.

"Ba'el sees within the mind." — Ba'el
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

logger = logging.getLogger("BAEL.MentalImagery")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ImageryType(Enum):
    """Types of mental imagery."""
    VISUAL = auto()
    AUDITORY = auto()
    MOTOR = auto()
    SPATIAL = auto()


class ImageFormat(Enum):
    """Debate on image format."""
    PICTORIAL = auto()      # Kosslyn: quasi-pictorial
    PROPOSITIONAL = auto()  # Pylyshyn: propositional


class TransformationType(Enum):
    """Types of mental transformation."""
    ROTATION = auto()
    SCALING = auto()
    TRANSLATION = auto()
    REFLECTION = auto()


class ScanDirection(Enum):
    """Scanning direction."""
    LEFT_TO_RIGHT = auto()
    RIGHT_TO_LEFT = auto()
    TOP_TO_BOTTOM = auto()
    BOTTOM_TO_TOP = auto()
    ALONG_PATH = auto()


@dataclass
class Position2D:
    """
    2D position.
    """
    x: float
    y: float

    def distance_to(
        self,
        other: 'Position2D'
    ) -> float:
        """Calculate distance."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2
        )


@dataclass
class ImageObject:
    """
    An object in the mental image.
    """
    id: str
    label: str
    position: Position2D
    size: float
    orientation: float  # degrees


@dataclass
class MentalImage:
    """
    A mental image.
    """
    id: str
    name: str
    objects: List[ImageObject]
    resolution: float
    vividness: float
    decay_rate: float = 0.1


@dataclass
class RotationResult:
    """
    Result of mental rotation.
    """
    original_angle: float
    target_angle: float
    rotation_amount: float
    response_time: float
    is_match: bool


@dataclass
class ScanResult:
    """
    Result of mental scanning.
    """
    start_position: Position2D
    end_position: Position2D
    distance: float
    scan_time: float


@dataclass
class ImageryMetrics:
    """
    Imagery metrics.
    """
    total_images: int
    average_vividness: float
    rotation_time_per_degree: float
    scan_time_per_unit: float


# ============================================================================
# VISUAL BUFFER
# ============================================================================

class VisualBuffer:
    """
    Kosslyn's visual buffer.

    "Ba'el's inner screen." — Ba'el
    """

    def __init__(
        self,
        resolution: float = 1.0,
        max_size: float = 10.0
    ):
        """Initialize visual buffer."""
        self._resolution = resolution
        self._max_size = max_size
        self._current_image: Optional[MentalImage] = None

        self._lock = threading.RLock()

    def load_image(
        self,
        image: MentalImage
    ) -> None:
        """Load image into buffer."""
        self._current_image = image

    def get_image(self) -> Optional[MentalImage]:
        """Get current image."""
        return self._current_image

    def clear(self) -> None:
        """Clear buffer."""
        self._current_image = None

    def zoom(
        self,
        factor: float
    ) -> None:
        """Zoom image."""
        if self._current_image:
            for obj in self._current_image.objects:
                obj.size *= factor
                obj.position.x *= factor
                obj.position.y *= factor

    def pan(
        self,
        dx: float,
        dy: float
    ) -> None:
        """Pan image."""
        if self._current_image:
            for obj in self._current_image.objects:
                obj.position.x += dx
                obj.position.y += dy

    def decay(
        self,
        amount: float = None
    ) -> None:
        """Apply decay to image."""
        if self._current_image:
            decay = amount or self._current_image.decay_rate
            self._current_image.vividness *= (1 - decay)
            self._current_image.resolution *= (1 - decay * 0.5)


# ============================================================================
# MENTAL ROTATION
# ============================================================================

class MentalRotationSimulator:
    """
    Shepard & Metzler mental rotation.

    "Ba'el rotates inner forms." — Ba'el
    """

    def __init__(
        self,
        time_per_degree: float = 20.0  # ms per degree
    ):
        """Initialize simulator."""
        self._time_per_degree = time_per_degree
        self._lock = threading.RLock()

    def rotate_object(
        self,
        obj: ImageObject,
        degrees: float
    ) -> None:
        """Rotate an object."""
        obj.orientation = (obj.orientation + degrees) % 360

    def simulate_rotation_task(
        self,
        angle_difference: float,
        is_same: bool = True
    ) -> RotationResult:
        """Simulate mental rotation comparison."""
        # Response time proportional to angle
        rotation_amount = min(angle_difference, 360 - angle_difference)
        response_time = rotation_amount * self._time_per_degree

        # Add noise
        response_time += random.gauss(0, 50)
        response_time = max(200, response_time)

        # Accuracy
        if is_same:
            is_match = random.random() < 0.95  # High accuracy
        else:
            # Mirror images take longer and more errors
            is_match = random.random() < 0.90

        return RotationResult(
            original_angle=0.0,
            target_angle=angle_difference,
            rotation_amount=rotation_amount,
            response_time=response_time,
            is_match=is_match
        )

    def run_rotation_experiment(
        self,
        angles: List[float] = None
    ) -> List[RotationResult]:
        """Run rotation experiment at multiple angles."""
        if angles is None:
            angles = [0, 30, 60, 90, 120, 150, 180]

        results = []
        for angle in angles:
            result = self.simulate_rotation_task(angle, is_same=True)
            results.append(result)

        return results


# ============================================================================
# MENTAL SCANNING
# ============================================================================

class MentalScanningSimulator:
    """
    Kosslyn's mental scanning.

    "Ba'el traverses inner landscapes." — Ba'el
    """

    def __init__(
        self,
        time_per_unit: float = 100.0  # ms per unit distance
    ):
        """Initialize simulator."""
        self._time_per_unit = time_per_unit
        self._lock = threading.RLock()

    def scan_between_points(
        self,
        start: Position2D,
        end: Position2D
    ) -> ScanResult:
        """Scan between two points."""
        distance = start.distance_to(end)
        scan_time = distance * self._time_per_unit

        # Add noise
        scan_time += random.gauss(0, 30)
        scan_time = max(100, scan_time)

        return ScanResult(
            start_position=start,
            end_position=end,
            distance=distance,
            scan_time=scan_time
        )

    def scan_to_object(
        self,
        image: MentalImage,
        current_pos: Position2D,
        target_label: str
    ) -> Optional[ScanResult]:
        """Scan to a named object."""
        target_obj = None
        for obj in image.objects:
            if obj.label == target_label:
                target_obj = obj
                break

        if not target_obj:
            return None

        return self.scan_between_points(current_pos, target_obj.position)

    def run_scanning_experiment(
        self,
        image: MentalImage,
        start_label: str,
        target_labels: List[str]
    ) -> List[ScanResult]:
        """Run scanning experiment."""
        results = []

        # Find start object
        start_obj = None
        for obj in image.objects:
            if obj.label == start_label:
                start_obj = obj
                break

        if not start_obj:
            return results

        current_pos = start_obj.position

        for target in target_labels:
            result = self.scan_to_object(image, current_pos, target)
            if result:
                results.append(result)
                current_pos = result.end_position

        return results


# ============================================================================
# IMAGE GENERATION
# ============================================================================

class ImageGenerator:
    """
    Generate mental images.

    "Ba'el creates inner visions." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._image_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._image_counter += 1
        return f"image_{self._image_counter}"

    def create_image(
        self,
        name: str,
        objects: List[Tuple[str, float, float]] = None,
        vividness: float = 0.8
    ) -> MentalImage:
        """Create a mental image."""
        image_objects = []

        if objects:
            for i, (label, x, y) in enumerate(objects):
                obj = ImageObject(
                    id=f"obj_{i}",
                    label=label,
                    position=Position2D(x, y),
                    size=1.0,
                    orientation=0.0
                )
                image_objects.append(obj)

        return MentalImage(
            id=self._generate_id(),
            name=name,
            objects=image_objects,
            resolution=1.0,
            vividness=vividness
        )

    def create_map_image(
        self,
        name: str,
        locations: Dict[str, Tuple[float, float]]
    ) -> MentalImage:
        """Create a map-like image."""
        objects = [(label, x, y) for label, (x, y) in locations.items()]
        return self.create_image(name, objects)

    def create_3d_object(
        self,
        name: str,
        complexity: int = 4
    ) -> MentalImage:
        """Create a 3D-like object for rotation."""
        objects = []
        for i in range(complexity):
            angle = (2 * math.pi * i) / complexity
            x = math.cos(angle) * 2
            y = math.sin(angle) * 2
            objects.append((f"part_{i}", x, y))

        return self.create_image(name, objects)


# ============================================================================
# MENTAL IMAGERY ENGINE
# ============================================================================

class MentalImageryEngine:
    """
    Complete mental imagery engine.

    "Ba'el's imagination system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._buffer = VisualBuffer()
        self._rotation = MentalRotationSimulator()
        self._scanning = MentalScanningSimulator()
        self._generator = ImageGenerator()

        self._images: Dict[str, MentalImage] = {}
        self._rotation_results: List[RotationResult] = []
        self._scan_results: List[ScanResult] = []

        self._lock = threading.RLock()

    # Image creation and management

    def create_image(
        self,
        name: str,
        objects: List[Tuple[str, float, float]] = None,
        vividness: float = 0.8
    ) -> MentalImage:
        """Create and store a mental image."""
        image = self._generator.create_image(name, objects, vividness)
        self._images[image.id] = image
        return image

    def create_map(
        self,
        name: str,
        locations: Dict[str, Tuple[float, float]]
    ) -> MentalImage:
        """Create a mental map."""
        image = self._generator.create_map_image(name, locations)
        self._images[image.id] = image
        return image

    def load_image(
        self,
        image_id: str
    ) -> bool:
        """Load image into visual buffer."""
        image = self._images.get(image_id)
        if image:
            self._buffer.load_image(copy.deepcopy(image))
            return True
        return False

    # Mental rotation

    def rotate(
        self,
        degrees: float,
        object_label: str = None
    ) -> None:
        """Rotate object(s) in current image."""
        image = self._buffer.get_image()
        if not image:
            return

        if object_label:
            for obj in image.objects:
                if obj.label == object_label:
                    self._rotation.rotate_object(obj, degrees)
        else:
            for obj in image.objects:
                self._rotation.rotate_object(obj, degrees)

    def mental_rotation_task(
        self,
        angle_difference: float,
        is_same: bool = True
    ) -> RotationResult:
        """Perform mental rotation comparison."""
        result = self._rotation.simulate_rotation_task(
            angle_difference, is_same
        )
        self._rotation_results.append(result)
        return result

    def run_rotation_experiment(
        self,
        angles: List[float] = None
    ) -> Dict[float, float]:
        """Run mental rotation experiment."""
        results = self._rotation.run_rotation_experiment(angles)
        self._rotation_results.extend(results)

        return {
            r.rotation_amount: r.response_time
            for r in results
        }

    # Mental scanning

    def scan_to(
        self,
        target_label: str
    ) -> Optional[ScanResult]:
        """Scan to a target object."""
        image = self._buffer.get_image()
        if not image:
            return None

        # Assume focus at center
        current_pos = Position2D(0, 0)

        result = self._scanning.scan_to_object(
            image, current_pos, target_label
        )

        if result:
            self._scan_results.append(result)

        return result

    def scan_path(
        self,
        start_label: str,
        path: List[str]
    ) -> List[ScanResult]:
        """Scan along a path."""
        image = self._buffer.get_image()
        if not image:
            return []

        results = self._scanning.run_scanning_experiment(
            image, start_label, path
        )
        self._scan_results.extend(results)

        return results

    # Image manipulation

    def zoom(
        self,
        factor: float
    ) -> None:
        """Zoom current image."""
        self._buffer.zoom(factor)

    def pan(
        self,
        dx: float,
        dy: float
    ) -> None:
        """Pan current image."""
        self._buffer.pan(dx, dy)

    def let_decay(
        self,
        amount: float = None
    ) -> None:
        """Let image decay."""
        self._buffer.decay(amount)

    # Kosslyn's island map experiment

    def create_island_map(self) -> MentalImage:
        """Create Kosslyn's famous island map."""
        locations = {
            'hut': (0.0, 0.0),
            'tree': (2.0, 1.0),
            'rock': (4.0, 0.5),
            'well': (1.0, 3.0),
            'lake': (3.5, 3.5),
            'beach': (5.0, 2.0)
        }

        return self.create_map('island', locations)

    def run_island_experiment(self) -> Dict[str, Any]:
        """Run Kosslyn's island scanning experiment."""
        image = self.create_island_map()
        self._buffer.load_image(copy.deepcopy(image))

        # Scan from hut to various locations
        targets = ['tree', 'rock', 'well', 'lake', 'beach']

        results = {}
        for target in targets:
            result = self._scanning.scan_to_object(
                self._buffer.get_image(),
                Position2D(0, 0),  # Start from hut
                target
            )
            if result:
                results[target] = {
                    'distance': result.distance,
                    'scan_time': result.scan_time
                }
                self._scan_results.append(result)

        return results

    # Analysis

    def get_rotation_slope(self) -> float:
        """Get rotation time per degree."""
        if not self._rotation_results:
            return self._rotation._time_per_degree

        # Linear regression
        angles = [r.rotation_amount for r in self._rotation_results]
        times = [r.response_time for r in self._rotation_results]

        if len(set(angles)) < 2:
            return self._rotation._time_per_degree

        mean_angle = sum(angles) / len(angles)
        mean_time = sum(times) / len(times)

        numerator = sum(
            (a - mean_angle) * (t - mean_time)
            for a, t in zip(angles, times)
        )
        denominator = sum((a - mean_angle) ** 2 for a in angles)

        if denominator > 0:
            return numerator / denominator
        return self._rotation._time_per_degree

    def get_scan_slope(self) -> float:
        """Get scan time per unit distance."""
        if not self._scan_results:
            return self._scanning._time_per_unit

        distances = [r.distance for r in self._scan_results]
        times = [r.scan_time for r in self._scan_results]

        if len(set(distances)) < 2:
            return self._scanning._time_per_unit

        mean_dist = sum(distances) / len(distances)
        mean_time = sum(times) / len(times)

        numerator = sum(
            (d - mean_dist) * (t - mean_time)
            for d, t in zip(distances, times)
        )
        denominator = sum((d - mean_dist) ** 2 for d in distances)

        if denominator > 0:
            return numerator / denominator
        return self._scanning._time_per_unit

    def get_metrics(self) -> ImageryMetrics:
        """Get imagery metrics."""
        images = list(self._images.values())

        return ImageryMetrics(
            total_images=len(images),
            average_vividness=(
                sum(i.vividness for i in images) / len(images)
                if images else 0.0
            ),
            rotation_time_per_degree=self.get_rotation_slope(),
            scan_time_per_unit=self.get_scan_slope()
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'images': len(self._images),
            'rotation_trials': len(self._rotation_results),
            'scan_trials': len(self._scan_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_mental_imagery_engine() -> MentalImageryEngine:
    """Create mental imagery engine."""
    return MentalImageryEngine()


def demonstrate_mental_imagery() -> Dict[str, Any]:
    """Demonstrate mental imagery."""
    engine = create_mental_imagery_engine()

    # Mental rotation experiment
    rotation_results = engine.run_rotation_experiment([0, 30, 60, 90, 120, 150, 180])

    # Island scanning experiment
    island_results = engine.run_island_experiment()

    metrics = engine.get_metrics()

    return {
        'rotation_times': rotation_results,
        'island_scans': island_results,
        'rotation_slope': metrics.rotation_time_per_degree,
        'scan_slope': metrics.scan_time_per_unit,
        'interpretation': (
            f"Mental rotation: ~{metrics.rotation_time_per_degree:.1f}ms per degree, "
            f"Mental scanning: ~{metrics.scan_time_per_unit:.1f}ms per unit"
        )
    }


def get_mental_imagery_facts() -> Dict[str, str]:
    """Get facts about mental imagery."""
    return {
        'kosslyn': 'Mental images are quasi-pictorial representations',
        'shepard_metzler': 'Mental rotation time proportional to angle',
        'scanning': 'Scan time proportional to imagined distance',
        'visual_buffer': 'Limited capacity visual representation',
        'pylyshyn': 'Alternative: images are propositional',
        'size_effect': 'Small imagined objects harder to inspect',
        'overflow': 'Large images extend beyond buffer',
        'vividness': 'Individual differences in imagery ability'
    }
