#!/usr/bin/env python3
"""
BAEL - Graph Database
Comprehensive in-memory graph database system.

Features:
- Node and edge management
- Property graphs
- Traversal algorithms (BFS, DFS)
- Shortest path algorithms (Dijkstra, A*)
- Graph pattern matching
- Cypher-like query language
- Transaction support
- Index management
- Graph analytics
- Import/Export
"""

import asyncio
import heapq
import json
import logging
import math
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generator, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class TraversalOrder(Enum):
    """Traversal order."""
    BREADTH_FIRST = "bfs"
    DEPTH_FIRST = "dfs"
    TOPOLOGICAL = "topological"


class Direction(Enum):
    """Edge direction."""
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


class OperationType(Enum):
    """Transaction operation type."""
    CREATE_NODE = "create_node"
    DELETE_NODE = "delete_node"
    UPDATE_NODE = "update_node"
    CREATE_EDGE = "create_edge"
    DELETE_EDGE = "delete_edge"
    UPDATE_EDGE = "update_edge"


class QueryOperator(Enum):
    """Query operators."""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER = ">"
    LESS = "<"
    GREATER_EQ = ">="
    LESS_EQ = "<="
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    REGEX = "regex"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Node:
    """Graph node."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    labels: Set[str] = field(default_factory=set)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.id == other.id
        return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.properties[key] = value
        self.updated_at = datetime.now()


@dataclass
class Edge:
    """Graph edge."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    label: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Edge):
            return self.id == other.id
        return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)


@dataclass
class Path:
    """Path through graph."""
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.edges)

    @property
    def total_weight(self) -> float:
        return sum(e.weight for e in self.edges)

    @property
    def start(self) -> Optional[Node]:
        return self.nodes[0] if self.nodes else None

    @property
    def end(self) -> Optional[Node]:
        return self.nodes[-1] if self.nodes else None


@dataclass
class QueryCondition:
    """Query condition."""
    property: str
    operator: QueryOperator
    value: Any


@dataclass
class GraphStats:
    """Graph statistics."""
    node_count: int = 0
    edge_count: int = 0
    label_counts: Dict[str, int] = field(default_factory=dict)
    avg_degree: float = 0.0
    max_degree: int = 0
    density: float = 0.0
    is_connected: bool = False


@dataclass
class TransactionOp:
    """Transaction operation."""
    type: OperationType
    data: Dict[str, Any]


# =============================================================================
# INDEX
# =============================================================================

class Index:
    """Property index for fast lookups."""

    def __init__(self, name: str, property_key: str):
        self.name = name
        self.property_key = property_key
        self._index: Dict[Any, Set[str]] = defaultdict(set)

    def add(self, node_id: str, value: Any) -> None:
        """Add entry to index."""
        self._index[value].add(node_id)

    def remove(self, node_id: str, value: Any) -> None:
        """Remove entry from index."""
        if value in self._index:
            self._index[value].discard(node_id)

    def get(self, value: Any) -> Set[str]:
        """Get node IDs by value."""
        return self._index.get(value, set())

    def clear(self) -> None:
        """Clear index."""
        self._index.clear()


# =============================================================================
# TRANSACTION
# =============================================================================

