#!/usr/bin/env python3
"""
BAEL - Token Manager
Advanced token management for AI agent LLM operations.

Features:
- Token counting and estimation
- Token budget management
- Context window optimization
- Token caching
- Usage tracking
- Rate limiting
- Cost estimation
- Multi-model support
"""

import asyncio
import copy
import hashlib
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TokenizerType(Enum):
    """Tokenizer types."""
    SIMPLE = "simple"
    GPT2 = "gpt2"
    GPT4 = "gpt4"
    CLAUDE = "claude"
    LLAMA = "llama"


class ModelFamily(Enum):
    """Model families."""
    GPT = "gpt"
    CLAUDE = "claude"
    LLAMA = "llama"
    MISTRAL = "mistral"
    GEMINI = "gemini"


class UsageType(Enum):
    """Token usage types."""
    INPUT = "input"
    OUTPUT = "output"
    TOTAL = "total"


class TruncationStrategy(Enum):
    """Text truncation strategies."""
    HEAD = "head"
    TAIL = "tail"
    MIDDLE = "middle"
    SENTENCES = "sentences"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TokenCount:
    """Token count result."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated: bool = True


@dataclass
class TokenBudget:
    """Token budget configuration."""
    max_input_tokens: int = 4000
    max_output_tokens: int = 1000
    max_total_tokens: int = 5000
    reserve_tokens: int = 100


@dataclass
class ModelConfig:
    """Model token configuration."""
    model_name: str
    family: ModelFamily
    context_window: int
    max_output_tokens: int
    tokens_per_message: int = 4
    tokens_per_name: int = 1
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class UsageRecord:
    """Token usage record."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageStats:
    """Usage statistics."""
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    tokens_per_minute: int = 60000
    requests_per_minute: int = 100
    tokens_per_day: int = 1000000


# =============================================================================
# SIMPLE TOKENIZER
# =============================================================================

class SimpleTokenizer:
    """Simple word-based tokenizer for estimation."""

    def __init__(self, chars_per_token: float = 4.0):
        self._chars_per_token = chars_per_token

    def count(self, text: str) -> int:
        """Count tokens in text."""
        if not text:
            return 0

        # Simple estimation: characters / chars_per_token
        return max(1, int(len(text) / self._chars_per_token))

    def encode(self, text: str) -> List[int]:
        """Encode text to token IDs (simplified)."""
        words = text.split()
        return list(range(len(words)))

    def decode(self, tokens: List[int]) -> str:
        """Decode tokens (not implemented for simple)."""
        return f"[{len(tokens)} tokens]"


class BPETokenizer:
    """BPE-style tokenizer estimation."""

    def __init__(self, model_type: TokenizerType = TokenizerType.GPT4):
        self._model_type = model_type

        # Approximate chars per token by model
        self._chars_per_token = {
            TokenizerType.GPT2: 4.0,
            TokenizerType.GPT4: 3.5,
            TokenizerType.CLAUDE: 3.5,
            TokenizerType.LLAMA: 3.8,
        }.get(model_type, 4.0)

    def count(self, text: str) -> int:
        """Estimate token count."""
        if not text:
            return 0

        # Account for special characters and whitespace
        # This is a heuristic approximation
        base_count = len(text) / self._chars_per_token

        # Adjust for punctuation (often separate tokens)
        punctuation = len(re.findall(r'[.,!?;:"\'\(\)\[\]\{\}]', text))

        # Adjust for numbers (often multiple tokens)
        numbers = len(re.findall(r'\d+', text))

        adjusted = base_count + punctuation * 0.3 + numbers * 0.2

        return max(1, int(adjusted))

    def count_messages(
        self,
        messages: List[Dict[str, str]],
        tokens_per_message: int = 4,
        tokens_per_name: int = 1
    ) -> int:
        """Count tokens in chat messages."""
        total = 0

        for message in messages:
            total += tokens_per_message

            for key, value in message.items():
                total += self.count(str(value))
                if key == "name":
                    total += tokens_per_name

        total += 3  # Reply priming

        return total


# =============================================================================
# TOKEN COUNTER
# =============================================================================

