#!/usr/bin/env python3
"""
BAEL - Curiosity Engine
Advanced curiosity-driven exploration and learning.

Features:
- Curiosity modeling
- Information gap detection
- Exploration strategies
- Novelty detection
- Interest tracking
- Question generation
- Learning prioritization
- Discovery management
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

class CuriosityType(Enum):
    """Types of curiosity."""
    EPISTEMIC = "epistemic"  # Knowledge-seeking
    PERCEPTUAL = "perceptual"  # Novelty-seeking
    DIVERSIVE = "diversive"  # Variety-seeking
    SPECIFIC = "specific"  # Focused inquiry
    SOCIAL = "social"  # Interest in others
    EMPATHIC = "empathic"  # Understanding feelings


class ExplorationStrategy(Enum):
    """Exploration strategies."""
    RANDOM = "random"
    EPSILON_GREEDY = "epsilon_greedy"
    UCB = "ucb"  # Upper confidence bound
    THOMPSON = "thompson"  # Thompson sampling
    CURIOSITY_DRIVEN = "curiosity_driven"
    NOVELTY_SEARCH = "novelty_search"


class NoveltyLevel(Enum):
    """Novelty levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class InterestLevel(Enum):
    """Interest levels."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    PASSIONATE = "passionate"


class GapType(Enum):
    """Information gap types."""
    UNKNOWN = "unknown"
    INCOMPLETE = "incomplete"
    UNCERTAIN = "uncertain"
    OUTDATED = "outdated"
    CONTRADICTORY = "contradictory"


class QuestionType(Enum):
    """Question types."""
    WHAT = "what"
    HOW = "how"
    WHY = "why"
    WHEN = "when"
    WHERE = "where"
    WHO = "who"
    WHETHER = "whether"
    COMPARISON = "comparison"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CuriosityState:
    """Current curiosity state."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    overall_curiosity: float = 0.5
    type_levels: Dict[CuriosityType, float] = field(default_factory=dict)
    active_interests: List[str] = field(default_factory=list)
    satiation_level: float = 0.0
    exploration_budget: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InformationGap:
    """Detected information gap."""
    gap_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    gap_type: GapType = GapType.UNKNOWN
    severity: float = 0.5
    confidence: float = 0.5
    related_knowledge: List[str] = field(default_factory=list)
    potential_value: float = 0.5
    exploration_cost: float = 0.1
    discovered_at: datetime = field(default_factory=datetime.now)


