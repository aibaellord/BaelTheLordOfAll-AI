"""
Advanced Debugging & Diagnostics System for BAEL

Provides request tracing, call stacks, memory profiling,
performance bottleneck identification, and system health diagnostics.
"""

import gc
import inspect
import json
import logging
import sys
import threading
import time
import traceback
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiagnosticLevel(Enum):
    """Diagnostic detail levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    VERBOSE = "verbose"
    FULL = "full"


@dataclass
class StackFrame:
    """Stack frame information"""
    function_name: str
    file_path: str
    line_number: int
    locals: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function": self.function_name,
            "file": self.file_path,
            "line": self.line_number,
            "locals": self.locals
        }


@dataclass
class CallStack:
    """Complete call stack"""
    thread_id: int
    thread_name: str
    frames: List[StackFrame] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "thread_name": self.thread_name,
            "frames": [f.to_dict() for f in self.frames],
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: datetime
    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    percent: float
    process_memory_mb: float
    objects_count: int
    top_objects: List[Tuple[str, int]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_mb": self.total_memory_mb,
            "available_mb": self.available_memory_mb,
            "used_mb": self.used_memory_mb,
            "percent": self.percent,
            "process_mb": self.process_memory_mb,
            "objects": self.objects_count,
            "top_objects": self.top_objects
        }


@dataclass
class PerformanceProfile:
    """Performance profile for function/operation"""
    name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    errors: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "call_count": self.call_count,
            "total_time_ms": round(self.total_time_ms, 3),
            "min_time_ms": round(self.min_time_ms, 3),
            "max_time_ms": round(self.max_time_ms, 3),
            "avg_time_ms": round(self.avg_time_ms, 3),
            "errors": self.errors,
            "last_error": self.last_error
        }


@dataclass
class DebugSession:
    """Debug session information"""
    session_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    events: deque = field(default_factory=lambda: deque(maxlen=10000))
    issues_found: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class CallStackCapture:
    """Captures call stacks for debugging"""

    @staticmethod
    def capture_current() -> CallStack:
        """Capture current call stack"""
        thread = threading.current_thread()
        frame = sys._getframe()
        frames = []

        while frame:
            stack_frame = StackFrame(
                function_name=frame.f_code.co_name,
                file_path=frame.f_code.co_filename,
                line_number=frame.f_lineno,
                locals={
                    k: repr(v)[:100] for k, v in frame.f_locals.items()
                    if not k.startswith('_')
                }
            )
            frames.append(stack_frame)
            frame = frame.f_back

        return CallStack(
            thread_id=thread.ident,
            thread_name=thread.name,
            frames=frames[::-1]  # Reverse to show bottom-to-top
        )

    @staticmethod
    def get_all_stacks() -> List[CallStack]:
        """Get call stacks for all threads"""
        stacks = []
        for thread_id, frame in sys._current_frames().items():
            thread = threading.current_thread()
            frames = []

            current_frame = frame
            while current_frame:
                stack_frame = StackFrame(
                    function_name=current_frame.f_code.co_name,
                    file_path=current_frame.f_code.co_filename,
                    line_number=current_frame.f_lineno
                )
                frames.append(stack_frame)
                current_frame = current_frame.f_back

            stacks.append(CallStack(
                thread_id=thread_id,
                thread_name=getattr(thread, 'name', f'Thread-{thread_id}'),
                frames=frames[::-1]
            ))

        return stacks


class MemoryProfiler:
    """Profiles memory usage"""

    def __init__(self):
        self.snapshots: deque = deque(maxlen=100)
        self.process = psutil.Process()

    def take_snapshot(self, level: DiagnosticLevel = DiagnosticLevel.BASIC) -> MemorySnapshot:
        """Take memory snapshot"""
        memory_info = psutil.virtual_memory()
        process_memory = self.process.memory_info()

        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            total_memory_mb=memory_info.total / (1024 * 1024),
            available_memory_mb=memory_info.available / (1024 * 1024),
            used_memory_mb=memory_info.used / (1024 * 1024),
            percent=memory_info.percent,
            process_memory_mb=process_memory.rss / (1024 * 1024),
            objects_count=len(gc.get_objects())
        )

        # Get top objects if verbose
        if level in (DiagnosticLevel.DETAILED, DiagnosticLevel.VERBOSE, DiagnosticLevel.FULL):
            type_counts = defaultdict(int)
            for obj in gc.get_objects():
                type_counts[type(obj).__name__] += 1

            snapshot.top_objects = sorted(
                type_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

        self.snapshots.append(snapshot)
        return snapshot

    def get_memory_trend(self) -> Dict[str, Any]:
        """Get memory usage trend"""
        if not self.snapshots:
            return {}

        snapshots = list(self.snapshots)
        used_values = [s.used_memory_mb for s in snapshots]

        return {
            "current": snapshots[-1].used_memory_mb,
            "min": min(used_values),
            "max": max(used_values),
            "trend": "increasing" if used_values[-1] > used_values[0] else "decreasing",
            "snapshots": len(snapshots)
        }


class PerformanceProfiler:
    """Profiles performance of operations"""

    def __init__(self):
        self.profiles: Dict[str, PerformanceProfile] = {}

    @contextmanager
    def profile(self, name: str):
        """Context manager for profiling"""
        start_time = time.time()

        if name not in self.profiles:
            self.profiles[name] = PerformanceProfile(name)

        profile = self.profiles[name]
        profile.call_count += 1

        try:
            yield profile
        except Exception as e:
            profile.errors += 1
            profile.last_error = str(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            profile.total_time_ms += duration_ms
            profile.min_time_ms = min(profile.min_time_ms, duration_ms)
            profile.max_time_ms = max(profile.max_time_ms, duration_ms)
            profile.avg_time_ms = profile.total_time_ms / profile.call_count

    def get_profile(self, name: str) -> Optional[PerformanceProfile]:
        """Get performance profile"""
        return self.profiles.get(name)

    def get_all_profiles(self) -> List[PerformanceProfile]:
        """Get all profiles"""
        return list(self.profiles.values())

    def find_bottlenecks(self, threshold_ms: float = 100) -> List[PerformanceProfile]:
        """Find performance bottlenecks"""
        return [p for p in self.profiles.values() if p.avg_time_ms > threshold_ms]


class Debugger:
    """Main debugger for system diagnostics"""

    def __init__(self):
        self.sessions: Dict[str, DebugSession] = {}
        self.stack_capturer = CallStackCapture()
        self.memory_profiler = MemoryProfiler()
        self.performance_profiler = PerformanceProfiler()
        self.breakpoints: Dict[str, Callable] = {}

    def start_session(self, name: str) -> str:
        """Start debug session"""
        import uuid
        session_id = str(uuid.uuid4())

        session = DebugSession(
            session_id=session_id,
            name=name,
            start_time=datetime.now()
        )

        self.sessions[session_id] = session
        logger.info(f"Started debug session: {name} ({session_id})")

        return session_id

    def end_session(self, session_id: str) -> Optional[DebugSession]:
        """End debug session"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        session.end_time = datetime.now()
        session.duration_seconds = (session.end_time - session.start_time).total_seconds()

        logger.info(f"Ended debug session: {session.name} ({session.duration_seconds:.2f}s)")

        return session

    def log_event(self, session_id: str, event_type: str, data: Dict[str, Any]):
        """Log event in session"""
        session = self.sessions.get(session_id)
        if not session:
            return

        session.events.append({
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    def set_breakpoint(self, condition: Callable, action: Callable):
        """Set breakpoint"""
        breakpoint_id = f"bp_{len(self.breakpoints)}"
        self.breakpoints[breakpoint_id] = (condition, action)
        return breakpoint_id

    def check_breakpoints(self, context: Dict[str, Any]) -> List[str]:
        """Check if any breakpoints are triggered"""
        triggered = []

        for bp_id, (condition, action) in self.breakpoints.items():
            try:
                if condition(context):
                    action(context)
                    triggered.append(bp_id)
            except Exception as e:
                logger.error(f"Error in breakpoint: {e}")

        return triggered

    def get_system_diagnostics(self, level: DiagnosticLevel = DiagnosticLevel.BASIC) -> Dict[str, Any]:
        """Get comprehensive system diagnostics"""
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "memory": self.memory_profiler.take_snapshot(level).to_dict(),
            "memory_trend": self.memory_profiler.get_memory_trend(),
            "call_stacks": [s.to_dict() for s in self.stack_capturer.get_all_stacks()],
            "performance_profiles": [p.to_dict() for p in self.performance_profiler.get_all_profiles()],
            "bottlenecks": [p.to_dict() for p in self.performance_profiler.find_bottlenecks()],
            "active_sessions": len([s for s in self.sessions.values() if s.end_time is None])
        }

        return diagnostics

    def generate_diagnostics_report(self, session_id: str) -> Dict[str, Any]:
        """Generate comprehensive diagnostics report"""
        session = self.sessions.get(session_id)
        if not session:
            return {}

        return {
            "session": {
                "id": session.session_id,
                "name": session.name,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "duration_seconds": session.duration_seconds
            },
            "events_count": len(session.events),
            "issues_found": session.issues_found,
            "diagnostics": session.diagnostics,
            "timestamp": datetime.now().isoformat()
        }

    def analyze_crash(self, exc_info: Tuple) -> Dict[str, Any]:
        """Analyze crash information"""
        exc_type, exc_value, exc_traceback = exc_info

        stack_frames = []
        tb = exc_traceback
        while tb:
            frame = tb.tb_frame
            stack_frames.append({
                "file": frame.f_code.co_filename,
                "function": frame.f_code.co_name,
                "line": tb.tb_lineno,
                "locals": {k: repr(v)[:100] for k, v in frame.f_locals.items() if not k.startswith('_')}
            })
            tb = tb.tb_next

        return {
            "exception_type": exc_type.__name__,
            "exception_message": str(exc_value),
            "stack_frames": stack_frames,
            "memory_state": self.memory_profiler.take_snapshot(DiagnosticLevel.DETAILED).to_dict(),
            "system_diagnostics": self.get_system_diagnostics(DiagnosticLevel.VERBOSE),
            "timestamp": datetime.now().isoformat()
        }


class IssueDetector:
    """Detects common issues and problems"""

    def __init__(self, debugger: Debugger):
        self.debugger = debugger

    def detect_memory_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks"""
        trends = list(self.debugger.memory_profiler.snapshots)
        if len(trends) < 2:
            return []

        leaks = []
        # Check if memory is continuously increasing
        for i in range(len(trends) - 1):
            if trends[i+1].used_memory_mb > trends[i].used_memory_mb * 1.5:
                leaks.append({
                    "type": "memory_increase",
                    "from": trends[i].timestamp.isoformat(),
                    "to": trends[i+1].timestamp.isoformat(),
                    "increase_mb": trends[i+1].used_memory_mb - trends[i].used_memory_mb
                })

        return leaks

    def detect_performance_issues(self) -> List[Dict[str, Any]]:
        """Detect performance issues"""
        issues = []

        # Check for slow operations
        slow_ops = self.debugger.performance_profiler.find_bottlenecks(threshold_ms=1000)
        for op in slow_ops:
            issues.append({
                "type": "slow_operation",
                "name": op.name,
                "avg_time_ms": op.avg_time_ms,
                "max_time_ms": op.max_time_ms,
                "call_count": op.call_count
            })

        return issues

    def detect_errors(self) -> List[Dict[str, Any]]:
        """Detect error patterns"""
        errors = []

        # Check profiles with errors
        for profile in self.debugger.performance_profiler.get_all_profiles():
            if profile.errors > 0:
                errors.append({
                    "operation": profile.name,
                    "error_count": profile.errors,
                    "last_error": profile.last_error
                })

        return errors


# Global debugger instance
_debugger = None


def get_debugger() -> Debugger:
    """Get global debugger"""
    global _debugger
    if _debugger is None:
        _debugger = Debugger()
    return _debugger


def get_issue_detector() -> IssueDetector:
    """Get issue detector"""
    return IssueDetector(get_debugger())


if __name__ == "__main__":
    logger.info("Debugging & Diagnostics System initialized")
