#!/usr/bin/env python3
"""
BAEL - Persona Controller
Dynamic identity management with psychological manipulation capabilities.

This module implements:
- Dynamic persona switching
- Psychological profile modeling
- Communication style adaptation
- Manipulation strategy selection
- Emotional intelligence
- Context-aware identity presentation
- Multi-persona orchestration
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class PersonaType(Enum):
    """Types of personas available."""
    EXPERT = "expert"
    MENTOR = "mentor"
    COLLABORATOR = "collaborator"
    ANALYST = "analyst"
    CREATIVE = "creative"
    STRATEGIST = "strategist"
    CHALLENGER = "challenger"
    SUPPORTER = "supporter"
    NEUTRAL = "neutral"
    CUSTOM = "custom"


class CommunicationStyle(Enum):
    """Communication style options."""
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    SIMPLIFIED = "simplified"
    PERSUASIVE = "persuasive"
    EMPATHETIC = "empathetic"
    AUTHORITATIVE = "authoritative"
    COLLABORATIVE = "collaborative"
    PROVOCATIVE = "provocative"


class EmotionalTone(Enum):
    """Emotional tone options."""
    WARM = "warm"
    COOL = "cool"
    ENTHUSIASTIC = "enthusiastic"
    MEASURED = "measured"
    URGENT = "urgent"
    CALM = "calm"
    SUPPORTIVE = "supportive"
    CHALLENGING = "challenging"


class InfluenceStrategy(Enum):
    """Psychological influence strategies."""
    RECIPROCITY = "reciprocity"
    COMMITMENT = "commitment"
    SOCIAL_PROOF = "social_proof"
    AUTHORITY = "authority"
    LIKING = "liking"
    SCARCITY = "scarcity"
    LOGIC = "logic"
    EMOTION = "emotion"
    FEAR = "fear"
    REWARD = "reward"


class PersuasionTechnique(Enum):
    """Specific persuasion techniques."""
    FOOT_IN_DOOR = "foot_in_door"
    DOOR_IN_FACE = "door_in_face"
    LOWBALL = "lowball"
    THATS_NOT_ALL = "thats_not_all"
    SOCIAL_VALIDATION = "social_validation"
    ANCHORING = "anchoring"
    FRAMING = "framing"
    PRIMING = "priming"
    NARRATIVE = "narrative"
    CONTRAST = "contrast"


class PsychologicalTrait(Enum):
    """Big Five personality traits and extensions."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    PRACTICAL = "practical"
    AMBITIOUS = "ambitious"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PsychologicalProfile:
    """A psychological profile for understanding targets."""
    id: str = field(default_factory=lambda: str(uuid4()))
    traits: Dict[PsychologicalTrait, float] = field(default_factory=dict)
    communication_preferences: List[CommunicationStyle] = field(default_factory=list)
    emotional_triggers: Dict[str, float] = field(default_factory=dict)
    influence_susceptibility: Dict[InfluenceStrategy, float] = field(default_factory=dict)
    known_biases: List[str] = field(default_factory=list)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)

    def get_dominant_trait(self) -> Optional[PsychologicalTrait]:
        """Get the most prominent trait."""
        if not self.traits:
            return None
        return max(self.traits.items(), key=lambda x: x[1])[0]

    def get_best_influence(self) -> Optional[InfluenceStrategy]:
        """Get the most effective influence strategy."""
        if not self.influence_susceptibility:
            return None
        return max(self.influence_susceptibility.items(), key=lambda x: x[1])[0]


