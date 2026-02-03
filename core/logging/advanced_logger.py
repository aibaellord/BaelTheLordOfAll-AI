#!/usr/bin/env python3
"""
BAEL - Advanced Logger System
Comprehensive logging infrastructure with structured logging,
log routing, filtering, formatting, and aggregation.

Features:
- Multiple log levels
- Structured logging
- Log routing
- Formatters (JSON, text, custom)
- Log rotation
- Log filtering
- Context propagation
- Async logging
- Log aggregation
- Metrics integration
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum, auto
from functools import wraps
from pathlib import Path
from threading import Lock, local
from typing import (Any, Awaitable, Callable, Dict, List, Optional, Set,
                    TextIO, Tuple, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LogLevel(IntEnum):
    """Log levels."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    NOTICE = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    FATAL = 60


class OutputType(Enum):
    """Output destination types."""
    CONSOLE = "console"
    FILE = "file"
    MEMORY = "memory"
    CALLBACK = "callback"


class RotationPolicy(Enum):
    """Log rotation policies."""
    SIZE = "size"
    TIME = "time"
    COUNT = "count"
    NONE = "none"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class LogRecord:
    """Log record structure."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    level: LogLevel = LogLevel.INFO
    logger_name: str = "root"
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    source_file: str = ""
    source_line: int = 0
    source_func: str = ""
    trace_id: str = ""
    span_id: str = ""

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    @property
    def level_name(self) -> str:
        return self.level.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "datetime": self.datetime.isoformat(),
            "level": self.level_name,
            "level_value": self.level.value,
            "logger": self.logger_name,
            "message": self.message,
            "context": self.context,
            "extra": self.extra,
            "exception": self.exception,
            "source": {
                "file": self.source_file,
                "line": self.source_line,
                "function": self.source_func
            },
            "trace_id": self.trace_id,
            "span_id": self.span_id
        }


@dataclass
class LogStats:
    """Logging statistics."""
    total_logs: int = 0
    logs_by_level: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    logs_by_logger: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors_count: int = 0
    warnings_count: int = 0
    avg_message_length: float = 0
    first_log_time: Optional[float] = None
    last_log_time: Optional[float] = None


# =============================================================================
# CONTEXT
# =============================================================================

class LogContext:
    """Thread-local log context."""

    _local = local()

    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        return cls._local.context.copy()

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        cls._local.context[key] = value

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        return cls._local.context.get(key, default)

    @classmethod
    def clear(cls) -> None:
        cls._local.context = {}

    @classmethod
    @contextmanager
    def scope(cls, **kwargs):
        """Context manager for scoped context."""
        old_context = cls.get_context()
        try:
            for k, v in kwargs.items():
                cls.set(k, v)
            yield
        finally:
            cls._local.context = old_context


# =============================================================================
# FORMATTERS
# =============================================================================

class LogFormatter(ABC):
    """Abstract log formatter."""

    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """Format a log record."""
        pass


class TextFormatter(LogFormatter):
    """Text log formatter."""

    def __init__(
        self,
        template: str = None,
        timestamp_format: str = "%Y-%m-%d %H:%M:%S.%f",
        include_context: bool = True
    ):
        self.template = template or "[{timestamp}] {level:8} [{logger}] {message}"
        self.timestamp_format = timestamp_format
        self.include_context = include_context

    def format(self, record: LogRecord) -> str:
        timestamp = record.datetime.strftime(self.timestamp_format)[:-3]  # milliseconds

        result = self.template.format(
            timestamp=timestamp,
            level=record.level_name,
            logger=record.logger_name,
            message=record.message,
            record_id=record.record_id,
            source_file=record.source_file,
            source_line=record.source_line,
            source_func=record.source_func,
            trace_id=record.trace_id,
            span_id=record.span_id
        )

        if self.include_context and record.context:
            ctx_str = " ".join(f"{k}={v}" for k, v in record.context.items())
            result += f" | {ctx_str}"

        if record.extra:
            extra_str = " ".join(f"{k}={v}" for k, v in record.extra.items())
            result += f" | {extra_str}"

        if record.exception:
            result += f"\n{record.exception}"

        return result


class JSONFormatter(LogFormatter):
    """JSON log formatter."""

    def __init__(
        self,
        include_all: bool = True,
        pretty: bool = False
    ):
        self.include_all = include_all
        self.pretty = pretty

    def format(self, record: LogRecord) -> str:
        if self.include_all:
            data = record.to_dict()
        else:
            data = {
                "timestamp": record.datetime.isoformat(),
                "level": record.level_name,
                "logger": record.logger_name,
                "message": record.message
            }

            if record.context:
                data["context"] = record.context
            if record.extra:
                data["extra"] = record.extra
            if record.exception:
                data["exception"] = record.exception

        if self.pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)


class ColorFormatter(LogFormatter):
    """Colored console formatter."""

    COLORS = {
        LogLevel.TRACE: "\033[90m",      # Gray
        LogLevel.DEBUG: "\033[36m",      # Cyan
        LogLevel.INFO: "\033[32m",       # Green
        LogLevel.NOTICE: "\033[34m",     # Blue
        LogLevel.WARNING: "\033[33m",    # Yellow
        LogLevel.ERROR: "\033[31m",      # Red
        LogLevel.CRITICAL: "\033[35m",   # Magenta
        LogLevel.FATAL: "\033[41m",      # Red background
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(self, base_formatter: LogFormatter = None):
        self.base_formatter = base_formatter or TextFormatter()

    def format(self, record: LogRecord) -> str:
        text = self.base_formatter.format(record)
        color = self.COLORS.get(record.level, "")

        if record.level >= LogLevel.ERROR:
            return f"{self.BOLD}{color}{text}{self.RESET}"
        return f"{color}{text}{self.RESET}"


# =============================================================================
# FILTERS
# =============================================================================

class LogFilter(ABC):
    """Abstract log filter."""

    @abstractmethod
    def filter(self, record: LogRecord) -> bool:
        """Return True to include, False to exclude."""
        pass


class LevelFilter(LogFilter):
    """Filter by log level."""

    def __init__(
        self,
        min_level: LogLevel = LogLevel.DEBUG,
        max_level: LogLevel = LogLevel.FATAL
    ):
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record: LogRecord) -> bool:
        return self.min_level <= record.level <= self.max_level


class LoggerNameFilter(LogFilter):
    """Filter by logger name pattern."""

    def __init__(self, patterns: List[str], exclude: bool = False):
        self.patterns = [re.compile(p) for p in patterns]
        self.exclude = exclude

    def filter(self, record: LogRecord) -> bool:
        matches = any(p.match(record.logger_name) for p in self.patterns)
        return not matches if self.exclude else matches


class MessageFilter(LogFilter):
    """Filter by message content."""

    def __init__(
        self,
        patterns: List[str],
        exclude: bool = False
    ):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.exclude = exclude

    def filter(self, record: LogRecord) -> bool:
        matches = any(p.search(record.message) for p in self.patterns)
        return not matches if self.exclude else matches


class RateLimitFilter(LogFilter):
    """Rate limit similar messages."""

    def __init__(
        self,
        window: float = 60.0,
        max_count: int = 10
    ):
        self.window = window
        self.max_count = max_count
        self.message_counts: Dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def filter(self, record: LogRecord) -> bool:
        key = f"{record.logger_name}:{record.message[:100]}"
        now = time.time()

        with self._lock:
            timestamps = self.message_counts[key]

            # Remove old timestamps
            while timestamps and timestamps[0] < now - self.window:
                timestamps.popleft()

            if len(timestamps) >= self.max_count:
                return False

            timestamps.append(now)
            return True


# =============================================================================
# HANDLERS
# =============================================================================

class LogHandler(ABC):
    """Abstract log handler."""

    def __init__(
        self,
        formatter: LogFormatter = None,
        filters: List[LogFilter] = None
    ):
        self.formatter = formatter or TextFormatter()
        self.filters = filters or []

    def should_log(self, record: LogRecord) -> bool:
        return all(f.filter(record) for f in self.filters)

    @abstractmethod
    async def emit(self, record: LogRecord) -> None:
        """Emit a log record."""
        pass

    async def close(self) -> None:
        """Close handler resources."""
        pass


class ConsoleHandler(LogHandler):
    """Console log handler."""

    def __init__(
        self,
        stream: TextIO = None,
        formatter: LogFormatter = None,
        filters: List[LogFilter] = None,
        use_colors: bool = True
    ):
        if use_colors and formatter is None:
            formatter = ColorFormatter()

        super().__init__(formatter, filters)
        self.stream = stream or sys.stdout

    async def emit(self, record: LogRecord) -> None:
        if not self.should_log(record):
            return

        try:
            message = self.formatter.format(record)
            self.stream.write(message + "\n")
            self.stream.flush()
        except Exception:
            pass


class FileHandler(LogHandler):
    """File log handler with rotation."""

    def __init__(
        self,
        path: str,
        formatter: LogFormatter = None,
        filters: List[LogFilter] = None,
        rotation: RotationPolicy = RotationPolicy.SIZE,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        max_files: int = 5,
        rotation_interval: int = 86400  # 1 day
    ):
        super().__init__(formatter or TextFormatter(), filters)
        self.path = Path(path)
        self.rotation = rotation
        self.max_size = max_size
        self.max_files = max_files
        self.rotation_interval = rotation_interval

        self._file: Optional[TextIO] = None
        self._size = 0
        self._last_rotation = time.time()
        self._lock = asyncio.Lock()

        self._ensure_directory()

    def _ensure_directory(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _open_file(self) -> None:
        if self._file is None:
            self._file = open(self.path, 'a', encoding='utf-8')
            self._size = self.path.stat().st_size if self.path.exists() else 0

    def _should_rotate(self) -> bool:
        if self.rotation == RotationPolicy.NONE:
            return False

        if self.rotation == RotationPolicy.SIZE:
            return self._size >= self.max_size

        if self.rotation == RotationPolicy.TIME:
            return time.time() - self._last_rotation >= self.rotation_interval

        return False

    def _rotate(self) -> None:
        if self._file:
            self._file.close()
            self._file = None

        # Rotate files
        for i in range(self.max_files - 1, 0, -1):
            src = self.path.with_suffix(f".{i}{self.path.suffix}")
            dst = self.path.with_suffix(f".{i + 1}{self.path.suffix}")

            if src.exists():
                if dst.exists():
                    dst.unlink()
                src.rename(dst)

        # Rename current file
        if self.path.exists():
            new_name = self.path.with_suffix(f".1{self.path.suffix}")
            self.path.rename(new_name)

        self._size = 0
        self._last_rotation = time.time()

    async def emit(self, record: LogRecord) -> None:
        if not self.should_log(record):
            return

        async with self._lock:
            try:
                if self._should_rotate():
                    self._rotate()

                self._open_file()

                message = self.formatter.format(record)
                self._file.write(message + "\n")
                self._file.flush()
                self._size += len(message) + 1

            except Exception as e:
                print(f"Log file error: {e}", file=sys.stderr)

    async def close(self) -> None:
        async with self._lock:
            if self._file:
                self._file.close()
                self._file = None


class MemoryHandler(LogHandler):
    """In-memory log handler."""

    def __init__(
        self,
        max_records: int = 10000,
        formatter: LogFormatter = None,
        filters: List[LogFilter] = None
    ):
        super().__init__(formatter or JSONFormatter(), filters)
        self.max_records = max_records
        self.records: deque = deque(maxlen=max_records)

    async def emit(self, record: LogRecord) -> None:
        if not self.should_log(record):
            return

        self.records.append(record)

    def get_records(
        self,
        level: LogLevel = None,
        logger_name: str = None,
        limit: int = None
    ) -> List[LogRecord]:
        """Get stored records."""
        records = list(self.records)

        if level:
            records = [r for r in records if r.level >= level]

        if logger_name:
            records = [r for r in records if r.logger_name == logger_name]

        if limit:
            records = records[-limit:]

        return records

    def clear(self) -> None:
        """Clear stored records."""
        self.records.clear()


class CallbackHandler(LogHandler):
    """Callback log handler."""

    def __init__(
        self,
        callback: Callable[[LogRecord], Awaitable[None]],
        formatter: LogFormatter = None,
        filters: List[LogFilter] = None
    ):
        super().__init__(formatter or TextFormatter(), filters)
        self.callback = callback

    async def emit(self, record: LogRecord) -> None:
        if not self.should_log(record):
            return

        try:
            await self.callback(record)
        except Exception:
            pass


# =============================================================================
# LOGGER
# =============================================================================

class Logger:
    """Logger instance."""

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.DEBUG,
        handlers: List[LogHandler] = None,
        parent: 'Logger' = None
    ):
        self.name = name
        self.level = level
        self.handlers = handlers or []
        self.parent = parent
        self.propagate = True

    def _create_record(
        self,
        level: LogLevel,
        message: str,
        extra: Dict[str, Any] = None,
        exc_info: bool = False
    ) -> LogRecord:
        """Create a log record."""
        # Get caller info
        frame = sys._getframe(3)
        source_file = frame.f_code.co_filename
        source_line = frame.f_lineno
        source_func = frame.f_code.co_name

        # Get exception info
        exception = None
        if exc_info:
            exception = traceback.format_exc()

        # Get context
        context = LogContext.get_context()

        return LogRecord(
            level=level,
            logger_name=self.name,
            message=message,
            context=context,
            extra=extra or {},
            exception=exception,
            source_file=source_file,
            source_line=source_line,
            source_func=source_func,
            trace_id=context.get("trace_id", ""),
            span_id=context.get("span_id", "")
        )

    async def _log(
        self,
        level: LogLevel,
        message: str,
        extra: Dict[str, Any] = None,
        exc_info: bool = False
    ) -> None:
        """Log a message."""
        if level < self.level:
            return

        record = self._create_record(level, message, extra, exc_info)

        # Emit to handlers
        for handler in self.handlers:
            await handler.emit(record)

        # Propagate to parent
        if self.propagate and self.parent:
            for handler in self.parent.handlers:
                await handler.emit(record)

    def _log_sync(
        self,
        level: LogLevel,
        message: str,
        extra: Dict[str, Any] = None,
        exc_info: bool = False
    ) -> None:
        """Synchronous log (creates task)."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._log(level, message, extra, exc_info))
        except RuntimeError:
            # No event loop, run synchronously
            asyncio.run(self._log(level, message, extra, exc_info))

    # Log methods
    async def trace(self, message: str, **extra):
        await self._log(LogLevel.TRACE, message, extra)

    async def debug(self, message: str, **extra):
        await self._log(LogLevel.DEBUG, message, extra)

    async def info(self, message: str, **extra):
        await self._log(LogLevel.INFO, message, extra)

    async def notice(self, message: str, **extra):
        await self._log(LogLevel.NOTICE, message, extra)

    async def warning(self, message: str, **extra):
        await self._log(LogLevel.WARNING, message, extra)

    async def error(self, message: str, exc_info: bool = False, **extra):
        await self._log(LogLevel.ERROR, message, extra, exc_info)

    async def critical(self, message: str, exc_info: bool = False, **extra):
        await self._log(LogLevel.CRITICAL, message, extra, exc_info)

    async def fatal(self, message: str, exc_info: bool = False, **extra):
        await self._log(LogLevel.FATAL, message, extra, exc_info)

    async def exception(self, message: str, **extra):
        await self._log(LogLevel.ERROR, message, extra, exc_info=True)

    def add_handler(self, handler: LogHandler) -> None:
        """Add a handler."""
        self.handlers.append(handler)

    def remove_handler(self, handler: LogHandler) -> None:
        """Remove a handler."""
        if handler in self.handlers:
            self.handlers.remove(handler)


