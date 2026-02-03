#!/usr/bin/env python3
"""
BAEL - Relevance Reasoner
Advanced relevance logic and reasoning.

Features:
- Relevance implication
- Variable sharing
- Relevant entailment
- Anderson-Belnap logic
- Information containment
- Relevant deduction
"""

import asyncio
import copy
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class RelevanceType(Enum):
    """Types of relevance relations."""
    VARIABLE_SHARING = "variable_sharing"  # Share variables
    CONTENT_OVERLAP = "content_overlap"  # Share content
    CAUSAL = "causal"  # Causally related
    INFORMATIONAL = "informational"  # Information flow


class ConnectiveType(Enum):
    """Types of logical connectives."""
    CONJUNCTION = "conjunction"  # &
    DISJUNCTION = "disjunction"  # ∨
    INTENSIONAL_DISJUNCTION = "intensional_disjunction"  # ⊕ (fusion)
    RELEVANT_IMPLICATION = "relevant_implication"  # →
    ENTAILMENT = "entailment"  # ⊢
    NEGATION = "negation"  # ¬


class LogicSystem(Enum):
    """Relevant logic systems."""
    R = "r"  # Anderson-Belnap R
    E = "e"  # System E (entailment)
    T = "t"  # Ticket entailment
    RM = "rm"  # R-mingle


class DeductionStatus(Enum):
    """Status of a deduction."""
    VALID = "valid"
    INVALID = "invalid"
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Variable:
    """A propositional variable."""
    var_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, Variable):
            return False
        return self.name == other.name

    def __str__(self):
        return self.name


@dataclass
class Formula:
    """A formula in relevance logic."""
    formula_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connective: Optional[ConnectiveType] = None
    variables: Set[str] = field(default_factory=set)
    subformulas: List['Formula'] = field(default_factory=list)
    atomic: Optional[str] = None

    def __str__(self):
        if self.atomic:
            return self.atomic
        if self.connective == ConnectiveType.NEGATION:
            return f"¬{self.subformulas[0]}"
        if self.connective == ConnectiveType.CONJUNCTION:
            return f"({self.subformulas[0]} & {self.subformulas[1]})"
        if self.connective == ConnectiveType.DISJUNCTION:
            return f"({self.subformulas[0]} ∨ {self.subformulas[1]})"
        if self.connective == ConnectiveType.RELEVANT_IMPLICATION:
            return f"({self.subformulas[0]} → {self.subformulas[1]})"
        if self.connective == ConnectiveType.ENTAILMENT:
            return f"({self.subformulas[0]} ⊢ {self.subformulas[1]})"
        if self.connective == ConnectiveType.INTENSIONAL_DISJUNCTION:
            return f"({self.subformulas[0]} ⊕ {self.subformulas[1]})"
        return "?"


@dataclass
class RelevanceRelation:
    """A relevance relation between formulas."""
    rel_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    formula1: str = ""
    formula2: str = ""
    relevance_type: RelevanceType = RelevanceType.VARIABLE_SHARING
    strength: float = 1.0


@dataclass
class Deduction:
    """A relevant deduction."""
    ded_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    premises: List[str] = field(default_factory=list)
    conclusion: str = ""
    status: DeductionStatus = DeductionStatus.VALID
    used_premises: Set[int] = field(default_factory=set)


@dataclass
class RelevanceProof:
    """Proof of relevance."""
    proof_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    formula1: str = ""
    formula2: str = ""
    shared_variables: Set[str] = field(default_factory=set)
    relevance_chain: List[str] = field(default_factory=list)
    is_relevant: bool = False


# =============================================================================
# FORMULA BUILDER
# =============================================================================

