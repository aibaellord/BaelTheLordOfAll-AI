#!/usr/bin/env python3
"""
BAEL - Chain Engine
LLM chain orchestration.

Features:
- Sequential chains
- Parallel chains
- Conditional branching
- Memory integration
- Chain composition
"""

import asyncio
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ChainType(Enum):
    """Types of chains."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ROUTER = "router"
    MAP_REDUCE = "map_reduce"
    TRANSFORM = "transform"


class StepStatus(Enum):
    """Step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ChainStatus(Enum):
    """Chain execution status."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputMode(Enum):
    """Output handling modes."""
    LAST = "last"
    ALL = "all"
    MERGE = "merge"
    FIRST = "first"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ChainInput:
    """Chain input."""
    input_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.input_id:
            self.input_id = str(uuid.uuid4())[:8]


@dataclass
class ChainOutput:
    """Chain output."""
    output_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    step_outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.output_id:
            self.output_id = str(uuid.uuid4())[:8]


@dataclass
class StepConfig:
    """Step configuration."""
    step_id: str = ""
    name: str = ""
    step_type: str = "transform"
    config: Dict[str, Any] = field(default_factory=dict)
    input_keys: List[str] = field(default_factory=list)
    output_key: str = ""

    def __post_init__(self):
        if not self.step_id:
            self.step_id = str(uuid.uuid4())[:8]


@dataclass
class StepResult:
    """Step execution result."""
    step_id: str
    name: str
    status: StepStatus = StepStatus.PENDING
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ChainConfig:
    """Chain configuration."""
    chain_id: str = ""
    name: str = ""
    chain_type: ChainType = ChainType.SEQUENTIAL
    steps: List[StepConfig] = field(default_factory=list)
    output_mode: OutputMode = OutputMode.LAST
    max_retries: int = 3
    timeout_seconds: float = 300.0

    def __post_init__(self):
        if not self.chain_id:
            self.chain_id = str(uuid.uuid4())[:8]


@dataclass
class ChainRun:
    """Chain execution run."""
    run_id: str = ""
    chain_id: str = ""
    status: ChainStatus = ChainStatus.CREATED
    step_results: List[StepResult] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    error: Optional[str] = None

    def __post_init__(self):
        if not self.run_id:
            self.run_id = str(uuid.uuid4())[:8]


@dataclass
class ChainStats:
    """Chain statistics."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    avg_duration_ms: float = 0.0
    by_chain: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# BASE COMPONENTS
# =============================================================================

class BaseStep(ABC):
    """Abstract base step."""

    def __init__(self, config: StepConfig):
        self.config = config

    @property
    @abstractmethod
    def step_type(self) -> str:
        """Get step type."""
        pass

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> Any:
        """Execute the step."""
        pass


class TransformStep(BaseStep):
    """Data transformation step."""

    def __init__(self, config: StepConfig, transform_fn: Optional[Callable] = None):
        super().__init__(config)
        self._transform_fn = transform_fn

    @property
    def step_type(self) -> str:
        return "transform"

    async def execute(self, inputs: Dict[str, Any]) -> Any:
        """Execute transformation."""
        if self._transform_fn:
            return self._transform_fn(inputs)

        transform_type = self.config.config.get("transform", "identity")

        if transform_type == "identity":
            return inputs
        elif transform_type == "extract":
            key = self.config.config.get("key", "")
            return inputs.get(key)
        elif transform_type == "merge":
            return {**inputs}
        elif transform_type == "uppercase":
            text = inputs.get("text", "")
            return {"text": text.upper()}
        elif transform_type == "lowercase":
            text = inputs.get("text", "")
            return {"text": text.lower()}

        return inputs


class LLMStep(BaseStep):
    """LLM invocation step (simulated)."""

    @property
    def step_type(self) -> str:
        return "llm"

    async def execute(self, inputs: Dict[str, Any]) -> Any:
        """Execute LLM call (simulated)."""
        prompt = inputs.get("prompt", "")

        await asyncio.sleep(0.05)

        response = f"[LLM Response to: {prompt[:50]}...]"

        return {
            "response": response,
            "tokens_used": len(prompt.split()) * 2,
            "model": self.config.config.get("model", "gpt-4")
        }


