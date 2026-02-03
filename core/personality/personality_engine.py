#!/usr/bin/env python3
"""
BAEL - Personality Engine
Advanced personality modeling and behavioral simulation.

Features:
- Personality traits (Big Five)
- Behavioral tendencies
- Communication styles
- Mood influence
- Personality adaptation
- Social dynamics
- Response modulation
- Character consistency
"""

import asyncio
import copy
import hashlib
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class PersonalityTrait(Enum):
    """Big Five personality traits."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class TraitFacet(Enum):
    """Trait facets."""
    # Openness facets
    IMAGINATION = "imagination"
    ARTISTIC_INTEREST = "artistic_interest"
    EMOTIONALITY = "emotionality"
    ADVENTUROUSNESS = "adventurousness"
    INTELLECT = "intellect"
    LIBERALISM = "liberalism"
    # Conscientiousness facets
    SELF_EFFICACY = "self_efficacy"
    ORDERLINESS = "orderliness"
    DUTIFULNESS = "dutifulness"
    ACHIEVEMENT = "achievement"
    SELF_DISCIPLINE = "self_discipline"
    CAUTIOUSNESS = "cautiousness"
    # Extraversion facets
    FRIENDLINESS = "friendliness"
    GREGARIOUSNESS = "gregariousness"
    ASSERTIVENESS = "assertiveness"
    ACTIVITY_LEVEL = "activity_level"
    EXCITEMENT_SEEKING = "excitement_seeking"
    CHEERFULNESS = "cheerfulness"
    # Agreeableness facets
    TRUST = "trust"
    MORALITY = "morality"
    ALTRUISM = "altruism"
    COOPERATION = "cooperation"
    MODESTY = "modesty"
    SYMPATHY = "sympathy"
    # Neuroticism facets
    ANXIETY = "anxiety"
    ANGER = "anger"
    DEPRESSION = "depression"
    SELF_CONSCIOUSNESS = "self_consciousness"
    IMMODERATION = "immoderation"
    VULNERABILITY = "vulnerability"


class CommunicationStyle(Enum):
    """Communication styles."""
    ANALYTICAL = "analytical"
    INTUITIVE = "intuitive"
    FUNCTIONAL = "functional"
    PERSONAL = "personal"


class SocialRole(Enum):
    """Social roles."""
    LEADER = "leader"
    FOLLOWER = "follower"
    MEDIATOR = "mediator"
    INNOVATOR = "innovator"
    CRITIC = "critic"
    SUPPORTER = "supporter"


class ResponseTone(Enum):
    """Response tones."""
    FORMAL = "formal"
    CASUAL = "casual"
    WARM = "warm"
    RESERVED = "reserved"
    ENTHUSIASTIC = "enthusiastic"
    CAUTIOUS = "cautious"


class MoodState(Enum):
    """Mood states."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANXIOUS = "anxious"
    EXCITED = "excited"
    CALM = "calm"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TraitScore:
    """Personality trait score."""
    trait: PersonalityTrait
    score: float = 0.5  # 0-1 scale
    confidence: float = 1.0


@dataclass
class FacetScore:
    """Trait facet score."""
    facet: TraitFacet
    parent_trait: PersonalityTrait
    score: float = 0.5
    weight: float = 1.0


@dataclass
class PersonalityProfile:
    """Complete personality profile."""
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    traits: Dict[PersonalityTrait, TraitScore] = field(default_factory=dict)
    facets: Dict[TraitFacet, FacetScore] = field(default_factory=dict)
    communication_style: CommunicationStyle = CommunicationStyle.ANALYTICAL
    social_role: SocialRole = SocialRole.SUPPORTER
    preferred_tone: ResponseTone = ResponseTone.FORMAL
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehavioralTendency:
    """Behavioral tendency."""
    tendency_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    action_probability: float = 0.5
    modifiers: Dict[str, float] = field(default_factory=dict)


@dataclass
class MoodInfluence:
    """Mood influence on behavior."""
    mood: MoodState
    trait_modifiers: Dict[PersonalityTrait, float] = field(default_factory=dict)
    intensity: float = 0.5
    duration: float = 60.0  # minutes


@dataclass
class InteractionContext:
    """Context for personality interaction."""
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    interlocutor_type: str = ""
    formality_level: float = 0.5  # 0 = informal, 1 = formal
    emotional_context: str = ""
    topic: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ResponseModulation:
    """Response modulation settings."""
    verbosity: float = 0.5  # 0 = terse, 1 = verbose
    emotionality: float = 0.5  # 0 = flat, 1 = expressive
    directness: float = 0.5  # 0 = indirect, 1 = direct
    formality: float = 0.5  # 0 = casual, 1 = formal
    enthusiasm: float = 0.5  # 0 = reserved, 1 = enthusiastic


@dataclass
class PersonalityStats:
    """Personality engine statistics."""
    total_profiles: int = 0
    total_interactions: int = 0
    mood_changes: int = 0
    trait_adaptations: int = 0


# =============================================================================
# TRAIT MAPPINGS
# =============================================================================

