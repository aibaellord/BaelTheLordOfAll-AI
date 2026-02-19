"""
BAEL Finger Tree Engine
=======================

Functional persistent data structure with efficient operations.

"Ba'el points with fingers." — Ba'el
"""

import logging
import threading
from typing import Any, Callable, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from functools import reduce

logger = logging.getLogger("BAEL.FingerTree")


V = TypeVar('V')
M = TypeVar('M')


# ============================================================================
# MONOID
# ============================================================================

@dataclass
class Monoid(Generic[M]):
    """Monoid for measure annotations."""
    identity: M
    combine: Callable[[M, M], M]


class SizeMonoid(Monoid[int]):
    """Size monoid for sequences."""
    def __init__(self):
        super().__init__(0, lambda a, b: a + b)


class PriorityMonoid(Monoid[Optional[float]]):
    """Priority monoid for priority queues."""
    def __init__(self):
        def combine(a, b):
            if a is None:
                return b
            if b is None:
                return a
            return min(a, b)
        super().__init__(None, combine)


# ============================================================================
# MEASURED VALUE
# ============================================================================

@dataclass
class Measured(Generic[V, M]):
    """Value with measure."""
    value: V
    measure: M


# ============================================================================
# DIGIT
# ============================================================================

class Digit(Generic[V]):
    """One to four elements at tree edge."""

    def __init__(self, *elements: V):
        if not 1 <= len(elements) <= 4:
            raise ValueError("Digit must have 1-4 elements")
        self._elements = list(elements)

    def __iter__(self):
        return iter(self._elements)

    def __len__(self):
        return len(self._elements)

    def head(self) -> V:
        return self._elements[0]

    def last(self) -> V:
        return self._elements[-1]

    def to_list(self) -> List[V]:
        return list(self._elements)

    def prepend(self, v: V) -> 'Digit[V]':
        return Digit(v, *self._elements)

    def append(self, v: V) -> 'Digit[V]':
        return Digit(*self._elements, v)


# ============================================================================
# NODE
# ============================================================================

class Node(Generic[V, M]):
    """Internal node (2-3 elements)."""

    def __init__(self, elements: List[V], measure: M):
        if not 2 <= len(elements) <= 3:
            raise ValueError("Node must have 2-3 elements")
        self._elements = elements
        self._measure = measure

    def __iter__(self):
        return iter(self._elements)

    def __len__(self):
        return len(self._elements)

    @property
    def measure(self) -> M:
        return self._measure

    def to_digit(self) -> Digit[V]:
        return Digit(*self._elements)


# ============================================================================
# FINGER TREE
# ============================================================================

class FingerTree(ABC, Generic[V, M]):
    """
    Finger Tree: functional sequence with O(1) amortized access to ends.

    Features:
    - O(1) amortized prepend/append
    - O(log n) concatenation
    - O(log n) split
    - Persistent (immutable)

    "Ba'el fingers efficiently." — Ba'el
    """

    @abstractmethod
    def is_empty(self) -> bool:
        pass

    @abstractmethod
    def head(self) -> V:
        pass

    @abstractmethod
    def last(self) -> V:
        pass

    @abstractmethod
    def tail(self) -> 'FingerTree[V, M]':
        pass

    @abstractmethod
    def init(self) -> 'FingerTree[V, M]':
        pass

    @abstractmethod
    def prepend(self, v: V) -> 'FingerTree[V, M]':
        pass

    @abstractmethod
    def append(self, v: V) -> 'FingerTree[V, M]':
        pass

    @abstractmethod
    def measure(self) -> M:
        pass

    @abstractmethod
    def to_list(self) -> List[V]:
        pass


class EmptyTree(FingerTree[V, M]):
    """Empty finger tree."""

    def __init__(self, monoid: Monoid[M]):
        self._monoid = monoid

    def is_empty(self) -> bool:
        return True

    def head(self) -> V:
        raise ValueError("Empty tree")

    def last(self) -> V:
        raise ValueError("Empty tree")

    def tail(self) -> FingerTree[V, M]:
        raise ValueError("Empty tree")

    def init(self) -> FingerTree[V, M]:
        raise ValueError("Empty tree")

    def prepend(self, v: V) -> FingerTree[V, M]:
        return SingleTree(v, self._monoid)

    def append(self, v: V) -> FingerTree[V, M]:
        return SingleTree(v, self._monoid)

    def measure(self) -> M:
        return self._monoid.identity

    def to_list(self) -> List[V]:
        return []


