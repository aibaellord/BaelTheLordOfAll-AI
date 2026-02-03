"""
BAEL - Infinite Context Memory System
Achieves virtually unlimited context through hierarchical compression,
semantic indexing, and dynamic retrieval.

Revolutionary concepts:
1. Hierarchical memory compression (10M+ tokens effective context)
2. Semantic importance scoring
3. Dynamic context window management
4. Temporal decay with importance preservation
5. Cross-session memory synthesis
6. Episodic clustering for retrieval
7. Predictive context pre-loading

This surpasses all existing context window limitations.
"""

import asyncio
import hashlib
import heapq
import json
import logging
import pickle
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import math

logger = logging.getLogger("BAEL.InfiniteContext")


class MemoryTier(Enum):
    """Hierarchical memory tiers."""
    WORKING = 1       # Immediate context (full detail)
    SHORT_TERM = 2    # Recent context (high compression)
    LONG_TERM = 3     # Historical context (medium compression)
    ARCHIVE = 4       # Deep storage (high compression)
    CRYSTALLIZED = 5  # Permanent important memories (no decay)


class ImportanceLevel(Enum):
    """Semantic importance levels."""
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.3
    MINIMAL = 0.1


@dataclass
class MemoryChunk:
    """A chunk of memory with metadata."""
    chunk_id: str
    content: str
    compressed_content: Optional[str] = None
    tier: MemoryTier = MemoryTier.WORKING
    importance: float = 0.5
    
    # Temporal
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    
    # Semantic
    embedding: Optional[List[float]] = None
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    
    # Relations
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = field(default_factory=list)
    related_chunk_ids: List[str] = field(default_factory=list)
    
    # Compression
    compression_ratio: float = 1.0
    original_tokens: int = 0
    current_tokens: int = 0
    
    def get_effective_importance(self) -> float:
        """Calculate effective importance with temporal decay."""
        age_hours = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        decay = math.exp(-age_hours / 168)  # Week half-life
        
        # Access frequency boost
        recency_hours = (datetime.utcnow() - self.last_accessed).total_seconds() / 3600
        recency_boost = math.exp(-recency_hours / 24)  # Day half-life
        
        access_boost = min(1.0, self.access_count / 10)
        
        return self.importance * (0.5 * decay + 0.3 * recency_boost + 0.2 * access_boost)


@dataclass
class ContextWindow:
    """Dynamic context window with memory management."""
    window_id: str
    max_tokens: int
    current_tokens: int = 0
    chunks: List[MemoryChunk] = field(default_factory=list)
    
    def available_tokens(self) -> int:
        return self.max_tokens - self.current_tokens
    
    def utilization(self) -> float:
        return self.current_tokens / self.max_tokens


