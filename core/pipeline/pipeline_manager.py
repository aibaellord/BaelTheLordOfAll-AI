#!/usr/bin/env python3
"""
BAEL - Pipeline Manager
Advanced data pipeline management for AI agent operations.

Features:
- Pipeline definition
- Stage execution
- Parallel execution
- Sequential execution
- Error handling
- Retry logic
- Pipeline branching
- Conditional execution
- Pipeline visualization
- Metrics collection
"""

import asyncio
import copy
import threading
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
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class StageStatus(Enum):
    """Stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PipelineStatus(Enum):
    """Pipeline execution status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(Enum):
    """Stage execution mode."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class RetryStrategy(Enum):
    """Retry strategies."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class StageConfig:
    """Stage configuration."""
    name: str = ""
    retry_count: int = 0
    retry_delay_seconds: float = 1.0
    retry_strategy: RetryStrategy = RetryStrategy.NONE
    timeout_seconds: Optional[float] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    on_success: Optional[str] = None  # Next stage
    on_failure: Optional[str] = None  # Fallback stage


@dataclass
class StageResult:
    """Stage execution result."""
    stage_id: str = ""
    stage_name: str = ""
    status: StageStatus = StageStatus.PENDING
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    retries: int = 0


@dataclass
class PipelineContext:
    """Pipeline execution context."""
    pipeline_id: str = ""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Dict[str, Any] = field(default_factory=dict)
    stage_outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Pipeline execution result."""
    pipeline_id: str = ""
    run_id: str = ""
    status: PipelineStatus = PipelineStatus.IDLE
    stage_results: List[StageResult] = field(default_factory=list)
    output: Any = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


@dataclass
class PipelineStats:
    """Pipeline statistics."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    avg_duration_ms: float = 0.0
    stages_executed: int = 0
    total_retries: int = 0


# =============================================================================
# STAGE
# =============================================================================

class Stage(ABC):
    """Base pipeline stage."""

    def __init__(
        self,
        name: str,
        config: Optional[StageConfig] = None
    ):
        self.stage_id = str(uuid.uuid4())
        self.name = name
        self.config = config or StageConfig(name=name)

    @abstractmethod
    async def execute(
        self,
        context: PipelineContext
    ) -> Any:
        """Execute the stage."""
        pass

    def should_run(self, context: PipelineContext) -> bool:
        """Check if stage should run."""
        if self.config.condition:
            return self.config.condition(context.data)
        return True


class FunctionStage(Stage):
    """Stage that executes a function."""

    def __init__(
        self,
        name: str,
        func: Callable[[PipelineContext], Any],
        config: Optional[StageConfig] = None
    ):
        super().__init__(name, config)
        self._func = func

    async def execute(self, context: PipelineContext) -> Any:
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(context)
        return self._func(context)


class LambdaStage(Stage):
    """Stage that executes a lambda on data."""

    def __init__(
        self,
        name: str,
        transform: Callable[[Any], Any],
        input_key: str = "input",
        output_key: str = "output",
        config: Optional[StageConfig] = None
    ):
        super().__init__(name, config)
        self._transform = transform
        self._input_key = input_key
        self._output_key = output_key

    async def execute(self, context: PipelineContext) -> Any:
        data = context.data.get(self._input_key)
        result = self._transform(data)
        context.data[self._output_key] = result
        return result


class MapStage(Stage):
    """Stage that maps function over list."""

    def __init__(
        self,
        name: str,
        func: Callable[[Any], Any],
        input_key: str = "items",
        output_key: str = "mapped",
        config: Optional[StageConfig] = None
    ):
        super().__init__(name, config)
        self._func = func
        self._input_key = input_key
        self._output_key = output_key

    async def execute(self, context: PipelineContext) -> Any:
        items = context.data.get(self._input_key, [])
        results = [self._func(item) for item in items]
        context.data[self._output_key] = results
        return results


class FilterStage(Stage):
    """Stage that filters list."""

    def __init__(
        self,
        name: str,
        predicate: Callable[[Any], bool],
        input_key: str = "items",
        output_key: str = "filtered",
        config: Optional[StageConfig] = None
    ):
        super().__init__(name, config)
        self._predicate = predicate
        self._input_key = input_key
        self._output_key = output_key

    async def execute(self, context: PipelineContext) -> Any:
        items = context.data.get(self._input_key, [])
        results = [item for item in items if self._predicate(item)]
        context.data[self._output_key] = results
        return results


