"""
BAEL Source Confusion Engine
==============================

Misattributing where memories came from.
Johnson's source monitoring failures.

"Ba'el knows the origin of every thought." — Ba'el
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

logger = logging.getLogger("BAEL.SourceConfusion")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SourceType(Enum):
    """Type of memory source."""
    PERCEIVED = auto()       # Actually seen
    IMAGINED = auto()        # Self-generated image
    HEARD = auto()           # Told by others
    READ = auto()            # From text
    DREAMED = auto()         # From dreams
    INFERRED = auto()        # Logical deduction


class ConfusionType(Enum):
    """Type of source confusion."""
    REALITY_MONITORING = auto()      # Imagined vs perceived
    EXTERNAL_MONITORING = auto()     # Person A vs B
    INTERNAL_MONITORING = auto()     # Thought vs said
    TEMPORAL_CONFUSION = auto()      # When it happened


class ConfusionDirection(Enum):
    """Direction of confusion."""
    INTERNAL_TO_EXTERNAL = auto()    # Imagined -> perceived
    EXTERNAL_TO_INTERNAL = auto()    # Perceived -> imagined
    SOURCE_A_TO_B = auto()           # Person A -> Person B
    TIME_SHIFT = auto()              # Wrong temporal context


@dataclass
class SourceFeatures:
    """
    Features used for source attribution.
    """
    perceptual_detail: float
    contextual_detail: float
    semantic_content: float
    cognitive_operations: float
    emotional_intensity: float


@dataclass
class MemoryRecord:
    """
    A memory with source information.
    """
    id: str
    content: str
    actual_source: SourceType
    features: SourceFeatures
    encoding_quality: float


@dataclass
class SourceAttribution:
    """
    An attribution of source.
    """
    memory_id: str
    attributed_source: SourceType
    confidence: float
    correct: bool


@dataclass
class ConfusionEvent:
    """
    A source confusion event.
    """
    memory_id: str
    actual_source: SourceType
    attributed_source: SourceType
    confusion_type: ConfusionType
    feature_similarity: float


@dataclass
class SourceConfusionMetrics:
    """
    Source confusion metrics.
    """
    overall_accuracy: float
    confusion_rate: float
    by_source: Dict[str, float]
    by_confusion_type: Dict[str, float]


# ============================================================================
# SOURCE CONFUSION MODEL
# ============================================================================

class SourceConfusionModel:
    """
    Johnson's source monitoring model.

    "Ba'el's origin tracing." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Feature weights for source judgment
        self._perceptual_weight = 0.3
        self._contextual_weight = 0.25
        self._semantic_weight = 0.15
        self._cognitive_weight = 0.2
        self._emotional_weight = 0.1

        # Source profiles (typical feature levels)
        self._source_profiles = {
            SourceType.PERCEIVED: SourceFeatures(0.8, 0.7, 0.5, 0.2, 0.5),
            SourceType.IMAGINED: SourceFeatures(0.4, 0.3, 0.6, 0.7, 0.5),
            SourceType.HEARD: SourceFeatures(0.3, 0.5, 0.7, 0.3, 0.4),
            SourceType.READ: SourceFeatures(0.2, 0.4, 0.8, 0.4, 0.3),
            SourceType.DREAMED: SourceFeatures(0.5, 0.2, 0.4, 0.6, 0.7),
            SourceType.INFERRED: SourceFeatures(0.1, 0.3, 0.9, 0.8, 0.2)
        }

        # Confusion susceptibility (source A confused with B)
        self._confusion_matrix = defaultdict(lambda: 0.1)
        self._confusion_matrix[(SourceType.IMAGINED, SourceType.PERCEIVED)] = 0.3
        self._confusion_matrix[(SourceType.HEARD, SourceType.READ)] = 0.25
        self._confusion_matrix[(SourceType.DREAMED, SourceType.PERCEIVED)] = 0.2

        self._lock = threading.RLock()

    def calculate_feature_match(
        self,
        features: SourceFeatures,
        source: SourceType
    ) -> float:
        """Calculate how well features match a source profile."""
        profile = self._source_profiles[source]

        perceptual_match = 1 - abs(features.perceptual_detail - profile.perceptual_detail)
        contextual_match = 1 - abs(features.contextual_detail - profile.contextual_detail)
        semantic_match = 1 - abs(features.semantic_content - profile.semantic_content)
        cognitive_match = 1 - abs(features.cognitive_operations - profile.cognitive_operations)
        emotional_match = 1 - abs(features.emotional_intensity - profile.emotional_intensity)

        weighted = (
            perceptual_match * self._perceptual_weight +
            contextual_match * self._contextual_weight +
            semantic_match * self._semantic_weight +
            cognitive_match * self._cognitive_weight +
            emotional_match * self._emotional_weight
        )

        return weighted

    def attribute_source(
        self,
        features: SourceFeatures
    ) -> Tuple[SourceType, float]:
        """Attribute source based on features."""
        best_match = None
        best_score = -1

        for source in SourceType:
            score = self.calculate_feature_match(features, source)
            if score > best_score:
                best_score = score
                best_match = source

        confidence = best_score

        return best_match, confidence

    def calculate_confusion_probability(
        self,
        actual_source: SourceType,
        candidate_source: SourceType,
        feature_similarity: float
    ) -> float:
        """Calculate probability of confusion."""
        base_confusion = self._confusion_matrix[(actual_source, candidate_source)]

        # Higher similarity = more confusion
        similarity_factor = feature_similarity * 0.5

        return base_confusion + similarity_factor

    def generate_degraded_features(
        self,
        original: SourceFeatures,
        degradation: float
    ) -> SourceFeatures:
        """Generate degraded features (as memory decays)."""
        noise = degradation * 0.3

        return SourceFeatures(
            perceptual_detail=max(0, min(1, original.perceptual_detail - degradation * 0.2 + random.uniform(-noise, noise))),
            contextual_detail=max(0, min(1, original.contextual_detail - degradation * 0.3 + random.uniform(-noise, noise))),
            semantic_content=max(0, min(1, original.semantic_content + random.uniform(-noise, noise))),
            cognitive_operations=max(0, min(1, original.cognitive_operations - degradation * 0.1 + random.uniform(-noise, noise))),
            emotional_intensity=max(0, min(1, original.emotional_intensity - degradation * 0.15 + random.uniform(-noise, noise)))
        )


