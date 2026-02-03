#!/usr/bin/env python3
"""
BAEL - Data Augmentation Engine
Comprehensive data augmentation for ML pipelines.

Features:
- Text augmentation (synonym, back-translation simulation)
- Numerical augmentation (noise, scaling, jittering)
- Structured data augmentation (SMOTE-style)
- Composition and chaining
- Probability-based augmentation
"""

import asyncio
import math
import random
import re
import string
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Sequence, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AugmentationType(Enum):
    """Types of augmentation."""
    TEXT = "text"
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    STRUCTURED = "structured"
    MIXED = "mixed"


class TextAugmentMethod(Enum):
    """Text augmentation methods."""
    SYNONYM = "synonym"
    RANDOM_SWAP = "random_swap"
    RANDOM_DELETE = "random_delete"
    RANDOM_INSERT = "random_insert"
    BACK_TRANSLATE = "back_translate"
    CHAR_NOISE = "char_noise"
    WORD_SPLIT = "word_split"
    CASE_CHANGE = "case_change"


class NumericalAugmentMethod(Enum):
    """Numerical augmentation methods."""
    GAUSSIAN_NOISE = "gaussian_noise"
    UNIFORM_NOISE = "uniform_noise"
    SCALING = "scaling"
    JITTERING = "jittering"
    MIXUP = "mixup"
    CUTOUT = "cutout"
    FEATURE_DROPOUT = "feature_dropout"


class AugmentationMode(Enum):
    """Augmentation application mode."""
    REPLACE = "replace"
    APPEND = "append"
    PROBABILISTIC = "probabilistic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class AugmentedSample:
    """An augmented data sample."""
    original: Any = None
    augmented: Any = None
    method: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class AugmentationResult:
    """Result of augmentation operation."""
    samples: List[AugmentedSample] = field(default_factory=list)
    original_count: int = 0
    augmented_count: int = 0
    methods_used: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    processing_time: float = 0.0


@dataclass
class AugmentationConfig:
    """Configuration for augmentation."""
    probability: float = 0.5
    min_augmentations: int = 1
    max_augmentations: int = 3
    preserve_labels: bool = True
    seed: Optional[int] = None


@dataclass
class TextAugmentConfig:
    """Text-specific augmentation config."""
    swap_probability: float = 0.1
    delete_probability: float = 0.1
    insert_probability: float = 0.1
    char_noise_probability: float = 0.05
    min_word_length: int = 3


@dataclass
class NumericalAugmentConfig:
    """Numerical augmentation config."""
    noise_std: float = 0.1
    noise_range: Tuple[float, float] = (-0.1, 0.1)
    scale_range: Tuple[float, float] = (0.9, 1.1)
    dropout_probability: float = 0.1
    mixup_alpha: float = 0.2


# =============================================================================
# BASE AUGMENTOR
# =============================================================================

class BaseAugmentor(ABC):
    """Abstract base augmentor."""

    def __init__(
        self,
        config: Optional[AugmentationConfig] = None,
        name: Optional[str] = None
    ):
        self.config = config or AugmentationConfig()
        self.name = name or self.__class__.__name__

        if self.config.seed is not None:
            random.seed(self.config.seed)

    @abstractmethod
    def augment(self, data: Any) -> Any:
        """Augment a single sample."""
        pass

    def should_augment(self) -> bool:
        """Probabilistic check for augmentation."""
        return random.random() < self.config.probability

    def augment_batch(
        self,
        data: List[Any],
        mode: AugmentationMode = AugmentationMode.APPEND
    ) -> List[AugmentedSample]:
        """Augment a batch of data."""
        results = []

        for sample in data:
            if mode == AugmentationMode.PROBABILISTIC:
                if not self.should_augment():
                    results.append(AugmentedSample(
                        original=sample,
                        augmented=sample,
                        method="none",
                        confidence=1.0
                    ))
                    continue

            augmented = self.augment(sample)
            results.append(AugmentedSample(
                original=sample,
                augmented=augmented,
                method=self.name,
                confidence=0.9
            ))

            if mode == AugmentationMode.APPEND:
                results.append(AugmentedSample(
                    original=sample,
                    augmented=sample,
                    method="original",
                    confidence=1.0
                ))

        return results


# =============================================================================
# TEXT AUGMENTORS
# =============================================================================

