#!/usr/bin/env python3
"""
BAEL - Saga Manager
Advanced saga pattern for distributed transactions.

Features:
- Saga orchestration
- Choreography support
- Compensating transactions
- Saga state machine
- Retry policies
- Timeout handling
- Saga persistence
- Event sourcing
- Dead letter handling
- Saga monitoring
"""

import asyncio
import copy
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class SagaStatus(Enum):
    """Saga status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    ABORTED = "aborted"


class StepStatus(Enum):
    """Step status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(Enum):
    """Saga execution mode."""
    ORCHESTRATION = "orchestration"
    CHOREOGRAPHY = "choreography"


class RetryStrategy(Enum):
    """Retry strategy."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class CompensationOrder(Enum):
    """Compensation execution order."""
    REVERSE = "reverse"
    PARALLEL = "parallel"
    CUSTOM = "custom"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SagaConfig:
    """Saga configuration."""
    timeout_seconds: int = 300
    step_timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_ms: int = 1000
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    compensation_order: CompensationOrder = CompensationOrder.REVERSE


@dataclass
class StepConfig:
    """Step configuration."""
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_ms: int = 1000
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    critical: bool = True


@dataclass
class StepResult:
    """Step execution result."""
    step_id: str = ""
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


@dataclass
class SagaResult:
    """Saga execution result."""
    saga_id: str = ""
    status: SagaStatus = SagaStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    steps_completed: int = 0
    steps_compensated: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


@dataclass
class SagaEvent:
    """Saga event for event sourcing."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    saga_id: str = ""
    event_type: str = ""
    step_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SagaStats:
    """Saga statistics."""
    total_sagas: int = 0
    completed: int = 0
    compensated: int = 0
    failed: int = 0
    active: int = 0
    average_duration_ms: float = 0.0


# =============================================================================
# STEP
# =============================================================================

