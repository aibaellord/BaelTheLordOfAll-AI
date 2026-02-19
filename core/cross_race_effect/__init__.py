"""
BAEL Cross-Race Effect Engine
================================

Own-race recognition advantage.
Meissner & Brigham's cross-race bias.

"Ba'el sees all faces equal." — Ba'el
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

logger = logging.getLogger("BAEL.CrossRaceEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class FaceCategory(Enum):
    """Category of face."""
    OWN_RACE = auto()
    OTHER_RACE = auto()


class ExperienceLevel(Enum):
    """Level of cross-race experience."""
    MINIMAL = auto()
    MODERATE = auto()
    EXTENSIVE = auto()


class ProcessingStyle(Enum):
    """Face processing style."""
    CONFIGURAL = auto()   # Holistic, relations between features
    FEATURAL = auto()     # Individual features


class EncodingDepth(Enum):
    """Depth of encoding."""
    SHALLOW = auto()
    MODERATE = auto()
    DEEP = auto()


@dataclass
class Face:
    """
    A face stimulus.
    """
    id: str
    category: FaceCategory
    features: Dict[str, float]  # Multidimensional
    distinctiveness: float


@dataclass
class FaceMemory:
    """
    Memory for a face.
    """
    face_id: str
    category: FaceCategory
    encoding_strength: float
    configural_encoding: float
    featural_encoding: float


@dataclass
class RecognitionResult:
    """
    Result of face recognition.
    """
    face_id: str
    category: FaceCategory
    hit: bool
    false_alarm: bool
    confidence: float


@dataclass
class CrossRaceMetrics:
    """
    Cross-race effect metrics.
    """
    own_race_accuracy: float
    other_race_accuracy: float
    cross_race_effect: float
    own_race_hit_rate: float
    other_race_hit_rate: float
    own_race_fa_rate: float
    other_race_fa_rate: float


# ============================================================================
# EXPERTISE-BASED MODEL
# ============================================================================

class ExpertiseBasedModel:
    """
    Expertise-based model of cross-race effect.

    "Ba'el's face expertise." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base encoding parameters
        self._base_encoding = 0.5

        # Own-race expertise advantage
        self._own_race_configural_boost = 0.25
        self._own_race_distinctiveness_boost = 0.15

        # Other-race encoding deficit
        self._other_race_configural_deficit = 0.2

        # Experience modulates effect
        self._experience_reduction = {
            ExperienceLevel.MINIMAL: 0.0,
            ExperienceLevel.MODERATE: 0.4,
            ExperienceLevel.EXTENSIVE: 0.7
        }

        # Processing defaults
        self._own_race_configural_weight = 0.7
        self._other_race_configural_weight = 0.4

        self._lock = threading.RLock()

    def calculate_encoding_strength(
        self,
        face: Face,
        experience: ExperienceLevel = ExperienceLevel.MINIMAL
    ) -> Tuple[float, float, float]:
        """Calculate encoding strength and components."""
        # Base encoding
        strength = self._base_encoding

        if face.category == FaceCategory.OWN_RACE:
            # Own-race advantage
            configural = self._own_race_configural_weight

            # Configural boost
            strength += self._own_race_configural_boost

            # Distinctiveness advantage
            strength += face.distinctiveness * self._own_race_distinctiveness_boost

        else:
            # Other-race deficit
            configural = self._other_race_configural_weight

            # Configural deficit
            strength -= self._other_race_configural_deficit

            # Experience can reduce deficit
            reduction = self._experience_reduction.get(experience, 0)
            strength += self._other_race_configural_deficit * reduction
            configural += (self._own_race_configural_weight - configural) * reduction

        featural = 1 - configural

        return strength, configural, featural

    def calculate_recognition_probability(
        self,
        memory: FaceMemory
    ) -> float:
        """Calculate recognition probability."""
        # Combine encoding strength with processing weights
        prob = memory.encoding_strength

        # Configural encoding is more diagnostic for recognition
        configural_weight = memory.configural_encoding
        prob *= (0.5 + configural_weight * 0.3)

        return min(0.95, max(0.1, prob))

    def calculate_false_alarm_rate(
        self,
        category: FaceCategory,
        experience: ExperienceLevel = ExperienceLevel.MINIMAL
    ) -> float:
        """Calculate false alarm rate."""
        # Other-race faces have higher FA due to lower distinctiveness
        if category == FaceCategory.OWN_RACE:
            fa_rate = 0.15
        else:
            fa_rate = 0.30

            # Experience reduces FA
            reduction = self._experience_reduction.get(experience, 0)
            fa_rate -= 0.15 * reduction

        return fa_rate