class SynonymAugmentor(BaseAugmentor):
    """Synonym-based text augmentation."""

    def __init__(
        self,
        synonyms: Optional[Dict[str, List[str]]] = None,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "SynonymAugmentor")

        self._synonyms = synonyms or {
            "good": ["great", "excellent", "fine", "nice"],
            "bad": ["poor", "terrible", "awful", "horrible"],
            "happy": ["joyful", "glad", "pleased", "delighted"],
            "sad": ["unhappy", "sorrowful", "dejected", "gloomy"],
            "big": ["large", "huge", "enormous", "massive"],
            "small": ["tiny", "little", "miniature", "compact"],
            "fast": ["quick", "rapid", "speedy", "swift"],
            "slow": ["sluggish", "gradual", "unhurried", "leisurely"],
            "smart": ["intelligent", "clever", "brilliant", "wise"],
            "beautiful": ["pretty", "gorgeous", "lovely", "stunning"]
        }

    def augment(self, text: str) -> str:
        """Replace words with synonyms."""
        words = text.split()
        augmented = []

        for word in words:
            lower_word = word.lower()

            if lower_word in self._synonyms and random.random() < 0.3:
                synonym = random.choice(self._synonyms[lower_word])

                if word[0].isupper():
                    synonym = synonym.capitalize()

                augmented.append(synonym)
            else:
                augmented.append(word)

        return " ".join(augmented)


class RandomSwapAugmentor(BaseAugmentor):
    """Randomly swap adjacent words."""

    def __init__(
        self,
        swap_ratio: float = 0.1,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "RandomSwapAugmentor")
        self._swap_ratio = swap_ratio

    def augment(self, text: str) -> str:
        """Swap random adjacent words."""
        words = text.split()

        if len(words) < 2:
            return text

        num_swaps = max(1, int(len(words) * self._swap_ratio))

        for _ in range(num_swaps):
            idx = random.randint(0, len(words) - 2)
            words[idx], words[idx + 1] = words[idx + 1], words[idx]

        return " ".join(words)


class RandomDeleteAugmentor(BaseAugmentor):
    """Randomly delete words."""

    def __init__(
        self,
        delete_ratio: float = 0.1,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "RandomDeleteAugmentor")
        self._delete_ratio = delete_ratio

    def augment(self, text: str) -> str:
        """Delete random words."""
        words = text.split()

        if len(words) < 3:
            return text

        kept = [w for w in words if random.random() > self._delete_ratio]

        if not kept:
            return words[0]

        return " ".join(kept)


class RandomInsertAugmentor(BaseAugmentor):
    """Randomly insert words."""

    def __init__(
        self,
        insert_ratio: float = 0.1,
        word_pool: Optional[List[str]] = None,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "RandomInsertAugmentor")
        self._insert_ratio = insert_ratio
        self._word_pool = word_pool or [
            "very", "really", "quite", "somewhat", "rather",
            "actually", "basically", "essentially", "indeed", "certainly"
        ]

    def augment(self, text: str) -> str:
        """Insert random words."""
        words = text.split()
        num_inserts = max(1, int(len(words) * self._insert_ratio))

        for _ in range(num_inserts):
            idx = random.randint(0, len(words))
            word = random.choice(self._word_pool)
            words.insert(idx, word)

        return " ".join(words)


class CharNoiseAugmentor(BaseAugmentor):
    """Add character-level noise to text."""

    def __init__(
        self,
        noise_ratio: float = 0.05,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "CharNoiseAugmentor")
        self._noise_ratio = noise_ratio
        self._chars = string.ascii_lowercase

    def augment(self, text: str) -> str:
        """Add character noise."""
        chars = list(text)

        for i in range(len(chars)):
            if chars[i].isalpha() and random.random() < self._noise_ratio:
                noise_type = random.choice(["replace", "insert", "delete", "swap"])

                if noise_type == "replace":
                    chars[i] = random.choice(self._chars)
                elif noise_type == "insert":
                    chars[i] = chars[i] + random.choice(self._chars)
                elif noise_type == "delete" and len(chars[i]) > 0:
                    chars[i] = ""
                elif noise_type == "swap" and i < len(chars) - 1:
                    chars[i], chars[i + 1] = chars[i + 1], chars[i]

        return "".join(chars)


class CaseChangeAugmentor(BaseAugmentor):
    """Change case of words."""

    def __init__(
        self,
        change_ratio: float = 0.1,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "CaseChangeAugmentor")
        self._change_ratio = change_ratio

    def augment(self, text: str) -> str:
        """Change word cases randomly."""
        words = text.split()

        for i in range(len(words)):
            if random.random() < self._change_ratio:
                change = random.choice(["upper", "lower", "title", "swap"])

                if change == "upper":
                    words[i] = words[i].upper()
                elif change == "lower":
                    words[i] = words[i].lower()
                elif change == "title":
                    words[i] = words[i].title()
                elif change == "swap":
                    words[i] = words[i].swapcase()

        return " ".join(words)