class ReduceStage(Stage):
    """Stage that reduces list to single value."""

    def __init__(
        self,
        name: str,
        func: Callable[[Any, Any], Any],
        initial: Any = None,
        input_key: str = "items",
        output_key: str = "reduced",
        config: Optional[StageConfig] = None
    ):
        super().__init__(name, config)
        self._func = func
        self._initial = initial
        self._input_key = input_key
        self._output_key = output_key

    async def execute(self, context: PipelineContext) -> Any:
        items = context.data.get(self._input_key, [])

        if not items:
            result = self._initial
        else:
            result = self._initial if self._initial is not None else items[0]
            start = 0 if self._initial is not None else 1

            for item in items[start:]:
                result = self._func(result, item)

        context.data[self._output_key] = result
        return result


class BranchStage(Stage):
    """Stage that branches based on condition."""

    def __init__(
        self,
        name: str,
        condition: Callable[[PipelineContext], bool],
        true_stage: str,
        false_stage: str,
        config: Optional[StageConfig] = None
    ):
        super().__init__(name, config)
        self._condition = condition
        self._true_stage = true_stage
        self._false_stage = false_stage

    async def execute(self, context: PipelineContext) -> Any:
        if self._condition(context):
            return {"branch": "true", "next": self._true_stage}
        return {"branch": "false", "next": self._false_stage}


# =============================================================================
# STAGE EXECUTOR
# =============================================================================

class StageExecutor:
    """Executes pipeline stages."""

    def __init__(self):
        self._lock = threading.Lock()

    async def execute(
        self,
        stage: Stage,
        context: PipelineContext
    ) -> StageResult:
        """Execute a stage with retry logic."""
        result = StageResult(
            stage_id=stage.stage_id,
            stage_name=stage.name,
            started_at=datetime.utcnow()
        )

        # Check condition
        if not stage.should_run(context):
            result.status = StageStatus.SKIPPED
            result.completed_at = datetime.utcnow()
            return result

        result.status = StageStatus.RUNNING

        config = stage.config
        max_retries = config.retry_count
        current_retry = 0

        while current_retry <= max_retries:
            try:
                # Execute with timeout
                if config.timeout_seconds:
                    output = await asyncio.wait_for(
                        stage.execute(context),
                        timeout=config.timeout_seconds
                    )
                else:
                    output = await stage.execute(context)

                result.output = output
                result.status = StageStatus.SUCCESS
                result.retries = current_retry

                # Store in context
                context.stage_outputs[stage.name] = output

                break

            except asyncio.TimeoutError:
                result.error = f"Timeout after {config.timeout_seconds}s"
                result.status = StageStatus.FAILED
                current_retry += 1

            except Exception as e:
                result.error = str(e)
                result.status = StageStatus.FAILED
                current_retry += 1

            if current_retry <= max_retries:
                # Calculate delay
                if config.retry_strategy == RetryStrategy.FIXED:
                    delay = config.retry_delay_seconds
                elif config.retry_strategy == RetryStrategy.EXPONENTIAL:
                    delay = config.retry_delay_seconds * (2 ** current_retry)
                else:
                    delay = config.retry_delay_seconds

                await asyncio.sleep(delay)

        result.completed_at = datetime.utcnow()
        result.duration_ms = (
            (result.completed_at - result.started_at).total_seconds() * 1000
        )

        return result


# =============================================================================
# PIPELINE
# =============================================================================

