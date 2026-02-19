"""
BAEL Topological Sort Engine
============================

Linear ordering of DAG vertices.

"Ba'el orders dependencies perfectly." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.TopologicalSort")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class TopSortStats:
    """Topological sort statistics."""
    node_count: int = 0
    edge_count: int = 0
    has_cycle: bool = False
    sort_length: int = 0


# ============================================================================
# KAHN'S ALGORITHM (BFS)
# ============================================================================

class KahnTopSort:
    """
    Kahn's algorithm for topological sort (BFS-based).

    Features:
    - O(V + E) complexity
    - Cycle detection
    - All topological orderings (lexicographic)

    "Ba'el sorts by peeling dependencies." — Ba'el
    """

    def __init__(self):
        """Initialize Kahn's topological sort."""
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._in_degree: Dict[int, int] = defaultdict(int)
        self._nodes: Set[int] = set()

        self._result: List[int] = []
        self._stats = TopSortStats()
        self._built = False
        self._lock = threading.RLock()

        logger.debug("Kahn topological sort initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add directed edge u → v (u must come before v)."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append(v)
            self._in_degree[v] += 1

            if u not in self._in_degree:
                self._in_degree[u] = 0

    def add_dependency(self, before: int, after: int) -> None:
        """Add dependency: before must come before after."""
        self.add_edge(before, after)

    def sort(self) -> Optional[List[int]]:
        """
        Perform topological sort.

        Returns:
            Sorted list or None if cycle exists
        """
        with self._lock:
            if self._built:
                if self._stats.has_cycle:
                    return None
                return self._result.copy()

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = sum(len(edges) for edges in self._adj.values())

            # Copy in-degrees
            in_degree = dict(self._in_degree)

            # Initialize queue with zero in-degree nodes
            queue = deque([node for node in self._nodes if in_degree.get(node, 0) == 0])
            result = []

            while queue:
                node = queue.popleft()
                result.append(node)

                for neighbor in self._adj[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            # Check for cycle
            if len(result) != len(self._nodes):
                self._stats.has_cycle = True
                self._result = []
                self._built = True
                logger.warning("Topological sort: cycle detected")
                return None

            self._result = result
            self._stats.has_cycle = False
            self._stats.sort_length = len(result)
            self._built = True

            logger.info(f"Kahn topological sort: {len(result)} nodes")
            return result.copy()

    def sort_lexicographic(self) -> Optional[List[int]]:
        """
        Topological sort with smallest-first ordering.

        Uses priority queue instead of regular queue.
        """
        with self._lock:
            import heapq

            in_degree = dict(self._in_degree)
            heap = [node for node in self._nodes if in_degree.get(node, 0) == 0]
            heapq.heapify(heap)

            result = []

            while heap:
                node = heapq.heappop(heap)
                result.append(node)

                for neighbor in self._adj[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        heapq.heappush(heap, neighbor)

            if len(result) != len(self._nodes):
                return None

            return result

    def get_all_orderings(self, max_count: int = 1000) -> List[List[int]]:
        """
        Get all valid topological orderings.

        Args:
            max_count: Maximum orderings to return

        Returns:
            List of valid orderings
        """
        with self._lock:
            orderings = []

            def backtrack(in_degree: Dict[int, int], current: List[int]) -> bool:
                if len(orderings) >= max_count:
                    return True

                if len(current) == len(self._nodes):
                    orderings.append(current.copy())
                    return False

                for node in self._nodes:
                    if node not in current and in_degree.get(node, 0) == 0:
                        current.append(node)

                        # Decrease in-degrees
                        new_in_degree = in_degree.copy()
                        for neighbor in self._adj[node]:
                            new_in_degree[neighbor] -= 1

                        if backtrack(new_in_degree, current):
                            return True

                        current.pop()

                return False

            backtrack(dict(self._in_degree), [])
            return orderings

    def has_cycle(self) -> bool:
        """Check if graph has a cycle."""
        self.sort()
        return self._stats.has_cycle

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'node_count': self._stats.node_count,
            'edge_count': self._stats.edge_count,
            'has_cycle': self._stats.has_cycle,
            'sort_length': self._stats.sort_length
        }


# ============================================================================
# DFS-BASED TOPOLOGICAL SORT
# ============================================================================

class DFSTopSort:
    """
    DFS-based topological sort.

    Features:
    - O(V + E) complexity
    - Reverse post-order
    - Cycle detection via coloring

    "Ba'el finishes last first." — Ba'el
    """

    def __init__(self):
        """Initialize DFS topological sort."""
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._nodes: Set[int] = set()

        self._result: List[int] = []
        self._stats = TopSortStats()
        self._built = False
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add directed edge u → v."""
        with self._lock:
            self._built = False
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append(v)

    def sort(self) -> Optional[List[int]]:
        """
        Perform topological sort using DFS.

        Returns:
            Sorted list or None if cycle exists
        """
        with self._lock:
            if self._built:
                if self._stats.has_cycle:
                    return None
                return self._result.copy()

            self._stats.node_count = len(self._nodes)
            self._stats.edge_count = sum(len(edges) for edges in self._adj.values())

            # 0 = unvisited, 1 = in progress, 2 = completed
            color = {node: 0 for node in self._nodes}
            result = []
            has_cycle = False

            def dfs(node: int) -> bool:
                nonlocal has_cycle

                if color[node] == 1:
                    # Back edge = cycle
                    has_cycle = True
                    return False

                if color[node] == 2:
                    return True

                color[node] = 1  # In progress

                for neighbor in self._adj[node]:
                    if not dfs(neighbor):
                        return False

                color[node] = 2  # Completed
                result.append(node)
                return True

            for node in self._nodes:
                if color[node] == 0:
                    if not dfs(node):
                        break

            if has_cycle:
                self._stats.has_cycle = True
                self._result = []
                self._built = True
                return None

            # Reverse for topological order
            result.reverse()
            self._result = result
            self._stats.has_cycle = False
            self._stats.sort_length = len(result)
            self._built = True

            return result.copy()

    def has_cycle(self) -> bool:
        """Check if graph has a cycle."""
        self.sort()
        return self._stats.has_cycle


# ============================================================================
# PARALLEL TOPOLOGICAL SORT
# ============================================================================

class ParallelTopSort:
    """
    Identify parallel levels in topological order.

    Returns groups of nodes that can be processed in parallel.
    """

    def __init__(self):
        """Initialize parallel topological sort."""
        self._adj: Dict[int, List[int]] = defaultdict(list)
        self._in_degree: Dict[int, int] = defaultdict(int)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add directed edge u → v."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].append(v)
            self._in_degree[v] += 1

            if u not in self._in_degree:
                self._in_degree[u] = 0

    def get_levels(self) -> Optional[List[List[int]]]:
        """
        Get parallel processing levels.

        Returns:
            List of levels (each level can be processed in parallel)
        """
        with self._lock:
            in_degree = dict(self._in_degree)
            levels = []
            processed = 0

            while processed < len(self._nodes):
                # Current level: all nodes with in-degree 0
                level = [node for node in self._nodes
                        if in_degree.get(node, 0) == 0
                        and node not in sum(levels, [])]

                if not level:
                    # Cycle detected
                    return None

                levels.append(level)
                processed += len(level)

                # Update in-degrees
                for node in level:
                    for neighbor in self._adj[node]:
                        in_degree[neighbor] -= 1

            return levels

    def get_critical_path_length(self) -> int:
        """Get length of critical path (number of levels)."""
        levels = self.get_levels()
        return len(levels) if levels else -1


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_kahn_sort() -> KahnTopSort:
    """Create Kahn's topological sort."""
    return KahnTopSort()


def create_dfs_sort() -> DFSTopSort:
    """Create DFS topological sort."""
    return DFSTopSort()


def create_parallel_sort() -> ParallelTopSort:
    """Create parallel topological sort."""
    return ParallelTopSort()


def topological_sort(edges: List[Tuple[int, int]]) -> Optional[List[int]]:
    """
    Perform topological sort.

    Args:
        edges: List of (u, v) directed edges (u before v)

    Returns:
        Sorted list or None if cycle
    """
    sorter = KahnTopSort()
    for u, v in edges:
        sorter.add_edge(u, v)
    return sorter.sort()


def has_cycle(edges: List[Tuple[int, int]]) -> bool:
    """Check if directed graph has a cycle."""
    return topological_sort(edges) is None


def get_parallel_levels(edges: List[Tuple[int, int]]) -> Optional[List[List[int]]]:
    """Get parallel processing levels."""
    sorter = ParallelTopSort()
    for u, v in edges:
        sorter.add_edge(u, v)
    return sorter.get_levels()


def dependency_order(
    dependencies: Dict[int, List[int]]
) -> Optional[List[int]]:
    """
    Order items respecting dependencies.

    Args:
        dependencies: Dict mapping item → list of items it depends on

    Returns:
        Ordered list (dependencies first)
    """
    sorter = KahnTopSort()

    for item, deps in dependencies.items():
        for dep in deps:
            sorter.add_edge(dep, item)

    return sorter.sort()
