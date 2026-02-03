#!/usr/bin/env python3
"""
BAEL - Rate Limiter
Advanced rate limiting and throttling system.

This module provides comprehensive rate limiting capabilities
for protecting resources and ensuring fair usage.

Features:
- Multiple rate limiting algorithms
- Sliding window rate limiting
- Token bucket algorithm
- Leaky bucket algorithm
- Fixed window counter
- Distributed rate limiting support
- Rate limit by key (user, IP, API key)
- Adaptive rate limiting
- Rate limit quotas
- Penalty and cooldown systems
"""

import asyncio
import hashlib
import logging
import math
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from heapq import heappop, heappush
from typing import (Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar,
                    Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    SLIDING_LOG = "sliding_log"


class RateLimitResult(Enum):
    """Rate limit check result."""
    ALLOWED = "allowed"
    DENIED = "denied"
    WARNING = "warning"
    THROTTLED = "throttled"


class KeyType(Enum):
    """Rate limit key types."""
    IP = "ip"
    USER = "user"
    API_KEY = "api_key"
    ENDPOINT = "endpoint"
    GLOBAL = "global"
    CUSTOM = "custom"


class QuotaType(Enum):
    """Quota types."""
    REQUESTS = "requests"
    DATA_TRANSFER = "data_transfer"
    OPERATIONS = "operations"
    TOKENS = "tokens"


class PenaltyType(Enum):
    """Penalty types."""
    NONE = "none"
    WARNING = "warning"
    SLOWDOWN = "slowdown"
    TEMPORARY_BAN = "temporary_ban"
    PERMANENT_BAN = "permanent_ban"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests: int = 100
    window_seconds: float = 60.0
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    burst_size: Optional[int] = None
    penalty_multiplier: float = 1.5
    cooldown_seconds: float = 60.0
    warning_threshold: float = 0.8


@dataclass
class RateLimitState:
    """Rate limit state for a key."""
    key: str
    requests: int = 0
    tokens: float = 0.0
    window_start: float = 0.0
    last_request: float = 0.0
    violations: int = 0
    penalty_until: Optional[float] = None
    request_times: List[float] = field(default_factory=list)


@dataclass
class RateLimitResponse:
    """Rate limit check response."""
    result: RateLimitResult
    key: str
    remaining: int = 0
    reset_at: float = 0.0
    retry_after: float = 0.0
    limit: int = 0
    window: float = 0.0
    warning: bool = False
    message: str = ""


@dataclass
class Quota:
    """Usage quota."""
    quota_type: QuotaType
    limit: int
    used: int = 0
    period_start: datetime = field(default_factory=datetime.now)
    period_seconds: float = 86400  # 1 day

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def percentage_used(self) -> float:
        if self.limit == 0:
            return 100.0
        return (self.used / self.limit) * 100

    def is_exceeded(self) -> bool:
        return self.used >= self.limit

    def reset_if_expired(self) -> bool:
        if datetime.now() > self.period_start + timedelta(seconds=self.period_seconds):
            self.used = 0
            self.period_start = datetime.now()
            return True
        return False


@dataclass
class ViolationRecord:
    """Violation record."""
    key: str
    timestamp: datetime
    violation_type: str
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# RATE LIMITING ALGORITHMS
# =============================================================================

class RateLimiter(ABC):
    """Abstract rate limiter."""

    @abstractmethod
    async def check(self, key: str) -> RateLimitResponse:
        """Check if request is allowed."""
        pass

    @abstractmethod
    async def record(self, key: str, count: int = 1) -> None:
        """Record a request."""
        pass

    @abstractmethod
    async def get_state(self, key: str) -> Optional[RateLimitState]:
        """Get current state for key."""
        pass

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset rate limit for key."""
        pass


class FixedWindowLimiter(RateLimiter):
    """Fixed window rate limiter."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.states: Dict[str, RateLimitState] = {}

    async def check(self, key: str) -> RateLimitResponse:
        now = time.time()
        state = await self._get_or_create_state(key)

        # Check window expiration
        if now - state.window_start >= self.config.window_seconds:
            state.requests = 0
            state.window_start = now

        remaining = self.config.requests - state.requests
        reset_at = state.window_start + self.config.window_seconds

        if state.requests >= self.config.requests:
            return RateLimitResponse(
                result=RateLimitResult.DENIED,
                key=key,
                remaining=0,
                reset_at=reset_at,
                retry_after=reset_at - now,
                limit=self.config.requests,
                window=self.config.window_seconds,
                message="Rate limit exceeded"
            )

        warning = remaining <= int(self.config.requests * (1 - self.config.warning_threshold))

        return RateLimitResponse(
            result=RateLimitResult.ALLOWED,
            key=key,
            remaining=remaining,
            reset_at=reset_at,
            limit=self.config.requests,
            window=self.config.window_seconds,
            warning=warning
        )

    async def record(self, key: str, count: int = 1) -> None:
        state = await self._get_or_create_state(key)
        state.requests += count
        state.last_request = time.time()

    async def get_state(self, key: str) -> Optional[RateLimitState]:
        return self.states.get(key)

    async def reset(self, key: str) -> None:
        if key in self.states:
            del self.states[key]

    async def _get_or_create_state(self, key: str) -> RateLimitState:
        if key not in self.states:
            self.states[key] = RateLimitState(
                key=key,
                window_start=time.time()
            )
        return self.states[key]


class SlidingWindowLimiter(RateLimiter):
    """Sliding window rate limiter."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.states: Dict[str, RateLimitState] = {}

    async def check(self, key: str) -> RateLimitResponse:
        now = time.time()
        state = await self._get_or_create_state(key)

        # Remove old requests
        cutoff = now - self.config.window_seconds
        state.request_times = [t for t in state.request_times if t > cutoff]

        current_count = len(state.request_times)
        remaining = self.config.requests - current_count

        # Estimate reset time
        if state.request_times:
            reset_at = state.request_times[0] + self.config.window_seconds
        else:
            reset_at = now + self.config.window_seconds

        if current_count >= self.config.requests:
            return RateLimitResponse(
                result=RateLimitResult.DENIED,
                key=key,
                remaining=0,
                reset_at=reset_at,
                retry_after=reset_at - now if reset_at > now else 0,
                limit=self.config.requests,
                window=self.config.window_seconds,
                message="Rate limit exceeded"
            )

        warning = remaining <= int(self.config.requests * (1 - self.config.warning_threshold))

        return RateLimitResponse(
            result=RateLimitResult.ALLOWED,
            key=key,
            remaining=remaining,
            reset_at=reset_at,
            limit=self.config.requests,
            window=self.config.window_seconds,
            warning=warning
        )

    async def record(self, key: str, count: int = 1) -> None:
        state = await self._get_or_create_state(key)
        now = time.time()
        for _ in range(count):
            state.request_times.append(now)
        state.last_request = now

    async def get_state(self, key: str) -> Optional[RateLimitState]:
        return self.states.get(key)

    async def reset(self, key: str) -> None:
        if key in self.states:
            del self.states[key]

    async def _get_or_create_state(self, key: str) -> RateLimitState:
        if key not in self.states:
            self.states[key] = RateLimitState(key=key)
        return self.states[key]


class TokenBucketLimiter(RateLimiter):
    """Token bucket rate limiter."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.bucket_size = config.burst_size or config.requests
        self.refill_rate = config.requests / config.window_seconds
        self.states: Dict[str, RateLimitState] = {}

    async def check(self, key: str) -> RateLimitResponse:
        now = time.time()
        state = await self._get_or_create_state(key)

        # Refill tokens
        elapsed = now - state.last_request
        refill = elapsed * self.refill_rate
        state.tokens = min(self.bucket_size, state.tokens + refill)
        state.last_request = now

        if state.tokens < 1:
            # Calculate when we'll have a token
            wait_time = (1 - state.tokens) / self.refill_rate

            return RateLimitResponse(
                result=RateLimitResult.DENIED,
                key=key,
                remaining=0,
                retry_after=wait_time,
                limit=self.bucket_size,
                window=self.config.window_seconds,
                message="Rate limit exceeded (no tokens available)"
            )

        remaining = int(state.tokens)
        warning = remaining <= int(self.bucket_size * (1 - self.config.warning_threshold))

        return RateLimitResponse(
            result=RateLimitResult.ALLOWED,
            key=key,
            remaining=remaining,
            limit=self.bucket_size,
            window=self.config.window_seconds,
            warning=warning
        )

    async def record(self, key: str, count: int = 1) -> None:
        state = await self._get_or_create_state(key)
        state.tokens = max(0, state.tokens - count)

    async def get_state(self, key: str) -> Optional[RateLimitState]:
        return self.states.get(key)

    async def reset(self, key: str) -> None:
        if key in self.states:
            del self.states[key]

    async def _get_or_create_state(self, key: str) -> RateLimitState:
        if key not in self.states:
            self.states[key] = RateLimitState(
                key=key,
                tokens=self.bucket_size,
                last_request=time.time()
            )
        return self.states[key]


class LeakyBucketLimiter(RateLimiter):
    """Leaky bucket rate limiter (smooths out bursts)."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.bucket_size = config.burst_size or config.requests
        self.leak_rate = config.requests / config.window_seconds
        self.states: Dict[str, RateLimitState] = {}
        self.queues: Dict[str, List[float]] = defaultdict(list)

    async def check(self, key: str) -> RateLimitResponse:
        now = time.time()
        state = await self._get_or_create_state(key)

        # Leak water
        elapsed = now - state.last_request
        leaked = elapsed * self.leak_rate
        state.tokens = max(0, state.tokens - leaked)
        state.last_request = now

        if state.tokens >= self.bucket_size:
            wait_time = (state.tokens - self.bucket_size + 1) / self.leak_rate

            return RateLimitResponse(
                result=RateLimitResult.DENIED,
                key=key,
                remaining=0,
                retry_after=wait_time,
                limit=self.bucket_size,
                window=self.config.window_seconds,
                message="Rate limit exceeded (bucket full)"
            )

        remaining = int(self.bucket_size - state.tokens)
        warning = remaining <= int(self.bucket_size * (1 - self.config.warning_threshold))

        return RateLimitResponse(
            result=RateLimitResult.ALLOWED,
            key=key,
            remaining=remaining,
            limit=self.bucket_size,
            window=self.config.window_seconds,
            warning=warning
        )

    async def record(self, key: str, count: int = 1) -> None:
        state = await self._get_or_create_state(key)
        state.tokens += count

    async def get_state(self, key: str) -> Optional[RateLimitState]:
        return self.states.get(key)

    async def reset(self, key: str) -> None:
        if key in self.states:
            del self.states[key]

    async def _get_or_create_state(self, key: str) -> RateLimitState:
        if key not in self.states:
            self.states[key] = RateLimitState(
                key=key,
                tokens=0,
                last_request=time.time()
            )
        return self.states[key]


# =============================================================================
# ADAPTIVE RATE LIMITER
# =============================================================================

class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts limits based on behavior.
    """

    def __init__(
        self,
        base_config: RateLimitConfig,
        min_multiplier: float = 0.1,
        max_multiplier: float = 2.0
    ):
        self.base_config = base_config
        self.min_multiplier = min_multiplier
        self.max_multiplier = max_multiplier

        self.multipliers: Dict[str, float] = defaultdict(lambda: 1.0)
        self.trust_scores: Dict[str, float] = defaultdict(lambda: 0.5)
        self.violation_history: Dict[str, List[ViolationRecord]] = defaultdict(list)

        self.base_limiter = self._create_limiter(base_config)

    def _create_limiter(self, config: RateLimitConfig) -> RateLimiter:
        """Create limiter based on algorithm."""
        if config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return FixedWindowLimiter(config)
        elif config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return SlidingWindowLimiter(config)
        elif config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return TokenBucketLimiter(config)
        elif config.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
            return LeakyBucketLimiter(config)
        else:
            return SlidingWindowLimiter(config)

    def get_effective_limit(self, key: str) -> int:
        """Get effective rate limit for a key."""
        multiplier = self.multipliers[key]
        return int(self.base_config.requests * multiplier)

    async def check(self, key: str) -> RateLimitResponse:
        """Check rate limit with adaptive adjustment."""
        response = await self.base_limiter.check(key)

        # Adjust remaining based on multiplier
        multiplier = self.multipliers[key]
        response.remaining = int(response.remaining * multiplier)
        response.limit = self.get_effective_limit(key)

        return response

    async def record(self, key: str, count: int = 1) -> None:
        """Record request and update trust score."""
        await self.base_limiter.record(key, count)

        # Improve trust for good behavior
        self._improve_trust(key, 0.01)

    async def record_violation(
        self,
        key: str,
        violation_type: str,
        details: Dict[str, Any] = None
    ) -> None:
        """Record a violation."""
        violation = ViolationRecord(
            key=key,
            timestamp=datetime.now(),
            violation_type=violation_type,
            details=details or {}
        )

        self.violation_history[key].append(violation)

        # Trim old violations
        cutoff = datetime.now() - timedelta(hours=24)
        self.violation_history[key] = [
            v for v in self.violation_history[key]
            if v.timestamp > cutoff
        ]

        # Decrease trust
        self._decrease_trust(key, 0.1)

        # Adjust multiplier
        self._update_multiplier(key)

    def _improve_trust(self, key: str, amount: float) -> None:
        """Improve trust score."""
        self.trust_scores[key] = min(1.0, self.trust_scores[key] + amount)
        self._update_multiplier(key)

    def _decrease_trust(self, key: str, amount: float) -> None:
        """Decrease trust score."""
        self.trust_scores[key] = max(0.0, self.trust_scores[key] - amount)

    def _update_multiplier(self, key: str) -> None:
        """Update rate limit multiplier based on trust."""
        trust = self.trust_scores[key]
        violations = len(self.violation_history[key])

        # Calculate multiplier
        base_mult = self.min_multiplier + (self.max_multiplier - self.min_multiplier) * trust

        # Penalty for recent violations
        penalty = 1.0 / (1 + violations * 0.2)

        self.multipliers[key] = base_mult * penalty

    def get_trust_score(self, key: str) -> float:
        """Get trust score for a key."""
        return self.trust_scores[key]

    def get_violation_count(self, key: str) -> int:
        """Get violation count for a key."""
        return len(self.violation_history[key])


# =============================================================================
# QUOTA MANAGER
# =============================================================================

class QuotaManager:
    """Manages usage quotas."""

    def __init__(self):
        self.quotas: Dict[str, Dict[QuotaType, Quota]] = defaultdict(dict)

    def set_quota(
        self,
        key: str,
        quota_type: QuotaType,
        limit: int,
        period_seconds: float = 86400
    ) -> Quota:
        """Set a quota for a key."""
        quota = Quota(
            quota_type=quota_type,
            limit=limit,
            period_seconds=period_seconds
        )
        self.quotas[key][quota_type] = quota
        return quota

    def check_quota(
        self,
        key: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> Tuple[bool, Quota]:
        """Check if quota allows the request."""
        if key not in self.quotas or quota_type not in self.quotas[key]:
            return True, None

        quota = self.quotas[key][quota_type]
        quota.reset_if_expired()

        return quota.remaining >= amount, quota

    def consume_quota(
        self,
        key: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> bool:
        """Consume quota."""
        allowed, quota = self.check_quota(key, quota_type, amount)

        if allowed and quota:
            quota.used += amount
            return True

        return allowed

    def get_quota(
        self,
        key: str,
        quota_type: QuotaType
    ) -> Optional[Quota]:
        """Get quota for a key."""
        return self.quotas.get(key, {}).get(quota_type)

    def get_all_quotas(self, key: str) -> Dict[QuotaType, Quota]:
        """Get all quotas for a key."""
        return dict(self.quotas.get(key, {}))

    def reset_quota(self, key: str, quota_type: QuotaType) -> bool:
        """Reset a quota."""
        if key in self.quotas and quota_type in self.quotas[key]:
            self.quotas[key][quota_type].used = 0
            self.quotas[key][quota_type].period_start = datetime.now()
            return True
        return False


# =============================================================================
# PENALTY MANAGER
# =============================================================================

class PenaltyManager:
    """Manages penalties for rate limit violations."""

    def __init__(self):
        self.penalties: Dict[str, Tuple[PenaltyType, float]] = {}
        self.violation_counts: Dict[str, int] = defaultdict(int)

        # Penalty thresholds
        self.thresholds = {
            3: PenaltyType.WARNING,
            5: PenaltyType.SLOWDOWN,
            10: PenaltyType.TEMPORARY_BAN,
            20: PenaltyType.PERMANENT_BAN
        }

        # Penalty durations
        self.durations = {
            PenaltyType.WARNING: 0,
            PenaltyType.SLOWDOWN: 300,  # 5 minutes
            PenaltyType.TEMPORARY_BAN: 3600,  # 1 hour
            PenaltyType.PERMANENT_BAN: float('inf')
        }

    def record_violation(self, key: str) -> PenaltyType:
        """Record a violation and determine penalty."""
        self.violation_counts[key] += 1
        count = self.violation_counts[key]

        # Determine penalty level
        penalty_type = PenaltyType.NONE
        for threshold, ptype in sorted(self.thresholds.items()):
            if count >= threshold:
                penalty_type = ptype

        # Apply penalty
        if penalty_type != PenaltyType.NONE:
            duration = self.durations[penalty_type]
            if duration == float('inf'):
                expires = float('inf')
            else:
                expires = time.time() + duration

            self.penalties[key] = (penalty_type, expires)

        return penalty_type

    def check_penalty(self, key: str) -> Tuple[bool, PenaltyType, float]:
        """Check if key is under penalty."""
        if key not in self.penalties:
            return False, PenaltyType.NONE, 0

        penalty_type, expires = self.penalties[key]
        now = time.time()

        if expires != float('inf') and now > expires:
            # Penalty expired
            del self.penalties[key]
            return False, PenaltyType.NONE, 0

        remaining = expires - now if expires != float('inf') else float('inf')
        return True, penalty_type, remaining

    def clear_penalty(self, key: str) -> bool:
        """Clear penalty for a key."""
        if key in self.penalties:
            del self.penalties[key]
            self.violation_counts[key] = 0
            return True
        return False

    def get_violation_count(self, key: str) -> int:
        """Get violation count."""
        return self.violation_counts[key]


# =============================================================================
# RATE LIMIT MANAGER
# =============================================================================

class RateLimitManager:
    """
    Master rate limiting manager for BAEL.

    Provides comprehensive rate limiting with multiple
    algorithms, quotas, and penalty management.
    """

    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
        self.adaptive_limiters: Dict[str, AdaptiveRateLimiter] = {}
        self.quota_manager = QuotaManager()
        self.penalty_manager = PenaltyManager()

        # Default configurations
        self.default_configs: Dict[str, RateLimitConfig] = {}

        # Statistics
        self.total_requests = 0
        self.denied_requests = 0

    def create_limiter(
        self,
        name: str,
        config: RateLimitConfig,
        adaptive: bool = False
    ) -> Union[RateLimiter, AdaptiveRateLimiter]:
        """Create a rate limiter."""
        if adaptive:
            limiter = AdaptiveRateLimiter(config)
            self.adaptive_limiters[name] = limiter
        else:
            if config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                limiter = FixedWindowLimiter(config)
            elif config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                limiter = SlidingWindowLimiter(config)
            elif config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                limiter = TokenBucketLimiter(config)
            elif config.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
                limiter = LeakyBucketLimiter(config)
            else:
                limiter = SlidingWindowLimiter(config)

            self.limiters[name] = limiter

        self.default_configs[name] = config
        return limiter

    async def check_and_record(
        self,
        limiter_name: str,
        key: str,
        count: int = 1
    ) -> RateLimitResponse:
        """Check rate limit and record if allowed."""
        self.total_requests += 1

        # Check penalty first
        under_penalty, penalty_type, remaining = self.penalty_manager.check_penalty(key)

        if under_penalty:
            if penalty_type == PenaltyType.PERMANENT_BAN:
                self.denied_requests += 1
                return RateLimitResponse(
                    result=RateLimitResult.DENIED,
                    key=key,
                    message="Permanently banned"
                )
            elif penalty_type == PenaltyType.TEMPORARY_BAN:
                self.denied_requests += 1
                return RateLimitResponse(
                    result=RateLimitResult.DENIED,
                    key=key,
                    retry_after=remaining,
                    message=f"Temporarily banned for {remaining:.0f} seconds"
                )
            elif penalty_type == PenaltyType.SLOWDOWN:
                # Add artificial delay
                await asyncio.sleep(min(remaining / 10, 5))

        # Check limiter
        limiter = self.limiters.get(limiter_name) or self.adaptive_limiters.get(limiter_name)

        if not limiter:
            return RateLimitResponse(
                result=RateLimitResult.ALLOWED,
                key=key,
                message="No limiter configured"
            )

        response = await limiter.check(key)

        if response.result == RateLimitResult.ALLOWED:
            await limiter.record(key, count)
        else:
            self.denied_requests += 1
            # Record violation
            penalty = self.penalty_manager.record_violation(key)
            if penalty != PenaltyType.NONE:
                response.message += f" (Penalty: {penalty.value})"

        return response

    async def check_quota_and_consume(
        self,
        key: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> Tuple[bool, Optional[Quota]]:
        """Check and consume quota."""
        allowed, quota = self.quota_manager.check_quota(key, quota_type, amount)

        if allowed:
            self.quota_manager.consume_quota(key, quota_type, amount)

        return allowed, quota

    def set_quota(
        self,
        key: str,
        quota_type: QuotaType,
        limit: int,
        period_seconds: float = 86400
    ) -> Quota:
        """Set a quota."""
        return self.quota_manager.set_quota(key, quota_type, limit, period_seconds)

    async def reset(self, limiter_name: str, key: str) -> None:
        """Reset rate limit for a key."""
        limiter = self.limiters.get(limiter_name) or self.adaptive_limiters.get(limiter_name)

        if limiter:
            await limiter.reset(key)

    def clear_penalty(self, key: str) -> bool:
        """Clear penalty for a key."""
        return self.penalty_manager.clear_penalty(key)

    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        return {
            "total_requests": self.total_requests,
            "denied_requests": self.denied_requests,
            "denial_rate": self.denied_requests / max(1, self.total_requests) * 100,
            "active_limiters": len(self.limiters),
            "adaptive_limiters": len(self.adaptive_limiters)
        }

    def get_limiter_names(self) -> List[str]:
        """Get all limiter names."""
        return list(set(self.limiters.keys()) | set(self.adaptive_limiters.keys()))


# =============================================================================
# RATE LIMIT DECORATOR
# =============================================================================

def rate_limit(
    manager: RateLimitManager,
    limiter_name: str,
    key_func: Callable[..., str] = None,
    on_exceeded: Callable = None
):
    """Decorator for rate limiting functions."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs) if key_func else "default"
            response = await manager.check_and_record(limiter_name, key)

            if response.result != RateLimitResult.ALLOWED:
                if on_exceeded:
                    return on_exceeded(response)
                raise Exception(f"Rate limit exceeded: {response.message}")

            return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs) if key_func else "default"
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(manager.check_and_record(limiter_name, key))

            if response.result != RateLimitResult.ALLOWED:
                if on_exceeded:
                    return on_exceeded(response)
                raise Exception(f"Rate limit exceeded: {response.message}")

            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Rate Limiter."""
    print("=" * 70)
    print("BAEL - RATE LIMITER DEMO")
    print("Advanced Rate Limiting System")
    print("=" * 70)
    print()

    manager = RateLimitManager()

    # 1. Fixed Window Limiter
    print("1. FIXED WINDOW RATE LIMITING:")
    print("-" * 40)

    manager.create_limiter("fixed", RateLimitConfig(
        requests=5,
        window_seconds=10,
        algorithm=RateLimitAlgorithm.FIXED_WINDOW
    ))

    for i in range(7):
        response = await manager.check_and_record("fixed", "user_001")
        status = "✓" if response.result == RateLimitResult.ALLOWED else "✗"
        print(f"   Request {i + 1}: {status} - Remaining: {response.remaining}")
    print()

    # 2. Sliding Window Limiter
    print("2. SLIDING WINDOW RATE LIMITING:")
    print("-" * 40)

    manager.create_limiter("sliding", RateLimitConfig(
        requests=3,
        window_seconds=5,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))

    for i in range(5):
        response = await manager.check_and_record("sliding", "user_002")
        status = "✓" if response.result == RateLimitResult.ALLOWED else "✗"
        print(f"   Request {i + 1}: {status} - Remaining: {response.remaining}")
    print()

    # 3. Token Bucket Limiter
    print("3. TOKEN BUCKET RATE LIMITING:")
    print("-" * 40)

    manager.create_limiter("bucket", RateLimitConfig(
        requests=10,
        window_seconds=1,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        burst_size=5
    ))

    print("   Burst of 5 requests:")
    for i in range(6):
        response = await manager.check_and_record("bucket", "user_003")
        status = "✓" if response.result == RateLimitResult.ALLOWED else "✗"
        print(f"   Request {i + 1}: {status} - Remaining: {response.remaining}")

    print("   Waiting 1 second for token refill...")
    await asyncio.sleep(1)

    response = await manager.check_and_record("bucket", "user_003")
    status = "✓" if response.result == RateLimitResult.ALLOWED else "✗"
    print(f"   After wait: {status} - Remaining: {response.remaining}")
    print()

    # 4. Adaptive Rate Limiting
    print("4. ADAPTIVE RATE LIMITING:")
    print("-" * 40)

    manager.create_limiter("adaptive", RateLimitConfig(
        requests=10,
        window_seconds=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ), adaptive=True)

    adaptive = manager.adaptive_limiters["adaptive"]

    print(f"   Initial trust score: {adaptive.get_trust_score('user_004'):.2f}")
    print(f"   Initial limit: {adaptive.get_effective_limit('user_004')}")

    # Record some violations
    await adaptive.record_violation("user_004", "abuse", {"type": "spam"})
    await adaptive.record_violation("user_004", "abuse", {"type": "spam"})

    print(f"   After violations - Trust: {adaptive.get_trust_score('user_004'):.2f}")
    print(f"   After violations - Limit: {adaptive.get_effective_limit('user_004')}")
    print()

    # 5. Quota Management
    print("5. QUOTA MANAGEMENT:")
    print("-" * 40)

    manager.set_quota("user_005", QuotaType.REQUESTS, 1000, 86400)
    manager.set_quota("user_005", QuotaType.DATA_TRANSFER, 10000000, 86400)  # 10MB

    quotas = manager.quota_manager.get_all_quotas("user_005")
    for qtype, quota in quotas.items():
        print(f"   {qtype.value}: {quota.used}/{quota.limit} ({quota.percentage_used:.1f}%)")

    # Consume some quota
    for _ in range(100):
        manager.quota_manager.consume_quota("user_005", QuotaType.REQUESTS)

    quota = manager.quota_manager.get_quota("user_005", QuotaType.REQUESTS)
    print(f"   After 100 requests: {quota.used}/{quota.limit}")
    print()

    # 6. Penalty System
    print("6. PENALTY SYSTEM:")
    print("-" * 40)

    for i in range(5):
        penalty = manager.penalty_manager.record_violation("bad_user")
        print(f"   Violation {i + 1}: Penalty = {penalty.value}")

    under_penalty, ptype, remaining = manager.penalty_manager.check_penalty("bad_user")
    print(f"   Under penalty: {under_penalty}")
    print(f"   Penalty type: {ptype.value}")
    print(f"   Remaining: {remaining:.1f} seconds")

    # Clear penalty
    manager.penalty_manager.clear_penalty("bad_user")
    print("   Penalty cleared")
    print()

    # 7. Statistics
    print("7. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 8. Limiter List
    print("8. CONFIGURED LIMITERS:")
    print("-" * 40)

    for name in manager.get_limiter_names():
        config = manager.default_configs.get(name)
        if config:
            print(f"   {name}: {config.requests} req/{config.window_seconds}s ({config.algorithm.value})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Rate Limiter Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
