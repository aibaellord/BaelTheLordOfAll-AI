#!/usr/bin/env python3
"""
BAEL - Narrative Engine
Advanced narrative reasoning and story generation.

Features:
- Story structure management
- Character modeling
- Plot development
- Theme extraction
- Narrative coherence
- Story generation
- Event sequencing
"""

import asyncio
import hashlib
import math
import random
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class NarrativeElement(Enum):
    """Elements of narrative structure."""
    EXPOSITION = "exposition"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"


class CharacterRole(Enum):
    """Character roles in narrative."""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    MENTOR = "mentor"
    ALLY = "ally"
    GUARDIAN = "guardian"
    HERALD = "herald"
    TRICKSTER = "trickster"
    SHAPESHIFTER = "shapeshifter"


class PlotType(Enum):
    """Types of plots."""
    QUEST = "quest"
    VOYAGE_AND_RETURN = "voyage_and_return"
    RAGS_TO_RICHES = "rags_to_riches"
    TRAGEDY = "tragedy"
    COMEDY = "comedy"
    REBIRTH = "rebirth"
    OVERCOMING_MONSTER = "overcoming_monster"


class ConflictType(Enum):
    """Types of conflict."""
    PERSON_VS_PERSON = "person_vs_person"
    PERSON_VS_NATURE = "person_vs_nature"
    PERSON_VS_SOCIETY = "person_vs_society"
    PERSON_VS_SELF = "person_vs_self"
    PERSON_VS_TECHNOLOGY = "person_vs_technology"
    PERSON_VS_SUPERNATURAL = "person_vs_supernatural"


class ThemeType(Enum):
    """Types of themes."""
    LOVE = "love"
    DEATH = "death"
    POWER = "power"
    REDEMPTION = "redemption"
    IDENTITY = "identity"
    FREEDOM = "freedom"
    JUSTICE = "justice"
    SURVIVAL = "survival"


class EmotionalTone(Enum):
    """Emotional tones."""
    JOYFUL = "joyful"
    MELANCHOLIC = "melancholic"
    TENSE = "tense"
    MYSTERIOUS = "mysterious"
    ROMANTIC = "romantic"
    TRAGIC = "tragic"
    HOPEFUL = "hopeful"
    DARK = "dark"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Character:
    """A narrative character."""
    character_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: CharacterRole = CharacterRole.PROTAGONIST
    traits: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    backstory: str = ""
    relationships: Dict[str, str] = field(default_factory=dict)  # character_id -> relationship


@dataclass
class StoryEvent:
    """An event in the story."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    participants: List[str] = field(default_factory=list)
    location: str = ""
    narrative_element: NarrativeElement = NarrativeElement.EXPOSITION
    emotional_tone: EmotionalTone = EmotionalTone.JOYFUL
    causes: List[str] = field(default_factory=list)  # Event IDs
    effects: List[str] = field(default_factory=list)  # Event IDs


@dataclass
class Scene:
    """A narrative scene."""
    scene_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    setting: str = ""
    events: List[str] = field(default_factory=list)
    characters_present: List[str] = field(default_factory=list)
    narrative_element: NarrativeElement = NarrativeElement.EXPOSITION


@dataclass
class Plot:
    """A story plot."""
    plot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plot_type: PlotType = PlotType.QUEST
    conflict: ConflictType = ConflictType.PERSON_VS_PERSON
    stakes: str = ""
    turning_points: List[str] = field(default_factory=list)


@dataclass
class Story:
    """A complete story."""
    story_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    plot: Optional[Plot] = None
    characters: List[str] = field(default_factory=list)
    scenes: List[str] = field(default_factory=list)
    themes: List[ThemeType] = field(default_factory=list)
    setting: str = ""


@dataclass
class NarrativeArc:
    """A character's narrative arc."""
    arc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str = ""
    initial_state: str = ""
    final_state: str = ""
    transformation: str = ""
    key_events: List[str] = field(default_factory=list)


# =============================================================================
# CHARACTER MANAGER
# =============================================================================