class TokenCounter:
    """Count tokens for various models."""

    def __init__(self):
        self._tokenizers: Dict[TokenizerType, Any] = {
            TokenizerType.SIMPLE: SimpleTokenizer(),
            TokenizerType.GPT2: BPETokenizer(TokenizerType.GPT2),
            TokenizerType.GPT4: BPETokenizer(TokenizerType.GPT4),
            TokenizerType.CLAUDE: BPETokenizer(TokenizerType.CLAUDE),
            TokenizerType.LLAMA: BPETokenizer(TokenizerType.LLAMA),
        }

        self._model_tokenizers: Dict[str, TokenizerType] = {
            "gpt-4": TokenizerType.GPT4,
            "gpt-4-turbo": TokenizerType.GPT4,
            "gpt-3.5-turbo": TokenizerType.GPT4,
            "claude-3-opus": TokenizerType.CLAUDE,
            "claude-3-sonnet": TokenizerType.CLAUDE,
            "claude-3-haiku": TokenizerType.CLAUDE,
            "llama-2": TokenizerType.LLAMA,
            "llama-3": TokenizerType.LLAMA,
        }

    def count(
        self,
        text: str,
        model: Optional[str] = None,
        tokenizer_type: Optional[TokenizerType] = None
    ) -> int:
        """Count tokens in text."""
        if tokenizer_type:
            tokenizer = self._tokenizers.get(tokenizer_type, SimpleTokenizer())
        elif model:
            tok_type = self._model_tokenizers.get(model, TokenizerType.GPT4)
            tokenizer = self._tokenizers.get(tok_type, SimpleTokenizer())
        else:
            tokenizer = self._tokenizers[TokenizerType.GPT4]

        return tokenizer.count(text)

    def count_messages(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ) -> int:
        """Count tokens in chat messages."""
        tok_type = self._model_tokenizers.get(model or "", TokenizerType.GPT4)
        tokenizer = self._tokenizers.get(tok_type)

        if isinstance(tokenizer, BPETokenizer):
            return tokenizer.count_messages(messages)

        # Fallback
        total = 0
        for msg in messages:
            for value in msg.values():
                total += self.count(str(value), model)
        return total + len(messages) * 4


# =============================================================================
# TOKEN BUDGET MANAGER
# =============================================================================

class TokenBudgetManager:
    """Manage token budgets."""

    def __init__(self, default_budget: Optional[TokenBudget] = None):
        self._default_budget = default_budget or TokenBudget()
        self._budgets: Dict[str, TokenBudget] = {}
        self._usage: Dict[str, int] = defaultdict(int)

    def set_budget(self, name: str, budget: TokenBudget) -> None:
        """Set budget for context."""
        self._budgets[name] = budget

    def get_budget(self, name: str) -> TokenBudget:
        """Get budget for context."""
        return self._budgets.get(name, self._default_budget)

    def check_budget(
        self,
        name: str,
        input_tokens: int,
        output_tokens: int = 0
    ) -> bool:
        """Check if usage is within budget."""
        budget = self.get_budget(name)

        if input_tokens > budget.max_input_tokens:
            return False

        if output_tokens > budget.max_output_tokens:
            return False

        total = input_tokens + output_tokens
        if total > budget.max_total_tokens:
            return False

        return True

    def remaining_budget(
        self,
        name: str,
        current_input: int = 0
    ) -> TokenBudget:
        """Get remaining budget."""
        budget = self.get_budget(name)

        return TokenBudget(
            max_input_tokens=budget.max_input_tokens - current_input,
            max_output_tokens=budget.max_output_tokens,
            max_total_tokens=budget.max_total_tokens - current_input,
            reserve_tokens=budget.reserve_tokens
        )

    def allocate(
        self,
        name: str,
        tokens: int,
        usage_type: UsageType = UsageType.INPUT
    ) -> bool:
        """Allocate tokens from budget."""
        budget = self.get_budget(name)
        key = f"{name}:{usage_type.value}"

        current = self._usage[key]
        limit = budget.max_input_tokens if usage_type == UsageType.INPUT else budget.max_output_tokens

        if current + tokens > limit:
            return False

        self._usage[key] += tokens
        return True

    def reset_usage(self, name: Optional[str] = None) -> None:
        """Reset usage tracking."""
        if name:
            keys = [k for k in self._usage if k.startswith(name)]
            for k in keys:
                del self._usage[k]
        else:
            self._usage.clear()


# =============================================================================
# TEXT TRUNCATOR
# =============================================================================

