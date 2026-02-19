"""
⚡ SEMANTIC COMPRESSION ⚡
=========================
Intelligent context compression.

Features:
- Lossless compression for code
- Lossy summarization for text
- Abstraction for concepts
- Hierarchical compression
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid
import hashlib


class CompressionLevel(Enum):
    """Compression aggressiveness"""
    NONE = 0           # No compression
    MINIMAL = 1        # Light compression
    MODERATE = 2       # Balanced
    AGGRESSIVE = 3     # High compression
    EXTREME = 4        # Maximum compression


@dataclass
class CompressedChunk:
    """Compressed content chunk"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Compressed content
    compressed: Any = None

    # Original metadata
    original_size: int = 0
    compressed_size: int = 0

    # Compression info
    level: CompressionLevel = CompressionLevel.MODERATE
    method: str = ""

    # Decompression data
    can_decompress: bool = True
    decompression_key: Optional[str] = None

    # Quality
    fidelity: float = 1.0  # 1.0 = lossless

    @property
    def compression_ratio(self) -> float:
        if self.original_size == 0:
            return 1.0
        return self.compressed_size / self.original_size


class LosslessCompressor:
    """
    Lossless compression using deduplication and references.
    """

    def __init__(self):
        # Content hash -> content
        self.content_store: Dict[str, str] = {}

        # Chunk ID -> content hash
        self.references: Dict[str, str] = {}

    def compress(
        self,
        content: str,
        chunk_id: str = None
    ) -> CompressedChunk:
        """Compress content losslessly"""
        chunk_id = chunk_id or str(uuid.uuid4())

        # Hash content
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check if already stored
        if content_hash in self.content_store:
            # Just store reference
            self.references[chunk_id] = content_hash

            return CompressedChunk(
                id=chunk_id,
                compressed=content_hash,  # Store hash as reference
                original_size=len(content),
                compressed_size=len(content_hash),
                method='dedup_reference',
                fidelity=1.0
            )

        # Store content
        self.content_store[content_hash] = content
        self.references[chunk_id] = content_hash

        return CompressedChunk(
            id=chunk_id,
            compressed=content_hash,
            original_size=len(content),
            compressed_size=len(content),  # First occurrence
            method='dedup_store',
            fidelity=1.0
        )

    def decompress(
        self,
        chunk: CompressedChunk
    ) -> Optional[str]:
        """Decompress content"""
        content_hash = chunk.compressed
        return self.content_store.get(content_hash)

    def get_unique_ratio(self) -> float:
        """Get ratio of unique content"""
        if not self.references:
            return 1.0
        return len(self.content_store) / len(self.references)


class SummaryCompressor:
    """
    Lossy compression through summarization.
    """

    def __init__(self, target_ratio: float = 0.3):
        self.target_ratio = target_ratio

    def compress(
        self,
        content: str,
        level: CompressionLevel = CompressionLevel.MODERATE
    ) -> CompressedChunk:
        """Compress by summarization"""
        # Calculate target length
        original_len = len(content)

        ratios = {
            CompressionLevel.MINIMAL: 0.8,
            CompressionLevel.MODERATE: 0.5,
            CompressionLevel.AGGRESSIVE: 0.3,
            CompressionLevel.EXTREME: 0.1
        }

        ratio = ratios.get(level, 0.5)
        target_len = int(original_len * ratio)

        # Simple extractive summary (take key sentences)
        sentences = content.split('. ')

        if len(sentences) <= 1:
            summary = content[:target_len]
        else:
            # Score sentences by position and length
            scored = []
            for i, sent in enumerate(sentences):
                # First and last sentences are important
                position_score = 1.0 if i == 0 or i == len(sentences) - 1 else 0.5
                # Medium-length sentences preferred
                length_score = min(len(sent) / 100, 1.0)
                scored.append((position_score + length_score, sent))

            scored.sort(key=lambda x: -x[0])

            # Take top sentences up to target length
            summary_parts = []
            current_len = 0

            for _, sent in scored:
                if current_len + len(sent) > target_len:
                    break
                summary_parts.append(sent)
                current_len += len(sent) + 2  # +2 for ". "

            summary = '. '.join(summary_parts)

        return CompressedChunk(
            compressed=summary,
            original_size=original_len,
            compressed_size=len(summary),
            level=level,
            method='extractive_summary',
            can_decompress=False,
            fidelity=0.7  # Lossy
        )

    def compress_progressive(
        self,
        content: str,
        levels: int = 3
    ) -> List[CompressedChunk]:
        """Create progressive compression levels"""
        chunks = []
        current = content

        for i in range(levels):
            level = CompressionLevel(min(i + 1, 4))
            chunk = self.compress(current, level)
            chunks.append(chunk)
            current = chunk.compressed

        return chunks


