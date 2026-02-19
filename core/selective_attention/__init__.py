"""
BAEL Selective Attention Engine
=================================

Visual search and feature integration.
Treisman's FIT and guided search.

"Ba'el focuses selectively." — Ba'el
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

logger = logging.getLogger("BAEL.SelectiveAttention")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class FeatureType(Enum):
    """Types of visual features."""
    COLOR = auto()
    ORIENTATION = auto()
    SIZE = auto()
    SHAPE = auto()
    MOTION = auto()
    DEPTH = auto()


class SearchType(Enum):
    """Types of visual search."""
    FEATURE = auto()       # Single feature pop-out
    CONJUNCTION = auto()   # Multiple features
    SERIAL = auto()        # Item-by-item
    PARALLEL = auto()      # All at once


class AttentionMode(Enum):
    """Modes of attention."""
    DIFFUSE = auto()       # Broad, parallel
    FOCUSED = auto()        # Narrow, serial


@dataclass
class VisualFeature:
    """
    A visual feature.
    """
    feature_type: FeatureType
    value: str  # e.g., "red", "vertical"


@dataclass
class VisualObject:
    """
    A visual object with features.
    """
    id: str
    features: List[VisualFeature]
    position: Tuple[float, float]
    is_target: bool


@dataclass
class SearchDisplay:
    """
    A visual search display.
    """
    objects: List[VisualObject]
    target_present: bool
    set_size: int
    target_features: List[VisualFeature]


@dataclass
class SearchResult:
    """
    Result of a visual search.
    """
    target_found: bool
    reaction_time: float
    items_searched: int
    search_type: SearchType
    correct: bool


@dataclass
class FeatureMap:
    """
    A feature map from early vision.
    """
    feature_type: FeatureType
    activations: Dict[str, List[str]]  # value -> [object_ids]


@dataclass
class SalienceMap:
    """
    Combined salience map.
    """
    saliences: Dict[str, float]  # object_id -> salience


@dataclass
class SelectiveAttentionMetrics:
    """
    Selective attention metrics.
    """
    feature_search_slope: float
    conjunction_search_slope: float
    pop_out_effect: bool
    accuracy: float


# ============================================================================
# FEATURE INTEGRATION THEORY
# ============================================================================

class FeatureMapProcessor:
    """
    Processes features into feature maps.

    "Ba'el's parallel feature detection." — Ba'el
    """

    def __init__(self):
        """Initialize processor."""
        self._lock = threading.RLock()

    def create_feature_maps(
        self,
        objects: List[VisualObject]
    ) -> Dict[FeatureType, FeatureMap]:
        """Create feature maps for all feature types."""
        maps = {}

        for feature_type in FeatureType:
            activations = defaultdict(list)

            for obj in objects:
                for feature in obj.features:
                    if feature.feature_type == feature_type:
                        activations[feature.value].append(obj.id)

            maps[feature_type] = FeatureMap(
                feature_type=feature_type,
                activations=dict(activations)
            )

        return maps

    def find_unique_feature(
        self,
        feature_maps: Dict[FeatureType, FeatureMap],
        target_features: List[VisualFeature],
        all_objects: List[VisualObject]
    ) -> Optional[str]:
        """Find object with unique feature (pop-out)."""
        for target_feature in target_features:
            feature_map = feature_maps.get(target_feature.feature_type)
            if not feature_map:
                continue

            # Check if target feature value is unique
            matching_ids = feature_map.activations.get(target_feature.value, [])

            if len(matching_ids) == 1:
                # Unique feature - pop-out!
                return matching_ids[0]

        return None


class SalienceCalculator:
    """
    Calculates salience based on features.

    "Ba'el's attention guidance." — Ba'el
    """

    def __init__(self):
        """Initialize calculator."""
        self._feature_weights: Dict[FeatureType, float] = {
            FeatureType.COLOR: 1.0,
            FeatureType.ORIENTATION: 0.9,
            FeatureType.SIZE: 0.8,
            FeatureType.SHAPE: 0.7,
            FeatureType.MOTION: 1.2,
            FeatureType.DEPTH: 0.6
        }

        self._lock = threading.RLock()

    def calculate_salience(
        self,
        objects: List[VisualObject],
        target_features: List[VisualFeature],
        feature_maps: Dict[FeatureType, FeatureMap]
    ) -> SalienceMap:
        """Calculate salience map."""
        saliences = {}

        for obj in objects:
            salience = 0.0

            for feature in obj.features:
                # Base salience from feature type
                weight = self._feature_weights.get(feature.feature_type, 0.5)

                # Boost if matches target feature
                for target_feature in target_features:
                    if (feature.feature_type == target_feature.feature_type and
                        feature.value == target_feature.value):
                        weight *= 2.0

                # Uniqueness bonus
                feature_map = feature_maps.get(feature.feature_type)
                if feature_map:
                    n_with_feature = len(feature_map.activations.get(feature.value, []))
                    if n_with_feature == 1:
                        weight *= 3.0  # Unique feature bonus
                    elif n_with_feature <= 3:
                        weight *= 1.5  # Rare feature bonus

                salience += weight

            saliences[obj.id] = salience

        return SalienceMap(saliences=saliences)


class FeatureIntegrationTheory:
    """
    Treisman's Feature Integration Theory.

    "Ba'el's attention spotlight." — Ba'el
    """

    def __init__(self):
        """Initialize FIT."""
        self._map_processor = FeatureMapProcessor()
        self._salience_calc = SalienceCalculator()

        # Timing parameters
        self._parallel_time = 50  # ms for parallel processing
        self._serial_time_per_item = 25  # ms per item for serial

        self._lock = threading.RLock()

    def search(
        self,
        display: SearchDisplay
    ) -> SearchResult:
        """Perform visual search."""
        start_time = time.time()

        # Stage 1: Create feature maps (parallel)
        feature_maps = self._map_processor.create_feature_maps(display.objects)

        # Stage 2: Check for pop-out (parallel)
        pop_out_target = self._map_processor.find_unique_feature(
            feature_maps, display.target_features, display.objects
        )

        if pop_out_target:
            # Feature search - parallel, fast
            obj = next((o for o in display.objects if o.id == pop_out_target), None)

            rt = self._parallel_time + random.gauss(0, 10)

            return SearchResult(
                target_found=obj.is_target if obj else False,
                reaction_time=rt,
                items_searched=1,
                search_type=SearchType.FEATURE,
                correct=True
            )

        # Stage 3: Calculate salience map
        salience_map = self._salience_calc.calculate_salience(
            display.objects, display.target_features, feature_maps
        )

        # Stage 4: Serial search (guided by salience)
        sorted_objects = sorted(
            display.objects,
            key=lambda o: salience_map.saliences.get(o.id, 0),
            reverse=True
        )

        items_searched = 0
        target_found = False

        for obj in sorted_objects:
            items_searched += 1

            # Check if this object has all target features
            obj_feature_values = {
                (f.feature_type, f.value) for f in obj.features
            }
            target_feature_values = {
                (f.feature_type, f.value) for f in display.target_features
            }

            if target_feature_values.issubset(obj_feature_values):
                target_found = True
                break

        # If target present, we should find it; if not, search all
        if display.target_present and not target_found:
            items_searched = len(display.objects)  # Keep searching

        # Calculate RT
        rt = self._parallel_time + items_searched * self._serial_time_per_item
        rt += random.gauss(0, 10)

        # Determine search type
        if len(display.target_features) > 1:
            search_type = SearchType.CONJUNCTION
        else:
            search_type = SearchType.SERIAL

        # Accuracy
        correct = (target_found == display.target_present)

        return SearchResult(
            target_found=target_found,
            reaction_time=rt,
            items_searched=items_searched,
            search_type=search_type,
            correct=correct
        )


# ============================================================================
# SEARCH DISPLAY GENERATOR
# ============================================================================

class SearchDisplayGenerator:
    """
    Generates visual search displays.

    "Ba'el creates search arrays." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._object_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._object_counter += 1
        return f"obj_{self._object_counter}"

    def generate_feature_search_display(
        self,
        set_size: int,
        target_present: bool = True
    ) -> SearchDisplay:
        """Generate feature search display (single distinguishing feature)."""
        objects = []

        # Target: red vertical
        target_features = [
            VisualFeature(FeatureType.COLOR, "red")
        ]

        # Add target if present
        if target_present:
            target = VisualObject(
                id=self._generate_id(),
                features=[
                    VisualFeature(FeatureType.COLOR, "red"),
                    VisualFeature(FeatureType.ORIENTATION, "vertical")
                ],
                position=(random.random(), random.random()),
                is_target=True
            )
            objects.append(target)
            set_size -= 1

        # Add distractors (all blue vertical)
        for _ in range(set_size):
            distractor = VisualObject(
                id=self._generate_id(),
                features=[
                    VisualFeature(FeatureType.COLOR, "blue"),
                    VisualFeature(FeatureType.ORIENTATION, "vertical")
                ],
                position=(random.random(), random.random()),
                is_target=False
            )
            objects.append(distractor)

        return SearchDisplay(
            objects=objects,
            target_present=target_present,
            set_size=len(objects),
            target_features=target_features
        )

    def generate_conjunction_search_display(
        self,
        set_size: int,
        target_present: bool = True
    ) -> SearchDisplay:
        """Generate conjunction search display (requires multiple features)."""
        objects = []

        # Target: red vertical
        target_features = [
            VisualFeature(FeatureType.COLOR, "red"),
            VisualFeature(FeatureType.ORIENTATION, "vertical")
        ]

        # Add target if present
        if target_present:
            target = VisualObject(
                id=self._generate_id(),
                features=[
                    VisualFeature(FeatureType.COLOR, "red"),
                    VisualFeature(FeatureType.ORIENTATION, "vertical")
                ],
                position=(random.random(), random.random()),
                is_target=True
            )
            objects.append(target)
            set_size -= 1

        # Add distractors (red horizontal OR blue vertical)
        for i in range(set_size):
            if i % 2 == 0:
                # Red horizontal
                distractor = VisualObject(
                    id=self._generate_id(),
                    features=[
                        VisualFeature(FeatureType.COLOR, "red"),
                        VisualFeature(FeatureType.ORIENTATION, "horizontal")
                    ],
                    position=(random.random(), random.random()),
                    is_target=False
                )
            else:
                # Blue vertical
                distractor = VisualObject(
                    id=self._generate_id(),
                    features=[
                        VisualFeature(FeatureType.COLOR, "blue"),
                        VisualFeature(FeatureType.ORIENTATION, "vertical")
                    ],
                    position=(random.random(), random.random()),
                    is_target=False
                )
            objects.append(distractor)

        return SearchDisplay(
            objects=objects,
            target_present=target_present,
            set_size=len(objects),
            target_features=target_features
        )