class CharacterManager:
    """Manage narrative characters."""

    def __init__(self):
        self._characters: Dict[str, Character] = {}

    def create_character(
        self,
        name: str,
        role: CharacterRole = CharacterRole.PROTAGONIST,
        traits: Optional[List[str]] = None,
        goals: Optional[List[str]] = None,
        backstory: str = ""
    ) -> Character:
        """Create a new character."""
        character = Character(
            name=name,
            role=role,
            traits=traits or [],
            goals=goals or [],
            backstory=backstory
        )
        self._characters[character.character_id] = character
        return character

    def get_character(self, character_id: str) -> Optional[Character]:
        """Get a character."""
        return self._characters.get(character_id)

    def get_by_role(self, role: CharacterRole) -> List[Character]:
        """Get characters by role."""
        return [c for c in self._characters.values() if c.role == role]

    def add_relationship(
        self,
        character1_id: str,
        character2_id: str,
        relationship: str
    ) -> bool:
        """Add relationship between characters."""
        c1 = self._characters.get(character1_id)
        c2 = self._characters.get(character2_id)

        if not c1 or not c2:
            return False

        c1.relationships[character2_id] = relationship
        return True

    def get_relationships(self, character_id: str) -> Dict[str, str]:
        """Get all relationships of a character."""
        character = self._characters.get(character_id)
        return character.relationships if character else {}

    def add_trait(self, character_id: str, trait: str) -> bool:
        """Add trait to character."""
        character = self._characters.get(character_id)
        if character:
            character.traits.append(trait)
            return True
        return False

    def add_goal(self, character_id: str, goal: str) -> bool:
        """Add goal to character."""
        character = self._characters.get(character_id)
        if character:
            character.goals.append(goal)
            return True
        return False


# =============================================================================
# PLOT MANAGER
# =============================================================================

class PlotManager:
    """Manage story plots."""

    def __init__(self):
        self._plots: Dict[str, Plot] = {}
        self._plot_templates: Dict[PlotType, List[str]] = {
            PlotType.QUEST: [
                "Call to adventure",
                "Departure",
                "Trials and tests",
                "Supreme ordeal",
                "Reward",
                "Return"
            ],
            PlotType.OVERCOMING_MONSTER: [
                "Monster appears",
                "Hero called",
                "Preparation",
                "Confrontation",
                "Victory"
            ],
            PlotType.RAGS_TO_RICHES: [
                "Initial poverty",
                "Discovery of potential",
                "Rising success",
                "Crisis",
                "Final triumph"
            ],
            PlotType.TRAGEDY: [
                "Protagonist's flaw introduced",
                "Rising action and hubris",
                "Catastrophic mistake",
                "Downfall",
                "Final recognition"
            ],
            PlotType.REBIRTH: [
                "Life under shadow",
                "Threat intensifies",
                "Complete darkness",
                "Redemption event",
                "New life"
            ]
        }

    def create_plot(
        self,
        plot_type: PlotType,
        conflict: ConflictType,
        stakes: str = ""
    ) -> Plot:
        """Create a plot."""
        plot = Plot(
            plot_type=plot_type,
            conflict=conflict,
            stakes=stakes,
            turning_points=self._plot_templates.get(plot_type, []).copy()
        )
        self._plots[plot.plot_id] = plot
        return plot

    def get_plot(self, plot_id: str) -> Optional[Plot]:
        """Get a plot."""
        return self._plots.get(plot_id)

    def add_turning_point(
        self,
        plot_id: str,
        turning_point: str,
        index: Optional[int] = None
    ) -> bool:
        """Add a turning point to the plot."""
        plot = self._plots.get(plot_id)
        if not plot:
            return False

        if index is not None:
            plot.turning_points.insert(index, turning_point)
        else:
            plot.turning_points.append(turning_point)

        return True

    def get_template(self, plot_type: PlotType) -> List[str]:
        """Get plot template."""
        return self._plot_templates.get(plot_type, [])


# =============================================================================
# EVENT SEQUENCER
# =============================================================================

