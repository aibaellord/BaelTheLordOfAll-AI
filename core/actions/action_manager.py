#!/usr/bin/env python3
"""
BAEL - Action Manager
Advanced action management and execution for AI agents.

Features:
- Action definition and registration
- Action composition and sequencing
- Rollback support
- Pre/post conditions
- Action history and audit
- Concurrent action execution
- Action validation
- Retry and recovery
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
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
R = TypeVar('R')


# =============================================================================
# ENUMS
# =============================================================================

class ActionStatus(Enum):
    """Action status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class ActionType(Enum):
    """Action type."""
    SIMPLE = "simple"
    COMPOSITE = "composite"
    CONDITIONAL = "conditional"
    TRANSACTIONAL = "transactional"
    ASYNC = "async"


class ActionPriority(Enum):
    """Action priority."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class RollbackMode(Enum):
    """Rollback mode."""
    NONE = "none"
    AUTO = "auto"
    MANUAL = "manual"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ActionContext:
    """Action execution context."""
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set context value."""
        self.data[key] = value


@dataclass
class ActionResult:
    """Action result."""
    action_id: str = ""
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionConfig:
    """Action configuration."""
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    rollback_mode: RollbackMode = RollbackMode.AUTO
    priority: ActionPriority = ActionPriority.NORMAL


@dataclass
class ActionDefinition:
    """Action definition."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    action_type: ActionType = ActionType.SIMPLE
    config: ActionConfig = field(default_factory=ActionConfig)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionRecord:
    """Action execution record."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str = ""
    action_name: str = ""
    status: ActionStatus = ActionStatus.PENDING
    result: Optional[ActionResult] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    context_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionStats:
    """Action statistics."""
    total_executed: int = 0
    successful: int = 0
    failed: int = 0
    rolled_back: int = 0
    avg_duration: float = 0.0


# =============================================================================
# CONDITIONS
# =============================================================================

class Condition(ABC):
    """Abstract condition."""

    @abstractmethod
    def evaluate(self, context: ActionContext) -> bool:
        """Evaluate condition."""
        pass


class TrueCondition(Condition):
    """Always true condition."""

    def evaluate(self, context: ActionContext) -> bool:
        return True


class FalseCondition(Condition):
    """Always false condition."""

    def evaluate(self, context: ActionContext) -> bool:
        return False


class KeyExistsCondition(Condition):
    """Check if key exists in context."""

    def __init__(self, key: str):
        self._key = key

    def evaluate(self, context: ActionContext) -> bool:
        return self._key in context.data


class ValueCondition(Condition):
    """Check value in context."""

    def __init__(self, key: str, expected: Any):
        self._key = key
        self._expected = expected

    def evaluate(self, context: ActionContext) -> bool:
        return context.get(self._key) == self._expected


class CallableCondition(Condition):
    """Callable-based condition."""

    def __init__(self, func: Callable[[ActionContext], bool]):
        self._func = func

    def evaluate(self, context: ActionContext) -> bool:
        return self._func(context)


class AndCondition(Condition):
    """AND condition."""

    def __init__(self, *conditions: Condition):
        self._conditions = conditions

    def evaluate(self, context: ActionContext) -> bool:
        return all(c.evaluate(context) for c in self._conditions)


class OrCondition(Condition):
    """OR condition."""

    def __init__(self, *conditions: Condition):
        self._conditions = conditions

    def evaluate(self, context: ActionContext) -> bool:
        return any(c.evaluate(context) for c in self._conditions)


class NotCondition(Condition):
    """NOT condition."""

    def __init__(self, condition: Condition):
        self._condition = condition

    def evaluate(self, context: ActionContext) -> bool:
        return not self._condition.evaluate(context)


# =============================================================================
# ACTION BASE
# =============================================================================

