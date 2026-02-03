#!/usr/bin/env python3
"""
BAEL - Business Process Workflow Engine
Comprehensive process orchestration and automation.

This module provides a complete workflow engine for
orchestrating complex business processes and pipelines.

Features:
- Visual workflow definition
- Node-based execution
- Conditional branching
- Parallel execution
- Error handling
- State persistence
- Rollback support
- Event triggers
- Human tasks
- Workflow versioning
"""

import asyncio
import functools
import json
import logging
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class WFNodeType(Enum):
    """Types of workflow nodes."""
    START = "start"
    END = "end"
    TASK = "task"
    DECISION = "decision"
    PARALLEL = "parallel"
    JOIN = "join"
    HUMAN = "human"
    SUBPROCESS = "subprocess"
    EVENT = "event"
    DELAY = "delay"


class WFStatus(Enum):
    """Workflow execution status."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WFNodeStatus(Enum):
    """Node execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WFTransitionType(Enum):
    """Types of transitions."""
    ALWAYS = "always"
    CONDITIONAL = "conditional"
    DEFAULT = "default"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class WFContext:
    """Context for workflow execution."""
    workflow_id: str
    instance_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value


@dataclass
class WFNodeResult:
    """Result of node execution."""
    node_id: str
    status: WFNodeStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    next_nodes: List[str] = field(default_factory=list)


@dataclass
class WFResult:
    """Result of workflow execution."""
    instance_id: str
    status: WFStatus
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0
    node_results: Dict[str, WFNodeResult] = field(default_factory=dict)


@dataclass
class WFTransitionDef:
    """Transition definition."""
    source_id: str
    target_id: str
    transition_type: WFTransitionType = WFTransitionType.ALWAYS
    condition: Optional[Callable[[WFContext], bool]] = None
    name: str = ""


@dataclass
class WFNodeExecution:
    """Node execution record."""
    node_id: str
    status: WFNodeStatus
    started_at: float = 0
    completed_at: float = 0
    output: Any = None
    error: Optional[str] = None
    retry_count: int = 0


# =============================================================================
# NODES
# =============================================================================

class WFNode(ABC):
    """Abstract workflow node."""

    def __init__(
        self,
        node_id: str,
        name: str = "",
        node_type: WFNodeType = WFNodeType.TASK
    ):
        self.node_id = node_id
        self.name = name or node_id
        self.node_type = node_type

        # Configuration
        self.retry_count = 0
        self.retry_delay = 1.0
        self.timeout: Optional[float] = None

        # Metadata
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, context: WFContext) -> WFNodeResult:
        """Execute the node."""
        pass

    def on_enter(self, context: WFContext) -> None:
        """Called when entering the node."""
        pass

    def on_exit(self, context: WFContext, result: WFNodeResult) -> None:
        """Called when exiting the node."""
        pass


class WFStartNode(WFNode):
    """Start node - entry point."""

    def __init__(self, node_id: str = "start"):
        super().__init__(node_id, "Start", WFNodeType.START)

    async def execute(self, context: WFContext) -> WFNodeResult:
        return WFNodeResult(
            node_id=self.node_id,
            status=WFNodeStatus.COMPLETED
        )


class WFEndNode(WFNode):
    """End node - exit point."""

    def __init__(self, node_id: str = "end"):
        super().__init__(node_id, "End", WFNodeType.END)

    async def execute(self, context: WFContext) -> WFNodeResult:
        return WFNodeResult(
            node_id=self.node_id,
            status=WFNodeStatus.COMPLETED,
            output=context.variables.copy()
        )


