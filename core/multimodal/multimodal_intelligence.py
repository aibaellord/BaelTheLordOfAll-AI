#!/usr/bin/env python3
"""
BAEL - Multi-Modal Intelligence System
Process and understand multiple modalities: text, images, audio, video.

Features:
- Cross-modal understanding
- Unified representation learning
- Modal fusion strategies
- Modality-specific encoders
- Cross-modal retrieval
- Multi-modal reasoning
"""

import asyncio
import base64
import hashlib
import io
import json
import logging
import math
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class Modality(Enum):
    """Supported modalities."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    CODE = "code"
    STRUCTURED = "structured"  # Tables, JSON, etc.


class FusionStrategy(Enum):
    """Multi-modal fusion strategies."""
    EARLY = "early"           # Fuse at input level
    LATE = "late"             # Fuse at decision level
    HYBRID = "hybrid"         # Multiple fusion points
    ATTENTION = "attention"   # Cross-attention fusion
    TENSOR = "tensor"         # Tensor product fusion


class ModalityQuality(Enum):
    """Quality levels for modality data."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass
class ModalityData:
    """Data for a single modality."""
    modality: Modality
    data: Any
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality: ModalityQuality = ModalityQuality.UNKNOWN
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""


@dataclass
class MultiModalInput:
    """Multi-modal input container."""
    id: str
    modalities: Dict[Modality, ModalityData] = field(default_factory=dict)
    primary_modality: Optional[Modality] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def add_modality(self, modality_data: ModalityData) -> None:
        """Add modality data."""
        self.modalities[modality_data.modality] = modality_data

    def get_modality(self, modality: Modality) -> Optional[ModalityData]:
        """Get specific modality data."""
        return self.modalities.get(modality)

    def has_modality(self, modality: Modality) -> bool:
        """Check if modality exists."""
        return modality in self.modalities


@dataclass
class FusedRepresentation:
    """Fused multi-modal representation."""
    id: str
    embedding: List[float]
    source_modalities: List[Modality]
    fusion_strategy: FusionStrategy
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossModalAlignment:
    """Alignment between modalities."""
    source_modality: Modality
    target_modality: Modality
    alignment_score: float
    aligned_regions: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# MODALITY ENCODERS
# =============================================================================

