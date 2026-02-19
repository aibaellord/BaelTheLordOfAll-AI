"""
BAEL Feature Integration Engine
=================================

Binding features into coherent objects.
Treisman's feature integration theory.

"Ba'el binds all features into one." — Ba'el
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

logger = logging.getLogger("BAEL.FeatureIntegration")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class FeatureDimension(Enum):
    """Feature dimensions."""
    COLOR = auto()
    SHAPE = auto()
    ORIENTATION = auto()
    SIZE = auto()
    MOTION = auto()


class SearchType(Enum):
    """Type of visual search."""
    FEATURE = auto()       # Pop-out search
    CONJUNCTION = auto()   # Serial search
    SPATIAL = auto()       # Location-based


class AttentionMode(Enum):
    """Mode of attention."""
    PREATTENTIVE = auto()  # Parallel, automatic
    FOCUSED = auto()       # Serial, effortful


class BindingState(Enum):
    """State of feature binding."""
    UNBOUND = auto()       # Free-floating features
    BOUND = auto()         # Correctly bound
    MISBOUND = auto()      # Illusory conjunction


@dataclass
class Feature:
    """
    A visual feature.
    """
    dimension: FeatureDimension
    value: str


@dataclass
class VisualObject:
    """
    A visual object with bound features.
    """
    id: str
    features: List[Feature]
    location: Tuple[float, float]
    attended: bool
    binding_state: BindingState


@dataclass
class SearchDisplay:
    """
    A visual search display.
    """
    id: str
    objects: List[VisualObject]
    target: Optional[VisualObject]
    distractors: List[VisualObject]
    set_size: int


@dataclass
class SearchResult:
    """
    Result of visual search.
    """
    display_id: str
    target_present: bool
    target_found: bool
    response_time_ms: float
    illusory_conjunction: bool


@dataclass
class FeatureIntegrationMetrics:
    """
    Feature integration metrics.
    """
    feature_search_slope: float    # ms per item
    conjunction_search_slope: float
    illusory_conjunction_rate: float
    pop_out_threshold: int


# ============================================================================
# FEATURE INTEGRATION MODEL
# ============================================================================

class FeatureIntegrationModel:
    """
    Model of feature integration.

    "Ba'el's binding model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Search parameters
        self._feature_search_slope = 5      # ms per item (pop-out)
        self._conjunction_search_slope = 25  # ms per item (serial)
        self._base_rt = 400                  # Base reaction time

        # Binding parameters
        self._binding_success_attended = 0.98
        self._binding_success_unattended = 0.70

        # Illusory conjunction
        self._ic_rate_unattended = 0.20
        self._ic_rate_crowded = 0.15

        # Capacity
        self._parallel_capacity = 4

        self._lock = threading.RLock()

    def is_pop_out(
        self,
        target: VisualObject,
        distractors: List[VisualObject]
    ) -> bool:
        """Determine if target will pop out."""
        if not distractors:
            return True

        # Check for unique feature
        target_features = {(f.dimension, f.value) for f in target.features}

        for dist in distractors:
            dist_features = {(f.dimension, f.value) for f in dist.features}

            # If any unique dimension value, pop-out possible
            unique = target_features - dist_features
            for dim, val in unique:
                # Check if this dimension differs from all distractors
                all_same = all(
                    any(f.dimension == dim and f.value != val for f in d.features)
                    for d in distractors
                )
                if all_same:
                    return True

        return False

    def calculate_search_time(
        self,
        search_type: SearchType,
        set_size: int,
        target_present: bool
    ) -> float:
        """Calculate visual search time."""
        rt = self._base_rt

        if search_type == SearchType.FEATURE:
            # Parallel search - minimal slope
            rt += set_size * self._feature_search_slope
        else:
            # Serial search
            if target_present:
                # On average, check half the items
                rt += (set_size / 2) * self._conjunction_search_slope
            else:
                # Check all items
                rt += set_size * self._conjunction_search_slope

        # Add noise
        rt += random.gauss(0, 50)

        return max(200, rt)

    def calculate_binding_probability(
        self,
        attended: bool,
        crowded: bool
    ) -> float:
        """Calculate correct binding probability."""
        if attended:
            prob = self._binding_success_attended
        else:
            prob = self._binding_success_unattended

        if crowded:
            prob -= 0.1

        return max(0.3, prob)

    def calculate_ic_probability(
        self,
        attended: bool,
        crowded: bool,
        time_pressure: bool
    ) -> float:
        """Calculate illusory conjunction probability."""
        if attended:
            return 0.02

        prob = self._ic_rate_unattended

        if crowded:
            prob += self._ic_rate_crowded

        if time_pressure:
            prob += 0.1

        return min(0.5, prob)