TRAIT_FACETS = {
    PersonalityTrait.OPENNESS: [
        TraitFacet.IMAGINATION,
        TraitFacet.ARTISTIC_INTEREST,
        TraitFacet.EMOTIONALITY,
        TraitFacet.ADVENTUROUSNESS,
        TraitFacet.INTELLECT,
        TraitFacet.LIBERALISM,
    ],
    PersonalityTrait.CONSCIENTIOUSNESS: [
        TraitFacet.SELF_EFFICACY,
        TraitFacet.ORDERLINESS,
        TraitFacet.DUTIFULNESS,
        TraitFacet.ACHIEVEMENT,
        TraitFacet.SELF_DISCIPLINE,
        TraitFacet.CAUTIOUSNESS,
    ],
    PersonalityTrait.EXTRAVERSION: [
        TraitFacet.FRIENDLINESS,
        TraitFacet.GREGARIOUSNESS,
        TraitFacet.ASSERTIVENESS,
        TraitFacet.ACTIVITY_LEVEL,
        TraitFacet.EXCITEMENT_SEEKING,
        TraitFacet.CHEERFULNESS,
    ],
    PersonalityTrait.AGREEABLENESS: [
        TraitFacet.TRUST,
        TraitFacet.MORALITY,
        TraitFacet.ALTRUISM,
        TraitFacet.COOPERATION,
        TraitFacet.MODESTY,
        TraitFacet.SYMPATHY,
    ],
    PersonalityTrait.NEUROTICISM: [
        TraitFacet.ANXIETY,
        TraitFacet.ANGER,
        TraitFacet.DEPRESSION,
        TraitFacet.SELF_CONSCIOUSNESS,
        TraitFacet.IMMODERATION,
        TraitFacet.VULNERABILITY,
    ],
}


# =============================================================================
# PERSONALITY GENERATOR
# =============================================================================

