"""
🧬 LEARNING INTEGRATION 🧬
==========================
Unified learning system.

Features:
- Learning coordination
- Knowledge consolidation
- Transfer learning
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
import uuid
import math


class LearningType(Enum):
    """Types of learning"""
    SUPERVISED = auto()
    UNSUPERVISED = auto()
    REINFORCEMENT = auto()
    IMITATION = auto()
    TRANSFER = auto()
    META = auto()
    CONTINUAL = auto()


@dataclass
class LearningEvent:
    """A learning event"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # What was learned
    content: Any = None
    learning_type: LearningType = LearningType.SUPERVISED

    # Context
    domain: str = ""
    task: str = ""

    # Quality
    confidence: float = 0.0
    utility: float = 0.0

    # Timing
    learned_at: datetime = field(default_factory=datetime.now)

    # Retention
    rehearsal_count: int = 0
    last_rehearsal: Optional[datetime] = None


@dataclass
class Knowledge:
    """A piece of knowledge"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content
    content: Any = None
    content_type: str = ""

    # Metadata
    domain: str = ""
    source: str = ""

    # Quality
    confidence: float = 1.0
    validity: float = 1.0

    # Usage tracking
    use_count: int = 0
    success_count: int = 0

    # Relations
    related_knowledge: List[str] = field(default_factory=list)

    def get_success_rate(self) -> float:
        """Get success rate when applied"""
        if self.use_count == 0:
            return 0.5
        return self.success_count / self.use_count


class LearningCoordinator:
    """
    Coordinates learning across systems.
    """

    def __init__(self):
        # Learning events
        self.events: List[LearningEvent] = []

        # Learning rate
        self.learning_rate: float = 0.1

        # Knowledge base
        self.knowledge: Dict[str, Knowledge] = {}

        # Learning strategies
        self.strategies: Dict[LearningType, Callable] = {}

        # Curriculum
        self.curriculum: List[str] = []  # Ordered learning tasks

    def add_strategy(
        self,
        learning_type: LearningType,
        strategy: Callable[[Any, Any], Knowledge]
    ):
        """Add learning strategy"""
        self.strategies[learning_type] = strategy

    def learn(
        self,
        content: Any,
        target: Any = None,
        learning_type: LearningType = LearningType.SUPERVISED
    ) -> Optional[Knowledge]:
        """Learn from experience"""
        strategy = self.strategies.get(learning_type)

        if not strategy:
            # Default learning
            knowledge = Knowledge(
                content=content,
                content_type=type(content).__name__
            )
        else:
            knowledge = strategy(content, target)

        # Record event
        event = LearningEvent(
            content=knowledge,
            learning_type=learning_type,
            confidence=knowledge.confidence
        )
        self.events.append(event)

        # Store knowledge
        self.knowledge[knowledge.id] = knowledge

        return knowledge

    def reinforce(self, knowledge_id: str, reward: float):
        """Reinforce knowledge"""
        if knowledge_id not in self.knowledge:
            return

        knowledge = self.knowledge[knowledge_id]

        # Update confidence based on reward
        delta = self.learning_rate * (reward - knowledge.confidence)
        knowledge.confidence += delta
        knowledge.confidence = min(1.0, max(0.0, knowledge.confidence))

        # Track usage
        knowledge.use_count += 1
        if reward > 0.5:
            knowledge.success_count += 1

    def forget(self, threshold: float = 0.1) -> int:
        """Forget low-confidence knowledge"""
        to_forget = [
            kid for kid, k in self.knowledge.items()
            if k.confidence < threshold
        ]

        for kid in to_forget:
            del self.knowledge[kid]

        return len(to_forget)

    def get_relevant(
        self,
        domain: str = None,
        task: str = None,
        n: int = 10
    ) -> List[Knowledge]:
        """Get relevant knowledge"""
        results = []

        for knowledge in self.knowledge.values():
            if domain and knowledge.domain != domain:
                continue

            results.append(knowledge)

        # Sort by confidence and success rate
        results.sort(
            key=lambda k: k.confidence * k.get_success_rate(),
            reverse=True
        )

        return results[:n]

    def set_curriculum(self, tasks: List[str]):
        """Set learning curriculum"""
        self.curriculum = tasks

    def get_next_task(self) -> Optional[str]:
        """Get next task in curriculum"""
        if self.curriculum:
            return self.curriculum[0]
        return None

    def complete_task(self, task: str):
        """Mark task as completed"""
        if task in self.curriculum:
            self.curriculum.remove(task)


class KnowledgeConsolidator:
    """
    Consolidates and organizes knowledge.
    """

    def __init__(self):
        # Knowledge clusters
        self.clusters: Dict[str, List[str]] = {}

        # Abstractions
        self.abstractions: Dict[str, Knowledge] = {}

        # Conflict resolution
        self.conflicts: List[Tuple[str, str]] = []

    def cluster_knowledge(
        self,
        knowledge_list: List[Knowledge]
    ) -> Dict[str, List[Knowledge]]:
        """Cluster related knowledge"""
        clusters = {}

        for k in knowledge_list:
            domain = k.domain or "general"
            if domain not in clusters:
                clusters[domain] = []
            clusters[domain].append(k)

        self.clusters = {
            domain: [k.id for k in knowledge]
            for domain, knowledge in clusters.items()
        }

        return clusters

    def abstract(
        self,
        knowledge_list: List[Knowledge]
    ) -> Knowledge:
        """Create abstraction from knowledge"""
        # Find commonalities
        common = {}

        if knowledge_list:
            first = knowledge_list[0]
            if isinstance(first.content, dict):
                # Find common keys
                common_keys = set(first.content.keys())
                for k in knowledge_list[1:]:
                    if isinstance(k.content, dict):
                        common_keys &= set(k.content.keys())

                common = {key: [] for key in common_keys}

        abstraction = Knowledge(
            content=common,
            content_type="abstraction",
            domain="meta",
            confidence=sum(k.confidence for k in knowledge_list) / len(knowledge_list) if knowledge_list else 0,
            related_knowledge=[k.id for k in knowledge_list]
        )

        self.abstractions[abstraction.id] = abstraction
        return abstraction

    def detect_conflicts(
        self,
        knowledge_list: List[Knowledge]
    ) -> List[Tuple[Knowledge, Knowledge]]:
        """Detect conflicting knowledge"""
        conflicts = []

        for i, k1 in enumerate(knowledge_list):
            for k2 in knowledge_list[i + 1:]:
                if self._is_conflicting(k1, k2):
                    conflicts.append((k1, k2))
                    self.conflicts.append((k1.id, k2.id))

        return conflicts

    def _is_conflicting(self, k1: Knowledge, k2: Knowledge) -> bool:
        """Check if knowledge conflicts"""
        # Same domain, different content
        if k1.domain == k2.domain and k1.content != k2.content:
            return True
        return False

    def resolve_conflict(
        self,
        k1: Knowledge,
        k2: Knowledge
    ) -> Knowledge:
        """Resolve conflict between knowledge"""
        # Prefer higher confidence
        if k1.confidence > k2.confidence:
            winner = k1
        elif k2.confidence > k1.confidence:
            winner = k2
        else:
            # Prefer higher success rate
            if k1.get_success_rate() >= k2.get_success_rate():
                winner = k1
            else:
                winner = k2

        return winner

    def consolidate(
        self,
        knowledge_list: List[Knowledge]
    ) -> Dict[str, Any]:
        """Full consolidation process"""
        # Cluster
        clusters = self.cluster_knowledge(knowledge_list)

        # Abstract per cluster
        abstractions = {}
        for domain, items in clusters.items():
            if len(items) > 1:
                abstractions[domain] = self.abstract(items)

        # Detect conflicts
        conflicts = self.detect_conflicts(knowledge_list)

        # Resolve conflicts
        resolutions = []
        for k1, k2 in conflicts:
            winner = self.resolve_conflict(k1, k2)
            resolutions.append(winner.id)

        return {
            'clusters': len(clusters),
            'abstractions': len(abstractions),
            'conflicts': len(conflicts),
            'resolutions': resolutions
        }


class TransferLearner:
    """
    Transfer learning across domains.
    """

    def __init__(self):
        # Domain mappings
        self.domain_mappings: Dict[Tuple[str, str], Dict[str, str]] = {}

        # Transfer history
        self.transfers: List[Dict[str, Any]] = []

        # Domain similarity
        self.domain_similarity: Dict[Tuple[str, str], float] = {}

    def add_mapping(
        self,
        source_domain: str,
        target_domain: str,
        mapping: Dict[str, str]
    ):
        """Add domain mapping"""
        self.domain_mappings[(source_domain, target_domain)] = mapping

    def set_similarity(
        self,
        domain1: str,
        domain2: str,
        similarity: float
    ):
        """Set domain similarity"""
        key = tuple(sorted([domain1, domain2]))
        self.domain_similarity[key] = similarity

    def get_similarity(self, domain1: str, domain2: str) -> float:
        """Get domain similarity"""
        if domain1 == domain2:
            return 1.0
        key = tuple(sorted([domain1, domain2]))
        return self.domain_similarity.get(key, 0.0)

    def can_transfer(
        self,
        source_domain: str,
        target_domain: str,
        threshold: float = 0.3
    ) -> bool:
        """Check if transfer is feasible"""
        similarity = self.get_similarity(source_domain, target_domain)
        return similarity >= threshold

    def transfer(
        self,
        knowledge: Knowledge,
        target_domain: str
    ) -> Knowledge:
        """Transfer knowledge to new domain"""
        source_domain = knowledge.domain

        # Get mapping if exists
        mapping = self.domain_mappings.get((source_domain, target_domain), {})

        # Create transferred knowledge
        transferred_content = knowledge.content
        if isinstance(transferred_content, dict) and mapping:
            transferred_content = {
                mapping.get(k, k): v
                for k, v in transferred_content.items()
            }

        # Compute transfer confidence
        similarity = self.get_similarity(source_domain, target_domain)
        transfer_confidence = knowledge.confidence * similarity

        transferred = Knowledge(
            content=transferred_content,
            content_type=knowledge.content_type,
            domain=target_domain,
            source=f"transfer:{knowledge.id}",
            confidence=transfer_confidence,
            related_knowledge=[knowledge.id]
        )

        # Record transfer
        self.transfers.append({
            'source_knowledge': knowledge.id,
            'target_knowledge': transferred.id,
            'source_domain': source_domain,
            'target_domain': target_domain,
            'confidence': transfer_confidence,
            'timestamp': datetime.now()
        })

        return transferred

    def adapt(
        self,
        knowledge: Knowledge,
        target_examples: List[Any]
    ) -> Knowledge:
        """Adapt knowledge with target examples"""
        # Fine-tune based on examples
        adapted = Knowledge(
            content=knowledge.content,
            content_type=knowledge.content_type,
            domain=knowledge.domain,
            source=f"adapted:{knowledge.id}",
            confidence=knowledge.confidence,
            related_knowledge=[knowledge.id]
        )

        # Adjust confidence based on examples
        if target_examples:
            adapted.confidence *= 0.9  # Slight reduction for uncertainty

        return adapted

    def get_transfer_history(
        self,
        source_domain: str = None,
        target_domain: str = None
    ) -> List[Dict[str, Any]]:
        """Get transfer history"""
        results = self.transfers

        if source_domain:
            results = [t for t in results if t['source_domain'] == source_domain]
        if target_domain:
            results = [t for t in results if t['target_domain'] == target_domain]

        return results


# Export all
__all__ = [
    'LearningType',
    'LearningEvent',
    'Knowledge',
    'LearningCoordinator',
    'KnowledgeConsolidator',
    'TransferLearner',
]
