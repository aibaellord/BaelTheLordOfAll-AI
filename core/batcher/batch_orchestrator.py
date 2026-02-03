#!/usr/bin/env python3
"""
BAEL - Batch Orchestrator
Comprehensive batch processing for AI training pipelines.

Features:
- Mini-batch generation
- Data shuffling
- Batch normalization
- Dynamic batching
- Gradient accumulation batches
- Memory-efficient batching
"""

import asyncio
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class BatchingStrategy(Enum):
    """Batching strategies."""
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    STRATIFIED = "stratified"
    BUCKETED = "bucketed"
    DYNAMIC = "dynamic"


class PadMode(Enum):
    """Padding modes for variable length."""
    NONE = "none"
    ZERO = "zero"
    REPEAT = "repeat"
    REFLECT = "reflect"
    TRUNCATE = "truncate"


class BatchState(Enum):
    """Batch processing state."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class DataSample:
    """Single data sample."""
    sample_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    features: List[float] = field(default_factory=list)
    target: Optional[Any] = None
    sample_weight: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataBatch:
    """A batch of samples."""
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    samples: List[DataSample] = field(default_factory=list)
    size: int = 0
    epoch_num: int = 0
    batch_num: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.size = len(self.samples)


@dataclass
class BatchingStats:
    """Statistics for batch processing."""
    total_samples: int = 0
    total_batches: int = 0
    processed_samples: int = 0
    processed_batches: int = 0
    current_epoch: int = 0
    avg_time_ms: float = 0.0


@dataclass
class BatchingConfig:
    """Configuration for batching."""
    batch_size: int = 32
    shuffle: bool = True
    drop_last: bool = False
    prefetch: int = 2


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class SampleDataset:
    """Base dataset class."""

    def __init__(self, samples: Optional[List[DataSample]] = None):
        self._data = samples or []

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, idx: int) -> DataSample:
        return self._data[idx]

    def append(self, sample: DataSample) -> None:
        """Add sample."""
        self._data.append(sample)

    def extend(self, samples: List[DataSample]) -> None:
        """Add multiple samples."""
        self._data.extend(samples)

    def get_all(self) -> List[DataSample]:
        """Get all samples."""
        return self._data.copy()

    def shuffle_data(self) -> None:
        """Shuffle samples in place."""
        random.shuffle(self._data)

    def partition(
        self,
        ratio: float = 0.8
    ) -> Tuple['SampleDataset', 'SampleDataset']:
        """Split dataset."""
        split_idx = int(len(self._data) * ratio)
        return (
            SampleDataset(self._data[:split_idx]),
            SampleDataset(self._data[split_idx:])
        )


# =============================================================================
# BATCH GENERATORS
# =============================================================================

class BaseBatchGen(ABC):
    """Abstract batch generator."""

    @abstractmethod
    def make_batches(self, dataset: SampleDataset) -> Iterator[DataBatch]:
        """Generate batches."""
        pass


class SequentialGen(BaseBatchGen):
    """Sequential batch generator."""

    def __init__(
        self,
        batch_size: int = 32,
        drop_last: bool = False
    ):
        self._batch_size = batch_size
        self._drop_last = drop_last

    def make_batches(self, dataset: SampleDataset) -> Iterator[DataBatch]:
        """Generate sequential batches."""
        samples = dataset.get_all()
        n = len(samples)

        for i in range(0, n, self._batch_size):
            batch_samples = samples[i:i + self._batch_size]

            if self._drop_last and len(batch_samples) < self._batch_size:
                break

            yield DataBatch(
                samples=batch_samples,
                batch_num=i // self._batch_size
            )


class RandomGen(BaseBatchGen):
    """Random shuffled batch generator."""

    def __init__(
        self,
        batch_size: int = 32,
        drop_last: bool = False,
        seed: Optional[int] = None
    ):
        self._batch_size = batch_size
        self._drop_last = drop_last
        self._seed = seed

    def make_batches(self, dataset: SampleDataset) -> Iterator[DataBatch]:
        """Generate randomized batches."""
        samples = dataset.get_all()

        if self._seed is not None:
            random.seed(self._seed)

        random.shuffle(samples)
        n = len(samples)

        for i in range(0, n, self._batch_size):
            batch_samples = samples[i:i + self._batch_size]

            if self._drop_last and len(batch_samples) < self._batch_size:
                break

            yield DataBatch(
                samples=batch_samples,
                batch_num=i // self._batch_size
            )


class StratifiedGen(BaseBatchGen):
    """Stratified batch generator for balanced classes."""

    def __init__(
        self,
        batch_size: int = 32,
        drop_last: bool = False
    ):
        self._batch_size = batch_size
        self._drop_last = drop_last

    def make_batches(self, dataset: SampleDataset) -> Iterator[DataBatch]:
        """Generate stratified batches."""
        samples = dataset.get_all()

        by_target: Dict[Any, List[DataSample]] = defaultdict(list)
        for sample in samples:
            by_target[sample.target].append(sample)

        for samples_list in by_target.values():
            random.shuffle(samples_list)

        target_iterators = {
            target: iter(samples_list)
            for target, samples_list in by_target.items()
        }

        targets = list(by_target.keys())
        samples_per_class = max(1, self._batch_size // len(targets))

        batch_num = 0
        while True:
            batch_samples = []

            for target in targets:
                for _ in range(samples_per_class):
                    try:
                        sample = next(target_iterators[target])
                        batch_samples.append(sample)
                    except StopIteration:
                        pass

            if not batch_samples:
                break

            if self._drop_last and len(batch_samples) < self._batch_size:
                break

            random.shuffle(batch_samples)

            yield DataBatch(
                samples=batch_samples,
                batch_num=batch_num
            )

            batch_num += 1


class BucketGen(BaseBatchGen):
    """Bucketed batch generator for variable length sequences."""

    def __init__(
        self,
        batch_size: int = 32,
        num_buckets: int = 5,
        length_fn: Optional[Callable[[DataSample], int]] = None
    ):
        self._batch_size = batch_size
        self._num_buckets = num_buckets
        self._length_fn = length_fn or (lambda s: len(s.features))

    def make_batches(self, dataset: SampleDataset) -> Iterator[DataBatch]:
        """Generate bucketed batches."""
        samples = dataset.get_all()

        samples_with_len = [
            (self._length_fn(s), s) for s in samples
        ]
        samples_with_len.sort(key=lambda x: x[0])

        bucket_size = max(1, len(samples) // self._num_buckets)
        buckets: List[List[DataSample]] = []

        for i in range(0, len(samples), bucket_size):
            bucket = [s for _, s in samples_with_len[i:i + bucket_size]]
            random.shuffle(bucket)
            buckets.append(bucket)

        batch_num = 0
        for bucket in buckets:
            for i in range(0, len(bucket), self._batch_size):
                batch_samples = bucket[i:i + self._batch_size]

                yield DataBatch(
                    samples=batch_samples,
                    batch_num=batch_num
                )
                batch_num += 1


class DynamicGen(BaseBatchGen):
    """Dynamic batch generator based on token/memory budget."""

    def __init__(
        self,
        max_tokens: int = 4096,
        token_fn: Optional[Callable[[DataSample], int]] = None
    ):
        self._max_tokens = max_tokens
        self._token_fn = token_fn or (lambda s: len(s.features))

    def make_batches(self, dataset: SampleDataset) -> Iterator[DataBatch]:
        """Generate dynamically sized batches."""
        samples = dataset.get_all()
        random.shuffle(samples)

        batch_samples: List[DataSample] = []
        current_tokens = 0
        batch_num = 0

        for sample in samples:
            sample_tokens = self._token_fn(sample)

            if current_tokens + sample_tokens > self._max_tokens and batch_samples:
                yield DataBatch(
                    samples=batch_samples,
                    batch_num=batch_num
                )
                batch_samples = []
                current_tokens = 0
                batch_num += 1

            batch_samples.append(sample)
            current_tokens += sample_tokens

        if batch_samples:
            yield DataBatch(
                samples=batch_samples,
                batch_num=batch_num
            )


# =============================================================================
# BATCH PROCESSORS
# =============================================================================

class BatchPadProcessor:
    """Pad batches to uniform length."""

    def __init__(
        self,
        mode: PadMode = PadMode.ZERO,
        pad_val: float = 0.0
    ):
        self._mode = mode
        self._pad_val = pad_val

    def process(self, batch: DataBatch, target_len: Optional[int] = None) -> DataBatch:
        """Pad batch to uniform length."""
        if not batch.samples:
            return batch

        max_len = target_len or max(
            len(s.features) for s in batch.samples
        )

        processed_samples = []

        for sample in batch.samples:
            features = sample.features
            current_len = len(features)

            if current_len >= max_len:
                if self._mode == PadMode.TRUNCATE:
                    features = features[:max_len]
                else:
                    features = features[:max_len]
            else:
                padding_needed = max_len - current_len

                if self._mode == PadMode.ZERO:
                    features = features + [self._pad_val] * padding_needed
                elif self._mode == PadMode.REPEAT:
                    while len(features) < max_len:
                        features = features + sample.features
                    features = features[:max_len]
                elif self._mode == PadMode.REFLECT:
                    reflected = list(reversed(sample.features))
                    while len(features) < max_len:
                        features = features + reflected
                    features = features[:max_len]

            processed_samples.append(DataSample(
                sample_id=sample.sample_id,
                features=features,
                target=sample.target,
                sample_weight=sample.sample_weight,
                meta=sample.meta
            ))

        return DataBatch(
            batch_id=batch.batch_id,
            samples=processed_samples,
            epoch_num=batch.epoch_num,
            batch_num=batch.batch_num
        )


class BatchCollateProcessor:
    """Collate batch samples into tensors."""

    def process(self, batch: DataBatch) -> Dict[str, List]:
        """Collate batch into dict of lists."""
        features = [s.features for s in batch.samples]
        targets = [s.target for s in batch.samples]
        weights = [s.sample_weight for s in batch.samples]

        return {
            'features': features,
            'targets': targets,
            'weights': weights
        }

    def process_flat(self, batch: DataBatch) -> Tuple[List[List[float]], List[Any]]:
        """Collate to feature and target lists."""
        features = [s.features for s in batch.samples]
        targets = [s.target for s in batch.samples]
        return features, targets


class BatchNormProcessor:
    """Normalize batch features."""

    def __init__(self):
        self._mean_cache: Optional[List[float]] = None
        self._var_cache: Optional[List[float]] = None
        self._momentum = 0.1
        self._eps = 1e-5

    def process(
        self,
        batch: DataBatch,
        is_training: bool = True
    ) -> DataBatch:
        """Normalize batch features."""
        if not batch.samples:
            return batch

        feat_len = len(batch.samples[0].features)

        if is_training:
            means = [0.0] * feat_len
            vars_ = [0.0] * feat_len
            n = len(batch.samples)

            for sample in batch.samples:
                for i, val in enumerate(sample.features):
                    means[i] += val / n

            for sample in batch.samples:
                for i, val in enumerate(sample.features):
                    vars_[i] += (val - means[i]) ** 2 / n

            if self._mean_cache is None:
                self._mean_cache = means.copy()
                self._var_cache = vars_.copy()
            else:
                for i in range(feat_len):
                    self._mean_cache[i] = (
                        (1 - self._momentum) * self._mean_cache[i] +
                        self._momentum * means[i]
                    )
                    self._var_cache[i] = (
                        (1 - self._momentum) * self._var_cache[i] +
                        self._momentum * vars_[i]
                    )
        else:
            means = self._mean_cache or [0.0] * feat_len
            vars_ = self._var_cache or [1.0] * feat_len

        normed_samples = []

        for sample in batch.samples:
            normed_features = []

            for i, val in enumerate(sample.features):
                std = math.sqrt(vars_[i] + self._eps)
                normed_val = (val - means[i]) / std
                normed_features.append(normed_val)

            normed_samples.append(DataSample(
                sample_id=sample.sample_id,
                features=normed_features,
                target=sample.target,
                sample_weight=sample.sample_weight,
                meta=sample.meta
            ))

        return DataBatch(
            batch_id=batch.batch_id,
            samples=normed_samples,
            epoch_num=batch.epoch_num,
            batch_num=batch.batch_num
        )


# =============================================================================
# DATA LOADER
# =============================================================================

class SampleDataLoader:
    """Data loader with batching."""

    def __init__(
        self,
        dataset: SampleDataset,
        batch_size: int = 32,
        shuffle: bool = True,
        drop_last: bool = False,
        strategy: BatchingStrategy = BatchingStrategy.RANDOM
    ):
        self._dataset = dataset
        self._batch_size = batch_size
        self._shuffle = shuffle
        self._drop_last = drop_last
        self._strategy = strategy
        self._generator = self._make_generator()

    def _make_generator(self) -> BaseBatchGen:
        """Create appropriate generator."""
        if self._strategy == BatchingStrategy.SEQUENTIAL:
            return SequentialGen(self._batch_size, self._drop_last)
        elif self._strategy == BatchingStrategy.RANDOM:
            return RandomGen(self._batch_size, self._drop_last)
        elif self._strategy == BatchingStrategy.STRATIFIED:
            return StratifiedGen(self._batch_size, self._drop_last)
        elif self._strategy == BatchingStrategy.BUCKETED:
            return BucketGen(self._batch_size)
        else:
            return RandomGen(self._batch_size, self._drop_last)

    def __len__(self) -> int:
        """Number of batches."""
        n = len(self._dataset)
        if self._drop_last:
            return n // self._batch_size
        return math.ceil(n / self._batch_size)

    def __iter__(self) -> Iterator[DataBatch]:
        """Iterate over batches."""
        return self._generator.make_batches(self._dataset)


# =============================================================================
# BATCH ORCHESTRATOR
# =============================================================================

class BatchOrchestrator:
    """
    Batch Orchestrator for BAEL.

    Comprehensive batch processing for AI training pipelines.
    """

    def __init__(self):
        self._datasets: Dict[str, SampleDataset] = {}
        self._loaders: Dict[str, SampleDataLoader] = {}
        self._padder = BatchPadProcessor()
        self._collator = BatchCollateProcessor()
        self._normalizer = BatchNormProcessor()
        self._stats: Dict[str, BatchingStats] = defaultdict(BatchingStats)
        self._history: deque = deque(maxlen=100)

    def make_dataset(
        self,
        name: str,
        samples: Optional[List[DataSample]] = None
    ) -> SampleDataset:
        """Create and store dataset."""
        dataset = SampleDataset(samples)
        self._datasets[name] = dataset
        return dataset

    def make_loader(
        self,
        name: str,
        dataset_name: str,
        batch_size: int = 32,
        shuffle: bool = True,
        drop_last: bool = False,
        strategy: BatchingStrategy = BatchingStrategy.RANDOM
    ) -> Optional[SampleDataLoader]:
        """Create data loader."""
        dataset = self._datasets.get(dataset_name)
        if not dataset:
            return None

        loader = SampleDataLoader(
            dataset=dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            drop_last=drop_last,
            strategy=strategy
        )

        self._loaders[name] = loader

        self._stats[name] = BatchingStats(
            total_samples=len(dataset),
            total_batches=len(loader)
        )

        return loader

    def batch_from_dataset(
        self,
        dataset: SampleDataset,
        batch_size: int = 32,
        strategy: BatchingStrategy = BatchingStrategy.RANDOM
    ) -> List[DataBatch]:
        """Generate all batches from dataset."""
        loader = SampleDataLoader(
            dataset=dataset,
            batch_size=batch_size,
            strategy=strategy
        )

        return list(loader)

    def pad(
        self,
        batch: DataBatch,
        mode: PadMode = PadMode.ZERO,
        target_len: Optional[int] = None
    ) -> DataBatch:
        """Pad batch to uniform length."""
        self._padder._mode = mode
        return self._padder.process(batch, target_len)

    def normalize(
        self,
        batch: DataBatch,
        is_training: bool = True
    ) -> DataBatch:
        """Normalize batch features."""
        return self._normalizer.process(batch, is_training)

    def collate(self, batch: DataBatch) -> Dict[str, List]:
        """Collate batch into dict."""
        return self._collator.process(batch)

    def mini_batches(
        self,
        samples: List[DataSample],
        batch_size: int = 32,
        shuffle: bool = True
    ) -> List[DataBatch]:
        """Create mini-batches from samples."""
        if shuffle:
            samples = samples.copy()
            random.shuffle(samples)

        batches = []

        for i in range(0, len(samples), batch_size):
            batch_samples = samples[i:i + batch_size]
            batches.append(DataBatch(
                samples=batch_samples,
                batch_num=i // batch_size
            ))

        return batches

    def accumulation_groups(
        self,
        batches: List[DataBatch],
        steps: int = 4
    ) -> List[List[DataBatch]]:
        """Group batches for gradient accumulation."""
        groups = []

        for i in range(0, len(batches), steps):
            group = batches[i:i + steps]
            groups.append(group)

        return groups

    def get_stats(self, loader_name: str) -> Optional[BatchingStats]:
        """Get loader statistics."""
        return self._stats.get(loader_name)

    def split(
        self,
        dataset_name: str,
        test_ratio: float = 0.2,
        shuffle: bool = True
    ) -> Tuple[Optional[SampleDataset], Optional[SampleDataset]]:
        """Split dataset into train and test."""
        dataset = self._datasets.get(dataset_name)
        if not dataset:
            return None, None

        if shuffle:
            dataset.shuffle_data()

        train_ds, test_ds = dataset.partition(1 - test_ratio)

        self._datasets[f"{dataset_name}_train"] = train_ds
        self._datasets[f"{dataset_name}_test"] = test_ds

        return train_ds, test_ds


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Batch Orchestrator."""
    print("=" * 70)
    print("BAEL - BATCH ORCHESTRATOR DEMO")
    print("Comprehensive Batch Processing for AI Training Pipelines")
    print("=" * 70)
    print()

    orch = BatchOrchestrator()

    samples = [
        DataSample(
            features=[random.gauss(0, 1) for _ in range(10)],
            target=i % 3,
            sample_weight=1.0
        )
        for i in range(100)
    ]

    dataset = orch.make_dataset("demo", samples)
    print(f"1. DATASET CREATED:")
    print(f"   Total samples: {len(dataset)}")
    print()

    # 2. Create Loader
    print("2. DATA LOADER:")
    print("-" * 40)

    loader = orch.make_loader(
        name="train_loader",
        dataset_name="demo",
        batch_size=16,
        shuffle=True,
        strategy=BatchingStrategy.RANDOM
    )

    if loader:
        print(f"   Batch size: 16")
        print(f"   Total batches: {len(loader)}")
    print()

    # 3. Generate Batches
    print("3. BATCH GENERATION:")
    print("-" * 40)

    batches = orch.batch_from_dataset(
        dataset,
        batch_size=16,
        strategy=BatchingStrategy.SEQUENTIAL
    )

    print(f"   Generated {len(batches)} batches")
    for i, batch in enumerate(batches[:3]):
        print(f"   Batch {i}: {batch.size} samples")
    print("   ...")
    print()

    # 4. Padding
    print("4. BATCH PADDING:")
    print("-" * 40)

    var_samples = [
        DataSample(features=[1.0] * (i + 5)) for i in range(5)
    ]
    var_dataset = SampleDataset(var_samples)
    var_batches = orch.batch_from_dataset(var_dataset, batch_size=5)

    original_lens = [len(s.features) for s in var_batches[0].samples]
    print(f"   Original lengths: {original_lens}")

    padded = orch.pad(var_batches[0], PadMode.ZERO)
    padded_lens = [len(s.features) for s in padded.samples]
    print(f"   Padded lengths: {padded_lens}")
    print()

    # 5. Normalization
    print("5. BATCH NORMALIZATION:")
    print("-" * 40)

    batch = batches[0]
    normalized = orch.normalize(batch, is_training=True)

    orig_mean = sum(batch.samples[0].features) / len(batch.samples[0].features)
    norm_mean = sum(normalized.samples[0].features) / len(normalized.samples[0].features)

    print(f"   Original sample mean: {orig_mean:.4f}")
    print(f"   Normalized sample mean: {norm_mean:.4f}")
    print()

    # 6. Collation
    print("6. BATCH COLLATION:")
    print("-" * 40)

    collated = orch.collate(batches[0])

    print(f"   Keys: {list(collated.keys())}")
    print(f"   Features shape: {len(collated['features'])} x {len(collated['features'][0])}")
    print(f"   Targets: {collated['targets'][:5]}...")
    print()

    # 7. Different Strategies
    print("7. BATCH STRATEGIES:")
    print("-" * 40)

    for strategy in [BatchingStrategy.SEQUENTIAL, BatchingStrategy.RANDOM, BatchingStrategy.STRATIFIED]:
        batches = orch.batch_from_dataset(
            dataset,
            batch_size=20,
            strategy=strategy
        )
        print(f"   {strategy.value}: {len(batches)} batches")
    print()

    # 8. Gradient Accumulation
    print("8. GRADIENT ACCUMULATION:")
    print("-" * 40)

    all_batches = orch.batch_from_dataset(dataset, batch_size=8)
    groups = orch.accumulation_groups(all_batches, steps=4)

    print(f"   Original batches: {len(all_batches)}")
    print(f"   Accumulation groups: {len(groups)}")
    print(f"   Batches per group: {len(groups[0]) if groups else 0}")
    print()

    # 9. Train/Test Split
    print("9. TRAIN/TEST SPLIT:")
    print("-" * 40)

    train_ds, test_ds = orch.split(
        "demo",
        test_ratio=0.2,
        shuffle=True
    )

    if train_ds and test_ds:
        print(f"   Train samples: {len(train_ds)}")
        print(f"   Test samples: {len(test_ds)}")
    print()

    # 10. Stats
    print("10. LOADER STATISTICS:")
    print("-" * 40)

    stats = orch.get_stats("train_loader")
    if stats:
        print(f"   Total samples: {stats.total_samples}")
        print(f"   Total batches: {stats.total_batches}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Batch Orchestrator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
