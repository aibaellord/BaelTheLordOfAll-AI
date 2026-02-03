#!/usr/bin/env python3
"""
BAEL - Vocabulary Manager
Comprehensive vocabulary management for NLP.

Features:
- Vocabulary building
- Tokenization support
- Special tokens handling
- Subword vocabularies
- Serialization
"""

import asyncio
import json
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import Counter
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

class VocabType(Enum):
    """Vocabulary types."""
    WORD = "word"
    CHARACTER = "character"
    SUBWORD = "subword"
    BPE = "bpe"
    WORDPIECE = "wordpiece"
    UNIGRAM = "unigram"


class SpecialToken(Enum):
    """Special tokens."""
    PAD = "[PAD]"
    UNK = "[UNK]"
    CLS = "[CLS]"
    SEP = "[SEP]"
    MASK = "[MASK]"
    BOS = "[BOS]"
    EOS = "[EOS]"


class NormalizationType(Enum):
    """Text normalization types."""
    NONE = "none"
    LOWERCASE = "lowercase"
    UNICODE = "unicode"
    STRIP_ACCENTS = "strip_accents"


class TokenizerType(Enum):
    """Tokenizer types."""
    WHITESPACE = "whitespace"
    WORD_PUNCT = "word_punct"
    CHARACTER = "character"
    REGEX = "regex"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class VocabConfig:
    """Vocabulary configuration."""
    vocab_type: VocabType = VocabType.WORD
    min_frequency: int = 1
    max_vocab_size: Optional[int] = None
    lowercase: bool = True
    strip_accents: bool = False
    special_tokens: List[str] = field(default_factory=list)
    unk_token: str = "[UNK]"
    pad_token: str = "[PAD]"


@dataclass
class VocabEntry:
    """Vocabulary entry."""
    token: str
    index: int
    frequency: int = 0
    is_special: bool = False

    def __hash__(self):
        return hash(self.token)


@dataclass
class VocabStats:
    """Vocabulary statistics."""
    total_tokens: int = 0
    unique_tokens: int = 0
    special_tokens: int = 0
    avg_token_length: float = 0.0
    min_frequency: int = 0
    max_frequency: int = 0
    coverage: float = 0.0


@dataclass
class TokenizedText:
    """Tokenized text result."""
    tokens: List[str] = field(default_factory=list)
    token_ids: List[int] = field(default_factory=list)
    attention_mask: List[int] = field(default_factory=list)
    special_tokens_mask: List[int] = field(default_factory=list)
    original_text: str = ""

    def __len__(self) -> int:
        return len(self.tokens)


@dataclass
class BPEMerge:
    """BPE merge operation."""
    pair: Tuple[str, str]
    new_token: str
    frequency: int = 0
    priority: int = 0


# =============================================================================
# TOKENIZERS
# =============================================================================

