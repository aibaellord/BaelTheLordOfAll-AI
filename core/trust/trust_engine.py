#!/usr/bin/env python3
"""
BAEL - Trust Engine
Agent trust and reputation management.

Features:
- Trust assessment
- Reputation tracking
- Trust propagation
- Trust decay
- Trustworthiness scoring
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TrustLevel(Enum):
    """Trust levels."""
    UNTRUSTED = 0
    SUSPICIOUS = 1
    NEUTRAL = 2
    TRUSTED = 3
    HIGHLY_TRUSTED = 4


class TrustDimension(Enum):
    """Dimensions of trust."""
    COMPETENCE = "competence"
    INTEGRITY = "integrity"
    BENEVOLENCE = "benevolence"
    RELIABILITY = "reliability"
    PREDICTABILITY = "predictability"


class InteractionType(Enum):
    """Types of interactions."""
    TASK_COMPLETION = "task_completion"
    INFORMATION_SHARING = "information_sharing"
    RESOURCE_SHARING = "resource_sharing"
    COLLABORATION = "collaboration"
    RECOMMENDATION = "recommendation"


class InteractionOutcome(Enum):
    """Interaction outcomes."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    BETRAYAL = "betrayal"


class TrustUpdateType(Enum):
    """Trust update types."""
    DIRECT = "direct"
    WITNESS = "witness"
    REPUTATION = "reputation"
    DECAY = "decay"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TrustScore:
    """A trust score."""
    entity_id: str = ""
    overall: float = 0.5
    dimensions: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    interaction_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.dimensions:
            for dim in TrustDimension:
                self.dimensions[dim.value] = 0.5


@dataclass
class Interaction:
    """An interaction record."""
    interaction_id: str = ""
    source_id: str = ""
    target_id: str = ""
    interaction_type: InteractionType = InteractionType.TASK_COMPLETION
    outcome: InteractionOutcome = InteractionOutcome.SUCCESS
    context: Dict[str, Any] = field(default_factory=dict)
    importance: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.interaction_id:
            self.interaction_id = str(uuid.uuid4())[:8]


@dataclass
class TrustUpdate:
    """A trust update."""
    update_id: str = ""
    entity_id: str = ""
    update_type: TrustUpdateType = TrustUpdateType.DIRECT
    old_score: float = 0.0
    new_score: float = 0.0
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.update_id:
            self.update_id = str(uuid.uuid4())[:8]


@dataclass
class Recommendation:
    """A trust recommendation."""
    recommendation_id: str = ""
    recommender_id: str = ""
    target_id: str = ""
    score: float = 0.0
    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.recommendation_id:
            self.recommendation_id = str(uuid.uuid4())[:8]


