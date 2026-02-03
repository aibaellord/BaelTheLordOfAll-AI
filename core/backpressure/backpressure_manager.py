#!/usr/bin/env python3
"""
BAEL - Backpressure Manager
Advanced backpressure management for AI agent operations.

Features:
- Flow control
- Rate limiting
- Load shedding
- Queue-based backpressure
- Reactive streams
- Demand signaling
- Overflow strategies
- Adaptive throttling
- Circuit breaker integration
- Health monitoring
"""

import asyncio
import copy
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class BackpressureStrategy(Enum):
    """Backpressure strategies."""
    DROP = "drop"
    BUFFER = "buffer"
    BLOCK = "block"
    SAMPLE = "sample"
    THROTTLE = "throttle"
    REJECT = "reject"


class OverflowAction(Enum):
    """Overflow actions."""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    ERROR = "error"
    BLOCK = "block"


class LoadLevel(Enum):
    """Load levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class FlowState(Enum):
    """Flow states."""
    FLOWING = "flowing"
    PAUSED = "paused"
    BLOCKED = "blocked"
    DRAINING = "draining"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class BackpressureConfig:
    """Backpressure configuration."""
    strategy: BackpressureStrategy = BackpressureStrategy.BUFFER
    buffer_size: int = 1000
    overflow_action: OverflowAction = OverflowAction.DROP_OLDEST
    high_watermark: float = 0.8
    low_watermark: float = 0.2
    sample_rate: float = 0.5
    throttle_rate_per_sec: float = 100.0
    block_timeout_ms: int = 5000


@dataclass
class FlowMetrics:
    """Flow metrics."""
    items_received: int = 0
    items_processed: int = 0
    items_dropped: int = 0
    items_buffered: int = 0
    items_rejected: int = 0
    avg_latency_ms: float = 0.0
    current_rate: float = 0.0
    buffer_utilization: float = 0.0
    load_level: LoadLevel = LoadLevel.NORMAL


@dataclass
class DemandSignal:
    """Demand signal from consumer."""
    consumer_id: str = ""
    demand: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BackpressureStats:
    """Backpressure statistics."""
    total_received: int = 0
    total_processed: int = 0
    total_dropped: int = 0
    total_rejected: int = 0
    buffer_overflows: int = 0
    blocks_triggered: int = 0
    pauses: int = 0
    resumes: int = 0


# =============================================================================
# RATE LIMITER
# =============================================================================

class TokenBucketLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        rate: float,
        capacity: int = 100
    ):
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens."""
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def acquire_async(
        self,
        tokens: int = 1,
        timeout: Optional[float] = None
    ) -> bool:
        """Acquire tokens async with wait."""
        start = time.time()

        while True:
            if self.acquire(tokens):
                return True

            if timeout and (time.time() - start) >= timeout:
                return False

            # Wait for tokens
            wait_time = tokens / self.rate
            await asyncio.sleep(min(wait_time, 0.1))

    def _refill(self) -> None:
        """Refill tokens."""
        now = time.time()
        elapsed = now - self._last_refill

        new_tokens = elapsed * self.rate
        self._tokens = min(self.capacity, self._tokens + new_tokens)
        self._last_refill = now

    def available(self) -> float:
        """Get available tokens."""
        with self._lock:
            self._refill()
            return self._tokens

    def set_rate(self, rate: float) -> None:
        """Set rate."""
        with self._lock:
            self.rate = rate


class SlidingWindowLimiter:
    """Sliding window rate limiter."""

    def __init__(
        self,
        rate: float,
        window_size_seconds: float = 1.0
    ):
        self.rate = rate
        self.window_size = window_size_seconds
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    def acquire(self, count: int = 1) -> bool:
        """Try to acquire."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_size

            # Remove old entries
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) + count <= self.rate:
                for _ in range(count):
                    self._timestamps.append(now)
                return True
            return False

    def current_rate(self) -> float:
        """Get current rate."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_size

            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            return len(self._timestamps) / self.window_size


