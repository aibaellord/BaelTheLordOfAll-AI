#!/usr/bin/env python3
"""
BAEL - Advanced Conversation Memory
Long-term conversation memory with semantic retrieval.

Features:
- Conversation persistence
- Semantic similarity search
- Context window management
- Memory consolidation
- Fact extraction
- Preference learning
"""

import asyncio
import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class MemoryType(Enum):
    """Types of memory entries."""
    MESSAGE = "message"
    FACT = "fact"
    PREFERENCE = "preference"
    ENTITY = "entity"
    SUMMARY = "summary"
    INSTRUCTION = "instruction"


class Importance(Enum):
    """Memory importance levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MemoryEntry:
    """Single memory entry."""
    id: str
    type: MemoryType
    content: str
    embedding: Optional[List[float]] = None

    # Metadata
    importance: Importance = Importance.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    # Relationships
    related_ids: List[str] = field(default_factory=list)
    source_id: Optional[str] = None

    # Tracking
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    decay_factor: float = 1.0

    # Extra data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "importance": self.importance.value,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "related_ids": self.related_ids,
            "access_count": self.access_count,
            "decay_factor": self.decay_factor,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(
            id=data["id"],
            type=MemoryType(data["type"]),
            content=data["content"],
            importance=Importance(data.get("importance", 2)),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            related_ids=data.get("related_ids", []),
            access_count=data.get("access_count", 0),
            decay_factor=data.get("decay_factor", 1.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class ConversationMessage:
    """Conversation message."""
    id: str
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Conversation:
    """Full conversation with messages."""
    id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def add_message(self, role: str, content: str, **metadata) -> ConversationMessage:
        """Add a message to the conversation."""
        msg = ConversationMessage(
            id=str(uuid4()),
            role=role,
            content=content,
            metadata=metadata
        )
        self.messages.append(msg)
        self.updated_at = datetime.now()
        return msg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }


# =============================================================================
# EMBEDDING PROVIDER
# =============================================================================

class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Get embedding for text."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for batch of texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self._dimension = 1536 if "3-small" in model else 3072

    async def embed(self, text: str) -> List[float]:
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

        return [item["embedding"] for item in data["data"]]

    @property
    def dimension(self) -> int:
        return self._dimension


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384  # Default for MiniLM

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()

    async def embed(self, text: str) -> List[float]:
        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension


# =============================================================================
# VECTOR STORE
# =============================================================================

class VectorStore(ABC):
    """Abstract vector store."""

    @abstractmethod
    async def add(self, id: str, embedding: List[float], metadata: Dict[str, Any] = None) -> None:
        """Add vector."""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter: Dict[str, Any] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> None:
        """Delete vector."""
        pass


class InMemoryVectorStore(VectorStore):
    """In-memory vector store."""

    def __init__(self):
        self.vectors: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}

    async def add(self, id: str, embedding: List[float], metadata: Dict[str, Any] = None) -> None:
        self.vectors[id] = (embedding, metadata or {})

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter: Dict[str, Any] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        import numpy as np

        query = np.array(query_embedding)
        results = []

        for id, (embedding, metadata) in self.vectors.items():
            # Apply filter
            if filter:
                match = all(metadata.get(k) == v for k, v in filter.items())
                if not match:
                    continue

            # Calculate cosine similarity
            vec = np.array(embedding)
            similarity = np.dot(query, vec) / (np.linalg.norm(query) * np.linalg.norm(vec))
            results.append((id, float(similarity), metadata))

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    async def delete(self, id: str) -> None:
        if id in self.vectors:
            del self.vectors[id]


class ChromaVectorStore(VectorStore):
    """ChromaDB vector store."""

    def __init__(self, collection_name: str = "bael_memory", persist_dir: str = None):
        import chromadb

        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            # Use ephemeral client for in-memory storage
            self.client = chromadb.EphemeralClient()

        self.collection = self.client.get_or_create_collection(collection_name)

    async def add(self, id: str, embedding: List[float], metadata: Dict[str, Any] = None) -> None:
        # Filter out None values from metadata
        clean_metadata = {k: v for k, v in (metadata or {}).items() if v is not None}

        self.collection.add(
            ids=[id],
            embeddings=[embedding],
            metadatas=[clean_metadata] if clean_metadata else None
        )

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filter: Dict[str, Any] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=filter
        )

        output = []
        if results["ids"]:
            for i, id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                # Convert distance to similarity (assuming L2)
                similarity = 1 / (1 + distance)
                output.append((id, similarity, metadata))

        return output

    async def delete(self, id: str) -> None:
        self.collection.delete(ids=[id])


# =============================================================================
# MEMORY MANAGER
# =============================================================================

class ConversationMemory:
    """Manage conversation memory with semantic retrieval."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        max_context_tokens: int = 4000
    ):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.max_context_tokens = max_context_tokens

        self.conversations: Dict[str, Conversation] = {}
        self.memories: Dict[str, MemoryEntry] = {}

    async def create_conversation(self, user_id: str = None) -> Conversation:
        """Create a new conversation."""
        conv = Conversation(
            id=str(uuid4()),
            user_id=user_id
        )
        self.conversations[conv.id] = conv
        return conv

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        extract_facts: bool = True,
        **metadata
    ) -> ConversationMessage:
        """Add message to conversation."""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation not found: {conversation_id}")

        conv = self.conversations[conversation_id]
        msg = conv.add_message(role, content, **metadata)

        # Create memory entry
        memory = MemoryEntry(
            id=msg.id,
            type=MemoryType.MESSAGE,
            content=f"{role}: {content}",
            session_id=conversation_id,
            user_id=conv.user_id
        )

        # Generate embedding
        memory.embedding = await self.embedding_provider.embed(content)

        # Store in vector store
        await self.vector_store.add(
            memory.id,
            memory.embedding,
            {
                "type": memory.type.value,
                "session_id": conversation_id,
                "role": role,
                "timestamp": memory.timestamp.isoformat()
            }
        )

        self.memories[memory.id] = memory

        # Extract facts if enabled
        if extract_facts and role == "user":
            await self._extract_facts(content, conversation_id, conv.user_id)

        return msg

    async def _extract_facts(
        self,
        content: str,
        session_id: str,
        user_id: str = None
    ) -> List[MemoryEntry]:
        """Extract facts from message content."""
        facts = []

        # Simple fact extraction patterns
        patterns = [
            (r"my name is (\w+)", "User's name is {0}"),
            (r"I(?:'m| am) (\d+) years? old", "User is {0} years old"),
            (r"I live in (.+?)(?:\.|$)", "User lives in {0}"),
            (r"I work (?:at|for) (.+?)(?:\.|$)", "User works at {0}"),
            (r"I(?:'m| am) a (\w+)", "User is a {0}"),
            (r"I prefer (\w+)", "User prefers {0}"),
            (r"I like (.+?)(?:\.|$)", "User likes {0}"),
            (r"I don't like (.+?)(?:\.|$)", "User dislikes {0}"),
        ]

        for pattern, template in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                fact_content = template.format(*match.groups())

                fact = MemoryEntry(
                    id=str(uuid4()),
                    type=MemoryType.FACT,
                    content=fact_content,
                    importance=Importance.HIGH,
                    session_id=session_id,
                    user_id=user_id,
                    metadata={"extracted_from": "user_message"}
                )

                fact.embedding = await self.embedding_provider.embed(fact_content)

                await self.vector_store.add(
                    fact.id,
                    fact.embedding,
                    {
                        "type": "fact",
                        "user_id": user_id,
                        "timestamp": fact.timestamp.isoformat()
                    }
                )

                self.memories[fact.id] = fact
                facts.append(fact)

        return facts

    async def get_relevant_context(
        self,
        query: str,
        conversation_id: str = None,
        limit: int = 10,
        include_facts: bool = True
    ) -> List[MemoryEntry]:
        """Get relevant context for a query."""
        # Get query embedding
        query_embedding = await self.embedding_provider.embed(query)

        # Build filter
        filter_dict = None
        if conversation_id and not include_facts:
            filter_dict = {"session_id": conversation_id}

        # Search vector store
        results = await self.vector_store.search(
            query_embedding,
            limit=limit,
            filter=filter_dict
        )

        # Get memory entries
        memories = []
        for id, similarity, metadata in results:
            if id in self.memories:
                memory = self.memories[id]
                memory.access_count += 1
                memory.last_accessed = datetime.now()
                memories.append(memory)

        return memories

    async def get_conversation_history(
        self,
        conversation_id: str,
        max_messages: int = None
    ) -> List[ConversationMessage]:
        """Get conversation history."""
        if conversation_id not in self.conversations:
            return []

        messages = self.conversations[conversation_id].messages

        if max_messages:
            messages = messages[-max_messages:]

        return messages

    async def build_context(
        self,
        query: str,
        conversation_id: str,
        max_tokens: int = None
    ) -> str:
        """Build context string for LLM."""
        max_tokens = max_tokens or self.max_context_tokens

        context_parts = []

        # Get relevant memories
        memories = await self.get_relevant_context(
            query,
            conversation_id,
            limit=5,
            include_facts=True
        )

        # Add facts first
        facts = [m for m in memories if m.type == MemoryType.FACT]
        if facts:
            context_parts.append("Relevant information:")
            for fact in facts[:3]:
                context_parts.append(f"- {fact.content}")

        # Add recent conversation
        history = await self.get_conversation_history(conversation_id, max_messages=10)

        if history:
            context_parts.append("\nRecent conversation:")
            for msg in history[-5:]:
                context_parts.append(f"{msg.role}: {msg.content}")

        return "\n".join(context_parts)

    async def summarize_conversation(
        self,
        conversation_id: str,
        llm_provider: callable = None
    ) -> Optional[MemoryEntry]:
        """Create summary of conversation."""
        if conversation_id not in self.conversations:
            return None

        conv = self.conversations[conversation_id]

        if len(conv.messages) < 5:
            return None

        # Build messages text
        messages_text = "\n".join([
            f"{m.role}: {m.content}"
            for m in conv.messages
        ])

        if llm_provider:
            # Use LLM for summarization
            prompt = f"""Summarize the following conversation in 2-3 sentences:

{messages_text}

Summary:"""
            summary_text = await llm_provider(prompt)
        else:
            # Simple extractive summary
            summary_text = f"Conversation with {len(conv.messages)} messages discussing: {conv.messages[0].content[:100]}..."

        summary = MemoryEntry(
            id=str(uuid4()),
            type=MemoryType.SUMMARY,
            content=summary_text,
            importance=Importance.HIGH,
            session_id=conversation_id,
            user_id=conv.user_id,
            source_id=conversation_id
        )

        summary.embedding = await self.embedding_provider.embed(summary_text)

        await self.vector_store.add(
            summary.id,
            summary.embedding,
            {
                "type": "summary",
                "session_id": conversation_id,
                "timestamp": summary.timestamp.isoformat()
            }
        )

        self.memories[summary.id] = summary

        return summary

    async def forget_old_memories(
        self,
        days: int = 30,
        keep_important: bool = True
    ) -> int:
        """Remove old memories."""
        cutoff = datetime.now() - timedelta(days=days)
        forgotten = 0

        for memory_id in list(self.memories.keys()):
            memory = self.memories[memory_id]

            if memory.timestamp < cutoff:
                if keep_important and memory.importance == Importance.CRITICAL:
                    continue

                await self.vector_store.delete(memory_id)
                del self.memories[memory_id]
                forgotten += 1

        return forgotten

    def get_user_facts(self, user_id: str) -> List[MemoryEntry]:
        """Get all facts for a user."""
        return [
            m for m in self.memories.values()
            if m.type == MemoryType.FACT and m.user_id == user_id
        ]