# ============================================================================
# SOURCE CONFUSION SYSTEM
# ============================================================================

class SourceConfusionSystem:
    """
    Source confusion simulation system.

    "Ba'el's origin tracking system." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = SourceConfusionModel()

        self._memories: Dict[str, MemoryRecord] = {}
        self._attributions: List[SourceAttribution] = []
        self._confusions: List[ConfusionEvent] = []

        self._counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def create_memory(
        self,
        content: str,
        source: SourceType,
        encoding_quality: float = 0.8
    ) -> MemoryRecord:
        """Create a memory with source."""
        # Generate features based on source
        profile = self._model._source_profiles[source]

        # Add noise based on encoding quality
        noise = (1 - encoding_quality) * 0.3

        features = SourceFeatures(
            perceptual_detail=max(0, min(1, profile.perceptual_detail + random.uniform(-noise, noise))),
            contextual_detail=max(0, min(1, profile.contextual_detail + random.uniform(-noise, noise))),
            semantic_content=max(0, min(1, profile.semantic_content + random.uniform(-noise, noise))),
            cognitive_operations=max(0, min(1, profile.cognitive_operations + random.uniform(-noise, noise))),
            emotional_intensity=max(0, min(1, profile.emotional_intensity + random.uniform(-noise, noise)))
        )

        memory = MemoryRecord(
            id=self._generate_id(),
            content=content,
            actual_source=source,
            features=features,
            encoding_quality=encoding_quality
        )

        self._memories[memory.id] = memory

        return memory

    def attribute_source(
        self,
        memory_id: str,
        degradation: float = 0.0
    ) -> SourceAttribution:
        """Attribute source to a memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return None

        # Potentially degrade features
        if degradation > 0:
            features = self._model.generate_degraded_features(
                memory.features, degradation
            )
        else:
            features = memory.features

        attributed, confidence = self._model.attribute_source(features)

        correct = attributed == memory.actual_source

        attribution = SourceAttribution(
            memory_id=memory_id,
            attributed_source=attributed,
            confidence=confidence,
            correct=correct
        )

        self._attributions.append(attribution)

        # Track confusion
        if not correct:
            # Calculate feature similarity
            similarity = self._model.calculate_feature_match(
                features, memory.actual_source
            )

            # Determine confusion type
            if memory.actual_source in [SourceType.IMAGINED, SourceType.DREAMED]:
                if attributed == SourceType.PERCEIVED:
                    confusion_type = ConfusionType.REALITY_MONITORING
                else:
                    confusion_type = ConfusionType.INTERNAL_MONITORING
            else:
                confusion_type = ConfusionType.EXTERNAL_MONITORING

            confusion = ConfusionEvent(
                memory_id=memory_id,
                actual_source=memory.actual_source,
                attributed_source=attributed,
                confusion_type=confusion_type,
                feature_similarity=similarity
            )

            self._confusions.append(confusion)

        return attribution


