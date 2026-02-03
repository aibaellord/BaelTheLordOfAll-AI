#!/usr/bin/env python3
"""
BAEL - Chain Manager
Advanced LLM chain orchestration for complex AI workflows.

Features:
- Sequential chains
- Parallel chains
- Conditional branching
- Chain composition
- Error handling
- Retry logic
- Chain caching
- Observability
"""

import asyncio
import copy
import hashlib
import json
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')


# =============================================================================
# ENUMS
# =============================================================================

class ChainType(Enum):
    """Chain types."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    MAP_REDUCE = "map_reduce"
    ROUTER = "router"


class ChainStatus(Enum):
    """Chain execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RetryStrategy(Enum):
    """Retry strategies."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class BranchCondition(Enum):
    """Branch condition types."""
    EQUALS = "equals"
    CONTAINS = "contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    REGEX = "regex"
    CUSTOM = "custom"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ChainInput:
    """Chain input data."""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChainOutput:
    """Chain output data."""
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


@dataclass
class StepResult:
    """Result of a chain step."""
    step_id: str
    step_name: str
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    retries: int = 0


@dataclass
class ChainConfig:
    """Chain configuration."""
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    timeout: float = 300.0
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    cache_enabled: bool = False
    cache_ttl: int = 3600


@dataclass
class ExecutionContext:
    """Chain execution context."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chain_id: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    variables: Dict[str, Any] = field(default_factory=dict)
    step_results: List[StepResult] = field(default_factory=list)
    status: ChainStatus = ChainStatus.PENDING


@dataclass
class ChainStats:
    """Chain statistics."""
    total_executions: int = 0
    successful: int = 0
    failed: int = 0
    avg_duration: float = 0.0
    total_retries: int = 0


# =============================================================================
# CHAIN STEP
# =============================================================================

class ChainStep(ABC):
    """Abstract chain step."""

    def __init__(self, name: str):
        self.step_id = str(uuid.uuid4())
        self.name = name

    @abstractmethod
    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> Any:
        """Execute step."""
        pass


class FunctionStep(ChainStep):
    """Step that executes a function."""

    def __init__(
        self,
        name: str,
        func: Callable[[Any, ExecutionContext], Awaitable[Any]]
    ):
        super().__init__(name)
        self._func = func

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> Any:
        """Execute function."""
        return await self._func(input_data, context)


class SyncFunctionStep(ChainStep):
    """Step that executes a sync function."""

    def __init__(
        self,
        name: str,
        func: Callable[[Any, ExecutionContext], Any]
    ):
        super().__init__(name)
        self._func = func

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> Any:
        """Execute sync function."""
        return self._func(input_data, context)


class TransformStep(ChainStep):
    """Step that transforms data."""

    def __init__(
        self,
        name: str,
        transform: Callable[[Any], Any]
    ):
        super().__init__(name)
        self._transform = transform

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> Any:
        """Apply transformation."""
        return self._transform(input_data)


class PassthroughStep(ChainStep):
    """Step that passes data through unchanged."""

    def __init__(self, name: str = "passthrough"):
        super().__init__(name)

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> Any:
        """Pass through."""
        return input_data


# =============================================================================
# CHAIN TYPES
# =============================================================================

class Chain(ABC):
    """Abstract chain base."""

    def __init__(self, config: ChainConfig):
        self.config = config
        self._steps: List[ChainStep] = []

    @abstractmethod
    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> ChainOutput:
        """Execute chain."""
        pass

    def add_step(self, step: ChainStep) -> "Chain":
        """Add step to chain."""
        self._steps.append(step)
        return self

    def get_steps(self) -> List[ChainStep]:
        """Get chain steps."""
        return self._steps.copy()


