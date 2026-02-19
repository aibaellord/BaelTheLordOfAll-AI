"""
BAEL Workflow DAG
==================

Directed Acyclic Graph for workflow structure.
Defines dependencies and execution order.

Features:
- DAG construction
- Validation
- Topological sorting
- Critical path analysis
- Visualization
"""

import hashlib
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .workflow_node import NodeStatus, NodeType, WorkflowNode

logger = logging.getLogger(__name__)


class EdgeType(Enum):
    """Types of edges in DAG."""
    DATA = "data"  # Data dependency
    CONTROL = "control"  # Control flow
    OPTIONAL = "optional"  # Optional dependency


@dataclass
class Edge:
    """An edge connecting two nodes."""
    source: str
    target: str
    edge_type: EdgeType = EdgeType.DATA

    # Data mapping
    output_key: str = "output"
    input_key: str = "input"

    # Metadata
    condition: Optional[Callable[[Any], bool]] = None
    weight: float = 1.0


@dataclass
class WorkflowDAG:
    """
    Directed Acyclic Graph for workflows.
    """
    id: str
    name: str

    # Nodes and edges
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)

    # Graph structure
    adjacency: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    reverse_adjacency: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    # Entry and exit points
    entry_nodes: Set[str] = field(default_factory=set)
    exit_nodes: Set[str] = field(default_factory=set)

    # Metadata
    description: str = ""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)

    def add_node(self, node: WorkflowNode) -> None:
        """Add a node to the DAG."""
        self.nodes[node.id] = node
        self._update_entry_exit()

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.DATA,
        output_key: str = "output",
        input_key: str = "input",
    ) -> Edge:
        """Add an edge between nodes."""
        edge = Edge(
            source=source_id,
            target=target_id,
            edge_type=edge_type,
            output_key=output_key,
            input_key=input_key,
        )

        self.edges.append(edge)

        # Update adjacency
        self.adjacency[source_id].add(target_id)
        self.reverse_adjacency[target_id].add(source_id)

        # Update node dependencies
        if source_id in self.nodes:
            self.nodes[source_id].add_downstream(target_id)
        if target_id in self.nodes:
            self.nodes[target_id].add_upstream(source_id)

        self._update_entry_exit()

        return edge

    def _update_entry_exit(self) -> None:
        """Update entry and exit nodes."""
        self.entry_nodes = set()
        self.exit_nodes = set()

        for node_id in self.nodes:
            # Entry: no upstream
            if not self.reverse_adjacency.get(node_id):
                self.entry_nodes.add(node_id)

            # Exit: no downstream
            if not self.adjacency.get(node_id):
                self.exit_nodes.add(node_id)

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_upstream(self, node_id: str) -> List[WorkflowNode]:
        """Get upstream nodes."""
        return [
            self.nodes[nid]
            for nid in self.reverse_adjacency.get(node_id, set())
            if nid in self.nodes
        ]

    def get_downstream(self, node_id: str) -> List[WorkflowNode]:
        """Get downstream nodes."""
        return [
            self.nodes[nid]
            for nid in self.adjacency.get(node_id, set())
            if nid in self.nodes
        ]

    def get_edges_from(self, node_id: str) -> List[Edge]:
        """Get edges from a node."""
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> List[Edge]:
        """Get edges to a node."""
        return [e for e in self.edges if e.target == node_id]

    def topological_sort(self) -> List[str]:
        """
        Topologically sort nodes.

        Returns:
            List of node IDs in execution order
        """
        # Kahn's algorithm
        in_degree = defaultdict(int)

        for node_id in self.nodes:
            in_degree[node_id] = len(self.reverse_adjacency.get(node_id, set()))

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            for downstream in self.adjacency.get(node_id, set()):
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    queue.append(downstream)

        if len(result) != len(self.nodes):
            raise ValueError("DAG contains a cycle")

        return result

    def get_execution_levels(self) -> List[List[str]]:
        """
        Get nodes grouped by execution level.
        Nodes at the same level can run in parallel.

        Returns:
            List of levels, each containing node IDs
        """
        levels = []
        remaining = set(self.nodes.keys())
        completed = set()

        while remaining:
            level = []

            for node_id in list(remaining):
                upstream = self.reverse_adjacency.get(node_id, set())
                if upstream.issubset(completed):
                    level.append(node_id)

            if not level:
                raise ValueError("DAG contains a cycle")

            levels.append(level)

            for node_id in level:
                remaining.remove(node_id)
                completed.add(node_id)

        return levels

    def get_critical_path(self) -> Tuple[List[str], float]:
        """
        Find the critical path (longest path through DAG).

        Returns:
            (path node IDs, total weight)
        """
        # Dynamic programming approach
        distances = {nid: 0.0 for nid in self.nodes}
        predecessors = {nid: None for nid in self.nodes}

        try:
            sorted_nodes = self.topological_sort()
        except ValueError:
            return [], 0.0

        for node_id in sorted_nodes:
            for edge in self.get_edges_from(node_id):
                new_dist = distances[node_id] + edge.weight
                if new_dist > distances[edge.target]:
                    distances[edge.target] = new_dist
                    predecessors[edge.target] = node_id

        # Find end node with maximum distance
        if not distances:
            return [], 0.0

        max_node = max(distances.items(), key=lambda x: x[1])
        end_node = max_node[0]
        total_weight = max_node[1]

        # Reconstruct path
        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = predecessors[current]

        path.reverse()

        return path, total_weight

    def validate(self) -> List[str]:
        """
        Validate the DAG.

        Returns:
            List of validation errors
        """
        errors = []

        # Check for empty DAG
        if not self.nodes:
            errors.append("DAG has no nodes")
            return errors

        # Check for cycles
        try:
            self.topological_sort()
        except ValueError:
            errors.append("DAG contains a cycle")

        # Check for orphan nodes
        all_node_ids = set(self.nodes.keys())
        edge_nodes = set()
        for edge in self.edges:
            edge_nodes.add(edge.source)
            edge_nodes.add(edge.target)

        orphans = all_node_ids - edge_nodes - self.entry_nodes
        if orphans and len(self.nodes) > 1:
            errors.append(f"Orphan nodes: {orphans}")

        # Check for missing nodes in edges
        for edge in self.edges:
            if edge.source not in self.nodes:
                errors.append(f"Edge source not found: {edge.source}")
            if edge.target not in self.nodes:
                errors.append(f"Edge target not found: {edge.target}")

        # Check for self-loops
        for edge in self.edges:
            if edge.source == edge.target:
                errors.append(f"Self-loop on node: {edge.source}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert DAG to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.edge_type.value,
                }
                for e in self.edges
            ],
            "entry_nodes": list(self.entry_nodes),
            "exit_nodes": list(self.exit_nodes),
        }

    def visualize(self) -> str:
        """Generate ASCII visualization."""
        lines = []
        lines.append(f"Workflow: {self.name}")
        lines.append("=" * 50)

        try:
            levels = self.get_execution_levels()
        except ValueError:
            lines.append("ERROR: Contains cycle")
            return "\n".join(lines)

        for i, level in enumerate(levels):
            lines.append(f"\nLevel {i}:")
            for node_id in level:
                node = self.nodes[node_id]
                status = node.status.value[:4].upper()
                lines.append(f"  [{status}] {node.name}")

                # Show outgoing edges
                for downstream in self.adjacency.get(node_id, set()):
                    down_node = self.nodes.get(downstream)
                    if down_node:
                        lines.append(f"       ↓ {down_node.name}")

        return "\n".join(lines)


