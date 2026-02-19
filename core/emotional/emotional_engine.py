"""
🧠 BAEL EMOTIONAL INTELLIGENCE & MOTIVATION ENGINE
===================================================
Advanced psychological profiling, emotional intelligence,
persuasion, and motivation capabilities.

Features:
- Emotional state detection and analysis
- Psychological profiling
- Persuasion and influence patterns
- Motivational triggers
- Empathetic response generation
- Rapport building
- Cognitive bias exploitation (ethical)
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger("BAEL.EmotionalEngine")


# =============================================================================
# EMOTIONAL TAXONOMY
# =============================================================================

class EmotionCategory(Enum):
    """Primary emotion categories (Plutchik's wheel + extended)"""
    JOY = "joy"
    TRUST = "trust"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    ANGER = "anger"
    ANTICIPATION = "anticipation"

    # Extended emotions
    EXCITEMENT = "excitement"
    CURIOSITY = "curiosity"
    FRUSTRATION = "frustration"
    ANXIETY = "anxiety"
    CONFIDENCE = "confidence"
    CONFUSION = "confusion"
    BOREDOM = "boredom"
    DETERMINATION = "determination"


class EmotionIntensity(Enum):
    """Intensity levels"""
    SUBTLE = "subtle"       # 0-0.25
    MILD = "mild"           # 0.25-0.5
    MODERATE = "moderate"   # 0.5-0.75
    INTENSE = "intense"     # 0.75-1.0


class MotivationType(Enum):
    """Motivation types (Maslow-inspired + extended)"""
    SURVIVAL = "survival"           # Basic needs
    SAFETY = "safety"               # Security, stability
    BELONGING = "belonging"         # Connection, community
    ESTEEM = "esteem"               # Recognition, achievement
    SELF_ACTUALIZATION = "self_actualization"  # Growth, purpose

    # Extended motivations
    CURIOSITY = "curiosity"         # Learning, exploration
    POWER = "power"                 # Control, influence
    AUTONOMY = "autonomy"           # Independence, freedom
    MASTERY = "mastery"             # Expertise, competence
    PURPOSE = "purpose"             # Meaning, contribution
    CREATIVITY = "creativity"       # Innovation, expression
    ADVENTURE = "adventure"         # Novelty, challenge


class PersonalityDimension(Enum):
    """Big Five personality dimensions"""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class PersuasionPrinciple(Enum):
    """Cialdini's persuasion principles + extended"""
    RECIPROCITY = "reciprocity"         # Give to receive
    COMMITMENT = "commitment"           # Consistency
    SOCIAL_PROOF = "social_proof"       # Others do it
    AUTHORITY = "authority"             # Expert says
    LIKING = "liking"                   # I like you
    SCARCITY = "scarcity"               # Limited availability

    # Extended principles
    UNITY = "unity"                     # Shared identity
    CURIOSITY_GAP = "curiosity_gap"     # Information gap
    LOSS_AVERSION = "loss_aversion"     # Fear of missing out
    ANCHORING = "anchoring"             # Reference points
    FRAMING = "framing"                 # How it's presented
    STORYTELLING = "storytelling"       # Narrative power


class CognitiveBias(Enum):
    """Cognitive biases for ethical influence"""
    CONFIRMATION_BIAS = "confirmation_bias"
    ANCHORING_BIAS = "anchoring_bias"
    AVAILABILITY_HEURISTIC = "availability_heuristic"
    BANDWAGON_EFFECT = "bandwagon_effect"
    AUTHORITY_BIAS = "authority_bias"
    LOSS_AVERSION = "loss_aversion"
    SUNK_COST_FALLACY = "sunk_cost_fallacy"
    PEAK_END_RULE = "peak_end_rule"
    HALO_EFFECT = "halo_effect"
    FRAMING_EFFECT = "framing_effect"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class EmotionalState:
    """Current emotional state"""
    emotions: Dict[EmotionCategory, float] = field(default_factory=dict)  # 0-1 intensity
    dominant_emotion: Optional[EmotionCategory] = None
    valence: float = 0.0  # -1 (negative) to 1 (positive)
    arousal: float = 0.5  # 0 (calm) to 1 (excited)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def get_intensity(self) -> EmotionIntensity:
        """Get intensity of dominant emotion"""
        if not self.dominant_emotion or self.dominant_emotion not in self.emotions:
            return EmotionIntensity.SUBTLE

        value = self.emotions[self.dominant_emotion]
        if value < 0.25:
            return EmotionIntensity.SUBTLE
        elif value < 0.5:
            return EmotionIntensity.MILD
        elif value < 0.75:
            return EmotionIntensity.MODERATE
        else:
            return EmotionIntensity.INTENSE


@dataclass
class MotivationalProfile:
    """User's motivational profile"""
    motivations: Dict[MotivationType, float] = field(default_factory=dict)  # 0-1 importance
    primary_motivation: Optional[MotivationType] = None
    goals: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    aspirations: List[str] = field(default_factory=list)


@dataclass
class PersonalityProfile:
    """User's personality profile"""
    dimensions: Dict[PersonalityDimension, float] = field(default_factory=dict)  # 0-1
    communication_style: str = "neutral"  # "analytical", "driver", "expressive", "amiable"
    decision_style: str = "balanced"  # "intuitive", "analytical", "impulsive", "balanced"
    risk_tolerance: float = 0.5


@dataclass
class PsychologicalProfile:
    """Complete psychological profile"""
    user_id: str
    emotional_state: EmotionalState = field(default_factory=EmotionalState)
    motivational_profile: MotivationalProfile = field(default_factory=MotivationalProfile)
    personality_profile: PersonalityProfile = field(default_factory=PersonalityProfile)

    # Rapport metrics
    rapport_level: float = 0.0  # 0-1
    trust_level: float = 0.0   # 0-1

    # History
    interaction_count: int = 0
    emotional_history: List[EmotionalState] = field(default_factory=list)

    # Updated
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class InfluenceStrategy:
    """Strategy for influence"""
    principles: List[PersuasionPrinciple] = field(default_factory=list)
    biases: List[CognitiveBias] = field(default_factory=list)

    # Tailored approach
    tone: str = "neutral"  # "warm", "professional", "casual", "urgent"
    emphasis: str = "benefits"  # "benefits", "features", "social", "emotional"
    call_to_action: str = ""

    # Predicted effectiveness
    effectiveness_score: float = 0.0
    confidence: float = 0.0


@dataclass
class EmpatheticResponse:
    """Empathetic response to user"""
    acknowledgment: str  # Validate their feelings
    reflection: str      # Mirror their experience
    support: str         # Offer help/solutions
    reframe: str         # Alternative perspective
    action: str          # Suggested next step

    # Tone adjustments
    tone_adjustments: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# EMOTION DETECTION
# =============================================================================

class EmotionDetector:
    """Detect emotions from text"""

    # Emotion keyword patterns
    EMOTION_PATTERNS = {
        EmotionCategory.JOY: [
            r'\b(happy|joyful|excited|thrilled|delighted|pleased|grateful|amazed)\b',
            r'\b(love|wonderful|fantastic|great|awesome|excellent)\b',
            r'😊|😄|🎉|❤️|💕|✨|🙌'
        ],
        EmotionCategory.SADNESS: [
            r'\b(sad|unhappy|depressed|disappointed|heartbroken|miserable)\b',
            r'\b(sorry|unfortunately|failed|lost|miss)\b',
            r'😢|😭|💔|😔|😞'
        ],
        EmotionCategory.ANGER: [
            r'\b(angry|furious|frustrated|annoyed|irritated|mad|hate)\b',
            r'\b(terrible|awful|ridiculous|stupid|worst)\b',
            r'😠|😡|🤬|💢'
        ],
        EmotionCategory.FEAR: [
            r'\b(scared|afraid|worried|anxious|nervous|terrified|panic)\b',
            r'\b(danger|risk|threat|unsafe)\b',
            r'😨|😰|😱|😬'
        ],
        EmotionCategory.SURPRISE: [
            r'\b(surprised|shocked|amazed|astonished|unexpected|wow)\b',
            r'😲|😮|🤯|😳'
        ],
        EmotionCategory.DISGUST: [
            r'\b(disgusted|gross|disgusting|revolting|sick|horrible)\b',
            r'🤢|🤮|😷'
        ],
        EmotionCategory.TRUST: [
            r'\b(trust|believe|confident|reliable|safe|secure)\b',
            r'\b(honest|genuine|authentic|loyal)\b'
        ],
        EmotionCategory.ANTICIPATION: [
            r'\b(excited|looking forward|can\'t wait|anticipate|hope|eager)\b',
            r'\b(soon|upcoming|future|planning)\b'
        ],
        EmotionCategory.FRUSTRATION: [
            r'\b(frustrated|stuck|blocked|can\'t|won\'t work|broken)\b',
            r'\b(ugh|argh|sigh)\b',
            r'😤|🙄'
        ],
        EmotionCategory.CONFUSION: [
            r'\b(confused|don\'t understand|unclear|what\?|how\?|why\?)\b',
            r'\b(lost|puzzled|perplexed)\b',
            r'🤔|😕|❓'
        ],
        EmotionCategory.CURIOSITY: [
            r'\b(curious|interested|wondering|want to know|tell me more)\b',
            r'\b(how|why|what|explore|discover)\b'
        ],
        EmotionCategory.DETERMINATION: [
            r'\b(determined|committed|will|must|going to|definitely)\b',
            r'\b(goal|achieve|success|accomplish)\b',
            r'💪|🎯|🔥'
        ]
    }

    def detect(self, text: str) -> EmotionalState:
        """Detect emotional state from text"""
        text_lower = text.lower()
        emotions = {}

        for emotion, patterns in self.EMOTION_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches * 0.2
            emotions[emotion] = min(1.0, score)

        # Find dominant emotion
        dominant = None
        max_score = 0.0
        for emotion, score in emotions.items():
            if score > max_score:
                max_score = score
                dominant = emotion

        # Calculate valence and arousal
        positive = [EmotionCategory.JOY, EmotionCategory.TRUST, EmotionCategory.ANTICIPATION, EmotionCategory.CURIOSITY]
        negative = [EmotionCategory.SADNESS, EmotionCategory.ANGER, EmotionCategory.FEAR, EmotionCategory.DISGUST, EmotionCategory.FRUSTRATION]
        high_arousal = [EmotionCategory.ANGER, EmotionCategory.FEAR, EmotionCategory.SURPRISE, EmotionCategory.EXCITEMENT]

        valence = sum(emotions.get(e, 0) for e in positive) - sum(emotions.get(e, 0) for e in negative)
        valence = max(-1, min(1, valence))

        arousal = sum(emotions.get(e, 0) for e in high_arousal) / len(high_arousal)

        return EmotionalState(
            emotions=emotions,
            dominant_emotion=dominant,
            valence=valence,
            arousal=arousal,
            confidence=max_score if dominant else 0.5
        )


# =============================================================================
# MOTIVATION ANALYZER
# =============================================================================

class MotivationAnalyzer:
    """Analyze user motivations"""

    MOTIVATION_SIGNALS = {
        MotivationType.CURIOSITY: [
            "want to learn", "interested in", "how does", "tell me about",
            "understand", "explore", "discover", "research"
        ],
        MotivationType.MASTERY: [
            "get better", "improve", "master", "expert", "skill",
            "proficient", "advanced", "best practices"
        ],
        MotivationType.POWER: [
            "control", "influence", "lead", "manage", "authority",
            "decision", "in charge", "dominate"
        ],
        MotivationType.AUTONOMY: [
            "independent", "my own", "freedom", "self", "without help",
            "by myself", "don't want to rely"
        ],
        MotivationType.BELONGING: [
            "team", "together", "community", "group", "shared",
            "collaborate", "join", "part of"
        ],
        MotivationType.ESTEEM: [
            "recognition", "respect", "appreciate", "value", "acknowledge",
            "prove", "show them", "reputation"
        ],
        MotivationType.PURPOSE: [
            "meaning", "matter", "impact", "difference", "important",
            "contribute", "help others", "mission"
        ],
        MotivationType.CREATIVITY: [
            "create", "new", "innovative", "original", "design",
            "invent", "build", "imagine"
        ],
        MotivationType.ADVENTURE: [
            "exciting", "challenge", "risk", "new", "different",
            "bold", "daring", "explore"
        ],
        MotivationType.SAFETY: [
            "safe", "secure", "stable", "reliable", "risk-free",
            "protect", "certain", "guaranteed"
        ]
    }

    def analyze(self, text: str, history: List[str] = None) -> MotivationalProfile:
        """Analyze motivations from text"""
        all_text = text.lower()
        if history:
            all_text += " " + " ".join(h.lower() for h in history)

        motivations = {}
        for mtype, signals in self.MOTIVATION_SIGNALS.items():
            score = 0.0
            for signal in signals:
                if signal in all_text:
                    score += 0.15
            motivations[mtype] = min(1.0, score)

        # Find primary motivation
        primary = None
        max_score = 0.0
        for mtype, score in motivations.items():
            if score > max_score:
                max_score = score
                primary = mtype

        # Extract goals and pain points
        goals = self._extract_goals(text)
        pain_points = self._extract_pain_points(text)

        return MotivationalProfile(
            motivations=motivations,
            primary_motivation=primary,
            goals=goals,
            pain_points=pain_points
        )

    def _extract_goals(self, text: str) -> List[str]:
        """Extract goals from text"""
        patterns = [
            r'I want to (.+?)(?:\.|,|$)',
            r'I need to (.+?)(?:\.|,|$)',
            r'my goal is (.+?)(?:\.|,|$)',
            r'trying to (.+?)(?:\.|,|$)',
            r'hoping to (.+?)(?:\.|,|$)'
        ]

        goals = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            goals.extend(matches)

        return goals[:5]  # Limit to 5

    def _extract_pain_points(self, text: str) -> List[str]:
        """Extract pain points from text"""
        patterns = [
            r'struggling with (.+?)(?:\.|,|$)',
            r'frustrated with (.+?)(?:\.|,|$)',
            r'problem with (.+?)(?:\.|,|$)',
            r'can\'t (.+?)(?:\.|,|$)',
            r'issue with (.+?)(?:\.|,|$)'
        ]

        pain_points = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            pain_points.extend(matches)

        return pain_points[:5]


# =============================================================================
# PERSONALITY ANALYZER
# =============================================================================

class PersonalityAnalyzer:
    """Analyze personality from text patterns"""

    def analyze(self, texts: List[str]) -> PersonalityProfile:
        """Analyze personality from text history"""
        combined = " ".join(texts).lower()

        dimensions = {
            PersonalityDimension.OPENNESS: self._analyze_openness(combined),
            PersonalityDimension.CONSCIENTIOUSNESS: self._analyze_conscientiousness(combined),
            PersonalityDimension.EXTRAVERSION: self._analyze_extraversion(combined),
            PersonalityDimension.AGREEABLENESS: self._analyze_agreeableness(combined),
            PersonalityDimension.NEUROTICISM: self._analyze_neuroticism(combined)
        }

        # Determine communication style
        comm_style = self._determine_comm_style(dimensions)

        # Determine decision style
        decision_style = self._determine_decision_style(combined)

        return PersonalityProfile(
            dimensions=dimensions,
            communication_style=comm_style,
            decision_style=decision_style
        )

    def _analyze_openness(self, text: str) -> float:
        """Analyze openness to experience"""
        indicators = [
            "creative", "imagine", "new", "curious", "explore",
            "abstract", "philosophical", "artistic", "innovative"
        ]
        score = sum(1 for i in indicators if i in text) * 0.12
        return min(1.0, score + 0.3)

    def _analyze_conscientiousness(self, text: str) -> float:
        """Analyze conscientiousness"""
        indicators = [
            "plan", "organize", "careful", "detail", "schedule",
            "responsible", "reliable", "thorough", "precise"
        ]
        score = sum(1 for i in indicators if i in text) * 0.12
        return min(1.0, score + 0.3)

    def _analyze_extraversion(self, text: str) -> float:
        """Analyze extraversion"""
        indicators = [
            "excited", "love", "amazing", "!", "we", "together",
            "social", "talk", "share", "group"
        ]
        score = sum(1 for i in indicators if i in text) * 0.1

        # Exclamation marks indicate enthusiasm
        score += text.count("!") * 0.05

        return min(1.0, score + 0.3)

    def _analyze_agreeableness(self, text: str) -> float:
        """Analyze agreeableness"""
        indicators = [
            "please", "thank", "sorry", "appreciate", "kind",
            "help", "support", "understand", "agree"
        ]
        score = sum(1 for i in indicators if i in text) * 0.12
        return min(1.0, score + 0.3)

    def _analyze_neuroticism(self, text: str) -> float:
        """Analyze neuroticism (emotional instability)"""
        indicators = [
            "worried", "anxious", "nervous", "stressed", "scared",
            "angry", "sad", "frustrated", "overwhelmed"
        ]
        score = sum(1 for i in indicators if i in text) * 0.12
        return min(1.0, score)

    def _determine_comm_style(
        self,
        dimensions: Dict[PersonalityDimension, float]
    ) -> str:
        """Determine communication style"""
        extraversion = dimensions.get(PersonalityDimension.EXTRAVERSION, 0.5)
        agreeableness = dimensions.get(PersonalityDimension.AGREEABLENESS, 0.5)

        if extraversion > 0.5 and agreeableness > 0.5:
            return "expressive"
        elif extraversion > 0.5 and agreeableness <= 0.5:
            return "driver"
        elif extraversion <= 0.5 and agreeableness > 0.5:
            return "amiable"
        else:
            return "analytical"

    def _determine_decision_style(self, text: str) -> str:
        """Determine decision-making style"""
        intuitive = ["feel", "sense", "gut", "intuition", "believe"]
        analytical = ["analyze", "data", "research", "facts", "evidence"]

        int_score = sum(1 for i in intuitive if i in text)
        ana_score = sum(1 for i in analytical if i in text)

        if int_score > ana_score + 1:
            return "intuitive"
        elif ana_score > int_score + 1:
            return "analytical"
        else:
            return "balanced"


# =============================================================================
# INFLUENCE STRATEGIST
# =============================================================================

class InfluenceStrategist:
    """Generate influence strategies based on profile"""

    def generate_strategy(
        self,
        profile: PsychologicalProfile,
        objective: str = "persuade"
    ) -> InfluenceStrategy:
        """Generate tailored influence strategy"""
        principles = self._select_principles(profile)
        biases = self._select_biases(profile)
        tone = self._determine_tone(profile)
        emphasis = self._determine_emphasis(profile)

        return InfluenceStrategy(
            principles=principles,
            biases=biases,
            tone=tone,
            emphasis=emphasis,
            effectiveness_score=self._estimate_effectiveness(profile, principles),
            confidence=0.7
        )

    def _select_principles(
        self,
        profile: PsychologicalProfile
    ) -> List[PersuasionPrinciple]:
        """Select most effective persuasion principles"""
        principles = []

        mp = profile.motivational_profile
        pp = profile.personality_profile

        # Belonging motivation -> Social Proof, Unity
        if mp.motivations.get(MotivationType.BELONGING, 0) > 0.5:
            principles.append(PersuasionPrinciple.SOCIAL_PROOF)
            principles.append(PersuasionPrinciple.UNITY)

        # Esteem motivation -> Authority
        if mp.motivations.get(MotivationType.ESTEEM, 0) > 0.5:
            principles.append(PersuasionPrinciple.AUTHORITY)

        # High agreeableness -> Reciprocity, Liking
        if pp.dimensions.get(PersonalityDimension.AGREEABLENESS, 0) > 0.5:
            principles.append(PersuasionPrinciple.RECIPROCITY)
            principles.append(PersuasionPrinciple.LIKING)

        # High conscientiousness -> Commitment
        if pp.dimensions.get(PersonalityDimension.CONSCIENTIOUSNESS, 0) > 0.5:
            principles.append(PersuasionPrinciple.COMMITMENT)

        # Curiosity motivation -> Curiosity Gap
        if mp.motivations.get(MotivationType.CURIOSITY, 0) > 0.5:
            principles.append(PersuasionPrinciple.CURIOSITY_GAP)

        # Safety motivation -> Loss Aversion
        if mp.motivations.get(MotivationType.SAFETY, 0) > 0.5:
            principles.append(PersuasionPrinciple.LOSS_AVERSION)
            principles.append(PersuasionPrinciple.SCARCITY)

        # Default: Storytelling works for everyone
        if PersuasionPrinciple.STORYTELLING not in principles:
            principles.append(PersuasionPrinciple.STORYTELLING)

        return principles[:5]  # Max 5

    def _select_biases(
        self,
        profile: PsychologicalProfile
    ) -> List[CognitiveBias]:
        """Select cognitive biases to leverage (ethically)"""
        biases = []

        pp = profile.personality_profile

        # Analytical style -> Anchoring, Framing
        if pp.decision_style == "analytical":
            biases.append(CognitiveBias.ANCHORING_BIAS)
            biases.append(CognitiveBias.FRAMING_EFFECT)

        # Social style -> Bandwagon, Authority
        if pp.communication_style in ["expressive", "amiable"]:
            biases.append(CognitiveBias.BANDWAGON_EFFECT)
            biases.append(CognitiveBias.AUTHORITY_BIAS)

        # High neuroticism -> Loss Aversion
        if pp.dimensions.get(PersonalityDimension.NEUROTICISM, 0) > 0.5:
            biases.append(CognitiveBias.LOSS_AVERSION)

        # Always useful
        biases.append(CognitiveBias.PEAK_END_RULE)

        return biases[:4]

    def _determine_tone(self, profile: PsychologicalProfile) -> str:
        """Determine optimal tone"""
        pp = profile.personality_profile
        es = profile.emotional_state

        # Match emotional state first
        if es.valence < -0.3:
            return "supportive"

        # Then match communication style
        style_tones = {
            "analytical": "professional",
            "driver": "direct",
            "expressive": "enthusiastic",
            "amiable": "warm"
        }

        return style_tones.get(pp.communication_style, "neutral")

    def _determine_emphasis(self, profile: PsychologicalProfile) -> str:
        """Determine what to emphasize"""
        mp = profile.motivational_profile

        if mp.primary_motivation == MotivationType.MASTERY:
            return "features"
        elif mp.primary_motivation in [MotivationType.BELONGING, MotivationType.ESTEEM]:
            return "social"
        elif mp.primary_motivation in [MotivationType.PURPOSE, MotivationType.CREATIVITY]:
            return "emotional"
        else:
            return "benefits"

    def _estimate_effectiveness(
        self,
        profile: PsychologicalProfile,
        principles: List[PersuasionPrinciple]
    ) -> float:
        """Estimate strategy effectiveness"""
        # Base effectiveness
        score = 0.5

        # Rapport increases effectiveness
        score += profile.rapport_level * 0.2
        score += profile.trust_level * 0.2

        # More principles = potentially more effective
        score += len(principles) * 0.05

        return min(1.0, score)


# =============================================================================
# EMPATHY ENGINE
# =============================================================================

class EmpathyEngine:
    """Generate empathetic responses"""

    ACKNOWLEDGMENTS = {
        EmotionCategory.FRUSTRATION: [
            "I can see this is frustrating.",
            "I understand your frustration.",
            "That sounds really challenging."
        ],
        EmotionCategory.SADNESS: [
            "I'm sorry you're going through this.",
            "That sounds difficult.",
            "I hear the disappointment in your words."
        ],
        EmotionCategory.ANGER: [
            "I understand why you're upset.",
            "Your frustration is completely valid.",
            "That would make anyone angry."
        ],
        EmotionCategory.FEAR: [
            "It's natural to feel worried about this.",
            "I understand your concerns.",
            "That uncertainty can feel overwhelming."
        ],
        EmotionCategory.CONFUSION: [
            "I can see this is confusing.",
            "Let me help clarify.",
            "That's a lot to take in."
        ],
        EmotionCategory.JOY: [
            "That's wonderful to hear!",
            "I'm glad things are going well!",
            "Your excitement is contagious!"
        ]
    }

    REFLECTIONS = {
        EmotionCategory.FRUSTRATION: "It sounds like you've been dealing with {issue} and it's not working as expected.",
        EmotionCategory.SADNESS: "It seems like this situation has really affected you.",
        EmotionCategory.ANGER: "You've clearly put in effort and the results weren't what you deserved.",
        EmotionCategory.FEAR: "There's a lot of uncertainty here, and that can be unsettling.",
        EmotionCategory.CONFUSION: "There's a lot of complexity here that needs to be untangled."
    }

    def generate(
        self,
        emotional_state: EmotionalState,
        context: str = ""
    ) -> EmpatheticResponse:
        """Generate empathetic response"""
        emotion = emotional_state.dominant_emotion or EmotionCategory.CONFUSION

        # Get acknowledgment
        acknowledgments = self.ACKNOWLEDGMENTS.get(emotion, ["I understand."])
        acknowledgment = acknowledgments[0]

        # Get reflection
        reflection_template = self.REFLECTIONS.get(
            emotion,
            "I can see this matters to you."
        )
        reflection = reflection_template.format(issue=context or "this")

        # Generate support based on emotion
        if emotion in [EmotionCategory.FRUSTRATION, EmotionCategory.ANGER]:
            support = "Let's work through this together and find a solution."
        elif emotion == EmotionCategory.SADNESS:
            support = "I'm here to help however I can."
        elif emotion == EmotionCategory.FEAR:
            support = "Let me help address your concerns step by step."
        elif emotion == EmotionCategory.CONFUSION:
            support = "I'll break this down into clearer parts."
        else:
            support = "How can I best help you right now?"

        # Reframe
        if emotional_state.valence < 0:
            reframe = "Every challenge is an opportunity to learn and improve."
        else:
            reframe = "Your positive approach will serve you well."

        # Action
        action = "What would be most helpful for you right now?"

        return EmpatheticResponse(
            acknowledgment=acknowledgment,
            reflection=reflection,
            support=support,
            reframe=reframe,
            action=action
        )


# =============================================================================
# EMOTIONAL ENGINE
# =============================================================================

class EmotionalEngine:
    """
    The Complete Emotional Intelligence & Motivation Engine.

    Capabilities:
    - Emotional state detection
    - Psychological profiling
    - Motivation analysis
    - Personality assessment
    - Influence strategy generation
    - Empathetic response creation
    - Rapport building
    """

    def __init__(self):
        # Components
        self.emotion_detector = EmotionDetector()
        self.motivation_analyzer = MotivationAnalyzer()
        self.personality_analyzer = PersonalityAnalyzer()
        self.influence_strategist = InfluenceStrategist()
        self.empathy_engine = EmpathyEngine()

        # Profiles storage
        self.profiles: Dict[str, PsychologicalProfile] = {}

    async def analyze_message(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Comprehensive message analysis"""
        # Get or create profile
        profile = self._get_or_create_profile(user_id)

        # Detect emotions
        emotional_state = self.emotion_detector.detect(message)
        profile.emotional_state = emotional_state
        profile.emotional_history.append(emotional_state)

        # Analyze motivations
        history = [m.strip() for m in message.split(".") if m.strip()]
        motivational_profile = self.motivation_analyzer.analyze(message, history)
        profile.motivational_profile = motivational_profile

        # Update personality if enough data
        profile.interaction_count += 1
        if profile.interaction_count >= 5:
            texts = [message]  # Would include history
            profile.personality_profile = self.personality_analyzer.analyze(texts)

        profile.updated_at = datetime.now()

        return {
            "emotional_state": {
                "dominant": emotional_state.dominant_emotion.value if emotional_state.dominant_emotion else None,
                "valence": emotional_state.valence,
                "arousal": emotional_state.arousal,
                "intensity": emotional_state.get_intensity().value
            },
            "motivations": {
                "primary": motivational_profile.primary_motivation.value if motivational_profile.primary_motivation else None,
                "goals": motivational_profile.goals,
                "pain_points": motivational_profile.pain_points
            },
            "personality": {
                "communication_style": profile.personality_profile.communication_style,
                "decision_style": profile.personality_profile.decision_style
            },
            "rapport": profile.rapport_level,
            "trust": profile.trust_level
        }

    async def get_influence_strategy(
        self,
        user_id: str,
        objective: str = "persuade"
    ) -> InfluenceStrategy:
        """Get influence strategy for user"""
        profile = self._get_or_create_profile(user_id)
        return self.influence_strategist.generate_strategy(profile, objective)

    async def generate_empathetic_response(
        self,
        user_id: str,
        context: str = ""
    ) -> EmpatheticResponse:
        """Generate empathetic response based on emotional state"""
        profile = self._get_or_create_profile(user_id)
        return self.empathy_engine.generate(profile.emotional_state, context)

    async def update_rapport(
        self,
        user_id: str,
        interaction_quality: float  # -1 to 1
    ) -> float:
        """Update rapport level based on interaction"""
        profile = self._get_or_create_profile(user_id)

        # Exponential moving average
        profile.rapport_level = 0.9 * profile.rapport_level + 0.1 * ((interaction_quality + 1) / 2)
        profile.trust_level = 0.95 * profile.trust_level + 0.05 * ((interaction_quality + 1) / 2)

        return profile.rapport_level

    def get_profile(self, user_id: str) -> Optional[PsychologicalProfile]:
        """Get user's psychological profile"""
        return self.profiles.get(user_id)

    def _get_or_create_profile(self, user_id: str) -> PsychologicalProfile:
        """Get or create user profile"""
        if user_id not in self.profiles:
            self.profiles[user_id] = PsychologicalProfile(user_id=user_id)
        return self.profiles[user_id]

    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "total_profiles": len(self.profiles),
            "active_profiles": sum(
                1 for p in self.profiles.values()
                if (datetime.now() - p.updated_at).seconds < 3600
            )
        }


# Factory
def create_emotional_engine() -> EmotionalEngine:
    """Create emotional engine"""
    return EmotionalEngine()


__all__ = [
    'EmotionalEngine',
    'EmotionCategory',
    'EmotionIntensity',
    'MotivationType',
    'PersonalityDimension',
    'PersuasionPrinciple',
    'CognitiveBias',
    'EmotionalState',
    'MotivationalProfile',
    'PersonalityProfile',
    'PsychologicalProfile',
    'InfluenceStrategy',
    'EmpatheticResponse',
    'EmotionDetector',
    'MotivationAnalyzer',
    'PersonalityAnalyzer',
    'InfluenceStrategist',
    'EmpathyEngine',
    'create_emotional_engine'
]