# =============================================================================
# NUMERICAL AUGMENTORS
# =============================================================================

class GaussianNoiseAugmentor(BaseAugmentor):
    """Add Gaussian noise to numerical data."""

    def __init__(
        self,
        mean: float = 0.0,
        std: float = 0.1,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "GaussianNoiseAugmentor")
        self._mean = mean
        self._std = std

    def augment(self, data: List[float]) -> List[float]:
        """Add Gaussian noise."""
        return [
            x + random.gauss(self._mean, self._std)
            for x in data
        ]


class UniformNoiseAugmentor(BaseAugmentor):
    """Add uniform noise to numerical data."""

    def __init__(
        self,
        low: float = -0.1,
        high: float = 0.1,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "UniformNoiseAugmentor")
        self._low = low
        self._high = high

    def augment(self, data: List[float]) -> List[float]:
        """Add uniform noise."""
        return [
            x + random.uniform(self._low, self._high)
            for x in data
        ]


class ScalingAugmentor(BaseAugmentor):
    """Scale numerical data."""

    def __init__(
        self,
        scale_range: Tuple[float, float] = (0.9, 1.1),
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "ScalingAugmentor")
        self._scale_range = scale_range

    def augment(self, data: List[float]) -> List[float]:
        """Scale data."""
        scale = random.uniform(*self._scale_range)
        return [x * scale for x in data]


class JitteringAugmentor(BaseAugmentor):
    """Add jitter to numerical data."""

    def __init__(
        self,
        jitter_std: float = 0.03,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "JitteringAugmentor")
        self._jitter_std = jitter_std

    def augment(self, data: List[float]) -> List[float]:
        """Add jitter."""
        return [
            x * (1 + random.gauss(0, self._jitter_std))
            for x in data
        ]


class FeatureDropoutAugmentor(BaseAugmentor):
    """Drop random features."""

    def __init__(
        self,
        dropout_prob: float = 0.1,
        fill_value: float = 0.0,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "FeatureDropoutAugmentor")
        self._dropout_prob = dropout_prob
        self._fill_value = fill_value

    def augment(self, data: List[float]) -> List[float]:
        """Drop features."""
        return [
            self._fill_value if random.random() < self._dropout_prob else x
            for x in data
        ]


class MixupAugmentor(BaseAugmentor):
    """Mixup augmentation for pairs."""

    def __init__(
        self,
        alpha: float = 0.2,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "MixupAugmentor")
        self._alpha = alpha

    def augment_pair(
        self,
        data1: List[float],
        data2: List[float]
    ) -> Tuple[List[float], float]:
        """Mix two samples."""
        if len(data1) != len(data2):
            return data1, 1.0

        lam = random.betavariate(self._alpha, self._alpha)
        mixed = [lam * x1 + (1 - lam) * x2 for x1, x2 in zip(data1, data2)]

        return mixed, lam

    def augment(self, data: List[float]) -> List[float]:
        """Single sample - no mixup possible."""
        return data


# =============================================================================
# COMPOSITION
# =============================================================================

class ComposedAugmentor(BaseAugmentor):
    """Compose multiple augmentors."""

    def __init__(
        self,
        augmentors: List[BaseAugmentor],
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "ComposedAugmentor")
        self._augmentors = augmentors

    def augment(self, data: Any) -> Any:
        """Apply all augmentors sequentially."""
        result = data

        for aug in self._augmentors:
            if aug.should_augment():
                result = aug.augment(result)

        return result


class RandomChoiceAugmentor(BaseAugmentor):
    """Randomly choose one augmentor."""

    def __init__(
        self,
        augmentors: List[BaseAugmentor],
        weights: Optional[List[float]] = None,
        config: Optional[AugmentationConfig] = None
    ):
        super().__init__(config, "RandomChoiceAugmentor")
        self._augmentors = augmentors
        self._weights = weights

    def augment(self, data: Any) -> Any:
        """Apply randomly chosen augmentor."""
        if self._weights:
            aug = random.choices(self._augmentors, weights=self._weights)[0]
        else:
            aug = random.choice(self._augmentors)

        return aug.augment(data)


# =============================================================================
# AUGMENTATION ENGINE
# =============================================================================