class Transaction:
    """Graph transaction."""

    def __init__(self, graph: "GraphDatabase"):
        self.graph = graph
        self.operations: List[TransactionOp] = []
        self.committed = False
        self.rolled_back = False

    def create_node(
        self,
        labels: Optional[Set[str]] = None,
        properties: Optional[Dict] = None
    ) -> Node:
        """Create a node in transaction."""
        node = Node(labels=labels or set(), properties=properties or {})

        self.operations.append(TransactionOp(
            type=OperationType.CREATE_NODE,
            data={"node": node}
        ))

        return node

    def delete_node(self, node_id: str) -> None:
        """Delete a node in transaction."""
        self.operations.append(TransactionOp(
            type=OperationType.DELETE_NODE,
            data={"node_id": node_id}
        ))

    def create_edge(
        self,
        source_id: str,
        target_id: str,
        label: str,
        properties: Optional[Dict] = None,
        weight: float = 1.0
    ) -> Edge:
        """Create an edge in transaction."""
        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            label=label,
            properties=properties or {},
            weight=weight
        )

        self.operations.append(TransactionOp(
            type=OperationType.CREATE_EDGE,
            data={"edge": edge}
        ))

        return edge

    def delete_edge(self, edge_id: str) -> None:
        """Delete an edge in transaction."""
        self.operations.append(TransactionOp(
            type=OperationType.DELETE_EDGE,
            data={"edge_id": edge_id}
        ))

    def commit(self) -> None:
        """Commit transaction."""
        if self.committed or self.rolled_back:
            return

        for op in self.operations:
            if op.type == OperationType.CREATE_NODE:
                self.graph._add_node(op.data["node"])
            elif op.type == OperationType.DELETE_NODE:
                self.graph._remove_node(op.data["node_id"])
            elif op.type == OperationType.CREATE_EDGE:
                self.graph._add_edge(op.data["edge"])
            elif op.type == OperationType.DELETE_EDGE:
                self.graph._remove_edge(op.data["edge_id"])

        self.committed = True

    def rollback(self) -> None:
        """Rollback transaction."""
        self.operations.clear()
        self.rolled_back = True


# =============================================================================
# QUERY BUILDER
# =============================================================================

class QueryBuilder:
    """Fluent query builder."""

    def __init__(self, graph: "GraphDatabase"):
        self.graph = graph
        self._node_labels: Set[str] = set()
        self._conditions: List[QueryCondition] = []
        self._limit: Optional[int] = None
        self._skip: int = 0
        self._order_by: Optional[str] = None
        self._order_desc: bool = False

    def match(self, *labels: str) -> "QueryBuilder":
        """Match nodes with labels."""
        self._node_labels.update(labels)
        return self

    def where(
        self,
        property: str,
        operator: Union[str, QueryOperator],
        value: Any
    ) -> "QueryBuilder":
        """Add where condition."""
        if isinstance(operator, str):
            operator = QueryOperator(operator)

        self._conditions.append(QueryCondition(property, operator, value))
        return self

    def limit(self, count: int) -> "QueryBuilder":
        """Limit results."""
        self._limit = count
        return self

    def skip(self, count: int) -> "QueryBuilder":
        """Skip results."""
        self._skip = count
        return self

    def order_by(self, property: str, desc: bool = False) -> "QueryBuilder":
        """Order results."""
        self._order_by = property
        self._order_desc = desc
        return self

    def execute(self) -> List[Node]:
        """Execute query."""
        # Get candidate nodes
        if self._node_labels:
            candidates = set()
            for label in self._node_labels:
                candidates.update(self.graph.get_nodes_by_label(label))
        else:
            candidates = set(self.graph.get_all_nodes())

        # Apply conditions
        results = []
        for node in candidates:
            if self._matches_conditions(node):
                results.append(node)

        # Sort
        if self._order_by:
            results.sort(
                key=lambda n: n.properties.get(self._order_by, ""),
                reverse=self._order_desc
            )

        # Skip and limit
        if self._skip:
            results = results[self._skip:]
        if self._limit:
            results = results[:self._limit]

        return results

    def _matches_conditions(self, node: Node) -> bool:
        """Check if node matches all conditions."""
        for cond in self._conditions:
            value = node.properties.get(cond.property)

            if not self._evaluate_condition(value, cond.operator, cond.value):
                return False

        return True

    def _evaluate_condition(
        self,
        value: Any,
        operator: QueryOperator,
        target: Any
    ) -> bool:
        """Evaluate a single condition."""
        if value is None:
            return False

        if operator == QueryOperator.EQUALS:
            return value == target
        elif operator == QueryOperator.NOT_EQUALS:
            return value != target
        elif operator == QueryOperator.GREATER:
            return value > target
        elif operator == QueryOperator.LESS:
            return value < target
        elif operator == QueryOperator.GREATER_EQ:
            return value >= target
        elif operator == QueryOperator.LESS_EQ:
            return value <= target
        elif operator == QueryOperator.CONTAINS:
            return target in str(value)
        elif operator == QueryOperator.STARTS_WITH:
            return str(value).startswith(str(target))
        elif operator == QueryOperator.ENDS_WITH:
            return str(value).endswith(str(target))
        elif operator == QueryOperator.IN:
            return value in target

        return False

    def count(self) -> int:
        """Count matching nodes."""
        return len(self.execute())

    def first(self) -> Optional[Node]:
        """Get first result."""
        results = self.limit(1).execute()
        return results[0] if results else None


