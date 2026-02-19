"""
BAEL Dominator Tree Engine
==========================

Dominators in directed graphs.

"Ba'el knows who controls whom." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.DominatorTree")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DominatorStats:
    """Dominator tree statistics."""
    node_count: int = 0
    edge_count: int = 0
    dominator_count: int = 0
    max_dom_depth: int = 0


# ============================================================================
# DOMINATOR TREE ENGINE
# ============================================================================

class DominatorTreeEngine:
    """
    Dominator Tree using Lengauer-Tarjan algorithm.

    Features:
    - O(E * α(E, V)) complexity (near-linear)
    - Immediate dominator computation
    - Dominance frontier computation
    - Control dependence analysis

    "Ba'el dominates all paths." — Ba'el
    """

    def __init__(self, entry: int):
        """
        Initialize dominator tree engine.

        Args:
            entry: Entry node (root)
        """
        self._entry = entry
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._pred: Dict[int, List[int]] = defaultdict(list)
        self._nodes: Set[int] = {entry}

        # Lengauer-Tarjan data structures
        self._parent: Dict[int, int] = {}
        self._semi: Dict[int, int] = {}
        self._vertex: List[int] = []
        self._bucket: Dict[int, Set[int]] = defaultdict(set)
        self._dom: Dict[int, int] = {}

        # Union-find for path compression
        self._ancestor: Dict[int, int] = {}
        self._label: Dict[int, int] = {}

        # Dominator tree
        self._dom_tree: Dict[int, List[int]] = defaultdict(list)
        self._dom_depth: Dict[int, int] = {}

        # Dominance frontier
        self._dom_frontier: Dict[int, Set[int]] = defaultdict(set)

        self._stats = DominatorStats()
        self._built = False
        self._lock = threading.RLock()

        logger.debug(f"Dominator tree engine initialized with entry {entry}")

    def add_edge(self, u: int, v: int) -> None:
        """Add directed edge u → v."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append(v)
            self._pred[v].append(u)

    def build(self) -> None:
        """Build dominator tree using Lengauer-Tarjan."""
        with self._lock:
            if self._built:
                return

            self._parent.clear()
            self._semi.clear()
            self._vertex.clear()
            self._bucket.clear()
            self._dom.clear()
            self._ancestor.clear()
            self._label.clear()
            self._dom_tree.clear()
            self._dom_depth.clear()
            self._dom_frontier.clear()

            # Initialize
            for node in self._nodes:
                self._semi[node] = 0
                self._ancestor[node] = 0
                self._label[node] = node

            # Step 1: DFS numbering
            self._dfs(self._entry)

            n = len(self._vertex)
            self._stats.node_count = n

            if n == 0:
                return

            # Process vertices in reverse DFS order
            for i in range(n - 1, 0, -1):
                w = self._vertex[i]

                # Step 2: Compute semidominator
                for v in self._pred[w]:
                    if v in self._semi and self._semi[v] > 0:
                        u = self._eval(v)
                        if self._semi[u] < self._semi[w]:
                            self._semi[w] = self._semi[u]

                self._bucket[self._vertex[self._semi[w]]].add(w)
                self._link(self._parent[w], w)

                # Step 3: Implicit definition of immediate dominator
                p = self._parent[w]
                while self._bucket[p]:
                    v = self._bucket[p].pop()
                    u = self._eval(v)

                    if self._semi[u] < self._semi[v]:
                        self._dom[v] = u
                    else:
                        self._dom[v] = p

            # Step 4: Explicit dominator
            for i in range(1, n):
                w = self._vertex[i]
                if w in self._dom and self._dom[w] != self._vertex[self._semi[w]]:
                    self._dom[w] = self._dom.get(self._dom[w], self._entry)

            self._dom[self._entry] = self._entry

            # Build dominator tree
            for node in self._nodes:
                if node in self._dom and node != self._entry:
                    self._dom_tree[self._dom[node]].append(node)

            # Compute depths
            self._compute_depths(self._entry, 0)

            # Compute dominance frontiers
            self._compute_dominance_frontiers()

            self._stats.dominator_count = len(self._dom)
            self._stats.max_dom_depth = max(self._dom_depth.values()) if self._dom_depth else 0
            self._stats.edge_count = sum(len(edges) for edges in self._adj.values())

            self._built = True
            logger.info(f"Dominator tree built: {n} nodes, depth {self._stats.max_dom_depth}")

    def _dfs(self, v: int) -> None:
        """DFS numbering."""
        self._semi[v] = len(self._vertex)
        self._vertex.append(v)

        for w in self._adj[v]:
            if w in self._semi and self._semi[w] == 0:
                self._parent[w] = v
                self._dfs(w)

    def _eval(self, v: int) -> int:
        """Evaluate with path compression."""
        if self._ancestor.get(v, 0) == 0:
            return v

        self._compress(v)
        return self._label[v]

    def _compress(self, v: int) -> None:
        """Path compression."""
        a = self._ancestor.get(v, 0)
        if a == 0:
            return

        if self._ancestor.get(a, 0) != 0:
            self._compress(a)

            if self._semi[self._label[a]] < self._semi[self._label[v]]:
                self._label[v] = self._label[a]

            self._ancestor[v] = self._ancestor.get(a, 0)

    def _link(self, v: int, w: int) -> None:
        """Link operation."""
        self._ancestor[w] = v

    def _compute_depths(self, node: int, depth: int) -> None:
        """Compute dominator tree depths."""
        self._dom_depth[node] = depth

        for child in self._dom_tree[node]:
            self._compute_depths(child, depth + 1)

    def _compute_dominance_frontiers(self) -> None:
        """Compute dominance frontiers."""
        for node in self._nodes:
            if node not in self._pred or len(self._pred[node]) < 2:
                continue

            for pred in self._pred[node]:
                runner = pred

                while runner in self._dom and runner != self._dom.get(node):
                    self._dom_frontier[runner].add(node)
                    runner = self._dom.get(runner, self._entry)

    def get_idom(self, node: int) -> Optional[int]:
        """Get immediate dominator of node."""
        self.build()
        return self._dom.get(node)

    def dominates(self, a: int, b: int) -> bool:
        """Check if a dominates b."""
        self.build()

        if a == b:
            return True

        current = b
        while current in self._dom and current != self._entry:
            current = self._dom[current]
            if current == a:
                return True

        return False

    def strictly_dominates(self, a: int, b: int) -> bool:
        """Check if a strictly dominates b (dominates but not equal)."""
        return a != b and self.dominates(a, b)

    def get_dominators(self, node: int) -> List[int]:
        """Get all dominators of node (path to entry)."""
        self.build()

        result = []
        current = node

        while current in self._dom:
            result.append(current)
            if current == self._entry:
                break
            current = self._dom[current]

        return result

    def get_dominated(self, node: int) -> Set[int]:
        """Get all nodes dominated by node."""
        self.build()

        result = set()
        stack = [node]

        while stack:
            current = stack.pop()
            result.add(current)
            stack.extend(self._dom_tree[current])

        return result

    def get_dominance_frontier(self, node: int) -> Set[int]:
        """Get dominance frontier of node."""
        self.build()
        return self._dom_frontier.get(node, set()).copy()

    def get_dom_tree_children(self, node: int) -> List[int]:
        """Get children in dominator tree."""
        self.build()
        return self._dom_tree.get(node, []).copy()

    def get_dom_depth(self, node: int) -> int:
        """Get depth in dominator tree."""
        self.build()
        return self._dom_depth.get(node, -1)

    def lca_in_dom_tree(self, a: int, b: int) -> Optional[int]:
        """Find LCA in dominator tree."""
        self.build()

        depth_a = self.get_dom_depth(a)
        depth_b = self.get_dom_depth(b)

        # Bring to same depth
        while depth_a > depth_b:
            a = self._dom.get(a, a)
            depth_a -= 1

        while depth_b > depth_a:
            b = self._dom.get(b, b)
            depth_b -= 1

        # Walk up together
        while a != b:
            a = self._dom.get(a, a)
            b = self._dom.get(b, b)

        return a

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        self.build()
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'dominator_count': self._stats.dominator_count,
            'max_dom_depth': self._stats.max_dom_depth
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_dominator_tree(entry: int) -> DominatorTreeEngine:
    """Create dominator tree engine."""
    return DominatorTreeEngine(entry)


def find_dominators(
    entry: int,
    edges: List[Tuple[int, int]]
) -> Dict[int, int]:
    """
    Find immediate dominators.

    Args:
        entry: Entry node
        edges: List of (u, v) directed edges

    Returns:
        Dict mapping node → immediate dominator
    """
    engine = DominatorTreeEngine(entry)
    for u, v in edges:
        engine.add_edge(u, v)
    engine.build()

    return {node: engine.get_idom(node) for node in engine._nodes}


def find_dominance_frontiers(
    entry: int,
    edges: List[Tuple[int, int]]
) -> Dict[int, Set[int]]:
    """
    Find dominance frontiers.

    Args:
        entry: Entry node
        edges: List of (u, v) directed edges

    Returns:
        Dict mapping node → dominance frontier
    """
    engine = DominatorTreeEngine(entry)
    for u, v in edges:
        engine.add_edge(u, v)
    engine.build()

    return {node: engine.get_dominance_frontier(node) for node in engine._nodes}
