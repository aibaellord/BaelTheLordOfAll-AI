"""
Adaptive Rate Limiter - Intelligent API Management
===================================================

Advanced rate limiting bypass and optimization techniques.

"Patience is not a virtue - intelligent timing is." — Ba'el
"""

import asyncio
import logging
import random
import time
from collections import deque
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger("BAEL.HiddenTechniques.RateLimiter")


class RateLimitStrategy(Enum):
    """Rate limit handling strategies."""
    FIXED_DELAY = "fixed_delay"          # Simple fixed delay
    EXPONENTIAL_BACKOFF = "exponential"  # Exponential backoff
    ADAPTIVE = "adaptive"                 # Learns optimal timing
    PREDICTIVE = "predictive"            # Predicts rate limits
    BURST = "burst"                      # Burst with recovery
    DISTRIBUTED = "distributed"          # Spread across time
    JITTER = "jitter"                    # Random jitter
    TOKEN_BUCKET = "token_bucket"        # Token bucket algorithm
    SLIDING_WINDOW = "sliding_window"    # Sliding window


class ProviderType(Enum):
    """API provider types with known limits."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    GROQ = "groq"
    GOOGLE = "google"
    AZURE = "azure"
    CUSTOM = "custom"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 3500
    tokens_per_minute: int = 100000
    max_concurrent: int = 10
    retry_after_seconds: float = 1.0
    max_retries: int = 5
    jitter_range: Tuple[float, float] = (0.1, 0.5)


@dataclass
class RequestStats:
    """Request statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    rate_limited_requests: int = 0
    total_wait_time: float = 0.0
    average_latency: float = 0.0
    tokens_used: int = 0


@dataclass
class RequestWindow:
    """Sliding window for request tracking."""
    timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    tokens: deque = field(default_factory=lambda: deque(maxlen=1000))

    def add(self, timestamp: float, tokens: int = 0):
        self.timestamps.append(timestamp)
        self.tokens.append(tokens)

    def count_since(self, since: float) -> int:
        return sum(1 for t in self.timestamps if t >= since)

    def tokens_since(self, since: float) -> int:
        return sum(t for ts, t in zip(self.timestamps, self.tokens) if ts >= since)


# Provider-specific configurations
PROVIDER_CONFIGS = {
    ProviderType.OPENAI: RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=3500,
        tokens_per_minute=90000,
        max_concurrent=10,
    ),
    ProviderType.ANTHROPIC: RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        tokens_per_minute=100000,
        max_concurrent=5,
    ),
    ProviderType.OPENROUTER: RateLimitConfig(
        requests_per_minute=200,
        requests_per_hour=10000,
        tokens_per_minute=500000,
        max_concurrent=20,
    ),
    ProviderType.GROQ: RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=1000,
        tokens_per_minute=30000,
        max_concurrent=5,
    ),
    ProviderType.GOOGLE: RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1500,
        tokens_per_minute=60000,
        max_concurrent=10,
    ),
}


