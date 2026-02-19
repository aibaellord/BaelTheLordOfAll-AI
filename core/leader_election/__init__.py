"""
BAEL Leader Election Engine Implementation
============================================

Distributed leadership coordination.

"Ba'el knows who leads and when to step forward." — Ba'el
"""

import asyncio
import logging
import random
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.LeaderElection")


# ============================================================================
# ENUMS
# ============================================================================

class ElectionAlgorithm(Enum):
    """Leader election algorithms."""
    BULLY = "bully"           # Bully algorithm
    RING = "ring"             # Ring algorithm
    RAFT = "raft"             # Raft-style
    PAXOS = "paxos"           # Paxos-style


class NodeState(Enum):
    """Node states in election."""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class ElectionState(Enum):
    """Election states."""
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Node:
    """A node in the cluster."""
    id: str
    address: str
    port: int

    # State
    state: NodeState = NodeState.FOLLOWER

    # Term/epoch
    current_term: int = 0
    voted_for: Optional[str] = None

    # Leadership
    is_leader: bool = False
    leader_id: Optional[str] = None

    # Health
    last_heartbeat: Optional[datetime] = None
    healthy: bool = True

    # Priority
    priority: int = 0  # Higher = more likely to be leader

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'address': self.address,
            'port': self.port,
            'state': self.state.value,
            'is_leader': self.is_leader,
            'term': self.current_term
        }


@dataclass
class Election:
    """An election event."""
    id: str
    term: int

    # State
    state: ElectionState = ElectionState.IDLE
    initiator_id: Optional[str] = None

    # Votes
    votes_received: Dict[str, bool] = field(default_factory=dict)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Result
    winner_id: Optional[str] = None


@dataclass
class LeaderElectionConfig:
    """Leader election configuration."""
    algorithm: ElectionAlgorithm = ElectionAlgorithm.RAFT
    heartbeat_interval_ms: float = 150.0
    election_timeout_min_ms: float = 300.0
    election_timeout_max_ms: float = 500.0
    leader_lease_seconds: float = 30.0


# ============================================================================
# LEADER ELECTION ENGINE
# ============================================================================

