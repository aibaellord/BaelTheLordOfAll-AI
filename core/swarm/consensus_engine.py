"""
BAEL Consensus Engine
======================

Collective decision-making for swarm intelligence.
Enables distributed consensus and voting.

Features:
- Multiple consensus methods
- Weighted voting
- Byzantine fault tolerance
- Quorum management
- Decision history
"""

import asyncio
import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ConsensusMethod(Enum):
    """Consensus methods."""
    MAJORITY = "majority"  # Simple majority
    SUPERMAJORITY = "supermajority"  # 2/3 majority
    UNANIMOUS = "unanimous"  # All agree
    WEIGHTED = "weighted"  # Weighted by expertise
    RANKED = "ranked"  # Ranked choice
    LIQUID = "liquid"  # Delegated voting
    BYZANTINE = "byzantine"  # BFT consensus


class VoteType(Enum):
    """Vote types."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    """A vote in consensus."""
    voter_id: str
    choice: Any
    vote_type: VoteType = VoteType.APPROVE

    # Weighting
    weight: float = 1.0
    confidence: float = 1.0

    # Delegation
    delegated_from: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning: str = ""


@dataclass
class VotingResult:
    """Result of a consensus vote."""
    proposal_id: str
    topic: str

    # Outcome
    decision: Any = None
    consensus_reached: bool = False

    # Votes
    total_votes: int = 0
    votes_for: int = 0
    votes_against: int = 0
    abstentions: int = 0

    # Analysis
    participation_rate: float = 0.0
    consensus_strength: float = 0.0

    # Metadata
    method: ConsensusMethod = ConsensusMethod.MAJORITY
    completed_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConsensusConfig:
    """Consensus configuration."""
    # Method
    default_method: ConsensusMethod = ConsensusMethod.MAJORITY

    # Thresholds
    quorum_percentage: float = 0.5
    majority_threshold: float = 0.5
    supermajority_threshold: float = 0.67

    # Timing
    voting_timeout_seconds: float = 300.0
    min_deliberation_seconds: float = 10.0

    # Byzantine
    max_byzantine_nodes: int = 0  # f in 3f+1


@dataclass
class Proposal:
    """A proposal for consensus."""
    id: str
    topic: str
    options: List[Any]

    # Configuration
    method: ConsensusMethod = ConsensusMethod.MAJORITY
    required_quorum: float = 0.5

    # State
    votes: Dict[str, Vote] = field(default_factory=dict)
    status: str = "pending"

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None

    # Metadata
    proposer: str = ""
    description: str = ""


class ConsensusEngine:
    """
    Consensus engine for BAEL swarm.

    Enables collective decision-making with
    multiple consensus mechanisms.
    """

    def __init__(self, config: Optional[ConsensusConfig] = None):
        self.config = config or ConsensusConfig()

        # Active proposals
        self._proposals: Dict[str, Proposal] = {}

        # Voter registry
        self._voters: Dict[str, Dict[str, Any]] = {}

        # Delegation map
        self._delegations: Dict[str, str] = {}  # delegator -> delegate

        # History
        self._history: List[VotingResult] = []

        # Stats
        self.stats = {
            "proposals_created": 0,
            "consensus_reached": 0,
            "consensus_failed": 0,
            "total_votes": 0,
        }

    def register_voter(
        self,
        voter_id: str,
        weight: float = 1.0,
        expertise: Optional[Dict[str, float]] = None,
    ) -> None:
        """Register a voter."""
        self._voters[voter_id] = {
            "weight": weight,
            "expertise": expertise or {},
            "registered_at": datetime.now(),
        }
        logger.debug(f"Registered voter: {voter_id}")

    def delegate(
        self,
        delegator: str,
        delegate: str,
    ) -> bool:
        """Delegate voting power."""
        if delegator == delegate:
            return False

        # Check for circular delegation
        current = delegate
        while current in self._delegations:
            if self._delegations[current] == delegator:
                return False  # Circular
            current = self._delegations[current]

        self._delegations[delegator] = delegate
        return True

    async def create_proposal(
        self,
        topic: str,
        options: List[Any],
        method: Optional[ConsensusMethod] = None,
        timeout_seconds: Optional[float] = None,
        description: str = "",
        proposer: str = "",
    ) -> Proposal:
        """
        Create a consensus proposal.

        Args:
            topic: Proposal topic
            options: Available options
            method: Consensus method
            timeout_seconds: Voting timeout
            description: Proposal description
            proposer: Proposer ID

        Returns:
            Created proposal
        """
        proposal_id = hashlib.md5(
            f"{topic}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        timeout = timeout_seconds or self.config.voting_timeout_seconds

        proposal = Proposal(
            id=proposal_id,
            topic=topic,
            options=options,
            method=method or self.config.default_method,
            required_quorum=self.config.quorum_percentage,
            deadline=datetime.now() + timedelta(seconds=timeout),
            proposer=proposer,
            description=description,
            status="active",
        )

        self._proposals[proposal_id] = proposal
        self.stats["proposals_created"] += 1

        logger.info(f"Proposal created: {proposal_id} - {topic}")

        return proposal

    async def vote(
        self,
        proposal_id: str,
        voter_id: str,
        choice: Any,
        confidence: float = 1.0,
        reasoning: str = "",
    ) -> bool:
        """
        Submit a vote.

        Args:
            proposal_id: Proposal to vote on
            voter_id: Voter identifier
            choice: Vote choice
            confidence: Vote confidence
            reasoning: Vote reasoning

        Returns:
            Success status
        """
        if proposal_id not in self._proposals:
            return False

        proposal = self._proposals[proposal_id]

        if proposal.status != "active":
            return False

        if proposal.deadline and datetime.now() > proposal.deadline:
            return False

        if choice not in proposal.options:
            return False

        # Get voter weight
        weight = 1.0
        if voter_id in self._voters:
            weight = self._voters[voter_id].get("weight", 1.0)

            # Add expertise weight if applicable
            expertise = self._voters[voter_id].get("expertise", {})
            topic_expertise = expertise.get(proposal.topic, 1.0)
            weight *= topic_expertise

        # Handle delegation
        effective_weight = weight
        for delegator, delegate in self._delegations.items():
            if delegate == voter_id:
                delegator_weight = self._voters.get(delegator, {}).get("weight", 1.0)
                effective_weight += delegator_weight

        vote = Vote(
            voter_id=voter_id,
            choice=choice,
            weight=effective_weight,
            confidence=confidence,
            reasoning=reasoning,
        )

        proposal.votes[voter_id] = vote
        self.stats["total_votes"] += 1

        logger.debug(f"Vote recorded: {voter_id} -> {choice} on {proposal_id}")

        return True

    async def resolve(
        self,
        proposal_id: str,
    ) -> VotingResult:
        """
        Resolve a proposal.

        Args:
            proposal_id: Proposal to resolve

        Returns:
            Voting result
        """
        if proposal_id not in self._proposals:
            raise ValueError(f"Unknown proposal: {proposal_id}")

        proposal = self._proposals[proposal_id]

        # Calculate result based on method
        if proposal.method == ConsensusMethod.MAJORITY:
            result = self._resolve_majority(proposal)
        elif proposal.method == ConsensusMethod.SUPERMAJORITY:
            result = self._resolve_supermajority(proposal)
        elif proposal.method == ConsensusMethod.UNANIMOUS:
            result = self._resolve_unanimous(proposal)
        elif proposal.method == ConsensusMethod.WEIGHTED:
            result = self._resolve_weighted(proposal)
        elif proposal.method == ConsensusMethod.RANKED:
            result = self._resolve_ranked(proposal)
        elif proposal.method == ConsensusMethod.BYZANTINE:
            result = self._resolve_byzantine(proposal)
        else:
            result = self._resolve_majority(proposal)

        # Update proposal status
        proposal.status = "resolved"

        # Update stats
        if result.consensus_reached:
            self.stats["consensus_reached"] += 1
        else:
            self.stats["consensus_failed"] += 1

        # Add to history
        self._history.append(result)

        logger.info(
            f"Proposal {proposal_id} resolved: "
            f"{'Consensus' if result.consensus_reached else 'No consensus'} - {result.decision}"
        )

        return result

    def _resolve_majority(self, proposal: Proposal) -> VotingResult:
        """Resolve by simple majority."""
        votes = proposal.votes

        # Check quorum
        participation = len(votes) / max(len(self._voters), 1)
        if participation < proposal.required_quorum:
            return VotingResult(
                proposal_id=proposal.id,
                topic=proposal.topic,
                consensus_reached=False,
                participation_rate=participation,
                method=ConsensusMethod.MAJORITY,
            )

        # Count votes per option
        vote_counts: Dict[Any, float] = {}
        for vote in votes.values():
            if vote.choice not in vote_counts:
                vote_counts[vote.choice] = 0
            vote_counts[vote.choice] += vote.weight * vote.confidence

        if not vote_counts:
            return VotingResult(
                proposal_id=proposal.id,
                topic=proposal.topic,
                consensus_reached=False,
                method=ConsensusMethod.MAJORITY,
            )

        # Find winner
        total = sum(vote_counts.values())
        winner = max(vote_counts, key=lambda x: vote_counts[x])
        winner_share = vote_counts[winner] / total if total > 0 else 0

        return VotingResult(
            proposal_id=proposal.id,
            topic=proposal.topic,
            decision=winner,
            consensus_reached=winner_share > self.config.majority_threshold,
            total_votes=len(votes),
            participation_rate=participation,
            consensus_strength=winner_share,
            method=ConsensusMethod.MAJORITY,
        )

    def _resolve_supermajority(self, proposal: Proposal) -> VotingResult:
        """Resolve by supermajority (2/3)."""
        result = self._resolve_majority(proposal)
        result.method = ConsensusMethod.SUPERMAJORITY
        result.consensus_reached = (
            result.consensus_strength >= self.config.supermajority_threshold
        )
        return result

    def _resolve_unanimous(self, proposal: Proposal) -> VotingResult:
        """Resolve by unanimous consent."""
        votes = proposal.votes

        if not votes:
            return VotingResult(
                proposal_id=proposal.id,
                topic=proposal.topic,
                consensus_reached=False,
                method=ConsensusMethod.UNANIMOUS,
            )

        choices = set(v.choice for v in votes.values())
        unanimous = len(choices) == 1

        return VotingResult(
            proposal_id=proposal.id,
            topic=proposal.topic,
            decision=list(choices)[0] if unanimous else None,
            consensus_reached=unanimous,
            total_votes=len(votes),
            consensus_strength=1.0 if unanimous else 0.0,
            method=ConsensusMethod.UNANIMOUS,
        )

    def _resolve_weighted(self, proposal: Proposal) -> VotingResult:
        """Resolve by weighted voting."""
        votes = proposal.votes

        # Sum weighted votes
        weighted_counts: Dict[Any, float] = {}
        total_weight = 0

        for vote in votes.values():
            effective_weight = vote.weight * vote.confidence
            if vote.choice not in weighted_counts:
                weighted_counts[vote.choice] = 0
            weighted_counts[vote.choice] += effective_weight
            total_weight += effective_weight

        if not weighted_counts:
            return VotingResult(
                proposal_id=proposal.id,
                topic=proposal.topic,
                consensus_reached=False,
                method=ConsensusMethod.WEIGHTED,
            )

        winner = max(weighted_counts, key=lambda x: weighted_counts[x])
        strength = weighted_counts[winner] / total_weight if total_weight > 0 else 0

        return VotingResult(
            proposal_id=proposal.id,
            topic=proposal.topic,
            decision=winner,
            consensus_reached=strength > self.config.majority_threshold,
            total_votes=len(votes),
            consensus_strength=strength,
            method=ConsensusMethod.WEIGHTED,
        )

    def _resolve_ranked(self, proposal: Proposal) -> VotingResult:
        """Resolve by ranked choice (simplified)."""
        # For simplicity, treat as majority
        return self._resolve_majority(proposal)

    def _resolve_byzantine(self, proposal: Proposal) -> VotingResult:
        """Resolve with Byzantine fault tolerance."""
        votes = proposal.votes
        n = len(self._voters)
        f = self.config.max_byzantine_nodes

        # BFT requires 3f+1 nodes minimum
        required_votes = 2 * f + 1

        if len(votes) < required_votes:
            return VotingResult(
                proposal_id=proposal.id,
                topic=proposal.topic,
                consensus_reached=False,
                total_votes=len(votes),
                method=ConsensusMethod.BYZANTINE,
            )

        # Check for 2f+1 matching votes
        vote_counts: Dict[Any, int] = {}
        for vote in votes.values():
            if vote.choice not in vote_counts:
                vote_counts[vote.choice] = 0
            vote_counts[vote.choice] += 1

        for choice, count in vote_counts.items():
            if count >= required_votes:
                return VotingResult(
                    proposal_id=proposal.id,
                    topic=proposal.topic,
                    decision=choice,
                    consensus_reached=True,
                    total_votes=len(votes),
                    consensus_strength=count / len(votes),
                    method=ConsensusMethod.BYZANTINE,
                )

        return VotingResult(
            proposal_id=proposal.id,
            topic=proposal.topic,
            consensus_reached=False,
            method=ConsensusMethod.BYZANTINE,
        )

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get a proposal."""
        return self._proposals.get(proposal_id)

    def get_history(self, limit: int = 100) -> List[VotingResult]:
        """Get voting history."""
        return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "active_proposals": sum(
                1 for p in self._proposals.values() if p.status == "active"
            ),
            "voters": len(self._voters),
        }