# ============================================================================
# CROSS-RACE EFFECT SYSTEM
# ============================================================================

class CrossRaceEffectSystem:
    """
    Cross-race effect experimental system.

    "Ba'el's face bias system." — Ba'el
    """

    def __init__(
        self,
        experience: ExperienceLevel = ExperienceLevel.MINIMAL
    ):
        """Initialize system."""
        self._model = ExpertiseBasedModel()
        self._experience = experience

        self._faces: Dict[str, Face] = {}
        self._memories: Dict[str, FaceMemory] = {}
        self._results: List[RecognitionResult] = []

        self._face_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._face_counter += 1
        return f"face_{self._face_counter}"

    def create_face(
        self,
        category: FaceCategory,
        distinctiveness: float = 0.5
    ) -> Face:
        """Create a face stimulus."""
        features = {
            f"feature_{i}": random.random()
            for i in range(10)
        }

        face = Face(
            id=self._generate_id(),
            category=category,
            features=features,
            distinctiveness=distinctiveness
        )

        self._faces[face.id] = face

        return face

    def encode_face(
        self,
        face_id: str
    ) -> FaceMemory:
        """Encode a face."""
        face = self._faces.get(face_id)
        if not face:
            return None

        strength, configural, featural = self._model.calculate_encoding_strength(
            face, self._experience
        )

        memory = FaceMemory(
            face_id=face_id,
            category=face.category,
            encoding_strength=strength,
            configural_encoding=configural,
            featural_encoding=featural
        )

        self._memories[face_id] = memory

        return memory

    def test_recognition(
        self,
        face_id: str,
        is_target: bool = True
    ) -> RecognitionResult:
        """Test recognition of a face."""
        face = self._faces.get(face_id)
        memory = self._memories.get(face_id)

        if not face:
            return None

        if is_target and memory:
            # Target face - calculate hit
            hit_prob = self._model.calculate_recognition_probability(memory)
            hit = random.random() < hit_prob
            fa = False
        else:
            # Foil face - calculate false alarm
            hit = False
            fa_rate = self._model.calculate_false_alarm_rate(
                face.category, self._experience
            )
            fa = random.random() < fa_rate

        result = RecognitionResult(
            face_id=face_id,
            category=face.category,
            hit=hit,
            false_alarm=fa,
            confidence=random.uniform(0.4, 0.9)
        )

        self._results.append(result)

        return result


# ============================================================================
# CROSS-RACE PARADIGM
# ============================================================================

