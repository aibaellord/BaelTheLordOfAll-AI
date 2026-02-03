#!/usr/bin/env python3
"""
BAEL - Epistemic Reasoner
Advanced knowledge and belief reasoning.

Features:
- Knowledge bases
- Belief revision
- Justification tracking
- Epistemic logic
- Modal reasoning
- Evidence handling
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

class EpistemicState(Enum):
    """Epistemic states of propositions."""
    KNOWN = "known"
    BELIEVED = "believed"
    SUSPECTED = "suspected"
    UNKNOWN = "unknown"
    DOUBTED = "doubted"


class JustificationType(Enum):
    """Types of justification."""
    EMPIRICAL = "empirical"
    TESTIMONIAL = "testimonial"
    INFERENTIAL = "inferential"
    A_PRIORI = "a_priori"
    MEMORY = "memory"


class RevisionOperation(Enum):
    """Belief revision operations."""
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    REVISION = "revision"


class ModalOperator(Enum):
    """Modal operators."""
    KNOWS = "knows"
    BELIEVES = "believes"
    POSSIBLY_KNOWS = "possibly_knows"
    COMMONLY_KNOWN = "commonly_known"


class EvidenceType(Enum):
    """Types of evidence."""
    DIRECT = "direct"
    CIRCUMSTANTIAL = "circumstantial"
    TESTIMONIAL = "testimonial"
    DOCUMENTARY = "documentary"
    INFERENTIAL = "inferential"


class TruthValue(Enum):
    """Truth values."""
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"
    INCONSISTENT = "inconsistent"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Proposition:
    """A logical proposition."""
    prop_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    truth_value: TruthValue = TruthValue.UNKNOWN
    confidence: float = 0.0
    source: str = ""


@dataclass
class Justification:
    """Justification for a belief."""
    just_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposition_id: str = ""
    justification_type: JustificationType = JustificationType.EMPIRICAL
    supporting_evidence: List[str] = field(default_factory=list)
    strength: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Belief:
    """A belief held by an agent."""
    belief_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposition_id: str = ""
    agent_id: str = ""
    state: EpistemicState = EpistemicState.BELIEVED
    justifications: List[str] = field(default_factory=list)
    degree: float = 0.5
    acquired: datetime = field(default_factory=datetime.now)


@dataclass
class Evidence:
    """Evidence supporting or refuting beliefs."""
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_type: EvidenceType = EvidenceType.DIRECT
    content: str = ""
    reliability: float = 0.5
    source: str = ""
    supports: List[str] = field(default_factory=list)
    refutes: List[str] = field(default_factory=list)


@dataclass
class Agent:
    """An epistemic agent."""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    beliefs: Set[str] = field(default_factory=set)
    knowledge: Set[str] = field(default_factory=set)


@dataclass
class EpistemicFormula:
    """An epistemic formula (modal logic)."""
    formula_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operator: ModalOperator = ModalOperator.KNOWS
    agent_id: str = ""
    proposition_id: str = ""
    nested: Optional[str] = None  # Nested formula ID


# =============================================================================
# PROPOSITION MANAGER
# =============================================================================

class PropositionManager:
    """Manage propositions."""

    def __init__(self):
        self._propositions: Dict[str, Proposition] = {}
        self._by_content: Dict[str, str] = {}

    def create(
        self,
        content: str,
        truth_value: TruthValue = TruthValue.UNKNOWN,
        confidence: float = 0.0,
        source: str = ""
    ) -> Proposition:
        """Create a proposition."""
        # Check if already exists
        if content in self._by_content:
            return self._propositions[self._by_content[content]]

        prop = Proposition(
            content=content,
            truth_value=truth_value,
            confidence=confidence,
            source=source
        )

        self._propositions[prop.prop_id] = prop
        self._by_content[content] = prop.prop_id
        return prop

    def get(self, prop_id: str) -> Optional[Proposition]:
        """Get a proposition."""
        return self._propositions.get(prop_id)

    def get_by_content(self, content: str) -> Optional[Proposition]:
        """Get proposition by content."""
        prop_id = self._by_content.get(content)
        return self._propositions.get(prop_id) if prop_id else None

    def set_truth(
        self,
        prop_id: str,
        truth_value: TruthValue,
        confidence: float = 0.0
    ) -> bool:
        """Set truth value of proposition."""
        prop = self._propositions.get(prop_id)
        if prop:
            prop.truth_value = truth_value
            prop.confidence = confidence
            return True
        return False

    def all_propositions(self) -> List[Proposition]:
        """Get all propositions."""
        return list(self._propositions.values())


# =============================================================================
# BELIEF MANAGER
# =============================================================================

class BeliefManager:
    """Manage beliefs."""

    def __init__(self, prop_manager: PropositionManager):
        self._beliefs: Dict[str, Belief] = {}
        self._by_agent: Dict[str, Set[str]] = defaultdict(set)
        self._by_proposition: Dict[str, Set[str]] = defaultdict(set)
        self._props = prop_manager

    def create_belief(
        self,
        agent_id: str,
        proposition_id: str,
        state: EpistemicState = EpistemicState.BELIEVED,
        degree: float = 0.5
    ) -> Belief:
        """Create a belief."""
        belief = Belief(
            proposition_id=proposition_id,
            agent_id=agent_id,
            state=state,
            degree=degree
        )

        self._beliefs[belief.belief_id] = belief
        self._by_agent[agent_id].add(belief.belief_id)
        self._by_proposition[proposition_id].add(belief.belief_id)

        return belief

    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """Get a belief."""
        return self._beliefs.get(belief_id)

    def get_agent_beliefs(self, agent_id: str) -> List[Belief]:
        """Get all beliefs of an agent."""
        belief_ids = self._by_agent.get(agent_id, set())
        return [self._beliefs[bid] for bid in belief_ids if bid in self._beliefs]

    def update_belief(
        self,
        belief_id: str,
        new_degree: Optional[float] = None,
        new_state: Optional[EpistemicState] = None
    ) -> bool:
        """Update a belief."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False

        if new_degree is not None:
            belief.degree = max(0.0, min(1.0, new_degree))

        if new_state is not None:
            belief.state = new_state

        return True

    def remove_belief(self, belief_id: str) -> bool:
        """Remove a belief."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False

        self._by_agent[belief.agent_id].discard(belief_id)
        self._by_proposition[belief.proposition_id].discard(belief_id)
        del self._beliefs[belief_id]

        return True


# =============================================================================
# JUSTIFICATION MANAGER
# =============================================================================

class JustificationManager:
    """Manage justifications."""

    def __init__(self, belief_manager: BeliefManager):
        self._justifications: Dict[str, Justification] = {}
        self._by_proposition: Dict[str, List[str]] = defaultdict(list)
        self._beliefs = belief_manager

    def create_justification(
        self,
        proposition_id: str,
        justification_type: JustificationType,
        supporting_evidence: Optional[List[str]] = None,
        strength: float = 0.5
    ) -> Justification:
        """Create a justification."""
        justification = Justification(
            proposition_id=proposition_id,
            justification_type=justification_type,
            supporting_evidence=supporting_evidence or [],
            strength=strength
        )

        self._justifications[justification.just_id] = justification
        self._by_proposition[proposition_id].append(justification.just_id)

        return justification

    def get_justification(self, just_id: str) -> Optional[Justification]:
        """Get a justification."""
        return self._justifications.get(just_id)

    def get_justifications_for(self, proposition_id: str) -> List[Justification]:
        """Get all justifications for a proposition."""
        just_ids = self._by_proposition.get(proposition_id, [])
        return [
            self._justifications[jid]
            for jid in just_ids
            if jid in self._justifications
        ]

    def calculate_justified_belief(self, proposition_id: str) -> float:
        """Calculate justified belief degree."""
        justifications = self.get_justifications_for(proposition_id)

        if not justifications:
            return 0.0

        # Combine justification strengths
        total_strength = sum(j.strength for j in justifications)
        max_strength = min(1.0, total_strength)

        return max_strength


# =============================================================================
# EVIDENCE MANAGER
# =============================================================================

class EvidenceManager:
    """Manage evidence."""

    def __init__(self):
        self._evidence: Dict[str, Evidence] = {}
        self._supports: Dict[str, Set[str]] = defaultdict(set)
        self._refutes: Dict[str, Set[str]] = defaultdict(set)

    def create_evidence(
        self,
        evidence_type: EvidenceType,
        content: str,
        reliability: float = 0.5,
        source: str = ""
    ) -> Evidence:
        """Create evidence."""
        evidence = Evidence(
            evidence_type=evidence_type,
            content=content,
            reliability=reliability,
            source=source
        )

        self._evidence[evidence.evidence_id] = evidence
        return evidence

    def add_support(self, evidence_id: str, proposition_id: str) -> bool:
        """Mark evidence as supporting a proposition."""
        evidence = self._evidence.get(evidence_id)
        if not evidence:
            return False

        evidence.supports.append(proposition_id)
        self._supports[proposition_id].add(evidence_id)
        return True

    def add_refutation(self, evidence_id: str, proposition_id: str) -> bool:
        """Mark evidence as refuting a proposition."""
        evidence = self._evidence.get(evidence_id)
        if not evidence:
            return False

        evidence.refutes.append(proposition_id)
        self._refutes[proposition_id].add(evidence_id)
        return True

    def get_supporting_evidence(self, proposition_id: str) -> List[Evidence]:
        """Get evidence supporting a proposition."""
        evidence_ids = self._supports.get(proposition_id, set())
        return [
            self._evidence[eid]
            for eid in evidence_ids
            if eid in self._evidence
        ]

    def get_refuting_evidence(self, proposition_id: str) -> List[Evidence]:
        """Get evidence refuting a proposition."""
        evidence_ids = self._refutes.get(proposition_id, set())
        return [
            self._evidence[eid]
            for eid in evidence_ids
            if eid in self._evidence
        ]

    def calculate_evidence_weight(self, proposition_id: str) -> Tuple[float, float]:
        """Calculate total supporting and refuting evidence weight."""
        supporting = self.get_supporting_evidence(proposition_id)
        refuting = self.get_refuting_evidence(proposition_id)

        support_weight = sum(e.reliability for e in supporting)
        refute_weight = sum(e.reliability for e in refuting)

        return support_weight, refute_weight


# =============================================================================
# BELIEF REVISION ENGINE
# =============================================================================

class BeliefRevisionEngine:
    """AGM-style belief revision."""

    def __init__(
        self,
        prop_manager: PropositionManager,
        belief_manager: BeliefManager
    ):
        self._props = prop_manager
        self._beliefs = belief_manager

    def expand(
        self,
        agent_id: str,
        proposition_id: str,
        degree: float = 0.5
    ) -> Optional[Belief]:
        """Expand belief set (add without checking consistency)."""
        return self._beliefs.create_belief(
            agent_id, proposition_id,
            EpistemicState.BELIEVED, degree
        )

    def contract(
        self,
        agent_id: str,
        proposition_id: str
    ) -> List[str]:
        """Contract belief set (remove belief and dependencies)."""
        removed = []

        beliefs = self._beliefs.get_agent_beliefs(agent_id)
        for belief in beliefs:
            if belief.proposition_id == proposition_id:
                self._beliefs.remove_belief(belief.belief_id)
                removed.append(belief.belief_id)

        return removed

    def revise(
        self,
        agent_id: str,
        proposition_id: str,
        degree: float = 0.5
    ) -> Tuple[List[str], Optional[Belief]]:
        """Revise belief set (contract negation, then expand)."""
        # First check for conflicting beliefs
        removed = []
        prop = self._props.get(proposition_id)

        if prop:
            # Find conflicting beliefs
            beliefs = self._beliefs.get_agent_beliefs(agent_id)
            for belief in beliefs:
                if self._conflicts(belief.proposition_id, proposition_id):
                    self._beliefs.remove_belief(belief.belief_id)
                    removed.append(belief.belief_id)

        # Now expand
        new_belief = self.expand(agent_id, proposition_id, degree)

        return removed, new_belief

    def _conflicts(self, prop1_id: str, prop2_id: str) -> bool:
        """Check if two propositions conflict."""
        p1 = self._props.get(prop1_id)
        p2 = self._props.get(prop2_id)

        if not p1 or not p2:
            return False

        # Simple negation check
        if p1.content.startswith("not ") and p1.content[4:] == p2.content:
            return True
        if p2.content.startswith("not ") and p2.content[4:] == p1.content:
            return True

        return False


# =============================================================================
# KNOWLEDGE BASE
# =============================================================================

class KnowledgeBase:
    """Knowledge base for an agent."""

    def __init__(
        self,
        agent_id: str,
        prop_manager: PropositionManager,
        belief_manager: BeliefManager,
        just_manager: JustificationManager
    ):
        self._agent_id = agent_id
        self._props = prop_manager
        self._beliefs = belief_manager
        self._justifications = just_manager
        self._known_props: Set[str] = set()

    def knows(self, proposition_id: str) -> bool:
        """Check if agent knows a proposition."""
        return proposition_id in self._known_props

    def add_knowledge(
        self,
        proposition_id: str,
        justification_type: JustificationType = JustificationType.EMPIRICAL,
        justification_strength: float = 1.0
    ) -> bool:
        """Add knowledge (justified true belief)."""
        prop = self._props.get(proposition_id)
        if not prop:
            return False

        # Knowledge requires truth
        if prop.truth_value != TruthValue.TRUE:
            return False

        # Create justified belief
        belief = self._beliefs.create_belief(
            self._agent_id,
            proposition_id,
            EpistemicState.KNOWN,
            degree=1.0
        )

        # Add justification
        justification = self._justifications.create_justification(
            proposition_id,
            justification_type,
            strength=justification_strength
        )

        belief.justifications.append(justification.just_id)
        self._known_props.add(proposition_id)

        return True

    def get_knowledge(self) -> List[Proposition]:
        """Get all known propositions."""
        return [
            self._props.get(pid)
            for pid in self._known_props
            if self._props.get(pid)
        ]

    def query(self, content: str) -> Optional[EpistemicState]:
        """Query epistemic state of a proposition."""
        prop = self._props.get_by_content(content)
        if not prop:
            return None

        if prop.prop_id in self._known_props:
            return EpistemicState.KNOWN

        # Check beliefs
        beliefs = self._beliefs.get_agent_beliefs(self._agent_id)
        for belief in beliefs:
            if belief.proposition_id == prop.prop_id:
                return belief.state

        return EpistemicState.UNKNOWN


# =============================================================================
# EPISTEMIC LOGIC
# =============================================================================

class EpistemicLogic:
    """Epistemic modal logic."""

    def __init__(self, prop_manager: PropositionManager):
        self._props = prop_manager
        self._formulas: Dict[str, EpistemicFormula] = {}
        self._knowledge_bases: Dict[str, KnowledgeBase] = {}

    def register_kb(self, agent_id: str, kb: KnowledgeBase) -> None:
        """Register a knowledge base."""
        self._knowledge_bases[agent_id] = kb

    def create_formula(
        self,
        operator: ModalOperator,
        agent_id: str,
        proposition_id: str,
        nested_formula_id: Optional[str] = None
    ) -> EpistemicFormula:
        """Create an epistemic formula."""
        formula = EpistemicFormula(
            operator=operator,
            agent_id=agent_id,
            proposition_id=proposition_id,
            nested=nested_formula_id
        )

        self._formulas[formula.formula_id] = formula
        return formula

    def evaluate(self, formula_id: str) -> TruthValue:
        """Evaluate an epistemic formula."""
        formula = self._formulas.get(formula_id)
        if not formula:
            return TruthValue.UNKNOWN

        kb = self._knowledge_bases.get(formula.agent_id)
        if not kb:
            return TruthValue.UNKNOWN

        if formula.operator == ModalOperator.KNOWS:
            return TruthValue.TRUE if kb.knows(formula.proposition_id) else TruthValue.FALSE

        elif formula.operator == ModalOperator.BELIEVES:
            state = kb.query(self._props.get(formula.proposition_id).content if self._props.get(formula.proposition_id) else "")
            if state in [EpistemicState.KNOWN, EpistemicState.BELIEVED]:
                return TruthValue.TRUE
            return TruthValue.FALSE

        return TruthValue.UNKNOWN

    def knows_that_knows(
        self,
        agent1_id: str,
        agent2_id: str,
        proposition_id: str
    ) -> TruthValue:
        """Check if agent1 knows that agent2 knows proposition."""
        kb2 = self._knowledge_bases.get(agent2_id)
        if not kb2:
            return TruthValue.UNKNOWN

        if kb2.knows(proposition_id):
            # Agent1 would need to know this fact
            kb1 = self._knowledge_bases.get(agent1_id)
            if kb1:
                # Create nested knowledge proposition
                content = f"{agent2_id} knows {proposition_id}"
                nested_prop = self._props.create(content, TruthValue.TRUE)

                if kb1.knows(nested_prop.prop_id):
                    return TruthValue.TRUE

        return TruthValue.FALSE


# =============================================================================
# EPISTEMIC REASONER
# =============================================================================

class EpistemicReasoner:
    """
    Epistemic Reasoner for BAEL.

    Advanced knowledge and belief reasoning.
    """

    def __init__(self):
        self._prop_manager = PropositionManager()
        self._belief_manager = BeliefManager(self._prop_manager)
        self._just_manager = JustificationManager(self._belief_manager)
        self._evidence_manager = EvidenceManager()
        self._revision_engine = BeliefRevisionEngine(
            self._prop_manager, self._belief_manager
        )
        self._logic = EpistemicLogic(self._prop_manager)

        self._agents: Dict[str, Agent] = {}
        self._knowledge_bases: Dict[str, KnowledgeBase] = {}

    # -------------------------------------------------------------------------
    # AGENT MANAGEMENT
    # -------------------------------------------------------------------------

    def create_agent(self, name: str) -> Agent:
        """Create an epistemic agent."""
        agent = Agent(name=name)
        self._agents[agent.agent_id] = agent

        # Create knowledge base
        kb = KnowledgeBase(
            agent.agent_id,
            self._prop_manager,
            self._belief_manager,
            self._just_manager
        )
        self._knowledge_bases[agent.agent_id] = kb
        self._logic.register_kb(agent.agent_id, kb)

        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent."""
        return self._agents.get(agent_id)

    # -------------------------------------------------------------------------
    # PROPOSITIONS
    # -------------------------------------------------------------------------

    def create_proposition(
        self,
        content: str,
        truth_value: TruthValue = TruthValue.UNKNOWN,
        confidence: float = 0.0
    ) -> Proposition:
        """Create a proposition."""
        return self._prop_manager.create(content, truth_value, confidence)

    def set_truth(
        self,
        prop_id: str,
        truth_value: TruthValue,
        confidence: float = 1.0
    ) -> bool:
        """Set truth value of proposition."""
        return self._prop_manager.set_truth(prop_id, truth_value, confidence)

    # -------------------------------------------------------------------------
    # BELIEFS
    # -------------------------------------------------------------------------

    def believe(
        self,
        agent_id: str,
        proposition_id: str,
        degree: float = 0.5
    ) -> Optional[Belief]:
        """Have agent believe a proposition."""
        return self._belief_manager.create_belief(
            agent_id, proposition_id,
            EpistemicState.BELIEVED, degree
        )

    def get_beliefs(self, agent_id: str) -> List[Belief]:
        """Get agent's beliefs."""
        return self._belief_manager.get_agent_beliefs(agent_id)

    def update_belief(
        self,
        belief_id: str,
        new_degree: Optional[float] = None,
        new_state: Optional[EpistemicState] = None
    ) -> bool:
        """Update a belief."""
        return self._belief_manager.update_belief(belief_id, new_degree, new_state)

    # -------------------------------------------------------------------------
    # KNOWLEDGE
    # -------------------------------------------------------------------------

    def knows(self, agent_id: str, proposition_id: str) -> bool:
        """Check if agent knows proposition."""
        kb = self._knowledge_bases.get(agent_id)
        return kb.knows(proposition_id) if kb else False

    def add_knowledge(
        self,
        agent_id: str,
        proposition_id: str,
        justification_type: JustificationType = JustificationType.EMPIRICAL
    ) -> bool:
        """Add knowledge to agent."""
        kb = self._knowledge_bases.get(agent_id)
        if not kb:
            return False
        return kb.add_knowledge(proposition_id, justification_type)

    def get_knowledge(self, agent_id: str) -> List[Proposition]:
        """Get agent's knowledge."""
        kb = self._knowledge_bases.get(agent_id)
        return kb.get_knowledge() if kb else []

    # -------------------------------------------------------------------------
    # EVIDENCE
    # -------------------------------------------------------------------------

    def add_evidence(
        self,
        evidence_type: EvidenceType,
        content: str,
        reliability: float = 0.5,
        source: str = ""
    ) -> Evidence:
        """Add evidence."""
        return self._evidence_manager.create_evidence(
            evidence_type, content, reliability, source
        )

    def evidence_supports(
        self,
        evidence_id: str,
        proposition_id: str
    ) -> bool:
        """Mark evidence as supporting proposition."""
        return self._evidence_manager.add_support(evidence_id, proposition_id)

    def evidence_refutes(
        self,
        evidence_id: str,
        proposition_id: str
    ) -> bool:
        """Mark evidence as refuting proposition."""
        return self._evidence_manager.add_refutation(evidence_id, proposition_id)

    def get_evidence_weight(
        self,
        proposition_id: str
    ) -> Tuple[float, float]:
        """Get supporting and refuting evidence weights."""
        return self._evidence_manager.calculate_evidence_weight(proposition_id)

    # -------------------------------------------------------------------------
    # JUSTIFICATION
    # -------------------------------------------------------------------------

    def justify(
        self,
        proposition_id: str,
        justification_type: JustificationType,
        evidence_ids: Optional[List[str]] = None,
        strength: float = 0.5
    ) -> Justification:
        """Add justification for proposition."""
        return self._just_manager.create_justification(
            proposition_id, justification_type, evidence_ids, strength
        )

    def get_justifications(self, proposition_id: str) -> List[Justification]:
        """Get justifications for proposition."""
        return self._just_manager.get_justifications_for(proposition_id)

    # -------------------------------------------------------------------------
    # BELIEF REVISION
    # -------------------------------------------------------------------------

    def expand_beliefs(
        self,
        agent_id: str,
        proposition_id: str,
        degree: float = 0.5
    ) -> Optional[Belief]:
        """Expand belief set."""
        return self._revision_engine.expand(agent_id, proposition_id, degree)

    def contract_beliefs(
        self,
        agent_id: str,
        proposition_id: str
    ) -> List[str]:
        """Contract belief set."""
        return self._revision_engine.contract(agent_id, proposition_id)

    def revise_beliefs(
        self,
        agent_id: str,
        proposition_id: str,
        degree: float = 0.5
    ) -> Tuple[List[str], Optional[Belief]]:
        """Revise belief set."""
        return self._revision_engine.revise(agent_id, proposition_id, degree)

    # -------------------------------------------------------------------------
    # EPISTEMIC LOGIC
    # -------------------------------------------------------------------------

    def create_epistemic_formula(
        self,
        operator: ModalOperator,
        agent_id: str,
        proposition_id: str
    ) -> EpistemicFormula:
        """Create epistemic formula."""
        return self._logic.create_formula(operator, agent_id, proposition_id)

    def evaluate_formula(self, formula_id: str) -> TruthValue:
        """Evaluate epistemic formula."""
        return self._logic.evaluate(formula_id)

    def query_epistemic_state(
        self,
        agent_id: str,
        content: str
    ) -> Optional[EpistemicState]:
        """Query epistemic state of proposition for agent."""
        kb = self._knowledge_bases.get(agent_id)
        return kb.query(content) if kb else None


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Epistemic Reasoner."""
    print("=" * 70)
    print("BAEL - EPISTEMIC REASONER DEMO")
    print("Advanced Knowledge and Belief Reasoning")
    print("=" * 70)
    print()

    reasoner = EpistemicReasoner()

    # 1. Create Agents
    print("1. CREATE EPISTEMIC AGENTS:")
    print("-" * 40)

    alice = reasoner.create_agent("Alice")
    bob = reasoner.create_agent("Bob")

    print(f"   Agent: {alice.name} (ID: {alice.agent_id[:8]}...)")
    print(f"   Agent: {bob.name} (ID: {bob.agent_id[:8]}...)")
    print()

    # 2. Create Propositions
    print("2. CREATE PROPOSITIONS:")
    print("-" * 40)

    p1 = reasoner.create_proposition(
        "The Earth is round",
        TruthValue.TRUE,
        confidence=1.0
    )

    p2 = reasoner.create_proposition(
        "It is raining",
        TruthValue.UNKNOWN
    )

    p3 = reasoner.create_proposition(
        "Alice is at home",
        TruthValue.TRUE
    )

    print(f"   P1: {p1.content} ({p1.truth_value.value})")
    print(f"   P2: {p2.content} ({p2.truth_value.value})")
    print(f"   P3: {p3.content} ({p3.truth_value.value})")
    print()

    # 3. Add Knowledge
    print("3. ADD KNOWLEDGE:")
    print("-" * 40)

    reasoner.add_knowledge(
        alice.agent_id,
        p1.prop_id,
        JustificationType.EMPIRICAL
    )

    reasoner.add_knowledge(
        alice.agent_id,
        p3.prop_id,
        JustificationType.MEMORY
    )

    print(f"   Alice knows: {p1.content}")
    print(f"   Alice knows: {p3.content}")
    print(f"   Does Alice know P1? {reasoner.knows(alice.agent_id, p1.prop_id)}")
    print(f"   Does Bob know P1? {reasoner.knows(bob.agent_id, p1.prop_id)}")
    print()

    # 4. Add Beliefs
    print("4. ADD BELIEFS:")
    print("-" * 40)

    belief1 = reasoner.believe(alice.agent_id, p2.prop_id, degree=0.7)
    belief2 = reasoner.believe(bob.agent_id, p2.prop_id, degree=0.3)

    print(f"   Alice believes '{p2.content}' with degree {belief1.degree}")
    print(f"   Bob believes '{p2.content}' with degree {belief2.degree}")
    print()

    # 5. Add Evidence
    print("5. ADD EVIDENCE:")
    print("-" * 40)

    evidence1 = reasoner.add_evidence(
        EvidenceType.DIRECT,
        "Dark clouds in the sky",
        reliability=0.6,
        source="observation"
    )

    evidence2 = reasoner.add_evidence(
        EvidenceType.TESTIMONIAL,
        "Weather forecast says rain",
        reliability=0.8,
        source="news"
    )

    reasoner.evidence_supports(evidence1.evidence_id, p2.prop_id)
    reasoner.evidence_supports(evidence2.evidence_id, p2.prop_id)

    support, refute = reasoner.get_evidence_weight(p2.prop_id)

    print(f"   Evidence 1: {evidence1.content} (rel: {evidence1.reliability})")
    print(f"   Evidence 2: {evidence2.content} (rel: {evidence2.reliability})")
    print(f"   Total support weight: {support:.2f}")
    print(f"   Total refute weight: {refute:.2f}")
    print()

    # 6. Add Justification
    print("6. ADD JUSTIFICATION:")
    print("-" * 40)

    just = reasoner.justify(
        p2.prop_id,
        JustificationType.INFERENTIAL,
        [evidence1.evidence_id, evidence2.evidence_id],
        strength=0.75
    )

    print(f"   Justification for '{p2.content}'")
    print(f"   Type: {just.justification_type.value}")
    print(f"   Strength: {just.strength}")
    print(f"   Supporting evidence: {len(just.supporting_evidence)}")
    print()

    # 7. Belief Revision
    print("7. BELIEF REVISION:")
    print("-" * 40)

    # Create conflicting proposition
    p_not_rain = reasoner.create_proposition(
        "not It is raining",
        TruthValue.TRUE
    )

    print(f"   Before revision - Alice's beliefs: {len(reasoner.get_beliefs(alice.agent_id))}")

    removed, new_belief = reasoner.revise_beliefs(
        alice.agent_id,
        p_not_rain.prop_id,
        degree=0.9
    )

    print(f"   Revised with: '{p_not_rain.content}'")
    print(f"   Beliefs removed: {len(removed)}")
    print(f"   After revision - Alice's beliefs: {len(reasoner.get_beliefs(alice.agent_id))}")
    print()

    # 8. Epistemic Logic
    print("8. EPISTEMIC LOGIC:")
    print("-" * 40)

    # K_alice(P1) - Alice knows P1
    formula1 = reasoner.create_epistemic_formula(
        ModalOperator.KNOWS,
        alice.agent_id,
        p1.prop_id
    )

    result1 = reasoner.evaluate_formula(formula1.formula_id)
    print(f"   K_Alice({p1.content[:20]}...): {result1.value}")

    # B_bob(P2) - Bob believes P2
    formula2 = reasoner.create_epistemic_formula(
        ModalOperator.BELIEVES,
        bob.agent_id,
        p2.prop_id
    )

    result2 = reasoner.evaluate_formula(formula2.formula_id)
    print(f"   B_Bob({p2.content}): {result2.value}")
    print()

    # 9. Query Epistemic State
    print("9. QUERY EPISTEMIC STATE:")
    print("-" * 40)

    queries = [
        (alice.agent_id, "The Earth is round"),
        (alice.agent_id, "It is raining"),
        (bob.agent_id, "The Earth is round"),
        (bob.agent_id, "Unknown proposition"),
    ]

    for agent_id, content in queries:
        agent = reasoner.get_agent(agent_id)
        state = reasoner.query_epistemic_state(agent_id, content)
        state_str = state.value if state else "N/A"
        print(f"   {agent.name} -> '{content[:25]}...': {state_str}")
    print()

    # 10. Get Agent Knowledge
    print("10. AGENT KNOWLEDGE SUMMARY:")
    print("-" * 40)

    alice_knowledge = reasoner.get_knowledge(alice.agent_id)
    print(f"   Alice knows {len(alice_knowledge)} propositions:")
    for prop in alice_knowledge:
        if prop:
            print(f"     - {prop.content}")

    bob_knowledge = reasoner.get_knowledge(bob.agent_id)
    print(f"   Bob knows {len(bob_knowledge)} propositions")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Epistemic Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
