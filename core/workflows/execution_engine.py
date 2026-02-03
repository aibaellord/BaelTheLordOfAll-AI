#!/usr/bin/env python3
"""
BAEL - Workflow Execution Engine
Executes visual workflows defined in the UI workflow builder.

Supports:
- Sequential and parallel node execution
- Conditional branching
- Loops with configurable iterations
- Error handling and retries
- Variable passing between nodes
- Real-time progress updates
"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.Workflows.Engine")


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class NodeType(Enum):
    """Workflow node types."""
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    MERGE = "merge"
    DELAY = "delay"
    SUBWORKFLOW = "subworkflow"
    TRANSFORM = "transform"
    OUTPUT = "output"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    HTTP_REQUEST = "http_request"
    CODE = "code"


class NodeStatus(Enum):
    """Node execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(Enum):
    """Workflow execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class NodeConnection:
    """Connection between nodes."""
    source_id: str
    source_port: str = "output"
    target_id: str = ""
    target_port: str = "input"
    condition: Optional[str] = None  # For conditional branching


@dataclass
class WorkflowNode:
    """A node in the workflow."""
    id: str = ""
    type: NodeType = NodeType.ACTION
    name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    connections: List[NodeConnection] = field(default_factory=list)

    # Runtime state
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"node-{uuid.uuid4().hex[:8]}"


@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str = ""
    name: str = "Untitled Workflow"
    description: str = ""
    nodes: List[WorkflowNode] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)  # Global workflow variables
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    tags: List[str] = field(default_factory=list)
    enabled: bool = True

    def __post_init__(self):
        if not self.id:
            self.id = f"workflow-{uuid.uuid4().hex[:12]}"

    @property
    def trigger_nodes(self) -> List[WorkflowNode]:
        """Get all trigger nodes."""
        return [n for n in self.nodes if n.type == NodeType.TRIGGER]

    @property
    def node_map(self) -> Dict[str, WorkflowNode]:
        """Get nodes indexed by ID."""
        return {n.id: n for n in self.nodes}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "name": n.name,
                    "config": n.config,
                    "position": n.position,
                    "connections": [
                        {
                            "source_id": c.source_id,
                            "source_port": c.source_port,
                            "target_id": c.target_id,
                            "target_port": c.target_port,
                            "condition": c.condition
                        }
                        for c in n.connections
                    ]
                }
                for n in self.nodes
            ],
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "tags": self.tags,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        """Create from dictionary."""
        nodes = []
        for nd in data.get("nodes", []):
            connections = [
                NodeConnection(**c) for c in nd.get("connections", [])
            ]
            nodes.append(WorkflowNode(
                id=nd.get("id", ""),
                type=NodeType(nd.get("type", "action")),
                name=nd.get("name", ""),
                config=nd.get("config", {}),
                position=nd.get("position", {"x": 0, "y": 0}),
                connections=connections
            ))

        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            nodes=nodes,
            variables=data.get("variables", {}),
            version=data.get("version", 1),
            tags=data.get("tags", []),
            enabled=data.get("enabled", True)
        )


@dataclass
class ExecutionContext:
    """Context for workflow execution."""
    workflow_id: str
    execution_id: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    node_outputs: Dict[str, Any] = field(default_factory=dict)  # node_id -> output
    current_node_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: WorkflowStatus = WorkflowStatus.IDLE
    error: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = f"exec-{uuid.uuid4().hex[:8]}"

    def log(self, message: str, level: str = "info", node_id: Optional[str] = None):
        """Add a log entry."""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "node_id": node_id
        })

    def set_node_output(self, node_id: str, output: Any):
        """Set output from a node."""
        self.node_outputs[node_id] = output

    def get_node_output(self, node_id: str) -> Any:
        """Get output from a node."""
        return self.node_outputs.get(node_id)

    def resolve_variable(self, value: Any) -> Any:
        """Resolve variable references in a value."""
        if isinstance(value, str):
            # Handle {{variable}} syntax
            if value.startswith("{{") and value.endswith("}}"):
                var_name = value[2:-2].strip()

                # Check node outputs (format: node.output)
                if "." in var_name:
                    parts = var_name.split(".", 1)
                    node_output = self.node_outputs.get(parts[0])
                    if node_output and isinstance(node_output, dict):
                        return node_output.get(parts[1])
                    return node_output

                # Check variables
                return self.variables.get(var_name, value)

            # Handle inline references
            import re
            pattern = r'\{\{([^}]+)\}\}'
            matches = re.findall(pattern, value)
            result = value
            for match in matches:
                resolved = self.resolve_variable(f"{{{{{match}}}}}")
                result = result.replace(f"{{{{{match}}}}}", str(resolved or ""))
            return result

        elif isinstance(value, dict):
            return {k: self.resolve_variable(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve_variable(v) for v in value]

        return value


# =============================================================================
# NODE EXECUTORS
# =============================================================================

class NodeExecutor:
    """Base class for node executors."""

    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Any:
        """Execute a node and return its output."""
        raise NotImplementedError


class ActionExecutor(NodeExecutor):
    """Execute generic action nodes."""

    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Any:
        action = node.config.get("action", "")
        params = context.resolve_variable(node.config.get("params", {}))

        context.log(f"Executing action: {action}", node_id=node.id)

        # Dispatch to appropriate handler
        if action == "log":
            message = params.get("message", "")
            logger.info(f"[Workflow Log] {message}")
            return {"logged": message}

        elif action == "set_variable":
            var_name = params.get("name", "")
            var_value = params.get("value")
            context.variables[var_name] = var_value
            return {"variable": var_name, "value": var_value}

        elif action == "http_request":
            return await self._http_request(params)

        elif action == "wait":
            delay = params.get("seconds", 1)
            await asyncio.sleep(delay)
            return {"waited": delay}

        else:
            return {"action": action, "params": params, "status": "executed"}

    async def _http_request(self, params: Dict) -> Dict:
        """Execute HTTP request."""
        try:
            import aiohttp

            method = params.get("method", "GET").upper()
            url = params.get("url", "")
            headers = params.get("headers", {})
            body = params.get("body")

            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=body) as resp:
                    return {
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "body": await resp.text()
                    }
        except Exception as e:
            return {"error": str(e)}


class LLMCallExecutor(NodeExecutor):
    """Execute LLM call nodes."""

    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Any:
        prompt = context.resolve_variable(node.config.get("prompt", ""))
        system_prompt = context.resolve_variable(node.config.get("system_prompt"))
        model = node.config.get("model")
        temperature = node.config.get("temperature", 0.7)

        context.log(f"Calling LLM: {prompt[:100]}...", node_id=node.id)

        try:
            from core.wiring import LLMExecutor
            executor = LLMExecutor(model=model)
            result = await executor.execute(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature
            )
            return {
                "response": result.get("content", ""),
                "model": result.get("model"),
                "tokens": result.get("tokens_used", 0)
            }
        except Exception as e:
            return {"error": str(e)}


class ToolCallExecutor(NodeExecutor):
    """Execute tool call nodes."""

    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Any:
        tool_name = node.config.get("tool", "")
        params = context.resolve_variable(node.config.get("params", {}))

        context.log(f"Calling tool: {tool_name}", node_id=node.id)

        try:
            # Try to get tool from registry
            from core.tools.registry import get_tool_registry
            registry = get_tool_registry()
            tool = registry.get(tool_name)

            if tool:
                if asyncio.iscoroutinefunction(tool.execute):
                    result = await tool.execute(**params)
                else:
                    result = tool.execute(**params)
                return {"result": result}
            else:
                return {"error": f"Tool not found: {tool_name}"}
        except ImportError:
            return {"error": "Tool registry not available"}
        except Exception as e:
            return {"error": str(e)}


class CodeExecutor(NodeExecutor):
    """Execute code nodes."""

    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Any:
        code = node.config.get("code", "")
        language = node.config.get("language", "python")

        context.log(f"Executing {language} code", node_id=node.id)

        if language == "python":
            try:
                # Prepare execution context
                local_vars = {
                    "context": context,
                    "variables": context.variables,
                    "node_outputs": context.node_outputs,
                    "result": None
                }

                # Safe builtins
                safe_builtins = {
                    'print': print, 'len': len, 'range': range,
                    'str': str, 'int': int, 'float': float, 'bool': bool,
                    'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
                    'sum': sum, 'min': min, 'max': max, 'abs': abs,
                    'sorted': sorted, 'enumerate': enumerate, 'zip': zip,
                    'map': map, 'filter': filter, 'json': json,
                    'True': True, 'False': False, 'None': None,
                }

                exec(code, {"__builtins__": safe_builtins}, local_vars)
                return local_vars.get("result", {"executed": True})

            except Exception as e:
                return {"error": str(e), "traceback": traceback.format_exc()}
        else:
            return {"error": f"Language {language} not supported"}


class ConditionExecutor(NodeExecutor):
    """Execute condition nodes for branching."""

    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Any:
        condition = context.resolve_variable(node.config.get("condition", ""))
        left = context.resolve_variable(node.config.get("left"))
        operator = node.config.get("operator", "==")
        right = context.resolve_variable(node.config.get("right"))

        context.log(f"Evaluating condition: {left} {operator} {right}", node_id=node.id)

        # Evaluate condition
        result = False
        try:
            if operator == "==":
                result = left == right
            elif operator == "!=":
                result = left != right
            elif operator == ">":
                result = float(left) > float(right)
            elif operator == "<":
                result = float(left) < float(right)
            elif operator == ">=":
                result = float(left) >= float(right)
            elif operator == "<=":
                result = float(left) <= float(right)
            elif operator == "contains":
                result = right in str(left)
            elif operator == "startswith":
                result = str(left).startswith(str(right))
            elif operator == "endswith":
                result = str(left).endswith(str(right))
            elif operator == "regex":
                import re
                result = bool(re.search(str(right), str(left)))
            elif operator == "truthy":
                result = bool(left)
        except Exception as e:
            context.log(f"Condition evaluation error: {e}", level="error", node_id=node.id)

        return {"result": result, "branch": "true" if result else "false"}


class LoopExecutor(NodeExecutor):
    """Execute loop nodes."""

    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Any:
        loop_type = node.config.get("loop_type", "count")
        items = context.resolve_variable(node.config.get("items", []))
        count = node.config.get("count", 5)
        max_iterations = node.config.get("max_iterations", 100)

        context.log(f"Starting loop: {loop_type}", node_id=node.id)

        if loop_type == "count":
            return {"iterations": list(range(count)), "type": "count"}
        elif loop_type == "foreach":
            if isinstance(items, (list, tuple)):
                return {"iterations": items[:max_iterations], "type": "foreach"}
            elif isinstance(items, dict):
                return {"iterations": list(items.items())[:max_iterations], "type": "foreach"}
            else:
                return {"iterations": [items], "type": "foreach"}
        else:
            return {"iterations": [], "type": loop_type}


class TransformExecutor(NodeExecutor):
    """Execute data transformation nodes."""

    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Any:
        transform_type = node.config.get("transform", "passthrough")
        input_data = context.resolve_variable(node.config.get("input", ""))

        context.log(f"Transforming data: {transform_type}", node_id=node.id)

        if transform_type == "passthrough":
            return input_data

        elif transform_type == "json_parse":
            try:
                return json.loads(input_data)
            except:
                return {"error": "Invalid JSON"}

        elif transform_type == "json_stringify":
            return json.dumps(input_data)

        elif transform_type == "extract":
            path = node.config.get("path", "")
            data = input_data
            for key in path.split("."):
                if isinstance(data, dict):
                    data = data.get(key)
                elif isinstance(data, (list, tuple)) and key.isdigit():
                    data = data[int(key)]
                else:
                    break
            return data

        elif transform_type == "template":
            template = node.config.get("template", "")
            return context.resolve_variable(template)

        elif transform_type == "map":
            expression = node.config.get("expression", "item")
            if isinstance(input_data, list):
                return [eval(expression, {"item": item, "index": i}) for i, item in enumerate(input_data)]
            return input_data

        elif transform_type == "filter":
            condition = node.config.get("condition", "True")
            if isinstance(input_data, list):
                return [item for item in input_data if eval(condition, {"item": item})]
            return input_data

        else:
            return input_data


# =============================================================================
# WORKFLOW ENGINE
# =============================================================================

class WorkflowEngine:
    """
    Executes workflows with support for parallel execution,
    branching, loops, and error handling.
    """

    def __init__(self):
        self.executors: Dict[NodeType, NodeExecutor] = {
            NodeType.ACTION: ActionExecutor(),
            NodeType.LLM_CALL: LLMCallExecutor(),
            NodeType.TOOL_CALL: ToolCallExecutor(),
            NodeType.CODE: CodeExecutor(),
            NodeType.CONDITION: ConditionExecutor(),
            NodeType.LOOP: LoopExecutor(),
            NodeType.TRANSFORM: TransformExecutor(),
        }

        # Active executions
        self.executions: Dict[str, ExecutionContext] = {}

        # Callbacks
        self.on_node_start: Optional[Callable[[str, WorkflowNode], None]] = None
        self.on_node_complete: Optional[Callable[[str, WorkflowNode, Any], None]] = None
        self.on_node_error: Optional[Callable[[str, WorkflowNode, str], None]] = None
        self.on_workflow_complete: Optional[Callable[[ExecutionContext], None]] = None

    def register_executor(self, node_type: NodeType, executor: NodeExecutor):
        """Register a custom node executor."""
        self.executors[node_type] = executor

    async def execute(
        self,
        workflow: Workflow,
        initial_variables: Optional[Dict[str, Any]] = None,
        trigger_data: Optional[Dict[str, Any]] = None
    ) -> ExecutionContext:
        """Execute a workflow."""
        # Create execution context
        context = ExecutionContext(
            workflow_id=workflow.id,
            variables={**workflow.variables, **(initial_variables or {})}
        )

        self.executions[context.execution_id] = context
        context.status = WorkflowStatus.RUNNING
        context.log(f"Starting workflow: {workflow.name}")

        try:
            # Find entry points (triggers or nodes with no incoming connections)
            entry_nodes = self._find_entry_nodes(workflow)

            if trigger_data:
                context.variables["trigger"] = trigger_data

            # Execute from entry points
            for node in entry_nodes:
                await self._execute_node(workflow, node, context)

            context.status = WorkflowStatus.COMPLETED
            context.completed_at = datetime.now()
            context.log("Workflow completed successfully")

        except Exception as e:
            context.status = WorkflowStatus.FAILED
            context.error = str(e)
            context.log(f"Workflow failed: {e}", level="error")
            logger.error(f"Workflow execution error: {e}\n{traceback.format_exc()}")

        finally:
            if self.on_workflow_complete:
                self.on_workflow_complete(context)

        return context

    def _find_entry_nodes(self, workflow: Workflow) -> List[WorkflowNode]:
        """Find nodes with no incoming connections."""
        # Get all target node IDs
        target_ids = set()
        for node in workflow.nodes:
            for conn in node.connections:
                target_ids.add(conn.target_id)

        # Find nodes not targeted by any connection
        entry_nodes = [n for n in workflow.nodes if n.id not in target_ids]

        # Prioritize trigger nodes
        triggers = [n for n in entry_nodes if n.type == NodeType.TRIGGER]
        if triggers:
            return triggers

        return entry_nodes or (workflow.nodes[:1] if workflow.nodes else [])

    async def _execute_node(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> Any:
        """Execute a single node and its downstream nodes."""
        if node.status == NodeStatus.COMPLETED:
            return context.get_node_output(node.id)

        context.current_node_id = node.id
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.now()

        if self.on_node_start:
            self.on_node_start(context.execution_id, node)

        context.log(f"Executing node: {node.name} ({node.type.value})", node_id=node.id)

        try:
            # Get executor
            executor = self.executors.get(node.type)
            if not executor:
                # Default to action executor
                executor = self.executors[NodeType.ACTION]

            # Execute
            result = await executor.execute(node, context)
            node.result = result
            node.status = NodeStatus.COMPLETED
            node.completed_at = datetime.now()

            # Store output
            context.set_node_output(node.id, result)

            if self.on_node_complete:
                self.on_node_complete(context.execution_id, node, result)

            # Handle special node types
            if node.type == NodeType.CONDITION:
                # Branch based on condition result
                branch = result.get("branch", "true")
                await self._execute_downstream(workflow, node, context, branch)

            elif node.type == NodeType.LOOP:
                # Execute loop iterations
                iterations = result.get("iterations", [])
                loop_results = []
                for i, item in enumerate(iterations):
                    context.variables["loop_index"] = i
                    context.variables["loop_item"] = item
                    await self._execute_downstream(workflow, node, context)
                    loop_results.append(context.variables.get("loop_result"))
                context.set_node_output(node.id, {"results": loop_results, "count": len(iterations)})

            elif node.type == NodeType.PARALLEL:
                # Execute downstream nodes in parallel
                await self._execute_downstream_parallel(workflow, node, context)

            else:
                # Execute downstream sequentially
                await self._execute_downstream(workflow, node, context)

            return result

        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = str(e)
            node.completed_at = datetime.now()

            if self.on_node_error:
                self.on_node_error(context.execution_id, node, str(e))

            context.log(f"Node failed: {e}", level="error", node_id=node.id)
            raise

    async def _execute_downstream(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: ExecutionContext,
        branch: Optional[str] = None
    ):
        """Execute downstream nodes."""
        node_map = workflow.node_map

        for conn in node.connections:
            # Check branch condition
            if branch and conn.condition and conn.condition != branch:
                continue

            target_node = node_map.get(conn.target_id)
            if target_node:
                await self._execute_node(workflow, target_node, context)

    async def _execute_downstream_parallel(
        self,
        workflow: Workflow,
        node: WorkflowNode,
        context: ExecutionContext
    ):
        """Execute downstream nodes in parallel."""
        node_map = workflow.node_map
        tasks = []

        for conn in node.connections:
            target_node = node_map.get(conn.target_id)
            if target_node:
                tasks.append(self._execute_node(workflow, target_node, context))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def pause_execution(self, execution_id: str) -> bool:
        """Pause a running execution."""
        context = self.executions.get(execution_id)
        if context and context.status == WorkflowStatus.RUNNING:
            context.status = WorkflowStatus.PAUSED
            return True
        return False

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        context = self.executions.get(execution_id)
        if context and context.status in (WorkflowStatus.RUNNING, WorkflowStatus.PAUSED):
            context.status = WorkflowStatus.CANCELLED
            return True
        return False

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status."""
        context = self.executions.get(execution_id)
        if not context:
            return None

        return {
            "execution_id": context.execution_id,
            "workflow_id": context.workflow_id,
            "status": context.status.value,
            "current_node": context.current_node_id,
            "variables": context.variables,
            "node_outputs": {k: str(v)[:200] for k, v in context.node_outputs.items()},
            "started_at": context.started_at.isoformat(),
            "completed_at": context.completed_at.isoformat() if context.completed_at else None,
            "error": context.error,
            "log_count": len(context.logs)
        }


