"""
BAEL - Psychological Warfare & Manipulation Engine
====================================================

Advanced psychological intelligence system.

Features:
1. Persuasion Tactics - Cialdini's principles, NLP patterns
2. Dark Psychology - Manipulation detection and defense
3. Influence Mapping - Social network analysis
4. Cognitive Bias Exploitation - Strategic advantage
5. Emotional Intelligence - Sentiment and emotion analysis
6. Personality Profiling - Big Five, MBTI, Dark Triad
7. Negotiation AI - Win-win and dominance strategies
8. Propaganda Analysis - Detecting and countering
9. Trust Building - Rapport and relationship
10. Mind Games - Strategic psychological operations

This module enables Ba'el to understand and navigate
the complex landscape of human psychology.

WARNING: For ethical use only. Manipulation detection,
not exploitation.
"""

import asyncio
import json
import logging
import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger("BAEL.PSYOPS")


# ============================================================================
# PERSUASION PRINCIPLES (Cialdini's 6+1)
# ============================================================================

class PersuasionPrinciple(Enum):
    """Robert Cialdini's principles of persuasion."""
    RECIPROCITY = "reciprocity"  # Give to receive
    COMMITMENT = "commitment"  # Consistency with past actions
    SOCIAL_PROOF = "social_proof"  # Following the crowd
    AUTHORITY = "authority"  # Expert influence
    LIKING = "liking"  # We say yes to those we like
    SCARCITY = "scarcity"  # Limited availability
    UNITY = "unity"  # Shared identity (7th principle)


class NLPPattern(Enum):
    """NLP language patterns for influence."""
    EMBEDDED_COMMAND = "embedded_command"
    PRESUPPOSITION = "presupposition"
    AMBIGUITY = "ambiguity"
    PACING_LEADING = "pacing_leading"
    ANCHORING = "anchoring"
    REFRAMING = "reframing"
    META_MODEL = "meta_model"
    MILTON_MODEL = "milton_model"
    DOUBLE_BIND = "double_bind"
    FUTURE_PACING = "future_pacing"


class CognitiveBias(Enum):
    """Common cognitive biases to understand/counter."""
    CONFIRMATION_BIAS = "confirmation_bias"
    ANCHORING_BIAS = "anchoring_bias"
    AVAILABILITY_HEURISTIC = "availability_heuristic"
    BANDWAGON_EFFECT = "bandwagon_effect"
    DUNNING_KRUGER = "dunning_kruger"
    SUNK_COST_FALLACY = "sunk_cost_fallacy"
    HALO_EFFECT = "halo_effect"
    NEGATIVITY_BIAS = "negativity_bias"
    OPTIMISM_BIAS = "optimism_bias"
    FRAMING_EFFECT = "framing_effect"
    LOSS_AVERSION = "loss_aversion"
    STATUS_QUO_BIAS = "status_quo_bias"
    AUTHORITY_BIAS = "authority_bias"
    INGROUP_BIAS = "ingroup_bias"
    RECENCY_BIAS = "recency_bias"


class ManipulationTactic(Enum):
    """Dark psychology tactics to detect/defend."""
    GASLIGHTING = "gaslighting"
    LOVE_BOMBING = "love_bombing"
    TRIANGULATION = "triangulation"
    SILENT_TREATMENT = "silent_treatment"
    PROJECTION = "projection"
    GUILT_TRIPPING = "guilt_tripping"
    MOVING_GOALPOSTS = "moving_goalposts"
    WORD_SALAD = "word_salad"
    FEAR_MONGERING = "fear_mongering"
    FALSE_DILEMMA = "false_dilemma"
    APPEAL_TO_EMOTION = "appeal_to_emotion"
    AD_HOMINEM = "ad_hominem"
    STRAWMAN = "strawman"
    RED_HERRING = "red_herring"
    SLIPPERY_SLOPE = "slippery_slope"


class Emotion(Enum):
    """Basic emotions (Plutchik's wheel)."""
    JOY = "joy"
    TRUST = "trust"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    ANGER = "anger"
    ANTICIPATION = "anticipation"
    # Secondary emotions
    LOVE = "love"  # Joy + Trust
    SUBMISSION = "submission"  # Trust + Fear
    AWE = "awe"  # Fear + Surprise
    DISAPPOINTMENT = "disappointment"  # Surprise + Sadness
    REMORSE = "remorse"  # Sadness + Disgust
    CONTEMPT = "contempt"  # Disgust + Anger
    AGGRESSIVENESS = "aggressiveness"  # Anger + Anticipation
    OPTIMISM = "optimism"  # Anticipation + Joy


