#!/usr/bin/env python3
"""
BAEL - Document Store
Advanced document storage and retrieval for AI agent operations.

Features:
- Document CRUD operations
- Full-text search
- Indexing
- Versioning
- Collections
- Tagging
- Metadata
- Query language
- Aggregations
- Document relationships
"""

import asyncio
import copy
import hashlib
import json
import re
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Pattern, Set, Tuple, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DocumentState(Enum):
    """Document states."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class IndexType(Enum):
    """Index types."""
    EXACT = "exact"
    FULLTEXT = "fulltext"
    NUMERIC = "numeric"
    DATE = "date"


class QueryOperator(Enum):
    """Query operators."""
    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GTE = "gte"  # Greater than or equal
    LT = "lt"  # Less than
    LTE = "lte"  # Less than or equal
    IN = "in"  # In list
    NIN = "nin"  # Not in list
    CONTAINS = "contains"  # String contains
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    EXISTS = "exists"


class SortOrder(Enum):
    """Sort order."""
    ASC = "asc"
    DESC = "desc"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Document:
    """A document in the store."""
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    collection: str = "default"
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    state: DocumentState = DocumentState.DRAFT
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    def __hash__(self):
        return hash(self.doc_id)


@dataclass
class DocumentVersion:
    """A version of a document."""
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str = ""
    version: int = 1
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class QueryCondition:
    """A query condition."""
    field: str
    operator: QueryOperator
    value: Any


@dataclass
class Query:
    """A document query."""
    conditions: List[QueryCondition] = field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: SortOrder = SortOrder.ASC
    limit: Optional[int] = None
    offset: int = 0
    include_deleted: bool = False


@dataclass
class IndexConfig:
    """Index configuration."""
    name: str
    field: str
    index_type: IndexType = IndexType.EXACT
    unique: bool = False


@dataclass
class QueryResult:
    """Query result."""
    documents: List[Document] = field(default_factory=list)
    total_count: int = 0
    page_size: int = 0
    page: int = 0
    has_more: bool = False


@dataclass
class AggregationResult:
    """Aggregation result."""
    field: str
    count: int = 0
    sum: float = 0.0
    avg: float = 0.0
    min_val: Any = None
    max_val: Any = None
    values: Dict[Any, int] = field(default_factory=dict)


# =============================================================================
# INDEX
# =============================================================================

class Index:
    """
    An index for fast document lookup.
    """

    def __init__(self, config: IndexConfig):
        self.config = config
        self._index: Dict[Any, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def add(self, doc_id: str, value: Any) -> bool:
        """Add value to index."""
        with self._lock:
            if self.config.unique and value in self._index:
                if self._index[value] and doc_id not in self._index[value]:
                    return False

            if self.config.index_type == IndexType.FULLTEXT and isinstance(value, str):
                # Index each word
                words = self._tokenize(value)
                for word in words:
                    self._index[word.lower()].add(doc_id)
            else:
                self._index[value].add(doc_id)

            return True

    def remove(self, doc_id: str, value: Any) -> None:
        """Remove value from index."""
        with self._lock:
            if self.config.index_type == IndexType.FULLTEXT and isinstance(value, str):
                words = self._tokenize(value)
                for word in words:
                    self._index[word.lower()].discard(doc_id)
            else:
                self._index[value].discard(doc_id)

    def search(
        self,
        value: Any,
        operator: QueryOperator = QueryOperator.EQ
    ) -> Set[str]:
        """Search index."""
        with self._lock:
            if operator == QueryOperator.EQ:
                return self._index.get(value, set()).copy()

            elif operator == QueryOperator.CONTAINS:
                if self.config.index_type == IndexType.FULLTEXT:
                    # Search for word
                    word = value.lower() if isinstance(value, str) else value
                    return self._index.get(word, set()).copy()
                else:
                    # Substring search
                    results = set()
                    for key, doc_ids in self._index.items():
                        if isinstance(key, str) and value in key:
                            results.update(doc_ids)
                    return results

            elif operator == QueryOperator.IN:
                results = set()
                for v in value:
                    results.update(self._index.get(v, set()))
                return results

            elif operator in (QueryOperator.GT, QueryOperator.GTE,
                             QueryOperator.LT, QueryOperator.LTE):
                results = set()
                for key, doc_ids in self._index.items():
                    if self._compare(key, value, operator):
                        results.update(doc_ids)
                return results

            return set()

    def _compare(self, a: Any, b: Any, op: QueryOperator) -> bool:
        """Compare values."""
        try:
            if op == QueryOperator.GT:
                return a > b
            elif op == QueryOperator.GTE:
                return a >= b
            elif op == QueryOperator.LT:
                return a < b
            elif op == QueryOperator.LTE:
                return a <= b
        except TypeError:
            return False
        return False

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for full-text indexing."""
        # Simple word tokenization
        words = re.findall(r'\w+', text)
        return [w for w in words if len(w) > 1]

    def clear(self) -> None:
        """Clear index."""
        with self._lock:
            self._index.clear()


