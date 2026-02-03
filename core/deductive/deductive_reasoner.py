#!/usr/bin/env python3
"""
BAEL - Deductive Reasoner
Advanced deductive reasoning and logical proof systems.

Features:
- Propositional logic
- First-order logic
- Natural deduction
- Resolution theorem proving
- Unification
- Forward/backward chaining
- Modal logic
"""

import asyncio
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, FrozenSet, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class LogicType(Enum):
    """Types of logic systems."""
    PROPOSITIONAL = "propositional"
    FIRST_ORDER = "first_order"
    MODAL = "modal"
    TEMPORAL = "temporal"


class ConnectiveType(Enum):
    """Logical connectives."""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    IFF = "iff"
    FORALL = "forall"
    EXISTS = "exists"


class InferenceRule(Enum):
    """Inference rules."""
    MODUS_PONENS = "modus_ponens"
    MODUS_TOLLENS = "modus_tollens"
    HYPOTHETICAL_SYLLOGISM = "hypothetical_syllogism"
    DISJUNCTIVE_SYLLOGISM = "disjunctive_syllogism"
    CONJUNCTION_INTRO = "conjunction_intro"
    CONJUNCTION_ELIM = "conjunction_elim"
    DISJUNCTION_INTRO = "disjunction_intro"
    UNIVERSAL_INSTANTIATION = "universal_instantiation"
    EXISTENTIAL_INSTANTIATION = "existential_instantiation"
    RESOLUTION = "resolution"


class ProofStatus(Enum):
    """Status of a proof."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class ModalOperator(Enum):
    """Modal operators."""
    NECESSARY = "necessary"      # Box (□)
    POSSIBLE = "possible"        # Diamond (◇)
    BELIEVES = "believes"
    KNOWS = "knows"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Term:
    """A logical term."""
    term_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    is_variable: bool = False
    is_constant: bool = False
    is_function: bool = False
    arguments: List['Term'] = field(default_factory=list)


@dataclass
class Atom:
    """An atomic proposition or predicate."""
    atom_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    predicate: str = ""
    terms: List[Term] = field(default_factory=list)
    negated: bool = False


@dataclass
class Formula:
    """A logical formula."""
    formula_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connective: Optional[ConnectiveType] = None
    atom: Optional[Atom] = None
    subformulas: List['Formula'] = field(default_factory=list)
    variable: Optional[str] = None  # For quantifiers
    modal_op: Optional[ModalOperator] = None


@dataclass
class Clause:
    """A clause (disjunction of literals)."""
    clause_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    literals: Set[Tuple[str, bool]] = field(default_factory=set)  # (atom, positive)


@dataclass
class Substitution:
    """A variable substitution."""
    bindings: Dict[str, Term] = field(default_factory=dict)


@dataclass
class ProofStep:
    """A step in a proof."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    formula: Formula
    rule: InferenceRule
    premises: List[str] = field(default_factory=list)  # Step IDs
    justification: str = ""


@dataclass
class Proof:
    """A complete proof."""
    proof_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: Formula = None
    steps: List[ProofStep] = field(default_factory=list)
    status: ProofStatus = ProofStatus.PENDING


# =============================================================================
# FORMULA BUILDER
# =============================================================================

