#!/usr/bin/env python3
"""
BAEL - Gossip Protocol Manager
Advanced gossip protocol for AI agent operations.

Features:
- Gossip dissemination
- Failure detection
- Membership management
- State synchronization
- Push/Pull gossip
- Infection style propagation
- Anti-entropy
- Rumor mongering
- Node health tracking
- Cluster awareness
"""

import asyncio
import copy
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
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, TypeVar, Union)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# ENUMS
# =============================================================================

class NodeState(Enum):
    """Node states."""
    ALIVE = "alive"
    SUSPECT = "suspect"
    DEAD = "dead"
    LEFT = "left"


class GossipType(Enum):
    """Gossip message types."""
    PING = "ping"
    PONG = "pong"
    PUSH = "push"
    PULL = "pull"
    PUSH_PULL = "push_pull"
    SYNC = "sync"
    JOIN = "join"
    LEAVE = "leave"
    SUSPECT = "suspect"
    ALIVE = "alive"
    DEAD = "dead"


class DisseminationStyle(Enum):
    """Dissemination styles."""
    PUSH = "push"
    PULL = "pull"
    PUSH_PULL = "push_pull"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class GossipConfig:
    """Gossip configuration."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    gossip_interval_ms: int = 1000
    fanout: int = 3
    probe_interval_ms: int = 500
    probe_timeout_ms: int = 200
    suspect_timeout_ms: int = 5000
    dead_timeout_ms: int = 30000
    sync_interval_ms: int = 5000
    max_transmissions: int = 10
    dissemination_style: DisseminationStyle = DisseminationStyle.PUSH_PULL


@dataclass
class GossipNode:
    """Node in gossip cluster."""
    node_id: str = ""
    address: str = ""
    port: int = 0
    state: NodeState = NodeState.ALIVE
    incarnation: int = 0
    last_seen: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GossipMessage:
    """Gossip message."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: GossipType = GossipType.PUSH
    sender_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: int = 10


@dataclass
class StateEntry:
    """State entry for synchronization."""
    key: str = ""
    value: Any = None
    version: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    deleted: bool = False


@dataclass
class GossipStats:
    """Gossip statistics."""
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    gossip_rounds: int = 0
    probes_sent: int = 0
    probes_failed: int = 0
    nodes_joined: int = 0
    nodes_left: int = 0
    nodes_suspected: int = 0
    nodes_dead: int = 0


# =============================================================================
# FAILURE DETECTOR
# =============================================================================

class FailureDetector:
    """SWIM-style failure detector."""

    def __init__(
        self,
        config: GossipConfig,
        on_suspect: Optional[Callable[[str], None]] = None,
        on_dead: Optional[Callable[[str], None]] = None,
        on_alive: Optional[Callable[[str], None]] = None
    ):
        self.config = config
        self._on_suspect = on_suspect
        self._on_dead = on_dead
        self._on_alive = on_alive

        self._nodes: Dict[str, GossipNode] = {}
        self._suspect_timers: Dict[str, datetime] = {}
        self._dead_timers: Dict[str, datetime] = {}
        self._lock = threading.RLock()

        self._stats = GossipStats()

    def add_node(self, node: GossipNode) -> None:
        """Add node to detector."""
        with self._lock:
            self._nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> None:
        """Remove node from detector."""
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
            if node_id in self._suspect_timers:
                del self._suspect_timers[node_id]
            if node_id in self._dead_timers:
                del self._dead_timers[node_id]

    def report_alive(self, node_id: str) -> None:
        """Report node as alive."""
        with self._lock:
            if node_id not in self._nodes:
                return

            node = self._nodes[node_id]
            was_suspect = node.state == NodeState.SUSPECT

            node.state = NodeState.ALIVE
            node.last_seen = datetime.utcnow()

            if node_id in self._suspect_timers:
                del self._suspect_timers[node_id]

            if was_suspect and self._on_alive:
                self._on_alive(node_id)

    def report_suspect(self, node_id: str) -> None:
        """Report node as suspected."""
        with self._lock:
            if node_id not in self._nodes:
                return

            node = self._nodes[node_id]

            if node.state == NodeState.ALIVE:
                node.state = NodeState.SUSPECT
                self._suspect_timers[node_id] = datetime.utcnow()
                self._stats.nodes_suspected += 1

                if self._on_suspect:
                    self._on_suspect(node_id)

    def report_dead(self, node_id: str) -> None:
        """Report node as dead."""
        with self._lock:
            if node_id not in self._nodes:
                return

            node = self._nodes[node_id]

            if node.state in (NodeState.ALIVE, NodeState.SUSPECT):
                node.state = NodeState.DEAD
                self._dead_timers[node_id] = datetime.utcnow()
                self._stats.nodes_dead += 1

                if node_id in self._suspect_timers:
                    del self._suspect_timers[node_id]

                if self._on_dead:
                    self._on_dead(node_id)

    def check_timeouts(self) -> None:
        """Check for suspect/dead timeouts."""
        now = datetime.utcnow()

        with self._lock:
            # Check suspect timeouts
            suspect_timeout = timedelta(milliseconds=self.config.suspect_timeout_ms)
            for node_id, suspect_time in list(self._suspect_timers.items()):
                if now - suspect_time > suspect_timeout:
                    self.report_dead(node_id)

            # Check dead timeouts (cleanup)
            dead_timeout = timedelta(milliseconds=self.config.dead_timeout_ms)
            for node_id, dead_time in list(self._dead_timers.items()):
                if now - dead_time > dead_timeout:
                    del self._dead_timers[node_id]
                    if node_id in self._nodes:
                        self._nodes[node_id].state = NodeState.LEFT

    def get_alive_nodes(self) -> List[GossipNode]:
        """Get alive nodes."""
        with self._lock:
            return [
                n for n in self._nodes.values()
                if n.state == NodeState.ALIVE
            ]

    def get_all_nodes(self) -> List[GossipNode]:
        """Get all nodes."""
        with self._lock:
            return list(self._nodes.values())


