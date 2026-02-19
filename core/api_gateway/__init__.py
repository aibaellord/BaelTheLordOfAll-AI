"""
BAEL API Gateway Engine
=======================

Unified API gateway for all BAEL services.

"One gateway to rule all endpoints." — Ba'el
"""

from .api_gateway import (
    # Enums
    RouteMethod,
    AuthType,
    RateLimitStrategy,
    ResponseFormat,
    CacheStrategy,

    # Data structures
    Route,
    Middleware,
    RateLimitConfig,
    CORSConfig,
    AuthConfig,
    GatewayConfig,

    # Classes
    APIGateway,
    Router,
    MiddlewareChain,
    RateLimiter,
    AuthHandler,
    ResponseHandler,

    # Instance
    api_gateway
)

__all__ = [
    # Enums
    "RouteMethod",
    "AuthType",
    "RateLimitStrategy",
    "ResponseFormat",
    "CacheStrategy",

    # Data structures
    "Route",
    "Middleware",
    "RateLimitConfig",
    "CORSConfig",
    "AuthConfig",
    "GatewayConfig",

    # Classes
    "APIGateway",
    "Router",
    "MiddlewareChain",
    "RateLimiter",
    "AuthHandler",
    "ResponseHandler",

    # Instance
    "api_gateway"
]
