"""
⚡ REALITY FUSION ⚡
===================
Multi-modal reality integration.

Features:
- Multiple modality support
- Fusion strategies
- Consistency checking
- Reality coherence
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class ModalityType(Enum):
    """Types of sensory/data modalities"""
    VISUAL = auto()       # Images, video
    TEXTUAL = auto()      # Text, language
    AUDITORY = auto()     # Audio, speech
    NUMERICAL = auto()    # Numbers, measurements
    SYMBOLIC = auto()     # Symbols, code
    TEMPORAL = auto()     # Time series
    SPATIAL = auto()      # 3D data
    GRAPH = auto()        # Graph structures
    EMBEDDING = auto()    # Vector embeddings


@dataclass
class ModalityData:
    """Data from a specific modality"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    modality: ModalityType = ModalityType.TEXTUAL

    # Raw data
    data: Any = None

    # Processed features
    features: Optional[np.ndarray] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class FusionStrategy(Enum):
    """Strategies for fusing modalities"""
    EARLY = auto()        # Fuse features early
    LATE = auto()         # Fuse decisions late
    HYBRID = auto()       # Combination
    ATTENTION = auto()    # Attention-based
    HIERARCHICAL = auto() # Hierarchical fusion


class ModalityFusion:
    """
    Fuses information from multiple modalities.
    """

    def __init__(
        self,
        strategy: FusionStrategy = FusionStrategy.LATE,
        weights: Dict[ModalityType, float] = None
    ):
        self.strategy = strategy
        self.weights = weights or {}

        # Default weights
        for modality in ModalityType:
            if modality not in self.weights:
                self.weights[modality] = 1.0

        # Normalize weights
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

    def fuse_early(
        self,
        modalities: List[ModalityData]
    ) -> np.ndarray:
        """Early fusion: concatenate features"""
        features = []

        for mod in modalities:
            if mod.features is not None:
                # Weight by modality
                weight = self.weights.get(mod.modality, 1.0)
                weighted = mod.features * weight * mod.confidence
                features.append(weighted)

        if not features:
            return np.array([])

        return np.concatenate(features)

    def fuse_late(
        self,
        predictions: Dict[ModalityType, Dict[str, float]]
    ) -> Dict[str, float]:
        """Late fusion: combine predictions"""
        combined = defaultdict(float)
        total_weight = defaultdict(float)

        for modality, preds in predictions.items():
            weight = self.weights.get(modality, 1.0)

            for key, value in preds.items():
                combined[key] += value * weight
                total_weight[key] += weight

        return {
            key: combined[key] / total_weight[key]
            for key in combined
        }

    def fuse_attention(
        self,
        modalities: List[ModalityData],
        query: np.ndarray
    ) -> np.ndarray:
        """Attention-based fusion"""
        if not modalities:
            return np.array([])

        # Compute attention scores
        scores = []
        for mod in modalities:
            if mod.features is not None:
                # Dot product attention
                score = np.dot(query, mod.features) / (
                    np.linalg.norm(query) * np.linalg.norm(mod.features) + 1e-10
                )
                scores.append(score * mod.confidence)
            else:
                scores.append(0.0)

        # Softmax
        scores = np.array(scores)
        exp_scores = np.exp(scores - np.max(scores))
        attention = exp_scores / (np.sum(exp_scores) + 1e-10)

        # Weighted combination
        result = np.zeros_like(modalities[0].features)
        for i, mod in enumerate(modalities):
            if mod.features is not None:
                result += attention[i] * mod.features

        return result

    def fuse(
        self,
        modalities: List[ModalityData],
        **kwargs
    ) -> Any:
        """Fuse modalities according to strategy"""
        if self.strategy == FusionStrategy.EARLY:
            return self.fuse_early(modalities)
        elif self.strategy == FusionStrategy.LATE:
            preds = kwargs.get('predictions', {})
            return self.fuse_late(preds)
        elif self.strategy == FusionStrategy.ATTENTION:
            query = kwargs.get('query', np.random.randn(100))
            return self.fuse_attention(modalities, query)
        else:
            return self.fuse_early(modalities)


@dataclass
class Inconsistency:
    """Detected inconsistency between modalities"""
    modality_a: ModalityType
    modality_b: ModalityType
    description: str
    severity: float  # 0-1
    resolution: Optional[str] = None


