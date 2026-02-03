"""
BAEL Council Orchestrator - Multi-Agent Deliberation System

Orchestrates BAEL's council system for complex decision-making:

COUNCIL TYPES:
1. Optimization Council - Improve performance and efficiency
2. Ethics Council - Evaluate ethical implications
3. Strategy Council - Strategic planning and game theory
4. Research Council - Deep investigation and analysis
5. Validation Council - Verify and validate conclusions
6. Innovation Council - Generate creative solutions
7. Risk Council - Assess risks and mitigations

DELIBERATION PHASES:
1. Convocation - Gather council members
2. Analysis - Multi-perspective analysis
3. Proposal - Generate solution proposals
4. Challenge - Devil's advocate challenges
5. Synthesis - Combine best elements
6. Validation - Verify synthesized solution
7. Decision - Vote and reach consensus

This enables sophisticated multi-agent reasoning for complex problems.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger("BAEL.CouncilOrchestrator")


# =============================================================================
# ENUMS
# =============================================================================

class CouncilType(Enum):
    """Types of councils for different decision domains."""
    OPTIMIZATION = "optimization"
    ETHICS = "ethics"
    STRATEGY = "strategy"
    RESEARCH = "research"
    VALIDATION = "validation"
    INNOVATION = "innovation"
    RISK = "risk"
    MASTER = "master"  # Meta-council that coordinates others


class DeliberationPhase(Enum):
    """Phases of council deliberation."""
    CONVOCATION = "convocation"
    ANALYSIS = "analysis"
    PROPOSAL = "proposal"
    CHALLENGE = "challenge"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    DECISION = "decision"
    DOCUMENTATION = "documentation"


class VoteType(Enum):
    """Types of votes."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    CONDITIONAL = "conditional"


class ConsensusType(Enum):
    """Types of consensus requirements."""
    UNANIMOUS = "unanimous"      # 100% agreement
    SUPERMAJORITY = "supermajority"  # 2/3 agreement
    MAJORITY = "majority"        # >50% agreement
    PLURALITY = "plurality"      # Most votes wins


class MemberRole(Enum):
    """Roles council members can take."""
    CHAIR = "chair"              # Leads deliberation
    ADVOCATE = "advocate"        # Argues for proposal
    CRITIC = "critic"            # Challenges proposals
    ANALYST = "analyst"          # Provides analysis
    SYNTHESIZER = "synthesizer"  # Combines perspectives
    OBSERVER = "observer"        # Watches and learns


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CouncilMember:
    """A member of a council."""
    id: str
    name: str
    role: MemberRole
    expertise: List[str]
    voting_weight: float = 1.0
    active: bool = True
    persona_id: Optional[str] = None

    # Performance tracking
    proposals_made: int = 0
    challenges_made: int = 0
    votes_cast: int = 0


@dataclass
class Perspective:
    """A perspective/analysis from a council member."""
    member_id: str
    aspect: str  # What aspect this covers
    analysis: str
    insights: List[str]
    concerns: List[str]
    confidence: float
    supporting_evidence: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Proposal:
    """A proposal from a council member."""
    id: str
    member_id: str
    title: str
    description: str
    solution: Any
    benefits: List[str]
    risks: List[str]
    resources_required: List[str]
    confidence: float
    implementation_steps: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Challenge:
    """A challenge/critique of a proposal."""
    id: str
    member_id: str
    proposal_id: str
    challenge_type: str  # weakness, risk, alternative, assumption
    description: str
    severity: str  # minor, moderate, major, critical
    suggested_mitigation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Vote:
    """A vote from a council member."""
    member_id: str
    vote_type: VoteType
    weight: float
    reasoning: str
    conditions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SynthesizedSolution:
    """Solution synthesized from multiple proposals."""
    id: str
    title: str
    description: str
    source_proposals: List[str]
    combined_benefits: List[str]
    addressed_concerns: List[str]
    remaining_risks: List[str]
    implementation_plan: List[str]
    confidence: float


@dataclass
class CouncilDecision:
    """Final decision from council deliberation."""
    id: str
    council_type: CouncilType
    question: str
    decision: str
    solution: Any
    vote_tally: Dict[str, int]
    consensus_type: ConsensusType
    confidence: float
    reasoning: str
    action_items: List[str]
    dissenting_opinions: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DeliberationSession:
    """A complete deliberation session."""
    id: str
    council_type: CouncilType
    question: str
    context: Dict[str, Any]
    members: List[CouncilMember]
    current_phase: DeliberationPhase
    perspectives: List[Perspective]
    proposals: List[Proposal]
    challenges: List[Challenge]
    votes: List[Vote]
    synthesized: Optional[SynthesizedSolution]
    decision: Optional[CouncilDecision]
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def get_phase_data(self, phase: DeliberationPhase) -> Dict[str, Any]:
        """Get data for a specific phase."""
        if phase == DeliberationPhase.ANALYSIS:
            return {"perspectives": self.perspectives}
        elif phase == DeliberationPhase.PROPOSAL:
            return {"proposals": self.proposals}
        elif phase == DeliberationPhase.CHALLENGE:
            return {"challenges": self.challenges}
        elif phase == DeliberationPhase.DECISION:
            return {"votes": self.votes, "decision": self.decision}
        return {}


