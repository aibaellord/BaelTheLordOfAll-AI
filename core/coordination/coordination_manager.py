#!/usr/bin/env python3
"""
BAEL - Coordination Manager
Advanced multi-agent coordination and synchronization.

Features:
- Distributed coordination
- Consensus protocols
- Leader election
- Barrier synchronization
- Distributed locks
- Task allocation
- Load balancing
- Conflict resolution
"""

import asyncio
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class AgentState(Enum):
    """States of a coordinated agent."""
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


class LockState(Enum):
    """States of a distributed lock."""
    FREE = "free"
    HELD = "held"
    WAITING = "waiting"


class ConsensusState(Enum):
    """States of consensus."""
    PROPOSAL = "proposal"
    VOTING = "voting"
    COMMIT = "commit"
    ABORT = "abort"


class ElectionState(Enum):
    """States of leader election."""
    CANDIDATE = "candidate"
    LEADER = "leader"
    FOLLOWER = "follower"


class AllocationStrategy(Enum):
    """Task allocation strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CAPABILITY_BASED = "capability_based"
    AUCTION = "auction"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    PRIORITY = "priority"
    TIMESTAMP = "timestamp"
    VOTING = "voting"
    ARBITRATION = "arbitration"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Agent:
    """A coordinated agent."""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    state: AgentState = AgentState.IDLE
    capabilities: Set[str] = field(default_factory=set)
    load: float = 0.0
    priority: int = 0
    last_heartbeat: float = field(default_factory=time.time)


@dataclass
class Task:
    """A task for allocation."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    required_capabilities: Set[str] = field(default_factory=set)
    priority: int = 0
    deadline: Optional[float] = None
    assigned_agent: Optional[str] = None
    status: str = "pending"


@dataclass
class Lock:
    """A distributed lock."""
    lock_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource: str = ""
    state: LockState = LockState.FREE
    holder: Optional[str] = None
    waiters: List[str] = field(default_factory=list)
    acquired_at: Optional[float] = None


@dataclass
class Proposal:
    """A consensus proposal."""
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    value: Any = None
    proposer: str = ""
    votes_for: Set[str] = field(default_factory=set)
    votes_against: Set[str] = field(default_factory=set)
    state: ConsensusState = ConsensusState.PROPOSAL
    timestamp: float = field(default_factory=time.time)


@dataclass
class Barrier:
    """A synchronization barrier."""
    barrier_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    expected_count: int = 0
    arrived: Set[str] = field(default_factory=set)
    released: bool = False


@dataclass
class Conflict:
    """A conflict between agents."""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agents: List[str] = field(default_factory=list)
    resource: str = ""
    resolution: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# LOCK MANAGER
# =============================================================================

class LockManager:
    """Manage distributed locks."""

    def __init__(self):
        self._locks: Dict[str, Lock] = {}
        self._agent_locks: Dict[str, Set[str]] = defaultdict(set)

    def create_lock(self, resource: str) -> Lock:
        """Create a new lock."""
        lock = Lock(resource=resource)
        self._locks[lock.lock_id] = lock
        return lock

    def acquire(
        self,
        lock_id: str,
        agent_id: str,
        timeout: Optional[float] = None
    ) -> bool:
        """Try to acquire a lock."""
        lock = self._locks.get(lock_id)
        if not lock:
            return False

        if lock.state == LockState.FREE:
            lock.state = LockState.HELD
            lock.holder = agent_id
            lock.acquired_at = time.time()
            self._agent_locks[agent_id].add(lock_id)
            return True

        if lock.holder == agent_id:
            return True  # Already held

        # Add to waiters
        if agent_id not in lock.waiters:
            lock.waiters.append(agent_id)

        return False

    def release(self, lock_id: str, agent_id: str) -> bool:
        """Release a lock."""
        lock = self._locks.get(lock_id)
        if not lock:
            return False

        if lock.holder != agent_id:
            return False

        lock.state = LockState.FREE
        lock.holder = None
        lock.acquired_at = None
        self._agent_locks[agent_id].discard(lock_id)

        # Grant to next waiter
        if lock.waiters:
            next_agent = lock.waiters.pop(0)
            lock.state = LockState.HELD
            lock.holder = next_agent
            lock.acquired_at = time.time()
            self._agent_locks[next_agent].add(lock_id)

        return True

    def get_holder(self, lock_id: str) -> Optional[str]:
        """Get the current holder of a lock."""
        lock = self._locks.get(lock_id)
        return lock.holder if lock else None

    def release_all(self, agent_id: str) -> int:
        """Release all locks held by an agent."""
        locks_released = 0
        for lock_id in list(self._agent_locks[agent_id]):
            if self.release(lock_id, agent_id):
                locks_released += 1
        return locks_released


