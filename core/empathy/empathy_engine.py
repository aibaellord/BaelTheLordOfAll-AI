#!/usr/bin/env python3
"""
BAEL - Empathy Engine
Empathic modeling and understanding for agents.

Features:
- Emotional state modeling
- Perspective taking
- Empathic response generation
- Affect recognition
- Social understanding
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class EmotionType(Enum):
    """Types of emotions."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"


class EmotionIntensity(Enum):
    """Emotion intensity levels."""
    NONE = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    INTENSE = 4


class PerspectiveType(Enum):
    """Types of perspectives."""
    COGNITIVE = "cognitive"
    AFFECTIVE = "affective"
    MOTIVATIONAL = "motivational"


class EmpathyLevel(Enum):
    """Levels of empathy."""
    NONE = 0
    RECOGNITION = 1
    UNDERSTANDING = 2
    SHARING = 3
    COMPASSION = 4


class ResponseType(Enum):
    """Types of empathic responses."""
    ACKNOWLEDGMENT = "acknowledgment"
    VALIDATION = "validation"
    SUPPORT = "support"
    ENCOURAGEMENT = "encouragement"
    COMFORT = "comfort"


class SocialCue(Enum):
    """Types of social cues."""
    VERBAL = "verbal"
    CONTEXTUAL = "contextual"
    BEHAVIORAL = "behavioral"
    RELATIONAL = "relational"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class EmotionalState:
    """An emotional state."""
    state_id: str = ""
    entity_id: str = ""
    emotions: Dict[str, float] = field(default_factory=dict)
    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.state_id:
            self.state_id = str(uuid.uuid4())[:8]


@dataclass
class Perspective:
    """A perspective model."""
    perspective_id: str = ""
    entity_id: str = ""
    perspective_type: PerspectiveType = PerspectiveType.COGNITIVE
    beliefs: Dict[str, Any] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    confidence: float = 0.5

    def __post_init__(self):
        if not self.perspective_id:
            self.perspective_id = str(uuid.uuid4())[:8]


@dataclass
class EmpathicResponse:
    """An empathic response."""
    response_id: str = ""
    response_type: ResponseType = ResponseType.ACKNOWLEDGMENT
    content: str = ""
    target_emotion: EmotionType = EmotionType.JOY
    empathy_level: EmpathyLevel = EmpathyLevel.RECOGNITION
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.response_id:
            self.response_id = str(uuid.uuid4())[:8]


@dataclass
class SocialContext:
    """Social context information."""
    context_id: str = ""
    participants: List[str] = field(default_factory=list)
    relationship_type: str = ""
    formality: float = 0.5
    cues: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.context_id:
            self.context_id = str(uuid.uuid4())[:8]


@dataclass
class AffectSignal:
    """An affect signal from input."""
    signal_id: str = ""
    source: str = ""
    emotions_detected: Dict[str, float] = field(default_factory=dict)
    sentiment: float = 0.0
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.signal_id:
            self.signal_id = str(uuid.uuid4())[:8]


@dataclass
class EmpathyConfig:
    """Empathy configuration."""
    default_empathy_level: EmpathyLevel = EmpathyLevel.UNDERSTANDING
    affect_decay: float = 0.1
    perspective_confidence_threshold: float = 0.6


# =============================================================================
# EMOTION MODELER
# =============================================================================

