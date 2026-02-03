#!/usr/bin/env python3
"""
BAEL - Persistence Engine
Data persistence for agents.

Features:
- Key-value persistence
- Document persistence
- Transaction support
- Write-ahead logging
- Snapshot management
"""

import asyncio
import hashlib
import json
import os
import pickle
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
)


T = TypeVar('T')
K = TypeVar('K')


# =============================================================================
# ENUMS
# =============================================================================

class PersistenceType(Enum):
    """Persistence types."""
    MEMORY = "memory"
    FILE = "file"
    WAL = "wal"


class TransactionState(Enum):
    """Transaction states."""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


class WriteOperation(Enum):
    """Write operation types."""
    PUT = "put"
    DELETE = "delete"
    UPDATE = "update"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PersistenceConfig:
    """Persistence configuration."""
    persistence_type: PersistenceType = PersistenceType.MEMORY
    data_dir: str = "./data"
    wal_enabled: bool = False
    snapshot_interval: int = 100
    max_wal_size: int = 1000


@dataclass
class WriteEntry:
    """Write-ahead log entry."""
    entry_id: str = ""
    operation: WriteOperation = WriteOperation.PUT
    key: str = ""
    value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    transaction_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())[:8]


@dataclass
class TransactionInfo:
    """Transaction information."""
    transaction_id: str = ""
    state: TransactionState = TransactionState.ACTIVE
    entries: List[WriteEntry] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    committed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.transaction_id:
            self.transaction_id = str(uuid.uuid4())[:8]


@dataclass
class SnapshotInfo:
    """Snapshot information."""
    snapshot_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    entry_count: int = 0
    size_bytes: int = 0
    checksum: str = ""
    
    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = str(uuid.uuid4())[:8]


@dataclass
class PersistenceStats:
    """Persistence statistics."""
    reads: int = 0
    writes: int = 0
    deletes: int = 0
    transactions: int = 0
    snapshots: int = 0
    wal_entries: int = 0


# =============================================================================
# WRITE-AHEAD LOG
# =============================================================================

class WriteAheadLog:
    """Write-ahead log for durability."""
    
    def __init__(self, max_size: int = 1000):
        self._entries: List[WriteEntry] = []
        self._max_size = max_size
        self._last_snapshot_entry: int = 0
    
    def append(self, entry: WriteEntry) -> None:
        """Append entry to log."""
        self._entries.append(entry)
        
        if len(self._entries) > self._max_size:
            self._truncate()
    
    def get_entries_since(self, index: int) -> List[WriteEntry]:
        """Get entries since index."""
        if index < 0 or index >= len(self._entries):
            return []
        return self._entries[index:]
    
    def get_all_entries(self) -> List[WriteEntry]:
        """Get all entries."""
        return list(self._entries)
    
    def mark_snapshot(self) -> None:
        """Mark current position for snapshot."""
        self._last_snapshot_entry = len(self._entries)
    
    def _truncate(self) -> None:
        """Truncate old entries."""
        if self._last_snapshot_entry > 0:
            self._entries = self._entries[self._last_snapshot_entry:]
            self._last_snapshot_entry = 0
    
    def clear(self) -> None:
        """Clear the log."""
        self._entries.clear()
        self._last_snapshot_entry = 0
    
    @property
    def size(self) -> int:
        return len(self._entries)


# =============================================================================
# TRANSACTION
# =============================================================================