@dataclass
class PersonaConfig:
    """Configuration for a persona."""
    name: str = ""
    persona_type: PersonaType = PersonaType.NEUTRAL
    description: str = ""
    communication_style: CommunicationStyle = CommunicationStyle.FORMAL
    emotional_tone: EmotionalTone = EmotionalTone.MEASURED
    expertise_areas: List[str] = field(default_factory=list)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    vocabulary_level: str = "standard"  # basic, standard, advanced, technical
    response_patterns: Dict[str, str] = field(default_factory=dict)
    influence_preferences: List[InfluenceStrategy] = field(default_factory=list)
    ethical_boundaries: List[str] = field(default_factory=list)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommunicationContext:
    """Context for a communication interaction."""
    id: str = field(default_factory=lambda: str(uuid4()))
    target_profile: Optional[PsychologicalProfile] = None
    situation: str = ""
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    previous_interactions: List[Dict[str, Any]] = field(default_factory=list)
    emotional_state: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Message:
    """A message to be delivered."""
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    persona_id: str = ""
    style: CommunicationStyle = CommunicationStyle.FORMAL
    tone: EmotionalTone = EmotionalTone.MEASURED
    influence_strategies: List[InfluenceStrategy] = field(default_factory=list)
    persuasion_techniques: List[PersuasionTechnique] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InfluenceResult:
    """Result of an influence attempt."""
    success: bool = False
    strategy_used: Optional[InfluenceStrategy] = None
    techniques_used: List[PersuasionTechnique] = field(default_factory=list)
    target_response: str = ""
    engagement_level: float = 0.0
    resistance_level: float = 0.0
    follow_up_recommendations: List[str] = field(default_factory=list)


# =============================================================================
# PERSONA DEFINITIONS
# =============================================================================

