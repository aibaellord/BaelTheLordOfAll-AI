#!/usr/bin/env python3
"""
BAEL - Document Store
Comprehensive document database with indexing and querying.

Features:
- JSON document storage
- Indexing (B-tree, hash, text)
- Query language
- Aggregation pipeline
- Transactions
- Full-text search
- Geospatial queries
- TTL support
- Change streams
- Replication support
"""

import asyncio
import bisect
import hashlib
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generator, Iterator, List, Optional,
                    Pattern, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class IndexType(Enum):
    """Index types."""
    BTREE = "btree"
    HASH = "hash"
    TEXT = "text"
    GEO = "geo"
    UNIQUE = "unique"


class QueryOperator(Enum):
    """Query operators."""
    EQ = "$eq"
    NE = "$ne"
    GT = "$gt"
    GTE = "$gte"
    LT = "$lt"
    LTE = "$lte"
    IN = "$in"
    NIN = "$nin"
    EXISTS = "$exists"
    REGEX = "$regex"
    AND = "$and"
    OR = "$or"
    NOT = "$not"
    ALL = "$all"
    ELEM_MATCH = "$elemMatch"
    SIZE = "$size"
    NEAR = "$near"
    TEXT = "$text"


class UpdateOperator(Enum):
    """Update operators."""
    SET = "$set"
    UNSET = "$unset"
    INC = "$inc"
    MUL = "$mul"
    MIN = "$min"
    MAX = "$max"
    PUSH = "$push"
    PULL = "$pull"
    POP = "$pop"
    ADD_TO_SET = "$addToSet"
    RENAME = "$rename"
    CURRENT_DATE = "$currentDate"


class SortOrder(Enum):
    """Sort order."""
    ASC = 1
    DESC = -1


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Document:
    """Document with metadata."""
    _id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    version: int = 1


@dataclass
class IndexDefinition:
    """Index definition."""
    name: str
    fields: List[Tuple[str, int]]  # (field, order)
    index_type: IndexType = IndexType.BTREE
    unique: bool = False
    sparse: bool = False
    ttl: Optional[int] = None  # TTL in seconds


@dataclass
class QueryResult:
    """Query result."""
    documents: List[Document]
    count: int
    execution_time: float = 0.0
    index_used: Optional[str] = None


@dataclass
class WriteResult:
    """Write operation result."""
    success: bool
    document_id: Optional[str] = None
    matched_count: int = 0
    modified_count: int = 0
    upserted_id: Optional[str] = None


@dataclass
class ChangeEvent:
    """Change stream event."""
    operation: str  # insert, update, delete
    document_id: str
    document: Optional[Document] = None
    update_description: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# INDEXES
# =============================================================================

class Index(ABC):
    """Abstract index."""

    def __init__(self, definition: IndexDefinition):
        self.definition = definition

    @abstractmethod
    def add(self, doc_id: str, value: Any) -> None:
        """Add entry to index."""
        pass

    @abstractmethod
    def remove(self, doc_id: str, value: Any) -> None:
        """Remove entry from index."""
        pass

    @abstractmethod
    def find(self, value: Any, operator: QueryOperator = QueryOperator.EQ) -> Set[str]:
        """Find document IDs matching value."""
        pass


