#!/usr/bin/env python3
"""
BAEL - Belief Manager
Advanced belief management for AI agents.

Features:
- Belief representation and storage
- Belief revision and update
- Belief strength tracking
- Justification chains
- Contradiction detection
- Belief propagation
- Evidence accumulation
- Truth maintenance
"""

import asyncio
import copy
import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class BeliefStatus(Enum):
    """Belief status."""
    ACTIVE = "active"
    RETRACTED = "retracted"
    SUSPENDED = "suspended"
    CONTRADICTED = "contradicted"


class BeliefType(Enum):
    """Belief type."""
    FACT = "fact"
    INFERENCE = "inference"
    ASSUMPTION = "assumption"
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"


class BeliefSource(Enum):
    """Belief source."""
    PERCEPTION = "perception"
    INFERENCE = "inference"
    COMMUNICATION = "communication"
    MEMORY = "memory"
    DEFAULT = "default"


class RevisionOperation(Enum):
    """Belief revision operation."""
    EXPAND = "expand"
    CONTRACT = "contract"
    REVISE = "revise"


class EvidenceType(Enum):
    """Evidence type."""
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    NEUTRAL = "neutral"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Belief:
    """A belief."""
    belief_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposition: str = ""
    belief_type: BeliefType = BeliefType.FACT
    source: BeliefSource = BeliefSource.DEFAULT
    status: BeliefStatus = BeliefStatus.ACTIVE
    strength: float = 1.0  # 0.0 to 1.0
    confidence: float = 1.0  # 0.0 to 1.0
    justifications: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Justification:
    """Justification for a belief."""
    justification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    belief_id: str = ""
    supporting_beliefs: List[str] = field(default_factory=list)
    rule: str = ""
    strength: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Evidence:
    """Evidence for/against a belief."""
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    belief_id: str = ""
    evidence_type: EvidenceType = EvidenceType.SUPPORTING
    content: str = ""
    weight: float = 1.0
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Contradiction:
    """Contradiction between beliefs."""
    contradiction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    belief_ids: List[str] = field(default_factory=list)
    reason: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False


@dataclass
class RevisionResult:
    """Result of belief revision."""
    operation: RevisionOperation = RevisionOperation.EXPAND
    affected_beliefs: List[str] = field(default_factory=list)
    retracted_beliefs: List[str] = field(default_factory=list)
    added_beliefs: List[str] = field(default_factory=list)
    success: bool = True


@dataclass
class BeliefStats:
    """Belief statistics."""
    total_beliefs: int = 0
    active_beliefs: int = 0
    retracted_beliefs: int = 0
    avg_strength: float = 0.0
    contradictions: int = 0


# =============================================================================
# BELIEF STORE
# =============================================================================

