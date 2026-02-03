#!/usr/bin/env python3
"""
BAEL - Symbolic Reasoning System
Formal logic, theorem proving, and symbolic computation.

Features:
- Propositional and predicate logic
- Theorem proving and verification
- Rule-based reasoning
- Constraint satisfaction
- Symbolic computation
- Formal verification
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple,
                    Union)
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class LogicType(Enum):
    """Types of logic."""
    PROPOSITIONAL = "propositional"
    FIRST_ORDER = "first_order"
    MODAL = "modal"
    TEMPORAL = "temporal"
    FUZZY = "fuzzy"


class ConnectiveType(Enum):
    """Logical connectives."""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    IFF = "iff"
    XOR = "xor"


class QuantifierType(Enum):
    """Quantifiers."""
    FORALL = "forall"
    EXISTS = "exists"


class ProofStatus(Enum):
    """Proof status."""
    PROVED = "proved"
    DISPROVED = "disproved"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"


# =============================================================================
# FORMULAS
# =============================================================================

class Formula(ABC):
    """Abstract formula."""

    @abstractmethod
    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        """Evaluate formula under valuation."""
        pass

    @abstractmethod
    def variables(self) -> Set[str]:
        """Get all variables in formula."""
        pass

    @abstractmethod
    def substitute(self, substitution: Dict[str, 'Formula']) -> 'Formula':
        """Substitute variables."""
        pass

    @abstractmethod
    def to_string(self) -> str:
        """Convert to string representation."""
        pass


@dataclass
class Atom(Formula):
    """Atomic proposition."""
    name: str

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        return valuation.get(self.name, False)

    def variables(self) -> Set[str]:
        return {self.name}

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        return substitution.get(self.name, self)

    def to_string(self) -> str:
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Atom) and self.name == other.name


@dataclass
class Not(Formula):
    """Negation."""
    operand: Formula

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        return not self.operand.evaluate(valuation)

    def variables(self) -> Set[str]:
        return self.operand.variables()

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        return Not(self.operand.substitute(substitution))

    def to_string(self) -> str:
        return f"¬{self.operand.to_string()}"

    def __hash__(self):
        return hash(("not", self.operand))

    def __eq__(self, other):
        return isinstance(other, Not) and self.operand == other.operand


@dataclass
class And(Formula):
    """Conjunction."""
    left: Formula
    right: Formula

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        return self.left.evaluate(valuation) and self.right.evaluate(valuation)

    def variables(self) -> Set[str]:
        return self.left.variables() | self.right.variables()

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        return And(
            self.left.substitute(substitution),
            self.right.substitute(substitution)
        )

    def to_string(self) -> str:
        return f"({self.left.to_string()} ∧ {self.right.to_string()})"

    def __hash__(self):
        return hash(("and", self.left, self.right))

    def __eq__(self, other):
        return isinstance(other, And) and self.left == other.left and self.right == other.right


@dataclass
class Or(Formula):
    """Disjunction."""
    left: Formula
    right: Formula

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        return self.left.evaluate(valuation) or self.right.evaluate(valuation)

    def variables(self) -> Set[str]:
        return self.left.variables() | self.right.variables()

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        return Or(
            self.left.substitute(substitution),
            self.right.substitute(substitution)
        )

    def to_string(self) -> str:
        return f"({self.left.to_string()} ∨ {self.right.to_string()})"

    def __hash__(self):
        return hash(("or", self.left, self.right))

    def __eq__(self, other):
        return isinstance(other, Or) and self.left == other.left and self.right == other.right


@dataclass
class Implies(Formula):
    """Implication."""
    antecedent: Formula
    consequent: Formula

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        return not self.antecedent.evaluate(valuation) or self.consequent.evaluate(valuation)

    def variables(self) -> Set[str]:
        return self.antecedent.variables() | self.consequent.variables()

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        return Implies(
            self.antecedent.substitute(substitution),
            self.consequent.substitute(substitution)
        )

    def to_string(self) -> str:
        return f"({self.antecedent.to_string()} → {self.consequent.to_string()})"

    def __hash__(self):
        return hash(("implies", self.antecedent, self.consequent))

    def __eq__(self, other):
        return isinstance(other, Implies) and \
               self.antecedent == other.antecedent and \
               self.consequent == other.consequent


@dataclass
class Iff(Formula):
    """Biconditional."""
    left: Formula
    right: Formula

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        return self.left.evaluate(valuation) == self.right.evaluate(valuation)

    def variables(self) -> Set[str]:
        return self.left.variables() | self.right.variables()

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        return Iff(
            self.left.substitute(substitution),
            self.right.substitute(substitution)
        )

    def to_string(self) -> str:
        return f"({self.left.to_string()} ↔ {self.right.to_string()})"

    def __hash__(self):
        return hash(("iff", self.left, self.right))

    def __eq__(self, other):
        return isinstance(other, Iff) and self.left == other.left and self.right == other.right


# =============================================================================
# FIRST-ORDER LOGIC
# =============================================================================

@dataclass
class Term(ABC):
    """Abstract term."""
    pass


@dataclass
class Variable(Term):
    """Variable term."""
    name: str

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name


@dataclass
class Constant(Term):
    """Constant term."""
    name: str

    def __hash__(self):
        return hash(("const", self.name))

    def __eq__(self, other):
        return isinstance(other, Constant) and self.name == other.name


@dataclass
class Function(Term):
    """Function application."""
    name: str
    arguments: List[Term] = field(default_factory=list)

    def __hash__(self):
        return hash((self.name, tuple(self.arguments)))

    def __eq__(self, other):
        return isinstance(other, Function) and \
               self.name == other.name and \
               self.arguments == other.arguments


@dataclass
class Predicate(Formula):
    """Predicate formula."""
    name: str
    arguments: List[Term] = field(default_factory=list)

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        # For predicate logic, we need an interpretation
        key = f"{self.name}({','.join(str(a) for a in self.arguments)})"
        return valuation.get(key, False)

    def variables(self) -> Set[str]:
        result = set()
        for arg in self.arguments:
            if isinstance(arg, Variable):
                result.add(arg.name)
        return result

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        new_args = []
        for arg in self.arguments:
            if isinstance(arg, Variable) and arg.name in substitution:
                new_args.append(substitution[arg.name])
            else:
                new_args.append(arg)
        return Predicate(self.name, new_args)

    def to_string(self) -> str:
        args = ",".join(str(a.name) if isinstance(a, (Variable, Constant)) else str(a) for a in self.arguments)
        return f"{self.name}({args})"

    def __hash__(self):
        return hash((self.name, tuple(self.arguments)))

    def __eq__(self, other):
        return isinstance(other, Predicate) and \
               self.name == other.name and \
               self.arguments == other.arguments


@dataclass
class Forall(Formula):
    """Universal quantifier."""
    variable: str
    formula: Formula

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        # For now, return True (needs domain for proper evaluation)
        return True

    def variables(self) -> Set[str]:
        return self.formula.variables() - {self.variable}

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        new_sub = {k: v for k, v in substitution.items() if k != self.variable}
        return Forall(self.variable, self.formula.substitute(new_sub))

    def to_string(self) -> str:
        return f"∀{self.variable}.{self.formula.to_string()}"

    def __hash__(self):
        return hash(("forall", self.variable, self.formula))

    def __eq__(self, other):
        return isinstance(other, Forall) and \
               self.variable == other.variable and \
               self.formula == other.formula


@dataclass
class Exists(Formula):
    """Existential quantifier."""
    variable: str
    formula: Formula

    def evaluate(self, valuation: Dict[str, bool]) -> bool:
        # For now, return True (needs domain for proper evaluation)
        return True

    def variables(self) -> Set[str]:
        return self.formula.variables() - {self.variable}

    def substitute(self, substitution: Dict[str, Formula]) -> Formula:
        new_sub = {k: v for k, v in substitution.items() if k != self.variable}
        return Exists(self.variable, self.formula.substitute(new_sub))

    def to_string(self) -> str:
        return f"∃{self.variable}.{self.formula.to_string()}"

    def __hash__(self):
        return hash(("exists", self.variable, self.formula))

    def __eq__(self, other):
        return isinstance(other, Exists) and \
               self.variable == other.variable and \
               self.formula == other.formula


# =============================================================================
# RULES AND THEOREMS
# =============================================================================

@dataclass
class Rule:
    """Inference rule."""
    name: str
    premises: List[Formula]
    conclusion: Formula

    def apply(
        self,
        known_formulas: Set[Formula],
        substitution: Dict[str, Formula] = None
    ) -> Optional[Formula]:
        """Apply rule to derive conclusion."""
        substitution = substitution or {}

        # Check if all premises are satisfied
        for premise in self.premises:
            subst_premise = premise.substitute(substitution)
            if subst_premise not in known_formulas:
                return None

        return self.conclusion.substitute(substitution)


@dataclass
class Theorem:
    """A proved theorem."""
    name: str
    statement: Formula
    proof: List[str]
    axioms_used: List[str] = field(default_factory=list)


# =============================================================================
# PROVER
# =============================================================================

class Prover:
    """Theorem prover."""

    def __init__(self):
        self.axioms: Dict[str, Formula] = {}
        self.theorems: Dict[str, Theorem] = {}
        self.rules: Dict[str, Rule] = {}

        # Initialize standard rules
        self._init_rules()

    def _init_rules(self) -> None:
        """Initialize standard inference rules."""
        # Modus Ponens: P, P → Q ⊢ Q
        p = Atom("P")
        q = Atom("Q")
        self.rules["modus_ponens"] = Rule(
            name="modus_ponens",
            premises=[p, Implies(p, q)],
            conclusion=q
        )

        # Modus Tollens: ¬Q, P → Q ⊢ ¬P
        self.rules["modus_tollens"] = Rule(
            name="modus_tollens",
            premises=[Not(q), Implies(p, q)],
            conclusion=Not(p)
        )

        # Conjunction Introduction: P, Q ⊢ P ∧ Q
        self.rules["conj_intro"] = Rule(
            name="conj_intro",
            premises=[p, q],
            conclusion=And(p, q)
        )

        # Conjunction Elimination: P ∧ Q ⊢ P
        self.rules["conj_elim_left"] = Rule(
            name="conj_elim_left",
            premises=[And(p, q)],
            conclusion=p
        )

        # Disjunction Introduction: P ⊢ P ∨ Q
        self.rules["disj_intro"] = Rule(
            name="disj_intro",
            premises=[p],
            conclusion=Or(p, q)
        )

    def add_axiom(self, name: str, formula: Formula) -> None:
        """Add axiom to prover."""
        self.axioms[name] = formula

    def add_rule(self, rule: Rule) -> None:
        """Add inference rule."""
        self.rules[rule.name] = rule

    async def prove(
        self,
        goal: Formula,
        assumptions: List[Formula] = None,
        max_depth: int = 10
    ) -> Tuple[ProofStatus, List[str]]:
        """Attempt to prove goal."""
        assumptions = assumptions or []

        # Known formulas
        known: Set[Formula] = set(self.axioms.values())
        known.update(assumptions)

        # Check if goal is already known
        if goal in known:
            return (ProofStatus.PROVED, ["Goal is an axiom/assumption"])

        # Proof trace
        proof: List[str] = []

        # Forward chaining
        for depth in range(max_depth):
            new_formulas = set()

            for rule_name, rule in self.rules.items():
                # Try to find matching substitutions
                result = self._try_apply_rule(rule, known, goal)
                if result:
                    new_formula, subst = result
                    if new_formula not in known:
                        new_formulas.add(new_formula)
                        proof.append(
                            f"Step {depth + 1}: Applied {rule_name} to derive {new_formula.to_string()}"
                        )

                        if new_formula == goal:
                            return (ProofStatus.PROVED, proof)

            if not new_formulas:
                break

            known.update(new_formulas)

        # Try refutation (prove negation leads to contradiction)
        negated_goal = Not(goal)
        test_known = known.copy()
        test_known.add(negated_goal)

        if self._find_contradiction(test_known):
            proof.append("Proved by refutation (negation leads to contradiction)")
            return (ProofStatus.PROVED, proof)

        return (ProofStatus.UNKNOWN, proof)

    def _try_apply_rule(
        self,
        rule: Rule,
        known: Set[Formula],
        goal: Formula
    ) -> Optional[Tuple[Formula, Dict[str, Formula]]]:
        """Try to apply a rule."""
        # Simple pattern matching
        for premise in rule.premises:
            for formula in known:
                subst = self._unify(premise, formula)
                if subst is not None:
                    result = rule.conclusion.substitute(subst)
                    return (result, subst)
        return None

    def _unify(
        self,
        pattern: Formula,
        formula: Formula
    ) -> Optional[Dict[str, Formula]]:
        """Unify pattern with formula."""
        if isinstance(pattern, Atom):
            # Variable matches anything
            return {pattern.name: formula}
        elif type(pattern) == type(formula):
            if isinstance(pattern, Not):
                return self._unify(pattern.operand, formula.operand)
            elif isinstance(pattern, (And, Or)):
                left = self._unify(pattern.left, formula.left)
                if left is None:
                    return None
                right = self._unify(pattern.right, formula.right)
                if right is None:
                    return None
                return {**left, **right}
            elif isinstance(pattern, Implies):
                ant = self._unify(pattern.antecedent, formula.antecedent)
                if ant is None:
                    return None
                con = self._unify(pattern.consequent, formula.consequent)
                if con is None:
                    return None
                return {**ant, **con}
        return None

    def _find_contradiction(self, formulas: Set[Formula]) -> bool:
        """Check if formula set contains contradiction."""
        for f in formulas:
            if isinstance(f, Not):
                if f.operand in formulas:
                    return True
            else:
                if Not(f) in formulas:
                    return True
        return False

    async def check_satisfiability(
        self,
        formula: Formula
    ) -> Tuple[bool, Optional[Dict[str, bool]]]:
        """Check if formula is satisfiable."""
        variables = list(formula.variables())
        n = len(variables)

        # Try all valuations
        for i in range(2 ** n):
            valuation = {}
            for j, var in enumerate(variables):
                valuation[var] = bool((i >> j) & 1)

            if formula.evaluate(valuation):
                return (True, valuation)

        return (False, None)

    async def check_validity(self, formula: Formula) -> bool:
        """Check if formula is valid (tautology)."""
        # Valid if negation is unsatisfiable
        sat, _ = await self.check_satisfiability(Not(formula))
        return not sat


# =============================================================================
# CONSTRAINT SOLVER
# =============================================================================

@dataclass
class Constraint:
    """A constraint."""
    variables: List[str]
    predicate: Callable[[Dict[str, Any]], bool]
    name: str = ""


class ConstraintSolver:
    """Constraint satisfaction solver."""

    def __init__(self):
        self.variables: Dict[str, List[Any]] = {}  # Variable -> Domain
        self.constraints: List[Constraint] = []

    def add_variable(self, name: str, domain: List[Any]) -> None:
        """Add a variable with its domain."""
        self.variables[name] = domain

    def add_constraint(self, constraint: Constraint) -> None:
        """Add a constraint."""
        self.constraints.append(constraint)

    async def solve(self) -> Optional[Dict[str, Any]]:
        """Solve constraints using backtracking."""
        if not self.variables:
            return {}

        var_list = list(self.variables.keys())
        return self._backtrack({}, var_list, 0)

    def _backtrack(
        self,
        assignment: Dict[str, Any],
        variables: List[str],
        index: int
    ) -> Optional[Dict[str, Any]]:
        """Backtracking search."""
        if index == len(variables):
            return assignment.copy()

        var = variables[index]
        domain = self.variables[var]

        for value in domain:
            assignment[var] = value

            if self._is_consistent(assignment):
                result = self._backtrack(assignment, variables, index + 1)
                if result is not None:
                    return result

            del assignment[var]

        return None

    def _is_consistent(self, assignment: Dict[str, Any]) -> bool:
        """Check if assignment is consistent with constraints."""
        for constraint in self.constraints:
            # Check if all variables in constraint are assigned
            if all(v in assignment for v in constraint.variables):
                if not constraint.predicate(assignment):
                    return False
        return True

    async def solve_all(self) -> List[Dict[str, Any]]:
        """Find all solutions."""
        solutions = []
        var_list = list(self.variables.keys())
        self._find_all({}, var_list, 0, solutions)
        return solutions

    def _find_all(
        self,
        assignment: Dict[str, Any],
        variables: List[str],
        index: int,
        solutions: List[Dict[str, Any]]
    ) -> None:
        """Find all solutions."""
        if index == len(variables):
            solutions.append(assignment.copy())
            return

        var = variables[index]
        domain = self.variables[var]

        for value in domain:
            assignment[var] = value

            if self._is_consistent(assignment):
                self._find_all(assignment, variables, index + 1, solutions)

            del assignment[var]


# =============================================================================
# SYMBOLIC REASONING SYSTEM
# =============================================================================

class SymbolicReasoningSystem:
    """Main symbolic reasoning system."""

    def __init__(self):
        self.prover = Prover()
        self.constraint_solver = ConstraintSolver()

        # Knowledge base
        self.knowledge_base: Set[Formula] = set()

    def add_fact(self, formula: Formula) -> None:
        """Add fact to knowledge base."""
        self.knowledge_base.add(formula)

    def add_axiom(self, name: str, formula: Formula) -> None:
        """Add axiom."""
        self.prover.add_axiom(name, formula)

    def add_rule(self, rule: Rule) -> None:
        """Add inference rule."""
        self.prover.add_rule(rule)

    async def prove(
        self,
        goal: Formula,
        assumptions: List[Formula] = None
    ) -> Dict[str, Any]:
        """Prove a goal."""
        all_assumptions = list(self.knowledge_base)
        if assumptions:
            all_assumptions.extend(assumptions)

        status, proof = await self.prover.prove(goal, all_assumptions)

        return {
            "status": status.value,
            "proof": proof,
            "goal": goal.to_string()
        }

    async def query(self, formula: Formula) -> bool:
        """Query if formula follows from knowledge base."""
        result = await self.prove(formula)
        return result["status"] == "proved"

    async def is_satisfiable(self, formula: Formula) -> Dict[str, Any]:
        """Check satisfiability."""
        sat, model = await self.prover.check_satisfiability(formula)
        return {
            "satisfiable": sat,
            "model": model
        }

    async def is_valid(self, formula: Formula) -> bool:
        """Check validity."""
        return await self.prover.check_validity(formula)

    def define_constraint_problem(
        self,
        variables: Dict[str, List[Any]],
        constraints: List[Callable]
    ) -> None:
        """Define a constraint satisfaction problem."""
        self.constraint_solver = ConstraintSolver()

        for name, domain in variables.items():
            self.constraint_solver.add_variable(name, domain)

        for i, pred in enumerate(constraints):
            # Infer variables from predicate
            import inspect
            sig = inspect.signature(pred)
            var_names = list(variables.keys())

            self.constraint_solver.add_constraint(Constraint(
                variables=var_names,
                predicate=pred,
                name=f"constraint_{i}"
            ))

    async def solve_constraints(self) -> Optional[Dict[str, Any]]:
        """Solve constraint problem."""
        return await self.constraint_solver.solve()

    async def solve_all_constraints(self) -> List[Dict[str, Any]]:
        """Find all solutions to constraint problem."""
        return await self.constraint_solver.solve_all()

    def get_knowledge_base_size(self) -> int:
        """Get size of knowledge base."""
        return len(self.knowledge_base)


# =============================================================================
# FORMULA PARSER
# =============================================================================

class FormulaParser:
    """Parse formulas from strings."""

    def __init__(self):
        self.operators = {
            '∧': 'and', '&': 'and', 'and': 'and',
            '∨': 'or', '|': 'or', 'or': 'or',
            '¬': 'not', '~': 'not', 'not': 'not',
            '→': 'implies', '->': 'implies', 'implies': 'implies',
            '↔': 'iff', '<->': 'iff', 'iff': 'iff',
            '∀': 'forall', 'forall': 'forall',
            '∃': 'exists', 'exists': 'exists'
        }

    def parse(self, text: str) -> Formula:
        """Parse formula from text."""
        tokens = self._tokenize(text)
        return self._parse_formula(tokens, 0)[0]

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize formula string."""
        tokens = []
        i = 0

        while i < len(text):
            if text[i].isspace():
                i += 1
            elif text[i] in '(),.':
                tokens.append(text[i])
                i += 1
            elif text[i] in '∧∨¬→↔∀∃&|~':
                tokens.append(text[i])
                i += 1
            elif text[i:i+2] in ['->', '<-']:
                if text[i:i+3] == '<->':
                    tokens.append('<->')
                    i += 3
                else:
                    tokens.append('->')
                    i += 2
            elif text[i].isalnum() or text[i] == '_':
                j = i
                while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                    j += 1
                tokens.append(text[i:j])
                i = j
            else:
                i += 1

        return tokens

    def _parse_formula(
        self,
        tokens: List[str],
        pos: int
    ) -> Tuple[Formula, int]:
        """Parse formula from tokens."""
        if pos >= len(tokens):
            raise ValueError("Unexpected end of input")

        token = tokens[pos]

        # Negation
        if token in ['¬', '~', 'not']:
            operand, new_pos = self._parse_formula(tokens, pos + 1)
            return (Not(operand), new_pos)

        # Quantifiers
        if token in ['∀', 'forall']:
            var = tokens[pos + 1]
            # Skip '.'
            formula, new_pos = self._parse_formula(tokens, pos + 3)
            return (Forall(var, formula), new_pos)

        if token in ['∃', 'exists']:
            var = tokens[pos + 1]
            formula, new_pos = self._parse_formula(tokens, pos + 3)
            return (Exists(var, formula), new_pos)

        # Parenthesized formula
        if token == '(':
            left, pos = self._parse_formula(tokens, pos + 1)

            if pos < len(tokens) and tokens[pos] in self.operators:
                op = self.operators[tokens[pos]]
                right, pos = self._parse_formula(tokens, pos + 1)

                if op == 'and':
                    formula = And(left, right)
                elif op == 'or':
                    formula = Or(left, right)
                elif op == 'implies':
                    formula = Implies(left, right)
                elif op == 'iff':
                    formula = Iff(left, right)
                else:
                    formula = left
            else:
                formula = left

            # Skip closing paren
            if pos < len(tokens) and tokens[pos] == ')':
                pos += 1

            return (formula, pos)

        # Atom
        return (Atom(token), pos + 1)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo symbolic reasoning system."""
    print("=== Symbolic Reasoning System Demo ===\n")

    # Create system
    srs = SymbolicReasoningSystem()

    # 1. Propositional Logic
    print("1. Propositional Logic:")

    # Define propositions
    p = Atom("raining")
    q = Atom("wet_ground")
    r = Atom("umbrella")

    # Add facts and rules
    srs.add_fact(p)  # It's raining
    srs.add_fact(Implies(p, q))  # Rain implies wet ground
    srs.add_fact(Implies(p, r))  # Rain implies need umbrella

    print(f"   Knowledge base: {srs.get_knowledge_base_size()} formulas")
    print(f"   Fact: {p.to_string()}")
    print(f"   Rule: {Implies(p, q).to_string()}")
    print(f"   Rule: {Implies(p, r).to_string()}")

    # Query
    result = await srs.query(q)
    print(f"   Query '{q.to_string()}': {result}")

    # 2. Theorem Proving
    print("\n2. Theorem Proving:")

    # Prove wet ground
    proof_result = await srs.prove(q)
    print(f"   Goal: {proof_result['goal']}")
    print(f"   Status: {proof_result['status']}")
    for step in proof_result['proof']:
        print(f"   {step}")

    # 3. Satisfiability
    print("\n3. Satisfiability Checking:")

    # Check if (P ∧ ¬P) is satisfiable
    contradiction = And(Atom("X"), Not(Atom("X")))
    sat_result = await srs.is_satisfiable(contradiction)
    print(f"   Formula: {contradiction.to_string()}")
    print(f"   Satisfiable: {sat_result['satisfiable']}")

    # Check if (P ∨ ¬P) is satisfiable
    tautology_base = Or(Atom("X"), Not(Atom("X")))
    sat_result = await srs.is_satisfiable(tautology_base)
    print(f"   Formula: {tautology_base.to_string()}")
    print(f"   Satisfiable: {sat_result['satisfiable']}")
    print(f"   Model: {sat_result['model']}")

    # 4. Validity
    print("\n4. Validity Checking:")

    is_valid = await srs.is_valid(tautology_base)
    print(f"   {tautology_base.to_string()} is valid: {is_valid}")

    simple = Atom("Y")
    is_valid = await srs.is_valid(simple)
    print(f"   {simple.to_string()} is valid: {is_valid}")

    # 5. First-Order Logic
    print("\n5. First-Order Logic:")

    # ∀x.Human(x) → Mortal(x)
    human_pred = Predicate("Human", [Variable("x")])
    mortal_pred = Predicate("Mortal", [Variable("x")])
    mortality_rule = Forall("x", Implies(human_pred, mortal_pred))
    print(f"   Rule: {mortality_rule.to_string()}")

    # ∃x.Human(x) ∧ Philosopher(x)
    philosopher_pred = Predicate("Philosopher", [Variable("x")])
    existence = Exists("x", And(human_pred, philosopher_pred))
    print(f"   Assertion: {existence.to_string()}")

    # 6. Constraint Satisfaction
    print("\n6. Constraint Satisfaction:")

    # Simple problem: x + y = 10, x > 3, y > 2
    srs.constraint_solver = ConstraintSolver()
    srs.constraint_solver.add_variable("x", list(range(1, 10)))
    srs.constraint_solver.add_variable("y", list(range(1, 10)))

    srs.constraint_solver.add_constraint(Constraint(
        variables=["x", "y"],
        predicate=lambda a: a["x"] + a["y"] == 10,
        name="sum_constraint"
    ))
    srs.constraint_solver.add_constraint(Constraint(
        variables=["x"],
        predicate=lambda a: a["x"] > 3,
        name="x_constraint"
    ))
    srs.constraint_solver.add_constraint(Constraint(
        variables=["y"],
        predicate=lambda a: a["y"] > 2,
        name="y_constraint"
    ))

    solution = await srs.solve_constraints()
    print(f"   Problem: x + y = 10, x > 3, y > 2")
    print(f"   Solution: {solution}")

    all_solutions = await srs.solve_all_constraints()
    print(f"   All solutions: {all_solutions}")

    # 7. N-Queens
    print("\n7. N-Queens Problem (N=4):")

    n = 4
    srs.constraint_solver = ConstraintSolver()

    # Each queen's row position
    for i in range(n):
        srs.constraint_solver.add_variable(f"q{i}", list(range(n)))

    # No two queens on same row or diagonal
    for i in range(n):
        for j in range(i + 1, n):
            def make_constraint(i, j):
                return lambda a: (
                    a[f"q{i}"] != a[f"q{j}"] and  # Different rows
                    abs(a[f"q{i}"] - a[f"q{j}"]) != j - i  # Different diagonals
                )
            srs.constraint_solver.add_constraint(Constraint(
                variables=[f"q{i}", f"q{j}"],
                predicate=make_constraint(i, j),
                name=f"queens_{i}_{j}"
            ))

    solutions = await srs.solve_all_constraints()
    print(f"   Found {len(solutions)} solutions")
    if solutions:
        print(f"   First solution: {solutions[0]}")

    # 8. Formula Parsing
    print("\n8. Formula Parsing:")

    parser = FormulaParser()

    formulas = [
        "A",
        "(A & B)",
        "(A | B)",
        "(A -> B)",
        "~A"
    ]

    for f_str in formulas:
        parsed = parser.parse(f_str)
        print(f"   '{f_str}' -> {parsed.to_string()}")


if __name__ == "__main__":
    asyncio.run(demo())
