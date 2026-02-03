#!/usr/bin/env python3
"""
BAEL - Constraint Engine
Constraint satisfaction and solving for agents.

Features:
- Constraint definition
- Constraint propagation
- Backtracking search
- Arc consistency
- Optimization
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ConstraintType(Enum):
    """Types of constraints."""
    UNARY = "unary"
    BINARY = "binary"
    N_ARY = "n_ary"
    GLOBAL = "global"
    SOFT = "soft"


class VariableState(Enum):
    """Variable states."""
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    FAILED = "failed"


class SolverStrategy(Enum):
    """Solver strategies."""
    BACKTRACKING = "backtracking"
    FORWARD_CHECKING = "forward_checking"
    ARC_CONSISTENCY = "arc_consistency"
    MIN_CONFLICTS = "min_conflicts"


class SelectionHeuristic(Enum):
    """Variable selection heuristics."""
    FIRST = "first"
    MRV = "mrv"
    DEGREE = "degree"
    RANDOM = "random"


class OrderingHeuristic(Enum):
    """Value ordering heuristics."""
    NATURAL = "natural"
    LCV = "lcv"
    RANDOM = "random"


class SolutionStatus(Enum):
    """Solution statuses."""
    SOLVED = "solved"
    UNSATISFIABLE = "unsatisfiable"
    TIMEOUT = "timeout"
    PARTIAL = "partial"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Variable:
    """A CSP variable."""
    var_id: str = ""
    name: str = ""
    domain: List[Any] = field(default_factory=list)
    current_domain: List[Any] = field(default_factory=list)
    value: Any = None
    state: VariableState = VariableState.UNASSIGNED

    def __post_init__(self):
        if not self.var_id:
            self.var_id = str(uuid.uuid4())[:8]
        if not self.current_domain:
            self.current_domain = list(self.domain)

    def __hash__(self):
        return hash(self.var_id)


@dataclass
class Constraint:
    """A constraint between variables."""
    constraint_id: str = ""
    name: str = ""
    constraint_type: ConstraintType = ConstraintType.BINARY
    variables: List[str] = field(default_factory=list)
    predicate: Optional[Callable] = None
    weight: float = 1.0

    def __post_init__(self):
        if not self.constraint_id:
            self.constraint_id = str(uuid.uuid4())[:8]


@dataclass
class Assignment:
    """An assignment of values to variables."""
    assignment_id: str = ""
    values: Dict[str, Any] = field(default_factory=dict)
    complete: bool = False
    consistent: bool = True
    cost: float = 0.0

    def __post_init__(self):
        if not self.assignment_id:
            self.assignment_id = str(uuid.uuid4())[:8]


@dataclass
class Solution:
    """A CSP solution."""
    solution_id: str = ""
    assignment: Dict[str, Any] = field(default_factory=dict)
    status: SolutionStatus = SolutionStatus.SOLVED
    iterations: int = 0
    backtracks: int = 0
    duration: float = 0.0

    def __post_init__(self):
        if not self.solution_id:
            self.solution_id = str(uuid.uuid4())[:8]


@dataclass
class CSPConfig:
    """CSP solver configuration."""
    strategy: SolverStrategy = SolverStrategy.BACKTRACKING
    selection: SelectionHeuristic = SelectionHeuristic.MRV
    ordering: OrderingHeuristic = OrderingHeuristic.LCV
    max_iterations: int = 10000
    timeout: float = 30.0


# =============================================================================
# VARIABLE MANAGER
# =============================================================================

class VariableManager:
    """Manage CSP variables."""

    def __init__(self):
        self._variables: Dict[str, Variable] = {}
        self._by_name: Dict[str, Variable] = {}

    def create(
        self,
        name: str,
        domain: List[Any]
    ) -> Variable:
        """Create a variable."""
        var = Variable(
            name=name,
            domain=domain,
            current_domain=list(domain)
        )

        self._variables[var.var_id] = var
        self._by_name[name] = var

        return var

    def get(self, var_id: str) -> Optional[Variable]:
        """Get variable by ID."""
        return self._variables.get(var_id)

    def get_by_name(self, name: str) -> Optional[Variable]:
        """Get variable by name."""
        return self._by_name.get(name)

    def assign(self, name: str, value: Any) -> bool:
        """Assign value to variable."""
        var = self._by_name.get(name)

        if var and value in var.current_domain:
            var.value = value
            var.state = VariableState.ASSIGNED
            return True

        return False

    def unassign(self, name: str) -> bool:
        """Unassign variable."""
        var = self._by_name.get(name)

        if var:
            var.value = None
            var.state = VariableState.UNASSIGNED
            return True

        return False

    def prune(self, name: str, value: Any) -> bool:
        """Prune value from domain."""
        var = self._by_name.get(name)

        if var and value in var.current_domain:
            var.current_domain.remove(value)
            return True

        return False

    def restore(self, name: str, value: Any) -> bool:
        """Restore value to domain."""
        var = self._by_name.get(name)

        if var and value in var.domain and value not in var.current_domain:
            var.current_domain.append(value)
            return True

        return False

    def reset_domains(self) -> None:
        """Reset all domains to original."""
        for var in self._variables.values():
            var.current_domain = list(var.domain)

    def reset_all(self) -> None:
        """Reset all variables."""
        for var in self._variables.values():
            var.value = None
            var.state = VariableState.UNASSIGNED
            var.current_domain = list(var.domain)

    def get_unassigned(self) -> List[Variable]:
        """Get unassigned variables."""
        return [v for v in self._variables.values()
                if v.state == VariableState.UNASSIGNED]

    def get_assigned(self) -> List[Variable]:
        """Get assigned variables."""
        return [v for v in self._variables.values()
                if v.state == VariableState.ASSIGNED]

    def is_complete(self) -> bool:
        """Check if all variables assigned."""
        return all(v.state == VariableState.ASSIGNED
                   for v in self._variables.values())

    def get_assignment(self) -> Dict[str, Any]:
        """Get current assignment."""
        return {v.name: v.value for v in self._variables.values()
                if v.state == VariableState.ASSIGNED}

    def count(self) -> int:
        """Count variables."""
        return len(self._variables)

    def all(self) -> List[Variable]:
        """Get all variables."""
        return list(self._variables.values())


# =============================================================================
# CONSTRAINT MANAGER
# =============================================================================

class ConstraintManager:
    """Manage constraints."""

    def __init__(self):
        self._constraints: Dict[str, Constraint] = {}
        self._by_variable: Dict[str, List[Constraint]] = defaultdict(list)

    def add(
        self,
        name: str,
        variables: List[str],
        predicate: Callable,
        constraint_type: Optional[ConstraintType] = None,
        weight: float = 1.0
    ) -> Constraint:
        """Add a constraint."""
        if constraint_type is None:
            if len(variables) == 1:
                constraint_type = ConstraintType.UNARY
            elif len(variables) == 2:
                constraint_type = ConstraintType.BINARY
            else:
                constraint_type = ConstraintType.N_ARY

        constraint = Constraint(
            name=name,
            variables=variables,
            predicate=predicate,
            constraint_type=constraint_type,
            weight=weight
        )

        self._constraints[constraint.constraint_id] = constraint

        for var in variables:
            self._by_variable[var].append(constraint)

        return constraint

    def get(self, constraint_id: str) -> Optional[Constraint]:
        """Get constraint by ID."""
        return self._constraints.get(constraint_id)

    def get_for_variable(self, var_name: str) -> List[Constraint]:
        """Get constraints involving variable."""
        return self._by_variable.get(var_name, [])

    def get_binary_constraints(
        self,
        var1: str,
        var2: str
    ) -> List[Constraint]:
        """Get binary constraints between two variables."""
        constraints1 = set(c.constraint_id for c in self._by_variable.get(var1, []))
        constraints2 = set(c.constraint_id for c in self._by_variable.get(var2, []))

        common = constraints1 & constraints2

        return [self._constraints[cid] for cid in common
                if self._constraints[cid].constraint_type == ConstraintType.BINARY]

    def check(
        self,
        constraint: Constraint,
        assignment: Dict[str, Any]
    ) -> bool:
        """Check if constraint is satisfied."""
        values = []

        for var in constraint.variables:
            if var not in assignment:
                return True
            values.append(assignment[var])

        try:
            return constraint.predicate(*values)
        except Exception:
            return False

    def check_all(self, assignment: Dict[str, Any]) -> bool:
        """Check all constraints."""
        for constraint in self._constraints.values():
            if not self.check(constraint, assignment):
                return False
        return True

    def get_violations(
        self,
        assignment: Dict[str, Any]
    ) -> List[Constraint]:
        """Get violated constraints."""
        violations = []

        for constraint in self._constraints.values():
            if not self.check(constraint, assignment):
                violations.append(constraint)

        return violations

    def count(self) -> int:
        """Count constraints."""
        return len(self._constraints)

    def all(self) -> List[Constraint]:
        """Get all constraints."""
        return list(self._constraints.values())


# =============================================================================
# HEURISTICS
# =============================================================================

class Heuristics:
    """Variable and value ordering heuristics."""

    def __init__(
        self,
        variable_manager: VariableManager,
        constraint_manager: ConstraintManager
    ):
        self._var_mgr = variable_manager
        self._con_mgr = constraint_manager

    def select_variable(
        self,
        heuristic: SelectionHeuristic
    ) -> Optional[Variable]:
        """Select next variable to assign."""
        unassigned = self._var_mgr.get_unassigned()

        if not unassigned:
            return None

        if heuristic == SelectionHeuristic.FIRST:
            return unassigned[0]

        elif heuristic == SelectionHeuristic.MRV:
            return min(unassigned, key=lambda v: len(v.current_domain))

        elif heuristic == SelectionHeuristic.DEGREE:
            return max(unassigned,
                      key=lambda v: len(self._con_mgr.get_for_variable(v.name)))

        elif heuristic == SelectionHeuristic.RANDOM:
            return random.choice(unassigned)

        return unassigned[0]

    def order_values(
        self,
        variable: Variable,
        heuristic: OrderingHeuristic
    ) -> List[Any]:
        """Order values for variable."""
        values = list(variable.current_domain)

        if heuristic == OrderingHeuristic.NATURAL:
            return values

        elif heuristic == OrderingHeuristic.RANDOM:
            random.shuffle(values)
            return values

        elif heuristic == OrderingHeuristic.LCV:
            def count_ruled_out(value):
                count = 0
                assignment = self._var_mgr.get_assignment()
                assignment[variable.name] = value

                for constraint in self._con_mgr.get_for_variable(variable.name):
                    for other_var in constraint.variables:
                        if other_var != variable.name:
                            other = self._var_mgr.get_by_name(other_var)
                            if other and other.state == VariableState.UNASSIGNED:
                                for other_val in other.current_domain:
                                    test_assignment = dict(assignment)
                                    test_assignment[other_var] = other_val
                                    if not self._con_mgr.check(constraint, test_assignment):
                                        count += 1

                return count

            return sorted(values, key=count_ruled_out)

        return values


# =============================================================================
# PROPAGATOR
# =============================================================================

class Propagator:
    """Constraint propagation."""

    def __init__(
        self,
        variable_manager: VariableManager,
        constraint_manager: ConstraintManager
    ):
        self._var_mgr = variable_manager
        self._con_mgr = constraint_manager

    def forward_check(
        self,
        assigned_var: str,
        assigned_value: Any
    ) -> Tuple[bool, List[Tuple[str, Any]]]:
        """Forward checking after assignment."""
        pruned = []
        assignment = {assigned_var: assigned_value}

        for constraint in self._con_mgr.get_for_variable(assigned_var):
            if constraint.constraint_type != ConstraintType.BINARY:
                continue

            for other_var in constraint.variables:
                if other_var == assigned_var:
                    continue

                other = self._var_mgr.get_by_name(other_var)

                if not other or other.state == VariableState.ASSIGNED:
                    continue

                for value in list(other.current_domain):
                    test_assignment = dict(assignment)
                    test_assignment[other_var] = value

                    if not self._con_mgr.check(constraint, test_assignment):
                        self._var_mgr.prune(other_var, value)
                        pruned.append((other_var, value))

                if not other.current_domain:
                    return False, pruned

        return True, pruned

    def arc_consistency(self) -> bool:
        """Enforce arc consistency (AC-3)."""
        queue = deque()

        for constraint in self._con_mgr.all():
            if constraint.constraint_type == ConstraintType.BINARY:
                queue.append((constraint.variables[0], constraint.variables[1], constraint))
                queue.append((constraint.variables[1], constraint.variables[0], constraint))

        while queue:
            xi, xj, constraint = queue.popleft()

            var_i = self._var_mgr.get_by_name(xi)
            var_j = self._var_mgr.get_by_name(xj)

            if not var_i or not var_j:
                continue

            if self._revise(var_i, var_j, constraint):
                if not var_i.current_domain:
                    return False

                for other_constraint in self._con_mgr.get_for_variable(xi):
                    for xk in other_constraint.variables:
                        if xk != xi and xk != xj:
                            queue.append((xk, xi, other_constraint))

        return True

    def _revise(
        self,
        var_i: Variable,
        var_j: Variable,
        constraint: Constraint
    ) -> bool:
        """Revise domain of var_i."""
        revised = False

        for val_i in list(var_i.current_domain):
            has_support = False

            for val_j in var_j.current_domain:
                if var_i.name == constraint.variables[0]:
                    assignment = {var_i.name: val_i, var_j.name: val_j}
                else:
                    assignment = {var_j.name: val_j, var_i.name: val_i}

                if self._con_mgr.check(constraint, assignment):
                    has_support = True
                    break

            if not has_support:
                var_i.current_domain.remove(val_i)
                revised = True

        return revised

    def restore(self, pruned: List[Tuple[str, Any]]) -> None:
        """Restore pruned values."""
        for var_name, value in pruned:
            self._var_mgr.restore(var_name, value)


# =============================================================================
# SOLVER
# =============================================================================

class Solver:
    """CSP solver."""

    def __init__(
        self,
        variable_manager: VariableManager,
        constraint_manager: ConstraintManager,
        config: CSPConfig
    ):
        self._var_mgr = variable_manager
        self._con_mgr = constraint_manager
        self._config = config

        self._heuristics = Heuristics(variable_manager, constraint_manager)
        self._propagator = Propagator(variable_manager, constraint_manager)

        self._iterations = 0
        self._backtracks = 0

    def solve(self) -> Solution:
        """Solve the CSP."""
        self._iterations = 0
        self._backtracks = 0

        start_time = time.time()

        self._var_mgr.reset_all()

        if self._config.strategy == SolverStrategy.ARC_CONSISTENCY:
            if not self._propagator.arc_consistency():
                return Solution(
                    status=SolutionStatus.UNSATISFIABLE,
                    iterations=self._iterations,
                    duration=time.time() - start_time
                )

        result = self._backtrack()

        duration = time.time() - start_time

        if result:
            return Solution(
                assignment=self._var_mgr.get_assignment(),
                status=SolutionStatus.SOLVED,
                iterations=self._iterations,
                backtracks=self._backtracks,
                duration=duration
            )

        return Solution(
            status=SolutionStatus.UNSATISFIABLE,
            iterations=self._iterations,
            backtracks=self._backtracks,
            duration=duration
        )

    def _backtrack(self) -> bool:
        """Backtracking search."""
        self._iterations += 1

        if self._iterations > self._config.max_iterations:
            return False

        if self._var_mgr.is_complete():
            return True

        var = self._heuristics.select_variable(self._config.selection)

        if not var:
            return False

        values = self._heuristics.order_values(var, self._config.ordering)

        for value in values:
            assignment = self._var_mgr.get_assignment()
            assignment[var.name] = value

            if self._con_mgr.check_all(assignment):
                self._var_mgr.assign(var.name, value)

                if self._config.strategy == SolverStrategy.FORWARD_CHECKING:
                    consistent, pruned = self._propagator.forward_check(var.name, value)

                    if consistent and self._backtrack():
                        return True

                    self._propagator.restore(pruned)
                else:
                    if self._backtrack():
                        return True

                self._var_mgr.unassign(var.name)
                self._backtracks += 1

        return False

    def solve_all(self, max_solutions: int = 10) -> List[Solution]:
        """Find all solutions."""
        solutions = []

        self._var_mgr.reset_all()

        self._find_all_solutions(solutions, max_solutions)

        return solutions

    def _find_all_solutions(
        self,
        solutions: List[Solution],
        max_solutions: int
    ) -> None:
        """Find all solutions recursively."""
        if len(solutions) >= max_solutions:
            return

        if self._var_mgr.is_complete():
            solutions.append(Solution(
                assignment=dict(self._var_mgr.get_assignment()),
                status=SolutionStatus.SOLVED
            ))
            return

        var = self._heuristics.select_variable(self._config.selection)

        if not var:
            return

        for value in var.current_domain:
            assignment = self._var_mgr.get_assignment()
            assignment[var.name] = value

            if self._con_mgr.check_all(assignment):
                self._var_mgr.assign(var.name, value)

                self._find_all_solutions(solutions, max_solutions)

                self._var_mgr.unassign(var.name)


# =============================================================================
# CONSTRAINT ENGINE
# =============================================================================

class ConstraintEngine:
    """
    Constraint Engine for BAEL.

    Constraint satisfaction and solving.
    """

    def __init__(self, config: Optional[CSPConfig] = None):
        self._config = config or CSPConfig()

        self._variable_manager = VariableManager()
        self._constraint_manager = ConstraintManager()
        self._solver: Optional[Solver] = None

    # ----- Variable Operations -----

    def add_variable(
        self,
        name: str,
        domain: List[Any]
    ) -> Variable:
        """Add a variable."""
        return self._variable_manager.create(name, domain)

    def get_variable(self, name: str) -> Optional[Variable]:
        """Get variable by name."""
        return self._variable_manager.get_by_name(name)

    def assign(self, name: str, value: Any) -> bool:
        """Assign value to variable."""
        return self._variable_manager.assign(name, value)

    def unassign(self, name: str) -> bool:
        """Unassign variable."""
        return self._variable_manager.unassign(name)

    def get_assignment(self) -> Dict[str, Any]:
        """Get current assignment."""
        return self._variable_manager.get_assignment()

    # ----- Constraint Operations -----

    def add_constraint(
        self,
        name: str,
        variables: List[str],
        predicate: Callable
    ) -> Constraint:
        """Add a constraint."""
        return self._constraint_manager.add(name, variables, predicate)

    def add_not_equal(self, var1: str, var2: str) -> Constraint:
        """Add not-equal constraint."""
        return self.add_constraint(
            f"{var1}_neq_{var2}",
            [var1, var2],
            lambda a, b: a != b
        )

    def add_equal(self, var1: str, var2: str) -> Constraint:
        """Add equality constraint."""
        return self.add_constraint(
            f"{var1}_eq_{var2}",
            [var1, var2],
            lambda a, b: a == b
        )

    def add_less_than(self, var1: str, var2: str) -> Constraint:
        """Add less-than constraint."""
        return self.add_constraint(
            f"{var1}_lt_{var2}",
            [var1, var2],
            lambda a, b: a < b
        )

    def add_all_different(self, variables: List[str]) -> List[Constraint]:
        """Add all-different constraint."""
        constraints = []

        for i, v1 in enumerate(variables):
            for v2 in variables[i + 1:]:
                constraints.append(self.add_not_equal(v1, v2))

        return constraints

    def check_consistent(self) -> bool:
        """Check if current assignment is consistent."""
        return self._constraint_manager.check_all(
            self._variable_manager.get_assignment()
        )

    def get_violations(self) -> List[Constraint]:
        """Get violated constraints."""
        return self._constraint_manager.get_violations(
            self._variable_manager.get_assignment()
        )

    # ----- Solving -----

    def solve(self) -> Solution:
        """Solve the CSP."""
        self._solver = Solver(
            self._variable_manager,
            self._constraint_manager,
            self._config
        )

        return self._solver.solve()

    def solve_all(self, max_solutions: int = 10) -> List[Solution]:
        """Find all solutions."""
        self._solver = Solver(
            self._variable_manager,
            self._constraint_manager,
            self._config
        )

        return self._solver.solve_all(max_solutions)

    # ----- Configuration -----

    def set_strategy(self, strategy: SolverStrategy) -> None:
        """Set solver strategy."""
        self._config.strategy = strategy

    def set_selection_heuristic(self, heuristic: SelectionHeuristic) -> None:
        """Set variable selection heuristic."""
        self._config.selection = heuristic

    def set_ordering_heuristic(self, heuristic: OrderingHeuristic) -> None:
        """Set value ordering heuristic."""
        self._config.ordering = heuristic

    # ----- Reset -----

    def reset(self) -> None:
        """Reset all variables."""
        self._variable_manager.reset_all()

    def clear(self) -> None:
        """Clear all variables and constraints."""
        self._variable_manager = VariableManager()
        self._constraint_manager = ConstraintManager()
        self._solver = None

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "variables": self._variable_manager.count(),
            "constraints": self._constraint_manager.count(),
            "assigned": len(self._variable_manager.get_assigned()),
            "unassigned": len(self._variable_manager.get_unassigned())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Constraint Engine."""
    print("=" * 70)
    print("BAEL - CONSTRAINT ENGINE DEMO")
    print("Constraint Satisfaction and Solving")
    print("=" * 70)
    print()

    engine = ConstraintEngine()

    # 1. N-Queens Problem (4x4)
    print("1. N-QUEENS PROBLEM (4x4):")
    print("-" * 40)

    for i in range(4):
        engine.add_variable(f"Q{i}", list(range(4)))

    for i in range(4):
        for j in range(i + 1, 4):
            engine.add_constraint(
                f"row_{i}_{j}",
                [f"Q{i}", f"Q{j}"],
                lambda a, b: a != b
            )

            engine.add_constraint(
                f"diag_{i}_{j}",
                [f"Q{i}", f"Q{j}"],
                lambda a, b, diff=j-i: abs(a - b) != diff
            )

    solution = engine.solve()

    print(f"   Status: {solution.status.value}")
    print(f"   Solution: {solution.assignment}")
    print(f"   Iterations: {solution.iterations}")
    print(f"   Backtracks: {solution.backtracks}")
    print(f"   Duration: {solution.duration:.4f}s")
    print()

    engine.clear()

    # 2. Graph Coloring
    print("2. GRAPH COLORING:")
    print("-" * 40)

    colors = ["red", "green", "blue"]

    for node in ["A", "B", "C", "D", "E"]:
        engine.add_variable(node, colors)

    edges = [("A", "B"), ("A", "C"), ("B", "C"), ("B", "D"), ("C", "D"), ("D", "E")]

    for v1, v2 in edges:
        engine.add_not_equal(v1, v2)

    solution = engine.solve()

    print(f"   Status: {solution.status.value}")
    print(f"   Coloring: {solution.assignment}")
    print()

    engine.clear()

    # 3. Simple Arithmetic CSP
    print("3. ARITHMETIC CSP:")
    print("-" * 40)

    engine.add_variable("X", list(range(1, 10)))
    engine.add_variable("Y", list(range(1, 10)))
    engine.add_variable("Z", list(range(1, 10)))

    engine.add_constraint("x_lt_y", ["X", "Y"], lambda x, y: x < y)
    engine.add_constraint("y_lt_z", ["Y", "Z"], lambda y, z: y < z)
    engine.add_constraint("sum_15", ["X", "Y", "Z"], lambda x, y, z: x + y + z == 15)

    solution = engine.solve()

    print(f"   Problem: X < Y < Z, X + Y + Z = 15")
    print(f"   Solution: X={solution.assignment.get('X')}, Y={solution.assignment.get('Y')}, Z={solution.assignment.get('Z')}")
    print()

    engine.clear()

    # 4. All Different
    print("4. ALL DIFFERENT:")
    print("-" * 40)

    for i in range(4):
        engine.add_variable(f"V{i}", [1, 2, 3, 4])

    engine.add_all_different(["V0", "V1", "V2", "V3"])

    solution = engine.solve()

    print(f"   Domain: [1, 2, 3, 4]")
    print(f"   Solution: {solution.assignment}")
    print()

    # 5. Find All Solutions
    print("5. FIND ALL SOLUTIONS:")
    print("-" * 40)

    engine.clear()

    engine.add_variable("A", [1, 2])
    engine.add_variable("B", [1, 2])
    engine.add_not_equal("A", "B")

    all_solutions = engine.solve_all()

    print(f"   Problem: A != B, domain [1, 2]")
    print(f"   Found {len(all_solutions)} solutions:")

    for sol in all_solutions:
        print(f"     {sol.assignment}")
    print()

    engine.clear()

    # 6. Manual Assignment
    print("6. MANUAL ASSIGNMENT:")
    print("-" * 40)

    engine.add_variable("P", [1, 2, 3])
    engine.add_variable("Q", [1, 2, 3])
    engine.add_not_equal("P", "Q")

    engine.assign("P", 1)

    print(f"   Assigned: P = 1")
    print(f"   Current assignment: {engine.get_assignment()}")
    print(f"   Consistent: {engine.check_consistent()}")

    engine.assign("Q", 1)
    print(f"   Assigned: Q = 1")
    print(f"   Consistent: {engine.check_consistent()}")

    violations = engine.get_violations()
    print(f"   Violations: {[v.name for v in violations]}")
    print()

    engine.clear()

    # 7. MRV Heuristic
    print("7. MRV HEURISTIC:")
    print("-" * 40)

    engine.add_variable("Small", [1])
    engine.add_variable("Medium", [1, 2, 3])
    engine.add_variable("Large", [1, 2, 3, 4, 5])

    engine.set_selection_heuristic(SelectionHeuristic.MRV)

    print("   Variables:")
    print(f"     Small: domain size 1")
    print(f"     Medium: domain size 3")
    print(f"     Large: domain size 5")
    print("   MRV will select 'Small' first (smallest domain)")
    print()

    engine.clear()

    # 8. Forward Checking
    print("8. FORWARD CHECKING:")
    print("-" * 40)

    engine.set_strategy(SolverStrategy.FORWARD_CHECKING)

    for i in range(3):
        engine.add_variable(f"F{i}", [1, 2, 3])

    engine.add_all_different(["F0", "F1", "F2"])

    solution = engine.solve()

    print(f"   Strategy: Forward Checking")
    print(f"   Solution: {solution.assignment}")
    print(f"   Backtracks: {solution.backtracks}")
    print()

    engine.clear()

    # 9. Arc Consistency
    print("9. ARC CONSISTENCY:")
    print("-" * 40)

    engine.set_strategy(SolverStrategy.ARC_CONSISTENCY)

    engine.add_variable("X1", [1, 2, 3])
    engine.add_variable("X2", [1, 2, 3])
    engine.add_constraint("x1_lt_x2", ["X1", "X2"], lambda a, b: a < b)

    solution = engine.solve()

    print(f"   Strategy: Arc Consistency (AC-3)")
    print(f"   Problem: X1 < X2")
    print(f"   Solution: {solution.assignment}")
    print()

    engine.clear()

    # 10. Unsatisfiable Problem
    print("10. UNSATISFIABLE PROBLEM:")
    print("-" * 40)

    engine.add_variable("A", [1])
    engine.add_variable("B", [1])
    engine.add_not_equal("A", "B")

    solution = engine.solve()

    print(f"   Problem: A != B, both domain [1]")
    print(f"   Status: {solution.status.value}")
    print()

    engine.clear()

    # 11. Custom Predicate
    print("11. CUSTOM PREDICATE:")
    print("-" * 40)

    engine.add_variable("Age", list(range(1, 100)))
    engine.add_variable("Year", list(range(2000, 2025)))

    engine.add_constraint(
        "born_2000",
        ["Age", "Year"],
        lambda age, year: year - age == 2000
    )

    engine.add_constraint(
        "age_limit",
        ["Age"],
        lambda age: 20 <= age <= 25
    )

    solution = engine.solve()

    print(f"   Problem: Year - Age = 2000, 20 <= Age <= 25")
    print(f"   Solution: Age={solution.assignment.get('Age')}, Year={solution.assignment.get('Year')}")
    print()

    engine.clear()

    # 12. Get Variable
    print("12. GET VARIABLE:")
    print("-" * 40)

    engine.add_variable("Test", [1, 2, 3, 4, 5])
    var = engine.get_variable("Test")

    if var:
        print(f"   Name: {var.name}")
        print(f"   Domain: {var.domain}")
        print(f"   State: {var.state.value}")
    print()

    engine.clear()

    # 13. Less Than Constraint
    print("13. LESS THAN CONSTRAINT:")
    print("-" * 40)

    engine.add_variable("First", [1, 2, 3])
    engine.add_variable("Second", [1, 2, 3])
    engine.add_less_than("First", "Second")

    all_solutions = engine.solve_all()

    print(f"   Problem: First < Second")
    print(f"   Solutions:")

    for sol in all_solutions:
        print(f"     {sol.assignment}")
    print()

    engine.clear()

    # 14. Reset
    print("14. RESET:")
    print("-" * 40)

    engine.add_variable("R1", [1, 2])
    engine.add_variable("R2", [1, 2])
    engine.assign("R1", 1)

    print(f"   Before reset: {engine.get_assignment()}")

    engine.reset()

    print(f"   After reset: {engine.get_assignment()}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Constraint Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
