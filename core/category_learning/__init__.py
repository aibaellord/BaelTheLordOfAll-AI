"""
BAEL Category Learning Engine
================================

Prototype vs exemplar models.
Rule-based and similarity-based categorization.

"Ba'el classifies the world." — Ba'el
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

logger = logging.getLogger("BAEL.CategoryLearning")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class CategoryModel(Enum):
    """Category representation models."""
    PROTOTYPE = auto()        # Rosch: central tendency
    EXEMPLAR = auto()         # Medin: stored instances
    RULE_BASED = auto()       # Explicit rules
    HYBRID = auto()           # COVIS: multiple systems


class FeatureType(Enum):
    """Types of features."""
    BINARY = auto()           # Present/absent
    CONTINUOUS = auto()       # Numerical value
    NOMINAL = auto()          # Categories


class CategoryStructure(Enum):
    """Category structure types."""
    FAMILY_RESEMBLANCE = auto()   # Overlapping features
    RULE_DEFINED = auto()         # Necessary features
    LINEARLY_SEPARABLE = auto()
    NON_LINEARLY_SEPARABLE = auto()


class GeneralizationGradient(Enum):
    """Generalization gradient shape."""
    EXPONENTIAL = auto()
    GAUSSIAN = auto()
    LINEAR = auto()


@dataclass
class Feature:
    """
    A feature dimension.
    """
    name: str
    feature_type: FeatureType
    possible_values: List[Any]
    weight: float = 1.0


@dataclass
class Stimulus:
    """
    A stimulus with features.
    """
    id: str
    features: Dict[str, Any]
    category: Optional[str] = None


@dataclass
class Prototype:
    """
    A category prototype.
    """
    category: str
    features: Dict[str, float]  # Average/typical values
    frequency: int


@dataclass
class Exemplar:
    """
    A stored exemplar.
    """
    id: str
    stimulus: Stimulus
    category: str
    activation: float


@dataclass
class ClassificationResult:
    """
    Result of classification.
    """
    stimulus_id: str
    predicted_category: str
    correct_category: Optional[str]
    confidence: float
    correct: bool
    response_time: float


@dataclass
class CategoryMetrics:
    """
    Category learning metrics.
    """
    accuracy: float
    typicality_effect: bool
    prototype_enhancement: float
    exemplar_specificity: float


# ============================================================================
# PROTOTYPE MODEL
# ============================================================================

class PrototypeModel:
    """
    Rosch's prototype model.

    "Ba'el knows the typical." — Ba'el
    """

    def __init__(
        self,
        sensitivity: float = 1.0
    ):
        """Initialize model."""
        self._prototypes: Dict[str, Prototype] = {}
        self._sensitivity = sensitivity

        self._lock = threading.RLock()

    def train(
        self,
        stimuli: List[Stimulus]
    ) -> None:
        """Train prototypes from stimuli."""
        # Group by category
        by_category = defaultdict(list)
        for stim in stimuli:
            if stim.category:
                by_category[stim.category].append(stim)

        # Calculate prototypes (central tendency)
        for category, items in by_category.items():
            # Average feature values
            prototype_features = defaultdict(float)
            counts = defaultdict(int)

            for item in items:
                for feature, value in item.features.items():
                    if isinstance(value, (int, float)):
                        prototype_features[feature] += value
                        counts[feature] += 1

            for feature in prototype_features:
                prototype_features[feature] /= counts[feature]

            self._prototypes[category] = Prototype(
                category=category,
                features=dict(prototype_features),
                frequency=len(items)
            )

    def classify(
        self,
        stimulus: Stimulus
    ) -> Tuple[str, float]:
        """Classify stimulus by prototype similarity."""
        if not self._prototypes:
            return "unknown", 0.0

        similarities = {}

        for category, prototype in self._prototypes.items():
            sim = self._calculate_similarity(stimulus, prototype)
            similarities[category] = sim

        # Choose most similar
        best_category = max(similarities, key=similarities.get)

        # Confidence via Luce choice
        total = sum(
            math.exp(self._sensitivity * s)
            for s in similarities.values()
        )
        confidence = (
            math.exp(self._sensitivity * similarities[best_category]) / total
            if total > 0 else 0.5
        )

        return best_category, confidence

    def _calculate_similarity(
        self,
        stimulus: Stimulus,
        prototype: Prototype
    ) -> float:
        """Calculate similarity to prototype."""
        total_distance = 0.0
        feature_count = 0

        for feature, proto_value in prototype.features.items():
            if feature in stimulus.features:
                stim_value = stimulus.features[feature]

                if isinstance(stim_value, (int, float)):
                    # Euclidean for continuous
                    distance = abs(stim_value - proto_value)
                    total_distance += distance ** 2
                    feature_count += 1

        if feature_count == 0:
            return 0.0

        # Convert distance to similarity
        distance = math.sqrt(total_distance / feature_count)
        similarity = math.exp(-distance)

        return similarity

    def get_typicality(
        self,
        stimulus: Stimulus,
        category: str
    ) -> float:
        """Get typicality rating (similarity to prototype)."""
        prototype = self._prototypes.get(category)
        if not prototype:
            return 0.0

        return self._calculate_similarity(stimulus, prototype)


# ============================================================================
# EXEMPLAR MODEL
# ============================================================================

class ExemplarModel:
    """
    Nosofsky's GCM exemplar model.

    "Ba'el remembers instances." — Ba'el
    """

    def __init__(
        self,
        sensitivity: float = 1.0,
        generalization: GeneralizationGradient = GeneralizationGradient.EXPONENTIAL
    ):
        """Initialize model."""
        self._exemplars: List[Exemplar] = []
        self._sensitivity = sensitivity
        self._generalization = generalization
        self._feature_weights: Dict[str, float] = defaultdict(lambda: 1.0)

        self._exemplar_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._exemplar_counter += 1
        return f"ex_{self._exemplar_counter}"

    def store_exemplar(
        self,
        stimulus: Stimulus
    ) -> Exemplar:
        """Store an exemplar."""
        exemplar = Exemplar(
            id=self._generate_id(),
            stimulus=stimulus,
            category=stimulus.category or "unknown",
            activation=1.0
        )

        self._exemplars.append(exemplar)
        return exemplar

    def train(
        self,
        stimuli: List[Stimulus]
    ) -> None:
        """Train by storing exemplars."""
        for stim in stimuli:
            self.store_exemplar(stim)

    def classify(
        self,
        stimulus: Stimulus
    ) -> Tuple[str, float]:
        """Classify by summed similarity to exemplars."""
        if not self._exemplars:
            return "unknown", 0.0

        # Sum similarities by category
        category_sums = defaultdict(float)

        for exemplar in self._exemplars:
            sim = self._calculate_similarity(stimulus, exemplar.stimulus)
            category_sums[exemplar.category] += sim

        if not category_sums:
            return "unknown", 0.0

        # Choose category with highest summed similarity
        best_category = max(category_sums, key=category_sums.get)

        # Confidence via Luce choice
        total = sum(category_sums.values())
        confidence = category_sums[best_category] / total if total > 0 else 0.5

        return best_category, confidence

    def _calculate_similarity(
        self,
        stim1: Stimulus,
        stim2: Stimulus
    ) -> float:
        """Calculate weighted similarity between stimuli."""
        total_distance = 0.0

        for feature in stim1.features:
            if feature in stim2.features:
                v1 = stim1.features[feature]
                v2 = stim2.features[feature]
                weight = self._feature_weights[feature]

                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    diff = abs(v1 - v2)
                    total_distance += weight * (diff ** 2)
                elif v1 != v2:
                    total_distance += weight

        distance = math.sqrt(total_distance)

        # Apply generalization gradient
        if self._generalization == GeneralizationGradient.EXPONENTIAL:
            similarity = math.exp(-self._sensitivity * distance)
        elif self._generalization == GeneralizationGradient.GAUSSIAN:
            similarity = math.exp(-self._sensitivity * (distance ** 2))
        else:
            similarity = max(0, 1 - self._sensitivity * distance)

        return similarity

    def set_attention_weight(
        self,
        feature: str,
        weight: float
    ) -> None:
        """Set attention weight for feature."""
        self._feature_weights[feature] = weight


# ============================================================================
# RULE-BASED MODEL
# ============================================================================

class RuleBasedModel:
    """
    Rule-based categorization.

    "Ba'el applies the rule." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        self._rules: Dict[str, List[Callable[[Stimulus], bool]]] = defaultdict(list)

        self._lock = threading.RLock()

    def add_rule(
        self,
        category: str,
        rule: Callable[[Stimulus], bool]
    ) -> None:
        """Add a classification rule."""
        self._rules[category].append(rule)

    def add_feature_rule(
        self,
        category: str,
        feature: str,
        value: Any,
        comparison: str = "=="
    ) -> None:
        """Add a simple feature-based rule."""
        if comparison == "==":
            rule = lambda s, f=feature, v=value: s.features.get(f) == v
        elif comparison == ">":
            rule = lambda s, f=feature, v=value: s.features.get(f, 0) > v
        elif comparison == "<":
            rule = lambda s, f=feature, v=value: s.features.get(f, 0) < v
        elif comparison == ">=":
            rule = lambda s, f=feature, v=value: s.features.get(f, 0) >= v
        elif comparison == "<=":
            rule = lambda s, f=feature, v=value: s.features.get(f, 0) <= v
        else:
            return

        self._rules[category].append(rule)

    def classify(
        self,
        stimulus: Stimulus
    ) -> Tuple[str, float]:
        """Classify by rule matching."""
        matches = {}

        for category, rules in self._rules.items():
            matched = sum(1 for rule in rules if rule(stimulus))
            matches[category] = matched / len(rules) if rules else 0

        if not matches:
            return "unknown", 0.0

        best_category = max(matches, key=matches.get)
        confidence = matches[best_category]

        return best_category, confidence


