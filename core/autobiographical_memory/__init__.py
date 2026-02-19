"""
BAEL Autobiographical Memory Engine
=====================================

Conway's self-memory system.
Life story and personal identity.

"Ba'el remembers the self." — Ba'el
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
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.AutobiographicalMemory")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class MemoryLevel(Enum):
    """Conway's autobiographical memory levels."""
    LIFETIME_PERIOD = auto()      # "When I lived in NYC"
    GENERAL_EVENT = auto()        # "My first job"
    EVENT_SPECIFIC = auto()       # "That meeting on Tuesday"


class LifeTheme(Enum):
    """Life story themes."""
    AGENCY = auto()          # Control, achievement
    COMMUNION = auto()        # Love, relationships
    REDEMPTION = auto()       # Bad to good
    CONTAMINATION = auto()    # Good to bad
    GROWTH = auto()           # Development
    LOSS = auto()             # Decline


class LifeChapter(Enum):
    """Life chapters."""
    CHILDHOOD = auto()
    ADOLESCENCE = auto()
    YOUNG_ADULT = auto()
    MIDDLE_ADULT = auto()
    LATE_ADULT = auto()


class SelfConcept(Enum):
    """Working self-concept aspects."""
    CURRENT_GOALS = auto()
    SELF_IMAGES = auto()
    SELF_BELIEFS = auto()
    POSSIBLE_SELVES = auto()


@dataclass
class LifetimePeriod:
    """
    A lifetime period in autobiographical memory.
    """
    id: str
    name: str
    theme: str
    start_age: int
    end_age: Optional[int]
    general_events: List[str]


@dataclass
class GeneralEvent:
    """
    A general event (extended/repeated).
    """
    id: str
    name: str
    category: str
    lifetime_period_id: str
    specific_events: List[str]
    emotional_valence: float


@dataclass
class SpecificEvent:
    """
    A specific autobiographical event.
    """
    id: str
    description: str
    general_event_id: str
    age_at_event: int

    # Episodic details
    sensory_details: Dict[str, str]
    emotional_intensity: float
    emotional_valence: float

    # Self-relevance
    self_defining: bool
    centrality_to_identity: float


@dataclass
class SelfDefiningMemory:
    """
    Singer & Salovey's self-defining memory.
    """
    id: str
    narrative: str
    theme: LifeTheme
    emotional_intensity: float
    vividness: float
    linked_memories: List[str]
    life_lesson: str


@dataclass
class AutobiographicalMetrics:
    """
    Autobiographical memory metrics.
    """
    lifetime_periods: int
    general_events: int
    specific_events: int
    self_defining_memories: int
    reminiscence_bump_present: bool


# ============================================================================
# WORKING SELF
# ============================================================================

class WorkingSelf:
    """
    Conway's working self - goals and self-concept.

    "Ba'el's executive of memory." — Ba'el
    """

    def __init__(self):
        """Initialize working self."""
        self._current_goals: List[str] = []
        self._self_images: List[str] = []
        self._self_beliefs: Dict[str, float] = {}
        self._possible_selves: Dict[str, str] = {}  # future/feared

        self._lock = threading.RLock()

    def set_current_goals(
        self,
        goals: List[str]
    ) -> None:
        """Set current goals."""
        self._current_goals = goals

    def add_self_image(
        self,
        image: str
    ) -> None:
        """Add a self-image."""
        self._self_images.append(image)

    def set_self_belief(
        self,
        belief: str,
        strength: float
    ) -> None:
        """Set a self-belief."""
        self._self_beliefs[belief] = strength

    def add_possible_self(
        self,
        future_self: str,
        feared_or_hoped: str = "hoped"
    ) -> None:
        """Add a possible self."""
        self._possible_selves[future_self] = feared_or_hoped

    def is_goal_relevant(
        self,
        memory_content: str
    ) -> float:
        """Check if memory is goal-relevant."""
        # Simple keyword matching
        relevance = 0.0
        for goal in self._current_goals:
            if goal.lower() in memory_content.lower():
                relevance += 0.3

        return min(1.0, relevance)

    def is_self_consistent(
        self,
        memory_content: str
    ) -> bool:
        """Check if memory is self-consistent."""
        # Memories consistent with self-beliefs are maintained
        for image in self._self_images:
            if image.lower() in memory_content.lower():
                return True
        return False

    def filter_by_coherence(
        self,
        memories: List[SpecificEvent]
    ) -> List[SpecificEvent]:
        """Filter memories by self-coherence."""
        coherent = []
        for memory in memories:
            if self.is_self_consistent(memory.description):
                coherent.append(memory)
            elif self.is_goal_relevant(memory.description) > 0.5:
                coherent.append(memory)

        return coherent if coherent else memories


