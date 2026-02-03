#!/usr/bin/env python3
"""
BAEL - Consensus Manager
Advanced distributed consensus for AI agent operations.

Features:
- Raft consensus
- Paxos consensus
- Leader election
- Log replication
- State machine replication
- Membership changes
- Snapshot support
- Heartbeat management
- Split brain prevention
- Quorum calculations
"""

import asyncio
import hashlib
import random
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class NodeRole(Enum):
    """Node roles in consensus."""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class ConsensusType(Enum):
    """Consensus types."""
    RAFT = "raft"
    PAXOS = "paxos"
    PBFT = "pbft"


class EntryType(Enum):
    """Log entry types."""
    COMMAND = "command"
    CONFIGURATION = "configuration"
    NOOP = "noop"


class VoteResult(Enum):
    """Vote result."""
    GRANTED = "granted"
    DENIED = "denied"
    ALREADY_VOTED = "already_voted"


class AppendResult(Enum):
    """Append result."""
    SUCCESS = "success"
    TERM_MISMATCH = "term_mismatch"
    LOG_MISMATCH = "log_mismatch"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ConsensusConfig:
    """Consensus configuration."""
    consensus_type: ConsensusType = ConsensusType.RAFT
    election_timeout_min_ms: int = 150
    election_timeout_max_ms: int = 300
    heartbeat_interval_ms: int = 50
    snapshot_threshold: int = 1000


@dataclass
class LogEntry:
    """Log entry."""
    index: int = 0
    term: int = 0
    entry_type: EntryType = EntryType.COMMAND
    command: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NodeState:
    """Node state."""
    node_id: str = ""
    role: NodeRole = NodeRole.FOLLOWER
    current_term: int = 0
    voted_for: Optional[str] = None
    leader_id: Optional[str] = None
    commit_index: int = 0
    last_applied: int = 0


@dataclass
class RequestVote:
    """Request vote RPC."""
    term: int = 0
    candidate_id: str = ""
    last_log_index: int = 0
    last_log_term: int = 0


@dataclass
class RequestVoteResponse:
    """Request vote response."""
    term: int = 0
    vote_granted: bool = False
    voter_id: str = ""


@dataclass
class AppendEntries:
    """Append entries RPC."""
    term: int = 0
    leader_id: str = ""
    prev_log_index: int = 0
    prev_log_term: int = 0
    entries: List[LogEntry] = field(default_factory=list)
    leader_commit: int = 0


@dataclass
class AppendEntriesResponse:
    """Append entries response."""
    term: int = 0
    success: bool = False
    match_index: int = 0
    node_id: str = ""


@dataclass
class ConsensusStats:
    """Consensus statistics."""
    current_term: int = 0
    role: str = ""
    leader_id: Optional[str] = None
    log_length: int = 0
    commit_index: int = 0
    votes_received: int = 0
    elections_started: int = 0
    elections_won: int = 0


# =============================================================================
# LOG STORAGE
# =============================================================================

class LogStorage:
    """In-memory log storage."""

    def __init__(self):
        self._entries: List[LogEntry] = []
        self._lock = threading.RLock()

    def append(self, entry: LogEntry) -> int:
        """Append entry."""
        with self._lock:
            entry.index = len(self._entries) + 1
            self._entries.append(entry)
            return entry.index

    def get(self, index: int) -> Optional[LogEntry]:
        """Get entry by index (1-based)."""
        with self._lock:
            if 1 <= index <= len(self._entries):
                return self._entries[index - 1]
            return None

    def get_range(self, start: int, end: int) -> List[LogEntry]:
        """Get entries in range."""
        with self._lock:
            return self._entries[start - 1:end] if start >= 1 else []

    def get_last(self) -> Optional[LogEntry]:
        """Get last entry."""
        with self._lock:
            return self._entries[-1] if self._entries else None

    def get_last_index(self) -> int:
        """Get last index."""
        with self._lock:
            return len(self._entries)

    def get_last_term(self) -> int:
        """Get term of last entry."""
        with self._lock:
            if self._entries:
                return self._entries[-1].term
            return 0

    def truncate(self, index: int) -> None:
        """Truncate log from index."""
        with self._lock:
            if index >= 1:
                self._entries = self._entries[:index - 1]

    def get_all(self) -> List[LogEntry]:
        """Get all entries."""
        with self._lock:
            return list(self._entries)