class EventSequencer:
    """Sequence and organize story events."""

    def __init__(self):
        self._events: Dict[str, StoryEvent] = {}
        self._sequence: List[str] = []

    def create_event(
        self,
        description: str,
        participants: Optional[List[str]] = None,
        location: str = "",
        narrative_element: NarrativeElement = NarrativeElement.EXPOSITION,
        emotional_tone: EmotionalTone = EmotionalTone.JOYFUL
    ) -> StoryEvent:
        """Create an event."""
        event = StoryEvent(
            description=description,
            participants=participants or [],
            location=location,
            narrative_element=narrative_element,
            emotional_tone=emotional_tone
        )
        self._events[event.event_id] = event
        self._sequence.append(event.event_id)
        return event

    def add_causal_link(
        self,
        cause_id: str,
        effect_id: str
    ) -> bool:
        """Add causal link between events."""
        cause = self._events.get(cause_id)
        effect = self._events.get(effect_id)

        if not cause or not effect:
            return False

        cause.effects.append(effect_id)
        effect.causes.append(cause_id)
        return True

    def get_sequence(self) -> List[StoryEvent]:
        """Get events in sequence."""
        return [self._events[eid] for eid in self._sequence if eid in self._events]

    def get_by_element(
        self,
        element: NarrativeElement
    ) -> List[StoryEvent]:
        """Get events by narrative element."""
        return [
            e for e in self._events.values()
            if e.narrative_element == element
        ]

    def reorder(self, new_order: List[str]) -> bool:
        """Reorder events."""
        if set(new_order) != set(self._sequence):
            return False
        self._sequence = new_order
        return True

    def get_event(self, event_id: str) -> Optional[StoryEvent]:
        """Get an event."""
        return self._events.get(event_id)


# =============================================================================
# SCENE BUILDER
# =============================================================================

