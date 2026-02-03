#!/usr/bin/env python3
"""
BAEL - Correlation Engine
Event correlation and pattern matching for agents.

Features:
- Event correlation rules
- Pattern matching
- Time-based correlation
- Causal analysis
- Alert aggregation
"""

import asyncio
import hashlib
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class EventType(Enum):
    """Event types."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    METRIC = "metric"
    LOG = "log"
    ALERT = "alert"
    TRACE = "trace"


class CorrelationType(Enum):
    """Correlation types."""
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    TOPOLOGICAL = "topological"
    STATISTICAL = "statistical"


class RuleOperator(Enum):
    """Rule operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    MATCHES = "matches"
    IN_LIST = "in_list"
    EXISTS = "exists"


class AggregationMethod(Enum):
    """Aggregation methods."""
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    FIRST = "first"
    LAST = "last"


class CorrelationStatus(Enum):
    """Correlation status."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Event:
    """An event to correlate."""
    event_id: str = ""
    event_type: EventType = EventType.INFO
    source: str = ""
    message: str = ""
    severity: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    attributes: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())[:8]


@dataclass
class RuleCondition:
    """A rule condition."""
    field: str = ""
    operator: RuleOperator = RuleOperator.EQUALS
    value: Any = None


@dataclass
class CorrelationRule:
    """A correlation rule."""
    rule_id: str = ""
    name: str = ""
    description: str = ""
    conditions: List[RuleCondition] = field(default_factory=list)
    time_window_seconds: float = 60.0
    min_events: int = 1
    max_events: Optional[int] = None
    group_by: List[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0

    def __post_init__(self):
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())[:8]


@dataclass
class CorrelatedEvent:
    """A correlated event group."""
    correlation_id: str = ""
    rule_id: str = ""
    rule_name: str = ""
    events: List[Event] = field(default_factory=list)
    status: CorrelationStatus = CorrelationStatus.ACTIVE
    first_event_time: datetime = field(default_factory=datetime.now)
    last_event_time: datetime = field(default_factory=datetime.now)
    count: int = 0
    group_key: str = ""
    severity: int = 1

    def __post_init__(self):
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())[:8]


@dataclass
class CausalLink:
    """A causal relationship."""
    link_id: str = ""
    cause_event_id: str = ""
    effect_event_id: str = ""
    confidence: float = 0.0
    delay_ms: float = 0.0

    def __post_init__(self):
        if not self.link_id:
            self.link_id = str(uuid.uuid4())[:8]


@dataclass
class CorrelationConfig:
    """Correlation engine configuration."""
    default_window_seconds: float = 60.0
    max_events_in_window: int = 1000
    enable_causal_analysis: bool = True
    dedup_window_seconds: float = 5.0


# =============================================================================
# RULE EVALUATOR
# =============================================================================

class RuleEvaluator:
    """Evaluate rule conditions."""

    def evaluate(self, event: Event, condition: RuleCondition) -> bool:
        """Evaluate a condition against an event."""
        value = self._get_field_value(event, condition.field)

        if condition.operator == RuleOperator.EXISTS:
            return value is not None

        if value is None:
            return False

        return self._compare(value, condition.operator, condition.value)

    def _get_field_value(self, event: Event, field: str) -> Any:
        """Get field value from event."""
        if field == "event_type":
            return event.event_type.value
        elif field == "source":
            return event.source
        elif field == "message":
            return event.message
        elif field == "severity":
            return event.severity
        elif field.startswith("attributes."):
            attr_name = field[11:]
            return event.attributes.get(attr_name)
        elif field.startswith("tags"):
            return event.tags
        else:
            return event.attributes.get(field)

    def _compare(self, value: Any, operator: RuleOperator, expected: Any) -> bool:
        """Compare values."""
        if operator == RuleOperator.EQUALS:
            return value == expected
        elif operator == RuleOperator.NOT_EQUALS:
            return value != expected
        elif operator == RuleOperator.CONTAINS:
            return str(expected) in str(value)
        elif operator == RuleOperator.STARTS_WITH:
            return str(value).startswith(str(expected))
        elif operator == RuleOperator.ENDS_WITH:
            return str(value).endswith(str(expected))
        elif operator == RuleOperator.GREATER_THAN:
            return float(value) > float(expected)
        elif operator == RuleOperator.LESS_THAN:
            return float(value) < float(expected)
        elif operator == RuleOperator.MATCHES:
            return bool(re.match(str(expected), str(value)))
        elif operator == RuleOperator.IN_LIST:
            if isinstance(expected, list):
                return value in expected
            return False
        return False

    def matches_rule(self, event: Event, rule: CorrelationRule) -> bool:
        """Check if event matches rule."""
        if not rule.enabled:
            return False

        for condition in rule.conditions:
            if not self.evaluate(event, condition):
                return False

        return True


# =============================================================================
# EVENT BUFFER
# =============================================================================

class EventBuffer:
    """Buffer events in time windows."""

    def __init__(self, max_size: int = 10000):
        self._events: deque = deque(maxlen=max_size)
        self._by_source: Dict[str, List[Event]] = defaultdict(list)
        self._max_size = max_size

    def add(self, event: Event) -> None:
        """Add event to buffer."""
        self._events.append(event)
        self._by_source[event.source].append(event)

        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up old events from source index."""
        cutoff = datetime.now() - timedelta(minutes=5)

        for source in list(self._by_source.keys()):
            self._by_source[source] = [
                e for e in self._by_source[source]
                if e.timestamp > cutoff
            ]
            if not self._by_source[source]:
                del self._by_source[source]

    def get_in_window(
        self,
        window_seconds: float,
        source: Optional[str] = None
    ) -> List[Event]:
        """Get events in time window."""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)

        if source:
            events = self._by_source.get(source, [])
        else:
            events = list(self._events)

        return [e for e in events if e.timestamp > cutoff]

    def get_by_source(self, source: str) -> List[Event]:
        """Get events by source."""
        return self._by_source.get(source, [])

    def count(self) -> int:
        """Count events in buffer."""
        return len(self._events)

    def clear(self) -> int:
        """Clear buffer."""
        count = len(self._events)
        self._events.clear()
        self._by_source.clear()
        return count


