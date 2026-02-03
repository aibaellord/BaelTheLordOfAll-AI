#!/usr/bin/env python3
"""
BAEL - Paraconsistent Reasoner
Advanced reasoning with inconsistent information.

Features:
- Four-valued logic (true, false, both, neither)
- Three-valued logic (Kleene, Łukasiewicz)
- Belnap's logic
- Contradiction handling
- Relevance preservation
- Belief base splitting
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

class TruthValue(Enum):
    """Four-valued truth values (Belnap)."""
    TRUE = "true"  # t (only true)
    FALSE = "false"  # f (only false)
    BOTH = "both"  # ⊤ (both true and false - contradiction)
    NEITHER = "neither"  # ⊥ (neither true nor false - unknown)


class ThreeValuedLogic(Enum):
    """Three-valued logic systems."""
    KLEENE_STRONG = "kleene_strong"
    KLEENE_WEAK = "kleene_weak"
    LUKASIEWICZ = "lukasiewicz"
    BOCHVAR = "bochvar"


class InferenceMode(Enum):
    """Inference modes."""
    CLASSICAL = "classical"
    PARACONSISTENT = "paraconsistent"
    EXPLOSIVE = "explosive"  # Ex contradictione quodlibet
    RELEVANT = "relevant"


class ContradictionStrategy(Enum):
    """How to handle contradictions."""
    IGNORE = "ignore"  # Ignore the contradiction
    QUARANTINE = "quarantine"  # Isolate contradictory beliefs
    RESOLVE = "resolve"  # Try to resolve
    TOLERATE = "tolerate"  # Tolerate (paraconsistent)


class ConsistencyLevel(Enum):
    """Levels of consistency."""
    CONSISTENT = "consistent"  # No contradictions
    LOCALLY_INCONSISTENT = "locally_inconsistent"  # Some local contradictions
    GLOBALLY_INCONSISTENT = "globally_inconsistent"  # Widespread


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Proposition:
    """A proposition with a truth value."""
    prop_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    value: TruthValue = TruthValue.NEITHER
    confidence: float = 1.0
    source: str = ""

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, Proposition):
            return False
        return self.name == other.name


@dataclass
class Belief:
    """A belief in the belief base."""
    belief_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    value: TruthValue = TruthValue.NEITHER
    strength: float = 1.0
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Contradiction:
    """A contradiction between beliefs."""
    contra_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    belief1: str = ""  # Belief ID
    belief2: str = ""  # Belief ID
    type: str = "direct"  # direct, indirect
    resolved: bool = False
    resolution: str = ""


@dataclass
class ConsistencyReport:
    """Report on consistency status."""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level: ConsistencyLevel = ConsistencyLevel.CONSISTENT
    contradictions: List[str] = field(default_factory=list)
    affected_beliefs: Set[str] = field(default_factory=set)
    consistent_subsets: List[Set[str]] = field(default_factory=list)


@dataclass
class InferenceResult:
    """Result of paraconsistent inference."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conclusion: str = ""
    value: TruthValue = TruthValue.NEITHER
    premises: List[str] = field(default_factory=list)
    mode: InferenceMode = InferenceMode.PARACONSISTENT


# =============================================================================
# FOUR-VALUED LOGIC
# =============================================================================