# =============================================================================
# PERSISTENCE
# =============================================================================

class MemoryPersistence:
    """Persist memory to disk."""

    def __init__(self, path: str):
        from pathlib import Path
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def save(self, memory: ConversationMemory) -> None:
        """Save memory to disk."""
        # Save conversations
        conversations_data = {
            id: conv.to_dict()
            for id, conv in memory.conversations.items()
        }

        with open(self.path / "conversations.json", "w") as f:
            json.dump(conversations_data, f)

        # Save memories (without embeddings)
        memories_data = {
            id: mem.to_dict()
            for id, mem in memory.memories.items()
        }

        with open(self.path / "memories.json", "w") as f:
            json.dump(memories_data, f)

    async def load(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore
    ) -> ConversationMemory:
        """Load memory from disk."""
        memory = ConversationMemory(embedding_provider, vector_store)

        # Load conversations
        conversations_file = self.path / "conversations.json"
        if conversations_file.exists():
            with open(conversations_file) as f:
                conversations_data = json.load(f)

            for id, data in conversations_data.items():
                conv = Conversation(
                    id=data["id"],
                    user_id=data.get("user_id"),
                    title=data.get("title"),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    metadata=data.get("metadata", {})
                )

                for msg_data in data.get("messages", []):
                    conv.messages.append(ConversationMessage(
                        id=msg_data["id"],
                        role=msg_data["role"],
                        content=msg_data["content"],
                        timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                        metadata=msg_data.get("metadata", {})
                    ))

                memory.conversations[id] = conv

        # Load memories
        memories_file = self.path / "memories.json"
        if memories_file.exists():
            with open(memories_file) as f:
                memories_data = json.load(f)

            for id, data in memories_data.items():
                mem = MemoryEntry.from_dict(data)

                # Regenerate embedding
                mem.embedding = await embedding_provider.embed(mem.content)

                # Add to vector store
                await vector_store.add(
                    mem.id,
                    mem.embedding,
                    {"type": mem.type.value, "session_id": mem.session_id}
                )

                memory.memories[id] = mem

        return memory