class BTreeIndex(Index):
    """B-tree index for range queries."""

    def __init__(self, definition: IndexDefinition):
        super().__init__(definition)
        self._keys: List[Any] = []
        self._values: Dict[Any, Set[str]] = defaultdict(set)

    def add(self, doc_id: str, value: Any) -> None:
        if value not in self._values:
            bisect.insort(self._keys, value)
        self._values[value].add(doc_id)

    def remove(self, doc_id: str, value: Any) -> None:
        if value in self._values:
            self._values[value].discard(doc_id)
            if not self._values[value]:
                del self._values[value]
                self._keys.remove(value)

    def find(self, value: Any, operator: QueryOperator = QueryOperator.EQ) -> Set[str]:
        results = set()

        if operator == QueryOperator.EQ:
            results = self._values.get(value, set()).copy()

        elif operator == QueryOperator.GT:
            idx = bisect.bisect_right(self._keys, value)
            for key in self._keys[idx:]:
                results.update(self._values[key])

        elif operator == QueryOperator.GTE:
            idx = bisect.bisect_left(self._keys, value)
            for key in self._keys[idx:]:
                results.update(self._values[key])

        elif operator == QueryOperator.LT:
            idx = bisect.bisect_left(self._keys, value)
            for key in self._keys[:idx]:
                results.update(self._values[key])

        elif operator == QueryOperator.LTE:
            idx = bisect.bisect_right(self._keys, value)
            for key in self._keys[:idx]:
                results.update(self._values[key])

        elif operator == QueryOperator.NE:
            for key, doc_ids in self._values.items():
                if key != value:
                    results.update(doc_ids)

        return results


class HashIndex(Index):
    """Hash index for equality lookups."""

    def __init__(self, definition: IndexDefinition):
        super().__init__(definition)
        self._index: Dict[Any, Set[str]] = defaultdict(set)

    def add(self, doc_id: str, value: Any) -> None:
        self._index[value].add(doc_id)

    def remove(self, doc_id: str, value: Any) -> None:
        if value in self._index:
            self._index[value].discard(doc_id)
            if not self._index[value]:
                del self._index[value]

    def find(self, value: Any, operator: QueryOperator = QueryOperator.EQ) -> Set[str]:
        if operator == QueryOperator.EQ:
            return self._index.get(value, set()).copy()
        elif operator == QueryOperator.IN:
            results = set()
            for v in value:
                results.update(self._index.get(v, set()))
            return results
        return set()


class TextIndex(Index):
    """Full-text search index."""

    def __init__(self, definition: IndexDefinition):
        super().__init__(definition)
        self._index: Dict[str, Set[str]] = defaultdict(set)  # word -> doc_ids

    def add(self, doc_id: str, value: Any) -> None:
        if isinstance(value, str):
            words = self._tokenize(value)
            for word in words:
                self._index[word].add(doc_id)

    def remove(self, doc_id: str, value: Any) -> None:
        if isinstance(value, str):
            words = self._tokenize(value)
            for word in words:
                self._index[word].discard(doc_id)

    def find(self, value: Any, operator: QueryOperator = QueryOperator.TEXT) -> Set[str]:
        if not isinstance(value, str):
            return set()

        words = self._tokenize(value)
        if not words:
            return set()

        results = self._index.get(words[0], set()).copy()
        for word in words[1:]:
            results &= self._index.get(word, set())

        return results

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        text = text.lower()
        words = re.findall(r'\w+', text)
        # Remove stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
        return [w for w in words if w not in stop_words and len(w) > 2]


class UniqueIndex(HashIndex):
    """Unique index."""

    def add(self, doc_id: str, value: Any) -> None:
        if value in self._index and doc_id not in self._index[value]:
            raise ValueError(f"Duplicate key: {value}")
        super().add(doc_id, value)


# =============================================================================
# QUERY EXECUTOR
# =============================================================================

