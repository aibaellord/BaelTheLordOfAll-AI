#!/usr/bin/env python3
"""
BAEL - Profiling Engine
Performance profiling for agents.

Features:
- CPU profiling
- Memory profiling
- Call tracing
- Hotspot detection
- Profile analysis
"""

import asyncio
import functools
import gc
import linecache
import sys
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
)


T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# =============================================================================
# ENUMS
# =============================================================================

class ProfileType(Enum):
    """Profile types."""
    CPU = "cpu"
    MEMORY = "memory"
    CALL = "call"
    TIME = "time"
    CUSTOM = "custom"


class ProfileState(Enum):
    """Profile states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class SortOrder(Enum):
    """Sort order for results."""
    TIME = "time"
    CALLS = "calls"
    NAME = "name"
    CUMULATIVE = "cumulative"
    MEMORY = "memory"


class AllocationEvent(Enum):
    """Memory allocation events."""
    ALLOC = "alloc"
    FREE = "free"
    REALLOC = "realloc"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ProfileConfig:
    """Profiling configuration."""
    profile_type: ProfileType = ProfileType.TIME
    sample_interval: float = 0.001
    max_depth: int = 50
    include_builtins: bool = False
    track_memory: bool = False


@dataclass
class CallInfo:
    """Information about a function call."""
    function: str = ""
    module: str = ""
    filename: str = ""
    lineno: int = 0
    call_count: int = 0
    total_time: float = 0.0
    own_time: float = 0.0
    callers: Dict[str, int] = field(default_factory=dict)
    callees: Dict[str, int] = field(default_factory=dict)


@dataclass
class MemoryInfo:
    """Memory usage information."""
    current_bytes: int = 0
    peak_bytes: int = 0
    allocation_count: int = 0
    deallocation_count: int = 0
    objects_tracked: int = 0


@dataclass
class MemorySnapshot:
    """Memory snapshot."""
    timestamp: datetime = field(default_factory=datetime.now)
    total_bytes: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_location: Dict[str, int] = field(default_factory=dict)


@dataclass
class HotspotInfo:
    """Hotspot information."""
    function: str = ""
    module: str = ""
    percentage: float = 0.0
    total_time: float = 0.0
    call_count: int = 0


@dataclass
class ProfileResult:
    """Profile result."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    profile_type: ProfileType = ProfileType.TIME
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_time: float = 0.0
    total_calls: int = 0
    functions: Dict[str, CallInfo] = field(default_factory=dict)
    hotspots: List[HotspotInfo] = field(default_factory=list)
    memory: Optional[MemoryInfo] = None


@dataclass
class ProfileStats:
    """Profiling statistics."""
    profiles_run: int = 0
    total_time_profiled: float = 0.0
    functions_tracked: int = 0
    hotspots_found: int = 0


# =============================================================================
# CALL STACK
# =============================================================================

class CallStack:
    """Tracks function call stack."""
    
    def __init__(self):
        self._stack: List[Tuple[str, float]] = []
        self._depth = 0
    
    def push(self, function: str) -> None:
        """Push a function onto the stack."""
        self._stack.append((function, time.perf_counter()))
        self._depth += 1
    
    def pop(self) -> Tuple[str, float]:
        """Pop a function from the stack."""
        if self._stack:
            func, start_time = self._stack.pop()
            self._depth -= 1
            elapsed = time.perf_counter() - start_time
            return func, elapsed
        return "", 0.0
    
    def peek(self) -> Optional[str]:
        """Peek at the top of the stack."""
        if self._stack:
            return self._stack[-1][0]
        return None
    
    @property
    def depth(self) -> int:
        return self._depth
    
    def clear(self) -> None:
        """Clear the stack."""
        self._stack.clear()
        self._depth = 0


# =============================================================================
# FUNCTION PROFILER
# =============================================================================

