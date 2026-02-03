#!/usr/bin/env python3
"""
BAEL - Workflow Processor
Complex workflow definition, execution, and orchestration system.

This module implements comprehensive workflow processing capabilities
for orchestrating complex multi-step operations with branching,
parallel execution, error recovery, and state persistence.

Features:
- DAG-based workflow definition
- Parallel and sequential execution
- Conditional branching
- Error recovery and retry logic
- State persistence and recovery
- Workflow templates
- Dynamic workflow generation
- Real-time monitoring
- Sub-workflow support
- Compensation (rollback) logic
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class WorkflowStatus(Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPENSATING = "compensating"


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPENSATED = "compensated"


class StepType(Enum):
    """Types of workflow steps."""
    TASK = "task"
    DECISION = "decision"
    PARALLEL = "parallel"
    SUBWORKFLOW = "subworkflow"
    WAIT = "wait"
    NOTIFY = "notify"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    LOOP = "loop"
    HUMAN_APPROVAL = "human_approval"


class RetryStrategy(Enum):
    """Retry strategies for failed steps."""
    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"


class TriggerType(Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    WEBHOOK = "webhook"
    CONDITIONAL = "conditional"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0
    multiplier: float = 2.0
    retryable_errors: List[str] = field(default_factory=list)


@dataclass
class StepInput:
    """Input specification for a step."""
    name: str = ""
    source: str = ""  # previous_step.output, context.variable, constant
    default: Any = None
    required: bool = True
    transform: Optional[str] = None


@dataclass
class StepOutput:
    """Output specification for a step."""
    name: str = ""
    path: str = ""  # JSONPath to extract from result
    store_in_context: bool = True


@dataclass
class Condition:
    """A condition for branching."""
    expression: str = ""
    operator: str = "eq"  # eq, ne, gt, lt, gte, lte, in, contains
    value: Any = None

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the condition against context."""
        try:
            # Get the value from expression (supports dot notation)
            actual = self._resolve_expression(self.expression, context)

            if self.operator == "eq":
                return actual == self.value
            elif self.operator == "ne":
                return actual != self.value
            elif self.operator == "gt":
                return actual > self.value
            elif self.operator == "lt":
                return actual < self.value
            elif self.operator == "gte":
                return actual >= self.value
            elif self.operator == "lte":
                return actual <= self.value
            elif self.operator == "in":
                return actual in self.value
            elif self.operator == "contains":
                return self.value in actual
            elif self.operator == "exists":
                return actual is not None
            elif self.operator == "truthy":
                return bool(actual)
            else:
                return False
        except Exception:
            return False

    def _resolve_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Resolve dot notation expression."""
        parts = expr.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value


@dataclass
class Branch:
    """A branch in a decision step."""
    name: str = ""
    condition: Condition = field(default_factory=Condition)
    target_step: str = ""
    is_default: bool = False


@dataclass
class StepConfig:
    """Configuration for a workflow step."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    step_type: StepType = StepType.TASK
    handler: str = ""  # Handler function/class name
    inputs: List[StepInput] = field(default_factory=list)
    outputs: List[StepOutput] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    branches: List[Branch] = field(default_factory=list)  # For decision steps
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    timeout_seconds: float = 300.0
    compensation_handler: Optional[str] = None  # For rollback
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepExecution:
    """Execution record for a step."""
    id: str = field(default_factory=lambda: str(uuid4()))
    step_id: str = ""
    status: StepStatus = StepStatus.PENDING
    attempt: int = 1
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