# =============================================================================
# COUNCIL TEMPLATES
# =============================================================================

COUNCIL_TEMPLATES = {
    CouncilType.OPTIMIZATION: {
        "name": "Optimization Council",
        "purpose": "Improve performance, efficiency, and resource utilization",
        "default_members": [
            CouncilMember(id="opt-1", name="Efficiency Analyst", role=MemberRole.ANALYST, expertise=["performance", "optimization"]),
            CouncilMember(id="opt-2", name="Resource Manager", role=MemberRole.ANALYST, expertise=["resources", "costs"]),
            CouncilMember(id="opt-3", name="Architecture Expert", role=MemberRole.ADVOCATE, expertise=["architecture", "scaling"]),
            CouncilMember(id="opt-4", name="Trade-off Critic", role=MemberRole.CRITIC, expertise=["trade-offs", "risks"]),
            CouncilMember(id="opt-5", name="Integration Lead", role=MemberRole.SYNTHESIZER, expertise=["integration", "systems"]),
        ],
        "consensus_type": ConsensusType.MAJORITY
    },
    CouncilType.ETHICS: {
        "name": "Ethics Council",
        "purpose": "Evaluate ethical implications and ensure alignment",
        "default_members": [
            CouncilMember(id="eth-1", name="Utilitarian Analyst", role=MemberRole.ANALYST, expertise=["utilitarianism", "consequences"]),
            CouncilMember(id="eth-2", name="Deontologist", role=MemberRole.ANALYST, expertise=["duties", "rights"]),
            CouncilMember(id="eth-3", name="Virtue Ethicist", role=MemberRole.ANALYST, expertise=["character", "virtue"]),
            CouncilMember(id="eth-4", name="Harm Assessor", role=MemberRole.CRITIC, expertise=["harm", "safety"]),
            CouncilMember(id="eth-5", name="Alignment Expert", role=MemberRole.CHAIR, expertise=["alignment", "values"]),
        ],
        "consensus_type": ConsensusType.SUPERMAJORITY
    },
    CouncilType.STRATEGY: {
        "name": "Strategy Council",
        "purpose": "Strategic planning and game-theoretic analysis",
        "default_members": [
            CouncilMember(id="str-1", name="Game Theorist", role=MemberRole.ANALYST, expertise=["game theory", "equilibrium"]),
            CouncilMember(id="str-2", name="Scenario Planner", role=MemberRole.ANALYST, expertise=["scenarios", "futures"]),
            CouncilMember(id="str-3", name="Risk Strategist", role=MemberRole.CRITIC, expertise=["risk", "uncertainty"]),
            CouncilMember(id="str-4", name="Opportunity Scout", role=MemberRole.ADVOCATE, expertise=["opportunities", "innovation"]),
            CouncilMember(id="str-5", name="Integration Strategist", role=MemberRole.SYNTHESIZER, expertise=["integration", "coherence"]),
        ],
        "consensus_type": ConsensusType.MAJORITY
    },
    CouncilType.RESEARCH: {
        "name": "Research Council",
        "purpose": "Deep investigation and evidence gathering",
        "default_members": [
            CouncilMember(id="res-1", name="Primary Researcher", role=MemberRole.ANALYST, expertise=["research", "evidence"]),
            CouncilMember(id="res-2", name="Literature Expert", role=MemberRole.ANALYST, expertise=["literature", "prior work"]),
            CouncilMember(id="res-3", name="Methodology Critic", role=MemberRole.CRITIC, expertise=["methodology", "validity"]),
            CouncilMember(id="res-4", name="Data Analyst", role=MemberRole.ANALYST, expertise=["data", "statistics"]),
            CouncilMember(id="res-5", name="Knowledge Synthesizer", role=MemberRole.SYNTHESIZER, expertise=["synthesis", "integration"]),
        ],
        "consensus_type": ConsensusType.MAJORITY
    },
    CouncilType.INNOVATION: {
        "name": "Innovation Council",
        "purpose": "Generate creative solutions and novel approaches",
        "default_members": [
            CouncilMember(id="inn-1", name="Divergent Thinker", role=MemberRole.ADVOCATE, expertise=["creativity", "divergent"]),
            CouncilMember(id="inn-2", name="Analogist", role=MemberRole.ANALYST, expertise=["analogies", "transfer"]),
            CouncilMember(id="inn-3", name="Constraint Breaker", role=MemberRole.CRITIC, expertise=["constraints", "assumptions"]),
            CouncilMember(id="inn-4", name="Feasibility Checker", role=MemberRole.CRITIC, expertise=["feasibility", "implementation"]),
            CouncilMember(id="inn-5", name="Concept Blender", role=MemberRole.SYNTHESIZER, expertise=["blending", "emergence"]),
        ],
        "consensus_type": ConsensusType.PLURALITY
    },
}


