"""
BAEL Cognitive Pipeline - 5-Layer Memory Architecture Integration

Implements the unified cognitive memory system that connects:

Layer 1: WORKING MEMORY
- Short-term, high-frequency access
- Limited capacity (~7 items)
- Attention-driven prioritization

Layer 2: EPISODIC MEMORY
- Specific experiences and events
- Temporal indexing
- Emotion-tagged retrieval

Layer 3: SEMANTIC MEMORY
- Conceptual knowledge and facts
- Concept relations and hierarchies
- Cross-domain connections

Layer 4: PROCEDURAL MEMORY
- Skills and how-to knowledge
- Action sequences
- Learned procedures

Layer 5: META MEMORY
- Knowledge about own knowledge
- Confidence calibration
- Memory strategy selection

The pipeline manages retrieval, storage, consolidation, and cross-layer integration.
"""

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger("BAEL.CognitivePipeline")


# =============================================================================
# MEMORY LAYER ENUM
# =============================================================================

class MemoryLayer(Enum):
    """The 5 layers of cognitive memory."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    META = "meta"


class MemoryOperation(Enum):
    """Operations on memory."""
    STORE = "store"
    RETRIEVE = "retrieve"
    UPDATE = "update"
    DELETE = "delete"
    CONSOLIDATE = "consolidate"
    TRANSFER = "transfer"


class RetrievalStrategy(Enum):
    """Strategies for memory retrieval."""
    EXACT = "exact"           # Exact match
    SEMANTIC = "semantic"     # Semantic similarity
    TEMPORAL = "temporal"     # Time-based
    EMOTIONAL = "emotional"   # Emotion-based
    CONTEXTUAL = "contextual" # Context-based
    ASSOCIATIVE = "associative"  # Association chains


# =============================================================================
# MEMORY ITEMS
# =============================================================================

@dataclass
class MemoryItem:
    """Base class for all memory items."""
    id: str
    content: Any
    layer: MemoryLayer
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5  # 0-1
    decay_rate: float = 0.1
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def access(self) -> None:
        """Record access to this memory."""
        self.accessed_at = datetime.now()
        self.access_count += 1
        # Boost importance on access
        self.importance = min(1.0, self.importance + 0.1)

    def decay(self, elapsed_hours: float) -> None:
        """Apply memory decay based on time."""
        decay = self.decay_rate * elapsed_hours / 24
        self.importance = max(0.0, self.importance - decay)

    def get_strength(self) -> float:
        """Calculate current memory strength."""
        recency = 1.0 / (1 + (datetime.now() - self.accessed_at).total_seconds() / 3600)
        frequency = min(1.0, self.access_count / 100)
        return (self.importance + recency + frequency) / 3


@dataclass
class WorkingMemoryItem(MemoryItem):
    """Item in working memory - short-term, high priority."""
    attention_weight: float = 1.0
    activation_level: float = 1.0

    def __post_init__(self):
        self.layer = MemoryLayer.WORKING
        self.decay_rate = 0.5  # Fast decay


@dataclass
class EpisodicMemoryItem(MemoryItem):
    """Episodic memory - specific experiences."""
    context: Dict[str, Any] = field(default_factory=dict)
    emotions: Dict[str, float] = field(default_factory=dict)
    participants: List[str] = field(default_factory=list)
    outcome: Optional[str] = None

    def __post_init__(self):
        self.layer = MemoryLayer.EPISODIC
        self.decay_rate = 0.05  # Slow decay


@dataclass
class SemanticMemoryItem(MemoryItem):
    """Semantic memory - conceptual knowledge."""
    concept_type: str = "fact"  # fact, concept, relation, rule
    relations: Dict[str, List[str]] = field(default_factory=dict)  # relation_type -> [related_ids]
    confidence: float = 0.8
    source: Optional[str] = None

    def __post_init__(self):
        self.layer = MemoryLayer.SEMANTIC
        self.decay_rate = 0.01  # Very slow decay


@dataclass
class ProceduralMemoryItem(MemoryItem):
    """Procedural memory - skills and procedures."""
    steps: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    execution_count: int = 0
    average_duration_ms: float = 0

    def __post_init__(self):
        self.layer = MemoryLayer.PROCEDURAL
        self.decay_rate = 0.02

    def record_execution(self, success: bool, duration_ms: float) -> None:
        """Record procedure execution."""
        self.execution_count += 1
        # Update success rate with exponential moving average
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        # Update average duration
        self.average_duration_ms = (1 - alpha) * self.average_duration_ms + alpha * duration_ms


@dataclass
class MetaMemoryItem(MemoryItem):
    """Meta memory - knowledge about own memory."""
    target_memory_id: Optional[str] = None
    confidence_estimate: float = 0.5
    retrieval_success_rate: float = 0.5
    last_error: Optional[str] = None

    def __post_init__(self):
        self.layer = MemoryLayer.META
        self.decay_rate = 0.01


# =============================================================================
# MEMORY STORES
# =============================================================================

class MemoryStore(ABC):
    """Abstract base class for memory layer stores."""

    @abstractmethod
    async def store(self, item: MemoryItem) -> str:
        """Store a memory item."""
        pass

    @abstractmethod
    async def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by ID."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        strategy: RetrievalStrategy = RetrievalStrategy.SEMANTIC,
        limit: int = 10
    ) -> List[MemoryItem]:
        """Search for memory items."""
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """Delete a memory item."""
        pass

    @abstractmethod
    async def decay_all(self) -> int:
        """Apply decay to all items, return count of decayed items."""
        pass


class InMemoryStore(MemoryStore):
    """In-memory implementation of a memory store."""

    def __init__(self, layer: MemoryLayer, capacity: int = 1000):
        self.layer = layer
        self.capacity = capacity
        self._items: Dict[str, MemoryItem] = {}
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> item_ids
        self._content_index: Dict[str, str] = {}  # content_hash -> item_id

    async def store(self, item: MemoryItem) -> str:
        """Store a memory item."""
        # Check capacity
        if len(self._items) >= self.capacity:
            await self._evict_weakest()

        # Store item
        self._items[item.id] = item

        # Update indexes
        for tag in item.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(item.id)

        content_hash = self._hash_content(item.content)
        self._content_index[content_hash] = item.id

        return item.id

    async def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by ID."""
        item = self._items.get(item_id)
        if item:
            item.access()
        return item

    async def search(
        self,
        query: str,
        strategy: RetrievalStrategy = RetrievalStrategy.SEMANTIC,
        limit: int = 10
    ) -> List[MemoryItem]:
        """Search for memory items."""
        results = []
        query_lower = query.lower()

        for item in self._items.values():
            score = 0.0

            if strategy == RetrievalStrategy.EXACT:
                if query_lower == str(item.content).lower():
                    score = 1.0

            elif strategy == RetrievalStrategy.SEMANTIC:
                # Simple keyword matching (would use embeddings in production)
                content_str = str(item.content).lower()
                query_words = query_lower.split()
                matches = sum(1 for w in query_words if w in content_str)
                score = matches / len(query_words) if query_words else 0

            elif strategy == RetrievalStrategy.TEMPORAL:
                # Recent items score higher
                age_hours = (datetime.now() - item.created_at).total_seconds() / 3600
                score = 1.0 / (1 + age_hours)

            elif strategy == RetrievalStrategy.CONTEXTUAL:
                # Match on tags
                query_tags = set(query_lower.split())
                tag_overlap = len(query_tags & set(item.tags))
                score = tag_overlap / len(query_tags) if query_tags else 0

            if score > 0:
                results.append((score, item))

        # Sort by score and limit
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in results[:limit]]

    async def delete(self, item_id: str) -> bool:
        """Delete a memory item."""
        if item_id not in self._items:
            return False

        item = self._items[item_id]

        # Remove from indexes
        for tag in item.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(item_id)

        content_hash = self._hash_content(item.content)
        if content_hash in self._content_index:
            del self._content_index[content_hash]

        del self._items[item_id]
        return True

    async def decay_all(self) -> int:
        """Apply decay to all items."""
        decayed = 0
        items_to_remove = []

        for item_id, item in self._items.items():
            hours_since_access = (datetime.now() - item.accessed_at).total_seconds() / 3600
            item.decay(hours_since_access)
            decayed += 1

            # Mark very weak items for removal
            if item.importance < 0.01:
                items_to_remove.append(item_id)

        # Remove dead memories
        for item_id in items_to_remove:
            await self.delete(item_id)

        return decayed

    async def _evict_weakest(self) -> None:
        """Evict weakest item to make room."""
        if not self._items:
            return

        weakest_id = min(self._items.keys(), key=lambda k: self._items[k].get_strength())
        await self.delete(weakest_id)

    def _hash_content(self, content: Any) -> str:
        """Generate hash of content."""
        return hashlib.md5(str(content).encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            "layer": self.layer.value,
            "count": len(self._items),
            "capacity": self.capacity,
            "utilization": len(self._items) / self.capacity,
            "avg_importance": sum(i.importance for i in self._items.values()) / len(self._items) if self._items else 0,
            "avg_access_count": sum(i.access_count for i in self._items.values()) / len(self._items) if self._items else 0
        }


