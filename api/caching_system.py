"""
Advanced Caching & Performance System for BAEL

Multi-level caching (L1 in-memory, L2 Redis, L3 disk), query optimization,
database performance tuning, and intelligent cache management.
"""

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CacheLevel(Enum):
    """Cache hierarchy levels."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DISK = "l3_disk"


class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    ARC = "arc"  # Adaptive Replacement Cache
    CLOCK = "clock"


@dataclass
class CacheEntry:
    """Single cache entry."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    def get_age_seconds(self) -> float:
        """Get entry age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()

    def update_access(self) -> None:
        """Update access time and count."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class L1MemoryCache:
    """Level 1: In-memory cache with LRU eviction."""

    def __init__(self, max_size_mb: int = 500, policy: EvictionPolicy = EvictionPolicy.LRU):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.policy = policy
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_size = 0
        self.hits = 0
        self.misses = 0

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
            tags: Optional[List[str]] = None) -> None:
        """Set cache entry."""
        if key in self.entries:
            self.current_size -= self.entries[key].size_bytes

        # Estimate size (rough approximation)
        size = len(str(value))

        # Evict if needed
        while self.current_size + size > self.max_size_bytes and self.entries:
            self._evict_one()

        entry = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
            size_bytes=size,
            tags=tags or []
        )

        self.entries[key] = entry
        # Move to end (most recently used)
        self.entries.move_to_end(key)
        self.current_size += size

    def get(self, key: str) -> Optional[Any]:
        """Get cache entry."""
        if key not in self.entries:
            self.misses += 1
            return None

        entry = self.entries[key]

        if entry.is_expired():
            del self.entries[key]
            self.current_size -= entry.size_bytes
            self.misses += 1
            return None

        entry.update_access()
        self.entries.move_to_end(key)  # Mark as recently used
        self.hits += 1
        return entry.value

    def delete(self, key: str) -> bool:
        """Delete entry."""
        if key in self.entries:
            entry = self.entries[key]
            self.current_size -= entry.size_bytes
            del self.entries[key]
            return True
        return False

    def _evict_one(self) -> None:
        """Evict one entry based on policy."""
        if not self.entries:
            return

        if self.policy == EvictionPolicy.LRU:
            # Remove least recently used (first item)
            key, entry = self.entries.popitem(last=False)
        elif self.policy == EvictionPolicy.LFU:
            # Remove least frequently used
            key = min(self.entries.keys(),
                     key=lambda k: self.entries[k].access_count)
            entry = self.entries.pop(key)
        elif self.policy == EvictionPolicy.FIFO:
            # Remove oldest
            key = min(self.entries.keys(),
                     key=lambda k: self.entries[k].created_at)
            entry = self.entries.pop(key)
        else:
            # Default to LRU
            key, entry = self.entries.popitem(last=False)

        self.current_size -= entry.size_bytes

    def clear(self) -> None:
        """Clear all entries."""
        self.entries.clear()
        self.current_size = 0

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            "level": "L1",
            "entries": len(self.entries),
            "size_bytes": self.current_size,
            "max_size_bytes": self.max_size_bytes,
            "usage_percent": (self.current_size / self.max_size_bytes) * 100,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": (self.hits / total * 100) if total > 0 else 0
        }


class L2RedisCache:
    """Level 2: Redis-like distributed cache simulation."""

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.entries: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
            tags: Optional[List[str]] = None) -> None:
        """Set entry in cache."""
        if len(self.entries) >= self.max_entries:
            # Simple eviction: remove random entry
            if self.entries:
                oldest_key = min(self.entries.keys(),
                               key=lambda k: self.entries[k].created_at)
                del self.entries[oldest_key]

        entry = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
            size_bytes=len(str(value)),
            tags=tags or []
        )
        self.entries[key] = entry

    def get(self, key: str) -> Optional[Any]:
        """Get entry from cache."""
        if key not in self.entries:
            self.misses += 1
            return None

        entry = self.entries[key]

        if entry.is_expired():
            del self.entries[key]
            self.misses += 1
            return None

        entry.update_access()
        self.hits += 1
        return entry.value

    def get_by_tag(self, tag: str) -> List[Tuple[str, Any]]:
        """Get entries by tag."""
        results = []
        for key, entry in self.entries.items():
            if tag in entry.tags and not entry.is_expired():
                results.append((key, entry.value))
        return results

    def delete(self, key: str) -> bool:
        """Delete entry."""
        if key in self.entries:
            del self.entries[key]
            return True
        return False

    def get_stats(self) -> Dict:
        """Get statistics."""
        total = self.hits + self.misses
        return {
            "level": "L2",
            "entries": len(self.entries),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": (self.hits / total * 100) if total > 0 else 0
        }