@dataclass
class NoveltySignal:
    """Novelty detection signal."""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    novelty_level: NoveltyLevel = NoveltyLevel.MEDIUM
    novelty_score: float = 0.5
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Interest:
    """Interest topic."""
    interest_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    level: InterestLevel = InterestLevel.MODERATE
    score: float = 0.5
    engagement_count: int = 0
    last_engaged: Optional[datetime] = None
    decay_rate: float = 0.01
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Question:
    """Generated question."""
    question_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    question_type: QuestionType = QuestionType.WHAT
    topic: str = ""
    priority: float = 0.5
    expected_value: float = 0.5
    answered: bool = False
    answer: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Discovery:
    """Discovery record."""
    discovery_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    source: str = ""
    novelty_score: float = 0.5
    value_score: float = 0.5
    related_gaps: List[str] = field(default_factory=list)
    related_questions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExplorationAction:
    """Exploration action."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    target: str = ""
    expected_novelty: float = 0.5
    expected_value: float = 0.5
    cost: float = 0.1
    executed: bool = False
    result: Optional[Dict[str, Any]] = None


@dataclass
class CuriosityStats:
    """Curiosity engine statistics."""
    total_gaps_detected: int = 0
    total_questions_generated: int = 0
    total_discoveries: int = 0
    total_explorations: int = 0
    novelty_signals_processed: int = 0


# =============================================================================
# NOVELTY DETECTOR
# =============================================================================

class NoveltyDetector:
    """Detect novelty in observations."""

    def __init__(
        self,
        memory_size: int = 1000,
        similarity_threshold: float = 0.7
    ):
        self._memory: deque = deque(maxlen=memory_size)
        self._feature_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"mean": 0.0, "var": 1.0, "count": 0}
        )
        self._similarity_threshold = similarity_threshold

    def compute_novelty(
        self,
        observation: Dict[str, Any]
    ) -> NoveltySignal:
        """Compute novelty of observation."""
        features = self._extract_features(observation)

        # Compute novelty scores
        scores = []

        # Feature-based novelty
        for feature, value in features.items():
            if isinstance(value, (int, float)):
                stats = self._feature_stats[feature]
                if stats["count"] > 0:
                    z_score = abs((value - stats["mean"]) / (math.sqrt(stats["var"]) + 1e-10))
                    scores.append(min(1.0, z_score / 3))  # Normalize

        # Memory-based novelty
        memory_novelty = self._compute_memory_novelty(features)
        scores.append(memory_novelty)

        # Aggregate
        novelty_score = sum(scores) / len(scores) if scores else 0.5

        # Update statistics
        self._update_stats(features)
        self._memory.append(features)

        # Determine level
        level = self._score_to_level(novelty_score)

        return NoveltySignal(
            source=observation.get("source", "unknown"),
            novelty_level=level,
            novelty_score=novelty_score,
            features=features
        )

    def _extract_features(
        self,
        observation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract features from observation."""
        features = {}

        for key, value in observation.items():
            if isinstance(value, (int, float)):
                features[key] = float(value)
            elif isinstance(value, str):
                features[f"{key}_hash"] = hash(value) % 1000000
                features[f"{key}_len"] = len(value)
            elif isinstance(value, list):
                features[f"{key}_len"] = len(value)

        return features

    def _compute_memory_novelty(
        self,
        features: Dict[str, Any]
    ) -> float:
        """Compute novelty relative to memory."""
        if not self._memory:
            return 1.0

        min_distance = float('inf')

        for past in self._memory:
            distance = self._compute_distance(features, past)
            min_distance = min(min_distance, distance)

        # Normalize distance to novelty score
        novelty = min(1.0, min_distance / 10)
        return novelty

    def _compute_distance(
        self,
        f1: Dict[str, Any],
        f2: Dict[str, Any]
    ) -> float:
        """Compute distance between feature sets."""
        common_keys = set(f1.keys()) & set(f2.keys())
        if not common_keys:
            return 1.0

        total_diff = 0.0
        for key in common_keys:
            v1 = f1.get(key, 0)
            v2 = f2.get(key, 0)
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                total_diff += abs(v1 - v2)

        return total_diff / len(common_keys)

    def _update_stats(self, features: Dict[str, Any]) -> None:
        """Update running statistics."""
        for feature, value in features.items():
            if isinstance(value, (int, float)):
                stats = self._feature_stats[feature]
                n = stats["count"]
                old_mean = stats["mean"]

                # Welford's algorithm
                n += 1
                delta = value - old_mean
                new_mean = old_mean + delta / n
                delta2 = value - new_mean
                new_var = (stats["var"] * (n - 1) + delta * delta2) / n if n > 1 else 0

                self._feature_stats[feature] = {
                    "mean": new_mean,
                    "var": new_var,
                    "count": n
                }

    def _score_to_level(self, score: float) -> NoveltyLevel:
        """Convert score to level."""
        if score < 0.1:
            return NoveltyLevel.NONE
        elif score < 0.3:
            return NoveltyLevel.LOW
        elif score < 0.6:
            return NoveltyLevel.MEDIUM
        elif score < 0.85:
            return NoveltyLevel.HIGH
        else:
            return NoveltyLevel.EXTREME


# =============================================================================
# INFORMATION GAP DETECTOR
# =============================================================================

