"""
🌐 COLLECTIVE INTELLIGENCE 🌐
=============================
Emergent group intelligence.

Features:
- Swarm decisions
- Emergent patterns
- Hive mind
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from datetime import datetime
import uuid
import math
import random


@dataclass
class CollectiveThought:
    """A thought from the collective"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Content
    content: Any = None
    thought_type: str = ""  # insight, decision, prediction, solution

    # Contributing nodes
    contributors: List[str] = field(default_factory=list)
    contribution_weights: Dict[str, float] = field(default_factory=dict)

    # Confidence
    confidence: float = 0.0
    consensus_level: float = 0.0

    # Emergence info
    emergence_pattern: str = ""
    iterations: int = 0

    # Timestamp
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SwarmDecision:
    """A decision made by the swarm"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Question
    question: str = ""
    options: List[Any] = field(default_factory=list)

    # Votes
    votes: Dict[int, List[str]] = field(default_factory=dict)  # option_idx -> node_ids
    weights: Dict[int, float] = field(default_factory=dict)     # option_idx -> total_weight

    # Decision
    chosen_option: Optional[int] = None
    confidence: float = 0.0

    # Process
    rounds: int = 0
    converged: bool = False

    def add_vote(self, option_idx: int, node_id: str, weight: float = 1.0):
        """Add vote"""
        if option_idx not in self.votes:
            self.votes[option_idx] = []
            self.weights[option_idx] = 0.0

        # Remove previous vote by this node
        for idx in self.votes:
            if node_id in self.votes[idx]:
                self.votes[idx].remove(node_id)
                self.weights[idx] -= weight

        self.votes[option_idx].append(node_id)
        self.weights[option_idx] += weight

    def decide(self) -> int:
        """Make decision"""
        if not self.weights:
            return -1

        # Find option with highest weight
        max_weight = max(self.weights.values())
        total_weight = sum(self.weights.values())

        for idx, weight in self.weights.items():
            if weight == max_weight:
                self.chosen_option = idx
                self.confidence = weight / total_weight if total_weight > 0 else 0
                return idx

        return -1


@dataclass
class EmergentPattern:
    """An emergent pattern in collective behavior"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Pattern description
    name: str = ""
    pattern_type: str = ""  # synchronization, clustering, hierarchy, wave

    # Characteristics
    frequency: float = 0.0      # How often it occurs
    strength: float = 0.0       # Pattern strength
    stability: float = 0.0      # How stable

    # Participating nodes
    nodes: List[str] = field(default_factory=list)

    # Temporal
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    occurrences: int = 0

    def record_occurrence(self, nodes: List[str], strength: float):
        """Record pattern occurrence"""
        self.occurrences += 1
        self.last_seen = datetime.now()
        self.nodes = nodes
        self.strength = (self.strength * 0.9 + strength * 0.1)  # Smoothed

        # Calculate stability
        duration = (self.last_seen - self.first_seen).total_seconds()
        if duration > 0:
            self.frequency = self.occurrences / duration
            self.stability = min(1.0, self.frequency * self.strength)