class FormulaBuilder:
    """Build logical formulas."""

    @staticmethod
    def atom(predicate: str, *args: str, negated: bool = False) -> Formula:
        """Create an atomic formula."""
        terms = [
            Term(name=arg, is_variable=arg[0].islower(), is_constant=arg[0].isupper())
            for arg in args
        ]
        return Formula(
            atom=Atom(predicate=predicate, terms=terms, negated=negated)
        )

    @staticmethod
    def prop(name: str, negated: bool = False) -> Formula:
        """Create a propositional atom."""
        return Formula(
            atom=Atom(predicate=name, negated=negated)
        )

    @staticmethod
    def neg(formula: Formula) -> Formula:
        """Negate a formula."""
        return Formula(
            connective=ConnectiveType.NOT,
            subformulas=[formula]
        )

    @staticmethod
    def conj(*formulas: Formula) -> Formula:
        """Conjunction of formulas."""
        return Formula(
            connective=ConnectiveType.AND,
            subformulas=list(formulas)
        )

    @staticmethod
    def disj(*formulas: Formula) -> Formula:
        """Disjunction of formulas."""
        return Formula(
            connective=ConnectiveType.OR,
            subformulas=list(formulas)
        )

    @staticmethod
    def implies(antecedent: Formula, consequent: Formula) -> Formula:
        """Implication."""
        return Formula(
            connective=ConnectiveType.IMPLIES,
            subformulas=[antecedent, consequent]
        )

    @staticmethod
    def iff(left: Formula, right: Formula) -> Formula:
        """Biconditional."""
        return Formula(
            connective=ConnectiveType.IFF,
            subformulas=[left, right]
        )

    @staticmethod
    def forall(variable: str, formula: Formula) -> Formula:
        """Universal quantification."""
        return Formula(
            connective=ConnectiveType.FORALL,
            subformulas=[formula],
            variable=variable
        )

    @staticmethod
    def exists(variable: str, formula: Formula) -> Formula:
        """Existential quantification."""
        return Formula(
            connective=ConnectiveType.EXISTS,
            subformulas=[formula],
            variable=variable
        )

    @staticmethod
    def necessary(formula: Formula) -> Formula:
        """Necessity modal operator."""
        return Formula(
            modal_op=ModalOperator.NECESSARY,
            subformulas=[formula]
        )

    @staticmethod
    def possible(formula: Formula) -> Formula:
        """Possibility modal operator."""
        return Formula(
            modal_op=ModalOperator.POSSIBLE,
            subformulas=[formula]
        )


# =============================================================================
# UNIFICATION
# =============================================================================

class Unifier:
    """Unification algorithm for terms."""

    def unify(
        self,
        term1: Term,
        term2: Term,
        substitution: Optional[Substitution] = None
    ) -> Optional[Substitution]:
        """Unify two terms."""
        if substitution is None:
            substitution = Substitution()

        # Apply current substitution
        term1 = self._apply_substitution(term1, substitution)
        term2 = self._apply_substitution(term2, substitution)

        # Same term
        if term1.name == term2.name and not term1.arguments and not term2.arguments:
            return substitution

        # Variable unification
        if term1.is_variable:
            return self._unify_variable(term1, term2, substitution)

        if term2.is_variable:
            return self._unify_variable(term2, term1, substitution)

        # Function unification
        if term1.is_function and term2.is_function:
            if term1.name != term2.name:
                return None
            if len(term1.arguments) != len(term2.arguments):
                return None

            for arg1, arg2 in zip(term1.arguments, term2.arguments):
                substitution = self.unify(arg1, arg2, substitution)
                if substitution is None:
                    return None

            return substitution

        # Constants must match
        if term1.is_constant and term2.is_constant:
            return substitution if term1.name == term2.name else None

        return None

    def _unify_variable(
        self,
        var: Term,
        term: Term,
        substitution: Substitution
    ) -> Optional[Substitution]:
        """Unify a variable with a term."""
        # Occurs check
        if self._occurs(var, term):
            return None

        new_sub = Substitution(bindings=substitution.bindings.copy())
        new_sub.bindings[var.name] = term
        return new_sub

    def _occurs(self, var: Term, term: Term) -> bool:
        """Check if variable occurs in term."""
        if var.name == term.name:
            return True

        for arg in term.arguments:
            if self._occurs(var, arg):
                return True

        return False

    def _apply_substitution(
        self,
        term: Term,
        substitution: Substitution
    ) -> Term:
        """Apply substitution to a term."""
        if term.is_variable and term.name in substitution.bindings:
            return substitution.bindings[term.name]

        if term.arguments:
            new_args = [
                self._apply_substitution(arg, substitution)
                for arg in term.arguments
            ]
            return Term(
                name=term.name,
                is_function=term.is_function,
                arguments=new_args
            )

        return term

    def unify_atoms(
        self,
        atom1: Atom,
        atom2: Atom
    ) -> Optional[Substitution]:
        """Unify two atoms."""
        if atom1.predicate != atom2.predicate:
            return None

        if len(atom1.terms) != len(atom2.terms):
            return None

        substitution = Substitution()

        for term1, term2 in zip(atom1.terms, atom2.terms):
            substitution = self.unify(term1, term2, substitution)
            if substitution is None:
                return None

        return substitution