class EmotionModeler:
    """Model emotional states."""

    def __init__(self):
        self._states: Dict[str, EmotionalState] = {}
        self._history: Dict[str, List[EmotionalState]] = defaultdict(list)

    def create_state(
        self,
        entity_id: str,
        emotions: Optional[Dict[str, float]] = None
    ) -> EmotionalState:
        """Create an emotional state."""
        emotions = emotions or {}

        valence = self._compute_valence(emotions)
        arousal = self._compute_arousal(emotions)

        state = EmotionalState(
            entity_id=entity_id,
            emotions=emotions,
            valence=valence,
            arousal=arousal
        )

        self._states[entity_id] = state
        self._history[entity_id].append(state)

        return state

    def update_state(
        self,
        entity_id: str,
        emotion_updates: Dict[str, float]
    ) -> EmotionalState:
        """Update an emotional state."""
        current = self._states.get(entity_id)

        if not current:
            return self.create_state(entity_id, emotion_updates)

        new_emotions = current.emotions.copy()

        for emotion, value in emotion_updates.items():
            current_value = new_emotions.get(emotion, 0.0)
            new_emotions[emotion] = (current_value + value) / 2

        new_emotions = {
            k: max(0.0, min(1.0, v))
            for k, v in new_emotions.items()
        }

        return self.create_state(entity_id, new_emotions)

    def get_state(self, entity_id: str) -> Optional[EmotionalState]:
        """Get current emotional state."""
        return self._states.get(entity_id)

    def get_dominant_emotion(
        self,
        entity_id: str
    ) -> Optional[Tuple[str, float]]:
        """Get dominant emotion for entity."""
        state = self._states.get(entity_id)

        if not state or not state.emotions:
            return None

        dominant = max(state.emotions.items(), key=lambda x: x[1])

        return dominant

    def _compute_valence(self, emotions: Dict[str, float]) -> float:
        """Compute emotional valence."""
        positive = [EmotionType.JOY.value, EmotionType.TRUST.value, EmotionType.ANTICIPATION.value]
        negative = [EmotionType.SADNESS.value, EmotionType.ANGER.value, EmotionType.FEAR.value, EmotionType.DISGUST.value]

        pos_sum = sum(emotions.get(e, 0) for e in positive)
        neg_sum = sum(emotions.get(e, 0) for e in negative)

        total = pos_sum + neg_sum

        if total == 0:
            return 0.0

        return (pos_sum - neg_sum) / total

    def _compute_arousal(self, emotions: Dict[str, float]) -> float:
        """Compute emotional arousal."""
        high_arousal = [EmotionType.ANGER.value, EmotionType.FEAR.value, EmotionType.SURPRISE.value]

        arousal_sum = sum(emotions.get(e, 0) for e in high_arousal)

        return min(1.0, arousal_sum)

    def get_intensity(self, entity_id: str) -> EmotionIntensity:
        """Get emotional intensity."""
        state = self._states.get(entity_id)

        if not state:
            return EmotionIntensity.NONE

        max_emotion = max(state.emotions.values()) if state.emotions else 0.0

        if max_emotion >= 0.8:
            return EmotionIntensity.INTENSE
        elif max_emotion >= 0.6:
            return EmotionIntensity.HIGH
        elif max_emotion >= 0.4:
            return EmotionIntensity.MODERATE
        elif max_emotion >= 0.2:
            return EmotionIntensity.LOW
        else:
            return EmotionIntensity.NONE

    def decay_emotions(
        self,
        entity_id: str,
        decay_rate: float = 0.1
    ) -> Optional[EmotionalState]:
        """Apply decay to emotions."""
        state = self._states.get(entity_id)

        if not state:
            return None

        decayed = {
            k: max(0.0, v - decay_rate)
            for k, v in state.emotions.items()
        }

        return self.create_state(entity_id, decayed)

    def get_history(
        self,
        entity_id: str,
        limit: int = 20
    ) -> List[EmotionalState]:
        """Get emotion history."""
        return self._history[entity_id][-limit:]


# =============================================================================
# PERSPECTIVE TAKER
# =============================================================================