class AdaptiveRateLimiter:
    """
    Intelligent rate limiter that adapts to API behavior.

    Features:
    - Learns optimal request timing
    - Predicts rate limit windows
    - Distributes requests intelligently
    - Handles multiple providers
    - Automatic retry with smart backoff
    """

    def __init__(
        self,
        provider: ProviderType = ProviderType.CUSTOM,
        strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE,
        config: RateLimitConfig = None,
    ):
        self.provider = provider
        self.strategy = strategy
        self.config = config or PROVIDER_CONFIGS.get(provider, RateLimitConfig())

        # State
        self._window = RequestWindow()
        self._stats = RequestStats()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._last_request_time = 0.0
        self._backoff_multiplier = 1.0
        self._rate_limit_until = 0.0
        self._success_streak = 0
        self._failure_streak = 0

        # Learning state
        self._optimal_delay = 60.0 / self.config.requests_per_minute
        self._learned_patterns: List[Tuple[float, bool]] = []

    async def acquire(self, estimated_tokens: int = 0) -> bool:
        """
        Acquire permission to make a request.

        Args:
            estimated_tokens: Estimated tokens for this request

        Returns:
            True if request can proceed, False if rate limited
        """
        now = time.time()

        # Check if we're in a rate limit period
        if now < self._rate_limit_until:
            wait_time = self._rate_limit_until - now
            logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            now = time.time()

        # Check sliding window limits
        minute_ago = now - 60
        hour_ago = now - 3600

        requests_last_minute = self._window.count_since(minute_ago)
        requests_last_hour = self._window.count_since(hour_ago)
        tokens_last_minute = self._window.tokens_since(minute_ago)

        # Apply strategy-specific delays
        delay = await self._calculate_delay(
            requests_last_minute,
            requests_last_hour,
            tokens_last_minute,
            estimated_tokens,
        )

        if delay > 0:
            logger.debug(f"Applying {self.strategy.value} delay: {delay:.2f}s")
            await asyncio.sleep(delay)

        # Acquire semaphore for concurrency control
        await self._semaphore.acquire()

        # Record request
        self._window.add(time.time(), estimated_tokens)
        self._last_request_time = time.time()
        self._stats.total_requests += 1
        self._stats.tokens_used += estimated_tokens

        return True

    def release(self, success: bool = True, retry_after: float = None) -> None:
        """
        Release the rate limiter after request completion.

        Args:
            success: Whether the request was successful
            retry_after: Server-specified retry delay (if rate limited)
        """
        self._semaphore.release()

        if success:
            self._stats.successful_requests += 1
            self._success_streak += 1
            self._failure_streak = 0

            # Decrease backoff on success
            if self._backoff_multiplier > 1.0:
                self._backoff_multiplier = max(1.0, self._backoff_multiplier * 0.8)

            # Learn from success
            self._learned_patterns.append((time.time() - self._last_request_time, True))

        else:
            self._stats.rate_limited_requests += 1
            self._success_streak = 0
            self._failure_streak += 1

            # Increase backoff on failure
            self._backoff_multiplier = min(10.0, self._backoff_multiplier * 2)

            # Set rate limit period
            if retry_after:
                self._rate_limit_until = time.time() + retry_after
            else:
                # Default exponential backoff
                backoff = self.config.retry_after_seconds * self._backoff_multiplier
                self._rate_limit_until = time.time() + backoff

            # Learn from failure
            self._learned_patterns.append((time.time() - self._last_request_time, False))

        # Update learned optimal delay
        self._update_optimal_delay()

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        estimated_tokens: int = 0,
        **kwargs,
    ) -> Any:
        """
        Execute function with automatic retry on rate limit.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            estimated_tokens: Estimated tokens for this request
            **kwargs: Keyword arguments for func

        Returns:
            Result of func
        """
        for attempt in range(self.config.max_retries):
            await self.acquire(estimated_tokens)

            try:
                start = time.time()
                result = await func(*args, **kwargs)
                latency = time.time() - start

                # Update latency stats
                self._stats.average_latency = (
                    self._stats.average_latency * 0.9 + latency * 0.1
                )

                self.release(success=True)
                return result

            except Exception as e:
                # Check if it's a rate limit error
                retry_after = self._extract_retry_after(e)

                if retry_after is not None or self._is_rate_limit_error(e):
                    self.release(success=False, retry_after=retry_after)

                    if attempt < self.config.max_retries - 1:
                        logger.warning(f"Rate limited, attempt {attempt + 1}/{self.config.max_retries}")
                        continue
                    else:
                        raise
                else:
                    self.release(success=True)  # Non-rate-limit error
                    raise

        raise Exception(f"Max retries ({self.config.max_retries}) exceeded")

    async def _calculate_delay(
        self,
        requests_last_minute: int,
        requests_last_hour: int,
        tokens_last_minute: int,
        estimated_tokens: int,
    ) -> float:
        """Calculate delay based on strategy."""

        if self.strategy == RateLimitStrategy.FIXED_DELAY:
            return self._optimal_delay

        elif self.strategy == RateLimitStrategy.EXPONENTIAL_BACKOFF:
            return self._optimal_delay * self._backoff_multiplier

        elif self.strategy == RateLimitStrategy.ADAPTIVE:
            # Adapt based on current usage
            minute_usage = requests_last_minute / self.config.requests_per_minute
            hour_usage = requests_last_hour / self.config.requests_per_hour
            token_usage = tokens_last_minute / self.config.tokens_per_minute

            max_usage = max(minute_usage, hour_usage, token_usage)

            if max_usage > 0.9:
                return self._optimal_delay * 3  # Slow down significantly
            elif max_usage > 0.7:
                return self._optimal_delay * 1.5
            elif max_usage < 0.3:
                return self._optimal_delay * 0.5  # Speed up
            else:
                return self._optimal_delay

        elif self.strategy == RateLimitStrategy.PREDICTIVE:
            # Predict based on patterns
            if len(self._learned_patterns) > 10:
                recent = self._learned_patterns[-10:]
                failure_rate = sum(1 for _, success in recent if not success) / 10

                if failure_rate > 0.3:
                    return self._optimal_delay * 2
                elif failure_rate > 0.1:
                    return self._optimal_delay * 1.3

            return self._optimal_delay

        elif self.strategy == RateLimitStrategy.BURST:
            # Allow bursts, then recover
            if requests_last_minute < self.config.requests_per_minute * 0.5:
                return 0  # Burst mode
            else:
                # Recovery mode
                return self._optimal_delay * 2

        elif self.strategy == RateLimitStrategy.JITTER:
            # Add random jitter
            base_delay = self._optimal_delay
            jitter = random.uniform(*self.config.jitter_range)
            return base_delay + jitter

        elif self.strategy == RateLimitStrategy.DISTRIBUTED:
            # Distribute evenly across time
            minute_remaining = 60 - (time.time() % 60)
            requests_remaining = self.config.requests_per_minute - requests_last_minute

            if requests_remaining > 0:
                return minute_remaining / requests_remaining
            else:
                return 60  # Wait for new minute

        else:
            return self._optimal_delay

    def _update_optimal_delay(self) -> None:
        """Update optimal delay based on learned patterns."""
        if len(self._learned_patterns) < 5:
            return

        # Find successful patterns
        successful = [(delay, success) for delay, success in self._learned_patterns[-50:] if success]

        if successful:
            # Average delay of successful requests
            avg_successful_delay = sum(d for d, _ in successful) / len(successful)

            # Blend with current optimal
            self._optimal_delay = self._optimal_delay * 0.7 + avg_successful_delay * 0.3

            # Clamp to reasonable range
            min_delay = 60.0 / self.config.requests_per_minute / 2
            max_delay = 60.0 / self.config.requests_per_minute * 3
            self._optimal_delay = max(min_delay, min(max_delay, self._optimal_delay))

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error."""
        error_str = str(error).lower()
        rate_limit_indicators = [
            "rate limit",
            "ratelimit",
            "too many requests",
            "429",
            "quota exceeded",
            "throttl",
        ]
        return any(ind in error_str for ind in rate_limit_indicators)

    def _extract_retry_after(self, error: Exception) -> Optional[float]:
        """Extract retry-after from error if present."""
        error_str = str(error)

        # Try to find retry-after value
        import re
        match = re.search(r'retry[- ]?after[:\s]+(\d+(?:\.\d+)?)', error_str, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Check for common patterns
        match = re.search(r'(\d+(?:\.\d+)?)\s*seconds?', error_str, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return None

    def get_stats(self) -> RequestStats:
        """Get request statistics."""
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        now = time.time()
        return {
            "provider": self.provider.value,
            "strategy": self.strategy.value,
            "optimal_delay": self._optimal_delay,
            "backoff_multiplier": self._backoff_multiplier,
            "success_streak": self._success_streak,
            "failure_streak": self._failure_streak,
            "rate_limited": now < self._rate_limit_until,
            "rate_limit_remaining": max(0, self._rate_limit_until - now),
            "requests_last_minute": self._window.count_since(now - 60),
            "requests_last_hour": self._window.count_since(now - 3600),
            "stats": {
                "total": self._stats.total_requests,
                "successful": self._stats.successful_requests,
                "rate_limited": self._stats.rate_limited_requests,
                "tokens_used": self._stats.tokens_used,
            },
        }


class MultiProviderRateLimiter:
    """
    Rate limiter for multiple API providers.

    Distributes requests across providers intelligently.
    """

    def __init__(self):
        self._limiters: Dict[ProviderType, AdaptiveRateLimiter] = {}

    def add_provider(
        self,
        provider: ProviderType,
        strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE,
        config: RateLimitConfig = None,
    ) -> None:
        """Add a provider to manage."""
        self._limiters[provider] = AdaptiveRateLimiter(provider, strategy, config)

    def get_best_provider(self) -> ProviderType:
        """Get the provider with most availability."""
        best = None
        best_score = -1

        for provider, limiter in self._limiters.items():
            status = limiter.get_status()

            if status["rate_limited"]:
                continue

            # Score based on success rate and availability
            stats = status["stats"]
            if stats["total"] > 0:
                success_rate = stats["successful"] / stats["total"]
            else:
                success_rate = 1.0

            usage = status["requests_last_minute"] / limiter.config.requests_per_minute
            availability = 1 - usage

            score = success_rate * 0.5 + availability * 0.5

            if score > best_score:
                best_score = score
                best = provider

        return best or list(self._limiters.keys())[0]

    async def acquire(self, provider: ProviderType = None, **kwargs) -> Tuple[ProviderType, bool]:
        """Acquire permission for best available provider."""
        if provider is None:
            provider = self.get_best_provider()

        limiter = self._limiters.get(provider)
        if limiter:
            success = await limiter.acquire(**kwargs)
            return provider, success

        return provider, True

    def release(self, provider: ProviderType, **kwargs) -> None:
        """Release limiter for provider."""
        limiter = self._limiters.get(provider)
        if limiter:
            limiter.release(**kwargs)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_limiter: Optional[AdaptiveRateLimiter] = None

def get_limiter(provider: ProviderType = ProviderType.OPENROUTER) -> AdaptiveRateLimiter:
    """Get or create default rate limiter."""
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = AdaptiveRateLimiter(provider)
    return _default_limiter


async def rate_limited_request(func: Callable, *args, **kwargs) -> Any:
    """Execute function with rate limiting."""
    limiter = get_limiter()
    return await limiter.execute_with_retry(func, *args, **kwargs)
