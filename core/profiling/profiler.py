#!/usr/bin/env python3
"""
BAEL - Agent Performance Profiler
Advanced profiling and benchmarking for agent operations.

Features:
- Execution time profiling
- Memory usage tracking
- Token consumption analysis
- Cost estimation
- Bottleneck detection
- Comparative benchmarking
"""

import asyncio
import cProfile
import functools
import gc
import io
import logging
import pstats
import resource
import sys
import time
import tracemalloc
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generator, List, Optional, Tuple,
                    TypeVar)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class ProfileLevel(Enum):
    """Profiling detail levels."""
    MINIMAL = 1     # Only timing
    STANDARD = 2    # Timing + memory
    DETAILED = 3    # All metrics
    DEBUG = 4       # Full trace


@dataclass
class TimingData:
    """Timing information."""
    start_time: float
    end_time: float = 0.0
    wall_time: float = 0.0
    cpu_time: float = 0.0

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


@dataclass
class MemoryData:
    """Memory usage information."""
    start_bytes: int = 0
    peak_bytes: int = 0
    end_bytes: int = 0
    allocations: int = 0

    @property
    def delta_mb(self) -> float:
        return (self.end_bytes - self.start_bytes) / (1024 * 1024)

    @property
    def peak_mb(self) -> float:
        return self.peak_bytes / (1024 * 1024)


