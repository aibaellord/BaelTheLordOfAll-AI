"""
BAEL Workflow Node
===================

Individual task nodes in workflow DAG.
Encapsulates task logic and metadata.

Features:
- Multiple node types
- Input/output handling
- Execution context
- Status tracking
- Dependency management
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of workflow nodes."""
    TASK = "task"  # Regular task
    PARALLEL = "parallel"  # Parallel execution group
    CONDITIONAL = "conditional"  # Conditional branch
    LOOP = "loop"  # Loop/iteration
    SUBWORKFLOW = "subworkflow"  # Nested workflow
    JOIN = "join"  # Synchronization point
    TRIGGER = "trigger"  # External trigger
    TRANSFORM = "transform"  # Data transformation
    VALIDATION = "validation"  # Validation step


class NodeStatus(Enum):
    """Node execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class NodeContext:
    """Execution context for a node."""
    # Inputs from upstream nodes
    inputs: Dict[str, Any] = field(default_factory=dict)

    # Global workflow variables
    variables: Dict[str, Any] = field(default_factory=dict)

    # Node-specific config
    config: Dict[str, Any] = field(default_factory=dict)

    # Execution metadata
    execution_id: str = ""
    attempt: int = 1
    start_time: Optional[datetime] = None

    def get_input(self, key: str, default: Any = None) -> Any:
        """Get an input value."""
        return self.inputs.get(key, default)

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable."""
        return self.variables.get(key, default)


@dataclass
class NodeResult:
    """Result of node execution."""
    node_id: str
    status: NodeStatus

    # Output data
    output: Any = None
    error: Optional[str] = None

    # Execution metrics
    execution_time_ms: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Retry info
    attempts: int = 1

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowNode:
    """
    A node in the workflow DAG.
    """
    id: str
    name: str
    node_type: NodeType = NodeType.TASK

    # Handler
    handler: Optional[Callable] = None

    # Dependencies
    upstream: Set[str] = field(default_factory=set)
    downstream: Set[str] = field(default_factory=set)

    # Input/Output mapping
    input_mapping: Dict[str, str] = field(default_factory=dict)  # {local: upstream.output}
    output_key: str = "output"

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 300.0
    retry_count: int = 3

    # Conditional
    condition: Optional[Callable[[NodeContext], bool]] = None

    # Status
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[NodeResult] = None

    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_upstream(self, node_id: str) -> None:
        """Add an upstream dependency."""
        self.upstream.add(node_id)

    def add_downstream(self, node_id: str) -> None:
        """Add a downstream node."""
        self.downstream.add(node_id)

    def is_ready(self, completed_nodes: Set[str]) -> bool:
        """Check if node is ready to execute."""
        return all(dep in completed_nodes for dep in self.upstream)

    async def execute(self, context: NodeContext) -> NodeResult:
        """
        Execute the node.

        Args:
            context: Execution context

        Returns:
            Execution result
        """
        start_time = datetime.now()

        result = NodeResult(
            node_id=self.id,
            status=NodeStatus.RUNNING,
            start_time=start_time,
            attempts=context.attempt,
        )

        try:
            self.status = NodeStatus.RUNNING

            # Check condition
            if self.condition and not self.condition(context):
                self.status = NodeStatus.SKIPPED
                result.status = NodeStatus.SKIPPED
                return result

            # Execute handler
            if self.handler:
                if asyncio.iscoroutinefunction(self.handler):
                    output = await asyncio.wait_for(
                        self.handler(context),
                        timeout=self.timeout_seconds,
                    )
                else:
                    # Run sync handler in executor
                    loop = asyncio.get_event_loop()
                    output = await loop.run_in_executor(
                        None,
                        lambda: self.handler(context),
                    )
            else:
                # Passthrough node
                output = context.inputs

            result.output = output
            result.status = NodeStatus.COMPLETED
            self.status = NodeStatus.COMPLETED

        except asyncio.TimeoutError:
            result.status = NodeStatus.FAILED
            result.error = f"Timeout after {self.timeout_seconds}s"
            self.status = NodeStatus.FAILED

        except Exception as e:
            result.status = NodeStatus.FAILED
            result.error = str(e)
            self.status = NodeStatus.FAILED
            logger.error(f"Node {self.id} failed: {e}")

        result.end_time = datetime.now()
        result.execution_time_ms = (
            result.end_time - start_time
        ).total_seconds() * 1000

        self.result = result

        return result

    def reset(self) -> None:
        """Reset node for re-execution."""
        self.status = NodeStatus.PENDING
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type.value,
            "status": self.status.value,
            "upstream": list(self.upstream),
            "downstream": list(self.downstream),
            "description": self.description,
            "tags": self.tags,
        }