class ConsistencyChecker:
    """
    Checks consistency across modalities.
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

        # Consistency rules
        self.rules: List[Callable[[List[ModalityData]], Optional[Inconsistency]]] = []

    def add_rule(
        self,
        rule: Callable[[List[ModalityData]], Optional[Inconsistency]]
    ):
        """Add consistency rule"""
        self.rules.append(rule)

    def check_feature_consistency(
        self,
        modalities: List[ModalityData]
    ) -> List[Inconsistency]:
        """Check feature-level consistency"""
        inconsistencies = []

        # Compare pairwise
        for i, mod_a in enumerate(modalities):
            for mod_b in modalities[i + 1:]:
                if mod_a.features is None or mod_b.features is None:
                    continue

                # Compute similarity
                if len(mod_a.features) == len(mod_b.features):
                    similarity = np.dot(mod_a.features, mod_b.features) / (
                        np.linalg.norm(mod_a.features) *
                        np.linalg.norm(mod_b.features) + 1e-10
                    )

                    if similarity < self.threshold:
                        inconsistencies.append(Inconsistency(
                            modality_a=mod_a.modality,
                            modality_b=mod_b.modality,
                            description=f"Low feature similarity: {similarity:.2f}",
                            severity=1 - similarity
                        ))

        return inconsistencies

    def check_temporal_consistency(
        self,
        modalities: List[ModalityData]
    ) -> List[Inconsistency]:
        """Check temporal consistency"""
        inconsistencies = []

        # Sort by timestamp
        sorted_mods = sorted(modalities, key=lambda m: m.timestamp)

        for i in range(len(sorted_mods) - 1):
            curr = sorted_mods[i]
            next_mod = sorted_mods[i + 1]

            # Check for large time gaps
            gap = (next_mod.timestamp - curr.timestamp).total_seconds()

            if gap > 3600:  # 1 hour
                inconsistencies.append(Inconsistency(
                    modality_a=curr.modality,
                    modality_b=next_mod.modality,
                    description=f"Large temporal gap: {gap:.0f}s",
                    severity=min(gap / 86400, 1.0)
                ))

        return inconsistencies

    def check(
        self,
        modalities: List[ModalityData]
    ) -> List[Inconsistency]:
        """Run all consistency checks"""
        inconsistencies = []

        # Built-in checks
        inconsistencies.extend(self.check_feature_consistency(modalities))
        inconsistencies.extend(self.check_temporal_consistency(modalities))

        # Custom rules
        for rule in self.rules:
            result = rule(modalities)
            if result:
                inconsistencies.append(result)

        return inconsistencies


class RealityFusion:
    """
    Comprehensive reality fusion system.

    Integrates multi-modal information into coherent reality model.
    """

    def __init__(self):
        self.modalities: Dict[str, ModalityData] = {}
        self.by_type: Dict[ModalityType, List[str]] = defaultdict(list)

        # Fusion and consistency
        self.fusion = ModalityFusion()
        self.checker = ConsistencyChecker()

        # Fused representation
        self.fused_representation: Optional[np.ndarray] = None
        self.reality_coherence: float = 1.0

    def add_modality(
        self,
        modality_type: ModalityType,
        data: Any,
        features: np.ndarray = None,
        confidence: float = 1.0,
        source: str = ""
    ) -> ModalityData:
        """Add modality data"""
        mod = ModalityData(
            modality=modality_type,
            data=data,
            features=features,
            confidence=confidence,
            source=source
        )

        self.modalities[mod.id] = mod
        self.by_type[modality_type].append(mod.id)

        return mod

    def get_modalities(
        self,
        modality_type: ModalityType = None
    ) -> List[ModalityData]:
        """Get modality data"""
        if modality_type:
            return [
                self.modalities[mid]
                for mid in self.by_type.get(modality_type, [])
            ]
        return list(self.modalities.values())

    def fuse(self) -> np.ndarray:
        """Fuse all modalities"""
        mods = self.get_modalities()
        self.fused_representation = self.fusion.fuse(mods)
        return self.fused_representation

    def check_coherence(self) -> Tuple[float, List[Inconsistency]]:
        """Check reality coherence"""
        mods = self.get_modalities()
        inconsistencies = self.checker.check(mods)

        if inconsistencies:
            total_severity = sum(i.severity for i in inconsistencies)
            self.reality_coherence = max(0, 1 - total_severity / len(mods))
        else:
            self.reality_coherence = 1.0

        return self.reality_coherence, inconsistencies

    def resolve_inconsistencies(
        self,
        inconsistencies: List[Inconsistency]
    ):
        """Attempt to resolve inconsistencies"""
        for inc in inconsistencies:
            # Simple resolution: trust higher confidence modality
            mods_a = self.get_modalities(inc.modality_a)
            mods_b = self.get_modalities(inc.modality_b)

            if mods_a and mods_b:
                avg_conf_a = np.mean([m.confidence for m in mods_a])
                avg_conf_b = np.mean([m.confidence for m in mods_b])

                # Downweight lower confidence modality
                target_type = inc.modality_b if avg_conf_a > avg_conf_b else inc.modality_a

                for mid in self.by_type.get(target_type, []):
                    self.modalities[mid].confidence *= 0.5

                inc.resolution = f"Downweighted {target_type.name}"

    def synthesize_reality(self) -> Dict[str, Any]:
        """Synthesize coherent reality model"""
        # Fuse modalities
        fused = self.fuse()

        # Check coherence
        coherence, inconsistencies = self.check_coherence()

        # Resolve if needed
        if coherence < 0.8:
            self.resolve_inconsistencies(inconsistencies)
            fused = self.fuse()
            coherence, _ = self.check_coherence()

        return {
            'fused_representation': fused,
            'coherence': coherence,
            'num_modalities': len(self.modalities),
            'modality_types': list(self.by_type.keys()),
            'inconsistencies_resolved': len([i for i in inconsistencies if i.resolution])
        }


# Export all
__all__ = [
    'ModalityType',
    'ModalityData',
    'FusionStrategy',
    'ModalityFusion',
    'Inconsistency',
    'ConsistencyChecker',
    'RealityFusion',
]