class PerspectiveTaker:
    """Take and model perspectives."""

    def __init__(self):
        self._perspectives: Dict[str, Dict[str, Perspective]] = defaultdict(dict)

    def model_perspective(
        self,
        entity_id: str,
        perspective_type: PerspectiveType,
        beliefs: Optional[Dict[str, Any]] = None,
        goals: Optional[List[str]] = None,
        concerns: Optional[List[str]] = None
    ) -> Perspective:
        """Model a perspective."""
        perspective = Perspective(
            entity_id=entity_id,
            perspective_type=perspective_type,
            beliefs=beliefs or {},
            goals=goals or [],
            concerns=concerns or []
        )

        self._perspectives[entity_id][perspective_type.value] = perspective

        return perspective

    def get_perspective(
        self,
        entity_id: str,
        perspective_type: PerspectiveType
    ) -> Optional[Perspective]:
        """Get a specific perspective."""
        entity_perspectives = self._perspectives.get(entity_id, {})
        return entity_perspectives.get(perspective_type.value)

    def get_all_perspectives(
        self,
        entity_id: str
    ) -> List[Perspective]:
        """Get all perspectives for entity."""
        return list(self._perspectives.get(entity_id, {}).values())

    def infer_belief(
        self,
        entity_id: str,
        belief_key: str
    ) -> Optional[Any]:
        """Infer a belief from perspectives."""
        cognitive = self.get_perspective(entity_id, PerspectiveType.COGNITIVE)

        if cognitive and belief_key in cognitive.beliefs:
            return cognitive.beliefs[belief_key]

        return None

    def infer_goal(
        self,
        entity_id: str
    ) -> Optional[str]:
        """Infer primary goal."""
        motivational = self.get_perspective(entity_id, PerspectiveType.MOTIVATIONAL)

        if motivational and motivational.goals:
            return motivational.goals[0]

        return None

    def update_perspective(
        self,
        entity_id: str,
        perspective_type: PerspectiveType,
        updates: Dict[str, Any]
    ) -> Optional[Perspective]:
        """Update a perspective."""
        perspective = self.get_perspective(entity_id, perspective_type)

        if not perspective:
            return None

        if "beliefs" in updates:
            perspective.beliefs.update(updates["beliefs"])

        if "goals" in updates:
            perspective.goals.extend(updates["goals"])

        if "concerns" in updates:
            perspective.concerns.extend(updates["concerns"])

        perspective.confidence = min(1.0, perspective.confidence + 0.1)

        return perspective

    def compare_perspectives(
        self,
        entity_a: str,
        entity_b: str,
        perspective_type: PerspectiveType
    ) -> float:
        """Compare perspectives between entities."""
        persp_a = self.get_perspective(entity_a, perspective_type)
        persp_b = self.get_perspective(entity_b, perspective_type)

        if not persp_a or not persp_b:
            return 0.0

        shared_beliefs = set(persp_a.beliefs.keys()) & set(persp_b.beliefs.keys())
        all_beliefs = set(persp_a.beliefs.keys()) | set(persp_b.beliefs.keys())

        if not all_beliefs:
            return 0.5

        agreement = 0
        for belief in shared_beliefs:
            if persp_a.beliefs[belief] == persp_b.beliefs[belief]:
                agreement += 1

        return agreement / len(all_beliefs) if all_beliefs else 0.0


# =============================================================================
# AFFECT RECOGNIZER
# =============================================================================

class AffectRecognizer:
    """Recognize affect from inputs."""

    def __init__(self):
        self._emotion_keywords = {
            EmotionType.JOY.value: ["happy", "glad", "excited", "pleased", "delighted", "wonderful"],
            EmotionType.SADNESS.value: ["sad", "unhappy", "depressed", "disappointed", "sorry", "unfortunate"],
            EmotionType.ANGER.value: ["angry", "frustrated", "annoyed", "furious", "upset", "irritated"],
            EmotionType.FEAR.value: ["afraid", "scared", "worried", "anxious", "concerned", "nervous"],
            EmotionType.SURPRISE.value: ["surprised", "amazed", "shocked", "unexpected", "astonished"],
            EmotionType.TRUST.value: ["trust", "believe", "confident", "reliable", "faithful"],
        }

        self._signals: List[AffectSignal] = []

    def recognize(
        self,
        text: str,
        source: str = ""
    ) -> AffectSignal:
        """Recognize affect from text."""
        text_lower = text.lower()

        emotions_detected = {}

        for emotion, keywords in self._emotion_keywords.items():
            score = 0.0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 0.2

            if score > 0:
                emotions_detected[emotion] = min(1.0, score)

        sentiment = self._compute_sentiment(text_lower)

        confidence = min(1.0, len(emotions_detected) * 0.3 + 0.2)

        signal = AffectSignal(
            source=source,
            emotions_detected=emotions_detected,
            sentiment=sentiment,
            confidence=confidence
        )

        self._signals.append(signal)

        return signal

    def _compute_sentiment(self, text: str) -> float:
        """Compute sentiment score."""
        positive_words = ["good", "great", "excellent", "love", "wonderful", "happy", "thank"]
        negative_words = ["bad", "terrible", "hate", "awful", "sad", "angry", "disappointed"]

        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)

        total = pos_count + neg_count

        if total == 0:
            return 0.0

        return (pos_count - neg_count) / total

    def get_dominant_affect(
        self,
        signal: AffectSignal
    ) -> Optional[Tuple[str, float]]:
        """Get dominant affect from signal."""
        if not signal.emotions_detected:
            return None

        return max(signal.emotions_detected.items(), key=lambda x: x[1])

    def get_recent_signals(
        self,
        limit: int = 20
    ) -> List[AffectSignal]:
        """Get recent affect signals."""
        return self._signals[-limit:]

    def aggregate_signals(
        self,
        signals: List[AffectSignal]
    ) -> Dict[str, float]:
        """Aggregate multiple signals."""
        aggregated = defaultdict(list)

        for signal in signals:
            for emotion, score in signal.emotions_detected.items():
                aggregated[emotion].append(score)

        return {
            emotion: sum(scores) / len(scores)
            for emotion, scores in aggregated.items()
        }


