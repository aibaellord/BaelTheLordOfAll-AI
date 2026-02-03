#!/usr/bin/env python3
"""
BAEL - Data Loader Engine
Comprehensive data loading and batching for ML pipelines.

Features:
- Dataset abstraction
- Data loading
- Batching
- Shuffling
- Prefetching
- Multi-format support
"""

import asyncio
import json
import os
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DataFormat(Enum):
    """Supported data formats."""
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"
    TEXT = "text"
    BINARY = "binary"
    NUMPY = "numpy"
    PICKLE = "pickle"


class SplitType(Enum):
    """Dataset split types."""
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    ALL = "all"


class ShuffleMode(Enum):
    """Shuffle modes."""
    NONE = "none"
    ONCE = "once"
    EACH_EPOCH = "each_epoch"


class PaddingStrategy(Enum):
    """Padding strategies for batches."""
    NONE = "none"
    MAX_LENGTH = "max_length"
    FIXED = "fixed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class DataSample:
    """A single data sample."""
    data: Any = None
    label: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    index: int = 0


@dataclass
class DataBatch:
    """A batch of samples."""
    samples: List[DataSample] = field(default_factory=list)
    batch_size: int = 0
    batch_index: int = 0

    def __post_init__(self):
        if self.samples and not self.batch_size:
            self.batch_size = len(self.samples)

    @property
    def data(self) -> List[Any]:
        """Get batch data."""
        return [s.data for s in self.samples]

    @property
    def labels(self) -> List[Any]:
        """Get batch labels."""
        return [s.label for s in self.samples]

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self) -> Iterator[DataSample]:
        return iter(self.samples)


@dataclass
class DatasetStats:
    """Dataset statistics."""
    total_samples: int = 0
    n_batches: int = 0
    split_sizes: Dict[str, int] = field(default_factory=dict)
    label_distribution: Dict[Any, int] = field(default_factory=dict)


@dataclass
class LoaderConfig:
    """Data loader configuration."""
    batch_size: int = 32
    shuffle: ShuffleMode = ShuffleMode.EACH_EPOCH
    drop_last: bool = False
    prefetch: int = 2
    num_workers: int = 0
    seed: Optional[int] = None
    padding: PaddingStrategy = PaddingStrategy.NONE
    max_length: Optional[int] = None


# =============================================================================
# BASE DATASET
# =============================================================================

class BaseDataset(ABC):
    """Abstract base class for datasets."""

    def __init__(self):
        self._samples: List[DataSample] = []
        self._indices: List[int] = []

    @abstractmethod
    def load(self) -> None:
        """Load the dataset."""
        pass

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, index: int) -> DataSample:
        if index < 0 or index >= len(self._samples):
            raise IndexError(f"Index {index} out of range")
        return self._samples[index]

    def __iter__(self) -> Iterator[DataSample]:
        return iter(self._samples)

    def shuffle(self, seed: Optional[int] = None) -> None:
        """Shuffle the dataset."""
        if seed is not None:
            random.seed(seed)

        random.shuffle(self._samples)

        for i, sample in enumerate(self._samples):
            sample.index = i

    def split(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        shuffle: bool = True,
        seed: Optional[int] = None
    ) -> Tuple["InMemoryDataset", "InMemoryDataset", "InMemoryDataset"]:
        """Split into train/val/test sets."""
        if shuffle:
            if seed is not None:
                random.seed(seed)
            indices = list(range(len(self._samples)))
            random.shuffle(indices)
        else:
            indices = list(range(len(self._samples)))

        n = len(indices)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_indices = indices[:n_train]
        val_indices = indices[n_train:n_train + n_val]
        test_indices = indices[n_train + n_val:]

        train_samples = [self._samples[i] for i in train_indices]
        val_samples = [self._samples[i] for i in val_indices]
        test_samples = [self._samples[i] for i in test_indices]

        train_dataset = InMemoryDataset(train_samples)
        val_dataset = InMemoryDataset(val_samples)
        test_dataset = InMemoryDataset(test_samples)

        return train_dataset, val_dataset, test_dataset

    def get_stats(self) -> DatasetStats:
        """Get dataset statistics."""
        label_dist = {}

        for sample in self._samples:
            label = sample.label
            if label is not None:
                label_dist[label] = label_dist.get(label, 0) + 1

        return DatasetStats(
            total_samples=len(self._samples),
            label_distribution=label_dist
        )


# =============================================================================
# DATASET IMPLEMENTATIONS
# =============================================================================

