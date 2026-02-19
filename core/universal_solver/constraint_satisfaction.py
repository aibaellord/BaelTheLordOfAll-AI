"""
🧠 CONSTRAINT SATISFACTION 🧠
=============================
CSP solver.

Features:
- Arc consistency
- Backtracking
- Constraint propagation
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from abc import ABC, abstractmethod
import uuid
from copy import deepcopy


@dataclass
class Domain:
    """Domain of possible values"""
    values: List[Any] = field(default_factory=list)

    def __len__(self):
        return len(self.values)

    def __contains__(self, value):
        return value in self.values

    def remove(self, value) -> bool:
        """Remove value from domain"""
        if value in self.values:
            self.values.remove(value)
            return True
        return False

    def is_empty(self) -> bool:
        return len(self.values) == 0

    def copy(self) -> 'Domain':
        return Domain(values=self.values.copy())


@dataclass
class Variable:
    """CSP variable"""
    name: str
    domain: Domain = field(default_factory=Domain)
    value: Any = None

    def is_assigned(self) -> bool:
        return self.value is not None

    def assign(self, value: Any):
        """Assign value"""
        if value in self.domain:
            self.value = value

    def unassign(self):
        """Remove assignment"""
        self.value = None

    def copy(self) -> 'Variable':
        return Variable(
            name=self.name,
            domain=self.domain.copy(),
            value=self.value
        )


class Constraint(ABC):
    """Base constraint class"""

    def __init__(self, variables: List[str]):
        self.variables = variables

    @abstractmethod
    def is_satisfied(self, assignment: Dict[str, Any]) -> bool:
        """Check if constraint is satisfied"""
        pass

    def is_consistent(
        self,
        variable: str,
        value: Any,
        assignment: Dict[str, Any]
    ) -> bool:
        """Check consistency with partial assignment"""
        test_assignment = assignment.copy()
        test_assignment[variable] = value

        # Only check if all constraint variables are assigned
        if all(v in test_assignment for v in self.variables):
            return self.is_satisfied(test_assignment)

        return True  # Assume consistent if not fully assigned


class BinaryConstraint(Constraint):
    """Binary constraint between two variables"""

    def __init__(
        self,
        var1: str,
        var2: str,
        relation: Callable[[Any, Any], bool]
    ):
        super().__init__([var1, var2])
        self.var1 = var1
        self.var2 = var2
        self.relation = relation

    def is_satisfied(self, assignment: Dict[str, Any]) -> bool:
        if self.var1 not in assignment or self.var2 not in assignment:
            return True
        return self.relation(assignment[self.var1], assignment[self.var2])


class AllDifferentConstraint(Constraint):
    """All variables must have different values"""

    def is_satisfied(self, assignment: Dict[str, Any]) -> bool:
        assigned_vars = [v for v in self.variables if v in assignment]
        values = [assignment[v] for v in assigned_vars]
        return len(values) == len(set(values))


class CSP:
    """
    Constraint Satisfaction Problem.
    """

    def __init__(self, name: str = ""):
        self.name = name

        self.variables: Dict[str, Variable] = {}
        self.constraints: List[Constraint] = []

        # Constraint lookup by variable
        self.variable_constraints: Dict[str, List[Constraint]] = {}

    def add_variable(self, name: str, domain: List[Any]):
        """Add variable"""
        self.variables[name] = Variable(
            name=name,
            domain=Domain(values=domain)
        )
        self.variable_constraints[name] = []

    def add_constraint(self, constraint: Constraint):
        """Add constraint"""
        self.constraints.append(constraint)

        for var in constraint.variables:
            if var in self.variable_constraints:
                self.variable_constraints[var].append(constraint)

    def is_consistent(
        self,
        variable: str,
        value: Any,
        assignment: Dict[str, Any]
    ) -> bool:
        """Check if assignment is consistent"""
        for constraint in self.variable_constraints.get(variable, []):
            if not constraint.is_consistent(variable, value, assignment):
                return False
        return True

    def is_complete(self, assignment: Dict[str, Any]) -> bool:
        """Check if assignment is complete"""
        return all(v in assignment for v in self.variables)

    def is_solution(self, assignment: Dict[str, Any]) -> bool:
        """Check if assignment is a solution"""
        if not self.is_complete(assignment):
            return False
        return all(c.is_satisfied(assignment) for c in self.constraints)

    def get_unassigned(self, assignment: Dict[str, Any]) -> List[str]:
        """Get unassigned variables"""
        return [v for v in self.variables if v not in assignment]

    def copy(self) -> 'CSP':
        """Create a copy"""
        new_csp = CSP(self.name)
        new_csp.variables = {
            name: var.copy()
            for name, var in self.variables.items()
        }
        new_csp.constraints = self.constraints.copy()
        new_csp.variable_constraints = {
            var: constraints.copy()
            for var, constraints in self.variable_constraints.items()
        }
        return new_csp


class ArcConsistency:
    """
    Arc consistency algorithms.
    """

    def __init__(self, csp: CSP):
        self.csp = csp

    def revise(
        self,
        xi: str,
        xj: str,
        constraint: BinaryConstraint
    ) -> bool:
        """Revise domain of xi"""
        revised = False

        domain_i = self.csp.variables[xi].domain
        domain_j = self.csp.variables[xj].domain

        to_remove = []

        for vi in domain_i.values:
            # Check if any value in xj satisfies constraint
            has_support = False
            for vj in domain_j.values:
                if constraint.relation(vi, vj):
                    has_support = True
                    break

            if not has_support:
                to_remove.append(vi)
                revised = True

        for vi in to_remove:
            domain_i.remove(vi)

        return revised

    def ac3(self) -> bool:
        """AC-3 algorithm"""
        # Initialize queue with all arcs
        queue: List[Tuple[str, str, BinaryConstraint]] = []

        for constraint in self.csp.constraints:
            if isinstance(constraint, BinaryConstraint):
                queue.append((constraint.var1, constraint.var2, constraint))
                queue.append((constraint.var2, constraint.var1, constraint))

        while queue:
            xi, xj, constraint = queue.pop(0)

            if self.revise(xi, xj, constraint):
                if self.csp.variables[xi].domain.is_empty():
                    return False  # Inconsistent

                # Add all arcs pointing to xi
                for c in self.csp.variable_constraints[xi]:
                    if isinstance(c, BinaryConstraint):
                        if c.var1 == xi:
                            queue.append((c.var2, xi, c))
                        elif c.var2 == xi:
                            queue.append((c.var1, xi, c))

        return True


class CSPSolver:
    """
    CSP solver with backtracking.
    """

    def __init__(self, csp: CSP):
        self.csp = csp

        # Statistics
        self.nodes_explored = 0
        self.backtracks = 0

    def solve(
        self,
        use_ac3: bool = True,
        use_mrv: bool = True,
        use_lcv: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Solve the CSP"""
        self.nodes_explored = 0
        self.backtracks = 0

        # Apply AC-3 preprocessing
        if use_ac3:
            ac = ArcConsistency(self.csp)
            if not ac.ac3():
                return None

        return self._backtrack({}, use_mrv, use_lcv)

    def _backtrack(
        self,
        assignment: Dict[str, Any],
        use_mrv: bool,
        use_lcv: bool
    ) -> Optional[Dict[str, Any]]:
        """Backtracking search"""
        self.nodes_explored += 1

        if self.csp.is_complete(assignment):
            return assignment

        # Select unassigned variable
        var = self._select_variable(assignment, use_mrv)

        # Order values
        values = self._order_values(var, assignment, use_lcv)

        for value in values:
            if self.csp.is_consistent(var, value, assignment):
                assignment[var] = value

                # Forward checking
                saved_domains = self._forward_check(var, value)

                if saved_domains is not None:
                    result = self._backtrack(assignment, use_mrv, use_lcv)

                    if result is not None:
                        return result

                    # Restore domains
                    self._restore_domains(saved_domains)

                del assignment[var]
                self.backtracks += 1

        return None

    def _select_variable(
        self,
        assignment: Dict[str, Any],
        use_mrv: bool
    ) -> str:
        """Select next variable (MRV heuristic)"""
        unassigned = self.csp.get_unassigned(assignment)

        if not use_mrv:
            return unassigned[0]

        # Minimum Remaining Values
        return min(
            unassigned,
            key=lambda v: len(self.csp.variables[v].domain)
        )

    def _order_values(
        self,
        variable: str,
        assignment: Dict[str, Any],
        use_lcv: bool
    ) -> List[Any]:
        """Order values (LCV heuristic)"""
        values = self.csp.variables[variable].domain.values.copy()

        if not use_lcv:
            return values

        # Least Constraining Value
        def count_conflicts(value: Any) -> int:
            conflicts = 0
            test_assignment = assignment.copy()
            test_assignment[variable] = value

            for constraint in self.csp.variable_constraints[variable]:
                for other_var in constraint.variables:
                    if other_var != variable and other_var not in assignment:
                        for other_val in self.csp.variables[other_var].domain.values:
                            if not constraint.is_consistent(other_var, other_val, test_assignment):
                                conflicts += 1

            return conflicts

        return sorted(values, key=count_conflicts)

    def _forward_check(
        self,
        variable: str,
        value: Any
    ) -> Optional[Dict[str, List[Any]]]:
        """Forward checking - prune inconsistent values"""
        saved = {}

        for constraint in self.csp.variable_constraints[variable]:
            for other_var in constraint.variables:
                if other_var != variable:
                    other_domain = self.csp.variables[other_var].domain

                    if other_var not in saved:
                        saved[other_var] = other_domain.values.copy()

                    to_remove = []
                    for other_val in other_domain.values:
                        test = {variable: value, other_var: other_val}
                        if not constraint.is_satisfied(test):
                            to_remove.append(other_val)

                    for val in to_remove:
                        other_domain.remove(val)

                    if other_domain.is_empty():
                        self._restore_domains(saved)
                        return None

        return saved

    def _restore_domains(self, saved: Dict[str, List[Any]]):
        """Restore saved domains"""
        for var, values in saved.items():
            self.csp.variables[var].domain.values = values


# Export all
__all__ = [
    'Domain',
    'Variable',
    'Constraint',
    'BinaryConstraint',
    'AllDifferentConstraint',
    'CSP',
    'ArcConsistency',
    'CSPSolver',
]
