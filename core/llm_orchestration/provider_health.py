"""
BAEL Provider Health Monitor
=============================

Continuous health monitoring for all LLM providers.
Ensures optimal routing by tracking real-time provider status.

Features:
- Active health probing
- Passive monitoring from request outcomes
- Latency tracking and trending
- Rate limit detection
- Automatic recovery detection
- Health history and analytics
- Alerting on degradation
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class ProbeType(Enum):
    """Types of health probes."""
    PING = "ping"           # Simple connectivity
    COMPLETION = "completion"  # Actual API call
    EMBEDDING = "embedding"    # Embedding API
    STREAMING = "streaming"    # Streaming API


@dataclass
class HealthMetrics:
    """Health metrics for a provider."""
    provider: str
    status: HealthStatus = HealthStatus.UNKNOWN

    # Latency metrics (ms)
    last_latency: float = 0.0
    avg_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0

    # Success/failure tracking
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 1.0

    # Rate limiting
    rate_limited: bool = False
    rate_limit_reset: Optional[datetime] = None

    # Timestamps
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    status_since: Optional[datetime] = None

    # History
    latency_history: deque = field(default_factory=lambda: deque(maxlen=100))
    status_history: deque = field(default_factory=lambda: deque(maxlen=50))

    def update_latency(self, latency_ms: float) -> None:
        """Update latency metrics."""
        self.last_latency = latency_ms
        self.latency_history.append(latency_ms)

        if self.latency_history:
            sorted_latencies = sorted(self.latency_history)
            n = len(sorted_latencies)

            self.avg_latency = sum(sorted_latencies) / n
            self.p50_latency = sorted_latencies[n // 2]
            self.p95_latency = sorted_latencies[int(n * 0.95)]
            self.p99_latency = sorted_latencies[int(n * 0.99)]

    def update_success_rate(self) -> None:
        """Recalculate success rate."""
        total = self.success_count + self.failure_count
        if total > 0:
            self.success_rate = self.success_count / total


@dataclass
class HealthProbeResult:
    """Result of a health probe."""
    provider: str
    probe_type: ProbeType
    success: bool
    latency_ms: float
    timestamp: datetime
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProviderHealthMonitor:
    """
    Monitors health of all LLM providers.
    """

    # Health thresholds
    LATENCY_DEGRADED_THRESHOLD = 5000  # ms
    LATENCY_UNHEALTHY_THRESHOLD = 15000  # ms
    SUCCESS_RATE_DEGRADED = 0.9
    SUCCESS_RATE_UNHEALTHY = 0.5
    FAILURE_WINDOW_SIZE = 10

    def __init__(
        self,
        providers: List[str],
        probe_interval: int = 60,  # seconds
    ):
        self.providers = providers
        self.probe_interval = probe_interval

        # Initialize metrics for each provider
        self.metrics: Dict[str, HealthMetrics] = {
            p: HealthMetrics(provider=p) for p in providers
        }

        # Recent failures for quick degradation detection
        self.recent_failures: Dict[str, deque] = {
            p: deque(maxlen=self.FAILURE_WINDOW_SIZE) for p in providers
        }

        # Callbacks for status changes
        self.status_callbacks: List[Callable[[str, HealthStatus, HealthStatus], None]] = []

        # Probe task
        self._probe_task: Optional[asyncio.Task] = None
        self._running = False

    def record_success(
        self,
        provider: str,
        latency_ms: float,
    ) -> None:
        """Record a successful request."""
        if provider not in self.metrics:
            self.metrics[provider] = HealthMetrics(provider=provider)

        metrics = self.metrics[provider]
        metrics.success_count += 1
        metrics.last_success = datetime.now()
        metrics.update_latency(latency_ms)
        metrics.update_success_rate()

        # Clear rate limiting if success
        if metrics.rate_limited:
            metrics.rate_limited = False
            metrics.rate_limit_reset = None

        # Record in recent (True = success)
        self.recent_failures[provider].append(True)

        # Update status
        self._update_status(provider)

    def record_failure(
        self,
        provider: str,
        error: Optional[str] = None,
        is_rate_limit: bool = False,
    ) -> None:
        """Record a failed request."""
        if provider not in self.metrics:
            self.metrics[provider] = HealthMetrics(provider=provider)

        metrics = self.metrics[provider]
        metrics.failure_count += 1
        metrics.last_failure = datetime.now()
        metrics.update_success_rate()

        if is_rate_limit:
            metrics.rate_limited = True
            metrics.rate_limit_reset = datetime.now() + timedelta(minutes=1)

        # Record in recent (False = failure)
        self.recent_failures[provider].append(False)

        # Update status
        self._update_status(provider)

    def _update_status(self, provider: str) -> None:
        """Update provider status based on metrics."""
        metrics = self.metrics[provider]
        old_status = metrics.status

        # Calculate recent success rate
        recent = list(self.recent_failures.get(provider, []))
        if recent:
            recent_success_rate = sum(1 for x in recent if x) / len(recent)
        else:
            recent_success_rate = 1.0

        # Determine new status
        if metrics.rate_limited:
            new_status = HealthStatus.DEGRADED
        elif recent_success_rate < self.SUCCESS_RATE_UNHEALTHY:
            new_status = HealthStatus.UNHEALTHY
        elif recent_success_rate < self.SUCCESS_RATE_DEGRADED:
            new_status = HealthStatus.DEGRADED
        elif metrics.avg_latency > self.LATENCY_UNHEALTHY_THRESHOLD:
            new_status = HealthStatus.UNHEALTHY
        elif metrics.avg_latency > self.LATENCY_DEGRADED_THRESHOLD:
            new_status = HealthStatus.DEGRADED
        else:
            new_status = HealthStatus.HEALTHY

        # Update if changed
        if new_status != old_status:
            metrics.status = new_status
            metrics.status_since = datetime.now()
            metrics.status_history.append({
                "status": new_status.value,
                "timestamp": datetime.now().isoformat(),
            })

            # Notify callbacks
            for callback in self.status_callbacks:
                try:
                    callback(provider, old_status, new_status)
                except Exception as e:
                    logger.error(f"Status callback error: {e}")

    def get_status(self, provider: str) -> HealthStatus:
        """Get current status for a provider."""
        if provider in self.metrics:
            return self.metrics[provider].status
        return HealthStatus.UNKNOWN

    def get_metrics(self, provider: str) -> Optional[HealthMetrics]:
        """Get metrics for a provider."""
        return self.metrics.get(provider)

    def get_healthy_providers(self) -> List[str]:
        """Get list of healthy providers."""
        return [
            p for p, m in self.metrics.items()
            if m.status == HealthStatus.HEALTHY
        ]

    def get_available_providers(self) -> List[str]:
        """Get list of available providers (healthy or degraded)."""
        return [
            p for p, m in self.metrics.items()
            if m.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNKNOWN)
        ]

    def on_status_change(
        self,
        callback: Callable[[str, HealthStatus, HealthStatus], None],
    ) -> None:
        """Register callback for status changes."""
        self.status_callbacks.append(callback)

    def get_summary(self) -> Dict[str, Any]:
        """Get health summary for all providers."""
        return {
            "total_providers": len(self.providers),
            "healthy": len([m for m in self.metrics.values() if m.status == HealthStatus.HEALTHY]),
            "degraded": len([m for m in self.metrics.values() if m.status == HealthStatus.DEGRADED]),
            "unhealthy": len([m for m in self.metrics.values() if m.status == HealthStatus.UNHEALTHY]),
            "providers": {
                p: {
                    "status": m.status.value,
                    "success_rate": f"{m.success_rate:.2%}",
                    "avg_latency_ms": f"{m.avg_latency:.0f}",
                    "rate_limited": m.rate_limited,
                }
                for p, m in self.metrics.items()
            },
        }

    async def probe_provider(
        self,
        provider: str,
        probe_func: Callable[[str], Any],
    ) -> HealthProbeResult:
        """Actively probe a provider's health."""
        start = time.time()

        try:
            await probe_func(provider)
            latency_ms = (time.time() - start) * 1000

            self.record_success(provider, latency_ms)

            return HealthProbeResult(
                provider=provider,
                probe_type=ProbeType.COMPLETION,
                success=True,
                latency_ms=latency_ms,
                timestamp=datetime.now(),
            )

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            is_rate_limit = "rate" in str(e).lower() or "429" in str(e)

            self.record_failure(provider, str(e), is_rate_limit)

            return HealthProbeResult(
                provider=provider,
                probe_type=ProbeType.COMPLETION,
                success=False,
                latency_ms=latency_ms,
                timestamp=datetime.now(),
                error=str(e),
            )


def demo():
    """Demonstrate health monitoring."""
    print("=" * 60)
    print("BAEL Provider Health Monitor Demo")
    print("=" * 60)

    providers = ["openrouter", "deepseek", "groq", "together"]
    monitor = ProviderHealthMonitor(providers)

    # Register status change callback
    def on_change(provider, old, new):
        print(f"  Status change: {provider} {old.value} -> {new.value}")

    monitor.on_status_change(on_change)

    # Simulate some requests
    import random

    print("\nSimulating requests...")
    for _ in range(20):
        provider = random.choice(providers)
        if random.random() > 0.2:  # 80% success
            monitor.record_success(provider, random.uniform(100, 1000))
        else:
            monitor.record_failure(provider, "Simulated error")

    # Show summary
    print("\nHealth Summary:")
    summary = monitor.get_summary()
    print(f"  Healthy: {summary['healthy']}")
    print(f"  Degraded: {summary['degraded']}")
    print(f"  Unhealthy: {summary['unhealthy']}")

    print("\nProvider Details:")
    for provider, details in summary["providers"].items():
        print(f"  {provider}: {details['status']} ({details['success_rate']})")


if __name__ == "__main__":
    demo()