class GapDetector:
    """Detect information gaps."""

    def __init__(self):
        self._known_topics: Set[str] = set()
        self._topic_coverage: Dict[str, float] = {}
        self._topic_confidence: Dict[str, float] = {}
        self._topic_age: Dict[str, datetime] = {}

    def register_knowledge(
        self,
        topic: str,
        coverage: float = 1.0,
        confidence: float = 1.0
    ) -> None:
        """Register known knowledge."""
        self._known_topics.add(topic)
        self._topic_coverage[topic] = coverage
        self._topic_confidence[topic] = confidence
        self._topic_age[topic] = datetime.now()

    def detect_gaps(
        self,
        context: Dict[str, Any],
        referenced_topics: List[str]
    ) -> List[InformationGap]:
        """Detect information gaps in context."""
        gaps = []

        for topic in referenced_topics:
            # Unknown topic
            if topic not in self._known_topics:
                gaps.append(InformationGap(
                    topic=topic,
                    gap_type=GapType.UNKNOWN,
                    severity=0.9,
                    confidence=0.8,
                    potential_value=0.7
                ))
            else:
                # Check coverage
                coverage = self._topic_coverage.get(topic, 0.0)
                if coverage < 0.5:
                    gaps.append(InformationGap(
                        topic=topic,
                        gap_type=GapType.INCOMPLETE,
                        severity=1.0 - coverage,
                        confidence=0.7,
                        potential_value=0.5
                    ))

                # Check confidence
                confidence = self._topic_confidence.get(topic, 0.0)
                if confidence < 0.5:
                    gaps.append(InformationGap(
                        topic=topic,
                        gap_type=GapType.UNCERTAIN,
                        severity=1.0 - confidence,
                        confidence=0.6,
                        potential_value=0.6
                    ))

                # Check age
                age = self._topic_age.get(topic)
                if age:
                    days_old = (datetime.now() - age).days
                    if days_old > 30:
                        staleness = min(1.0, days_old / 365)
                        gaps.append(InformationGap(
                            topic=topic,
                            gap_type=GapType.OUTDATED,
                            severity=staleness,
                            confidence=0.5,
                            potential_value=0.4
                        ))

        # Sort by priority
        gaps.sort(key=lambda g: g.severity * g.potential_value, reverse=True)

        return gaps

    def fill_gap(
        self,
        gap_id: str,
        topic: str,
        new_coverage: float = 1.0,
        new_confidence: float = 1.0
    ) -> None:
        """Mark gap as filled."""
        self.register_knowledge(topic, new_coverage, new_confidence)


# =============================================================================
# INTEREST TRACKER
# =============================================================================

class InterestTracker:
    """Track interests and engagement."""

    def __init__(self, max_interests: int = 100):
        self._interests: Dict[str, Interest] = {}
        self._max_interests = max_interests
        self._engagement_history: deque = deque(maxlen=1000)

    def register_interest(
        self,
        topic: str,
        initial_level: InterestLevel = InterestLevel.MODERATE
    ) -> Interest:
        """Register new interest."""
        if topic in self._interests:
            return self._interests[topic]

        level_to_score = {
            InterestLevel.NONE: 0.0,
            InterestLevel.LOW: 0.25,
            InterestLevel.MODERATE: 0.5,
            InterestLevel.HIGH: 0.75,
            InterestLevel.PASSIONATE: 1.0,
        }

        interest = Interest(
            topic=topic,
            level=initial_level,
            score=level_to_score[initial_level]
        )

        self._interests[topic] = interest
        self._prune_interests()

        return interest

    def engage(self, topic: str, intensity: float = 0.1) -> None:
        """Record engagement with topic."""
        if topic not in self._interests:
            self.register_interest(topic)

        interest = self._interests[topic]
        interest.engagement_count += 1
        interest.last_engaged = datetime.now()
        interest.score = min(1.0, interest.score + intensity)
        interest.level = self._score_to_level(interest.score)

        self._engagement_history.append({
            "topic": topic,
            "intensity": intensity,
            "timestamp": datetime.now()
        })

    def decay_interests(self, rate: Optional[float] = None) -> None:
        """Decay all interests over time."""
        now = datetime.now()

        for interest in self._interests.values():
            decay = rate if rate is not None else interest.decay_rate

            if interest.last_engaged:
                hours_since = (now - interest.last_engaged).total_seconds() / 3600
                decay_amount = decay * hours_since
                interest.score = max(0.0, interest.score - decay_amount)
                interest.level = self._score_to_level(interest.score)

    def get_top_interests(self, n: int = 10) -> List[Interest]:
        """Get top interests by score."""
        sorted_interests = sorted(
            self._interests.values(),
            key=lambda i: i.score,
            reverse=True
        )
        return sorted_interests[:n]

    def get_interest(self, topic: str) -> Optional[Interest]:
        """Get interest by topic."""
        return self._interests.get(topic)

    def _score_to_level(self, score: float) -> InterestLevel:
        """Convert score to level."""
        if score < 0.1:
            return InterestLevel.NONE
        elif score < 0.35:
            return InterestLevel.LOW
        elif score < 0.65:
            return InterestLevel.MODERATE
        elif score < 0.9:
            return InterestLevel.HIGH
        else:
            return InterestLevel.PASSIONATE

    def _prune_interests(self) -> None:
        """Prune low-value interests."""
        if len(self._interests) <= self._max_interests:
            return

        # Sort by score
        sorted_topics = sorted(
            self._interests.keys(),
            key=lambda t: self._interests[t].score
        )

        # Remove lowest
        to_remove = len(self._interests) - self._max_interests
        for topic in sorted_topics[:to_remove]:
            del self._interests[topic]


# =============================================================================
# QUESTION GENERATOR
# =============================================================================