# =============================================================================
# CONSENSUS MANAGER
# =============================================================================

class ConsensusManager:
    """Manage consensus protocols."""

    def __init__(self, quorum_ratio: float = 0.5):
        self._proposals: Dict[str, Proposal] = {}
        self._quorum_ratio = quorum_ratio

    def propose(
        self,
        value: Any,
        proposer: str
    ) -> Proposal:
        """Create a new proposal."""
        proposal = Proposal(value=value, proposer=proposer)
        self._proposals[proposal.proposal_id] = proposal
        return proposal

    def vote(
        self,
        proposal_id: str,
        voter: str,
        vote: bool
    ) -> bool:
        """Vote on a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.state != ConsensusState.PROPOSAL:
            return False

        if vote:
            proposal.votes_for.add(voter)
            proposal.votes_against.discard(voter)
        else:
            proposal.votes_against.add(voter)
            proposal.votes_for.discard(voter)

        return True

    def check_consensus(
        self,
        proposal_id: str,
        total_agents: int
    ) -> ConsensusState:
        """Check if consensus is reached."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return ConsensusState.ABORT

        quorum = int(total_agents * self._quorum_ratio) + 1

        if len(proposal.votes_for) >= quorum:
            proposal.state = ConsensusState.COMMIT
            return ConsensusState.COMMIT

        if len(proposal.votes_against) >= quorum:
            proposal.state = ConsensusState.ABORT
            return ConsensusState.ABORT

        return ConsensusState.VOTING

    def get_decision(
        self,
        proposal_id: str
    ) -> Tuple[Optional[Any], ConsensusState]:
        """Get the decision for a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None, ConsensusState.ABORT

        if proposal.state == ConsensusState.COMMIT:
            return proposal.value, ConsensusState.COMMIT

        return None, proposal.state


# =============================================================================
# LEADER ELECTION
# =============================================================================

class LeaderElection:
    """Leader election protocol."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._leader: Optional[str] = None
        self._term: int = 0
        self._votes: Dict[str, str] = {}  # voter -> candidate

    def register_agent(self, agent: Agent) -> None:
        """Register an agent for election."""
        self._agents[agent.agent_id] = agent

    def start_election(self, candidate_id: str) -> bool:
        """Start a new election."""
        if candidate_id not in self._agents:
            return False

        self._term += 1
        self._votes.clear()
        self._votes[candidate_id] = candidate_id  # Vote for self

        return True

    def vote(
        self,
        voter_id: str,
        candidate_id: str
    ) -> bool:
        """Vote for a candidate."""
        if voter_id in self._votes:
            return False  # Already voted

        self._votes[voter_id] = candidate_id
        return True

    def check_winner(self) -> Optional[str]:
        """Check if there's a winner."""
        total_agents = len(self._agents)
        needed = total_agents // 2 + 1

        vote_counts: Dict[str, int] = defaultdict(int)
        for candidate in self._votes.values():
            vote_counts[candidate] += 1

        for candidate, count in vote_counts.items():
            if count >= needed:
                self._leader = candidate
                return candidate

        return None

    def get_leader(self) -> Optional[str]:
        """Get current leader."""
        return self._leader

    def is_leader(self, agent_id: str) -> bool:
        """Check if agent is leader."""
        return self._leader == agent_id

    def bully_election(self) -> Optional[str]:
        """Perform bully algorithm election."""
        # Find agent with highest priority
        if not self._agents:
            return None

        best = max(
            self._agents.values(),
            key=lambda a: a.priority
        )
        self._leader = best.agent_id
        return self._leader