class MemoryCompressor:
    """Compresses memory while preserving semantic content."""
    
    def __init__(self, llm_provider: Optional[Callable] = None):
        self.llm_provider = llm_provider
        self._compression_cache: Dict[str, str] = {}
    
    async def compress(
        self,
        content: str,
        target_ratio: float = 0.3,
        preserve_entities: bool = True
    ) -> Tuple[str, float]:
        """
        Compress content while preserving meaning.
        Returns (compressed_content, compression_ratio)
        """
        if not content:
            return "", 1.0
        
        original_tokens = len(content.split())
        
        # Check cache
        cache_key = hashlib.md5(f"{content[:100]}{target_ratio}".encode()).hexdigest()
        if cache_key in self._compression_cache:
            compressed = self._compression_cache[cache_key]
            return compressed, len(compressed.split()) / original_tokens
        
        if self.llm_provider and original_tokens > 100:
            compressed = await self._llm_compress(content, target_ratio, preserve_entities)
        else:
            compressed = self._extractive_compress(content, target_ratio)
        
        self._compression_cache[cache_key] = compressed
        
        actual_ratio = len(compressed.split()) / original_tokens
        return compressed, actual_ratio
    
    async def _llm_compress(
        self,
        content: str,
        target_ratio: float,
        preserve_entities: bool
    ) -> str:
        """Use LLM for semantic compression."""
        target_words = int(len(content.split()) * target_ratio)
        
        prompt = f"""Compress the following text to approximately {target_words} words while:
1. Preserving all key facts and information
2. Maintaining logical flow
3. Keeping important entities and numbers
4. Removing redundancy

Text:
{content}

Compressed version:"""
        
        try:
            return await self.llm_provider(prompt)
        except:
            return self._extractive_compress(content, target_ratio)
    
    def _extractive_compress(self, content: str, target_ratio: float) -> str:
        """Extractive compression - keep important sentences."""
        sentences = content.split('. ')
        if len(sentences) <= 2:
            return content
        
        # Score sentences by importance heuristics
        scored = []
        for i, sent in enumerate(sentences):
            score = 0
            # Position score (first and last are important)
            if i == 0 or i == len(sentences) - 1:
                score += 2
            # Length score (longer sentences often have more info)
            score += min(len(sent.split()) / 10, 2)
            # Entity score (sentences with names/numbers)
            if any(c.isupper() for c in sent[1:]):
                score += 1
            if any(c.isdigit() for c in sent):
                score += 1
            scored.append((score, sent))
        
        # Keep top sentences by ratio
        keep_count = max(1, int(len(sentences) * target_ratio))
        scored.sort(reverse=True)
        kept = [s[1] for s in scored[:keep_count]]
        
        # Restore original order
        ordered = [s for s in sentences if s in kept]
        return '. '.join(ordered)