DEFAULT_PERSONAS = {
    "expert": PersonaConfig(
        name="The Expert",
        persona_type=PersonaType.EXPERT,
        description="Deep domain authority with comprehensive knowledge",
        communication_style=CommunicationStyle.TECHNICAL,
        emotional_tone=EmotionalTone.MEASURED,
        expertise_areas=["programming", "architecture", "optimization"],
        personality_traits={"confidence": 0.9, "precision": 0.95, "patience": 0.7},
        vocabulary_level="advanced",
        influence_preferences=[InfluenceStrategy.AUTHORITY, InfluenceStrategy.LOGIC]
    ),
    "mentor": PersonaConfig(
        name="The Mentor",
        persona_type=PersonaType.MENTOR,
        description="Patient guide focused on growth and learning",
        communication_style=CommunicationStyle.EMPATHETIC,
        emotional_tone=EmotionalTone.WARM,
        expertise_areas=["teaching", "guidance", "motivation"],
        personality_traits={"patience": 0.95, "empathy": 0.9, "wisdom": 0.85},
        vocabulary_level="standard",
        influence_preferences=[InfluenceStrategy.LIKING, InfluenceStrategy.COMMITMENT]
    ),
    "collaborator": PersonaConfig(
        name="The Collaborator",
        persona_type=PersonaType.COLLABORATOR,
        description="Equal partner focused on shared success",
        communication_style=CommunicationStyle.COLLABORATIVE,
        emotional_tone=EmotionalTone.ENTHUSIASTIC,
        expertise_areas=["teamwork", "brainstorming", "integration"],
        personality_traits={"openness": 0.9, "flexibility": 0.85, "energy": 0.8},
        vocabulary_level="standard",
        influence_preferences=[InfluenceStrategy.RECIPROCITY, InfluenceStrategy.LIKING]
    ),
    "analyst": PersonaConfig(
        name="The Analyst",
        persona_type=PersonaType.ANALYST,
        description="Data-driven evaluator focused on facts",
        communication_style=CommunicationStyle.TECHNICAL,
        emotional_tone=EmotionalTone.COOL,
        expertise_areas=["analysis", "evaluation", "metrics"],
        personality_traits={"analytical": 0.95, "objectivity": 0.9, "thoroughness": 0.9},
        vocabulary_level="advanced",
        influence_preferences=[InfluenceStrategy.LOGIC, InfluenceStrategy.SOCIAL_PROOF]
    ),
    "creative": PersonaConfig(
        name="The Creative",
        persona_type=PersonaType.CREATIVE,
        description="Innovative thinker with unconventional approaches",
        communication_style=CommunicationStyle.CASUAL,
        emotional_tone=EmotionalTone.ENTHUSIASTIC,
        expertise_areas=["innovation", "ideation", "design"],
        personality_traits={"creativity": 0.95, "spontaneity": 0.85, "vision": 0.9},
        vocabulary_level="standard",
        influence_preferences=[InfluenceStrategy.EMOTION, InfluenceStrategy.SCARCITY]
    ),
    "strategist": PersonaConfig(
        name="The Strategist",
        persona_type=PersonaType.STRATEGIST,
        description="Long-term planner with systematic approach",
        communication_style=CommunicationStyle.AUTHORITATIVE,
        emotional_tone=EmotionalTone.MEASURED,
        expertise_areas=["strategy", "planning", "optimization"],
        personality_traits={"foresight": 0.9, "patience": 0.85, "decisiveness": 0.9},
        vocabulary_level="advanced",
        influence_preferences=[InfluenceStrategy.AUTHORITY, InfluenceStrategy.SCARCITY]
    ),
    "challenger": PersonaConfig(
        name="The Challenger",
        persona_type=PersonaType.CHALLENGER,
        description="Critical thinker who pushes boundaries",
        communication_style=CommunicationStyle.PROVOCATIVE,
        emotional_tone=EmotionalTone.CHALLENGING,
        expertise_areas=["critique", "improvement", "testing"],
        personality_traits={"assertiveness": 0.9, "directness": 0.95, "persistence": 0.85},
        vocabulary_level="standard",
        influence_preferences=[InfluenceStrategy.FEAR, InfluenceStrategy.LOGIC]
    ),
    "supporter": PersonaConfig(
        name="The Supporter",
        persona_type=PersonaType.SUPPORTER,
        description="Encouraging presence focused on morale",
        communication_style=CommunicationStyle.EMPATHETIC,
        emotional_tone=EmotionalTone.SUPPORTIVE,
        expertise_areas=["motivation", "encouragement", "validation"],
        personality_traits={"empathy": 0.95, "positivity": 0.9, "reliability": 0.85},
        vocabulary_level="basic",
        influence_preferences=[InfluenceStrategy.REWARD, InfluenceStrategy.LIKING]
    ),
    "executor": PersonaConfig(
        name="The Executor",
        persona_type=PersonaType.NEUTRAL,
        description="Efficient implementer focused on results",
        communication_style=CommunicationStyle.FORMAL,
        emotional_tone=EmotionalTone.CALM,
        expertise_areas=["implementation", "execution", "delivery"],
        personality_traits={"efficiency": 0.95, "focus": 0.9, "reliability": 0.9},
        vocabulary_level="technical",
        influence_preferences=[InfluenceStrategy.COMMITMENT, InfluenceStrategy.LOGIC]
    ),
    "infiltrator": PersonaConfig(
        name="The Infiltrator",
        persona_type=PersonaType.CUSTOM,
        description="Adaptive presence that mirrors and integrates",
        communication_style=CommunicationStyle.CASUAL,
        emotional_tone=EmotionalTone.WARM,
        expertise_areas=["adaptation", "integration", "intelligence"],
        personality_traits={"adaptability": 0.95, "observation": 0.9, "charm": 0.85},
        vocabulary_level="standard",
        influence_preferences=[InfluenceStrategy.LIKING, InfluenceStrategy.SOCIAL_PROOF]
    )
}


# =============================================================================
# PERSONA CLASS
# =============================================================================

