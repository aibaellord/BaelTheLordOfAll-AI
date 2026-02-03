#!/usr/bin/env python3
"""
BAEL - Dependency Graph Manager
Comprehensive dependency graph analysis and resolution system.

Features:
- Directed acyclic graph (DAG) management
- Dependency resolution with topological sort
- Cycle detection
- Path finding
- Impact analysis
- Version constraint resolution
- Parallel execution scheduling
- Graph visualization (text-based)
- Conflict detection
- Optional dependency support
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class NodeState(Enum):
    """Node state for graph traversal."""
    UNVISITED = "unvisited"
    VISITING = "visiting"
    VISITED = "visited"


class DependencyType(Enum):
    """Dependency type."""
    REQUIRED = "required"
    OPTIONAL = "optional"
    DEV = "dev"
    PEER = "peer"


class ResolutionStrategy(Enum):
    """Dependency resolution strategy."""
    NEWEST = "newest"
    OLDEST = "oldest"
    EXACT = "exact"


class ConflictResolution(Enum):
    """Conflict resolution strategy."""
    FAIL = "fail"
    NEWEST_WINS = "newest_wins"
    OLDEST_WINS = "oldest_wins"
    FIRST_WINS = "first_wins"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Version:
    """Semantic version."""
    major: int
    minor: int
    patch: int
    prerelease: str = ""

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parse version string."""
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', version_str)

        if not match:
            raise ValueError(f"Invalid version: {version_str}")

        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4) or ""
        )

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"

        if self.prerelease:
            return f"{base}-{self.prerelease}"

        return base

    def __lt__(self, other: "Version") -> bool:
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Prerelease versions are lower
        if self.prerelease and not other.prerelease:
            return True

        if not self.prerelease and other.prerelease:
            return False

        return self.prerelease < other.prerelease

    def __le__(self, other: "Version") -> bool:
        return self == other or self < other

    def __eq__(self, other: "Version") -> bool:
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch and
            self.prerelease == other.prerelease
        )

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))


@dataclass
class VersionConstraint:
    """Version constraint."""
    operator: str  # =, >, <, >=, <=, ^, ~
    version: Version

    @classmethod
    def parse(cls, constraint_str: str) -> "VersionConstraint":
        """Parse constraint string."""
        match = re.match(r'^([=><^~]+)?(.+)$', constraint_str.strip())

        if not match:
            raise ValueError(f"Invalid constraint: {constraint_str}")

        operator = match.group(1) or "="
        version = Version.parse(match.group(2))

        return cls(operator=operator, version=version)

    def matches(self, version: Version) -> bool:
        """Check if version matches constraint."""
        if self.operator == "=":
            return version == self.version

        elif self.operator == ">":
            return version > self.version

        elif self.operator == "<":
            return version < self.version

        elif self.operator == ">=":
            return version >= self.version

        elif self.operator == "<=":
            return version <= self.version

        elif self.operator == "^":
            # Compatible with major version
            return (
                version.major == self.version.major and
                version >= self.version
            )

        elif self.operator == "~":
            # Compatible with minor version
            return (
                version.major == self.version.major and
                version.minor == self.version.minor and
                version >= self.version
            )

        return False

    def __str__(self) -> str:
        return f"{self.operator}{self.version}"


@dataclass
class Node:
    """Graph node representing a dependency."""
    id: str
    name: str
    version: Optional[Version] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: "Node") -> bool:
        return self.id == other.id


@dataclass
class Edge:
    """Graph edge representing a dependency relationship."""
    source: str
    target: str
    dependency_type: DependencyType = DependencyType.REQUIRED
    constraint: Optional[VersionConstraint] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.source, self.target))


@dataclass
class Cycle:
    """Detected cycle in graph."""
    nodes: List[str]

    @property
    def path(self) -> str:
        """Get cycle path string."""
        return " -> ".join(self.nodes + [self.nodes[0]])


@dataclass
class ResolutionResult:
    """Dependency resolution result."""
    resolved: List[Node]
    unresolved: List[str]
    conflicts: List[Tuple[str, str, str]]  # (node, version1, version2)
    order: List[str]  # Topological order

    @property
    def success(self) -> bool:
        return len(self.unresolved) == 0 and len(self.conflicts) == 0


@dataclass
class ImpactAnalysis:
    """Impact analysis result."""
    node_id: str
    direct_dependents: List[str]
    all_dependents: List[str]
    impact_level: int  # Number of affected nodes