class ModalityEncoder(ABC):
    """Abstract modality encoder."""

    @property
    @abstractmethod
    def modality(self) -> Modality:
        """Get supported modality."""
        pass

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Get embedding dimension."""
        pass

    @abstractmethod
    async def encode(self, data: Any) -> List[float]:
        """Encode data to embedding."""
        pass

    @abstractmethod
    async def preprocess(self, raw_data: Any) -> Any:
        """Preprocess raw data."""
        pass


class TextEncoder(ModalityEncoder):
    """Text modality encoder."""

    def __init__(self, embedding_dim: int = 768):
        self._embedding_dim = embedding_dim

    @property
    def modality(self) -> Modality:
        return Modality.TEXT

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    async def preprocess(self, raw_data: Any) -> str:
        """Preprocess text data."""
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode('utf-8')

        text = str(raw_data)

        # Basic preprocessing
        text = text.strip()
        text = ' '.join(text.split())  # Normalize whitespace

        return text

    async def encode(self, data: str) -> List[float]:
        """Encode text to embedding."""
        # Simulate embedding generation
        # In production, would use sentence transformers or similar

        # Create deterministic embedding from text hash
        text_hash = hashlib.sha256(data.encode()).digest()

        # Convert hash to embedding
        embedding = []
        for i in range(0, min(len(text_hash), self._embedding_dim * 4), 4):
            if i + 4 <= len(text_hash):
                val = int.from_bytes(text_hash[i:i+4], 'big')
                normalized = (val / (2**32)) * 2 - 1  # -1 to 1
                embedding.append(normalized)

        # Pad or truncate
        while len(embedding) < self._embedding_dim:
            embedding.append(0.0)
        embedding = embedding[:self._embedding_dim]

        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding


class ImageEncoder(ModalityEncoder):
    """Image modality encoder."""

    def __init__(self, embedding_dim: int = 512):
        self._embedding_dim = embedding_dim

    @property
    def modality(self) -> Modality:
        return Modality.IMAGE

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    async def preprocess(self, raw_data: Any) -> Dict[str, Any]:
        """Preprocess image data."""
        if isinstance(raw_data, bytes):
            # Assume raw bytes
            return {
                "data": raw_data,
                "format": "bytes",
                "size": len(raw_data)
            }
        elif isinstance(raw_data, str):
            if raw_data.startswith("data:image"):
                # Base64 data URI
                header, data = raw_data.split(',', 1)
                image_bytes = base64.b64decode(data)
                return {
                    "data": image_bytes,
                    "format": "base64",
                    "size": len(image_bytes)
                }
            else:
                # Assume path
                return {
                    "data": raw_data,
                    "format": "path",
                    "size": 0
                }
        elif isinstance(raw_data, dict):
            return raw_data
        else:
            return {"data": raw_data, "format": "unknown", "size": 0}

    async def encode(self, data: Dict[str, Any]) -> List[float]:
        """Encode image to embedding."""
        # Simulate image embedding
        # In production, would use CLIP or similar vision encoder

        # Create deterministic embedding from image data
        if isinstance(data.get("data"), bytes):
            data_hash = hashlib.sha256(data["data"]).digest()
        else:
            data_hash = hashlib.sha256(str(data).encode()).digest()

        embedding = []
        for i in range(0, min(len(data_hash), self._embedding_dim * 4), 4):
            if i + 4 <= len(data_hash):
                val = int.from_bytes(data_hash[i:i+4], 'big')
                normalized = (val / (2**32)) * 2 - 1
                embedding.append(normalized)

        # Pad
        while len(embedding) < self._embedding_dim:
            embedding.append(0.0)
        embedding = embedding[:self._embedding_dim]

        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding


class AudioEncoder(ModalityEncoder):
    """Audio modality encoder."""

    def __init__(self, embedding_dim: int = 256):
        self._embedding_dim = embedding_dim

    @property
    def modality(self) -> Modality:
        return Modality.AUDIO

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    async def preprocess(self, raw_data: Any) -> Dict[str, Any]:
        """Preprocess audio data."""
        if isinstance(raw_data, bytes):
            return {
                "data": raw_data,
                "format": "wav",
                "duration": len(raw_data) / (16000 * 2),  # Assume 16kHz 16-bit
                "sample_rate": 16000
            }
        elif isinstance(raw_data, str):
            return {
                "data": raw_data,
                "format": "path",
                "duration": 0,
                "sample_rate": 0
            }
        return {"data": raw_data, "format": "unknown"}

    async def encode(self, data: Dict[str, Any]) -> List[float]:
        """Encode audio to embedding."""
        # Simulate audio embedding
        # In production, would use Whisper encoder or similar

        if isinstance(data.get("data"), bytes):
            data_hash = hashlib.sha256(data["data"]).digest()
        else:
            data_hash = hashlib.sha256(str(data).encode()).digest()

        embedding = []
        for i in range(0, min(len(data_hash), self._embedding_dim * 4), 4):
            if i + 4 <= len(data_hash):
                val = int.from_bytes(data_hash[i:i+4], 'big')
                normalized = (val / (2**32)) * 2 - 1
                embedding.append(normalized)

        while len(embedding) < self._embedding_dim:
            embedding.append(0.0)
        embedding = embedding[:self._embedding_dim]

        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding


class CodeEncoder(ModalityEncoder):
    """Code modality encoder."""

    def __init__(self, embedding_dim: int = 512):
        self._embedding_dim = embedding_dim

    @property
    def modality(self) -> Modality:
        return Modality.CODE

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    async def preprocess(self, raw_data: Any) -> Dict[str, Any]:
        """Preprocess code data."""
        if isinstance(raw_data, dict):
            code = raw_data.get("code", "")
            language = raw_data.get("language", "unknown")
        else:
            code = str(raw_data)
            language = "unknown"

        # Detect language if not specified
        if language == "unknown":
            language = self._detect_language(code)

        return {
            "code": code,
            "language": language,
            "lines": len(code.split('\n')),
            "tokens": len(code.split())
        }

    def _detect_language(self, code: str) -> str:
        """Simple language detection."""
        if "def " in code and ":" in code:
            return "python"
        elif "function " in code or "const " in code or "let " in code:
            return "javascript"
        elif "#include" in code or "int main" in code:
            return "cpp"
        elif "public class" in code:
            return "java"
        return "unknown"

    async def encode(self, data: Dict[str, Any]) -> List[float]:
        """Encode code to embedding."""
        # Combine code content and structure
        code = data.get("code", "")
        language = data.get("language", "")

        combined = f"{language}:{code}"
        data_hash = hashlib.sha256(combined.encode()).digest()

        embedding = []
        for i in range(0, min(len(data_hash), self._embedding_dim * 4), 4):
            if i + 4 <= len(data_hash):
                val = int.from_bytes(data_hash[i:i+4], 'big')
                normalized = (val / (2**32)) * 2 - 1
                embedding.append(normalized)

        while len(embedding) < self._embedding_dim:
            embedding.append(0.0)
        embedding = embedding[:self._embedding_dim]

        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding


# =============================================================================
# MODAL FUSION
# =============================================================================

class ModalFusion(ABC):
    """Abstract modal fusion strategy."""

    @property
    @abstractmethod
    def strategy(self) -> FusionStrategy:
        """Get fusion strategy type."""
        pass

    @abstractmethod
    async def fuse(
        self,
        embeddings: Dict[Modality, List[float]]
    ) -> List[float]:
        """Fuse multiple modality embeddings."""
        pass


class EarlyFusion(ModalFusion):
    """Concatenate and project early fusion."""

    def __init__(self, output_dim: int = 512):
        self.output_dim = output_dim

    @property
    def strategy(self) -> FusionStrategy:
        return FusionStrategy.EARLY

    async def fuse(
        self,
        embeddings: Dict[Modality, List[float]]
    ) -> List[float]:
        """Fuse by concatenation and projection."""
        # Concatenate all embeddings
        concatenated = []
        for modality in sorted(embeddings.keys(), key=lambda m: m.value):
            concatenated.extend(embeddings[modality])

        # Project to output dimension
        # Simulated linear projection
        if len(concatenated) > self.output_dim:
            # Downsample with averaging
            chunk_size = len(concatenated) // self.output_dim
            result = []
            for i in range(self.output_dim):
                start = i * chunk_size
                end = start + chunk_size
                chunk_avg = sum(concatenated[start:end]) / chunk_size
                result.append(chunk_avg)
        else:
            # Pad with zeros
            result = concatenated + [0.0] * (self.output_dim - len(concatenated))

        # Normalize
        norm = math.sqrt(sum(x*x for x in result))
        if norm > 0:
            result = [x / norm for x in result]

        return result


class LateFusion(ModalFusion):
    """Fuse at decision level."""

    def __init__(self, output_dim: int = 512, weights: Dict[Modality, float] = None):
        self.output_dim = output_dim
        self.weights = weights or {}

    @property
    def strategy(self) -> FusionStrategy:
        return FusionStrategy.LATE

    async def fuse(
        self,
        embeddings: Dict[Modality, List[float]]
    ) -> List[float]:
        """Fuse by weighted average."""
        if not embeddings:
            return [0.0] * self.output_dim

        # Determine weights
        weights = {}
        total_weight = 0.0
        for modality in embeddings:
            w = self.weights.get(modality, 1.0)
            weights[modality] = w
            total_weight += w

        # Normalize weights
        for modality in weights:
            weights[modality] /= total_weight

        # Weighted average
        result = [0.0] * self.output_dim

        for modality, embedding in embeddings.items():
            weight = weights[modality]

            # Resize embedding if needed
            if len(embedding) != self.output_dim:
                if len(embedding) > self.output_dim:
                    embedding = embedding[:self.output_dim]
                else:
                    embedding = embedding + [0.0] * (self.output_dim - len(embedding))

            for i in range(self.output_dim):
                result[i] += weight * embedding[i]

        # Normalize
        norm = math.sqrt(sum(x*x for x in result))
        if norm > 0:
            result = [x / norm for x in result]

        return result


class AttentionFusion(ModalFusion):
    """Cross-attention based fusion."""

    def __init__(self, output_dim: int = 512, num_heads: int = 8):
        self.output_dim = output_dim
        self.num_heads = num_heads

    @property
    def strategy(self) -> FusionStrategy:
        return FusionStrategy.ATTENTION

    async def fuse(
        self,
        embeddings: Dict[Modality, List[float]]
    ) -> List[float]:
        """Fuse using attention mechanism."""
        if not embeddings:
            return [0.0] * self.output_dim

        # Stack embeddings as matrix
        modalities = list(embeddings.keys())
        embedding_matrix = []

        for mod in modalities:
            emb = embeddings[mod]
            if len(emb) != self.output_dim:
                if len(emb) > self.output_dim:
                    emb = emb[:self.output_dim]
                else:
                    emb = emb + [0.0] * (self.output_dim - len(emb))
            embedding_matrix.append(emb)

        # Compute attention scores (simplified)
        attention_scores = []
        for i, emb_i in enumerate(embedding_matrix):
            scores = []
            for j, emb_j in enumerate(embedding_matrix):
                # Dot product attention
                score = sum(a * b for a, b in zip(emb_i, emb_j))
                score /= math.sqrt(self.output_dim)
                scores.append(score)

            # Softmax
            max_score = max(scores)
            exp_scores = [math.exp(s - max_score) for s in scores]
            total = sum(exp_scores)
            attention_scores.append([s / total for s in exp_scores])

        # Apply attention
        result = [0.0] * self.output_dim
        for i, scores in enumerate(attention_scores):
            for j, weight in enumerate(scores):
                for k in range(self.output_dim):
                    result[k] += weight * embedding_matrix[j][k]

        # Average across modalities
        n_modalities = len(modalities)
        result = [x / n_modalities for x in result]

        # Normalize
        norm = math.sqrt(sum(x*x for x in result))
        if norm > 0:
            result = [x / norm for x in result]

        return result


# =============================================================================
# CROSS-MODAL ALIGNMENT
# =============================================================================

class CrossModalAligner:
    """Align representations across modalities."""

    def __init__(self, alignment_dim: int = 256):
        self.alignment_dim = alignment_dim
        self.alignment_cache: Dict[str, CrossModalAlignment] = {}

    async def align(
        self,
        source: ModalityData,
        target: ModalityData
    ) -> CrossModalAlignment:
        """Align source modality to target."""
        cache_key = f"{source.modality.value}_{target.modality.value}_{id(source)}_{id(target)}"

        if cache_key in self.alignment_cache:
            return self.alignment_cache[cache_key]

        # Compute alignment score
        if source.embedding and target.embedding:
            # Cosine similarity
            dot = sum(a * b for a, b in zip(source.embedding, target.embedding))
            norm_s = math.sqrt(sum(x*x for x in source.embedding))
            norm_t = math.sqrt(sum(x*x for x in target.embedding))

            if norm_s > 0 and norm_t > 0:
                score = dot / (norm_s * norm_t)
            else:
                score = 0.0
        else:
            score = 0.0

        alignment = CrossModalAlignment(
            source_modality=source.modality,
            target_modality=target.modality,
            alignment_score=score
        )

        self.alignment_cache[cache_key] = alignment

        return alignment

    async def compute_all_alignments(
        self,
        modality_data: Dict[Modality, ModalityData]
    ) -> List[CrossModalAlignment]:
        """Compute alignments between all modality pairs."""
        alignments = []
        modalities = list(modality_data.keys())

        for i, mod_i in enumerate(modalities):
            for mod_j in modalities[i+1:]:
                alignment = await self.align(
                    modality_data[mod_i],
                    modality_data[mod_j]
                )
                alignments.append(alignment)

        return alignments


# =============================================================================
# CROSS-MODAL RETRIEVAL
# =============================================================================

class CrossModalRetriever:
    """Retrieve across modalities."""

    def __init__(self):
        self.index: Dict[Modality, List[Tuple[str, List[float], Any]]] = defaultdict(list)

    def add_item(
        self,
        modality: Modality,
        item_id: str,
        embedding: List[float],
        data: Any
    ) -> None:
        """Add item to index."""
        self.index[modality].append((item_id, embedding, data))

    async def retrieve(
        self,
        query_modality: Modality,
        query_embedding: List[float],
        target_modality: Modality,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve items from target modality using query."""
        if target_modality not in self.index:
            return []

        results = []

        for item_id, embedding, data in self.index[target_modality]:
            # Compute similarity
            min_len = min(len(query_embedding), len(embedding))
            dot = sum(
                query_embedding[i] * embedding[i]
                for i in range(min_len)
            )

            norm_q = math.sqrt(sum(x*x for x in query_embedding[:min_len]))
            norm_e = math.sqrt(sum(x*x for x in embedding[:min_len]))

            if norm_q > 0 and norm_e > 0:
                similarity = dot / (norm_q * norm_e)
            else:
                similarity = 0.0

            results.append({
                "id": item_id,
                "similarity": similarity,
                "modality": target_modality.value,
                "data": data
            })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:top_k]

    async def cross_modal_search(
        self,
        query: ModalityData,
        target_modalities: List[Modality] = None,
        top_k: int = 5
    ) -> Dict[Modality, List[Dict[str, Any]]]:
        """Search across all target modalities."""
        if not query.embedding:
            return {}

        target_modalities = target_modalities or [
            m for m in Modality if m != query.modality
        ]

        results = {}
        for target_mod in target_modalities:
            results[target_mod] = await self.retrieve(
                query.modality,
                query.embedding,
                target_mod,
                top_k
            )

        return results