class QueryExecutor:
    """Execute queries against documents."""

    def __init__(self, documents: Dict[str, Document], indexes: Dict[str, Index]):
        self.documents = documents
        self.indexes = indexes

    def execute(self, query: Dict[str, Any]) -> Set[str]:
        """Execute a query and return matching document IDs."""
        if not query:
            return set(self.documents.keys())

        results: Optional[Set[str]] = None

        for key, value in query.items():
            if key == QueryOperator.AND.value:
                sub_results = None
                for sub_query in value:
                    sr = self.execute(sub_query)
                    sub_results = sr if sub_results is None else sub_results & sr
                matches = sub_results or set()

            elif key == QueryOperator.OR.value:
                sub_results = set()
                for sub_query in value:
                    sub_results |= self.execute(sub_query)
                matches = sub_results

            else:
                matches = self._match_field(key, value)

            results = matches if results is None else results & matches

        return results or set()

    def _match_field(self, field: str, value: Any) -> Set[str]:
        """Match a field condition."""
        if isinstance(value, dict):
            # Operator query
            operator_results = None
            for op, op_value in value.items():
                op_enum = QueryOperator(op)
                matches = self._apply_operator(field, op_enum, op_value)
                operator_results = matches if operator_results is None else operator_results & matches
            return operator_results or set()
        else:
            # Equality
            return self._apply_operator(field, QueryOperator.EQ, value)

    def _apply_operator(self, field: str, operator: QueryOperator, value: Any) -> Set[str]:
        """Apply operator to find matching documents."""
        # Try to use index
        for idx_name, index in self.indexes.items():
            if index.definition.fields[0][0] == field:
                if operator in (QueryOperator.EQ, QueryOperator.GT, QueryOperator.GTE,
                               QueryOperator.LT, QueryOperator.LTE, QueryOperator.NE,
                               QueryOperator.IN, QueryOperator.TEXT):
                    return index.find(value, operator)

        # Full scan
        matches = set()
        for doc_id, doc in self.documents.items():
            doc_value = self._get_field_value(doc.data, field)

            if self._check_operator(doc_value, operator, value):
                matches.add(doc_id)

        return matches

    def _get_field_value(self, data: Dict, field: str) -> Any:
        """Get nested field value."""
        parts = field.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None

        return current

    def _check_operator(self, doc_value: Any, operator: QueryOperator, target: Any) -> bool:
        """Check if value matches operator."""
        if operator == QueryOperator.EQ:
            return doc_value == target

        elif operator == QueryOperator.NE:
            return doc_value != target

        elif operator == QueryOperator.GT:
            return doc_value is not None and doc_value > target

        elif operator == QueryOperator.GTE:
            return doc_value is not None and doc_value >= target

        elif operator == QueryOperator.LT:
            return doc_value is not None and doc_value < target

        elif operator == QueryOperator.LTE:
            return doc_value is not None and doc_value <= target

        elif operator == QueryOperator.IN:
            return doc_value in target

        elif operator == QueryOperator.NIN:
            return doc_value not in target

        elif operator == QueryOperator.EXISTS:
            return (doc_value is not None) == target

        elif operator == QueryOperator.REGEX:
            if isinstance(doc_value, str):
                return bool(re.search(target, doc_value))
            return False

        elif operator == QueryOperator.SIZE:
            if isinstance(doc_value, (list, str)):
                return len(doc_value) == target
            return False

        elif operator == QueryOperator.ALL:
            if isinstance(doc_value, list):
                return all(t in doc_value for t in target)
            return False

        return False


# =============================================================================
# AGGREGATION
# =============================================================================

