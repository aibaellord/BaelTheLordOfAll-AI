"""
🔄 LEARNING SYSTEM 🔄
=====================
Continuous learning.

Features:
- Experience collection
- Knowledge updates
- Transfer learning
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import uuid
import math


class LearningStrategy(Enum):
    """Learning strategies"""
    SUPERVISED = auto()
    REINFORCEMENT = auto()
    SELF_SUPERVISED = auto()
    TRANSFER = auto()
    META_LEARNING = auto()
    CONTINUAL = auto()
    CURRICULUM = auto()


@dataclass
class Experience:
    """A learning experience"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    # Action taken
    action: str = ""
    action_params: Dict[str, Any] = field(default_factory=dict)

    # Outcome
    outcome: Any = None
    outcome_quality: float = 0.0  # -1.0 to 1.0

    # Feedback
    feedback: Optional[str] = None
    reward: float = 0.0

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0

    # Learning value
    novelty: float = 0.0
    importance: float = 0.0

    def compute_learning_value(self) -> float:
        """Compute overall learning value"""
        # Combine novelty, importance, and absolute reward
        return (self.novelty * 0.3 +
                self.importance * 0.3 +
                abs(self.reward) * 0.4)


@dataclass
class KnowledgeUpdate:
    """A knowledge update"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # What was learned
    topic: str = ""
    knowledge_type: str = ""  # fact, skill, pattern, rule

    # Content
    content: Any = None

    # Confidence
    confidence: float = 1.0

    # Source experiences
    source_experiences: List[str] = field(default_factory=list)

    # Supersedes previous knowledge
    supersedes: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def decay_confidence(self, factor: float = 0.99):
        """Apply confidence decay"""
        self.confidence *= factor


class ExperienceBuffer:
    """
    Buffer for collecting experiences.
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.experiences: List[Experience] = []

        # Indexing
        self.by_action: Dict[str, List[Experience]] = {}
        self.by_context_key: Dict[str, List[Experience]] = {}

    def add(self, experience: Experience):
        """Add experience"""
        if len(self.experiences) >= self.max_size:
            self._evict()

        self.experiences.append(experience)

        # Index
        if experience.action not in self.by_action:
            self.by_action[experience.action] = []
        self.by_action[experience.action].append(experience)

    def _evict(self):
        """Evict low-value experiences"""
        # Remove lowest learning value
        if self.experiences:
            self.experiences.sort(key=lambda e: e.compute_learning_value())
            removed = self.experiences.pop(0)

            # Update indices
            if removed.action in self.by_action:
                self.by_action[removed.action] = [
                    e for e in self.by_action[removed.action]
                    if e.id != removed.id
                ]

    def sample(self, n: int, prioritized: bool = True) -> List[Experience]:
        """Sample experiences"""
        if not self.experiences:
            return []

        if not prioritized:
            import random
            return random.sample(
                self.experiences,
                min(n, len(self.experiences))
            )

        # Priority sampling based on learning value
        sorted_exp = sorted(
            self.experiences,
            key=lambda e: e.compute_learning_value(),
            reverse=True
        )
        return sorted_exp[:n]

    def get_similar(
        self,
        experience: Experience,
        n: int = 5
    ) -> List[Experience]:
        """Get similar experiences"""
        # Simple similarity: same action
        similar = self.by_action.get(experience.action, [])
        return similar[:n]