class BeliefStore:
    """Store for beliefs."""

    def __init__(self):
        self._beliefs: Dict[str, Belief] = {}
        self._by_proposition: Dict[str, Set[str]] = defaultdict(set)
        self._by_type: Dict[BeliefType, Set[str]] = defaultdict(set)
        self._by_status: Dict[BeliefStatus, Set[str]] = defaultdict(set)

    def add(self, belief: Belief) -> str:
        """Add belief."""
        self._beliefs[belief.belief_id] = belief

        # Index by proposition (normalized)
        prop_key = belief.proposition.lower().strip()
        self._by_proposition[prop_key].add(belief.belief_id)

        # Index by type
        self._by_type[belief.belief_type].add(belief.belief_id)

        # Index by status
        self._by_status[belief.status].add(belief.belief_id)

        return belief.belief_id

    def get(self, belief_id: str) -> Optional[Belief]:
        """Get belief by ID."""
        return self._beliefs.get(belief_id)

    def get_by_proposition(self, proposition: str) -> List[Belief]:
        """Get beliefs by proposition."""
        prop_key = proposition.lower().strip()
        ids = self._by_proposition.get(prop_key, set())
        return [self._beliefs[bid] for bid in ids if bid in self._beliefs]

    def get_by_type(self, belief_type: BeliefType) -> List[Belief]:
        """Get beliefs by type."""
        ids = self._by_type.get(belief_type, set())
        return [self._beliefs[bid] for bid in ids if bid in self._beliefs]

    def get_active(self) -> List[Belief]:
        """Get active beliefs."""
        ids = self._by_status.get(BeliefStatus.ACTIVE, set())
        return [self._beliefs[bid] for bid in ids if bid in self._beliefs]

    def update_status(
        self,
        belief_id: str,
        status: BeliefStatus
    ) -> bool:
        """Update belief status."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False

        # Remove from old status index
        self._by_status[belief.status].discard(belief_id)

        # Update status
        belief.status = status
        belief.updated_at = datetime.now()

        # Add to new status index
        self._by_status[status].add(belief_id)

        return True

    def update_strength(
        self,
        belief_id: str,
        strength: float
    ) -> bool:
        """Update belief strength."""
        belief = self._beliefs.get(belief_id)
        if belief:
            belief.strength = max(0.0, min(1.0, strength))
            belief.updated_at = datetime.now()
            return True
        return False

    def delete(self, belief_id: str) -> bool:
        """Delete belief."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False

        prop_key = belief.proposition.lower().strip()
        self._by_proposition[prop_key].discard(belief_id)
        self._by_type[belief.belief_type].discard(belief_id)
        self._by_status[belief.status].discard(belief_id)

        del self._beliefs[belief_id]
        return True

    def count(self) -> int:
        """Count beliefs."""
        return len(self._beliefs)

    def all(self) -> List[Belief]:
        """Get all beliefs."""
        return list(self._beliefs.values())


# =============================================================================
# JUSTIFICATION STORE
# =============================================================================

class JustificationStore:
    """Store for justifications."""

    def __init__(self):
        self._justifications: Dict[str, Justification] = {}
        self._by_belief: Dict[str, List[str]] = defaultdict(list)

    def add(self, justification: Justification) -> str:
        """Add justification."""
        self._justifications[justification.justification_id] = justification
        self._by_belief[justification.belief_id].append(
            justification.justification_id
        )
        return justification.justification_id

    def get(self, justification_id: str) -> Optional[Justification]:
        """Get justification."""
        return self._justifications.get(justification_id)

    def get_for_belief(self, belief_id: str) -> List[Justification]:
        """Get justifications for belief."""
        ids = self._by_belief.get(belief_id, [])
        return [
            self._justifications[jid]
            for jid in ids
            if jid in self._justifications
        ]

    def delete(self, justification_id: str) -> bool:
        """Delete justification."""
        justification = self._justifications.get(justification_id)
        if justification:
            self._by_belief[justification.belief_id].remove(justification_id)
            del self._justifications[justification_id]
            return True
        return False


# =============================================================================
# EVIDENCE STORE
# =============================================================================

class EvidenceStore:
    """Store for evidence."""

    def __init__(self):
        self._evidence: Dict[str, Evidence] = {}
        self._by_belief: Dict[str, List[str]] = defaultdict(list)

    def add(self, evidence: Evidence) -> str:
        """Add evidence."""
        self._evidence[evidence.evidence_id] = evidence
        self._by_belief[evidence.belief_id].append(evidence.evidence_id)
        return evidence.evidence_id

    def get(self, evidence_id: str) -> Optional[Evidence]:
        """Get evidence."""
        return self._evidence.get(evidence_id)

    def get_for_belief(self, belief_id: str) -> List[Evidence]:
        """Get evidence for belief."""
        ids = self._by_belief.get(belief_id, [])
        return [self._evidence[eid] for eid in ids if eid in self._evidence]

    def get_supporting(self, belief_id: str) -> List[Evidence]:
        """Get supporting evidence."""
        return [
            e for e in self.get_for_belief(belief_id)
            if e.evidence_type == EvidenceType.SUPPORTING
        ]

    def get_contradicting(self, belief_id: str) -> List[Evidence]:
        """Get contradicting evidence."""
        return [
            e for e in self.get_for_belief(belief_id)
            if e.evidence_type == EvidenceType.CONTRADICTING
        ]


# =============================================================================
# CONTRADICTION DETECTOR
# =============================================================================