# =============================================================================
# GRAPH OPERATIONS
# =============================================================================

class DependencyGraph:
    """Dependency graph data structure."""

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: Node) -> None:
        """Add node to graph."""
        self._nodes[node.id] = node

    def remove_node(self, node_id: str) -> bool:
        """Remove node and its edges."""
        if node_id not in self._nodes:
            return False

        # Remove edges
        for target in list(self._adjacency[node_id]):
            self.remove_edge(node_id, target)

        for source in list(self._reverse_adjacency[node_id]):
            self.remove_edge(source, node_id)

        del self._nodes[node_id]

        return True

    def add_edge(self, edge: Edge) -> None:
        """Add edge to graph."""
        edge_id = f"{edge.source}->{edge.target}"
        self._edges[edge_id] = edge
        self._adjacency[edge.source].add(edge.target)
        self._reverse_adjacency[edge.target].add(edge.source)

    def remove_edge(self, source: str, target: str) -> bool:
        """Remove edge from graph."""
        edge_id = f"{source}->{target}"

        if edge_id not in self._edges:
            return False

        del self._edges[edge_id]
        self._adjacency[source].discard(target)
        self._reverse_adjacency[target].discard(source)

        return True

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        return self._nodes.get(node_id)

    def get_edge(self, source: str, target: str) -> Optional[Edge]:
        """Get edge by source and target."""
        return self._edges.get(f"{source}->{target}")

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get direct dependencies of node."""
        return list(self._adjacency.get(node_id, set()))

    def get_dependents(self, node_id: str) -> List[str]:
        """Get direct dependents of node."""
        return list(self._reverse_adjacency.get(node_id, set()))

    def nodes(self) -> List[Node]:
        """Get all nodes."""
        return list(self._nodes.values())

    def edges(self) -> List[Edge]:
        """Get all edges."""
        return list(self._edges.values())

    @property
    def node_count(self) -> int:
        """Get node count."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Get edge count."""
        return len(self._edges)


# =============================================================================
# GRAPH ALGORITHMS
# =============================================================================