# =============================================================================
# GROUP KEY GENERATOR
# =============================================================================

class GroupKeyGenerator:
    """Generate group keys for correlation."""

    def generate(self, event: Event, group_by: List[str]) -> str:
        """Generate group key from event."""
        if not group_by:
            return "default"

        parts = []

        for field in group_by:
            value = self._get_field(event, field)
            parts.append(f"{field}={value}")

        key_str = "|".join(parts)

        return hashlib.md5(key_str.encode()).hexdigest()[:12]

    def _get_field(self, event: Event, field: str) -> str:
        """Get field value as string."""
        if field == "source":
            return event.source
        elif field == "event_type":
            return event.event_type.value
        elif field == "severity":
            return str(event.severity)
        elif field.startswith("attributes."):
            attr = field[11:]
            return str(event.attributes.get(attr, ""))
        else:
            return str(event.attributes.get(field, ""))


# =============================================================================
# CORRELATION MANAGER
# =============================================================================

class CorrelationManager:
    """Manage active correlations."""

    def __init__(self):
        self._correlations: Dict[str, CorrelatedEvent] = {}
        self._by_rule: Dict[str, Dict[str, str]] = defaultdict(dict)

    def get_or_create(
        self,
        rule: CorrelationRule,
        group_key: str,
        event: Event
    ) -> CorrelatedEvent:
        """Get or create correlation for rule/group."""
        lookup_key = f"{rule.rule_id}:{group_key}"

        if lookup_key in self._by_rule[rule.rule_id]:
            corr_id = self._by_rule[rule.rule_id][lookup_key]
            return self._correlations[corr_id]

        correlation = CorrelatedEvent(
            rule_id=rule.rule_id,
            rule_name=rule.name,
            group_key=group_key,
            first_event_time=event.timestamp
        )

        self._correlations[correlation.correlation_id] = correlation
        self._by_rule[rule.rule_id][lookup_key] = correlation.correlation_id

        return correlation

    def add_event(
        self,
        correlation: CorrelatedEvent,
        event: Event
    ) -> None:
        """Add event to correlation."""
        correlation.events.append(event)
        correlation.last_event_time = event.timestamp
        correlation.count = len(correlation.events)

        max_severity = max(e.severity for e in correlation.events)
        correlation.severity = max_severity

    def get(self, correlation_id: str) -> Optional[CorrelatedEvent]:
        """Get correlation by ID."""
        return self._correlations.get(correlation_id)

    def get_by_rule(self, rule_id: str) -> List[CorrelatedEvent]:
        """Get correlations for a rule."""
        corr_ids = self._by_rule.get(rule_id, {}).values()
        return [self._correlations[cid] for cid in corr_ids if cid in self._correlations]

    def get_active(self) -> List[CorrelatedEvent]:
        """Get active correlations."""
        return [
            c for c in self._correlations.values()
            if c.status == CorrelationStatus.ACTIVE
        ]

    def resolve(self, correlation_id: str) -> bool:
        """Resolve a correlation."""
        corr = self._correlations.get(correlation_id)
        if corr:
            corr.status = CorrelationStatus.RESOLVED
            return True
        return False

    def suppress(self, correlation_id: str) -> bool:
        """Suppress a correlation."""
        corr = self._correlations.get(correlation_id)
        if corr:
            corr.status = CorrelationStatus.SUPPRESSED
            return True
        return False

    def escalate(self, correlation_id: str) -> bool:
        """Escalate a correlation."""
        corr = self._correlations.get(correlation_id)
        if corr:
            corr.status = CorrelationStatus.ESCALATED
            return True
        return False

    def cleanup_expired(self, max_age_seconds: float) -> int:
        """Clean up expired correlations."""
        cutoff = datetime.now() - timedelta(seconds=max_age_seconds)

        to_remove = []

        for corr_id, corr in self._correlations.items():
            if corr.last_event_time < cutoff:
                to_remove.append(corr_id)

        for corr_id in to_remove:
            corr = self._correlations[corr_id]

            lookup_key = f"{corr.rule_id}:{corr.group_key}"
            if lookup_key in self._by_rule.get(corr.rule_id, {}):
                del self._by_rule[corr.rule_id][lookup_key]

            del self._correlations[corr_id]

        return len(to_remove)

    def count(self) -> int:
        """Count correlations."""
        return len(self._correlations)


