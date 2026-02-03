#!/usr/bin/env python3
"""
BAEL - Workflow Execution Engine
Actually runs visual workflows with node-by-node execution.

This transforms the workflow builder from a visual tool into a real
automation engine that executes nodes, handles branching, and manages state.
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.Workflow.Execution")


# =============================================================================
# ENUMS
# =============================================================================

class NodeType(Enum):
    """Types of workflow nodes."""
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    MERGE = "merge"
    DELAY = "delay"
    OUTPUT = "output"
    SUBWORKFLOW = "subworkflow"


class ExecutionStatus(Enum):
    """Node/workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    WAITING = "waiting"


class TriggerType(Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    FILE_CHANGE = "file_change"
    MESSAGE = "message"
    API_CALL = "api_call"
    EVENT = "event"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NodeResult:
    """Result of node execution."""
    node_id: str
    status: ExecutionStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowNode:
    """A node in a workflow."""
    id: str
    type: NodeType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)  # IDs of downstream nodes
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})

    # Condition-specific
    condition_true: Optional[str] = None  # Node ID if condition is true
    condition_false: Optional[str] = None  # Node ID if condition is false

    # Loop-specific
    loop_body: Optional[str] = None  # First node of loop body
    loop_exit: Optional[str] = None  # Node after loop


@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str
    name: str
    description: str = ""
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    trigger_node: Optional[str] = None  # Entry point
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionContext:
    """Context for a workflow execution."""
    execution_id: str
    workflow_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    current_node: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# =============================================================================
# NODE EXECUTORS
# =============================================================================

class NodeExecutor(ABC):
    """Base class for node executors."""

    @property
    @abstractmethod
    def node_type(self) -> NodeType:
        """Get the node type this executor handles."""
        pass

    @abstractmethod
    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> NodeResult:
        """Execute the node."""
        pass


class TriggerExecutor(NodeExecutor):
    """Executes trigger nodes."""

    @property
    def node_type(self) -> NodeType:
        return NodeType.TRIGGER

    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> NodeResult:
        """Trigger just passes through - actual triggering happens externally."""
        trigger_data = context.variables.get("_trigger_data", {})
        return NodeResult(
            node_id=node.id,
            status=ExecutionStatus.COMPLETED,
            output={"triggered": True, "data": trigger_data}
        )


