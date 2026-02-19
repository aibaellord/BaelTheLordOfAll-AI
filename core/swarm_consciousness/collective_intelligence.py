"""
⚡ COLLECTIVE INTELLIGENCE ⚡
============================
Emergent wisdom from agent collectives.

Implements:
- Collective Memory (distributed knowledge)
- Consensus Building
- Distributed Reasoning
- Emergent Knowledge Discovery
- Wisdom of the Swarm
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid
import hashlib


@dataclass
class KnowledgeItem:
    """A piece of collective knowledge"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None
    source_agent: str = ""
    confidence: float = 1.0
    votes: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CollectiveMemory:
    """
    Distributed memory shared across swarm.

    Features:
    - Voting-based validation
    - Confidence aggregation
    - Temporal decay
    - Semantic clustering
    """

    def __init__(
        self,
        decay_rate: float = 0.01,
        consensus_threshold: int = 3
    ):
        self.decay_rate = decay_rate
        self.consensus_threshold = consensus_threshold

        # Knowledge storage
        self.knowledge: Dict[str, KnowledgeItem] = {}

        # Index by content hash for deduplication
        self.content_index: Dict[str, str] = {}  # hash -> id

        # Tag index
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)

        # Agent contributions
        self.agent_contributions: Dict[str, int] = defaultdict(int)

    def _hash_content(self, content: Any) -> str:
        """Hash content for deduplication"""
        return hashlib.md5(str(content).encode()).hexdigest()

    def store(
        self,
        content: Any,
        agent_id: str,
        confidence: float = 1.0,
        tags: Set[str] = None
    ) -> str:
        """Store knowledge item"""
        content_hash = self._hash_content(content)

        if content_hash in self.content_index:
            # Update existing knowledge
            existing_id = self.content_index[content_hash]
            item = self.knowledge[existing_id]
            item.votes += 1
            item.confidence = (
                item.confidence * (item.votes - 1) + confidence
            ) / item.votes
            return existing_id

        # Create new knowledge
        item = KnowledgeItem(
            content=content,
            source_agent=agent_id,
            confidence=confidence,
            tags=tags or set()
        )

        self.knowledge[item.id] = item
        self.content_index[content_hash] = item.id

        for tag in item.tags:
            self.tag_index[tag].add(item.id)

        self.agent_contributions[agent_id] += 1
        return item.id

    def retrieve(
        self,
        item_id: str
    ) -> Optional[KnowledgeItem]:
        """Retrieve knowledge by ID"""
        return self.knowledge.get(item_id)

    def query_by_tags(
        self,
        tags: Set[str],
        require_all: bool = False
    ) -> List[KnowledgeItem]:
        """Query knowledge by tags"""
        if not tags:
            return []

        if require_all:
            result_ids = None
            for tag in tags:
                tag_ids = self.tag_index.get(tag, set())
                if result_ids is None:
                    result_ids = tag_ids.copy()
                else:
                    result_ids &= tag_ids
        else:
            result_ids = set()
            for tag in tags:
                result_ids |= self.tag_index.get(tag, set())

        return [self.knowledge[id] for id in result_ids if id in self.knowledge]

    def get_consensus_knowledge(self) -> List[KnowledgeItem]:
        """Get knowledge with sufficient votes"""
        return [
            item for item in self.knowledge.values()
            if item.votes >= self.consensus_threshold
        ]

    def vote(
        self,
        item_id: str,
        agent_id: str,
        agreement: bool
    ):
        """Vote on knowledge item"""
        if item_id not in self.knowledge:
            return

        item = self.knowledge[item_id]
        if agreement:
            item.votes += 1
            item.confidence = min(1.0, item.confidence * 1.1)
        else:
            item.votes -= 1
            item.confidence *= 0.9

        # Remove if votes too low
        if item.votes <= 0:
            self._remove(item_id)

    def _remove(self, item_id: str):
        """Remove knowledge item"""
        if item_id not in self.knowledge:
            return

        item = self.knowledge[item_id]
        content_hash = self._hash_content(item.content)

        del self.content_index[content_hash]
        for tag in item.tags:
            self.tag_index[tag].discard(item_id)
        del self.knowledge[item_id]

    def decay(self):
        """Apply temporal decay"""
        to_remove = []
        for item_id, item in self.knowledge.items():
            item.confidence *= (1 - self.decay_rate)
            if item.confidence < 0.1:
                to_remove.append(item_id)

        for item_id in to_remove:
            self._remove(item_id)


class ConsensusMethod(Enum):
    """Methods for reaching consensus"""
    MAJORITY_VOTE = auto()
    WEIGHTED_VOTE = auto()
    MEDIAN = auto()
    BAYESIAN = auto()