# =============================================================================
# FLOW CONTROLLER
# =============================================================================

class FlowController:
    """Flow control for backpressure."""

    def __init__(
        self,
        config: BackpressureConfig
    ):
        self.controller_id = str(uuid.uuid4())
        self.config = config

        self._state = FlowState.FLOWING
        self._buffer: deque = deque(maxlen=config.buffer_size)
        self._demand: Dict[str, int] = {}

        self._lock = threading.RLock()
        self._not_full = asyncio.Condition()
        self._not_empty = asyncio.Condition()

        self._stats = BackpressureStats()
        self._metrics = FlowMetrics()

        self._on_overflow: Optional[Callable[[Any], None]] = None
        self._on_pause: Optional[Callable[[], None]] = None
        self._on_resume: Optional[Callable[[], None]] = None

    def set_callbacks(
        self,
        on_overflow: Optional[Callable[[Any], None]] = None,
        on_pause: Optional[Callable[[], None]] = None,
        on_resume: Optional[Callable[[], None]] = None
    ) -> None:
        """Set callbacks."""
        self._on_overflow = on_overflow
        self._on_pause = on_pause
        self._on_resume = on_resume

    # -------------------------------------------------------------------------
    # FLOW CONTROL
    # -------------------------------------------------------------------------

    async def submit(
        self,
        item: Any,
        timeout: Optional[float] = None
    ) -> bool:
        """Submit item with flow control."""
        with self._lock:
            self._stats.total_received += 1
            self._metrics.items_received += 1

            # Check state
            if self._state == FlowState.BLOCKED:
                if self.config.strategy == BackpressureStrategy.REJECT:
                    self._stats.total_rejected += 1
                    self._metrics.items_rejected += 1
                    return False

            # Apply strategy
            if self.config.strategy == BackpressureStrategy.DROP:
                return self._handle_drop(item)

            elif self.config.strategy == BackpressureStrategy.SAMPLE:
                return self._handle_sample(item)

            elif self.config.strategy == BackpressureStrategy.BUFFER:
                return self._handle_buffer(item)

            elif self.config.strategy == BackpressureStrategy.BLOCK:
                return await self._handle_block(item, timeout)

            elif self.config.strategy == BackpressureStrategy.THROTTLE:
                return self._handle_buffer(item)

            return False

    def _handle_drop(self, item: Any) -> bool:
        """Handle drop strategy."""
        buffer_size = len(self._buffer)
        max_size = self.config.buffer_size

        if buffer_size >= max_size:
            self._stats.total_dropped += 1
            self._metrics.items_dropped += 1
            return False

        self._buffer.append(item)
        self._metrics.items_buffered = len(self._buffer)
        return True

    def _handle_sample(self, item: Any) -> bool:
        """Handle sample strategy."""
        import random

        if random.random() > self.config.sample_rate:
            self._stats.total_dropped += 1
            self._metrics.items_dropped += 1
            return False

        return self._handle_buffer(item)

    def _handle_buffer(self, item: Any) -> bool:
        """Handle buffer strategy."""
        buffer_size = len(self._buffer)
        max_size = self.config.buffer_size

        if buffer_size >= max_size:
            # Overflow handling
            self._stats.buffer_overflows += 1

            if self.config.overflow_action == OverflowAction.DROP_OLDEST:
                dropped = self._buffer.popleft()
                self._stats.total_dropped += 1

                if self._on_overflow:
                    self._on_overflow(dropped)

                self._buffer.append(item)
                return True

            elif self.config.overflow_action == OverflowAction.DROP_NEWEST:
                self._stats.total_dropped += 1

                if self._on_overflow:
                    self._on_overflow(item)
                return False

            elif self.config.overflow_action == OverflowAction.ERROR:
                raise BufferError("Buffer overflow")

        self._buffer.append(item)
        self._metrics.items_buffered = len(self._buffer)
        self._check_watermarks()
        return True

    async def _handle_block(
        self,
        item: Any,
        timeout: Optional[float]
    ) -> bool:
        """Handle block strategy."""
        buffer_size = len(self._buffer)
        max_size = self.config.buffer_size

        if buffer_size >= max_size:
            self._stats.blocks_triggered += 1

            # Wait for space
            start = time.time()
            block_timeout = timeout or (self.config.block_timeout_ms / 1000)

            while len(self._buffer) >= max_size:
                elapsed = time.time() - start
                if elapsed >= block_timeout:
                    return False

                await asyncio.sleep(0.01)

        self._buffer.append(item)
        self._metrics.items_buffered = len(self._buffer)
        return True

    def _check_watermarks(self) -> None:
        """Check watermarks and update state."""
        utilization = len(self._buffer) / self.config.buffer_size
        self._metrics.buffer_utilization = utilization

        if utilization >= self.config.high_watermark:
            if self._state == FlowState.FLOWING:
                self._state = FlowState.PAUSED
                self._stats.pauses += 1

                if self._on_pause:
                    self._on_pause()

                self._metrics.load_level = LoadLevel.HIGH

        elif utilization <= self.config.low_watermark:
            if self._state == FlowState.PAUSED:
                self._state = FlowState.FLOWING
                self._stats.resumes += 1

                if self._on_resume:
                    self._on_resume()

                self._metrics.load_level = LoadLevel.LOW

    # -------------------------------------------------------------------------
    # CONSUMPTION
    # -------------------------------------------------------------------------

    async def consume(
        self,
        timeout: Optional[float] = None
    ) -> Optional[Any]:
        """Consume item from buffer."""
        start = time.time()

        while True:
            with self._lock:
                if self._buffer:
                    item = self._buffer.popleft()
                    self._stats.total_processed += 1
                    self._metrics.items_processed += 1
                    self._metrics.items_buffered = len(self._buffer)
                    self._check_watermarks()
                    return item

            if timeout is not None:
                if time.time() - start >= timeout:
                    return None

            await asyncio.sleep(0.001)

    def try_consume(self) -> Optional[Any]:
        """Try to consume without waiting."""
        with self._lock:
            if self._buffer:
                item = self._buffer.popleft()
                self._stats.total_processed += 1
                self._metrics.items_processed += 1
                self._metrics.items_buffered = len(self._buffer)
                self._check_watermarks()
                return item
            return None

    def consume_batch(
        self,
        max_items: int = 10
    ) -> List[Any]:
        """Consume batch of items."""
        with self._lock:
            items = []

            for _ in range(min(max_items, len(self._buffer))):
                item = self._buffer.popleft()
                items.append(item)
                self._stats.total_processed += 1
                self._metrics.items_processed += 1

            self._metrics.items_buffered = len(self._buffer)
            self._check_watermarks()
            return items

    # -------------------------------------------------------------------------
    # DEMAND SIGNALING
    # -------------------------------------------------------------------------

    def request(
        self,
        consumer_id: str,
        demand: int
    ) -> None:
        """Request items (demand signal)."""
        with self._lock:
            current = self._demand.get(consumer_id, 0)
            self._demand[consumer_id] = current + demand

    def fulfill_demand(
        self,
        consumer_id: str
    ) -> List[Any]:
        """Fulfill demand for consumer."""
        with self._lock:
            demand = self._demand.get(consumer_id, 0)
            if demand <= 0:
                return []

            items = []
            fulfilled = 0

            while fulfilled < demand and self._buffer:
                item = self._buffer.popleft()
                items.append(item)
                fulfilled += 1
                self._stats.total_processed += 1
                self._metrics.items_processed += 1

            self._demand[consumer_id] = demand - fulfilled
            self._metrics.items_buffered = len(self._buffer)
            self._check_watermarks()
            return items

    def get_pending_demand(
        self,
        consumer_id: str
    ) -> int:
        """Get pending demand."""
        with self._lock:
            return self._demand.get(consumer_id, 0)

    # -------------------------------------------------------------------------
    # STATE
    # -------------------------------------------------------------------------

    def state(self) -> FlowState:
        """Get flow state."""
        with self._lock:
            return self._state

    def pause(self) -> None:
        """Pause flow."""
        with self._lock:
            if self._state == FlowState.FLOWING:
                self._state = FlowState.PAUSED
                self._stats.pauses += 1

    def resume(self) -> None:
        """Resume flow."""
        with self._lock:
            if self._state == FlowState.PAUSED:
                self._state = FlowState.FLOWING
                self._stats.resumes += 1

    def block(self) -> None:
        """Block flow."""
        with self._lock:
            self._state = FlowState.BLOCKED

    def unblock(self) -> None:
        """Unblock flow."""
        with self._lock:
            if self._state == FlowState.BLOCKED:
                self._state = FlowState.FLOWING

    def drain(self) -> List[Any]:
        """Drain all items."""
        with self._lock:
            self._state = FlowState.DRAINING
            items = list(self._buffer)
            self._buffer.clear()
            self._stats.total_processed += len(items)
            self._metrics.items_processed += len(items)
            self._metrics.items_buffered = 0
            self._state = FlowState.FLOWING
            return items

    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------

    def metrics(self) -> FlowMetrics:
        """Get flow metrics."""
        with self._lock:
            return copy.copy(self._metrics)

    def stats(self) -> BackpressureStats:
        """Get backpressure stats."""
        with self._lock:
            return copy.copy(self._stats)

    def buffer_size(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)

    def buffer_utilization(self) -> float:
        """Get buffer utilization."""
        with self._lock:
            return len(self._buffer) / self.config.buffer_size


