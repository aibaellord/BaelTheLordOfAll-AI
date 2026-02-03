"""
BAEL - Episodic Memory Module
Autobiographical memory for experiences and events.
"""

from .episodic_memory import (EmotionalValence, Episode, EpisodeQuery,
                              EpisodicMemoryManager, EpisodicMemoryStore,
                              EventType)

__all__ = [
    "EventType",
    "EmotionalValence",
    "Episode",
    "EpisodeQuery",
    "EpisodicMemoryStore",
    "EpisodicMemoryManager"
]
