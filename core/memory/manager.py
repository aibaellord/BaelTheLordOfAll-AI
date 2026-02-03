"""
BAEL - The Lord of All AI Agents
Memory Manager - 5-Layer Cognitive Memory System

This module implements a sophisticated memory architecture inspired by human cognition:
1. Episodic Memory - Specific experiences and events
2. Semantic Memory - General knowledge and facts
3. Procedural Memory - Learned skills and procedures
4. Working Memory - Active, short-term processing
5. Vector Memory - Semantic search via embeddings
"""

import asyncio
import hashlib
import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("BAEL.Memory")


class MemoryType(Enum):
    """Types of memory in BAEL's cognitive system."""
    EPISODIC = "episodic"       # Specific experiences
    SEMANTIC = "semantic"        # General knowledge
    PROCEDURAL = "procedural"    # Skills and procedures
    WORKING = "working"          # Active processing
    VECTOR = "vector"            # Embedding-based


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    type: MemoryType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    importance: float = 0.5
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    associations: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class MemoryQuery:
    """Query for searching memory."""
    query: str
    memory_types: List[MemoryType] = field(default_factory=lambda: list(MemoryType))
    limit: int = 10
    min_importance: float = 0.0
    tags: Optional[List[str]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    include_expired: bool = False


class WorkingMemory:
    """
    Working Memory - Active, short-term cognitive processing.

    Similar to human working memory, this holds currently active information
    needed for ongoing tasks. Limited capacity, constantly updated.
    """

    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self._items: Dict[str, Any] = {}
        self._order: List[str] = []
        self._attention_weights: Dict[str, float] = {}

    def set(self, key: str, value: Any, attention: float = 1.0):
        """Store item in working memory."""
        if key not in self._items and len(self._items) >= self.capacity:
            # Remove least attended item
            self._evict_least_attended()

        self._items[key] = value
        self._attention_weights[key] = attention

        if key in self._order:
            self._order.remove(key)
        self._order.append(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve item from working memory."""
        if key in self._items:
            # Boost attention on access
            self._attention_weights[key] = min(1.0, self._attention_weights.get(key, 0.5) + 0.1)
            return self._items[key]
        return default

    def update_attention(self, key: str, delta: float):
        """Update attention weight for an item."""
        if key in self._attention_weights:
            self._attention_weights[key] = max(0, min(1.0, self._attention_weights[key] + delta))

    def _evict_least_attended(self):
        """Evict the least attended item."""
        if not self._attention_weights:
            return

        min_key = min(self._attention_weights.keys(), key=lambda k: self._attention_weights[k])
        self.remove(min_key)

    def remove(self, key: str):
        """Remove item from working memory."""
        self._items.pop(key, None)
        self._attention_weights.pop(key, None)
        if key in self._order:
            self._order.remove(key)

    def clear(self):
        """Clear all working memory."""
        self._items.clear()
        self._attention_weights.clear()
        self._order.clear()

    def get_all(self) -> Dict[str, Any]:
        """Get all items in working memory."""
        return dict(self._items)

    def get_focused(self, top_n: int = 3) -> Dict[str, Any]:
        """Get top N most attended items."""
        sorted_keys = sorted(
            self._attention_weights.keys(),
            key=lambda k: self._attention_weights[k],
            reverse=True
        )[:top_n]
        return {k: self._items[k] for k in sorted_keys if k in self._items}


class EpisodicMemory:
    """
    Episodic Memory - Specific experiences and events.

    Stores detailed records of specific interactions, events, and experiences.
    Supports temporal queries and contextual retrieval.
    """

    def __init__(self, storage_path: Path, max_entries: int = 10000):
        self.storage_path = storage_path / "episodic"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self._entries: Dict[str, MemoryEntry] = {}
        self._temporal_index: Dict[str, List[str]] = {}  # date -> entry_ids

    async def initialize(self):
        """Load existing episodic memories."""
        index_file = self.storage_path / "index.json"
        if index_file.exists():
            with open(index_file, 'r') as f:
                index_data = json.load(f)
                self._temporal_index = index_data.get('temporal_index', {})

            # Load recent entries
            for date_key in sorted(self._temporal_index.keys(), reverse=True)[:30]:
                for entry_id in self._temporal_index[date_key]:
                    entry_file = self.storage_path / f"{entry_id}.json"
                    if entry_file.exists():
                        with open(entry_file, 'r') as f:
                            data = json.load(f)
                            self._entries[entry_id] = self._dict_to_entry(data)

        logger.info(f"📚 Loaded {len(self._entries)} episodic memories")

    async def store(self, content: Dict[str, Any], metadata: Optional[Dict] = None) -> str:
        """Store a new episodic memory."""
        entry_id = self._generate_id(content)

        entry = MemoryEntry(
            id=entry_id,
            type=MemoryType.EPISODIC,
            content=content,
            metadata=metadata or {},
            importance=self._calculate_importance(content),
            tags=self._extract_tags(content)
        )

        self._entries[entry_id] = entry

        # Update temporal index
        date_key = entry.created_at.strftime("%Y-%m-%d")
        if date_key not in self._temporal_index:
            self._temporal_index[date_key] = []
        self._temporal_index[date_key].append(entry_id)

        # Persist
        await self._persist_entry(entry)

        # Cleanup if needed
        if len(self._entries) > self.max_entries:
            await self._cleanup_old_entries()

        return entry_id

    async def retrieve(
        self,
        query: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Retrieve episodic memories matching criteria."""
        results = []

        for entry in self._entries.values():
            if time_range:
                if entry.created_at < time_range[0] or entry.created_at > time_range[1]:
                    continue

            if query:
                content_str = json.dumps(entry.content).lower()
                if query.lower() not in content_str:
                    continue

            results.append(entry)
            entry.access_count += 1
            entry.last_accessed = datetime.now()

        # Sort by recency and importance
        results.sort(key=lambda e: (e.importance * 0.5 + (1 / (1 + (datetime.now() - e.last_accessed).days)) * 0.5), reverse=True)

        return results[:limit]

    def _generate_id(self, content: Any) -> str:
        """Generate unique ID for content."""
        content_str = json.dumps(content, sort_keys=True, default=str)
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(f"{content_str}{timestamp}".encode()).hexdigest()[:16]

    def _calculate_importance(self, content: Dict) -> float:
        """Calculate importance score for episodic memory."""
        importance = 0.5

        # Increase for success
        if content.get('result', {}).get('success', False):
            importance += 0.1

        # Increase for complex tasks
        if content.get('task_type') in ['planning', 'architecture', 'security']:
            importance += 0.1

        # Increase for high confidence
        if content.get('result', {}).get('confidence', 0) > 0.8:
            importance += 0.1

        return min(1.0, importance)

    def _extract_tags(self, content: Dict) -> List[str]:
        """Extract tags from content."""
        tags = []
        if 'task_type' in content:
            tags.append(content['task_type'])
        if 'session_id' in content:
            tags.append('session')
        return tags

    async def _persist_entry(self, entry: Optional[MemoryEntry]):
        """Persist entry to disk."""
        if entry is None:
            return
        entry_file = self.storage_path / f"{entry.id}.json"
        with open(entry_file, 'w') as f:
            json.dump(self._entry_to_dict(entry), f, indent=2, default=str)

        # Update index
        index_file = self.storage_path / "index.json"
        with open(index_file, 'w') as f:
            json.dump({'temporal_index': self._temporal_index}, f, indent=2)

    async def _cleanup_old_entries(self):
        """Remove old, low-importance entries."""
        entries_to_remove = []

        for entry_id, entry in self._entries.items():
            age_days = (datetime.now() - entry.created_at).days
            if age_days > 30 and entry.importance < 0.5 and entry.access_count < 3:
                entries_to_remove.append(entry_id)

        for entry_id in entries_to_remove[:100]:  # Remove max 100 at a time
            del self._entries[entry_id]
            entry_file = self.storage_path / f"{entry_id}.json"
            if entry_file.exists():
                entry_file.unlink()

        logger.info(f"🧹 Cleaned up {len(entries_to_remove)} old episodic memories")

    def _entry_to_dict(self, entry: MemoryEntry) -> Dict:
        """Convert entry to dictionary."""
        return {
            'id': entry.id,
            'type': entry.type.value,
            'content': entry.content,
            'metadata': entry.metadata,
            'importance': entry.importance,
            'access_count': entry.access_count,
            'last_accessed': entry.last_accessed.isoformat(),
            'created_at': entry.created_at.isoformat(),
            'tags': entry.tags
        }

    def _dict_to_entry(self, data: Dict) -> MemoryEntry:
        """Convert dictionary to entry."""
        return MemoryEntry(
            id=data['id'],
            type=MemoryType(data['type']),
            content=data['content'],
            metadata=data.get('metadata', {}),
            importance=data.get('importance', 0.5),
            access_count=data.get('access_count', 0),
            last_accessed=datetime.fromisoformat(data['last_accessed']) if 'last_accessed' in data else datetime.now(),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            tags=data.get('tags', [])
        )


class SemanticMemory:
    """
    Semantic Memory - General knowledge and facts.

    Stores factual knowledge, concepts, and their relationships.
    Supports hierarchical organization and inference.
    """

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path / "semantic"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._knowledge: Dict[str, Dict[str, Any]] = {}
        self._concepts: Dict[str, List[str]] = {}  # concept -> related concepts
        self._facts: Dict[str, List[str]] = {}  # category -> facts

    async def initialize(self):
        """Load existing semantic memories."""
        knowledge_file = self.storage_path / "knowledge.json"
        if knowledge_file.exists():
            with open(knowledge_file, 'r') as f:
                data = json.load(f)
                self._knowledge = data.get('knowledge', {})
                self._concepts = data.get('concepts', {})
                self._facts = data.get('facts', {})

        logger.info(f"📖 Loaded {len(self._knowledge)} semantic knowledge entries")

    async def store(self, key: str, value: Any, category: Optional[str] = None) -> str:
        """Store semantic knowledge."""
        entry_id = hashlib.sha256(key.encode()).hexdigest()[:16]

        self._knowledge[key] = {
            'id': entry_id,
            'value': value,
            'category': category,
            'created_at': datetime.now().isoformat(),
            'access_count': 0
        }

        if category:
            if category not in self._facts:
                self._facts[category] = []
            self._facts[category].append(key)

        await self._persist()
        return entry_id

    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve semantic knowledge by key."""
        if key in self._knowledge:
            self._knowledge[key]['access_count'] += 1
            return self._knowledge[key]['value']
        return None

    async def query(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """Query semantic memory."""
        results = []

        search_keys = self._facts.get(category, list(self._knowledge.keys())) if category else self._knowledge.keys()

        for key in search_keys:
            if query.lower() in key.lower():
                results.append({
                    'key': key,
                    **self._knowledge[key]
                })

        return results

    async def add_concept_relation(self, concept: str, related: List[str]):
        """Add concept relationships."""
        if concept not in self._concepts:
            self._concepts[concept] = []
        self._concepts[concept].extend(related)
        self._concepts[concept] = list(set(self._concepts[concept]))
        await self._persist()

    async def get_related_concepts(self, concept: str, depth: int = 2) -> List[str]:
        """Get related concepts up to specified depth."""
        related = set()
        to_explore = [(concept, 0)]
        explored = set()

        while to_explore:
            current, current_depth = to_explore.pop(0)
            if current in explored or current_depth > depth:
                continue
            explored.add(current)

            if current in self._concepts:
                for rel in self._concepts[current]:
                    related.add(rel)
                    to_explore.append((rel, current_depth + 1))

        return list(related)

    async def _persist(self):
        """Persist semantic memory."""
        knowledge_file = self.storage_path / "knowledge.json"
        with open(knowledge_file, 'w') as f:
            json.dump({
                'knowledge': self._knowledge,
                'concepts': self._concepts,
                'facts': self._facts
            }, f, indent=2)


class ProceduralMemory:
    """
    Procedural Memory - Learned skills and procedures.

    Stores patterns of successful actions, learned procedures,
    and skill-based knowledge for automatic execution.
    """

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path / "procedural"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._procedures: Dict[str, Dict[str, Any]] = {}
        self._skills: Dict[str, List[str]] = {}  # skill_category -> procedure_ids
        self._success_patterns: List[Dict] = []

    async def initialize(self):
        """Load existing procedural memories."""
        procedures_file = self.storage_path / "procedures.json"
        if procedures_file.exists():
            with open(procedures_file, 'r') as f:
                data = json.load(f)
                self._procedures = data.get('procedures', {})
                self._skills = data.get('skills', {})
                self._success_patterns = data.get('success_patterns', [])

        logger.info(f"🎯 Loaded {len(self._procedures)} procedural memories")

    async def store(self, pattern: Dict[str, Any]) -> str:
        """Store a learned procedure or pattern."""
        procedure_id = hashlib.sha256(
            json.dumps(pattern, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        self._procedures[procedure_id] = {
            'id': procedure_id,
            'pattern': pattern,
            'created_at': datetime.now().isoformat(),
            'success_count': 1,
            'failure_count': 0
        }

        # Categorize by task type
        task_type = pattern.get('task_type', 'general')
        if task_type not in self._skills:
            self._skills[task_type] = []
        self._skills[task_type].append(procedure_id)

        # Track success pattern
        self._success_patterns.append({
            'procedure_id': procedure_id,
            'task_type': task_type,
            'approach': pattern.get('approach', ''),
            'timestamp': datetime.now().isoformat()
        })

        await self._persist()
        return procedure_id

    async def retrieve_for_task(self, task_type: str, limit: int = 5) -> List[Dict]:
        """Retrieve procedures relevant to a task type."""
        if task_type not in self._skills:
            return []

        procedure_ids = self._skills[task_type]
        procedures = []

        for pid in procedure_ids:
            if pid in self._procedures:
                proc = self._procedures[pid]
                # Calculate effectiveness
                total = proc['success_count'] + proc['failure_count']
                effectiveness = proc['success_count'] / total if total > 0 else 0.5
                procedures.append({
                    **proc,
                    'effectiveness': effectiveness
                })

        # Sort by effectiveness
        procedures.sort(key=lambda p: p['effectiveness'], reverse=True)

        return procedures[:limit]

    async def update_outcome(self, procedure_id: str, success: bool):
        """Update procedure with outcome feedback."""
        if procedure_id in self._procedures:
            if success:
                self._procedures[procedure_id]['success_count'] += 1
            else:
                self._procedures[procedure_id]['failure_count'] += 1
            await self._persist()

    async def get_all(self) -> List[Dict]:
        """Get all procedural memories."""
        return list(self._procedures.values())

    async def _persist(self):
        """Persist procedural memory."""
        procedures_file = self.storage_path / "procedures.json"
        with open(procedures_file, 'w') as f:
            json.dump({
                'procedures': self._procedures,
                'skills': self._skills,
                'success_patterns': self._success_patterns[-1000:]  # Keep last 1000
            }, f, indent=2)


class VectorMemory:
    """
    Vector Memory - Semantic search via embeddings.

    Uses vector embeddings for semantic similarity search,
    enabling retrieval based on meaning rather than keywords.
    """

    def __init__(self, storage_path: Path, config: Dict[str, Any]):
        self.storage_path = storage_path / "vector"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.config = config
        self._client = None
        self._collection = None
        self._embedder = None

    async def initialize(self):
        """Initialize vector store (ChromaDB)."""
        try:
            import chromadb

            persist_directory = str(self.storage_path / "chromadb")

            # Use new PersistentClient API (ChromaDB >= 0.4.0)
            self._client = chromadb.PersistentClient(path=persist_directory)

            self._collection = self._client.get_or_create_collection(
                name="bael_memories",
                metadata={"description": "BAEL's unified vector memory"}
            )

            logger.info(f"🔮 Vector memory initialized with {self._collection.count()} entries")

        except ImportError:
            logger.warning("ChromaDB not installed. Vector memory disabled.")

    async def store(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        memory_type: str = "general"
    ) -> str:
        """Store content in vector memory."""
        if not self._collection:
            return ""

        doc_id = hashlib.sha256(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        self._collection.add(
            documents=[content],
            metadatas=[{
                'memory_type': memory_type,
                'created_at': datetime.now().isoformat(),
                **(metadata or {})
            }],
            ids=[doc_id]
        )

        return doc_id

    async def search(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None
    ) -> List[Dict]:
        """Search vector memory by semantic similarity."""
        if not self._collection:
            return []

        where_filter = {"memory_type": memory_type} if memory_type else None

        results = self._collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_filter
        )

        formatted_results = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0
                })

        return formatted_results

    async def delete(self, doc_id: str):
        """Delete from vector memory."""
        if self._collection:
            self._collection.delete(ids=[doc_id])


class MemoryManager:
    """
    Central Memory Manager - Orchestrates all memory systems.

    Provides unified interface for storing and retrieving memories
    across all five cognitive memory systems.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage_path = Path(config.get('storage_path', 'memory/storage'))
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize memory systems
        self.working = WorkingMemory(
            capacity=config.get('working_memory', {}).get('capacity', 10)
        )
        self.episodic = EpisodicMemory(
            storage_path=self.storage_path,
            max_entries=config.get('episodic', {}).get('max_entries', 10000)
        )
        self.semantic = SemanticMemory(storage_path=self.storage_path)
        self.procedural = ProceduralMemory(storage_path=self.storage_path)
        self.vector = VectorMemory(
            storage_path=self.storage_path,
            config=config.get('vector', {})
        )

        self._initialized = False

    async def initialize(self):
        """Initialize all memory systems."""
        if self._initialized:
            return

        logger.info("🧠 Initializing BAEL Memory Systems...")

        await self.episodic.initialize()
        await self.semantic.initialize()
        await self.procedural.initialize()
        await self.vector.initialize()

        self._initialized = True
        logger.info("✅ All memory systems initialized")

    # =========================================================================
    # WORKING MEMORY INTERFACE
    # =========================================================================

    def set_working(self, key: str, value: Any, attention: float = 1.0):
        """Set working memory item."""
        self.working.set(key, value, attention)

    def get_working(self, key: str, default: Any = None) -> Any:
        """Get working memory item."""
        return self.working.get(key, default)

    def get_focus(self, top_n: int = 3) -> Dict[str, Any]:
        """Get most focused working memory items."""
        return self.working.get_focused(top_n)

    # =========================================================================
    # EPISODIC MEMORY INTERFACE
    # =========================================================================

    async def store_episodic(self, content: Dict[str, Any], metadata: Optional[Dict] = None) -> str:
        """Store episodic memory."""
        entry_id = await self.episodic.store(content, metadata)

        # Also store in vector memory for semantic search
        await self.vector.store(
            content=json.dumps(content),
            metadata={'source': 'episodic', 'entry_id': entry_id},
            memory_type='episodic'
        )

        return entry_id

    async def recall_episodic(
        self,
        query: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Recall episodic memories."""
        return await self.episodic.retrieve(query, time_range, limit)

    # =========================================================================
    # SEMANTIC MEMORY INTERFACE
    # =========================================================================

    async def store_knowledge(self, key: str, value: Any, category: Optional[str] = None) -> str:
        """Store semantic knowledge."""
        entry_id = await self.semantic.store(key, value, category)

        # Also store in vector memory
        await self.vector.store(
            content=f"{key}: {json.dumps(value) if isinstance(value, dict) else value}",
            metadata={'source': 'semantic', 'key': key, 'category': category},
            memory_type='semantic'
        )

        return entry_id

    async def get_knowledge(self, key: str) -> Optional[Any]:
        """Get semantic knowledge."""
        return await self.semantic.retrieve(key)

    async def query_knowledge(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """Query semantic memory."""
        return await self.semantic.query(query, category)

    # =========================================================================
    # PROCEDURAL MEMORY INTERFACE
    # =========================================================================

    async def store_procedural(self, pattern: Dict[str, Any]) -> str:
        """Store procedural memory."""
        return await self.procedural.store(pattern)

    async def get_procedural_memory(self) -> List[Dict]:
        """Get all procedural memories."""
        return await self.procedural.get_all()

    async def get_procedures_for_task(self, task_type: str, limit: int = 5) -> List[Dict]:
        """Get relevant procedures for a task type."""
        return await self.procedural.retrieve_for_task(task_type, limit)

    async def update_procedure_outcome(self, procedure_id: str, success: bool):
        """Update procedure with outcome."""
        await self.procedural.update_outcome(procedure_id, success)

    # =========================================================================
    # VECTOR MEMORY INTERFACE
    # =========================================================================

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None
    ) -> List[Dict]:
        """Search across all memories semantically."""
        return await self.vector.search(query, limit, memory_type)

    # =========================================================================
    # UNIFIED SEARCH
    # =========================================================================

    async def comprehensive_search(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> Dict[str, List]:
        """Search across all memory types."""
        results = {
            'working': [],
            'episodic': [],
            'semantic': [],
            'procedural': [],
            'vector': []
        }

        types = memory_types or ['working', 'episodic', 'semantic', 'procedural', 'vector']

        if 'working' in types:
            working = self.working.get_all()
            results['working'] = [
                {'key': k, 'value': v}
                for k, v in working.items()
                if query.lower() in str(v).lower()
            ]

        if 'episodic' in types:
            results['episodic'] = await self.recall_episodic(query=query, limit=limit)

        if 'semantic' in types:
            results['semantic'] = await self.query_knowledge(query)

        if 'procedural' in types:
            all_procs = await self.get_procedural_memory()
            results['procedural'] = [
                p for p in all_procs
                if query.lower() in json.dumps(p).lower()
            ][:limit]

        if 'vector' in types:
            results['vector'] = await self.semantic_search(query, limit)

        return results

    # =========================================================================
    # MEMORY CONSOLIDATION
    # =========================================================================

    async def consolidate(self):
        """
        Consolidate memories - move important short-term to long-term.
        Similar to memory consolidation during sleep.
        """
        logger.info("🔄 Starting memory consolidation...")

        # Find high-importance working memory items
        working_items = self.working.get_all()
        for key, value in working_items.items():
            attention = self.working._attention_weights.get(key, 0)
            if attention > 0.7:  # High attention items
                # Store to semantic memory
                await self.store_knowledge(
                    key=f"consolidated_{key}",
                    value=value,
                    category='consolidated'
                )

        # Strengthen frequently accessed memories
        # (Future: implement spaced repetition)

        logger.info("✅ Memory consolidation complete")

    async def forget(self, threshold: float = 0.2):
        """
        Controlled forgetting - remove low-importance old memories.
        """
        logger.info("🧹 Starting controlled forgetting...")

        # Clear low-attention working memory
        to_forget = []
        for key, attention in self.working._attention_weights.items():
            if attention < threshold:
                to_forget.append(key)

        for key in to_forget:
            self.working.remove(key)

        logger.info(f"✅ Forgot {len(to_forget)} low-attention items from working memory")

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    async def save(self):
        """Save all memory systems to disk."""
        logger.info("💾 Saving all memory systems...")

        # Most systems persist on write, but ensure final save
        await self.episodic._persist_entry(list(self.episodic._entries.values())[-1] if self.episodic._entries else None)
        await self.semantic._persist()
        await self.procedural._persist()

        # Save working memory snapshot
        working_file = self.storage_path / "working_snapshot.json"
        with open(working_file, 'w') as f:
            json.dump({
                'items': {k: str(v) for k, v in self.working._items.items()},
                'attention': self.working._attention_weights,
                'saved_at': datetime.now().isoformat()
            }, f, indent=2)

        logger.info("✅ All memory systems saved")

    async def load(self):
        """Load all memory systems from disk."""
        await self.initialize()

        # Restore working memory if snapshot exists
        working_file = self.storage_path / "working_snapshot.json"
        if working_file.exists():
            with open(working_file, 'r') as f:
                data = json.load(f)
                for key, value in data.get('items', {}).items():
                    attention = data.get('attention', {}).get(key, 0.5)
                    self.working.set(key, value, attention)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'MemoryManager',
    'MemoryType',
    'MemoryEntry',
    'MemoryQuery',
    'WorkingMemory',
    'EpisodicMemory',
    'SemanticMemory',
    'ProceduralMemory',
    'VectorMemory'
]