@dataclass
class TokenData:
    """Token usage information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""

    @property
    def cost_estimate(self) -> float:
        """Estimate cost based on GPT-4 pricing."""
        # Approximate pricing per 1K tokens
        pricing = {
            "gpt-4": (0.03, 0.06),
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "claude-3-opus": (0.015, 0.075),
            "claude-3-sonnet": (0.003, 0.015),
            "claude-3-haiku": (0.00025, 0.00125),
        }

        model_key = self.model.lower()
        for key, (prompt_rate, completion_rate) in pricing.items():
            if key in model_key:
                return (
                    (self.prompt_tokens / 1000) * prompt_rate +
                    (self.completion_tokens / 1000) * completion_rate
                )

        # Default fallback
        return (self.total_tokens / 1000) * 0.01


@dataclass
class ProfileResult:
    """Complete profiling result."""
    id: str
    name: str
    timing: TimingData
    memory: Optional[MemoryData] = None
    tokens: Optional[TokenData] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["ProfileResult"] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "duration_ms": self.timing.duration_ms,
            "cpu_time_ms": self.timing.cpu_time * 1000,
            "memory_delta_mb": self.memory.delta_mb if self.memory else None,
            "memory_peak_mb": self.memory.peak_mb if self.memory else None,
            "tokens": self.tokens.total_tokens if self.tokens else None,
            "cost_estimate": self.tokens.cost_estimate if self.tokens else None,
            "error": self.error,
            "children": [c.to_dict() for c in self.children],
            "metadata": self.metadata
        }


@dataclass
class Benchmark:
    """Benchmark result."""
    name: str
    iterations: int
    results: List[ProfileResult]

    @property
    def mean_duration_ms(self) -> float:
        durations = [r.timing.duration_ms for r in self.results]
        return sum(durations) / len(durations) if durations else 0

    @property
    def min_duration_ms(self) -> float:
        return min((r.timing.duration_ms for r in self.results), default=0)

    @property
    def max_duration_ms(self) -> float:
        return max((r.timing.duration_ms for r in self.results), default=0)

    @property
    def std_dev_ms(self) -> float:
        durations = [r.timing.duration_ms for r in self.results]
        if len(durations) < 2:
            return 0
        mean = self.mean_duration_ms
        variance = sum((d - mean) ** 2 for d in durations) / len(durations)
        return variance ** 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "mean_ms": self.mean_duration_ms,
            "min_ms": self.min_duration_ms,
            "max_ms": self.max_duration_ms,
            "std_dev_ms": self.std_dev_ms,
            "results": [r.to_dict() for r in self.results]
        }


# =============================================================================
# PROFILER
# =============================================================================

class Profiler:
    """Agent performance profiler."""

    def __init__(self, level: ProfileLevel = ProfileLevel.STANDARD):
        self.level = level
        self.results: List[ProfileResult] = []
        self._current_stack: List[ProfileResult] = []
        self._token_tracker: Optional[Callable] = None

    def set_token_tracker(self, tracker: Callable[[], TokenData]) -> None:
        """Set function to track token usage."""
        self._token_tracker = tracker

    @contextmanager
    def profile(
        self,
        name: str,
        metadata: Dict[str, Any] = None
    ) -> Generator[ProfileResult, None, None]:
        """Profile a code block."""
        result = ProfileResult(
            id=str(uuid4()),
            name=name,
            timing=TimingData(start_time=time.perf_counter()),
            metadata=metadata or {}
        )

        # Memory tracking
        if self.level >= ProfileLevel.STANDARD:
            tracemalloc.start()
            result.memory = MemoryData(
                start_bytes=tracemalloc.get_traced_memory()[0]
            )

        # CPU timing
        cpu_start = time.process_time()

        # Stack management
        if self._current_stack:
            self._current_stack[-1].children.append(result)
        else:
            self.results.append(result)
        self._current_stack.append(result)

        try:
            yield result
        except Exception as e:
            result.error = str(e)
            raise
        finally:
            # Timing
            result.timing.end_time = time.perf_counter()
            result.timing.cpu_time = time.process_time() - cpu_start
            result.timing.wall_time = result.timing.end_time - result.timing.start_time

            # Memory
            if result.memory:
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                result.memory.end_bytes = current
                result.memory.peak_bytes = peak

            # Tokens
            if self._token_tracker:
                result.tokens = self._token_tracker()

            # Pop from stack
            self._current_stack.pop()

    @asynccontextmanager
    async def aprofile(
        self,
        name: str,
        metadata: Dict[str, Any] = None
    ):
        """Async profile context manager."""
        with self.profile(name, metadata) as result:
            yield result

    def profile_function(self, name: str = None):
        """Decorator to profile a function."""
        def decorator(func):
            fn_name = name or func.__name__

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.profile(fn_name):
                    return func(*args, **kwargs)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with self.aprofile(fn_name):
                    return await func(*args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return wrapper

        return decorator

    def detailed_profile(self, func: Callable, *args, **kwargs) -> Tuple[Any, str]:
        """Run function with cProfile for detailed stats."""
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()

        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(30)

        return result, stream.getvalue()

    def get_summary(self) -> Dict[str, Any]:
        """Get profiling summary."""
        if not self.results:
            return {"message": "No profiling data"}

        total_time = sum(r.timing.duration_ms for r in self.results)
        total_memory = sum(
            r.memory.delta_mb for r in self.results
            if r.memory
        )
        total_tokens = sum(
            r.tokens.total_tokens for r in self.results
            if r.tokens
        )
        total_cost = sum(
            r.tokens.cost_estimate for r in self.results
            if r.tokens
        )

        # Find bottlenecks
        sorted_by_time = sorted(
            self.results,
            key=lambda r: r.timing.duration_ms,
            reverse=True
        )

        return {
            "total_operations": len(self.results),
            "total_time_ms": total_time,
            "total_memory_mb": total_memory,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "average_time_ms": total_time / len(self.results),
            "bottlenecks": [
                {
                    "name": r.name,
                    "duration_ms": r.timing.duration_ms,
                    "percentage": (r.timing.duration_ms / total_time) * 100
                }
                for r in sorted_by_time[:5]
            ]
        }

    def clear(self) -> None:
        """Clear profiling data."""
        self.results.clear()
        self._current_stack.clear()


# =============================================================================
# BENCHMARKER
# =============================================================================

class Benchmarker:
    """Run and compare benchmarks."""

    def __init__(self, profiler: Profiler = None):
        self.profiler = profiler or Profiler(ProfileLevel.MINIMAL)
        self.benchmarks: Dict[str, Benchmark] = {}

    def run(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
        *args,
        **kwargs
    ) -> Benchmark:
        """Run benchmark."""
        # Warmup
        for _ in range(warmup):
            func(*args, **kwargs)

        # Force GC
        gc.collect()

        results = []
        for i in range(iterations):
            with self.profiler.profile(f"{name}_{i}") as result:
                func(*args, **kwargs)
            results.append(result)

        benchmark = Benchmark(
            name=name,
            iterations=iterations,
            results=results
        )

        self.benchmarks[name] = benchmark
        return benchmark

    async def run_async(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
        *args,
        **kwargs
    ) -> Benchmark:
        """Run async benchmark."""
        # Warmup
        for _ in range(warmup):
            await func(*args, **kwargs)

        gc.collect()

        results = []
        for i in range(iterations):
            async with self.profiler.aprofile(f"{name}_{i}") as result:
                await func(*args, **kwargs)
            results.append(result)

        benchmark = Benchmark(
            name=name,
            iterations=iterations,
            results=results
        )

        self.benchmarks[name] = benchmark
        return benchmark

    def compare(self, *names: str) -> Dict[str, Any]:
        """Compare benchmarks."""
        comparisons = []

        for name in names:
            if name in self.benchmarks:
                b = self.benchmarks[name]
                comparisons.append({
                    "name": name,
                    "mean_ms": b.mean_duration_ms,
                    "min_ms": b.min_duration_ms,
                    "max_ms": b.max_duration_ms,
                    "std_dev_ms": b.std_dev_ms
                })

        if len(comparisons) >= 2:
            baseline = comparisons[0]
            for c in comparisons[1:]:
                c["speedup"] = baseline["mean_ms"] / c["mean_ms"]
                c["difference_ms"] = baseline["mean_ms"] - c["mean_ms"]

        return {
            "comparisons": comparisons,
            "fastest": min(comparisons, key=lambda x: x["mean_ms"])["name"] if comparisons else None,
            "slowest": max(comparisons, key=lambda x: x["mean_ms"])["name"] if comparisons else None
        }


# =============================================================================
# RESOURCE MONITOR
# =============================================================================

class ResourceMonitor:
    """Monitor system resources."""

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.samples: List[Dict[str, Any]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start monitoring."""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Monitoring loop."""
        while self._running:
            sample = self._collect_sample()
            self.samples.append(sample)
            await asyncio.sleep(self.interval)

    def _collect_sample(self) -> Dict[str, Any]:
        """Collect resource sample."""
        try:
            import psutil
            process = psutil.Process()

            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "memory_percent": process.memory_percent(),
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
        except ImportError:
            # Fallback without psutil
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "timestamp": datetime.now().isoformat(),
                "user_time": usage.ru_utime,
                "system_time": usage.ru_stime,
                "max_rss_mb": usage.ru_maxrss / (1024 * 1024)
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get resource statistics."""
        if not self.samples:
            return {"message": "No samples collected"}

        cpu_values = [s.get("cpu_percent", 0) for s in self.samples]
        mem_values = [s.get("memory_mb", 0) for s in self.samples]

        return {
            "sample_count": len(self.samples),
            "duration_seconds": len(self.samples) * self.interval,
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_mb": {
                "avg": sum(mem_values) / len(mem_values),
                "max": max(mem_values),
                "min": min(mem_values)
            }
        }

    def clear(self) -> None:
        """Clear samples."""
        self.samples.clear()


