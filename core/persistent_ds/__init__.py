"""
BAEL Persistent Data Structures Engine
=======================================

Functional persistent data structures with full history.

"Ba'el remembers all versions." — Ba'el
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple, Generic, TypeVar, Iterator
from dataclasses import dataclass, field
from copy import copy
import math

logger = logging.getLogger("BAEL.PersistentDataStructures")


T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# PERSISTENT ARRAY
# ============================================================================

@dataclass
class PArrayNode(Generic[T]):
    """Node in persistent array tree."""
    value: Optional[T] = None
    left: Optional['PArrayNode[T]'] = None
    right: Optional['PArrayNode[T]'] = None


class PersistentArray(Generic[T]):
    """
    Persistent array with O(log n) operations.

    Features:
    - Full persistence (all versions accessible)
    - O(log n) get and set
    - O(1) version creation

    "Ba'el arrays persist through time." — Ba'el
    """

    def __init__(self, size: int = 0, default: T = None):
        """Initialize persistent array."""
        self._size = size
        self._default = default
        self._root: Optional[PArrayNode[T]] = self._build_tree(0, size - 1)
        self._version = 0
        self._versions: Dict[int, 'PersistentArray[T]'] = {0: self}
        self._lock = threading.RLock()

    def _build_tree(self, lo: int, hi: int) -> Optional[PArrayNode[T]]:
        """Build balanced tree for range."""
        if lo > hi:
            return None

        mid = (lo + hi) // 2
        node = PArrayNode(value=self._default)

        if lo < hi:
            node.left = self._build_tree(lo, mid - 1)
            node.right = self._build_tree(mid + 1, hi)

        return node

    def get(self, index: int) -> T:
        """Get element at index."""
        with self._lock:
            if index < 0 or index >= self._size:
                raise IndexError(f"Index {index} out of range")

            return self._get_node(self._root, 0, self._size - 1, index)

    def _get_node(
        self,
        node: Optional[PArrayNode[T]],
        lo: int,
        hi: int,
        index: int
    ) -> T:
        """Get value from tree."""
        if node is None:
            return self._default

        mid = (lo + hi) // 2

        if index == mid:
            return node.value
        elif index < mid:
            return self._get_node(node.left, lo, mid - 1, index)
        else:
            return self._get_node(node.right, mid + 1, hi, index)

    def set(self, index: int, value: T) -> 'PersistentArray[T]':
        """
        Set element at index, returning new version.

        Original array unchanged.
        """
        with self._lock:
            if index < 0 or index >= self._size:
                raise IndexError(f"Index {index} out of range")

            new_root = self._set_node(self._root, 0, self._size - 1, index, value)

            new_array = PersistentArray.__new__(PersistentArray)
            new_array._size = self._size
            new_array._default = self._default
            new_array._root = new_root
            new_array._version = self._version + 1
            new_array._versions = self._versions
            new_array._versions[new_array._version] = new_array
            new_array._lock = self._lock

            return new_array

    def _set_node(
        self,
        node: Optional[PArrayNode[T]],
        lo: int,
        hi: int,
        index: int,
        value: T
    ) -> PArrayNode[T]:
        """Set value in tree (path copying)."""
        if node is None:
            node = PArrayNode(value=self._default)

        mid = (lo + hi) // 2

        # Path copy
        new_node = PArrayNode(value=node.value, left=node.left, right=node.right)

        if index == mid:
            new_node.value = value
        elif index < mid:
            new_node.left = self._set_node(node.left, lo, mid - 1, index, value)
        else:
            new_node.right = self._set_node(node.right, mid + 1, hi, index, value)

        return new_node

    def __getitem__(self, index: int) -> T:
        return self.get(index)

    def __len__(self) -> int:
        return self._size

    @property
    def version(self) -> int:
        return self._version

    def get_version(self, v: int) -> 'PersistentArray[T]':
        """Get specific version of array."""
        return self._versions.get(v, self)


# ============================================================================
# PERSISTENT LIST (CONS LIST)
# ============================================================================

@dataclass
class PListNode(Generic[T]):
    """Node in persistent linked list."""
    head: T
    tail: Optional['PListNode[T]'] = None


class PersistentList(Generic[T]):
    """
    Persistent singly-linked list.

    Features:
    - O(1) cons (prepend)
    - O(1) head/tail
    - Full structural sharing

    "Ba'el lists persist eternally." — Ba'el
    """

    def __init__(self, node: Optional[PListNode[T]] = None):
        """Initialize persistent list."""
        self._node = node
        self._length = self._compute_length()

    def _compute_length(self) -> int:
        """Compute list length."""
        count = 0
        node = self._node
        while node is not None:
            count += 1
            node = node.tail
        return count

    @staticmethod
    def empty() -> 'PersistentList[T]':
        """Create empty list."""
        return PersistentList(None)

    @staticmethod
    def from_iterable(items: List[T]) -> 'PersistentList[T]':
        """Create list from iterable."""
        result = PersistentList.empty()
        for item in reversed(items):
            result = result.cons(item)
        return result

    def cons(self, value: T) -> 'PersistentList[T]':
        """
        Prepend value, returning new list.

        O(1) operation with structural sharing.
        """
        new_node = PListNode(head=value, tail=self._node)
        result = PersistentList(new_node)
        result._length = self._length + 1
        return result

    def head(self) -> Optional[T]:
        """Get first element."""
        return self._node.head if self._node else None

    def tail(self) -> 'PersistentList[T]':
        """
        Get list without first element.

        O(1) operation with structural sharing.
        """
        if self._node is None:
            return PersistentList.empty()

        result = PersistentList(self._node.tail)
        result._length = max(0, self._length - 1)
        return result

    def is_empty(self) -> bool:
        """Check if list is empty."""
        return self._node is None

    def __len__(self) -> int:
        return self._length

    def __iter__(self) -> Iterator[T]:
        node = self._node
        while node is not None:
            yield node.head
            node = node.tail

    def to_list(self) -> List[T]:
        """Convert to Python list."""
        return list(self)


# ============================================================================
# PERSISTENT TREEMAP (RED-BLACK TREE)
# ============================================================================

class Color:
    RED = True
    BLACK = False


@dataclass
class RBNode(Generic[K, V]):
    """Red-black tree node."""
    key: K
    value: V
    color: bool = Color.RED
    left: Optional['RBNode[K, V]'] = None
    right: Optional['RBNode[K, V]'] = None


class PersistentTreeMap(Generic[K, V]):
    """
    Persistent red-black tree map.

    Features:
    - O(log n) get, insert, delete
    - Full persistence via path copying
    - Maintains balance

    "Ba'el maps persist in balance." — Ba'el
    """

    def __init__(self, root: Optional[RBNode[K, V]] = None, size: int = 0):
        """Initialize persistent treemap."""
        self._root = root
        self._size = size
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> 'PersistentTreeMap[K, V]':
        """Create empty map."""
        return PersistentTreeMap()

    def get(self, key: K) -> Optional[V]:
        """Get value for key."""
        with self._lock:
            node = self._root
            while node is not None:
                if key == node.key:
                    return node.value
                elif key < node.key:
                    node = node.left
                else:
                    node = node.right
            return None

    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    def insert(self, key: K, value: V) -> 'PersistentTreeMap[K, V]':
        """
        Insert key-value, returning new map.

        Original map unchanged.
        """
        with self._lock:
            new_root, added = self._insert(self._root, key, value)

            if new_root is not None:
                new_root = self._copy_node(new_root)
                new_root.color = Color.BLACK

            new_size = self._size + (1 if added else 0)
            return PersistentTreeMap(new_root, new_size)

    def _copy_node(self, node: RBNode[K, V]) -> RBNode[K, V]:
        """Create shallow copy of node."""
        return RBNode(
            key=node.key,
            value=node.value,
            color=node.color,
            left=node.left,
            right=node.right
        )

    def _insert(
        self,
        node: Optional[RBNode[K, V]],
        key: K,
        value: V
    ) -> Tuple[RBNode[K, V], bool]:
        """Insert with path copying."""
        if node is None:
            return RBNode(key=key, value=value, color=Color.RED), True

        new_node = self._copy_node(node)
        added = False

        if key == new_node.key:
            new_node.value = value
        elif key < new_node.key:
            new_node.left, added = self._insert(new_node.left, key, value)
        else:
            new_node.right, added = self._insert(new_node.right, key, value)

        # Balance
        return self._balance(new_node), added

    def _balance(self, node: RBNode[K, V]) -> RBNode[K, V]:
        """Balance red-black tree."""
        # Left-left red
        if (self._is_red(node.left) and
            node.left and self._is_red(node.left.left)):
            node = self._rotate_right(node)
            node.left.color = Color.BLACK

        # Left-right red
        elif (self._is_red(node.left) and
              node.left and self._is_red(node.left.right)):
            node.left = self._rotate_left(node.left)
            node = self._rotate_right(node)
            node.left.color = Color.BLACK

        # Right-right red
        elif (self._is_red(node.right) and
              node.right and self._is_red(node.right.right)):
            node = self._rotate_left(node)
            node.right.color = Color.BLACK

        # Right-left red
        elif (self._is_red(node.right) and
              node.right and self._is_red(node.right.left)):
            node.right = self._rotate_right(node.right)
            node = self._rotate_left(node)
            node.right.color = Color.BLACK

        # Two red children - color flip
        elif self._is_red(node.left) and self._is_red(node.right):
            node.color = Color.RED
            if node.left:
                node.left = self._copy_node(node.left)
                node.left.color = Color.BLACK
            if node.right:
                node.right = self._copy_node(node.right)
                node.right.color = Color.BLACK

        return node

    def _is_red(self, node: Optional[RBNode[K, V]]) -> bool:
        """Check if node is red."""
        return node is not None and node.color == Color.RED

    def _rotate_left(self, node: RBNode[K, V]) -> RBNode[K, V]:
        """Left rotation."""
        new_root = self._copy_node(node.right)
        node = self._copy_node(node)
        node.right = new_root.left
        new_root.left = node
        new_root.color = node.color
        node.color = Color.RED
        return new_root

    def _rotate_right(self, node: RBNode[K, V]) -> RBNode[K, V]:
        """Right rotation."""
        new_root = self._copy_node(node.left)
        node = self._copy_node(node)
        node.left = new_root.right
        new_root.right = node
        new_root.color = node.color
        node.color = Color.RED
        return new_root

    def keys(self) -> List[K]:
        """Get all keys in order."""
        result = []
        self._inorder(self._root, result)
        return result

    def _inorder(self, node: Optional[RBNode[K, V]], result: List[K]):
        """In-order traversal."""
        if node is None:
            return
        self._inorder(node.left, result)
        result.append(node.key)
        self._inorder(node.right, result)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: K) -> bool:
        return self.contains(key)


# ============================================================================
# PERSISTENT VECTOR (BITMAPPED VECTOR TRIE)
# ============================================================================

class PersistentVector(Generic[T]):
    """
    Persistent vector using wide branching trie.

    Features:
    - O(log32 n) ≈ O(1) get/set
    - Efficient append
    - Wide branching (32-way)

    "Ba'el vectors persist with width." — Ba'el
    """

    BITS = 5
    WIDTH = 32  # 2^5
    MASK = 31   # 2^5 - 1

    def __init__(
        self,
        size: int = 0,
        shift: int = BITS,
        root: Optional[List] = None,
        tail: Optional[List[T]] = None
    ):
        """Initialize persistent vector."""
        self._size = size
        self._shift = shift
        self._root = root if root is not None else []
        self._tail = tail if tail is not None else []
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> 'PersistentVector[T]':
        """Create empty vector."""
        return PersistentVector()

    @staticmethod
    def from_list(items: List[T]) -> 'PersistentVector[T]':
        """Create vector from list."""
        result = PersistentVector.empty()
        for item in items:
            result = result.append(item)
        return result

    def _tail_offset(self) -> int:
        """Calculate where tail starts."""
        if self._size < self.WIDTH:
            return 0
        return ((self._size - 1) >> self.BITS) << self.BITS

    def get(self, index: int) -> T:
        """Get element at index."""
        with self._lock:
            if index < 0 or index >= self._size:
                raise IndexError(f"Index {index} out of range")

            if index >= self._tail_offset():
                return self._tail[index - self._tail_offset()]

            # Navigate tree
            node = self._root
            level = self._shift

            while level > 0:
                node = node[(index >> level) & self.MASK]
                level -= self.BITS

            return node[index & self.MASK]

    def set(self, index: int, value: T) -> 'PersistentVector[T]':
        """
        Set element at index, returning new vector.
        """
        with self._lock:
            if index < 0 or index >= self._size:
                raise IndexError(f"Index {index} out of range")

            if index >= self._tail_offset():
                new_tail = self._tail[:]
                new_tail[index - self._tail_offset()] = value
                return PersistentVector(
                    self._size, self._shift, self._root, new_tail
                )

            # Update in tree with path copying
            new_root = self._set_in_tree(self._root, self._shift, index, value)
            return PersistentVector(
                self._size, self._shift, new_root, self._tail[:]
            )

    def _set_in_tree(
        self,
        node: List,
        level: int,
        index: int,
        value: T
    ) -> List:
        """Set value in tree with path copying."""
        new_node = node[:]

        if level == 0:
            new_node[index & self.MASK] = value
        else:
            subidx = (index >> level) & self.MASK
            new_node[subidx] = self._set_in_tree(
                node[subidx], level - self.BITS, index, value
            )

        return new_node

    def append(self, value: T) -> 'PersistentVector[T]':
        """
        Append value, returning new vector.
        """
        with self._lock:
            # Room in tail?
            if len(self._tail) < self.WIDTH:
                new_tail = self._tail + [value]
                return PersistentVector(
                    self._size + 1, self._shift, self._root, new_tail
                )

            # Push tail into tree
            new_root, new_shift = self._push_tail(
                self._root, self._shift, self._tail
            )

            return PersistentVector(
                self._size + 1, new_shift, new_root, [value]
            )

    def _push_tail(
        self,
        root: List,
        shift: int,
        tail: List[T]
    ) -> Tuple[List, int]:
        """Push tail into tree."""
        # Tree is full?
        if (self._size >> self.BITS) > (1 << shift):
            new_root = [root, self._new_path(shift, tail)]
            return new_root, shift + self.BITS

        new_root = self._push_tail_internal(root, shift, tail)
        return new_root, shift

    def _push_tail_internal(
        self,
        node: List,
        level: int,
        tail: List[T]
    ) -> List:
        """Push tail into subtree."""
        if level == self.BITS:
            return node + [tail]

        new_node = node[:]
        subidx = ((self._size - 1) >> level) & self.MASK

        if subidx < len(node):
            child = self._push_tail_internal(node[subidx], level - self.BITS, tail)
            new_node[subidx] = child
        else:
            new_node.append(self._new_path(level - self.BITS, tail))

        return new_node

    def _new_path(self, level: int, tail: List[T]) -> List:
        """Create new path to tail."""
        if level == 0:
            return tail
        return [self._new_path(level - self.BITS, tail)]

    def __getitem__(self, index: int) -> T:
        return self.get(index)

    def __len__(self) -> int:
        return self._size

    def to_list(self) -> List[T]:
        """Convert to Python list."""
        return [self.get(i) for i in range(self._size)]


# ============================================================================
# PERSISTENT STACK
# ============================================================================

class PersistentStack(Generic[T]):
    """
    Persistent stack using persistent list.

    "Ba'el stacks persist in LIFO." — Ba'el
    """

    def __init__(self, lst: Optional[PersistentList[T]] = None):
        """Initialize persistent stack."""
        self._list = lst if lst else PersistentList.empty()

    @staticmethod
    def empty() -> 'PersistentStack[T]':
        """Create empty stack."""
        return PersistentStack()

    def push(self, value: T) -> 'PersistentStack[T]':
        """Push value, returning new stack."""
        return PersistentStack(self._list.cons(value))

    def pop(self) -> Tuple[Optional[T], 'PersistentStack[T]']:
        """Pop value, returning (value, new_stack)."""
        if self._list.is_empty():
            return None, self
        return self._list.head(), PersistentStack(self._list.tail())

    def peek(self) -> Optional[T]:
        """Peek at top without popping."""
        return self._list.head()

    def is_empty(self) -> bool:
        """Check if stack is empty."""
        return self._list.is_empty()

    def __len__(self) -> int:
        return len(self._list)


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_persistent_array(size: int, default: T = None) -> PersistentArray[T]:
    """Create persistent array."""
    return PersistentArray(size, default)


def create_persistent_list() -> PersistentList[T]:
    """Create empty persistent list."""
    return PersistentList.empty()


def create_persistent_treemap() -> PersistentTreeMap[K, V]:
    """Create empty persistent treemap."""
    return PersistentTreeMap.empty()


def create_persistent_vector() -> PersistentVector[T]:
    """Create empty persistent vector."""
    return PersistentVector.empty()


def create_persistent_stack() -> PersistentStack[T]:
    """Create empty persistent stack."""
    return PersistentStack.empty()
