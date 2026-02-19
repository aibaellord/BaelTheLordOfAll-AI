"""
BAEL 2-SAT Solver Engine
========================

Boolean satisfiability for 2-CNF formulas.

"Ba'el determines the truth in polynomial time." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("BAEL.TwoSAT")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Literal:
    """Boolean literal."""
    variable: int
    negated: bool = False

    def __neg__(self) -> 'Literal':
        return Literal(self.variable, not self.negated)

    def __repr__(self) -> str:
        return f"{'¬' if self.negated else ''}x{self.variable}"

    def __hash__(self):
        return hash((self.variable, self.negated))

    def __eq__(self, other):
        if not isinstance(other, Literal):
            return False
        return self.variable == other.variable and self.negated == other.negated


@dataclass
class Clause:
    """2-SAT clause (disjunction of two literals)."""
    a: Literal
    b: Literal

    def __repr__(self) -> str:
        return f"({self.a} ∨ {self.b})"


@dataclass
class TwoSATStats:
    """2-SAT statistics."""
    variable_count: int = 0
    clause_count: int = 0
    scc_count: int = 0
    satisfiable: Optional[bool] = None


# ============================================================================
# 2-SAT SOLVER ENGINE
# ============================================================================

class TwoSATEngine:
    """
    2-SAT Solver using Strongly Connected Components.

    Features:
    - O(n + m) satisfiability check
    - O(n + m) solution construction
    - Implication graph analysis

    "Ba'el finds truth through implication." — Ba'el
    """

    def __init__(self, num_variables: int = 0):
        """
        Initialize 2-SAT solver.

        Args:
            num_variables: Number of boolean variables
        """
        self._num_vars = num_variables
        self._clauses: List[Clause] = []
        self._graph: Dict[int, List[int]] = defaultdict(list)
        self._reverse_graph: Dict[int, List[int]] = defaultdict(list)
        self._solution: Optional[List[bool]] = None
        self._stats = TwoSATStats()
        self._lock = threading.RLock()

        logger.debug(f"2-SAT solver initialized with {num_variables} variables")

    def _literal_to_node(self, lit: Literal) -> int:
        """Convert literal to node index."""
        if lit.negated:
            return self._num_vars + lit.variable
        return lit.variable

    def _node_to_literal(self, node: int) -> Literal:
        """Convert node index to literal."""
        if node >= self._num_vars:
            return Literal(node - self._num_vars, negated=True)
        return Literal(node, negated=False)

    def _negate_node(self, node: int) -> int:
        """Get negation of node."""
        if node >= self._num_vars:
            return node - self._num_vars
        return node + self._num_vars

    def add_clause(self, a: Literal, b: Literal) -> None:
        """
        Add clause (a ∨ b).

        Args:
            a: First literal
            b: Second literal
        """
        with self._lock:
            # Track max variable
            self._num_vars = max(self._num_vars, a.variable + 1, b.variable + 1)

            clause = Clause(a, b)
            self._clauses.append(clause)
            self._stats.clause_count += 1

            # Add implications: (a ∨ b) ≡ (¬a → b) ∧ (¬b → a)
            node_a = self._literal_to_node(a)
            node_b = self._literal_to_node(b)
            node_neg_a = self._negate_node(node_a)
            node_neg_b = self._negate_node(node_b)

            # ¬a → b
            self._graph[node_neg_a].append(node_b)
            self._reverse_graph[node_b].append(node_neg_a)

            # ¬b → a
            self._graph[node_neg_b].append(node_a)
            self._reverse_graph[node_a].append(node_neg_b)

    def add_or(self, a: Literal, b: Literal) -> None:
        """Add clause (a ∨ b)."""
        self.add_clause(a, b)

    def add_implication(self, a: Literal, b: Literal) -> None:
        """
        Add implication (a → b).
        Equivalent to (¬a ∨ b).
        """
        self.add_clause(-a, b)

    def add_must_be_true(self, a: Literal) -> None:
        """
        Force literal to be true.
        Adds clause (a ∨ a) ≡ a.
        """
        self.add_clause(a, a)

    def add_must_be_false(self, a: Literal) -> None:
        """Force literal to be false."""
        self.add_must_be_true(-a)

    def add_xor(self, a: Literal, b: Literal) -> None:
        """
        Add XOR constraint (a ⊕ b).
        Equivalent to (a ∨ b) ∧ (¬a ∨ ¬b).
        """
        self.add_clause(a, b)
        self.add_clause(-a, -b)

    def add_equivalence(self, a: Literal, b: Literal) -> None:
        """
        Add equivalence (a ↔ b).
        Equivalent to (a → b) ∧ (b → a).
        """
        self.add_implication(a, b)
        self.add_implication(b, a)

    def add_at_most_one(self, literals: List[Literal]) -> None:
        """
        At most one literal can be true.
        For each pair, add (¬a ∨ ¬b).
        """
        for i in range(len(literals)):
            for j in range(i + 1, len(literals)):
                self.add_clause(-literals[i], -literals[j])

    def solve(self) -> bool:
        """
        Check satisfiability and compute solution.

        Returns:
            True if satisfiable
        """
        with self._lock:
            self._stats.variable_count = self._num_vars

            if self._num_vars == 0:
                self._solution = []
                self._stats.satisfiable = True
                return True

            # Run Kosaraju's SCC algorithm
            num_nodes = 2 * self._num_vars

            # First DFS to get finish order
            visited = [False] * num_nodes
            order = []

            def dfs1(node: int) -> None:
                visited[node] = True
                for neighbor in self._graph.get(node, []):
                    if not visited[neighbor]:
                        dfs1(neighbor)
                order.append(node)

            for node in range(num_nodes):
                if not visited[node]:
                    dfs1(node)

            # Second DFS on reverse graph
            visited = [False] * num_nodes
            scc_id = [0] * num_nodes
            current_scc = 0

            def dfs2(node: int, scc: int) -> None:
                visited[node] = True
                scc_id[node] = scc
                for neighbor in self._reverse_graph.get(node, []):
                    if not visited[neighbor]:
                        dfs2(neighbor, scc)

            for node in reversed(order):
                if not visited[node]:
                    dfs2(node, current_scc)
                    current_scc += 1

            self._stats.scc_count = current_scc

            # Check satisfiability
            for var in range(self._num_vars):
                if scc_id[var] == scc_id[var + self._num_vars]:
                    # x and ¬x in same SCC - unsatisfiable
                    self._solution = None
                    self._stats.satisfiable = False
                    logger.info("2-SAT: UNSATISFIABLE")
                    return False

            # Build solution
            # Variable is true if ¬x has lower SCC id than x
            # (because of topological ordering)
            self._solution = [False] * self._num_vars

            for var in range(self._num_vars):
                # Higher SCC id = earlier in topological order = assigned true
                self._solution[var] = scc_id[var] > scc_id[var + self._num_vars]

            self._stats.satisfiable = True
            logger.info(f"2-SAT: SATISFIABLE with {self._num_vars} variables")

            return True

    def get_solution(self) -> Optional[List[bool]]:
        """
        Get satisfying assignment.

        Returns:
            List of boolean values for each variable, or None if unsatisfiable
        """
        if self._solution is None and self._stats.satisfiable is None:
            self.solve()
        return self._solution

    def evaluate(self, assignment: List[bool]) -> bool:
        """
        Evaluate formula with given assignment.

        Args:
            assignment: Boolean value for each variable

        Returns:
            True if all clauses satisfied
        """
        for clause in self._clauses:
            val_a = assignment[clause.a.variable]
            if clause.a.negated:
                val_a = not val_a

            val_b = assignment[clause.b.variable]
            if clause.b.negated:
                val_b = not val_b

            if not (val_a or val_b):
                return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            'variable_count': self._stats.variable_count,
            'clause_count': self._stats.clause_count,
            'scc_count': self._stats.scc_count,
            'satisfiable': self._stats.satisfiable
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_2sat(num_variables: int = 0) -> TwoSATEngine:
    """Create 2-SAT solver."""
    return TwoSATEngine(num_variables)


def lit(variable: int, negated: bool = False) -> Literal:
    """
    Create literal.

    Args:
        variable: Variable index (0-indexed)
        negated: Whether to negate

    Returns:
        Literal
    """
    return Literal(variable, negated)


def solve_2sat(clauses: List[Tuple[Tuple[int, bool], Tuple[int, bool]]]) -> Optional[List[bool]]:
    """
    Solve 2-SAT problem.

    Args:
        clauses: List of ((var1, neg1), (var2, neg2)) tuples

    Returns:
        Solution or None
    """
    if not clauses:
        return []

    # Find number of variables
    num_vars = 0
    for (v1, _), (v2, _) in clauses:
        num_vars = max(num_vars, v1 + 1, v2 + 1)

    solver = TwoSATEngine(num_vars)

    for (v1, n1), (v2, n2) in clauses:
        solver.add_clause(Literal(v1, n1), Literal(v2, n2))

    if solver.solve():
        return solver.get_solution()

    return None


def is_2sat_satisfiable(clauses: List[Tuple[Tuple[int, bool], Tuple[int, bool]]]) -> bool:
    """Check if 2-SAT formula is satisfiable."""
    return solve_2sat(clauses) is not None