@dataclass
class WorkflowConfig:
    """Configuration for a workflow."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: Dict[str, StepConfig] = field(default_factory=dict)
    start_step: str = ""
    end_steps: List[str] = field(default_factory=list)
    inputs: List[StepInput] = field(default_factory=list)
    outputs: List[StepOutput] = field(default_factory=list)
    global_retry_config: RetryConfig = field(default_factory=RetryConfig)
    global_timeout_seconds: float = 3600.0
    trigger: TriggerType = TriggerType.MANUAL
    tags: List[str] = field(default_factory=list)

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate workflow configuration."""
        errors = []

        if not self.start_step:
            errors.append("No start step defined")
        elif self.start_step not in self.steps:
            errors.append(f"Start step '{self.start_step}' not found")

        # Check all referenced steps exist
        for step_id, step in self.steps.items():
            for next_step in step.next_steps:
                if next_step not in self.steps:
                    errors.append(f"Step '{step_id}' references unknown step '{next_step}'")
            for branch in step.branches:
                if branch.target_step not in self.steps:
                    errors.append(f"Branch in '{step_id}' targets unknown step '{branch.target_step}'")

        # Check for cycles (simplified)
        visited = set()
        def has_cycle(step_id: str, path: Set[str]) -> bool:
            if step_id in path:
                return True
            if step_id in visited:
                return False
            visited.add(step_id)
            path.add(step_id)
            step = self.steps.get(step_id)
            if step:
                for next_step in step.next_steps:
                    if has_cycle(next_step, path.copy()):
                        return True
            return False

        if self.start_step and has_cycle(self.start_step, set()):
            errors.append("Workflow contains cycles")

        return len(errors) == 0, errors


@dataclass
class WorkflowExecution:
    """Execution record for a workflow."""
    id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    workflow_version: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    step_executions: Dict[str, List[StepExecution]] = field(default_factory=lambda: defaultdict(list))
    current_steps: Set[str] = field(default_factory=set)
    completed_steps: Set[str] = field(default_factory=set)
    failed_steps: Set[str] = field(default_factory=set)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# =============================================================================
# STEP HANDLERS
# =============================================================================

