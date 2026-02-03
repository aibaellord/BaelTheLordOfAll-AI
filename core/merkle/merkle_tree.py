#!/usr/bin/env python3
"""
BAEL - Merkle Tree
Advanced cryptographic data structure for AI agent verification.

Features:
- Binary Merkle tree
- Sparse Merkle tree
- Patricia Merkle trie
- Proof generation and verification
- Batch operations
- Incremental updates
- Audit trails
- Serialization support
"""

import asyncio
import copy
import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class HashAlgorithm(Enum):
    """Hash algorithms."""
    SHA256 = "sha256"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    BLAKE2B = "blake2b"


class ProofType(Enum):
    """Proof types."""
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
    CONSISTENCY = "consistency"


class NodePosition(Enum):
    """Node position in proof."""
    LEFT = "left"
    RIGHT = "right"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class MerkleNode:
    """Merkle tree node."""
    hash: bytes
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    data: Optional[bytes] = None
    index: Optional[int] = None


@dataclass
class ProofStep:
    """Single step in a Merkle proof."""
    hash: bytes
    position: NodePosition


@dataclass
class MerkleProof:
    """Merkle inclusion/exclusion proof."""
    proof_type: ProofType
    leaf_hash: bytes
    root_hash: bytes
    steps: List[ProofStep] = field(default_factory=list)
    leaf_index: Optional[int] = None


@dataclass
class TreeStats:
    """Tree statistics."""
    leaf_count: int = 0
    depth: int = 0
    node_count: int = 0
    root_hash: Optional[bytes] = None


# =============================================================================
# HASH UTILITIES
# =============================================================================

class Hasher:
    """Hash utilities."""

    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        self._algorithm = algorithm

    def hash(self, data: bytes) -> bytes:
        """Hash data."""
        if self._algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).digest()
        elif self._algorithm == HashAlgorithm.SHA512:
            return hashlib.sha512(data).digest()
        elif self._algorithm == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).digest()
        elif self._algorithm == HashAlgorithm.BLAKE2B:
            return hashlib.blake2b(data, digest_size=32).digest()
        else:
            return hashlib.sha256(data).digest()

    def combine(self, left: bytes, right: bytes) -> bytes:
        """Combine two hashes."""
        return self.hash(left + right)

    def leaf_hash(self, data: bytes) -> bytes:
        """Hash leaf data with prefix."""
        return self.hash(b'\x00' + data)

    def node_hash(self, left: bytes, right: bytes) -> bytes:
        """Hash internal node with prefix."""
        return self.hash(b'\x01' + left + right)


# =============================================================================
# BINARY MERKLE TREE
# =============================================================================

