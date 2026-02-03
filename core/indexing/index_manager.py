#!/usr/bin/env python3
"""
BAEL - Index Manager
Advanced indexing for AI agent operations.

Features:
- Multiple index types
- Full-text indexing
- Inverted indexes
- B-tree indexes
- Hash indexes
- Composite indexes
- Index maintenance
- Query optimization
- Statistics tracking
- Concurrent access
"""

import asyncio
import bisect
import hashlib
import re
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

class IndexType(Enum):
    """Index types."""
    HASH = "hash"
    BTREE = "btree"
    INVERTED = "inverted"
    FULLTEXT = "fulltext"
    COMPOSITE = "composite"
    SPATIAL = "spatial"
    BITMAP = "bitmap"


class IndexState(Enum):
    """Index state."""
    BUILDING = "building"
    READY = "ready"
    UPDATING = "updating"
    INVALID = "invalid"
    DROPPED = "dropped"


class QueryOperator(Enum):
    """Query operators."""
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    IN = "in"
    LIKE = "like"
    PREFIX = "prefix"
    RANGE = "range"


class SortOrder(Enum):
    """Sort order."""
    ASC = "asc"
    DESC = "desc"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class IndexConfig:
    """Index configuration."""
    name: str = ""
    index_type: IndexType = IndexType.HASH
    fields: List[str] = field(default_factory=list)
    unique: bool = False
    sparse: bool = False
    case_sensitive: bool = True
    analyzer: Optional[str] = None


@dataclass
class IndexStats:
    """Index statistics."""
    name: str = ""
    index_type: IndexType = IndexType.HASH
    entry_count: int = 0
    unique_keys: int = 0
    memory_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    lookups: int = 0
    hits: int = 0
    misses: int = 0


@dataclass
class QueryCondition:
    """Query condition."""
    field: str = ""
    operator: QueryOperator = QueryOperator.EQ
    value: Any = None
    value2: Any = None  # For range queries


@dataclass
class QueryResult:
    """Query result."""
    items: List[Any] = field(default_factory=list)
    count: int = 0
    scan_count: int = 0
    index_used: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class TextToken:
    """Text token for full-text indexing."""
    term: str = ""
    position: int = 0
    doc_id: str = ""
    field: str = ""


# =============================================================================
# INDEX INTERFACE
# =============================================================================

class Index(ABC, Generic[K, V]):
    """Base index interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get index name."""
        pass

    @property
    @abstractmethod
    def index_type(self) -> IndexType:
        """Get index type."""
        pass

    @abstractmethod
    def insert(self, key: K, value: V) -> None:
        """Insert entry."""
        pass

    @abstractmethod
    def delete(self, key: K, value: Optional[V] = None) -> bool:
        """Delete entry."""
        pass

    @abstractmethod
    def lookup(self, key: K) -> List[V]:
        """Lookup by key."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear index."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Get entry count."""
        pass


# =============================================================================
# HASH INDEX
# =============================================================================

