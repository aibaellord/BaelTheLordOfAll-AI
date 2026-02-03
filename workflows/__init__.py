"""
BAEL - Workflow System
Composable workflow definitions for complex multi-step tasks.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.Workflows")


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    persona: str  # Which persona handles this
    template: Optional[str]  # Prompt template to use
    inputs: List[str]  # Input variable names
    outputs: List[str]  # Output variable names
    condition: Optional[str] = None  # Condition to execute
    timeout_seconds: int = 300
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "persona": self.persona,
            "template": self.template,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "condition": self.condition,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStep":
        return cls(
            id=data["id"],
            name=data["name"],
            persona=data["persona"],
            template=data.get("template"),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            condition=data.get("condition"),
            timeout_seconds=data.get("timeout_seconds", 300),
            retry_count=data.get("retry_count", 0)
        )


@dataclass
class Workflow:
    """A complete workflow definition."""
    name: str
    description: str
    steps: List[WorkflowStep]
    output: Dict[str, str]  # Maps output names to step outputs
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "output": self.output,
            "version": self.version,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        return cls(
            name=data["name"],
            description=data["description"],
            steps=[WorkflowStep.from_dict(s) for s in data.get("steps", [])],
            output=data.get("output", {}),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", [])
        )


@dataclass
class WorkflowExecution:
    """An execution instance of a workflow."""
    id: str
    workflow_name: str
    status: WorkflowStatus
    current_step: int
    context: Dict[str, Any]  # Variables available to steps
    step_results: List[Dict[str, Any]]
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "current_step": self.current_step,
            "context": self.context,
            "step_results": self.step_results,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


class WorkflowEngine:
    """
    Executes workflows by coordinating steps and personas.

    Provides:
    - Step-by-step execution
    - Context management
    - Error handling
    - Pause/resume capability
    """

    def __init__(self, workflows_dir: Optional[str] = None):
        self.workflows_dir = Path(workflows_dir) if workflows_dir else Path(__file__).parent
        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._step_handlers: Dict[str, Callable] = {}

    def load_workflows(self) -> None:
        """Load all workflow definitions."""
        definitions_dir = self.workflows_dir / "definitions"
        if definitions_dir.exists():
            for file in definitions_dir.glob("*.json"):
                data = json.loads(file.read_text())
                workflow = Workflow.from_dict(data)
                self._workflows[workflow.name] = workflow
                logger.info(f"Loaded workflow: {workflow.name}")

    def register_handler(
        self,
        persona: str,
        handler: Callable[..., Awaitable[Dict[str, Any]]]
    ) -> None:
        """Register a step handler for a persona."""
        self._step_handlers[persona] = handler

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self._workflows.get(name)

    def list_workflows(self) -> List[str]:
        """List available workflows."""
        return list(self._workflows.keys())

    async def start(
        self,
        workflow_name: str,
        initial_context: Dict[str, Any]
    ) -> WorkflowExecution:
        """Start a workflow execution."""
        workflow = self._workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")

        import hashlib
        exec_id = hashlib.md5(
            f"{workflow_name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        execution = WorkflowExecution(
            id=exec_id,
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING,
            current_step=0,
            context=initial_context.copy(),
            step_results=[],
            started_at=datetime.now()
        )

        self._executions[exec_id] = execution

        # Execute steps
        try:
            await self._execute(execution, workflow)
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            logger.error(f"Workflow {workflow_name} failed: {e}")

        return execution

    async def _execute(
        self,
        execution: WorkflowExecution,
        workflow: Workflow
    ) -> None:
        """Execute workflow steps."""
        for i, step in enumerate(workflow.steps):
            if execution.status != WorkflowStatus.RUNNING:
                break

            execution.current_step = i

            # Check condition
            if step.condition:
                if not self._evaluate_condition(step.condition, execution.context):
                    execution.step_results.append({
                        "step_id": step.id,
                        "status": StepStatus.SKIPPED.value,
                        "reason": f"Condition not met: {step.condition}"
                    })
                    continue

            # Get handler
            handler = self._step_handlers.get(step.persona)
            if not handler:
                logger.warning(f"No handler for persona: {step.persona}")
                execution.step_results.append({
                    "step_id": step.id,
                    "status": StepStatus.SKIPPED.value,
                    "reason": f"No handler for {step.persona}"
                })
                continue

            # Prepare inputs
            inputs = {
                name: execution.context.get(name)
                for name in step.inputs
            }

            # Execute step
            try:
                result = await handler(
                    step=step,
                    inputs=inputs,
                    context=execution.context
                )

                # Store outputs
                for output_name in step.outputs:
                    if output_name in result:
                        execution.context[output_name] = result[output_name]

                execution.step_results.append({
                    "step_id": step.id,
                    "status": StepStatus.COMPLETED.value,
                    "outputs": {k: v for k, v in result.items() if k in step.outputs}
                })

            except Exception as e:
                execution.step_results.append({
                    "step_id": step.id,
                    "status": StepStatus.FAILED.value,
                    "error": str(e)
                })
                raise

        execution.status = WorkflowStatus.COMPLETED
        execution.completed_at = datetime.now()

    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition string."""
        # Simple condition evaluation
        # In production, use a proper expression parser
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except:
            return False

    def pause(self, execution_id: str) -> bool:
        """Pause a workflow execution."""
        if execution_id in self._executions:
            self._executions[execution_id].status = WorkflowStatus.PAUSED
            return True
        return False

    def resume(self, execution_id: str) -> bool:
        """Resume a paused workflow."""
        if execution_id in self._executions:
            self._executions[execution_id].status = WorkflowStatus.RUNNING
            return True
        return False

    def cancel(self, execution_id: str) -> bool:
        """Cancel a workflow execution."""
        if execution_id in self._executions:
            self._executions[execution_id].status = WorkflowStatus.CANCELLED
            return True
        return False

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get an execution by ID."""
        return self._executions.get(execution_id)


# Global engine instance
engine = WorkflowEngine()

__all__ = [
    "WorkflowStatus",
    "StepStatus",
    "WorkflowStep",
    "Workflow",
    "WorkflowExecution",
    "WorkflowEngine",
    "engine"
]
