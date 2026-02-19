"""
⚡ THEOREM PROVER ⚡
===================
Automated theorem proving.

Features:
- Propositional logic
- First-order logic
- Natural deduction
- Proof search
"""

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class LogicalOperator(Enum):
    """Logical operators"""
    AND = auto()      # ∧
    OR = auto()       # ∨
    NOT = auto()      # ¬
    IMPLIES = auto()  # →
    IFF = auto()      # ↔
    FORALL = auto()   # ∀
    EXISTS = auto()   # ∃


@dataclass
class Proposition:
    """Logical proposition"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Atomic proposition
    name: str = ""

    # Compound proposition
    operator: Optional[LogicalOperator] = None
    operands: List['Proposition'] = field(default_factory=list)

    # Quantified proposition
    variable: str = ""  # For quantifiers

    def __repr__(self):
        if self.operator is None:
            return self.name

        symbols = {
            LogicalOperator.AND: '∧',
            LogicalOperator.OR: '∨',
            LogicalOperator.NOT: '¬',
            LogicalOperator.IMPLIES: '→',
            LogicalOperator.IFF: '↔',
            LogicalOperator.FORALL: '∀',
            LogicalOperator.EXISTS: '∃',
        }

        if self.operator == LogicalOperator.NOT:
            return f"¬{self.operands[0]}"
        elif self.operator in [LogicalOperator.FORALL, LogicalOperator.EXISTS]:
            return f"{symbols[self.operator]}{self.variable}.{self.operands[0]}"
        else:
            return f"({self.operands[0]} {symbols[self.operator]} {self.operands[1]})"

    def __and__(self, other: 'Proposition') -> 'Proposition':
        return Proposition(operator=LogicalOperator.AND, operands=[self, other])

    def __or__(self, other: 'Proposition') -> 'Proposition':
        return Proposition(operator=LogicalOperator.OR, operands=[self, other])

    def __invert__(self) -> 'Proposition':
        return Proposition(operator=LogicalOperator.NOT, operands=[self])

    def implies(self, other: 'Proposition') -> 'Proposition':
        return Proposition(operator=LogicalOperator.IMPLIES, operands=[self, other])

    def iff(self, other: 'Proposition') -> 'Proposition':
        return Proposition(operator=LogicalOperator.IFF, operands=[self, other])

    def is_atomic(self) -> bool:
        return self.operator is None

    def get_atoms(self) -> Set[str]:
        """Get all atomic propositions"""
        if self.is_atomic():
            return {self.name}

        atoms = set()
        for operand in self.operands:
            atoms.update(operand.get_atoms())
        return atoms

    def evaluate(self, assignment: Dict[str, bool]) -> bool:
        """Evaluate proposition under assignment"""
        if self.is_atomic():
            return assignment.get(self.name, False)

        if self.operator == LogicalOperator.NOT:
            return not self.operands[0].evaluate(assignment)
        elif self.operator == LogicalOperator.AND:
            return all(op.evaluate(assignment) for op in self.operands)
        elif self.operator == LogicalOperator.OR:
            return any(op.evaluate(assignment) for op in self.operands)
        elif self.operator == LogicalOperator.IMPLIES:
            p, q = self.operands
            return (not p.evaluate(assignment)) or q.evaluate(assignment)
        elif self.operator == LogicalOperator.IFF:
            p, q = self.operands
            return p.evaluate(assignment) == q.evaluate(assignment)

        return False


@dataclass
class ProofStep:
    """Single step in a proof"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    proposition: Proposition = None

    # Justification
    rule: str = ""  # Name of inference rule
    premises: List[str] = field(default_factory=list)  # IDs of premises used

    # Line number in proof
    line_number: int = 0

    def __repr__(self):
        return f"{self.line_number}. {self.proposition} [{self.rule}]"