class InMemoryDataset(BaseDataset):
    """Dataset stored entirely in memory."""

    def __init__(self, samples: Optional[List[DataSample]] = None):
        super().__init__()

        if samples:
            self._samples = samples
            for i, sample in enumerate(self._samples):
                sample.index = i

    def load(self) -> None:
        """Already loaded in memory."""
        pass

    def add_sample(self, data: Any, label: Optional[Any] = None, metadata: Optional[Dict] = None) -> None:
        """Add a sample."""
        sample = DataSample(
            data=data,
            label=label,
            metadata=metadata or {},
            index=len(self._samples)
        )
        self._samples.append(sample)

    def add_samples(self, data_list: List[Any], labels: Optional[List[Any]] = None) -> None:
        """Add multiple samples."""
        if labels is None:
            labels = [None] * len(data_list)

        for data, label in zip(data_list, labels):
            self.add_sample(data, label)


class TextFileDataset(BaseDataset):
    """Dataset from text files (one sample per line)."""

    def __init__(self, file_path: str, label: Optional[Any] = None):
        super().__init__()
        self._file_path = file_path
        self._default_label = label

    def load(self) -> None:
        """Load from text file."""
        if not os.path.exists(self._file_path):
            return

        with open(self._file_path, "r") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    self._samples.append(DataSample(
                        data=line,
                        label=self._default_label,
                        index=i
                    ))


class JSONLDataset(BaseDataset):
    """Dataset from JSONL files."""

    def __init__(
        self,
        file_path: str,
        data_field: str = "text",
        label_field: Optional[str] = "label"
    ):
        super().__init__()
        self._file_path = file_path
        self._data_field = data_field
        self._label_field = label_field

    def load(self) -> None:
        """Load from JSONL file."""
        if not os.path.exists(self._file_path):
            return

        with open(self._file_path, "r") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                    data = obj.get(self._data_field)
                    label = obj.get(self._label_field) if self._label_field else None

                    self._samples.append(DataSample(
                        data=data,
                        label=label,
                        metadata=obj,
                        index=i
                    ))
                except json.JSONDecodeError:
                    continue


class GeneratorDataset(BaseDataset):
    """Dataset from a generator function."""

    def __init__(self, generator_fn: Callable[[], Iterator[Tuple[Any, Any]]]):
        super().__init__()
        self._generator_fn = generator_fn

    def load(self) -> None:
        """Load from generator."""
        for i, (data, label) in enumerate(self._generator_fn()):
            self._samples.append(DataSample(
                data=data,
                label=label,
                index=i
            ))


class MappedDataset(BaseDataset):
    """Dataset with a transform applied to each sample."""

    def __init__(
        self,
        base_dataset: BaseDataset,
        transform: Callable[[DataSample], DataSample]
    ):
        super().__init__()
        self._base = base_dataset
        self._transform = transform

    def load(self) -> None:
        """Apply transform to base dataset."""
        for sample in self._base:
            transformed = self._transform(sample)
            transformed.index = len(self._samples)
            self._samples.append(transformed)


class ConcatDataset(BaseDataset):
    """Concatenation of multiple datasets."""

    def __init__(self, datasets: List[BaseDataset]):
        super().__init__()
        self._datasets = datasets

    def load(self) -> None:
        """Concatenate all datasets."""
        index = 0

        for dataset in self._datasets:
            for sample in dataset:
                new_sample = DataSample(
                    data=sample.data,
                    label=sample.label,
                    metadata=sample.metadata.copy(),
                    index=index
                )
                self._samples.append(new_sample)
                index += 1


# =============================================================================
# DATA LOADER
# =============================================================================

class DataLoader:
    """
    Data loader for batching and iterating over datasets.
    """

    def __init__(
        self,
        dataset: BaseDataset,
        config: Optional[LoaderConfig] = None
    ):
        self._dataset = dataset
        self._config = config or LoaderConfig()
        self._indices: List[int] = []
        self._epoch = 0
        self._batch_index = 0

        if self._config.seed is not None:
            random.seed(self._config.seed)

        self._reset_indices()

    def _reset_indices(self) -> None:
        """Reset indices for new epoch."""
        self._indices = list(range(len(self._dataset)))

        if self._config.shuffle in (ShuffleMode.ONCE, ShuffleMode.EACH_EPOCH):
            random.shuffle(self._indices)

        self._batch_index = 0

    def __len__(self) -> int:
        """Number of batches."""
        n = len(self._dataset)
        bs = self._config.batch_size

        if self._config.drop_last:
            return n // bs
        else:
            return (n + bs - 1) // bs

    def __iter__(self) -> Iterator[DataBatch]:
        """Iterate over batches."""
        if self._config.shuffle == ShuffleMode.EACH_EPOCH and self._epoch > 0:
            self._reset_indices()

        bs = self._config.batch_size
        n = len(self._indices)

        for start in range(0, n, bs):
            end = min(start + bs, n)

            if self._config.drop_last and (end - start) < bs:
                break

            batch_indices = self._indices[start:end]
            samples = [self._dataset[i] for i in batch_indices]

            yield DataBatch(
                samples=samples,
                batch_size=len(samples),
                batch_index=self._batch_index
            )

            self._batch_index += 1

        self._epoch += 1

    def get_batch(self, batch_index: int) -> DataBatch:
        """Get a specific batch by index."""
        bs = self._config.batch_size
        start = batch_index * bs
        end = min(start + bs, len(self._indices))

        batch_indices = self._indices[start:end]
        samples = [self._dataset[i] for i in batch_indices]

        return DataBatch(
            samples=samples,
            batch_size=len(samples),
            batch_index=batch_index
        )

    def reset(self) -> None:
        """Reset the loader."""
        self._epoch = 0
        self._reset_indices()


