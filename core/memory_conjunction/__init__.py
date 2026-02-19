"""
BAEL Memory Conjunction Engine
================================

Recombining features from different memories.
Reinitz's conjunction errors.

"Ba'el weaves threads of memory into new tapestries." — Ba'el
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

logger = logging.getLogger("BAEL.MemoryConjunction")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class FeatureType(Enum):
    """Type of feature."""
    FACE_SHAPE = auto()
    HAIR = auto()
    EYES = auto()
    NOSE = auto()
    MOUTH = auto()
    EXPRESSION = auto()
    ACCESSORY = auto()


class ConjunctionType(Enum):
    """Type of conjunction error."""
    WITHIN_LIST = auto()      # From studied items
    ACROSS_CONTEXT = auto()   # From different contexts
    SEMANTIC = auto()         # Semantically related
    TEMPORAL = auto()         # Temporally close


class TestType(Enum):
    """Type of recognition test."""
    FORCED_CHOICE = auto()
    OLD_NEW = auto()
    SOURCE = auto()


class ErrorType(Enum):
    """Type of memory error."""
    HIT = auto()
    MISS = auto()
    FALSE_ALARM_NEW = auto()
    FALSE_ALARM_CONJUNCTION = auto()
    CORRECT_REJECTION = auto()


@dataclass
class Feature:
    """
    A feature of an item.
    """
    feature_type: FeatureType
    value: str
    source_item: str


@dataclass
class Face:
    """
    A face stimulus.
    """
    id: str
    features: Dict[FeatureType, Feature]
    context: str


@dataclass
class ConjunctionFace:
    """
    A conjunction face (recombined features).
    """
    id: str
    source_faces: List[str]
    features: Dict[FeatureType, Feature]


@dataclass
class RecognitionTrial:
    """
    A recognition trial.
    """
    test_face: Face
    is_old: bool
    is_conjunction: bool
    source_faces: Optional[List[str]]
    response: str
    error_type: ErrorType


@dataclass
class ConjunctionMetrics:
    """
    Conjunction error metrics.
    """
    hit_rate: float
    conjunction_fa: float
    new_fa: float
    discrimination: float


# ============================================================================
# MEMORY CONJUNCTION MODEL
# ============================================================================

class MemoryConjunctionModel:
    """
    Model of memory conjunction errors.

    "Ba'el's feature binding model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base rates
        self._base_hit_rate = 0.75
        self._base_new_fa = 0.15

        # Conjunction false alarm (between old and new)
        self._conjunction_fa = 0.45

        # Feature binding strength
        self._binding_strength = 0.6

        # Number of shared features effect
        self._feature_sharing_effect = 0.08  # Per feature

        # Temporal proximity effect
        self._temporal_effect = 0.10

        # Semantic similarity effect
        self._semantic_effect = 0.08

        # Context reinstatement
        self._context_effect = 0.12

        # Encoding depth
        self._deep_encoding_protection = 0.15

        self._lock = threading.RLock()

    def calculate_feature_overlap(
        self,
        face1: Face,
        face2: Face
    ) -> float:
        """Calculate feature overlap between faces."""
        shared = 0
        total = len(FeatureType)

        for ftype in FeatureType:
            if ftype in face1.features and ftype in face2.features:
                if face1.features[ftype].value == face2.features[ftype].value:
                    shared += 1

        return shared / total

    def calculate_conjunction_strength(
        self,
        conjunction: ConjunctionFace,
        studied_faces: List[Face]
    ) -> float:
        """Calculate strength of conjunction."""
        # How many features match studied faces?
        matched_features = 0

        for ftype, feature in conjunction.features.items():
            for studied in studied_faces:
                if (ftype in studied.features and
                    studied.features[ftype].value == feature.value):
                    matched_features += 1
                    break

        proportion = matched_features / max(1, len(conjunction.features))

        return proportion * self._feature_sharing_effect * len(conjunction.features)

    def calculate_hit_probability(
        self,
        encoding_depth: float = 0.5
    ) -> float:
        """Calculate hit probability."""
        prob = self._base_hit_rate

        # Deep encoding helps
        prob += encoding_depth * self._deep_encoding_protection

        # Add noise
        prob += random.uniform(-0.1, 0.1)

        return max(0.5, min(0.95, prob))

    def calculate_conjunction_fa_probability(
        self,
        n_shared_features: int,
        temporal_proximity: float = 0.5,
        same_context: bool = False
    ) -> float:
        """Calculate conjunction false alarm probability."""
        prob = self._base_new_fa

        # Shared features increase FA
        prob += n_shared_features * self._feature_sharing_effect

        # Temporal proximity
        prob += temporal_proximity * self._temporal_effect

        # Same context
        if same_context:
            prob += self._context_effect

        # Bound by conjunction FA ceiling
        prob = min(prob, self._conjunction_fa + 0.10)

        # Add noise
        prob += random.uniform(-0.1, 0.1)

        return max(0.1, min(0.65, prob))

    def calculate_new_fa_probability(
        self
    ) -> float:
        """Calculate new item false alarm probability."""
        prob = self._base_new_fa
        prob += random.uniform(-0.05, 0.05)
        return max(0.05, min(0.30, prob))


