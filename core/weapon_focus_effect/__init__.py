"""
BAEL Weapon Focus Effect Engine
=================================

Attention narrowing in threatening situations.
Loftus's weapon focus phenomenon.

"Ba'el's gaze is drawn to the blade." — Ba'el
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

logger = logging.getLogger("BAEL.WeaponFocusEffect")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ObjectType(Enum):
    """Type of object held."""
    WEAPON_GUN = auto()
    WEAPON_KNIFE = auto()
    UNUSUAL_NEUTRAL = auto()
    COMMON_NEUTRAL = auto()


class ThreatLevel(Enum):
    """Level of threat."""
    NONE = auto()
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()
    EXTREME = auto()


class MemoryTarget(Enum):
    """What is being remembered."""
    FACE = auto()
    OBJECT = auto()
    PERIPHERAL_DETAILS = auto()
    CENTRAL_DETAILS = auto()


class ArousalLevel(Enum):
    """Arousal level."""
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()


@dataclass
class CrimeScene:
    """
    A crime scene representation.
    """
    id: str
    perpetrator_id: str
    object_type: ObjectType
    threat_level: ThreatLevel
    exposure_time_s: float
    peripheral_details: List[str]


@dataclass
class Witness:
    """
    An eyewitness.
    """
    id: str
    anxiety_level: float      # 0-1
    arousal: ArousalLevel
    distance_m: float


@dataclass
class MemoryTest:
    """
    Memory test result.
    """
    scene: CrimeScene
    witness: Witness
    target: MemoryTarget
    accuracy: float
    confidence: float


@dataclass
class WeaponFocusMetrics:
    """
    Weapon focus metrics.
    """
    face_accuracy_weapon: float
    face_accuracy_control: float
    weapon_accuracy: float
    peripheral_accuracy: float
    effect_size: float


# ============================================================================
# WEAPON FOCUS MODEL
# ============================================================================

class WeaponFocusModel:
    """
    Model of weapon focus effect.

    "Ba'el's threat attention model." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Base accuracy rates
        self._base_face_accuracy = 0.70

        # Weapon focus reduction
        self._weapon_focus_reduction = 0.18

        # Object type effects
        self._object_effects = {
            ObjectType.WEAPON_GUN: -0.20,
            ObjectType.WEAPON_KNIFE: -0.15,
            ObjectType.UNUSUAL_NEUTRAL: -0.05,
            ObjectType.COMMON_NEUTRAL: 0.0
        }

        # Threat level effects
        self._threat_effects = {
            ThreatLevel.NONE: 0.0,
            ThreatLevel.LOW: -0.05,
            ThreatLevel.MODERATE: -0.10,
            ThreatLevel.HIGH: -0.18,
            ThreatLevel.EXTREME: -0.25
        }

        # Arousal effects (inverted U)
        self._optimal_arousal = 0.5
        self._arousal_sensitivity = 0.15

        # Exposure time effects
        self._time_benefit = 0.02  # Per second

        # Distance effects
        self._distance_penalty = 0.01  # Per meter

        # Memory trade-off
        self._weapon_memory_boost = 0.25
        self._peripheral_reduction = 0.30

        self._lock = threading.RLock()

    def calculate_face_accuracy(
        self,
        object_type: ObjectType,
        threat_level: ThreatLevel,
        arousal: float = 0.5,
        exposure_time_s: float = 5.0,
        distance_m: float = 3.0
    ) -> float:
        """Calculate face memory accuracy."""
        accuracy = self._base_face_accuracy

        # Object effect
        accuracy += self._object_effects[object_type]

        # Threat effect
        accuracy += self._threat_effects[threat_level]

        # Arousal (inverted U)
        arousal_effect = -abs(arousal - self._optimal_arousal) * self._arousal_sensitivity
        accuracy += arousal_effect

        # Time benefit
        accuracy += min(exposure_time_s, 30) * self._time_benefit

        # Distance penalty
        accuracy -= max(0, distance_m - 2) * self._distance_penalty

        # Add noise
        accuracy += random.uniform(-0.1, 0.1)

        return max(0.2, min(0.95, accuracy))

    def calculate_object_accuracy(
        self,
        object_type: ObjectType,
        exposure_time_s: float = 5.0
    ) -> float:
        """Calculate object memory accuracy."""
        base = 0.65

        # Weapons are remembered well
        if object_type in [ObjectType.WEAPON_GUN, ObjectType.WEAPON_KNIFE]:
            base += self._weapon_memory_boost

        # Time benefit
        base += min(exposure_time_s, 30) * self._time_benefit

        # Add noise
        base += random.uniform(-0.1, 0.1)

        return max(0.3, min(0.95, base))

    def calculate_peripheral_accuracy(
        self,
        object_type: ObjectType,
        threat_level: ThreatLevel
    ) -> float:
        """Calculate peripheral detail memory."""
        base = 0.60

        # Weapon/threat reduces peripheral
        if object_type in [ObjectType.WEAPON_GUN, ObjectType.WEAPON_KNIFE]:
            base -= self._peripheral_reduction

        # Threat reduces peripheral
        base += self._threat_effects[threat_level] * 1.5

        # Add noise
        base += random.uniform(-0.1, 0.1)

        return max(0.15, min(0.80, base))

    def get_attention_distribution(
        self,
        object_type: ObjectType
    ) -> Dict[str, float]:
        """Get attention allocation."""
        if object_type in [ObjectType.WEAPON_GUN, ObjectType.WEAPON_KNIFE]:
            return {
                'weapon': 0.45,
                'face': 0.25,
                'peripheral': 0.15,
                'escape_routes': 0.15
            }
        else:
            return {
                'object': 0.15,
                'face': 0.40,
                'peripheral': 0.30,
                'other': 0.15
            }

    def get_mechanisms(
        self
    ) -> Dict[str, str]:
        """Get proposed mechanisms."""
        return {
            'attention_narrowing': 'Threat captures attention',
            'cue_utilization': 'High arousal narrows cue use',
            'unusualness': 'Unexpected object draws attention',
            'threat_priority': 'Survival prioritizes threat monitoring'
        }


