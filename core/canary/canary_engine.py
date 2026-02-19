"""
BAEL Canary Release Engine Implementation
==========================================

Gradual rollout with monitoring and automatic rollback.

"Ba'el tests in production with surgical precision." — Ba'el
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid
import statistics

logger = logging.getLogger("BAEL.Canary")


# ============================================================================
# ENUMS
# ============================================================================

class CanaryState(Enum):
    """Canary release states."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    MONITORING = "monitoring"
    PROMOTING = "promoting"
    PROMOTED = "promoted"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class MetricType(Enum):
    """Types of metrics to monitor."""
    ERROR_RATE = "error_rate"
    LATENCY_P50 = "latency_p50"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    SUCCESS_RATE = "success_rate"
    THROUGHPUT = "throughput"
    SATURATION = "saturation"


class ThresholdOperator(Enum):
    """Threshold comparison operators."""
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    EQUALS = "equals"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CanaryMetric:
    """A metric for canary analysis."""
    name: str
    metric_type: MetricType
    value: float
    threshold: float
    operator: ThresholdOperator = ThresholdOperator.LESS_THAN
    timestamp: datetime = field(default_factory=datetime.now)

    def is_healthy(self) -> bool:
        """Check if metric is within threshold."""
        if self.operator == ThresholdOperator.LESS_THAN:
            return self.value < self.threshold
        elif self.operator == ThresholdOperator.GREATER_THAN:
            return self.value > self.threshold
        else:
            return self.value == self.threshold


@dataclass
class CanaryStep:
    """A canary rollout step."""
    traffic_percentage: float
    duration_seconds: float

    # State
    started_at: Optional[datetime] = None
    completed: bool = False

    # Metrics collected during this step
    metrics: List[CanaryMetric] = field(default_factory=list)


@dataclass
class CanaryRelease:
    """A canary release."""
    id: str
    version: str
    baseline_version: str

    # State
    state: CanaryState = CanaryState.PENDING
    current_step: int = 0

    # Steps
    steps: List[CanaryStep] = field(default_factory=list)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Analysis
    success_rate: float = 0.0
    baseline_success_rate: float = 0.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def current_traffic(self) -> float:
        """Get current traffic percentage."""
        if self.current_step < len(self.steps):
            return self.steps[self.current_step].traffic_percentage
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'version': self.version,
            'baseline_version': self.baseline_version,
            'state': self.state.value,
            'current_step': self.current_step,
            'current_traffic': self.current_traffic,
            'success_rate': self.success_rate
        }


@dataclass
class CanaryConfig:
    """Canary configuration."""
    # Default steps
    default_steps: List[tuple] = field(default_factory=lambda: [
        (5, 60),    # 5% for 60s
        (10, 120),  # 10% for 120s
        (25, 180),  # 25% for 180s
        (50, 300),  # 50% for 300s
        (100, 0),   # 100% (promoted)
    ])

    # Thresholds
    max_error_rate: float = 0.01  # 1%
    max_latency_p99: float = 500  # 500ms
    min_success_rate: float = 0.99  # 99%

    # Analysis
    analysis_interval: float = 10.0
    min_samples: int = 10

    # Rollback
    auto_rollback: bool = True
    rollback_on_metric_violation: bool = True


# ============================================================================
# CANARY MANAGER
# ============================================================================

