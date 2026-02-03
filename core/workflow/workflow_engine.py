"""
BAEL - Workflow Engine
Advanced workflow automation and orchestration.

Features:
- Visual workflow builder
- Conditional branching
- Parallel execution
- Error handling
- State persistence
- Event triggers
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger("BAEL.Workflow")


# =============================================================================
# TYPES & ENUMS
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
    WAIT = "wait"
    TRIGGER = "trigger"
    SUBPROCESS = "subprocess"


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    EVENT = "event"
    CONDITION = "condition"


@dataclass
class WorkflowNode:
    """A node in a workflow."""
    id: str
    name: str
    node_type: NodeType

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)

    # Connections
    next_nodes: List[str] = field(default_factory=list)

    # For decision nodes
    conditions: Dict[str, str] = field(default_factory=dict)  # condition -> next_node_id
    default_next: Optional[str] = None

    # For parallel nodes
    parallel_branches: List[List[str]] = field(default_factory=list)

    # For loop nodes
    loop_condition: Optional[str] = None
    loop_body: List[str] = field(default_factory=list)
    max_iterations: int = 100

    # Execution
    handler: Optional[str] = None  # Handler function name
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_delay: int = 5


@dataclass
class WorkflowDefinition:
    """A complete workflow definition."""
    id: str
    name: str
    description: str
    version: str = "1.0.0"

    # Structure
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    start_node_id: Optional[str] = None

    # Configuration
    variables: Dict[str, Any] = field(default_factory=dict)
    triggers: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = "system"
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkflowInstance:
    """A running instance of a workflow."""
    id: str
    workflow_id: str
    workflow: WorkflowDefinition

    # State
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_node_id: Optional[str] = None

    # Context
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Parallel tracking
    pending_branches: Set[str] = field(default_factory=set)


# =============================================================================
# WORKFLOW BUILDER
# =============================================================================

class WorkflowBuilder:
    """Fluent API for building workflows."""

    def __init__(self, workflow_id: str, name: str):
        self._workflow = WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=""
        )
        self._node_counter = 0

    def description(self, desc: str) -> 'WorkflowBuilder':
        """Set workflow description."""
        self._workflow.description = desc
        return self

    def variable(self, name: str, default: Any = None) -> 'WorkflowBuilder':
        """Add a workflow variable."""
        self._workflow.variables[name] = default
        return self

    def start(self) -> 'WorkflowBuilder':
        """Add start node."""
        node = WorkflowNode(
            id="start",
            name="Start",
            node_type=NodeType.START
        )
        self._workflow.nodes["start"] = node
        self._workflow.start_node_id = "start"
        return self

    def task(
        self,
        node_id: str,
        name: str,
        handler: str,
        config: Dict[str, Any] = None
    ) -> 'WorkflowBuilder':
        """Add a task node."""
        node = WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.TASK,
            handler=handler,
            config=config or {}
        )
        self._workflow.nodes[node_id] = node
        return self

    def decision(
        self,
        node_id: str,
        name: str,
        conditions: Dict[str, str],
        default: str = None
    ) -> 'WorkflowBuilder':
        """Add a decision node."""
        node = WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.DECISION,
            conditions=conditions,
            default_next=default
        )
        self._workflow.nodes[node_id] = node
        return self

    def parallel(
        self,
        node_id: str,
        name: str,
        branches: List[List[str]]
    ) -> 'WorkflowBuilder':
        """Add a parallel execution node."""
        node = WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.PARALLEL,
            parallel_branches=branches
        )
        self._workflow.nodes[node_id] = node
        return self

    def join(self, node_id: str, name: str) -> 'WorkflowBuilder':
        """Add a join node (wait for parallel branches)."""
        node = WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.JOIN
        )
        self._workflow.nodes[node_id] = node
        return self

    def loop(
        self,
        node_id: str,
        name: str,
        condition: str,
        body: List[str],
        max_iter: int = 100
    ) -> 'WorkflowBuilder':
        """Add a loop node."""
        node = WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.LOOP,
            loop_condition=condition,
            loop_body=body,
            max_iterations=max_iter
        )
        self._workflow.nodes[node_id] = node
        return self

    def wait(
        self,
        node_id: str,
        name: str,
        duration_seconds: int = 0,
        until_event: str = None
    ) -> 'WorkflowBuilder':
        """Add a wait node."""
        node = WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.WAIT,
            config={
                "duration": duration_seconds,
                "event": until_event
            }
        )
        self._workflow.nodes[node_id] = node
        return self

    def end(self) -> 'WorkflowBuilder':
        """Add end node."""
        node = WorkflowNode(
            id="end",
            name="End",
            node_type=NodeType.END
        )
        self._workflow.nodes["end"] = node
        return self

    def connect(self, from_id: str, to_id: str) -> 'WorkflowBuilder':
        """Connect two nodes."""
        if from_id in self._workflow.nodes:
            self._workflow.nodes[from_id].next_nodes.append(to_id)
        return self

    def trigger(
        self,
        trigger_type: TriggerType,
        config: Dict[str, Any] = None
    ) -> 'WorkflowBuilder':
        """Add a trigger."""
        self._workflow.triggers.append({
            "type": trigger_type.value,
            "config": config or {}
        })
        return self

    def build(self) -> WorkflowDefinition:
        """Build and return the workflow."""
        return self._workflow


# =============================================================================
# WORKFLOW ENGINE
# =============================================================================

class WorkflowEngine:
    """Executes workflows."""

    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
        self._handlers: Dict[str, Callable] = {}
        self._instance_counter = 0

        # Register default handlers
        self._register_default_handlers()

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.name}")

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a task handler."""
        self._handlers[name] = handler

    def _register_default_handlers(self) -> None:
        """Register default handlers."""

        async def log_handler(context: Dict[str, Any]) -> Dict[str, Any]:
            message = context.get("config", {}).get("message", "Log step")
            logger.info(f"Workflow log: {message}")
            return {"logged": True}

        async def set_variable_handler(context: Dict[str, Any]) -> Dict[str, Any]:
            config = context.get("config", {})
            variables = context.get("variables", {})
            name = config.get("name")
            value = config.get("value")
            if name:
                variables[name] = value
            return {"set": name, "value": value}

        async def http_request_handler(context: Dict[str, Any]) -> Dict[str, Any]:
            config = context.get("config", {})
            # Simulated HTTP request
            return {
                "status": 200,
                "url": config.get("url"),
                "method": config.get("method", "GET")
            }

        async def ai_think_handler(context: Dict[str, Any]) -> Dict[str, Any]:
            config = context.get("config", {})
            prompt = config.get("prompt", "")
            # Would integrate with brain
            return {"response": f"AI response for: {prompt[:50]}"}

        self._handlers["log"] = log_handler
        self._handlers["set_variable"] = set_variable_handler
        self._handlers["http_request"] = http_request_handler
        self._handlers["ai_think"] = ai_think_handler

    async def start(
        self,
        workflow_id: str,
        variables: Dict[str, Any] = None
    ) -> WorkflowInstance:
        """Start a workflow instance."""
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow = self._workflows[workflow_id]

        instance_id = f"instance_{self._instance_counter}"
        self._instance_counter += 1

        instance = WorkflowInstance(
            id=instance_id,
            workflow_id=workflow_id,
            workflow=workflow,
            status=WorkflowStatus.PENDING,
            variables={**workflow.variables, **(variables or {})}
        )

        self._instances[instance_id] = instance

        # Start execution
        asyncio.create_task(self._execute(instance))

        logger.info(f"Started workflow instance: {instance_id}")
        return instance

    async def _execute(self, instance: WorkflowInstance) -> None:
        """Execute a workflow instance."""
        instance.status = WorkflowStatus.RUNNING
        instance.started_at = datetime.now()
        instance.current_node_id = instance.workflow.start_node_id

        try:
            while instance.current_node_id:
                node = instance.workflow.nodes.get(instance.current_node_id)
                if not node:
                    raise ValueError(f"Node not found: {instance.current_node_id}")

                # Record in history
                instance.history.append({
                    "node_id": node.id,
                    "node_name": node.name,
                    "timestamp": datetime.now().isoformat()
                })

                # Execute based on node type
                next_node_id = await self._execute_node(instance, node)

                if node.node_type == NodeType.END:
                    break

                instance.current_node_id = next_node_id

            instance.status = WorkflowStatus.COMPLETED
            instance.completed_at = datetime.now()
            logger.info(f"Workflow completed: {instance.id}")

        except Exception as e:
            instance.status = WorkflowStatus.FAILED
            instance.error = str(e)
            instance.completed_at = datetime.now()
            logger.error(f"Workflow failed: {instance.id} - {e}")

    async def _execute_node(
        self,
        instance: WorkflowInstance,
        node: WorkflowNode
    ) -> Optional[str]:
        """Execute a single node."""
        logger.debug(f"Executing node: {node.name} ({node.node_type.value})")

        if node.node_type == NodeType.START:
            return node.next_nodes[0] if node.next_nodes else None

        elif node.node_type == NodeType.END:
            return None

        elif node.node_type == NodeType.TASK:
            return await self._execute_task(instance, node)

        elif node.node_type == NodeType.DECISION:
            return await self._execute_decision(instance, node)

        elif node.node_type == NodeType.PARALLEL:
            return await self._execute_parallel(instance, node)

        elif node.node_type == NodeType.JOIN:
            return await self._execute_join(instance, node)

        elif node.node_type == NodeType.LOOP:
            return await self._execute_loop(instance, node)

        elif node.node_type == NodeType.WAIT:
            return await self._execute_wait(instance, node)

        return node.next_nodes[0] if node.next_nodes else None

    async def _execute_task(
        self,
        instance: WorkflowInstance,
        node: WorkflowNode
    ) -> Optional[str]:
        """Execute a task node."""
        handler_name = node.handler

        if not handler_name or handler_name not in self._handlers:
            logger.warning(f"Handler not found: {handler_name}")
            return node.next_nodes[0] if node.next_nodes else None

        handler = self._handlers[handler_name]

        context = {
            "node": node,
            "config": node.config,
            "variables": instance.variables,
            "history": instance.history
        }

        # Execute with retry
        for attempt in range(node.retry_count + 1):
            try:
                result = await asyncio.wait_for(
                    handler(context),
                    timeout=node.timeout_seconds
                )

                # Store result in variables
                instance.variables[f"_result_{node.id}"] = result

                return node.next_nodes[0] if node.next_nodes else None

            except asyncio.TimeoutError:
                logger.warning(f"Task timeout: {node.name} (attempt {attempt + 1})")
                if attempt < node.retry_count:
                    await asyncio.sleep(node.retry_delay)
                else:
                    raise

            except Exception as e:
                logger.warning(f"Task error: {node.name} - {e} (attempt {attempt + 1})")
                if attempt < node.retry_count:
                    await asyncio.sleep(node.retry_delay)
                else:
                    raise

    async def _execute_decision(
        self,
        instance: WorkflowInstance,
        node: WorkflowNode
    ) -> Optional[str]:
        """Execute a decision node."""
        for condition, next_node_id in node.conditions.items():
            try:
                # Evaluate condition with variables
                result = eval(condition, {"__builtins__": {}}, instance.variables)
                if result:
                    return next_node_id
            except Exception as e:
                logger.warning(f"Condition error: {condition} - {e}")

        return node.default_next

    async def _execute_parallel(
        self,
        instance: WorkflowInstance,
        node: WorkflowNode
    ) -> Optional[str]:
        """Execute parallel branches."""
        tasks = []

        for branch in node.parallel_branches:
            if branch:
                # Execute first node of each branch
                branch_node_id = branch[0]
                branch_node = instance.workflow.nodes.get(branch_node_id)
                if branch_node:
                    task = self._execute_node(instance, branch_node)
                    tasks.append(task)
                    instance.pending_branches.add(branch_node_id)

        # Wait for all branches
        await asyncio.gather(*tasks, return_exceptions=True)

        return node.next_nodes[0] if node.next_nodes else None

    async def _execute_join(
        self,
        instance: WorkflowInstance,
        node: WorkflowNode
    ) -> Optional[str]:
        """Execute a join node (wait for parallel branches)."""
        # Simply continue - parallel execution handles waiting
        instance.pending_branches.clear()
        return node.next_nodes[0] if node.next_nodes else None

    async def _execute_loop(
        self,
        instance: WorkflowInstance,
        node: WorkflowNode
    ) -> Optional[str]:
        """Execute a loop node."""
        iteration = 0

        while iteration < node.max_iterations:
            # Check condition
            try:
                should_continue = eval(
                    node.loop_condition or "False",
                    {"__builtins__": {}},
                    {**instance.variables, "_iteration": iteration}
                )
                if not should_continue:
                    break
            except Exception as e:
                logger.warning(f"Loop condition error: {e}")
                break

            # Execute loop body
            for body_node_id in node.loop_body:
                body_node = instance.workflow.nodes.get(body_node_id)
                if body_node:
                    await self._execute_node(instance, body_node)

            iteration += 1

        instance.variables["_loop_iterations"] = iteration
        return node.next_nodes[0] if node.next_nodes else None

    async def _execute_wait(
        self,
        instance: WorkflowInstance,
        node: WorkflowNode
    ) -> Optional[str]:
        """Execute a wait node."""
        duration = node.config.get("duration", 0)

        if duration > 0:
            await asyncio.sleep(duration)

        return node.next_nodes[0] if node.next_nodes else None

    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get a workflow instance."""
        return self._instances.get(instance_id)

    def list_instances(
        self,
        workflow_id: str = None,
        status: WorkflowStatus = None
    ) -> List[WorkflowInstance]:
        """List workflow instances."""
        instances = list(self._instances.values())

        if workflow_id:
            instances = [i for i in instances if i.workflow_id == workflow_id]

        if status:
            instances = [i for i in instances if i.status == status]

        return instances

    async def pause(self, instance_id: str) -> bool:
        """Pause a workflow instance."""
        instance = self._instances.get(instance_id)
        if instance and instance.status == WorkflowStatus.RUNNING:
            instance.status = WorkflowStatus.PAUSED
            return True
        return False

    async def resume(self, instance_id: str) -> bool:
        """Resume a paused workflow instance."""
        instance = self._instances.get(instance_id)
        if instance and instance.status == WorkflowStatus.PAUSED:
            instance.status = WorkflowStatus.RUNNING
            asyncio.create_task(self._execute(instance))
            return True
        return False

    async def cancel(self, instance_id: str) -> bool:
        """Cancel a workflow instance."""
        instance = self._instances.get(instance_id)
        if instance and instance.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
            instance.status = WorkflowStatus.CANCELLED
            instance.completed_at = datetime.now()
            return True
        return False


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test workflow engine."""
    engine = WorkflowEngine()

    # Build a sample workflow
    workflow = (
        WorkflowBuilder("sample-workflow", "Sample Workflow")
        .description("A sample workflow demonstrating various node types")
        .variable("counter", 0)
        .variable("threshold", 5)
        .start()
        .task("init", "Initialize", "log", {"message": "Workflow started"})
        .decision("check", "Check Counter", {
            "counter < threshold": "increment"
        }, default="finish")
        .task("increment", "Increment", "set_variable", {"name": "counter", "value": 1})
        .task("finish", "Finish", "log", {"message": "Workflow finished"})
        .end()
        .connect("start", "init")
        .connect("init", "check")
        .connect("increment", "check")
        .connect("finish", "end")
        .trigger(TriggerType.MANUAL)
        .build()
    )

    engine.register_workflow(workflow)

    print(f"Workflow: {workflow.name}")
    print(f"Nodes: {len(workflow.nodes)}")
    print(f"Variables: {workflow.variables}")

    # Start the workflow
    instance = await engine.start(workflow.id, {"counter": 0, "threshold": 3})

    print(f"\nInstance: {instance.id}")
    print(f"Status: {instance.status.value}")

    # Wait for completion
    await asyncio.sleep(2)

    print(f"\nFinal status: {instance.status.value}")
    print(f"History: {len(instance.history)} steps")
    for step in instance.history:
        print(f"  - {step['node_name']}")


if __name__ == "__main__":
    asyncio.run(main())
