"""
🌐 CONSENSUS PROTOCOLS 🌐
=========================
Distributed consensus.

Features:
- PBFT consensus
- Raft consensus
- Voting mechanisms
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime
import uuid
import hashlib


class ConsensusType(Enum):
    """Consensus types"""
    PBFT = auto()          # Practical Byzantine Fault Tolerance
    RAFT = auto()          # Leader-based consensus
    POW = auto()           # Proof of Work
    POS = auto()           # Proof of Stake
    VOTING = auto()        # Simple voting
    WEIGHTED_VOTING = auto()


@dataclass
class Vote:
    """A consensus vote"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    voter_id: str = ""
    proposal_id: str = ""

    # Vote value
    approve: bool = True

    # Weight
    weight: float = 1.0

    # Signature (for verification)
    signature: str = ""

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    def sign(self, secret: str):
        """Sign vote"""
        content = f"{self.voter_id}:{self.proposal_id}:{self.approve}"
        self.signature = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()

    def verify(self, secret: str) -> bool:
        """Verify signature"""
        content = f"{self.voter_id}:{self.proposal_id}:{self.approve}"
        expected = hashlib.sha256(f"{content}:{secret}".encode()).hexdigest()
        return self.signature == expected


@dataclass
class Proposal:
    """A consensus proposal"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content
    proposer_id: str = ""
    content: Any = None
    content_hash: str = ""

    # Type
    proposal_type: str = ""

    # Votes
    votes: List[Vote] = field(default_factory=list)

    # Status
    is_decided: bool = False
    is_accepted: bool = False

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None

    # Required votes
    required_votes: int = 0

    def add_vote(self, vote: Vote):
        """Add vote"""
        # Check for duplicate
        for v in self.votes:
            if v.voter_id == vote.voter_id:
                return  # Already voted

        self.votes.append(vote)

    def compute_hash(self):
        """Compute content hash"""
        self.content_hash = hashlib.sha256(str(self.content).encode()).hexdigest()

    def get_approval_count(self) -> int:
        """Get approval count"""
        return sum(1 for v in self.votes if v.approve)

    def get_weighted_approval(self) -> float:
        """Get weighted approval"""
        return sum(v.weight for v in self.votes if v.approve)


class ConsensusProtocol:
    """
    Base consensus protocol.
    """

    def __init__(self, consensus_type: ConsensusType = ConsensusType.VOTING):
        self.consensus_type = consensus_type

        self.proposals: Dict[str, Proposal] = {}
        self.participants: Set[str] = set()

        # Quorum
        self.quorum_fraction: float = 0.5

        # Callbacks
        self.on_decide: List[Callable[[Proposal], None]] = []

    def add_participant(self, participant_id: str):
        """Add participant"""
        self.participants.add(participant_id)

    def remove_participant(self, participant_id: str):
        """Remove participant"""
        self.participants.discard(participant_id)

    def get_quorum(self) -> int:
        """Get required quorum"""
        return max(1, int(len(self.participants) * self.quorum_fraction) + 1)

    def propose(self, proposer_id: str, content: Any, proposal_type: str = "") -> Proposal:
        """Create proposal"""
        proposal = Proposal(
            proposer_id=proposer_id,
            content=content,
            proposal_type=proposal_type,
            required_votes=self.get_quorum()
        )
        proposal.compute_hash()

        self.proposals[proposal.id] = proposal
        return proposal

    def vote(self, voter_id: str, proposal_id: str, approve: bool) -> Optional[Vote]:
        """Cast vote"""
        if voter_id not in self.participants:
            return None

        if proposal_id not in self.proposals:
            return None

        proposal = self.proposals[proposal_id]
        if proposal.is_decided:
            return None

        vote = Vote(
            voter_id=voter_id,
            proposal_id=proposal_id,
            approve=approve
        )

        proposal.add_vote(vote)

        # Check if decided
        self._check_decision(proposal)

        return vote

    def _check_decision(self, proposal: Proposal):
        """Check if proposal is decided"""
        if proposal.is_decided:
            return

        approvals = proposal.get_approval_count()
        rejections = len(proposal.votes) - approvals

        # Accepted if quorum approves
        if approvals >= proposal.required_votes:
            proposal.is_decided = True
            proposal.is_accepted = True
            proposal.decided_at = datetime.now()

            for callback in self.on_decide:
                callback(proposal)

        # Rejected if cannot reach quorum
        elif rejections > len(self.participants) - proposal.required_votes:
            proposal.is_decided = True
            proposal.is_accepted = False
            proposal.decided_at = datetime.now()

            for callback in self.on_decide:
                callback(proposal)

    def get_pending_proposals(self) -> List[Proposal]:
        """Get pending proposals"""
        return [p for p in self.proposals.values() if not p.is_decided]


class PBFTConsensus(ConsensusProtocol):
    """
    Practical Byzantine Fault Tolerance.
    """

    def __init__(self):
        super().__init__(ConsensusType.PBFT)

        # PBFT phases
        self.pre_prepare: Dict[str, Set[str]] = {}  # proposal_id -> nodes
        self.prepare: Dict[str, Set[str]] = {}
        self.commit: Dict[str, Set[str]] = {}

        # View number
        self.view: int = 0
        self.primary: Optional[str] = None

    def set_primary(self, node_id: str):
        """Set primary node"""
        self.primary = node_id

    def get_f(self) -> int:
        """Get maximum faulty nodes tolerable"""
        n = len(self.participants)
        return (n - 1) // 3

    def get_quorum(self) -> int:
        """PBFT quorum: 2f + 1"""
        return 2 * self.get_f() + 1

    def pre_prepare_msg(self, proposal_id: str, node_id: str):
        """Handle pre-prepare message"""
        if proposal_id not in self.pre_prepare:
            self.pre_prepare[proposal_id] = set()
        self.pre_prepare[proposal_id].add(node_id)

    def prepare_msg(self, proposal_id: str, node_id: str):
        """Handle prepare message"""
        if proposal_id not in self.prepare:
            self.prepare[proposal_id] = set()
        self.prepare[proposal_id].add(node_id)

        # Check if ready for commit
        if len(self.prepare.get(proposal_id, set())) >= self.get_quorum():
            # Ready for commit phase
            pass

    def commit_msg(self, proposal_id: str, node_id: str):
        """Handle commit message"""
        if proposal_id not in self.commit:
            self.commit[proposal_id] = set()
        self.commit[proposal_id].add(node_id)

        # Check if decided
        if len(self.commit.get(proposal_id, set())) >= self.get_quorum():
            if proposal_id in self.proposals:
                proposal = self.proposals[proposal_id]
                proposal.is_decided = True
                proposal.is_accepted = True
                proposal.decided_at = datetime.now()

    def view_change(self):
        """Trigger view change"""
        self.view += 1
        # Rotate primary
        participants = sorted(self.participants)
        if participants:
            self.primary = participants[self.view % len(participants)]


class RaftConsensus(ConsensusProtocol):
    """
    Raft consensus protocol.
    """

    def __init__(self):
        super().__init__(ConsensusType.RAFT)

        # Raft state
        self.current_term: int = 0
        self.voted_for: Optional[str] = None
        self.leader: Optional[str] = None

        # Log
        self.log: List[Dict[str, Any]] = []
        self.commit_index: int = -1

        # Node states
        self.node_states: Dict[str, str] = {}  # follower, candidate, leader

        # Timeouts
        self.election_timeout_ms: int = 150
        self.heartbeat_interval_ms: int = 50

    def set_leader(self, node_id: str):
        """Set leader"""
        self.leader = node_id
        self.node_states[node_id] = "leader"

    def start_election(self, candidate_id: str):
        """Start election"""
        self.current_term += 1
        self.voted_for = candidate_id
        self.node_states[candidate_id] = "candidate"

    def request_vote(
        self,
        candidate_id: str,
        term: int,
        voter_id: str
    ) -> bool:
        """Request vote from voter"""
        # If term is old, reject
        if term < self.current_term:
            return False

        # If already voted for someone else this term, reject
        if self.voted_for and self.voted_for != candidate_id:
            return False

        # Grant vote
        self.voted_for = candidate_id
        return True

    def append_entries(
        self,
        leader_id: str,
        term: int,
        entries: List[Any],
        leader_commit: int
    ) -> bool:
        """Append entries (heartbeat + log replication)"""
        # If term is old, reject
        if term < self.current_term:
            return False

        # Accept leader
        self.current_term = term
        self.leader = leader_id

        # Append entries
        for entry in entries:
            self.log.append({
                'term': term,
                'data': entry
            })

        # Update commit index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log) - 1)

        return True

    def propose(
        self,
        proposer_id: str,
        content: Any,
        proposal_type: str = ""
    ) -> Proposal:
        """Propose (only leader can propose)"""
        if proposer_id != self.leader:
            raise ValueError("Only leader can propose")

        proposal = super().propose(proposer_id, content, proposal_type)

        # Add to log
        self.log.append({
            'term': self.current_term,
            'proposal_id': proposal.id,
            'data': content
        })

        return proposal

    def get_state(self, node_id: str) -> str:
        """Get node state"""
        return self.node_states.get(node_id, "follower")


# Export all
__all__ = [
    'ConsensusType',
    'Vote',
    'Proposal',
    'ConsensusProtocol',
    'PBFTConsensus',
    'RaftConsensus',
]