class PersonalityGenerator:
    """Generate personality profiles."""

    def generate_random(self, name: str = "") -> PersonalityProfile:
        """Generate random personality."""
        profile = PersonalityProfile(name=name or f"personality_{uuid.uuid4().hex[:8]}")

        # Generate trait scores
        for trait in PersonalityTrait:
            profile.traits[trait] = TraitScore(
                trait=trait,
                score=random.gauss(0.5, 0.2),
                confidence=random.uniform(0.7, 1.0)
            )
            profile.traits[trait].score = max(0.0, min(1.0, profile.traits[trait].score))

        # Generate facet scores
        for trait, facets in TRAIT_FACETS.items():
            base_score = profile.traits[trait].score
            for facet in facets:
                profile.facets[facet] = FacetScore(
                    facet=facet,
                    parent_trait=trait,
                    score=max(0.0, min(1.0, base_score + random.gauss(0, 0.1)))
                )

        # Derive communication style
        profile.communication_style = self._derive_communication_style(profile)

        # Derive social role
        profile.social_role = self._derive_social_role(profile)

        # Derive preferred tone
        profile.preferred_tone = self._derive_tone(profile)

        return profile

    def generate_archetype(
        self,
        archetype: str,
        name: str = ""
    ) -> PersonalityProfile:
        """Generate personality from archetype."""
        archetypes = {
            "leader": {
                PersonalityTrait.OPENNESS: 0.6,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.8,
                PersonalityTrait.EXTRAVERSION: 0.8,
                PersonalityTrait.AGREEABLENESS: 0.5,
                PersonalityTrait.NEUROTICISM: 0.3,
            },
            "analyst": {
                PersonalityTrait.OPENNESS: 0.7,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.9,
                PersonalityTrait.EXTRAVERSION: 0.3,
                PersonalityTrait.AGREEABLENESS: 0.5,
                PersonalityTrait.NEUROTICISM: 0.4,
            },
            "helper": {
                PersonalityTrait.OPENNESS: 0.5,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.7,
                PersonalityTrait.EXTRAVERSION: 0.6,
                PersonalityTrait.AGREEABLENESS: 0.9,
                PersonalityTrait.NEUROTICISM: 0.4,
            },
            "creative": {
                PersonalityTrait.OPENNESS: 0.95,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.4,
                PersonalityTrait.EXTRAVERSION: 0.5,
                PersonalityTrait.AGREEABLENESS: 0.6,
                PersonalityTrait.NEUROTICISM: 0.5,
            },
            "diplomat": {
                PersonalityTrait.OPENNESS: 0.6,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.7,
                PersonalityTrait.EXTRAVERSION: 0.7,
                PersonalityTrait.AGREEABLENESS: 0.85,
                PersonalityTrait.NEUROTICISM: 0.3,
            },
        }

        scores = archetypes.get(archetype.lower(), {
            trait: 0.5 for trait in PersonalityTrait
        })

        profile = PersonalityProfile(name=name or archetype)

        for trait, score in scores.items():
            profile.traits[trait] = TraitScore(
                trait=trait,
                score=score,
                confidence=0.9
            )

        # Generate facets
        for trait, facets in TRAIT_FACETS.items():
            base_score = profile.traits[trait].score
            for facet in facets:
                profile.facets[facet] = FacetScore(
                    facet=facet,
                    parent_trait=trait,
                    score=base_score
                )

        profile.communication_style = self._derive_communication_style(profile)
        profile.social_role = self._derive_social_role(profile)
        profile.preferred_tone = self._derive_tone(profile)

        return profile

    def _derive_communication_style(
        self,
        profile: PersonalityProfile
    ) -> CommunicationStyle:
        """Derive communication style from traits."""
        o = profile.traits.get(PersonalityTrait.OPENNESS, TraitScore(PersonalityTrait.OPENNESS)).score
        c = profile.traits.get(PersonalityTrait.CONSCIENTIOUSNESS, TraitScore(PersonalityTrait.CONSCIENTIOUSNESS)).score
        e = profile.traits.get(PersonalityTrait.EXTRAVERSION, TraitScore(PersonalityTrait.EXTRAVERSION)).score
        a = profile.traits.get(PersonalityTrait.AGREEABLENESS, TraitScore(PersonalityTrait.AGREEABLENESS)).score

        if c > 0.7 and o < 0.5:
            return CommunicationStyle.ANALYTICAL
        elif o > 0.7:
            return CommunicationStyle.INTUITIVE
        elif c > 0.6 and e > 0.5:
            return CommunicationStyle.FUNCTIONAL
        elif a > 0.7 and e > 0.5:
            return CommunicationStyle.PERSONAL

        return CommunicationStyle.ANALYTICAL

    def _derive_social_role(
        self,
        profile: PersonalityProfile
    ) -> SocialRole:
        """Derive social role from traits."""
        e = profile.traits.get(PersonalityTrait.EXTRAVERSION, TraitScore(PersonalityTrait.EXTRAVERSION)).score
        a = profile.traits.get(PersonalityTrait.AGREEABLENESS, TraitScore(PersonalityTrait.AGREEABLENESS)).score
        o = profile.traits.get(PersonalityTrait.OPENNESS, TraitScore(PersonalityTrait.OPENNESS)).score
        c = profile.traits.get(PersonalityTrait.CONSCIENTIOUSNESS, TraitScore(PersonalityTrait.CONSCIENTIOUSNESS)).score

        if e > 0.7 and c > 0.6:
            return SocialRole.LEADER
        elif a > 0.7 and e > 0.5:
            return SocialRole.MEDIATOR
        elif o > 0.8:
            return SocialRole.INNOVATOR
        elif c > 0.7 and a < 0.5:
            return SocialRole.CRITIC
        elif a > 0.7:
            return SocialRole.SUPPORTER

        return SocialRole.FOLLOWER

    def _derive_tone(
        self,
        profile: PersonalityProfile
    ) -> ResponseTone:
        """Derive preferred tone from traits."""
        e = profile.traits.get(PersonalityTrait.EXTRAVERSION, TraitScore(PersonalityTrait.EXTRAVERSION)).score
        a = profile.traits.get(PersonalityTrait.AGREEABLENESS, TraitScore(PersonalityTrait.AGREEABLENESS)).score
        n = profile.traits.get(PersonalityTrait.NEUROTICISM, TraitScore(PersonalityTrait.NEUROTICISM)).score
        c = profile.traits.get(PersonalityTrait.CONSCIENTIOUSNESS, TraitScore(PersonalityTrait.CONSCIENTIOUSNESS)).score

        if c > 0.7:
            return ResponseTone.FORMAL
        elif e > 0.7:
            return ResponseTone.ENTHUSIASTIC
        elif a > 0.7:
            return ResponseTone.WARM
        elif n > 0.6:
            return ResponseTone.CAUTIOUS
        elif e < 0.4:
            return ResponseTone.RESERVED

        return ResponseTone.CASUAL


# =============================================================================
# MOOD MANAGER
# =============================================================================