# =============================================================================
# LOGGER MANAGER
# =============================================================================

class LoggerManager:
    """
    Advanced Logger Manager for BAEL.
    """

    def __init__(self):
        self.loggers: Dict[str, Logger] = {}
        self.root = Logger("root")
        self.handlers: List[LogHandler] = []
        self.default_level = LogLevel.DEBUG

        # Statistics
        self._stats = LogStats()
        self._stats_lock = asyncio.Lock()

        # Default console handler
        self.root.add_handler(ConsoleHandler())

    def get_logger(self, name: str) -> Logger:
        """Get or create a logger."""
        if name in self.loggers:
            return self.loggers[name]

        # Create logger with parent hierarchy
        parts = name.split(".")
        parent = self.root

        for i in range(len(parts)):
            parent_name = ".".join(parts[:i + 1])

            if parent_name not in self.loggers:
                logger = Logger(
                    parent_name,
                    self.default_level,
                    parent=parent
                )
                self.loggers[parent_name] = logger

            parent = self.loggers[parent_name]

        return parent

    def add_handler(self, handler: LogHandler) -> None:
        """Add global handler."""
        self.handlers.append(handler)
        self.root.add_handler(handler)

    def remove_handler(self, handler: LogHandler) -> None:
        """Remove global handler."""
        if handler in self.handlers:
            self.handlers.remove(handler)
        self.root.remove_handler(handler)

    def set_level(self, level: LogLevel, logger_name: str = None) -> None:
        """Set log level."""
        if logger_name:
            logger = self.get_logger(logger_name)
            logger.level = level
        else:
            self.default_level = level
            self.root.level = level

    async def update_stats(self, record: LogRecord) -> None:
        """Update logging statistics."""
        async with self._stats_lock:
            self._stats.total_logs += 1
            self._stats.logs_by_level[record.level_name] += 1
            self._stats.logs_by_logger[record.logger_name] += 1

            if record.level >= LogLevel.ERROR:
                self._stats.errors_count += 1
            elif record.level == LogLevel.WARNING:
                self._stats.warnings_count += 1

            if self._stats.first_log_time is None:
                self._stats.first_log_time = record.timestamp
            self._stats.last_log_time = record.timestamp

            # Update average message length
            n = self._stats.total_logs
            self._stats.avg_message_length = (
                (self._stats.avg_message_length * (n - 1) + len(record.message)) / n
            )

    def get_stats(self) -> LogStats:
        """Get logging statistics."""
        return self._stats

    async def close(self) -> None:
        """Close all handlers."""
        for handler in self.handlers:
            await handler.close()

        for logger in self.loggers.values():
            for handler in logger.handlers:
                await handler.close()