# =============================================================================
# DATA LOADER ENGINE
# =============================================================================

class DataLoaderEngine:
    """
    Data Loader Engine for BAEL.

    Comprehensive data loading and batching.
    """

    def __init__(self):
        self._datasets: Dict[str, BaseDataset] = {}
        self._loaders: Dict[str, DataLoader] = {}

    def create_dataset(
        self,
        name: str,
        data: Optional[List[Any]] = None,
        labels: Optional[List[Any]] = None
    ) -> InMemoryDataset:
        """Create an in-memory dataset."""
        dataset = InMemoryDataset()

        if data:
            dataset.add_samples(data, labels)

        self._datasets[name] = dataset
        return dataset

    def load_text_dataset(
        self,
        name: str,
        file_path: str,
        label: Optional[Any] = None
    ) -> TextFileDataset:
        """Load a text file dataset."""
        dataset = TextFileDataset(file_path, label)
        dataset.load()
        self._datasets[name] = dataset
        return dataset

    def load_jsonl_dataset(
        self,
        name: str,
        file_path: str,
        data_field: str = "text",
        label_field: Optional[str] = "label"
    ) -> JSONLDataset:
        """Load a JSONL dataset."""
        dataset = JSONLDataset(file_path, data_field, label_field)
        dataset.load()
        self._datasets[name] = dataset
        return dataset

    def create_loader(
        self,
        name: str,
        dataset: BaseDataset,
        batch_size: int = 32,
        shuffle: ShuffleMode = ShuffleMode.EACH_EPOCH,
        drop_last: bool = False,
        seed: Optional[int] = None
    ) -> DataLoader:
        """Create a data loader."""
        config = LoaderConfig(
            batch_size=batch_size,
            shuffle=shuffle,
            drop_last=drop_last,
            seed=seed
        )

        loader = DataLoader(dataset, config)
        self._loaders[name] = loader
        return loader

    def get_dataset(self, name: str) -> Optional[BaseDataset]:
        """Get a dataset by name."""
        return self._datasets.get(name)

    def get_loader(self, name: str) -> Optional[DataLoader]:
        """Get a loader by name."""
        return self._loaders.get(name)

    def split_dataset(
        self,
        name: str,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        shuffle: bool = True,
        seed: Optional[int] = None
    ) -> Tuple[InMemoryDataset, InMemoryDataset, InMemoryDataset]:
        """Split a dataset into train/val/test."""
        dataset = self._datasets.get(name)

        if not dataset:
            raise ValueError(f"Dataset not found: {name}")

        train_ds, val_ds, test_ds = dataset.split(
            train_ratio, val_ratio, test_ratio, shuffle, seed
        )

        self._datasets[f"{name}_train"] = train_ds
        self._datasets[f"{name}_val"] = val_ds
        self._datasets[f"{name}_test"] = test_ds

        return train_ds, val_ds, test_ds

    def concat_datasets(
        self,
        name: str,
        dataset_names: List[str]
    ) -> ConcatDataset:
        """Concatenate multiple datasets."""
        datasets = []

        for ds_name in dataset_names:
            ds = self._datasets.get(ds_name)
            if ds:
                datasets.append(ds)

        concat_ds = ConcatDataset(datasets)
        concat_ds.load()

        self._datasets[name] = concat_ds
        return concat_ds

    def map_dataset(
        self,
        name: str,
        source_name: str,
        transform: Callable[[DataSample], DataSample]
    ) -> MappedDataset:
        """Create a mapped dataset."""
        source = self._datasets.get(source_name)

        if not source:
            raise ValueError(f"Dataset not found: {source_name}")

        mapped = MappedDataset(source, transform)
        mapped.load()

        self._datasets[name] = mapped
        return mapped

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "n_datasets": len(self._datasets),
            "n_loaders": len(self._loaders),
            "datasets": {
                name: {
                    "size": len(ds),
                    "type": type(ds).__name__
                }
                for name, ds in self._datasets.items()
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Data Loader Engine."""
    print("=" * 70)
    print("BAEL - DATA LOADER ENGINE DEMO")
    print("Data Loading and Batching for ML Pipelines")
    print("=" * 70)
    print()

    engine = DataLoaderEngine()

    # 1. Create In-Memory Dataset
    print("1. CREATE IN-MEMORY DATASET:")
    print("-" * 40)

    texts = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is transforming industries",
        "Neural networks learn from data patterns",
        "Deep learning achieves remarkable results",
        "AI agents can perform complex tasks",
        "Natural language processing enables understanding",
        "Computer vision recognizes images accurately",
        "Reinforcement learning optimizes decisions",
        "Transfer learning leverages prior knowledge",
        "Generative models create new content"
    ]

    labels = [0, 1, 1, 1, 1, 1, 1, 1, 1, 1]

    dataset = engine.create_dataset("text_data", texts, labels)

    print(f"   Dataset size: {len(dataset)}")
    print(f"   Sample: {dataset[0].data[:50]}...")
    print()

    # 2. Dataset Statistics
    print("2. DATASET STATISTICS:")
    print("-" * 40)

    stats = dataset.get_stats()

    print(f"   Total samples: {stats.total_samples}")
    print(f"   Label distribution: {stats.label_distribution}")
    print()

    # 3. Split Dataset
    print("3. SPLIT DATASET:")
    print("-" * 40)

    train_ds, val_ds, test_ds = engine.split_dataset(
        "text_data",
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42
    )

    print(f"   Train size: {len(train_ds)}")
    print(f"   Val size: {len(val_ds)}")
    print(f"   Test size: {len(test_ds)}")
    print()

    # 4. Create Data Loader
    print("4. CREATE DATA LOADER:")
    print("-" * 40)

    loader = engine.create_loader(
        "train_loader",
        train_ds,
        batch_size=3,
        shuffle=ShuffleMode.EACH_EPOCH,
        seed=42
    )

    print(f"   Batch size: 3")
    print(f"   Number of batches: {len(loader)}")
    print()

    # 5. Iterate Batches
    print("5. ITERATE BATCHES:")
    print("-" * 40)

    for i, batch in enumerate(loader):
        print(f"   Batch {i+1}: {batch.batch_size} samples")
        print(f"      Labels: {batch.labels}")
    print()

    # 6. Shuffle Each Epoch
    print("6. SHUFFLE EACH EPOCH:")
    print("-" * 40)

    print("   Epoch 1 order:")
    epoch1_labels = []
    for batch in loader:
        epoch1_labels.extend(batch.labels)
    print(f"      Labels: {epoch1_labels}")

    print("   Epoch 2 order (reshuffled):")
    epoch2_labels = []
    for batch in loader:
        epoch2_labels.extend(batch.labels)
    print(f"      Labels: {epoch2_labels}")
    print()

    # 7. Map Transform
    print("7. MAP TRANSFORM:")
    print("-" * 40)

    def uppercase_transform(sample: DataSample) -> DataSample:
        return DataSample(
            data=sample.data.upper(),
            label=sample.label,
            metadata=sample.metadata
        )

    mapped_ds = engine.map_dataset(
        "uppercase_data",
        "text_data",
        uppercase_transform
    )

    print(f"   Original: {dataset[0].data[:30]}...")
    print(f"   Mapped: {mapped_ds[0].data[:30]}...")
    print()

    # 8. Generator Dataset
    print("8. GENERATOR DATASET:")
    print("-" * 40)

    def number_generator():
        for i in range(5):
            yield i * 10, i % 2

    gen_dataset = GeneratorDataset(number_generator)
    gen_dataset.load()

    print(f"   Size: {len(gen_dataset)}")
    for sample in gen_dataset:
        print(f"      Data: {sample.data}, Label: {sample.label}")
    print()

    # 9. Concat Datasets
    print("9. CONCAT DATASETS:")
    print("-" * 40)

    concat_ds = engine.concat_datasets(
        "combined",
        ["text_data_train", "text_data_val"]
    )

    print(f"   Train size: {len(train_ds)}")
    print(f"   Val size: {len(val_ds)}")
    print(f"   Combined size: {len(concat_ds)}")
    print()

    # 10. Engine Summary
    print("10. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Datasets: {summary['n_datasets']}")
    print(f"   Loaders: {summary['n_loaders']}")
    for name, info in list(summary['datasets'].items())[:5]:
        print(f"      {name}: {info['size']} samples ({info['type']})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Data Loader Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