class QuestionGenerator:
    """Generate questions from gaps and interests."""

    def __init__(self):
        self._templates = {
            QuestionType.WHAT: [
                "What is {topic}?",
                "What are the key aspects of {topic}?",
                "What does {topic} involve?",
            ],
            QuestionType.HOW: [
                "How does {topic} work?",
                "How can {topic} be applied?",
                "How is {topic} implemented?",
            ],
            QuestionType.WHY: [
                "Why is {topic} important?",
                "Why does {topic} happen?",
                "Why should we care about {topic}?",
            ],
            QuestionType.WHEN: [
                "When is {topic} relevant?",
                "When should {topic} be used?",
                "When did {topic} emerge?",
            ],
            QuestionType.WHERE: [
                "Where is {topic} applied?",
                "Where can {topic} be found?",
                "Where does {topic} occur?",
            ],
            QuestionType.WHO: [
                "Who uses {topic}?",
                "Who benefits from {topic}?",
                "Who developed {topic}?",
            ],
            QuestionType.WHETHER: [
                "Is {topic} effective?",
                "Should {topic} be adopted?",
                "Does {topic} work?",
            ],
            QuestionType.COMPARISON: [
                "How does {topic} compare to alternatives?",
                "What are the pros and cons of {topic}?",
                "What makes {topic} different?",
            ],
        }

    def generate_from_gap(self, gap: InformationGap) -> List[Question]:
        """Generate questions from information gap."""
        questions = []

        # Determine appropriate question types based on gap type
        type_mapping = {
            GapType.UNKNOWN: [QuestionType.WHAT, QuestionType.HOW],
            GapType.INCOMPLETE: [QuestionType.WHAT, QuestionType.HOW, QuestionType.WHY],
            GapType.UNCERTAIN: [QuestionType.WHETHER, QuestionType.HOW],
            GapType.OUTDATED: [QuestionType.WHAT, QuestionType.WHEN],
            GapType.CONTRADICTORY: [QuestionType.WHY, QuestionType.WHETHER],
        }

        question_types = type_mapping.get(gap.gap_type, [QuestionType.WHAT])

        for qtype in question_types:
            templates = self._templates.get(qtype, [])
            if templates:
                template = random.choice(templates)
                text = template.format(topic=gap.topic)

                questions.append(Question(
                    text=text,
                    question_type=qtype,
                    topic=gap.topic,
                    priority=gap.severity,
                    expected_value=gap.potential_value
                ))

        return questions

    def generate_from_interest(
        self,
        interest: Interest,
        depth: str = "basic"
    ) -> List[Question]:
        """Generate questions from interest."""
        questions = []

        # Determine question types based on depth
        if depth == "basic":
            qtypes = [QuestionType.WHAT, QuestionType.WHY]
        elif depth == "intermediate":
            qtypes = [QuestionType.HOW, QuestionType.WHEN, QuestionType.WHERE]
        else:  # advanced
            qtypes = [QuestionType.COMPARISON, QuestionType.WHETHER]

        for qtype in qtypes:
            templates = self._templates.get(qtype, [])
            if templates:
                template = random.choice(templates)
                text = template.format(topic=interest.topic)

                questions.append(Question(
                    text=text,
                    question_type=qtype,
                    topic=interest.topic,
                    priority=interest.score,
                    expected_value=0.5
                ))

        return questions


# =============================================================================
# EXPLORATION STRATEGY
# =============================================================================

class Explorer(ABC):
    """Abstract explorer."""

    @abstractmethod
    def select_action(
        self,
        actions: List[ExplorationAction]
    ) -> ExplorationAction:
        """Select exploration action."""
        pass


class RandomExplorer(Explorer):
    """Random exploration."""

    def select_action(
        self,
        actions: List[ExplorationAction]
    ) -> ExplorationAction:
        return random.choice(actions) if actions else None


class EpsilonGreedyExplorer(Explorer):
    """Epsilon-greedy exploration."""

    def __init__(self, epsilon: float = 0.1):
        self._epsilon = epsilon

    def select_action(
        self,
        actions: List[ExplorationAction]
    ) -> ExplorationAction:
        if not actions:
            return None

        if random.random() < self._epsilon:
            return random.choice(actions)
        else:
            return max(actions, key=lambda a: a.expected_value)


