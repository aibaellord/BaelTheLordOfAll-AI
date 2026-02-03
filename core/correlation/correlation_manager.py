#!/usr/bin/env python3
"""
BAEL - Correlation Manager
Advanced correlation tracking for AI agent operations.

Features:
- Correlation ID generation
- Request tracing
- Causation tracking
- Parent-child relationships
- Context propagation
- Correlation storage
- TTL management
- Statistics
- Visualization data
- Chain reconstruction
"""

import asyncio
import contextvars
import hashlib
import random
import string
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


# =============================================================================
# CONTEXT VARIABLES
# =============================================================================

_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id', default=None
)
_causation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'causation_id', default=None
)
_parent_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'parent_id', default=None
)


# =============================================================================
# ENUMS
# =============================================================================

class CorrelationType(Enum):
    """Correlation types."""
    REQUEST = "request"
    EVENT = "event"
    COMMAND = "command"
    MESSAGE = "message"
    TASK = "task"
    FLOW = "flow"


class CorrelationState(Enum):
    """Correlation state."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class IdFormat(Enum):
    """ID format."""
    UUID = "uuid"
    UUID_SHORT = "uuid_short"
    ALPHANUMERIC = "alphanumeric"
    TIMESTAMP = "timestamp"
    HIERARCHICAL = "hierarchical"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CorrelationContext:
    """Correlation context."""
    correlation_id: str = ""
    causation_id: Optional[str] = None
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    correlation_type: CorrelationType = CorrelationType.REQUEST
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationEntry:
    """Correlation entry."""
    correlation_id: str = ""
    correlation_type: CorrelationType = CorrelationType.REQUEST
    state: CorrelationState = CorrelationState.ACTIVE
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    causation_chain: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    ttl_seconds: int = 3600
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)


@dataclass
class CorrelationChain:
    """Chain of correlations."""
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    root_id: str = ""
    entries: List[CorrelationEntry] = field(default_factory=list)
    depth: int = 0
    width: int = 0
    total_duration_ms: float = 0.0


@dataclass
class CorrelationStats:
    """Correlation statistics."""
    total_active: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_expired: int = 0
    avg_chain_depth: float = 0.0
    avg_chain_width: float = 0.0
    by_type: Dict[str, int] = field(default_factory=dict)


@dataclass
class PropagationHeaders:
    """Headers for context propagation."""
    correlation_id: str = ""
    causation_id: Optional[str] = None
    parent_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


# =============================================================================
# ID GENERATORS
# =============================================================================

class IdGenerator(ABC):
    """Base ID generator."""

    @abstractmethod
    def generate(self, prefix: str = "") -> str:
        """Generate an ID."""
        pass


class UUIDGenerator(IdGenerator):
    """UUID generator."""

    def generate(self, prefix: str = "") -> str:
        return f"{prefix}{uuid.uuid4()}" if prefix else str(uuid.uuid4())


class ShortUUIDGenerator(IdGenerator):
    """Short UUID generator."""

    def generate(self, prefix: str = "") -> str:
        short = str(uuid.uuid4())[:8]
        return f"{prefix}{short}" if prefix else short


class AlphanumericGenerator(IdGenerator):
    """Alphanumeric generator."""

    def __init__(self, length: int = 16):
        self.length = length
        self._chars = string.ascii_lowercase + string.digits

    def generate(self, prefix: str = "") -> str:
        random_part = ''.join(random.choices(self._chars, k=self.length))
        return f"{prefix}{random_part}" if prefix else random_part


class TimestampGenerator(IdGenerator):
    """Timestamp-based generator."""

    def generate(self, prefix: str = "") -> str:
        ts = int(time.time() * 1000000)
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
        id_value = f"{ts}-{random_suffix}"
        return f"{prefix}{id_value}" if prefix else id_value


class HierarchicalGenerator(IdGenerator):
    """Hierarchical ID generator."""

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def generate(self, prefix: str = "") -> str:
        with self._lock:
            self._counters[prefix] += 1
            seq = self._counters[prefix]

        if prefix:
            return f"{prefix}.{seq}"
        return f"root.{seq}"

    def generate_child(self, parent_id: str) -> str:
        """Generate child ID."""
        return self.generate(parent_id)


# =============================================================================
# CORRELATION STORE
# =============================================================================

class CorrelationStore:
    """In-memory correlation store."""

    def __init__(self, max_entries: int = 100000):
        self._entries: Dict[str, CorrelationEntry] = {}
        self._by_parent: Dict[str, Set[str]] = defaultdict(set)
        self._by_type: Dict[CorrelationType, Set[str]] = defaultdict(set)
        self._max_entries = max_entries
        self._lock = threading.RLock()

    def add(self, entry: CorrelationEntry) -> None:
        """Add entry."""
        with self._lock:
            # Evict if needed
            if len(self._entries) >= self._max_entries:
                self._evict_expired()

            self._entries[entry.correlation_id] = entry

            if entry.parent_id:
                self._by_parent[entry.parent_id].add(entry.correlation_id)

            self._by_type[entry.correlation_type].add(entry.correlation_id)

    def get(self, correlation_id: str) -> Optional[CorrelationEntry]:
        """Get entry."""
        with self._lock:
            return self._entries.get(correlation_id)

    def update(self, entry: CorrelationEntry) -> None:
        """Update entry."""
        entry.updated_at = datetime.utcnow()

        with self._lock:
            self._entries[entry.correlation_id] = entry

    def remove(self, correlation_id: str) -> bool:
        """Remove entry."""
        with self._lock:
            if correlation_id in self._entries:
                entry = self._entries.pop(correlation_id)

                if entry.parent_id:
                    self._by_parent[entry.parent_id].discard(correlation_id)

                self._by_type[entry.correlation_type].discard(correlation_id)
                return True

        return False

    def get_children(self, parent_id: str) -> List[CorrelationEntry]:
        """Get children of a parent."""
        with self._lock:
            child_ids = self._by_parent.get(parent_id, set())
            return [self._entries[cid] for cid in child_ids if cid in self._entries]

    def get_by_type(
        self,
        correlation_type: CorrelationType
    ) -> List[CorrelationEntry]:
        """Get entries by type."""
        with self._lock:
            entry_ids = self._by_type.get(correlation_type, set())
            return [self._entries[eid] for eid in entry_ids if eid in self._entries]

    def get_active(self) -> List[CorrelationEntry]:
        """Get active entries."""
        with self._lock:
            return [
                e for e in self._entries.values()
                if e.state == CorrelationState.ACTIVE
            ]

    def _evict_expired(self) -> int:
        """Evict expired entries."""
        now = datetime.utcnow()
        expired = []

        for cid, entry in self._entries.items():
            expiry = entry.created_at + timedelta(seconds=entry.ttl_seconds)
            if now > expiry:
                expired.append(cid)

        for cid in expired:
            self.remove(cid)

        return len(expired)

    def count(self) -> int:
        """Get entry count."""
        with self._lock:
            return len(self._entries)


# =============================================================================
# CONTEXT PROPAGATOR
# =============================================================================

class ContextPropagator(ABC):
    """Base context propagator."""

    @abstractmethod
    def inject(self, context: CorrelationContext) -> Dict[str, str]:
        """Inject context into headers."""
        pass

    @abstractmethod
    def extract(self, headers: Dict[str, str]) -> CorrelationContext:
        """Extract context from headers."""
        pass


class StandardPropagator(ContextPropagator):
    """Standard propagator with X-Correlation-ID headers."""

    CORRELATION_HEADER = "X-Correlation-ID"
    CAUSATION_HEADER = "X-Causation-ID"
    PARENT_HEADER = "X-Parent-ID"

    def inject(self, context: CorrelationContext) -> Dict[str, str]:
        headers = {
            self.CORRELATION_HEADER: context.correlation_id
        }

        if context.causation_id:
            headers[self.CAUSATION_HEADER] = context.causation_id

        if context.parent_id:
            headers[self.PARENT_HEADER] = context.parent_id

        return headers

    def extract(self, headers: Dict[str, str]) -> CorrelationContext:
        correlation_id = headers.get(self.CORRELATION_HEADER, "")

        return CorrelationContext(
            correlation_id=correlation_id,
            causation_id=headers.get(self.CAUSATION_HEADER),
            parent_id=headers.get(self.PARENT_HEADER)
        )


class W3CTracePropagator(ContextPropagator):
    """W3C Trace Context propagator."""

    TRACEPARENT_HEADER = "traceparent"
    TRACESTATE_HEADER = "tracestate"

    def inject(self, context: CorrelationContext) -> Dict[str, str]:
        # Generate trace and span IDs
        trace_id = context.metadata.get("trace_id", context.correlation_id.replace("-", "")[:32])
        span_id = context.metadata.get("span_id", context.correlation_id.replace("-", "")[:16])

        traceparent = f"00-{trace_id}-{span_id}-01"

        headers = {
            self.TRACEPARENT_HEADER: traceparent
        }

        return headers

    def extract(self, headers: Dict[str, str]) -> CorrelationContext:
        traceparent = headers.get(self.TRACEPARENT_HEADER, "")

        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 3:
                trace_id = parts[1]
                span_id = parts[2]

                return CorrelationContext(
                    correlation_id=trace_id,
                    metadata={
                        "trace_id": trace_id,
                        "span_id": span_id
                    }
                )

        return CorrelationContext()


# =============================================================================
# CORRELATION MANAGER
# =============================================================================

class CorrelationManager:
    """
    Correlation Manager for BAEL.

    Advanced correlation tracking.
    """

    def __init__(
        self,
        id_format: IdFormat = IdFormat.UUID,
        default_ttl: int = 3600,
        max_entries: int = 100000
    ):
        self._id_format = id_format
        self._default_ttl = default_ttl
        self._generators: Dict[IdFormat, IdGenerator] = {
            IdFormat.UUID: UUIDGenerator(),
            IdFormat.UUID_SHORT: ShortUUIDGenerator(),
            IdFormat.ALPHANUMERIC: AlphanumericGenerator(),
            IdFormat.TIMESTAMP: TimestampGenerator(),
            IdFormat.HIERARCHICAL: HierarchicalGenerator()
        }
        self._store = CorrelationStore(max_entries)
        self._propagators: Dict[str, ContextPropagator] = {
            "standard": StandardPropagator(),
            "w3c": W3CTracePropagator()
        }
        self._default_propagator = "standard"
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # CORRELATION ID GENERATION
    # -------------------------------------------------------------------------

    def generate_id(
        self,
        prefix: str = "",
        format: Optional[IdFormat] = None
    ) -> str:
        """Generate correlation ID."""
        fmt = format or self._id_format
        generator = self._generators.get(fmt, self._generators[IdFormat.UUID])
        return generator.generate(prefix)

    def generate_child_id(
        self,
        parent_id: str,
        format: Optional[IdFormat] = None
    ) -> str:
        """Generate child correlation ID."""
        fmt = format or self._id_format

        if fmt == IdFormat.HIERARCHICAL:
            gen = self._generators[IdFormat.HIERARCHICAL]
            if isinstance(gen, HierarchicalGenerator):
                return gen.generate_child(parent_id)

        # For other formats, generate new ID
        return self.generate_id(format=fmt)

    # -------------------------------------------------------------------------
    # CONTEXT MANAGEMENT
    # -------------------------------------------------------------------------

    def start_correlation(
        self,
        correlation_type: CorrelationType = CorrelationType.REQUEST,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> CorrelationContext:
        """Start new correlation."""
        correlation_id = self.generate_id()

        # Get current context
        current_correlation = _correlation_id.get()
        causation_id = current_correlation if current_correlation else parent_id

        context = CorrelationContext(
            correlation_id=correlation_id,
            causation_id=causation_id,
            parent_id=parent_id,
            root_id=parent_id or correlation_id,
            correlation_type=correlation_type,
            metadata=metadata or {}
        )

        # Create entry
        entry = CorrelationEntry(
            correlation_id=correlation_id,
            correlation_type=correlation_type,
            parent_id=parent_id,
            causation_chain=[causation_id] if causation_id else [],
            ttl_seconds=ttl or self._default_ttl,
            metadata=metadata or {}
        )

        self._store.add(entry)

        # Update parent's children
        if parent_id:
            parent = self._store.get(parent_id)
            if parent:
                parent.children.append(correlation_id)
                self._store.update(parent)

        # Set context variables
        _correlation_id.set(correlation_id)
        _causation_id.set(causation_id)
        _parent_id.set(parent_id)

        return context

    def end_correlation(
        self,
        correlation_id: str,
        success: bool = True
    ) -> None:
        """End correlation."""
        entry = self._store.get(correlation_id)

        if entry:
            entry.state = CorrelationState.COMPLETED if success else CorrelationState.FAILED
            entry.completed_at = datetime.utcnow()
            self._store.update(entry)

    def get_current_context(self) -> CorrelationContext:
        """Get current correlation context."""
        return CorrelationContext(
            correlation_id=_correlation_id.get() or "",
            causation_id=_causation_id.get(),
            parent_id=_parent_id.get()
        )

    def set_context(self, context: CorrelationContext) -> None:
        """Set correlation context."""
        _correlation_id.set(context.correlation_id)
        _causation_id.set(context.causation_id)
        _parent_id.set(context.parent_id)

    def clear_context(self) -> None:
        """Clear correlation context."""
        _correlation_id.set(None)
        _causation_id.set(None)
        _parent_id.set(None)

    # -------------------------------------------------------------------------
    # CONTEXT PROPAGATION
    # -------------------------------------------------------------------------

    def inject_headers(
        self,
        context: Optional[CorrelationContext] = None,
        propagator: Optional[str] = None
    ) -> Dict[str, str]:
        """Inject context into headers."""
        ctx = context or self.get_current_context()
        prop_name = propagator or self._default_propagator
        prop = self._propagators.get(prop_name, self._propagators["standard"])

        return prop.inject(ctx)

    def extract_headers(
        self,
        headers: Dict[str, str],
        propagator: Optional[str] = None
    ) -> CorrelationContext:
        """Extract context from headers."""
        prop_name = propagator or self._default_propagator
        prop = self._propagators.get(prop_name, self._propagators["standard"])

        return prop.extract(headers)

    def continue_from_headers(
        self,
        headers: Dict[str, str],
        correlation_type: CorrelationType = CorrelationType.REQUEST
    ) -> CorrelationContext:
        """Continue correlation from headers."""
        extracted = self.extract_headers(headers)

        if extracted.correlation_id:
            return self.start_correlation(
                correlation_type=correlation_type,
                parent_id=extracted.correlation_id,
                metadata=extracted.metadata
            )

        return self.start_correlation(correlation_type=correlation_type)

    # -------------------------------------------------------------------------
    # CHAIN OPERATIONS
    # -------------------------------------------------------------------------

    def get_chain(self, correlation_id: str) -> CorrelationChain:
        """Get correlation chain from root."""
        root_id = self._find_root(correlation_id)

        chain = CorrelationChain(root_id=root_id)
        visited = set()

        self._build_chain(root_id, chain, visited, 0)

        if chain.entries:
            chain.depth = max(
                len(e.causation_chain) for e in chain.entries
            )
            chain.width = max(
                len(e.children) for e in chain.entries
            ) if chain.entries else 0

            first = min(e.created_at for e in chain.entries)
            last = max(e.updated_at for e in chain.entries)
            chain.total_duration_ms = (last - first).total_seconds() * 1000

        return chain

    def _find_root(self, correlation_id: str) -> str:
        """Find root of correlation chain."""
        visited = set()
        current = correlation_id

        while current and current not in visited:
            visited.add(current)
            entry = self._store.get(current)

            if not entry or not entry.parent_id:
                return current

            current = entry.parent_id

        return correlation_id

    def _build_chain(
        self,
        correlation_id: str,
        chain: CorrelationChain,
        visited: Set[str],
        depth: int
    ) -> None:
        """Build chain recursively."""
        if correlation_id in visited:
            return

        visited.add(correlation_id)
        entry = self._store.get(correlation_id)

        if entry:
            chain.entries.append(entry)

            for child_id in entry.children:
                self._build_chain(child_id, chain, visited, depth + 1)

    def get_causation_chain(self, correlation_id: str) -> List[str]:
        """Get causation chain."""
        entry = self._store.get(correlation_id)

        if entry:
            return list(entry.causation_chain)

        return []

    # -------------------------------------------------------------------------
    # ENTRY OPERATIONS
    # -------------------------------------------------------------------------

    def get_entry(self, correlation_id: str) -> Optional[CorrelationEntry]:
        """Get correlation entry."""
        return self._store.get(correlation_id)

    def add_metadata(
        self,
        correlation_id: str,
        key: str,
        value: Any
    ) -> None:
        """Add metadata to correlation."""
        entry = self._store.get(correlation_id)

        if entry:
            entry.metadata[key] = value
            self._store.update(entry)

    def add_tag(self, correlation_id: str, tag: str) -> None:
        """Add tag to correlation."""
        entry = self._store.get(correlation_id)

        if entry:
            entry.tags.add(tag)
            self._store.update(entry)

    def get_children(self, correlation_id: str) -> List[CorrelationEntry]:
        """Get children of correlation."""
        return self._store.get_children(correlation_id)

    # -------------------------------------------------------------------------
    # QUERY OPERATIONS
    # -------------------------------------------------------------------------

    def find_by_type(
        self,
        correlation_type: CorrelationType
    ) -> List[CorrelationEntry]:
        """Find entries by type."""
        return self._store.get_by_type(correlation_type)

    def find_active(self) -> List[CorrelationEntry]:
        """Find active correlations."""
        return self._store.get_active()

    def find_by_tag(self, tag: str) -> List[CorrelationEntry]:
        """Find entries by tag."""
        active = self._store.get_active()
        return [e for e in active if tag in e.tags]

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> CorrelationStats:
        """Get correlation statistics."""
        entries = list(self._store._entries.values())

        stats = CorrelationStats()

        for entry in entries:
            if entry.state == CorrelationState.ACTIVE:
                stats.total_active += 1
            elif entry.state == CorrelationState.COMPLETED:
                stats.total_completed += 1
            elif entry.state == CorrelationState.FAILED:
                stats.total_failed += 1
            elif entry.state == CorrelationState.EXPIRED:
                stats.total_expired += 1

            type_name = entry.correlation_type.value
            stats.by_type[type_name] = stats.by_type.get(type_name, 0) + 1

        # Calculate averages
        chains = []
        for entry in entries:
            if not entry.parent_id:  # Root entries
                chain = self.get_chain(entry.correlation_id)
                chains.append(chain)

        if chains:
            stats.avg_chain_depth = sum(c.depth for c in chains) / len(chains)
            stats.avg_chain_width = sum(c.width for c in chains) / len(chains)

        return stats

    # -------------------------------------------------------------------------
    # VISUALIZATION
    # -------------------------------------------------------------------------

    def get_tree_structure(
        self,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Get tree structure for visualization."""
        root_id = self._find_root(correlation_id)
        return self._build_tree(root_id)

    def _build_tree(self, correlation_id: str) -> Dict[str, Any]:
        """Build tree recursively."""
        entry = self._store.get(correlation_id)

        if not entry:
            return {}

        node = {
            "id": entry.correlation_id,
            "type": entry.correlation_type.value,
            "state": entry.state.value,
            "created_at": entry.created_at.isoformat(),
            "metadata": entry.metadata,
            "children": []
        }

        for child_id in entry.children:
            child_tree = self._build_tree(child_id)
            if child_tree:
                node["children"].append(child_tree)

        return node

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------

    def cleanup_expired(self) -> int:
        """Clean up expired correlations."""
        return self._store._evict_expired()

    def count(self) -> int:
        """Get total correlation count."""
        return self._store.count()


