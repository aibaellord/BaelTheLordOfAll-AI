"""
BAEL Source Monitoring Engine
==============================

Memory source attribution and reality monitoring.
Johnson's Source Monitoring Framework.

"Ba'el knows where memories come from." — Ba'el
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

logger = logging.getLogger("BAEL.SourceMonitoring")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SourceType(Enum):
    """Types of memory sources."""
    PERCEIVED = auto()     # Actually experienced
    IMAGINED = auto()      # Imagined/self-generated
    HEARD = auto()         # Told by others
    READ = auto()          # From reading
    INFERRED = auto()      # Derived by reasoning
    DREAMED = auto()       # From dreams


class SourceCategory(Enum):
    """Broad source categories."""
    EXTERNAL = auto()      # From the world
    INTERNAL = auto()      # Self-generated
    MIXED = auto()         # Both external and internal


class MonitoringType(Enum):
    """Types of source monitoring."""
    EXTERNAL = auto()      # Which external source?
    INTERNAL = auto()      # Which internal source?
    REALITY = auto()       # External vs internal?


class ErrorType(Enum):
    """Types of source monitoring errors."""
    SOURCE_CONFUSION = auto()    # Wrong source within category
    REALITY_CONFUSION = auto()   # Internal confused as external
    CRYPTOMNESIA = auto()        # Forgotten source (unintentional plagiarism)
    CONFABULATION = auto()       # Filling in with imagination


@dataclass
class SourceFeatures:
    """
    Features that distinguish sources.
    """
    perceptual_detail: float      # 0-1, sensory richness
    contextual_detail: float      # 0-1, spatial/temporal context
    semantic_detail: float        # 0-1, meaning/concepts
    affective_intensity: float    # 0-1, emotional content
    cognitive_operations: float   # 0-1, thinking involved


@dataclass
class MemoryRecord:
    """
    A memory record with source information.
    """
    id: str
    content: Any
    true_source: SourceType
    features: SourceFeatures
    timestamp: float
    confidence: float = 0.7
    attributed_source: Optional[SourceType] = None


@dataclass
class Attribution:
    """
    A source attribution judgment.
    """
    memory_id: str
    attributed_source: SourceType
    confidence: float
    features_used: List[str]
    correct: bool


@dataclass
class MonitoringMetrics:
    """
    Source monitoring performance.
    """
    accuracy: float
    reality_monitoring_accuracy: float
    external_monitoring_accuracy: float
    false_memory_rate: float


# ============================================================================
# SOURCE FEATURE GENERATOR
# ============================================================================

class SourceFeatureGenerator:
    """
    Generate source-typical features.

    "Ba'el knows source signatures." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        # Typical feature profiles for each source
        self._source_profiles = {
            SourceType.PERCEIVED: SourceFeatures(
                perceptual_detail=0.9,
                contextual_detail=0.8,
                semantic_detail=0.5,
                affective_intensity=0.6,
                cognitive_operations=0.3
            ),
            SourceType.IMAGINED: SourceFeatures(
                perceptual_detail=0.4,
                contextual_detail=0.3,
                semantic_detail=0.7,
                affective_intensity=0.5,
                cognitive_operations=0.8
            ),
            SourceType.HEARD: SourceFeatures(
                perceptual_detail=0.6,
                contextual_detail=0.6,
                semantic_detail=0.7,
                affective_intensity=0.4,
                cognitive_operations=0.4
            ),
            SourceType.READ: SourceFeatures(
                perceptual_detail=0.3,
                contextual_detail=0.5,
                semantic_detail=0.9,
                affective_intensity=0.3,
                cognitive_operations=0.6
            ),
            SourceType.INFERRED: SourceFeatures(
                perceptual_detail=0.2,
                contextual_detail=0.4,
                semantic_detail=0.8,
                affective_intensity=0.3,
                cognitive_operations=0.9
            ),
            SourceType.DREAMED: SourceFeatures(
                perceptual_detail=0.6,
                contextual_detail=0.3,
                semantic_detail=0.4,
                affective_intensity=0.7,
                cognitive_operations=0.2
            )
        }

        self._lock = threading.RLock()

    def generate_features(
        self,
        source: SourceType,
        noise: float = 0.1
    ) -> SourceFeatures:
        """Generate features for a memory from given source."""
        profile = self._source_profiles.get(source, self._source_profiles[SourceType.PERCEIVED])

        # Add noise
        def add_noise(val: float) -> float:
            noisy = val + random.gauss(0, noise)
            return max(0.0, min(1.0, noisy))

        return SourceFeatures(
            perceptual_detail=add_noise(profile.perceptual_detail),
            contextual_detail=add_noise(profile.contextual_detail),
            semantic_detail=add_noise(profile.semantic_detail),
            affective_intensity=add_noise(profile.affective_intensity),
            cognitive_operations=add_noise(profile.cognitive_operations)
        )

    def get_profile(
        self,
        source: SourceType
    ) -> SourceFeatures:
        """Get typical profile for source."""
        return self._source_profiles.get(source, self._source_profiles[SourceType.PERCEIVED])


