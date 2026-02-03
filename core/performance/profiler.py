"""
BAEL - Performance Profiling Utilities
Decorators and utilities for profiling critical system paths.
"""

import cProfile
import functools
import io
import logging
import pstats
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("BAEL.Profiler")


# =============================================================================
# Performance Metrics Storage
# =============================================================================

class PerformanceMetrics:
    """Thread-safe performance metrics collector."""

    def __init__(self):
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.total_times: Dict[str, float] = defaultdict(float)
        self.min_times: Dict[str, float] = {}
        self.max_times: Dict[str, float] = {}

    def record(self, func_name: str, execution_time: float):
        """Record execution metrics."""
        self.call_counts[func_name] += 1
        self.total_times[func_name] += execution_time

        if func_name not in self.min_times:
            self.min_times[func_name] = execution_time
        else:
            self.min_times[func_name] = min(self.min_times[func_name], execution_time)

        if func_name not in self.max_times:
            self.max_times[func_name] = execution_time
        else:
            self.max_times[func_name] = max(self.max_times[func_name], execution_time)

    def get_stats(self, func_name: str) -> Dict[str, Any]:
        """Get statistics for a function."""
        if func_name not in self.call_counts:
            return {}

        count = self.call_counts[func_name]
        total = self.total_times[func_name]

        return {
            "calls": count,
            "total_time": total,
            "avg_time": total / count,
            "min_time": self.min_times[func_name],
            "max_time": self.max_times[func_name]
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all statistics sorted by total time."""
        stats = {}
        for func_name in self.call_counts.keys():
            stats[func_name] = self.get_stats(func_name)

        # Sort by total time descending
        return dict(sorted(stats.items(), key=lambda x: x[1]["total_time"], reverse=True))

    def reset(self):
        """Reset all metrics."""
        self.call_counts.clear()
        self.total_times.clear()
        self.min_times.clear()
        self.max_times.clear()


# Global metrics instance
_global_metrics = PerformanceMetrics()


def get_metrics() -> PerformanceMetrics:
    """Get global metrics instance."""
    return _global_metrics


# =============================================================================
# Profiling Decorators
# =============================================================================

def profile_time(func: Callable) -> Callable:
    """
    Decorator to measure execution time of a function.

    Usage:
        @profile_time
        async def my_function():
            ...
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__qualname__}"
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            execution_time = time.perf_counter() - start_time
            _global_metrics.record(func_name, execution_time)

            # Log slow operations (>1 second)
            if execution_time > 1.0:
                logger.warning(f"⚠️ Slow operation: {func_name} took {execution_time:.3f}s")

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__qualname__}"
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            execution_time = time.perf_counter() - start_time
            _global_metrics.record(func_name, execution_time)

            # Log slow operations (>1 second)
            if execution_time > 1.0:
                logger.warning(f"⚠️ Slow operation: {func_name} took {execution_time:.3f}s")

    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def profile_cpu(sort_by: str = 'cumulative', limit: int = 20):
    """
    Decorator to profile CPU usage with cProfile.

    Args:
        sort_by: Sort criterion for stats ('cumulative', 'time', 'calls')
        limit: Number of top entries to show

    Usage:
        @profile_cpu(sort_by='time', limit=10)
        def my_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            profiler.enable()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.disable()

                # Print stats
                stream = io.StringIO()
                stats = pstats.Stats(profiler, stream=stream)
                stats.sort_stats(sort_by)
                stats.print_stats(limit)

                logger.info(f"\n{'='*80}\nCPU Profile: {func.__qualname__}\n{'='*80}\n{stream.getvalue()}")

        return wrapper

    return decorator


@contextmanager
def profile_section(section_name: str):
    """
    Context manager to profile a code section.

    Usage:
        with profile_section("data_loading"):
            # code to profile
            load_data()
    """
    start_time = time.perf_counter()

    try:
        yield
    finally:
        execution_time = time.perf_counter() - start_time
        _global_metrics.record(section_name, execution_time)
        logger.debug(f"Section '{section_name}' took {execution_time:.3f}s")


# =============================================================================
# Performance Reporting
# =============================================================================

def print_performance_report(top_n: int = 20):
    """Print a performance report of top N slowest operations."""
    stats = _global_metrics.get_all_stats()

    if not stats:
        logger.info("No performance data collected yet.")
        return

    logger.info("\n" + "="*80)
    logger.info(f"PERFORMANCE REPORT - Top {top_n} Operations by Total Time")
    logger.info("="*80)

    header = f"{'Function':<50} {'Calls':>8} {'Total(s)':>10} {'Avg(ms)':>10} {'Min(ms)':>10} {'Max(ms)':>10}"
    logger.info(header)
    logger.info("-"*80)

    for i, (func_name, data) in enumerate(list(stats.items())[:top_n], 1):
        # Truncate function name if too long
        display_name = func_name if len(func_name) <= 50 else "..." + func_name[-47:]

        row = (
            f"{display_name:<50} "
            f"{data['calls']:>8} "
            f"{data['total_time']:>10.3f} "
            f"{data['avg_time']*1000:>10.2f} "
            f"{data['min_time']*1000:>10.2f} "
            f"{data['max_time']*1000:>10.2f}"
        )
        logger.info(row)

    logger.info("="*80 + "\n")


def get_hotspots(threshold_seconds: float = 0.1) -> Dict[str, Dict[str, Any]]:
    """
    Get performance hotspots (functions taking more than threshold).

    Args:
        threshold_seconds: Minimum avg time to be considered a hotspot

    Returns:
        Dictionary of hotspot functions and their stats
    """
    all_stats = _global_metrics.get_all_stats()

    hotspots = {
        func_name: stats
        for func_name, stats in all_stats.items()
        if stats["avg_time"] >= threshold_seconds
    }

    return hotspots


# =============================================================================
# Memory Profiling
# =============================================================================

def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage statistics."""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    return {
        "rss_mb": memory_info.rss / 1024 / 1024,  # Resident set size
        "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual memory size
        "percent": process.memory_percent(),
        "available_mb": psutil.virtual_memory().available / 1024 / 1024
    }


@contextmanager
def track_memory(operation_name: str):
    """
    Context manager to track memory usage of an operation.

    Usage:
        with track_memory("model_loading"):
            model = load_large_model()
    """
    import os

    import psutil

    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss / 1024 / 1024  # MB

    try:
        yield
    finally:
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        delta = end_memory - start_memory

        logger.info(f"Memory: {operation_name} - Start: {start_memory:.1f}MB, End: {end_memory:.1f}MB, Delta: {delta:+.1f}MB")


# =============================================================================
# API for External Use
# =============================================================================

__all__ = [
    'profile_time',
    'profile_cpu',
    'profile_section',
    'print_performance_report',
    'get_hotspots',
    'get_metrics',
    'get_memory_usage',
    'track_memory'
]