# =============================================================================
# CONTEXT MANAGER DECORATOR
# =============================================================================

class correlation_scope:
    """Context manager for correlation scope."""

    def __init__(
        self,
        manager: CorrelationManager,
        correlation_type: CorrelationType = CorrelationType.REQUEST,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.manager = manager
        self.correlation_type = correlation_type
        self.parent_id = parent_id
        self.metadata = metadata
        self.context: Optional[CorrelationContext] = None

    def __enter__(self) -> CorrelationContext:
        self.context = self.manager.start_correlation(
            correlation_type=self.correlation_type,
            parent_id=self.parent_id,
            metadata=self.metadata
        )
        return self.context

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.context:
            success = exc_type is None
            self.manager.end_correlation(
                self.context.correlation_id,
                success=success
            )
        return False


class async_correlation_scope:
    """Async context manager for correlation scope."""

    def __init__(
        self,
        manager: CorrelationManager,
        correlation_type: CorrelationType = CorrelationType.REQUEST,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.manager = manager
        self.correlation_type = correlation_type
        self.parent_id = parent_id
        self.metadata = metadata
        self.context: Optional[CorrelationContext] = None

    async def __aenter__(self) -> CorrelationContext:
        self.context = self.manager.start_correlation(
            correlation_type=self.correlation_type,
            parent_id=self.parent_id,
            metadata=self.metadata
        )
        return self.context

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.context:
            success = exc_type is None
            self.manager.end_correlation(
                self.context.correlation_id,
                success=success
            )
        return False


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Correlation Manager."""
    print("=" * 70)
    print("BAEL - CORRELATION MANAGER DEMO")
    print("Advanced Correlation Tracking for AI Agents")
    print("=" * 70)
    print()

    manager = CorrelationManager()

    # 1. Start Correlation
    print("1. START CORRELATION:")
    print("-" * 40)

    ctx = manager.start_correlation(
        correlation_type=CorrelationType.REQUEST,
        metadata={"source": "demo", "user": "test_user"}
    )

    print(f"   Correlation ID: {ctx.correlation_id}")
    print(f"   Type: {ctx.correlation_type.value}")
    print(f"   Metadata: {ctx.metadata}")
    print()

    # 2. Child Correlation
    print("2. CHILD CORRELATION:")
    print("-" * 40)

    child_ctx = manager.start_correlation(
        correlation_type=CorrelationType.TASK,
        parent_id=ctx.correlation_id,
        metadata={"task": "process_data"}
    )

    print(f"   Child ID: {child_ctx.correlation_id}")
    print(f"   Parent ID: {child_ctx.parent_id}")
    print(f"   Causation ID: {child_ctx.causation_id}")
    print()

    # 3. Grandchild
    print("3. GRANDCHILD CORRELATION:")
    print("-" * 40)

    grandchild_ctx = manager.start_correlation(
        correlation_type=CorrelationType.EVENT,
        parent_id=child_ctx.correlation_id
    )

    print(f"   Grandchild ID: {grandchild_ctx.correlation_id}")
    print(f"   Root ID: {grandchild_ctx.root_id}")
    print()

    # End grandchild
    manager.end_correlation(grandchild_ctx.correlation_id, success=True)

    # 4. Get Current Context
    print("4. CURRENT CONTEXT:")
    print("-" * 40)

    current = manager.get_current_context()

    print(f"   Current correlation: {current.correlation_id}")
    print(f"   Current causation: {current.causation_id}")
    print()

    # 5. Context Propagation
    print("5. CONTEXT PROPAGATION:")
    print("-" * 40)

    headers = manager.inject_headers(ctx)

    print(f"   Headers: {headers}")

    extracted = manager.extract_headers(headers)

    print(f"   Extracted ID: {extracted.correlation_id}")
    print()

    # 6. Correlation Chain
    print("6. CORRELATION CHAIN:")
    print("-" * 40)

    chain = manager.get_chain(grandchild_ctx.correlation_id)

    print(f"   Chain ID: {chain.chain_id[:8]}...")
    print(f"   Root ID: {chain.root_id[:8]}...")
    print(f"   Entries: {len(chain.entries)}")
    print(f"   Depth: {chain.depth}")
    print(f"   Width: {chain.width}")
    print()

    # 7. Tree Structure
    print("7. TREE STRUCTURE:")
    print("-" * 40)

    tree = manager.get_tree_structure(ctx.correlation_id)

    def print_tree(node, indent=0):
        prefix = "   " + "  " * indent
        print(f"{prefix}- {node['id'][:8]}... ({node['type']})")
        for child in node.get("children", []):
            print_tree(child, indent + 1)

    print_tree(tree)
    print()

    # 8. Add Metadata and Tags
    print("8. METADATA AND TAGS:")
    print("-" * 40)

    manager.add_metadata(ctx.correlation_id, "processed", True)
    manager.add_tag(ctx.correlation_id, "important")
    manager.add_tag(ctx.correlation_id, "demo")

    entry = manager.get_entry(ctx.correlation_id)

    print(f"   Metadata: {entry.metadata}")
    print(f"   Tags: {entry.tags}")
    print()

    # 9. Find by Tag
    print("9. FIND BY TAG:")
    print("-" * 40)

    by_tag = manager.find_by_tag("important")

    print(f"   Found {len(by_tag)} entries with 'important' tag")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Active: {stats.total_active}")
    print(f"   Completed: {stats.total_completed}")
    print(f"   By type: {stats.by_type}")
    print(f"   Avg chain depth: {stats.avg_chain_depth:.1f}")
    print()

    # 11. Context Scope
    print("11. CONTEXT SCOPE:")
    print("-" * 40)

    with correlation_scope(
        manager,
        CorrelationType.COMMAND,
        metadata={"command": "test"}
    ) as scope_ctx:
        print(f"   In scope: {scope_ctx.correlation_id[:8]}...")

        inner_ctx = manager.get_current_context()
        print(f"   Inner correlation: {inner_ctx.correlation_id[:8]}...")

    print()

    # 12. End Correlations
    print("12. END CORRELATIONS:")
    print("-" * 40)

    manager.end_correlation(child_ctx.correlation_id, success=True)
    manager.end_correlation(ctx.correlation_id, success=True)

    stats = manager.get_stats()

    print(f"   Completed: {stats.total_completed}")
    print(f"   Total entries: {manager.count()}")
    print()

    # 13. Different ID Formats
    print("13. ID FORMATS:")
    print("-" * 40)

    for fmt in IdFormat:
        id_val = manager.generate_id(format=fmt)
        print(f"   {fmt.value}: {id_val}")
    print()

    # 14. W3C Trace Context
    print("14. W3C TRACE CONTEXT:")
    print("-" * 40)

    w3c_headers = manager.inject_headers(ctx, propagator="w3c")

    print(f"   W3C headers: {w3c_headers}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Correlation Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
