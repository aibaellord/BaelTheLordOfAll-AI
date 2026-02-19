"""
BAEL Strongly Connected Components Engine
==========================================

SCC decomposition for directed graphs.

"Ba'el finds the cycles within cycles." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.SCC")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SCCComponent:
    """A strongly connected component."""
    id: int
    nodes: Set[int] = field(default_factory=set)


@dataclass
class SCCStats:
    """SCC statistics."""
    node_count: int = 0
    edge_count: int = 0
    scc_count: int = 0
    largest_scc: int = 0


# ============================================================================
# KOSARAJU'S ALGORITHM
# ============================================================================

class KosarajuSCC:
    """
    Kosaraju's algorithm for SCC.

    Features:
    - Two DFS passes
    - O(V + E) complexity
    - Simple and intuitive

    "Ba'el traverses forward and backward." — Ba'el
    """

    def __init__(self):
        """Initialize Kosaraju SCC."""
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._radj: Dict[int, List[int]] = defaultdict(list)  # Reverse
        self._nodes: Set[int] = set()

        self._scc_id: Dict[int, int] = {}
        self._components: List[SCCComponent] = []
        self._stats = SCCStats()
        self._built = False
        self._lock = threading.RLock()

        logger.debug("Kosaraju SCC initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add directed edge u → v."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append(v)
            self._radj[v].append(u)

    def build(self) -> None:
        """Build SCCs using Kosaraju's algorithm."""
        with self._lock:
            if self._built:
                return

            self._scc_id.clear()
            self._components.clear()

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = sum(len(edges) for edges in self._adj.values())

            # Pass 1: DFS on original graph to get finish order
            visited = set()
            order = []

            def dfs1(node: int) -> None:
                visited.add(node)
                for neighbor in self._adj[node]:
                    if neighbor not in visited:
                        dfs1(neighbor)
                order.append(node)

            for node in self._nodes:
                if node not in visited:
                    dfs1(node)

            # Pass 2: DFS on reverse graph in reverse finish order
            visited.clear()

            def dfs2(node: int, scc_id: int) -> None:
                visited.add(node)
                self._scc_id[node] = scc_id
                self._components[scc_id].nodes.add(node)

                for neighbor in self._radj[node]:
                    if neighbor not in visited:
                        dfs2(neighbor, scc_id)

            for node in reversed(order):
                if node not in visited:
                    scc_id = len(self._components)
                    self._components.append(SCCComponent(id=scc_id))
                    dfs2(node, scc_id)

            self._stats.scc_count = len(self._components)
            self._stats.largest_scc = max(
                (len(c.nodes) for c in self._components), default=0
            )

            self._built = True
            logger.info(f"Kosaraju SCC: {self._stats.scc_count} components")

    def get_scc_id(self, node: int) -> int:
        """Get SCC ID for node."""
        self.build()
        return self._scc_id.get(node, -1)

    def get_component(self, scc_id: int) -> Optional[SCCComponent]:
        """Get component by ID."""
        self.build()
        if 0 <= scc_id < len(self._components):
            return self._components[scc_id]
        return None

    def get_all_components(self) -> List[SCCComponent]:
        """Get all SCCs."""
        self.build()
        return self._components.copy()

    def same_scc(self, u: int, v: int) -> bool:
        """Check if u and v are in same SCC."""
        self.build()
        return self._scc_id.get(u, -1) == self._scc_id.get(v, -2)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        self.build()
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'scc_count': self._stats.scc_count,
            'largest_scc': self._stats.largest_scc
        }


# ============================================================================
# TARJAN'S ALGORITHM
# ============================================================================

