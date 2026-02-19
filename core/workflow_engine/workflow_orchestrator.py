"""
BAEL Workflow Orchestrator
==========================

Advanced workflow automation with self-healing and evolution.

"Workflows that heal, learn, and evolve." — Ba'el
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import hashlib
import random

logger = logging.getLogger("BAEL.Workflow")


# =============================================================================
# ENUMS
# =============================================================================

class NodeType(Enum):
    """Types of workflow nodes."""
    START = "start"
    END = "end"
    TASK = "task"
    DECISION = "decision"
    PARALLEL = "parallel"
    JOIN = "join"
    LOOP = "loop"
    SUBWORKFLOW = "subworkflow"
    HUMAN_INPUT = "human_input"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    MEMORY_ACCESS = "memory_access"
    REASONING = "reasoning"
    API_CALL = "api_call"
    FILE_OPERATION = "file_operation"
    DATA_TRANSFORM = "data_transform"
    NOTIFICATION = "notification"
    WAIT = "wait"
    WEBHOOK = "webhook"


class NodeStatus(Enum):
    """Status of a node execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowStatus(Enum):
    """Status of workflow execution."""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(Enum):
    """Workflow trigger types."""
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    EVENT = "event"
    FILE_CHANGE = "file_change"
    API = "api"
    CONDITION = "condition"


class RetryStrategy(Enum):
    """Retry strategies for failed nodes."""
    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR_BACKOFF = "linear"
    EXPONENTIAL_BACKOFF = "exponential"
    CUSTOM = "custom"