class SequentialChain(Chain):
    """Chain that executes steps sequentially."""

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> ChainOutput:
        """Execute steps in sequence."""
        start_time = time.time()
        current_data = input_data

        try:
            for step in self._steps:
                step_start = time.time()

                result = await step.execute(current_data, context)

                step_result = StepResult(
                    step_id=step.step_id,
                    step_name=step.name,
                    output=result,
                    duration=time.time() - step_start
                )
                context.step_results.append(step_result)

                current_data = result

            return ChainOutput(
                result=current_data,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return ChainOutput(
                error=str(e),
                execution_time=time.time() - start_time
            )


class ParallelChain(Chain):
    """Chain that executes steps in parallel."""

    def __init__(self, config: ChainConfig, merge_strategy: str = "list"):
        super().__init__(config)
        self._merge_strategy = merge_strategy

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> ChainOutput:
        """Execute steps in parallel."""
        start_time = time.time()

        try:
            tasks = []
            for step in self._steps:
                task = asyncio.create_task(
                    self._execute_step(step, input_data, context)
                )
                tasks.append((step, task))

            results = []
            for step, task in tasks:
                result = await task
                results.append(result)

            # Merge results
            if self._merge_strategy == "dict":
                merged = {}
                for step, result in zip(self._steps, results):
                    merged[step.name] = result
            else:
                merged = results

            return ChainOutput(
                result=merged,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return ChainOutput(
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def _execute_step(
        self,
        step: ChainStep,
        input_data: Any,
        context: ExecutionContext
    ) -> Any:
        """Execute single step."""
        step_start = time.time()
        result = await step.execute(input_data, context)

        step_result = StepResult(
            step_id=step.step_id,
            step_name=step.name,
            output=result,
            duration=time.time() - step_start
        )
        context.step_results.append(step_result)

        return result


class ConditionalChain(Chain):
    """Chain with conditional branching."""

    def __init__(self, config: ChainConfig):
        super().__init__(config)
        self._branches: Dict[str, Tuple[Callable[[Any], bool], Chain]] = {}
        self._default: Optional[Chain] = None

    def add_branch(
        self,
        name: str,
        condition: Callable[[Any], bool],
        chain: Chain
    ) -> "ConditionalChain":
        """Add conditional branch."""
        self._branches[name] = (condition, chain)
        return self

    def set_default(self, chain: Chain) -> "ConditionalChain":
        """Set default branch."""
        self._default = chain
        return self

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> ChainOutput:
        """Execute matching branch."""
        start_time = time.time()

        try:
            # Find matching branch
            for name, (condition, chain) in self._branches.items():
                if condition(input_data):
                    context.variables["branch"] = name
                    result = await chain.execute(input_data, context)
                    result.execution_time = time.time() - start_time
                    return result

            # Use default
            if self._default:
                context.variables["branch"] = "default"
                result = await self._default.execute(input_data, context)
                result.execution_time = time.time() - start_time
                return result

            return ChainOutput(
                error="No matching branch found",
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return ChainOutput(
                error=str(e),
                execution_time=time.time() - start_time
            )


class MapReduceChain(Chain):
    """Chain for map-reduce operations."""

    def __init__(
        self,
        config: ChainConfig,
        map_step: ChainStep,
        reduce_step: ChainStep
    ):
        super().__init__(config)
        self._map_step = map_step
        self._reduce_step = reduce_step

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> ChainOutput:
        """Map over input, then reduce."""
        start_time = time.time()

        try:
            if not isinstance(input_data, (list, tuple)):
                input_data = [input_data]

            # Map phase
            map_tasks = []
            for item in input_data:
                task = asyncio.create_task(
                    self._map_step.execute(item, context)
                )
                map_tasks.append(task)

            mapped_results = await asyncio.gather(*map_tasks)

            # Reduce phase
            reduced = await self._reduce_step.execute(list(mapped_results), context)

            return ChainOutput(
                result=reduced,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return ChainOutput(
                error=str(e),
                execution_time=time.time() - start_time
            )


class RouterChain(Chain):
    """Chain that routes to different chains based on input."""

    def __init__(
        self,
        config: ChainConfig,
        router: Callable[[Any], str]
    ):
        super().__init__(config)
        self._router = router
        self._routes: Dict[str, Chain] = {}

    def add_route(self, route_name: str, chain: Chain) -> "RouterChain":
        """Add route."""
        self._routes[route_name] = chain
        return self

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> ChainOutput:
        """Route and execute."""
        start_time = time.time()

        try:
            route = self._router(input_data)
            context.variables["route"] = route

            if route not in self._routes:
                return ChainOutput(
                    error=f"Route not found: {route}",
                    execution_time=time.time() - start_time
                )

            chain = self._routes[route]
            result = await chain.execute(input_data, context)
            result.execution_time = time.time() - start_time
            return result

        except Exception as e:
            return ChainOutput(
                error=str(e),
                execution_time=time.time() - start_time
            )


# =============================================================================
# CHAIN EXECUTOR
# =============================================================================

class ChainExecutor:
    """Execute chains with retry and error handling."""

    def __init__(self):
        self._retry_delays = {
            RetryStrategy.FIXED: lambda n: 1.0,
            RetryStrategy.LINEAR: lambda n: n * 1.0,
            RetryStrategy.EXPONENTIAL: lambda n: 2 ** n * 0.5,
        }

    async def execute(
        self,
        chain: Chain,
        input_data: Any,
        context: Optional[ExecutionContext] = None
    ) -> ChainOutput:
        """Execute chain with retries."""
        if context is None:
            context = ExecutionContext(chain_id=chain.config.chain_id)

        context.status = ChainStatus.RUNNING

        retries = 0
        last_error = None

        while retries <= chain.config.max_retries:
            try:
                result = await asyncio.wait_for(
                    chain.execute(input_data, context),
                    timeout=chain.config.timeout
                )

                if result.error is None:
                    context.status = ChainStatus.COMPLETED
                    return result

                last_error = result.error

            except asyncio.TimeoutError:
                last_error = "Chain execution timed out"
            except Exception as e:
                last_error = str(e)

            retries += 1

            if retries <= chain.config.max_retries:
                delay = self._get_delay(chain.config.retry_strategy, retries)
                await asyncio.sleep(delay)

        context.status = ChainStatus.FAILED
        return ChainOutput(error=last_error)

    def _get_delay(self, strategy: RetryStrategy, retry_num: int) -> float:
        """Get retry delay."""
        delay_func = self._retry_delays.get(strategy, lambda n: 1.0)
        return delay_func(retry_num)


# =============================================================================
# CHAIN CACHE
# =============================================================================

class ChainCache:
    """Cache chain results."""

    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl

    def _make_key(self, chain_id: str, input_data: Any) -> str:
        """Make cache key."""
        input_hash = hashlib.md5(
            json.dumps(input_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        return f"{chain_id}:{input_hash}"

    def get(self, chain_id: str, input_data: Any) -> Optional[Any]:
        """Get cached result."""
        key = self._make_key(chain_id, input_data)

        if key in self._cache:
            result, expires_at = self._cache[key]
            if datetime.now() < expires_at:
                return result
            del self._cache[key]

        return None

    def set(
        self,
        chain_id: str,
        input_data: Any,
        result: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Cache result."""
        key = self._make_key(chain_id, input_data)
        expires_at = datetime.now() + timedelta(seconds=ttl or self._default_ttl)
        self._cache[key] = (result, expires_at)

    def invalidate(self, chain_id: str) -> int:
        """Invalidate chain cache."""
        prefix = f"{chain_id}:"
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)

    def clear(self) -> int:
        """Clear all cache."""
        count = len(self._cache)
        self._cache.clear()
        return count


# =============================================================================
# CHAIN BUILDER
# =============================================================================

class ChainBuilder:
    """Fluent chain builder."""

    def __init__(self, name: str = ""):
        self._config = ChainConfig(name=name)
        self._steps: List[ChainStep] = []
        self._chain_type = ChainType.SEQUENTIAL
        self._branches: Dict[str, Tuple[Callable[[Any], bool], Chain]] = {}
        self._default_branch: Optional[Chain] = None

    def with_timeout(self, seconds: float) -> "ChainBuilder":
        """Set timeout."""
        self._config.timeout = seconds
        return self

    def with_retries(
        self,
        max_retries: int,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    ) -> "ChainBuilder":
        """Set retry policy."""
        self._config.max_retries = max_retries
        self._config.retry_strategy = strategy
        return self

    def with_cache(self, ttl: int = 3600) -> "ChainBuilder":
        """Enable caching."""
        self._config.cache_enabled = True
        self._config.cache_ttl = ttl
        return self

    def add_step(self, step: ChainStep) -> "ChainBuilder":
        """Add step."""
        self._steps.append(step)
        return self

    def add_function(
        self,
        name: str,
        func: Callable[[Any, ExecutionContext], Awaitable[Any]]
    ) -> "ChainBuilder":
        """Add async function step."""
        self._steps.append(FunctionStep(name, func))
        return self

    def add_transform(
        self,
        name: str,
        transform: Callable[[Any], Any]
    ) -> "ChainBuilder":
        """Add transform step."""
        self._steps.append(TransformStep(name, transform))
        return self

    def parallel(self, merge_strategy: str = "list") -> "ChainBuilder":
        """Set parallel execution."""
        self._chain_type = ChainType.PARALLEL
        return self

    def add_branch(
        self,
        name: str,
        condition: Callable[[Any], bool],
        chain: Chain
    ) -> "ChainBuilder":
        """Add conditional branch."""
        self._chain_type = ChainType.CONDITIONAL
        self._branches[name] = (condition, chain)
        return self

    def set_default_branch(self, chain: Chain) -> "ChainBuilder":
        """Set default branch."""
        self._default_branch = chain
        return self

    def build(self) -> Chain:
        """Build chain."""
        if self._chain_type == ChainType.SEQUENTIAL:
            chain = SequentialChain(self._config)
        elif self._chain_type == ChainType.PARALLEL:
            chain = ParallelChain(self._config)
        elif self._chain_type == ChainType.CONDITIONAL:
            chain = ConditionalChain(self._config)
            for name, (condition, branch) in self._branches.items():
                chain.add_branch(name, condition, branch)
            if self._default_branch:
                chain.set_default(self._default_branch)
            return chain
        else:
            chain = SequentialChain(self._config)

        for step in self._steps:
            chain.add_step(step)

        return chain


# =============================================================================
# CHAIN MANAGER
# =============================================================================

class ChainManager:
    """
    Chain Manager for BAEL.

    Advanced LLM chain orchestration.
    """

    def __init__(self):
        self._chains: Dict[str, Chain] = {}
        self._executor = ChainExecutor()
        self._cache = ChainCache()
        self._stats: Dict[str, ChainStats] = defaultdict(ChainStats)
        self._executions: Dict[str, ExecutionContext] = {}

    # -------------------------------------------------------------------------
    # CHAIN MANAGEMENT
    # -------------------------------------------------------------------------

    def register(self, chain: Chain) -> str:
        """Register chain."""
        self._chains[chain.config.chain_id] = chain
        return chain.config.chain_id

    def get(self, chain_id: str) -> Optional[Chain]:
        """Get chain by ID."""
        return self._chains.get(chain_id)

    def get_by_name(self, name: str) -> Optional[Chain]:
        """Get chain by name."""
        for chain in self._chains.values():
            if chain.config.name == name:
                return chain
        return None

    def unregister(self, chain_id: str) -> bool:
        """Unregister chain."""
        if chain_id in self._chains:
            del self._chains[chain_id]
            return True
        return False

    def list_chains(self) -> List[ChainConfig]:
        """List all chains."""
        return [c.config for c in self._chains.values()]

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def execute(
        self,
        chain_id: str,
        input_data: Any,
        use_cache: bool = True
    ) -> ChainOutput:
        """Execute chain."""
        chain = self._chains.get(chain_id)
        if not chain:
            return ChainOutput(error=f"Chain not found: {chain_id}")

        # Check cache
        if use_cache and chain.config.cache_enabled:
            cached = self._cache.get(chain_id, input_data)
            if cached is not None:
                return ChainOutput(result=cached)

        # Execute
        context = ExecutionContext(chain_id=chain_id)
        self._executions[context.execution_id] = context

        start_time = time.time()
        result = await self._executor.execute(chain, input_data, context)
        duration = time.time() - start_time

        # Update stats
        stats = self._stats[chain_id]
        stats.total_executions += 1
        if result.error is None:
            stats.successful += 1
            stats.avg_duration = (
                (stats.avg_duration * (stats.successful - 1) + duration) /
                stats.successful
            )

            # Cache result
            if use_cache and chain.config.cache_enabled:
                self._cache.set(
                    chain_id,
                    input_data,
                    result.result,
                    chain.config.cache_ttl
                )
        else:
            stats.failed += 1

        return result

    async def execute_by_name(
        self,
        name: str,
        input_data: Any
    ) -> ChainOutput:
        """Execute chain by name."""
        chain = self.get_by_name(name)
        if not chain:
            return ChainOutput(error=f"Chain not found: {name}")

        return await self.execute(chain.config.chain_id, input_data)

    # -------------------------------------------------------------------------
    # CHAIN BUILDING
    # -------------------------------------------------------------------------

    def builder(self, name: str = "") -> ChainBuilder:
        """Get chain builder."""
        return ChainBuilder(name)

    def create_sequential(self, name: str) -> Chain:
        """Create sequential chain."""
        config = ChainConfig(name=name)
        chain = SequentialChain(config)
        self.register(chain)
        return chain

    def create_parallel(
        self,
        name: str,
        merge_strategy: str = "list"
    ) -> ParallelChain:
        """Create parallel chain."""
        config = ChainConfig(name=name)
        chain = ParallelChain(config, merge_strategy)
        self.register(chain)
        return chain

    def create_conditional(self, name: str) -> ConditionalChain:
        """Create conditional chain."""
        config = ChainConfig(name=name)
        chain = ConditionalChain(config)
        self.register(chain)
        return chain

    def create_map_reduce(
        self,
        name: str,
        map_step: ChainStep,
        reduce_step: ChainStep
    ) -> MapReduceChain:
        """Create map-reduce chain."""
        config = ChainConfig(name=name)
        chain = MapReduceChain(config, map_step, reduce_step)
        self.register(chain)
        return chain

    def create_router(
        self,
        name: str,
        router: Callable[[Any], str]
    ) -> RouterChain:
        """Create router chain."""
        config = ChainConfig(name=name)
        chain = RouterChain(config, router)
        self.register(chain)
        return chain

    # -------------------------------------------------------------------------
    # CHAIN COMPOSITION
    # -------------------------------------------------------------------------

    def compose(
        self,
        name: str,
        chains: List[Chain]
    ) -> SequentialChain:
        """Compose chains sequentially."""
        config = ChainConfig(name=name)
        composed = SequentialChain(config)

        for chain in chains:
            # Wrap chain as step
            step = ChainWrapperStep(chain)
            composed.add_step(step)

        self.register(composed)
        return composed

    def merge(
        self,
        name: str,
        chains: List[Chain],
        merge_strategy: str = "dict"
    ) -> ParallelChain:
        """Merge chains in parallel."""
        config = ChainConfig(name=name)
        merged = ParallelChain(config, merge_strategy)

        for chain in chains:
            step = ChainWrapperStep(chain)
            merged.add_step(step)

        self.register(merged)
        return merged

    # -------------------------------------------------------------------------
    # CACHE
    # -------------------------------------------------------------------------

    def invalidate_cache(self, chain_id: str) -> int:
        """Invalidate chain cache."""
        return self._cache.invalidate(chain_id)

    def clear_cache(self) -> int:
        """Clear all cache."""
        return self._cache.clear()

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def get_stats(self, chain_id: str) -> ChainStats:
        """Get chain stats."""
        return self._stats.get(chain_id, ChainStats())

    def get_execution(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get execution context."""
        return self._executions.get(execution_id)


# =============================================================================
# CHAIN WRAPPER STEP
# =============================================================================

class ChainWrapperStep(ChainStep):
    """Wrap a chain as a step."""

    def __init__(self, chain: Chain):
        super().__init__(chain.config.name)
        self._chain = chain

    async def execute(
        self,
        input_data: Any,
        context: ExecutionContext
    ) -> Any:
        """Execute wrapped chain."""
        result = await self._chain.execute(input_data, context)
        if result.error:
            raise Exception(result.error)
        return result.result


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Chain Manager."""
    print("=" * 70)
    print("BAEL - CHAIN MANAGER DEMO")
    print("Advanced LLM Chain Orchestration")
    print("=" * 70)
    print()

    manager = ChainManager()

    # 1. Sequential Chain
    print("1. SEQUENTIAL CHAIN:")
    print("-" * 40)

    async def step1(data: Any, ctx: ExecutionContext) -> str:
        return f"Step1: {data}"

    async def step2(data: Any, ctx: ExecutionContext) -> str:
        return f"Step2: {data}"

    chain1 = (manager.builder("sequential_demo")
        .add_function("step1", step1)
        .add_function("step2", step2)
        .build())

    manager.register(chain1)
    result = await manager.execute(chain1.config.chain_id, "hello")

    print(f"   Input: 'hello'")
    print(f"   Output: '{result.result}'")
    print(f"   Time: {result.execution_time:.4f}s")
    print()

    # 2. Transform Steps
    print("2. TRANSFORM STEPS:")
    print("-" * 40)

    chain2 = (manager.builder("transform_demo")
        .add_transform("uppercase", lambda x: x.upper())
        .add_transform("add_prefix", lambda x: f"RESULT: {x}")
        .build())

    manager.register(chain2)
    result = await manager.execute(chain2.config.chain_id, "test")

    print(f"   Input: 'test'")
    print(f"   Output: '{result.result}'")
    print()

    # 3. Parallel Chain
    print("3. PARALLEL CHAIN:")
    print("-" * 40)

    async def task_a(data: Any, ctx: ExecutionContext) -> str:
        await asyncio.sleep(0.1)
        return f"A: {data}"

    async def task_b(data: Any, ctx: ExecutionContext) -> str:
        await asyncio.sleep(0.1)
        return f"B: {data}"

    async def task_c(data: Any, ctx: ExecutionContext) -> str:
        await asyncio.sleep(0.1)
        return f"C: {data}"

    parallel = manager.create_parallel("parallel_demo", merge_strategy="dict")
    parallel.add_step(FunctionStep("task_a", task_a))
    parallel.add_step(FunctionStep("task_b", task_b))
    parallel.add_step(FunctionStep("task_c", task_c))

    result = await manager.execute(parallel.config.chain_id, "input")

    print(f"   Input: 'input'")
    print(f"   Output: {result.result}")
    print(f"   Time: {result.execution_time:.4f}s (parallel)")
    print()

    # 4. Conditional Chain
    print("4. CONDITIONAL CHAIN:")
    print("-" * 40)

    small_chain = (manager.builder("small_handler")
        .add_transform("handle", lambda x: f"Small: {x}")
        .build())

    large_chain = (manager.builder("large_handler")
        .add_transform("handle", lambda x: f"Large: {x}")
        .build())

    conditional = manager.create_conditional("conditional_demo")
    conditional.add_branch(
        "small",
        lambda x: isinstance(x, int) and x < 10,
        small_chain
    )
    conditional.add_branch(
        "large",
        lambda x: isinstance(x, int) and x >= 10,
        large_chain
    )

    result1 = await manager.execute(conditional.config.chain_id, 5)
    result2 = await manager.execute(conditional.config.chain_id, 100)

    print(f"   Input: 5 -> Output: '{result1.result}'")
    print(f"   Input: 100 -> Output: '{result2.result}'")
    print()

    # 5. Map-Reduce Chain
    print("5. MAP-REDUCE CHAIN:")
    print("-" * 40)

    map_step = TransformStep("square", lambda x: x * x)
    reduce_step = TransformStep("sum", lambda x: sum(x))

    mr_chain = manager.create_map_reduce("mapreduce_demo", map_step, reduce_step)

    result = await manager.execute(mr_chain.config.chain_id, [1, 2, 3, 4, 5])

    print(f"   Input: [1, 2, 3, 4, 5]")
    print(f"   Map: square each")
    print(f"   Reduce: sum")
    print(f"   Output: {result.result}")
    print()

    # 6. Router Chain
    print("6. ROUTER CHAIN:")
    print("-" * 40)

    def route_by_type(data: Any) -> str:
        if isinstance(data, str):
            return "string"
        elif isinstance(data, int):
            return "number"
        return "other"

    string_handler = (manager.builder("string_handler")
        .add_transform("handle", lambda x: f"String: {x.upper()}")
        .build())

    number_handler = (manager.builder("number_handler")
        .add_transform("handle", lambda x: f"Number: {x * 2}")
        .build())

    router = manager.create_router("router_demo", route_by_type)
    router.add_route("string", string_handler)
    router.add_route("number", number_handler)

    result1 = await manager.execute(router.config.chain_id, "hello")
    result2 = await manager.execute(router.config.chain_id, 42)

    print(f"   Input: 'hello' -> '{result1.result}'")
    print(f"   Input: 42 -> '{result2.result}'")
    print()

    # 7. Chain Composition
    print("7. CHAIN COMPOSITION:")
    print("-" * 40)

    chain_a = (manager.builder("chain_a")
        .add_transform("a", lambda x: x + 1)
        .build())

    chain_b = (manager.builder("chain_b")
        .add_transform("b", lambda x: x * 2)
        .build())

    composed = manager.compose("composed_chain", [chain_a, chain_b])
    result = await manager.execute(composed.config.chain_id, 5)

    print(f"   Input: 5")
    print(f"   Chain A: +1")
    print(f"   Chain B: *2")
    print(f"   Output: {result.result}")
    print()

    # 8. Retry Logic
    print("8. RETRY LOGIC:")
    print("-" * 40)

    attempt_count = [0]

    async def flaky_step(data: Any, ctx: ExecutionContext) -> str:
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise Exception("Simulated failure")
        return f"Success on attempt {attempt_count[0]}"

    retry_chain = (manager.builder("retry_demo")
        .with_retries(5, RetryStrategy.EXPONENTIAL)
        .add_function("flaky", flaky_step)
        .build())

    manager.register(retry_chain)
    result = await manager.execute(retry_chain.config.chain_id, "test")

    print(f"   Attempts: {attempt_count[0]}")
    print(f"   Result: '{result.result}'")
    print()

    # 9. Caching
    print("9. CHAIN CACHING:")
    print("-" * 40)

    call_count = [0]

    async def expensive_step(data: Any, ctx: ExecutionContext) -> str:
        call_count[0] += 1
        await asyncio.sleep(0.1)
        return f"Result for {data}"

    cached_chain = (manager.builder("cached_demo")
        .with_cache(ttl=60)
        .add_function("expensive", expensive_step)
        .build())

    manager.register(cached_chain)

    # First call
    result1 = await manager.execute(cached_chain.config.chain_id, "input1")
    # Second call (cached)
    result2 = await manager.execute(cached_chain.config.chain_id, "input1")

    print(f"   Call count: {call_count[0]} (second was cached)")
    print(f"   First result: '{result1.result}'")
    print(f"   Second result: '{result2.result}'")
    print()

    # 10. Stats
    print("10. CHAIN STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats(chain1.config.chain_id)
    print(f"   Chain: {chain1.config.name}")
    print(f"   Total executions: {stats.total_executions}")
    print(f"   Successful: {stats.successful}")
    print(f"   Failed: {stats.failed}")
    print()

    # 11. List Chains
    print("11. REGISTERED CHAINS:")
    print("-" * 40)

    chains = manager.list_chains()
    print(f"   Total chains: {len(chains)}")
    for config in chains[:5]:
        print(f"     - {config.name or config.chain_id[:8]}")
    print()

    # 12. Chain Builder Fluent API
    print("12. FLUENT BUILDER API:")
    print("-" * 40)

    fluent_chain = (manager.builder("fluent_demo")
        .with_timeout(30.0)
        .with_retries(3, RetryStrategy.LINEAR)
        .add_transform("step1", lambda x: x.upper())
        .add_transform("step2", lambda x: f"[{x}]")
        .add_transform("step3", lambda x: f"Final: {x}")
        .build())

    manager.register(fluent_chain)
    result = await manager.execute(fluent_chain.config.chain_id, "hello")

    print(f"   Input: 'hello'")
    print(f"   Output: '{result.result}'")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Chain Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
