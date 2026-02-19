"""
BAEL Auto-Scaler
================

Automatic resource scaling and load management.

"Infinite capacity through intelligent adaptation." — Ba'el
"""

import asyncio
import logging
import time
import psutil
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import threading

logger = logging.getLogger("BAEL.AutoScaler")


class ScalingDirection(Enum):
    """Direction of scaling."""
    UP = "up"
    DOWN = "down"
    NONE = "none"


class ScalingStrategy(Enum):
    """Scaling strategies."""
    REACTIVE = "reactive"       # React to current load
    PREDICTIVE = "predictive"   # Predict future load
    SCHEDULED = "scheduled"     # Time-based scaling
    ADAPTIVE = "adaptive"       # Learn and adapt
    BURST = "burst"             # Handle sudden spikes
    GRADUAL = "gradual"         # Slow, steady scaling


class ResourceType(Enum):
    """Types of resources to scale."""
    WORKERS = "workers"
    MEMORY = "memory"
    CONNECTIONS = "connections"
    THREADS = "threads"
    CACHE = "cache"
    QUEUE = "queue"


class LoadLevel(Enum):
    """Load levels."""
    IDLE = "idle"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    OVERLOAD = "overload"


@dataclass
class ResourceConfig:
    """Configuration for a scalable resource."""
    resource_type: ResourceType
    min_capacity: int
    max_capacity: int
    current_capacity: int
    scale_up_threshold: float = 0.75
    scale_down_threshold: float = 0.25
    scale_up_increment: int = 1
    scale_down_increment: int = 1
    cooldown_seconds: float = 30.0


@dataclass
class LoadMetrics:
    """Current load metrics."""
    cpu_percent: float
    memory_percent: float
    active_tasks: int
    queue_depth: int
    request_rate: float  # requests per second
    latency_p99: float  # milliseconds
    error_rate: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ScalingDecision:
    """A scaling decision."""
    resource: ResourceType
    direction: ScalingDirection
    current: int
    target: int
    reason: str
    confidence: float  # 0-1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ScalingEvent:
    """Record of a scaling event."""
    decision: ScalingDecision
    executed: bool
    success: bool
    duration_ms: float
    error: Optional[str] = None


class MetricsCollector:
    """Collects system and application metrics."""

    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self._metrics_history: deque = deque(maxlen=window_size)
        self._request_times: deque = deque(maxlen=1000)
        self._latencies: deque = deque(maxlen=1000)
        self._errors: deque = deque(maxlen=1000)
        self._active_tasks = 0
        self._queue_depth = 0
        self._lock = threading.Lock()

    def record_request(self, latency_ms: float, is_error: bool = False) -> None:
        """Record a request."""
        now = time.time()
        with self._lock:
            self._request_times.append(now)
            self._latencies.append(latency_ms)
            if is_error:
                self._errors.append(now)

    def set_active_tasks(self, count: int) -> None:
        """Set active task count."""
        self._active_tasks = count

    def set_queue_depth(self, depth: int) -> None:
        """Set queue depth."""
        self._queue_depth = depth

    def collect(self) -> LoadMetrics:
        """Collect current metrics."""
        now = time.time()
        one_minute_ago = now - 60

        with self._lock:
            # Request rate (requests per second in last minute)
            recent_requests = [t for t in self._request_times if t > one_minute_ago]
            request_rate = len(recent_requests) / 60.0

            # P99 latency
            if self._latencies:
                sorted_latencies = sorted(self._latencies)
                p99_idx = int(len(sorted_latencies) * 0.99)
                latency_p99 = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]
            else:
                latency_p99 = 0.0

            # Error rate
            recent_errors = [t for t in self._errors if t > one_minute_ago]
            error_rate = len(recent_errors) / len(recent_requests) if recent_requests else 0.0

        metrics = LoadMetrics(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=psutil.virtual_memory().percent,
            active_tasks=self._active_tasks,
            queue_depth=self._queue_depth,
            request_rate=request_rate,
            latency_p99=latency_p99,
            error_rate=error_rate,
        )

        self._metrics_history.append(metrics)
        return metrics

    def get_trend(self, metric_name: str, window: int = 10) -> float:
        """Get trend for a metric (-1 to 1, negative = decreasing)."""
        if len(self._metrics_history) < 2:
            return 0.0

        recent = list(self._metrics_history)[-window:]
        if len(recent) < 2:
            return 0.0

        values = [getattr(m, metric_name) for m in recent]

        # Simple linear regression slope
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * v for i, v in enumerate(values))
        sum_x2 = sum(i * i for i in range(n))

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator

        # Normalize to -1 to 1
        avg = sum_y / n
        if avg == 0:
            return 0.0

        normalized = slope / avg
        return max(-1.0, min(1.0, normalized))