# =============================================================================
# MAIN
# =============================================================================

async def demo():
    """Demo conversation memory."""
    # Use in-memory stores for demo
    from typing import List as ListType

    class DemoEmbedding(EmbeddingProvider):
        async def embed(self, text: str) -> ListType[float]:
            # Simple hash-based embedding for demo
            import hashlib
            h = hashlib.md5(text.encode()).hexdigest()
            return [int(h[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]

        async def embed_batch(self, texts: ListType[str]) -> ListType[ListType[float]]:
            return [await self.embed(t) for t in texts]

        @property
        def dimension(self) -> int:
            return 16

    embedding = DemoEmbedding()
    vector_store = InMemoryVectorStore()
    memory = ConversationMemory(embedding, vector_store)

    # Create conversation
    conv = await memory.create_conversation(user_id="user123")
    print(f"Created conversation: {conv.id}")

    # Add messages
    await memory.add_message(conv.id, "user", "Hi! My name is Alice and I'm a software developer.")
    await memory.add_message(conv.id, "assistant", "Hello Alice! Nice to meet you. What kind of development do you do?")
    await memory.add_message(conv.id, "user", "I work at Google and I mostly do Python and Go programming.")
    await memory.add_message(conv.id, "assistant", "That's great! How can I help you today?")
    await memory.add_message(conv.id, "user", "I prefer dark mode themes for my editor.")

    # Get facts
    facts = memory.get_user_facts("user123")
    print(f"\nExtracted facts ({len(facts)}):")
    for fact in facts:
        print(f"  - {fact.content}")

    # Get relevant context
    print("\nRelevant context for 'What programming languages does Alice use?':")
    context = await memory.build_context(
        "What programming languages does Alice use?",
        conv.id
    )
    print(context)

    # Test semantic search
    print("\nSemantic search for 'work':")
    memories = await memory.get_relevant_context("work and employment", limit=3)
    for mem in memories:
        print(f"  - {mem.content[:80]}...")


if __name__ == "__main__":
    asyncio.run(demo())
