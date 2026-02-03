#!/usr/bin/env python3
"""
BAEL - Tokenizer Engine
Comprehensive text tokenization for NLP pipelines.

Features:
- Character-level tokenization
- Word-level tokenization
- Subword tokenization (BPE)
- Special token handling
- Vocabulary management
- Encoding/decoding
"""

import asyncio
import math
import random
import re
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TokenizerType(Enum):
    """Tokenizer types."""
    CHARACTER = "character"
    WORD = "word"
    WHITESPACE = "whitespace"
    BPE = "bpe"
    WORDPIECE = "wordpiece"
    SENTENCEPIECE = "sentencepiece"
    CUSTOM = "custom"


class PaddingStrategy(Enum):
    """Padding strategies."""
    LONGEST = "longest"
    MAX_LENGTH = "max_length"
    DO_NOT_PAD = "do_not_pad"


class TruncationStrategy(Enum):
    """Truncation strategies."""
    LONGEST_FIRST = "longest_first"
    ONLY_FIRST = "only_first"
    ONLY_SECOND = "only_second"
    DO_NOT_TRUNCATE = "do_not_truncate"


class SpecialToken(Enum):
    """Special tokens."""
    PAD = "[PAD]"
    UNK = "[UNK]"
    CLS = "[CLS]"
    SEP = "[SEP]"
    MASK = "[MASK]"
    BOS = "[BOS]"
    EOS = "[EOS]"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Token:
    """A single token."""
    token_id: int = 0
    text: str = ""
    start: int = 0
    end: int = 0
    is_special: bool = False


@dataclass
class EncodedSequence:
    """Encoded sequence."""
    input_ids: List[int] = field(default_factory=list)
    attention_mask: List[int] = field(default_factory=list)
    token_type_ids: List[int] = field(default_factory=list)
    tokens: List[Token] = field(default_factory=list)
    length: int = 0

    def __post_init__(self):
        self.length = len(self.input_ids)


@dataclass
class Vocabulary:
    """Token vocabulary."""
    token_to_id: Dict[str, int] = field(default_factory=dict)
    id_to_token: Dict[int, str] = field(default_factory=dict)
    size: int = 0

    def add_token(self, token: str) -> int:
        """Add token to vocabulary."""
        if token not in self.token_to_id:
            self.token_to_id[token] = self.size
            self.id_to_token[self.size] = token
            self.size += 1
        return self.token_to_id[token]

    def get_id(self, token: str) -> Optional[int]:
        """Get token ID."""
        return self.token_to_id.get(token)

    def get_token(self, token_id: int) -> Optional[str]:
        """Get token by ID."""
        return self.id_to_token.get(token_id)


@dataclass
class TokenizerConfig:
    """Tokenizer configuration."""
    vocab_size: int = 30000
    max_length: int = 512
    lowercase: bool = True
    strip_accents: bool = False
    pad_token: str = "[PAD]"
    unk_token: str = "[UNK]"
    cls_token: str = "[CLS]"
    sep_token: str = "[SEP]"
    mask_token: str = "[MASK]"


# =============================================================================
# TOKENIZER BASE
# =============================================================================