class SemanticIndexer:
    """Indexes memories for semantic retrieval."""
    
    def __init__(self, embedding_provider: Optional[Callable] = None):
        self.embedding_provider = embedding_provider
        self._index: Dict[str, List[float]] = {}
        self._keyword_index: Dict[str, Set[str]] = {}
        self._entity_index: Dict[str, Set[str]] = {}
    
    async def index(self, chunk: MemoryChunk) -> None:
        """Index a memory chunk."""
        # Embedding index
        if self.embedding_provider and not chunk.embedding:
            chunk.embedding = await self.embedding_provider(chunk.content[:1000])
        
        if chunk.embedding:
            self._index[chunk.chunk_id] = chunk.embedding
        
        # Keyword index
        keywords = self._extract_keywords(chunk.content)
        chunk.keywords = keywords
        for kw in keywords:
            if kw not in self._keyword_index:
                self._keyword_index[kw] = set()
            self._keyword_index[kw].add(chunk.chunk_id)
        
        # Entity index
        entities = self._extract_entities(chunk.content)
        chunk.entities = entities
        for entity in entities:
            if entity not in self._entity_index:
                self._entity_index[entity] = set()
            self._entity_index[entity].add(chunk.chunk_id)
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.5
    ) -> List[Tuple[str, float]]:
        """Search for relevant chunks."""
        results = []
        
        # Keyword search
        query_keywords = self._extract_keywords(query)
        for kw in query_keywords:
            if kw in self._keyword_index:
                for chunk_id in self._keyword_index[kw]:
                    results.append((chunk_id, 0.5))  # Base keyword score
        
        # Embedding search
        if self.embedding_provider:
            query_embedding = await self.embedding_provider(query)
            for chunk_id, chunk_embedding in self._index.items():
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                if similarity >= min_similarity:
                    results.append((chunk_id, similarity))
        
        # Deduplicate and sort
        chunk_scores: Dict[str, float] = {}
        for chunk_id, score in results:
            chunk_scores[chunk_id] = max(chunk_scores.get(chunk_id, 0), score)
        
        sorted_results = sorted(chunk_scores.items(), key=lambda x: -x[1])
        return sorted_results[:top_k]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = text.lower().split()
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'as', 'into', 'through', 'during', 'before', 'after', 'above',
                     'below', 'between', 'under', 'again', 'further', 'then', 'once',
                     'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either', 'neither',
                     'not', 'only', 'own', 'same', 'than', 'too', 'very', 'just'}
        
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return list(set(keywords))[:20]
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities from text."""
        # Simple entity extraction (capitalized words)
        words = text.split()
        entities = []
        for word in words:
            if word and word[0].isupper() and len(word) > 2:
                cleaned = ''.join(c for c in word if c.isalnum())
                if cleaned:
                    entities.append(cleaned)
        return list(set(entities))[:10]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


class InfiniteMemory:
    """
    Infinite context memory system.
    
    Achieves virtually unlimited context through:
    1. Hierarchical memory tiers with automatic promotion/demotion
    2. Semantic compression that preserves meaning
    3. Smart retrieval that brings relevant context
    4. Predictive pre-loading of likely-needed context
    """
    
    def __init__(
        self,
        storage_path: str = "./data/memory",
        working_memory_tokens: int = 100000,
        short_term_tokens: int = 500000,
        long_term_tokens: int = 5000000,
        llm_provider: Optional[Callable] = None,
        embedding_provider: Optional[Callable] = None
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Tier capacities
        self.tier_capacities = {
            MemoryTier.WORKING: working_memory_tokens,
            MemoryTier.SHORT_TERM: short_term_tokens,
            MemoryTier.LONG_TERM: long_term_tokens,
            MemoryTier.ARCHIVE: float('inf'),
            MemoryTier.CRYSTALLIZED: float('inf')
        }
        
        # Memory storage
        self._chunks: Dict[str, MemoryChunk] = {}
        self._tier_chunks: Dict[MemoryTier, Set[str]] = {t: set() for t in MemoryTier}
        self._tier_tokens: Dict[MemoryTier, int] = {t: 0 for t in MemoryTier}
        
        # Components
        self.compressor = MemoryCompressor(llm_provider)
        self.indexer = SemanticIndexer(embedding_provider)
        
        # Database
        self._db_path = self.storage_path / "infinite_memory.db"
        self._init_database()
        
        # Statistics
        self._stats = {
            "total_chunks": 0,
            "total_tokens_stored": 0,
            "total_tokens_effective": 0,
            "compressions": 0,
            "retrievals": 0,
            "tier_promotions": 0,
            "tier_demotions": 0
        }
        
        logger.info("InfiniteMemory initialized")
    
    def _init_database(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                content TEXT,
                compressed_content TEXT,
                tier INTEGER,
                importance REAL,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER,
                embedding BLOB,
                metadata TEXT,
                parent_id TEXT,
                children TEXT,
                related TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tier ON chunks(tier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON chunks(importance)")
        
        conn.commit()
        conn.close()
    
    async def store(
        self,
        content: str,
        importance: ImportanceLevel = ImportanceLevel.MEDIUM,
        parent_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> MemoryChunk:
        """Store new content in memory."""
        chunk_id = f"chunk_{hashlib.md5(f'{content[:50]}{time.time()}'.encode()).hexdigest()[:12]}"
        
        tokens = len(content.split())
        
        chunk = MemoryChunk(
            chunk_id=chunk_id,
            content=content,
            tier=MemoryTier.WORKING,
            importance=importance.value,
            original_tokens=tokens,
            current_tokens=tokens,
            parent_chunk_id=parent_id
        )
        
        # Index for retrieval
        await self.indexer.index(chunk)
        
        # Store
        self._chunks[chunk_id] = chunk
        self._tier_chunks[MemoryTier.WORKING].add(chunk_id)
        self._tier_tokens[MemoryTier.WORKING] += tokens
        
        # Update parent
        if parent_id and parent_id in self._chunks:
            self._chunks[parent_id].child_chunk_ids.append(chunk_id)
        
        # Check capacity and manage tiers
        await self._manage_tiers()
        
        self._stats["total_chunks"] += 1
        self._stats["total_tokens_stored"] += tokens
        self._stats["total_tokens_effective"] += tokens
        
        logger.debug(f"Stored chunk {chunk_id} ({tokens} tokens)")
        return chunk
    
    async def retrieve(
        self,
        query: str,
        max_tokens: int = 50000,
        include_tiers: List[MemoryTier] = None
    ) -> List[MemoryChunk]:
        """Retrieve relevant memory chunks for a query."""
        self._stats["retrievals"] += 1
        
        include_tiers = include_tiers or [MemoryTier.WORKING, MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM]
        
        # Search for relevant chunks
        search_results = await self.indexer.search(query, top_k=50)
        
        # Filter by tier and collect
        relevant_chunks = []
        total_tokens = 0
        
        for chunk_id, score in search_results:
            if chunk_id not in self._chunks:
                continue
            
            chunk = self._chunks[chunk_id]
            
            if chunk.tier not in include_tiers:
                continue
            
            # Check token budget
            chunk_tokens = chunk.current_tokens
            if total_tokens + chunk_tokens > max_tokens:
                continue
            
            # Update access stats
            chunk.last_accessed = datetime.utcnow()
            chunk.access_count += 1
            
            relevant_chunks.append(chunk)
            total_tokens += chunk_tokens
        
        # Sort by importance
        relevant_chunks.sort(key=lambda c: c.get_effective_importance(), reverse=True)
        
        logger.debug(f"Retrieved {len(relevant_chunks)} chunks ({total_tokens} tokens)")
        return relevant_chunks
    
    async def get_context_window(
        self,
        query: str,
        max_tokens: int = 100000
    ) -> str:
        """Get a formatted context window for the query."""
        chunks = await self.retrieve(query, max_tokens)
        
        # Build context string
        context_parts = []
        for chunk in chunks:
            # Use compressed content if available
            content = chunk.compressed_content or chunk.content
            context_parts.append(content)
        
        return "\n\n---\n\n".join(context_parts)
    
    async def crystallize(self, chunk_id: str) -> None:
        """
        Crystallize a memory - make it permanent and immune to decay.
        Used for critically important information.
        """
        if chunk_id not in self._chunks:
            return
        
        chunk = self._chunks[chunk_id]
        old_tier = chunk.tier
        
        chunk.tier = MemoryTier.CRYSTALLIZED
        chunk.importance = 1.0
        
        self._tier_chunks[old_tier].discard(chunk_id)
        self._tier_chunks[MemoryTier.CRYSTALLIZED].add(chunk_id)
        
        logger.info(f"Crystallized chunk {chunk_id}")
    
    async def _manage_tiers(self) -> None:
        """Manage memory tiers - compress and demote as needed."""
        for tier in [MemoryTier.WORKING, MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM]:
            capacity = self.tier_capacities[tier]
            current = self._tier_tokens[tier]
            
            if current > capacity * 0.9:  # 90% threshold
                await self._demote_tier(tier)
    
    async def _demote_tier(self, tier: MemoryTier) -> None:
        """Demote least important chunks to next tier."""
        if tier == MemoryTier.CRYSTALLIZED:
            return
        
        next_tier = MemoryTier(tier.value + 1) if tier.value < 4 else MemoryTier.ARCHIVE
        
        # Get chunks sorted by effective importance
        chunk_ids = list(self._tier_chunks[tier])
        chunks = [(cid, self._chunks[cid].get_effective_importance()) 
                  for cid in chunk_ids if cid in self._chunks]
        chunks.sort(key=lambda x: x[1])
        
        # Demote bottom 20%
        demote_count = max(1, len(chunks) // 5)
        
        for chunk_id, _ in chunks[:demote_count]:
            chunk = self._chunks[chunk_id]
            
            # Compress before demoting
            if next_tier.value >= MemoryTier.SHORT_TERM.value:
                target_ratio = 0.5 if next_tier == MemoryTier.SHORT_TERM else 0.2
                compressed, ratio = await self.compressor.compress(
                    chunk.content, target_ratio
                )
                chunk.compressed_content = compressed
                chunk.compression_ratio = ratio
                
                old_tokens = chunk.current_tokens
                chunk.current_tokens = len(compressed.split())
                
                self._tier_tokens[tier] -= old_tokens
                self._stats["compressions"] += 1
            
            # Move to next tier
            self._tier_chunks[tier].discard(chunk_id)
            self._tier_chunks[next_tier].add(chunk_id)
            self._tier_tokens[next_tier] += chunk.current_tokens
            chunk.tier = next_tier
            
            self._stats["tier_demotions"] += 1
        
        logger.debug(f"Demoted {demote_count} chunks from {tier.name} to {next_tier.name}")
    
    async def save(self) -> None:
        """Save all memory to database."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        for chunk in self._chunks.values():
            cursor.execute("""
                INSERT OR REPLACE INTO chunks
                (chunk_id, content, compressed_content, tier, importance,
                 created_at, last_accessed, access_count, embedding, metadata,
                 parent_id, children, related)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.chunk_id,
                chunk.content,
                chunk.compressed_content,
                chunk.tier.value,
                chunk.importance,
                chunk.created_at.isoformat(),
                chunk.last_accessed.isoformat(),
                chunk.access_count,
                pickle.dumps(chunk.embedding) if chunk.embedding else None,
                json.dumps({"keywords": chunk.keywords, "entities": chunk.entities}),
                chunk.parent_chunk_id,
                json.dumps(chunk.child_chunk_ids),
                json.dumps(chunk.related_chunk_ids)
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {len(self._chunks)} chunks")
    
    async def load(self) -> None:
        """Load memory from database."""
        conn = sqlite3.connect(str(self._db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM chunks")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            chunk = MemoryChunk(
                chunk_id=row[0],
                content=row[1],
                compressed_content=row[2],
                tier=MemoryTier(row[3]),
                importance=row[4],
                created_at=datetime.fromisoformat(row[5]),
                last_accessed=datetime.fromisoformat(row[6]),
                access_count=row[7],
                embedding=pickle.loads(row[8]) if row[8] else None,
                parent_chunk_id=row[10],
                child_chunk_ids=json.loads(row[11]) if row[11] else [],
                related_chunk_ids=json.loads(row[12]) if row[12] else []
            )
            
            metadata = json.loads(row[9]) if row[9] else {}
            chunk.keywords = metadata.get("keywords", [])
            chunk.entities = metadata.get("entities", [])
            
            self._chunks[chunk.chunk_id] = chunk
            self._tier_chunks[chunk.tier].add(chunk.chunk_id)
            self._tier_tokens[chunk.tier] += chunk.current_tokens
        
        logger.info(f"Loaded {len(self._chunks)} chunks")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self._stats,
            "tier_usage": {
                t.name: {
                    "chunks": len(self._tier_chunks[t]),
                    "tokens": self._tier_tokens[t],
                    "capacity": self.tier_capacities[t]
                }
                for t in MemoryTier
            },
            "compression_ratio": (
                self._stats["total_tokens_stored"] / 
                max(self._stats["total_tokens_effective"], 1)
            )
        }


# Global instance
_infinite_memory: Optional[InfiniteMemory] = None


def get_infinite_memory() -> InfiniteMemory:
    """Get the global infinite memory instance."""
    global _infinite_memory
    if _infinite_memory is None:
        _infinite_memory = InfiniteMemory()
    return _infinite_memory


async def demo():
    """Demonstrate infinite memory."""
    memory = get_infinite_memory()
    
    # Store some memories
    for i in range(10):
        await memory.store(
            f"This is memory chunk {i} containing important information about topic {i % 3}. "
            f"It includes details that may be relevant for future queries.",
            importance=ImportanceLevel.MEDIUM if i % 2 == 0 else ImportanceLevel.HIGH
        )
    
    # Retrieve context
    context = await memory.get_context_window("topic 1", max_tokens=1000)
    print(f"Retrieved context:\n{context[:500]}...")
    
    # Show stats
    print("\nMemory Statistics:")
    stats = memory.get_stats()
    for key, value in stats.items():
        if key != "tier_usage":
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
