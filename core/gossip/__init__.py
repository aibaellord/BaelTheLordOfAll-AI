"""
BAEL Gossip Protocol Engine Implementation
============================================

Epidemic-style information dissemination.

"Ba'el spreads knowledge like whispers on the wind." — Ba'el
"""

import asyncio
import hashlib
import logging
import random
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

logger = logging.getLogger("BAEL.Gossip")


# ============================================================================
# ENUMS
# ============================================================================

class GossipType(Enum):
    """Gossip message types."""
    STATE = "state"           # Full state sync
    DELTA = "delta"           # Delta update
    RUMOR = "rumor"           # Rumor mongering
    ACK = "ack"               # Acknowledgment
    HEARTBEAT = "heartbeat"   # Heartbeat


class NodeStatus(Enum):
    """Node health status."""
    ALIVE = "alive"
    SUSPECT = "suspect"
    DEAD = "dead"


class PropagationMode(Enum):
    """Gossip propagation modes."""
    PUSH = "push"             # Send to peers
    PULL = "pull"             # Request from peers
    PUSH_PULL = "push_pull"   # Both


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class GossipNode:
    """A node in the gossip network."""
    id: str
    address: str
    port: int

    # Status
    status: NodeStatus = NodeStatus.ALIVE

    # Heartbeat
    heartbeat: int = 0
    last_heartbeat: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Failure detection
    suspicion_start: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'address': self.address,
            'port': self.port,
            'status': self.status.value,
            'heartbeat': self.heartbeat,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GossipNode':
        return cls(
            id=data['id'],
            address=data['address'],
            port=data['port'],
            status=NodeStatus(data.get('status', 'alive')),
            heartbeat=data.get('heartbeat', 0),
            metadata=data.get('metadata', {})
        )


@dataclass
class GossipMessage:
    """A gossip message."""
    id: str
    gossip_type: GossipType
    sender_id: str

    # Data
    data: Dict[str, Any] = field(default_factory=dict)

    # Versioning
    version: int = 0

    # Propagation
    hop_count: int = 0
    max_hops: int = 10

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.gossip_type.value,
            'sender': self.sender_id,
            'data': self.data,
            'version': self.version,
            'hops': self.hop_count,
            'ts': self.timestamp.isoformat()
        }


@dataclass
class GossipConfig:
    """Gossip configuration."""
    mode: PropagationMode = PropagationMode.PUSH_PULL
    gossip_interval_ms: float = 1000.0
    gossip_fanout: int = 3
    heartbeat_interval_ms: float = 500.0
    suspicion_timeout_ms: float = 5000.0
    dead_timeout_ms: float = 30000.0
    max_hops: int = 10


# ============================================================================
# GOSSIP ENGINE
# ============================================================================

