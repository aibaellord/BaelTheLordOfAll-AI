"""
BAEL Boundary Extension Engine
================================

Scene memory distortion - remembering seeing more than was shown.
Extrapolating beyond perceptual boundaries.

"Ba'el sees beyond the edge." — Ba'el
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

logger = logging.getLogger("BAEL.BoundaryExtension")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SceneType(Enum):
    """Types of visual scenes."""
    LANDSCAPE = auto()
    INTERIOR = auto()
    CLOSEUP = auto()
    ABSTRACT = auto()
    CROWDED = auto()


class ViewType(Enum):
    """Types of camera views."""
    WIDE = auto()
    MEDIUM = auto()
    CLOSE = auto()
    EXTREME_CLOSE = auto()


class ExtensionDirection(Enum):
    """Directions of boundary extension."""
    ALL = auto()
    HORIZONTAL = auto()
    VERTICAL = auto()
    NONE = auto()


@dataclass
class SceneContent:
    """
    Content of a visual scene.
    """
    objects: List[str]
    focal_object: str
    background: str
    depth_cues: float  # 0-1


@dataclass
class Scene:
    """
    A visual scene with boundaries.
    """
    id: str
    scene_type: SceneType
    view_type: ViewType
    content: SceneContent
    actual_boundaries: Dict[str, float]  # left, right, top, bottom in normalized units
    presentation_time_ms: float


@dataclass
class RememberedScene:
    """
    A remembered scene (potentially extended).
    """
    scene_id: str
    remembered_boundaries: Dict[str, float]
    extension_amount: Dict[str, float]
    total_extension: float
    confidence: float


@dataclass
class BoundaryExtensionMetrics:
    """
    Boundary extension metrics.
    """
    mean_extension: float
    extension_by_view: Dict[str, float]
    confidence_correlation: float


# ============================================================================
# PERCEPTUAL SCHEMA MODEL
# ============================================================================

class PerceptualSchemaModel:
    """
    Perceptual schema model of boundary extension.

    "Ba'el's scene completion." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Extension parameters
        self._base_extension = 0.1  # 10% base extension
        self._close_view_boost = 0.15  # Close-ups extend more
        self._depth_cue_factor = 0.1

        self._lock = threading.RLock()

    def calculate_extension(
        self,
        scene: Scene
    ) -> Dict[str, float]:
        """Calculate expected boundary extension."""
        # Base extension
        base = self._base_extension

        # Close-up views extend more (more to extrapolate)
        if scene.view_type == ViewType.EXTREME_CLOSE:
            view_bonus = self._close_view_boost * 2
        elif scene.view_type == ViewType.CLOSE:
            view_bonus = self._close_view_boost
        elif scene.view_type == ViewType.MEDIUM:
            view_bonus = self._close_view_boost * 0.5
        else:
            view_bonus = 0

        # Depth cues increase extension
        depth_bonus = scene.content.depth_cues * self._depth_cue_factor

        # Total extension
        extension = base + view_bonus + depth_bonus

        # Apply to all directions with some variation
        extensions = {
            'left': extension * random.uniform(0.8, 1.2),
            'right': extension * random.uniform(0.8, 1.2),
            'top': extension * random.uniform(0.7, 1.1),
            'bottom': extension * random.uniform(0.7, 1.1)
        }

        return extensions

    def apply_extension(
        self,
        actual_boundaries: Dict[str, float],
        extensions: Dict[str, float]
    ) -> Dict[str, float]:
        """Apply extension to boundaries."""
        remembered = {}

        # Extend outward
        remembered['left'] = actual_boundaries['left'] - extensions['left']
        remembered['right'] = actual_boundaries['right'] + extensions['right']
        remembered['top'] = actual_boundaries['top'] - extensions['top']
        remembered['bottom'] = actual_boundaries['bottom'] + extensions['bottom']

        return remembered


# ============================================================================
# SCENE MEMORY SYSTEM
# ============================================================================

