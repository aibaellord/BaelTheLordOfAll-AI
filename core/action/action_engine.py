#!/usr/bin/env python3
"""
BAEL - Action Engine
Action execution and effect management.

Features:
- Action definition
- Effect propagation
- Rollback support
- Action composition
- Execution monitoring
"""

import asyncio
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ActionType(Enum):
    """Action types."""
    ATOMIC = "atomic"
    COMPOSITE = "composite"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    PARALLEL = "parallel"


class ActionStatus(Enum):
    """Action execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class EffectType(Enum):
    """Effect types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    INVOKE = "invoke"
    NOTIFY = "notify"


class RollbackStrategy(Enum):
    """Rollback strategies."""
    NONE = "none"
    COMPENSATE = "compensate"
    UNDO = "undo"
    RETRY = "retry"


class ExecutionMode(Enum):
    """Execution modes."""
    SYNC = "sync"
    ASYNC = "async"
    BATCH = "batch"
    STREAM = "stream"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ActionContext:
    """Action execution context."""
    context_id: str = ""
    parent_id: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.context_id:
            self.context_id = str(uuid.uuid4())[:8]

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value


@dataclass
class Effect:
    """Action effect."""
    effect_id: str = ""
    effect_type: EffectType = EffectType.UPDATE
    target: str = ""
    attribute: str = ""
    old_value: Any = None
    new_value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.effect_id:
            self.effect_id = str(uuid.uuid4())[:8]


@dataclass
class ActionResult:
    """Action execution result."""
    action_id: str
    status: ActionStatus = ActionStatus.COMPLETED
    output: Any = None
    error: Optional[str] = None
    effects: List[Effect] = field(default_factory=list)
    duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    child_results: List["ActionResult"] = field(default_factory=list)


@dataclass
class ActionConfig:
    """Action configuration."""
    action_id: str = ""
    name: str = ""
    description: str = ""
    action_type: ActionType = ActionType.ATOMIC
    handler: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    rollback_strategy: RollbackStrategy = RollbackStrategy.COMPENSATE

    def __post_init__(self):
        if not self.action_id:
            self.action_id = str(uuid.uuid4())[:8]


@dataclass
class ActionDefinition:
    """Complete action definition."""
    config: ActionConfig = field(default_factory=ActionConfig)
    preconditions: List[Callable[[ActionContext], bool]] = field(default_factory=list)
    execute_fn: Optional[Callable] = None
    rollback_fn: Optional[Callable] = None
    validators: List[Callable[[Any], bool]] = field(default_factory=list)


@dataclass
class ActionHistory:
    """Action execution history."""
    entries: List[Tuple[datetime, str, ActionResult]] = field(default_factory=list)

    def add(self, action_id: str, result: ActionResult) -> None:
        self.entries.append((datetime.now(), action_id, result))

    def get_recent(self, n: int = 10) -> List[Tuple[datetime, str, ActionResult]]:
        return self.entries[-n:]


@dataclass
class ActionStats:
    """Action statistics."""
    total_executions: int = 0
    successful: int = 0
    failed: int = 0
    rolled_back: int = 0
    total_effects: int = 0
    avg_duration_ms: float = 0.0
    by_type: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# ACTION HANDLERS
# =============================================================================

class BaseActionHandler(ABC):
    """Abstract base action handler."""

    @property
    @abstractmethod
    def handler_type(self) -> str:
        """Get handler type."""
        pass

    @abstractmethod
    async def execute(
        self,
        config: ActionConfig,
        context: ActionContext
    ) -> ActionResult:
        """Execute the action."""
        pass

    async def rollback(
        self,
        config: ActionConfig,
        context: ActionContext,
        result: ActionResult
    ) -> bool:
        """Rollback the action."""
        return True


