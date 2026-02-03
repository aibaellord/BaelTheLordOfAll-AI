#!/usr/bin/env python3
"""
BAEL - Logger Engine
Comprehensive logging for ML training pipelines.

Features:
- Multi-level logging
- Structured logging
- Metric logging
- File and console handlers
- Log rotation
- Training-specific logging
"""

import asyncio
import json
import os
import sys
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
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
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    METRIC = 25

    def __lt__(self, other: 'LogLevel') -> bool:
        return self.value < other.value

    def __le__(self, other: 'LogLevel') -> bool:
        return self.value <= other.value


class LogFormat(Enum):
    """Log formats."""
    PLAIN = "plain"
    JSON = "json"
    STRUCTURED = "structured"
    MINIMAL = "minimal"


class LogDestination(Enum):
    """Log destinations."""
    CONSOLE = "console"
    FILE = "file"
    BOTH = "both"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LogRecord:
    """A log record."""
    timestamp: datetime = field(default_factory=datetime.now)
    level: LogLevel = LogLevel.INFO
    message: str = ""
    logger_name: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    source_file: str = ""
    source_line: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "message": self.message,
            "logger": self.logger_name,
            "extra": self.extra,
            "source": f"{self.source_file}:{self.source_line}"
        }


@dataclass
class MetricRecord:
    """A metric log record."""
    name: str = ""
    value: float = 0.0
    step: int = 0
    epoch: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class LoggerConfig:
    """Logger configuration."""
    name: str = "bael"
    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.STRUCTURED
    destination: LogDestination = LogDestination.CONSOLE
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024
    max_files: int = 5
    include_timestamp: bool = True
    include_level: bool = True
    include_source: bool = False
    colorize: bool = True


@dataclass
class TrainingLogState:
    """Training log state."""
    epoch: int = 0
    step: int = 0
    total_epochs: int = 0
    total_steps: int = 0
    metrics: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    start_time: Optional[datetime] = None
    last_log_time: Optional[datetime] = None


# =============================================================================
# FORMATTERS
# =============================================================================

class LogFormatter(ABC):
    """Abstract log formatter."""

    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """Format a log record."""
        pass


class PlainFormatter(LogFormatter):
    """Plain text formatter."""

    def __init__(self, config: LoggerConfig):
        self._config = config

    def format(self, record: LogRecord) -> str:
        """Format as plain text."""
        parts = []

        if self._config.include_timestamp:
            parts.append(record.timestamp.strftime("%Y-%m-%d %H:%M:%S"))

        if self._config.include_level:
            parts.append(f"[{record.level.name}]")

        parts.append(record.message)

        if record.extra:
            extra_str = " ".join(f"{k}={v}" for k, v in record.extra.items())
            parts.append(f"({extra_str})")

        return " ".join(parts)


class JSONFormatter(LogFormatter):
    """JSON formatter."""

    def format(self, record: LogRecord) -> str:
        """Format as JSON."""
        return json.dumps(record.to_dict())


class StructuredFormatter(LogFormatter):
    """Structured formatter with columns."""

    def __init__(self, config: LoggerConfig):
        self._config = config
        self._colors = {
            LogLevel.DEBUG: "\033[36m",
            LogLevel.INFO: "\033[32m",
            LogLevel.WARNING: "\033[33m",
            LogLevel.ERROR: "\033[31m",
            LogLevel.CRITICAL: "\033[35m",
            LogLevel.METRIC: "\033[34m",
        }
        self._reset = "\033[0m"

    def format(self, record: LogRecord) -> str:
        """Format with structure."""
        parts = []

        if self._config.include_timestamp:
            ts = record.timestamp.strftime("%H:%M:%S")
            parts.append(f"[{ts}]")

        if self._config.include_level:
            level_str = record.level.name.ljust(8)

            if self._config.colorize:
                color = self._colors.get(record.level, "")
                parts.append(f"{color}{level_str}{self._reset}")
            else:
                parts.append(level_str)

        parts.append(record.message)

        if record.extra:
            extra_parts = []
            for k, v in record.extra.items():
                if isinstance(v, float):
                    extra_parts.append(f"{k}={v:.4f}")
                else:
                    extra_parts.append(f"{k}={v}")
            parts.append(f"| {' '.join(extra_parts)}")

        return " ".join(parts)