class SceneMemorySystem:
    """
    Scene memory with boundary extension.

    "Ba'el's visual memory." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._schema_model = PerceptualSchemaModel()

        self._scenes: Dict[str, Scene] = {}
        self._memories: Dict[str, RememberedScene] = {}

        self._scene_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._scene_counter += 1
        return f"scene_{self._scene_counter}"

    def view_scene(
        self,
        scene_type: SceneType,
        view_type: ViewType,
        objects: List[str] = None,
        focal_object: str = "center_object",
        presentation_time_ms: float = 1000
    ) -> Scene:
        """View and encode a scene."""
        if objects is None:
            objects = [f"object_{i}" for i in range(random.randint(3, 7))]

        content = SceneContent(
            objects=objects,
            focal_object=focal_object,
            background="background_texture",
            depth_cues=random.uniform(0.3, 0.9)
        )

        # Actual boundaries (normalized 0-1)
        boundaries = {
            'left': 0.0,
            'right': 1.0,
            'top': 0.0,
            'bottom': 1.0
        }

        scene = Scene(
            id=self._generate_id(),
            scene_type=scene_type,
            view_type=view_type,
            content=content,
            actual_boundaries=boundaries,
            presentation_time_ms=presentation_time_ms
        )

        self._scenes[scene.id] = scene

        # Encode with extension
        extensions = self._schema_model.calculate_extension(scene)
        remembered_bounds = self._schema_model.apply_extension(boundaries, extensions)

        total_extension = sum(extensions.values())

        memory = RememberedScene(
            scene_id=scene.id,
            remembered_boundaries=remembered_bounds,
            extension_amount=extensions,
            total_extension=total_extension,
            confidence=random.uniform(0.6, 0.9)
        )

        self._memories[scene.id] = memory

        return scene

    def recall_scene(
        self,
        scene_id: str,
        delay_minutes: float = 0
    ) -> Optional[RememberedScene]:
        """Recall a scene (with boundary extension)."""
        memory = self._memories.get(scene_id)
        if not memory:
            return None

        # Extension may increase slightly with delay
        if delay_minutes > 0:
            delay_factor = 1 + delay_minutes * 0.01
            for key in memory.extension_amount:
                memory.extension_amount[key] *= delay_factor
            memory.total_extension *= delay_factor

        return memory


# ============================================================================
# EXPERIMENTAL PARADIGM
# ============================================================================

class BoundaryExtensionParadigm:
    """
    Boundary extension experimental paradigm.

    "Ba'el's extension study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_experiment(
        self,
        n_scenes: int = 20,
        delay_minutes: float = 5
    ) -> Dict[str, Any]:
        """Run boundary extension experiment."""
        system = SceneMemorySystem()

        # View scenes with varying views
        view_types = list(ViewType)

        for i in range(n_scenes):
            view = view_types[i % len(view_types)]
            system.view_scene(SceneType.LANDSCAPE, view)

        # Recall scenes
        extensions = []
        by_view: Dict[str, List[float]] = defaultdict(list)

        for scene_id, scene in system._scenes.items():
            memory = system.recall_scene(scene_id, delay_minutes)
            if memory:
                extensions.append(memory.total_extension)
                by_view[scene.view_type.name].append(memory.total_extension)

        mean_extension = sum(extensions) / len(extensions) if extensions else 0

        view_means = {
            view: sum(exts) / len(exts) if exts else 0
            for view, exts in by_view.items()
        }

        return {
            'n_scenes': n_scenes,
            'mean_extension': mean_extension,
            'extension_by_view': view_means,
            'delay_minutes': delay_minutes
        }

    def run_view_comparison(
        self,
        n_per_view: int = 10
    ) -> Dict[str, Any]:
        """Compare extension across view types."""
        results = {}

        for view_type in ViewType:
            system = SceneMemorySystem()

            extensions = []
            for _ in range(n_per_view):
                scene = system.view_scene(SceneType.LANDSCAPE, view_type)
                memory = system.recall_scene(scene.id, 0)
                if memory:
                    extensions.append(memory.total_extension)

            results[view_type.name] = {
                'mean_extension': sum(extensions) / len(extensions) if extensions else 0
            }

        return results

    def run_normalization_test(
        self
    ) -> Dict[str, Any]:
        """Test boundary normalization hypothesis."""
        system = SceneMemorySystem()

        # View scenes and then compare to "same" and "wider" tests
        scene = system.view_scene(SceneType.LANDSCAPE, ViewType.CLOSE)
        memory = system.recall_scene(scene.id, 5)

        if not memory:
            return {'error': 'No memory formed'}

        # Simulate recognition test
        # "Same" view should be rejected (appears too close)
        # "Wider" view should be accepted (matches extended memory)

        extension = memory.total_extension

        return {
            'original_view': 'CLOSE',
            'extension_amount': extension,
            'same_rejected': extension > 0.2,  # Would reject "same" as too close
            'wider_accepted': extension > 0.1,  # Would accept slightly wider
            'interpretation': 'Subjects reject same view and accept wider view'
        }