class AtomicHandler(BaseActionHandler):
    """Atomic action handler."""

    def __init__(self):
        self._functions: Dict[str, Callable] = {}
        self._rollback_functions: Dict[str, Callable] = {}

    @property
    def handler_type(self) -> str:
        return "atomic"

    def register(
        self,
        name: str,
        execute_fn: Callable,
        rollback_fn: Optional[Callable] = None
    ) -> None:
        """Register an atomic action."""
        self._functions[name] = execute_fn
        if rollback_fn:
            self._rollback_functions[name] = rollback_fn

    async def execute(
        self,
        config: ActionConfig,
        context: ActionContext
    ) -> ActionResult:
        """Execute atomic action."""
        start_time = time.time()
        result = ActionResult(
            action_id=config.action_id,
            started_at=datetime.now()
        )

        handler_name = config.handler or config.name
        func = self._functions.get(handler_name)

        try:
            if func:
                if asyncio.iscoroutinefunction(func):
                    output = await asyncio.wait_for(
                        func(context, **config.params),
                        timeout=config.timeout_seconds
                    )
                else:
                    output = func(context, **config.params)
            else:
                await asyncio.sleep(0.01)
                output = {"executed": True, **config.params}

            result.status = ActionStatus.COMPLETED
            result.output = output

        except asyncio.TimeoutError:
            result.status = ActionStatus.FAILED
            result.error = "Timeout"

        except Exception as e:
            result.status = ActionStatus.FAILED
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        result.completed_at = datetime.now()

        return result

    async def rollback(
        self,
        config: ActionConfig,
        context: ActionContext,
        result: ActionResult
    ) -> bool:
        """Rollback atomic action."""
        handler_name = config.handler or config.name
        rollback_fn = self._rollback_functions.get(handler_name)

        if rollback_fn:
            try:
                if asyncio.iscoroutinefunction(rollback_fn):
                    await rollback_fn(context, result)
                else:
                    rollback_fn(context, result)
                return True
            except Exception:
                return False

        return True


class CompositeHandler(BaseActionHandler):
    """Composite (sequential) action handler."""

    def __init__(self, executor: "ActionExecutor"):
        self._executor = executor

    @property
    def handler_type(self) -> str:
        return "composite"

    async def execute(
        self,
        config: ActionConfig,
        context: ActionContext
    ) -> ActionResult:
        """Execute composite action."""
        start_time = time.time()
        result = ActionResult(
            action_id=config.action_id,
            started_at=datetime.now()
        )

        sub_actions = config.params.get("actions", [])

        for sub_config in sub_actions:
            if isinstance(sub_config, dict):
                sub_config = ActionConfig(**sub_config)

            sub_result = await self._executor.execute(sub_config, context)
            result.child_results.append(sub_result)

            if sub_result.status == ActionStatus.FAILED:
                result.status = ActionStatus.FAILED
                result.error = f"Sub-action failed: {sub_result.error}"
                break
        else:
            result.status = ActionStatus.COMPLETED

        result.duration_ms = (time.time() - start_time) * 1000
        result.completed_at = datetime.now()

        return result


class ParallelHandler(BaseActionHandler):
    """Parallel action handler."""

    def __init__(self, executor: "ActionExecutor"):
        self._executor = executor

    @property
    def handler_type(self) -> str:
        return "parallel"

    async def execute(
        self,
        config: ActionConfig,
        context: ActionContext
    ) -> ActionResult:
        """Execute actions in parallel."""
        start_time = time.time()
        result = ActionResult(
            action_id=config.action_id,
            started_at=datetime.now()
        )

        sub_actions = config.params.get("actions", [])

        tasks = []
        for sub_config in sub_actions:
            if isinstance(sub_config, dict):
                sub_config = ActionConfig(**sub_config)

            tasks.append(self._executor.execute(sub_config, context))

        sub_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_success = True
        for sub_result in sub_results:
            if isinstance(sub_result, Exception):
                result.child_results.append(ActionResult(
                    action_id="error",
                    status=ActionStatus.FAILED,
                    error=str(sub_result)
                ))
                all_success = False
            else:
                result.child_results.append(sub_result)
                if sub_result.status == ActionStatus.FAILED:
                    all_success = False

        result.status = ActionStatus.COMPLETED if all_success else ActionStatus.FAILED
        result.duration_ms = (time.time() - start_time) * 1000
        result.completed_at = datetime.now()

        return result


