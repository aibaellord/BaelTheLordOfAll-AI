"""
⚡ HYPERDIMENSIONAL CLASSIFIER ⚡
=================================
Machine learning with hyperdimensional computing.

Advantages over neural networks:
- One-shot learning
- Interpretable representations
- Constant-time inference
- Hardware-efficient (binary operations)
- Robust to noise
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from .hyperdimensional_core import (
    HyperdimensionalVector,
    HyperdimensionalSpace,
    HDBinding,
    HDBundling,
    HDPermutation,
    HDSimilarity,
    VectorType,
)


@dataclass
class ClassPrototype:
    """Prototype vector for a class"""
    class_name: str
    vector: HyperdimensionalVector
    sample_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EncodedSample:
    """An encoded data sample"""
    id: str
    features: Dict[str, Any]
    vector: HyperdimensionalVector
    label: Optional[str] = None


class HDEncoder:
    """
    Encodes various data types as HD vectors.
    """

    def __init__(
        self,
        dimension: int = 10000,
        vector_type: VectorType = VectorType.BIPOLAR
    ):
        self.dimension = dimension
        self.vector_type = vector_type
        self.space = HyperdimensionalSpace(dimension, vector_type)

        # Feature encoders
        self.feature_vectors: Dict[str, HyperdimensionalVector] = {}
        self.value_vectors: Dict[str, Dict[str, HyperdimensionalVector]] = {}
        self.level_vectors: Dict[str, List[HyperdimensionalVector]] = {}

    def _get_feature_vector(self, feature_name: str) -> HyperdimensionalVector:
        """Get or create feature vector"""
        if feature_name not in self.feature_vectors:
            self.feature_vectors[feature_name] = HyperdimensionalVector.from_seed(
                f"feature:{feature_name}", self.dimension
            )
        return self.feature_vectors[feature_name]

    def _get_value_vector(
        self,
        feature_name: str,
        value: str
    ) -> HyperdimensionalVector:
        """Get or create value vector for categorical feature"""
        if feature_name not in self.value_vectors:
            self.value_vectors[feature_name] = {}

        if value not in self.value_vectors[feature_name]:
            self.value_vectors[feature_name][value] = HyperdimensionalVector.from_seed(
                f"value:{feature_name}:{value}", self.dimension
            )

        return self.value_vectors[feature_name][value]

    def _get_level_vectors(
        self,
        feature_name: str,
        num_levels: int = 100
    ) -> List[HyperdimensionalVector]:
        """Get or create level vectors for quantized encoding"""
        if feature_name not in self.level_vectors:
            # Create correlated level vectors
            base = HyperdimensionalVector.random(self.dimension, self.vector_type)
            levels = [base]

            for i in range(1, num_levels):
                # Each level is slightly different from previous
                flip_count = self.dimension // num_levels
                next_level = levels[-1].vector.copy()
                flip_idx = np.random.choice(
                    self.dimension, flip_count, replace=False
                )
                next_level[flip_idx] *= -1
                levels.append(HyperdimensionalVector(
                    vector=next_level,
                    dimension=self.dimension,
                    vector_type=self.vector_type
                ))

            self.level_vectors[feature_name] = levels

        return self.level_vectors[feature_name]

    def encode_categorical(
        self,
        feature_name: str,
        value: str
    ) -> HyperdimensionalVector:
        """Encode categorical feature"""
        feature_vec = self._get_feature_vector(feature_name)
        value_vec = self._get_value_vector(feature_name, value)
        return HDBinding.bind(feature_vec, value_vec)

    def encode_numerical(
        self,
        feature_name: str,
        value: float,
        min_val: float = 0.0,
        max_val: float = 1.0,
        num_levels: int = 100
    ) -> HyperdimensionalVector:
        """
        Encode numerical feature using thermometer encoding.

        Similar values get similar vectors.
        """
        feature_vec = self._get_feature_vector(feature_name)
        levels = self._get_level_vectors(feature_name, num_levels)

        # Normalize value
        normalized = (value - min_val) / (max_val - min_val + 1e-10)
        normalized = max(0, min(1, normalized))

        # Get level index
        level_idx = int(normalized * (num_levels - 1))
        level_vec = levels[level_idx]

        return HDBinding.bind(feature_vec, level_vec)

    def encode_text(
        self,
        feature_name: str,
        text: str,
        ngram_size: int = 3
    ) -> HyperdimensionalVector:
        """
        Encode text using n-gram encoding.
        """
        feature_vec = self._get_feature_vector(feature_name)

        # Generate n-grams
        ngrams = []
        for i in range(len(text) - ngram_size + 1):
            ngram = text[i:i+ngram_size]
            ngram_vec = HyperdimensionalVector.from_seed(
                f"ngram:{ngram}", self.dimension
            )
            # Position encode
            ngram_vec = ngram_vec.permute(i)
            ngrams.append(ngram_vec)

        if not ngrams:
            return feature_vec

        text_vec = HDBundling.bundle(ngrams)
        return HDBinding.bind(feature_vec, text_vec)

    def encode_sequence(
        self,
        feature_name: str,
        items: List[str]
    ) -> HyperdimensionalVector:
        """Encode sequence with position"""
        feature_vec = self._get_feature_vector(feature_name)

        item_vecs = []
        for i, item in enumerate(items):
            item_vec = HyperdimensionalVector.from_seed(
                f"item:{item}", self.dimension
            )
            item_vecs.append(item_vec.permute(i))

        if not item_vecs:
            return feature_vec

        seq_vec = HDBundling.bundle(item_vecs)
        return HDBinding.bind(feature_vec, seq_vec)

    def encode_image(
        self,
        feature_name: str,
        image: np.ndarray,
        patch_size: int = 4
    ) -> HyperdimensionalVector:
        """
        Encode image using patch encoding.
        """
        feature_vec = self._get_feature_vector(feature_name)

        h, w = image.shape[:2]
        patches = []

        for i in range(0, h - patch_size + 1, patch_size):
            for j in range(0, w - patch_size + 1, patch_size):
                patch = image[i:i+patch_size, j:j+patch_size]

                # Hash patch to vector
                patch_hash = hash(patch.tobytes())
                patch_vec = HyperdimensionalVector.from_seed(
                    f"patch:{patch_hash}", self.dimension
                )

                # Position encode
                pos = i * (w // patch_size) + j
                patch_vec = patch_vec.permute(pos % self.dimension)
                patches.append(patch_vec)

        if not patches:
            return feature_vec

        img_vec = HDBundling.bundle(patches)
        return HDBinding.bind(feature_vec, img_vec)

    def encode_sample(
        self,
        features: Dict[str, Any]
    ) -> HyperdimensionalVector:
        """
        Encode complete sample with multiple features.
        """
        encoded_features = []

        for name, value in features.items():
            if isinstance(value, str):
                enc = self.encode_categorical(name, value)
            elif isinstance(value, (int, float)):
                enc = self.encode_numerical(name, float(value))
            elif isinstance(value, list):
                if all(isinstance(v, str) for v in value):
                    enc = self.encode_sequence(name, value)
                else:
                    enc = self.encode_numerical(name, np.mean(value))
            elif isinstance(value, np.ndarray):
                if len(value.shape) == 2:
                    enc = self.encode_image(name, value)
                else:
                    enc = self.encode_numerical(name, np.mean(value))
            else:
                enc = self.encode_categorical(name, str(value))

            encoded_features.append(enc)

        if not encoded_features:
            return HyperdimensionalVector(dimension=self.dimension)

        return HDBundling.bundle(encoded_features)


class HDClassifier:
    """
    Hyperdimensional classifier.

    Works by:
    1. Encoding samples as HD vectors
    2. Bundling samples per class to create prototypes
    3. Classifying by nearest prototype
    """

    def __init__(
        self,
        dimension: int = 10000,
        vector_type: VectorType = VectorType.BIPOLAR
    ):
        self.dimension = dimension
        self.vector_type = vector_type
        self.encoder = HDEncoder(dimension, vector_type)

        self.prototypes: Dict[str, ClassPrototype] = {}
        self.samples: List[EncodedSample] = []

    def train(
        self,
        samples: List[Dict[str, Any]],
        labels: List[str]
    ):
        """
        Train classifier on samples.

        Encodes all samples and creates class prototypes.
        """
        # Group by class
        class_samples: Dict[str, List[HyperdimensionalVector]] = {}

        for features, label in zip(samples, labels):
            encoded = self.encoder.encode_sample(features)

            if label not in class_samples:
                class_samples[label] = []
            class_samples[label].append(encoded)

            self.samples.append(EncodedSample(
                id=str(uuid.uuid4()),
                features=features,
                vector=encoded,
                label=label
            ))

        # Create prototypes by bundling
        for class_name, vectors in class_samples.items():
            prototype_vec = HDBundling.bundle(vectors).binarize()

            self.prototypes[class_name] = ClassPrototype(
                class_name=class_name,
                vector=prototype_vec,
                sample_count=len(vectors)
            )

    def train_one(
        self,
        features: Dict[str, Any],
        label: str
    ):
        """
        One-shot learning: add single sample to class.
        """
        encoded = self.encoder.encode_sample(features)

        if label not in self.prototypes:
            self.prototypes[label] = ClassPrototype(
                class_name=label,
                vector=encoded,
                sample_count=1
            )
        else:
            # Bundle with existing prototype
            existing = self.prototypes[label]
            new_vec = HDBundling.bundle([existing.vector, encoded]).binarize()
            self.prototypes[label] = ClassPrototype(
                class_name=label,
                vector=new_vec,
                sample_count=existing.sample_count + 1
            )

        self.samples.append(EncodedSample(
            id=str(uuid.uuid4()),
            features=features,
            vector=encoded,
            label=label
        ))

    def predict(
        self,
        features: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        Predict class for sample.

        Returns (class_name, confidence)
        """
        if not self.prototypes:
            return ("unknown", 0.0)

        encoded = self.encoder.encode_sample(features)

        best_class = None
        best_similarity = -1

        for class_name, prototype in self.prototypes.items():
            similarity = encoded.similarity(prototype.vector)
            if similarity > best_similarity:
                best_similarity = similarity
                best_class = class_name

        # Normalize confidence
        confidence = (best_similarity + 1) / 2  # Map [-1, 1] to [0, 1]

        return (best_class or "unknown", float(confidence))

    def predict_top_k(
        self,
        features: Dict[str, Any],
        k: int = 3
    ) -> List[Tuple[str, float]]:
        """Predict top-k classes"""
        if not self.prototypes:
            return []

        encoded = self.encoder.encode_sample(features)

        results = []
        for class_name, prototype in self.prototypes.items():
            similarity = encoded.similarity(prototype.vector)
            results.append((class_name, float(similarity)))

        results.sort(key=lambda x: -x[1])
        return results[:k]

    def retrain(self):
        """Retrain from stored samples"""
        if not self.samples:
            return

        # Clear prototypes
        self.prototypes.clear()

        # Group by class
        class_samples: Dict[str, List[HyperdimensionalVector]] = {}

        for sample in self.samples:
            if sample.label not in class_samples:
                class_samples[sample.label] = []
            class_samples[sample.label].append(sample.vector)

        # Create prototypes
        for class_name, vectors in class_samples.items():
            prototype_vec = HDBundling.bundle(vectors).binarize()
            self.prototypes[class_name] = ClassPrototype(
                class_name=class_name,
                vector=prototype_vec,
                sample_count=len(vectors)
            )


