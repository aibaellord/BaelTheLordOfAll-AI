#!/usr/bin/env python3
"""
BAEL - Belief Engine
Agent belief management and reasoning.

Features:
- Belief representation
- Belief revision
- Truth maintenance
- Confidence tracking
- Epistemic reasoning
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

class BeliefType(Enum):
    """Types of beliefs."""
    FACTUAL = "factual"
    HYPOTHETICAL = "hypothetical"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    DERIVED = "derived"
    OBSERVED = "observed"


class BeliefStatus(Enum):
    """Belief status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETRACTED = "retracted"
    CONTRADICTED = "contradicted"


class ConfidenceLevel(Enum):
    """Confidence levels."""
    CERTAIN = 1.0
    HIGH = 0.8
    MODERATE = 0.6
    LOW = 0.4
    UNCERTAIN = 0.2


class RevisionType(Enum):
    """Belief revision types."""
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    REVISION = "revision"
    CONSOLIDATION = "consolidation"


class EpistemicMode(Enum):
    """Epistemic modalities."""
    KNOW = "know"
    BELIEVE = "believe"
    SUSPECT = "suspect"
    DOUBT = "doubt"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Belief:
    """A belief."""
    belief_id: str = ""
    content: str = ""
    belief_type: BeliefType = BeliefType.FACTUAL
    status: BeliefStatus = BeliefStatus.ACTIVE
    confidence: float = 1.0
    source: str = ""
    justifications: List[str] = field(default_factory=list)
    supports: List[str] = field(default_factory=list)
    contradicts: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.belief_id:
            self.belief_id = str(uuid.uuid4())[:8]

    def __hash__(self):
        return hash(self.belief_id)

    def __eq__(self, other):
        if isinstance(other, Belief):
            return self.belief_id == other.belief_id
        return False


@dataclass
class BeliefRevision:
    """Belief revision record."""
    revision_id: str = ""
    belief_id: str = ""
    revision_type: RevisionType = RevisionType.REVISION
    old_content: str = ""
    new_content: str = ""
    old_confidence: float = 1.0
    new_confidence: float = 1.0
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.revision_id:
            self.revision_id = str(uuid.uuid4())[:8]


@dataclass
class JustificationNode:
    """Node in justification network."""
    node_id: str = ""
    belief_id: str = ""
    premises: List[str] = field(default_factory=list)
    inference_rule: str = ""
    strength: float = 1.0

    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid.uuid4())[:8]


@dataclass
class EpistemicState:
    """Agent epistemic state."""
    agent_id: str = ""
    beliefs: Dict[str, float] = field(default_factory=dict)
    knowledge: Set[str] = field(default_factory=set)
    suspicions: Set[str] = field(default_factory=set)
    doubts: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = str(uuid.uuid4())[:8]


@dataclass
class BeliefQuery:
    """Query for beliefs."""
    content_pattern: Optional[str] = None
    belief_types: Optional[List[BeliefType]] = None
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    status: Optional[BeliefStatus] = None
    source: Optional[str] = None


@dataclass
class BeliefStats:
    """Belief statistics."""
    total_beliefs: int = 0
    active_beliefs: int = 0
    retracted_beliefs: int = 0
    avg_confidence: float = 0.0
    by_type: Dict[str, int] = field(default_factory=dict)
    revisions: int = 0


# =============================================================================
# BELIEF BASE
# =============================================================================