class LoadPredictor:
    """Predicts future load based on historical patterns."""

    def __init__(self):
        self._hourly_patterns: Dict[int, List[float]] = {h: [] for h in range(24)}
        self._day_patterns: Dict[int, List[float]] = {d: [] for d in range(7)}

    def record_load(self, load: float) -> None:
        """Record current load for pattern learning."""
        now = datetime.now()
        self._hourly_patterns[now.hour].append(load)
        self._day_patterns[now.weekday()].append(load)

        # Keep only last 100 samples per slot
        if len(self._hourly_patterns[now.hour]) > 100:
            self._hourly_patterns[now.hour] = self._hourly_patterns[now.hour][-100:]
        if len(self._day_patterns[now.weekday()]) > 100:
            self._day_patterns[now.weekday()] = self._day_patterns[now.weekday()][-100:]

    def predict_load(self, hours_ahead: int = 1) -> float:
        """Predict load N hours in the future."""
        future = datetime.now() + timedelta(hours=hours_ahead)

        # Get historical patterns
        hourly_samples = self._hourly_patterns[future.hour]
        daily_samples = self._day_patterns[future.weekday()]

        if not hourly_samples and not daily_samples:
            return 0.5  # Default to medium

        hourly_avg = sum(hourly_samples) / len(hourly_samples) if hourly_samples else 0.5
        daily_avg = sum(daily_samples) / len(daily_samples) if daily_samples else 0.5

        # Weight hourly more heavily
        return hourly_avg * 0.7 + daily_avg * 0.3