# ============================================================================
# SOURCE ATTRIBUTOR
# ============================================================================

class SourceAttributor:
    """
    Make source attribution judgments.

    "Ba'el attributes sources." — Ba'el
    """

    def __init__(
        self,
        feature_generator: SourceFeatureGenerator
    ):
        """Initialize attributor."""
        self._generator = feature_generator
        self._lock = threading.RLock()

    def attribute(
        self,
        record: MemoryRecord,
        monitoring_type: MonitoringType = MonitoringType.REALITY
    ) -> Attribution:
        """Make source attribution for memory record."""
        features = record.features

        if monitoring_type == MonitoringType.REALITY:
            source, confidence, features_used = self._reality_monitoring(features)
        elif monitoring_type == MonitoringType.EXTERNAL:
            source, confidence, features_used = self._external_monitoring(features)
        else:
            source, confidence, features_used = self._internal_monitoring(features)

        correct = source == record.true_source

        return Attribution(
            memory_id=record.id,
            attributed_source=source,
            confidence=confidence,
            features_used=features_used,
            correct=correct
        )

    def _reality_monitoring(
        self,
        features: SourceFeatures
    ) -> Tuple[SourceType, float, List[str]]:
        """Reality monitoring: external vs internal."""
        features_used = []

        # High perceptual detail suggests external
        external_score = 0.0

        if features.perceptual_detail > 0.6:
            external_score += 0.3
            features_used.append('perceptual_detail')

        if features.contextual_detail > 0.5:
            external_score += 0.2
            features_used.append('contextual_detail')

        # High cognitive operations suggests internal
        if features.cognitive_operations > 0.6:
            external_score -= 0.3
            features_used.append('cognitive_operations')

        # Low semantic detail suggests external perception
        if features.semantic_detail < 0.5:
            external_score += 0.1

        # Decide
        if external_score > 0.1:
            source = SourceType.PERCEIVED
            confidence = 0.5 + external_score
        else:
            source = SourceType.IMAGINED
            confidence = 0.5 - external_score

        return source, min(1.0, confidence), features_used

    def _external_monitoring(
        self,
        features: SourceFeatures
    ) -> Tuple[SourceType, float, List[str]]:
        """External source monitoring."""
        features_used = []

        # High perceptual suggests perceived
        if features.perceptual_detail > 0.7:
            features_used.append('perceptual_detail')
            return SourceType.PERCEIVED, 0.7, features_used

        # High semantic suggests read
        if features.semantic_detail > 0.7:
            features_used.append('semantic_detail')
            return SourceType.READ, 0.6, features_used

        # Moderate context suggests heard
        if features.contextual_detail > 0.5:
            features_used.append('contextual_detail')
            return SourceType.HEARD, 0.5, features_used

        return SourceType.PERCEIVED, 0.4, features_used

    def _internal_monitoring(
        self,
        features: SourceFeatures
    ) -> Tuple[SourceType, float, List[str]]:
        """Internal source monitoring."""
        features_used = []

        # High cognitive suggests inferred
        if features.cognitive_operations > 0.7:
            features_used.append('cognitive_operations')
            return SourceType.INFERRED, 0.7, features_used

        # High affective + perceptual suggests dreamed
        if features.affective_intensity > 0.6 and features.perceptual_detail > 0.5:
            features_used.extend(['affective_intensity', 'perceptual_detail'])
            return SourceType.DREAMED, 0.5, features_used

        return SourceType.IMAGINED, 0.6, features_used