class BeliefBase:
    """Collection of beliefs."""

    def __init__(self):
        self._beliefs: Dict[str, Belief] = {}
        self._content_index: Dict[str, str] = {}
        self._by_type: Dict[BeliefType, Set[str]] = defaultdict(set)
        self._by_source: Dict[str, Set[str]] = defaultdict(set)

    def add(self, belief: Belief) -> bool:
        """Add a belief."""
        if belief.belief_id in self._beliefs:
            return False

        self._beliefs[belief.belief_id] = belief
        self._content_index[belief.content] = belief.belief_id
        self._by_type[belief.belief_type].add(belief.belief_id)

        if belief.source:
            self._by_source[belief.source].add(belief.belief_id)

        return True

    def remove(self, belief_id: str) -> Optional[Belief]:
        """Remove a belief."""
        belief = self._beliefs.pop(belief_id, None)

        if belief:
            self._content_index.pop(belief.content, None)
            self._by_type[belief.belief_type].discard(belief_id)

            if belief.source:
                self._by_source[belief.source].discard(belief_id)

        return belief

    def get(self, belief_id: str) -> Optional[Belief]:
        """Get a belief by ID."""
        return self._beliefs.get(belief_id)

    def get_by_content(self, content: str) -> Optional[Belief]:
        """Get a belief by content."""
        belief_id = self._content_index.get(content)
        if belief_id:
            return self._beliefs.get(belief_id)
        return None

    def query(self, query: BeliefQuery) -> List[Belief]:
        """Query beliefs."""
        results = []

        for belief in self._beliefs.values():
            if query.content_pattern:
                if query.content_pattern.lower() not in belief.content.lower():
                    continue

            if query.belief_types:
                if belief.belief_type not in query.belief_types:
                    continue

            if belief.confidence < query.min_confidence:
                continue

            if belief.confidence > query.max_confidence:
                continue

            if query.status and belief.status != query.status:
                continue

            if query.source and belief.source != query.source:
                continue

            results.append(belief)

        return results

    def all_active(self) -> List[Belief]:
        """Get all active beliefs."""
        return [b for b in self._beliefs.values() if b.status == BeliefStatus.ACTIVE]

    def by_type(self, belief_type: BeliefType) -> List[Belief]:
        """Get beliefs by type."""
        ids = self._by_type.get(belief_type, set())
        return [self._beliefs[bid] for bid in ids if bid in self._beliefs]

    def by_source(self, source: str) -> List[Belief]:
        """Get beliefs by source."""
        ids = self._by_source.get(source, set())
        return [self._beliefs[bid] for bid in ids if bid in self._beliefs]

    def contains(self, content: str) -> bool:
        """Check if belief exists."""
        return content in self._content_index

    def count(self) -> int:
        """Count beliefs."""
        return len(self._beliefs)

    def clear(self) -> None:
        """Clear all beliefs."""
        self._beliefs.clear()
        self._content_index.clear()
        self._by_type.clear()
        self._by_source.clear()


# =============================================================================
# JUSTIFICATION NETWORK
# =============================================================================

class JustificationNetwork:
    """Network of belief justifications."""

    def __init__(self):
        self._nodes: Dict[str, JustificationNode] = {}
        self._belief_nodes: Dict[str, List[str]] = defaultdict(list)
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._dependents: Dict[str, Set[str]] = defaultdict(set)

    def add_justification(
        self,
        belief_id: str,
        premises: List[str],
        inference_rule: str = "default",
        strength: float = 1.0
    ) -> JustificationNode:
        """Add a justification for a belief."""
        node = JustificationNode(
            belief_id=belief_id,
            premises=premises,
            inference_rule=inference_rule,
            strength=strength
        )

        self._nodes[node.node_id] = node
        self._belief_nodes[belief_id].append(node.node_id)

        for premise_id in premises:
            self._dependencies[belief_id].add(premise_id)
            self._dependents[premise_id].add(belief_id)

        return node

    def remove_justification(self, node_id: str) -> Optional[JustificationNode]:
        """Remove a justification."""
        node = self._nodes.pop(node_id, None)

        if node:
            self._belief_nodes[node.belief_id].remove(node_id)

            for premise_id in node.premises:
                self._dependencies[node.belief_id].discard(premise_id)
                self._dependents[premise_id].discard(node.belief_id)

        return node

    def get_justifications(self, belief_id: str) -> List[JustificationNode]:
        """Get justifications for a belief."""
        node_ids = self._belief_nodes.get(belief_id, [])
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def get_dependencies(self, belief_id: str) -> Set[str]:
        """Get beliefs this belief depends on."""
        return self._dependencies.get(belief_id, set())

    def get_dependents(self, belief_id: str) -> Set[str]:
        """Get beliefs that depend on this belief."""
        return self._dependents.get(belief_id, set())

    def is_grounded(self, belief_id: str) -> bool:
        """Check if belief is grounded (has independent support)."""
        justifications = self.get_justifications(belief_id)

        if not justifications:
            return True

        for justification in justifications:
            if not justification.premises:
                return True

        return False

    def propagate_retraction(self, belief_id: str) -> Set[str]:
        """Get beliefs that should be retracted."""
        affected = set()
        queue = [belief_id]

        while queue:
            current = queue.pop(0)
            dependents = self.get_dependents(current)

            for dependent in dependents:
                if dependent not in affected:
                    affected.add(dependent)
                    queue.append(dependent)

        return affected


