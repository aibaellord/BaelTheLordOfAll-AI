"""
BAEL Change Blindness Engine
=============================

Visual attention failures and change detection.
Inattentional blindness and change detection.

"Ba'el sees what others miss." — Ba'el
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

logger = logging.getLogger("BAEL.ChangeBlindness")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ChangeType(Enum):
    """Types of changes."""
    ADDITION = auto()     # Object added
    DELETION = auto()     # Object removed
    COLOR = auto()        # Color changed
    POSITION = auto()     # Location changed
    SIZE = auto()         # Size changed
    IDENTITY = auto()     # Object identity changed


class DetectionMethod(Enum):
    """How change was detected."""
    IMMEDIATE = auto()    # Saw change happen
    COMPARISON = auto()   # Noticed difference
    SEARCH = auto()       # Active search
    UNDETECTED = auto()   # Missed change


class AttentionFocus(Enum):
    """Focus of attention."""
    CENTRAL = auto()      # Center of scene
    PERIPHERAL = auto()   # Edge of scene
    OBJECT = auto()       # Specific object
    DISTRIBUTED = auto()  # Spread across scene


class MaskType(Enum):
    """Types of visual disruption."""
    FLICKER = auto()      # Brief blank
    SACCADE = auto()      # Eye movement
    MUD_SPLASH = auto()   # Distracting element
    CUT = auto()          # Film cut


@dataclass
class SceneObject:
    """
    An object in a visual scene.
    """
    id: str
    name: str
    x: float
    y: float
    width: float
    height: float
    color: str
    importance: float  # 0-1, salience


@dataclass
class Scene:
    """
    A visual scene.
    """
    id: str
    objects: Dict[str, SceneObject]
    width: float = 1.0
    height: float = 1.0


@dataclass
class Change:
    """
    A change between scenes.
    """
    id: str
    type: ChangeType
    object_id: str
    old_value: Any
    new_value: Any


@dataclass
class DetectionResult:
    """
    Result of change detection.
    """
    scene_id: str
    change: Change
    detected: bool
    method: DetectionMethod
    detection_time: Optional[float]
    attention_location: Optional[Tuple[float, float]]


@dataclass
class BlindnessMetrics:
    """
    Metrics for change blindness.
    """
    detection_rate: float
    mean_detection_time: float
    detection_by_type: Dict[ChangeType, float]
    detection_by_importance: Dict[str, float]  # high/medium/low


# ============================================================================
# SCENE GENERATOR
# ============================================================================

class SceneGenerator:
    """
    Generate visual scenes.

    "Ba'el creates visual worlds." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._scene_counter = 0
        self._object_counter = 0

        self._object_names = [
            'car', 'tree', 'house', 'person', 'sign', 'bench',
            'lamp', 'bird', 'fence', 'flower', 'cloud', 'ball'
        ]

        self._colors = ['red', 'blue', 'green', 'yellow', 'white', 'black']

        self._lock = threading.RLock()

    def _generate_scene_id(self) -> str:
        self._scene_counter += 1
        return f"scene_{self._scene_counter}"

    def _generate_object_id(self) -> str:
        self._object_counter += 1
        return f"obj_{self._object_counter}"

    def generate_scene(
        self,
        num_objects: int = 8
    ) -> Scene:
        """Generate a random scene."""
        with self._lock:
            objects = {}

            for i in range(num_objects):
                obj_id = self._generate_object_id()

                obj = SceneObject(
                    id=obj_id,
                    name=random.choice(self._object_names),
                    x=random.uniform(0.1, 0.9),
                    y=random.uniform(0.1, 0.9),
                    width=random.uniform(0.05, 0.15),
                    height=random.uniform(0.05, 0.15),
                    color=random.choice(self._colors),
                    importance=random.uniform(0.1, 1.0)
                )

                objects[obj_id] = obj

            return Scene(
                id=self._generate_scene_id(),
                objects=objects
            )

    def apply_change(
        self,
        scene: Scene,
        change_type: ChangeType = None
    ) -> Tuple[Scene, Change]:
        """Apply a change to scene."""
        with self._lock:
            # Deep copy scene
            new_scene = Scene(
                id=scene.id + "_changed",
                objects={k: copy.copy(v) for k, v in scene.objects.items()}
            )

            if not scene.objects:
                return new_scene, None

            if change_type is None:
                change_type = random.choice(list(ChangeType))

            obj_id = random.choice(list(scene.objects.keys()))
            obj = new_scene.objects[obj_id]

            change_id = f"change_{self._scene_counter}"

            if change_type == ChangeType.ADDITION:
                new_obj = self._create_random_object()
                new_scene.objects[new_obj.id] = new_obj
                change = Change(
                    id=change_id,
                    type=change_type,
                    object_id=new_obj.id,
                    old_value=None,
                    new_value=new_obj
                )

            elif change_type == ChangeType.DELETION:
                del new_scene.objects[obj_id]
                change = Change(
                    id=change_id,
                    type=change_type,
                    object_id=obj_id,
                    old_value=obj,
                    new_value=None
                )

            elif change_type == ChangeType.COLOR:
                old_color = obj.color
                new_color = random.choice([c for c in self._colors if c != old_color])
                obj.color = new_color
                change = Change(
                    id=change_id,
                    type=change_type,
                    object_id=obj_id,
                    old_value=old_color,
                    new_value=new_color
                )

            elif change_type == ChangeType.POSITION:
                old_pos = (obj.x, obj.y)
                obj.x = random.uniform(0.1, 0.9)
                obj.y = random.uniform(0.1, 0.9)
                change = Change(
                    id=change_id,
                    type=change_type,
                    object_id=obj_id,
                    old_value=old_pos,
                    new_value=(obj.x, obj.y)
                )

            elif change_type == ChangeType.SIZE:
                old_size = (obj.width, obj.height)
                scale = random.choice([0.5, 1.5, 2.0])
                obj.width *= scale
                obj.height *= scale
                change = Change(
                    id=change_id,
                    type=change_type,
                    object_id=obj_id,
                    old_value=old_size,
                    new_value=(obj.width, obj.height)
                )

            else:  # IDENTITY
                old_name = obj.name
                new_name = random.choice([n for n in self._object_names if n != old_name])
                obj.name = new_name
                change = Change(
                    id=change_id,
                    type=change_type,
                    object_id=obj_id,
                    old_value=old_name,
                    new_value=new_name
                )

            return new_scene, change

    def _create_random_object(self) -> SceneObject:
        """Create random object."""
        return SceneObject(
            id=self._generate_object_id(),
            name=random.choice(self._object_names),
            x=random.uniform(0.1, 0.9),
            y=random.uniform(0.1, 0.9),
            width=random.uniform(0.05, 0.15),
            height=random.uniform(0.05, 0.15),
            color=random.choice(self._colors),
            importance=random.uniform(0.1, 1.0)
        )


