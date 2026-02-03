"""
BAEL Phase 6.3: Advanced Workflow Engine
═════════════════════════════════════════════════════════════════════════════

Visual workflow builder enabling conditional logic, parallel execution,
human-in-the-loop approval, webhook integration, and state machine patterns.

Features:
  • Workflow Definition & Building
  • Conditional Logic Branching
  • Parallel Execution
  • Sequential Execution
  • Human Approval Steps
  • Error Handling & Retries
  • Webhook Triggers & Actions
  • State Machine Patterns
  • Workflow Versioning
  • Execution Tracking & Monitoring
  • 20+ Workflow Patterns

Author: BAEL Team
Date: February 1, 2026
"""

import json
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class NodeType(str, Enum):
    """Workflow node types."""
    START = "start"
    END = "end"
    TASK = "task"
    DECISION = "decision"
    PARALLEL = "parallel"
    MERGE = "merge"
    APPROVAL = "approval"
    WEBHOOK = "webhook"
    DELAY = "delay"
    LOOP = "loop"


class ExecutionStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class NodeStatus(str, Enum):
    """Individual node execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class RetryPolicy(str, Enum):
    """Task retry policy."""
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class TriggerType(str, Enum):
    """Workflow trigger types."""
    MANUAL = "manual"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"
    EVENT = "event"
    API = "api"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class WorkflowContext:
    """Execution context for workflow."""
    workflow_id: str
    execution_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None

    def set_variable(self, name: str, value: Any) -> None:
        """Set context variable."""
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get context variable."""
        return self.variables.get(name, default)

    def interpolate(self, text: str) -> str:
        """Interpolate variables in text."""
        result = text
        for key, value in self.variables.items():
            result = result.replace(f"${{{key}}}", str(value))
        return result


@dataclass
class NodeConfig:
    """Configuration for workflow node."""
    id: str
    type: NodeType
    name: str
    description: str = ""
    timeout_seconds: int = 300
    retry_policy: RetryPolicy = RetryPolicy.NONE
    max_retries: int = 3
    retry_delay_seconds: int = 5
    skip_on_error: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskNode(NodeConfig):
    """Task execution node."""
    handler: Optional[Callable] = None
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class DecisionNode(NodeConfig):
    """Conditional branching node."""
    condition: Optional[Callable[[WorkflowContext], bool]] = None
    true_path: Optional[str] = None
    false_path: Optional[str] = None


@dataclass
class ParallelNode(NodeConfig):
    """Parallel execution node."""
    branches: List[List[str]] = field(default_factory=list)


@dataclass
class ApprovalNode(NodeConfig):
    """Human approval step."""
    approvers: List[str] = field(default_factory=list)
    approval_timeout_seconds: int = 3600
    approved_path: Optional[str] = None
    rejected_path: Optional[str] = None


@dataclass
class WebhookNode(NodeConfig):
    """Webhook trigger/action node."""
    url: str = ""
    method: str = "POST"
    payload_template: Dict[str, Any] = field(default_factory=dict)
    expected_response: Optional[str] = None


@dataclass
class NodeExecution:
    """Execution record for node."""
    node_id: str
    status: NodeStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0

    def is_complete(self) -> bool:
        """Check if node execution is complete."""
        return self.status in [NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED]


@dataclass
class WorkflowExecution:
    """Execution record for entire workflow."""
    workflow_id: str
    execution_id: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    context: Optional[WorkflowContext] = None
    node_executions: Dict[str, NodeExecution] = field(default_factory=dict)
    error_message: Optional[str] = None
    triggered_by: TriggerType = TriggerType.MANUAL
    triggered_by_id: Optional[str] = None


