#!/usr/bin/env python3
"""
BAEL - Belief Revision Engine
Advanced AGM belief revision and contraction.

Features:
- AGM belief revision operators
- Contraction (give up beliefs)
- Expansion (add beliefs)
- Revision (consistent addition)
- Epistemic entrenchment
- Recovery and relevance postulates
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

class OperationType(Enum):
    """Types of belief change operations."""
    EXPANSION = "expansion"  # K + φ
    CONTRACTION = "contraction"  # K ÷ φ
    REVISION = "revision"  # K * φ


class EntrenchmentLevel(Enum):
    """Epistemic entrenchment levels."""
    CORE = "core"  # Tautologies, highly entrenched
    ESTABLISHED = "established"  # Well-established beliefs
    TENTATIVE = "tentative"  # Tentative beliefs
    PERIPHERAL = "peripheral"  # Easily given up


class ContractionMethod(Enum):
    """Methods for contraction."""
    FULL_MEET = "full_meet"  # Intersection of all remainder sets
    PARTIAL_MEET = "partial_meet"  # Selected remainder sets
    MAXICHOICE = "maxichoice"  # Single maximal subset
    ENTRENCHMENT = "entrenchment"  # Based on epistemic entrenchment


class ConsistencyStatus(Enum):
    """Consistency status of belief set."""
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    UNKNOWN = "unknown"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Belief:
    """A belief with entrenchment."""
    belief_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    entrenchment: EntrenchmentLevel = EntrenchmentLevel.TENTATIVE
    entrenchment_value: float = 0.5  # 0 to 1
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __hash__(self):
        return hash(self.content)

    def __eq__(self, other):
        if not isinstance(other, Belief):
            return False
        return self.content == other.content

    def __str__(self):
        return self.content


@dataclass
class BeliefSet:
    """A belief set (closed under logical consequence)."""
    set_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    beliefs: Set[str] = field(default_factory=set)
    name: str = ""


@dataclass
class RevisionResult:
    """Result of a revision operation."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: OperationType = OperationType.REVISION
    input_belief: str = ""
    success: bool = True
    original_beliefs: Set[str] = field(default_factory=set)
    result_beliefs: Set[str] = field(default_factory=set)
    removed_beliefs: Set[str] = field(default_factory=set)
    added_beliefs: Set[str] = field(default_factory=set)


@dataclass
class EntrenchmentOrdering:
    """Ordering of beliefs by entrenchment."""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ordering: List[Set[str]] = field(default_factory=list)  # From least to most


# =============================================================================
# LOGICAL OPERATIONS
# =============================================================================

class LogicalOperations:
    """Simple logical operations for belief manipulation."""

    @staticmethod
    def negation(belief: str) -> str:
        """Negate a belief."""
        if belief.startswith("¬") or belief.startswith("~"):
            return belief[1:]
        return f"¬{belief}"

    @staticmethod
    def is_negation_of(b1: str, b2: str) -> bool:
        """Check if b1 is negation of b2."""
        return b1 == LogicalOperations.negation(b2)

    @staticmethod
    def is_tautology(belief: str) -> bool:
        """Check if belief is a tautology."""
        # Simplified check
        return belief in ["⊤", "true", "T"]

    @staticmethod
    def is_contradiction(belief: str) -> bool:
        """Check if belief is a contradiction."""
        return belief in ["⊥", "false", "F"]

    @staticmethod
    def implies(b1: str, b2: str) -> bool:
        """Check if b1 implies b2 (simplified)."""
        # In reality, this would use a theorem prover
        if b1 == b2:
            return True
        if LogicalOperations.is_tautology(b2):
            return True
        if LogicalOperations.is_contradiction(b1):
            return True
        return False


# =============================================================================
# BELIEF BASE
# =============================================================================

