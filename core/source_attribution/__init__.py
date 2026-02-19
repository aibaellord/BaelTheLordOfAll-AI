"""
BAEL Source Attribution Engine
=================================

Reality monitoring and source memory.
Johnson's MEM framework.

"Ba'el knows where knowledge comes from." — Ba'el
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

logger = logging.getLogger("BAEL.SourceAttribution")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SourceType(Enum):
    """Types of memory sources."""
    EXTERNAL = auto()          # Perceived from environment
    INTERNAL = auto()          # Self-generated
    IMAGINED = auto()          # Imagined
    DREAMED = auto()           # From dreams
    SUGGESTED = auto()         # From suggestion
    INFERRED = auto()          # Inferred/deduced


class ExternalSource(Enum):
    """External source subtypes."""
    VISUAL = auto()
    AUDITORY = auto()
    PERSON_A = auto()
    PERSON_B = auto()
    TEXT = auto()
    VIDEO = auto()


class InternalSource(Enum):
    """Internal source subtypes."""
    THOUGHT = auto()
    SAID = auto()
    IMAGINED = auto()
    PLANNED = auto()
    DREAMED = auto()


class QualityDimension(Enum):
    """Memory quality dimensions (MEM)."""
    PERCEPTUAL = auto()        # Sensory detail
    CONTEXTUAL = auto()        # Time, place
    SEMANTIC = auto()          # Meaning
    AFFECTIVE = auto()         # Emotional
    COGNITIVE = auto()         # Thought processes


class AttributionError(Enum):
    """Types of source attribution errors."""
    REALITY_CONFUSION = auto()      # Internal vs external
    SOURCE_CONFUSION = auto()       # External source A vs B
    CRYPTOMNESIA = auto()           # Others' ideas as own
    FALSE_MEMORY = auto()           # Imagined as real


@dataclass
class MemoryQuality:
    """
    Memory quality on MEM dimensions.
    """
    perceptual_detail: float      # Sensory richness
    contextual_detail: float      # Spatiotemporal info
    semantic_detail: float        # Meaning content
    affective_intensity: float    # Emotional weight
    cognitive_operations: float   # Thought processes


@dataclass
class SourcedMemory:
    """
    A memory with source information.
    """
    id: str
    content: str
    actual_source: SourceType
    actual_subsource: Optional[str]
    quality: MemoryQuality
    encoding_time: float


@dataclass
class SourceJudgment:
    """
    A source attribution judgment.
    """
    memory_id: str
    attributed_source: SourceType
    attributed_subsource: Optional[str]
    confidence: float
    correct: bool
    error_type: Optional[AttributionError]


@dataclass
class SourceMetrics:
    """
    Source attribution metrics.
    """
    overall_accuracy: float
    reality_monitoring_accuracy: float
    external_source_accuracy: float
    internal_source_accuracy: float
    false_memory_rate: float


# ============================================================================
# MEM FRAMEWORK
# ============================================================================

class MEMFramework:
    """
    Johnson's Multiple-Entry Modular (MEM) framework.

    "Ba'el's reality monitoring." — Ba'el
    """

    def __init__(self):
        """Initialize MEM framework."""
        # Typical quality profiles by source
        self._source_profiles: Dict[SourceType, MemoryQuality] = {
            SourceType.EXTERNAL: MemoryQuality(
                perceptual_detail=0.8,
                contextual_detail=0.7,
                semantic_detail=0.6,
                affective_intensity=0.5,
                cognitive_operations=0.3
            ),
            SourceType.INTERNAL: MemoryQuality(
                perceptual_detail=0.3,
                contextual_detail=0.4,
                semantic_detail=0.7,
                affective_intensity=0.6,
                cognitive_operations=0.8
            ),
            SourceType.IMAGINED: MemoryQuality(
                perceptual_detail=0.5,
                contextual_detail=0.3,
                semantic_detail=0.5,
                affective_intensity=0.7,
                cognitive_operations=0.7
            )
        }

        self._lock = threading.RLock()

    def calculate_source_likelihood(
        self,
        quality: MemoryQuality,
        source: SourceType
    ) -> float:
        """Calculate likelihood that memory is from source."""
        profile = self._source_profiles.get(source)
        if not profile:
            return 0.5

        # Compare quality to typical profile
        differences = []

        differences.append(abs(quality.perceptual_detail - profile.perceptual_detail))
        differences.append(abs(quality.contextual_detail - profile.contextual_detail))
        differences.append(abs(quality.semantic_detail - profile.semantic_detail))
        differences.append(abs(quality.affective_intensity - profile.affective_intensity))
        differences.append(abs(quality.cognitive_operations - profile.cognitive_operations))

        avg_diff = sum(differences) / len(differences)

        # Convert to likelihood
        likelihood = 1 - avg_diff
        return likelihood

    def infer_source(
        self,
        quality: MemoryQuality
    ) -> Tuple[SourceType, float]:
        """Infer most likely source from quality."""
        likelihoods = {}

        for source in [SourceType.EXTERNAL, SourceType.INTERNAL, SourceType.IMAGINED]:
            likelihoods[source] = self.calculate_source_likelihood(quality, source)

        best_source = max(likelihoods, key=likelihoods.get)
        confidence = likelihoods[best_source]

        return best_source, confidence

    def is_reality_monitoring_difficult(
        self,
        quality: MemoryQuality
    ) -> bool:
        """Check if reality monitoring is difficult for this memory."""
        # High perceptual detail in imagined = confusion risk
        external_like = self.calculate_source_likelihood(quality, SourceType.EXTERNAL)
        internal_like = self.calculate_source_likelihood(quality, SourceType.INTERNAL)

        # Similar likelihoods = difficult
        return abs(external_like - internal_like) < 0.2


# ============================================================================
# SOURCE MEMORY STORE
# ============================================================================

class SourceMemoryStore:
    """
    Memory store with source tracking.

    "Ba'el's sourced knowledge." — Ba'el
    """

    def __init__(self):
        """Initialize store."""
        self._memories: Dict[str, SourcedMemory] = {}
        self._memory_counter = 0

        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._memory_counter += 1
        return f"smem_{self._memory_counter}"

    def encode_memory(
        self,
        content: str,
        source: SourceType,
        subsource: str = None,
        quality: MemoryQuality = None
    ) -> SourcedMemory:
        """Encode a memory with source."""
        if quality is None:
            # Generate quality based on source type
            quality = self._generate_quality(source)

        memory = SourcedMemory(
            id=self._generate_id(),
            content=content,
            actual_source=source,
            actual_subsource=subsource,
            quality=quality,
            encoding_time=time.time()
        )

        self._memories[memory.id] = memory
        return memory

    def _generate_quality(
        self,
        source: SourceType
    ) -> MemoryQuality:
        """Generate typical quality for source."""
        if source == SourceType.EXTERNAL:
            return MemoryQuality(
                perceptual_detail=0.7 + random.uniform(-0.2, 0.2),
                contextual_detail=0.6 + random.uniform(-0.2, 0.2),
                semantic_detail=0.5 + random.uniform(-0.2, 0.2),
                affective_intensity=0.4 + random.uniform(-0.2, 0.2),
                cognitive_operations=0.3 + random.uniform(-0.1, 0.1)
            )
        elif source == SourceType.INTERNAL:
            return MemoryQuality(
                perceptual_detail=0.3 + random.uniform(-0.1, 0.1),
                contextual_detail=0.4 + random.uniform(-0.2, 0.2),
                semantic_detail=0.7 + random.uniform(-0.2, 0.2),
                affective_intensity=0.5 + random.uniform(-0.2, 0.2),
                cognitive_operations=0.8 + random.uniform(-0.2, 0.2)
            )
        else:
            return MemoryQuality(
                perceptual_detail=0.5 + random.uniform(-0.2, 0.2),
                contextual_detail=0.4 + random.uniform(-0.2, 0.2),
                semantic_detail=0.5 + random.uniform(-0.2, 0.2),
                affective_intensity=0.6 + random.uniform(-0.2, 0.2),
                cognitive_operations=0.6 + random.uniform(-0.2, 0.2)
            )

    def get_memory(
        self,
        memory_id: str
    ) -> Optional[SourcedMemory]:
        """Get a memory."""
        return self._memories.get(memory_id)

    def get_memories_by_source(
        self,
        source: SourceType
    ) -> List[SourcedMemory]:
        """Get memories by source."""
        return [
            m for m in self._memories.values()
            if m.actual_source == source
        ]


# ============================================================================
# SOURCE ATTRIBUTION ENGINE
# ============================================================================

class SourceAttributionEngine:
    """
    Complete source attribution engine.

    "Ba'el's source monitoring." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._store = SourceMemoryStore()
        self._mem = MEMFramework()

        self._judgments: List[SourceJudgment] = []

        self._lock = threading.RLock()

    # Memory encoding

    def encode_external_memory(
        self,
        content: str,
        subsource: str = None
    ) -> SourcedMemory:
        """Encode an external memory."""
        return self._store.encode_memory(
            content, SourceType.EXTERNAL, subsource
        )

    def encode_internal_memory(
        self,
        content: str,
        subsource: str = None
    ) -> SourcedMemory:
        """Encode an internal memory."""
        return self._store.encode_memory(
            content, SourceType.INTERNAL, subsource
        )

    def encode_imagined_memory(
        self,
        content: str
    ) -> SourcedMemory:
        """Encode an imagined memory."""
        return self._store.encode_memory(
            content, SourceType.IMAGINED
        )

    def encode_with_quality(
        self,
        content: str,
        source: SourceType,
        quality: MemoryQuality,
        subsource: str = None
    ) -> SourcedMemory:
        """Encode with specific quality."""
        return self._store.encode_memory(
            content, source, subsource, quality
        )

    # Source judgment

    def judge_source(
        self,
        memory_id: str
    ) -> SourceJudgment:
        """Make source attribution judgment."""
        memory = self._store.get_memory(memory_id)
        if not memory:
            return None

        # Use MEM to infer source
        inferred_source, confidence = self._mem.infer_source(memory.quality)

        # Check correctness
        correct = inferred_source == memory.actual_source

        # Determine error type if wrong
        error_type = None
        if not correct:
            if memory.actual_source == SourceType.EXTERNAL and inferred_source in [SourceType.INTERNAL, SourceType.IMAGINED]:
                error_type = AttributionError.REALITY_CONFUSION
            elif memory.actual_source in [SourceType.INTERNAL, SourceType.IMAGINED] and inferred_source == SourceType.EXTERNAL:
                error_type = AttributionError.REALITY_CONFUSION
            elif memory.actual_source == SourceType.IMAGINED and inferred_source == SourceType.EXTERNAL:
                error_type = AttributionError.FALSE_MEMORY

        judgment = SourceJudgment(
            memory_id=memory_id,
            attributed_source=inferred_source,
            attributed_subsource=None,
            confidence=confidence,
            correct=correct,
            error_type=error_type
        )

        self._judgments.append(judgment)
        return judgment

    def judge_external_source(
        self,
        memory_id: str,
        possible_sources: List[str]
    ) -> SourceJudgment:
        """Judge which external source."""
        memory = self._store.get_memory(memory_id)
        if not memory or memory.actual_source != SourceType.EXTERNAL:
            return None

        # Random choice weighted by confidence
        # (In reality, would use contextual cues)
        if memory.actual_subsource in possible_sources:
            # Correct answer exists
            correct_prob = 0.6 + memory.quality.contextual_detail * 0.3
            if random.random() < correct_prob:
                attributed = memory.actual_subsource
            else:
                attributed = random.choice(possible_sources)
        else:
            attributed = random.choice(possible_sources)

        correct = attributed == memory.actual_subsource

        judgment = SourceJudgment(
            memory_id=memory_id,
            attributed_source=SourceType.EXTERNAL,
            attributed_subsource=attributed,
            confidence=memory.quality.contextual_detail,
            correct=correct,
            error_type=AttributionError.SOURCE_CONFUSION if not correct else None
        )

        self._judgments.append(judgment)
        return judgment

    # Reality monitoring

    def reality_monitoring_test(
        self,
        memory_id: str
    ) -> Dict[str, Any]:
        """Test reality monitoring for a memory."""
        memory = self._store.get_memory(memory_id)
        if not memory:
            return None

        # Is this memory from external reality or internal?
        difficulty = self._mem.is_reality_monitoring_difficult(memory.quality)

        judgment = self.judge_source(memory_id)

        return {
            'actual_source': memory.actual_source.name,
            'attributed_source': judgment.attributed_source.name,
            'correct': judgment.correct,
            'difficulty': 'high' if difficulty else 'low',
            'confidence': judgment.confidence,
            'error_type': judgment.error_type.name if judgment.error_type else None
        }

    # False memory creation

    def create_false_memory_risk(
        self,
        imagined_content: str,
        repetitions: int = 3
    ) -> SourcedMemory:
        """Create imagined memory with false memory risk."""
        # Repeated imagination increases perceptual detail
        # making it harder to distinguish from real

        base_quality = MemoryQuality(
            perceptual_detail=0.4,
            contextual_detail=0.3,
            semantic_detail=0.6,
            affective_intensity=0.5,
            cognitive_operations=0.7
        )

        # Each repetition increases perceptual detail
        perceptual = min(0.9, base_quality.perceptual_detail + repetitions * 0.1)

        inflated_quality = MemoryQuality(
            perceptual_detail=perceptual,
            contextual_detail=base_quality.contextual_detail + repetitions * 0.05,
            semantic_detail=base_quality.semantic_detail,
            affective_intensity=base_quality.affective_intensity + repetitions * 0.05,
            cognitive_operations=max(0.3, base_quality.cognitive_operations - repetitions * 0.1)
        )

        return self.encode_with_quality(
            imagined_content,
            SourceType.IMAGINED,
            inflated_quality
        )

    # Analysis

    def get_metrics(self) -> SourceMetrics:
        """Get source attribution metrics."""
        if not self._judgments:
            return SourceMetrics(
                overall_accuracy=0.0,
                reality_monitoring_accuracy=0.0,
                external_source_accuracy=0.0,
                internal_source_accuracy=0.0,
                false_memory_rate=0.0
            )

        overall = sum(1 for j in self._judgments if j.correct) / len(self._judgments)

        # Reality monitoring: external vs internal
        rm_judgments = [
            j for j in self._judgments
            if self._store.get_memory(j.memory_id).actual_source in [SourceType.EXTERNAL, SourceType.INTERNAL]
        ]
        rm_accuracy = sum(1 for j in rm_judgments if j.correct) / len(rm_judgments) if rm_judgments else 0.0

        # External source accuracy
        ext_judgments = [
            j for j in self._judgments
            if self._store.get_memory(j.memory_id).actual_source == SourceType.EXTERNAL
        ]
        ext_accuracy = sum(1 for j in ext_judgments if j.correct) / len(ext_judgments) if ext_judgments else 0.0

        # Internal source accuracy
        int_judgments = [
            j for j in self._judgments
            if self._store.get_memory(j.memory_id).actual_source == SourceType.INTERNAL
        ]
        int_accuracy = sum(1 for j in int_judgments if j.correct) / len(int_judgments) if int_judgments else 0.0

        # False memory rate
        false_memories = sum(
            1 for j in self._judgments
            if j.error_type == AttributionError.FALSE_MEMORY
        )
        false_memory_rate = false_memories / len(self._judgments)

        return SourceMetrics(
            overall_accuracy=overall,
            reality_monitoring_accuracy=rm_accuracy,
            external_source_accuracy=ext_accuracy,
            internal_source_accuracy=int_accuracy,
            false_memory_rate=false_memory_rate
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'memories': len(self._store._memories),
            'judgments': len(self._judgments),
            'external_memories': len(self._store.get_memories_by_source(SourceType.EXTERNAL)),
            'internal_memories': len(self._store.get_memories_by_source(SourceType.INTERNAL)),
            'imagined_memories': len(self._store.get_memories_by_source(SourceType.IMAGINED))
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_source_attribution_engine() -> SourceAttributionEngine:
    """Create source attribution engine."""
    return SourceAttributionEngine()


def demonstrate_source_attribution() -> Dict[str, Any]:
    """Demonstrate source attribution."""
    engine = create_source_attribution_engine()

    # Encode various memories
    ext1 = engine.encode_external_memory("The news said it would rain", "TV")
    ext2 = engine.encode_external_memory("John told me about the meeting", "John")
    int1 = engine.encode_internal_memory("I thought about calling mom")
    int2 = engine.encode_internal_memory("I planned to buy groceries")
    img1 = engine.encode_imagined_memory("Imagined winning the lottery")

    # Create false memory risk
    false_risk = engine.create_false_memory_risk(
        "Imagined shaking hands with celebrity",
        repetitions=5
    )

    # Judge sources
    results = []
    for mem in [ext1, ext2, int1, int2, img1, false_risk]:
        test = engine.reality_monitoring_test(mem.id)
        results.append(test)

    metrics = engine.get_metrics()

    return {
        'reality_monitoring_tests': results,
        'overall_accuracy': metrics.overall_accuracy,
        'reality_monitoring_accuracy': metrics.reality_monitoring_accuracy,
        'false_memory_rate': metrics.false_memory_rate,
        'interpretation': (
            f"Overall accuracy: {metrics.overall_accuracy:.0%}, "
            f"False memory risk demonstrated"
        )
    }


def get_source_attribution_facts() -> Dict[str, str]:
    """Get facts about source attribution."""
    return {
        'johnson_mem': 'Multiple-Entry Modular framework for reality monitoring',
        'reality_monitoring': 'Distinguishing external from internal sources',
        'source_monitoring': 'Identifying specific source within category',
        'perceptual_detail': 'External memories have more sensory detail',
        'cognitive_operations': 'Internal memories have more thought records',
        'false_memories': 'Imagined events can be confused with real ones',
        'cryptomnesia': 'Unconscious plagiarism from forgotten sources',
        'age_effects': 'Source memory declines more than item memory with age'
    }