# =============================================================================
# MULTI-MODAL REASONING
# =============================================================================

class MultiModalReasoner:
    """Reason across multiple modalities."""

    def __init__(self):
        self.reasoning_history: List[Dict[str, Any]] = []

    async def reason(
        self,
        inputs: MultiModalInput,
        question: str
    ) -> Dict[str, Any]:
        """Perform multi-modal reasoning."""
        # Analyze available modalities
        available = list(inputs.modalities.keys())

        reasoning_steps = []

        # Step 1: Modality analysis
        step1 = {
            "step": 1,
            "action": "analyze_modalities",
            "available_modalities": [m.value for m in available],
            "primary": inputs.primary_modality.value if inputs.primary_modality else None
        }
        reasoning_steps.append(step1)

        # Step 2: Cross-modal consistency check
        consistency_score = 1.0
        if len(available) >= 2:
            # Check if modalities are consistent
            embeddings = [
                inputs.modalities[m].embedding
                for m in available
                if inputs.modalities[m].embedding
            ]

            if len(embeddings) >= 2:
                # Pairwise similarity
                sims = []
                for i, emb_i in enumerate(embeddings):
                    for emb_j in embeddings[i+1:]:
                        min_len = min(len(emb_i), len(emb_j))
                        dot = sum(emb_i[k] * emb_j[k] for k in range(min_len))
                        norm_i = math.sqrt(sum(x*x for x in emb_i[:min_len]))
                        norm_j = math.sqrt(sum(x*x for x in emb_j[:min_len]))
                        if norm_i > 0 and norm_j > 0:
                            sims.append(dot / (norm_i * norm_j))

                if sims:
                    consistency_score = sum(sims) / len(sims)

        step2 = {
            "step": 2,
            "action": "consistency_check",
            "consistency_score": consistency_score
        }
        reasoning_steps.append(step2)

        # Step 3: Question analysis
        question_lower = question.lower()
        required_modalities = []

        if any(w in question_lower for w in ["look", "see", "image", "picture", "visual"]):
            required_modalities.append(Modality.IMAGE)
        if any(w in question_lower for w in ["say", "hear", "sound", "audio", "listen"]):
            required_modalities.append(Modality.AUDIO)
        if any(w in question_lower for w in ["code", "function", "program", "script"]):
            required_modalities.append(Modality.CODE)
        if any(w in question_lower for w in ["read", "text", "write", "describe"]):
            required_modalities.append(Modality.TEXT)

        step3 = {
            "step": 3,
            "action": "question_analysis",
            "question": question,
            "required_modalities": [m.value for m in required_modalities],
            "modalities_available": all(m in available for m in required_modalities)
        }
        reasoning_steps.append(step3)

        # Step 4: Generate answer
        missing = [m for m in required_modalities if m not in available]

        if missing:
            answer = f"Cannot fully answer - missing modalities: {[m.value for m in missing]}"
            confidence = 0.5
        else:
            answer = f"Based on analysis of {len(available)} modalities with {consistency_score:.2%} consistency."
            confidence = consistency_score

        step4 = {
            "step": 4,
            "action": "generate_answer",
            "answer": answer,
            "confidence": confidence
        }
        reasoning_steps.append(step4)

        result = {
            "question": question,
            "answer": answer,
            "confidence": confidence,
            "reasoning_steps": reasoning_steps,
            "modalities_used": [m.value for m in available]
        }

        self.reasoning_history.append(result)

        return result


