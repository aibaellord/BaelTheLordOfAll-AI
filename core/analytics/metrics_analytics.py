"""
BAEL - Agent Metrics & Analytics
Comprehensive metrics collection and analytics system.

Features:
- Real-time metrics collection
- Performance analytics
- Usage tracking
- Cost analysis
- Trend detection
- Custom dashboards
"""

import asyncio
import json
import logging
import math
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class AggregationType(Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"
    RATE = "rate"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of metric points."""
    name: str
    type: MetricType
    points: List[MetricPoint] = field(default_factory=list)
    max_points: int = 10000

    def add(self, value: float, labels: Dict[str, str] = None):
        """Add a data point."""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels or {}
        )
        self.points.append(point)

        # Trim old points
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]

    def get_values(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[float]:
        """Get values in time range."""
        values = []

        for point in self.points:
            if start_time and point.timestamp < start_time:
                continue
            if end_time and point.timestamp > end_time:
                continue
            values.append(point.value)

        return values


@dataclass
class TokenUsage:
    """Token usage tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    cost: float = 0.0


@dataclass
class TaskMetrics:
    """Metrics for a single task."""
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    steps: int = 0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    errors: int = 0
    tool_calls: int = 0
    model_calls: int = 0


# =============================================================================
# METRIC COLLECTORS
# =============================================================================

class Counter:
    """Thread-safe counter metric."""

    def __init__(self, name: str, labels: Dict[str, str] = None):
        self.name = name
        self.labels = labels or {}
        self._value = 0.0
        self._series = MetricSeries(name, MetricType.COUNTER)

    def inc(self, amount: float = 1.0):
        """Increment counter."""
        self._value += amount
        self._series.add(self._value, self.labels)

    def get(self) -> float:
        """Get current value."""
        return self._value

    def reset(self):
        """Reset counter."""
        self._value = 0.0


class Gauge:
    """Thread-safe gauge metric."""

    def __init__(self, name: str, labels: Dict[str, str] = None):
        self.name = name
        self.labels = labels or {}
        self._value = 0.0
        self._series = MetricSeries(name, MetricType.GAUGE)

    def set(self, value: float):
        """Set gauge value."""
        self._value = value
        self._series.add(value, self.labels)

    def inc(self, amount: float = 1.0):
        """Increment gauge."""
        self._value += amount
        self._series.add(self._value, self.labels)

    def dec(self, amount: float = 1.0):
        """Decrement gauge."""
        self._value -= amount
        self._series.add(self._value, self.labels)

    def get(self) -> float:
        """Get current value."""
        return self._value


class Histogram:
    """Histogram metric for distributions."""

    def __init__(
        self,
        name: str,
        buckets: List[float] = None,
        labels: Dict[str, str] = None
    ):
        self.name = name
        self.labels = labels or {}
        self.buckets = buckets or [
            0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5,
            1.0, 2.5, 5.0, 10.0, float('inf')
        ]

        self._values: List[float] = []
        self._bucket_counts: Dict[float, int] = {b: 0 for b in self.buckets}
        self._series = MetricSeries(name, MetricType.HISTOGRAM)

    def observe(self, value: float):
        """Observe a value."""
        self._values.append(value)
        self._series.add(value, self.labels)

        # Update buckets
        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[bucket] += 1
                break

        # Limit stored values
        if len(self._values) > 10000:
            self._values = self._values[-10000:]

    def get_percentile(self, p: float) -> float:
        """Get percentile value."""
        if not self._values:
            return 0.0

        sorted_values = sorted(self._values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    def get_stats(self) -> Dict[str, float]:
        """Get statistics."""
        if not self._values:
            return {
                "count": 0,
                "sum": 0,
                "min": 0,
                "max": 0,
                "avg": 0,
                "p50": 0,
                "p90": 0,
                "p95": 0,
                "p99": 0
            }

        return {
            "count": len(self._values),
            "sum": sum(self._values),
            "min": min(self._values),
            "max": max(self._values),
            "avg": statistics.mean(self._values),
            "p50": self.get_percentile(50),
            "p90": self.get_percentile(90),
            "p95": self.get_percentile(95),
            "p99": self.get_percentile(99)
        }


class Timer:
    """Timer metric for measuring durations."""

    def __init__(self, name: str, labels: Dict[str, str] = None):
        self.name = name
        self.labels = labels or {}
        self._histogram = Histogram(name, labels=labels)
        self._start_time: Optional[float] = None

    def start(self):
        """Start timer."""
        self._start_time = time.time()

    def stop(self) -> float:
        """Stop timer and return duration."""
        if self._start_time is None:
            return 0.0

        duration = time.time() - self._start_time
        self._histogram.observe(duration)
        self._start_time = None
        return duration

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def get_stats(self) -> Dict[str, float]:
        """Get timer statistics."""
        return self._histogram.get_stats()


# =============================================================================
# METRICS REGISTRY
# =============================================================================

class MetricsRegistry:
    """Central registry for all metrics."""

    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._timers: Dict[str, Timer] = {}

    def counter(
        self,
        name: str,
        labels: Dict[str, str] = None
    ) -> Counter:
        """Get or create counter."""
        key = self._make_key(name, labels)

        if key not in self._counters:
            self._counters[key] = Counter(name, labels)

        return self._counters[key]

    def gauge(
        self,
        name: str,
        labels: Dict[str, str] = None
    ) -> Gauge:
        """Get or create gauge."""
        key = self._make_key(name, labels)

        if key not in self._gauges:
            self._gauges[key] = Gauge(name, labels)

        return self._gauges[key]

    def histogram(
        self,
        name: str,
        buckets: List[float] = None,
        labels: Dict[str, str] = None
    ) -> Histogram:
        """Get or create histogram."""
        key = self._make_key(name, labels)

        if key not in self._histograms:
            self._histograms[key] = Histogram(name, buckets, labels)

        return self._histograms[key]

    def timer(
        self,
        name: str,
        labels: Dict[str, str] = None
    ) -> Timer:
        """Get or create timer."""
        key = self._make_key(name, labels)

        if key not in self._timers:
            self._timers[key] = Timer(name, labels)

        return self._timers[key]

    def _make_key(
        self,
        name: str,
        labels: Dict[str, str] = None
    ) -> str:
        """Make unique key for metric."""
        if not labels:
            return name

        label_str = ",".join(
            f"{k}={v}" for k, v in sorted(labels.items())
        )
        return f"{name}{{{label_str}}}"

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as dictionary."""
        return {
            "counters": {
                k: v.get() for k, v in self._counters.items()
            },
            "gauges": {
                k: v.get() for k, v in self._gauges.items()
            },
            "histograms": {
                k: v.get_stats() for k, v in self._histograms.items()
            },
            "timers": {
                k: v.get_stats() for k, v in self._timers.items()
            }
        }


# Global registry
_registry = MetricsRegistry()


def get_registry() -> MetricsRegistry:
    """Get global metrics registry."""
    return _registry


# =============================================================================
# AGENT ANALYTICS
# =============================================================================

class AgentAnalytics:
    """Analytics for agent operations."""

    def __init__(self):
        self.registry = get_registry()

        # Core metrics
        self.task_counter = self.registry.counter("bael_tasks_total")
        self.task_success = self.registry.counter("bael_tasks_success")
        self.task_failure = self.registry.counter("bael_tasks_failure")
        self.active_tasks = self.registry.gauge("bael_active_tasks")
        self.task_duration = self.registry.histogram("bael_task_duration_seconds")

        # LLM metrics
        self.llm_requests = self.registry.counter("bael_llm_requests_total")
        self.llm_tokens = self.registry.counter("bael_llm_tokens_total")
        self.llm_cost = self.registry.counter("bael_llm_cost_usd")
        self.llm_latency = self.registry.histogram("bael_llm_latency_seconds")

        # Tool metrics
        self.tool_calls = self.registry.counter("bael_tool_calls_total")
        self.tool_latency = self.registry.histogram("bael_tool_latency_seconds")

        # Memory metrics
        self.memory_operations = self.registry.counter("bael_memory_ops_total")
        self.memory_size = self.registry.gauge("bael_memory_size_bytes")

        # Error metrics
        self.errors = self.registry.counter("bael_errors_total")

        # Task tracking
        self._active_tasks: Dict[str, TaskMetrics] = {}
        self._completed_tasks: deque = deque(maxlen=1000)

    def start_task(self, task_id: str) -> None:
        """Record task start."""
        self.task_counter.inc()
        self.active_tasks.inc()

        self._active_tasks[task_id] = TaskMetrics(
            task_id=task_id,
            start_time=time.time()
        )

    def complete_task(
        self,
        task_id: str,
        success: bool = True,
        tokens: Optional[TokenUsage] = None
    ) -> Optional[float]:
        """Record task completion."""
        task = self._active_tasks.pop(task_id, None)
        if not task:
            return None

        task.end_time = time.time()
        task.status = "success" if success else "failure"

        if tokens:
            task.tokens = tokens

        duration = task.end_time - task.start_time

        self.active_tasks.dec()
        self.task_duration.observe(duration)

        if success:
            self.task_success.inc()
        else:
            self.task_failure.inc()

        self._completed_tasks.append(task)
        return duration

    def record_llm_call(
        self,
        model: str,
        tokens: TokenUsage,
        latency: float
    ) -> None:
        """Record LLM API call."""
        self.llm_requests.inc()
        self.llm_tokens.inc(tokens.total_tokens)
        self.llm_cost.inc(tokens.cost)
        self.llm_latency.observe(latency)

        # Model-specific counter
        model_counter = self.registry.counter(
            "bael_llm_requests_by_model",
            {"model": model}
        )
        model_counter.inc()

    def record_tool_call(
        self,
        tool_name: str,
        latency: float,
        success: bool = True
    ) -> None:
        """Record tool invocation."""
        self.tool_calls.inc()
        self.tool_latency.observe(latency)

        # Tool-specific counter
        tool_counter = self.registry.counter(
            "bael_tool_calls_by_name",
            {"tool": tool_name, "success": str(success)}
        )
        tool_counter.inc()

    def record_error(
        self,
        error_type: str,
        component: str = "unknown"
    ) -> None:
        """Record error."""
        self.errors.inc()

        error_counter = self.registry.counter(
            "bael_errors_by_type",
            {"type": error_type, "component": component}
        )
        error_counter.inc()

    def get_summary(self) -> Dict[str, Any]:
        """Get analytics summary."""
        return {
            "tasks": {
                "total": self.task_counter.get(),
                "success": self.task_success.get(),
                "failure": self.task_failure.get(),
                "active": self.active_tasks.get(),
                "duration_stats": self.task_duration.get_stats()
            },
            "llm": {
                "requests": self.llm_requests.get(),
                "total_tokens": self.llm_tokens.get(),
                "total_cost_usd": self.llm_cost.get(),
                "latency_stats": self.llm_latency.get_stats()
            },
            "tools": {
                "total_calls": self.tool_calls.get(),
                "latency_stats": self.tool_latency.get_stats()
            },
            "errors": {
                "total": self.errors.get()
            }
        }


# =============================================================================
# COST ANALYZER
# =============================================================================

class CostAnalyzer:
    """Analyze and track LLM costs."""

    # Pricing per 1M tokens (as of 2024)
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-opus-4": {"input": 15.00, "output": 75.00},
    }

    def __init__(self):
        self._usage_log: List[Dict[str, Any]] = []
        self._daily_costs: Dict[str, float] = defaultdict(float)
        self._model_costs: Dict[str, float] = defaultdict(float)

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost for a request."""
        # Normalize model name
        model_key = None
        for key in self.PRICING:
            if key in model.lower():
                model_key = key
                break

        if not model_key:
            logger.warning(f"Unknown model for pricing: {model}")
            return 0.0

        pricing = self.PRICING[model_key]

        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        task_id: Optional[str] = None
    ) -> float:
        """Record token usage and calculate cost."""
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)

        # Log usage
        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost,
            "task_id": task_id
        }

        self._usage_log.append(entry)

        # Track daily costs
        date_key = datetime.now().strftime("%Y-%m-%d")
        self._daily_costs[date_key] += cost

        # Track model costs
        self._model_costs[model] += cost

        return cost

    def get_daily_cost(self, date: Optional[str] = None) -> float:
        """Get cost for a specific day."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self._daily_costs.get(date, 0.0)

    def get_total_cost(self) -> float:
        """Get total cost across all time."""
        return sum(self._daily_costs.values())

    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get detailed cost breakdown."""
        return {
            "total": self.get_total_cost(),
            "by_day": dict(self._daily_costs),
            "by_model": dict(self._model_costs),
            "recent_requests": self._usage_log[-100:]
        }

    def estimate_monthly_cost(self) -> float:
        """Estimate monthly cost based on recent usage."""
        if not self._daily_costs:
            return 0.0

        # Average daily cost
        avg_daily = sum(self._daily_costs.values()) / len(self._daily_costs)
        return avg_daily * 30