class Pipeline:
    """Pipeline definition."""

    def __init__(
        self,
        name: str,
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    ):
        self.pipeline_id = str(uuid.uuid4())
        self.name = name
        self.mode = mode
        self._stages: List[Stage] = []
        self._stage_map: Dict[str, Stage] = {}
        self._dependencies: Dict[str, List[str]] = defaultdict(list)

    def add_stage(
        self,
        stage: Stage,
        after: Optional[str] = None
    ) -> 'Pipeline':
        """Add stage to pipeline."""
        self._stages.append(stage)
        self._stage_map[stage.name] = stage

        if after:
            self._dependencies[stage.name].append(after)

        return self

    def get_stage(self, name: str) -> Optional[Stage]:
        """Get stage by name."""
        return self._stage_map.get(name)

    def get_stages(self) -> List[Stage]:
        """Get all stages."""
        return list(self._stages)

    def get_execution_order(self) -> List[Stage]:
        """Get stages in execution order."""
        if self.mode == ExecutionMode.PARALLEL:
            return list(self._stages)

        # Topological sort for dependencies
        visited = set()
        order = []

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)

            for dep in self._dependencies.get(name, []):
                visit(dep)

            if name in self._stage_map:
                order.append(self._stage_map[name])

        for stage in self._stages:
            visit(stage.name)

        return order


# =============================================================================
# PIPELINE MANAGER
# =============================================================================

