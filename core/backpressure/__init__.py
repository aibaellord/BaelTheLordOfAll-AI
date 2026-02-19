"""
BAEL Backpressure Engine Implementation
========================================

Flow control for overwhelmed systems.

"Ba'el resists overflow with measured response." — Ba'el
"""

import asyncio
import logging
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.Backpressure")


# ============================================================================
# ENUMS
# ============================================================================

class BackpressureStrategy(Enum):
    """Backpressure handling strategies."""
    DROP_OLDEST = "drop_oldest"   # Drop oldest items
    DROP_NEWEST = "drop_newest"   # Drop newest items
    BLOCK = "block"               # Block until space
    REJECT = "reject"             # Reject new items
    THROTTLE = "throttle"         # Slow down producers
    SAMPLE = "sample"             # Keep only every nth


class BackpressureState(Enum):
    """System state."""
    NORMAL = "normal"             # Under capacity
    WARNING = "warning"           # Approaching limit
    CRITICAL = "critical"         # At capacity
    OVERLOAD = "overload"         # Above capacity


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BackpressureMetrics:
    """Backpressure metrics."""
    items_received: int = 0
    items_dropped: int = 0
    items_processed: int = 0
    current_queue_size: int = 0
    peak_queue_size: int = 0
    avg_processing_time_ms: float = 0.0


@dataclass
class BackpressureConfig:
    """Backpressure configuration."""
    max_queue_size: int = 1000
    strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST

    # Thresholds
    warning_threshold: float = 0.7    # 70%
    critical_threshold: float = 0.9   # 90%

    # Throttling
    min_rate: float = 0.1  # Minimum rate when throttled
    throttle_factor: float = 0.5  # Rate reduction factor

    # Sampling
    sample_rate: int = 10  # Keep every nth when sampling


@dataclass
class FlowController:
    """A flow controller."""
    id: str
    name: str
    config: BackpressureConfig

    # State
    state: BackpressureState = BackpressureState.NORMAL
    current_rate: float = 1.0  # 1.0 = full speed

    # Metrics
    metrics: BackpressureMetrics = field(default_factory=BackpressureMetrics)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state.value,
            'current_rate': self.current_rate,
            'queue_size': self.metrics.current_queue_size,
            'max_queue_size': self.config.max_queue_size
        }


# ============================================================================
# BACKPRESSURE ENGINE
# ============================================================================

