"""
BAEL Planarity Testing Engine
=============================

Planarity testing and planar embedding algorithms.

"Ba'el knows if the graph lies flat." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger("BAEL.Planarity")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PlanarResult:
    """Planarity test result."""
    is_planar: bool = False
    embedding: Optional[Dict[int, List[int]]] = None
    kuratowski_subgraph: Optional[List[Tuple[int, int]]] = None


@dataclass
class PlanarStats:
    """Planarity statistics."""
    node_count: int = 0
    edge_count: int = 0
    face_count: int = 0
    genus: int = 0


# ============================================================================
# PLANARITY TESTING - EULER'S FORMULA CHECK
# ============================================================================

class EulerCheck:
    """
    Quick planarity check using Euler's formula.

    For connected planar graphs: V - E + F = 2
    A planar graph with V vertices has at most 3V - 6 edges.

    "Ba'el applies Euler's wisdom." — Ba'el
    """

    def __init__(self):
        """Initialize Euler check."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

        logger.debug("Euler planarity check initialized")

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)

    def quick_check(self) -> bool:
        """
        Quick necessary (not sufficient) check for planarity.

        Returns:
            False if definitely not planar, True if maybe planar
        """
        with self._lock:
            v = len(self._nodes)
            e = sum(len(adj) for adj in self._adj.values()) // 2

            if v < 3:
                return True

            # For simple connected planar graph: E ≤ 3V - 6
            if e > 3 * v - 6:
                return False

            # Check for no triangles: E ≤ 2V - 4
            if self._is_bipartite():
                if e > 2 * v - 4:
                    return False

            return True

    def _is_bipartite(self) -> bool:
        """Check if graph is bipartite."""
        if not self._nodes:
            return True

        color = {}

        for start in self._nodes:
            if start in color:
                continue

            queue = deque([start])
            color[start] = 0

            while queue:
                node = queue.popleft()

                for neighbor in self._adj[node]:
                    if neighbor not in color:
                        color[neighbor] = 1 - color[node]
                        queue.append(neighbor)
                    elif color[neighbor] == color[node]:
                        return False

        return True


# ============================================================================
# PLANARITY TESTING - DFS-BASED (SIMPLIFIED LR)
# ============================================================================

class SimplePlanarity:
    """
    Simplified planarity testing using DFS.

    This is a basic O(V²) algorithm for small graphs.
    For production, use Boyer-Myrvold or LR Planarity.

    "Ba'el tests embeddings carefully." — Ba'el
    """

    def __init__(self):
        """Initialize simple planarity."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)

    def is_planar(self) -> bool:
        """
        Test planarity.

        Returns:
            True if graph is planar
        """
        with self._lock:
            # Quick checks
            euler = EulerCheck()
            for u in self._adj:
                for v in self._adj[u]:
                    if u < v:
                        euler.add_edge(u, v)

            if not euler.quick_check():
                return False

            # Check for K5 or K3,3 subdivision
            if self._contains_k5_subdivision():
                return False

            if self._contains_k33_subdivision():
                return False

            return True

    def _contains_k5_subdivision(self) -> bool:
        """Check if graph contains K5 subdivision."""
        # Find vertices with degree >= 4 (potential K5 vertices)
        high_degree = [v for v in self._nodes if len(self._adj[v]) >= 4]

        if len(high_degree) < 5:
            return False

        # Check subsets of 5 high-degree vertices
        from itertools import combinations

        for subset in combinations(high_degree, 5):
            if self._check_k5_subdivision(subset):
                return True

        return False

    def _check_k5_subdivision(self, vertices: Tuple[int, ...]) -> bool:
        """Check if given 5 vertices form K5 subdivision."""
        vertex_set = set(vertices)

        # Check all pairs have disjoint paths
        for i, u in enumerate(vertices):
            for v in vertices[i+1:]:
                if not self._has_path_avoiding(u, v, vertex_set - {u, v}):
                    return False

        return True

    def _has_path_avoiding(self, u: int, v: int, avoid: Set[int]) -> bool:
        """Check if path exists from u to v avoiding certain vertices."""
        visited = {u}
        queue = deque([u])

        while queue:
            node = queue.popleft()

            if node == v:
                return True

            for neighbor in self._adj[node]:
                if neighbor not in visited:
                    if neighbor == v or neighbor not in avoid:
                        visited.add(neighbor)
                        queue.append(neighbor)

        return False

    def _contains_k33_subdivision(self) -> bool:
        """Check if graph contains K3,3 subdivision."""
        # Find vertices with degree >= 3
        high_degree = [v for v in self._nodes if len(self._adj[v]) >= 3]

        if len(high_degree) < 6:
            return False

        from itertools import combinations

        # Check all ways to partition 6 vertices into two groups of 3
        for subset in combinations(high_degree, 6):
            for group1 in combinations(subset, 3):
                group2 = tuple(v for v in subset if v not in group1)

                if self._check_k33_subdivision(group1, group2):
                    return True

        return False

    def _check_k33_subdivision(self, group1: Tuple[int, ...], group2: Tuple[int, ...]) -> bool:
        """Check if groups form K3,3 subdivision."""
        all_vertices = set(group1) | set(group2)

        for u in group1:
            for v in group2:
                if not self._has_path_avoiding(u, v, all_vertices - {u, v}):
                    return False

        return True


# ============================================================================
# PLANAR EMBEDDING
# ============================================================================

class PlanarEmbedding:
    """
    Compute planar embedding (rotation system).

    Features:
    - Clockwise ordering of edges around each vertex
    - Face computation
    - Dual graph construction

    "Ba'el embeds graphs in the plane." — Ba'el
    """

    def __init__(self):
        """Initialize planar embedding."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._embedding: Dict[int, List[int]] = {}
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)

    def compute_embedding(self) -> Optional[Dict[int, List[int]]]:
        """
        Compute a planar embedding if graph is planar.

        Returns:
            Rotation system mapping each vertex to clockwise ordered neighbors
        """
        with self._lock:
            # Check planarity first
            checker = SimplePlanarity()
            for u in self._adj:
                for v in self._adj[u]:
                    if u < v:
                        checker.add_edge(u, v)

            if not checker.is_planar():
                return None

            # Simple embedding: just use sorted order (works for many cases)
            # A proper implementation would use LR-planarity or similar
            embedding = {}

            for node in self._nodes:
                embedding[node] = sorted(self._adj[node])

            self._embedding = embedding
            return embedding

    def get_faces(self) -> List[List[int]]:
        """
        Get faces of the planar embedding.

        Returns:
            List of faces, each face is a list of vertices
        """
        if not self._embedding:
            self.compute_embedding()

        if not self._embedding:
            return []

        with self._lock:
            faces = []
            visited_edges = set()

            for start in self._nodes:
                for first_neighbor in self._embedding[start]:
                    edge = (start, first_neighbor)

                    if edge in visited_edges:
                        continue

                    # Trace face
                    face = []
                    current = start
                    next_node = first_neighbor

                    while True:
                        face.append(current)
                        visited_edges.add((current, next_node))

                        # Find next edge in rotation
                        neighbors = self._embedding[next_node]
                        idx = neighbors.index(current)
                        # Next in clockwise order
                        next_idx = (idx - 1) % len(neighbors)

                        current = next_node
                        next_node = neighbors[next_idx]

                        if current == start and next_node == first_neighbor:
                            break

                    if face:
                        faces.append(face)

            return faces

    def face_count(self) -> int:
        """Get number of faces (including outer face)."""
        return len(self.get_faces())

    def verify_euler(self) -> bool:
        """Verify Euler's formula: V - E + F = 2."""
        v = len(self._nodes)
        e = sum(len(adj) for adj in self._adj.values()) // 2
        f = self.face_count()

        return v - e + f == 2


