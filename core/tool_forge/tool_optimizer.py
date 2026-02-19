"""
BAEL Tool Optimizer
====================

Performance optimization for generated tools.
Maximizes efficiency and reduces overhead.

Features:
- Performance profiling
- Code optimization
- Caching strategies
- Parallelization
- Resource management
"""

import asyncio
import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Optimization strategies."""
    CACHE = "cache"  # Add caching
    PARALLELIZE = "parallelize"  # Enable parallelization
    BATCH = "batch"  # Batch operations
    LAZY = "lazy"  # Lazy evaluation
    PRECOMPUTE = "precompute"  # Precompute values
    INLINE = "inline"  # Inline small functions
    MEMOIZE = "memoize"  # Memoization


class ProfileMetric(Enum):
    """Profiling metrics."""
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CALL_COUNT = "call_count"
    CACHE_HITS = "cache_hits"


@dataclass
class PerformanceProfile:
    """Performance profile of a tool."""
    tool_name: str

    # Timing
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0

    # Counts
    call_count: int = 0
    error_count: int = 0

    # Cache
    cache_hits: int = 0
    cache_misses: int = 0

    # Resource usage
    peak_memory_mb: float = 0.0

    # History
    execution_times: List[float] = field(default_factory=list)

    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def error_rate(self) -> float:
        """Calculate error rate."""
        return self.error_count / self.call_count if self.call_count > 0 else 0.0


@dataclass
class OptimizationResult:
    """Result of optimization."""
    id: str
    tool_name: str

    # Strategies applied
    strategies: List[OptimizationStrategy] = field(default_factory=list)

    # Performance impact
    speedup: float = 1.0
    memory_reduction: float = 0.0

    # Before/after
    original_avg_time: float = 0.0
    optimized_avg_time: float = 0.0

    # Generated optimizations
    optimized_code: str = ""
    wrapper_function: Optional[Callable] = None

    # Metadata
    optimized_at: datetime = field(default_factory=datetime.now)


class ToolOptimizer:
    """
    Tool optimizer for BAEL.

    Optimizes tool performance automatically.
    """

    def __init__(
        self,
        cache_size: int = 1000,
        profile_history: int = 100,
    ):
        self.cache_size = cache_size
        self.profile_history = profile_history

        # Profiles
        self._profiles: Dict[str, PerformanceProfile] = {}

        # Caches
        self._caches: Dict[str, Dict] = {}

        # Optimizations applied
        self._optimizations: Dict[str, OptimizationResult] = {}

        # Stats
        self.stats = {
            "tools_profiled": 0,
            "tools_optimized": 0,
            "total_speedup": 0.0,
            "cache_operations": 0,
        }

    def profile(
        self,
        func: Callable,
        name: Optional[str] = None,
    ) -> Callable:
        """
        Add profiling to a function.

        Args:
            func: Function to profile
            name: Profile name

        Returns:
            Profiled function
        """
        name = name or func.__name__

        if name not in self._profiles:
            self._profiles[name] = PerformanceProfile(tool_name=name)
            self.stats["tools_profiled"] += 1

        profile = self._profiles[name]

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    profile.error_count += 1
                    raise
                finally:
                    elapsed = (time.perf_counter() - start) * 1000
                    self._record_execution(profile, elapsed)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    profile.error_count += 1
                    raise
                finally:
                    elapsed = (time.perf_counter() - start) * 1000
                    self._record_execution(profile, elapsed)

            return sync_wrapper

    def _record_execution(
        self,
        profile: PerformanceProfile,
        elapsed_ms: float,
    ) -> None:
        """Record an execution in the profile."""
        profile.call_count += 1
        profile.total_time_ms += elapsed_ms
        profile.avg_time_ms = profile.total_time_ms / profile.call_count
        profile.min_time_ms = min(profile.min_time_ms, elapsed_ms)
        profile.max_time_ms = max(profile.max_time_ms, elapsed_ms)

        # Keep limited history
        profile.execution_times.append(elapsed_ms)
        if len(profile.execution_times) > self.profile_history:
            profile.execution_times.pop(0)

    def add_cache(
        self,
        func: Callable,
        maxsize: Optional[int] = None,
        ttl_seconds: Optional[float] = None,
    ) -> Callable:
        """
        Add caching to a function.

        Args:
            func: Function to cache
            maxsize: Maximum cache size
            ttl_seconds: Cache TTL

        Returns:
            Cached function
        """
        name = func.__name__
        maxsize = maxsize or self.cache_size

        # Initialize cache
        if name not in self._caches:
            self._caches[name] = {}

        cache = self._caches[name]
        cache_times: Dict[str, float] = {}

        # Get or create profile
        if name not in self._profiles:
            self._profiles[name] = PerformanceProfile(tool_name=name)
        profile = self._profiles[name]

        def make_key(args, kwargs) -> str:
            """Create cache key from arguments."""
            return hashlib.md5(
                str((args, sorted(kwargs.items()))).encode()
            ).hexdigest()

        def is_expired(key: str) -> bool:
            """Check if cache entry is expired."""
            if not ttl_seconds:
                return False
            return time.time() - cache_times.get(key, 0) > ttl_seconds

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_cached(*args, **kwargs):
                key = make_key(args, kwargs)

                if key in cache and not is_expired(key):
                    profile.cache_hits += 1
                    self.stats["cache_operations"] += 1
                    return cache[key]

                profile.cache_misses += 1
                result = await func(*args, **kwargs)

                # Store in cache
                if len(cache) >= maxsize:
                    # Remove oldest entry
                    oldest = min(cache_times, key=cache_times.get)
                    del cache[oldest]
                    del cache_times[oldest]

                cache[key] = result
                cache_times[key] = time.time()
                self.stats["cache_operations"] += 1

                return result

            return async_cached
        else:
            @wraps(func)
            def sync_cached(*args, **kwargs):
                key = make_key(args, kwargs)

                if key in cache and not is_expired(key):
                    profile.cache_hits += 1
                    self.stats["cache_operations"] += 1
                    return cache[key]

                profile.cache_misses += 1
                result = func(*args, **kwargs)

                if len(cache) >= maxsize:
                    oldest = min(cache_times, key=cache_times.get)
                    del cache[oldest]
                    del cache_times[oldest]

                cache[key] = result
                cache_times[key] = time.time()
                self.stats["cache_operations"] += 1

                return result

            return sync_cached

    def parallelize(
        self,
        func: Callable,
        max_workers: int = 4,
    ) -> Callable:
        """
        Add parallelization to a batch function.

        Args:
            func: Function to parallelize (should accept iterable)
            max_workers: Maximum parallel workers

        Returns:
            Parallelized function
        """
        @wraps(func)
        async def parallel_wrapper(items, *args, **kwargs):
            semaphore = asyncio.Semaphore(max_workers)

            async def process_item(item):
                async with semaphore:
                    if asyncio.iscoroutinefunction(func):
                        return await func(item, *args, **kwargs)
                    else:
                        return func(item, *args, **kwargs)

            tasks = [process_item(item) for item in items]
            return await asyncio.gather(*tasks)

        return parallel_wrapper

    def batch(
        self,
        func: Callable,
        batch_size: int = 10,
    ) -> Callable:
        """
        Add batching to a function.

        Args:
            func: Function to batch
            batch_size: Items per batch

        Returns:
            Batched function
        """
        pending = []

        @wraps(func)
        async def batched_wrapper(item, *args, **kwargs):
            pending.append((item, args, kwargs))

            if len(pending) >= batch_size:
                # Process batch
                batch = pending.copy()
                pending.clear()

                results = []
                for i, a, k in batch:
                    if asyncio.iscoroutinefunction(func):
                        results.append(await func(i, *a, **k))
                    else:
                        results.append(func(i, *a, **k))

                return results[-1]  # Return result for current item

            return None  # Batching in progress

        return batched_wrapper

    def optimize(
        self,
        func: Callable,
        strategies: Optional[List[OptimizationStrategy]] = None,
    ) -> Tuple[Callable, OptimizationResult]:
        """
        Apply optimizations to a function.

        Args:
            func: Function to optimize
            strategies: Strategies to apply

        Returns:
            (optimized_function, optimization_result)
        """
        name = func.__name__
        strategies = strategies or self._analyze_function(func)

        result_id = hashlib.md5(
            f"opt:{name}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        result = OptimizationResult(
            id=result_id,
            tool_name=name,
            strategies=strategies,
        )

        # Get original performance if profiled
        if name in self._profiles:
            result.original_avg_time = self._profiles[name].avg_time_ms

        # Apply strategies
        optimized = func

        for strategy in strategies:
            if strategy == OptimizationStrategy.CACHE:
                optimized = self.add_cache(optimized)
            elif strategy == OptimizationStrategy.MEMOIZE:
                optimized = lru_cache(maxsize=self.cache_size)(optimized)

        # Add profiling to measure improvement
        optimized = self.profile(optimized, f"{name}_optimized")

        result.wrapper_function = optimized

        self._optimizations[result_id] = result
        self.stats["tools_optimized"] += 1

        return optimized, result

    def _analyze_function(
        self,
        func: Callable,
    ) -> List[OptimizationStrategy]:
        """Analyze function to determine optimal strategies."""
        strategies = []

        # Check if function is pure (no side effects)
        # For simplicity, assume cacheable by default
        strategies.append(OptimizationStrategy.CACHE)

        # Check profile for patterns
        name = func.__name__
        if name in self._profiles:
            profile = self._profiles[name]

            # If many repeated calls with same results, memoize
            if profile.call_count > 10 and profile.cache_hit_rate() > 0.5:
                strategies.append(OptimizationStrategy.MEMOIZE)

        return strategies

    def clear_cache(self, name: Optional[str] = None) -> int:
        """Clear cache for a function or all caches."""
        if name:
            if name in self._caches:
                count = len(self._caches[name])
                self._caches[name].clear()
                return count
            return 0
        else:
            count = sum(len(c) for c in self._caches.values())
            self._caches.clear()
            return count

    def get_profile(self, name: str) -> Optional[PerformanceProfile]:
        """Get profile for a function."""
        return self._profiles.get(name)

    def list_profiles(self) -> List[PerformanceProfile]:
        """List all profiles."""
        return list(self._profiles.values())

    def get_slowest(self, n: int = 5) -> List[PerformanceProfile]:
        """Get the N slowest functions."""
        profiles = list(self._profiles.values())
        profiles.sort(key=lambda p: p.avg_time_ms, reverse=True)
        return profiles[:n]

    def get_most_called(self, n: int = 5) -> List[PerformanceProfile]:
        """Get the N most called functions."""
        profiles = list(self._profiles.values())
        profiles.sort(key=lambda p: p.call_count, reverse=True)
        return profiles[:n]

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        total_calls = sum(p.call_count for p in self._profiles.values())
        total_cache_hits = sum(p.cache_hits for p in self._profiles.values())
        total_cache_misses = sum(p.cache_misses for p in self._profiles.values())

        return {
            **self.stats,
            "total_calls_tracked": total_calls,
            "overall_cache_hit_rate": (
                total_cache_hits / (total_cache_hits + total_cache_misses)
                if total_cache_hits + total_cache_misses > 0 else 0
            ),
            "cache_size": sum(len(c) for c in self._caches.values()),
        }


def demo():
    """Demonstrate tool optimizer."""
    import asyncio

    print("=" * 60)
    print("BAEL Tool Optimizer Demo")
    print("=" * 60)

    async def run_demo():
        optimizer = ToolOptimizer()

        # Define a slow function
        def slow_calculate(n: int) -> int:
            """Simulate slow calculation."""
            time.sleep(0.01)  # Simulate work
            return n * n

        # Profile the function
        print("\nProfiling function...")
        profiled = optimizer.profile(slow_calculate, "slow_calculate")

        # Run several times
        for i in range(10):
            profiled(i % 5)  # Some repeated inputs

        profile = optimizer.get_profile("slow_calculate")
        print(f"  Calls: {profile.call_count}")
        print(f"  Avg time: {profile.avg_time_ms:.2f}ms")

        # Optimize with caching
        print("\nOptimizing with cache...")
        cached = optimizer.add_cache(slow_calculate)
        cached = optimizer.profile(cached, "cached_calculate")

        # Run with same inputs
        for i in range(10):
            cached(i % 5)  # Repeated inputs should hit cache

        cached_profile = optimizer.get_profile("cached_calculate")
        print(f"  Calls: {cached_profile.call_count}")
        print(f"  Cache hit rate: {cached_profile.cache_hit_rate():.0%}")
        print(f"  Avg time: {cached_profile.avg_time_ms:.2f}ms")

        # Automatic optimization
        print("\nAuto-optimizing...")

        def process_data(x):
            time.sleep(0.005)
            return x + 1

        optimized, result = optimizer.optimize(process_data)

        print(f"  Strategies applied: {[s.value for s in result.strategies]}")

        # Run optimized version
        for i in range(20):
            optimized(i % 4)

        # Get slowest functions
        print("\nSlowest functions:")
        for profile in optimizer.get_slowest(3):
            print(f"  {profile.tool_name}: {profile.avg_time_ms:.2f}ms avg")

        print(f"\nStats: {optimizer.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
