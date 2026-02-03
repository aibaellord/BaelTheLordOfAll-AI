#!/usr/bin/env python3
"""
BAEL - Consensus Engine
Distributed consensus for agents.

Features:
- Leader election
- State machine replication
- Log replication
- Quorum management
- Term management
"""

import asyncio
import hashlib
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any, Callable, Coroutine, Dict, Generic, List, Optional, Set, Tuple, TypeVar
)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class NodeState(Enum):
    """Node states in consensus."""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class EntryType(Enum):
    """Log entry types."""
    COMMAND = "command"
    CONFIG = "config"
    NOOP = "noop"


class VoteResponse(Enum):
    """Vote response types."""
    GRANTED = "granted"
    DENIED = "denied"
    ALREADY_VOTED = "already_voted"


class ConsensusState(Enum):
    """Consensus cluster states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class LogEntry:
    """A log entry."""
    entry_id: str = ""
    term: int = 0
    index: int = 0
    entry_type: EntryType = EntryType.COMMAND
    command: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())[:8]


@dataclass
class NodeConfig:
    """Node configuration."""
    node_id: str = ""
    name: str = ""
    endpoint: str = ""
    
    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(uuid.uuid4())[:8]


@dataclass
class ConsensusConfig:
    """Consensus configuration."""
    election_timeout_min: float = 0.15
    election_timeout_max: float = 0.3
    heartbeat_interval: float = 0.05
    max_log_entries: int = 1000


@dataclass
class VoteRequest:
    """Vote request message."""
    candidate_id: str = ""
    term: int = 0
    last_log_index: int = 0
    last_log_term: int = 0


@dataclass
class AppendEntriesRequest:
    """Append entries request."""
    leader_id: str = ""
    term: int = 0
    prev_log_index: int = 0
    prev_log_term: int = 0
    entries: List[LogEntry] = field(default_factory=list)
    leader_commit: int = 0


@dataclass
class AppendEntriesResponse:
    """Append entries response."""
    node_id: str = ""
    term: int = 0
    success: bool = False
    match_index: int = 0


@dataclass
class NodeStats:
    """Node statistics."""
    logs_replicated: int = 0
    votes_received: int = 0
    elections_started: int = 0
    terms_served_as_leader: int = 0


@dataclass
class ConsensusStats:
    """Consensus statistics."""
    total_nodes: int = 0
    quorum_size: int = 0
    current_term: int = 0
    leader_id: str = ""
    commits: int = 0


# =============================================================================
# STATE MACHINE
# =============================================================================

class StateMachine(ABC):
    """Abstract state machine."""
    
    @abstractmethod
    def apply(self, command: Any) -> Any:
        """Apply command to state machine."""
        pass
    
    @abstractmethod
    def snapshot(self) -> Any:
        """Get state snapshot."""
        pass
    
    @abstractmethod
    def restore(self, snapshot: Any) -> None:
        """Restore from snapshot."""
        pass


class KeyValueStateMachine(StateMachine):
    """Key-value state machine."""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
    
    def apply(self, command: Any) -> Any:
        """Apply command."""
        if not isinstance(command, dict):
            return None
        
        op = command.get("op")
        key = command.get("key")
        value = command.get("value")
        
        if op == "set":
            self._data[key] = value
            return value
        elif op == "get":
            return self._data.get(key)
        elif op == "delete":
            return self._data.pop(key, None)
        
        return None
    
    def snapshot(self) -> Any:
        """Get snapshot."""
        return dict(self._data)
    
    def restore(self, snapshot: Any) -> None:
        """Restore from snapshot."""
        if isinstance(snapshot, dict):
            self._data = dict(snapshot)


# =============================================================================
# CONSENSUS NODE
# =============================================================================

class ConsensusNode:
    """A node in consensus cluster."""
    
    def __init__(
        self,
        config: NodeConfig,
        consensus_config: Optional[ConsensusConfig] = None,
        state_machine: Optional[StateMachine] = None
    ):
        self._config = config
        self._consensus_config = consensus_config or ConsensusConfig()
        self._state_machine = state_machine or KeyValueStateMachine()
        
        self._state = NodeState.FOLLOWER
        self._current_term = 0
        self._voted_for: Optional[str] = None
        self._leader_id: Optional[str] = None
        
        self._log: List[LogEntry] = []
        self._commit_index = 0
        self._last_applied = 0
        
        self._next_index: Dict[str, int] = {}
        self._match_index: Dict[str, int] = {}
        
        self._peers: Dict[str, NodeConfig] = {}
        
        self._election_timer: Optional[asyncio.Task] = None
        self._heartbeat_timer: Optional[asyncio.Task] = None
        
        self._stats = NodeStats()
        
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
    
    def add_peer(self, peer: NodeConfig) -> None:
        """Add peer node."""
        self._peers[peer.node_id] = peer
        self._next_index[peer.node_id] = len(self._log) + 1
        self._match_index[peer.node_id] = 0
    
    def remove_peer(self, node_id: str) -> bool:
        """Remove peer node."""
        if node_id in self._peers:
            del self._peers[node_id]
            self._next_index.pop(node_id, None)
            self._match_index.pop(node_id, None)
            return True
        return False
    
    def _reset_election_timer(self) -> None:
        """Reset election timer."""
        if self._election_timer:
            self._election_timer.cancel()
        
        timeout = random.uniform(
            self._consensus_config.election_timeout_min,
            self._consensus_config.election_timeout_max
        )
        
        async def election_timeout():
            await asyncio.sleep(timeout)
            await self._start_election()
        
        self._election_timer = asyncio.create_task(election_timeout())
    
    def _stop_election_timer(self) -> None:
        """Stop election timer."""
        if self._election_timer:
            self._election_timer.cancel()
            self._election_timer = None
    
    def _start_heartbeat_timer(self) -> None:
        """Start heartbeat timer."""
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()
        
        async def heartbeat_loop():
            while self._state == NodeState.LEADER:
                await self._send_heartbeats()
                await asyncio.sleep(self._consensus_config.heartbeat_interval)
        
        self._heartbeat_timer = asyncio.create_task(heartbeat_loop())
    
    def _stop_heartbeat_timer(self) -> None:
        """Stop heartbeat timer."""
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()
            self._heartbeat_timer = None
    
    async def _start_election(self) -> None:
        """Start leader election."""
        self._state = NodeState.CANDIDATE
        self._current_term += 1
        self._voted_for = self._config.node_id
        
        self._stats.elections_started += 1
        
        votes = 1
        
        last_log_index = len(self._log)
        last_log_term = self._log[-1].term if self._log else 0
        
        request = VoteRequest(
            candidate_id=self._config.node_id,
            term=self._current_term,
            last_log_index=last_log_index,
            last_log_term=last_log_term
        )
        
        for peer_id in self._peers:
            response = await self._request_vote_from_peer(peer_id, request)
            
            if response == VoteResponse.GRANTED:
                votes += 1
                self._stats.votes_received += 1
        
        quorum = (len(self._peers) + 2) // 2
        
        if votes >= quorum:
            self._become_leader()
        else:
            self._reset_election_timer()
    
    async def _request_vote_from_peer(
        self,
        peer_id: str,
        request: VoteRequest
    ) -> VoteResponse:
        """Request vote from peer (simulated)."""
        await asyncio.sleep(0.01)
        
        if random.random() > 0.3:
            return VoteResponse.GRANTED
        return VoteResponse.DENIED
    
    def _become_leader(self) -> None:
        """Become leader."""
        self._state = NodeState.LEADER
        self._leader_id = self._config.node_id
        
        for peer_id in self._peers:
            self._next_index[peer_id] = len(self._log) + 1
            self._match_index[peer_id] = 0
        
        self._stop_election_timer()
        self._start_heartbeat_timer()
        
        self._stats.terms_served_as_leader += 1
        
        self._notify("leader_elected", self._config.node_id)
    
    def _become_follower(self, term: int) -> None:
        """Become follower."""
        self._state = NodeState.FOLLOWER
        self._current_term = term
        self._voted_for = None
        
        self._stop_heartbeat_timer()
        self._reset_election_timer()
    
    async def _send_heartbeats(self) -> None:
        """Send heartbeats to peers."""
        for peer_id in self._peers:
            request = AppendEntriesRequest(
                leader_id=self._config.node_id,
                term=self._current_term,
                prev_log_index=self._next_index[peer_id] - 1,
                prev_log_term=self._get_log_term(self._next_index[peer_id] - 1),
                entries=[],
                leader_commit=self._commit_index
            )
            
            response = await self._send_append_entries(peer_id, request)
            
            if response and response.success:
                pass
    
    async def _send_append_entries(
        self,
        peer_id: str,
        request: AppendEntriesRequest
    ) -> Optional[AppendEntriesResponse]:
        """Send append entries to peer (simulated)."""
        await asyncio.sleep(0.01)
        
        return AppendEntriesResponse(
            node_id=peer_id,
            term=self._current_term,
            success=True,
            match_index=len(self._log)
        )
    
    def _get_log_term(self, index: int) -> int:
        """Get term for log index."""
        if index <= 0 or index > len(self._log):
            return 0
        return self._log[index - 1].term
    
    async def handle_vote_request(
        self,
        request: VoteRequest
    ) -> VoteResponse:
        """Handle vote request."""
        if request.term < self._current_term:
            return VoteResponse.DENIED
        
        if request.term > self._current_term:
            self._become_follower(request.term)
        
        if self._voted_for is not None and self._voted_for != request.candidate_id:
            return VoteResponse.ALREADY_VOTED
        
        last_log_index = len(self._log)
        last_log_term = self._log[-1].term if self._log else 0
        
        if request.last_log_term < last_log_term:
            return VoteResponse.DENIED
        
        if request.last_log_term == last_log_term and request.last_log_index < last_log_index:
            return VoteResponse.DENIED
        
        self._voted_for = request.candidate_id
        self._reset_election_timer()
        
        return VoteResponse.GRANTED
    
    async def handle_append_entries(
        self,
        request: AppendEntriesRequest
    ) -> AppendEntriesResponse:
        """Handle append entries request."""
        if request.term < self._current_term:
            return AppendEntriesResponse(
                node_id=self._config.node_id,
                term=self._current_term,
                success=False
            )
        
        if request.term > self._current_term or self._state != NodeState.FOLLOWER:
            self._become_follower(request.term)
        
        self._leader_id = request.leader_id
        self._reset_election_timer()
        
        if request.prev_log_index > 0:
            if request.prev_log_index > len(self._log):
                return AppendEntriesResponse(
                    node_id=self._config.node_id,
                    term=self._current_term,
                    success=False
                )
            
            if self._get_log_term(request.prev_log_index) != request.prev_log_term:
                self._log = self._log[:request.prev_log_index - 1]
                return AppendEntriesResponse(
                    node_id=self._config.node_id,
                    term=self._current_term,
                    success=False
                )
        
        for entry in request.entries:
            if entry.index <= len(self._log):
                if self._get_log_term(entry.index) != entry.term:
                    self._log = self._log[:entry.index - 1]
                    self._log.append(entry)
            else:
                self._log.append(entry)
            
            self._stats.logs_replicated += 1
        
        if request.leader_commit > self._commit_index:
            self._commit_index = min(
                request.leader_commit,
                len(self._log)
            )
            self._apply_committed_entries()
        
        return AppendEntriesResponse(
            node_id=self._config.node_id,
            term=self._current_term,
            success=True,
            match_index=len(self._log)
        )
    
    async def propose(self, command: Any) -> Optional[LogEntry]:
        """Propose a command."""
        if self._state != NodeState.LEADER:
            return None
        
        entry = LogEntry(
            term=self._current_term,
            index=len(self._log) + 1,
            entry_type=EntryType.COMMAND,
            command=command
        )
        
        self._log.append(entry)
        
        await self._replicate_log()
        
        return entry
    
    async def _replicate_log(self) -> None:
        """Replicate log to peers."""
        for peer_id in self._peers:
            next_idx = self._next_index[peer_id]
            
            entries = self._log[next_idx - 1:]
            
            request = AppendEntriesRequest(
                leader_id=self._config.node_id,
                term=self._current_term,
                prev_log_index=next_idx - 1,
                prev_log_term=self._get_log_term(next_idx - 1),
                entries=entries,
                leader_commit=self._commit_index
            )
            
            response = await self._send_append_entries(peer_id, request)
            
            if response and response.success:
                self._next_index[peer_id] = response.match_index + 1
                self._match_index[peer_id] = response.match_index
        
        self._update_commit_index()
    
    def _update_commit_index(self) -> None:
        """Update commit index based on quorum."""
        for n in range(len(self._log), self._commit_index, -1):
            if self._get_log_term(n) != self._current_term:
                continue
            
            match_count = 1
            
            for peer_id in self._peers:
                if self._match_index.get(peer_id, 0) >= n:
                    match_count += 1
            
            quorum = (len(self._peers) + 2) // 2
            
            if match_count >= quorum:
                self._commit_index = n
                self._apply_committed_entries()
                break
    
    def _apply_committed_entries(self) -> None:
        """Apply committed entries to state machine."""
        while self._last_applied < self._commit_index:
            self._last_applied += 1
            entry = self._log[self._last_applied - 1]
            
            if entry.entry_type == EntryType.COMMAND:
                self._state_machine.apply(entry.command)
    
    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        self._callbacks[event].append(callback)
    
    def _notify(self, event: str, data: Any) -> None:
        """Notify callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception:
                pass
    
    def start(self) -> None:
        """Start the node."""
        self._reset_election_timer()
    
    def stop(self) -> None:
        """Stop the node."""
        self._stop_election_timer()
        self._stop_heartbeat_timer()
    
    @property
    def node_id(self) -> str:
        return self._config.node_id
    
    @property
    def name(self) -> str:
        return self._config.name
    
    @property
    def state(self) -> NodeState:
        return self._state
    
    @property
    def term(self) -> int:
        return self._current_term
    
    @property
    def is_leader(self) -> bool:
        return self._state == NodeState.LEADER
    
    @property
    def leader_id(self) -> Optional[str]:
        return self._leader_id
    
    @property
    def log_length(self) -> int:
        return len(self._log)
    
    @property
    def commit_index(self) -> int:
        return self._commit_index
    
    @property
    def stats(self) -> NodeStats:
        return self._stats