# =============================================================================
# STATE STORE
# =============================================================================

class GossipStateStore:
    """CRDT-inspired state store for gossip."""

    def __init__(self):
        self._state: Dict[str, StateEntry] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get value."""
        with self._lock:
            entry = self._state.get(key)
            if entry and not entry.deleted:
                return entry.value
            return None

    def set(
        self,
        key: str,
        value: Any,
        version: Optional[int] = None
    ) -> StateEntry:
        """Set value."""
        with self._lock:
            existing = self._state.get(key)

            new_version = version
            if new_version is None:
                new_version = (existing.version + 1) if existing else 1

            entry = StateEntry(
                key=key,
                value=value,
                version=new_version,
                timestamp=datetime.utcnow(),
                deleted=False
            )

            self._state[key] = entry
            return entry

    def delete(self, key: str) -> Optional[StateEntry]:
        """Delete value (tombstone)."""
        with self._lock:
            existing = self._state.get(key)
            if existing:
                entry = StateEntry(
                    key=key,
                    value=None,
                    version=existing.version + 1,
                    timestamp=datetime.utcnow(),
                    deleted=True
                )
                self._state[key] = entry
                return entry
            return None

    def merge(self, entries: List[StateEntry]) -> List[StateEntry]:
        """Merge entries (last-write-wins)."""
        updated = []

        with self._lock:
            for entry in entries:
                existing = self._state.get(entry.key)

                if existing is None:
                    self._state[entry.key] = entry
                    updated.append(entry)
                elif entry.version > existing.version:
                    self._state[entry.key] = entry
                    updated.append(entry)
                elif entry.version == existing.version and entry.timestamp > existing.timestamp:
                    self._state[entry.key] = entry
                    updated.append(entry)

        return updated

    def get_all(self) -> List[StateEntry]:
        """Get all entries."""
        with self._lock:
            return list(self._state.values())

    def get_since(
        self,
        since: datetime
    ) -> List[StateEntry]:
        """Get entries since timestamp."""
        with self._lock:
            return [
                e for e in self._state.values()
                if e.timestamp > since
            ]

    def digest(self) -> Dict[str, int]:
        """Get digest (key -> version map)."""
        with self._lock:
            return {k: v.version for k, v in self._state.items()}


# =============================================================================
# GOSSIP ENGINE
# =============================================================================

class GossipEngine:
    """Core gossip engine."""

    def __init__(self, config: GossipConfig):
        self.config = config
        self.node_id = config.node_id

        self._state = GossipStateStore()
        self._detector = FailureDetector(
            config,
            on_suspect=self._on_node_suspect,
            on_dead=self._on_node_dead,
            on_alive=self._on_node_alive
        )

        self._message_handlers: Dict[GossipType, Callable] = {}
        self._pending_messages: Dict[str, GossipMessage] = {}
        self._seen_messages: Set[str] = set()

        self._running = False
        self._lock = threading.RLock()

        self._stats = GossipStats()

        # Callbacks
        self._on_state_change: Optional[Callable[[str, Any], None]] = None
        self._on_node_join: Optional[Callable[[GossipNode], None]] = None
        self._on_node_leave: Optional[Callable[[str], None]] = None

    def set_callbacks(
        self,
        on_state_change: Optional[Callable[[str, Any], None]] = None,
        on_node_join: Optional[Callable[[GossipNode], None]] = None,
        on_node_leave: Optional[Callable[[str], None]] = None
    ) -> None:
        """Set callbacks."""
        self._on_state_change = on_state_change
        self._on_node_join = on_node_join
        self._on_node_leave = on_node_leave

    # -------------------------------------------------------------------------
    # NODE EVENTS
    # -------------------------------------------------------------------------

    def _on_node_suspect(self, node_id: str) -> None:
        """Handle node suspect."""
        pass

    def _on_node_dead(self, node_id: str) -> None:
        """Handle node dead."""
        if self._on_node_leave:
            self._on_node_leave(node_id)

    def _on_node_alive(self, node_id: str) -> None:
        """Handle node alive."""
        pass

    # -------------------------------------------------------------------------
    # MEMBERSHIP
    # -------------------------------------------------------------------------

    def join(
        self,
        node_id: str,
        address: str = "",
        port: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GossipNode:
        """Join a node to cluster."""
        node = GossipNode(
            node_id=node_id,
            address=address,
            port=port,
            state=NodeState.ALIVE,
            incarnation=0,
            metadata=metadata or {}
        )

        self._detector.add_node(node)
        self._stats.nodes_joined += 1

        if self._on_node_join:
            self._on_node_join(node)

        return node

    def leave(self, node_id: str) -> None:
        """Leave node from cluster."""
        self._detector.remove_node(node_id)
        self._stats.nodes_left += 1

        if self._on_node_leave:
            self._on_node_leave(node_id)

    def get_members(self) -> List[GossipNode]:
        """Get cluster members."""
        return self._detector.get_all_nodes()

    def get_alive_members(self) -> List[GossipNode]:
        """Get alive cluster members."""
        return self._detector.get_alive_nodes()

    # -------------------------------------------------------------------------
    # STATE MANAGEMENT
    # -------------------------------------------------------------------------

    def set_state(self, key: str, value: Any) -> None:
        """Set state value."""
        self._state.set(key, value)

        if self._on_state_change:
            self._on_state_change(key, value)

    def get_state(self, key: str) -> Optional[Any]:
        """Get state value."""
        return self._state.get(key)

    def delete_state(self, key: str) -> None:
        """Delete state value."""
        self._state.delete(key)

        if self._on_state_change:
            self._on_state_change(key, None)

    def get_all_state(self) -> Dict[str, Any]:
        """Get all state."""
        entries = self._state.get_all()
        return {
            e.key: e.value
            for e in entries
            if not e.deleted
        }

    # -------------------------------------------------------------------------
    # MESSAGE HANDLING
    # -------------------------------------------------------------------------

    def create_message(
        self,
        message_type: GossipType,
        payload: Dict[str, Any]
    ) -> GossipMessage:
        """Create gossip message."""
        return GossipMessage(
            message_type=message_type,
            sender_id=self.node_id,
            payload=payload,
            ttl=self.config.max_transmissions
        )

    def receive_message(
        self,
        message: GossipMessage
    ) -> Optional[GossipMessage]:
        """Receive and process gossip message."""
        with self._lock:
            # Check if seen
            if message.message_id in self._seen_messages:
                return None

            self._seen_messages.add(message.message_id)
            self._stats.messages_received += 1

            # Report sender alive
            self._detector.report_alive(message.sender_id)

            # Process by type
            response = None

            if message.message_type == GossipType.PING:
                response = self._handle_ping(message)
            elif message.message_type == GossipType.PONG:
                self._handle_pong(message)
            elif message.message_type == GossipType.PUSH:
                self._handle_push(message)
            elif message.message_type == GossipType.PULL:
                response = self._handle_pull(message)
            elif message.message_type == GossipType.PUSH_PULL:
                response = self._handle_push_pull(message)
            elif message.message_type == GossipType.SYNC:
                response = self._handle_sync(message)

            return response

    def _handle_ping(
        self,
        message: GossipMessage
    ) -> GossipMessage:
        """Handle ping message."""
        return self.create_message(
            GossipType.PONG,
            {"timestamp": datetime.utcnow().isoformat()}
        )

    def _handle_pong(
        self,
        message: GossipMessage
    ) -> None:
        """Handle pong message."""
        pass

    def _handle_push(
        self,
        message: GossipMessage
    ) -> None:
        """Handle push message."""
        entries = message.payload.get("entries", [])
        state_entries = [
            StateEntry(
                key=e["key"],
                value=e["value"],
                version=e["version"],
                timestamp=datetime.fromisoformat(e["timestamp"]),
                deleted=e.get("deleted", False)
            )
            for e in entries
        ]

        updated = self._state.merge(state_entries)

        for entry in updated:
            if self._on_state_change:
                self._on_state_change(
                    entry.key,
                    entry.value if not entry.deleted else None
                )

    def _handle_pull(
        self,
        message: GossipMessage
    ) -> GossipMessage:
        """Handle pull message."""
        entries = self._state.get_all()
        return self.create_message(
            GossipType.PUSH,
            {
                "entries": [
                    {
                        "key": e.key,
                        "value": e.value,
                        "version": e.version,
                        "timestamp": e.timestamp.isoformat(),
                        "deleted": e.deleted
                    }
                    for e in entries
                ]
            }
        )

    def _handle_push_pull(
        self,
        message: GossipMessage
    ) -> GossipMessage:
        """Handle push-pull message."""
        # First handle push
        self._handle_push(message)

        # Then respond with pull
        return self._handle_pull(message)

    def _handle_sync(
        self,
        message: GossipMessage
    ) -> GossipMessage:
        """Handle sync message (anti-entropy)."""
        remote_digest = message.payload.get("digest", {})
        local_digest = self._state.digest()

        # Find differences
        to_send = []
        to_request = []

        for key, version in local_digest.items():
            remote_version = remote_digest.get(key, 0)
            if version > remote_version:
                entry = self._state._state.get(key)
                if entry:
                    to_send.append({
                        "key": entry.key,
                        "value": entry.value,
                        "version": entry.version,
                        "timestamp": entry.timestamp.isoformat(),
                        "deleted": entry.deleted
                    })

        for key, version in remote_digest.items():
            local_version = local_digest.get(key, 0)
            if version > local_version:
                to_request.append(key)

        return self.create_message(
            GossipType.SYNC,
            {
                "entries": to_send,
                "request": to_request
            }
        )

    # -------------------------------------------------------------------------
    # GOSSIP ROUND
    # -------------------------------------------------------------------------

    def select_gossip_targets(self) -> List[GossipNode]:
        """Select random targets for gossip."""
        alive = self._detector.get_alive_nodes()

        # Exclude self
        candidates = [n for n in alive if n.node_id != self.node_id]

        if not candidates:
            return []

        # Random selection
        k = min(self.config.fanout, len(candidates))
        return random.sample(candidates, k)

    def create_gossip_message(self) -> GossipMessage:
        """Create gossip message based on style."""
        style = self.config.dissemination_style

        if style == DisseminationStyle.PUSH:
            entries = self._state.get_all()
            return self.create_message(
                GossipType.PUSH,
                {
                    "entries": [
                        {
                            "key": e.key,
                            "value": e.value,
                            "version": e.version,
                            "timestamp": e.timestamp.isoformat(),
                            "deleted": e.deleted
                        }
                        for e in entries
                    ]
                }
            )

        elif style == DisseminationStyle.PULL:
            return self.create_message(
                GossipType.PULL,
                {"digest": self._state.digest()}
            )

        else:  # PUSH_PULL
            entries = self._state.get_all()
            return self.create_message(
                GossipType.PUSH_PULL,
                {
                    "entries": [
                        {
                            "key": e.key,
                            "value": e.value,
                            "version": e.version,
                            "timestamp": e.timestamp.isoformat(),
                            "deleted": e.deleted
                        }
                        for e in entries
                    ],
                    "digest": self._state.digest()
                }
            )

    # -------------------------------------------------------------------------
    # PROBING
    # -------------------------------------------------------------------------

    def probe(self, node_id: str) -> GossipMessage:
        """Create probe message."""
        self._stats.probes_sent += 1
        return self.create_message(
            GossipType.PING,
            {"timestamp": datetime.utcnow().isoformat()}
        )

    def report_probe_failure(self, node_id: str) -> None:
        """Report probe failure."""
        self._stats.probes_failed += 1
        self._detector.report_suspect(node_id)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def stats(self) -> GossipStats:
        """Get gossip statistics."""
        with self._lock:
            return copy.copy(self._stats)


# =============================================================================
# GOSSIP MANAGER
# =============================================================================

class GossipManager:
    """
    Gossip Manager for BAEL.

    Advanced gossip protocol management.
    """

    def __init__(self):
        self._engines: Dict[str, GossipEngine] = {}
        self._lock = threading.RLock()

    def create_engine(
        self,
        node_id: Optional[str] = None,
        gossip_interval_ms: int = 1000,
        fanout: int = 3,
        dissemination_style: DisseminationStyle = DisseminationStyle.PUSH_PULL
    ) -> GossipEngine:
        """Create gossip engine."""
        config = GossipConfig(
            node_id=node_id or str(uuid.uuid4()),
            gossip_interval_ms=gossip_interval_ms,
            fanout=fanout,
            dissemination_style=dissemination_style
        )

        engine = GossipEngine(config)

        with self._lock:
            self._engines[engine.node_id] = engine

        return engine

    def get_engine(self, node_id: str) -> Optional[GossipEngine]:
        """Get gossip engine."""
        with self._lock:
            return self._engines.get(node_id)

    def delete_engine(self, node_id: str) -> bool:
        """Delete gossip engine."""
        with self._lock:
            if node_id in self._engines:
                del self._engines[node_id]
                return True
            return False

    def list_engines(self) -> List[str]:
        """List engine IDs."""
        with self._lock:
            return list(self._engines.keys())

    # -------------------------------------------------------------------------
    # SIMULATION
    # -------------------------------------------------------------------------

    async def simulate_gossip_round(
        self,
        engines: List[GossipEngine]
    ) -> Dict[str, int]:
        """Simulate gossip round between engines."""
        messages_sent = {}

        for engine in engines:
            targets = []

            # Find other engines
            for other in engines:
                if other.node_id != engine.node_id:
                    targets.append(other)

            if not targets:
                continue

            # Select random targets
            k = min(engine.config.fanout, len(targets))
            selected = random.sample(targets, k)

            # Create and send message
            message = engine.create_gossip_message()
            engine._stats.messages_sent += 1
            engine._stats.gossip_rounds += 1

            count = 0
            for target in selected:
                response = target.receive_message(message)
                count += 1

                if response:
                    engine.receive_message(response)

            messages_sent[engine.node_id] = count

        return messages_sent

    async def simulate_failure_detection(
        self,
        engines: List[GossipEngine],
        dead_node_id: str
    ) -> Dict[str, NodeState]:
        """Simulate failure detection."""
        states = {}

        for engine in engines:
            if engine.node_id == dead_node_id:
                continue

            # Check timeouts
            engine._detector.check_timeouts()

            # Report suspect for dead node
            engine._detector.report_suspect(dead_node_id)

            nodes = engine.get_members()
            for node in nodes:
                if node.node_id == dead_node_id:
                    states[engine.node_id] = node.state
                    break

        return states


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Gossip Manager."""
    print("=" * 70)
    print("BAEL - GOSSIP PROTOCOL MANAGER DEMO")
    print("Advanced Gossip Protocol for AI Agents")
    print("=" * 70)
    print()

    manager = GossipManager()

    # 1. Create Engines
    print("1. CREATE GOSSIP ENGINES:")
    print("-" * 40)

    engines = []
    for i in range(5):
        engine = manager.create_engine(
            node_id=f"node_{i}",
            fanout=2
        )
        engines.append(engine)
        print(f"   Created: {engine.node_id}")
    print()

    # 2. Join Nodes
    print("2. JOIN NODES:")
    print("-" * 40)

    for engine in engines:
        for other in engines:
            if other.node_id != engine.node_id:
                engine.join(
                    other.node_id,
                    address=f"127.0.0.{engines.index(other) + 1}",
                    port=8000 + engines.index(other)
                )

    for engine in engines:
        members = engine.get_members()
        print(f"   {engine.node_id}: {len(members)} members")
    print()

    # 3. Set State
    print("3. SET STATE:")
    print("-" * 40)

    engines[0].set_state("key1", "value1")
    engines[0].set_state("key2", {"data": 123})
    engines[1].set_state("key3", [1, 2, 3])

    print(f"   node_0: key1 = {engines[0].get_state('key1')}")
    print(f"   node_0: key2 = {engines[0].get_state('key2')}")
    print(f"   node_1: key3 = {engines[1].get_state('key3')}")
    print()

    # 4. Gossip Round
    print("4. GOSSIP ROUND:")
    print("-" * 40)

    sent = await manager.simulate_gossip_round(engines)

    for node_id, count in sent.items():
        print(f"   {node_id}: {count} messages")
    print()

    # 5. Check State Propagation
    print("5. STATE PROPAGATION:")
    print("-" * 40)

    # Run multiple rounds
    for _ in range(5):
        await manager.simulate_gossip_round(engines)

    for engine in engines:
        state = engine.get_all_state()
        print(f"   {engine.node_id}: {len(state)} keys")
    print()

    # 6. Probing
    print("6. PROBING:")
    print("-" * 40)

    probe = engines[0].probe("node_1")
    print(f"   Probe from node_0 to node_1")
    print(f"   Message type: {probe.message_type.value}")

    response = engines[1].receive_message(probe)
    if response:
        print(f"   Response type: {response.message_type.value}")
    print()

    # 7. Failure Detection
    print("7. FAILURE DETECTION:")
    print("-" * 40)

    # Simulate node_3 failure
    engines[0].report_probe_failure("node_3")
    engines[1].report_probe_failure("node_3")

    states = await manager.simulate_failure_detection(engines, "node_3")

    for node_id, state in states.items():
        print(f"   {node_id} sees node_3 as: {state.value}")
    print()

    # 8. Delete State
    print("8. DELETE STATE:")
    print("-" * 40)

    print(f"   Before delete: {engines[0].get_state('key1')}")
    engines[0].delete_state("key1")
    print(f"   After delete: {engines[0].get_state('key1')}")
    print()

    # 9. Leave Node
    print("9. LEAVE NODE:")
    print("-" * 40)

    before = len(engines[0].get_members())
    engines[0].leave("node_4")
    after = len(engines[0].get_members())

    print(f"   Members: {before} -> {after}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    for engine in engines[:3]:
        stats = engine.stats()
        print(f"   {engine.node_id}:")
        print(f"     Sent: {stats.messages_sent}")
        print(f"     Received: {stats.messages_received}")
        print(f"     Rounds: {stats.gossip_rounds}")
    print()

    # 11. Message Creation
    print("11. MESSAGE CREATION:")
    print("-" * 40)

    push = engines[0].create_message(GossipType.PUSH, {"data": "test"})
    print(f"   Type: {push.message_type.value}")
    print(f"   Sender: {push.sender_id}")
    print(f"   TTL: {push.ttl}")
    print()

    # 12. Gossip Targets
    print("12. GOSSIP TARGETS:")
    print("-" * 40)

    targets = engines[0].select_gossip_targets()
    print(f"   From node_0:")
    for t in targets:
        print(f"     -> {t.node_id}")
    print()

    # 13. Get Alive Members
    print("13. ALIVE MEMBERS:")
    print("-" * 40)

    alive = engines[0].get_alive_members()
    print(f"   node_0 sees {len(alive)} alive members")
    print()

    # 14. List Engines
    print("14. LIST ENGINES:")
    print("-" * 40)

    engine_ids = manager.list_engines()
    print(f"   Engines: {len(engine_ids)}")
    for eid in engine_ids:
        print(f"     {eid}")
    print()

    # 15. Delete Engine
    print("15. DELETE ENGINE:")
    print("-" * 40)

    count_before = len(manager.list_engines())
    deleted = manager.delete_engine("node_4")
    count_after = len(manager.list_engines())

    print(f"   Deleted: {deleted}")
    print(f"   Engines: {count_before} -> {count_after}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Gossip Protocol Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