class Transaction:
    """A database transaction."""
    
    def __init__(self, store: 'PersistentStore'):
        self._info = TransactionInfo()
        self._store = store
        self._original_values: Dict[str, Any] = {}
    
    def put(self, key: str, value: Any) -> None:
        """Put value in transaction."""
        if key not in self._original_values:
            self._original_values[key] = self._store.get(key)
        
        entry = WriteEntry(
            operation=WriteOperation.PUT,
            key=key,
            value=value,
            transaction_id=self._info.transaction_id
        )
        
        self._info.entries.append(entry)
    
    def delete(self, key: str) -> None:
        """Delete key in transaction."""
        if key not in self._original_values:
            self._original_values[key] = self._store.get(key)
        
        entry = WriteEntry(
            operation=WriteOperation.DELETE,
            key=key,
            transaction_id=self._info.transaction_id
        )
        
        self._info.entries.append(entry)
    
    async def commit(self) -> bool:
        """Commit the transaction."""
        for entry in self._info.entries:
            if entry.operation == WriteOperation.PUT:
                self._store._data[entry.key] = entry.value
            elif entry.operation == WriteOperation.DELETE:
                self._store._data.pop(entry.key, None)
            
            if self._store._wal:
                self._store._wal.append(entry)
        
        self._info.state = TransactionState.COMMITTED
        self._info.committed_at = datetime.now()
        
        return True
    
    async def rollback(self) -> bool:
        """Rollback the transaction."""
        self._info.state = TransactionState.ROLLED_BACK
        self._info.entries.clear()
        
        return True
    
    @property
    def transaction_id(self) -> str:
        return self._info.transaction_id
    
    @property
    def info(self) -> TransactionInfo:
        return self._info


# =============================================================================
# PERSISTENT STORE
# =============================================================================

class PersistentStore(Generic[K, T]):
    """A persistent key-value store."""
    
    def __init__(
        self,
        name: str,
        config: Optional[PersistenceConfig] = None
    ):
        self._name = name
        self._config = config or PersistenceConfig()
        
        self._data: Dict[K, T] = {}
        self._wal: Optional[WriteAheadLog] = None
        
        self._stats = PersistenceStats()
        self._write_count = 0
        
        if self._config.wal_enabled:
            self._wal = WriteAheadLog(self._config.max_wal_size)
    
    def put(self, key: K, value: T) -> None:
        """Put value into store."""
        self._data[key] = value
        self._stats.writes += 1
        self._write_count += 1
        
        if self._wal:
            entry = WriteEntry(
                operation=WriteOperation.PUT,
                key=str(key),
                value=value
            )
            self._wal.append(entry)
            self._stats.wal_entries += 1
    
    def get(self, key: K) -> Optional[T]:
        """Get value from store."""
        self._stats.reads += 1
        return self._data.get(key)
    
    def delete(self, key: K) -> bool:
        """Delete from store."""
        if key in self._data:
            del self._data[key]
            self._stats.deletes += 1
            
            if self._wal:
                entry = WriteEntry(
                    operation=WriteOperation.DELETE,
                    key=str(key)
                )
                self._wal.append(entry)
                self._stats.wal_entries += 1
            
            return True
        
        return False
    
    def contains(self, key: K) -> bool:
        """Check if key exists."""
        return key in self._data
    
    def keys(self) -> List[K]:
        """Get all keys."""
        return list(self._data.keys())
    
    def values(self) -> List[T]:
        """Get all values."""
        return list(self._data.values())
    
    def items(self) -> List[Tuple[K, T]]:
        """Get all items."""
        return list(self._data.items())
    
    def clear(self) -> None:
        """Clear the store."""
        self._data.clear()
        
        if self._wal:
            self._wal.clear()
    
    def size(self) -> int:
        """Get store size."""
        return len(self._data)
    
    def begin_transaction(self) -> Transaction:
        """Begin a transaction."""
        self._stats.transactions += 1
        return Transaction(self)
    
    def create_snapshot(self) -> SnapshotInfo:
        """Create a snapshot."""
        data_bytes = json.dumps(
            {str(k): v for k, v in self._data.items()},
            default=str
        ).encode()
        
        checksum = hashlib.md5(data_bytes).hexdigest()
        
        info = SnapshotInfo(
            entry_count=len(self._data),
            size_bytes=len(data_bytes),
            checksum=checksum
        )
        
        if self._wal:
            self._wal.mark_snapshot()
        
        self._stats.snapshots += 1
        
        return info
    
    def restore_from_snapshot(self, data: Dict[K, T]) -> None:
        """Restore from snapshot."""
        self._data = dict(data)
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def stats(self) -> PersistenceStats:
        return self._stats