class L3DiskCache:
    """Level 3: Disk-based cache."""

    def __init__(self, max_entries: int = 100000):
        self.max_entries = max_entries
        self.entries: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set entry on disk."""
        if len(self.entries) >= self.max_entries:
            # Remove oldest
            if self.entries:
                oldest_key = min(self.entries.keys(),
                               key=lambda k: self.entries[k].created_at)
                del self.entries[oldest_key]

        entry = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds
        )
        self.entries[key] = entry

    def get(self, key: str) -> Optional[Any]:
        """Get entry from disk."""
        if key not in self.entries:
            self.misses += 1
            return None

        entry = self.entries[key]

        if entry.is_expired():
            del self.entries[key]
            self.misses += 1
            return None

        entry.update_access()
        self.hits += 1
        return entry.value

    def get_stats(self) -> Dict:
        """Get statistics."""
        total = self.hits + self.misses
        return {
            "level": "L3",
            "entries": len(self.entries),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": (self.hits / total * 100) if total > 0 else 0
        }


class MultiLevelCache:
    """Unified multi-level cache system."""

    def __init__(self):
        self.l1 = L1MemoryCache(max_size_mb=500)
        self.l2 = L2RedisCache(max_entries=10000)
        self.l3 = L3DiskCache(max_entries=100000)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
            level: CacheLevel = CacheLevel.L1_MEMORY) -> None:
        """Set value across cache levels."""
        if level == CacheLevel.L1_MEMORY:
            self.l1.set(key, value, ttl_seconds)
        elif level == CacheLevel.L2_REDIS:
            self.l2.set(key, value, ttl_seconds)
            # Also put in L1
            self.l1.set(key, value, ttl_seconds)
        else:  # L3
            self.l3.set(key, value, ttl_seconds)
            self.l2.set(key, value, ttl_seconds)
            self.l1.set(key, value, ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache hierarchy."""
        # Check L1
        value = self.l1.get(key)
        if value is not None:
            return value

        # Check L2
        value = self.l2.get(key)
        if value is not None:
            self.l1.set(key, value)  # Promote to L1
            return value

        # Check L3
        value = self.l3.get(key)
        if value is not None:
            # Promote through levels
            self.l2.set(key, value)
            self.l1.set(key, value)
            return value

        return None

    def delete(self, key: str) -> None:
        """Delete from all levels."""
        self.l1.delete(key)
        self.l2.delete(key)
        self.l3.delete(key)

    def clear(self) -> None:
        """Clear all caches."""
        self.l1.clear()
        self.l2.entries.clear()
        self.l3.entries.clear()

    def get_cache_stats(self) -> Dict:
        """Get statistics for all levels."""
        return {
            "l1": self.l1.get_stats(),
            "l2": self.l2.get_stats(),
            "l3": self.l3.get_stats(),
            "total_hit_rate": self._compute_total_hit_rate()
        }

    def _compute_total_hit_rate(self) -> float:
        """Compute total hit rate across all levels."""
        total_hits = self.l1.hits + self.l2.hits + self.l3.hits
        total_requests = total_hits + max(self.l1.misses, self.l2.misses, self.l3.misses)
        return (total_hits / total_requests * 100) if total_requests > 0 else 0