class Action(ABC):
    """Abstract action."""

    def __init__(
        self,
        name: str = "",
        config: Optional[ActionConfig] = None
    ):
        self.action_id = str(uuid.uuid4())
        self.name = name or self.__class__.__name__
        self.config = config or ActionConfig()
        self.preconditions: List[Condition] = []
        self.postconditions: List[Condition] = []
        self._rollback_data: Optional[Any] = None

    def add_precondition(self, condition: Condition) -> "Action":
        """Add precondition."""
        self.preconditions.append(condition)
        return self

    def add_postcondition(self, condition: Condition) -> "Action":
        """Add postcondition."""
        self.postconditions.append(condition)
        return self

    def check_preconditions(self, context: ActionContext) -> bool:
        """Check preconditions."""
        return all(c.evaluate(context) for c in self.preconditions)

    def check_postconditions(self, context: ActionContext) -> bool:
        """Check postconditions."""
        return all(c.evaluate(context) for c in self.postconditions)

    @abstractmethod
    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute action."""
        pass

    async def rollback(self, context: ActionContext) -> bool:
        """Rollback action."""
        return True


# =============================================================================
# SIMPLE ACTIONS
# =============================================================================

class FunctionAction(Action):
    """Function-based action."""

    def __init__(
        self,
        func: Callable[[ActionContext], Any],
        name: str = "",
        rollback_func: Optional[Callable[[ActionContext, Any], None]] = None
    ):
        super().__init__(name or func.__name__)
        self._func = func
        self._rollback_func = rollback_func

    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute function."""
        start_time = time.time()

        try:
            # Store rollback data
            self._rollback_data = copy.deepcopy(context.data)

            # Execute
            if asyncio.iscoroutinefunction(self._func):
                result = await self._func(context)
            else:
                result = self._func(context)

            return ActionResult(
                action_id=self.action_id,
                success=True,
                data=result,
                duration=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                action_id=self.action_id,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )

    async def rollback(self, context: ActionContext) -> bool:
        """Rollback function."""
        if self._rollback_func:
            try:
                if asyncio.iscoroutinefunction(self._rollback_func):
                    await self._rollback_func(context, self._rollback_data)
                else:
                    self._rollback_func(context, self._rollback_data)
                return True
            except Exception:
                return False

        # Restore context
        if self._rollback_data:
            context.data = self._rollback_data

        return True


class SetValueAction(Action):
    """Set value in context."""

    def __init__(self, key: str, value: Any):
        super().__init__(f"SetValue_{key}")
        self._key = key
        self._value = value
        self._old_value: Any = None

    async def execute(self, context: ActionContext) -> ActionResult:
        """Set value."""
        self._old_value = context.get(self._key)
        context.set(self._key, self._value)

        return ActionResult(
            action_id=self.action_id,
            success=True,
            data=self._value
        )

    async def rollback(self, context: ActionContext) -> bool:
        """Restore old value."""
        if self._old_value is not None:
            context.set(self._key, self._old_value)
        else:
            del context.data[self._key]
        return True


class DelayAction(Action):
    """Delay action."""

    def __init__(self, delay_seconds: float):
        super().__init__(f"Delay_{delay_seconds}s")
        self._delay = delay_seconds

    async def execute(self, context: ActionContext) -> ActionResult:
        """Wait for delay."""
        await asyncio.sleep(self._delay)

        return ActionResult(
            action_id=self.action_id,
            success=True,
            data={"delayed": self._delay}
        )


class LogAction(Action):
    """Log action."""

    def __init__(self, message: str, level: str = "info"):
        super().__init__("Log")
        self._message = message
        self._level = level

    async def execute(self, context: ActionContext) -> ActionResult:
        """Log message."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{self._level.upper()}] {self._message}"

        # Add to context
        logs = context.get("_logs", [])
        logs.append(log_entry)
        context.set("_logs", logs)

        return ActionResult(
            action_id=self.action_id,
            success=True,
            data=log_entry
        )


# =============================================================================
# COMPOSITE ACTIONS
# =============================================================================

class SequentialAction(Action):
    """Execute actions sequentially."""

    def __init__(
        self,
        actions: List[Action],
        name: str = "Sequential",
        stop_on_failure: bool = True
    ):
        super().__init__(name)
        self._actions = actions
        self._stop_on_failure = stop_on_failure
        self._executed: List[Action] = []

    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute actions sequentially."""
        start_time = time.time()
        results: List[ActionResult] = []

        for action in self._actions:
            # Check preconditions
            if not action.check_preconditions(context):
                if self._stop_on_failure:
                    return ActionResult(
                        action_id=self.action_id,
                        success=False,
                        error=f"Precondition failed for {action.name}",
                        duration=time.time() - start_time
                    )
                continue

            # Execute
            result = await action.execute(context)
            results.append(result)
            self._executed.append(action)

            if not result.success and self._stop_on_failure:
                return ActionResult(
                    action_id=self.action_id,
                    success=False,
                    error=f"Action {action.name} failed: {result.error}",
                    data=results,
                    duration=time.time() - start_time
                )

        return ActionResult(
            action_id=self.action_id,
            success=True,
            data=results,
            duration=time.time() - start_time
        )

    async def rollback(self, context: ActionContext) -> bool:
        """Rollback in reverse order."""
        success = True

        for action in reversed(self._executed):
            if not await action.rollback(context):
                success = False

        self._executed.clear()
        return success


