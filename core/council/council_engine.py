#!/usr/bin/env python3
"""
BAEL - Council Engine
Multi-agent council orchestration and deliberation.

Features:
- Council formation
- Voting mechanisms
- Consensus building
- Role assignment
- Collective decision making
"""

import asyncio
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
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

class CouncilType(Enum):
    """Council types."""
    DEMOCRATIC = "democratic"
    HIERARCHICAL = "hierarchical"
    CONSENSUS = "consensus"
    EXPERT = "expert"
    ROTATING = "rotating"


class VotingMethod(Enum):
    """Voting methods."""
    MAJORITY = "majority"
    SUPERMAJORITY = "supermajority"
    UNANIMOUS = "unanimous"
    PLURALITY = "plurality"
    RANKED_CHOICE = "ranked_choice"
    WEIGHTED = "weighted"


class MemberRole(Enum):
    """Council member roles."""
    LEADER = "leader"
    EXPERT = "expert"
    VOTER = "voter"
    OBSERVER = "observer"
    MEDIATOR = "mediator"


class SessionStatus(Enum):
    """Council session status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VOTING = "voting"
    CONCLUDED = "concluded"
    CANCELLED = "cancelled"


class ProposalStatus(Enum):
    """Proposal status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DecisionType(Enum):
    """Decision types."""
    POLICY = "policy"
    ACTION = "action"
    ALLOCATION = "allocation"
    ELECTION = "election"
    RESOLUTION = "resolution"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CouncilMember:
    """Council member."""
    member_id: str = ""
    name: str = ""
    role: MemberRole = MemberRole.VOTER
    expertise: List[str] = field(default_factory=list)
    voting_weight: float = 1.0
    joined_at: datetime = field(default_factory=datetime.now)
    active: bool = True

    def __post_init__(self):
        if not self.member_id:
            self.member_id = str(uuid.uuid4())[:8]


@dataclass
class Vote:
    """Individual vote."""
    vote_id: str = ""
    member_id: str = ""
    proposal_id: str = ""
    choice: str = ""
    weight: float = 1.0
    reasoning: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.vote_id:
            self.vote_id = str(uuid.uuid4())[:8]


@dataclass
class Proposal:
    """Council proposal."""
    proposal_id: str = ""
    title: str = ""
    description: str = ""
    proposer_id: str = ""
    decision_type: DecisionType = DecisionType.ACTION
    options: List[str] = field(default_factory=list)
    status: ProposalStatus = ProposalStatus.DRAFT
    votes: List[Vote] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None

    def __post_init__(self):
        if not self.proposal_id:
            self.proposal_id = str(uuid.uuid4())[:8]
        if not self.options:
            self.options = ["approve", "reject", "abstain"]


@dataclass
class Deliberation:
    """Council deliberation."""
    deliberation_id: str = ""
    topic: str = ""
    participants: List[str] = field(default_factory=list)
    contributions: List[Tuple[str, str, datetime]] = field(default_factory=list)
    summary: Optional[str] = None

    def __post_init__(self):
        if not self.deliberation_id:
            self.deliberation_id = str(uuid.uuid4())[:8]

    def add_contribution(self, member_id: str, content: str) -> None:
        self.contributions.append((member_id, content, datetime.now()))


@dataclass
class CouncilSession:
    """Council session."""
    session_id: str = ""
    council_id: str = ""
    agenda: List[str] = field(default_factory=list)
    status: SessionStatus = SessionStatus.PENDING
    proposals: List[Proposal] = field(default_factory=list)
    deliberations: List[Deliberation] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())[:8]


@dataclass
class CouncilConfig:
    """Council configuration."""
    council_id: str = ""
    name: str = ""
    council_type: CouncilType = CouncilType.DEMOCRATIC
    voting_method: VotingMethod = VotingMethod.MAJORITY
    quorum: float = 0.5
    supermajority_threshold: float = 0.67
    max_members: int = 10

    def __post_init__(self):
        if not self.council_id:
            self.council_id = str(uuid.uuid4())[:8]


@dataclass
class CouncilStats:
    """Council statistics."""
    total_sessions: int = 0
    proposals_submitted: int = 0
    proposals_approved: int = 0
    proposals_rejected: int = 0
    total_votes: int = 0
    avg_participation: float = 0.0
    by_decision_type: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# VOTING SYSTEMS
# =============================================================================