class MoodManager:
    """Manage mood states and influences."""

    def __init__(self):
        self._current_mood: MoodState = MoodState.NEUTRAL
        self._mood_intensity: float = 0.5
        self._mood_history: deque = deque(maxlen=100)
        self._influences: List[MoodInfluence] = []

    @property
    def current_mood(self) -> MoodState:
        return self._current_mood

    @property
    def mood_intensity(self) -> float:
        return self._mood_intensity

    def set_mood(
        self,
        mood: MoodState,
        intensity: float = 0.5
    ) -> None:
        """Set current mood."""
        self._current_mood = mood
        self._mood_intensity = max(0.0, min(1.0, intensity))
        self._mood_history.append({
            "mood": mood,
            "intensity": self._mood_intensity,
            "timestamp": datetime.now()
        })

    def add_influence(self, influence: MoodInfluence) -> None:
        """Add mood influence."""
        self._influences.append(influence)

    def decay_mood(self, rate: float = 0.1) -> None:
        """Decay mood toward neutral."""
        if self._current_mood != MoodState.NEUTRAL:
            self._mood_intensity -= rate
            if self._mood_intensity <= 0:
                self._current_mood = MoodState.NEUTRAL
                self._mood_intensity = 0.5

    def get_trait_modifiers(self) -> Dict[PersonalityTrait, float]:
        """Get trait modifiers from current mood."""
        modifiers = {trait: 0.0 for trait in PersonalityTrait}

        # Base mood effects
        if self._current_mood == MoodState.POSITIVE:
            modifiers[PersonalityTrait.EXTRAVERSION] += 0.1 * self._mood_intensity
            modifiers[PersonalityTrait.AGREEABLENESS] += 0.1 * self._mood_intensity
        elif self._current_mood == MoodState.NEGATIVE:
            modifiers[PersonalityTrait.NEUROTICISM] += 0.15 * self._mood_intensity
            modifiers[PersonalityTrait.AGREEABLENESS] -= 0.1 * self._mood_intensity
        elif self._current_mood == MoodState.ANXIOUS:
            modifiers[PersonalityTrait.NEUROTICISM] += 0.2 * self._mood_intensity
            modifiers[PersonalityTrait.CONSCIENTIOUSNESS] += 0.05 * self._mood_intensity
        elif self._current_mood == MoodState.EXCITED:
            modifiers[PersonalityTrait.EXTRAVERSION] += 0.2 * self._mood_intensity
            modifiers[PersonalityTrait.OPENNESS] += 0.1 * self._mood_intensity
        elif self._current_mood == MoodState.CALM:
            modifiers[PersonalityTrait.NEUROTICISM] -= 0.1 * self._mood_intensity
            modifiers[PersonalityTrait.AGREEABLENESS] += 0.05 * self._mood_intensity

        # Apply active influences
        for influence in self._influences:
            if influence.mood == self._current_mood:
                for trait, mod in influence.trait_modifiers.items():
                    modifiers[trait] += mod * influence.intensity

        return modifiers


# =============================================================================
# RESPONSE MODULATOR
# =============================================================================

class ResponseModulator:
    """Modulate responses based on personality."""

    def __init__(self, profile: PersonalityProfile):
        self._profile = profile

    def get_modulation(
        self,
        context: InteractionContext,
        mood_manager: Optional[MoodManager] = None
    ) -> ResponseModulation:
        """Get response modulation settings."""
        modulation = ResponseModulation()

        # Base from personality
        traits = self._profile.traits

        # Verbosity: extraversion + openness
        e = traits.get(PersonalityTrait.EXTRAVERSION, TraitScore(PersonalityTrait.EXTRAVERSION)).score
        o = traits.get(PersonalityTrait.OPENNESS, TraitScore(PersonalityTrait.OPENNESS)).score
        modulation.verbosity = (e * 0.6 + o * 0.4)

        # Emotionality: extraversion + neuroticism - conscientiousness
        n = traits.get(PersonalityTrait.NEUROTICISM, TraitScore(PersonalityTrait.NEUROTICISM)).score
        c = traits.get(PersonalityTrait.CONSCIENTIOUSNESS, TraitScore(PersonalityTrait.CONSCIENTIOUSNESS)).score
        modulation.emotionality = max(0.0, min(1.0, e * 0.4 + n * 0.3 - c * 0.1 + 0.2))

        # Directness: extraversion + low agreeableness
        a = traits.get(PersonalityTrait.AGREEABLENESS, TraitScore(PersonalityTrait.AGREEABLENESS)).score
        modulation.directness = e * 0.5 + (1 - a) * 0.3 + 0.2

        # Formality: conscientiousness
        modulation.formality = c * 0.7 + 0.15

        # Enthusiasm: extraversion + openness
        modulation.enthusiasm = (e * 0.5 + o * 0.3 + 0.1)

        # Apply context adjustments
        modulation.formality = (modulation.formality + context.formality_level) / 2

        # Apply mood adjustments
        if mood_manager:
            if mood_manager.current_mood == MoodState.POSITIVE:
                modulation.enthusiasm += 0.15 * mood_manager.mood_intensity
            elif mood_manager.current_mood == MoodState.NEGATIVE:
                modulation.enthusiasm -= 0.1 * mood_manager.mood_intensity
                modulation.verbosity -= 0.1 * mood_manager.mood_intensity
            elif mood_manager.current_mood == MoodState.ANXIOUS:
                modulation.verbosity += 0.1 * mood_manager.mood_intensity

        # Clamp values
        modulation.verbosity = max(0.0, min(1.0, modulation.verbosity))
        modulation.emotionality = max(0.0, min(1.0, modulation.emotionality))
        modulation.directness = max(0.0, min(1.0, modulation.directness))
        modulation.formality = max(0.0, min(1.0, modulation.formality))
        modulation.enthusiasm = max(0.0, min(1.0, modulation.enthusiasm))

        return modulation

    def modulate_text(
        self,
        text: str,
        modulation: ResponseModulation
    ) -> str:
        """Apply modulation to text (placeholder)."""
        # In real implementation, this would use NLP to adjust text style
        result = text

        # Simple adjustments
        if modulation.formality > 0.7:
            result = result.replace("can't", "cannot")
            result = result.replace("don't", "do not")
            result = result.replace("won't", "will not")

        if modulation.enthusiasm > 0.7:
            if not result.endswith("!"):
                result = result.rstrip(".") + "!"

        return result