class ConditionalHandler(BaseActionHandler):
    """Conditional action handler."""

    def __init__(self, executor: "ActionExecutor"):
        self._executor = executor

    @property
    def handler_type(self) -> str:
        return "conditional"

    async def execute(
        self,
        config: ActionConfig,
        context: ActionContext
    ) -> ActionResult:
        """Execute conditional action."""
        start_time = time.time()
        result = ActionResult(
            action_id=config.action_id,
            started_at=datetime.now()
        )

        condition = config.params.get("condition")
        then_action = config.params.get("then")
        else_action = config.params.get("else")

        condition_met = False

        if callable(condition):
            condition_met = condition(context)
        elif isinstance(condition, str):
            condition_met = context.get(condition, False)
        elif isinstance(condition, bool):
            condition_met = condition

        action_to_run = then_action if condition_met else else_action

        if action_to_run:
            if isinstance(action_to_run, dict):
                action_to_run = ActionConfig(**action_to_run)

            sub_result = await self._executor.execute(action_to_run, context)
            result.child_results.append(sub_result)
            result.status = sub_result.status
        else:
            result.status = ActionStatus.COMPLETED

        result.duration_ms = (time.time() - start_time) * 1000
        result.completed_at = datetime.now()

        return result


class LoopHandler(BaseActionHandler):
    """Loop action handler."""

    def __init__(self, executor: "ActionExecutor"):
        self._executor = executor

    @property
    def handler_type(self) -> str:
        return "loop"

    async def execute(
        self,
        config: ActionConfig,
        context: ActionContext
    ) -> ActionResult:
        """Execute loop action."""
        start_time = time.time()
        result = ActionResult(
            action_id=config.action_id,
            started_at=datetime.now()
        )

        loop_action = config.params.get("action")
        iterations = config.params.get("iterations", 1)
        items = config.params.get("items", [])
        max_iterations = config.params.get("max", 100)

        if items:
            iteration_source = items
        else:
            iteration_source = range(min(iterations, max_iterations))

        for i, item in enumerate(iteration_source):
            context.set("_loop_index", i)
            context.set("_loop_item", item)

            if isinstance(loop_action, dict):
                action_config = ActionConfig(**loop_action)
            else:
                action_config = loop_action

            sub_result = await self._executor.execute(action_config, context)
            result.child_results.append(sub_result)

            if sub_result.status == ActionStatus.FAILED:
                result.status = ActionStatus.FAILED
                result.error = f"Loop iteration {i} failed"
                break
        else:
            result.status = ActionStatus.COMPLETED

        result.duration_ms = (time.time() - start_time) * 1000
        result.completed_at = datetime.now()

        return result


# =============================================================================
# ACTION EXECUTOR
# =============================================================================