class FormulaBuilder:
    """Build formulas in relevance logic."""

    def __init__(self):
        self._formulas: Dict[str, Formula] = {}

    def atom(self, name: str) -> Formula:
        """Create an atomic formula."""
        f = Formula(
            atomic=name,
            variables={name}
        )
        self._formulas[str(f)] = f
        return f

    def negation(self, sub: Formula) -> Formula:
        """Create negation."""
        f = Formula(
            connective=ConnectiveType.NEGATION,
            variables=sub.variables.copy(),
            subformulas=[sub]
        )
        self._formulas[str(f)] = f
        return f

    def conjunction(self, left: Formula, right: Formula) -> Formula:
        """Create conjunction (intensional)."""
        f = Formula(
            connective=ConnectiveType.CONJUNCTION,
            variables=left.variables | right.variables,
            subformulas=[left, right]
        )
        self._formulas[str(f)] = f
        return f

    def disjunction(self, left: Formula, right: Formula) -> Formula:
        """Create disjunction."""
        f = Formula(
            connective=ConnectiveType.DISJUNCTION,
            variables=left.variables | right.variables,
            subformulas=[left, right]
        )
        self._formulas[str(f)] = f
        return f

    def implication(self, antecedent: Formula, consequent: Formula) -> Formula:
        """Create relevant implication (→)."""
        f = Formula(
            connective=ConnectiveType.RELEVANT_IMPLICATION,
            variables=antecedent.variables | consequent.variables,
            subformulas=[antecedent, consequent]
        )
        self._formulas[str(f)] = f
        return f

    def entailment(self, premise: Formula, conclusion: Formula) -> Formula:
        """Create entailment (⊢)."""
        f = Formula(
            connective=ConnectiveType.ENTAILMENT,
            variables=premise.variables | conclusion.variables,
            subformulas=[premise, conclusion]
        )
        self._formulas[str(f)] = f
        return f

    def fusion(self, left: Formula, right: Formula) -> Formula:
        """Create intensional disjunction (fusion ⊕)."""
        f = Formula(
            connective=ConnectiveType.INTENSIONAL_DISJUNCTION,
            variables=left.variables | right.variables,
            subformulas=[left, right]
        )
        self._formulas[str(f)] = f
        return f

    def get_variables(self, formula: Formula) -> Set[str]:
        """Get all variables in formula."""
        return formula.variables


# =============================================================================
# RELEVANCE CHECKER
# =============================================================================

