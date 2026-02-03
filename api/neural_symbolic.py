"""
Neural-Symbolic Integration for BAEL

Hybrid systems combining neural embeddings with symbolic reasoning,
attention mechanisms, and interpretable AI.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Embedding:
    """Embedding vector."""
    vector: List[float]
    entity_id: str
    entity_type: str
    model_name: str
    created_at: datetime = field(default_factory=datetime.now)

    def similarity(self, other: "Embedding") -> float:
        """Calculate cosine similarity to another embedding."""
        if len(self.vector) != len(other.vector):
            return 0.0

        dot_product = sum(a * b for a, b in zip(self.vector, other.vector))
        magnitude_self = math.sqrt(sum(x**2 for x in self.vector))
        magnitude_other = math.sqrt(sum(x**2 for x in other.vector))

        if magnitude_self == 0 or magnitude_other == 0:
            return 0.0

        return dot_product / (magnitude_self * magnitude_other)


class EmbeddingModel:
    """Neural embedding model."""

    def __init__(self, model_name: str, embedding_dim: int = 768):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.embeddings: Dict[str, Embedding] = {}

    def embed(self, text: str, entity_id: str, entity_type: str = "text") -> Embedding:
        """Create embedding for text (simplified)."""
        # In production, would use actual embedding model
        # Simple hash-based embedding for demo
        hash_val = hash(text)
        vector = [
            math.sin((hash_val + i) * 0.1) for i in range(self.embedding_dim)
        ]

        embedding = Embedding(
            vector=vector,
            entity_id=entity_id,
            entity_type=entity_type,
            model_name=self.model_name
        )

        self.embeddings[entity_id] = embedding
        return embedding

    def find_similar(self, query_embedding: Embedding, top_k: int = 5) -> List[Tuple[str, float]]:
        """Find most similar embeddings."""
        similarities = []

        for entity_id, embedding in self.embeddings.items():
            if entity_id != query_embedding.entity_id:
                sim = query_embedding.similarity(embedding)
                similarities.append((entity_id, sim))

        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]


class AttentionHead:
    """Single attention head."""

    def __init__(self, embedding_dim: int, num_heads: int = 8):
        self.embedding_dim = embedding_dim
        self.head_dim = embedding_dim // num_heads
        self.scale = math.sqrt(self.head_dim)

    def compute_attention(self, query: List[float], key: List[float],
                         value: List[float]) -> Tuple[List[float], List[float]]:
        """Compute attention weights and output."""
        # Simplified attention computation
        dot_product = sum(q * k for q, k in zip(query, key)) / self.scale
        attention_weight = 1.0 / (1.0 + math.exp(-dot_product))  # Sigmoid

        output = [attention_weight * v for v in value]
        return output, [attention_weight]


class MultiHeadAttention:
    """Multi-head attention mechanism."""

    def __init__(self, embedding_dim: int, num_heads: int = 8):
        self.embedding_dim = embedding_dim
        self.num_heads = num_heads
        self.heads = [AttentionHead(embedding_dim, num_heads) for _ in range(num_heads)]
        self.attention_weights: Dict[str, List[float]] = {}

    def forward(self, query: List[float], keys: List[List[float]],
               values: List[List[float]]) -> Tuple[List[float], Dict[str, Any]]:
        """Compute multi-head attention."""
        head_outputs = []

        for i, (key, value) in enumerate(zip(keys, values)):
            if i < len(self.heads):
                output, weight = self.heads[i].compute_attention(query, key, value)
                head_outputs.append(output)
                self.attention_weights[f"head_{i}"] = weight

        # Concatenate and project (simplified)
        final_output = []
        max_len = max(len(h) for h in head_outputs) if head_outputs else 0
        for i in range(max_len):
            final_output.append(
                sum(h[i] if i < len(h) else 0 for h in head_outputs) / len(self.heads)
                if self.heads else 0
            )

        return final_output, self.attention_weights


class SymbolicReasoner:
    """Symbolic reasoning component."""

    def __init__(self):
        self.knowledge_base: Dict[str, List[Tuple[str, str]]] = {}
        self.rules: List[Tuple[str, str, str]] = []

    def add_fact(self, entity: str, relation: str, value: str) -> None:
        """Add symbolic fact."""
        if entity not in self.knowledge_base:
            self.knowledge_base[entity] = []
        self.knowledge_base[entity].append((relation, value))

    def add_rule(self, condition1: str, condition2: str, conclusion: str) -> None:
        """Add symbolic rule."""
        self.rules.append((condition1, condition2, conclusion))

    def infer(self, query: str) -> List[str]:
        """Perform symbolic inference."""
        results = []

        # Direct lookup
        for entity, relations in self.knowledge_base.items():
            for relation, value in relations:
                if query.lower() in f"{entity}_{relation}_{value}".lower():
                    results.append(f"{entity} {relation} {value}")

        # Rule application (simplified)
        for rule in self.rules:
            if any(r in results for r in rule[:2]):
                results.append(rule[2])

        return results

    def get_explanation(self, conclusion: str) -> Dict[str, Any]:
        """Get explanation for conclusion."""
        return {
            "conclusion": conclusion,
            "facts": list(self.knowledge_base.items())[:3],
            "rules_applied": [r for r in self.rules if r[2] == conclusion],
            "confidence": 0.8
        }


class InterpretableModel:
    """Interpretable AI model."""

    def __init__(self):
        self.feature_importance: Dict[str, float] = {}
        self.decision_path: List[str] = []
        self.explanations: List[Dict[str, Any]] = []

    def set_feature_importance(self, features: Dict[str, float]) -> None:
        """Set feature importance scores."""
        self.feature_importance = features

    def generate_explanation(self, prediction: Any, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable explanation."""
        top_features = sorted(
            self.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        explanation = {
            "prediction": str(prediction),
            "top_contributing_features": top_features,
            "decision_path": self.decision_path,
            "confidence": 0.85,
            "timestamp": datetime.now().isoformat()
        }

        self.explanations.append(explanation)
        return explanation

    def get_model_transparency(self) -> Dict[str, Any]:
        """Get model transparency metrics."""
        return {
            "feature_importance": self.feature_importance,
            "num_decisions": len(self.decision_path),
            "explainability_score": sum(self.feature_importance.values()) / len(self.feature_importance) if self.feature_importance else 0,
            "recent_explanations": self.explanations[-5:]
        }


class NeuralSymbolicSystem:
    """Unified neural-symbolic system."""

    def __init__(self):
        self.embedding_model = EmbeddingModel("bael_embeddings")
        self.attention = MultiHeadAttention(768, 8)
        self.symbolic = SymbolicReasoner()
        self.interpretable = InterpretableModel()

    def hybrid_reasoning(self, query: str, embedding_context: List[float]) -> Dict[str, Any]:
        """Hybrid neural-symbolic reasoning."""
        # Neural component: embedding
        query_embedding = self.embedding_model.embed(query, "query_0")
        similar = self.embedding_model.find_similar(query_embedding, top_k=3)

        # Symbolic component: inference
        symbolic_results = self.symbolic.infer(query)

        # Combine results
        return {
            "neural_results": similar,
            "symbolic_results": symbolic_results,
            "combined_ranking": self._combine_results(similar, symbolic_results),
            "interpretability": self.interpretable.get_model_transparency()
        }

    def _combine_results(self, neural: List[Tuple[str, float]],
                        symbolic: List[str]) -> List[Tuple[str, float]]:
        """Combine neural and symbolic results."""
        combined = {}

        # Neural results
        for entity, score in neural:
            combined[entity] = combined.get(entity, 0) + score * 0.6

        # Symbolic results
        for result in symbolic:
            for entity, _ in neural:
                if entity in result:
                    combined[entity] = combined.get(entity, 0) + 0.4

        return sorted(combined.items(), key=lambda x: x[1], reverse=True)

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "embeddings": len(self.embedding_model.embeddings),
            "facts": sum(len(v) for v in self.symbolic.knowledge_base.values()),
            "rules": len(self.symbolic.rules),
            "interpretability": self.interpretable.get_model_transparency(),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
_neural_symbolic = None


def get_neural_symbolic_system() -> NeuralSymbolicSystem:
    """Get or create global neural-symbolic system."""
    global _neural_symbolic
    if _neural_symbolic is None:
        _neural_symbolic = NeuralSymbolicSystem()
    return _neural_symbolic
