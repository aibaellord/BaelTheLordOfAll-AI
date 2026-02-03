"""
BAEL - Emotion & Sentiment Engine
Emotional intelligence and sentiment analysis for natural interactions.

Features:
- Emotional state detection
- Sentiment analysis
- Empathetic response generation
- Mood tracking
- Rapport building
"""

import asyncio
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Emotion")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class Emotion(Enum):
    """Basic emotions."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"


class Sentiment(Enum):
    """Sentiment categories."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class UserMood(Enum):
    """User mood states."""
    ENTHUSIASTIC = "enthusiastic"
    ENGAGED = "engaged"
    CURIOUS = "curious"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    IMPATIENT = "impatient"
    SATISFIED = "satisfied"


@dataclass
class EmotionalState:
    """Current emotional state."""
    primary_emotion: Emotion
    secondary_emotion: Optional[Emotion] = None
    sentiment: Sentiment = Sentiment.NEUTRAL
    intensity: float = 0.5  # 0-1
    confidence: float = 0.5  # 0-1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UserProfile:
    """User emotional profile."""
    mood_history: List[UserMood] = field(default_factory=list)
    sentiment_history: List[Sentiment] = field(default_factory=list)
    frustration_level: float = 0.0
    rapport_score: float = 0.5
    preferences: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SENTIMENT ANALYZER
# =============================================================================

class SentimentAnalyzer:
    """Analyzes sentiment in text."""

    def __init__(self):
        # Positive indicators
        self.positive_words = {
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'love', 'like', 'awesome', 'perfect', 'best', 'happy', 'thanks',
            'thank', 'appreciate', 'helpful', 'brilliant', 'superb', 'nice',
            'beautiful', 'incredible', 'outstanding', 'impressive', 'pleased'
        }

        # Negative indicators
        self.negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'hate', 'wrong', 'error',
            'fail', 'failed', 'failing', 'broken', 'bug', 'issue', 'problem',
            'frustrated', 'annoying', 'useless', 'stupid', 'waste', 'worse',
            'worst', 'ugly', 'confusing', 'confused', 'disappointed', 'slow'
        }

        # Intensifiers
        self.intensifiers = {
            'very', 'really', 'extremely', 'incredibly', 'absolutely',
            'totally', 'completely', 'highly', 'super', 'so'
        }

        # Negators
        self.negators = {'not', "n't", 'no', 'never', 'neither', 'nobody', 'none'}

    def analyze(self, text: str) -> Tuple[Sentiment, float]:
        """Analyze sentiment of text."""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        positive_score = 0
        negative_score = 0

        prev_negator = False
        prev_intensifier = False

        for i, word in enumerate(words):
            multiplier = 1.5 if prev_intensifier else 1.0

            if word in self.positive_words:
                if prev_negator:
                    negative_score += multiplier
                else:
                    positive_score += multiplier

            elif word in self.negative_words:
                if prev_negator:
                    positive_score += multiplier * 0.5  # Negated negative is weakly positive
                else:
                    negative_score += multiplier

            prev_negator = word in self.negators or word.endswith("n't")
            prev_intensifier = word in self.intensifiers

        # Calculate overall sentiment
        total = positive_score + negative_score
        if total == 0:
            return Sentiment.NEUTRAL, 0.5

        ratio = positive_score / total
        confidence = min(total / 10, 1.0)  # More words = more confidence

        if ratio >= 0.8:
            return Sentiment.VERY_POSITIVE, confidence
        elif ratio >= 0.6:
            return Sentiment.POSITIVE, confidence
        elif ratio >= 0.4:
            return Sentiment.NEUTRAL, confidence
        elif ratio >= 0.2:
            return Sentiment.NEGATIVE, confidence
        else:
            return Sentiment.VERY_NEGATIVE, confidence


# =============================================================================
# EMOTION DETECTOR
# =============================================================================

