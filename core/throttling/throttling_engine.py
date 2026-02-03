#!/usr/bin/env python3
"""
BAEL - Throttling Engine
Rate limiting and throttling for agents.

Features:
- Token bucket algorithm
- Sliding window limiting
- Fixed window limiting
- Leaky bucket algorithm
- Quota management
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, Iterator, List, Optional, Set, Tuple,
    Type, TypeVar, Union
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ThrottleAlgorithm(Enum):
    """Throttling algorithms."""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    SLIDING_LOG = "sliding_log"


class ThrottleResult(Enum):
    """Throttle check results."""
    ALLOWED = "allowed"
    DENIED = "denied"
    LIMITED = "limited"
    QUEUED = "queued"


class QuotaType(Enum):
    """Quota types."""
    REQUESTS = "requests"
    BANDWIDTH = "bandwidth"
    TOKENS = "tokens"
    COST = "cost"
    CUSTOM = "custom"


class QuotaPeriod(Enum):
    """Quota periods."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ThrottleConfig:
    """Throttle configuration."""
    algorithm: ThrottleAlgorithm = ThrottleAlgorithm.TOKEN_BUCKET
    rate: float = 100.0
    burst: float = 10.0
    window_seconds: float = 60.0


@dataclass
class ThrottleState:
    """Throttle state."""
    key: str = ""
    tokens: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)
    request_count: int = 0
    window_start: datetime = field(default_factory=datetime.now)
    timestamps: List[float] = field(default_factory=list)


@dataclass
class ThrottleResponse:
    """Response from throttle check."""
    result: ThrottleResult = ThrottleResult.ALLOWED
    remaining: float = 0.0
    reset_at: Optional[datetime] = None
    retry_after_seconds: float = 0.0
    limit: float = 0.0
    used: float = 0.0


@dataclass
class QuotaConfig:
    """Quota configuration."""
    quota_type: QuotaType = QuotaType.REQUESTS
    limit: float = 1000.0
    period: QuotaPeriod = QuotaPeriod.HOUR
    soft_limit: Optional[float] = None
    burst_allowance: float = 0.0


@dataclass
class QuotaUsage:
    """Quota usage tracking."""
    key: str = ""
    quota_type: QuotaType = QuotaType.REQUESTS
    used: float = 0.0
    limit: float = 0.0
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)
    
    @property
    def remaining(self) -> float:
        """Get remaining quota."""
        return max(0.0, self.limit - self.used)
    
    @property
    def usage_percent(self) -> float:
        """Get usage percentage."""
        if self.limit == 0:
            return 100.0
        return (self.used / self.limit) * 100.0


@dataclass
class ThrottlingStats:
    """Throttling statistics."""
    total_requests: int = 0
    allowed_requests: int = 0
    denied_requests: int = 0
    limited_requests: int = 0
    avg_wait_time: float = 0.0


# =============================================================================
# RATE LIMITERS
# =============================================================================

