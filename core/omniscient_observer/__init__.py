"""
BAEL Omniscient Observer Engine
================================

All-seeing observation and monitoring system.

"Ba'el sees all." — Ba'el
"""

import logging
import threading
import time
import asyncio
import weakref
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import copy
import traceback
import sys

logger = logging.getLogger("BAEL.OmniscientObserver")


T = TypeVar('T')


# ============================================================================
# OBSERVATION TYPES
# ============================================================================

class ObservationType(Enum):
    """Types of observations."""
    FUNCTION_CALL = auto()
    FUNCTION_RETURN = auto()
    EXCEPTION = auto()
    STATE_CHANGE = auto()
    METRIC = auto()
    EVENT = auto()
    THOUGHT = auto()          # Internal reasoning
    DECISION = auto()         # Decision made
    PREDICTION = auto()       # Prediction made
    MEMORY_ACCESS = auto()    # Memory read/write


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    ANOMALY = 5


# ============================================================================
# OBSERVATION
# ============================================================================

@dataclass
class Observation:
    """
    A single observation.
    """
    id: str
    observation_type: ObservationType
    timestamp: float
    source: str
    data: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    alert_level: Optional[AlertLevel] = None
    tags: List[str] = field(default_factory=list)

    @property
    def age_ms(self) -> float:
        return (time.time() - self.timestamp) * 1000


@dataclass
class Alert:
    """
    An alert triggered by observations.
    """
    id: str
    level: AlertLevel
    message: str
    observations: List[str]  # Observation IDs
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False


# ============================================================================
# OBSERVER INTERFACE
# ============================================================================

class Observer(ABC):
    """Base observer interface."""

    @abstractmethod
    def observe(self, observation: Observation) -> None:
        """Process an observation."""
        pass

    @abstractmethod
    def get_insights(self) -> Dict[str, Any]:
        """Get insights from observations."""
        pass


# ============================================================================
# METRIC COLLECTOR
# ============================================================================

class MetricCollector(Observer):
    """
    Collect and aggregate metrics.

    "Ba'el measures all." — Ba'el
    """

    def __init__(self, window_size: int = 1000):
        """Initialize collector."""
        self._window_size = window_size
        self._metrics: Dict[str, List[Tuple[float, float]]] = {}  # name -> [(timestamp, value)]
        self._aggregates: Dict[str, Dict[str, float]] = {}
        self._lock = threading.RLock()

    def observe(self, observation: Observation) -> None:
        """Process metric observation."""
        if observation.observation_type != ObservationType.METRIC:
            return

        with self._lock:
            name = observation.data.get('name', 'unknown')
            value = observation.data.get('value', 0.0)

            if name not in self._metrics:
                self._metrics[name] = []

            self._metrics[name].append((observation.timestamp, value))

            # Trim to window
            if len(self._metrics[name]) > self._window_size:
                self._metrics[name] = self._metrics[name][-self._window_size:]

            # Update aggregates
            self._update_aggregates(name)

    def _update_aggregates(self, name: str) -> None:
        """Update aggregates for metric."""
        values = [v for _, v in self._metrics[name]]
        if not values:
            return

        self._aggregates[name] = {
            'count': len(values),
            'sum': sum(values),
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
            'last': values[-1]
        }

    def record(self, name: str, value: float) -> None:
        """Record metric directly."""
        obs = Observation(
            id=f"metric_{time.time()}",
            observation_type=ObservationType.METRIC,
            timestamp=time.time(),
            source="direct",
            data={'name': name, 'value': value}
        )
        self.observe(obs)

    def get(self, name: str) -> Optional[Dict[str, float]]:
        """Get aggregates for metric."""
        return self._aggregates.get(name)

    def get_insights(self) -> Dict[str, Any]:
        """Get all metric insights."""
        with self._lock:
            return {
                'metrics': list(self._metrics.keys()),
                'aggregates': copy.deepcopy(self._aggregates)
            }


# ============================================================================
# TRACE COLLECTOR
# ============================================================================

