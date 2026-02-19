"""
BAEL Weapon Focus Engine
==========================

Attention narrowing under threat/stress.
Eyewitness memory phenomena.

"Ba'el focuses on threat." — Ba'el
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

logger = logging.getLogger("BAEL.WeaponFocus")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ThreatLevel(Enum):
    """Levels of threat."""
    NONE = auto()
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()
    EXTREME = auto()


class ObjectType(Enum):
    """Types of objects in scene."""
    WEAPON = auto()
    FACE = auto()
    CLOTHING = auto()
    PERIPHERAL = auto()
    CENTRAL = auto()


class ArousalLevel(Enum):
    """Arousal levels."""
    LOW = auto()
    MODERATE = auto()
    HIGH = auto()
    VERY_HIGH = auto()


@dataclass
class SceneObject:
    """
    An object in the scene.
    """
    id: str
    name: str
    object_type: ObjectType
    threat_value: float  # 0-1
    salience: float
    position: Tuple[float, float]  # x, y


@dataclass
class AttentionAllocation:
    """
    How attention was allocated.
    """
    object_id: str
    fixation_duration_ms: float
    encoding_strength: float
    processing_depth: float


@dataclass
class MemoryTrace:
    """
    A memory trace for an object.
    """
    object_id: str
    object_type: ObjectType
    trace_strength: float
    detail_level: float
    confidence: float


@dataclass
class WeaponFocusMetrics:
    """
    Weapon focus metrics.
    """
    weapon_recall: float
    perpetrator_recall: float
    peripheral_recall: float
    weapon_focus_effect: float
    tunnel_vision_extent: float


# ============================================================================
# ATTENTION NARROWING MODEL
# ============================================================================

class AttentionNarrowingModel:
    """
    Model of attention narrowing under stress.

    "Ba'el's tunnel vision." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Attention parameters
        self._base_attention_span = 5.0  # objects
        self._stress_narrowing_factor = 0.6

        # Threat bias
        self._threat_bias = 0.8  # Bias toward threatening objects

        self._lock = threading.RLock()

    def calculate_attention_span(
        self,
        threat_level: ThreatLevel
    ) -> float:
        """Calculate effective attention span under threat."""
        threat_values = {
            ThreatLevel.NONE: 0.0,
            ThreatLevel.LOW: 0.2,
            ThreatLevel.MODERATE: 0.5,
            ThreatLevel.HIGH: 0.8,
            ThreatLevel.EXTREME: 1.0
        }

        threat_val = threat_values[threat_level]
        narrowing = 1 - (threat_val * self._stress_narrowing_factor)

        return self._base_attention_span * narrowing

    def allocate_attention(
        self,
        objects: List[SceneObject],
        threat_level: ThreatLevel
    ) -> List[AttentionAllocation]:
        """Allocate attention across scene objects."""
        effective_span = self.calculate_attention_span(threat_level)

        # Calculate attention priority for each object
        priorities = []
        for obj in objects:
            priority = obj.salience

            # Threat bias: threatening objects capture attention
            if obj.object_type == ObjectType.WEAPON:
                priority += obj.threat_value * self._threat_bias

            # Under high threat, peripheral objects get less attention
            if threat_level in [ThreatLevel.HIGH, ThreatLevel.EXTREME]:
                if obj.object_type == ObjectType.PERIPHERAL:
                    priority *= 0.3

            priorities.append((obj, priority))

        # Sort by priority
        priorities.sort(key=lambda x: x[1], reverse=True)

        # Allocate attention
        allocations = []
        total_attention = 1.0

        for i, (obj, priority) in enumerate(priorities):
            if i >= effective_span:
                # Outside attention span
                allocation = 0.05
            else:
                # Within span, weighted by priority
                allocation = priority / sum(p for _, p in priorities[:int(effective_span) + 1])

            fixation = allocation * 1000  # ms
            encoding = allocation * 0.9
            depth = allocation * 0.8

            alloc = AttentionAllocation(
                object_id=obj.id,
                fixation_duration_ms=fixation,
                encoding_strength=encoding,
                processing_depth=depth
            )
            allocations.append(alloc)

        return allocations


# ============================================================================
# AROUSAL MEMORY MODEL
# ============================================================================

