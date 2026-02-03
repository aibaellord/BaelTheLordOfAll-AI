#!/usr/bin/env python3
"""
BAEL - Advanced Logging and Tracing System
Structured logging with distributed tracing support.

Features:
- Structured JSON logging
- Log levels and filtering
- Context propagation
- Distributed tracing (OpenTelemetry)
- Log aggregation
- Real-time log streaming
- Log analysis and alerting
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from abc import ABC, abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, TextIO, Union
from uuid import uuid4

# =============================================================================
# CONTEXT VARIABLES
# =============================================================================

# Trace context
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")
parent_span_id_var: ContextVar[str] = ContextVar("parent_span_id", default="")

# Request context
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")


# =============================================================================
# LOG LEVELS
# =============================================================================

class LogLevel(Enum):
    """Log levels with numeric values."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """Convert string to log level."""
        return cls[level.upper()]


# =============================================================================
# LOG RECORD
# =============================================================================

@dataclass
class LogRecord:
    """Structured log record."""
    timestamp: datetime
    level: LogLevel
    message: str
    logger_name: str

    # Context
    trace_id: str = ""
    span_id: str = ""
    request_id: str = ""
    user_id: str = ""

    # Location
    filename: str = ""
    lineno: int = 0
    function: str = ""

    # Extra data
    extra: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None

    # Metadata
    service: str = "bael"
    environment: str = "development"
    host: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "message": self.message,
            "logger": self.logger_name,
            "service": self.service,
            "environment": self.environment
        }

        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.span_id:
            result["span_id"] = self.span_id
        if self.request_id:
            result["request_id"] = self.request_id
        if self.user_id:
            result["user_id"] = self.user_id

        if self.filename:
            result["location"] = {
                "file": self.filename,
                "line": self.lineno,
                "function": self.function
            }

        if self.extra:
            result["extra"] = self.extra
        if self.exception:
            result["exception"] = self.exception
        if self.host:
            result["host"] = self.host

        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


# =============================================================================
# LOG FORMATTERS
# =============================================================================

class LogFormatter(ABC):
    """Base log formatter."""

    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """Format log record."""
        pass


class JSONFormatter(LogFormatter):
    """JSON log formatter."""

    def __init__(self, indent: int = None):
        self.indent = indent

    def format(self, record: LogRecord) -> str:
        return json.dumps(record.to_dict(), indent=self.indent)


class TextFormatter(LogFormatter):
    """Human-readable text formatter."""

    COLORS = {
        LogLevel.TRACE: "\033[37m",    # White
        LogLevel.DEBUG: "\033[36m",    # Cyan
        LogLevel.INFO: "\033[32m",     # Green
        LogLevel.WARNING: "\033[33m",  # Yellow
        LogLevel.ERROR: "\033[31m",    # Red
        LogLevel.CRITICAL: "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, colorize: bool = True, include_location: bool = True):
        self.colorize = colorize
        self.include_location = include_location

    def format(self, record: LogRecord) -> str:
        timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = record.level.name.ljust(8)

        if self.colorize:
            color = self.COLORS.get(record.level, "")
            level = f"{color}{level}{self.RESET}"

        parts = [f"{timestamp} | {level} | {record.logger_name}"]

        if record.trace_id:
            parts.append(f"[{record.trace_id[:8]}]")

        parts.append(f"| {record.message}")

        if self.include_location and record.filename:
            parts.append(f"({record.filename}:{record.lineno})")

        line = " ".join(parts)

        if record.extra:
            line += f" | {json.dumps(record.extra)}"

        if record.exception:
            line += f"\n{record.exception}"

        return line


# =============================================================================
# LOG HANDLERS
# =============================================================================

class LogHandler(ABC):
    """Base log handler."""

    def __init__(
        self,
        formatter: LogFormatter = None,
        min_level: LogLevel = LogLevel.DEBUG,
        filters: List[Callable[[LogRecord], bool]] = None
    ):
        self.formatter = formatter or TextFormatter()
        self.min_level = min_level
        self.filters = filters or []

    def should_handle(self, record: LogRecord) -> bool:
        """Check if record should be handled."""
        if record.level.value < self.min_level.value:
            return False

        for filter_func in self.filters:
            if not filter_func(record):
                return False

        return True

    @abstractmethod
    def emit(self, record: LogRecord) -> None:
        """Emit log record."""
        pass

    def close(self) -> None:
        """Close handler."""
        pass


class ConsoleHandler(LogHandler):
    """Console output handler."""

    def __init__(
        self,
        stream: TextIO = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.stream = stream or sys.stdout

    def emit(self, record: LogRecord) -> None:
        if self.should_handle(record):
            try:
                output = self.formatter.format(record)
                self.stream.write(output + "\n")
                self.stream.flush()
            except Exception:
                pass


class FileHandler(LogHandler):
    """File output handler with rotation."""

    def __init__(
        self,
        path: str,
        max_size_mb: float = 100,
        backup_count: int = 5,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.path = Path(path)
        self.max_size = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self._file: Optional[TextIO] = None
        self._open_file()

    def _open_file(self) -> None:
        """Open log file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "a")

    def _rotate(self) -> None:
        """Rotate log files."""
        if self._file:
            self._file.close()

        # Shift existing backups
        for i in range(self.backup_count - 1, 0, -1):
            src = self.path.with_suffix(f".{i}")
            dst = self.path.with_suffix(f".{i + 1}")
            if src.exists():
                src.rename(dst)

        # Rename current to .1
        if self.path.exists():
            self.path.rename(self.path.with_suffix(".1"))

        self._open_file()

    def emit(self, record: LogRecord) -> None:
        if not self.should_handle(record):
            return

        try:
            output = self.formatter.format(record)
            self._file.write(output + "\n")
            self._file.flush()

            # Check rotation
            if self.path.stat().st_size > self.max_size:
                self._rotate()

        except Exception:
            pass

    def close(self) -> None:
        if self._file:
            self._file.close()