class ActionExecutor:
    """Execute actions with effect tracking."""

    def __init__(self):
        self._atomic = AtomicHandler()
        self._handlers: Dict[ActionType, BaseActionHandler] = {
            ActionType.ATOMIC: self._atomic
        }

        self._handlers[ActionType.COMPOSITE] = CompositeHandler(self)
        self._handlers[ActionType.PARALLEL] = ParallelHandler(self)
        self._handlers[ActionType.CONDITIONAL] = ConditionalHandler(self)
        self._handlers[ActionType.LOOP] = LoopHandler(self)

        self._history = ActionHistory()
        self._effects_log: List[Effect] = []

    def register_action(
        self,
        name: str,
        execute_fn: Callable,
        rollback_fn: Optional[Callable] = None
    ) -> None:
        """Register an atomic action."""
        self._atomic.register(name, execute_fn, rollback_fn)

    async def execute(
        self,
        config: ActionConfig,
        context: Optional[ActionContext] = None
    ) -> ActionResult:
        """Execute an action."""
        context = context or ActionContext()

        handler = self._handlers.get(config.action_type)
        if not handler:
            return ActionResult(
                action_id=config.action_id,
                status=ActionStatus.FAILED,
                error=f"Unknown action type: {config.action_type}"
            )

        result = await handler.execute(config, context)

        self._history.add(config.action_id, result)

        for effect in result.effects:
            self._effects_log.append(effect)

        return result

    async def execute_with_rollback(
        self,
        config: ActionConfig,
        context: Optional[ActionContext] = None
    ) -> ActionResult:
        """Execute with automatic rollback on failure."""
        context = context or ActionContext()

        result = await self.execute(config, context)

        if result.status == ActionStatus.FAILED:
            if config.rollback_strategy != RollbackStrategy.NONE:
                await self.rollback(config, context, result)

        return result

    async def rollback(
        self,
        config: ActionConfig,
        context: ActionContext,
        result: ActionResult
    ) -> bool:
        """Rollback an action."""
        handler = self._handlers.get(config.action_type)

        if handler:
            success = await handler.rollback(config, context, result)

            if success:
                result.status = ActionStatus.ROLLED_BACK

            return success

        return False

    def track_effect(
        self,
        effect_type: EffectType,
        target: str,
        attribute: str,
        old_value: Any,
        new_value: Any
    ) -> Effect:
        """Track an effect."""
        effect = Effect(
            effect_type=effect_type,
            target=target,
            attribute=attribute,
            old_value=old_value,
            new_value=new_value
        )

        self._effects_log.append(effect)

        return effect

    def get_history(self, n: int = 10) -> List[Tuple[datetime, str, ActionResult]]:
        """Get execution history."""
        return self._history.get_recent(n)

    def get_effects(self) -> List[Effect]:
        """Get all tracked effects."""
        return self._effects_log


# =============================================================================
# ACTION ENGINE
# =============================================================================