class BaseTokenizer(ABC):
    """Abstract base tokenizer."""

    def __init__(self, config: Optional[TokenizerConfig] = None):
        self.config = config or TokenizerConfig()
        self.vocab = Vocabulary()
        self._init_special_tokens()

    def _init_special_tokens(self) -> None:
        """Initialize special tokens."""
        self.vocab.add_token(self.config.pad_token)
        self.vocab.add_token(self.config.unk_token)
        self.vocab.add_token(self.config.cls_token)
        self.vocab.add_token(self.config.sep_token)
        self.vocab.add_token(self.config.mask_token)

    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into tokens."""
        pass

    def encode(
        self,
        text: str,
        add_special_tokens: bool = True,
        max_length: Optional[int] = None,
        padding: PaddingStrategy = PaddingStrategy.DO_NOT_PAD,
        truncation: bool = False
    ) -> EncodedSequence:
        """Encode text to token IDs."""
        tokens = self.tokenize(text)

        if truncation:
            max_len = max_length or self.config.max_length
            if add_special_tokens:
                max_len -= 2
            tokens = tokens[:max_len]

        if add_special_tokens:
            tokens = [self.config.cls_token] + tokens + [self.config.sep_token]

        input_ids = []
        token_objects = []

        for i, token in enumerate(tokens):
            token_id = self.vocab.get_id(token)
            if token_id is None:
                token_id = self.vocab.get_id(self.config.unk_token)
            input_ids.append(token_id)

            token_objects.append(Token(
                token_id=token_id,
                text=token,
                start=i,
                end=i + 1,
                is_special=token in [
                    self.config.pad_token,
                    self.config.unk_token,
                    self.config.cls_token,
                    self.config.sep_token,
                    self.config.mask_token
                ]
            ))

        attention_mask = [1] * len(input_ids)

        if padding != PaddingStrategy.DO_NOT_PAD:
            target_len = max_length or self.config.max_length

            if len(input_ids) < target_len:
                pad_len = target_len - len(input_ids)
                pad_id = self.vocab.get_id(self.config.pad_token)

                input_ids.extend([pad_id] * pad_len)
                attention_mask.extend([0] * pad_len)

        return EncodedSequence(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=[0] * len(input_ids),
            tokens=token_objects
        )

    def decode(
        self,
        token_ids: List[int],
        skip_special_tokens: bool = True
    ) -> str:
        """Decode token IDs to text."""
        tokens = []

        special = {
            self.config.pad_token,
            self.config.unk_token,
            self.config.cls_token,
            self.config.sep_token,
            self.config.mask_token
        }

        for token_id in token_ids:
            token = self.vocab.get_token(token_id)
            if token:
                if skip_special_tokens and token in special:
                    continue
                tokens.append(token)

        return self._join_tokens(tokens)

    def _join_tokens(self, tokens: List[str]) -> str:
        """Join tokens into text."""
        return " ".join(tokens)

    def batch_encode(
        self,
        texts: List[str],
        **kwargs
    ) -> List[EncodedSequence]:
        """Encode multiple texts."""
        return [self.encode(text, **kwargs) for text in texts]


# =============================================================================
# TOKENIZER IMPLEMENTATIONS
# =============================================================================

class CharacterTokenizer(BaseTokenizer):
    """Character-level tokenizer."""

    def __init__(self, config: Optional[TokenizerConfig] = None):
        super().__init__(config)

    def tokenize(self, text: str) -> List[str]:
        """Tokenize by character."""
        if self.config.lowercase:
            text = text.lower()
        return list(text)

    def _join_tokens(self, tokens: List[str]) -> str:
        """Join characters."""
        return "".join(tokens)

    def build_vocab(self, texts: List[str]) -> None:
        """Build vocabulary from texts."""
        for text in texts:
            for char in text:
                if self.config.lowercase:
                    char = char.lower()
                self.vocab.add_token(char)


class WhitespaceTokenizer(BaseTokenizer):
    """Whitespace tokenizer."""

    def tokenize(self, text: str) -> List[str]:
        """Tokenize by whitespace."""
        if self.config.lowercase:
            text = text.lower()
        return text.split()

    def build_vocab(self, texts: List[str]) -> None:
        """Build vocabulary from texts."""
        for text in texts:
            for token in self.tokenize(text):
                self.vocab.add_token(token)


class WordTokenizer(BaseTokenizer):
    """Word tokenizer with punctuation handling."""

    def __init__(self, config: Optional[TokenizerConfig] = None):
        super().__init__(config)
        self._pattern = re.compile(r'\w+|[^\w\s]')

    def tokenize(self, text: str) -> List[str]:
        """Tokenize by words and punctuation."""
        if self.config.lowercase:
            text = text.lower()
        return self._pattern.findall(text)

    def build_vocab(self, texts: List[str]) -> None:
        """Build vocabulary from texts."""
        for text in texts:
            for token in self.tokenize(text):
                self.vocab.add_token(token)


class BPETokenizer(BaseTokenizer):
    """Byte Pair Encoding tokenizer."""

    def __init__(
        self,
        config: Optional[TokenizerConfig] = None,
        num_merges: int = 1000
    ):
        super().__init__(config)
        self._num_merges = num_merges
        self._merges: List[Tuple[str, str]] = []
        self._word_tokenizer = WordTokenizer(config)

    def _get_pairs(self, word: List[str]) -> Set[Tuple[str, str]]:
        """Get adjacent pairs in word."""
        pairs = set()
        for i in range(len(word) - 1):
            pairs.add((word[i], word[i + 1]))
        return pairs

    def _merge_pair(
        self,
        pair: Tuple[str, str],
        word: List[str]
    ) -> List[str]:
        """Merge a pair in word."""
        new_word = []
        i = 0

        while i < len(word):
            if i < len(word) - 1 and word[i] == pair[0] and word[i + 1] == pair[1]:
                new_word.append(pair[0] + pair[1])
                i += 2
            else:
                new_word.append(word[i])
                i += 1

        return new_word

    def train(self, texts: List[str]) -> None:
        """Train BPE on texts."""
        words: Dict[str, int] = defaultdict(int)

        for text in texts:
            tokens = self._word_tokenizer.tokenize(text)
            for token in tokens:
                words[" ".join(token) + " </w>"] += 1

        for word in words:
            for char in word.split():
                self.vocab.add_token(char)

        for _ in range(self._num_merges):
            pairs: Dict[Tuple[str, str], int] = defaultdict(int)

            for word, freq in words.items():
                symbols = word.split()
                for pair in self._get_pairs(symbols):
                    pairs[pair] += freq

            if not pairs:
                break

            best_pair = max(pairs, key=pairs.get)
            self._merges.append(best_pair)

            merged_token = best_pair[0] + best_pair[1]
            self.vocab.add_token(merged_token)

            new_words = {}
            for word, freq in words.items():
                symbols = word.split()
                merged = self._merge_pair(best_pair, symbols)
                new_words[" ".join(merged)] = freq
            words = new_words

    def tokenize(self, text: str) -> List[str]:
        """Tokenize using learned BPE."""
        if self.config.lowercase:
            text = text.lower()

        words = self._word_tokenizer.tokenize(text)
        tokens = []

        for word in words:
            word_chars = list(word) + ["</w>"]

            for pair in self._merges:
                word_chars = self._merge_pair(pair, word_chars)

            tokens.extend(word_chars)

        return tokens

    def _join_tokens(self, tokens: List[str]) -> str:
        """Join BPE tokens."""
        text = "".join(tokens)
        text = text.replace("</w>", " ")
        return text.strip()


class WordPieceTokenizer(BaseTokenizer):
    """WordPiece tokenizer (used by BERT)."""

    def __init__(
        self,
        config: Optional[TokenizerConfig] = None,
        prefix: str = "##"
    ):
        super().__init__(config)
        self._prefix = prefix
        self._word_tokenizer = WordTokenizer(config)

    def build_vocab(self, texts: List[str], max_vocab: int = 30000) -> None:
        """Build WordPiece vocabulary."""
        word_counts: Counter = Counter()

        for text in texts:
            tokens = self._word_tokenizer.tokenize(text)
            word_counts.update(tokens)

        for word, _ in word_counts.most_common(max_vocab - self.vocab.size):
            for i, char in enumerate(word):
                if i == 0:
                    self.vocab.add_token(char)
                else:
                    self.vocab.add_token(self._prefix + char)
            self.vocab.add_token(word)

    def tokenize(self, text: str) -> List[str]:
        """Tokenize using WordPiece."""
        if self.config.lowercase:
            text = text.lower()

        words = self._word_tokenizer.tokenize(text)
        tokens = []

        for word in words:
            if self.vocab.get_id(word) is not None:
                tokens.append(word)
                continue

            sub_tokens = []
            start = 0

            while start < len(word):
                end = len(word)
                found = None

                while start < end:
                    substr = word[start:end]
                    if start > 0:
                        substr = self._prefix + substr

                    if self.vocab.get_id(substr) is not None:
                        found = substr
                        break
                    end -= 1

                if found is None:
                    sub_tokens.append(self.config.unk_token)
                    break

                sub_tokens.append(found)
                start = end

            tokens.extend(sub_tokens)

        return tokens

    def _join_tokens(self, tokens: List[str]) -> str:
        """Join WordPiece tokens."""
        text = ""
        for token in tokens:
            if token.startswith(self._prefix):
                text += token[len(self._prefix):]
            else:
                text += " " + token
        return text.strip()


# =============================================================================
# TOKENIZER ENGINE
# =============================================================================

class TokenizerEngine:
    """
    Tokenizer Engine for BAEL.

    Comprehensive text tokenization for NLP pipelines.
    """

    def __init__(self):
        self._tokenizers: Dict[str, BaseTokenizer] = {}
        self._default: Optional[str] = None

    def create_tokenizer(
        self,
        name: str,
        tokenizer_type: TokenizerType,
        config: Optional[TokenizerConfig] = None
    ) -> BaseTokenizer:
        """Create and register tokenizer."""
        if tokenizer_type == TokenizerType.CHARACTER:
            tokenizer = CharacterTokenizer(config)
        elif tokenizer_type == TokenizerType.WHITESPACE:
            tokenizer = WhitespaceTokenizer(config)
        elif tokenizer_type == TokenizerType.WORD:
            tokenizer = WordTokenizer(config)
        elif tokenizer_type == TokenizerType.BPE:
            tokenizer = BPETokenizer(config)
        elif tokenizer_type == TokenizerType.WORDPIECE:
            tokenizer = WordPieceTokenizer(config)
        else:
            tokenizer = WhitespaceTokenizer(config)

        self._tokenizers[name] = tokenizer

        if self._default is None:
            self._default = name

        return tokenizer

    def get_tokenizer(self, name: str) -> Optional[BaseTokenizer]:
        """Get tokenizer by name."""
        return self._tokenizers.get(name)

    def set_default(self, name: str) -> bool:
        """Set default tokenizer."""
        if name in self._tokenizers:
            self._default = name
            return True
        return False

    def tokenize(self, text: str, tokenizer_name: Optional[str] = None) -> List[str]:
        """Tokenize using specified or default tokenizer."""
        name = tokenizer_name or self._default
        if not name or name not in self._tokenizers:
            return text.split()
        return self._tokenizers[name].tokenize(text)

    def encode(
        self,
        text: str,
        tokenizer_name: Optional[str] = None,
        **kwargs
    ) -> EncodedSequence:
        """Encode using specified or default tokenizer."""
        name = tokenizer_name or self._default
        if not name or name not in self._tokenizers:
            return EncodedSequence()
        return self._tokenizers[name].encode(text, **kwargs)

    def decode(
        self,
        token_ids: List[int],
        tokenizer_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """Decode using specified or default tokenizer."""
        name = tokenizer_name or self._default
        if not name or name not in self._tokenizers:
            return ""
        return self._tokenizers[name].decode(token_ids, **kwargs)

    def batch_encode(
        self,
        texts: List[str],
        tokenizer_name: Optional[str] = None,
        **kwargs
    ) -> List[EncodedSequence]:
        """Batch encode texts."""
        name = tokenizer_name or self._default
        if not name or name not in self._tokenizers:
            return []
        return self._tokenizers[name].batch_encode(texts, **kwargs)

    def build_vocab(
        self,
        texts: List[str],
        tokenizer_name: Optional[str] = None
    ) -> None:
        """Build vocabulary for tokenizer."""
        name = tokenizer_name or self._default
        if name and name in self._tokenizers:
            tokenizer = self._tokenizers[name]
            if hasattr(tokenizer, 'build_vocab'):
                tokenizer.build_vocab(texts)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Tokenizer Engine."""
    print("=" * 70)
    print("BAEL - TOKENIZER ENGINE DEMO")
    print("Comprehensive Text Tokenization for NLP Pipelines")
    print("=" * 70)
    print()

    engine = TokenizerEngine()

    sample_text = "Hello world! This is a test of the tokenizer engine."

    # 1. Character Tokenizer
    print("1. CHARACTER TOKENIZER:")
    print("-" * 40)

    char_tok = engine.create_tokenizer("char", TokenizerType.CHARACTER)
    char_tokens = engine.tokenize(sample_text, "char")

    print(f"   Text: {sample_text}")
    print(f"   Tokens: {char_tokens[:20]}...")
    print(f"   Count: {len(char_tokens)}")
    print()

    # 2. Whitespace Tokenizer
    print("2. WHITESPACE TOKENIZER:")
    print("-" * 40)

    ws_tok = engine.create_tokenizer("whitespace", TokenizerType.WHITESPACE)
    ws_tokens = engine.tokenize(sample_text, "whitespace")

    print(f"   Tokens: {ws_tokens}")
    print()

    # 3. Word Tokenizer
    print("3. WORD TOKENIZER:")
    print("-" * 40)

    word_tok = engine.create_tokenizer("word", TokenizerType.WORD)
    word_tokens = engine.tokenize(sample_text, "word")

    print(f"   Tokens: {word_tokens}")
    print()

    # 4. Build Vocabulary
    print("4. BUILD VOCABULARY:")
    print("-" * 40)

    corpus = [
        "the quick brown fox",
        "jumps over the lazy dog",
        "hello world program",
        "machine learning models"
    ]

    engine.build_vocab(corpus, "word")

    tokenizer = engine.get_tokenizer("word")
    print(f"   Vocabulary size: {tokenizer.vocab.size}")
    print(f"   Sample tokens: {list(tokenizer.vocab.token_to_id.keys())[:10]}")
    print()

    # 5. Encoding
    print("5. ENCODING:")
    print("-" * 40)

    encoded = engine.encode("hello world", "word", add_special_tokens=True)

    print(f"   Input IDs: {encoded.input_ids}")
    print(f"   Attention mask: {encoded.attention_mask}")
    print(f"   Length: {encoded.length}")
    print()

    # 6. Decoding
    print("6. DECODING:")
    print("-" * 40)

    decoded = engine.decode(encoded.input_ids, "word", skip_special_tokens=True)

    print(f"   Decoded: {decoded}")
    print()

    # 7. Padding
    print("7. PADDING:")
    print("-" * 40)

    padded = engine.encode(
        "hello world",
        "word",
        add_special_tokens=True,
        max_length=10,
        padding=PaddingStrategy.MAX_LENGTH
    )

    print(f"   Input IDs: {padded.input_ids}")
    print(f"   Attention mask: {padded.attention_mask}")
    print()

    # 8. Truncation
    print("8. TRUNCATION:")
    print("-" * 40)

    long_text = "this is a very long sentence with many words that needs to be truncated"
    truncated = engine.encode(
        long_text,
        "word",
        add_special_tokens=True,
        max_length=8,
        truncation=True
    )

    print(f"   Original tokens: {len(engine.tokenize(long_text, 'word'))}")
    print(f"   Truncated IDs: {truncated.input_ids}")
    print()

    # 9. Batch Encoding
    print("9. BATCH ENCODING:")
    print("-" * 40)

    texts = ["hello world", "good morning", "how are you"]
    batch = engine.batch_encode(texts, "word")

    for i, encoded in enumerate(batch):
        print(f"   Text {i + 1}: {encoded.input_ids}")
    print()

    # 10. BPE Tokenizer
    print("10. BPE TOKENIZER:")
    print("-" * 40)

    bpe_tok = engine.create_tokenizer("bpe", TokenizerType.BPE)

    training_corpus = [
        "low lower lowest",
        "new newer newest",
        "wide wider widest"
    ]

    bpe_tok.train(training_corpus)

    bpe_tokens = engine.tokenize("lower", "bpe")
    print(f"   Text: 'lower'")
    print(f"   BPE tokens: {bpe_tokens}")
    print(f"   Vocab size: {bpe_tok.vocab.size}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Tokenizer Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