@dataclass
class TrustRelationship:
    """A trust relationship."""
    source_id: str = ""
    target_id: str = ""
    trust_score: float = 0.5
    history: List[Tuple[datetime, float]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TrustStats:
    """Trust statistics."""
    total_entities: int = 0
    avg_trust: float = 0.0
    interactions_recorded: int = 0
    trust_updates: int = 0
    recommendations_processed: int = 0


# =============================================================================
# TRUST CALCULATOR
# =============================================================================

class TrustCalculator:
    """Calculate trust scores."""

    def __init__(self):
        self._dimension_weights: Dict[str, float] = {
            TrustDimension.COMPETENCE.value: 0.25,
            TrustDimension.INTEGRITY.value: 0.25,
            TrustDimension.BENEVOLENCE.value: 0.2,
            TrustDimension.RELIABILITY.value: 0.2,
            TrustDimension.PREDICTABILITY.value: 0.1
        }

        self._outcome_impacts: Dict[InteractionOutcome, float] = {
            InteractionOutcome.SUCCESS: 0.1,
            InteractionOutcome.PARTIAL: 0.02,
            InteractionOutcome.FAILURE: -0.1,
            InteractionOutcome.BETRAYAL: -0.3
        }

    def calculate_overall(self, dimensions: Dict[str, float]) -> float:
        """Calculate overall trust from dimensions."""
        total = 0.0
        total_weight = 0.0

        for dim, weight in self._dimension_weights.items():
            if dim in dimensions:
                total += dimensions[dim] * weight
                total_weight += weight

        if total_weight > 0:
            return total / total_weight

        return 0.5

    def update_from_interaction(
        self,
        current_score: TrustScore,
        interaction: Interaction,
        learning_rate: float = 0.1
    ) -> TrustScore:
        """Update trust from an interaction."""
        impact = self._outcome_impacts.get(interaction.outcome, 0.0)
        impact *= interaction.importance

        dims_affected = self._get_affected_dimensions(interaction.interaction_type)

        for dim in dims_affected:
            if dim in current_score.dimensions:
                old_val = current_score.dimensions[dim]
                new_val = old_val + learning_rate * impact
                current_score.dimensions[dim] = max(0.0, min(1.0, new_val))

        current_score.overall = self.calculate_overall(current_score.dimensions)
        current_score.interaction_count += 1
        current_score.confidence = min(
            1.0,
            current_score.confidence + 0.05
        )
        current_score.last_updated = datetime.now()

        return current_score

    def _get_affected_dimensions(
        self,
        interaction_type: InteractionType
    ) -> List[str]:
        """Get dimensions affected by interaction type."""
        mapping = {
            InteractionType.TASK_COMPLETION: [
                TrustDimension.COMPETENCE.value,
                TrustDimension.RELIABILITY.value
            ],
            InteractionType.INFORMATION_SHARING: [
                TrustDimension.INTEGRITY.value,
                TrustDimension.BENEVOLENCE.value
            ],
            InteractionType.RESOURCE_SHARING: [
                TrustDimension.BENEVOLENCE.value,
                TrustDimension.RELIABILITY.value
            ],
            InteractionType.COLLABORATION: [
                TrustDimension.COMPETENCE.value,
                TrustDimension.BENEVOLENCE.value,
                TrustDimension.PREDICTABILITY.value
            ],
            InteractionType.RECOMMENDATION: [
                TrustDimension.INTEGRITY.value,
                TrustDimension.COMPETENCE.value
            ]
        }

        return mapping.get(interaction_type, [])

    def apply_decay(
        self,
        score: TrustScore,
        decay_rate: float = 0.01,
        toward_neutral: bool = True
    ) -> TrustScore:
        """Apply trust decay."""
        neutral = 0.5

        for dim in score.dimensions:
            current = score.dimensions[dim]

            if toward_neutral:
                diff = neutral - current
                score.dimensions[dim] = current + decay_rate * diff
            else:
                score.dimensions[dim] = current * (1 - decay_rate)

        score.overall = self.calculate_overall(score.dimensions)
        score.last_updated = datetime.now()

        return score

    def combine_recommendations(
        self,
        current_score: TrustScore,
        recommendations: List[Recommendation],
        trust_in_recommenders: Dict[str, float]
    ) -> TrustScore:
        """Combine recommendations into trust score."""
        if not recommendations:
            return current_score

        weighted_sum = 0.0
        total_weight = 0.0

        for rec in recommendations:
            recommender_trust = trust_in_recommenders.get(rec.recommender_id, 0.5)
            weight = rec.weight * recommender_trust

            weighted_sum += rec.score * weight
            total_weight += weight

        if total_weight > 0:
            rec_score = weighted_sum / total_weight

            blend_factor = min(0.3, len(recommendations) * 0.05)

            for dim in current_score.dimensions:
                old_val = current_score.dimensions[dim]
                current_score.dimensions[dim] = (
                    (1 - blend_factor) * old_val +
                    blend_factor * rec_score
                )

            current_score.overall = self.calculate_overall(current_score.dimensions)

        return current_score


# =============================================================================
# TRUST STORE
# =============================================================================

class TrustStore:
    """Store and retrieve trust data."""

    def __init__(self):
        self._scores: Dict[str, TrustScore] = {}
        self._relationships: Dict[Tuple[str, str], TrustRelationship] = {}
        self._interactions: List[Interaction] = []
        self._updates: List[TrustUpdate] = []

    def get_score(self, entity_id: str) -> TrustScore:
        """Get trust score for an entity."""
        if entity_id not in self._scores:
            self._scores[entity_id] = TrustScore(entity_id=entity_id)

        return self._scores[entity_id]

    def set_score(self, entity_id: str, score: TrustScore) -> None:
        """Set trust score for an entity."""
        self._scores[entity_id] = score

    def get_relationship(
        self,
        source_id: str,
        target_id: str
    ) -> TrustRelationship:
        """Get trust relationship."""
        key = (source_id, target_id)

        if key not in self._relationships:
            self._relationships[key] = TrustRelationship(
                source_id=source_id,
                target_id=target_id
            )

        return self._relationships[key]

    def update_relationship(
        self,
        source_id: str,
        target_id: str,
        trust_score: float
    ) -> None:
        """Update trust relationship."""
        rel = self.get_relationship(source_id, target_id)
        rel.trust_score = trust_score
        rel.history.append((datetime.now(), trust_score))

        if len(rel.history) > 100:
            rel.history = rel.history[-100:]

    def record_interaction(self, interaction: Interaction) -> None:
        """Record an interaction."""
        self._interactions.append(interaction)

        if len(self._interactions) > 10000:
            self._interactions = self._interactions[-10000:]

    def record_update(self, update: TrustUpdate) -> None:
        """Record a trust update."""
        self._updates.append(update)

        if len(self._updates) > 10000:
            self._updates = self._updates[-10000:]

    def get_interactions(
        self,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Interaction]:
        """Get interactions."""
        if entity_id:
            filtered = [
                i for i in self._interactions
                if i.source_id == entity_id or i.target_id == entity_id
            ]
            return filtered[-limit:]

        return self._interactions[-limit:]

    def get_updates(
        self,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[TrustUpdate]:
        """Get trust updates."""
        if entity_id:
            filtered = [
                u for u in self._updates
                if u.entity_id == entity_id
            ]
            return filtered[-limit:]

        return self._updates[-limit:]

    def get_all_entities(self) -> List[str]:
        """Get all entity IDs."""
        return list(self._scores.keys())

    def get_trusted_entities(
        self,
        threshold: float = 0.6
    ) -> List[Tuple[str, float]]:
        """Get entities above trust threshold."""
        trusted = [
            (eid, score.overall)
            for eid, score in self._scores.items()
            if score.overall >= threshold
        ]

        return sorted(trusted, key=lambda x: x[1], reverse=True)


# =============================================================================
# REPUTATION AGGREGATOR
# =============================================================================

class ReputationAggregator:
    """Aggregate reputation from multiple sources."""

    def __init__(self, trust_store: TrustStore):
        self._store = trust_store
        self._recommendations: Dict[str, List[Recommendation]] = defaultdict(list)

    def add_recommendation(
        self,
        recommender_id: str,
        target_id: str,
        score: float,
        weight: float = 1.0
    ) -> Recommendation:
        """Add a recommendation."""
        rec = Recommendation(
            recommender_id=recommender_id,
            target_id=target_id,
            score=max(0.0, min(1.0, score)),
            weight=weight
        )

        self._recommendations[target_id].append(rec)

        return rec

    def get_recommendations(
        self,
        target_id: str
    ) -> List[Recommendation]:
        """Get recommendations for an entity."""
        return self._recommendations.get(target_id, [])

    def calculate_reputation(
        self,
        entity_id: str
    ) -> float:
        """Calculate aggregated reputation."""
        recommendations = self.get_recommendations(entity_id)

        if not recommendations:
            return 0.5

        total = 0.0
        total_weight = 0.0

        for rec in recommendations:
            recommender_trust = self._store.get_score(rec.recommender_id).overall
            weight = rec.weight * recommender_trust

            total += rec.score * weight
            total_weight += weight

        if total_weight > 0:
            return total / total_weight

        return 0.5

    def get_reputation_breakdown(
        self,
        entity_id: str
    ) -> Dict[str, Any]:
        """Get detailed reputation breakdown."""
        recommendations = self.get_recommendations(entity_id)

        if not recommendations:
            return {
                "reputation": 0.5,
                "sources": 0,
                "breakdown": []
            }

        breakdown = []
        for rec in recommendations[-10:]:
            recommender_trust = self._store.get_score(rec.recommender_id).overall

            breakdown.append({
                "recommender": rec.recommender_id,
                "score": rec.score,
                "recommender_trust": recommender_trust,
                "effective_weight": rec.weight * recommender_trust
            })

        return {
            "reputation": self.calculate_reputation(entity_id),
            "sources": len(recommendations),
            "breakdown": breakdown
        }


# =============================================================================
# TRUST NETWORK
# =============================================================================

class TrustNetwork:
    """Model trust as a network."""

    def __init__(self, trust_store: TrustStore):
        self._store = trust_store
        self._edges: Dict[str, Set[str]] = defaultdict(set)

    def add_edge(self, source_id: str, target_id: str) -> None:
        """Add a trust edge."""
        self._edges[source_id].add(target_id)

    def get_neighbors(self, entity_id: str) -> Set[str]:
        """Get direct trust neighbors."""
        return self._edges.get(entity_id, set())

    def propagate_trust(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 3
    ) -> float:
        """Propagate trust through network."""
        if source_id == target_id:
            return 1.0

        direct_rel = self._store.get_relationship(source_id, target_id)
        if direct_rel.trust_score > 0:
            return direct_rel.trust_score

        paths = self._find_paths(source_id, target_id, max_hops)

        if not paths:
            return 0.0

        path_trusts = []

        for path in paths:
            trust = 1.0

            for i in range(len(path) - 1):
                rel = self._store.get_relationship(path[i], path[i + 1])
                trust *= rel.trust_score

            decay = 0.8 ** (len(path) - 1)
            path_trusts.append(trust * decay)

        return max(path_trusts) if path_trusts else 0.0

    def _find_paths(
        self,
        source: str,
        target: str,
        max_hops: int
    ) -> List[List[str]]:
        """Find paths between entities."""
        if max_hops <= 0:
            return []

        paths = []

        queue = deque([(source, [source])])

        while queue:
            current, path = queue.popleft()

            if len(path) > max_hops + 1:
                continue

            for neighbor in self.get_neighbors(current):
                if neighbor == target:
                    paths.append(path + [neighbor])
                elif neighbor not in path:
                    queue.append((neighbor, path + [neighbor]))

        return paths

    def get_trust_radius(
        self,
        entity_id: str,
        threshold: float = 0.5
    ) -> Dict[str, float]:
        """Get entities within trust radius."""
        result = {}

        queue = deque([(entity_id, 1.0, 0)])
        visited = {entity_id}

        while queue:
            current, trust, hops = queue.popleft()

            if hops > 3:
                continue

            for neighbor in self.get_neighbors(current):
                if neighbor in visited:
                    continue

                rel = self._store.get_relationship(current, neighbor)
                new_trust = trust * rel.trust_score * 0.8

                if new_trust >= threshold:
                    result[neighbor] = new_trust
                    visited.add(neighbor)
                    queue.append((neighbor, new_trust, hops + 1))

        return result


# =============================================================================
# TRUST ENGINE
# =============================================================================

class TrustEngine:
    """
    Trust Engine for BAEL.

    Agent trust and reputation management.
    """

    def __init__(self):
        self._store = TrustStore()
        self._calculator = TrustCalculator()
        self._reputation = ReputationAggregator(self._store)
        self._network = TrustNetwork(self._store)

        self._decay_interval = timedelta(days=1)
        self._stats = TrustStats()

    def get_trust(self, entity_id: str) -> TrustScore:
        """Get trust score for an entity."""
        return self._store.get_score(entity_id)

    def get_trust_level(self, entity_id: str) -> TrustLevel:
        """Get trust level for an entity."""
        score = self._store.get_score(entity_id)

        if score.overall >= 0.8:
            return TrustLevel.HIGHLY_TRUSTED
        elif score.overall >= 0.6:
            return TrustLevel.TRUSTED
        elif score.overall >= 0.4:
            return TrustLevel.NEUTRAL
        elif score.overall >= 0.2:
            return TrustLevel.SUSPICIOUS
        else:
            return TrustLevel.UNTRUSTED

    def record_interaction(
        self,
        source_id: str,
        target_id: str,
        interaction_type: InteractionType,
        outcome: InteractionOutcome,
        importance: float = 1.0,
        context: Optional[Dict[str, Any]] = None
    ) -> TrustScore:
        """Record an interaction and update trust."""
        interaction = Interaction(
            source_id=source_id,
            target_id=target_id,
            interaction_type=interaction_type,
            outcome=outcome,
            importance=importance,
            context=context or {}
        )

        self._store.record_interaction(interaction)
        self._stats.interactions_recorded += 1

        current_score = self._store.get_score(target_id)
        old_overall = current_score.overall

        updated_score = self._calculator.update_from_interaction(
            current_score, interaction
        )

        self._store.set_score(target_id, updated_score)

        self._store.update_relationship(source_id, target_id, updated_score.overall)
        self._network.add_edge(source_id, target_id)

        update = TrustUpdate(
            entity_id=target_id,
            update_type=TrustUpdateType.DIRECT,
            old_score=old_overall,
            new_score=updated_score.overall,
            reason=f"Interaction: {interaction_type.value} -> {outcome.value}"
        )
        self._store.record_update(update)
        self._stats.trust_updates += 1

        return updated_score

    def add_recommendation(
        self,
        recommender_id: str,
        target_id: str,
        score: float,
        weight: float = 1.0
    ) -> None:
        """Add a trust recommendation."""
        self._reputation.add_recommendation(
            recommender_id, target_id, score, weight
        )
        self._stats.recommendations_processed += 1

    def apply_recommendations(
        self,
        target_id: str
    ) -> TrustScore:
        """Apply recommendations to trust score."""
        current_score = self._store.get_score(target_id)
        old_overall = current_score.overall

        recommendations = self._reputation.get_recommendations(target_id)

        trust_in_recommenders = {
            rec.recommender_id: self._store.get_score(rec.recommender_id).overall
            for rec in recommendations
        }

        updated_score = self._calculator.combine_recommendations(
            current_score,
            recommendations,
            trust_in_recommenders
        )

        self._store.set_score(target_id, updated_score)

        update = TrustUpdate(
            entity_id=target_id,
            update_type=TrustUpdateType.REPUTATION,
            old_score=old_overall,
            new_score=updated_score.overall,
            reason=f"Applied {len(recommendations)} recommendations"
        )
        self._store.record_update(update)

        return updated_score

    def get_reputation(self, entity_id: str) -> float:
        """Get aggregated reputation."""
        return self._reputation.calculate_reputation(entity_id)

    def get_reputation_breakdown(
        self,
        entity_id: str
    ) -> Dict[str, Any]:
        """Get reputation breakdown."""
        return self._reputation.get_reputation_breakdown(entity_id)

    def propagate_trust(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 3
    ) -> float:
        """Propagate trust through network."""
        return self._network.propagate_trust(source_id, target_id, max_hops)

    def get_trust_radius(
        self,
        entity_id: str,
        threshold: float = 0.5
    ) -> Dict[str, float]:
        """Get entities within trust radius."""
        return self._network.get_trust_radius(entity_id, threshold)

    def apply_decay(
        self,
        entity_id: Optional[str] = None
    ) -> None:
        """Apply trust decay."""
        if entity_id:
            entities = [entity_id]
        else:
            entities = self._store.get_all_entities()

        for eid in entities:
            score = self._store.get_score(eid)

            time_since_update = datetime.now() - score.last_updated

            if time_since_update > self._decay_interval:
                old_overall = score.overall

                updated = self._calculator.apply_decay(score)
                self._store.set_score(eid, updated)

                update = TrustUpdate(
                    entity_id=eid,
                    update_type=TrustUpdateType.DECAY,
                    old_score=old_overall,
                    new_score=updated.overall,
                    reason="Time-based decay"
                )
                self._store.record_update(update)

    def get_trusted_entities(
        self,
        threshold: float = 0.6
    ) -> List[Tuple[str, float]]:
        """Get entities above trust threshold."""
        return self._store.get_trusted_entities(threshold)

    def get_interaction_history(
        self,
        entity_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Interaction]:
        """Get interaction history."""
        return self._store.get_interactions(entity_id, limit)

    def get_trust_updates(
        self,
        entity_id: Optional[str] = None,
        limit: int = 50
    ) -> List[TrustUpdate]:
        """Get trust updates."""
        return self._store.get_updates(entity_id, limit)

    def get_trust_dimensions(
        self,
        entity_id: str
    ) -> Dict[str, float]:
        """Get trust dimensions for an entity."""
        score = self._store.get_score(entity_id)
        return score.dimensions.copy()

    def set_dimension_weight(
        self,
        dimension: TrustDimension,
        weight: float
    ) -> None:
        """Set weight for a trust dimension."""
        self._calculator._dimension_weights[dimension.value] = max(0.0, weight)

    def is_trusted(
        self,
        entity_id: str,
        threshold: float = 0.5
    ) -> bool:
        """Check if entity is trusted."""
        score = self._store.get_score(entity_id)
        return score.overall >= threshold

    def compare_trust(
        self,
        entity1_id: str,
        entity2_id: str
    ) -> Dict[str, Any]:
        """Compare trust between two entities."""
        score1 = self._store.get_score(entity1_id)
        score2 = self._store.get_score(entity2_id)

        comparison = {
            "entity1": {
                "id": entity1_id,
                "overall": score1.overall,
                "level": self.get_trust_level(entity1_id).name,
                "interactions": score1.interaction_count
            },
            "entity2": {
                "id": entity2_id,
                "overall": score2.overall,
                "level": self.get_trust_level(entity2_id).name,
                "interactions": score2.interaction_count
            },
            "difference": score1.overall - score2.overall,
            "more_trusted": entity1_id if score1.overall > score2.overall else entity2_id
        }

        return comparison

    @property
    def stats(self) -> TrustStats:
        """Get statistics."""
        self._stats.total_entities = len(self._store.get_all_entities())

        entities = self._store.get_all_entities()
        if entities:
            total_trust = sum(
                self._store.get_score(eid).overall
                for eid in entities
            )
            self._stats.avg_trust = total_trust / len(entities)

        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        stats = self.stats

        return {
            "total_entities": stats.total_entities,
            "avg_trust": f"{stats.avg_trust:.2f}",
            "interactions_recorded": stats.interactions_recorded,
            "trust_updates": stats.trust_updates,
            "recommendations_processed": stats.recommendations_processed,
            "trusted_entities": len(self.get_trusted_entities(0.6)),
            "highly_trusted": len(self.get_trusted_entities(0.8))
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Trust Engine."""
    print("=" * 70)
    print("BAEL - TRUST ENGINE DEMO")
    print("Agent Trust and Reputation Management")
    print("=" * 70)
    print()

    engine = TrustEngine()

    # 1. Record Interactions
    print("1. RECORD INTERACTIONS:")
    print("-" * 40)

    score1 = engine.record_interaction(
        "agent_a", "agent_b",
        InteractionType.TASK_COMPLETION,
        InteractionOutcome.SUCCESS
    )

    print(f"   agent_b after successful task: {score1.overall:.3f}")

    score2 = engine.record_interaction(
        "agent_a", "agent_b",
        InteractionType.COLLABORATION,
        InteractionOutcome.SUCCESS,
        importance=1.5
    )

    print(f"   agent_b after collaboration: {score2.overall:.3f}")

    score3 = engine.record_interaction(
        "agent_a", "agent_c",
        InteractionType.INFORMATION_SHARING,
        InteractionOutcome.FAILURE
    )

    print(f"   agent_c after failed sharing: {score3.overall:.3f}")
    print()

    # 2. Get Trust Levels
    print("2. GET TRUST LEVELS:")
    print("-" * 40)

    for entity in ["agent_b", "agent_c", "agent_d"]:
        level = engine.get_trust_level(entity)
        score = engine.get_trust(entity)
        print(f"   {entity}: {level.name} ({score.overall:.3f})")
    print()

    # 3. Trust Dimensions
    print("3. TRUST DIMENSIONS:")
    print("-" * 40)

    dims = engine.get_trust_dimensions("agent_b")
    print(f"   agent_b dimensions:")
    for dim, value in dims.items():
        print(f"     {dim}: {value:.3f}")
    print()

    # 4. Add Recommendations
    print("4. ADD RECOMMENDATIONS:")
    print("-" * 40)

    for i in range(5):
        engine.record_interaction(
            f"agent_{i}", "agent_a",
            InteractionType.TASK_COMPLETION,
            InteractionOutcome.SUCCESS
        )

    engine.add_recommendation("agent_b", "agent_x", 0.8, weight=1.0)
    engine.add_recommendation("agent_c", "agent_x", 0.6, weight=0.8)
    engine.add_recommendation("agent_d", "agent_x", 0.9, weight=0.5)

    reputation = engine.get_reputation("agent_x")
    print(f"   agent_x reputation: {reputation:.3f}")

    breakdown = engine.get_reputation_breakdown("agent_x")
    print(f"   Sources: {breakdown['sources']}")
    print()

    # 5. Apply Recommendations
    print("5. APPLY RECOMMENDATIONS:")
    print("-" * 40)

    before = engine.get_trust("agent_x").overall
    updated = engine.apply_recommendations("agent_x")

    print(f"   Before: {before:.3f}")
    print(f"   After: {updated.overall:.3f}")
    print()

    # 6. Build Trust Network
    print("6. BUILD TRUST NETWORK:")
    print("-" * 40)

    pairs = [
        ("agent_a", "agent_b"),
        ("agent_b", "agent_c"),
        ("agent_c", "agent_d"),
        ("agent_a", "agent_c"),
    ]

    for source, target in pairs:
        engine.record_interaction(
            source, target,
            InteractionType.TASK_COMPLETION,
            InteractionOutcome.SUCCESS
        )

    print("   Network edges created")
    print()

    # 7. Propagate Trust
    print("7. PROPAGATE TRUST:")
    print("-" * 40)

    propagated = engine.propagate_trust("agent_a", "agent_d", max_hops=3)
    print(f"   Trust from agent_a to agent_d: {propagated:.3f}")

    direct = engine.get_trust("agent_d").overall
    print(f"   Direct trust in agent_d: {direct:.3f}")
    print()

    # 8. Trust Radius
    print("8. TRUST RADIUS:")
    print("-" * 40)

    radius = engine.get_trust_radius("agent_a", threshold=0.3)

    print(f"   Entities within trust radius of agent_a:")
    for entity, trust in sorted(radius.items(), key=lambda x: x[1], reverse=True):
        print(f"     {entity}: {trust:.3f}")
    print()

    # 9. Compare Trust
    print("9. COMPARE TRUST:")
    print("-" * 40)

    comparison = engine.compare_trust("agent_b", "agent_c")

    print(f"   {comparison['entity1']['id']}: {comparison['entity1']['overall']:.3f}")
    print(f"   {comparison['entity2']['id']}: {comparison['entity2']['overall']:.3f}")
    print(f"   More trusted: {comparison['more_trusted']}")
    print()

    # 10. Get Trusted Entities
    print("10. GET TRUSTED ENTITIES:")
    print("-" * 40)

    trusted = engine.get_trusted_entities(threshold=0.5)

    print(f"   Trusted entities (>0.5):")
    for entity, score in trusted[:5]:
        print(f"     {entity}: {score:.3f}")
    print()

    # 11. Interaction History
    print("11. INTERACTION HISTORY:")
    print("-" * 40)

    history = engine.get_interaction_history(limit=5)

    print(f"   Recent interactions:")
    for interaction in history[:3]:
        print(f"     {interaction.source_id} -> {interaction.target_id}: {interaction.outcome.value}")
    print()

    # 12. Trust Updates
    print("12. TRUST UPDATES:")
    print("-" * 40)

    updates = engine.get_trust_updates(limit=5)

    print(f"   Recent updates:")
    for update in updates[:3]:
        delta = update.new_score - update.old_score
        sign = "+" if delta > 0 else ""
        print(f"     {update.entity_id}: {sign}{delta:.3f} ({update.update_type.value})")
    print()

    # 13. Statistics
    print("13. TRUST STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Entities: {stats.total_entities}")
    print(f"   Avg Trust: {stats.avg_trust:.3f}")
    print(f"   Interactions: {stats.interactions_recorded}")
    print(f"   Trust Updates: {stats.trust_updates}")
    print(f"   Recommendations: {stats.recommendations_processed}")
    print()

    # 14. Summary
    print("14. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Trust Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