# =============================================================================
# BELIEF REVISION OPERATOR
# =============================================================================

class BeliefRevisionOperator(ABC):
    """Base class for belief revision."""

    @abstractmethod
    def revise(
        self,
        belief_base: BeliefBase,
        new_belief: Belief
    ) -> List[BeliefRevision]:
        """Revise belief base with new belief."""
        pass


class AGMRevisionOperator(BeliefRevisionOperator):
    """AGM-style belief revision."""

    def revise(
        self,
        belief_base: BeliefBase,
        new_belief: Belief
    ) -> List[BeliefRevision]:
        """AGM revision: contraction + expansion."""
        revisions = []

        existing = belief_base.get_by_content(new_belief.content)

        if existing:
            if new_belief.confidence > existing.confidence:
                revision = BeliefRevision(
                    belief_id=existing.belief_id,
                    revision_type=RevisionType.REVISION,
                    old_content=existing.content,
                    new_content=new_belief.content,
                    old_confidence=existing.confidence,
                    new_confidence=new_belief.confidence,
                    reason="Higher confidence update"
                )

                existing.confidence = new_belief.confidence
                existing.updated_at = datetime.now()
                revisions.append(revision)
        else:
            for contradiction_id in new_belief.contradicts:
                contradicting = belief_base.get(contradiction_id)
                if contradicting and contradicting.status == BeliefStatus.ACTIVE:
                    if new_belief.confidence > contradicting.confidence:
                        revision = BeliefRevision(
                            belief_id=contradicting.belief_id,
                            revision_type=RevisionType.CONTRACTION,
                            old_content=contradicting.content,
                            new_content="",
                            old_confidence=contradicting.confidence,
                            new_confidence=0.0,
                            reason=f"Contradicted by {new_belief.belief_id}"
                        )

                        contradicting.status = BeliefStatus.CONTRADICTED
                        revisions.append(revision)

            belief_base.add(new_belief)
            revisions.append(BeliefRevision(
                belief_id=new_belief.belief_id,
                revision_type=RevisionType.EXPANSION,
                old_content="",
                new_content=new_belief.content,
                old_confidence=0.0,
                new_confidence=new_belief.confidence,
                reason="New belief added"
            ))

        return revisions


class ProbabilisticRevisionOperator(BeliefRevisionOperator):
    """Probabilistic belief revision."""

    def __init__(self, decay_rate: float = 0.1):
        self._decay_rate = decay_rate

    def revise(
        self,
        belief_base: BeliefBase,
        new_belief: Belief
    ) -> List[BeliefRevision]:
        """Bayesian-style revision."""
        revisions = []

        for belief in belief_base.all_active():
            if belief.belief_id in new_belief.supports:
                old_confidence = belief.confidence
                belief.confidence = min(1.0, belief.confidence * 1.2)

                if old_confidence != belief.confidence:
                    revisions.append(BeliefRevision(
                        belief_id=belief.belief_id,
                        revision_type=RevisionType.REVISION,
                        old_content=belief.content,
                        new_content=belief.content,
                        old_confidence=old_confidence,
                        new_confidence=belief.confidence,
                        reason="Supporting evidence"
                    ))

            elif belief.belief_id in new_belief.contradicts:
                old_confidence = belief.confidence
                belief.confidence = max(0.0, belief.confidence * 0.5)

                if old_confidence != belief.confidence:
                    revisions.append(BeliefRevision(
                        belief_id=belief.belief_id,
                        revision_type=RevisionType.REVISION,
                        old_content=belief.content,
                        new_content=belief.content,
                        old_confidence=old_confidence,
                        new_confidence=belief.confidence,
                        reason="Contradicting evidence"
                    ))

        belief_base.add(new_belief)
        revisions.append(BeliefRevision(
            belief_id=new_belief.belief_id,
            revision_type=RevisionType.EXPANSION,
            old_content="",
            new_content=new_belief.content,
            old_confidence=0.0,
            new_confidence=new_belief.confidence,
            reason="New belief added"
        ))

        return revisions