class BaseTokenizer(ABC):
    """Abstract base tokenizer."""

    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into tokens."""
        pass

    def normalize(
        self,
        text: str,
        lowercase: bool = True,
        strip_accents: bool = False
    ) -> str:
        """Normalize text."""
        if lowercase:
            text = text.lower()

        if strip_accents:
            import unicodedata
            text = unicodedata.normalize("NFD", text)
            text = "".join(
                c for c in text
                if unicodedata.category(c) != "Mn"
            )

        return text


class WhitespaceTokenizer(BaseTokenizer):
    """Whitespace tokenizer."""

    def tokenize(self, text: str) -> List[str]:
        return text.split()


class WordPunctTokenizer(BaseTokenizer):
    """Word and punctuation tokenizer."""

    def __init__(self):
        self._pattern = re.compile(r"\w+|[^\w\s]")

    def tokenize(self, text: str) -> List[str]:
        return self._pattern.findall(text)


class CharacterTokenizer(BaseTokenizer):
    """Character-level tokenizer."""

    def tokenize(self, text: str) -> List[str]:
        return list(text)


class RegexTokenizer(BaseTokenizer):
    """Regex-based tokenizer."""

    def __init__(self, pattern: str = r"\w+"):
        self._pattern = re.compile(pattern)

    def tokenize(self, text: str) -> List[str]:
        return self._pattern.findall(text)


# =============================================================================
# VOCABULARY
# =============================================================================

class Vocabulary:
    """
    Vocabulary for NLP.

    Maps between tokens and indices.
    """

    def __init__(self, config: Optional[VocabConfig] = None):
        self._config = config or VocabConfig()
        self._token_to_idx: Dict[str, int] = {}
        self._idx_to_token: Dict[int, str] = {}
        self._token_freqs: Dict[str, int] = {}
        self._special_tokens: Set[str] = set()
        self._next_idx = 0

        self._add_special_tokens()

    def _add_special_tokens(self) -> None:
        """Add special tokens."""
        default_special = [
            self._config.pad_token,
            self._config.unk_token
        ]

        for token in default_special + self._config.special_tokens:
            if token and token not in self._token_to_idx:
                self._add_token(token, is_special=True)

    def _add_token(
        self,
        token: str,
        frequency: int = 0,
        is_special: bool = False
    ) -> int:
        """Add a token to vocabulary."""
        if token in self._token_to_idx:
            if frequency > 0:
                self._token_freqs[token] = self._token_freqs.get(token, 0) + frequency
            return self._token_to_idx[token]

        idx = self._next_idx
        self._token_to_idx[token] = idx
        self._idx_to_token[idx] = token
        self._token_freqs[token] = frequency
        self._next_idx += 1

        if is_special:
            self._special_tokens.add(token)

        return idx

    def add_tokens(
        self,
        tokens: List[str],
        frequencies: Optional[Dict[str, int]] = None
    ) -> int:
        """Add multiple tokens."""
        added = 0

        for token in tokens:
            if token not in self._token_to_idx:
                freq = frequencies.get(token, 0) if frequencies else 0
                self._add_token(token, freq)
                added += 1

        return added

    def build_from_texts(
        self,
        texts: List[str],
        tokenizer: Optional[BaseTokenizer] = None
    ) -> "Vocabulary":
        """Build vocabulary from texts."""
        if tokenizer is None:
            tokenizer = WhitespaceTokenizer()

        counter = Counter()

        for text in texts:
            if self._config.lowercase:
                text = text.lower()

            tokens = tokenizer.tokenize(text)
            counter.update(tokens)

        filtered = [
            (token, freq) for token, freq in counter.items()
            if freq >= self._config.min_frequency
        ]

        filtered.sort(key=lambda x: (-x[1], x[0]))

        if self._config.max_vocab_size:
            max_size = self._config.max_vocab_size - len(self._special_tokens)
            filtered = filtered[:max_size]

        for token, freq in filtered:
            self._add_token(token, freq)

        return self

    def token_to_id(self, token: str) -> int:
        """Convert token to ID."""
        return self._token_to_idx.get(
            token,
            self._token_to_idx.get(self._config.unk_token, 0)
        )

    def id_to_token(self, idx: int) -> str:
        """Convert ID to token."""
        return self._idx_to_token.get(idx, self._config.unk_token)

    def tokens_to_ids(self, tokens: List[str]) -> List[int]:
        """Convert tokens to IDs."""
        return [self.token_to_id(t) for t in tokens]

    def ids_to_tokens(self, ids: List[int]) -> List[str]:
        """Convert IDs to tokens."""
        return [self.id_to_token(i) for i in ids]

    def __contains__(self, token: str) -> bool:
        return token in self._token_to_idx

    def __len__(self) -> int:
        return len(self._token_to_idx)

    def __getitem__(self, token: str) -> int:
        return self.token_to_id(token)

    @property
    def unk_token_id(self) -> int:
        return self._token_to_idx.get(self._config.unk_token, 0)

    @property
    def pad_token_id(self) -> int:
        return self._token_to_idx.get(self._config.pad_token, 0)

    @property
    def special_tokens(self) -> Set[str]:
        return self._special_tokens.copy()

    def get_frequency(self, token: str) -> int:
        """Get token frequency."""
        return self._token_freqs.get(token, 0)

    def stats(self) -> VocabStats:
        """Get vocabulary statistics."""
        freqs = list(self._token_freqs.values())
        token_lengths = [len(t) for t in self._token_to_idx.keys()]

        return VocabStats(
            total_tokens=sum(freqs) if freqs else 0,
            unique_tokens=len(self._token_to_idx),
            special_tokens=len(self._special_tokens),
            avg_token_length=sum(token_lengths) / len(token_lengths) if token_lengths else 0,
            min_frequency=min(freqs) if freqs else 0,
            max_frequency=max(freqs) if freqs else 0
        )

    def save(self, path: str) -> None:
        """Save vocabulary to file."""
        data = {
            "config": {
                "vocab_type": self._config.vocab_type.value,
                "min_frequency": self._config.min_frequency,
                "max_vocab_size": self._config.max_vocab_size,
                "lowercase": self._config.lowercase,
                "unk_token": self._config.unk_token,
                "pad_token": self._config.pad_token,
                "special_tokens": self._config.special_tokens
            },
            "vocab": self._token_to_idx,
            "frequencies": self._token_freqs,
            "special": list(self._special_tokens)
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Vocabulary":
        """Load vocabulary from file."""
        with open(path, "r") as f:
            data = json.load(f)

        config_data = data.get("config", {})
        config = VocabConfig(
            vocab_type=VocabType(config_data.get("vocab_type", "word")),
            min_frequency=config_data.get("min_frequency", 1),
            max_vocab_size=config_data.get("max_vocab_size"),
            lowercase=config_data.get("lowercase", True),
            unk_token=config_data.get("unk_token", "[UNK]"),
            pad_token=config_data.get("pad_token", "[PAD]"),
            special_tokens=config_data.get("special_tokens", [])
        )

        vocab = cls(config)

        for token, idx in data.get("vocab", {}).items():
            vocab._token_to_idx[token] = idx
            vocab._idx_to_token[idx] = token

        vocab._token_freqs = data.get("frequencies", {})
        vocab._special_tokens = set(data.get("special", []))
        vocab._next_idx = max(vocab._idx_to_token.keys(), default=-1) + 1

        return vocab


# =============================================================================
# BPE VOCABULARY
# =============================================================================

class BPEVocabulary(Vocabulary):
    """
    Byte-Pair Encoding vocabulary.

    Learns subword units from data.
    """

    def __init__(
        self,
        config: Optional[VocabConfig] = None,
        num_merges: int = 10000
    ):
        config = config or VocabConfig(vocab_type=VocabType.BPE)
        super().__init__(config)

        self._num_merges = num_merges
        self._merges: List[BPEMerge] = []
        self._merge_ranks: Dict[Tuple[str, str], int] = {}

    def train(
        self,
        texts: List[str],
        verbose: bool = False
    ) -> "BPEVocabulary":
        """Train BPE on texts."""
        word_freqs: Dict[str, int] = Counter()

        for text in texts:
            if self._config.lowercase:
                text = text.lower()
            words = text.split()
            for word in words:
                word_with_end = " ".join(list(word)) + " </w>"
                word_freqs[word_with_end] += 1

        for _ in range(self._num_merges):
            pair_freqs = Counter()

            for word, freq in word_freqs.items():
                symbols = word.split()
                for i in range(len(symbols) - 1):
                    pair = (symbols[i], symbols[i + 1])
                    pair_freqs[pair] += freq

            if not pair_freqs:
                break

            best_pair = max(pair_freqs.items(), key=lambda x: x[1])
            pair, freq = best_pair

            new_token = "".join(pair).replace(" ", "")

            merge = BPEMerge(
                pair=pair,
                new_token=new_token,
                frequency=freq,
                priority=len(self._merges)
            )
            self._merges.append(merge)
            self._merge_ranks[pair] = len(self._merges) - 1

            new_word_freqs = {}
            pattern = re.escape(" ".join(pair))
            replacement = new_token

            for word, word_freq in word_freqs.items():
                new_word = re.sub(pattern, replacement, word)
                new_word_freqs[new_word] = word_freq

            word_freqs = new_word_freqs

        all_tokens = set()
        for word in word_freqs.keys():
            all_tokens.update(word.split())

        for token in sorted(all_tokens):
            if token not in self._token_to_idx:
                self._add_token(token)

        return self

    def encode_word(self, word: str) -> List[str]:
        """Encode a word using BPE."""
        if self._config.lowercase:
            word = word.lower()

        tokens = list(word) + ["</w>"]

        while len(tokens) > 1:
            min_pair = None
            min_rank = float("inf")

            for i in range(len(tokens) - 1):
                pair = (tokens[i], tokens[i + 1])
                rank = self._merge_ranks.get(pair, float("inf"))
                if rank < min_rank:
                    min_rank = rank
                    min_pair = (i, pair)

            if min_pair is None or min_rank == float("inf"):
                break

            i, pair = min_pair
            new_token = "".join(pair).replace(" ", "")
            tokens = tokens[:i] + [new_token] + tokens[i + 2:]

        return tokens

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text using BPE."""
        if self._config.lowercase:
            text = text.lower()

        words = text.split()
        tokens = []

        for word in words:
            word_tokens = self.encode_word(word)
            tokens.extend(word_tokens)

        return tokens


