"""
BAEL Cache Engine
=================

Advanced caching system with multiple eviction policies,
distributed caching support, and Redis-like features.

"Memory is the foundation of intelligence." — Ba'el
"""

from .cache_manager import (
    # Enums
    EvictionPolicy,
    CacheType,
    CacheStatus,
    SerializationFormat,

    # Data structures
    CacheEntry,
    CacheConfig,
    CacheStats,

    # Classes
    CacheEngine,
    LRUCache,
    LFUCache,
    TTLCache,
    DistributedCache,
    MultiLevelCache,

    # Instance
    cache_engine,
)

__all__ = [
    # Enums
    'EvictionPolicy',
    'CacheType',
    'CacheStatus',
    'SerializationFormat',

    # Data structures
    'CacheEntry',
    'CacheConfig',
    'CacheStats',

    # Classes
    'CacheEngine',
    'LRUCache',
    'LFUCache',
    'TTLCache',
    'DistributedCache',
    'MultiLevelCache',

    # Instance
    'cache_engine',
]