# =============================================================================
# BARRIER SYNCHRONIZATION
# =============================================================================

class BarrierManager:
    """Manage synchronization barriers."""

    def __init__(self):
        self._barriers: Dict[str, Barrier] = {}
        self._callbacks: Dict[str, Callable[[], None]] = {}

    def create_barrier(
        self,
        name: str,
        count: int,
        callback: Optional[Callable[[], None]] = None
    ) -> Barrier:
        """Create a new barrier."""
        barrier = Barrier(name=name, expected_count=count)
        self._barriers[barrier.barrier_id] = barrier

        if callback:
            self._callbacks[barrier.barrier_id] = callback

        return barrier

    def arrive(
        self,
        barrier_id: str,
        agent_id: str
    ) -> Tuple[bool, bool]:
        """Arrive at a barrier. Returns (success, released)."""
        barrier = self._barriers.get(barrier_id)
        if not barrier or barrier.released:
            return False, False

        barrier.arrived.add(agent_id)

        if len(barrier.arrived) >= barrier.expected_count:
            barrier.released = True

            if barrier_id in self._callbacks:
                self._callbacks[barrier_id]()

            return True, True

        return True, False

    def is_released(self, barrier_id: str) -> bool:
        """Check if barrier is released."""
        barrier = self._barriers.get(barrier_id)
        return barrier.released if barrier else False

    def get_waiting_count(self, barrier_id: str) -> int:
        """Get number of agents waiting."""
        barrier = self._barriers.get(barrier_id)
        return len(barrier.arrived) if barrier else 0

    def reset(self, barrier_id: str) -> bool:
        """Reset a barrier."""
        barrier = self._barriers.get(barrier_id)
        if not barrier:
            return False

        barrier.arrived.clear()
        barrier.released = False
        return True


# =============================================================================
# TASK ALLOCATOR
# =============================================================================

