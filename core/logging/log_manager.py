#!/usr/bin/env python3
"""
BAEL - Log Manager
Advanced logging system for AI agent operations.

Features:
- Multi-level logging
- Structured logging (JSON)
- Log rotation
- Async logging
- Log filtering
- Context propagation
- Log aggregation
- Custom formatters
- Log sinks (console, file, memory)
- Correlation IDs
- Performance logging
"""

import asyncio
import io
import json
import os
import sys
import threading
import time
import traceback
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, TextIO, Tuple, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LogLevel(IntEnum):
    """Log levels with numeric values."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    FATAL = 60


class LogFormat(Enum):
    """Log output formats."""
    TEXT = "text"
    JSON = "json"
    COMPACT = "compact"
    DETAILED = "detailed"


class SinkType(Enum):
    """Log sink types."""
    CONSOLE = "console"
    FILE = "file"
    MEMORY = "memory"
    ASYNC = "async"
    NULL = "null"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LogRecord:
    """A single log record."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    level: LogLevel = LogLevel.INFO
    message: str = ""
    logger_name: str = "root"

    # Context
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None

    # Source
    module: str = ""
    function: str = ""
    line_number: int = 0

    # Data
    extra: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    stack_trace: Optional[str] = None

    # Performance
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "message": self.message,
            "logger_name": self.logger_name,
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "extra": self.extra,
            "exception": self.exception,
            "stack_trace": self.stack_trace,
            "duration_ms": self.duration_ms
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class LogConfig:
    """Logger configuration."""
    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.TEXT
    include_timestamp: bool = True
    include_source: bool = True
    include_correlation: bool = True
    max_message_length: int = 10000
    async_mode: bool = False


@dataclass
class LogStats:
    """Logging statistics."""
    total_logs: int = 0
    logs_by_level: Dict[str, int] = field(default_factory=dict)
    errors_count: int = 0
    avg_processing_time_ms: float = 0.0
    dropped_logs: int = 0


@dataclass
class FilterResult:
    """Filter result."""
    should_log: bool = True
    modified_record: Optional[LogRecord] = None


# =============================================================================
# FORMATTERS
# =============================================================================

class LogFormatter(ABC):
    """Abstract log formatter."""

    @abstractmethod
    def format(self, record: LogRecord) -> str:
        pass


class TextFormatter(LogFormatter):
    """Plain text formatter."""

    def __init__(
        self,
        template: Optional[str] = None,
        datefmt: str = "%Y-%m-%d %H:%M:%S"
    ):
        self.template = template or "{timestamp} [{level}] {logger}: {message}"
        self.datefmt = datefmt

    def format(self, record: LogRecord) -> str:
        timestamp = record.timestamp.strftime(self.datefmt)

        result = self.template.format(
            timestamp=timestamp,
            level=record.level.name.ljust(8),
            logger=record.logger_name,
            message=record.message,
            module=record.module,
            function=record.function,
            line=record.line_number
        )

        if record.extra:
            extras = " ".join(f"{k}={v}" for k, v in record.extra.items())
            result += f" | {extras}"

        if record.exception:
            result += f"\n  Exception: {record.exception}"

        if record.stack_trace:
            result += f"\n{record.stack_trace}"

        return result


class JsonFormatter(LogFormatter):
    """JSON formatter."""

    def __init__(self, pretty: bool = False):
        self.pretty = pretty

    def format(self, record: LogRecord) -> str:
        data = record.to_dict()

        if self.pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)


class CompactFormatter(LogFormatter):
    """Compact single-line formatter."""

    def format(self, record: LogRecord) -> str:
        parts = [
            record.timestamp.strftime("%H:%M:%S"),
            record.level.name[0],  # First letter
            record.message[:100]
        ]

        if record.correlation_id:
            parts.append(f"[{record.correlation_id[:8]}]")

        return " ".join(parts)


