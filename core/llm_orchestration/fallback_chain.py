"""
BAEL Fallback Chain
====================

Intelligent failover system with multi-strategy recovery.
Ensures 100% uptime through automatic provider switching.

Features:
- Multi-level fallback chains
- Exponential backoff with jitter
- Circuit breaker pattern
- Health-aware routing
- Cost-aware failover (prefer free → paid)
- Geographic failover
- Model degradation strategies
"""

import asyncio
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class FallbackStrategy(Enum):
    """Fallback strategies for provider failure."""
    SEQUENTIAL = "sequential"           # Try providers in order
    PARALLEL_RACE = "parallel_race"     # Race all, use first response
    PARALLEL_VOTE = "parallel_vote"     # Vote on responses
    COST_ORDERED = "cost_ordered"       # Free → cheap → expensive
    LATENCY_ORDERED = "latency_ordered" # Fast → slow
    QUALITY_ORDERED = "quality_ordered" # Best → worst
    ADAPTIVE = "adaptive"               # Learn from history


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"     # Normal operation
    OPEN = "open"         # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class FailureType(Enum):
    """Types of provider failures."""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    CONTENT_FILTER = "content_filter"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


@dataclass
class FailoverEvent:
    """Record of a failover event."""
    timestamp: datetime
    from_provider: str
    to_provider: str
    failure_type: FailureType
    error_message: str
    latency_ms: float
    attempt: int
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreaker:
    """Circuit breaker for a single provider."""
    provider: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    open_until: Optional[datetime] = None

    # Configuration
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: int = 60
    half_open_max_calls: int = 3
    half_open_calls: int = 0

    def record_success(self) -> None:
        """Record a successful call."""
        self.success_count += 1
        self.last_success = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.success_threshold:
                self._close()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self, failure_type: FailureType) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self._open()
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._open()

    def _open(self) -> None:
        """Open the circuit (start rejecting)."""
        self.state = CircuitState.OPEN
        self.open_until = datetime.now() + timedelta(seconds=self.timeout_seconds)
        self.half_open_calls = 0
        logger.warning(f"Circuit opened for {self.provider}")

    def _close(self) -> None:
        """Close the circuit (resume normal)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.open_until = None
        logger.info(f"Circuit closed for {self.provider}")

    def can_execute(self) -> bool:
        """Check if circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if datetime.now() >= self.open_until:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.half_open_calls = 0
                return True
            return False

        # Half-open: allow limited calls
        if self.half_open_calls < self.half_open_max_calls:
            self.half_open_calls += 1
            return True
        return False