# =============================================================================
# TRACE COLLECTOR
# =============================================================================

class TraceCollector:
    """Collect execution traces for analysis."""

    def __init__(self, max_traces: int = 1000):
        self.max_traces = max_traces
        self.traces: List[Dict[str, Any]] = []

    def add_trace(
        self,
        operation: str,
        duration_ms: float,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Add trace entry."""
        trace = {
            "id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "duration_ms": duration_ms,
            "metadata": metadata or {}
        }

        self.traces.append(trace)

        # Trim if needed
        if len(self.traces) > self.max_traces:
            self.traces = self.traces[-self.max_traces:]

    def find_slow_operations(
        self,
        threshold_ms: float = 1000
    ) -> List[Dict[str, Any]]:
        """Find operations exceeding threshold."""
        return [
            t for t in self.traces
            if t["duration_ms"] > threshold_ms
        ]

    def get_operation_stats(self) -> Dict[str, Dict[str, float]]:
        """Get stats grouped by operation."""
        from collections import defaultdict

        by_op: Dict[str, List[float]] = defaultdict(list)
        for trace in self.traces:
            by_op[trace["operation"]].append(trace["duration_ms"])

        stats = {}
        for op, durations in by_op.items():
            stats[op] = {
                "count": len(durations),
                "total_ms": sum(durations),
                "avg_ms": sum(durations) / len(durations),
                "min_ms": min(durations),
                "max_ms": max(durations)
            }

        return stats


# =============================================================================
# GLOBAL PROFILER
# =============================================================================

_profiler: Optional[Profiler] = None


def get_profiler() -> Profiler:
    """Get global profiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = Profiler()
    return _profiler


def profile(name: str = None, metadata: Dict[str, Any] = None):
    """Decorator using global profiler."""
    profiler = get_profiler()
    return profiler.profile_function(name)


# =============================================================================
# MAIN
# =============================================================================

async def demo():
    """Demo profiler."""
    profiler = Profiler(ProfileLevel.DETAILED)

    # Profile some operations
    with profiler.profile("outer_operation"):
        # Simulate work
        time.sleep(0.1)

        with profiler.profile("inner_operation_1"):
            time.sleep(0.05)

        with profiler.profile("inner_operation_2"):
            # Allocate memory
            data = [i for i in range(100000)]
            time.sleep(0.03)

    print("Profile Summary:")
    print(profiler.get_summary())

    # Benchmark
    benchmarker = Benchmarker()

    def sort_list(n: int):
        import random
        data = [random.random() for _ in range(n)]
        return sorted(data)

    print("\nRunning benchmarks...")

    b1 = benchmarker.run("sort_1000", sort_list, iterations=50, warmup=5, n=1000)
    print(f"sort_1000: mean={b1.mean_duration_ms:.2f}ms, std={b1.std_dev_ms:.2f}ms")

    b2 = benchmarker.run("sort_10000", sort_list, iterations=50, warmup=5, n=10000)
    print(f"sort_10000: mean={b2.mean_duration_ms:.2f}ms, std={b2.std_dev_ms:.2f}ms")

    comparison = benchmarker.compare("sort_1000", "sort_10000")
    print(f"\nComparison: {comparison}")

    # Resource monitor
    monitor = ResourceMonitor(interval=0.1)
    await monitor.start()

    # Do some work
    await asyncio.sleep(0.5)

    await monitor.stop()
    print(f"\nResource stats: {monitor.get_stats()}")


if __name__ == "__main__":
    asyncio.run(demo())