class DAGValidator:
    """Validates workflow DAGs."""

    def __init__(self, dag: WorkflowDAG):
        self.dag = dag
        self.errors = []
        self.warnings = []

    def validate_all(self) -> bool:
        """Run all validations."""
        self.errors = []
        self.warnings = []

        self._validate_structure()
        self._validate_nodes()
        self._validate_edges()
        self._validate_data_flow()

        return len(self.errors) == 0

    def _validate_structure(self) -> None:
        """Validate DAG structure."""
        errors = self.dag.validate()
        self.errors.extend(errors)

    def _validate_nodes(self) -> None:
        """Validate individual nodes."""
        for node_id, node in self.dag.nodes.items():
            if not node.name:
                self.errors.append(f"Node {node_id} has no name")

            if node.node_type == NodeType.TASK and not node.handler:
                self.warnings.append(f"Task node {node_id} has no handler")

    def _validate_edges(self) -> None:
        """Validate edges."""
        for edge in self.dag.edges:
            if edge.source == edge.target:
                self.errors.append(f"Self-loop: {edge.source}")

    def _validate_data_flow(self) -> None:
        """Validate data flow."""
        # Check that required inputs are provided
        for node_id, node in self.dag.nodes.items():
            if node.input_mapping:
                for local_key, source_ref in node.input_mapping.items():
                    parts = source_ref.split('.')
                    if len(parts) >= 2:
                        source_node = parts[0]
                        if source_node not in self.dag.nodes:
                            self.errors.append(
                                f"Node {node_id}: Input {local_key} references unknown node {source_node}"
                            )

    def get_report(self) -> str:
        """Get validation report."""
        lines = ["Validation Report", "=" * 40]

        if not self.errors and not self.warnings:
            lines.append("✓ No issues found")

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  ✗ {err}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  ⚠ {warn}")

        return "\n".join(lines)


