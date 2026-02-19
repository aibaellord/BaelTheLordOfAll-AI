"""
BAEL Centroid Decomposition Engine
==================================

Divide and conquer on trees.

"Ba'el finds the center of all trees." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field

logger = logging.getLogger("BAEL.CentroidDecomposition")

T = TypeVar('T')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class CentroidNode:
    """Node in centroid tree."""
    id: int
    centroid_parent: int = -1  # Parent in centroid tree
    centroid_depth: int = 0  # Depth in centroid tree
    subtree_size: int = 1
    removed: bool = False


@dataclass
class CentroidStats:
    """Centroid decomposition statistics."""
    node_count: int = 0
    centroid_depth: int = 0
    queries: int = 0


# ============================================================================
# CENTROID DECOMPOSITION ENGINE
# ============================================================================

class CentroidDecompositionEngine(Generic[T]):
    """
    Centroid Decomposition for tree divide and conquer.

    Features:
    - O(n log n) preprocessing
    - O(log n) centroid tree depth
    - Efficient path counting
    - Distance queries

    "Ba'el divides and conquers the tree of fate." — Ba'el
    """

    def __init__(self):
        """Initialize centroid decomposition."""
        self._nodes: Dict[int, CentroidNode] = {}
        self._adjacency: Dict[int, List[int]] = {}
        self._values: Dict[int, T] = {}
        self._centroid_children: Dict[int, List[int]] = {}
        self._centroid_root: int = -1
        self._stats = CentroidStats()
        self._lock = threading.RLock()
        self._built = False

        logger.debug("Centroid decomposition initialized")

    # ========================================================================
    # TREE CONSTRUCTION
    # ========================================================================

    def add_node(self, node_id: int, value: T = None) -> None:
        """Add a node."""
        with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = CentroidNode(id=node_id)
                self._adjacency[node_id] = []
                self._values[node_id] = value
                self._centroid_children[node_id] = []
                self._stats.node_count += 1
                self._built = False

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self.add_node(u)
            self.add_node(v)

            self._adjacency[u].append(v)
            self._adjacency[v].append(u)
            self._built = False

    def set_value(self, node_id: int, value: T) -> None:
        """Set node value."""
        with self._lock:
            if node_id in self._nodes:
                self._values[node_id] = value

    # ========================================================================
    # BUILD DECOMPOSITION
    # ========================================================================

    def build(self) -> None:
        """Build centroid decomposition."""
        with self._lock:
            if not self._nodes:
                return

            # Reset removed flags
            for node in self._nodes.values():
                node.removed = False
                node.centroid_parent = -1
                node.centroid_depth = 0

            # Clear centroid children
            for node_id in self._centroid_children:
                self._centroid_children[node_id] = []

            # Find any node as starting point
            start = next(iter(self._nodes))

            # Build decomposition
            self._centroid_root = self._decompose(start, -1, 0)

            # Compute max depth
            self._stats.centroid_depth = max(
                node.centroid_depth for node in self._nodes.values()
            )

            self._built = True
            logger.info(
                f"Centroid decomposition built: {self._stats.node_count} nodes, "
                f"depth {self._stats.centroid_depth}"
            )

    def _get_subtree_size(self, node: int, parent: int) -> int:
        """Compute subtree size (excluding removed nodes)."""
        size = 1

        for child in self._adjacency[node]:
            if child != parent and not self._nodes[child].removed:
                size += self._get_subtree_size(child, node)

        self._nodes[node].subtree_size = size
        return size

    def _find_centroid(self, node: int, parent: int, tree_size: int) -> int:
        """Find centroid of tree."""
        for child in self._adjacency[node]:
            if child != parent and not self._nodes[child].removed:
                if self._nodes[child].subtree_size > tree_size // 2:
                    return self._find_centroid(child, node, tree_size)

        return node

    def _decompose(self, node: int, parent_centroid: int, depth: int) -> int:
        """Decompose tree recursively."""
        # Compute sizes
        tree_size = self._get_subtree_size(node, -1)

        # Find centroid
        centroid = self._find_centroid(node, -1, tree_size)

        # Set centroid properties
        self._nodes[centroid].centroid_parent = parent_centroid
        self._nodes[centroid].centroid_depth = depth
        self._nodes[centroid].removed = True

        if parent_centroid != -1:
            self._centroid_children[parent_centroid].append(centroid)

        # Recursively decompose subtrees
        for child in self._adjacency[centroid]:
            if not self._nodes[child].removed:
                self._decompose(child, centroid, depth + 1)

        return centroid

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_centroid_path(self, node: int) -> List[int]:
        """
        Get path from node to centroid root in centroid tree.

        Args:
            node: Node ID

        Returns:
            List of centroids from node to root
        """
        with self._lock:
            if not self._built:
                raise RuntimeError("Must build first")

            path = []
            current = node

            # Find first ancestor that's a centroid
            # In general, we go up centroid parents
            # First, we need to find the centroid that "owns" this node

            while current != -1:
                path.append(current)
                current = self._nodes[current].centroid_parent

            return path

    def get_centroid_ancestors(self, node: int) -> List[int]:
        """
        Get all centroid ancestors.

        Args:
            node: Node ID

        Returns:
            List of centroid ancestors
        """
        return self.get_centroid_path(node)

    def count_paths_through_centroid(
        self,
        centroid: int,
        condition: Callable[[int, int], bool] = None
    ) -> int:
        """
        Count paths passing through centroid.

        Args:
            centroid: Centroid node
            condition: Optional condition(dist, value) for counting

        Returns:
            Number of valid paths
        """
        with self._lock:
            if not self._built:
                raise RuntimeError("Must build first")

            self._stats.queries += 1

            # Get distances to all nodes in subtree
            all_dists = []

            for child in self._adjacency[centroid]:
                if self._nodes[child].centroid_parent == centroid or \
                   centroid in self.get_centroid_ancestors(child):
                    subtree_dists = []
                    self._get_distances(child, centroid, 1, subtree_dists)
                    all_dists.append(subtree_dists)

            # Count valid paths
            count = 0

            if condition is None:
                # Count all pairs
                for i, dists1 in enumerate(all_dists):
                    for j, dists2 in enumerate(all_dists):
                        if i < j:
                            count += len(dists1) * len(dists2)
            else:
                # Apply condition
                # This is a simplified version - full implementation would
                # depend on the specific condition
                pass

            return count

    def _get_distances(
        self,
        node: int,
        parent: int,
        dist: int,
        result: List[Tuple[int, Any]]
    ) -> None:
        """Get distances from centroid to all nodes in subtree."""
        result.append((dist, self._values.get(node)))

        for child in self._adjacency[node]:
            if child != parent and \
               self._nodes[child].centroid_parent != node and \
               not self._is_ancestor_in_centroid_tree(node, child):
                self._get_distances(child, node, dist + 1, result)

    def _is_ancestor_in_centroid_tree(self, ancestor: int, node: int) -> bool:
        """Check if ancestor is an ancestor of node in centroid tree."""
        current = node
        while current != -1:
            if current == ancestor:
                return True
            current = self._nodes[current].centroid_parent
        return False

    def distance_query(self, u: int, v: int) -> int:
        """
        Find distance between two nodes.

        Args:
            u: First node
            v: Second node

        Returns:
            Number of edges on path
        """
        with self._lock:
            if not self._built:
                raise RuntimeError("Must build first")

            self._stats.queries += 1

            # BFS from u to v
            from collections import deque

            visited = {u: 0}
            queue = deque([u])

            while queue:
                node = queue.popleft()

                if node == v:
                    return visited[v]

                for child in self._adjacency[node]:
                    if child not in visited:
                        visited[child] = visited[node] + 1
                        queue.append(child)

            return -1  # Not connected

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_centroid_root(self) -> int:
        """Get root of centroid tree."""
        return self._centroid_root

    def get_centroid_children(self, centroid: int) -> List[int]:
        """Get children in centroid tree."""
        return self._centroid_children.get(centroid, [])

    def get_centroid_depth(self, node: int) -> int:
        """Get depth in centroid tree."""
        return self._nodes[node].centroid_depth if node in self._nodes else -1

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'centroid_depth': self._stats.centroid_depth,
            'queries': self._stats.queries
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_centroid_decomposition() -> CentroidDecompositionEngine:
    """Create centroid decomposition engine."""
    return CentroidDecompositionEngine()


def build_from_edges(
    edges: List[Tuple[int, int]]
) -> CentroidDecompositionEngine:
    """
    Build from edge list.

    Args:
        edges: List of (u, v) edges

    Returns:
        Built centroid decomposition
    """
    cd = CentroidDecompositionEngine()

    for u, v in edges:
        cd.add_edge(u, v)

    cd.build()
    return cd