# ============================================================================
# FALSE MEMORY GENERATOR
# ============================================================================

class FalseMemoryGenerator:
    """
    Generate false memories through source errors.

    "Ba'el understands memory illusions." — Ba'el
    """

    def __init__(
        self,
        feature_generator: SourceFeatureGenerator
    ):
        """Initialize generator."""
        self._generator = feature_generator
        self._lock = threading.RLock()

    def create_false_memory(
        self,
        original: MemoryRecord,
        error_type: ErrorType
    ) -> MemoryRecord:
        """Create false memory from original."""
        if error_type == ErrorType.SOURCE_CONFUSION:
            return self._source_confusion(original)
        elif error_type == ErrorType.REALITY_CONFUSION:
            return self._reality_confusion(original)
        elif error_type == ErrorType.CRYPTOMNESIA:
            return self._cryptomnesia(original)
        else:
            return self._confabulation(original)

    def _source_confusion(
        self,
        original: MemoryRecord
    ) -> MemoryRecord:
        """Wrong source within same category."""
        # External to different external, or internal to different internal
        if original.true_source in [SourceType.PERCEIVED, SourceType.HEARD, SourceType.READ]:
            # Pick different external source
            alternatives = [SourceType.PERCEIVED, SourceType.HEARD, SourceType.READ]
            alternatives.remove(original.true_source)
            false_source = random.choice(alternatives)
        else:
            # Pick different internal source
            alternatives = [SourceType.IMAGINED, SourceType.INFERRED, SourceType.DREAMED]
            if original.true_source in alternatives:
                alternatives.remove(original.true_source)
            false_source = random.choice(alternatives)

        return MemoryRecord(
            id=original.id + "_false",
            content=original.content,
            true_source=original.true_source,
            features=self._generator.generate_features(false_source),
            timestamp=original.timestamp,
            confidence=original.confidence * 0.9,
            attributed_source=false_source
        )

    def _reality_confusion(
        self,
        original: MemoryRecord
    ) -> MemoryRecord:
        """Internal confused as external (or vice versa)."""
        if original.true_source in [SourceType.IMAGINED, SourceType.INFERRED]:
            # Internal becomes external
            false_source = SourceType.PERCEIVED
        else:
            # External becomes internal
            false_source = SourceType.IMAGINED

        return MemoryRecord(
            id=original.id + "_reality_error",
            content=original.content,
            true_source=original.true_source,
            features=self._generator.generate_features(false_source),
            timestamp=original.timestamp,
            confidence=original.confidence * 0.8,
            attributed_source=false_source
        )

    def _cryptomnesia(
        self,
        original: MemoryRecord
    ) -> MemoryRecord:
        """Forgotten source (unintentional plagiarism)."""
        # Source features degraded, attributed to self
        features = SourceFeatures(
            perceptual_detail=original.features.perceptual_detail * 0.3,
            contextual_detail=original.features.contextual_detail * 0.2,
            semantic_detail=original.features.semantic_detail * 0.9,
            affective_intensity=original.features.affective_intensity * 0.5,
            cognitive_operations=0.8  # Seems like own thinking
        )

        return MemoryRecord(
            id=original.id + "_crypto",
            content=original.content,
            true_source=original.true_source,
            features=features,
            timestamp=original.timestamp,
            confidence=0.6,
            attributed_source=SourceType.IMAGINED  # Think it's own idea
        )

    def _confabulation(
        self,
        original: MemoryRecord
    ) -> MemoryRecord:
        """Filling in gaps with imagination."""
        # High confidence, mixed features
        features = SourceFeatures(
            perceptual_detail=0.6,
            contextual_detail=0.5,
            semantic_detail=0.7,
            affective_intensity=0.5,
            cognitive_operations=0.4
        )

        return MemoryRecord(
            id=original.id + "_confab",
            content=f"{original.content} [filled in]",
            true_source=SourceType.IMAGINED,
            features=features,
            timestamp=time.time(),
            confidence=0.8,  # Confabulations often have high confidence
            attributed_source=SourceType.PERCEIVED
        )