class AbstractionCompressor:
    """
    Compression through abstraction.

    Creates higher-level representations.
    """

    def __init__(self):
        # Concept mappings
        self.concepts: Dict[str, str] = {}
        self.concept_examples: Dict[str, List[str]] = defaultdict(list)

    def learn_concept(
        self,
        concept_name: str,
        examples: List[str]
    ):
        """Learn a concept from examples"""
        self.concept_examples[concept_name].extend(examples)

        # Create representative pattern
        if examples:
            # Simple: use most common words
            words = defaultdict(int)
            for ex in examples:
                for word in ex.lower().split():
                    words[word] += 1

            top_words = sorted(words.items(), key=lambda x: -x[1])[:5]
            pattern = ' '.join(w for w, _ in top_words)
            self.concepts[concept_name] = pattern

    def match_concept(
        self,
        content: str
    ) -> Optional[str]:
        """Find matching concept for content"""
        content_words = set(content.lower().split())

        best_match = None
        best_overlap = 0

        for concept_name, pattern in self.concepts.items():
            pattern_words = set(pattern.split())
            overlap = len(content_words & pattern_words)

            if overlap > best_overlap:
                best_overlap = overlap
                best_match = concept_name

        return best_match

    def compress(
        self,
        content: str
    ) -> CompressedChunk:
        """Compress by abstraction"""
        concept = self.match_concept(content)

        if concept:
            return CompressedChunk(
                compressed=f"[{concept}]: {content[:50]}...",
                original_size=len(content),
                compressed_size=len(concept) + 55,
                method='abstraction',
                can_decompress=False,
                fidelity=0.5
            )

        # No matching concept, return truncated
        return CompressedChunk(
            compressed=content[:100] + "...",
            original_size=len(content),
            compressed_size=103,
            method='truncation',
            can_decompress=False,
            fidelity=0.3
        )


class SemanticCompressor:
    """
    Master compressor combining multiple strategies.
    """

    def __init__(self):
        self.lossless = LosslessCompressor()
        self.summary = SummaryCompressor()
        self.abstraction = AbstractionCompressor()

        # Statistics
        self.total_original = 0
        self.total_compressed = 0

    def compress(
        self,
        content: str,
        content_type: str = 'text',
        level: CompressionLevel = CompressionLevel.MODERATE
    ) -> CompressedChunk:
        """
        Compress content using appropriate strategy.
        """
        self.total_original += len(content)

        if level == CompressionLevel.NONE:
            chunk = CompressedChunk(
                compressed=content,
                original_size=len(content),
                compressed_size=len(content),
                method='none',
                fidelity=1.0
            )
        elif content_type == 'code':
            # Lossless for code
            chunk = self.lossless.compress(content)
        elif level.value <= CompressionLevel.MINIMAL.value:
            chunk = self.lossless.compress(content)
        elif level.value <= CompressionLevel.AGGRESSIVE.value:
            chunk = self.summary.compress(content, level)
        else:
            chunk = self.abstraction.compress(content)

        self.total_compressed += chunk.compressed_size
        return chunk

    def compress_batch(
        self,
        contents: List[str],
        level: CompressionLevel = CompressionLevel.MODERATE
    ) -> List[CompressedChunk]:
        """Compress multiple contents"""
        return [self.compress(c, level=level) for c in contents]

    def get_statistics(self) -> Dict[str, float]:
        """Get compression statistics"""
        return {
            'total_original': self.total_original,
            'total_compressed': self.total_compressed,
            'overall_ratio': (
                self.total_compressed / self.total_original
                if self.total_original > 0 else 1.0
            ),
            'unique_content_ratio': self.lossless.get_unique_ratio()
        }

    def decompress(
        self,
        chunk: CompressedChunk
    ) -> Optional[str]:
        """Attempt decompression"""
        if not chunk.can_decompress:
            return chunk.compressed  # Return as-is

        if chunk.method.startswith('dedup'):
            return self.lossless.decompress(chunk)

        return chunk.compressed


# Export all
__all__ = [
    'CompressionLevel',
    'CompressedChunk',
    'LosslessCompressor',
    'SummaryCompressor',
    'AbstractionCompressor',
    'SemanticCompressor',
]