class TextTruncator:
    """Truncate text to fit token budget."""

    def __init__(self, counter: TokenCounter):
        self._counter = counter

    def truncate(
        self,
        text: str,
        max_tokens: int,
        strategy: TruncationStrategy = TruncationStrategy.TAIL,
        model: Optional[str] = None
    ) -> str:
        """Truncate text to max tokens."""
        current = self._counter.count(text, model)

        if current <= max_tokens:
            return text

        if strategy == TruncationStrategy.TAIL:
            return self._truncate_tail(text, max_tokens, model)
        elif strategy == TruncationStrategy.HEAD:
            return self._truncate_head(text, max_tokens, model)
        elif strategy == TruncationStrategy.MIDDLE:
            return self._truncate_middle(text, max_tokens, model)
        elif strategy == TruncationStrategy.SENTENCES:
            return self._truncate_sentences(text, max_tokens, model)
        else:
            return self._truncate_tail(text, max_tokens, model)

    def _truncate_tail(
        self,
        text: str,
        max_tokens: int,
        model: Optional[str]
    ) -> str:
        """Keep beginning, truncate end."""
        words = text.split()

        # Binary search for right length
        low, high = 0, len(words)

        while low < high:
            mid = (low + high + 1) // 2
            truncated = " ".join(words[:mid])

            if self._counter.count(truncated, model) <= max_tokens:
                low = mid
            else:
                high = mid - 1

        return " ".join(words[:low]) + "..."

    def _truncate_head(
        self,
        text: str,
        max_tokens: int,
        model: Optional[str]
    ) -> str:
        """Truncate beginning, keep end."""
        words = text.split()

        low, high = 0, len(words)

        while low < high:
            mid = (low + high) // 2
            truncated = " ".join(words[mid:])

            if self._counter.count(truncated, model) <= max_tokens:
                high = mid
            else:
                low = mid + 1

        return "..." + " ".join(words[low:])

    def _truncate_middle(
        self,
        text: str,
        max_tokens: int,
        model: Optional[str]
    ) -> str:
        """Keep beginning and end, truncate middle."""
        half_tokens = max_tokens // 2

        head = self._truncate_tail(text, half_tokens, model).rstrip(".")
        tail = self._truncate_head(text, half_tokens, model).lstrip(".")

        return head + " [...] " + tail

    def _truncate_sentences(
        self,
        text: str,
        max_tokens: int,
        model: Optional[str]
    ) -> str:
        """Truncate at sentence boundaries."""
        sentences = re.split(r'(?<=[.!?])\s+', text)

        result = []
        current_tokens = 0

        for sentence in sentences:
            tokens = self._counter.count(sentence, model)

            if current_tokens + tokens <= max_tokens:
                result.append(sentence)
                current_tokens += tokens
            else:
                break

        return " ".join(result)


# =============================================================================
# USAGE TRACKER
# =============================================================================