# =============================================================================
# CAUSAL ANALYZER
# =============================================================================

class CausalAnalyzer:
    """Analyze causal relationships."""

    def __init__(self):
        self._links: Dict[str, CausalLink] = {}
        self._patterns: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def analyze(
        self,
        events: List[Event],
        max_delay_ms: float = 5000
    ) -> List[CausalLink]:
        """Analyze causal relationships in events."""
        links = []

        sorted_events = sorted(events, key=lambda e: e.timestamp)

        for i, cause in enumerate(sorted_events):
            for j in range(i + 1, len(sorted_events)):
                effect = sorted_events[j]

                delay = (effect.timestamp - cause.timestamp).total_seconds() * 1000

                if delay > max_delay_ms:
                    break

                confidence = self._calculate_confidence(cause, effect, delay)

                if confidence > 0.5:
                    link = CausalLink(
                        cause_event_id=cause.event_id,
                        effect_event_id=effect.event_id,
                        confidence=confidence,
                        delay_ms=delay
                    )
                    links.append(link)
                    self._links[link.link_id] = link

                    self._update_pattern(cause, effect)

        return links

    def _calculate_confidence(
        self,
        cause: Event,
        effect: Event,
        delay_ms: float
    ) -> float:
        """Calculate causal confidence."""
        confidence = 0.5

        if cause.source == effect.source:
            confidence += 0.2

        if cause.severity < effect.severity:
            confidence += 0.1

        time_factor = max(0, 1 - (delay_ms / 5000))
        confidence += 0.2 * time_factor

        pattern_key = f"{cause.event_type.value}:{cause.source}"
        effect_key = f"{effect.event_type.value}:{effect.source}"

        historical = self._patterns.get(pattern_key, {}).get(effect_key, 0)
        confidence += min(0.2, historical * 0.02)

        return min(1.0, confidence)

    def _update_pattern(self, cause: Event, effect: Event) -> None:
        """Update causal pattern."""
        pattern_key = f"{cause.event_type.value}:{cause.source}"
        effect_key = f"{effect.event_type.value}:{effect.source}"
        self._patterns[pattern_key][effect_key] += 1

    def get_causes(self, event_id: str) -> List[CausalLink]:
        """Get causes for an event."""
        return [l for l in self._links.values() if l.effect_event_id == event_id]

    def get_effects(self, event_id: str) -> List[CausalLink]:
        """Get effects of an event."""
        return [l for l in self._links.values() if l.cause_event_id == event_id]