class UCBExplorer(Explorer):
    """Upper Confidence Bound exploration."""

    def __init__(self, c: float = 1.414):
        self._c = c
        self._action_counts: Dict[str, int] = defaultdict(int)
        self._total_counts = 0

    def select_action(
        self,
        actions: List[ExplorationAction]
    ) -> ExplorationAction:
        if not actions:
            return None

        self._total_counts += 1

        best_action = None
        best_ucb = float('-inf')

        for action in actions:
            count = self._action_counts[action.action_type]

            if count == 0:
                ucb = float('inf')
            else:
                exploitation = action.expected_value
                exploration = self._c * math.sqrt(
                    math.log(self._total_counts) / count
                )
                ucb = exploitation + exploration

            if ucb > best_ucb:
                best_ucb = ucb
                best_action = action

        if best_action:
            self._action_counts[best_action.action_type] += 1

        return best_action


class CuriosityDrivenExplorer(Explorer):
    """Curiosity-driven exploration."""

    def __init__(
        self,
        novelty_weight: float = 0.5,
        value_weight: float = 0.3,
        cost_weight: float = 0.2
    ):
        self._novelty_weight = novelty_weight
        self._value_weight = value_weight
        self._cost_weight = cost_weight

    def select_action(
        self,
        actions: List[ExplorationAction]
    ) -> ExplorationAction:
        if not actions:
            return None

        def compute_score(action: ExplorationAction) -> float:
            novelty = action.expected_novelty * self._novelty_weight
            value = action.expected_value * self._value_weight
            cost_penalty = (1 - action.cost) * self._cost_weight
            return novelty + value + cost_penalty

        return max(actions, key=compute_score)


# =============================================================================
# CURIOSITY ENGINE
# =============================================================================

