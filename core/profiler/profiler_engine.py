#!/usr/bin/env python3
"""
BAEL - Profiler Engine
Comprehensive performance profiling for ML pipelines.

Features:
- Time profiling
- Memory profiling
- Operation counting
- Throughput measurement
- Bottleneck detection
- Detailed reporting
"""

import asyncio
import gc
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ProfilerType(Enum):
    """Profiler types."""
    TIME = "time"
    MEMORY = "memory"
    OPERATIONS = "operations"
    THROUGHPUT = "throughput"
    COMBINED = "combined"


class ProfilerState(Enum):
    """Profiler states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class OperationType(Enum):
    """Operation types for counting."""
    FORWARD = "forward"
    BACKWARD = "backward"
    OPTIMIZATION = "optimization"
    DATA_LOADING = "data_loading"
    PREPROCESSING = "preprocessing"
    INFERENCE = "inference"
    EVALUATION = "evaluation"
    CUSTOM = "custom"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TimeRecord:
    """Time measurement record."""
    name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0


@dataclass
class MemoryRecord:
    """Memory measurement record."""
    name: str = ""
    allocated: int = 0
    freed: int = 0
    peak: int = 0
    current: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OperationRecord:
    """Operation count record."""
    operation_type: OperationType = OperationType.CUSTOM
    name: str = ""
    count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0


@dataclass
class ThroughputRecord:
    """Throughput measurement record."""
    name: str = ""
    items_processed: int = 0
    time_elapsed: float = 0.0
    items_per_second: float = 0.0
    bytes_processed: int = 0
    bytes_per_second: float = 0.0


@dataclass
class ProfilerConfig:
    """Profiler configuration."""
    enabled: bool = True
    track_time: bool = True
    track_memory: bool = True
    track_operations: bool = True
    track_throughput: bool = True
    memory_threshold_mb: float = 100.0
    time_threshold_ms: float = 100.0
    warmup_runs: int = 3


@dataclass
class ProfilerReport:
    """Profiler report."""
    total_time: float = 0.0
    time_records: Dict[str, TimeRecord] = field(default_factory=dict)
    memory_records: Dict[str, MemoryRecord] = field(default_factory=dict)
    operation_records: Dict[str, OperationRecord] = field(default_factory=dict)
    throughput_records: Dict[str, ThroughputRecord] = field(default_factory=dict)
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# TIMER
# =============================================================================

class Timer:
    """Simple timer context manager."""

    def __init__(self, name: str = ""):
        self.name = name
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0

    def __enter__(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time

    def start(self) -> None:
        """Start timer."""
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        """Stop timer and return duration."""
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        return self.duration


# =============================================================================
# PROFILER COMPONENTS
# =============================================================================

class TimeProfiler:
    """Time profiler component."""

    def __init__(self):
        self._records: Dict[str, TimeRecord] = {}
        self._active_timers: Dict[str, float] = {}

    def start(self, name: str) -> None:
        """Start timing a section."""
        self._active_timers[name] = time.perf_counter()

    def stop(self, name: str) -> float:
        """Stop timing a section."""
        if name not in self._active_timers:
            return 0.0

        start = self._active_timers.pop(name)
        end = time.perf_counter()
        duration = end - start

        if name not in self._records:
            self._records[name] = TimeRecord(name=name)

        record = self._records[name]
        record.call_count += 1
        record.total_time += duration
        record.min_time = min(record.min_time, duration)
        record.max_time = max(record.max_time, duration)
        record.avg_time = record.total_time / record.call_count
        record.duration = duration

        return duration

    def get_records(self) -> Dict[str, TimeRecord]:
        """Get all time records."""
        return self._records.copy()

    def reset(self) -> None:
        """Reset all records."""
        self._records.clear()
        self._active_timers.clear()


class MemoryProfiler:
    """Memory profiler component."""

    def __init__(self):
        self._records: Dict[str, MemoryRecord] = {}
        self._snapshots: Dict[str, int] = {}

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import sys
            return sum(sys.getsizeof(obj) for obj in gc.get_objects()[:1000])
        except:
            return 0

    def snapshot(self, name: str) -> int:
        """Take memory snapshot."""
        current = self._get_memory_usage()
        self._snapshots[name] = current

        if name not in self._records:
            self._records[name] = MemoryRecord(name=name)

        record = self._records[name]
        record.current = current
        record.peak = max(record.peak, current)

        return current

    def compare(self, name1: str, name2: str) -> int:
        """Compare two snapshots."""
        if name1 not in self._snapshots or name2 not in self._snapshots:
            return 0
        return self._snapshots[name2] - self._snapshots[name1]

    def get_records(self) -> Dict[str, MemoryRecord]:
        """Get all memory records."""
        return self._records.copy()

    def reset(self) -> None:
        """Reset all records."""
        self._records.clear()
        self._snapshots.clear()


class OperationProfiler:
    """Operation counter component."""

    def __init__(self):
        self._records: Dict[str, OperationRecord] = {}

    def count(
        self,
        name: str,
        operation_type: OperationType = OperationType.CUSTOM,
        duration: float = 0.0
    ) -> None:
        """Count an operation."""
        if name not in self._records:
            self._records[name] = OperationRecord(
                name=name,
                operation_type=operation_type
            )

        record = self._records[name]
        record.count += 1
        record.total_time += duration
        record.avg_time = record.total_time / record.count

    def get_records(self) -> Dict[str, OperationRecord]:
        """Get all operation records."""
        return self._records.copy()

    def reset(self) -> None:
        """Reset all records."""
        self._records.clear()


class ThroughputProfiler:
    """Throughput measurement component."""

    def __init__(self):
        self._records: Dict[str, ThroughputRecord] = {}
        self._start_times: Dict[str, float] = {}
        self._item_counts: Dict[str, int] = {}
        self._byte_counts: Dict[str, int] = {}

    def start(self, name: str) -> None:
        """Start throughput measurement."""
        self._start_times[name] = time.perf_counter()
        self._item_counts[name] = 0
        self._byte_counts[name] = 0

    def add_items(self, name: str, count: int, bytes_size: int = 0) -> None:
        """Add processed items."""
        if name not in self._item_counts:
            self._item_counts[name] = 0
            self._byte_counts[name] = 0

        self._item_counts[name] += count
        self._byte_counts[name] += bytes_size

    def stop(self, name: str) -> ThroughputRecord:
        """Stop and compute throughput."""
        if name not in self._start_times:
            return ThroughputRecord(name=name)

        elapsed = time.perf_counter() - self._start_times[name]
        items = self._item_counts.get(name, 0)
        bytes_size = self._byte_counts.get(name, 0)

        record = ThroughputRecord(
            name=name,
            items_processed=items,
            time_elapsed=elapsed,
            items_per_second=items / elapsed if elapsed > 0 else 0,
            bytes_processed=bytes_size,
            bytes_per_second=bytes_size / elapsed if elapsed > 0 else 0
        )

        self._records[name] = record
        return record

    def get_records(self) -> Dict[str, ThroughputRecord]:
        """Get all throughput records."""
        return self._records.copy()

    def reset(self) -> None:
        """Reset all records."""
        self._records.clear()
        self._start_times.clear()
        self._item_counts.clear()
        self._byte_counts.clear()


# =============================================================================
# PROFILER ENGINE
# =============================================================================

class ProfilerEngine:
    """
    Profiler Engine for BAEL.

    Comprehensive performance profiling for ML pipelines.
    """

    def __init__(self, config: Optional[ProfilerConfig] = None):
        self.config = config or ProfilerConfig()
        self._time_profiler = TimeProfiler()
        self._memory_profiler = MemoryProfiler()
        self._operation_profiler = OperationProfiler()
        self._throughput_profiler = ThroughputProfiler()
        self._state = ProfilerState.IDLE
        self._global_start: Optional[float] = None

    def start(self) -> None:
        """Start profiling session."""
        self._state = ProfilerState.RUNNING
        self._global_start = time.perf_counter()

    def stop(self) -> None:
        """Stop profiling session."""
        self._state = ProfilerState.STOPPED

    def pause(self) -> None:
        """Pause profiling."""
        self._state = ProfilerState.PAUSED

    def resume(self) -> None:
        """Resume profiling."""
        if self._state == ProfilerState.PAUSED:
            self._state = ProfilerState.RUNNING

    def time_start(self, name: str) -> None:
        """Start timing a section."""
        if self._state == ProfilerState.RUNNING and self.config.track_time:
            self._time_profiler.start(name)

    def time_stop(self, name: str) -> float:
        """Stop timing a section."""
        if self._state == ProfilerState.RUNNING and self.config.track_time:
            return self._time_profiler.stop(name)
        return 0.0

    def time(self, name: str) -> 'ProfilerContext':
        """Context manager for timing."""
        return ProfilerContext(self, name)

    def memory_snapshot(self, name: str) -> int:
        """Take memory snapshot."""
        if self._state == ProfilerState.RUNNING and self.config.track_memory:
            return self._memory_profiler.snapshot(name)
        return 0

    def count_operation(
        self,
        name: str,
        operation_type: OperationType = OperationType.CUSTOM,
        duration: float = 0.0
    ) -> None:
        """Count an operation."""
        if self._state == ProfilerState.RUNNING and self.config.track_operations:
            self._operation_profiler.count(name, operation_type, duration)

    def throughput_start(self, name: str) -> None:
        """Start throughput measurement."""
        if self._state == ProfilerState.RUNNING and self.config.track_throughput:
            self._throughput_profiler.start(name)

    def throughput_add(self, name: str, count: int, bytes_size: int = 0) -> None:
        """Add items to throughput measurement."""
        if self._state == ProfilerState.RUNNING and self.config.track_throughput:
            self._throughput_profiler.add_items(name, count, bytes_size)

    def throughput_stop(self, name: str) -> Optional[ThroughputRecord]:
        """Stop throughput measurement."""
        if self._state == ProfilerState.RUNNING and self.config.track_throughput:
            return self._throughput_profiler.stop(name)
        return None

    def profile(self, func: Callable) -> Callable:
        """Decorator to profile a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = func.__name__
            self.time_start(name)
            self.memory_snapshot(f"{name}_before")

            result = func(*args, **kwargs)

            duration = self.time_stop(name)
            self.memory_snapshot(f"{name}_after")
            self.count_operation(name, OperationType.CUSTOM, duration)

            return result
        return wrapper

    async def aprofile(self, coro: Callable) -> Callable:
        """Decorator to profile an async function."""
        @wraps(coro)
        async def wrapper(*args, **kwargs):
            name = coro.__name__
            self.time_start(name)

            result = await coro(*args, **kwargs)

            duration = self.time_stop(name)
            self.count_operation(name, OperationType.CUSTOM, duration)

            return result
        return wrapper

    def generate_report(self) -> ProfilerReport:
        """Generate profiling report."""
        total_time = 0.0
        if self._global_start is not None:
            total_time = time.perf_counter() - self._global_start

        report = ProfilerReport(
            total_time=total_time,
            time_records=self._time_profiler.get_records(),
            memory_records=self._memory_profiler.get_records(),
            operation_records=self._operation_profiler.get_records(),
            throughput_records=self._throughput_profiler.get_records()
        )

        for name, record in report.time_records.items():
            if record.avg_time * 1000 > self.config.time_threshold_ms:
                report.bottlenecks.append(f"Time: {name} ({record.avg_time * 1000:.2f}ms)")

        for name, record in report.memory_records.items():
            if record.peak / (1024 * 1024) > self.config.memory_threshold_mb:
                report.bottlenecks.append(f"Memory: {name} ({record.peak / (1024 * 1024):.2f}MB)")

        if report.bottlenecks:
            report.recommendations.append("Consider optimizing identified bottlenecks")
            report.recommendations.append("Profile with more granularity around slow sections")

        return report

    def print_report(self) -> None:
        """Print profiling report to console."""
        report = self.generate_report()

        print("\n" + "=" * 60)
        print("PROFILER REPORT")
        print("=" * 60)

        print(f"\nTotal Time: {report.total_time:.4f}s")

        if report.time_records:
            print("\n--- Time Profile ---")
            sorted_times = sorted(
                report.time_records.values(),
                key=lambda r: r.total_time,
                reverse=True
            )
            for record in sorted_times[:10]:
                print(f"  {record.name}: {record.total_time:.4f}s "
                      f"({record.call_count} calls, avg {record.avg_time * 1000:.2f}ms)")

        if report.operation_records:
            print("\n--- Operations ---")
            for name, record in report.operation_records.items():
                print(f"  {name}: {record.count} ops, {record.total_time:.4f}s total")

        if report.throughput_records:
            print("\n--- Throughput ---")
            for name, record in report.throughput_records.items():
                print(f"  {name}: {record.items_per_second:.2f} items/s")

        if report.bottlenecks:
            print("\n--- Bottlenecks ---")
            for bottleneck in report.bottlenecks:
                print(f"  ⚠ {bottleneck}")

        print("\n" + "=" * 60)

    def reset(self) -> None:
        """Reset all profilers."""
        self._time_profiler.reset()
        self._memory_profiler.reset()
        self._operation_profiler.reset()
        self._throughput_profiler.reset()
        self._state = ProfilerState.IDLE
        self._global_start = None