class PipelineManager:
    """
    Pipeline Manager for BAEL.

    Advanced data pipeline management.
    """

    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._executor = StageExecutor()
        self._results: Dict[str, List[PipelineResult]] = defaultdict(list)
        self._stats: Dict[str, PipelineStats] = defaultdict(PipelineStats)
        self._running: Dict[str, bool] = {}
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # PIPELINE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_pipeline(
        self,
        name: str,
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    ) -> Pipeline:
        """Create pipeline."""
        pipeline = Pipeline(name, mode)

        with self._lock:
            self._pipelines[pipeline.pipeline_id] = pipeline
            self._stats[pipeline.pipeline_id] = PipelineStats()

        return pipeline

    def get_pipeline(
        self,
        pipeline_id: str
    ) -> Optional[Pipeline]:
        """Get pipeline."""
        with self._lock:
            return self._pipelines.get(pipeline_id)

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete pipeline."""
        with self._lock:
            if pipeline_id in self._pipelines:
                del self._pipelines[pipeline_id]
                return True
            return False

    def list_pipelines(self) -> List[Pipeline]:
        """List all pipelines."""
        with self._lock:
            return list(self._pipelines.values())

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def execute(
        self,
        pipeline_id: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PipelineResult:
        """Execute pipeline."""
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)

            if not pipeline:
                return PipelineResult(
                    pipeline_id=pipeline_id,
                    status=PipelineStatus.FAILED
                )

            self._running[pipeline_id] = True

        context = PipelineContext(
            pipeline_id=pipeline_id,
            data=data or {},
            metadata=metadata or {}
        )

        result = PipelineResult(
            pipeline_id=pipeline_id,
            run_id=context.run_id,
            started_at=datetime.utcnow()
        )

        result.status = PipelineStatus.RUNNING

        try:
            if pipeline.mode == ExecutionMode.SEQUENTIAL:
                await self._execute_sequential(pipeline, context, result)
            else:
                await self._execute_parallel(pipeline, context, result)

            # Check if all stages succeeded
            all_success = all(
                r.status in (StageStatus.SUCCESS, StageStatus.SKIPPED)
                for r in result.stage_results
            )

            if all_success:
                result.status = PipelineStatus.SUCCESS
                result.output = context.stage_outputs
            else:
                result.status = PipelineStatus.FAILED

        except Exception as e:
            result.status = PipelineStatus.FAILED

        result.completed_at = datetime.utcnow()
        result.duration_ms = (
            (result.completed_at - result.started_at).total_seconds() * 1000
        )

        with self._lock:
            self._running[pipeline_id] = False
            self._results[pipeline_id].append(result)
            self._update_stats(pipeline_id, result)

        return result

    async def _execute_sequential(
        self,
        pipeline: Pipeline,
        context: PipelineContext,
        result: PipelineResult
    ) -> None:
        """Execute stages sequentially."""
        stages = pipeline.get_execution_order()
        current_idx = 0

        while current_idx < len(stages):
            # Check cancellation
            with self._lock:
                if not self._running.get(pipeline.pipeline_id, False):
                    break

            stage = stages[current_idx]
            stage_result = await self._executor.execute(stage, context)
            result.stage_results.append(stage_result)

            if stage_result.status == StageStatus.FAILED:
                # Check for fallback
                if stage.config.on_failure:
                    fallback = pipeline.get_stage(stage.config.on_failure)
                    if fallback:
                        # Find index of fallback stage
                        for i, s in enumerate(stages):
                            if s.name == fallback.name:
                                current_idx = i
                                continue

                break

            elif stage_result.status == StageStatus.SUCCESS:
                # Check for branch result
                if isinstance(stage_result.output, dict):
                    next_stage = stage_result.output.get("next")
                    if next_stage:
                        for i, s in enumerate(stages):
                            if s.name == next_stage:
                                current_idx = i
                                continue

            current_idx += 1

    async def _execute_parallel(
        self,
        pipeline: Pipeline,
        context: PipelineContext,
        result: PipelineResult
    ) -> None:
        """Execute stages in parallel."""
        stages = pipeline.get_stages()

        tasks = [
            self._executor.execute(stage, context)
            for stage in stages
        ]

        stage_results = await asyncio.gather(*tasks, return_exceptions=True)

        for sr in stage_results:
            if isinstance(sr, Exception):
                result.stage_results.append(StageResult(
                    status=StageStatus.FAILED,
                    error=str(sr)
                ))
            else:
                result.stage_results.append(sr)

    # -------------------------------------------------------------------------
    # CANCELLATION
    # -------------------------------------------------------------------------

    def cancel(self, pipeline_id: str) -> bool:
        """Cancel running pipeline."""
        with self._lock:
            if pipeline_id in self._running:
                self._running[pipeline_id] = False
                return True
            return False

    def is_running(self, pipeline_id: str) -> bool:
        """Check if pipeline is running."""
        with self._lock:
            return self._running.get(pipeline_id, False)

    # -------------------------------------------------------------------------
    # RESULTS
    # -------------------------------------------------------------------------

    def get_results(
        self,
        pipeline_id: str,
        limit: int = 10
    ) -> List[PipelineResult]:
        """Get pipeline results."""
        with self._lock:
            results = self._results.get(pipeline_id, [])
            return results[-limit:]

    def get_last_result(
        self,
        pipeline_id: str
    ) -> Optional[PipelineResult]:
        """Get last pipeline result."""
        results = self.get_results(pipeline_id, 1)
        return results[0] if results else None

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def _update_stats(
        self,
        pipeline_id: str,
        result: PipelineResult
    ) -> None:
        """Update pipeline stats."""
        stats = self._stats[pipeline_id]
        stats.total_runs += 1

        if result.status == PipelineStatus.SUCCESS:
            stats.successful_runs += 1
        elif result.status == PipelineStatus.FAILED:
            stats.failed_runs += 1

        stats.stages_executed += len(result.stage_results)

        for sr in result.stage_results:
            stats.total_retries += sr.retries

        # Update average duration
        all_results = self._results.get(pipeline_id, [])
        if all_results:
            total_duration = sum(r.duration_ms for r in all_results)
            stats.avg_duration_ms = total_duration / len(all_results)

    def get_stats(
        self,
        pipeline_id: str
    ) -> PipelineStats:
        """Get pipeline stats."""
        with self._lock:
            return copy.copy(self._stats.get(pipeline_id, PipelineStats()))

    # -------------------------------------------------------------------------
    # BUILDERS
    # -------------------------------------------------------------------------

    def function_stage(
        self,
        name: str,
        func: Callable[[PipelineContext], Any],
        **kwargs
    ) -> FunctionStage:
        """Create function stage."""
        config = StageConfig(name=name, **kwargs)
        return FunctionStage(name, func, config)

    def map_stage(
        self,
        name: str,
        func: Callable[[Any], Any],
        input_key: str = "items",
        output_key: str = "mapped",
        **kwargs
    ) -> MapStage:
        """Create map stage."""
        config = StageConfig(name=name, **kwargs)
        return MapStage(name, func, input_key, output_key, config)

    def filter_stage(
        self,
        name: str,
        predicate: Callable[[Any], bool],
        input_key: str = "items",
        output_key: str = "filtered",
        **kwargs
    ) -> FilterStage:
        """Create filter stage."""
        config = StageConfig(name=name, **kwargs)
        return FilterStage(name, predicate, input_key, output_key, config)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Pipeline Manager."""
    print("=" * 70)
    print("BAEL - PIPELINE MANAGER DEMO")
    print("Advanced Data Pipeline Management for AI Agents")
    print("=" * 70)
    print()

    manager = PipelineManager()

    # 1. Create Simple Pipeline
    print("1. CREATE SIMPLE PIPELINE:")
    print("-" * 40)

    pipeline = manager.create_pipeline("data_processing")

    # Add stages
    pipeline.add_stage(FunctionStage(
        "load_data",
        lambda ctx: ctx.data.update({"items": [1, 2, 3, 4, 5]}) or "loaded"
    ))

    pipeline.add_stage(MapStage(
        "double",
        lambda x: x * 2,
        input_key="items",
        output_key="doubled"
    ))

    pipeline.add_stage(FilterStage(
        "filter_even",
        lambda x: x % 4 == 0,
        input_key="doubled",
        output_key="filtered"
    ))

    pipeline.add_stage(ReduceStage(
        "sum",
        lambda a, b: a + b,
        initial=0,
        input_key="filtered",
        output_key="total"
    ))

    print(f"   Pipeline: {pipeline.name}")
    print(f"   Stages: {len(pipeline.get_stages())}")
    print()

    # 2. Execute Pipeline
    print("2. EXECUTE PIPELINE:")
    print("-" * 40)

    result = await manager.execute(pipeline.pipeline_id)

    print(f"   Status: {result.status.value}")
    print(f"   Duration: {result.duration_ms:.2f} ms")
    print(f"   Output: {result.output}")
    print()

    # 3. Stage Results
    print("3. STAGE RESULTS:")
    print("-" * 40)

    for sr in result.stage_results:
        print(f"   {sr.stage_name}: {sr.status.value} ({sr.duration_ms:.2f} ms)")
    print()

    # 4. Pipeline with Retry
    print("4. PIPELINE WITH RETRY:")
    print("-" * 40)

    retry_pipeline = manager.create_pipeline("retry_test")

    attempt_count = {"count": 0}

    def flaky_func(ctx):
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise Exception("Flaky error")
        return "success"

    retry_pipeline.add_stage(FunctionStage(
        "flaky_stage",
        flaky_func,
        StageConfig(
            name="flaky_stage",
            retry_count=5,
            retry_delay_seconds=0.1,
            retry_strategy=RetryStrategy.FIXED
        )
    ))

    result = await manager.execute(retry_pipeline.pipeline_id)

    print(f"   Status: {result.status.value}")
    print(f"   Retries: {result.stage_results[0].retries}")
    print()

    # 5. Parallel Pipeline
    print("5. PARALLEL PIPELINE:")
    print("-" * 40)

    parallel_pipeline = manager.create_pipeline(
        "parallel_tasks",
        ExecutionMode.PARALLEL
    )

    async def slow_task(ctx, name, delay):
        await asyncio.sleep(delay)
        return f"{name} done"

    parallel_pipeline.add_stage(FunctionStage(
        "task_a",
        lambda ctx: asyncio.create_task(slow_task(ctx, "A", 0.1))
    ))

    parallel_pipeline.add_stage(FunctionStage(
        "task_b",
        lambda ctx: asyncio.create_task(slow_task(ctx, "B", 0.1))
    ))

    parallel_pipeline.add_stage(FunctionStage(
        "task_c",
        lambda ctx: asyncio.create_task(slow_task(ctx, "C", 0.1))
    ))

    result = await manager.execute(parallel_pipeline.pipeline_id)

    print(f"   Status: {result.status.value}")
    print(f"   Duration: {result.duration_ms:.2f} ms")
    print(f"   Stages: {len(result.stage_results)}")
    print()

    # 6. Conditional Stage
    print("6. CONDITIONAL STAGE:")
    print("-" * 40)

    cond_pipeline = manager.create_pipeline("conditional")

    cond_pipeline.add_stage(FunctionStage(
        "check",
        lambda ctx: ctx.data.get("value", 0)
    ))

    cond_pipeline.add_stage(FunctionStage(
        "if_positive",
        lambda ctx: "positive!",
        StageConfig(
            name="if_positive",
            condition=lambda data: data.get("value", 0) > 0
        )
    ))

    cond_pipeline.add_stage(FunctionStage(
        "if_negative",
        lambda ctx: "negative!",
        StageConfig(
            name="if_negative",
            condition=lambda data: data.get("value", 0) < 0
        )
    ))

    result = await manager.execute(
        cond_pipeline.pipeline_id,
        data={"value": 10}
    )

    print(f"   With value=10:")
    for sr in result.stage_results:
        print(f"   - {sr.stage_name}: {sr.status.value}")
    print()

    # 7. Get Results
    print("7. GET RESULTS:")
    print("-" * 40)

    results = manager.get_results(pipeline.pipeline_id)

    print(f"   Results for {pipeline.name}: {len(results)}")

    last = manager.get_last_result(pipeline.pipeline_id)
    if last:
        print(f"   Last run: {last.status.value}")
    print()

    # 8. Statistics
    print("8. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats(pipeline.pipeline_id)

    print(f"   Total runs: {stats.total_runs}")
    print(f"   Successful: {stats.successful_runs}")
    print(f"   Failed: {stats.failed_runs}")
    print(f"   Avg duration: {stats.avg_duration_ms:.2f} ms")
    print()

    # 9. List Pipelines
    print("9. LIST PIPELINES:")
    print("-" * 40)

    pipelines = manager.list_pipelines()

    for p in pipelines:
        print(f"   {p.name}: {len(p.get_stages())} stages, {p.mode.value}")
    print()

    # 10. Lambda Stage
    print("10. LAMBDA STAGE:")
    print("-" * 40)

    lambda_pipeline = manager.create_pipeline("lambda_demo")

    lambda_pipeline.add_stage(FunctionStage(
        "init",
        lambda ctx: ctx.data.update({"input": [1, 2, 3]})
    ))

    lambda_pipeline.add_stage(LambdaStage(
        "transform",
        lambda x: [v ** 2 for v in x] if x else [],
        input_key="input",
        output_key="squared"
    ))

    result = await manager.execute(lambda_pipeline.pipeline_id)

    print(f"   Output: {result.output}")
    print()

    # 11. Delete Pipeline
    print("11. DELETE PIPELINE:")
    print("-" * 40)

    count_before = len(manager.list_pipelines())
    deleted = manager.delete_pipeline(lambda_pipeline.pipeline_id)
    count_after = len(manager.list_pipelines())

    print(f"   Deleted: {deleted}")
    print(f"   Pipelines: {count_before} -> {count_after}")
    print()

    # 12. Builder Methods
    print("12. BUILDER METHODS:")
    print("-" * 40)

    built_pipeline = manager.create_pipeline("built")

    built_pipeline.add_stage(
        manager.function_stage("load", lambda ctx: ctx.data.update({"items": [1, 2, 3, 4, 5]}))
    )

    built_pipeline.add_stage(
        manager.map_stage("triple", lambda x: x * 3)
    )

    built_pipeline.add_stage(
        manager.filter_stage("big", lambda x: x > 10)
    )

    result = await manager.execute(built_pipeline.pipeline_id)

    print(f"   Status: {result.status.value}")
    print(f"   Output: {result.output}")
    print()

    # 13. Timeout Stage
    print("13. TIMEOUT STAGE:")
    print("-" * 40)

    timeout_pipeline = manager.create_pipeline("timeout_test")

    async def slow_stage(ctx):
        await asyncio.sleep(2)
        return "done"

    timeout_pipeline.add_stage(FunctionStage(
        "slow",
        slow_stage,
        StageConfig(
            name="slow",
            timeout_seconds=0.1
        )
    ))

    result = await manager.execute(timeout_pipeline.pipeline_id)

    print(f"   Status: {result.status.value}")
    if result.stage_results:
        print(f"   Error: {result.stage_results[0].error}")
    print()

    # 14. Check Running
    print("14. CHECK RUNNING:")
    print("-" * 40)

    print(f"   Pipeline running: {manager.is_running(pipeline.pipeline_id)}")
    print()

    # 15. Execution Order
    print("15. EXECUTION ORDER:")
    print("-" * 40)

    order = pipeline.get_execution_order()

    for i, stage in enumerate(order):
        print(f"   {i+1}. {stage.name}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Pipeline Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
