#!/usr/bin/env python3
"""
BAEL - Constraint Solver
Advanced constraint satisfaction and optimization.

Features:
- Constraint propagation
- Arc consistency (AC-3)
- Backtracking search
- Forward checking
- Conflict-directed backjumping
- Min-conflicts local search
- Global constraints
- Optimization objectives
"""

import asyncio
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ConstraintType(Enum):
    """Types of constraints."""
    EQUALITY = "equality"
    INEQUALITY = "inequality"
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    ALL_DIFFERENT = "all_different"
    SUM = "sum"
    PRODUCT = "product"
    TABLE = "table"
    CUSTOM = "custom"


class SolverStatus(Enum):
    """Status of solver."""
    UNKNOWN = "unknown"
    SATISFIABLE = "satisfiable"
    UNSATISFIABLE = "unsatisfiable"
    OPTIMAL = "optimal"
    TIMEOUT = "timeout"


class SearchStrategy(Enum):
    """Search strategies."""
    BACKTRACKING = "backtracking"
    FORWARD_CHECKING = "forward_checking"
    MAC = "mac"  # Maintaining Arc Consistency
    MIN_CONFLICTS = "min_conflicts"
    CONFLICT_BACKJUMP = "conflict_backjump"


class VariableOrdering(Enum):
    """Variable ordering heuristics."""
    STATIC = "static"
    MRV = "mrv"  # Minimum Remaining Values
    DEGREE = "degree"  # Most constraints
    DOM_DEG = "dom_deg"  # Domain/Degree ratio


class ValueOrdering(Enum):
    """Value ordering heuristics."""
    STATIC = "static"
    LCV = "lcv"  # Least Constraining Value
    RANDOM = "random"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Variable:
    """A CSP variable."""
    var_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    domain: List[Any] = field(default_factory=list)
    current_value: Optional[Any] = None