class BackpressureEngine:
    """
    Backpressure handling engine.

    Features:
    - Multiple strategies
    - Rate limiting
    - Queue management
    - Automatic throttling

    "Ba'el flows like water, adapting to pressure." — Ba'el
    """

    def __init__(self, default_config: Optional[BackpressureConfig] = None):
        """Initialize backpressure engine."""
        self.default_config = default_config or BackpressureConfig()

        # Controllers
        self._controllers: Dict[str, FlowController] = {}
        self._queues: Dict[str, deque] = {}

        # Processing
        self._processors: Dict[str, Callable] = {}
        self._processing_tasks: Dict[str, asyncio.Task] = {}

        # Rate limiting
        self._last_process_time: Dict[str, float] = {}
        self._sample_counter: Dict[str, int] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'controllers_created': 0,
            'total_items': 0,
            'total_dropped': 0
        }

        logger.info("Backpressure Engine initialized")

    # ========================================================================
    # CONTROLLER MANAGEMENT
    # ========================================================================

    def create_controller(
        self,
        name: str,
        config: Optional[BackpressureConfig] = None,
        controller_id: Optional[str] = None
    ) -> FlowController:
        """
        Create a flow controller.

        Args:
            name: Controller name
            config: Configuration
            controller_id: Optional ID

        Returns:
            FlowController
        """
        controller = FlowController(
            id=controller_id or str(uuid.uuid4()),
            name=name,
            config=config or self.default_config
        )

        with self._lock:
            self._controllers[controller.id] = controller
            self._queues[controller.id] = deque(
                maxlen=controller.config.max_queue_size if
                controller.config.strategy != BackpressureStrategy.BLOCK
                else None
            )
            self._sample_counter[controller.id] = 0
            self._stats['controllers_created'] += 1

        logger.info(f"Controller created: {name}")

        return controller

    def get_or_create(
        self,
        name: str,
        **kwargs
    ) -> FlowController:
        """Get controller or create if not exists."""
        with self._lock:
            for controller in self._controllers.values():
                if controller.name == name:
                    return controller

        return self.create_controller(name, **kwargs)

    # ========================================================================
    # PUSH / PULL
    # ========================================================================

    async def push(
        self,
        controller_id: str,
        item: Any,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Push item into queue with backpressure.

        Args:
            controller_id: Controller to use
            item: Item to push
            timeout: Timeout for blocking strategy

        Returns:
            True if accepted, False if dropped
        """
        controller = self._controllers.get(controller_id)
        if not controller:
            raise ValueError(f"Controller not found: {controller_id}")

        queue = self._queues[controller_id]
        config = controller.config

        controller.metrics.items_received += 1
        self._stats['total_items'] += 1

        # Update state
        self._update_state(controller, len(queue))

        # Handle based on strategy
        if config.strategy == BackpressureStrategy.BLOCK:
            return await self._handle_block(controller, queue, item, timeout)

        elif config.strategy == BackpressureStrategy.REJECT:
            if len(queue) >= config.max_queue_size:
                self._drop_item(controller)
                return False
            queue.append(item)
            return True

        elif config.strategy == BackpressureStrategy.DROP_NEWEST:
            if len(queue) >= config.max_queue_size:
                self._drop_item(controller)
                return False
            queue.append(item)
            return True

        elif config.strategy == BackpressureStrategy.DROP_OLDEST:
            if len(queue) >= config.max_queue_size:
                queue.popleft()  # Drop oldest
                self._drop_item(controller)
            queue.append(item)
            return True

        elif config.strategy == BackpressureStrategy.THROTTLE:
            return await self._handle_throttle(controller, queue, item)

        elif config.strategy == BackpressureStrategy.SAMPLE:
            return self._handle_sample(controller, queue, item)

        return False

    async def _handle_block(
        self,
        controller: FlowController,
        queue: deque,
        item: Any,
        timeout: Optional[float]
    ) -> bool:
        """Handle blocking strategy."""
        start = time.time()

        while len(queue) >= controller.config.max_queue_size:
            if timeout and (time.time() - start) >= timeout:
                self._drop_item(controller)
                return False

            await asyncio.sleep(0.01)

        queue.append(item)
        return True

    async def _handle_throttle(
        self,
        controller: FlowController,
        queue: deque,
        item: Any
    ) -> bool:
        """Handle throttling strategy."""
        config = controller.config

        # Calculate required delay based on queue size
        ratio = len(queue) / config.max_queue_size

        if ratio > config.warning_threshold:
            # Reduce rate
            controller.current_rate = max(
                config.min_rate,
                1.0 - (ratio * config.throttle_factor)
            )

            delay = (1.0 - controller.current_rate) * 0.1
            if delay > 0:
                await asyncio.sleep(delay)
        else:
            controller.current_rate = 1.0

        if len(queue) < config.max_queue_size:
            queue.append(item)
            return True

        self._drop_item(controller)
        return False

    def _handle_sample(
        self,
        controller: FlowController,
        queue: deque,
        item: Any
    ) -> bool:
        """Handle sampling strategy."""
        config = controller.config

        self._sample_counter[controller.id] += 1

        # Keep every nth sample when at capacity
        if len(queue) >= config.max_queue_size * config.critical_threshold:
            if self._sample_counter[controller.id] % config.sample_rate != 0:
                self._drop_item(controller)
                return False

        if len(queue) < config.max_queue_size:
            queue.append(item)
            return True

        self._drop_item(controller)
        return False

    def _drop_item(self, controller: FlowController) -> None:
        """Record dropped item."""
        controller.metrics.items_dropped += 1
        self._stats['total_dropped'] += 1

    async def pull(
        self,
        controller_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Any]:
        """
        Pull item from queue.

        Args:
            controller_id: Controller to use
            timeout: Timeout to wait for item

        Returns:
            Item or None if empty
        """
        controller = self._controllers.get(controller_id)
        if not controller:
            raise ValueError(f"Controller not found: {controller_id}")

        queue = self._queues[controller_id]

        if timeout:
            start = time.time()
            while not queue:
                if (time.time() - start) >= timeout:
                    return None
                await asyncio.sleep(0.01)

        if queue:
            item = queue.popleft()
            controller.metrics.items_processed += 1
            controller.metrics.current_queue_size = len(queue)
            self._update_state(controller, len(queue))
            return item

        return None

    # ========================================================================
    # PROCESSING
    # ========================================================================

    def register_processor(
        self,
        controller_id: str,
        processor: Callable
    ) -> None:
        """Register a processor for a controller."""
        self._processors[controller_id] = processor

    async def start_processing(self, controller_id: str) -> None:
        """Start processing queue."""
        if controller_id in self._processing_tasks:
            return

        task = asyncio.create_task(self._process_loop(controller_id))
        self._processing_tasks[controller_id] = task

    async def stop_processing(self, controller_id: str) -> None:
        """Stop processing queue."""
        task = self._processing_tasks.get(controller_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._processing_tasks[controller_id]

    async def _process_loop(self, controller_id: str) -> None:
        """Process loop for controller."""
        processor = self._processors.get(controller_id)

        while True:
            item = await self.pull(controller_id, timeout=1.0)

            if item is not None and processor:
                start = time.time()

                try:
                    if asyncio.iscoroutinefunction(processor):
                        await processor(item)
                    else:
                        await asyncio.to_thread(processor, item)

                except Exception as e:
                    logger.error(f"Processing error: {e}")

                # Update timing
                elapsed_ms = (time.time() - start) * 1000
                controller = self._controllers.get(controller_id)
                if controller:
                    n = controller.metrics.items_processed
                    avg = controller.metrics.avg_processing_time_ms
                    controller.metrics.avg_processing_time_ms = (
                        (avg * (n - 1) + elapsed_ms) / n
                    )

    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================

    def _update_state(self, controller: FlowController, queue_size: int) -> None:
        """Update controller state."""
        config = controller.config
        ratio = queue_size / config.max_queue_size

        controller.metrics.current_queue_size = queue_size
        controller.metrics.peak_queue_size = max(
            controller.metrics.peak_queue_size,
            queue_size
        )

        if ratio >= 1.0:
            controller.state = BackpressureState.OVERLOAD
        elif ratio >= config.critical_threshold:
            controller.state = BackpressureState.CRITICAL
        elif ratio >= config.warning_threshold:
            controller.state = BackpressureState.WARNING
        else:
            controller.state = BackpressureState.NORMAL

    def get_pressure(self, controller_id: str) -> float:
        """Get current pressure level (0-1)."""
        controller = self._controllers.get(controller_id)
        if not controller:
            return 0.0

        queue = self._queues.get(controller_id)
        if not queue:
            return 0.0

        return len(queue) / controller.config.max_queue_size

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_controller(self, controller_id: str) -> Optional[FlowController]:
        """Get controller by ID."""
        return self._controllers.get(controller_id)

    def list_controllers(self) -> List[FlowController]:
        """List all controllers."""
        return list(self._controllers.values())

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        controller_stats = {
            c.name: {
                'state': c.state.value,
                'pressure': self.get_pressure(c.id),
                'rate': c.current_rate
            }
            for c in self._controllers.values()
        }

        return {
            'controllers': controller_stats,
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

backpressure_engine = BackpressureEngine()


def create_flow_controller(name: str, **kwargs) -> FlowController:
    """Create flow controller."""
    return backpressure_engine.create_controller(name, **kwargs)


async def push_with_backpressure(controller_id: str, item: Any) -> bool:
    """Push with backpressure."""
    return await backpressure_engine.push(controller_id, item)


async def pull_from_queue(controller_id: str) -> Optional[Any]:
    """Pull from queue."""
    return await backpressure_engine.pull(controller_id)