class AutoScaler:
    """
    Automatic resource scaling system.

    Features:
    - Multi-strategy scaling (reactive, predictive, scheduled)
    - Resource pooling and limits
    - Cooldown periods
    - Load prediction
    - Burst handling
    - Gradual scaling
    """

    def __init__(
        self,
        strategy: ScalingStrategy = ScalingStrategy.ADAPTIVE,
    ):
        self.strategy = strategy
        self._resources: Dict[ResourceType, ResourceConfig] = {}
        self._metrics_collector = MetricsCollector()
        self._load_predictor = LoadPredictor()
        self._scaling_history: List[ScalingEvent] = []
        self._last_scale_time: Dict[ResourceType, float] = {}
        self._scale_callbacks: Dict[ResourceType, Callable] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    def configure_resource(
        self,
        resource_type: ResourceType,
        min_capacity: int,
        max_capacity: int,
        initial_capacity: int = None,
        scale_up_threshold: float = 0.75,
        scale_down_threshold: float = 0.25,
        scale_up_increment: int = 1,
        scale_down_increment: int = 1,
        cooldown_seconds: float = 30.0,
    ) -> None:
        """Configure a scalable resource."""
        self._resources[resource_type] = ResourceConfig(
            resource_type=resource_type,
            min_capacity=min_capacity,
            max_capacity=max_capacity,
            current_capacity=initial_capacity or min_capacity,
            scale_up_threshold=scale_up_threshold,
            scale_down_threshold=scale_down_threshold,
            scale_up_increment=scale_up_increment,
            scale_down_increment=scale_down_increment,
            cooldown_seconds=cooldown_seconds,
        )

    def register_scale_callback(
        self,
        resource_type: ResourceType,
        callback: Callable[[int, int], bool],
    ) -> None:
        """
        Register callback for scaling events.

        Callback receives (current_capacity, target_capacity) and returns success.
        """
        self._scale_callbacks[resource_type] = callback

    def record_request(self, latency_ms: float, is_error: bool = False) -> None:
        """Record a request for metrics."""
        self._metrics_collector.record_request(latency_ms, is_error)

    def set_active_tasks(self, count: int) -> None:
        """Set active task count."""
        self._metrics_collector.set_active_tasks(count)

    def set_queue_depth(self, depth: int) -> None:
        """Set queue depth."""
        self._metrics_collector.set_queue_depth(depth)

    async def start(self, check_interval: float = 10.0) -> None:
        """Start auto-scaling monitor."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(check_interval))
        logger.info("AutoScaler started")

    async def stop(self) -> None:
        """Stop auto-scaling monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("AutoScaler stopped")

    async def _monitor_loop(self, interval: float) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_and_scale()
            except Exception as e:
                logger.error(f"AutoScaler error: {e}")

            await asyncio.sleep(interval)

    async def _check_and_scale(self) -> None:
        """Check metrics and scale if needed."""
        metrics = self._metrics_collector.collect()

        # Record for prediction
        load = self._calculate_load_level(metrics)
        self._load_predictor.record_load(load)

        # Make scaling decisions for each resource
        for resource_type, config in self._resources.items():
            decision = self._make_scaling_decision(resource_type, config, metrics)

            if decision.direction != ScalingDirection.NONE:
                event = await self._execute_scaling(decision)
                self._scaling_history.append(event)

    def _calculate_load_level(self, metrics: LoadMetrics) -> float:
        """Calculate overall load level (0-1)."""
        # Weighted combination of metrics
        weights = {
            "cpu": 0.25,
            "memory": 0.15,
            "queue": 0.25,
            "latency": 0.20,
            "errors": 0.15,
        }

        cpu_score = min(metrics.cpu_percent / 100.0, 1.0)
        memory_score = min(metrics.memory_percent / 100.0, 1.0)

        # Normalize queue depth (assume max 1000)
        queue_score = min(metrics.queue_depth / 1000.0, 1.0)

        # Normalize latency (assume 1000ms is bad)
        latency_score = min(metrics.latency_p99 / 1000.0, 1.0)

        error_score = min(metrics.error_rate, 1.0)

        return (
            weights["cpu"] * cpu_score +
            weights["memory"] * memory_score +
            weights["queue"] * queue_score +
            weights["latency"] * latency_score +
            weights["errors"] * error_score
        )

    def _make_scaling_decision(
        self,
        resource_type: ResourceType,
        config: ResourceConfig,
        metrics: LoadMetrics,
    ) -> ScalingDecision:
        """Make scaling decision for a resource."""
        # Check cooldown
        last_scale = self._last_scale_time.get(resource_type, 0)
        if time.time() - last_scale < config.cooldown_seconds:
            return ScalingDecision(
                resource=resource_type,
                direction=ScalingDirection.NONE,
                current=config.current_capacity,
                target=config.current_capacity,
                reason="In cooldown period",
                confidence=1.0,
            )

        load = self._calculate_load_level(metrics)
        direction = ScalingDirection.NONE
        target = config.current_capacity
        reason = ""
        confidence = 0.0

        if self.strategy == ScalingStrategy.REACTIVE:
            direction, target, reason, confidence = self._reactive_decision(
                config, load, metrics
            )

        elif self.strategy == ScalingStrategy.PREDICTIVE:
            direction, target, reason, confidence = self._predictive_decision(
                config, load, metrics
            )

        elif self.strategy == ScalingStrategy.ADAPTIVE:
            # Combine reactive and predictive
            r_dir, r_target, r_reason, r_conf = self._reactive_decision(config, load, metrics)
            p_dir, p_target, p_reason, p_conf = self._predictive_decision(config, load, metrics)

            if r_dir == p_dir:
                direction = r_dir
                target = max(r_target, p_target) if direction == ScalingDirection.UP else min(r_target, p_target)
                reason = f"Adaptive: {r_reason}; {p_reason}"
                confidence = (r_conf + p_conf) / 2
            elif r_conf > p_conf:
                direction, target, reason, confidence = r_dir, r_target, r_reason, r_conf
            else:
                direction, target, reason, confidence = p_dir, p_target, p_reason, p_conf

        elif self.strategy == ScalingStrategy.BURST:
            direction, target, reason, confidence = self._burst_decision(config, load, metrics)

        elif self.strategy == ScalingStrategy.GRADUAL:
            direction, target, reason, confidence = self._gradual_decision(config, load, metrics)

        return ScalingDecision(
            resource=resource_type,
            direction=direction,
            current=config.current_capacity,
            target=target,
            reason=reason,
            confidence=confidence,
        )

    def _reactive_decision(
        self,
        config: ResourceConfig,
        load: float,
        metrics: LoadMetrics,
    ) -> tuple:
        """Make reactive scaling decision."""
        if load >= config.scale_up_threshold:
            if config.current_capacity < config.max_capacity:
                target = min(
                    config.current_capacity + config.scale_up_increment,
                    config.max_capacity
                )
                return (
                    ScalingDirection.UP,
                    target,
                    f"Load {load:.0%} >= threshold {config.scale_up_threshold:.0%}",
                    0.8,
                )

        elif load <= config.scale_down_threshold:
            if config.current_capacity > config.min_capacity:
                target = max(
                    config.current_capacity - config.scale_down_increment,
                    config.min_capacity
                )
                return (
                    ScalingDirection.DOWN,
                    target,
                    f"Load {load:.0%} <= threshold {config.scale_down_threshold:.0%}",
                    0.7,
                )

        return (ScalingDirection.NONE, config.current_capacity, "Load within normal range", 0.9)

    def _predictive_decision(
        self,
        config: ResourceConfig,
        load: float,
        metrics: LoadMetrics,
    ) -> tuple:
        """Make predictive scaling decision."""
        # Predict load 1 hour ahead
        predicted = self._load_predictor.predict_load(1)

        # Also check trend
        trend = self._metrics_collector.get_trend("cpu_percent")

        # Combine prediction with trend
        expected = predicted + trend * 0.2

        if expected >= config.scale_up_threshold:
            if config.current_capacity < config.max_capacity:
                # Scale up more aggressively when predicting
                increment = config.scale_up_increment * 2
                target = min(
                    config.current_capacity + increment,
                    config.max_capacity
                )
                return (
                    ScalingDirection.UP,
                    target,
                    f"Predicted load {expected:.0%} (trend: {trend:+.2f})",
                    0.6,
                )

        elif expected <= config.scale_down_threshold * 0.8:  # More conservative down
            if config.current_capacity > config.min_capacity:
                target = max(
                    config.current_capacity - config.scale_down_increment,
                    config.min_capacity
                )
                return (
                    ScalingDirection.DOWN,
                    target,
                    f"Predicted low load {expected:.0%}",
                    0.5,
                )

        return (ScalingDirection.NONE, config.current_capacity, "Predicted load stable", 0.7)

    def _burst_decision(
        self,
        config: ResourceConfig,
        load: float,
        metrics: LoadMetrics,
    ) -> tuple:
        """Make burst-mode scaling decision."""
        # Aggressive scale-up, conservative scale-down
        if load >= config.scale_up_threshold * 0.9:  # Lower threshold
            if config.current_capacity < config.max_capacity:
                # Scale up by larger increment
                increment = min(config.scale_up_increment * 3, config.max_capacity - config.current_capacity)
                target = config.current_capacity + increment
                return (
                    ScalingDirection.UP,
                    target,
                    f"Burst mode: Load {load:.0%}",
                    0.85,
                )

        elif load <= config.scale_down_threshold * 0.5:  # Much lower threshold
            if config.current_capacity > config.min_capacity:
                target = max(
                    config.current_capacity - config.scale_down_increment,
                    config.min_capacity
                )
                return (
                    ScalingDirection.DOWN,
                    target,
                    f"Burst mode: Low load {load:.0%}",
                    0.6,
                )

        return (ScalingDirection.NONE, config.current_capacity, "Burst mode: Stable", 0.8)

    def _gradual_decision(
        self,
        config: ResourceConfig,
        load: float,
        metrics: LoadMetrics,
    ) -> tuple:
        """Make gradual scaling decision."""
        # Only scale if load persists
        trend = self._metrics_collector.get_trend("cpu_percent", window=20)

        if load >= config.scale_up_threshold and trend > 0.1:
            if config.current_capacity < config.max_capacity:
                return (
                    ScalingDirection.UP,
                    config.current_capacity + 1,  # Always just 1
                    f"Gradual: Sustained high load (trend: {trend:+.2f})",
                    0.7,
                )

        elif load <= config.scale_down_threshold and trend < -0.1:
            if config.current_capacity > config.min_capacity:
                return (
                    ScalingDirection.DOWN,
                    config.current_capacity - 1,  # Always just 1
                    f"Gradual: Sustained low load (trend: {trend:+.2f})",
                    0.6,
                )

        return (ScalingDirection.NONE, config.current_capacity, "Gradual: Waiting for trend", 0.8)

    async def _execute_scaling(self, decision: ScalingDecision) -> ScalingEvent:
        """Execute a scaling decision."""
        start = time.time()
        success = False
        error = None

        try:
            config = self._resources[decision.resource]
            callback = self._scale_callbacks.get(decision.resource)

            if callback:
                if asyncio.iscoroutinefunction(callback):
                    success = await callback(decision.current, decision.target)
                else:
                    success = callback(decision.current, decision.target)
            else:
                # No callback - just update internal state
                success = True

            if success:
                config.current_capacity = decision.target
                self._last_scale_time[decision.resource] = time.time()
                logger.info(
                    f"Scaled {decision.resource.value}: {decision.current} -> {decision.target} "
                    f"({decision.reason})"
                )

        except Exception as e:
            error = str(e)
            logger.error(f"Scaling failed: {e}")

        return ScalingEvent(
            decision=decision,
            executed=True,
            success=success,
            duration_ms=(time.time() - start) * 1000,
            error=error,
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "strategy": self.strategy.value,
            "running": self._running,
            "resources": {
                rt.value: {
                    "current": cfg.current_capacity,
                    "min": cfg.min_capacity,
                    "max": cfg.max_capacity,
                }
                for rt, cfg in self._resources.items()
            },
            "recent_events": [
                {
                    "resource": e.decision.resource.value,
                    "direction": e.decision.direction.value,
                    "from": e.decision.current,
                    "to": e.decision.target,
                    "success": e.success,
                }
                for e in self._scaling_history[-10:]
            ],
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_auto_scaler = AutoScaler()


def get_auto_scaler() -> AutoScaler:
    """Get the global auto-scaler."""
    return _auto_scaler


async def configure_default_scaling() -> None:
    """Configure default scaling for BAEL."""
    scaler = get_auto_scaler()

    scaler.configure_resource(
        ResourceType.WORKERS,
        min_capacity=2,
        max_capacity=32,
        initial_capacity=4,
        scale_up_threshold=0.7,
        scale_down_threshold=0.3,
    )

    scaler.configure_resource(
        ResourceType.CONNECTIONS,
        min_capacity=5,
        max_capacity=100,
        initial_capacity=10,
        scale_up_threshold=0.8,
        scale_down_threshold=0.2,
    )

    scaler.configure_resource(
        ResourceType.CACHE,
        min_capacity=100,
        max_capacity=10000,
        initial_capacity=500,
        scale_up_threshold=0.9,
        scale_down_threshold=0.3,
    )

    await scaler.start()