class TarjanSCC:
    """
    Tarjan's algorithm for SCC.

    Features:
    - Single DFS pass
    - O(V + E) complexity
    - Low-link values

    "Ba'el discovers with a single sweep." — Ba'el
    """

    def __init__(self):
        """Initialize Tarjan SCC."""
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._nodes: Set[int] = set()

        # Tarjan state
        self._index: Dict[int, int] = {}
        self._lowlink: Dict[int, int] = {}
        self._on_stack: Dict[int, bool] = {}
        self._stack: List[int] = []
        self._current_index = 0

        self._scc_id: Dict[int, int] = {}
        self._components: List[SCCComponent] = []
        self._stats = SCCStats()
        self._built = False
        self._lock = threading.RLock()

        logger.debug("Tarjan SCC initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add directed edge u → v."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append(v)

    def build(self) -> None:
        """Build SCCs using Tarjan's algorithm."""
        with self._lock:
            if self._built:
                return

            self._index.clear()
            self._lowlink.clear()
            self._on_stack.clear()
            self._stack.clear()
            self._current_index = 0
            self._scc_id.clear()
            self._components.clear()

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = sum(len(edges) for edges in self._adj.values())

            def strongconnect(v: int) -> None:
                self._index[v] = self._current_index
                self._lowlink[v] = self._current_index
                self._current_index += 1
                self._stack.append(v)
                self._on_stack[v] = True

                for w in self._adj[v]:
                    if w not in self._index:
                        strongconnect(w)
                        self._lowlink[v] = min(self._lowlink[v], self._lowlink[w])
                    elif self._on_stack.get(w, False):
                        self._lowlink[v] = min(self._lowlink[v], self._index[w])

                # Root of SCC
                if self._lowlink[v] == self._index[v]:
                    scc_id = len(self._components)
                    scc = SCCComponent(id=scc_id)

                    while True:
                        w = self._stack.pop()
                        self._on_stack[w] = False
                        self._scc_id[w] = scc_id
                        scc.nodes.add(w)

                        if w == v:
                            break

                    self._components.append(scc)

            for node in self._nodes:
                if node not in self._index:
                    strongconnect(node)

            self._stats.scc_count = len(self._components)
            self._stats.largest_scc = max(
                (len(c.nodes) for c in self._components), default=0
            )

            self._built = True
            logger.info(f"Tarjan SCC: {self._stats.scc_count} components")

    def get_scc_id(self, node: int) -> int:
        """Get SCC ID for node."""
        self.build()
        return self._scc_id.get(node, -1)

    def get_component(self, scc_id: int) -> Optional[SCCComponent]:
        """Get component by ID."""
        self.build()
        if 0 <= scc_id < len(self._components):
            return self._components[scc_id]
        return None

    def get_all_components(self) -> List[SCCComponent]:
        """Get all SCCs."""
        self.build()
        return self._components.copy()

    def same_scc(self, u: int, v: int) -> bool:
        """Check if u and v are in same SCC."""
        self.build()
        return self._scc_id.get(u, -1) == self._scc_id.get(v, -2)

    def get_condensation_graph(self) -> Dict[int, Set[int]]:
        """
        Get condensation DAG (each SCC as single node).

        Returns:
            Dict mapping SCC_id → set of adjacent SCC_ids
        """
        self.build()

        dag: Dict[int, Set[int]] = defaultdict(set)

        for u in self._nodes:
            for v in self._adj[u]:
                u_scc = self._scc_id[u]
                v_scc = self._scc_id[v]

                if u_scc != v_scc:
                    dag[u_scc].add(v_scc)

        return dict(dag)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        self.build()
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'scc_count': self._stats.scc_count,
            'largest_scc': self._stats.largest_scc
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_kosaraju_scc() -> KosarajuSCC:
    """Create Kosaraju SCC engine."""
    return KosarajuSCC()


def create_tarjan_scc() -> TarjanSCC:
    """Create Tarjan SCC engine."""
    return TarjanSCC()


def find_sccs(
    edges: List[Tuple[int, int]],
    algorithm: str = "tarjan"
) -> List[Set[int]]:
    """
    Find all strongly connected components.

    Args:
        edges: List of (u, v) directed edges
        algorithm: "tarjan" or "kosaraju"

    Returns:
        List of node sets (one per SCC)
    """
    if algorithm == "kosaraju":
        engine = KosarajuSCC()
    else:
        engine = TarjanSCC()

    for u, v in edges:
        engine.add_edge(u, v)

    return [comp.nodes for comp in engine.get_all_components()]


def count_sccs(edges: List[Tuple[int, int]]) -> int:
    """Count number of SCCs."""
    engine = TarjanSCC()
    for u, v in edges:
        engine.add_edge(u, v)
    engine.build()
    return engine._stats.scc_count


def is_strongly_connected(edges: List[Tuple[int, int]]) -> bool:
    """Check if graph is strongly connected (single SCC)."""
    return count_sccs(edges) == 1


def get_condensation_dag(
    edges: List[Tuple[int, int]]
) -> Tuple[Dict[int, Set[int]], Dict[int, Set[int]]]:
    """
    Get condensation DAG.

    Returns:
        (dag_edges, scc_nodes) where:
        - dag_edges: SCC_id → set of adjacent SCC_ids
        - scc_nodes: SCC_id → nodes in that SCC
    """
    engine = TarjanSCC()
    for u, v in edges:
        engine.add_edge(u, v)

    dag = engine.get_condensation_graph()
    scc_nodes = {comp.id: comp.nodes for comp in engine.get_all_components()}

    return dag, scc_nodes