class ActionEngine:
    """
    Action Engine for BAEL.

    Action execution and effect management.
    """

    def __init__(self):
        self._executor = ActionExecutor()
        self._definitions: Dict[str, ActionDefinition] = {}
        self._stats = ActionStats()

    def define_action(
        self,
        name: str,
        action_type: ActionType = ActionType.ATOMIC,
        handler: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        rollback: RollbackStrategy = RollbackStrategy.COMPENSATE
    ) -> ActionConfig:
        """Define an action."""
        config = ActionConfig(
            name=name,
            action_type=action_type,
            handler=handler,
            params=params or {},
            timeout_seconds=timeout,
            rollback_strategy=rollback
        )

        definition = ActionDefinition(config=config)
        self._definitions[name] = definition

        return config

    def register_handler(
        self,
        name: str,
        execute_fn: Callable,
        rollback_fn: Optional[Callable] = None
    ) -> None:
        """Register action handler."""
        self._executor.register_action(name, execute_fn, rollback_fn)

    def get_definition(self, name: str) -> Optional[ActionDefinition]:
        """Get action definition."""
        return self._definitions.get(name)

    async def execute(
        self,
        name: str,
        context: Optional[ActionContext] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """Execute a defined action."""
        definition = self._definitions.get(name)

        if not definition:
            return ActionResult(
                action_id=name,
                status=ActionStatus.FAILED,
                error=f"Action not defined: {name}"
            )

        config = definition.config

        if params:
            config = ActionConfig(
                action_id=config.action_id,
                name=config.name,
                action_type=config.action_type,
                handler=config.handler,
                params={**config.params, **params},
                timeout_seconds=config.timeout_seconds,
                rollback_strategy=config.rollback_strategy
            )

        context = context or ActionContext()

        for precondition in definition.preconditions:
            if not precondition(context):
                return ActionResult(
                    action_id=config.action_id,
                    status=ActionStatus.FAILED,
                    error="Precondition failed"
                )

        result = await self._executor.execute_with_rollback(config, context)

        if result.status == ActionStatus.COMPLETED and definition.validators:
            for validator in definition.validators:
                if not validator(result.output):
                    result.status = ActionStatus.FAILED
                    result.error = "Validation failed"
                    break

        self._update_stats(config.action_type, result)

        return result

    async def execute_inline(
        self,
        action_type: ActionType,
        params: Dict[str, Any],
        context: Optional[ActionContext] = None
    ) -> ActionResult:
        """Execute an inline action."""
        config = ActionConfig(
            name="inline_action",
            action_type=action_type,
            params=params
        )

        result = await self._executor.execute(config, context or ActionContext())

        self._update_stats(action_type, result)

        return result

    async def execute_sequence(
        self,
        actions: List[str],
        context: Optional[ActionContext] = None
    ) -> ActionResult:
        """Execute actions in sequence."""
        sub_configs = []

        for name in actions:
            definition = self._definitions.get(name)
            if definition:
                sub_configs.append(definition.config)

        config = ActionConfig(
            name="sequence",
            action_type=ActionType.COMPOSITE,
            params={"actions": sub_configs}
        )

        return await self._executor.execute(config, context or ActionContext())

    async def execute_parallel(
        self,
        actions: List[str],
        context: Optional[ActionContext] = None
    ) -> ActionResult:
        """Execute actions in parallel."""
        sub_configs = []

        for name in actions:
            definition = self._definitions.get(name)
            if definition:
                sub_configs.append(definition.config)

        config = ActionConfig(
            name="parallel",
            action_type=ActionType.PARALLEL,
            params={"actions": sub_configs}
        )

        return await self._executor.execute(config, context or ActionContext())

    def track_effect(
        self,
        effect_type: EffectType,
        target: str,
        attribute: str,
        old_value: Any,
        new_value: Any
    ) -> Effect:
        """Track an effect."""
        effect = self._executor.track_effect(
            effect_type, target, attribute, old_value, new_value
        )

        self._stats.total_effects += 1

        return effect

    def get_history(self, n: int = 10) -> List[Tuple[datetime, str, ActionResult]]:
        """Get execution history."""
        return self._executor.get_history(n)

    def get_effects(self) -> List[Effect]:
        """Get all tracked effects."""
        return self._executor.get_effects()

    def _update_stats(
        self,
        action_type: ActionType,
        result: ActionResult
    ) -> None:
        """Update statistics."""
        self._stats.total_executions += 1

        if result.status == ActionStatus.COMPLETED:
            self._stats.successful += 1
        elif result.status == ActionStatus.FAILED:
            self._stats.failed += 1
        elif result.status == ActionStatus.ROLLED_BACK:
            self._stats.rolled_back += 1

        type_key = action_type.value
        self._stats.by_type[type_key] = \
            self._stats.by_type.get(type_key, 0) + 1

        if self._stats.total_executions > 0:
            history = self._executor.get_history(100)
            total_duration = sum(r.duration_ms for _, _, r in history)
            self._stats.avg_duration_ms = total_duration / len(history)

    @property
    def stats(self) -> ActionStats:
        """Get action statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "defined_actions": len(self._definitions),
            "total_executions": self._stats.total_executions,
            "successful": self._stats.successful,
            "failed": self._stats.failed,
            "rolled_back": self._stats.rolled_back,
            "total_effects": self._stats.total_effects,
            "avg_duration_ms": round(self._stats.avg_duration_ms, 2),
            "by_type": self._stats.by_type
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Action Engine."""
    print("=" * 70)
    print("BAEL - ACTION ENGINE DEMO")
    print("Action Execution and Effect Management")
    print("=" * 70)
    print()

    engine = ActionEngine()

    # 1. Register Handlers
    print("1. REGISTER HANDLERS:")
    print("-" * 40)

    async def process_data(ctx: ActionContext, **params):
        data = params.get("data", [])
        return {"processed": len(data), "data": data}

    async def save_data(ctx: ActionContext, **params):
        return {"saved": True, "location": params.get("path", "/tmp")}

    async def notify(ctx: ActionContext, **params):
        return {"notified": params.get("recipients", [])}

    engine.register_handler("process", process_data)
    engine.register_handler("save", save_data)
    engine.register_handler("notify", notify)

    print("   Registered: process, save, notify")
    print()

    # 2. Define Actions
    print("2. DEFINE ACTIONS:")
    print("-" * 40)

    engine.define_action(
        name="process_data",
        action_type=ActionType.ATOMIC,
        handler="process",
        params={"data": [1, 2, 3]}
    )

    engine.define_action(
        name="save_results",
        action_type=ActionType.ATOMIC,
        handler="save",
        params={"path": "/data/results.json"}
    )

    engine.define_action(
        name="send_notification",
        action_type=ActionType.ATOMIC,
        handler="notify",
        params={"recipients": ["admin@example.com"]}
    )

    print("   Defined: process_data, save_results, send_notification")
    print()

    # 3. Execute Single Action
    print("3. EXECUTE SINGLE ACTION:")
    print("-" * 40)

    result = await engine.execute("process_data")

    print(f"   Status: {result.status.value}")
    print(f"   Output: {result.output}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print()

    # 4. Execute with Custom Params
    print("4. EXECUTE WITH CUSTOM PARAMS:")
    print("-" * 40)

    result = await engine.execute(
        "process_data",
        params={"data": ["a", "b", "c", "d", "e"]}
    )

    print(f"   Output: {result.output}")
    print()

    # 5. Execute Sequence
    print("5. EXECUTE SEQUENCE:")
    print("-" * 40)

    result = await engine.execute_sequence([
        "process_data",
        "save_results",
        "send_notification"
    ])

    print(f"   Status: {result.status.value}")
    print(f"   Steps: {len(result.child_results)}")

    for i, child in enumerate(result.child_results):
        print(f"      Step {i+1}: {child.status.value}")
    print()

    # 6. Execute Parallel
    print("6. EXECUTE PARALLEL:")
    print("-" * 40)

    result = await engine.execute_parallel([
        "process_data",
        "send_notification"
    ])

    print(f"   Status: {result.status.value}")
    print(f"   Parallel tasks: {len(result.child_results)}")
    print(f"   Total Duration: {result.duration_ms:.2f}ms")
    print()

    # 7. Inline Conditional
    print("7. INLINE CONDITIONAL:")
    print("-" * 40)

    context = ActionContext()
    context.set("should_process", True)

    result = await engine.execute_inline(
        ActionType.CONDITIONAL,
        params={
            "condition": "should_process",
            "then": {"name": "process", "action_type": "atomic", "handler": "process"},
            "else": {"name": "skip", "action_type": "atomic"}
        },
        context=context
    )

    print(f"   Condition: should_process = True")
    print(f"   Status: {result.status.value}")
    print()

    # 8. Inline Loop
    print("8. INLINE LOOP:")
    print("-" * 40)

    result = await engine.execute_inline(
        ActionType.LOOP,
        params={
            "iterations": 3,
            "action": {"name": "iter", "action_type": "atomic", "handler": "process", "params": {"data": []}}
        }
    )

    print(f"   Iterations: 3")
    print(f"   Status: {result.status.value}")
    print(f"   Results: {len(result.child_results)}")
    print()

    # 9. Track Effects
    print("9. TRACK EFFECTS:")
    print("-" * 40)

    engine.track_effect(
        EffectType.CREATE,
        target="database",
        attribute="records",
        old_value=None,
        new_value={"id": 1, "name": "test"}
    )

    engine.track_effect(
        EffectType.UPDATE,
        target="cache",
        attribute="count",
        old_value=10,
        new_value=15
    )

    effects = engine.get_effects()
    print(f"   Tracked effects: {len(effects)}")

    for effect in effects[-2:]:
        print(f"      {effect.effect_type.value}: {effect.target}.{effect.attribute}")
    print()

    # 10. Execution History
    print("10. EXECUTION HISTORY:")
    print("-" * 40)

    history = engine.get_history(5)

    for timestamp, action_id, result in history:
        print(f"   {timestamp.strftime('%H:%M:%S')} - {action_id}: {result.status.value}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Executions: {stats.total_executions}")
    print(f"   Successful: {stats.successful}")
    print(f"   Failed: {stats.failed}")
    print(f"   Rolled Back: {stats.rolled_back}")
    print(f"   Total Effects: {stats.total_effects}")
    print(f"   Avg Duration: {stats.avg_duration_ms:.2f}ms")
    print()

    # 12. Engine Summary
    print("12. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Defined Actions: {summary['defined_actions']}")
    print(f"   Executions: {summary['total_executions']}")
    print(f"   By Type: {summary['by_type']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Action Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