class RateLimiter(ABC):
    """Base rate limiter."""
    
    @abstractmethod
    def acquire(self, key: str, tokens: float = 1.0) -> ThrottleResponse:
        """Try to acquire tokens."""
        pass
    
    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset limiter for key."""
        pass
    
    @abstractmethod
    def get_state(self, key: str) -> Optional[ThrottleState]:
        """Get limiter state."""
        pass


class TokenBucketLimiter(RateLimiter):
    """Token bucket rate limiter."""
    
    def __init__(
        self,
        rate: float = 10.0,
        burst: float = 10.0
    ):
        self._rate = rate
        self._burst = burst
        self._buckets: Dict[str, ThrottleState] = {}
    
    def acquire(self, key: str, tokens: float = 1.0) -> ThrottleResponse:
        """Try to acquire tokens."""
        now = datetime.now()
        state = self._get_or_create(key)
        
        elapsed = (now - state.last_update).total_seconds()
        state.tokens = min(
            self._burst,
            state.tokens + elapsed * self._rate
        )
        state.last_update = now
        
        if state.tokens >= tokens:
            state.tokens -= tokens
            state.request_count += 1
            
            return ThrottleResponse(
                result=ThrottleResult.ALLOWED,
                remaining=state.tokens,
                limit=self._burst,
                used=self._burst - state.tokens
            )
        
        wait_time = (tokens - state.tokens) / self._rate
        
        return ThrottleResponse(
            result=ThrottleResult.DENIED,
            remaining=state.tokens,
            retry_after_seconds=wait_time,
            limit=self._burst,
            used=self._burst - state.tokens
        )
    
    def _get_or_create(self, key: str) -> ThrottleState:
        """Get or create bucket."""
        if key not in self._buckets:
            self._buckets[key] = ThrottleState(
                key=key,
                tokens=self._burst
            )
        return self._buckets[key]
    
    def reset(self, key: str) -> None:
        """Reset bucket."""
        if key in self._buckets:
            self._buckets[key].tokens = self._burst
            self._buckets[key].last_update = datetime.now()
    
    def get_state(self, key: str) -> Optional[ThrottleState]:
        """Get bucket state."""
        return self._buckets.get(key)


class LeakyBucketLimiter(RateLimiter):
    """Leaky bucket rate limiter."""
    
    def __init__(
        self,
        rate: float = 10.0,
        capacity: float = 100.0
    ):
        self._rate = rate
        self._capacity = capacity
        self._buckets: Dict[str, ThrottleState] = {}
    
    def acquire(self, key: str, tokens: float = 1.0) -> ThrottleResponse:
        """Try to acquire tokens."""
        now = datetime.now()
        state = self._get_or_create(key)
        
        elapsed = (now - state.last_update).total_seconds()
        leaked = elapsed * self._rate
        state.tokens = max(0, state.tokens - leaked)
        state.last_update = now
        
        if state.tokens + tokens <= self._capacity:
            state.tokens += tokens
            state.request_count += 1
            
            return ThrottleResponse(
                result=ThrottleResult.ALLOWED,
                remaining=self._capacity - state.tokens,
                limit=self._capacity,
                used=state.tokens
            )
        
        wait_time = (state.tokens + tokens - self._capacity) / self._rate
        
        return ThrottleResponse(
            result=ThrottleResult.DENIED,
            remaining=self._capacity - state.tokens,
            retry_after_seconds=wait_time,
            limit=self._capacity,
            used=state.tokens
        )
    
    def _get_or_create(self, key: str) -> ThrottleState:
        """Get or create bucket."""
        if key not in self._buckets:
            self._buckets[key] = ThrottleState(
                key=key,
                tokens=0
            )
        return self._buckets[key]
    
    def reset(self, key: str) -> None:
        """Reset bucket."""
        if key in self._buckets:
            self._buckets[key].tokens = 0
            self._buckets[key].last_update = datetime.now()
    
    def get_state(self, key: str) -> Optional[ThrottleState]:
        """Get bucket state."""
        return self._buckets.get(key)


class FixedWindowLimiter(RateLimiter):
    """Fixed window rate limiter."""
    
    def __init__(
        self,
        limit: int = 100,
        window_seconds: float = 60.0
    ):
        self._limit = limit
        self._window_seconds = window_seconds
        self._windows: Dict[str, ThrottleState] = {}
    
    def acquire(self, key: str, tokens: float = 1.0) -> ThrottleResponse:
        """Try to acquire tokens."""
        now = datetime.now()
        state = self._get_or_create(key)
        
        elapsed = (now - state.window_start).total_seconds()
        if elapsed >= self._window_seconds:
            state.window_start = now
            state.request_count = 0
        
        if state.request_count + tokens <= self._limit:
            state.request_count += int(tokens)
            
            reset_at = state.window_start + timedelta(seconds=self._window_seconds)
            
            return ThrottleResponse(
                result=ThrottleResult.ALLOWED,
                remaining=self._limit - state.request_count,
                reset_at=reset_at,
                limit=self._limit,
                used=state.request_count
            )
        
        reset_at = state.window_start + timedelta(seconds=self._window_seconds)
        wait_time = (reset_at - now).total_seconds()
        
        return ThrottleResponse(
            result=ThrottleResult.DENIED,
            remaining=0,
            reset_at=reset_at,
            retry_after_seconds=max(0, wait_time),
            limit=self._limit,
            used=state.request_count
        )
    
    def _get_or_create(self, key: str) -> ThrottleState:
        """Get or create window."""
        if key not in self._windows:
            self._windows[key] = ThrottleState(
                key=key,
                window_start=datetime.now()
            )
        return self._windows[key]
    
    def reset(self, key: str) -> None:
        """Reset window."""
        if key in self._windows:
            self._windows[key].window_start = datetime.now()
            self._windows[key].request_count = 0
    
    def get_state(self, key: str) -> Optional[ThrottleState]:
        """Get window state."""
        return self._windows.get(key)


class SlidingWindowLimiter(RateLimiter):
    """Sliding window rate limiter."""
    
    def __init__(
        self,
        limit: int = 100,
        window_seconds: float = 60.0
    ):
        self._limit = limit
        self._window_seconds = window_seconds
        self._states: Dict[str, ThrottleState] = {}
    
    def acquire(self, key: str, tokens: float = 1.0) -> ThrottleResponse:
        """Try to acquire tokens."""
        now = time.time()
        state = self._get_or_create(key)
        
        cutoff = now - self._window_seconds
        state.timestamps = [t for t in state.timestamps if t > cutoff]
        
        current_count = len(state.timestamps)
        
        if current_count + tokens <= self._limit:
            for _ in range(int(tokens)):
                state.timestamps.append(now)
            state.request_count += int(tokens)
            
            return ThrottleResponse(
                result=ThrottleResult.ALLOWED,
                remaining=self._limit - len(state.timestamps),
                limit=self._limit,
                used=len(state.timestamps)
            )
        
        if state.timestamps:
            oldest = min(state.timestamps)
            wait_time = oldest + self._window_seconds - now
        else:
            wait_time = 0
        
        return ThrottleResponse(
            result=ThrottleResult.DENIED,
            remaining=0,
            retry_after_seconds=max(0, wait_time),
            limit=self._limit,
            used=len(state.timestamps)
        )
    
    def _get_or_create(self, key: str) -> ThrottleState:
        """Get or create state."""
        if key not in self._states:
            self._states[key] = ThrottleState(key=key)
        return self._states[key]
    
    def reset(self, key: str) -> None:
        """Reset state."""
        if key in self._states:
            self._states[key].timestamps.clear()
            self._states[key].request_count = 0
    
    def get_state(self, key: str) -> Optional[ThrottleState]:
        """Get state."""
        return self._states.get(key)


# =============================================================================
# RATE LIMITER FACTORY
# =============================================================================

class RateLimiterFactory:
    """Create rate limiters."""
    
    @classmethod
    def create(
        cls,
        algorithm: ThrottleAlgorithm,
        rate: float = 10.0,
        burst: float = 10.0,
        window_seconds: float = 60.0
    ) -> RateLimiter:
        """Create a rate limiter."""
        if algorithm == ThrottleAlgorithm.TOKEN_BUCKET:
            return TokenBucketLimiter(rate=rate, burst=burst)
        
        elif algorithm == ThrottleAlgorithm.LEAKY_BUCKET:
            return LeakyBucketLimiter(rate=rate, capacity=burst)
        
        elif algorithm == ThrottleAlgorithm.FIXED_WINDOW:
            return FixedWindowLimiter(limit=int(burst), window_seconds=window_seconds)
        
        elif algorithm == ThrottleAlgorithm.SLIDING_WINDOW:
            return SlidingWindowLimiter(limit=int(burst), window_seconds=window_seconds)
        
        elif algorithm == ThrottleAlgorithm.SLIDING_LOG:
            return SlidingWindowLimiter(limit=int(burst), window_seconds=window_seconds)
        
        return TokenBucketLimiter(rate=rate, burst=burst)


# =============================================================================
# QUOTA MANAGER
# =============================================================================

class QuotaManager:
    """Manage quotas."""
    
    def __init__(self):
        self._quotas: Dict[str, QuotaConfig] = {}
        self._usage: Dict[str, QuotaUsage] = {}
    
    def set_quota(self, key: str, config: QuotaConfig) -> None:
        """Set quota for key."""
        self._quotas[key] = config
        self._init_usage(key, config)
    
    def _init_usage(self, key: str, config: QuotaConfig) -> None:
        """Initialize usage tracking."""
        now = datetime.now()
        period_seconds = self._get_period_seconds(config.period)
        
        self._usage[key] = QuotaUsage(
            key=key,
            quota_type=config.quota_type,
            limit=config.limit,
            period_start=now,
            period_end=now + timedelta(seconds=period_seconds)
        )
    
    def _get_period_seconds(self, period: QuotaPeriod) -> float:
        """Get period in seconds."""
        periods = {
            QuotaPeriod.SECOND: 1,
            QuotaPeriod.MINUTE: 60,
            QuotaPeriod.HOUR: 3600,
            QuotaPeriod.DAY: 86400,
            QuotaPeriod.WEEK: 604800,
            QuotaPeriod.MONTH: 2592000,
        }
        return periods.get(period, 3600)
    
    def use(self, key: str, amount: float = 1.0) -> bool:
        """Use quota."""
        if key not in self._usage:
            return True
        
        usage = self._usage[key]
        config = self._quotas.get(key)
        
        now = datetime.now()
        if now >= usage.period_end and config:
            self._init_usage(key, config)
            usage = self._usage[key]
        
        if usage.used + amount <= usage.limit:
            usage.used += amount
            return True
        
        if config and config.burst_allowance > 0:
            if usage.used + amount <= usage.limit + config.burst_allowance:
                usage.used += amount
                return True
        
        return False
    
    def get_usage(self, key: str) -> Optional[QuotaUsage]:
        """Get quota usage."""
        return self._usage.get(key)
    
    def get_remaining(self, key: str) -> float:
        """Get remaining quota."""
        usage = self._usage.get(key)
        return usage.remaining if usage else float('inf')
    
    def reset(self, key: str) -> bool:
        """Reset quota."""
        config = self._quotas.get(key)
        if config:
            self._init_usage(key, config)
            return True
        return False
    
    def list_quotas(self) -> List[str]:
        """List quota keys."""
        return list(self._quotas.keys())


# =============================================================================
# THROTTLE GROUP
# =============================================================================

class ThrottleGroup:
    """Group of throttles applied together."""
    
    def __init__(self, name: str):
        self._name = name
        self._limiters: List[Tuple[str, RateLimiter]] = []
    
    @property
    def name(self) -> str:
        return self._name
    
    def add_limiter(self, name: str, limiter: RateLimiter) -> None:
        """Add a limiter to group."""
        self._limiters.append((name, limiter))
    
    def acquire(self, key: str, tokens: float = 1.0) -> ThrottleResponse:
        """Acquire from all limiters."""
        responses = []
        
        for name, limiter in self._limiters:
            response = limiter.acquire(key, tokens)
            responses.append((name, response))
            
            if response.result == ThrottleResult.DENIED:
                return ThrottleResponse(
                    result=ThrottleResult.DENIED,
                    remaining=response.remaining,
                    retry_after_seconds=response.retry_after_seconds,
                    limit=response.limit,
                    used=response.used
                )
        
        min_remaining = min(r.remaining for _, r in responses) if responses else 0
        
        return ThrottleResponse(
            result=ThrottleResult.ALLOWED,
            remaining=min_remaining,
            limit=max(r.limit for _, r in responses) if responses else 0,
            used=max(r.used for _, r in responses) if responses else 0
        )
    
    def reset(self, key: str) -> None:
        """Reset all limiters."""
        for _, limiter in self._limiters:
            limiter.reset(key)


# =============================================================================
# THROTTLING ENGINE
# =============================================================================

class ThrottlingEngine:
    """
    Throttling Engine for BAEL.
    
    Rate limiting and quota management.
    """
    
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
        self._groups: Dict[str, ThrottleGroup] = {}
        self._quotas = QuotaManager()
        
        self._stats: Dict[str, ThrottlingStats] = defaultdict(ThrottlingStats)
    
    # ----- Limiter Management -----
    
    def create_limiter(
        self,
        name: str,
        algorithm: ThrottleAlgorithm = ThrottleAlgorithm.TOKEN_BUCKET,
        rate: float = 10.0,
        burst: float = 10.0,
        window_seconds: float = 60.0
    ) -> RateLimiter:
        """Create a rate limiter."""
        limiter = RateLimiterFactory.create(
            algorithm=algorithm,
            rate=rate,
            burst=burst,
            window_seconds=window_seconds
        )
        self._limiters[name] = limiter
        return limiter
    
    def get_limiter(self, name: str) -> Optional[RateLimiter]:
        """Get a limiter."""
        return self._limiters.get(name)
    
    def delete_limiter(self, name: str) -> bool:
        """Delete a limiter."""
        if name in self._limiters:
            del self._limiters[name]
            return True
        return False
    
    def list_limiters(self) -> List[str]:
        """List limiter names."""
        return list(self._limiters.keys())
    
    # ----- Throttle Operations -----
    
    def acquire(
        self,
        limiter_name: str,
        key: str,
        tokens: float = 1.0
    ) -> ThrottleResponse:
        """Acquire tokens from limiter."""
        limiter = self._limiters.get(limiter_name)
        
        if not limiter:
            return ThrottleResponse(result=ThrottleResult.ALLOWED)
        
        response = limiter.acquire(key, tokens)
        self._update_stats(limiter_name, response)
        
        return response
    
    def check(
        self,
        limiter_name: str,
        key: str,
        tokens: float = 1.0
    ) -> bool:
        """Check if acquisition would succeed."""
        limiter = self._limiters.get(limiter_name)
        
        if not limiter:
            return True
        
        state = limiter.get_state(key)
        
        if state:
            if hasattr(limiter, '_burst'):
                return state.tokens >= tokens
            elif hasattr(limiter, '_limit'):
                return state.request_count + tokens <= limiter._limit
        
        return True
    
    def reset(self, limiter_name: str, key: str) -> bool:
        """Reset limiter for key."""
        limiter = self._limiters.get(limiter_name)
        
        if limiter:
            limiter.reset(key)
            return True
        
        return False
    
    def get_state(
        self,
        limiter_name: str,
        key: str
    ) -> Optional[ThrottleState]:
        """Get limiter state for key."""
        limiter = self._limiters.get(limiter_name)
        
        if limiter:
            return limiter.get_state(key)
        
        return None
    
    def _update_stats(
        self,
        limiter_name: str,
        response: ThrottleResponse
    ) -> None:
        """Update statistics."""
        stats = self._stats[limiter_name]
        stats.total_requests += 1
        
        if response.result == ThrottleResult.ALLOWED:
            stats.allowed_requests += 1
        elif response.result == ThrottleResult.DENIED:
            stats.denied_requests += 1
        elif response.result == ThrottleResult.LIMITED:
            stats.limited_requests += 1
    
    # ----- Group Operations -----
    
    def create_group(self, name: str) -> ThrottleGroup:
        """Create a throttle group."""
        group = ThrottleGroup(name)
        self._groups[name] = group
        return group
    
    def get_group(self, name: str) -> Optional[ThrottleGroup]:
        """Get a group."""
        return self._groups.get(name)
    
    def add_to_group(
        self,
        group_name: str,
        limiter_name: str
    ) -> bool:
        """Add limiter to group."""
        group = self._groups.get(group_name)
        limiter = self._limiters.get(limiter_name)
        
        if group and limiter:
            group.add_limiter(limiter_name, limiter)
            return True
        
        return False
    
    def acquire_group(
        self,
        group_name: str,
        key: str,
        tokens: float = 1.0
    ) -> ThrottleResponse:
        """Acquire from group."""
        group = self._groups.get(group_name)
        
        if not group:
            return ThrottleResponse(result=ThrottleResult.ALLOWED)
        
        return group.acquire(key, tokens)
    
    # ----- Quota Operations -----
    
    def set_quota(
        self,
        key: str,
        limit: float,
        period: QuotaPeriod = QuotaPeriod.HOUR,
        quota_type: QuotaType = QuotaType.REQUESTS
    ) -> None:
        """Set a quota."""
        config = QuotaConfig(
            quota_type=quota_type,
            limit=limit,
            period=period
        )
        self._quotas.set_quota(key, config)
    
    def use_quota(self, key: str, amount: float = 1.0) -> bool:
        """Use quota."""
        return self._quotas.use(key, amount)
    
    def get_quota_usage(self, key: str) -> Optional[QuotaUsage]:
        """Get quota usage."""
        return self._quotas.get_usage(key)
    
    def get_quota_remaining(self, key: str) -> float:
        """Get remaining quota."""
        return self._quotas.get_remaining(key)
    
    def reset_quota(self, key: str) -> bool:
        """Reset quota."""
        return self._quotas.reset(key)
    
    def list_quotas(self) -> List[str]:
        """List quotas."""
        return self._quotas.list_quotas()
    
    # ----- Combined Operations -----
    
    def throttle(
        self,
        limiter_name: str,
        key: str,
        quota_key: Optional[str] = None,
        tokens: float = 1.0
    ) -> ThrottleResponse:
        """Combined throttle and quota check."""
        rate_response = self.acquire(limiter_name, key, tokens)
        
        if rate_response.result != ThrottleResult.ALLOWED:
            return rate_response
        
        if quota_key:
            if not self.use_quota(quota_key, tokens):
                return ThrottleResponse(
                    result=ThrottleResult.LIMITED,
                    remaining=self.get_quota_remaining(quota_key),
                    limit=0
                )
        
        return rate_response
    
    # ----- Decorators -----
    
    def rate_limit(
        self,
        limiter_name: str,
        key_func: Optional[Callable] = None
    ) -> Callable:
        """Rate limit decorator."""
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                key = key_func(*args, **kwargs) if key_func else "default"
                response = self.acquire(limiter_name, key)
                
                if response.result != ThrottleResult.ALLOWED:
                    if response.retry_after_seconds > 0:
                        await asyncio.sleep(response.retry_after_seconds)
                        response = self.acquire(limiter_name, key)
                
                if response.result == ThrottleResult.ALLOWED:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    return func(*args, **kwargs)
                
                raise Exception(f"Rate limit exceeded: retry after {response.retry_after_seconds}s")
            
            return wrapper
        return decorator
    
    # ----- Statistics -----
    
    def get_stats(self, limiter_name: str) -> ThrottlingStats:
        """Get limiter stats."""
        return self._stats.get(limiter_name, ThrottlingStats())
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_requests = sum(s.total_requests for s in self._stats.values())
        allowed_requests = sum(s.allowed_requests for s in self._stats.values())
        denied_requests = sum(s.denied_requests for s in self._stats.values())
        
        return {
            "limiters": len(self._limiters),
            "groups": len(self._groups),
            "quotas": len(self._quotas.list_quotas()),
            "total_requests": total_requests,
            "allowed_requests": allowed_requests,
            "denied_requests": denied_requests,
            "allow_rate": allowed_requests / total_requests if total_requests > 0 else 1.0
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "limiters": self.list_limiters(),
            "groups": list(self._groups.keys()),
            "quotas": self.list_quotas()
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Throttling Engine."""
    print("=" * 70)
    print("BAEL - THROTTLING ENGINE DEMO")
    print("Rate Limiting & Quota Management")
    print("=" * 70)
    print()
    
    engine = ThrottlingEngine()
    
    # 1. Create Token Bucket Limiter
    print("1. TOKEN BUCKET LIMITER:")
    print("-" * 40)
    
    engine.create_limiter(
        "api",
        ThrottleAlgorithm.TOKEN_BUCKET,
        rate=5.0,
        burst=10.0
    )
    
    for i in range(12):
        response = engine.acquire("api", "user1")
        status = "✓" if response.result == ThrottleResult.ALLOWED else "✗"
        print(f"   Request {i+1}: {status} remaining={response.remaining:.1f}")
    print()
    
    # 2. Fixed Window Limiter
    print("2. FIXED WINDOW LIMITER:")
    print("-" * 40)
    
    engine.create_limiter(
        "fixed",
        ThrottleAlgorithm.FIXED_WINDOW,
        burst=5.0,
        window_seconds=1.0
    )
    
    for i in range(7):
        response = engine.acquire("fixed", "user1")
        status = "✓" if response.result == ThrottleResult.ALLOWED else "✗"
        print(f"   Request {i+1}: {status} remaining={response.remaining:.0f}")
    print()
    
    # 3. Sliding Window Limiter
    print("3. SLIDING WINDOW LIMITER:")
    print("-" * 40)
    
    engine.create_limiter(
        "sliding",
        ThrottleAlgorithm.SLIDING_WINDOW,
        burst=5.0,
        window_seconds=1.0
    )
    
    for i in range(7):
        response = engine.acquire("sliding", "user1")
        status = "✓" if response.result == ThrottleResult.ALLOWED else "✗"
        print(f"   Request {i+1}: {status} remaining={response.remaining:.0f}")
    print()
    
    # 4. Leaky Bucket Limiter
    print("4. LEAKY BUCKET LIMITER:")
    print("-" * 40)
    
    engine.create_limiter(
        "leaky",
        ThrottleAlgorithm.LEAKY_BUCKET,
        rate=2.0,
        burst=5.0
    )
    
    for i in range(6):
        response = engine.acquire("leaky", "user1")
        status = "✓" if response.result == ThrottleResult.ALLOWED else "✗"
        print(f"   Request {i+1}: {status} remaining={response.remaining:.1f}")
    print()
    
    # 5. Reset Limiter
    print("5. RESET LIMITER:")
    print("-" * 40)
    
    state_before = engine.get_state("api", "user1")
    print(f"   Before reset: tokens={state_before.tokens:.1f}")
    
    engine.reset("api", "user1")
    
    state_after = engine.get_state("api", "user1")
    print(f"   After reset: tokens={state_after.tokens:.1f}")
    print()
    
    # 6. Throttle Groups
    print("6. THROTTLE GROUPS:")
    print("-" * 40)
    
    engine.create_limiter(
        "per_second",
        ThrottleAlgorithm.TOKEN_BUCKET,
        rate=10.0,
        burst=10.0
    )
    
    engine.create_limiter(
        "per_minute",
        ThrottleAlgorithm.FIXED_WINDOW,
        burst=100.0,
        window_seconds=60.0
    )
    
    engine.create_group("combined")
    engine.add_to_group("combined", "per_second")
    engine.add_to_group("combined", "per_minute")
    
    for i in range(3):
        response = engine.acquire_group("combined", "user1")
        status = "✓" if response.result == ThrottleResult.ALLOWED else "✗"
        print(f"   Group request {i+1}: {status}")
    print()
    
    # 7. Quotas
    print("7. QUOTAS:")
    print("-" * 40)
    
    engine.set_quota(
        "user1:requests",
        limit=100.0,
        period=QuotaPeriod.HOUR
    )
    
    for i in range(5):
        success = engine.use_quota("user1:requests", 10.0)
        usage = engine.get_quota_usage("user1:requests")
        print(f"   Use 10: success={success}, used={usage.used}, remaining={usage.remaining}")
    print()
    
    # 8. Quota with Different Periods
    print("8. QUOTA PERIODS:")
    print("-" * 40)
    
    engine.set_quota("daily", 1000.0, QuotaPeriod.DAY)
    engine.set_quota("weekly", 5000.0, QuotaPeriod.WEEK)
    engine.set_quota("monthly", 10000.0, QuotaPeriod.MONTH)
    
    for key in ["daily", "weekly", "monthly"]:
        usage = engine.get_quota_usage(key)
        print(f"   {key}: limit={usage.limit}, remaining={usage.remaining}")
    print()
    
    # 9. Combined Throttle + Quota
    print("9. COMBINED THROTTLE + QUOTA:")
    print("-" * 40)
    
    engine.create_limiter("combined_api", ThrottleAlgorithm.TOKEN_BUCKET, rate=10.0, burst=5.0)
    engine.set_quota("combined_quota", 10.0, QuotaPeriod.MINUTE)
    
    for i in range(8):
        response = engine.throttle("combined_api", "user1", "combined_quota")
        status = "✓" if response.result == ThrottleResult.ALLOWED else "✗"
        remaining = engine.get_quota_remaining("combined_quota")
        print(f"   Combined {i+1}: {status} quota_remaining={remaining:.0f}")
    print()
    
    # 10. Wait and Retry
    print("10. WAIT AND RETRY:")
    print("-" * 40)
    
    engine.create_limiter("wait_test", ThrottleAlgorithm.TOKEN_BUCKET, rate=5.0, burst=2.0)
    
    engine.acquire("wait_test", "user1")
    engine.acquire("wait_test", "user1")
    
    response = engine.acquire("wait_test", "user1")
    if response.result == ThrottleResult.DENIED:
        print(f"   Denied, retry after: {response.retry_after_seconds:.2f}s")
        await asyncio.sleep(response.retry_after_seconds)
        response = engine.acquire("wait_test", "user1")
        print(f"   After waiting: {response.result.value}")
    print()
    
    # 11. Limiter Statistics
    print("11. LIMITER STATISTICS:")
    print("-" * 40)
    
    stats = engine.get_stats("api")
    print(f"   Total requests: {stats.total_requests}")
    print(f"   Allowed: {stats.allowed_requests}")
    print(f"   Denied: {stats.denied_requests}")
    print()
    
    # 12. Engine Statistics
    print("12. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")
    print()
    
    # 13. List Resources
    print("13. LIST RESOURCES:")
    print("-" * 40)
    
    print(f"   Limiters: {engine.list_limiters()}")
    print(f"   Quotas: {engine.list_quotas()}")
    print()
    
    # 14. Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Throttling Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