class EmotionDetector:
    """Detects emotions in text."""

    def __init__(self):
        self.emotion_patterns = {
            Emotion.JOY: [
                r'\b(happy|joy|excited|thrilled|delighted|glad|pleased)\b',
                r'(:\)|:-\)|😊|😀|🎉|❤️)',
                r'\b(love|wonderful|amazing|fantastic)\b'
            ],
            Emotion.SADNESS: [
                r'\b(sad|unhappy|depressed|disappointed|upset|sorry)\b',
                r'(:\(|:-\(|😢|😭)',
                r'\b(unfortunately|regret|miss)\b'
            ],
            Emotion.ANGER: [
                r'\b(angry|furious|annoyed|frustrated|mad|hate)\b',
                r'(>:\(|😠|😡)',
                r'\b(ridiculous|unacceptable|terrible)\b'
            ],
            Emotion.FEAR: [
                r'\b(afraid|scared|worried|anxious|nervous|concerned)\b',
                r'(😰|😨|😱)',
                r'\b(dangerous|risky|uncertain)\b'
            ],
            Emotion.SURPRISE: [
                r'\b(surprised|shocked|amazed|astonished|wow)\b',
                r'(😮|😲|🤯)',
                r'\b(unexpected|incredible|unbelievable)\b'
            ],
            Emotion.DISGUST: [
                r'\b(disgusted|gross|revolting|nauseating)\b',
                r'(🤮|🤢)',
                r'\b(horrible|repulsive|awful)\b'
            ],
            Emotion.TRUST: [
                r'\b(trust|believe|confident|rely|depend)\b',
                r'(🤝|💪)',
                r'\b(reliable|trustworthy|honest)\b'
            ],
            Emotion.ANTICIPATION: [
                r'\b(excited|anticipate|expect|hope|eager|looking forward)\b',
                r'(🤞|🙏)',
                r'\b(can\'t wait|soon|upcoming)\b'
            ]
        }

    def detect(self, text: str) -> EmotionalState:
        """Detect emotions in text."""
        text_lower = text.lower()
        emotion_scores = defaultdict(float)

        for emotion, patterns in self.emotion_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                emotion_scores[emotion] += len(matches)

        if not emotion_scores:
            return EmotionalState(
                primary_emotion=Emotion.NEUTRAL,
                sentiment=Sentiment.NEUTRAL,
                intensity=0.5,
                confidence=0.5
            )

        # Sort by score
        sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)

        primary = sorted_emotions[0][0]
        secondary = sorted_emotions[1][0] if len(sorted_emotions) > 1 else None

        total_score = sum(emotion_scores.values())
        intensity = min(sorted_emotions[0][1] / 3, 1.0)
        confidence = min(total_score / 5, 1.0)

        # Determine sentiment from emotion
        positive_emotions = {Emotion.JOY, Emotion.TRUST, Emotion.ANTICIPATION}
        negative_emotions = {Emotion.SADNESS, Emotion.ANGER, Emotion.FEAR, Emotion.DISGUST}

        if primary in positive_emotions:
            sentiment = Sentiment.POSITIVE if intensity < 0.7 else Sentiment.VERY_POSITIVE
        elif primary in negative_emotions:
            sentiment = Sentiment.NEGATIVE if intensity < 0.7 else Sentiment.VERY_NEGATIVE
        else:
            sentiment = Sentiment.NEUTRAL

        return EmotionalState(
            primary_emotion=primary,
            secondary_emotion=secondary,
            sentiment=sentiment,
            intensity=intensity,
            confidence=confidence
        )


# =============================================================================
# MOOD TRACKER
# =============================================================================