# =============================================================================
# TRUTH MAINTENANCE
# =============================================================================

class TruthMaintenanceSystem:
    """Maintain consistency of beliefs."""

    def __init__(self, belief_base: BeliefBase, network: JustificationNetwork):
        self._belief_base = belief_base
        self._network = network

    def check_consistency(self) -> List[Tuple[str, str]]:
        """Check for inconsistencies."""
        inconsistencies = []

        beliefs = self._belief_base.all_active()

        for i, b1 in enumerate(beliefs):
            for b2 in beliefs[i + 1:]:
                if b2.belief_id in b1.contradicts or b1.belief_id in b2.contradicts:
                    inconsistencies.append((b1.belief_id, b2.belief_id))

        return inconsistencies

    def resolve_inconsistency(
        self,
        belief_id_1: str,
        belief_id_2: str
    ) -> Optional[str]:
        """Resolve inconsistency by retracting weaker belief."""
        b1 = self._belief_base.get(belief_id_1)
        b2 = self._belief_base.get(belief_id_2)

        if not b1 or not b2:
            return None

        if b1.confidence >= b2.confidence:
            b2.status = BeliefStatus.RETRACTED
            return belief_id_2
        else:
            b1.status = BeliefStatus.RETRACTED
            return belief_id_1

    def propagate_retraction(self, belief_id: str) -> Set[str]:
        """Propagate retraction through justification network."""
        affected = self._network.propagate_retraction(belief_id)

        for affected_id in affected:
            belief = self._belief_base.get(affected_id)
            if belief:
                if not self._has_alternative_support(affected_id):
                    belief.status = BeliefStatus.SUSPENDED

        return affected

    def _has_alternative_support(self, belief_id: str) -> bool:
        """Check if belief has alternative support."""
        justifications = self._network.get_justifications(belief_id)

        for justification in justifications:
            all_active = True

            for premise_id in justification.premises:
                premise = self._belief_base.get(premise_id)
                if not premise or premise.status != BeliefStatus.ACTIVE:
                    all_active = False
                    break

            if all_active:
                return True

        return self._network.is_grounded(belief_id)

    def consolidate(self) -> int:
        """Consolidate belief base by removing retracted beliefs."""
        to_remove = []

        for belief in self._belief_base._beliefs.values():
            if belief.status == BeliefStatus.RETRACTED:
                to_remove.append(belief.belief_id)

        for belief_id in to_remove:
            self._belief_base.remove(belief_id)

        return len(to_remove)


# =============================================================================
# EPISTEMIC REASONER
# =============================================================================

