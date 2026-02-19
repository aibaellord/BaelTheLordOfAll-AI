"""
BAEL Episodic Buffer Engine
============================

Baddeley's episodic buffer component.
Multimodal integration and binding.

"Ba'el binds all experience." — Ba'el
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

logger = logging.getLogger("BAEL.EpisodicBuffer")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class ModalityType(Enum):
    """Types of modalities."""
    VERBAL = auto()
    VISUAL = auto()
    SPATIAL = auto()
    SEMANTIC = auto()
    TEMPORAL = auto()


class ChunkType(Enum):
    """Types of integrated chunks."""
    SIMPLE = auto()        # Single modality
    BOUND = auto()         # Multi-modal binding
    NARRATIVE = auto()     # Temporal sequence
    SCHEMA = auto()        # Knowledge-enhanced


class AccessType(Enum):
    """Types of memory access."""
    PERCEPTION = auto()    # From sensory input
    RETRIEVAL = auto()     # From long-term memory
    GENERATION = auto()    # From imagination


@dataclass
class ModalContent:
    """
    Content from a single modality.
    """
    modality: ModalityType
    content: Any
    strength: float = 1.0


@dataclass
class EpisodicChunk:
    """
    A chunk in the episodic buffer.
    """
    id: str
    contents: List[ModalContent]
    chunk_type: ChunkType
    binding_strength: float
    temporal_order: int
    creation_time: float
    access_count: int = 0


@dataclass
class Episode:
    """
    A complete episode.
    """
    id: str
    chunks: List[EpisodicChunk]
    narrative_coherence: float
    duration_estimate: float


@dataclass
class IntegrationResult:
    """
    Result of integration operation.
    """
    chunk: EpisodicChunk
    modalities_integrated: int
    binding_quality: float
    ltm_contribution: float


@dataclass
class EpisodicBufferMetrics:
    """
    Episodic buffer metrics.
    """
    capacity: int
    binding_accuracy: float
    ltm_integration: float
    narrative_coherence: float


# ============================================================================
# BINDING MECHANISM
# ============================================================================

class BindingMechanism:
    """
    Bind information across modalities.

    "Ba'el weaves experience." — Ba'el
    """

    def __init__(self):
        """Initialize mechanism."""
        self._lock = threading.RLock()

    def calculate_binding_strength(
        self,
        contents: List[ModalContent]
    ) -> float:
        """Calculate binding strength for multimodal content."""
        if len(contents) <= 1:
            return 1.0

        # More modalities = harder to bind
        base_strength = 1.0 - (len(contents) - 1) * 0.1

        # Average content strength
        avg_strength = sum(c.strength for c in contents) / len(contents)

        # Coherence bonus for related content
        coherence = self._estimate_coherence(contents)

        return min(1.0, base_strength * avg_strength * (1 + coherence * 0.2))

    def _estimate_coherence(
        self,
        contents: List[ModalContent]
    ) -> float:
        """Estimate coherence between contents."""
        # Simplified - real coherence would check semantic relations
        modalities = set(c.modality for c in contents)

        # Verbal + semantic = high coherence
        if {ModalityType.VERBAL, ModalityType.SEMANTIC}.issubset(modalities):
            return 0.8

        # Visual + spatial = high coherence
        if {ModalityType.VISUAL, ModalityType.SPATIAL}.issubset(modalities):
            return 0.7

        return 0.5

    def bind(
        self,
        contents: List[ModalContent],
        chunk_id: str,
        temporal_order: int
    ) -> EpisodicChunk:
        """Create a bound chunk."""
        binding_strength = self.calculate_binding_strength(contents)

        chunk_type = ChunkType.SIMPLE if len(contents) == 1 else ChunkType.BOUND

        return EpisodicChunk(
            id=chunk_id,
            contents=contents,
            chunk_type=chunk_type,
            binding_strength=binding_strength,
            temporal_order=temporal_order,
            creation_time=time.time()
        )

    def rebind(
        self,
        chunk: EpisodicChunk,
        new_content: ModalContent
    ) -> EpisodicChunk:
        """Add new content to existing chunk."""
        chunk.contents.append(new_content)
        chunk.binding_strength = self.calculate_binding_strength(chunk.contents)
        chunk.chunk_type = ChunkType.BOUND
        return chunk


# ============================================================================
# LTM INTERFACE
# ============================================================================

class LTMInterface:
    """
    Interface with long-term memory.

    "Ba'el retrieves wisdom." — Ba'el
    """

    def __init__(self):
        """Initialize interface."""
        # Simulated LTM
        self._semantic_store: Dict[str, Any] = {
            'dog': {'category': 'animal', 'features': ['fur', 'barks', 'four_legs']},
            'cat': {'category': 'animal', 'features': ['fur', 'meows', 'four_legs']},
            'car': {'category': 'vehicle', 'features': ['wheels', 'engine', 'drives']},
        }

        self._episodic_store: List[Episode] = []
        self._lock = threading.RLock()

    def retrieve_semantic(
        self,
        cue: str
    ) -> Optional[ModalContent]:
        """Retrieve semantic information."""
        if cue.lower() in self._semantic_store:
            content = self._semantic_store[cue.lower()]
            return ModalContent(
                modality=ModalityType.SEMANTIC,
                content=content,
                strength=0.8
            )
        return None

    def retrieve_episodic(
        self,
        cue: str
    ) -> List[Episode]:
        """Retrieve relevant episodes."""
        # Simplified cue-based retrieval
        relevant = []
        for episode in self._episodic_store:
            for chunk in episode.chunks:
                for content in chunk.contents:
                    if cue.lower() in str(content.content).lower():
                        relevant.append(episode)
                        break
        return relevant

    def store_episode(
        self,
        episode: Episode
    ) -> None:
        """Store episode to LTM."""
        self._episodic_store.append(episode)

    def enhance_with_schema(
        self,
        chunk: EpisodicChunk
    ) -> EpisodicChunk:
        """Enhance chunk with schematic knowledge."""
        for content in chunk.contents:
            if content.modality == ModalityType.VERBAL:
                semantic = self.retrieve_semantic(str(content.content))
                if semantic:
                    chunk.contents.append(semantic)
                    chunk.chunk_type = ChunkType.SCHEMA
                    chunk.binding_strength *= 1.2  # Schema bonus

        return chunk


# ============================================================================
# EPISODIC BUFFER ENGINE
# ============================================================================

class EpisodicBufferEngine:
    """
    Complete episodic buffer engine.

    "Ba'el's experience integrator." — Ba'el
    """

    def __init__(
        self,
        capacity: int = 4
    ):
        """Initialize engine."""
        self._binding = BindingMechanism()
        self._ltm = LTMInterface()

        self._buffer: Dict[str, EpisodicChunk] = {}
        self._capacity = capacity
        self._temporal_counter = 0
        self._chunk_counter = 0

        self._episodes: List[Episode] = []
        self._integration_results: List[IntegrationResult] = []

        self._lock = threading.RLock()

    def _generate_chunk_id(self) -> str:
        self._chunk_counter += 1
        return f"chunk_{self._chunk_counter}"

    # Buffer operations

    def add_content(
        self,
        modality: ModalityType,
        content: Any,
        strength: float = 1.0
    ) -> EpisodicChunk:
        """Add single-modality content to buffer."""
        modal_content = ModalContent(
            modality=modality,
            content=content,
            strength=strength
        )

        self._temporal_counter += 1

        chunk = self._binding.bind(
            [modal_content],
            self._generate_chunk_id(),
            self._temporal_counter
        )

        self._manage_capacity()
        self._buffer[chunk.id] = chunk

        return chunk

    def integrate(
        self,
        contents: List[Tuple[ModalityType, Any]]
    ) -> IntegrationResult:
        """Integrate multimodal content."""
        modal_contents = [
            ModalContent(modality=m, content=c)
            for m, c in contents
        ]

        self._temporal_counter += 1

        chunk = self._binding.bind(
            modal_contents,
            self._generate_chunk_id(),
            self._temporal_counter
        )

        # Try to enhance with LTM
        original_binding = chunk.binding_strength
        chunk = self._ltm.enhance_with_schema(chunk)
        ltm_contribution = chunk.binding_strength - original_binding

        self._manage_capacity()
        self._buffer[chunk.id] = chunk

        result = IntegrationResult(
            chunk=chunk,
            modalities_integrated=len(contents),
            binding_quality=chunk.binding_strength,
            ltm_contribution=max(0, ltm_contribution)
        )

        self._integration_results.append(result)
        return result

    def _manage_capacity(self) -> None:
        """Manage buffer capacity."""
        while len(self._buffer) >= self._capacity:
            # Remove oldest with weakest binding
            oldest = min(
                self._buffer.values(),
                key=lambda c: (c.binding_strength, -c.temporal_order)
            )
            del self._buffer[oldest.id]

    # Binding operations

    def bind_chunks(
        self,
        chunk_ids: List[str]
    ) -> Optional[EpisodicChunk]:
        """Bind multiple chunks together."""
        chunks = [
            self._buffer[cid] for cid in chunk_ids
            if cid in self._buffer
        ]

        if not chunks:
            return None

        # Combine all contents
        all_contents = []
        for chunk in chunks:
            all_contents.extend(chunk.contents)

        self._temporal_counter += 1

        combined = self._binding.bind(
            all_contents,
            self._generate_chunk_id(),
            self._temporal_counter
        )
        combined.chunk_type = ChunkType.NARRATIVE

        # Remove old chunks
        for cid in chunk_ids:
            if cid in self._buffer:
                del self._buffer[cid]

        self._buffer[combined.id] = combined
        return combined

    # LTM interaction

    def retrieve_and_integrate(
        self,
        cue: str,
        current_content: ModalContent = None
    ) -> Optional[EpisodicChunk]:
        """Retrieve from LTM and integrate with current content."""
        semantic = self._ltm.retrieve_semantic(cue)

        if not semantic:
            return None

        contents = [semantic]
        if current_content:
            contents.append(current_content)

        self._temporal_counter += 1

        chunk = self._binding.bind(
            contents,
            self._generate_chunk_id(),
            self._temporal_counter
        )
        chunk.chunk_type = ChunkType.SCHEMA

        self._manage_capacity()
        self._buffer[chunk.id] = chunk

        return chunk

    def consolidate_episode(self) -> Episode:
        """Consolidate buffer contents as episode."""
        chunks = sorted(
            self._buffer.values(),
            key=lambda c: c.temporal_order
        )

        # Calculate narrative coherence
        if len(chunks) > 1:
            coherence_sum = sum(
                self._calculate_chunk_similarity(chunks[i], chunks[i + 1])
                for i in range(len(chunks) - 1)
            )
            coherence = coherence_sum / (len(chunks) - 1)
        else:
            coherence = 1.0

        episode = Episode(
            id=f"episode_{len(self._episodes) + 1}",
            chunks=list(chunks),
            narrative_coherence=coherence,
            duration_estimate=len(chunks) * 2.0  # Rough estimate
        )

        self._episodes.append(episode)
        self._ltm.store_episode(episode)

        return episode

    def _calculate_chunk_similarity(
        self,
        chunk1: EpisodicChunk,
        chunk2: EpisodicChunk
    ) -> float:
        """Calculate similarity between chunks."""
        # Check modality overlap
        mods1 = set(c.modality for c in chunk1.contents)
        mods2 = set(c.modality for c in chunk2.contents)

        overlap = len(mods1 & mods2) / len(mods1 | mods2)

        # Temporal proximity bonus
        temporal_dist = abs(chunk1.temporal_order - chunk2.temporal_order)
        proximity = 1.0 / (1 + temporal_dist)

        return (overlap + proximity) / 2

    # Access and retrieval

    def access_chunk(
        self,
        chunk_id: str
    ) -> Optional[EpisodicChunk]:
        """Access a chunk (increases access count)."""
        if chunk_id in self._buffer:
            self._buffer[chunk_id].access_count += 1
            return self._buffer[chunk_id]
        return None

    def get_buffer_contents(self) -> List[EpisodicChunk]:
        """Get all buffer contents."""
        return list(self._buffer.values())

    # Sentence processing (prose memory)

    def process_sentence(
        self,
        sentence: str
    ) -> EpisodicChunk:
        """Process a sentence (integrating verbal and semantic)."""
        words = sentence.split()

        # Verbal representation
        verbal = ModalContent(
            modality=ModalityType.VERBAL,
            content=sentence,
            strength=1.0
        )

        contents = [verbal]

        # Add semantic content for key words
        for word in words[:3]:  # First few words
            semantic = self._ltm.retrieve_semantic(word)
            if semantic:
                contents.append(semantic)

        self._temporal_counter += 1

        chunk = self._binding.bind(
            contents,
            self._generate_chunk_id(),
            self._temporal_counter
        )

        if len(contents) > 1:
            chunk.chunk_type = ChunkType.SCHEMA

        self._manage_capacity()
        self._buffer[chunk.id] = chunk

        return chunk

    # Metrics

    def get_metrics(self) -> EpisodicBufferMetrics:
        """Get episodic buffer metrics."""
        chunks = list(self._buffer.values())

        if not chunks:
            return EpisodicBufferMetrics(
                capacity=self._capacity,
                binding_accuracy=0.0,
                ltm_integration=0.0,
                narrative_coherence=0.0
            )

        # Binding accuracy
        avg_binding = sum(c.binding_strength for c in chunks) / len(chunks)

        # LTM integration
        schema_chunks = sum(1 for c in chunks if c.chunk_type == ChunkType.SCHEMA)
        ltm_integration = schema_chunks / len(chunks)

        # Narrative coherence from integration results
        if self._integration_results:
            avg_quality = sum(
                r.binding_quality for r in self._integration_results
            ) / len(self._integration_results)
        else:
            avg_quality = 0.5

        return EpisodicBufferMetrics(
            capacity=self._capacity,
            binding_accuracy=avg_binding,
            ltm_integration=ltm_integration,
            narrative_coherence=avg_quality
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'buffer_size': len(self._buffer),
            'capacity': self._capacity,
            'episodes_created': len(self._episodes),
            'integrations': len(self._integration_results)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_episodic_buffer_engine(
    capacity: int = 4
) -> EpisodicBufferEngine:
    """Create episodic buffer engine."""
    return EpisodicBufferEngine(capacity=capacity)


def demonstrate_episodic_buffer() -> Dict[str, Any]:
    """Demonstrate episodic buffer."""
    engine = create_episodic_buffer_engine()

    # Add multimodal content
    result1 = engine.integrate([
        (ModalityType.VERBAL, "The dog ran"),
        (ModalityType.VISUAL, "brown_dog_image")
    ])

    # Process sentence with semantic integration
    chunk = engine.process_sentence("The cat sat on the mat")

    # Create episode
    episode = engine.consolidate_episode()

    metrics = engine.get_metrics()

    return {
        'integration_quality': result1.binding_quality,
        'ltm_contribution': result1.ltm_contribution,
        'episode_coherence': episode.narrative_coherence,
        'binding_accuracy': metrics.binding_accuracy,
        'interpretation': (
            f'Integrated {len(engine.get_buffer_contents())} chunks '
            f'with {metrics.binding_accuracy:.2f} binding quality'
        )
    }


def get_episodic_buffer_facts() -> Dict[str, str]:
    """Get facts about episodic buffer."""
    return {
        'baddeley_2000': 'Episodic buffer added to working memory model',
        'capacity': '~4 integrated chunks',
        'function': 'Binds information across modalities and with LTM',
        'attention': 'Controlled by central executive',
        'ltm_link': 'Provides interface between WM and episodic LTM',
        'prose_memory': 'Explains memory for meaningful sentences',
        'binding': 'Creates integrated multi-modal representations',
        'episodes': 'Contributes to formation of episodic memories'
    }