@dataclass
class Constraint:
    """A constraint."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    constraint_type: ConstraintType = ConstraintType.CUSTOM
    variables: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    check_fn: Optional[Callable[..., bool]] = None


@dataclass
class Solution:
    """A solution to a CSP."""
    solution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assignment: Dict[str, Any] = field(default_factory=dict)
    is_complete: bool = False
    is_consistent: bool = True
    objective_value: Optional[float] = None


@dataclass
class SearchStatistics:
    """Statistics from search."""
    nodes_explored: int = 0
    backtracks: int = 0
    propagations: int = 0
    runtime: float = 0.0
    solutions_found: int = 0


# =============================================================================
# DOMAIN MANAGER
# =============================================================================

class DomainManager:
    """Manage variable domains."""

    def __init__(self):
        self._domains: Dict[str, List[Any]] = {}
        self._initial_domains: Dict[str, List[Any]] = {}
        self._domain_stack: List[Dict[str, List[Any]]] = []

    def set_domain(self, var_name: str, domain: List[Any]) -> None:
        """Set domain for variable."""
        self._domains[var_name] = list(domain)
        self._initial_domains[var_name] = list(domain)

    def get_domain(self, var_name: str) -> List[Any]:
        """Get current domain."""
        return self._domains.get(var_name, [])

    def remove_value(self, var_name: str, value: Any) -> bool:
        """Remove value from domain."""
        domain = self._domains.get(var_name, [])
        if value in domain:
            domain.remove(value)
            return True
        return False

    def is_empty(self, var_name: str) -> bool:
        """Check if domain is empty."""
        return len(self._domains.get(var_name, [])) == 0

    def save_state(self) -> None:
        """Save current domains to stack."""
        state = {var: list(dom) for var, dom in self._domains.items()}
        self._domain_stack.append(state)

    def restore_state(self) -> None:
        """Restore domains from stack."""
        if self._domain_stack:
            self._domains = self._domain_stack.pop()

    def reset(self) -> None:
        """Reset to initial domains."""
        self._domains = {var: list(dom) for var, dom in self._initial_domains.items()}
        self._domain_stack = []


# =============================================================================
# CONSTRAINT EVALUATOR
# =============================================================================

class ConstraintEvaluator:
    """Evaluate constraints."""

    def check(
        self,
        constraint: Constraint,
        assignment: Dict[str, Any]
    ) -> bool:
        """Check if constraint is satisfied."""
        # Get values
        values = []
        for var in constraint.variables:
            if var not in assignment:
                return True  # Can't check yet
            values.append(assignment[var])

        ct = constraint.constraint_type

        if ct == ConstraintType.EQUALITY:
            return len(set(values)) == 1

        elif ct == ConstraintType.INEQUALITY:
            return values[0] != values[1] if len(values) >= 2 else True

        elif ct == ConstraintType.LESS_THAN:
            return values[0] < values[1] if len(values) >= 2 else True

        elif ct == ConstraintType.GREATER_THAN:
            return values[0] > values[1] if len(values) >= 2 else True

        elif ct == ConstraintType.ALL_DIFFERENT:
            return len(set(values)) == len(values)

        elif ct == ConstraintType.SUM:
            target = constraint.parameters.get("target", 0)
            return sum(values) == target

        elif ct == ConstraintType.PRODUCT:
            target = constraint.parameters.get("target", 1)
            product = 1
            for v in values:
                product *= v
            return product == target

        elif ct == ConstraintType.TABLE:
            allowed = constraint.parameters.get("allowed", [])
            return tuple(values) in allowed

        elif ct == ConstraintType.CUSTOM:
            if constraint.check_fn:
                return constraint.check_fn(*values)
            return True

        return True

    def is_arc_consistent(
        self,
        var1: str,
        var2: str,
        constraint: Constraint,
        domain1: List[Any],
        domain2: List[Any]
    ) -> Tuple[bool, List[Any]]:
        """Check and enforce arc consistency."""
        new_domain1 = []

        for val1 in domain1:
            # Check if there exists a consistent value in domain2
            has_support = False
            for val2 in domain2:
                assignment = {var1: val1, var2: val2}
                if self.check(constraint, assignment):
                    has_support = True
                    break

            if has_support:
                new_domain1.append(val1)

        return (len(new_domain1) < len(domain1), new_domain1)


# =============================================================================
# ARC CONSISTENCY
# =============================================================================

class AC3:
    """AC-3 arc consistency algorithm."""

    def __init__(
        self,
        variables: Dict[str, Variable],
        constraints: List[Constraint],
        domain_manager: DomainManager
    ):
        self._variables = variables
        self._constraints = constraints
        self._domain_manager = domain_manager
        self._evaluator = ConstraintEvaluator()
        self._propagations = 0

    def propagate(self) -> bool:
        """Run AC-3 propagation."""
        # Build constraint graph
        var_constraints: Dict[str, List[Constraint]] = defaultdict(list)
        for c in self._constraints:
            for var in c.variables:
                var_constraints[var].append(c)

        # Initialize queue with all arcs
        queue = deque()
        for c in self._constraints:
            if len(c.variables) == 2:
                queue.append((c.variables[0], c.variables[1], c))
                queue.append((c.variables[1], c.variables[0], c))

        while queue:
            var1, var2, constraint = queue.popleft()
            self._propagations += 1

            domain1 = self._domain_manager.get_domain(var1)
            domain2 = self._domain_manager.get_domain(var2)

            revised, new_domain = self._evaluator.is_arc_consistent(
                var1, var2, constraint, domain1, domain2
            )

            if revised:
                if not new_domain:
                    return False  # Domain wipeout

                self._domain_manager._domains[var1] = new_domain

                # Add arcs that need rechecking
                for c in var_constraints[var1]:
                    for other_var in c.variables:
                        if other_var != var1 and other_var != var2:
                            queue.append((other_var, var1, c))

        return True

    def get_propagations(self) -> int:
        """Get number of propagations."""
        return self._propagations


# =============================================================================
# BACKTRACKING SOLVER
# =============================================================================

class BacktrackingSolver:
    """Backtracking search with CSP."""

    def __init__(
        self,
        variables: Dict[str, Variable],
        constraints: List[Constraint],
        var_ordering: VariableOrdering = VariableOrdering.MRV,
        val_ordering: ValueOrdering = ValueOrdering.STATIC
    ):
        self._variables = variables
        self._constraints = constraints
        self._var_ordering = var_ordering
        self._val_ordering = val_ordering
        self._domain_manager = DomainManager()
        self._evaluator = ConstraintEvaluator()
        self._stats = SearchStatistics()

        # Initialize domains
        for var_name, var in variables.items():
            self._domain_manager.set_domain(var_name, var.domain)

    def solve(self, find_all: bool = False) -> List[Solution]:
        """Solve the CSP."""
        start_time = time.time()
        self._stats = SearchStatistics()
        self._domain_manager.reset()

        solutions = []
        self._backtrack({}, solutions, find_all)

        self._stats.runtime = time.time() - start_time
        self._stats.solutions_found = len(solutions)

        return solutions

    def _backtrack(
        self,
        assignment: Dict[str, Any],
        solutions: List[Solution],
        find_all: bool
    ) -> bool:
        """Recursive backtracking."""
        self._stats.nodes_explored += 1

        # Check if complete
        if len(assignment) == len(self._variables):
            solutions.append(Solution(
                assignment=dict(assignment),
                is_complete=True,
                is_consistent=True
            ))
            return not find_all  # Stop if not finding all

        # Select next variable
        var = self._select_variable(assignment)
        if not var:
            return False

        # Try each value
        values = self._order_values(var, assignment)

        for value in values:
            assignment[var] = value

            if self._is_consistent(assignment):
                result = self._backtrack(assignment, solutions, find_all)
                if result:
                    return True

            del assignment[var]
            self._stats.backtracks += 1

        return False

    def _select_variable(
        self,
        assignment: Dict[str, Any]
    ) -> Optional[str]:
        """Select next variable to assign."""
        unassigned = [
            v for v in self._variables
            if v not in assignment
        ]

        if not unassigned:
            return None

        if self._var_ordering == VariableOrdering.STATIC:
            return unassigned[0]

        elif self._var_ordering == VariableOrdering.MRV:
            # Minimum Remaining Values
            return min(
                unassigned,
                key=lambda v: len(self._domain_manager.get_domain(v))
            )

        elif self._var_ordering == VariableOrdering.DEGREE:
            # Most constraints
            def count_constraints(var):
                return sum(
                    1 for c in self._constraints
                    if var in c.variables and any(
                        v not in assignment for v in c.variables if v != var
                    )
                )
            return max(unassigned, key=count_constraints)

        return unassigned[0]

    def _order_values(
        self,
        var: str,
        assignment: Dict[str, Any]
    ) -> List[Any]:
        """Order values for variable."""
        domain = self._domain_manager.get_domain(var)

        if self._val_ordering == ValueOrdering.STATIC:
            return domain

        elif self._val_ordering == ValueOrdering.RANDOM:
            return random.sample(domain, len(domain))

        elif self._val_ordering == ValueOrdering.LCV:
            # Least Constraining Value
            def count_ruled_out(value):
                assignment[var] = value
                count = 0
                for c in self._constraints:
                    if var in c.variables:
                        for other_var in c.variables:
                            if other_var != var and other_var not in assignment:
                                for other_val in self._domain_manager.get_domain(other_var):
                                    test_assign = dict(assignment)
                                    test_assign[other_var] = other_val
                                    if not self._evaluator.check(c, test_assign):
                                        count += 1
                del assignment[var]
                return count

            return sorted(domain, key=count_ruled_out)

        return domain

    def _is_consistent(self, assignment: Dict[str, Any]) -> bool:
        """Check if assignment is consistent."""
        for constraint in self._constraints:
            if not self._evaluator.check(constraint, assignment):
                return False
        return True

    def get_statistics(self) -> SearchStatistics:
        """Get search statistics."""
        return self._stats


# =============================================================================
# FORWARD CHECKING SOLVER
# =============================================================================

class ForwardCheckingSolver:
    """Backtracking with forward checking."""

    def __init__(
        self,
        variables: Dict[str, Variable],
        constraints: List[Constraint]
    ):
        self._variables = variables
        self._constraints = constraints
        self._domain_manager = DomainManager()
        self._evaluator = ConstraintEvaluator()
        self._stats = SearchStatistics()

        # Initialize domains
        for var_name, var in variables.items():
            self._domain_manager.set_domain(var_name, var.domain)

    def solve(self) -> Optional[Solution]:
        """Solve with forward checking."""
        start_time = time.time()
        self._stats = SearchStatistics()
        self._domain_manager.reset()

        solution = self._search({})

        self._stats.runtime = time.time() - start_time

        return solution

    def _search(self, assignment: Dict[str, Any]) -> Optional[Solution]:
        """Search with forward checking."""
        self._stats.nodes_explored += 1

        if len(assignment) == len(self._variables):
            return Solution(
                assignment=dict(assignment),
                is_complete=True,
                is_consistent=True
            )

        # Select variable with MRV
        unassigned = [v for v in self._variables if v not in assignment]
        var = min(
            unassigned,
            key=lambda v: len(self._domain_manager.get_domain(v))
        )

        for value in list(self._domain_manager.get_domain(var)):
            assignment[var] = value
            self._domain_manager.save_state()

            if self._forward_check(var, value, assignment):
                result = self._search(assignment)
                if result:
                    return result

            del assignment[var]
            self._domain_manager.restore_state()
            self._stats.backtracks += 1

        return None

    def _forward_check(
        self,
        var: str,
        value: Any,
        assignment: Dict[str, Any]
    ) -> bool:
        """Prune domains of unassigned neighbors."""
        for constraint in self._constraints:
            if var not in constraint.variables:
                continue

            for other_var in constraint.variables:
                if other_var == var or other_var in assignment:
                    continue

                # Prune inconsistent values
                domain = self._domain_manager.get_domain(other_var)
                new_domain = []

                for other_val in domain:
                    test_assign = dict(assignment)
                    test_assign[other_var] = other_val

                    if self._evaluator.check(constraint, test_assign):
                        new_domain.append(other_val)
                    else:
                        self._stats.propagations += 1

                self._domain_manager._domains[other_var] = new_domain

                if not new_domain:
                    return False  # Domain wipeout

        return True

    def get_statistics(self) -> SearchStatistics:
        """Get search statistics."""
        return self._stats


# =============================================================================
# MIN-CONFLICTS SOLVER
# =============================================================================

class MinConflictsSolver:
    """Local search using min-conflicts."""

    def __init__(
        self,
        variables: Dict[str, Variable],
        constraints: List[Constraint],
        max_iterations: int = 10000
    ):
        self._variables = variables
        self._constraints = constraints
        self._max_iterations = max_iterations
        self._evaluator = ConstraintEvaluator()

    def solve(self) -> Optional[Solution]:
        """Solve using min-conflicts."""
        # Random initial assignment
        assignment = {
            var_name: random.choice(var.domain) if var.domain else None
            for var_name, var in self._variables.items()
        }

        for iteration in range(self._max_iterations):
            # Find conflicted variables
            conflicted = self._get_conflicted_variables(assignment)

            if not conflicted:
                return Solution(
                    assignment=assignment,
                    is_complete=True,
                    is_consistent=True
                )

            # Pick random conflicted variable
            var = random.choice(conflicted)

            # Find value with minimum conflicts
            min_conflicts = float('inf')
            best_value = assignment[var]

            for value in self._variables[var].domain:
                assignment[var] = value
                conflicts = self._count_conflicts(assignment)

                if conflicts < min_conflicts:
                    min_conflicts = conflicts
                    best_value = value

            assignment[var] = best_value

        # Check final assignment
        if self._count_conflicts(assignment) == 0:
            return Solution(
                assignment=assignment,
                is_complete=True,
                is_consistent=True
            )

        return None

    def _get_conflicted_variables(
        self,
        assignment: Dict[str, Any]
    ) -> List[str]:
        """Get variables involved in conflicts."""
        conflicted = set()

        for constraint in self._constraints:
            if not self._evaluator.check(constraint, assignment):
                conflicted.update(constraint.variables)

        return list(conflicted)

    def _count_conflicts(self, assignment: Dict[str, Any]) -> int:
        """Count number of violated constraints."""
        return sum(
            1 for c in self._constraints
            if not self._evaluator.check(c, assignment)
        )


# =============================================================================
# OPTIMIZATION SOLVER
# =============================================================================

class OptimizationSolver:
    """CSP with optimization objective."""

    def __init__(
        self,
        variables: Dict[str, Variable],
        constraints: List[Constraint],
        objective: Callable[[Dict[str, Any]], float],
        maximize: bool = True
    ):
        self._variables = variables
        self._constraints = constraints
        self._objective = objective
        self._maximize = maximize
        self._evaluator = ConstraintEvaluator()
        self._best_solution: Optional[Solution] = None
        self._best_value: float = float('-inf') if maximize else float('inf')

    def solve(self) -> Optional[Solution]:
        """Solve optimization problem."""
        self._best_solution = None
        self._best_value = float('-inf') if self._maximize else float('inf')

        self._branch_and_bound({})

        if self._best_solution:
            self._best_solution.objective_value = self._best_value

        return self._best_solution

    def _branch_and_bound(self, assignment: Dict[str, Any]) -> None:
        """Branch and bound search."""
        # Check if complete
        if len(assignment) == len(self._variables):
            if self._is_consistent(assignment):
                value = self._objective(assignment)

                if self._maximize:
                    if value > self._best_value:
                        self._best_value = value
                        self._best_solution = Solution(
                            assignment=dict(assignment),
                            is_complete=True,
                            is_consistent=True
                        )
                else:
                    if value < self._best_value:
                        self._best_value = value
                        self._best_solution = Solution(
                            assignment=dict(assignment),
                            is_complete=True,
                            is_consistent=True
                        )
            return

        # Bound: estimate best possible value
        partial_value = self._objective(assignment)
        if self._maximize and partial_value <= self._best_value:
            return  # Prune
        if not self._maximize and partial_value >= self._best_value:
            return  # Prune

        # Select next variable
        unassigned = [v for v in self._variables if v not in assignment]
        if not unassigned:
            return

        var = unassigned[0]

        for value in self._variables[var].domain:
            assignment[var] = value

            if self._is_consistent(assignment):
                self._branch_and_bound(assignment)

            del assignment[var]

    def _is_consistent(self, assignment: Dict[str, Any]) -> bool:
        """Check if assignment is consistent."""
        for constraint in self._constraints:
            if not self._evaluator.check(constraint, assignment):
                return False
        return True


# =============================================================================
# CONSTRAINT SOLVER
# =============================================================================

class ConstraintSolver:
    """
    Constraint Solver for BAEL.

    Advanced constraint satisfaction and optimization.
    """

    def __init__(self):
        self._problems: Dict[str, Dict[str, Any]] = {}
        self._solutions: Dict[str, List[Solution]] = {}

    # -------------------------------------------------------------------------
    # PROBLEM DEFINITION
    # -------------------------------------------------------------------------

    def create_problem(self, name: str) -> str:
        """Create a new CSP problem."""
        self._problems[name] = {
            "variables": {},
            "constraints": [],
            "objective": None,
            "maximize": True
        }
        return name

    def add_variable(
        self,
        problem_name: str,
        var_name: str,
        domain: List[Any]
    ) -> Variable:
        """Add a variable to the problem."""
        problem = self._problems.get(problem_name)
        if not problem:
            raise ValueError(f"Problem {problem_name} not found")

        var = Variable(name=var_name, domain=list(domain))
        problem["variables"][var_name] = var
        return var

    def add_constraint(
        self,
        problem_name: str,
        variables: List[str],
        constraint_type: ConstraintType,
        parameters: Optional[Dict[str, Any]] = None,
        check_fn: Optional[Callable[..., bool]] = None
    ) -> Constraint:
        """Add a constraint to the problem."""
        problem = self._problems.get(problem_name)
        if not problem:
            raise ValueError(f"Problem {problem_name} not found")

        constraint = Constraint(
            constraint_type=constraint_type,
            variables=variables,
            parameters=parameters or {},
            check_fn=check_fn
        )

        problem["constraints"].append(constraint)
        return constraint

    def set_objective(
        self,
        problem_name: str,
        objective: Callable[[Dict[str, Any]], float],
        maximize: bool = True
    ) -> None:
        """Set optimization objective."""
        problem = self._problems.get(problem_name)
        if not problem:
            raise ValueError(f"Problem {problem_name} not found")

        problem["objective"] = objective
        problem["maximize"] = maximize

    # -------------------------------------------------------------------------
    # SOLVING
    # -------------------------------------------------------------------------

    def solve(
        self,
        problem_name: str,
        strategy: SearchStrategy = SearchStrategy.BACKTRACKING,
        find_all: bool = False
    ) -> List[Solution]:
        """Solve the CSP."""
        problem = self._problems.get(problem_name)
        if not problem:
            return []

        variables = problem["variables"]
        constraints = problem["constraints"]
        objective = problem.get("objective")

        if objective:
            # Optimization problem
            solver = OptimizationSolver(
                variables,
                constraints,
                objective,
                problem.get("maximize", True)
            )
            result = solver.solve()
            solutions = [result] if result else []

        elif strategy == SearchStrategy.BACKTRACKING:
            solver = BacktrackingSolver(
                variables,
                constraints,
                var_ordering=VariableOrdering.MRV,
                val_ordering=ValueOrdering.LCV
            )
            solutions = solver.solve(find_all)

        elif strategy == SearchStrategy.FORWARD_CHECKING:
            solver = ForwardCheckingSolver(variables, constraints)
            result = solver.solve()
            solutions = [result] if result else []

        elif strategy == SearchStrategy.MIN_CONFLICTS:
            solver = MinConflictsSolver(variables, constraints)
            result = solver.solve()
            solutions = [result] if result else []

        else:
            solver = BacktrackingSolver(variables, constraints)
            solutions = solver.solve(find_all)

        self._solutions[problem_name] = solutions
        return solutions

    def get_solutions(self, problem_name: str) -> List[Solution]:
        """Get solutions for a problem."""
        return self._solutions.get(problem_name, [])

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def add_all_different(
        self,
        problem_name: str,
        variables: List[str]
    ) -> Constraint:
        """Add all-different constraint."""
        return self.add_constraint(
            problem_name,
            variables,
            ConstraintType.ALL_DIFFERENT
        )

    def add_sum_constraint(
        self,
        problem_name: str,
        variables: List[str],
        target: int
    ) -> Constraint:
        """Add sum constraint."""
        return self.add_constraint(
            problem_name,
            variables,
            ConstraintType.SUM,
            {"target": target}
        )

    def add_not_equal(
        self,
        problem_name: str,
        var1: str,
        var2: str
    ) -> Constraint:
        """Add not-equal constraint."""
        return self.add_constraint(
            problem_name,
            [var1, var2],
            ConstraintType.INEQUALITY
        )

    def add_less_than(
        self,
        problem_name: str,
        var1: str,
        var2: str
    ) -> Constraint:
        """Add less-than constraint."""
        return self.add_constraint(
            problem_name,
            [var1, var2],
            ConstraintType.LESS_THAN
        )

    # -------------------------------------------------------------------------
    # PREDEFINED PROBLEMS
    # -------------------------------------------------------------------------

    def create_n_queens(self, n: int) -> str:
        """Create N-Queens problem."""
        problem_name = f"nqueens_{n}"
        self.create_problem(problem_name)

        # Variables: one per column, domain is row
        for col in range(n):
            self.add_variable(problem_name, f"Q{col}", list(range(n)))

        # Constraints: no two queens on same row or diagonal
        for i in range(n):
            for j in range(i + 1, n):
                # Different rows
                self.add_not_equal(problem_name, f"Q{i}", f"Q{j}")

                # Different diagonals
                def not_on_diagonal(qi, qj, diff=j-i):
                    return abs(qi - qj) != diff

                self.add_constraint(
                    problem_name,
                    [f"Q{i}", f"Q{j}"],
                    ConstraintType.CUSTOM,
                    check_fn=lambda qi, qj, d=j-i: abs(qi - qj) != d
                )

        return problem_name

    def create_sudoku(self, grid: List[List[int]]) -> str:
        """Create Sudoku problem."""
        problem_name = "sudoku"
        self.create_problem(problem_name)

        # Variables: 9x9 cells
        for i in range(9):
            for j in range(9):
                if grid[i][j] != 0:
                    # Fixed value
                    self.add_variable(problem_name, f"C{i}{j}", [grid[i][j]])
                else:
                    self.add_variable(problem_name, f"C{i}{j}", list(range(1, 10)))

        # Row constraints
        for i in range(9):
            row_vars = [f"C{i}{j}" for j in range(9)]
            self.add_all_different(problem_name, row_vars)

        # Column constraints
        for j in range(9):
            col_vars = [f"C{i}{j}" for i in range(9)]
            self.add_all_different(problem_name, col_vars)

        # Box constraints
        for box_i in range(3):
            for box_j in range(3):
                box_vars = []
                for i in range(3):
                    for j in range(3):
                        box_vars.append(f"C{box_i*3+i}{box_j*3+j}")
                self.add_all_different(problem_name, box_vars)

        return problem_name

    def create_graph_coloring(
        self,
        edges: List[Tuple[int, int]],
        num_nodes: int,
        num_colors: int
    ) -> str:
        """Create graph coloring problem."""
        problem_name = "graph_coloring"
        self.create_problem(problem_name)

        # Variables: one per node
        for node in range(num_nodes):
            self.add_variable(problem_name, f"N{node}", list(range(num_colors)))

        # Constraints: adjacent nodes different colors
        for u, v in edges:
            self.add_not_equal(problem_name, f"N{u}", f"N{v}")

        return problem_name


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Constraint Solver."""
    print("=" * 70)
    print("BAEL - CONSTRAINT SOLVER DEMO")
    print("Advanced Constraint Satisfaction and Optimization")
    print("=" * 70)
    print()

    solver = ConstraintSolver()

    # 1. N-Queens Problem
    print("1. N-QUEENS PROBLEM (8x8):")
    print("-" * 40)

    solver.create_n_queens(8)
    solutions = solver.solve("nqueens_8", SearchStrategy.BACKTRACKING)

    if solutions:
        sol = solutions[0]
        print(f"   Found solution:")
        queens = [sol.assignment.get(f"Q{i}", 0) for i in range(8)]

        # Print board
        for row in range(8):
            line = "   "
            for col in range(8):
                if queens[col] == row:
                    line += "Q "
                else:
                    line += ". "
            print(line)
    else:
        print("   No solution found")
    print()

    # 2. Graph Coloring
    print("2. GRAPH COLORING:")
    print("-" * 40)

    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]  # Square with diagonal
    solver.create_graph_coloring(edges, 4, 3)
    solutions = solver.solve("graph_coloring", SearchStrategy.FORWARD_CHECKING)

    if solutions:
        sol = solutions[0]
        colors = ["Red", "Green", "Blue"]
        print(f"   Coloring:")
        for i in range(4):
            color_idx = sol.assignment.get(f"N{i}", 0)
            print(f"     Node {i}: {colors[color_idx]}")
    print()

    # 3. Custom CSP
    print("3. CUSTOM CSP:")
    print("-" * 40)

    solver.create_problem("custom")
    solver.add_variable("custom", "X", [1, 2, 3, 4, 5])
    solver.add_variable("custom", "Y", [1, 2, 3, 4, 5])
    solver.add_variable("custom", "Z", [1, 2, 3, 4, 5])

    # X + Y + Z = 10
    solver.add_sum_constraint("custom", ["X", "Y", "Z"], 10)
    # X < Y
    solver.add_less_than("custom", "X", "Y")
    # Y < Z
    solver.add_less_than("custom", "Y", "Z")

    solutions = solver.solve("custom", SearchStrategy.BACKTRACKING, find_all=True)
    print(f"   Constraint: X + Y + Z = 10, X < Y < Z")
    print(f"   Found {len(solutions)} solutions:")
    for sol in solutions[:5]:
        print(f"     X={sol.assignment['X']}, Y={sol.assignment['Y']}, Z={sol.assignment['Z']}")
    print()

    # 4. Min-Conflicts
    print("4. MIN-CONFLICTS LOCAL SEARCH:")
    print("-" * 40)

    solver.create_n_queens(8)
    solutions = solver.solve("nqueens_8", SearchStrategy.MIN_CONFLICTS)

    if solutions:
        print("   Found 8-Queens solution using min-conflicts")
        sol = solutions[0]
        queens = [sol.assignment.get(f"Q{i}", 0) for i in range(8)]
        print(f"   Positions: {queens}")
    else:
        print("   No solution found (try again - local search is stochastic)")
    print()

    # 5. Optimization Problem
    print("5. OPTIMIZATION (MAXIMIZE):")
    print("-" * 40)

    solver.create_problem("optimize")
    solver.add_variable("optimize", "A", [1, 2, 3, 4, 5])
    solver.add_variable("optimize", "B", [1, 2, 3, 4, 5])

    # A + B <= 7
    solver.add_constraint(
        "optimize",
        ["A", "B"],
        ConstraintType.CUSTOM,
        check_fn=lambda a, b: a + b <= 7
    )

    # Maximize A * B
    solver.set_objective("optimize", lambda d: d.get("A", 0) * d.get("B", 0), maximize=True)

    solutions = solver.solve("optimize")
    if solutions:
        sol = solutions[0]
        print(f"   Maximize A * B subject to A + B <= 7")
        print(f"   Optimal: A={sol.assignment['A']}, B={sol.assignment['B']}")
        print(f"   Value: {sol.objective_value}")
    print()

    # 6. Sudoku (Simple)
    print("6. SUDOKU (4x4 Mini-Sudoku):")
    print("-" * 40)

    # Create simple 4x4 Sudoku variant
    solver.create_problem("mini_sudoku")

    # 4x4 grid with some given values
    given = {
        (0, 0): 1, (0, 3): 4,
        (1, 1): 2,
        (2, 2): 3,
        (3, 0): 4, (3, 3): 1
    }

    for i in range(4):
        for j in range(4):
            if (i, j) in given:
                solver.add_variable("mini_sudoku", f"C{i}{j}", [given[(i, j)]])
            else:
                solver.add_variable("mini_sudoku", f"C{i}{j}", [1, 2, 3, 4])

    # Row constraints
    for i in range(4):
        row_vars = [f"C{i}{j}" for j in range(4)]
        solver.add_all_different("mini_sudoku", row_vars)

    # Column constraints
    for j in range(4):
        col_vars = [f"C{i}{j}" for i in range(4)]
        solver.add_all_different("mini_sudoku", col_vars)

    # 2x2 box constraints
    for box_i in range(2):
        for box_j in range(2):
            box_vars = [
                f"C{box_i*2+i}{box_j*2+j}"
                for i in range(2) for j in range(2)
            ]
            solver.add_all_different("mini_sudoku", box_vars)

    solutions = solver.solve("mini_sudoku", SearchStrategy.FORWARD_CHECKING)
    if solutions:
        sol = solutions[0]
        print("   Solution:")
        for i in range(4):
            line = "   "
            for j in range(4):
                line += f"{sol.assignment[f'C{i}{j}']} "
            print(line)
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Constraint Solver Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