class CanaryManager:
    """
    Canary release manager.

    Features:
    - Gradual traffic shifting
    - Metric-based analysis
    - Automatic rollback
    - Multiple rollout strategies

    "Ba'el advances with measured precision." — Ba'el
    """

    def __init__(self, config: Optional[CanaryConfig] = None):
        """Initialize canary manager."""
        self.config = config or CanaryConfig()

        # Releases
        self._releases: Dict[str, CanaryRelease] = {}
        self._active_release: Optional[str] = None

        # Metrics collection
        self._metric_collectors: Dict[MetricType, Callable] = {}

        # Handlers
        self._deploy_handler: Optional[Callable] = None
        self._traffic_handler: Optional[Callable] = None

        # Thread safety
        self._lock = threading.RLock()

        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None

        # Stats
        self._stats = {
            'releases': 0,
            'promoted': 0,
            'rolled_back': 0
        }

        logger.info("Canary Manager initialized")

    # ========================================================================
    # RELEASE MANAGEMENT
    # ========================================================================

    async def start_canary(
        self,
        version: str,
        baseline_version: str,
        release_id: Optional[str] = None,
        steps: Optional[List[tuple]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CanaryRelease:
        """
        Start a canary release.

        Args:
            version: New version to release
            baseline_version: Current version for comparison
            release_id: Optional release ID
            steps: Custom steps [(traffic%, duration_seconds), ...]
            metadata: Additional metadata

        Returns:
            CanaryRelease
        """
        # Create steps
        step_config = steps or self.config.default_steps
        canary_steps = [
            CanaryStep(traffic_percentage=t, duration_seconds=d)
            for t, d in step_config
        ]

        release = CanaryRelease(
            id=release_id or str(uuid.uuid4()),
            version=version,
            baseline_version=baseline_version,
            steps=canary_steps,
            metadata=metadata or {}
        )

        with self._lock:
            if self._active_release:
                raise RuntimeError("Another canary release is active")

            self._releases[release.id] = release
            self._active_release = release.id

        # Start deployment
        release.state = CanaryState.DEPLOYING
        release.started_at = datetime.now()

        try:
            # Deploy canary version
            if self._deploy_handler:
                await self._call_handler(self._deploy_handler, release)

            # Start monitoring
            release.state = CanaryState.MONITORING
            await self._run_canary(release)

        except Exception as e:
            release.state = CanaryState.FAILED
            logger.error(f"Canary failed: {e}")

            if self.config.auto_rollback:
                await self.rollback(release.id)

        finally:
            self._stats['releases'] += 1

        return release

    async def _run_canary(self, release: CanaryRelease) -> None:
        """Run through canary steps."""
        for i, step in enumerate(release.steps):
            release.current_step = i
            step.started_at = datetime.now()

            # Set traffic
            await self._set_traffic(release, step.traffic_percentage)

            # Monitor for duration
            if step.duration_seconds > 0:
                await self._monitor_step(release, step)

                # Check if healthy
                if not self._is_step_healthy(step):
                    if self.config.rollback_on_metric_violation:
                        await self.rollback(release.id)
                        return

            step.completed = True

        # All steps completed - promote
        await self.promote(release.id)

    async def _set_traffic(
        self,
        release: CanaryRelease,
        percentage: float
    ) -> None:
        """Set traffic percentage to canary."""
        logger.info(f"Setting canary traffic to {percentage}%")

        if self._traffic_handler:
            await self._call_handler(
                self._traffic_handler, release.version, percentage
            )

    async def _monitor_step(
        self,
        release: CanaryRelease,
        step: CanaryStep
    ) -> None:
        """Monitor a canary step."""
        end_time = time.time() + step.duration_seconds

        while time.time() < end_time:
            # Collect metrics
            metrics = await self._collect_metrics()
            step.metrics.extend(metrics)

            # Update release success rate
            release.success_rate = self._calculate_success_rate(step.metrics)

            # Check for violations
            for metric in metrics:
                if not metric.is_healthy():
                    logger.warning(
                        f"Metric violation: {metric.name} = {metric.value}"
                    )

            await asyncio.sleep(self.config.analysis_interval)

    async def _collect_metrics(self) -> List[CanaryMetric]:
        """Collect metrics from registered collectors."""
        metrics = []

        for metric_type, collector in self._metric_collectors.items():
            try:
                value = await self._call_handler(collector)

                # Get threshold for this metric
                threshold = self._get_threshold(metric_type)
                operator = self._get_operator(metric_type)

                metrics.append(CanaryMetric(
                    name=metric_type.value,
                    metric_type=metric_type,
                    value=value,
                    threshold=threshold,
                    operator=operator
                ))

            except Exception as e:
                logger.error(f"Metric collection error: {e}")

        return metrics

    def _get_threshold(self, metric_type: MetricType) -> float:
        """Get threshold for metric type."""
        thresholds = {
            MetricType.ERROR_RATE: self.config.max_error_rate,
            MetricType.LATENCY_P99: self.config.max_latency_p99,
            MetricType.SUCCESS_RATE: self.config.min_success_rate
        }
        return thresholds.get(metric_type, 0.0)

    def _get_operator(self, metric_type: MetricType) -> ThresholdOperator:
        """Get operator for metric type."""
        if metric_type == MetricType.SUCCESS_RATE:
            return ThresholdOperator.GREATER_THAN
        return ThresholdOperator.LESS_THAN

    def _is_step_healthy(self, step: CanaryStep) -> bool:
        """Check if step is healthy based on metrics."""
        if len(step.metrics) < self.config.min_samples:
            return True  # Not enough data

        # Check recent metrics
        recent = step.metrics[-self.config.min_samples:]
        unhealthy = sum(1 for m in recent if not m.is_healthy())

        # Allow up to 20% unhealthy
        return unhealthy / len(recent) < 0.2

    def _calculate_success_rate(self, metrics: List[CanaryMetric]) -> float:
        """Calculate success rate from metrics."""
        success_metrics = [
            m for m in metrics
            if m.metric_type == MetricType.SUCCESS_RATE
        ]

        if not success_metrics:
            return 0.0

        return statistics.mean(m.value for m in success_metrics)

    # ========================================================================
    # PROMOTION / ROLLBACK
    # ========================================================================

    async def promote(self, release_id: str) -> bool:
        """
        Promote canary to full production.

        Args:
            release_id: Release to promote

        Returns:
            True if promoted
        """
        with self._lock:
            release = self._releases.get(release_id)
            if not release:
                return False

            if release.state not in (CanaryState.MONITORING,):
                return False

        release.state = CanaryState.PROMOTING

        # Set traffic to 100%
        await self._set_traffic(release, 100.0)

        release.state = CanaryState.PROMOTED
        release.completed_at = datetime.now()

        with self._lock:
            self._active_release = None

        self._stats['promoted'] += 1
        logger.info(f"Canary promoted: {release_id}")

        return True

    async def rollback(self, release_id: str) -> bool:
        """
        Rollback canary release.

        Args:
            release_id: Release to rollback

        Returns:
            True if rolled back
        """
        with self._lock:
            release = self._releases.get(release_id)
            if not release:
                return False

        release.state = CanaryState.ROLLING_BACK

        # Set traffic to 0%
        await self._set_traffic(release, 0.0)

        release.state = CanaryState.ROLLED_BACK
        release.completed_at = datetime.now()

        with self._lock:
            self._active_release = None

        self._stats['rolled_back'] += 1
        logger.warning(f"Canary rolled back: {release_id}")

        return True

    # ========================================================================
    # HANDLERS
    # ========================================================================

    def set_deploy_handler(self, handler: Callable) -> None:
        """Set deployment handler."""
        self._deploy_handler = handler

    def set_traffic_handler(self, handler: Callable) -> None:
        """Set traffic routing handler."""
        self._traffic_handler = handler

    def register_metric_collector(
        self,
        metric_type: MetricType,
        collector: Callable
    ) -> None:
        """Register a metric collector."""
        self._metric_collectors[metric_type] = collector

    async def _call_handler(self, handler: Callable, *args) -> Any:
        """Call handler function."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args)
        else:
            return await asyncio.to_thread(handler, *args)

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_release(self, release_id: str) -> Optional[CanaryRelease]:
        """Get release by ID."""
        return self._releases.get(release_id)

    def get_active_release(self) -> Optional[CanaryRelease]:
        """Get active release."""
        if self._active_release:
            return self._releases.get(self._active_release)
        return None

    def list_releases(
        self,
        state: Optional[CanaryState] = None
    ) -> List[CanaryRelease]:
        """List releases."""
        with self._lock:
            releases = list(self._releases.values())
            if state:
                releases = [r for r in releases if r.state == state]
            return releases

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        active = self.get_active_release()

        return {
            'active_release': active.id if active else None,
            'active_traffic': active.current_traffic if active else 0,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

canary_manager = CanaryManager()


async def start_canary(
    version: str,
    baseline_version: str,
    **kwargs
) -> CanaryRelease:
    """Start a canary release."""
    return await canary_manager.start_canary(version, baseline_version, **kwargs)


async def promote_canary(release_id: str) -> bool:
    """Promote canary."""
    return await canary_manager.promote(release_id)


async def rollback_canary(release_id: str) -> bool:
    """Rollback canary."""
    return await canary_manager.rollback(release_id)