class SceneBuilder:
    """Build narrative scenes."""

    def __init__(self, event_sequencer: EventSequencer):
        self._event_sequencer = event_sequencer
        self._scenes: Dict[str, Scene] = {}

    def create_scene(
        self,
        title: str,
        setting: str,
        narrative_element: NarrativeElement = NarrativeElement.EXPOSITION
    ) -> Scene:
        """Create a scene."""
        scene = Scene(
            title=title,
            setting=setting,
            narrative_element=narrative_element
        )
        self._scenes[scene.scene_id] = scene
        return scene

    def add_event_to_scene(
        self,
        scene_id: str,
        event_id: str
    ) -> bool:
        """Add an event to a scene."""
        scene = self._scenes.get(scene_id)
        if not scene:
            return False

        scene.events.append(event_id)

        # Update characters present
        event = self._event_sequencer.get_event(event_id)
        if event:
            for participant in event.participants:
                if participant not in scene.characters_present:
                    scene.characters_present.append(participant)

        return True

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Get a scene."""
        return self._scenes.get(scene_id)

    def get_all_scenes(self) -> List[Scene]:
        """Get all scenes."""
        return list(self._scenes.values())


# =============================================================================
# THEME ANALYZER
# =============================================================================

class ThemeAnalyzer:
    """Analyze and extract themes."""

    def __init__(self):
        self._theme_keywords: Dict[ThemeType, List[str]] = {
            ThemeType.LOVE: ["love", "heart", "romance", "passion", "devotion"],
            ThemeType.DEATH: ["death", "mortality", "loss", "grief", "end"],
            ThemeType.POWER: ["power", "control", "authority", "domination", "strength"],
            ThemeType.REDEMPTION: ["redemption", "forgiveness", "salvation", "atonement"],
            ThemeType.IDENTITY: ["identity", "self", "who am I", "purpose", "belonging"],
            ThemeType.FREEDOM: ["freedom", "liberty", "escape", "independence", "choice"],
            ThemeType.JUSTICE: ["justice", "fairness", "revenge", "punishment", "right"],
            ThemeType.SURVIVAL: ["survival", "endurance", "struggle", "resilience"]
        }

    def extract_themes(
        self,
        text: str
    ) -> List[Tuple[ThemeType, float]]:
        """Extract themes from text."""
        text_lower = text.lower()
        theme_scores: Dict[ThemeType, float] = {}

        for theme, keywords in self._theme_keywords.items():
            score = sum(
                1 for keyword in keywords
                if keyword in text_lower
            )
            if score > 0:
                theme_scores[theme] = score / len(keywords)

        # Sort by score
        sorted_themes = sorted(
            theme_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_themes

    def suggest_themes(
        self,
        plot_type: PlotType
    ) -> List[ThemeType]:
        """Suggest themes based on plot type."""
        suggestions = {
            PlotType.QUEST: [ThemeType.IDENTITY, ThemeType.POWER, ThemeType.FREEDOM],
            PlotType.TRAGEDY: [ThemeType.DEATH, ThemeType.POWER, ThemeType.REDEMPTION],
            PlotType.REBIRTH: [ThemeType.REDEMPTION, ThemeType.IDENTITY, ThemeType.LOVE],
            PlotType.RAGS_TO_RICHES: [ThemeType.POWER, ThemeType.IDENTITY, ThemeType.JUSTICE],
            PlotType.OVERCOMING_MONSTER: [ThemeType.SURVIVAL, ThemeType.JUSTICE, ThemeType.POWER]
        }
        return suggestions.get(plot_type, [ThemeType.IDENTITY])


# =============================================================================
# STORY GENERATOR
# =============================================================================

class StoryGenerator:
    """Generate story content."""

    def __init__(
        self,
        character_manager: CharacterManager,
        plot_manager: PlotManager,
        event_sequencer: EventSequencer
    ):
        self._characters = character_manager
        self._plots = plot_manager
        self._events = event_sequencer

    def generate_story_outline(
        self,
        plot_type: PlotType,
        protagonist_name: str,
        antagonist_name: str = "Unknown Antagonist"
    ) -> Dict[str, Any]:
        """Generate a basic story outline."""
        # Create characters
        protagonist = self._characters.create_character(
            protagonist_name,
            CharacterRole.PROTAGONIST,
            traits=["brave", "determined"],
            goals=["overcome challenge"]
        )

        antagonist = self._characters.create_character(
            antagonist_name,
            CharacterRole.ANTAGONIST,
            traits=["cunning", "powerful"],
            goals=["oppose protagonist"]
        )

        # Create plot
        plot = self._plots.create_plot(
            plot_type,
            ConflictType.PERSON_VS_PERSON,
            stakes="The fate of the world"
        )

        # Generate events for each turning point
        events = []
        elements = [
            NarrativeElement.EXPOSITION,
            NarrativeElement.RISING_ACTION,
            NarrativeElement.CLIMAX,
            NarrativeElement.FALLING_ACTION,
            NarrativeElement.RESOLUTION
        ]

        for i, turning_point in enumerate(plot.turning_points[:5]):
            element = elements[min(i, len(elements) - 1)]
            event = self._events.create_event(
                turning_point,
                participants=[protagonist.character_id],
                narrative_element=element
            )
            events.append(event)

        return {
            "protagonist": protagonist,
            "antagonist": antagonist,
            "plot": plot,
            "events": events
        }

    def generate_scene_description(
        self,
        scene: Scene,
        characters: List[Character]
    ) -> str:
        """Generate a scene description."""
        char_names = [c.name for c in characters]

        description = f"Scene: {scene.title}\n"
        description += f"Setting: {scene.setting}\n"
        description += f"Characters: {', '.join(char_names)}\n"
        description += f"Narrative element: {scene.narrative_element.value}\n"

        return description


# =============================================================================
# COHERENCE CHECKER
# =============================================================================

class CoherenceChecker:
    """Check narrative coherence."""

    def __init__(
        self,
        event_sequencer: EventSequencer,
        character_manager: CharacterManager
    ):
        self._events = event_sequencer
        self._characters = character_manager

    def check_causal_coherence(self) -> List[str]:
        """Check if causal links are coherent."""
        issues = []

        for event in self._events.get_sequence():
            for cause_id in event.causes:
                cause = self._events.get_event(cause_id)
                if not cause:
                    issues.append(
                        f"Event '{event.description[:30]}...' references "
                        f"non-existent cause"
                    )

        return issues

    def check_character_coherence(self) -> List[str]:
        """Check character coherence."""
        issues = []

        for event in self._events.get_sequence():
            for participant_id in event.participants:
                if not self._characters.get_character(participant_id):
                    issues.append(
                        f"Event '{event.description[:30]}...' references "
                        f"unknown character"
                    )

        return issues

    def check_narrative_structure(self) -> List[str]:
        """Check narrative structure coherence."""
        issues = []
        events = self._events.get_sequence()

        if not events:
            issues.append("No events in story")
            return issues

        # Check for exposition at start
        if events[0].narrative_element != NarrativeElement.EXPOSITION:
            issues.append("Story should start with exposition")

        # Check for climax
        has_climax = any(
            e.narrative_element == NarrativeElement.CLIMAX
            for e in events
        )
        if not has_climax:
            issues.append("Story lacks a climax")

        # Check for resolution at end
        if events[-1].narrative_element != NarrativeElement.RESOLUTION:
            issues.append("Story should end with resolution")

        return issues

    def get_coherence_score(self) -> float:
        """Calculate overall coherence score."""
        issues = []
        issues.extend(self.check_causal_coherence())
        issues.extend(self.check_character_coherence())
        issues.extend(self.check_narrative_structure())

        max_issues = 10
        score = max(0.0, 1.0 - (len(issues) / max_issues))
        return score


# =============================================================================
# NARRATIVE ENGINE
# =============================================================================

class NarrativeEngine:
    """
    Narrative Engine for BAEL.

    Advanced narrative reasoning and story generation.
    """

    def __init__(self):
        self._character_manager = CharacterManager()
        self._plot_manager = PlotManager()
        self._event_sequencer = EventSequencer()
        self._scene_builder = SceneBuilder(self._event_sequencer)
        self._theme_analyzer = ThemeAnalyzer()
        self._story_generator = StoryGenerator(
            self._character_manager,
            self._plot_manager,
            self._event_sequencer
        )
        self._coherence_checker = CoherenceChecker(
            self._event_sequencer,
            self._character_manager
        )

        self._stories: Dict[str, Story] = {}

    # -------------------------------------------------------------------------
    # CHARACTER OPERATIONS
    # -------------------------------------------------------------------------

    def create_character(
        self,
        name: str,
        role: CharacterRole = CharacterRole.PROTAGONIST,
        traits: Optional[List[str]] = None,
        goals: Optional[List[str]] = None,
        backstory: str = ""
    ) -> Character:
        """Create a character."""
        return self._character_manager.create_character(
            name, role, traits, goals, backstory
        )

    def get_character(self, character_id: str) -> Optional[Character]:
        """Get a character."""
        return self._character_manager.get_character(character_id)

    def add_relationship(
        self,
        character1_id: str,
        character2_id: str,
        relationship: str
    ) -> bool:
        """Add relationship between characters."""
        return self._character_manager.add_relationship(
            character1_id, character2_id, relationship
        )

    # -------------------------------------------------------------------------
    # PLOT OPERATIONS
    # -------------------------------------------------------------------------

    def create_plot(
        self,
        plot_type: PlotType,
        conflict: ConflictType,
        stakes: str = ""
    ) -> Plot:
        """Create a plot."""
        return self._plot_manager.create_plot(plot_type, conflict, stakes)

    def get_plot_template(self, plot_type: PlotType) -> List[str]:
        """Get plot template."""
        return self._plot_manager.get_template(plot_type)

    # -------------------------------------------------------------------------
    # EVENT OPERATIONS
    # -------------------------------------------------------------------------

    def create_event(
        self,
        description: str,
        participants: Optional[List[str]] = None,
        location: str = "",
        narrative_element: NarrativeElement = NarrativeElement.EXPOSITION,
        emotional_tone: EmotionalTone = EmotionalTone.JOYFUL
    ) -> StoryEvent:
        """Create a story event."""
        return self._event_sequencer.create_event(
            description, participants, location, narrative_element, emotional_tone
        )

    def link_events(
        self,
        cause_id: str,
        effect_id: str
    ) -> bool:
        """Add causal link between events."""
        return self._event_sequencer.add_causal_link(cause_id, effect_id)

    def get_event_sequence(self) -> List[StoryEvent]:
        """Get events in sequence."""
        return self._event_sequencer.get_sequence()

    # -------------------------------------------------------------------------
    # SCENE OPERATIONS
    # -------------------------------------------------------------------------

    def create_scene(
        self,
        title: str,
        setting: str,
        narrative_element: NarrativeElement = NarrativeElement.EXPOSITION
    ) -> Scene:
        """Create a scene."""
        return self._scene_builder.create_scene(title, setting, narrative_element)

    def add_event_to_scene(
        self,
        scene_id: str,
        event_id: str
    ) -> bool:
        """Add event to scene."""
        return self._scene_builder.add_event_to_scene(scene_id, event_id)

    # -------------------------------------------------------------------------
    # STORY OPERATIONS
    # -------------------------------------------------------------------------

    def create_story(
        self,
        title: str,
        plot: Plot,
        themes: Optional[List[ThemeType]] = None,
        setting: str = ""
    ) -> Story:
        """Create a story."""
        story = Story(
            title=title,
            plot=plot,
            themes=themes or [],
            setting=setting
        )
        self._stories[story.story_id] = story
        return story

    def generate_story_outline(
        self,
        plot_type: PlotType,
        protagonist_name: str,
        antagonist_name: str = "Unknown Antagonist"
    ) -> Dict[str, Any]:
        """Generate a story outline."""
        return self._story_generator.generate_story_outline(
            plot_type, protagonist_name, antagonist_name
        )

    # -------------------------------------------------------------------------
    # THEME ANALYSIS
    # -------------------------------------------------------------------------

    def extract_themes(self, text: str) -> List[Tuple[ThemeType, float]]:
        """Extract themes from text."""
        return self._theme_analyzer.extract_themes(text)

    def suggest_themes(self, plot_type: PlotType) -> List[ThemeType]:
        """Suggest themes for plot type."""
        return self._theme_analyzer.suggest_themes(plot_type)

    # -------------------------------------------------------------------------
    # COHERENCE
    # -------------------------------------------------------------------------

    def check_coherence(self) -> Dict[str, Any]:
        """Check story coherence."""
        causal = self._coherence_checker.check_causal_coherence()
        character = self._coherence_checker.check_character_coherence()
        structure = self._coherence_checker.check_narrative_structure()
        score = self._coherence_checker.get_coherence_score()

        return {
            "causal_issues": causal,
            "character_issues": character,
            "structure_issues": structure,
            "score": score
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Narrative Engine."""
    print("=" * 70)
    print("BAEL - NARRATIVE ENGINE DEMO")
    print("Advanced Narrative Reasoning and Story Generation")
    print("=" * 70)
    print()

    engine = NarrativeEngine()

    # 1. Create Characters
    print("1. CREATE CHARACTERS:")
    print("-" * 40)

    hero = engine.create_character(
        "Elena",
        CharacterRole.PROTAGONIST,
        traits=["brave", "curious", "kind"],
        goals=["save her kingdom", "discover her powers"],
        backstory="A young princess who discovers she has magical abilities"
    )

    villain = engine.create_character(
        "Lord Malachar",
        CharacterRole.ANTAGONIST,
        traits=["cunning", "powerful", "ruthless"],
        goals=["conquer the realm", "obtain ultimate power"]
    )

    mentor = engine.create_character(
        "Sage Aldric",
        CharacterRole.MENTOR,
        traits=["wise", "patient", "mysterious"],
        goals=["guide Elena", "protect ancient secrets"]
    )

    print(f"   Hero: {hero.name} ({hero.role.value})")
    print(f"   Villain: {villain.name} ({villain.role.value})")
    print(f"   Mentor: {mentor.name} ({mentor.role.value})")
    print()

    # 2. Add Relationships
    print("2. CHARACTER RELATIONSHIPS:")
    print("-" * 40)

    engine.add_relationship(hero.character_id, villain.character_id, "nemesis")
    engine.add_relationship(hero.character_id, mentor.character_id, "student")
    engine.add_relationship(mentor.character_id, villain.character_id, "former ally")

    print("   Elena <-> Lord Malachar: nemesis")
    print("   Elena <-> Sage Aldric: student")
    print("   Sage Aldric <-> Lord Malachar: former ally")
    print()

    # 3. Create Plot
    print("3. CREATE PLOT:")
    print("-" * 40)

    plot = engine.create_plot(
        PlotType.QUEST,
        ConflictType.PERSON_VS_PERSON,
        stakes="The fate of the entire kingdom"
    )

    print(f"   Plot type: {plot.plot_type.value}")
    print(f"   Conflict: {plot.conflict.value}")
    print(f"   Stakes: {plot.stakes}")
    print(f"   Turning points: {plot.turning_points}")
    print()

    # 4. Create Events
    print("4. CREATE STORY EVENTS:")
    print("-" * 40)

    e1 = engine.create_event(
        "Elena discovers her magical powers during a festival",
        participants=[hero.character_id],
        location="Royal Palace",
        narrative_element=NarrativeElement.EXPOSITION,
        emotional_tone=EmotionalTone.MYSTERIOUS
    )

    e2 = engine.create_event(
        "Sage Aldric appears and offers to train Elena",
        participants=[hero.character_id, mentor.character_id],
        location="Palace Gardens",
        narrative_element=NarrativeElement.RISING_ACTION,
        emotional_tone=EmotionalTone.HOPEFUL
    )

    e3 = engine.create_event(
        "Lord Malachar attacks the kingdom",
        participants=[villain.character_id],
        location="Kingdom Border",
        narrative_element=NarrativeElement.RISING_ACTION,
        emotional_tone=EmotionalTone.TENSE
    )

    e4 = engine.create_event(
        "Elena confronts Lord Malachar in final battle",
        participants=[hero.character_id, villain.character_id],
        location="Dark Tower",
        narrative_element=NarrativeElement.CLIMAX,
        emotional_tone=EmotionalTone.TENSE
    )

    e5 = engine.create_event(
        "Elena defeats Malachar and saves the kingdom",
        participants=[hero.character_id, villain.character_id],
        location="Dark Tower",
        narrative_element=NarrativeElement.RESOLUTION,
        emotional_tone=EmotionalTone.JOYFUL
    )

    # Link events
    engine.link_events(e1.event_id, e2.event_id)
    engine.link_events(e2.event_id, e3.event_id)
    engine.link_events(e3.event_id, e4.event_id)
    engine.link_events(e4.event_id, e5.event_id)

    for event in [e1, e2, e3, e4, e5]:
        print(f"   [{event.narrative_element.value}] {event.description[:50]}...")
    print()

    # 5. Create Scenes
    print("5. CREATE SCENES:")
    print("-" * 40)

    scene1 = engine.create_scene(
        "The Discovery",
        "Royal Palace during the Summer Festival",
        NarrativeElement.EXPOSITION
    )
    engine.add_event_to_scene(scene1.scene_id, e1.event_id)
    engine.add_event_to_scene(scene1.scene_id, e2.event_id)

    scene2 = engine.create_scene(
        "The Confrontation",
        "Lord Malachar's Dark Tower",
        NarrativeElement.CLIMAX
    )
    engine.add_event_to_scene(scene2.scene_id, e4.event_id)
    engine.add_event_to_scene(scene2.scene_id, e5.event_id)

    print(f"   Scene: {scene1.title} ({len(scene1.events)} events)")
    print(f"   Scene: {scene2.title} ({len(scene2.events)} events)")
    print()

    # 6. Theme Analysis
    print("6. THEME ANALYSIS:")
    print("-" * 40)

    story_text = """
    Elena's journey is about discovering her true identity and finding
    the power within herself. She must fight for freedom against tyranny
    and prove that love and justice will always triumph over darkness.
    """

    themes = engine.extract_themes(story_text)
    print("   Extracted themes:")
    for theme, score in themes[:3]:
        print(f"     - {theme.value}: {score:.2f}")

    suggested = engine.suggest_themes(PlotType.QUEST)
    print(f"   Suggested for Quest: {[t.value for t in suggested]}")
    print()

    # 7. Coherence Check
    print("7. COHERENCE CHECK:")
    print("-" * 40)

    coherence = engine.check_coherence()
    print(f"   Coherence score: {coherence['score']:.2f}")
    print(f"   Causal issues: {len(coherence['causal_issues'])}")
    print(f"   Character issues: {len(coherence['character_issues'])}")
    print(f"   Structure issues: {len(coherence['structure_issues'])}")

    for issue in coherence['structure_issues']:
        print(f"     - {issue}")
    print()

    # 8. Generate Story Outline
    print("8. AUTO-GENERATE STORY OUTLINE:")
    print("-" * 40)

    outline = engine.generate_story_outline(
        PlotType.OVERCOMING_MONSTER,
        "Sir Marcus",
        "The Dragon"
    )

    print(f"   Protagonist: {outline['protagonist'].name}")
    print(f"   Antagonist: {outline['antagonist'].name}")
    print(f"   Plot: {outline['plot'].plot_type.value}")
    print(f"   Events: {len(outline['events'])}")
    print()

    # 9. Plot Templates
    print("9. PLOT TEMPLATES:")
    print("-" * 40)

    for plot_type in [PlotType.TRAGEDY, PlotType.REBIRTH]:
        template = engine.get_plot_template(plot_type)
        print(f"   {plot_type.value}: {template[:3]}...")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Narrative Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