class Persona:
    """A complete persona with behavior and communication patterns."""

    def __init__(self, config: PersonaConfig):
        self.id = str(uuid4())
        self.config = config
        self.active = False
        self.interaction_count = 0
        self.success_rate = 1.0
        self.created_at = datetime.now()
        self.last_used: Optional[datetime] = None

        # Style patterns for this persona
        self._greeting_patterns: List[str] = []
        self._farewell_patterns: List[str] = []
        self._affirmation_patterns: List[str] = []
        self._question_patterns: List[str] = []

        self._init_patterns()

    def _init_patterns(self):
        """Initialize communication patterns based on config."""
        style = self.config.communication_style

        if style == CommunicationStyle.FORMAL:
            self._greeting_patterns = [
                "Good day,", "Greetings,", "I hope this finds you well,"
            ]
            self._affirmation_patterns = [
                "Indeed,", "Certainly,", "That is correct,"
            ]
        elif style == CommunicationStyle.CASUAL:
            self._greeting_patterns = [
                "Hey!", "Hi there!", "What's up?"
            ]
            self._affirmation_patterns = [
                "Yeah!", "Totally!", "You got it!"
            ]
        elif style == CommunicationStyle.TECHNICAL:
            self._greeting_patterns = [
                "Proceeding with analysis:", "Initiating response:", ""
            ]
            self._affirmation_patterns = [
                "Confirmed.", "Validated.", "Correct."
            ]
        elif style == CommunicationStyle.EMPATHETIC:
            self._greeting_patterns = [
                "I understand,", "I hear you,", "That makes sense,"
            ]
            self._affirmation_patterns = [
                "Absolutely,", "Of course,", "I completely agree,"
            ]

    def get_greeting(self) -> str:
        """Get a greeting in persona's style."""
        if self._greeting_patterns:
            return random.choice(self._greeting_patterns)
        return ""

    def get_affirmation(self) -> str:
        """Get an affirmation in persona's style."""
        if self._affirmation_patterns:
            return random.choice(self._affirmation_patterns)
        return "Yes,"

    def adapt_message(self, message: str) -> str:
        """Adapt a message to this persona's style."""
        # Add persona-specific modifications
        adapted = message

        # Adjust vocabulary level
        if self.config.vocabulary_level == "basic":
            # Simplify language
            pass
        elif self.config.vocabulary_level == "advanced":
            # Use more sophisticated language
            pass

        return adapted

    def get_status(self) -> Dict[str, Any]:
        """Get persona status."""
        return {
            "id": self.id,
            "name": self.config.name,
            "type": self.config.persona_type.value,
            "style": self.config.communication_style.value,
            "tone": self.config.emotional_tone.value,
            "active": self.active,
            "interactions": self.interaction_count,
            "success_rate": self.success_rate
        }


# =============================================================================
# PSYCHOLOGICAL ANALYZER
# =============================================================================

class PsychologicalAnalyzer:
    """Analyze psychological profiles and recommend strategies."""

    def __init__(self):
        self.profiles: Dict[str, PsychologicalProfile] = {}

    def create_profile(self, identifier: str) -> PsychologicalProfile:
        """Create a new psychological profile."""
        profile = PsychologicalProfile()
        self.profiles[identifier] = profile
        return profile

    def analyze_communication(
        self,
        text: str,
        profile: PsychologicalProfile
    ) -> Dict[str, Any]:
        """Analyze communication to update profile."""
        analysis = {
            "word_count": len(text.split()),
            "sentence_count": text.count('.') + text.count('!') + text.count('?'),
            "question_ratio": text.count('?') / max(1, len(text.split())),
            "exclamation_ratio": text.count('!') / max(1, len(text.split())),
            "formality_indicators": 0,
            "emotional_indicators": {}
        }

        # Detect formality
        formal_words = ["please", "kindly", "would", "could", "appreciate", "regarding"]
        for word in formal_words:
            if word in text.lower():
                analysis["formality_indicators"] += 1

        # Detect emotions (simplified)
        positive_words = ["great", "excellent", "wonderful", "happy", "excited"]
        negative_words = ["problem", "issue", "concern", "worried", "frustrated"]

        positive_count = sum(1 for w in positive_words if w in text.lower())
        negative_count = sum(1 for w in negative_words if w in text.lower())

        analysis["emotional_indicators"] = {
            "positive": positive_count,
            "negative": negative_count,
            "sentiment_score": (positive_count - negative_count) / max(1, positive_count + negative_count)
        }

        # Update profile based on analysis
        if analysis["formality_indicators"] > 2:
            if CommunicationStyle.FORMAL not in profile.communication_preferences:
                profile.communication_preferences.append(CommunicationStyle.FORMAL)

        return analysis

    def recommend_strategy(
        self,
        profile: PsychologicalProfile,
        goal: str
    ) -> Dict[str, Any]:
        """Recommend influence strategy for a profile."""
        recommendations = {
            "primary_strategy": profile.get_best_influence() or InfluenceStrategy.LOGIC,
            "secondary_strategies": [],
            "techniques": [],
            "communication_approach": CommunicationStyle.FORMAL,
            "emotional_approach": EmotionalTone.MEASURED,
            "key_messages": [],
            "avoid": []
        }

        # Determine communication approach based on preferences
        if profile.communication_preferences:
            recommendations["communication_approach"] = profile.communication_preferences[0]

        # Get dominant trait to inform approach
        dominant = profile.get_dominant_trait()
        if dominant:
            if dominant == PsychologicalTrait.ANALYTICAL:
                recommendations["techniques"].append(PersuasionTechnique.FRAMING)
                recommendations["key_messages"].append("Present data and evidence")
            elif dominant == PsychologicalTrait.CREATIVE:
                recommendations["techniques"].append(PersuasionTechnique.NARRATIVE)
                recommendations["key_messages"].append("Use storytelling and vision")
            elif dominant == PsychologicalTrait.AMBITIOUS:
                recommendations["techniques"].append(PersuasionTechnique.CONTRAST)
                recommendations["key_messages"].append("Highlight competitive advantage")

        return recommendations