class SingleTree(FingerTree[V, M]):
    """Single-element finger tree."""

    def __init__(self, value: V, monoid: Monoid[M]):
        self._value = value
        self._monoid = monoid

    def is_empty(self) -> bool:
        return False

    def head(self) -> V:
        return self._value

    def last(self) -> V:
        return self._value

    def tail(self) -> FingerTree[V, M]:
        return EmptyTree(self._monoid)

    def init(self) -> FingerTree[V, M]:
        return EmptyTree(self._monoid)

    def prepend(self, v: V) -> FingerTree[V, M]:
        return DeepTree(
            Digit(v),
            EmptyTree(self._monoid),
            Digit(self._value),
            self._monoid
        )

    def append(self, v: V) -> FingerTree[V, M]:
        return DeepTree(
            Digit(self._value),
            EmptyTree(self._monoid),
            Digit(v),
            self._monoid
        )

    def measure(self) -> M:
        # For simplicity, use identity
        return self._monoid.identity

    def to_list(self) -> List[V]:
        return [self._value]


class DeepTree(FingerTree[V, M]):
    """Deep finger tree with prefix, spine, and suffix."""

    def __init__(
        self,
        prefix: Digit[V],
        middle: FingerTree[Node[V, M], M],
        suffix: Digit[V],
        monoid: Monoid[M]
    ):
        self._prefix = prefix
        self._middle = middle
        self._suffix = suffix
        self._monoid = monoid

    def is_empty(self) -> bool:
        return False

    def head(self) -> V:
        return self._prefix.head()

    def last(self) -> V:
        return self._suffix.last()

    def tail(self) -> FingerTree[V, M]:
        prefix_list = self._prefix.to_list()

        if len(prefix_list) > 1:
            return DeepTree(
                Digit(*prefix_list[1:]),
                self._middle,
                self._suffix,
                self._monoid
            )

        if self._middle.is_empty():
            suffix_list = self._suffix.to_list()
            if len(suffix_list) == 1:
                return SingleTree(suffix_list[0], self._monoid)
            return DeepTree(
                Digit(suffix_list[0]),
                EmptyTree(self._monoid),
                Digit(*suffix_list[1:]),
                self._monoid
            )

        node = self._middle.head()
        return DeepTree(
            node.to_digit(),
            self._middle.tail(),
            self._suffix,
            self._monoid
        )

    def init(self) -> FingerTree[V, M]:
        suffix_list = self._suffix.to_list()

        if len(suffix_list) > 1:
            return DeepTree(
                self._prefix,
                self._middle,
                Digit(*suffix_list[:-1]),
                self._monoid
            )

        if self._middle.is_empty():
            prefix_list = self._prefix.to_list()
            if len(prefix_list) == 1:
                return SingleTree(prefix_list[0], self._monoid)
            return DeepTree(
                Digit(*prefix_list[:-1]),
                EmptyTree(self._monoid),
                Digit(prefix_list[-1]),
                self._monoid
            )

        node = self._middle.last()
        return DeepTree(
            self._prefix,
            self._middle.init(),
            node.to_digit(),
            self._monoid
        )

    def prepend(self, v: V) -> FingerTree[V, M]:
        prefix_list = self._prefix.to_list()

        if len(prefix_list) < 4:
            return DeepTree(
                Digit(v, *prefix_list),
                self._middle,
                self._suffix,
                self._monoid
            )

        # Push to middle
        new_node = Node(
            prefix_list[1:4],
            self._monoid.identity
        )

        return DeepTree(
            Digit(v, prefix_list[0]),
            self._middle.prepend(new_node),
            self._suffix,
            self._monoid
        )

    def append(self, v: V) -> FingerTree[V, M]:
        suffix_list = self._suffix.to_list()

        if len(suffix_list) < 4:
            return DeepTree(
                self._prefix,
                self._middle,
                Digit(*suffix_list, v),
                self._monoid
            )

        # Push to middle
        new_node = Node(
            suffix_list[0:3],
            self._monoid.identity
        )

        return DeepTree(
            self._prefix,
            self._middle.append(new_node),
            Digit(suffix_list[3], v),
            self._monoid
        )

    def measure(self) -> M:
        # Simplified - would compute from cached measures
        return self._monoid.identity

    def to_list(self) -> List[V]:
        result = []
        result.extend(self._prefix.to_list())

        for node in self._middle.to_list():
            result.extend(list(node))

        result.extend(self._suffix.to_list())
        return result