class ContinuousLearner:
    """
    Continuous learning system.
    """

    def __init__(self):
        self.experience_buffer = ExperienceBuffer()
        self.knowledge: Dict[str, KnowledgeUpdate] = {}

        # Learning rate
        self.learning_rate: float = 0.01

        # Strategy
        self.strategy: LearningStrategy = LearningStrategy.CONTINUAL

        # Callbacks
        self.on_learn: List[Callable[[KnowledgeUpdate], None]] = []

    def record_experience(self, experience: Experience):
        """Record an experience"""
        # Compute novelty
        similar = self.experience_buffer.get_similar(experience)
        if similar:
            experience.novelty = 1.0 - len(similar) / 100
        else:
            experience.novelty = 1.0

        self.experience_buffer.add(experience)

        # Trigger learning if high value
        if experience.compute_learning_value() > 0.5:
            self._learn_from_experience(experience)

    def _learn_from_experience(self, experience: Experience):
        """Learn from a single experience"""
        # Create knowledge update
        update = KnowledgeUpdate(
            topic=experience.action,
            knowledge_type="pattern",
            content={
                'context': experience.context,
                'params': experience.action_params,
                'outcome_quality': experience.outcome_quality,
                'reward': experience.reward
            },
            source_experiences=[experience.id]
        )

        self.integrate_knowledge(update)

    def integrate_knowledge(self, update: KnowledgeUpdate):
        """Integrate knowledge update"""
        # Check for existing knowledge on topic
        existing = None
        for kid, k in self.knowledge.items():
            if k.topic == update.topic:
                existing = k
                break

        if existing:
            # Merge with existing
            existing.confidence = (
                existing.confidence * (1 - self.learning_rate) +
                update.confidence * self.learning_rate
            )
            existing.source_experiences.extend(update.source_experiences)
            existing.access_count += 1
        else:
            # Add new knowledge
            self.knowledge[update.id] = update

        # Callbacks
        for callback in self.on_learn:
            callback(update)

    def retrieve_knowledge(
        self,
        topic: str,
        threshold: float = 0.5
    ) -> List[KnowledgeUpdate]:
        """Retrieve knowledge on topic"""
        results = []

        for update in self.knowledge.values():
            if topic.lower() in update.topic.lower():
                if update.confidence >= threshold:
                    update.access_count += 1
                    results.append(update)

        return sorted(results, key=lambda k: k.confidence, reverse=True)

    def consolidate(self):
        """Consolidate learning (periodic maintenance)"""
        # Decay confidence on unused knowledge
        for update in self.knowledge.values():
            if update.access_count == 0:
                update.decay_confidence()

        # Remove very low confidence knowledge
        self.knowledge = {
            k: v for k, v in self.knowledge.items()
            if v.confidence > 0.1
        }

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics"""
        return {
            'total_experiences': len(self.experience_buffer.experiences),
            'knowledge_items': len(self.knowledge),
            'avg_knowledge_confidence': (
                sum(k.confidence for k in self.knowledge.values()) / len(self.knowledge)
                if self.knowledge else 0
            ),
            'learning_rate': self.learning_rate,
            'strategy': self.strategy.name
        }


class TransferLearning:
    """
    Transfer learning capabilities.
    """

    def __init__(self):
        self.domain_mappings: Dict[str, Dict[str, float]] = {}
        self.transferred_knowledge: List[KnowledgeUpdate] = []

    def learn_domain_mapping(
        self,
        source_domain: str,
        target_domain: str,
        similarity: float
    ):
        """Learn domain mapping"""
        if source_domain not in self.domain_mappings:
            self.domain_mappings[source_domain] = {}
        self.domain_mappings[source_domain][target_domain] = similarity

    def transfer(
        self,
        knowledge: KnowledgeUpdate,
        target_domain: str
    ) -> Optional[KnowledgeUpdate]:
        """Transfer knowledge to new domain"""
        # Find mapping
        source_domain = knowledge.topic.split('.')[0] if '.' in knowledge.topic else knowledge.topic

        mapping = self.domain_mappings.get(source_domain, {})
        similarity = mapping.get(target_domain, 0.0)

        if similarity < 0.3:
            return None  # Too different

        # Create transferred knowledge
        transferred = KnowledgeUpdate(
            topic=f"{target_domain}.{knowledge.topic.split('.')[-1]}",
            knowledge_type=knowledge.knowledge_type,
            content=knowledge.content,
            confidence=knowledge.confidence * similarity,
            source_experiences=knowledge.source_experiences.copy()
        )

        self.transferred_knowledge.append(transferred)
        return transferred

    def find_transferable(
        self,
        knowledge_base: Dict[str, KnowledgeUpdate],
        target_domain: str
    ) -> List[KnowledgeUpdate]:
        """Find knowledge transferable to domain"""
        transferable = []

        for knowledge in knowledge_base.values():
            transferred = self.transfer(knowledge, target_domain)
            if transferred:
                transferable.append(transferred)

        return transferable


# Export all
__all__ = [
    'LearningStrategy',
    'Experience',
    'KnowledgeUpdate',
    'ExperienceBuffer',
    'ContinuousLearner',
    'TransferLearning',
]