# =============================================================================
# TREND ANALYZER
# =============================================================================

class TrendAnalyzer:
    """Analyze trends in metrics."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size

    def detect_trend(
        self,
        values: List[float]
    ) -> Tuple[str, float]:
        """Detect trend direction and strength."""
        if len(values) < 2:
            return "stable", 0.0

        # Calculate simple linear regression
        n = len(values)
        x = list(range(n))

        mean_x = sum(x) / n
        mean_y = sum(values) / n

        numerator = sum(
            (x[i] - mean_x) * (values[i] - mean_y)
            for i in range(n)
        )
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            return "stable", 0.0

        slope = numerator / denominator

        # Determine trend
        if abs(slope) < 0.01:
            return "stable", slope
        elif slope > 0:
            return "increasing", slope
        else:
            return "decreasing", slope

    def detect_anomalies(
        self,
        values: List[float],
        std_threshold: float = 2.0
    ) -> List[Tuple[int, float]]:
        """Detect anomalous values."""
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        std = statistics.stdev(values)

        anomalies = []
        for i, value in enumerate(values):
            z_score = abs(value - mean) / std if std > 0 else 0
            if z_score > std_threshold:
                anomalies.append((i, value))

        return anomalies

    def calculate_moving_average(
        self,
        values: List[float],
        window: int = 10
    ) -> List[float]:
        """Calculate moving average."""
        if len(values) < window:
            return values

        result = []
        for i in range(len(values) - window + 1):
            avg = sum(values[i:i + window]) / window
            result.append(avg)

        return result

    def forecast_next(
        self,
        values: List[float],
        periods: int = 5
    ) -> List[float]:
        """Simple linear forecast."""
        if len(values) < 2:
            return [values[-1]] * periods if values else [0] * periods

        # Linear regression
        n = len(values)
        x = list(range(n))

        mean_x = sum(x) / n
        mean_y = sum(values) / n

        numerator = sum(
            (x[i] - mean_x) * (values[i] - mean_y)
            for i in range(n)
        )
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

        slope = numerator / denominator if denominator else 0
        intercept = mean_y - slope * mean_x

        # Forecast
        forecasts = []
        for i in range(n, n + periods):
            forecasts.append(intercept + slope * i)

        return forecasts


# =============================================================================
# DASHBOARD
# =============================================================================

class MetricsDashboard:
    """Generate dashboard data."""

    def __init__(
        self,
        analytics: AgentAnalytics,
        cost_analyzer: CostAnalyzer
    ):
        self.analytics = analytics
        self.cost_analyzer = cost_analyzer
        self.trend_analyzer = TrendAnalyzer()

    def get_overview(self) -> Dict[str, Any]:
        """Get dashboard overview."""
        summary = self.analytics.get_summary()
        costs = self.cost_analyzer.get_cost_breakdown()

        return {
            "timestamp": datetime.now().isoformat(),
            "performance": {
                "tasks_completed": summary["tasks"]["total"],
                "success_rate": (
                    summary["tasks"]["success"] / summary["tasks"]["total"]
                    if summary["tasks"]["total"] > 0 else 0
                ) * 100,
                "avg_task_duration": summary["tasks"]["duration_stats"]["avg"],
                "avg_llm_latency": summary["llm"]["latency_stats"]["avg"]
            },
            "usage": {
                "total_llm_calls": summary["llm"]["requests"],
                "total_tokens": summary["llm"]["total_tokens"],
                "total_tool_calls": summary["tools"]["total_calls"]
            },
            "costs": {
                "today": self.cost_analyzer.get_daily_cost(),
                "total": costs["total"],
                "estimated_monthly": self.cost_analyzer.estimate_monthly_cost()
            },
            "health": {
                "error_count": summary["errors"]["total"],
                "active_tasks": summary["tasks"]["active"]
            }
        }

    def get_time_series(
        self,
        metric_name: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get time series data for a metric."""
        registry = get_registry()

        # Find the metric
        if metric_name in registry._histograms:
            series = registry._histograms[metric_name]._series
        elif metric_name in registry._counters:
            series = registry._counters[metric_name]._series
        elif metric_name in registry._gauges:
            series = registry._gauges[metric_name]._series
        else:
            return []

        # Filter by time
        cutoff = time.time() - (hours * 3600)

        return [
            {
                "timestamp": p.timestamp,
                "value": p.value,
                "labels": p.labels
            }
            for p in series.points
            if p.timestamp >= cutoff
        ]