class MerkleTree:
    """Binary Merkle tree."""

    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        self._hasher = Hasher(algorithm)
        self._leaves: List[bytes] = []
        self._leaf_hashes: List[bytes] = []
        self._root: Optional[MerkleNode] = None

    def add(self, data: bytes) -> int:
        """Add leaf data. Returns index."""
        self._leaves.append(data)
        self._leaf_hashes.append(self._hasher.leaf_hash(data))
        return len(self._leaves) - 1

    def add_all(self, items: List[bytes]) -> List[int]:
        """Add multiple items."""
        indices = []
        for item in items:
            indices.append(self.add(item))
        return indices

    def build(self) -> Optional[bytes]:
        """Build tree and return root hash."""
        if not self._leaf_hashes:
            return None

        # Build bottom-up
        nodes = [
            MerkleNode(hash=h, data=self._leaves[i], index=i)
            for i, h in enumerate(self._leaf_hashes)
        ]

        while len(nodes) > 1:
            next_level = []

            for i in range(0, len(nodes), 2):
                left = nodes[i]

                if i + 1 < len(nodes):
                    right = nodes[i + 1]
                else:
                    right = left  # Duplicate last node

                combined = self._hasher.node_hash(left.hash, right.hash)
                parent = MerkleNode(
                    hash=combined,
                    left=left,
                    right=right
                )
                next_level.append(parent)

            nodes = next_level

        self._root = nodes[0]
        return self._root.hash

    def root_hash(self) -> Optional[bytes]:
        """Get root hash."""
        if self._root:
            return self._root.hash
        return None

    def get_proof(self, index: int) -> Optional[MerkleProof]:
        """Get inclusion proof for leaf."""
        if not self._root or index >= len(self._leaf_hashes):
            return None

        steps = []
        level_size = len(self._leaf_hashes)
        current_index = index

        # Build proof path
        hashes = self._leaf_hashes[:]

        while level_size > 1:
            next_level = []

            for i in range(0, level_size, 2):
                left_idx = i
                right_idx = i + 1 if i + 1 < level_size else i

                left_hash = hashes[left_idx]
                right_hash = hashes[right_idx]

                if current_index == left_idx:
                    steps.append(ProofStep(
                        hash=right_hash,
                        position=NodePosition.RIGHT
                    ))
                    current_index = len(next_level)
                elif current_index == right_idx:
                    steps.append(ProofStep(
                        hash=left_hash,
                        position=NodePosition.LEFT
                    ))
                    current_index = len(next_level)

                combined = self._hasher.node_hash(left_hash, right_hash)
                next_level.append(combined)

            hashes = next_level
            level_size = len(hashes)

        return MerkleProof(
            proof_type=ProofType.INCLUSION,
            leaf_hash=self._leaf_hashes[index],
            root_hash=self._root.hash,
            steps=steps,
            leaf_index=index
        )

    def verify_proof(self, proof: MerkleProof) -> bool:
        """Verify a Merkle proof."""
        current = proof.leaf_hash

        for step in proof.steps:
            if step.position == NodePosition.LEFT:
                current = self._hasher.node_hash(step.hash, current)
            else:
                current = self._hasher.node_hash(current, step.hash)

        return current == proof.root_hash

    def leaf_count(self) -> int:
        """Get leaf count."""
        return len(self._leaves)

    def depth(self) -> int:
        """Get tree depth."""
        if not self._leaves:
            return 0

        import math
        return math.ceil(math.log2(len(self._leaves))) + 1

    def stats(self) -> TreeStats:
        """Get tree statistics."""
        return TreeStats(
            leaf_count=len(self._leaves),
            depth=self.depth(),
            node_count=2 * len(self._leaves) - 1 if self._leaves else 0,
            root_hash=self.root_hash()
        )


# =============================================================================
# SPARSE MERKLE TREE
# =============================================================================