def demo():
    """Demonstrate consensus engine."""
    import asyncio

    print("=" * 60)
    print("BAEL Consensus Engine Demo")
    print("=" * 60)

    async def run_demo():
        engine = ConsensusEngine()

        # Register voters
        engine.register_voter("agent_1", weight=1.0, expertise={"deployment": 0.9})
        engine.register_voter("agent_2", weight=1.0, expertise={"deployment": 0.8})
        engine.register_voter("agent_3", weight=0.8, expertise={"testing": 0.9})
        engine.register_voter("agent_4", weight=0.8)
        engine.register_voter("agent_5", weight=1.0)

        print(f"\nRegistered {len(engine._voters)} voters")

        # Create proposal
        proposal = await engine.create_proposal(
            topic="deployment",
            options=["blue_green", "canary", "rolling"],
            method=ConsensusMethod.WEIGHTED,
            description="Choose deployment strategy",
        )

        print(f"\nProposal: {proposal.topic}")
        print(f"Options: {proposal.options}")
        print(f"Method: {proposal.method.value}")

        # Submit votes
        print("\nVoting...")
        await engine.vote(proposal.id, "agent_1", "blue_green", confidence=0.9)
        await engine.vote(proposal.id, "agent_2", "blue_green", confidence=0.8)
        await engine.vote(proposal.id, "agent_3", "canary", confidence=0.7)
        await engine.vote(proposal.id, "agent_4", "blue_green", confidence=0.6)
        await engine.vote(proposal.id, "agent_5", "rolling", confidence=0.5)

        # Resolve
        result = await engine.resolve(proposal.id)

        print(f"\nResult:")
        print(f"  Decision: {result.decision}")
        print(f"  Consensus: {'Yes' if result.consensus_reached else 'No'}")
        print(f"  Strength: {result.consensus_strength:.1%}")
        print(f"  Total votes: {result.total_votes}")

        # Test delegation
        print("\nTesting delegation...")
        engine.delegate("agent_5", "agent_1")

        proposal2 = await engine.create_proposal(
            topic="testing_strategy",
            options=["unit_first", "integration_first", "e2e_first"],
            method=ConsensusMethod.MAJORITY,
        )

        await engine.vote(proposal2.id, "agent_1", "unit_first")
        await engine.vote(proposal2.id, "agent_2", "unit_first")
        await engine.vote(proposal2.id, "agent_3", "integration_first")

        result2 = await engine.resolve(proposal2.id)
        print(f"  Delegated result: {result2.decision}")

        print(f"\nStats: {engine.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