class ConditionStep(BaseStep):
    """Conditional branching step."""

    @property
    def step_type(self) -> str:
        return "condition"

    async def execute(self, inputs: Dict[str, Any]) -> Any:
        """Evaluate condition."""
        condition_type = self.config.config.get("condition", "exists")
        key = self.config.config.get("key", "")
        value = self.config.config.get("value")

        if condition_type == "exists":
            result = key in inputs and inputs[key] is not None
        elif condition_type == "equals":
            result = inputs.get(key) == value
        elif condition_type == "contains":
            result = value in str(inputs.get(key, ""))
        elif condition_type == "greater_than":
            result = inputs.get(key, 0) > value
        elif condition_type == "less_than":
            result = inputs.get(key, 0) < value
        else:
            result = True

        return {"condition_result": result}


class RouterStep(BaseStep):
    """Route to different paths."""

    @property
    def step_type(self) -> str:
        return "router"

    async def execute(self, inputs: Dict[str, Any]) -> Any:
        """Route based on input."""
        routing_key = self.config.config.get("routing_key", "route")
        routes = self.config.config.get("routes", {})
        default_route = self.config.config.get("default", "default")

        route_value = inputs.get(routing_key, default_route)
        selected_route = routes.get(route_value, default_route)

        return {
            "selected_route": selected_route,
            "route_value": route_value
        }


class AggregateStep(BaseStep):
    """Aggregate results."""

    @property
    def step_type(self) -> str:
        return "aggregate"

    async def execute(self, inputs: Dict[str, Any]) -> Any:
        """Aggregate inputs."""
        aggregation_type = self.config.config.get("aggregation", "merge")
        items = inputs.get("items", [])

        if aggregation_type == "merge":
            result = {}
            for item in items:
                if isinstance(item, dict):
                    result.update(item)
            return result
        elif aggregation_type == "concat":
            texts = [str(item) for item in items]
            return {"text": "\n".join(texts)}
        elif aggregation_type == "sum":
            values = [item.get("value", 0) for item in items if isinstance(item, dict)]
            return {"sum": sum(values)}
        elif aggregation_type == "list":
            return {"items": items}

        return {"items": items}


# =============================================================================
# CHAIN EXECUTORS
# =============================================================================

class BaseChainExecutor(ABC):
    """Abstract chain executor."""

    @property
    @abstractmethod
    def chain_type(self) -> ChainType:
        """Get chain type."""
        pass

    @abstractmethod
    async def execute(
        self,
        config: ChainConfig,
        inputs: Dict[str, Any],
        steps: Dict[str, BaseStep]
    ) -> ChainRun:
        """Execute the chain."""
        pass


class SequentialExecutor(BaseChainExecutor):
    """Sequential chain executor."""

    @property
    def chain_type(self) -> ChainType:
        return ChainType.SEQUENTIAL

    async def execute(
        self,
        config: ChainConfig,
        inputs: Dict[str, Any],
        steps: Dict[str, BaseStep]
    ) -> ChainRun:
        """Execute steps sequentially."""
        run = ChainRun(
            chain_id=config.chain_id,
            input_data=inputs,
            status=ChainStatus.RUNNING,
            started_at=datetime.now()
        )

        current_data = inputs.copy()

        for step_config in config.steps:
            step = steps.get(step_config.step_id)
            if not step:
                continue

            step_result = StepResult(
                step_id=step_config.step_id,
                name=step_config.name,
                status=StepStatus.RUNNING,
                started_at=datetime.now()
            )

            try:
                start_time = time.time()

                step_inputs = {}
                if step_config.input_keys:
                    for key in step_config.input_keys:
                        if key in current_data:
                            step_inputs[key] = current_data[key]
                else:
                    step_inputs = current_data

                output = await step.execute(step_inputs)

                step_result.status = StepStatus.COMPLETED
                step_result.output = output
                step_result.duration_ms = (time.time() - start_time) * 1000
                step_result.completed_at = datetime.now()

                if step_config.output_key:
                    current_data[step_config.output_key] = output
                elif isinstance(output, dict):
                    current_data.update(output)

            except Exception as e:
                step_result.status = StepStatus.FAILED
                step_result.error = str(e)
                step_result.completed_at = datetime.now()

                run.status = ChainStatus.FAILED
                run.error = str(e)
                break

            run.step_results.append(step_result)

        if run.status != ChainStatus.FAILED:
            run.status = ChainStatus.COMPLETED

        run.output_data = current_data
        run.completed_at = datetime.now()
        run.duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000

        return run