class MoodTracker:
    """Tracks user mood over time."""

    def __init__(self):
        self.profiles: Dict[str, UserProfile] = {}
        self.default_profile = UserProfile()

    def get_profile(self, user_id: str = "default") -> UserProfile:
        """Get or create user profile."""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile()
        return self.profiles[user_id]

    def update_mood(self, emotional_state: EmotionalState, user_id: str = "default") -> UserMood:
        """Update user mood based on emotional state."""
        profile = self.get_profile(user_id)

        # Map emotion to mood
        mood_mapping = {
            (Emotion.JOY, True): UserMood.ENTHUSIASTIC,
            (Emotion.JOY, False): UserMood.SATISFIED,
            (Emotion.ANGER, True): UserMood.FRUSTRATED,
            (Emotion.FEAR, False): UserMood.CONFUSED,
            (Emotion.ANTICIPATION, True): UserMood.ENTHUSIASTIC,
            (Emotion.ANTICIPATION, False): UserMood.CURIOUS,
            (Emotion.TRUST, False): UserMood.ENGAGED,
            (Emotion.SURPRISE, False): UserMood.CURIOUS,
        }

        high_intensity = emotional_state.intensity > 0.6
        mood = mood_mapping.get(
            (emotional_state.primary_emotion, high_intensity),
            UserMood.NEUTRAL
        )

        # Update history
        profile.mood_history.append(mood)
        profile.sentiment_history.append(emotional_state.sentiment)

        # Keep history bounded
        if len(profile.mood_history) > 50:
            profile.mood_history = profile.mood_history[-50:]
            profile.sentiment_history = profile.sentiment_history[-50:]

        # Update frustration level
        if mood == UserMood.FRUSTRATED:
            profile.frustration_level = min(profile.frustration_level + 0.2, 1.0)
        elif mood in [UserMood.SATISFIED, UserMood.ENTHUSIASTIC]:
            profile.frustration_level = max(profile.frustration_level - 0.3, 0.0)
        else:
            profile.frustration_level = max(profile.frustration_level - 0.1, 0.0)

        # Update rapport
        positive_moods = [UserMood.ENTHUSIASTIC, UserMood.SATISFIED, UserMood.ENGAGED]
        recent_moods = profile.mood_history[-10:]
        positive_count = sum(1 for m in recent_moods if m in positive_moods)
        profile.rapport_score = positive_count / max(len(recent_moods), 1)

        return mood


# =============================================================================
# EMPATHY ENGINE
# =============================================================================

class EmpathyEngine:
    """Generates empathetic responses."""

    def __init__(self, model_router=None):
        self.model_router = model_router
        self.response_templates = {
            UserMood.FRUSTRATED: [
                "I understand this can be frustrating. Let me help you work through this.",
                "I hear your frustration. Let's take a step back and approach this differently.",
                "I apologize for any confusion. Let me clarify and help you solve this."
            ],
            UserMood.CONFUSED: [
                "I can see this is confusing. Let me explain it more clearly.",
                "No worries, this can be tricky. Let me break it down step by step.",
                "Let me clarify that for you with a simpler explanation."
            ],
            UserMood.ENTHUSIASTIC: [
                "I love your enthusiasm! Let's dive deeper into this.",
                "That's great! Your excitement is contagious. Here's more...",
                "Wonderful! Let's build on that energy and explore further."
            ],
            UserMood.IMPATIENT: [
                "I'll get straight to the point.",
                "Let me give you a quick answer.",
                "Here's the direct solution:"
            ],
            UserMood.CURIOUS: [
                "Great question! Here's an interesting perspective...",
                "I'd be happy to explore that with you.",
                "That's a fascinating topic. Let me share some insights."
            ],
            UserMood.SATISFIED: [
                "Glad I could help!",
                "Happy to be of assistance.",
                "Great! Let me know if you need anything else."
            ]
        }

    def get_empathetic_prefix(self, mood: UserMood) -> str:
        """Get an empathetic response prefix."""
        import random
        templates = self.response_templates.get(mood, [])
        return random.choice(templates) if templates else ""

    async def enhance_response(
        self,
        response: str,
        emotional_state: EmotionalState,
        mood: UserMood,
        profile: UserProfile
    ) -> str:
        """Enhance response with empathy."""

        # High frustration needs acknowledgment
        if profile.frustration_level > 0.6:
            prefix = self.get_empathetic_prefix(UserMood.FRUSTRATED)
            response = f"{prefix}\n\n{response}"

        # Low rapport needs rapport building
        elif profile.rapport_score < 0.3:
            prefix = "I appreciate your patience. "
            response = f"{prefix}{response}"

        # Match energy for positive moods
        elif mood == UserMood.ENTHUSIASTIC:
            prefix = self.get_empathetic_prefix(UserMood.ENTHUSIASTIC)
            response = f"{prefix}\n\n{response}"

        # Be direct for impatient users
        elif mood == UserMood.IMPATIENT:
            # Strip unnecessary verbosity
            response = self._make_concise(response)

        return response

    def _make_concise(self, text: str) -> str:
        """Make response more concise."""
        # Remove filler phrases
        fillers = [
            "As I mentioned earlier,",
            "To be more specific,",
            "In other words,",
            "It's worth noting that",
            "As you may know,"
        ]
        for filler in fillers:
            text = text.replace(filler, "")
        return text.strip()


