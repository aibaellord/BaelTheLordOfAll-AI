"""
BAEL Saga Engine Implementation
================================

Saga pattern for managing distributed transactions.

"Ba'el coordinates the cosmic dance of distributed transactions." — Ba'el
"""

import asyncio
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("BAEL.Saga")

T = TypeVar('T')


# ============================================================================
# ENUMS
# ============================================================================

class SagaState(Enum):
    """Saga execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    TIMEOUT = "timeout"


class StepState(Enum):
    """Individual step states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    SKIPPED = "skipped"


class CompensationStrategy(Enum):
    """Compensation strategies."""
    BACKWARD = "backward"      # Compensate in reverse order
    FORWARD = "forward"        # Compensate in forward order
    PARALLEL = "parallel"      # Compensate all at once
    CUSTOM = "custom"          # Custom order


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SagaStep:
    """
    Definition of a saga step.

    Each step has an action and optional compensation.
    """
    name: str

    # Actions
    action: Callable[..., Any] = None  # Main action
    compensation: Optional[Callable[..., Any]] = None  # Undo action

    # Configuration
    timeout_seconds: float = 30.0
    retries: int = 3
    retry_delay_seconds: float = 1.0

    # Dependencies
    depends_on: List[str] = field(default_factory=list)

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Result of step execution."""
    step_name: str
    state: StepState
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    attempts: int = 1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SagaDefinition:
    """
    Definition of a complete saga.
    """
    name: str
    steps: List[SagaStep] = field(default_factory=list)

    # Configuration
    compensation_strategy: CompensationStrategy = CompensationStrategy.BACKWARD
    timeout_seconds: float = 300.0  # 5 minutes

    # Metadata
    description: str = ""
    version: str = "1.0.0"

    def add_step(
        self,
        name: str,
        action: Callable,
        compensation: Optional[Callable] = None,
        **kwargs
    ) -> 'SagaDefinition':
        """Add a step to the saga."""
        step = SagaStep(
            name=name,
            action=action,
            compensation=compensation,
            **kwargs
        )
        self.steps.append(step)
        return self

    def get_step(self, name: str) -> Optional[SagaStep]:
        """Get step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None