class GossipEngine:
    """
    Gossip protocol engine.

    Features:
    - Epidemic information spread
    - Failure detection
    - Push/pull/push-pull modes
    - Convergence guarantees

    "Ba'el's whispers reach all ears eventually." — Ba'el
    """

    def __init__(
        self,
        node_id: str,
        address: str = "localhost",
        port: int = 8000,
        config: Optional[GossipConfig] = None
    ):
        """Initialize gossip engine."""
        self.node_id = node_id
        self.config = config or GossipConfig()

        # This node
        self._self = GossipNode(
            id=node_id,
            address=address,
            port=port
        )

        # Cluster membership
        self._nodes: Dict[str, GossipNode] = {node_id: self._self}

        # State to gossip
        self._state: Dict[str, Any] = {}
        self._state_version = 0

        # Received messages (dedup)
        self._seen_messages: Set[str] = set()
        self._message_timestamps: Dict[str, datetime] = {}

        # Communication
        self._send_handler: Optional[Callable] = None

        # Event callbacks
        self._on_state_change: Optional[Callable] = None
        self._on_node_join: Optional[Callable] = None
        self._on_node_leave: Optional[Callable] = None

        # Tasks
        self._gossip_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._failure_task: Optional[asyncio.Task] = None

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'state_updates': 0,
            'nodes_detected': 0
        }

        logger.info(f"Gossip engine initialized: {node_id}")

    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================

    def set_state(self, key: str, value: Any) -> int:
        """
        Set state value.

        Returns:
            New state version
        """
        with self._lock:
            self._state[key] = value
            self._state_version += 1
            self._stats['state_updates'] += 1

        return self._state_version

    def get_state(self, key: str) -> Optional[Any]:
        """Get state value."""
        return self._state.get(key)

    def get_all_state(self) -> Dict[str, Any]:
        """Get all state."""
        return dict(self._state)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set node metadata."""
        self._self.metadata[key] = value

    # ========================================================================
    # NODE MANAGEMENT
    # ========================================================================

    def add_node(
        self,
        node_id: str,
        address: str,
        port: int
    ) -> GossipNode:
        """Add a node to the cluster."""
        node = GossipNode(
            id=node_id,
            address=address,
            port=port
        )

        with self._lock:
            self._nodes[node_id] = node
            self._stats['nodes_detected'] += 1

        if self._on_node_join:
            asyncio.create_task(self._call_handler(self._on_node_join, node))

        return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node."""
        with self._lock:
            if node_id in self._nodes and node_id != self.node_id:
                node = self._nodes.pop(node_id)

                if self._on_node_leave:
                    asyncio.create_task(
                        self._call_handler(self._on_node_leave, node)
                    )

                return True
        return False

    def get_node(self, node_id: str) -> Optional[GossipNode]:
        """Get a node."""
        return self._nodes.get(node_id)

    def get_alive_nodes(self) -> List[GossipNode]:
        """Get all alive nodes."""
        return [
            n for n in self._nodes.values()
            if n.status == NodeStatus.ALIVE
        ]

    # ========================================================================
    # GOSSIP PROTOCOL
    # ========================================================================

    async def gossip(self) -> int:
        """
        Perform one round of gossip.

        Returns:
            Number of nodes gossiped to
        """
        if self.config.mode == PropagationMode.PUSH:
            return await self._gossip_push()
        elif self.config.mode == PropagationMode.PULL:
            return await self._gossip_pull()
        else:
            await self._gossip_push()
            return await self._gossip_pull()

    async def _gossip_push(self) -> int:
        """Push state to random peers."""
        peers = self._select_gossip_peers()

        if not peers:
            return 0

        # Create state message
        message = GossipMessage(
            id=str(uuid.uuid4()),
            gossip_type=GossipType.STATE,
            sender_id=self.node_id,
            data={
                'state': self._state,
                'nodes': {
                    k: v.to_dict() for k, v in self._nodes.items()
                }
            },
            version=self._state_version
        )

        # Send to peers
        sent = 0
        for peer in peers:
            if await self._send_message(peer, message):
                sent += 1

        return sent

    async def _gossip_pull(self) -> int:
        """Pull state from random peers."""
        peers = self._select_gossip_peers()

        if not peers:
            return 0

        pulled = 0
        for peer in peers:
            # Request state
            message = GossipMessage(
                id=str(uuid.uuid4()),
                gossip_type=GossipType.DELTA,
                sender_id=self.node_id,
                data={'version': self._state_version}
            )

            if await self._send_message(peer, message):
                pulled += 1

        return pulled

    def _select_gossip_peers(self) -> List[GossipNode]:
        """Select random peers for gossip."""
        candidates = [
            n for n in self._nodes.values()
            if n.id != self.node_id and n.status != NodeStatus.DEAD
        ]

        if not candidates:
            return []

        count = min(self.config.gossip_fanout, len(candidates))
        return random.sample(candidates, count)

    # ========================================================================
    # MESSAGE HANDLING
    # ========================================================================

    async def _send_message(
        self,
        node: GossipNode,
        message: GossipMessage
    ) -> bool:
        """Send message to node."""
        if not self._send_handler:
            return False

        try:
            await self._send_handler(node, message.to_dict())
            self._stats['messages_sent'] += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send to {node.id}: {e}")
            return False

    async def receive_message(
        self,
        message_data: Dict[str, Any]
    ) -> None:
        """
        Receive and process a gossip message.

        Args:
            message_data: Message data dict
        """
        # Deduplicate
        msg_id = message_data.get('id')
        if msg_id in self._seen_messages:
            return

        with self._lock:
            self._seen_messages.add(msg_id)
            self._message_timestamps[msg_id] = datetime.now()

        self._stats['messages_received'] += 1

        gossip_type = GossipType(message_data.get('type'))
        sender_id = message_data.get('sender')
        data = message_data.get('data', {})

        # Update sender status
        if sender_id in self._nodes:
            self._nodes[sender_id].status = NodeStatus.ALIVE
            self._nodes[sender_id].last_heartbeat = datetime.now()

        if gossip_type == GossipType.STATE:
            await self._handle_state_message(sender_id, data)
        elif gossip_type == GossipType.DELTA:
            await self._handle_delta_request(sender_id, data)
        elif gossip_type == GossipType.HEARTBEAT:
            await self._handle_heartbeat(sender_id, data)

    async def _handle_state_message(
        self,
        sender_id: str,
        data: Dict[str, Any]
    ) -> None:
        """Handle state sync message."""
        # Merge state
        remote_state = data.get('state', {})

        changed = False
        for key, value in remote_state.items():
            if key not in self._state or self._state[key] != value:
                self._state[key] = value
                changed = True

        # Merge nodes
        remote_nodes = data.get('nodes', {})

        for node_id, node_data in remote_nodes.items():
            if node_id not in self._nodes:
                node = GossipNode.from_dict(node_data)
                self._nodes[node_id] = node
                self._stats['nodes_detected'] += 1

                if self._on_node_join:
                    await self._call_handler(self._on_node_join, node)

        if changed and self._on_state_change:
            await self._call_handler(self._on_state_change, self._state)

    async def _handle_delta_request(
        self,
        sender_id: str,
        data: Dict[str, Any]
    ) -> None:
        """Handle delta request."""
        remote_version = data.get('version', 0)

        if self._state_version > remote_version:
            # Send full state
            sender = self._nodes.get(sender_id)
            if sender:
                message = GossipMessage(
                    id=str(uuid.uuid4()),
                    gossip_type=GossipType.STATE,
                    sender_id=self.node_id,
                    data={'state': self._state},
                    version=self._state_version
                )
                await self._send_message(sender, message)

    async def _handle_heartbeat(
        self,
        sender_id: str,
        data: Dict[str, Any]
    ) -> None:
        """Handle heartbeat."""
        if sender_id in self._nodes:
            node = self._nodes[sender_id]
            node.heartbeat = data.get('heartbeat', 0)
            node.last_heartbeat = datetime.now()
            node.status = NodeStatus.ALIVE
            node.suspicion_start = None

    # ========================================================================
    # FAILURE DETECTION
    # ========================================================================

    async def _check_failures(self) -> None:
        """Check for failed nodes."""
        now = datetime.now()
        suspicion_timeout = timedelta(
            milliseconds=self.config.suspicion_timeout_ms
        )
        dead_timeout = timedelta(
            milliseconds=self.config.dead_timeout_ms
        )

        for node in self._nodes.values():
            if node.id == self.node_id:
                continue

            if node.last_heartbeat:
                since_heartbeat = now - node.last_heartbeat

                if since_heartbeat > dead_timeout:
                    if node.status != NodeStatus.DEAD:
                        node.status = NodeStatus.DEAD
                        logger.warning(f"Node marked dead: {node.id}")

                        if self._on_node_leave:
                            await self._call_handler(
                                self._on_node_leave,
                                node
                            )

                elif since_heartbeat > suspicion_timeout:
                    if node.status == NodeStatus.ALIVE:
                        node.status = NodeStatus.SUSPECT
                        node.suspicion_start = now
                        logger.info(f"Node suspected: {node.id}")

    # ========================================================================
    # HEARTBEAT
    # ========================================================================

    async def _send_heartbeats(self) -> None:
        """Send heartbeat to peers."""
        self._self.heartbeat += 1

        message = GossipMessage(
            id=str(uuid.uuid4()),
            gossip_type=GossipType.HEARTBEAT,
            sender_id=self.node_id,
            data={'heartbeat': self._self.heartbeat}
        )

        for node in self._select_gossip_peers():
            await self._send_message(node, message)

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_state_change(self, callback: Callable) -> None:
        """Set state change callback."""
        self._on_state_change = callback

    def on_node_join(self, callback: Callable) -> None:
        """Set node join callback."""
        self._on_node_join = callback

    def on_node_leave(self, callback: Callable) -> None:
        """Set node leave callback."""
        self._on_node_leave = callback

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
        """Start gossip engine."""
        logger.info("Starting gossip engine")

        # Start gossip task
        self._gossip_task = asyncio.create_task(self._gossip_loop())

        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Start failure detection
        self._failure_task = asyncio.create_task(self._failure_loop())

    async def _gossip_loop(self) -> None:
        """Gossip loop."""
        while True:
            try:
                await self.gossip()
            except Exception as e:
                logger.error(f"Gossip error: {e}")

            await asyncio.sleep(
                self.config.gossip_interval_ms / 1000
            )

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop."""
        while True:
            try:
                await self._send_heartbeats()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            await asyncio.sleep(
                self.config.heartbeat_interval_ms / 1000
            )

    async def _failure_loop(self) -> None:
        """Failure detection loop."""
        while True:
            try:
                await self._check_failures()
            except Exception as e:
                logger.error(f"Failure check error: {e}")

            await asyncio.sleep(
                self.config.suspicion_timeout_ms / 1000
            )

    async def stop(self) -> None:
        """Stop gossip engine."""
        if self._gossip_task:
            self._gossip_task.cancel()

        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        if self._failure_task:
            self._failure_task.cancel()

        logger.info("Gossip engine stopped")

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'node_id': self.node_id,
            'state_version': self._state_version,
            'node_count': len(self._nodes),
            'alive_count': len(self.get_alive_nodes()),
            **self._stats
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

gossip_engine: Optional[GossipEngine] = None


def get_gossip_engine(
    node_id: Optional[str] = None,
    config: Optional[GossipConfig] = None
) -> GossipEngine:
    """Get or create gossip engine."""
    global gossip_engine
    if gossip_engine is None:
        gossip_engine = GossipEngine(
            node_id or str(uuid.uuid4()),
            config=config
        )
    return gossip_engine