class NodeFactory:
    """Factory for creating workflow nodes."""

    @staticmethod
    def create_task(
        name: str,
        handler: Callable,
        description: str = "",
        **kwargs,
    ) -> WorkflowNode:
        """Create a task node."""
        node_id = hashlib.md5(f"{name}:{datetime.now()}".encode()).hexdigest()[:12]

        return WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.TASK,
            handler=handler,
            description=description,
            **kwargs,
        )

    @staticmethod
    def create_parallel(
        name: str,
        tasks: List[Callable],
        **kwargs,
    ) -> WorkflowNode:
        """Create a parallel execution node."""
        async def parallel_handler(context: NodeContext) -> Dict[str, Any]:
            tasks_coro = []
            for i, task in enumerate(tasks):
                if asyncio.iscoroutinefunction(task):
                    tasks_coro.append(task(context))
                else:
                    loop = asyncio.get_event_loop()
                    tasks_coro.append(loop.run_in_executor(None, lambda t=task: t(context)))

            results = await asyncio.gather(*tasks_coro, return_exceptions=True)

            return {f"task_{i}": r for i, r in enumerate(results)}

        node_id = hashlib.md5(f"{name}:parallel:{datetime.now()}".encode()).hexdigest()[:12]

        return WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.PARALLEL,
            handler=parallel_handler,
            **kwargs,
        )

    @staticmethod
    def create_conditional(
        name: str,
        condition: Callable[[NodeContext], bool],
        true_handler: Callable,
        false_handler: Optional[Callable] = None,
        **kwargs,
    ) -> WorkflowNode:
        """Create a conditional node."""
        async def conditional_handler(context: NodeContext) -> Any:
            if condition(context):
                handler = true_handler
            else:
                handler = false_handler

            if handler is None:
                return None

            if asyncio.iscoroutinefunction(handler):
                return await handler(context)
            else:
                return handler(context)

        node_id = hashlib.md5(f"{name}:conditional:{datetime.now()}".encode()).hexdigest()[:12]

        return WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.CONDITIONAL,
            handler=conditional_handler,
            **kwargs,
        )

    @staticmethod
    def create_loop(
        name: str,
        iterator_key: str,
        body_handler: Callable,
        **kwargs,
    ) -> WorkflowNode:
        """Create a loop node."""
        async def loop_handler(context: NodeContext) -> List[Any]:
            items = context.get_input(iterator_key, [])
            results = []

            for item in items:
                loop_context = NodeContext(
                    inputs={"item": item, **context.inputs},
                    variables=context.variables,
                    config=context.config,
                )

                if asyncio.iscoroutinefunction(body_handler):
                    result = await body_handler(loop_context)
                else:
                    result = body_handler(loop_context)

                results.append(result)

            return results

        node_id = hashlib.md5(f"{name}:loop:{datetime.now()}".encode()).hexdigest()[:12]

        return WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.LOOP,
            handler=loop_handler,
            **kwargs,
        )

    @staticmethod
    def create_transform(
        name: str,
        transform_fn: Callable[[Any], Any],
        input_key: str = "input",
        **kwargs,
    ) -> WorkflowNode:
        """Create a data transformation node."""
        def transform_handler(context: NodeContext) -> Any:
            data = context.get_input(input_key)
            return transform_fn(data)

        node_id = hashlib.md5(f"{name}:transform:{datetime.now()}".encode()).hexdigest()[:12]

        return WorkflowNode(
            id=node_id,
            name=name,
            node_type=NodeType.TRANSFORM,
            handler=transform_handler,
            **kwargs,
        )


def demo():
    """Demonstrate workflow nodes."""
    import asyncio

    print("=" * 60)
    print("BAEL Workflow Node Demo")
    print("=" * 60)

    # Create nodes
    async def fetch_data(ctx: NodeContext) -> Dict[str, Any]:
        await asyncio.sleep(0.1)  # Simulate I/O
        return {"data": [1, 2, 3, 4, 5]}

    async def process_data(ctx: NodeContext) -> Dict[str, Any]:
        data = ctx.get_input("data", [])
        return {"processed": [x * 2 for x in data]}

    async def save_results(ctx: NodeContext) -> Dict[str, Any]:
        processed = ctx.get_input("processed", [])
        return {"saved": len(processed), "sum": sum(processed)}

    nodes = [
        NodeFactory.create_task("fetch", fetch_data, "Fetch data"),
        NodeFactory.create_task("process", process_data, "Process data"),
        NodeFactory.create_task("save", save_results, "Save results"),
    ]

    print(f"\nCreated {len(nodes)} nodes:")
    for node in nodes:
        print(f"  - {node.name} ({node.node_type.value})")

    # Execute nodes
    print("\nExecuting nodes...")

    async def run():
        # Node 1: Fetch
        ctx1 = NodeContext()
        result1 = await nodes[0].execute(ctx1)
        print(f"  Fetch: {result1.status.value} -> {result1.output}")

        # Node 2: Process (with input from fetch)
        ctx2 = NodeContext(inputs=result1.output)
        result2 = await nodes[1].execute(ctx2)
        print(f"  Process: {result2.status.value} -> {result2.output}")

        # Node 3: Save (with input from process)
        ctx3 = NodeContext(inputs=result2.output)
        result3 = await nodes[2].execute(ctx3)
        print(f"  Save: {result3.status.value} -> {result3.output}")

    asyncio.run(run())

    # Parallel node
    print("\nParallel execution:")

    def task_a(ctx): return {"a": "done"}
    def task_b(ctx): return {"b": "done"}
    def task_c(ctx): return {"c": "done"}

    parallel_node = NodeFactory.create_parallel(
        "parallel_tasks",
        [task_a, task_b, task_c],
    )

    async def run_parallel():
        ctx = NodeContext()
        result = await parallel_node.execute(ctx)
        print(f"  Parallel: {result.output}")

    asyncio.run(run_parallel())


if __name__ == "__main__":
    demo()