# =============================================================================
# DEDUPLICATOR
# =============================================================================

class Deduplicator:
    """Deduplicate events."""

    def __init__(self, window_seconds: float = 5.0):
        self._window = window_seconds
        self._seen: Dict[str, datetime] = {}

    def is_duplicate(self, event: Event) -> bool:
        """Check if event is a duplicate."""
        key = self._generate_key(event)

        self._cleanup()

        if key in self._seen:
            return True

        self._seen[key] = datetime.now()
        return False

    def _generate_key(self, event: Event) -> str:
        """Generate dedup key."""
        key_str = f"{event.source}:{event.event_type.value}:{event.message}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _cleanup(self) -> None:
        """Clean up expired entries."""
        cutoff = datetime.now() - timedelta(seconds=self._window)

        self._seen = {k: v for k, v in self._seen.items() if v > cutoff}


# =============================================================================
# RULE MANAGER
# =============================================================================

class RuleManager:
    """Manage correlation rules."""

    def __init__(self):
        self._rules: Dict[str, CorrelationRule] = {}

    def add(self, rule: CorrelationRule) -> str:
        """Add a rule."""
        self._rules[rule.rule_id] = rule
        return rule.rule_id

    def get(self, rule_id: str) -> Optional[CorrelationRule]:
        """Get rule by ID."""
        return self._rules.get(rule_id)

    def get_by_name(self, name: str) -> Optional[CorrelationRule]:
        """Get rule by name."""
        for rule in self._rules.values():
            if rule.name == name:
                return rule
        return None

    def list(self, enabled_only: bool = False) -> List[CorrelationRule]:
        """List rules."""
        rules = list(self._rules.values())

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        rules.sort(key=lambda r: r.priority, reverse=True)

        return rules

    def enable(self, rule_id: str) -> bool:
        """Enable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable(self, rule_id: str) -> bool:
        """Disable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def delete(self, rule_id: str) -> bool:
        """Delete a rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def count(self) -> int:
        """Count rules."""
        return len(self._rules)


# =============================================================================
# CORRELATION ENGINE
# =============================================================================

class CorrelationEngine:
    """
    Correlation Engine for BAEL.

    Event correlation and pattern matching.
    """

    def __init__(self, config: Optional[CorrelationConfig] = None):
        self._config = config or CorrelationConfig()

        self._rules = RuleManager()
        self._evaluator = RuleEvaluator()
        self._buffer = EventBuffer(self._config.max_events_in_window)
        self._key_generator = GroupKeyGenerator()
        self._correlations = CorrelationManager()
        self._causal = CausalAnalyzer()
        self._dedup = Deduplicator(self._config.dedup_window_seconds)

        self._callbacks: List[Callable] = []

    # ----- Rule Management -----

    def create_rule(
        self,
        name: str,
        conditions: Optional[List[Dict[str, Any]]] = None,
        time_window: Optional[float] = None,
        min_events: int = 1,
        group_by: Optional[List[str]] = None
    ) -> CorrelationRule:
        """Create a correlation rule."""
        rule_conditions = []

        if conditions:
            for cond in conditions:
                rule_conditions.append(RuleCondition(
                    field=cond.get("field", ""),
                    operator=RuleOperator(cond.get("operator", "equals")),
                    value=cond.get("value")
                ))

        rule = CorrelationRule(
            name=name,
            conditions=rule_conditions,
            time_window_seconds=time_window or self._config.default_window_seconds,
            min_events=min_events,
            group_by=group_by or []
        )

        self._rules.add(rule)

        return rule

    def get_rule(self, rule_id: str) -> Optional[CorrelationRule]:
        """Get rule by ID."""
        return self._rules.get(rule_id)

    def get_rule_by_name(self, name: str) -> Optional[CorrelationRule]:
        """Get rule by name."""
        return self._rules.get_by_name(name)

    def list_rules(self, enabled_only: bool = False) -> List[CorrelationRule]:
        """List all rules."""
        return self._rules.list(enabled_only)

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        return self._rules.enable(rule_id)

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        return self._rules.disable(rule_id)

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        return self._rules.delete(rule_id)

    # ----- Event Processing -----

    def process_event(self, event: Event) -> List[CorrelatedEvent]:
        """Process an event through correlation rules."""
        if self._dedup.is_duplicate(event):
            return []

        self._buffer.add(event)

        correlated = []

        for rule in self._rules.list(enabled_only=True):
            if self._evaluator.matches_rule(event, rule):
                correlation = self._correlate(event, rule)
                if correlation:
                    correlated.append(correlation)

        if self._config.enable_causal_analysis:
            recent = self._buffer.get_in_window(5.0)
            self._causal.analyze(recent)

        for callback in self._callbacks:
            for corr in correlated:
                callback(corr)

        return correlated

    def _correlate(
        self,
        event: Event,
        rule: CorrelationRule
    ) -> Optional[CorrelatedEvent]:
        """Correlate event with rule."""
        group_key = self._key_generator.generate(event, rule.group_by)

        correlation = self._correlations.get_or_create(rule, group_key, event)

        window_start = datetime.now() - timedelta(seconds=rule.time_window_seconds)

        if correlation.first_event_time < window_start:
            correlation = self._correlations.get_or_create(rule, group_key + "_new", event)

        self._correlations.add_event(correlation, event)

        if correlation.count >= rule.min_events:
            if rule.max_events and correlation.count > rule.max_events:
                return None
            return correlation

        return None

    def emit(
        self,
        event_type: EventType,
        source: str,
        message: str,
        severity: int = 1,
        attributes: Optional[Dict[str, Any]] = None
    ) -> List[CorrelatedEvent]:
        """Emit and process an event."""
        event = Event(
            event_type=event_type,
            source=source,
            message=message,
            severity=severity,
            attributes=attributes or {}
        )

        return self.process_event(event)

    # ----- Correlation Management -----

    def get_correlation(self, correlation_id: str) -> Optional[CorrelatedEvent]:
        """Get correlation by ID."""
        return self._correlations.get(correlation_id)

    def get_active_correlations(self) -> List[CorrelatedEvent]:
        """Get active correlations."""
        return self._correlations.get_active()

    def get_correlations_for_rule(self, rule_id: str) -> List[CorrelatedEvent]:
        """Get correlations for a rule."""
        return self._correlations.get_by_rule(rule_id)

    def resolve_correlation(self, correlation_id: str) -> bool:
        """Resolve a correlation."""
        return self._correlations.resolve(correlation_id)

    def suppress_correlation(self, correlation_id: str) -> bool:
        """Suppress a correlation."""
        return self._correlations.suppress(correlation_id)

    def escalate_correlation(self, correlation_id: str) -> bool:
        """Escalate a correlation."""
        return self._correlations.escalate(correlation_id)

    # ----- Causal Analysis -----

    def get_causes(self, event_id: str) -> List[CausalLink]:
        """Get causes for an event."""
        return self._causal.get_causes(event_id)

    def get_effects(self, event_id: str) -> List[CausalLink]:
        """Get effects of an event."""
        return self._causal.get_effects(event_id)

    # ----- Callbacks -----

    def on_correlation(self, callback: Callable) -> None:
        """Add correlation callback."""
        self._callbacks.append(callback)

    # ----- Maintenance -----

    def cleanup(self) -> int:
        """Clean up expired correlations."""
        return self._correlations.cleanup_expired(
            self._config.default_window_seconds * 2
        )

    def clear_buffer(self) -> int:
        """Clear event buffer."""
        return self._buffer.clear()

    # ----- Stats -----

    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        return {
            "rules": self._rules.count(),
            "enabled_rules": len(self._rules.list(enabled_only=True)),
            "buffered_events": self._buffer.count(),
            "active_correlations": len(self._correlations.get_active()),
            "total_correlations": self._correlations.count()
        }

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "rules": self._rules.count(),
            "correlations": self._correlations.count(),
            "buffered_events": self._buffer.count(),
            "causal_analysis": self._config.enable_causal_analysis,
            "default_window": self._config.default_window_seconds
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Correlation Engine."""
    print("=" * 70)
    print("BAEL - CORRELATION ENGINE DEMO")
    print("Event Correlation & Pattern Matching")
    print("=" * 70)
    print()

    engine = CorrelationEngine()

    # 1. Create Correlation Rules
    print("1. CREATE CORRELATION RULES:")
    print("-" * 40)

    error_rule = engine.create_rule(
        name="repeated_errors",
        conditions=[
            {"field": "event_type", "operator": "equals", "value": "error"},
            {"field": "severity", "operator": "greater_than", "value": 2}
        ],
        time_window=30.0,
        min_events=3,
        group_by=["source"]
    )
    print(f"   Created: {error_rule.name} ({error_rule.rule_id})")

    db_rule = engine.create_rule(
        name="database_issues",
        conditions=[
            {"field": "source", "operator": "starts_with", "value": "database"},
            {"field": "event_type", "operator": "in_list", "value": ["error", "warning"]}
        ],
        time_window=60.0,
        min_events=2
    )
    print(f"   Created: {db_rule.name} ({db_rule.rule_id})")

    alert_rule = engine.create_rule(
        name="critical_alerts",
        conditions=[
            {"field": "event_type", "operator": "equals", "value": "critical"},
        ],
        min_events=1
    )
    print(f"   Created: {alert_rule.name} ({alert_rule.rule_id})")
    print()

    # 2. List Rules
    print("2. LIST RULES:")
    print("-" * 40)

    for rule in engine.list_rules():
        print(f"   - {rule.name}: {len(rule.conditions)} conditions, window={rule.time_window_seconds}s")
    print()

    # 3. Process Events
    print("3. PROCESS EVENTS:")
    print("-" * 40)

    correlations = []

    events = [
        Event(event_type=EventType.ERROR, source="api-server", message="Request timeout", severity=3),
        Event(event_type=EventType.ERROR, source="api-server", message="Connection failed", severity=3),
        Event(event_type=EventType.ERROR, source="api-server", message="Service unavailable", severity=4),
        Event(event_type=EventType.WARNING, source="database-primary", message="Slow query detected", severity=2),
        Event(event_type=EventType.ERROR, source="database-primary", message="Connection pool exhausted", severity=4),
        Event(event_type=EventType.CRITICAL, source="auth-service", message="Authentication failure", severity=5),
    ]

    for event in events:
        result = engine.process_event(event)
        correlations.extend(result)
        print(f"   Processed: {event.source} - {event.message}")
        if result:
            for c in result:
                print(f"     -> Correlated: {c.rule_name} (count={c.count})")
    print()

    # 4. Active Correlations
    print("4. ACTIVE CORRELATIONS:")
    print("-" * 40)

    active = engine.get_active_correlations()
    print(f"   Active correlations: {len(active)}")
    for corr in active:
        print(f"   - {corr.rule_name}: {corr.count} events, severity={corr.severity}")
    print()

    # 5. Emit Events
    print("5. EMIT EVENTS:")
    print("-" * 40)

    result = engine.emit(
        EventType.ERROR,
        source="api-server",
        message="Another error occurred",
        severity=3
    )
    print(f"   Emitted error event")
    if result:
        print(f"   Correlations triggered: {len(result)}")
    print()

    # 6. Get Correlation Details
    print("6. CORRELATION DETAILS:")
    print("-" * 40)

    if active:
        corr = active[0]
        print(f"   Correlation: {corr.correlation_id}")
        print(f"   Rule: {corr.rule_name}")
        print(f"   Status: {corr.status.value}")
        print(f"   Events: {corr.count}")
        print(f"   First event: {corr.first_event_time}")
        print(f"   Last event: {corr.last_event_time}")
        print(f"   Severity: {corr.severity}")
    print()

    # 7. Correlation Callbacks
    print("7. CORRELATION CALLBACKS:")
    print("-" * 40)

    callback_count = [0]

    def on_correlation(corr: CorrelatedEvent):
        callback_count[0] += 1
        print(f"   [Callback] Correlation: {corr.rule_name}")

    engine.on_correlation(on_correlation)

    engine.emit(EventType.CRITICAL, "alert-system", "System alert", severity=5)

    print(f"   Callbacks triggered: {callback_count[0]}")
    print()

    # 8. Causal Analysis
    print("8. CAUSAL ANALYSIS:")
    print("-" * 40)

    if events:
        causes = engine.get_causes(events[-1].event_id)
        effects = engine.get_effects(events[0].event_id)

        print(f"   Causes for last event: {len(causes)}")
        for link in causes[:3]:
            print(f"   - Confidence: {link.confidence:.2f}, delay: {link.delay_ms:.0f}ms")

        print(f"   Effects of first event: {len(effects)}")
    print()

    # 9. Resolve Correlation
    print("9. RESOLVE CORRELATION:")
    print("-" * 40)

    if active:
        corr_id = active[0].correlation_id
        engine.resolve_correlation(corr_id)

        corr = engine.get_correlation(corr_id)
        print(f"   Resolved: {corr_id}")
        print(f"   New status: {corr.status.value}")
    print()

    # 10. Escalate Correlation
    print("10. ESCALATE CORRELATION:")
    print("-" * 40)

    current_active = engine.get_active_correlations()
    if current_active:
        corr_id = current_active[0].correlation_id
        engine.escalate_correlation(corr_id)

        corr = engine.get_correlation(corr_id)
        print(f"   Escalated: {corr_id}")
        print(f"   New status: {corr.status.value}")
    else:
        print("   No active correlations to escalate")
    print()

    # 11. Enable/Disable Rules
    print("11. ENABLE/DISABLE RULES:")
    print("-" * 40)

    print(f"   Before: {len(engine.list_rules(enabled_only=True))} enabled rules")

    engine.disable_rule(error_rule.rule_id)
    print(f"   Disabled: {error_rule.name}")

    print(f"   After: {len(engine.list_rules(enabled_only=True))} enabled rules")

    engine.enable_rule(error_rule.rule_id)
    print(f"   Re-enabled: {error_rule.name}")
    print()

    # 12. Rule-specific Correlations
    print("12. RULE-SPECIFIC CORRELATIONS:")
    print("-" * 40)

    for rule in engine.list_rules():
        correlations = engine.get_correlations_for_rule(rule.rule_id)
        print(f"   {rule.name}: {len(correlations)} correlations")
    print()

    # 13. Cleanup
    print("13. CLEANUP:")
    print("-" * 40)

    expired = engine.cleanup()
    print(f"   Expired correlations cleaned: {expired}")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Correlation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
