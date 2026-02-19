"""
BAEL Alert Manager
===================

Alert management and notification system.
Monitors metrics and triggers alerts.

Features:
- Alert rules
- Multiple severities
- Notification channels
- Alert grouping
- Silencing
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(Enum):
    """Alert states."""
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class ComparisonOperator(Enum):
    """Comparison operators for rules."""
    GREATER_THAN = "gt"
    GREATER_EQUAL = "ge"
    LESS_THAN = "lt"
    LESS_EQUAL = "le"
    EQUAL = "eq"
    NOT_EQUAL = "ne"


@dataclass
class AlertRule:
    """A rule for generating alerts."""
    name: str
    description: str = ""

    # Condition
    metric_name: str = ""
    operator: ComparisonOperator = ComparisonOperator.GREATER_THAN
    threshold: float = 0.0

    # Labels filter
    label_filters: Dict[str, str] = field(default_factory=dict)

    # Alert config
    severity: AlertSeverity = AlertSeverity.WARNING
    for_duration: timedelta = field(default_factory=lambda: timedelta(minutes=1))

    # Additional labels for the alert
    alert_labels: Dict[str, str] = field(default_factory=dict)

    # Annotations (templates for alert message)
    annotations: Dict[str, str] = field(default_factory=dict)

    # Custom evaluation function
    custom_eval: Optional[Callable[[Dict[str, Any]], bool]] = None

    # State
    enabled: bool = True

    def evaluate(self, value: float) -> bool:
        """Evaluate rule against a value."""
        if self.operator == ComparisonOperator.GREATER_THAN:
            return value > self.threshold
        elif self.operator == ComparisonOperator.GREATER_EQUAL:
            return value >= self.threshold
        elif self.operator == ComparisonOperator.LESS_THAN:
            return value < self.threshold
        elif self.operator == ComparisonOperator.LESS_EQUAL:
            return value <= self.threshold
        elif self.operator == ComparisonOperator.EQUAL:
            return value == self.threshold
        elif self.operator == ComparisonOperator.NOT_EQUAL:
            return value != self.threshold
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "enabled": self.enabled,
        }


@dataclass
class Alert:
    """A triggered alert."""
    id: str
    rule_name: str

    # State
    state: AlertState = AlertState.PENDING
    severity: AlertSeverity = AlertSeverity.WARNING

    # Message
    summary: str = ""
    description: str = ""

    # Labels
    labels: Dict[str, str] = field(default_factory=dict)

    # Value
    value: float = 0.0
    threshold: float = 0.0

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    fired_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Notifications
    notifications_sent: List[str] = field(default_factory=list)

    def fire(self) -> None:
        """Mark alert as firing."""
        self.state = AlertState.FIRING
        self.fired_at = datetime.now()

    def resolve(self) -> None:
        """Mark alert as resolved."""
        self.state = AlertState.RESOLVED
        self.resolved_at = datetime.now()

    def silence(self) -> None:
        """Mark alert as silenced."""
        self.state = AlertState.SILENCED

    @property
    def duration(self) -> timedelta:
        """Get alert duration."""
        end = self.resolved_at or datetime.now()
        return end - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "state": self.state.value,
            "severity": self.severity.value,
            "summary": self.summary,
            "value": self.value,
            "started_at": self.started_at.isoformat(),
            "duration_seconds": self.duration.total_seconds(),
        }


class NotificationChannel:
    """Base class for notification channels."""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    def send(self, alert: Alert) -> bool:
        """Send notification. Returns success."""
        raise NotImplementedError

    def test(self) -> bool:
        """Test the channel."""
        return True


class ConsoleChannel(NotificationChannel):
    """Print alerts to console."""

    def __init__(self):
        super().__init__("console")

    def send(self, alert: Alert) -> bool:
        severity_colors = {
            AlertSeverity.INFO: "",
            AlertSeverity.WARNING: "⚠️ ",
            AlertSeverity.ERROR: "🔴 ",
            AlertSeverity.CRITICAL: "🚨 ",
        }

        prefix = severity_colors.get(alert.severity, "")
        print(f"{prefix}[ALERT] {alert.summary}")
        print(f"        Value: {alert.value} (threshold: {alert.threshold})")

        return True


class WebhookChannel(NotificationChannel):
    """Send alerts via webhook."""

    def __init__(self, name: str, url: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(name)
        self.url = url
        self.headers = headers or {}

    def send(self, alert: Alert) -> bool:
        """Send alert via webhook."""
        # In real implementation:
        # import requests
        # response = requests.post(
        #     self.url,
        #     json=alert.to_dict(),
        #     headers=self.headers,
        # )
        # return response.status_code == 200

        logger.info(f"Webhook: {self.url} <- {alert.summary}")
        return True


class SlackChannel(NotificationChannel):
    """Send alerts to Slack."""

    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        super().__init__("slack")
        self.webhook_url = webhook_url
        self.channel = channel

    def send(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        # In real implementation, format and send to Slack API
        logger.info(f"Slack {self.channel}: {alert.summary}")
        return True


@dataclass
class Silence:
    """A silence for suppressing alerts."""
    id: str

    # Matching
    matchers: Dict[str, str] = field(default_factory=dict)  # label -> regex

    # Duration
    starts_at: datetime = field(default_factory=datetime.now)
    ends_at: Optional[datetime] = None

    # Metadata
    created_by: str = ""
    comment: str = ""

    def matches(self, alert: Alert) -> bool:
        """Check if silence matches alert."""
        # Check if active
        now = datetime.now()
        if now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False

        # Check matchers
        for label, pattern in self.matchers.items():
            alert_value = alert.labels.get(label, "")
            if not re.match(pattern, alert_value):
                return False

        return True


class AlertManager:
    """
    Alert manager for BAEL.

    Manages alerts and notifications.
    """

    def __init__(self):
        # Rules
        self._rules: Dict[str, AlertRule] = {}

        # Active alerts
        self._alerts: Dict[str, Alert] = {}

        # Pending alerts (waiting for duration)
        self._pending: Dict[str, Tuple[Alert, datetime]] = {}

        # Notification channels
        self._channels: List[NotificationChannel] = []

        # Silences
        self._silences: Dict[str, Silence] = {}

        # History
        self._alert_history: List[Alert] = []

        # Stats
        self.stats = {
            "rules_evaluated": 0,
            "alerts_fired": 0,
            "alerts_resolved": 0,
            "notifications_sent": 0,
        }

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        """Remove an alert rule."""
        self._rules.pop(name, None)

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self._channels.append(channel)

    def add_silence(self, silence: Silence) -> None:
        """Add a silence."""
        self._silences[silence.id] = silence

    def remove_silence(self, silence_id: str) -> None:
        """Remove a silence."""
        self._silences.pop(silence_id, None)

    def _generate_alert_id(self, rule: AlertRule, labels: Dict[str, str]) -> str:
        """Generate unique alert ID."""
        key = f"{rule.name}:{sorted(labels.items())}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def evaluate(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[Alert]:
        """
        Evaluate rules against a metric value.

        Args:
            metric_name: Name of the metric
            value: Current value
            labels: Metric labels

        Returns:
            List of new/updated alerts
        """
        labels = labels or {}
        triggered_alerts = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            if rule.metric_name != metric_name:
                continue

            # Check label filters
            if rule.label_filters:
                matches = all(
                    labels.get(k) == v for k, v in rule.label_filters.items()
                )
                if not matches:
                    continue

            self.stats["rules_evaluated"] += 1

            # Evaluate condition
            if rule.evaluate(value):
                alert = self._handle_firing(rule, value, labels)
                if alert:
                    triggered_alerts.append(alert)
            else:
                self._handle_resolved(rule, labels)

        return triggered_alerts

    def _handle_firing(
        self,
        rule: AlertRule,
        value: float,
        labels: Dict[str, str],
    ) -> Optional[Alert]:
        """Handle a firing condition."""
        alert_id = self._generate_alert_id(rule, labels)

        # Already firing?
        if alert_id in self._alerts:
            return None

        # Already pending?
        if alert_id in self._pending:
            alert, start_time = self._pending[alert_id]

            # Check duration
            if datetime.now() - start_time >= rule.for_duration:
                # Fire!
                alert.fire()
                self._alerts[alert_id] = alert
                del self._pending[alert_id]

                # Check silences
                for silence in self._silences.values():
                    if silence.matches(alert):
                        alert.silence()
                        return alert

                # Send notifications
                self._notify(alert)
                self.stats["alerts_fired"] += 1

                return alert

            return None

        # Create new pending alert
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            summary=rule.annotations.get("summary", f"Alert: {rule.name}"),
            description=rule.annotations.get("description", rule.description),
            labels={**labels, **rule.alert_labels},
            value=value,
            threshold=rule.threshold,
        )

        self._pending[alert_id] = (alert, datetime.now())

        return None

    def _handle_resolved(self, rule: AlertRule, labels: Dict[str, str]) -> None:
        """Handle a resolved condition."""
        alert_id = self._generate_alert_id(rule, labels)

        # Remove from pending
        self._pending.pop(alert_id, None)

        # Resolve if firing
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.resolve()

            del self._alerts[alert_id]
            self._alert_history.append(alert)

            self.stats["alerts_resolved"] += 1

            # Send resolution notification
            self._notify(alert, resolved=True)

    def _notify(self, alert: Alert, resolved: bool = False) -> None:
        """Send notifications for an alert."""
        for channel in self._channels:
            if not channel.enabled:
                continue

            try:
                success = channel.send(alert)
                if success:
                    alert.notifications_sent.append(channel.name)
                    self.stats["notifications_sent"] += 1
            except Exception as e:
                logger.warning(f"Notification failed: {channel.name}: {e}")

    def get_firing_alerts(self) -> List[Alert]:
        """Get all firing alerts."""
        return list(self._alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return self._alert_history[-limit:]

    def get_rules(self) -> List[AlertRule]:
        """Get all rules."""
        return list(self._rules.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "rules_count": len(self._rules),
            "firing_count": len(self._alerts),
            "pending_count": len(self._pending),
            "channels_count": len(self._channels),
        }


def demo():
    """Demonstrate alert manager."""
    print("=" * 60)
    print("BAEL Alert Manager Demo")
    print("=" * 60)

    manager = AlertManager()

    # Add notification channel
    manager.add_channel(ConsoleChannel())

    # Add rules
    high_cpu = AlertRule(
        name="HighCPU",
        description="CPU usage is high",
        metric_name="cpu_percent",
        operator=ComparisonOperator.GREATER_THAN,
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        for_duration=timedelta(seconds=0),  # Immediate for demo
        annotations={
            "summary": "High CPU usage detected",
            "description": "CPU usage is above 80%",
        },
    )
    manager.add_rule(high_cpu)

    low_memory = AlertRule(
        name="LowMemory",
        description="Memory is running low",
        metric_name="memory_available_mb",
        operator=ComparisonOperator.LESS_THAN,
        threshold=1000,
        severity=AlertSeverity.CRITICAL,
        for_duration=timedelta(seconds=0),
        annotations={
            "summary": "Low memory warning",
            "description": "Available memory below 1GB",
        },
    )
    manager.add_rule(low_memory)

    print(f"\nRules configured: {len(manager.get_rules())}")
    for rule in manager.get_rules():
        print(f"  - {rule.name}: {rule.metric_name} {rule.operator.value} {rule.threshold}")

    # Simulate metric values
    print("\nEvaluating metrics...")

    # Normal values
    manager.evaluate("cpu_percent", 45.0)
    manager.evaluate("memory_available_mb", 4000)
    print("  CPU: 45% - OK")
    print("  Memory: 4000MB - OK")

    # High CPU
    print("\n  CPU spike detected:")
    alerts = manager.evaluate("cpu_percent", 95.0)

    # Low memory
    print("\n  Memory warning:")
    alerts = manager.evaluate("memory_available_mb", 500)

    # Check firing alerts
    print(f"\nFiring alerts: {len(manager.get_firing_alerts())}")
    for alert in manager.get_firing_alerts():
        print(f"  [{alert.severity.value}] {alert.summary}")

    # Resolve
    print("\n  System recovered:")
    manager.evaluate("cpu_percent", 30.0)
    manager.evaluate("memory_available_mb", 8000)

    print(f"\nFiring alerts: {len(manager.get_firing_alerts())}")
    print(f"\nStats: {manager.get_stats()}")


if __name__ == "__main__":
    demo()