# =============================================================================
# RESPONSE GENERATOR
# =============================================================================

class ResponseGenerator:
    """Generate empathic responses."""

    def __init__(self):
        self._templates = {
            ResponseType.ACKNOWLEDGMENT: [
                "I understand that you're feeling {emotion}.",
                "I can see this is {emotion} for you.",
            ],
            ResponseType.VALIDATION: [
                "It's completely valid to feel {emotion} about this.",
                "Your feelings of {emotion} are understandable.",
            ],
            ResponseType.SUPPORT: [
                "I'm here to help you through this.",
                "You don't have to face this alone.",
            ],
            ResponseType.ENCOURAGEMENT: [
                "You're handling this well.",
                "I believe in your ability to get through this.",
            ],
            ResponseType.COMFORT: [
                "It's going to be okay.",
                "Things will get better.",
            ],
        }

        self._responses: List[EmpathicResponse] = []

    def generate(
        self,
        response_type: ResponseType,
        target_emotion: EmotionType,
        empathy_level: EmpathyLevel = EmpathyLevel.UNDERSTANDING
    ) -> EmpathicResponse:
        """Generate an empathic response."""
        templates = self._templates.get(response_type, [])

        if templates:
            template = random.choice(templates)
            content = template.format(emotion=target_emotion.value)
        else:
            content = f"I acknowledge your {target_emotion.value}."

        response = EmpathicResponse(
            response_type=response_type,
            content=content,
            target_emotion=target_emotion,
            empathy_level=empathy_level
        )

        self._responses.append(response)

        return response

    def generate_contextual(
        self,
        emotional_state: EmotionalState,
        context: SocialContext
    ) -> EmpathicResponse:
        """Generate contextually appropriate response."""
        if not emotional_state.emotions:
            return self.generate(
                ResponseType.ACKNOWLEDGMENT,
                EmotionType.JOY,
                EmpathyLevel.RECOGNITION
            )

        dominant_emotion = max(
            emotional_state.emotions.items(),
            key=lambda x: x[1]
        )

        emotion_type = EmotionType(dominant_emotion[0])
        intensity = dominant_emotion[1]

        if intensity >= 0.7:
            response_type = ResponseType.COMFORT
            empathy_level = EmpathyLevel.COMPASSION
        elif intensity >= 0.5:
            response_type = ResponseType.VALIDATION
            empathy_level = EmpathyLevel.SHARING
        elif intensity >= 0.3:
            response_type = ResponseType.SUPPORT
            empathy_level = EmpathyLevel.UNDERSTANDING
        else:
            response_type = ResponseType.ACKNOWLEDGMENT
            empathy_level = EmpathyLevel.RECOGNITION

        if context.formality > 0.7:
            empathy_level = EmpathyLevel.RECOGNITION

        return self.generate(response_type, emotion_type, empathy_level)

    def get_responses(
        self,
        limit: int = 20
    ) -> List[EmpathicResponse]:
        """Get generated responses."""
        return self._responses[-limit:]


# =============================================================================
# EMPATHY ENGINE
# =============================================================================