class TaskAllocator:
    """Allocate tasks to agents."""

    def __init__(self, strategy: AllocationStrategy = AllocationStrategy.LEAST_LOADED):
        self._strategy = strategy
        self._tasks: Dict[str, Task] = {}
        self._agents: Dict[str, Agent] = {}
        self._round_robin_idx = 0

    def register_agent(self, agent: Agent) -> None:
        """Register an agent."""
        self._agents[agent.agent_id] = agent

    def add_task(self, task: Task) -> None:
        """Add a task."""
        self._tasks[task.task_id] = task

    def allocate(self, task_id: str) -> Optional[str]:
        """Allocate a task to an agent."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        if self._strategy == AllocationStrategy.ROUND_ROBIN:
            return self._allocate_round_robin(task)
        elif self._strategy == AllocationStrategy.LEAST_LOADED:
            return self._allocate_least_loaded(task)
        elif self._strategy == AllocationStrategy.CAPABILITY_BASED:
            return self._allocate_capability_based(task)
        elif self._strategy == AllocationStrategy.AUCTION:
            return self._allocate_auction(task)

        return None

    def _allocate_round_robin(self, task: Task) -> Optional[str]:
        """Round-robin allocation."""
        agents = list(self._agents.values())
        if not agents:
            return None

        agent = agents[self._round_robin_idx % len(agents)]
        self._round_robin_idx += 1

        task.assigned_agent = agent.agent_id
        task.status = "assigned"
        agent.load += 1

        return agent.agent_id

    def _allocate_least_loaded(self, task: Task) -> Optional[str]:
        """Allocate to least loaded agent."""
        available = [a for a in self._agents.values() if a.state == AgentState.IDLE]
        if not available:
            available = list(self._agents.values())

        if not available:
            return None

        agent = min(available, key=lambda a: a.load)
        task.assigned_agent = agent.agent_id
        task.status = "assigned"
        agent.load += 1

        return agent.agent_id

    def _allocate_capability_based(self, task: Task) -> Optional[str]:
        """Allocate based on capabilities."""
        capable = []

        for agent in self._agents.values():
            if task.required_capabilities <= agent.capabilities:
                capable.append(agent)

        if not capable:
            return None

        # Choose least loaded among capable
        agent = min(capable, key=lambda a: a.load)
        task.assigned_agent = agent.agent_id
        task.status = "assigned"
        agent.load += 1

        return agent.agent_id

    def _allocate_auction(self, task: Task) -> Optional[str]:
        """Auction-based allocation."""
        # Simple auction: agents bid based on inverse load
        bids: List[Tuple[str, float]] = []

        for agent in self._agents.values():
            if task.required_capabilities <= agent.capabilities:
                bid = 1.0 / (1.0 + agent.load)
                bids.append((agent.agent_id, bid))

        if not bids:
            return None

        # Winner is highest bidder
        winner_id, _ = max(bids, key=lambda x: x[1])

        task.assigned_agent = winner_id
        task.status = "assigned"
        self._agents[winner_id].load += 1

        return winner_id

    def complete_task(self, task_id: str) -> bool:
        """Mark task as complete."""
        task = self._tasks.get(task_id)
        if not task or not task.assigned_agent:
            return False

        agent = self._agents.get(task.assigned_agent)
        if agent:
            agent.load = max(0, agent.load - 1)

        task.status = "completed"
        return True


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver:
    """Resolve conflicts between agents."""

    def __init__(self, strategy: ConflictResolution = ConflictResolution.PRIORITY):
        self._strategy = strategy
        self._conflicts: Dict[str, Conflict] = {}
        self._agents: Dict[str, Agent] = {}

    def register_agent(self, agent: Agent) -> None:
        """Register an agent."""
        self._agents[agent.agent_id] = agent

    def detect_conflict(
        self,
        agent_ids: List[str],
        resource: str
    ) -> Conflict:
        """Detect a conflict."""
        conflict = Conflict(agents=agent_ids, resource=resource)
        self._conflicts[conflict.conflict_id] = conflict
        return conflict

    def resolve(self, conflict_id: str) -> Optional[str]:
        """Resolve a conflict and return winner."""
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            return None

        if self._strategy == ConflictResolution.PRIORITY:
            return self._resolve_priority(conflict)
        elif self._strategy == ConflictResolution.TIMESTAMP:
            return self._resolve_timestamp(conflict)
        elif self._strategy == ConflictResolution.VOTING:
            return self._resolve_voting(conflict)
        elif self._strategy == ConflictResolution.ARBITRATION:
            return self._resolve_arbitration(conflict)

        return None

    def _resolve_priority(self, conflict: Conflict) -> Optional[str]:
        """Resolve by agent priority."""
        agents = [self._agents.get(a) for a in conflict.agents]
        agents = [a for a in agents if a is not None]

        if not agents:
            return None

        winner = max(agents, key=lambda a: a.priority)
        conflict.resolution = winner.agent_id
        return winner.agent_id

    def _resolve_timestamp(self, conflict: Conflict) -> Optional[str]:
        """Resolve by timestamp (first come first served)."""
        agents = [self._agents.get(a) for a in conflict.agents]
        agents = [a for a in agents if a is not None]

        if not agents:
            return None

        winner = min(agents, key=lambda a: a.last_heartbeat)
        conflict.resolution = winner.agent_id
        return winner.agent_id

    def _resolve_voting(self, conflict: Conflict) -> Optional[str]:
        """Resolve by voting among agents."""
        # Simple voting: each agent votes for agent with highest priority
        votes: Dict[str, int] = defaultdict(int)

        for agent in self._agents.values():
            if agent.agent_id not in conflict.agents:
                best = max(
                    conflict.agents,
                    key=lambda a: self._agents.get(a, Agent()).priority
                )
                votes[best] += 1

        if votes:
            winner = max(votes, key=lambda x: votes[x])
            conflict.resolution = winner
            return winner

        return self._resolve_priority(conflict)

    def _resolve_arbitration(self, conflict: Conflict) -> Optional[str]:
        """Random arbitration."""
        if not conflict.agents:
            return None

        winner = random.choice(conflict.agents)
        conflict.resolution = winner
        return winner


# =============================================================================
# COORDINATION MANAGER
# =============================================================================

class CoordinationManager:
    """
    Coordination Manager for BAEL.

    Advanced multi-agent coordination and synchronization.
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._lock_manager = LockManager()
        self._consensus_manager = ConsensusManager()
        self._leader_election = LeaderElection()
        self._barrier_manager = BarrierManager()
        self._task_allocator = TaskAllocator()
        self._conflict_resolver = ConflictResolver()

    # -------------------------------------------------------------------------
    # AGENT MANAGEMENT
    # -------------------------------------------------------------------------

    def register_agent(
        self,
        name: str,
        capabilities: Optional[Set[str]] = None,
        priority: int = 0
    ) -> Agent:
        """Register a new agent."""
        agent = Agent(
            name=name,
            capabilities=capabilities or set(),
            priority=priority
        )
        self._agents[agent.agent_id] = agent

        # Register with components
        self._leader_election.register_agent(agent)
        self._task_allocator.register_agent(agent)
        self._conflict_resolver.register_agent(agent)

        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent."""
        return self._agents.get(agent_id)

    def update_heartbeat(self, agent_id: str) -> None:
        """Update agent heartbeat."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.last_heartbeat = time.time()

    def set_agent_state(
        self,
        agent_id: str,
        state: AgentState
    ) -> bool:
        """Set agent state."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.state = state
        return True

    # -------------------------------------------------------------------------
    # DISTRIBUTED LOCKS
    # -------------------------------------------------------------------------

    def create_lock(self, resource: str) -> Lock:
        """Create a distributed lock."""
        return self._lock_manager.create_lock(resource)

    def acquire_lock(
        self,
        lock_id: str,
        agent_id: str
    ) -> bool:
        """Acquire a lock."""
        return self._lock_manager.acquire(lock_id, agent_id)

    def release_lock(
        self,
        lock_id: str,
        agent_id: str
    ) -> bool:
        """Release a lock."""
        return self._lock_manager.release(lock_id, agent_id)

    # -------------------------------------------------------------------------
    # CONSENSUS
    # -------------------------------------------------------------------------

    def propose(
        self,
        value: Any,
        proposer: str
    ) -> Proposal:
        """Create a consensus proposal."""
        return self._consensus_manager.propose(value, proposer)

    def vote_on_proposal(
        self,
        proposal_id: str,
        voter: str,
        vote: bool
    ) -> bool:
        """Vote on a proposal."""
        return self._consensus_manager.vote(proposal_id, voter, vote)

    def check_consensus(
        self,
        proposal_id: str
    ) -> ConsensusState:
        """Check consensus status."""
        return self._consensus_manager.check_consensus(
            proposal_id, len(self._agents)
        )

    # -------------------------------------------------------------------------
    # LEADER ELECTION
    # -------------------------------------------------------------------------

    def start_election(self, candidate_id: str) -> bool:
        """Start leader election."""
        return self._leader_election.start_election(candidate_id)

    def vote_for_leader(
        self,
        voter_id: str,
        candidate_id: str
    ) -> bool:
        """Vote in election."""
        return self._leader_election.vote(voter_id, candidate_id)

    def get_leader(self) -> Optional[str]:
        """Get current leader."""
        return self._leader_election.get_leader()

    def elect_leader_bully(self) -> Optional[str]:
        """Elect leader using bully algorithm."""
        return self._leader_election.bully_election()

    # -------------------------------------------------------------------------
    # BARRIERS
    # -------------------------------------------------------------------------

    def create_barrier(
        self,
        name: str,
        count: int
    ) -> Barrier:
        """Create a synchronization barrier."""
        return self._barrier_manager.create_barrier(name, count)

    def arrive_at_barrier(
        self,
        barrier_id: str,
        agent_id: str
    ) -> Tuple[bool, bool]:
        """Arrive at barrier."""
        return self._barrier_manager.arrive(barrier_id, agent_id)

    def is_barrier_released(self, barrier_id: str) -> bool:
        """Check if barrier is released."""
        return self._barrier_manager.is_released(barrier_id)

    # -------------------------------------------------------------------------
    # TASK ALLOCATION
    # -------------------------------------------------------------------------

    def add_task(
        self,
        name: str,
        required_capabilities: Optional[Set[str]] = None,
        priority: int = 0
    ) -> Task:
        """Add a task for allocation."""
        task = Task(
            name=name,
            required_capabilities=required_capabilities or set(),
            priority=priority
        )
        self._task_allocator.add_task(task)
        return task

    def allocate_task(self, task_id: str) -> Optional[str]:
        """Allocate a task."""
        return self._task_allocator.allocate(task_id)

    def complete_task(self, task_id: str) -> bool:
        """Mark task complete."""
        return self._task_allocator.complete_task(task_id)

    def set_allocation_strategy(
        self,
        strategy: AllocationStrategy
    ) -> None:
        """Set allocation strategy."""
        self._task_allocator._strategy = strategy

    # -------------------------------------------------------------------------
    # CONFLICT RESOLUTION
    # -------------------------------------------------------------------------

    def detect_conflict(
        self,
        agent_ids: List[str],
        resource: str
    ) -> Conflict:
        """Detect a conflict."""
        return self._conflict_resolver.detect_conflict(agent_ids, resource)

    def resolve_conflict(self, conflict_id: str) -> Optional[str]:
        """Resolve a conflict."""
        return self._conflict_resolver.resolve(conflict_id)

    def set_conflict_strategy(
        self,
        strategy: ConflictResolution
    ) -> None:
        """Set conflict resolution strategy."""
        self._conflict_resolver._strategy = strategy


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Coordination Manager."""
    print("=" * 70)
    print("BAEL - COORDINATION MANAGER DEMO")
    print("Advanced Multi-Agent Coordination and Synchronization")
    print("=" * 70)
    print()

    manager = CoordinationManager()

    # 1. Register Agents
    print("1. REGISTER AGENTS:")
    print("-" * 40)

    agent1 = manager.register_agent("Agent-1", {"compute", "network"}, priority=10)
    agent2 = manager.register_agent("Agent-2", {"compute", "storage"}, priority=5)
    agent3 = manager.register_agent("Agent-3", {"network", "storage"}, priority=8)

    print(f"   Registered: {agent1.name} (priority={agent1.priority})")
    print(f"   Registered: {agent2.name} (priority={agent2.priority})")
    print(f"   Registered: {agent3.name} (priority={agent3.priority})")
    print()

    # 2. Distributed Locks
    print("2. DISTRIBUTED LOCKS:")
    print("-" * 40)

    lock = manager.create_lock("database")
    print(f"   Created lock for resource: {lock.resource}")

    acquired = manager.acquire_lock(lock.lock_id, agent1.agent_id)
    print(f"   Agent-1 acquire: {acquired}")

    acquired = manager.acquire_lock(lock.lock_id, agent2.agent_id)
    print(f"   Agent-2 acquire (should be False): {acquired}")

    released = manager.release_lock(lock.lock_id, agent1.agent_id)
    print(f"   Agent-1 release: {released}")
    print()

    # 3. Consensus
    print("3. CONSENSUS PROTOCOL:")
    print("-" * 40)

    proposal = manager.propose("Upgrade to v2.0", agent1.agent_id)
    print(f"   Proposal: {proposal.value}")

    manager.vote_on_proposal(proposal.proposal_id, agent1.agent_id, True)
    manager.vote_on_proposal(proposal.proposal_id, agent2.agent_id, True)
    manager.vote_on_proposal(proposal.proposal_id, agent3.agent_id, False)

    state = manager.check_consensus(proposal.proposal_id)
    print(f"   Votes: 2 for, 1 against")
    print(f"   Consensus state: {state.value}")
    print()

    # 4. Leader Election
    print("4. LEADER ELECTION:")
    print("-" * 40)

    leader = manager.elect_leader_bully()
    print(f"   Bully election winner: Agent with ID ending ...{leader[-6:]}")

    leader_agent = manager.get_agent(leader)
    if leader_agent:
        print(f"   Leader: {leader_agent.name} (priority={leader_agent.priority})")
    print()

    # 5. Barrier Synchronization
    print("5. BARRIER SYNCHRONIZATION:")
    print("-" * 40)

    barrier = manager.create_barrier("phase1", count=3)
    print(f"   Created barrier for 3 agents")

    success, released = manager.arrive_at_barrier(barrier.barrier_id, agent1.agent_id)
    print(f"   Agent-1 arrived, released: {released}")

    success, released = manager.arrive_at_barrier(barrier.barrier_id, agent2.agent_id)
    print(f"   Agent-2 arrived, released: {released}")

    success, released = manager.arrive_at_barrier(barrier.barrier_id, agent3.agent_id)
    print(f"   Agent-3 arrived, released: {released}")
    print()

    # 6. Task Allocation
    print("6. TASK ALLOCATION:")
    print("-" * 40)

    task1 = manager.add_task("Process data", {"compute"}, priority=5)
    task2 = manager.add_task("Network sync", {"network"}, priority=3)
    task3 = manager.add_task("Store results", {"storage"}, priority=4)

    print(f"   Created tasks: {task1.name}, {task2.name}, {task3.name}")

    # Capability-based allocation
    manager.set_allocation_strategy(AllocationStrategy.CAPABILITY_BASED)

    assigned1 = manager.allocate_task(task1.task_id)
    assigned2 = manager.allocate_task(task2.task_id)
    assigned3 = manager.allocate_task(task3.task_id)

    a1 = manager.get_agent(assigned1) if assigned1 else None
    a2 = manager.get_agent(assigned2) if assigned2 else None
    a3 = manager.get_agent(assigned3) if assigned3 else None

    print(f"   Task '{task1.name}' → {a1.name if a1 else 'None'}")
    print(f"   Task '{task2.name}' → {a2.name if a2 else 'None'}")
    print(f"   Task '{task3.name}' → {a3.name if a3 else 'None'}")
    print()

    # 7. Conflict Resolution
    print("7. CONFLICT RESOLUTION:")
    print("-" * 40)

    conflict = manager.detect_conflict(
        [agent1.agent_id, agent2.agent_id, agent3.agent_id],
        "shared_resource"
    )
    print(f"   Conflict detected for: {conflict.resource}")

    # Priority-based resolution
    manager.set_conflict_strategy(ConflictResolution.PRIORITY)
    winner = manager.resolve_conflict(conflict.conflict_id)
    winner_agent = manager.get_agent(winner) if winner else None
    print(f"   Winner (by priority): {winner_agent.name if winner_agent else 'None'}")
    print()

    # 8. Agent State Management
    print("8. AGENT STATE MANAGEMENT:")
    print("-" * 40)

    manager.set_agent_state(agent1.agent_id, AgentState.WORKING)
    manager.set_agent_state(agent2.agent_id, AgentState.WAITING)
    manager.set_agent_state(agent3.agent_id, AgentState.IDLE)

    for agent in [agent1, agent2, agent3]:
        print(f"   {agent.name}: {agent.state.value}")
    print()

    # 9. Load Balancing Demo
    print("9. LOAD BALANCING:")
    print("-" * 40)

    manager.set_allocation_strategy(AllocationStrategy.LEAST_LOADED)

    # Create multiple tasks
    for i in range(6):
        task = manager.add_task(f"Load-Task-{i}")
        assigned = manager.allocate_task(task.task_id)
        agent = manager.get_agent(assigned) if assigned else None
        if agent:
            print(f"   Task-{i} → {agent.name} (load={agent.load})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Coordination Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