# =============================================================================
# RESOLUTION PROVER
# =============================================================================

class ResolutionProver:
    """Resolution-based theorem prover."""

    def __init__(self):
        self._unifier = Unifier()

    def to_cnf(self, formula: Formula) -> List[Clause]:
        """Convert formula to Conjunctive Normal Form (clauses)."""
        # Simplistic CNF conversion for propositional logic
        clauses = []

        if formula.atom:
            clause = Clause()
            clause.literals.add((formula.atom.predicate, not formula.atom.negated))
            clauses.append(clause)

        elif formula.connective == ConnectiveType.AND:
            for subformula in formula.subformulas:
                clauses.extend(self.to_cnf(subformula))

        elif formula.connective == ConnectiveType.OR:
            # Combine literals into one clause
            clause = Clause()
            for subformula in formula.subformulas:
                sub_clauses = self.to_cnf(subformula)
                for sc in sub_clauses:
                    clause.literals.update(sc.literals)
            clauses.append(clause)

        elif formula.connective == ConnectiveType.NOT:
            if formula.subformulas[0].atom:
                atom = formula.subformulas[0].atom
                clause = Clause()
                clause.literals.add((atom.predicate, atom.negated))  # Flip
                clauses.append(clause)
            else:
                # Double negation
                if formula.subformulas[0].connective == ConnectiveType.NOT:
                    return self.to_cnf(formula.subformulas[0].subformulas[0])

        elif formula.connective == ConnectiveType.IMPLIES:
            # P -> Q = ~P v Q
            antecedent = formula.subformulas[0]
            consequent = formula.subformulas[1]
            disjunction = FormulaBuilder.disj(
                FormulaBuilder.neg(antecedent),
                consequent
            )
            return self.to_cnf(disjunction)

        return clauses if clauses else [Clause()]

    def resolve(
        self,
        clause1: Clause,
        clause2: Clause
    ) -> List[Clause]:
        """Apply resolution rule to two clauses."""
        resolvents = []

        for lit1 in clause1.literals:
            for lit2 in clause2.literals:
                # Look for complementary literals
                if lit1[0] == lit2[0] and lit1[1] != lit2[1]:
                    # Create resolvent
                    new_literals = (
                        clause1.literals - {lit1}
                    ) | (
                        clause2.literals - {lit2}
                    )

                    if new_literals:  # Not empty clause
                        resolvent = Clause(literals=new_literals)
                        resolvents.append(resolvent)
                    else:
                        # Empty clause - contradiction found
                        resolvents.append(Clause())

        return resolvents

    def prove(
        self,
        premises: List[Formula],
        goal: Formula,
        max_iterations: int = 1000
    ) -> Tuple[bool, Proof]:
        """Prove goal from premises using resolution."""
        proof = Proof(goal=goal)

        # Convert to CNF
        clauses: Set[FrozenSet[Tuple[str, bool]]] = set()

        for premise in premises:
            for clause in self.to_cnf(premise):
                clauses.add(frozenset(clause.literals))

        # Negate the goal
        negated_goal = FormulaBuilder.neg(goal)
        for clause in self.to_cnf(negated_goal):
            clauses.add(frozenset(clause.literals))

        # Resolution loop
        for _ in range(max_iterations):
            new_clauses: Set[FrozenSet[Tuple[str, bool]]] = set()

            clause_list = list(clauses)
            for i, c1 in enumerate(clause_list):
                for c2 in clause_list[i+1:]:
                    resolvents = self.resolve(
                        Clause(literals=set(c1)),
                        Clause(literals=set(c2))
                    )

                    for resolvent in resolvents:
                        if not resolvent.literals:
                            # Empty clause - proof found!
                            proof.status = ProofStatus.VALID
                            return True, proof

                        new_clauses.add(frozenset(resolvent.literals))

            if new_clauses <= clauses:
                # No new clauses
                proof.status = ProofStatus.INVALID
                return False, proof

            clauses = clauses | new_clauses

        proof.status = ProofStatus.UNKNOWN
        return False, proof