class QueryOptimizer:
    """Optimizes database queries."""

    def __init__(self):
        self.query_plans: Dict[str, Dict] = {}
        self.execution_times: Dict[str, List[float]] = {}

    def analyze_query(self, query: str) -> Dict:
        """Analyze query for optimization opportunities."""
        query_hash = hashlib.md5(query.encode()).hexdigest()

        return {
            "query_hash": query_hash,
            "estimated_cost": self._estimate_cost(query),
            "optimization_suggestions": self._suggest_optimizations(query),
            "indexed_fields": self._identify_indexed_fields(query)
        }

    def _estimate_cost(self, query: str) -> float:
        """Estimate query cost."""
        # Simple heuristic
        cost = 1.0
        if "JOIN" in query.upper():
            cost += 0.5 * query.upper().count("JOIN")
        if "WHERE" not in query.upper():
            cost += 2.0  # Full table scan
        return cost

    def _suggest_optimizations(self, query: str) -> List[str]:
        """Suggest optimizations."""
        suggestions = []
        if "WHERE" not in query.upper():
            suggestions.append("Add WHERE clause to reduce result set")
        if query.upper().count("JOIN") > 3:
            suggestions.append("Consider breaking into multiple queries")
        if "SELECT *" in query.upper():
            suggestions.append("Specify needed columns instead of SELECT *")
        return suggestions

    def _identify_indexed_fields(self, query: str) -> List[str]:
        """Identify fields that should be indexed."""
        fields = []
        if "WHERE" in query.upper():
            fields.append("*")  # Mark WHERE fields for indexing
        return fields

    def record_execution(self, query: str, execution_time_ms: float) -> None:
        """Record query execution time."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if query_hash not in self.execution_times:
            self.execution_times[query_hash] = []
        self.execution_times[query_hash].append(execution_time_ms)


class PerformanceMonitor:
    """Monitors system performance."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.thresholds: Dict[str, float] = {
            "query_time_ms": 1000,
            "cache_hit_rate": 0.8,
            "memory_usage_percent": 90
        }

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record performance metric."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)

        # Keep last 1000 measurements
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]

    def check_thresholds(self) -> Dict[str, bool]:
        """Check if metrics exceed thresholds."""
        status = {}
        for metric, threshold in self.thresholds.items():
            if metric in self.metrics and self.metrics[metric]:
                recent_avg = sum(self.metrics[metric][-10:]) / 10
                status[metric] = recent_avg <= threshold
        return status

    def get_performance_summary(self) -> Dict:
        """Get performance summary."""
        return {
            "metrics": {
                name: {
                    "latest": values[-1] if values else None,
                    "average": sum(values) / len(values) if values else None,
                    "min": min(values) if values else None,
                    "max": max(values) if values else None
                }
                for name, values in self.metrics.items()
            },
            "threshold_status": self.check_thresholds()
        }


class AdvancedCachingPerformanceSystem:
    """Main caching and performance orchestrator."""

    def __init__(self):
        self.cache = MultiLevelCache()
        self.optimizer = QueryOptimizer()
        self.monitor = PerformanceMonitor()

    def cache_query_result(self, query: str, result: Any,
                          ttl_seconds: int = 3600) -> None:
        """Cache query result."""
        cache_key = f"query_{hashlib.md5(query.encode()).hexdigest()}"
        self.cache.set(cache_key, result, ttl_seconds, CacheLevel.L2_REDIS)

    def get_cached_result(self, query: str) -> Optional[Any]:
        """Get cached query result."""
        cache_key = f"query_{hashlib.md5(query.encode()).hexdigest()}"
        return self.cache.get(cache_key)

    def get_system_stats(self) -> Dict:
        """Get system statistics."""
        return {
            "cache_stats": self.cache.get_cache_stats(),
            "performance": self.monitor.get_performance_summary(),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
_caching_system = None


def get_caching_system() -> AdvancedCachingPerformanceSystem:
    """Get or create global caching system."""
    global _caching_system
    if _caching_system is None:
        _caching_system = AdvancedCachingPerformanceSystem()
    return _caching_system