class BeliefBase:
    """A belief base with entrenchment."""

    def __init__(self):
        self._beliefs: Dict[str, Belief] = {}
        self._entrenchment: Dict[str, float] = {}

    def add(
        self,
        content: str,
        entrenchment: float = 0.5,
        source: str = ""
    ) -> Belief:
        """Add a belief."""
        level = self._entrenchment_level(entrenchment)
        belief = Belief(
            content=content,
            entrenchment=level,
            entrenchment_value=entrenchment,
            source=source
        )
        self._beliefs[content] = belief
        self._entrenchment[content] = entrenchment
        return belief

    def _entrenchment_level(self, value: float) -> EntrenchmentLevel:
        """Convert numeric entrenchment to level."""
        if value >= 0.9:
            return EntrenchmentLevel.CORE
        elif value >= 0.7:
            return EntrenchmentLevel.ESTABLISHED
        elif value >= 0.3:
            return EntrenchmentLevel.TENTATIVE
        else:
            return EntrenchmentLevel.PERIPHERAL

    def get(self, content: str) -> Optional[Belief]:
        """Get a belief."""
        return self._beliefs.get(content)

    def remove(self, content: str) -> bool:
        """Remove a belief."""
        if content in self._beliefs:
            del self._beliefs[content]
            del self._entrenchment[content]
            return True
        return False

    def contains(self, content: str) -> bool:
        """Check if belief is in base."""
        return content in self._beliefs

    def all_beliefs(self) -> Set[str]:
        """Get all belief contents."""
        return set(self._beliefs.keys())

    def get_entrenchment(self, content: str) -> float:
        """Get entrenchment value."""
        return self._entrenchment.get(content, 0.0)

    def is_consistent(self) -> bool:
        """Check if belief base is consistent."""
        for b in self._beliefs:
            neg = LogicalOperations.negation(b)
            if neg in self._beliefs:
                return False
        return True


# =============================================================================
# EXPANSION OPERATOR
# =============================================================================

class ExpansionOperator:
    """
    Expansion: K + φ

    Simply adds φ to K without checking consistency.
    """

    def __init__(self, base: BeliefBase):
        self._base = base

    def expand(
        self,
        belief: str,
        entrenchment: float = 0.5
    ) -> RevisionResult:
        """Expand belief base with new belief."""
        original = self._base.all_beliefs()

        # Simply add
        self._base.add(belief, entrenchment)

        return RevisionResult(
            operation=OperationType.EXPANSION,
            input_belief=belief,
            success=True,
            original_beliefs=original,
            result_beliefs=self._base.all_beliefs(),
            added_beliefs={belief}
        )


# =============================================================================
# CONTRACTION OPERATOR
# =============================================================================

class ContractionOperator:
    """
    Contraction: K ÷ φ

    Removes φ while maintaining consistency and closure.
    """

    def __init__(self, base: BeliefBase):
        self._base = base

    def contract(
        self,
        belief: str,
        method: ContractionMethod = ContractionMethod.ENTRENCHMENT
    ) -> RevisionResult:
        """Contract belief from base."""
        original = self._base.all_beliefs()

        if belief not in self._base.all_beliefs():
            # Nothing to contract
            return RevisionResult(
                operation=OperationType.CONTRACTION,
                input_belief=belief,
                success=True,
                original_beliefs=original,
                result_beliefs=original
            )

        removed: Set[str] = set()

        if method == ContractionMethod.ENTRENCHMENT:
            removed = self._entrenchment_contraction(belief)
        elif method == ContractionMethod.MAXICHOICE:
            removed = self._maxichoice_contraction(belief)
        else:
            # Full meet - just remove the belief
            removed = {belief}

        for b in removed:
            self._base.remove(b)

        return RevisionResult(
            operation=OperationType.CONTRACTION,
            input_belief=belief,
            success=True,
            original_beliefs=original,
            result_beliefs=self._base.all_beliefs(),
            removed_beliefs=removed
        )

    def _entrenchment_contraction(self, belief: str) -> Set[str]:
        """Contract based on epistemic entrenchment."""
        # Remove belief and any less entrenched beliefs that depend on it
        to_remove = {belief}
        threshold = self._base.get_entrenchment(belief)

        # Remove beliefs with lower or equal entrenchment that might depend
        for b in self._base.all_beliefs():
            if self._base.get_entrenchment(b) <= threshold:
                # Check if b "depends" on belief (simplified)
                if b.startswith(belief) or belief in b:
                    to_remove.add(b)

        return to_remove

    def _maxichoice_contraction(self, belief: str) -> Set[str]:
        """Maxichoice contraction - remove only the belief."""
        return {belief}


# =============================================================================
# REVISION OPERATOR
# =============================================================================

class RevisionOperator:
    """
    Revision: K * φ

    Adds φ consistently. Uses Levi identity:
    K * φ = (K ÷ ¬φ) + φ
    """

    def __init__(self, base: BeliefBase):
        self._base = base
        self._expansion = ExpansionOperator(base)
        self._contraction = ContractionOperator(base)

    def revise(
        self,
        belief: str,
        entrenchment: float = 0.5
    ) -> RevisionResult:
        """Revise belief base with new belief."""
        original = self._base.all_beliefs()

        # Check if already consistent
        negation = LogicalOperations.negation(belief)

        if negation in self._base.all_beliefs():
            # Levi identity: contract ¬φ, then expand with φ
            self._contraction.contract(negation)

        # Add the belief
        self._base.add(belief, entrenchment)

        return RevisionResult(
            operation=OperationType.REVISION,
            input_belief=belief,
            success=True,
            original_beliefs=original,
            result_beliefs=self._base.all_beliefs(),
            removed_beliefs=original - self._base.all_beliefs(),
            added_beliefs={belief}
        )