class ExecutionMode(Enum):
    """Execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    STREAMING = "streaming"
    BATCH = "batch"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class NodeConfig:
    """Configuration for a workflow node."""
    timeout_seconds: float = 60.0
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retry_delay_seconds: float = 1.0
    cache_result: bool = False
    cache_ttl_seconds: int = 3600
    parallel_execution: bool = False
    condition: Optional[str] = None
    error_handler: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowNode:
    """A node in the workflow graph."""
    id: str
    name: str
    node_type: NodeType
    handler: Optional[str] = None  # Function/tool name
    config: NodeConfig = field(default_factory=NodeConfig)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    # For decisions
    condition: Optional[str] = None
    branches: Dict[str, str] = field(default_factory=dict)  # condition -> next_node_id
    # For loops
    loop_var: Optional[str] = None
    loop_collection: Optional[str] = None
    max_iterations: int = 100
    # Execution state
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt_count: int = 0


@dataclass
class WorkflowEdge:
    """An edge connecting two nodes."""
    source_id: str
    target_id: str
    condition: Optional[str] = None
    label: Optional[str] = None
    data_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_start_nodes(self) -> List[WorkflowNode]:
        """Get starting nodes (no incoming edges)."""
        target_ids = {e.target_id for e in self.edges}
        return [n for n in self.nodes if n.id not in target_ids or n.node_type == NodeType.START]

    def get_end_nodes(self) -> List[WorkflowNode]:
        """Get end nodes (no outgoing edges)."""
        source_ids = {e.source_id for e in self.edges}
        return [n for n in self.nodes if n.id not in source_ids or n.node_type == NodeType.END]

    def get_successors(self, node_id: str) -> List[str]:
        """Get successor node IDs."""
        return [e.target_id for e in self.edges if e.source_id == node_id]

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get predecessor node IDs."""
        return [e.source_id for e in self.edges if e.target_id == node_id]

    def topological_sort(self) -> List[str]:
        """Topological sort of nodes."""
        in_degree = {n.id: 0 for n in self.nodes}
        for edge in self.edges:
            in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

        queue = [nid for nid, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for succ in self.get_successors(node_id):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        return result


@dataclass
class ExecutionContext:
    """Context for workflow execution."""
    workflow_id: str
    execution_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    current_node: Optional[str] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeResult:
    """Result of a node execution."""
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    attempts: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# NODE HANDLERS
# =============================================================================

class NodeHandlerRegistry:
    """Registry for node handlers."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._register_builtin_handlers()

    def _register_builtin_handlers(self):
        """Register built-in handlers."""
        self.register("log", self._handle_log)
        self.register("transform", self._handle_transform)
        self.register("filter", self._handle_filter)
        self.register("map", self._handle_map)
        self.register("reduce", self._handle_reduce)
        self.register("http_request", self._handle_http_request)
        self.register("file_read", self._handle_file_read)
        self.register("file_write", self._handle_file_write)
        self.register("json_parse", self._handle_json_parse)
        self.register("json_stringify", self._handle_json_stringify)
        self.register("wait", self._handle_wait)
        self.register("condition", self._handle_condition)
        self.register("aggregate", self._handle_aggregate)
        self.register("split", self._handle_split)
        self.register("merge", self._handle_merge)

    def register(self, name: str, handler: Callable):
        """Register a handler."""
        self._handlers[name] = handler

    def get(self, name: str) -> Optional[Callable]:
        """Get a handler by name."""
        return self._handlers.get(name)

    async def execute(
        self,
        handler_name: str,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Any:
        """Execute a handler."""
        handler = self.get(handler_name)
        if not handler:
            raise ValueError(f"Unknown handler: {handler_name}")

        if asyncio.iscoroutinefunction(handler):
            return await handler(inputs, context)
        return handler(inputs, context)

    # Built-in handlers
    async def _handle_log(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Log handler."""
        message = inputs.get("message", "")
        level = inputs.get("level", "info")
        getattr(logger, level, logger.info)(f"[Workflow {context.workflow_id}] {message}")
        return {"logged": True, "message": message}

    async def _handle_transform(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Transform data handler."""
        data = inputs.get("data")
        expression = inputs.get("expression", "data")

        # Safe eval with limited context
        result = eval(expression, {"__builtins__": {}}, {"data": data, "context": context.variables})
        return result

    async def _handle_filter(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Filter handler."""
        items = inputs.get("items", [])
        condition = inputs.get("condition", "True")

        result = []
        for item in items:
            if eval(condition, {"__builtins__": {}}, {"item": item}):
                result.append(item)
        return result

    async def _handle_map(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Map handler."""
        items = inputs.get("items", [])
        expression = inputs.get("expression", "item")

        return [eval(expression, {"__builtins__": {}}, {"item": item}) for item in items]

    async def _handle_reduce(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Reduce handler."""
        items = inputs.get("items", [])
        expression = inputs.get("expression", "acc + item")
        initial = inputs.get("initial", 0)

        result = initial
        for item in items:
            result = eval(expression, {"__builtins__": {}}, {"acc": result, "item": item})
        return result

    async def _handle_http_request(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """HTTP request handler."""
        # Simplified implementation
        url = inputs.get("url")
        method = inputs.get("method", "GET")
        headers = inputs.get("headers", {})
        body = inputs.get("body")

        return {
            "status": "simulated",
            "url": url,
            "method": method,
            "message": "HTTP requests require httpx/aiohttp"
        }

    async def _handle_file_read(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """File read handler."""
        path = Path(inputs.get("path", ""))
        encoding = inputs.get("encoding", "utf-8")

        if path.exists():
            return path.read_text(encoding=encoding)
        return None

    async def _handle_file_write(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """File write handler."""
        path = Path(inputs.get("path", ""))
        content = inputs.get("content", "")
        encoding = inputs.get("encoding", "utf-8")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return {"written": True, "path": str(path)}

    async def _handle_json_parse(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """JSON parse handler."""
        text = inputs.get("text", "{}")
        return json.loads(text)

    async def _handle_json_stringify(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """JSON stringify handler."""
        data = inputs.get("data")
        indent = inputs.get("indent")
        return json.dumps(data, indent=indent)

    async def _handle_wait(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Wait handler."""
        seconds = inputs.get("seconds", 1)
        await asyncio.sleep(seconds)
        return {"waited": seconds}

    async def _handle_condition(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Condition evaluation handler."""
        condition = inputs.get("condition", "True")
        data = inputs.get("data", {})

        result = eval(condition, {"__builtins__": {}}, data)
        return {"result": bool(result)}

    async def _handle_aggregate(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Aggregate handler."""
        items = inputs.get("items", [])
        operation = inputs.get("operation", "sum")

        if operation == "sum":
            return sum(items)
        elif operation == "avg":
            return sum(items) / len(items) if items else 0
        elif operation == "min":
            return min(items) if items else None
        elif operation == "max":
            return max(items) if items else None
        elif operation == "count":
            return len(items)
        return items

    async def _handle_split(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Split handler."""
        data = inputs.get("data", "")
        separator = inputs.get("separator", ",")

        if isinstance(data, str):
            return data.split(separator)
        return list(data)

    async def _handle_merge(self, inputs: Dict[str, Any], context: ExecutionContext) -> Any:
        """Merge handler."""
        items = inputs.get("items", [])
        strategy = inputs.get("strategy", "concat")

        if strategy == "concat":
            result = []
            for item in items:
                if isinstance(item, list):
                    result.extend(item)
                else:
                    result.append(item)
            return result
        elif strategy == "dict":
            result = {}
            for item in items:
                if isinstance(item, dict):
                    result.update(item)
            return result
        return items


# =============================================================================
# WORKFLOW REGISTRY
# =============================================================================

class WorkflowRegistry:
    """Registry for workflow definitions."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/workflows")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._workflows: Dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> str:
        """Register a workflow."""
        self._workflows[workflow.id] = workflow
        self._persist(workflow)
        return workflow.id

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow by ID."""
        if workflow_id in self._workflows:
            return self._workflows[workflow_id]
        return self._load(workflow_id)

    def list_all(self) -> List[WorkflowDefinition]:
        """List all workflows."""
        return list(self._workflows.values())

    def delete(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]

        path = self.storage_path / f"{workflow_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def _persist(self, workflow: WorkflowDefinition):
        """Persist workflow to disk."""
        path = self.storage_path / f"{workflow.id}.json"
        data = {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "version": workflow.version,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "node_type": n.node_type.value,
                    "handler": n.handler,
                    "inputs": n.inputs,
                    "condition": n.condition,
                    "branches": n.branches
                }
                for n in workflow.nodes
            ],
            "edges": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "condition": e.condition,
                    "data_mapping": e.data_mapping
                }
                for e in workflow.edges
            ],
            "variables": workflow.variables,
            "execution_mode": workflow.execution_mode.value,
            "metadata": workflow.metadata
        }
        path.write_text(json.dumps(data, indent=2))

    def _load(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Load workflow from disk."""
        path = self.storage_path / f"{workflow_id}.json"
        if not path.exists():
            return None

        data = json.loads(path.read_text())
        workflow = WorkflowDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            nodes=[
                WorkflowNode(
                    id=n["id"],
                    name=n["name"],
                    node_type=NodeType(n["node_type"]),
                    handler=n.get("handler"),
                    inputs=n.get("inputs", {}),
                    condition=n.get("condition"),
                    branches=n.get("branches", {})
                )
                for n in data.get("nodes", [])
            ],
            edges=[
                WorkflowEdge(
                    source_id=e["source_id"],
                    target_id=e["target_id"],
                    condition=e.get("condition"),
                    data_mapping=e.get("data_mapping", {})
                )
                for e in data.get("edges", [])
            ],
            variables=data.get("variables", {}),
            execution_mode=ExecutionMode(data.get("execution_mode", "sequential")),
            metadata=data.get("metadata", {})
        )

        self._workflows[workflow.id] = workflow
        return workflow


# =============================================================================
# WORKFLOW EXECUTOR
# =============================================================================

class WorkflowExecutor:
    """Executes workflow definitions."""

    def __init__(self, handler_registry: Optional[NodeHandlerRegistry] = None):
        self.handler_registry = handler_registry or NodeHandlerRegistry()
        self._executions: Dict[str, ExecutionContext] = {}
        self._results: Dict[str, WorkflowResult] = {}

    async def execute(
        self,
        workflow: WorkflowDefinition,
        inputs: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> WorkflowResult:
        """Execute a workflow."""
        execution_id = execution_id or str(uuid.uuid4())

        context = ExecutionContext(
            workflow_id=workflow.id,
            execution_id=execution_id,
            variables={**workflow.variables, **(inputs or {})}
        )

        self._executions[execution_id] = context

        start_time = datetime.now()

        try:
            # Execute in topological order
            execution_order = workflow.topological_sort()

            for node_id in execution_order:
                node = workflow.get_node(node_id)
                if not node:
                    continue

                context.current_node = node_id

                # Check condition
                if node.condition:
                    if not self._evaluate_condition(node.condition, context):
                        node.status = NodeStatus.SKIPPED
                        continue

                # Execute node
                result = await self._execute_node(node, context)
                context.node_results[node_id] = result.output

                if result.status == NodeStatus.FAILED:
                    raise Exception(result.error)

            status = WorkflowStatus.COMPLETED
            errors = []

        except Exception as e:
            status = WorkflowStatus.FAILED
            errors = [str(e)]
            context.errors.append({
                "node": context.current_node,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        result = WorkflowResult(
            workflow_id=workflow.id,
            execution_id=execution_id,
            status=status,
            outputs=context.node_results,
            duration_ms=duration_ms,
            errors=errors,
            metadata=context.metadata
        )

        self._results[execution_id] = result
        return result

    async def _execute_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> NodeResult:
        """Execute a single node."""
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.now()

        try:
            # Handle special node types
            if node.node_type == NodeType.START:
                output = context.variables
            elif node.node_type == NodeType.END:
                output = context.node_results
            elif node.node_type == NodeType.DECISION:
                output = await self._handle_decision(node, context)
            elif node.node_type == NodeType.LOOP:
                output = await self._handle_loop(node, context)
            elif node.node_type == NodeType.PARALLEL:
                output = await self._handle_parallel(node, context)
            elif node.node_type == NodeType.WAIT:
                seconds = node.inputs.get("seconds", 1)
                await asyncio.sleep(seconds)
                output = {"waited": seconds}
            elif node.handler:
                # Resolve inputs
                resolved_inputs = self._resolve_inputs(node.inputs, context)
                output = await self.handler_registry.execute(
                    node.handler,
                    resolved_inputs,
                    context
                )
            else:
                output = node.inputs

            node.status = NodeStatus.COMPLETED
            node.result = output
            node.completed_at = datetime.now()

            return NodeResult(
                node_id=node.id,
                status=NodeStatus.COMPLETED,
                output=output,
                duration_ms=(node.completed_at - node.started_at).total_seconds() * 1000,
                attempts=node.attempt_count + 1
            )

        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = str(e)
            node.completed_at = datetime.now()

            # Retry logic
            if node.attempt_count < node.config.max_retries:
                node.attempt_count += 1
                node.status = NodeStatus.RETRYING

                delay = self._calculate_retry_delay(node)
                await asyncio.sleep(delay)

                return await self._execute_node(node, context)

            return NodeResult(
                node_id=node.id,
                status=NodeStatus.FAILED,
                error=str(e),
                duration_ms=(node.completed_at - node.started_at).total_seconds() * 1000,
                attempts=node.attempt_count + 1
            )

    async def _handle_decision(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Handle decision node."""
        for condition, branch_id in node.branches.items():
            if self._evaluate_condition(condition, context):
                return {"branch": branch_id, "condition": condition}

        # Default branch
        if "default" in node.branches:
            return {"branch": node.branches["default"], "condition": "default"}

        return {"branch": None, "condition": None}

    async def _handle_loop(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> List[Any]:
        """Handle loop node."""
        collection = self._resolve_value(node.loop_collection, context)

        if not isinstance(collection, (list, tuple)):
            collection = list(collection)

        results = []
        for i, item in enumerate(collection):
            if i >= node.max_iterations:
                break

            context.variables[node.loop_var or "item"] = item
            context.variables["loop_index"] = i

            # Execute loop body (simplified - would need subgraph execution)
            if node.handler:
                result = await self.handler_registry.execute(
                    node.handler,
                    {**node.inputs, "item": item, "index": i},
                    context
                )
                results.append(result)

        return results

    async def _handle_parallel(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> List[Any]:
        """Handle parallel execution."""
        # Get parallel tasks from inputs
        tasks = node.inputs.get("tasks", [])

        async def run_task(task):
            if isinstance(task, dict) and "handler" in task:
                return await self.handler_registry.execute(
                    task["handler"],
                    task.get("inputs", {}),
                    context
                )
            return task

        results = await asyncio.gather(*[run_task(t) for t in tasks])
        return list(results)

    def _resolve_inputs(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Resolve input references."""
        resolved = {}
        for key, value in inputs.items():
            resolved[key] = self._resolve_value(value, context)
        return resolved

    def _resolve_value(self, value: Any, context: ExecutionContext) -> Any:
        """Resolve a single value."""
        if isinstance(value, str) and value.startswith("$"):
            # Variable reference
            path = value[1:].split(".")
            result = context.variables

            for part in path:
                if isinstance(result, dict):
                    result = result.get(part)
                elif hasattr(result, part):
                    result = getattr(result, part)
                else:
                    return None

            return result

        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            # Node result reference
            expr = value[2:-2].strip()
            return context.node_results.get(expr)

        return value

    def _evaluate_condition(self, condition: str, context: ExecutionContext) -> bool:
        """Evaluate a condition expression."""
        try:
            return bool(eval(
                condition,
                {"__builtins__": {}},
                {**context.variables, **context.node_results}
            ))
        except Exception:
            return False

    def _calculate_retry_delay(self, node: WorkflowNode) -> float:
        """Calculate retry delay based on strategy."""
        base_delay = node.config.retry_delay_seconds
        attempt = node.attempt_count

        if node.config.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif node.config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            return base_delay * attempt
        elif node.config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return base_delay * (2 ** (attempt - 1))
        else:
            return base_delay


# =============================================================================
# WORKFLOW SCHEDULER
# =============================================================================

class WorkflowScheduler:
    """Schedules workflow executions."""

    def __init__(self, executor: WorkflowExecutor, registry: WorkflowRegistry):
        self.executor = executor
        self.registry = registry
        self._schedules: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def schedule(
        self,
        workflow_id: str,
        trigger_type: TriggerType,
        config: Dict[str, Any]
    ) -> str:
        """Schedule a workflow."""
        schedule_id = str(uuid.uuid4())[:8]

        self._schedules[schedule_id] = {
            "workflow_id": workflow_id,
            "trigger_type": trigger_type,
            "config": config,
            "last_run": None,
            "next_run": self._calculate_next_run(trigger_type, config),
            "active": True
        }

        return schedule_id

    def unschedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            return True
        return False

    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = datetime.now()

            for schedule_id, schedule in list(self._schedules.items()):
                if not schedule["active"]:
                    continue

                next_run = schedule.get("next_run")
                if next_run and now >= next_run:
                    # Execute workflow
                    workflow = self.registry.get(schedule["workflow_id"])
                    if workflow:
                        asyncio.create_task(
                            self.executor.execute(workflow)
                        )

                    # Update schedule
                    schedule["last_run"] = now
                    schedule["next_run"] = self._calculate_next_run(
                        schedule["trigger_type"],
                        schedule["config"]
                    )

            await asyncio.sleep(1)  # Check every second

    def _calculate_next_run(
        self,
        trigger_type: TriggerType,
        config: Dict[str, Any]
    ) -> Optional[datetime]:
        """Calculate next run time."""
        now = datetime.now()

        if trigger_type == TriggerType.SCHEDULE:
            interval = config.get("interval_seconds", 3600)
            return now + timedelta(seconds=interval)

        # For manual and event-based, no automatic scheduling
        return None


# =============================================================================
# WORKFLOW MONITOR
# =============================================================================

class WorkflowMonitor:
    """Monitors workflow executions."""

    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._alerts: List[Dict[str, Any]] = []

    def record_execution(self, result: WorkflowResult):
        """Record execution metrics."""
        workflow_id = result.workflow_id

        if workflow_id not in self._metrics:
            self._metrics[workflow_id] = {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "total_duration_ms": 0,
                "avg_duration_ms": 0
            }

        metrics = self._metrics[workflow_id]
        metrics["total_executions"] += 1
        metrics["total_duration_ms"] += result.duration_ms
        metrics["avg_duration_ms"] = (
            metrics["total_duration_ms"] / metrics["total_executions"]
        )

        if result.status == WorkflowStatus.COMPLETED:
            metrics["successful"] += 1
        else:
            metrics["failed"] += 1
            self._create_alert(result)

    def _create_alert(self, result: WorkflowResult):
        """Create alert for failed execution."""
        self._alerts.append({
            "workflow_id": result.workflow_id,
            "execution_id": result.execution_id,
            "type": "execution_failed",
            "errors": result.errors,
            "timestamp": datetime.now().isoformat()
        })

    def get_metrics(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a workflow."""
        return self._metrics.get(workflow_id)

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self._alerts[-limit:]


# =============================================================================
# WORKFLOW ORCHESTRATOR
# =============================================================================

class WorkflowOrchestrator:
    """Main workflow orchestration engine."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.registry = WorkflowRegistry(storage_path)
        self.handler_registry = NodeHandlerRegistry()
        self.executor = WorkflowExecutor(self.handler_registry)
        self.scheduler = WorkflowScheduler(self.executor, self.registry)
        self.monitor = WorkflowMonitor()

    async def initialize(self):
        """Initialize the orchestrator."""
        await self.scheduler.start()

    async def shutdown(self):
        """Shutdown the orchestrator."""
        await self.scheduler.stop()

    def create_workflow(
        self,
        name: str,
        description: str = "",
        nodes: Optional[List[Dict[str, Any]]] = None,
        edges: Optional[List[Tuple[str, str]]] = None
    ) -> WorkflowDefinition:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())[:8]

        workflow_nodes = []
        if nodes:
            for n in nodes:
                workflow_nodes.append(WorkflowNode(
                    id=n.get("id", str(uuid.uuid4())[:6]),
                    name=n.get("name", "Unnamed"),
                    node_type=NodeType(n.get("type", "task")),
                    handler=n.get("handler"),
                    inputs=n.get("inputs", {}),
                    condition=n.get("condition"),
                    branches=n.get("branches", {})
                ))

        workflow_edges = []
        if edges:
            for source, target in edges:
                workflow_edges.append(WorkflowEdge(
                    source_id=source,
                    target_id=target
                ))

        workflow = WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=description,
            nodes=workflow_nodes,
            edges=workflow_edges
        )

        self.registry.register(workflow)
        return workflow

    async def execute(
        self,
        workflow_id: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """Execute a workflow."""
        workflow = self.registry.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        result = await self.executor.execute(workflow, inputs)
        self.monitor.record_execution(result)
        return result

    async def execute_definition(
        self,
        workflow: WorkflowDefinition,
        inputs: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """Execute a workflow definition directly."""
        result = await self.executor.execute(workflow, inputs)
        self.monitor.record_execution(result)
        return result

    def schedule(
        self,
        workflow_id: str,
        trigger_type: TriggerType,
        config: Dict[str, Any]
    ) -> str:
        """Schedule a workflow."""
        return self.scheduler.schedule(workflow_id, trigger_type, config)

    def register_handler(self, name: str, handler: Callable):
        """Register a custom node handler."""
        self.handler_registry.register(name, handler)

    def get_metrics(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow metrics."""
        return self.monitor.get_metrics(workflow_id)

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self.monitor.get_alerts(limit)

    async def create_from_description(self, description: str) -> WorkflowDefinition:
        """Create workflow from natural language description."""
        # Parse description to extract workflow structure
        # This is a simplified implementation

        # Keywords for node types
        node_keywords = {
            "start": ["start", "begin", "initiate"],
            "end": ["end", "finish", "complete"],
            "api": ["api", "request", "fetch", "http"],
            "transform": ["transform", "convert", "process"],
            "condition": ["if", "when", "condition", "check"],
            "loop": ["loop", "iterate", "for each", "repeat"],
            "notify": ["notify", "send", "email", "message", "alert"],
            "wait": ["wait", "delay", "pause", "sleep"]
        }

        words = description.lower().split()
        detected_nodes = []

        for node_type, keywords in node_keywords.items():
            for keyword in keywords:
                if keyword in description.lower():
                    detected_nodes.append(node_type)
                    break

        # Create workflow from detected nodes
        nodes = [{"id": "start", "name": "Start", "type": "start"}]

        for i, node_type in enumerate(detected_nodes):
            nodes.append({
                "id": f"node_{i}",
                "name": f"{node_type.title()} Step",
                "type": node_type,
                "handler": node_type if node_type in ["transform", "log", "wait"] else None
            })

        nodes.append({"id": "end", "name": "End", "type": "end"})

        # Create edges
        edges = []
        for i in range(len(nodes) - 1):
            edges.append((nodes[i]["id"], nodes[i + 1]["id"]))

        return self.create_workflow(
            name=f"Workflow from description",
            description=description,
            nodes=nodes,
            edges=edges
        )


# =============================================================================
# CONVENIENCE INSTANCE
# =============================================================================

workflow_engine = WorkflowOrchestrator()