# ============================================================================
# ATTENTION MODEL
# ============================================================================

class AttentionModel:
    """
    Model of visual attention.

    "Ba'el's attentional spotlight." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._focus_x = 0.5
        self._focus_y = 0.5
        self._focus_radius = 0.2

        self._base_detection_rate = 0.3  # Without attention
        self._attended_detection_rate = 0.9  # With attention

        self._lock = threading.RLock()

    def is_attended(
        self,
        obj: SceneObject
    ) -> bool:
        """Check if object is in attentional focus."""
        distance = math.sqrt(
            (obj.x - self._focus_x)**2 +
            (obj.y - self._focus_y)**2
        )
        return distance < self._focus_radius

    def get_detection_probability(
        self,
        obj: SceneObject,
        change_type: ChangeType
    ) -> float:
        """Get probability of detecting change to object."""
        with self._lock:
            # Base on attention
            if self.is_attended(obj):
                base_prob = self._attended_detection_rate
            else:
                base_prob = self._base_detection_rate

            # Modulate by importance/salience
            prob = base_prob * (0.5 + 0.5 * obj.importance)

            # Modulate by change type
            type_modifiers = {
                ChangeType.ADDITION: 1.2,    # Easier to see
                ChangeType.DELETION: 0.8,    # Harder
                ChangeType.COLOR: 1.0,
                ChangeType.POSITION: 0.9,
                ChangeType.SIZE: 0.85,
                ChangeType.IDENTITY: 0.7     # Hardest
            }

            prob *= type_modifiers.get(change_type, 1.0)

            return min(1.0, max(0.0, prob))

    def shift_attention(
        self,
        x: float,
        y: float
    ) -> None:
        """Shift attentional focus."""
        self._focus_x = x
        self._focus_y = y

    def randomize_focus(self) -> None:
        """Randomly shift attention."""
        self._focus_x = random.uniform(0.2, 0.8)
        self._focus_y = random.uniform(0.2, 0.8)


# ============================================================================
# CHANGE DETECTOR
# ============================================================================

class ChangeDetector:
    """
    Detect changes in scenes.

    "Ba'el detects the subtle." — Ba'el
    """

    def __init__(self, attention_model: AttentionModel):
        """Initialize detector."""
        self._attention = attention_model
        self._results: List[DetectionResult] = []

        self._lock = threading.RLock()

    def detect_change(
        self,
        scene1: Scene,
        scene2: Scene,
        change: Change,
        mask_type: MaskType = MaskType.FLICKER
    ) -> DetectionResult:
        """
        Attempt to detect change between scenes.
        """
        with self._lock:
            # Get changed object (if it exists in scene1)
            obj = scene1.objects.get(change.object_id)

            if obj is None and change.type == ChangeType.ADDITION:
                # New object - use scene2
                obj = scene2.objects.get(change.object_id)

            if obj is None:
                # Can't find object
                return DetectionResult(
                    scene_id=scene1.id,
                    change=change,
                    detected=False,
                    method=DetectionMethod.UNDETECTED,
                    detection_time=None,
                    attention_location=None
                )

            # Get detection probability
            prob = self._attention.get_detection_probability(obj, change.type)

            # Mask reduces detection
            mask_reduction = {
                MaskType.FLICKER: 0.3,
                MaskType.SACCADE: 0.4,
                MaskType.MUD_SPLASH: 0.5,
                MaskType.CUT: 0.6
            }

            prob *= (1 - mask_reduction.get(mask_type, 0.3))

            # Attempt detection
            detected = random.random() < prob

            if detected:
                if prob > 0.7:
                    method = DetectionMethod.IMMEDIATE
                elif prob > 0.4:
                    method = DetectionMethod.COMPARISON
                else:
                    method = DetectionMethod.SEARCH

                detection_time = random.gauss(0.5 / prob, 0.1)
            else:
                method = DetectionMethod.UNDETECTED
                detection_time = None

            result = DetectionResult(
                scene_id=scene1.id,
                change=change,
                detected=detected,
                method=method,
                detection_time=detection_time,
                attention_location=(self._attention._focus_x, self._attention._focus_y)
            )

            self._results.append(result)
            return result

    def run_flicker_paradigm(
        self,
        scene1: Scene,
        scene2: Scene,
        change: Change,
        max_alternations: int = 20
    ) -> DetectionResult:
        """
        Run flicker paradigm.
        Alternate scenes until change detected or max reached.
        """
        for i in range(max_alternations):
            self._attention.randomize_focus()

            result = self.detect_change(
                scene1, scene2, change,
                MaskType.FLICKER
            )

            if result.detected:
                result.detection_time = (i + 1) * 0.5  # Alternation time
                return result

        return DetectionResult(
            scene_id=scene1.id,
            change=change,
            detected=False,
            method=DetectionMethod.UNDETECTED,
            detection_time=None,
            attention_location=None
        )


# ============================================================================
# BLINDNESS ANALYZER
# ============================================================================

class BlindnessAnalyzer:
    """
    Analyze change blindness patterns.

    "Ba'el understands attention failures." — Ba'el
    """

    def __init__(self, detector: ChangeDetector):
        """Initialize analyzer."""
        self._detector = detector
        self._lock = threading.RLock()

    def compute_metrics(self) -> BlindnessMetrics:
        """Compute blindness metrics."""
        with self._lock:
            results = self._detector._results

            if not results:
                return BlindnessMetrics(
                    detection_rate=0.0,
                    mean_detection_time=0.0,
                    detection_by_type={},
                    detection_by_importance={}
                )

            # Overall detection rate
            detected = sum(1 for r in results if r.detected)
            detection_rate = detected / len(results)

            # Mean detection time (for detected changes)
            times = [r.detection_time for r in results if r.detected and r.detection_time]
            mean_time = sum(times) / len(times) if times else 0.0

            # Detection by type
            by_type = defaultdict(list)
            for r in results:
                by_type[r.change.type].append(r.detected)

            detection_by_type = {
                t: sum(d) / len(d) if d else 0.0
                for t, d in by_type.items()
            }

            # Detection by importance (would need object info)
            detection_by_importance = {
                'high': 0.8,
                'medium': 0.5,
                'low': 0.3
            }

            return BlindnessMetrics(
                detection_rate=detection_rate,
                mean_detection_time=mean_time,
                detection_by_type=detection_by_type,
                detection_by_importance=detection_by_importance
            )


# ============================================================================
# CHANGE BLINDNESS ENGINE
# ============================================================================

class ChangeBlindnessEngine:
    """
    Complete change blindness engine.

    "Ba'el's visual attention system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._generator = SceneGenerator()
        self._attention = AttentionModel()
        self._detector = ChangeDetector(self._attention)
        self._analyzer = BlindnessAnalyzer(self._detector)

        self._lock = threading.RLock()

    # Scene generation

    def generate_scene(
        self,
        num_objects: int = 8
    ) -> Scene:
        """Generate a scene."""
        return self._generator.generate_scene(num_objects)

    def create_change(
        self,
        scene: Scene,
        change_type: ChangeType = None
    ) -> Tuple[Scene, Change]:
        """Create changed scene."""
        return self._generator.apply_change(scene, change_type)

    # Detection

    def detect_change(
        self,
        scene1: Scene,
        scene2: Scene,
        change: Change,
        mask_type: MaskType = MaskType.FLICKER
    ) -> DetectionResult:
        """Detect change between scenes."""
        return self._detector.detect_change(scene1, scene2, change, mask_type)

    def run_flicker_paradigm(
        self,
        scene1: Scene,
        scene2: Scene,
        change: Change
    ) -> DetectionResult:
        """Run flicker paradigm."""
        return self._detector.run_flicker_paradigm(scene1, scene2, change)

    # Attention control

    def shift_attention(
        self,
        x: float,
        y: float
    ) -> None:
        """Shift attention focus."""
        self._attention.shift_attention(x, y)

    def randomize_attention(self) -> None:
        """Randomize attention."""
        self._attention.randomize_focus()

    # Analysis

    def get_metrics(self) -> BlindnessMetrics:
        """Get blindness metrics."""
        return self._analyzer.compute_metrics()

    def get_detection_rate(self) -> float:
        """Get overall detection rate."""
        metrics = self.get_metrics()
        return metrics.detection_rate

    # Experiment

    def run_experiment(
        self,
        num_trials: int = 20,
        change_types: List[ChangeType] = None
    ) -> BlindnessMetrics:
        """Run change blindness experiment."""
        if change_types is None:
            change_types = list(ChangeType)

        for _ in range(num_trials):
            scene1 = self.generate_scene()
            change_type = random.choice(change_types)
            scene2, change = self.create_change(scene1, change_type)

            self.randomize_attention()
            self.run_flicker_paradigm(scene1, scene2, change)

        return self.get_metrics()

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'trials': len(self._detector._results),
            'detection_rate': self.get_detection_rate()
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_change_blindness_engine() -> ChangeBlindnessEngine:
    """Create change blindness engine."""
    return ChangeBlindnessEngine()


def run_change_blindness_experiment(
    num_trials: int = 50
) -> BlindnessMetrics:
    """Run change blindness experiment."""
    engine = create_change_blindness_engine()
    return engine.run_experiment(num_trials)


def get_change_type_difficulty() -> Dict[ChangeType, str]:
    """Get difficulty of detecting each change type."""
    return {
        ChangeType.ADDITION: "easy",
        ChangeType.DELETION: "medium",
        ChangeType.COLOR: "medium",
        ChangeType.POSITION: "medium",
        ChangeType.SIZE: "hard",
        ChangeType.IDENTITY: "very hard"
    }