# ============================================================================
# MEMORY CONJUNCTION SYSTEM
# ============================================================================

class MemoryConjunctionSystem:
    """
    Memory conjunction simulation system.

    "Ba'el's conjunction system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = MemoryConjunctionModel()

        self._faces: Dict[str, Face] = {}
        self._conjunctions: Dict[str, ConjunctionFace] = {}
        self._studied: List[str] = []
        self._trials: List[RecognitionTrial] = []

        self._counter = 0
        self._lock = threading.RLock()

        # Feature pools
        self._feature_pools = {
            FeatureType.FACE_SHAPE: ["oval", "round", "square", "heart"],
            FeatureType.HAIR: ["black", "brown", "blonde", "red", "gray"],
            FeatureType.EYES: ["brown", "blue", "green", "hazel"],
            FeatureType.NOSE: ["small", "medium", "large", "pointed"],
            FeatureType.MOUTH: ["thin", "full", "wide", "small"],
            FeatureType.EXPRESSION: ["neutral", "smile", "serious"],
            FeatureType.ACCESSORY: ["none", "glasses", "earrings", "hat"]
        }

    def _generate_id(self) -> str:
        self._counter += 1
        return f"face_{self._counter}"

    def _random_feature(
        self,
        ftype: FeatureType,
        source_id: str
    ) -> Feature:
        """Generate random feature."""
        value = random.choice(self._feature_pools[ftype])
        return Feature(
            feature_type=ftype,
            value=value,
            source_item=source_id
        )

    def create_face(
        self,
        context: str = "default"
    ) -> Face:
        """Create a face with random features."""
        face_id = self._generate_id()

        features = {}
        for ftype in FeatureType:
            features[ftype] = self._random_feature(ftype, face_id)

        face = Face(
            id=face_id,
            features=features,
            context=context
        )

        self._faces[face_id] = face

        return face

    def study_face(
        self,
        face_id: str
    ) -> bool:
        """Study a face."""
        if face_id in self._faces:
            self._studied.append(face_id)
            return True
        return False

    def create_conjunction(
        self,
        source_face_ids: List[str]
    ) -> ConjunctionFace:
        """Create conjunction face from sources."""
        if len(source_face_ids) < 2:
            return None

        source_faces = [self._faces[fid] for fid in source_face_ids if fid in self._faces]
        if len(source_faces) < 2:
            return None

        conj_id = self._generate_id()

        # Randomly combine features from sources
        features = {}
        for ftype in FeatureType:
            source = random.choice(source_faces)
            if ftype in source.features:
                features[ftype] = Feature(
                    feature_type=ftype,
                    value=source.features[ftype].value,
                    source_item=source.id
                )

        conjunction = ConjunctionFace(
            id=conj_id,
            source_faces=source_face_ids,
            features=features
        )

        self._conjunctions[conj_id] = conjunction

        return conjunction

    def test_recognition(
        self,
        face: Face,
        is_old: bool,
        is_conjunction: bool = False,
        source_faces: Optional[List[str]] = None
    ) -> RecognitionTrial:
        """Test recognition of face."""
        if is_old:
            prob = self._model.calculate_hit_probability()
        elif is_conjunction:
            n_features = len(source_faces) if source_faces else 2
            prob = self._model.calculate_conjunction_fa_probability(
                n_shared_features=n_features * 2  # Approximate
            )
        else:
            prob = self._model.calculate_new_fa_probability()

        responded_old = random.random() < prob

        # Determine error type
        if is_old:
            error_type = ErrorType.HIT if responded_old else ErrorType.MISS
        elif is_conjunction:
            error_type = (ErrorType.FALSE_ALARM_CONJUNCTION if responded_old
                          else ErrorType.CORRECT_REJECTION)
        else:
            error_type = (ErrorType.FALSE_ALARM_NEW if responded_old
                          else ErrorType.CORRECT_REJECTION)

        trial = RecognitionTrial(
            test_face=face,
            is_old=is_old,
            is_conjunction=is_conjunction,
            source_faces=source_faces,
            response="old" if responded_old else "new",
            error_type=error_type
        )

        self._trials.append(trial)

        return trial


# ============================================================================
# MEMORY CONJUNCTION PARADIGM
# ============================================================================

class MemoryConjunctionParadigm:
    """
    Memory conjunction paradigm.

    "Ba'el's conjunction study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self,
        n_faces: int = 12
    ) -> Dict[str, Any]:
        """Run classic conjunction paradigm."""
        system = MemoryConjunctionSystem()

        # Create and study faces
        studied_faces = []
        for _ in range(n_faces):
            face = system.create_face()
            system.study_face(face.id)
            studied_faces.append(face)

        # Create test items
        n_old = n_faces // 3
        n_conjunction = n_faces // 3
        n_new = n_faces // 3

        results = {
            'old': [],
            'conjunction': [],
            'new': []
        }

        # Test old faces
        for face in studied_faces[:n_old]:
            trial = system.test_recognition(face, is_old=True)
            results['old'].append(trial.error_type == ErrorType.HIT)

        # Test conjunction faces
        for i in range(n_conjunction):
            sources = random.sample([f.id for f in studied_faces], 2)
            conj = system.create_conjunction(sources)

            if conj:
                conj_face = Face(
                    id=conj.id,
                    features=conj.features,
                    context="test"
                )
                trial = system.test_recognition(
                    conj_face, is_old=False, is_conjunction=True, source_faces=sources
                )
                results['conjunction'].append(trial.error_type == ErrorType.FALSE_ALARM_CONJUNCTION)

        # Test new faces
        for _ in range(n_new):
            new_face = system.create_face("new")
            trial = system.test_recognition(new_face, is_old=False)
            results['new'].append(trial.error_type == ErrorType.FALSE_ALARM_NEW)

        hit_rate = sum(results['old']) / max(1, len(results['old']))
        conjunction_fa = sum(results['conjunction']) / max(1, len(results['conjunction']))
        new_fa = sum(results['new']) / max(1, len(results['new']))

        return {
            'hit_rate': hit_rate,
            'conjunction_fa': conjunction_fa,
            'new_fa': new_fa,
            'conjunction_effect': conjunction_fa - new_fa,
            'interpretation': f'Conjunction FA ({conjunction_fa:.0%}) > New FA ({new_fa:.0%})'
        }

    def run_feature_study(
        self
    ) -> Dict[str, Any]:
        """Study effect of shared features."""
        model = MemoryConjunctionModel()

        results = {}

        for n_features in range(1, 7):
            prob = model.calculate_conjunction_fa_probability(n_features)

            results[f'{n_features}_features'] = {
                'fa_probability': prob
            }

        return {
            'by_features': results,
            'interpretation': 'More shared features = higher FA'
        }

    def run_temporal_study(
        self
    ) -> Dict[str, Any]:
        """Study temporal proximity effects."""
        model = MemoryConjunctionModel()

        proximities = [0.0, 0.25, 0.5, 0.75, 1.0]

        results = {}

        for proximity in proximities:
            prob = model.calculate_conjunction_fa_probability(
                n_shared_features=3,
                temporal_proximity=proximity
            )

            results[f'{int(proximity * 100)}%'] = {
                'fa_probability': prob
            }

        return {
            'by_proximity': results,
            'interpretation': 'Temporally close = more conjunction errors'
        }

    def run_context_study(
        self
    ) -> Dict[str, Any]:
        """Study context effects."""
        model = MemoryConjunctionModel()

        conditions = {
            'same_context': True,
            'different_context': False
        }

        results = {}

        for condition, same_ctx in conditions.items():
            prob = model.calculate_conjunction_fa_probability(
                n_shared_features=3,
                same_context=same_ctx
            )

            results[condition] = {
                'fa_probability': prob
            }

        return {
            'by_context': results,
            'interpretation': 'Same context increases conjunction errors'
        }

    def run_binding_failure_study(
        self
    ) -> Dict[str, Any]:
        """Study binding failure mechanism."""
        mechanisms = {
            'encoding_failure': 'Features not bound at encoding',
            'retrieval_failure': 'Binding lost at retrieval',
            'familiarity': 'Feature familiarity without recollection',
            'source_confusion': 'Confusion about feature sources'
        }

        return {
            'mechanisms': mechanisms,
            'key_insight': 'Features encoded but bindings weak',
            'interpretation': 'Conjunction errors from binding failures'
        }

    def run_faces_vs_words_study(
        self
    ) -> Dict[str, Any]:
        """Compare faces vs words."""
        # Faces show more conjunction errors than words
        conditions = {
            'faces': {'conjunction_fa': 0.45, 'reason': 'Many configural features'},
            'words': {'conjunction_fa': 0.30, 'reason': 'Fewer recombineable features'},
            'scenes': {'conjunction_fa': 0.35, 'reason': 'Object + location binding'}
        }

        return {
            'by_material': conditions,
            'interpretation': 'Faces most susceptible to conjunctions'
        }

    def run_encoding_depth_study(
        self
    ) -> Dict[str, Any]:
        """Study encoding depth effects."""
        model = MemoryConjunctionModel()

        depths = [0.2, 0.5, 0.8]

        results = {}

        for depth in depths:
            hit = model.calculate_hit_probability(depth)

            results[f'{int(depth * 100)}%'] = {
                'hit_rate': hit
            }

        return {
            'by_depth': results,
            'interpretation': 'Deep encoding protects against conjunctions'
        }