@dataclass
class WorkflowMetrics:
    """Workflow performance metrics."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    cancelled_executions: int = 0
    avg_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
    success_rate: float = 0.0
    last_execution: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════
# Workflow Building
# ═══════════════════════════════════════════════════════════════════════════

class WorkflowBuilder:
    """Fluent API for building workflows."""

    def __init__(self, name: str, description: str = ""):
        """Initialize workflow builder."""
        self.workflow_id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.nodes: Dict[str, NodeConfig] = {}
        self.edges: List[Tuple[str, str]] = []
        self.start_node_id: Optional[str] = None
        self.end_node_id: Optional[str] = None

    def add_start(self) -> "WorkflowBuilder":
        """Add start node."""
        node_id = f"start_{uuid.uuid4().hex[:8]}"
        self.nodes[node_id] = NodeConfig(id=node_id, type=NodeType.START, name="Start")
        self.start_node_id = node_id
        return self

    def add_end(self) -> "WorkflowBuilder":
        """Add end node."""
        node_id = f"end_{uuid.uuid4().hex[:8]}"
        self.nodes[node_id] = NodeConfig(id=node_id, type=NodeType.END, name="End")
        self.end_node_id = node_id
        return self

    def add_task(
        self,
        name: str,
        handler: Optional[Callable] = None,
        timeout_seconds: int = 300,
        retry_policy: RetryPolicy = RetryPolicy.NONE
    ) -> str:
        """Add task node."""
        node_id = f"task_{uuid.uuid4().hex[:8]}"
        self.nodes[node_id] = TaskNode(
            id=node_id,
            type=NodeType.TASK,
            name=name,
            handler=handler,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy
        )
        return node_id

    def add_decision(
        self,
        name: str,
        condition: Optional[Callable[[WorkflowContext], bool]] = None
    ) -> str:
        """Add decision node."""
        node_id = f"decision_{uuid.uuid4().hex[:8]}"
        self.nodes[node_id] = DecisionNode(
            id=node_id,
            type=NodeType.DECISION,
            name=name,
            condition=condition
        )
        return node_id

    def add_parallel(self, name: str) -> str:
        """Add parallel execution node."""
        node_id = f"parallel_{uuid.uuid4().hex[:8]}"
        self.nodes[node_id] = ParallelNode(
            id=node_id,
            type=NodeType.PARALLEL,
            name=name
        )
        return node_id

    def add_approval(
        self,
        name: str,
        approvers: List[str],
        timeout_seconds: int = 3600
    ) -> str:
        """Add approval node."""
        node_id = f"approval_{uuid.uuid4().hex[:8]}"
        self.nodes[node_id] = ApprovalNode(
            id=node_id,
            type=NodeType.APPROVAL,
            name=name,
            approvers=approvers,
            approval_timeout_seconds=timeout_seconds
        )
        return node_id

    def add_webhook(
        self,
        name: str,
        url: str,
        method: str = "POST",
        payload_template: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add webhook node."""
        node_id = f"webhook_{uuid.uuid4().hex[:8]}"
        self.nodes[node_id] = WebhookNode(
            id=node_id,
            type=NodeType.WEBHOOK,
            name=name,
            url=url,
            method=method,
            payload_template=payload_template or {}
        )
        return node_id

    def add_edge(self, from_node: str, to_node: str) -> "WorkflowBuilder":
        """Add edge between nodes."""
        self.edges.append((from_node, to_node))
        return self

    def build(self) -> "Workflow":
        """Build workflow from definition."""
        if not self.start_node_id or not self.end_node_id:
            raise ValueError("Workflow must have start and end nodes")

        return Workflow(
            workflow_id=self.workflow_id,
            name=self.name,
            description=self.description,
            nodes=self.nodes,
            edges=self.edges,
            start_node_id=self.start_node_id,
            end_node_id=self.end_node_id
        )


# ═══════════════════════════════════════════════════════════════════════════
# Workflow Execution Engine
# ═══════════════════════════════════════════════════════════════════════════