class ArousalMemoryModel:
    """
    Memory encoding under arousal.

    "Ba'el's stress memory." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Yerkes-Dodson parameters
        self._optimal_arousal = 0.5
        self._arousal_effect_central = 0.3  # Benefit for central details
        self._arousal_cost_peripheral = 0.4  # Cost for peripheral details

        self._lock = threading.RLock()

    def yerkes_dodson(
        self,
        arousal: float,
        is_central: bool
    ) -> float:
        """Apply Yerkes-Dodson effect."""
        if is_central:
            # Central details: moderate arousal helps
            optimal = self._optimal_arousal
            distance = abs(arousal - optimal)
            effect = 1.0 - (distance ** 2) * 0.5
            return max(0.3, effect)
        else:
            # Peripheral details: arousal hurts
            return max(0.1, 1.0 - arousal * self._arousal_cost_peripheral)

    def encode_memory(
        self,
        attention: AttentionAllocation,
        obj: SceneObject,
        threat_level: ThreatLevel
    ) -> MemoryTrace:
        """Encode memory trace based on attention and arousal."""
        arousal = {
            ThreatLevel.NONE: 0.2,
            ThreatLevel.LOW: 0.3,
            ThreatLevel.MODERATE: 0.5,
            ThreatLevel.HIGH: 0.7,
            ThreatLevel.EXTREME: 0.9
        }[threat_level]

        is_central = obj.object_type in [ObjectType.WEAPON, ObjectType.FACE, ObjectType.CENTRAL]

        # Yerkes-Dodson modulation
        arousal_mod = self.yerkes_dodson(arousal, is_central)

        # Encoding strength
        trace_strength = attention.encoding_strength * arousal_mod

        # Weapon focus: weapons get enhanced encoding
        if obj.object_type == ObjectType.WEAPON:
            trace_strength *= 1.3

        # Peripheral details suffer
        if obj.object_type == ObjectType.PERIPHERAL:
            trace_strength *= 0.5

        # Detail level
        detail = attention.processing_depth * arousal_mod
        if obj.object_type == ObjectType.WEAPON:
            detail *= 1.2
        elif obj.object_type == ObjectType.FACE and threat_level in [ThreatLevel.HIGH, ThreatLevel.EXTREME]:
            # Face processing impaired when attention on weapon
            detail *= 0.6

        # Confidence (often inflated)
        confidence = trace_strength * 1.2  # Overconfidence common

        trace_strength = max(0, min(1, trace_strength + random.gauss(0, 0.05)))
        detail = max(0, min(1, detail))
        confidence = max(0, min(1, confidence))

        return MemoryTrace(
            object_id=obj.id,
            object_type=obj.object_type,
            trace_strength=trace_strength,
            detail_level=detail,
            confidence=confidence
        )


# ============================================================================
# EYEWITNESS PARADIGM
# ============================================================================

class EyewitnessParadigm:
    """
    Eyewitness memory paradigm.

    "Ba'el's crime scene." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._attention_model = AttentionNarrowingModel()
        self._memory_model = ArousalMemoryModel()

        self._scenes: Dict[str, List[SceneObject]] = {}
        self._memory_traces: Dict[str, List[MemoryTrace]] = {}

        self._object_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._object_counter += 1
        return f"obj_{self._object_counter}"

    def create_crime_scene(
        self,
        scene_id: str,
        has_weapon: bool = True
    ) -> List[SceneObject]:
        """Create a crime scene."""
        objects = []

        # Perpetrator face
        objects.append(SceneObject(
            id=self._generate_id(),
            name="perpetrator_face",
            object_type=ObjectType.FACE,
            threat_value=0.4,
            salience=0.7,
            position=(0.5, 0.5)
        ))

        # Weapon (if present)
        if has_weapon:
            objects.append(SceneObject(
                id=self._generate_id(),
                name="gun",
                object_type=ObjectType.WEAPON,
                threat_value=0.95,
                salience=0.9,
                position=(0.4, 0.6)
            ))

        # Perpetrator clothing
        objects.append(SceneObject(
            id=self._generate_id(),
            name="clothing",
            object_type=ObjectType.CLOTHING,
            threat_value=0.0,
            salience=0.5,
            position=(0.5, 0.7)
        ))

        # Peripheral details
        peripherals = ["car", "sign", "building", "bystander"]
        for i, name in enumerate(peripherals):
            objects.append(SceneObject(
                id=self._generate_id(),
                name=name,
                object_type=ObjectType.PERIPHERAL,
                threat_value=0.0,
                salience=0.3,
                position=(0.2 + i * 0.2, 0.9)
            ))

        self._scenes[scene_id] = objects
        return objects

    def witness_scene(
        self,
        scene_id: str,
        threat_level: ThreatLevel
    ) -> List[MemoryTrace]:
        """Witness a scene and encode memories."""
        objects = self._scenes.get(scene_id, [])
        if not objects:
            return []

        # Allocate attention
        allocations = self._attention_model.allocate_attention(objects, threat_level)

        # Create allocation lookup
        alloc_dict = {a.object_id: a for a in allocations}

        # Encode memories
        traces = []
        for obj in objects:
            alloc = alloc_dict.get(obj.id)
            if alloc:
                trace = self._memory_model.encode_memory(alloc, obj, threat_level)
                traces.append(trace)

        self._memory_traces[scene_id] = traces
        return traces

    def test_memory(
        self,
        scene_id: str,
        delay_minutes: float = 0
    ) -> Dict[str, float]:
        """Test memory for scene details."""
        traces = self._memory_traces.get(scene_id, [])

        # Apply forgetting
        decay = math.exp(-delay_minutes / 30)

        results = {}
        for trace in traces:
            recall_prob = trace.trace_strength * decay
            recalled = random.random() < recall_prob
            results[trace.object_id] = {
                'object_type': trace.object_type.name,
                'recalled': recalled,
                'detail_level': trace.detail_level * decay if recalled else 0,
                'confidence': trace.confidence
            }

        return results


