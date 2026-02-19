"""
BAEL Block Cut Tree Engine
==========================

Bridges, articulation points, and biconnected components.

"Ba'el finds the critical connections." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.BlockCutTree")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BCTStats:
    """Block cut tree statistics."""
    node_count: int = 0
    edge_count: int = 0
    articulation_points: int = 0
    bridges: int = 0
    biconnected_components: int = 0


@dataclass
class BiconnectedComponent:
    """A biconnected component."""
    id: int
    nodes: Set[int] = field(default_factory=set)
    edges: List[Tuple[int, int]] = field(default_factory=list)


# ============================================================================
# BLOCK CUT TREE ENGINE
# ============================================================================

class BlockCutTreeEngine:
    """
    Block Cut Tree for articulation points and bridges.

    Features:
    - O(V + E) articulation point detection
    - O(V + E) bridge detection
    - O(V + E) biconnected component decomposition
    - Block-cut tree construction

    "Ba'el identifies the critical failures." — Ba'el
    """

    def __init__(self):
        """Initialize block cut tree engine."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._edges: Set[Tuple[int, int]] = set()

        # Results
        self._articulation_points: Set[int] = set()
        self._bridges: List[Tuple[int, int]] = []
        self._biconnected_components: List[BiconnectedComponent] = []

        # Block-cut tree
        self._bct_adj: Dict[int, Set[int]] = defaultdict(set)
        self._is_articulation: Dict[int, bool] = {}

        # DFS state
        self._discovery: Dict[int, int] = {}
        self._low: Dict[int, int] = {}
        self._parent: Dict[int, int] = {}
        self._timer = 0
        self._edge_stack: List[Tuple[int, int]] = []

        self._stats = BCTStats()
        self._built = False
        self._lock = threading.RLock()

        logger.debug("Block cut tree engine initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)

            edge = (min(u, v), max(u, v))
            if edge not in self._edges:
                self._edges.add(edge)
                self._adj[u].add(v)
                self._adj[v].add(u)

    def build(self) -> None:
        """Build block cut tree."""
        with self._lock:
            if self._built:
                return

            self._articulation_points.clear()
            self._bridges.clear()
            self._biconnected_components.clear()
            self._bct_adj.clear()

            self._discovery.clear()
            self._low.clear()
            self._parent.clear()
            self._timer = 0
            self._edge_stack.clear()

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = len(self._edges)

            # Run DFS from each unvisited node
            for node in self._nodes:
                if node not in self._discovery:
                    self._dfs(node)

            # Build block-cut tree
            self._build_block_cut_tree()

            self._stats.articulation_points = len(self._articulation_points)
            self._stats.bridges = len(self._bridges)
            self._stats.biconnected_components = len(self._biconnected_components)

            self._built = True
            logger.info(f"BCT built: {self._stats.articulation_points} APs, "
                       f"{self._stats.bridges} bridges, "
                       f"{self._stats.biconnected_components} BCCs")

    def _dfs(self, u: int) -> None:
        """DFS for finding articulation points and bridges."""
        self._discovery[u] = self._timer
        self._low[u] = self._timer
        self._timer += 1

        children = 0

        for v in self._adj[u]:
            if v not in self._discovery:
                # Tree edge
                children += 1
                self._parent[v] = u
                self._edge_stack.append((u, v))

                self._dfs(v)

                self._low[u] = min(self._low[u], self._low[v])

                # Check for articulation point
                is_root = self._parent.get(u) is None

                if is_root and children > 1:
                    self._articulation_points.add(u)
                    self._extract_component(u, v)
                elif not is_root and self._low[v] >= self._discovery[u]:
                    self._articulation_points.add(u)
                    self._extract_component(u, v)

                # Check for bridge
                if self._low[v] > self._discovery[u]:
                    self._bridges.append((min(u, v), max(u, v)))

            elif v != self._parent.get(u):
                # Back edge
                self._low[u] = min(self._low[u], self._discovery[v])

                if self._discovery[v] < self._discovery[u]:
                    self._edge_stack.append((u, v))

        # If root and has edges remaining
        if self._parent.get(u) is None and self._edge_stack:
            self._extract_remaining_component()

    def _extract_component(self, u: int, v: int) -> None:
        """Extract biconnected component ending with edge (u, v)."""
        comp_id = len(self._biconnected_components)
        comp = BiconnectedComponent(id=comp_id)

        while self._edge_stack:
            edge = self._edge_stack.pop()
            comp.edges.append(edge)
            comp.nodes.add(edge[0])
            comp.nodes.add(edge[1])

            if edge == (u, v) or edge == (v, u):
                break

        if comp.nodes:
            self._biconnected_components.append(comp)

    def _extract_remaining_component(self) -> None:
        """Extract remaining edges as a component."""
        if not self._edge_stack:
            return

        comp_id = len(self._biconnected_components)
        comp = BiconnectedComponent(id=comp_id)

        while self._edge_stack:
            edge = self._edge_stack.pop()
            comp.edges.append(edge)
            comp.nodes.add(edge[0])
            comp.nodes.add(edge[1])

        if comp.nodes:
            self._biconnected_components.append(comp)

    def _build_block_cut_tree(self) -> None:
        """Build block-cut tree."""
        # Node IDs: articulation points keep their ID
        # Components get ID = max_node + component_id + 1

        max_node = max(self._nodes) if self._nodes else 0

        for comp in self._biconnected_components:
            comp_node = max_node + comp.id + 1

            for node in comp.nodes:
                if node in self._articulation_points:
                    self._bct_adj[node].add(comp_node)
                    self._bct_adj[comp_node].add(node)

        for node in self._articulation_points:
            self._is_articulation[node] = True

    def get_articulation_points(self) -> Set[int]:
        """Get all articulation points."""
        self.build()
        return self._articulation_points.copy()

    def get_bridges(self) -> List[Tuple[int, int]]:
        """Get all bridges."""
        self.build()
        return self._bridges.copy()

    def get_biconnected_components(self) -> List[BiconnectedComponent]:
        """Get all biconnected components."""
        self.build()
        return self._biconnected_components.copy()

    def is_articulation_point(self, node: int) -> bool:
        """Check if node is an articulation point."""
        self.build()
        return node in self._articulation_points

    def is_bridge(self, u: int, v: int) -> bool:
        """Check if edge is a bridge."""
        self.build()
        edge = (min(u, v), max(u, v))
        return edge in self._bridges

    def get_component_for_node(self, node: int) -> List[BiconnectedComponent]:
        """Get biconnected components containing a node."""
        self.build()
        return [comp for comp in self._biconnected_components if node in comp.nodes]

    def would_disconnect(self, node: int) -> bool:
        """Check if removing node would disconnect the graph."""
        return self.is_articulation_point(node)

    def would_disconnect_edge(self, u: int, v: int) -> bool:
        """Check if removing edge would disconnect the graph."""
        return self.is_bridge(u, v)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        self.build()
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'articulation_points': self._stats.articulation_points,
            'bridges': self._stats.bridges,
            'biconnected_components': self._stats.biconnected_components
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_block_cut_tree() -> BlockCutTreeEngine:
    """Create block cut tree engine."""
    return BlockCutTreeEngine()


def find_articulation_points(edges: List[Tuple[int, int]]) -> Set[int]:
    """
    Find all articulation points.

    Args:
        edges: List of (u, v) edges

    Returns:
        Set of articulation points
    """
    engine = BlockCutTreeEngine()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.get_articulation_points()


def find_bridges(edges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Find all bridges.

    Args:
        edges: List of (u, v) edges

    Returns:
        List of bridge edges
    """
    engine = BlockCutTreeEngine()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.get_bridges()


def find_biconnected_components(
    edges: List[Tuple[int, int]]
) -> List[BiconnectedComponent]:
    """
    Find all biconnected components.

    Args:
        edges: List of (u, v) edges

    Returns:
        List of biconnected components
    """
    engine = BlockCutTreeEngine()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.get_biconnected_components()


def is_biconnected(edges: List[Tuple[int, int]]) -> bool:
    """Check if graph is biconnected (no articulation points)."""
    engine = BlockCutTreeEngine()
    for u, v in edges:
        engine.add_edge(u, v)
    return len(engine.get_articulation_points()) == 0


def is_bridge_connected(edges: List[Tuple[int, int]]) -> bool:
    """Check if graph is bridge-connected (no bridges)."""
    engine = BlockCutTreeEngine()
    for u, v in edges:
        engine.add_edge(u, v)
    return len(engine.get_bridges()) == 0