# ============================================================================
# SOURCE CONFUSION PARADIGM
# ============================================================================

class SourceConfusionParadigm:
    """
    Source confusion experimental paradigm.

    "Ba'el's confusion study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_reality_monitoring_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run reality monitoring paradigm."""
        system = SourceConfusionSystem()

        # Create perceived and imagined memories
        perceived = []
        imagined = []

        for i in range(20):
            p_mem = system.create_memory(f"perceived_{i}", SourceType.PERCEIVED)
            perceived.append(p_mem)

            i_mem = system.create_memory(f"imagined_{i}", SourceType.IMAGINED)
            imagined.append(i_mem)

        # Test with delay (degradation)
        perceived_correct = 0
        imagined_correct = 0

        for mem in perceived:
            attr = system.attribute_source(mem.id, degradation=0.3)
            if attr.correct:
                perceived_correct += 1

        for mem in imagined:
            attr = system.attribute_source(mem.id, degradation=0.3)
            if attr.correct:
                imagined_correct += 1

        perceived_acc = perceived_correct / len(perceived)
        imagined_acc = imagined_correct / len(imagined)

        return {
            'perceived_accuracy': perceived_acc,
            'imagined_accuracy': imagined_acc,
            'confusion_rate': 1 - (perceived_acc + imagined_acc) / 2,
            'interpretation': 'Imagined memories often confused with perceived'
        }

    def run_external_monitoring_paradigm(
        self
    ) -> Dict[str, Any]:
        """Run external source monitoring paradigm."""
        system = SourceConfusionSystem()

        # Same content, different external sources
        heard_mems = []
        read_mems = []

        for i in range(15):
            h_mem = system.create_memory(f"fact_{i}", SourceType.HEARD)
            heard_mems.append(h_mem)

            r_mem = system.create_memory(f"fact_{i}", SourceType.READ)
            read_mems.append(r_mem)

        # Test
        heard_correct = sum(
            1 for m in heard_mems
            if system.attribute_source(m.id, 0.2).correct
        )

        read_correct = sum(
            1 for m in read_mems
            if system.attribute_source(m.id, 0.2).correct
        )

        return {
            'heard_accuracy': heard_correct / len(heard_mems),
            'read_accuracy': read_correct / len(read_mems),
            'confusions': len(system._confusions),
            'interpretation': 'External sources often confused with each other'
        }

    def run_repeated_imagination_study(
        self
    ) -> Dict[str, Any]:
        """Study how repeated imagination affects source confusion."""
        system = SourceConfusionSystem()

        results = {}

        for repetitions in [0, 1, 3, 5]:
            # Create imagined memory with increasing perceptual detail
            features = SourceFeatures(
                perceptual_detail=0.4 + repetitions * 0.1,  # Increases with imagination
                contextual_detail=0.3 + repetitions * 0.05,
                semantic_content=0.6,
                cognitive_operations=0.7 - repetitions * 0.05,  # Decreases
                emotional_intensity=0.5
            )

            mem = system.create_memory(
                f"imagined_repeated_{repetitions}",
                SourceType.IMAGINED,
                encoding_quality=0.8
            )

            # Override features
            mem.features = features

            attr = system.attribute_source(mem.id)

            results[f"reps_{repetitions}"] = {
                'attributed_perceived': attr.attributed_source == SourceType.PERCEIVED,
                'perceptual_detail': features.perceptual_detail
            }

        return {
            'by_repetition': results,
            'interpretation': 'Repeated imagination increases source confusion'
        }

    def run_aging_study(
        self
    ) -> Dict[str, Any]:
        """Study aging effects on source monitoring."""
        conditions = {
            'young': {'encoding': 0.9, 'degradation': 0.2},
            'older': {'encoding': 0.7, 'degradation': 0.4}
        }

        results = {}

        for age, params in conditions.items():
            system = SourceConfusionSystem()

            # Create memories
            for i in range(20):
                source = random.choice(list(SourceType))
                system.create_memory(f"mem_{i}", source, params['encoding'])

            # Test
            correct = 0
            for mem_id in system._memories:
                attr = system.attribute_source(mem_id, params['degradation'])
                if attr.correct:
                    correct += 1

            results[age] = {
                'accuracy': correct / 20,
                'confusions': len(system._confusions)
            }

        return {
            'by_age': results,
            'interpretation': 'Older adults show more source confusions'
        }

    def run_divided_attention_study(
        self
    ) -> Dict[str, Any]:
        """Study divided attention effects."""
        conditions = {
            'full_attention': 0.9,
            'divided_attention': 0.5
        }

        results = {}

        for condition, encoding in conditions.items():
            system = SourceConfusionSystem()

            # Create memories
            for i in range(15):
                system.create_memory(
                    f"mem_{i}",
                    random.choice([SourceType.PERCEIVED, SourceType.HEARD]),
                    encoding
                )

            # Test
            correct = sum(
                1 for mid in system._memories
                if system.attribute_source(mid).correct
            )

            results[condition] = {
                'accuracy': correct / 15,
                'confusions': len(system._confusions)
            }

        return {
            'by_attention': results,
            'interpretation': 'Divided attention impairs source encoding'
        }

    def run_emotional_content_study(
        self
    ) -> Dict[str, Any]:
        """Study emotional content effects."""
        system = SourceConfusionSystem()

        # Create memories with different emotional content
        conditions = {
            'neutral': 0.3,
            'moderate': 0.5,
            'high': 0.8
        }

        results = {}

        for condition, emotion in conditions.items():
            mems = []

            for i in range(10):
                mem = system.create_memory(
                    f"mem_{condition}_{i}",
                    SourceType.PERCEIVED
                )
                mem.features.emotional_intensity = emotion
                mems.append(mem)

            correct = sum(
                1 for m in mems
                if system.attribute_source(m.id).correct
            )

            results[condition] = {
                'accuracy': correct / 10
            }

        return {
            'by_emotion': results,
            'interpretation': 'Emotional content affects source memory'
        }


