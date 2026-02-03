"""
Monitoring, Logging & Observability - Distributed tracing and health monitoring.

Features:
- Distributed tracing across systems
- Comprehensive logging with structured output
- Real-time metrics collection
- Health checks and service discovery
- Alert management and routing
- SLA tracking

Target: 1,600+ lines for complete monitoring system
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# ============================================================================
# MONITORING ENUMS
# ============================================================================

class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

class TraceStatus(Enum):
    """Span/trace status."""
    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Span:
    """Distributed trace span."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation: str

    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0

    status: TraceStatus = TraceStatus.OK
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self) -> None:
        """Mark span as finished."""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            'span_id': self.span_id,
            'trace_id': self.trace_id,
            'operation': self.operation,
            'duration_ms': self.duration_ms,
            'status': self.status.value,
            'tags': self.tags
        }

@dataclass
class LogEntry:
    """Structured log entry."""
    log_id: str
    timestamp: datetime
    level: LogLevel
    message: str
    component: str

    context: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'log_id': self.log_id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.name,
            'message': self.message,
            'component': self.component,
            'context': self.context
        }

@dataclass
class HealthCheck:
    """Health check for component."""
    check_id: str
    component: str
    timestamp: datetime
    status: HealthStatus
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'check_id': self.check_id,
            'component': self.component,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'response_ms': self.response_time_ms,
            'details': self.details
        }

@dataclass
class Alert:
    """System alert."""
    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)

    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    def acknowledge(self, user_id: str) -> None:
        """Acknowledge alert."""
        self.acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'severity': self.severity.name,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged
        }

@dataclass
class SLA:
    """Service Level Agreement."""
    sla_id: str
    service: str
    availability_target: float  # e.g., 0.99 for 99%
    response_time_p99_ms: float
    error_rate_target: float

    tracked_uptime: float = 0.0
    tracked_response_time: float = 0.0
    tracked_error_rate: float = 0.0

    def is_met(self) -> bool:
        """Check if SLA targets are met."""
        return (self.tracked_uptime >= self.availability_target and
                self.tracked_response_time <= self.response_time_p99_ms and
                self.tracked_error_rate <= self.error_rate_target)

# ============================================================================
# DISTRIBUTED TRACER
# ============================================================================