# =============================================================================
# AGM POSTULATES CHECKER
# =============================================================================

class AGMPostulatesChecker:
    """Check AGM postulates for revision operations."""

    def __init__(self):
        pass

    def check_success(
        self,
        result: RevisionResult,
        input_belief: str
    ) -> bool:
        """Check success postulate: φ ∈ K * φ."""
        if result.operation == OperationType.REVISION:
            return input_belief in result.result_beliefs
        return True

    def check_inclusion(
        self,
        result: RevisionResult
    ) -> bool:
        """Check inclusion postulate: K * φ ⊆ K + φ."""
        if result.operation == OperationType.REVISION:
            # K * φ should be subset of what K + φ would give
            expansion = result.original_beliefs | {result.input_belief}
            return result.result_beliefs.issubset(expansion)
        return True

    def check_vacuity(
        self,
        result: RevisionResult,
        original_contained_negation: bool
    ) -> bool:
        """Check vacuity: If ¬φ ∉ K, then K * φ = K + φ."""
        if result.operation == OperationType.REVISION:
            if not original_contained_negation:
                # Should be simple expansion
                expected = result.original_beliefs | {result.input_belief}
                return result.result_beliefs == expected
        return True

    def check_consistency(
        self,
        result: RevisionResult,
        input_is_consistent: bool
    ) -> bool:
        """Check consistency: If φ is consistent, K * φ is consistent."""
        if not input_is_consistent:
            return True

        # Check result for contradictions
        for b in result.result_beliefs:
            neg = LogicalOperations.negation(b)
            if neg in result.result_beliefs:
                return False
        return True

    def check_extensionality(
        self,
        result1: RevisionResult,
        result2: RevisionResult,
        beliefs_equivalent: bool
    ) -> bool:
        """Check extensionality: If φ ↔ ψ, then K * φ = K * ψ."""
        if beliefs_equivalent:
            return result1.result_beliefs == result2.result_beliefs
        return True

    def check_recovery(
        self,
        original: Set[str],
        contracted: Set[str],
        expanded: Set[str]
    ) -> bool:
        """Check recovery: K ⊆ (K ÷ φ) + φ."""
        return original.issubset(expanded)


# =============================================================================
# ENTRENCHMENT MANAGER
# =============================================================================

class EntrenchmentManager:
    """Manage epistemic entrenchment ordering."""

    def __init__(self, base: BeliefBase):
        self._base = base

    def compute_ordering(self) -> EntrenchmentOrdering:
        """Compute entrenchment ordering from belief base."""
        beliefs = [(b, self._base.get_entrenchment(b))
                   for b in self._base.all_beliefs()]

        # Sort by entrenchment
        beliefs.sort(key=lambda x: x[1])

        # Group by similar entrenchment
        ordering: List[Set[str]] = []
        current_set: Set[str] = set()
        current_value = -1.0

        for belief, value in beliefs:
            if abs(value - current_value) > 0.1:
                if current_set:
                    ordering.append(current_set)
                current_set = {belief}
                current_value = value
            else:
                current_set.add(belief)

        if current_set:
            ordering.append(current_set)

        return EntrenchmentOrdering(ordering=ordering)

    def compare(self, b1: str, b2: str) -> int:
        """Compare entrenchment: -1 if b1 < b2, 0 if equal, 1 if b1 > b2."""
        e1 = self._base.get_entrenchment(b1)
        e2 = self._base.get_entrenchment(b2)

        if abs(e1 - e2) < 0.01:
            return 0
        return -1 if e1 < e2 else 1

    def least_entrenched(self) -> Set[str]:
        """Get least entrenched beliefs."""
        if not self._base.all_beliefs():
            return set()

        min_ent = min(self._base.get_entrenchment(b)
                     for b in self._base.all_beliefs())

        return {b for b in self._base.all_beliefs()
                if abs(self._base.get_entrenchment(b) - min_ent) < 0.01}

    def most_entrenched(self) -> Set[str]:
        """Get most entrenched beliefs."""
        if not self._base.all_beliefs():
            return set()

        max_ent = max(self._base.get_entrenchment(b)
                     for b in self._base.all_beliefs())

        return {b for b in self._base.all_beliefs()
                if abs(self._base.get_entrenchment(b) - max_ent) < 0.01}


