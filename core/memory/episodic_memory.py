"""
BAEL Episodic Memory
=====================

Autobiographical memory for AI agents.
Stores and retrieves event-based experiences.

Features:
- Temporal indexing
- Context-based retrieval
- Memory consolidation
- Experience replay
- Emotion tagging
"""

import asyncio
import hashlib
import json
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class EmotionalValence(Enum):
    """Emotional valence of memories."""
    VERY_POSITIVE = 2
    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1
    VERY_NEGATIVE = -2


class MemoryStrength(Enum):
    """Memory strength levels."""
    FLEETING = "fleeting"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    PERMANENT = "permanent"


@dataclass
class TemporalContext:
    """Temporal context for an episode."""
    timestamp: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0

    # Temporal markers
    day_of_week: int = 0
    hour_of_day: int = 0

    # Relative timing
    since_last_episode: float = 0.0
    session_number: int = 0

    def __post_init__(self):
        self.day_of_week = self.timestamp.weekday()
        self.hour_of_day = self.timestamp.hour


@dataclass
class MemoryTrace:
    """A trace/feature of a memory."""
    feature_type: str
    value: Any
    salience: float = 1.0  # How distinctive

    # Associations
    associated_concepts: List[str] = field(default_factory=list)

    def similarity(self, other: "MemoryTrace") -> float:
        """Calculate similarity to another trace."""
        if self.feature_type != other.feature_type:
            return 0.0

        if isinstance(self.value, str) and isinstance(other.value, str):
            # String similarity
            return 1.0 if self.value == other.value else 0.3
        elif isinstance(self.value, (int, float)) and isinstance(other.value, (int, float)):
            # Numerical similarity
            diff = abs(self.value - other.value)
            return max(0.0, 1.0 - diff / (max(abs(self.value), abs(other.value), 1)))
        elif isinstance(self.value, list) and isinstance(other.value, list):
            # List overlap
            set1, set2 = set(self.value), set(other.value)
            if not set1 and not set2:
                return 1.0
            return len(set1 & set2) / len(set1 | set2)

        return 1.0 if self.value == other.value else 0.0


@dataclass
class Episode:
    """An episodic memory."""
    id: str
    description: str

    # Content
    traces: List[MemoryTrace] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    # Temporal
    temporal: TemporalContext = field(default_factory=TemporalContext)

    # Emotional
    valence: EmotionalValence = EmotionalValence.NEUTRAL
    arousal: float = 0.5  # 0-1 intensity

    # Memory properties
    strength: MemoryStrength = MemoryStrength.MODERATE
    access_count: int = 0
    importance: float = 0.5

    # Associations
    linked_episodes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    consolidation_level: int = 0

    # Embedding for semantic search
    embedding: Optional[List[float]] = None

    def decay(self, time_delta: timedelta) -> None:
        """Apply memory decay."""
        hours = time_delta.total_seconds() / 3600

        # Ebbinghaus forgetting curve
        decay_rate = 0.1
        retention = math.exp(-decay_rate * hours)

        # Stronger memories decay slower
        strength_factor = {
            MemoryStrength.PERMANENT: 1.0,
            MemoryStrength.STRONG: 0.9,
            MemoryStrength.MODERATE: 0.7,
            MemoryStrength.WEAK: 0.5,
            MemoryStrength.FLEETING: 0.3,
        }

        adjusted_retention = retention * strength_factor[self.strength]
        self.importance *= adjusted_retention

    def reinforce(self, amount: float = 0.1) -> None:
        """Reinforce memory (prevent decay)."""
        self.access_count += 1
        self.last_accessed = datetime.now()
        self.importance = min(1.0, self.importance + amount)

        # Potentially strengthen
        if self.access_count > 10 and self.strength == MemoryStrength.MODERATE:
            self.strength = MemoryStrength.STRONG
        elif self.access_count > 50 and self.strength == MemoryStrength.STRONG:
            self.strength = MemoryStrength.PERMANENT


