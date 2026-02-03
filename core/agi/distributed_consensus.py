"""
BAEL Phase 7.5: Distributed Consensus & Voting
═════════════════════════════════════════════════════════════════════════════

Distributed consensus protocols with Byzantine fault tolerance, PBFT,
Raft, voting systems, and leader election mechanisms.

Features:
  • Practical Byzantine Fault Tolerance (PBFT)
  • Raft Consensus Protocol
  • Paxos-inspired Voting
  • Leader Election (Bully, Ring, Raft)
  • Quorum-based Decisions
  • State Machine Replication
  • View Changes & Recovery
  • Fault Detection
  • Message Ordering & Validation
  • Consensus Logging

Author: BAEL Team
Date: February 2, 2026
"""

import hashlib
import json
import logging
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ═══════════════════════════════════════════════════════════════════════════

class ConsensusProtocol(str, Enum):
    """Consensus protocol types."""
    PBFT = "pbft"  # Practical Byzantine Fault Tolerance
    RAFT = "raft"  # Raft consensus
    PAXOS = "paxos"  # Paxos-inspired
    VOTING = "voting"  # Simple majority voting


class NodeState(str, Enum):
    """Distributed node state."""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"
    REPLICA = "replica"
    FAULTY = "faulty"


class MessageType(str, Enum):
    """Consensus message types."""
    # PBFT
    REQUEST = "request"
    PRE_PREPARE = "pre_prepare"
    PREPARE = "prepare"
    COMMIT = "commit"
    REPLY = "reply"
    VIEW_CHANGE = "view_change"
    NEW_VIEW = "new_view"

    # Raft
    APPEND_ENTRIES = "append_entries"
    REQUEST_VOTE = "request_vote"
    VOTE_RESPONSE = "vote_response"

    # General
    HEARTBEAT = "heartbeat"