class HashIndex(Index[Any, str]):
    """Hash-based index for exact lookups."""

    def __init__(self, config: IndexConfig):
        self._name = config.name
        self._fields = config.fields
        self._unique = config.unique
        self._data: Dict[int, List[str]] = defaultdict(list)
        self._reverse: Dict[str, int] = {}
        self._stats = IndexStats(
            name=config.name,
            index_type=IndexType.HASH
        )
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def index_type(self) -> IndexType:
        return IndexType.HASH

    def _compute_hash(self, key: Any) -> int:
        """Compute hash for key."""
        if isinstance(key, (list, tuple)):
            key_str = "|".join(str(k) for k in key)
        else:
            key_str = str(key)

        return hash(key_str)

    def insert(self, key: Any, value: str) -> None:
        """Insert entry."""
        h = self._compute_hash(key)

        with self._lock:
            if self._unique and h in self._data and self._data[h]:
                raise ValueError(f"Duplicate key: {key}")

            if value not in self._data[h]:
                self._data[h].append(value)
                self._reverse[value] = h
                self._stats.entry_count += 1

            self._stats.last_updated = datetime.utcnow()

    def delete(self, key: Any, value: Optional[str] = None) -> bool:
        """Delete entry."""
        h = self._compute_hash(key)

        with self._lock:
            if h not in self._data:
                return False

            if value:
                if value in self._data[h]:
                    self._data[h].remove(value)
                    del self._reverse[value]
                    self._stats.entry_count -= 1
                    return True
            else:
                count = len(self._data[h])
                for v in self._data[h]:
                    if v in self._reverse:
                        del self._reverse[v]
                del self._data[h]
                self._stats.entry_count -= count
                return count > 0

        return False

    def lookup(self, key: Any) -> List[str]:
        """Lookup by key."""
        h = self._compute_hash(key)

        with self._lock:
            self._stats.lookups += 1

            if h in self._data:
                self._stats.hits += 1
                return list(self._data[h])

            self._stats.misses += 1
            return []

    def clear(self) -> None:
        """Clear index."""
        with self._lock:
            self._data.clear()
            self._reverse.clear()
            self._stats.entry_count = 0

    def count(self) -> int:
        """Get entry count."""
        with self._lock:
            return self._stats.entry_count

    def get_stats(self) -> IndexStats:
        """Get statistics."""
        with self._lock:
            self._stats.unique_keys = len(self._data)
            self._stats.memory_bytes = len(str(self._data)) + len(str(self._reverse))
            return self._stats


# =============================================================================
# B-TREE INDEX
# =============================================================================

class BTreeIndex(Index[Any, str]):
    """B-tree index for range queries."""

    def __init__(self, config: IndexConfig):
        self._name = config.name
        self._fields = config.fields
        self._unique = config.unique
        self._keys: List[Any] = []
        self._values: Dict[Any, List[str]] = defaultdict(list)
        self._stats = IndexStats(
            name=config.name,
            index_type=IndexType.BTREE
        )
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def index_type(self) -> IndexType:
        return IndexType.BTREE

    def insert(self, key: Any, value: str) -> None:
        """Insert entry."""
        with self._lock:
            if self._unique and key in self._values and self._values[key]:
                raise ValueError(f"Duplicate key: {key}")

            if key not in self._values or not self._values[key]:
                pos = bisect.bisect_left(self._keys, key)
                self._keys.insert(pos, key)

            if value not in self._values[key]:
                self._values[key].append(value)
                self._stats.entry_count += 1

            self._stats.last_updated = datetime.utcnow()

    def delete(self, key: Any, value: Optional[str] = None) -> bool:
        """Delete entry."""
        with self._lock:
            if key not in self._values:
                return False

            if value:
                if value in self._values[key]:
                    self._values[key].remove(value)
                    self._stats.entry_count -= 1

                    if not self._values[key]:
                        del self._values[key]
                        self._keys.remove(key)

                    return True
            else:
                count = len(self._values[key])
                del self._values[key]
                self._keys.remove(key)
                self._stats.entry_count -= count
                return count > 0

        return False

    def lookup(self, key: Any) -> List[str]:
        """Lookup by key."""
        with self._lock:
            self._stats.lookups += 1

            if key in self._values:
                self._stats.hits += 1
                return list(self._values[key])

            self._stats.misses += 1
            return []

    def range(
        self,
        min_key: Any,
        max_key: Any,
        include_min: bool = True,
        include_max: bool = True
    ) -> List[str]:
        """Range query."""
        with self._lock:
            results = []

            start = bisect.bisect_left(self._keys, min_key)
            end = bisect.bisect_right(self._keys, max_key)

            for i in range(start, end):
                key = self._keys[i]

                if key == min_key and not include_min:
                    continue
                if key == max_key and not include_max:
                    continue

                results.extend(self._values[key])

            return results

    def less_than(self, key: Any, inclusive: bool = False) -> List[str]:
        """Less than query."""
        with self._lock:
            results = []

            end = bisect.bisect_right(self._keys, key) if inclusive else bisect.bisect_left(self._keys, key)

            for i in range(0, end):
                results.extend(self._values[self._keys[i]])

            return results

    def greater_than(self, key: Any, inclusive: bool = False) -> List[str]:
        """Greater than query."""
        with self._lock:
            results = []

            start = bisect.bisect_left(self._keys, key) if inclusive else bisect.bisect_right(self._keys, key)

            for i in range(start, len(self._keys)):
                results.extend(self._values[self._keys[i]])

            return results

    def min_key(self) -> Optional[Any]:
        """Get minimum key."""
        with self._lock:
            return self._keys[0] if self._keys else None

    def max_key(self) -> Optional[Any]:
        """Get maximum key."""
        with self._lock:
            return self._keys[-1] if self._keys else None

    def clear(self) -> None:
        """Clear index."""
        with self._lock:
            self._keys.clear()
            self._values.clear()
            self._stats.entry_count = 0

    def count(self) -> int:
        """Get entry count."""
        with self._lock:
            return self._stats.entry_count

    def get_stats(self) -> IndexStats:
        """Get statistics."""
        with self._lock:
            self._stats.unique_keys = len(self._keys)
            return self._stats


