#!/usr/bin/env python3
"""
BAEL - Emotion Engine
Advanced emotional modeling and affective computing.

Features:
- Emotion detection and classification
- Emotional state management
- Mood modeling
- Sentiment analysis
- Emotional expression
- Empathy simulation
- Emotional regulation
- Affective memory
"""

import asyncio
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

class EmotionType(Enum):
    """Basic emotion types (Ekman's model)."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"


class EmotionIntensity(Enum):
    """Emotion intensity levels."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    EXTREME = 4


class MoodType(Enum):
    """Mood types (longer-term emotional states)."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    CALM = "calm"
    ANXIOUS = "anxious"
    DEPRESSED = "depressed"


class SentimentPolarity(Enum):
    """Sentiment polarity."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class RegulationStrategy(Enum):
    """Emotion regulation strategies."""
    SUPPRESSION = "suppression"
    REAPPRAISAL = "reappraisal"
    DISTRACTION = "distraction"
    ACCEPTANCE = "acceptance"
    EXPRESSION = "expression"


class ExpressionType(Enum):
    """Emotional expression types."""
    VERBAL = "verbal"
    FACIAL = "facial"
    BEHAVIORAL = "behavioral"
    PHYSIOLOGICAL = "physiological"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Emotion:
    """Individual emotion instance."""
    emotion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    emotion_type: EmotionType = EmotionType.NEUTRAL
    intensity: float = 0.0  # 0.0 to 1.0
    valence: float = 0.0    # -1.0 to 1.0 (negative to positive)
    arousal: float = 0.0    # 0.0 to 1.0 (calm to excited)
    dominance: float = 0.5  # 0.0 to 1.0 (submissive to dominant)
    source: str = ""
    trigger: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    duration: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmotionalState:
    """Current emotional state."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    primary_emotion: EmotionType = EmotionType.NEUTRAL
    emotions: Dict[EmotionType, float] = field(default_factory=dict)
    valence: float = 0.0
    arousal: float = 0.0
    mood: MoodType = MoodType.NEUTRAL
    stability: float = 1.0  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Mood:
    """Mood state."""
    mood_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mood_type: MoodType = MoodType.NEUTRAL
    intensity: float = 0.5
    duration: timedelta = field(default_factory=lambda: timedelta(hours=1))
    started_at: datetime = field(default_factory=datetime.now)


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    text: str = ""
    polarity: SentimentPolarity = SentimentPolarity.NEUTRAL
    score: float = 0.0  # -1.0 to 1.0
    confidence: float = 0.0
    emotions: Dict[EmotionType, float] = field(default_factory=dict)


@dataclass
class EmotionalExpression:
    """Emotional expression."""
    expression_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    expression_type: ExpressionType = ExpressionType.VERBAL
    emotion: EmotionType = EmotionType.NEUTRAL
    content: str = ""
    intensity: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EmotionMemory:
    """Emotional memory entry."""
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event: str = ""
    emotion: EmotionType = EmotionType.NEUTRAL
    intensity: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)
    recall_count: int = 0


@dataclass
class EmotionStats:
    """Emotion statistics."""
    total_emotions: int = 0
    avg_valence: float = 0.0
    avg_arousal: float = 0.0
    dominant_emotion: EmotionType = EmotionType.NEUTRAL
    emotion_counts: Dict[EmotionType, int] = field(default_factory=dict)


# =============================================================================
# EMOTION WHEEL (Plutchik)
# =============================================================================

class EmotionWheel:
    """Plutchik's emotion wheel for complex emotions."""

    # Opposite emotions
    OPPOSITES = {
        EmotionType.JOY: EmotionType.SADNESS,
        EmotionType.SADNESS: EmotionType.JOY,
        EmotionType.ANGER: EmotionType.FEAR,
        EmotionType.FEAR: EmotionType.ANGER,
        EmotionType.TRUST: EmotionType.DISGUST,
        EmotionType.DISGUST: EmotionType.TRUST,
        EmotionType.SURPRISE: EmotionType.ANTICIPATION,
        EmotionType.ANTICIPATION: EmotionType.SURPRISE,
    }

    # Adjacent emotions combine to form complex emotions
    DYADS = {
        (EmotionType.JOY, EmotionType.TRUST): "love",
        (EmotionType.TRUST, EmotionType.FEAR): "submission",
        (EmotionType.FEAR, EmotionType.SURPRISE): "awe",
        (EmotionType.SURPRISE, EmotionType.SADNESS): "disapproval",
        (EmotionType.SADNESS, EmotionType.DISGUST): "remorse",
        (EmotionType.DISGUST, EmotionType.ANGER): "contempt",
        (EmotionType.ANGER, EmotionType.ANTICIPATION): "aggressiveness",
        (EmotionType.ANTICIPATION, EmotionType.JOY): "optimism",
    }

    # Emotion intensities
    INTENSITIES = {
        EmotionType.JOY: ["serenity", "joy", "ecstasy"],
        EmotionType.SADNESS: ["pensiveness", "sadness", "grief"],
        EmotionType.ANGER: ["annoyance", "anger", "rage"],
        EmotionType.FEAR: ["apprehension", "fear", "terror"],
        EmotionType.TRUST: ["acceptance", "trust", "admiration"],
        EmotionType.DISGUST: ["boredom", "disgust", "loathing"],
        EmotionType.SURPRISE: ["distraction", "surprise", "amazement"],
        EmotionType.ANTICIPATION: ["interest", "anticipation", "vigilance"],
    }

    @classmethod
    def get_opposite(cls, emotion: EmotionType) -> Optional[EmotionType]:
        """Get opposite emotion."""
        return cls.OPPOSITES.get(emotion)

    @classmethod
    def combine(
        cls,
        emotion1: EmotionType,
        emotion2: EmotionType
    ) -> Optional[str]:
        """Combine emotions to form complex emotion."""
        key = (emotion1, emotion2)
        if key in cls.DYADS:
            return cls.DYADS[key]

        # Try reverse order
        key = (emotion2, emotion1)
        return cls.DYADS.get(key)

    @classmethod
    def get_intensity_word(
        cls,
        emotion: EmotionType,
        intensity: float
    ) -> str:
        """Get word for intensity level."""
        if emotion not in cls.INTENSITIES:
            return emotion.value

        words = cls.INTENSITIES[emotion]

        if intensity < 0.33:
            return words[0]
        elif intensity < 0.66:
            return words[1]
        else:
            return words[2]


