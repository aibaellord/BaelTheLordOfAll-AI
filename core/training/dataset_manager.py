"""
BAEL Dataset Manager
=====================

Dataset management and preprocessing pipeline.
Handles data loading, splitting, and augmentation.

Features:
- Multiple data formats
- Train/val/test splitting
- Data augmentation
- Streaming support
- Caching
"""

import hashlib
import json
import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generator, Iterator, List, Optional,
                    Tuple, Union)

logger = logging.getLogger(__name__)


class DataSplit(Enum):
    """Data split types."""
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


@dataclass
class DataSample:
    """A single data sample."""
    id: str
    input_text: str
    target_text: str = ""

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    split: DataSplit = DataSplit.TRAIN

    # Tokenized
    input_ids: Optional[List[int]] = None
    attention_mask: Optional[List[int]] = None
    labels: Optional[List[int]] = None


@dataclass
class Dataset:
    """A dataset container."""
    name: str

    # Samples
    samples: List[DataSample] = field(default_factory=list)

    # Splits
    train_indices: List[int] = field(default_factory=list)
    val_indices: List[int] = field(default_factory=list)
    test_indices: List[int] = field(default_factory=list)

    # Metadata
    description: str = ""
    source: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    # Stats
    total_tokens: int = 0
    avg_length: float = 0.0

    def __len__(self) -> int:
        return len(self.samples)

    def get_split(self, split: DataSplit) -> List[DataSample]:
        """Get samples for a split."""
        if split == DataSplit.TRAIN:
            return [self.samples[i] for i in self.train_indices]
        elif split == DataSplit.VALIDATION:
            return [self.samples[i] for i in self.val_indices]
        else:
            return [self.samples[i] for i in self.test_indices]


class DataLoader:
    """
    Data loader for batched iteration.
    """

    def __init__(
        self,
        dataset: Dataset,
        split: DataSplit = DataSplit.TRAIN,
        batch_size: int = 32,
        shuffle: bool = True,
        drop_last: bool = False,
    ):
        self.dataset = dataset
        self.split = split
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.drop_last = drop_last

        self._indices = self._get_indices()

    def _get_indices(self) -> List[int]:
        """Get indices for the split."""
        if self.split == DataSplit.TRAIN:
            return list(self.dataset.train_indices)
        elif self.split == DataSplit.VALIDATION:
            return list(self.dataset.val_indices)
        else:
            return list(self.dataset.test_indices)

    def __len__(self) -> int:
        n = len(self._indices)
        if self.drop_last:
            return n // self.batch_size
        return (n + self.batch_size - 1) // self.batch_size

    def __iter__(self) -> Iterator[List[DataSample]]:
        indices = list(self._indices)

        if self.shuffle:
            random.shuffle(indices)

        for i in range(0, len(indices), self.batch_size):
            batch_indices = indices[i:i + self.batch_size]

            if self.drop_last and len(batch_indices) < self.batch_size:
                break

            batch = [self.dataset.samples[idx] for idx in batch_indices]
            yield batch


class Preprocessor:
    """
    Data preprocessor for text transformation.
    """

    def __init__(
        self,
        tokenizer: Optional[Any] = None,
        max_length: int = 512,
        padding: str = "max_length",
        truncation: bool = True,
    ):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.padding = padding
        self.truncation = truncation

        # Transformations
        self._transforms: List[Callable[[str], str]] = []

    def add_transform(self, transform: Callable[[str], str]) -> None:
        """Add a text transformation."""
        self._transforms.append(transform)

    def preprocess(self, text: str) -> str:
        """Apply all transformations."""
        for transform in self._transforms:
            text = transform(text)
        return text

    def tokenize(self, sample: DataSample) -> DataSample:
        """Tokenize a sample."""
        if not self.tokenizer:
            # Simple whitespace tokenization fallback
            tokens = sample.input_text.split()
            sample.input_ids = list(range(len(tokens)))  # Placeholder
            sample.attention_mask = [1] * len(tokens)
            return sample

        # Use tokenizer
        encoded = self.tokenizer(
            sample.input_text,
            max_length=self.max_length,
            padding=self.padding,
            truncation=self.truncation,
            return_tensors=None,
        )

        sample.input_ids = encoded["input_ids"]
        sample.attention_mask = encoded["attention_mask"]

        if sample.target_text:
            labels = self.tokenizer(
                sample.target_text,
                max_length=self.max_length,
                padding=self.padding,
                truncation=self.truncation,
                return_tensors=None,
            )
            sample.labels = labels["input_ids"]

        return sample

    def batch_tokenize(
        self,
        samples: List[DataSample],
    ) -> List[DataSample]:
        """Tokenize a batch of samples."""
        return [self.tokenize(s) for s in samples]