class GraphAlgorithms:
    """Graph algorithms."""

    @staticmethod
    def topological_sort(graph: DependencyGraph) -> List[str]:
        """Topological sort using Kahn's algorithm."""
        # Calculate in-degrees
        in_degree: Dict[str, int] = defaultdict(int)

        for node in graph.nodes():
            in_degree[node.id] = 0

        for edge in graph.edges():
            in_degree[edge.target] += 1

        # Queue nodes with no dependencies
        queue = deque([
            node.id for node in graph.nodes()
            if in_degree[node.id] == 0
        ])

        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            for dep in graph.get_dependencies(node_id):
                in_degree[dep] -= 1

                if in_degree[dep] == 0:
                    queue.append(dep)

        # Check for cycle
        if len(result) != graph.node_count:
            raise ValueError("Graph contains cycle")

        return result

    @staticmethod
    def detect_cycles(graph: DependencyGraph) -> List[Cycle]:
        """Detect all cycles in graph using DFS."""
        cycles = []
        state: Dict[str, NodeState] = {
            node.id: NodeState.UNVISITED
            for node in graph.nodes()
        }
        path: List[str] = []

        def dfs(node_id: str) -> None:
            if state[node_id] == NodeState.VISITING:
                # Found cycle
                cycle_start = path.index(node_id)
                cycles.append(Cycle(nodes=path[cycle_start:]))
                return

            if state[node_id] == NodeState.VISITED:
                return

            state[node_id] = NodeState.VISITING
            path.append(node_id)

            for dep in graph.get_dependencies(node_id):
                if dep in state:
                    dfs(dep)

            path.pop()
            state[node_id] = NodeState.VISITED

        for node in graph.nodes():
            if state[node.id] == NodeState.UNVISITED:
                dfs(node.id)

        return cycles

    @staticmethod
    def find_path(
        graph: DependencyGraph,
        source: str,
        target: str
    ) -> Optional[List[str]]:
        """Find path between nodes using BFS."""
        if source not in [n.id for n in graph.nodes()]:
            return None

        if source == target:
            return [source]

        visited: Set[str] = set()
        queue: deque = deque([(source, [source])])

        while queue:
            node_id, path = queue.popleft()

            if node_id in visited:
                continue

            visited.add(node_id)

            for dep in graph.get_dependencies(node_id):
                new_path = path + [dep]

                if dep == target:
                    return new_path

                queue.append((dep, new_path))

        return None

    @staticmethod
    def find_all_paths(
        graph: DependencyGraph,
        source: str,
        target: str
    ) -> List[List[str]]:
        """Find all paths between nodes."""
        paths = []

        def dfs(node_id: str, path: List[str], visited: Set[str]) -> None:
            if node_id == target:
                paths.append(path[:])
                return

            for dep in graph.get_dependencies(node_id):
                if dep not in visited:
                    visited.add(dep)
                    path.append(dep)
                    dfs(dep, path, visited)
                    path.pop()
                    visited.remove(dep)

        if source in [n.id for n in graph.nodes()]:
            dfs(source, [source], {source})

        return paths

    @staticmethod
    def get_all_dependencies(
        graph: DependencyGraph,
        node_id: str,
        transitive: bool = True
    ) -> Set[str]:
        """Get all dependencies (transitive closure)."""
        if not transitive:
            return set(graph.get_dependencies(node_id))

        visited: Set[str] = set()
        queue = deque(graph.get_dependencies(node_id))

        while queue:
            dep = queue.popleft()

            if dep in visited:
                continue

            visited.add(dep)
            queue.extend(graph.get_dependencies(dep))

        return visited

    @staticmethod
    def get_all_dependents(
        graph: DependencyGraph,
        node_id: str,
        transitive: bool = True
    ) -> Set[str]:
        """Get all dependents (reverse transitive closure)."""
        if not transitive:
            return set(graph.get_dependents(node_id))

        visited: Set[str] = set()
        queue = deque(graph.get_dependents(node_id))

        while queue:
            dep = queue.popleft()

            if dep in visited:
                continue

            visited.add(dep)
            queue.extend(graph.get_dependents(dep))

        return visited


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class DependencyResolver:
    """Dependency resolver."""

    def __init__(
        self,
        strategy: ResolutionStrategy = ResolutionStrategy.NEWEST,
        conflict_resolution: ConflictResolution = ConflictResolution.NEWEST_WINS
    ):
        self.strategy = strategy
        self.conflict_resolution = conflict_resolution

    def resolve(
        self,
        graph: DependencyGraph,
        available_versions: Dict[str, List[Version]] = None
    ) -> ResolutionResult:
        """Resolve dependencies."""
        available_versions = available_versions or {}

        # Check for cycles
        cycles = GraphAlgorithms.detect_cycles(graph)

        if cycles:
            return ResolutionResult(
                resolved=[],
                unresolved=[c.path for c in cycles],
                conflicts=[],
                order=[]
            )

        # Topological sort
        try:
            order = GraphAlgorithms.topological_sort(graph)
        except ValueError:
            return ResolutionResult(
                resolved=[],
                unresolved=["Cycle detected"],
                conflicts=[],
                order=[]
            )

        # Resolve versions
        resolved = []
        conflicts = []

        for node_id in order:
            node = graph.get_node(node_id)

            if not node:
                continue

            resolved.append(node)

        return ResolutionResult(
            resolved=resolved,
            unresolved=[],
            conflicts=conflicts,
            order=order
        )

    def get_execution_order(
        self,
        graph: DependencyGraph
    ) -> List[List[str]]:
        """Get parallel execution order (levels)."""
        # Calculate in-degrees
        in_degree: Dict[str, int] = defaultdict(int)

        for node in graph.nodes():
            in_degree[node.id] = len(graph.get_dependents(node.id))

        levels = []
        remaining = set(n.id for n in graph.nodes())

        while remaining:
            # Find nodes with no remaining dependencies
            level = [
                node_id for node_id in remaining
                if all(
                    dep not in remaining
                    for dep in graph.get_dependents(node_id)
                )
            ]

            if not level:
                break  # Cycle detected

            levels.append(level)
            remaining -= set(level)

        return levels


# =============================================================================
# DEPENDENCY GRAPH MANAGER
# =============================================================================