# =============================================================================
# EMOTION DETECTOR
# =============================================================================

class EmotionDetector:
    """Detect emotions from text."""

    # Emotion keywords
    EMOTION_KEYWORDS = {
        EmotionType.JOY: [
            "happy", "joyful", "glad", "delighted", "pleased",
            "cheerful", "elated", "ecstatic", "thrilled", "excited"
        ],
        EmotionType.SADNESS: [
            "sad", "unhappy", "depressed", "gloomy", "melancholy",
            "sorrowful", "miserable", "dejected", "heartbroken", "down"
        ],
        EmotionType.ANGER: [
            "angry", "mad", "furious", "enraged", "irritated",
            "annoyed", "frustrated", "hostile", "outraged", "livid"
        ],
        EmotionType.FEAR: [
            "afraid", "scared", "fearful", "terrified", "anxious",
            "worried", "nervous", "panicked", "horrified", "frightened"
        ],
        EmotionType.SURPRISE: [
            "surprised", "amazed", "astonished", "shocked", "stunned",
            "startled", "astounded", "bewildered", "dumbfounded", "wow"
        ],
        EmotionType.DISGUST: [
            "disgusted", "revolted", "repulsed", "nauseated", "sick",
            "gross", "awful", "horrible", "yuck", "ugh"
        ],
        EmotionType.TRUST: [
            "trusting", "confident", "secure", "believing", "faithful",
            "loyal", "reliable", "honest", "sincere", "devoted"
        ],
        EmotionType.ANTICIPATION: [
            "anticipating", "expecting", "hopeful", "eager", "looking forward",
            "excited about", "waiting", "preparing", "ready", "planning"
        ],
    }

    def detect(self, text: str) -> Dict[EmotionType, float]:
        """Detect emotions in text."""
        text_lower = text.lower()
        scores: Dict[EmotionType, float] = {}

        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                # Normalize score (max 1.0)
                scores[emotion] = min(count / 3.0, 1.0)

        return scores

    def get_primary_emotion(self, text: str) -> Tuple[EmotionType, float]:
        """Get primary emotion from text."""
        scores = self.detect(text)

        if not scores:
            return EmotionType.NEUTRAL, 0.0

        primary = max(scores.items(), key=lambda x: x[1])
        return primary[0], primary[1]

    def detect_valence(self, text: str) -> float:
        """Detect emotional valence (-1 to 1)."""
        scores = self.detect(text)

        positive = sum(
            scores.get(e, 0) for e in
            [EmotionType.JOY, EmotionType.TRUST, EmotionType.ANTICIPATION]
        )

        negative = sum(
            scores.get(e, 0) for e in
            [EmotionType.SADNESS, EmotionType.ANGER, EmotionType.FEAR, EmotionType.DISGUST]
        )

        total = positive + negative
        if total == 0:
            return 0.0

        return (positive - negative) / total