# ============================================================================
# AUTOBIOGRAPHICAL KNOWLEDGE BASE
# ============================================================================

class AutobiographicalKnowledgeBase:
    """
    Hierarchical autobiographical knowledge.

    "Ba'el's life story." — Ba'el
    """

    def __init__(self):
        """Initialize knowledge base."""
        self._lifetime_periods: Dict[str, LifetimePeriod] = {}
        self._general_events: Dict[str, GeneralEvent] = {}
        self._specific_events: Dict[str, SpecificEvent] = {}

        self._period_counter = 0
        self._event_counter = 0
        self._specific_counter = 0

        self._lock = threading.RLock()

    def _generate_period_id(self) -> str:
        self._period_counter += 1
        return f"period_{self._period_counter}"

    def _generate_event_id(self) -> str:
        self._event_counter += 1
        return f"general_{self._event_counter}"

    def _generate_specific_id(self) -> str:
        self._specific_counter += 1
        return f"specific_{self._specific_counter}"

    # Lifetime periods

    def add_lifetime_period(
        self,
        name: str,
        theme: str,
        start_age: int,
        end_age: int = None
    ) -> LifetimePeriod:
        """Add a lifetime period."""
        period = LifetimePeriod(
            id=self._generate_period_id(),
            name=name,
            theme=theme,
            start_age=start_age,
            end_age=end_age,
            general_events=[]
        )

        self._lifetime_periods[period.id] = period
        return period

    # General events

    def add_general_event(
        self,
        name: str,
        category: str,
        period_id: str,
        valence: float = 0.0
    ) -> Optional[GeneralEvent]:
        """Add a general event."""
        period = self._lifetime_periods.get(period_id)
        if not period:
            return None

        event = GeneralEvent(
            id=self._generate_event_id(),
            name=name,
            category=category,
            lifetime_period_id=period_id,
            specific_events=[],
            emotional_valence=valence
        )

        self._general_events[event.id] = event
        period.general_events.append(event.id)

        return event

    # Specific events

    def add_specific_event(
        self,
        description: str,
        general_event_id: str,
        age: int,
        sensory_details: Dict[str, str] = None,
        emotional_intensity: float = 0.5,
        emotional_valence: float = 0.0,
        self_defining: bool = False,
        centrality: float = 0.5
    ) -> Optional[SpecificEvent]:
        """Add a specific event."""
        general = self._general_events.get(general_event_id)
        if not general:
            return None

        event = SpecificEvent(
            id=self._generate_specific_id(),
            description=description,
            general_event_id=general_event_id,
            age_at_event=age,
            sensory_details=sensory_details or {},
            emotional_intensity=emotional_intensity,
            emotional_valence=emotional_valence,
            self_defining=self_defining,
            centrality_to_identity=centrality
        )

        self._specific_events[event.id] = event
        general.specific_events.append(event.id)

        return event

    # Retrieval

    def get_events_by_period(
        self,
        period_id: str
    ) -> List[GeneralEvent]:
        """Get events from a lifetime period."""
        period = self._lifetime_periods.get(period_id)
        if not period:
            return []

        return [
            self._general_events[eid]
            for eid in period.general_events
            if eid in self._general_events
        ]

    def get_events_by_age(
        self,
        min_age: int,
        max_age: int
    ) -> List[SpecificEvent]:
        """Get events in age range."""
        return [
            e for e in self._specific_events.values()
            if min_age <= e.age_at_event <= max_age
        ]

    def get_self_defining_events(self) -> List[SpecificEvent]:
        """Get self-defining events."""
        return [
            e for e in self._specific_events.values()
            if e.self_defining
        ]