class ContradictionDetector:
    """Detect contradictions."""

    def __init__(self, belief_store: BeliefStore):
        self._belief_store = belief_store
        self._contradictions: Dict[str, Contradiction] = {}
        self._negation_patterns = [
            ("not ", ""),
            ("is ", "is not "),
            ("can ", "cannot "),
            ("will ", "will not ")
        ]

    def detect(self, belief: Belief) -> List[Contradiction]:
        """Detect contradictions with a belief."""
        contradictions = []

        prop = belief.proposition.lower().strip()

        # Check for negation patterns
        for pattern, replacement in self._negation_patterns:
            negated = prop.replace(pattern, replacement)
            if negated == prop:
                negated = replacement + prop if replacement else pattern + prop

            # Find contradicting beliefs
            contradicting = self._belief_store.get_by_proposition(negated)

            for other in contradicting:
                if (other.belief_id != belief.belief_id and
                    other.status == BeliefStatus.ACTIVE):
                    contradiction = Contradiction(
                        belief_ids=[belief.belief_id, other.belief_id],
                        reason=f"Logical negation: '{belief.proposition}' vs '{other.proposition}'"
                    )
                    contradictions.append(contradiction)
                    self._contradictions[contradiction.contradiction_id] = contradiction

        return contradictions

    def get_all(self) -> List[Contradiction]:
        """Get all contradictions."""
        return list(self._contradictions.values())

    def resolve(
        self,
        contradiction_id: str,
        kept_belief_id: str
    ) -> bool:
        """Resolve contradiction by keeping one belief."""
        contradiction = self._contradictions.get(contradiction_id)
        if not contradiction:
            return False

        for bid in contradiction.belief_ids:
            if bid != kept_belief_id:
                self._belief_store.update_status(
                    bid,
                    BeliefStatus.CONTRADICTED
                )

        contradiction.resolved = True
        return True


# =============================================================================
# BELIEF REVISION
# =============================================================================

class BeliefRevision:
    """AGM-style belief revision."""

    def __init__(
        self,
        belief_store: BeliefStore,
        contradiction_detector: ContradictionDetector
    ):
        self._belief_store = belief_store
        self._contradiction_detector = contradiction_detector

    def expand(self, belief: Belief) -> RevisionResult:
        """Expand belief base (add without checking)."""
        belief_id = self._belief_store.add(belief)

        return RevisionResult(
            operation=RevisionOperation.EXPAND,
            added_beliefs=[belief_id],
            success=True
        )

    def contract(self, proposition: str) -> RevisionResult:
        """Contract belief base (remove belief)."""
        beliefs = self._belief_store.get_by_proposition(proposition)
        retracted = []

        for belief in beliefs:
            self._belief_store.update_status(
                belief.belief_id,
                BeliefStatus.RETRACTED
            )
            retracted.append(belief.belief_id)

        return RevisionResult(
            operation=RevisionOperation.CONTRACT,
            retracted_beliefs=retracted,
            success=True
        )

    def revise(self, belief: Belief) -> RevisionResult:
        """Revise belief base (add and resolve contradictions)."""
        # Detect contradictions first
        contradictions = self._contradiction_detector.detect(belief)

        retracted = []
        for contradiction in contradictions:
            # Retract weaker beliefs
            for bid in contradiction.belief_ids:
                other = self._belief_store.get(bid)
                if other and other.strength < belief.strength:
                    self._belief_store.update_status(
                        bid,
                        BeliefStatus.RETRACTED
                    )
                    retracted.append(bid)

        # Add the new belief
        belief_id = self._belief_store.add(belief)

        return RevisionResult(
            operation=RevisionOperation.REVISE,
            added_beliefs=[belief_id],
            retracted_beliefs=retracted,
            affected_beliefs=[belief_id] + retracted,
            success=True
        )


# =============================================================================
# BELIEF PROPAGATION
# =============================================================================

