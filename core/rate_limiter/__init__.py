"""
BAEL Rate Limiter Engine
=========================

Advanced rate limiting with:
- Token bucket
- Sliding window
- Leaky bucket
- Quotas
- Distributed support

"Ba'el controls the flow of all requests." — Ba'el
"""

from .rate_limiter_engine import (
    # Enums
    RateLimitAlgorithm,
    RateLimitScope,
    RateLimitAction,

    # Data structures
    RateLimit,
    RateLimitResult,
    Quota,
    RateLimiterConfig,

    # Engine
    RateLimiterEngine,
    rate_limiter_engine,
)

__all__ = [
    # Enums
    "RateLimitAlgorithm",
    "RateLimitScope",
    "RateLimitAction",

    # Data structures
    "RateLimit",
    "RateLimitResult",
    "Quota",
    "RateLimiterConfig",

    # Engine
    "RateLimiterEngine",
    "rate_limiter_engine",
]
