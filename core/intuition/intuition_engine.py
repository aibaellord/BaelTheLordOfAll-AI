#!/usr/bin/env python3
"""
BAEL - Intuition Engine
Advanced intuitive reasoning and pattern recognition.

Features:
- Implicit pattern recognition
- Fast heuristic judgments
- Gut feeling simulation
- Recognition-primed decisions
- Chunking and expertise
- Implicit learning
"""

import asyncio
import copy
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

class IntuitionType(Enum):
    """Types of intuition."""
    PATTERN_BASED = "pattern_based"
    EXPERTISE_BASED = "expertise_based"
    EMOTIONAL = "emotional"
    PREMONITORY = "premonitory"


class ConfidenceLevel(Enum):
    """Levels of intuitive confidence."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    COMPELLING = "compelling"


class ChunkType(Enum):
    """Types of cognitive chunks."""
    PERCEPTUAL = "perceptual"
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    EPISODIC = "episodic"


class HeuristicType(Enum):
    """Types of heuristics."""
    AVAILABILITY = "availability"
    REPRESENTATIVENESS = "representativeness"
    ANCHORING = "anchoring"
    AFFECT = "affect"
    RECOGNITION = "recognition"


class DecisionMode(Enum):
    """Modes of decision making."""
    RECOGNITION_PRIMED = "recognition_primed"
    DELIBERATIVE = "deliberative"
    MIXED = "mixed"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Pattern:
    """A recognized pattern."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    features: Dict[str, Any] = field(default_factory=dict)
    frequency: int = 0
    last_seen: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Chunk:
    """A cognitive chunk."""
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    chunk_type: ChunkType = ChunkType.CONCEPTUAL
    elements: List[str] = field(default_factory=list)
    strength: float = 1.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intuition:
    """An intuitive judgment."""
    intuition_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conclusion: str = ""
    intuition_type: IntuitionType = IntuitionType.PATTERN_BASED
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    confidence_score: float = 0.5
    supporting_patterns: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Heuristic:
    """A heuristic rule."""
    heuristic_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    heuristic_type: HeuristicType = HeuristicType.AVAILABILITY
    condition: str = ""
    conclusion: str = ""
    reliability: float = 0.7


@dataclass
class Experience:
    """A stored experience."""
    exp_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    situation: Dict[str, Any] = field(default_factory=dict)
    action: str = ""
    outcome: str = ""
    success: bool = True
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class GutFeeling:
    """A gut feeling / somatic marker."""
    feeling_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stimulus: str = ""
    valence: float = 0.0  # -1 to 1
    intensity: float = 0.0  # 0 to 1
    body_response: str = ""


# =============================================================================
# PATTERN RECOGNIZER
# =============================================================================

class PatternRecognizer:
    """Recognize patterns implicitly."""

    def __init__(self):
        self._patterns: Dict[str, Pattern] = {}
        self._pattern_index: Dict[str, List[str]] = defaultdict(list)

    def learn(
        self,
        name: str,
        features: Dict[str, Any]
    ) -> Pattern:
        """Learn a pattern."""
        pattern = Pattern(name=name, features=features, frequency=1)
        self._patterns[pattern.pattern_id] = pattern

        # Index by features
        for key, val in features.items():
            self._pattern_index[f"{key}:{val}"].append(pattern.pattern_id)

        return pattern

    def reinforce(self, pattern_id: str) -> None:
        """Reinforce a pattern."""
        pattern = self._patterns.get(pattern_id)
        if pattern:
            pattern.frequency += 1
            pattern.last_seen = datetime.now().timestamp()

    def recognize(
        self,
        features: Dict[str, Any],
        threshold: float = 0.5
    ) -> List[Tuple[Pattern, float]]:
        """Recognize patterns from features."""
        candidates = defaultdict(float)

        for key, val in features.items():
            idx_key = f"{key}:{val}"
            for pattern_id in self._pattern_index.get(idx_key, []):
                pattern = self._patterns.get(pattern_id)
                if pattern:
                    candidates[pattern_id] += 1.0 / len(pattern.features)

        matches = []
        for pattern_id, score in candidates.items():
            if score >= threshold:
                pattern = self._patterns[pattern_id]
                # Weight by frequency
                adjusted_score = score * (1 + math.log1p(pattern.frequency) / 10)
                matches.append((pattern, min(adjusted_score, 1.0)))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def get_pattern(self, pattern_id: str) -> Optional[Pattern]:
        """Get a pattern."""
        return self._patterns.get(pattern_id)

    def all_patterns(self) -> List[Pattern]:
        """Get all patterns."""
        return list(self._patterns.values())