@dataclass
class SagaExecution:
    """
    Execution state of a saga instance.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    saga_name: str = ""

    # State
    state: SagaState = SagaState.PENDING
    current_step: int = 0

    # Results
    step_results: List[StepResult] = field(default_factory=list)

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error tracking
    last_error: Optional[str] = None
    failed_step: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        """Get total duration in milliseconds."""
        if not self.started_at:
            return 0.0

        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds() * 1000

    @property
    def success(self) -> bool:
        """Check if saga completed successfully."""
        return self.state == SagaState.COMPLETED

    def get_result(self, step_name: str) -> Optional[StepResult]:
        """Get result for a specific step."""
        for result in self.step_results:
            if result.step_name == step_name:
                return result
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'saga_name': self.saga_name,
            'state': self.state.value,
            'current_step': self.current_step,
            'step_results': [
                {
                    'name': r.step_name,
                    'state': r.state.value,
                    'error': r.error,
                    'duration_ms': r.duration_ms
                }
                for r in self.step_results
            ],
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_ms': self.duration_ms,
            'last_error': self.last_error
        }


# ============================================================================
# SAGA ORCHESTRATOR
# ============================================================================

class SagaOrchestrator:
    """
    Orchestrator for saga execution.

    Features:
    - Step-by-step execution
    - Automatic compensation on failure
    - Retry support
    - Timeout handling
    - Async execution

    "Ba'el guides sagas to their destined conclusion." — Ba'el
    """

    def __init__(self):
        # Registered sagas
        self._sagas: Dict[str, SagaDefinition] = {}

        # Active executions
        self._executions: Dict[str, SagaExecution] = {}

        # Execution history
        self._history: List[SagaExecution] = []

        self._lock = threading.RLock()

        logger.info("Saga Orchestrator initialized")

    # ========================================================================
    # SAGA REGISTRATION
    # ========================================================================

    def register(self, saga: SagaDefinition) -> None:
        """Register a saga definition."""
        with self._lock:
            self._sagas[saga.name] = saga

        logger.debug(f"Registered saga: {saga.name}")

    def define(self, name: str, **kwargs) -> SagaDefinition:
        """Create and register a new saga."""
        saga = SagaDefinition(name=name, **kwargs)
        self.register(saga)
        return saga

    def get_saga(self, name: str) -> Optional[SagaDefinition]:
        """Get saga definition by name."""
        return self._sagas.get(name)

    # ========================================================================
    # EXECUTION
    # ========================================================================

    async def execute(
        self,
        saga_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SagaExecution:
        """
        Execute a saga.

        Args:
            saga_name: Name of registered saga
            context: Initial context data

        Returns:
            Saga execution result
        """
        saga = self._sagas.get(saga_name)
        if not saga:
            raise KeyError(f"Saga not found: {saga_name}")

        # Create execution
        execution = SagaExecution(
            saga_name=saga_name,
            context=context or {},
            started_at=datetime.now()
        )

        with self._lock:
            self._executions[execution.id] = execution

        logger.info(f"Starting saga: {saga_name} (ID: {execution.id})")

        try:
            # Execute steps
            execution.state = SagaState.RUNNING

            for i, step in enumerate(saga.steps):
                execution.current_step = i

                # Check timeout
                if self._check_timeout(execution, saga):
                    execution.state = SagaState.TIMEOUT
                    await self._compensate(saga, execution)
                    break

                # Execute step
                result = await self._execute_step(step, execution)
                execution.step_results.append(result)

                # Check for failure
                if result.state == StepState.FAILED:
                    execution.state = SagaState.COMPENSATING
                    execution.last_error = result.error
                    execution.failed_step = step.name

                    await self._compensate(saga, execution)
                    break

            # Mark complete if no failure
            if execution.state == SagaState.RUNNING:
                execution.state = SagaState.COMPLETED

        except Exception as e:
            logger.error(f"Saga execution error: {e}")
            execution.state = SagaState.FAILED
            execution.last_error = str(e)

            # Try to compensate
            try:
                await self._compensate(saga, execution)
            except Exception as ce:
                logger.error(f"Compensation error: {ce}")

        finally:
            execution.completed_at = datetime.now()

            with self._lock:
                del self._executions[execution.id]
                self._history.append(execution)

        logger.info(
            f"Saga {saga_name} completed: {execution.state.value} "
            f"({execution.duration_ms:.2f}ms)"
        )

        return execution

    async def _execute_step(
        self,
        step: SagaStep,
        execution: SagaExecution
    ) -> StepResult:
        """Execute a single saga step."""
        start_time = datetime.now()
        attempts = 0
        last_error = None

        while attempts < step.retries:
            attempts += 1

            try:
                logger.debug(f"Executing step: {step.name} (attempt {attempts})")

                # Execute with timeout
                if asyncio.iscoroutinefunction(step.action):
                    result_data = await asyncio.wait_for(
                        step.action(execution.context),
                        timeout=step.timeout_seconds
                    )
                else:
                    loop = asyncio.get_event_loop()
                    result_data = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: step.action(execution.context)
                        ),
                        timeout=step.timeout_seconds
                    )

                # Update context with result
                if isinstance(result_data, dict):
                    execution.context.update(result_data)

                duration = (datetime.now() - start_time).total_seconds() * 1000

                return StepResult(
                    step_name=step.name,
                    state=StepState.COMPLETED,
                    data=result_data,
                    duration_ms=duration,
                    attempts=attempts
                )

            except asyncio.TimeoutError:
                last_error = f"Step timed out after {step.timeout_seconds}s"
                logger.warning(f"Step {step.name} timeout")

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Step {step.name} failed (attempt {attempts}): {e}"
                )

                if attempts < step.retries:
                    await asyncio.sleep(step.retry_delay_seconds)

        duration = (datetime.now() - start_time).total_seconds() * 1000

        return StepResult(
            step_name=step.name,
            state=StepState.FAILED,
            error=last_error,
            duration_ms=duration,
            attempts=attempts
        )

    async def _compensate(
        self,
        saga: SagaDefinition,
        execution: SagaExecution
    ) -> None:
        """Run compensation for failed saga."""
        logger.info(f"Starting compensation for saga {saga.name}")

        execution.state = SagaState.COMPENSATING

        # Get completed steps that need compensation
        completed_steps = [
            r for r in execution.step_results
            if r.state == StepState.COMPLETED
        ]

        if saga.compensation_strategy == CompensationStrategy.BACKWARD:
            # Compensate in reverse order
            steps_to_compensate = list(reversed(completed_steps))
        elif saga.compensation_strategy == CompensationStrategy.FORWARD:
            steps_to_compensate = completed_steps
        elif saga.compensation_strategy == CompensationStrategy.PARALLEL:
            # Will handle parallel execution
            steps_to_compensate = completed_steps
        else:
            steps_to_compensate = completed_steps

        if saga.compensation_strategy == CompensationStrategy.PARALLEL:
            # Parallel compensation
            tasks = []
            for result in steps_to_compensate:
                step = saga.get_step(result.step_name)
                if step and step.compensation:
                    tasks.append(
                        self._compensate_step(step, execution)
                    )

            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Sequential compensation
            for result in steps_to_compensate:
                step = saga.get_step(result.step_name)
                if step and step.compensation:
                    await self._compensate_step(step, execution)

        execution.state = SagaState.COMPENSATED
        logger.info(f"Compensation complete for saga {saga.name}")

    async def _compensate_step(
        self,
        step: SagaStep,
        execution: SagaExecution
    ) -> None:
        """Compensate a single step."""
        try:
            logger.debug(f"Compensating step: {step.name}")

            if asyncio.iscoroutinefunction(step.compensation):
                await step.compensation(execution.context)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: step.compensation(execution.context)
                )

            # Update step result
            for result in execution.step_results:
                if result.step_name == step.name:
                    result.state = StepState.COMPENSATED
                    break

        except Exception as e:
            logger.error(f"Failed to compensate step {step.name}: {e}")

    def _check_timeout(
        self,
        execution: SagaExecution,
        saga: SagaDefinition
    ) -> bool:
        """Check if saga has timed out."""
        if not execution.started_at:
            return False

        elapsed = (datetime.now() - execution.started_at).total_seconds()
        return elapsed > saga.timeout_seconds

    # ========================================================================
    # SYNC EXECUTION
    # ========================================================================

    def execute_sync(
        self,
        saga_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SagaExecution:
        """Execute saga synchronously."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.execute(saga_name, context)
            )
        finally:
            loop.close()

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_execution(self, execution_id: str) -> Optional[SagaExecution]:
        """Get active execution by ID."""
        return self._executions.get(execution_id)

    def get_history(
        self,
        saga_name: Optional[str] = None,
        limit: int = 100
    ) -> List[SagaExecution]:
        """Get execution history."""
        history = self._history

        if saga_name:
            history = [e for e in history if e.saga_name == saga_name]

        return history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        with self._lock:
            return {
                'registered_sagas': len(self._sagas),
                'active_executions': len(self._executions),
                'history_size': len(self._history),
                'sagas': list(self._sagas.keys())
            }


# ============================================================================
# CONVENIENCE
# ============================================================================

saga_orchestrator = SagaOrchestrator()