@dataclass
class Proof:
    """A proof derivation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Goal to prove
    goal: Proposition = None

    # Assumptions
    assumptions: List[Proposition] = field(default_factory=list)

    # Proof steps
    steps: List[ProofStep] = field(default_factory=list)

    # Status
    is_complete: bool = False

    def add_step(
        self,
        proposition: Proposition,
        rule: str,
        premises: List[str] = None
    ) -> ProofStep:
        """Add step to proof"""
        step = ProofStep(
            proposition=proposition,
            rule=rule,
            premises=premises or [],
            line_number=len(self.steps) + 1
        )
        self.steps.append(step)

        # Check if goal reached
        if self._propositions_equal(proposition, self.goal):
            self.is_complete = True

        return step

    def _propositions_equal(self, p1: Proposition, p2: Proposition) -> bool:
        """Check if two propositions are structurally equal"""
        if p1.is_atomic() and p2.is_atomic():
            return p1.name == p2.name

        if p1.operator != p2.operator:
            return False

        if len(p1.operands) != len(p2.operands):
            return False

        return all(
            self._propositions_equal(o1, o2)
            for o1, o2 in zip(p1.operands, p2.operands)
        )


@dataclass
class Axiom:
    """Logical axiom"""
    name: str
    schema: Proposition


@dataclass
class Theorem:
    """Proven theorem"""
    name: str
    statement: Proposition
    proof: Optional[Proof] = None

    # Dependencies
    uses_theorems: List[str] = field(default_factory=list)


class ProofStrategy(Enum):
    """Proof strategies"""
    DIRECT = auto()
    CONTRADICTION = auto()
    INDUCTION = auto()
    CASE_ANALYSIS = auto()
    FORWARD_CHAINING = auto()
    BACKWARD_CHAINING = auto()


class TheoremProver:
    """
    Automated theorem prover.
    """

    def __init__(self):
        self.axioms: Dict[str, Axiom] = {}
        self.theorems: Dict[str, Theorem] = {}

        # Initialize standard axioms
        self._init_axioms()

    def _init_axioms(self):
        """Initialize logical axioms"""
        p = Proposition(name="P")
        q = Proposition(name="Q")
        r = Proposition(name="R")

        # Axiom schemas
        self.axioms['identity'] = Axiom(
            name="Identity",
            schema=p.implies(p)  # P → P
        )

        self.axioms['explosion'] = Axiom(
            name="Explosion",
            schema=(p & ~p).implies(q)  # (P ∧ ¬P) → Q
        )

    def prove(
        self,
        goal: Proposition,
        assumptions: List[Proposition] = None,
        strategy: ProofStrategy = ProofStrategy.DIRECT
    ) -> Optional[Proof]:
        """Attempt to prove goal from assumptions"""
        proof = Proof(goal=goal, assumptions=assumptions or [])

        # Add assumptions as premises
        for i, assumption in enumerate(proof.assumptions):
            proof.add_step(assumption, "assumption")

        if strategy == ProofStrategy.DIRECT:
            return self._prove_direct(proof)
        elif strategy == ProofStrategy.CONTRADICTION:
            return self._prove_contradiction(proof)
        elif strategy == ProofStrategy.CASE_ANALYSIS:
            return self._prove_cases(proof)

        return None

    def _prove_direct(self, proof: Proof) -> Optional[Proof]:
        """Direct proof by forward chaining"""
        # Simple truth table check for propositional logic
        atoms = proof.goal.get_atoms()
        for assumption in proof.assumptions:
            atoms.update(assumption.get_atoms())

        atoms = list(atoms)
        n = len(atoms)

        # Check all assignments
        for i in range(2 ** n):
            assignment = {
                atom: bool((i >> j) & 1)
                for j, atom in enumerate(atoms)
            }

            # Check if assumptions are satisfied
            all_assumptions = all(
                a.evaluate(assignment) for a in proof.assumptions
            )

            if all_assumptions and not proof.goal.evaluate(assignment):
                # Found counterexample
                return None

        # Valid - construct proof
        proof.add_step(proof.goal, "truth table")
        proof.is_complete = True
        return proof

    def _prove_contradiction(self, proof: Proof) -> Optional[Proof]:
        """Proof by contradiction"""
        # Assume negation of goal
        negated = ~proof.goal
        extended_assumptions = proof.assumptions + [negated]

        # Try to derive contradiction
        atoms = negated.get_atoms()
        for a in extended_assumptions:
            atoms.update(a.get_atoms())

        atoms = list(atoms)
        n = len(atoms)

        # Check if assumptions are consistent
        consistent = False
        for i in range(2 ** n):
            assignment = {
                atom: bool((i >> j) & 1)
                for j, atom in enumerate(atoms)
            }

            if all(a.evaluate(assignment) for a in extended_assumptions):
                consistent = True
                break

        if not consistent:
            # Contradiction found
            proof.add_step(negated, "assumption (contradiction)")
            proof.add_step(
                Proposition(name="⊥", operator=None),
                "contradiction"
            )
            proof.add_step(proof.goal, "proof by contradiction")
            proof.is_complete = True
            return proof

        return None

    def _prove_cases(self, proof: Proof) -> Optional[Proof]:
        """Proof by case analysis"""
        # Try to find a disjunction in assumptions
        for assumption in proof.assumptions:
            if assumption.operator == LogicalOperator.OR:
                case1, case2 = assumption.operands

                # Try to prove goal from each case
                proof1 = self.prove(
                    proof.goal,
                    proof.assumptions + [case1],
                    ProofStrategy.DIRECT
                )
                proof2 = self.prove(
                    proof.goal,
                    proof.assumptions + [case2],
                    ProofStrategy.DIRECT
                )

                if proof1 and proof2:
                    proof.add_step(proof.goal, "case analysis")
                    proof.is_complete = True
                    return proof

        return None

    def is_tautology(self, prop: Proposition) -> bool:
        """Check if proposition is a tautology"""
        atoms = list(prop.get_atoms())
        n = len(atoms)

        for i in range(2 ** n):
            assignment = {
                atom: bool((i >> j) & 1)
                for j, atom in enumerate(atoms)
            }

            if not prop.evaluate(assignment):
                return False

        return True

    def is_satisfiable(self, prop: Proposition) -> Tuple[bool, Optional[Dict[str, bool]]]:
        """Check if proposition is satisfiable"""
        atoms = list(prop.get_atoms())
        n = len(atoms)

        for i in range(2 ** n):
            assignment = {
                atom: bool((i >> j) & 1)
                for j, atom in enumerate(atoms)
            }

            if prop.evaluate(assignment):
                return True, assignment

        return False, None


class NaturalDeduction:
    """
    Natural deduction proof system.
    """

    def __init__(self):
        self.rules = {
            'and_intro': self._and_intro,
            'and_elim_left': self._and_elim_left,
            'and_elim_right': self._and_elim_right,
            'or_intro_left': self._or_intro_left,
            'or_intro_right': self._or_intro_right,
            'implies_intro': self._implies_intro,
            'implies_elim': self._implies_elim,
            'not_intro': self._not_intro,
            'not_elim': self._not_elim,
        }

    def _and_intro(
        self,
        p: Proposition,
        q: Proposition
    ) -> Proposition:
        """∧-introduction: P, Q ⊢ P ∧ Q"""
        return p & q

    def _and_elim_left(self, pq: Proposition) -> Optional[Proposition]:
        """∧-elimination: P ∧ Q ⊢ P"""
        if pq.operator == LogicalOperator.AND:
            return pq.operands[0]
        return None

    def _and_elim_right(self, pq: Proposition) -> Optional[Proposition]:
        """∧-elimination: P ∧ Q ⊢ Q"""
        if pq.operator == LogicalOperator.AND:
            return pq.operands[1]
        return None

    def _or_intro_left(
        self,
        p: Proposition,
        q: Proposition
    ) -> Proposition:
        """∨-introduction: P ⊢ P ∨ Q"""
        return p | q

    def _or_intro_right(
        self,
        p: Proposition,
        q: Proposition
    ) -> Proposition:
        """∨-introduction: Q ⊢ P ∨ Q"""
        return p | q

    def _implies_intro(
        self,
        p: Proposition,
        q: Proposition
    ) -> Proposition:
        """→-introduction: If we can derive Q from P, then P → Q"""
        return p.implies(q)

    def _implies_elim(
        self,
        impl: Proposition,
        p: Proposition
    ) -> Optional[Proposition]:
        """→-elimination (modus ponens): P → Q, P ⊢ Q"""
        if impl.operator == LogicalOperator.IMPLIES:
            if self._equal(impl.operands[0], p):
                return impl.operands[1]
        return None

    def _not_intro(self, p: Proposition) -> Proposition:
        """¬-introduction: If P leads to contradiction, then ¬P"""
        return ~p

    def _not_elim(self, notp: Proposition) -> Optional[Proposition]:
        """¬-elimination (double negation): ¬¬P ⊢ P"""
        if notp.operator == LogicalOperator.NOT:
            inner = notp.operands[0]
            if inner.operator == LogicalOperator.NOT:
                return inner.operands[0]
        return None

    def _equal(self, p1: Proposition, p2: Proposition) -> bool:
        """Check structural equality"""
        if p1.is_atomic() and p2.is_atomic():
            return p1.name == p2.name
        if p1.operator != p2.operator:
            return False
        if len(p1.operands) != len(p2.operands):
            return False
        return all(self._equal(a, b) for a, b in zip(p1.operands, p2.operands))

    def apply_rule(
        self,
        rule_name: str,
        *args
    ) -> Optional[Proposition]:
        """Apply inference rule"""
        if rule_name in self.rules:
            return self.rules[rule_name](*args)
        return None


# Export all
__all__ = [
    'LogicalOperator',
    'Proposition',
    'ProofStep',
    'Proof',
    'Axiom',
    'Theorem',
    'ProofStrategy',
    'TheoremProver',
    'NaturalDeduction',
]