# ============================================================================
# SOURCE CONFUSION ENGINE
# ============================================================================

class SourceConfusionEngine:
    """
    Complete source confusion engine.

    "Ba'el's origin confusion engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SourceConfusionParadigm()
        self._system = SourceConfusionSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Memory management

    def create_memory(
        self,
        content: str,
        source: SourceType,
        encoding_quality: float = 0.8
    ) -> MemoryRecord:
        """Create memory."""
        return self._system.create_memory(content, source, encoding_quality)

    def attribute_source(
        self,
        memory_id: str,
        degradation: float = 0.0
    ) -> SourceAttribution:
        """Attribute source."""
        return self._system.attribute_source(memory_id, degradation)

    # Experiments

    def run_reality_monitoring(
        self
    ) -> Dict[str, Any]:
        """Run reality monitoring paradigm."""
        result = self._paradigm.run_reality_monitoring_paradigm()
        self._experiment_results.append(result)
        return result

    def run_external_monitoring(
        self
    ) -> Dict[str, Any]:
        """Run external monitoring paradigm."""
        return self._paradigm.run_external_monitoring_paradigm()

    def study_repeated_imagination(
        self
    ) -> Dict[str, Any]:
        """Study repeated imagination."""
        return self._paradigm.run_repeated_imagination_study()

    def study_aging(
        self
    ) -> Dict[str, Any]:
        """Study aging effects."""
        return self._paradigm.run_aging_study()

    def study_divided_attention(
        self
    ) -> Dict[str, Any]:
        """Study divided attention."""
        return self._paradigm.run_divided_attention_study()

    def study_emotion(
        self
    ) -> Dict[str, Any]:
        """Study emotion effects."""
        return self._paradigm.run_emotional_content_study()

    # Analysis

    def get_metrics(self) -> SourceConfusionMetrics:
        """Get metrics."""
        if not self._system._attributions:
            return SourceConfusionMetrics(
                overall_accuracy=0.0,
                confusion_rate=0.0,
                by_source={},
                by_confusion_type={}
            )

        correct = sum(1 for a in self._system._attributions if a.correct)
        total = len(self._system._attributions)

        return SourceConfusionMetrics(
            overall_accuracy=correct / total,
            confusion_rate=len(self._system._confusions) / total,
            by_source={},
            by_confusion_type={}
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._system._memories),
            'attributions': len(self._system._attributions),
            'confusions': len(self._system._confusions)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_source_confusion_engine() -> SourceConfusionEngine:
    """Create source confusion engine."""
    return SourceConfusionEngine()


def demonstrate_source_confusion() -> Dict[str, Any]:
    """Demonstrate source confusion."""
    engine = create_source_confusion_engine()

    # Reality monitoring
    reality = engine.run_reality_monitoring()

    # External monitoring
    external = engine.run_external_monitoring()

    # Repeated imagination
    imagination = engine.study_repeated_imagination()

    # Aging
    aging = engine.study_aging()

    return {
        'reality_monitoring': {
            'perceived_acc': f"{reality['perceived_accuracy']:.0%}",
            'imagined_acc': f"{reality['imagined_accuracy']:.0%}",
            'confusion_rate': f"{reality['confusion_rate']:.0%}"
        },
        'external_monitoring': {
            'heard_acc': f"{external['heard_accuracy']:.0%}",
            'read_acc': f"{external['read_accuracy']:.0%}"
        },
        'repeated_imagination': {
            k: "perceived!" if v['attributed_perceived'] else "correct"
            for k, v in imagination['by_repetition'].items()
        },
        'aging': {
            k: f"acc: {v['accuracy']:.0%}"
            for k, v in aging['by_age'].items()
        },
        'interpretation': (
            f"Reality monitoring accuracy: "
            f"perceived {reality['perceived_accuracy']:.0%}, "
            f"imagined {reality['imagined_accuracy']:.0%}. "
            f"Repeated imagination increases confusion."
        )
    }


def get_source_confusion_facts() -> Dict[str, str]:
    """Get facts about source confusion."""
    return {
        'johnson_raye_1981': 'Source monitoring framework',
        'reality_monitoring': 'Distinguishing internal from external',
        'external_monitoring': 'Distinguishing sources of input',
        'features': 'Perceptual, contextual, cognitive operations',
        'repeated_imagination': 'Increases false perceived memories',
        'aging': 'Older adults show more source errors',
        'clinical': 'Impaired in schizophrenia, confabulation',
        'application': 'Eyewitness memory, false memories'
    }