class EpistemicReasoner:
    """Reason about knowledge and beliefs."""

    def __init__(self, belief_base: BeliefBase):
        self._belief_base = belief_base
        self._epistemic_states: Dict[str, EpistemicState] = {}

    def create_epistemic_state(self, agent_id: str) -> EpistemicState:
        """Create epistemic state for an agent."""
        state = EpistemicState(agent_id=agent_id)
        self._epistemic_states[agent_id] = state
        return state

    def get_epistemic_state(self, agent_id: str) -> Optional[EpistemicState]:
        """Get agent's epistemic state."""
        return self._epistemic_states.get(agent_id)

    def classify_belief(self, belief: Belief) -> EpistemicMode:
        """Classify belief into epistemic mode."""
        if belief.confidence >= 0.95 and belief.belief_type == BeliefType.FACTUAL:
            return EpistemicMode.KNOW
        elif belief.confidence >= 0.6:
            return EpistemicMode.BELIEVE
        elif belief.confidence >= 0.3:
            return EpistemicMode.SUSPECT
        else:
            return EpistemicMode.DOUBT

    def update_epistemic_state(
        self,
        agent_id: str,
        belief: Belief
    ) -> EpistemicState:
        """Update agent's epistemic state."""
        state = self._epistemic_states.get(agent_id)

        if not state:
            state = self.create_epistemic_state(agent_id)

        mode = self.classify_belief(belief)

        if mode == EpistemicMode.KNOW:
            state.knowledge.add(belief.belief_id)
            state.beliefs[belief.belief_id] = belief.confidence
        elif mode == EpistemicMode.BELIEVE:
            state.beliefs[belief.belief_id] = belief.confidence
        elif mode == EpistemicMode.SUSPECT:
            state.suspicions.add(belief.belief_id)
            state.beliefs[belief.belief_id] = belief.confidence
        else:
            state.doubts.add(belief.belief_id)

        return state

    def knows(self, agent_id: str, belief_id: str) -> bool:
        """Check if agent knows belief."""
        state = self._epistemic_states.get(agent_id)
        return state and belief_id in state.knowledge

    def believes(self, agent_id: str, belief_id: str) -> Optional[float]:
        """Check agent's belief degree."""
        state = self._epistemic_states.get(agent_id)
        if state:
            return state.beliefs.get(belief_id)
        return None

    def common_beliefs(
        self,
        agent_ids: List[str],
        min_confidence: float = 0.5
    ) -> Set[str]:
        """Find common beliefs among agents."""
        if not agent_ids:
            return set()

        common = None

        for agent_id in agent_ids:
            state = self._epistemic_states.get(agent_id)
            if not state:
                return set()

            agent_beliefs = {
                bid for bid, conf in state.beliefs.items()
                if conf >= min_confidence
            }

            if common is None:
                common = agent_beliefs
            else:
                common = common.intersection(agent_beliefs)

        return common or set()


# =============================================================================
# BELIEF ENGINE
# =============================================================================