class RelevanceChecker:
    """Check relevance between formulas."""

    def __init__(self):
        self._cache: Dict[Tuple[str, str], bool] = {}

    def variable_sharing(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> RelevanceProof:
        """Check variable sharing between formulas."""
        shared = formula1.variables & formula2.variables

        is_relevant = len(shared) > 0

        return RelevanceProof(
            formula1=str(formula1),
            formula2=str(formula2),
            shared_variables=shared,
            is_relevant=is_relevant
        )

    def content_overlap(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> float:
        """Measure content overlap."""
        if not formula1.variables and not formula2.variables:
            return 0.0

        shared = len(formula1.variables & formula2.variables)
        total = len(formula1.variables | formula2.variables)

        return shared / total if total > 0 else 0.0

    def is_relevant(
        self,
        formula1: Formula,
        formula2: Formula,
        relevance_type: RelevanceType = RelevanceType.VARIABLE_SHARING
    ) -> bool:
        """Check if two formulas are relevant to each other."""
        key = (str(formula1), str(formula2))
        if key in self._cache:
            return self._cache[key]

        if relevance_type == RelevanceType.VARIABLE_SHARING:
            proof = self.variable_sharing(formula1, formula2)
            result = proof.is_relevant
        else:
            overlap = self.content_overlap(formula1, formula2)
            result = overlap > 0

        self._cache[key] = result
        return result


# =============================================================================
# RELEVANT IMPLICATION
# =============================================================================

class RelevantImplication:
    """Evaluate relevant implication."""

    def __init__(self, relevance_checker: RelevanceChecker):
        self._checker = relevance_checker

    def is_valid_implication(
        self,
        antecedent: Formula,
        consequent: Formula
    ) -> bool:
        """
        Check if A → B is valid in relevance logic.

        Key property: the antecedent must be relevant to the consequent.
        This blocks material implication paradoxes.
        """
        return self._checker.is_relevant(antecedent, consequent)

    def evaluate_implication(
        self,
        antecedent: Formula,
        consequent: Formula,
        antecedent_true: bool,
        consequent_true: bool
    ) -> Optional[bool]:
        """
        Evaluate A → B with given truth values.

        In relevance logic:
        - If A and B are not relevant, A → B is undefined
        - Otherwise, follows standard evaluation
        """
        if not self._checker.is_relevant(antecedent, consequent):
            return None  # Undefined - not relevant

        # Standard evaluation for relevant formulas
        if antecedent_true and not consequent_true:
            return False
        return True


# =============================================================================
# DEDUCTION VALIDATOR
# =============================================================================

class DeductionValidator:
    """Validate deductions in relevance logic."""

    def __init__(self, builder: FormulaBuilder, checker: RelevanceChecker):
        self._builder = builder
        self._checker = checker

    def validate_deduction(
        self,
        premises: List[Formula],
        conclusion: Formula
    ) -> Deduction:
        """
        Validate a deduction.

        In relevance logic:
        - All premises must be used (no weakening with irrelevant premises)
        - Premises must be relevant to conclusion
        """
        used_premises: Set[int] = set()
        all_relevant = True

        # Check each premise for relevance to conclusion
        for i, premise in enumerate(premises):
            if self._checker.is_relevant(premise, conclusion):
                used_premises.add(i)
            else:
                all_relevant = False

        # Also check premise-to-premise relevance chains
        for i, p1 in enumerate(premises):
            for j, p2 in enumerate(premises):
                if i != j and self._checker.is_relevant(p1, p2):
                    if self._checker.is_relevant(p2, conclusion):
                        used_premises.add(i)

        if len(used_premises) == len(premises) and all_relevant:
            status = DeductionStatus.RELEVANT
        elif len(used_premises) > 0:
            status = DeductionStatus.VALID  # Valid but not all relevant
        else:
            status = DeductionStatus.IRRELEVANT

        return Deduction(
            premises=[str(p) for p in premises],
            conclusion=str(conclusion),
            status=status,
            used_premises=used_premises
        )

    def modus_ponens(
        self,
        p: Formula,
        p_implies_q: Formula
    ) -> Optional[Deduction]:
        """
        Relevant modus ponens.

        From P and P → Q, derive Q.
        Only valid if P is actually relevant to Q.
        """
        if p_implies_q.connective != ConnectiveType.RELEVANT_IMPLICATION:
            return None

        antecedent = p_implies_q.subformulas[0]
        consequent = p_implies_q.subformulas[1]

        # Check if p matches antecedent
        if str(p) != str(antecedent):
            return None

        # Check relevance
        if not self._checker.is_relevant(p, consequent):
            return Deduction(
                premises=[str(p), str(p_implies_q)],
                conclusion=str(consequent),
                status=DeductionStatus.IRRELEVANT
            )

        return Deduction(
            premises=[str(p), str(p_implies_q)],
            conclusion=str(consequent),
            status=DeductionStatus.RELEVANT,
            used_premises={0, 1}
        )


# =============================================================================
# RELEVANCE LOGIC SYSTEMS
# =============================================================================

class RelevanceLogicSystem:
    """Different relevance logic systems."""

    def __init__(self, system: LogicSystem = LogicSystem.R):
        self.system = system

    def axiom_schemes(self) -> List[str]:
        """Get axiom schemes for this system."""
        axioms = []

        # Common to all relevance logics
        axioms.append("A → A")  # Identity
        axioms.append("(A → B) → ((B → C) → (A → C))")  # Suffixing
        axioms.append("(A → (A → B)) → (A → B)")  # Contraction
        axioms.append("(A & B) → A")  # Simplification
        axioms.append("(A & B) → B")  # Simplification
        axioms.append("((A → B) & (A → C)) → (A → (B & C))")
        axioms.append("A → (A ∨ B)")  # Addition
        axioms.append("B → (A ∨ B)")  # Addition
        axioms.append("((A → C) & (B → C)) → ((A ∨ B) → C)")
        axioms.append("(A & (B ∨ C)) → ((A & B) ∨ (A & C))")  # Distribution
        axioms.append("¬¬A → A")  # Double negation
        axioms.append("(A → ¬B) → (B → ¬A)")  # Contraposition

        if self.system == LogicSystem.R:
            # R-specific
            axioms.append("(A → B) → ((C → A) → (C → B))")  # Prefixing

        elif self.system == LogicSystem.E:
            # E-specific (stronger than R)
            axioms.append("((A → A) → B) → B")  # Necessity of identity

        elif self.system == LogicSystem.RM:
            # R-Mingle (weaker, allows A → (A → A))
            axioms.append("A → (A → A)")  # Mingle

        return axioms

    def inference_rules(self) -> List[str]:
        """Get inference rules."""
        rules = [
            "From A and A → B, infer B (Modus Ponens)",
            "From A and B, infer A & B (Adjunction)"
        ]

        if self.system == LogicSystem.E:
            rules.append("From A, infer (B → B) → A (Necessitation variant)")

        return rules


# =============================================================================
# INFORMATION CONTAINMENT
# =============================================================================

class InformationContainment:
    """Check information containment between formulas."""

    def __init__(self):
        pass

    def contains(self, formula1: Formula, formula2: Formula) -> bool:
        """Check if formula1 contains all information in formula2."""
        return formula2.variables.issubset(formula1.variables)

    def information_overlap(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> float:
        """Measure information overlap."""
        if not formula2.variables:
            return 1.0 if not formula1.variables else 0.0

        contained = len(formula1.variables & formula2.variables)
        total = len(formula2.variables)

        return contained / total if total > 0 else 0.0

    def minimal_information(
        self,
        formulas: List[Formula]
    ) -> Set[str]:
        """Find minimal information set (intersection of all)."""
        if not formulas:
            return set()

        result = formulas[0].variables.copy()
        for f in formulas[1:]:
            result &= f.variables

        return result


# =============================================================================
# RELEVANCE REASONER
# =============================================================================

class RelevanceReasoner:
    """
    Relevance Reasoner for BAEL.

    Advanced relevance logic and reasoning.
    """

    def __init__(self, system: LogicSystem = LogicSystem.R):
        self._builder = FormulaBuilder()
        self._checker = RelevanceChecker()
        self._implication = RelevantImplication(self._checker)
        self._validator = DeductionValidator(self._builder, self._checker)
        self._system = RelevanceLogicSystem(system)
        self._containment = InformationContainment()

    # -------------------------------------------------------------------------
    # FORMULA BUILDING
    # -------------------------------------------------------------------------

    def atom(self, name: str) -> Formula:
        """Create an atomic formula."""
        return self._builder.atom(name)

    def neg(self, formula: Formula) -> Formula:
        """Negate a formula."""
        return self._builder.negation(formula)

    def conj(self, left: Formula, right: Formula) -> Formula:
        """Create conjunction."""
        return self._builder.conjunction(left, right)

    def disj(self, left: Formula, right: Formula) -> Formula:
        """Create disjunction."""
        return self._builder.disjunction(left, right)

    def implies(self, antecedent: Formula, consequent: Formula) -> Formula:
        """Create relevant implication."""
        return self._builder.implication(antecedent, consequent)

    def entails(self, premise: Formula, conclusion: Formula) -> Formula:
        """Create entailment."""
        return self._builder.entailment(premise, conclusion)

    def fusion(self, left: Formula, right: Formula) -> Formula:
        """Create fusion (intensional disjunction)."""
        return self._builder.fusion(left, right)

    def get_variables(self, formula: Formula) -> Set[str]:
        """Get all variables in formula."""
        return self._builder.get_variables(formula)

    # -------------------------------------------------------------------------
    # RELEVANCE CHECKING
    # -------------------------------------------------------------------------

    def check_relevance(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> RelevanceProof:
        """Check relevance between formulas."""
        return self._checker.variable_sharing(formula1, formula2)

    def is_relevant(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> bool:
        """Check if two formulas are relevant."""
        return self._checker.is_relevant(formula1, formula2)

    def content_overlap(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> float:
        """Measure content overlap."""
        return self._checker.content_overlap(formula1, formula2)

    # -------------------------------------------------------------------------
    # IMPLICATION
    # -------------------------------------------------------------------------

    def valid_implication(
        self,
        antecedent: Formula,
        consequent: Formula
    ) -> bool:
        """Check if implication is valid."""
        return self._implication.is_valid_implication(antecedent, consequent)

    def evaluate_implication(
        self,
        antecedent: Formula,
        consequent: Formula,
        ant_true: bool,
        cons_true: bool
    ) -> Optional[bool]:
        """Evaluate implication with truth values."""
        return self._implication.evaluate_implication(
            antecedent, consequent, ant_true, cons_true
        )

    # -------------------------------------------------------------------------
    # DEDUCTION
    # -------------------------------------------------------------------------

    def validate_deduction(
        self,
        premises: List[Formula],
        conclusion: Formula
    ) -> Deduction:
        """Validate a deduction."""
        return self._validator.validate_deduction(premises, conclusion)

    def modus_ponens(
        self,
        p: Formula,
        p_implies_q: Formula
    ) -> Optional[Deduction]:
        """Apply relevant modus ponens."""
        return self._validator.modus_ponens(p, p_implies_q)

    # -------------------------------------------------------------------------
    # LOGIC SYSTEM
    # -------------------------------------------------------------------------

    def get_system(self) -> LogicSystem:
        """Get current logic system."""
        return self._system.system

    def axiom_schemes(self) -> List[str]:
        """Get axiom schemes."""
        return self._system.axiom_schemes()

    def inference_rules(self) -> List[str]:
        """Get inference rules."""
        return self._system.inference_rules()

    # -------------------------------------------------------------------------
    # INFORMATION
    # -------------------------------------------------------------------------

    def contains_info(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> bool:
        """Check if formula1 contains info of formula2."""
        return self._containment.contains(formula1, formula2)

    def info_overlap(
        self,
        formula1: Formula,
        formula2: Formula
    ) -> float:
        """Measure information overlap."""
        return self._containment.information_overlap(formula1, formula2)

    def minimal_info(self, formulas: List[Formula]) -> Set[str]:
        """Find minimal information set."""
        return self._containment.minimal_information(formulas)

    # -------------------------------------------------------------------------
    # PARADOX PREVENTION
    # -------------------------------------------------------------------------

    def blocks_explosion(
        self,
        p: Formula,
        not_p: Formula,
        arbitrary_q: Formula
    ) -> bool:
        """
        Check that relevance logic blocks explosion.

        Classical: P, ¬P ⊢ Q (anything follows from contradiction)
        Relevance: Only if P is relevant to Q
        """
        # Check if P and Q share variables
        return not self.is_relevant(p, arbitrary_q)

    def blocks_material_implication_paradoxes(
        self,
        p: Formula,
        q: Formula
    ) -> bool:
        """
        Check that relevance logic blocks material implication paradoxes.

        Classical: Q ⊢ P → Q (true conclusion implies anything implies it)
        Classical: ¬P ⊢ P → Q (false antecedent makes implication true)
        Relevance: Blocks both if P and Q are not relevant
        """
        return not self.is_relevant(p, q)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Relevance Reasoner."""
    print("=" * 70)
    print("BAEL - RELEVANCE REASONER DEMO")
    print("Advanced Relevance Logic and Reasoning")
    print("=" * 70)
    print()

    reasoner = RelevanceReasoner(LogicSystem.R)

    # 1. Create Atomic Formulas
    print("1. CREATE ATOMIC FORMULAS:")
    print("-" * 40)

    p = reasoner.atom("P")
    q = reasoner.atom("Q")
    r = reasoner.atom("R")
    s = reasoner.atom("S")

    print(f"   P: {p}")
    print(f"   Q: {q}")
    print(f"   R: {r}")
    print(f"   S: {s}")
    print()

    # 2. Build Complex Formulas
    print("2. BUILD COMPLEX FORMULAS:")
    print("-" * 40)

    p_and_q = reasoner.conj(p, q)
    p_or_r = reasoner.disj(p, r)
    p_implies_q = reasoner.implies(p, q)
    not_p = reasoner.neg(p)

    print(f"   P & Q: {p_and_q}")
    print(f"   P ∨ R: {p_or_r}")
    print(f"   P → Q: {p_implies_q}")
    print(f"   ¬P: {not_p}")
    print()

    # 3. Check Relevance
    print("3. CHECK RELEVANCE (VARIABLE SHARING):")
    print("-" * 40)

    # P and Q share no variables
    proof1 = reasoner.check_relevance(p, q)
    print(f"   P relevant to Q: {proof1.is_relevant}")
    print(f"   Shared variables: {proof1.shared_variables}")

    # P and (P & Q) share P
    proof2 = reasoner.check_relevance(p, p_and_q)
    print(f"   P relevant to (P & Q): {proof2.is_relevant}")
    print(f"   Shared variables: {proof2.shared_variables}")

    # (P & Q) and (Q & R) share Q
    q_and_r = reasoner.conj(q, r)
    proof3 = reasoner.check_relevance(p_and_q, q_and_r)
    print(f"   (P & Q) relevant to (Q & R): {proof3.is_relevant}")
    print(f"   Shared variables: {proof3.shared_variables}")
    print()

    # 4. Relevant Implication
    print("4. RELEVANT IMPLICATION:")
    print("-" * 40)

    # P → P is valid (same variable)
    p_implies_p = reasoner.implies(p, p)
    print(f"   P → P valid: {reasoner.valid_implication(p, p)}")

    # P → Q valid only if they share variables
    print(f"   P → Q valid: {reasoner.valid_implication(p, q)}")

    # (P & Q) → Q valid (shared Q)
    print(f"   (P & Q) → Q valid: {reasoner.valid_implication(p_and_q, q)}")
    print()

    # 5. Material Implication Paradoxes BLOCKED
    print("5. MATERIAL IMPLICATION PARADOXES BLOCKED:")
    print("-" * 40)

    print("   Classical logic paradoxes:")
    print("     - Q ⊢ P → Q (true conclusion makes any implication true)")
    print("     - ¬P ⊢ P → Q (false antecedent makes any implication true)")
    print()

    # Check if relevance logic blocks these
    blocked = reasoner.blocks_material_implication_paradoxes(p, s)
    print(f"   P and S share variables: {reasoner.is_relevant(p, s)}")
    print(f"   Paradox blocked: {blocked}")
    print()

    # 6. Explosion (Ex Contradictione Quodlibet) BLOCKED
    print("6. EXPLOSION BLOCKED:")
    print("-" * 40)

    print("   Classical: P, ¬P ⊢ Q (from contradiction, anything follows)")

    blocked_explosion = reasoner.blocks_explosion(p, not_p, s)
    print(f"   In relevance logic:")
    print(f"     P relevant to S: {reasoner.is_relevant(p, s)}")
    print(f"     Explosion blocked: {blocked_explosion}")
    print()

    # 7. Validate Deduction
    print("7. VALIDATE DEDUCTION:")
    print("-" * 40)

    # Valid: P, P → Q ⊢ Q
    p_implies_q_formula = reasoner.implies(p, q)
    deduction1 = reasoner.validate_deduction([p, p_implies_q_formula], q)
    print(f"   P, P→Q ⊢ Q: {deduction1.status.value}")

    # With unrelated premise
    deduction2 = reasoner.validate_deduction([p, p_implies_q_formula, s], q)
    print(f"   P, P→Q, S ⊢ Q: {deduction2.status.value}")
    print(f"   Used premises: {deduction2.used_premises} (S not used)")
    print()

    # 8. Modus Ponens
    print("8. RELEVANT MODUS PONENS:")
    print("-" * 40)

    # P, P → Q ⊢ Q
    mp_result = reasoner.modus_ponens(p, reasoner.implies(p, q))
    if mp_result:
        print(f"   From P and P → Q:")
        print(f"   Conclusion: {mp_result.conclusion}")
        print(f"   Status: {mp_result.status.value}")
    print()

    # 9. Logic System Axioms
    print("9. ANDERSON-BELNAP R AXIOMS:")
    print("-" * 40)

    axioms = reasoner.axiom_schemes()[:6]  # First 6
    for i, axiom in enumerate(axioms, 1):
        print(f"   {i}. {axiom}")
    print(f"   ... ({len(reasoner.axiom_schemes())} total axioms)")
    print()

    # 10. Inference Rules
    print("10. INFERENCE RULES:")
    print("-" * 40)

    for rule in reasoner.inference_rules():
        print(f"   • {rule}")
    print()

    # 11. Information Containment
    print("11. INFORMATION CONTAINMENT:")
    print("-" * 40)

    p_and_q_and_r = reasoner.conj(p_and_q, r)

    print(f"   (P & Q & R) contains info of P: {reasoner.contains_info(p_and_q_and_r, p)}")
    print(f"   P contains info of (P & Q): {reasoner.contains_info(p, p_and_q)}")
    print(f"   Info overlap (P & Q), (Q & R): {reasoner.info_overlap(p_and_q, q_and_r):.2f}")

    minimal = reasoner.minimal_info([p_and_q, q_and_r])
    print(f"   Minimal info of [(P & Q), (Q & R)]: {minimal}")
    print()

    # 12. Content Overlap
    print("12. CONTENT OVERLAP:")
    print("-" * 40)

    overlap1 = reasoner.content_overlap(p_and_q, q_and_r)
    overlap2 = reasoner.content_overlap(p, s)
    overlap3 = reasoner.content_overlap(p_and_q, p_and_q)

    print(f"   (P & Q) vs (Q & R): {overlap1:.2f}")
    print(f"   P vs S: {overlap2:.2f}")
    print(f"   (P & Q) vs (P & Q): {overlap3:.2f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Relevance Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