# ============================================================================
# PERSONALITY MODELS
# ============================================================================

@dataclass
class BigFiveProfile:
    """Big Five personality traits (OCEAN model)."""
    openness: float = 0.5  # 0-1 scale
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5
    
    def get_dominant_traits(self) -> List[str]:
        """Get traits above 0.7."""
        traits = []
        if self.openness > 0.7:
            traits.append("open")
        if self.conscientiousness > 0.7:
            traits.append("conscientious")
        if self.extraversion > 0.7:
            traits.append("extraverted")
        if self.agreeableness > 0.7:
            traits.append("agreeable")
        if self.neuroticism > 0.7:
            traits.append("neurotic")
        return traits
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism
        }


@dataclass
class DarkTriadProfile:
    """Dark Triad personality traits."""
    narcissism: float = 0.0  # 0-1 scale
    machiavellianism: float = 0.0
    psychopathy: float = 0.0
    
    @property
    def is_dark(self) -> bool:
        """Check if any trait is elevated."""
        return any([
            self.narcissism > 0.6,
            self.machiavellianism > 0.6,
            self.psychopathy > 0.6
        ])
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "narcissism": self.narcissism,
            "machiavellianism": self.machiavellianism,
            "psychopathy": self.psychopathy,
            "is_dark": self.is_dark
        }


@dataclass
class MBTIType:
    """Myers-Briggs Type Indicator."""
    extraversion_introversion: str = "I"  # E or I
    sensing_intuition: str = "N"  # S or N
    thinking_feeling: str = "T"  # T or F
    judging_perceiving: str = "P"  # J or P
    
    @property
    def type_code(self) -> str:
        return f"{self.extraversion_introversion}{self.sensing_intuition}{self.thinking_feeling}{self.judging_perceiving}"
    
    @property
    def cognitive_functions(self) -> List[str]:
        """Get cognitive function stack."""
        stacks = {
            "INTJ": ["Ni", "Te", "Fi", "Se"],
            "INTP": ["Ti", "Ne", "Si", "Fe"],
            "ENTJ": ["Te", "Ni", "Se", "Fi"],
            "ENTP": ["Ne", "Ti", "Fe", "Si"],
            "INFJ": ["Ni", "Fe", "Ti", "Se"],
            "INFP": ["Fi", "Ne", "Si", "Te"],
            "ENFJ": ["Fe", "Ni", "Se", "Ti"],
            "ENFP": ["Ne", "Fi", "Te", "Si"],
            "ISTJ": ["Si", "Te", "Fi", "Ne"],
            "ISFJ": ["Si", "Fe", "Ti", "Ne"],
            "ESTJ": ["Te", "Si", "Ne", "Fi"],
            "ESFJ": ["Fe", "Si", "Ne", "Ti"],
            "ISTP": ["Ti", "Se", "Ni", "Fe"],
            "ISFP": ["Fi", "Se", "Ni", "Te"],
            "ESTP": ["Se", "Ti", "Fe", "Ni"],
            "ESFP": ["Se", "Fi", "Te", "Ni"]
        }
        return stacks.get(self.type_code, [])


# ============================================================================
# ANALYSIS CLASSES
# ============================================================================

@dataclass
class EmotionalAnalysis:
    """Result of emotional analysis."""
    text: str
    primary_emotion: Emotion
    secondary_emotions: List[Tuple[Emotion, float]]
    intensity: float  # 0-1
    valence: float  # -1 to 1 (negative to positive)
    arousal: float  # 0-1 (calm to excited)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text[:100] + "..." if len(self.text) > 100 else self.text,
            "primary_emotion": self.primary_emotion.value,
            "secondary_emotions": [(e.value, s) for e, s in self.secondary_emotions],
            "intensity": self.intensity,
            "valence": self.valence,
            "arousal": self.arousal
        }


@dataclass
class ManipulationDetection:
    """Result of manipulation detection."""
    text: str
    is_manipulative: bool
    tactics_detected: List[Tuple[ManipulationTactic, float]]
    severity: float  # 0-1
    defense_recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_manipulative": self.is_manipulative,
            "tactics": [(t.value, s) for t, s in self.tactics_detected],
            "severity": self.severity,
            "recommendations": self.defense_recommendations
        }