class AssociativeMemoryClassifier:
    """
    Classifier using associative memory.

    Stores key-value pairs where key=sample, value=label.
    Retrieval by similarity.
    """

    def __init__(self, dimension: int = 10000):
        self.dimension = dimension
        self.encoder = HDEncoder(dimension)

        # Associative memory
        self.memory_vector = np.zeros(dimension)
        self.samples: List[EncodedSample] = []

    def store(
        self,
        features: Dict[str, Any],
        label: str
    ):
        """Store sample-label association"""
        sample_vec = self.encoder.encode_sample(features)
        label_vec = HyperdimensionalVector.from_seed(f"label:{label}", self.dimension)

        # Bind sample to label
        association = HDBinding.bind(sample_vec, label_vec)

        # Add to memory
        self.memory_vector += association.vector

        # Normalize periodically
        norm = np.linalg.norm(self.memory_vector)
        if norm > 100:
            self.memory_vector /= (norm / 10)

        self.samples.append(EncodedSample(
            id=str(uuid.uuid4()),
            features=features,
            vector=sample_vec,
            label=label
        ))

    def retrieve(
        self,
        features: Dict[str, Any],
        labels: List[str]
    ) -> Tuple[str, float]:
        """
        Retrieve label for sample.

        Requires list of possible labels.
        """
        sample_vec = self.encoder.encode_sample(features)

        # Unbind sample from memory
        memory_hd = HyperdimensionalVector(
            vector=self.memory_vector,
            dimension=self.dimension
        )
        retrieved = HDBinding.unbind(memory_hd, sample_vec)

        # Match to labels
        best_label = None
        best_similarity = -1

        for label in labels:
            label_vec = HyperdimensionalVector.from_seed(
                f"label:{label}", self.dimension
            )
            similarity = retrieved.similarity(label_vec)

            if similarity > best_similarity:
                best_similarity = similarity
                best_label = label

        return (best_label or "unknown", float(best_similarity))


