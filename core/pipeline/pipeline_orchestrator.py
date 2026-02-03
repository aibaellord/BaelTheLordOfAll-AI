#!/usr/bin/env python3
"""
BAEL - Pipeline Orchestrator
Comprehensive ML pipeline orchestration.

Features:
- Pipeline definition and execution
- Stage management
- Parallel execution
- Error handling and retry
- Pipeline persistence
- Execution monitoring
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class StageStatus(Enum):
    """Stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PipelineStatus(Enum):
    """Pipeline execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class ExecutionMode(Enum):
    """Pipeline execution mode."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class RetryStrategy(Enum):
    """Retry strategies."""
    NONE = "none"
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class StageResult:
    """Result of stage execution."""
    stage_id: str = ""
    status: StageStatus = StageStatus.PENDING
    output: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    retries: int = 0


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    pipeline_id: str = ""
    status: PipelineStatus = PipelineStatus.IDLE
    stage_results: Dict[str, StageResult] = field(default_factory=dict)
    final_output: Any = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration: float = 0.0
    stages_completed: int = 0
    stages_failed: int = 0


@dataclass
class StageConfig:
    """Stage configuration."""
    timeout: Optional[float] = None
    max_retries: int = 0
    retry_strategy: RetryStrategy = RetryStrategy.NONE
    retry_delay: float = 1.0
    skip_on_failure: bool = False
    cache_output: bool = False


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    name: str = "pipeline"
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_parallel: int = 4
    fail_fast: bool = True
    enable_caching: bool = False
    log_execution: bool = True


