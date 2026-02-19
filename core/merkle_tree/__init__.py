"""
BAEL Merkle Tree Engine Implementation
========================================

Cryptographic data integrity verification.

"Ba'el verifies truth through mathematical proof." — Ba'el
"""

import hashlib
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger("BAEL.MerkleTree")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MerkleNode:
    """A node in the Merkle tree."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    data: Optional[Any] = None
    is_leaf: bool = False

    def __repr__(self) -> str:
        return f"MerkleNode({self.hash[:8]}...)"


@dataclass
class MerkleProof:
    """Proof of inclusion in Merkle tree."""
    leaf_hash: str
    proof_hashes: List[Tuple[str, str]]  # (hash, position: 'left' or 'right')
    root_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'leaf_hash': self.leaf_hash,
            'proof': self.proof_hashes,
            'root': self.root_hash
        }


# ============================================================================
# MERKLE TREE
# ============================================================================

class MerkleTree:
    """
    Merkle tree implementation.

    Features:
    - Efficient data integrity verification
    - Proof generation and verification
    - Difference detection

    "Ba'el constructs irrefutable proof of truth." — Ba'el
    """

    def __init__(
        self,
        data: Optional[List[Any]] = None,
        hash_function: str = "sha256"
    ):
        """
        Initialize Merkle tree.

        Args:
            data: Initial data items
            hash_function: Hash function to use
        """
        self._hash_func = getattr(hashlib, hash_function)
        self._leaves: List[MerkleNode] = []
        self._root: Optional[MerkleNode] = None
        self._lock = threading.RLock()

        if data:
            self.build(data)

    def _hash(self, data: Any) -> str:
        """Hash data."""
        if isinstance(data, bytes):
            content = data
        elif isinstance(data, str):
            content = data.encode('utf-8')
        else:
            content = json.dumps(data, sort_keys=True).encode('utf-8')

        return self._hash_func(content).hexdigest()

    def _hash_pair(self, left: str, right: str) -> str:
        """Hash two hashes together."""
        combined = (left + right).encode('utf-8')
        return self._hash_func(combined).hexdigest()

    def build(self, data: List[Any]) -> str:
        """
        Build Merkle tree from data.

        Args:
            data: List of data items

        Returns:
            Root hash
        """
        if not data:
            self._root = None
            self._leaves = []
            return ""

        with self._lock:
            # Create leaf nodes
            self._leaves = [
                MerkleNode(
                    hash=self._hash(item),
                    data=item,
                    is_leaf=True
                )
                for item in data
            ]

            # Build tree
            self._root = self._build_tree(self._leaves)

            return self._root.hash

    def _build_tree(self, nodes: List[MerkleNode]) -> MerkleNode:
        """Recursively build tree from nodes."""
        if len(nodes) == 1:
            return nodes[0]

        # Ensure even number of nodes
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])  # Duplicate last node

        # Build parent level
        parents = []

        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1]

            parent_hash = self._hash_pair(left.hash, right.hash)
            parent = MerkleNode(
                hash=parent_hash,
                left=left,
                right=right
            )
            parents.append(parent)

        return self._build_tree(parents)

    @property
    def root_hash(self) -> Optional[str]:
        """Get root hash."""
        return self._root.hash if self._root else None

    def get_leaf_count(self) -> int:
        """Get number of leaves."""
        return len(self._leaves)

    # ========================================================================
    # PROOF GENERATION
    # ========================================================================

    def get_proof(self, index: int) -> Optional[MerkleProof]:
        """
        Generate proof of inclusion for leaf at index.

        Args:
            index: Leaf index

        Returns:
            Merkle proof or None
        """
        if not self._leaves or index >= len(self._leaves):
            return None

        leaf = self._leaves[index]
        proof_hashes = []

        # Find path from leaf to root
        current_index = index
        current_level = self._leaves

        while len(current_level) > 1:
            # Ensure even
            if len(current_level) % 2 == 1:
                current_level = current_level + [current_level[-1]]

            # Get sibling
            sibling_index = current_index ^ 1  # XOR to get sibling
            sibling = current_level[sibling_index]

            # Position relative to sibling
            position = "right" if current_index % 2 == 0 else "left"
            proof_hashes.append((sibling.hash, position))

            # Move up
            current_index = current_index // 2

            # Build parent level
            parents = []
            for i in range(0, len(current_level), 2):
                parent_hash = self._hash_pair(
                    current_level[i].hash,
                    current_level[i + 1].hash
                )
                parents.append(MerkleNode(hash=parent_hash))

            current_level = parents

        return MerkleProof(
            leaf_hash=leaf.hash,
            proof_hashes=proof_hashes,
            root_hash=self._root.hash if self._root else ""
        )

    def get_proof_by_data(self, data: Any) -> Optional[MerkleProof]:
        """Generate proof for data item."""
        data_hash = self._hash(data)

        for i, leaf in enumerate(self._leaves):
            if leaf.hash == data_hash:
                return self.get_proof(i)

        return None

    # ========================================================================
    # PROOF VERIFICATION
    # ========================================================================

    def verify_proof(self, proof: MerkleProof) -> bool:
        """
        Verify a Merkle proof.

        Args:
            proof: The proof to verify

        Returns:
            True if valid
        """
        current_hash = proof.leaf_hash

        for sibling_hash, position in proof.proof_hashes:
            if position == "right":
                current_hash = self._hash_pair(current_hash, sibling_hash)
            else:
                current_hash = self._hash_pair(sibling_hash, current_hash)

        return current_hash == proof.root_hash

    @staticmethod
    def verify_proof_static(
        proof: MerkleProof,
        hash_function: str = "sha256"
    ) -> bool:
        """Verify proof without tree instance."""
        hash_func = getattr(hashlib, hash_function)

        def hash_pair(left: str, right: str) -> str:
            combined = (left + right).encode('utf-8')
            return hash_func(combined).hexdigest()

        current_hash = proof.leaf_hash

        for sibling_hash, position in proof.proof_hashes:
            if position == "right":
                current_hash = hash_pair(current_hash, sibling_hash)
            else:
                current_hash = hash_pair(sibling_hash, current_hash)

        return current_hash == proof.root_hash

    # ========================================================================
    # DIFFERENCE DETECTION
    # ========================================================================

    def get_differences(self, other: 'MerkleTree') -> List[int]:
        """
        Find differing leaves between two trees.

        Args:
            other: Other Merkle tree

        Returns:
            List of differing leaf indices
        """
        if not self._root or not other._root:
            return list(range(max(len(self._leaves), len(other._leaves))))

        if self._root.hash == other._root.hash:
            return []  # Trees are identical

        differences = []
        self._find_differences(
            self._root,
            other._root,
            0,
            len(self._leaves),
            differences
        )

        return differences

    def _find_differences(
        self,
        node1: Optional[MerkleNode],
        node2: Optional[MerkleNode],
        start: int,
        end: int,
        differences: List[int]
    ) -> None:
        """Recursively find differences."""
        if node1 is None and node2 is None:
            return

        if node1 is None or node2 is None:
            # One tree is missing this subtree
            for i in range(start, end):
                if i not in differences:
                    differences.append(i)
            return

        if node1.hash == node2.hash:
            return  # Subtrees are identical

        if node1.is_leaf or node2.is_leaf:
            # Leaf difference
            differences.append(start)
            return

        # Recurse into children
        mid = (start + end) // 2

        self._find_differences(
            node1.left, node2.left if node2 else None,
            start, mid, differences
        )
        self._find_differences(
            node1.right, node2.right if node2 else None,
            mid, end, differences
        )

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def contains(self, data: Any) -> bool:
        """Check if data is in the tree."""
        data_hash = self._hash(data)
        return any(leaf.hash == data_hash for leaf in self._leaves)

    def get_audit_trail(self, index: int) -> List[str]:
        """Get hashes from leaf to root."""
        proof = self.get_proof(index)
        if not proof:
            return []

        trail = [proof.leaf_hash]
        trail.extend(h for h, _ in proof.proof_hashes)
        trail.append(proof.root_hash)

        return trail


# ============================================================================
# MERKLE PATRICIA TRIE (SIMPLIFIED)
# ============================================================================

class MerklePatriciaTrie:
    """
    Simplified Merkle Patricia Trie.

    Key-value store with cryptographic verification.

    "Ba'el indexes truth efficiently." — Ba'el
    """

    def __init__(self):
        """Initialize trie."""
        self._data: Dict[str, Any] = {}
        self._tree: Optional[MerkleTree] = None
        self._dirty = True

    def put(self, key: str, value: Any) -> None:
        """Put key-value pair."""
        self._data[key] = value
        self._dirty = True

    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        """Delete key."""
        if key in self._data:
            del self._data[key]
            self._dirty = True
            return True
        return False

    def _rebuild(self) -> None:
        """Rebuild Merkle tree from data."""
        if not self._dirty:
            return

        # Sort keys for deterministic ordering
        items = [
            {"key": k, "value": v}
            for k, v in sorted(self._data.items())
        ]

        self._tree = MerkleTree(items)
        self._dirty = False

    @property
    def root_hash(self) -> Optional[str]:
        """Get root hash."""
        self._rebuild()
        return self._tree.root_hash if self._tree else None

    def get_proof(self, key: str) -> Optional[MerkleProof]:
        """Get proof for key."""
        if key not in self._data:
            return None

        self._rebuild()

        # Find index of key
        sorted_keys = sorted(self._data.keys())
        index = sorted_keys.index(key)

        return self._tree.get_proof(index) if self._tree else None

    def verify_proof(self, key: str, value: Any, proof: MerkleProof) -> bool:
        """Verify proof for key-value pair."""
        if not self._tree:
            return False

        # Hash the key-value item
        item_hash = self._tree._hash({"key": key, "value": value})

        # Check if proof leaf matches
        if proof.leaf_hash != item_hash:
            return False

        return self._tree.verify_proof(proof)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_merkle_tree(data: List[Any]) -> MerkleTree:
    """Create a Merkle tree."""
    return MerkleTree(data)


def verify_merkle_proof(proof: MerkleProof) -> bool:
    """Verify a Merkle proof."""
    return MerkleTree.verify_proof_static(proof)


def create_merkle_trie() -> MerklePatriciaTrie:
    """Create a Merkle Patricia Trie."""
    return MerklePatriciaTrie()
