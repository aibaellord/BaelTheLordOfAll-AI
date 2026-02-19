"""
BAEL Binding Problem Engine
============================

Treisman's Feature Integration Theory.
Solving the binding problem through attention.

"Ba'el binds features together." — Ba'el
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

logger = logging.getLogger("BAEL.BindingProblem")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class FeatureDimension(Enum):
    """Feature dimensions."""
    COLOR = auto()
    SHAPE = auto()
    SIZE = auto()
    ORIENTATION = auto()
    MOTION = auto()
    TEXTURE = auto()
    LOCATION = auto()
    DEPTH = auto()


class ProcessingStage(Enum):
    """Stages of feature processing."""
    PREATTENTIVE = auto()   # Parallel, automatic
    FOCUSED = auto()        # Serial, attention-requiring
    BOUND = auto()          # Features integrated


class ConjunctionType(Enum):
    """Types of feature conjunctions."""
    SIMPLE = auto()         # Two features
    COMPLEX = auto()        # Multiple features
    SPATIAL = auto()        # Location-bound


@dataclass
class Feature:
    """
    A basic feature.
    """
    id: str
    dimension: FeatureDimension
    value: Any
    salience: float = 0.5
    location: Optional[Tuple[float, float]] = None


@dataclass
class FeatureMap:
    """
    A feature map for one dimension.
    """
    dimension: FeatureDimension
    features: Dict[Tuple[float, float], Feature] = field(default_factory=dict)

    def add(self, feature: Feature, location: Tuple[float, float]) -> None:
        self.features[location] = feature

    def get_at(self, location: Tuple[float, float]) -> Optional[Feature]:
        return self.features.get(location)

    def search(self, value: Any) -> List[Tuple[float, float]]:
        """Find locations with value."""
        return [
            loc for loc, feat in self.features.items()
            if feat.value == value
        ]


@dataclass
class BoundObject:
    """
    An object with bound features.
    """
    id: str
    features: List[Feature]
    location: Tuple[float, float]
    binding_strength: float = 1.0
    timestamp: float = field(default_factory=time.time)

    @property
    def age(self) -> float:
        return time.time() - self.timestamp

    def get_feature(self, dimension: FeatureDimension) -> Optional[Feature]:
        """Get feature for dimension."""
        for f in self.features:
            if f.dimension == dimension:
                return f
        return None

    @property
    def is_bound(self) -> bool:
        return self.binding_strength > 0.5


@dataclass
class SearchResult:
    """
    Result of visual search.
    """
    found: bool
    location: Optional[Tuple[float, float]]
    search_time: float
    items_checked: int
    search_type: str  # 'pop-out' or 'serial'


@dataclass
class BindingError:
    """
    An illusory conjunction (binding error).
    """
    id: str
    perceived: BoundObject
    actual_features: List[Feature]
    error_type: str  # 'conjunction' or 'location'


# ============================================================================
# FEATURE MAPS
# ============================================================================

class FeatureMapSystem:
    """
    System of parallel feature maps.

    "Ba'el's parallel feature analysis." — Ba'el
    """

    def __init__(self):
        """Initialize feature map system."""
        self._maps: Dict[FeatureDimension, FeatureMap] = {}
        for dim in FeatureDimension:
            self._maps[dim] = FeatureMap(dimension=dim)
        self._feature_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._feature_counter += 1
        return f"feature_{self._feature_counter}"

    def register_feature(
        self,
        dimension: FeatureDimension,
        value: Any,
        location: Tuple[float, float],
        salience: float = 0.5
    ) -> Feature:
        """Register feature in map."""
        with self._lock:
            feature = Feature(
                id=self._generate_id(),
                dimension=dimension,
                value=value,
                salience=salience,
                location=location
            )

            self._maps[dimension].add(feature, location)
            return feature

    def get_features_at(
        self,
        location: Tuple[float, float]
    ) -> List[Feature]:
        """Get all features at location."""
        with self._lock:
            features = []
            for fmap in self._maps.values():
                feat = fmap.get_at(location)
                if feat:
                    features.append(feat)
            return features

    def parallel_search(
        self,
        dimension: FeatureDimension,
        value: Any
    ) -> List[Tuple[float, float]]:
        """Parallel (pop-out) search for feature."""
        with self._lock:
            return self._maps[dimension].search(value)

    def clear(self) -> None:
        """Clear all feature maps."""
        with self._lock:
            for dim in FeatureDimension:
                self._maps[dim] = FeatureMap(dimension=dim)

    @property
    def all_locations(self) -> Set[Tuple[float, float]]:
        """Get all locations with features."""
        locations = set()
        for fmap in self._maps.values():
            locations.update(fmap.features.keys())
        return locations


# ============================================================================
# ATTENTION BINDING
# ============================================================================

class AttentionBinder:
    """
    Bind features through attention.

    "Ba'el binds with attention." — Ba'el
    """

    def __init__(
        self,
        binding_strength: float = 0.8,
        binding_time: float = 0.05
    ):
        """Initialize attention binder."""
        self._feature_maps = FeatureMapSystem()
        self._binding_strength = binding_strength
        self._binding_time = binding_time
        self._bound_objects: Dict[str, BoundObject] = {}
        self._object_counter = 0
        self._attention_location: Optional[Tuple[float, float]] = None
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._object_counter += 1
        return f"object_{self._object_counter}"

    def attend(
        self,
        location: Tuple[float, float]
    ) -> Optional[BoundObject]:
        """Attend to location and bind features."""
        with self._lock:
            self._attention_location = location

            # Get features at location
            features = self._feature_maps.get_features_at(location)

            if not features:
                return None

            # Bind features into object
            obj = BoundObject(
                id=self._generate_id(),
                features=features,
                location=location,
                binding_strength=self._binding_strength
            )

            self._bound_objects[obj.id] = obj

            # Simulate binding time
            time.sleep(self._binding_time)

            return obj

    def preattentive_detect(
        self,
        dimension: FeatureDimension,
        value: Any
    ) -> List[Tuple[float, float]]:
        """Preattentive (parallel) detection."""
        return self._feature_maps.parallel_search(dimension, value)

    def create_binding_error(
        self,
        location1: Tuple[float, float],
        location2: Tuple[float, float]
    ) -> Optional[BindingError]:
        """Create illusory conjunction."""
        with self._lock:
            features1 = self._feature_maps.get_features_at(location1)
            features2 = self._feature_maps.get_features_at(location2)

            if not features1 or not features2:
                return None

            # Mix features from both locations
            mixed = []
            for f in features1:
                if random.random() > 0.5:
                    mixed.append(f)
            for f in features2:
                if random.random() > 0.5 and f.dimension not in [m.dimension for m in mixed]:
                    mixed.append(f)

            if not mixed:
                return None

            illusory = BoundObject(
                id=self._generate_id(),
                features=mixed,
                location=location1,  # Mislocalized
                binding_strength=0.3  # Weak binding
            )

            return BindingError(
                id=f"error_{random.randint(1000, 9999)}",
                perceived=illusory,
                actual_features=features1 + features2,
                error_type='conjunction'
            )

    @property
    def feature_maps(self) -> FeatureMapSystem:
        return self._feature_maps

    @property
    def attention_location(self) -> Optional[Tuple[float, float]]:
        return self._attention_location

    @property
    def bound_objects(self) -> List[BoundObject]:
        return list(self._bound_objects.values())


# ============================================================================
# VISUAL SEARCH
# ============================================================================

class VisualSearch:
    """
    Visual search with feature integration.

    "Ba'el searches the visual field." — Ba'el
    """

    def __init__(self):
        """Initialize visual search."""
        self._binder = AttentionBinder()
        self._base_time = 0.02
        self._per_item_time = 0.05
        self._lock = threading.RLock()

    def setup_display(
        self,
        items: List[Dict[str, Any]]
    ) -> None:
        """Set up display with items."""
        with self._lock:
            self._binder.feature_maps.clear()

            for item in items:
                location = item.get('location', (random.random(), random.random()))

                for dim_name, value in item.items():
                    if dim_name == 'location':
                        continue

                    try:
                        dim = FeatureDimension[dim_name.upper()]
                        self._binder.feature_maps.register_feature(
                            dim, value, location
                        )
                    except KeyError:
                        pass

    def feature_search(
        self,
        target_dimension: FeatureDimension,
        target_value: Any
    ) -> SearchResult:
        """Feature search (pop-out)."""
        with self._lock:
            start_time = time.time()

            locations = self._binder.preattentive_detect(
                target_dimension, target_value
            )

            elapsed = time.time() - start_time + self._base_time

            if locations:
                return SearchResult(
                    found=True,
                    location=locations[0],
                    search_time=elapsed,
                    items_checked=1,  # Parallel = constant time
                    search_type='pop-out'
                )
            else:
                return SearchResult(
                    found=False,
                    location=None,
                    search_time=elapsed,
                    items_checked=1,
                    search_type='pop-out'
                )

    def conjunction_search(
        self,
        target_features: Dict[FeatureDimension, Any]
    ) -> SearchResult:
        """Conjunction search (serial)."""
        with self._lock:
            start_time = time.time()
            items_checked = 0

            all_locations = self._binder.feature_maps.all_locations

            for location in all_locations:
                items_checked += 1

                # Bind and check
                obj = self._binder.attend(location)

                if obj:
                    matches = True
                    for dim, value in target_features.items():
                        feat = obj.get_feature(dim)
                        if not feat or feat.value != value:
                            matches = False
                            break

                    if matches:
                        elapsed = time.time() - start_time
                        elapsed += items_checked * self._per_item_time

                        return SearchResult(
                            found=True,
                            location=location,
                            search_time=elapsed,
                            items_checked=items_checked,
                            search_type='serial'
                        )

            elapsed = time.time() - start_time
            elapsed += items_checked * self._per_item_time

            return SearchResult(
                found=False,
                location=None,
                search_time=elapsed,
                items_checked=items_checked,
                search_type='serial'
            )

    @property
    def binder(self) -> AttentionBinder:
        return self._binder


# ============================================================================
# BINDING PROBLEM ENGINE
# ============================================================================

class BindingProblemEngine:
    """
    Complete Feature Integration Theory engine.

    "Ba'el solves binding." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._search = VisualSearch()
        self._binding_errors: List[BindingError] = []
        self._search_history: List[SearchResult] = []
        self._lock = threading.RLock()

    # Setup

    def create_display(
        self,
        items: List[Dict[str, Any]]
    ) -> None:
        """Create visual display."""
        self._search.setup_display(items)

    # Feature registration

    def register_feature(
        self,
        dimension: FeatureDimension,
        value: Any,
        location: Tuple[float, float]
    ) -> Feature:
        """Register feature in display."""
        return self._search.binder.feature_maps.register_feature(
            dimension, value, location
        )

    # Search

    def pop_out_search(
        self,
        dimension: FeatureDimension,
        value: Any
    ) -> SearchResult:
        """Pop-out (feature) search."""
        result = self._search.feature_search(dimension, value)
        self._search_history.append(result)
        return result

    def serial_search(
        self,
        target: Dict[FeatureDimension, Any]
    ) -> SearchResult:
        """Serial (conjunction) search."""
        result = self._search.conjunction_search(target)
        self._search_history.append(result)
        return result

    def search(
        self,
        target: Dict[FeatureDimension, Any]
    ) -> SearchResult:
        """Automatic search - feature or conjunction."""
        if len(target) == 1:
            dim, value = list(target.items())[0]
            return self.pop_out_search(dim, value)
        else:
            return self.serial_search(target)

    # Binding

    def bind_at(
        self,
        location: Tuple[float, float]
    ) -> Optional[BoundObject]:
        """Bind features at location."""
        return self._search.binder.attend(location)

    def create_illusory_conjunction(
        self,
        loc1: Tuple[float, float],
        loc2: Tuple[float, float]
    ) -> Optional[BindingError]:
        """Create illusory conjunction."""
        error = self._search.binder.create_binding_error(loc1, loc2)
        if error:
            self._binding_errors.append(error)
        return error

    # Analysis

    def search_slope(self) -> Dict[str, float]:
        """Calculate search slopes."""
        if len(self._search_history) < 2:
            return {'feature': 0.0, 'conjunction': 0.0}

        feature_results = [r for r in self._search_history if r.search_type == 'pop-out']
        conj_results = [r for r in self._search_history if r.search_type == 'serial']

        feature_slope = 0.0
        if feature_results:
            # Should be ~0 (flat)
            times = [r.search_time for r in feature_results]
            feature_slope = sum(times) / len(times)

        conj_slope = 0.0
        if conj_results:
            # Should be positive (serial)
            total_time = sum(r.search_time for r in conj_results)
            total_items = sum(r.items_checked for r in conj_results)
            if total_items > 0:
                conj_slope = total_time / total_items

        return {
            'feature': feature_slope,
            'conjunction': conj_slope
        }

    @property
    def binding_errors(self) -> List[BindingError]:
        return self._binding_errors

    @property
    def bound_objects(self) -> List[BoundObject]:
        return self._search.binder.bound_objects

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'bound_objects': len(self._search.binder.bound_objects),
            'binding_errors': len(self._binding_errors),
            'searches': len(self._search_history),
            'locations': len(self._search.binder.feature_maps.all_locations)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_binding_engine() -> BindingProblemEngine:
    """Create binding problem engine."""
    return BindingProblemEngine()


def demonstrate_pop_out():
    """Demonstrate pop-out effect."""
    engine = create_binding_engine()

    # Create display with distractors
    items = []
    for i in range(20):
        items.append({
            'color': 'blue',
            'shape': 'circle',
            'location': (random.random(), random.random())
        })

    # Add target (red among blue)
    items.append({
        'color': 'red',
        'shape': 'circle',
        'location': (0.5, 0.5)
    })

    engine.create_display(items)
    result = engine.pop_out_search(FeatureDimension.COLOR, 'red')

    return result