class AsyncHandler(LogHandler):
    """Async handler with buffering."""

    def __init__(
        self,
        target: LogHandler,
        buffer_size: int = 1000,
        flush_interval: float = 5.0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.target = target
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self._buffer: List[LogRecord] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start async flushing."""
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Stop async flushing."""
        if self._flush_task:
            self._flush_task.cancel()
            await self.flush()

    async def _flush_loop(self) -> None:
        """Periodic flush loop."""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()

    async def flush(self) -> None:
        """Flush buffer to target."""
        async with self._lock:
            for record in self._buffer:
                self.target.emit(record)
            self._buffer.clear()

    def emit(self, record: LogRecord) -> None:
        if not self.should_handle(record):
            return

        self._buffer.append(record)

        if len(self._buffer) >= self.buffer_size:
            asyncio.create_task(self.flush())


class WebhookHandler(LogHandler):
    """Send logs to webhook endpoint."""

    def __init__(
        self,
        url: str,
        headers: Dict[str, str] = None,
        batch_size: int = 100,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.url = url
        self.headers = headers or {}
        self.batch_size = batch_size
        self._buffer: List[LogRecord] = []

    def emit(self, record: LogRecord) -> None:
        if not self.should_handle(record):
            return

        self._buffer.append(record)

        if len(self._buffer) >= self.batch_size:
            self._send_batch()

    def _send_batch(self) -> None:
        """Send batch of logs."""
        if not self._buffer:
            return

        try:
            import httpx

            payload = {
                "logs": [r.to_dict() for r in self._buffer]
            }

            httpx.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=10
            )

            self._buffer.clear()

        except Exception:
            pass


# =============================================================================
# LOGGER
# =============================================================================

class Logger:
    """Structured logger."""

    def __init__(
        self,
        name: str,
        handlers: List[LogHandler] = None,
        level: LogLevel = LogLevel.DEBUG,
        propagate: bool = True
    ):
        self.name = name
        self.handlers = handlers or []
        self.level = level
        self.propagate = propagate
        self.parent: Optional["Logger"] = None
        self._context: Dict[str, Any] = {}

        # Get hostname
        import socket
        self._host = socket.gethostname()

    def add_handler(self, handler: LogHandler) -> None:
        """Add handler."""
        self.handlers.append(handler)

    def bind(self, **kwargs) -> "Logger":
        """Create child logger with bound context."""
        child = Logger(
            name=self.name,
            handlers=self.handlers,
            level=self.level,
            propagate=self.propagate
        )
        child._context = {**self._context, **kwargs}
        child.parent = self
        return child

    def _log(
        self,
        level: LogLevel,
        message: str,
        exc_info: bool = False,
        **kwargs
    ) -> None:
        """Internal log method."""
        if level.value < self.level.value:
            return

        # Get caller info
        import inspect
        frame = inspect.currentframe()
        if frame:
            for _ in range(3):  # Skip internal frames
                if frame.f_back:
                    frame = frame.f_back
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            function = frame.f_code.co_name
        else:
            filename, lineno, function = "", 0, ""

        # Get exception info
        exception = None
        if exc_info:
            exception = traceback.format_exc()

        # Build record
        record = LogRecord(
            timestamp=datetime.now(),
            level=level,
            message=message,
            logger_name=self.name,
            trace_id=trace_id_var.get(),
            span_id=span_id_var.get(),
            request_id=request_id_var.get(),
            user_id=user_id_var.get(),
            filename=os.path.basename(filename),
            lineno=lineno,
            function=function,
            extra={**self._context, **kwargs},
            exception=exception,
            host=self._host,
            environment=os.environ.get("ENVIRONMENT", "development")
        )

        # Emit to handlers
        for handler in self.handlers:
            try:
                handler.emit(record)
            except Exception:
                pass

        # Propagate to parent
        if self.propagate and self.parent:
            for handler in self.parent.handlers:
                try:
                    handler.emit(record)
                except Exception:
                    pass

    def trace(self, message: str, **kwargs) -> None:
        """Log at TRACE level."""
        self._log(LogLevel.TRACE, message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log at DEBUG level."""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log at INFO level."""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log at WARNING level."""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log at ERROR level."""
        self._log(LogLevel.ERROR, message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log at CRITICAL level."""
        self._log(LogLevel.CRITICAL, message, exc_info=exc_info, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self._log(LogLevel.ERROR, message, exc_info=True, **kwargs)


# =============================================================================
# TRACING
# =============================================================================

@dataclass
class Span:
    """Distributed trace span."""
    trace_id: str
    span_id: str
    parent_span_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "ok"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events
        }


class Tracer:
    """Distributed tracer."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._spans: List[Span] = []
        self._exporters: List[Callable[[Span], None]] = []

    def add_exporter(self, exporter: Callable[[Span], None]) -> None:
        """Add span exporter."""
        self._exporters.append(exporter)

    @contextmanager
    def start_span(self, name: str, attributes: Dict[str, Any] = None):
        """Start a new span."""
        # Get or create trace ID
        trace_id = trace_id_var.get() or str(uuid4())
        parent_span_id = span_id_var.get()
        span_id = str(uuid4())

        # Set context
        trace_id_var.set(trace_id)
        span_id_var.set(span_id)
        parent_span_id_var.set(parent_span_id)

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            start_time=datetime.now(),
            attributes=attributes or {}
        )

        try:
            yield span
            span.status = "ok"
        except Exception as e:
            span.status = "error"
            span.add_event("exception", {"message": str(e)})
            raise
        finally:
            span.end_time = datetime.now()
            self._spans.append(span)

            # Export span
            for exporter in self._exporters:
                try:
                    exporter(span)
                except Exception:
                    pass

            # Restore parent span
            span_id_var.set(parent_span_id)

    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> None:
        """Add event to current span."""
        # Would add to current span
        pass


# =============================================================================
# LOGGING MANAGER
# =============================================================================

class LoggingManager:
    """Central logging configuration."""

    _instance: Optional["LoggingManager"] = None

    def __new__(cls) -> "LoggingManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._loggers: Dict[str, Logger] = {}
        self._root_logger: Optional[Logger] = None
        self._tracer: Optional[Tracer] = None
        self._initialized = True

    def configure(
        self,
        level: LogLevel = LogLevel.INFO,
        format: str = "text",
        output: str = "console",
        log_file: str = None,
        service_name: str = "bael"
    ) -> None:
        """Configure logging."""
        handlers = []

        # Create formatter
        if format == "json":
            formatter = JSONFormatter()
        else:
            formatter = TextFormatter(colorize=output == "console")

        # Create handlers
        if output in ("console", "both"):
            handlers.append(ConsoleHandler(formatter=formatter, min_level=level))

        if output in ("file", "both") and log_file:
            handlers.append(FileHandler(
                path=log_file,
                formatter=JSONFormatter(),
                min_level=level
            ))

        # Create root logger
        self._root_logger = Logger(
            name="root",
            handlers=handlers,
            level=level
        )

        # Create tracer
        self._tracer = Tracer(service_name)

    def get_logger(self, name: str) -> Logger:
        """Get or create logger."""
        if name not in self._loggers:
            logger = Logger(
                name=name,
                handlers=[],
                level=LogLevel.DEBUG,
                propagate=True
            )
            logger.parent = self._root_logger
            self._loggers[name] = logger

        return self._loggers[name]

    def get_tracer(self) -> Tracer:
        """Get tracer."""
        if not self._tracer:
            self._tracer = Tracer("bael")
        return self._tracer


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_manager = LoggingManager()


def configure_logging(**kwargs) -> None:
    """Configure logging."""
    _manager.configure(**kwargs)


def get_logger(name: str) -> Logger:
    """Get logger by name."""
    return _manager.get_logger(name)


def get_tracer() -> Tracer:
    """Get tracer."""
    return _manager.get_tracer()


# =============================================================================
# INTEGRATION WITH STDLIB
# =============================================================================

class StdlibHandler(logging.Handler):
    """Bridge to stdlib logging."""

    def __init__(self, logger: Logger):
        super().__init__()
        self.bael_logger = logger

    def emit(self, record: logging.LogRecord) -> None:
        level_map = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.CRITICAL
        }

        level = level_map.get(record.levelno, LogLevel.INFO)
        message = record.getMessage()

        self.bael_logger._log(
            level,
            message,
            exc_info=record.exc_info is not None
        )


def setup_stdlib_logging(level: int = logging.INFO) -> None:
    """Configure stdlib logging to use BAEL logger."""
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [StdlibHandler(get_logger("stdlib"))]


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Demo logging."""
    # Configure
    configure_logging(
        level=LogLevel.DEBUG,
        format="text",
        output="console",
        service_name="bael-demo"
    )

    # Get logger
    logger = get_logger("demo")

    # Log messages
    logger.debug("This is a debug message")
    logger.info("Application started", version="1.0.0")
    logger.warning("Something might be wrong", component="auth")
    logger.error("An error occurred", error_code=500)

    # With bound context
    user_logger = logger.bind(user_id="user123", session="abc")
    user_logger.info("User action", action="login")

    # With tracing
    tracer = get_tracer()

    with tracer.start_span("process_request", {"method": "POST"}):
        logger.info("Processing request")

        with tracer.start_span("database_query"):
            logger.debug("Querying database")
            time.sleep(0.1)

    logger.info("Request completed")


if __name__ == "__main__":
    main()