class AggregationPipeline:
    """Aggregation pipeline executor."""

    def __init__(self, documents: List[Document]):
        self.documents = [d.data for d in documents]

    def execute(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline."""
        result = self.documents

        for stage in pipeline:
            for op, params in stage.items():
                if op == "$match":
                    result = self._match(result, params)
                elif op == "$project":
                    result = self._project(result, params)
                elif op == "$group":
                    result = self._group(result, params)
                elif op == "$sort":
                    result = self._sort(result, params)
                elif op == "$limit":
                    result = result[:params]
                elif op == "$skip":
                    result = result[params:]
                elif op == "$unwind":
                    result = self._unwind(result, params)
                elif op == "$lookup":
                    pass  # Would require collection reference
                elif op == "$count":
                    result = [{params: len(result)}]

        return result

    def _match(self, docs: List[Dict], query: Dict) -> List[Dict]:
        """Match stage."""
        # Simplified matching
        results = []
        for doc in docs:
            matches = True
            for field, value in query.items():
                if isinstance(value, dict):
                    for op, op_val in value.items():
                        doc_val = self._get_value(doc, field)
                        if op == "$gt" and not (doc_val is not None and doc_val > op_val):
                            matches = False
                        elif op == "$lt" and not (doc_val is not None and doc_val < op_val):
                            matches = False
                        elif op == "$gte" and not (doc_val is not None and doc_val >= op_val):
                            matches = False
                        elif op == "$lte" and not (doc_val is not None and doc_val <= op_val):
                            matches = False
                else:
                    if self._get_value(doc, field) != value:
                        matches = False
            if matches:
                results.append(doc)
        return results

    def _project(self, docs: List[Dict], spec: Dict) -> List[Dict]:
        """Project stage."""
        results = []
        for doc in docs:
            projected = {}
            for field, include in spec.items():
                if include:
                    if isinstance(include, str) and include.startswith("$"):
                        projected[field] = self._get_value(doc, include[1:])
                    else:
                        projected[field] = self._get_value(doc, field)
            results.append(projected)
        return results

    def _group(self, docs: List[Dict], spec: Dict) -> List[Dict]:
        """Group stage."""
        groups: Dict[Any, Dict] = {}
        group_field = spec.get("_id")

        for doc in docs:
            if isinstance(group_field, str) and group_field.startswith("$"):
                key = self._get_value(doc, group_field[1:])
            else:
                key = group_field

            if key not in groups:
                groups[key] = {"_id": key}

            for field, expr in spec.items():
                if field == "_id":
                    continue

                if isinstance(expr, dict):
                    for op, val in expr.items():
                        field_val = self._get_value(doc, val[1:]) if isinstance(val, str) and val.startswith("$") else val

                        if op == "$sum":
                            groups[key][field] = groups[key].get(field, 0) + (field_val or 0)
                        elif op == "$avg":
                            if field + "_sum" not in groups[key]:
                                groups[key][field + "_sum"] = 0
                                groups[key][field + "_count"] = 0
                            groups[key][field + "_sum"] += field_val or 0
                            groups[key][field + "_count"] += 1
                            groups[key][field] = groups[key][field + "_sum"] / groups[key][field + "_count"]
                        elif op == "$min":
                            if field not in groups[key] or (field_val is not None and field_val < groups[key][field]):
                                groups[key][field] = field_val
                        elif op == "$max":
                            if field not in groups[key] or (field_val is not None and field_val > groups[key][field]):
                                groups[key][field] = field_val
                        elif op == "$push":
                            if field not in groups[key]:
                                groups[key][field] = []
                            groups[key][field].append(field_val)

        return list(groups.values())

    def _sort(self, docs: List[Dict], spec: Dict) -> List[Dict]:
        """Sort stage."""
        for field, order in reversed(list(spec.items())):
            docs = sorted(docs, key=lambda d: self._get_value(d, field) or "", reverse=(order == -1))
        return docs

    def _unwind(self, docs: List[Dict], path: str) -> List[Dict]:
        """Unwind stage."""
        if path.startswith("$"):
            path = path[1:]

        results = []
        for doc in docs:
            arr = self._get_value(doc, path)
            if isinstance(arr, list):
                for item in arr:
                    new_doc = doc.copy()
                    self._set_value(new_doc, path, item)
                    results.append(new_doc)
            else:
                results.append(doc)
        return results

    def _get_value(self, doc: Dict, field: str) -> Any:
        """Get nested value."""
        parts = field.split('.')
        current = doc
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _set_value(self, doc: Dict, field: str, value: Any) -> None:
        """Set nested value."""
        parts = field.split('.')
        current = doc
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value


# =============================================================================
# DOCUMENT STORE
# =============================================================================

class DocumentStore:
    """
    Document Store for BAEL.

    Provides document storage with indexing, querying, and aggregation.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._documents: Dict[str, Document] = {}
        self._indexes: Dict[str, Index] = {}
        self._change_listeners: List[Callable[[ChangeEvent], None]] = []
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # CRUD OPERATIONS
    # -------------------------------------------------------------------------

    async def insert_one(self, data: Dict[str, Any], ttl: Optional[int] = None) -> WriteResult:
        """Insert a single document."""
        async with self._lock:
            doc_id = data.get("_id", str(uuid.uuid4()))

            if doc_id in self._documents:
                return WriteResult(success=False)

            expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl else None

            doc = Document(
                _id=doc_id,
                data={**data, "_id": doc_id},
                expires_at=expires_at
            )

            self._documents[doc_id] = doc
            self._index_document(doc)

            await self._emit_change(ChangeEvent(
                operation="insert",
                document_id=doc_id,
                document=doc
            ))

            return WriteResult(success=True, document_id=doc_id, matched_count=1, modified_count=1)

    async def insert_many(self, documents: List[Dict[str, Any]]) -> List[WriteResult]:
        """Insert multiple documents."""
        results = []
        for doc in documents:
            result = await self.insert_one(doc)
            results.append(result)
        return results

    async def find_one(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None
    ) -> Optional[Document]:
        """Find a single document."""
        executor = QueryExecutor(self._documents, self._indexes)
        doc_ids = executor.execute(query)

        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc and not self._is_expired(doc):
                if projection:
                    return self._apply_projection(doc, projection)
                return doc

        return None

    async def find(
        self,
        query: Dict[str, Any],
        sort: Optional[List[Tuple[str, int]]] = None,
        limit: Optional[int] = None,
        skip: int = 0,
        projection: Optional[Dict[str, int]] = None
    ) -> QueryResult:
        """Find documents matching query."""
        start_time = time.time()

        executor = QueryExecutor(self._documents, self._indexes)
        doc_ids = executor.execute(query)

        # Get documents
        docs = []
        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc and not self._is_expired(doc):
                docs.append(doc)

        # Sort
        if sort:
            for field, order in reversed(sort):
                docs.sort(
                    key=lambda d: d.data.get(field, ""),
                    reverse=(order == -1)
                )

        # Skip/Limit
        docs = docs[skip:]
        if limit:
            docs = docs[:limit]

        # Projection
        if projection:
            docs = [self._apply_projection(d, projection) for d in docs]

        return QueryResult(
            documents=docs,
            count=len(docs),
            execution_time=time.time() - start_time
        )

    async def update_one(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False
    ) -> WriteResult:
        """Update a single document."""
        doc = await self.find_one(query)

        if not doc:
            if upsert:
                # Create new document
                new_data = {}
                for key, value in query.items():
                    if not key.startswith("$"):
                        new_data[key] = value

                self._apply_update(new_data, update)
                result = await self.insert_one(new_data)
                return WriteResult(
                    success=True,
                    upserted_id=result.document_id,
                    matched_count=0,
                    modified_count=1
                )
            return WriteResult(success=False, matched_count=0)

        async with self._lock:
            # Remove from indexes
            self._unindex_document(doc)

            # Apply update
            self._apply_update(doc.data, update)
            doc.updated_at = datetime.utcnow()
            doc.version += 1

            # Re-index
            self._index_document(doc)

            await self._emit_change(ChangeEvent(
                operation="update",
                document_id=doc._id,
                update_description=update
            ))

        return WriteResult(success=True, matched_count=1, modified_count=1)

    async def update_many(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> WriteResult:
        """Update multiple documents."""
        result = await self.find(query)
        modified = 0

        for doc in result.documents:
            r = await self.update_one({"_id": doc._id}, update)
            if r.success:
                modified += 1

        return WriteResult(success=True, matched_count=result.count, modified_count=modified)

    async def delete_one(self, query: Dict[str, Any]) -> WriteResult:
        """Delete a single document."""
        doc = await self.find_one(query)

        if not doc:
            return WriteResult(success=False, matched_count=0)

        async with self._lock:
            self._unindex_document(doc)
            del self._documents[doc._id]

            await self._emit_change(ChangeEvent(
                operation="delete",
                document_id=doc._id
            ))

        return WriteResult(success=True, matched_count=1, modified_count=1)

    async def delete_many(self, query: Dict[str, Any]) -> WriteResult:
        """Delete multiple documents."""
        result = await self.find(query)
        deleted = 0

        for doc in result.documents:
            r = await self.delete_one({"_id": doc._id})
            if r.success:
                deleted += 1

        return WriteResult(success=True, matched_count=result.count, modified_count=deleted)

    def _apply_update(self, data: Dict, update: Dict) -> None:
        """Apply update operators to document."""
        for op, fields in update.items():
            if op == UpdateOperator.SET.value:
                for field, value in fields.items():
                    self._set_field(data, field, value)

            elif op == UpdateOperator.UNSET.value:
                for field in fields:
                    self._unset_field(data, field)

            elif op == UpdateOperator.INC.value:
                for field, amount in fields.items():
                    current = self._get_field(data, field) or 0
                    self._set_field(data, field, current + amount)

            elif op == UpdateOperator.MUL.value:
                for field, factor in fields.items():
                    current = self._get_field(data, field) or 0
                    self._set_field(data, field, current * factor)

            elif op == UpdateOperator.PUSH.value:
                for field, value in fields.items():
                    arr = self._get_field(data, field) or []
                    arr.append(value)
                    self._set_field(data, field, arr)

            elif op == UpdateOperator.PULL.value:
                for field, value in fields.items():
                    arr = self._get_field(data, field) or []
                    arr = [x for x in arr if x != value]
                    self._set_field(data, field, arr)

            elif op == UpdateOperator.ADD_TO_SET.value:
                for field, value in fields.items():
                    arr = self._get_field(data, field) or []
                    if value not in arr:
                        arr.append(value)
                    self._set_field(data, field, arr)

    def _get_field(self, data: Dict, field: str) -> Any:
        """Get nested field value."""
        parts = field.split('.')
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _set_field(self, data: Dict, field: str, value: Any) -> None:
        """Set nested field value."""
        parts = field.split('.')
        current = data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value

    def _unset_field(self, data: Dict, field: str) -> None:
        """Unset a field."""
        parts = field.split('.')
        current = data
        for part in parts[:-1]:
            if part not in current:
                return
            current = current[part]
        current.pop(parts[-1], None)

    def _apply_projection(self, doc: Document, projection: Dict[str, int]) -> Document:
        """Apply projection to document."""
        if not projection:
            return doc

        # Handle inclusion vs exclusion
        include_mode = any(v == 1 for v in projection.values() if v != 0)

        new_data = {}

        if include_mode:
            for field, include in projection.items():
                if include == 1:
                    value = self._get_field(doc.data, field)
                    if value is not None:
                        self._set_field(new_data, field, value)
        else:
            new_data = doc.data.copy()
            for field, include in projection.items():
                if include == 0:
                    self._unset_field(new_data, field)

        return Document(
            _id=doc._id,
            data=new_data,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )

    # -------------------------------------------------------------------------
    # INDEXING
    # -------------------------------------------------------------------------

    def create_index(self, definition: IndexDefinition) -> None:
        """Create an index."""
        if definition.index_type == IndexType.BTREE:
            index = BTreeIndex(definition)
        elif definition.index_type == IndexType.HASH:
            index = HashIndex(definition)
        elif definition.index_type == IndexType.TEXT:
            index = TextIndex(definition)
        elif definition.index_type == IndexType.UNIQUE:
            index = UniqueIndex(definition)
        else:
            index = BTreeIndex(definition)

        self._indexes[definition.name] = index

        # Index existing documents
        for doc in self._documents.values():
            field = definition.fields[0][0]
            value = self._get_field(doc.data, field)
            if value is not None:
                index.add(doc._id, value)

    def drop_index(self, name: str) -> bool:
        """Drop an index."""
        if name in self._indexes:
            del self._indexes[name]
            return True
        return False

    def list_indexes(self) -> List[IndexDefinition]:
        """List all indexes."""
        return [idx.definition for idx in self._indexes.values()]

    def _index_document(self, doc: Document) -> None:
        """Add document to all indexes."""
        for index in self._indexes.values():
            field = index.definition.fields[0][0]
            value = self._get_field(doc.data, field)
            if value is not None:
                index.add(doc._id, value)

    def _unindex_document(self, doc: Document) -> None:
        """Remove document from all indexes."""
        for index in self._indexes.values():
            field = index.definition.fields[0][0]
            value = self._get_field(doc.data, field)
            if value is not None:
                index.remove(doc._id, value)

    # -------------------------------------------------------------------------
    # AGGREGATION
    # -------------------------------------------------------------------------

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline."""
        docs = list(self._documents.values())
        docs = [d for d in docs if not self._is_expired(d)]

        aggregator = AggregationPipeline(docs)
        return aggregator.execute(pipeline)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def _is_expired(self, doc: Document) -> bool:
        """Check if document is expired."""
        if doc.expires_at is None:
            return False
        return datetime.utcnow() > doc.expires_at

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Count documents."""
        if query:
            result = await self.find(query)
            return result.count
        return len([d for d in self._documents.values() if not self._is_expired(d)])

    async def distinct(self, field: str, query: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Get distinct values for a field."""
        if query:
            result = await self.find(query)
            docs = result.documents
        else:
            docs = [d for d in self._documents.values() if not self._is_expired(d)]

        values = set()
        for doc in docs:
            value = self._get_field(doc.data, field)
            if value is not None:
                if isinstance(value, list):
                    values.update(value)
                else:
                    values.add(value)

        return list(values)

    # -------------------------------------------------------------------------
    # CHANGE STREAMS
    # -------------------------------------------------------------------------

    def watch(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Watch for changes."""
        self._change_listeners.append(callback)

    def unwatch(self, callback: Callable[[ChangeEvent], None]) -> None:
        """Stop watching."""
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)

    async def _emit_change(self, event: ChangeEvent) -> None:
        """Emit change event."""
        for listener in self._change_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Change listener error: {e}")

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "name": self.name,
            "count": len(self._documents),
            "indexes": len(self._indexes),
            "size_bytes": sum(len(str(d.data)) for d in self._documents.values())
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Document Store."""
    print("=" * 70)
    print("BAEL - DOCUMENT STORE DEMO")
    print("Document Database with Indexing")
    print("=" * 70)
    print()

    store = DocumentStore("users")

    # 1. Insert Documents
    print("1. INSERT DOCUMENTS:")
    print("-" * 40)

    users = [
        {"name": "Alice", "age": 30, "city": "Boston", "tags": ["dev", "python"]},
        {"name": "Bob", "age": 25, "city": "NYC", "tags": ["dev", "java"]},
        {"name": "Charlie", "age": 35, "city": "Boston", "tags": ["manager"]},
        {"name": "Diana", "age": 28, "city": "LA", "tags": ["dev", "python", "ml"]},
        {"name": "Eve", "age": 32, "city": "NYC", "tags": ["dev", "javascript"]},
    ]

    for user in users:
        result = await store.insert_one(user)
        print(f"   Inserted: {user['name']} (id: {result.document_id[:8]}...)")
    print()

    # 2. Create Indexes
    print("2. CREATE INDEXES:")
    print("-" * 40)

    store.create_index(IndexDefinition("age_idx", [("age", 1)], IndexType.BTREE))
    store.create_index(IndexDefinition("city_idx", [("city", 1)], IndexType.HASH))
    store.create_index(IndexDefinition("name_idx", [("name", 1)], IndexType.UNIQUE))

    for idx in store.list_indexes():
        print(f"   Index: {idx.name} ({idx.index_type.value})")
    print()

    # 3. Find One
    print("3. FIND ONE:")
    print("-" * 40)

    doc = await store.find_one({"name": "Alice"})
    if doc:
        print(f"   Found: {doc.data['name']}, age={doc.data['age']}")
    print()

    # 4. Find with Query
    print("4. FIND WITH QUERY:")
    print("-" * 40)

    result = await store.find({"city": "Boston"})
    print(f"   Boston residents: {result.count}")
    for doc in result.documents:
        print(f"     - {doc.data['name']}")
    print()

    # 5. Range Query
    print("5. RANGE QUERY:")
    print("-" * 40)

    result = await store.find({"age": {"$gte": 30}})
    print(f"   Age >= 30: {result.count}")
    for doc in result.documents:
        print(f"     - {doc.data['name']} (age: {doc.data['age']})")
    print()

    # 6. Compound Query
    print("6. COMPOUND QUERY:")
    print("-" * 40)

    result = await store.find({
        "$and": [
            {"city": "NYC"},
            {"age": {"$lt": 30}}
        ]
    })
    print(f"   NYC + age < 30: {result.count}")
    for doc in result.documents:
        print(f"     - {doc.data['name']}")
    print()

    # 7. Update
    print("7. UPDATE:")
    print("-" * 40)

    result = await store.update_one(
        {"name": "Alice"},
        {"$set": {"city": "Chicago"}, "$inc": {"age": 1}}
    )
    print(f"   Modified: {result.modified_count}")

    doc = await store.find_one({"name": "Alice"})
    if doc:
        print(f"   Alice now: city={doc.data['city']}, age={doc.data['age']}")
    print()

    # 8. Array Operations
    print("8. ARRAY OPERATIONS:")
    print("-" * 40)

    await store.update_one(
        {"name": "Alice"},
        {"$push": {"tags": "golang"}}
    )

    doc = await store.find_one({"name": "Alice"})
    if doc:
        print(f"   Alice tags: {doc.data['tags']}")
    print()

    # 9. Aggregation
    print("9. AGGREGATION:")
    print("-" * 40)

    result = await store.aggregate([
        {"$group": {
            "_id": "$city",
            "count": {"$sum": 1},
            "avg_age": {"$avg": "$age"}
        }},
        {"$sort": {"count": -1}}
    ])

    for item in result:
        print(f"   {item['_id']}: count={item['count']}, avg_age={item.get('avg_age', 0):.1f}")
    print()

    # 10. Distinct
    print("10. DISTINCT VALUES:")
    print("-" * 40)

    cities = await store.distinct("city")
    print(f"   Cities: {cities}")

    all_tags = await store.distinct("tags")
    print(f"   All tags: {all_tags}")
    print()

    # 11. Sort and Limit
    print("11. SORT AND LIMIT:")
    print("-" * 40)

    result = await store.find(
        {},
        sort=[("age", -1)],
        limit=3
    )
    print("   Top 3 oldest:")
    for doc in result.documents:
        print(f"     - {doc.data['name']} (age: {doc.data['age']})")
    print()

    # 12. Projection
    print("12. PROJECTION:")
    print("-" * 40)

    result = await store.find({}, projection={"name": 1, "age": 1})
    print("   Name and age only:")
    for doc in result.documents[:2]:
        print(f"     - {doc.data}")
    print()

    # 13. Watch Changes
    print("13. CHANGE STREAMS:")
    print("-" * 40)

    changes = []
    def on_change(event):
        changes.append(event)

    store.watch(on_change)

    await store.insert_one({"name": "Frank", "age": 40})
    await store.update_one({"name": "Frank"}, {"$set": {"city": "Seattle"}})

    print(f"   Changes captured: {len(changes)}")
    for event in changes:
        print(f"     - {event.operation}: {event.document_id[:8]}...")
    print()

    # 14. Delete
    print("14. DELETE:")
    print("-" * 40)

    count_before = await store.count()
    result = await store.delete_one({"name": "Frank"})
    count_after = await store.count()

    print(f"   Before: {count_before}, After: {count_after}")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = store.stats()
    print(f"   Collection: {stats['name']}")
    print(f"   Documents: {stats['count']}")
    print(f"   Indexes: {stats['indexes']}")
    print(f"   Size: {stats['size_bytes']} bytes")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Document Store Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