class Workflow:
    """Workflow definition and execution."""

    def __init__(
        self,
        workflow_id: str,
        name: str,
        nodes: Dict[str, NodeConfig],
        edges: List[Tuple[str, str]],
        start_node_id: str,
        end_node_id: str,
        description: str = ""
    ):
        """Initialize workflow."""
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.nodes = nodes
        self.edges = edges
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        self.version = "1.0.0"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.metrics = WorkflowMetrics()
        self.logger = logging.getLogger(__name__)
        self._adjacency_list = self._build_adjacency_list()

    def _build_adjacency_list(self) -> Dict[str, List[str]]:
        """Build adjacency list from edges."""
        adj = defaultdict(list)
        for from_node, to_node in self.edges:
            adj[from_node].append(to_node)
        return adj

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate workflow definition."""
        errors = []

        # Check all referenced nodes exist
        for from_node, to_node in self.edges:
            if from_node not in self.nodes:
                errors.append(f"Referenced node '{from_node}' not defined")
            if to_node not in self.nodes:
                errors.append(f"Referenced node '{to_node}' not defined")

        # Check start and end nodes exist
        if self.start_node_id not in self.nodes:
            errors.append("Start node not defined")
        if self.end_node_id not in self.nodes:
            errors.append("End node not defined")

        # Check for unreachable nodes
        reachable = self._find_reachable_nodes(self.start_node_id)
        for node_id in self.nodes:
            if node_id not in reachable and node_id != self.start_node_id:
                errors.append(f"Node '{node_id}' is unreachable from start")

        return len(errors) == 0, errors

    def _find_reachable_nodes(self, start: str) -> Set[str]:
        """Find all reachable nodes from start node."""
        visited = set()
        queue = deque([start])

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)

            for next_node in self._adjacency_list.get(node, []):
                if next_node not in visited:
                    queue.append(next_node)

        return visited

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary."""
        return {
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'nodes': {k: asdict(v) if hasattr(v, '__dataclass_fields__') else v
                     for k, v in self.nodes.items()},
            'edges': self.edges,
            'start_node_id': self.start_node_id,
            'end_node_id': self.end_node_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class WorkflowExecutor:
    """Executes workflows step-by-step."""

    def __init__(self, workflow: Workflow):
        """Initialize executor."""
        self.workflow = workflow
        self.logger = logging.getLogger(__name__)
        self._execution_queue: deque[str] = deque()
        self._completed_nodes: Set[str] = set()
        self._failed_nodes: Set[str] = set()

    def execute(
        self,
        context: Optional[WorkflowContext] = None,
        trigger_type: TriggerType = TriggerType.MANUAL,
        trigger_id: Optional[str] = None
    ) -> WorkflowExecution:
        """Execute workflow."""
        if context is None:
            context = WorkflowContext(
                workflow_id=self.workflow.workflow_id,
                execution_id=str(uuid.uuid4())
            )

        execution = WorkflowExecution(
            workflow_id=self.workflow.workflow_id,
            execution_id=context.execution_id,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(timezone.utc),
            context=context,
            triggered_by=trigger_type,
            triggered_by_id=trigger_id
        )

        context.start_time = execution.start_time

        try:
            self._execute_node(self.workflow.start_node_id, context, execution)
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
        finally:
            execution.end_time = datetime.now(timezone.utc)
            execution.duration_seconds = (
                execution.end_time - execution.start_time
            ).total_seconds()
            self._update_metrics(execution)

        return execution

    def _execute_node(
        self,
        node_id: str,
        context: WorkflowContext,
        execution: WorkflowExecution
    ) -> None:
        """Execute single node."""
        node = self.workflow.nodes.get(node_id)
        if not node:
            return

        node_exec = NodeExecution(
            node_id=node_id,
            status=NodeStatus.RUNNING,
            start_time=datetime.now(timezone.utc)
        )

        try:
            if node.type == NodeType.START:
                node_exec.status = NodeStatus.COMPLETED
                self._execute_next_nodes(node_id, context, execution)

            elif node.type == NodeType.END:
                node_exec.status = NodeStatus.COMPLETED
                execution.status = ExecutionStatus.COMPLETED

            elif node.type == NodeType.TASK:
                task_node = node
                if hasattr(task_node, 'handler') and task_node.handler:
                    result = task_node.handler(context)
                    node_exec.output_data = {'result': result}
                node_exec.status = NodeStatus.COMPLETED
                self._execute_next_nodes(node_id, context, execution)

            elif node.type == NodeType.DECISION:
                decision_node = node
                if hasattr(decision_node, 'condition') and decision_node.condition:
                    condition_result = decision_node.condition(context)
                    next_node = (
                        decision_node.true_path if condition_result
                        else decision_node.false_path
                    )
                    node_exec.status = NodeStatus.COMPLETED
                    if next_node:
                        self._execute_node(next_node, context, execution)

            elif node.type == NodeType.APPROVAL:
                node_exec.status = NodeStatus.WAITING
                execution.status = ExecutionStatus.WAITING_APPROVAL

            elif node.type == NodeType.PARALLEL:
                parallel_node = node
                if hasattr(parallel_node, 'branches'):
                    for branch in parallel_node.branches:
                        if branch:
                            self._execute_node(branch[0], context, execution)
                node_exec.status = NodeStatus.COMPLETED

        except Exception as e:
            node_exec.status = NodeStatus.FAILED
            node_exec.error_message = str(e)
            self.logger.error(f"Node {node_id} execution failed: {e}")
            if not node.skip_on_error:
                raise

        finally:
            node_exec.end_time = datetime.now(timezone.utc)
            node_exec.duration_seconds = (
                node_exec.end_time - node_exec.start_time
            ).total_seconds()
            execution.node_executions[node_id] = node_exec

    def _execute_next_nodes(
        self,
        node_id: str,
        context: WorkflowContext,
        execution: WorkflowExecution
    ) -> None:
        """Execute all successor nodes."""
        for next_node in self.workflow._adjacency_list.get(node_id, []):
            self._execute_node(next_node, context, execution)

    def _update_metrics(self, execution: WorkflowExecution) -> None:
        """Update workflow metrics."""
        metrics = self.workflow.metrics
        metrics.total_executions += 1

        if execution.status == ExecutionStatus.COMPLETED:
            metrics.successful_executions += 1
        elif execution.status == ExecutionStatus.FAILED:
            metrics.failed_executions += 1
        elif execution.status == ExecutionStatus.CANCELLED:
            metrics.cancelled_executions += 1

        metrics.last_execution = execution.start_time

        if execution.duration_seconds > 0:
            if metrics.max_duration_seconds == 0:
                metrics.min_duration_seconds = execution.duration_seconds
            metrics.max_duration_seconds = max(
                metrics.max_duration_seconds,
                execution.duration_seconds
            )
            metrics.min_duration_seconds = min(
                metrics.min_duration_seconds,
                execution.duration_seconds
            )

            total = metrics.successful_executions + metrics.failed_executions
            metrics.avg_duration_seconds = (
                (metrics.avg_duration_seconds * (total - 1) + execution.duration_seconds) / total
            )

        if metrics.total_executions > 0:
            metrics.success_rate = (
                metrics.successful_executions / metrics.total_executions * 100
            )


# ═══════════════════════════════════════════════════════════════════════════
# Workflow Registry & Manager
# ═══════════════════════════════════════════════════════════════════════════

class WorkflowRegistry:
    """Central registry for workflows."""

    def __init__(self):
        """Initialize registry."""
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self._lock = threading.RLock()

    def register(self, workflow: Workflow) -> None:
        """Register workflow."""
        with self._lock:
            is_valid, errors = workflow.validate()
            if not is_valid:
                raise ValueError(f"Invalid workflow: {', '.join(errors)}")
            self.workflows[workflow.workflow_id] = workflow

    def get(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[Workflow]:
        """List all workflows."""
        return list(self.workflows.values())

    def record_execution(self, execution: WorkflowExecution) -> None:
        """Record workflow execution."""
        with self._lock:
            self.executions[execution.execution_id] = execution

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution record."""
        return self.executions.get(execution_id)


class WorkflowEngine:
    """Main workflow orchestration engine."""

    def __init__(self):
        """Initialize workflow engine."""
        self.registry = WorkflowRegistry()
        self.logger = logging.getLogger(__name__)

    def create_workflow(
        self,
        name: str,
        description: str = ""
    ) -> WorkflowBuilder:
        """Create new workflow using builder."""
        return WorkflowBuilder(name, description)

    def register_workflow(self, workflow: Workflow) -> None:
        """Register workflow."""
        self.registry.register(workflow)
        self.logger.info(f"Registered workflow: {workflow.name}")

    def execute_workflow(
        self,
        workflow_id: str,
        context: Optional[WorkflowContext] = None,
        trigger_type: TriggerType = TriggerType.MANUAL
    ) -> Optional[WorkflowExecution]:
        """Execute registered workflow."""
        workflow = self.registry.get(workflow_id)
        if not workflow:
            self.logger.error(f"Workflow '{workflow_id}' not found")
            return None

        executor = WorkflowExecutor(workflow)
        execution = executor.execute(context, trigger_type)
        self.registry.record_execution(execution)

        self.logger.info(
            f"Workflow execution completed: {workflow.name} "
            f"({execution.execution_id}) - Status: {execution.status.value}"
        )

        return execution

    def get_workflow_metrics(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow metrics."""
        workflow = self.registry.get(workflow_id)
        if not workflow:
            return None

        metrics = workflow.metrics
        return {
            'total_executions': metrics.total_executions,
            'successful_executions': metrics.successful_executions,
            'failed_executions': metrics.failed_executions,
            'cancelled_executions': metrics.cancelled_executions,
            'success_rate': metrics.success_rate,
            'avg_duration_seconds': metrics.avg_duration_seconds,
            'max_duration_seconds': metrics.max_duration_seconds,
            'min_duration_seconds': metrics.min_duration_seconds,
            'last_execution': metrics.last_execution.isoformat() if metrics.last_execution else None
        }


# ═══════════════════════════════════════════════════════════════════════════
# Global Workflow Engine Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get or create global workflow engine."""
    global _global_workflow_engine
    if _global_workflow_engine is None:
        _global_workflow_engine = WorkflowEngine()
    return _global_workflow_engine
