"""
BAEL Log Aggregator
====================

Centralized log collection and analysis.
Aggregates logs from all system components.

Features:
- Structured logging
- Log parsing
- Pattern detection
- Search and filtering
- Log analysis
"""

import hashlib
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generator, List, Optional, Pattern,
                    Tuple)

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels."""
    TRACE = 10
    DEBUG = 20
    INFO = 30
    WARNING = 40
    ERROR = 50
    CRITICAL = 60

    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """Parse level from string."""
        level = level.upper()
        mapping = {
            "TRACE": cls.TRACE,
            "DEBUG": cls.DEBUG,
            "INFO": cls.INFO,
            "WARN": cls.WARNING,
            "WARNING": cls.WARNING,
            "ERROR": cls.ERROR,
            "CRITICAL": cls.CRITICAL,
            "FATAL": cls.CRITICAL,
        }
        return mapping.get(level, cls.INFO)


@dataclass
class LogEntry:
    """A single log entry."""
    id: str
    timestamp: datetime
    level: LogLevel
    message: str

    # Source
    service: str = ""
    component: str = ""
    host: str = ""

    # Context
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    # Structured fields
    fields: Dict[str, Any] = field(default_factory=dict)

    # Raw
    raw: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "message": self.message,
            "service": self.service,
            "component": self.component,
            "trace_id": self.trace_id,
            "fields": self.fields,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class LogPattern:
    """A pattern for log parsing/detection."""
    name: str
    pattern: str

    # Compiled regex
    _regex: Optional[Pattern] = None

    # Extraction groups
    groups: List[str] = field(default_factory=list)

    # Classification
    level_override: Optional[LogLevel] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        self._regex = re.compile(self.pattern)

    def match(self, text: str) -> Optional[Dict[str, str]]:
        """Match pattern against text."""
        if not self._regex:
            return None

        match = self._regex.search(text)
        if match:
            return match.groupdict()
        return None


@dataclass
class LogQuery:
    """Query for searching logs."""
    # Text search
    text: str = ""
    regex: Optional[str] = None

    # Filters
    levels: List[LogLevel] = field(default_factory=list)
    services: List[str] = field(default_factory=list)

    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Trace
    trace_id: Optional[str] = None

    # Pagination
    limit: int = 100
    offset: int = 0

    # Sorting
    order: str = "desc"  # "asc" or "desc"


class LogParser:
    """
    Parser for log entries.
    """

    # Common log formats
    COMMON_PATTERNS = [
        # JSON
        LogPattern(
            name="json",
            pattern=r'^\{.*\}$',
        ),
        # Standard format: timestamp level message
        LogPattern(
            name="standard",
            pattern=r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+(?P<level>\w+)\s+(?P<message>.+)$',
            groups=["timestamp", "level", "message"],
        ),
        # Nginx access log
        LogPattern(
            name="nginx_access",
            pattern=r'^(?P<ip>[\d.]+)\s+-\s+-\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>\w+)\s+(?P<path>[^"]+)\s+HTTP/[\d.]+"\s+(?P<status>\d+)',
            groups=["ip", "timestamp", "method", "path", "status"],
        ),
    ]

    def __init__(self):
        self.patterns = list(self.COMMON_PATTERNS)
        self._entry_counter = 0

    def add_pattern(self, pattern: LogPattern) -> None:
        """Add a custom pattern."""
        self.patterns.append(pattern)

    def parse(self, raw: str, service: str = "") -> LogEntry:
        """
        Parse a log line.

        Args:
            raw: Raw log line
            service: Source service name

        Returns:
            Parsed log entry
        """
        self._entry_counter += 1
        entry_id = hashlib.md5(f"{self._entry_counter}:{raw[:50]}".encode()).hexdigest()[:12]

        # Try JSON first
        if raw.strip().startswith('{'):
            try:
                data = json.loads(raw)
                return LogEntry(
                    id=entry_id,
                    timestamp=self._parse_timestamp(data.get("timestamp", "")),
                    level=LogLevel.from_string(data.get("level", "info")),
                    message=data.get("message", data.get("msg", "")),
                    service=data.get("service", service),
                    component=data.get("component", ""),
                    trace_id=data.get("trace_id"),
                    span_id=data.get("span_id"),
                    fields={k: v for k, v in data.items()
                           if k not in ["timestamp", "level", "message", "msg"]},
                    raw=raw,
                )
            except json.JSONDecodeError:
                pass

        # Try other patterns
        for pattern in self.patterns:
            match = pattern.match(raw)
            if match:
                return LogEntry(
                    id=entry_id,
                    timestamp=self._parse_timestamp(match.get("timestamp", "")),
                    level=pattern.level_override or LogLevel.from_string(match.get("level", "info")),
                    message=match.get("message", raw),
                    service=service,
                    fields=match,
                    raw=raw,
                )

        # Fallback: treat as plain message
        return LogEntry(
            id=entry_id,
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message=raw,
            service=service,
            raw=raw,
        )

    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse timestamp string."""
        if not ts:
            return datetime.now()

        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%d/%b/%Y:%H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(ts[:26], fmt[:len(ts)])
            except ValueError:
                continue

        return datetime.now()