class ActionExecutor(NodeExecutor):
    """Executes action nodes - the workhorse of workflows."""

    def __init__(self, action_registry: Optional[Dict[str, Callable]] = None):
        self.actions = action_registry or {}

    @property
    def node_type(self) -> NodeType:
        return NodeType.ACTION

    def register_action(self, name: str, handler: Callable) -> None:
        """Register an action handler."""
        self.actions[name] = handler

    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> NodeResult:
        start = time.time()
        action_type = node.config.get("action_type", "unknown")

        try:
            if action_type in self.actions:
                handler = self.actions[action_type]
                # Resolve variables in config
                resolved_config = self._resolve_variables(node.config, context)

                if asyncio.iscoroutinefunction(handler):
                    result = await handler(resolved_config, context)
                else:
                    result = handler(resolved_config, context)

                return NodeResult(
                    node_id=node.id,
                    status=ExecutionStatus.COMPLETED,
                    output=result,
                    duration_ms=(time.time() - start) * 1000
                )
            else:
                # Try to execute via brain
                result = await self._execute_via_brain(action_type, node.config, context, engine)
                return NodeResult(
                    node_id=node.id,
                    status=ExecutionStatus.COMPLETED,
                    output=result,
                    duration_ms=(time.time() - start) * 1000
                )

        except Exception as e:
            logger.error(f"Action {action_type} failed: {e}")
            return NodeResult(
                node_id=node.id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def _resolve_variables(self, config: Dict, context: ExecutionContext) -> Dict:
        """Resolve variable references in config."""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                resolved[key] = context.variables.get(var_name, value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_variables(value, context)
            else:
                resolved[key] = value
        return resolved

    async def _execute_via_brain(
        self,
        action_type: str,
        config: Dict,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> Any:
        """Execute action through the brain's tool system."""
        if engine.brain:
            # Use brain to execute the action
            return await engine.brain.execute_tool(action_type, config)
        else:
            raise ValueError(f"Unknown action type: {action_type}")


class ConditionExecutor(NodeExecutor):
    """Executes condition/branching nodes."""

    @property
    def node_type(self) -> NodeType:
        return NodeType.CONDITION

    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> NodeResult:
        condition = node.config.get("condition", "")

        try:
            # Evaluate condition
            result = self._evaluate_condition(condition, context)

            # Set next node based on result
            next_node = node.condition_true if result else node.condition_false

            return NodeResult(
                node_id=node.id,
                status=ExecutionStatus.COMPLETED,
                output={
                    "condition": condition,
                    "result": result,
                    "next_node": next_node
                }
            )
        except Exception as e:
            return NodeResult(
                node_id=node.id,
                status=ExecutionStatus.FAILED,
                error=str(e)
            )

    def _evaluate_condition(self, condition: str, context: ExecutionContext) -> bool:
        """Evaluate a condition expression."""
        # Simple expression evaluation with variables
        local_vars = {**context.variables}

        # Add node results as accessible variables
        for node_id, result in context.node_results.items():
            local_vars[f"node_{node_id}"] = result.output

        try:
            # Safe eval with limited scope
            return bool(eval(condition, {"__builtins__": {}}, local_vars))
        except Exception:
            # Default to False on evaluation error
            return False


class LoopExecutor(NodeExecutor):
    """Executes loop nodes."""

    @property
    def node_type(self) -> NodeType:
        return NodeType.LOOP

    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> NodeResult:
        loop_type = node.config.get("loop_type", "for_each")
        items = node.config.get("items", [])
        max_iterations = node.config.get("max_iterations", 100)

        # Resolve items if it's a variable reference
        if isinstance(items, str) and items.startswith("${"):
            var_name = items[2:-1]
            items = context.variables.get(var_name, [])

        results = []
        iteration = 0

        for item in items[:max_iterations]:
            # Set loop variables
            context.variables["_loop_item"] = item
            context.variables["_loop_index"] = iteration

            # Execute loop body
            if node.loop_body:
                body_result = await engine._execute_node(node.loop_body, context)
                results.append(body_result.output)

            iteration += 1

        return NodeResult(
            node_id=node.id,
            status=ExecutionStatus.COMPLETED,
            output={
                "iterations": iteration,
                "results": results
            }
        )


class ParallelExecutor(NodeExecutor):
    """Executes parallel branch nodes."""

    @property
    def node_type(self) -> NodeType:
        return NodeType.PARALLEL

    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> NodeResult:
        branches = node.connections

        # Execute all branches in parallel
        tasks = [
            engine._execute_node(branch_id, context)
            for branch_id in branches
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        branch_results = {}
        all_success = True

        for branch_id, result in zip(branches, results):
            if isinstance(result, Exception):
                branch_results[branch_id] = {"error": str(result)}
                all_success = False
            else:
                branch_results[branch_id] = result.output
                if result.status != ExecutionStatus.COMPLETED:
                    all_success = False

        return NodeResult(
            node_id=node.id,
            status=ExecutionStatus.COMPLETED if all_success else ExecutionStatus.FAILED,
            output=branch_results
        )


class DelayExecutor(NodeExecutor):
    """Executes delay/wait nodes."""

    @property
    def node_type(self) -> NodeType:
        return NodeType.DELAY

    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> NodeResult:
        delay_seconds = node.config.get("delay_seconds", 1)

        await asyncio.sleep(delay_seconds)

        return NodeResult(
            node_id=node.id,
            status=ExecutionStatus.COMPLETED,
            output={"delayed_seconds": delay_seconds}
        )


class OutputExecutor(NodeExecutor):
    """Executes output/terminal nodes."""

    @property
    def node_type(self) -> NodeType:
        return NodeType.OUTPUT

    async def execute(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        engine: "WorkflowExecutionEngine"
    ) -> NodeResult:
        output_type = node.config.get("output_type", "return")
        output_value = node.config.get("value", context.variables)

        # Resolve if variable reference
        if isinstance(output_value, str) and output_value.startswith("${"):
            var_name = output_value[2:-1]
            output_value = context.variables.get(var_name, output_value)

        if output_type == "log":
            logger.info(f"Workflow output: {output_value}")
        elif output_type == "webhook":
            # Send to webhook
            webhook_url = node.config.get("webhook_url")
            if webhook_url:
                await self._send_webhook(webhook_url, output_value)
        elif output_type == "store":
            # Store in memory/database
            store_key = node.config.get("store_key", "workflow_result")
            context.variables[store_key] = output_value

        return NodeResult(
            node_id=node.id,
            status=ExecutionStatus.COMPLETED,
            output=output_value
        )

    async def _send_webhook(self, url: str, data: Any) -> None:
        """Send data to a webhook URL."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=data)
        except Exception as e:
            logger.error(f"Webhook failed: {e}")


# =============================================================================
# WORKFLOW EXECUTION ENGINE
# =============================================================================

class WorkflowExecutionEngine:
    """
    Main engine for executing workflows.
    Manages node execution, state, and branching.
    """

    def __init__(self, brain: Optional[Any] = None):
        self.brain = brain
        self.executors: Dict[NodeType, NodeExecutor] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, ExecutionContext] = {}
        self.running: Set[str] = set()

        # Register default executors
        self._register_default_executors()

        # Register built-in actions
        self._register_builtin_actions()

    def _register_default_executors(self) -> None:
        """Register the default node executors."""
        self.action_executor = ActionExecutor()

        executors = [
            TriggerExecutor(),
            self.action_executor,
            ConditionExecutor(),
            LoopExecutor(),
            ParallelExecutor(),
            DelayExecutor(),
            OutputExecutor(),
        ]

        for executor in executors:
            self.executors[executor.node_type] = executor

    def _register_builtin_actions(self) -> None:
        """Register built-in action handlers."""

        async def http_request(config: Dict, context: ExecutionContext) -> Dict:
            import aiohttp
            method = config.get("method", "GET")
            url = config.get("url", "")
            headers = config.get("headers", {})
            body = config.get("body")

            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=body) as resp:
                    return {
                        "status": resp.status,
                        "body": await resp.text()
                    }

        async def execute_code(config: Dict, context: ExecutionContext) -> Any:
            code = config.get("code", "")
            language = config.get("language", "python")

            if language == "python":
                local_vars = {"context": context, "result": None}
                exec(code, {"__builtins__": __builtins__}, local_vars)
                return local_vars.get("result")
            else:
                raise ValueError(f"Unsupported language: {language}")

        async def set_variable(config: Dict, context: ExecutionContext) -> Dict:
            name = config.get("name", "")
            value = config.get("value")
            context.variables[name] = value
            return {"set": name, "value": value}

        async def send_message(config: Dict, context: ExecutionContext) -> Dict:
            message = config.get("message", "")
            channel = config.get("channel", "log")

            if channel == "log":
                logger.info(f"Workflow message: {message}")

            return {"sent": True, "message": message}

        async def think(config: Dict, context: ExecutionContext) -> Dict:
            """Use brain to think about something."""
            if self.brain:
                prompt = config.get("prompt", "")
                result = await self.brain.think(prompt)
                return result
            return {"error": "No brain connected"}

        # Register actions
        self.action_executor.register_action("http_request", http_request)
        self.action_executor.register_action("execute_code", execute_code)
        self.action_executor.register_action("set_variable", set_variable)
        self.action_executor.register_action("send_message", send_message)
        self.action_executor.register_action("think", think)

    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow."""
        self.workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.name} ({workflow.id})")

    def register_action(self, name: str, handler: Callable) -> None:
        """Register a custom action handler."""
        self.action_executor.register_action(name, handler)

    async def execute(
        self,
        workflow_id: str,
        trigger_data: Optional[Dict] = None,
        variables: Optional[Dict] = None
    ) -> ExecutionContext:
        """Execute a workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        workflow = self.workflows[workflow_id]

        # Create execution context
        context = ExecutionContext(
            execution_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            variables={
                **workflow.variables,
                **(variables or {}),
                "_trigger_data": trigger_data or {}
            },
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now()
        )

        self.executions[context.execution_id] = context
        self.running.add(context.execution_id)

        logger.info(f"Starting workflow execution: {workflow.name} ({context.execution_id})")

        try:
            # Start from trigger node
            if workflow.trigger_node:
                await self._execute_from_node(workflow.trigger_node, context, workflow)

            context.status = ExecutionStatus.COMPLETED
            logger.info(f"Workflow completed: {context.execution_id}")

        except Exception as e:
            context.status = ExecutionStatus.FAILED
            context.error = str(e)
            logger.error(f"Workflow failed: {context.execution_id} - {e}")

        finally:
            context.completed_at = datetime.now()
            self.running.discard(context.execution_id)

        return context

    async def _execute_from_node(
        self,
        node_id: str,
        context: ExecutionContext,
        workflow: Workflow
    ) -> None:
        """Execute from a specific node and follow connections."""
        if node_id not in workflow.nodes:
            return

        node = workflow.nodes[node_id]
        result = await self._execute_node(node_id, context)

        # Determine next node(s)
        if result.status == ExecutionStatus.COMPLETED:
            if node.type == NodeType.CONDITION:
                # Condition branching
                next_node = result.output.get("next_node")
                if next_node:
                    await self._execute_from_node(next_node, context, workflow)
            elif node.type == NodeType.PARALLEL:
                # Parallel already executed branches
                pass
            elif node.type == NodeType.OUTPUT:
                # Terminal node
                pass
            else:
                # Execute all connections
                for next_id in node.connections:
                    await self._execute_from_node(next_id, context, workflow)

    async def _execute_node(
        self,
        node_id: str,
        context: ExecutionContext
    ) -> NodeResult:
        """Execute a single node."""
        workflow = self.workflows[context.workflow_id]

        if node_id not in workflow.nodes:
            return NodeResult(
                node_id=node_id,
                status=ExecutionStatus.FAILED,
                error=f"Node not found: {node_id}"
            )

        node = workflow.nodes[node_id]
        context.current_node = node_id

        executor = self.executors.get(node.type)
        if not executor:
            return NodeResult(
                node_id=node_id,
                status=ExecutionStatus.FAILED,
                error=f"No executor for node type: {node.type}"
            )

        logger.debug(f"Executing node: {node.name} ({node_id})")
        result = await executor.execute(node, context, self)

        # Store result
        context.node_results[node_id] = result

        # Update variables with output
        if result.output is not None:
            context.variables[f"_node_{node_id}"] = result.output

        return result

    def cancel(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        if execution_id in self.executions:
            context = self.executions[execution_id]
            context.status = ExecutionStatus.CANCELLED
            self.running.discard(execution_id)
            return True
        return False

    def get_execution(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get execution context by ID."""
        return self.executions.get(execution_id)

    def get_running_executions(self) -> List[ExecutionContext]:
        """Get all running executions."""
        return [
            self.executions[eid]
            for eid in self.running
            if eid in self.executions
        ]

    def workflow_from_dict(self, data: Dict) -> Workflow:
        """Create a workflow from a dictionary (from UI)."""
        nodes = {}
        for node_data in data.get("nodes", []):
            node = WorkflowNode(
                id=node_data["id"],
                type=NodeType(node_data["type"]),
                name=node_data["name"],
                config=node_data.get("config", {}),
                connections=node_data.get("connections", []),
                position=node_data.get("position", {"x": 0, "y": 0}),
                condition_true=node_data.get("condition_true"),
                condition_false=node_data.get("condition_false"),
                loop_body=node_data.get("loop_body"),
                loop_exit=node_data.get("loop_exit")
            )
            nodes[node.id] = node

        # Find trigger node
        trigger_node = None
        for node in nodes.values():
            if node.type == NodeType.TRIGGER:
                trigger_node = node.id
                break

        return Workflow(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Untitled Workflow"),
            description=data.get("description", ""),
            nodes=nodes,
            trigger_node=trigger_node,
            variables=data.get("variables", {}),
            metadata=data.get("metadata", {})
        )


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_engine: Optional[WorkflowExecutionEngine] = None


def get_workflow_engine(brain: Optional[Any] = None) -> WorkflowExecutionEngine:
    """Get the global workflow engine instance."""
    global _engine
    if _engine is None:
        _engine = WorkflowExecutionEngine(brain)
    return _engine


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    async def demo():
        engine = get_workflow_engine()

        # Create a simple workflow
        workflow = Workflow(
            id="demo-workflow",
            name="Demo Workflow",
            description="A simple demo workflow",
            nodes={
                "trigger": WorkflowNode(
                    id="trigger",
                    type=NodeType.TRIGGER,
                    name="Start",
                    connections=["action1"]
                ),
                "action1": WorkflowNode(
                    id="action1",
                    type=NodeType.ACTION,
                    name="Set Greeting",
                    config={"action_type": "set_variable", "name": "greeting", "value": "Hello, World!"},
                    connections=["output"]
                ),
                "output": WorkflowNode(
                    id="output",
                    type=NodeType.OUTPUT,
                    name="Log Result",
                    config={"output_type": "log", "value": "${greeting}"}
                )
            },
            trigger_node="trigger"
        )

        engine.register_workflow(workflow)

        result = await engine.execute("demo-workflow")
        print(f"Execution: {result.status.value}")
        print(f"Variables: {result.variables}")

    asyncio.run(demo())