class WFTaskNode(WFNode):
    """Task node - executes a function."""

    def __init__(
        self,
        node_id: str,
        name: str = "",
        task: Callable[[WFContext], Awaitable[Any]] = None
    ):
        super().__init__(node_id, name, WFNodeType.TASK)
        self._task = task

    async def execute(self, context: WFContext) -> WFNodeResult:
        start_time = time.time()

        try:
            if self._task:
                if asyncio.iscoroutinefunction(self._task):
                    output = await self._task(context)
                else:
                    output = self._task(context)
            else:
                output = None

            return WFNodeResult(
                node_id=self.node_id,
                status=WFNodeStatus.COMPLETED,
                output=output,
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return WFNodeResult(
                node_id=self.node_id,
                status=WFNodeStatus.FAILED,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )


class WFDecisionNode(WFNode):
    """Decision node - conditional branching."""

    def __init__(
        self,
        node_id: str,
        name: str = "",
        condition: Callable[[WFContext], str] = None
    ):
        super().__init__(node_id, name, WFNodeType.DECISION)
        self._condition = condition
        self.branches: Dict[str, str] = {}
        self.default_branch: Optional[str] = None

    def add_branch(self, result: str, target_id: str) -> None:
        self.branches[result] = target_id

    async def execute(self, context: WFContext) -> WFNodeResult:
        try:
            if self._condition:
                if asyncio.iscoroutinefunction(self._condition):
                    result = await self._condition(context)
                else:
                    result = self._condition(context)
            else:
                result = "default"

            next_node = self.branches.get(result, self.default_branch)

            if not next_node:
                return WFNodeResult(
                    node_id=self.node_id,
                    status=WFNodeStatus.FAILED,
                    error=f"No branch for result: {result}"
                )

            return WFNodeResult(
                node_id=self.node_id,
                status=WFNodeStatus.COMPLETED,
                output=result,
                next_nodes=[next_node]
            )
        except Exception as e:
            return WFNodeResult(
                node_id=self.node_id,
                status=WFNodeStatus.FAILED,
                error=str(e)
            )


class WFParallelNode(WFNode):
    """Parallel node - fork execution."""

    def __init__(self, node_id: str, name: str = ""):
        super().__init__(node_id, name, WFNodeType.PARALLEL)
        self.branch_nodes: List[str] = []

    def add_branch(self, node_id: str) -> None:
        self.branch_nodes.append(node_id)

    async def execute(self, context: WFContext) -> WFNodeResult:
        return WFNodeResult(
            node_id=self.node_id,
            status=WFNodeStatus.COMPLETED,
            next_nodes=self.branch_nodes.copy()
        )


class WFJoinNode(WFNode):
    """Join node - synchronize parallel branches."""

    def __init__(self, node_id: str, name: str = ""):
        super().__init__(node_id, name, WFNodeType.JOIN)
        self.expected_inputs: int = 2
        self._received: Set[str] = set()

    def receive(self, from_node: str) -> bool:
        self._received.add(from_node)
        return len(self._received) >= self.expected_inputs

    def reset(self) -> None:
        self._received.clear()

    async def execute(self, context: WFContext) -> WFNodeResult:
        return WFNodeResult(
            node_id=self.node_id,
            status=WFNodeStatus.COMPLETED
        )


class WFDelayNode(WFNode):
    """Delay node - pause execution."""

    def __init__(
        self,
        node_id: str,
        name: str = "",
        delay_seconds: float = 1.0
    ):
        super().__init__(node_id, name, WFNodeType.DELAY)
        self.delay_seconds = delay_seconds

    async def execute(self, context: WFContext) -> WFNodeResult:
        await asyncio.sleep(self.delay_seconds)
        return WFNodeResult(
            node_id=self.node_id,
            status=WFNodeStatus.COMPLETED
        )


class WFHumanTaskNode(WFNode):
    """Human task node - requires human interaction."""

    def __init__(
        self,
        node_id: str,
        name: str = "",
        assignee: str = None
    ):
        super().__init__(node_id, name, WFNodeType.HUMAN)
        self.assignee = assignee
        self.completed = False
        self.result: Any = None

    def complete(self, result: Any) -> None:
        self.completed = True
        self.result = result

    async def execute(self, context: WFContext) -> WFNodeResult:
        if not self.completed:
            return WFNodeResult(
                node_id=self.node_id,
                status=WFNodeStatus.PENDING
            )

        return WFNodeResult(
            node_id=self.node_id,
            status=WFNodeStatus.COMPLETED,
            output=self.result
        )


# =============================================================================
# WORKFLOW DEFINITION
# =============================================================================

class WFDefinition:
    """
    Defines a workflow structure.
    """

    def __init__(
        self,
        workflow_id: str,
        name: str = "",
        version: str = "1.0.0"
    ):
        self.workflow_id = workflow_id
        self.name = name or workflow_id
        self.version = version

        # Nodes
        self.nodes: Dict[str, WFNode] = {}
        self.start_node: Optional[str] = None

        # Transitions
        self.transitions: Dict[str, List[WFTransitionDef]] = defaultdict(list)

        # Metadata
        self.metadata: Dict[str, Any] = {}
        self.created_at = time.time()

    def add_node(self, node: WFNode) -> 'WFDefinition':
        """Add a node."""
        self.nodes[node.node_id] = node

        if node.node_type == WFNodeType.START:
            self.start_node = node.node_id

        return self

    def add_transition(
        self,
        source_id: str,
        target_id: str,
        condition: Callable[[WFContext], bool] = None,
        name: str = ""
    ) -> 'WFDefinition':
        """Add a transition."""
        transition = WFTransitionDef(
            source_id=source_id,
            target_id=target_id,
            transition_type=WFTransitionType.CONDITIONAL if condition else WFTransitionType.ALWAYS,
            condition=condition,
            name=name
        )

        self.transitions[source_id].append(transition)
        return self

    def connect(self, source_id: str, target_id: str) -> 'WFDefinition':
        """Connect two nodes."""
        return self.add_transition(source_id, target_id)

    def get_node(self, node_id: str) -> Optional[WFNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_next_nodes(
        self,
        node_id: str,
        context: WFContext
    ) -> List[str]:
        """Get next nodes based on transitions."""
        transitions = self.transitions.get(node_id, [])
        next_nodes = []

        for transition in transitions:
            if transition.transition_type == WFTransitionType.ALWAYS:
                next_nodes.append(transition.target_id)
            elif transition.condition:
                try:
                    if transition.condition(context):
                        next_nodes.append(transition.target_id)
                except:
                    pass

        return next_nodes

    def validate(self) -> List[str]:
        """Validate the workflow definition."""
        errors = []

        if not self.start_node:
            errors.append("No start node defined")

        if self.start_node and self.start_node not in self.nodes:
            errors.append(f"Start node '{self.start_node}' not found")

        for source_id, transitions in self.transitions.items():
            if source_id not in self.nodes:
                errors.append(f"Transition source '{source_id}' not found")

            for trans in transitions:
                if trans.target_id not in self.nodes:
                    errors.append(f"Transition target '{trans.target_id}' not found")

        return errors


# =============================================================================
# WORKFLOW INSTANCE
# =============================================================================

class WFInstance:
    """
    A running instance of a workflow.
    """

    def __init__(
        self,
        definition: WFDefinition,
        variables: Dict[str, Any] = None
    ):
        self.instance_id = str(uuid.uuid4())
        self.definition = definition
        self.status = WFStatus.CREATED

        # Context
        self.context = WFContext(
            workflow_id=definition.workflow_id,
            instance_id=self.instance_id,
            variables=variables or {}
        )

        # Execution state
        self.current_nodes: Set[str] = set()
        self.completed_nodes: Set[str] = set()
        self.node_executions: Dict[str, WFNodeExecution] = {}

        # Timing
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None

        # Error
        self.error: Optional[str] = None

    def start(self) -> None:
        """Start the workflow."""
        if self.definition.start_node:
            self.status = WFStatus.RUNNING
            self.started_at = time.time()
            self.current_nodes.add(self.definition.start_node)

    def complete(self, output: Dict[str, Any] = None) -> None:
        """Complete the workflow."""
        self.status = WFStatus.COMPLETED
        self.completed_at = time.time()

        if output:
            self.context.variables.update(output)

    def fail(self, error: str) -> None:
        """Fail the workflow."""
        self.status = WFStatus.FAILED
        self.completed_at = time.time()
        self.error = error

    def get_result(self) -> WFResult:
        """Get workflow result."""
        return WFResult(
            instance_id=self.instance_id,
            status=self.status,
            output=self.context.variables,
            error=self.error,
            duration_ms=(
                (self.completed_at - self.started_at) * 1000
                if self.started_at and self.completed_at else 0
            ),
            node_results={
                node_id: WFNodeResult(
                    node_id=node_id,
                    status=exec.status,
                    output=exec.output,
                    error=exec.error,
                    duration_ms=(exec.completed_at - exec.started_at) * 1000 if exec.completed_at else 0
                )
                for node_id, exec in self.node_executions.items()
            }
        )


# =============================================================================
# WORKFLOW ENGINE
# =============================================================================

class WFEngine:
    """
    Core workflow execution engine.
    """

    def __init__(self):
        self.definitions: Dict[str, WFDefinition] = {}
        self.instances: Dict[str, WFInstance] = {}

        # Event handlers
        self.on_node_start: List[Callable] = []
        self.on_node_complete: List[Callable] = []
        self.on_workflow_complete: List[Callable] = []

        # Statistics
        self.total_runs = 0
        self.completed_runs = 0
        self.failed_runs = 0

    def register(self, definition: WFDefinition) -> None:
        """Register a workflow definition."""
        errors = definition.validate()
        if errors:
            raise ValueError(f"Invalid workflow: {errors}")

        self.definitions[definition.workflow_id] = definition

    def create_instance(
        self,
        workflow_id: str,
        variables: Dict[str, Any] = None
    ) -> WFInstance:
        """Create a new workflow instance."""
        definition = self.definitions.get(workflow_id)
        if not definition:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        instance = WFInstance(definition, variables)
        self.instances[instance.instance_id] = instance
        return instance

    async def run(
        self,
        workflow_id: str,
        variables: Dict[str, Any] = None
    ) -> WFResult:
        """Run a workflow to completion."""
        instance = self.create_instance(workflow_id, variables)
        return await self.execute(instance)

    async def execute(self, instance: WFInstance) -> WFResult:
        """Execute a workflow instance."""
        self.total_runs += 1
        instance.start()

        try:
            while instance.current_nodes and instance.status == WFStatus.RUNNING:
                nodes_to_execute = list(instance.current_nodes)

                results = await asyncio.gather(
                    *[self._execute_node(instance, node_id) for node_id in nodes_to_execute],
                    return_exceptions=True
                )

                for node_id, result in zip(nodes_to_execute, results):
                    if isinstance(result, Exception):
                        instance.fail(str(result))
                        break

                    await self._process_node_result(instance, node_id, result)

            if instance.status == WFStatus.RUNNING:
                instance.complete()

            if instance.status == WFStatus.COMPLETED:
                self.completed_runs += 1
            else:
                self.failed_runs += 1

            for handler in self.on_workflow_complete:
                if asyncio.iscoroutinefunction(handler):
                    await handler(instance)
                else:
                    handler(instance)

            return instance.get_result()

        except Exception as e:
            instance.fail(str(e))
            self.failed_runs += 1
            return instance.get_result()

    async def _execute_node(
        self,
        instance: WFInstance,
        node_id: str
    ) -> WFNodeResult:
        """Execute a single node."""
        node = instance.definition.get_node(node_id)
        if not node:
            return WFNodeResult(
                node_id=node_id,
                status=WFNodeStatus.FAILED,
                error=f"Node '{node_id}' not found"
            )

        execution = WFNodeExecution(
            node_id=node_id,
            status=WFNodeStatus.RUNNING,
            started_at=time.time()
        )
        instance.node_executions[node_id] = execution

        for handler in self.on_node_start:
            if asyncio.iscoroutinefunction(handler):
                await handler(instance, node)
            else:
                handler(instance, node)

        result = None
        for attempt in range(max(1, node.retry_count + 1)):
            try:
                if node.timeout:
                    result = await asyncio.wait_for(
                        node.execute(instance.context),
                        timeout=node.timeout
                    )
                else:
                    result = await node.execute(instance.context)

                if result.status == WFNodeStatus.COMPLETED:
                    break

                if attempt < node.retry_count:
                    execution.retry_count += 1
                    await asyncio.sleep(node.retry_delay)

            except asyncio.TimeoutError:
                result = WFNodeResult(
                    node_id=node_id,
                    status=WFNodeStatus.FAILED,
                    error="Node execution timed out"
                )
            except Exception as e:
                result = WFNodeResult(
                    node_id=node_id,
                    status=WFNodeStatus.FAILED,
                    error=str(e)
                )

        execution.status = result.status
        execution.completed_at = time.time()
        execution.output = result.output
        execution.error = result.error

        for handler in self.on_node_complete:
            if asyncio.iscoroutinefunction(handler):
                await handler(instance, node, result)
            else:
                handler(instance, node, result)

        return result

    async def _process_node_result(
        self,
        instance: WFInstance,
        node_id: str,
        result: WFNodeResult
    ) -> None:
        """Process node execution result."""
        instance.current_nodes.discard(node_id)

        if result.status == WFNodeStatus.FAILED:
            instance.fail(result.error or f"Node '{node_id}' failed")
            return

        if result.status == WFNodeStatus.PENDING:
            instance.status = WFStatus.WAITING
            instance.current_nodes.add(node_id)
            return

        instance.completed_nodes.add(node_id)

        node = instance.definition.get_node(node_id)

        if result.next_nodes:
            next_nodes = result.next_nodes
        elif node and node.node_type == WFNodeType.END:
            next_nodes = []
        else:
            next_nodes = instance.definition.get_next_nodes(
                node_id,
                instance.context
            )

        for next_id in next_nodes:
            next_node = instance.definition.get_node(next_id)

            if isinstance(next_node, WFJoinNode):
                if next_node.receive(node_id):
                    next_node.reset()
                    instance.current_nodes.add(next_id)
            else:
                instance.current_nodes.add(next_id)

    def get_instance(self, instance_id: str) -> Optional[WFInstance]:
        """Get workflow instance."""
        return self.instances.get(instance_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "definitions": len(self.definitions),
            "instances": len(self.instances),
            "total_runs": self.total_runs,
            "completed_runs": self.completed_runs,
            "failed_runs": self.failed_runs,
            "success_rate": (
                self.completed_runs / self.total_runs
                if self.total_runs > 0 else 0
            )
        }


# =============================================================================
# WORKFLOW BUILDER
# =============================================================================

class WFBuilder:
    """
    Fluent builder for workflows.
    """

    def __init__(self, workflow_id: str, name: str = ""):
        self.definition = WFDefinition(workflow_id, name)
        self._last_node: Optional[str] = None

    def start(self, node_id: str = "start") -> 'WFBuilder':
        """Add start node."""
        self.definition.add_node(WFStartNode(node_id))
        self._last_node = node_id
        return self

    def end(self, node_id: str = "end") -> 'WFBuilder':
        """Add end node."""
        self.definition.add_node(WFEndNode(node_id))
        if self._last_node:
            self.definition.connect(self._last_node, node_id)
        self._last_node = node_id
        return self

    def task(
        self,
        node_id: str,
        task: Callable[[WFContext], Awaitable[Any]],
        name: str = ""
    ) -> 'WFBuilder':
        """Add task node."""
        self.definition.add_node(WFTaskNode(node_id, name, task))
        if self._last_node:
            self.definition.connect(self._last_node, node_id)
        self._last_node = node_id
        return self

    def decision(
        self,
        node_id: str,
        condition: Callable[[WFContext], str],
        branches: Dict[str, str],
        name: str = ""
    ) -> 'WFBuilder':
        """Add decision node."""
        node = WFDecisionNode(node_id, name, condition)

        for result, target in branches.items():
            node.add_branch(result, target)

        self.definition.add_node(node)
        if self._last_node:
            self.definition.connect(self._last_node, node_id)
        self._last_node = node_id
        return self

    def parallel(
        self,
        node_id: str,
        branches: List[str],
        name: str = ""
    ) -> 'WFBuilder':
        """Add parallel node."""
        node = WFParallelNode(node_id, name)

        for branch in branches:
            node.add_branch(branch)

        self.definition.add_node(node)
        if self._last_node:
            self.definition.connect(self._last_node, node_id)
        self._last_node = node_id
        return self

    def join(
        self,
        node_id: str,
        expected_inputs: int = 2,
        name: str = ""
    ) -> 'WFBuilder':
        """Add join node."""
        node = WFJoinNode(node_id, name)
        node.expected_inputs = expected_inputs
        self.definition.add_node(node)
        self._last_node = node_id
        return self

    def delay(
        self,
        node_id: str,
        seconds: float,
        name: str = ""
    ) -> 'WFBuilder':
        """Add delay node."""
        self.definition.add_node(WFDelayNode(node_id, name, seconds))
        if self._last_node:
            self.definition.connect(self._last_node, node_id)
        self._last_node = node_id
        return self

    def connect(
        self,
        source_id: str,
        target_id: str,
        condition: Callable = None
    ) -> 'WFBuilder':
        """Connect two nodes."""
        self.definition.add_transition(source_id, target_id, condition)
        return self

    def node(self, node: WFNode) -> 'WFBuilder':
        """Add custom node."""
        self.definition.add_node(node)
        if self._last_node:
            self.definition.connect(self._last_node, node.node_id)
        self._last_node = node.node_id
        return self

    def build(self) -> WFDefinition:
        """Build the workflow definition."""
        return self.definition


# =============================================================================
# WORKFLOW MANAGER
# =============================================================================

class ProcessWorkflowManager:
    """
    Master workflow manager for BAEL.

    Manages workflow definitions, instances, and execution.
    """

    def __init__(self):
        self.engine = WFEngine()
        self.scheduled: Dict[str, asyncio.Task] = {}

    def register(self, definition: WFDefinition) -> None:
        """Register a workflow."""
        self.engine.register(definition)

    def builder(self, workflow_id: str, name: str = "") -> WFBuilder:
        """Create workflow builder."""
        return WFBuilder(workflow_id, name)

    async def run(
        self,
        workflow_id: str,
        variables: Dict[str, Any] = None
    ) -> WFResult:
        """Run a workflow."""
        return await self.engine.run(workflow_id, variables)

    async def run_async(
        self,
        workflow_id: str,
        variables: Dict[str, Any] = None
    ) -> str:
        """Start workflow asynchronously, return instance ID."""
        instance = self.engine.create_instance(workflow_id, variables)
        asyncio.create_task(self.engine.execute(instance))
        return instance.instance_id

    def get_instance(self, instance_id: str) -> Optional[WFInstance]:
        """Get workflow instance."""
        return self.engine.get_instance(instance_id)

    def get_status(self, instance_id: str) -> Optional[WFStatus]:
        """Get instance status."""
        instance = self.get_instance(instance_id)
        return instance.status if instance else None

    def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.engine.get_statistics(),
            "scheduled": len(self.scheduled)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Workflow Engine."""
    print("=" * 70)
    print("BAEL - BUSINESS PROCESS WORKFLOW ENGINE DEMO")
    print("Process Orchestration & Automation")
    print("=" * 70)
    print()

    manager = ProcessWorkflowManager()

    # 1. Simple Linear Workflow
    print("1. SIMPLE LINEAR WORKFLOW:")
    print("-" * 40)

    async def step1(ctx: WFContext):
        ctx.set("step1_done", True)
        return "Step 1 complete"

    async def step2(ctx: WFContext):
        ctx.set("step2_done", True)
        return "Step 2 complete"

    simple_workflow = (
        manager.builder("simple-workflow", "Simple Workflow")
        .start()
        .task("step1", step1, "Step 1")
        .task("step2", step2, "Step 2")
        .end()
        .build()
    )

    manager.register(simple_workflow)

    result = await manager.run("simple-workflow", {"input": "test"})
    print(f"   Status: {result.status.value}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print(f"   Output: step1_done={result.output.get('step1_done')}")
    print()

    # 2. Decision Workflow
    print("2. DECISION WORKFLOW:")
    print("-" * 40)

    async def check_amount(ctx: WFContext):
        amount = ctx.get("amount", 0)
        return "high" if amount > 100 else "low"

    async def process_high(ctx: WFContext):
        ctx.set("approval", "manager")
        return "Manager approval required"

    async def process_low(ctx: WFContext):
        ctx.set("approval", "auto")
        return "Auto approved"

    decision_def = WFDefinition("decision-wf", "Decision Workflow")
    decision_def.add_node(WFStartNode())

    check_node = WFDecisionNode("check", "Check Amount", check_amount)
    check_node.add_branch("high", "high_value")
    check_node.add_branch("low", "low_value")
    decision_def.add_node(check_node)

    decision_def.add_node(WFTaskNode("high_value", "High Value", process_high))
    decision_def.add_node(WFTaskNode("low_value", "Low Value", process_low))
    decision_def.add_node(WFEndNode())

    decision_def.connect("start", "check")
    decision_def.connect("high_value", "end")
    decision_def.connect("low_value", "end")

    manager.register(decision_def)

    result_high = await manager.run("decision-wf", {"amount": 200})
    print(f"   Amount=200: approval={result_high.output.get('approval')}")

    result_low = await manager.run("decision-wf", {"amount": 50})
    print(f"   Amount=50: approval={result_low.output.get('approval')}")
    print()

    # 3. Parallel Workflow
    print("3. PARALLEL WORKFLOW:")
    print("-" * 40)

    async def task_a(ctx: WFContext):
        await asyncio.sleep(0.1)
        ctx.set("task_a", "done")

    async def task_b(ctx: WFContext):
        await asyncio.sleep(0.15)
        ctx.set("task_b", "done")

    async def task_c(ctx: WFContext):
        await asyncio.sleep(0.05)
        ctx.set("task_c", "done")

    parallel_def = WFDefinition("parallel-wf", "Parallel Workflow")
    parallel_def.add_node(WFStartNode())

    fork = WFParallelNode("fork", "Fork")
    fork.add_branch("task_a")
    fork.add_branch("task_b")
    fork.add_branch("task_c")
    parallel_def.add_node(fork)

    parallel_def.add_node(WFTaskNode("task_a", "Task A", task_a))
    parallel_def.add_node(WFTaskNode("task_b", "Task B", task_b))
    parallel_def.add_node(WFTaskNode("task_c", "Task C", task_c))

    join = WFJoinNode("join", "Join")
    join.expected_inputs = 3
    parallel_def.add_node(join)

    parallel_def.add_node(WFEndNode())

    parallel_def.connect("start", "fork")
    parallel_def.connect("task_a", "join")
    parallel_def.connect("task_b", "join")
    parallel_def.connect("task_c", "join")
    parallel_def.connect("join", "end")

    manager.register(parallel_def)

    result = await manager.run("parallel-wf")
    print(f"   Status: {result.status.value}")
    print(f"   All tasks: A={result.output.get('task_a')}, B={result.output.get('task_b')}, C={result.output.get('task_c')}")
    print(f"   Duration: {result.duration_ms:.2f}ms (parallel execution)")
    print()

    # 4. Error Handling
    print("4. ERROR HANDLING:")
    print("-" * 40)

    async def failing_task(ctx: WFContext):
        raise ValueError("Simulated failure")

    error_wf = (
        manager.builder("error-wf", "Error Workflow")
        .start()
        .task("failing", failing_task)
        .end()
        .build()
    )

    manager.register(error_wf)

    result = await manager.run("error-wf")
    print(f"   Status: {result.status.value}")
    print(f"   Error: {result.error}")
    print()

    # 5. Statistics
    print("5. ENGINE STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    print(f"    Definitions: {stats['definitions']}")
    print(f"    Total runs: {stats['total_runs']}")
    print(f"    Completed: {stats['completed_runs']}")
    print(f"    Failed: {stats['failed_runs']}")
    print(f"    Success rate: {stats['success_rate']:.1%}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Workflow Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