# ============================================================================
# SOURCE MONITORING ENGINE
# ============================================================================

class SourceMonitoringEngine:
    """
    Complete source monitoring engine.

    "Ba'el's memory attribution system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._feature_gen = SourceFeatureGenerator()
        self._attributor = SourceAttributor(self._feature_gen)
        self._false_gen = FalseMemoryGenerator(self._feature_gen)

        self._memories: Dict[str, MemoryRecord] = {}
        self._attributions: List[Attribution] = []

        self._memory_counter = 0

        self._lock = threading.RLock()

    def _generate_memory_id(self) -> str:
        self._memory_counter += 1
        return f"mem_{self._memory_counter}"

    # Memory creation

    def encode_memory(
        self,
        content: Any,
        source: SourceType,
        confidence: float = 0.7
    ) -> MemoryRecord:
        """Encode a new memory with source."""
        features = self._feature_gen.generate_features(source)

        record = MemoryRecord(
            id=self._generate_memory_id(),
            content=content,
            true_source=source,
            features=features,
            timestamp=time.time(),
            confidence=confidence
        )

        self._memories[record.id] = record
        return record

    def encode_perceived(
        self,
        content: Any
    ) -> MemoryRecord:
        """Encode a perceived (experienced) memory."""
        return self.encode_memory(content, SourceType.PERCEIVED)

    def encode_imagined(
        self,
        content: Any
    ) -> MemoryRecord:
        """Encode an imagined memory."""
        return self.encode_memory(content, SourceType.IMAGINED)

    def encode_heard(
        self,
        content: Any,
        from_whom: str = "someone"
    ) -> MemoryRecord:
        """Encode something heard from another."""
        return self.encode_memory(f"{content} (from {from_whom})", SourceType.HEARD)

    # Source attribution

    def attribute_source(
        self,
        memory_id: str,
        monitoring_type: MonitoringType = MonitoringType.REALITY
    ) -> Attribution:
        """Attribute source of memory."""
        if memory_id not in self._memories:
            raise ValueError(f"Memory {memory_id} not found")

        record = self._memories[memory_id]
        attribution = self._attributor.attribute(record, monitoring_type)

        # Update memory with attribution
        record.attributed_source = attribution.attributed_source

        self._attributions.append(attribution)
        return attribution

    def reality_check(
        self,
        memory_id: str
    ) -> Tuple[bool, float]:
        """Check if memory is from external reality."""
        attribution = self.attribute_source(memory_id, MonitoringType.REALITY)

        is_external = attribution.attributed_source in [
            SourceType.PERCEIVED, SourceType.HEARD, SourceType.READ
        ]

        return is_external, attribution.confidence

    # False memories

    def create_false_memory(
        self,
        original_id: str,
        error_type: ErrorType
    ) -> MemoryRecord:
        """Create false memory from existing memory."""
        if original_id not in self._memories:
            raise ValueError(f"Memory {original_id} not found")

        original = self._memories[original_id]
        false_memory = self._false_gen.create_false_memory(original, error_type)

        self._memories[false_memory.id] = false_memory
        return false_memory

    # Analysis

    def get_source_category(
        self,
        source: SourceType
    ) -> SourceCategory:
        """Get broad category for source type."""
        if source in [SourceType.PERCEIVED, SourceType.HEARD, SourceType.READ]:
            return SourceCategory.EXTERNAL
        elif source in [SourceType.IMAGINED, SourceType.INFERRED, SourceType.DREAMED]:
            return SourceCategory.INTERNAL
        return SourceCategory.MIXED

    def get_source_profile(
        self,
        source: SourceType
    ) -> SourceFeatures:
        """Get typical feature profile for source."""
        return self._feature_gen.get_profile(source)

    # Metrics

    def get_metrics(self) -> MonitoringMetrics:
        """Get monitoring performance metrics."""
        if not self._attributions:
            return MonitoringMetrics(
                accuracy=0.0,
                reality_monitoring_accuracy=0.0,
                external_monitoring_accuracy=0.0,
                false_memory_rate=0.0
            )

        correct = sum(1 for a in self._attributions if a.correct)
        accuracy = correct / len(self._attributions)

        # Reality monitoring accuracy (external vs internal)
        reality_correct = 0
        reality_total = 0
        for a in self._attributions:
            mem = self._memories.get(a.memory_id)
            if mem:
                true_cat = self.get_source_category(mem.true_source)
                attr_cat = self.get_source_category(a.attributed_source)
                reality_total += 1
                if true_cat == attr_cat:
                    reality_correct += 1

        reality_accuracy = reality_correct / reality_total if reality_total > 0 else 0.0

        # False memory rate
        false_count = sum(
            1 for m in self._memories.values()
            if m.attributed_source and m.attributed_source != m.true_source
        )
        false_rate = false_count / len(self._memories) if self._memories else 0.0

        return MonitoringMetrics(
            accuracy=accuracy,
            reality_monitoring_accuracy=reality_accuracy,
            external_monitoring_accuracy=accuracy,  # Simplified
            false_memory_rate=false_rate
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._memories),
            'attributions': len(self._attributions)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_source_monitoring_engine() -> SourceMonitoringEngine:
    """Create source monitoring engine."""
    return SourceMonitoringEngine()


def demonstrate_source_confusion() -> Dict[str, Any]:
    """Demonstrate source monitoring error."""
    engine = create_source_monitoring_engine()

    # Encode a perceived memory
    original = engine.encode_perceived("I saw the suspect at the store")

    # Create source confusion
    false_mem = engine.create_false_memory(original.id, ErrorType.SOURCE_CONFUSION)

    # Attribute sources
    orig_attr = engine.attribute_source(original.id)
    false_attr = engine.attribute_source(false_mem.id)

    return {
        'original': {
            'true_source': original.true_source.name,
            'attributed': orig_attr.attributed_source.name,
            'correct': orig_attr.correct
        },
        'false_memory': {
            'true_source': false_mem.true_source.name,
            'attributed': false_attr.attributed_source.name,
            'correct': false_attr.correct
        }
    }


def get_source_monitoring_facts() -> Dict[str, str]:
    """Get facts about source monitoring."""
    return {
        'johnson_1993': 'Source Monitoring Framework by Johnson, Hashtroudi & Lindsay',
        'reality_monitoring': 'Distinguishing perceived events from imagined events',
        'external_monitoring': 'Distinguishing between external sources (who said it?)',
        'internal_monitoring': 'Distinguishing between internal sources (did I say or think it?)',
        'features': 'Perceptual, contextual, semantic, affective, and cognitive operation details',
        'aging': 'Source monitoring declines more with age than recognition memory',
        'cryptomnesia': 'Forgetting the source leads to unintentional plagiarism'
    }