# ============================================================================
# REMINISCENCE BUMP
# ============================================================================

class ReminiscenceBumpAnalyzer:
    """
    Analyze reminiscence bump effect.

    "Ba'el's peak of memory." — Ba'el
    """

    def __init__(
        self,
        bump_start: int = 10,
        bump_end: int = 30,
        bump_peak: int = 20
    ):
        """Initialize analyzer."""
        self._bump_start = bump_start
        self._bump_end = bump_end
        self._bump_peak = bump_peak

        self._lock = threading.RLock()

    def analyze_distribution(
        self,
        events: List[SpecificEvent]
    ) -> Dict[str, Any]:
        """Analyze age distribution of memories."""
        if not events:
            return {'bump_present': False}

        ages = [e.age_at_event for e in events]

        # Count by decade
        decades = defaultdict(int)
        for age in ages:
            decade = (age // 10) * 10
            decades[decade] += 1

        # Check for bump
        bump_count = sum(
            1 for age in ages
            if self._bump_start <= age <= self._bump_end
        )

        other_count = len(ages) - bump_count

        bump_proportion = bump_count / len(ages) if ages else 0

        # Bump typically contains disproportionate memories
        bump_present = bump_proportion > 0.3

        return {
            'total_memories': len(ages),
            'bump_memories': bump_count,
            'bump_proportion': bump_proportion,
            'bump_present': bump_present,
            'decade_distribution': dict(decades),
            'peak_decade': max(decades.items(), key=lambda x: x[1])[0] if decades else None
        }

    def get_bump_probability(
        self,
        age: int
    ) -> float:
        """Get probability of remembering event at this age."""
        # Gaussian-like bump
        if age < self._bump_start or age > self._bump_end:
            return 0.2 + random.uniform(-0.05, 0.05)

        # Within bump period
        distance_from_peak = abs(age - self._bump_peak)
        sigma = (self._bump_end - self._bump_start) / 4

        prob = math.exp(-(distance_from_peak ** 2) / (2 * sigma ** 2))
        return 0.2 + 0.6 * prob


# ============================================================================
# AUTOBIOGRAPHICAL MEMORY ENGINE
# ============================================================================

class AutobiographicalMemoryEngine:
    """
    Complete autobiographical memory engine.

    "Ba'el's self-memory system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._working_self = WorkingSelf()
        self._knowledge_base = AutobiographicalKnowledgeBase()
        self._bump_analyzer = ReminiscenceBumpAnalyzer()

        self._self_defining_memories: Dict[str, SelfDefiningMemory] = {}
        self._sdm_counter = 0

        self._lock = threading.RLock()

    def _generate_sdm_id(self) -> str:
        self._sdm_counter += 1
        return f"sdm_{self._sdm_counter}"

    # Working self

    def set_goals(
        self,
        goals: List[str]
    ) -> None:
        """Set current goals."""
        self._working_self.set_current_goals(goals)

    def add_self_image(
        self,
        image: str
    ) -> None:
        """Add self-image."""
        self._working_self.add_self_image(image)

    def add_possible_self(
        self,
        self_description: str,
        future_or_feared: str = "future"
    ) -> None:
        """Add possible self."""
        self._working_self.add_possible_self(self_description, future_or_feared)

    # Memory encoding

    def create_lifetime_period(
        self,
        name: str,
        theme: str,
        start_age: int,
        end_age: int = None
    ) -> LifetimePeriod:
        """Create a lifetime period."""
        return self._knowledge_base.add_lifetime_period(
            name, theme, start_age, end_age
        )

    def create_general_event(
        self,
        name: str,
        category: str,
        period_id: str,
        valence: float = 0.0
    ) -> Optional[GeneralEvent]:
        """Create a general event."""
        return self._knowledge_base.add_general_event(
            name, category, period_id, valence
        )

    def encode_specific_event(
        self,
        description: str,
        general_event_id: str,
        age: int,
        sensory_details: Dict[str, str] = None,
        emotional_intensity: float = 0.5,
        emotional_valence: float = 0.0,
        self_defining: bool = False
    ) -> Optional[SpecificEvent]:
        """Encode a specific autobiographical event."""
        # Calculate centrality
        centrality = 0.5
        if self_defining:
            centrality = 0.8
        if abs(emotional_intensity) > 0.7:
            centrality += 0.1

        return self._knowledge_base.add_specific_event(
            description=description,
            general_event_id=general_event_id,
            age=age,
            sensory_details=sensory_details,
            emotional_intensity=emotional_intensity,
            emotional_valence=emotional_valence,
            self_defining=self_defining,
            centrality=min(1.0, centrality)
        )

    # Self-defining memories

    def create_self_defining_memory(
        self,
        narrative: str,
        theme: LifeTheme,
        emotional_intensity: float,
        vividness: float,
        life_lesson: str
    ) -> SelfDefiningMemory:
        """Create a self-defining memory."""
        sdm = SelfDefiningMemory(
            id=self._generate_sdm_id(),
            narrative=narrative,
            theme=theme,
            emotional_intensity=emotional_intensity,
            vividness=vividness,
            linked_memories=[],
            life_lesson=life_lesson
        )

        self._self_defining_memories[sdm.id] = sdm
        return sdm

    def link_sdm_to_event(
        self,
        sdm_id: str,
        event_id: str
    ) -> None:
        """Link self-defining memory to specific event."""
        sdm = self._self_defining_memories.get(sdm_id)
        if sdm:
            sdm.linked_memories.append(event_id)

    # Retrieval

    def retrieve_by_cue(
        self,
        cue: str,
        top_k: int = 5
    ) -> List[SpecificEvent]:
        """Retrieve memories by cue."""
        events = list(self._knowledge_base._specific_events.values())

        # Simple relevance scoring
        scored = []
        for event in events:
            score = 0.0
            if cue.lower() in event.description.lower():
                score += 0.5
            score += event.centrality_to_identity * 0.3
            score += event.emotional_intensity * 0.2

            scored.append((score, event))

        scored.sort(reverse=True, key=lambda x: x[0])

        return [event for _, event in scored[:top_k]]

    def retrieve_by_period(
        self,
        period_id: str
    ) -> List[GeneralEvent]:
        """Retrieve general events from period."""
        return self._knowledge_base.get_events_by_period(period_id)

    def retrieve_by_age(
        self,
        age: int,
        range_years: int = 5
    ) -> List[SpecificEvent]:
        """Retrieve events around an age."""
        return self._knowledge_base.get_events_by_age(
            age - range_years, age + range_years
        )

    def get_self_defining_memories(self) -> List[SelfDefiningMemory]:
        """Get all self-defining memories."""
        return list(self._self_defining_memories.values())

    # Life narrative

    def construct_life_narrative(self) -> Dict[str, Any]:
        """Construct life narrative."""
        periods = list(self._knowledge_base._lifetime_periods.values())
        periods.sort(key=lambda p: p.start_age)

        sdms = self.get_self_defining_memories()

        # Extract themes
        themes = [sdm.theme.name for sdm in sdms]
        theme_counts = defaultdict(int)
        for theme in themes:
            theme_counts[theme] += 1

        dominant_theme = max(theme_counts.items(), key=lambda x: x[1])[0] if theme_counts else None

        return {
            'periods': [
                {
                    'name': p.name,
                    'ages': f"{p.start_age}-{p.end_age or 'present'}",
                    'theme': p.theme,
                    'events': len(p.general_events)
                }
                for p in periods
            ],
            'self_defining_memories': len(sdms),
            'dominant_theme': dominant_theme,
            'life_lessons': [sdm.life_lesson for sdm in sdms]
        }

    # Analysis

    def analyze_reminiscence_bump(self) -> Dict[str, Any]:
        """Analyze reminiscence bump."""
        events = list(self._knowledge_base._specific_events.values())
        return self._bump_analyzer.analyze_distribution(events)

    def get_identity_centrality_distribution(self) -> Dict[str, float]:
        """Get distribution of identity centrality."""
        events = list(self._knowledge_base._specific_events.values())

        high = sum(1 for e in events if e.centrality_to_identity > 0.7)
        medium = sum(1 for e in events if 0.3 < e.centrality_to_identity <= 0.7)
        low = sum(1 for e in events if e.centrality_to_identity <= 0.3)
        total = len(events)

        if total == 0:
            return {'high': 0, 'medium': 0, 'low': 0}

        return {
            'high': high / total,
            'medium': medium / total,
            'low': low / total
        }

    def get_metrics(self) -> AutobiographicalMetrics:
        """Get autobiographical memory metrics."""
        bump = self.analyze_reminiscence_bump()

        return AutobiographicalMetrics(
            lifetime_periods=len(self._knowledge_base._lifetime_periods),
            general_events=len(self._knowledge_base._general_events),
            specific_events=len(self._knowledge_base._specific_events),
            self_defining_memories=len(self._self_defining_memories),
            reminiscence_bump_present=bump.get('bump_present', False)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'lifetime_periods': len(self._knowledge_base._lifetime_periods),
            'general_events': len(self._knowledge_base._general_events),
            'specific_events': len(self._knowledge_base._specific_events),
            'self_defining_memories': len(self._self_defining_memories)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_autobiographical_memory_engine() -> AutobiographicalMemoryEngine:
    """Create autobiographical memory engine."""
    return AutobiographicalMemoryEngine()


def demonstrate_autobiographical_memory() -> Dict[str, Any]:
    """Demonstrate autobiographical memory."""
    engine = create_autobiographical_memory_engine()

    # Create life structure
    childhood = engine.create_lifetime_period("Childhood", "Family and play", 0, 12)
    adolescence = engine.create_lifetime_period("Adolescence", "Identity formation", 13, 18)
    young_adult = engine.create_lifetime_period("Young adulthood", "Career and relationships", 19, 30)

    # Add general events
    school = engine.create_general_event("School years", "education", childhood.id, 0.3)
    first_job = engine.create_general_event("First job", "career", young_adult.id, 0.5)

    # Add specific events
    if school:
        engine.encode_specific_event(
            "First day of school - meeting best friend",
            school.id, 6,
            sensory_details={"visual": "bright classroom"},
            emotional_intensity=0.7,
            emotional_valence=0.5,
            self_defining=True
        )

    # Reminiscence bump period memories
    for age in [15, 18, 20, 22, 25]:
        if first_job:
            engine.encode_specific_event(
                f"Important memory at age {age}",
                first_job.id, age,
                emotional_intensity=0.6 + random.uniform(-0.2, 0.2)
            )

    # Self-defining memory
    sdm = engine.create_self_defining_memory(
        narrative="Overcoming challenge that shaped who I am",
        theme=LifeTheme.GROWTH,
        emotional_intensity=0.9,
        vividness=0.85,
        life_lesson="Persistence pays off"
    )

    narrative = engine.construct_life_narrative()
    bump = engine.analyze_reminiscence_bump()
    metrics = engine.get_metrics()

    return {
        'periods': len(narrative['periods']),
        'self_defining_memories': narrative['self_defining_memories'],
        'dominant_theme': narrative['dominant_theme'],
        'bump_present': bump['bump_present'],
        'bump_proportion': bump.get('bump_proportion', 0),
        'interpretation': (
            f"Life narrative with {metrics.specific_events} events, "
            f"{'reminiscence bump detected' if bump['bump_present'] else 'no clear bump'}"
        )
    }


def get_autobiographical_memory_facts() -> Dict[str, str]:
    """Get facts about autobiographical memory."""
    return {
        'conway_model': 'Self-Memory System with working self and knowledge base',
        'hierarchy': 'Lifetime periods → General events → Event-specific knowledge',
        'reminiscence_bump': 'More memories from ages 10-30',
        'self_defining': 'Singer & Salovey: memories central to identity',
        'working_self': 'Current goals and self-concept filter retrieval',
        'coherence': 'Memories must fit with self-concept',
        'life_story': 'McAdams: narrative identity',
        'themes': 'Agency, communion, redemption, contamination'
    }