class MinimalFormatter(LogFormatter):
    """Minimal formatter."""

    def format(self, record: LogRecord) -> str:
        """Format minimally."""
        return record.message


# =============================================================================
# HANDLERS
# =============================================================================

class LogHandler(ABC):
    """Abstract log handler."""

    def __init__(self, formatter: LogFormatter, level: LogLevel = LogLevel.DEBUG):
        self._formatter = formatter
        self._level = level

    @abstractmethod
    def emit(self, record: LogRecord) -> None:
        """Emit a log record."""
        pass

    def should_handle(self, record: LogRecord) -> bool:
        """Check if record should be handled."""
        return record.level.value >= self._level.value

    def close(self) -> None:
        """Close handler."""
        pass


class ConsoleHandler(LogHandler):
    """Console log handler."""

    def __init__(
        self,
        formatter: LogFormatter,
        level: LogLevel = LogLevel.DEBUG,
        stream: TextIO = None
    ):
        super().__init__(formatter, level)
        self._stream = stream or sys.stdout

    def emit(self, record: LogRecord) -> None:
        """Emit to console."""
        if not self.should_handle(record):
            return

        message = self._formatter.format(record)
        self._stream.write(message + "\n")
        self._stream.flush()


class FileHandler(LogHandler):
    """File log handler."""

    def __init__(
        self,
        formatter: LogFormatter,
        file_path: str,
        level: LogLevel = LogLevel.DEBUG,
        max_size: int = 10 * 1024 * 1024,
        max_files: int = 5
    ):
        super().__init__(formatter, level)
        self._file_path = Path(file_path)
        self._max_size = max_size
        self._max_files = max_files
        self._file: Optional[TextIO] = None
        self._current_size = 0

        self._open_file()

    def _open_file(self) -> None:
        """Open log file."""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        if self._file_path.exists():
            self._current_size = self._file_path.stat().st_size
        else:
            self._current_size = 0

        self._file = open(self._file_path, "a", encoding="utf-8")

    def _rotate(self) -> None:
        """Rotate log files."""
        if self._file:
            self._file.close()

        for i in range(self._max_files - 1, 0, -1):
            old_path = Path(f"{self._file_path}.{i}")
            new_path = Path(f"{self._file_path}.{i + 1}")

            if old_path.exists():
                if new_path.exists():
                    new_path.unlink()
                old_path.rename(new_path)

        if self._file_path.exists():
            Path(f"{self._file_path}.1").write_bytes(self._file_path.read_bytes())
            self._file_path.unlink()

        self._open_file()

    def emit(self, record: LogRecord) -> None:
        """Emit to file."""
        if not self.should_handle(record) or not self._file:
            return

        message = self._formatter.format(record)
        message_bytes = (message + "\n").encode("utf-8")

        if self._current_size + len(message_bytes) > self._max_size:
            self._rotate()

        self._file.write(message + "\n")
        self._file.flush()
        self._current_size += len(message_bytes)

    def close(self) -> None:
        """Close file handler."""
        if self._file:
            self._file.close()
            self._file = None


# =============================================================================
# LOGGER
# =============================================================================