class EpisodicMemory:
    """
    Episodic memory system for BAEL.

    Manages autobiographical memories with temporal
    and contextual indexing.
    """

    def __init__(
        self,
        max_episodes: int = 10000,
        decay_enabled: bool = True,
    ):
        self.max_episodes = max_episodes
        self.decay_enabled = decay_enabled

        # Storage
        self._episodes: Dict[str, Episode] = {}

        # Indices
        self._temporal_index: Dict[str, List[str]] = {}  # date -> episode_ids
        self._tag_index: Dict[str, Set[str]] = {}
        self._context_index: Dict[str, Set[str]] = {}

        # Recent access buffer
        self._recent: deque = deque(maxlen=100)

        # Session tracking
        self._session_number = 0
        self._last_episode_time: Optional[datetime] = None

        # Stats
        self.stats = {
            "episodes_created": 0,
            "episodes_retrieved": 0,
            "episodes_forgotten": 0,
            "consolidations": 0,
        }

    def encode(
        self,
        description: str,
        traces: Optional[List[MemoryTrace]] = None,
        context: Optional[Dict[str, Any]] = None,
        valence: EmotionalValence = EmotionalValence.NEUTRAL,
        arousal: float = 0.5,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
    ) -> Episode:
        """
        Encode a new episodic memory.

        Args:
            description: Episode description
            traces: Memory traces/features
            context: Contextual information
            valence: Emotional valence
            arousal: Emotional intensity
            tags: Episode tags
            importance: Initial importance

        Returns:
            Created episode
        """
        episode_id = hashlib.md5(
            f"{description}:{datetime.now()}".encode()
        ).hexdigest()[:16]

        # Create temporal context
        now = datetime.now()
        since_last = 0.0
        if self._last_episode_time:
            since_last = (now - self._last_episode_time).total_seconds()

        temporal = TemporalContext(
            timestamp=now,
            since_last_episode=since_last,
            session_number=self._session_number,
        )

        episode = Episode(
            id=episode_id,
            description=description,
            traces=traces or [],
            context=context or {},
            temporal=temporal,
            valence=valence,
            arousal=arousal,
            tags=tags or [],
            importance=importance,
        )

        # Store
        self._episodes[episode_id] = episode
        self._last_episode_time = now

        # Index
        self._index_episode(episode)

        self.stats["episodes_created"] += 1

        # Manage capacity
        if len(self._episodes) > self.max_episodes:
            self._forget_weakest()

        logger.debug(f"Encoded episode: {episode_id}")

        return episode

    def _index_episode(self, episode: Episode) -> None:
        """Index an episode for retrieval."""
        # Temporal index
        date_key = episode.temporal.timestamp.strftime("%Y-%m-%d")
        if date_key not in self._temporal_index:
            self._temporal_index[date_key] = []
        self._temporal_index[date_key].append(episode.id)

        # Tag index
        for tag in episode.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(episode.id)

        # Context index
        for key in episode.context.keys():
            if key not in self._context_index:
                self._context_index[key] = set()
            self._context_index[key].add(episode.id)

    def retrieve(
        self,
        episode_id: str,
        reinforce: bool = True,
    ) -> Optional[Episode]:
        """Retrieve an episode by ID."""
        if episode_id not in self._episodes:
            return None

        episode = self._episodes[episode_id]

        if reinforce:
            episode.reinforce()

        self._recent.append(episode_id)
        self.stats["episodes_retrieved"] += 1

        return episode

    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        context_keys: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        valence: Optional[EmotionalValence] = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> List[Episode]:
        """
        Search episodic memory.

        Args:
            query: Text query
            tags: Filter by tags
            context_keys: Filter by context keys
            time_range: Filter by time range
            valence: Filter by emotional valence
            min_importance: Minimum importance
            limit: Maximum results

        Returns:
            Matching episodes
        """
        candidates = set(self._episodes.keys())

        # Filter by tags
        if tags:
            tag_matches = set()
            for tag in tags:
                if tag in self._tag_index:
                    tag_matches.update(self._tag_index[tag])
            candidates &= tag_matches

        # Filter by context
        if context_keys:
            context_matches = set()
            for key in context_keys:
                if key in self._context_index:
                    context_matches.update(self._context_index[key])
            candidates &= context_matches

        # Filter by time
        if time_range:
            start, end = time_range
            time_matches = set()
            for ep_id in candidates:
                ep = self._episodes[ep_id]
                if start <= ep.temporal.timestamp <= end:
                    time_matches.add(ep_id)
            candidates = time_matches

        # Get episodes and apply remaining filters
        results = []
        for ep_id in candidates:
            ep = self._episodes[ep_id]

            if ep.importance < min_importance:
                continue

            if valence and ep.valence != valence:
                continue

            if query:
                # Simple text matching
                if query.lower() not in ep.description.lower():
                    continue

            results.append(ep)

        # Sort by importance and recency
        results.sort(key=lambda e: (e.importance, e.last_accessed), reverse=True)

        # Reinforce accessed memories
        for ep in results[:limit]:
            ep.reinforce(0.05)
            self._recent.append(ep.id)

        return results[:limit]

    def search_similar(
        self,
        episode: Episode,
        limit: int = 5,
    ) -> List[Tuple[Episode, float]]:
        """Find similar episodes."""
        scores = []

        for ep_id, other in self._episodes.items():
            if ep_id == episode.id:
                continue

            similarity = self._calculate_similarity(episode, other)
            if similarity > 0.1:
                scores.append((other, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:limit]

    def _calculate_similarity(
        self,
        ep1: Episode,
        ep2: Episode,
    ) -> float:
        """Calculate similarity between episodes."""
        # Tag overlap
        tags1, tags2 = set(ep1.tags), set(ep2.tags)
        tag_sim = len(tags1 & tags2) / len(tags1 | tags2) if tags1 or tags2 else 0

        # Trace similarity
        trace_sim = 0.0
        if ep1.traces and ep2.traces:
            matches = 0
            for t1 in ep1.traces:
                for t2 in ep2.traces:
                    matches += t1.similarity(t2)
            trace_sim = matches / (len(ep1.traces) * len(ep2.traces))

        # Context overlap
        ctx1, ctx2 = set(ep1.context.keys()), set(ep2.context.keys())
        ctx_sim = len(ctx1 & ctx2) / len(ctx1 | ctx2) if ctx1 or ctx2 else 0

        # Temporal proximity
        time_diff = abs((ep1.temporal.timestamp - ep2.temporal.timestamp).total_seconds())
        time_sim = math.exp(-time_diff / 86400)  # Decay over days

        # Weighted combination
        return 0.3 * tag_sim + 0.3 * trace_sim + 0.2 * ctx_sim + 0.2 * time_sim

    def link_episodes(
        self,
        episode_id1: str,
        episode_id2: str,
    ) -> bool:
        """Create bidirectional link between episodes."""
        if episode_id1 not in self._episodes or episode_id2 not in self._episodes:
            return False

        ep1 = self._episodes[episode_id1]
        ep2 = self._episodes[episode_id2]

        if episode_id2 not in ep1.linked_episodes:
            ep1.linked_episodes.append(episode_id2)
        if episode_id1 not in ep2.linked_episodes:
            ep2.linked_episodes.append(episode_id1)

        return True

    def apply_decay(self) -> int:
        """Apply decay to all memories."""
        if not self.decay_enabled:
            return 0

        now = datetime.now()
        decayed = 0

        for episode in self._episodes.values():
            delta = now - episode.last_accessed
            if delta.total_seconds() > 60:  # Only decay after 1 minute
                episode.decay(delta)
                decayed += 1

        return decayed

    def _forget_weakest(self) -> None:
        """Forget the weakest memories."""
        if not self._episodes:
            return

        # Find weakest
        weakest = min(
            self._episodes.values(),
            key=lambda e: e.importance * (1 if e.strength != MemoryStrength.PERMANENT else 10),
        )

        if weakest.strength == MemoryStrength.PERMANENT:
            return

        self._remove_episode(weakest.id)
        self.stats["episodes_forgotten"] += 1

    def _remove_episode(self, episode_id: str) -> None:
        """Remove an episode and its indices."""
        if episode_id not in self._episodes:
            return

        episode = self._episodes[episode_id]

        # Remove from indices
        date_key = episode.temporal.timestamp.strftime("%Y-%m-%d")
        if date_key in self._temporal_index:
            self._temporal_index[date_key] = [
                e for e in self._temporal_index[date_key] if e != episode_id
            ]

        for tag in episode.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(episode_id)

        for key in episode.context.keys():
            if key in self._context_index:
                self._context_index[key].discard(episode_id)

        del self._episodes[episode_id]

    def get_recent(self, n: int = 10) -> List[Episode]:
        """Get recently accessed episodes."""
        recent_ids = list(self._recent)[-n:]
        return [self._episodes[eid] for eid in recent_ids if eid in self._episodes]

    def start_session(self) -> None:
        """Start a new session."""
        self._session_number += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self.stats,
            "total_episodes": len(self._episodes),
            "sessions": self._session_number,
        }