class DetailedFormatter(LogFormatter):
    """Detailed multi-line formatter."""

    def format(self, record: LogRecord) -> str:
        lines = [
            "=" * 60,
            f"Level:     {record.level.name}",
            f"Time:      {record.timestamp.isoformat()}",
            f"Logger:    {record.logger_name}",
            f"Message:   {record.message}"
        ]

        if record.correlation_id:
            lines.append(f"Corr ID:   {record.correlation_id}")

        if record.module:
            lines.append(f"Source:    {record.module}:{record.function}:{record.line_number}")

        if record.extra:
            lines.append("Extra:")
            for k, v in record.extra.items():
                lines.append(f"  {k}: {v}")

        if record.exception:
            lines.append(f"Exception: {record.exception}")

        if record.stack_trace:
            lines.append("Stack Trace:")
            lines.append(record.stack_trace)

        if record.duration_ms:
            lines.append(f"Duration:  {record.duration_ms:.2f}ms")

        lines.append("=" * 60)
        return "\n".join(lines)


# =============================================================================
# FILTERS
# =============================================================================

class LogFilter(ABC):
    """Abstract log filter."""

    @abstractmethod
    def filter(self, record: LogRecord) -> FilterResult:
        pass


class LevelFilter(LogFilter):
    """Filter by log level."""

    def __init__(self, min_level: LogLevel):
        self.min_level = min_level

    def filter(self, record: LogRecord) -> FilterResult:
        return FilterResult(should_log=record.level >= self.min_level)


class LoggerNameFilter(LogFilter):
    """Filter by logger name pattern."""

    def __init__(self, patterns: List[str], exclude: bool = False):
        self.patterns = patterns
        self.exclude = exclude

    def filter(self, record: LogRecord) -> FilterResult:
        matches = any(
            pattern in record.logger_name or record.logger_name.startswith(pattern)
            for pattern in self.patterns
        )

        if self.exclude:
            return FilterResult(should_log=not matches)
        return FilterResult(should_log=matches)


class RateLimitFilter(LogFilter):
    """Rate limit filter."""

    def __init__(self, max_per_second: int = 100):
        self.max_per_second = max_per_second
        self._counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_per_second))
        self._lock = threading.Lock()

    def filter(self, record: LogRecord) -> FilterResult:
        now = time.time()
        key = f"{record.logger_name}:{record.level.name}"

        with self._lock:
            # Remove old entries
            queue = self._counts[key]
            while queue and queue[0] < now - 1:
                queue.popleft()

            if len(queue) >= self.max_per_second:
                return FilterResult(should_log=False)

            queue.append(now)
            return FilterResult(should_log=True)


class SamplingFilter(LogFilter):
    """Sample logs at a rate."""

    def __init__(self, sample_rate: float = 1.0):
        self.sample_rate = sample_rate
        self._counter = 0
        self._lock = threading.Lock()

    def filter(self, record: LogRecord) -> FilterResult:
        if self.sample_rate >= 1.0:
            return FilterResult(should_log=True)

        with self._lock:
            self._counter += 1
            should_log = (self._counter % int(1 / self.sample_rate)) == 0
            return FilterResult(should_log=should_log)


# =============================================================================
# SINKS
# =============================================================================

class LogSink(ABC):
    """Abstract log sink."""

    @abstractmethod
    def write(self, formatted: str, record: LogRecord) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class ConsoleSink(LogSink):
    """Console output sink."""

    def __init__(
        self,
        stream: Optional[TextIO] = None,
        colorize: bool = True
    ):
        self.stream = stream or sys.stderr
        self.colorize = colorize
        self._lock = threading.Lock()

        self._colors = {
            LogLevel.TRACE: "\033[90m",    # Gray
            LogLevel.DEBUG: "\033[36m",    # Cyan
            LogLevel.INFO: "\033[32m",     # Green
            LogLevel.WARNING: "\033[33m",  # Yellow
            LogLevel.ERROR: "\033[31m",    # Red
            LogLevel.CRITICAL: "\033[35m", # Magenta
            LogLevel.FATAL: "\033[41m",    # Red background
        }
        self._reset = "\033[0m"

    def write(self, formatted: str, record: LogRecord) -> None:
        with self._lock:
            if self.colorize:
                color = self._colors.get(record.level, "")
                self.stream.write(f"{color}{formatted}{self._reset}\n")
            else:
                self.stream.write(f"{formatted}\n")
            self.stream.flush()