class ProfilerContext:
    """Context manager for profiling."""

    def __init__(self, profiler: ProfilerEngine, name: str):
        self._profiler = profiler
        self._name = name

    def __enter__(self) -> 'ProfilerContext':
        self._profiler.time_start(self._name)
        return self

    def __exit__(self, *args) -> None:
        self._profiler.time_stop(self._name)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Profiler Engine."""
    print("=" * 70)
    print("BAEL - PROFILER ENGINE DEMO")
    print("Comprehensive Performance Profiling for ML Pipelines")
    print("=" * 70)
    print()

    profiler = ProfilerEngine()
    profiler.start()

    # 1. Basic Time Profiling
    print("1. BASIC TIME PROFILING:")
    print("-" * 40)

    profiler.time_start("operation_1")
    time.sleep(0.05)
    duration = profiler.time_stop("operation_1")

    print(f"   Operation 1 duration: {duration * 1000:.2f}ms")
    print()

    # 2. Context Manager Timing
    print("2. CONTEXT MANAGER TIMING:")
    print("-" * 40)

    with profiler.time("operation_2"):
        time.sleep(0.03)

    records = profiler._time_profiler.get_records()
    print(f"   Operation 2 duration: {records['operation_2'].duration * 1000:.2f}ms")
    print()

    # 3. Multiple Calls
    print("3. MULTIPLE CALLS PROFILING:")
    print("-" * 40)

    for i in range(5):
        profiler.time_start("repeated_op")
        time.sleep(0.01 + i * 0.005)
        profiler.time_stop("repeated_op")

    record = profiler._time_profiler.get_records()["repeated_op"]
    print(f"   Calls: {record.call_count}")
    print(f"   Total: {record.total_time * 1000:.2f}ms")
    print(f"   Avg: {record.avg_time * 1000:.2f}ms")
    print(f"   Min: {record.min_time * 1000:.2f}ms")
    print(f"   Max: {record.max_time * 1000:.2f}ms")
    print()

    # 4. Memory Profiling
    print("4. MEMORY PROFILING:")
    print("-" * 40)

    profiler.memory_snapshot("before_alloc")
    data = [i for i in range(10000)]
    profiler.memory_snapshot("after_alloc")

    diff = profiler._memory_profiler.compare("before_alloc", "after_alloc")
    print(f"   Memory difference: {diff} bytes")
    print()

    # 5. Operation Counting
    print("5. OPERATION COUNTING:")
    print("-" * 40)

    for i in range(100):
        profiler.count_operation("forward_pass", OperationType.FORWARD, 0.001)

    for i in range(100):
        profiler.count_operation("backward_pass", OperationType.BACKWARD, 0.002)

    ops = profiler._operation_profiler.get_records()
    print(f"   Forward passes: {ops['forward_pass'].count}")
    print(f"   Backward passes: {ops['backward_pass'].count}")
    print()

    # 6. Throughput Measurement
    print("6. THROUGHPUT MEASUREMENT:")
    print("-" * 40)

    profiler.throughput_start("data_processing")

    for batch in range(10):
        time.sleep(0.01)
        profiler.throughput_add("data_processing", 32, 32 * 1024)

    throughput = profiler.throughput_stop("data_processing")
    print(f"   Items processed: {throughput.items_processed}")
    print(f"   Time elapsed: {throughput.time_elapsed:.3f}s")
    print(f"   Throughput: {throughput.items_per_second:.2f} items/s")
    print(f"   Bandwidth: {throughput.bytes_per_second / 1024:.2f} KB/s")
    print()

    # 7. Function Decorator
    print("7. FUNCTION DECORATOR:")
    print("-" * 40)

    @profiler.profile
    def sample_function():
        total = 0
        for i in range(1000):
            total += i
        return total

    result = sample_function()
    result = sample_function()
    result = sample_function()

    record = profiler._time_profiler.get_records()["sample_function"]
    print(f"   Function called: {record.call_count} times")
    print(f"   Total time: {record.total_time * 1000:.2f}ms")
    print()

    # 8. Timer Utility
    print("8. TIMER UTILITY:")
    print("-" * 40)

    timer = Timer("direct_timer")
    with timer:
        time.sleep(0.02)

    print(f"   Timer duration: {timer.duration * 1000:.2f}ms")
    print()

    # 9. Profiler Report
    print("9. PROFILER REPORT:")
    print("-" * 40)

    report = profiler.generate_report()

    print(f"   Total profiling time: {report.total_time:.4f}s")
    print(f"   Time records: {len(report.time_records)}")
    print(f"   Memory records: {len(report.memory_records)}")
    print(f"   Operation records: {len(report.operation_records)}")
    print(f"   Throughput records: {len(report.throughput_records)}")
    print()

    # 10. Full Report
    print("10. FULL REPORT:")
    print("-" * 40)

    profiler.stop()
    profiler.print_report()
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Profiler Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