class EmpathyEngine:
    """
    Empathy Engine for BAEL.

    Empathic modeling and understanding.
    """

    def __init__(self, config: Optional[EmpathyConfig] = None):
        self._config = config or EmpathyConfig()

        self._emotion_modeler = EmotionModeler()
        self._perspective_taker = PerspectiveTaker()
        self._affect_recognizer = AffectRecognizer()
        self._response_generator = ResponseGenerator()

        self._contexts: Dict[str, SocialContext] = {}

    # ----- Emotion Operations -----

    def model_emotions(
        self,
        entity_id: str,
        emotions: Dict[str, float]
    ) -> EmotionalState:
        """Model emotional state."""
        return self._emotion_modeler.create_state(entity_id, emotions)

    def update_emotions(
        self,
        entity_id: str,
        emotion_updates: Dict[str, float]
    ) -> EmotionalState:
        """Update emotional state."""
        return self._emotion_modeler.update_state(entity_id, emotion_updates)

    def get_emotional_state(
        self,
        entity_id: str
    ) -> Optional[EmotionalState]:
        """Get emotional state."""
        return self._emotion_modeler.get_state(entity_id)

    def get_dominant_emotion(
        self,
        entity_id: str
    ) -> Optional[Tuple[str, float]]:
        """Get dominant emotion."""
        return self._emotion_modeler.get_dominant_emotion(entity_id)

    def get_emotion_intensity(
        self,
        entity_id: str
    ) -> EmotionIntensity:
        """Get emotion intensity."""
        return self._emotion_modeler.get_intensity(entity_id)

    # ----- Perspective Operations -----

    def model_perspective(
        self,
        entity_id: str,
        perspective_type: PerspectiveType,
        beliefs: Optional[Dict[str, Any]] = None,
        goals: Optional[List[str]] = None,
        concerns: Optional[List[str]] = None
    ) -> Perspective:
        """Model a perspective."""
        return self._perspective_taker.model_perspective(
            entity_id=entity_id,
            perspective_type=perspective_type,
            beliefs=beliefs,
            goals=goals,
            concerns=concerns
        )

    def get_perspective(
        self,
        entity_id: str,
        perspective_type: PerspectiveType
    ) -> Optional[Perspective]:
        """Get a perspective."""
        return self._perspective_taker.get_perspective(entity_id, perspective_type)

    def infer_belief(
        self,
        entity_id: str,
        belief_key: str
    ) -> Optional[Any]:
        """Infer a belief."""
        return self._perspective_taker.infer_belief(entity_id, belief_key)

    def infer_goal(self, entity_id: str) -> Optional[str]:
        """Infer primary goal."""
        return self._perspective_taker.infer_goal(entity_id)

    def compare_perspectives(
        self,
        entity_a: str,
        entity_b: str
    ) -> float:
        """Compare perspectives."""
        return self._perspective_taker.compare_perspectives(
            entity_a, entity_b, PerspectiveType.COGNITIVE
        )

    # ----- Affect Operations -----

    def recognize_affect(
        self,
        text: str,
        source: str = ""
    ) -> AffectSignal:
        """Recognize affect from text."""
        signal = self._affect_recognizer.recognize(text, source)

        if source:
            self._emotion_modeler.update_state(source, signal.emotions_detected)

        return signal

    def get_sentiment(self, text: str) -> float:
        """Get sentiment score."""
        signal = self._affect_recognizer.recognize(text)
        return signal.sentiment

    # ----- Context Operations -----

    def set_context(
        self,
        context_id: str,
        participants: List[str],
        relationship_type: str = "",
        formality: float = 0.5
    ) -> SocialContext:
        """Set social context."""
        context = SocialContext(
            context_id=context_id,
            participants=participants,
            relationship_type=relationship_type,
            formality=formality
        )

        self._contexts[context_id] = context

        return context

    def get_context(self, context_id: str) -> Optional[SocialContext]:
        """Get social context."""
        return self._contexts.get(context_id)

    # ----- Response Operations -----

    def generate_response(
        self,
        entity_id: str,
        context_id: Optional[str] = None
    ) -> EmpathicResponse:
        """Generate empathic response."""
        emotional_state = self._emotion_modeler.get_state(entity_id)

        if not emotional_state:
            emotional_state = EmotionalState(entity_id=entity_id)

        context = self._contexts.get(context_id) if context_id else SocialContext()

        return self._response_generator.generate_contextual(
            emotional_state, context
        )

    def generate_acknowledgment(
        self,
        emotion: EmotionType
    ) -> EmpathicResponse:
        """Generate acknowledgment response."""
        return self._response_generator.generate(
            ResponseType.ACKNOWLEDGMENT,
            emotion,
            EmpathyLevel.RECOGNITION
        )

    def generate_validation(
        self,
        emotion: EmotionType
    ) -> EmpathicResponse:
        """Generate validation response."""
        return self._response_generator.generate(
            ResponseType.VALIDATION,
            emotion,
            EmpathyLevel.UNDERSTANDING
        )

    def generate_support(
        self,
        emotion: EmotionType
    ) -> EmpathicResponse:
        """Generate support response."""
        return self._response_generator.generate(
            ResponseType.SUPPORT,
            emotion,
            EmpathyLevel.SHARING
        )

    # ----- Empathy Level Operations -----

    def compute_empathy_level(
        self,
        entity_id: str
    ) -> EmpathyLevel:
        """Compute empathy level for entity."""
        emotional_state = self._emotion_modeler.get_state(entity_id)
        perspectives = self._perspective_taker.get_all_perspectives(entity_id)

        if not emotional_state and not perspectives:
            return EmpathyLevel.NONE

        if emotional_state:
            level = EmpathyLevel.RECOGNITION

            if perspectives:
                level = EmpathyLevel.UNDERSTANDING

                avg_confidence = sum(p.confidence for p in perspectives) / len(perspectives)

                if avg_confidence >= self._config.perspective_confidence_threshold:
                    level = EmpathyLevel.SHARING

                if avg_confidence >= 0.8 and self._emotion_modeler.get_intensity(entity_id).value >= 3:
                    level = EmpathyLevel.COMPASSION

            return level

        return EmpathyLevel.RECOGNITION

    # ----- Decay Operations -----

    def decay_emotions(self, entity_id: str) -> Optional[EmotionalState]:
        """Apply emotional decay."""
        return self._emotion_modeler.decay_emotions(
            entity_id,
            self._config.affect_decay
        )

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "entities_modeled": len(self._emotion_modeler._states),
            "perspectives_modeled": sum(
                len(persp)
                for persp in self._perspective_taker._perspectives.values()
            ),
            "affect_signals": len(self._affect_recognizer._signals),
            "responses_generated": len(self._response_generator._responses),
            "contexts": len(self._contexts)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Empathy Engine."""
    print("=" * 70)
    print("BAEL - EMPATHY ENGINE DEMO")
    print("Empathic Modeling and Understanding")
    print("=" * 70)
    print()

    engine = EmpathyEngine()

    # 1. Model Emotions
    print("1. MODEL EMOTIONS:")
    print("-" * 40)

    state1 = engine.model_emotions("user1", {
        EmotionType.SADNESS.value: 0.7,
        EmotionType.FEAR.value: 0.4
    })

    print(f"   Entity: {state1.entity_id}")
    print(f"   Emotions: {state1.emotions}")
    print(f"   Valence: {state1.valence:.2f}")
    print(f"   Arousal: {state1.arousal:.2f}")
    print()

    # 2. Get Dominant Emotion
    print("2. DOMINANT EMOTION:")
    print("-" * 40)

    dominant = engine.get_dominant_emotion("user1")
    if dominant:
        print(f"   Dominant: {dominant[0]} ({dominant[1]:.2f})")

    intensity = engine.get_emotion_intensity("user1")
    print(f"   Intensity: {intensity.name}")
    print()

    # 3. Model Perspective
    print("3. MODEL PERSPECTIVE:")
    print("-" * 40)

    cognitive = engine.model_perspective(
        "user1",
        PerspectiveType.COGNITIVE,
        beliefs={"task_is_difficult": True, "needs_help": True},
        goals=["complete_task", "reduce_stress"],
        concerns=["deadline", "quality"]
    )

    print(f"   Entity: {cognitive.entity_id}")
    print(f"   Type: {cognitive.perspective_type.value}")
    print(f"   Beliefs: {cognitive.beliefs}")
    print(f"   Goals: {cognitive.goals}")
    print()

    # 4. Infer from Perspective
    print("4. INFER FROM PERSPECTIVE:")
    print("-" * 40)

    belief = engine.infer_belief("user1", "needs_help")
    print(f"   needs_help: {belief}")

    motivational = engine.model_perspective(
        "user1",
        PerspectiveType.MOTIVATIONAL,
        goals=["succeed", "learn"]
    )

    goal = engine.infer_goal("user1")
    print(f"   Primary goal: {goal}")
    print()

    # 5. Recognize Affect
    print("5. RECOGNIZE AFFECT:")
    print("-" * 40)

    text = "I'm really frustrated and worried about this deadline."
    signal = engine.recognize_affect(text, "user1")

    print(f"   Text: '{text}'")
    print(f"   Emotions detected: {signal.emotions_detected}")
    print(f"   Sentiment: {signal.sentiment:.2f}")
    print(f"   Confidence: {signal.confidence:.2f}")
    print()

    # 6. Update Emotions
    print("6. UPDATE EMOTIONS:")
    print("-" * 40)

    updated = engine.update_emotions("user1", {
        EmotionType.ANGER.value: 0.6
    })

    print(f"   Updated emotions: {updated.emotions}")
    dominant = engine.get_dominant_emotion("user1")
    if dominant:
        print(f"   New dominant: {dominant[0]} ({dominant[1]:.2f})")
    print()

    # 7. Set Social Context
    print("7. SET SOCIAL CONTEXT:")
    print("-" * 40)

    context = engine.set_context(
        "session1",
        participants=["user1", "agent"],
        relationship_type="support",
        formality=0.3
    )

    print(f"   Context: {context.context_id}")
    print(f"   Participants: {context.participants}")
    print(f"   Relationship: {context.relationship_type}")
    print(f"   Formality: {context.formality}")
    print()

    # 8. Generate Response
    print("8. GENERATE EMPATHIC RESPONSE:")
    print("-" * 40)

    response = engine.generate_response("user1", "session1")

    print(f"   Type: {response.response_type.value}")
    print(f"   Content: {response.content}")
    print(f"   Empathy Level: {response.empathy_level.name}")
    print()

    # 9. Generate Specific Responses
    print("9. SPECIFIC RESPONSES:")
    print("-" * 40)

    ack = engine.generate_acknowledgment(EmotionType.FRUSTRATION if hasattr(EmotionType, 'FRUSTRATION') else EmotionType.ANGER)
    print(f"   Acknowledgment: {ack.content}")

    val = engine.generate_validation(EmotionType.FEAR)
    print(f"   Validation: {val.content}")

    sup = engine.generate_support(EmotionType.SADNESS)
    print(f"   Support: {sup.content}")
    print()

    # 10. Compute Empathy Level
    print("10. COMPUTE EMPATHY LEVEL:")
    print("-" * 40)

    empathy_level = engine.compute_empathy_level("user1")
    print(f"   Empathy Level: {empathy_level.name}")
    print()

    # 11. Compare Perspectives
    print("11. COMPARE PERSPECTIVES:")
    print("-" * 40)

    engine.model_perspective(
        "user2",
        PerspectiveType.COGNITIVE,
        beliefs={"task_is_difficult": True, "can_do_it": True}
    )

    similarity = engine.compare_perspectives("user1", "user2")
    print(f"   Perspective similarity: {similarity:.2f}")
    print()

    # 12. Emotion Decay
    print("12. EMOTION DECAY:")
    print("-" * 40)

    print(f"   Before decay: {engine.get_emotional_state('user1').emotions}")

    engine.decay_emotions("user1")

    print(f"   After decay: {engine.get_emotional_state('user1').emotions}")
    print()

    # 13. Sentiment Analysis
    print("13. SENTIMENT ANALYSIS:")
    print("-" * 40)

    texts = [
        "This is wonderful, I love it!",
        "This is terrible and I hate it.",
        "The weather is nice today."
    ]

    for text in texts:
        sentiment = engine.get_sentiment(text)
        print(f"   '{text[:30]}...': {sentiment:.2f}")
    print()

    # 14. Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Empathy Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