class DatasetManager:
    """
    Dataset manager for BAEL training.

    Handles dataset operations.
    """

    def __init__(
        self,
        cache_dir: str = "./data_cache",
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Loaded datasets
        self._datasets: Dict[str, Dataset] = {}

        # Stats
        self.stats = {
            "datasets_loaded": 0,
            "total_samples": 0,
        }

    def create_dataset(
        self,
        name: str,
        samples: List[Dict[str, Any]],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        shuffle: bool = True,
    ) -> Dataset:
        """
        Create a dataset from samples.

        Args:
            name: Dataset name
            samples: List of sample dicts with 'input' and 'target' keys
            train_ratio: Training split ratio
            val_ratio: Validation split ratio
            shuffle: Shuffle before splitting

        Returns:
            Created dataset
        """
        dataset = Dataset(name=name)

        # Convert to DataSample objects
        for i, sample in enumerate(samples):
            sample_id = hashlib.md5(
                f"{name}:{i}:{sample.get('input', '')[:50]}".encode()
            ).hexdigest()[:12]

            data_sample = DataSample(
                id=sample_id,
                input_text=sample.get("input", ""),
                target_text=sample.get("target", ""),
                metadata=sample.get("metadata", {}),
            )
            dataset.samples.append(data_sample)

        # Create splits
        indices = list(range(len(dataset.samples)))
        if shuffle:
            random.shuffle(indices)

        train_end = int(len(indices) * train_ratio)
        val_end = train_end + int(len(indices) * val_ratio)

        dataset.train_indices = indices[:train_end]
        dataset.val_indices = indices[train_end:val_end]
        dataset.test_indices = indices[val_end:]

        # Update sample splits
        for idx in dataset.train_indices:
            dataset.samples[idx].split = DataSplit.TRAIN
        for idx in dataset.val_indices:
            dataset.samples[idx].split = DataSplit.VALIDATION
        for idx in dataset.test_indices:
            dataset.samples[idx].split = DataSplit.TEST

        # Calculate stats
        total_len = sum(len(s.input_text) for s in dataset.samples)
        dataset.avg_length = total_len / max(len(dataset.samples), 1)

        self._datasets[name] = dataset
        self.stats["datasets_loaded"] += 1
        self.stats["total_samples"] += len(dataset.samples)

        return dataset

    def load_jsonl(
        self,
        path: str,
        name: Optional[str] = None,
        input_key: str = "input",
        target_key: str = "target",
        **kwargs,
    ) -> Dataset:
        """
        Load dataset from JSONL file.

        Args:
            path: Path to JSONL file
            name: Dataset name (defaults to filename)
            input_key: Key for input text
            target_key: Key for target text

        Returns:
            Loaded dataset
        """
        path = Path(path)
        name = name or path.stem

        samples = []
        with open(path, 'r') as f:
            for line in f:
                data = json.loads(line)
                samples.append({
                    "input": data.get(input_key, ""),
                    "target": data.get(target_key, ""),
                    "metadata": {k: v for k, v in data.items()
                               if k not in [input_key, target_key]},
                })

        dataset = self.create_dataset(name, samples, **kwargs)
        dataset.source = str(path)

        return dataset

    def load_instruction_dataset(
        self,
        path: str,
        name: Optional[str] = None,
        instruction_key: str = "instruction",
        input_key: str = "input",
        output_key: str = "output",
        **kwargs,
    ) -> Dataset:
        """
        Load instruction-following dataset (Alpaca-style).

        Args:
            path: Path to JSON/JSONL file
            name: Dataset name
            instruction_key: Key for instruction
            input_key: Key for input
            output_key: Key for output

        Returns:
            Loaded dataset
        """
        path = Path(path)
        name = name or path.stem

        # Load data
        if path.suffix == '.jsonl':
            data = []
            with open(path, 'r') as f:
                for line in f:
                    data.append(json.loads(line))
        else:
            with open(path, 'r') as f:
                data = json.load(f)

        # Convert to samples
        samples = []
        for item in data:
            instruction = item.get(instruction_key, "")
            input_text = item.get(input_key, "")
            output = item.get(output_key, "")

            # Format as prompt
            if input_text:
                full_input = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n"
            else:
                full_input = f"### Instruction:\n{instruction}\n\n### Response:\n"

            samples.append({
                "input": full_input,
                "target": output,
            })

        return self.create_dataset(name, samples, **kwargs)

    def generate_synthetic(
        self,
        name: str,
        generator: Callable[[], Tuple[str, str]],
        count: int = 1000,
        **kwargs,
    ) -> Dataset:
        """
        Generate synthetic dataset.

        Args:
            name: Dataset name
            generator: Function that returns (input, target) pairs
            count: Number of samples to generate

        Returns:
            Generated dataset
        """
        samples = []
        for _ in range(count):
            input_text, target_text = generator()
            samples.append({
                "input": input_text,
                "target": target_text,
            })

        return self.create_dataset(name, samples, **kwargs)

    def augment(
        self,
        dataset: Dataset,
        augmentor: Callable[[str], List[str]],
        target_augmentor: Optional[Callable[[str], List[str]]] = None,
    ) -> Dataset:
        """
        Augment dataset with additional samples.

        Args:
            dataset: Dataset to augment
            augmentor: Function to augment input text
            target_augmentor: Optional function to augment target

        Returns:
            Augmented dataset
        """
        new_samples = []

        for sample in dataset.samples:
            augmented_inputs = augmentor(sample.input_text)

            for aug_input in augmented_inputs:
                if target_augmentor:
                    augmented_targets = target_augmentor(sample.target_text)
                    for aug_target in augmented_targets:
                        new_samples.append({
                            "input": aug_input,
                            "target": aug_target,
                        })
                else:
                    new_samples.append({
                        "input": aug_input,
                        "target": sample.target_text,
                    })

        # Add to dataset
        return self.create_dataset(
            f"{dataset.name}_augmented",
            [{"input": s.input_text, "target": s.target_text} for s in dataset.samples] + new_samples,
        )

    def get_dataset(self, name: str) -> Optional[Dataset]:
        """Get a loaded dataset."""
        return self._datasets.get(name)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "datasets": list(self._datasets.keys()),
        }