# ============================================================================
# FEATURE INTEGRATION SYSTEM
# ============================================================================

class FeatureIntegrationSystem:
    """
    Feature integration simulation system.

    "Ba'el's binding system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = FeatureIntegrationModel()

        self._displays: Dict[str, SearchDisplay] = {}
        self._results: List[SearchResult] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_object(
        self,
        color: str,
        shape: str,
        location: Tuple[float, float]
    ) -> VisualObject:
        """Create a visual object."""
        features = [
            Feature(FeatureDimension.COLOR, color),
            Feature(FeatureDimension.SHAPE, shape)
        ]

        return VisualObject(
            id=self._generate_id(),
            features=features,
            location=location,
            attended=False,
            binding_state=BindingState.UNBOUND
        )

    def create_display(
        self,
        target: Optional[VisualObject],
        distractors: List[VisualObject]
    ) -> SearchDisplay:
        """Create a search display."""
        objects = distractors.copy()
        if target:
            objects.append(target)

        display = SearchDisplay(
            id=self._generate_id(),
            objects=objects,
            target=target,
            distractors=distractors,
            set_size=len(objects)
        )

        self._displays[display.id] = display

        return display

    def run_search(
        self,
        display_id: str
    ) -> SearchResult:
        """Run visual search."""
        display = self._displays.get(display_id)
        if not display:
            return None

        target_present = display.target is not None

        # Determine search type
        if target_present:
            pop_out = self._model.is_pop_out(display.target, display.distractors)
            search_type = SearchType.FEATURE if pop_out else SearchType.CONJUNCTION
        else:
            search_type = SearchType.CONJUNCTION

        # Calculate RT
        rt = self._model.calculate_search_time(
            search_type, display.set_size, target_present
        )

        # Determine success
        if target_present:
            if search_type == SearchType.FEATURE:
                target_found = random.random() < 0.98
            else:
                target_found = random.random() < 0.92
        else:
            target_found = False

        # Check for illusory conjunction
        ic_occurred = False
        if search_type == SearchType.CONJUNCTION and not target_found:
            ic_prob = self._model.calculate_ic_probability(
                attended=False,
                crowded=display.set_size > 8,
                time_pressure=False
            )
            ic_occurred = random.random() < ic_prob

        result = SearchResult(
            display_id=display_id,
            target_present=target_present,
            target_found=target_found,
            response_time_ms=rt,
            illusory_conjunction=ic_occurred
        )

        self._results.append(result)

        return result

    def attend_object(
        self,
        obj: VisualObject
    ):
        """Attend to an object (enables correct binding)."""
        obj.attended = True

        # Binding succeeds with attention
        binding_prob = self._model.calculate_binding_probability(
            attended=True, crowded=False
        )

        if random.random() < binding_prob:
            obj.binding_state = BindingState.BOUND
        else:
            obj.binding_state = BindingState.MISBOUND


# ============================================================================
# FEATURE INTEGRATION PARADIGM
# ============================================================================

class FeatureIntegrationParadigm:
    """
    Feature integration paradigm.

    "Ba'el's FIT study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_visual_search_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run visual search paradigm."""
        system = FeatureIntegrationSystem()

        results = {
            'feature_search': defaultdict(list),
            'conjunction_search': defaultdict(list)
        }

        # Feature search (red among green)
        for set_size in [4, 8, 16, 32]:
            for _ in range(20):
                # Target present
                target = system.create_object("red", "circle", (0, 0))
                distractors = [
                    system.create_object("green", "circle", (i, i))
                    for i in range(set_size - 1)
                ]

                display = system.create_display(target, distractors)
                result = system.run_search(display.id)

                results['feature_search'][set_size].append(result.response_time_ms)

        # Conjunction search (red circle among red squares and green circles)
        for set_size in [4, 8, 16, 32]:
            for _ in range(20):
                target = system.create_object("red", "circle", (0, 0))
                distractors = []

                for i in range(set_size - 1):
                    if i % 2 == 0:
                        distractors.append(system.create_object("red", "square", (i, i)))
                    else:
                        distractors.append(system.create_object("green", "circle", (i, i)))

                display = system.create_display(target, distractors)
                result = system.run_search(display.id)

                results['conjunction_search'][set_size].append(result.response_time_ms)

        # Calculate means and slopes
        feature_means = {
            ss: sum(rts) / len(rts)
            for ss, rts in results['feature_search'].items()
        }
        conjunction_means = {
            ss: sum(rts) / len(rts)
            for ss, rts in results['conjunction_search'].items()
        }

        # Estimate slopes
        feature_slope = (feature_means[32] - feature_means[4]) / 28
        conjunction_slope = (conjunction_means[32] - conjunction_means[4]) / 28

        return {
            'feature_search': feature_means,
            'conjunction_search': conjunction_means,
            'feature_slope': feature_slope,
            'conjunction_slope': conjunction_slope,
            'interpretation': 'Feature search parallel, conjunction serial'
        }

    def run_illusory_conjunction_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run illusory conjunction paradigm."""
        system = FeatureIntegrationSystem()

        conditions = {
            'attended': {'n_trials': 30, 'attended': True},
            'unattended': {'n_trials': 30, 'attended': False}
        }

        results = {}

        for condition, params in conditions.items():
            ic_count = 0

            for _ in range(params['n_trials']):
                # Create objects with different features
                obj1 = system.create_object("red", "circle", (0, 0))
                obj2 = system.create_object("green", "square", (1, 1))

                # Binding
                if params['attended']:
                    system.attend_object(obj1)
                    system.attend_object(obj2)
                else:
                    # Unattended - may get IC
                    ic_prob = system._model.calculate_ic_probability(
                        attended=False, crowded=False, time_pressure=False
                    )
                    if random.random() < ic_prob:
                        ic_count += 1

            results[condition] = {
                'ic_rate': ic_count / params['n_trials']
            }

        return {
            'by_attention': results,
            'interpretation': 'Illusory conjunctions more common without attention'
        }

    def run_time_pressure_study(
        self
    ) -> Dict[str, Any]:
        """Study time pressure effects."""
        model = FeatureIntegrationModel()

        conditions = {
            'no_pressure': False,
            'time_pressure': True
        }

        results = {}

        for condition, pressure in conditions.items():
            ic_rate = model.calculate_ic_probability(
                attended=False, crowded=False, time_pressure=pressure
            )

            results[condition] = {
                'ic_rate': ic_rate
            }

        return {
            'by_pressure': results,
            'interpretation': 'Time pressure increases illusory conjunctions'
        }

    def run_crowding_study(
        self
    ) -> Dict[str, Any]:
        """Study crowding effects."""
        model = FeatureIntegrationModel()

        conditions = {
            'sparse': {'crowded': False},
            'crowded': {'crowded': True}
        }

        results = {}

        for condition, params in conditions.items():
            binding_prob = model.calculate_binding_probability(
                attended=False, crowded=params['crowded']
            )

            results[condition] = {
                'correct_binding': binding_prob
            }

        return {
            'by_crowding': results,
            'interpretation': 'Crowding impairs feature binding'
        }

    def run_preattentive_features_study(
        self
    ) -> Dict[str, Any]:
        """Study which features are preattentively processed."""
        preattentive = [
            FeatureDimension.COLOR,
            FeatureDimension.ORIENTATION,
            FeatureDimension.SIZE,
            FeatureDimension.MOTION
        ]

        results = {}

        for dim in preattentive:
            # Feature search with this dimension
            results[dim.name] = {
                'pop_out': True,
                'search_slope': 5 + random.uniform(-2, 2)
            }

        # Conjunctions don't pop out
        results['CONJUNCTION'] = {
            'pop_out': False,
            'search_slope': 25 + random.uniform(-5, 5)
        }

        return {
            'by_dimension': results,
            'interpretation': 'Basic features processed in parallel'
        }

    def run_location_study(
        self
    ) -> Dict[str, Any]:
        """Study role of location in binding."""
        system = FeatureIntegrationSystem()

        # Same location = better binding
        conditions = {
            'same_location': {'distance': 0},
            'different_location': {'distance': 5}
        }

        results = {}

        for condition, params in conditions.items():
            correct = 0
            n_trials = 30

            for _ in range(n_trials):
                obj = system.create_object("red", "circle", (0, 0))

                # Binding accuracy depends on location
                if params['distance'] == 0:
                    correct += 1 if random.random() < 0.95 else 0
                else:
                    correct += 1 if random.random() < 0.80 else 0

            results[condition] = {
                'binding_accuracy': correct / n_trials
            }

        return {
            'by_location': results,
            'interpretation': 'Location is the binding "glue"'
        }


# ============================================================================
# FEATURE INTEGRATION ENGINE
# ============================================================================

class FeatureIntegrationEngine:
    """
    Complete feature integration engine.

    "Ba'el's FIT engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = FeatureIntegrationParadigm()
        self._system = FeatureIntegrationSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Object/display operations

    def create_object(
        self,
        color: str,
        shape: str,
        location: Tuple[float, float]
    ) -> VisualObject:
        """Create object."""
        return self._system.create_object(color, shape, location)

    def create_display(
        self,
        target: Optional[VisualObject],
        distractors: List[VisualObject]
    ) -> SearchDisplay:
        """Create display."""
        return self._system.create_display(target, distractors)

    def search(
        self,
        display_id: str
    ) -> SearchResult:
        """Run search."""
        return self._system.run_search(display_id)

    # Experiments

    def run_visual_search(
        self
    ) -> Dict[str, Any]:
        """Run visual search paradigm."""
        result = self._paradigm.run_visual_search_paradigm()
        self._experiment_results.append(result)
        return result

    def study_illusory_conjunctions(
        self
    ) -> Dict[str, Any]:
        """Study illusory conjunctions."""
        return self._paradigm.run_illusory_conjunction_paradigm()

    def study_time_pressure(
        self
    ) -> Dict[str, Any]:
        """Study time pressure."""
        return self._paradigm.run_time_pressure_study()

    def study_crowding(
        self
    ) -> Dict[str, Any]:
        """Study crowding."""
        return self._paradigm.run_crowding_study()

    def study_preattentive(
        self
    ) -> Dict[str, Any]:
        """Study preattentive features."""
        return self._paradigm.run_preattentive_features_study()

    def study_location(
        self
    ) -> Dict[str, Any]:
        """Study location role."""
        return self._paradigm.run_location_study()

    # Analysis

    def get_metrics(self) -> FeatureIntegrationMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_visual_search()

        last = self._experiment_results[-1]

        return FeatureIntegrationMetrics(
            feature_search_slope=last['feature_slope'],
            conjunction_search_slope=last['conjunction_slope'],
            illusory_conjunction_rate=0.2,
            pop_out_threshold=4
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'displays': len(self._system._displays),
            'searches': len(self._system._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_feature_integration_engine() -> FeatureIntegrationEngine:
    """Create feature integration engine."""
    return FeatureIntegrationEngine()


def demonstrate_feature_integration() -> Dict[str, Any]:
    """Demonstrate feature integration."""
    engine = create_feature_integration_engine()

    # Visual search
    search = engine.run_visual_search()

    # Illusory conjunctions
    ic = engine.study_illusory_conjunctions()

    # Preattentive
    preattentive = engine.study_preattentive()

    # Location
    location = engine.study_location()

    return {
        'search_slopes': {
            'feature': f"{search['feature_slope']:.1f}ms/item",
            'conjunction': f"{search['conjunction_slope']:.1f}ms/item"
        },
        'illusory_conjunctions': {
            k: f"{v['ic_rate']:.0%}"
            for k, v in ic['by_attention'].items()
        },
        'preattentive_features': [
            k for k, v in preattentive['by_dimension'].items()
            if v.get('pop_out', False)
        ],
        'location_binding': {
            k: f"{v['binding_accuracy']:.0%}"
            for k, v in location['by_location'].items()
        },
        'interpretation': (
            f"Feature search: {search['feature_slope']:.1f}ms/item. "
            f"Conjunction search: {search['conjunction_slope']:.1f}ms/item. "
            f"Attention needed for correct binding."
        )
    }


def get_feature_integration_facts() -> Dict[str, str]:
    """Get facts about feature integration."""
    return {
        'treisman_1980': 'Feature integration theory',
        'preattentive': 'Basic features processed in parallel',
        'attention': 'Required to bind features',
        'pop_out': 'Unique features detected automatically',
        'illusory_conjunctions': 'Misbinding without attention',
        'location': 'Spatial location is binding medium',
        'saliency': 'Feature differences guide attention',
        'applications': 'Visual search, interface design, attention'
    }