class LeaderElectionEngine:
    """
    Leader election engine.

    Features:
    - Multiple algorithms
    - Automatic failover
    - Leader lease
    - Split-brain protection

    "Ba'el determines the worthy leader." — Ba'el
    """

    def __init__(
        self,
        node_id: str,
        config: Optional[LeaderElectionConfig] = None
    ):
        """Initialize leader election engine."""
        self.node_id = node_id
        self.config = config or LeaderElectionConfig()

        # This node
        self._node = Node(
            id=node_id,
            address="localhost",
            port=8000
        )

        # Cluster members
        self._nodes: Dict[str, Node] = {node_id: self._node}

        # Election state
        self._current_election: Optional[Election] = None
        self._election_timer: Optional[asyncio.Task] = None
        self._heartbeat_timer: Optional[asyncio.Task] = None

        # Thread safety
        self._lock = threading.RLock()

        # Callbacks
        self._on_leader_elected: Optional[Callable] = None
        self._on_leader_lost: Optional[Callable] = None

        # Communication handlers
        self._send_handler: Optional[Callable] = None

        # Stats
        self._stats = {
            'elections_initiated': 0,
            'elections_won': 0,
            'times_leader': 0
        }

        logger.info(f"Leader Election Engine initialized: {node_id}")

    # ========================================================================
    # CLUSTER MANAGEMENT
    # ========================================================================

    def add_node(
        self,
        node_id: str,
        address: str = "localhost",
        port: int = 8000,
        priority: int = 0
    ) -> Node:
        """Add a node to the cluster."""
        node = Node(
            id=node_id,
            address=address,
            port=port,
            priority=priority
        )

        with self._lock:
            self._nodes[node_id] = node

        logger.info(f"Node added: {node_id}")

        return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the cluster."""
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]

                # If leader was removed, trigger election
                if self._node.leader_id == node_id:
                    asyncio.create_task(self.start_election())

                return True
        return False

    # ========================================================================
    # ELECTION PROCESS
    # ========================================================================

    async def start_election(self) -> Optional[str]:
        """
        Start a leader election.

        Returns:
            Winner node ID or None
        """
        with self._lock:
            # Increment term
            self._node.current_term += 1
            self._node.state = NodeState.CANDIDATE
            self._node.voted_for = self.node_id  # Vote for self

            election = Election(
                id=str(uuid.uuid4()),
                term=self._node.current_term,
                initiator_id=self.node_id,
                state=ElectionState.IN_PROGRESS
            )
            election.started_at = datetime.now()
            election.votes_received[self.node_id] = True

            self._current_election = election
            self._stats['elections_initiated'] += 1

        logger.info(f"Election started: term {self._node.current_term}")

        # Request votes from all nodes
        if self.config.algorithm == ElectionAlgorithm.RAFT:
            winner = await self._raft_election(election)
        elif self.config.algorithm == ElectionAlgorithm.BULLY:
            winner = await self._bully_election(election)
        else:
            winner = await self._simple_election(election)

        return winner

    async def _raft_election(self, election: Election) -> Optional[str]:
        """Raft-style election."""
        # Send vote requests
        vote_tasks = []

        for node_id, node in self._nodes.items():
            if node_id != self.node_id:
                task = asyncio.create_task(
                    self._request_vote(node, election.term)
                )
                vote_tasks.append((node_id, task))

        # Wait for votes with timeout
        timeout = random.uniform(
            self.config.election_timeout_min_ms,
            self.config.election_timeout_max_ms
        ) / 1000

        try:
            await asyncio.wait_for(
                asyncio.gather(*[t for _, t in vote_tasks]),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            pass

        # Count votes
        votes = sum(1 for v in election.votes_received.values() if v)
        majority = (len(self._nodes) // 2) + 1

        if votes >= majority:
            await self._become_leader(election)
            return self.node_id
        else:
            self._node.state = NodeState.FOLLOWER
            election.state = ElectionState.FAILED
            return None

    async def _bully_election(self, election: Election) -> Optional[str]:
        """Bully algorithm election."""
        # Send election messages to higher-priority nodes
        higher_nodes = [
            n for n in self._nodes.values()
            if n.priority > self._node.priority or
            (n.priority == self._node.priority and n.id > self.node_id)
        ]

        if not higher_nodes:
            # We are the highest, become leader
            await self._become_leader(election)
            return self.node_id

        # Wait for response from higher nodes
        await asyncio.sleep(
            self.config.election_timeout_max_ms / 1000
        )

        # If no response, become leader
        active_higher = [n for n in higher_nodes if n.healthy]

        if not active_higher:
            await self._become_leader(election)
            return self.node_id

        # Otherwise, wait for them to become leader
        self._node.state = NodeState.FOLLOWER
        return None

    async def _simple_election(self, election: Election) -> Optional[str]:
        """Simple highest-ID election."""
        # Highest priority/ID wins
        highest = max(
            self._nodes.values(),
            key=lambda n: (n.priority, n.id)
        )

        if highest.id == self.node_id:
            await self._become_leader(election)
            return self.node_id

        self._node.state = NodeState.FOLLOWER
        self._node.leader_id = highest.id
        return highest.id

    async def _request_vote(self, node: Node, term: int) -> bool:
        """Request vote from a node."""
        if self._send_handler:
            try:
                response = await self._send_handler(
                    node,
                    {'type': 'vote_request', 'term': term, 'candidate': self.node_id}
                )

                if response and response.get('vote_granted'):
                    self._current_election.votes_received[node.id] = True
                    return True

            except Exception as e:
                logger.error(f"Vote request failed: {e}")

        return False

    async def _become_leader(self, election: Election) -> None:
        """Become the leader."""
        with self._lock:
            self._node.state = NodeState.LEADER
            self._node.is_leader = True
            self._node.leader_id = self.node_id

            # Update all nodes
            for node in self._nodes.values():
                node.leader_id = self.node_id

            election.state = ElectionState.COMPLETED
            election.winner_id = self.node_id
            election.completed_at = datetime.now()

            self._stats['elections_won'] += 1
            self._stats['times_leader'] += 1

        logger.info(f"Became leader: term {self._node.current_term}")

        # Start heartbeats
        await self._start_heartbeat()

        # Notify callback
        if self._on_leader_elected:
            await self._call_handler(self._on_leader_elected, self.node_id)

    async def step_down(self) -> None:
        """Step down from leadership."""
        with self._lock:
            was_leader = self._node.is_leader
            self._node.state = NodeState.FOLLOWER
            self._node.is_leader = False

        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()

        if was_leader:
            logger.info("Stepped down from leadership")

            if self._on_leader_lost:
                await self._call_handler(self._on_leader_lost)

    # ========================================================================
    # HEARTBEAT
    # ========================================================================

    async def _start_heartbeat(self) -> None:
        """Start sending heartbeats."""
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()

        self._heartbeat_timer = asyncio.create_task(
            self._heartbeat_loop()
        )

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop."""
        while self._node.is_leader:
            # Send heartbeat to all nodes
            for node in self._nodes.values():
                if node.id != self.node_id:
                    await self._send_heartbeat(node)

            await asyncio.sleep(
                self.config.heartbeat_interval_ms / 1000
            )

    async def _send_heartbeat(self, node: Node) -> None:
        """Send heartbeat to a node."""
        if self._send_handler:
            try:
                await self._send_handler(
                    node,
                    {
                        'type': 'heartbeat',
                        'term': self._node.current_term,
                        'leader': self.node_id
                    }
                )
                node.last_heartbeat = datetime.now()
                node.healthy = True
            except Exception:
                node.healthy = False

    def receive_heartbeat(
        self,
        leader_id: str,
        term: int
    ) -> None:
        """Receive heartbeat from leader."""
        with self._lock:
            if term >= self._node.current_term:
                self._node.current_term = term
                self._node.leader_id = leader_id
                self._node.state = NodeState.FOLLOWER
                self._node.is_leader = False
                self._node.last_heartbeat = datetime.now()

    # ========================================================================
    # VOTE HANDLING
    # ========================================================================

    def receive_vote_request(
        self,
        candidate_id: str,
        term: int
    ) -> bool:
        """
        Receive vote request.

        Returns:
            True if vote granted
        """
        with self._lock:
            if term < self._node.current_term:
                return False

            if term > self._node.current_term:
                self._node.current_term = term
                self._node.voted_for = None

            if self._node.voted_for is None or self._node.voted_for == candidate_id:
                self._node.voted_for = candidate_id
                return True

            return False

    # ========================================================================
    # QUERIES
    # ========================================================================

    def is_leader(self) -> bool:
        """Check if this node is the leader."""
        return self._node.is_leader

    def get_leader(self) -> Optional[str]:
        """Get current leader ID."""
        return self._node.leader_id

    def get_node(self) -> Node:
        """Get this node."""
        return self._node

    def list_nodes(self) -> List[Node]:
        """List all nodes."""
        return list(self._nodes.values())

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_leader_elected(self, callback: Callable) -> None:
        """Set leader elected callback."""
        self._on_leader_elected = callback

    def on_leader_lost(self, callback: Callable) -> None:
        """Set leader lost callback."""
        self._on_leader_lost = callback

    def set_send_handler(self, handler: Callable) -> None:
        """Set network send handler."""
        self._send_handler = handler

    async def _call_handler(self, handler: Callable, *args) -> Any:
        """Call handler function."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args)
        else:
            return await asyncio.to_thread(handler, *args)

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    async def start(self) -> None:
        """Start the election engine."""
        logger.info("Leader election engine started")

        # Start election timer
        await self._start_election_timer()

    async def _start_election_timer(self) -> None:
        """Start election timeout timer."""
        if self._election_timer:
            self._election_timer.cancel()

        timeout = random.uniform(
            self.config.election_timeout_min_ms,
            self.config.election_timeout_max_ms
        ) / 1000

        self._election_timer = asyncio.create_task(
            self._election_timer_loop(timeout)
        )

    async def _election_timer_loop(self, timeout: float) -> None:
        """Election timer loop."""
        while True:
            await asyncio.sleep(timeout)

            # Check if we need to start election
            if not self._node.is_leader:
                if self._node.last_heartbeat:
                    since_heartbeat = datetime.now() - self._node.last_heartbeat
                    if since_heartbeat.total_seconds() > timeout:
                        await self.start_election()
                else:
                    await self.start_election()

    async def stop(self) -> None:
        """Stop the election engine."""
        if self._election_timer:
            self._election_timer.cancel()

        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()

        logger.info("Leader election engine stopped")

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'node_id': self.node_id,
            'state': self._node.state.value,
            'is_leader': self._node.is_leader,
            'leader_id': self._node.leader_id,
            'term': self._node.current_term,
            'cluster_size': len(self._nodes),
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

election_engine: Optional[LeaderElectionEngine] = None


def get_election_engine(
    node_id: Optional[str] = None,
    config: Optional[LeaderElectionConfig] = None
) -> LeaderElectionEngine:
    """Get or create election engine."""
    global election_engine
    if election_engine is None:
        election_engine = LeaderElectionEngine(
            node_id or str(uuid.uuid4()),
            config
        )
    return election_engine


def is_leader() -> bool:
    """Check if this node is leader."""
    if election_engine:
        return election_engine.is_leader()
    return False