# ============================================================================
# BOUNDARY EXTENSION ENGINE
# ============================================================================

class BoundaryExtensionEngine:
    """
    Complete boundary extension engine.

    "Ba'el's perceptual extrapolation." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = BoundaryExtensionParadigm()
        self._system = SceneMemorySystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Scene viewing

    def view_scene(
        self,
        scene_type: SceneType = SceneType.LANDSCAPE,
        view_type: ViewType = ViewType.MEDIUM,
        objects: List[str] = None
    ) -> Scene:
        """View a scene."""
        return self._system.view_scene(scene_type, view_type, objects)

    # Recall

    def recall_scene(
        self,
        scene_id: str,
        delay: float = 0
    ) -> Optional[RememberedScene]:
        """Recall a scene."""
        return self._system.recall_scene(scene_id, delay)

    # Experiments

    def run_extension_experiment(
        self,
        n_scenes: int = 20
    ) -> Dict[str, Any]:
        """Run boundary extension experiment."""
        result = self._paradigm.run_experiment(n_scenes, 5)
        self._experiment_results.append(result)
        return result

    def run_view_comparison(
        self,
        n_per_view: int = 10
    ) -> Dict[str, Any]:
        """Compare extension by view type."""
        return self._paradigm.run_view_comparison(n_per_view)

    def run_normalization_test(
        self
    ) -> Dict[str, Any]:
        """Test normalization hypothesis."""
        return self._paradigm.run_normalization_test()

    def run_delay_effect_test(
        self,
        delays: List[float] = None
    ) -> Dict[str, Any]:
        """Test effect of delay on extension."""
        if delays is None:
            delays = [0, 5, 15, 30]

        results = {}

        for delay in delays:
            system = SceneMemorySystem()

            extensions = []
            for _ in range(10):
                scene = system.view_scene(SceneType.LANDSCAPE, ViewType.CLOSE)
                memory = system.recall_scene(scene.id, delay)
                if memory:
                    extensions.append(memory.total_extension)

            results[f"delay_{delay}min"] = {
                'mean_extension': sum(extensions) / len(extensions) if extensions else 0
            }

        return results

    # Analysis

    def get_metrics(self) -> BoundaryExtensionMetrics:
        """Get boundary extension metrics."""
        if not self._experiment_results:
            self.run_extension_experiment(20)

        last = self._experiment_results[-1]

        return BoundaryExtensionMetrics(
            mean_extension=last['mean_extension'],
            extension_by_view=last['extension_by_view'],
            confidence_correlation=0.0  # Would need correlation calculation
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'scenes': len(self._system._scenes),
            'memories': len(self._system._memories),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_boundary_extension_engine() -> BoundaryExtensionEngine:
    """Create boundary extension engine."""
    return BoundaryExtensionEngine()


def demonstrate_boundary_extension() -> Dict[str, Any]:
    """Demonstrate boundary extension."""
    engine = create_boundary_extension_engine()

    # Basic experiment
    basic = engine.run_extension_experiment(20)

    # View comparison
    views = engine.run_view_comparison(10)

    # Normalization test
    normalization = engine.run_normalization_test()

    # Delay effect
    delay = engine.run_delay_effect_test([0, 10, 30])

    return {
        'boundary_extension': {
            'mean_extension': f"{basic['mean_extension']:.0%}",
            'by_view': basic['extension_by_view']
        },
        'view_comparison': {
            view: f"{data['mean_extension']:.0%}"
            for view, data in views.items()
        },
        'normalization': {
            'extension': f"{normalization.get('extension_amount', 0):.0%}",
            'same_rejected': normalization.get('same_rejected', False)
        },
        'delay_effect': {
            delay: f"{data['mean_extension']:.0%}"
            for delay, data in delay.items()
        },
        'interpretation': (
            f"Mean extension: {basic['mean_extension']:.0%}. "
            f"Close-up views extend more than wide views."
        )
    }


def get_boundary_extension_facts() -> Dict[str, str]:
    """Get facts about boundary extension."""
    return {
        'intraub_richardson_1989': 'Original boundary extension demonstration',
        'perceptual_schema': 'Scene schemas include beyond-view expectations',
        'close_up_effect': 'Close-up views show more extension',
        'normalization': 'Memory normalizes toward canonical view',
        'scene_perception': 'Related to rapid scene understanding',
        'amodal_completion': 'Similar to completing occluded objects',
        'recognition_test': 'Same view rejected, wider view accepted',
        'robustness': 'Effect persists across many conditions'
    }