class UsageTracker:
    """Track token usage over time."""

    def __init__(self):
        self._records: List[UsageRecord] = []
        self._by_model: Dict[str, List[UsageRecord]] = defaultdict(list)

    def record(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """Record usage."""
        record = UsageRecord(
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            metadata=metadata or {}
        )

        self._records.append(record)
        self._by_model[model_name].append(record)

        return record

    def get_stats(
        self,
        model_name: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> UsageStats:
        """Get usage statistics."""
        records = self._by_model.get(model_name, self._records) if model_name else self._records

        if since:
            records = [r for r in records if r.timestamp >= since]

        if not records:
            return UsageStats()

        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_cost = sum(r.cost for r in records)

        return UsageStats(
            total_requests=len(records),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_input + total_output,
            total_cost=total_cost,
            avg_input_tokens=total_input / len(records),
            avg_output_tokens=total_output / len(records)
        )

    def get_records(
        self,
        model_name: Optional[str] = None,
        limit: int = 100
    ) -> List[UsageRecord]:
        """Get recent records."""
        records = self._by_model.get(model_name, self._records) if model_name else self._records
        return records[-limit:]

    def clear(self, before: Optional[datetime] = None) -> int:
        """Clear records."""
        if before:
            original = len(self._records)
            self._records = [r for r in self._records if r.timestamp >= before]

            for model in self._by_model:
                self._by_model[model] = [
                    r for r in self._by_model[model]
                    if r.timestamp >= before
                ]

            return original - len(self._records)
        else:
            count = len(self._records)
            self._records.clear()
            self._by_model.clear()
            return count


# =============================================================================
# RATE LIMITER
# =============================================================================

class TokenRateLimiter:
    """Rate limit token usage."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._minute_usage: Dict[str, List[Tuple[datetime, int]]] = defaultdict(list)
        self._day_usage: Dict[str, int] = defaultdict(int)
        self._last_day: Dict[str, datetime] = {}

    def check(self, model: str, tokens: int) -> bool:
        """Check if request is within limits."""
        now = datetime.now()

        # Check daily limit
        if model in self._last_day:
            if (now - self._last_day[model]).days >= 1:
                self._day_usage[model] = 0
                self._last_day[model] = now
        else:
            self._last_day[model] = now

        if self._day_usage[model] + tokens > self.config.tokens_per_day:
            return False

        # Check minute limit
        minute_ago = now - timedelta(minutes=1)
        self._minute_usage[model] = [
            (t, count) for t, count in self._minute_usage[model]
            if t > minute_ago
        ]

        minute_total = sum(count for _, count in self._minute_usage[model])

        if minute_total + tokens > self.config.tokens_per_minute:
            return False

        return True

    def record(self, model: str, tokens: int) -> None:
        """Record token usage."""
        now = datetime.now()

        self._minute_usage[model].append((now, tokens))
        self._day_usage[model] += tokens

    def remaining(self, model: str) -> Dict[str, int]:
        """Get remaining limits."""
        minute_ago = datetime.now() - timedelta(minutes=1)

        minute_used = sum(
            count for t, count in self._minute_usage[model]
            if t > minute_ago
        )

        return {
            "tokens_per_minute": self.config.tokens_per_minute - minute_used,
            "tokens_per_day": self.config.tokens_per_day - self._day_usage[model]
        }


# =============================================================================
# TOKEN MANAGER
# =============================================================================

class TokenManager:
    """
    Token Manager for BAEL.

    Advanced token management for LLM operations.
    """

    def __init__(self):
        self._counter = TokenCounter()
        self._budget_manager = TokenBudgetManager()
        self._truncator = TextTruncator(self._counter)
        self._tracker = UsageTracker()
        self._rate_limiter = TokenRateLimiter(RateLimitConfig())

        self._model_configs: Dict[str, ModelConfig] = {}
        self._setup_default_models()

    def _setup_default_models(self) -> None:
        """Setup default model configurations."""
        configs = [
            ModelConfig(
                model_name="gpt-4-turbo",
                family=ModelFamily.GPT,
                context_window=128000,
                max_output_tokens=4096,
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03
            ),
            ModelConfig(
                model_name="gpt-3.5-turbo",
                family=ModelFamily.GPT,
                context_window=16000,
                max_output_tokens=4096,
                cost_per_1k_input=0.0005,
                cost_per_1k_output=0.0015
            ),
            ModelConfig(
                model_name="claude-3-opus",
                family=ModelFamily.CLAUDE,
                context_window=200000,
                max_output_tokens=4096,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075
            ),
            ModelConfig(
                model_name="claude-3-sonnet",
                family=ModelFamily.CLAUDE,
                context_window=200000,
                max_output_tokens=4096,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015
            ),
        ]

        for config in configs:
            self._model_configs[config.model_name] = config

    # -------------------------------------------------------------------------
    # COUNTING
    # -------------------------------------------------------------------------

    def count_tokens(
        self,
        text: str,
        model: Optional[str] = None
    ) -> int:
        """Count tokens in text."""
        return self._counter.count(text, model)

    def count_messages(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ) -> int:
        """Count tokens in messages."""
        return self._counter.count_messages(messages, model)

    # -------------------------------------------------------------------------
    # BUDGET
    # -------------------------------------------------------------------------

    def set_budget(
        self,
        name: str,
        max_input: int = 4000,
        max_output: int = 1000
    ) -> None:
        """Set token budget."""
        budget = TokenBudget(
            max_input_tokens=max_input,
            max_output_tokens=max_output,
            max_total_tokens=max_input + max_output
        )
        self._budget_manager.set_budget(name, budget)

    def check_budget(
        self,
        name: str,
        text: str,
        model: Optional[str] = None
    ) -> bool:
        """Check if text fits in budget."""
        tokens = self.count_tokens(text, model)
        return self._budget_manager.check_budget(name, tokens)

    def remaining_tokens(self, name: str) -> int:
        """Get remaining input tokens."""
        return self._budget_manager.get_budget(name).max_input_tokens

    # -------------------------------------------------------------------------
    # TRUNCATION
    # -------------------------------------------------------------------------

    def truncate(
        self,
        text: str,
        max_tokens: int,
        strategy: TruncationStrategy = TruncationStrategy.TAIL,
        model: Optional[str] = None
    ) -> str:
        """Truncate text to fit token limit."""
        return self._truncator.truncate(text, max_tokens, strategy, model)

    def fit_to_budget(
        self,
        text: str,
        budget_name: str,
        model: Optional[str] = None
    ) -> str:
        """Truncate text to fit budget."""
        budget = self._budget_manager.get_budget(budget_name)
        return self.truncate(text, budget.max_input_tokens, model=model)

    # -------------------------------------------------------------------------
    # USAGE TRACKING
    # -------------------------------------------------------------------------

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Record usage and return cost."""
        config = self._model_configs.get(model)

        cost = 0.0
        if config:
            cost = (
                (input_tokens / 1000) * config.cost_per_1k_input +
                (output_tokens / 1000) * config.cost_per_1k_output
            )

        self._tracker.record(model, input_tokens, output_tokens, cost)
        self._rate_limiter.record(model, input_tokens + output_tokens)

        return cost

    def get_usage_stats(
        self,
        model: Optional[str] = None
    ) -> UsageStats:
        """Get usage statistics."""
        return self._tracker.get_stats(model)

    # -------------------------------------------------------------------------
    # RATE LIMITING
    # -------------------------------------------------------------------------

    def check_rate_limit(self, model: str, tokens: int) -> bool:
        """Check rate limit."""
        return self._rate_limiter.check(model, tokens)

    def get_rate_limits(self, model: str) -> Dict[str, int]:
        """Get remaining rate limits."""
        return self._rate_limiter.remaining(model)

    # -------------------------------------------------------------------------
    # COST ESTIMATION
    # -------------------------------------------------------------------------

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estimate cost for request."""
        config = self._model_configs.get(model)
        if not config:
            return 0.0

        return (
            (input_tokens / 1000) * config.cost_per_1k_input +
            (output_tokens / 1000) * config.cost_per_1k_output
        )

    def estimate_text_cost(
        self,
        text: str,
        model: str,
        output_ratio: float = 0.5
    ) -> float:
        """Estimate cost for text."""
        input_tokens = self.count_tokens(text, model)
        output_tokens = int(input_tokens * output_ratio)

        return self.estimate_cost(model, input_tokens, output_tokens)

    # -------------------------------------------------------------------------
    # MODEL INFO
    # -------------------------------------------------------------------------

    def get_model_config(self, model: str) -> Optional[ModelConfig]:
        """Get model configuration."""
        return self._model_configs.get(model)

    def get_context_window(self, model: str) -> int:
        """Get model context window."""
        config = self._model_configs.get(model)
        return config.context_window if config else 4096

    def list_models(self) -> List[str]:
        """List configured models."""
        return list(self._model_configs.keys())


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Token Manager."""
    print("=" * 70)
    print("BAEL - TOKEN MANAGER DEMO")
    print("Advanced Token Management for AI Agents")
    print("=" * 70)
    print()

    manager = TokenManager()

    # 1. Token Counting
    print("1. TOKEN COUNTING:")
    print("-" * 40)

    text = "Hello, world! This is a test of the token counting system."
    tokens = manager.count_tokens(text)

    print(f"   Text: '{text}'")
    print(f"   Tokens: {tokens}")
    print()

    # 2. Model-specific Counting
    print("2. MODEL-SPECIFIC COUNTING:")
    print("-" * 40)

    for model in ["gpt-4-turbo", "claude-3-opus"]:
        tokens = manager.count_tokens(text, model)
        print(f"   {model}: {tokens} tokens")
    print()

    # 3. Message Counting
    print("3. MESSAGE COUNTING:")
    print("-" * 40)

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."}
    ]

    tokens = manager.count_messages(messages)
    print(f"   Messages: {len(messages)}")
    print(f"   Total tokens: {tokens}")
    print()

    # 4. Token Budget
    print("4. TOKEN BUDGET:")
    print("-" * 40)

    manager.set_budget("chat", max_input=1000, max_output=500)

    short_text = "Hello!"
    long_text = "x" * 10000

    print(f"   Short text fits: {manager.check_budget('chat', short_text)}")
    print(f"   Long text fits: {manager.check_budget('chat', long_text)}")
    print()

    # 5. Truncation
    print("5. TEXT TRUNCATION:")
    print("-" * 40)

    long_text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four. This is sentence five."

    truncated = manager.truncate(long_text, 10, TruncationStrategy.TAIL)
    print(f"   Original: {len(long_text)} chars")
    print(f"   Truncated (tail): '{truncated}'")

    truncated = manager.truncate(long_text, 10, TruncationStrategy.SENTENCES)
    print(f"   Truncated (sentences): '{truncated}'")
    print()

    # 6. Usage Tracking
    print("6. USAGE TRACKING:")
    print("-" * 40)

    cost1 = manager.record_usage("gpt-4-turbo", 1000, 500)
    cost2 = manager.record_usage("gpt-4-turbo", 2000, 1000)
    cost3 = manager.record_usage("claude-3-opus", 500, 200)

    print(f"   Recorded 3 requests")
    print(f"   Costs: ${cost1:.4f}, ${cost2:.4f}, ${cost3:.4f}")
    print()

    # 7. Usage Statistics
    print("7. USAGE STATISTICS:")
    print("-" * 40)

    stats = manager.get_usage_stats()
    print(f"   Total requests: {stats.total_requests}")
    print(f"   Total input tokens: {stats.total_input_tokens}")
    print(f"   Total output tokens: {stats.total_output_tokens}")
    print(f"   Total cost: ${stats.total_cost:.4f}")
    print()

    # 8. Model-specific Stats
    print("8. MODEL-SPECIFIC STATS:")
    print("-" * 40)

    gpt_stats = manager.get_usage_stats("gpt-4-turbo")
    print(f"   GPT-4 requests: {gpt_stats.total_requests}")
    print(f"   GPT-4 tokens: {gpt_stats.total_tokens}")
    print()

    # 9. Cost Estimation
    print("9. COST ESTIMATION:")
    print("-" * 40)

    cost = manager.estimate_cost("gpt-4-turbo", 10000, 2000)
    print(f"   10K input + 2K output (gpt-4-turbo): ${cost:.4f}")

    cost = manager.estimate_cost("claude-3-opus", 10000, 2000)
    print(f"   10K input + 2K output (claude-3-opus): ${cost:.4f}")
    print()

    # 10. Rate Limits
    print("10. RATE LIMITS:")
    print("-" * 40)

    can_proceed = manager.check_rate_limit("gpt-4-turbo", 5000)
    print(f"   Can use 5K tokens: {can_proceed}")

    remaining = manager.get_rate_limits("gpt-4-turbo")
    print(f"   Remaining per minute: {remaining['tokens_per_minute']}")
    print()

    # 11. Context Window
    print("11. CONTEXT WINDOWS:")
    print("-" * 40)

    for model in manager.list_models():
        window = manager.get_context_window(model)
        print(f"   {model}: {window:,} tokens")
    print()

    # 12. Model Config
    print("12. MODEL CONFIG:")
    print("-" * 40)

    config = manager.get_model_config("gpt-4-turbo")
    if config:
        print(f"   Model: {config.model_name}")
        print(f"   Family: {config.family.value}")
        print(f"   Context: {config.context_window:,}")
        print(f"   Cost: ${config.cost_per_1k_input}/1K in, ${config.cost_per_1k_output}/1K out")
    print()

    # 13. Fit to Budget
    print("13. FIT TO BUDGET:")
    print("-" * 40)

    manager.set_budget("small", max_input=20, max_output=10)
    fitted = manager.fit_to_budget(long_text, "small")
    print(f"   Budget: 20 tokens")
    print(f"   Fitted: '{fitted}'")
    print()

    # 14. Text Cost Estimation
    print("14. TEXT COST ESTIMATION:")
    print("-" * 40)

    sample = "This is a sample prompt for the AI model."
    cost = manager.estimate_text_cost(sample, "gpt-4-turbo", output_ratio=1.0)
    print(f"   Text: '{sample}'")
    print(f"   Estimated cost: ${cost:.6f}")
    print()

    # 15. List Models
    print("15. CONFIGURED MODELS:")
    print("-" * 40)

    models = manager.list_models()
    print(f"   Models: {models}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Token Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