class BeliefEngine:
    """
    Belief Engine for BAEL.

    Agent belief management and reasoning.
    """

    def __init__(self):
        self._belief_base = BeliefBase()
        self._network = JustificationNetwork()
        self._tms = TruthMaintenanceSystem(self._belief_base, self._network)
        self._revision_operator: BeliefRevisionOperator = AGMRevisionOperator()
        self._reasoner = EpistemicReasoner(self._belief_base)

        self._revisions: List[BeliefRevision] = []
        self._stats = BeliefStats()

    def add_belief(
        self,
        content: str,
        belief_type: BeliefType = BeliefType.FACTUAL,
        confidence: float = 1.0,
        source: str = "",
        justifications: Optional[List[str]] = None,
        supports: Optional[List[str]] = None,
        contradicts: Optional[List[str]] = None
    ) -> Belief:
        """Add a belief."""
        belief = Belief(
            content=content,
            belief_type=belief_type,
            confidence=confidence,
            source=source,
            justifications=justifications or [],
            supports=supports or [],
            contradicts=contradicts or []
        )

        revisions = self._revision_operator.revise(self._belief_base, belief)
        self._revisions.extend(revisions)

        if justifications:
            premise_ids = []
            for just_content in justifications:
                just_belief = self._belief_base.get_by_content(just_content)
                if just_belief:
                    premise_ids.append(just_belief.belief_id)

            if premise_ids:
                self._network.add_justification(belief.belief_id, premise_ids)

        self._update_stats()

        return belief

    def revise_belief(
        self,
        belief_id: str,
        new_content: Optional[str] = None,
        new_confidence: Optional[float] = None
    ) -> Optional[BeliefRevision]:
        """Revise an existing belief."""
        belief = self._belief_base.get(belief_id)
        if not belief:
            return None

        revision = BeliefRevision(
            belief_id=belief_id,
            revision_type=RevisionType.REVISION,
            old_content=belief.content,
            new_content=new_content or belief.content,
            old_confidence=belief.confidence,
            new_confidence=new_confidence if new_confidence is not None else belief.confidence
        )

        if new_content:
            self._belief_base._content_index.pop(belief.content, None)
            belief.content = new_content
            self._belief_base._content_index[new_content] = belief_id

        if new_confidence is not None:
            belief.confidence = new_confidence

        belief.updated_at = datetime.now()

        self._revisions.append(revision)
        self._update_stats()

        return revision

    def retract_belief(self, belief_id: str) -> Set[str]:
        """Retract a belief and propagate."""
        belief = self._belief_base.get(belief_id)
        if not belief:
            return set()

        belief.status = BeliefStatus.RETRACTED

        affected = self._tms.propagate_retraction(belief_id)

        self._revisions.append(BeliefRevision(
            belief_id=belief_id,
            revision_type=RevisionType.CONTRACTION,
            old_content=belief.content,
            new_content="",
            old_confidence=belief.confidence,
            new_confidence=0.0,
            reason="Manual retraction"
        ))

        self._update_stats()

        return affected

    def query(self, query: BeliefQuery) -> List[Belief]:
        """Query beliefs."""
        return self._belief_base.query(query)

    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """Get a belief by ID."""
        return self._belief_base.get(belief_id)

    def get_by_content(self, content: str) -> Optional[Belief]:
        """Get a belief by content."""
        return self._belief_base.get_by_content(content)

    def has_belief(self, content: str) -> bool:
        """Check if belief exists."""
        return self._belief_base.contains(content)

    def get_active_beliefs(self) -> List[Belief]:
        """Get all active beliefs."""
        return self._belief_base.all_active()

    def get_by_type(self, belief_type: BeliefType) -> List[Belief]:
        """Get beliefs by type."""
        return self._belief_base.by_type(belief_type)

    def add_justification(
        self,
        belief_id: str,
        premise_ids: List[str],
        inference_rule: str = "default"
    ) -> Optional[JustificationNode]:
        """Add justification for a belief."""
        belief = self._belief_base.get(belief_id)
        if not belief:
            return None

        for premise_id in premise_ids:
            if not self._belief_base.get(premise_id):
                return None

        return self._network.add_justification(belief_id, premise_ids, inference_rule)

    def get_justifications(self, belief_id: str) -> List[JustificationNode]:
        """Get justifications for a belief."""
        return self._network.get_justifications(belief_id)

    def get_dependencies(self, belief_id: str) -> Set[str]:
        """Get beliefs this belief depends on."""
        return self._network.get_dependencies(belief_id)

    def get_dependents(self, belief_id: str) -> Set[str]:
        """Get beliefs that depend on this belief."""
        return self._network.get_dependents(belief_id)

    def check_consistency(self) -> List[Tuple[str, str]]:
        """Check belief consistency."""
        return self._tms.check_consistency()

    def resolve_inconsistencies(self) -> List[str]:
        """Resolve all inconsistencies."""
        resolved = []

        inconsistencies = self.check_consistency()

        for b1_id, b2_id in inconsistencies:
            retracted = self._tms.resolve_inconsistency(b1_id, b2_id)
            if retracted:
                resolved.append(retracted)

        return resolved

    def consolidate(self) -> int:
        """Consolidate belief base."""
        return self._tms.consolidate()

    def create_agent_epistemic_state(self, agent_id: str) -> EpistemicState:
        """Create epistemic state for an agent."""
        return self._reasoner.create_epistemic_state(agent_id)

    def update_agent_belief(
        self,
        agent_id: str,
        belief_id: str
    ) -> Optional[EpistemicState]:
        """Update agent's epistemic state with belief."""
        belief = self._belief_base.get(belief_id)
        if not belief:
            return None

        return self._reasoner.update_epistemic_state(agent_id, belief)

    def agent_knows(self, agent_id: str, belief_id: str) -> bool:
        """Check if agent knows belief."""
        return self._reasoner.knows(agent_id, belief_id)

    def agent_believes(
        self,
        agent_id: str,
        belief_id: str
    ) -> Optional[float]:
        """Get agent's belief degree."""
        return self._reasoner.believes(agent_id, belief_id)

    def common_beliefs(
        self,
        agent_ids: List[str],
        min_confidence: float = 0.5
    ) -> Set[str]:
        """Find common beliefs among agents."""
        return self._reasoner.common_beliefs(agent_ids, min_confidence)

    def set_revision_operator(self, operator: BeliefRevisionOperator) -> None:
        """Set the belief revision operator."""
        self._revision_operator = operator

    def get_revisions(self, count: int = 10) -> List[BeliefRevision]:
        """Get recent revisions."""
        return self._revisions[-count:]

    def _update_stats(self) -> None:
        """Update statistics."""
        beliefs = list(self._belief_base._beliefs.values())

        self._stats.total_beliefs = len(beliefs)
        self._stats.active_beliefs = sum(
            1 for b in beliefs if b.status == BeliefStatus.ACTIVE
        )
        self._stats.retracted_beliefs = sum(
            1 for b in beliefs if b.status == BeliefStatus.RETRACTED
        )

        if beliefs:
            self._stats.avg_confidence = sum(b.confidence for b in beliefs) / len(beliefs)

        self._stats.by_type = {}
        for belief in beliefs:
            key = belief.belief_type.value
            self._stats.by_type[key] = self._stats.by_type.get(key, 0) + 1

        self._stats.revisions = len(self._revisions)

    @property
    def stats(self) -> BeliefStats:
        """Get belief statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_beliefs": self._stats.total_beliefs,
            "active_beliefs": self._stats.active_beliefs,
            "retracted_beliefs": self._stats.retracted_beliefs,
            "avg_confidence": round(self._stats.avg_confidence, 3),
            "by_type": self._stats.by_type,
            "revisions": self._stats.revisions,
            "justification_nodes": len(self._network._nodes)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Belief Engine."""
    print("=" * 70)
    print("BAEL - BELIEF ENGINE DEMO")
    print("Agent Belief Management and Reasoning")
    print("=" * 70)
    print()

    engine = BeliefEngine()

    # 1. Add Beliefs
    print("1. ADD BELIEFS:")
    print("-" * 40)

    b1 = engine.add_belief(
        content="The sky is blue",
        belief_type=BeliefType.OBSERVED,
        confidence=0.95,
        source="perception"
    )

    b2 = engine.add_belief(
        content="Water is wet",
        belief_type=BeliefType.FACTUAL,
        confidence=1.0,
        source="knowledge_base"
    )

    b3 = engine.add_belief(
        content="It will rain tomorrow",
        belief_type=BeliefType.HYPOTHETICAL,
        confidence=0.6,
        source="inference"
    )

    print(f"   {b1.belief_id}: {b1.content} (conf: {b1.confidence})")
    print(f"   {b2.belief_id}: {b2.content} (conf: {b2.confidence})")
    print(f"   {b3.belief_id}: {b3.content} (conf: {b3.confidence})")
    print()

    # 2. Derived Belief with Justification
    print("2. DERIVED BELIEF WITH JUSTIFICATION:")
    print("-" * 40)

    b4 = engine.add_belief(
        content="I should bring an umbrella",
        belief_type=BeliefType.DERIVED,
        confidence=0.55,
        source="reasoning",
        justifications=["It will rain tomorrow"]
    )

    justifications = engine.get_justifications(b4.belief_id)

    print(f"   Belief: {b4.content}")
    print(f"   Type: {b4.belief_type.value}")
    print(f"   Confidence: {b4.confidence}")
    print(f"   Justifications: {len(justifications)}")
    print()

    # 3. Belief Revision
    print("3. BELIEF REVISION:")
    print("-" * 40)

    old_conf = b3.confidence
    revision = engine.revise_belief(
        b3.belief_id,
        new_confidence=0.85
    )

    print(f"   Revised: {b3.content}")
    print(f"   Old Confidence: {old_conf}")
    print(f"   New Confidence: {b3.confidence}")
    print()

    # 4. Contradicting Beliefs
    print("4. CONTRADICTING BELIEFS:")
    print("-" * 40)

    b5 = engine.add_belief(
        content="It will be sunny tomorrow",
        belief_type=BeliefType.HYPOTHETICAL,
        confidence=0.7,
        contradicts=[b3.belief_id]
    )

    print(f"   Added: {b5.content}")
    print(f"   Contradicts: {b3.belief_id}")

    inconsistencies = engine.check_consistency()

    print(f"   Inconsistencies: {len(inconsistencies)}")
    print()

    # 5. Resolve Inconsistencies
    print("5. RESOLVE INCONSISTENCIES:")
    print("-" * 40)

    resolved = engine.resolve_inconsistencies()

    print(f"   Resolved: {len(resolved)} inconsistencies")
    for rid in resolved:
        belief = engine.get_belief(rid)
        if belief:
            print(f"      Retracted: {belief.content}")
    print()

    # 6. Query Beliefs
    print("6. QUERY BELIEFS:")
    print("-" * 40)

    query = BeliefQuery(
        min_confidence=0.5,
        status=BeliefStatus.ACTIVE
    )

    results = engine.query(query)

    print(f"   Active beliefs with confidence >= 0.5:")
    for belief in results:
        print(f"      {belief.content} ({belief.confidence})")
    print()

    # 7. Epistemic Reasoning
    print("7. EPISTEMIC REASONING:")
    print("-" * 40)

    state1 = engine.create_agent_epistemic_state("agent_1")
    state2 = engine.create_agent_epistemic_state("agent_2")

    for belief in engine.get_active_beliefs():
        engine.update_agent_belief("agent_1", belief.belief_id)
        engine.update_agent_belief("agent_2", belief.belief_id)

    knows_water = engine.agent_knows("agent_1", b2.belief_id)
    believes_rain = engine.agent_believes("agent_1", b3.belief_id)

    print(f"   Agent 1 knows '{b2.content}': {knows_water}")
    print(f"   Agent 1 believes rain (degree): {believes_rain}")
    print()

    # 8. Common Beliefs
    print("8. COMMON BELIEFS:")
    print("-" * 40)

    common = engine.common_beliefs(["agent_1", "agent_2"], min_confidence=0.5)

    print(f"   Common beliefs (>= 0.5 confidence):")
    for bid in common:
        belief = engine.get_belief(bid)
        if belief:
            print(f"      {belief.content}")
    print()

    # 9. Belief Retraction
    print("9. BELIEF RETRACTION:")
    print("-" * 40)

    affected = engine.retract_belief(b3.belief_id)

    print(f"   Retracted: {b3.content}")
    print(f"   Affected dependent beliefs: {len(affected)}")
    for aid in affected:
        belief = engine.get_belief(aid)
        if belief:
            print(f"      {belief.content} -> {belief.status.value}")
    print()

    # 10. Probabilistic Revision
    print("10. PROBABILISTIC REVISION:")
    print("-" * 40)

    engine.set_revision_operator(ProbabilisticRevisionOperator(decay_rate=0.1))

    b6 = engine.add_belief(
        content="New supporting evidence",
        belief_type=BeliefType.OBSERVED,
        confidence=0.9,
        supports=[b2.belief_id]
    )

    updated_b2 = engine.get_belief(b2.belief_id)

    print(f"   Added supporting evidence for '{b2.content}'")
    print(f"   Updated confidence: {updated_b2.confidence}")
    print()

    # 11. Statistics
    print("11. STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Beliefs: {stats.total_beliefs}")
    print(f"   Active: {stats.active_beliefs}")
    print(f"   Retracted: {stats.retracted_beliefs}")
    print(f"   Avg Confidence: {stats.avg_confidence:.3f}")
    print(f"   By Type: {stats.by_type}")
    print(f"   Total Revisions: {stats.revisions}")
    print()

    # 12. Engine Summary
    print("12. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Total: {summary['total_beliefs']}")
    print(f"   Active: {summary['active_beliefs']}")
    print(f"   Revisions: {summary['revisions']}")
    print(f"   Justification Nodes: {summary['justification_nodes']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Belief Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