class Step:
    """Saga step."""

    def __init__(
        self,
        step_id: Optional[str] = None,
        name: str = "",
        action: Optional[Callable[..., Awaitable[Any]]] = None,
        compensation: Optional[Callable[..., Awaitable[Any]]] = None,
        config: Optional[StepConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.step_id = step_id or str(uuid.uuid4())
        self.name = name or self.step_id
        self.action = action
        self.compensation = compensation
        self.config = config or StepConfig()
        self.metadata = metadata or {}

        self._status = StepStatus.PENDING
        self._result: Optional[Any] = None
        self._error: Optional[str] = None
        self._attempts = 0
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

    @property
    def status(self) -> StepStatus:
        """Get step status."""
        return self._status

    @status.setter
    def status(self, value: StepStatus) -> None:
        """Set step status."""
        self._status = value

    async def execute(self, context: Dict[str, Any]) -> StepResult:
        """Execute step action."""
        self._status = StepStatus.EXECUTING
        self._started_at = datetime.utcnow()

        delay = self.config.retry_delay_ms

        while self._attempts < self.config.max_retries + 1:
            self._attempts += 1

            try:
                if self.action:
                    self._result = await asyncio.wait_for(
                        self.action(context),
                        timeout=self.config.timeout_seconds
                    )

                self._status = StepStatus.COMPLETED
                self._completed_at = datetime.utcnow()
                break

            except asyncio.TimeoutError:
                self._error = f"Step timeout after {self.config.timeout_seconds}s"
                self._status = StepStatus.FAILED
            except Exception as e:
                self._error = str(e)
                self._status = StepStatus.FAILED

            if self._attempts < self.config.max_retries + 1:
                # Wait before retry
                await asyncio.sleep(delay / 1000)

                if self.config.retry_strategy == RetryStrategy.EXPONENTIAL:
                    delay *= 2
                elif self.config.retry_strategy == RetryStrategy.LINEAR:
                    delay += self.config.retry_delay_ms

        if self._status != StepStatus.COMPLETED:
            self._completed_at = datetime.utcnow()

        return self.to_result()

    async def compensate(self, context: Dict[str, Any]) -> StepResult:
        """Execute compensation."""
        self._status = StepStatus.COMPENSATING

        try:
            if self.compensation:
                await asyncio.wait_for(
                    self.compensation(context),
                    timeout=self.config.timeout_seconds
                )

            self._status = StepStatus.COMPENSATED
        except Exception as e:
            self._error = f"Compensation failed: {str(e)}"
            self._status = StepStatus.FAILED

        return self.to_result()

    def to_result(self) -> StepResult:
        """Convert to step result."""
        duration_ms = 0.0
        if self._started_at and self._completed_at:
            duration_ms = (
                self._completed_at - self._started_at
            ).total_seconds() * 1000

        return StepResult(
            step_id=self.step_id,
            status=self._status,
            result=self._result,
            error=self._error,
            attempts=self._attempts,
            started_at=self._started_at,
            completed_at=self._completed_at,
            duration_ms=duration_ms
        )

    def reset(self) -> None:
        """Reset step state."""
        self._status = StepStatus.PENDING
        self._result = None
        self._error = None
        self._attempts = 0
        self._started_at = None
        self._completed_at = None


# =============================================================================
# SAGA
# =============================================================================

class Saga:
    """Saga definition."""

    def __init__(
        self,
        saga_id: Optional[str] = None,
        name: str = "",
        config: Optional[SagaConfig] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.name = name or self.saga_id
        self.config = config or SagaConfig()
        self.metadata = metadata or {}

        self._steps: List[Step] = []
        self._status = SagaStatus.PENDING
        self._context: Dict[str, Any] = {}
        self._events: List[SagaEvent] = []

        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._current_step: int = 0

    @property
    def status(self) -> SagaStatus:
        """Get saga status."""
        return self._status

    @status.setter
    def status(self, value: SagaStatus) -> None:
        """Set saga status."""
        self._status = value
        self._add_event("status_changed", {"new_status": value.value})

    def add_step(self, step: Step) -> 'Saga':
        """Add step to saga."""
        self._steps.append(step)
        return self

    def step(
        self,
        name: str = "",
        action: Optional[Callable[..., Awaitable[Any]]] = None,
        compensation: Optional[Callable[..., Awaitable[Any]]] = None,
        config: Optional[StepConfig] = None
    ) -> 'Saga':
        """Add step fluently."""
        step = Step(
            name=name,
            action=action,
            compensation=compensation,
            config=config
        )
        return self.add_step(step)

    def get_steps(self) -> List[Step]:
        """Get all steps."""
        return self._steps.copy()

    def get_step(self, step_id: str) -> Optional[Step]:
        """Get step by ID."""
        for step in self._steps:
            if step.step_id == step_id:
                return step
        return None

    def set_context(self, key: str, value: Any) -> None:
        """Set context value."""
        self._context[key] = value

    def get_context(self, key: str) -> Optional[Any]:
        """Get context value."""
        return self._context.get(key)

    def get_full_context(self) -> Dict[str, Any]:
        """Get full context."""
        return self._context.copy()

    def _add_event(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        step_id: Optional[str] = None
    ) -> None:
        """Add event."""
        event = SagaEvent(
            saga_id=self.saga_id,
            event_type=event_type,
            step_id=step_id,
            data=data or {}
        )
        self._events.append(event)

    def get_events(self) -> List[SagaEvent]:
        """Get all events."""
        return self._events.copy()

    def to_result(self) -> SagaResult:
        """Convert to saga result."""
        duration_ms = 0.0
        if self._started_at and self._completed_at:
            duration_ms = (
                self._completed_at - self._started_at
            ).total_seconds() * 1000

        steps_completed = sum(
            1 for s in self._steps
            if s.status == StepStatus.COMPLETED
        )
        steps_compensated = sum(
            1 for s in self._steps
            if s.status == StepStatus.COMPENSATED
        )

        return SagaResult(
            saga_id=self.saga_id,
            status=self._status,
            steps_completed=steps_completed,
            steps_compensated=steps_compensated,
            started_at=self._started_at,
            completed_at=self._completed_at,
            duration_ms=duration_ms
        )


# =============================================================================
# SAGA EXECUTOR
# =============================================================================

class SagaExecutor:
    """Execute sagas."""

    def __init__(self):
        self._running: Dict[str, Saga] = {}

    async def execute(self, saga: Saga) -> SagaResult:
        """Execute saga."""
        saga._started_at = datetime.utcnow()
        saga.status = SagaStatus.RUNNING
        self._running[saga.saga_id] = saga

        try:
            # Execute steps
            for i, step in enumerate(saga.get_steps()):
                saga._current_step = i
                saga._add_event("step_started", step_id=step.step_id)

                result = await step.execute(saga.get_full_context())

                if result.status == StepStatus.COMPLETED:
                    saga._add_event(
                        "step_completed",
                        {"result": result.result},
                        step.step_id
                    )

                    # Store result in context
                    if result.result is not None:
                        saga.set_context(
                            f"step_{step.name}_result",
                            result.result
                        )
                else:
                    saga._add_event(
                        "step_failed",
                        {"error": result.error},
                        step.step_id
                    )

                    if step.config.critical:
                        # Trigger compensation
                        await self._compensate(saga, i)
                        saga._completed_at = datetime.utcnow()
                        return saga.to_result()

            saga.status = SagaStatus.COMPLETED
            saga._completed_at = datetime.utcnow()
            saga._add_event("saga_completed")

        except asyncio.TimeoutError:
            saga._add_event("saga_timeout")
            await self._compensate(saga, saga._current_step)
        except Exception as e:
            saga._add_event("saga_error", {"error": str(e)})
            await self._compensate(saga, saga._current_step)
        finally:
            del self._running[saga.saga_id]

        return saga.to_result()

    async def _compensate(
        self,
        saga: Saga,
        from_step: int
    ) -> None:
        """Execute compensations."""
        saga.status = SagaStatus.COMPENSATING
        saga._add_event("compensation_started")

        steps = saga.get_steps()[:from_step + 1]

        if saga.config.compensation_order == CompensationOrder.REVERSE:
            steps = list(reversed(steps))

        for step in steps:
            if step.status == StepStatus.COMPLETED and step.compensation:
                saga._add_event(
                    "step_compensating",
                    step_id=step.step_id
                )

                result = await step.compensate(saga.get_full_context())

                if result.status == StepStatus.COMPENSATED:
                    saga._add_event(
                        "step_compensated",
                        step_id=step.step_id
                    )
                else:
                    saga._add_event(
                        "compensation_failed",
                        {"error": result.error},
                        step.step_id
                    )

        saga.status = SagaStatus.COMPENSATED
        saga._add_event("compensation_completed")

    def is_running(self, saga_id: str) -> bool:
        """Check if saga is running."""
        return saga_id in self._running

    def running_count(self) -> int:
        """Get running saga count."""
        return len(self._running)


# =============================================================================
# SAGA MANAGER
# =============================================================================

class SagaManager:
    """
    Saga Manager for BAEL.

    Advanced saga pattern implementation.
    """

    def __init__(self, config: Optional[SagaConfig] = None):
        self.config = config or SagaConfig()

        self._sagas: Dict[str, Saga] = {}
        self._definitions: Dict[str, Saga] = {}
        self._executor = SagaExecutor()

        self._stats = SagaStats()
        self._durations: List[float] = []
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # SAGA DEFINITIONS
    # -------------------------------------------------------------------------

    async def define(
        self,
        name: str,
        config: Optional[SagaConfig] = None
    ) -> Saga:
        """Define a new saga template."""
        saga = Saga(
            name=name,
            config=config or self.config
        )

        async with self._lock:
            self._definitions[name] = saga

        return saga

    async def get_definition(self, name: str) -> Optional[Saga]:
        """Get saga definition."""
        async with self._lock:
            return self._definitions.get(name)

    # -------------------------------------------------------------------------
    # SAGA CREATION
    # -------------------------------------------------------------------------

    async def create(
        self,
        name: str = "",
        config: Optional[SagaConfig] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Saga:
        """Create new saga instance."""
        saga = Saga(
            name=name,
            config=config or self.config,
            metadata=metadata
        )

        if context:
            for key, value in context.items():
                saga.set_context(key, value)

        async with self._lock:
            self._sagas[saga.saga_id] = saga
            self._stats.total_sagas += 1

        return saga

    async def create_from_definition(
        self,
        definition_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Saga]:
        """Create saga from definition."""
        async with self._lock:
            definition = self._definitions.get(definition_name)
            if not definition:
                return None

            saga = Saga(
                name=definition.name,
                config=definition.config,
                metadata=definition.metadata.copy()
            )

            for step in definition.get_steps():
                saga.add_step(Step(
                    name=step.name,
                    action=step.action,
                    compensation=step.compensation,
                    config=step.config
                ))

            if context:
                for key, value in context.items():
                    saga.set_context(key, value)

            self._sagas[saga.saga_id] = saga
            self._stats.total_sagas += 1

            return saga

    async def get_saga(self, saga_id: str) -> Optional[Saga]:
        """Get saga by ID."""
        async with self._lock:
            return self._sagas.get(saga_id)

    # -------------------------------------------------------------------------
    # SAGA EXECUTION
    # -------------------------------------------------------------------------

    async def execute(self, saga_id: str) -> Optional[SagaResult]:
        """Execute saga."""
        saga = await self.get_saga(saga_id)
        if not saga:
            return None

        async with self._lock:
            self._stats.active += 1

        try:
            result = await self._executor.execute(saga)

            async with self._lock:
                self._stats.active -= 1

                if result.status == SagaStatus.COMPLETED:
                    self._stats.completed += 1
                elif result.status == SagaStatus.COMPENSATED:
                    self._stats.compensated += 1
                else:
                    self._stats.failed += 1

                self._durations.append(result.duration_ms)
                self._update_average()

            return result

        except Exception:
            async with self._lock:
                self._stats.active -= 1
                self._stats.failed += 1
            raise

    async def execute_saga(
        self,
        saga: Saga
    ) -> SagaResult:
        """Execute saga directly."""
        async with self._lock:
            if saga.saga_id not in self._sagas:
                self._sagas[saga.saga_id] = saga
                self._stats.total_sagas += 1
            self._stats.active += 1

        try:
            result = await self._executor.execute(saga)

            async with self._lock:
                self._stats.active -= 1

                if result.status == SagaStatus.COMPLETED:
                    self._stats.completed += 1
                elif result.status == SagaStatus.COMPENSATED:
                    self._stats.compensated += 1
                else:
                    self._stats.failed += 1

                self._durations.append(result.duration_ms)
                self._update_average()

            return result

        except Exception:
            async with self._lock:
                self._stats.active -= 1
                self._stats.failed += 1
            raise

    # -------------------------------------------------------------------------
    # BUILDER PATTERN
    # -------------------------------------------------------------------------

    async def build(
        self,
        name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> 'SagaBuilder':
        """Create saga builder."""
        saga = await self.create(name=name, context=context)
        return SagaBuilder(self, saga)

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def list_sagas(
        self,
        status: Optional[SagaStatus] = None
    ) -> List[Saga]:
        """List sagas."""
        async with self._lock:
            sagas = list(self._sagas.values())

            if status:
                sagas = [s for s in sagas if s.status == status]

            return sagas

    async def get_saga_events(
        self,
        saga_id: str
    ) -> List[SagaEvent]:
        """Get saga events."""
        saga = await self.get_saga(saga_id)
        if saga:
            return saga.get_events()
        return []

    async def is_running(self, saga_id: str) -> bool:
        """Check if saga is running."""
        return self._executor.is_running(saga_id)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def _update_average(self) -> None:
        """Update average duration."""
        if self._durations:
            self._stats.average_duration_ms = (
                sum(self._durations) / len(self._durations)
            )

    async def stats(self) -> SagaStats:
        """Get saga stats."""
        async with self._lock:
            return copy.copy(self._stats)

    async def saga_count(self) -> int:
        """Get saga count."""
        async with self._lock:
            return len(self._sagas)

    async def active_count(self) -> int:
        """Get active saga count."""
        return self._executor.running_count()


# =============================================================================
# SAGA BUILDER
# =============================================================================

class SagaBuilder:
    """Fluent saga builder."""

    def __init__(self, manager: SagaManager, saga: Saga):
        self._manager = manager
        self._saga = saga

    def step(
        self,
        name: str,
        action: Callable[..., Awaitable[Any]],
        compensation: Optional[Callable[..., Awaitable[Any]]] = None,
        config: Optional[StepConfig] = None
    ) -> 'SagaBuilder':
        """Add step."""
        self._saga.step(
            name=name,
            action=action,
            compensation=compensation,
            config=config
        )
        return self

    def context(self, key: str, value: Any) -> 'SagaBuilder':
        """Set context value."""
        self._saga.set_context(key, value)
        return self

    def metadata(self, key: str, value: Any) -> 'SagaBuilder':
        """Set metadata."""
        self._saga.metadata[key] = value
        return self

    async def execute(self) -> SagaResult:
        """Execute the built saga."""
        return await self._manager.execute_saga(self._saga)

    def build(self) -> Saga:
        """Return the saga without executing."""
        return self._saga


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Saga Manager."""
    print("=" * 70)
    print("BAEL - SAGA MANAGER DEMO")
    print("Advanced Saga Pattern for AI Agents")
    print("=" * 70)
    print()

    manager = SagaManager(SagaConfig(
        timeout_seconds=60,
        max_retries=2
    ))

    # Tracking
    executed_steps: List[str] = []
    compensated_steps: List[str] = []

    # Step implementations
    async def create_order(ctx: Dict[str, Any]) -> Dict[str, Any]:
        executed_steps.append("create_order")
        return {"order_id": "ORD-123", "amount": ctx.get("amount", 100)}

    async def reserve_inventory(ctx: Dict[str, Any]) -> Dict[str, Any]:
        executed_steps.append("reserve_inventory")
        return {"reservation_id": "RES-456"}

    async def process_payment(ctx: Dict[str, Any]) -> Dict[str, Any]:
        executed_steps.append("process_payment")
        return {"payment_id": "PAY-789"}

    async def cancel_order(ctx: Dict[str, Any]) -> None:
        compensated_steps.append("cancel_order")

    async def release_inventory(ctx: Dict[str, Any]) -> None:
        compensated_steps.append("release_inventory")

    async def refund_payment(ctx: Dict[str, Any]) -> None:
        compensated_steps.append("refund_payment")

    # 1. Create Saga
    print("1. CREATE SAGA:")
    print("-" * 40)

    saga = await manager.create(
        name="order_saga",
        context={"amount": 250}
    )

    saga.step("create_order", create_order, cancel_order)
    saga.step("reserve_inventory", reserve_inventory, release_inventory)
    saga.step("process_payment", process_payment, refund_payment)

    print(f"   Saga ID: {saga.saga_id[:8]}...")
    print(f"   Steps: {len(saga.get_steps())}")
    print()

    # 2. Execute Saga
    print("2. EXECUTE SAGA (SUCCESS):")
    print("-" * 40)

    result = await manager.execute(saga.saga_id)

    print(f"   Status: {result.status.value}")
    print(f"   Steps completed: {result.steps_completed}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print(f"   Executed: {executed_steps}")
    print()

    # 3. Saga with Compensation
    print("3. SAGA WITH COMPENSATION:")
    print("-" * 40)

    executed_steps.clear()
    compensated_steps.clear()

    async def failing_step(ctx: Dict[str, Any]) -> None:
        executed_steps.append("failing_step")
        raise ValueError("Payment failed!")

    fail_saga = await manager.create(name="fail_saga")
    fail_saga.step("create_order", create_order, cancel_order)
    fail_saga.step("reserve_inventory", reserve_inventory, release_inventory)
    fail_saga.step("process_payment", failing_step, refund_payment)

    result = await manager.execute(fail_saga.saga_id)

    print(f"   Status: {result.status.value}")
    print(f"   Steps completed: {result.steps_completed}")
    print(f"   Steps compensated: {result.steps_compensated}")
    print(f"   Executed: {executed_steps}")
    print(f"   Compensated: {compensated_steps}")
    print()

    # 4. Builder Pattern
    print("4. BUILDER PATTERN:")
    print("-" * 40)

    executed_steps.clear()

    builder = await manager.build("builder_saga")
    result = await (
        builder
        .context("user_id", "user-1")
        .step("create_order", create_order, cancel_order)
        .step("reserve_inventory", reserve_inventory, release_inventory)
        .execute()
    )

    print(f"   Status: {result.status.value}")
    print(f"   Executed: {executed_steps}")
    print()

    # 5. Define Saga Template
    print("5. DEFINE SAGA TEMPLATE:")
    print("-" * 40)

    template = await manager.define("order_template")
    template.step("create_order", create_order, cancel_order)
    template.step("reserve_inventory", reserve_inventory, release_inventory)
    template.step("process_payment", process_payment, refund_payment)

    print(f"   Template: {template.name}")
    print(f"   Steps: {len(template.get_steps())}")
    print()

    # 6. Create from Template
    print("6. CREATE FROM TEMPLATE:")
    print("-" * 40)

    executed_steps.clear()

    instance = await manager.create_from_definition(
        "order_template",
        context={"amount": 500}
    )

    result = await manager.execute(instance.saga_id)

    print(f"   Status: {result.status.value}")
    print(f"   Executed: {executed_steps}")
    print()

    # 7. Get Saga Events
    print("7. GET SAGA EVENTS:")
    print("-" * 40)

    events = await manager.get_saga_events(saga.saga_id)

    print(f"   Event count: {len(events)}")
    for event in events[:3]:
        print(f"   - {event.event_type}: {event.step_id or 'saga'}")
    print()

    # 8. List Sagas
    print("8. LIST SAGAS:")
    print("-" * 40)

    all_sagas = await manager.list_sagas()
    completed = await manager.list_sagas(SagaStatus.COMPLETED)

    print(f"   Total sagas: {len(all_sagas)}")
    print(f"   Completed: {len(completed)}")
    print()

    # 9. Saga Stats
    print("9. SAGA STATS:")
    print("-" * 40)

    stats = await manager.stats()

    print(f"   Total: {stats.total_sagas}")
    print(f"   Completed: {stats.completed}")
    print(f"   Compensated: {stats.compensated}")
    print(f"   Failed: {stats.failed}")
    print(f"   Avg duration: {stats.average_duration_ms:.2f}ms")
    print()

    # 10. Get Saga
    print("10. GET SAGA:")
    print("-" * 40)

    retrieved = await manager.get_saga(saga.saga_id)

    print(f"   Found: {retrieved is not None}")
    print(f"   Name: {retrieved.name if retrieved else 'N/A'}")
    print(f"   Status: {retrieved.status.value if retrieved else 'N/A'}")
    print()

    # 11. Saga Context
    print("11. SAGA CONTEXT:")
    print("-" * 40)

    context = saga.get_full_context()

    print(f"   Context keys: {list(context.keys())}")
    print(f"   Amount: {context.get('amount')}")
    print()

    # 12. Step Results
    print("12. STEP RESULTS:")
    print("-" * 40)

    for step in saga.get_steps():
        result = step.to_result()
        print(f"   {step.name}: {result.status.value} ({result.duration_ms:.1f}ms)")
    print()

    # 13. Check Running
    print("13. CHECK RUNNING:")
    print("-" * 40)

    is_running = await manager.is_running(saga.saga_id)
    print(f"   Running: {is_running}")
    print()

    # 14. Saga Count
    print("14. SAGA COUNT:")
    print("-" * 40)

    count = await manager.saga_count()
    active = await manager.active_count()

    print(f"   Total: {count}")
    print(f"   Active: {active}")
    print()

    # 15. Get Definition
    print("15. GET DEFINITION:")
    print("-" * 40)

    definition = await manager.get_definition("order_template")

    print(f"   Found: {definition is not None}")
    print(f"   Steps: {len(definition.get_steps()) if definition else 0}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Saga Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