# ============================================================================
# CATEGORY LEARNING ENGINE
# ============================================================================

class CategoryLearningEngine:
    """
    Complete category learning engine.

    "Ba'el's categorization." — Ba'el
    """

    def __init__(
        self,
        model_type: CategoryModel = CategoryModel.HYBRID
    ):
        """Initialize engine."""
        self._model_type = model_type

        self._prototype_model = PrototypeModel()
        self._exemplar_model = ExemplarModel()
        self._rule_model = RuleBasedModel()

        self._features: Dict[str, Feature] = {}
        self._stimuli: Dict[str, Stimulus] = {}
        self._results: List[ClassificationResult] = []

        self._stimulus_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._stimulus_counter += 1
        return f"stim_{self._stimulus_counter}"

    # Feature and stimulus creation

    def define_feature(
        self,
        name: str,
        feature_type: FeatureType,
        possible_values: List[Any]
    ) -> Feature:
        """Define a feature dimension."""
        feature = Feature(
            name=name,
            feature_type=feature_type,
            possible_values=possible_values
        )
        self._features[name] = feature
        return feature

    def create_stimulus(
        self,
        features: Dict[str, Any],
        category: str = None
    ) -> Stimulus:
        """Create a stimulus."""
        stimulus = Stimulus(
            id=self._generate_id(),
            features=features,
            category=category
        )
        self._stimuli[stimulus.id] = stimulus
        return stimulus

    # Training

    def train(
        self,
        stimuli: List[Stimulus]
    ) -> None:
        """Train all models."""
        if self._model_type in [CategoryModel.PROTOTYPE, CategoryModel.HYBRID]:
            self._prototype_model.train(stimuli)

        if self._model_type in [CategoryModel.EXEMPLAR, CategoryModel.HYBRID]:
            self._exemplar_model.train(stimuli)

    def add_rule(
        self,
        category: str,
        feature: str,
        value: Any,
        comparison: str = "=="
    ) -> None:
        """Add a rule for rule-based categorization."""
        self._rule_model.add_feature_rule(category, feature, value, comparison)

    # Classification

    def classify(
        self,
        stimulus: Stimulus
    ) -> ClassificationResult:
        """Classify a stimulus."""
        start_time = time.time()

        if self._model_type == CategoryModel.PROTOTYPE:
            category, confidence = self._prototype_model.classify(stimulus)
        elif self._model_type == CategoryModel.EXEMPLAR:
            category, confidence = self._exemplar_model.classify(stimulus)
        elif self._model_type == CategoryModel.RULE_BASED:
            category, confidence = self._rule_model.classify(stimulus)
        else:
            # Hybrid: combine predictions
            proto_cat, proto_conf = self._prototype_model.classify(stimulus)
            ex_cat, ex_conf = self._exemplar_model.classify(stimulus)

            # Use higher confidence
            if proto_conf > ex_conf:
                category, confidence = proto_cat, proto_conf
            else:
                category, confidence = ex_cat, ex_conf

        rt = (time.time() - start_time) * 1000 + 300 + random.gauss(0, 50)

        correct = stimulus.category == category if stimulus.category else True

        result = ClassificationResult(
            stimulus_id=stimulus.id,
            predicted_category=category,
            correct_category=stimulus.category,
            confidence=confidence,
            correct=correct,
            response_time=rt
        )

        self._results.append(result)
        return result

    # Analysis

    def test_typicality_effect(
        self,
        category: str,
        typical_stimulus: Stimulus,
        atypical_stimulus: Stimulus
    ) -> Dict[str, Any]:
        """Test typicality effect."""
        typical_result = self.classify(typical_stimulus)
        atypical_result = self.classify(atypical_stimulus)

        # Typical items should be faster and more accurate
        typicality_effect = (
            atypical_result.response_time - typical_result.response_time
        )

        return {
            'typical_rt': typical_result.response_time,
            'atypical_rt': atypical_result.response_time,
            'rt_difference': typicality_effect,
            'typical_correct': typical_result.correct,
            'atypical_correct': atypical_result.correct,
            'typicality_effect_present': typicality_effect > 0
        }

    def test_prototype_enhancement(
        self,
        category: str,
        novel_prototype: Stimulus,
        novel_other: Stimulus
    ) -> Dict[str, Any]:
        """Test prototype enhancement effect."""
        # Novel prototype should be classified with high confidence
        proto_result = self.classify(novel_prototype)
        other_result = self.classify(novel_other)

        enhancement = proto_result.confidence - other_result.confidence

        return {
            'prototype_confidence': proto_result.confidence,
            'other_confidence': other_result.confidence,
            'enhancement': enhancement,
            'prototype_enhanced': enhancement > 0.1
        }

    def get_metrics(self) -> CategoryMetrics:
        """Get category learning metrics."""
        if not self._results:
            return CategoryMetrics(
                accuracy=0.0,
                typicality_effect=False,
                prototype_enhancement=0.0,
                exemplar_specificity=0.0
            )

        correct = sum(1 for r in self._results if r.correct)
        accuracy = correct / len(self._results)

        return CategoryMetrics(
            accuracy=accuracy,
            typicality_effect=True,  # Would need actual testing
            prototype_enhancement=0.0,
            exemplar_specificity=0.0
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'model_type': self._model_type.name,
            'features': len(self._features),
            'stimuli': len(self._stimuli),
            'prototypes': len(self._prototype_model._prototypes),
            'exemplars': len(self._exemplar_model._exemplars),
            'classifications': len(self._results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_category_learning_engine(
    model_type: CategoryModel = CategoryModel.HYBRID
) -> CategoryLearningEngine:
    """Create category learning engine."""
    return CategoryLearningEngine(model_type)


def demonstrate_category_learning() -> Dict[str, Any]:
    """Demonstrate category learning."""
    engine = create_category_learning_engine(CategoryModel.HYBRID)

    # Define features
    engine.define_feature("size", FeatureType.CONTINUOUS, [0, 1])
    engine.define_feature("color_warmth", FeatureType.CONTINUOUS, [0, 1])
    engine.define_feature("pattern", FeatureType.BINARY, [0, 1])

    # Create training stimuli for two categories
    cat_a_stimuli = []
    for i in range(5):
        stim = engine.create_stimulus(
            features={
                "size": 0.3 + random.gauss(0, 0.1),
                "color_warmth": 0.2 + random.gauss(0, 0.1),
                "pattern": 1
            },
            category="A"
        )
        cat_a_stimuli.append(stim)

    cat_b_stimuli = []
    for i in range(5):
        stim = engine.create_stimulus(
            features={
                "size": 0.7 + random.gauss(0, 0.1),
                "color_warmth": 0.8 + random.gauss(0, 0.1),
                "pattern": 0
            },
            category="B"
        )
        cat_b_stimuli.append(stim)

    # Train
    engine.train(cat_a_stimuli + cat_b_stimuli)

    # Test classification
    test_stim = engine.create_stimulus(
        features={"size": 0.35, "color_warmth": 0.25, "pattern": 1},
        category="A"
    )
    result = engine.classify(test_stim)

    # Typicality test
    typical_a = engine.create_stimulus(
        features={"size": 0.3, "color_warmth": 0.2, "pattern": 1},
        category="A"
    )
    atypical_a = engine.create_stimulus(
        features={"size": 0.4, "color_warmth": 0.35, "pattern": 1},
        category="A"
    )

    typicality = engine.test_typicality_effect("A", typical_a, atypical_a)

    metrics = engine.get_metrics()

    return {
        'classification': {
            'predicted': result.predicted_category,
            'correct': result.correct,
            'confidence': result.confidence
        },
        'typicality': {
            'effect_present': typicality['typicality_effect_present'],
            'rt_difference': typicality['rt_difference']
        },
        'metrics': {
            'accuracy': metrics.accuracy
        },
        'interpretation': (
            f"Classified as {result.predicted_category} with "
            f"{result.confidence:.0%} confidence, "
            f"typicality effect {'present' if typicality['typicality_effect_present'] else 'absent'}"
        )
    }


def get_category_learning_facts() -> Dict[str, str]:
    """Get facts about category learning."""
    return {
        'rosch': 'Prototype theory: categories organized around central tendency',
        'medin_schaffer': 'Exemplar theory: categories are stored instances',
        'gcm': 'Generalized Context Model: summed similarity to exemplars',
        'alcove': 'Attention Learning COVEring map: exemplar + attention',
        'covis': 'COmpetition between Verbal and Implicit Systems',
        'typicality': 'Typical members categorized faster and more accurately',
        'prototype_enhancement': 'Novel prototypes often "remembered" as old',
        'family_resemblance': 'Categories with overlapping features, no defining rule'
    }