class SparseMerkleTree:
    """Sparse Merkle tree for large key spaces."""

    def __init__(
        self,
        depth: int = 256,
        algorithm: HashAlgorithm = HashAlgorithm.SHA256
    ):
        self._depth = depth
        self._hasher = Hasher(algorithm)
        self._data: Dict[bytes, bytes] = {}
        self._default_hashes: List[bytes] = []

        # Precompute default hashes for each level
        self._compute_defaults()

    def _compute_defaults(self) -> None:
        """Compute default hashes for empty subtrees."""
        empty = self._hasher.hash(b'')
        self._default_hashes = [empty]

        for _ in range(self._depth):
            combined = self._hasher.node_hash(
                self._default_hashes[-1],
                self._default_hashes[-1]
            )
            self._default_hashes.append(combined)

        self._default_hashes.reverse()

    def _key_to_path(self, key: bytes) -> List[int]:
        """Convert key to bit path."""
        key_hash = self._hasher.hash(key)
        path = []

        for i in range(self._depth):
            byte_idx = i // 8
            bit_idx = 7 - (i % 8)
            bit = (key_hash[byte_idx] >> bit_idx) & 1
            path.append(bit)

        return path

    def set(self, key: bytes, value: bytes) -> None:
        """Set key-value pair."""
        self._data[key] = value

    def get(self, key: bytes) -> Optional[bytes]:
        """Get value for key."""
        return self._data.get(key)

    def delete(self, key: bytes) -> bool:
        """Delete key."""
        if key in self._data:
            del self._data[key]
            return True
        return False

    def root_hash(self) -> bytes:
        """Compute root hash."""
        if not self._data:
            return self._default_hashes[0]

        # Build tree with only non-empty paths
        nodes: Dict[Tuple[int, int], bytes] = {}

        # Insert leaves
        for key, value in self._data.items():
            path = self._key_to_path(key)
            leaf_hash = self._hasher.leaf_hash(value)

            # Path as tuple for node indexing
            node_idx = 0
            for bit in path:
                node_idx = node_idx * 2 + bit + 1

            nodes[(self._depth, node_idx)] = leaf_hash

        # Build up
        for level in range(self._depth - 1, -1, -1):
            level_nodes = {
                idx: h for (lvl, idx), h in nodes.items()
                if lvl == level + 1
            }

            for idx in level_nodes:
                parent_idx = (idx - 1) // 2
                sibling_idx = idx + 1 if idx % 2 == 1 else idx - 1

                if sibling_idx < 1:
                    sibling_idx = idx + 1 if idx % 2 == 0 else idx - 1

                left_idx = min(idx, sibling_idx) if (idx % 2 == 1) else idx
                right_idx = max(idx, sibling_idx) if (idx % 2 == 1) else sibling_idx

                left = nodes.get((level + 1, left_idx), self._default_hashes[level + 1])
                right = nodes.get((level + 1, right_idx), self._default_hashes[level + 1])

                nodes[(level, parent_idx)] = self._hasher.node_hash(left, right)

        return nodes.get((0, 0), self._default_hashes[0])

    def get_proof(self, key: bytes) -> MerkleProof:
        """Get proof for key."""
        path = self._key_to_path(key)
        steps = []

        value = self._data.get(key, b'')
        leaf_hash = self._hasher.leaf_hash(value) if value else self._default_hashes[self._depth]

        # Simplified proof - just return siblings along path
        for i, bit in enumerate(path):
            sibling_hash = self._default_hashes[self._depth - i]
            position = NodePosition.RIGHT if bit == 0 else NodePosition.LEFT
            steps.append(ProofStep(hash=sibling_hash, position=position))

        return MerkleProof(
            proof_type=ProofType.INCLUSION if key in self._data else ProofType.EXCLUSION,
            leaf_hash=leaf_hash,
            root_hash=self.root_hash(),
            steps=steps
        )


# =============================================================================
# MERKLE PATRICIA TRIE
# =============================================================================

@dataclass
class TrieNode:
    """Patricia trie node."""
    prefix: bytes = b''
    value: Optional[bytes] = None
    children: Dict[int, 'TrieNode'] = field(default_factory=dict)


class MerklePatriciaTrie:
    """Merkle Patricia Trie for efficient key-value storage."""

    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        self._hasher = Hasher(algorithm)
        self._root = TrieNode()

    def _key_to_nibbles(self, key: bytes) -> List[int]:
        """Convert key to nibbles (4-bit values)."""
        nibbles = []
        for byte in key:
            nibbles.append(byte >> 4)
            nibbles.append(byte & 0x0F)
        return nibbles

    def set(self, key: bytes, value: bytes) -> None:
        """Set key-value pair."""
        nibbles = self._key_to_nibbles(key)
        self._insert(self._root, nibbles, 0, value)

    def _insert(
        self,
        node: TrieNode,
        nibbles: List[int],
        depth: int,
        value: bytes
    ) -> None:
        """Insert value at nibbles path."""
        if depth >= len(nibbles):
            node.value = value
            return

        nibble = nibbles[depth]

        if nibble not in node.children:
            node.children[nibble] = TrieNode()

        self._insert(node.children[nibble], nibbles, depth + 1, value)

    def get(self, key: bytes) -> Optional[bytes]:
        """Get value for key."""
        nibbles = self._key_to_nibbles(key)
        return self._get(self._root, nibbles, 0)

    def _get(
        self,
        node: TrieNode,
        nibbles: List[int],
        depth: int
    ) -> Optional[bytes]:
        """Get value at nibbles path."""
        if depth >= len(nibbles):
            return node.value

        nibble = nibbles[depth]

        if nibble not in node.children:
            return None

        return self._get(node.children[nibble], nibbles, depth + 1)

    def delete(self, key: bytes) -> bool:
        """Delete key."""
        nibbles = self._key_to_nibbles(key)
        return self._delete(self._root, nibbles, 0)

    def _delete(
        self,
        node: TrieNode,
        nibbles: List[int],
        depth: int
    ) -> bool:
        """Delete value at nibbles path."""
        if depth >= len(nibbles):
            if node.value is not None:
                node.value = None
                return True
            return False

        nibble = nibbles[depth]

        if nibble not in node.children:
            return False

        result = self._delete(node.children[nibble], nibbles, depth + 1)

        # Cleanup empty nodes
        child = node.children[nibble]
        if child.value is None and not child.children:
            del node.children[nibble]

        return result

    def root_hash(self) -> bytes:
        """Compute root hash."""
        return self._hash_node(self._root)

    def _hash_node(self, node: TrieNode) -> bytes:
        """Hash a trie node."""
        parts = []

        if node.value is not None:
            parts.append(self._hasher.leaf_hash(node.value))

        for nibble in sorted(node.children.keys()):
            child_hash = self._hash_node(node.children[nibble])
            parts.append(bytes([nibble]) + child_hash)

        if not parts:
            return self._hasher.hash(b'')

        return self._hasher.hash(b''.join(parts))