class BaseVotingSystem(ABC):
    """Abstract voting system."""

    @property
    @abstractmethod
    def method(self) -> VotingMethod:
        """Get voting method."""
        pass

    @abstractmethod
    def tally(
        self,
        votes: List[Vote],
        options: List[str],
        threshold: float = 0.5
    ) -> Tuple[str, Dict[str, float]]:
        """Tally votes and return winner."""
        pass


class MajorityVoting(BaseVotingSystem):
    """Simple majority voting."""

    @property
    def method(self) -> VotingMethod:
        return VotingMethod.MAJORITY

    def tally(
        self,
        votes: List[Vote],
        options: List[str],
        threshold: float = 0.5
    ) -> Tuple[str, Dict[str, float]]:
        counts = Counter(v.choice for v in votes)
        total = len(votes)

        percentages = {
            opt: counts.get(opt, 0) / total if total > 0 else 0
            for opt in options
        }

        winner = max(options, key=lambda o: counts.get(o, 0))

        if percentages.get(winner, 0) > threshold:
            return winner, percentages

        return "no_decision", percentages


class SupermajorityVoting(BaseVotingSystem):
    """Supermajority voting (2/3 or custom)."""

    @property
    def method(self) -> VotingMethod:
        return VotingMethod.SUPERMAJORITY

    def tally(
        self,
        votes: List[Vote],
        options: List[str],
        threshold: float = 0.67
    ) -> Tuple[str, Dict[str, float]]:
        counts = Counter(v.choice for v in votes)
        total = len(votes)

        percentages = {
            opt: counts.get(opt, 0) / total if total > 0 else 0
            for opt in options
        }

        for opt in options:
            if percentages.get(opt, 0) >= threshold:
                return opt, percentages

        return "no_decision", percentages


class UnanimousVoting(BaseVotingSystem):
    """Unanimous voting."""

    @property
    def method(self) -> VotingMethod:
        return VotingMethod.UNANIMOUS

    def tally(
        self,
        votes: List[Vote],
        options: List[str],
        threshold: float = 1.0
    ) -> Tuple[str, Dict[str, float]]:
        choices = set(v.choice for v in votes)
        total = len(votes)

        percentages = {
            opt: (len(votes) if opt in choices and len(choices) == 1 else 0) / total
            if total > 0 else 0
            for opt in options
        }

        if len(choices) == 1:
            return list(choices)[0], percentages

        return "no_decision", percentages


class WeightedVoting(BaseVotingSystem):
    """Weighted voting based on member weights."""

    @property
    def method(self) -> VotingMethod:
        return VotingMethod.WEIGHTED

    def tally(
        self,
        votes: List[Vote],
        options: List[str],
        threshold: float = 0.5
    ) -> Tuple[str, Dict[str, float]]:
        weighted_counts: Dict[str, float] = defaultdict(float)
        total_weight = sum(v.weight for v in votes)

        for vote in votes:
            weighted_counts[vote.choice] += vote.weight

        percentages = {
            opt: weighted_counts.get(opt, 0) / total_weight if total_weight > 0 else 0
            for opt in options
        }

        winner = max(options, key=lambda o: weighted_counts.get(o, 0))

        if percentages.get(winner, 0) > threshold:
            return winner, percentages

        return "no_decision", percentages


class RankedChoiceVoting(BaseVotingSystem):
    """Ranked choice / instant runoff voting."""

    @property
    def method(self) -> VotingMethod:
        return VotingMethod.RANKED_CHOICE

    def tally(
        self,
        votes: List[Vote],
        options: List[str],
        threshold: float = 0.5
    ) -> Tuple[str, Dict[str, float]]:
        counts = Counter(v.choice for v in votes)
        total = len(votes)

        percentages = {
            opt: counts.get(opt, 0) / total if total > 0 else 0
            for opt in options
        }

        winner = max(options, key=lambda o: counts.get(o, 0))

        return winner, percentages


# =============================================================================
# COUNCIL
# =============================================================================