class ParallelAction(Action):
    """Execute actions in parallel."""

    def __init__(
        self,
        actions: List[Action],
        name: str = "Parallel",
        max_concurrent: int = 0
    ):
        super().__init__(name)
        self._actions = actions
        self._max_concurrent = max_concurrent or len(actions)

    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute actions in parallel."""
        start_time = time.time()

        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def run_with_semaphore(action: Action) -> ActionResult:
            async with semaphore:
                return await action.execute(context)

        tasks = [run_with_semaphore(a) for a in self._actions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        action_results: List[ActionResult] = []
        all_success = True

        for r in results:
            if isinstance(r, Exception):
                action_results.append(ActionResult(
                    success=False,
                    error=str(r)
                ))
                all_success = False
            else:
                action_results.append(r)
                if not r.success:
                    all_success = False

        return ActionResult(
            action_id=self.action_id,
            success=all_success,
            data=action_results,
            duration=time.time() - start_time
        )


class ConditionalAction(Action):
    """Conditional action execution."""

    def __init__(
        self,
        condition: Condition,
        then_action: Action,
        else_action: Optional[Action] = None,
        name: str = "Conditional"
    ):
        super().__init__(name)
        self._condition = condition
        self._then_action = then_action
        self._else_action = else_action
        self._executed_action: Optional[Action] = None

    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute conditional action."""
        if self._condition.evaluate(context):
            self._executed_action = self._then_action
            return await self._then_action.execute(context)
        elif self._else_action:
            self._executed_action = self._else_action
            return await self._else_action.execute(context)

        return ActionResult(
            action_id=self.action_id,
            success=True,
            data=None
        )

    async def rollback(self, context: ActionContext) -> bool:
        """Rollback executed action."""
        if self._executed_action:
            return await self._executed_action.rollback(context)
        return True


