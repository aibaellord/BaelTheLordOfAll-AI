"""
BAEL Mission Executor
======================

Autonomous mission execution engine.
Executes planned missions with full autonomy.

Features:
- Task orchestration
- Parallel execution
- Error recovery
- State management
- Progress reporting
- Resource management
"""

import asyncio
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """Execution state."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    COMPLETING = "completing"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass
class ExecutorConfig:
    """Executor configuration."""
    # Parallelism
    max_parallel_tasks: int = 5

    # Retry policy
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    retry_backoff_multiplier: float = 2.0

    # Timeouts
    task_timeout_seconds: float = 300.0
    mission_timeout_seconds: Optional[float] = None

    # Checkpointing
    checkpoint_interval_seconds: float = 60.0

    # Error handling
    fail_fast: bool = False
    continue_on_task_failure: bool = True

    # Resource limits
    max_api_calls_per_minute: int = 100
    max_concurrent_api_calls: int = 10


@dataclass
class ExecutionContext:
    """Context for task execution."""
    mission_id: str
    task_id: str

    # State
    attempt: int = 1

    # Inputs from dependencies
    inputs: Dict[str, Any] = field(default_factory=dict)

    # Outputs to be passed to dependents
    outputs: Dict[str, Any] = field(default_factory=dict)

    # Shared context across tasks
    shared: Dict[str, Any] = field(default_factory=dict)

    # Tools and capabilities
    tools: Dict[str, Callable] = field(default_factory=dict)

    # Timing
    started_at: Optional[datetime] = None
    timeout_at: Optional[datetime] = None


@dataclass
class ExecutionResult:
    """Result of task/mission execution."""
    success: bool

    # Output
    data: Any = None
    outputs: Dict[str, Any] = field(default_factory=dict)

    # Errors
    error: Optional[str] = None
    error_trace: Optional[str] = None

    # Timing
    duration: timedelta = field(default_factory=timedelta)

    # Stats
    tasks_completed: int = 0
    tasks_failed: int = 0
    retries: int = 0


@dataclass
class TaskExecution:
    """Task execution state."""
    task_id: str
    state: ExecutionState = ExecutionState.IDLE

    # Context
    context: Optional[ExecutionContext] = None

    # Result
    result: Optional[ExecutionResult] = None

    # Retries
    attempts: int = 0
    last_error: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class MissionExecutor:
    """
    Autonomous mission execution engine for BAEL.
    """

    def __init__(
        self,
        config: Optional[ExecutorConfig] = None,
    ):
        self.config = config or ExecutorConfig()

        # State
        self.state = ExecutionState.IDLE
        self.current_mission: Optional[str] = None

        # Task tracking
        self.task_executions: Dict[str, TaskExecution] = {}
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()

        # Task handlers
        self._task_handlers: Dict[str, Callable] = {}

        # Shared context
        self._shared_context: Dict[str, Any] = {}

        # Rate limiting
        self._api_call_times: List[float] = []
        self._api_semaphore = asyncio.Semaphore(self.config.max_concurrent_api_calls)

        # Control
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused
        self._stop_requested = False

        # Callbacks
        self._on_task_start: List[Callable] = []
        self._on_task_complete: List[Callable] = []
        self._on_task_fail: List[Callable] = []
        self._on_mission_complete: List[Callable] = []

        # Stats
        self.stats = {
            "missions_executed": 0,
            "tasks_executed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "total_retries": 0,
        }

    def register_handler(
        self,
        task_type: str,
        handler: Callable[[ExecutionContext], Any],
    ) -> None:
        """Register a task handler."""
        self._task_handlers[task_type] = handler

    async def execute_mission(
        self,
        mission: Any,  # Mission from MissionPlanner
        task_registry: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute a complete mission.

        Args:
            mission: Mission to execute
            task_registry: Registry of tasks (from TaskDecomposer)

        Returns:
            ExecutionResult
        """
        self.stats["missions_executed"] += 1
        start_time = time.time()

        self.state = ExecutionState.INITIALIZING
        self.current_mission = mission.id

        # Reset state
        self.task_executions.clear()
        self.running_tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        self._stop_requested = False

        try:
            # Initialize phase executions
            for phase in mission.phases:
                for task_id in phase.task_ids:
                    self.task_executions[task_id] = TaskExecution(task_id=task_id)

            # Execute phases
            self.state = ExecutionState.RUNNING

            for phase in mission.phases:
                if self._stop_requested:
                    break

                # Check phase dependencies
                if not self._can_start_phase(phase, mission):
                    if not self.config.continue_on_task_failure:
                        self.state = ExecutionState.FAILED
                        break
                    continue

                # Execute phase tasks
                phase_result = await self._execute_phase(phase, task_registry or {})

                if not phase_result.success and self.config.fail_fast:
                    self.state = ExecutionState.FAILED
                    break

            # Complete
            self.state = ExecutionState.COMPLETING

            success = len(self.failed_tasks) == 0 or self.config.continue_on_task_failure

            result = ExecutionResult(
                success=success,
                outputs=dict(self._shared_context),
                tasks_completed=len(self.completed_tasks),
                tasks_failed=len(self.failed_tasks),
                retries=self.stats["total_retries"],
                duration=timedelta(seconds=time.time() - start_time),
            )

            self.state = ExecutionState.FINISHED if success else ExecutionState.FAILED

            # Notify completion
            for callback in self._on_mission_complete:
                try:
                    callback(mission, result)
                except Exception as e:
                    logger.error(f"Mission complete callback error: {e}")

            return result

        except Exception as e:
            self.state = ExecutionState.FAILED
            return ExecutionResult(
                success=False,
                error=str(e),
                error_trace=traceback.format_exc(),
                duration=timedelta(seconds=time.time() - start_time),
            )

    def _can_start_phase(self, phase: Any, mission: Any) -> bool:
        """Check if phase dependencies are met."""
        for dep_id in phase.depends_on:
            # Find the dependent phase
            for p in mission.phases:
                if p.id == dep_id:
                    if p.status.value not in ("completed",):
                        return False
                    break
        return True

    async def _execute_phase(
        self,
        phase: Any,
        task_registry: Dict[str, Any],
    ) -> ExecutionResult:
        """Execute a mission phase."""
        task_ids = phase.task_ids

        # Execute tasks respecting dependencies
        while task_ids:
            if self._stop_requested:
                break

            await self._pause_event.wait()

            # Find tasks ready to run
            ready_tasks = []
            for task_id in task_ids:
                if task_id in self.completed_tasks or task_id in self.failed_tasks:
                    continue
                if task_id in self.running_tasks:
                    continue

                task = task_registry.get(task_id)
                if task and self._can_start_task(task):
                    ready_tasks.append(task_id)

            if not ready_tasks:
                # Wait for running tasks
                if self.running_tasks:
                    await asyncio.sleep(0.5)
                    continue
                else:
                    break

            # Limit parallelism
            ready_tasks = ready_tasks[:self.config.max_parallel_tasks - len(self.running_tasks)]

            # Start tasks
            tasks = []
            for task_id in ready_tasks:
                task = task_registry.get(task_id)
                tasks.append(self._execute_task(task))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        success = not any(
            tid in self.failed_tasks
            for tid in task_ids
        )

        return ExecutionResult(
            success=success,
            tasks_completed=len([t for t in task_ids if t in self.completed_tasks]),
            tasks_failed=len([t for t in task_ids if t in self.failed_tasks]),
        )

    def _can_start_task(self, task: Any) -> bool:
        """Check if task can start."""
        for dep_id in task.depends_on:
            if dep_id not in self.completed_tasks:
                return False
        return True

    async def _execute_task(
        self,
        task: Any,
    ) -> ExecutionResult:
        """Execute a single task with retries."""
        task_id = task.id
        execution = self.task_executions.get(task_id) or TaskExecution(task_id=task_id)

        self.running_tasks.add(task_id)
        execution.state = ExecutionState.RUNNING
        execution.started_at = datetime.now()

        self.stats["tasks_executed"] += 1

        # Notify start
        for callback in self._on_task_start:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"Task start callback error: {e}")

        # Prepare context
        context = ExecutionContext(
            mission_id=self.current_mission or "",
            task_id=task_id,
            shared=self._shared_context,
            tools=self._task_handlers,
        )

        # Gather inputs from dependencies
        for dep_id in task.depends_on:
            dep_execution = self.task_executions.get(dep_id)
            if dep_execution and dep_execution.result:
                context.inputs[dep_id] = dep_execution.result.outputs

        execution.context = context

        # Retry loop
        result = None
        retry_delay = self.config.retry_delay_seconds

        for attempt in range(1, self.config.max_retries + 1):
            execution.attempts = attempt
            context.attempt = attempt

            try:
                # Apply timeout
                timeout = self.config.task_timeout_seconds
                result = await asyncio.wait_for(
                    self._run_task_handler(task, context),
                    timeout=timeout,
                )

                # Success
                execution.state = ExecutionState.FINISHED
                execution.result = result
                execution.completed_at = datetime.now()

                self.running_tasks.discard(task_id)
                self.completed_tasks.add(task_id)
                self.stats["tasks_succeeded"] += 1

                # Store outputs in shared context
                if result.outputs:
                    self._shared_context[task_id] = result.outputs

                # Notify completion
                for callback in self._on_task_complete:
                    try:
                        callback(task, result)
                    except Exception as e:
                        logger.error(f"Task complete callback error: {e}")

                return result

            except asyncio.TimeoutError:
                execution.last_error = "Task timeout"
                logger.warning(f"Task {task_id} timed out (attempt {attempt})")

            except Exception as e:
                execution.last_error = str(e)
                logger.warning(f"Task {task_id} failed (attempt {attempt}): {e}")

            # Retry if not last attempt
            if attempt < self.config.max_retries:
                self.stats["total_retries"] += 1
                await asyncio.sleep(retry_delay)
                retry_delay *= self.config.retry_backoff_multiplier

        # All retries failed
        execution.state = ExecutionState.FAILED
        result = ExecutionResult(
            success=False,
            error=execution.last_error,
        )
        execution.result = result
        execution.completed_at = datetime.now()

        self.running_tasks.discard(task_id)
        self.failed_tasks.add(task_id)
        self.stats["tasks_failed"] += 1

        # Notify failure
        for callback in self._on_task_fail:
            try:
                callback(task, result)
            except Exception as e:
                logger.error(f"Task fail callback error: {e}")

        return result

    async def _run_task_handler(
        self,
        task: Any,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Run the task handler."""
        # Find handler by task type
        handler = self._task_handlers.get(task.type.value if hasattr(task, "type") else "default")

        if not handler:
            # Use default handler
            handler = self._default_task_handler

        # Rate limiting
        await self._rate_limit()

        try:
            start_time = time.time()

            if asyncio.iscoroutinefunction(handler):
                result = await handler(context)
            else:
                result = handler(context)

            duration = timedelta(seconds=time.time() - start_time)

            if isinstance(result, ExecutionResult):
                result.duration = duration
                return result
            else:
                return ExecutionResult(
                    success=True,
                    data=result,
                    outputs=context.outputs,
                    duration=duration,
                )

        except Exception as e:
            raise

    async def _default_task_handler(
        self,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Default task handler (placeholder)."""
        # This would be overridden with actual task logic
        logger.info(f"Executing task: {context.task_id}")
        await asyncio.sleep(0.1)  # Simulate work

        return ExecutionResult(
            success=True,
            outputs={"completed": True},
        )

    async def _rate_limit(self) -> None:
        """Apply rate limiting."""
        async with self._api_semaphore:
            current_time = time.time()

            # Clean old entries
            cutoff = current_time - 60
            self._api_call_times = [
                t for t in self._api_call_times if t > cutoff
            ]

            # Check rate
            if len(self._api_call_times) >= self.config.max_api_calls_per_minute:
                # Wait until oldest expires
                wait_time = self._api_call_times[0] + 60 - current_time
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self._api_call_times.append(time.time())

    def pause(self) -> None:
        """Pause execution."""
        self._pause_event.clear()
        self.state = ExecutionState.PAUSED
        logger.info("Execution paused")

    def resume(self) -> None:
        """Resume execution."""
        self._pause_event.set()
        self.state = ExecutionState.RUNNING
        logger.info("Execution resumed")

    def stop(self) -> None:
        """Request stop."""
        self._stop_requested = True
        logger.info("Stop requested")

    def on_task_start(self, callback: Callable) -> None:
        """Register task start callback."""
        self._on_task_start.append(callback)

    def on_task_complete(self, callback: Callable) -> None:
        """Register task complete callback."""
        self._on_task_complete.append(callback)

    def on_task_fail(self, callback: Callable) -> None:
        """Register task fail callback."""
        self._on_task_fail.append(callback)

    def on_mission_complete(self, callback: Callable) -> None:
        """Register mission complete callback."""
        self._on_mission_complete.append(callback)

    def get_status(self) -> Dict[str, Any]:
        """Get executor status."""
        return {
            "state": self.state.value,
            "current_mission": self.current_mission,
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        return {
            **self.stats,
            "state": self.state.value,
        }


def demo():
    """Demonstrate mission executor."""
    import asyncio
    from dataclasses import dataclass
    from enum import Enum

    print("=" * 60)
    print("BAEL Mission Executor Demo")
    print("=" * 60)

    # Mock mission and task structures
    @dataclass
    class MockPhase:
        id: str
        name: str
        depends_on: List[str] = field(default_factory=list)
        task_ids: List[str] = field(default_factory=list)
        status: Any = None

    @dataclass
    class MockMission:
        id: str
        name: str
        phases: List[MockPhase] = field(default_factory=list)

    @dataclass
    class MockTask:
        id: str
        name: str
        type: Any = None
        depends_on: List[str] = field(default_factory=list)

    # Create executor
    executor = MissionExecutor(ExecutorConfig(
        max_parallel_tasks=3,
        max_retries=2,
        task_timeout_seconds=10.0,
    ))

    # Register handlers
    async def research_handler(ctx: ExecutionContext):
        await asyncio.sleep(0.1)
        return ExecutionResult(success=True, outputs={"data": "research results"})

    executor.register_handler("research", research_handler)
    executor.register_handler("default", executor._default_task_handler)

    # Register callbacks
    executor.on_task_complete(lambda t, r: print(f"  ✓ {t.name}"))
    executor.on_task_fail(lambda t, r: print(f"  ✗ {t.name}: {r.error}"))

    # Create mock mission
    mission = MockMission(
        id="demo_mission",
        name="Demo Mission",
        phases=[
            MockPhase(
                id="phase_1",
                name="Phase 1",
                task_ids=["task_1", "task_2"],
            ),
            MockPhase(
                id="phase_2",
                name="Phase 2",
                depends_on=["phase_1"],
                task_ids=["task_3"],
            ),
        ],
    )

    # Create mock tasks
    task_registry = {
        "task_1": MockTask(id="task_1", name="Task 1"),
        "task_2": MockTask(id="task_2", name="Task 2"),
        "task_3": MockTask(id="task_3", name="Task 3", depends_on=["task_1", "task_2"]),
    }

    print("\nExecuting mission:")

    # Execute
    async def run():
        return await executor.execute_mission(mission, task_registry)

    result = asyncio.run(run())

    print(f"\nResult: {'Success' if result.success else 'Failed'}")
    print(f"  Tasks completed: {result.tasks_completed}")
    print(f"  Tasks failed: {result.tasks_failed}")
    print(f"  Duration: {result.duration}")

    print(f"\nStats: {executor.get_stats()}")


if __name__ == "__main__":
    demo()