# =============================================================================
# COLLECTION
# =============================================================================

class Collection:
    """
    A collection of documents.
    """

    def __init__(self, name: str):
        self.name = name
        self.created_at = datetime.utcnow()

        self._documents: Dict[str, Document] = {}
        self._indexes: Dict[str, Index] = {}
        self._versions: Dict[str, List[DocumentVersion]] = defaultdict(list)
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # DOCUMENT OPERATIONS
    # -------------------------------------------------------------------------

    def insert(self, document: Document) -> bool:
        """Insert a document."""
        with self._lock:
            if document.doc_id in self._documents:
                return False

            document.collection = self.name
            self._documents[document.doc_id] = document

            # Update indexes
            for idx in self._indexes.values():
                value = self._get_field_value(document.data, idx.config.field)
                if value is not None:
                    if not idx.add(document.doc_id, value):
                        # Unique constraint violated
                        del self._documents[document.doc_id]
                        return False

            # Save initial version
            self._save_version(document)

            return True

    def update(
        self,
        doc_id: str,
        updates: Dict[str, Any],
        upsert: bool = False
    ) -> Optional[Document]:
        """Update a document."""
        with self._lock:
            doc = self._documents.get(doc_id)

            if not doc:
                if upsert:
                    new_doc = Document(doc_id=doc_id, data=updates)
                    self.insert(new_doc)
                    return new_doc
                return None

            # Remove old index values
            for idx in self._indexes.values():
                old_value = self._get_field_value(doc.data, idx.config.field)
                if old_value is not None:
                    idx.remove(doc_id, old_value)

            # Apply updates
            for key, value in updates.items():
                self._set_field_value(doc.data, key, value)

            doc.version += 1
            doc.updated_at = datetime.utcnow()

            # Add new index values
            for idx in self._indexes.values():
                new_value = self._get_field_value(doc.data, idx.config.field)
                if new_value is not None:
                    idx.add(doc_id, new_value)

            # Save version
            self._save_version(doc)

            return doc

    def delete(self, doc_id: str, hard: bool = False) -> bool:
        """Delete a document."""
        with self._lock:
            doc = self._documents.get(doc_id)
            if not doc:
                return False

            if hard:
                # Remove from indexes
                for idx in self._indexes.values():
                    value = self._get_field_value(doc.data, idx.config.field)
                    if value is not None:
                        idx.remove(doc_id, value)

                del self._documents[doc_id]
                self._versions.pop(doc_id, None)
            else:
                # Soft delete
                doc.state = DocumentState.DELETED
                doc.updated_at = datetime.utcnow()
                self._save_version(doc)

            return True

    def get(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        with self._lock:
            return self._documents.get(doc_id)

    def find(self, query: Query) -> QueryResult:
        """Find documents matching query."""
        with self._lock:
            # Start with all documents
            candidates = set(self._documents.keys())

            # Apply conditions
            for condition in query.conditions:
                matching = self._evaluate_condition(condition)
                candidates &= matching

            # Filter deleted unless requested
            if not query.include_deleted:
                candidates = {
                    doc_id for doc_id in candidates
                    if self._documents[doc_id].state != DocumentState.DELETED
                }

            # Get documents
            docs = [self._documents[doc_id] for doc_id in candidates]

            # Sort
            if query.sort_by:
                reverse = query.sort_order == SortOrder.DESC
                docs.sort(
                    key=lambda d: self._get_field_value(d.data, query.sort_by) or "",
                    reverse=reverse
                )

            total = len(docs)

            # Paginate
            if query.offset:
                docs = docs[query.offset:]
            if query.limit:
                docs = docs[:query.limit]

            return QueryResult(
                documents=docs,
                total_count=total,
                page_size=query.limit or len(docs),
                page=query.offset // query.limit if query.limit else 0,
                has_more=query.offset + len(docs) < total
            )

    def find_one(self, query: Query) -> Optional[Document]:
        """Find single document matching query."""
        query.limit = 1
        result = self.find(query)
        return result.documents[0] if result.documents else None

    def count(self, query: Optional[Query] = None) -> int:
        """Count documents."""
        if query:
            return self.find(query).total_count

        with self._lock:
            return len([
                d for d in self._documents.values()
                if d.state != DocumentState.DELETED
            ])

    # -------------------------------------------------------------------------
    # VERSIONING
    # -------------------------------------------------------------------------

    def _save_version(self, doc: Document) -> None:
        """Save document version."""
        version = DocumentVersion(
            doc_id=doc.doc_id,
            version=doc.version,
            data=copy.deepcopy(doc.data),
            metadata=copy.deepcopy(doc.metadata)
        )
        self._versions[doc.doc_id].append(version)

    def get_version(self, doc_id: str, version: int) -> Optional[DocumentVersion]:
        """Get specific version."""
        with self._lock:
            versions = self._versions.get(doc_id, [])
            for v in versions:
                if v.version == version:
                    return v
            return None

    def get_versions(self, doc_id: str) -> List[DocumentVersion]:
        """Get all versions of a document."""
        with self._lock:
            return self._versions.get(doc_id, []).copy()

    def restore_version(self, doc_id: str, version: int) -> Optional[Document]:
        """Restore document to specific version."""
        with self._lock:
            ver = self.get_version(doc_id, version)
            if not ver:
                return None

            doc = self._documents.get(doc_id)
            if not doc:
                return None

            return self.update(doc_id, ver.data)

    # -------------------------------------------------------------------------
    # INDEXES
    # -------------------------------------------------------------------------

    def create_index(self, config: IndexConfig) -> bool:
        """Create an index."""
        with self._lock:
            if config.name in self._indexes:
                return False

            idx = Index(config)

            # Index existing documents
            for doc in self._documents.values():
                value = self._get_field_value(doc.data, config.field)
                if value is not None:
                    idx.add(doc.doc_id, value)

            self._indexes[config.name] = idx
            return True

    def drop_index(self, name: str) -> bool:
        """Drop an index."""
        with self._lock:
            if name in self._indexes:
                del self._indexes[name]
                return True
            return False

    def list_indexes(self) -> List[IndexConfig]:
        """List all indexes."""
        with self._lock:
            return [idx.config for idx in self._indexes.values()]

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_field_value(self, data: Dict, field: str) -> Any:
        """Get nested field value using dot notation."""
        parts = field.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _set_field_value(self, data: Dict, field: str, value: Any) -> None:
        """Set nested field value using dot notation."""
        parts = field.split('.')
        current = data

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def _evaluate_condition(self, condition: QueryCondition) -> Set[str]:
        """Evaluate a query condition."""
        # Check if we have an index
        for idx in self._indexes.values():
            if idx.config.field == condition.field:
                return idx.search(condition.value, condition.operator)

        # Fall back to scan
        results = set()

        for doc_id, doc in self._documents.items():
            value = self._get_field_value(doc.data, condition.field)

            if self._matches(value, condition.value, condition.operator):
                results.add(doc_id)

        return results

    def _matches(self, actual: Any, expected: Any, op: QueryOperator) -> bool:
        """Check if value matches condition."""
        if op == QueryOperator.EQ:
            return actual == expected
        elif op == QueryOperator.NE:
            return actual != expected
        elif op == QueryOperator.GT:
            return actual is not None and actual > expected
        elif op == QueryOperator.GTE:
            return actual is not None and actual >= expected
        elif op == QueryOperator.LT:
            return actual is not None and actual < expected
        elif op == QueryOperator.LTE:
            return actual is not None and actual <= expected
        elif op == QueryOperator.IN:
            return actual in expected
        elif op == QueryOperator.NIN:
            return actual not in expected
        elif op == QueryOperator.CONTAINS:
            return isinstance(actual, str) and expected in actual
        elif op == QueryOperator.STARTS_WITH:
            return isinstance(actual, str) and actual.startswith(expected)
        elif op == QueryOperator.ENDS_WITH:
            return isinstance(actual, str) and actual.endswith(expected)
        elif op == QueryOperator.REGEX:
            return isinstance(actual, str) and bool(re.search(expected, actual))
        elif op == QueryOperator.EXISTS:
            return (actual is not None) == expected

        return False


# =============================================================================
# QUERY BUILDER
# =============================================================================

class QueryBuilder:
    """
    Fluent query builder.
    """

    def __init__(self):
        self._query = Query()

    def where(
        self,
        field: str,
        operator: Union[QueryOperator, str],
        value: Any
    ) -> 'QueryBuilder':
        """Add where condition."""
        if isinstance(operator, str):
            operator = QueryOperator(operator)

        self._query.conditions.append(QueryCondition(
            field=field,
            operator=operator,
            value=value
        ))
        return self

    def eq(self, field: str, value: Any) -> 'QueryBuilder':
        """Equal condition."""
        return self.where(field, QueryOperator.EQ, value)

    def ne(self, field: str, value: Any) -> 'QueryBuilder':
        """Not equal condition."""
        return self.where(field, QueryOperator.NE, value)

    def gt(self, field: str, value: Any) -> 'QueryBuilder':
        """Greater than condition."""
        return self.where(field, QueryOperator.GT, value)

    def gte(self, field: str, value: Any) -> 'QueryBuilder':
        """Greater than or equal condition."""
        return self.where(field, QueryOperator.GTE, value)

    def lt(self, field: str, value: Any) -> 'QueryBuilder':
        """Less than condition."""
        return self.where(field, QueryOperator.LT, value)

    def lte(self, field: str, value: Any) -> 'QueryBuilder':
        """Less than or equal condition."""
        return self.where(field, QueryOperator.LTE, value)

    def contains(self, field: str, value: str) -> 'QueryBuilder':
        """String contains condition."""
        return self.where(field, QueryOperator.CONTAINS, value)

    def in_list(self, field: str, values: List[Any]) -> 'QueryBuilder':
        """In list condition."""
        return self.where(field, QueryOperator.IN, values)

    def exists(self, field: str, exists: bool = True) -> 'QueryBuilder':
        """Field exists condition."""
        return self.where(field, QueryOperator.EXISTS, exists)

    def regex(self, field: str, pattern: str) -> 'QueryBuilder':
        """Regex match condition."""
        return self.where(field, QueryOperator.REGEX, pattern)

    def sort(
        self,
        field: str,
        order: SortOrder = SortOrder.ASC
    ) -> 'QueryBuilder':
        """Sort results."""
        self._query.sort_by = field
        self._query.sort_order = order
        return self

    def limit(self, n: int) -> 'QueryBuilder':
        """Limit results."""
        self._query.limit = n
        return self

    def offset(self, n: int) -> 'QueryBuilder':
        """Offset results."""
        self._query.offset = n
        return self

    def include_deleted(self, include: bool = True) -> 'QueryBuilder':
        """Include deleted documents."""
        self._query.include_deleted = include
        return self

    def build(self) -> Query:
        """Build the query."""
        return self._query


# =============================================================================
# DOCUMENT STORE
# =============================================================================

class DocumentStore:
    """
    Document Store for BAEL.

    Advanced document storage.
    """

    def __init__(self):
        self._collections: Dict[str, Collection] = {}
        self._default_collection = "default"
        self._lock = threading.RLock()

        # Create default collection
        self._collections[self._default_collection] = Collection(self._default_collection)

    # -------------------------------------------------------------------------
    # COLLECTION MANAGEMENT
    # -------------------------------------------------------------------------

    def create_collection(self, name: str) -> Collection:
        """Create a collection."""
        with self._lock:
            if name not in self._collections:
                self._collections[name] = Collection(name)
            return self._collections[name]

    def get_collection(self, name: str) -> Optional[Collection]:
        """Get a collection."""
        with self._lock:
            return self._collections.get(name)

    def drop_collection(self, name: str) -> bool:
        """Drop a collection."""
        with self._lock:
            if name in self._collections and name != self._default_collection:
                del self._collections[name]
                return True
            return False

    def list_collections(self) -> List[str]:
        """List all collections."""
        with self._lock:
            return list(self._collections.keys())

    # -------------------------------------------------------------------------
    # DOCUMENT OPERATIONS
    # -------------------------------------------------------------------------

    def insert(
        self,
        data: Dict[str, Any],
        collection: str = "default",
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Insert a document."""
        doc = Document(
            collection=collection,
            data=data,
            tags=tags or set(),
            metadata=metadata or {}
        )

        coll = self.create_collection(collection)
        coll.insert(doc)

        return doc

    def insert_many(
        self,
        documents: List[Dict[str, Any]],
        collection: str = "default"
    ) -> List[Document]:
        """Insert multiple documents."""
        results = []
        for data in documents:
            doc = self.insert(data, collection)
            results.append(doc)
        return results

    def update(
        self,
        doc_id: str,
        updates: Dict[str, Any],
        collection: str = "default"
    ) -> Optional[Document]:
        """Update a document."""
        coll = self.get_collection(collection)
        if not coll:
            return None
        return coll.update(doc_id, updates)

    def delete(
        self,
        doc_id: str,
        collection: str = "default",
        hard: bool = False
    ) -> bool:
        """Delete a document."""
        coll = self.get_collection(collection)
        if not coll:
            return False
        return coll.delete(doc_id, hard)

    def get(
        self,
        doc_id: str,
        collection: str = "default"
    ) -> Optional[Document]:
        """Get a document."""
        coll = self.get_collection(collection)
        if not coll:
            return None
        return coll.get(doc_id)

    # -------------------------------------------------------------------------
    # QUERYING
    # -------------------------------------------------------------------------

    def find(
        self,
        query: Query,
        collection: str = "default"
    ) -> QueryResult:
        """Find documents."""
        coll = self.get_collection(collection)
        if not coll:
            return QueryResult()
        return coll.find(query)

    def find_one(
        self,
        query: Query,
        collection: str = "default"
    ) -> Optional[Document]:
        """Find single document."""
        coll = self.get_collection(collection)
        if not coll:
            return None
        return coll.find_one(query)

    def query(self, collection: str = "default") -> 'CollectionQuery':
        """Create a query for collection."""
        return CollectionQuery(self, collection)

    # -------------------------------------------------------------------------
    # FULL-TEXT SEARCH
    # -------------------------------------------------------------------------

    def search(
        self,
        text: str,
        field: str,
        collection: str = "default"
    ) -> List[Document]:
        """Full-text search."""
        coll = self.get_collection(collection)
        if not coll:
            return []

        # Ensure fulltext index exists
        index_name = f"_ft_{field}"
        if index_name not in [i.name for i in coll.list_indexes()]:
            coll.create_index(IndexConfig(
                name=index_name,
                field=field,
                index_type=IndexType.FULLTEXT
            ))

        query = QueryBuilder().contains(field, text).build()
        return coll.find(query).documents

    # -------------------------------------------------------------------------
    # TAGS
    # -------------------------------------------------------------------------

    def add_tag(
        self,
        doc_id: str,
        tag: str,
        collection: str = "default"
    ) -> bool:
        """Add tag to document."""
        doc = self.get(doc_id, collection)
        if not doc:
            return False
        doc.tags.add(tag)
        return True

    def remove_tag(
        self,
        doc_id: str,
        tag: str,
        collection: str = "default"
    ) -> bool:
        """Remove tag from document."""
        doc = self.get(doc_id, collection)
        if not doc:
            return False
        doc.tags.discard(tag)
        return True

    def find_by_tag(
        self,
        tag: str,
        collection: str = "default"
    ) -> List[Document]:
        """Find documents by tag."""
        coll = self.get_collection(collection)
        if not coll:
            return []

        with coll._lock:
            return [
                doc for doc in coll._documents.values()
                if tag in doc.tags and doc.state != DocumentState.DELETED
            ]

    # -------------------------------------------------------------------------
    # AGGREGATIONS
    # -------------------------------------------------------------------------

    def aggregate(
        self,
        field: str,
        collection: str = "default",
        query: Optional[Query] = None
    ) -> AggregationResult:
        """Aggregate on a field."""
        coll = self.get_collection(collection)
        if not coll:
            return AggregationResult(field=field)

        # Get matching documents
        if query:
            docs = coll.find(query).documents
        else:
            docs = [
                d for d in coll._documents.values()
                if d.state != DocumentState.DELETED
            ]

        result = AggregationResult(field=field)
        numeric_values = []
        value_counts: Dict[Any, int] = defaultdict(int)

        for doc in docs:
            value = coll._get_field_value(doc.data, field)
            if value is not None:
                result.count += 1
                value_counts[value] += 1

                if isinstance(value, (int, float)):
                    numeric_values.append(value)

        result.values = dict(value_counts)

        if numeric_values:
            result.sum = sum(numeric_values)
            result.avg = result.sum / len(numeric_values)
            result.min_val = min(numeric_values)
            result.max_val = max(numeric_values)

        return result

    def distinct(
        self,
        field: str,
        collection: str = "default"
    ) -> List[Any]:
        """Get distinct values for field."""
        result = self.aggregate(field, collection)
        return list(result.values.keys())

    # -------------------------------------------------------------------------
    # VERSIONING
    # -------------------------------------------------------------------------

    def get_versions(
        self,
        doc_id: str,
        collection: str = "default"
    ) -> List[DocumentVersion]:
        """Get document versions."""
        coll = self.get_collection(collection)
        if not coll:
            return []
        return coll.get_versions(doc_id)

    def restore_version(
        self,
        doc_id: str,
        version: int,
        collection: str = "default"
    ) -> Optional[Document]:
        """Restore document to version."""
        coll = self.get_collection(collection)
        if not coll:
            return None
        return coll.restore_version(doc_id, version)


# =============================================================================
# COLLECTION QUERY
# =============================================================================

class CollectionQuery:
    """
    Fluent query interface for a collection.
    """

    def __init__(self, store: DocumentStore, collection: str):
        self._store = store
        self._collection = collection
        self._builder = QueryBuilder()

    def where(
        self,
        field: str,
        operator: Union[QueryOperator, str],
        value: Any
    ) -> 'CollectionQuery':
        self._builder.where(field, operator, value)
        return self

    def eq(self, field: str, value: Any) -> 'CollectionQuery':
        self._builder.eq(field, value)
        return self

    def gt(self, field: str, value: Any) -> 'CollectionQuery':
        self._builder.gt(field, value)
        return self

    def lt(self, field: str, value: Any) -> 'CollectionQuery':
        self._builder.lt(field, value)
        return self

    def contains(self, field: str, value: str) -> 'CollectionQuery':
        self._builder.contains(field, value)
        return self

    def sort(
        self,
        field: str,
        order: SortOrder = SortOrder.ASC
    ) -> 'CollectionQuery':
        self._builder.sort(field, order)
        return self

    def limit(self, n: int) -> 'CollectionQuery':
        self._builder.limit(n)
        return self

    def offset(self, n: int) -> 'CollectionQuery':
        self._builder.offset(n)
        return self

    def execute(self) -> QueryResult:
        """Execute query."""
        return self._store.find(self._builder.build(), self._collection)

    def first(self) -> Optional[Document]:
        """Get first result."""
        self._builder.limit(1)
        result = self.execute()
        return result.documents[0] if result.documents else None

    def all(self) -> List[Document]:
        """Get all results."""
        return self.execute().documents

    def count(self) -> int:
        """Get count."""
        return self.execute().total_count


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Document Store."""
    print("=" * 70)
    print("BAEL - DOCUMENT STORE DEMO")
    print("Advanced Document Storage for AI Agents")
    print("=" * 70)
    print()

    store = DocumentStore()

    # 1. Insert Documents
    print("1. INSERT DOCUMENTS:")
    print("-" * 40)

    doc1 = store.insert({
        "name": "John Doe",
        "age": 30,
        "email": "john@example.com",
        "department": "Engineering"
    }, tags={"employee", "engineer"})

    doc2 = store.insert({
        "name": "Jane Smith",
        "age": 25,
        "email": "jane@example.com",
        "department": "Marketing"
    }, tags={"employee", "marketing"})

    doc3 = store.insert({
        "name": "Bob Wilson",
        "age": 35,
        "email": "bob@example.com",
        "department": "Engineering"
    }, tags={"employee", "engineer"})

    print(f"   Inserted: {doc1.doc_id[:8]}... (John)")
    print(f"   Inserted: {doc2.doc_id[:8]}... (Jane)")
    print(f"   Inserted: {doc3.doc_id[:8]}... (Bob)")
    print()

    # 2. Get Document
    print("2. GET DOCUMENT:")
    print("-" * 40)

    retrieved = store.get(doc1.doc_id)
    if retrieved:
        print(f"   Name: {retrieved.data['name']}")
        print(f"   Age: {retrieved.data['age']}")
        print(f"   Tags: {retrieved.tags}")
    print()

    # 3. Update Document
    print("3. UPDATE DOCUMENT:")
    print("-" * 40)

    updated = store.update(doc1.doc_id, {"age": 31, "title": "Senior Engineer"})
    if updated:
        print(f"   Updated age: {updated.data['age']}")
        print(f"   New field: {updated.data.get('title')}")
        print(f"   Version: {updated.version}")
    print()

    # 4. Query with Builder
    print("4. QUERY WITH BUILDER:")
    print("-" * 40)

    query = QueryBuilder().eq("department", "Engineering").build()
    result = store.find(query)

    print(f"   Query: department = 'Engineering'")
    print(f"   Found: {result.total_count} documents")
    for doc in result.documents:
        print(f"   - {doc.data['name']}")
    print()

    # 5. Fluent Query
    print("5. FLUENT QUERY:")
    print("-" * 40)

    results = (store.query()
               .gt("age", 28)
               .sort("age", SortOrder.DESC)
               .all())

    print(f"   Query: age > 28, sorted DESC")
    for doc in results:
        print(f"   - {doc.data['name']} (age: {doc.data['age']})")
    print()

    # 6. Find by Tag
    print("6. FIND BY TAG:")
    print("-" * 40)

    engineers = store.find_by_tag("engineer")
    print(f"   Tag: 'engineer'")
    for doc in engineers:
        print(f"   - {doc.data['name']}")
    print()

    # 7. Collections
    print("7. COLLECTIONS:")
    print("-" * 40)

    store.create_collection("projects")
    store.insert({"title": "Project Alpha", "status": "active"}, collection="projects")
    store.insert({"title": "Project Beta", "status": "completed"}, collection="projects")

    print(f"   Collections: {store.list_collections()}")

    projects = store.query("projects").all()
    for p in projects:
        print(f"   - {p.data['title']}: {p.data['status']}")
    print()

    # 8. Indexes
    print("8. INDEXES:")
    print("-" * 40)

    coll = store.get_collection("default")
    if coll:
        coll.create_index(IndexConfig(
            name="email_idx",
            field="email",
            index_type=IndexType.EXACT,
            unique=True
        ))

        print(f"   Created index: email_idx")
        print(f"   Indexes: {[i.name for i in coll.list_indexes()]}")
    print()

    # 9. Full-text Search
    print("9. FULL-TEXT SEARCH:")
    print("-" * 40)

    # Add some text content
    store.insert({"title": "Python Programming", "content": "Learn Python basics"})
    store.insert({"title": "Advanced Python", "content": "Python for experts"})
    store.insert({"title": "Java Guide", "content": "Java programming tutorial"})

    results = store.search("Python", "content")
    print(f"   Search: 'Python' in content")
    for doc in results:
        print(f"   - {doc.data['title']}")
    print()

    # 10. Aggregations
    print("10. AGGREGATIONS:")
    print("-" * 40)

    agg = store.aggregate("age")
    print(f"   Field: age")
    print(f"   Count: {agg.count}")
    print(f"   Sum: {agg.sum}")
    print(f"   Avg: {agg.avg:.1f}")
    print(f"   Min: {agg.min_val}")
    print(f"   Max: {agg.max_val}")
    print()

    # 11. Distinct Values
    print("11. DISTINCT VALUES:")
    print("-" * 40)

    depts = store.distinct("department")
    print(f"   Departments: {depts}")
    print()

    # 12. Document Versions
    print("12. DOCUMENT VERSIONS:")
    print("-" * 40)

    versions = store.get_versions(doc1.doc_id)
    print(f"   Document: {doc1.doc_id[:8]}...")
    print(f"   Versions: {len(versions)}")
    for v in versions:
        print(f"   - v{v.version}: age={v.data.get('age')}")
    print()

    # 13. Restore Version
    print("13. RESTORE VERSION:")
    print("-" * 40)

    restored = store.restore_version(doc1.doc_id, 1)
    if restored:
        print(f"   Restored to v1")
        print(f"   Current age: {restored.data['age']}")
        print(f"   Current version: {restored.version}")
    print()

    # 14. Delete Document
    print("14. DELETE DOCUMENT:")
    print("-" * 40)

    deleted = store.delete(doc2.doc_id)
    print(f"   Soft deleted: {deleted}")

    doc = store.get(doc2.doc_id)
    if doc:
        print(f"   State: {doc.state.value}")

    # Count excluding deleted
    count = store.query().count()
    print(f"   Visible documents: {count}")
    print()

    # 15. Pagination
    print("15. PAGINATION:")
    print("-" * 40)

    # Insert more docs for pagination
    for i in range(5):
        store.insert({"name": f"User {i}", "seq": i})

    page1 = store.query().sort("seq").limit(3).offset(0).execute()
    page2 = store.query().sort("seq").limit(3).offset(3).execute()

    print(f"   Page 1: {[d.data.get('name', d.data.get('seq')) for d in page1.documents]}")
    print(f"   Page 2: {[d.data.get('name', d.data.get('seq')) for d in page2.documents]}")
    print(f"   Total: {page1.total_count}")
    print()

    # 16. Complex Query
    print("16. COMPLEX QUERY:")
    print("-" * 40)

    results = (store.query()
               .eq("department", "Engineering")
               .gt("age", 25)
               .sort("name")
               .all())

    print(f"   Query: department='Engineering' AND age>25")
    for doc in results:
        print(f"   - {doc.data['name']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Document Store Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