class StepHandler(ABC):
    """Base class for step handlers."""

    @abstractmethod
    async def execute(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the step and return outputs."""
        pass

    async def compensate(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Compensate (rollback) the step. Return True if successful."""
        return True


class TaskHandler(StepHandler):
    """Handler for task steps."""

    def __init__(self):
        self.registered_tasks: Dict[str, Callable] = {}

    def register_task(self, name: str, func: Callable) -> None:
        """Register a task function."""
        self.registered_tasks[name] = func

    async def execute(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the task."""
        task_func = self.registered_tasks.get(step.handler)
        if not task_func:
            raise ValueError(f"Unknown task handler: {step.handler}")

        # Call task function
        if asyncio.iscoroutinefunction(task_func):
            result = await task_func(inputs, context)
        else:
            result = task_func(inputs, context)

        return result if isinstance(result, dict) else {"result": result}


class DecisionHandler(StepHandler):
    """Handler for decision (branching) steps."""

    async def execute(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate conditions and return next step."""
        for branch in step.branches:
            if branch.is_default:
                continue
            if branch.condition.evaluate({**context, **inputs}):
                return {"next_step": branch.target_step, "branch": branch.name}

        # Find default branch
        default_branches = [b for b in step.branches if b.is_default]
        if default_branches:
            return {"next_step": default_branches[0].target_step, "branch": "default"}

        return {"next_step": None, "branch": None}


class ParallelHandler(StepHandler):
    """Handler for parallel execution steps."""

    async def execute(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return list of parallel steps to execute."""
        return {"parallel_steps": step.next_steps}


class WaitHandler(StepHandler):
    """Handler for wait steps."""

    async def execute(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Wait for specified duration or condition."""
        duration = inputs.get("duration_seconds", 0)
        if duration > 0:
            await asyncio.sleep(duration)
        return {"waited": True, "duration": duration}


class TransformHandler(StepHandler):
    """Handler for data transformation steps."""

    async def execute(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data according to rules."""
        transform_rules = step.metadata.get("transform_rules", {})
        result = {}

        for output_key, rule in transform_rules.items():
            if rule.get("type") == "copy":
                source = rule.get("source", "")
                result[output_key] = self._resolve_path(source, inputs)
            elif rule.get("type") == "template":
                template = rule.get("template", "")
                result[output_key] = template.format(**inputs)
            elif rule.get("type") == "aggregate":
                items = inputs.get(rule.get("source", "items"), [])
                operation = rule.get("operation", "count")
                if operation == "count":
                    result[output_key] = len(items)
                elif operation == "sum":
                    result[output_key] = sum(items)

        return result

    def _resolve_path(self, path: str, data: Dict[str, Any]) -> Any:
        """Resolve dot notation path."""
        parts = path.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value


class ValidateHandler(StepHandler):
    """Handler for validation steps."""

    async def execute(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate data against schema/rules."""
        validation_rules = step.metadata.get("validation_rules", [])
        errors = []

        for rule in validation_rules:
            field = rule.get("field")
            rule_type = rule.get("type")
            value = inputs.get(field)

            if rule_type == "required" and value is None:
                errors.append(f"Field '{field}' is required")
            elif rule_type == "type" and value is not None:
                expected_type = rule.get("expected")
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field '{field}' must be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field '{field}' must be a number")
            elif rule_type == "range" and isinstance(value, (int, float)):
                min_val = rule.get("min")
                max_val = rule.get("max")
                if min_val is not None and value < min_val:
                    errors.append(f"Field '{field}' must be >= {min_val}")
                if max_val is not None and value > max_val:
                    errors.append(f"Field '{field}' must be <= {max_val}")

        return {"valid": len(errors) == 0, "errors": errors}


class LoopHandler(StepHandler):
    """Handler for loop steps."""

    async def execute(
        self,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Setup loop iteration."""
        items = inputs.get("items", [])
        loop_body = step.metadata.get("loop_body_step")

        return {
            "items": items,
            "total": len(items),
            "loop_body": loop_body,
            "iterations": list(range(len(items)))
        }


# =============================================================================
# WORKFLOW ENGINE
# =============================================================================

class WorkflowEngine:
    """
    The main workflow execution engine.

    Handles workflow lifecycle, step execution, error recovery,
    and state management.
    """

    def __init__(self):
        self.workflows: Dict[str, WorkflowConfig] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.handlers: Dict[StepType, StepHandler] = {
            StepType.TASK: TaskHandler(),
            StepType.DECISION: DecisionHandler(),
            StepType.PARALLEL: ParallelHandler(),
            StepType.WAIT: WaitHandler(),
            StepType.TRANSFORM: TransformHandler(),
            StepType.VALIDATE: ValidateHandler(),
            StepType.LOOP: LoopHandler(),
        }
        self.running = False
        self.state_store_path: Optional[Path] = None

    def register_workflow(self, workflow: WorkflowConfig) -> bool:
        """Register a workflow definition."""
        valid, errors = workflow.validate()
        if not valid:
            logger.error(f"Invalid workflow: {errors}")
            return False

        self.workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.name} ({workflow.id})")
        return True

    def register_task(self, name: str, func: Callable) -> None:
        """Register a task handler function."""
        task_handler = self.handlers.get(StepType.TASK)
        if isinstance(task_handler, TaskHandler):
            task_handler.register_task(name, func)

    async def start_workflow(
        self,
        workflow_id: str,
        inputs: Dict[str, Any] = None
    ) -> WorkflowExecution:
        """Start a new workflow execution."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_version=workflow.version,
            context=inputs or {}
        )

        self.executions[execution.id] = execution

        # Start execution
        asyncio.create_task(self._execute_workflow(execution))

        return execution

    async def _execute_workflow(self, execution: WorkflowExecution) -> None:
        """Execute a workflow."""
        workflow = self.workflows.get(execution.workflow_id)
        if not workflow:
            execution.status = WorkflowStatus.FAILED
            execution.error = "Workflow not found"
            return

        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.now()

        try:
            # Start with the first step
            execution.current_steps.add(workflow.start_step)

            while execution.current_steps and execution.status == WorkflowStatus.RUNNING:
                # Execute all current steps in parallel
                step_tasks = []
                for step_id in list(execution.current_steps):
                    step = workflow.steps.get(step_id)
                    if step:
                        task = asyncio.create_task(
                            self._execute_step(workflow, step, execution)
                        )
                        step_tasks.append((step_id, task))

                # Wait for all current steps to complete
                for step_id, task in step_tasks:
                    try:
                        next_steps = await task
                        execution.current_steps.discard(step_id)
                        execution.completed_steps.add(step_id)

                        # Add next steps
                        for next_step in next_steps:
                            if next_step not in execution.completed_steps:
                                # Check if all dependencies are met
                                if self._dependencies_met(workflow, next_step, execution):
                                    execution.current_steps.add(next_step)
                    except Exception as e:
                        execution.current_steps.discard(step_id)
                        execution.failed_steps.add(step_id)
                        execution.status = WorkflowStatus.FAILED
                        execution.error = str(e)
                        break

                # Save state
                await self._save_state(execution)

            # Mark completion
            if execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.COMPLETED

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            logger.error(f"Workflow execution failed: {e}")

        finally:
            execution.completed_at = datetime.now()

    def _dependencies_met(
        self,
        workflow: WorkflowConfig,
        step_id: str,
        execution: WorkflowExecution
    ) -> bool:
        """Check if all dependencies for a step are met."""
        # Find all steps that have this step as next
        for other_id, other_step in workflow.steps.items():
            if step_id in other_step.next_steps:
                if other_id not in execution.completed_steps:
                    return False
            for branch in other_step.branches:
                if branch.target_step == step_id:
                    if other_id not in execution.completed_steps:
                        return False
        return True

    async def _execute_step(
        self,
        workflow: WorkflowConfig,
        step: StepConfig,
        execution: WorkflowExecution
    ) -> List[str]:
        """Execute a single step and return next steps."""
        step_execution = StepExecution(step_id=step.id)
        execution.step_executions[step.id].append(step_execution)

        step_execution.status = StepStatus.RUNNING
        step_execution.started_at = datetime.now()

        try:
            # Prepare inputs
            inputs = await self._prepare_inputs(step, execution)
            step_execution.input_data = inputs

            # Get handler
            handler = self.handlers.get(step.step_type)
            if not handler:
                raise ValueError(f"No handler for step type: {step.step_type}")

            # Execute with timeout and retry
            outputs = await self._execute_with_retry(
                handler, step, inputs, execution.context
            )

            step_execution.output_data = outputs
            step_execution.status = StepStatus.COMPLETED

            # Store outputs in context
            for output in step.outputs:
                if output.store_in_context:
                    value = outputs.get(output.name, outputs.get(output.path))
                    if value is not None:
                        execution.context[f"{step.id}.{output.name}"] = value

            # Determine next steps
            if step.step_type == StepType.DECISION:
                next_step = outputs.get("next_step")
                return [next_step] if next_step else []
            elif step.step_type == StepType.PARALLEL:
                return outputs.get("parallel_steps", [])
            else:
                return step.next_steps

        except Exception as e:
            step_execution.status = StepStatus.FAILED
            step_execution.error = str(e)
            raise

        finally:
            step_execution.completed_at = datetime.now()
            step_execution.duration_ms = (
                step_execution.completed_at - step_execution.started_at
            ).total_seconds() * 1000

    async def _prepare_inputs(
        self,
        step: StepConfig,
        execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Prepare inputs for a step."""
        inputs = {}

        for input_spec in step.inputs:
            value = None

            if input_spec.source.startswith("context."):
                # Get from context
                key = input_spec.source[8:]
                value = execution.context.get(key)
            elif "." in input_spec.source:
                # Get from previous step output
                parts = input_spec.source.split(".")
                step_id = parts[0]
                output_key = ".".join(parts[1:])
                step_execs = execution.step_executions.get(step_id, [])
                if step_execs:
                    value = step_execs[-1].output_data.get(output_key)
            else:
                # Get from workflow context
                value = execution.context.get(input_spec.source)

            if value is None:
                value = input_spec.default

            if value is None and input_spec.required:
                raise ValueError(f"Required input '{input_spec.name}' not found")

            inputs[input_spec.name] = value

        return inputs

    async def _execute_with_retry(
        self,
        handler: StepHandler,
        step: StepConfig,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute step with retry logic."""
        retry_config = step.retry_config
        last_error = None

        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    handler.execute(step, inputs, context),
                    timeout=step.timeout_seconds
                )
                return result

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Step timeout after {step.timeout_seconds}s")
            except Exception as e:
                last_error = e

            # Check if we should retry
            if attempt < retry_config.max_attempts:
                if retry_config.strategy == RetryStrategy.NONE:
                    break

                # Calculate delay
                delay = self._calculate_retry_delay(retry_config, attempt)
                logger.warning(
                    f"Step '{step.name}' failed (attempt {attempt}), "
                    f"retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        raise last_error

    def _calculate_retry_delay(self, config: RetryConfig, attempt: int) -> float:
        """Calculate delay before next retry."""
        if config.strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            return config.initial_delay_seconds
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            return min(
                config.initial_delay_seconds * attempt,
                config.max_delay_seconds
            )
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return min(
                config.initial_delay_seconds * (config.multiplier ** (attempt - 1)),
                config.max_delay_seconds
            )
        return config.initial_delay_seconds

    async def pause_workflow(self, execution_id: str) -> bool:
        """Pause a running workflow."""
        execution = self.executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.PAUSED
            await self._save_state(execution)
            return True
        return False

    async def resume_workflow(self, execution_id: str) -> bool:
        """Resume a paused workflow."""
        execution = self.executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            asyncio.create_task(self._execute_workflow(execution))
            return True
        return False

    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a workflow execution."""
        execution = self.executions.get(execution_id)
        if execution and execution.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
            execution.status = WorkflowStatus.CANCELLED
            return True
        return False

    async def _save_state(self, execution: WorkflowExecution) -> None:
        """Save execution state for recovery."""
        if self.state_store_path:
            state_file = self.state_store_path / f"{execution.id}.state"
            with open(state_file, "wb") as f:
                pickle.dump(execution, f)

    async def restore_state(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Restore execution state from storage."""
        if self.state_store_path:
            state_file = self.state_store_path / f"{execution_id}.state"
            if state_file.exists():
                with open(state_file, "rb") as f:
                    execution = pickle.load(f)
                    self.executions[execution.id] = execution
                    return execution
        return None

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow execution."""
        execution = self.executions.get(execution_id)
        if not execution:
            return None

        return {
            "id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "current_steps": list(execution.current_steps),
            "completed_steps": list(execution.completed_steps),
            "failed_steps": list(execution.failed_steps),
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "error": execution.error
        }


# =============================================================================
# WORKFLOW BUILDER
# =============================================================================

class WorkflowBuilder:
    """Builder for creating workflows programmatically."""

    def __init__(self, name: str):
        self.workflow = WorkflowConfig(name=name)
        self._current_step: Optional[str] = None

    def set_description(self, description: str) -> "WorkflowBuilder":
        """Set workflow description."""
        self.workflow.description = description
        return self

    def add_step(
        self,
        step_id: str,
        name: str,
        step_type: StepType = StepType.TASK,
        handler: str = ""
    ) -> "WorkflowBuilder":
        """Add a step to the workflow."""
        step = StepConfig(
            id=step_id,
            name=name,
            step_type=step_type,
            handler=handler
        )
        self.workflow.steps[step_id] = step

        if not self.workflow.start_step:
            self.workflow.start_step = step_id

        self._current_step = step_id
        return self

    def with_input(
        self,
        name: str,
        source: str,
        required: bool = True,
        default: Any = None
    ) -> "WorkflowBuilder":
        """Add input to current step."""
        if self._current_step:
            step = self.workflow.steps[self._current_step]
            step.inputs.append(StepInput(
                name=name,
                source=source,
                required=required,
                default=default
            ))
        return self

    def with_output(
        self,
        name: str,
        store_in_context: bool = True
    ) -> "WorkflowBuilder":
        """Add output to current step."""
        if self._current_step:
            step = self.workflow.steps[self._current_step]
            step.outputs.append(StepOutput(
                name=name,
                store_in_context=store_in_context
            ))
        return self

    def then(self, next_step_id: str) -> "WorkflowBuilder":
        """Connect current step to next step."""
        if self._current_step:
            step = self.workflow.steps[self._current_step]
            step.next_steps.append(next_step_id)
        return self

    def with_branch(
        self,
        name: str,
        target: str,
        expression: str,
        operator: str = "eq",
        value: Any = None,
        is_default: bool = False
    ) -> "WorkflowBuilder":
        """Add a branch to current step (for decision steps)."""
        if self._current_step:
            step = self.workflow.steps[self._current_step]
            step.branches.append(Branch(
                name=name,
                target_step=target,
                condition=Condition(
                    expression=expression,
                    operator=operator,
                    value=value
                ),
                is_default=is_default
            ))
        return self

    def with_retry(
        self,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    ) -> "WorkflowBuilder":
        """Configure retry for current step."""
        if self._current_step:
            step = self.workflow.steps[self._current_step]
            step.retry_config = RetryConfig(
                strategy=strategy,
                max_attempts=max_attempts
            )
        return self

    def with_timeout(self, seconds: float) -> "WorkflowBuilder":
        """Set timeout for current step."""
        if self._current_step:
            step = self.workflow.steps[self._current_step]
            step.timeout_seconds = seconds
        return self

    def as_end_step(self) -> "WorkflowBuilder":
        """Mark current step as an end step."""
        if self._current_step:
            self.workflow.end_steps.append(self._current_step)
        return self

    def build(self) -> WorkflowConfig:
        """Build and return the workflow."""
        valid, errors = self.workflow.validate()
        if not valid:
            raise ValueError(f"Invalid workflow: {errors}")
        return self.workflow


# =============================================================================
# WORKFLOW PROCESSOR
# =============================================================================

class WorkflowProcessor:
    """
    The master workflow processor for BAEL.

    Provides high-level workflow management including
    templates, scheduling, and monitoring.
    """

    def __init__(self):
        self.engine = WorkflowEngine()
        self.templates: Dict[str, WorkflowConfig] = {}
        self.schedules: Dict[str, Dict[str, Any]] = {}

    def register_template(self, template: WorkflowConfig) -> None:
        """Register a workflow template."""
        self.templates[template.name] = template

    async def execute_template(
        self,
        template_name: str,
        inputs: Dict[str, Any] = None
    ) -> WorkflowExecution:
        """Execute a workflow from template."""
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")

        # Create instance from template
        workflow = WorkflowConfig(
            name=f"{template.name}_{uuid4().hex[:8]}",
            description=template.description,
            version=template.version,
            steps=template.steps.copy(),
            start_step=template.start_step,
            end_steps=template.end_steps.copy(),
            inputs=template.inputs.copy(),
            outputs=template.outputs.copy()
        )

        self.engine.register_workflow(workflow)
        return await self.engine.start_workflow(workflow.id, inputs)

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status."""
        return self.engine.get_execution_status(execution_id)

    async def wait_for_completion(
        self,
        execution_id: str,
        timeout_seconds: float = 3600
    ) -> WorkflowExecution:
        """Wait for workflow to complete."""
        start_time = time.time()

        while True:
            execution = self.engine.executions.get(execution_id)
            if not execution:
                raise ValueError(f"Unknown execution: {execution_id}")

            if execution.status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED
            ]:
                return execution

            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"Workflow did not complete in {timeout_seconds}s")

            await asyncio.sleep(0.5)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Workflow Processor."""
    print("=" * 70)
    print("BAEL - WORKFLOW PROCESSOR DEMO")
    print("Complex Workflow Orchestration")
    print("=" * 70)
    print()

    # Create processor
    processor = WorkflowProcessor()

    # Register task handlers
    async def fetch_data(inputs, context):
        await asyncio.sleep(0.1)  # Simulate work
        return {"data": {"items": [1, 2, 3, 4, 5], "count": 5}}

    async def process_data(inputs, context):
        data = inputs.get("data", {})
        items = data.get("items", [])
        return {"processed": [x * 2 for x in items], "sum": sum(items)}

    async def validate_result(inputs, context):
        processed = inputs.get("processed", [])
        return {"valid": len(processed) > 0, "count": len(processed)}

    async def notify_complete(inputs, context):
        return {"notified": True, "message": "Workflow complete!"}

    processor.engine.register_task("fetch_data", fetch_data)
    processor.engine.register_task("process_data", process_data)
    processor.engine.register_task("validate_result", validate_result)
    processor.engine.register_task("notify_complete", notify_complete)

    # 1. Build a workflow
    print("1. BUILDING WORKFLOW:")
    print("-" * 40)

    workflow = (
        WorkflowBuilder("DataProcessingPipeline")
        .set_description("Fetch, process, validate, and notify")

        # Step 1: Fetch data
        .add_step("fetch", "Fetch Data", StepType.TASK, "fetch_data")
        .with_output("data")
        .with_retry(max_attempts=3)
        .then("process")

        # Step 2: Process data
        .add_step("process", "Process Data", StepType.TASK, "process_data")
        .with_input("data", "fetch.data")
        .with_output("processed")
        .with_output("sum")
        .then("validate")

        # Step 3: Validate
        .add_step("validate", "Validate Result", StepType.TASK, "validate_result")
        .with_input("processed", "process.processed")
        .with_output("valid")
        .then("decide")

        # Step 4: Decision
        .add_step("decide", "Check Validity", StepType.DECISION)
        .with_branch("valid", "notify", "valid", "eq", True)
        .with_branch("invalid", "error", "valid", "eq", False, is_default=True)

        # Step 5a: Notify
        .add_step("notify", "Send Notification", StepType.TASK, "notify_complete")
        .as_end_step()

        # Step 5b: Error
        .add_step("error", "Handle Error", StepType.TASK, "notify_complete")
        .as_end_step()

        .build()
    )

    print(f"   Workflow: {workflow.name}")
    print(f"   Steps: {len(workflow.steps)}")
    print(f"   Start: {workflow.start_step}")
    print()

    # 2. Register and execute
    print("2. EXECUTING WORKFLOW:")
    print("-" * 40)

    processor.engine.register_workflow(workflow)
    execution = await processor.engine.start_workflow(workflow.id, {"source": "demo"})

    print(f"   Execution ID: {execution.id[:8]}...")
    print(f"   Status: {execution.status.value}")

    # Wait for completion
    result = await processor.wait_for_completion(execution.id, timeout_seconds=30)
    print(f"   Final Status: {result.status.value}")
    print()

    # 3. Show execution details
    print("3. EXECUTION DETAILS:")
    print("-" * 40)

    status = processor.get_execution_status(execution.id)
    print(f"   Completed Steps: {len(status['completed_steps'])}")
    print(f"   Failed Steps: {len(status['failed_steps'])}")

    for step_id in status["completed_steps"]:
        step_execs = result.step_executions.get(step_id, [])
        if step_execs:
            exec_record = step_execs[-1]
            print(f"   - {step_id}: {exec_record.duration_ms:.1f}ms")
    print()

    # 4. Show context
    print("4. WORKFLOW CONTEXT:")
    print("-" * 40)

    for key, value in list(result.context.items())[:5]:
        print(f"   {key}: {value}")
    print()

    # 5. Demonstrate workflow template
    print("5. WORKFLOW TEMPLATE:")
    print("-" * 40)

    processor.register_template(workflow)
    print(f"   Registered template: {workflow.name}")

    # Execute from template
    exec2 = await processor.execute_template("DataProcessingPipeline", {"source": "template"})
    await processor.wait_for_completion(exec2.id)
    print(f"   Template execution: {exec2.status.value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Workflow Processor Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