class LoopAction(Action):
    """Loop action."""

    def __init__(
        self,
        action: Action,
        count: int = 1,
        condition: Optional[Condition] = None,
        name: str = "Loop"
    ):
        super().__init__(name)
        self._action = action
        self._count = count
        self._condition = condition
        self._iterations = 0

    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute loop."""
        start_time = time.time()
        results: List[ActionResult] = []

        for i in range(self._count):
            if self._condition and not self._condition.evaluate(context):
                break

            result = await self._action.execute(context)
            results.append(result)
            self._iterations += 1

            if not result.success:
                return ActionResult(
                    action_id=self.action_id,
                    success=False,
                    error=f"Iteration {i} failed",
                    data=results,
                    duration=time.time() - start_time
                )

        return ActionResult(
            action_id=self.action_id,
            success=True,
            data=results,
            duration=time.time() - start_time,
            metadata={"iterations": self._iterations}
        )


class RetryAction(Action):
    """Retry action on failure."""

    def __init__(
        self,
        action: Action,
        max_retries: int = 3,
        delay: float = 1.0,
        name: str = "Retry"
    ):
        super().__init__(name)
        self._action = action
        self._max_retries = max_retries
        self._delay = delay

    async def execute(self, context: ActionContext) -> ActionResult:
        """Execute with retries."""
        start_time = time.time()
        last_error: Optional[str] = None

        for attempt in range(self._max_retries + 1):
            result = await self._action.execute(context)

            if result.success:
                result.metadata["attempts"] = attempt + 1
                return result

            last_error = result.error

            if attempt < self._max_retries:
                await asyncio.sleep(self._delay)

        return ActionResult(
            action_id=self.action_id,
            success=False,
            error=f"Failed after {self._max_retries + 1} attempts: {last_error}",
            duration=time.time() - start_time,
            metadata={"attempts": self._max_retries + 1}
        )


# =============================================================================
# ACTION REGISTRY
# =============================================================================

class ActionRegistry:
    """Registry for actions."""

    def __init__(self):
        self._actions: Dict[str, Action] = {}
        self._by_type: Dict[ActionType, List[str]] = defaultdict(list)
        self._by_tag: Dict[str, List[str]] = defaultdict(list)

    def register(
        self,
        action: Action,
        action_type: ActionType = ActionType.SIMPLE,
        tags: Optional[List[str]] = None
    ) -> str:
        """Register action."""
        self._actions[action.action_id] = action
        self._by_type[action_type].append(action.action_id)

        for tag in (tags or []):
            self._by_tag[tag].append(action.action_id)

        return action.action_id

    def get(self, action_id: str) -> Optional[Action]:
        """Get action."""
        return self._actions.get(action_id)

    def get_by_name(self, name: str) -> Optional[Action]:
        """Get action by name."""
        for action in self._actions.values():
            if action.name == name:
                return action
        return None

    def get_by_type(self, action_type: ActionType) -> List[Action]:
        """Get actions by type."""
        return [
            self._actions[aid]
            for aid in self._by_type[action_type]
            if aid in self._actions
        ]

    def get_by_tag(self, tag: str) -> List[Action]:
        """Get actions by tag."""
        return [
            self._actions[aid]
            for aid in self._by_tag[tag]
            if aid in self._actions
        ]

    def unregister(self, action_id: str) -> bool:
        """Unregister action."""
        if action_id in self._actions:
            del self._actions[action_id]
            return True
        return False

    def list_all(self) -> List[str]:
        """List all action IDs."""
        return list(self._actions.keys())


# =============================================================================
# ACTION EXECUTOR
# =============================================================================

class ActionExecutor:
    """Execute actions."""

    def __init__(self):
        self._running: Dict[str, asyncio.Task] = {}
        self._history: List[ActionRecord] = []
        self._stats = ActionStats()

    async def execute(
        self,
        action: Action,
        context: Optional[ActionContext] = None
    ) -> ActionResult:
        """Execute action."""
        ctx = context or ActionContext()

        # Create record
        record = ActionRecord(
            action_id=action.action_id,
            action_name=action.name,
            status=ActionStatus.RUNNING,
            context_snapshot=copy.deepcopy(ctx.data)
        )

        try:
            # Check preconditions
            if not action.check_preconditions(ctx):
                record.status = ActionStatus.FAILED
                record.completed_at = datetime.now()
                self._history.append(record)

                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    error="Preconditions not met"
                )

            # Execute with timeout
            if action.config.timeout > 0:
                result = await asyncio.wait_for(
                    action.execute(ctx),
                    timeout=action.config.timeout
                )
            else:
                result = await action.execute(ctx)

            # Check postconditions
            if result.success and not action.check_postconditions(ctx):
                # Rollback if auto
                if action.config.rollback_mode == RollbackMode.AUTO:
                    await action.rollback(ctx)
                    record.status = ActionStatus.ROLLED_BACK
                    self._stats.rolled_back += 1
                else:
                    record.status = ActionStatus.FAILED

                result = ActionResult(
                    action_id=action.action_id,
                    success=False,
                    error="Postconditions not met"
                )
            else:
                record.status = (
                    ActionStatus.COMPLETED if result.success
                    else ActionStatus.FAILED
                )

            record.result = result
            record.completed_at = datetime.now()
            self._history.append(record)

            # Update stats
            self._stats.total_executed += 1
            if result.success:
                self._stats.successful += 1
            else:
                self._stats.failed += 1

            # Update average duration
            n = self._stats.total_executed
            old_avg = self._stats.avg_duration
            self._stats.avg_duration = (
                (old_avg * (n - 1) + result.duration) / n
            )

            return result

        except asyncio.TimeoutError:
            record.status = ActionStatus.FAILED
            record.completed_at = datetime.now()
            self._history.append(record)

            self._stats.total_executed += 1
            self._stats.failed += 1

            return ActionResult(
                action_id=action.action_id,
                success=False,
                error="Action timed out"
            )

        except Exception as e:
            record.status = ActionStatus.FAILED
            record.completed_at = datetime.now()
            self._history.append(record)

            self._stats.total_executed += 1
            self._stats.failed += 1

            return ActionResult(
                action_id=action.action_id,
                success=False,
                error=str(e)
            )

    def get_history(self, limit: int = 100) -> List[ActionRecord]:
        """Get action history."""
        return self._history[-limit:]

    def get_stats(self) -> ActionStats:
        """Get execution statistics."""
        return self._stats


# =============================================================================
# ACTION BUILDER
# =============================================================================

class ActionBuilder:
    """Builder for actions."""

    def __init__(self):
        self._actions: List[Action] = []
        self._name: str = "CompositeAction"
        self._config = ActionConfig()

    def name(self, name: str) -> "ActionBuilder":
        """Set name."""
        self._name = name
        return self

    def add(self, action: Action) -> "ActionBuilder":
        """Add action."""
        self._actions.append(action)
        return self

    def function(
        self,
        func: Callable[[ActionContext], Any],
        name: str = ""
    ) -> "ActionBuilder":
        """Add function action."""
        self._actions.append(FunctionAction(func, name))
        return self

    def set_value(self, key: str, value: Any) -> "ActionBuilder":
        """Add set value action."""
        self._actions.append(SetValueAction(key, value))
        return self

    def delay(self, seconds: float) -> "ActionBuilder":
        """Add delay action."""
        self._actions.append(DelayAction(seconds))
        return self

    def log(self, message: str, level: str = "info") -> "ActionBuilder":
        """Add log action."""
        self._actions.append(LogAction(message, level))
        return self

    def timeout(self, seconds: float) -> "ActionBuilder":
        """Set timeout."""
        self._config.timeout = seconds
        return self

    def retries(self, count: int) -> "ActionBuilder":
        """Set retries."""
        self._config.max_retries = count
        return self

    def build_sequential(self) -> SequentialAction:
        """Build sequential action."""
        action = SequentialAction(self._actions, self._name)
        action.config = self._config
        return action

    def build_parallel(self) -> ParallelAction:
        """Build parallel action."""
        action = ParallelAction(self._actions, self._name)
        action.config = self._config
        return action


# =============================================================================
# ACTION MANAGER
# =============================================================================

class ActionManager:
    """
    Action Manager for BAEL.

    Manages action definitions, registration, and execution.
    """

    def __init__(self):
        self._registry = ActionRegistry()
        self._executor = ActionExecutor()

    # -------------------------------------------------------------------------
    # REGISTRATION
    # -------------------------------------------------------------------------

    def register(
        self,
        action: Action,
        tags: Optional[List[str]] = None
    ) -> str:
        """Register action."""
        return self._registry.register(action, tags=tags)

    def register_function(
        self,
        func: Callable[[ActionContext], Any],
        name: str = "",
        tags: Optional[List[str]] = None
    ) -> str:
        """Register function action."""
        action = FunctionAction(func, name)
        return self._registry.register(action, tags=tags)

    def get(self, action_id: str) -> Optional[Action]:
        """Get action."""
        return self._registry.get(action_id)

    def get_by_name(self, name: str) -> Optional[Action]:
        """Get action by name."""
        return self._registry.get_by_name(name)

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def execute(
        self,
        action: Union[str, Action],
        context: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """Execute action."""
        if isinstance(action, str):
            action_obj = self._registry.get(action)
            if not action_obj:
                action_obj = self._registry.get_by_name(action)
            if not action_obj:
                return ActionResult(
                    success=False,
                    error=f"Action not found: {action}"
                )
        else:
            action_obj = action

        ctx = ActionContext(data=context or {})
        return await self._executor.execute(action_obj, ctx)

    async def execute_sequence(
        self,
        actions: List[Union[str, Action]],
        context: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """Execute actions sequentially."""
        resolved_actions: List[Action] = []

        for action in actions:
            if isinstance(action, str):
                action_obj = self._registry.get(action)
                if not action_obj:
                    action_obj = self._registry.get_by_name(action)
                if action_obj:
                    resolved_actions.append(action_obj)
            else:
                resolved_actions.append(action)

        seq_action = SequentialAction(resolved_actions)
        ctx = ActionContext(data=context or {})
        return await self._executor.execute(seq_action, ctx)

    async def execute_parallel(
        self,
        actions: List[Union[str, Action]],
        context: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 0
    ) -> ActionResult:
        """Execute actions in parallel."""
        resolved_actions: List[Action] = []

        for action in actions:
            if isinstance(action, str):
                action_obj = self._registry.get(action)
                if not action_obj:
                    action_obj = self._registry.get_by_name(action)
                if action_obj:
                    resolved_actions.append(action_obj)
            else:
                resolved_actions.append(action)

        parallel_action = ParallelAction(
            resolved_actions,
            max_concurrent=max_concurrent
        )
        ctx = ActionContext(data=context or {})
        return await self._executor.execute(parallel_action, ctx)

    # -------------------------------------------------------------------------
    # BUILDER
    # -------------------------------------------------------------------------

    def builder(self) -> ActionBuilder:
        """Get action builder."""
        return ActionBuilder()

    # -------------------------------------------------------------------------
    # HISTORY AND STATS
    # -------------------------------------------------------------------------

    def get_history(self, limit: int = 100) -> List[ActionRecord]:
        """Get action history."""
        return self._executor.get_history(limit)

    def get_stats(self) -> ActionStats:
        """Get execution statistics."""
        return self._executor.get_stats()

    def list_actions(self) -> List[str]:
        """List registered actions."""
        return self._registry.list_all()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Action Manager."""
    print("=" * 70)
    print("BAEL - ACTION MANAGER DEMO")
    print("Advanced Action Management and Execution")
    print("=" * 70)
    print()

    manager = ActionManager()

    # 1. Register Simple Actions
    print("1. REGISTER SIMPLE ACTIONS:")
    print("-" * 40)

    def greet_action(ctx: ActionContext) -> str:
        name = ctx.get("name", "World")
        return f"Hello, {name}!"

    action_id = manager.register_function(greet_action, "greet")
    print(f"   Registered: greet ({action_id[:8]}...)")

    def calculate_action(ctx: ActionContext) -> int:
        a = ctx.get("a", 0)
        b = ctx.get("b", 0)
        result = a + b
        ctx.set("result", result)
        return result

    manager.register_function(calculate_action, "calculate")
    print(f"   Registered: calculate")
    print()

    # 2. Execute Action
    print("2. EXECUTE ACTION:")
    print("-" * 40)

    result = await manager.execute("greet", {"name": "BAEL"})
    print(f"   Result: {result.data}")
    print(f"   Success: {result.success}")
    print()

    # 3. Function Action
    print("3. FUNCTION ACTION:")
    print("-" * 40)

    action = FunctionAction(
        lambda ctx: ctx.get("x", 0) * 2,
        name="double"
    )

    result = await manager.execute(action, {"x": 21})
    print(f"   Double 21 = {result.data}")
    print()

    # 4. Sequential Actions
    print("4. SEQUENTIAL ACTIONS:")
    print("-" * 40)

    seq = (manager.builder()
        .name("SequentialDemo")
        .set_value("step", 1)
        .log("Step 1 complete")
        .set_value("step", 2)
        .log("Step 2 complete")
        .set_value("step", 3)
        .log("Step 3 complete")
        .build_sequential())

    ctx = ActionContext()
    result = await manager.execute(seq, ctx.data)

    print(f"   Executed {len(result.data)} actions")
    print(f"   Final step: {ctx.get('step')}")
    print()

    # 5. Parallel Actions
    print("5. PARALLEL ACTIONS:")
    print("-" * 40)

    async def task1(ctx: ActionContext):
        await asyncio.sleep(0.1)
        return "Task 1 done"

    async def task2(ctx: ActionContext):
        await asyncio.sleep(0.1)
        return "Task 2 done"

    async def task3(ctx: ActionContext):
        await asyncio.sleep(0.1)
        return "Task 3 done"

    parallel = ParallelAction([
        FunctionAction(task1, "task1"),
        FunctionAction(task2, "task2"),
        FunctionAction(task3, "task3")
    ])

    result = await manager.execute(parallel)

    print(f"   Parallel execution: {result.success}")
    print(f"   Duration: {result.duration:.3f}s")
    print()

    # 6. Conditional Action
    print("6. CONDITIONAL ACTION:")
    print("-" * 40)

    conditional = ConditionalAction(
        condition=ValueCondition("mode", "admin"),
        then_action=FunctionAction(lambda ctx: "Admin access granted"),
        else_action=FunctionAction(lambda ctx: "User access only")
    )

    result1 = await manager.execute(conditional, {"mode": "admin"})
    result2 = await manager.execute(conditional, {"mode": "user"})

    print(f"   Admin mode: {result1.data}")
    print(f"   User mode: {result2.data}")
    print()

    # 7. Loop Action
    print("7. LOOP ACTION:")
    print("-" * 40)

    counter_action = FunctionAction(
        lambda ctx: ctx.set("count", ctx.get("count", 0) + 1),
        name="increment"
    )

    loop = LoopAction(counter_action, count=5)

    ctx = ActionContext()
    result = await manager.execute(loop, ctx.data)

    print(f"   Loop iterations: {result.metadata.get('iterations')}")
    print()

    # 8. Retry Action
    print("8. RETRY ACTION:")
    print("-" * 40)

    attempt_count = [0]

    def flaky_action(ctx: ActionContext):
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise Exception("Temporary failure")
        return "Success on attempt 3"

    retry = RetryAction(
        FunctionAction(flaky_action, "flaky"),
        max_retries=3,
        delay=0.1
    )

    result = await manager.execute(retry)

    print(f"   Result: {result.data}")
    print(f"   Attempts: {result.metadata.get('attempts')}")
    print()

    # 9. Preconditions
    print("9. PRECONDITIONS:")
    print("-" * 40)

    restricted_action = FunctionAction(
        lambda ctx: "Accessed restricted resource",
        name="restricted"
    )
    restricted_action.add_precondition(KeyExistsCondition("auth_token"))

    result1 = await manager.execute(restricted_action, {})
    result2 = await manager.execute(restricted_action, {"auth_token": "secret"})

    print(f"   Without token: {result1.error}")
    print(f"   With token: {result2.data}")
    print()

    # 10. Rollback
    print("10. ROLLBACK SUPPORT:")
    print("-" * 40)

    set_action = SetValueAction("balance", 100)

    ctx = ActionContext(data={"balance": 50})
    original = ctx.get("balance")

    await set_action.execute(ctx)
    after_set = ctx.get("balance")

    await set_action.rollback(ctx)
    after_rollback = ctx.get("balance")

    print(f"   Original: {original}")
    print(f"   After set: {after_set}")
    print(f"   After rollback: {after_rollback}")
    print()

    # 11. Complex Conditions
    print("11. COMPLEX CONDITIONS:")
    print("-" * 40)

    complex_condition = AndCondition(
        KeyExistsCondition("user"),
        OrCondition(
            ValueCondition("role", "admin"),
            ValueCondition("role", "moderator")
        )
    )

    ctx1 = ActionContext(data={"user": "alice", "role": "admin"})
    ctx2 = ActionContext(data={"user": "bob", "role": "user"})

    print(f"   Admin user: {complex_condition.evaluate(ctx1)}")
    print(f"   Regular user: {complex_condition.evaluate(ctx2)}")
    print()

    # 12. Action Builder
    print("12. ACTION BUILDER:")
    print("-" * 40)

    workflow = (manager.builder()
        .name("CompleteWorkflow")
        .log("Starting workflow", "info")
        .set_value("status", "initialized")
        .function(lambda ctx: ctx.set("data", [1, 2, 3]), "load_data")
        .delay(0.05)
        .log("Workflow complete", "info")
        .build_sequential())

    result = await manager.execute(workflow)

    print(f"   Workflow success: {result.success}")
    print(f"   Steps executed: {len(result.data)}")
    print()

    # 13. Action History
    print("13. ACTION HISTORY:")
    print("-" * 40)

    history = manager.get_history(limit=5)

    print(f"   Recent actions: {len(history)}")
    for record in history[:3]:
        status = record.status.value
        print(f"     - {record.action_name}: {status}")
    print()

    # 14. Statistics
    print("14. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total executed: {stats.total_executed}")
    print(f"   Successful: {stats.successful}")
    print(f"   Failed: {stats.failed}")
    print(f"   Avg duration: {stats.avg_duration:.4f}s")
    print()

    # 15. List Actions
    print("15. REGISTERED ACTIONS:")
    print("-" * 40)

    action_ids = manager.list_actions()

    print(f"   Registered: {len(action_ids)} actions")
    for aid in action_ids[:3]:
        action = manager.get(aid)
        if action:
            print(f"     - {action.name}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Action Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