# =============================================================================
# INVERTED INDEX
# =============================================================================

class InvertedIndex(Index[str, str]):
    """Inverted index for keyword search."""

    def __init__(self, config: IndexConfig):
        self._name = config.name
        self._fields = config.fields
        self._case_sensitive = config.case_sensitive
        self._postings: Dict[str, Set[str]] = defaultdict(set)
        self._doc_terms: Dict[str, Set[str]] = defaultdict(set)
        self._stats = IndexStats(
            name=config.name,
            index_type=IndexType.INVERTED
        )
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def index_type(self) -> IndexType:
        return IndexType.INVERTED

    def _normalize(self, term: str) -> str:
        """Normalize term."""
        if not self._case_sensitive:
            return term.lower()
        return term

    def insert(self, key: str, value: str) -> None:
        """Insert term for document."""
        term = self._normalize(key)

        with self._lock:
            self._postings[term].add(value)
            self._doc_terms[value].add(term)
            self._stats.entry_count = sum(len(p) for p in self._postings.values())
            self._stats.last_updated = datetime.utcnow()

    def insert_document(self, doc_id: str, text: str) -> None:
        """Insert document with text tokenization."""
        terms = self._tokenize(text)

        with self._lock:
            for term in terms:
                self.insert(term, doc_id)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text."""
        # Simple word tokenization
        words = re.findall(r'\b\w+\b', text)
        return [self._normalize(w) for w in words]

    def delete(self, key: str, value: Optional[str] = None) -> bool:
        """Delete term or document."""
        term = self._normalize(key)

        with self._lock:
            if value:
                if term in self._postings and value in self._postings[term]:
                    self._postings[term].remove(value)
                    if value in self._doc_terms:
                        self._doc_terms[value].discard(term)
                    return True
            else:
                if term in self._postings:
                    del self._postings[term]
                    return True

        return False

    def delete_document(self, doc_id: str) -> bool:
        """Delete all terms for document."""
        with self._lock:
            if doc_id not in self._doc_terms:
                return False

            terms = self._doc_terms.pop(doc_id)

            for term in terms:
                if term in self._postings:
                    self._postings[term].discard(doc_id)
                    if not self._postings[term]:
                        del self._postings[term]

            return True

    def lookup(self, key: str) -> List[str]:
        """Lookup documents by term."""
        term = self._normalize(key)

        with self._lock:
            self._stats.lookups += 1

            if term in self._postings:
                self._stats.hits += 1
                return list(self._postings[term])

            self._stats.misses += 1
            return []

    def search(self, query: str) -> List[str]:
        """Search with multiple terms (AND)."""
        terms = self._tokenize(query)

        if not terms:
            return []

        with self._lock:
            # Get documents for first term
            result_set = self._postings.get(terms[0], set()).copy()

            # Intersect with other terms
            for term in terms[1:]:
                result_set &= self._postings.get(term, set())

            return list(result_set)

    def search_or(self, query: str) -> List[str]:
        """Search with multiple terms (OR)."""
        terms = self._tokenize(query)

        if not terms:
            return []

        with self._lock:
            result_set: Set[str] = set()

            for term in terms:
                result_set |= self._postings.get(term, set())

            return list(result_set)

    def prefix_search(self, prefix: str) -> List[str]:
        """Search by prefix."""
        prefix = self._normalize(prefix)

        with self._lock:
            result_set: Set[str] = set()

            for term, docs in self._postings.items():
                if term.startswith(prefix):
                    result_set |= docs

            return list(result_set)

    def clear(self) -> None:
        """Clear index."""
        with self._lock:
            self._postings.clear()
            self._doc_terms.clear()
            self._stats.entry_count = 0

    def count(self) -> int:
        """Get entry count."""
        with self._lock:
            return len(self._doc_terms)

    def term_count(self) -> int:
        """Get unique term count."""
        with self._lock:
            return len(self._postings)

    def get_stats(self) -> IndexStats:
        """Get statistics."""
        with self._lock:
            self._stats.unique_keys = len(self._postings)
            return self._stats


# =============================================================================
# COMPOSITE INDEX
# =============================================================================

class CompositeIndex(Index[Tuple, str]):
    """Composite index on multiple fields."""

    def __init__(self, config: IndexConfig):
        self._name = config.name
        self._fields = config.fields
        self._unique = config.unique
        self._tree = BTreeIndex(config)
        self._stats = IndexStats(
            name=config.name,
            index_type=IndexType.COMPOSITE
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def index_type(self) -> IndexType:
        return IndexType.COMPOSITE

    def _make_key(self, values: Dict[str, Any]) -> Tuple:
        """Make composite key from values."""
        return tuple(values.get(f) for f in self._fields)

    def insert(self, key: Tuple, value: str) -> None:
        """Insert entry."""
        self._tree.insert(key, value)
        self._stats.entry_count = self._tree.count()

    def insert_doc(self, doc_id: str, values: Dict[str, Any]) -> None:
        """Insert document with field values."""
        key = self._make_key(values)
        self.insert(key, doc_id)

    def delete(self, key: Tuple, value: Optional[str] = None) -> bool:
        """Delete entry."""
        result = self._tree.delete(key, value)
        self._stats.entry_count = self._tree.count()
        return result

    def lookup(self, key: Tuple) -> List[str]:
        """Lookup by composite key."""
        return self._tree.lookup(key)

    def lookup_by_values(self, values: Dict[str, Any]) -> List[str]:
        """Lookup by field values."""
        key = self._make_key(values)
        return self.lookup(key)

    def prefix_match(self, partial_key: Tuple) -> List[str]:
        """Match by prefix of composite key."""
        results = []

        # Get all and filter
        for key in self._tree._keys:
            if key[:len(partial_key)] == partial_key:
                results.extend(self._tree._values[key])

        return results

    def clear(self) -> None:
        """Clear index."""
        self._tree.clear()
        self._stats.entry_count = 0

    def count(self) -> int:
        """Get entry count."""
        return self._tree.count()

    def get_stats(self) -> IndexStats:
        """Get statistics."""
        return self._stats


# =============================================================================
# INDEX MANAGER
# =============================================================================

class IndexManager:
    """
    Index Manager for BAEL.

    Advanced indexing.
    """

    def __init__(self):
        self._indexes: Dict[str, Index] = {}
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._doc_indexes: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # INDEX MANAGEMENT
    # -------------------------------------------------------------------------

    def create_index(self, config: IndexConfig) -> Index:
        """Create an index."""
        with self._lock:
            if config.name in self._indexes:
                raise ValueError(f"Index already exists: {config.name}")

            if config.index_type == IndexType.HASH:
                index = HashIndex(config)
            elif config.index_type == IndexType.BTREE:
                index = BTreeIndex(config)
            elif config.index_type == IndexType.INVERTED:
                index = InvertedIndex(config)
            elif config.index_type == IndexType.COMPOSITE:
                index = CompositeIndex(config)
            else:
                index = HashIndex(config)

            self._indexes[config.name] = index
            return index

    def get_index(self, name: str) -> Optional[Index]:
        """Get index by name."""
        with self._lock:
            return self._indexes.get(name)

    def drop_index(self, name: str) -> bool:
        """Drop an index."""
        with self._lock:
            if name in self._indexes:
                self._indexes[name].clear()
                del self._indexes[name]
                return True
            return False

    def list_indexes(self) -> List[str]:
        """List all index names."""
        with self._lock:
            return list(self._indexes.keys())

    def rebuild_index(self, name: str) -> bool:
        """Rebuild an index from documents."""
        with self._lock:
            index = self._indexes.get(name)
            if not index:
                return False

            index.clear()

            # Re-index all documents
            for doc_id, doc in self._documents.items():
                self._index_document(name, doc_id, doc)

            return True

    # -------------------------------------------------------------------------
    # DOCUMENT OPERATIONS
    # -------------------------------------------------------------------------

    def index_document(
        self,
        doc_id: str,
        document: Dict[str, Any],
        indexes: Optional[List[str]] = None
    ) -> None:
        """Index a document."""
        with self._lock:
            self._documents[doc_id] = document

            target_indexes = indexes or list(self._indexes.keys())

            for index_name in target_indexes:
                self._index_document(index_name, doc_id, document)
                self._doc_indexes[doc_id].add(index_name)

    def _index_document(
        self,
        index_name: str,
        doc_id: str,
        document: Dict[str, Any]
    ) -> None:
        """Index document in specific index."""
        index = self._indexes.get(index_name)
        if not index:
            return

        if isinstance(index, HashIndex):
            # Extract key from fields
            if len(index._fields) == 1:
                key = document.get(index._fields[0])
            else:
                key = tuple(document.get(f) for f in index._fields)

            if key is not None:
                index.insert(key, doc_id)

        elif isinstance(index, BTreeIndex):
            if len(index._fields) == 1:
                key = document.get(index._fields[0])
            else:
                key = tuple(document.get(f) for f in index._fields)

            if key is not None:
                index.insert(key, doc_id)

        elif isinstance(index, InvertedIndex):
            for field in index._fields:
                text = document.get(field)
                if isinstance(text, str):
                    index.insert_document(doc_id, text)

        elif isinstance(index, CompositeIndex):
            key = tuple(document.get(f) for f in index._fields)
            if all(k is not None for k in key):
                index.insert(key, doc_id)

    def remove_document(self, doc_id: str) -> bool:
        """Remove document from all indexes."""
        with self._lock:
            if doc_id not in self._documents:
                return False

            document = self._documents.pop(doc_id)
            indexed_in = self._doc_indexes.pop(doc_id, set())

            for index_name in indexed_in:
                index = self._indexes.get(index_name)
                if index:
                    if isinstance(index, InvertedIndex):
                        index.delete_document(doc_id)
                    else:
                        # For other indexes, we need the key
                        if hasattr(index, '_fields'):
                            if len(index._fields) == 1:
                                key = document.get(index._fields[0])
                            else:
                                key = tuple(document.get(f) for f in index._fields)

                            if key is not None:
                                index.delete(key, doc_id)

            return True

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        with self._lock:
            return self._documents.get(doc_id)

    # -------------------------------------------------------------------------
    # QUERY OPERATIONS
    # -------------------------------------------------------------------------

    def query(
        self,
        conditions: List[QueryCondition],
        index_hint: Optional[str] = None,
        limit: Optional[int] = None,
        sort_field: Optional[str] = None,
        sort_order: SortOrder = SortOrder.ASC
    ) -> QueryResult:
        """Query documents using conditions."""
        start = time.time()

        with self._lock:
            # Select index
            index_name = index_hint or self._select_index(conditions)

            # Execute query
            if index_name:
                doc_ids = self._query_with_index(conditions, index_name)
            else:
                doc_ids = self._query_scan(conditions)

            # Get documents
            docs = [
                self._documents[did]
                for did in doc_ids
                if did in self._documents
            ]

            # Sort if requested
            if sort_field:
                reverse = sort_order == SortOrder.DESC
                docs.sort(key=lambda d: d.get(sort_field, ""), reverse=reverse)

            # Apply limit
            if limit:
                docs = docs[:limit]

            duration = (time.time() - start) * 1000

            return QueryResult(
                items=docs,
                count=len(docs),
                scan_count=len(doc_ids),
                index_used=index_name,
                duration_ms=duration
            )

    def _select_index(self, conditions: List[QueryCondition]) -> Optional[str]:
        """Select best index for query."""
        if not conditions:
            return None

        # Simple selection: find index that covers first condition
        for cond in conditions:
            for name, index in self._indexes.items():
                if hasattr(index, '_fields') and cond.field in index._fields:
                    return name

        return None

    def _query_with_index(
        self,
        conditions: List[QueryCondition],
        index_name: str
    ) -> List[str]:
        """Query using index."""
        index = self._indexes.get(index_name)
        if not index:
            return self._query_scan(conditions)

        result_set: Optional[Set[str]] = None

        for cond in conditions:
            matches = self._apply_condition(index, cond)
            match_set = set(matches)

            if result_set is None:
                result_set = match_set
            else:
                result_set &= match_set

        return list(result_set) if result_set else []

    def _apply_condition(
        self,
        index: Index,
        condition: QueryCondition
    ) -> List[str]:
        """Apply condition to index."""
        if condition.operator == QueryOperator.EQ:
            return index.lookup(condition.value)

        elif condition.operator == QueryOperator.IN:
            results = []
            for val in condition.value:
                results.extend(index.lookup(val))
            return results

        elif isinstance(index, BTreeIndex):
            if condition.operator == QueryOperator.LT:
                return index.less_than(condition.value, inclusive=False)
            elif condition.operator == QueryOperator.LE:
                return index.less_than(condition.value, inclusive=True)
            elif condition.operator == QueryOperator.GT:
                return index.greater_than(condition.value, inclusive=False)
            elif condition.operator == QueryOperator.GE:
                return index.greater_than(condition.value, inclusive=True)
            elif condition.operator == QueryOperator.RANGE:
                return index.range(condition.value, condition.value2)

        elif isinstance(index, InvertedIndex):
            if condition.operator == QueryOperator.LIKE:
                return index.search(condition.value)
            elif condition.operator == QueryOperator.PREFIX:
                return index.prefix_search(condition.value)

        return []

    def _query_scan(self, conditions: List[QueryCondition]) -> List[str]:
        """Full scan query."""
        results = []

        for doc_id, doc in self._documents.items():
            if self._match_conditions(doc, conditions):
                results.append(doc_id)

        return results

    def _match_conditions(
        self,
        doc: Dict[str, Any],
        conditions: List[QueryCondition]
    ) -> bool:
        """Check if document matches conditions."""
        for cond in conditions:
            value = doc.get(cond.field)

            if cond.operator == QueryOperator.EQ:
                if value != cond.value:
                    return False
            elif cond.operator == QueryOperator.NE:
                if value == cond.value:
                    return False
            elif cond.operator == QueryOperator.LT:
                if value is None or value >= cond.value:
                    return False
            elif cond.operator == QueryOperator.LE:
                if value is None or value > cond.value:
                    return False
            elif cond.operator == QueryOperator.GT:
                if value is None or value <= cond.value:
                    return False
            elif cond.operator == QueryOperator.GE:
                if value is None or value < cond.value:
                    return False
            elif cond.operator == QueryOperator.IN:
                if value not in cond.value:
                    return False

        return True

    # -------------------------------------------------------------------------
    # FULL-TEXT SEARCH
    # -------------------------------------------------------------------------

    def search(
        self,
        query: str,
        index_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> QueryResult:
        """Full-text search."""
        start = time.time()

        with self._lock:
            # Find inverted index
            idx_name = index_name
            if not idx_name:
                for name, idx in self._indexes.items():
                    if isinstance(idx, InvertedIndex):
                        idx_name = name
                        break

            if not idx_name:
                return QueryResult()

            index = self._indexes.get(idx_name)
            if not isinstance(index, InvertedIndex):
                return QueryResult()

            doc_ids = index.search(query)

            docs = [
                self._documents[did]
                for did in doc_ids
                if did in self._documents
            ]

            if limit:
                docs = docs[:limit]

            duration = (time.time() - start) * 1000

            return QueryResult(
                items=docs,
                count=len(docs),
                scan_count=len(doc_ids),
                index_used=idx_name,
                duration_ms=duration
            )

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_index_stats(self, name: str) -> Optional[IndexStats]:
        """Get statistics for an index."""
        with self._lock:
            index = self._indexes.get(name)
            if index and hasattr(index, 'get_stats'):
                return index.get_stats()
            return None

    def get_all_stats(self) -> Dict[str, IndexStats]:
        """Get statistics for all indexes."""
        with self._lock:
            stats = {}
            for name, index in self._indexes.items():
                if hasattr(index, 'get_stats'):
                    stats[name] = index.get_stats()
            return stats

    def document_count(self) -> int:
        """Get total document count."""
        with self._lock:
            return len(self._documents)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Index Manager."""
    print("=" * 70)
    print("BAEL - INDEX MANAGER DEMO")
    print("Advanced Indexing for AI Agents")
    print("=" * 70)
    print()

    manager = IndexManager()

    # 1. Create Hash Index
    print("1. CREATE HASH INDEX:")
    print("-" * 40)

    hash_idx = manager.create_index(IndexConfig(
        name="email_idx",
        index_type=IndexType.HASH,
        fields=["email"],
        unique=True
    ))

    print(f"   Created: {hash_idx.name} ({hash_idx.index_type.value})")
    print()

    # 2. Create B-Tree Index
    print("2. CREATE B-TREE INDEX:")
    print("-" * 40)

    btree_idx = manager.create_index(IndexConfig(
        name="age_idx",
        index_type=IndexType.BTREE,
        fields=["age"]
    ))

    print(f"   Created: {btree_idx.name} ({btree_idx.index_type.value})")
    print()

    # 3. Create Inverted Index
    print("3. CREATE INVERTED INDEX:")
    print("-" * 40)

    text_idx = manager.create_index(IndexConfig(
        name="content_idx",
        index_type=IndexType.INVERTED,
        fields=["content", "title"],
        case_sensitive=False
    ))

    print(f"   Created: {text_idx.name} ({text_idx.index_type.value})")
    print()

    # 4. Index Documents
    print("4. INDEX DOCUMENTS:")
    print("-" * 40)

    documents = [
        {"id": "1", "email": "alice@example.com", "age": 30, "title": "Engineer", "content": "Python developer"},
        {"id": "2", "email": "bob@example.com", "age": 25, "title": "Designer", "content": "UI UX designer"},
        {"id": "3", "email": "charlie@example.com", "age": 35, "title": "Manager", "content": "Project manager"},
        {"id": "4", "email": "diana@example.com", "age": 28, "title": "Developer", "content": "JavaScript developer"},
        {"id": "5", "email": "eve@example.com", "age": 32, "title": "Architect", "content": "System architect"},
    ]

    for doc in documents:
        manager.index_document(doc["id"], doc)

    print(f"   Indexed {len(documents)} documents")
    print(f"   Total documents: {manager.document_count()}")
    print()

    # 5. Hash Index Lookup
    print("5. HASH INDEX LOOKUP:")
    print("-" * 40)

    result = manager.query([
        QueryCondition(field="email", operator=QueryOperator.EQ, value="alice@example.com")
    ], index_hint="email_idx")

    print(f"   Found: {len(result.items)} documents")
    print(f"   Index used: {result.index_used}")
    if result.items:
        print(f"   Document: {result.items[0]}")
    print()

    # 6. B-Tree Range Query
    print("6. B-TREE RANGE QUERY:")
    print("-" * 40)

    # Direct range query on B-tree
    ages = btree_idx.range(25, 32)

    print(f"   Documents with age 25-32: {len(ages)}")

    # Using query conditions
    result = manager.query([
        QueryCondition(field="age", operator=QueryOperator.GE, value=25),
        QueryCondition(field="age", operator=QueryOperator.LE, value=32)
    ], index_hint="age_idx")

    print(f"   Query result: {len(result.items)} documents")
    print()

    # 7. Full-Text Search
    print("7. FULL-TEXT SEARCH:")
    print("-" * 40)

    result = manager.search("developer")

    print(f"   Search 'developer': {len(result.items)} results")
    for item in result.items:
        print(f"     - {item.get('title')}: {item.get('content')}")
    print()

    # 8. Prefix Search
    print("8. PREFIX SEARCH:")
    print("-" * 40)

    prefix_results = text_idx.prefix_search("dev")

    print(f"   Prefix 'dev': {len(prefix_results)} documents")
    print()

    # 9. Composite Index
    print("9. COMPOSITE INDEX:")
    print("-" * 40)

    comp_idx = manager.create_index(IndexConfig(
        name="name_age_idx",
        index_type=IndexType.COMPOSITE,
        fields=["title", "age"]
    ))

    # Reindex documents for composite
    for doc in documents:
        comp_idx.insert((doc["title"], doc["age"]), doc["id"])

    results = comp_idx.lookup(("Developer", 28))

    print(f"   Lookup (Developer, 28): {results}")
    print()

    # 10. Index Statistics
    print("10. INDEX STATISTICS:")
    print("-" * 40)

    all_stats = manager.get_all_stats()

    for name, stats in all_stats.items():
        print(f"   {name}:")
        print(f"     Entries: {stats.entry_count}")
        print(f"     Unique keys: {stats.unique_keys}")
        print(f"     Lookups: {stats.lookups}")
    print()

    # 11. List Indexes
    print("11. LIST INDEXES:")
    print("-" * 40)

    indexes = manager.list_indexes()

    for name in indexes:
        idx = manager.get_index(name)
        print(f"   {name}: {idx.index_type.value} ({idx.count()} entries)")
    print()

    # 12. Remove Document
    print("12. REMOVE DOCUMENT:")
    print("-" * 40)

    removed = manager.remove_document("3")

    print(f"   Removed doc '3': {removed}")
    print(f"   Remaining documents: {manager.document_count()}")
    print()

    # 13. Rebuild Index
    print("13. REBUILD INDEX:")
    print("-" * 40)

    rebuilt = manager.rebuild_index("email_idx")

    print(f"   Rebuilt email_idx: {rebuilt}")
    print()

    # 14. Complex Query
    print("14. COMPLEX QUERY:")
    print("-" * 40)

    result = manager.query([
        QueryCondition(field="age", operator=QueryOperator.GT, value=25)
    ], sort_field="age", sort_order=SortOrder.ASC)

    print(f"   Age > 25, sorted by age: {len(result.items)} results")
    for item in result.items:
        print(f"     {item.get('email')}: age {item.get('age')}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Index Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