class CrossRaceParadigm:
    """
    Cross-race effect experimental paradigm.

    "Ba'el's face bias study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_basic_experiment(
        self,
        n_per_condition: int = 20
    ) -> Dict[str, Any]:
        """Run basic cross-race recognition experiment."""
        system = CrossRaceEffectSystem()

        own_race_hits = 0
        own_race_targets = 0
        own_race_fas = 0
        own_race_foils = 0

        other_race_hits = 0
        other_race_targets = 0
        other_race_fas = 0
        other_race_foils = 0

        # Study phase
        for i in range(n_per_condition):
            # Own race faces
            own_face = system.create_face(FaceCategory.OWN_RACE)
            system.encode_face(own_face.id)

            # Other race faces
            other_face = system.create_face(FaceCategory.OTHER_RACE)
            system.encode_face(other_face.id)

        # Test phase - targets
        for face_id, memory in system._memories.items():
            result = system.test_recognition(face_id, is_target=True)

            if result.category == FaceCategory.OWN_RACE:
                own_race_targets += 1
                if result.hit:
                    own_race_hits += 1
            else:
                other_race_targets += 1
                if result.hit:
                    other_race_hits += 1

        # Test phase - foils (new faces)
        for i in range(n_per_condition):
            # Own race foil
            own_foil = system.create_face(FaceCategory.OWN_RACE)
            result = system.test_recognition(own_foil.id, is_target=False)
            own_race_foils += 1
            if result.false_alarm:
                own_race_fas += 1

            # Other race foil
            other_foil = system.create_face(FaceCategory.OTHER_RACE)
            result = system.test_recognition(other_foil.id, is_target=False)
            other_race_foils += 1
            if result.false_alarm:
                other_race_fas += 1

        # Calculate metrics
        own_hit_rate = own_race_hits / own_race_targets if own_race_targets > 0 else 0
        other_hit_rate = other_race_hits / other_race_targets if other_race_targets > 0 else 0
        own_fa_rate = own_race_fas / own_race_foils if own_race_foils > 0 else 0
        other_fa_rate = other_race_fas / other_race_foils if other_race_foils > 0 else 0

        # d' approximation (simplified)
        own_accuracy = own_hit_rate - own_fa_rate
        other_accuracy = other_hit_rate - other_fa_rate

        return {
            'own_race_hit_rate': own_hit_rate,
            'other_race_hit_rate': other_hit_rate,
            'own_race_fa_rate': own_fa_rate,
            'other_race_fa_rate': other_fa_rate,
            'own_race_accuracy': own_accuracy,
            'other_race_accuracy': other_accuracy,
            'cross_race_effect': own_accuracy - other_accuracy
        }

    def run_experience_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare effect across experience levels."""
        results = {}

        for experience in ExperienceLevel:
            system = CrossRaceEffectSystem(experience=experience)

            # Study other-race faces
            for i in range(10):
                face = system.create_face(FaceCategory.OTHER_RACE)
                system.encode_face(face.id)

            # Test
            hits = 0
            for face_id in list(system._memories.keys()):
                result = system.test_recognition(face_id, is_target=True)
                if result.hit:
                    hits += 1

            results[experience.name] = hits / 10

        return results

    def run_encoding_depth_test(
        self
    ) -> Dict[str, Any]:
        """Test encoding depth effect."""
        # Deeper encoding can reduce CRE

        shallow_cre = []
        deep_cre = []

        for _ in range(5):
            # Shallow encoding (no individuation)
            system = CrossRaceEffectSystem()

            for i in range(10):
                own = system.create_face(FaceCategory.OWN_RACE)
                other = system.create_face(FaceCategory.OTHER_RACE)
                system.encode_face(own.id)
                system.encode_face(other.id)

            own_hits = sum(1 for fid in system._memories if system._faces[fid].category == FaceCategory.OWN_RACE and system.test_recognition(fid).hit)
            other_hits = sum(1 for fid in system._memories if system._faces[fid].category == FaceCategory.OTHER_RACE and system.test_recognition(fid).hit)

            shallow_cre.append((own_hits - other_hits) / 10)

            # Deep encoding (individuation instructions)
            system = CrossRaceEffectSystem(experience=ExperienceLevel.MODERATE)

            for i in range(10):
                own = system.create_face(FaceCategory.OWN_RACE, distinctiveness=0.7)
                other = system.create_face(FaceCategory.OTHER_RACE, distinctiveness=0.7)
                system.encode_face(own.id)
                system.encode_face(other.id)

            own_hits = 0
            other_hits = 0
            for fid in list(system._memories.keys()):
                result = system.test_recognition(fid)
                if result.hit:
                    if result.category == FaceCategory.OWN_RACE:
                        own_hits += 1
                    else:
                        other_hits += 1

            deep_cre.append((own_hits - other_hits) / 10)

        return {
            'shallow_encoding_cre': sum(shallow_cre) / 5,
            'deep_encoding_cre': sum(deep_cre) / 5,
            'reduction': sum(shallow_cre) / 5 - sum(deep_cre) / 5,
            'interpretation': 'Individuation instructions reduce CRE'
        }

    def run_developmental_test(
        self
    ) -> Dict[str, Any]:
        """Test developmental trajectory."""
        # CRE develops with increasing own-race exposure

        ages = ['infant', 'child', 'adult']
        experience_mapping = {
            'infant': ExperienceLevel.MINIMAL,  # Before perceptual narrowing
            'child': ExperienceLevel.MINIMAL,   # After narrowing
            'adult': ExperienceLevel.MINIMAL    # Established bias
        }

        results = {}

        for age in ages:
            experience = experience_mapping[age]
            system = CrossRaceEffectSystem(experience=experience)

            # Faces
            for i in range(10):
                own = system.create_face(FaceCategory.OWN_RACE)
                other = system.create_face(FaceCategory.OTHER_RACE)
                system.encode_face(own.id)
                system.encode_face(other.id)

            own_hits = 0
            other_hits = 0

            for fid in list(system._memories.keys()):
                result = system.test_recognition(fid)
                if result.hit:
                    if result.category == FaceCategory.OWN_RACE:
                        own_hits += 1
                    else:
                        other_hits += 1

            cre = (own_hits - other_hits) / 10

            # Infants don't show CRE before ~9 months
            if age == 'infant':
                cre *= 0.2  # Minimal effect

            results[age] = cre

        return results