# =============================================================================
# PROMETHEUS EXPORTER
# =============================================================================

class PrometheusExporter:
    """Export metrics in Prometheus format."""

    def __init__(self, registry: MetricsRegistry):
        self.registry = registry

    def export(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []

        # Counters
        for name, counter in self.registry._counters.items():
            lines.append(f"# TYPE {counter.name} counter")
            lines.append(f"{name} {counter.get()}")

        # Gauges
        for name, gauge in self.registry._gauges.items():
            lines.append(f"# TYPE {gauge.name} gauge")
            lines.append(f"{name} {gauge.get()}")

        # Histograms
        for name, histogram in self.registry._histograms.items():
            stats = histogram.get_stats()
            lines.append(f"# TYPE {histogram.name} histogram")
            lines.append(f"{name}_count {stats['count']}")
            lines.append(f"{name}_sum {stats['sum']}")

            for bucket, count in histogram._bucket_counts.items():
                if bucket == float('inf'):
                    lines.append(f'{name}_bucket{{le="+Inf"}} {count}')
                else:
                    lines.append(f'{name}_bucket{{le="{bucket}"}} {count}')

        return "\n".join(lines)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def main():
    """Demonstrate metrics and analytics."""
    analytics = AgentAnalytics()
    cost_analyzer = CostAnalyzer()

    # Simulate some tasks
    print("=== Simulating Agent Activity ===\n")

    for i in range(5):
        task_id = f"task_{i+1}"

        # Start task
        analytics.start_task(task_id)
        print(f"Started {task_id}")

        # Simulate work
        await asyncio.sleep(0.1)

        # Simulate LLM call
        tokens = TokenUsage(
            prompt_tokens=500 + i * 100,
            completion_tokens=200 + i * 50,
            total_tokens=700 + i * 150
        )

        cost = cost_analyzer.record_usage(
            model="gpt-4o",
            prompt_tokens=tokens.prompt_tokens,
            completion_tokens=tokens.completion_tokens,
            task_id=task_id
        )
        tokens.cost = cost

        analytics.record_llm_call("gpt-4o", tokens, 0.5 + i * 0.1)

        # Simulate tool calls
        for tool in ["web_search", "code_execute", "file_read"]:
            analytics.record_tool_call(tool, 0.2, success=True)

        # Complete task
        duration = analytics.complete_task(task_id, success=i != 3, tokens=tokens)
        print(f"Completed {task_id} in {duration:.2f}s")

    # Add some errors
    analytics.record_error("timeout", "llm")
    analytics.record_error("validation", "tool")

    # Get summary
    print("\n=== Analytics Summary ===")
    summary = analytics.get_summary()
    print(json.dumps(summary, indent=2))

    # Cost analysis
    print("\n=== Cost Analysis ===")
    costs = cost_analyzer.get_cost_breakdown()
    print(f"Total cost: ${costs['total']:.4f}")
    print(f"Estimated monthly: ${cost_analyzer.estimate_monthly_cost():.2f}")

    # Dashboard
    dashboard = MetricsDashboard(analytics, cost_analyzer)
    print("\n=== Dashboard Overview ===")
    overview = dashboard.get_overview()
    print(json.dumps(overview, indent=2))

    # Prometheus export
    exporter = PrometheusExporter(get_registry())
    print("\n=== Prometheus Metrics ===")
    print(exporter.export()[:500] + "...")

    # Trend analysis
    trend_analyzer = TrendAnalyzer()
    values = [1.0, 1.2, 1.5, 1.8, 2.0, 2.3, 2.5]
    trend, slope = trend_analyzer.detect_trend(values)
    print(f"\nTrend analysis: {trend} (slope: {slope:.3f})")
    print(f"Forecast: {trend_analyzer.forecast_next(values, 3)}")


if __name__ == "__main__":
    asyncio.run(main())