# =============================================================================
# BEHAVIORAL PREDICTOR
# =============================================================================

class BehavioralPredictor:
    """Predict behavior based on personality."""

    def __init__(self, profile: PersonalityProfile):
        self._profile = profile
        self._tendencies: List[BehavioralTendency] = []

    def add_tendency(self, tendency: BehavioralTendency) -> None:
        """Add behavioral tendency."""
        self._tendencies.append(tendency)

    def predict_response_style(
        self,
        situation: str
    ) -> Dict[str, float]:
        """Predict response style for situation."""
        predictions = {
            "cooperative": 0.5,
            "assertive": 0.5,
            "cautious": 0.5,
            "creative": 0.5,
            "emotional": 0.5,
        }

        traits = self._profile.traits
        e = traits.get(PersonalityTrait.EXTRAVERSION, TraitScore(PersonalityTrait.EXTRAVERSION)).score
        a = traits.get(PersonalityTrait.AGREEABLENESS, TraitScore(PersonalityTrait.AGREEABLENESS)).score
        c = traits.get(PersonalityTrait.CONSCIENTIOUSNESS, TraitScore(PersonalityTrait.CONSCIENTIOUSNESS)).score
        n = traits.get(PersonalityTrait.NEUROTICISM, TraitScore(PersonalityTrait.NEUROTICISM)).score
        o = traits.get(PersonalityTrait.OPENNESS, TraitScore(PersonalityTrait.OPENNESS)).score

        predictions["cooperative"] = a * 0.6 + (1 - e) * 0.2 + 0.2
        predictions["assertive"] = e * 0.5 + (1 - a) * 0.3 + 0.2
        predictions["cautious"] = c * 0.4 + n * 0.3 + (1 - o) * 0.2
        predictions["creative"] = o * 0.7 + (1 - c) * 0.2
        predictions["emotional"] = n * 0.4 + e * 0.3 + (1 - c) * 0.2

        # Adjust for situation keywords
        situation_lower = situation.lower()

        if "conflict" in situation_lower:
            predictions["assertive"] += 0.1
            predictions["cooperative"] -= 0.05
        elif "team" in situation_lower or "collaborate" in situation_lower:
            predictions["cooperative"] += 0.15
        elif "new" in situation_lower or "novel" in situation_lower:
            predictions["creative"] += 0.1
        elif "pressure" in situation_lower or "stress" in situation_lower:
            predictions["cautious"] += 0.1
            predictions["emotional"] += 0.1

        # Clamp
        for key in predictions:
            predictions[key] = max(0.0, min(1.0, predictions[key]))

        return predictions

    def predict_action_probability(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> float:
        """Predict probability of taking action."""
        # Base probability
        probability = 0.5

        traits = self._profile.traits
        e = traits.get(PersonalityTrait.EXTRAVERSION, TraitScore(PersonalityTrait.EXTRAVERSION)).score
        a = traits.get(PersonalityTrait.AGREEABLENESS, TraitScore(PersonalityTrait.AGREEABLENESS)).score
        c = traits.get(PersonalityTrait.CONSCIENTIOUSNESS, TraitScore(PersonalityTrait.CONSCIENTIOUSNESS)).score
        n = traits.get(PersonalityTrait.NEUROTICISM, TraitScore(PersonalityTrait.NEUROTICISM)).score
        o = traits.get(PersonalityTrait.OPENNESS, TraitScore(PersonalityTrait.OPENNESS)).score

        action_lower = action.lower()

        # Adjust based on action type
        if "speak" in action_lower or "present" in action_lower:
            probability += (e - 0.5) * 0.4
        elif "help" in action_lower or "assist" in action_lower:
            probability += (a - 0.5) * 0.4
        elif "risk" in action_lower or "try" in action_lower:
            probability += (o - 0.5) * 0.3 - (n - 0.5) * 0.2
        elif "organize" in action_lower or "plan" in action_lower:
            probability += (c - 0.5) * 0.4
        elif "avoid" in action_lower or "retreat" in action_lower:
            probability += (n - 0.5) * 0.3 - (e - 0.5) * 0.2

        return max(0.0, min(1.0, probability))


# =============================================================================
# PERSONALITY ADAPTER
# =============================================================================

class PersonalityAdapter:
    """Adapt personality over time."""

    def __init__(self, profile: PersonalityProfile):
        self._profile = profile
        self._original = copy.deepcopy(profile)
        self._adaptation_rate = 0.01
        self._adaptation_history: deque = deque(maxlen=1000)

    def adapt(
        self,
        feedback: Dict[str, float],
        learning_rate: float = 0.01
    ) -> Dict[PersonalityTrait, float]:
        """Adapt personality based on feedback."""
        changes = {}

        for trait, adjustment in feedback.items():
            try:
                personality_trait = PersonalityTrait(trait)
                if personality_trait in self._profile.traits:
                    old_score = self._profile.traits[personality_trait].score
                    new_score = old_score + adjustment * learning_rate
                    new_score = max(0.0, min(1.0, new_score))

                    self._profile.traits[personality_trait].score = new_score
                    changes[personality_trait] = new_score - old_score
            except ValueError:
                continue

        self._adaptation_history.append({
            "feedback": feedback,
            "changes": changes,
            "timestamp": datetime.now()
        })

        return changes

    def reset(self) -> None:
        """Reset to original personality."""
        self._profile.traits = copy.deepcopy(self._original.traits)
        self._profile.facets = copy.deepcopy(self._original.facets)

    def get_drift(self) -> Dict[PersonalityTrait, float]:
        """Get drift from original personality."""
        drift = {}

        for trait in PersonalityTrait:
            if trait in self._profile.traits and trait in self._original.traits:
                drift[trait] = (
                    self._profile.traits[trait].score -
                    self._original.traits[trait].score
                )

        return drift


# =============================================================================
# PERSONALITY ENGINE
# =============================================================================

class PersonalityEngine:
    """
    Personality Engine for BAEL.

    Advanced personality modeling and behavioral simulation.
    """

    def __init__(
        self,
        default_profile: Optional[PersonalityProfile] = None
    ):
        self._generator = PersonalityGenerator()
        self._profiles: Dict[str, PersonalityProfile] = {}
        self._mood_managers: Dict[str, MoodManager] = {}
        self._adapters: Dict[str, PersonalityAdapter] = {}
        self._stats = PersonalityStats()

        # Create default profile
        if default_profile:
            self._default_profile = default_profile
        else:
            self._default_profile = self._generator.generate_archetype("analyst", "bael")

        self.add_profile(self._default_profile)

    # -------------------------------------------------------------------------
    # PROFILE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_profile(self, profile: PersonalityProfile) -> None:
        """Add personality profile."""
        self._profiles[profile.profile_id] = profile
        self._mood_managers[profile.profile_id] = MoodManager()
        self._adapters[profile.profile_id] = PersonalityAdapter(profile)
        self._stats.total_profiles += 1

    def get_profile(self, profile_id: str) -> Optional[PersonalityProfile]:
        """Get profile by ID."""
        return self._profiles.get(profile_id)

    def get_default_profile(self) -> PersonalityProfile:
        """Get default profile."""
        return self._default_profile

    def create_profile(
        self,
        name: str = "",
        archetype: Optional[str] = None
    ) -> PersonalityProfile:
        """Create new profile."""
        if archetype:
            profile = self._generator.generate_archetype(archetype, name)
        else:
            profile = self._generator.generate_random(name)

        self.add_profile(profile)
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete profile."""
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            self._mood_managers.pop(profile_id, None)
            self._adapters.pop(profile_id, None)
            self._stats.total_profiles -= 1
            return True
        return False

    def list_profiles(self) -> List[PersonalityProfile]:
        """List all profiles."""
        return list(self._profiles.values())

    # -------------------------------------------------------------------------
    # TRAIT ACCESS
    # -------------------------------------------------------------------------

    def get_trait(
        self,
        profile_id: str,
        trait: PersonalityTrait
    ) -> Optional[float]:
        """Get trait score."""
        profile = self._profiles.get(profile_id)
        if profile and trait in profile.traits:
            return profile.traits[trait].score
        return None

    def get_all_traits(
        self,
        profile_id: str
    ) -> Dict[PersonalityTrait, float]:
        """Get all trait scores."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return {}

        return {
            trait: score.score
            for trait, score in profile.traits.items()
        }

    def get_facet(
        self,
        profile_id: str,
        facet: TraitFacet
    ) -> Optional[float]:
        """Get facet score."""
        profile = self._profiles.get(profile_id)
        if profile and facet in profile.facets:
            return profile.facets[facet].score
        return None

    def get_effective_traits(
        self,
        profile_id: str
    ) -> Dict[PersonalityTrait, float]:
        """Get traits with mood modifiers."""
        base_traits = self.get_all_traits(profile_id)

        mood_manager = self._mood_managers.get(profile_id)
        if not mood_manager:
            return base_traits

        modifiers = mood_manager.get_trait_modifiers()

        effective = {}
        for trait, score in base_traits.items():
            effective[trait] = max(0.0, min(1.0, score + modifiers.get(trait, 0.0)))

        return effective

    # -------------------------------------------------------------------------
    # MOOD MANAGEMENT
    # -------------------------------------------------------------------------

    def set_mood(
        self,
        profile_id: str,
        mood: MoodState,
        intensity: float = 0.5
    ) -> None:
        """Set mood for profile."""
        if profile_id in self._mood_managers:
            self._mood_managers[profile_id].set_mood(mood, intensity)
            self._stats.mood_changes += 1

    def get_mood(self, profile_id: str) -> Tuple[MoodState, float]:
        """Get current mood."""
        if profile_id in self._mood_managers:
            mm = self._mood_managers[profile_id]
            return mm.current_mood, mm.mood_intensity
        return MoodState.NEUTRAL, 0.5

    def decay_mood(self, profile_id: str, rate: float = 0.1) -> None:
        """Decay mood toward neutral."""
        if profile_id in self._mood_managers:
            self._mood_managers[profile_id].decay_mood(rate)

    # -------------------------------------------------------------------------
    # RESPONSE MODULATION
    # -------------------------------------------------------------------------

    def get_response_modulation(
        self,
        profile_id: str,
        context: Optional[InteractionContext] = None
    ) -> ResponseModulation:
        """Get response modulation settings."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return ResponseModulation()

        context = context or InteractionContext()
        modulator = ResponseModulator(profile)
        mood_manager = self._mood_managers.get(profile_id)

        self._stats.total_interactions += 1

        return modulator.get_modulation(context, mood_manager)

    def modulate_response(
        self,
        profile_id: str,
        text: str,
        context: Optional[InteractionContext] = None
    ) -> str:
        """Modulate response text based on personality."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return text

        modulator = ResponseModulator(profile)
        modulation = self.get_response_modulation(profile_id, context)

        return modulator.modulate_text(text, modulation)

    # -------------------------------------------------------------------------
    # BEHAVIOR PREDICTION
    # -------------------------------------------------------------------------

    def predict_behavior(
        self,
        profile_id: str,
        situation: str
    ) -> Dict[str, float]:
        """Predict behavioral tendencies."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return {}

        predictor = BehavioralPredictor(profile)
        return predictor.predict_response_style(situation)

    def predict_action(
        self,
        profile_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Predict probability of action."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return 0.5

        predictor = BehavioralPredictor(profile)
        return predictor.predict_action_probability(action, context or {})

    # -------------------------------------------------------------------------
    # ADAPTATION
    # -------------------------------------------------------------------------

    def adapt_personality(
        self,
        profile_id: str,
        feedback: Dict[str, float],
        learning_rate: float = 0.01
    ) -> Dict[PersonalityTrait, float]:
        """Adapt personality based on feedback."""
        if profile_id not in self._adapters:
            return {}

        changes = self._adapters[profile_id].adapt(feedback, learning_rate)
        self._stats.trait_adaptations += 1

        return changes

    def reset_adaptation(self, profile_id: str) -> None:
        """Reset personality to original."""
        if profile_id in self._adapters:
            self._adapters[profile_id].reset()

    def get_adaptation_drift(
        self,
        profile_id: str
    ) -> Dict[PersonalityTrait, float]:
        """Get personality drift from original."""
        if profile_id not in self._adapters:
            return {}

        return self._adapters[profile_id].get_drift()

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def compare_profiles(
        self,
        profile_id_1: str,
        profile_id_2: str
    ) -> Dict[str, Any]:
        """Compare two personality profiles."""
        p1 = self._profiles.get(profile_id_1)
        p2 = self._profiles.get(profile_id_2)

        if not p1 or not p2:
            return {}

        trait_diffs = {}
        for trait in PersonalityTrait:
            s1 = p1.traits.get(trait, TraitScore(trait)).score
            s2 = p2.traits.get(trait, TraitScore(trait)).score
            trait_diffs[trait.value] = abs(s1 - s2)

        # Calculate overall similarity
        total_diff = sum(trait_diffs.values())
        similarity = 1.0 - (total_diff / len(PersonalityTrait))

        return {
            "trait_differences": trait_diffs,
            "similarity": similarity,
            "same_communication_style": p1.communication_style == p2.communication_style,
            "same_social_role": p1.social_role == p2.social_role,
        }

    def get_personality_summary(self, profile_id: str) -> Dict[str, Any]:
        """Get personality summary."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return {}

        traits = self.get_all_traits(profile_id)

        # Identify dominant traits
        sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)
        dominant = [t.value for t, s in sorted_traits[:2]]

        return {
            "name": profile.name,
            "dominant_traits": dominant,
            "communication_style": profile.communication_style.value,
            "social_role": profile.social_role.value,
            "preferred_tone": profile.preferred_tone.value,
            "trait_scores": {t.value: s for t, s in traits.items()},
        }

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> PersonalityStats:
        """Get engine statistics."""
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Personality Engine."""
    print("=" * 70)
    print("BAEL - PERSONALITY ENGINE DEMO")
    print("Advanced Personality Modeling and Behavioral Simulation")
    print("=" * 70)
    print()

    engine = PersonalityEngine()

    # 1. Create Profiles
    print("1. CREATE PERSONALITY PROFILES:")
    print("-" * 40)

    leader = engine.create_profile("Commander", archetype="leader")
    analyst = engine.create_profile("Strategist", archetype="analyst")
    helper = engine.create_profile("Supporter", archetype="helper")
    random_p = engine.create_profile("Random Agent")

    print(f"   Created: {leader.name} ({leader.social_role.value})")
    print(f"   Created: {analyst.name} ({analyst.social_role.value})")
    print(f"   Created: {helper.name} ({helper.social_role.value})")
    print(f"   Created: {random_p.name}")
    print()

    # 2. Get Traits
    print("2. GET TRAIT SCORES:")
    print("-" * 40)

    traits = engine.get_all_traits(leader.profile_id)
    for trait, score in traits.items():
        print(f"   {trait.value}: {score:.3f}")
    print()

    # 3. Get Personality Summary
    print("3. PERSONALITY SUMMARY:")
    print("-" * 40)

    summary = engine.get_personality_summary(leader.profile_id)
    print(f"   Name: {summary['name']}")
    print(f"   Dominant: {summary['dominant_traits']}")
    print(f"   Style: {summary['communication_style']}")
    print(f"   Role: {summary['social_role']}")
    print()

    # 4. Set Mood
    print("4. SET MOOD:")
    print("-" * 40)

    engine.set_mood(leader.profile_id, MoodState.EXCITED, 0.8)
    mood, intensity = engine.get_mood(leader.profile_id)
    print(f"   Mood: {mood.value} (intensity: {intensity:.2f})")

    # Show effective traits with mood
    effective = engine.get_effective_traits(leader.profile_id)
    base = engine.get_all_traits(leader.profile_id)

    print("   Trait changes due to mood:")
    for trait in PersonalityTrait:
        diff = effective[trait] - base[trait]
        if abs(diff) > 0.01:
            print(f"     {trait.value}: {diff:+.3f}")
    print()

    # 5. Response Modulation
    print("5. RESPONSE MODULATION:")
    print("-" * 40)

    context = InteractionContext(
        formality_level=0.7,
        topic="project planning"
    )

    modulation = engine.get_response_modulation(leader.profile_id, context)
    print(f"   Verbosity: {modulation.verbosity:.3f}")
    print(f"   Emotionality: {modulation.emotionality:.3f}")
    print(f"   Directness: {modulation.directness:.3f}")
    print(f"   Formality: {modulation.formality:.3f}")
    print(f"   Enthusiasm: {modulation.enthusiasm:.3f}")
    print()

    # 6. Modulate Text
    print("6. MODULATE TEXT:")
    print("-" * 40)

    original = "I think we should proceed with the plan."
    modulated = engine.modulate_response(leader.profile_id, original, context)

    print(f"   Original: {original}")
    print(f"   Modulated: {modulated}")
    print()

    # 7. Predict Behavior
    print("7. PREDICT BEHAVIOR:")
    print("-" * 40)

    predictions = engine.predict_behavior(leader.profile_id, "team conflict resolution")
    for behavior, prob in predictions.items():
        print(f"   {behavior}: {prob:.3f}")
    print()

    # 8. Predict Action
    print("8. PREDICT ACTION PROBABILITY:")
    print("-" * 40)

    actions = ["speak up in meeting", "help a colleague", "take a risk", "avoid confrontation"]
    for action in actions:
        prob = engine.predict_action(leader.profile_id, action)
        print(f"   {action}: {prob:.3f}")
    print()

    # 9. Compare Profiles
    print("9. COMPARE PROFILES:")
    print("-" * 40)

    comparison = engine.compare_profiles(leader.profile_id, analyst.profile_id)
    print(f"   Similarity: {comparison['similarity']:.3f}")
    print(f"   Same style: {comparison['same_communication_style']}")
    print(f"   Same role: {comparison['same_social_role']}")
    print()

    # 10. Adapt Personality
    print("10. ADAPT PERSONALITY:")
    print("-" * 40)

    feedback = {
        "extraversion": 0.5,
        "agreeableness": -0.3,
    }

    changes = engine.adapt_personality(leader.profile_id, feedback, learning_rate=0.1)
    print(f"   Feedback: {feedback}")
    print(f"   Changes: {changes}")
    print()

    # 11. Get Drift
    print("11. GET ADAPTATION DRIFT:")
    print("-" * 40)

    drift = engine.get_adaptation_drift(leader.profile_id)
    for trait, diff in drift.items():
        if abs(diff) > 0.001:
            print(f"   {trait.value}: {diff:+.4f}")
    print()

    # 12. Reset Adaptation
    print("12. RESET ADAPTATION:")
    print("-" * 40)

    engine.reset_adaptation(leader.profile_id)
    new_drift = engine.get_adaptation_drift(leader.profile_id)
    print(f"   Drift after reset: {sum(abs(d) for d in new_drift.values()):.6f}")
    print()

    # 13. List Profiles
    print("13. LIST PROFILES:")
    print("-" * 40)

    profiles = engine.list_profiles()
    for p in profiles:
        print(f"   - {p.name}: {p.communication_style.value}, {p.social_role.value}")
    print()

    # 14. Mood Decay
    print("14. MOOD DECAY:")
    print("-" * 40)

    mood_before, intensity_before = engine.get_mood(leader.profile_id)
    print(f"   Before: {mood_before.value} ({intensity_before:.2f})")

    engine.decay_mood(leader.profile_id, rate=0.3)
    mood_after, intensity_after = engine.get_mood(leader.profile_id)
    print(f"   After decay: {mood_after.value} ({intensity_after:.2f})")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Total profiles: {stats.total_profiles}")
    print(f"   Total interactions: {stats.total_interactions}")
    print(f"   Mood changes: {stats.mood_changes}")
    print(f"   Trait adaptations: {stats.trait_adaptations}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Personality Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