class DAGBuilder:
    """Builder for creating workflow DAGs."""

    def __init__(self, name: str):
        dag_id = hashlib.md5(f"{name}:{datetime.now()}".encode()).hexdigest()[:12]
        self.dag = WorkflowDAG(id=dag_id, name=name)
        self._last_node: Optional[str] = None

    def add_node(
        self,
        node: WorkflowNode,
        depends_on: Optional[List[str]] = None,
    ) -> "DAGBuilder":
        """Add a node."""
        self.dag.add_node(node)

        if depends_on:
            for dep in depends_on:
                self.dag.add_edge(dep, node.id)

        self._last_node = node.id

        return self

    def then(self, node: WorkflowNode) -> "DAGBuilder":
        """Add a node after the last one."""
        self.dag.add_node(node)

        if self._last_node:
            self.dag.add_edge(self._last_node, node.id)

        self._last_node = node.id

        return self

    def parallel(self, nodes: List[WorkflowNode]) -> "DAGBuilder":
        """Add parallel nodes."""
        for node in nodes:
            self.dag.add_node(node)

            if self._last_node:
                self.dag.add_edge(self._last_node, node.id)

        return self

    def join(self, sources: List[str], target: WorkflowNode) -> "DAGBuilder":
        """Join multiple nodes into one."""
        self.dag.add_node(target)

        for source in sources:
            self.dag.add_edge(source, target.id)

        self._last_node = target.id

        return self

    def build(self) -> WorkflowDAG:
        """Build the DAG."""
        return self.dag


def demo():
    """Demonstrate workflow DAG."""
    print("=" * 60)
    print("BAEL Workflow DAG Demo")
    print("=" * 60)

    from .workflow_node import NodeFactory

    # Build DAG
    builder = DAGBuilder("Data Pipeline")

    # Create nodes
    extract = NodeFactory.create_task("extract", lambda ctx: {"data": [1, 2, 3]})
    transform = NodeFactory.create_task("transform", lambda ctx: {"transformed": True})
    load = NodeFactory.create_task("load", lambda ctx: {"loaded": True})
    notify = NodeFactory.create_task("notify", lambda ctx: {"notified": True})

    # Build pipeline
    dag = (
        builder
        .add_node(extract)
        .then(transform)
        .then(load)
        .then(notify)
        .build()
    )

    print(f"\nDAG: {dag.name}")
    print(f"Nodes: {len(dag.nodes)}")
    print(f"Edges: {len(dag.edges)}")
    print(f"Entry: {dag.entry_nodes}")
    print(f"Exit: {dag.exit_nodes}")

    # Topological sort
    order = dag.topological_sort()
    print(f"\nExecution order:")
    for i, node_id in enumerate(order, 1):
        node = dag.get_node(node_id)
        print(f"  {i}. {node.name}")

    # Execution levels
    levels = dag.get_execution_levels()
    print(f"\nExecution levels:")
    for i, level in enumerate(levels):
        node_names = [dag.get_node(nid).name for nid in level]
        print(f"  Level {i}: {node_names}")

    # Critical path
    path, weight = dag.get_critical_path()
    path_names = [dag.get_node(nid).name for nid in path]
    print(f"\nCritical path: {' -> '.join(path_names)}")

    # Validation
    print("\nValidation:")
    validator = DAGValidator(dag)
    is_valid = validator.validate_all()
    print(f"  Valid: {is_valid}")
    print(validator.get_report())

    # Visualization
    print("\n" + dag.visualize())


if __name__ == "__main__":
    demo()