# =============================================================================
# CONSENSUS ENGINE
# =============================================================================

class ConsensusEngine:
    """
    Consensus Engine for BAEL.
    
    Distributed consensus for agents.
    """
    
    def __init__(self, default_config: Optional[ConsensusConfig] = None):
        self._default_config = default_config or ConsensusConfig()
        
        self._nodes: Dict[str, ConsensusNode] = {}
        self._clusters: Dict[str, List[str]] = {}
    
    # ----- Node Management -----
    
    def create_node(
        self,
        name: str,
        endpoint: str = "",
        config: Optional[ConsensusConfig] = None,
        state_machine: Optional[StateMachine] = None
    ) -> ConsensusNode:
        """Create a consensus node."""
        node_config = NodeConfig(name=name, endpoint=endpoint)
        
        config = config or self._default_config
        
        node = ConsensusNode(node_config, config, state_machine)
        self._nodes[node.node_id] = node
        
        return node
    
    def get_node(self, node_id: str) -> Optional[ConsensusNode]:
        """Get a node."""
        return self._nodes.get(node_id)
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node."""
        node = self._nodes.pop(node_id, None)
        
        if node:
            node.stop()
            return True
        
        return False
    
    def list_nodes(self) -> List[str]:
        """List node IDs."""
        return list(self._nodes.keys())
    
    # ----- Cluster Management -----
    
    def create_cluster(
        self,
        name: str,
        node_ids: List[str]
    ) -> bool:
        """Create a cluster from nodes."""
        nodes = [self._nodes.get(nid) for nid in node_ids if nid in self._nodes]
        
        if len(nodes) < 2:
            return False
        
        for node in nodes:
            for other in nodes:
                if node.node_id != other.node_id:
                    peer = NodeConfig(
                        node_id=other.node_id,
                        name=other.name
                    )
                    node.add_peer(peer)
        
        self._clusters[name] = node_ids
        
        return True
    
    def start_cluster(self, name: str) -> bool:
        """Start a cluster."""
        if name not in self._clusters:
            return False
        
        for node_id in self._clusters[name]:
            node = self._nodes.get(node_id)
            if node:
                node.start()
        
        return True
    
    def stop_cluster(self, name: str) -> bool:
        """Stop a cluster."""
        if name not in self._clusters:
            return False
        
        for node_id in self._clusters[name]:
            node = self._nodes.get(node_id)
            if node:
                node.stop()
        
        return True
    
    def get_cluster_leader(self, name: str) -> Optional[ConsensusNode]:
        """Get cluster leader."""
        if name not in self._clusters:
            return None
        
        for node_id in self._clusters[name]:
            node = self._nodes.get(node_id)
            if node and node.is_leader:
                return node
        
        return None
    
    def list_clusters(self) -> List[str]:
        """List cluster names."""
        return list(self._clusters.keys())
    
    # ----- Operations -----
    
    async def propose(
        self,
        cluster_name: str,
        command: Any
    ) -> Optional[LogEntry]:
        """Propose command to cluster."""
        leader = self.get_cluster_leader(cluster_name)
        
        if leader:
            return await leader.propose(command)
        
        return None
    
    async def set(
        self,
        cluster_name: str,
        key: str,
        value: Any
    ) -> bool:
        """Set key-value via consensus."""
        command = {"op": "set", "key": key, "value": value}
        
        entry = await self.propose(cluster_name, command)
        
        return entry is not None
    
    async def get(
        self,
        cluster_name: str,
        key: str
    ) -> Optional[Any]:
        """Get value from leader."""
        leader = self.get_cluster_leader(cluster_name)
        
        if leader and hasattr(leader._state_machine, '_data'):
            return leader._state_machine._data.get(key)
        
        return None
    
    # ----- Status -----
    
    def get_node_state(self, node_id: str) -> Optional[NodeState]:
        """Get node state."""
        node = self._nodes.get(node_id)
        return node.state if node else None
    
    def get_cluster_state(self, name: str) -> ConsensusState:
        """Get cluster state."""
        if name not in self._clusters:
            return ConsensusState.UNAVAILABLE
        
        active_count = 0
        has_leader = False
        
        for node_id in self._clusters[name]:
            node = self._nodes.get(node_id)
            if node:
                active_count += 1
                if node.is_leader:
                    has_leader = True
        
        total = len(self._clusters[name])
        quorum = (total // 2) + 1
        
        if active_count >= quorum and has_leader:
            return ConsensusState.HEALTHY
        elif active_count >= quorum:
            return ConsensusState.DEGRADED
        else:
            return ConsensusState.UNAVAILABLE
    
    def get_cluster_stats(self, name: str) -> Optional[ConsensusStats]:
        """Get cluster stats."""
        if name not in self._clusters:
            return None
        
        nodes = [self._nodes.get(nid) for nid in self._clusters[name]]
        nodes = [n for n in nodes if n]
        
        leader = None
        max_term = 0
        
        for node in nodes:
            if node.is_leader:
                leader = node
            if node.term > max_term:
                max_term = node.term
        
        return ConsensusStats(
            total_nodes=len(nodes),
            quorum_size=(len(nodes) // 2) + 1,
            current_term=max_term,
            leader_id=leader.node_id if leader else "",
            commits=leader.commit_index if leader else 0
        )
    
    # ----- Engine Stats -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        return {
            "nodes": len(self._nodes),
            "clusters": len(self._clusters)
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        cluster_info = {}
        
        for name in self._clusters:
            leader = self.get_cluster_leader(name)
            state = self.get_cluster_state(name)
            
            cluster_info[name] = {
                "nodes": len(self._clusters[name]),
                "leader": leader.name if leader else None,
                "state": state.value
            }
        
        return {"clusters": cluster_info}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Consensus Engine."""
    print("=" * 70)
    print("BAEL - CONSENSUS ENGINE DEMO")
    print("Distributed Consensus for Agents")
    print("=" * 70)
    print()
    
    engine = ConsensusEngine()
    
    # 1. Create Nodes
    print("1. CREATE NODES:")
    print("-" * 40)
    
    node1 = engine.create_node("node-1", "localhost:8001")
    node2 = engine.create_node("node-2", "localhost:8002")
    node3 = engine.create_node("node-3", "localhost:8003")
    
    print(f"   Created: {node1.name} ({node1.node_id[:8]})")
    print(f"   Created: {node2.name} ({node2.node_id[:8]})")
    print(f"   Created: {node3.name} ({node3.node_id[:8]})")
    print()
    
    # 2. Create Cluster
    print("2. CREATE CLUSTER:")
    print("-" * 40)
    
    success = engine.create_cluster(
        "main",
        [node1.node_id, node2.node_id, node3.node_id]
    )
    
    print(f"   Created cluster 'main': {success}")
    print()
    
    # 3. Start Cluster
    print("3. START CLUSTER:")
    print("-" * 40)
    
    engine.start_cluster("main")
    print(f"   Cluster started")
    
    await asyncio.sleep(0.5)
    print()
    
    # 4. Check Node States
    print("4. CHECK NODE STATES:")
    print("-" * 40)
    
    for node_id in engine.list_nodes():
        node = engine.get_node(node_id)
        print(f"   {node.name}: {node.state.value} (term {node.term})")
    print()
    
    # 5. Find Leader
    print("5. FIND LEADER:")
    print("-" * 40)
    
    leader = engine.get_cluster_leader("main")
    if leader:
        print(f"   Leader: {leader.name}")
        print(f"   Term: {leader.term}")
    else:
        print(f"   No leader elected yet")
        
        for node_id in engine.list_nodes():
            node = engine.get_node(node_id)
            if node:
                node._become_leader()
                break
        
        leader = engine.get_cluster_leader("main")
        print(f"   Force elected: {leader.name if leader else 'none'}")
    print()
    
    # 6. Propose Commands
    print("6. PROPOSE COMMANDS:")
    print("-" * 40)
    
    if leader:
        entry = await leader.propose({"op": "set", "key": "x", "value": 100})
        print(f"   Proposed set x=100: {entry.entry_id if entry else 'failed'}")
        
        entry = await leader.propose({"op": "set", "key": "y", "value": 200})
        print(f"   Proposed set y=200: {entry.entry_id if entry else 'failed'}")
    print()
    
    # 7. Log Status
    print("7. LOG STATUS:")
    print("-" * 40)
    
    for node_id in engine.list_nodes():
        node = engine.get_node(node_id)
        print(f"   {node.name}:")
        print(f"      Log length: {node.log_length}")
        print(f"      Commit index: {node.commit_index}")
    print()
    
    # 8. Cluster State
    print("8. CLUSTER STATE:")
    print("-" * 40)
    
    state = engine.get_cluster_state("main")
    print(f"   State: {state.value}")
    print()
    
    # 9. Cluster Stats
    print("9. CLUSTER STATS:")
    print("-" * 40)
    
    stats = engine.get_cluster_stats("main")
    print(f"   Total nodes: {stats.total_nodes}")
    print(f"   Quorum size: {stats.quorum_size}")
    print(f"   Current term: {stats.current_term}")
    print(f"   Commits: {stats.commits}")
    print()
    
    # 10. Node Stats
    print("10. NODE STATS:")
    print("-" * 40)
    
    for node_id in engine.list_nodes():
        node = engine.get_node(node_id)
        print(f"   {node.name}:")
        print(f"      Elections started: {node.stats.elections_started}")
        print(f"      Votes received: {node.stats.votes_received}")
        print(f"      Terms as leader: {node.stats.terms_served_as_leader}")
    print()
    
    # 11. Set/Get via Consensus
    print("11. SET/GET VIA CONSENSUS:")
    print("-" * 40)
    
    await engine.set("main", "counter", 42)
    print(f"   Set counter=42")
    
    value = await engine.get("main", "counter")
    print(f"   Get counter: {value}")
    print()
    
    # 12. List Clusters
    print("12. LIST CLUSTERS:")
    print("-" * 40)
    
    clusters = engine.list_clusters()
    for c in clusters:
        print(f"   - {c}")
    print()
    
    # 13. Engine Statistics
    print("13. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 14. Engine Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for name, info in summary["clusters"].items():
        print(f"   {name}:")
        print(f"      Nodes: {info['nodes']}")
        print(f"      Leader: {info['leader']}")
        print(f"      State: {info['state']}")
    print()
    
    # 15. Stop Cluster
    print("15. STOP CLUSTER:")
    print("-" * 40)
    
    engine.stop_cluster("main")
    print(f"   Cluster stopped")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Consensus Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