# =============================================================================
# NATURAL DEDUCTION
# =============================================================================

class NaturalDeduction:
    """Natural deduction proof system."""

    def __init__(self):
        self._steps: List[ProofStep] = []

    def apply_modus_ponens(
        self,
        implication: Formula,
        antecedent: Formula
    ) -> Optional[Formula]:
        """Apply Modus Ponens: P, P->Q |- Q."""
        if implication.connective != ConnectiveType.IMPLIES:
            return None

        if len(implication.subformulas) != 2:
            return None

        # Check antecedent matches
        impl_ant = implication.subformulas[0]
        if self._formulas_equal(impl_ant, antecedent):
            step = ProofStep(
                formula=implication.subformulas[1],
                rule=InferenceRule.MODUS_PONENS,
                justification="Modus Ponens"
            )
            self._steps.append(step)
            return implication.subformulas[1]

        return None

    def apply_modus_tollens(
        self,
        implication: Formula,
        negated_consequent: Formula
    ) -> Optional[Formula]:
        """Apply Modus Tollens: P->Q, ~Q |- ~P."""
        if implication.connective != ConnectiveType.IMPLIES:
            return None

        consequent = implication.subformulas[1]

        # Check negated consequent matches
        if negated_consequent.connective == ConnectiveType.NOT:
            if self._formulas_equal(consequent, negated_consequent.subformulas[0]):
                result = FormulaBuilder.neg(implication.subformulas[0])
                step = ProofStep(
                    formula=result,
                    rule=InferenceRule.MODUS_TOLLENS,
                    justification="Modus Tollens"
                )
                self._steps.append(step)
                return result

        return None

    def apply_conjunction_intro(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> Formula:
        """Apply Conjunction Introduction: P, Q |- P ∧ Q."""
        result = FormulaBuilder.conj(formula1, formula2)
        step = ProofStep(
            formula=result,
            rule=InferenceRule.CONJUNCTION_INTRO,
            justification="Conjunction Introduction"
        )
        self._steps.append(step)
        return result

    def apply_conjunction_elim(
        self,
        conjunction: Formula,
        left: bool = True
    ) -> Optional[Formula]:
        """Apply Conjunction Elimination: P ∧ Q |- P (or Q)."""
        if conjunction.connective != ConnectiveType.AND:
            return None

        if len(conjunction.subformulas) < 2:
            return None

        result = conjunction.subformulas[0] if left else conjunction.subformulas[1]
        step = ProofStep(
            formula=result,
            rule=InferenceRule.CONJUNCTION_ELIM,
            justification="Conjunction Elimination"
        )
        self._steps.append(step)
        return result

    def apply_disjunction_intro(
        self,
        formula: Formula,
        other: Formula
    ) -> Formula:
        """Apply Disjunction Introduction: P |- P ∨ Q."""
        result = FormulaBuilder.disj(formula, other)
        step = ProofStep(
            formula=result,
            rule=InferenceRule.DISJUNCTION_INTRO,
            justification="Disjunction Introduction"
        )
        self._steps.append(step)
        return result

    def apply_disjunctive_syllogism(
        self,
        disjunction: Formula,
        negated: Formula
    ) -> Optional[Formula]:
        """Apply Disjunctive Syllogism: P ∨ Q, ~P |- Q."""
        if disjunction.connective != ConnectiveType.OR:
            return None

        if negated.connective != ConnectiveType.NOT:
            return None

        neg_inner = negated.subformulas[0]

        for i, sub in enumerate(disjunction.subformulas):
            if self._formulas_equal(sub, neg_inner):
                # Return the other disjunct
                other_idx = 1 if i == 0 else 0
                result = disjunction.subformulas[other_idx]
                step = ProofStep(
                    formula=result,
                    rule=InferenceRule.DISJUNCTIVE_SYLLOGISM,
                    justification="Disjunctive Syllogism"
                )
                self._steps.append(step)
                return result

        return None

    def apply_hypothetical_syllogism(
        self,
        impl1: Formula,
        impl2: Formula
    ) -> Optional[Formula]:
        """Apply Hypothetical Syllogism: P->Q, Q->R |- P->R."""
        if impl1.connective != ConnectiveType.IMPLIES:
            return None
        if impl2.connective != ConnectiveType.IMPLIES:
            return None

        # Check if consequent of impl1 matches antecedent of impl2
        if self._formulas_equal(impl1.subformulas[1], impl2.subformulas[0]):
            result = FormulaBuilder.implies(
                impl1.subformulas[0],
                impl2.subformulas[1]
            )
            step = ProofStep(
                formula=result,
                rule=InferenceRule.HYPOTHETICAL_SYLLOGISM,
                justification="Hypothetical Syllogism"
            )
            self._steps.append(step)
            return result

        return None

    def _formulas_equal(self, f1: Formula, f2: Formula) -> bool:
        """Check if two formulas are structurally equal."""
        if f1.atom and f2.atom:
            return (
                f1.atom.predicate == f2.atom.predicate and
                f1.atom.negated == f2.atom.negated
            )

        if f1.connective != f2.connective:
            return False

        if len(f1.subformulas) != len(f2.subformulas):
            return False

        return all(
            self._formulas_equal(s1, s2)
            for s1, s2 in zip(f1.subformulas, f2.subformulas)
        )

    def get_proof(self, goal: Formula) -> Proof:
        """Get the current proof."""
        return Proof(
            goal=goal,
            steps=self._steps.copy(),
            status=ProofStatus.VALID if self._steps else ProofStatus.PENDING
        )


# =============================================================================
# FORWARD CHAINING
# =============================================================================

class ForwardChainer:
    """Forward chaining inference engine."""

    def __init__(self):
        self._facts: Set[str] = set()
        self._rules: List[Tuple[Set[str], str]] = []  # (antecedents, consequent)

    def add_fact(self, fact: str) -> None:
        """Add a fact."""
        self._facts.add(fact)

    def add_rule(self, antecedents: Set[str], consequent: str) -> None:
        """Add a rule: antecedents -> consequent."""
        self._rules.append((antecedents, consequent))

    def infer(self, max_iterations: int = 100) -> Set[str]:
        """Run forward chaining."""
        changed = True
        iterations = 0

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            for antecedents, consequent in self._rules:
                if consequent in self._facts:
                    continue

                if antecedents <= self._facts:
                    self._facts.add(consequent)
                    changed = True

        return self._facts.copy()

    def query(self, goal: str) -> bool:
        """Query if a fact can be derived."""
        self.infer()
        return goal in self._facts


# =============================================================================
# BACKWARD CHAINING
# =============================================================================

class BackwardChainer:
    """Backward chaining inference engine."""

    def __init__(self):
        self._facts: Set[str] = set()
        self._rules: List[Tuple[Set[str], str]] = []

    def add_fact(self, fact: str) -> None:
        """Add a fact."""
        self._facts.add(fact)

    def add_rule(self, antecedents: Set[str], consequent: str) -> None:
        """Add a rule."""
        self._rules.append((antecedents, consequent))

    def prove(
        self,
        goal: str,
        visited: Optional[Set[str]] = None
    ) -> Tuple[bool, List[str]]:
        """Prove a goal using backward chaining."""
        if visited is None:
            visited = set()

        # Prevent cycles
        if goal in visited:
            return False, []

        visited.add(goal)

        # Check if goal is a fact
        if goal in self._facts:
            return True, [f"Fact: {goal}"]

        # Try to prove using rules
        for antecedents, consequent in self._rules:
            if consequent == goal:
                # Try to prove all antecedents
                proof_steps = [f"Goal: {goal} from rule with antecedents {antecedents}"]
                all_proved = True

                for ant in antecedents:
                    proved, sub_proof = self.prove(ant, visited.copy())
                    if proved:
                        proof_steps.extend(sub_proof)
                    else:
                        all_proved = False
                        break

                if all_proved:
                    return True, proof_steps

        return False, []


# =============================================================================
# DEDUCTIVE REASONER
# =============================================================================

class DeductiveReasoner:
    """
    Deductive Reasoner for BAEL.

    Advanced deductive reasoning and logical proof systems.
    """

    def __init__(self):
        self._resolution_prover = ResolutionProver()
        self._natural_deduction = NaturalDeduction()
        self._forward_chainer = ForwardChainer()
        self._backward_chainer = BackwardChainer()
        self._unifier = Unifier()

        self._knowledge_base: List[Formula] = []

    # -------------------------------------------------------------------------
    # FORMULA BUILDING
    # -------------------------------------------------------------------------

    def atom(self, predicate: str, *args: str, negated: bool = False) -> Formula:
        """Create an atomic formula."""
        return FormulaBuilder.atom(predicate, *args, negated=negated)

    def prop(self, name: str, negated: bool = False) -> Formula:
        """Create a propositional atom."""
        return FormulaBuilder.prop(name, negated)

    def neg(self, formula: Formula) -> Formula:
        """Negate a formula."""
        return FormulaBuilder.neg(formula)

    def conj(self, *formulas: Formula) -> Formula:
        """Conjunction."""
        return FormulaBuilder.conj(*formulas)

    def disj(self, *formulas: Formula) -> Formula:
        """Disjunction."""
        return FormulaBuilder.disj(*formulas)

    def implies(self, antecedent: Formula, consequent: Formula) -> Formula:
        """Implication."""
        return FormulaBuilder.implies(antecedent, consequent)

    def forall(self, variable: str, formula: Formula) -> Formula:
        """Universal quantification."""
        return FormulaBuilder.forall(variable, formula)

    def exists(self, variable: str, formula: Formula) -> Formula:
        """Existential quantification."""
        return FormulaBuilder.exists(variable, formula)

    # -------------------------------------------------------------------------
    # KNOWLEDGE BASE
    # -------------------------------------------------------------------------

    def add_knowledge(self, formula: Formula) -> None:
        """Add formula to knowledge base."""
        self._knowledge_base.append(formula)

    def clear_knowledge(self) -> None:
        """Clear knowledge base."""
        self._knowledge_base.clear()

    # -------------------------------------------------------------------------
    # RESOLUTION
    # -------------------------------------------------------------------------

    def prove_resolution(
        self,
        goal: Formula,
        max_iterations: int = 1000
    ) -> Tuple[bool, Proof]:
        """Prove goal using resolution."""
        return self._resolution_prover.prove(
            self._knowledge_base,
            goal,
            max_iterations
        )

    # -------------------------------------------------------------------------
    # NATURAL DEDUCTION
    # -------------------------------------------------------------------------

    def modus_ponens(
        self,
        implication: Formula,
        antecedent: Formula
    ) -> Optional[Formula]:
        """Apply Modus Ponens."""
        return self._natural_deduction.apply_modus_ponens(implication, antecedent)

    def modus_tollens(
        self,
        implication: Formula,
        negated_consequent: Formula
    ) -> Optional[Formula]:
        """Apply Modus Tollens."""
        return self._natural_deduction.apply_modus_tollens(
            implication, negated_consequent
        )

    def conjunction_intro(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> Formula:
        """Apply Conjunction Introduction."""
        return self._natural_deduction.apply_conjunction_intro(formula1, formula2)

    def conjunction_elim(
        self,
        conjunction: Formula,
        left: bool = True
    ) -> Optional[Formula]:
        """Apply Conjunction Elimination."""
        return self._natural_deduction.apply_conjunction_elim(conjunction, left)

    def disjunction_intro(
        self,
        formula: Formula,
        other: Formula
    ) -> Formula:
        """Apply Disjunction Introduction."""
        return self._natural_deduction.apply_disjunction_intro(formula, other)

    def disjunctive_syllogism(
        self,
        disjunction: Formula,
        negated: Formula
    ) -> Optional[Formula]:
        """Apply Disjunctive Syllogism."""
        return self._natural_deduction.apply_disjunctive_syllogism(disjunction, negated)

    def hypothetical_syllogism(
        self,
        impl1: Formula,
        impl2: Formula
    ) -> Optional[Formula]:
        """Apply Hypothetical Syllogism."""
        return self._natural_deduction.apply_hypothetical_syllogism(impl1, impl2)

    # -------------------------------------------------------------------------
    # FORWARD/BACKWARD CHAINING
    # -------------------------------------------------------------------------

    def add_fact(self, fact: str) -> None:
        """Add a fact for chaining."""
        self._forward_chainer.add_fact(fact)
        self._backward_chainer.add_fact(fact)

    def add_rule(self, antecedents: Set[str], consequent: str) -> None:
        """Add a rule for chaining."""
        self._forward_chainer.add_rule(antecedents, consequent)
        self._backward_chainer.add_rule(antecedents, consequent)

    def forward_chain(self) -> Set[str]:
        """Run forward chaining."""
        return self._forward_chainer.infer()

    def backward_chain(self, goal: str) -> Tuple[bool, List[str]]:
        """Prove goal using backward chaining."""
        return self._backward_chainer.prove(goal)

    # -------------------------------------------------------------------------
    # UNIFICATION
    # -------------------------------------------------------------------------

    def unify(
        self,
        term1: Term,
        term2: Term
    ) -> Optional[Substitution]:
        """Unify two terms."""
        return self._unifier.unify(term1, term2)

    def unify_atoms(
        self,
        atom1: Atom,
        atom2: Atom
    ) -> Optional[Substitution]:
        """Unify two atoms."""
        return self._unifier.unify_atoms(atom1, atom2)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Deductive Reasoner."""
    print("=" * 70)
    print("BAEL - DEDUCTIVE REASONER DEMO")
    print("Advanced Logical Proof and Theorem Proving")
    print("=" * 70)
    print()

    reasoner = DeductiveReasoner()

    # 1. Propositional Logic
    print("1. PROPOSITIONAL LOGIC:")
    print("-" * 40)

    p = reasoner.prop("P")
    q = reasoner.prop("Q")
    r = reasoner.prop("R")

    p_implies_q = reasoner.implies(p, q)
    q_implies_r = reasoner.implies(q, r)

    print("   P → Q")
    print("   Q → R")

    # Hypothetical Syllogism
    p_implies_r = reasoner.hypothetical_syllogism(p_implies_q, q_implies_r)
    if p_implies_r:
        print("   Hypothetical Syllogism: P → R ✓")
    print()

    # 2. Modus Ponens
    print("2. MODUS PONENS:")
    print("-" * 40)

    print("   Given: P, P → Q")
    result = reasoner.modus_ponens(p_implies_q, p)
    if result:
        print("   Derived: Q ✓")
    print()

    # 3. Modus Tollens
    print("3. MODUS TOLLENS:")
    print("-" * 40)

    not_q = reasoner.neg(q)
    print("   Given: P → Q, ¬Q")
    result = reasoner.modus_tollens(p_implies_q, not_q)
    if result:
        print("   Derived: ¬P ✓")
    print()

    # 4. Conjunction
    print("4. CONJUNCTION RULES:")
    print("-" * 40)

    conj_pq = reasoner.conjunction_intro(p, q)
    print("   P, Q ⊢ P ∧ Q ✓")

    left = reasoner.conjunction_elim(conj_pq, left=True)
    right = reasoner.conjunction_elim(conj_pq, left=False)
    print("   P ∧ Q ⊢ P ✓")
    print("   P ∧ Q ⊢ Q ✓")
    print()

    # 5. Disjunctive Syllogism
    print("5. DISJUNCTIVE SYLLOGISM:")
    print("-" * 40)

    p_or_q = reasoner.disj(p, q)
    not_p = reasoner.neg(p)
    print("   Given: P ∨ Q, ¬P")

    result = reasoner.disjunctive_syllogism(p_or_q, not_p)
    if result:
        print("   Derived: Q ✓")
    print()

    # 6. Resolution Proof
    print("6. RESOLUTION THEOREM PROVING:")
    print("-" * 40)

    reasoner.add_knowledge(p)
    reasoner.add_knowledge(p_implies_q)

    print("   Knowledge Base: P, P → Q")
    print("   Goal: Q")

    proved, proof = reasoner.prove_resolution(q)
    print(f"   Proved: {proved}")
    print(f"   Status: {proof.status.value}")
    print()

    # 7. Forward Chaining
    print("7. FORWARD CHAINING:")
    print("-" * 40)

    reasoner.add_fact("human(Socrates)")
    reasoner.add_rule({"human(Socrates)"}, "mortal(Socrates)")
    reasoner.add_rule({"mortal(Socrates)"}, "will_die(Socrates)")

    print("   Facts: human(Socrates)")
    print("   Rules: human(X) → mortal(X), mortal(X) → will_die(X)")

    derived = reasoner.forward_chain()
    print(f"   Derived facts: {derived}")
    print()

    # 8. Backward Chaining
    print("8. BACKWARD CHAINING:")
    print("-" * 40)

    print("   Goal: will_die(Socrates)")
    proved, steps = reasoner.backward_chain("will_die(Socrates)")
    print(f"   Proved: {proved}")
    print("   Proof steps:")
    for step in steps[:5]:
        print(f"     - {step}")
    print()

    # 9. Unification
    print("9. UNIFICATION:")
    print("-" * 40)

    x = Term(name="x", is_variable=True)
    y = Term(name="y", is_variable=True)
    a = Term(name="A", is_constant=True)
    b = Term(name="B", is_constant=True)

    print("   Unify x with A")
    sub = reasoner.unify(x, a)
    if sub:
        print(f"   Substitution: {{{k}: {v.name} for k, v in sub.bindings.items()}}")

    print("   Unify A with B")
    sub = reasoner.unify(a, b)
    print(f"   Result: {sub}")  # Should be None
    print()

    # 10. Complex Example
    print("10. COMPLEX DEDUCTION:")
    print("-" * 40)

    # "If it rains, the ground is wet"
    # "If the ground is wet, plants grow"
    # "It rains"
    # Therefore: "Plants grow"

    rains = reasoner.prop("Rains")
    ground_wet = reasoner.prop("GroundWet")
    plants_grow = reasoner.prop("PlantsGrow")

    rule1 = reasoner.implies(rains, ground_wet)
    rule2 = reasoner.implies(ground_wet, plants_grow)

    print("   Premises:")
    print("     1. Rains → GroundWet")
    print("     2. GroundWet → PlantsGrow")
    print("     3. Rains")

    # Apply Modus Ponens twice
    step1 = reasoner.modus_ponens(rule1, rains)
    if step1:
        print("   Step 1: GroundWet (MP on 1,3)")
        step2 = reasoner.modus_ponens(rule2, step1)
        if step2:
            print("   Step 2: PlantsGrow (MP on 2,Step1)")
            print("   Conclusion: PlantsGrow ✓")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Deductive Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