@dataclass
class Vote:
    """A vote from an agent"""
    agent_id: str
    value: Any
    confidence: float = 1.0
    weight: float = 1.0


class ConsensusEngine:
    """
    Reaches consensus among multiple agents.
    """

    def __init__(
        self,
        method: ConsensusMethod = ConsensusMethod.WEIGHTED_VOTE
    ):
        self.method = method
        self.votes: Dict[str, List[Vote]] = defaultdict(list)
        self.consensus_history: List[Dict[str, Any]] = []

    def submit_vote(
        self,
        topic: str,
        agent_id: str,
        value: Any,
        confidence: float = 1.0,
        weight: float = 1.0
    ):
        """Submit vote on topic"""
        vote = Vote(
            agent_id=agent_id,
            value=value,
            confidence=confidence,
            weight=weight
        )
        self.votes[topic].append(vote)

    def reach_consensus(
        self,
        topic: str
    ) -> Tuple[Any, float]:
        """Reach consensus on topic"""
        votes = self.votes.get(topic, [])
        if not votes:
            return None, 0.0

        if self.method == ConsensusMethod.MAJORITY_VOTE:
            result, confidence = self._majority_vote(votes)
        elif self.method == ConsensusMethod.WEIGHTED_VOTE:
            result, confidence = self._weighted_vote(votes)
        elif self.method == ConsensusMethod.MEDIAN:
            result, confidence = self._median_vote(votes)
        elif self.method == ConsensusMethod.BAYESIAN:
            result, confidence = self._bayesian_vote(votes)
        else:
            result, confidence = self._majority_vote(votes)

        # Record
        self.consensus_history.append({
            'topic': topic,
            'result': result,
            'confidence': confidence,
            'n_votes': len(votes),
            'timestamp': datetime.now()
        })

        return result, confidence

    def _majority_vote(
        self,
        votes: List[Vote]
    ) -> Tuple[Any, float]:
        """Simple majority vote"""
        counts = defaultdict(int)
        for vote in votes:
            counts[str(vote.value)] += 1

        if not counts:
            return None, 0.0

        best_value = max(counts.keys(), key=lambda k: counts[k])
        confidence = counts[best_value] / len(votes)

        # Recover original value type
        for vote in votes:
            if str(vote.value) == best_value:
                return vote.value, confidence

        return best_value, confidence

    def _weighted_vote(
        self,
        votes: List[Vote]
    ) -> Tuple[Any, float]:
        """Weighted vote by confidence"""
        weighted_counts = defaultdict(float)
        total_weight = 0

        for vote in votes:
            weight = vote.confidence * vote.weight
            weighted_counts[str(vote.value)] += weight
            total_weight += weight

        if total_weight == 0:
            return None, 0.0

        best_value = max(weighted_counts.keys(), key=lambda k: weighted_counts[k])
        confidence = weighted_counts[best_value] / total_weight

        for vote in votes:
            if str(vote.value) == best_value:
                return vote.value, confidence

        return best_value, confidence

    def _median_vote(
        self,
        votes: List[Vote]
    ) -> Tuple[Any, float]:
        """Median for numerical votes"""
        try:
            values = [float(vote.value) for vote in votes]
            median = float(np.median(values))

            # Confidence based on spread
            std = np.std(values) if len(values) > 1 else 0
            confidence = 1.0 / (1.0 + std)

            return median, confidence
        except (ValueError, TypeError):
            return self._majority_vote(votes)

    def _bayesian_vote(
        self,
        votes: List[Vote]
    ) -> Tuple[Any, float]:
        """Bayesian aggregation"""
        # Treat confidence as likelihood
        log_odds = defaultdict(float)

        for vote in votes:
            key = str(vote.value)
            # Log odds update
            if vote.confidence > 0 and vote.confidence < 1:
                odds = vote.confidence / (1 - vote.confidence)
                log_odds[key] += math.log(odds + 1e-10)

        if not log_odds:
            return None, 0.0

        best_value = max(log_odds.keys(), key=lambda k: log_odds[k])

        # Convert back to probability
        max_log_odds = log_odds[best_value]
        confidence = 1 / (1 + math.exp(-max_log_odds))

        for vote in votes:
            if str(vote.value) == best_value:
                return vote.value, confidence

        return best_value, confidence

    def clear_topic(self, topic: str):
        """Clear votes for topic"""
        if topic in self.votes:
            del self.votes[topic]