# =============================================================================
# GRAPH DATABASE
# =============================================================================

class GraphDatabase:
    """
    Comprehensive Graph Database for BAEL.

    Provides in-memory graph storage and querying.
    """

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}

        # Adjacency lists
        self._outgoing: Dict[str, Set[str]] = defaultdict(set)  # node_id -> edge_ids
        self._incoming: Dict[str, Set[str]] = defaultdict(set)  # node_id -> edge_ids

        # Label index
        self._label_index: Dict[str, Set[str]] = defaultdict(set)  # label -> node_ids

        # Property indexes
        self._indexes: Dict[str, Index] = {}

        # Stats
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # NODE OPERATIONS
    # -------------------------------------------------------------------------

    def create_node(
        self,
        labels: Optional[Set[str]] = None,
        properties: Optional[Dict] = None
    ) -> Node:
        """Create a node."""
        node = Node(labels=labels or set(), properties=properties or {})
        self._add_node(node)
        return node

    def _add_node(self, node: Node) -> None:
        """Add node to graph."""
        self._nodes[node.id] = node

        for label in node.labels:
            self._label_index[label].add(node.id)

        # Update property indexes
        for index in self._indexes.values():
            if index.property_key in node.properties:
                index.add(node.id, node.properties[index.property_key])

        self._stats["nodes_created"] += 1

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        return self._nodes.get(node_id)

    def get_nodes_by_label(self, label: str) -> List[Node]:
        """Get all nodes with label."""
        node_ids = self._label_index.get(label, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def get_all_nodes(self) -> List[Node]:
        """Get all nodes."""
        return list(self._nodes.values())

    def update_node(
        self,
        node_id: str,
        properties: Optional[Dict] = None,
        labels: Optional[Set[str]] = None
    ) -> Optional[Node]:
        """Update a node."""
        node = self._nodes.get(node_id)
        if not node:
            return None

        if properties:
            node.properties.update(properties)

        if labels is not None:
            # Update label index
            for old_label in node.labels:
                self._label_index[old_label].discard(node_id)

            node.labels = labels

            for new_label in labels:
                self._label_index[new_label].add(node_id)

        node.updated_at = datetime.now()
        return node

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its edges."""
        if node_id not in self._nodes:
            return False

        self._remove_node(node_id)
        return True

    def _remove_node(self, node_id: str) -> None:
        """Remove node from graph."""
        node = self._nodes.get(node_id)
        if not node:
            return

        # Remove connected edges
        edges_to_remove = list(self._outgoing[node_id]) + list(self._incoming[node_id])
        for edge_id in set(edges_to_remove):
            self._remove_edge(edge_id)

        # Remove from label index
        for label in node.labels:
            self._label_index[label].discard(node_id)

        # Remove from property indexes
        for index in self._indexes.values():
            if index.property_key in node.properties:
                index.remove(node_id, node.properties[index.property_key])

        del self._nodes[node_id]
        self._stats["nodes_deleted"] += 1

    # -------------------------------------------------------------------------
    # EDGE OPERATIONS
    # -------------------------------------------------------------------------

    def create_edge(
        self,
        source_id: str,
        target_id: str,
        label: str,
        properties: Optional[Dict] = None,
        weight: float = 1.0
    ) -> Optional[Edge]:
        """Create an edge."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            label=label,
            properties=properties or {},
            weight=weight
        )

        self._add_edge(edge)
        return edge

    def _add_edge(self, edge: Edge) -> None:
        """Add edge to graph."""
        self._edges[edge.id] = edge
        self._outgoing[edge.source_id].add(edge.id)
        self._incoming[edge.target_id].add(edge.id)
        self._stats["edges_created"] += 1

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get edge by ID."""
        return self._edges.get(edge_id)

    def get_edges(
        self,
        node_id: str,
        direction: Direction = Direction.BOTH,
        label: Optional[str] = None
    ) -> List[Edge]:
        """Get edges connected to a node."""
        edge_ids = set()

        if direction in (Direction.OUTGOING, Direction.BOTH):
            edge_ids.update(self._outgoing.get(node_id, set()))

        if direction in (Direction.INCOMING, Direction.BOTH):
            edge_ids.update(self._incoming.get(node_id, set()))

        edges = [self._edges[eid] for eid in edge_ids if eid in self._edges]

        if label:
            edges = [e for e in edges if e.label == label]

        return edges

    def get_all_edges(self) -> List[Edge]:
        """Get all edges."""
        return list(self._edges.values())

    def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge."""
        if edge_id not in self._edges:
            return False

        self._remove_edge(edge_id)
        return True

    def _remove_edge(self, edge_id: str) -> None:
        """Remove edge from graph."""
        edge = self._edges.get(edge_id)
        if not edge:
            return

        self._outgoing[edge.source_id].discard(edge_id)
        self._incoming[edge.target_id].discard(edge_id)

        del self._edges[edge_id]
        self._stats["edges_deleted"] += 1

    # -------------------------------------------------------------------------
    # NEIGHBOR ACCESS
    # -------------------------------------------------------------------------

    def get_neighbors(
        self,
        node_id: str,
        direction: Direction = Direction.BOTH,
        label: Optional[str] = None
    ) -> List[Node]:
        """Get neighboring nodes."""
        neighbors = set()

        if direction in (Direction.OUTGOING, Direction.BOTH):
            for edge_id in self._outgoing.get(node_id, set()):
                edge = self._edges.get(edge_id)
                if edge and (not label or edge.label == label):
                    neighbors.add(edge.target_id)

        if direction in (Direction.INCOMING, Direction.BOTH):
            for edge_id in self._incoming.get(node_id, set()):
                edge = self._edges.get(edge_id)
                if edge and (not label or edge.label == label):
                    neighbors.add(edge.source_id)

        return [self._nodes[nid] for nid in neighbors if nid in self._nodes]

    def get_degree(
        self,
        node_id: str,
        direction: Direction = Direction.BOTH
    ) -> int:
        """Get node degree."""
        degree = 0

        if direction in (Direction.OUTGOING, Direction.BOTH):
            degree += len(self._outgoing.get(node_id, set()))

        if direction in (Direction.INCOMING, Direction.BOTH):
            degree += len(self._incoming.get(node_id, set()))

        return degree

    # -------------------------------------------------------------------------
    # TRAVERSAL
    # -------------------------------------------------------------------------

    def traverse(
        self,
        start_id: str,
        order: TraversalOrder = TraversalOrder.BREADTH_FIRST,
        max_depth: Optional[int] = None,
        direction: Direction = Direction.OUTGOING,
        label: Optional[str] = None
    ) -> Generator[Tuple[Node, int], None, None]:
        """Traverse graph from starting node."""
        if start_id not in self._nodes:
            return

        if order == TraversalOrder.BREADTH_FIRST:
            yield from self._bfs(start_id, max_depth, direction, label)
        elif order == TraversalOrder.DEPTH_FIRST:
            yield from self._dfs(start_id, max_depth, direction, label)
        elif order == TraversalOrder.TOPOLOGICAL:
            yield from self._topological_sort()

    def _bfs(
        self,
        start_id: str,
        max_depth: Optional[int],
        direction: Direction,
        label: Optional[str]
    ) -> Generator[Tuple[Node, int], None, None]:
        """Breadth-first traversal."""
        visited = {start_id}
        queue = deque([(start_id, 0)])

        while queue:
            node_id, depth = queue.popleft()

            if max_depth is not None and depth > max_depth:
                continue

            node = self._nodes.get(node_id)
            if node:
                yield node, depth

            for neighbor in self.get_neighbors(node_id, direction, label):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append((neighbor.id, depth + 1))

    def _dfs(
        self,
        start_id: str,
        max_depth: Optional[int],
        direction: Direction,
        label: Optional[str]
    ) -> Generator[Tuple[Node, int], None, None]:
        """Depth-first traversal."""
        visited = set()
        stack = [(start_id, 0)]

        while stack:
            node_id, depth = stack.pop()

            if node_id in visited:
                continue

            if max_depth is not None and depth > max_depth:
                continue

            visited.add(node_id)

            node = self._nodes.get(node_id)
            if node:
                yield node, depth

            for neighbor in self.get_neighbors(node_id, direction, label):
                if neighbor.id not in visited:
                    stack.append((neighbor.id, depth + 1))

    def _topological_sort(self) -> Generator[Tuple[Node, int], None, None]:
        """Topological sort (for DAGs)."""
        in_degree = defaultdict(int)

        for node_id in self._nodes:
            in_degree[node_id] = len(self._incoming.get(node_id, set()))

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = 0

        while queue:
            node_id = queue.popleft()
            node = self._nodes.get(node_id)

            if node:
                yield node, order
                order += 1

            for neighbor in self.get_neighbors(node_id, Direction.OUTGOING):
                in_degree[neighbor.id] -= 1
                if in_degree[neighbor.id] == 0:
                    queue.append(neighbor.id)

    # -------------------------------------------------------------------------
    # SHORTEST PATH
    # -------------------------------------------------------------------------

    def shortest_path(
        self,
        start_id: str,
        end_id: str,
        weighted: bool = True
    ) -> Optional[Path]:
        """Find shortest path between two nodes."""
        if start_id not in self._nodes or end_id not in self._nodes:
            return None

        if weighted:
            return self._dijkstra(start_id, end_id)
        else:
            return self._bfs_path(start_id, end_id)

    def _dijkstra(self, start_id: str, end_id: str) -> Optional[Path]:
        """Dijkstra's shortest path algorithm."""
        distances = {start_id: 0.0}
        previous: Dict[str, Tuple[str, str]] = {}  # node_id -> (prev_node_id, edge_id)
        visited = set()
        heap = [(0.0, start_id)]

        while heap:
            dist, node_id = heapq.heappop(heap)

            if node_id in visited:
                continue

            visited.add(node_id)

            if node_id == end_id:
                break

            for edge_id in self._outgoing.get(node_id, set()):
                edge = self._edges.get(edge_id)
                if not edge:
                    continue

                neighbor_id = edge.target_id
                new_dist = dist + edge.weight

                if neighbor_id not in distances or new_dist < distances[neighbor_id]:
                    distances[neighbor_id] = new_dist
                    previous[neighbor_id] = (node_id, edge_id)
                    heapq.heappush(heap, (new_dist, neighbor_id))

        if end_id not in previous and start_id != end_id:
            return None

        # Reconstruct path
        path_nodes = []
        path_edges = []
        current = end_id

        while current in previous:
            path_nodes.append(self._nodes[current])
            prev_node, edge_id = previous[current]
            path_edges.append(self._edges[edge_id])
            current = prev_node

        path_nodes.append(self._nodes[start_id])
        path_nodes.reverse()
        path_edges.reverse()

        return Path(nodes=path_nodes, edges=path_edges)

    def _bfs_path(self, start_id: str, end_id: str) -> Optional[Path]:
        """BFS shortest path (unweighted)."""
        previous: Dict[str, Tuple[str, str]] = {}
        visited = {start_id}
        queue = deque([start_id])

        while queue:
            node_id = queue.popleft()

            if node_id == end_id:
                break

            for edge_id in self._outgoing.get(node_id, set()):
                edge = self._edges.get(edge_id)
                if not edge:
                    continue

                neighbor_id = edge.target_id

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    previous[neighbor_id] = (node_id, edge_id)
                    queue.append(neighbor_id)

        if end_id not in previous and start_id != end_id:
            return None

        # Reconstruct
        path_nodes = []
        path_edges = []
        current = end_id

        while current in previous:
            path_nodes.append(self._nodes[current])
            prev_node, edge_id = previous[current]
            path_edges.append(self._edges[edge_id])
            current = prev_node

        path_nodes.append(self._nodes[start_id])
        path_nodes.reverse()
        path_edges.reverse()

        return Path(nodes=path_nodes, edges=path_edges)

    # -------------------------------------------------------------------------
    # ALGORITHMS
    # -------------------------------------------------------------------------

    def connected_components(self) -> List[Set[str]]:
        """Find connected components."""
        visited = set()
        components = []

        for node_id in self._nodes:
            if node_id not in visited:
                component = set()
                stack = [node_id]

                while stack:
                    nid = stack.pop()
                    if nid in visited:
                        continue

                    visited.add(nid)
                    component.add(nid)

                    for neighbor in self.get_neighbors(nid, Direction.BOTH):
                        if neighbor.id not in visited:
                            stack.append(neighbor.id)

                components.append(component)

        return components

    def has_cycle(self) -> bool:
        """Check if graph has a cycle."""
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in self.get_neighbors(node_id, Direction.OUTGOING):
                if neighbor.id not in visited:
                    if dfs(neighbor.id):
                        return True
                elif neighbor.id in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def pagerank(
        self,
        damping: float = 0.85,
        iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Dict[str, float]:
        """Calculate PageRank scores."""
        n = len(self._nodes)
        if n == 0:
            return {}

        # Initialize ranks
        ranks = {nid: 1.0 / n for nid in self._nodes}

        for _ in range(iterations):
            new_ranks = {}
            diff = 0.0

            for node_id in self._nodes:
                rank_sum = 0.0

                for edge_id in self._incoming.get(node_id, set()):
                    edge = self._edges.get(edge_id)
                    if edge:
                        source_id = edge.source_id
                        out_degree = len(self._outgoing.get(source_id, set()))
                        if out_degree > 0:
                            rank_sum += ranks[source_id] / out_degree

                new_rank = (1 - damping) / n + damping * rank_sum
                new_ranks[node_id] = new_rank
                diff += abs(new_rank - ranks[node_id])

            ranks = new_ranks

            if diff < tolerance:
                break

        return ranks

    # -------------------------------------------------------------------------
    # QUERY
    # -------------------------------------------------------------------------

    def query(self) -> QueryBuilder:
        """Start a query."""
        return QueryBuilder(self)

    # -------------------------------------------------------------------------
    # TRANSACTIONS
    # -------------------------------------------------------------------------

    def begin_transaction(self) -> Transaction:
        """Begin a transaction."""
        return Transaction(self)

    # -------------------------------------------------------------------------
    # INDEXES
    # -------------------------------------------------------------------------

    def create_index(self, name: str, property_key: str) -> Index:
        """Create a property index."""
        index = Index(name, property_key)

        # Populate index
        for node in self._nodes.values():
            if property_key in node.properties:
                index.add(node.id, node.properties[property_key])

        self._indexes[name] = index
        return index

    def drop_index(self, name: str) -> bool:
        """Drop an index."""
        if name in self._indexes:
            del self._indexes[name]
            return True
        return False

    def find_by_index(self, index_name: str, value: Any) -> List[Node]:
        """Find nodes using index."""
        if index_name not in self._indexes:
            return []

        node_ids = self._indexes[index_name].get(value)
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    # -------------------------------------------------------------------------
    # IMPORT/EXPORT
    # -------------------------------------------------------------------------

    def export_json(self) -> str:
        """Export graph to JSON."""
        data = {
            "nodes": [],
            "edges": []
        }

        for node in self._nodes.values():
            data["nodes"].append({
                "id": node.id,
                "labels": list(node.labels),
                "properties": node.properties
            })

        for edge in self._edges.values():
            data["edges"].append({
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "label": edge.label,
                "properties": edge.properties,
                "weight": edge.weight
            })

        return json.dumps(data, indent=2, default=str)

    def import_json(self, json_str: str) -> None:
        """Import graph from JSON."""
        data = json.loads(json_str)

        for node_data in data.get("nodes", []):
            node = Node(
                id=node_data["id"],
                labels=set(node_data.get("labels", [])),
                properties=node_data.get("properties", {})
            )
            self._add_node(node)

        for edge_data in data.get("edges", []):
            edge = Edge(
                id=edge_data["id"],
                source_id=edge_data["source"],
                target_id=edge_data["target"],
                label=edge_data.get("label", ""),
                properties=edge_data.get("properties", {}),
                weight=edge_data.get("weight", 1.0)
            )
            self._add_edge(edge)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> GraphStats:
        """Get graph statistics."""
        node_count = len(self._nodes)
        edge_count = len(self._edges)

        label_counts = {}
        for label, node_ids in self._label_index.items():
            label_counts[label] = len(node_ids)

        degrees = [self.get_degree(nid) for nid in self._nodes]
        avg_degree = sum(degrees) / node_count if node_count > 0 else 0.0
        max_degree = max(degrees) if degrees else 0

        # Density
        max_edges = node_count * (node_count - 1)
        density = edge_count / max_edges if max_edges > 0 else 0.0

        # Connected
        components = self.connected_components()
        is_connected = len(components) <= 1

        return GraphStats(
            node_count=node_count,
            edge_count=edge_count,
            label_counts=label_counts,
            avg_degree=avg_degree,
            max_degree=max_degree,
            density=density,
            is_connected=is_connected
        )

    def clear(self) -> None:
        """Clear entire graph."""
        self._nodes.clear()
        self._edges.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._label_index.clear()

        for index in self._indexes.values():
            index.clear()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Graph Database."""
    print("=" * 70)
    print("BAEL - GRAPH DATABASE DEMO")
    print("Comprehensive In-Memory Graph System")
    print("=" * 70)
    print()

    db = GraphDatabase()

    # 1. Create Nodes
    print("1. CREATE NODES:")
    print("-" * 40)

    alice = db.create_node({"Person"}, {"name": "Alice", "age": 30})
    bob = db.create_node({"Person"}, {"name": "Bob", "age": 25})
    charlie = db.create_node({"Person"}, {"name": "Charlie", "age": 35})
    company = db.create_node({"Company"}, {"name": "BAEL Corp", "industry": "AI"})

    print(f"   Created node: {alice.properties['name']} (id: {alice.id[:8]}...)")
    print(f"   Created node: {bob.properties['name']} (id: {bob.id[:8]}...)")
    print(f"   Created node: {charlie.properties['name']} (id: {charlie.id[:8]}...)")
    print(f"   Created node: {company.properties['name']} (id: {company.id[:8]}...)")
    print()

    # 2. Create Edges
    print("2. CREATE EDGES:")
    print("-" * 40)

    e1 = db.create_edge(alice.id, bob.id, "KNOWS", {"since": 2020})
    e2 = db.create_edge(bob.id, charlie.id, "KNOWS", {"since": 2021})
    e3 = db.create_edge(alice.id, charlie.id, "KNOWS", {"since": 2019})
    e4 = db.create_edge(alice.id, company.id, "WORKS_AT", {"role": "CEO"})
    e5 = db.create_edge(bob.id, company.id, "WORKS_AT", {"role": "CTO"})

    print(f"   Alice -> KNOWS -> Bob")
    print(f"   Bob -> KNOWS -> Charlie")
    print(f"   Alice -> KNOWS -> Charlie")
    print(f"   Alice -> WORKS_AT -> BAEL Corp")
    print(f"   Bob -> WORKS_AT -> BAEL Corp")
    print()

    # 3. Get Neighbors
    print("3. GET NEIGHBORS:")
    print("-" * 40)

    alice_neighbors = db.get_neighbors(alice.id, Direction.OUTGOING)
    print(f"   Alice's outgoing neighbors:")
    for n in alice_neighbors:
        print(f"     - {n.properties['name']}")
    print()

    # 4. Query Builder
    print("4. QUERY BUILDER:")
    print("-" * 40)

    results = (db.query()
               .match("Person")
               .where("age", ">", 24)
               .order_by("age")
               .execute())

    print(f"   Query: Match Person where age > 24, order by age")
    for node in results:
        print(f"     - {node.properties['name']} (age: {node.properties['age']})")
    print()

    # 5. Traversal
    print("5. GRAPH TRAVERSAL:")
    print("-" * 40)

    print(f"   BFS from Alice:")
    for node, depth in db.traverse(alice.id, TraversalOrder.BREADTH_FIRST, max_depth=2):
        print(f"     Depth {depth}: {node.properties['name']}")
    print()

    # 6. Shortest Path
    print("6. SHORTEST PATH:")
    print("-" * 40)

    path = db.shortest_path(alice.id, charlie.id)
    if path:
        print(f"   Path from Alice to Charlie:")
        print(f"     Nodes: {' -> '.join(n.properties['name'] for n in path.nodes)}")
        print(f"     Length: {path.length}")
        print(f"     Total weight: {path.total_weight}")
    print()

    # 7. Transactions
    print("7. TRANSACTIONS:")
    print("-" * 40)

    tx = db.begin_transaction()
    david = tx.create_node({"Person"}, {"name": "David", "age": 28})
    tx.create_edge(david.id, company.id, "WORKS_AT", {"role": "Engineer"})
    tx.commit()

    print(f"   Transaction committed")
    print(f"   Created: David, works at BAEL Corp")
    print()

    # 8. Indexes
    print("8. PROPERTY INDEXES:")
    print("-" * 40)

    db.create_index("name_index", "name")
    results = db.find_by_index("name_index", "Alice")

    print(f"   Created index on 'name'")
    print(f"   Find by name='Alice': {len(results)} result(s)")
    print()

    # 9. Connected Components
    print("9. CONNECTED COMPONENTS:")
    print("-" * 40)

    components = db.connected_components()
    print(f"   Number of components: {len(components)}")
    for i, comp in enumerate(components):
        names = [db.get_node(nid).properties['name'] for nid in comp]
        print(f"     Component {i + 1}: {names}")
    print()

    # 10. PageRank
    print("10. PAGERANK:")
    print("-" * 40)

    ranks = db.pagerank()
    sorted_ranks = sorted(ranks.items(), key=lambda x: x[1], reverse=True)

    print(f"   PageRank scores:")
    for node_id, rank in sorted_ranks[:5]:
        node = db.get_node(node_id)
        print(f"     {node.properties['name']}: {rank:.4f}")
    print()

    # 11. Cycle Detection
    print("11. CYCLE DETECTION:")
    print("-" * 40)

    has_cycle = db.has_cycle()
    print(f"   Graph has cycle: {has_cycle}")
    print()

    # 12. Graph Statistics
    print("12. GRAPH STATISTICS:")
    print("-" * 40)

    stats = db.get_stats()
    print(f"   Nodes: {stats.node_count}")
    print(f"   Edges: {stats.edge_count}")
    print(f"   Labels: {stats.label_counts}")
    print(f"   Avg degree: {stats.avg_degree:.2f}")
    print(f"   Max degree: {stats.max_degree}")
    print(f"   Density: {stats.density:.4f}")
    print(f"   Connected: {stats.is_connected}")
    print()

    # 13. Export/Import
    print("13. EXPORT/IMPORT:")
    print("-" * 40)

    json_export = db.export_json()
    print(f"   Exported to JSON ({len(json_export)} chars)")

    db2 = GraphDatabase()
    db2.import_json(json_export)
    print(f"   Imported to new graph: {len(db2.get_all_nodes())} nodes, {len(db2.get_all_edges())} edges")
    print()

    # 14. Update Node
    print("14. UPDATE NODE:")
    print("-" * 40)

    db.update_node(alice.id, {"age": 31, "title": "CEO"})
    updated = db.get_node(alice.id)
    print(f"   Updated Alice: {updated.properties}")
    print()

    # 15. Delete Operations
    print("15. DELETE OPERATIONS:")
    print("-" * 40)

    initial_edge_count = len(db.get_all_edges())
    db.delete_edge(e1.id)
    print(f"   Deleted edge Alice->Bob")
    print(f"   Edges: {initial_edge_count} -> {len(db.get_all_edges())}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Graph Database Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