class AugmentorEngine:
    """
    Data Augmentation Engine for BAEL.

    Comprehensive augmentation for ML pipelines.
    """

    def __init__(self):
        self._augmentors: Dict[str, BaseAugmentor] = {}
        self._pipelines: Dict[str, List[str]] = {}

    def register_augmentor(
        self,
        name: str,
        augmentor: BaseAugmentor
    ) -> None:
        """Register an augmentor."""
        self._augmentors[name] = augmentor

    def create_text_augmentor(
        self,
        method: TextAugmentMethod,
        config: Optional[AugmentationConfig] = None,
        **kwargs
    ) -> BaseAugmentor:
        """Create text augmentor."""
        if method == TextAugmentMethod.SYNONYM:
            return SynonymAugmentor(config=config, **kwargs)
        elif method == TextAugmentMethod.RANDOM_SWAP:
            return RandomSwapAugmentor(config=config, **kwargs)
        elif method == TextAugmentMethod.RANDOM_DELETE:
            return RandomDeleteAugmentor(config=config, **kwargs)
        elif method == TextAugmentMethod.RANDOM_INSERT:
            return RandomInsertAugmentor(config=config, **kwargs)
        elif method == TextAugmentMethod.CHAR_NOISE:
            return CharNoiseAugmentor(config=config, **kwargs)
        elif method == TextAugmentMethod.CASE_CHANGE:
            return CaseChangeAugmentor(config=config, **kwargs)
        else:
            return SynonymAugmentor(config=config)

    def create_numerical_augmentor(
        self,
        method: NumericalAugmentMethod,
        config: Optional[AugmentationConfig] = None,
        **kwargs
    ) -> BaseAugmentor:
        """Create numerical augmentor."""
        if method == NumericalAugmentMethod.GAUSSIAN_NOISE:
            return GaussianNoiseAugmentor(config=config, **kwargs)
        elif method == NumericalAugmentMethod.UNIFORM_NOISE:
            return UniformNoiseAugmentor(config=config, **kwargs)
        elif method == NumericalAugmentMethod.SCALING:
            return ScalingAugmentor(config=config, **kwargs)
        elif method == NumericalAugmentMethod.JITTERING:
            return JitteringAugmentor(config=config, **kwargs)
        elif method == NumericalAugmentMethod.FEATURE_DROPOUT:
            return FeatureDropoutAugmentor(config=config, **kwargs)
        elif method == NumericalAugmentMethod.MIXUP:
            return MixupAugmentor(config=config, **kwargs)
        else:
            return GaussianNoiseAugmentor(config=config)

    def create_pipeline(
        self,
        name: str,
        augmentor_names: List[str]
    ) -> ComposedAugmentor:
        """Create augmentation pipeline."""
        augmentors = [
            self._augmentors[n] for n in augmentor_names
            if n in self._augmentors
        ]

        self._pipelines[name] = augmentor_names

        composed = ComposedAugmentor(augmentors)
        self._augmentors[name] = composed

        return composed

    def augment(
        self,
        data: Any,
        augmentor_name: str
    ) -> Any:
        """Augment using named augmentor."""
        if augmentor_name not in self._augmentors:
            return data

        return self._augmentors[augmentor_name].augment(data)

    def augment_batch(
        self,
        data: List[Any],
        augmentor_name: str,
        mode: AugmentationMode = AugmentationMode.APPEND
    ) -> AugmentationResult:
        """Augment batch of data."""
        import time

        start = time.time()

        if augmentor_name not in self._augmentors:
            return AugmentationResult()

        aug = self._augmentors[augmentor_name]
        samples = aug.augment_batch(data, mode)

        end = time.time()

        return AugmentationResult(
            samples=samples,
            original_count=len(data),
            augmented_count=len(samples),
            methods_used=[augmentor_name],
            success_rate=1.0,
            processing_time=end - start
        )

    def augment_dataset(
        self,
        data: List[Any],
        augmentor_name: str,
        multiplier: int = 2
    ) -> List[Any]:
        """Augment dataset with multiplier."""
        if augmentor_name not in self._augmentors:
            return data

        aug = self._augmentors[augmentor_name]
        result = list(data)

        for _ in range(multiplier - 1):
            for sample in data:
                result.append(aug.augment(sample))

        return result


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Augmentation Engine."""
    print("=" * 70)
    print("BAEL - DATA AUGMENTATION ENGINE DEMO")
    print("Comprehensive Data Augmentation for ML Pipelines")
    print("=" * 70)
    print()

    engine = AugmentorEngine()

    # 1. Synonym Augmentation
    print("1. SYNONYM AUGMENTATION:")
    print("-" * 40)

    syn_aug = engine.create_text_augmentor(TextAugmentMethod.SYNONYM)
    engine.register_augmentor("synonym", syn_aug)

    text = "This is a good and beautiful day with fast cars."
    augmented = engine.augment(text, "synonym")

    print(f"   Original: {text}")
    print(f"   Augmented: {augmented}")
    print()

    # 2. Random Swap
    print("2. RANDOM SWAP:")
    print("-" * 40)

    swap_aug = engine.create_text_augmentor(TextAugmentMethod.RANDOM_SWAP)
    engine.register_augmentor("swap", swap_aug)

    text = "The quick brown fox jumps over the lazy dog"
    augmented = engine.augment(text, "swap")

    print(f"   Original: {text}")
    print(f"   Augmented: {augmented}")
    print()

    # 3. Random Delete
    print("3. RANDOM DELETE:")
    print("-" * 40)

    del_aug = engine.create_text_augmentor(TextAugmentMethod.RANDOM_DELETE)
    engine.register_augmentor("delete", del_aug)

    augmented = engine.augment(text, "delete")

    print(f"   Original: {text}")
    print(f"   Augmented: {augmented}")
    print()

    # 4. Character Noise
    print("4. CHARACTER NOISE:")
    print("-" * 40)

    noise_aug = engine.create_text_augmentor(TextAugmentMethod.CHAR_NOISE)
    engine.register_augmentor("char_noise", noise_aug)

    augmented = engine.augment(text, "char_noise")

    print(f"   Original: {text}")
    print(f"   Augmented: {augmented}")
    print()

    # 5. Gaussian Noise
    print("5. GAUSSIAN NOISE (NUMERICAL):")
    print("-" * 40)

    gauss_aug = engine.create_numerical_augmentor(
        NumericalAugmentMethod.GAUSSIAN_NOISE,
        std=0.1
    )
    engine.register_augmentor("gaussian", gauss_aug)

    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    augmented = engine.augment(data, "gaussian")

    print(f"   Original: {data}")
    print(f"   Augmented: {[round(x, 3) for x in augmented]}")
    print()

    # 6. Scaling
    print("6. SCALING (NUMERICAL):")
    print("-" * 40)

    scale_aug = engine.create_numerical_augmentor(
        NumericalAugmentMethod.SCALING,
        scale_range=(0.8, 1.2)
    )
    engine.register_augmentor("scaling", scale_aug)

    augmented = engine.augment(data, "scaling")

    print(f"   Original: {data}")
    print(f"   Augmented: {[round(x, 3) for x in augmented]}")
    print()

    # 7. Feature Dropout
    print("7. FEATURE DROPOUT:")
    print("-" * 40)

    dropout_aug = engine.create_numerical_augmentor(
        NumericalAugmentMethod.FEATURE_DROPOUT,
        dropout_prob=0.2
    )
    engine.register_augmentor("dropout", dropout_aug)

    augmented = engine.augment(data, "dropout")

    print(f"   Original: {data}")
    print(f"   Augmented: {augmented}")
    print()

    # 8. Composed Pipeline
    print("8. COMPOSED PIPELINE:")
    print("-" * 40)

    pipeline = engine.create_pipeline("text_pipeline", ["synonym", "swap"])

    text = "This is a good example of text augmentation."
    augmented = engine.augment(text, "text_pipeline")

    print(f"   Original: {text}")
    print(f"   Augmented: {augmented}")
    print()

    # 9. Batch Augmentation
    print("9. BATCH AUGMENTATION:")
    print("-" * 40)

    texts = [
        "Hello world",
        "Good morning",
        "How are you"
    ]

    result = engine.augment_batch(texts, "synonym", AugmentationMode.APPEND)

    print(f"   Original count: {result.original_count}")
    print(f"   Augmented count: {result.augmented_count}")
    print(f"   Processing time: {result.processing_time:.4f}s")

    for sample in result.samples[:4]:
        print(f"   - {sample.original} -> {sample.augmented}")
    print()

    # 10. Dataset Augmentation
    print("10. DATASET AUGMENTATION:")
    print("-" * 40)

    data = [
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0]
    ]

    augmented = engine.augment_dataset(data, "gaussian", multiplier=3)

    print(f"   Original size: {len(data)}")
    print(f"   Augmented size: {len(augmented)}")

    for i, sample in enumerate(augmented[:4]):
        print(f"   Sample {i + 1}: {[round(x, 2) for x in sample]}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Augmentation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