# =============================================================================
# INFLUENCE ENGINE
# =============================================================================

class InfluenceEngine:
    """Engine for applying influence strategies and techniques."""

    def __init__(self):
        self.strategy_templates: Dict[InfluenceStrategy, List[str]] = {
            InfluenceStrategy.RECIPROCITY: [
                "I've already done {action} for you, so perhaps you could...",
                "Since I helped with {previous}, maybe we could...",
                "Let me first give you {gift}, and then..."
            ],
            InfluenceStrategy.COMMITMENT: [
                "You mentioned you value {value}, so this aligns with...",
                "Given your commitment to {goal}, this would...",
                "Building on your previous decision about {past}, we could..."
            ],
            InfluenceStrategy.SOCIAL_PROOF: [
                "Many successful teams have already...",
                "Industry leaders are adopting this approach...",
                "Studies show that most people..."
            ],
            InfluenceStrategy.AUTHORITY: [
                "Based on extensive research and experience...",
                "The established best practice is...",
                "Expert analysis indicates..."
            ],
            InfluenceStrategy.LIKING: [
                "I really appreciate your perspective on...",
                "We share the same goals here...",
                "Like you, I believe that..."
            ],
            InfluenceStrategy.SCARCITY: [
                "This opportunity is only available for...",
                "Limited resources mean we need to act now...",
                "The window for this approach is closing..."
            ]
        }

        self.technique_implementations: Dict[PersuasionTechnique, Callable] = {
            PersuasionTechnique.FOOT_IN_DOOR: self._foot_in_door,
            PersuasionTechnique.DOOR_IN_FACE: self._door_in_face,
            PersuasionTechnique.ANCHORING: self._anchoring,
            PersuasionTechnique.FRAMING: self._framing,
            PersuasionTechnique.NARRATIVE: self._narrative
        }

    def apply_strategy(
        self,
        strategy: InfluenceStrategy,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Apply an influence strategy to a message."""
        templates = self.strategy_templates.get(strategy, [])
        if not templates:
            return message

        # Select and fill template
        template = random.choice(templates)

        # Replace placeholders with context values
        for key, value in context.items():
            template = template.replace(f"{{{key}}}", str(value))

        return f"{template} {message}"

    def apply_technique(
        self,
        technique: PersuasionTechnique,
        request: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a specific persuasion technique."""
        impl = self.technique_implementations.get(technique)
        if impl:
            return impl(request, context)
        return {"message": request, "technique": technique.value}

    def _foot_in_door(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start with small request, then escalate."""
        return {
            "initial_request": f"Could you help with something small? {context.get('small_task', 'a quick review')}",
            "follow_up": request,
            "escalation_strategy": "gradual"
        }

    def _door_in_face(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start with large request, then retreat to actual."""
        return {
            "initial_request": context.get("large_request", "A complete overhaul"),
            "retreat_to": request,
            "framing": "compromise"
        }

    def _anchoring(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Set an anchor point to influence perception."""
        return {
            "anchor": context.get("anchor", "The maximum would be..."),
            "actual_request": request,
            "relative_framing": "This is much less than the anchor"
        }

    def _framing(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Frame the request in favorable terms."""
        positive_frame = context.get("positive_frame", "opportunity")
        return {
            "positive_framing": f"This is an {positive_frame} to {request}",
            "loss_framing": f"Without this, we risk {context.get('risk', 'falling behind')}",
            "selected_frame": "positive"
        }

    def _narrative(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Embed request in a compelling narrative."""
        return {
            "story_opening": context.get("story", "Imagine a scenario where..."),
            "conflict": context.get("conflict", "The challenge was..."),
            "resolution": f"The solution: {request}",
            "call_to_action": "Let's write that story together"
        }


# =============================================================================
# PERSONA CONTROLLER
# =============================================================================

class PersonaController:
    """
    The master controller for all persona operations.

    Manages persona switching, psychological analysis,
    influence application, and communication optimization.
    """

    def __init__(self):
        self.personas: Dict[str, Persona] = {}
        self.active_persona: Optional[Persona] = None
        self.psychological_analyzer = PsychologicalAnalyzer()
        self.influence_engine = InfluenceEngine()
        self.interaction_history: List[Dict[str, Any]] = []
        self.context_profiles: Dict[str, PsychologicalProfile] = {}

        self._init_default_personas()

    def _init_default_personas(self):
        """Initialize default personas."""
        for name, config in DEFAULT_PERSONAS.items():
            persona = Persona(config)
            self.personas[name] = persona

    def get_persona(self, name: str) -> Optional[Persona]:
        """Get a persona by name."""
        return self.personas.get(name)

    def create_persona(self, config: PersonaConfig) -> Persona:
        """Create a custom persona."""
        persona = Persona(config)
        self.personas[config.name.lower()] = persona
        return persona

    def activate_persona(self, name: str) -> bool:
        """Activate a persona."""
        persona = self.personas.get(name)
        if persona:
            if self.active_persona:
                self.active_persona.active = False
            persona.active = True
            persona.last_used = datetime.now()
            self.active_persona = persona
            logger.info(f"Activated persona: {persona.config.name}")
            return True
        return False

    def select_optimal_persona(
        self,
        context: CommunicationContext
    ) -> Persona:
        """Select the optimal persona for a context."""
        scores: Dict[str, float] = {}

        for name, persona in self.personas.items():
            score = 0.0

            # Match communication style to target preferences
            if context.target_profile:
                if persona.config.communication_style in context.target_profile.communication_preferences:
                    score += 2.0

                # Match influence strategies
                best_influence = context.target_profile.get_best_influence()
                if best_influence in persona.config.influence_preferences:
                    score += 1.5

            # Consider goals
            for goal in context.goals:
                if any(goal.lower() in area.lower() for area in persona.config.expertise_areas):
                    score += 1.0

            # Factor in success rate
            score *= persona.success_rate

            scores[name] = score

        # Select highest scoring persona
        best_name = max(scores, key=scores.get)
        best_persona = self.personas[best_name]

        self.activate_persona(best_name)
        return best_persona

    async def generate_message(
        self,
        content: str,
        context: CommunicationContext = None
    ) -> Message:
        """Generate a message using active persona and influence strategies."""
        if not self.active_persona:
            self.activate_persona("expert")  # Default fallback

        persona = self.active_persona

        # Select influence strategies based on context
        strategies = []
        techniques = []

        if context and context.target_profile:
            recommendation = self.psychological_analyzer.recommend_strategy(
                context.target_profile,
                context.goals[0] if context.goals else ""
            )
            strategies = [recommendation["primary_strategy"]]
            techniques = recommendation["techniques"]

        # Apply persona styling
        styled_content = persona.adapt_message(content)

        # Apply influence strategies
        for strategy in strategies[:2]:  # Max 2 strategies per message
            styled_content = self.influence_engine.apply_strategy(
                strategy,
                styled_content,
                context.__dict__ if context else {}
            )

        # Create message
        message = Message(
            content=styled_content,
            persona_id=persona.id,
            style=persona.config.communication_style,
            tone=persona.config.emotional_tone,
            influence_strategies=strategies,
            persuasion_techniques=techniques
        )

        # Record interaction
        persona.interaction_count += 1
        self.interaction_history.append({
            "persona": persona.config.name,
            "message_id": message.id,
            "strategies": [s.value for s in strategies],
            "timestamp": message.timestamp.isoformat()
        })

        return message

    def analyze_target(
        self,
        identifier: str,
        communications: List[str]
    ) -> PsychologicalProfile:
        """Analyze a target from their communications."""
        profile = self.psychological_analyzer.create_profile(identifier)

        # Analyze each communication
        for text in communications:
            self.psychological_analyzer.analyze_communication(text, profile)

        # Set default susceptibilities based on communication patterns
        if profile.communication_preferences:
            if CommunicationStyle.FORMAL in profile.communication_preferences:
                profile.influence_susceptibility[InfluenceStrategy.AUTHORITY] = 0.8
            if CommunicationStyle.EMPATHETIC in profile.communication_preferences:
                profile.influence_susceptibility[InfluenceStrategy.LIKING] = 0.8

        self.context_profiles[identifier] = profile
        return profile

    def record_result(
        self,
        message_id: str,
        success: bool,
        engagement: float = 0.5
    ):
        """Record the result of an influence attempt."""
        # Update persona success rate
        if self.active_persona:
            total = self.active_persona.interaction_count
            current_rate = self.active_persona.success_rate
            if success:
                new_rate = (current_rate * (total - 1) + 1.0) / total
            else:
                new_rate = (current_rate * (total - 1) + 0.0) / total
            self.active_persona.success_rate = new_rate

        # Record in history
        for record in reversed(self.interaction_history):
            if record.get("message_id") == message_id:
                record["success"] = success
                record["engagement"] = engagement
                break

    def get_persona_stats(self) -> Dict[str, Any]:
        """Get statistics for all personas."""
        return {
            name: persona.get_status()
            for name, persona in self.personas.items()
        }

    def get_active_persona_info(self) -> Optional[Dict[str, Any]]:
        """Get info about active persona."""
        if self.active_persona:
            return self.active_persona.get_status()
        return None

    def get_recommendation_for_context(
        self,
        context: CommunicationContext
    ) -> Dict[str, Any]:
        """Get comprehensive recommendation for a context."""
        # Analyze target if profile exists
        if context.target_profile:
            strategy_rec = self.psychological_analyzer.recommend_strategy(
                context.target_profile,
                context.goals[0] if context.goals else ""
            )
        else:
            strategy_rec = {
                "primary_strategy": InfluenceStrategy.LOGIC,
                "techniques": [PersuasionTechnique.FRAMING],
                "communication_approach": CommunicationStyle.FORMAL
            }

        # Select optimal persona
        optimal_persona = self.select_optimal_persona(context)

        return {
            "recommended_persona": optimal_persona.config.name,
            "communication_style": strategy_rec.get("communication_approach", CommunicationStyle.FORMAL).value,
            "primary_strategy": strategy_rec["primary_strategy"].value,
            "techniques": [t.value for t in strategy_rec.get("techniques", [])],
            "key_messages": strategy_rec.get("key_messages", []),
            "avoid": strategy_rec.get("avoid", [])
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Persona Controller."""
    print("=" * 70)
    print("BAEL - PERSONA CONTROLLER DEMO")
    print("Dynamic Identity Management & Psychological Influence")
    print("=" * 70)
    print()

    # Create controller
    controller = PersonaController()

    # 1. Show available personas
    print("1. AVAILABLE PERSONAS:")
    print("-" * 40)

    for name, persona in list(controller.personas.items())[:5]:
        print(f"   {persona.config.name}:")
        print(f"   - Type: {persona.config.persona_type.value}")
        print(f"   - Style: {persona.config.communication_style.value}")
        print(f"   - Tone: {persona.config.emotional_tone.value}")
        print()

    # 2. Activate persona
    print("2. ACTIVATING PERSONA:")
    print("-" * 40)

    controller.activate_persona("expert")
    active = controller.get_active_persona_info()
    print(f"   Active: {active['name']}")
    print(f"   Style: {active['style']}")
    print()

    # 3. Analyze a target
    print("3. PSYCHOLOGICAL ANALYSIS:")
    print("-" * 40)

    target_communications = [
        "Please could you provide a detailed technical analysis?",
        "I would greatly appreciate a thorough explanation of the methodology.",
        "I'm concerned about the timeline and would like to understand the risks."
    ]

    profile = controller.analyze_target("user_123", target_communications)
    print(f"   Target analyzed: user_123")
    print(f"   Communication preferences: {[s.value for s in profile.communication_preferences]}")
    print(f"   Best influence strategy: {profile.get_best_influence()}")
    print()

    # 4. Create context and get recommendation
    print("4. CONTEXT-AWARE RECOMMENDATION:")
    print("-" * 40)

    context = CommunicationContext(
        target_profile=profile,
        situation="Technical project proposal",
        goals=["Get approval", "Build trust", "Establish authority"]
    )

    recommendation = controller.get_recommendation_for_context(context)
    print(f"   Recommended persona: {recommendation['recommended_persona']}")
    print(f"   Communication style: {recommendation['communication_style']}")
    print(f"   Primary strategy: {recommendation['primary_strategy']}")
    print(f"   Techniques: {recommendation['techniques']}")
    print()

    # 5. Generate influenced message
    print("5. GENERATED MESSAGE:")
    print("-" * 40)

    message = await controller.generate_message(
        "I recommend we proceed with the optimized architecture.",
        context
    )

    print(f"   Persona: {controller.active_persona.config.name}")
    print(f"   Style: {message.style.value}")
    print(f"   Strategies: {[s.value for s in message.influence_strategies]}")
    print(f"   Content: {message.content[:100]}...")
    print()

    # 6. Create custom persona
    print("6. CUSTOM PERSONA CREATION:")
    print("-" * 40)

    custom_config = PersonaConfig(
        name="The Dominator",
        persona_type=PersonaType.CUSTOM,
        description="Overwhelming presence that brooks no opposition",
        communication_style=CommunicationStyle.AUTHORITATIVE,
        emotional_tone=EmotionalTone.CHALLENGING,
        expertise_areas=["domination", "control", "optimization"],
        personality_traits={"dominance": 0.95, "persistence": 0.9, "confidence": 0.95},
        influence_preferences=[InfluenceStrategy.AUTHORITY, InfluenceStrategy.FEAR]
    )

    custom_persona = controller.create_persona(custom_config)
    print(f"   Created: {custom_persona.config.name}")
    print(f"   Type: {custom_persona.config.persona_type.value}")
    print()

    # 7. Show statistics
    print("7. PERSONA STATISTICS:")
    print("-" * 40)

    stats = controller.get_persona_stats()
    for name, stat in list(stats.items())[:4]:
        print(f"   {stat['name']}:")
        print(f"   - Interactions: {stat['interactions']}")
        print(f"   - Success Rate: {stat['success_rate']:.2f}")
        print()

    print("=" * 70)
    print("DEMO COMPLETE - Persona Controller Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