class MemorySink(LogSink):
    """In-memory log sink."""

    def __init__(self, max_records: int = 10000):
        self.max_records = max_records
        self._records: deque = deque(maxlen=max_records)
        self._lock = threading.Lock()

    def write(self, formatted: str, record: LogRecord) -> None:
        with self._lock:
            self._records.append((formatted, record))

    def get_records(self) -> List[Tuple[str, LogRecord]]:
        with self._lock:
            return list(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


class FileSink(LogSink):
    """File log sink with rotation."""

    def __init__(
        self,
        filepath: str,
        max_size_mb: float = 10.0,
        max_files: int = 5
    ):
        self.filepath = filepath
        self.max_size = int(max_size_mb * 1024 * 1024)
        self.max_files = max_files

        self._file: Optional[TextIO] = None
        self._current_size = 0
        self._lock = threading.Lock()

        self._open_file()

    def _open_file(self) -> None:
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        self._file = open(self.filepath, 'a', encoding='utf-8')
        self._current_size = self._file.tell()

    def _rotate(self) -> None:
        if self._file:
            self._file.close()

        # Rotate files
        for i in range(self.max_files - 1, 0, -1):
            old_name = f"{self.filepath}.{i}"
            new_name = f"{self.filepath}.{i + 1}"
            if os.path.exists(old_name):
                if i + 1 > self.max_files:
                    os.remove(old_name)
                else:
                    os.rename(old_name, new_name)

        if os.path.exists(self.filepath):
            os.rename(self.filepath, f"{self.filepath}.1")

        self._open_file()

    def write(self, formatted: str, record: LogRecord) -> None:
        with self._lock:
            if self._file is None:
                self._open_file()

            line = formatted + "\n"
            line_size = len(line.encode('utf-8'))

            if self._current_size + line_size > self.max_size:
                self._rotate()

            self._file.write(line)
            self._current_size += line_size

    def flush(self) -> None:
        with self._lock:
            if self._file:
                self._file.flush()

    def close(self) -> None:
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None


class AsyncSink(LogSink):
    """Async buffered sink."""

    def __init__(
        self,
        wrapped_sink: LogSink,
        buffer_size: int = 1000,
        flush_interval: float = 1.0
    ):
        self.wrapped = wrapped_sink
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval

        self._buffer: List[Tuple[str, LogRecord]] = []
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()

    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(self.flush_interval)
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            buffer = self._buffer
            self._buffer = []

        for formatted, record in buffer:
            self.wrapped.write(formatted, record)
        self.wrapped.flush()

    def write(self, formatted: str, record: LogRecord) -> None:
        with self._lock:
            self._buffer.append((formatted, record))

            if len(self._buffer) >= self.buffer_size:
                # Immediate flush
                buffer = self._buffer
                self._buffer = []

        # Flush outside lock
        if 'buffer' in locals():
            for f, r in buffer:
                self.wrapped.write(f, r)
            self.wrapped.flush()

    def flush(self) -> None:
        self._flush_buffer()

    def close(self) -> None:
        self._running = False
        self._flush_buffer()
        self.wrapped.close()


class NullSink(LogSink):
    """Null sink (discards logs)."""

    def write(self, formatted: str, record: LogRecord) -> None:
        pass


# =============================================================================
# CONTEXT
# =============================================================================

class LogContext:
    """Thread-local logging context."""

    _local = threading.local()

    @classmethod
    def get(cls) -> Dict[str, Any]:
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        return cls._local.context

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        ctx = cls.get()
        ctx[key] = value

    @classmethod
    def remove(cls, key: str) -> None:
        ctx = cls.get()
        ctx.pop(key, None)

    @classmethod
    def clear(cls) -> None:
        cls._local.context = {}

    @classmethod
    @contextmanager
    def scope(cls, **kwargs):
        """Context manager for scoped context."""
        old_values = {}
        ctx = cls.get()

        for key, value in kwargs.items():
            if key in ctx:
                old_values[key] = ctx[key]
            ctx[key] = value

        try:
            yield
        finally:
            for key in kwargs:
                if key in old_values:
                    ctx[key] = old_values[key]
                else:
                    ctx.pop(key, None)


# =============================================================================
# LOGGER
# =============================================================================

class Logger:
    """
    Individual logger instance.
    """

    def __init__(
        self,
        name: str,
        manager: 'LogManager',
        config: Optional[LogConfig] = None
    ):
        self.name = name
        self._manager = manager
        self.config = config or LogConfig()

        self._filters: List[LogFilter] = []
        self._extra: Dict[str, Any] = {}

    def add_filter(self, log_filter: LogFilter) -> None:
        """Add a filter."""
        self._filters.append(log_filter)

    def bind(self, **kwargs) -> 'Logger':
        """Create a child logger with bound context."""
        child = Logger(self.name, self._manager, self.config)
        child._filters = self._filters.copy()
        child._extra = {**self._extra, **kwargs}
        return child

    def _create_record(
        self,
        level: LogLevel,
        message: str,
        exc_info: bool = False,
        **kwargs
    ) -> LogRecord:
        """Create a log record."""
        # Get caller info
        frame = sys._getframe(3)  # Skip _create_record, log method, and public method

        record = LogRecord(
            level=level,
            message=message[:self.config.max_message_length],
            logger_name=self.name,
            module=frame.f_code.co_filename,
            function=frame.f_code.co_name,
            line_number=frame.f_lineno,
            extra={**self._extra, **kwargs}
        )

        # Add context
        ctx = LogContext.get()
        if 'correlation_id' in ctx:
            record.correlation_id = ctx['correlation_id']
        if 'request_id' in ctx:
            record.request_id = ctx['request_id']

        # Add exception info
        if exc_info:
            exc = sys.exc_info()
            if exc[0]:
                record.exception = str(exc[1])
                record.stack_trace = ''.join(traceback.format_exception(*exc))

        return record

    def _should_log(self, record: LogRecord) -> bool:
        """Check if record should be logged."""
        if record.level < self.config.level:
            return False

        for f in self._filters:
            result = f.filter(record)
            if not result.should_log:
                return False

        return True

    def _log(self, level: LogLevel, message: str, exc_info: bool = False, **kwargs) -> None:
        """Internal log method."""
        record = self._create_record(level, message, exc_info, **kwargs)

        if not self._should_log(record):
            return

        self._manager.emit(record)

    def trace(self, message: str, **kwargs) -> None:
        self._log(LogLevel.TRACE, message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = True, **kwargs) -> None:
        self._log(LogLevel.ERROR, message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = True, **kwargs) -> None:
        self._log(LogLevel.CRITICAL, message, exc_info=exc_info, **kwargs)

    def fatal(self, message: str, exc_info: bool = True, **kwargs) -> None:
        self._log(LogLevel.FATAL, message, exc_info=exc_info, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with stack trace."""
        self._log(LogLevel.ERROR, message, exc_info=True, **kwargs)

    @contextmanager
    def timed(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log with timing."""
        start = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start) * 1000
            record = self._create_record(level, message, **kwargs)
            record.duration_ms = duration

            if self._should_log(record):
                self._manager.emit(record)


# =============================================================================
# LOG MANAGER
# =============================================================================

class LogManager:
    """
    Log Manager for BAEL.

    Central logging management.
    """

    def __init__(self, config: Optional[LogConfig] = None):
        self.config = config or LogConfig()

        self._loggers: Dict[str, Logger] = {}
        self._sinks: List[Tuple[LogSink, LogFormatter]] = []
        self._global_filters: List[LogFilter] = []

        self._stats = LogStats()
        self._lock = threading.Lock()

        # Default console sink
        self.add_sink(ConsoleSink(), self._get_formatter())

    def _get_formatter(self) -> LogFormatter:
        """Get formatter based on config."""
        if self.config.format == LogFormat.JSON:
            return JsonFormatter()
        elif self.config.format == LogFormat.COMPACT:
            return CompactFormatter()
        elif self.config.format == LogFormat.DETAILED:
            return DetailedFormatter()
        return TextFormatter()

    # -------------------------------------------------------------------------
    # LOGGER MANAGEMENT
    # -------------------------------------------------------------------------

    def get_logger(self, name: str) -> Logger:
        """Get or create a logger."""
        with self._lock:
            if name not in self._loggers:
                self._loggers[name] = Logger(name, self, self.config)
            return self._loggers[name]

    def __getitem__(self, name: str) -> Logger:
        """Get logger by name."""
        return self.get_logger(name)

    # -------------------------------------------------------------------------
    # SINK MANAGEMENT
    # -------------------------------------------------------------------------

    def add_sink(
        self,
        sink: LogSink,
        formatter: Optional[LogFormatter] = None
    ) -> None:
        """Add a log sink."""
        with self._lock:
            self._sinks.append((sink, formatter or self._get_formatter()))

    def remove_sink(self, sink: LogSink) -> None:
        """Remove a log sink."""
        with self._lock:
            self._sinks = [(s, f) for s, f in self._sinks if s != sink]

    def clear_sinks(self) -> None:
        """Remove all sinks."""
        with self._lock:
            for sink, _ in self._sinks:
                sink.close()
            self._sinks.clear()

    # -------------------------------------------------------------------------
    # FILTER MANAGEMENT
    # -------------------------------------------------------------------------

    def add_filter(self, log_filter: LogFilter) -> None:
        """Add a global filter."""
        with self._lock:
            self._global_filters.append(log_filter)

    def remove_filter(self, log_filter: LogFilter) -> None:
        """Remove a global filter."""
        with self._lock:
            self._global_filters = [
                f for f in self._global_filters if f != log_filter
            ]

    # -------------------------------------------------------------------------
    # EMIT
    # -------------------------------------------------------------------------

    def emit(self, record: LogRecord) -> None:
        """Emit a log record to all sinks."""
        start = time.time()

        # Apply global filters
        for f in self._global_filters:
            result = f.filter(record)
            if not result.should_log:
                with self._lock:
                    self._stats.dropped_logs += 1
                return

        # Write to sinks
        with self._lock:
            sinks = self._sinks.copy()

        for sink, formatter in sinks:
            try:
                formatted = formatter.format(record)
                sink.write(formatted, record)
            except Exception:
                pass  # Don't let sink errors crash logging

        # Update stats
        duration = (time.time() - start) * 1000
        with self._lock:
            self._stats.total_logs += 1
            level_name = record.level.name
            self._stats.logs_by_level[level_name] = (
                self._stats.logs_by_level.get(level_name, 0) + 1
            )

            if record.level >= LogLevel.ERROR:
                self._stats.errors_count += 1

            # Rolling average
            n = self._stats.total_logs
            self._stats.avg_processing_time_ms = (
                (self._stats.avg_processing_time_ms * (n - 1) + duration) / n
            )

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def flush(self) -> None:
        """Flush all sinks."""
        with self._lock:
            for sink, _ in self._sinks:
                sink.flush()

    def shutdown(self) -> None:
        """Shutdown logging."""
        self.flush()
        with self._lock:
            for sink, _ in self._sinks:
                sink.close()

    def get_stats(self) -> LogStats:
        """Get logging statistics."""
        with self._lock:
            return LogStats(
                total_logs=self._stats.total_logs,
                logs_by_level=self._stats.logs_by_level.copy(),
                errors_count=self._stats.errors_count,
                avg_processing_time_ms=self._stats.avg_processing_time_ms,
                dropped_logs=self._stats.dropped_logs
            )

    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------

    def configure(
        self,
        level: Optional[LogLevel] = None,
        format: Optional[LogFormat] = None,
        **kwargs
    ) -> None:
        """Configure the log manager."""
        with self._lock:
            if level:
                self.config.level = level
            if format:
                self.config.format = format

            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

            # Update all loggers
            for logger in self._loggers.values():
                logger.config = self.config


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_log_manager: Optional[LogManager] = None


def get_log_manager() -> LogManager:
    """Get the global log manager."""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def get_logger(name: str) -> Logger:
    """Get a logger."""
    return get_log_manager().get_logger(name)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Log Manager."""
    print("=" * 70)
    print("BAEL - LOG MANAGER DEMO")
    print("Advanced Logging System for AI Agents")
    print("=" * 70)
    print()

    # Create manager with console sink already added
    manager = LogManager()

    # 1. Basic Logging
    print("1. BASIC LOGGING:")
    print("-" * 40)

    log = manager.get_logger("demo")
    log.info("This is an info message")
    log.warning("This is a warning")
    log.debug("This won't show (below INFO level)")
    print()

    # 2. Log Levels
    print("2. LOG LEVELS:")
    print("-" * 40)

    manager.configure(level=LogLevel.DEBUG)
    log.debug("Now debug is visible")
    log.trace("Trace still hidden (below DEBUG)")

    manager.configure(level=LogLevel.TRACE)
    log.trace("Now trace is visible too")
    print()

    # 3. Structured Logging
    print("3. STRUCTURED LOGGING:")
    print("-" * 40)

    log.info("User action", user_id=123, action="login", ip="192.168.1.1")
    print()

    # 4. JSON Format
    print("4. JSON FORMAT:")
    print("-" * 40)

    json_manager = LogManager(LogConfig(format=LogFormat.JSON))
    json_log = json_manager.get_logger("json_demo")
    json_log.info("JSON formatted log", key="value")
    print()

    # 5. Bound Logger
    print("5. BOUND LOGGER (Context):")
    print("-" * 40)

    service_log = log.bind(service="user-service", version="1.0")
    service_log.info("Service started")
    service_log.info("Processing request")
    print()

    # 6. Context Scope
    print("6. CONTEXT SCOPE:")
    print("-" * 40)

    with LogContext.scope(correlation_id="abc-123", request_id="req-456"):
        log.info("Inside context scope")

    log.info("Outside context scope")
    print()

    # 7. Exception Logging
    print("7. EXCEPTION LOGGING:")
    print("-" * 40)

    try:
        result = 1 / 0
    except ZeroDivisionError:
        log.exception("Division failed")
    print()

    # 8. Timed Logging
    print("8. TIMED LOGGING:")
    print("-" * 40)

    with log.timed("Operation completed"):
        await asyncio.sleep(0.1)
    print()

    # 9. Memory Sink
    print("9. MEMORY SINK:")
    print("-" * 40)

    mem_manager = LogManager()
    mem_manager.clear_sinks()
    mem_sink = MemorySink(max_records=100)
    mem_manager.add_sink(mem_sink, TextFormatter())

    mem_log = mem_manager.get_logger("memory")
    mem_log.info("First message")
    mem_log.info("Second message")
    mem_log.info("Third message")

    records = mem_sink.get_records()
    print(f"   Records in memory: {len(records)}")
    for formatted, record in records:
        print(f"   - {record.message}")
    print()

    # 10. Filters
    print("10. FILTERS:")
    print("-" * 40)

    filter_manager = LogManager()
    filter_manager.add_filter(LevelFilter(LogLevel.WARNING))
    filter_log = filter_manager.get_logger("filtered")

    print("   With WARNING filter:")
    filter_log.info("This is hidden")
    filter_log.warning("This is visible")
    print()

    # 11. Rate Limiting
    print("11. RATE LIMITING:")
    print("-" * 40)

    rate_manager = LogManager()
    rate_manager.add_filter(RateLimitFilter(max_per_second=3))
    rate_log = rate_manager.get_logger("rated")

    print("   Sending 5 logs (limit 3/sec):")
    for i in range(5):
        rate_log.info(f"Message {i + 1}")
    print()

    # 12. Multiple Formatters
    print("12. MULTIPLE FORMATTERS:")
    print("-" * 40)

    # Show compact format
    compact_manager = LogManager(LogConfig(format=LogFormat.COMPACT))
    compact_log = compact_manager.get_logger("compact")
    print("   Compact format:")
    compact_log.info("Compact message")
    print()

    # 13. Async Sink
    print("13. ASYNC SINK:")
    print("-" * 40)

    base_sink = MemorySink()
    async_sink = AsyncSink(base_sink, buffer_size=10, flush_interval=0.5)

    async_manager = LogManager()
    async_manager.clear_sinks()
    async_manager.add_sink(async_sink, TextFormatter())

    async_log = async_manager.get_logger("async")
    async_log.info("Async message 1")
    async_log.info("Async message 2")

    # Wait for flush
    await asyncio.sleep(0.6)
    print(f"   Buffered records: {len(base_sink.get_records())}")
    async_sink.close()
    print()

    # 14. Detailed Format
    print("14. DETAILED FORMAT:")
    print("-" * 40)

    detailed_manager = LogManager(LogConfig(format=LogFormat.DETAILED))
    detailed_log = detailed_manager.get_logger("detailed")
    detailed_log.info("Detailed message", user="test", action="demo")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total logs: {stats.total_logs}")
    print(f"   By level: {stats.logs_by_level}")
    print(f"   Errors: {stats.errors_count}")
    print(f"   Avg time: {stats.avg_processing_time_ms:.3f}ms")
    print(f"   Dropped: {stats.dropped_logs}")
    print()

    # Cleanup
    manager.shutdown()
    json_manager.shutdown()
    filter_manager.shutdown()
    rate_manager.shutdown()
    compact_manager.shutdown()
    async_manager.shutdown()
    detailed_manager.shutdown()
    mem_manager.shutdown()

    print("=" * 70)
    print("DEMO COMPLETE - Log Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
