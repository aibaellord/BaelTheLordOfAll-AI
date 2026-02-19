"""
BAEL Consistent Hashing Engine Implementation
===============================================

Distributed key routing with minimal remapping.

"Ba'el distributes burdens with perfect balance." — Ba'el
"""

import bisect
import hashlib
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger("BAEL.ConsistentHash")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class VirtualNode:
    """A virtual node on the hash ring."""
    id: str
    physical_node: str
    position: int
    replica_index: int


@dataclass
class PhysicalNode:
    """A physical node in the cluster."""
    id: str
    address: str
    port: int
    weight: int = 1
    healthy: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'address': self.address,
            'port': self.port,
            'weight': self.weight,
            'healthy': self.healthy,
            'metadata': self.metadata
        }


@dataclass
class ConsistentHashConfig:
    """Consistent hashing configuration."""
    virtual_nodes: int = 150          # Virtual nodes per physical node
    replication_factor: int = 3        # Number of replicas
    hash_function: str = "md5"         # Hash function


# ============================================================================
# CONSISTENT HASH RING
# ============================================================================

class ConsistentHashRing:
    """
    Consistent hash ring implementation.

    Features:
    - Virtual nodes for load balancing
    - Weighted node distribution
    - Minimal key remapping on node changes
    - Replication support

    "Ba'el ensures perfect distribution of responsibility." — Ba'el
    """

    def __init__(self, config: Optional[ConsistentHashConfig] = None):
        """Initialize consistent hash ring."""
        self.config = config or ConsistentHashConfig()

        # Ring structure
        self._ring: List[Tuple[int, VirtualNode]] = []
        self._positions: List[int] = []  # Sorted positions for binary search

        # Nodes
        self._physical_nodes: Dict[str, PhysicalNode] = {}
        self._virtual_nodes: Dict[str, List[VirtualNode]] = {}

        # Hash function
        self._hash_func = getattr(hashlib, self.config.hash_function)

        # Thread safety
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'nodes_added': 0,
            'nodes_removed': 0,
            'lookups': 0
        }

        logger.info("Consistent hash ring initialized")

    def _hash(self, key: str) -> int:
        """Hash a key to ring position."""
        digest = self._hash_func(key.encode('utf-8')).hexdigest()
        return int(digest, 16) % (2 ** 32)

    # ========================================================================
    # NODE MANAGEMENT
    # ========================================================================

    def add_node(
        self,
        node_id: str,
        address: str = "localhost",
        port: int = 8000,
        weight: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PhysicalNode:
        """
        Add a physical node to the ring.

        Args:
            node_id: Unique node identifier
            address: Node address
            port: Node port
            weight: Node weight (affects virtual node count)
            metadata: Optional metadata

        Returns:
            Added node
        """
        node = PhysicalNode(
            id=node_id,
            address=address,
            port=port,
            weight=weight,
            metadata=metadata or {}
        )

        with self._lock:
            self._physical_nodes[node_id] = node

            # Create virtual nodes
            virtual_count = self.config.virtual_nodes * weight
            vnodes = []

            for i in range(virtual_count):
                vnode_key = f"{node_id}:{i}"
                position = self._hash(vnode_key)

                vnode = VirtualNode(
                    id=vnode_key,
                    physical_node=node_id,
                    position=position,
                    replica_index=i
                )
                vnodes.append(vnode)

                # Add to ring
                bisect.insort(self._ring, (position, vnode))

            self._virtual_nodes[node_id] = vnodes
            self._positions = [pos for pos, _ in self._ring]

            self._stats['nodes_added'] += 1

        logger.info(f"Node added: {node_id} ({len(vnodes)} virtual nodes)")

        return node

    def remove_node(self, node_id: str) -> bool:
        """
        Remove a physical node from the ring.

        Args:
            node_id: Node to remove

        Returns:
            True if removed
        """
        with self._lock:
            if node_id not in self._physical_nodes:
                return False

            # Remove virtual nodes
            vnodes = self._virtual_nodes.get(node_id, [])
            positions_to_remove = {vn.position for vn in vnodes}

            self._ring = [
                (pos, vn) for pos, vn in self._ring
                if pos not in positions_to_remove
            ]

            # Update tracking
            del self._physical_nodes[node_id]
            del self._virtual_nodes[node_id]
            self._positions = [pos for pos, _ in self._ring]

            self._stats['nodes_removed'] += 1

        logger.info(f"Node removed: {node_id}")

        return True

    def set_node_health(self, node_id: str, healthy: bool) -> bool:
        """Set node health status."""
        if node_id in self._physical_nodes:
            self._physical_nodes[node_id].healthy = healthy
            return True
        return False

    # ========================================================================
    # KEY ROUTING
    # ========================================================================

    def get_node(self, key: str) -> Optional[PhysicalNode]:
        """
        Get the node responsible for a key.

        Args:
            key: Key to look up

        Returns:
            Responsible physical node
        """
        with self._lock:
            if not self._ring:
                return None

            self._stats['lookups'] += 1

            position = self._hash(key)

            # Binary search for next position
            idx = bisect.bisect_left(self._positions, position)

            # Wrap around if needed
            if idx >= len(self._ring):
                idx = 0

            # Find healthy node
            start_idx = idx
            while True:
                _, vnode = self._ring[idx]
                pnode = self._physical_nodes[vnode.physical_node]

                if pnode.healthy:
                    return pnode

                idx = (idx + 1) % len(self._ring)

                if idx == start_idx:
                    # All nodes unhealthy
                    return None

    def get_node_id(self, key: str) -> Optional[str]:
        """Get node ID for a key."""
        node = self.get_node(key)
        return node.id if node else None

    def get_replicas(self, key: str, count: Optional[int] = None) -> List[PhysicalNode]:
        """
        Get replica nodes for a key.

        Args:
            key: Key to look up
            count: Number of replicas (default: config.replication_factor)

        Returns:
            List of replica nodes
        """
        count = count or self.config.replication_factor

        with self._lock:
            if not self._ring:
                return []

            position = self._hash(key)
            idx = bisect.bisect_left(self._positions, position)

            replicas = []
            seen_nodes = set()

            for _ in range(len(self._ring)):
                if len(replicas) >= count:
                    break

                current_idx = (idx + len(replicas)) % len(self._ring)
                _, vnode = self._ring[current_idx]
                pnode = self._physical_nodes[vnode.physical_node]

                if pnode.id not in seen_nodes and pnode.healthy:
                    replicas.append(pnode)
                    seen_nodes.add(pnode.id)

            return replicas

    # ========================================================================
    # REBALANCING
    # ========================================================================

    def get_keys_for_node(
        self,
        node_id: str,
        all_keys: List[str]
    ) -> List[str]:
        """
        Get keys that belong to a node.

        Args:
            node_id: Node ID
            all_keys: List of all keys

        Returns:
            Keys belonging to this node
        """
        return [
            key for key in all_keys
            if self.get_node_id(key) == node_id
        ]

    def get_key_distribution(
        self,
        keys: List[str]
    ) -> Dict[str, int]:
        """
        Get distribution of keys across nodes.

        Args:
            keys: List of keys

        Returns:
            Node ID -> key count mapping
        """
        distribution: Dict[str, int] = {}

        for key in keys:
            node_id = self.get_node_id(key)
            if node_id:
                distribution[node_id] = distribution.get(node_id, 0) + 1

        return distribution

    def get_affected_keys(
        self,
        node_id: str,
        all_keys: List[str],
        adding: bool = True
    ) -> List[str]:
        """
        Get keys affected by adding/removing a node.

        Args:
            node_id: Node being added/removed
            all_keys: All keys
            adding: True if adding node, False if removing

        Returns:
            List of affected keys
        """
        affected = []

        if adding:
            # Keys that would move to the new node
            for key in all_keys:
                current_node = self.get_node_id(key)
                if current_node != node_id:
                    # Temporarily check if it would go to new node
                    # This is simplified - real implementation would simulate
                    affected.append(key)
        else:
            # Keys currently on this node
            affected = self.get_keys_for_node(node_id, all_keys)

        return affected

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_nodes(self) -> List[PhysicalNode]:
        """Get all physical nodes."""
        return list(self._physical_nodes.values())

    def get_healthy_nodes(self) -> List[PhysicalNode]:
        """Get all healthy nodes."""
        return [n for n in self._physical_nodes.values() if n.healthy]

    def get_node_count(self) -> int:
        """Get physical node count."""
        return len(self._physical_nodes)

    def get_virtual_node_count(self) -> int:
        """Get virtual node count."""
        return len(self._ring)

    # ========================================================================
    # VISUALIZATION
    # ========================================================================

    def get_ring_segments(self) -> List[Dict[str, Any]]:
        """
        Get ring segments for visualization.

        Returns:
            List of segment info
        """
        if not self._ring:
            return []

        segments = []
        max_pos = 2 ** 32

        for i, (pos, vnode) in enumerate(self._ring):
            next_pos = self._ring[(i + 1) % len(self._ring)][0]

            if next_pos > pos:
                size = next_pos - pos
            else:
                size = (max_pos - pos) + next_pos

            segments.append({
                'position': pos,
                'physical_node': vnode.physical_node,
                'virtual_node': vnode.id,
                'segment_size': size,
                'percentage': (size / max_pos) * 100
            })

        return segments

    # ========================================================================
    # STATS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get ring statistics."""
        return {
            'physical_nodes': len(self._physical_nodes),
            'virtual_nodes': len(self._ring),
            'healthy_nodes': len(self.get_healthy_nodes()),
            **self._stats
        }


# ============================================================================
# JUMP CONSISTENT HASH
# ============================================================================

class JumpConsistentHash:
    """
    Jump Consistent Hash implementation.

    Fast, memory-efficient consistent hashing.

    "Ba'el leaps to the correct destination instantly." — Ba'el
    """

    @staticmethod
    def hash(key: str, num_buckets: int) -> int:
        """
        Get bucket for key using jump consistent hash.

        Args:
            key: Key to hash
            num_buckets: Number of buckets

        Returns:
            Bucket index
        """
        key_hash = int(
            hashlib.md5(key.encode('utf-8')).hexdigest(), 16
        )

        b = -1
        j = 0

        while j < num_buckets:
            b = j
            key_hash = (key_hash * 2862933555777941757 + 1) & 0xFFFFFFFFFFFFFFFF
            j = int((b + 1) * (float(1 << 31) / float((key_hash >> 33) + 1)))

        return b


# ============================================================================
# RENDEZVOUS HASHING
# ============================================================================

class RendezvousHash:
    """
    Rendezvous (Highest Random Weight) hashing.

    Alternative to consistent hashing.

    "Ba'el finds the highest destiny for each key." — Ba'el
    """

    def __init__(self):
        """Initialize rendezvous hash."""
        self._nodes: Dict[str, PhysicalNode] = {}

    def add_node(
        self,
        node_id: str,
        address: str = "localhost",
        port: int = 8000
    ) -> None:
        """Add a node."""
        self._nodes[node_id] = PhysicalNode(
            id=node_id,
            address=address,
            port=port
        )

    def remove_node(self, node_id: str) -> bool:
        """Remove a node."""
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False

    def _weight(self, key: str, node_id: str) -> int:
        """Calculate weight for key-node pair."""
        combined = f"{key}:{node_id}"
        return int(hashlib.md5(combined.encode('utf-8')).hexdigest(), 16)

    def get_node(self, key: str) -> Optional[PhysicalNode]:
        """Get node with highest weight for key."""
        if not self._nodes:
            return None

        best_node = None
        best_weight = -1

        for node_id, node in self._nodes.items():
            if not node.healthy:
                continue

            weight = self._weight(key, node_id)
            if weight > best_weight:
                best_weight = weight
                best_node = node

        return best_node

    def get_ranked_nodes(
        self,
        key: str,
        count: int = 3
    ) -> List[PhysicalNode]:
        """Get top N nodes by weight for key."""
        weighted = [
            (self._weight(key, node_id), node)
            for node_id, node in self._nodes.items()
            if node.healthy
        ]

        weighted.sort(key=lambda x: x[0], reverse=True)

        return [node for _, node in weighted[:count]]


# ============================================================================
# CONVENIENCE
# ============================================================================

hash_ring: Optional[ConsistentHashRing] = None


def get_hash_ring(config: Optional[ConsistentHashConfig] = None) -> ConsistentHashRing:
    """Get or create hash ring."""
    global hash_ring
    if hash_ring is None:
        hash_ring = ConsistentHashRing(config)
    return hash_ring


def add_node(node_id: str, **kwargs) -> PhysicalNode:
    """Add node to ring."""
    return get_hash_ring().add_node(node_id, **kwargs)


def get_node_for_key(key: str) -> Optional[PhysicalNode]:
    """Get node for key."""
    return get_hash_ring().get_node(key)


def jump_hash(key: str, buckets: int) -> int:
    """Quick jump consistent hash."""
    return JumpConsistentHash.hash(key, buckets)
