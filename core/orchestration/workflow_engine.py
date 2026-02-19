"""
⚡ WORKFLOW ENGINE ⚡
====================
Advanced workflow definition and execution.

Features:
- DAG-based workflows
- Conditional branching
- Parallel execution
- State management
"""

import math
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class WorkflowState(Enum):
    """Workflow execution states"""
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class WorkflowCondition:
    """Condition for workflow transitions"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Condition function
    predicate: Optional[Callable[[Dict[str, Any]], bool]] = None

    # Simple expression-based condition
    variable: str = ""
    operator: str = "=="  # ==, !=, >, <, >=, <=, in, not_in
    value: Any = None

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition"""
        if self.predicate:
            return self.predicate(context)

        if not self.variable:
            return True

        actual = context.get(self.variable)

        if self.operator == "==":
            return actual == self.value
        elif self.operator == "!=":
            return actual != self.value
        elif self.operator == ">":
            return actual > self.value
        elif self.operator == "<":
            return actual < self.value
        elif self.operator == ">=":
            return actual >= self.value
        elif self.operator == "<=":
            return actual <= self.value
        elif self.operator == "in":
            return actual in self.value
        elif self.operator == "not_in":
            return actual not in self.value

        return True


@dataclass
class WorkflowStep:
    """Single step in workflow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Execution
    handler: Optional[Callable] = None
    is_async: bool = False
    timeout: float = 300.0  # 5 minutes default

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0

    # Input/Output
    input_mapping: Dict[str, str] = field(default_factory=dict)  # context_key -> param_name
    output_key: str = ""  # Key to store result

    # State
    state: WorkflowState = WorkflowState.PENDING
    result: Any = None
    error: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowTransition:
    """Transition between workflow steps"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_step: str = ""  # Step ID
    to_step: str = ""    # Step ID

    # Condition
    condition: Optional[WorkflowCondition] = None

    # Priority (higher = checked first)
    priority: int = 0

    def can_transition(self, context: Dict[str, Any]) -> bool:
        """Check if transition is valid"""
        if self.condition:
            return self.condition.evaluate(context)
        return True


@dataclass
class WorkflowDefinition:
    """Definition of a workflow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    # Steps
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)

    # Transitions
    transitions: List[WorkflowTransition] = field(default_factory=list)

    # Entry/Exit
    entry_step: str = ""
    exit_steps: Set[str] = field(default_factory=set)

    # Metadata
    created: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: WorkflowStep):
        """Add step to workflow"""
        self.steps[step.id] = step

        if not self.entry_step:
            self.entry_step = step.id

    def add_transition(
        self,
        from_step: str,
        to_step: str,
        condition: WorkflowCondition = None
    ) -> WorkflowTransition:
        """Add transition between steps"""
        transition = WorkflowTransition(
            from_step=from_step,
            to_step=to_step,
            condition=condition
        )
        self.transitions.append(transition)
        return transition

    def get_outgoing(self, step_id: str) -> List[WorkflowTransition]:
        """Get outgoing transitions from step"""
        return [t for t in self.transitions if t.from_step == step_id]

    def validate(self) -> List[str]:
        """Validate workflow definition"""
        errors = []

        if not self.entry_step:
            errors.append("No entry step defined")
        elif self.entry_step not in self.steps:
            errors.append(f"Entry step {self.entry_step} not found")

        for exit_step in self.exit_steps:
            if exit_step not in self.steps:
                errors.append(f"Exit step {exit_step} not found")

        for trans in self.transitions:
            if trans.from_step not in self.steps:
                errors.append(f"Transition from unknown step {trans.from_step}")
            if trans.to_step not in self.steps:
                errors.append(f"Transition to unknown step {trans.to_step}")

        return errors


@dataclass
class WorkflowInstance:
    """Running instance of a workflow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    definition_id: str = ""

    # State
    state: WorkflowState = WorkflowState.PENDING
    current_step: Optional[str] = None

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    # History
    step_history: List[str] = field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    result: Any = None
    error: Optional[str] = None