# =============================================================================
# BELIEF REVISION ENGINE
# =============================================================================

class BeliefRevisionEngine:
    """
    Belief Revision Engine for BAEL.

    Advanced AGM belief revision and contraction.
    """

    def __init__(self):
        self._base = BeliefBase()
        self._expansion = ExpansionOperator(self._base)
        self._contraction = ContractionOperator(self._base)
        self._revision = RevisionOperator(self._base)
        self._postulates = AGMPostulatesChecker()
        self._entrenchment = EntrenchmentManager(self._base)
        self._history: List[RevisionResult] = []

    # -------------------------------------------------------------------------
    # BELIEF MANAGEMENT
    # -------------------------------------------------------------------------

    def add(
        self,
        content: str,
        entrenchment: float = 0.5,
        source: str = ""
    ) -> Belief:
        """Add a belief directly."""
        return self._base.add(content, entrenchment, source)

    def get(self, content: str) -> Optional[Belief]:
        """Get a belief."""
        return self._base.get(content)

    def contains(self, content: str) -> bool:
        """Check if belief is in base."""
        return self._base.contains(content)

    def all_beliefs(self) -> Set[str]:
        """Get all beliefs."""
        return self._base.all_beliefs()

    def is_consistent(self) -> bool:
        """Check consistency."""
        return self._base.is_consistent()

    # -------------------------------------------------------------------------
    # EXPANSION
    # -------------------------------------------------------------------------

    def expand(
        self,
        belief: str,
        entrenchment: float = 0.5
    ) -> RevisionResult:
        """Expand with new belief (K + φ)."""
        result = self._expansion.expand(belief, entrenchment)
        self._history.append(result)
        return result

    # -------------------------------------------------------------------------
    # CONTRACTION
    # -------------------------------------------------------------------------

    def contract(
        self,
        belief: str,
        method: ContractionMethod = ContractionMethod.ENTRENCHMENT
    ) -> RevisionResult:
        """Contract belief (K ÷ φ)."""
        result = self._contraction.contract(belief, method)
        self._history.append(result)
        return result

    # -------------------------------------------------------------------------
    # REVISION
    # -------------------------------------------------------------------------

    def revise(
        self,
        belief: str,
        entrenchment: float = 0.5
    ) -> RevisionResult:
        """Revise with new belief (K * φ)."""
        result = self._revision.revise(belief, entrenchment)
        self._history.append(result)
        return result

    # -------------------------------------------------------------------------
    # ENTRENCHMENT
    # -------------------------------------------------------------------------

    def get_entrenchment(self, content: str) -> float:
        """Get entrenchment value."""
        return self._base.get_entrenchment(content)

    def set_entrenchment(self, content: str, value: float) -> None:
        """Set entrenchment value."""
        belief = self._base.get(content)
        if belief:
            belief.entrenchment_value = value
            belief.entrenchment = self._base._entrenchment_level(value)
            self._base._entrenchment[content] = value

    def entrenchment_ordering(self) -> EntrenchmentOrdering:
        """Get entrenchment ordering."""
        return self._entrenchment.compute_ordering()

    def least_entrenched(self) -> Set[str]:
        """Get least entrenched beliefs."""
        return self._entrenchment.least_entrenched()

    def most_entrenched(self) -> Set[str]:
        """Get most entrenched beliefs."""
        return self._entrenchment.most_entrenched()

    def compare_entrenchment(self, b1: str, b2: str) -> int:
        """Compare entrenchment of two beliefs."""
        return self._entrenchment.compare(b1, b2)

    # -------------------------------------------------------------------------
    # POSTULATES
    # -------------------------------------------------------------------------

    def check_postulates(self, result: RevisionResult) -> Dict[str, bool]:
        """Check AGM postulates for a revision result."""
        checks = {}

        checks["success"] = self._postulates.check_success(
            result, result.input_belief
        )

        checks["inclusion"] = self._postulates.check_inclusion(result)

        neg = LogicalOperations.negation(result.input_belief)
        checks["vacuity"] = self._postulates.check_vacuity(
            result, neg in result.original_beliefs
        )

        checks["consistency"] = self._postulates.check_consistency(
            result, not LogicalOperations.is_contradiction(result.input_belief)
        )

        return checks

    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------

    def history(self) -> List[RevisionResult]:
        """Get revision history."""
        return self._history.copy()

    def undo(self) -> Optional[RevisionResult]:
        """Undo last operation."""
        if not self._history:
            return None

        last = self._history.pop()

        # Restore state
        for b in last.added_beliefs:
            self._base.remove(b)

        for b in last.removed_beliefs:
            self._base.add(b)

        return last


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Belief Revision Engine."""
    print("=" * 70)
    print("BAEL - BELIEF REVISION ENGINE DEMO")
    print("Advanced AGM Belief Revision and Contraction")
    print("=" * 70)
    print()

    engine = BeliefRevisionEngine()

    # 1. Initial Beliefs
    print("1. INITIAL BELIEFS:")
    print("-" * 40)

    engine.add("bird", entrenchment=0.8)
    engine.add("flies", entrenchment=0.6)
    engine.add("has_wings", entrenchment=0.9)

    print(f"   Beliefs: {engine.all_beliefs()}")
    print(f"   Consistent: {engine.is_consistent()}")
    print()

    # 2. Expansion
    print("2. EXPANSION (K + φ):")
    print("-" * 40)

    result = engine.expand("sings", entrenchment=0.5)
    print(f"   Added: {result.input_belief}")
    print(f"   Result: {result.result_beliefs}")
    print()

    # 3. Contraction
    print("3. CONTRACTION (K ÷ φ):")
    print("-" * 40)

    result = engine.contract("flies")
    print(f"   Contracted: {result.input_belief}")
    print(f"   Removed: {result.removed_beliefs}")
    print(f"   Result: {result.result_beliefs}")
    print()

    # 4. Revision with Conflict
    print("4. REVISION WITH CONFLICT (K * φ):")
    print("-" * 40)

    # Add back flies, then revise with ¬flies
    engine.add("flies", entrenchment=0.6)
    print(f"   Before: {engine.all_beliefs()}")

    result = engine.revise("¬flies", entrenchment=0.7)
    print(f"   Revised with: {result.input_belief}")
    print(f"   Removed: {result.removed_beliefs}")
    print(f"   Result: {result.result_beliefs}")
    print(f"   Consistent: {engine.is_consistent()}")
    print()

    # 5. Entrenchment Ordering
    print("5. ENTRENCHMENT ORDERING:")
    print("-" * 40)

    for b in engine.all_beliefs():
        ent = engine.get_entrenchment(b)
        belief = engine.get(b)
        level = belief.entrenchment.value if belief else "unknown"
        print(f"   {b}: {ent:.2f} ({level})")

    ordering = engine.entrenchment_ordering()
    print(f"\n   Ordering (least to most entrenched):")
    for i, level in enumerate(ordering.ordering):
        print(f"     Level {i}: {level}")
    print()

    # 6. Least/Most Entrenched
    print("6. EXTREME ENTRENCHMENT:")
    print("-" * 40)

    print(f"   Least entrenched: {engine.least_entrenched()}")
    print(f"   Most entrenched: {engine.most_entrenched()}")
    print()

    # 7. Check AGM Postulates
    print("7. AGM POSTULATES CHECK:")
    print("-" * 40)

    # New revision to check
    engine2 = BeliefRevisionEngine()
    engine2.add("p", 0.5)
    engine2.add("q", 0.5)
    result = engine2.revise("r", 0.5)

    checks = engine2.check_postulates(result)
    for postulate, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"   {postulate}: {status}")
    print()

    # 8. Levi Identity
    print("8. LEVI IDENTITY (K * φ = (K ÷ ¬φ) + φ):")
    print("-" * 40)

    engine3 = BeliefRevisionEngine()
    engine3.add("p", 0.5)
    engine3.add("¬q", 0.6)

    print(f"   Initial: {engine3.all_beliefs()}")

    # Revise with q (should remove ¬q first)
    result = engine3.revise("q", 0.7)
    print(f"   Revise with 'q':")
    print(f"     Removed: {result.removed_beliefs}")
    print(f"     Result: {engine3.all_beliefs()}")
    print()

    # 9. Undo
    print("9. UNDO OPERATION:")
    print("-" * 40)

    print(f"   Before undo: {engine3.all_beliefs()}")
    undone = engine3.undo()
    if undone:
        print(f"   Undid: {undone.operation.value} of '{undone.input_belief}'")
        print(f"   After undo: {engine3.all_beliefs()}")
    print()

    # 10. History
    print("10. REVISION HISTORY:")
    print("-" * 40)

    for i, h in enumerate(engine.history()):
        print(f"   {i+1}. {h.operation.value}: {h.input_belief}")
    print()

    # 11. Compare Entrenchment
    print("11. COMPARE ENTRENCHMENT:")
    print("-" * 40)

    cmp = engine.compare_entrenchment("has_wings", "sings")
    relation = ">" if cmp > 0 else ("<" if cmp < 0 else "=")
    print(f"   has_wings {relation} sings in entrenchment")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Belief Revision Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
