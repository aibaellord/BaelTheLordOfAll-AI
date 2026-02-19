"""
BAEL Graph Isomorphism Engine
=============================

Graph isomorphism detection and matching algorithms.

"Ba'el recognizes structural equivalence." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, auto

logger = logging.getLogger("BAEL.GraphIsomorphism")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class IsomorphismType(Enum):
    """Type of isomorphism."""
    FULL = auto()            # Complete graph isomorphism
    SUBGRAPH = auto()        # Subgraph isomorphism
    INDUCED_SUBGRAPH = auto() # Induced subgraph isomorphism


@dataclass
class Graph:
    """Simple graph representation."""
    vertices: int
    edges: List[Tuple[int, int]] = field(default_factory=list)
    directed: bool = False
    labels: Dict[int, Any] = field(default_factory=dict)
    edge_labels: Dict[Tuple[int, int], Any] = field(default_factory=dict)

    def adjacency_list(self) -> Dict[int, Set[int]]:
        """Get adjacency list representation."""
        adj: Dict[int, Set[int]] = {i: set() for i in range(self.vertices)}
        for u, v in self.edges:
            adj[u].add(v)
            if not self.directed:
                adj[v].add(u)
        return adj

    def degree(self, v: int) -> int:
        """Get degree of vertex."""
        return len(self.adjacency_list()[v])

    def degree_sequence(self) -> List[int]:
        """Get sorted degree sequence."""
        adj = self.adjacency_list()
        return sorted([len(adj[v]) for v in range(self.vertices)], reverse=True)


@dataclass
class IsomorphismResult:
    """Isomorphism result."""
    is_isomorphic: bool
    mapping: Optional[Dict[int, int]] = None  # G1 vertex -> G2 vertex
    all_mappings: List[Dict[int, int]] = field(default_factory=list)
    comparisons: int = 0


@dataclass
class VF2State:
    """State for VF2 algorithm."""
    core_1: Dict[int, int]  # G1 -> G2 mapping
    core_2: Dict[int, int]  # G2 -> G1 mapping
    in_1: Dict[int, int]    # Depth when vertex entered T_in for G1
    in_2: Dict[int, int]    # Depth when vertex entered T_in for G2
    out_1: Dict[int, int]   # Depth when vertex entered T_out for G1
    out_2: Dict[int, int]   # Depth when vertex entered T_out for G2
    depth: int = 0


# ============================================================================
# WEISFEILER-LEHMAN
# ============================================================================

class WeisfeilerLehman:
    """
    Weisfeiler-Lehman isomorphism test.

    Features:
    - O(n² log n) per iteration
    - Not complete but efficient
    - Good for most practical graphs

    "Ba'el refines vertex colors." — Ba'el
    """

    def __init__(self, iterations: int = 10):
        """Initialize WL test."""
        self._iterations = iterations
        self._lock = threading.RLock()

    def hash(self, graph: Graph) -> str:
        """
        Compute WL hash of graph.

        Useful for quick non-isomorphism detection.
        """
        with self._lock:
            n = graph.vertices
            adj = graph.adjacency_list()

            # Initial coloring (degree + vertex label if exists)
            colors = []
            for v in range(n):
                label = graph.labels.get(v, '')
                colors.append((len(adj[v]), str(label)))

            for _ in range(self._iterations):
                new_colors = []

                for v in range(n):
                    neighbor_colors = sorted([colors[u] for u in adj[v]])
                    new_colors.append((colors[v], tuple(neighbor_colors)))

                # Relabel
                unique = sorted(set(new_colors))
                color_map = {c: i for i, c in enumerate(unique)}
                colors = [(color_map[c],) for c in new_colors]

            # Canonical hash
            color_counts = defaultdict(int)
            for c in colors:
                color_counts[c] += 1

            return str(sorted(color_counts.items()))

    def might_be_isomorphic(self, g1: Graph, g2: Graph) -> bool:
        """
        Check if graphs might be isomorphic.

        Returns False if definitely not isomorphic.
        Returns True if possibly isomorphic (need further testing).
        """
        with self._lock:
            if g1.vertices != g2.vertices:
                return False

            if len(g1.edges) != len(g2.edges):
                return False

            if g1.degree_sequence() != g2.degree_sequence():
                return False

            return self.hash(g1) == self.hash(g2)


# ============================================================================
# VF2 ALGORITHM
# ============================================================================

class VF2Algorithm:
    """
    VF2 graph isomorphism algorithm.

    Features:
    - Complete algorithm (finds all isomorphisms)
    - O(n! n) worst case, but efficient in practice
    - Handles labeled graphs

    "Ba'el matches graphs completely." — Ba'el
    """

    def __init__(self):
        """Initialize VF2."""
        self._lock = threading.RLock()

    def is_isomorphic(
        self,
        g1: Graph,
        g2: Graph,
        find_all: bool = False
    ) -> IsomorphismResult:
        """
        Check if two graphs are isomorphic.

        Args:
            g1: First graph
            g2: Second graph
            find_all: If True, find all isomorphisms

        Returns:
            IsomorphismResult with mapping(s) if isomorphic
        """
        with self._lock:
            # Quick checks
            if g1.vertices != g2.vertices:
                return IsomorphismResult(is_isomorphic=False)

            if len(g1.edges) != len(g2.edges):
                return IsomorphismResult(is_isomorphic=False)

            if g1.degree_sequence() != g2.degree_sequence():
                return IsomorphismResult(is_isomorphic=False)

            n = g1.vertices
            adj1 = g1.adjacency_list()
            adj2 = g2.adjacency_list()

            # Initialize state
            state = VF2State(
                core_1={}, core_2={},
                in_1={}, in_2={},
                out_1={}, out_2={}
            )

            all_mappings = []
            comparisons = [0]

            def match(state: VF2State) -> bool:
                """Recursive matching."""
                comparisons[0] += 1

                if len(state.core_1) == n:
                    # Complete match found
                    all_mappings.append(dict(state.core_1))
                    return not find_all  # Continue searching if find_all

                # Get candidate pairs
                candidates = self._get_candidates(state, g1, g2, adj1, adj2)

                for v1, v2 in candidates:
                    if self._is_feasible(state, v1, v2, g1, g2, adj1, adj2):
                        # Add to mapping
                        new_state = self._update_state(state, v1, v2, adj1, adj2)

                        if match(new_state):
                            return True

                return False

            match(state)

            if all_mappings:
                return IsomorphismResult(
                    is_isomorphic=True,
                    mapping=all_mappings[0],
                    all_mappings=all_mappings,
                    comparisons=comparisons[0]
                )

            return IsomorphismResult(is_isomorphic=False, comparisons=comparisons[0])

    def _get_candidates(
        self,
        state: VF2State,
        g1: Graph,
        g2: Graph,
        adj1: Dict[int, Set[int]],
        adj2: Dict[int, Set[int]]
    ) -> List[Tuple[int, int]]:
        """Get candidate pairs for next matching."""
        n1, n2 = g1.vertices, g2.vertices

        # T_out sets
        t1_out = {v for v in state.out_1 if v not in state.core_1}
        t2_out = {v for v in state.out_2 if v not in state.core_2}

        if t1_out and t2_out:
            v1 = min(t1_out)
            candidates = [(v1, v2) for v2 in t2_out]
            return candidates

        # T_in sets
        t1_in = {v for v in state.in_1 if v not in state.core_1}
        t2_in = {v for v in state.in_2 if v not in state.core_2}

        if t1_in and t2_in:
            v1 = min(t1_in)
            candidates = [(v1, v2) for v2 in t2_in]
            return candidates

        # Disconnected vertices
        unmapped_1 = set(range(n1)) - set(state.core_1.keys())
        unmapped_2 = set(range(n2)) - set(state.core_2.keys())

        if unmapped_1 and unmapped_2:
            v1 = min(unmapped_1)
            candidates = [(v1, v2) for v2 in unmapped_2]
            return candidates

        return []

    def _is_feasible(
        self,
        state: VF2State,
        v1: int,
        v2: int,
        g1: Graph,
        g2: Graph,
        adj1: Dict[int, Set[int]],
        adj2: Dict[int, Set[int]]
    ) -> bool:
        """Check if candidate pair is feasible."""
        # Check labels
        if g1.labels.get(v1) != g2.labels.get(v2):
            return False

        # Check consistency with current mapping
        for u1 in adj1[v1]:
            if u1 in state.core_1:
                u2 = state.core_1[u1]
                if u2 not in adj2[v2]:
                    return False

        for u2 in adj2[v2]:
            if u2 in state.core_2:
                u1 = state.core_2[u2]
                if u1 not in adj1[v1]:
                    return False

        # Look-ahead pruning
        # Count neighbors in T_in, T_out, and neither

        def count_neighbors(v: int, adj: Dict[int, Set[int]],
                          core: Dict[int, int],
                          t_in: Dict[int, int],
                          t_out: Dict[int, int]) -> Tuple[int, int, int]:
            in_core = in_in = in_out = in_new = 0
            for u in adj[v]:
                if u in core:
                    in_core += 1
                elif u in t_in:
                    in_in += 1
                elif u in t_out:
                    in_out += 1
                else:
                    in_new += 1
            return in_in, in_out, in_new

        in1_in, in1_out, in1_new = count_neighbors(
            v1, adj1, state.core_1, state.in_1, state.out_1
        )
        in2_in, in2_out, in2_new = count_neighbors(
            v2, adj2, state.core_2, state.in_2, state.out_2
        )

        return in1_in <= in2_in and in1_out <= in2_out and in1_new <= in2_new

    def _update_state(
        self,
        state: VF2State,
        v1: int,
        v2: int,
        adj1: Dict[int, Set[int]],
        adj2: Dict[int, Set[int]]
    ) -> VF2State:
        """Create new state with added mapping."""
        new_depth = state.depth + 1

        new_state = VF2State(
            core_1=dict(state.core_1),
            core_2=dict(state.core_2),
            in_1=dict(state.in_1),
            in_2=dict(state.in_2),
            out_1=dict(state.out_1),
            out_2=dict(state.out_2),
            depth=new_depth
        )

        new_state.core_1[v1] = v2
        new_state.core_2[v2] = v1

        # Update T_in and T_out for G1
        for u in adj1[v1]:
            if u not in new_state.core_1:
                if u not in new_state.in_1:
                    new_state.in_1[u] = new_depth
                if u not in new_state.out_1:
                    new_state.out_1[u] = new_depth

        # Update T_in and T_out for G2
        for u in adj2[v2]:
            if u not in new_state.core_2:
                if u not in new_state.in_2:
                    new_state.in_2[u] = new_depth
                if u not in new_state.out_2:
                    new_state.out_2[u] = new_depth

        return new_state


# ============================================================================
# SUBGRAPH ISOMORPHISM
# ============================================================================

class SubgraphIsomorphism:
    """
    Subgraph isomorphism detection.

    Features:
    - Find if pattern exists in target graph
    - VF2-based algorithm

    "Ba'el finds patterns in graphs." — Ba'el
    """

    def __init__(self):
        """Initialize subgraph isomorphism."""
        self._lock = threading.RLock()

    def find_subgraph(
        self,
        pattern: Graph,
        target: Graph,
        find_all: bool = False
    ) -> IsomorphismResult:
        """
        Find pattern as subgraph of target.

        Returns mapping from pattern vertices to target vertices.
        """
        with self._lock:
            if pattern.vertices > target.vertices:
                return IsomorphismResult(is_isomorphic=False)

            if len(pattern.edges) > len(target.edges):
                return IsomorphismResult(is_isomorphic=False)

            adj_p = pattern.adjacency_list()
            adj_t = target.adjacency_list()

            all_mappings = []
            comparisons = [0]

            def backtrack(mapping: Dict[int, int], used: Set[int]) -> bool:
                comparisons[0] += 1

                if len(mapping) == pattern.vertices:
                    all_mappings.append(dict(mapping))
                    return not find_all

                v_p = len(mapping)  # Next pattern vertex to map

                for v_t in range(target.vertices):
                    if v_t in used:
                        continue

                    # Check if mapping is consistent
                    valid = True

                    # Check labels
                    if pattern.labels.get(v_p) != target.labels.get(v_t):
                        valid = False

                    # Check edges
                    if valid:
                        for u_p in adj_p[v_p]:
                            if u_p in mapping:
                                u_t = mapping[u_p]
                                if u_t not in adj_t[v_t]:
                                    valid = False
                                    break

                    if valid:
                        mapping[v_p] = v_t
                        used.add(v_t)

                        if backtrack(mapping, used):
                            return True

                        del mapping[v_p]
                        used.remove(v_t)

                return False

            backtrack({}, set())

            if all_mappings:
                return IsomorphismResult(
                    is_isomorphic=True,
                    mapping=all_mappings[0],
                    all_mappings=all_mappings,
                    comparisons=comparisons[0]
                )

            return IsomorphismResult(is_isomorphic=False, comparisons=comparisons[0])


# ============================================================================
# CANONICAL LABELING
# ============================================================================

class CanonicalLabeling:
    """
    Canonical labeling of graphs.

    Features:
    - Produces canonical form for comparison
    - Uses degree-based partitioning

    "Ba'el labels graphs canonically." — Ba'el
    """

    def __init__(self):
        """Initialize canonical labeling."""
        self._lock = threading.RLock()

    def canonical_form(self, graph: Graph) -> Tuple[List[Tuple[int, int]], str]:
        """
        Compute canonical form of graph.

        Returns:
            (canonical_edges, hash_string)
        """
        with self._lock:
            n = graph.vertices
            adj = graph.adjacency_list()

            # Partition by degree
            degree_map: Dict[int, List[int]] = defaultdict(list)
            for v in range(n):
                degree_map[len(adj[v])].append(v)

            # Sort partitions
            partitions = [sorted(degree_map[d]) for d in sorted(degree_map.keys())]

            # Create canonical ordering
            ordering = []
            for partition in partitions:
                ordering.extend(sorted(partition))

            # Create relabeling
            relabel = {v: i for i, v in enumerate(ordering)}

            # Create canonical edge list
            canonical_edges = []
            for u, v in graph.edges:
                new_u, new_v = relabel[u], relabel[v]
                if new_u > new_v:
                    new_u, new_v = new_v, new_u
                canonical_edges.append((new_u, new_v))

            canonical_edges.sort()

            # Create hash
            hash_str = f"{n}:{str(canonical_edges)}"

            return canonical_edges, hash_str

    def are_isomorphic_by_canonical(self, g1: Graph, g2: Graph) -> bool:
        """
        Check isomorphism using canonical form.

        Quick but not always complete.
        """
        with self._lock:
            _, hash1 = self.canonical_form(g1)
            _, hash2 = self.canonical_form(g2)
            return hash1 == hash2


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_weisfeiler_lehman(iterations: int = 10) -> WeisfeilerLehman:
    """Create Weisfeiler-Lehman tester."""
    return WeisfeilerLehman(iterations)


def create_vf2() -> VF2Algorithm:
    """Create VF2 algorithm."""
    return VF2Algorithm()


def create_subgraph_isomorphism() -> SubgraphIsomorphism:
    """Create subgraph isomorphism detector."""
    return SubgraphIsomorphism()


def create_canonical_labeling() -> CanonicalLabeling:
    """Create canonical labeling."""
    return CanonicalLabeling()


def graph_from_edges(
    n: int,
    edges: List[Tuple[int, int]],
    directed: bool = False
) -> Graph:
    """Create graph from edge list."""
    return Graph(vertices=n, edges=edges, directed=directed)


def are_isomorphic(
    n1: int,
    edges1: List[Tuple[int, int]],
    n2: int,
    edges2: List[Tuple[int, int]]
) -> bool:
    """Check if two graphs are isomorphic."""
    g1 = Graph(vertices=n1, edges=edges1)
    g2 = Graph(vertices=n2, edges=edges2)
    return VF2Algorithm().is_isomorphic(g1, g2).is_isomorphic


def find_subgraph(
    pattern_n: int,
    pattern_edges: List[Tuple[int, int]],
    target_n: int,
    target_edges: List[Tuple[int, int]]
) -> Optional[Dict[int, int]]:
    """Find pattern in target graph."""
    pattern = Graph(vertices=pattern_n, edges=pattern_edges)
    target = Graph(vertices=target_n, edges=target_edges)
    result = SubgraphIsomorphism().find_subgraph(pattern, target)
    return result.mapping if result.is_isomorphic else None


def graph_hash(n: int, edges: List[Tuple[int, int]]) -> str:
    """Compute Weisfeiler-Lehman hash of graph."""
    graph = Graph(vertices=n, edges=edges)
    return WeisfeilerLehman().hash(graph)
