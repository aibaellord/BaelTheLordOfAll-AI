"""
BAEL Episodic Memory Engine
============================

Tulving's episodic memory - autobiographical events.
What, where, when - mental time travel.

"Ba'el remembers the past." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict
import copy

logger = logging.getLogger("BAEL.EpisodicMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class TemporalRelation(Enum):
    """Temporal relations between events."""
    BEFORE = auto()
    AFTER = auto()
    DURING = auto()
    OVERLAPS = auto()
    SIMULTANEOUS = auto()


class RecollectionType(Enum):
    """Types of recollection."""
    REMEMBER = auto()    # Vivid, detailed recollection
    KNOW = auto()        # Familiarity without details
    GUESS = auto()       # Uncertain retrieval


class CueType(Enum):
    """Types of retrieval cues."""
    TEMPORAL = auto()    # When-based
    SPATIAL = auto()     # Where-based
    CONTENT = auto()     # What-based
    EMOTIONAL = auto()   # Feeling-based
    CONTEXTUAL = auto()  # Overall context


@dataclass
class SpatialContext:
    """
    Spatial context (where).
    """
    location: str
    coordinates: Optional[Tuple[float, float, float]] = None
    environment: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalContext:
    """
    Temporal context (when).
    """
    timestamp: float
    duration: float = 0.0
    sequence_position: int = 0
    time_of_day: str = ""
    day_of_week: str = ""

    @property
    def age(self) -> float:
        """Age of memory in seconds."""
        return time.time() - self.timestamp


@dataclass
class EmotionalContext:
    """
    Emotional context (how it felt).
    """
    valence: float = 0.0      # -1 negative to +1 positive
    arousal: float = 0.0       # 0 calm to 1 excited
    dominance: float = 0.5     # Control feeling
    emotion_label: str = ""


@dataclass
class Episode:
    """
    An episodic memory.
    """
    id: str
    content: Any               # What happened
    spatial: SpatialContext    # Where
    temporal: TemporalContext  # When
    emotional: EmotionalContext
    participants: List[str] = field(default_factory=list)
    features: Dict[str, Any] = field(default_factory=dict)

    # Encoding properties
    encoding_strength: float = 1.0
    rehearsal_count: int = 0
    last_retrieval: Optional[float] = None

    # Decay
    base_level: float = 1.0

    @property
    def age(self) -> float:
        return self.temporal.age

    @property
    def activation(self) -> float:
        """Current activation level (ACT-R style)."""
        # Base-level + decay
        if self.age > 0:
            decay_factor = math.log(1 + self.age) * 0.5
            activation = self.base_level - decay_factor

            # Boost from rehearsals
            activation += math.log(1 + self.rehearsal_count) * 0.3

            return max(0.0, activation)
        return self.base_level


@dataclass
class RetrievalResult:
    """
    Result of memory retrieval.
    """
    episode: Episode
    match_strength: float
    recollection_type: RecollectionType
    retrieval_time: float = field(default_factory=time.time)
    cues_used: List[str] = field(default_factory=list)


# ============================================================================
# EPISODE ENCODER
# ============================================================================

class EpisodeEncoder:
    """
    Encode experiences into episodes.

    "Ba'el encodes experiences." — Ba'el
    """

    def __init__(self):
        """Initialize encoder."""
        self._episode_counter = 0
        self._current_context: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._episode_counter += 1
        return f"episode_{self._episode_counter}"

    def set_context(
        self,
        location: str = None,
        emotion: EmotionalContext = None,
        **kwargs
    ) -> None:
        """Set current encoding context."""
        with self._lock:
            if location:
                self._current_context['location'] = location
            if emotion:
                self._current_context['emotion'] = emotion
            self._current_context.update(kwargs)

    def encode(
        self,
        content: Any,
        location: str = "",
        participants: List[str] = None,
        emotional_valence: float = 0.0,
        emotional_arousal: float = 0.0,
        features: Dict[str, Any] = None,
        encoding_strength: float = 1.0
    ) -> Episode:
        """Encode an episode."""
        with self._lock:
            now = time.time()

            spatial = SpatialContext(
                location=location or self._current_context.get('location', '')
            )

            temporal = TemporalContext(
                timestamp=now
            )

            current_emotion = self._current_context.get('emotion')
            if current_emotion:
                emotional = current_emotion
            else:
                emotional = EmotionalContext(
                    valence=emotional_valence,
                    arousal=emotional_arousal
                )

            episode = Episode(
                id=self._generate_id(),
                content=content,
                spatial=spatial,
                temporal=temporal,
                emotional=emotional,
                participants=participants or [],
                features=features or {},
                encoding_strength=encoding_strength
            )

            return episode

    def encode_sequence(
        self,
        events: List[Any],
        location: str = "",
        interval: float = 1.0
    ) -> List[Episode]:
        """Encode sequence of events."""
        with self._lock:
            episodes = []

            for i, event in enumerate(events):
                episode = self.encode(
                    content=event,
                    location=location
                )
                episode.temporal.sequence_position = i
                episodes.append(episode)

            return episodes


# ============================================================================
# EPISODE STORE
# ============================================================================

class EpisodeStore:
    """
    Store and index episodes.

    "Ba'el's autobiographical store." — Ba'el
    """

    def __init__(self, capacity: int = 10000):
        """Initialize store."""
        self._episodes: Dict[str, Episode] = {}
        self._capacity = capacity

        # Indices
        self._temporal_index: List[str] = []  # Sorted by time
        self._spatial_index: Dict[str, List[str]] = defaultdict(list)
        self._participant_index: Dict[str, List[str]] = defaultdict(list)

        self._lock = threading.RLock()

    def store(self, episode: Episode) -> bool:
        """Store episode."""
        with self._lock:
            # Check capacity
            if len(self._episodes) >= self._capacity:
                self._evict_oldest()

            self._episodes[episode.id] = episode

            # Index temporally
            self._temporal_index.append(episode.id)
            self._temporal_index.sort(
                key=lambda eid: self._episodes[eid].temporal.timestamp
            )

            # Index spatially
            if episode.spatial.location:
                self._spatial_index[episode.spatial.location].append(episode.id)

            # Index by participants
            for participant in episode.participants:
                self._participant_index[participant].append(episode.id)

            return True

    def _evict_oldest(self) -> None:
        """Evict oldest, weakest episode."""
        if not self._episodes:
            return

        # Find weakest activation
        weakest_id = min(
            self._episodes.keys(),
            key=lambda eid: self._episodes[eid].activation
        )

        self.remove(weakest_id)

    def remove(self, episode_id: str) -> bool:
        """Remove episode."""
        with self._lock:
            if episode_id not in self._episodes:
                return False

            episode = self._episodes[episode_id]

            # Remove from indices
            if episode_id in self._temporal_index:
                self._temporal_index.remove(episode_id)

            if episode.spatial.location in self._spatial_index:
                if episode_id in self._spatial_index[episode.spatial.location]:
                    self._spatial_index[episode.spatial.location].remove(episode_id)

            for participant in episode.participants:
                if episode_id in self._participant_index[participant]:
                    self._participant_index[participant].remove(episode_id)

            del self._episodes[episode_id]
            return True

    def get(self, episode_id: str) -> Optional[Episode]:
        """Get episode by ID."""
        return self._episodes.get(episode_id)

    def get_by_location(self, location: str) -> List[Episode]:
        """Get episodes by location."""
        with self._lock:
            episode_ids = self._spatial_index.get(location, [])
            return [self._episodes[eid] for eid in episode_ids if eid in self._episodes]

    def get_by_participant(self, participant: str) -> List[Episode]:
        """Get episodes involving participant."""
        with self._lock:
            episode_ids = self._participant_index.get(participant, [])
            return [self._episodes[eid] for eid in episode_ids if eid in self._episodes]

    def get_recent(self, count: int = 10) -> List[Episode]:
        """Get most recent episodes."""
        with self._lock:
            recent_ids = self._temporal_index[-count:]
            return [self._episodes[eid] for eid in reversed(recent_ids)]

    def get_in_timerange(
        self,
        start: float,
        end: float
    ) -> List[Episode]:
        """Get episodes in time range."""
        with self._lock:
            return [
                ep for ep in self._episodes.values()
                if start <= ep.temporal.timestamp <= end
            ]

    @property
    def episodes(self) -> List[Episode]:
        return list(self._episodes.values())

    @property
    def size(self) -> int:
        return len(self._episodes)


# ============================================================================
# EPISODE RETRIEVER
# ============================================================================

class EpisodeRetriever:
    """
    Retrieve episodes with various cues.

    "Ba'el retrieves the past." — Ba'el
    """

    def __init__(self, store: EpisodeStore):
        """Initialize retriever."""
        self._store = store
        self._retrieval_count = 0
        self._lock = threading.RLock()

    def _compute_match(
        self,
        episode: Episode,
        cue: Dict[str, Any]
    ) -> float:
        """Compute match strength between episode and cue."""
        match = 0.0
        weights = 0.0

        # Content match
        if 'content' in cue:
            cue_content = str(cue['content']).lower()
            ep_content = str(episode.content).lower()

            if cue_content in ep_content or ep_content in cue_content:
                match += 1.0
            elif any(word in ep_content for word in cue_content.split()):
                match += 0.5
            weights += 1.0

        # Location match
        if 'location' in cue:
            if cue['location'].lower() == episode.spatial.location.lower():
                match += 1.0
            weights += 1.0

        # Temporal match
        if 'time' in cue:
            time_diff = abs(cue['time'] - episode.temporal.timestamp)
            # Closer in time = better match
            temporal_match = 1.0 / (1.0 + time_diff / 3600)  # Hour scale
            match += temporal_match
            weights += 1.0

        # Participant match
        if 'participant' in cue:
            if cue['participant'] in episode.participants:
                match += 1.0
            weights += 1.0

        # Emotional match
        if 'valence' in cue:
            valence_diff = abs(cue['valence'] - episode.emotional.valence)
            match += 1.0 - valence_diff
            weights += 1.0

        # Base activation boost
        match += episode.activation * 0.5
        weights += 0.5

        if weights > 0:
            return match / weights
        return 0.0

    def retrieve(
        self,
        cue: Dict[str, Any],
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[RetrievalResult]:
        """Retrieve episodes matching cue."""
        with self._lock:
            self._retrieval_count += 1

            results = []
            cue_types = list(cue.keys())

            for episode in self._store.episodes:
                match_strength = self._compute_match(episode, cue)

                if match_strength >= threshold:
                    # Determine recollection type
                    if match_strength > 0.8:
                        rec_type = RecollectionType.REMEMBER
                    elif match_strength > 0.5:
                        rec_type = RecollectionType.KNOW
                    else:
                        rec_type = RecollectionType.GUESS

                    result = RetrievalResult(
                        episode=episode,
                        match_strength=match_strength,
                        recollection_type=rec_type,
                        cues_used=cue_types
                    )
                    results.append(result)

                    # Update episode retrieval info
                    episode.last_retrieval = time.time()
                    episode.rehearsal_count += 1

            # Sort by match strength
            results.sort(key=lambda r: r.match_strength, reverse=True)

            return results[:top_k]

    def recall_by_time(
        self,
        target_time: float,
        window: float = 3600
    ) -> List[RetrievalResult]:
        """Recall episodes around a time."""
        return self.retrieve(
            {'time': target_time},
            threshold=0.1
        )

    def recall_by_place(self, location: str) -> List[RetrievalResult]:
        """Recall episodes at a place."""
        return self.retrieve({'location': location})

    def recall_by_person(self, participant: str) -> List[RetrievalResult]:
        """Recall episodes with a person."""
        return self.retrieve({'participant': participant})

    @property
    def retrieval_count(self) -> int:
        return self._retrieval_count


# ============================================================================
# EPISODIC MEMORY ENGINE
# ============================================================================

class EpisodicMemoryEngine:
    """
    Complete episodic memory system.

    "Ba'el's autobiographical memory." — Ba'el
    """

    def __init__(self, capacity: int = 10000):
        """Initialize engine."""
        self._encoder = EpisodeEncoder()
        self._store = EpisodeStore(capacity)
        self._retriever = EpisodeRetriever(self._store)
        self._lock = threading.RLock()

    # Encoding

    def experience(
        self,
        what: Any,
        where: str = "",
        who: List[str] = None,
        emotional_valence: float = 0.0,
        emotional_arousal: float = 0.0
    ) -> Episode:
        """Record an experience."""
        episode = self._encoder.encode(
            content=what,
            location=where,
            participants=who,
            emotional_valence=emotional_valence,
            emotional_arousal=emotional_arousal
        )
        self._store.store(episode)
        return episode

    def set_context(
        self,
        location: str = None,
        emotion: EmotionalContext = None
    ) -> None:
        """Set encoding context."""
        self._encoder.set_context(location=location, emotion=emotion)

    # Retrieval

    def remember(
        self,
        cue: Dict[str, Any],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """Remember episodes matching cue."""
        return self._retriever.retrieve(cue, top_k)

    def recall_what(self, content: Any) -> List[RetrievalResult]:
        """Recall by content."""
        return self._retriever.retrieve({'content': content})

    def recall_when(
        self,
        target_time: float,
        window: float = 3600
    ) -> List[RetrievalResult]:
        """Recall by time."""
        return self._retriever.recall_by_time(target_time, window)

    def recall_where(self, location: str) -> List[RetrievalResult]:
        """Recall by location."""
        return self._retriever.recall_by_place(location)

    def recall_who(self, participant: str) -> List[RetrievalResult]:
        """Recall by participant."""
        return self._retriever.recall_by_person(participant)

    def recent_memories(self, count: int = 10) -> List[Episode]:
        """Get recent memories."""
        return self._store.get_recent(count)

    # Mental time travel

    def travel_to(self, episode_id: str) -> Optional[Episode]:
        """Travel to a specific episode."""
        with self._lock:
            episode = self._store.get(episode_id)
            if episode:
                episode.last_retrieval = time.time()
                episode.rehearsal_count += 1
            return episode

    def travel_to_time(self, target_time: float) -> List[Episode]:
        """Travel to a time period."""
        results = self.recall_when(target_time)
        return [r.episode for r in results]

    @property
    def store(self) -> EpisodeStore:
        return self._store

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'episodes': self._store.size,
            'retrievals': self._retriever.retrieval_count,
            'locations': len(self._store._spatial_index),
            'participants': len(self._store._participant_index)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_episodic_memory_engine(capacity: int = 10000) -> EpisodicMemoryEngine:
    """Create episodic memory engine."""
    return EpisodicMemoryEngine(capacity)


def create_episode(
    content: Any,
    location: str = "",
    participants: List[str] = None
) -> Episode:
    """Create episode."""
    return Episode(
        id=f"episode_{random.randint(1000, 9999)}",
        content=content,
        spatial=SpatialContext(location=location),
        temporal=TemporalContext(timestamp=time.time()),
        emotional=EmotionalContext(),
        participants=participants or []
    )