class ParallelExecutor(BaseChainExecutor):
    """Parallel chain executor."""

    @property
    def chain_type(self) -> ChainType:
        return ChainType.PARALLEL

    async def execute(
        self,
        config: ChainConfig,
        inputs: Dict[str, Any],
        steps: Dict[str, BaseStep]
    ) -> ChainRun:
        """Execute steps in parallel."""
        run = ChainRun(
            chain_id=config.chain_id,
            input_data=inputs,
            status=ChainStatus.RUNNING,
            started_at=datetime.now()
        )

        async def execute_step(step_config: StepConfig) -> StepResult:
            step = steps.get(step_config.step_id)
            if not step:
                return StepResult(
                    step_id=step_config.step_id,
                    name=step_config.name,
                    status=StepStatus.SKIPPED
                )

            step_result = StepResult(
                step_id=step_config.step_id,
                name=step_config.name,
                status=StepStatus.RUNNING,
                started_at=datetime.now()
            )

            try:
                start_time = time.time()
                output = await step.execute(inputs)

                step_result.status = StepStatus.COMPLETED
                step_result.output = output
                step_result.duration_ms = (time.time() - start_time) * 1000
                step_result.completed_at = datetime.now()

            except Exception as e:
                step_result.status = StepStatus.FAILED
                step_result.error = str(e)
                step_result.completed_at = datetime.now()

            return step_result

        tasks = [execute_step(sc) for sc in config.steps]
        results = await asyncio.gather(*tasks)

        run.step_results = list(results)

        all_outputs = {}
        failed = False

        for i, (step_config, result) in enumerate(zip(config.steps, results)):
            if result.status == StepStatus.FAILED:
                failed = True

            if result.output:
                if step_config.output_key:
                    all_outputs[step_config.output_key] = result.output
                else:
                    all_outputs[f"step_{i}"] = result.output

        run.status = ChainStatus.FAILED if failed else ChainStatus.COMPLETED
        run.output_data = all_outputs
        run.completed_at = datetime.now()
        run.duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000

        return run


class ConditionalExecutor(BaseChainExecutor):
    """Conditional chain executor."""

    @property
    def chain_type(self) -> ChainType:
        return ChainType.CONDITIONAL

    async def execute(
        self,
        config: ChainConfig,
        inputs: Dict[str, Any],
        steps: Dict[str, BaseStep]
    ) -> ChainRun:
        """Execute with conditional branching."""
        run = ChainRun(
            chain_id=config.chain_id,
            input_data=inputs,
            status=ChainStatus.RUNNING,
            started_at=datetime.now()
        )

        current_data = inputs.copy()

        for step_config in config.steps:
            step = steps.get(step_config.step_id)
            if not step:
                continue

            if step.step_type == "condition":
                cond_result = await step.execute(current_data)
                condition_met = cond_result.get("condition_result", True)

                step_result = StepResult(
                    step_id=step_config.step_id,
                    name=step_config.name,
                    status=StepStatus.COMPLETED,
                    output=cond_result,
                    completed_at=datetime.now()
                )
                run.step_results.append(step_result)

                if not condition_met:
                    break
            else:
                step_result = StepResult(
                    step_id=step_config.step_id,
                    name=step_config.name,
                    status=StepStatus.RUNNING,
                    started_at=datetime.now()
                )

                try:
                    output = await step.execute(current_data)
                    step_result.status = StepStatus.COMPLETED
                    step_result.output = output
                    step_result.completed_at = datetime.now()

                    if isinstance(output, dict):
                        current_data.update(output)

                except Exception as e:
                    step_result.status = StepStatus.FAILED
                    step_result.error = str(e)
                    run.status = ChainStatus.FAILED
                    break

                run.step_results.append(step_result)

        if run.status != ChainStatus.FAILED:
            run.status = ChainStatus.COMPLETED

        run.output_data = current_data
        run.completed_at = datetime.now()
        run.duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000

        return run