class BeliefPropagation:
    """Propagate belief updates."""

    def __init__(
        self,
        belief_store: BeliefStore,
        justification_store: JustificationStore
    ):
        self._belief_store = belief_store
        self._justification_store = justification_store

    def propagate(self, belief_id: str) -> List[str]:
        """Propagate belief changes."""
        affected = []

        # Find beliefs that depend on this one
        for belief in self._belief_store.all():
            if belief.belief_id == belief_id:
                continue

            justifications = self._justification_store.get_for_belief(
                belief.belief_id
            )

            for justification in justifications:
                if belief_id in justification.supporting_beliefs:
                    # This belief depends on the changed one
                    source_belief = self._belief_store.get(belief_id)

                    if source_belief:
                        if source_belief.status != BeliefStatus.ACTIVE:
                            # Weaken the dependent belief
                            new_strength = belief.strength * 0.5
                            self._belief_store.update_strength(
                                belief.belief_id,
                                new_strength
                            )
                            affected.append(belief.belief_id)

        return affected


# =============================================================================
# TRUTH MAINTENANCE
# =============================================================================

class TruthMaintenance:
    """Truth maintenance system."""

    def __init__(
        self,
        belief_store: BeliefStore,
        justification_store: JustificationStore,
        propagation: BeliefPropagation
    ):
        self._belief_store = belief_store
        self._justification_store = justification_store
        self._propagation = propagation

    def maintain(self, belief_id: str) -> List[str]:
        """Maintain truth for a belief."""
        belief = self._belief_store.get(belief_id)
        if not belief:
            return []

        affected = []

        # Check if justifications are still valid
        justifications = self._justification_store.get_for_belief(belief_id)

        valid_justifications = []
        for justification in justifications:
            all_valid = True
            for support_id in justification.supporting_beliefs:
                support = self._belief_store.get(support_id)
                if not support or support.status != BeliefStatus.ACTIVE:
                    all_valid = False
                    break

            if all_valid:
                valid_justifications.append(justification)

        # Update belief based on justifications
        if not valid_justifications and belief.belief_type == BeliefType.INFERENCE:
            # No valid justifications for inferred belief
            self._belief_store.update_status(
                belief_id,
                BeliefStatus.SUSPENDED
            )
            affected.append(belief_id)

            # Propagate
            affected.extend(self._propagation.propagate(belief_id))

        return affected


# =============================================================================
# BELIEF MANAGER
# =============================================================================