class WorkflowEngine:
    """
    Executes workflow definitions.
    """

    def __init__(self):
        self.definitions: Dict[str, WorkflowDefinition] = {}
        self.instances: Dict[str, WorkflowInstance] = {}

        # Callbacks
        self.on_step_start: Optional[Callable] = None
        self.on_step_complete: Optional[Callable] = None
        self.on_workflow_complete: Optional[Callable] = None

    def register(self, definition: WorkflowDefinition):
        """Register workflow definition"""
        errors = definition.validate()
        if errors:
            raise ValueError(f"Invalid workflow: {errors}")

        self.definitions[definition.id] = definition

    def create_instance(
        self,
        definition_id: str,
        initial_context: Dict[str, Any] = None
    ) -> WorkflowInstance:
        """Create workflow instance"""
        if definition_id not in self.definitions:
            raise ValueError(f"Unknown workflow: {definition_id}")

        instance = WorkflowInstance(
            definition_id=definition_id,
            context=initial_context or {}
        )

        self.instances[instance.id] = instance
        return instance

    def start(self, instance_id: str):
        """Start workflow execution"""
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Unknown instance: {instance_id}")

        definition = self.definitions[instance.definition_id]

        instance.state = WorkflowState.RUNNING
        instance.started_at = datetime.now()
        instance.current_step = definition.entry_step

        self._execute_step(instance, definition)

    def _execute_step(
        self,
        instance: WorkflowInstance,
        definition: WorkflowDefinition
    ):
        """Execute current step"""
        step_id = instance.current_step
        if not step_id or step_id not in definition.steps:
            self._complete_workflow(instance)
            return

        step = definition.steps[step_id]

        # Callback
        if self.on_step_start:
            self.on_step_start(instance, step)

        step.state = WorkflowState.RUNNING
        step.started_at = datetime.now()

        try:
            # Prepare inputs
            inputs = {}
            for context_key, param_name in step.input_mapping.items():
                if context_key in instance.context:
                    inputs[param_name] = instance.context[context_key]

            # Execute handler
            if step.handler:
                result = step.handler(**inputs)
                step.result = result

                # Store in context
                if step.output_key:
                    instance.context[step.output_key] = result

            step.state = WorkflowState.COMPLETED
            step.completed_at = datetime.now()
            instance.step_history.append(step_id)

            # Callback
            if self.on_step_complete:
                self.on_step_complete(instance, step)

            # Find next step
            self._transition(instance, definition)

        except Exception as e:
            step.state = WorkflowState.FAILED
            step.error = str(e)

            if step.max_retries > 0:
                step.max_retries -= 1
                # Retry
                self._execute_step(instance, definition)
            else:
                instance.state = WorkflowState.FAILED
                instance.error = f"Step {step.name} failed: {e}"

    def _transition(
        self,
        instance: WorkflowInstance,
        definition: WorkflowDefinition
    ):
        """Transition to next step"""
        current = instance.current_step

        # Check if exit step
        if current in definition.exit_steps:
            self._complete_workflow(instance)
            return

        # Find valid transition
        transitions = definition.get_outgoing(current)
        transitions.sort(key=lambda t: -t.priority)

        for trans in transitions:
            if trans.can_transition(instance.context):
                instance.current_step = trans.to_step
                self._execute_step(instance, definition)
                return

        # No valid transition found
        self._complete_workflow(instance)

    def _complete_workflow(self, instance: WorkflowInstance):
        """Complete workflow execution"""
        instance.state = WorkflowState.COMPLETED
        instance.completed_at = datetime.now()
        instance.result = instance.context

        if self.on_workflow_complete:
            self.on_workflow_complete(instance)

    def pause(self, instance_id: str):
        """Pause workflow"""
        instance = self.instances.get(instance_id)
        if instance:
            instance.state = WorkflowState.PAUSED

    def resume(self, instance_id: str):
        """Resume paused workflow"""
        instance = self.instances.get(instance_id)
        if instance and instance.state == WorkflowState.PAUSED:
            instance.state = WorkflowState.RUNNING
            definition = self.definitions[instance.definition_id]
            self._execute_step(instance, definition)


class ParallelExecutor:
    """
    Executes workflow steps in parallel.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    async def execute_parallel(
        self,
        steps: List[WorkflowStep],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute steps in parallel"""
        tasks = []

        for step in steps:
            if step.is_async:
                task = self._execute_async(step, context)
            else:
                task = asyncio.to_thread(self._execute_sync, step, context)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for step, result in zip(steps, results):
            if isinstance(result, Exception):
                step.state = WorkflowState.FAILED
                step.error = str(result)
            else:
                step.result = result
                if step.output_key:
                    output[step.output_key] = result

        return output

    async def _execute_async(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Any:
        """Execute async step"""
        inputs = {
            param: context.get(key)
            for key, param in step.input_mapping.items()
        }
        return await step.handler(**inputs)

    def _execute_sync(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Any:
        """Execute sync step"""
        inputs = {
            param: context.get(key)
            for key, param in step.input_mapping.items()
        }
        return step.handler(**inputs)


# Export all
__all__ = [
    'WorkflowState',
    'WorkflowCondition',
    'WorkflowStep',
    'WorkflowTransition',
    'WorkflowDefinition',
    'WorkflowInstance',
    'WorkflowEngine',
    'ParallelExecutor',
]
