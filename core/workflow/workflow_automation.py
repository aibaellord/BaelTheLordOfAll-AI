"""
Workflow Automation Engine - BPMN-based workflow execution and management.

Features:
- BPMN-based workflow definition
- Conditional logic and branching
- Task automation
- Approval workflows
- Workflow versioning
- Execution history and audit

Target: 1,500+ lines for complete workflow engine
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

# ============================================================================
# WORKFLOW ENUMS
# ============================================================================

class TaskType(Enum):
    """Workflow task types."""
    START = "START"
    END = "END"
    ACTIVITY = "ACTIVITY"
    DECISION = "DECISION"
    WAIT = "WAIT"
    APPROVAL = "APPROVAL"
    PARALLEL = "PARALLEL"
    LOOP = "LOOP"

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    WAITING = "WAITING"
    SKIPPED = "SKIPPED"

class WorkflowStatus(Enum):
    """Workflow execution status."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"

class ApprovalStatus(Enum):
    """Approval task status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class WorkflowVariable:
    """Workflow variable."""
    name: str
    value: Any
    type: str
    scope: str = "process"

@dataclass
class Task:
    """Single workflow task."""
    id: str
    type: TaskType
    name: str
    description: str
    handler: Optional[Callable] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

@dataclass
class ApprovalTask(Task):
    """Approval task."""
    assignee: str = ""
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    comments: str = ""

@dataclass
class Transition:
    """Flow transition between tasks."""
    id: str
    from_task: str
    to_task: str
    condition: Optional[Callable] = None
    label: str = ""

@dataclass
class WorkflowDefinition:
    """Workflow template definition."""
    id: str
    name: str
    version: str
    description: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    transitions: List[Transition] = field(default_factory=list)
    variables: Dict[str, WorkflowVariable] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class WorkflowExecution:
    """Workflow instance execution."""
    id: str
    definition_id: str
    status: WorkflowStatus = WorkflowStatus.IN_PROGRESS
    tasks: Dict[str, Task] = field(default_factory=dict)
    variables: Dict[str, WorkflowVariable] = field(default_factory=dict)
    current_task: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

# ============================================================================
# WORKFLOW BUILDER
# ============================================================================

class WorkflowBuilder:
    """Build workflow definitions."""

    def __init__(self, name: str, version: str = "1.0"):
        self.definition = WorkflowDefinition(
            id=f"wf-{uuid.uuid4().hex[:8]}",
            name=name,
            version=version,
            description=""
        )
        self.logger = logging.getLogger("workflow_builder")

    def add_task(self, task: Task) -> 'WorkflowBuilder':
        """Add task to workflow."""
        self.definition.tasks[task.id] = task
        self.logger.info(f"Added task: {task.name}")
        return self

    def add_transition(self, transition: Transition) -> 'WorkflowBuilder':
        """Add transition between tasks."""
        self.definition.transitions.append(transition)
        self.logger.info(f"Added transition: {transition.label}")
        return self

    def add_variable(self, variable: WorkflowVariable) -> 'WorkflowBuilder':
        """Add workflow variable."""
        self.definition.variables[variable.name] = variable
        return self

    def set_description(self, description: str) -> 'WorkflowBuilder':
        """Set workflow description."""
        self.definition.description = description
        return self

    def build(self) -> WorkflowDefinition:
        """Build and return definition."""
        self.logger.info(f"Built workflow: {self.definition.name}")
        return self.definition

# ============================================================================
# WORKFLOW ENGINE
# ============================================================================

class WorkflowEngine:
    """Execute workflow definitions."""

    def __init__(self):
        self.definitions: Dict[str, WorkflowDefinition] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.execution_history: List[WorkflowExecution] = []
        self.task_handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("workflow_engine")

    def register_definition(self, definition: WorkflowDefinition) -> None:
        """Register workflow definition."""
        self.definitions[definition.id] = definition
        self.logger.info(f"Registered workflow: {definition.name}")

    def register_task_handler(self, task_type: str, handler: Callable) -> None:
        """Register task handler."""
        self.task_handlers[task_type] = handler
        self.logger.info(f"Registered handler: {task_type}")

    async def execute_workflow(self, definition_id: str,
                              context: Dict[str, Any] = None) -> Optional[WorkflowExecution]:
        """Execute workflow."""
        definition = self.definitions.get(definition_id)

        if definition is None:
            self.logger.error(f"Definition not found: {definition_id}")
            return None

        # Create execution instance
        execution = WorkflowExecution(
            id=f"exec-{uuid.uuid4().hex[:8]}",
            definition_id=definition_id,
            tasks={},
            variables={k: v for k, v in definition.variables.items()},
            current_task=None
        )

        # Copy context to variables
        if context:
            for key, value in context.items():
                execution.variables[key] = WorkflowVariable(
                    name=key,
                    value=value,
                    type=type(value).__name__
                )

        self.executions[execution.id] = execution

        # Find start task
        start_task_id = None
        for task_id, task in definition.tasks.items():
            if task.type == TaskType.START:
                start_task_id = task_id
                break

        if start_task_id:
            await self._execute_task(execution, definition, start_task_id)

        execution.status = WorkflowStatus.COMPLETED
        execution.completed_at = datetime.now()
        execution.duration_seconds = (
            execution.completed_at - execution.started_at
        ).total_seconds()

        self.execution_history.append(execution)

        return execution

    async def _execute_task(self, execution: WorkflowExecution,
                           definition: WorkflowDefinition,
                           task_id: str) -> None:
        """Execute single task."""
        task = definition.tasks.get(task_id)

        if task is None:
            return

        # Create execution copy
        exec_task = Task(
            id=task.id,
            type=task.type,
            name=task.name,
            description=task.description,
            handler=task.handler,
            inputs=task.inputs.copy(),
            outputs={},
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now()
        )

        execution.current_task = task_id
        execution.tasks[task_id] = exec_task

        try:
            # Execute handler if exists
            if task.handler:
                handler = self.task_handlers.get(task.type.value)
                if handler:
                    result = await handler(task, execution)
                    exec_task.outputs = result or {}

            exec_task.status = TaskStatus.COMPLETED
            exec_task.completed_at = datetime.now()
            exec_task.duration_seconds = (
                exec_task.completed_at - exec_task.started_at
            ).total_seconds()

            # Find next task(s)
            for transition in definition.transitions:
                if transition.from_task == task_id:
                    if transition.condition is None or await transition.condition(execution):
                        await self._execute_task(
                            execution, definition, transition.to_task
                        )

        except Exception as e:
            self.logger.error(f"Task error: {e}")
            exec_task.status = TaskStatus.FAILED

# ============================================================================
# APPROVAL WORKFLOW MANAGER
# ============================================================================

class ApprovalWorkflow:
    """Manage approval-based workflows."""

    def __init__(self, workflow_engine: WorkflowEngine):
        self.engine = workflow_engine
        self.pending_approvals: Dict[str, ApprovalTask] = {}
        self.approval_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("approval_workflow")

    async def create_approval_task(self, execution_id: str, task_id: str,
                                  assignee: str) -> ApprovalTask:
        """Create approval task."""
        approval = ApprovalTask(
            id=f"apt-{uuid.uuid4().hex[:8]}",
            type=TaskType.APPROVAL,
            name="Approval Required",
            description="Pending approval",
            assignee=assignee,
            approval_status=ApprovalStatus.PENDING
        )

        self.pending_approvals[approval.id] = approval
        return approval

    async def approve(self, approval_id: str, approved_by: str,
                     comments: str = "") -> bool:
        """Approve task."""
        approval = self.pending_approvals.get(approval_id)

        if approval is None:
            return False

        approval.approval_status = ApprovalStatus.APPROVED
        approval.approved_by = approved_by
        approval.comments = comments
        approval.completed_at = datetime.now()

        self.approval_history.append({
            'approval_id': approval_id,
            'approved_by': approved_by,
            'timestamp': datetime.now(),
            'comments': comments
        })

        self.logger.info(f"Approved: {approval_id}")
        return True

    async def reject(self, approval_id: str, rejected_by: str,
                    comments: str = "") -> bool:
        """Reject task."""
        approval = self.pending_approvals.get(approval_id)

        if approval is None:
            return False

        approval.approval_status = ApprovalStatus.REJECTED
        approval.comments = comments

        self.logger.warning(f"Rejected: {approval_id}")
        return True

# ============================================================================
# WORKFLOW MANAGEMENT SYSTEM
# ============================================================================

class WorkflowManagementSystem:
    """Complete workflow management system."""

    def __init__(self):
        self.engine = WorkflowEngine()
        self.approval_workflow = ApprovalWorkflow(self.engine)
        self.logger = logging.getLogger("workflow_management")

    def create_builder(self, name: str) -> WorkflowBuilder:
        """Create workflow builder."""
        return WorkflowBuilder(name)

    async def execute(self, definition_id: str,
                     context: Dict[str, Any] = None) -> Optional[WorkflowExecution]:
        """Execute workflow."""
        return await self.engine.execute_workflow(definition_id, context)

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by ID."""
        return self.engine.executions.get(execution_id)

    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status."""
        execution = self.engine.executions.get(execution_id)

        if execution is None:
            return {}

        return {
            'id': execution.id,
            'status': execution.status.value,
            'current_task': execution.current_task,
            'completed_tasks': len([
                t for t in execution.tasks.values()
                if t.status == TaskStatus.COMPLETED
            ]),
            'total_tasks': len(execution.tasks),
            'duration_seconds': execution.duration_seconds
        }

def create_workflow_system() -> WorkflowManagementSystem:
    """Create workflow management system."""
    return WorkflowManagementSystem()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    wf_sys = create_workflow_system()
    print("Workflow management system initialized")