class FourValuedLogic:
    """Four-valued logic operations (Belnap)."""

    @staticmethod
    def negation(v: TruthValue) -> TruthValue:
        """Logical negation in 4-valued logic."""
        if v == TruthValue.TRUE:
            return TruthValue.FALSE
        elif v == TruthValue.FALSE:
            return TruthValue.TRUE
        elif v == TruthValue.BOTH:
            return TruthValue.BOTH  # ~⊤ = ⊤
        else:
            return TruthValue.NEITHER  # ~⊥ = ⊥

    @staticmethod
    def conjunction(v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Logical AND in 4-valued logic."""
        # Order: FALSE < NEITHER < TRUE, BOTH
        # Take meet in truth ordering
        if v1 == TruthValue.FALSE or v2 == TruthValue.FALSE:
            return TruthValue.FALSE
        if v1 == TruthValue.NEITHER or v2 == TruthValue.NEITHER:
            if v1 == TruthValue.BOTH or v2 == TruthValue.BOTH:
                return TruthValue.NEITHER
            return TruthValue.NEITHER
        if v1 == TruthValue.TRUE and v2 == TruthValue.TRUE:
            return TruthValue.TRUE
        if v1 == TruthValue.BOTH or v2 == TruthValue.BOTH:
            if v1 == TruthValue.TRUE or v2 == TruthValue.TRUE:
                return TruthValue.BOTH
            return TruthValue.BOTH
        return TruthValue.NEITHER

    @staticmethod
    def disjunction(v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Logical OR in 4-valued logic."""
        if v1 == TruthValue.TRUE or v2 == TruthValue.TRUE:
            return TruthValue.TRUE
        if v1 == TruthValue.BOTH or v2 == TruthValue.BOTH:
            if v1 == TruthValue.FALSE or v2 == TruthValue.FALSE:
                return TruthValue.BOTH
            return TruthValue.BOTH
        if v1 == TruthValue.NEITHER or v2 == TruthValue.NEITHER:
            return TruthValue.NEITHER
        return TruthValue.FALSE

    @staticmethod
    def implication(v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Material implication: A → B ≡ ¬A ∨ B."""
        neg_v1 = FourValuedLogic.negation(v1)
        return FourValuedLogic.disjunction(neg_v1, v2)

    @staticmethod
    def is_designated(v: TruthValue) -> bool:
        """Check if value is designated (true enough)."""
        return v in [TruthValue.TRUE, TruthValue.BOTH]

    @staticmethod
    def consensus(v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Consensus operation (meet in information ordering)."""
        # ⊥ < t, f < ⊤
        if v1 == v2:
            return v1
        if v1 == TruthValue.NEITHER:
            return TruthValue.NEITHER
        if v2 == TruthValue.NEITHER:
            return TruthValue.NEITHER
        if v1 == TruthValue.BOTH:
            return v2
        if v2 == TruthValue.BOTH:
            return v1
        # t, f -> ⊥ (no consensus)
        return TruthValue.NEITHER

    @staticmethod
    def gullibility(v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Gullibility operation (join in information ordering)."""
        if v1 == v2:
            return v1
        if v1 == TruthValue.BOTH:
            return TruthValue.BOTH
        if v2 == TruthValue.BOTH:
            return TruthValue.BOTH
        if v1 == TruthValue.NEITHER:
            return v2
        if v2 == TruthValue.NEITHER:
            return v1
        # t, f -> ⊤ (believe both)
        return TruthValue.BOTH


# =============================================================================
# THREE-VALUED LOGIC
# =============================================================================

class ThreeValueLogic:
    """Three-valued logic operations."""

    # Third value interpretation
    UNKNOWN = 0.5  # Middle value

    @staticmethod
    def to_numeric(v: TruthValue) -> float:
        """Convert to numeric value."""
        if v == TruthValue.TRUE:
            return 1.0
        elif v == TruthValue.FALSE:
            return 0.0
        else:
            return 0.5

    @staticmethod
    def from_numeric(n: float) -> TruthValue:
        """Convert from numeric value."""
        if n >= 0.75:
            return TruthValue.TRUE
        elif n <= 0.25:
            return TruthValue.FALSE
        else:
            return TruthValue.NEITHER

    @staticmethod
    def kleene_negation(v: float) -> float:
        """Kleene negation: 1 - v."""
        return 1.0 - v

    @staticmethod
    def kleene_conjunction(v1: float, v2: float) -> float:
        """Kleene strong conjunction: min(v1, v2)."""
        return min(v1, v2)

    @staticmethod
    def kleene_disjunction(v1: float, v2: float) -> float:
        """Kleene strong disjunction: max(v1, v2)."""
        return max(v1, v2)

    @staticmethod
    def lukasiewicz_implication(v1: float, v2: float) -> float:
        """Łukasiewicz implication: min(1, 1 - v1 + v2)."""
        return min(1.0, 1.0 - v1 + v2)

    @staticmethod
    def lukasiewicz_conjunction(v1: float, v2: float) -> float:
        """Łukasiewicz conjunction: max(0, v1 + v2 - 1)."""
        return max(0.0, v1 + v2 - 1.0)

    @staticmethod
    def lukasiewicz_disjunction(v1: float, v2: float) -> float:
        """Łukasiewicz disjunction: min(1, v1 + v2)."""
        return min(1.0, v1 + v2)


# =============================================================================
# BELIEF BASE
# =============================================================================

class BeliefBase:
    """A paraconsistent belief base."""

    def __init__(self):
        self._beliefs: Dict[str, Belief] = {}
        self._by_content: Dict[str, List[str]] = defaultdict(list)

    def add(
        self,
        content: str,
        value: TruthValue,
        strength: float = 1.0,
        source: str = ""
    ) -> Belief:
        """Add a belief."""
        belief = Belief(
            content=content,
            value=value,
            strength=strength,
            source=source
        )
        self._beliefs[belief.belief_id] = belief
        self._by_content[content].append(belief.belief_id)
        return belief

    def get(self, belief_id: str) -> Optional[Belief]:
        """Get a belief by ID."""
        return self._beliefs.get(belief_id)

    def remove(self, belief_id: str) -> bool:
        """Remove a belief."""
        if belief_id in self._beliefs:
            belief = self._beliefs[belief_id]
            self._by_content[belief.content].remove(belief_id)
            del self._beliefs[belief_id]
            return True
        return False

    def beliefs_about(self, content: str) -> List[Belief]:
        """Get all beliefs about a content."""
        ids = self._by_content.get(content, [])
        return [self._beliefs[bid] for bid in ids if bid in self._beliefs]

    def all_beliefs(self) -> List[Belief]:
        """Get all beliefs."""
        return list(self._beliefs.values())

    def aggregate_value(self, content: str) -> TruthValue:
        """Aggregate all beliefs about content."""
        beliefs = self.beliefs_about(content)
        if not beliefs:
            return TruthValue.NEITHER

        # Use gullibility (accept all evidence)
        result = TruthValue.NEITHER
        for belief in beliefs:
            result = FourValuedLogic.gullibility(result, belief.value)

        return result


# =============================================================================
# CONTRADICTION DETECTOR
# =============================================================================

class ContradictionDetector:
    """Detect contradictions in belief base."""

    def __init__(self, belief_base: BeliefBase):
        self._beliefs = belief_base
        self._contradictions: List[Contradiction] = []

    def detect_direct(self) -> List[Contradiction]:
        """Detect direct contradictions (P and ¬P)."""
        contradictions = []
        contents = defaultdict(list)

        for belief in self._beliefs.all_beliefs():
            content = belief.content
            if content.startswith("¬") or content.startswith("~"):
                pos_content = content[1:]
            else:
                pos_content = content
            contents[pos_content].append(belief)

        for pos_content, beliefs in contents.items():
            pos_beliefs = [b for b in beliefs if not (b.content.startswith("¬") or b.content.startswith("~"))]
            neg_beliefs = [b for b in beliefs if b.content.startswith("¬") or b.content.startswith("~")]

            for pb in pos_beliefs:
                for nb in neg_beliefs:
                    if pb.value in [TruthValue.TRUE, TruthValue.BOTH] and \
                       nb.value in [TruthValue.TRUE, TruthValue.BOTH]:
                        contra = Contradiction(
                            belief1=pb.belief_id,
                            belief2=nb.belief_id,
                            type="direct"
                        )
                        contradictions.append(contra)

        return contradictions

    def detect_by_content(self) -> List[Contradiction]:
        """Detect contradictions for same content with different values."""
        contradictions = []

        for content in set(b.content for b in self._beliefs.all_beliefs()):
            beliefs = self._beliefs.beliefs_about(content)

            for i, b1 in enumerate(beliefs):
                for b2 in beliefs[i+1:]:
                    if b1.value != b2.value:
                        # Check if they are truly contradictory
                        if (b1.value == TruthValue.TRUE and b2.value == TruthValue.FALSE) or \
                           (b1.value == TruthValue.FALSE and b2.value == TruthValue.TRUE):
                            contra = Contradiction(
                                belief1=b1.belief_id,
                                belief2=b2.belief_id,
                                type="value_conflict"
                            )
                            contradictions.append(contra)

        return contradictions

    def check_consistency(self) -> ConsistencyReport:
        """Check overall consistency."""
        direct = self.detect_direct()
        value_conflicts = self.detect_by_content()

        all_contras = direct + value_conflicts

        if not all_contras:
            return ConsistencyReport(level=ConsistencyLevel.CONSISTENT)

        affected = set()
        for c in all_contras:
            affected.add(c.belief1)
            affected.add(c.belief2)

        total = len(self._beliefs.all_beliefs())
        ratio = len(affected) / total if total > 0 else 0

        level = ConsistencyLevel.LOCALLY_INCONSISTENT if ratio < 0.5 else ConsistencyLevel.GLOBALLY_INCONSISTENT

        return ConsistencyReport(
            level=level,
            contradictions=[c.contra_id for c in all_contras],
            affected_beliefs=affected
        )


# =============================================================================
# PARACONSISTENT INFERENCE ENGINE
# =============================================================================

class ParaconsistentInferenceEngine:
    """Inference engine for paraconsistent reasoning."""

    def __init__(self, belief_base: BeliefBase):
        self._beliefs = belief_base

    def infer_conjunction(
        self,
        p1: str,
        p2: str
    ) -> InferenceResult:
        """Infer conjunction of two propositions."""
        v1 = self._beliefs.aggregate_value(p1)
        v2 = self._beliefs.aggregate_value(p2)

        result_value = FourValuedLogic.conjunction(v1, v2)

        return InferenceResult(
            conclusion=f"({p1} ∧ {p2})",
            value=result_value,
            premises=[p1, p2],
            mode=InferenceMode.PARACONSISTENT
        )

    def infer_disjunction(
        self,
        p1: str,
        p2: str
    ) -> InferenceResult:
        """Infer disjunction of two propositions."""
        v1 = self._beliefs.aggregate_value(p1)
        v2 = self._beliefs.aggregate_value(p2)

        result_value = FourValuedLogic.disjunction(v1, v2)

        return InferenceResult(
            conclusion=f"({p1} ∨ {p2})",
            value=result_value,
            premises=[p1, p2],
            mode=InferenceMode.PARACONSISTENT
        )

    def infer_implication(
        self,
        p1: str,
        p2: str
    ) -> InferenceResult:
        """Infer implication."""
        v1 = self._beliefs.aggregate_value(p1)
        v2 = self._beliefs.aggregate_value(p2)

        result_value = FourValuedLogic.implication(v1, v2)

        return InferenceResult(
            conclusion=f"({p1} → {p2})",
            value=result_value,
            premises=[p1, p2],
            mode=InferenceMode.PARACONSISTENT
        )

    def infer_negation(self, p: str) -> InferenceResult:
        """Infer negation."""
        v = self._beliefs.aggregate_value(p)
        result_value = FourValuedLogic.negation(v)

        return InferenceResult(
            conclusion=f"¬{p}",
            value=result_value,
            premises=[p],
            mode=InferenceMode.PARACONSISTENT
        )

    def modus_ponens(
        self,
        antecedent: str,
        consequent: str
    ) -> InferenceResult:
        """Paraconsistent modus ponens."""
        v_ant = self._beliefs.aggregate_value(antecedent)
        v_impl = self._beliefs.aggregate_value(f"({antecedent} → {consequent})")

        if v_impl == TruthValue.NEITHER:
            # No implication known
            v_impl = FourValuedLogic.implication(v_ant,
                self._beliefs.aggregate_value(consequent))

        # In paraconsistent logic, modus ponens is restricted
        if FourValuedLogic.is_designated(v_ant) and FourValuedLogic.is_designated(v_impl):
            result_value = self._beliefs.aggregate_value(consequent)
            if result_value == TruthValue.NEITHER:
                result_value = TruthValue.TRUE if v_ant == TruthValue.TRUE else TruthValue.BOTH
        else:
            result_value = TruthValue.NEITHER

        return InferenceResult(
            conclusion=consequent,
            value=result_value,
            premises=[antecedent, f"({antecedent} → {consequent})"],
            mode=InferenceMode.PARACONSISTENT
        )


# =============================================================================
# BELIEF REVISION
# =============================================================================

class ParaconsistentBeliefRevision:
    """Belief revision for paraconsistent bases."""

    def __init__(self, belief_base: BeliefBase):
        self._beliefs = belief_base
        self._detector = ContradictionDetector(belief_base)

    def expand(
        self,
        content: str,
        value: TruthValue
    ) -> Belief:
        """Expand belief base (may introduce contradiction)."""
        return self._beliefs.add(content, value)

    def revise(
        self,
        content: str,
        value: TruthValue,
        strategy: ContradictionStrategy = ContradictionStrategy.TOLERATE
    ) -> Tuple[Belief, List[Contradiction]]:
        """Revise belief base with new belief."""
        if strategy == ContradictionStrategy.TOLERATE:
            # Just add, tolerate contradictions
            belief = self._beliefs.add(content, value)
            return belief, []

        elif strategy == ContradictionStrategy.QUARANTINE:
            # Add but mark contradicting beliefs
            existing = self._beliefs.beliefs_about(content)
            conflicting = [b for b in existing
                          if b.value != value and b.value != TruthValue.NEITHER]

            belief = self._beliefs.add(content, value)

            contras = []
            for conf in conflicting:
                contra = Contradiction(
                    belief1=belief.belief_id,
                    belief2=conf.belief_id,
                    type="revision_conflict"
                )
                contras.append(contra)

            return belief, contras

        elif strategy == ContradictionStrategy.RESOLVE:
            # Remove conflicting beliefs
            existing = self._beliefs.beliefs_about(content)
            for b in existing:
                if b.value != value:
                    self._beliefs.remove(b.belief_id)

            belief = self._beliefs.add(content, value)
            return belief, []

        else:  # IGNORE
            belief = self._beliefs.add(content, value)
            return belief, []

    def contract(self, content: str) -> List[Belief]:
        """Contract belief base by removing all beliefs about content."""
        removed = []
        beliefs = self._beliefs.beliefs_about(content).copy()

        for b in beliefs:
            self._beliefs.remove(b.belief_id)
            removed.append(b)

        return removed


# =============================================================================
# PARACONSISTENT REASONER
# =============================================================================

class ParaconsistentReasoner:
    """
    Paraconsistent Reasoner for BAEL.

    Advanced reasoning with inconsistent information using
    four-valued logic (Belnap's FOUR).
    """

    def __init__(self):
        self._beliefs = BeliefBase()
        self._detector = ContradictionDetector(self._beliefs)
        self._inference = ParaconsistentInferenceEngine(self._beliefs)
        self._revision = ParaconsistentBeliefRevision(self._beliefs)

    # -------------------------------------------------------------------------
    # BELIEF MANAGEMENT
    # -------------------------------------------------------------------------

    def believe(
        self,
        content: str,
        value: TruthValue = TruthValue.TRUE,
        strength: float = 1.0,
        source: str = ""
    ) -> Belief:
        """Add a belief."""
        return self._beliefs.add(content, value, strength, source)

    def disbelieve(
        self,
        content: str,
        strength: float = 1.0,
        source: str = ""
    ) -> Belief:
        """Add a disbelief (FALSE)."""
        return self._beliefs.add(content, TruthValue.FALSE, strength, source)

    def suspend(
        self,
        content: str,
        strength: float = 1.0,
        source: str = ""
    ) -> Belief:
        """Suspend belief (NEITHER)."""
        return self._beliefs.add(content, TruthValue.NEITHER, strength, source)

    def conflicted(
        self,
        content: str,
        strength: float = 1.0,
        source: str = ""
    ) -> Belief:
        """Mark as conflicted (BOTH)."""
        return self._beliefs.add(content, TruthValue.BOTH, strength, source)

    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """Get a belief by ID."""
        return self._beliefs.get(belief_id)

    def remove_belief(self, belief_id: str) -> bool:
        """Remove a belief."""
        return self._beliefs.remove(belief_id)

    def all_beliefs(self) -> List[Belief]:
        """Get all beliefs."""
        return self._beliefs.all_beliefs()

    def get_value(self, content: str) -> TruthValue:
        """Get aggregated truth value for content."""
        return self._beliefs.aggregate_value(content)

    def is_believed(self, content: str) -> bool:
        """Check if content is believed (designated)."""
        v = self.get_value(content)
        return FourValuedLogic.is_designated(v)

    # -------------------------------------------------------------------------
    # FOUR-VALUED LOGIC
    # -------------------------------------------------------------------------

    def negate(self, v: TruthValue) -> TruthValue:
        """Negate a truth value."""
        return FourValuedLogic.negation(v)

    def conjoin(self, v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Conjoin two truth values."""
        return FourValuedLogic.conjunction(v1, v2)

    def disjoin(self, v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Disjoin two truth values."""
        return FourValuedLogic.disjunction(v1, v2)

    def imply(self, v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Material implication."""
        return FourValuedLogic.implication(v1, v2)

    def consensus(self, v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Consensus of two values."""
        return FourValuedLogic.consensus(v1, v2)

    def gullibility(self, v1: TruthValue, v2: TruthValue) -> TruthValue:
        """Gullibility (accept all evidence)."""
        return FourValuedLogic.gullibility(v1, v2)

    # -------------------------------------------------------------------------
    # INFERENCE
    # -------------------------------------------------------------------------

    def infer_and(self, p1: str, p2: str) -> InferenceResult:
        """Infer conjunction."""
        return self._inference.infer_conjunction(p1, p2)

    def infer_or(self, p1: str, p2: str) -> InferenceResult:
        """Infer disjunction."""
        return self._inference.infer_disjunction(p1, p2)

    def infer_implies(self, p1: str, p2: str) -> InferenceResult:
        """Infer implication."""
        return self._inference.infer_implication(p1, p2)

    def infer_not(self, p: str) -> InferenceResult:
        """Infer negation."""
        return self._inference.infer_negation(p)

    def modus_ponens(self, antecedent: str, consequent: str) -> InferenceResult:
        """Paraconsistent modus ponens."""
        return self._inference.modus_ponens(antecedent, consequent)

    # -------------------------------------------------------------------------
    # CONTRADICTION HANDLING
    # -------------------------------------------------------------------------

    def detect_contradictions(self) -> List[Contradiction]:
        """Detect all contradictions."""
        direct = self._detector.detect_direct()
        value_conflicts = self._detector.detect_by_content()
        return direct + value_conflicts

    def check_consistency(self) -> ConsistencyReport:
        """Check overall consistency."""
        return self._detector.check_consistency()

    def is_consistent(self) -> bool:
        """Check if belief base is consistent."""
        report = self.check_consistency()
        return report.level == ConsistencyLevel.CONSISTENT

    # -------------------------------------------------------------------------
    # BELIEF REVISION
    # -------------------------------------------------------------------------

    def expand(self, content: str, value: TruthValue) -> Belief:
        """Expand belief base."""
        return self._revision.expand(content, value)

    def revise(
        self,
        content: str,
        value: TruthValue,
        strategy: ContradictionStrategy = ContradictionStrategy.TOLERATE
    ) -> Tuple[Belief, List[Contradiction]]:
        """Revise belief base."""
        return self._revision.revise(content, value, strategy)

    def contract(self, content: str) -> List[Belief]:
        """Contract belief base."""
        return self._revision.contract(content)

    # -------------------------------------------------------------------------
    # THREE-VALUED LOGIC
    # -------------------------------------------------------------------------

    def three_valued_and(
        self,
        v1: float,
        v2: float,
        logic: ThreeValuedLogic = ThreeValuedLogic.KLEENE_STRONG
    ) -> float:
        """Three-valued conjunction."""
        if logic in [ThreeValuedLogic.KLEENE_STRONG, ThreeValuedLogic.KLEENE_WEAK]:
            return ThreeValueLogic.kleene_conjunction(v1, v2)
        else:
            return ThreeValueLogic.lukasiewicz_conjunction(v1, v2)

    def three_valued_or(
        self,
        v1: float,
        v2: float,
        logic: ThreeValuedLogic = ThreeValuedLogic.KLEENE_STRONG
    ) -> float:
        """Three-valued disjunction."""
        if logic in [ThreeValuedLogic.KLEENE_STRONG, ThreeValuedLogic.KLEENE_WEAK]:
            return ThreeValueLogic.kleene_disjunction(v1, v2)
        else:
            return ThreeValueLogic.lukasiewicz_disjunction(v1, v2)

    def three_valued_implies(
        self,
        v1: float,
        v2: float,
        logic: ThreeValuedLogic = ThreeValuedLogic.LUKASIEWICZ
    ) -> float:
        """Three-valued implication."""
        return ThreeValueLogic.lukasiewicz_implication(v1, v2)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Paraconsistent Reasoner."""
    print("=" * 70)
    print("BAEL - PARACONSISTENT REASONER DEMO")
    print("Advanced Reasoning with Inconsistent Information")
    print("=" * 70)
    print()

    reasoner = ParaconsistentReasoner()

    # 1. Four-Valued Logic
    print("1. FOUR-VALUED LOGIC (BELNAP):")
    print("-" * 40)

    print("   Truth Values:")
    print(f"      TRUE (t): only true")
    print(f"      FALSE (f): only false")
    print(f"      BOTH (⊤): both true and false (contradiction)")
    print(f"      NEITHER (⊥): neither true nor false (unknown)")
    print()

    print("   Negation:")
    for v in TruthValue:
        neg = reasoner.negate(v)
        print(f"      ¬{v.value} = {neg.value}")
    print()

    # 2. Add Beliefs
    print("2. ADD BELIEFS:")
    print("-" * 40)

    reasoner.believe("rain", TruthValue.TRUE, source="weather_report")
    reasoner.believe("umbrella", TruthValue.TRUE, source="observation")
    reasoner.believe("sunny", TruthValue.FALSE, source="weather_report")

    print(f"   rain: TRUE (weather report)")
    print(f"   umbrella: TRUE (observation)")
    print(f"   sunny: FALSE (weather report)")
    print()

    # 3. Introduce Contradiction
    print("3. INTRODUCE CONTRADICTION:")
    print("-" * 40)

    reasoner.believe("rain", TruthValue.FALSE, source="sensor")

    print(f"   rain: FALSE (sensor)")
    print(f"   Now 'rain' has contradictory evidence!")
    print()

    # 4. Aggregated Values
    print("4. AGGREGATED VALUES:")
    print("-" * 40)

    rain_value = reasoner.get_value("rain")
    umbrella_value = reasoner.get_value("umbrella")
    sunny_value = reasoner.get_value("sunny")
    unknown_value = reasoner.get_value("unknown_prop")

    print(f"   rain: {rain_value.value} (conflicting evidence → BOTH)")
    print(f"   umbrella: {umbrella_value.value}")
    print(f"   sunny: {sunny_value.value}")
    print(f"   unknown_prop: {unknown_value.value} (no evidence → NEITHER)")
    print()

    # 5. Check Consistency
    print("5. CHECK CONSISTENCY:")
    print("-" * 40)

    report = reasoner.check_consistency()
    print(f"   Level: {report.level.value}")
    print(f"   Affected beliefs: {len(report.affected_beliefs)}")
    print()

    # 6. Paraconsistent Inference
    print("6. PARACONSISTENT INFERENCE:")
    print("-" * 40)

    # Conjunction
    result_and = reasoner.infer_and("rain", "umbrella")
    print(f"   rain ∧ umbrella: {result_and.value.value}")

    # Disjunction
    result_or = reasoner.infer_or("rain", "sunny")
    print(f"   rain ∨ sunny: {result_or.value.value}")

    # Negation
    result_not = reasoner.infer_not("sunny")
    print(f"   ¬sunny: {result_not.value.value}")
    print()

    # 7. No Ex Contradictione Quodlibet
    print("7. NO EXPLOSION (EX CONTRADICTIONE QUODLIBET):")
    print("-" * 40)

    print(f"   In classical logic: P ∧ ¬P ⊨ Q (anything follows)")
    print(f"   In paraconsistent logic: contradictions are contained!")

    # rain is BOTH, but it doesn't make everything true
    moon_value = reasoner.get_value("moon_is_cheese")
    print(f"   rain is BOTH, but moon_is_cheese: {moon_value.value}")
    print(f"   Contradiction doesn't spread!")
    print()

    # 8. Belief Revision
    print("8. BELIEF REVISION:")
    print("-" * 40)

    reasoner2 = ParaconsistentReasoner()
    reasoner2.believe("cat", TruthValue.TRUE)

    # Revise with conflicting info
    belief, contras = reasoner2.revise(
        "cat",
        TruthValue.FALSE,
        ContradictionStrategy.QUARANTINE
    )

    print(f"   Added 'cat: TRUE', then revised with 'cat: FALSE'")
    print(f"   Strategy: QUARANTINE")
    print(f"   Contradictions detected: {len(contras)}")

    # With TOLERATE
    reasoner3 = ParaconsistentReasoner()
    reasoner3.believe("dog", TruthValue.TRUE)
    belief, contras = reasoner3.revise(
        "dog",
        TruthValue.FALSE,
        ContradictionStrategy.TOLERATE
    )

    cat_value = reasoner3.get_value("dog")
    print(f"   TOLERATE strategy: dog becomes {cat_value.value}")
    print()

    # 9. Three-Valued Logic
    print("9. THREE-VALUED LOGIC:")
    print("-" * 40)

    v1 = 0.5  # Unknown
    v2 = 1.0  # True

    kleene_and = reasoner.three_valued_and(v1, v2, ThreeValuedLogic.KLEENE_STRONG)
    lukasiewicz_and = reasoner.three_valued_and(v1, v2, ThreeValuedLogic.LUKASIEWICZ)

    print(f"   Unknown (0.5) ∧ True (1.0):")
    print(f"      Kleene: {kleene_and}")
    print(f"      Łukasiewicz: {lukasiewicz_and}")

    lukasiewicz_impl = reasoner.three_valued_implies(0.5, 0.7)
    print(f"   Unknown (0.5) → 0.7:")
    print(f"      Łukasiewicz: {lukasiewicz_impl}")
    print()

    # 10. Consensus vs Gullibility
    print("10. CONSENSUS VS GULLIBILITY:")
    print("-" * 40)

    print("   Consensus (skeptical - meet in info ordering):")
    c1 = reasoner.consensus(TruthValue.TRUE, TruthValue.FALSE)
    c2 = reasoner.consensus(TruthValue.TRUE, TruthValue.BOTH)
    print(f"      TRUE ⊓ FALSE = {c1.value}")
    print(f"      TRUE ⊓ BOTH = {c2.value}")

    print("   Gullibility (credulous - join in info ordering):")
    g1 = reasoner.gullibility(TruthValue.TRUE, TruthValue.FALSE)
    g2 = reasoner.gullibility(TruthValue.TRUE, TruthValue.NEITHER)
    print(f"      TRUE ⊔ FALSE = {g1.value}")
    print(f"      TRUE ⊔ NEITHER = {g2.value}")
    print()

    # 11. Is Believed Check
    print("11. DESIGNATED VALUES (IS BELIEVED):")
    print("-" * 40)

    for v in TruthValue:
        is_designated = FourValuedLogic.is_designated(v)
        print(f"   {v.value}: {'designated ✓' if is_designated else 'not designated ✗'}")
    print()

    # 12. All Beliefs
    print("12. ALL BELIEFS IN BASE:")
    print("-" * 40)

    for belief in reasoner.all_beliefs():
        print(f"   {belief.content}: {belief.value.value} (source: {belief.source or 'none'})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Paraconsistent Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