class MapReduceExecutor(BaseChainExecutor):
    """Map-reduce chain executor."""

    @property
    def chain_type(self) -> ChainType:
        return ChainType.MAP_REDUCE

    async def execute(
        self,
        config: ChainConfig,
        inputs: Dict[str, Any],
        steps: Dict[str, BaseStep]
    ) -> ChainRun:
        """Execute map-reduce pattern."""
        run = ChainRun(
            chain_id=config.chain_id,
            input_data=inputs,
            status=ChainStatus.RUNNING,
            started_at=datetime.now()
        )

        items = inputs.get("items", [])

        map_step = None
        reduce_step = None

        for step_config in config.steps:
            step = steps.get(step_config.step_id)
            if step_config.config.get("role") == "map":
                map_step = step
            elif step_config.config.get("role") == "reduce":
                reduce_step = step

        if not map_step:
            map_step = TransformStep(StepConfig(name="identity_map"))

        if not reduce_step:
            reduce_step = AggregateStep(StepConfig(name="aggregate", config={"aggregation": "list"}))

        async def map_item(item):
            return await map_step.execute({"item": item})

        mapped_results = await asyncio.gather(*[map_item(item) for item in items])

        map_result = StepResult(
            step_id="map",
            name="map",
            status=StepStatus.COMPLETED,
            output=mapped_results,
            completed_at=datetime.now()
        )
        run.step_results.append(map_result)

        reduced = await reduce_step.execute({"items": mapped_results})

        reduce_result = StepResult(
            step_id="reduce",
            name="reduce",
            status=StepStatus.COMPLETED,
            output=reduced,
            completed_at=datetime.now()
        )
        run.step_results.append(reduce_result)

        run.status = ChainStatus.COMPLETED
        run.output_data = reduced if isinstance(reduced, dict) else {"result": reduced}
        run.completed_at = datetime.now()
        run.duration_ms = (run.completed_at - run.started_at).total_seconds() * 1000

        return run


# =============================================================================
# CHAIN ENGINE
# =============================================================================