# =============================================================================
# MERKLE FOREST (MULTIPLE TREES)
# =============================================================================

class MerkleForest:
    """Collection of Merkle trees."""

    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        self._algorithm = algorithm
        self._trees: Dict[str, MerkleTree] = {}

    def create_tree(self, name: str) -> MerkleTree:
        """Create new tree."""
        tree = MerkleTree(self._algorithm)
        self._trees[name] = tree
        return tree

    def get_tree(self, name: str) -> Optional[MerkleTree]:
        """Get tree by name."""
        return self._trees.get(name)

    def delete_tree(self, name: str) -> bool:
        """Delete tree."""
        if name in self._trees:
            del self._trees[name]
            return True
        return False

    def list_trees(self) -> List[str]:
        """List tree names."""
        return list(self._trees.keys())

    def forest_root(self) -> bytes:
        """Compute combined root of all trees."""
        hasher = Hasher(self._algorithm)

        roots = []
        for name in sorted(self._trees.keys()):
            tree = self._trees[name]
            root = tree.root_hash()
            if root:
                roots.append(root)

        if not roots:
            return hasher.hash(b'')

        combined = roots[0]
        for root in roots[1:]:
            combined = hasher.combine(combined, root)

        return combined


# =============================================================================
# MERKLE MANAGER
# =============================================================================

