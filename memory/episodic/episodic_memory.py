"""
BAEL - Episodic Memory System
Stores and retrieves autobiographical experiences and events.

Episodic memory captures:
- Specific events with temporal context
- User interactions and outcomes
- Task execution history
- Learning experiences
- Emotional context and importance
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Memory.Episodic")


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class EventType(Enum):
    """Types of episodic events."""
    CONVERSATION = "conversation"
    TASK_EXECUTION = "task_execution"
    LEARNING = "learning"
    ERROR = "error"
    SUCCESS = "success"
    DECISION = "decision"
    DISCOVERY = "discovery"
    INTERACTION = "interaction"
    REFLECTION = "reflection"
    INSIGHT = "insight"


class EmotionalValence(Enum):
    """Emotional context of episodes."""
    VERY_POSITIVE = 2
    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1
    VERY_NEGATIVE = -2


@dataclass
class Episode:
    """A single episodic memory entry."""
    id: str
    event_type: EventType
    timestamp: datetime
    content: str
    context: Dict[str, Any]
    participants: List[str]  # e.g., ["user", "architect_persona", "coder_persona"]
    location: str  # conceptual location (e.g., "code_review", "research_session")
    duration_seconds: float
    outcome: Optional[str] = None
    emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL
    importance: float = 0.5  # 0.0 to 1.0
    tags: List[str] = field(default_factory=list)
    linked_episodes: List[str] = field(default_factory=list)  # Related episode IDs
    embedding: Optional[List[float]] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    decay_rate: float = 0.01  # Memory decay factor

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "context": self.context,
            "participants": self.participants,
            "location": self.location,
            "duration_seconds": self.duration_seconds,
            "outcome": self.outcome,
            "emotional_valence": self.emotional_valence.value,
            "importance": self.importance,
            "tags": self.tags,
            "linked_episodes": self.linked_episodes,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "decay_rate": self.decay_rate
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        return cls(
            id=data["id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content=data["content"],
            context=data.get("context", {}),
            participants=data.get("participants", []),
            location=data.get("location", "unknown"),
            duration_seconds=data.get("duration_seconds", 0),
            outcome=data.get("outcome"),
            emotional_valence=EmotionalValence(data.get("emotional_valence", 0)),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            linked_episodes=data.get("linked_episodes", []),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            decay_rate=data.get("decay_rate", 0.01)
        )

    def current_strength(self) -> float:
        """Calculate current memory strength with decay."""
        if not self.last_accessed:
            base_time = self.timestamp
        else:
            base_time = self.last_accessed

        hours_elapsed = (datetime.now() - base_time).total_seconds() / 3600
        decay = self.decay_rate * hours_elapsed

        # Strength factors
        base_strength = self.importance
        access_bonus = min(0.3, self.access_count * 0.02)
        emotional_bonus = abs(self.emotional_valence.value) * 0.1

        strength = (base_strength + access_bonus + emotional_bonus) * (1 - decay)
        return max(0.0, min(1.0, strength))


@dataclass
class EpisodeQuery:
    """Query parameters for searching episodes."""
    text: Optional[str] = None
    event_types: Optional[List[EventType]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    participants: Optional[List[str]] = None
    location: Optional[str] = None
    min_importance: float = 0.0
    tags: Optional[List[str]] = None
    emotional_valence: Optional[EmotionalValence] = None
    limit: int = 20
    include_weak: bool = False  # Include decayed memories


# =============================================================================
# EPISODIC MEMORY STORE
# =============================================================================

class EpisodicMemoryStore:
    """
    Persistent storage for episodic memories.

    Uses SQLite for durability with in-memory caching for performance.
    """

    def __init__(self, db_path: str = "memory/episodic/episodes.db"):
        self.db_path = db_path
        self._cache: Dict[str, Episode] = {}
        self._cache_limit = 1000
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database."""
        if self._initialized:
            return

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Create database and tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT,
                participants TEXT,
                location TEXT,
                duration_seconds REAL,
                outcome TEXT,
                emotional_valence INTEGER,
                importance REAL,
                tags TEXT,
                linked_episodes TEXT,
                embedding BLOB,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                decay_rate REAL DEFAULT 0.01
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON episodes(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON episodes(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON episodes(location)")

        conn.commit()
        conn.close()

        self._initialized = True
        logger.info(f"Episodic memory store initialized at {self.db_path}")

    def _generate_id(self, content: str, timestamp: datetime) -> str:
        """Generate unique episode ID."""
        data = f"{content}{timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    async def store(self, episode: Episode) -> str:
        """Store an episode."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO episodes
            (id, event_type, timestamp, content, context, participants, location,
             duration_seconds, outcome, emotional_valence, importance, tags,
             linked_episodes, embedding, access_count, last_accessed, decay_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode.id,
            episode.event_type.value,
            episode.timestamp.isoformat(),
            episode.content,
            json.dumps(episode.context),
            json.dumps(episode.participants),
            episode.location,
            episode.duration_seconds,
            episode.outcome,
            episode.emotional_valence.value,
            episode.importance,
            json.dumps(episode.tags),
            json.dumps(episode.linked_episodes),
            json.dumps(episode.embedding) if episode.embedding else None,
            episode.access_count,
            episode.last_accessed.isoformat() if episode.last_accessed else None,
            episode.decay_rate
        ))

        conn.commit()
        conn.close()

        # Update cache
        self._cache[episode.id] = episode
        self._trim_cache()

        logger.debug(f"Stored episode: {episode.id}")
        return episode.id

    async def retrieve(self, episode_id: str) -> Optional[Episode]:
        """Retrieve an episode by ID."""
        await self.initialize()

        # Check cache first
        if episode_id in self._cache:
            episode = self._cache[episode_id]
            await self._record_access(episode)
            return episode

        # Query database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        episode = self._row_to_episode(row)
        await self._record_access(episode)

        # Cache it
        self._cache[episode_id] = episode
        self._trim_cache()

        return episode

    async def search(self, query: EpisodeQuery) -> List[Episode]:
        """Search episodes based on query parameters."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        sql = "SELECT * FROM episodes WHERE 1=1"
        params = []

        if query.event_types:
            placeholders = ",".join("?" * len(query.event_types))
            sql += f" AND event_type IN ({placeholders})"
            params.extend([et.value for et in query.event_types])

        if query.time_range:
            sql += " AND timestamp BETWEEN ? AND ?"
            params.extend([
                query.time_range[0].isoformat(),
                query.time_range[1].isoformat()
            ])

        if query.location:
            sql += " AND location = ?"
            params.append(query.location)

        if query.min_importance > 0:
            sql += " AND importance >= ?"
            params.append(query.min_importance)

        if query.emotional_valence:
            sql += " AND emotional_valence = ?"
            params.append(query.emotional_valence.value)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(query.limit * 2)  # Get extra for filtering

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        episodes = [self._row_to_episode(row) for row in rows]

        # Apply additional filters
        if query.text:
            text_lower = query.text.lower()
            episodes = [e for e in episodes if text_lower in e.content.lower()]

        if query.participants:
            episodes = [e for e in episodes
                       if any(p in e.participants for p in query.participants)]

        if query.tags:
            episodes = [e for e in episodes
                       if any(t in e.tags for t in query.tags)]

        # Filter weak memories unless requested
        if not query.include_weak:
            episodes = [e for e in episodes if e.current_strength() > 0.1]

        # Sort by relevance (strength + recency)
        episodes.sort(key=lambda e: (e.current_strength(), e.timestamp), reverse=True)

        return episodes[:query.limit]

    async def get_recent(self, hours: int = 24, limit: int = 50) -> List[Episode]:
        """Get recent episodes."""
        cutoff = datetime.now() - timedelta(hours=hours)
        query = EpisodeQuery(
            time_range=(cutoff, datetime.now()),
            limit=limit
        )
        return await self.search(query)

    async def get_by_type(self, event_type: EventType, limit: int = 20) -> List[Episode]:
        """Get episodes by type."""
        query = EpisodeQuery(event_types=[event_type], limit=limit)
        return await self.search(query)

    async def get_related(self, episode_id: str, limit: int = 10) -> List[Episode]:
        """Get episodes related to a given episode."""
        episode = await self.retrieve(episode_id)
        if not episode:
            return []

        related = []

        # Get directly linked episodes
        for linked_id in episode.linked_episodes:
            linked = await self.retrieve(linked_id)
            if linked:
                related.append(linked)

        # Find episodes with similar tags
        if episode.tags:
            query = EpisodeQuery(tags=episode.tags, limit=limit)
            similar = await self.search(query)
            for s in similar:
                if s.id != episode_id and s not in related:
                    related.append(s)

        return related[:limit]

    async def link_episodes(self, episode_id1: str, episode_id2: str) -> None:
        """Create a bidirectional link between episodes."""
        ep1 = await self.retrieve(episode_id1)
        ep2 = await self.retrieve(episode_id2)

        if ep1 and ep2:
            if episode_id2 not in ep1.linked_episodes:
                ep1.linked_episodes.append(episode_id2)
                await self.store(ep1)

            if episode_id1 not in ep2.linked_episodes:
                ep2.linked_episodes.append(episode_id1)
                await self.store(ep2)

    async def consolidate(self, older_than_hours: int = 168) -> int:
        """
        Consolidate old memories - strengthen important ones, decay others.
        Returns number of memories consolidated.
        """
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        query = EpisodeQuery(
            time_range=(datetime.min, cutoff),
            include_weak=True,
            limit=1000
        )

        old_episodes = await self.search(query)
        consolidated = 0

        for episode in old_episodes:
            strength = episode.current_strength()

            if strength < 0.05:
                # Memory too weak - archive or delete
                await self._archive(episode)
                consolidated += 1
            elif episode.access_count > 5 or episode.importance > 0.7:
                # Frequently accessed or important - reduce decay
                episode.decay_rate *= 0.5
                await self.store(episode)
                consolidated += 1

        logger.info(f"Consolidated {consolidated} episodes")
        return consolidated

    async def _record_access(self, episode: Episode) -> None:
        """Record that an episode was accessed."""
        episode.access_count += 1
        episode.last_accessed = datetime.now()

        # Update in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE episodes SET access_count = ?, last_accessed = ? WHERE id = ?
        """, (episode.access_count, episode.last_accessed.isoformat(), episode.id))
        conn.commit()
        conn.close()

    async def _archive(self, episode: Episode) -> None:
        """Archive a weak memory (could move to cold storage)."""
        # For now, just delete
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM episodes WHERE id = ?", (episode.id,))
        conn.commit()
        conn.close()

        if episode.id in self._cache:
            del self._cache[episode.id]

    def _row_to_episode(self, row: tuple) -> Episode:
        """Convert database row to Episode."""
        return Episode(
            id=row[0],
            event_type=EventType(row[1]),
            timestamp=datetime.fromisoformat(row[2]),
            content=row[3],
            context=json.loads(row[4]) if row[4] else {},
            participants=json.loads(row[5]) if row[5] else [],
            location=row[6] or "unknown",
            duration_seconds=row[7] or 0,
            outcome=row[8],
            emotional_valence=EmotionalValence(row[9]) if row[9] is not None else EmotionalValence.NEUTRAL,
            importance=row[10] or 0.5,
            tags=json.loads(row[11]) if row[11] else [],
            linked_episodes=json.loads(row[12]) if row[12] else [],
            embedding=json.loads(row[13]) if row[13] else None,
            access_count=row[14] or 0,
            last_accessed=datetime.fromisoformat(row[15]) if row[15] else None,
            decay_rate=row[16] or 0.01
        )

    def _trim_cache(self) -> None:
        """Trim cache to limit."""
        if len(self._cache) > self._cache_limit:
            # Remove oldest accessed
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_accessed or x[1].timestamp
            )
            for key, _ in sorted_items[:len(self._cache) - self._cache_limit]:
                del self._cache[key]

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        await self.initialize()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM episodes")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT event_type, COUNT(*) FROM episodes GROUP BY event_type
        """)
        by_type = dict(cursor.fetchall())

        cursor.execute("SELECT AVG(importance) FROM episodes")
        avg_importance = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM episodes
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        last_24h = cursor.fetchone()[0]

        conn.close()

        return {
            "total_episodes": total,
            "by_type": by_type,
            "average_importance": avg_importance,
            "last_24h": last_24h,
            "cache_size": len(self._cache)
        }


# =============================================================================
# EPISODIC MEMORY MANAGER
# =============================================================================

class EpisodicMemoryManager:
    """
    High-level interface for episodic memory operations.

    Provides:
    - Easy episode creation
    - Intelligent retrieval
    - Memory narratives
    - Timeline construction
    """

    def __init__(self, store: Optional[EpisodicMemoryStore] = None):
        self.store = store or EpisodicMemoryStore()
        self._current_session: Optional[str] = None
        self._session_start: Optional[datetime] = None

    async def initialize(self) -> None:
        """Initialize the manager."""
        await self.store.initialize()
        self._start_session()

    def _start_session(self) -> None:
        """Start a new session."""
        self._session_start = datetime.now()
        self._current_session = f"session_{self._session_start.strftime('%Y%m%d_%H%M%S')}"

    async def record_event(
        self,
        content: str,
        event_type: EventType = EventType.INTERACTION,
        context: Optional[Dict[str, Any]] = None,
        participants: Optional[List[str]] = None,
        location: str = "general",
        duration: float = 0,
        outcome: Optional[str] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL
    ) -> str:
        """Record a new episodic event."""
        episode_id = self.store._generate_id(content, datetime.now())

        episode = Episode(
            id=episode_id,
            event_type=event_type,
            timestamp=datetime.now(),
            content=content,
            context=context or {},
            participants=participants or ["system"],
            location=location,
            duration_seconds=duration,
            outcome=outcome,
            importance=importance,
            tags=tags or [],
            emotional_valence=emotional_valence
        )

        # Add session context
        if self._current_session:
            episode.context["session"] = self._current_session

        await self.store.store(episode)
        return episode_id

    async def record_conversation(
        self,
        user_input: str,
        response: str,
        personas_involved: List[str],
        success: bool = True,
        importance: float = 0.5
    ) -> str:
        """Record a conversation exchange."""
        content = f"User: {user_input}\n\nResponse: {response}"

        return await self.record_event(
            content=content,
            event_type=EventType.CONVERSATION,
            participants=["user"] + personas_involved,
            location="conversation",
            outcome="success" if success else "incomplete",
            importance=importance,
            emotional_valence=EmotionalValence.POSITIVE if success else EmotionalValence.NEUTRAL
        )

    async def record_task(
        self,
        task_description: str,
        result: str,
        duration: float,
        success: bool,
        tools_used: Optional[List[str]] = None
    ) -> str:
        """Record a task execution."""
        return await self.record_event(
            content=f"Task: {task_description}\n\nResult: {result}",
            event_type=EventType.TASK_EXECUTION,
            context={"tools_used": tools_used or []},
            location="task_execution",
            duration=duration,
            outcome="success" if success else "failure",
            importance=0.7 if success else 0.5,
            emotional_valence=EmotionalValence.POSITIVE if success else EmotionalValence.NEGATIVE,
            tags=["task"] + (tools_used or [])
        )

    async def record_learning(
        self,
        what_learned: str,
        source: str,
        confidence: float = 0.7
    ) -> str:
        """Record a learning event."""
        return await self.record_event(
            content=what_learned,
            event_type=EventType.LEARNING,
            context={"source": source, "confidence": confidence},
            location="learning",
            importance=0.8,
            emotional_valence=EmotionalValence.POSITIVE,
            tags=["learning", "knowledge"]
        )

    async def record_insight(
        self,
        insight: str,
        related_to: Optional[str] = None
    ) -> str:
        """Record an insight or discovery."""
        episode_id = await self.record_event(
            content=insight,
            event_type=EventType.INSIGHT,
            location="reflection",
            importance=0.9,
            emotional_valence=EmotionalValence.VERY_POSITIVE,
            tags=["insight", "discovery"]
        )

        # Link to related episode if provided
        if related_to:
            await self.store.link_episodes(episode_id, related_to)

        return episode_id

    async def recall_similar(
        self,
        query: str,
        limit: int = 10
    ) -> List[Episode]:
        """Recall episodes similar to a query."""
        return await self.store.search(EpisodeQuery(text=query, limit=limit))

    async def recall_context(
        self,
        context_type: str,
        limit: int = 10
    ) -> List[Episode]:
        """Recall episodes from a specific context/location."""
        return await self.store.search(EpisodeQuery(location=context_type, limit=limit))

    async def get_timeline(
        self,
        start: datetime,
        end: datetime,
        event_types: Optional[List[EventType]] = None
    ) -> List[Episode]:
        """Get a timeline of events."""
        query = EpisodeQuery(
            time_range=(start, end),
            event_types=event_types,
            limit=100
        )
        episodes = await self.store.search(query)
        episodes.sort(key=lambda e: e.timestamp)
        return episodes

    async def get_narrative(
        self,
        topic: Optional[str] = None,
        hours: int = 24
    ) -> str:
        """Generate a narrative summary of recent events."""
        episodes = await self.store.get_recent(hours=hours)

        if topic:
            episodes = [e for e in episodes if topic.lower() in e.content.lower()]

        if not episodes:
            return "No relevant episodes found."

        # Build narrative
        narrative_parts = []
        for ep in episodes[:10]:
            time_str = ep.timestamp.strftime("%H:%M")
            narrative_parts.append(
                f"[{time_str}] {ep.event_type.value}: {ep.content[:200]}..."
            )

        return "\n".join(narrative_parts)

    async def forget_before(self, before: datetime) -> int:
        """Forget episodes before a date (with consolidation)."""
        return await self.store.consolidate(
            older_than_hours=int((datetime.now() - before).total_seconds() / 3600)
        )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "EventType",
    "EmotionalValence",
    "Episode",
    "EpisodeQuery",
    "EpisodicMemoryStore",
    "EpisodicMemoryManager"
]