class Council:
    """Council for collective decision making."""

    def __init__(self, config: CouncilConfig):
        self._config = config
        self._members: Dict[str, CouncilMember] = {}
        self._sessions: List[CouncilSession] = []
        self._current_session: Optional[CouncilSession] = None

        self._voting_systems: Dict[VotingMethod, BaseVotingSystem] = {
            VotingMethod.MAJORITY: MajorityVoting(),
            VotingMethod.SUPERMAJORITY: SupermajorityVoting(),
            VotingMethod.UNANIMOUS: UnanimousVoting(),
            VotingMethod.WEIGHTED: WeightedVoting(),
            VotingMethod.RANKED_CHOICE: RankedChoiceVoting()
        }

    @property
    def council_id(self) -> str:
        return self._config.council_id

    @property
    def name(self) -> str:
        return self._config.name

    def add_member(
        self,
        name: str,
        role: MemberRole = MemberRole.VOTER,
        expertise: Optional[List[str]] = None,
        weight: float = 1.0
    ) -> CouncilMember:
        """Add a member to the council."""
        if len(self._members) >= self._config.max_members:
            raise ValueError("Council at maximum capacity")

        member = CouncilMember(
            name=name,
            role=role,
            expertise=expertise or [],
            voting_weight=weight
        )

        self._members[member.member_id] = member

        return member

    def remove_member(self, member_id: str) -> bool:
        """Remove a member."""
        if member_id in self._members:
            self._members[member_id].active = False
            return True
        return False

    def get_member(self, member_id: str) -> Optional[CouncilMember]:
        """Get a member."""
        return self._members.get(member_id)

    def list_members(
        self,
        active_only: bool = True
    ) -> List[CouncilMember]:
        """List council members."""
        members = list(self._members.values())

        if active_only:
            members = [m for m in members if m.active]

        return members

    def start_session(self, agenda: Optional[List[str]] = None) -> CouncilSession:
        """Start a new session."""
        session = CouncilSession(
            council_id=self.council_id,
            agenda=agenda or [],
            status=SessionStatus.IN_PROGRESS,
            started_at=datetime.now()
        )

        self._sessions.append(session)
        self._current_session = session

        return session

    def end_session(self) -> Optional[CouncilSession]:
        """End current session."""
        if self._current_session:
            self._current_session.status = SessionStatus.CONCLUDED
            self._current_session.ended_at = datetime.now()

            session = self._current_session
            self._current_session = None

            return session

        return None

    def submit_proposal(
        self,
        title: str,
        description: str,
        proposer_id: str,
        decision_type: DecisionType = DecisionType.ACTION,
        options: Optional[List[str]] = None
    ) -> Optional[Proposal]:
        """Submit a proposal."""
        if not self._current_session:
            return None

        proposal = Proposal(
            title=title,
            description=description,
            proposer_id=proposer_id,
            decision_type=decision_type,
            options=options or ["approve", "reject", "abstain"],
            status=ProposalStatus.SUBMITTED
        )

        self._current_session.proposals.append(proposal)

        return proposal

    def cast_vote(
        self,
        proposal_id: str,
        member_id: str,
        choice: str,
        reasoning: Optional[str] = None
    ) -> Optional[Vote]:
        """Cast a vote on a proposal."""
        if not self._current_session:
            return None

        proposal = None
        for p in self._current_session.proposals:
            if p.proposal_id == proposal_id:
                proposal = p
                break

        if not proposal:
            return None

        member = self._members.get(member_id)
        if not member or not member.active:
            return None

        if member.role == MemberRole.OBSERVER:
            return None

        for existing in proposal.votes:
            if existing.member_id == member_id:
                return None

        if choice not in proposal.options:
            return None

        vote = Vote(
            member_id=member_id,
            proposal_id=proposal_id,
            choice=choice,
            weight=member.voting_weight,
            reasoning=reasoning
        )

        proposal.votes.append(vote)
        proposal.status = ProposalStatus.VOTING

        return vote

    def tally_votes(
        self,
        proposal_id: str
    ) -> Tuple[str, Dict[str, float]]:
        """Tally votes for a proposal."""
        if not self._current_session:
            return "no_session", {}

        proposal = None
        for p in self._current_session.proposals:
            if p.proposal_id == proposal_id:
                proposal = p
                break

        if not proposal:
            return "not_found", {}

        active_members = [m for m in self._members.values() if m.active and m.role != MemberRole.OBSERVER]
        quorum = self._config.quorum

        if len(proposal.votes) / len(active_members) < quorum:
            return "no_quorum", {}

        voting_system = self._voting_systems.get(
            self._config.voting_method,
            MajorityVoting()
        )

        threshold = (
            self._config.supermajority_threshold
            if self._config.voting_method == VotingMethod.SUPERMAJORITY
            else 0.5
        )

        winner, percentages = voting_system.tally(
            proposal.votes,
            proposal.options,
            threshold
        )

        if winner != "no_decision":
            proposal.status = (
                ProposalStatus.APPROVED if winner == "approve"
                else ProposalStatus.REJECTED
            )

        return winner, percentages

    def start_deliberation(
        self,
        topic: str,
        participants: Optional[List[str]] = None
    ) -> Optional[Deliberation]:
        """Start a deliberation."""
        if not self._current_session:
            return None

        if participants is None:
            participants = [m.member_id for m in self._members.values() if m.active]

        deliberation = Deliberation(
            topic=topic,
            participants=participants
        )

        self._current_session.deliberations.append(deliberation)

        return deliberation

    def contribute(
        self,
        deliberation_id: str,
        member_id: str,
        content: str
    ) -> bool:
        """Add a contribution to deliberation."""
        if not self._current_session:
            return False

        for delib in self._current_session.deliberations:
            if delib.deliberation_id == deliberation_id:
                if member_id in delib.participants:
                    delib.add_contribution(member_id, content)
                    return True

        return False

    def record_decision(
        self,
        proposal_id: str,
        decision: str,
        notes: Optional[str] = None
    ) -> None:
        """Record a council decision."""
        if self._current_session:
            self._current_session.decisions.append({
                "proposal_id": proposal_id,
                "decision": decision,
                "notes": notes,
                "timestamp": datetime.now().isoformat()
            })

    def get_session_summary(self) -> Optional[Dict[str, Any]]:
        """Get current session summary."""
        if not self._current_session:
            return None

        return {
            "session_id": self._current_session.session_id,
            "status": self._current_session.status.value,
            "proposals": len(self._current_session.proposals),
            "deliberations": len(self._current_session.deliberations),
            "decisions": len(self._current_session.decisions),
            "agenda": self._current_session.agenda
        }