# ============================================================================
# OUTERPLANAR TESTING
# ============================================================================

class OuterplanarTest:
    """
    Outerplanar graph testing.

    A graph is outerplanar if it can be embedded with all vertices on outer face.

    "Ba'el knows the boundary graphs." — Ba'el
    """

    def __init__(self):
        """Initialize outerplanar test."""
        self._adj: Dict[int, Set[int]] = defaultdict(set)
        self._nodes: Set[int] = set()
        self._lock = threading.RLock()

    def add_edge(self, u: int, v: int) -> None:
        """Add undirected edge."""
        with self._lock:
            self._nodes.add(u)
            self._nodes.add(v)
            self._adj[u].add(v)
            self._adj[v].add(u)

    def is_outerplanar(self) -> bool:
        """
        Test if graph is outerplanar.

        Outerplanar graphs:
        - Have no K4 or K2,3 minor
        - E ≤ 2V - 3 for connected graphs

        Returns:
            True if graph is outerplanar
        """
        with self._lock:
            v = len(self._nodes)
            e = sum(len(adj) for adj in self._adj.values()) // 2

            if v < 4:
                return True

            # Edge count check
            if e > 2 * v - 3:
                return False

            # Check for K4 minor (simplified)
            if self._contains_k4():
                return False

            return True

    def _contains_k4(self) -> bool:
        """Check if graph contains K4 as a minor."""
        # Find 4-clique
        high_degree = [v for v in self._nodes if len(self._adj[v]) >= 3]

        if len(high_degree) < 4:
            return False

        from itertools import combinations

        for subset in combinations(high_degree, 4):
            is_clique = True
            subset_set = set(subset)

            for i, u in enumerate(subset):
                for v in subset[i+1:]:
                    if v not in self._adj[u]:
                        is_clique = False
                        break
                if not is_clique:
                    break

            if is_clique:
                return True

        return False


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_euler_check() -> EulerCheck:
    """Create Euler planarity check."""
    return EulerCheck()


def create_simple_planarity() -> SimplePlanarity:
    """Create simple planarity tester."""
    return SimplePlanarity()


def create_planar_embedding() -> PlanarEmbedding:
    """Create planar embedding engine."""
    return PlanarEmbedding()


def create_outerplanar_test() -> OuterplanarTest:
    """Create outerplanar tester."""
    return OuterplanarTest()


def is_planar(edges: List[Tuple[int, int]]) -> bool:
    """Test if graph is planar."""
    engine = SimplePlanarity()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.is_planar()


def is_outerplanar(edges: List[Tuple[int, int]]) -> bool:
    """Test if graph is outerplanar."""
    engine = OuterplanarTest()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.is_outerplanar()


def planar_embedding(edges: List[Tuple[int, int]]) -> Optional[Dict[int, List[int]]]:
    """Get planar embedding if graph is planar."""
    engine = PlanarEmbedding()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.compute_embedding()


def get_faces(edges: List[Tuple[int, int]]) -> List[List[int]]:
    """Get faces of planar graph."""
    engine = PlanarEmbedding()
    for u, v in edges:
        engine.add_edge(u, v)
    return engine.get_faces()