@dataclass
class ReasoningFragment:
    """Fragment of distributed reasoning"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    premise: str = ""
    conclusion: str = ""
    confidence: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    supports: List[str] = field(default_factory=list)
    contradicts: List[str] = field(default_factory=list)


class DistributedReasoning:
    """
    Distributed reasoning across agents.

    Combines partial reasoning from multiple agents
    into complete inference chains.
    """

    def __init__(self):
        self.fragments: Dict[str, ReasoningFragment] = {}
        self.by_premise: Dict[str, List[str]] = defaultdict(list)
        self.by_conclusion: Dict[str, List[str]] = defaultdict(list)

    def submit_fragment(
        self,
        agent_id: str,
        premise: str,
        conclusion: str,
        confidence: float = 1.0
    ) -> str:
        """Submit reasoning fragment"""
        fragment = ReasoningFragment(
            agent_id=agent_id,
            premise=premise,
            conclusion=conclusion,
            confidence=confidence
        )

        self.fragments[fragment.id] = fragment
        self.by_premise[premise].append(fragment.id)
        self.by_conclusion[conclusion].append(fragment.id)

        # Find relationships
        self._find_relationships(fragment)

        return fragment.id

    def _find_relationships(self, fragment: ReasoningFragment):
        """Find supporting and contradicting fragments"""
        # Fragments with same premise
        same_premise = [
            self.fragments[fid]
            for fid in self.by_premise.get(fragment.premise, [])
            if fid != fragment.id
        ]

        for other in same_premise:
            if other.conclusion == fragment.conclusion:
                fragment.supports.append(other.id)
                other.supports.append(fragment.id)
            # Could add contradiction detection here

        # Fragments whose conclusion is our premise (dependencies)
        predecessors = self.by_conclusion.get(fragment.premise, [])
        fragment.dependencies.extend(predecessors)

    def get_chain(
        self,
        start_premise: str,
        target_conclusion: str,
        max_depth: int = 10
    ) -> List[ReasoningFragment]:
        """Find reasoning chain from premise to conclusion"""
        visited = set()

        def dfs(premise: str, depth: int) -> Optional[List[ReasoningFragment]]:
            if depth > max_depth:
                return None

            if premise in visited:
                return None
            visited.add(premise)

            # Check fragments with this premise
            for fid in self.by_premise.get(premise, []):
                fragment = self.fragments[fid]

                if fragment.conclusion == target_conclusion:
                    return [fragment]

                # Continue search
                rest = dfs(fragment.conclusion, depth + 1)
                if rest is not None:
                    return [fragment] + rest

            return None

        return dfs(start_premise, 0) or []

    def calculate_chain_confidence(
        self,
        chain: List[ReasoningFragment]
    ) -> float:
        """Calculate combined confidence of reasoning chain"""
        if not chain:
            return 0.0

        # Product of confidences (conservative)
        confidence = 1.0
        for fragment in chain:
            confidence *= fragment.confidence

        return confidence

    def get_supported_conclusions(
        self,
        min_support: int = 2
    ) -> List[Tuple[str, float]]:
        """Get conclusions with multiple supporting fragments"""
        conclusion_support = defaultdict(list)

        for fragment in self.fragments.values():
            conclusion_support[fragment.conclusion].append(fragment)

        supported = []
        for conclusion, fragments in conclusion_support.items():
            if len(fragments) >= min_support:
                # Average confidence
                avg_conf = sum(f.confidence for f in fragments) / len(fragments)
                supported.append((conclusion, avg_conf))

        return sorted(supported, key=lambda x: -x[1])


@dataclass
class EmergentPattern:
    """Pattern that emerged from collective behavior"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = ""
    description: str = ""
    strength: float = 0.0
    participating_agents: List[str] = field(default_factory=list)
    evidence: List[Any] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class EmergentKnowledge:
    """
    Detects knowledge that emerges from collective behavior.

    Finds patterns that no individual agent would discover.
    """

    def __init__(self, collective_memory: CollectiveMemory):
        self.memory = collective_memory
        self.patterns: List[EmergentPattern] = []
        self.pattern_threshold = 0.5

    def analyze_convergence(self) -> List[EmergentPattern]:
        """Detect convergent knowledge patterns"""
        patterns = []

        # Group knowledge by tags
        tag_groups = defaultdict(list)
        for item in self.memory.knowledge.values():
            for tag in item.tags:
                tag_groups[tag].append(item)

        # Find converging groups
        for tag, items in tag_groups.items():
            if len(items) < 3:
                continue

            # Check if agents are converging
            agents = set(item.source_agent for item in items)

            if len(agents) >= 2:
                avg_confidence = sum(i.confidence for i in items) / len(items)

                if avg_confidence > self.pattern_threshold:
                    pattern = EmergentPattern(
                        pattern_type="convergence",
                        description=f"Multiple agents converging on '{tag}'",
                        strength=avg_confidence,
                        participating_agents=list(agents),
                        evidence=[i.content for i in items]
                    )
                    patterns.append(pattern)

        self.patterns.extend(patterns)
        return patterns

    def analyze_consensus(self) -> List[EmergentPattern]:
        """Detect consensus patterns"""
        patterns = []

        # Find high-vote items
        consensus_items = self.memory.get_consensus_knowledge()

        for item in consensus_items:
            pattern = EmergentPattern(
                pattern_type="consensus",
                description=f"Collective agreement: {str(item.content)[:50]}",
                strength=item.confidence,
                participating_agents=[item.source_agent],
                evidence=[item]
            )
            patterns.append(pattern)

        self.patterns.extend(patterns)
        return patterns

    def analyze_novelty(
        self,
        reference_knowledge: Set[str]
    ) -> List[EmergentPattern]:
        """Detect novel knowledge not in reference set"""
        patterns = []

        for item in self.memory.knowledge.values():
            content_str = str(item.content)

            # Check if novel
            is_novel = not any(
                ref.lower() in content_str.lower()
                for ref in reference_knowledge
            )

            if is_novel and item.votes >= 2:
                pattern = EmergentPattern(
                    pattern_type="novelty",
                    description=f"Novel knowledge: {content_str[:50]}",
                    strength=item.confidence,
                    participating_agents=[item.source_agent],
                    evidence=[item]
                )
                patterns.append(pattern)

        self.patterns.extend(patterns)
        return patterns