# =============================================================================
# CONSOLIDATION ENGINE
# =============================================================================

class ConsolidationEngine:
    """
    Manages memory consolidation between layers.

    Consolidation transfers important items from faster-decaying layers
    (working) to slower-decaying layers (episodic, semantic).
    """

    def __init__(self):
        self.consolidation_threshold = 0.7  # Importance threshold for consolidation
        self.consolidation_count = 0

    async def consolidate(
        self,
        source_store: MemoryStore,
        target_store: MemoryStore,
        source_layer: MemoryLayer,
        target_layer: MemoryLayer
    ) -> int:
        """Consolidate memories from source to target layer."""
        consolidated = 0

        # Get all items from source
        items = await source_store.search("", strategy=RetrievalStrategy.TEMPORAL, limit=1000)

        for item in items:
            if item.importance >= self.consolidation_threshold:
                # Create new item for target layer
                new_item = await self._transform_for_layer(item, target_layer)
                await target_store.store(new_item)
                consolidated += 1
                self.consolidation_count += 1

        return consolidated

    async def _transform_for_layer(
        self,
        item: MemoryItem,
        target_layer: MemoryLayer
    ) -> MemoryItem:
        """Transform a memory item for a different layer."""

        if target_layer == MemoryLayer.EPISODIC:
            return EpisodicMemoryItem(
                id=str(uuid4()),
                content=item.content,
                layer=target_layer,
                importance=item.importance,
                tags=item.tags,
                embedding=item.embedding,
                metadata=item.metadata,
                context={"source_layer": item.layer.value}
            )

        elif target_layer == MemoryLayer.SEMANTIC:
            return SemanticMemoryItem(
                id=str(uuid4()),
                content=item.content,
                layer=target_layer,
                importance=item.importance,
                tags=item.tags,
                embedding=item.embedding,
                metadata=item.metadata,
                concept_type="fact",
                confidence=item.importance
            )

        elif target_layer == MemoryLayer.PROCEDURAL:
            return ProceduralMemoryItem(
                id=str(uuid4()),
                content=item.content,
                layer=target_layer,
                importance=item.importance,
                tags=item.tags,
                embedding=item.embedding,
                metadata=item.metadata,
                steps=[str(item.content)]
            )

        else:
            return MemoryItem(
                id=str(uuid4()),
                content=item.content,
                layer=target_layer,
                importance=item.importance,
                tags=item.tags,
                embedding=item.embedding,
                metadata=item.metadata
            )