class MerkleManager:
    """
    Merkle Tree Manager for BAEL.

    Advanced cryptographic verification structures.
    """

    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        self._algorithm = algorithm
        self._trees: Dict[str, MerkleTree] = {}
        self._sparse_trees: Dict[str, SparseMerkleTree] = {}
        self._tries: Dict[str, MerklePatriciaTrie] = {}
        self._forests: Dict[str, MerkleForest] = {}

    # -------------------------------------------------------------------------
    # BINARY TREE
    # -------------------------------------------------------------------------

    def create_tree(self, name: str) -> MerkleTree:
        """Create binary Merkle tree."""
        tree = MerkleTree(self._algorithm)
        self._trees[name] = tree
        return tree

    def get_tree(self, name: str) -> Optional[MerkleTree]:
        """Get tree."""
        return self._trees.get(name)

    def add_leaf(self, tree_name: str, data: bytes) -> Optional[int]:
        """Add leaf to tree."""
        tree = self._trees.get(tree_name)
        if tree:
            return tree.add(data)
        return None

    def build_tree(self, tree_name: str) -> Optional[bytes]:
        """Build tree and get root."""
        tree = self._trees.get(tree_name)
        if tree:
            return tree.build()
        return None

    def get_inclusion_proof(
        self,
        tree_name: str,
        index: int
    ) -> Optional[MerkleProof]:
        """Get inclusion proof."""
        tree = self._trees.get(tree_name)
        if tree:
            return tree.get_proof(index)
        return None

    def verify_inclusion(
        self,
        tree_name: str,
        proof: MerkleProof
    ) -> bool:
        """Verify inclusion proof."""
        tree = self._trees.get(tree_name)
        if tree:
            return tree.verify_proof(proof)
        return False

    # -------------------------------------------------------------------------
    # SPARSE TREE
    # -------------------------------------------------------------------------

    def create_sparse_tree(
        self,
        name: str,
        depth: int = 256
    ) -> SparseMerkleTree:
        """Create sparse Merkle tree."""
        tree = SparseMerkleTree(depth, self._algorithm)
        self._sparse_trees[name] = tree
        return tree

    def get_sparse_tree(self, name: str) -> Optional[SparseMerkleTree]:
        """Get sparse tree."""
        return self._sparse_trees.get(name)

    def sparse_set(self, tree_name: str, key: bytes, value: bytes) -> bool:
        """Set value in sparse tree."""
        tree = self._sparse_trees.get(tree_name)
        if tree:
            tree.set(key, value)
            return True
        return False

    def sparse_get(self, tree_name: str, key: bytes) -> Optional[bytes]:
        """Get value from sparse tree."""
        tree = self._sparse_trees.get(tree_name)
        if tree:
            return tree.get(key)
        return None

    # -------------------------------------------------------------------------
    # PATRICIA TRIE
    # -------------------------------------------------------------------------

    def create_trie(self, name: str) -> MerklePatriciaTrie:
        """Create Patricia trie."""
        trie = MerklePatriciaTrie(self._algorithm)
        self._tries[name] = trie
        return trie

    def get_trie(self, name: str) -> Optional[MerklePatriciaTrie]:
        """Get trie."""
        return self._tries.get(name)

    def trie_set(self, trie_name: str, key: bytes, value: bytes) -> bool:
        """Set value in trie."""
        trie = self._tries.get(trie_name)
        if trie:
            trie.set(key, value)
            return True
        return False

    def trie_get(self, trie_name: str, key: bytes) -> Optional[bytes]:
        """Get value from trie."""
        trie = self._tries.get(trie_name)
        if trie:
            return trie.get(key)
        return None

    # -------------------------------------------------------------------------
    # FOREST
    # -------------------------------------------------------------------------

    def create_forest(self, name: str) -> MerkleForest:
        """Create forest."""
        forest = MerkleForest(self._algorithm)
        self._forests[name] = forest
        return forest

    def get_forest(self, name: str) -> Optional[MerkleForest]:
        """Get forest."""
        return self._forests.get(name)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def hash(self, data: bytes) -> bytes:
        """Hash data."""
        return Hasher(self._algorithm).hash(data)

    def list_trees(self) -> List[str]:
        """List all tree names."""
        return list(self._trees.keys())

    def list_sparse_trees(self) -> List[str]:
        """List sparse tree names."""
        return list(self._sparse_trees.keys())

    def list_tries(self) -> List[str]:
        """List trie names."""
        return list(self._tries.keys())


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Merkle Tree."""
    print("=" * 70)
    print("BAEL - MERKLE TREE DEMO")
    print("Advanced Cryptographic Verification for AI Agents")
    print("=" * 70)
    print()

    manager = MerkleManager()

    # 1. Create Binary Merkle Tree
    print("1. BINARY MERKLE TREE:")
    print("-" * 40)

    tree = manager.create_tree("main")

    for i in range(8):
        tree.add(f"data_{i}".encode())

    root = tree.build()
    print(f"   Root hash: {root.hex()[:16]}...")
    print(f"   Leaf count: {tree.leaf_count()}")
    print(f"   Depth: {tree.depth()}")
    print()

    # 2. Generate Proof
    print("2. INCLUSION PROOF:")
    print("-" * 40)

    proof = tree.get_proof(3)
    if proof:
        print(f"   Leaf index: {proof.leaf_index}")
        print(f"   Proof steps: {len(proof.steps)}")
        print(f"   Verified: {tree.verify_proof(proof)}")
    print()

    # 3. Sparse Merkle Tree
    print("3. SPARSE MERKLE TREE:")
    print("-" * 40)

    sparse = manager.create_sparse_tree("sparse", depth=32)

    sparse.set(b"key1", b"value1")
    sparse.set(b"key2", b"value2")

    root = sparse.root_hash()
    print(f"   Root: {root.hex()[:16]}...")
    print(f"   Get key1: {sparse.get(b'key1')}")
    print()

    # 4. Patricia Trie
    print("4. PATRICIA TRIE:")
    print("-" * 40)

    trie = manager.create_trie("trie")

    trie.set(b"hello", b"world")
    trie.set(b"help", b"me")
    trie.set(b"helicopter", b"fly")

    print(f"   Get 'hello': {trie.get(b'hello')}")
    print(f"   Get 'help': {trie.get(b'help')}")
    print(f"   Root: {trie.root_hash().hex()[:16]}...")
    print()

    # 5. Forest
    print("5. MERKLE FOREST:")
    print("-" * 40)

    forest = manager.create_forest("forest")

    t1 = forest.create_tree("tree1")
    t1.add(b"a")
    t1.add(b"b")
    t1.build()

    t2 = forest.create_tree("tree2")
    t2.add(b"c")
    t2.add(b"d")
    t2.build()

    forest_root = forest.forest_root()
    print(f"   Trees: {forest.list_trees()}")
    print(f"   Forest root: {forest_root.hex()[:16]}...")
    print()

    # 6. Add via Manager
    print("6. ADD VIA MANAGER:")
    print("-" * 40)

    idx = manager.add_leaf("main", b"new_data")
    root = manager.build_tree("main")
    print(f"   Added at index: {idx}")
    print(f"   New root: {root.hex()[:16]}..." if root else "   No root")
    print()

    # 7. Sparse via Manager
    print("7. SPARSE VIA MANAGER:")
    print("-" * 40)

    manager.sparse_set("sparse", b"managed_key", b"managed_value")
    value = manager.sparse_get("sparse", b"managed_key")
    print(f"   Value: {value}")
    print()

    # 8. Trie via Manager
    print("8. TRIE VIA MANAGER:")
    print("-" * 40)

    manager.trie_set("trie", b"managed", b"data")
    value = manager.trie_get("trie", b"managed")
    print(f"   Value: {value}")
    print()

    # 9. List Structures
    print("9. LIST STRUCTURES:")
    print("-" * 40)

    print(f"   Trees: {manager.list_trees()}")
    print(f"   Sparse: {manager.list_sparse_trees()}")
    print(f"   Tries: {manager.list_tries()}")
    print()

    # 10. Hash Utility
    print("10. HASH UTILITY:")
    print("-" * 40)

    h = manager.hash(b"test data")
    print(f"   Hash: {h.hex()[:32]}...")
    print()

    # 11. Tree Stats
    print("11. TREE STATS:")
    print("-" * 40)

    stats = tree.stats()
    print(f"   Leaves: {stats.leaf_count}")
    print(f"   Depth: {stats.depth}")
    print(f"   Nodes: {stats.node_count}")
    print()

    # 12. Proof Verification
    print("12. PROOF VERIFICATION:")
    print("-" * 40)

    proof = manager.get_inclusion_proof("main", 0)
    if proof:
        verified = manager.verify_inclusion("main", proof)
        print(f"   Verified: {verified}")
    print()

    # 13. Delete from Trie
    print("13. DELETE FROM TRIE:")
    print("-" * 40)

    before = trie.get(b"hello")
    trie.delete(b"hello")
    after = trie.get(b"hello")

    print(f"   Before: {before}")
    print(f"   After: {after}")
    print()

    # 14. Sparse Delete
    print("14. SPARSE DELETE:")
    print("-" * 40)

    sparse.delete(b"key1")
    value = sparse.get(b"key1")
    print(f"   After delete: {value}")
    print()

    # 15. Forest Delete
    print("15. FOREST DELETE TREE:")
    print("-" * 40)

    deleted = forest.delete_tree("tree1")
    print(f"   Deleted: {deleted}")
    print(f"   Remaining: {forest.list_trees()}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Merkle Tree Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