class Logger:
    """Logger class."""

    def __init__(self, name: str, config: Optional[LoggerConfig] = None):
        self.name = name
        self.config = config or LoggerConfig(name=name)
        self._handlers: List[LogHandler] = []
        self._training_state = TrainingLogState()

        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup handlers based on config."""
        if self.config.format == LogFormat.PLAIN:
            formatter = PlainFormatter(self.config)
        elif self.config.format == LogFormat.JSON:
            formatter = JSONFormatter()
        elif self.config.format == LogFormat.MINIMAL:
            formatter = MinimalFormatter()
        else:
            formatter = StructuredFormatter(self.config)

        if self.config.destination in [LogDestination.CONSOLE, LogDestination.BOTH]:
            self._handlers.append(ConsoleHandler(formatter, self.config.level))

        if self.config.destination in [LogDestination.FILE, LogDestination.BOTH]:
            if self.config.file_path:
                self._handlers.append(FileHandler(
                    formatter,
                    self.config.file_path,
                    self.config.level,
                    self.config.max_file_size,
                    self.config.max_files
                ))

    def _log(
        self,
        level: LogLevel,
        message: str,
        **extra
    ) -> None:
        """Log a message."""
        if level.value < self.config.level.value:
            return

        record = LogRecord(
            level=level,
            message=message,
            logger_name=self.name,
            extra=extra
        )

        for handler in self._handlers:
            handler.emit(record)

    def debug(self, message: str, **extra) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **extra)

    def info(self, message: str, **extra) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **extra)

    def warning(self, message: str, **extra) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **extra)

    def error(self, message: str, **extra) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, **extra)

    def critical(self, message: str, **extra) -> None:
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, **extra)

    def metric(
        self,
        name: str,
        value: float,
        step: Optional[int] = None,
        epoch: Optional[int] = None,
        **tags
    ) -> None:
        """Log a metric."""
        step = step or self._training_state.step
        epoch = epoch or self._training_state.epoch

        self._training_state.metrics[name].append(value)

        self._log(
            LogLevel.METRIC,
            f"{name}: {value:.4f}",
            step=step,
            epoch=epoch,
            **tags
        )

    def epoch_start(self, epoch: int, total_epochs: int) -> None:
        """Log epoch start."""
        self._training_state.epoch = epoch
        self._training_state.total_epochs = total_epochs
        self._training_state.start_time = datetime.now()

        self.info(f"Epoch {epoch}/{total_epochs} started")

    def epoch_end(self, epoch: int, metrics: Optional[Dict[str, float]] = None) -> None:
        """Log epoch end."""
        elapsed = None
        if self._training_state.start_time:
            elapsed = (datetime.now() - self._training_state.start_time).total_seconds()

        extra = {"epoch": epoch}
        if elapsed:
            extra["time"] = f"{elapsed:.2f}s"
        if metrics:
            extra.update(metrics)

        self.info(f"Epoch {epoch} completed", **extra)

    def step(
        self,
        step: int,
        total_steps: Optional[int] = None,
        metrics: Optional[Dict[str, float]] = None
    ) -> None:
        """Log training step."""
        self._training_state.step = step
        if total_steps:
            self._training_state.total_steps = total_steps

        if metrics:
            for name, value in metrics.items():
                self.metric(name, value, step=step)

    def progress(
        self,
        current: int,
        total: int,
        prefix: str = "Progress",
        metrics: Optional[Dict[str, float]] = None
    ) -> None:
        """Log progress."""
        pct = current / total * 100 if total > 0 else 0

        extra = {"progress": f"{pct:.1f}%"}
        if metrics:
            extra.update({k: f"{v:.4f}" for k, v in metrics.items()})

        self.info(f"{prefix}: {current}/{total}", **extra)

    def separator(self, char: str = "=", length: int = 60) -> None:
        """Log a separator line."""
        self._log(LogLevel.INFO, char * length)

    def close(self) -> None:
        """Close logger."""
        for handler in self._handlers:
            handler.close()


# =============================================================================
# LOGGER ENGINE
# =============================================================================

class LoggerEngine:
    """
    Logger Engine for BAEL.

    Comprehensive logging for ML training pipelines.
    """

    def __init__(self):
        self._loggers: Dict[str, Logger] = {}
        self._default_config = LoggerConfig()

    def create_logger(
        self,
        name: str,
        config: Optional[LoggerConfig] = None
    ) -> Logger:
        """Create and register logger."""
        logger = Logger(name, config or self._default_config)
        self._loggers[name] = logger
        return logger

    def get_logger(self, name: str) -> Optional[Logger]:
        """Get logger by name."""
        if name not in self._loggers:
            return self.create_logger(name)
        return self._loggers.get(name)

    def set_default_config(self, config: LoggerConfig) -> None:
        """Set default config for new loggers."""
        self._default_config = config

    def set_level(self, level: LogLevel, logger_name: Optional[str] = None) -> None:
        """Set log level."""
        if logger_name:
            if logger_name in self._loggers:
                self._loggers[logger_name].config.level = level
        else:
            for logger in self._loggers.values():
                logger.config.level = level

    def close_all(self) -> None:
        """Close all loggers."""
        for logger in self._loggers.values():
            logger.close()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Logger Engine."""
    print("=" * 70)
    print("BAEL - LOGGER ENGINE DEMO")
    print("Comprehensive Logging for ML Training Pipelines")
    print("=" * 70)
    print()

    engine = LoggerEngine()

    # 1. Basic Logging
    print("1. BASIC LOGGING:")
    print("-" * 40)

    logger = engine.create_logger("training")

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    print()

    # 2. Logging with Extra Data
    print("2. LOGGING WITH EXTRA DATA:")
    print("-" * 40)

    logger.info("Training started", model="BAEL", batch_size=32, lr=0.001)
    logger.info("Batch processed", batch=1, loss=0.5432, accuracy=0.8765)
    print()

    # 3. Metric Logging
    print("3. METRIC LOGGING:")
    print("-" * 40)

    logger.metric("loss", 0.5432, step=1)
    logger.metric("accuracy", 0.8765, step=1)
    logger.metric("loss", 0.4321, step=2)
    logger.metric("accuracy", 0.9012, step=2)
    print()

    # 4. Epoch Logging
    print("4. EPOCH LOGGING:")
    print("-" * 40)

    logger.epoch_start(1, 10)
    time.sleep(0.1)
    logger.epoch_end(1, {"loss": 0.432, "accuracy": 0.901})
    print()

    # 5. Progress Logging
    print("5. PROGRESS LOGGING:")
    print("-" * 40)

    for i in range(0, 101, 25):
        logger.progress(i, 100, "Training", {"loss": 0.5 - i * 0.004})
    print()

    # 6. JSON Format Logger
    print("6. JSON FORMAT LOGGER:")
    print("-" * 40)

    json_config = LoggerConfig(
        name="json_logger",
        format=LogFormat.JSON
    )
    json_logger = engine.create_logger("json", json_config)

    json_logger.info("JSON formatted log", data="value", count=42)
    print()

    # 7. Minimal Format Logger
    print("7. MINIMAL FORMAT LOGGER:")
    print("-" * 40)

    minimal_config = LoggerConfig(
        name="minimal_logger",
        format=LogFormat.MINIMAL
    )
    minimal_logger = engine.create_logger("minimal", minimal_config)

    minimal_logger.info("Just the message, nothing else")
    print()

    # 8. Log Levels
    print("8. LOG LEVELS:")
    print("-" * 40)

    warning_config = LoggerConfig(
        name="warning_only",
        level=LogLevel.WARNING
    )
    warning_logger = engine.create_logger("warning_only", warning_config)

    warning_logger.debug("This won't show")
    warning_logger.info("This won't show either")
    warning_logger.warning("This will show")
    warning_logger.error("This will show too")
    print()

    # 9. Separator
    print("9. SEPARATOR:")
    print("-" * 40)

    logger.separator("=", 50)
    logger.info("Between separators")
    logger.separator("-", 50)
    print()

    # 10. Training Simulation
    print("10. TRAINING SIMULATION:")
    print("-" * 40)

    sim_logger = engine.create_logger("simulation")
    sim_logger.separator()
    sim_logger.info("BAEL Training Session")
    sim_logger.separator()

    for epoch in range(1, 4):
        sim_logger.epoch_start(epoch, 3)

        for step in range(1, 4):
            loss = 0.5 / (epoch * step)
            acc = 0.7 + 0.1 * epoch
            sim_logger.step(step, 3, {"loss": loss, "acc": acc})
            time.sleep(0.05)

        sim_logger.epoch_end(epoch, {"final_loss": loss, "final_acc": acc})

    sim_logger.separator()
    sim_logger.info("Training completed")
    print()

    engine.close_all()

    print("=" * 70)
    print("DEMO COMPLETE - Logger Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