# ============================================================================
# SELECTIVE ATTENTION ENGINE
# ============================================================================

class SelectiveAttentionEngine:
    """
    Complete selective attention engine.

    "Ba'el's visual attention." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._fit = FeatureIntegrationTheory()
        self._generator = SearchDisplayGenerator()

        self._search_history: List[SearchResult] = []

        self._lock = threading.RLock()

    # Search operations

    def feature_search(
        self,
        set_size: int = 20,
        target_present: bool = True
    ) -> SearchResult:
        """Perform feature search."""
        display = self._generator.generate_feature_search_display(set_size, target_present)
        result = self._fit.search(display)
        self._search_history.append(result)
        return result

    def conjunction_search(
        self,
        set_size: int = 20,
        target_present: bool = True
    ) -> SearchResult:
        """Perform conjunction search."""
        display = self._generator.generate_conjunction_search_display(set_size, target_present)
        result = self._fit.search(display)
        self._search_history.append(result)
        return result

    def custom_search(
        self,
        display: SearchDisplay
    ) -> SearchResult:
        """Perform search on custom display."""
        result = self._fit.search(display)
        self._search_history.append(result)
        return result

    # Experiments

    def run_set_size_experiment(
        self,
        search_type: str = "feature",
        set_sizes: List[int] = None,
        trials_per_condition: int = 10
    ) -> Dict[str, Any]:
        """Run set size manipulation experiment."""
        if set_sizes is None:
            set_sizes = [5, 10, 15, 20, 25]

        results = {}

        for size in set_sizes:
            rts = []
            accuracies = []

            for _ in range(trials_per_condition):
                if search_type == "feature":
                    result = self.feature_search(size, target_present=True)
                else:
                    result = self.conjunction_search(size, target_present=True)

                rts.append(result.reaction_time)
                accuracies.append(1 if result.correct else 0)

            results[size] = {
                'mean_rt': sum(rts) / len(rts),
                'accuracy': sum(accuracies) / len(accuracies)
            }

        # Calculate search slope
        sizes = list(results.keys())
        rts = [results[s]['mean_rt'] for s in sizes]

        if len(sizes) > 1:
            slope = (rts[-1] - rts[0]) / (sizes[-1] - sizes[0])
        else:
            slope = 0

        return {
            'search_type': search_type,
            'results_by_set_size': results,
            'slope_ms_per_item': slope,
            'pop_out': slope < 5  # Less than 5ms/item indicates pop-out
        }

    def compare_search_types(
        self,
        set_sizes: List[int] = None,
        trials_per_condition: int = 10
    ) -> Dict[str, Any]:
        """Compare feature vs conjunction search."""
        feature_exp = self.run_set_size_experiment("feature", set_sizes, trials_per_condition)
        conjunction_exp = self.run_set_size_experiment("conjunction", set_sizes, trials_per_condition)

        return {
            'feature_search': {
                'slope': feature_exp['slope_ms_per_item'],
                'pop_out': feature_exp['pop_out']
            },
            'conjunction_search': {
                'slope': conjunction_exp['slope_ms_per_item'],
                'pop_out': conjunction_exp['pop_out']
            },
            'serial_vs_parallel': {
                'feature_is_parallel': feature_exp['slope_ms_per_item'] < 10,
                'conjunction_is_serial': conjunction_exp['slope_ms_per_item'] > 15
            }
        }

    # Analysis

    def get_metrics(self) -> SelectiveAttentionMetrics:
        """Get selective attention metrics."""
        feature_searches = [r for r in self._search_history if r.search_type == SearchType.FEATURE]
        conjunction_searches = [r for r in self._search_history if r.search_type == SearchType.CONJUNCTION]

        if feature_searches:
            avg_feature_rt = sum(r.reaction_time for r in feature_searches) / len(feature_searches)
            avg_feature_items = sum(r.items_searched for r in feature_searches) / len(feature_searches)
            feature_slope = avg_feature_rt / avg_feature_items if avg_feature_items > 0 else 0
        else:
            feature_slope = 0

        if conjunction_searches:
            avg_conj_rt = sum(r.reaction_time for r in conjunction_searches) / len(conjunction_searches)
            avg_conj_items = sum(r.items_searched for r in conjunction_searches) / len(conjunction_searches)
            conjunction_slope = avg_conj_rt / avg_conj_items if avg_conj_items > 0 else 0
        else:
            conjunction_slope = 0

        all_searches = self._search_history
        accuracy = sum(1 for r in all_searches if r.correct) / len(all_searches) if all_searches else 0

        return SelectiveAttentionMetrics(
            feature_search_slope=feature_slope,
            conjunction_search_slope=conjunction_slope,
            pop_out_effect=feature_slope < 10,
            accuracy=accuracy
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'total_searches': len(self._search_history),
            'feature_searches': sum(1 for r in self._search_history if r.search_type == SearchType.FEATURE),
            'conjunction_searches': sum(1 for r in self._search_history if r.search_type == SearchType.CONJUNCTION)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_selective_attention_engine() -> SelectiveAttentionEngine:
    """Create selective attention engine."""
    return SelectiveAttentionEngine()


def demonstrate_selective_attention() -> Dict[str, Any]:
    """Demonstrate selective attention."""
    engine = create_selective_attention_engine()

    # Compare feature and conjunction search
    comparison = engine.compare_search_types(
        set_sizes=[5, 10, 15, 20],
        trials_per_condition=5
    )

    # Get metrics
    metrics = engine.get_metrics()

    return {
        'feature_search_slope': f"{comparison['feature_search']['slope']:.1f} ms/item",
        'conjunction_search_slope': f"{comparison['conjunction_search']['slope']:.1f} ms/item",
        'feature_pop_out': comparison['feature_search']['pop_out'],
        'conjunction_serial': comparison['serial_vs_parallel']['conjunction_is_serial'],
        'accuracy': f"{metrics.accuracy:.0%}",
        'interpretation': (
            f"Feature search is parallel (pop-out: {comparison['feature_search']['pop_out']}). "
            f"Conjunction search is serial (slope: {comparison['conjunction_search']['slope']:.1f} ms/item)."
        )
    }


def get_selective_attention_facts() -> Dict[str, str]:
    """Get facts about selective attention."""
    return {
        'treisman_fit': 'Feature Integration Theory: features processed parallel, binding requires attention',
        'pop_out': 'Unique features are detected in parallel regardless of set size',
        'conjunction_search': 'Combining features requires serial attention',
        'search_slope': 'RT increase per item indicates search efficiency',
        'feature_maps': 'Early vision creates maps for different feature dimensions',
        'salience_map': 'Combined map guides attention',
        'guided_search': "Wolfe's extension: top-down guidance affects salience",
        'illusory_conjunctions': 'Incorrect feature binding when attention is overloaded'
    }