# ============================================================================
# MEMORY CONJUNCTION ENGINE
# ============================================================================

class MemoryConjunctionEngine:
    """
    Complete memory conjunction engine.

    "Ba'el's conjunction engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = MemoryConjunctionParadigm()
        self._system = MemoryConjunctionSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Face operations

    def create_face(
        self,
        context: str = "default"
    ) -> Face:
        """Create face."""
        return self._system.create_face(context)

    def study_face(
        self,
        face_id: str
    ) -> bool:
        """Study face."""
        return self._system.study_face(face_id)

    def create_conjunction(
        self,
        source_ids: List[str]
    ) -> ConjunctionFace:
        """Create conjunction."""
        return self._system.create_conjunction(source_ids)

    def test_recognition(
        self,
        face: Face,
        is_old: bool
    ) -> RecognitionTrial:
        """Test recognition."""
        return self._system.test_recognition(face, is_old)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def study_features(
        self
    ) -> Dict[str, Any]:
        """Study feature effects."""
        return self._paradigm.run_feature_study()

    def study_temporal(
        self
    ) -> Dict[str, Any]:
        """Study temporal effects."""
        return self._paradigm.run_temporal_study()

    def study_context(
        self
    ) -> Dict[str, Any]:
        """Study context effects."""
        return self._paradigm.run_context_study()

    def study_binding(
        self
    ) -> Dict[str, Any]:
        """Study binding failure."""
        return self._paradigm.run_binding_failure_study()

    def compare_materials(
        self
    ) -> Dict[str, Any]:
        """Compare materials."""
        return self._paradigm.run_faces_vs_words_study()

    def study_encoding(
        self
    ) -> Dict[str, Any]:
        """Study encoding depth."""
        return self._paradigm.run_encoding_depth_study()

    # Analysis

    def get_metrics(self) -> ConjunctionMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return ConjunctionMetrics(
            hit_rate=last['hit_rate'],
            conjunction_fa=last['conjunction_fa'],
            new_fa=last['new_fa'],
            discrimination=last['hit_rate'] - last['conjunction_fa']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'faces': len(self._system._faces),
            'conjunctions': len(self._system._conjunctions),
            'trials': len(self._system._trials)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_memory_conjunction_engine() -> MemoryConjunctionEngine:
    """Create memory conjunction engine."""
    return MemoryConjunctionEngine()


def demonstrate_memory_conjunction() -> Dict[str, Any]:
    """Demonstrate memory conjunction."""
    engine = create_memory_conjunction_engine()

    # Classic
    classic = engine.run_classic()

    # Features
    features = engine.study_features()

    # Binding
    binding = engine.study_binding()

    # Materials
    materials = engine.compare_materials()

    return {
        'classic': {
            'hit_rate': f"{classic['hit_rate']:.0%}",
            'conjunction_fa': f"{classic['conjunction_fa']:.0%}",
            'new_fa': f"{classic['new_fa']:.0%}",
            'effect': f"{classic['conjunction_effect']:.0%}"
        },
        'by_features': {
            k: f"FA: {v['fa_probability']:.0%}"
            for k, v in list(features['by_features'].items())[:3]
        },
        'mechanisms': list(binding['mechanisms'].keys()),
        'materials': {
            k: f"{v['conjunction_fa']:.0%}"
            for k, v in materials['by_material'].items()
        },
        'interpretation': (
            f"Conjunction FA ({classic['conjunction_fa']:.0%}) > New FA ({classic['new_fa']:.0%}). "
            f"Features recombined from different memories. "
            f"Binding failures at encoding or retrieval."
        )
    }


def get_memory_conjunction_facts() -> Dict[str, str]:
    """Get facts about memory conjunction."""
    return {
        'reinitz_1992': 'Memory conjunction errors discovery',
        'phenomenon': 'False recognition of recombined features',
        'mechanism': 'Feature binding failure',
        'faces': 'Especially common with faces',
        'temporal': 'Close in time = more errors',
        'context': 'Same context increases errors',
        'encoding': 'Deep encoding provides protection',
        'applications': 'Eyewitness memory, lineup procedures'
    }