class BeliefManager:
    """
    Belief Manager for BAEL.

    Advanced belief management.
    """

    def __init__(self):
        self._belief_store = BeliefStore()
        self._justification_store = JustificationStore()
        self._evidence_store = EvidenceStore()
        self._contradiction_detector = ContradictionDetector(self._belief_store)
        self._revision = BeliefRevision(
            self._belief_store,
            self._contradiction_detector
        )
        self._propagation = BeliefPropagation(
            self._belief_store,
            self._justification_store
        )
        self._truth_maintenance = TruthMaintenance(
            self._belief_store,
            self._justification_store,
            self._propagation
        )

    # -------------------------------------------------------------------------
    # BELIEF OPERATIONS
    # -------------------------------------------------------------------------

    def add_belief(
        self,
        proposition: str,
        belief_type: str = "fact",
        source: str = "default",
        strength: float = 1.0,
        confidence: float = 1.0
    ) -> str:
        """Add a belief."""
        type_map = {
            "fact": BeliefType.FACT,
            "inference": BeliefType.INFERENCE,
            "assumption": BeliefType.ASSUMPTION,
            "observation": BeliefType.OBSERVATION,
            "hypothesis": BeliefType.HYPOTHESIS
        }

        source_map = {
            "perception": BeliefSource.PERCEPTION,
            "inference": BeliefSource.INFERENCE,
            "communication": BeliefSource.COMMUNICATION,
            "memory": BeliefSource.MEMORY,
            "default": BeliefSource.DEFAULT
        }

        belief = Belief(
            proposition=proposition,
            belief_type=type_map.get(belief_type.lower(), BeliefType.FACT),
            source=source_map.get(source.lower(), BeliefSource.DEFAULT),
            strength=strength,
            confidence=confidence
        )

        result = self._revision.revise(belief)

        if result.added_beliefs:
            return result.added_beliefs[0]

        return ""

    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """Get belief."""
        return self._belief_store.get(belief_id)

    def find_beliefs(self, proposition: str) -> List[Belief]:
        """Find beliefs by proposition."""
        return self._belief_store.get_by_proposition(proposition)

    def get_active_beliefs(self) -> List[Belief]:
        """Get active beliefs."""
        return self._belief_store.get_active()

    def update_strength(
        self,
        belief_id: str,
        strength: float
    ) -> bool:
        """Update belief strength."""
        return self._belief_store.update_strength(belief_id, strength)

    def retract_belief(self, belief_id: str) -> bool:
        """Retract a belief."""
        success = self._belief_store.update_status(
            belief_id,
            BeliefStatus.RETRACTED
        )

        if success:
            self._propagation.propagate(belief_id)

        return success

    def retract_by_proposition(self, proposition: str) -> int:
        """Retract beliefs by proposition."""
        result = self._revision.contract(proposition)
        return len(result.retracted_beliefs)

    # -------------------------------------------------------------------------
    # JUSTIFICATION
    # -------------------------------------------------------------------------

    def add_justification(
        self,
        belief_id: str,
        supporting_beliefs: List[str],
        rule: str = ""
    ) -> str:
        """Add justification for belief."""
        justification = Justification(
            belief_id=belief_id,
            supporting_beliefs=supporting_beliefs,
            rule=rule
        )

        # Update belief justifications
        belief = self._belief_store.get(belief_id)
        if belief:
            belief.justifications.append(justification.justification_id)

        return self._justification_store.add(justification)

    def get_justifications(self, belief_id: str) -> List[Justification]:
        """Get justifications for belief."""
        return self._justification_store.get_for_belief(belief_id)

    # -------------------------------------------------------------------------
    # EVIDENCE
    # -------------------------------------------------------------------------

    def add_evidence(
        self,
        belief_id: str,
        content: str,
        evidence_type: str = "supporting",
        weight: float = 1.0
    ) -> str:
        """Add evidence for belief."""
        type_map = {
            "supporting": EvidenceType.SUPPORTING,
            "contradicting": EvidenceType.CONTRADICTING,
            "neutral": EvidenceType.NEUTRAL
        }

        evidence = Evidence(
            belief_id=belief_id,
            evidence_type=type_map.get(evidence_type.lower(), EvidenceType.SUPPORTING),
            content=content,
            weight=weight
        )

        eid = self._evidence_store.add(evidence)

        # Update belief strength based on evidence
        self._update_from_evidence(belief_id)

        return eid

    def _update_from_evidence(self, belief_id: str) -> None:
        """Update belief strength from evidence."""
        supporting = self._evidence_store.get_supporting(belief_id)
        contradicting = self._evidence_store.get_contradicting(belief_id)

        support_weight = sum(e.weight for e in supporting)
        contradict_weight = sum(e.weight for e in contradicting)

        total = support_weight + contradict_weight
        if total > 0:
            strength = support_weight / total
            self._belief_store.update_strength(belief_id, strength)

    def get_evidence(self, belief_id: str) -> List[Evidence]:
        """Get evidence for belief."""
        return self._evidence_store.get_for_belief(belief_id)

    # -------------------------------------------------------------------------
    # CONTRADICTION
    # -------------------------------------------------------------------------

    def detect_contradictions(self, belief_id: str) -> List[Contradiction]:
        """Detect contradictions."""
        belief = self._belief_store.get(belief_id)
        if belief:
            return self._contradiction_detector.detect(belief)
        return []

    def get_contradictions(self) -> List[Contradiction]:
        """Get all contradictions."""
        return self._contradiction_detector.get_all()

    def resolve_contradiction(
        self,
        contradiction_id: str,
        kept_belief_id: str
    ) -> bool:
        """Resolve contradiction."""
        return self._contradiction_detector.resolve(
            contradiction_id,
            kept_belief_id
        )

    # -------------------------------------------------------------------------
    # INFERENCE
    # -------------------------------------------------------------------------

    def infer(
        self,
        proposition: str,
        from_beliefs: List[str],
        rule: str = ""
    ) -> str:
        """Infer a new belief."""
        # Check if all source beliefs are active
        for bid in from_beliefs:
            belief = self._belief_store.get(bid)
            if not belief or belief.status != BeliefStatus.ACTIVE:
                return ""

        # Calculate strength from source beliefs
        strengths = [
            self._belief_store.get(bid).strength
            for bid in from_beliefs
            if self._belief_store.get(bid)
        ]

        inferred_strength = min(strengths) if strengths else 0.5

        # Create inferred belief
        belief_id = self.add_belief(
            proposition,
            belief_type="inference",
            source="inference",
            strength=inferred_strength
        )

        # Add justification
        if belief_id:
            self.add_justification(belief_id, from_beliefs, rule)

        return belief_id

    # -------------------------------------------------------------------------
    # TRUTH MAINTENANCE
    # -------------------------------------------------------------------------

    def maintain_truth(self, belief_id: str) -> List[str]:
        """Maintain truth for belief."""
        return self._truth_maintenance.maintain(belief_id)

    def maintain_all(self) -> List[str]:
        """Maintain truth for all beliefs."""
        affected = []

        for belief in self._belief_store.all():
            affected.extend(self.maintain_truth(belief.belief_id))

        return affected

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> BeliefStats:
        """Get belief statistics."""
        beliefs = self._belief_store.all()
        active = [b for b in beliefs if b.status == BeliefStatus.ACTIVE]
        retracted = [b for b in beliefs if b.status == BeliefStatus.RETRACTED]

        avg_strength = (
            sum(b.strength for b in active) / len(active)
            if active else 0.0
        )

        return BeliefStats(
            total_beliefs=len(beliefs),
            active_beliefs=len(active),
            retracted_beliefs=len(retracted),
            avg_strength=avg_strength,
            contradictions=len(self._contradiction_detector.get_all())
        )

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "beliefs": [
                {
                    "id": b.belief_id,
                    "proposition": b.proposition,
                    "type": b.belief_type.value,
                    "status": b.status.value,
                    "strength": b.strength,
                    "confidence": b.confidence
                }
                for b in self._belief_store.all()
            ],
            "stats": {
                "total": self._belief_store.count(),
                "active": len(self._belief_store.get_active())
            }
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Belief Manager."""
    print("=" * 70)
    print("BAEL - BELIEF MANAGER DEMO")
    print("Advanced Belief Management")
    print("=" * 70)
    print()

    manager = BeliefManager()

    # 1. Add Beliefs
    print("1. ADD BELIEFS:")
    print("-" * 40)

    b1 = manager.add_belief("The sky is blue", "observation", "perception", 0.9)
    b2 = manager.add_belief("Water is wet", "fact", "default", 1.0)
    b3 = manager.add_belief("Dogs are mammals", "fact", "memory", 0.95)
    b4 = manager.add_belief("Cats are mammals", "fact", "memory", 0.95)

    print(f"   Added: The sky is blue ({b1[:8]}...)")
    print(f"   Added: Water is wet ({b2[:8]}...)")
    print(f"   Added: Dogs are mammals ({b3[:8]}...)")
    print(f"   Added: Cats are mammals ({b4[:8]}...)")
    print()

    # 2. Get Belief
    print("2. GET BELIEF:")
    print("-" * 40)

    belief = manager.get_belief(b1)

    print(f"   Proposition: {belief.proposition}")
    print(f"   Type: {belief.belief_type.value}")
    print(f"   Strength: {belief.strength}")
    print(f"   Status: {belief.status.value}")
    print()

    # 3. Find Beliefs
    print("3. FIND BELIEFS:")
    print("-" * 40)

    found = manager.find_beliefs("Dogs are mammals")

    print(f"   Found: {len(found)} belief(s)")
    if found:
        print(f"   First: {found[0].proposition}")
    print()

    # 4. Add Justification
    print("4. ADD JUSTIFICATION:")
    print("-" * 40)

    b5 = manager.add_belief("Animals exist", "inference", "inference", 0.9)
    jid = manager.add_justification(b5, [b3, b4], "if mammals then animals")

    print(f"   Belief: Animals exist ({b5[:8]}...)")
    print(f"   Justified by: Dogs are mammals, Cats are mammals")
    print(f"   Rule: if mammals then animals")
    print()

    # 5. Add Evidence
    print("5. ADD EVIDENCE:")
    print("-" * 40)

    manager.add_evidence(b1, "Clear day observation", "supporting", 0.8)
    manager.add_evidence(b1, "Sunset with orange sky", "contradicting", 0.3)

    belief = manager.get_belief(b1)
    evidence = manager.get_evidence(b1)

    print(f"   Evidence for '{belief.proposition}':")
    for e in evidence:
        print(f"     - {e.content} ({e.evidence_type.value}, weight={e.weight})")
    print(f"   Updated strength: {belief.strength:.2f}")
    print()

    # 6. Contradiction Detection
    print("6. CONTRADICTION DETECTION:")
    print("-" * 40)

    b6 = manager.add_belief("The sky is not blue", "observation", "perception", 0.5)

    contradictions = manager.detect_contradictions(b6)

    print(f"   Detected contradictions: {len(contradictions)}")
    if contradictions:
        c = contradictions[0]
        print(f"   Reason: {c.reason}")
    print()

    # 7. Inference
    print("7. INFERENCE:")
    print("-" * 40)

    b7 = manager.infer(
        "Dogs and cats are related",
        [b3, b4],
        "both are mammals"
    )

    inferred = manager.get_belief(b7)

    print(f"   Inferred: {inferred.proposition}")
    print(f"   Strength: {inferred.strength}")

    justifications = manager.get_justifications(b7)
    print(f"   Justifications: {len(justifications)}")
    print()

    # 8. Update Strength
    print("8. UPDATE STRENGTH:")
    print("-" * 40)

    original = manager.get_belief(b3).strength
    manager.update_strength(b3, 0.7)
    updated = manager.get_belief(b3).strength

    print(f"   'Dogs are mammals' strength:")
    print(f"   Before: {original}")
    print(f"   After: {updated}")
    print()

    # 9. Retract Belief
    print("9. RETRACT BELIEF:")
    print("-" * 40)

    manager.retract_belief(b6)
    retracted = manager.get_belief(b6)

    print(f"   Retracted: {retracted.proposition}")
    print(f"   Status: {retracted.status.value}")
    print()

    # 10. Active Beliefs
    print("10. ACTIVE BELIEFS:")
    print("-" * 40)

    active = manager.get_active_beliefs()

    print(f"   Active beliefs: {len(active)}")
    for b in active[:3]:
        print(f"     - {b.proposition} (strength={b.strength:.2f})")
    print()

    # 11. Truth Maintenance
    print("11. TRUTH MAINTENANCE:")
    print("-" * 40)

    # Retract a supporting belief
    manager.retract_belief(b3)
    affected = manager.maintain_all()

    print(f"   Retracted: Dogs are mammals")
    print(f"   Affected beliefs: {len(affected)}")
    print()

    # 12. Get Contradictions
    print("12. ALL CONTRADICTIONS:")
    print("-" * 40)

    all_contradictions = manager.get_contradictions()

    print(f"   Total contradictions: {len(all_contradictions)}")
    for c in all_contradictions[:2]:
        print(f"     - {c.reason[:50]}...")
    print()

    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total beliefs: {stats.total_beliefs}")
    print(f"   Active: {stats.active_beliefs}")
    print(f"   Retracted: {stats.retracted_beliefs}")
    print(f"   Avg strength: {stats.avg_strength:.2f}")
    print(f"   Contradictions: {stats.contradictions}")
    print()

    # 14. Export
    print("14. EXPORT:")
    print("-" * 40)

    export = manager.to_dict()

    print(f"   Exported beliefs: {len(export['beliefs'])}")
    print(f"   Export preview: {json.dumps(export['stats'], indent=2)}")
    print()

    # 15. Belief Types
    print("15. BELIEFS BY TYPE:")
    print("-" * 40)

    facts = manager._belief_store.get_by_type(BeliefType.FACT)
    observations = manager._belief_store.get_by_type(BeliefType.OBSERVATION)
    inferences = manager._belief_store.get_by_type(BeliefType.INFERENCE)

    print(f"   Facts: {len(facts)}")
    print(f"   Observations: {len(observations)}")
    print(f"   Inferences: {len(inferences)}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Belief Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
