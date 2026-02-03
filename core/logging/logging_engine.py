#!/usr/bin/env python3
"""
BAEL - Logging Engine
Structured logging and observability for agents.

Features:
- Multi-level logging
- Structured log formats
- Log aggregation
- Log filtering
- Output handlers
"""

import asyncio
import hashlib
import json
import os
import sys
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, TextIO, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LogLevel(Enum):
    """Log levels."""
    TRACE = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogFormat(Enum):
    """Log output formats."""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"
    COMPACT = "compact"


class OutputType(Enum):
    """Output handler types."""
    CONSOLE = "console"
    FILE = "file"
    MEMORY = "memory"
    CALLBACK = "callback"


class ColorCode(Enum):
    """ANSI color codes."""
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LogRecord:
    """A log record."""
    record_id: str = ""
    level: LogLevel = LogLevel.INFO
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    logger_name: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    source: Optional[str] = None

    def __post_init__(self):
        if not self.record_id:
            self.record_id = str(uuid.uuid4())[:8]


@dataclass
class LogConfig:
    """Logging configuration."""
    min_level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.TEXT
    include_timestamp: bool = True
    include_source: bool = False
    colorize: bool = True
    max_message_length: int = 0


@dataclass
class FilterConfig:
    """Log filter configuration."""
    min_level: Optional[LogLevel] = None
    max_level: Optional[LogLevel] = None
    loggers: Optional[Set[str]] = None
    exclude_loggers: Optional[Set[str]] = None
    pattern: Optional[str] = None


# =============================================================================
# LOG FORMATTER
# =============================================================================

class LogFormatter:
    """Format log records."""

    LEVEL_COLORS = {
        LogLevel.TRACE: ColorCode.GRAY,
        LogLevel.DEBUG: ColorCode.CYAN,
        LogLevel.INFO: ColorCode.GREEN,
        LogLevel.WARNING: ColorCode.YELLOW,
        LogLevel.ERROR: ColorCode.RED,
        LogLevel.CRITICAL: ColorCode.MAGENTA
    }

    def __init__(self, config: LogConfig):
        self._config = config

    def format(self, record: LogRecord) -> str:
        """Format a log record."""
        if self._config.format == LogFormat.JSON:
            return self._format_json(record)
        elif self._config.format == LogFormat.STRUCTURED:
            return self._format_structured(record)
        elif self._config.format == LogFormat.COMPACT:
            return self._format_compact(record)
        else:
            return self._format_text(record)

    def _format_text(self, record: LogRecord) -> str:
        """Format as plain text."""
        parts = []

        if self._config.include_timestamp:
            parts.append(record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])

        level_str = f"[{record.level.name:8}]"

        if self._config.colorize:
            color = self.LEVEL_COLORS.get(record.level, ColorCode.WHITE)
            level_str = f"{color.value}{level_str}{ColorCode.RESET.value}"

        parts.append(level_str)

        if record.logger_name:
            parts.append(f"[{record.logger_name}]")

        message = record.message
        if self._config.max_message_length > 0:
            if len(message) > self._config.max_message_length:
                message = message[:self._config.max_message_length] + "..."

        parts.append(message)

        if record.context:
            ctx_str = " ".join(f"{k}={v}" for k, v in record.context.items())
            parts.append(f"| {ctx_str}")

        if record.exception:
            parts.append(f"\n{record.exception}")

        return " ".join(parts)

    def _format_json(self, record: LogRecord) -> str:
        """Format as JSON."""
        data = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "logger": record.logger_name
        }

        if record.context:
            data["context"] = record.context

        if record.exception:
            data["exception"] = record.exception

        if record.source:
            data["source"] = record.source

        return json.dumps(data, default=str)

    def _format_structured(self, record: LogRecord) -> str:
        """Format as structured key=value."""
        parts = [
            f"ts={record.timestamp.isoformat()}",
            f"level={record.level.name}",
            f"msg=\"{record.message}\""
        ]

        if record.logger_name:
            parts.append(f"logger={record.logger_name}")

        for key, value in record.context.items():
            if isinstance(value, str):
                parts.append(f"{key}=\"{value}\"")
            else:
                parts.append(f"{key}={value}")

        return " ".join(parts)

    def _format_compact(self, record: LogRecord) -> str:
        """Format as compact single line."""
        level_char = record.level.name[0]
        ts = record.timestamp.strftime("%H:%M:%S")

        return f"{ts} {level_char} {record.message}"