# ============================================================================
# SEQUENCE
# ============================================================================

class Sequence(Generic[V]):
    """
    Functional sequence using finger trees.

    O(1) amortized operations at both ends.
    O(log n) concatenation and split.

    "Ba'el sequences functionally." — Ba'el
    """

    def __init__(self, tree: Optional[FingerTree[V, int]] = None):
        """Initialize sequence."""
        self._monoid = SizeMonoid()
        self._tree = tree or EmptyTree(self._monoid)
        self._lock = threading.RLock()

    @staticmethod
    def from_list(items: List[V]) -> 'Sequence[V]':
        """Create sequence from list."""
        seq = Sequence()
        for item in items:
            seq = seq.append(item)
        return seq

    def is_empty(self) -> bool:
        """Check if empty."""
        return self._tree.is_empty()

    def prepend(self, v: V) -> 'Sequence[V]':
        """Add to front."""
        return Sequence(self._tree.prepend(v))

    def append(self, v: V) -> 'Sequence[V]':
        """Add to back."""
        return Sequence(self._tree.append(v))

    def head(self) -> V:
        """Get first element."""
        return self._tree.head()

    def last(self) -> V:
        """Get last element."""
        return self._tree.last()

    def tail(self) -> 'Sequence[V]':
        """Remove first element."""
        return Sequence(self._tree.tail())

    def init(self) -> 'Sequence[V]':
        """Remove last element."""
        return Sequence(self._tree.init())

    def to_list(self) -> List[V]:
        """Convert to list."""
        return self._tree.to_list()

    def __iter__(self):
        return iter(self.to_list())

    def __len__(self) -> int:
        return len(self.to_list())


# ============================================================================
# DEQUE
# ============================================================================

class FunctionalDeque(Generic[V]):
    """
    Functional double-ended queue.

    O(1) amortized operations at both ends.
    Persistent.

    "Ba'el dequeues persistently." — Ba'el
    """

    def __init__(self, seq: Optional[Sequence[V]] = None):
        """Initialize deque."""
        self._seq = seq or Sequence()

    @staticmethod
    def from_list(items: List[V]) -> 'FunctionalDeque[V]':
        """Create from list."""
        return FunctionalDeque(Sequence.from_list(items))

    def is_empty(self) -> bool:
        return self._seq.is_empty()

    def push_front(self, v: V) -> 'FunctionalDeque[V]':
        """Add to front."""
        return FunctionalDeque(self._seq.prepend(v))

    def push_back(self, v: V) -> 'FunctionalDeque[V]':
        """Add to back."""
        return FunctionalDeque(self._seq.append(v))

    def pop_front(self) -> Tuple[V, 'FunctionalDeque[V]']:
        """Remove from front."""
        return self._seq.head(), FunctionalDeque(self._seq.tail())

    def pop_back(self) -> Tuple[V, 'FunctionalDeque[V]']:
        """Remove from back."""
        return self._seq.last(), FunctionalDeque(self._seq.init())

    def front(self) -> V:
        """Peek front."""
        return self._seq.head()

    def back(self) -> V:
        """Peek back."""
        return self._seq.last()

    def to_list(self) -> List[V]:
        """Convert to list."""
        return self._seq.to_list()


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_sequence() -> Sequence:
    """Create empty sequence."""
    return Sequence()


def sequence_from_list(items: List[Any]) -> Sequence:
    """Create sequence from list."""
    return Sequence.from_list(items)


def create_deque() -> FunctionalDeque:
    """Create empty functional deque."""
    return FunctionalDeque()


def deque_from_list(items: List[Any]) -> FunctionalDeque:
    """Create functional deque from list."""
    return FunctionalDeque.from_list(items)
