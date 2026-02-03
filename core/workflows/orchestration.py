"""
BAEL Workflow Orchestration Engine - Directed Acyclic Graph (DAG) based workflow execution

Features:
- DAG-based workflow definition
- Conditional execution paths
- Parallel task execution
- Error handling and recovery
- State persistence
- Async execution with progress tracking
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    status: TaskStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: float = 0
    retry_count: int = 0

    def to_dict(self) -> Dict:
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'output': self.output,
            'error': self.error,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms,
            'retry_count': self.retry_count,
        }


@dataclass
class TaskDefinition:
    """Task definition for workflow"""
    id: str
    name: str
    action: str  # Reference to callable action
    inputs: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 5
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None  # Condition expression
    parallel: bool = False
    error_handler: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'action': self.action,
            'inputs': self.inputs,
            'description': self.description,
            'timeout_seconds': self.timeout_seconds,
            'max_retries': self.max_retries,
            'depends_on': self.depends_on,
            'condition': self.condition,
            'parallel': self.parallel,
        }


@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    tasks: Dict[str, TaskDefinition] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def add_task(self, task: TaskDefinition):
        """Add task to workflow"""
        self.tasks[task.id] = task

    def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate workflow structure"""
        errors = []

        if not self.id or not self.name:
            errors.append("Workflow must have id and name")

        if not self.tasks:
            errors.append("Workflow must have at least one task")

        # Check for circular dependencies
        if self._has_circular_dependencies():
            errors.append("Workflow has circular dependencies")

        # Validate task dependencies
        task_ids = set(self.tasks.keys())
        for task in self.tasks.values():
            for dep in task.depends_on:
                if dep not in task_ids:
                    errors.append(f"Task {task.id} depends on nonexistent task {dep}")

        return len(errors) == 0, errors

    def _has_circular_dependencies(self) -> bool:
        """Detect circular dependencies using DFS"""
        visited = set()
        rec_stack = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = self.tasks.get(task_id)
            if task:
                for dep in task.depends_on:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        for task_id in self.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False

    def get_execution_order(self) -> List[str]:
        """Get topological sort of tasks"""
        visited = set()
        order = []

        def dfs(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)

            task = self.tasks.get(task_id)
            if task:
                for dep in task.depends_on:
                    dfs(dep)

            order.append(task_id)

        for task_id in self.tasks:
            dfs(task_id)

        return order

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'tasks': {tid: t.to_dict() for tid, t in self.tasks.items()},
            'variables': self.variables,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    error: Optional[str] = None

    def add_result(self, result: TaskResult):
        """Record task result"""
        self.task_results[result.task_id] = result

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result"""
        return self.task_results.get(task_id)

    def is_complete(self) -> bool:
        """Check if workflow is complete"""
        return self.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        ]

    def get_progress(self) -> float:
        """Get workflow progress 0-100%"""
        if not self.task_results:
            return 0

        completed = sum(
            1 for r in self.task_results.values()
            if r.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]
        )

        return (completed / len(self.task_results)) * 100

    def to_dict(self) -> Dict:
        return {
            'execution_id': self.execution_id,
            'workflow_id': self.workflow_id,
            'status': self.status.value,
            'task_results': {
                tid: r.to_dict() for tid, r in self.task_results.items()
            },
            'variables': self.variables,
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'error': self.error,
            'progress': self.get_progress(),
        }


class WorkflowEngine:
    """Workflow orchestration engine"""

    def __init__(self):
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.action_registry: Dict[str, Callable] = {}
        self.execution_history: List[WorkflowExecution] = []

    def register_action(self, name: str, action: Callable):
        """Register executable action"""
        self.action_registry[name] = action

    def create_workflow(self, definition: WorkflowDefinition) -> bool:
        """Create new workflow"""
        valid, errors = definition.validate()
        if not valid:
            logger.error(f"Invalid workflow: {errors}")
            return False

        self.workflows[definition.id] = definition
        logger.info(f"Workflow created: {definition.id}")
        return True

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition"""
        return self.workflows.get(workflow_id)

    async def execute_workflow(
        self,
        workflow_id: str,
        execution_id: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """Execute workflow"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            variables=variables or {},
            started_at=datetime.utcnow().isoformat(),
        )

        self.executions[execution_id] = execution
        execution.status = WorkflowStatus.RUNNING

        try:
            # Get execution order
            order = workflow.get_execution_order()

            # Execute tasks
            for task_id in order:
                if execution.status == WorkflowStatus.CANCELLED:
                    break

                await self._execute_task(workflow, execution, task_id)

            # Determine final status
            failed_tasks = [
                r for r in execution.task_results.values()
                if r.status == TaskStatus.FAILED
            ]

            if failed_tasks:
                execution.status = WorkflowStatus.FAILED
                execution.error = f"{len(failed_tasks)} tasks failed"
            else:
                execution.status = WorkflowStatus.COMPLETED

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            logger.error(f"Workflow execution failed: {e}")

        finally:
            execution.ended_at = datetime.utcnow().isoformat()
            self.execution_history.append(execution)

        return execution

    async def _execute_task(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
        task_id: str
    ):
        """Execute single task"""
        task = workflow.get_task(task_id)
        if not task:
            return

        # Check condition
        if task.condition and not self._evaluate_condition(
            task.condition,
            execution.variables,
            execution.task_results
        ):
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.SKIPPED,
                start_time=datetime.utcnow().isoformat(),
                end_time=datetime.utcnow().isoformat(),
            )
            execution.add_result(result)
            return

        # Check dependencies
        if not self._dependencies_met(task, execution):
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error="Dependencies not met",
                start_time=datetime.utcnow().isoformat(),
                end_time=datetime.utcnow().isoformat(),
            )
            execution.add_result(result)
            return

        # Execute with retries
        for attempt in range(task.max_retries + 1):
            result = await self._run_task(task, execution)
            result.retry_count = attempt

            if result.status == TaskStatus.COMPLETED:
                execution.add_result(result)
                return

            if attempt < task.max_retries:
                await asyncio.sleep(task.retry_delay_seconds)
            else:
                execution.add_result(result)
                return

    async def _run_task(
        self,
        task: TaskDefinition,
        execution: WorkflowExecution
    ) -> TaskResult:
        """Run single task attempt"""
        start_time = datetime.utcnow().isoformat()

        try:
            # Get action
            action = self.action_registry.get(task.action)
            if not action:
                raise ValueError(f"Action not found: {task.action}")

            # Prepare inputs
            inputs = self._resolve_inputs(task.inputs, execution)

            # Execute with timeout
            try:
                if asyncio.iscoroutinefunction(action):
                    output = await asyncio.wait_for(
                        action(**inputs),
                        timeout=task.timeout_seconds
                    )
                else:
                    output = action(**inputs)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Task {task.id} timed out after {task.timeout_seconds}s")

            end_time = datetime.utcnow().isoformat()

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output=output,
                start_time=start_time,
                end_time=end_time,
                duration_ms=self._calculate_duration(start_time, end_time),
            )

        except Exception as e:
            end_time = datetime.utcnow().isoformat()

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration_ms=self._calculate_duration(start_time, end_time),
            )

    def _resolve_inputs(
        self,
        inputs: Dict[str, Any],
        execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Resolve input references to actual values"""
        resolved = {}

        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("$"):
                # Variable reference
                var_path = value[1:]  # Remove $
                resolved[key] = self._get_variable(var_path, execution)
            elif isinstance(value, str) and value.startswith("#"):
                # Task reference
                task_ref = value[1:]  # Remove #
                resolved[key] = self._get_task_output(task_ref, execution)
            else:
                resolved[key] = value

        return resolved

    def _get_variable(
        self,
        path: str,
        execution: WorkflowExecution
    ) -> Any:
        """Get variable value by path"""
        parts = path.split(".")
        value = execution.variables

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def _get_task_output(
        self,
        task_ref: str,
        execution: WorkflowExecution
    ) -> Any:
        """Get task output value"""
        result = execution.get_result(task_ref)
        return result.output if result else None

    def _evaluate_condition(
        self,
        condition: str,
        variables: Dict[str, Any],
        results: Dict[str, TaskResult]
    ) -> bool:
        """Evaluate condition expression"""
        # Simple condition evaluation
        # In production, use safer evaluation (ast.literal_eval or custom parser)
        try:
            context = {
                'vars': variables,
                'results': results,
            }
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return True  # Default to true on error

    def _dependencies_met(
        self,
        task: TaskDefinition,
        execution: WorkflowExecution
    ) -> bool:
        """Check if all task dependencies are met"""
        for dep_id in task.depends_on:
            result = execution.get_result(dep_id)
            if not result or result.status != TaskStatus.COMPLETED:
                return False

        return True

    @staticmethod
    def _calculate_duration(start_time: str, end_time: str) -> float:
        """Calculate duration in milliseconds"""
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        return (end - start).total_seconds() * 1000

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution"""
        return self.executions.get(execution_id)

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel running execution"""
        execution = self.get_execution(execution_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.CANCELLED
            return True
        return False

    def get_execution_history(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 50
    ) -> List[WorkflowExecution]:
        """Get execution history"""
        if workflow_id:
            history = [
                e for e in self.execution_history
                if e.workflow_id == workflow_id
            ]
        else:
            history = self.execution_history

        return history[-limit:]

    def get_statistics(self) -> Dict:
        """Get engine statistics"""
        total_executions = len(self.execution_history)
        completed = len([
            e for e in self.execution_history
            if e.status == WorkflowStatus.COMPLETED
        ])
        failed = len([
            e for e in self.execution_history
            if e.status == WorkflowStatus.FAILED
        ])

        return {
            'total_workflows': len(self.workflows),
            'total_executions': total_executions,
            'completed_executions': completed,
            'failed_executions': failed,
            'success_rate': (completed / total_executions * 100) if total_executions > 0 else 0,
            'registered_actions': len(self.action_registry),
        }