class DistributedTracer:
    """Distributed tracing system."""

    def __init__(self, max_spans: int = 10000):
        self.spans: Dict[str, Span] = {}
        self.traces: Dict[str, List[str]] = defaultdict(list)  # trace_id -> span_ids
        self.span_cache: deque = deque(maxlen=max_spans)
        self.logger = logging.getLogger("distributed_tracer")

    def start_trace(self) -> str:
        """Start new trace."""
        trace_id = f"trace-{uuid.uuid4().hex[:16]}"
        self.traces[trace_id] = []
        return trace_id

    def start_span(self, trace_id: str, operation: str,
                   parent_span_id: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> Span:
        """Start new span."""
        span = Span(
            span_id=f"span-{uuid.uuid4().hex[:8]}",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation=operation,
            start_time=datetime.now(),
            tags=tags or {}
        )

        self.spans[span.span_id] = span
        self.traces[trace_id].append(span.span_id)
        self.span_cache.append(span)

        return span

    def finish_span(self, span: Span, status: TraceStatus = TraceStatus.OK) -> None:
        """Finish span."""
        span.finish()
        span.status = status

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get complete trace."""
        if trace_id not in self.traces:
            return None

        span_ids = self.traces[trace_id]
        spans = [self.spans[sid].to_dict() for sid in span_ids if sid in self.spans]

        total_duration = sum(s['duration_ms'] for s in spans)

        return {
            'trace_id': trace_id,
            'spans': spans,
            'total_duration_ms': total_duration,
            'span_count': len(spans)
        }

    def get_slow_traces(self, threshold_ms: float = 1000,
                       limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow traces."""
        slow = []

        for trace_id in self.traces:
            trace = self.get_trace(trace_id)
            if trace and trace['total_duration_ms'] > threshold_ms:
                slow.append(trace)

        slow.sort(key=lambda x: x['total_duration_ms'], reverse=True)
        return slow[:limit]

# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

class StructuredLogger:
    """Structured logging system."""

    def __init__(self, max_logs: int = 50000):
        self.logs: List[LogEntry] = []
        self.log_cache: deque = deque(maxlen=max_logs)
        self.logger = logging.getLogger("structured_logger")

    def log(self, level: LogLevel, message: str, component: str,
            context: Optional[Dict[str, Any]] = None,
            trace_id: Optional[str] = None,
            span_id: Optional[str] = None) -> str:
        """Create log entry."""
        entry = LogEntry(
            log_id=f"log-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            level=level,
            message=message,
            component=component,
            context=context or {},
            trace_id=trace_id,
            span_id=span_id
        )

        self.logs.append(entry)
        self.log_cache.append(entry)

        # Also log to Python logging
        getattr(logging.getLogger(component), level.name.lower())(
            f"{message} {json.dumps(context or {})}"
        )

        return entry.log_id

    def search_logs(self, component: Optional[str] = None,
                   level: Optional[LogLevel] = None,
                   trace_id: Optional[str] = None,
                   hours: int = 24,
                   limit: int = 1000) -> List[LogEntry]:
        """Search logs."""
        cutoff = datetime.now() - timedelta(hours=hours)

        results = [l for l in self.logs
                  if l.timestamp >= cutoff]

        if component:
            results = [l for l in results if l.component == component]

        if level:
            results = [l for l in results if l.level.value >= level.value]

        if trace_id:
            results = [l for l in results if l.trace_id == trace_id]

        return results[-limit:]

    def get_error_logs(self, hours: int = 1) -> List[LogEntry]:
        """Get error logs."""
        return self.search_logs(level=LogLevel.ERROR, hours=hours)

# ============================================================================
# HEALTH CHECK MANAGER
# ============================================================================

class HealthCheckManager:
    """Manage health checks."""

    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.check_handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("health_check")

    def register_check(self, component: str, handler: Callable) -> None:
        """Register health check."""
        self.check_handlers[component] = handler
        self.logger.info(f"Registered health check for {component}")

    async def run_check(self, component: str) -> Optional[HealthCheck]:
        """Run health check."""
        if component not in self.check_handlers:
            return None

        start = datetime.now()

        try:
            handler = self.check_handlers[component]

            if asyncio.iscoroutinefunction(handler):
                result = await handler()
            else:
                result = handler()

            response_time = (datetime.now() - start).total_seconds() * 1000

            check = HealthCheck(
                check_id=f"chk-{uuid.uuid4().hex[:8]}",
                component=component,
                timestamp=datetime.now(),
                status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                details={'result': str(result)}
            )

        except Exception as e:
            response_time = (datetime.now() - start).total_seconds() * 1000

            check = HealthCheck(
                check_id=f"chk-{uuid.uuid4().hex[:8]}",
                component=component,
                timestamp=datetime.now(),
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                details={'error': str(e)}
            )

        self.checks.append(check)
        return check

    async def run_all_checks(self) -> List[HealthCheck]:
        """Run all health checks."""
        results = []

        for component in self.check_handlers:
            check = await self.run_check(component)
            if check:
                results.append(check)

        return results

    def get_unhealthy_components(self) -> List[str]:
        """Get unhealthy components."""
        recent_checks = {}

        for check in self.checks[-100:]:
            if check.component not in recent_checks:
                recent_checks[check.component] = check

        return [c for c, check in recent_checks.items()
                if check.status != HealthStatus.HEALTHY]

# ============================================================================
# ALERT MANAGER
# ============================================================================

class AlertManager:
    """Manage system alerts."""

    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_routes: Dict[AlertSeverity, List[Callable]] = defaultdict(list)
        self.logger = logging.getLogger("alert_manager")

    def register_route(self, severity: AlertSeverity, handler: Callable) -> None:
        """Register alert route."""
        self.alert_routes[severity].append(handler)

    async def create_alert(self, severity: AlertSeverity, title: str,
                          description: str, source: str) -> str:
        """Create alert."""
        alert = Alert(
            alert_id=f"alrt-{uuid.uuid4().hex[:16]}",
            severity=severity,
            title=title,
            description=description,
            source=source
        )

        self.alerts.append(alert)

        # Route alert
        handlers = self.alert_routes.get(severity, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"Error in alert handler: {e}")

        return alert.alert_id

    def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledge(user_id)
                return True
        return False

    def get_open_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get unacknowledged alerts."""
        alerts = [a for a in self.alerts if not a.acknowledged]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        by_severity = defaultdict(int)

        for alert in self.alerts:
            by_severity[alert.severity.name] += 1

        open_count = sum(1 for a in self.alerts if not a.acknowledged)

        return {
            'total_alerts': len(self.alerts),
            'open_alerts': open_count,
            'by_severity': dict(by_severity)
        }

# ============================================================================
# SLA TRACKER
# ============================================================================

class SLATracker:
    """Track SLA compliance."""

    def __init__(self):
        self.slas: Dict[str, SLA] = {}
        self.logger = logging.getLogger("sla_tracker")

    def register_sla(self, service: str, availability_target: float,
                    response_time_p99: float, error_rate_target: float) -> str:
        """Register SLA."""
        sla_id = f"sla-{uuid.uuid4().hex[:8]}"

        sla = SLA(
            sla_id=sla_id,
            service=service,
            availability_target=availability_target,
            response_time_p99_ms=response_time_p99,
            error_rate_target=error_rate_target
        )

        self.slas[sla_id] = sla
        self.logger.info(f"Registered SLA for {service}")
        return sla_id

    def update_metrics(self, sla_id: str, uptime: float,
                      response_time: float, error_rate: float) -> None:
        """Update SLA metrics."""
        if sla_id in self.slas:
            sla = self.slas[sla_id]
            sla.tracked_uptime = uptime
            sla.tracked_response_time = response_time
            sla.tracked_error_rate = error_rate

    def get_sla_compliance(self) -> Dict[str, Any]:
        """Get SLA compliance."""
        compliant = sum(1 for s in self.slas.values() if s.is_met())

        services = {
            sla.service: {
                'compliant': sla.is_met(),
                'uptime': sla.tracked_uptime,
                'response_time': sla.tracked_response_time,
                'error_rate': sla.tracked_error_rate
            }
            for sla in self.slas.values()
        }

        return {
            'compliant_slas': compliant,
            'total_slas': len(self.slas),
            'services': services
        }

# ============================================================================
# MONITORING SYSTEM
# ============================================================================

class MonitoringSystem:
    """Complete monitoring system."""

    def __init__(self):
        self.tracer = DistributedTracer()
        self.logger_sys = StructuredLogger()
        self.health_check_mgr = HealthCheckManager()
        self.alert_mgr = AlertManager()
        self.sla_tracker = SLATracker()

        self.logger = logging.getLogger("monitoring")

    def get_system_observability(self) -> Dict[str, Any]:
        """Get complete observability dashboard."""
        unhealthy = self.health_check_mgr.get_unhealthy_components()
        open_alerts = self.alert_mgr.get_open_alerts()
        sla_compliance = self.sla_tracker.get_sla_compliance()

        return {
            'timestamp': datetime.now().isoformat(),
            'components_unhealthy': len(unhealthy),
            'open_alerts': len(open_alerts),
            'critical_alerts': len([a for a in open_alerts if a.severity == AlertSeverity.CRITICAL]),
            'sla_compliant': sla_compliance['compliant_slas'],
            'total_slas': sla_compliance['total_slas'],
            'recent_errors': len(self.logger_sys.get_error_logs()),
            'traces_active': len(self.tracer.traces)
        }

def create_monitoring_system() -> MonitoringSystem:
    """Create monitoring system."""
    return MonitoringSystem()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    monitoring = create_monitoring_system()
    print("Monitoring system initialized")