class CollectiveIntelligence:
    """
    Collective intelligence coordinator.
    """

    def __init__(self):
        self.thoughts: Dict[str, CollectiveThought] = {}
        self.decisions: Dict[str, SwarmDecision] = {}
        self.patterns: Dict[str, EmergentPattern] = {}

        # Node capabilities
        self.node_capabilities: Dict[str, Dict[str, float]] = {}

        # Aggregation methods
        self.aggregation_method: str = "weighted_average"

    def register_node(self, node_id: str, capabilities: Dict[str, float]):
        """Register node capabilities"""
        self.node_capabilities[node_id] = capabilities

    def aggregate_insights(
        self,
        insights: List[Tuple[str, Any, float]],  # (node_id, insight, confidence)
        thought_type: str = "insight"
    ) -> CollectiveThought:
        """Aggregate insights from multiple nodes"""
        thought = CollectiveThought(thought_type=thought_type)

        # Collect contributions
        for node_id, insight, confidence in insights:
            thought.contributors.append(node_id)
            thought.contribution_weights[node_id] = confidence

        # Aggregate based on method
        if self.aggregation_method == "weighted_average":
            total_weight = sum(thought.contribution_weights.values())

            if total_weight > 0:
                # For numeric insights
                if all(isinstance(i[1], (int, float)) for i in insights):
                    weighted_sum = sum(
                        i[1] * thought.contribution_weights[i[0]]
                        for i in insights
                    )
                    thought.content = weighted_sum / total_weight
                else:
                    # For non-numeric, use highest confidence
                    best_insight = max(insights, key=lambda x: x[2])
                    thought.content = best_insight[1]

                thought.confidence = total_weight / len(insights)

        elif self.aggregation_method == "voting":
            # Count votes for each unique insight
            vote_counts: Dict[Any, float] = {}
            for node_id, insight, confidence in insights:
                key = str(insight)
                if key not in vote_counts:
                    vote_counts[key] = 0
                vote_counts[key] += confidence

            # Best voted
            if vote_counts:
                best_key = max(vote_counts.keys(), key=lambda k: vote_counts[k])
                thought.content = best_key
                thought.confidence = vote_counts[best_key] / sum(vote_counts.values())

        # Calculate consensus
        if len(insights) > 1:
            # Variance of contributions indicates consensus
            values = list(thought.contribution_weights.values())
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            thought.consensus_level = 1.0 / (1.0 + variance)
        else:
            thought.consensus_level = 1.0

        self.thoughts[thought.id] = thought
        return thought

    def swarm_decide(
        self,
        question: str,
        options: List[Any],
        node_preferences: Dict[str, Dict[int, float]],  # node_id -> {option_idx: preference}
        rounds: int = 3
    ) -> SwarmDecision:
        """Make swarm decision"""
        decision = SwarmDecision(question=question, options=options)

        # Initial votes
        for node_id, prefs in node_preferences.items():
            best_option = max(prefs.keys(), key=lambda k: prefs[k])
            weight = self._get_node_weight(node_id)
            decision.add_vote(best_option, node_id, weight)

        # Iterative refinement
        for round_num in range(rounds):
            decision.rounds += 1

            # Nodes can see collective preference and adjust
            current_best = decision.decide()

            # Check for convergence
            if decision.confidence > 0.8:
                decision.converged = True
                break

        decision.decide()
        self.decisions[decision.id] = decision
        return decision

    def _get_node_weight(self, node_id: str) -> float:
        """Get node voting weight"""
        if node_id not in self.node_capabilities:
            return 1.0

        caps = self.node_capabilities[node_id]
        return sum(caps.values()) / len(caps) if caps else 1.0

    def detect_pattern(
        self,
        node_states: Dict[str, Any],
        pattern_type: str = "synchronization"
    ) -> Optional[EmergentPattern]:
        """Detect emergent patterns"""
        if pattern_type == "synchronization":
            return self._detect_synchronization(node_states)
        elif pattern_type == "clustering":
            return self._detect_clustering(node_states)
        return None

    def _detect_synchronization(
        self,
        node_states: Dict[str, Any]
    ) -> Optional[EmergentPattern]:
        """Detect synchronization pattern"""
        if not node_states:
            return None

        # Check if states are similar
        values = list(node_states.values())

        # For numeric states
        if all(isinstance(v, (int, float)) for v in values):
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)

            # Low variance = high synchronization
            sync_strength = 1.0 / (1.0 + variance)

            if sync_strength > 0.7:
                pattern = EmergentPattern(
                    name="state_synchronization",
                    pattern_type="synchronization",
                    strength=sync_strength,
                    nodes=list(node_states.keys())
                )

                # Update existing or add new
                pattern_key = f"sync_{pattern_type}"
                if pattern_key in self.patterns:
                    self.patterns[pattern_key].record_occurrence(
                        pattern.nodes, sync_strength
                    )
                    return self.patterns[pattern_key]
                else:
                    self.patterns[pattern_key] = pattern
                    return pattern

        return None

    def _detect_clustering(
        self,
        node_states: Dict[str, Any]
    ) -> Optional[EmergentPattern]:
        """Detect clustering pattern"""
        if len(node_states) < 3:
            return None

        # Simple clustering: group by value
        clusters: Dict[Any, List[str]] = {}

        for node_id, state in node_states.items():
            key = str(state)
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(node_id)

        # Detect significant clusters
        largest_cluster = max(clusters.values(), key=len) if clusters else []

        if len(largest_cluster) >= len(node_states) * 0.5:
            # Significant cluster found
            pattern = EmergentPattern(
                name="state_clustering",
                pattern_type="clustering",
                strength=len(largest_cluster) / len(node_states),
                nodes=largest_cluster
            )

            pattern_key = f"cluster_{len(clusters)}"
            self.patterns[pattern_key] = pattern
            return pattern

        return None