class ChainEngine:
    """
    Chain Engine for BAEL.

    LLM chain orchestration.
    """

    def __init__(self):
        self._executors: Dict[ChainType, BaseChainExecutor] = {
            ChainType.SEQUENTIAL: SequentialExecutor(),
            ChainType.PARALLEL: ParallelExecutor(),
            ChainType.CONDITIONAL: ConditionalExecutor(),
            ChainType.MAP_REDUCE: MapReduceExecutor()
        }

        self._chains: Dict[str, ChainConfig] = {}
        self._steps: Dict[str, BaseStep] = {}
        self._runs: Dict[str, ChainRun] = {}

        self._stats = ChainStats()

    def get_executor(self, chain_type: ChainType) -> BaseChainExecutor:
        """Get executor by type."""
        return self._executors.get(chain_type, SequentialExecutor())

    def register_chain(
        self,
        name: str,
        chain_type: ChainType = ChainType.SEQUENTIAL,
        steps: Optional[List[StepConfig]] = None,
        output_mode: OutputMode = OutputMode.LAST
    ) -> ChainConfig:
        """Register a chain."""
        config = ChainConfig(
            name=name,
            chain_type=chain_type,
            steps=steps or [],
            output_mode=output_mode
        )

        self._chains[name] = config

        return config

    def get_chain(self, name: str) -> Optional[ChainConfig]:
        """Get chain by name."""
        return self._chains.get(name)

    def add_step(
        self,
        chain_name: str,
        step_name: str,
        step_type: str = "transform",
        config: Optional[Dict[str, Any]] = None,
        input_keys: Optional[List[str]] = None,
        output_key: str = ""
    ) -> Optional[StepConfig]:
        """Add a step to a chain."""
        chain = self._chains.get(chain_name)
        if not chain:
            return None

        step_config = StepConfig(
            name=step_name,
            step_type=step_type,
            config=config or {},
            input_keys=input_keys or [],
            output_key=output_key
        )

        chain.steps.append(step_config)

        if step_type == "transform":
            step = TransformStep(step_config)
        elif step_type == "llm":
            step = LLMStep(step_config)
        elif step_type == "condition":
            step = ConditionStep(step_config)
        elif step_type == "router":
            step = RouterStep(step_config)
        elif step_type == "aggregate":
            step = AggregateStep(step_config)
        else:
            step = TransformStep(step_config)

        self._steps[step_config.step_id] = step

        return step_config

    def register_custom_step(
        self,
        step_id: str,
        step: BaseStep
    ) -> None:
        """Register a custom step."""
        self._steps[step_id] = step

    async def run(
        self,
        chain_name: str,
        inputs: Dict[str, Any]
    ) -> ChainRun:
        """Run a chain."""
        chain = self._chains.get(chain_name)
        if not chain:
            raise ValueError(f"Chain not found: {chain_name}")

        executor = self.get_executor(chain.chain_type)

        run = await executor.execute(chain, inputs, self._steps)

        self._runs[run.run_id] = run
        self._update_stats(chain_name, run)

        return run

    async def run_inline(
        self,
        chain_type: ChainType,
        steps: List[Tuple[str, str, Dict[str, Any]]],
        inputs: Dict[str, Any]
    ) -> ChainRun:
        """Run an inline chain without registration."""
        step_configs = []

        for name, step_type, config in steps:
            step_config = StepConfig(
                name=name,
                step_type=step_type,
                config=config
            )
            step_configs.append(step_config)

            if step_type == "transform":
                step = TransformStep(step_config)
            elif step_type == "llm":
                step = LLMStep(step_config)
            elif step_type == "condition":
                step = ConditionStep(step_config)
            else:
                step = TransformStep(step_config)

            self._steps[step_config.step_id] = step

        chain_config = ChainConfig(
            name="inline_chain",
            chain_type=chain_type,
            steps=step_configs
        )

        executor = self.get_executor(chain_type)
        run = await executor.execute(chain_config, inputs, self._steps)

        return run

    def get_run(self, run_id: str) -> Optional[ChainRun]:
        """Get a run by ID."""
        return self._runs.get(run_id)

    def list_runs(
        self,
        chain_name: Optional[str] = None,
        status: Optional[ChainStatus] = None
    ) -> List[ChainRun]:
        """List chain runs."""
        runs = list(self._runs.values())

        if chain_name:
            chain = self._chains.get(chain_name)
            if chain:
                runs = [r for r in runs if r.chain_id == chain.chain_id]

        if status:
            runs = [r for r in runs if r.status == status]

        return runs

    def compose_chains(
        self,
        name: str,
        chain_names: List[str]
    ) -> ChainConfig:
        """Compose multiple chains into one."""
        all_steps = []

        for chain_name in chain_names:
            chain = self._chains.get(chain_name)
            if chain:
                all_steps.extend(chain.steps)

        return self.register_chain(
            name=name,
            chain_type=ChainType.SEQUENTIAL,
            steps=all_steps
        )

    def _update_stats(self, chain_name: str, run: ChainRun) -> None:
        """Update statistics."""
        self._stats.total_runs += 1

        if run.status == ChainStatus.COMPLETED:
            self._stats.successful_runs += 1
        elif run.status == ChainStatus.FAILED:
            self._stats.failed_runs += 1

        self._stats.by_chain[chain_name] = \
            self._stats.by_chain.get(chain_name, 0) + 1

        if self._stats.total_runs > 0:
            total_duration = sum(r.duration_ms for r in self._runs.values())
            self._stats.avg_duration_ms = total_duration / self._stats.total_runs

    @property
    def stats(self) -> ChainStats:
        """Get engine statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_chains": len(self._chains),
            "total_steps": len(self._steps),
            "total_runs": len(self._runs),
            "stats": {
                "runs": self._stats.total_runs,
                "successful": self._stats.successful_runs,
                "failed": self._stats.failed_runs,
                "avg_duration_ms": round(self._stats.avg_duration_ms, 2),
                "by_chain": self._stats.by_chain
            },
            "chain_types": [t.value for t in self._executors.keys()]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Chain Engine."""
    print("=" * 70)
    print("BAEL - CHAIN ENGINE DEMO")
    print("LLM Chain Orchestration")
    print("=" * 70)
    print()

    engine = ChainEngine()

    # 1. Create Sequential Chain
    print("1. SEQUENTIAL CHAIN:")
    print("-" * 40)

    engine.register_chain(
        name="text_processing",
        chain_type=ChainType.SEQUENTIAL
    )

    engine.add_step(
        "text_processing",
        "uppercase",
        "transform",
        config={"transform": "uppercase"}
    )

    engine.add_step(
        "text_processing",
        "analyze",
        "llm",
        config={"model": "gpt-4"}
    )

    run = await engine.run(
        "text_processing",
        inputs={"text": "hello world", "prompt": "Analyze this text"}
    )

    print(f"   Chain: text_processing")
    print(f"   Status: {run.status.value}")
    print(f"   Duration: {run.duration_ms:.2f}ms")
    print(f"   Steps: {len(run.step_results)}")

    for sr in run.step_results:
        print(f"      - {sr.name}: {sr.status.value}")
    print()

    # 2. Parallel Chain
    print("2. PARALLEL CHAIN:")
    print("-" * 40)

    engine.register_chain(
        name="parallel_analysis",
        chain_type=ChainType.PARALLEL
    )

    engine.add_step(
        "parallel_analysis",
        "sentiment",
        "llm",
        config={"model": "gpt-3.5"},
        output_key="sentiment_result"
    )

    engine.add_step(
        "parallel_analysis",
        "summary",
        "llm",
        config={"model": "gpt-4"},
        output_key="summary_result"
    )

    engine.add_step(
        "parallel_analysis",
        "keywords",
        "llm",
        config={"model": "gpt-3.5"},
        output_key="keywords_result"
    )

    run = await engine.run(
        "parallel_analysis",
        inputs={"prompt": "Analyze the given text"}
    )

    print(f"   Chain: parallel_analysis")
    print(f"   Status: {run.status.value}")
    print(f"   Duration: {run.duration_ms:.2f}ms")
    print(f"   Parallel Steps: {len(run.step_results)}")
    print(f"   Output Keys: {list(run.output_data.keys())}")
    print()

    # 3. Conditional Chain
    print("3. CONDITIONAL CHAIN:")
    print("-" * 40)

    engine.register_chain(
        name="conditional_flow",
        chain_type=ChainType.CONDITIONAL
    )

    engine.add_step(
        "conditional_flow",
        "check_score",
        "condition",
        config={"condition": "greater_than", "key": "score", "value": 50}
    )

    engine.add_step(
        "conditional_flow",
        "high_score_action",
        "transform",
        config={"transform": "identity"}
    )

    run = await engine.run(
        "conditional_flow",
        inputs={"score": 75, "text": "High performer"}
    )

    print(f"   Condition: score > 50")
    print(f"   Input Score: 75")
    print(f"   Status: {run.status.value}")
    print(f"   Steps Executed: {len(run.step_results)}")
    print()

    # 4. Map-Reduce Chain
    print("4. MAP-REDUCE CHAIN:")
    print("-" * 40)

    engine.register_chain(
        name="map_reduce_flow",
        chain_type=ChainType.MAP_REDUCE
    )

    engine.add_step(
        "map_reduce_flow",
        "map_step",
        "transform",
        config={"role": "map", "transform": "identity"}
    )

    engine.add_step(
        "map_reduce_flow",
        "reduce_step",
        "aggregate",
        config={"role": "reduce", "aggregation": "list"}
    )

    run = await engine.run(
        "map_reduce_flow",
        inputs={"items": [1, 2, 3, 4, 5]}
    )

    print(f"   Items: [1, 2, 3, 4, 5]")
    print(f"   Status: {run.status.value}")
    print(f"   Result: {run.output_data}")
    print()

    # 5. Inline Chain
    print("5. INLINE CHAIN:")
    print("-" * 40)

    run = await engine.run_inline(
        chain_type=ChainType.SEQUENTIAL,
        steps=[
            ("step1", "transform", {"transform": "lowercase"}),
            ("step2", "llm", {"model": "gpt-4"})
        ],
        inputs={"text": "HELLO", "prompt": "Process this"}
    )

    print(f"   Inline Steps: 2")
    print(f"   Status: {run.status.value}")
    print(f"   Duration: {run.duration_ms:.2f}ms")
    print()

    # 6. Chain Composition
    print("6. CHAIN COMPOSITION:")
    print("-" * 40)

    engine.register_chain("chain_a", ChainType.SEQUENTIAL)
    engine.add_step("chain_a", "step_a", "transform", config={"transform": "identity"})

    engine.register_chain("chain_b", ChainType.SEQUENTIAL)
    engine.add_step("chain_b", "step_b", "llm", config={"model": "gpt-4"})

    composed = engine.compose_chains(
        "composed_chain",
        ["chain_a", "chain_b"]
    )

    print(f"   Composed: chain_a + chain_b")
    print(f"   Total Steps: {len(composed.steps)}")
    print()

    # 7. List Runs
    print("7. LIST RUNS:")
    print("-" * 40)

    all_runs = engine.list_runs()
    completed = engine.list_runs(status=ChainStatus.COMPLETED)

    print(f"   Total Runs: {len(all_runs)}")
    print(f"   Completed: {len(completed)}")
    print()

    # 8. Engine Statistics
    print("8. ENGINE STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Runs: {stats.total_runs}")
    print(f"   Successful: {stats.successful_runs}")
    print(f"   Failed: {stats.failed_runs}")
    print(f"   Avg Duration: {stats.avg_duration_ms:.2f}ms")
    print()

    # 9. Engine Summary
    print("9. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Chains: {summary['total_chains']}")
    print(f"   Steps: {summary['total_steps']}")
    print(f"   Runs: {summary['total_runs']}")
    print(f"   Chain Types: {summary['chain_types']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Chain Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