@dataclass
class TraceSpan:
    """A span in a distributed trace."""
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    operation: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict] = field(default_factory=list)
    status: str = "ok"

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


class TraceCollector(Observer):
    """
    Collect distributed traces.

    "Ba'el traces all paths." — Ba'el
    """

    def __init__(self, max_traces: int = 1000):
        """Initialize trace collector."""
        self._max_traces = max_traces
        self._traces: Dict[str, List[TraceSpan]] = {}
        self._active_spans: Dict[str, TraceSpan] = {}
        self._span_id = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._span_id += 1
        return f"span_{self._span_id}"

    def start_span(
        self,
        trace_id: str,
        operation: str,
        parent_id: Optional[str] = None
    ) -> TraceSpan:
        """Start new span."""
        with self._lock:
            span = TraceSpan(
                trace_id=trace_id,
                span_id=self._generate_id(),
                parent_id=parent_id,
                operation=operation,
                start_time=time.time()
            )

            self._active_spans[span.span_id] = span

            if trace_id not in self._traces:
                self._traces[trace_id] = []
            self._traces[trace_id].append(span)

            return span

    def end_span(self, span_id: str, status: str = "ok") -> None:
        """End span."""
        with self._lock:
            if span_id in self._active_spans:
                span = self._active_spans[span_id]
                span.end_time = time.time()
                span.status = status
                del self._active_spans[span_id]

    def add_log(self, span_id: str, message: str, data: Optional[Dict] = None) -> None:
        """Add log to span."""
        with self._lock:
            if span_id in self._active_spans:
                self._active_spans[span_id].logs.append({
                    'timestamp': time.time(),
                    'message': message,
                    'data': data or {}
                })

    def observe(self, observation: Observation) -> None:
        """Process trace-related observation."""
        if observation.observation_type == ObservationType.FUNCTION_CALL:
            trace_id = observation.context.get('trace_id', 'default')
            parent_id = observation.context.get('parent_span')
            self.start_span(trace_id, observation.data.get('function', 'unknown'), parent_id)

        elif observation.observation_type == ObservationType.FUNCTION_RETURN:
            span_id = observation.context.get('span_id')
            if span_id:
                self.end_span(span_id)

    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for trace."""
        return self._traces.get(trace_id, [])

    def get_insights(self) -> Dict[str, Any]:
        """Get trace insights."""
        with self._lock:
            total_spans = sum(len(spans) for spans in self._traces.values())
            active = len(self._active_spans)

            # Calculate average duration
            durations = []
            for spans in self._traces.values():
                for span in spans:
                    if span.duration_ms:
                        durations.append(span.duration_ms)

            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                'total_traces': len(self._traces),
                'total_spans': total_spans,
                'active_spans': active,
                'avg_duration_ms': avg_duration
            }


# ============================================================================
# ANOMALY DETECTOR
# ============================================================================

class AnomalyDetector(Observer):
    """
    Detect anomalies in observations.

    "Ba'el detects the unusual." — Ba'el
    """

    def __init__(self, sensitivity: float = 2.0):
        """
        Initialize anomaly detector.

        Args:
            sensitivity: Number of std devs for anomaly threshold
        """
        self._sensitivity = sensitivity
        self._baselines: Dict[str, Dict[str, float]] = {}
        self._observations: Dict[str, List[float]] = {}
        self._anomalies: List[Tuple[str, Observation]] = []
        self._lock = threading.RLock()

    def observe(self, observation: Observation) -> None:
        """Check for anomalies."""
        if observation.observation_type != ObservationType.METRIC:
            return

        with self._lock:
            name = observation.data.get('name', 'unknown')
            value = observation.data.get('value', 0.0)

            if name not in self._observations:
                self._observations[name] = []

            self._observations[name].append(value)

            # Need enough data for baseline
            if len(self._observations[name]) < 30:
                return

            # Update baseline
            self._update_baseline(name)

            # Check for anomaly
            baseline = self._baselines.get(name, {})
            mean = baseline.get('mean', value)
            std = baseline.get('std', 0)

            if std > 0:
                z_score = abs(value - mean) / std
                if z_score > self._sensitivity:
                    self._anomalies.append((
                        f"Anomaly in {name}: value={value}, z-score={z_score:.2f}",
                        observation
                    ))
                    observation.alert_level = AlertLevel.ANOMALY

    def _update_baseline(self, name: str) -> None:
        """Update baseline statistics."""
        values = self._observations[name][-100:]  # Last 100

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5

        self._baselines[name] = {
            'mean': mean,
            'std': std,
            'min': min(values),
            'max': max(values)
        }

    def get_insights(self) -> Dict[str, Any]:
        """Get anomaly insights."""
        with self._lock:
            return {
                'total_anomalies': len(self._anomalies),
                'recent_anomalies': [msg for msg, _ in self._anomalies[-10:]],
                'baselines': copy.deepcopy(self._baselines)
            }


# ============================================================================
# OMNISCIENT OBSERVER
# ============================================================================

class OmniscientObserver:
    """
    All-seeing observer system.

    "Ba'el observes the cosmos." — Ba'el
    """

    def __init__(self):
        """Initialize omniscient observer."""
        self._observers: List[Observer] = []
        self._observations: List[Observation] = []
        self._alerts: List[Alert] = []
        self._max_observations = 10000
        self._obs_id = 0
        self._alert_id = 0
        self._lock = threading.RLock()

        # Add default observers
        self._metric_collector = MetricCollector()
        self._trace_collector = TraceCollector()
        self._anomaly_detector = AnomalyDetector()

        self.add_observer(self._metric_collector)
        self.add_observer(self._trace_collector)
        self.add_observer(self._anomaly_detector)

    def _generate_obs_id(self) -> str:
        self._obs_id += 1
        return f"obs_{self._obs_id}"

    def _generate_alert_id(self) -> str:
        self._alert_id += 1
        return f"alert_{self._alert_id}"

    def add_observer(self, observer: Observer) -> None:
        """Add observer."""
        with self._lock:
            self._observers.append(observer)

    def observe(
        self,
        observation_type: ObservationType,
        source: str,
        data: Dict[str, Any],
        context: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> Observation:
        """
        Record observation.

        All observers are notified.
        """
        with self._lock:
            obs = Observation(
                id=self._generate_obs_id(),
                observation_type=observation_type,
                timestamp=time.time(),
                source=source,
                data=data,
                context=context or {},
                tags=tags or []
            )

            self._observations.append(obs)

            # Trim observations
            if len(self._observations) > self._max_observations:
                self._observations = self._observations[-self._max_observations:]

            # Notify observers
            for observer in self._observers:
                try:
                    observer.observe(obs)
                except Exception as e:
                    logger.warning(f"Observer failed: {e}")

            # Check for alert
            if obs.alert_level:
                self._create_alert(obs)

            return obs

    def _create_alert(self, obs: Observation) -> Alert:
        """Create alert from observation."""
        alert = Alert(
            id=self._generate_alert_id(),
            level=obs.alert_level,
            message=f"{obs.observation_type.name}: {obs.data}",
            observations=[obs.id]
        )
        self._alerts.append(alert)
        return alert

    # =========== CONVENIENCE METHODS ===========

    def observe_call(
        self,
        function_name: str,
        args: Tuple = (),
        kwargs: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> Observation:
        """Observe function call."""
        return self.observe(
            ObservationType.FUNCTION_CALL,
            function_name,
            {'function': function_name, 'args': str(args), 'kwargs': str(kwargs or {})},
            context
        )

    def observe_return(
        self,
        function_name: str,
        result: Any,
        duration_ms: float,
        context: Optional[Dict] = None
    ) -> Observation:
        """Observe function return."""
        return self.observe(
            ObservationType.FUNCTION_RETURN,
            function_name,
            {'function': function_name, 'result_type': type(result).__name__, 'duration_ms': duration_ms},
            context
        )

    def observe_exception(
        self,
        source: str,
        exception: Exception,
        context: Optional[Dict] = None
    ) -> Observation:
        """Observe exception."""
        obs = self.observe(
            ObservationType.EXCEPTION,
            source,
            {'exception': type(exception).__name__, 'message': str(exception), 'traceback': traceback.format_exc()},
            context
        )
        obs.alert_level = AlertLevel.ERROR
        self._create_alert(obs)
        return obs

    def observe_metric(
        self,
        name: str,
        value: float,
        tags: Optional[List[str]] = None
    ) -> Observation:
        """Observe metric."""
        return self.observe(
            ObservationType.METRIC,
            "metrics",
            {'name': name, 'value': value},
            tags=tags
        )

    def observe_thought(
        self,
        thought: str,
        reasoning: Optional[str] = None
    ) -> Observation:
        """Observe internal thought."""
        return self.observe(
            ObservationType.THOUGHT,
            "consciousness",
            {'thought': thought, 'reasoning': reasoning}
        )

    def observe_decision(
        self,
        decision: str,
        alternatives: List[str],
        confidence: float
    ) -> Observation:
        """Observe decision made."""
        return self.observe(
            ObservationType.DECISION,
            "decision_engine",
            {'decision': decision, 'alternatives': alternatives, 'confidence': confidence}
        )

    # =========== DECORATORS ===========

    def watch(self, func: Callable) -> Callable:
        """Decorator to observe function calls."""
        def wrapper(*args, **kwargs):
            start = time.time()
            context = {'trace_id': f"trace_{start}"}

            self.observe_call(func.__name__, args, kwargs, context)

            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                self.observe_return(func.__name__, result, duration, context)
                return result
            except Exception as e:
                self.observe_exception(func.__name__, e, context)
                raise

        return wrapper

    # =========== QUERIES ===========

    def get_observations(
        self,
        observation_type: Optional[ObservationType] = None,
        source: Optional[str] = None,
        since: Optional[float] = None
    ) -> List[Observation]:
        """Query observations."""
        with self._lock:
            result = self._observations

            if observation_type:
                result = [o for o in result if o.observation_type == observation_type]
            if source:
                result = [o for o in result if o.source == source]
            if since:
                result = [o for o in result if o.timestamp >= since]

            return result

    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        unacknowledged_only: bool = False
    ) -> List[Alert]:
        """Query alerts."""
        with self._lock:
            result = self._alerts

            if level:
                result = [a for a in result if a.level == level]
            if unacknowledged_only:
                result = [a for a in result if not a.acknowledged]

            return result

    def get_full_insight(self) -> Dict[str, Any]:
        """Get complete insight from all observers."""
        with self._lock:
            insights = {
                'total_observations': len(self._observations),
                'total_alerts': len(self._alerts),
                'unacknowledged_alerts': len([a for a in self._alerts if not a.acknowledged]),
                'observers': {}
            }

            for observer in self._observers:
                name = type(observer).__name__
                insights['observers'][name] = observer.get_insights()

            return insights


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_omniscient: Optional[OmniscientObserver] = None


def get_omniscient() -> OmniscientObserver:
    """Get global omniscient observer instance."""
    global _omniscient
    if _omniscient is None:
        _omniscient = OmniscientObserver()
    return _omniscient


# ============================================================================
# CONVENIENCE
# ============================================================================

def observe(
    observation_type: ObservationType,
    source: str,
    data: Dict[str, Any]
) -> Observation:
    """Quick observation."""
    return get_omniscient().observe(observation_type, source, data)


def metric(name: str, value: float) -> Observation:
    """Record metric."""
    return get_omniscient().observe_metric(name, value)


def watch(func: Callable) -> Callable:
    """Decorator to watch function."""
    return get_omniscient().watch(func)


def thought(content: str) -> Observation:
    """Record thought."""
    return get_omniscient().observe_thought(content)


def decision(choice: str, alternatives: List[str], confidence: float = 1.0) -> Observation:
    """Record decision."""
    return get_omniscient().observe_decision(choice, alternatives, confidence)