class HiveMind:
    """
    Unified hive mind system.
    """

    def __init__(self):
        self.collective = CollectiveIntelligence()

        # Global state
        self.global_state: Dict[str, Any] = {}

        # Thought stream
        self.thought_stream: List[CollectiveThought] = []

        # Configuration
        self.sync_interval_seconds: int = 1
        self.thought_retention: int = 1000

    def think(
        self,
        inputs: List[Tuple[str, Any]],  # (node_id, input)
        thought_type: str = "insight"
    ) -> CollectiveThought:
        """Collective thinking"""
        # Convert to weighted insights
        insights = [
            (node_id, inp, 1.0)
            for node_id, inp in inputs
        ]

        thought = self.collective.aggregate_insights(insights, thought_type)

        # Add to stream
        self.thought_stream.append(thought)

        # Trim
        if len(self.thought_stream) > self.thought_retention:
            self.thought_stream = self.thought_stream[-self.thought_retention:]

        return thought

    def decide(
        self,
        question: str,
        options: List[Any],
        node_votes: Dict[str, int]  # node_id -> option_idx
    ) -> SwarmDecision:
        """Collective decision"""
        # Convert to preference format
        preferences = {
            node_id: {vote: 1.0}
            for node_id, vote in node_votes.items()
        }

        return self.collective.swarm_decide(question, options, preferences)

    def update_global_state(self, node_id: str, state: Dict[str, Any]):
        """Update global state from node"""
        for key, value in state.items():
            global_key = f"{node_id}.{key}"
            self.global_state[global_key] = value

    def get_consensus_state(self, key: str) -> Any:
        """Get consensus on a state value"""
        # Collect all node values for this key
        values = []
        for global_key, value in self.global_state.items():
            if global_key.endswith(f".{key}"):
                values.append(value)

        if not values:
            return None

        # Numeric consensus
        if all(isinstance(v, (int, float)) for v in values):
            return sum(values) / len(values)

        # Mode for categorical
        from collections import Counter
        counter = Counter(str(v) for v in values)
        return counter.most_common(1)[0][0] if counter else None

    def get_collective_stats(self) -> Dict[str, Any]:
        """Get hive mind statistics"""
        return {
            'total_thoughts': len(self.thought_stream),
            'total_decisions': len(self.collective.decisions),
            'detected_patterns': len(self.collective.patterns),
            'registered_nodes': len(self.collective.node_capabilities),
            'avg_consensus': (
                sum(t.consensus_level for t in self.thought_stream) / len(self.thought_stream)
                if self.thought_stream else 0
            )
        }


# Export all
__all__ = [
    'CollectiveThought',
    'SwarmDecision',
    'EmergentPattern',
    'CollectiveIntelligence',
    'HiveMind',
]