# =============================================================================
# BACKPRESSURE MANAGER
# =============================================================================

class BackpressureManager:
    """
    Backpressure Manager for BAEL.

    Advanced backpressure management.
    """

    def __init__(self):
        self._controllers: Dict[str, FlowController] = {}
        self._rate_limiters: Dict[str, TokenBucketLimiter] = {}
        self._window_limiters: Dict[str, SlidingWindowLimiter] = {}
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # FLOW CONTROLLERS
    # -------------------------------------------------------------------------

    def create_controller(
        self,
        strategy: BackpressureStrategy = BackpressureStrategy.BUFFER,
        buffer_size: int = 1000,
        overflow_action: OverflowAction = OverflowAction.DROP_OLDEST,
        high_watermark: float = 0.8,
        low_watermark: float = 0.2
    ) -> FlowController:
        """Create flow controller."""
        config = BackpressureConfig(
            strategy=strategy,
            buffer_size=buffer_size,
            overflow_action=overflow_action,
            high_watermark=high_watermark,
            low_watermark=low_watermark
        )

        controller = FlowController(config)

        with self._lock:
            self._controllers[controller.controller_id] = controller

        return controller

    def get_controller(
        self,
        controller_id: str
    ) -> Optional[FlowController]:
        """Get flow controller."""
        with self._lock:
            return self._controllers.get(controller_id)

    def delete_controller(self, controller_id: str) -> bool:
        """Delete flow controller."""
        with self._lock:
            if controller_id in self._controllers:
                del self._controllers[controller_id]
                return True
            return False

    # -------------------------------------------------------------------------
    # RATE LIMITERS
    # -------------------------------------------------------------------------

    def create_token_bucket(
        self,
        rate: float,
        capacity: int = 100
    ) -> TokenBucketLimiter:
        """Create token bucket limiter."""
        limiter = TokenBucketLimiter(rate, capacity)
        limiter_id = str(uuid.uuid4())

        with self._lock:
            self._rate_limiters[limiter_id] = limiter

        return limiter

    def create_sliding_window(
        self,
        rate: float,
        window_size: float = 1.0
    ) -> SlidingWindowLimiter:
        """Create sliding window limiter."""
        limiter = SlidingWindowLimiter(rate, window_size)
        limiter_id = str(uuid.uuid4())

        with self._lock:
            self._window_limiters[limiter_id] = limiter

        return limiter

    # -------------------------------------------------------------------------
    # AGGREGATION
    # -------------------------------------------------------------------------

    def get_all_metrics(self) -> Dict[str, FlowMetrics]:
        """Get metrics for all controllers."""
        with self._lock:
            return {
                cid: c.metrics()
                for cid, c in self._controllers.items()
            }

    def get_all_stats(self) -> Dict[str, BackpressureStats]:
        """Get stats for all controllers."""
        with self._lock:
            return {
                cid: c.stats()
                for cid, c in self._controllers.items()
            }

    def get_aggregate_load(self) -> LoadLevel:
        """Get aggregate load level."""
        with self._lock:
            if not self._controllers:
                return LoadLevel.NORMAL

            levels = [c.metrics().load_level for c in self._controllers.values()]

            critical_count = sum(1 for l in levels if l == LoadLevel.CRITICAL)
            high_count = sum(1 for l in levels if l == LoadLevel.HIGH)

            if critical_count > 0:
                return LoadLevel.CRITICAL
            elif high_count > len(levels) // 2:
                return LoadLevel.HIGH
            elif high_count > 0:
                return LoadLevel.NORMAL
            else:
                return LoadLevel.LOW

    # -------------------------------------------------------------------------
    # LISTING
    # -------------------------------------------------------------------------

    def list_controllers(self) -> List[str]:
        """List controller IDs."""
        with self._lock:
            return list(self._controllers.keys())

    def controller_count(self) -> int:
        """Get controller count."""
        with self._lock:
            return len(self._controllers)