# =============================================================================
# COUNCIL ORCHESTRATOR
# =============================================================================

class CouncilOrchestrator:
    """
    Orchestrates multi-agent council deliberation.

    Manages the full deliberation lifecycle:
    1. Convene appropriate council for the question
    2. Guide through analysis, proposal, challenge phases
    3. Synthesize solutions from multiple proposals
    4. Facilitate voting and consensus building
    5. Document decisions and action items
    """

    def __init__(self):
        self._councils: Dict[CouncilType, Dict[str, Any]] = {}
        self._sessions: Dict[str, DeliberationSession] = {}
        self._initialized = False

        # Metrics
        self._metrics = {
            "sessions_completed": 0,
            "decisions_made": 0,
            "proposals_generated": 0,
            "challenges_raised": 0,
            "consensus_reached": 0,
            "average_confidence": 0
        }

    async def initialize(self) -> None:
        """Initialize all councils from templates."""
        logger.info("Initializing Council Orchestrator...")

        for council_type, template in COUNCIL_TEMPLATES.items():
            self._councils[council_type] = {
                "type": council_type,
                "name": template["name"],
                "purpose": template["purpose"],
                "members": template["default_members"],
                "consensus_type": template["consensus_type"],
                "active_sessions": 0
            }

        self._initialized = True
        logger.info(f"Initialized {len(self._councils)} councils")

    async def convene(
        self,
        council_type: CouncilType,
        question: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Convene a council for deliberation."""
        if not self._initialized:
            await self.initialize()

        council = self._councils.get(council_type)
        if not council:
            raise ValueError(f"Unknown council type: {council_type}")

        session_id = str(uuid4())

        session = DeliberationSession(
            id=session_id,
            council_type=council_type,
            question=question,
            context=context or {},
            members=council["members"].copy(),
            current_phase=DeliberationPhase.CONVOCATION,
            perspectives=[],
            proposals=[],
            challenges=[],
            votes=[],
            synthesized=None,
            decision=None
        )

        self._sessions[session_id] = session
        council["active_sessions"] += 1

        logger.info(f"Convened {council_type.value} council for: {question[:50]}...")

        return session_id

    async def deliberate(
        self,
        session_id: str,
        auto_advance: bool = True
    ) -> CouncilDecision:
        """
        Run full deliberation process.

        If auto_advance is True, automatically moves through all phases.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Unknown session: {session_id}")

        phases = [
            (DeliberationPhase.ANALYSIS, self._run_analysis),
            (DeliberationPhase.PROPOSAL, self._run_proposals),
            (DeliberationPhase.CHALLENGE, self._run_challenges),
            (DeliberationPhase.SYNTHESIS, self._run_synthesis),
            (DeliberationPhase.VALIDATION, self._run_validation),
            (DeliberationPhase.DECISION, self._run_decision),
            (DeliberationPhase.DOCUMENTATION, self._run_documentation),
        ]

        for phase, phase_handler in phases:
            session.current_phase = phase
            await phase_handler(session)

            if not auto_advance:
                break

        session.completed_at = datetime.now()
        self._metrics["sessions_completed"] += 1

        return session.decision

    async def _run_analysis(self, session: DeliberationSession) -> None:
        """Run analysis phase - gather perspectives from all members."""
        logger.debug(f"Session {session.id}: Running analysis phase")

        for member in session.members:
            if member.role in [MemberRole.ANALYST, MemberRole.CHAIR]:
                perspective = await self._generate_perspective(member, session)
                session.perspectives.append(perspective)

        logger.debug(f"Generated {len(session.perspectives)} perspectives")

    async def _run_proposals(self, session: DeliberationSession) -> None:
        """Run proposal phase - generate solution proposals."""
        logger.debug(f"Session {session.id}: Running proposal phase")

        for member in session.members:
            if member.role in [MemberRole.ADVOCATE, MemberRole.SYNTHESIZER, MemberRole.CHAIR]:
                proposal = await self._generate_proposal(member, session)
                session.proposals.append(proposal)
                member.proposals_made += 1
                self._metrics["proposals_generated"] += 1

        logger.debug(f"Generated {len(session.proposals)} proposals")

    async def _run_challenges(self, session: DeliberationSession) -> None:
        """Run challenge phase - critique proposals."""
        logger.debug(f"Session {session.id}: Running challenge phase")

        critics = [m for m in session.members if m.role == MemberRole.CRITIC]

        for proposal in session.proposals:
            for critic in critics:
                challenge = await self._generate_challenge(critic, proposal, session)
                session.challenges.append(challenge)
                critic.challenges_made += 1
                self._metrics["challenges_raised"] += 1

        logger.debug(f"Generated {len(session.challenges)} challenges")

    async def _run_synthesis(self, session: DeliberationSession) -> None:
        """Run synthesis phase - combine best elements of proposals."""
        logger.debug(f"Session {session.id}: Running synthesis phase")

        synthesizers = [m for m in session.members if m.role == MemberRole.SYNTHESIZER]

        if synthesizers:
            session.synthesized = await self._synthesize_proposals(
                synthesizers[0],
                session.proposals,
                session.challenges,
                session
            )
        else:
            # Use best proposal as synthesis
            if session.proposals:
                best = max(session.proposals, key=lambda p: p.confidence)
                session.synthesized = SynthesizedSolution(
                    id=str(uuid4()),
                    title=best.title,
                    description=best.description,
                    source_proposals=[best.id],
                    combined_benefits=best.benefits,
                    addressed_concerns=[],
                    remaining_risks=best.risks,
                    implementation_plan=best.implementation_steps,
                    confidence=best.confidence
                )

    async def _run_validation(self, session: DeliberationSession) -> None:
        """Run validation phase - verify synthesized solution."""
        logger.debug(f"Session {session.id}: Running validation phase")

        # In production, would run validation checks
        # For now, just log
        if session.synthesized:
            logger.debug(f"Validating synthesized solution: {session.synthesized.title}")

    async def _run_decision(self, session: DeliberationSession) -> None:
        """Run decision phase - vote and reach consensus."""
        logger.debug(f"Session {session.id}: Running decision phase")

        # Collect votes
        for member in session.members:
            vote = await self._cast_vote(member, session)
            session.votes.append(vote)
            member.votes_cast += 1

        # Tally votes
        tally = {v.value: 0 for v in VoteType}
        weighted_tally = {v.value: 0.0 for v in VoteType}

        for vote in session.votes:
            tally[vote.vote_type.value] += 1
            weighted_tally[vote.vote_type.value] += vote.weight

        # Determine outcome
        total_weight = sum(weighted_tally.values())
        approve_weight = weighted_tally[VoteType.APPROVE.value]

        council = self._councils[session.council_type]
        consensus_type = council["consensus_type"]

        if consensus_type == ConsensusType.UNANIMOUS:
            approved = tally[VoteType.REJECT.value] == 0
        elif consensus_type == ConsensusType.SUPERMAJORITY:
            approved = (approve_weight / total_weight) >= 0.67 if total_weight > 0 else False
        elif consensus_type == ConsensusType.MAJORITY:
            approved = (approve_weight / total_weight) > 0.5 if total_weight > 0 else False
        else:  # PLURALITY
            approved = approve_weight >= weighted_tally[VoteType.REJECT.value]

        # Create decision
        session.decision = CouncilDecision(
            id=str(uuid4()),
            council_type=session.council_type,
            question=session.question,
            decision="APPROVED" if approved else "REJECTED",
            solution=session.synthesized.description if session.synthesized else None,
            vote_tally=tally,
            consensus_type=consensus_type,
            confidence=session.synthesized.confidence if session.synthesized else 0.5,
            reasoning=self._generate_reasoning(session, approved),
            action_items=session.synthesized.implementation_plan if session.synthesized else [],
            dissenting_opinions=[v.reasoning for v in session.votes if v.vote_type == VoteType.REJECT]
        )

        if approved:
            self._metrics["consensus_reached"] += 1

        self._metrics["decisions_made"] += 1
        logger.info(f"Council decision: {session.decision.decision}")

    async def _run_documentation(self, session: DeliberationSession) -> None:
        """Run documentation phase - record deliberation for learning."""
        logger.debug(f"Session {session.id}: Running documentation phase")
        # In production, would persist to memory/database

    async def _generate_perspective(
        self,
        member: CouncilMember,
        session: DeliberationSession
    ) -> Perspective:
        """Generate a perspective from a council member."""
        # In production, would use LLM with member's persona
        return Perspective(
            member_id=member.id,
            aspect=member.expertise[0] if member.expertise else "general",
            analysis=f"Analysis from {member.name} regarding: {session.question}",
            insights=[f"Insight about {e}" for e in member.expertise[:2]],
            concerns=[f"Concern about {session.council_type.value}"],
            confidence=0.75
        )

    async def _generate_proposal(
        self,
        member: CouncilMember,
        session: DeliberationSession
    ) -> Proposal:
        """Generate a proposal from a council member."""
        return Proposal(
            id=str(uuid4()),
            member_id=member.id,
            title=f"Proposal from {member.name}",
            description=f"Solution to: {session.question}",
            solution={"approach": member.expertise[0] if member.expertise else "general"},
            benefits=["Benefit 1", "Benefit 2"],
            risks=["Risk 1"],
            resources_required=["Resource 1"],
            confidence=0.7,
            implementation_steps=["Step 1", "Step 2", "Step 3"]
        )

    async def _generate_challenge(
        self,
        member: CouncilMember,
        proposal: Proposal,
        session: DeliberationSession
    ) -> Challenge:
        """Generate a challenge from a critic."""
        return Challenge(
            id=str(uuid4()),
            member_id=member.id,
            proposal_id=proposal.id,
            challenge_type="weakness",
            description=f"Challenge to {proposal.title}",
            severity="moderate",
            suggested_mitigation="Consider alternative approach"
        )

    async def _synthesize_proposals(
        self,
        member: CouncilMember,
        proposals: List[Proposal],
        challenges: List[Challenge],
        session: DeliberationSession
    ) -> SynthesizedSolution:
        """Synthesize proposals into unified solution."""
        # Combine benefits from all proposals
        all_benefits = []
        for p in proposals:
            all_benefits.extend(p.benefits)

        # Get unique concerns from challenges
        all_concerns = list(set(c.description for c in challenges))

        return SynthesizedSolution(
            id=str(uuid4()),
            title="Synthesized Solution",
            description=f"Combined solution addressing: {session.question}",
            source_proposals=[p.id for p in proposals],
            combined_benefits=list(set(all_benefits)),
            addressed_concerns=all_concerns[:3],
            remaining_risks=["Residual risk"],
            implementation_plan=["Step 1", "Step 2", "Step 3"],
            confidence=0.8
        )

    async def _cast_vote(
        self,
        member: CouncilMember,
        session: DeliberationSession
    ) -> Vote:
        """Cast a vote from a council member."""
        # In production, would use LLM with member's perspective
        return Vote(
            member_id=member.id,
            vote_type=VoteType.APPROVE,  # Would be determined by deliberation
            weight=member.voting_weight,
            reasoning=f"Vote reasoning from {member.name}"
        )

    def _generate_reasoning(
        self,
        session: DeliberationSession,
        approved: bool
    ) -> str:
        """Generate reasoning for the decision."""
        if approved:
            return f"The council approved the solution based on {len(session.perspectives)} perspectives, {len(session.proposals)} proposals, addressing {len(session.challenges)} challenges."
        else:
            return f"The council rejected the solution due to unresolved challenges."

    def get_session(self, session_id: str) -> Optional[DeliberationSession]:
        """Get a deliberation session by ID."""
        return self._sessions.get(session_id)

    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        return {
            **self._metrics,
            "active_sessions": sum(c["active_sessions"] for c in self._councils.values()),
            "councils": {ct.value: c["active_sessions"] for ct, c in self._councils.items()}
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate Council Orchestrator capabilities."""
    orchestrator = CouncilOrchestrator()
    await orchestrator.initialize()

    # Convene ethics council
    session_id = await orchestrator.convene(
        CouncilType.ETHICS,
        "Should the AI system be allowed to make autonomous decisions about user data?",
        context={"domain": "privacy", "risk_level": "high"}
    )

    print(f"Convened session: {session_id}")

    # Run deliberation
    decision = await orchestrator.deliberate(session_id)

    print(f"\n{'='*60}")
    print(f"Council: {decision.council_type.value}")
    print(f"Question: {decision.question}")
    print(f"Decision: {decision.decision}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Consensus: {decision.consensus_type.value}")
    print(f"Vote Tally: {decision.vote_tally}")
    print(f"Reasoning: {decision.reasoning}")
    print(f"Action Items: {decision.action_items}")

    print(f"\nMetrics: {orchestrator.get_metrics()}")


if __name__ == "__main__":
    asyncio.run(demo())
