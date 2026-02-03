#!/usr/bin/env python3
"""
BAEL - Saga Orchestrator
Comprehensive distributed transaction management with saga pattern.

Features:
- Saga orchestration
- Compensating transactions
- Step-by-step execution
- Rollback handling
- Saga state management
- Concurrent saga execution
- Saga persistence
- Timeout handling
- Retry policies
- Event-driven sagas
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SagaStatus(Enum):
    """Saga execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    TIMEOUT = "timeout"


class StepStatus(Enum):
    """Step execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    SKIPPED = "skipped"


class CompensationPolicy(Enum):
    """Compensation policy."""
    BACKWARD = "backward"
    FORWARD = "forward"
    PARALLEL = "parallel"


class RetryPolicy(Enum):
    """Retry policy."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SagaContext:
    """Saga execution context."""
    saga_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set_result(self, step_name: str, result: Any) -> None:
        self.results[step_name] = result

    def get_result(self, step_name: str) -> Any:
        return self.results.get(step_name)

    def add_error(self, error: str) -> None:
        self.errors.append(error)


@dataclass
class StepResult:
    """Step execution result."""
    success: bool
    data: Any = None
    error: str = ""
    duration: float = 0.0


@dataclass
class SagaStep:
    """Saga step definition."""
    name: str
    execute: Callable[[SagaContext], Awaitable[StepResult]]
    compensate: Callable[[SagaContext], Awaitable[None]] = None
    timeout: float = 30.0
    retries: int = 0
    retry_delay: float = 1.0
    retry_policy: RetryPolicy = RetryPolicy.NONE
    condition: Callable[[SagaContext], bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepState:
    """Step execution state."""
    step: SagaStep
    status: StepStatus = StepStatus.PENDING
    result: Optional[StepResult] = None
    attempts: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    compensated_at: float = 0.0
    error: str = ""


@dataclass
class SagaState:
    """Saga execution state."""
    saga_id: str
    name: str
    status: SagaStatus = SagaStatus.PENDING
    current_step: int = 0
    steps: List[StepState] = field(default_factory=list)
    context: SagaContext = field(default_factory=SagaContext)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "saga_id": self.saga_id,
            "name": self.name,
            "status": self.status.value,
            "current_step": self.current_step,
            "steps": [
                {
                    "name": s.step.name,
                    "status": s.status.value,
                    "attempts": s.attempts,
                    "error": s.error
                }
                for s in self.steps
            ],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


@dataclass
class SagaStats:
    """Saga orchestrator statistics."""
    total_sagas: int = 0
    completed: int = 0
    failed: int = 0
    compensated: int = 0
    running: int = 0
    avg_duration: float = 0.0


# =============================================================================
# SAGA DEFINITION
# =============================================================================

class SagaDefinition:
    """Saga definition with steps."""

    def __init__(self, name: str):
        self.name = name
        self.steps: List[SagaStep] = []
        self.on_complete: Optional[Callable[[SagaContext], Awaitable[None]]] = None
        self.on_error: Optional[Callable[[SagaContext, str], Awaitable[None]]] = None
        self.compensation_policy = CompensationPolicy.BACKWARD
        self.timeout: float = 300.0

    def add_step(
        self,
        name: str,
        execute: Callable[[SagaContext], Awaitable[StepResult]],
        compensate: Callable[[SagaContext], Awaitable[None]] = None,
        timeout: float = 30.0,
        retries: int = 0,
        retry_delay: float = 1.0,
        retry_policy: RetryPolicy = RetryPolicy.NONE,
        condition: Callable[[SagaContext], bool] = None
    ) -> 'SagaDefinition':
        """Add a step to the saga."""
        step = SagaStep(
            name=name,
            execute=execute,
            compensate=compensate,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            retry_policy=retry_policy,
            condition=condition
        )

        self.steps.append(step)
        return self

    def with_timeout(self, timeout: float) -> 'SagaDefinition':
        """Set saga timeout."""
        self.timeout = timeout
        return self

    def with_compensation_policy(
        self,
        policy: CompensationPolicy
    ) -> 'SagaDefinition':
        """Set compensation policy."""
        self.compensation_policy = policy
        return self

    def on_completed(
        self,
        handler: Callable[[SagaContext], Awaitable[None]]
    ) -> 'SagaDefinition':
        """Set completion handler."""
        self.on_complete = handler
        return self

    def on_failed(
        self,
        handler: Callable[[SagaContext, str], Awaitable[None]]
    ) -> 'SagaDefinition':
        """Set error handler."""
        self.on_error = handler
        return self


# =============================================================================
# SAGA BUILDER
# =============================================================================

class SagaBuilder:
    """Fluent saga builder."""

    def __init__(self, name: str):
        self.definition = SagaDefinition(name)

    def step(
        self,
        name: str,
        execute: Callable[[SagaContext], Awaitable[StepResult]],
        compensate: Callable[[SagaContext], Awaitable[None]] = None
    ) -> 'SagaBuilder':
        """Add a step."""
        self.definition.add_step(name, execute, compensate)
        return self

    def step_with_retry(
        self,
        name: str,
        execute: Callable[[SagaContext], Awaitable[StepResult]],
        compensate: Callable[[SagaContext], Awaitable[None]] = None,
        retries: int = 3,
        retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL
    ) -> 'SagaBuilder':
        """Add a step with retry."""
        self.definition.add_step(
            name,
            execute,
            compensate,
            retries=retries,
            retry_policy=retry_policy
        )
        return self

    def conditional_step(
        self,
        name: str,
        condition: Callable[[SagaContext], bool],
        execute: Callable[[SagaContext], Awaitable[StepResult]],
        compensate: Callable[[SagaContext], Awaitable[None]] = None
    ) -> 'SagaBuilder':
        """Add a conditional step."""
        self.definition.add_step(
            name,
            execute,
            compensate,
            condition=condition
        )
        return self

    def timeout(self, seconds: float) -> 'SagaBuilder':
        """Set timeout."""
        self.definition.with_timeout(seconds)
        return self

    def on_complete(
        self,
        handler: Callable[[SagaContext], Awaitable[None]]
    ) -> 'SagaBuilder':
        """Set completion handler."""
        self.definition.on_completed(handler)
        return self

    def on_error(
        self,
        handler: Callable[[SagaContext, str], Awaitable[None]]
    ) -> 'SagaBuilder':
        """Set error handler."""
        self.definition.on_failed(handler)
        return self

    def build(self) -> SagaDefinition:
        """Build the saga definition."""
        return self.definition


# =============================================================================
# SAGA EXECUTOR
# =============================================================================

class SagaExecutor:
    """Saga executor."""

    def __init__(self, definition: SagaDefinition):
        self.definition = definition

    async def execute(
        self,
        context: SagaContext = None
    ) -> SagaState:
        """Execute the saga."""
        context = context or SagaContext()

        state = SagaState(
            saga_id=context.saga_id,
            name=self.definition.name,
            context=context
        )

        # Initialize step states
        for step in self.definition.steps:
            state.steps.append(StepState(step=step))

        state.status = SagaStatus.RUNNING
        state.started_at = time.time()

        try:
            # Execute steps
            for i, step_state in enumerate(state.steps):
                state.current_step = i

                # Check condition
                if step_state.step.condition:
                    if not step_state.step.condition(context):
                        step_state.status = StepStatus.SKIPPED
                        continue

                # Execute step
                result = await self._execute_step(step_state, context)

                if not result.success:
                    state.error = result.error
                    state.status = SagaStatus.COMPENSATING

                    # Compensate completed steps
                    await self._compensate(state, i - 1)

                    state.status = SagaStatus.COMPENSATED
                    state.completed_at = time.time()

                    if self.definition.on_error:
                        await self.definition.on_error(context, result.error)

                    return state

            # All steps completed
            state.status = SagaStatus.COMPLETED
            state.completed_at = time.time()

            if self.definition.on_complete:
                await self.definition.on_complete(context)

        except asyncio.TimeoutError:
            state.status = SagaStatus.TIMEOUT
            state.error = "Saga timeout"
            await self._compensate(state, state.current_step - 1)

        except Exception as e:
            state.status = SagaStatus.FAILED
            state.error = str(e)
            await self._compensate(state, state.current_step - 1)

        return state

    async def _execute_step(
        self,
        step_state: StepState,
        context: SagaContext
    ) -> StepResult:
        """Execute a single step."""
        step = step_state.step
        step_state.status = StepStatus.EXECUTING
        step_state.started_at = time.time()

        attempts = 0
        max_attempts = step.retries + 1

        while attempts < max_attempts:
            attempts += 1
            step_state.attempts = attempts

            try:
                result = await asyncio.wait_for(
                    step.execute(context),
                    timeout=step.timeout
                )

                step_state.result = result
                step_state.completed_at = time.time()

                if result.success:
                    step_state.status = StepStatus.COMPLETED
                    context.set_result(step.name, result.data)
                    return result

                step_state.error = result.error

            except asyncio.TimeoutError:
                step_state.error = f"Step timeout after {step.timeout}s"
                result = StepResult(
                    success=False,
                    error=step_state.error
                )

            except Exception as e:
                step_state.error = str(e)
                result = StepResult(
                    success=False,
                    error=str(e)
                )

            # Retry logic
            if attempts < max_attempts:
                delay = self._calculate_retry_delay(
                    step.retry_policy,
                    step.retry_delay,
                    attempts
                )
                await asyncio.sleep(delay)

        step_state.status = StepStatus.FAILED
        return result

    def _calculate_retry_delay(
        self,
        policy: RetryPolicy,
        base_delay: float,
        attempt: int
    ) -> float:
        """Calculate retry delay."""
        if policy == RetryPolicy.FIXED:
            return base_delay

        if policy == RetryPolicy.EXPONENTIAL:
            return base_delay * (2 ** (attempt - 1))

        return 0.0

    async def _compensate(
        self,
        state: SagaState,
        from_step: int
    ) -> None:
        """Compensate completed steps."""
        policy = self.definition.compensation_policy

        if policy == CompensationPolicy.BACKWARD:
            # Compensate in reverse order
            for i in range(from_step, -1, -1):
                step_state = state.steps[i]
                await self._compensate_step(step_state, state.context)

        elif policy == CompensationPolicy.PARALLEL:
            # Compensate all at once
            tasks = []
            for i in range(from_step, -1, -1):
                step_state = state.steps[i]
                tasks.append(
                    self._compensate_step(step_state, state.context)
                )
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _compensate_step(
        self,
        step_state: StepState,
        context: SagaContext
    ) -> None:
        """Compensate a single step."""
        if step_state.status == StepStatus.SKIPPED:
            return

        if step_state.step.compensate is None:
            return

        step_state.status = StepStatus.COMPENSATING

        try:
            await step_state.step.compensate(context)
            step_state.status = StepStatus.COMPENSATED
            step_state.compensated_at = time.time()
        except Exception as e:
            logger.exception(f"Compensation failed: {e}")
            step_state.error = f"Compensation failed: {e}"


# =============================================================================
# SAGA STORE
# =============================================================================

class SagaStore(ABC):
    """Abstract saga state store."""

    @abstractmethod
    async def save(self, state: SagaState) -> None:
        """Save saga state."""
        pass

    @abstractmethod
    async def get(self, saga_id: str) -> Optional[SagaState]:
        """Get saga state."""
        pass

    @abstractmethod
    async def list_by_status(
        self,
        status: SagaStatus
    ) -> List[SagaState]:
        """List sagas by status."""
        pass


class InMemorySagaStore(SagaStore):
    """In-memory saga store."""

    def __init__(self):
        self.sagas: Dict[str, SagaState] = {}

    async def save(self, state: SagaState) -> None:
        self.sagas[state.saga_id] = state

    async def get(self, saga_id: str) -> Optional[SagaState]:
        return self.sagas.get(saga_id)

    async def list_by_status(
        self,
        status: SagaStatus
    ) -> List[SagaState]:
        return [
            s for s in self.sagas.values()
            if s.status == status
        ]


# =============================================================================
# SAGA ORCHESTRATOR
# =============================================================================

class SagaOrchestrator:
    """
    Comprehensive Saga Orchestrator for BAEL.
    """

    def __init__(
        self,
        store: SagaStore = None
    ):
        self.store = store or InMemorySagaStore()
        self.definitions: Dict[str, SagaDefinition] = {}
        self.running: Dict[str, asyncio.Task] = {}
        self.stats = SagaStats()
        self._durations: List[float] = []

    def register(
        self,
        definition: SagaDefinition
    ) -> None:
        """Register a saga definition."""
        self.definitions[definition.name] = definition

    def unregister(self, name: str) -> bool:
        """Unregister a saga definition."""
        if name in self.definitions:
            del self.definitions[name]
            return True
        return False

    async def start(
        self,
        name: str,
        initial_data: Dict[str, Any] = None
    ) -> SagaState:
        """Start a new saga execution."""
        definition = self.definitions.get(name)

        if not definition:
            raise ValueError(f"Saga '{name}' not registered")

        context = SagaContext(data=initial_data or {})
        executor = SagaExecutor(definition)

        self.stats.total_sagas += 1
        self.stats.running += 1

        state = await executor.execute(context)

        self.stats.running -= 1

        if state.status == SagaStatus.COMPLETED:
            self.stats.completed += 1
        elif state.status == SagaStatus.COMPENSATED:
            self.stats.compensated += 1
        else:
            self.stats.failed += 1

        # Track duration
        duration = state.completed_at - state.started_at
        self._durations.append(duration)
        self.stats.avg_duration = sum(self._durations) / len(self._durations)

        # Persist state
        await self.store.save(state)

        return state

    async def start_async(
        self,
        name: str,
        initial_data: Dict[str, Any] = None
    ) -> str:
        """Start saga asynchronously."""
        context = SagaContext(data=initial_data or {})
        saga_id = context.saga_id

        task = asyncio.create_task(self.start(name, initial_data))
        self.running[saga_id] = task

        return saga_id

    async def get_status(self, saga_id: str) -> Optional[SagaState]:
        """Get saga status."""
        return await self.store.get(saga_id)

    async def list_running(self) -> List[SagaState]:
        """List running sagas."""
        return await self.store.list_by_status(SagaStatus.RUNNING)

    async def list_failed(self) -> List[SagaState]:
        """List failed sagas."""
        return await self.store.list_by_status(SagaStatus.FAILED)

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "total_sagas": self.stats.total_sagas,
            "completed": self.stats.completed,
            "failed": self.stats.failed,
            "compensated": self.stats.compensated,
            "running": self.stats.running,
            "avg_duration": self.stats.avg_duration,
            "registered_sagas": list(self.definitions.keys())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Saga Orchestrator System."""
    print("=" * 70)
    print("BAEL - SAGA ORCHESTRATOR SYSTEM DEMO")
    print("Comprehensive Distributed Transaction Management")
    print("=" * 70)
    print()

    orchestrator = SagaOrchestrator()

    # 1. Define Order Saga
    print("1. DEFINE ORDER SAGA:")
    print("-" * 40)

    async def create_order(ctx: SagaContext) -> StepResult:
        order_id = f"ORD-{uuid.uuid4().hex[:8]}"
        ctx.set("order_id", order_id)
        print(f"      [Step] Created order: {order_id}")
        return StepResult(success=True, data={"order_id": order_id})

    async def compensate_order(ctx: SagaContext) -> None:
        order_id = ctx.get("order_id")
        print(f"      [Compensate] Cancelled order: {order_id}")

    async def reserve_inventory(ctx: SagaContext) -> StepResult:
        order_id = ctx.get("order_id")
        print(f"      [Step] Reserved inventory for: {order_id}")
        return StepResult(success=True, data={"reserved": True})

    async def compensate_inventory(ctx: SagaContext) -> None:
        order_id = ctx.get("order_id")
        print(f"      [Compensate] Released inventory for: {order_id}")

    async def process_payment(ctx: SagaContext) -> StepResult:
        amount = ctx.get("amount", 100)
        print(f"      [Step] Processed payment: ${amount}")
        return StepResult(success=True, data={"payment_id": "PAY-123"})

    async def compensate_payment(ctx: SagaContext) -> None:
        print(f"      [Compensate] Refunded payment")

    async def ship_order(ctx: SagaContext) -> StepResult:
        order_id = ctx.get("order_id")
        print(f"      [Step] Shipped order: {order_id}")
        return StepResult(success=True, data={"tracking": "TRK-456"})

    order_saga = (
        SagaBuilder("OrderSaga")
        .step("create_order", create_order, compensate_order)
        .step("reserve_inventory", reserve_inventory, compensate_inventory)
        .step("process_payment", process_payment, compensate_payment)
        .step("ship_order", ship_order)
        .timeout(60.0)
        .build()
    )

    orchestrator.register(order_saga)

    print(f"   Saga: {order_saga.name}")
    print(f"   Steps: {len(order_saga.steps)}")
    print()

    # 2. Execute Successful Saga
    print("2. EXECUTE SUCCESSFUL SAGA:")
    print("-" * 40)

    state = await orchestrator.start(
        "OrderSaga",
        {"amount": 150, "product": "Widget"}
    )

    print(f"\n   Status: {state.status.value}")
    print(f"   Duration: {(state.completed_at - state.started_at)*1000:.2f}ms")
    print()

    # 3. Define Failing Saga
    print("3. DEFINE FAILING SAGA:")
    print("-" * 40)

    async def failing_step(ctx: SagaContext) -> StepResult:
        print(f"      [Step] This step will fail...")
        return StepResult(success=False, error="Payment declined")

    failing_saga = (
        SagaBuilder("FailingSaga")
        .step("create_order", create_order, compensate_order)
        .step("reserve_inventory", reserve_inventory, compensate_inventory)
        .step("process_payment", failing_step, compensate_payment)
        .step("ship_order", ship_order)
        .build()
    )

    orchestrator.register(failing_saga)
    print(f"   Saga: {failing_saga.name}")
    print()

    # 4. Execute Failing Saga
    print("4. EXECUTE FAILING SAGA (with compensation):")
    print("-" * 40)

    state = await orchestrator.start(
        "FailingSaga",
        {"amount": 50}
    )

    print(f"\n   Status: {state.status.value}")
    print(f"   Error: {state.error}")
    print(f"   Steps compensated:")

    for step_state in state.steps:
        if step_state.status == StepStatus.COMPENSATED:
            print(f"      - {step_state.step.name}")
    print()

    # 5. Saga with Retry
    print("5. SAGA WITH RETRY:")
    print("-" * 40)

    attempt_count = 0

    async def flaky_step(ctx: SagaContext) -> StepResult:
        nonlocal attempt_count
        attempt_count += 1
        print(f"      [Step] Attempt {attempt_count}")

        if attempt_count < 3:
            return StepResult(success=False, error="Temporary failure")

        return StepResult(success=True, data={"attempts": attempt_count})

    retry_saga = (
        SagaBuilder("RetrySaga")
        .step_with_retry(
            "flaky_step",
            flaky_step,
            retries=3,
            retry_policy=RetryPolicy.FIXED
        )
        .build()
    )

    orchestrator.register(retry_saga)

    state = await orchestrator.start("RetrySaga")

    print(f"\n   Status: {state.status.value}")
    print(f"   Total attempts: {attempt_count}")
    print()

    # 6. Conditional Steps
    print("6. CONDITIONAL STEPS:")
    print("-" * 40)

    async def premium_step(ctx: SagaContext) -> StepResult:
        print(f"      [Step] Premium processing applied!")
        return StepResult(success=True)

    async def standard_step(ctx: SagaContext) -> StepResult:
        print(f"      [Step] Standard processing")
        return StepResult(success=True)

    conditional_saga = (
        SagaBuilder("ConditionalSaga")
        .step("standard", standard_step)
        .conditional_step(
            "premium",
            lambda ctx: ctx.get("is_premium", False),
            premium_step
        )
        .build()
    )

    orchestrator.register(conditional_saga)

    print("   Regular customer:")
    await orchestrator.start("ConditionalSaga", {"is_premium": False})

    print("\n   Premium customer:")
    await orchestrator.start("ConditionalSaga", {"is_premium": True})
    print()

    # 7. Saga with Handlers
    print("7. SAGA WITH HANDLERS:")
    print("-" * 40)

    async def on_success(ctx: SagaContext) -> None:
        print(f"      [Complete] Order {ctx.get('order_id')} completed!")

    async def on_failure(ctx: SagaContext, error: str) -> None:
        print(f"      [Failed] Error: {error}")

    handler_saga = (
        SagaBuilder("HandlerSaga")
        .step("create_order", create_order, compensate_order)
        .step("ship_order", ship_order)
        .on_complete(on_success)
        .on_error(on_failure)
        .build()
    )

    orchestrator.register(handler_saga)

    await orchestrator.start("HandlerSaga")
    print()

    # 8. Get Saga Status
    print("8. GET SAGA STATUS:")
    print("-" * 40)

    state = await orchestrator.start(
        "OrderSaga",
        {"amount": 200}
    )

    saga_status = await orchestrator.get_status(state.saga_id)

    print(f"   Saga ID: {saga_status.saga_id[:8]}...")
    print(f"   Name: {saga_status.name}")
    print(f"   Status: {saga_status.status.value}")
    print(f"   Steps:")

    for step_state in saga_status.steps:
        print(f"      - {step_state.step.name}: {step_state.status.value}")
    print()

    # 9. Saga State Serialization
    print("9. SAGA STATE SERIALIZATION:")
    print("-" * 40)

    state_dict = state.to_dict()

    print(f"   Serialized fields: {len(state_dict)}")
    print(f"   Status: {state_dict['status']}")
    print(f"   Steps: {len(state_dict['steps'])}")
    print()

    # 10. Orchestrator Statistics
    print("10. ORCHESTRATOR STATISTICS:")
    print("-" * 40)

    stats = orchestrator.get_stats()

    print(f"   Total sagas: {stats['total_sagas']}")
    print(f"   Completed: {stats['completed']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Compensated: {stats['compensated']}")
    print(f"   Avg duration: {stats['avg_duration']*1000:.2f}ms")
    print(f"   Registered: {stats['registered_sagas']}")
    print()

    # 11. Complex Multi-Step Saga
    print("11. COMPLEX MULTI-STEP SAGA:")
    print("-" * 40)

    async def validate_order(ctx: SagaContext) -> StepResult:
        print(f"      [Step] Validating order...")
        return StepResult(success=True)

    async def check_fraud(ctx: SagaContext) -> StepResult:
        print(f"      [Step] Checking fraud...")
        return StepResult(success=True)

    async def notify_customer(ctx: SagaContext) -> StepResult:
        print(f"      [Step] Notifying customer...")
        return StepResult(success=True)

    async def update_analytics(ctx: SagaContext) -> StepResult:
        print(f"      [Step] Updating analytics...")
        return StepResult(success=True)

    complex_saga = (
        SagaBuilder("ComplexOrderSaga")
        .step("validate", validate_order)
        .step("fraud_check", check_fraud)
        .step("create_order", create_order, compensate_order)
        .step("reserve_inventory", reserve_inventory, compensate_inventory)
        .step("process_payment", process_payment, compensate_payment)
        .step("ship_order", ship_order)
        .step("notify", notify_customer)
        .step("analytics", update_analytics)
        .timeout(120.0)
        .build()
    )

    orchestrator.register(complex_saga)

    state = await orchestrator.start(
        "ComplexOrderSaga",
        {"amount": 500, "customer": "Alice"}
    )

    print(f"\n   Status: {state.status.value}")
    print(f"   Steps completed: {sum(1 for s in state.steps if s.status == StepStatus.COMPLETED)}")
    print()

    # 12. Summary
    print("12. FINAL SUMMARY:")
    print("-" * 40)

    stats = orchestrator.get_stats()

    print(f"   Total sagas executed: {stats['total_sagas']}")
    print(f"   Success rate: {(stats['completed']/stats['total_sagas'])*100:.1f}%")
    print(f"   Compensation rate: {(stats['compensated']/stats['total_sagas'])*100:.1f}%")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Saga Orchestrator System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
