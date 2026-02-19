"""
BAEL Progress Monitor
======================

Real-time progress monitoring and alerting.
Provides visibility into mission execution.

Features:
- Progress tracking
- Performance metrics
- Alert generation
- Resource usage monitoring
- Time estimation
- Bottleneck detection
"""

import asyncio
import logging
import time
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


class AlertType(Enum):
    """Types of alerts."""
    SLOW_PROGRESS = "slow_progress"
    STALLED = "stalled"
    ERROR_RATE = "error_rate"
    RESOURCE_HIGH = "resource_high"
    DEADLINE_RISK = "deadline_risk"
    TASK_FAILED = "task_failed"
    MISSION_COMPLETE = "mission_complete"


@dataclass
class Alert:
    """An alert notification."""
    id: str
    type: AlertType
    severity: AlertSeverity
    message: str

    # Context
    mission_id: Optional[str] = None
    task_id: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Details
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.resolved_at is None


@dataclass
class ProgressUpdate:
    """Progress update event."""
    mission_id: str
    task_id: Optional[str] = None

    # Progress
    progress: float = 0.0
    delta: float = 0.0

    # Message
    message: str = ""

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)

    # Metrics
    items_completed: int = 0
    items_total: int = 0


@dataclass
class ProgressMetrics:
    """Progress metrics for a mission/task."""
    # Progress
    current_progress: float = 0.0
    progress_rate: float = 0.0  # Progress per minute

    # Timing
    elapsed_time: timedelta = field(default_factory=timedelta)
    estimated_remaining: timedelta = field(default_factory=timedelta)
    estimated_completion: Optional[datetime] = None

    # Performance
    tasks_completed: int = 0
    tasks_failed: int = 0
    error_rate: float = 0.0

    # Resource usage
    api_calls: int = 0
    tokens_used: int = 0
    cost_incurred: float = 0.0

    # Velocity
    avg_task_duration: timedelta = field(default_factory=timedelta)
    throughput: float = 0.0  # Tasks per minute


@dataclass
class ProgressCheckpoint:
    """Progress checkpoint for recovery."""
    mission_id: str
    checkpoint_id: str
    progress: float
    timestamp: datetime

    # State
    completed_tasks: List[str] = field(default_factory=list)
    current_task: Optional[str] = None

    # Data
    outputs: Dict[str, Any] = field(default_factory=dict)