# =============================================================================
# COGNITIVE PIPELINE
# =============================================================================

@dataclass
class MemoryQuery:
    """Query for memory retrieval."""
    query: str
    layers: List[MemoryLayer] = field(default_factory=lambda: list(MemoryLayer))
    strategy: RetrievalStrategy = RetrievalStrategy.SEMANTIC
    limit: int = 10
    min_importance: float = 0.0
    require_embedding: bool = False
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryResult:
    """Result of memory query."""
    items: List[MemoryItem]
    layers_searched: List[MemoryLayer]
    total_found: int
    retrieval_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CognitivePipeline:
    """
    The unified cognitive memory pipeline.

    Manages the 5-layer memory architecture:
    1. Working Memory - Current focus, limited capacity
    2. Episodic Memory - Experiences and events
    3. Semantic Memory - Facts and concepts
    4. Procedural Memory - Skills and procedures
    5. Meta Memory - Knowledge about knowledge

    Provides:
    - Unified query interface across all layers
    - Automatic consolidation between layers
    - Memory decay and forgetting
    - Context-aware retrieval
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}

        # Initialize stores for each layer
        self._stores: Dict[MemoryLayer, MemoryStore] = {
            MemoryLayer.WORKING: InMemoryStore(MemoryLayer.WORKING, capacity=config.get("working_capacity", 7)),
            MemoryLayer.EPISODIC: InMemoryStore(MemoryLayer.EPISODIC, capacity=config.get("episodic_capacity", 10000)),
            MemoryLayer.SEMANTIC: InMemoryStore(MemoryLayer.SEMANTIC, capacity=config.get("semantic_capacity", 100000)),
            MemoryLayer.PROCEDURAL: InMemoryStore(MemoryLayer.PROCEDURAL, capacity=config.get("procedural_capacity", 1000)),
            MemoryLayer.META: InMemoryStore(MemoryLayer.META, capacity=config.get("meta_capacity", 1000)),
        }

        self._consolidation = ConsolidationEngine()
        self._initialized = False

        # Metrics
        self._metrics = {
            "total_stores": 0,
            "total_retrievals": 0,
            "cache_hits": 0,
            "consolidations": 0
        }

    async def initialize(self) -> None:
        """Initialize the cognitive pipeline."""
        if self._initialized:
            return

        logger.info("Initializing Cognitive Pipeline...")

        # Start background tasks
        asyncio.create_task(self._decay_loop())
        asyncio.create_task(self._consolidation_loop())

        self._initialized = True
        logger.info("Cognitive Pipeline initialized")

    async def store(
        self,
        content: Any,
        layer: MemoryLayer = MemoryLayer.WORKING,
        importance: float = 0.5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Store a memory item in the specified layer."""
        tags = tags or []
        metadata = metadata or {}

        # Create appropriate item type
        if layer == MemoryLayer.WORKING:
            item = WorkingMemoryItem(
                id=str(uuid4()),
                content=content,
                layer=layer,
                importance=importance,
                tags=tags,
                metadata=metadata
            )
        elif layer == MemoryLayer.EPISODIC:
            item = EpisodicMemoryItem(
                id=str(uuid4()),
                content=content,
                layer=layer,
                importance=importance,
                tags=tags,
                metadata=metadata
            )
        elif layer == MemoryLayer.SEMANTIC:
            item = SemanticMemoryItem(
                id=str(uuid4()),
                content=content,
                layer=layer,
                importance=importance,
                tags=tags,
                metadata=metadata
            )
        elif layer == MemoryLayer.PROCEDURAL:
            item = ProceduralMemoryItem(
                id=str(uuid4()),
                content=content,
                layer=layer,
                importance=importance,
                tags=tags,
                metadata=metadata
            )
        else:
            item = MetaMemoryItem(
                id=str(uuid4()),
                content=content,
                layer=layer,
                importance=importance,
                tags=tags,
                metadata=metadata
            )

        # Store in appropriate store
        store = self._stores[layer]
        item_id = await store.store(item)

        self._metrics["total_stores"] += 1

        return item_id

    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve memories matching the query."""
        start_time = datetime.now()
        all_items = []

        # Search each specified layer
        for layer in query.layers:
            store = self._stores.get(layer)
            if store:
                items = await store.search(
                    query.query,
                    strategy=query.strategy,
                    limit=query.limit
                )
                all_items.extend(items)

        # Filter by importance
        if query.min_importance > 0:
            all_items = [i for i in all_items if i.importance >= query.min_importance]

        # Sort by strength and limit
        all_items.sort(key=lambda i: i.get_strength(), reverse=True)
        all_items = all_items[:query.limit]

        self._metrics["total_retrievals"] += 1

        return MemoryResult(
            items=all_items,
            layers_searched=query.layers,
            total_found=len(all_items),
            retrieval_time_ms=(datetime.now() - start_time).total_seconds() * 1000
        )

    async def remember(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """Quick retrieval across all layers (convenience method)."""
        result = await self.retrieve(MemoryQuery(
            query=query,
            layers=list(MemoryLayer),
            strategy=RetrievalStrategy.SEMANTIC,
            limit=limit
        ))
        return result.items

    async def learn(
        self,
        content: Any,
        importance: float = 0.7,
        tags: List[str] = None
    ) -> str:
        """Learn new information (store in working, will consolidate if important)."""
        return await self.store(
            content=content,
            layer=MemoryLayer.WORKING,
            importance=importance,
            tags=tags
        )

    async def learn_procedure(
        self,
        name: str,
        steps: List[str],
        preconditions: List[str] = None,
        postconditions: List[str] = None
    ) -> str:
        """Learn a new procedure."""
        item = ProceduralMemoryItem(
            id=str(uuid4()),
            content=name,
            layer=MemoryLayer.PROCEDURAL,
            importance=0.8,
            tags=["procedure", name.lower().replace(" ", "_")],
            steps=steps,
            preconditions=preconditions or [],
            postconditions=postconditions or []
        )

        store = self._stores[MemoryLayer.PROCEDURAL]
        return await store.store(item)

    async def learn_concept(
        self,
        name: str,
        definition: str,
        relations: Dict[str, List[str]] = None
    ) -> str:
        """Learn a new concept."""
        item = SemanticMemoryItem(
            id=str(uuid4()),
            content={"name": name, "definition": definition},
            layer=MemoryLayer.SEMANTIC,
            importance=0.8,
            tags=["concept", name.lower().replace(" ", "_")],
            concept_type="concept",
            relations=relations or {}
        )

        store = self._stores[MemoryLayer.SEMANTIC]
        return await store.store(item)

    async def record_experience(
        self,
        description: str,
        context: Dict[str, Any] = None,
        emotions: Dict[str, float] = None,
        outcome: str = None
    ) -> str:
        """Record an experience in episodic memory."""
        item = EpisodicMemoryItem(
            id=str(uuid4()),
            content=description,
            layer=MemoryLayer.EPISODIC,
            importance=0.7,
            tags=["experience"],
            context=context or {},
            emotions=emotions or {},
            outcome=outcome
        )

        store = self._stores[MemoryLayer.EPISODIC]
        return await store.store(item)

    async def _decay_loop(self) -> None:
        """Background loop for memory decay."""
        while True:
            await asyncio.sleep(60)  # Run every minute

            try:
                for layer, store in self._stores.items():
                    await store.decay_all()
            except Exception as e:
                logger.error(f"Decay loop error: {e}")

    async def _consolidation_loop(self) -> None:
        """Background loop for memory consolidation."""
        while True:
            await asyncio.sleep(300)  # Run every 5 minutes

            try:
                # Consolidate working -> episodic
                count = await self._consolidation.consolidate(
                    self._stores[MemoryLayer.WORKING],
                    self._stores[MemoryLayer.EPISODIC],
                    MemoryLayer.WORKING,
                    MemoryLayer.EPISODIC
                )

                if count > 0:
                    logger.debug(f"Consolidated {count} items from working to episodic")
                    self._metrics["consolidations"] += count

            except Exception as e:
                logger.error(f"Consolidation loop error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        layer_stats = {}
        for layer, store in self._stores.items():
            if isinstance(store, InMemoryStore):
                layer_stats[layer.value] = store.get_stats()

        return {
            "layers": layer_stats,
            "metrics": self._metrics,
            "consolidation_count": self._consolidation.consolidation_count
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate Cognitive Pipeline capabilities."""
    pipeline = CognitivePipeline()
    await pipeline.initialize()

    # Store various types of memories
    print("Storing memories...")

    # Working memory
    await pipeline.learn("The current task is to analyze user sentiment", importance=0.9)
    await pipeline.learn("User mentioned being frustrated", importance=0.8)

    # Episodic memory
    await pipeline.record_experience(
        "User asked about weather",
        context={"topic": "weather", "location": "NYC"},
        emotions={"curiosity": 0.7},
        outcome="Provided weather forecast"
    )

    # Semantic memory
    await pipeline.learn_concept(
        "Machine Learning",
        "A subset of AI that enables systems to learn from data",
        relations={"is_part_of": ["AI"], "includes": ["Neural Networks", "Decision Trees"]}
    )

    # Procedural memory
    await pipeline.learn_procedure(
        "Sentiment Analysis",
        steps=[
            "1. Tokenize input text",
            "2. Extract features",
            "3. Apply classifier",
            "4. Return sentiment score"
        ],
        preconditions=["text_input_available"],
        postconditions=["sentiment_score_generated"]
    )

    # Retrieve memories
    print("\nRetrieving memories about 'user'...")
    items = await pipeline.remember("user", limit=5)
    for item in items:
        print(f"  [{item.layer.value}] {item.content[:50]}... (importance: {item.importance:.2f})")

    print("\nRetrieving memories about 'learning'...")
    items = await pipeline.remember("learning", limit=5)
    for item in items:
        print(f"  [{item.layer.value}] {str(item.content)[:50]}... (importance: {item.importance:.2f})")

    # Get stats
    print("\nPipeline Statistics:")
    import json
    print(json.dumps(pipeline.get_stats(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(demo())