# ============================================================================
# CROSS-RACE EFFECT ENGINE
# ============================================================================

class CrossRaceEffectEngine:
    """
    Complete cross-race effect engine.

    "Ba'el's face bias engine." — Ba'el
    """

    def __init__(
        self,
        experience: ExperienceLevel = ExperienceLevel.MINIMAL
    ):
        """Initialize engine."""
        self._paradigm = CrossRaceParadigm()
        self._system = CrossRaceEffectSystem(experience)

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Face management

    def create_face(
        self,
        category: FaceCategory,
        distinctiveness: float = 0.5
    ) -> Face:
        """Create a face."""
        return self._system.create_face(category, distinctiveness)

    def encode(
        self,
        face_id: str
    ) -> FaceMemory:
        """Encode a face."""
        return self._system.encode_face(face_id)

    def test(
        self,
        face_id: str,
        is_target: bool = True
    ) -> RecognitionResult:
        """Test recognition."""
        return self._system.test_recognition(face_id, is_target)

    # Experiments

    def run_basic_experiment(
        self,
        n_per_condition: int = 20
    ) -> Dict[str, Any]:
        """Run basic experiment."""
        result = self._paradigm.run_basic_experiment(n_per_condition)
        self._experiment_results.append(result)
        return result

    def compare_experience(
        self
    ) -> Dict[str, Any]:
        """Compare experience levels."""
        return self._paradigm.run_experience_comparison()

    def test_encoding_depth(
        self
    ) -> Dict[str, Any]:
        """Test encoding depth."""
        return self._paradigm.run_encoding_depth_test()

    def test_development(
        self
    ) -> Dict[str, Any]:
        """Test developmental trajectory."""
        return self._paradigm.run_developmental_test()

    def run_eyewitness_simulation(
        self
    ) -> Dict[str, Any]:
        """Simulate eyewitness cross-race scenario."""
        system = CrossRaceEffectSystem()

        # Witness encodes other-race perpetrator
        perpetrator = system.create_face(FaceCategory.OTHER_RACE)
        system.encode_face(perpetrator.id)

        # Lineup with foils
        foils = [
            system.create_face(FaceCategory.OTHER_RACE)
            for _ in range(5)
        ]

        # Test perpetrator
        perp_result = system.test_recognition(perpetrator.id, is_target=True)

        # Test foils
        fa_results = [
            system.test_recognition(f.id, is_target=False)
            for f in foils
        ]

        false_alarms = sum(1 for r in fa_results if r.false_alarm)

        return {
            'identified_perpetrator': perp_result.hit,
            'false_identifications': false_alarms,
            'lineup_size': 6,
            'implications': 'Cross-race misidentifications are a leading cause of wrongful convictions'
        }

    # Analysis

    def get_metrics(self) -> CrossRaceMetrics:
        """Get cross-race metrics."""
        if not self._experiment_results:
            self.run_basic_experiment()

        last = self._experiment_results[-1]

        return CrossRaceMetrics(
            own_race_accuracy=last['own_race_accuracy'],
            other_race_accuracy=last['other_race_accuracy'],
            cross_race_effect=last['cross_race_effect'],
            own_race_hit_rate=last['own_race_hit_rate'],
            other_race_hit_rate=last['other_race_hit_rate'],
            own_race_fa_rate=last['own_race_fa_rate'],
            other_race_fa_rate=last['other_race_fa_rate']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'faces': len(self._system._faces),
            'memories': len(self._system._memories),
            'experiments': len(self._experiment_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_cross_race_engine(
    experience: ExperienceLevel = ExperienceLevel.MINIMAL
) -> CrossRaceEffectEngine:
    """Create cross-race effect engine."""
    return CrossRaceEffectEngine(experience)


def demonstrate_cross_race_effect() -> Dict[str, Any]:
    """Demonstrate cross-race effect."""
    engine = create_cross_race_engine()

    # Basic experiment
    basic = engine.run_basic_experiment(20)

    # Experience comparison
    experience = engine.compare_experience()

    # Encoding depth
    encoding = engine.test_encoding_depth()

    # Development
    development = engine.test_development()

    # Eyewitness simulation
    eyewitness = engine.run_eyewitness_simulation()

    return {
        'cross_race_effect': {
            'own_race_accuracy': f"{basic['own_race_accuracy']:.0%}",
            'other_race_accuracy': f"{basic['other_race_accuracy']:.0%}",
            'effect_size': f"{basic['cross_race_effect']:.0%}"
        },
        'by_experience': {
            level: f"{rate:.0%}"
            for level, rate in experience.items()
        },
        'encoding_depth': {
            'shallow_cre': f"{encoding['shallow_encoding_cre']:.0%}",
            'deep_cre': f"{encoding['deep_encoding_cre']:.0%}",
            'reduction': f"{encoding['reduction']:.0%}"
        },
        'development': {
            age: f"CRE: {cre:.0%}"
            for age, cre in development.items()
        },
        'eyewitness': {
            'identified': eyewitness['identified_perpetrator'],
            'false_alarms': eyewitness['false_identifications']
        },
        'interpretation': (
            f"Cross-race effect: {basic['cross_race_effect']:.0%}. "
            f"Own-race faces recognized better due to expertise."
        )
    }


def get_cross_race_facts() -> Dict[str, str]:
    """Get facts about cross-race effect."""
    return {
        'meissner_brigham_2001': 'Major meta-analysis of CRE',
        'expertise_hypothesis': 'Own-race expertise from differential exposure',
        'perceptual_narrowing': 'Develops in first year of life',
        'configural_processing': 'Own-race uses more configural processing',
        'contact_reduces': 'Cross-race contact reduces effect',
        'eyewitness': 'Major factor in wrongful convictions',
        'mirror_effect': 'Higher hits AND lower FAs for own-race',
        'individuation': 'Instructions to individuate reduce CRE'
    }