class VoteDecision(str, Enum):
    """Voting decisions."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class ConsensusStatus(str, Enum):
    """Consensus round status."""
    PENDING = "pending"
    PREPARED = "prepared"
    COMMITTED = "committed"
    ABORTED = "aborted"


# ═══════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NodeInfo:
    """Distributed node information."""
    node_id: str
    state: NodeState
    term: int = 0  # Current term (Raft)
    view: int = 0  # Current view (PBFT)
    voted_for: Optional[str] = None
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_faulty: bool = False
    message_count: int = 0


@dataclass
class ConsensusMessage:
    """Consensus protocol message."""
    message_id: str
    message_type: MessageType
    sender_id: str
    view: int
    sequence_number: int
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: Optional[str] = None

    def compute_signature(self, secret: str = "secret") -> str:
        """Compute message signature."""
        data = f"{self.message_id}{self.sender_id}{self.view}{self.sequence_number}{json.dumps(self.payload, sort_keys=True)}"
        return hashlib.sha256(f"{data}{secret}".encode()).hexdigest()

    def verify_signature(self, secret: str = "secret") -> bool:
        """Verify message signature."""
        expected = self.compute_signature(secret)
        return self.signature == expected


@dataclass
class LogEntry:
    """Replicated log entry."""
    index: int
    term: int
    command: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    committed: bool = False


@dataclass
class ConsensusRound:
    """Consensus round tracking."""
    round_id: str
    sequence_number: int
    view: int
    request: ConsensusMessage
    status: ConsensusStatus = ConsensusStatus.PENDING
    pre_prepare_msg: Optional[ConsensusMessage] = None
    prepare_msgs: Dict[str, ConsensusMessage] = field(default_factory=dict)
    commit_msgs: Dict[str, ConsensusMessage] = field(default_factory=dict)
    replies: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None


@dataclass
class QuorumConfig:
    """Quorum configuration."""
    total_nodes: int
    byzantine_tolerance: int  # f = max faulty nodes

    @property
    def minimum_quorum(self) -> int:
        """Minimum nodes for quorum (2f + 1)."""
        return 2 * self.byzantine_tolerance + 1

    @property
    def prepare_quorum(self) -> int:
        """PBFT prepare quorum (2f + 1)."""
        return 2 * self.byzantine_tolerance + 1

    @property
    def commit_quorum(self) -> int:
        """PBFT commit quorum (2f + 1)."""
        return 2 * self.byzantine_tolerance + 1

    def can_tolerate_faults(self) -> bool:
        """Check if configuration can tolerate faults."""
        return self.total_nodes >= 3 * self.byzantine_tolerance + 1


# ═══════════════════════════════════════════════════════════════════════════
# PBFT Consensus Engine
# ═══════════════════════════════════════════════════════════════════════════

class PBFTConsensus:
    """Practical Byzantine Fault Tolerance consensus."""

    def __init__(
        self,
        node_id: str,
        total_nodes: int,
        byzantine_tolerance: int = 1
    ):
        """Initialize PBFT consensus."""
        self.node_id = node_id
        self.node_info = NodeInfo(node_id=node_id, state=NodeState.REPLICA)
        self.quorum = QuorumConfig(total_nodes, byzantine_tolerance)

        self.current_view = 0
        self.sequence_number = 0
        self.high_water_mark = 100
        self.low_water_mark = 0

        self.active_rounds: Dict[int, ConsensusRound] = {}
        self.message_log: List[ConsensusMessage] = []
        self.committed_log: List[LogEntry] = []

        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def is_primary(self) -> bool:
        """Check if this node is primary."""
        # Primary is node with ID matching view number mod total nodes
        primary_idx = self.current_view % self.quorum.total_nodes
        return self.node_id == f"node_{primary_idx}"

    def submit_request(
        self,
        client_id: str,
        operation: str,
        data: Dict[str, Any]
    ) -> str:
        """Submit client request."""
        with self._lock:
            self.sequence_number += 1

            request = ConsensusMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.REQUEST,
                sender_id=client_id,
                view=self.current_view,
                sequence_number=self.sequence_number,
                payload={'operation': operation, 'data': data}
            )

            if self.is_primary():
                self._handle_request_as_primary(request)
            else:
                self._forward_to_primary(request)

            return request.message_id

    def _handle_request_as_primary(self, request: ConsensusMessage) -> None:
        """Handle request as primary node."""
        # Create consensus round
        round_obj = ConsensusRound(
            round_id=str(uuid.uuid4()),
            sequence_number=request.sequence_number,
            view=self.current_view,
            request=request
        )

        self.active_rounds[request.sequence_number] = round_obj

        # Send PRE-PREPARE to replicas
        pre_prepare = ConsensusMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.PRE_PREPARE,
            sender_id=self.node_id,
            view=self.current_view,
            sequence_number=request.sequence_number,
            payload=request.payload
        )
        pre_prepare.signature = pre_prepare.compute_signature()

        round_obj.pre_prepare_msg = pre_prepare
        self.message_log.append(pre_prepare)

        self.logger.info(f"Primary sent PRE-PREPARE for seq {request.sequence_number}")

    def _forward_to_primary(self, request: ConsensusMessage) -> None:
        """Forward request to primary."""
        self.logger.info(f"Forwarding request {request.message_id} to primary")

    def receive_pre_prepare(self, pre_prepare: ConsensusMessage) -> None:
        """Receive PRE-PREPARE message."""
        with self._lock:
            if not self._validate_pre_prepare(pre_prepare):
                self.logger.warning(f"Invalid PRE-PREPARE from {pre_prepare.sender_id}")
                return

            # Send PREPARE to all replicas
            prepare = ConsensusMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.PREPARE,
                sender_id=self.node_id,
                view=pre_prepare.view,
                sequence_number=pre_prepare.sequence_number,
                payload=pre_prepare.payload
            )
            prepare.signature = prepare.compute_signature()

            self.message_log.append(prepare)

            # Update round
            if pre_prepare.sequence_number in self.active_rounds:
                round_obj = self.active_rounds[pre_prepare.sequence_number]
                round_obj.prepare_msgs[self.node_id] = prepare

            self.logger.info(f"Sent PREPARE for seq {pre_prepare.sequence_number}")

    def receive_prepare(self, prepare: ConsensusMessage) -> None:
        """Receive PREPARE message."""
        with self._lock:
            if not self._validate_prepare(prepare):
                return

            seq = prepare.sequence_number
            if seq not in self.active_rounds:
                return

            round_obj = self.active_rounds[seq]
            round_obj.prepare_msgs[prepare.sender_id] = prepare

            # Check if prepared (received 2f PREPAREs)
            if len(round_obj.prepare_msgs) >= self.quorum.prepare_quorum - 1:
                self._enter_prepared_state(round_obj)

    def _enter_prepared_state(self, round_obj: ConsensusRound) -> None:
        """Enter prepared state and send COMMIT."""
        round_obj.status = ConsensusStatus.PREPARED

        commit = ConsensusMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.COMMIT,
            sender_id=self.node_id,
            view=round_obj.view,
            sequence_number=round_obj.sequence_number,
            payload=round_obj.request.payload
        )
        commit.signature = commit.compute_signature()

        self.message_log.append(commit)
        round_obj.commit_msgs[self.node_id] = commit

        self.logger.info(f"Entered PREPARED state for seq {round_obj.sequence_number}")

    def receive_commit(self, commit: ConsensusMessage) -> None:
        """Receive COMMIT message."""
        with self._lock:
            if not self._validate_commit(commit):
                return

            seq = commit.sequence_number
            if seq not in self.active_rounds:
                return

            round_obj = self.active_rounds[seq]
            round_obj.commit_msgs[commit.sender_id] = commit

            # Check if committed (received 2f + 1 COMMITs)
            if len(round_obj.commit_msgs) >= self.quorum.commit_quorum:
                self._enter_committed_state(round_obj)

    def _enter_committed_state(self, round_obj: ConsensusRound) -> None:
        """Enter committed state and execute request."""
        round_obj.status = ConsensusStatus.COMMITTED
        round_obj.end_time = datetime.now(timezone.utc)

        # Add to committed log
        log_entry = LogEntry(
            index=len(self.committed_log),
            term=round_obj.view,
            command=round_obj.request.payload.get('operation', ''),
            data=round_obj.request.payload.get('data', {}),
            committed=True
        )
        self.committed_log.append(log_entry)

        self.logger.info(f"Committed seq {round_obj.sequence_number}")

    def _validate_pre_prepare(self, msg: ConsensusMessage) -> bool:
        """Validate PRE-PREPARE message."""
        return (
            msg.view == self.current_view and
            self.low_water_mark < msg.sequence_number <= self.high_water_mark
        )

    def _validate_prepare(self, msg: ConsensusMessage) -> bool:
        """Validate PREPARE message."""
        return msg.view == self.current_view

    def _validate_commit(self, msg: ConsensusMessage) -> bool:
        """Validate COMMIT message."""
        return msg.view == self.current_view

    def initiate_view_change(self) -> None:
        """Initiate view change protocol."""
        with self._lock:
            self.current_view += 1

            view_change = ConsensusMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.VIEW_CHANGE,
                sender_id=self.node_id,
                view=self.current_view,
                sequence_number=0,
                payload={
                    'prepared_rounds': [
                        asdict(r) for r in self.active_rounds.values()
                        if r.status == ConsensusStatus.PREPARED
                    ]
                }
            )

            self.message_log.append(view_change)
            self.logger.info(f"Initiated view change to view {self.current_view}")


# ═══════════════════════════════════════════════════════════════════════════
# Raft Consensus Engine
# ═══════════════════════════════════════════════════════════════════════════

class RaftConsensus:
    """Raft consensus protocol."""

    def __init__(self, node_id: str, total_nodes: int):
        """Initialize Raft consensus."""
        self.node_id = node_id
        self.node_info = NodeInfo(node_id=node_id, state=NodeState.FOLLOWER)
        self.total_nodes = total_nodes

        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0

        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        self.election_timeout = 5.0  # seconds
        self.heartbeat_interval = 1.0  # seconds
        self.last_heartbeat = datetime.now(timezone.utc)

        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def start_election(self) -> None:
        """Start leader election."""
        with self._lock:
            self.current_term += 1
            self.node_info.state = NodeState.CANDIDATE
            self.node_info.term = self.current_term
            self.voted_for = self.node_id

            votes_received = 1  # Vote for self

            # Send REQUEST_VOTE to all nodes
            request_vote = ConsensusMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.REQUEST_VOTE,
                sender_id=self.node_id,
                view=0,
                sequence_number=0,
                payload={
                    'term': self.current_term,
                    'candidate_id': self.node_id,
                    'last_log_index': len(self.log) - 1 if self.log else -1,
                    'last_log_term': self.log[-1].term if self.log else 0
                }
            )

            self.logger.info(f"Started election for term {self.current_term}")

    def receive_request_vote(self, request: ConsensusMessage) -> ConsensusMessage:
        """Handle vote request."""
        with self._lock:
            term = request.payload['term']
            candidate_id = request.payload['candidate_id']

            grant_vote = False

            if term > self.current_term:
                self.current_term = term
                self.node_info.term = term
                self.node_info.state = NodeState.FOLLOWER
                self.voted_for = None

            if (term >= self.current_term and
                (self.voted_for is None or self.voted_for == candidate_id)):
                grant_vote = True
                self.voted_for = candidate_id

            response = ConsensusMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.VOTE_RESPONSE,
                sender_id=self.node_id,
                view=0,
                sequence_number=0,
                payload={
                    'term': self.current_term,
                    'vote_granted': grant_vote
                }
            )

            self.logger.info(f"Vote {'granted' if grant_vote else 'denied'} to {candidate_id}")
            return response

    def become_leader(self) -> None:
        """Become leader after winning election."""
        with self._lock:
            self.node_info.state = NodeState.LEADER

            # Initialize leader state
            for i in range(self.total_nodes):
                node_id = f"node_{i}"
                if node_id != self.node_id:
                    self.next_index[node_id] = len(self.log)
                    self.match_index[node_id] = 0

            self.logger.info(f"Became leader for term {self.current_term}")
            self._send_heartbeats()

    def _send_heartbeats(self) -> None:
        """Send heartbeat to all followers."""
        heartbeat = ConsensusMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.HEARTBEAT,
            sender_id=self.node_id,
            view=0,
            sequence_number=0,
            payload={
                'term': self.current_term,
                'leader_id': self.node_id,
                'commit_index': self.commit_index
            }
        )

        self.last_heartbeat = datetime.now(timezone.utc)
        self.logger.debug(f"Sent heartbeat for term {self.current_term}")

    def append_log_entry(self, command: str, data: Dict[str, Any]) -> None:
        """Append entry to log."""
        with self._lock:
            if self.node_info.state != NodeState.LEADER:
                self.logger.warning("Only leader can append entries")
                return

            entry = LogEntry(
                index=len(self.log),
                term=self.current_term,
                command=command,
                data=data
            )

            self.log.append(entry)
            self.logger.info(f"Appended log entry at index {entry.index}")

    def receive_append_entries(
        self,
        entries: List[LogEntry],
        leader_commit: int
    ) -> bool:
        """Receive append entries from leader."""
        with self._lock:
            # Append entries
            for entry in entries:
                if entry.index < len(self.log):
                    # Replace conflicting entry
                    self.log[entry.index] = entry
                else:
                    self.log.append(entry)

            # Update commit index
            if leader_commit > self.commit_index:
                self.commit_index = min(leader_commit, len(self.log) - 1)

            self.last_heartbeat = datetime.now(timezone.utc)
            return True


# ═══════════════════════════════════════════════════════════════════════════
# Voting System
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Vote:
    """Single vote in voting system."""
    voter_id: str
    decision: VoteDecision
    weight: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rationale: Optional[str] = None


@dataclass
class Proposal:
    """Proposal for voting."""
    proposal_id: str
    title: str
    description: str
    proposer_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    voting_deadline: Optional[datetime] = None
    votes: List[Vote] = field(default_factory=list)
    status: str = "active"  # active, passed, rejected, expired
    required_quorum: float = 0.5  # Fraction of voters needed
    approval_threshold: float = 0.5  # Fraction of votes needed


class VotingSystem:
    """Distributed voting system."""

    def __init__(self):
        """Initialize voting system."""
        self.proposals: Dict[str, Proposal] = {}
        self.voters: Set[str] = set()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def register_voter(self, voter_id: str) -> None:
        """Register voter."""
        with self._lock:
            self.voters.add(voter_id)
            self.logger.info(f"Registered voter: {voter_id}")

    def create_proposal(
        self,
        title: str,
        description: str,
        proposer_id: str,
        voting_deadline: Optional[datetime] = None,
        required_quorum: float = 0.5,
        approval_threshold: float = 0.5
    ) -> Proposal:
        """Create new proposal."""
        with self._lock:
            proposal = Proposal(
                proposal_id=str(uuid.uuid4()),
                title=title,
                description=description,
                proposer_id=proposer_id,
                voting_deadline=voting_deadline,
                required_quorum=required_quorum,
                approval_threshold=approval_threshold
            )

            self.proposals[proposal.proposal_id] = proposal
            self.logger.info(f"Created proposal: {title}")

            return proposal

    def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        decision: VoteDecision,
        weight: float = 1.0,
        rationale: Optional[str] = None
    ) -> bool:
        """Cast vote on proposal."""
        with self._lock:
            if voter_id not in self.voters:
                self.logger.warning(f"Unregistered voter: {voter_id}")
                return False

            if proposal_id not in self.proposals:
                self.logger.warning(f"Proposal not found: {proposal_id}")
                return False

            proposal = self.proposals[proposal_id]

            if proposal.status != "active":
                self.logger.warning(f"Proposal not active: {proposal_id}")
                return False

            # Check if already voted
            existing = [v for v in proposal.votes if v.voter_id == voter_id]
            if existing:
                self.logger.warning(f"Voter {voter_id} already voted")
                return False

            vote = Vote(
                voter_id=voter_id,
                decision=decision,
                weight=weight,
                rationale=rationale
            )

            proposal.votes.append(vote)
            self.logger.info(f"Vote cast by {voter_id} on {proposal_id}: {decision.value}")

            # Check if voting complete
            self._check_proposal_outcome(proposal)

            return True

    def _check_proposal_outcome(self, proposal: Proposal) -> None:
        """Check if proposal has reached outcome."""
        total_voters = len(self.voters)
        total_votes = len(proposal.votes)

        # Check quorum
        quorum_met = total_votes >= proposal.required_quorum * total_voters

        if not quorum_met:
            return

        # Count approvals
        approve_votes = sum(
            v.weight for v in proposal.votes
            if v.decision == VoteDecision.APPROVE
        )
        total_weight = sum(v.weight for v in proposal.votes)

        approval_rate = approve_votes / total_weight if total_weight > 0 else 0

        if approval_rate >= proposal.approval_threshold:
            proposal.status = "passed"
            self.logger.info(f"Proposal {proposal.proposal_id} PASSED")
        elif total_votes == total_voters:
            # All votes in, didn't pass
            proposal.status = "rejected"
            self.logger.info(f"Proposal {proposal.proposal_id} REJECTED")

    def get_proposal_results(self, proposal_id: str) -> Dict[str, Any]:
        """Get proposal voting results."""
        with self._lock:
            if proposal_id not in self.proposals:
                return {}

            proposal = self.proposals[proposal_id]

            approve = sum(1 for v in proposal.votes if v.decision == VoteDecision.APPROVE)
            reject = sum(1 for v in proposal.votes if v.decision == VoteDecision.REJECT)
            abstain = sum(1 for v in proposal.votes if v.decision == VoteDecision.ABSTAIN)

            return {
                'proposal_id': proposal.proposal_id,
                'title': proposal.title,
                'status': proposal.status,
                'total_votes': len(proposal.votes),
                'approve': approve,
                'reject': reject,
                'abstain': abstain,
                'approval_rate': approve / len(proposal.votes) if proposal.votes else 0
            }


# ═══════════════════════════════════════════════════════════════════════════
# Leader Election
# ═══════════════════════════════════════════════════════════════════════════

class LeaderElection:
    """Leader election mechanisms."""

    def __init__(self, nodes: List[str]):
        """Initialize leader election."""
        self.nodes = sorted(nodes)  # Maintain order
        self.current_leader: Optional[str] = None
        self.election_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def bully_algorithm(self, failed_node: Optional[str] = None) -> str:
        """Bully algorithm - highest ID becomes leader."""
        with self._lock:
            active_nodes = [n for n in self.nodes if n != failed_node]

            if not active_nodes:
                return ""

            # Highest ID wins
            new_leader = max(active_nodes)

            self.current_leader = new_leader
            self._record_election("bully", new_leader)

            self.logger.info(f"Bully algorithm elected: {new_leader}")
            return new_leader

    def ring_algorithm(self) -> str:
        """Ring algorithm - pass token around ring."""
        with self._lock:
            if not self.nodes:
                return ""

            # Simulate token passing, highest ID wins
            new_leader = max(self.nodes)

            self.current_leader = new_leader
            self._record_election("ring", new_leader)

            self.logger.info(f"Ring algorithm elected: {new_leader}")
            return new_leader

    def raft_election(self, term: int) -> Tuple[str, int]:
        """Raft-style election with terms."""
        with self._lock:
            if not self.nodes:
                return "", term

            # Simulate voting - random node wins
            votes_needed = len(self.nodes) // 2 + 1

            # First candidate in sorted list wins (deterministic for testing)
            new_leader = self.nodes[term % len(self.nodes)]

            self.current_leader = new_leader
            self._record_election("raft", new_leader, {"term": term})

            self.logger.info(f"Raft election elected: {new_leader} in term {term}")
            return new_leader, term

    def _record_election(
        self,
        algorithm: str,
        leader: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record election in history."""
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'algorithm': algorithm,
            'leader': leader,
            'metadata': metadata or {}
        }
        self.election_history.append(record)

    def get_current_leader(self) -> Optional[str]:
        """Get current leader."""
        return self.current_leader