# =============================================================================
# VOCABULARY MANAGER
# =============================================================================

class VocabManager:
    """
    Vocabulary Manager for BAEL.

    Comprehensive vocabulary management.
    """

    def __init__(self, vocab_dir: str = "./vocabularies"):
        self._vocab_dir = Path(vocab_dir)
        self._vocab_dir.mkdir(parents=True, exist_ok=True)

        self._vocabularies: Dict[str, Vocabulary] = {}
        self._tokenizers: Dict[TokenizerType, BaseTokenizer] = {
            TokenizerType.WHITESPACE: WhitespaceTokenizer(),
            TokenizerType.WORD_PUNCT: WordPunctTokenizer(),
            TokenizerType.CHARACTER: CharacterTokenizer()
        }

    def create_vocabulary(
        self,
        name: str,
        config: Optional[VocabConfig] = None,
        vocab_type: VocabType = VocabType.WORD
    ) -> Vocabulary:
        """Create a new vocabulary."""
        config = config or VocabConfig(vocab_type=vocab_type)

        if vocab_type == VocabType.BPE:
            vocab = BPEVocabulary(config)
        else:
            vocab = Vocabulary(config)

        self._vocabularies[name] = vocab
        return vocab

    def build_vocabulary(
        self,
        name: str,
        texts: List[str],
        config: Optional[VocabConfig] = None,
        tokenizer_type: TokenizerType = TokenizerType.WHITESPACE
    ) -> Vocabulary:
        """Build vocabulary from texts."""
        config = config or VocabConfig()
        vocab = Vocabulary(config)

        tokenizer = self._tokenizers.get(tokenizer_type, WhitespaceTokenizer())
        vocab.build_from_texts(texts, tokenizer)

        self._vocabularies[name] = vocab
        return vocab

    def train_bpe(
        self,
        name: str,
        texts: List[str],
        num_merges: int = 10000,
        config: Optional[VocabConfig] = None
    ) -> BPEVocabulary:
        """Train BPE vocabulary."""
        config = config or VocabConfig(vocab_type=VocabType.BPE)
        vocab = BPEVocabulary(config, num_merges)
        vocab.train(texts)

        self._vocabularies[name] = vocab
        return vocab

    def get_vocabulary(self, name: str) -> Optional[Vocabulary]:
        """Get a vocabulary by name."""
        return self._vocabularies.get(name)

    def encode(
        self,
        name: str,
        text: str,
        max_length: Optional[int] = None,
        padding: bool = False,
        truncation: bool = False
    ) -> TokenizedText:
        """Encode text using a vocabulary."""
        vocab = self._vocabularies.get(name)
        if not vocab:
            return TokenizedText(original_text=text)

        if isinstance(vocab, BPEVocabulary):
            tokens = vocab.tokenize(text)
        else:
            tokenizer = self._tokenizers.get(
                TokenizerType.WHITESPACE,
                WhitespaceTokenizer()
            )
            tokens = tokenizer.tokenize(
                text.lower() if vocab._config.lowercase else text
            )

        if truncation and max_length and len(tokens) > max_length:
            tokens = tokens[:max_length]

        if padding and max_length and len(tokens) < max_length:
            pad_count = max_length - len(tokens)
            tokens.extend([vocab._config.pad_token] * pad_count)

        token_ids = vocab.tokens_to_ids(tokens)

        attention_mask = [
            0 if t == vocab._config.pad_token else 1
            for t in tokens
        ]

        special_tokens_mask = [
            1 if t in vocab.special_tokens else 0
            for t in tokens
        ]

        return TokenizedText(
            tokens=tokens,
            token_ids=token_ids,
            attention_mask=attention_mask,
            special_tokens_mask=special_tokens_mask,
            original_text=text
        )

    def decode(
        self,
        name: str,
        token_ids: List[int],
        skip_special: bool = True
    ) -> str:
        """Decode token IDs to text."""
        vocab = self._vocabularies.get(name)
        if not vocab:
            return ""

        tokens = vocab.ids_to_tokens(token_ids)

        if skip_special:
            tokens = [t for t in tokens if t not in vocab.special_tokens]

        if isinstance(vocab, BPEVocabulary):
            text = "".join(tokens).replace("</w>", " ").strip()
        else:
            text = " ".join(tokens)

        return text

    def save_vocabulary(self, name: str, path: Optional[str] = None) -> str:
        """Save a vocabulary to file."""
        vocab = self._vocabularies.get(name)
        if not vocab:
            raise ValueError(f"Vocabulary not found: {name}")

        if path is None:
            path = str(self._vocab_dir / f"{name}.json")

        vocab.save(path)
        return path

    def load_vocabulary(self, name: str, path: str) -> Vocabulary:
        """Load a vocabulary from file."""
        vocab = Vocabulary.load(path)
        self._vocabularies[name] = vocab
        return vocab

    def list_vocabularies(self) -> List[str]:
        """List all vocabularies."""
        return list(self._vocabularies.keys())

    def merge_vocabularies(
        self,
        name: str,
        vocab_names: List[str]
    ) -> Vocabulary:
        """Merge multiple vocabularies."""
        merged = Vocabulary()

        for vocab_name in vocab_names:
            vocab = self._vocabularies.get(vocab_name)
            if vocab:
                tokens = list(vocab._token_to_idx.keys())
                merged.add_tokens(tokens, vocab._token_freqs)

        self._vocabularies[name] = merged
        return merged

    def summary(self) -> Dict[str, Any]:
        """Get manager summary."""
        vocab_stats = {}

        for name, vocab in self._vocabularies.items():
            stats = vocab.stats()
            vocab_stats[name] = {
                "size": len(vocab),
                "special_tokens": stats.special_tokens,
                "type": vocab._config.vocab_type.value
            }

        return {
            "vocab_dir": str(self._vocab_dir),
            "total_vocabularies": len(self._vocabularies),
            "vocabularies": vocab_stats,
            "tokenizers": [t.value for t in self._tokenizers.keys()]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Vocabulary Manager."""
    print("=" * 70)
    print("BAEL - VOCABULARY MANAGER DEMO")
    print("NLP Vocabulary Management")
    print("=" * 70)
    print()

    manager = VocabManager(vocab_dir="/tmp/bael_vocabs")

    # Sample texts
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is a subset of artificial intelligence.",
        "Natural language processing enables computers to understand text.",
        "Deep learning models can learn complex patterns from data.",
        "Neural networks are inspired by the human brain.",
        "The transformer architecture revolutionized NLP.",
        "BERT and GPT are popular language models.",
        "Tokenization is the first step in text processing."
    ]

    # 1. Build Word Vocabulary
    print("1. BUILD WORD VOCABULARY:")
    print("-" * 40)

    word_vocab = manager.build_vocabulary(
        "word_vocab",
        texts,
        VocabConfig(min_frequency=1, lowercase=True)
    )

    stats = word_vocab.stats()
    print(f"   Size: {len(word_vocab)}")
    print(f"   Special tokens: {stats.special_tokens}")
    print(f"   Avg token length: {stats.avg_token_length:.2f}")
    print()

    # 2. Encode Text
    print("2. ENCODE TEXT:")
    print("-" * 40)

    text = "The quick brown fox"
    encoded = manager.encode("word_vocab", text)

    print(f"   Text: '{text}'")
    print(f"   Tokens: {encoded.tokens}")
    print(f"   IDs: {encoded.token_ids}")
    print()

    # 3. Decode Text
    print("3. DECODE TEXT:")
    print("-" * 40)

    decoded = manager.decode("word_vocab", encoded.token_ids)

    print(f"   IDs: {encoded.token_ids}")
    print(f"   Decoded: '{decoded}'")
    print()

    # 4. Padding and Truncation
    print("4. PADDING AND TRUNCATION:")
    print("-" * 40)

    padded = manager.encode(
        "word_vocab",
        "short text",
        max_length=10,
        padding=True
    )

    print(f"   Original: 'short text'")
    print(f"   Padded tokens: {padded.tokens}")
    print(f"   Attention mask: {padded.attention_mask}")
    print()

    # 5. Character Vocabulary
    print("5. CHARACTER VOCABULARY:")
    print("-" * 40)

    char_vocab = manager.build_vocabulary(
        "char_vocab",
        texts,
        VocabConfig(vocab_type=VocabType.CHARACTER),
        TokenizerType.CHARACTER
    )

    print(f"   Size: {len(char_vocab)}")

    char_encoded = manager.encode("char_vocab", "hello")
    print(f"   'hello' tokens: {char_encoded.tokens[:10]}...")
    print()

    # 6. Train BPE
    print("6. TRAIN BPE VOCABULARY:")
    print("-" * 40)

    bpe_vocab = manager.train_bpe(
        "bpe_vocab",
        texts,
        num_merges=100
    )

    print(f"   Size: {len(bpe_vocab)}")
    print(f"   Merges: {len(bpe_vocab._merges)}")

    bpe_encoded = manager.encode("bpe_vocab", "learning")
    print(f"   'learning' tokens: {bpe_encoded.tokens}")
    print()

    # 7. Special Tokens
    print("7. SPECIAL TOKENS:")
    print("-" * 40)

    special_config = VocabConfig(
        special_tokens=["[CLS]", "[SEP]", "[MASK]"]
    )
    special_vocab = manager.create_vocabulary("special_vocab", special_config)

    print(f"   Special tokens: {special_vocab.special_tokens}")
    print(f"   PAD ID: {special_vocab.pad_token_id}")
    print(f"   UNK ID: {special_vocab.unk_token_id}")
    print()

    # 8. Token Lookup
    print("8. TOKEN LOOKUP:")
    print("-" * 40)

    test_tokens = ["the", "quick", "unknown_word"]

    for token in test_tokens:
        in_vocab = token in word_vocab
        token_id = word_vocab.token_to_id(token)
        freq = word_vocab.get_frequency(token)
        print(f"   '{token}': in_vocab={in_vocab}, id={token_id}, freq={freq}")
    print()

    # 9. Save and Load
    print("9. SAVE AND LOAD:")
    print("-" * 40)

    save_path = manager.save_vocabulary("word_vocab")
    print(f"   Saved to: {save_path}")

    loaded_vocab = manager.load_vocabulary("word_vocab_loaded", save_path)
    print(f"   Loaded size: {len(loaded_vocab)}")
    print()

    # 10. Manager Summary
    print("10. MANAGER SUMMARY:")
    print("-" * 40)

    summary = manager.summary()

    print(f"   Total vocabularies: {summary['total_vocabularies']}")
    print(f"   Tokenizers: {summary['tokenizers']}")

    for name, info in summary['vocabularies'].items():
        print(f"   - {name}: {info['size']} tokens ({info['type']})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Vocabulary Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