# =============================================================================
# EMOTIONAL INTELLIGENCE ENGINE
# =============================================================================

class EmotionalIntelligence:
    """Main emotional intelligence engine."""

    def __init__(self, model_router=None):
        self.model_router = model_router
        self.sentiment_analyzer = SentimentAnalyzer()
        self.emotion_detector = EmotionDetector()
        self.mood_tracker = MoodTracker()
        self.empathy_engine = EmpathyEngine(model_router)

    async def analyze(self, text: str, user_id: str = "default") -> Dict[str, Any]:
        """Analyze text for emotional content."""

        # Detect emotion
        emotional_state = self.emotion_detector.detect(text)

        # Analyze sentiment
        sentiment, confidence = self.sentiment_analyzer.analyze(text)
        emotional_state.sentiment = sentiment

        # Update mood
        mood = self.mood_tracker.update_mood(emotional_state, user_id)

        # Get profile
        profile = self.mood_tracker.get_profile(user_id)

        return {
            "emotional_state": {
                "primary_emotion": emotional_state.primary_emotion.value,
                "secondary_emotion": emotional_state.secondary_emotion.value if emotional_state.secondary_emotion else None,
                "sentiment": emotional_state.sentiment.value,
                "intensity": emotional_state.intensity,
                "confidence": emotional_state.confidence
            },
            "mood": mood.value,
            "profile": {
                "frustration_level": profile.frustration_level,
                "rapport_score": profile.rapport_score
            }
        }

    async def enhance_response(
        self,
        response: str,
        text: str,
        user_id: str = "default"
    ) -> str:
        """Enhance response with emotional intelligence."""

        # Analyze incoming text
        emotional_state = self.emotion_detector.detect(text)
        mood = self.mood_tracker.update_mood(emotional_state, user_id)
        profile = self.mood_tracker.get_profile(user_id)

        # Enhance response
        enhanced = await self.empathy_engine.enhance_response(
            response,
            emotional_state,
            mood,
            profile
        )

        return enhanced


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test emotional intelligence."""
    ei = EmotionalIntelligence()

    test_texts = [
        "This is absolutely fantastic! I love how well this works!",
        "I'm so frustrated. Nothing is working and I've tried everything.",
        "I'm a bit confused about how this feature works.",
        "Just give me the answer already.",
        "Interesting! Can you tell me more about this?",
        "Thanks, that was really helpful!"
    ]

    for text in test_texts:
        result = await ei.analyze(text)
        print(f"\nText: {text}")
        print(f"  Emotion: {result['emotional_state']['primary_emotion']}")
        print(f"  Sentiment: {result['emotional_state']['sentiment']}")
        print(f"  Mood: {result['mood']}")
        print(f"  Frustration: {result['profile']['frustration_level']:.2f}")
        print(f"  Rapport: {result['profile']['rapport_score']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