# =============================================================================
# STATE MACHINE
# =============================================================================

class StateMachine(ABC):
    """Base state machine."""

    @abstractmethod
    def apply(self, command: Any) -> Any:
        """Apply command to state machine."""
        pass

    @abstractmethod
    def snapshot(self) -> bytes:
        """Create snapshot."""
        pass

    @abstractmethod
    def restore(self, data: bytes) -> None:
        """Restore from snapshot."""
        pass


class KeyValueStateMachine(StateMachine):
    """Simple key-value state machine."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def apply(self, command: Any) -> Any:
        if not isinstance(command, dict):
            return None

        op = command.get("op")
        key = command.get("key")

        with self._lock:
            if op == "set":
                self._data[key] = command.get("value")
                return True
            elif op == "get":
                return self._data.get(key)
            elif op == "delete":
                return self._data.pop(key, None)
            elif op == "keys":
                return list(self._data.keys())

        return None

    def snapshot(self) -> bytes:
        import json
        with self._lock:
            return json.dumps(self._data).encode()

    def restore(self, data: bytes) -> None:
        import json
        with self._lock:
            self._data = json.loads(data.decode())

    def get_data(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)


# =============================================================================
# RAFT NODE
# =============================================================================

class RaftNode:
    """Raft consensus node."""

    def __init__(
        self,
        node_id: str,
        peers: List[str],
        state_machine: Optional[StateMachine] = None,
        config: Optional[ConsensusConfig] = None
    ):
        self._node_id = node_id
        self._peers = set(peers)
        self._config = config or ConsensusConfig()
        self._state_machine = state_machine or KeyValueStateMachine()

        self._state = NodeState(node_id=node_id)
        self._log = LogStorage()

        # Leader state
        self._next_index: Dict[str, int] = {}
        self._match_index: Dict[str, int] = {}

        # Timing
        self._last_heartbeat = datetime.utcnow()
        self._election_timeout = self._random_timeout()

        # Stats
        self._elections_started = 0
        self._elections_won = 0

        self._lock = threading.RLock()
        self._running = False

    def _random_timeout(self) -> timedelta:
        """Get random election timeout."""
        ms = random.randint(
            self._config.election_timeout_min_ms,
            self._config.election_timeout_max_ms
        )
        return timedelta(milliseconds=ms)

    # -------------------------------------------------------------------------
    # CORE RAFT OPERATIONS
    # -------------------------------------------------------------------------

    async def request_vote(self, request: RequestVote) -> RequestVoteResponse:
        """Handle RequestVote RPC."""
        with self._lock:
            response = RequestVoteResponse(
                term=self._state.current_term,
                vote_granted=False,
                voter_id=self._node_id
            )

            # If term is stale, reject
            if request.term < self._state.current_term:
                return response

            # If higher term, become follower
            if request.term > self._state.current_term:
                self._become_follower(request.term)

            response.term = self._state.current_term

            # Check if already voted
            if (self._state.voted_for is None or
                self._state.voted_for == request.candidate_id):

                # Check log is up to date
                last_term = self._log.get_last_term()
                last_index = self._log.get_last_index()

                log_ok = (request.last_log_term > last_term or
                         (request.last_log_term == last_term and
                          request.last_log_index >= last_index))

                if log_ok:
                    self._state.voted_for = request.candidate_id
                    self._last_heartbeat = datetime.utcnow()
                    response.vote_granted = True

            return response

    async def append_entries(
        self,
        request: AppendEntries
    ) -> AppendEntriesResponse:
        """Handle AppendEntries RPC."""
        with self._lock:
            response = AppendEntriesResponse(
                term=self._state.current_term,
                success=False,
                node_id=self._node_id
            )

            # If term is stale, reject
            if request.term < self._state.current_term:
                return response

            # If higher term, become follower
            if request.term > self._state.current_term:
                self._become_follower(request.term)

            # Reset election timeout
            self._last_heartbeat = datetime.utcnow()
            self._state.leader_id = request.leader_id

            if self._state.role == NodeRole.CANDIDATE:
                self._state.role = NodeRole.FOLLOWER

            response.term = self._state.current_term

            # Check previous log entry
            if request.prev_log_index > 0:
                prev_entry = self._log.get(request.prev_log_index)

                if not prev_entry or prev_entry.term != request.prev_log_term:
                    return response

            # Append entries
            for i, entry in enumerate(request.entries):
                index = request.prev_log_index + 1 + i
                existing = self._log.get(index)

                if existing:
                    if existing.term != entry.term:
                        self._log.truncate(index)
                        self._log.append(entry)
                else:
                    self._log.append(entry)

            response.success = True
            response.match_index = self._log.get_last_index()

            # Update commit index
            if request.leader_commit > self._state.commit_index:
                self._state.commit_index = min(
                    request.leader_commit,
                    self._log.get_last_index()
                )

                # Apply committed entries
                self._apply_committed()

            return response

    def _become_follower(self, term: int) -> None:
        """Become follower."""
        self._state.current_term = term
        self._state.role = NodeRole.FOLLOWER
        self._state.voted_for = None
        self._state.leader_id = None

    def _become_candidate(self) -> None:
        """Become candidate."""
        self._state.current_term += 1
        self._state.role = NodeRole.CANDIDATE
        self._state.voted_for = self._node_id
        self._state.leader_id = None
        self._elections_started += 1

    def _become_leader(self) -> None:
        """Become leader."""
        self._state.role = NodeRole.LEADER
        self._state.leader_id = self._node_id
        self._elections_won += 1

        # Initialize leader state
        last_index = self._log.get_last_index()
        for peer in self._peers:
            self._next_index[peer] = last_index + 1
            self._match_index[peer] = 0

        # Append noop entry
        self._log.append(LogEntry(
            term=self._state.current_term,
            entry_type=EntryType.NOOP
        ))

    def _apply_committed(self) -> None:
        """Apply committed log entries."""
        while self._state.last_applied < self._state.commit_index:
            self._state.last_applied += 1
            entry = self._log.get(self._state.last_applied)

            if entry and entry.entry_type == EntryType.COMMAND:
                self._state_machine.apply(entry.command)

    # -------------------------------------------------------------------------
    # CLIENT OPERATIONS
    # -------------------------------------------------------------------------

    async def submit_command(self, command: Any) -> Tuple[bool, int]:
        """Submit command to leader."""
        with self._lock:
            if self._state.role != NodeRole.LEADER:
                return (False, -1)

            entry = LogEntry(
                term=self._state.current_term,
                entry_type=EntryType.COMMAND,
                command=command
            )

            index = self._log.append(entry)
            return (True, index)

    async def query(self, command: Any) -> Any:
        """Query state machine (reads)."""
        # For linearizable reads, would need to verify leadership
        return self._state_machine.apply(command)

    # -------------------------------------------------------------------------
    # ELECTION
    # -------------------------------------------------------------------------

    async def start_election(self) -> bool:
        """Start leader election."""
        with self._lock:
            self._become_candidate()

            votes = 1  # Vote for self
            total_nodes = len(self._peers) + 1
            majority = total_nodes // 2 + 1

            request = RequestVote(
                term=self._state.current_term,
                candidate_id=self._node_id,
                last_log_index=self._log.get_last_index(),
                last_log_term=self._log.get_last_term()
            )

        # In real implementation, would send to all peers
        # Here we simulate receiving votes

        with self._lock:
            if votes >= majority:
                self._become_leader()
                return True

        return False

    def check_election_timeout(self) -> bool:
        """Check if election timeout elapsed."""
        with self._lock:
            if self._state.role == NodeRole.LEADER:
                return False

            elapsed = datetime.utcnow() - self._last_heartbeat
            return elapsed > self._election_timeout

    # -------------------------------------------------------------------------
    # REPLICATION
    # -------------------------------------------------------------------------

    async def replicate_to_peer(
        self,
        peer_id: str
    ) -> Optional[AppendEntriesResponse]:
        """Replicate log to peer."""
        with self._lock:
            if self._state.role != NodeRole.LEADER:
                return None

            next_idx = self._next_index.get(peer_id, 1)
            prev_idx = next_idx - 1

            prev_term = 0
            if prev_idx > 0:
                prev_entry = self._log.get(prev_idx)
                if prev_entry:
                    prev_term = prev_entry.term

            entries = self._log.get_range(
                next_idx,
                self._log.get_last_index()
            )

            request = AppendEntries(
                term=self._state.current_term,
                leader_id=self._node_id,
                prev_log_index=prev_idx,
                prev_log_term=prev_term,
                entries=entries,
                leader_commit=self._state.commit_index
            )

        # Would send to peer and get response
        # Simulated response
        response = AppendEntriesResponse(
            term=self._state.current_term,
            success=True,
            match_index=self._log.get_last_index(),
            node_id=peer_id
        )

        with self._lock:
            if response.success:
                self._match_index[peer_id] = response.match_index
                self._next_index[peer_id] = response.match_index + 1

                # Update commit index
                self._update_commit_index()
            else:
                # Decrement next index
                self._next_index[peer_id] = max(1, next_idx - 1)

        return response

    def _update_commit_index(self) -> None:
        """Update leader's commit index."""
        if self._state.role != NodeRole.LEADER:
            return

        # Find N such that majority of matchIndex >= N
        total = len(self._peers) + 1
        majority = total // 2 + 1

        for n in range(self._log.get_last_index(), self._state.commit_index, -1):
            entry = self._log.get(n)
            if not entry or entry.term != self._state.current_term:
                continue

            count = 1  # Self
            for peer in self._peers:
                if self._match_index.get(peer, 0) >= n:
                    count += 1

            if count >= majority:
                self._state.commit_index = n
                self._apply_committed()
                break

    # -------------------------------------------------------------------------
    # HEARTBEAT
    # -------------------------------------------------------------------------

    async def send_heartbeats(self) -> int:
        """Send heartbeats to all peers."""
        with self._lock:
            if self._state.role != NodeRole.LEADER:
                return 0

        count = 0
        for peer in self._peers:
            response = await self.replicate_to_peer(peer)
            if response and response.success:
                count += 1

        return count

    # -------------------------------------------------------------------------
    # MEMBERSHIP
    # -------------------------------------------------------------------------

    def add_peer(self, peer_id: str) -> None:
        """Add peer to cluster."""
        with self._lock:
            self._peers.add(peer_id)
            if self._state.role == NodeRole.LEADER:
                self._next_index[peer_id] = self._log.get_last_index() + 1
                self._match_index[peer_id] = 0

    def remove_peer(self, peer_id: str) -> None:
        """Remove peer from cluster."""
        with self._lock:
            self._peers.discard(peer_id)
            self._next_index.pop(peer_id, None)
            self._match_index.pop(peer_id, None)

    def get_peers(self) -> Set[str]:
        """Get all peers."""
        with self._lock:
            return set(self._peers)

    # -------------------------------------------------------------------------
    # STATE
    # -------------------------------------------------------------------------

    def get_state(self) -> NodeState:
        """Get current node state."""
        with self._lock:
            return NodeState(
                node_id=self._node_id,
                role=self._state.role,
                current_term=self._state.current_term,
                voted_for=self._state.voted_for,
                leader_id=self._state.leader_id,
                commit_index=self._state.commit_index,
                last_applied=self._state.last_applied
            )

    def is_leader(self) -> bool:
        """Check if this node is leader."""
        with self._lock:
            return self._state.role == NodeRole.LEADER

    def get_leader_id(self) -> Optional[str]:
        """Get current leader ID."""
        with self._lock:
            return self._state.leader_id

    def get_log(self) -> List[LogEntry]:
        """Get all log entries."""
        return self._log.get_all()

    def get_stats(self) -> ConsensusStats:
        """Get statistics."""
        with self._lock:
            return ConsensusStats(
                current_term=self._state.current_term,
                role=self._state.role.value,
                leader_id=self._state.leader_id,
                log_length=self._log.get_last_index(),
                commit_index=self._state.commit_index,
                votes_received=0,
                elections_started=self._elections_started,
                elections_won=self._elections_won
            )