# =============================================================================
# DECORATORS
# =============================================================================

def log_function(
    logger: Logger = None,
    level: LogLevel = LogLevel.DEBUG,
    log_args: bool = True,
    log_result: bool = False,
    log_time: bool = True
):
    """Decorator to log function calls."""
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            manager = LoggerManager()
            logger = manager.get_logger(func.__module__)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()

            msg = f"Calling {func.__name__}"
            if log_args:
                msg += f"(args={args}, kwargs={kwargs})"

            await logger._log(level, msg)

            try:
                result = await func(*args, **kwargs)

                elapsed = time.time() - start
                msg = f"Completed {func.__name__}"

                if log_result:
                    msg += f" -> {result}"
                if log_time:
                    msg += f" ({elapsed:.3f}s)"

                await logger._log(level, msg)
                return result

            except Exception as e:
                elapsed = time.time() - start
                await logger._log(
                    LogLevel.ERROR,
                    f"Failed {func.__name__}: {e} ({elapsed:.3f}s)",
                    exc_info=True
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_manager: Optional[LoggerManager] = None


def get_manager() -> LoggerManager:
    """Get global logger manager."""
    global _manager
    if _manager is None:
        _manager = LoggerManager()
    return _manager


def get_logger(name: str) -> Logger:
    """Get a logger instance."""
    return get_manager().get_logger(name)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Advanced Logger System."""
    print("=" * 70)
    print("BAEL - ADVANCED LOGGER SYSTEM DEMO")
    print("Comprehensive Structured Logging")
    print("=" * 70)
    print()

    manager = LoggerManager()

    # 1. Basic Logging
    print("1. BASIC LOGGING:")
    print("-" * 40)

    logger = manager.get_logger("bael.core")

    await logger.trace("Trace message")
    await logger.debug("Debug message")
    await logger.info("Info message")
    await logger.notice("Notice message")
    await logger.warning("Warning message")
    await logger.error("Error message")
    await logger.critical("Critical message")
    print()

    # 2. Structured Logging
    print("2. STRUCTURED LOGGING:")
    print("-" * 40)

    await logger.info(
        "User logged in",
        user_id="12345",
        ip="192.168.1.1",
        method="oauth"
    )

    await logger.info(
        "Request processed",
        path="/api/users",
        method="GET",
        duration_ms=45
    )
    print()

    # 3. Context Propagation
    print("3. CONTEXT PROPAGATION:")
    print("-" * 40)

    with LogContext.scope(
        trace_id="abc-123",
        span_id="span-001",
        request_id="req-456"
    ):
        await logger.info("Request started")
        await logger.info("Processing data")
        await logger.info("Request completed")
    print()

    # 4. Multiple Handlers
    print("4. MULTIPLE HANDLERS:")
    print("-" * 40)

    memory_handler = MemoryHandler(max_records=1000)
    manager.add_handler(memory_handler)

    await logger.info("This goes to console and memory")
    await logger.warning("Warning also stored in memory")
    await logger.error("Error stored too")

    records = memory_handler.get_records()
    print(f"   Records in memory: {len(records)}")
    print()

    # 5. JSON Formatting
    print("5. JSON FORMATTING:")
    print("-" * 40)

    json_formatter = JSONFormatter(pretty=True)
    json_handler = MemoryHandler(formatter=json_formatter)

    record = LogRecord(
        level=LogLevel.INFO,
        logger_name="demo",
        message="JSON formatted message",
        context={"user": "admin"},
        extra={"action": "test"}
    )

    await json_handler.emit(record)

    for rec in json_handler.records:
        print(json_formatter.format(rec)[:200] + "...")
    print()

    # 6. Filtering
    print("6. LOG FILTERING:")
    print("-" * 40)

    # Level filter
    level_filter = LevelFilter(min_level=LogLevel.WARNING)
    filtered_handler = MemoryHandler(filters=[level_filter])

    test_logger = manager.get_logger("filtered")
    test_logger.handlers = [filtered_handler]
    test_logger.propagate = False

    await test_logger.debug("This will be filtered out")
    await test_logger.info("This too")
    await test_logger.warning("This will pass")
    await test_logger.error("This too")

    print(f"   Filtered records: {len(filtered_handler.records)}")
    print()

    # 7. Rate Limiting
    print("7. RATE LIMITING:")
    print("-" * 40)

    rate_filter = RateLimitFilter(window=1.0, max_count=3)
    rate_handler = MemoryHandler(filters=[rate_filter])

    rate_logger = manager.get_logger("rate_limited")
    rate_logger.handlers = [rate_handler]
    rate_logger.propagate = False

    for i in range(10):
        await rate_logger.info("Repeated message")

    print(f"   Logged (rate limited): {len(rate_handler.records)}")
    print()

    # 8. Logger Hierarchy
    print("8. LOGGER HIERARCHY:")
    print("-" * 40)

    parent = manager.get_logger("app")
    child = manager.get_logger("app.module")
    grandchild = manager.get_logger("app.module.submodule")

    print(f"   Parent: {parent.name}")
    print(f"   Child: {child.name} (parent={child.parent.name if child.parent else 'None'})")
    print(f"   Grandchild: {grandchild.name}")
    print()

    # 9. Exception Logging
    print("9. EXCEPTION LOGGING:")
    print("-" * 40)

    try:
        raise ValueError("Something went wrong!")
    except Exception:
        await logger.exception("An error occurred")
    print()

    # 10. Callback Handler
    print("10. CALLBACK HANDLER:")
    print("-" * 40)

    callback_count = 0

    async def log_callback(record: LogRecord):
        nonlocal callback_count
        callback_count += 1

    callback_handler = CallbackHandler(log_callback)
    cb_logger = manager.get_logger("callback")
    cb_logger.handlers = [callback_handler]
    cb_logger.propagate = False

    await cb_logger.info("Message 1")
    await cb_logger.info("Message 2")
    await cb_logger.info("Message 3")

    print(f"   Callback invoked: {callback_count} times")
    print()

    # 11. Statistics
    print("11. LOGGING STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total logs: {stats.total_logs}")
    print(f"   By level: {dict(stats.logs_by_level)}")
    print(f"   Errors: {stats.errors_count}")
    print(f"   Warnings: {stats.warnings_count}")
    print()

    # 12. Color Formatter Demo
    print("12. COLOR FORMATTER:")
    print("-" * 40)

    color_logger = manager.get_logger("colors")
    await color_logger.trace("Trace level (gray)")
    await color_logger.debug("Debug level (cyan)")
    await color_logger.info("Info level (green)")
    await color_logger.warning("Warning level (yellow)")
    await color_logger.error("Error level (red)")
    await color_logger.critical("Critical level (magenta)")
    print()

    await manager.close()

    print("=" * 70)
    print("DEMO COMPLETE - Advanced Logger System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