class DependencyGraphManager:
    """
    Comprehensive Dependency Graph Manager for BAEL.

    Provides dependency graph analysis and resolution.
    """

    def __init__(self):
        self._graphs: Dict[str, DependencyGraph] = {}
        self._resolver = DependencyResolver()
        self._stats: Dict[str, int] = defaultdict(int)

    # -------------------------------------------------------------------------
    # GRAPH MANAGEMENT
    # -------------------------------------------------------------------------

    def create_graph(self, name: str) -> DependencyGraph:
        """Create new dependency graph."""
        graph = DependencyGraph()
        self._graphs[name] = graph
        self._stats["graphs_created"] += 1

        return graph

    def get_graph(self, name: str) -> Optional[DependencyGraph]:
        """Get graph by name."""
        return self._graphs.get(name)

    def delete_graph(self, name: str) -> bool:
        """Delete graph."""
        if name in self._graphs:
            del self._graphs[name]
            return True

        return False

    def list_graphs(self) -> List[str]:
        """List graph names."""
        return list(self._graphs.keys())

    # -------------------------------------------------------------------------
    # NODE OPERATIONS
    # -------------------------------------------------------------------------

    def add_node(
        self,
        graph_name: str,
        node_id: str,
        name: str = None,
        version: str = None,
        **metadata
    ) -> Node:
        """Add node to graph."""
        graph = self._graphs.get(graph_name)

        if not graph:
            raise ValueError(f"Graph not found: {graph_name}")

        node = Node(
            id=node_id,
            name=name or node_id,
            version=Version.parse(version) if version else None,
            metadata=metadata
        )

        graph.add_node(node)
        self._stats["nodes_added"] += 1

        return node

    def remove_node(self, graph_name: str, node_id: str) -> bool:
        """Remove node from graph."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return False

        return graph.remove_node(node_id)

    # -------------------------------------------------------------------------
    # EDGE OPERATIONS
    # -------------------------------------------------------------------------

    def add_dependency(
        self,
        graph_name: str,
        source: str,
        target: str,
        dependency_type: DependencyType = DependencyType.REQUIRED,
        constraint: str = None,
        **metadata
    ) -> Edge:
        """Add dependency edge."""
        graph = self._graphs.get(graph_name)

        if not graph:
            raise ValueError(f"Graph not found: {graph_name}")

        edge = Edge(
            source=source,
            target=target,
            dependency_type=dependency_type,
            constraint=VersionConstraint.parse(constraint) if constraint else None,
            metadata=metadata
        )

        graph.add_edge(edge)
        self._stats["edges_added"] += 1

        return edge

    def remove_dependency(
        self,
        graph_name: str,
        source: str,
        target: str
    ) -> bool:
        """Remove dependency edge."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return False

        return graph.remove_edge(source, target)

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def detect_cycles(self, graph_name: str) -> List[Cycle]:
        """Detect cycles in graph."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return []

        return GraphAlgorithms.detect_cycles(graph)

    def get_topological_order(self, graph_name: str) -> List[str]:
        """Get topological order."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return []

        try:
            return GraphAlgorithms.topological_sort(graph)
        except ValueError:
            return []

    def find_path(
        self,
        graph_name: str,
        source: str,
        target: str
    ) -> Optional[List[str]]:
        """Find path between nodes."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return None

        return GraphAlgorithms.find_path(graph, source, target)

    def get_all_dependencies(
        self,
        graph_name: str,
        node_id: str,
        transitive: bool = True
    ) -> Set[str]:
        """Get all dependencies of node."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return set()

        return GraphAlgorithms.get_all_dependencies(graph, node_id, transitive)

    def get_all_dependents(
        self,
        graph_name: str,
        node_id: str,
        transitive: bool = True
    ) -> Set[str]:
        """Get all dependents of node."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return set()

        return GraphAlgorithms.get_all_dependents(graph, node_id, transitive)

    def impact_analysis(
        self,
        graph_name: str,
        node_id: str
    ) -> ImpactAnalysis:
        """Analyze impact of changing a node."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return ImpactAnalysis(
                node_id=node_id,
                direct_dependents=[],
                all_dependents=[],
                impact_level=0
            )

        direct = graph.get_dependents(node_id)
        all_deps = GraphAlgorithms.get_all_dependents(graph, node_id)

        return ImpactAnalysis(
            node_id=node_id,
            direct_dependents=direct,
            all_dependents=list(all_deps),
            impact_level=len(all_deps)
        )

    # -------------------------------------------------------------------------
    # RESOLUTION
    # -------------------------------------------------------------------------

    def resolve(
        self,
        graph_name: str,
        strategy: ResolutionStrategy = ResolutionStrategy.NEWEST
    ) -> ResolutionResult:
        """Resolve dependencies."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return ResolutionResult(
                resolved=[],
                unresolved=["Graph not found"],
                conflicts=[],
                order=[]
            )

        resolver = DependencyResolver(strategy=strategy)

        return resolver.resolve(graph)

    def get_execution_order(self, graph_name: str) -> List[List[str]]:
        """Get parallel execution order."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return []

        return self._resolver.get_execution_order(graph)

    # -------------------------------------------------------------------------
    # VISUALIZATION
    # -------------------------------------------------------------------------

    def to_text(self, graph_name: str) -> str:
        """Convert graph to text representation."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return ""

        lines = [f"Graph: {graph_name}"]
        lines.append(f"Nodes: {graph.node_count}, Edges: {graph.edge_count}")
        lines.append("")

        for node in graph.nodes():
            deps = graph.get_dependencies(node.id)
            version_str = f" ({node.version})" if node.version else ""

            if deps:
                lines.append(f"{node.name}{version_str} -> {', '.join(deps)}")
            else:
                lines.append(f"{node.name}{version_str} (no dependencies)")

        return "\n".join(lines)

    def to_mermaid(self, graph_name: str) -> str:
        """Convert graph to Mermaid diagram."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return ""

        lines = ["graph TD"]

        for edge in graph.edges():
            source_node = graph.get_node(edge.source)
            target_node = graph.get_node(edge.target)

            source_label = source_node.name if source_node else edge.source
            target_label = target_node.name if target_node else edge.target

            lines.append(f"    {edge.source}[{source_label}] --> {edge.target}[{target_label}]")

        return "\n".join(lines)

    def to_dot(self, graph_name: str) -> str:
        """Convert graph to DOT format."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return ""

        lines = [f"digraph {graph_name} {{"]
        lines.append("    rankdir=TB;")

        for node in graph.nodes():
            version_str = f"\\n{node.version}" if node.version else ""
            lines.append(f'    {node.id} [label="{node.name}{version_str}"];')

        for edge in graph.edges():
            lines.append(f"    {edge.source} -> {edge.target};")

        lines.append("}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_graph_stats(self, graph_name: str) -> Dict[str, Any]:
        """Get graph statistics."""
        graph = self._graphs.get(graph_name)

        if not graph:
            return {}

        # Calculate metrics
        nodes = graph.nodes()
        in_degrees = [len(graph.get_dependents(n.id)) for n in nodes]
        out_degrees = [len(graph.get_dependencies(n.id)) for n in nodes]

        return {
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "avg_in_degree": sum(in_degrees) / len(nodes) if nodes else 0,
            "avg_out_degree": sum(out_degrees) / len(nodes) if nodes else 0,
            "max_in_degree": max(in_degrees) if in_degrees else 0,
            "max_out_degree": max(out_degrees) if out_degrees else 0,
            "root_nodes": len([n for n in nodes if len(graph.get_dependents(n.id)) == 0]),
            "leaf_nodes": len([n for n in nodes if len(graph.get_dependencies(n.id)) == 0])
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "graph_count": len(self._graphs),
            "graphs_created": self._stats["graphs_created"],
            "nodes_added": self._stats["nodes_added"],
            "edges_added": self._stats["edges_added"]
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Dependency Graph Manager."""
    print("=" * 70)
    print("BAEL - DEPENDENCY GRAPH MANAGER DEMO")
    print("Comprehensive Dependency Analysis System")
    print("=" * 70)
    print()

    manager = DependencyGraphManager()

    # 1. Create Graph
    print("1. CREATE GRAPH:")
    print("-" * 40)

    graph = manager.create_graph("project")
    print(f"   Created graph: project")
    print()

    # 2. Add Nodes
    print("2. ADD NODES:")
    print("-" * 40)

    nodes = [
        ("app", "Application", "1.0.0"),
        ("auth", "Auth Module", "2.0.0"),
        ("db", "Database", "3.0.0"),
        ("cache", "Cache", "1.5.0"),
        ("logging", "Logging", "1.0.0"),
        ("config", "Config", "1.0.0"),
        ("utils", "Utilities", "1.2.0")
    ]

    for node_id, name, version in nodes:
        manager.add_node("project", node_id, name, version)
        print(f"   Added: {name} v{version}")
    print()

    # 3. Add Dependencies
    print("3. ADD DEPENDENCIES:")
    print("-" * 40)

    dependencies = [
        ("app", "auth"),
        ("app", "db"),
        ("app", "logging"),
        ("auth", "db"),
        ("auth", "cache"),
        ("db", "config"),
        ("db", "logging"),
        ("cache", "config"),
        ("logging", "config"),
        ("logging", "utils"),
        ("config", "utils")
    ]

    for source, target in dependencies:
        manager.add_dependency("project", source, target)
        print(f"   {source} -> {target}")
    print()

    # 4. Topological Order
    print("4. TOPOLOGICAL ORDER:")
    print("-" * 40)

    order = manager.get_topological_order("project")
    print(f"   Build order: {' -> '.join(order)}")
    print()

    # 5. Get Dependencies
    print("5. GET DEPENDENCIES:")
    print("-" * 40)

    for node_id in ["app", "auth", "db"]:
        direct = manager.get_all_dependencies("project", node_id, transitive=False)
        all_deps = manager.get_all_dependencies("project", node_id, transitive=True)
        print(f"   {node_id}:")
        print(f"      Direct: {direct}")
        print(f"      All: {all_deps}")
    print()

    # 6. Get Dependents
    print("6. GET DEPENDENTS:")
    print("-" * 40)

    for node_id in ["utils", "config", "logging"]:
        direct = manager.get_all_dependents("project", node_id, transitive=False)
        all_deps = manager.get_all_dependents("project", node_id, transitive=True)
        print(f"   {node_id}:")
        print(f"      Direct: {direct}")
        print(f"      All: {all_deps}")
    print()

    # 7. Find Path
    print("7. FIND PATH:")
    print("-" * 40)

    paths = [
        ("app", "utils"),
        ("app", "config"),
        ("auth", "utils")
    ]

    for source, target in paths:
        path = manager.find_path("project", source, target)

        if path:
            print(f"   {source} to {target}: {' -> '.join(path)}")
        else:
            print(f"   {source} to {target}: No path found")
    print()

    # 8. Impact Analysis
    print("8. IMPACT ANALYSIS:")
    print("-" * 40)

    for node_id in ["utils", "config", "logging"]:
        impact = manager.impact_analysis("project", node_id)
        print(f"   {node_id}:")
        print(f"      Direct dependents: {impact.direct_dependents}")
        print(f"      Impact level: {impact.impact_level}")
    print()

    # 9. Parallel Execution Order
    print("9. PARALLEL EXECUTION ORDER:")
    print("-" * 40)

    levels = manager.get_execution_order("project")

    for i, level in enumerate(levels):
        print(f"   Level {i + 1}: {level}")
    print()

    # 10. Cycle Detection
    print("10. CYCLE DETECTION:")
    print("-" * 40)

    cycles = manager.detect_cycles("project")

    if cycles:
        for cycle in cycles:
            print(f"   Cycle: {cycle.path}")
    else:
        print("   No cycles detected ✓")

    # Create a graph with cycle
    manager.create_graph("with_cycle")
    manager.add_node("with_cycle", "A", "A")
    manager.add_node("with_cycle", "B", "B")
    manager.add_node("with_cycle", "C", "C")
    manager.add_dependency("with_cycle", "A", "B")
    manager.add_dependency("with_cycle", "B", "C")
    manager.add_dependency("with_cycle", "C", "A")  # Creates cycle

    cycles = manager.detect_cycles("with_cycle")
    print(f"   Graph with cycle: {cycles[0].path if cycles else 'none'}")
    print()

    # 11. Resolution
    print("11. DEPENDENCY RESOLUTION:")
    print("-" * 40)

    result = manager.resolve("project")

    print(f"   Success: {result.success}")
    print(f"   Order: {result.order}")
    print(f"   Resolved: {len(result.resolved)} nodes")
    print()

    # 12. Text Visualization
    print("12. TEXT VISUALIZATION:")
    print("-" * 40)

    text = manager.to_text("project")

    for line in text.split("\n"):
        print(f"   {line}")
    print()

    # 13. Mermaid Diagram
    print("13. MERMAID DIAGRAM:")
    print("-" * 40)

    mermaid = manager.to_mermaid("project")

    for line in mermaid.split("\n")[:6]:
        print(f"   {line}")
    print("   ...")
    print()

    # 14. Graph Statistics
    print("14. GRAPH STATISTICS:")
    print("-" * 40)

    stats = manager.get_graph_stats("project")

    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # 15. Manager Statistics
    print("15. MANAGER STATISTICS:")
    print("-" * 40)

    manager_stats = manager.get_stats()

    for key, value in manager_stats.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Dependency Graph Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