def demo():
    """Demonstrate episodic memory."""
    print("=" * 60)
    print("BAEL Episodic Memory Demo")
    print("=" * 60)

    memory = EpisodicMemory()
    memory.start_session()

    # Encode episodes
    print("\nEncoding episodes...")

    ep1 = memory.encode(
        description="Successfully debugged authentication issue",
        traces=[
            MemoryTrace("action", "debugging", salience=0.9),
            MemoryTrace("file", "auth.py", salience=0.8),
        ],
        context={"project": "webapp", "difficulty": "high"},
        valence=EmotionalValence.POSITIVE,
        tags=["debugging", "success", "authentication"],
        importance=0.8,
    )

    ep2 = memory.encode(
        description="Implemented new caching layer",
        traces=[
            MemoryTrace("action", "development", salience=0.9),
            MemoryTrace("file", "cache.py", salience=0.8),
        ],
        context={"project": "webapp", "difficulty": "medium"},
        valence=EmotionalValence.POSITIVE,
        tags=["development", "performance", "caching"],
        importance=0.7,
    )

    ep3 = memory.encode(
        description="Failed deployment due to config error",
        traces=[
            MemoryTrace("action", "deployment", salience=0.9),
            MemoryTrace("error", "config_missing", salience=1.0),
        ],
        context={"project": "webapp", "environment": "production"},
        valence=EmotionalValence.NEGATIVE,
        arousal=0.8,
        tags=["deployment", "failure", "config"],
        importance=0.9,
    )

    print(f"  Created {len(memory._episodes)} episodes")

    # Link related episodes
    memory.link_episodes(ep1.id, ep2.id)

    # Search
    print("\nSearching episodes...")

    results = memory.search(tags=["debugging"])
    print(f"  Tag 'debugging': {len(results)} results")

    results = memory.search(valence=EmotionalValence.NEGATIVE)
    print(f"  Negative valence: {len(results)} results")

    results = memory.search(min_importance=0.75)
    print(f"  High importance: {len(results)} results")

    # Similar episodes
    print("\nFinding similar episodes...")
    similar = memory.search_similar(ep1, limit=2)
    for ep, score in similar:
        print(f"  {ep.description[:40]}... (similarity: {score:.2f})")

    # Access and reinforce
    print("\nReinforcing memories...")
    retrieved = memory.retrieve(ep1.id)
    print(f"  Episode access count: {retrieved.access_count}")

    for _ in range(5):
        memory.retrieve(ep1.id)
    print(f"  After reinforcement: {retrieved.access_count}")

    # Recent episodes
    recent = memory.get_recent(5)
    print(f"\nRecent episodes: {len(recent)}")

    print(f"\nStats: {memory.get_stats()}")


if __name__ == "__main__":
    demo()
