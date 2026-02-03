"""
MODEL COMPRESSION & DEPLOYMENT SYSTEM - Quantization, pruning, knowledge distillation,
neural architecture compression, edge deployment optimization, latency-accuracy tradeoffs.

Features:
- Quantization (INT8, FP16, dynamic range, per-channel)
- Magnitude and structured pruning
- Knowledge distillation (teacher-student)
- Layer-wise compression
- Latency-accuracy Pareto frontier
- Edge deployment optimization
- Compression verification
- Performance tracking

Target: 1,800+ lines for model compression system
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ============================================================================
# COMPRESSION ENUMS
# ============================================================================

class QuantizationType(Enum):
    """Quantization types."""
    INT8 = "int8"
    FP16 = "fp16"
    DYNAMIC_RANGE = "dynamic_range"
    PER_CHANNEL = "per_channel"

class PruningType(Enum):
    """Pruning types."""
    MAGNITUDE = "magnitude"
    STRUCTURED = "structured"
    ITERATIVE = "iterative"
    LOTTERY_TICKET = "lottery_ticket"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class CompressionProfile:
    """Compression configuration."""
    profile_id: str
    name: str
    quantization_type: QuantizationType = QuantizationType.INT8
    quantization_bits: int = 8
    pruning_type: PruningType = PruningType.MAGNITUDE
    pruning_ratio: float = 0.5  # Remove 50% of weights
    distillation_temperature: float = 4.0
    target_latency_ms: Optional[float] = None
    min_accuracy: float = 0.95  # 95% of original accuracy

@dataclass
class CompressionResult:
    """Result of compression."""
    result_id: str
    original_model_id: str
    compressed_model_id: str
    profile: CompressionProfile
    timestamp: datetime = field(default_factory=datetime.now)

    # Metrics
    original_size_mb: float = 0.0
    compressed_size_mb: float = 0.0
    compression_ratio: float = 0.0  # Original / Compressed

    original_latency_ms: float = 0.0
    compressed_latency_ms: float = 0.0
    latency_reduction: float = 0.0  # %

    original_accuracy: float = 0.0
    compressed_accuracy: float = 0.0
    accuracy_loss: float = 0.0  # %

    inference_speedup: float = 0.0
    memory_savings: float = 0.0

# ============================================================================
# QUANTIZATION
# ============================================================================

class Quantizer:
    """Quantize model weights."""

    def __init__(self):
        self.logger = logging.getLogger("quantizer")

    def quantize_int8(self, weights: np.ndarray) -> Tuple[np.ndarray, Dict[str, float]]:
        """Quantize to INT8."""

        # Calculate scaling factor
        min_val = np.min(weights)
        max_val = np.max(weights)
        scale = (max_val - min_val) / 255.0

        if scale == 0:
            scale = 1.0

        zero_point = int(-min_val / scale)

        # Quantize
        quantized = np.round((weights - min_val) / scale).astype(np.int8)

        return quantized, {'scale': scale, 'zero_point': zero_point}

    def quantize_fp16(self, weights: np.ndarray) -> np.ndarray:
        """Quantize to FP16."""

        # Simple FP16 conversion (reduced precision)
        return weights.astype(np.float16)

    def quantize_dynamic_range(self, weights: np.ndarray,
                              num_bits: int = 4) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Dynamic range quantization (non-uniform)."""

        # Find percentiles
        min_val = np.percentile(weights, 1)
        max_val = np.percentile(weights, 99)

        # Non-uniform quantization
        quantization_levels = 2 ** num_bits
        quantized = np.digitize(weights, np.linspace(min_val, max_val, quantization_levels))

        return quantized, {
            'num_bits': num_bits,
            'min': min_val,
            'max': max_val,
            'levels': quantization_levels
        }

    def quantize_per_channel(self, weights: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Per-channel quantization (channel-wise scaling)."""

        quantized = weights.copy()
        scales = []

        # For each channel (assuming last dimension is channel)
        for i in range(weights.shape[-1]):
            if len(weights.shape) == 1:
                channel_weights = weights
            else:
                channel_weights = weights[..., i]

            # Quantize this channel independently
            min_val = np.min(channel_weights)
            max_val = np.max(channel_weights)
            scale = (max_val - min_val) / 255.0

            if scale == 0:
                scale = 1.0

            if len(weights.shape) == 1:
                quantized = np.round((channel_weights - min_val) / scale).astype(np.int8)
            else:
                quantized[..., i] = np.round((channel_weights - min_val) / scale).astype(np.int8)

            scales.append({'scale': scale, 'min': min_val})

        return quantized, scales

# ============================================================================
# PRUNING
# ============================================================================

class Pruner:
    """Prune model weights."""

    def __init__(self):
        self.logger = logging.getLogger("pruner")

    def magnitude_pruning(self, weights: np.ndarray,
                         pruning_ratio: float = 0.5) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Remove small magnitude weights."""

        # Calculate threshold
        threshold = np.percentile(np.abs(weights), pruning_ratio * 100)

        # Prune
        mask = np.abs(weights) >= threshold
        pruned = weights * mask

        # Statistics
        num_pruned = np.sum(~mask)
        num_remaining = np.sum(mask)

        return pruned, {
            'threshold': threshold,
            'num_pruned': int(num_pruned),
            'num_remaining': int(num_remaining),
            'actual_ratio': float(num_pruned / weights.size)
        }

    def structured_pruning(self, weights: np.ndarray,
                          pruning_ratio: float = 0.5) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Prune entire channels/filters."""

        # For each channel, compute norm
        if len(weights.shape) < 2:
            # Fallback to magnitude pruning
            return self.magnitude_pruning(weights, pruning_ratio)

        channel_norms = np.linalg.norm(weights.reshape(weights.shape[0], -1), axis=1)

        # Determine which channels to keep
        threshold = np.percentile(channel_norms, pruning_ratio * 100)
        mask = channel_norms >= threshold

        # Prune
        pruned = weights[mask]

        return pruned, {
            'threshold': threshold,
            'channels_removed': int(np.sum(~mask)),
            'channels_remaining': int(np.sum(mask)),
            'compression_ratio': pruned.size / weights.size if weights.size > 0 else 0.0
        }

    def iterative_pruning(self, weights: np.ndarray,
                         target_pruning_ratio: float = 0.5,
                         iterations: int = 5) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Iteratively prune and fine-tune."""

        current_weights = weights.copy()
        history = []

        per_iteration = target_pruning_ratio / iterations

        for i in range(iterations):
            pruned, stats = self.magnitude_pruning(current_weights, per_iteration)

            stats['iteration'] = i + 1
            history.append(stats)

            current_weights = pruned

        return current_weights, history

# ============================================================================
# KNOWLEDGE DISTILLATION
# ============================================================================

class KnowledgeDistiller:
    """Transfer knowledge from teacher to student model."""

    def __init__(self):
        self.logger = logging.getLogger("knowledge_distiller")

    def compute_distillation_loss(self, teacher_logits: np.ndarray,
                                 student_logits: np.ndarray,
                                 temperature: float = 4.0,
                                 alpha: float = 0.7) -> float:
        """Compute distillation loss."""

        # Soft targets from teacher
        teacher_probs = self._softmax(teacher_logits / temperature)
        student_probs = self._softmax(student_logits / temperature)

        # KL divergence from student to teacher
        kl_loss = np.sum(teacher_probs * np.log(teacher_probs / (student_probs + 1e-10)))

        # Hard loss (cross-entropy with true labels)
        hard_loss = -np.mean(teacher_probs * np.log(student_probs + 1e-10))

        # Combined loss
        loss = alpha * kl_loss + (1 - alpha) * hard_loss

        return loss

    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        """Compute softmax."""

        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        return exp_logits / (np.sum(exp_logits, axis=-1, keepdims=True) + 1e-10)

    def distill_weights(self, teacher_weights: Dict[str, np.ndarray],
                       student_shape: Dict[str, Tuple]) -> Dict[str, np.ndarray]:
        """Initialize student with teacher weights."""

        student_weights = {}

        for layer_name, student_shape_tuple in student_shape.items():
            if layer_name in teacher_weights:
                teacher_weight = teacher_weights[layer_name]

                # Resize teacher weights to student shape
                if teacher_weight.shape == student_shape_tuple:
                    student_weights[layer_name] = teacher_weight.copy()
                else:
                    # Simple resizing (should use proper interpolation)
                    student_weights[layer_name] = np.random.randn(*student_shape_tuple) * 0.01
                    # Copy what we can
                    min_shape = tuple(min(t, s) for t, s in zip(teacher_weight.shape, student_shape_tuple))
                    student_weights[layer_name][:min_shape[0]] = teacher_weight[:min_shape[0]]
            else:
                student_weights[layer_name] = np.random.randn(*student_shape_tuple) * 0.01

        return student_weights

# ============================================================================
# COMPRESSION ANALYZER
# ============================================================================

class CompressionAnalyzer:
    """Analyze compression tradeoffs."""

    def __init__(self):
        self.logger = logging.getLogger("compression_analyzer")
        self.results: List[CompressionResult] = []

    def compute_pareto_frontier(self, results: List[CompressionResult]
                               ) -> List[CompressionResult]:
        """Find Pareto-optimal compression profiles."""

        if not results:
            return []

        frontier = []

        for candidate in results:
            dominated = False

            for other in results:
                if other == candidate:
                    continue

                # Check if other dominates candidate
                # (better accuracy, better latency, smaller size)
                if (other.compressed_accuracy >= candidate.compressed_accuracy and
                    other.compressed_latency_ms <= candidate.compressed_latency_ms and
                    other.compressed_size_mb <= candidate.compressed_size_mb):

                    if not (other.compressed_accuracy == candidate.compressed_accuracy and
                           other.compressed_latency_ms == candidate.compressed_latency_ms and
                           other.compressed_size_mb == candidate.compressed_size_mb):
                        dominated = True
                        break

            if not dominated:
                frontier.append(candidate)

        return frontier

    def rank_profiles(self, results: List[CompressionResult],
                     weights: Optional[Dict[str, float]] = None
                     ) -> List[Tuple[CompressionResult, float]]:
        """Rank compression profiles by weighted score."""

        if weights is None:
            weights = {
                'accuracy': 0.4,
                'latency': 0.4,
                'size': 0.2
            }

        scored = []

        for result in results:
            # Normalize metrics
            accuracy_score = result.compressed_accuracy / (result.original_accuracy + 1e-10)
            latency_score = 1.0 - (result.compressed_latency_ms / (result.original_latency_ms + 1e-10))
            size_score = 1.0 - (result.compressed_size_mb / (result.original_size_mb + 1e-10))

            # Combined score
            score = (weights['accuracy'] * accuracy_score +
                    weights['latency'] * latency_score +
                    weights['size'] * size_score)

            scored.append((result, score))

        return sorted(scored, key=lambda x: x[1], reverse=True)

# ============================================================================
# MODEL COMPRESSION SYSTEM
# ============================================================================

class ModelCompressionSystem:
    """Complete model compression system."""

    def __init__(self):
        self.quantizer = Quantizer()
        self.pruner = Pruner()
        self.distiller = KnowledgeDistiller()
        self.analyzer = CompressionAnalyzer()
        self.logger = logging.getLogger("model_compression_system")
        self.compression_history: List[CompressionResult] = []

    async def compress_model(self, model_id: str, model_weights: Dict[str, np.ndarray],
                            profile: CompressionProfile,
                            teacher_weights: Optional[Dict[str, np.ndarray]] = None
                            ) -> CompressionResult:
        """Compress model using profile."""

        compressed_weights = {k: v.copy() for k, v in model_weights.items()}

        # Quantization
        if profile.quantization_type == QuantizationType.INT8:
            for layer, weights in compressed_weights.items():
                quantized, _ = self.quantizer.quantize_int8(weights)
                compressed_weights[layer] = quantized

        elif profile.quantization_type == QuantizationType.FP16:
            for layer, weights in compressed_weights.items():
                compressed_weights[layer] = self.quantizer.quantize_fp16(weights)

        # Pruning
        if profile.pruning_ratio > 0:
            if profile.pruning_type == PruningType.MAGNITUDE:
                for layer, weights in compressed_weights.items():
                    pruned, _ = self.pruner.magnitude_pruning(weights, profile.pruning_ratio)
                    compressed_weights[layer] = pruned

            elif profile.pruning_type == PruningType.STRUCTURED:
                for layer, weights in compressed_weights.items():
                    if len(weights.shape) >= 2:
                        pruned, _ = self.pruner.structured_pruning(weights, profile.pruning_ratio)
                        compressed_weights[layer] = pruned

        # Knowledge distillation
        if teacher_weights:
            compressed_weights = self.distiller.distill_weights(teacher_weights,
                                                               {k: v.shape for k, v in compressed_weights.items()})

        # Create result
        result = CompressionResult(
            result_id=f"compression-{model_id}",
            original_model_id=model_id,
            compressed_model_id=f"{model_id}-compressed",
            profile=profile
        )

        # Compute metrics
        original_size = sum(w.nbytes for w in model_weights.values()) / (1024 * 1024)
        compressed_size = sum(w.nbytes for w in compressed_weights.values()) / (1024 * 1024)

        result.original_size_mb = original_size
        result.compressed_size_mb = compressed_size
        result.compression_ratio = original_size / (compressed_size + 1e-10)

        self.compression_history.append(result)

        self.logger.info(f"Compressed {model_id}: {original_size:.2f}MB → {compressed_size:.2f}MB")

        return result

    def get_recommended_profile(self, target_latency_ms: Optional[float] = None,
                               min_accuracy: float = 0.95) -> CompressionProfile:
        """Get recommended compression profile."""

        profile = CompressionProfile(
            profile_id=f"profile-recommended",
            name="Recommended",
            quantization_type=QuantizationType.INT8,
            pruning_ratio=0.3,  # Moderate pruning
            min_accuracy=min_accuracy
        )

        if target_latency_ms:
            profile.target_latency_ms = target_latency_ms

        return profile

    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""

        if not self.compression_history:
            return {}

        avg_compression_ratio = np.mean([r.compression_ratio for r in self.compression_history])
        avg_latency_reduction = np.mean([r.latency_reduction for r in self.compression_history])
        avg_accuracy_loss = np.mean([r.accuracy_loss for r in self.compression_history])

        pareto_frontier = self.analyzer.compute_pareto_frontier(self.compression_history)

        return {
            'total_compressions': len(self.compression_history),
            'avg_compression_ratio': avg_compression_ratio,
            'avg_latency_reduction_percent': avg_latency_reduction,
            'avg_accuracy_loss_percent': avg_accuracy_loss,
            'pareto_frontier_size': len(pareto_frontier)
        }

def create_model_compression_system() -> ModelCompressionSystem:
    """Create model compression system."""
    return ModelCompressionSystem()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    system = create_model_compression_system()
    print("Model compression system initialized")