# ============================================================================
# WEAPON FOCUS SYSTEM
# ============================================================================

class WeaponFocusSystem:
    """
    Weapon focus simulation system.

    "Ba'el's threat system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = WeaponFocusModel()

        self._scenes: Dict[str, CrimeScene] = {}
        self._witnesses: Dict[str, Witness] = {}
        self._tests: List[MemoryTest] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_scene(
        self,
        object_type: ObjectType,
        threat_level: ThreatLevel,
        exposure_time_s: float = 5.0
    ) -> CrimeScene:
        """Create a crime scene."""
        scene = CrimeScene(
            id=self._generate_id(),
            perpetrator_id=self._generate_id(),
            object_type=object_type,
            threat_level=threat_level,
            exposure_time_s=exposure_time_s,
            peripheral_details=["car", "bystander", "sign", "building"]
        )

        self._scenes[scene.id] = scene

        return scene

    def create_witness(
        self,
        anxiety_level: float = 0.5,
        distance_m: float = 3.0
    ) -> Witness:
        """Create a witness."""
        if anxiety_level > 0.7:
            arousal = ArousalLevel.HIGH
        elif anxiety_level > 0.4:
            arousal = ArousalLevel.MODERATE
        else:
            arousal = ArousalLevel.LOW

        witness = Witness(
            id=self._generate_id(),
            anxiety_level=anxiety_level,
            arousal=arousal,
            distance_m=distance_m
        )

        self._witnesses[witness.id] = witness

        return witness

    def test_memory(
        self,
        scene: CrimeScene,
        witness: Witness,
        target: MemoryTarget
    ) -> MemoryTest:
        """Test witness memory."""
        if target == MemoryTarget.FACE:
            accuracy = self._model.calculate_face_accuracy(
                scene.object_type,
                scene.threat_level,
                witness.anxiety_level,
                scene.exposure_time_s,
                witness.distance_m
            )
        elif target == MemoryTarget.OBJECT:
            accuracy = self._model.calculate_object_accuracy(
                scene.object_type,
                scene.exposure_time_s
            )
        elif target == MemoryTarget.PERIPHERAL_DETAILS:
            accuracy = self._model.calculate_peripheral_accuracy(
                scene.object_type,
                scene.threat_level
            )
        else:  # CENTRAL_DETAILS
            accuracy = self._model.calculate_face_accuracy(
                scene.object_type,
                scene.threat_level
            )

        test = MemoryTest(
            scene=scene,
            witness=witness,
            target=target,
            accuracy=accuracy,
            confidence=random.uniform(0.4, 0.9)
        )

        self._tests.append(test)

        return test


# ============================================================================
# WEAPON FOCUS PARADIGM
# ============================================================================

class WeaponFocusParadigm:
    """
    Weapon focus paradigm.

    "Ba'el's focus study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_classic_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run classic weapon focus paradigm."""
        system = WeaponFocusSystem()

        conditions = {
            'weapon': ObjectType.WEAPON_GUN,
            'control': ObjectType.COMMON_NEUTRAL
        }

        results = {}

        for condition, object_type in conditions.items():
            scene = system.create_scene(
                object_type,
                ThreatLevel.MODERATE if object_type == ObjectType.WEAPON_GUN else ThreatLevel.NONE
            )
            witness = system.create_witness()

            face_test = system.test_memory(scene, witness, MemoryTarget.FACE)
            object_test = system.test_memory(scene, witness, MemoryTarget.OBJECT)
            periph_test = system.test_memory(scene, witness, MemoryTarget.PERIPHERAL_DETAILS)

            results[condition] = {
                'face': face_test.accuracy,
                'object': object_test.accuracy,
                'peripheral': periph_test.accuracy
            }

        effect_size = results['control']['face'] - results['weapon']['face']

        return {
            'weapon': results['weapon'],
            'control': results['control'],
            'effect_size': effect_size,
            'interpretation': f'Weapon focus effect: {effect_size:.0%} reduction'
        }

    def run_threat_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare threat levels."""
        model = WeaponFocusModel()

        results = {}

        for threat in ThreatLevel:
            accuracy = model.calculate_face_accuracy(
                ObjectType.WEAPON_GUN,
                threat
            )

            results[threat.name] = {
                'face_accuracy': accuracy
            }

        return {
            'by_threat': results,
            'interpretation': 'Higher threat = worse face memory'
        }

    def run_object_comparison(
        self
    ) -> Dict[str, Any]:
        """Compare object types."""
        model = WeaponFocusModel()

        results = {}

        for obj_type in ObjectType:
            face_acc = model.calculate_face_accuracy(
                obj_type, ThreatLevel.MODERATE
            )
            obj_acc = model.calculate_object_accuracy(obj_type)

            results[obj_type.name] = {
                'face': face_acc,
                'object': obj_acc
            }

        return {
            'by_object': results,
            'interpretation': 'Weapons impair face memory most'
        }

    def run_attention_study(
        self
    ) -> Dict[str, Any]:
        """Study attention distribution."""
        model = WeaponFocusModel()

        conditions = {
            'weapon_present': ObjectType.WEAPON_GUN,
            'no_weapon': ObjectType.COMMON_NEUTRAL
        }

        results = {}

        for condition, obj_type in conditions.items():
            attention = model.get_attention_distribution(obj_type)

            results[condition] = attention

        return {
            'by_condition': results,
            'interpretation': 'Weapon draws attention away from face'
        }

    def run_exposure_time_study(
        self
    ) -> Dict[str, Any]:
        """Study exposure time effects."""
        model = WeaponFocusModel()

        times = [1, 5, 15, 30]  # Seconds

        results = {
            'weapon': {},
            'control': {}
        }

        for time_s in times:
            weapon_acc = model.calculate_face_accuracy(
                ObjectType.WEAPON_GUN, ThreatLevel.MODERATE,
                exposure_time_s=time_s
            )
            control_acc = model.calculate_face_accuracy(
                ObjectType.COMMON_NEUTRAL, ThreatLevel.NONE,
                exposure_time_s=time_s
            )

            results['weapon'][f'{time_s}s'] = weapon_acc
            results['control'][f'{time_s}s'] = control_acc

        return {
            'by_time': results,
            'interpretation': 'More time helps but gap persists'
        }

    def run_unusualness_study(
        self
    ) -> Dict[str, Any]:
        """Study unusualness vs threat."""
        model = WeaponFocusModel()

        # Compare unusual neutral vs weapon
        conditions = {
            'unusual_neutral': (ObjectType.UNUSUAL_NEUTRAL, ThreatLevel.NONE),
            'weapon': (ObjectType.WEAPON_GUN, ThreatLevel.HIGH)
        }

        results = {}

        for condition, (obj, threat) in conditions.items():
            accuracy = model.calculate_face_accuracy(obj, threat)

            results[condition] = {
                'face_accuracy': accuracy
            }

        return {
            'comparison': results,
            'interpretation': 'Threat > unusualness in attention capture'
        }

    def run_mechanism_study(
        self
    ) -> Dict[str, Any]:
        """Study underlying mechanisms."""
        model = WeaponFocusModel()

        mechanisms = model.get_mechanisms()

        return {
            'mechanisms': mechanisms,
            'key_debate': 'Unusualness vs arousal/threat',
            'interpretation': 'Both contribute, threat primary'
        }


# ============================================================================
# WEAPON FOCUS ENGINE
# ============================================================================

class WeaponFocusEngine:
    """
    Complete weapon focus engine.

    "Ba'el's focus engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = WeaponFocusParadigm()
        self._system = WeaponFocusSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Scene operations

    def create_scene(
        self,
        object_type: ObjectType,
        threat_level: ThreatLevel
    ) -> CrimeScene:
        """Create scene."""
        return self._system.create_scene(object_type, threat_level)

    def create_witness(
        self,
        anxiety: float = 0.5
    ) -> Witness:
        """Create witness."""
        return self._system.create_witness(anxiety)

    def test_memory(
        self,
        scene: CrimeScene,
        witness: Witness,
        target: MemoryTarget
    ) -> MemoryTest:
        """Test memory."""
        return self._system.test_memory(scene, witness, target)

    # Experiments

    def run_classic(
        self
    ) -> Dict[str, Any]:
        """Run classic paradigm."""
        result = self._paradigm.run_classic_paradigm()
        self._experiment_results.append(result)
        return result

    def compare_threats(
        self
    ) -> Dict[str, Any]:
        """Compare threat levels."""
        return self._paradigm.run_threat_comparison()

    def compare_objects(
        self
    ) -> Dict[str, Any]:
        """Compare object types."""
        return self._paradigm.run_object_comparison()

    def study_attention(
        self
    ) -> Dict[str, Any]:
        """Study attention."""
        return self._paradigm.run_attention_study()

    def study_exposure_time(
        self
    ) -> Dict[str, Any]:
        """Study exposure time."""
        return self._paradigm.run_exposure_time_study()

    def study_unusualness(
        self
    ) -> Dict[str, Any]:
        """Study unusualness."""
        return self._paradigm.run_unusualness_study()

    def study_mechanisms(
        self
    ) -> Dict[str, Any]:
        """Study mechanisms."""
        return self._paradigm.run_mechanism_study()

    # Analysis

    def get_metrics(self) -> WeaponFocusMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_classic()

        last = self._experiment_results[-1]

        return WeaponFocusMetrics(
            face_accuracy_weapon=last['weapon']['face'],
            face_accuracy_control=last['control']['face'],
            weapon_accuracy=last['weapon']['object'],
            peripheral_accuracy=last['weapon']['peripheral'],
            effect_size=last['effect_size']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'scenes': len(self._system._scenes),
            'witnesses': len(self._system._witnesses),
            'tests': len(self._system._tests)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_weapon_focus_engine() -> WeaponFocusEngine:
    """Create weapon focus engine."""
    return WeaponFocusEngine()


def demonstrate_weapon_focus() -> Dict[str, Any]:
    """Demonstrate weapon focus effect."""
    engine = create_weapon_focus_engine()

    # Classic
    classic = engine.run_classic()

    # Threat
    threat = engine.compare_threats()

    # Attention
    attention = engine.study_attention()

    # Mechanisms
    mechanisms = engine.study_mechanisms()

    return {
        'classic': {
            'weapon_face': f"{classic['weapon']['face']:.0%}",
            'control_face': f"{classic['control']['face']:.0%}",
            'effect': f"{classic['effect_size']:.0%}"
        },
        'by_threat': {
            k: f"{v['face_accuracy']:.0%}"
            for k, v in threat['by_threat'].items()
        },
        'attention': {
            'weapon': attention['by_condition']['weapon_present'],
            'control': attention['by_condition']['no_weapon']
        },
        'mechanisms': mechanisms['mechanisms'],
        'interpretation': (
            f"Effect: {classic['effect_size']:.0%}. "
            f"Weapons capture attention. "
            f"Face memory impaired, weapon memory enhanced."
        )
    }


def get_weapon_focus_facts() -> Dict[str, str]:
    """Get facts about weapon focus effect."""
    return {
        'loftus_1987': 'Weapon focus demonstration',
        'effect_size': '15-20% reduction in face memory',
        'mechanism': 'Attention narrowing + threat priority',
        'weapon_memory': 'Weapon itself remembered well',
        'peripheral': 'Peripheral details impaired',
        'arousal': 'High arousal narrows attention',
        'forensic': 'Critical for eyewitness testimony',
        'applications': 'Lineup procedures, witness evaluation'
    }