# =============================================================================
# COUNCIL ENGINE
# =============================================================================

class CouncilEngine:
    """
    Council Engine for BAEL.

    Multi-agent council orchestration.
    """

    def __init__(self):
        self._councils: Dict[str, Council] = {}
        self._stats = CouncilStats()

    def create_council(
        self,
        name: str,
        council_type: CouncilType = CouncilType.DEMOCRATIC,
        voting_method: VotingMethod = VotingMethod.MAJORITY,
        quorum: float = 0.5,
        max_members: int = 10
    ) -> Council:
        """Create a new council."""
        config = CouncilConfig(
            name=name,
            council_type=council_type,
            voting_method=voting_method,
            quorum=quorum,
            max_members=max_members
        )

        council = Council(config)
        self._councils[council.council_id] = council

        return council

    def get_council(self, council_id: str) -> Optional[Council]:
        """Get a council."""
        return self._councils.get(council_id)

    def list_councils(self) -> List[Council]:
        """List all councils."""
        return list(self._councils.values())

    async def run_session(
        self,
        council_id: str,
        agenda: List[str],
        proposals: List[Dict[str, Any]],
        simulate_votes: bool = True
    ) -> Optional[CouncilSession]:
        """Run a complete council session."""
        council = self._councils.get(council_id)
        if not council:
            return None

        session = council.start_session(agenda)
        self._stats.total_sessions += 1

        for prop_data in proposals:
            members = council.list_members()
            if not members:
                continue

            proposer = members[0]

            proposal = council.submit_proposal(
                title=prop_data.get("title", "Untitled"),
                description=prop_data.get("description", ""),
                proposer_id=proposer.member_id,
                decision_type=prop_data.get("type", DecisionType.ACTION),
                options=prop_data.get("options")
            )

            if proposal:
                self._stats.proposals_submitted += 1

                if simulate_votes:
                    for member in members:
                        if member.role != MemberRole.OBSERVER:
                            choice = random.choice(proposal.options)
                            council.cast_vote(
                                proposal.proposal_id,
                                member.member_id,
                                choice
                            )
                            self._stats.total_votes += 1

                    winner, _ = council.tally_votes(proposal.proposal_id)

                    if winner == "approve":
                        self._stats.proposals_approved += 1
                    elif winner == "reject":
                        self._stats.proposals_rejected += 1

                    council.record_decision(
                        proposal.proposal_id,
                        winner
                    )

        council.end_session()

        return session

    async def deliberate(
        self,
        council_id: str,
        topic: str,
        contributions: List[Tuple[str, str]]
    ) -> Optional[Deliberation]:
        """Run a deliberation."""
        council = self._councils.get(council_id)
        if not council:
            return None

        if not council._current_session:
            council.start_session([topic])

        members = council.list_members()

        deliberation = council.start_deliberation(
            topic=topic,
            participants=[m.member_id for m in members]
        )

        if deliberation:
            for member_idx, content in contributions:
                if isinstance(member_idx, int) and member_idx < len(members):
                    council.contribute(
                        deliberation.deliberation_id,
                        members[member_idx].member_id,
                        content
                    )
                elif isinstance(member_idx, str):
                    council.contribute(
                        deliberation.deliberation_id,
                        member_idx,
                        content
                    )

        return deliberation

    async def reach_consensus(
        self,
        council_id: str,
        proposal_title: str,
        description: str
    ) -> Tuple[str, float]:
        """Attempt to reach consensus on a proposal."""
        council = self._councils.get(council_id)
        if not council:
            return "no_council", 0.0

        if not council._current_session:
            council.start_session([proposal_title])

        members = council.list_members()
        if not members:
            return "no_members", 0.0

        proposal = council.submit_proposal(
            title=proposal_title,
            description=description,
            proposer_id=members[0].member_id,
            options=["approve", "reject", "abstain"]
        )

        if not proposal:
            return "proposal_failed", 0.0

        self._stats.proposals_submitted += 1

        approve_prob = 0.7

        for member in members:
            if member.role != MemberRole.OBSERVER:
                if random.random() < approve_prob:
                    choice = "approve"
                elif random.random() < 0.2:
                    choice = "abstain"
                else:
                    choice = "reject"

                council.cast_vote(
                    proposal.proposal_id,
                    member.member_id,
                    choice
                )
                self._stats.total_votes += 1

        winner, percentages = council.tally_votes(proposal.proposal_id)

        if winner == "approve":
            self._stats.proposals_approved += 1
        elif winner == "reject":
            self._stats.proposals_rejected += 1

        consensus_level = percentages.get(winner, 0)

        return winner, consensus_level

    def get_council_stats(self, council_id: str) -> Optional[Dict[str, Any]]:
        """Get stats for a council."""
        council = self._councils.get(council_id)
        if not council:
            return None

        sessions = council._sessions

        return {
            "council_id": council_id,
            "name": council.name,
            "members": len(council.list_members()),
            "total_sessions": len(sessions),
            "total_proposals": sum(len(s.proposals) for s in sessions),
            "total_decisions": sum(len(s.decisions) for s in sessions)
        }

    @property
    def stats(self) -> CouncilStats:
        """Get engine statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_councils": len(self._councils),
            "total_sessions": self._stats.total_sessions,
            "proposals": {
                "submitted": self._stats.proposals_submitted,
                "approved": self._stats.proposals_approved,
                "rejected": self._stats.proposals_rejected
            },
            "total_votes": self._stats.total_votes,
            "approval_rate": (
                self._stats.proposals_approved / self._stats.proposals_submitted
                if self._stats.proposals_submitted > 0 else 0
            )
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Council Engine."""
    print("=" * 70)
    print("BAEL - COUNCIL ENGINE DEMO")
    print("Multi-Agent Council Orchestration")
    print("=" * 70)
    print()

    engine = CouncilEngine()

    # 1. Create Council
    print("1. CREATE COUNCIL:")
    print("-" * 40)

    council = engine.create_council(
        name="Strategic Council",
        council_type=CouncilType.DEMOCRATIC,
        voting_method=VotingMethod.MAJORITY,
        quorum=0.5,
        max_members=7
    )

    print(f"   Created: {council.name}")
    print(f"   ID: {council.council_id}")
    print()

    # 2. Add Members
    print("2. ADD MEMBERS:")
    print("-" * 40)

    leader = council.add_member("Alpha", MemberRole.LEADER, ["strategy"], 2.0)
    expert1 = council.add_member("Beta", MemberRole.EXPERT, ["tech"], 1.5)
    expert2 = council.add_member("Gamma", MemberRole.EXPERT, ["data"], 1.5)
    voter1 = council.add_member("Delta", MemberRole.VOTER, [], 1.0)
    voter2 = council.add_member("Epsilon", MemberRole.VOTER, [], 1.0)

    members = council.list_members()
    for m in members:
        print(f"   {m.name}: {m.role.value} (weight: {m.voting_weight})")
    print()

    # 3. Start Session
    print("3. START SESSION:")
    print("-" * 40)

    session = council.start_session([
        "Review Q4 Strategy",
        "Approve Resource Allocation",
        "Technical Direction Vote"
    ])

    print(f"   Session ID: {session.session_id}")
    print(f"   Agenda items: {len(session.agenda)}")
    print()

    # 4. Submit Proposal
    print("4. SUBMIT PROPOSAL:")
    print("-" * 40)

    proposal = council.submit_proposal(
        title="Increase Compute Budget",
        description="Proposal to increase compute allocation by 50%",
        proposer_id=leader.member_id,
        decision_type=DecisionType.ALLOCATION,
        options=["approve", "reject", "defer"]
    )

    print(f"   Title: {proposal.title}")
    print(f"   Options: {proposal.options}")
    print()

    # 5. Cast Votes
    print("5. CAST VOTES:")
    print("-" * 40)

    votes = [
        (leader.member_id, "approve"),
        (expert1.member_id, "approve"),
        (expert2.member_id, "approve"),
        (voter1.member_id, "reject"),
        (voter2.member_id, "defer")
    ]

    for member_id, choice in votes:
        vote = council.cast_vote(proposal.proposal_id, member_id, choice)
        member = council.get_member(member_id)
        print(f"   {member.name} voted: {choice}")
    print()

    # 6. Tally Votes
    print("6. TALLY VOTES:")
    print("-" * 40)

    winner, percentages = council.tally_votes(proposal.proposal_id)

    print(f"   Result: {winner}")
    print("   Breakdown:")
    for opt, pct in percentages.items():
        print(f"      {opt}: {pct:.1%}")
    print()

    # 7. Deliberation
    print("7. DELIBERATION:")
    print("-" * 40)

    deliberation = council.start_deliberation(
        topic="Technical Architecture Decision",
        participants=[m.member_id for m in members[:3]]
    )

    council.contribute(
        deliberation.deliberation_id,
        leader.member_id,
        "We should prioritize scalability."
    )

    council.contribute(
        deliberation.deliberation_id,
        expert1.member_id,
        "Agree, microservices architecture recommended."
    )

    print(f"   Topic: {deliberation.topic}")
    print(f"   Contributions: {len(deliberation.contributions)}")
    print()

    # 8. Record Decision
    print("8. RECORD DECISION:")
    print("-" * 40)

    council.record_decision(
        proposal.proposal_id,
        winner,
        "Approved with majority vote"
    )

    summary = council.get_session_summary()
    print(f"   Proposals: {summary['proposals']}")
    print(f"   Decisions: {summary['decisions']}")
    print()

    # 9. End Session
    print("9. END SESSION:")
    print("-" * 40)

    ended = council.end_session()

    print(f"   Status: {ended.status.value}")
    print(f"   Duration: {(ended.ended_at - ended.started_at).seconds}s")
    print()

    # 10. Run Automated Session
    print("10. RUN AUTOMATED SESSION:")
    print("-" * 40)

    proposals = [
        {"title": "Budget Review", "description": "Q4 budget"},
        {"title": "Hiring Plan", "description": "New team members"}
    ]

    session = await engine.run_session(
        council.council_id,
        agenda=["Budget", "Hiring"],
        proposals=proposals,
        simulate_votes=True
    )

    print(f"   Session completed")
    print(f"   Proposals processed: {len(session.proposals)}")
    print(f"   Decisions made: {len(session.decisions)}")
    print()

    # 11. Reach Consensus
    print("11. REACH CONSENSUS:")
    print("-" * 40)

    council2 = engine.create_council(
        name="Consensus Council",
        voting_method=VotingMethod.SUPERMAJORITY
    )

    for i in range(5):
        council2.add_member(f"Member-{i+1}")

    result, level = await engine.reach_consensus(
        council2.council_id,
        "Emergency Funding",
        "Approve emergency funding request"
    )

    print(f"   Result: {result}")
    print(f"   Consensus Level: {level:.1%}")
    print()

    # 12. Statistics
    print("12. STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Sessions: {stats.total_sessions}")
    print(f"   Proposals Submitted: {stats.proposals_submitted}")
    print(f"   Approved: {stats.proposals_approved}")
    print(f"   Rejected: {stats.proposals_rejected}")
    print(f"   Total Votes: {stats.total_votes}")
    print()

    # 13. Engine Summary
    print("13. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    print(f"   Councils: {summary['total_councils']}")
    print(f"   Sessions: {summary['total_sessions']}")
    print(f"   Approval Rate: {summary['approval_rate']:.1%}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Council Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