class FunctionProfiler:
    """Profiles individual functions."""
    
    def __init__(self, config: Optional[ProfileConfig] = None):
        self._config = config or ProfileConfig()
        self._calls: Dict[str, CallInfo] = {}
        self._stack = CallStack()
        self._active = False
    
    def start(self) -> None:
        """Start profiling."""
        self._active = True
    
    def stop(self) -> None:
        """Stop profiling."""
        self._active = False
    
    def record_call(
        self,
        function: str,
        module: str = "",
        filename: str = "",
        lineno: int = 0
    ) -> None:
        """Record a function call start."""
        if not self._active:
            return
        
        caller = self._stack.peek()
        self._stack.push(function)
        
        if function not in self._calls:
            self._calls[function] = CallInfo(
                function=function,
                module=module,
                filename=filename,
                lineno=lineno
            )
        
        self._calls[function].call_count += 1
        
        if caller and caller in self._calls:
            self._calls[caller].callees[function] = self._calls[caller].callees.get(function, 0) + 1
            self._calls[function].callers[caller] = self._calls[function].callers.get(caller, 0) + 1
    
    def record_return(self, function: str) -> None:
        """Record a function return."""
        if not self._active:
            return
        
        func, elapsed = self._stack.pop()
        
        if func == function and function in self._calls:
            self._calls[function].total_time += elapsed
            self._calls[function].own_time += elapsed
            
            caller = self._stack.peek()
            if caller and caller in self._calls:
                self._calls[caller].own_time -= elapsed
    
    def get_results(self) -> Dict[str, CallInfo]:
        """Get profiling results."""
        return dict(self._calls)
    
    def clear(self) -> None:
        """Clear profiling data."""
        self._calls.clear()
        self._stack.clear()


# =============================================================================
# MEMORY PROFILER
# =============================================================================

class MemoryProfiler:
    """Profiles memory usage."""
    
    def __init__(self):
        self._snapshots: List[MemorySnapshot] = []
        self._tracking = False
        self._baseline: Dict[str, int] = {}
    
    def start(self) -> None:
        """Start memory profiling."""
        self._tracking = True
        gc.collect()
        self._take_baseline()
    
    def stop(self) -> None:
        """Stop memory profiling."""
        self._tracking = False
    
    def _take_baseline(self) -> None:
        """Take a baseline snapshot."""
        self._baseline = self._count_objects()
    
    def _count_objects(self) -> Dict[str, int]:
        """Count objects by type."""
        counts: Dict[str, int] = defaultdict(int)
        
        for obj in gc.get_objects():
            type_name = type(obj).__name__
            counts[type_name] += 1
        
        return dict(counts)
    
    def take_snapshot(self) -> MemorySnapshot:
        """Take a memory snapshot."""
        gc.collect()
        
        current = self._count_objects()
        
        snapshot = MemorySnapshot(
            by_type=current
        )
        
        self._snapshots.append(snapshot)
        return snapshot
    
    def get_diff(self) -> Dict[str, int]:
        """Get difference from baseline."""
        current = self._count_objects()
        diff: Dict[str, int] = {}
        
        all_types = set(current.keys()) | set(self._baseline.keys())
        
        for type_name in all_types:
            cur_count = current.get(type_name, 0)
            base_count = self._baseline.get(type_name, 0)
            delta = cur_count - base_count
            
            if delta != 0:
                diff[type_name] = delta
        
        return diff
    
    def get_info(self) -> MemoryInfo:
        """Get memory information."""
        gc.collect()
        
        current = self._count_objects()
        total_objects = sum(current.values())
        
        return MemoryInfo(
            objects_tracked=total_objects,
            allocation_count=len(self._snapshots)
        )
    
    def get_snapshots(self) -> List[MemorySnapshot]:
        """Get all snapshots."""
        return list(self._snapshots)
    
    def clear(self) -> None:
        """Clear profiling data."""
        self._snapshots.clear()
        self._baseline.clear()


# =============================================================================
# PROFILER DECORATOR
# =============================================================================

