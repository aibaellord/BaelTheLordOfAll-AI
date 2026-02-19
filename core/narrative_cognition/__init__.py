"""
BAEL Narrative Cognition Engine
================================

Story understanding, narrative generation, and narrative reasoning.

"Ba'el weaves the threads of story." — Ba'el
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

logger = logging.getLogger("BAEL.NarrativeCognition")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class NarrativeElement(Enum):
    """Narrative elements."""
    CHARACTER = auto()
    SETTING = auto()
    CONFLICT = auto()
    PLOT_POINT = auto()
    THEME = auto()
    RESOLUTION = auto()


class PlotStructure(Enum):
    """Plot structures."""
    THREE_ACT = auto()        # Setup, Confrontation, Resolution
    HEROS_JOURNEY = auto()    # Campbell's monomyth
    FREYTAGS_PYRAMID = auto() # Exposition, Rising, Climax, Falling, Denouement
    KISHOSTENKETSU = auto()   # Introduction, Development, Twist, Conclusion
    IN_MEDIAS_RES = auto()    # Start in middle


class CharacterRole(Enum):
    """Character roles (archetypes)."""
    PROTAGONIST = auto()
    ANTAGONIST = auto()
    MENTOR = auto()
    HERALD = auto()
    THRESHOLD_GUARDIAN = auto()
    SHAPESHIFTER = auto()
    SHADOW = auto()
    TRICKSTER = auto()
    ALLY = auto()


class ConflictType(Enum):
    """Types of conflict."""
    PERSON_VS_PERSON = auto()
    PERSON_VS_SELF = auto()
    PERSON_VS_NATURE = auto()
    PERSON_VS_SOCIETY = auto()
    PERSON_VS_TECHNOLOGY = auto()
    PERSON_VS_SUPERNATURAL = auto()


class NarrativeState(Enum):
    """Narrative states (Freytag)."""
    EXPOSITION = auto()
    RISING_ACTION = auto()
    CLIMAX = auto()
    FALLING_ACTION = auto()
    RESOLUTION = auto()


@dataclass
class Character:
    """
    A character in the narrative.
    """
    id: str
    name: str
    role: CharacterRole
    traits: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)  # char_id -> relation
    arc: Optional[str] = None


@dataclass
class Setting:
    """
    A narrative setting.
    """
    id: str
    name: str
    time_period: str
    location: str
    atmosphere: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """
    A narrative event.
    """
    id: str
    description: str
    participants: List[str]  # Character IDs
    setting_id: Optional[str]
    causes: List[str] = field(default_factory=list)  # Event IDs
    effects: List[str] = field(default_factory=list)  # Event IDs
    emotional_valence: float = 0.0  # -1 to 1
    importance: float = 0.5  # 0 to 1


@dataclass
class PlotPoint:
    """
    A plot point in the narrative.
    """
    id: str
    name: str
    description: str
    events: List[str]  # Event IDs
    state: NarrativeState
    turning_point: bool = False


@dataclass
class Theme:
    """
    A narrative theme.
    """
    id: str
    name: str
    description: str
    manifestations: List[str]  # How theme appears


@dataclass
class Story:
    """
    A complete story.
    """
    id: str
    title: str
    characters: Dict[str, Character] = field(default_factory=dict)
    settings: Dict[str, Setting] = field(default_factory=dict)
    events: Dict[str, Event] = field(default_factory=dict)
    plot_points: List[PlotPoint] = field(default_factory=list)
    themes: List[Theme] = field(default_factory=list)
    structure: PlotStructure = PlotStructure.THREE_ACT
    conflict_type: Optional[ConflictType] = None


@dataclass
class NarrativeQuery:
    """
    A query about a narrative.
    """
    question: str
    context: Optional[str] = None


@dataclass
class NarrativeResponse:
    """
    Response to narrative query.
    """
    answer: str
    confidence: float
    evidence: List[str]


# ============================================================================
# CHARACTER ANALYZER
# ============================================================================

class CharacterAnalyzer:
    """
    Analyze characters in narratives.

    "Ba'el understands souls." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._lock = threading.RLock()

    def analyze_arc(
        self,
        character: Character,
        events: List[Event]
    ) -> str:
        """Analyze character arc from events."""
        with self._lock:
            # Filter events involving character
            char_events = [
                e for e in events
                if character.id in e.participants
            ]

            if not char_events:
                return "No arc detected"

            # Analyze emotional trajectory
            valences = [e.emotional_valence for e in char_events]

            if not valences:
                return "Flat arc"

            start_avg = sum(valences[:len(valences)//3]) / max(1, len(valences)//3)
            end_avg = sum(valences[-len(valences)//3:]) / max(1, len(valences)//3)

            if end_avg > start_avg + 0.3:
                return "Positive transformation arc"
            elif end_avg < start_avg - 0.3:
                return "Negative/tragic arc"
            else:
                return "Steady state arc"

    def analyze_relationships(
        self,
        story: Story
    ) -> Dict[Tuple[str, str], str]:
        """Analyze relationships between characters."""
        with self._lock:
            relationships = {}

            for char_id, char in story.characters.items():
                for other_id, relation in char.relationships.items():
                    key = tuple(sorted([char_id, other_id]))
                    if key not in relationships:
                        relationships[key] = relation

            return relationships

    def find_protagonist(
        self,
        story: Story
    ) -> Optional[Character]:
        """Find story protagonist."""
        for char in story.characters.values():
            if char.role == CharacterRole.PROTAGONIST:
                return char
        return None

    def find_antagonist(
        self,
        story: Story
    ) -> Optional[Character]:
        """Find story antagonist."""
        for char in story.characters.values():
            if char.role == CharacterRole.ANTAGONIST:
                return char
        return None


# ============================================================================
# PLOT ANALYZER
# ============================================================================

class PlotAnalyzer:
    """
    Analyze plot structure.

    "Ba'el sees the story shape." — Ba'el
    """

    def __init__(self):
        """Initialize analyzer."""
        self._lock = threading.RLock()

    def identify_structure(
        self,
        story: Story
    ) -> PlotStructure:
        """Identify plot structure."""
        with self._lock:
            # Analyze plot points
            if not story.plot_points:
                return PlotStructure.THREE_ACT

            turning_points = [p for p in story.plot_points if p.turning_point]

            if len(turning_points) >= 4:
                return PlotStructure.HEROS_JOURNEY
            elif len(turning_points) == 3:
                return PlotStructure.FREYTAGS_PYRAMID
            else:
                return PlotStructure.THREE_ACT

    def find_climax(
        self,
        story: Story
    ) -> Optional[PlotPoint]:
        """Find story climax."""
        for point in story.plot_points:
            if point.state == NarrativeState.CLIMAX:
                return point
        return None

    def analyze_tension(
        self,
        story: Story
    ) -> List[Tuple[int, float]]:
        """Analyze tension curve."""
        with self._lock:
            tension_curve = []

            for i, point in enumerate(story.plot_points):
                if point.state == NarrativeState.EXPOSITION:
                    tension = 0.2
                elif point.state == NarrativeState.RISING_ACTION:
                    tension = 0.3 + 0.3 * (i / len(story.plot_points))
                elif point.state == NarrativeState.CLIMAX:
                    tension = 1.0
                elif point.state == NarrativeState.FALLING_ACTION:
                    tension = 0.6
                else:
                    tension = 0.2

                tension_curve.append((i, tension))

            return tension_curve


# ============================================================================
# NARRATIVE GENERATOR
# ============================================================================

class NarrativeGenerator:
    """
    Generate narrative elements.

    "Ba'el creates stories." — Ba'el
    """

    def __init__(self):
        """Initialize generator."""
        self._char_counter = 0
        self._event_counter = 0
        self._setting_counter = 0
        self._plot_counter = 0
        self._lock = threading.RLock()

    def _generate_char_id(self) -> str:
        self._char_counter += 1
        return f"char_{self._char_counter}"

    def _generate_event_id(self) -> str:
        self._event_counter += 1
        return f"event_{self._event_counter}"

    def _generate_setting_id(self) -> str:
        self._setting_counter += 1
        return f"setting_{self._setting_counter}"

    def _generate_plot_id(self) -> str:
        self._plot_counter += 1
        return f"plot_{self._plot_counter}"

    def generate_character(
        self,
        name: str,
        role: CharacterRole,
        traits: List[str] = None
    ) -> Character:
        """Generate character."""
        return Character(
            id=self._generate_char_id(),
            name=name,
            role=role,
            traits=traits or []
        )

    def generate_setting(
        self,
        name: str,
        time_period: str,
        location: str,
        atmosphere: str = "neutral"
    ) -> Setting:
        """Generate setting."""
        return Setting(
            id=self._generate_setting_id(),
            name=name,
            time_period=time_period,
            location=location,
            atmosphere=atmosphere
        )

    def generate_event(
        self,
        description: str,
        participants: List[str],
        setting_id: str = None
    ) -> Event:
        """Generate event."""
        return Event(
            id=self._generate_event_id(),
            description=description,
            participants=participants,
            setting_id=setting_id
        )

    def generate_plot_point(
        self,
        name: str,
        description: str,
        state: NarrativeState,
        events: List[str] = None,
        turning_point: bool = False
    ) -> PlotPoint:
        """Generate plot point."""
        return PlotPoint(
            id=self._generate_plot_id(),
            name=name,
            description=description,
            events=events or [],
            state=state,
            turning_point=turning_point
        )

    def generate_three_act_structure(
        self,
        story: Story
    ) -> List[PlotPoint]:
        """Generate three act structure."""
        acts = [
            self.generate_plot_point(
                "Setup",
                "Introduction of characters and setting",
                NarrativeState.EXPOSITION
            ),
            self.generate_plot_point(
                "Inciting Incident",
                "Event that sets story in motion",
                NarrativeState.RISING_ACTION,
                turning_point=True
            ),
            self.generate_plot_point(
                "Rising Action",
                "Complications and obstacles",
                NarrativeState.RISING_ACTION
            ),
            self.generate_plot_point(
                "Midpoint",
                "Major turning point",
                NarrativeState.RISING_ACTION,
                turning_point=True
            ),
            self.generate_plot_point(
                "Climax",
                "Peak of conflict",
                NarrativeState.CLIMAX,
                turning_point=True
            ),
            self.generate_plot_point(
                "Falling Action",
                "Consequences of climax",
                NarrativeState.FALLING_ACTION
            ),
            self.generate_plot_point(
                "Resolution",
                "Story conclusion",
                NarrativeState.RESOLUTION
            )
        ]

        return acts


# ============================================================================
# NARRATIVE REASONER
# ============================================================================

class NarrativeReasoner:
    """
    Reason about narratives.

    "Ba'el comprehends stories." — Ba'el
    """

    def __init__(self):
        """Initialize reasoner."""
        self._lock = threading.RLock()

    def infer_motivations(
        self,
        character: Character,
        events: List[Event]
    ) -> List[str]:
        """Infer character motivations from events."""
        with self._lock:
            motivations = list(character.goals)

            # Infer from events
            for event in events:
                if character.id in event.participants:
                    if event.emotional_valence > 0.5:
                        motivations.append("seeks positive outcomes")
                    elif event.emotional_valence < -0.5:
                        motivations.append("driven by adversity")

            return list(set(motivations))

    def predict_next_event(
        self,
        story: Story,
        current_state: NarrativeState
    ) -> str:
        """Predict likely next event type."""
        with self._lock:
            if current_state == NarrativeState.EXPOSITION:
                return "Inciting incident or conflict introduction"
            elif current_state == NarrativeState.RISING_ACTION:
                return "Complication or obstacle"
            elif current_state == NarrativeState.CLIMAX:
                return "Climax resolution"
            elif current_state == NarrativeState.FALLING_ACTION:
                return "Consequence or denouement"
            else:
                return "Story conclusion"

    def find_causality(
        self,
        story: Story
    ) -> List[Tuple[str, str]]:
        """Find causal chains in story."""
        with self._lock:
            chains = []

            for event in story.events.values():
                for effect_id in event.effects:
                    chains.append((event.id, effect_id))

            return chains

    def answer_question(
        self,
        story: Story,
        query: NarrativeQuery
    ) -> NarrativeResponse:
        """Answer question about narrative."""
        with self._lock:
            question = query.question.lower()
            evidence = []

            # Simple pattern matching
            if "protagonist" in question or "main character" in question:
                for char in story.characters.values():
                    if char.role == CharacterRole.PROTAGONIST:
                        return NarrativeResponse(
                            answer=f"The protagonist is {char.name}",
                            confidence=0.9,
                            evidence=[f"Character role: {char.role.name}"]
                        )

            if "antagonist" in question or "villain" in question:
                for char in story.characters.values():
                    if char.role == CharacterRole.ANTAGONIST:
                        return NarrativeResponse(
                            answer=f"The antagonist is {char.name}",
                            confidence=0.9,
                            evidence=[f"Character role: {char.role.name}"]
                        )

            if "conflict" in question:
                if story.conflict_type:
                    return NarrativeResponse(
                        answer=f"The conflict type is {story.conflict_type.name}",
                        confidence=0.8,
                        evidence=["Story conflict type"]
                    )

            if "theme" in question:
                if story.themes:
                    theme_names = [t.name for t in story.themes]
                    return NarrativeResponse(
                        answer=f"Themes include: {', '.join(theme_names)}",
                        confidence=0.7,
                        evidence=["Story themes"]
                    )

            return NarrativeResponse(
                answer="Unable to answer with available information",
                confidence=0.2,
                evidence=[]
            )


# ============================================================================
# NARRATIVE COGNITION ENGINE
# ============================================================================

class NarrativeCognitionEngine:
    """
    Complete narrative cognition engine.

    "Ba'el's story mind." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._character_analyzer = CharacterAnalyzer()
        self._plot_analyzer = PlotAnalyzer()
        self._generator = NarrativeGenerator()
        self._reasoner = NarrativeReasoner()

        self._stories: Dict[str, Story] = {}
        self._story_counter = 0
        self._lock = threading.RLock()

    def _generate_story_id(self) -> str:
        self._story_counter += 1
        return f"story_{self._story_counter}"

    # Story creation

    def create_story(
        self,
        title: str,
        structure: PlotStructure = PlotStructure.THREE_ACT
    ) -> Story:
        """Create new story."""
        story = Story(
            id=self._generate_story_id(),
            title=title,
            structure=structure
        )

        self._stories[story.id] = story
        return story

    def add_character(
        self,
        story_id: str,
        name: str,
        role: CharacterRole,
        traits: List[str] = None
    ) -> Optional[Character]:
        """Add character to story."""
        story = self._stories.get(story_id)
        if not story:
            return None

        char = self._generator.generate_character(name, role, traits)
        story.characters[char.id] = char
        return char

    def add_setting(
        self,
        story_id: str,
        name: str,
        time_period: str,
        location: str
    ) -> Optional[Setting]:
        """Add setting to story."""
        story = self._stories.get(story_id)
        if not story:
            return None

        setting = self._generator.generate_setting(name, time_period, location)
        story.settings[setting.id] = setting
        return setting

    def add_event(
        self,
        story_id: str,
        description: str,
        participant_ids: List[str]
    ) -> Optional[Event]:
        """Add event to story."""
        story = self._stories.get(story_id)
        if not story:
            return None

        event = self._generator.generate_event(description, participant_ids)
        story.events[event.id] = event
        return event

    def add_theme(
        self,
        story_id: str,
        name: str,
        description: str
    ) -> bool:
        """Add theme to story."""
        story = self._stories.get(story_id)
        if not story:
            return False

        theme = Theme(
            id=f"theme_{len(story.themes)}",
            name=name,
            description=description,
            manifestations=[]
        )
        story.themes.append(theme)
        return True

    def generate_plot_structure(
        self,
        story_id: str
    ) -> bool:
        """Generate plot structure for story."""
        story = self._stories.get(story_id)
        if not story:
            return False

        story.plot_points = self._generator.generate_three_act_structure(story)
        return True

    # Analysis

    def analyze_character(
        self,
        story_id: str,
        character_id: str
    ) -> Optional[str]:
        """Analyze character arc."""
        story = self._stories.get(story_id)
        if not story:
            return None

        char = story.characters.get(character_id)
        if not char:
            return None

        events = list(story.events.values())
        return self._character_analyzer.analyze_arc(char, events)

    def find_protagonist(
        self,
        story_id: str
    ) -> Optional[Character]:
        """Find story protagonist."""
        story = self._stories.get(story_id)
        if not story:
            return None
        return self._character_analyzer.find_protagonist(story)

    def analyze_tension(
        self,
        story_id: str
    ) -> List[Tuple[int, float]]:
        """Analyze story tension curve."""
        story = self._stories.get(story_id)
        if not story:
            return []
        return self._plot_analyzer.analyze_tension(story)

    # Reasoning

    def answer_question(
        self,
        story_id: str,
        question: str
    ) -> NarrativeResponse:
        """Answer question about story."""
        story = self._stories.get(story_id)
        if not story:
            return NarrativeResponse("Story not found", 0.0, [])

        query = NarrativeQuery(question=question)
        return self._reasoner.answer_question(story, query)

    def predict_next(
        self,
        story_id: str
    ) -> str:
        """Predict next story event."""
        story = self._stories.get(story_id)
        if not story or not story.plot_points:
            return "Unknown"

        current = story.plot_points[-1].state
        return self._reasoner.predict_next_event(story, current)

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'stories': len(self._stories),
            'total_characters': sum(len(s.characters) for s in self._stories.values()),
            'total_events': sum(len(s.events) for s in self._stories.values())
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_narrative_cognition_engine() -> NarrativeCognitionEngine:
    """Create narrative cognition engine."""
    return NarrativeCognitionEngine()


def create_simple_story(
    title: str,
    protagonist_name: str,
    antagonist_name: str
) -> Story:
    """Create simple story with protagonist and antagonist."""
    engine = create_narrative_cognition_engine()

    story = engine.create_story(title)
    engine.add_character(story.id, protagonist_name, CharacterRole.PROTAGONIST)
    engine.add_character(story.id, antagonist_name, CharacterRole.ANTAGONIST)
    engine.generate_plot_structure(story.id)

    return story