@dataclass
class PersuasionAnalysis:
    """Analysis of persuasion in text."""
    text: str
    principles_used: List[Tuple[PersuasionPrinciple, float]]
    nlp_patterns: List[Tuple[NLPPattern, str]]
    biases_exploited: List[CognitiveBias]
    effectiveness_score: float
    ethical_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "principles": [(p.value, s) for p, s in self.principles_used],
            "nlp_patterns": [(p.value, ex) for p, ex in self.nlp_patterns],
            "biases_exploited": [b.value for b in self.biases_exploited],
            "effectiveness": self.effectiveness_score,
            "ethical_score": self.ethical_score
        }


# ============================================================================
# PSYCHOLOGICAL WARFARE ENGINE
# ============================================================================

class PsychologicalWarfareEngine:
    """
    Master engine for psychological operations.
    
    Provides:
    - Emotional intelligence
    - Manipulation detection
    - Persuasion analysis
    - Personality profiling
    - Influence strategies
    """
    
    def __init__(self):
        # Emotion keywords
        self.emotion_keywords: Dict[Emotion, List[str]] = {
            Emotion.JOY: ["happy", "joy", "excited", "thrilled", "delighted", "elated", "wonderful"],
            Emotion.TRUST: ["trust", "believe", "faith", "confident", "reliable", "safe", "secure"],
            Emotion.FEAR: ["afraid", "scared", "terrified", "anxious", "worried", "panic", "dread"],
            Emotion.SURPRISE: ["surprised", "shocked", "amazed", "astonished", "unexpected", "wow"],
            Emotion.SADNESS: ["sad", "depressed", "unhappy", "miserable", "grief", "sorrow", "cry"],
            Emotion.DISGUST: ["disgusted", "revolted", "sick", "gross", "awful", "repulsed"],
            Emotion.ANGER: ["angry", "furious", "mad", "rage", "hate", "annoyed", "frustrated"],
            Emotion.ANTICIPATION: ["excited", "eager", "looking forward", "can't wait", "hopeful"]
        }
        
        # Manipulation patterns
        self.manipulation_patterns: Dict[ManipulationTactic, List[str]] = {
            ManipulationTactic.GASLIGHTING: [
                r"you're (crazy|imagining|overreacting)",
                r"that never happened",
                r"you're too sensitive",
                r"no one else thinks that"
            ],
            ManipulationTactic.GUILT_TRIPPING: [
                r"after all I've done",
                r"if you really loved me",
                r"you owe me",
                r"you're being selfish"
            ],
            ManipulationTactic.FEAR_MONGERING: [
                r"terrible things will happen",
                r"you'll regret this",
                r"you have no choice",
                r"it's too dangerous"
            ],
            ManipulationTactic.FALSE_DILEMMA: [
                r"either .* or",
                r"you're with (me|us) or against",
                r"there are only two options",
                r"it's black or white"
            ]
        }
        
        # Persuasion indicators
        self.persuasion_indicators: Dict[PersuasionPrinciple, List[str]] = {
            PersuasionPrinciple.RECIPROCITY: [
                "free", "gift", "bonus", "because I helped you"
            ],
            PersuasionPrinciple.SCARCITY: [
                "limited time", "only", "exclusive", "last chance", "hurry", "few left"
            ],
            PersuasionPrinciple.AUTHORITY: [
                "expert", "doctor", "scientist", "research shows", "studies prove"
            ],
            PersuasionPrinciple.SOCIAL_PROOF: [
                "everyone", "millions", "best-selling", "most popular", "trending"
            ],
            PersuasionPrinciple.LIKING: [
                "friend", "like you", "similar", "we", "together"
            ],
            PersuasionPrinciple.COMMITMENT: [
                "you agreed", "you said", "consistent with", "you've already"
            ]
        }
        
        logger.info("PsychologicalWarfareEngine initialized")
    
    # -------------------------------------------------------------------------
    # EMOTIONAL ANALYSIS
    # -------------------------------------------------------------------------
    
    def analyze_emotion(self, text: str) -> EmotionalAnalysis:
        """Analyze emotional content of text."""
        text_lower = text.lower()
        
        # Count emotion keywords
        emotion_scores: Dict[Emotion, float] = defaultdict(float)
        
        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                count = text_lower.count(keyword)
                emotion_scores[emotion] += count
        
        # Normalize scores
        total = sum(emotion_scores.values()) or 1
        for emotion in emotion_scores:
            emotion_scores[emotion] /= total
        
        # Get primary emotion
        if emotion_scores:
            primary = max(emotion_scores.items(), key=lambda x: x[1])
            primary_emotion = primary[0]
        else:
            primary_emotion = Emotion.ANTICIPATION
        
        # Get secondary emotions
        sorted_emotions = sorted(
            emotion_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        secondary = sorted_emotions[1:4]
        
        # Calculate valence (positive vs negative)
        positive_emotions = {Emotion.JOY, Emotion.TRUST, Emotion.ANTICIPATION}
        negative_emotions = {Emotion.FEAR, Emotion.SADNESS, Emotion.DISGUST, Emotion.ANGER}
        
        positive_score = sum(emotion_scores[e] for e in positive_emotions)
        negative_score = sum(emotion_scores[e] for e in negative_emotions)
        
        valence = positive_score - negative_score  # -1 to 1
        
        # Calculate arousal (high energy vs low)
        high_arousal = {Emotion.JOY, Emotion.ANGER, Emotion.FEAR, Emotion.SURPRISE}
        low_arousal = {Emotion.SADNESS, Emotion.TRUST}
        
        high_score = sum(emotion_scores[e] for e in high_arousal)
        low_score = sum(emotion_scores[e] for e in low_arousal)
        
        arousal = (high_score - low_score + 1) / 2  # 0 to 1
        
        # Intensity based on punctuation and caps
        exclamation_count = text.count("!")
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        intensity = min((exclamation_count * 0.1 + caps_ratio) * 2, 1.0)
        
        return EmotionalAnalysis(
            text=text,
            primary_emotion=primary_emotion,
            secondary_emotions=secondary,
            intensity=intensity,
            valence=valence,
            arousal=arousal
        )
    
    # -------------------------------------------------------------------------
    # MANIPULATION DETECTION
    # -------------------------------------------------------------------------
    
    def detect_manipulation(self, text: str) -> ManipulationDetection:
        """Detect manipulation tactics in text."""
        text_lower = text.lower()
        
        detected: List[Tuple[ManipulationTactic, float]] = []
        
        for tactic, patterns in self.manipulation_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    # Higher confidence for more specific matches
                    confidence = 0.7 + (len(pattern) / 50) * 0.3
                    detected.append((tactic, min(confidence, 1.0)))
                    break
        
        # Check for other indicators
        # Excessive use of absolutes
        absolutes = ["always", "never", "everyone", "no one", "all", "none"]
        absolute_count = sum(text_lower.count(a) for a in absolutes)
        if absolute_count > 3:
            detected.append((ManipulationTactic.STRAWMAN, 0.5))
        
        # Is manipulative?
        is_manipulative = len(detected) > 0
        
        # Severity
        severity = min(sum(s for _, s in detected) / 3, 1.0)
        
        # Defense recommendations
        recommendations = []
        for tactic, _ in detected:
            recommendations.extend(self._get_defense_for_tactic(tactic))
        
        return ManipulationDetection(
            text=text,
            is_manipulative=is_manipulative,
            tactics_detected=detected,
            severity=severity,
            defense_recommendations=list(set(recommendations))[:5]
        )
    
    def _get_defense_for_tactic(self, tactic: ManipulationTactic) -> List[str]:
        """Get defense recommendations for a tactic."""
        defenses = {
            ManipulationTactic.GASLIGHTING: [
                "Trust your own perception and memory",
                "Keep a journal of events",
                "Seek third-party validation"
            ],
            ManipulationTactic.GUILT_TRIPPING: [
                "Recognize that guilt is being weaponized",
                "Maintain your boundaries",
                "You are not responsible for others' emotions"
            ],
            ManipulationTactic.FEAR_MONGERING: [
                "Ask for evidence",
                "Consider other perspectives",
                "Don't make decisions under pressure"
            ],
            ManipulationTactic.FALSE_DILEMMA: [
                "Look for third options",
                "Question the binary framing",
                "Take time to consider alternatives"
            ]
        }
        return defenses.get(tactic, ["Stay aware and question motives"])
    
    # -------------------------------------------------------------------------
    # PERSUASION ANALYSIS
    # -------------------------------------------------------------------------
    
    def analyze_persuasion(self, text: str) -> PersuasionAnalysis:
        """Analyze persuasion techniques in text."""
        text_lower = text.lower()
        
        principles: List[Tuple[PersuasionPrinciple, float]] = []
        
        for principle, indicators in self.persuasion_indicators.items():
            score = sum(1 for ind in indicators if ind in text_lower) / len(indicators)
            if score > 0:
                principles.append((principle, score))
        
        # Detect NLP patterns
        nlp_patterns: List[Tuple[NLPPattern, str]] = []
        
        # Embedded commands (imperative in middle of sentence)
        embedded_match = re.search(r'[^.!?]*\b(imagine|notice|feel|realize|understand)\b[^.!?]*', text_lower)
        if embedded_match:
            nlp_patterns.append((NLPPattern.EMBEDDED_COMMAND, embedded_match.group()))
        
        # Presuppositions (assuming something true)
        presup_patterns = [r"when you", r"as you", r"after you", r"before you"]
        for pattern in presup_patterns:
            match = re.search(pattern, text_lower)
            if match:
                nlp_patterns.append((NLPPattern.PRESUPPOSITION, match.group()))
                break
        
        # Reframing
        if "but" in text_lower or "however" in text_lower:
            nlp_patterns.append((NLPPattern.REFRAMING, "but/however reframe"))
        
        # Biases exploited
        biases: List[CognitiveBias] = []
        if any(p[0] == PersuasionPrinciple.SCARCITY for p in principles):
            biases.append(CognitiveBias.LOSS_AVERSION)
        if any(p[0] == PersuasionPrinciple.SOCIAL_PROOF for p in principles):
            biases.append(CognitiveBias.BANDWAGON_EFFECT)
        if any(p[0] == PersuasionPrinciple.AUTHORITY for p in principles):
            biases.append(CognitiveBias.AUTHORITY_BIAS)
        
        # Effectiveness score
        effectiveness = min(len(principles) * 0.2 + len(nlp_patterns) * 0.15, 1.0)
        
        # Ethical score (higher = more ethical)
        ethical_score = 1.0 - (len(biases) * 0.15) - (effectiveness * 0.2)
        ethical_score = max(ethical_score, 0.0)
        
        return PersuasionAnalysis(
            text=text,
            principles_used=principles,
            nlp_patterns=nlp_patterns,
            biases_exploited=biases,
            effectiveness_score=effectiveness,
            ethical_score=ethical_score
        )
    
    # -------------------------------------------------------------------------
    # PERSONALITY PROFILING
    # -------------------------------------------------------------------------
    
    def infer_big_five(self, texts: List[str]) -> BigFiveProfile:
        """Infer Big Five personality from text samples."""
        combined = " ".join(texts).lower()
        word_count = len(combined.split())
        
        # Simplified inference based on word usage
        
        # Openness: abstract words, creativity
        openness_words = ["imagine", "create", "idea", "art", "philosophy", "curious", "novel"]
        openness = sum(combined.count(w) for w in openness_words) / max(word_count, 1) * 50
        
        # Conscientiousness: order, planning
        conscientious_words = ["plan", "organize", "careful", "detail", "schedule", "efficient"]
        conscientiousness = sum(combined.count(w) for w in conscientious_words) / max(word_count, 1) * 50
        
        # Extraversion: social, energetic
        extravert_words = ["party", "friend", "social", "fun", "exciting", "people", "talk"]
        extraversion = sum(combined.count(w) for w in extravert_words) / max(word_count, 1) * 50
        
        # Agreeableness: cooperative, trusting
        agreeable_words = ["help", "kind", "trust", "care", "cooperate", "gentle", "please"]
        agreeableness = sum(combined.count(w) for w in agreeable_words) / max(word_count, 1) * 50
        
        # Neuroticism: anxiety, negative emotion
        neurotic_words = ["worry", "anxious", "nervous", "stress", "fear", "upset", "angry"]
        neuroticism = sum(combined.count(w) for w in neurotic_words) / max(word_count, 1) * 50
        
        # Normalize to 0-1 scale
        return BigFiveProfile(
            openness=min(openness, 1.0),
            conscientiousness=min(conscientiousness, 1.0),
            extraversion=min(extraversion, 1.0),
            agreeableness=min(agreeableness, 1.0),
            neuroticism=min(neuroticism, 1.0)
        )
    
    def detect_dark_triad(self, texts: List[str]) -> DarkTriadProfile:
        """Detect Dark Triad traits from text samples."""
        combined = " ".join(texts).lower()
        word_count = len(combined.split())
        
        # Narcissism indicators
        narcissism_words = ["i", "me", "my", "best", "superior", "special", "admire"]
        narcissism = sum(combined.count(w) for w in narcissism_words) / max(word_count, 1) * 10
        
        # Machiavellianism indicators
        mach_words = ["strategy", "manipulate", "control", "power", "advantage", "exploit"]
        machiavellianism = sum(combined.count(w) for w in mach_words) / max(word_count, 1) * 20
        
        # Psychopathy indicators
        psych_words = ["don't care", "boring", "thrill", "risk", "whatever", "blame"]
        psychopathy = sum(combined.count(w) for w in psych_words) / max(word_count, 1) * 20
        
        return DarkTriadProfile(
            narcissism=min(narcissism, 1.0),
            machiavellianism=min(machiavellianism, 1.0),
            psychopathy=min(psychopathy, 1.0)
        )
    
    # -------------------------------------------------------------------------
    # INFLUENCE STRATEGIES
    # -------------------------------------------------------------------------
    
    def generate_influence_strategy(
        self,
        target_profile: BigFiveProfile,
        goal: str
    ) -> Dict[str, Any]:
        """Generate ethical influence strategy based on personality."""
        strategies = []
        
        # Tailor approach to personality
        if target_profile.openness > 0.6:
            strategies.append({
                "approach": "Present novel ideas and creative angles",
                "reasoning": "High openness responds to novelty"
            })
        else:
            strategies.append({
                "approach": "Use proven, traditional approaches",
                "reasoning": "Lower openness prefers familiar"
            })
        
        if target_profile.conscientiousness > 0.6:
            strategies.append({
                "approach": "Provide detailed plans and data",
                "reasoning": "High conscientiousness values thoroughness"
            })
        else:
            strategies.append({
                "approach": "Keep it flexible and big-picture",
                "reasoning": "Lower conscientiousness prefers spontaneity"
            })
        
        if target_profile.extraversion > 0.6:
            strategies.append({
                "approach": "Engage in discussion, be enthusiastic",
                "reasoning": "Extraverts energized by interaction"
            })
        else:
            strategies.append({
                "approach": "Give space for reflection, use writing",
                "reasoning": "Introverts need processing time"
            })
        
        if target_profile.agreeableness > 0.6:
            strategies.append({
                "approach": "Emphasize harmony and mutual benefit",
                "reasoning": "High agreeableness values cooperation"
            })
        else:
            strategies.append({
                "approach": "Appeal to self-interest and logic",
                "reasoning": "Lower agreeableness is more skeptical"
            })
        
        if target_profile.neuroticism > 0.6:
            strategies.append({
                "approach": "Provide reassurance and minimize risks",
                "reasoning": "High neuroticism needs security"
            })
        else:
            strategies.append({
                "approach": "Present opportunities and possibilities",
                "reasoning": "Lower neuroticism handles uncertainty"
            })
        
        return {
            "goal": goal,
            "target_profile": target_profile.to_dict(),
            "strategies": strategies,
            "recommended_persuasion_principles": self._get_principles_for_profile(target_profile),
            "ethical_guidelines": [
                "Always be truthful",
                "Respect autonomy",
                "Seek mutual benefit",
                "Allow informed consent"
            ]
        }
    
    def _get_principles_for_profile(
        self,
        profile: BigFiveProfile
    ) -> List[PersuasionPrinciple]:
        """Get effective persuasion principles for a personality."""
        principles = []
        
        if profile.agreeableness > 0.5:
            principles.append(PersuasionPrinciple.RECIPROCITY)
            principles.append(PersuasionPrinciple.LIKING)
        
        if profile.conscientiousness > 0.5:
            principles.append(PersuasionPrinciple.COMMITMENT)
            principles.append(PersuasionPrinciple.AUTHORITY)
        
        if profile.neuroticism > 0.5:
            principles.append(PersuasionPrinciple.SOCIAL_PROOF)
        else:
            principles.append(PersuasionPrinciple.SCARCITY)
        
        if profile.openness < 0.5:
            principles.append(PersuasionPrinciple.SOCIAL_PROOF)
        
        return principles
    
    # -------------------------------------------------------------------------
    # NEGOTIATION
    # -------------------------------------------------------------------------
    
    def analyze_negotiation_position(
        self,
        my_position: Dict[str, Any],
        their_position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze negotiation positions and suggest strategies."""
        
        # Find common ground
        my_priorities = set(my_position.get("priorities", []))
        their_priorities = set(their_position.get("priorities", []))
        common = my_priorities & their_priorities
        
        # Find conflicts
        my_must_haves = set(my_position.get("must_have", []))
        their_must_haves = set(their_position.get("must_have", []))
        conflicts = my_must_haves & their_must_haves
        
        # BATNA analysis
        my_batna = my_position.get("batna_strength", 5)
        their_batna = their_position.get("batna_strength", 5)
        
        leverage = (my_batna - their_batna) / 10  # -1 to 1
        
        return {
            "common_ground": list(common),
            "potential_conflicts": list(conflicts),
            "your_leverage": leverage,
            "recommended_style": self._get_negotiation_style(leverage),
            "opening_strategy": self._get_opening_strategy(leverage),
            "concession_strategy": [
                "Start with your least important issues",
                "Bundle concessions together",
                "Always get something in return"
            ],
            "warning_signs": [
                "Artificial deadlines",
                "Good cop / bad cop",
                "Nibbling (last-minute requests)"
            ]
        }
    
    def _get_negotiation_style(self, leverage: float) -> str:
        """Get recommended negotiation style based on leverage."""
        if leverage > 0.3:
            return "Competitive - you have strong position"
        elif leverage < -0.3:
            return "Collaborative - find creative solutions"
        else:
            return "Compromising - balanced give and take"
    
    def _get_opening_strategy(self, leverage: float) -> str:
        """Get opening strategy recommendation."""
        if leverage > 0.3:
            return "Open high/aggressive - anchor the negotiation in your favor"
        elif leverage < -0.3:
            return "Open collaborative - explore interests before positions"
        else:
            return "Open reasonably - signal willingness to negotiate"


# ============================================================================
# SINGLETON
# ============================================================================

_psyops_engine: Optional[PsychologicalWarfareEngine] = None


def get_psyops_engine() -> PsychologicalWarfareEngine:
    """Get the global psyops engine."""
    global _psyops_engine
    if _psyops_engine is None:
        _psyops_engine = PsychologicalWarfareEngine()
    return _psyops_engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate psychological warfare engine."""
    print("=" * 60)
    print("PSYCHOLOGICAL WARFARE ENGINE")
    print("=" * 60)
    
    engine = get_psyops_engine()
    
    # Emotional analysis
    print("\n--- Emotional Analysis ---")
    test_text = "I'm so excited and happy about this amazing opportunity! This is wonderful news!"
    analysis = engine.analyze_emotion(test_text)
    print(f"Text: {test_text}")
    print(json.dumps(analysis.to_dict(), indent=2))
    
    # Manipulation detection
    print("\n--- Manipulation Detection ---")
    manip_text = "After all I've done for you, you're being selfish. If you really loved me, you would do this."
    detection = engine.detect_manipulation(manip_text)
    print(f"Text: {manip_text}")
    print(json.dumps(detection.to_dict(), indent=2))
    
    # Persuasion analysis
    print("\n--- Persuasion Analysis ---")
    persuade_text = "Limited time offer! Experts agree this is the best product. Join millions of satisfied customers."
    persuasion = engine.analyze_persuasion(persuade_text)
    print(f"Text: {persuade_text}")
    print(json.dumps(persuasion.to_dict(), indent=2))
    
    # Personality inference
    print("\n--- Personality Inference ---")
    sample_texts = [
        "I love exploring new ideas and creating art",
        "I carefully plan everything in detail",
        "Sometimes I worry about what could go wrong"
    ]
    big_five = engine.infer_big_five(sample_texts)
    print("Inferred Big Five:")
    print(json.dumps(big_five.to_dict(), indent=2))
    
    # Influence strategy
    print("\n--- Influence Strategy ---")
    strategy = engine.generate_influence_strategy(big_five, "Get approval for project")
    print(json.dumps(strategy, indent=2, default=str))
    
    print("\n" + "=" * 60)
    print("PSYCHOLOGICAL ANALYSIS COMPLETE")


if __name__ == "__main__":
    asyncio.run(demo())