class ProfileDecorator:
    """Decorator for profiling functions."""
    
    def __init__(self, profiler: FunctionProfiler):
        self._profiler = profiler
    
    def __call__(self, func: F) -> F:
        """Decorate a function for profiling."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            self._profiler.record_call(
                function=func_name,
                module=func.__module__,
                filename=func.__code__.co_filename,
                lineno=func.__code__.co_firstlineno
            )
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                self._profiler.record_return(func_name)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            self._profiler.record_call(
                function=func_name,
                module=func.__module__,
                filename=func.__code__.co_filename,
                lineno=func.__code__.co_firstlineno
            )
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                self._profiler.record_return(func_name)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore


# =============================================================================
# SIMPLE TIMER
# =============================================================================

class SimpleTimer:
    """Simple timer for profiling."""
    
    def __init__(self, name: str = ""):
        self._name = name
        self._start_time: Optional[float] = None
        self._elapsed: float = 0.0
        self._running = False
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def elapsed(self) -> float:
        if self._running and self._start_time:
            return self._elapsed + (time.perf_counter() - self._start_time)
        return self._elapsed
    
    def start(self) -> None:
        """Start the timer."""
        if not self._running:
            self._start_time = time.perf_counter()
            self._running = True
    
    def stop(self) -> float:
        """Stop the timer."""
        if self._running and self._start_time:
            self._elapsed += time.perf_counter() - self._start_time
            self._running = False
        return self._elapsed
    
    def reset(self) -> None:
        """Reset the timer."""
        self._elapsed = 0.0
        self._start_time = None
        self._running = False
    
    def __enter__(self) -> "SimpleTimer":
        self.start()
        return self
    
    def __exit__(self, *args) -> None:
        self.stop()


# =============================================================================
# PROFILE SESSION
# =============================================================================

class ProfileSession:
    """A profiling session."""
    
    def __init__(
        self,
        name: str,
        config: Optional[ProfileConfig] = None
    ):
        self._name = name
        self._config = config or ProfileConfig()
        self._function_profiler = FunctionProfiler(config)
        self._memory_profiler = MemoryProfiler()
        self._state = ProfileState.IDLE
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._result: Optional[ProfileResult] = None
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def state(self) -> ProfileState:
        return self._state
    
    def start(self) -> None:
        """Start the session."""
        self._start_time = datetime.now()
        self._state = ProfileState.RUNNING
        self._function_profiler.start()
        
        if self._config.track_memory:
            self._memory_profiler.start()
    
    def stop(self) -> ProfileResult:
        """Stop the session."""
        self._end_time = datetime.now()
        self._state = ProfileState.STOPPED
        self._function_profiler.stop()
        
        if self._config.track_memory:
            self._memory_profiler.stop()
        
        self._result = self._generate_result()
        return self._result
    
    def pause(self) -> None:
        """Pause the session."""
        self._function_profiler.stop()
        self._state = ProfileState.PAUSED
    
    def resume(self) -> None:
        """Resume the session."""
        self._function_profiler.start()
        self._state = ProfileState.RUNNING
    
    def _generate_result(self) -> ProfileResult:
        """Generate the profile result."""
        functions = self._function_profiler.get_results()
        
        total_time = sum(f.total_time for f in functions.values())
        total_calls = sum(f.call_count for f in functions.values())
        
        hotspots = []
        for func_name, info in sorted(
            functions.items(),
            key=lambda x: x[1].total_time,
            reverse=True
        )[:10]:
            percentage = (info.total_time / total_time * 100) if total_time > 0 else 0
            hotspots.append(HotspotInfo(
                function=func_name,
                module=info.module,
                percentage=percentage,
                total_time=info.total_time,
                call_count=info.call_count
            ))
        
        memory = None
        if self._config.track_memory:
            memory = self._memory_profiler.get_info()
        
        return ProfileResult(
            profile_type=self._config.profile_type,
            start_time=self._start_time or datetime.now(),
            end_time=self._end_time,
            total_time=total_time,
            total_calls=total_calls,
            functions=functions,
            hotspots=hotspots,
            memory=memory
        )
    
    @property
    def result(self) -> Optional[ProfileResult]:
        return self._result
    
    def get_decorator(self) -> ProfileDecorator:
        """Get a decorator for this session."""
        return ProfileDecorator(self._function_profiler)


# =============================================================================
# PROFILING ENGINE
# =============================================================================

class ProfilingEngine:
    """
    Profiling Engine for BAEL.
    
    Performance profiling for agents.
    """
    
    def __init__(self, config: Optional[ProfileConfig] = None):
        self._default_config = config or ProfileConfig()
        self._sessions: Dict[str, ProfileSession] = {}
        self._results: Dict[str, ProfileResult] = {}
        self._timers: Dict[str, SimpleTimer] = {}
        self._stats = ProfileStats()
    
    # ----- Session Management -----
    
    def create_session(
        self,
        name: str,
        config: Optional[ProfileConfig] = None
    ) -> ProfileSession:
        """Create a profiling session."""
        session = ProfileSession(name, config or self._default_config)
        self._sessions[name] = session
        return session
    
    def get_session(self, name: str) -> Optional[ProfileSession]:
        """Get a profiling session."""
        return self._sessions.get(name)
    
    def start_session(self, name: str) -> bool:
        """Start a session."""
        session = self._sessions.get(name)
        if session:
            session.start()
            return True
        return False
    
    def stop_session(self, name: str) -> Optional[ProfileResult]:
        """Stop a session."""
        session = self._sessions.get(name)
        if session:
            result = session.stop()
            self._results[name] = result
            self._stats.profiles_run += 1
            self._stats.total_time_profiled += result.total_time
            self._stats.functions_tracked += len(result.functions)
            self._stats.hotspots_found += len(result.hotspots)
            return result
        return None
    
    def list_sessions(self) -> List[str]:
        """List all sessions."""
        return list(self._sessions.keys())
    
    # ----- Quick Profiling -----
    
    def profile(self, name: str = "default") -> ProfileSession:
        """Quick profile context manager."""
        session = self.create_session(name)
        return session
    
    class ProfileContext:
        """Context manager for profiling."""
        
        def __init__(self, engine: "ProfilingEngine", name: str):
            self._engine = engine
            self._name = name
            self._session: Optional[ProfileSession] = None
        
        def __enter__(self) -> ProfileSession:
            self._session = self._engine.create_session(self._name)
            self._session.start()
            return self._session
        
        def __exit__(self, *args) -> None:
            if self._session:
                self._engine.stop_session(self._name)
    
    def profiling(self, name: str = "default") -> ProfileContext:
        """Get a profile context manager."""
        return self.ProfileContext(self, name)
    
    # ----- Timer Management -----
    
    def timer(self, name: str) -> SimpleTimer:
        """Get or create a timer."""
        if name not in self._timers:
            self._timers[name] = SimpleTimer(name)
        return self._timers[name]
    
    def start_timer(self, name: str) -> SimpleTimer:
        """Start a timer."""
        timer = self.timer(name)
        timer.start()
        return timer
    
    def stop_timer(self, name: str) -> float:
        """Stop a timer and return elapsed time."""
        timer = self._timers.get(name)
        if timer:
            return timer.stop()
        return 0.0
    
    def get_timer_elapsed(self, name: str) -> float:
        """Get elapsed time for a timer."""
        timer = self._timers.get(name)
        if timer:
            return timer.elapsed
        return 0.0
    
    def list_timers(self) -> Dict[str, float]:
        """List all timers and their elapsed times."""
        return {name: timer.elapsed for name, timer in self._timers.items()}
    
    # ----- Function Profiling -----
    
    def profile_function(self, session_name: str = "default") -> ProfileDecorator:
        """Get a function profiling decorator."""
        session = self._sessions.get(session_name)
        
        if not session:
            session = self.create_session(session_name)
        
        return session.get_decorator()
    
    # ----- Results -----
    
    def get_result(self, session_name: str) -> Optional[ProfileResult]:
        """Get a profile result."""
        return self._results.get(session_name)
    
    def get_hotspots(
        self,
        session_name: str,
        limit: int = 10
    ) -> List[HotspotInfo]:
        """Get hotspots from a profile."""
        result = self._results.get(session_name)
        if result:
            return result.hotspots[:limit]
        return []
    
    def get_call_graph(
        self,
        session_name: str,
        function: str
    ) -> Dict[str, Any]:
        """Get call graph for a function."""
        result = self._results.get(session_name)
        if not result:
            return {}
        
        func_info = result.functions.get(function)
        if not func_info:
            return {}
        
        return {
            "function": function,
            "call_count": func_info.call_count,
            "total_time": func_info.total_time,
            "own_time": func_info.own_time,
            "callers": func_info.callers,
            "callees": func_info.callees
        }
    
    def format_result(
        self,
        session_name: str,
        sort_by: SortOrder = SortOrder.TIME,
        limit: int = 20
    ) -> str:
        """Format a profile result as text."""
        result = self._results.get(session_name)
        if not result:
            return f"No result found for session: {session_name}"
        
        lines = [
            f"Profile: {session_name}",
            f"Duration: {result.total_time:.3f}s",
            f"Total Calls: {result.total_calls}",
            "",
            f"{'Function':<50} {'Calls':>10} {'Total':>10} {'Own':>10}",
            "-" * 82
        ]
        
        functions = list(result.functions.values())
        
        if sort_by == SortOrder.TIME:
            functions.sort(key=lambda x: x.total_time, reverse=True)
        elif sort_by == SortOrder.CALLS:
            functions.sort(key=lambda x: x.call_count, reverse=True)
        elif sort_by == SortOrder.NAME:
            functions.sort(key=lambda x: x.function)
        
        for func in functions[:limit]:
            name = func.function[:48] if len(func.function) > 48 else func.function
            lines.append(
                f"{name:<50} {func.call_count:>10} {func.total_time:>10.3f} {func.own_time:>10.3f}"
            )
        
        if result.hotspots:
            lines.extend([
                "",
                "Top Hotspots:",
                "-" * 40
            ])
            for hs in result.hotspots[:5]:
                lines.append(f"  {hs.function}: {hs.percentage:.1f}% ({hs.total_time:.3f}s)")
        
        return "\n".join(lines)
    
    # ----- Stats -----
    
    @property
    def stats(self) -> ProfileStats:
        return self._stats
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "sessions": len(self._sessions),
            "results": len(self._results),
            "timers": len(self._timers),
            "profiles_run": self._stats.profiles_run,
            "total_time_profiled": self._stats.total_time_profiled,
            "functions_tracked": self._stats.functions_tracked,
            "hotspots_found": self._stats.hotspots_found
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Profiling Engine."""
    print("=" * 70)
    print("BAEL - PROFILING ENGINE DEMO")
    print("Performance Profiling for Agents")
    print("=" * 70)
    print()
    
    engine = ProfilingEngine()
    
    # 1. Create a Session
    print("1. CREATE PROFILING SESSION:")
    print("-" * 40)
    
    session = engine.create_session("demo-profile", ProfileConfig(track_memory=True))
    print(f"   Created session: {session.name}")
    print(f"   State: {session.state.value}")
    print()
    
    # 2. Simple Timer
    print("2. SIMPLE TIMER:")
    print("-" * 40)
    
    timer = engine.timer("operation")
    timer.start()
    await asyncio.sleep(0.1)
    elapsed = timer.stop()
    print(f"   Timer elapsed: {elapsed:.3f}s")
    print()
    
    # 3. Timer Context Manager
    print("3. TIMER CONTEXT MANAGER:")
    print("-" * 40)
    
    with engine.timer("context_timer") as t:
        await asyncio.sleep(0.05)
    
    print(f"   Context timer: {t.elapsed:.3f}s")
    print()
    
    # 4. Start/Stop Timer
    print("4. START/STOP TIMER:")
    print("-" * 40)
    
    engine.start_timer("measured_op")
    await asyncio.sleep(0.02)
    duration = engine.stop_timer("measured_op")
    print(f"   Measured duration: {duration:.3f}s")
    print()
    
    # 5. Profile Session
    print("5. PROFILE SESSION:")
    print("-" * 40)
    
    session.start()
    
    profiler = session._function_profiler
    
    profiler.record_call("main", module="demo")
    await asyncio.sleep(0.05)
    
    profiler.record_call("helper1", module="demo")
    await asyncio.sleep(0.02)
    profiler.record_return("helper1")
    
    profiler.record_call("helper2", module="demo")
    await asyncio.sleep(0.03)
    profiler.record_return("helper2")
    
    profiler.record_return("main")
    
    result = session.stop()
    
    print(f"   Total time: {result.total_time:.3f}s")
    print(f"   Total calls: {result.total_calls}")
    print(f"   Functions tracked: {len(result.functions)}")
    print()
    
    # 6. Profile Context Manager
    print("6. PROFILE CONTEXT MANAGER:")
    print("-" * 40)
    
    with engine.profiling("quick-profile") as ps:
        ps._function_profiler.record_call("quick_func")
        await asyncio.sleep(0.01)
        ps._function_profiler.record_return("quick_func")
    
    quick_result = engine.get_result("quick-profile")
    print(f"   Quick profile total time: {quick_result.total_time:.3f}s")
    print()
    
    # 7. Hotspots
    print("7. HOTSPOTS:")
    print("-" * 40)
    
    hotspots = engine.get_hotspots("demo-profile")
    for hs in hotspots:
        print(f"   - {hs.function}: {hs.percentage:.1f}% ({hs.total_time:.3f}s)")
    print()
    
    # 8. Call Graph
    print("8. CALL GRAPH:")
    print("-" * 40)
    
    call_graph = engine.get_call_graph("demo-profile", "main")
    if call_graph:
        print(f"   Function: {call_graph['function']}")
        print(f"   Call count: {call_graph['call_count']}")
        print(f"   Total time: {call_graph['total_time']:.3f}s")
        print(f"   Callees: {call_graph['callees']}")
    print()
    
    # 9. Format Result
    print("9. FORMATTED RESULT:")
    print("-" * 40)
    
    formatted = engine.format_result("demo-profile", limit=10)
    print(formatted)
    print()
    
    # 10. List Timers
    print("10. LIST TIMERS:")
    print("-" * 40)
    
    timers = engine.list_timers()
    for name, elapsed in timers.items():
        print(f"   {name}: {elapsed:.3f}s")
    print()
    
    # 11. List Sessions
    print("11. LIST SESSIONS:")
    print("-" * 40)
    
    sessions = engine.list_sessions()
    for name in sessions:
        s = engine.get_session(name)
        print(f"   {name}: {s.state.value}")
    print()
    
    # 12. Profile with Decorator
    print("12. PROFILE WITH DECORATOR:")
    print("-" * 40)
    
    dec_session = engine.create_session("decorator-profile")
    dec_session.start()
    
    @dec_session.get_decorator()
    def decorated_function():
        time.sleep(0.01)
        return "done"
    
    for _ in range(3):
        decorated_function()
    
    dec_result = dec_session.stop()
    print(f"   Decorated function calls: {dec_result.total_calls}")
    print(f"   Total time: {dec_result.total_time:.3f}s")
    print()
    
    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats
    print(f"   Profiles run: {stats.profiles_run}")
    print(f"   Total time profiled: {stats.total_time_profiled:.3f}s")
    print(f"   Functions tracked: {stats.functions_tracked}")
    print(f"   Hotspots found: {stats.hotspots_found}")
    print()
    
    # 14. Engine Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Profiling Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