class LogStore:
    """
    In-memory log storage.
    """

    def __init__(self, max_entries: int = 100000):
        self.max_entries = max_entries
        self._entries: List[LogEntry] = []
        self._by_service: Dict[str, List[LogEntry]] = defaultdict(list)
        self._by_trace: Dict[str, List[LogEntry]] = defaultdict(list)

    def add(self, entry: LogEntry) -> None:
        """Add a log entry."""
        self._entries.append(entry)

        if entry.service:
            self._by_service[entry.service].append(entry)

        if entry.trace_id:
            self._by_trace[entry.trace_id].append(entry)

        # Prune if needed
        if len(self._entries) > self.max_entries:
            self._prune()

    def _prune(self) -> None:
        """Remove old entries."""
        keep = self.max_entries * 3 // 4
        removed = self._entries[:-keep]
        self._entries = self._entries[-keep:]

        # Rebuild indices
        self._by_service.clear()
        self._by_trace.clear()

        for entry in self._entries:
            if entry.service:
                self._by_service[entry.service].append(entry)
            if entry.trace_id:
                self._by_trace[entry.trace_id].append(entry)

    def query(self, q: LogQuery) -> List[LogEntry]:
        """Query log entries."""
        results = self._entries

        # Filter by service
        if q.services:
            results = [e for e in results if e.service in q.services]

        # Filter by level
        if q.levels:
            results = [e for e in results if e.level in q.levels]

        # Filter by time
        if q.start_time:
            results = [e for e in results if e.timestamp >= q.start_time]
        if q.end_time:
            results = [e for e in results if e.timestamp <= q.end_time]

        # Filter by trace
        if q.trace_id:
            results = [e for e in results if e.trace_id == q.trace_id]

        # Text search
        if q.text:
            text_lower = q.text.lower()
            results = [e for e in results if text_lower in e.message.lower()]

        # Regex search
        if q.regex:
            pattern = re.compile(q.regex)
            results = [e for e in results if pattern.search(e.message)]

        # Sort
        results = sorted(results, key=lambda e: e.timestamp, reverse=(q.order == "desc"))

        # Paginate
        return results[q.offset:q.offset + q.limit]

    def get_by_trace(self, trace_id: str) -> List[LogEntry]:
        """Get entries for a trace."""
        return sorted(self._by_trace.get(trace_id, []), key=lambda e: e.timestamp)

    def count(self) -> int:
        """Get total count."""
        return len(self._entries)