# =============================================================================
# SENTIMENT ANALYZER
# =============================================================================

class SentimentAnalyzer:
    """Analyze sentiment in text."""

    POSITIVE_WORDS = {
        "good", "great", "excellent", "amazing", "wonderful",
        "fantastic", "awesome", "love", "like", "best",
        "beautiful", "perfect", "happy", "joy", "success",
        "positive", "brilliant", "outstanding", "superb", "nice"
    }

    NEGATIVE_WORDS = {
        "bad", "terrible", "awful", "horrible", "worst",
        "hate", "dislike", "poor", "failure", "ugly",
        "negative", "wrong", "sad", "angry", "fear",
        "disappointing", "frustrating", "annoying", "boring", "dumb"
    }

    INTENSIFIERS = {
        "very": 1.5,
        "extremely": 2.0,
        "really": 1.3,
        "so": 1.4,
        "absolutely": 1.8,
        "completely": 1.6,
        "totally": 1.5,
        "quite": 1.2,
    }

    NEGATORS = {"not", "no", "never", "neither", "nobody", "nothing", "none"}

    def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment."""
        words = text.lower().split()

        positive_score = 0.0
        negative_score = 0.0
        negate_next = False
        intensity = 1.0

        for word in words:
            # Check for negators
            if word in self.NEGATORS:
                negate_next = True
                continue

            # Check for intensifiers
            if word in self.INTENSIFIERS:
                intensity = self.INTENSIFIERS[word]
                continue

            # Check sentiment
            is_positive = word in self.POSITIVE_WORDS
            is_negative = word in self.NEGATIVE_WORDS

            if negate_next:
                is_positive, is_negative = is_negative, is_positive
                negate_next = False

            if is_positive:
                positive_score += intensity
            elif is_negative:
                negative_score += intensity

            intensity = 1.0  # Reset intensity

        total = positive_score + negative_score

        if total == 0:
            polarity = SentimentPolarity.NEUTRAL
            score = 0.0
        elif positive_score > negative_score * 1.2:
            polarity = SentimentPolarity.POSITIVE
            score = positive_score / (positive_score + negative_score)
        elif negative_score > positive_score * 1.2:
            polarity = SentimentPolarity.NEGATIVE
            score = -negative_score / (positive_score + negative_score)
        else:
            polarity = SentimentPolarity.MIXED
            score = (positive_score - negative_score) / total

        return SentimentResult(
            text=text,
            polarity=polarity,
            score=score,
            confidence=min(total / 5.0, 1.0)
        )


# =============================================================================
# MOOD MANAGER
# =============================================================================

class MoodManager:
    """Manage mood states."""

    def __init__(self):
        self._current_mood = Mood()
        self._mood_history: List[Mood] = []
        self._emotion_buffer: deque = deque(maxlen=100)

    def update_mood(self, emotions: List[Emotion]) -> MoodType:
        """Update mood based on emotions."""
        for emotion in emotions:
            self._emotion_buffer.append(emotion)

        if not self._emotion_buffer:
            return MoodType.NEUTRAL

        # Calculate average valence and arousal
        avg_valence = sum(e.valence for e in self._emotion_buffer) / len(self._emotion_buffer)
        avg_arousal = sum(e.arousal for e in self._emotion_buffer) / len(self._emotion_buffer)

        # Determine mood
        if avg_valence > 0.3:
            if avg_arousal > 0.5:
                mood_type = MoodType.EXCITED
            else:
                mood_type = MoodType.POSITIVE
        elif avg_valence < -0.3:
            if avg_arousal > 0.5:
                mood_type = MoodType.ANXIOUS
            else:
                mood_type = MoodType.DEPRESSED
        else:
            if avg_arousal > 0.5:
                mood_type = MoodType.NEUTRAL
            else:
                mood_type = MoodType.CALM

        # Update mood
        new_mood = Mood(
            mood_type=mood_type,
            intensity=abs(avg_valence)
        )

        self._mood_history.append(self._current_mood)
        self._current_mood = new_mood

        return mood_type

    def get_mood(self) -> Mood:
        """Get current mood."""
        return self._current_mood

    def get_mood_history(self, n: int = 10) -> List[Mood]:
        """Get mood history."""
        return self._mood_history[-n:]


# =============================================================================
# EMOTION REGULATOR
# =============================================================================

class EmotionRegulator:
    """Regulate emotions."""

    def __init__(self):
        self._strategies: Dict[RegulationStrategy, Callable[[Emotion], Emotion]] = {
            RegulationStrategy.SUPPRESSION: self._suppress,
            RegulationStrategy.REAPPRAISAL: self._reappraise,
            RegulationStrategy.DISTRACTION: self._distract,
            RegulationStrategy.ACCEPTANCE: self._accept,
            RegulationStrategy.EXPRESSION: self._express,
        }

    def regulate(
        self,
        emotion: Emotion,
        strategy: RegulationStrategy = RegulationStrategy.REAPPRAISAL
    ) -> Emotion:
        """Regulate emotion using strategy."""
        if strategy in self._strategies:
            return self._strategies[strategy](emotion)
        return emotion

    def _suppress(self, emotion: Emotion) -> Emotion:
        """Suppress emotion (reduce intensity)."""
        return Emotion(
            emotion_type=emotion.emotion_type,
            intensity=emotion.intensity * 0.3,
            valence=emotion.valence * 0.3,
            arousal=emotion.arousal * 0.3,
            source=emotion.source,
            trigger=f"suppressed: {emotion.trigger}"
        )

    def _reappraise(self, emotion: Emotion) -> Emotion:
        """Reappraise emotion (change interpretation)."""
        # Negative emotions become less negative
        new_valence = emotion.valence * 0.5 if emotion.valence < 0 else emotion.valence

        return Emotion(
            emotion_type=emotion.emotion_type,
            intensity=emotion.intensity * 0.7,
            valence=new_valence,
            arousal=emotion.arousal * 0.7,
            source=emotion.source,
            trigger=f"reappraised: {emotion.trigger}"
        )

    def _distract(self, emotion: Emotion) -> Emotion:
        """Distract from emotion."""
        return Emotion(
            emotion_type=EmotionType.NEUTRAL,
            intensity=0.3,
            valence=0.0,
            arousal=0.2,
            source="distraction",
            trigger=f"distracted from: {emotion.trigger}"
        )

    def _accept(self, emotion: Emotion) -> Emotion:
        """Accept emotion (no change, but marked)."""
        return Emotion(
            emotion_type=emotion.emotion_type,
            intensity=emotion.intensity,
            valence=emotion.valence,
            arousal=emotion.arousal * 0.8,  # Slightly calmer
            source=emotion.source,
            trigger=f"accepted: {emotion.trigger}"
        )

    def _express(self, emotion: Emotion) -> Emotion:
        """Express emotion (release intensity)."""
        return Emotion(
            emotion_type=emotion.emotion_type,
            intensity=emotion.intensity * 0.5,
            valence=emotion.valence,
            arousal=emotion.arousal * 0.6,
            source=emotion.source,
            trigger=f"expressed: {emotion.trigger}"
        )

    def recommend_strategy(self, emotion: Emotion) -> RegulationStrategy:
        """Recommend regulation strategy."""
        if emotion.intensity > 0.8:
            if emotion.valence < -0.5:
                return RegulationStrategy.REAPPRAISAL
            else:
                return RegulationStrategy.EXPRESSION

        elif emotion.arousal > 0.7:
            return RegulationStrategy.DISTRACTION

        elif emotion.valence < -0.3:
            return RegulationStrategy.ACCEPTANCE

        return RegulationStrategy.ACCEPTANCE


# =============================================================================
# EMPATHY SIMULATOR
# =============================================================================

class EmpathySimulator:
    """Simulate empathetic responses."""

    def __init__(self):
        self._empathy_level = 0.7  # 0.0 to 1.0

    def empathize(self, emotion: Emotion) -> Emotion:
        """Generate empathetic response."""
        # Mirror emotion with reduced intensity
        return Emotion(
            emotion_type=emotion.emotion_type,
            intensity=emotion.intensity * self._empathy_level * 0.5,
            valence=emotion.valence * self._empathy_level,
            arousal=emotion.arousal * self._empathy_level * 0.7,
            source="empathy",
            trigger=f"empathy for: {emotion.trigger}"
        )

    def generate_response(self, emotion: Emotion) -> str:
        """Generate empathetic verbal response."""
        emotion_type = emotion.emotion_type
        intensity = emotion.intensity

        if emotion_type == EmotionType.JOY:
            if intensity > 0.7:
                return "That's wonderful! I'm so happy for you!"
            return "That's great to hear!"

        elif emotion_type == EmotionType.SADNESS:
            if intensity > 0.7:
                return "I'm truly sorry. That must be very difficult."
            return "I understand. It's okay to feel this way."

        elif emotion_type == EmotionType.ANGER:
            if intensity > 0.7:
                return "I can see this is really frustrating. That's completely valid."
            return "I understand why you might feel that way."

        elif emotion_type == EmotionType.FEAR:
            if intensity > 0.7:
                return "That sounds very scary. You're not alone in this."
            return "It's natural to feel concerned. Let's work through this together."

        elif emotion_type == EmotionType.SURPRISE:
            return "Wow, that is surprising! I can see why you're taken aback."

        elif emotion_type == EmotionType.DISGUST:
            return "I understand your reaction. That does sound unpleasant."

        elif emotion_type == EmotionType.TRUST:
            return "I appreciate your confidence. I'll do my best to help."

        elif emotion_type == EmotionType.ANTICIPATION:
            return "That's exciting! I hope it goes well for you."

        return "I hear you. How can I help?"

    def set_empathy_level(self, level: float) -> None:
        """Set empathy level."""
        self._empathy_level = max(0.0, min(1.0, level))


# =============================================================================
# AFFECTIVE MEMORY
# =============================================================================

class AffectiveMemory:
    """Store emotional memories."""

    def __init__(self, capacity: int = 1000):
        self._memories: Dict[str, EmotionMemory] = {}
        self._by_emotion: Dict[EmotionType, List[str]] = defaultdict(list)
        self._capacity = capacity

    def store(
        self,
        event: str,
        emotion: EmotionType,
        intensity: float
    ) -> EmotionMemory:
        """Store emotional memory."""
        memory = EmotionMemory(
            event=event,
            emotion=emotion,
            intensity=intensity
        )

        self._memories[memory.memory_id] = memory
        self._by_emotion[emotion].append(memory.memory_id)

        # Enforce capacity
        if len(self._memories) > self._capacity:
            # Remove oldest
            oldest = min(self._memories.values(), key=lambda m: m.timestamp)
            self._remove(oldest.memory_id)

        return memory

    def _remove(self, memory_id: str) -> None:
        """Remove memory."""
        if memory_id in self._memories:
            memory = self._memories[memory_id]
            self._by_emotion[memory.emotion].remove(memory_id)
            del self._memories[memory_id]

    def recall(self, memory_id: str) -> Optional[EmotionMemory]:
        """Recall memory."""
        if memory_id in self._memories:
            memory = self._memories[memory_id]
            memory.recall_count += 1
            return memory
        return None

    def recall_by_emotion(
        self,
        emotion: EmotionType,
        n: int = 5
    ) -> List[EmotionMemory]:
        """Recall memories by emotion."""
        memory_ids = self._by_emotion.get(emotion, [])[-n:]

        memories = []
        for mid in memory_ids:
            memory = self.recall(mid)
            if memory:
                memories.append(memory)

        return memories

    def search(self, query: str) -> List[EmotionMemory]:
        """Search memories."""
        query_lower = query.lower()
        return [
            m for m in self._memories.values()
            if query_lower in m.event.lower()
        ]

    def get_most_intense(self, n: int = 5) -> List[EmotionMemory]:
        """Get most intense memories."""
        return sorted(
            self._memories.values(),
            key=lambda m: m.intensity,
            reverse=True
        )[:n]


# =============================================================================
# EMOTION ENGINE
# =============================================================================

class EmotionEngine:
    """
    Emotion Engine for BAEL.

    Advanced emotional modeling and affective computing.
    """

    def __init__(self, empathy_level: float = 0.7):
        self._detector = EmotionDetector()
        self._analyzer = SentimentAnalyzer()
        self._mood_manager = MoodManager()
        self._regulator = EmotionRegulator()
        self._empathy = EmpathySimulator()
        self._memory = AffectiveMemory()
        self._current_state = EmotionalState()
        self._emotion_history: List[Emotion] = []
        self._stats = EmotionStats()

        self._empathy.set_empathy_level(empathy_level)

    # -------------------------------------------------------------------------
    # EMOTION DETECTION
    # -------------------------------------------------------------------------

    def detect_emotions(self, text: str) -> Dict[EmotionType, float]:
        """Detect emotions in text."""
        return self._detector.detect(text)

    def get_primary_emotion(self, text: str) -> Tuple[EmotionType, float]:
        """Get primary emotion from text."""
        return self._detector.get_primary_emotion(text)

    def create_emotion(
        self,
        emotion_type: EmotionType,
        intensity: float = 0.5,
        source: str = "",
        trigger: str = ""
    ) -> Emotion:
        """Create emotion instance."""
        # Calculate valence based on emotion type
        valence_map = {
            EmotionType.JOY: 0.8,
            EmotionType.TRUST: 0.5,
            EmotionType.ANTICIPATION: 0.3,
            EmotionType.SURPRISE: 0.1,
            EmotionType.NEUTRAL: 0.0,
            EmotionType.FEAR: -0.4,
            EmotionType.SADNESS: -0.6,
            EmotionType.DISGUST: -0.5,
            EmotionType.ANGER: -0.7,
        }

        arousal_map = {
            EmotionType.ANGER: 0.8,
            EmotionType.FEAR: 0.7,
            EmotionType.JOY: 0.6,
            EmotionType.SURPRISE: 0.6,
            EmotionType.ANTICIPATION: 0.5,
            EmotionType.DISGUST: 0.4,
            EmotionType.TRUST: 0.3,
            EmotionType.SADNESS: 0.2,
            EmotionType.NEUTRAL: 0.1,
        }

        emotion = Emotion(
            emotion_type=emotion_type,
            intensity=intensity,
            valence=valence_map.get(emotion_type, 0.0) * intensity,
            arousal=arousal_map.get(emotion_type, 0.5) * intensity,
            source=source,
            trigger=trigger
        )

        self._add_emotion(emotion)
        return emotion

    def _add_emotion(self, emotion: Emotion) -> None:
        """Add emotion to history and update state."""
        self._emotion_history.append(emotion)
        self._update_state(emotion)
        self._update_stats(emotion)

    def _update_state(self, emotion: Emotion) -> None:
        """Update emotional state."""
        # Update emotion intensities
        self._current_state.emotions[emotion.emotion_type] = emotion.intensity

        # Update primary emotion
        if emotion.intensity > 0.5:
            self._current_state.primary_emotion = emotion.emotion_type

        # Update valence and arousal (running average)
        alpha = 0.3
        self._current_state.valence = (
            (1 - alpha) * self._current_state.valence +
            alpha * emotion.valence
        )
        self._current_state.arousal = (
            (1 - alpha) * self._current_state.arousal +
            alpha * emotion.arousal
        )

        self._current_state.timestamp = datetime.now()

    def _update_stats(self, emotion: Emotion) -> None:
        """Update statistics."""
        self._stats.total_emotions += 1

        # Update counts
        if emotion.emotion_type not in self._stats.emotion_counts:
            self._stats.emotion_counts[emotion.emotion_type] = 0
        self._stats.emotion_counts[emotion.emotion_type] += 1

        # Update averages
        n = self._stats.total_emotions
        self._stats.avg_valence = (
            (self._stats.avg_valence * (n - 1) + emotion.valence) / n
        )
        self._stats.avg_arousal = (
            (self._stats.avg_arousal * (n - 1) + emotion.arousal) / n
        )

        # Update dominant
        self._stats.dominant_emotion = max(
            self._stats.emotion_counts.items(),
            key=lambda x: x[1]
        )[0]

    # -------------------------------------------------------------------------
    # SENTIMENT ANALYSIS
    # -------------------------------------------------------------------------

    def analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze sentiment in text."""
        result = self._analyzer.analyze(text)

        # Add detected emotions
        result.emotions = self.detect_emotions(text)

        return result

    def get_valence(self, text: str) -> float:
        """Get emotional valence from text."""
        return self._detector.detect_valence(text)

    # -------------------------------------------------------------------------
    # MOOD
    # -------------------------------------------------------------------------

    def update_mood(self) -> MoodType:
        """Update mood based on recent emotions."""
        recent = self._emotion_history[-20:]
        return self._mood_manager.update_mood(recent)

    def get_mood(self) -> Mood:
        """Get current mood."""
        return self._mood_manager.get_mood()

    def get_mood_history(self, n: int = 10) -> List[Mood]:
        """Get mood history."""
        return self._mood_manager.get_mood_history(n)

    # -------------------------------------------------------------------------
    # REGULATION
    # -------------------------------------------------------------------------

    def regulate(
        self,
        emotion: Emotion,
        strategy: Optional[RegulationStrategy] = None
    ) -> Emotion:
        """Regulate emotion."""
        if strategy is None:
            strategy = self._regulator.recommend_strategy(emotion)

        return self._regulator.regulate(emotion, strategy)

    def recommend_regulation(self, emotion: Emotion) -> RegulationStrategy:
        """Recommend regulation strategy."""
        return self._regulator.recommend_strategy(emotion)

    # -------------------------------------------------------------------------
    # EMPATHY
    # -------------------------------------------------------------------------

    def empathize(self, emotion: Emotion) -> Emotion:
        """Generate empathetic response."""
        return self._empathy.empathize(emotion)

    def generate_empathetic_response(self, emotion: Emotion) -> str:
        """Generate empathetic verbal response."""
        return self._empathy.generate_response(emotion)

    def set_empathy_level(self, level: float) -> None:
        """Set empathy level."""
        self._empathy.set_empathy_level(level)

    # -------------------------------------------------------------------------
    # MEMORY
    # -------------------------------------------------------------------------

    def remember(
        self,
        event: str,
        emotion: EmotionType,
        intensity: float
    ) -> EmotionMemory:
        """Store emotional memory."""
        return self._memory.store(event, emotion, intensity)

    def recall_by_emotion(
        self,
        emotion: EmotionType,
        n: int = 5
    ) -> List[EmotionMemory]:
        """Recall memories by emotion."""
        return self._memory.recall_by_emotion(emotion, n)

    def search_memories(self, query: str) -> List[EmotionMemory]:
        """Search emotional memories."""
        return self._memory.search(query)

    def get_intense_memories(self, n: int = 5) -> List[EmotionMemory]:
        """Get most intense memories."""
        return self._memory.get_most_intense(n)

    # -------------------------------------------------------------------------
    # STATE
    # -------------------------------------------------------------------------

    def get_state(self) -> EmotionalState:
        """Get current emotional state."""
        return self._current_state

    def get_history(self, n: int = 10) -> List[Emotion]:
        """Get emotion history."""
        return self._emotion_history[-n:]

    def get_stats(self) -> EmotionStats:
        """Get emotion statistics."""
        return self._stats

    # -------------------------------------------------------------------------
    # EMOTION WHEEL
    # -------------------------------------------------------------------------

    def get_opposite(self, emotion: EmotionType) -> Optional[EmotionType]:
        """Get opposite emotion."""
        return EmotionWheel.get_opposite(emotion)

    def combine_emotions(
        self,
        emotion1: EmotionType,
        emotion2: EmotionType
    ) -> Optional[str]:
        """Combine emotions."""
        return EmotionWheel.combine(emotion1, emotion2)

    def get_intensity_word(
        self,
        emotion: EmotionType,
        intensity: float
    ) -> str:
        """Get intensity word."""
        return EmotionWheel.get_intensity_word(emotion, intensity)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Emotion Engine."""
    print("=" * 70)
    print("BAEL - EMOTION ENGINE DEMO")
    print("Advanced Emotional Modeling and Affective Computing")
    print("=" * 70)
    print()

    engine = EmotionEngine(empathy_level=0.8)

    # 1. Detect Emotions
    print("1. DETECT EMOTIONS:")
    print("-" * 40)

    text = "I am so happy and excited about this wonderful news!"
    emotions = engine.detect_emotions(text)

    print(f"   Text: \"{text}\"")
    print(f"   Detected emotions:")
    for etype, intensity in emotions.items():
        print(f"     {etype.value}: {intensity:.2f}")
    print()

    # 2. Primary Emotion
    print("2. PRIMARY EMOTION:")
    print("-" * 40)

    primary, intensity = engine.get_primary_emotion(text)

    print(f"   Primary: {primary.value}")
    print(f"   Intensity: {intensity:.2f}")
    print()

    # 3. Create Emotion
    print("3. CREATE EMOTION:")
    print("-" * 40)

    emotion = engine.create_emotion(
        emotion_type=EmotionType.JOY,
        intensity=0.8,
        source="success",
        trigger="completed task"
    )

    print(f"   Type: {emotion.emotion_type.value}")
    print(f"   Intensity: {emotion.intensity:.2f}")
    print(f"   Valence: {emotion.valence:.2f}")
    print(f"   Arousal: {emotion.arousal:.2f}")
    print()

    # 4. Sentiment Analysis
    print("4. SENTIMENT ANALYSIS:")
    print("-" * 40)

    text = "This is really terrible and frustrating!"
    sentiment = engine.analyze_sentiment(text)

    print(f"   Text: \"{text}\"")
    print(f"   Polarity: {sentiment.polarity.value}")
    print(f"   Score: {sentiment.score:.2f}")
    print(f"   Confidence: {sentiment.confidence:.2f}")
    print()

    # 5. Emotional Valence
    print("5. EMOTIONAL VALENCE:")
    print("-" * 40)

    texts = [
        "I love this amazing product!",
        "This is awful and disappointing.",
        "It's okay, nothing special."
    ]

    for t in texts:
        valence = engine.get_valence(t)
        print(f"   \"{t[:30]}...\" -> {valence:.2f}")
    print()

    # 6. Mood Management
    print("6. MOOD MANAGEMENT:")
    print("-" * 40)

    # Create several emotions
    engine.create_emotion(EmotionType.JOY, 0.7, "event", "good news")
    engine.create_emotion(EmotionType.TRUST, 0.6, "relationship", "support")

    mood_type = engine.update_mood()
    mood = engine.get_mood()

    print(f"   Current mood: {mood.mood_type.value}")
    print(f"   Intensity: {mood.intensity:.2f}")
    print()

    # 7. Emotion Regulation
    print("7. EMOTION REGULATION:")
    print("-" * 40)

    negative_emotion = engine.create_emotion(
        EmotionType.ANGER,
        intensity=0.9,
        trigger="unfair situation"
    )

    recommended = engine.recommend_regulation(negative_emotion)
    regulated = engine.regulate(negative_emotion, recommended)

    print(f"   Original intensity: {negative_emotion.intensity:.2f}")
    print(f"   Recommended strategy: {recommended.value}")
    print(f"   Regulated intensity: {regulated.intensity:.2f}")
    print()

    # 8. Empathy
    print("8. EMPATHY:")
    print("-" * 40)

    sad_emotion = engine.create_emotion(
        EmotionType.SADNESS,
        intensity=0.8,
        trigger="loss"
    )

    empathetic = engine.empathize(sad_emotion)
    response = engine.generate_empathetic_response(sad_emotion)

    print(f"   Input emotion: {sad_emotion.emotion_type.value} ({sad_emotion.intensity:.2f})")
    print(f"   Empathetic emotion: {empathetic.intensity:.2f}")
    print(f"   Response: \"{response}\"")
    print()

    # 9. Emotional Memory
    print("9. EMOTIONAL MEMORY:")
    print("-" * 40)

    engine.remember("graduation day", EmotionType.JOY, 0.95)
    engine.remember("job interview", EmotionType.FEAR, 0.7)
    engine.remember("birthday party", EmotionType.JOY, 0.8)

    joy_memories = engine.recall_by_emotion(EmotionType.JOY)

    print(f"   Stored memories: 3")
    print(f"   Joy memories: {len(joy_memories)}")
    for m in joy_memories:
        print(f"     - {m.event}: {m.intensity:.2f}")
    print()

    # 10. Emotion Wheel
    print("10. EMOTION WHEEL:")
    print("-" * 40)

    opposite = engine.get_opposite(EmotionType.JOY)
    combined = engine.combine_emotions(EmotionType.JOY, EmotionType.TRUST)
    intensity_word = engine.get_intensity_word(EmotionType.ANGER, 0.9)

    print(f"   Opposite of joy: {opposite.value if opposite else 'N/A'}")
    print(f"   Joy + Trust = {combined}")
    print(f"   High anger = {intensity_word}")
    print()

    # 11. Emotional State
    print("11. EMOTIONAL STATE:")
    print("-" * 40)

    state = engine.get_state()

    print(f"   Primary emotion: {state.primary_emotion.value}")
    print(f"   Valence: {state.valence:.2f}")
    print(f"   Arousal: {state.arousal:.2f}")
    print(f"   Active emotions: {len(state.emotions)}")
    print()

    # 12. Emotion History
    print("12. EMOTION HISTORY:")
    print("-" * 40)

    history = engine.get_history(5)

    for e in history:
        print(f"   {e.emotion_type.value}: {e.intensity:.2f} ({e.trigger})")
    print()

    # 13. Statistics
    print("13. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()

    print(f"   Total emotions: {stats.total_emotions}")
    print(f"   Avg valence: {stats.avg_valence:.2f}")
    print(f"   Avg arousal: {stats.avg_arousal:.2f}")
    print(f"   Dominant: {stats.dominant_emotion.value}")
    print()

    # 14. Multiple Sentiments
    print("14. MULTIPLE SENTIMENTS:")
    print("-" * 40)

    texts = [
        "This is absolutely wonderful!",
        "I'm not very happy about this.",
        "The weather is normal today."
    ]

    for t in texts:
        result = engine.analyze_sentiment(t)
        print(f"   \"{t[:25]}...\" -> {result.polarity.value} ({result.score:.2f})")
    print()

    # 15. Intense Memories
    print("15. INTENSE MEMORIES:")
    print("-" * 40)

    intense = engine.get_intense_memories(3)

    for m in intense:
        print(f"   {m.event}: {m.emotion.value} ({m.intensity:.2f})")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Emotion Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