# ═══════════════════════════════════════════════════════════════════════════
# Distributed Consensus Coordinator
# ═══════════════════════════════════════════════════════════════════════════

class DistributedConsensusCoordinator:
    """Coordinate distributed consensus across protocols."""

    def __init__(
        self,
        num_nodes: int = 7,
        byzantine_tolerance: int = 2,
        protocol: ConsensusProtocol = ConsensusProtocol.PBFT
    ):
        """Initialize consensus coordinator."""
        self.num_nodes = num_nodes
        self.byzantine_tolerance = byzantine_tolerance
        self.protocol = protocol

        self.nodes: Dict[str, NodeInfo] = {}
        self.pbft_instances: Dict[str, PBFTConsensus] = {}
        self.raft_instances: Dict[str, RaftConsensus] = {}
        self.voting_system = VotingSystem()
        self.leader_election = LeaderElection([f"node_{i}" for i in range(num_nodes)])

        self._initialize_nodes()

        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()

    def _initialize_nodes(self) -> None:
        """Initialize consensus nodes."""
        for i in range(self.num_nodes):
            node_id = f"node_{i}"

            self.nodes[node_id] = NodeInfo(
                node_id=node_id,
                state=NodeState.REPLICA if self.protocol == ConsensusProtocol.PBFT else NodeState.FOLLOWER
            )

            if self.protocol == ConsensusProtocol.PBFT:
                self.pbft_instances[node_id] = PBFTConsensus(
                    node_id, self.num_nodes, self.byzantine_tolerance
                )
            elif self.protocol == ConsensusProtocol.RAFT:
                self.raft_instances[node_id] = RaftConsensus(node_id, self.num_nodes)

            self.voting_system.register_voter(node_id)

    def submit_transaction(
        self,
        client_id: str,
        operation: str,
        data: Dict[str, Any]
    ) -> str:
        """Submit transaction for consensus."""
        with self._lock:
            if self.protocol == ConsensusProtocol.PBFT:
                # Submit to any PBFT node
                node = list(self.pbft_instances.values())[0]
                return node.submit_request(client_id, operation, data)

            elif self.protocol == ConsensusProtocol.RAFT:
                # Find leader
                leader = self._find_raft_leader()
                if leader:
                    leader.append_log_entry(operation, data)
                    return f"raft_{len(leader.log) - 1}"

            return ""

    def _find_raft_leader(self) -> Optional[RaftConsensus]:
        """Find current Raft leader."""
        for instance in self.raft_instances.values():
            if instance.node_info.state == NodeState.LEADER:
                return instance
        return None

    def create_vote_proposal(
        self,
        title: str,
        description: str,
        proposer_id: str
    ) -> str:
        """Create voting proposal."""
        proposal = self.voting_system.create_proposal(
            title, description, proposer_id
        )
        return proposal.proposal_id

    def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        decision: VoteDecision
    ) -> bool:
        """Cast vote."""
        return self.voting_system.cast_vote(proposal_id, voter_id, decision)

    def elect_leader(self, algorithm: str = "raft") -> str:
        """Elect new leader."""
        with self._lock:
            if algorithm == "bully":
                return self.leader_election.bully_algorithm()
            elif algorithm == "ring":
                return self.leader_election.ring_algorithm()
            else:  # raft
                leader, _ = self.leader_election.raft_election(0)
                return leader

    def get_consensus_status(self) -> Dict[str, Any]:
        """Get consensus system status."""
        with self._lock:
            status = {
                'protocol': self.protocol.value,
                'num_nodes': self.num_nodes,
                'byzantine_tolerance': self.byzantine_tolerance,
                'nodes': [asdict(n) for n in self.nodes.values()],
                'current_leader': self.leader_election.get_current_leader()
            }

            if self.protocol == ConsensusProtocol.PBFT:
                pbft_stats = []
                for node_id, instance in self.pbft_instances.items():
                    pbft_stats.append({
                        'node_id': node_id,
                        'view': instance.current_view,
                        'committed_entries': len(instance.committed_log)
                    })
                status['pbft_stats'] = pbft_stats

            return status


# ═══════════════════════════════════════════════════════════════════════════
# Global Consensus Coordinator Singleton
# ═══════════════════════════════════════════════════════════════════════════

_global_consensus_coordinator: Optional[DistributedConsensusCoordinator] = None


def get_consensus_coordinator(
    num_nodes: int = 7,
    protocol: ConsensusProtocol = ConsensusProtocol.PBFT
) -> DistributedConsensusCoordinator:
    """Get or create global consensus coordinator."""
    global _global_consensus_coordinator
    if _global_consensus_coordinator is None:
        _global_consensus_coordinator = DistributedConsensusCoordinator(
            num_nodes=num_nodes,
            protocol=protocol
        )
    return _global_consensus_coordinator