class BufferError(Exception):
    """Buffer error."""
    pass


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Backpressure Manager."""
    print("=" * 70)
    print("BAEL - BACKPRESSURE MANAGER DEMO")
    print("Advanced Backpressure Management for AI Agents")
    print("=" * 70)
    print()

    manager = BackpressureManager()

    # 1. Create Controller
    print("1. CREATE FLOW CONTROLLER:")
    print("-" * 40)

    controller = manager.create_controller(
        strategy=BackpressureStrategy.BUFFER,
        buffer_size=10,
        high_watermark=0.8,
        low_watermark=0.2
    )

    print(f"   Controller: {controller.controller_id[:8]}...")
    print(f"   Strategy: {controller.config.strategy.value}")
    print(f"   Buffer size: {controller.config.buffer_size}")
    print()

    # 2. Submit Items
    print("2. SUBMIT ITEMS:")
    print("-" * 40)

    for i in range(15):
        success = await controller.submit(f"item_{i}")
        print(f"   Submit item_{i}: {success}")

    print(f"   Buffer size: {controller.buffer_size()}")
    print()

    # 3. Check Metrics
    print("3. CHECK METRICS:")
    print("-" * 40)

    metrics = controller.metrics()
    print(f"   Received: {metrics.items_received}")
    print(f"   Processed: {metrics.items_processed}")
    print(f"   Dropped: {metrics.items_dropped}")
    print(f"   Buffered: {metrics.items_buffered}")
    print(f"   Utilization: {metrics.buffer_utilization:.2%}")
    print()

    # 4. Consume Items
    print("4. CONSUME ITEMS:")
    print("-" * 40)

    for _ in range(5):
        item = await controller.consume(timeout=1.0)
        print(f"   Consumed: {item}")

    print(f"   Buffer size: {controller.buffer_size()}")
    print()

    # 5. Batch Consume
    print("5. BATCH CONSUME:")
    print("-" * 40)

    batch = controller.consume_batch(max_items=3)
    print(f"   Batch: {batch}")
    print(f"   Buffer size: {controller.buffer_size()}")
    print()

    # 6. Flow State
    print("6. FLOW STATE:")
    print("-" * 40)

    print(f"   State: {controller.state().value}")

    controller.pause()
    print(f"   After pause: {controller.state().value}")

    controller.resume()
    print(f"   After resume: {controller.state().value}")
    print()

    # 7. Demand Signaling
    print("7. DEMAND SIGNALING:")
    print("-" * 40)

    # Add items
    for i in range(5):
        await controller.submit(f"demand_item_{i}")

    controller.request("consumer_1", 3)
    print(f"   Requested: 3")
    print(f"   Pending demand: {controller.get_pending_demand('consumer_1')}")

    fulfilled = controller.fulfill_demand("consumer_1")
    print(f"   Fulfilled: {fulfilled}")
    print()

    # 8. Token Bucket Limiter
    print("8. TOKEN BUCKET LIMITER:")
    print("-" * 40)

    limiter = manager.create_token_bucket(rate=10, capacity=5)

    print(f"   Available: {limiter.available():.1f}")

    for i in range(7):
        acquired = limiter.acquire()
        print(f"   Acquire {i}: {acquired}")

    print(f"   Available after: {limiter.available():.1f}")
    print()

    # 9. Sliding Window Limiter
    print("9. SLIDING WINDOW LIMITER:")
    print("-" * 40)

    window = manager.create_sliding_window(rate=5, window_size=1.0)

    for i in range(7):
        acquired = window.acquire()
        print(f"   Acquire {i}: {acquired}")

    print(f"   Current rate: {window.current_rate():.1f}/s")
    print()

    # 10. Drop Strategy
    print("10. DROP STRATEGY:")
    print("-" * 40)

    drop_controller = manager.create_controller(
        strategy=BackpressureStrategy.DROP,
        buffer_size=3
    )

    for i in range(5):
        success = await drop_controller.submit(f"drop_{i}")
        print(f"   Submit drop_{i}: {success}")

    stats = drop_controller.stats()
    print(f"   Dropped: {stats.total_dropped}")
    print()

    # 11. Sample Strategy
    print("11. SAMPLE STRATEGY:")
    print("-" * 40)

    sample_controller = manager.create_controller(
        strategy=BackpressureStrategy.SAMPLE,
        buffer_size=100
    )
    sample_controller.config.sample_rate = 0.3

    for i in range(10):
        await sample_controller.submit(f"sample_{i}")

    print(f"   Submitted: 10")
    print(f"   Buffered: {sample_controller.buffer_size()}")
    print()

    # 12. Drain
    print("12. DRAIN BUFFER:")
    print("-" * 40)

    # Add items
    for i in range(3):
        await controller.submit(f"drain_{i}")

    drained = controller.drain()
    print(f"   Drained: {len(drained)} items")
    print(f"   Buffer size: {controller.buffer_size()}")
    print()

    # 13. Block/Unblock
    print("13. BLOCK/UNBLOCK:")
    print("-" * 40)

    controller.block()
    print(f"   State: {controller.state().value}")

    controller.unblock()
    print(f"   State: {controller.state().value}")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats = controller.stats()
    print(f"   Total received: {stats.total_received}")
    print(f"   Total processed: {stats.total_processed}")
    print(f"   Total dropped: {stats.total_dropped}")
    print(f"   Buffer overflows: {stats.buffer_overflows}")
    print(f"   Pauses: {stats.pauses}")
    print(f"   Resumes: {stats.resumes}")
    print()

    # 15. Aggregate Load
    print("15. AGGREGATE LOAD:")
    print("-" * 40)

    load = manager.get_aggregate_load()
    print(f"   Aggregate load: {load.value}")
    print(f"   Controllers: {manager.controller_count()}")
    print()

    # 16. List Controllers
    print("16. LIST CONTROLLERS:")
    print("-" * 40)

    controllers = manager.list_controllers()
    print(f"   Controllers: {len(controllers)}")
    for cid in controllers[:3]:
        print(f"     {cid[:8]}...")
    print()

    # 17. Delete Controller
    print("17. DELETE CONTROLLER:")
    print("-" * 40)

    count_before = len(manager.list_controllers())
    deleted = manager.delete_controller(drop_controller.controller_id)
    count_after = len(manager.list_controllers())

    print(f"   Deleted: {deleted}")
    print(f"   Controllers: {count_before} -> {count_after}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Backpressure Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