class LogAggregator:
    """
    Log aggregator for BAEL.

    Collects and analyzes logs.
    """

    def __init__(self, max_entries: int = 100000):
        self.parser = LogParser()
        self.store = LogStore(max_entries)

        # Pattern detection
        self._anomaly_patterns: List[LogPattern] = [
            LogPattern(
                name="exception",
                pattern=r'(?:Exception|Error|Traceback)',
                level_override=LogLevel.ERROR,
                tags=["exception"],
            ),
            LogPattern(
                name="timeout",
                pattern=r'(?:timeout|timed out)',
                level_override=LogLevel.WARNING,
                tags=["timeout"],
            ),
            LogPattern(
                name="connection_error",
                pattern=r'(?:connection refused|connection reset|ECONNREFUSED)',
                level_override=LogLevel.ERROR,
                tags=["connection"],
            ),
        ]

        # Stats
        self.stats = {
            "entries_processed": 0,
            "errors_detected": 0,
            "anomalies_detected": 0,
        }

    def ingest(
        self,
        log_line: str,
        service: str = "",
    ) -> LogEntry:
        """
        Ingest a log line.

        Args:
            log_line: Raw log line
            service: Source service name

        Returns:
            Parsed log entry
        """
        entry = self.parser.parse(log_line, service)

        # Check for anomalies
        for pattern in self._anomaly_patterns:
            if pattern.match(entry.message):
                entry.fields["detected_patterns"] = pattern.tags
                self.stats["anomalies_detected"] += 1

        self.store.add(entry)
        self.stats["entries_processed"] += 1

        if entry.level.value >= LogLevel.ERROR.value:
            self.stats["errors_detected"] += 1

        return entry

    def ingest_batch(
        self,
        log_lines: List[str],
        service: str = "",
    ) -> List[LogEntry]:
        """Ingest multiple log lines."""
        return [self.ingest(line, service) for line in log_lines]

    def search(self, query: LogQuery) -> List[LogEntry]:
        """Search logs."""
        return self.store.query(query)

    def search_text(
        self,
        text: str,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Simple text search."""
        return self.search(LogQuery(text=text, limit=limit))

    def get_trace(self, trace_id: str) -> List[LogEntry]:
        """Get all logs for a trace."""
        return self.store.get_by_trace(trace_id)

    def get_error_summary(
        self,
        duration: timedelta = timedelta(hours=1),
    ) -> Dict[str, Any]:
        """Get error summary for time period."""
        start = datetime.now() - duration

        query = LogQuery(
            levels=[LogLevel.ERROR, LogLevel.CRITICAL],
            start_time=start,
            limit=1000,
        )

        errors = self.search(query)

        # Group by message pattern
        error_groups: Dict[str, List[LogEntry]] = defaultdict(list)
        for entry in errors:
            # Simple grouping by first 50 chars
            key = entry.message[:50]
            error_groups[key].append(entry)

        return {
            "total_errors": len(errors),
            "unique_patterns": len(error_groups),
            "top_errors": [
                {
                    "pattern": k,
                    "count": len(v),
                    "first_seen": min(e.timestamp for e in v).isoformat(),
                    "last_seen": max(e.timestamp for e in v).isoformat(),
                }
                for k, v in sorted(error_groups.items(), key=lambda x: -len(x[1]))[:10]
            ],
        }

    def get_service_stats(self) -> Dict[str, Dict[str, int]]:
        """Get stats per service."""
        stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for entry in self.store._entries:
            stats[entry.service or "unknown"][entry.level.name] += 1

        return dict(stats)

    def add_pattern(self, pattern: LogPattern) -> None:
        """Add an anomaly detection pattern."""
        self._anomaly_patterns.append(pattern)

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            **self.stats,
            "store_size": self.store.count(),
            "patterns_count": len(self._anomaly_patterns),
        }


def demo():
    """Demonstrate log aggregator."""
    print("=" * 60)
    print("BAEL Log Aggregator Demo")
    print("=" * 60)

    aggregator = LogAggregator()

    # Sample logs
    sample_logs = [
        '{"timestamp": "2024-01-15T10:30:00Z", "level": "info", "message": "Server started", "service": "api"}',
        '{"timestamp": "2024-01-15T10:30:01Z", "level": "info", "message": "Connected to database", "service": "api"}',
        '{"timestamp": "2024-01-15T10:30:02Z", "level": "debug", "message": "Loaded 42 routes", "service": "api"}',
        '{"timestamp": "2024-01-15T10:30:10Z", "level": "info", "message": "Request: GET /api/users", "service": "api", "trace_id": "abc123"}',
        '{"timestamp": "2024-01-15T10:30:11Z", "level": "info", "message": "Query executed in 15ms", "service": "db", "trace_id": "abc123"}',
        '{"timestamp": "2024-01-15T10:30:12Z", "level": "error", "message": "Connection refused to cache server", "service": "cache"}',
        '{"timestamp": "2024-01-15T10:30:15Z", "level": "warning", "message": "Request timeout after 30s", "service": "api"}',
        '2024-01-15 10:30:20 ERROR Exception in request handler',
        '2024-01-15 10:30:21 INFO Retrying connection...',
        '2024-01-15 10:30:25 INFO Connection restored',
    ]

    print("\nIngesting logs...")
    for log in sample_logs:
        entry = aggregator.ingest(log)
        print(f"  [{entry.level.name}] {entry.message[:50]}")

    # Search
    print("\nSearching for 'connection'...")
    results = aggregator.search_text("connection")
    for entry in results:
        print(f"  [{entry.level.name}] {entry.message}")

    # Get trace
    print("\nTrace abc123:")
    trace = aggregator.get_trace("abc123")
    for entry in trace:
        print(f"  [{entry.service}] {entry.message}")

    # Error summary
    print("\nError summary:")
    summary = aggregator.get_error_summary()
    print(f"  Total errors: {summary['total_errors']}")
    print(f"  Unique patterns: {summary['unique_patterns']}")

    # Service stats
    print("\nService stats:")
    service_stats = aggregator.get_service_stats()
    for service, levels in service_stats.items():
        print(f"  {service}: {dict(levels)}")

    print(f"\nStats: {aggregator.get_stats()}")


if __name__ == "__main__":
    demo()