class SwarmWisdom:
    """
    High-level swarm wisdom aggregation.

    Combines all collective intelligence mechanisms.
    """

    def __init__(self):
        self.memory = CollectiveMemory()
        self.consensus = ConsensusEngine(ConsensusMethod.BAYESIAN)
        self.reasoning = DistributedReasoning()
        self.emergence = EmergentKnowledge(self.memory)

        # Wisdom metrics
        self.total_knowledge = 0
        self.consensus_count = 0
        self.emergence_count = 0

    def contribute_knowledge(
        self,
        agent_id: str,
        content: Any,
        confidence: float = 1.0,
        tags: Set[str] = None
    ) -> str:
        """Agent contributes knowledge"""
        item_id = self.memory.store(content, agent_id, confidence, tags)
        self.total_knowledge = len(self.memory.knowledge)
        return item_id

    def propose_decision(
        self,
        topic: str,
        agent_id: str,
        proposal: Any,
        confidence: float = 1.0
    ):
        """Agent proposes decision"""
        self.consensus.submit_vote(topic, agent_id, proposal, confidence)

    def decide(self, topic: str) -> Tuple[Any, float]:
        """Reach collective decision"""
        result, confidence = self.consensus.reach_consensus(topic)
        self.consensus_count = len(self.consensus.consensus_history)
        return result, confidence

    def reason(
        self,
        agent_id: str,
        premise: str,
        conclusion: str,
        confidence: float = 1.0
    ) -> str:
        """Agent contributes reasoning"""
        return self.reasoning.submit_fragment(
            agent_id, premise, conclusion, confidence
        )

    def find_reasoning_path(
        self,
        premise: str,
        conclusion: str
    ) -> Tuple[List[ReasoningFragment], float]:
        """Find collective reasoning path"""
        chain = self.reasoning.get_chain(premise, conclusion)
        confidence = self.reasoning.calculate_chain_confidence(chain)
        return chain, confidence

    def discover_emergence(self) -> List[EmergentPattern]:
        """Discover emergent patterns"""
        patterns = []
        patterns.extend(self.emergence.analyze_convergence())
        patterns.extend(self.emergence.analyze_consensus())
        self.emergence_count = len(self.emergence.patterns)
        return patterns

    def get_wisdom_summary(self) -> Dict[str, Any]:
        """Get summary of collective wisdom"""
        return {
            'total_knowledge': self.total_knowledge,
            'consensus_decisions': self.consensus_count,
            'emergent_patterns': self.emergence_count,
            'reasoning_fragments': len(self.reasoning.fragments),
            'high_confidence_knowledge': len(
                self.memory.get_consensus_knowledge()
            ),
            'supported_conclusions': len(
                self.reasoning.get_supported_conclusions()
            )
        }


# Export all
__all__ = [
    'KnowledgeItem',
    'CollectiveMemory',
    'ConsensusMethod',
    'Vote',
    'ConsensusEngine',
    'ReasoningFragment',
    'DistributedReasoning',
    'EmergentPattern',
    'EmergentKnowledge',
    'SwarmWisdom',
]