@dataclass
class ExecutionContext:
    """Execution context passed through pipeline."""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    stage_outputs: Dict[str, Any] = field(default_factory=dict)
    pipeline_id: str = ""
    current_stage: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in context."""
        self.data[key] = value

    def get_stage_output(self, stage_id: str) -> Any:
        """Get output from a previous stage."""
        return self.stage_outputs.get(stage_id)


# =============================================================================
# STAGE
# =============================================================================

class Stage(ABC):
    """Abstract pipeline stage."""

    def __init__(
        self,
        stage_id: Optional[str] = None,
        name: Optional[str] = None,
        config: Optional[StageConfig] = None
    ):
        self.stage_id = stage_id or str(uuid.uuid4())[:8]
        self.name = name or self.__class__.__name__
        self.config = config or StageConfig()
        self._dependencies: List[str] = []

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Any:
        """Execute the stage."""
        pass

    def depends_on(self, *stage_ids: str) -> 'Stage':
        """Add dependencies."""
        self._dependencies.extend(stage_ids)
        return self

    def get_dependencies(self) -> List[str]:
        """Get stage dependencies."""
        return self._dependencies.copy()

    async def run(self, context: ExecutionContext) -> StageResult:
        """Run stage with retry logic."""
        result = StageResult(
            stage_id=self.stage_id,
            start_time=datetime.now()
        )

        retries = 0
        delay = self.config.retry_delay

        while True:
            try:
                result.status = StageStatus.RUNNING
                context.current_stage = self.stage_id

                if self.config.timeout:
                    output = await asyncio.wait_for(
                        self.execute(context),
                        timeout=self.config.timeout
                    )
                else:
                    output = await self.execute(context)

                result.status = StageStatus.COMPLETED
                result.output = output
                break

            except asyncio.TimeoutError:
                result.error = f"Stage timed out after {self.config.timeout}s"
                result.status = StageStatus.FAILED
            except Exception as e:
                result.error = str(e)
                result.status = StageStatus.FAILED

            if retries >= self.config.max_retries:
                break

            retries += 1
            result.retries = retries

            if self.config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                await asyncio.sleep(delay)
                delay *= 2
            elif self.config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
                await asyncio.sleep(delay)
                delay += self.config.retry_delay
            elif self.config.retry_strategy == RetryStrategy.IMMEDIATE:
                pass
            else:
                break

        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()

        return result


class FunctionStage(Stage):
    """Stage that wraps a function."""

    def __init__(
        self,
        func: Callable[[ExecutionContext], Any],
        stage_id: Optional[str] = None,
        name: Optional[str] = None,
        config: Optional[StageConfig] = None
    ):
        super().__init__(stage_id, name or func.__name__, config)
        self._func = func

    async def execute(self, context: ExecutionContext) -> Any:
        """Execute the function."""
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(context)
        return self._func(context)


class TransformStage(Stage):
    """Stage for data transformation."""

    def __init__(
        self,
        transform_func: Callable[[Any], Any],
        input_key: str = "input",
        output_key: str = "output",
        stage_id: Optional[str] = None,
        config: Optional[StageConfig] = None
    ):
        super().__init__(stage_id, "TransformStage", config)
        self._transform = transform_func
        self._input_key = input_key
        self._output_key = output_key

    async def execute(self, context: ExecutionContext) -> Any:
        """Execute transformation."""
        data = context.get(self._input_key)
        result = self._transform(data)
        context.set(self._output_key, result)
        return result


class ConditionalStage(Stage):
    """Stage with conditional execution."""

    def __init__(
        self,
        condition: Callable[[ExecutionContext], bool],
        if_true: Stage,
        if_false: Optional[Stage] = None,
        stage_id: Optional[str] = None,
        config: Optional[StageConfig] = None
    ):
        super().__init__(stage_id, "ConditionalStage", config)
        self._condition = condition
        self._if_true = if_true
        self._if_false = if_false

    async def execute(self, context: ExecutionContext) -> Any:
        """Execute based on condition."""
        if self._condition(context):
            result = await self._if_true.run(context)
            return result.output
        elif self._if_false:
            result = await self._if_false.run(context)
            return result.output
        return None


class ParallelStage(Stage):
    """Stage that runs multiple stages in parallel."""

    def __init__(
        self,
        stages: List[Stage],
        stage_id: Optional[str] = None,
        config: Optional[StageConfig] = None
    ):
        super().__init__(stage_id, "ParallelStage", config)
        self._stages = stages

    async def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute stages in parallel."""
        tasks = [stage.run(context) for stage in self._stages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs = {}
        for stage, result in zip(self._stages, results):
            if isinstance(result, Exception):
                outputs[stage.stage_id] = None
            else:
                outputs[stage.stage_id] = result.output

        return outputs


# =============================================================================
# PIPELINE
# =============================================================================

class Pipeline:
    """Pipeline for orchestrating stages."""

    def __init__(
        self,
        pipeline_id: Optional[str] = None,
        config: Optional[PipelineConfig] = None
    ):
        self.pipeline_id = pipeline_id or str(uuid.uuid4())[:8]
        self.config = config or PipelineConfig()
        self._stages: Dict[str, Stage] = {}
        self._order: List[str] = []
        self._status = PipelineStatus.IDLE
        self._result: Optional[PipelineResult] = None

    def add_stage(self, stage: Stage) -> 'Pipeline':
        """Add a stage to the pipeline."""
        self._stages[stage.stage_id] = stage

        if stage.stage_id not in self._order:
            self._order.append(stage.stage_id)

        return self

    def add_stages(self, *stages: Stage) -> 'Pipeline':
        """Add multiple stages."""
        for stage in stages:
            self.add_stage(stage)
        return self

    def get_stage(self, stage_id: str) -> Optional[Stage]:
        """Get stage by ID."""
        return self._stages.get(stage_id)

    def _topological_sort(self) -> List[str]:
        """Sort stages by dependencies."""
        in_degree: Dict[str, int] = {sid: 0 for sid in self._stages}
        graph: Dict[str, List[str]] = {sid: [] for sid in self._stages}

        for stage_id, stage in self._stages.items():
            for dep in stage.get_dependencies():
                if dep in graph:
                    graph[dep].append(stage_id)
                    in_degree[stage_id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._stages):
            return self._order

        return result

    async def run(
        self,
        initial_context: Optional[ExecutionContext] = None
    ) -> PipelineResult:
        """Run the pipeline."""
        context = initial_context or ExecutionContext()
        context.pipeline_id = self.pipeline_id

        result = PipelineResult(
            pipeline_id=self.pipeline_id,
            start_time=datetime.now()
        )

        self._status = PipelineStatus.RUNNING
        result.status = PipelineStatus.RUNNING

        execution_order = self._topological_sort()

        try:
            if self.config.execution_mode == ExecutionMode.SEQUENTIAL:
                await self._run_sequential(execution_order, context, result)
            elif self.config.execution_mode == ExecutionMode.PARALLEL:
                await self._run_parallel(execution_order, context, result)
            else:
                await self._run_sequential(execution_order, context, result)

            if result.stages_failed > 0 and self.config.fail_fast:
                result.status = PipelineStatus.FAILED
            else:
                result.status = PipelineStatus.COMPLETED

        except Exception as e:
            result.status = PipelineStatus.FAILED

        result.end_time = datetime.now()
        result.total_duration = (result.end_time - result.start_time).total_seconds()
        result.final_output = context.data

        self._status = result.status
        self._result = result

        return result

    async def _run_sequential(
        self,
        order: List[str],
        context: ExecutionContext,
        result: PipelineResult
    ) -> None:
        """Run stages sequentially."""
        for stage_id in order:
            if self._status == PipelineStatus.CANCELLED:
                break

            stage = self._stages[stage_id]
            stage_result = await stage.run(context)

            result.stage_results[stage_id] = stage_result
            context.stage_outputs[stage_id] = stage_result.output

            if stage_result.status == StageStatus.COMPLETED:
                result.stages_completed += 1
            else:
                result.stages_failed += 1

                if self.config.fail_fast and not stage.config.skip_on_failure:
                    break

    async def _run_parallel(
        self,
        order: List[str],
        context: ExecutionContext,
        result: PipelineResult
    ) -> None:
        """Run stages in parallel where possible."""
        completed: Set[str] = set()
        pending = set(order)

        while pending:
            ready = []

            for stage_id in pending:
                stage = self._stages[stage_id]
                deps = set(stage.get_dependencies())

                if deps.issubset(completed):
                    ready.append(stage_id)

            if not ready:
                if pending:
                    ready = [list(pending)[0]]

            ready = ready[:self.config.max_parallel]

            tasks = []
            for stage_id in ready:
                stage = self._stages[stage_id]
                tasks.append(stage.run(context))

            stage_results = await asyncio.gather(*tasks, return_exceptions=True)

            for stage_id, stage_result in zip(ready, stage_results):
                if isinstance(stage_result, Exception):
                    result.stage_results[stage_id] = StageResult(
                        stage_id=stage_id,
                        status=StageStatus.FAILED,
                        error=str(stage_result)
                    )
                    result.stages_failed += 1
                else:
                    result.stage_results[stage_id] = stage_result
                    context.stage_outputs[stage_id] = stage_result.output

                    if stage_result.status == StageStatus.COMPLETED:
                        result.stages_completed += 1
                    else:
                        result.stages_failed += 1

                completed.add(stage_id)
                pending.discard(stage_id)

            if result.stages_failed > 0 and self.config.fail_fast:
                break

    def cancel(self) -> None:
        """Cancel pipeline execution."""
        self._status = PipelineStatus.CANCELLED

    def get_status(self) -> PipelineStatus:
        """Get pipeline status."""
        return self._status

    def get_result(self) -> Optional[PipelineResult]:
        """Get pipeline result."""
        return self._result


# =============================================================================
# PIPELINE ORCHESTRATOR
# =============================================================================

class PipelineOrchestrator:
    """
    Pipeline Orchestrator for BAEL.

    Comprehensive ML pipeline orchestration.
    """

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._history: List[PipelineResult] = []

    def create_pipeline(
        self,
        name: str,
        config: Optional[PipelineConfig] = None
    ) -> Pipeline:
        """Create a new pipeline."""
        if config:
            config.name = name
        else:
            config = PipelineConfig(name=name)

        pipeline = Pipeline(config=config)
        self._pipelines[name] = pipeline
        return pipeline

    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """Get pipeline by name."""
        return self._pipelines.get(name)

    async def run_pipeline(
        self,
        name: str,
        context: Optional[ExecutionContext] = None
    ) -> Optional[PipelineResult]:
        """Run a pipeline."""
        pipeline = self._pipelines.get(name)
        if not pipeline:
            return None

        result = await pipeline.run(context)
        self._history.append(result)

        return result

    def get_history(self) -> List[PipelineResult]:
        """Get execution history."""
        return self._history.copy()

    def create_stage(
        self,
        func: Callable[[ExecutionContext], Any],
        stage_id: Optional[str] = None,
        name: Optional[str] = None,
        config: Optional[StageConfig] = None
    ) -> FunctionStage:
        """Create a function stage."""
        return FunctionStage(func, stage_id, name, config)

    def create_transform_stage(
        self,
        transform_func: Callable[[Any], Any],
        input_key: str = "input",
        output_key: str = "output",
        stage_id: Optional[str] = None,
        config: Optional[StageConfig] = None
    ) -> TransformStage:
        """Create a transform stage."""
        return TransformStage(transform_func, input_key, output_key, stage_id, config)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Pipeline Orchestrator."""
    print("=" * 70)
    print("BAEL - PIPELINE ORCHESTRATOR DEMO")
    print("Comprehensive ML Pipeline Orchestration")
    print("=" * 70)
    print()

    orchestrator = PipelineOrchestrator()

    # 1. Simple Sequential Pipeline
    print("1. SIMPLE SEQUENTIAL PIPELINE:")
    print("-" * 40)

    async def load_data(ctx: ExecutionContext) -> List[int]:
        print("   Loading data...")
        data = list(range(10))
        ctx.set("data", data)
        return data

    async def process_data(ctx: ExecutionContext) -> List[int]:
        print("   Processing data...")
        data = ctx.get("data")
        processed = [x * 2 for x in data]
        ctx.set("processed", processed)
        return processed

    async def save_results(ctx: ExecutionContext) -> str:
        print("   Saving results...")
        processed = ctx.get("processed")
        return f"Saved {len(processed)} items"

    pipeline = orchestrator.create_pipeline("simple")
    pipeline.add_stages(
        orchestrator.create_stage(load_data, "load"),
        orchestrator.create_stage(process_data, "process"),
        orchestrator.create_stage(save_results, "save")
    )

    context = ExecutionContext()
    result = await orchestrator.run_pipeline("simple", context)

    print(f"   Status: {result.status.value}")
    print(f"   Duration: {result.total_duration:.4f}s")
    print(f"   Stages completed: {result.stages_completed}")
    print()

    # 2. Pipeline with Dependencies
    print("2. PIPELINE WITH DEPENDENCIES:")
    print("-" * 40)

    async def fetch_users(ctx: ExecutionContext) -> List[str]:
        await asyncio.sleep(0.05)
        return ["Alice", "Bob", "Charlie"]

    async def fetch_orders(ctx: ExecutionContext) -> List[str]:
        await asyncio.sleep(0.05)
        return ["Order1", "Order2"]

    async def combine_data(ctx: ExecutionContext) -> Dict:
        users = ctx.get_stage_output("users")
        orders = ctx.get_stage_output("orders")
        return {"users": users, "orders": orders}

    dep_pipeline = orchestrator.create_pipeline(
        "dependent",
        PipelineConfig(execution_mode=ExecutionMode.PARALLEL)
    )

    users_stage = orchestrator.create_stage(fetch_users, "users")
    orders_stage = orchestrator.create_stage(fetch_orders, "orders")
    combine_stage = orchestrator.create_stage(combine_data, "combine")
    combine_stage.depends_on("users", "orders")

    dep_pipeline.add_stages(users_stage, orders_stage, combine_stage)

    result = await orchestrator.run_pipeline("dependent")

    print(f"   Status: {result.status.value}")
    print(f"   Combined output: {result.stage_results['combine'].output}")
    print()

    # 3. Transform Pipeline
    print("3. TRANSFORM PIPELINE:")
    print("-" * 40)

    transform_pipeline = orchestrator.create_pipeline("transform")

    transform_pipeline.add_stages(
        orchestrator.create_transform_stage(
            lambda x: x * 2,
            "input", "doubled",
            "double"
        ),
        orchestrator.create_transform_stage(
            lambda x: x + 10,
            "doubled", "final",
            "add_ten"
        )
    )

    ctx = ExecutionContext(data={"input": 5})
    result = await orchestrator.run_pipeline("transform", ctx)

    print(f"   Input: 5")
    print(f"   Doubled: {ctx.get('doubled')}")
    print(f"   Final: {ctx.get('final')}")
    print()

    # 4. Retry Logic
    print("4. RETRY LOGIC:")
    print("-" * 40)

    attempt_count = 0

    async def flaky_stage(ctx: ExecutionContext) -> str:
        nonlocal attempt_count
        attempt_count += 1

        if attempt_count < 3:
            raise Exception(f"Attempt {attempt_count} failed")

        return "Success on attempt 3"

    retry_config = StageConfig(
        max_retries=3,
        retry_strategy=RetryStrategy.IMMEDIATE
    )

    retry_pipeline = orchestrator.create_pipeline("retry")
    retry_pipeline.add_stage(
        orchestrator.create_stage(flaky_stage, "flaky", config=retry_config)
    )

    result = await orchestrator.run_pipeline("retry")

    print(f"   Status: {result.status.value}")
    print(f"   Retries: {result.stage_results['flaky'].retries}")
    print(f"   Output: {result.stage_results['flaky'].output}")
    print()

    # 5. Conditional Execution
    print("5. CONDITIONAL EXECUTION:")
    print("-" * 40)

    async def high_value_process(ctx: ExecutionContext) -> str:
        return "High value processing"

    async def low_value_process(ctx: ExecutionContext) -> str:
        return "Low value processing"

    conditional = ConditionalStage(
        condition=lambda ctx: ctx.get("value", 0) > 50,
        if_true=FunctionStage(high_value_process, "high"),
        if_false=FunctionStage(low_value_process, "low"),
        stage_id="conditional"
    )

    cond_pipeline = orchestrator.create_pipeline("conditional")
    cond_pipeline.add_stage(conditional)

    high_ctx = ExecutionContext(data={"value": 100})
    result = await orchestrator.run_pipeline("conditional", high_ctx)
    print(f"   Value=100: {result.stage_results['conditional'].output}")

    low_ctx = ExecutionContext(data={"value": 10})
    result = await orchestrator.run_pipeline("conditional", low_ctx)
    print(f"   Value=10: {result.stage_results['conditional'].output}")
    print()

    # 6. Parallel Stages
    print("6. PARALLEL STAGES:")
    print("-" * 40)

    async def task_a(ctx: ExecutionContext) -> str:
        await asyncio.sleep(0.1)
        return "Task A done"

    async def task_b(ctx: ExecutionContext) -> str:
        await asyncio.sleep(0.1)
        return "Task B done"

    async def task_c(ctx: ExecutionContext) -> str:
        await asyncio.sleep(0.1)
        return "Task C done"

    parallel = ParallelStage([
        FunctionStage(task_a, "a"),
        FunctionStage(task_b, "b"),
        FunctionStage(task_c, "c")
    ], "parallel")

    par_pipeline = orchestrator.create_pipeline("parallel")
    par_pipeline.add_stage(parallel)

    start = time.time()
    result = await orchestrator.run_pipeline("parallel")
    elapsed = time.time() - start

    print(f"   Duration: {elapsed:.3f}s (parallel, not 0.3s)")
    print(f"   Results: {result.stage_results['parallel'].output}")
    print()

    # 7. Execution History
    print("7. EXECUTION HISTORY:")
    print("-" * 40)

    history = orchestrator.get_history()

    print(f"   Total executions: {len(history)}")
    for i, h in enumerate(history[-3:]):
        print(f"   {i + 1}. Pipeline {h.pipeline_id}: {h.status.value} ({h.total_duration:.3f}s)")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Pipeline Orchestrator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