# =============================================================================
# LOG HANDLER INTERFACE
# =============================================================================

class LogHandler(ABC):
    """Abstract log handler."""

    @abstractmethod
    def handle(self, record: LogRecord, formatted: str) -> None:
        """Handle a log record."""
        pass

    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered logs."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the handler."""
        pass


# =============================================================================
# CONSOLE HANDLER
# =============================================================================

class ConsoleHandler(LogHandler):
    """Log to console."""

    def __init__(self, stream: TextIO = None):
        self._stream = stream or sys.stdout

    def handle(self, record: LogRecord, formatted: str) -> None:
        """Write to console."""
        self._stream.write(formatted + "\n")

    def flush(self) -> None:
        """Flush stream."""
        self._stream.flush()

    def close(self) -> None:
        """Close handler."""
        pass


# =============================================================================
# FILE HANDLER
# =============================================================================

class FileHandler(LogHandler):
    """Log to file."""

    def __init__(
        self,
        path: Path,
        max_size: int = 0,
        backup_count: int = 0
    ):
        self._path = Path(path)
        self._max_size = max_size
        self._backup_count = backup_count
        self._file: Optional[TextIO] = None
        self._current_size = 0

        self._open()

    def _open(self) -> None:
        """Open log file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._path, "a", encoding="utf-8")
        self._current_size = self._path.stat().st_size if self._path.exists() else 0

    def handle(self, record: LogRecord, formatted: str) -> None:
        """Write to file."""
        if not self._file:
            return

        line = formatted + "\n"

        if self._max_size > 0:
            self._current_size += len(line.encode("utf-8"))

            if self._current_size > self._max_size:
                self._rotate()

        self._file.write(line)

    def _rotate(self) -> None:
        """Rotate log files."""
        self.close()

        for i in range(self._backup_count - 1, 0, -1):
            src = Path(f"{self._path}.{i}")
            dst = Path(f"{self._path}.{i + 1}")

            if src.exists():
                src.rename(dst)

        if self._path.exists():
            self._path.rename(Path(f"{self._path}.1"))

        self._open()

    def flush(self) -> None:
        """Flush file."""
        if self._file:
            self._file.flush()

    def close(self) -> None:
        """Close file."""
        if self._file:
            self._file.close()
            self._file = None


# =============================================================================
# MEMORY HANDLER
# =============================================================================

class MemoryHandler(LogHandler):
    """Log to memory buffer."""

    def __init__(self, max_records: int = 1000):
        self._max_records = max_records
        self._records: deque = deque(maxlen=max_records)

    def handle(self, record: LogRecord, formatted: str) -> None:
        """Store in memory."""
        self._records.append((record, formatted))

    def flush(self) -> None:
        """Nothing to flush."""
        pass

    def close(self) -> None:
        """Clear records."""
        self._records.clear()

    def get_records(self) -> List[LogRecord]:
        """Get stored records."""
        return [r for r, _ in self._records]

    def get_formatted(self) -> List[str]:
        """Get formatted logs."""
        return [f for _, f in self._records]

    def clear(self) -> None:
        """Clear buffer."""
        self._records.clear()


# =============================================================================
# CALLBACK HANDLER
# =============================================================================

class CallbackHandler(LogHandler):
    """Log to callback function."""

    def __init__(self, callback: Callable[[LogRecord, str], None]):
        self._callback = callback

    def handle(self, record: LogRecord, formatted: str) -> None:
        """Call the callback."""
        try:
            self._callback(record, formatted)
        except Exception:
            pass

    def flush(self) -> None:
        """Nothing to flush."""
        pass

    def close(self) -> None:
        """Nothing to close."""
        pass


# =============================================================================
# LOG FILTER
# =============================================================================

class LogFilter:
    """Filter log records."""

    def __init__(self, config: FilterConfig):
        self._config = config

    def filter(self, record: LogRecord) -> bool:
        """Check if record should be logged."""
        if self._config.min_level:
            if record.level.value < self._config.min_level.value:
                return False

        if self._config.max_level:
            if record.level.value > self._config.max_level.value:
                return False

        if self._config.loggers:
            if record.logger_name not in self._config.loggers:
                return False

        if self._config.exclude_loggers:
            if record.logger_name in self._config.exclude_loggers:
                return False

        if self._config.pattern:
            if self._config.pattern.lower() not in record.message.lower():
                return False

        return True


# =============================================================================
# LOGGER
# =============================================================================

class Logger:
    """A logger instance."""

    def __init__(
        self,
        name: str,
        config: LogConfig,
        handlers: List[LogHandler],
        formatter: LogFormatter,
        filters: Optional[List[LogFilter]] = None
    ):
        self._name = name
        self._config = config
        self._handlers = handlers
        self._formatter = formatter
        self._filters = filters or []
        self._context: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        """Get logger name."""
        return self._name

    def with_context(self, **kwargs) -> 'Logger':
        """Create logger with additional context."""
        new_logger = Logger(
            self._name,
            self._config,
            self._handlers,
            self._formatter,
            self._filters
        )
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def _log(
        self,
        level: LogLevel,
        message: str,
        **context
    ) -> None:
        """Log a message."""
        if level.value < self._config.min_level.value:
            return

        merged_context = {**self._context, **context}

        exc_info = None
        if context.get("exc_info"):
            exc_info = traceback.format_exc()

        record = LogRecord(
            level=level,
            message=message,
            logger_name=self._name,
            context=merged_context,
            exception=exc_info
        )

        for log_filter in self._filters:
            if not log_filter.filter(record):
                return

        formatted = self._formatter.format(record)

        for handler in self._handlers:
            handler.handle(record, formatted)

    def trace(self, message: str, **context) -> None:
        """Log trace message."""
        self._log(LogLevel.TRACE, message, **context)

    def debug(self, message: str, **context) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **context)

    def warning(self, message: str, **context) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **context)

    def error(self, message: str, **context) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, **context)

    def critical(self, message: str, **context) -> None:
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, **context)

    def exception(self, message: str, **context) -> None:
        """Log exception with traceback."""
        self._log(LogLevel.ERROR, message, exc_info=True, **context)


# =============================================================================
# LOGGING ENGINE
# =============================================================================

class LoggingEngine:
    """
    Logging Engine for BAEL.

    Structured logging and observability.
    """

    def __init__(self, config: Optional[LogConfig] = None):
        self._config = config or LogConfig()

        self._formatter = LogFormatter(self._config)
        self._handlers: List[LogHandler] = []
        self._filters: List[LogFilter] = []
        self._loggers: Dict[str, Logger] = {}

        self._memory_handler: Optional[MemoryHandler] = None

        self._handlers.append(ConsoleHandler())

    # ----- Handler Management -----

    def add_console_handler(self) -> ConsoleHandler:
        """Add console handler."""
        handler = ConsoleHandler()
        self._handlers.append(handler)
        return handler

    def add_file_handler(
        self,
        path: str,
        max_size: int = 0,
        backup_count: int = 0
    ) -> FileHandler:
        """Add file handler."""
        handler = FileHandler(Path(path), max_size, backup_count)
        self._handlers.append(handler)
        return handler

    def add_memory_handler(self, max_records: int = 1000) -> MemoryHandler:
        """Add memory handler."""
        handler = MemoryHandler(max_records)
        self._handlers.append(handler)
        self._memory_handler = handler
        return handler

    def add_callback_handler(
        self,
        callback: Callable[[LogRecord, str], None]
    ) -> CallbackHandler:
        """Add callback handler."""
        handler = CallbackHandler(callback)
        self._handlers.append(handler)
        return handler

    # ----- Filter Management -----

    def add_filter(self, config: FilterConfig) -> LogFilter:
        """Add log filter."""
        log_filter = LogFilter(config)
        self._filters.append(log_filter)
        return log_filter

    def set_level(self, level: LogLevel) -> None:
        """Set minimum log level."""
        self._config.min_level = level

    # ----- Logger Management -----

    def get_logger(self, name: str = "") -> Logger:
        """Get or create a logger."""
        if name not in self._loggers:
            logger = Logger(
                name,
                self._config,
                self._handlers,
                self._formatter,
                self._filters
            )
            self._loggers[name] = logger

        return self._loggers[name]

    # ----- Direct Logging -----

    def trace(self, message: str, **context) -> None:
        """Log trace message."""
        self.get_logger().trace(message, **context)

    def debug(self, message: str, **context) -> None:
        """Log debug message."""
        self.get_logger().debug(message, **context)

    def info(self, message: str, **context) -> None:
        """Log info message."""
        self.get_logger().info(message, **context)

    def warning(self, message: str, **context) -> None:
        """Log warning message."""
        self.get_logger().warning(message, **context)

    def error(self, message: str, **context) -> None:
        """Log error message."""
        self.get_logger().error(message, **context)

    def critical(self, message: str, **context) -> None:
        """Log critical message."""
        self.get_logger().critical(message, **context)

    def exception(self, message: str, **context) -> None:
        """Log exception."""
        self.get_logger().exception(message, **context)

    # ----- Memory Access -----

    def get_logs(self) -> List[str]:
        """Get logs from memory handler."""
        if self._memory_handler:
            return self._memory_handler.get_formatted()
        return []

    def get_records(self) -> List[LogRecord]:
        """Get log records from memory handler."""
        if self._memory_handler:
            return self._memory_handler.get_records()
        return []

    def clear_logs(self) -> None:
        """Clear memory logs."""
        if self._memory_handler:
            self._memory_handler.clear()

    # ----- Control -----

    def flush(self) -> None:
        """Flush all handlers."""
        for handler in self._handlers:
            handler.flush()

    def shutdown(self) -> None:
        """Shutdown all handlers."""
        for handler in self._handlers:
            handler.flush()
            handler.close()

    def set_format(self, format: LogFormat) -> None:
        """Set log format."""
        self._config.format = format
        self._formatter = LogFormatter(self._config)

    def set_colorize(self, colorize: bool) -> None:
        """Set colorization."""
        self._config.colorize = colorize
        self._formatter = LogFormatter(self._config)

    # ----- Summary -----

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "min_level": self._config.min_level.name,
            "format": self._config.format.value,
            "handlers": len(self._handlers),
            "filters": len(self._filters),
            "loggers": len(self._loggers),
            "colorize": self._config.colorize
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Logging Engine."""
    print("=" * 70)
    print("BAEL - LOGGING ENGINE DEMO")
    print("Structured Logging and Observability")
    print("=" * 70)
    print()

    engine = LoggingEngine(LogConfig(min_level=LogLevel.DEBUG))

    # 1. Basic Logging
    print("1. BASIC LOGGING:")
    print("-" * 40)

    engine.debug("Debug message")
    engine.info("Info message")
    engine.warning("Warning message")
    engine.error("Error message")
    print()

    # 2. Contextual Logging
    print("2. CONTEXTUAL LOGGING:")
    print("-" * 40)

    engine.info("User logged in", user_id="123", ip="192.168.1.1")
    engine.warning("Rate limit approaching", rate=95, limit=100)
    print()

    # 3. Named Loggers
    print("3. NAMED LOGGERS:")
    print("-" * 40)

    auth_logger = engine.get_logger("auth")
    db_logger = engine.get_logger("database")

    auth_logger.info("Authentication successful")
    db_logger.debug("Query executed", query="SELECT *", duration_ms=42)
    print()

    # 4. Logger with Context
    print("4. LOGGER WITH CONTEXT:")
    print("-" * 40)

    request_logger = engine.get_logger("http").with_context(
        request_id="req-456",
        method="GET"
    )

    request_logger.info("Request started", path="/api/users")
    request_logger.info("Request completed", status=200)
    print()

    # 5. Memory Handler
    print("5. MEMORY HANDLER:")
    print("-" * 40)

    engine.add_memory_handler(max_records=100)

    engine.info("This goes to memory too")
    engine.debug("So does this")

    records = engine.get_records()
    print(f"   Records in memory: {len(records)}")
    print()

    # 6. JSON Format
    print("6. JSON FORMAT:")
    print("-" * 40)

    json_engine = LoggingEngine(LogConfig(
        min_level=LogLevel.INFO,
        format=LogFormat.JSON,
        colorize=False
    ))

    json_engine.info("JSON formatted log", user="test", action="demo")
    print()

    # 7. Structured Format
    print("7. STRUCTURED FORMAT:")
    print("-" * 40)

    struct_engine = LoggingEngine(LogConfig(
        min_level=LogLevel.INFO,
        format=LogFormat.STRUCTURED,
        colorize=False
    ))

    struct_engine.info("Structured log entry", service="api", version="1.0")
    print()

    # 8. Compact Format
    print("8. COMPACT FORMAT:")
    print("-" * 40)

    compact_engine = LoggingEngine(LogConfig(
        min_level=LogLevel.INFO,
        format=LogFormat.COMPACT,
        colorize=False
    ))

    compact_engine.info("Compact log")
    compact_engine.warning("Another compact log")
    compact_engine.error("Compact error")
    print()

    # 9. Log Levels
    print("9. LOG LEVELS:")
    print("-" * 40)

    level_engine = LoggingEngine(LogConfig(min_level=LogLevel.WARNING))

    level_engine.debug("This won't appear")
    level_engine.info("This won't appear either")
    level_engine.warning("This will appear")
    level_engine.error("This will also appear")
    print()

    # 10. Callback Handler
    print("10. CALLBACK HANDLER:")
    print("-" * 40)

    collected = []

    def my_callback(record, formatted):
        collected.append(record.level.name)

    engine.add_callback_handler(my_callback)

    engine.info("Callback test 1")
    engine.warning("Callback test 2")

    print(f"   Collected levels: {collected[-2:]}")
    print()

    # 11. Filter by Level
    print("11. FILTER BY LEVEL:")
    print("-" * 40)

    filter_engine = LoggingEngine(LogConfig(min_level=LogLevel.DEBUG))
    filter_engine.add_memory_handler(100)

    filter_engine.add_filter(FilterConfig(min_level=LogLevel.WARNING))

    filter_engine.debug("Filtered out")
    filter_engine.info("Also filtered")
    filter_engine.warning("This passes")
    filter_engine.error("This too")

    print(f"   Logged records: {len(filter_engine.get_records())}")
    print()

    # 12. Filter by Logger
    print("12. FILTER BY LOGGER:")
    print("-" * 40)

    name_engine = LoggingEngine(LogConfig(min_level=LogLevel.DEBUG))
    name_engine.add_memory_handler(100)

    name_engine.add_filter(FilterConfig(
        loggers={"important"}
    ))

    name_engine.get_logger("ignored").info("Ignored message")
    name_engine.get_logger("important").info("Important message")

    print(f"   Logged records: {len(name_engine.get_records())}")
    print()

    # 13. Exclude Loggers
    print("13. EXCLUDE LOGGERS:")
    print("-" * 40)

    exclude_engine = LoggingEngine(LogConfig(min_level=LogLevel.DEBUG))
    exclude_engine.add_memory_handler(100)

    exclude_engine.add_filter(FilterConfig(
        exclude_loggers={"noisy"}
    ))

    exclude_engine.get_logger("noisy").info("Noisy message")
    exclude_engine.get_logger("quiet").info("Quiet message")

    print(f"   Logged records: {len(exclude_engine.get_records())}")
    print()

    # 14. Log All Levels
    print("14. ALL LOG LEVELS:")
    print("-" * 40)

    all_levels_engine = LoggingEngine(LogConfig(
        min_level=LogLevel.TRACE,
        colorize=True
    ))

    all_levels_engine.trace("Trace level")
    all_levels_engine.debug("Debug level")
    all_levels_engine.info("Info level")
    all_levels_engine.warning("Warning level")
    all_levels_engine.error("Error level")
    all_levels_engine.critical("Critical level")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    engine.shutdown()

    print("=" * 70)
    print("DEMO COMPLETE - Logging Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