# =============================================================================
# WORKFLOW STORAGE
# =============================================================================

class WorkflowStorage:
    """Persist and retrieve workflows."""

    def __init__(self, storage_path: str = "data/workflows"):
        self.storage_path = storage_path
        import os
        os.makedirs(storage_path, exist_ok=True)

    def save(self, workflow: Workflow) -> bool:
        """Save a workflow."""
        try:
            file_path = f"{self.storage_path}/{workflow.id}.json"
            with open(file_path, 'w') as f:
                json.dump(workflow.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save workflow: {e}")
            return False

    def load(self, workflow_id: str) -> Optional[Workflow]:
        """Load a workflow by ID."""
        try:
            file_path = f"{self.storage_path}/{workflow_id}.json"
            with open(file_path, 'r') as f:
                data = json.load(f)
            return Workflow.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load workflow: {e}")
            return None

    def list_all(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        import os
        workflows = []

        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                try:
                    with open(f"{self.storage_path}/{filename}", 'r') as f:
                        data = json.load(f)
                    workflows.append({
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "description": data.get("description", ""),
                        "tags": data.get("tags", []),
                        "enabled": data.get("enabled", True),
                        "node_count": len(data.get("nodes", []))
                    })
                except Exception:
                    pass

        return workflows

    def delete(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        import os
        try:
            file_path = f"{self.storage_path}/{workflow_id}.json"
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            logger.error(f"Failed to delete workflow: {e}")
        return False


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_engine: Optional[WorkflowEngine] = None
_storage: Optional[WorkflowStorage] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine


def get_workflow_storage() -> WorkflowStorage:
    """Get the global workflow storage."""
    global _storage
    if _storage is None:
        _storage = WorkflowStorage()
    return _storage


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def run_workflow(
    workflow_id: str,
    variables: Optional[Dict[str, Any]] = None
) -> ExecutionContext:
    """Run a workflow by ID."""
    storage = get_workflow_storage()
    workflow = storage.load(workflow_id)

    if not workflow:
        raise ValueError(f"Workflow not found: {workflow_id}")

    engine = get_workflow_engine()
    return await engine.execute(workflow, initial_variables=variables)


async def run_inline(
    nodes: List[Dict[str, Any]],
    variables: Optional[Dict[str, Any]] = None
) -> ExecutionContext:
    """Run a workflow defined inline."""
    workflow = Workflow.from_dict({"nodes": nodes, "variables": variables or {}})
    engine = get_workflow_engine()
    return await engine.execute(workflow)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) > 1:
            workflow_id = sys.argv[1]
            print(f"Running workflow: {workflow_id}")
            context = await run_workflow(workflow_id)
            print(f"Status: {context.status.value}")
            print(f"Outputs: {context.node_outputs}")
        else:
            # Demo workflow
            workflow = Workflow(
                name="Demo Workflow",
                nodes=[
                    WorkflowNode(
                        id="start",
                        type=NodeType.ACTION,
                        name="Start",
                        config={"action": "log", "params": {"message": "Starting workflow..."}},
                        connections=[NodeConnection(source_id="start", target_id="transform")]
                    ),
                    WorkflowNode(
                        id="transform",
                        type=NodeType.TRANSFORM,
                        name="Create Data",
                        config={"transform": "passthrough", "input": {"x": 1, "y": 2}},
                        connections=[NodeConnection(source_id="transform", target_id="end")]
                    ),
                    WorkflowNode(
                        id="end",
                        type=NodeType.ACTION,
                        name="End",
                        config={"action": "log", "params": {"message": "Workflow complete!"}}
                    )
                ]
            )

            engine = get_workflow_engine()
            context = await engine.execute(workflow)

            print(f"\n🔄 WORKFLOW EXECUTION")
            print(f"{'='*50}")
            print(f"Status: {context.status.value}")
            print(f"Duration: {(context.completed_at - context.started_at).total_seconds():.2f}s")
            print(f"\nLogs:")
            for log in context.logs:
                print(f"  [{log['level']}] {log['message']}")

    asyncio.run(main())