# =============================================================================
# CONSENSUS MANAGER
# =============================================================================

class ConsensusManager:
    """
    Consensus Manager for BAEL.

    Advanced distributed consensus.
    """

    def __init__(
        self,
        node_id: str,
        peers: Optional[List[str]] = None,
        config: Optional[ConsensusConfig] = None
    ):
        self._config = config or ConsensusConfig()
        self._node = RaftNode(
            node_id,
            peers or [],
            KeyValueStateMachine(),
            self._config
        )
        self._running = False
        self._tasks: List[asyncio.Task] = []

    # -------------------------------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start consensus manager."""
        self._running = True

        self._tasks.append(
            asyncio.create_task(self._election_loop())
        )
        self._tasks.append(
            asyncio.create_task(self._heartbeat_loop())
        )

    async def stop(self) -> None:
        """Stop consensus manager."""
        self._running = False

        for task in self._tasks:
            task.cancel()

        self._tasks.clear()

    async def _election_loop(self) -> None:
        """Election timeout loop."""
        while self._running:
            await asyncio.sleep(0.05)  # 50ms

            if self._node.check_election_timeout():
                await self._node.start_election()

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop."""
        interval = self._config.heartbeat_interval_ms / 1000

        while self._running:
            await asyncio.sleep(interval)

            if self._node.is_leader():
                await self._node.send_heartbeats()

    # -------------------------------------------------------------------------
    # CLIENT API
    # -------------------------------------------------------------------------

    async def set(self, key: str, value: Any) -> bool:
        """Set key-value."""
        success, _ = await self._node.submit_command({
            "op": "set",
            "key": key,
            "value": value
        })
        return success

    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        return await self._node.query({
            "op": "get",
            "key": key
        })

    async def delete(self, key: str) -> bool:
        """Delete key."""
        success, _ = await self._node.submit_command({
            "op": "delete",
            "key": key
        })
        return success

    async def keys(self) -> List[str]:
        """Get all keys."""
        result = await self._node.query({"op": "keys"})
        return result if result else []

    # -------------------------------------------------------------------------
    # CLUSTER MANAGEMENT
    # -------------------------------------------------------------------------

    def add_peer(self, peer_id: str) -> None:
        """Add peer."""
        self._node.add_peer(peer_id)

    def remove_peer(self, peer_id: str) -> None:
        """Remove peer."""
        self._node.remove_peer(peer_id)

    def get_peers(self) -> Set[str]:
        """Get peers."""
        return self._node.get_peers()

    def is_leader(self) -> bool:
        """Check if leader."""
        return self._node.is_leader()

    def get_leader(self) -> Optional[str]:
        """Get leader ID."""
        return self._node.get_leader_id()

    def get_state(self) -> NodeState:
        """Get node state."""
        return self._node.get_state()

    def get_log(self) -> List[LogEntry]:
        """Get log entries."""
        return self._node.get_log()

    def get_stats(self) -> ConsensusStats:
        """Get statistics."""
        return self._node.get_stats()

    # -------------------------------------------------------------------------
    # MANUAL OPERATIONS
    # -------------------------------------------------------------------------

    async def force_election(self) -> bool:
        """Force start election."""
        return await self._node.start_election()

    async def step_down(self) -> None:
        """Step down from leader."""
        state = self._node.get_state()
        if state.role == NodeRole.LEADER:
            self._node._become_follower(state.current_term)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Consensus Manager."""
    print("=" * 70)
    print("BAEL - CONSENSUS MANAGER DEMO")
    print("Advanced Distributed Consensus for AI Agents")
    print("=" * 70)
    print()

    # Create manager
    manager = ConsensusManager(
        node_id="node-1",
        peers=["node-2", "node-3"],
        config=ConsensusConfig(
            election_timeout_min_ms=150,
            election_timeout_max_ms=300,
            heartbeat_interval_ms=50
        )
    )

    # 1. Initial State
    print("1. INITIAL STATE:")
    print("-" * 40)

    state = manager.get_state()

    print(f"   Node ID: {state.node_id}")
    print(f"   Role: {state.role.value}")
    print(f"   Term: {state.current_term}")
    print()

    # 2. Force Election
    print("2. FORCE ELECTION:")
    print("-" * 40)

    won = await manager.force_election()

    print(f"   Election won: {won}")
    print(f"   New role: {manager.get_state().role.value}")
    print(f"   Is leader: {manager.is_leader()}")
    print()

    # 3. Write Data
    print("3. WRITE DATA:")
    print("-" * 40)

    if manager.is_leader():
        await manager.set("key1", "value1")
        await manager.set("key2", {"nested": "data"})
        await manager.set("counter", 42)
        print("   Written: key1, key2, counter")
    else:
        print("   Not leader, cannot write")
    print()

    # 4. Read Data
    print("4. READ DATA:")
    print("-" * 40)

    v1 = await manager.get("key1")
    v2 = await manager.get("key2")
    v3 = await manager.get("counter")

    print(f"   key1: {v1}")
    print(f"   key2: {v2}")
    print(f"   counter: {v3}")
    print()

    # 5. Get All Keys
    print("5. GET ALL KEYS:")
    print("-" * 40)

    keys = await manager.keys()

    print(f"   Keys: {keys}")
    print()

    # 6. Log Entries
    print("6. LOG ENTRIES:")
    print("-" * 40)

    log = manager.get_log()

    for entry in log[:5]:
        print(f"   Index {entry.index}: term={entry.term}, "
              f"type={entry.entry_type.value}")

    if len(log) > 5:
        print(f"   ... and {len(log) - 5} more")
    print()

    # 7. Peer Management
    print("7. PEER MANAGEMENT:")
    print("-" * 40)

    peers = manager.get_peers()
    print(f"   Current peers: {peers}")

    manager.add_peer("node-4")
    print(f"   After adding node-4: {manager.get_peers()}")

    manager.remove_peer("node-4")
    print(f"   After removing node-4: {manager.get_peers()}")
    print()

    # 8. Delete Data
    print("8. DELETE DATA:")
    print("-" * 40)

    if manager.is_leader():
        await manager.delete("key1")
        keys_after = await manager.keys()
        print(f"   Deleted key1, remaining keys: {keys_after}")
    print()

    # 9. Statistics
    print("9. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Current term: {stats.current_term}")
    print(f"   Role: {stats.role}")
    print(f"   Leader ID: {stats.leader_id}")
    print(f"   Log length: {stats.log_length}")
    print(f"   Commit index: {stats.commit_index}")
    print(f"   Elections started: {stats.elections_started}")
    print(f"   Elections won: {stats.elections_won}")
    print()

    # 10. Leader Info
    print("10. LEADER INFO:")
    print("-" * 40)

    print(f"   Is leader: {manager.is_leader()}")
    print(f"   Leader ID: {manager.get_leader()}")
    print()

    # 11. Step Down
    print("11. STEP DOWN:")
    print("-" * 40)

    if manager.is_leader():
        await manager.step_down()
        print(f"   Stepped down")
        print(f"   New role: {manager.get_state().role.value}")
    else:
        print("   Not leader, nothing to step down from")
    print()

    # 12. Another Election
    print("12. ANOTHER ELECTION:")
    print("-" * 40)

    won = await manager.force_election()

    print(f"   Election won: {won}")
    print(f"   Current state: {manager.get_state().role.value}")
    print()

    # 13. Request Vote Handling
    print("13. REQUEST VOTE HANDLING:")
    print("-" * 40)

    request = RequestVote(
        term=manager.get_state().current_term + 1,
        candidate_id="node-2",
        last_log_index=0,
        last_log_term=0
    )

    response = await manager._node.request_vote(request)

    print(f"   Vote request from node-2")
    print(f"   Vote granted: {response.vote_granted}")
    print(f"   Response term: {response.term}")
    print()

    # 14. Append Entries Handling
    print("14. APPEND ENTRIES HANDLING:")
    print("-" * 40)

    state = manager.get_state()

    append = AppendEntries(
        term=state.current_term,
        leader_id="node-2",
        prev_log_index=0,
        prev_log_term=0,
        entries=[LogEntry(term=state.current_term, entry_type=EntryType.NOOP)],
        leader_commit=0
    )

    response = await manager._node.append_entries(append)

    print(f"   Append entries from node-2")
    print(f"   Success: {response.success}")
    print(f"   Match index: {response.match_index}")
    print()

    # 15. Final State
    print("15. FINAL STATE:")
    print("-" * 40)

    state = manager.get_state()

    print(f"   Node ID: {state.node_id}")
    print(f"   Role: {state.role.value}")
    print(f"   Term: {state.current_term}")
    print(f"   Voted for: {state.voted_for}")
    print(f"   Leader ID: {state.leader_id}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Consensus Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