class ProgressMonitor:
    """
    Real-time progress monitoring for BAEL.
    """

    def __init__(self):
        # Progress tracking
        self.metrics: Dict[str, ProgressMetrics] = {}  # mission_id -> metrics
        self.updates: Dict[str, List[ProgressUpdate]] = {}  # mission_id -> updates

        # Alerts
        self.alerts: Dict[str, Alert] = {}
        self.alert_counter = 0

        # Checkpoints
        self.checkpoints: Dict[str, List[ProgressCheckpoint]] = {}

        # Thresholds
        self.thresholds = {
            "stall_minutes": 5.0,
            "slow_progress_rate": 0.01,  # 1% per minute minimum
            "error_rate_warning": 0.1,
            "error_rate_critical": 0.3,
            "deadline_warning_hours": 1.0,
        }

        # Callbacks
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        self._progress_callbacks: List[Callable[[ProgressUpdate], None]] = []

        # Monitoring state
        self._monitoring: Set[str] = set()
        self._monitor_tasks: Dict[str, asyncio.Task] = {}

        # Stats
        self.stats = {
            "updates_processed": 0,
            "alerts_generated": 0,
            "checkpoints_created": 0,
        }

    def start_monitoring(self, mission_id: str) -> None:
        """Start monitoring a mission."""
        if mission_id in self._monitoring:
            return

        self._monitoring.add(mission_id)
        self.metrics[mission_id] = ProgressMetrics()
        self.updates[mission_id] = []
        self.checkpoints[mission_id] = []

        # Start background monitoring task
        self._monitor_tasks[mission_id] = asyncio.create_task(
            self._monitor_loop(mission_id)
        )

        logger.info(f"Started monitoring mission: {mission_id}")

    def stop_monitoring(self, mission_id: str) -> None:
        """Stop monitoring a mission."""
        self._monitoring.discard(mission_id)

        if mission_id in self._monitor_tasks:
            self._monitor_tasks[mission_id].cancel()
            del self._monitor_tasks[mission_id]

        logger.info(f"Stopped monitoring mission: {mission_id}")

    async def _monitor_loop(self, mission_id: str) -> None:
        """Background monitoring loop."""
        last_progress = 0.0
        last_update_time = time.time()

        while mission_id in self._monitoring:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                metrics = self.metrics.get(mission_id)
                if not metrics:
                    continue

                current_time = time.time()
                elapsed_minutes = (current_time - last_update_time) / 60

                # Check for stall
                if metrics.current_progress == last_progress and elapsed_minutes >= self.thresholds["stall_minutes"]:
                    self._create_alert(
                        AlertType.STALLED,
                        AlertSeverity.WARNING,
                        f"Mission stalled - no progress for {elapsed_minutes:.1f} minutes",
                        mission_id=mission_id,
                    )

                # Check progress rate
                elif metrics.progress_rate < self.thresholds["slow_progress_rate"] and metrics.current_progress > 0:
                    self._create_alert(
                        AlertType.SLOW_PROGRESS,
                        AlertSeverity.INFO,
                        f"Slow progress: {metrics.progress_rate:.1%}/min",
                        mission_id=mission_id,
                    )

                # Check error rate
                if metrics.error_rate >= self.thresholds["error_rate_critical"]:
                    self._create_alert(
                        AlertType.ERROR_RATE,
                        AlertSeverity.CRITICAL,
                        f"High error rate: {metrics.error_rate:.0%}",
                        mission_id=mission_id,
                    )
                elif metrics.error_rate >= self.thresholds["error_rate_warning"]:
                    self._create_alert(
                        AlertType.ERROR_RATE,
                        AlertSeverity.WARNING,
                        f"Elevated error rate: {metrics.error_rate:.0%}",
                        mission_id=mission_id,
                    )

                last_progress = metrics.current_progress
                last_update_time = current_time

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")

    def report_progress(
        self,
        mission_id: str,
        progress: float,
        task_id: Optional[str] = None,
        message: str = "",
        items_completed: int = 0,
        items_total: int = 0,
    ) -> None:
        """
        Report progress update.

        Args:
            mission_id: Mission ID
            progress: Current progress (0-1)
            task_id: Optional task ID
            message: Progress message
            items_completed: Items completed count
            items_total: Total items count
        """
        self.stats["updates_processed"] += 1

        metrics = self.metrics.get(mission_id)
        if not metrics:
            return

        # Calculate delta
        delta = progress - metrics.current_progress

        # Create update
        update = ProgressUpdate(
            mission_id=mission_id,
            task_id=task_id,
            progress=progress,
            delta=delta,
            message=message,
            items_completed=items_completed,
            items_total=items_total,
        )

        # Store update
        if mission_id in self.updates:
            self.updates[mission_id].append(update)

        # Update metrics
        self._update_metrics(mission_id, update)

        # Notify callbacks
        for callback in self._progress_callbacks:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _update_metrics(self, mission_id: str, update: ProgressUpdate) -> None:
        """Update metrics from progress update."""
        metrics = self.metrics.get(mission_id)
        if not metrics:
            return

        old_progress = metrics.current_progress
        metrics.current_progress = update.progress

        # Calculate progress rate
        updates = self.updates.get(mission_id, [])
        if len(updates) >= 2:
            first_update = updates[0]
            elapsed = (update.timestamp - first_update.timestamp).total_seconds() / 60
            if elapsed > 0:
                metrics.progress_rate = (update.progress - first_update.progress) / elapsed

        # Calculate time estimates
        if metrics.progress_rate > 0:
            remaining_progress = 1.0 - update.progress
            remaining_minutes = remaining_progress / metrics.progress_rate
            metrics.estimated_remaining = timedelta(minutes=remaining_minutes)
            metrics.estimated_completion = datetime.now() + metrics.estimated_remaining

        # Calculate elapsed time
        if updates:
            metrics.elapsed_time = update.timestamp - updates[0].timestamp

    def report_task_complete(
        self,
        mission_id: str,
        task_id: str,
        duration: timedelta,
    ) -> None:
        """Report task completion."""
        metrics = self.metrics.get(mission_id)
        if metrics:
            metrics.tasks_completed += 1

            # Update average duration
            if metrics.tasks_completed == 1:
                metrics.avg_task_duration = duration
            else:
                # Running average
                prev_avg = metrics.avg_task_duration.total_seconds()
                new_val = duration.total_seconds()
                n = metrics.tasks_completed
                new_avg = prev_avg + (new_val - prev_avg) / n
                metrics.avg_task_duration = timedelta(seconds=new_avg)

            # Calculate throughput
            if metrics.elapsed_time.total_seconds() > 0:
                metrics.throughput = metrics.tasks_completed / (
                    metrics.elapsed_time.total_seconds() / 60
                )

    def report_task_failed(
        self,
        mission_id: str,
        task_id: str,
        error: str,
    ) -> None:
        """Report task failure."""
        metrics = self.metrics.get(mission_id)
        if metrics:
            metrics.tasks_failed += 1

            total_tasks = metrics.tasks_completed + metrics.tasks_failed
            if total_tasks > 0:
                metrics.error_rate = metrics.tasks_failed / total_tasks

        self._create_alert(
            AlertType.TASK_FAILED,
            AlertSeverity.WARNING,
            f"Task failed: {error}",
            mission_id=mission_id,
            task_id=task_id,
        )

    def report_resource_usage(
        self,
        mission_id: str,
        api_calls: int = 0,
        tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Report resource usage."""
        metrics = self.metrics.get(mission_id)
        if metrics:
            metrics.api_calls += api_calls
            metrics.tokens_used += tokens
            metrics.cost_incurred += cost

    def create_checkpoint(
        self,
        mission_id: str,
        completed_tasks: List[str],
        current_task: Optional[str] = None,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> ProgressCheckpoint:
        """Create a progress checkpoint."""
        self.stats["checkpoints_created"] += 1

        metrics = self.metrics.get(mission_id)
        progress = metrics.current_progress if metrics else 0.0

        checkpoint = ProgressCheckpoint(
            mission_id=mission_id,
            checkpoint_id=f"cp_{int(time.time())}",
            progress=progress,
            timestamp=datetime.now(),
            completed_tasks=completed_tasks.copy(),
            current_task=current_task,
            outputs=outputs or {},
        )

        if mission_id not in self.checkpoints:
            self.checkpoints[mission_id] = []
        self.checkpoints[mission_id].append(checkpoint)

        logger.debug(f"Created checkpoint: {checkpoint.checkpoint_id}")

        return checkpoint

    def get_latest_checkpoint(
        self,
        mission_id: str,
    ) -> Optional[ProgressCheckpoint]:
        """Get latest checkpoint for mission."""
        checkpoints = self.checkpoints.get(mission_id, [])
        return checkpoints[-1] if checkpoints else None

    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **details,
    ) -> Alert:
        """Create an alert."""
        self.alert_counter += 1
        self.stats["alerts_generated"] += 1

        alert = Alert(
            id=f"alert_{self.alert_counter}",
            type=alert_type,
            severity=severity,
            message=message,
            mission_id=mission_id,
            task_id=task_id,
            details=details,
        )

        self.alerts[alert.id] = alert

        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.log(
            logging.WARNING if severity.value in ("warning", "error", "critical") else logging.INFO,
            f"Alert [{severity.value}]: {message}",
        )

        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        alert = self.alerts.get(alert_id)
        if alert:
            alert.acknowledged_at = datetime.now()
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        alert = self.alerts.get(alert_id)
        if alert:
            alert.resolved_at = datetime.now()
            return True
        return False

    def get_active_alerts(
        self,
        mission_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Alert]:
        """Get active alerts."""
        alerts = [a for a in self.alerts.values() if a.is_active]

        if mission_id:
            alerts = [a for a in alerts if a.mission_id == mission_id]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def get_metrics(self, mission_id: str) -> Optional[ProgressMetrics]:
        """Get current metrics for mission."""
        return self.metrics.get(mission_id)

    def on_alert(self, callback: Callable[[Alert], None]) -> None:
        """Register alert callback."""
        self._alert_callbacks.append(callback)

    def on_progress(self, callback: Callable[[ProgressUpdate], None]) -> None:
        """Register progress callback."""
        self._progress_callbacks.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            **self.stats,
            "active_missions": len(self._monitoring),
            "active_alerts": len([a for a in self.alerts.values() if a.is_active]),
        }


def demo():
    """Demonstrate progress monitor."""
    import asyncio

    print("=" * 60)
    print("BAEL Progress Monitor Demo")
    print("=" * 60)

    monitor = ProgressMonitor()
    mission_id = "mission_001"

    # Register callbacks
    monitor.on_alert(lambda a: print(f"  ALERT: [{a.severity.value}] {a.message}"))
    monitor.on_progress(lambda p: print(f"  Progress: {p.progress:.0%} - {p.message}"))

    # Start monitoring
    monitor.start_monitoring(mission_id)

    # Simulate progress
    print("\nSimulating progress updates:")

    for i in range(1, 6):
        progress = i * 0.2
        monitor.report_progress(
            mission_id,
            progress=progress,
            message=f"Completed step {i}",
            items_completed=i,
            items_total=5,
        )

        # Report task completion
        monitor.report_task_complete(
            mission_id,
            f"task_{i}",
            timedelta(seconds=30),
        )

    # Simulate failure
    monitor.report_task_failed(mission_id, "task_6", "Connection timeout")

    # Create checkpoint
    checkpoint = monitor.create_checkpoint(
        mission_id,
        completed_tasks=["task_1", "task_2", "task_3", "task_4", "task_5"],
    )
    print(f"\nCheckpoint: {checkpoint.checkpoint_id}")

    # Get metrics
    metrics = monitor.get_metrics(mission_id)
    if metrics:
        print(f"\nMetrics:")
        print(f"  Progress: {metrics.current_progress:.0%}")
        print(f"  Tasks completed: {metrics.tasks_completed}")
        print(f"  Error rate: {metrics.error_rate:.0%}")
        print(f"  Throughput: {metrics.throughput:.2f} tasks/min")

    # Get alerts
    alerts = monitor.get_active_alerts(mission_id)
    print(f"\nActive alerts: {len(alerts)}")

    # Stop monitoring
    monitor.stop_monitoring(mission_id)

    print(f"\nStats: {monitor.get_stats()}")


if __name__ == "__main__":
    demo()