# ============================================================================
# WEAPON FOCUS ENGINE
# ============================================================================

class WeaponFocusEngine:
    """
    Complete weapon focus engine.

    "Ba'el's threat-focused attention." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = EyewitnessParadigm()

        self._experiment_results: List[Dict] = []

        self._scene_counter = 0
        self._lock = threading.RLock()

    def _new_scene_id(self) -> str:
        self._scene_counter += 1
        return f"scene_{self._scene_counter}"

    # Scene creation

    def create_weapon_scene(self) -> str:
        """Create scene with weapon."""
        scene_id = self._new_scene_id()
        self._paradigm.create_crime_scene(scene_id, has_weapon=True)
        return scene_id

    def create_control_scene(self) -> str:
        """Create scene without weapon."""
        scene_id = self._new_scene_id()
        self._paradigm.create_crime_scene(scene_id, has_weapon=False)
        return scene_id

    # Witnessing

    def witness(
        self,
        scene_id: str,
        threat_level: ThreatLevel = ThreatLevel.HIGH
    ) -> List[MemoryTrace]:
        """Witness a scene."""
        return self._paradigm.witness_scene(scene_id, threat_level)

    # Memory testing

    def test_memory(
        self,
        scene_id: str,
        delay_minutes: float = 0
    ) -> Dict[str, Any]:
        """Test memory for scene."""
        return self._paradigm.test_memory(scene_id, delay_minutes)

    # Experiments

    def run_weapon_focus_experiment(
        self,
        n_trials: int = 20,
        delay_minutes: float = 10
    ) -> Dict[str, Any]:
        """Run weapon focus experiment."""
        weapon_results = {
            'weapon_recall': [],
            'face_recall': [],
            'peripheral_recall': []
        }

        control_results = {
            'face_recall': [],
            'peripheral_recall': []
        }

        for _ in range(n_trials):
            # Weapon condition
            weapon_scene = self.create_weapon_scene()
            self.witness(weapon_scene, ThreatLevel.HIGH)
            w_memory = self.test_memory(weapon_scene, delay_minutes)

            for obj_id, data in w_memory.items():
                if data['object_type'] == 'WEAPON':
                    weapon_results['weapon_recall'].append(data['recalled'])
                elif data['object_type'] == 'FACE':
                    weapon_results['face_recall'].append(data['recalled'])
                elif data['object_type'] == 'PERIPHERAL':
                    weapon_results['peripheral_recall'].append(data['recalled'])

            # Control condition (no weapon)
            control_scene = self.create_control_scene()
            self.witness(control_scene, ThreatLevel.MODERATE)
            c_memory = self.test_memory(control_scene, delay_minutes)

            for obj_id, data in c_memory.items():
                if data['object_type'] == 'FACE':
                    control_results['face_recall'].append(data['recalled'])
                elif data['object_type'] == 'PERIPHERAL':
                    control_results['peripheral_recall'].append(data['recalled'])

        # Calculate recall rates
        w_weapon = sum(weapon_results['weapon_recall']) / len(weapon_results['weapon_recall']) if weapon_results['weapon_recall'] else 0
        w_face = sum(weapon_results['face_recall']) / len(weapon_results['face_recall']) if weapon_results['face_recall'] else 0
        w_periph = sum(weapon_results['peripheral_recall']) / len(weapon_results['peripheral_recall']) if weapon_results['peripheral_recall'] else 0

        c_face = sum(control_results['face_recall']) / len(control_results['face_recall']) if control_results['face_recall'] else 0
        c_periph = sum(control_results['peripheral_recall']) / len(control_results['peripheral_recall']) if control_results['peripheral_recall'] else 0

        weapon_focus_effect = c_face - w_face  # How much worse face memory is with weapon

        result = {
            'weapon_condition': {
                'weapon_recall': w_weapon,
                'face_recall': w_face,
                'peripheral_recall': w_periph
            },
            'control_condition': {
                'face_recall': c_face,
                'peripheral_recall': c_periph
            },
            'weapon_focus_effect': weapon_focus_effect,
            'tunnel_vision': c_periph - w_periph
        }

        self._experiment_results.append(result)
        return result

    def run_threat_level_comparison(
        self,
        n_per_level: int = 10
    ) -> Dict[str, Any]:
        """Compare memory across threat levels."""
        results = {}

        for level in [ThreatLevel.LOW, ThreatLevel.MODERATE, ThreatLevel.HIGH, ThreatLevel.EXTREME]:
            face_recalls = []
            peripheral_recalls = []

            for _ in range(n_per_level):
                scene_id = self.create_weapon_scene()
                self.witness(scene_id, level)
                memory = self.test_memory(scene_id, 5)

                for obj_id, data in memory.items():
                    if data['object_type'] == 'FACE':
                        face_recalls.append(data['recalled'])
                    elif data['object_type'] == 'PERIPHERAL':
                        peripheral_recalls.append(data['recalled'])

            results[level.name] = {
                'face_recall': sum(face_recalls) / len(face_recalls) if face_recalls else 0,
                'peripheral_recall': sum(peripheral_recalls) / len(peripheral_recalls) if peripheral_recalls else 0
            }

        return results

    # Analysis

    def get_metrics(self) -> WeaponFocusMetrics:
        """Get weapon focus metrics."""
        if not self._experiment_results:
            self.run_weapon_focus_experiment(10, 5)

        last = self._experiment_results[-1]

        return WeaponFocusMetrics(
            weapon_recall=last['weapon_condition']['weapon_recall'],
            perpetrator_recall=last['weapon_condition']['face_recall'],
            peripheral_recall=last['weapon_condition']['peripheral_recall'],
            weapon_focus_effect=last['weapon_focus_effect'],
            tunnel_vision_extent=last['tunnel_vision']
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'scenes': len(self._paradigm._scenes),
            'experiments': len(self._experiment_results)
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

    # Basic experiment
    basic = engine.run_weapon_focus_experiment(15, 10)

    # Threat level comparison
    levels = engine.run_threat_level_comparison(10)

    return {
        'weapon_focus': {
            'weapon_recall': f"{basic['weapon_condition']['weapon_recall']:.0%}",
            'face_with_weapon': f"{basic['weapon_condition']['face_recall']:.0%}",
            'face_without_weapon': f"{basic['control_condition']['face_recall']:.0%}",
            'effect': f"{basic['weapon_focus_effect']:.0%}"
        },
        'tunnel_vision': {
            'peripheral_with_weapon': f"{basic['weapon_condition']['peripheral_recall']:.0%}",
            'peripheral_without_weapon': f"{basic['control_condition']['peripheral_recall']:.0%}",
            'effect': f"{basic['tunnel_vision']:.0%}"
        },
        'threat_levels': {
            level: {
                'face': f"{data['face_recall']:.0%}",
                'peripheral': f"{data['peripheral_recall']:.0%}"
            }
            for level, data in levels.items()
        },
        'interpretation': (
            f"Weapon focus effect: {basic['weapon_focus_effect']:.0%}. "
            f"Weapons capture attention, impairing memory for perpetrator and periphery."
        )
    }


def get_weapon_focus_facts() -> Dict[str, str]:
    """Get facts about weapon focus."""
    return {
        'loftus_1987': 'Classic demonstration of weapon focus effect',
        'attention_capture': 'Weapons automatically capture attention',
        'tunnel_vision': 'High stress narrows attention span',
        'yerkes_dodson': 'Moderate arousal optimal; high arousal impairs',
        'central_peripheral': 'Central details enhanced, peripheral impaired',
        'eyewitness': 'Major factor in eyewitness testimony reliability',
        'overconfidence': 'Witnesses often overconfident despite poor memory',
        'duration': 'Effect persists across delays'
    }