# =============================================================================
# CHUNK MANAGER
# =============================================================================

class ChunkManager:
    """Manage cognitive chunks."""

    def __init__(self):
        self._chunks: Dict[str, Chunk] = {}

    def create(
        self,
        name: str,
        elements: List[str],
        chunk_type: ChunkType = ChunkType.CONCEPTUAL,
        context: Optional[Dict[str, Any]] = None
    ) -> Chunk:
        """Create a chunk."""
        chunk = Chunk(
            name=name,
            elements=elements,
            chunk_type=chunk_type,
            context=context or {}
        )
        self._chunks[chunk.chunk_id] = chunk
        return chunk

    def strengthen(self, chunk_id: str, amount: float = 0.1) -> None:
        """Strengthen a chunk."""
        chunk = self._chunks.get(chunk_id)
        if chunk:
            chunk.strength = min(chunk.strength + amount, 10.0)

    def weaken(self, chunk_id: str, amount: float = 0.05) -> None:
        """Weaken a chunk."""
        chunk = self._chunks.get(chunk_id)
        if chunk:
            chunk.strength = max(chunk.strength - amount, 0.0)

    def recall(self, cue: str) -> List[Chunk]:
        """Recall chunks matching a cue."""
        matches = []
        for chunk in self._chunks.values():
            if cue in chunk.elements or cue in chunk.name:
                matches.append(chunk)

        return sorted(matches, key=lambda c: c.strength, reverse=True)

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get a chunk."""
        return self._chunks.get(chunk_id)

    def all_chunks(self) -> List[Chunk]:
        """Get all chunks."""
        return list(self._chunks.values())


# =============================================================================
# EXPERIENCE STORE
# =============================================================================

class ExperienceStore:
    """Store and retrieve experiences."""

    def __init__(self):
        self._experiences: Dict[str, Experience] = {}

    def store(
        self,
        situation: Dict[str, Any],
        action: str,
        outcome: str,
        success: bool = True
    ) -> Experience:
        """Store an experience."""
        exp = Experience(
            situation=situation,
            action=action,
            outcome=outcome,
            success=success
        )
        self._experiences[exp.exp_id] = exp
        return exp

    def retrieve_similar(
        self,
        situation: Dict[str, Any],
        n: int = 5
    ) -> List[Tuple[Experience, float]]:
        """Retrieve similar experiences."""
        matches = []

        for exp in self._experiences.values():
            # Calculate similarity
            common = set(situation.keys()) & set(exp.situation.keys())
            if not common:
                continue

            matching = sum(1 for k in common if situation[k] == exp.situation[k])
            sim = matching / max(len(situation), len(exp.situation))

            matches.append((exp, sim))

        return sorted(matches, key=lambda x: x[1], reverse=True)[:n]

    def get_experience(self, exp_id: str) -> Optional[Experience]:
        """Get an experience."""
        return self._experiences.get(exp_id)

    def all_experiences(self) -> List[Experience]:
        """Get all experiences."""
        return list(self._experiences.values())


# =============================================================================
# HEURISTIC ENGINE
# =============================================================================

class HeuristicEngine:
    """Apply heuristic reasoning."""

    def __init__(self):
        self._heuristics: Dict[str, Heuristic] = {}

    def add(
        self,
        name: str,
        condition: str,
        conclusion: str,
        heuristic_type: HeuristicType = HeuristicType.AVAILABILITY,
        reliability: float = 0.7
    ) -> Heuristic:
        """Add a heuristic."""
        heuristic = Heuristic(
            name=name,
            condition=condition,
            conclusion=conclusion,
            heuristic_type=heuristic_type,
            reliability=reliability
        )
        self._heuristics[heuristic.heuristic_id] = heuristic
        return heuristic

    def apply(
        self,
        situation: Dict[str, Any]
    ) -> List[Tuple[Heuristic, str]]:
        """Apply heuristics to a situation."""
        results = []

        for heuristic in self._heuristics.values():
            # Simple pattern match
            if any(heuristic.condition in str(v) for v in situation.values()):
                results.append((heuristic, heuristic.conclusion))

        return results

    def get_heuristic(self, heuristic_id: str) -> Optional[Heuristic]:
        """Get a heuristic."""
        return self._heuristics.get(heuristic_id)

    def all_heuristics(self) -> List[Heuristic]:
        """Get all heuristics."""
        return list(self._heuristics.values())


# =============================================================================
# GUT FEELING GENERATOR
# =============================================================================

class GutFeelingGenerator:
    """Generate gut feelings / somatic markers."""

    def __init__(self):
        self._feelings: Dict[str, GutFeeling] = {}
        self._associations: Dict[str, float] = {}  # stimulus -> valence

    def associate(
        self,
        stimulus: str,
        valence: float
    ) -> None:
        """Create a stimulus-valence association."""
        self._associations[stimulus] = valence

    def generate(
        self,
        stimulus: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GutFeeling:
        """Generate a gut feeling."""
        valence = self._associations.get(stimulus, 0.0)

        # Context can modify valence
        if context:
            for key, val in context.items():
                if key in self._associations:
                    valence += self._associations[key] * 0.2

        valence = max(-1.0, min(1.0, valence))
        intensity = abs(valence)

        # Body response
        if valence > 0.5:
            body_response = "warmth, relaxation"
        elif valence < -0.5:
            body_response = "tension, discomfort"
        else:
            body_response = "neutral"

        feeling = GutFeeling(
            stimulus=stimulus,
            valence=valence,
            intensity=intensity,
            body_response=body_response
        )
        self._feelings[feeling.feeling_id] = feeling
        return feeling

    def get_feeling(self, feeling_id: str) -> Optional[GutFeeling]:
        """Get a gut feeling."""
        return self._feelings.get(feeling_id)


# =============================================================================
# INTUITION ENGINE
# =============================================================================

class IntuitionEngine:
    """
    Intuition Engine for BAEL.

    Advanced intuitive reasoning and pattern recognition.
    """

    def __init__(self):
        self._pattern_rec = PatternRecognizer()
        self._chunk_mgr = ChunkManager()
        self._experience_store = ExperienceStore()
        self._heuristic_engine = HeuristicEngine()
        self._gut_feeling_gen = GutFeelingGenerator()
        self._intuitions: Dict[str, Intuition] = {}

    # -------------------------------------------------------------------------
    # PATTERNS
    # -------------------------------------------------------------------------

    def learn_pattern(
        self,
        name: str,
        features: Dict[str, Any]
    ) -> Pattern:
        """Learn a pattern."""
        return self._pattern_rec.learn(name, features)

    def recognize_patterns(
        self,
        features: Dict[str, Any],
        threshold: float = 0.5
    ) -> List[Tuple[Pattern, float]]:
        """Recognize patterns."""
        return self._pattern_rec.recognize(features, threshold)

    def reinforce_pattern(self, pattern_id: str) -> None:
        """Reinforce a pattern."""
        self._pattern_rec.reinforce(pattern_id)

    # -------------------------------------------------------------------------
    # CHUNKS
    # -------------------------------------------------------------------------

    def create_chunk(
        self,
        name: str,
        elements: List[str],
        chunk_type: ChunkType = ChunkType.CONCEPTUAL
    ) -> Chunk:
        """Create a chunk."""
        return self._chunk_mgr.create(name, elements, chunk_type)

    def recall_chunks(self, cue: str) -> List[Chunk]:
        """Recall chunks."""
        return self._chunk_mgr.recall(cue)

    def strengthen_chunk(self, chunk_id: str) -> None:
        """Strengthen a chunk."""
        self._chunk_mgr.strengthen(chunk_id)

    # -------------------------------------------------------------------------
    # EXPERIENCES
    # -------------------------------------------------------------------------

    def store_experience(
        self,
        situation: Dict[str, Any],
        action: str,
        outcome: str,
        success: bool = True
    ) -> Experience:
        """Store an experience."""
        return self._experience_store.store(situation, action, outcome, success)

    def retrieve_similar(
        self,
        situation: Dict[str, Any],
        n: int = 5
    ) -> List[Tuple[Experience, float]]:
        """Retrieve similar experiences."""
        return self._experience_store.retrieve_similar(situation, n)

    # -------------------------------------------------------------------------
    # HEURISTICS
    # -------------------------------------------------------------------------

    def add_heuristic(
        self,
        name: str,
        condition: str,
        conclusion: str,
        heuristic_type: HeuristicType = HeuristicType.AVAILABILITY
    ) -> Heuristic:
        """Add a heuristic."""
        return self._heuristic_engine.add(name, condition, conclusion, heuristic_type)

    def apply_heuristics(
        self,
        situation: Dict[str, Any]
    ) -> List[Tuple[Heuristic, str]]:
        """Apply heuristics."""
        return self._heuristic_engine.apply(situation)

    # -------------------------------------------------------------------------
    # GUT FEELINGS
    # -------------------------------------------------------------------------

    def associate_feeling(self, stimulus: str, valence: float) -> None:
        """Create feeling association."""
        self._gut_feeling_gen.associate(stimulus, valence)

    def generate_gut_feeling(
        self,
        stimulus: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GutFeeling:
        """Generate gut feeling."""
        return self._gut_feeling_gen.generate(stimulus, context)

    # -------------------------------------------------------------------------
    # INTUITION
    # -------------------------------------------------------------------------

    def intuit(
        self,
        situation: Dict[str, Any]
    ) -> Intuition:
        """Generate an intuition about a situation."""
        conclusions = []
        supporting_patterns = []
        confidence_scores = []

        # 1. Pattern recognition
        patterns = self.recognize_patterns(situation)
        for pattern, score in patterns[:3]:
            conclusions.append(f"Matches pattern: {pattern.name}")
            supporting_patterns.append(pattern.pattern_id)
            confidence_scores.append(score)

        # 2. Heuristic application
        heuristics = self.apply_heuristics(situation)
        for heuristic, conclusion in heuristics[:3]:
            conclusions.append(conclusion)
            confidence_scores.append(heuristic.reliability)

        # 3. Experience retrieval
        experiences = self.retrieve_similar(situation, n=3)
        for exp, sim in experiences:
            if exp.success:
                conclusions.append(f"Similar to successful: {exp.action}")
            else:
                conclusions.append(f"Avoid (similar to failure): {exp.action}")
            confidence_scores.append(sim)

        # Combine conclusions
        if conclusions:
            main_conclusion = conclusions[0]
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
        else:
            main_conclusion = "No clear intuition"
            avg_confidence = 0.0

        # Determine confidence level
        if avg_confidence > 0.8:
            conf_level = ConfidenceLevel.COMPELLING
        elif avg_confidence > 0.6:
            conf_level = ConfidenceLevel.STRONG
        elif avg_confidence > 0.4:
            conf_level = ConfidenceLevel.MODERATE
        else:
            conf_level = ConfidenceLevel.WEAK

        intuition = Intuition(
            conclusion=main_conclusion,
            intuition_type=IntuitionType.PATTERN_BASED,
            confidence=conf_level,
            confidence_score=avg_confidence,
            supporting_patterns=supporting_patterns
        )

        self._intuitions[intuition.intuition_id] = intuition
        return intuition

    def quick_decision(
        self,
        situation: Dict[str, Any],
        options: List[str]
    ) -> Tuple[str, float]:
        """Make a quick intuitive decision."""
        scores = {}

        for option in options:
            # Generate gut feeling for each option
            feeling = self.generate_gut_feeling(option, situation)

            # Check relevant experiences
            similar = self.retrieve_similar({**situation, "option": option}, n=2)
            exp_score = 0.0
            for exp, sim in similar:
                if exp.success:
                    exp_score += sim
                else:
                    exp_score -= sim

            scores[option] = feeling.valence * 0.5 + exp_score * 0.5

        best = max(options, key=lambda o: scores[o])
        return best, scores[best]

    def get_intuition(self, intuition_id: str) -> Optional[Intuition]:
        """Get an intuition."""
        return self._intuitions.get(intuition_id)

    def all_intuitions(self) -> List[Intuition]:
        """Get all intuitions."""
        return list(self._intuitions.values())


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Intuition Engine."""
    print("=" * 70)
    print("BAEL - INTUITION ENGINE DEMO")
    print("Advanced Intuitive Reasoning and Pattern Recognition")
    print("=" * 70)
    print()

    engine = IntuitionEngine()

    # 1. Learn Patterns
    print("1. LEARN PATTERNS:")
    print("-" * 40)

    p1 = engine.learn_pattern("good_weather", {
        "sky": "clear",
        "temperature": "warm",
        "wind": "light"
    })
    engine.reinforce_pattern(p1.pattern_id)
    engine.reinforce_pattern(p1.pattern_id)

    p2 = engine.learn_pattern("bad_weather", {
        "sky": "cloudy",
        "temperature": "cold",
        "wind": "strong"
    })

    print(f"   Learned: {p1.name} (freq: {p1.frequency})")
    print(f"   Learned: {p2.name} (freq: {p2.frequency})")
    print()

    # 2. Recognize Patterns
    print("2. RECOGNIZE PATTERNS:")
    print("-" * 40)

    situation = {"sky": "clear", "temperature": "warm", "humidity": "low"}
    matches = engine.recognize_patterns(situation)
    for pattern, score in matches:
        print(f"   {pattern.name}: {score:.2f}")
    print()

    # 3. Create Chunks
    print("3. CREATE CHUNKS:")
    print("-" * 40)

    chunk = engine.create_chunk(
        "morning_routine",
        ["wake_up", "shower", "breakfast", "commute"],
        ChunkType.PROCEDURAL
    )
    engine.strengthen_chunk(chunk.chunk_id)
    print(f"   Chunk: {chunk.name}")
    print(f"   Elements: {chunk.elements}")
    print(f"   Strength: {chunk.strength}")
    print()

    # 4. Store Experiences
    print("4. STORE EXPERIENCES:")
    print("-" * 40)

    engine.store_experience(
        situation={"location": "beach", "weather": "sunny"},
        action="go_swimming",
        outcome="had_fun",
        success=True
    )
    engine.store_experience(
        situation={"location": "beach", "weather": "rainy"},
        action="go_swimming",
        outcome="got_sick",
        success=False
    )
    engine.store_experience(
        situation={"location": "mountain", "weather": "clear"},
        action="go_hiking",
        outcome="beautiful_views",
        success=True
    )

    print("   Stored 3 experiences")
    print()

    # 5. Retrieve Similar Experiences
    print("5. RETRIEVE SIMILAR EXPERIENCES:")
    print("-" * 40)

    current = {"location": "beach", "weather": "sunny"}
    similar = engine.retrieve_similar(current, n=3)
    for exp, sim in similar:
        status = "✓" if exp.success else "✗"
        print(f"   {status} {exp.action} → {exp.outcome} (sim: {sim:.2f})")
    print()

    # 6. Add Heuristics
    print("6. ADD HEURISTICS:")
    print("-" * 40)

    engine.add_heuristic(
        "sunny_means_good",
        "sunny",
        "Good conditions expected",
        HeuristicType.AVAILABILITY
    )
    engine.add_heuristic(
        "crowd_means_popular",
        "crowded",
        "Popular destination",
        HeuristicType.REPRESENTATIVENESS
    )

    print("   Added availability and representativeness heuristics")
    print()

    # 7. Apply Heuristics
    print("7. APPLY HEURISTICS:")
    print("-" * 40)

    test_situation = {"weather": "sunny", "day": "weekend"}
    results = engine.apply_heuristics(test_situation)
    for heuristic, conclusion in results:
        print(f"   {heuristic.name}: {conclusion}")
    print()

    # 8. Gut Feelings
    print("8. GUT FEELINGS:")
    print("-" * 40)

    engine.associate_feeling("beach", 0.8)
    engine.associate_feeling("traffic", -0.6)
    engine.associate_feeling("relaxation", 0.9)

    feeling1 = engine.generate_gut_feeling("beach")
    feeling2 = engine.generate_gut_feeling("traffic")

    print(f"   Beach: valence={feeling1.valence:.2f}, {feeling1.body_response}")
    print(f"   Traffic: valence={feeling2.valence:.2f}, {feeling2.body_response}")
    print()

    # 9. Generate Intuition
    print("9. GENERATE INTUITION:")
    print("-" * 40)

    situation = {"location": "beach", "weather": "sunny", "time": "morning"}
    intuition = engine.intuit(situation)

    print(f"   Conclusion: {intuition.conclusion}")
    print(f"   Confidence: {intuition.confidence.value} ({intuition.confidence_score:.2f})")
    print(f"   Type: {intuition.intuition_type.value}")
    print()

    # 10. Quick Decision
    print("10. QUICK DECISION:")
    print("-" * 40)

    options = ["go_swimming", "stay_home", "go_hiking"]
    best, score = engine.quick_decision(
        {"weather": "sunny", "location": "beach"},
        options
    )

    print(f"   Options: {options}")
    print(f"   Best choice: {best} (score: {score:.2f})")
    print()

    # 11. Recall Chunks
    print("11. RECALL CHUNKS:")
    print("-" * 40)

    recalled = engine.recall_chunks("breakfast")
    for chunk in recalled:
        print(f"   {chunk.name}: {chunk.elements}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Intuition Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