class CuriosityEngine:
    """
    Curiosity Engine for BAEL.

    Advanced curiosity-driven exploration and learning.
    """

    def __init__(
        self,
        strategy: ExplorationStrategy = ExplorationStrategy.CURIOSITY_DRIVEN
    ):
        self._novelty_detector = NoveltyDetector()
        self._gap_detector = GapDetector()
        self._interest_tracker = InterestTracker()
        self._question_generator = QuestionGenerator()
        self._explorer = self._create_explorer(strategy)

        self._current_state = CuriosityState()
        self._discoveries: List[Discovery] = []
        self._pending_questions: List[Question] = []
        self._stats = CuriosityStats()

    def _create_explorer(
        self,
        strategy: ExplorationStrategy
    ) -> Explorer:
        """Create explorer for strategy."""
        if strategy == ExplorationStrategy.RANDOM:
            return RandomExplorer()
        elif strategy == ExplorationStrategy.EPSILON_GREEDY:
            return EpsilonGreedyExplorer()
        elif strategy == ExplorationStrategy.UCB:
            return UCBExplorer()
        else:
            return CuriosityDrivenExplorer()

    # -------------------------------------------------------------------------
    # STATE MANAGEMENT
    # -------------------------------------------------------------------------

    def get_state(self) -> CuriosityState:
        """Get current curiosity state."""
        return self._current_state

    def set_curiosity(
        self,
        curiosity_type: CuriosityType,
        level: float
    ) -> None:
        """Set curiosity level for type."""
        self._current_state.type_levels[curiosity_type] = max(0.0, min(1.0, level))
        self._update_overall_curiosity()

    def get_curiosity(
        self,
        curiosity_type: Optional[CuriosityType] = None
    ) -> float:
        """Get curiosity level."""
        if curiosity_type:
            return self._current_state.type_levels.get(curiosity_type, 0.5)
        return self._current_state.overall_curiosity

    def _update_overall_curiosity(self) -> None:
        """Update overall curiosity from type levels."""
        levels = self._current_state.type_levels
        if levels:
            self._current_state.overall_curiosity = sum(levels.values()) / len(levels)
        else:
            self._current_state.overall_curiosity = 0.5

    def satiate(self, amount: float = 0.1) -> None:
        """Reduce curiosity through satiation."""
        self._current_state.satiation_level += amount
        self._current_state.satiation_level = min(1.0, self._current_state.satiation_level)

        # Reduce curiosity based on satiation
        reduction = amount * 0.5
        for ctype in self._current_state.type_levels:
            self._current_state.type_levels[ctype] = max(
                0.0,
                self._current_state.type_levels[ctype] - reduction
            )

        self._update_overall_curiosity()

    def reset_satiation(self) -> None:
        """Reset satiation level."""
        self._current_state.satiation_level = 0.0

    # -------------------------------------------------------------------------
    # NOVELTY DETECTION
    # -------------------------------------------------------------------------

    def detect_novelty(
        self,
        observation: Dict[str, Any]
    ) -> NoveltySignal:
        """Detect novelty in observation."""
        signal = self._novelty_detector.compute_novelty(observation)
        self._stats.novelty_signals_processed += 1

        # Update curiosity based on novelty
        if signal.novelty_score > 0.5:
            boost = (signal.novelty_score - 0.5) * 0.2
            self.set_curiosity(
                CuriosityType.PERCEPTUAL,
                self.get_curiosity(CuriosityType.PERCEPTUAL) + boost
            )

        return signal

    # -------------------------------------------------------------------------
    # GAP DETECTION
    # -------------------------------------------------------------------------

    def register_knowledge(
        self,
        topic: str,
        coverage: float = 1.0,
        confidence: float = 1.0
    ) -> None:
        """Register known knowledge."""
        self._gap_detector.register_knowledge(topic, coverage, confidence)

    def detect_gaps(
        self,
        context: Dict[str, Any],
        topics: List[str]
    ) -> List[InformationGap]:
        """Detect information gaps."""
        gaps = self._gap_detector.detect_gaps(context, topics)
        self._stats.total_gaps_detected += len(gaps)

        # Update curiosity based on gaps
        if gaps:
            avg_severity = sum(g.severity for g in gaps) / len(gaps)
            self.set_curiosity(
                CuriosityType.EPISTEMIC,
                self.get_curiosity(CuriosityType.EPISTEMIC) + avg_severity * 0.1
            )

        return gaps

    def fill_gap(
        self,
        topic: str,
        coverage: float = 1.0,
        confidence: float = 1.0
    ) -> None:
        """Fill information gap."""
        self._gap_detector.fill_gap("", topic, coverage, confidence)
        self.satiate(0.05)

    # -------------------------------------------------------------------------
    # INTEREST TRACKING
    # -------------------------------------------------------------------------

    def register_interest(
        self,
        topic: str,
        level: InterestLevel = InterestLevel.MODERATE
    ) -> Interest:
        """Register interest."""
        interest = self._interest_tracker.register_interest(topic, level)
        self._current_state.active_interests.append(topic)
        return interest

    def engage_interest(
        self,
        topic: str,
        intensity: float = 0.1
    ) -> None:
        """Engage with interest."""
        self._interest_tracker.engage(topic, intensity)

    def get_top_interests(self, n: int = 10) -> List[Interest]:
        """Get top interests."""
        return self._interest_tracker.get_top_interests(n)

    def decay_interests(self, rate: float = 0.01) -> None:
        """Decay interests."""
        self._interest_tracker.decay_interests(rate)

    # -------------------------------------------------------------------------
    # QUESTION GENERATION
    # -------------------------------------------------------------------------

    def generate_questions(
        self,
        gaps: Optional[List[InformationGap]] = None,
        interests: Optional[List[Interest]] = None,
        max_questions: int = 10
    ) -> List[Question]:
        """Generate questions from gaps and interests."""
        questions = []

        if gaps:
            for gap in gaps[:5]:
                questions.extend(self._question_generator.generate_from_gap(gap))

        if interests:
            for interest in interests[:5]:
                questions.extend(
                    self._question_generator.generate_from_interest(interest)
                )

        # Sort by priority
        questions.sort(key=lambda q: q.priority, reverse=True)
        questions = questions[:max_questions]

        self._pending_questions.extend(questions)
        self._stats.total_questions_generated += len(questions)

        return questions

    def answer_question(
        self,
        question_id: str,
        answer: str
    ) -> bool:
        """Mark question as answered."""
        for q in self._pending_questions:
            if q.question_id == question_id:
                q.answered = True
                q.answer = answer
                self.satiate(0.05)
                return True
        return False

    def get_pending_questions(self) -> List[Question]:
        """Get unanswered questions."""
        return [q for q in self._pending_questions if not q.answered]

    # -------------------------------------------------------------------------
    # EXPLORATION
    # -------------------------------------------------------------------------

    def create_exploration_actions(
        self,
        context: Dict[str, Any]
    ) -> List[ExplorationAction]:
        """Create exploration actions."""
        actions = []

        # Create actions from gaps
        gaps = self.detect_gaps(context, list(context.keys()))
        for gap in gaps[:5]:
            actions.append(ExplorationAction(
                action_type="investigate_gap",
                target=gap.topic,
                expected_novelty=gap.severity,
                expected_value=gap.potential_value,
                cost=gap.exploration_cost
            ))

        # Create actions from interests
        interests = self.get_top_interests(5)
        for interest in interests:
            actions.append(ExplorationAction(
                action_type="explore_interest",
                target=interest.topic,
                expected_novelty=0.3,
                expected_value=interest.score,
                cost=0.1
            ))

        # Create random exploration action
        actions.append(ExplorationAction(
            action_type="random_explore",
            target="unknown",
            expected_novelty=0.7,
            expected_value=0.3,
            cost=0.2
        ))

        return actions

    def select_exploration(
        self,
        actions: List[ExplorationAction]
    ) -> Optional[ExplorationAction]:
        """Select exploration action."""
        return self._explorer.select_action(actions)

    def execute_exploration(
        self,
        action: ExplorationAction,
        result: Dict[str, Any]
    ) -> Discovery:
        """Execute exploration and record discovery."""
        action.executed = True
        action.result = result

        # Compute novelty of result
        novelty = self.detect_novelty(result)

        # Create discovery
        discovery = Discovery(
            content=str(result.get("content", "")),
            source=action.target,
            novelty_score=novelty.novelty_score,
            value_score=action.expected_value
        )

        self._discoveries.append(discovery)
        self._stats.total_discoveries += 1
        self._stats.total_explorations += 1

        # Reduce exploration budget
        self._current_state.exploration_budget -= action.cost
        self._current_state.exploration_budget = max(0, self._current_state.exploration_budget)

        return discovery

    def reset_exploration_budget(self, budget: float = 1.0) -> None:
        """Reset exploration budget."""
        self._current_state.exploration_budget = budget

    # -------------------------------------------------------------------------
    # LEARNING PRIORITIZATION
    # -------------------------------------------------------------------------

    def prioritize_learning(
        self,
        topics: List[str]
    ) -> List[Tuple[str, float]]:
        """Prioritize topics for learning."""
        priorities = []

        for topic in topics:
            priority = 0.5

            # Boost from gaps
            gaps = self.detect_gaps({}, [topic])
            if gaps:
                priority += gaps[0].severity * 0.3

            # Boost from interests
            interest = self._interest_tracker.get_interest(topic)
            if interest:
                priority += interest.score * 0.3

            # Boost from curiosity state
            priority += self._current_state.overall_curiosity * 0.2

            priorities.append((topic, min(1.0, priority)))

        priorities.sort(key=lambda x: x[1], reverse=True)
        return priorities

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> CuriosityStats:
        """Get engine statistics."""
        return self._stats

    def get_discoveries(
        self,
        min_novelty: float = 0.0
    ) -> List[Discovery]:
        """Get discoveries above novelty threshold."""
        return [d for d in self._discoveries if d.novelty_score >= min_novelty]


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Curiosity Engine."""
    print("=" * 70)
    print("BAEL - CURIOSITY ENGINE DEMO")
    print("Curiosity-Driven Exploration and Learning")
    print("=" * 70)
    print()

    engine = CuriosityEngine()

    # 1. Set Curiosity Levels
    print("1. SET CURIOSITY LEVELS:")
    print("-" * 40)

    engine.set_curiosity(CuriosityType.EPISTEMIC, 0.8)
    engine.set_curiosity(CuriosityType.PERCEPTUAL, 0.6)
    engine.set_curiosity(CuriosityType.SOCIAL, 0.4)

    state = engine.get_state()
    for ctype, level in state.type_levels.items():
        print(f"   {ctype.value}: {level:.2f}")
    print(f"   Overall: {state.overall_curiosity:.2f}")
    print()

    # 2. Register Knowledge
    print("2. REGISTER KNOWLEDGE:")
    print("-" * 40)

    topics = ["machine_learning", "neural_networks", "reinforcement_learning"]
    for topic in topics:
        engine.register_knowledge(topic, coverage=0.7, confidence=0.8)
        print(f"   Registered: {topic}")
    print()

    # 3. Detect Novelty
    print("3. DETECT NOVELTY:")
    print("-" * 40)

    observations = [
        {"source": "paper1", "topic": "transformers", "year": 2023, "citations": 500},
        {"source": "paper2", "topic": "transformers", "year": 2023, "citations": 520},
        {"source": "paper3", "topic": "quantum_ml", "year": 2024, "citations": 10},
    ]

    for obs in observations:
        novelty = engine.detect_novelty(obs)
        print(f"   {obs['source']}: {novelty.novelty_level.value} ({novelty.novelty_score:.3f})")
    print()

    # 4. Detect Information Gaps
    print("4. DETECT INFORMATION GAPS:")
    print("-" * 40)

    context = {"domain": "AI research"}
    referenced = ["machine_learning", "quantum_computing", "neuromorphic_chips"]

    gaps = engine.detect_gaps(context, referenced)
    for gap in gaps:
        print(f"   {gap.topic}: {gap.gap_type.value} (severity: {gap.severity:.2f})")
    print()

    # 5. Register Interests
    print("5. REGISTER INTERESTS:")
    print("-" * 40)

    interests = [
        ("deep_learning", InterestLevel.HIGH),
        ("robotics", InterestLevel.MODERATE),
        ("nlp", InterestLevel.PASSIONATE),
    ]

    for topic, level in interests:
        engine.register_interest(topic, level)
        print(f"   Registered: {topic} ({level.value})")
    print()

    # 6. Engage With Interest
    print("6. ENGAGE WITH INTEREST:")
    print("-" * 40)

    engine.engage_interest("deep_learning", 0.2)
    engine.engage_interest("deep_learning", 0.1)

    top = engine.get_top_interests(3)
    for interest in top:
        print(f"   {interest.topic}: {interest.score:.2f} ({interest.engagement_count} engagements)")
    print()

    # 7. Generate Questions
    print("7. GENERATE QUESTIONS:")
    print("-" * 40)

    questions = engine.generate_questions(gaps=gaps, interests=top, max_questions=5)
    for q in questions:
        print(f"   [{q.question_type.value}] {q.text}")
    print()

    # 8. Answer Question
    print("8. ANSWER QUESTION:")
    print("-" * 40)

    if questions:
        q = questions[0]
        engine.answer_question(q.question_id, "This is the answer...")
        print(f"   Answered: {q.text[:50]}...")
        print(f"   Pending questions: {len(engine.get_pending_questions())}")
    print()

    # 9. Create Exploration Actions
    print("9. CREATE EXPLORATION ACTIONS:")
    print("-" * 40)

    actions = engine.create_exploration_actions(context)
    for action in actions[:5]:
        print(f"   {action.action_type}: {action.target} (novelty: {action.expected_novelty:.2f})")
    print()

    # 10. Select Exploration
    print("10. SELECT EXPLORATION:")
    print("-" * 40)

    selected = engine.select_exploration(actions)
    if selected:
        print(f"   Selected: {selected.action_type} -> {selected.target}")

        # Execute exploration
        result = {"content": "New discovery about " + selected.target}
        discovery = engine.execute_exploration(selected, result)
        print(f"   Discovery novelty: {discovery.novelty_score:.3f}")
    print()

    # 11. Prioritize Learning
    print("11. PRIORITIZE LEARNING:")
    print("-" * 40)

    learning_topics = ["quantum_ml", "deep_learning", "ethics_in_ai", "robotics"]
    priorities = engine.prioritize_learning(learning_topics)
    for topic, priority in priorities:
        print(f"   {topic}: {priority:.3f}")
    print()

    # 12. Satiation
    print("12. SATIATION:")
    print("-" * 40)

    print(f"   Before: Overall curiosity = {engine.get_curiosity():.3f}")
    engine.satiate(0.3)
    print(f"   After satiate(0.3): Overall curiosity = {engine.get_curiosity():.3f}")
    engine.reset_satiation()
    print(f"   After reset: Satiation level = {engine.get_state().satiation_level:.3f}")
    print()

    # 13. Interest Decay
    print("13. INTEREST DECAY:")
    print("-" * 40)

    print("   Before decay:")
    for interest in engine.get_top_interests(3):
        print(f"     {interest.topic}: {interest.score:.3f}")

    engine.decay_interests(rate=0.1)

    print("   After decay:")
    for interest in engine.get_top_interests(3):
        print(f"     {interest.topic}: {interest.score:.3f}")
    print()

    # 14. Get Discoveries
    print("14. GET DISCOVERIES:")
    print("-" * 40)

    discoveries = engine.get_discoveries(min_novelty=0.0)
    print(f"   Total discoveries: {len(discoveries)}")
    for d in discoveries:
        print(f"     - {d.source}: {d.novelty_score:.3f}")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = engine.get_stats()
    print(f"   Gaps detected: {stats.total_gaps_detected}")
    print(f"   Questions generated: {stats.total_questions_generated}")
    print(f"   Discoveries: {stats.total_discoveries}")
    print(f"   Explorations: {stats.total_explorations}")
    print(f"   Novelty signals: {stats.novelty_signals_processed}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Curiosity Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