def demo():
    """Demonstrate dataset manager."""
    print("=" * 60)
    print("BAEL Dataset Manager Demo")
    print("=" * 60)

    manager = DatasetManager()

    # Create sample data
    samples = [
        {"input": "Translate to French: Hello", "target": "Bonjour"},
        {"input": "Translate to French: Goodbye", "target": "Au revoir"},
        {"input": "Translate to French: Thank you", "target": "Merci"},
        {"input": "Translate to French: Please", "target": "S'il vous plaît"},
        {"input": "Translate to French: Yes", "target": "Oui"},
        {"input": "Translate to French: No", "target": "Non"},
        {"input": "Translate to French: Good morning", "target": "Bonjour"},
        {"input": "Translate to French: Good night", "target": "Bonne nuit"},
        {"input": "Translate to French: I love you", "target": "Je t'aime"},
        {"input": "Translate to French: How are you?", "target": "Comment allez-vous?"},
    ]

    print("\nCreating dataset...")
    dataset = manager.create_dataset(
        "translation",
        samples,
        train_ratio=0.7,
        val_ratio=0.2,
    )

    print(f"  Name: {dataset.name}")
    print(f"  Total samples: {len(dataset)}")
    print(f"  Train: {len(dataset.train_indices)}")
    print(f"  Val: {len(dataset.val_indices)}")
    print(f"  Test: {len(dataset.test_indices)}")
    print(f"  Avg length: {dataset.avg_length:.1f}")

    # Data loader
    print("\nData loader:")
    loader = DataLoader(dataset, batch_size=3, shuffle=False)
    print(f"  Batches: {len(loader)}")

    for i, batch in enumerate(loader):
        print(f"  Batch {i+1}: {len(batch)} samples")
        if i >= 1:
            break

    # Preprocessor
    print("\nPreprocessor:")
    preprocessor = Preprocessor(max_length=128)
    preprocessor.add_transform(str.lower)

    sample = dataset.samples[0]
    processed = preprocessor.preprocess(sample.input_text)
    print(f"  Original: {sample.input_text}")
    print(f"  Processed: {processed}")

    # Synthetic generation
    print("\nSynthetic generation:")

    def math_generator():
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        return f"What is {a} + {b}?", str(a + b)

    math_dataset = manager.generate_synthetic(
        "math",
        math_generator,
        count=5,
    )

    for sample in math_dataset.samples[:3]:
        print(f"  Q: {sample.input_text} A: {sample.target_text}")

    print(f"\nStats: {manager.get_stats()}")


if __name__ == "__main__":
    demo()