# =============================================================================
# MULTI-MODAL INTELLIGENCE SYSTEM
# =============================================================================

class MultiModalIntelligence:
    """Main multi-modal intelligence system."""

    def __init__(self, unified_dim: int = 512):
        self.unified_dim = unified_dim

        # Encoders
        self.encoders: Dict[Modality, ModalityEncoder] = {
            Modality.TEXT: TextEncoder(embedding_dim=768),
            Modality.IMAGE: ImageEncoder(embedding_dim=512),
            Modality.AUDIO: AudioEncoder(embedding_dim=256),
            Modality.CODE: CodeEncoder(embedding_dim=512)
        }

        # Fusion strategies
        self.fusion_strategies: Dict[FusionStrategy, ModalFusion] = {
            FusionStrategy.EARLY: EarlyFusion(output_dim=unified_dim),
            FusionStrategy.LATE: LateFusion(output_dim=unified_dim),
            FusionStrategy.ATTENTION: AttentionFusion(output_dim=unified_dim)
        }

        # Components
        self.aligner = CrossModalAligner(alignment_dim=unified_dim)
        self.retriever = CrossModalRetriever()
        self.reasoner = MultiModalReasoner()

        # Default fusion
        self.default_fusion = FusionStrategy.ATTENTION

    async def process_input(
        self,
        raw_inputs: Dict[Modality, Any]
    ) -> MultiModalInput:
        """Process raw multi-modal input."""
        mm_input = MultiModalInput(id=str(uuid4()))

        for modality, raw_data in raw_inputs.items():
            if modality not in self.encoders:
                logger.warning(f"No encoder for modality: {modality}")
                continue

            encoder = self.encoders[modality]

            # Preprocess
            processed = await encoder.preprocess(raw_data)

            # Encode
            embedding = await encoder.encode(processed)

            # Create modality data
            mod_data = ModalityData(
                modality=modality,
                data=processed,
                embedding=embedding
            )

            mm_input.add_modality(mod_data)

        # Set primary modality (most information)
        if mm_input.modalities:
            # Use text as primary if available, else first available
            if Modality.TEXT in mm_input.modalities:
                mm_input.primary_modality = Modality.TEXT
            else:
                mm_input.primary_modality = list(mm_input.modalities.keys())[0]

        return mm_input

    async def fuse(
        self,
        mm_input: MultiModalInput,
        strategy: FusionStrategy = None
    ) -> FusedRepresentation:
        """Fuse multi-modal input."""
        strategy = strategy or self.default_fusion

        if strategy not in self.fusion_strategies:
            strategy = self.default_fusion

        # Collect embeddings
        embeddings = {}
        for modality, data in mm_input.modalities.items():
            if data.embedding:
                embeddings[modality] = data.embedding

        # Fuse
        fused_embedding = await self.fusion_strategies[strategy].fuse(embeddings)

        return FusedRepresentation(
            id=str(uuid4()),
            embedding=fused_embedding,
            source_modalities=list(embeddings.keys()),
            fusion_strategy=strategy,
            confidence=1.0
        )

    async def align_modalities(
        self,
        mm_input: MultiModalInput
    ) -> List[CrossModalAlignment]:
        """Compute cross-modal alignments."""
        return await self.aligner.compute_all_alignments(mm_input.modalities)

    async def retrieve_cross_modal(
        self,
        query: MultiModalInput,
        target_modalities: List[Modality] = None,
        top_k: int = 5
    ) -> Dict[Modality, List[Dict[str, Any]]]:
        """Cross-modal retrieval."""
        if not query.primary_modality:
            return {}

        primary_data = query.get_modality(query.primary_modality)
        if not primary_data:
            return {}

        return await self.retriever.cross_modal_search(
            primary_data,
            target_modalities,
            top_k
        )

    async def reason(
        self,
        mm_input: MultiModalInput,
        question: str
    ) -> Dict[str, Any]:
        """Perform multi-modal reasoning."""
        return await self.reasoner.reason(mm_input, question)

    async def understand(
        self,
        raw_inputs: Dict[Modality, Any],
        question: str = None
    ) -> Dict[str, Any]:
        """Full understanding pipeline."""
        # 1. Process input
        mm_input = await self.process_input(raw_inputs)

        # 2. Fuse modalities
        fused = await self.fuse(mm_input)

        # 3. Compute alignments
        alignments = await self.align_modalities(mm_input)

        # 4. Reason if question provided
        reasoning = None
        if question:
            reasoning = await self.reason(mm_input, question)

        return {
            "input_id": mm_input.id,
            "modalities": [m.value for m in mm_input.modalities.keys()],
            "primary_modality": mm_input.primary_modality.value if mm_input.primary_modality else None,
            "fused_representation_dim": len(fused.embedding),
            "fusion_strategy": fused.fusion_strategy.value,
            "alignments": [
                {
                    "source": a.source_modality.value,
                    "target": a.target_modality.value,
                    "score": a.alignment_score
                }
                for a in alignments
            ],
            "reasoning": reasoning
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo multi-modal intelligence system."""
    print("=== Multi-Modal Intelligence System Demo ===\n")

    # Create system
    mmi = MultiModalIntelligence(unified_dim=512)

    # 1. Process multi-modal input
    print("1. Processing Multi-Modal Input:")
    raw_inputs = {
        Modality.TEXT: "A beautiful sunset over the ocean with orange and purple clouds.",
        Modality.IMAGE: base64.b64encode(b"fake_image_data").decode(),
        Modality.CODE: """
def describe_sunset():
    colors = ['orange', 'purple', 'red']
    return f"The sunset has {', '.join(colors)} colors"
"""
    }

    mm_input = await mmi.process_input(raw_inputs)
    print(f"   Processed {len(mm_input.modalities)} modalities")
    print(f"   Primary modality: {mm_input.primary_modality.value}")

    for mod, data in mm_input.modalities.items():
        print(f"   - {mod.value}: embedding dim = {len(data.embedding)}")

    # 2. Fuse modalities
    print("\n2. Fusing Modalities:")
    for strategy in [FusionStrategy.EARLY, FusionStrategy.LATE, FusionStrategy.ATTENTION]:
        fused = await mmi.fuse(mm_input, strategy)
        print(f"   {strategy.value}: dim = {len(fused.embedding)}, sources = {len(fused.source_modalities)}")

    # 3. Align modalities
    print("\n3. Cross-Modal Alignment:")
    alignments = await mmi.align_modalities(mm_input)
    for alignment in alignments:
        print(f"   {alignment.source_modality.value} <-> {alignment.target_modality.value}: {alignment.alignment_score:.4f}")

    # 4. Multi-modal reasoning
    print("\n4. Multi-Modal Reasoning:")
    questions = [
        "What colors are in the image?",
        "Can you describe what the code does?",
        "What is the connection between the text and code?"
    ]

    for question in questions:
        result = await mmi.reason(mm_input, question)
        print(f"   Q: {question}")
        print(f"   A: {result['answer']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print()

    # 5. Full understanding pipeline
    print("5. Full Understanding Pipeline:")
    understanding = await mmi.understand(
        raw_inputs,
        question="Describe the overall theme"
    )

    print(f"   Input ID: {understanding['input_id']}")
    print(f"   Modalities: {understanding['modalities']}")
    print(f"   Fusion: {understanding['fusion_strategy']}")
    print(f"   Alignments: {len(understanding['alignments'])}")

    if understanding['reasoning']:
        print(f"   Reasoning answer: {understanding['reasoning']['answer']}")

    # 6. Cross-modal retrieval
    print("\n6. Cross-Modal Retrieval Demo:")

    # Add some items to index
    for i in range(5):
        text_data = f"Sample text description {i}"
        text_encoder = mmi.encoders[Modality.TEXT]
        processed = await text_encoder.preprocess(text_data)
        embedding = await text_encoder.encode(processed)
        mmi.retriever.add_item(
            Modality.TEXT,
            f"text_{i}",
            embedding,
            text_data
        )

    for i in range(3):
        code_data = f"def function_{i}(): pass"
        code_encoder = mmi.encoders[Modality.CODE]
        processed = await code_encoder.preprocess(code_data)
        embedding = await code_encoder.encode(processed)
        mmi.retriever.add_item(
            Modality.CODE,
            f"code_{i}",
            embedding,
            code_data
        )

    # Retrieve using image query
    primary_data = mm_input.get_modality(mm_input.primary_modality)
    results = await mmi.retriever.cross_modal_search(primary_data, top_k=3)

    for modality, items in results.items():
        print(f"   Retrieved from {modality.value}:")
        for item in items[:2]:
            print(f"     - {item['id']}: similarity = {item['similarity']:.4f}")


if __name__ == "__main__":
    asyncio.run(demo())