class OneShotLearner:
    """
    One-shot learning with hyperdimensional computing.

    Can learn from single example per class.
    """

    def __init__(self, dimension: int = 10000):
        self.dimension = dimension
        self.encoder = HDEncoder(dimension)
        self.prototypes: Dict[str, HyperdimensionalVector] = {}

    def learn(
        self,
        class_name: str,
        example: Dict[str, Any]
    ):
        """Learn class from single example"""
        self.prototypes[class_name] = self.encoder.encode_sample(example)

    def learn_few(
        self,
        class_name: str,
        examples: List[Dict[str, Any]]
    ):
        """Learn from few examples"""
        vectors = [self.encoder.encode_sample(ex) for ex in examples]
        self.prototypes[class_name] = HDBundling.bundle(vectors).binarize()

    def classify(
        self,
        sample: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Classify sample"""
        if not self.prototypes:
            return ("unknown", 0.0)

        sample_vec = self.encoder.encode_sample(sample)

        best_class = None
        best_sim = -1

        for class_name, prototype in self.prototypes.items():
            sim = sample_vec.similarity(prototype)
            if sim > best_sim:
                best_sim = sim
                best_class = class_name

        return (best_class or "unknown", float(best_sim))

    def siamese_match(
        self,
        sample_a: Dict[str, Any],
        sample_b: Dict[str, Any]
    ) -> float:
        """Compute similarity between two samples"""
        vec_a = self.encoder.encode_sample(sample_a)
        vec_b = self.encoder.encode_sample(sample_b)
        return vec_a.similarity(vec_b)


# Export all
__all__ = [
    'ClassPrototype',
    'EncodedSample',
    'HDEncoder',
    'HDClassifier',
    'AssociativeMemoryClassifier',
    'OneShotLearner',
]