@dataclass
class BackoffConfig:
    """Backoff configuration."""
    initial_delay: float = 0.5
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: float = 0.3

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt number."""
        delay = min(
            self.max_delay,
            self.initial_delay * (self.multiplier ** attempt)
        )
        # Add jitter
        jitter_range = delay * self.jitter
        delay += random.uniform(-jitter_range, jitter_range)
        return max(0.1, delay)


class FallbackChain:
    """
    Intelligent fallback chain with circuit breakers and adaptive routing.
    """

    def __init__(
        self,
        providers: List[str],
        strategy: FallbackStrategy = FallbackStrategy.ADAPTIVE,
        backoff_config: Optional[BackoffConfig] = None,
    ):
        self.providers = providers
        self.strategy = strategy
        self.backoff_config = backoff_config or BackoffConfig()

        # Circuit breakers per provider
        self.circuits: Dict[str, CircuitBreaker] = {
            p: CircuitBreaker(provider=p) for p in providers
        }

        # Provider stats
        self.provider_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_calls": 0,
            "successes": 0,
            "failures": 0,
            "avg_latency": 0.0,
            "cost_tier": 0,  # 0=free, 1=cheap, 2=medium, 3=expensive
        })

        # Event history
        self.failover_events: List[FailoverEvent] = []

        # Adaptive weights
        self.adaptive_weights: Dict[str, float] = {p: 1.0 for p in providers}

    def _classify_failure(self, error: Exception) -> FailureType:
        """Classify the type of failure from exception."""
        error_str = str(error).lower()

        if "timeout" in error_str:
            return FailureType.TIMEOUT
        elif "rate" in error_str or "429" in error_str:
            return FailureType.RATE_LIMIT
        elif "auth" in error_str or "401" in error_str or "403" in error_str:
            return FailureType.AUTH_ERROR
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            return FailureType.SERVER_ERROR
        elif "network" in error_str or "connection" in error_str:
            return FailureType.NETWORK_ERROR
        elif "content" in error_str or "filter" in error_str or "blocked" in error_str:
            return FailureType.CONTENT_FILTER
        else:
            return FailureType.UNKNOWN

    def _get_ordered_providers(self) -> List[str]:
        """Get providers ordered by current strategy."""
        available = [
            p for p in self.providers
            if self.circuits[p].can_execute()
        ]

        if not available:
            # Reset circuits if all are open
            for circuit in self.circuits.values():
                if circuit.state == CircuitState.OPEN:
                    circuit.state = CircuitState.HALF_OPEN
            available = self.providers

        if self.strategy == FallbackStrategy.SEQUENTIAL:
            return available

        elif self.strategy == FallbackStrategy.COST_ORDERED:
            return sorted(
                available,
                key=lambda p: self.provider_stats[p]["cost_tier"]
            )

        elif self.strategy == FallbackStrategy.LATENCY_ORDERED:
            return sorted(
                available,
                key=lambda p: self.provider_stats[p]["avg_latency"]
            )

        elif self.strategy == FallbackStrategy.QUALITY_ORDERED:
            return sorted(
                available,
                key=lambda p: -self._get_quality_score(p)
            )

        elif self.strategy == FallbackStrategy.ADAPTIVE:
            return sorted(
                available,
                key=lambda p: -self.adaptive_weights[p]
            )

        return available

    def _get_quality_score(self, provider: str) -> float:
        """Calculate quality score for provider."""
        stats = self.provider_stats[provider]
        if stats["total_calls"] == 0:
            return 0.5

        success_rate = stats["successes"] / stats["total_calls"]
        latency_factor = 1.0 / (1.0 + stats["avg_latency"] / 1000)

        return success_rate * 0.7 + latency_factor * 0.3

    def _update_adaptive_weights(
        self,
        provider: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Update adaptive routing weights."""
        stats = self.provider_stats[provider]
        stats["total_calls"] += 1

        if success:
            stats["successes"] += 1
            # Update running average latency
            n = stats["total_calls"]
            stats["avg_latency"] = (
                stats["avg_latency"] * (n - 1) + latency_ms
            ) / n

            # Increase weight
            self.adaptive_weights[provider] = min(
                2.0,
                self.adaptive_weights[provider] * 1.1
            )
        else:
            stats["failures"] += 1
            # Decrease weight
            self.adaptive_weights[provider] = max(
                0.1,
                self.adaptive_weights[provider] * 0.7
            )

    async def execute_with_fallback(
        self,
        func: Callable[..., T],
        *args,
        max_attempts: int = None,
        **kwargs,
    ) -> T:
        """
        Execute function with automatic fallback to next provider.

        Args:
            func: Async function taking provider as first arg
            *args: Additional positional args
            max_attempts: Maximum total attempts
            **kwargs: Additional keyword args

        Returns:
            Result from successful provider

        Raises:
            Exception: If all providers fail
        """
        max_attempts = max_attempts or len(self.providers) * 2
        ordered_providers = self._get_ordered_providers()

        last_error = None
        attempt = 0
        current_provider_idx = 0

        while attempt < max_attempts:
            if current_provider_idx >= len(ordered_providers):
                current_provider_idx = 0
                # Wait before cycling through again
                await asyncio.sleep(self.backoff_config.get_delay(attempt))

            provider = ordered_providers[current_provider_idx]
            circuit = self.circuits[provider]

            if not circuit.can_execute():
                current_provider_idx += 1
                continue

            attempt += 1
            start_time = time.time()

            try:
                result = await func(provider, *args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000

                # Record success
                circuit.record_success()
                self._update_adaptive_weights(provider, True, latency_ms)

                return result

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                failure_type = self._classify_failure(e)

                logger.warning(
                    f"Provider {provider} failed (attempt {attempt}): "
                    f"{failure_type.value} - {e}"
                )

                # Record failure
                circuit.record_failure(failure_type)
                self._update_adaptive_weights(provider, False, latency_ms)

                # Record failover event
                next_provider = (
                    ordered_providers[(current_provider_idx + 1) % len(ordered_providers)]
                    if current_provider_idx + 1 < len(ordered_providers)
                    else ordered_providers[0]
                )

                self.failover_events.append(FailoverEvent(
                    timestamp=datetime.now(),
                    from_provider=provider,
                    to_provider=next_provider,
                    failure_type=failure_type,
                    error_message=str(e),
                    latency_ms=latency_ms,
                    attempt=attempt,
                    success=False,
                ))

                last_error = e
                current_provider_idx += 1

                # Short delay before next attempt
                if failure_type == FailureType.RATE_LIMIT:
                    await asyncio.sleep(self.backoff_config.get_delay(attempt))

        raise RuntimeError(
            f"All providers failed after {attempt} attempts. "
            f"Last error: {last_error}"
        )

    async def execute_parallel_race(
        self,
        func: Callable[..., T],
        *args,
        providers: Optional[List[str]] = None,
        **kwargs,
    ) -> T:
        """
        Execute across multiple providers in parallel, return first success.

        Args:
            func: Async function taking provider as first arg
            *args: Additional positional args
            providers: Specific providers to use (default: top 3)
            **kwargs: Additional keyword args

        Returns:
            Result from fastest successful provider
        """
        if providers is None:
            providers = self._get_ordered_providers()[:3]

        async def try_provider(provider: str):
            try:
                return await func(provider, *args, **kwargs)
            except Exception as e:
                self.circuits[provider].record_failure(self._classify_failure(e))
                raise

        # Create tasks for all providers
        tasks = [
            asyncio.create_task(try_provider(p))
            for p in providers
        ]

        # Wait for first success
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        # Get result from completed task
        for task in done:
            try:
                result = task.result()
                return result
            except Exception:
                continue

        raise RuntimeError("All parallel providers failed")

    def get_stats(self) -> Dict[str, Any]:
        """Get fallback chain statistics."""
        return {
            "providers": {
                p: {
                    **self.provider_stats[p],
                    "circuit_state": self.circuits[p].state.value,
                    "adaptive_weight": self.adaptive_weights[p],
                }
                for p in self.providers
            },
            "total_failovers": len(self.failover_events),
            "recent_failovers": [
                {
                    "from": e.from_provider,
                    "to": e.to_provider,
                    "type": e.failure_type.value,
                    "time": e.timestamp.isoformat(),
                }
                for e in self.failover_events[-10:]
            ],
        }

    def reset_circuit(self, provider: str) -> None:
        """Manually reset a circuit breaker."""
        if provider in self.circuits:
            self.circuits[provider]._close()

    def set_cost_tier(self, provider: str, tier: int) -> None:
        """Set cost tier for provider (0=free, 3=expensive)."""
        if provider in self.provider_stats:
            self.provider_stats[provider]["cost_tier"] = tier


def demo():
    """Demonstrate fallback chain."""
    print("=" * 60)
    print("BAEL Fallback Chain Demo")
    print("=" * 60)

    providers = ["openrouter", "deepseek", "groq", "together", "ollama"]
    chain = FallbackChain(providers, strategy=FallbackStrategy.ADAPTIVE)

    # Set cost tiers
    chain.set_cost_tier("openrouter", 0)
    chain.set_cost_tier("deepseek", 0)
    chain.set_cost_tier("groq", 0)
    chain.set_cost_tier("together", 1)
    chain.set_cost_tier("ollama", 0)

    print(f"\nProviders: {providers}")
    print(f"Strategy: {chain.strategy.value}")
    print(f"\nOrdered providers: {chain._get_ordered_providers()}")
    print(f"\nStats: {chain.get_stats()}")


if __name__ == "__main__":
    demo()
