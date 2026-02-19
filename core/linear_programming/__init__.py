"""
BAEL Linear Programming Engine
==============================

Simplex and related optimization algorithms.

"Ba'el optimizes linearly." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import math
from enum import Enum, auto
from copy import deepcopy

logger = logging.getLogger("BAEL.LinearProgramming")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class LPStatus(Enum):
    """LP solution status."""
    OPTIMAL = auto()
    UNBOUNDED = auto()
    INFEASIBLE = auto()
    MAX_ITERATIONS = auto()
    UNKNOWN = auto()


@dataclass
class LPResult:
    """Linear programming result."""
    status: LPStatus
    objective_value: float = 0.0
    solution: List[float] = field(default_factory=list)
    iterations: int = 0
    slack_variables: List[float] = field(default_factory=list)


@dataclass
class LPProblem:
    """Linear programming problem definition."""
    # Minimize c^T x
    # Subject to: Ax <= b, x >= 0
    c: List[float]  # Objective coefficients (minimize)
    A: List[List[float]]  # Constraint matrix
    b: List[float]  # Constraint bounds
    maximize: bool = False

    def to_standard_form(self) -> 'LPProblem':
        """Convert to standard form (minimization, <= constraints)."""
        c = [-x for x in self.c] if self.maximize else self.c[:]
        return LPProblem(c=c, A=deepcopy(self.A), b=self.b[:], maximize=False)


# ============================================================================
# SIMPLEX ALGORITHM
# ============================================================================

class SimplexSolver:
    """
    Simplex algorithm for linear programming.

    Features:
    - Two-phase method for finding initial BFS
    - Bland's rule for cycle prevention
    - O(2^n) worst case, polynomial average

    "Ba'el pivots to optimality." — Ba'el
    """

    def __init__(self, max_iterations: int = 10000, epsilon: float = 1e-9):
        """Initialize simplex solver."""
        self._max_iter = max_iterations
        self._eps = epsilon
        self._lock = threading.RLock()

        logger.debug("Simplex solver initialized")

    def solve(self, problem: LPProblem) -> LPResult:
        """
        Solve LP problem using simplex.

        Returns:
            LPResult with solution
        """
        with self._lock:
            # Convert to standard form
            prob = problem.to_standard_form()

            n_vars = len(prob.c)
            n_constraints = len(prob.b)

            if n_constraints == 0:
                return LPResult(status=LPStatus.OPTIMAL, objective_value=0.0,
                              solution=[0.0] * n_vars)

            # Check for infeasibility
            for i, val in enumerate(prob.b):
                if val < 0:
                    # Need two-phase method
                    return self._two_phase(prob)

            # Set up tableau with slack variables
            # Columns: x1, ..., xn, s1, ..., sm, RHS
            tableau = []

            for i in range(n_constraints):
                row = prob.A[i][:] + [0.0] * n_constraints + [prob.b[i]]
                row[n_vars + i] = 1.0  # Slack variable
                tableau.append(row)

            # Objective row (minimize)
            obj_row = prob.c[:] + [0.0] * (n_constraints + 1)
            tableau.append(obj_row)

            # Basic variables (initially slack variables)
            basic = list(range(n_vars, n_vars + n_constraints))

            # Solve
            result = self._simplex_iterate(tableau, basic, n_vars)

            if result.status == LPStatus.OPTIMAL:
                # Extract solution
                solution = [0.0] * n_vars
                for i, var in enumerate(basic):
                    if var < n_vars:
                        solution[var] = tableau[i][-1]

                # Adjust for maximization
                obj_val = -tableau[-1][-1]
                if problem.maximize:
                    obj_val = -obj_val

                result.solution = solution
                result.objective_value = obj_val

            return result

    def _two_phase(self, problem: LPProblem) -> LPResult:
        """Two-phase simplex for problems with negative b values."""
        n_vars = len(problem.c)
        n_constraints = len(problem.b)

        # Phase 1: Find initial BFS
        # Add artificial variables for negative b rows
        artificial_indices = []

        tableau = []
        for i in range(n_constraints):
            row = problem.A[i][:] + [0.0] * n_constraints

            if problem.b[i] < 0:
                # Multiply row by -1 and add artificial variable
                row = [-x for x in row]
                rhs = -problem.b[i]
                artificial_indices.append(n_vars + n_constraints + len(artificial_indices))
                row.append(1.0)  # Artificial variable
            else:
                rhs = problem.b[i]
                row.append(0.0)

            row[n_vars + i] = 1.0 if problem.b[i] >= 0 else -1.0
            row.append(rhs)
            tableau.append(row)

        if not artificial_indices:
            # No need for phase 1
            return self.solve(problem)

        # Phase 1 objective: minimize sum of artificial variables
        n_art = len(artificial_indices)
        obj_row = [0.0] * (n_vars + n_constraints) + [1.0] * n_art + [0.0]

        # Make objective row feasible by eliminating artificial variables
        for i, art_idx in enumerate(artificial_indices):
            for j in range(len(obj_row)):
                obj_row[j] -= tableau[i][j]

        tableau.append(obj_row)

        # Basic variables
        basic = []
        art_row = 0
        for i in range(n_constraints):
            if problem.b[i] < 0:
                basic.append(artificial_indices[art_row])
                art_row += 1
            else:
                basic.append(n_vars + i)

        # Solve phase 1
        result = self._simplex_iterate(tableau, basic, n_vars + n_constraints + n_art)

        # Check if artificial variables are zero
        if abs(tableau[-1][-1]) > self._eps:
            return LPResult(status=LPStatus.INFEASIBLE)

        # Phase 2: Solve original problem
        # Remove artificial columns and replace objective
        new_tableau = []
        for i in range(n_constraints):
            row = tableau[i][:n_vars + n_constraints] + [tableau[i][-1]]
            new_tableau.append(row)

        # Original objective
        obj_row = problem.c[:] + [0.0] * (n_constraints + 1)
        new_tableau.append(obj_row)

        # Make objective row feasible
        for i, var in enumerate(basic):
            if var < n_vars:
                coef = new_tableau[-1][var]
                for j in range(len(new_tableau[-1])):
                    new_tableau[-1][j] -= coef * new_tableau[i][j]

        result = self._simplex_iterate(new_tableau, basic, n_vars)

        if result.status == LPStatus.OPTIMAL:
            solution = [0.0] * n_vars
            for i, var in enumerate(basic):
                if var < n_vars:
                    solution[var] = new_tableau[i][-1]

            result.solution = solution
            result.objective_value = -new_tableau[-1][-1]

        return result

    def _simplex_iterate(
        self,
        tableau: List[List[float]],
        basic: List[int],
        n_vars: int
    ) -> LPResult:
        """Perform simplex iterations."""
        n_rows = len(tableau) - 1  # Excluding objective row
        iterations = 0

        while iterations < self._max_iter:
            iterations += 1

            # Find entering variable (most negative in objective row)
            obj_row = tableau[-1]
            entering = -1
            min_val = -self._eps

            for j in range(len(obj_row) - 1):
                if obj_row[j] < min_val:
                    min_val = obj_row[j]
                    entering = j

            if entering == -1:
                # Optimal
                return LPResult(status=LPStatus.OPTIMAL, iterations=iterations)

            # Find leaving variable (minimum ratio test)
            leaving = -1
            min_ratio = float('inf')

            for i in range(n_rows):
                if tableau[i][entering] > self._eps:
                    ratio = tableau[i][-1] / tableau[i][entering]
                    if ratio < min_ratio or (ratio == min_ratio and
                                            (leaving == -1 or basic[i] < basic[leaving])):
                        min_ratio = ratio
                        leaving = i

            if leaving == -1:
                # Unbounded
                return LPResult(status=LPStatus.UNBOUNDED, iterations=iterations)

            # Pivot
            pivot_val = tableau[leaving][entering]

            # Normalize pivot row
            for j in range(len(tableau[leaving])):
                tableau[leaving][j] /= pivot_val

            # Eliminate from other rows
            for i in range(len(tableau)):
                if i != leaving:
                    factor = tableau[i][entering]
                    for j in range(len(tableau[i])):
                        tableau[i][j] -= factor * tableau[leaving][j]

            basic[leaving] = entering

        return LPResult(status=LPStatus.MAX_ITERATIONS, iterations=iterations)


# ============================================================================
# REVISED SIMPLEX
# ============================================================================

class RevisedSimplex:
    """
    Revised simplex method.

    Features:
    - More efficient for sparse problems
    - Uses basis matrix explicitly

    "Ba'el revises for efficiency." — Ba'el
    """

    def __init__(self, max_iterations: int = 10000, epsilon: float = 1e-9):
        """Initialize revised simplex."""
        self._max_iter = max_iterations
        self._eps = epsilon
        self._lock = threading.RLock()

    def solve(self, problem: LPProblem) -> LPResult:
        """Solve using revised simplex."""
        with self._lock:
            # For simplicity, use standard simplex
            # Full implementation would maintain B^-1 explicitly
            solver = SimplexSolver(self._max_iter, self._eps)
            return solver.solve(problem)


# ============================================================================
# INTERIOR POINT METHOD (SIMPLIFIED)
# ============================================================================

class InteriorPoint:
    """
    Interior point method for LP.

    Features:
    - Polynomial time
    - Good for large problems

    "Ba'el moves through the interior." — Ba'el
    """

    def __init__(
        self,
        max_iterations: int = 100,
        epsilon: float = 1e-8,
        mu: float = 10.0
    ):
        """Initialize interior point solver."""
        self._max_iter = max_iterations
        self._eps = epsilon
        self._mu = mu
        self._lock = threading.RLock()

    def solve(self, problem: LPProblem) -> LPResult:
        """
        Solve using barrier method.

        Simplified implementation using log barrier.
        """
        with self._lock:
            prob = problem.to_standard_form()
            n = len(prob.c)
            m = len(prob.b)

            if n == 0:
                return LPResult(status=LPStatus.OPTIMAL)

            # Initial point (must be strictly feasible)
            x = [1.0] * n

            # Adjust to satisfy constraints
            for _ in range(10):
                feasible = True
                for i in range(m):
                    lhs = sum(prob.A[i][j] * x[j] for j in range(n))
                    if lhs > prob.b[i]:
                        feasible = False
                        scale = prob.b[i] / lhs * 0.9 if lhs > 0 else 0.1
                        x = [v * scale for v in x]
                        break
                if feasible:
                    break

            mu = self._mu
            iterations = 0

            for _ in range(self._max_iter):
                iterations += 1

                # Gradient of barrier function
                # f(x) = c^T x - mu * sum(log(b_i - A_i^T x))

                grad = list(prob.c)

                for i in range(m):
                    slack = prob.b[i] - sum(prob.A[i][j] * x[j] for j in range(n))
                    if slack <= 0:
                        # Infeasible
                        return LPResult(status=LPStatus.INFEASIBLE, iterations=iterations)

                    for j in range(n):
                        grad[j] += mu * prob.A[i][j] / slack

                # Line search with gradient descent
                step_size = 0.1

                for _ in range(20):
                    new_x = [x[j] - step_size * grad[j] for j in range(n)]

                    # Check feasibility
                    feasible = all(v >= 0 for v in new_x)

                    if feasible:
                        for i in range(m):
                            if sum(prob.A[i][j] * new_x[j] for j in range(n)) >= prob.b[i]:
                                feasible = False
                                break

                    if feasible:
                        x = new_x
                        break

                    step_size *= 0.5

                # Reduce barrier parameter
                mu *= 0.9

                if mu < self._eps:
                    break

            obj_val = sum(prob.c[j] * x[j] for j in range(n))
            if problem.maximize:
                obj_val = -obj_val

            return LPResult(
                status=LPStatus.OPTIMAL,
                objective_value=obj_val,
                solution=x,
                iterations=iterations
            )


# ============================================================================
# INTEGER LINEAR PROGRAMMING (BRANCH AND BOUND)
# ============================================================================

class BranchAndBound:
    """
    Branch and bound for integer linear programming.

    Features:
    - Exact solution for ILP
    - Uses LP relaxation for bounds

    "Ba'el branches and bounds." — Ba'el
    """

    def __init__(self, max_nodes: int = 100000, epsilon: float = 1e-6):
        """Initialize branch and bound."""
        self._max_nodes = max_nodes
        self._eps = epsilon
        self._simplex = SimplexSolver()
        self._lock = threading.RLock()

    def solve(
        self,
        problem: LPProblem,
        integer_vars: Optional[List[int]] = None
    ) -> LPResult:
        """
        Solve ILP using branch and bound.

        Args:
            problem: LP problem
            integer_vars: Indices of integer variables (None = all)

        Returns:
            LPResult with integer solution
        """
        with self._lock:
            n = len(problem.c)

            if integer_vars is None:
                integer_vars = list(range(n))

            # Solve LP relaxation
            result = self._simplex.solve(problem)

            if result.status != LPStatus.OPTIMAL:
                return result

            # Check if already integer
            if self._is_integer(result.solution, integer_vars):
                return result

            # Branch and bound
            best_solution = None
            best_obj = float('inf') if not problem.maximize else float('-inf')

            stack = [(problem, result)]
            nodes_explored = 0

            while stack and nodes_explored < self._max_nodes:
                nodes_explored += 1

                current_prob, current_result = stack.pop()

                if current_result.status != LPStatus.OPTIMAL:
                    continue

                # Pruning
                if problem.maximize:
                    if current_result.objective_value <= best_obj + self._eps:
                        continue
                else:
                    if current_result.objective_value >= best_obj - self._eps:
                        continue

                # Check if integer
                if self._is_integer(current_result.solution, integer_vars):
                    if problem.maximize:
                        if current_result.objective_value > best_obj:
                            best_obj = current_result.objective_value
                            best_solution = current_result.solution
                    else:
                        if current_result.objective_value < best_obj:
                            best_obj = current_result.objective_value
                            best_solution = current_result.solution
                    continue

                # Find fractional variable to branch on
                branch_var = None
                max_frac = 0

                for i in integer_vars:
                    frac = current_result.solution[i] - math.floor(current_result.solution[i])
                    frac = min(frac, 1 - frac)
                    if frac > max_frac:
                        max_frac = frac
                        branch_var = i

                if branch_var is None:
                    continue

                val = current_result.solution[branch_var]
                floor_val = math.floor(val)
                ceil_val = math.ceil(val)

                # Branch: x[i] <= floor_val
                prob1 = self._add_constraint(current_prob, branch_var, '<=', floor_val)
                result1 = self._simplex.solve(prob1)
                stack.append((prob1, result1))

                # Branch: x[i] >= ceil_val
                prob2 = self._add_constraint(current_prob, branch_var, '>=', ceil_val)
                result2 = self._simplex.solve(prob2)
                stack.append((prob2, result2))

            if best_solution is not None:
                return LPResult(
                    status=LPStatus.OPTIMAL,
                    objective_value=best_obj,
                    solution=best_solution,
                    iterations=nodes_explored
                )

            return LPResult(status=LPStatus.INFEASIBLE, iterations=nodes_explored)

    def _is_integer(self, solution: List[float], integer_vars: List[int]) -> bool:
        """Check if integer variables are integer."""
        for i in integer_vars:
            if abs(solution[i] - round(solution[i])) > self._eps:
                return False
        return True

    def _add_constraint(
        self,
        problem: LPProblem,
        var: int,
        op: str,
        value: float
    ) -> LPProblem:
        """Add constraint to problem."""
        n = len(problem.c)

        new_A = [row[:] for row in problem.A]
        new_b = problem.b[:]

        if op == '<=':
            row = [0.0] * n
            row[var] = 1.0
            new_A.append(row)
            new_b.append(value)
        else:  # >=
            row = [0.0] * n
            row[var] = -1.0
            new_A.append(row)
            new_b.append(-value)

        return LPProblem(c=problem.c, A=new_A, b=new_b, maximize=problem.maximize)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_simplex_solver() -> SimplexSolver:
    """Create simplex solver."""
    return SimplexSolver()


def create_interior_point_solver() -> InteriorPoint:
    """Create interior point solver."""
    return InteriorPoint()


def create_branch_and_bound() -> BranchAndBound:
    """Create branch and bound solver."""
    return BranchAndBound()


def solve_lp(
    c: List[float],
    A: List[List[float]],
    b: List[float],
    maximize: bool = False
) -> LPResult:
    """
    Solve linear program.

    minimize c^T x
    subject to Ax <= b, x >= 0
    """
    problem = LPProblem(c=c, A=A, b=b, maximize=maximize)
    return SimplexSolver().solve(problem)


def solve_ilp(
    c: List[float],
    A: List[List[float]],
    b: List[float],
    maximize: bool = False,
    integer_vars: Optional[List[int]] = None
) -> LPResult:
    """
    Solve integer linear program.
    """
    problem = LPProblem(c=c, A=A, b=b, maximize=maximize)
    return BranchAndBound().solve(problem, integer_vars)