# =============================================================================
# DOCUMENT STORE
# =============================================================================

class DocumentStore:
    """A document-oriented store."""
    
    def __init__(
        self,
        name: str,
        config: Optional[PersistenceConfig] = None
    ):
        self._name = name
        self._config = config or PersistenceConfig()
        
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._indexes: Dict[str, Dict[Any, Set[str]]] = {}
        
        self._stats = PersistenceStats()
    
    def insert(self, doc: Dict[str, Any]) -> str:
        """Insert a document."""
        doc_id = doc.get("_id") or str(uuid.uuid4())[:8]
        doc["_id"] = doc_id
        
        self._documents[doc_id] = doc
        self._update_indexes(doc_id, doc)
        
        self._stats.writes += 1
        
        return doc_id
    
    def find_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Find document by ID."""
        self._stats.reads += 1
        return self._documents.get(doc_id)
    
    def find(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find documents matching query."""
        results = []
        
        for doc in self._documents.values():
            if self._matches(doc, query):
                results.append(doc)
        
        self._stats.reads += len(results)
        
        return results
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find first matching document."""
        for doc in self._documents.values():
            if self._matches(doc, query):
                self._stats.reads += 1
                return doc
        
        return None
    
    def _matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Check if document matches query."""
        for key, value in query.items():
            if key.startswith("$"):
                continue
            
            if key not in doc:
                return False
            
            if isinstance(value, dict):
                if not self._check_operators(doc[key], value):
                    return False
            elif doc[key] != value:
                return False
        
        return True
    
    def _check_operators(self, field_value: Any, operators: Dict[str, Any]) -> bool:
        """Check query operators."""
        for op, value in operators.items():
            if op == "$gt" and not (field_value > value):
                return False
            elif op == "$gte" and not (field_value >= value):
                return False
            elif op == "$lt" and not (field_value < value):
                return False
            elif op == "$lte" and not (field_value <= value):
                return False
            elif op == "$ne" and not (field_value != value):
                return False
            elif op == "$in" and field_value not in value:
                return False
        
        return True
    
    def update(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """Update a document."""
        if doc_id not in self._documents:
            return False
        
        doc = self._documents[doc_id]
        
        for key, value in updates.items():
            if key.startswith("$"):
                if key == "$set":
                    doc.update(value)
                elif key == "$unset":
                    for k in value:
                        doc.pop(k, None)
                elif key == "$inc":
                    for k, v in value.items():
                        doc[k] = doc.get(k, 0) + v
            else:
                doc[key] = value
        
        self._update_indexes(doc_id, doc)
        self._stats.writes += 1
        
        return True
    
    def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id in self._documents:
            doc = self._documents.pop(doc_id)
            self._remove_from_indexes(doc_id, doc)
            self._stats.deletes += 1
            return True
        
        return False
    
    def create_index(self, field: str) -> None:
        """Create an index on a field."""
        self._indexes[field] = defaultdict(set)
        
        for doc_id, doc in self._documents.items():
            if field in doc:
                self._indexes[field][doc[field]].add(doc_id)
    
    def _update_indexes(self, doc_id: str, doc: Dict[str, Any]) -> None:
        """Update indexes for document."""
        for field, index in self._indexes.items():
            for value, doc_ids in index.items():
                doc_ids.discard(doc_id)
            
            if field in doc:
                index[doc[field]].add(doc_id)
    
    def _remove_from_indexes(self, doc_id: str, doc: Dict[str, Any]) -> None:
        """Remove document from indexes."""
        for field, index in self._indexes.items():
            if field in doc:
                index[doc[field]].discard(doc_id)
    
    def find_by_index(self, field: str, value: Any) -> List[Dict[str, Any]]:
        """Find documents using index."""
        if field not in self._indexes:
            return self.find({field: value})
        
        doc_ids = self._indexes[field].get(value, set())
        
        results = []
        for doc_id in doc_ids:
            if doc_id in self._documents:
                results.append(self._documents[doc_id])
        
        self._stats.reads += len(results)
        
        return results
    
    def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Count documents."""
        if query:
            return len(self.find(query))
        return len(self._documents)
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def stats(self) -> PersistenceStats:
        return self._stats


# =============================================================================
# PERSISTENCE ENGINE
# =============================================================================

class PersistenceEngine:
    """
    Persistence Engine for BAEL.
    
    Data persistence for agents.
    """
    
    def __init__(self, default_config: Optional[PersistenceConfig] = None):
        self._default_config = default_config or PersistenceConfig()
        
        self._stores: Dict[str, PersistentStore] = {}
        self._doc_stores: Dict[str, DocumentStore] = {}
    
    # ----- Store Management -----
    
    def create_store(
        self,
        name: str,
        config: Optional[PersistenceConfig] = None
    ) -> PersistentStore:
        """Create a persistent store."""
        config = config or self._default_config
        store = PersistentStore(name, config)
        self._stores[name] = store
        return store
    
    def get_store(self, name: str) -> Optional[PersistentStore]:
        """Get a store."""
        return self._stores.get(name)
    
    def remove_store(self, name: str) -> bool:
        """Remove a store."""
        if name in self._stores:
            del self._stores[name]
            return True
        return False
    
    def list_stores(self) -> List[str]:
        """List store names."""
        return list(self._stores.keys())
    
    # ----- Document Store Management -----
    
    def create_document_store(
        self,
        name: str,
        config: Optional[PersistenceConfig] = None
    ) -> DocumentStore:
        """Create a document store."""
        config = config or self._default_config
        store = DocumentStore(name, config)
        self._doc_stores[name] = store
        return store
    
    def get_document_store(self, name: str) -> Optional[DocumentStore]:
        """Get a document store."""
        return self._doc_stores.get(name)
    
    def remove_document_store(self, name: str) -> bool:
        """Remove a document store."""
        if name in self._doc_stores:
            del self._doc_stores[name]
            return True
        return False
    
    def list_document_stores(self) -> List[str]:
        """List document store names."""
        return list(self._doc_stores.keys())
    
    # ----- Key-Value Operations -----
    
    def put(self, store_name: str, key: Any, value: Any) -> bool:
        """Put value into store."""
        store = self._stores.get(store_name)
        
        if store:
            store.put(key, value)
            return True
        
        return False
    
    def get(self, store_name: str, key: Any) -> Optional[Any]:
        """Get value from store."""
        store = self._stores.get(store_name)
        
        if store:
            return store.get(key)
        
        return None
    
    def delete(self, store_name: str, key: Any) -> bool:
        """Delete from store."""
        store = self._stores.get(store_name)
        
        if store:
            return store.delete(key)
        
        return False
    
    # ----- Document Operations -----
    
    def insert_document(
        self,
        store_name: str,
        doc: Dict[str, Any]
    ) -> Optional[str]:
        """Insert document."""
        store = self._doc_stores.get(store_name)
        
        if store:
            return store.insert(doc)
        
        return None
    
    def find_documents(
        self,
        store_name: str,
        query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find documents."""
        store = self._doc_stores.get(store_name)
        
        if store:
            return store.find(query)
        
        return []
    
    def update_document(
        self,
        store_name: str,
        doc_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update document."""
        store = self._doc_stores.get(store_name)
        
        if store:
            return store.update(doc_id, updates)
        
        return False
    
    def delete_document(
        self,
        store_name: str,
        doc_id: str
    ) -> bool:
        """Delete document."""
        store = self._doc_stores.get(store_name)
        
        if store:
            return store.delete(doc_id)
        
        return False
    
    # ----- Transaction Support -----
    
    def begin_transaction(
        self,
        store_name: str
    ) -> Optional[Transaction]:
        """Begin transaction."""
        store = self._stores.get(store_name)
        
        if store:
            return store.begin_transaction()
        
        return None
    
    # ----- Snapshot Support -----
    
    def create_snapshot(
        self,
        store_name: str
    ) -> Optional[SnapshotInfo]:
        """Create snapshot."""
        store = self._stores.get(store_name)
        
        if store:
            return store.create_snapshot()
        
        return None
    
    # ----- Status -----
    
    def get_store_stats(
        self,
        store_name: str
    ) -> Optional[PersistenceStats]:
        """Get store stats."""
        store = self._stores.get(store_name)
        
        if store:
            return store.stats
        
        doc_store = self._doc_stores.get(store_name)
        
        if doc_store:
            return doc_store.stats
        
        return None
    
    # ----- Engine Stats -----
    
    def stats(self) -> Dict[str, Any]:
        """Get engine stats."""
        total_reads = 0
        total_writes = 0
        
        for store in self._stores.values():
            total_reads += store.stats.reads
            total_writes += store.stats.writes
        
        for store in self._doc_stores.values():
            total_reads += store.stats.reads
            total_writes += store.stats.writes
        
        return {
            "kv_stores": len(self._stores),
            "document_stores": len(self._doc_stores),
            "total_reads": total_reads,
            "total_writes": total_writes
        }
    
    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        stores_info = {}
        
        for name, store in self._stores.items():
            stores_info[name] = {
                "type": "key-value",
                "size": store.size(),
                "reads": store.stats.reads,
                "writes": store.stats.writes
            }
        
        for name, store in self._doc_stores.items():
            stores_info[name] = {
                "type": "document",
                "count": store.count(),
                "reads": store.stats.reads,
                "writes": store.stats.writes
            }
        
        return {"stores": stores_info}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Persistence Engine."""
    print("=" * 70)
    print("BAEL - PERSISTENCE ENGINE DEMO")
    print("Data Persistence for Agents")
    print("=" * 70)
    print()
    
    engine = PersistenceEngine()
    
    # 1. Create Key-Value Store
    print("1. CREATE KEY-VALUE STORE:")
    print("-" * 40)
    
    kv_store = engine.create_store("cache", PersistenceConfig(
        wal_enabled=True
    ))
    
    print(f"   Created store: {kv_store.name}")
    print(f"   WAL enabled: {kv_store._config.wal_enabled}")
    print()
    
    # 2. Put/Get Operations
    print("2. PUT/GET OPERATIONS:")
    print("-" * 40)
    
    engine.put("cache", "user:1001", {"name": "Alice", "age": 30})
    engine.put("cache", "user:1002", {"name": "Bob", "age": 25})
    engine.put("cache", "user:1003", {"name": "Charlie", "age": 35})
    
    print(f"   Inserted 3 users")
    
    user = engine.get("cache", "user:1001")
    print(f"   user:1001: {user}")
    print()
    
    # 3. Delete Operation
    print("3. DELETE OPERATION:")
    print("-" * 40)
    
    deleted = engine.delete("cache", "user:1003")
    print(f"   Deleted user:1003: {deleted}")
    print(f"   Store size: {kv_store.size()}")
    print()
    
    # 4. Transaction
    print("4. TRANSACTION:")
    print("-" * 40)
    
    tx = engine.begin_transaction("cache")
    print(f"   Transaction started: {tx.transaction_id}")
    
    tx.put("user:1004", {"name": "David", "age": 28})
    tx.put("user:1005", {"name": "Eve", "age": 32})
    
    await tx.commit()
    print(f"   Transaction committed")
    print(f"   Store size: {kv_store.size()}")
    print()
    
    # 5. Snapshot
    print("5. SNAPSHOT:")
    print("-" * 40)
    
    snapshot = engine.create_snapshot("cache")
    print(f"   Snapshot ID: {snapshot.snapshot_id}")
    print(f"   Entry count: {snapshot.entry_count}")
    print(f"   Size: {snapshot.size_bytes} bytes")
    print(f"   Checksum: {snapshot.checksum[:16]}...")
    print()
    
    # 6. Create Document Store
    print("6. CREATE DOCUMENT STORE:")
    print("-" * 40)
    
    doc_store = engine.create_document_store("products")
    print(f"   Created document store: {doc_store.name}")
    print()
    
    # 7. Insert Documents
    print("7. INSERT DOCUMENTS:")
    print("-" * 40)
    
    doc_id1 = engine.insert_document("products", {
        "name": "Laptop",
        "price": 999.99,
        "category": "electronics"
    })
    
    doc_id2 = engine.insert_document("products", {
        "name": "Mouse",
        "price": 29.99,
        "category": "electronics"
    })
    
    doc_id3 = engine.insert_document("products", {
        "name": "Desk",
        "price": 199.99,
        "category": "furniture"
    })
    
    print(f"   Inserted: {doc_id1}")
    print(f"   Inserted: {doc_id2}")
    print(f"   Inserted: {doc_id3}")
    print()
    
    # 8. Find Documents
    print("8. FIND DOCUMENTS:")
    print("-" * 40)
    
    electronics = engine.find_documents("products", {"category": "electronics"})
    print(f"   Electronics products: {len(electronics)}")
    for doc in electronics:
        print(f"      {doc['name']}: ${doc['price']}")
    print()
    
    # 9. Query Operators
    print("9. QUERY OPERATORS:")
    print("-" * 40)
    
    expensive = engine.find_documents("products", {
        "price": {"$gt": 100}
    })
    
    print(f"   Products over $100: {len(expensive)}")
    for doc in expensive:
        print(f"      {doc['name']}: ${doc['price']}")
    print()
    
    # 10. Update Document
    print("10. UPDATE DOCUMENT:")
    print("-" * 40)
    
    engine.update_document("products", doc_id1, {
        "$set": {"price": 899.99},
        "$inc": {"views": 1}
    })
    
    updated = doc_store.find_by_id(doc_id1)
    print(f"   Updated: {updated}")
    print()
    
    # 11. Create Index
    print("11. CREATE INDEX:")
    print("-" * 40)
    
    doc_store.create_index("category")
    print(f"   Created index on 'category'")
    
    indexed_results = doc_store.find_by_index("category", "electronics")
    print(f"   Indexed query results: {len(indexed_results)}")
    print()
    
    # 12. Store Statistics
    print("12. STORE STATISTICS:")
    print("-" * 40)
    
    kv_stats = engine.get_store_stats("cache")
    print(f"   Cache store:")
    print(f"      Reads: {kv_stats.reads}")
    print(f"      Writes: {kv_stats.writes}")
    print(f"      WAL entries: {kv_stats.wal_entries}")
    
    doc_stats = engine.get_store_stats("products")
    print(f"   Products store:")
    print(f"      Reads: {doc_stats.reads}")
    print(f"      Writes: {doc_stats.writes}")
    print()
    
    # 13. List Stores
    print("13. LIST STORES:")
    print("-" * 40)
    
    print(f"   Key-Value stores: {engine.list_stores()}")
    print(f"   Document stores: {engine.list_document_stores()}")
    print()
    
    # 14. Engine Statistics
    print("14. ENGINE STATISTICS:")
    print("-" * 40)
    
    stats = engine.stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 15. Engine Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)
    
    summary = engine.summary()
    for name, info in summary["stores"].items():
        print(f"   {name}:")
        for key, value in info.items():
            print(f"      {key}: {value}")
    print()
    
    print("=" * 70)
    print("DEMO COMPLETE - Persistence Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
