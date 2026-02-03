#!/usr/bin/env python3
"""
BAEL - Reputation Manager
Advanced trust networks and reputation systems.

Features:
- Trust scoring
- Reputation calculation
- Rating systems
- Decay mechanisms
- Network effects
- Credibility assessment
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
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class TrustLevel(Enum):
    """Trust level categories."""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class RatingType(Enum):
    """Types of ratings."""
    BINARY = "binary"  # Like/Dislike
    STARS = "stars"  # 1-5 stars
    CONTINUOUS = "continuous"  # 0.0-1.0
    WEIGHTED = "weighted"


class ReputationMetric(Enum):
    """Reputation metrics."""
    RELIABILITY = "reliability"
    ACCURACY = "accuracy"
    RESPONSIVENESS = "responsiveness"
    QUALITY = "quality"
    HELPFULNESS = "helpfulness"


class AggregationMethod(Enum):
    """Aggregation methods for reputation."""
    AVERAGE = "average"
    WEIGHTED_AVERAGE = "weighted_average"
    BAYESIAN = "bayesian"
    ELO = "elo"
    PAGERANK = "pagerank"


class DecayType(Enum):
    """Types of decay functions."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    NONE = "none"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Entity:
    """An entity with reputation."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rating:
    """A rating given by one entity to another."""
    rating_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rater_id: str = ""
    ratee_id: str = ""
    value: float = 0.0
    rating_type: RatingType = RatingType.CONTINUOUS
    metric: Optional[ReputationMetric] = None
    timestamp: datetime = field(default_factory=datetime.now)
    context: str = ""


@dataclass
class TrustRelation:
    """A trust relationship between entities."""
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trustor_id: str = ""  # Who trusts
    trustee_id: str = ""  # Who is trusted
    trust_value: float = 0.5  # 0-1
    confidence: float = 1.0  # Confidence in the trust value
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Reputation:
    """Reputation score for an entity."""
    rep_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    overall_score: float = 0.5
    metric_scores: Dict[str, float] = field(default_factory=dict)
    rating_count: int = 0
    trust_level: TrustLevel = TrustLevel.MEDIUM
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class CredibilityAssessment:
    """Assessment of an entity's credibility."""
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    credibility_score: float = 0.5
    factors: Dict[str, float] = field(default_factory=dict)
    assessment_time: datetime = field(default_factory=datetime.now)


# =============================================================================
# ENTITY MANAGER
# =============================================================================

class EntityManager:
    """Manage entities in the reputation system."""

    def __init__(self):
        self._entities: Dict[str, Entity] = {}

    def create_entity(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """Create a new entity."""
        entity = Entity(
            name=name,
            metadata=metadata or {}
        )
        self._entities[entity.entity_id] = entity
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity."""
        return self._entities.get(entity_id)

    def list_entities(self) -> List[Entity]:
        """List all entities."""
        return list(self._entities.values())

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity."""
        if entity_id in self._entities:
            del self._entities[entity_id]
            return True
        return False


# =============================================================================
# RATING MANAGER
# =============================================================================

class RatingManager:
    """Manage ratings between entities."""

    def __init__(self):
        self._ratings: Dict[str, Rating] = {}
        self._by_ratee: Dict[str, List[str]] = defaultdict(list)
        self._by_rater: Dict[str, List[str]] = defaultdict(list)

    def add_rating(
        self,
        rater_id: str,
        ratee_id: str,
        value: float,
        rating_type: RatingType = RatingType.CONTINUOUS,
        metric: Optional[ReputationMetric] = None,
        context: str = ""
    ) -> Rating:
        """Add a rating."""
        # Normalize value
        if rating_type == RatingType.BINARY:
            value = 1.0 if value > 0 else 0.0
        elif rating_type == RatingType.STARS:
            value = max(1, min(5, round(value))) / 5.0
        else:
            value = max(0.0, min(1.0, value))

        rating = Rating(
            rater_id=rater_id,
            ratee_id=ratee_id,
            value=value,
            rating_type=rating_type,
            metric=metric,
            context=context
        )

        self._ratings[rating.rating_id] = rating
        self._by_ratee[ratee_id].append(rating.rating_id)
        self._by_rater[rater_id].append(rating.rating_id)

        return rating

    def get_ratings_for(self, entity_id: str) -> List[Rating]:
        """Get all ratings for an entity."""
        rating_ids = self._by_ratee.get(entity_id, [])
        return [self._ratings[rid] for rid in rating_ids if rid in self._ratings]

    def get_ratings_by(self, entity_id: str) -> List[Rating]:
        """Get all ratings by an entity."""
        rating_ids = self._by_rater.get(entity_id, [])
        return [self._ratings[rid] for rid in rating_ids if rid in self._ratings]

    def average_rating(self, entity_id: str) -> float:
        """Calculate average rating for an entity."""
        ratings = self.get_ratings_for(entity_id)
        if not ratings:
            return 0.5
        return sum(r.value for r in ratings) / len(ratings)


# =============================================================================
# TRUST NETWORK
# =============================================================================

class TrustNetwork:
    """Manage trust relationships between entities."""

    def __init__(self):
        self._relations: Dict[str, TrustRelation] = {}
        self._trust_graph: Dict[str, Dict[str, str]] = defaultdict(dict)  # trustor -> trustee -> relation_id

    def set_trust(
        self,
        trustor_id: str,
        trustee_id: str,
        trust_value: float,
        confidence: float = 1.0
    ) -> TrustRelation:
        """Set trust from one entity to another."""
        trust_value = max(0.0, min(1.0, trust_value))
        confidence = max(0.0, min(1.0, confidence))

        # Check if relation exists
        existing_id = self._trust_graph.get(trustor_id, {}).get(trustee_id)

        if existing_id and existing_id in self._relations:
            relation = self._relations[existing_id]
            relation.trust_value = trust_value
            relation.confidence = confidence
            relation.updated_at = datetime.now()
        else:
            relation = TrustRelation(
                trustor_id=trustor_id,
                trustee_id=trustee_id,
                trust_value=trust_value,
                confidence=confidence
            )
            self._relations[relation.relation_id] = relation
            self._trust_graph[trustor_id][trustee_id] = relation.relation_id

        return relation

    def get_trust(
        self,
        trustor_id: str,
        trustee_id: str
    ) -> Optional[float]:
        """Get direct trust value."""
        rel_id = self._trust_graph.get(trustor_id, {}).get(trustee_id)
        if rel_id and rel_id in self._relations:
            return self._relations[rel_id].trust_value
        return None

    def get_trustees(self, trustor_id: str) -> List[Tuple[str, float]]:
        """Get entities trusted by this entity."""
        result = []
        for trustee_id, rel_id in self._trust_graph.get(trustor_id, {}).items():
            if rel_id in self._relations:
                result.append((trustee_id, self._relations[rel_id].trust_value))
        return result

    def propagated_trust(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3
    ) -> float:
        """Calculate propagated trust through network."""
        if source_id == target_id:
            return 1.0

        # Direct trust
        direct = self.get_trust(source_id, target_id)
        if direct is not None:
            return direct

        # BFS for propagated trust
        visited = {source_id}
        queue = [(source_id, 1.0, 0)]  # (entity, accumulated_trust, depth)
        trust_values = []

        while queue:
            current, acc_trust, depth = queue.pop(0)

            if depth >= max_depth:
                continue

            for trustee_id, trust_val in self.get_trustees(current):
                if trustee_id in visited:
                    continue

                new_trust = acc_trust * trust_val

                if trustee_id == target_id:
                    trust_values.append(new_trust)
                else:
                    visited.add(trustee_id)
                    queue.append((trustee_id, new_trust, depth + 1))

        if not trust_values:
            return 0.5  # Default neutral

        # Average of all paths
        return sum(trust_values) / len(trust_values)


# =============================================================================
# REPUTATION CALCULATOR
# =============================================================================

class ReputationCalculator:
    """Calculate reputation scores."""

    def __init__(
        self,
        rating_manager: RatingManager,
        trust_network: TrustNetwork
    ):
        self._ratings = rating_manager
        self._trust = trust_network
        self._reputations: Dict[str, Reputation] = {}
        self._decay_type = DecayType.EXPONENTIAL
        self._decay_rate = 0.01  # Per day

    def set_decay(
        self,
        decay_type: DecayType,
        decay_rate: float = 0.01
    ) -> None:
        """Set decay parameters."""
        self._decay_type = decay_type
        self._decay_rate = decay_rate

    def calculate_reputation(
        self,
        entity_id: str,
        method: AggregationMethod = AggregationMethod.WEIGHTED_AVERAGE
    ) -> Reputation:
        """Calculate reputation for an entity."""
        if method == AggregationMethod.AVERAGE:
            return self._simple_average(entity_id)
        elif method == AggregationMethod.WEIGHTED_AVERAGE:
            return self._weighted_average(entity_id)
        elif method == AggregationMethod.BAYESIAN:
            return self._bayesian(entity_id)
        else:
            return self._simple_average(entity_id)

    def _simple_average(self, entity_id: str) -> Reputation:
        """Simple average of ratings."""
        ratings = self._ratings.get_ratings_for(entity_id)

        if not ratings:
            rep = Reputation(
                entity_id=entity_id,
                overall_score=0.5,
                rating_count=0,
                trust_level=TrustLevel.MEDIUM
            )
            self._reputations[entity_id] = rep
            return rep

        # Calculate overall and by metric
        metric_scores: Dict[str, List[float]] = defaultdict(list)
        all_scores = []

        for rating in ratings:
            decayed = self._apply_decay(rating.value, rating.timestamp)
            all_scores.append(decayed)

            if rating.metric:
                metric_scores[rating.metric.value].append(decayed)

        overall = sum(all_scores) / len(all_scores)
        metrics = {k: sum(v) / len(v) for k, v in metric_scores.items()}

        rep = Reputation(
            entity_id=entity_id,
            overall_score=overall,
            metric_scores=metrics,
            rating_count=len(ratings),
            trust_level=self._score_to_level(overall)
        )

        self._reputations[entity_id] = rep
        return rep

    def _weighted_average(self, entity_id: str) -> Reputation:
        """Weighted average based on rater trust."""
        ratings = self._ratings.get_ratings_for(entity_id)

        if not ratings:
            rep = Reputation(
                entity_id=entity_id,
                overall_score=0.5,
                rating_count=0,
                trust_level=TrustLevel.MEDIUM
            )
            self._reputations[entity_id] = rep
            return rep

        # Calculate weighted scores
        weighted_sum = 0.0
        weight_total = 0.0

        metric_weighted: Dict[str, Tuple[float, float]] = defaultdict(lambda: (0.0, 0.0))

        for rating in ratings:
            # Get rater's trust/reputation as weight
            rater_rep = self._reputations.get(rating.rater_id)
            weight = rater_rep.overall_score if rater_rep else 0.5
            weight = max(0.1, weight)  # Minimum weight

            decayed = self._apply_decay(rating.value, rating.timestamp)

            weighted_sum += decayed * weight
            weight_total += weight

            if rating.metric:
                curr = metric_weighted[rating.metric.value]
                metric_weighted[rating.metric.value] = (
                    curr[0] + decayed * weight,
                    curr[1] + weight
                )

        overall = weighted_sum / weight_total if weight_total > 0 else 0.5

        metrics = {}
        for k, (ws, wt) in metric_weighted.items():
            metrics[k] = ws / wt if wt > 0 else 0.5

        rep = Reputation(
            entity_id=entity_id,
            overall_score=overall,
            metric_scores=metrics,
            rating_count=len(ratings),
            trust_level=self._score_to_level(overall)
        )

        self._reputations[entity_id] = rep
        return rep

    def _bayesian(self, entity_id: str) -> Reputation:
        """Bayesian reputation with prior."""
        ratings = self._ratings.get_ratings_for(entity_id)

        # Prior: neutral reputation
        prior_alpha = 1.0
        prior_beta = 1.0

        # Posterior
        positive = sum(1 for r in ratings if r.value >= 0.5)
        negative = len(ratings) - positive

        alpha = prior_alpha + positive
        beta = prior_beta + negative

        # Mean of Beta distribution
        overall = alpha / (alpha + beta)

        rep = Reputation(
            entity_id=entity_id,
            overall_score=overall,
            rating_count=len(ratings),
            trust_level=self._score_to_level(overall)
        )

        self._reputations[entity_id] = rep
        return rep

    def _apply_decay(self, value: float, timestamp: datetime) -> float:
        """Apply time decay to a value."""
        if self._decay_type == DecayType.NONE:
            return value

        now = datetime.now()
        days = (now - timestamp).total_seconds() / 86400

        if self._decay_type == DecayType.LINEAR:
            decay = max(0, 1 - self._decay_rate * days)
        else:  # Exponential
            decay = math.exp(-self._decay_rate * days)

        # Decay towards neutral (0.5)
        return 0.5 + (value - 0.5) * decay

    def _score_to_level(self, score: float) -> TrustLevel:
        """Convert score to trust level."""
        if score < 0.2:
            return TrustLevel.UNTRUSTED
        elif score < 0.4:
            return TrustLevel.LOW
        elif score < 0.6:
            return TrustLevel.MEDIUM
        elif score < 0.8:
            return TrustLevel.HIGH
        else:
            return TrustLevel.VERIFIED

    def get_reputation(self, entity_id: str) -> Optional[Reputation]:
        """Get stored reputation."""
        return self._reputations.get(entity_id)


# =============================================================================
# CREDIBILITY ASSESSOR
# =============================================================================

class CredibilityAssessor:
    """Assess credibility of entities."""

    def __init__(
        self,
        reputation_calculator: ReputationCalculator,
        trust_network: TrustNetwork
    ):
        self._reputation = reputation_calculator
        self._trust = trust_network

    def assess(
        self,
        entity_id: str,
        assessor_id: Optional[str] = None
    ) -> CredibilityAssessment:
        """Assess credibility of an entity."""
        factors = {}

        # Factor 1: Reputation score
        rep = self._reputation.get_reputation(entity_id)
        if rep:
            factors['reputation'] = rep.overall_score
        else:
            factors['reputation'] = 0.5

        # Factor 2: Direct trust (if assessor provided)
        if assessor_id:
            direct = self._trust.get_trust(assessor_id, entity_id)
            if direct is not None:
                factors['direct_trust'] = direct
            else:
                # Propagated trust
                prop = self._trust.propagated_trust(assessor_id, entity_id)
                factors['propagated_trust'] = prop

        # Factor 3: Network centrality (simple version)
        trustees = len(self._trust.get_trustees(entity_id))
        factors['network_size'] = min(1.0, trustees / 10.0)

        # Factor 4: Rating count (experience)
        if rep:
            factors['experience'] = min(1.0, rep.rating_count / 100.0)
        else:
            factors['experience'] = 0.0

        # Calculate overall credibility
        weights = {
            'reputation': 0.4,
            'direct_trust': 0.3,
            'propagated_trust': 0.2,
            'network_size': 0.15,
            'experience': 0.15
        }

        credibility = 0.0
        total_weight = 0.0

        for factor, value in factors.items():
            w = weights.get(factor, 0.1)
            credibility += value * w
            total_weight += w

        credibility = credibility / total_weight if total_weight > 0 else 0.5

        return CredibilityAssessment(
            entity_id=entity_id,
            credibility_score=credibility,
            factors=factors
        )


# =============================================================================
# REPUTATION MANAGER
# =============================================================================

class ReputationManager:
    """
    Reputation Manager for BAEL.

    Advanced trust networks and reputation systems.
    """

    def __init__(self):
        self._entities = EntityManager()
        self._ratings = RatingManager()
        self._trust = TrustNetwork()
        self._reputation = ReputationCalculator(self._ratings, self._trust)
        self._credibility = CredibilityAssessor(self._reputation, self._trust)

    # -------------------------------------------------------------------------
    # ENTITY MANAGEMENT
    # -------------------------------------------------------------------------

    def create_entity(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """Create a new entity."""
        return self._entities.create_entity(name, metadata)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity."""
        return self._entities.get_entity(entity_id)

    def list_entities(self) -> List[Entity]:
        """List all entities."""
        return self._entities.list_entities()

    # -------------------------------------------------------------------------
    # RATING MANAGEMENT
    # -------------------------------------------------------------------------

    def rate(
        self,
        rater_id: str,
        ratee_id: str,
        value: float,
        rating_type: RatingType = RatingType.CONTINUOUS,
        metric: Optional[ReputationMetric] = None,
        context: str = ""
    ) -> Rating:
        """Add a rating."""
        return self._ratings.add_rating(
            rater_id, ratee_id, value, rating_type, metric, context
        )

    def get_ratings_for(self, entity_id: str) -> List[Rating]:
        """Get ratings for an entity."""
        return self._ratings.get_ratings_for(entity_id)

    def average_rating(self, entity_id: str) -> float:
        """Get average rating for an entity."""
        return self._ratings.average_rating(entity_id)

    # -------------------------------------------------------------------------
    # TRUST MANAGEMENT
    # -------------------------------------------------------------------------

    def set_trust(
        self,
        trustor_id: str,
        trustee_id: str,
        trust_value: float,
        confidence: float = 1.0
    ) -> TrustRelation:
        """Set trust relationship."""
        return self._trust.set_trust(
            trustor_id, trustee_id, trust_value, confidence
        )

    def get_trust(
        self,
        trustor_id: str,
        trustee_id: str
    ) -> Optional[float]:
        """Get direct trust value."""
        return self._trust.get_trust(trustor_id, trustee_id)

    def propagated_trust(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3
    ) -> float:
        """Get propagated trust."""
        return self._trust.propagated_trust(source_id, target_id, max_depth)

    def get_trustees(self, trustor_id: str) -> List[Tuple[str, float]]:
        """Get entities trusted by this entity."""
        return self._trust.get_trustees(trustor_id)

    # -------------------------------------------------------------------------
    # REPUTATION CALCULATION
    # -------------------------------------------------------------------------

    def calculate_reputation(
        self,
        entity_id: str,
        method: AggregationMethod = AggregationMethod.WEIGHTED_AVERAGE
    ) -> Reputation:
        """Calculate reputation for an entity."""
        return self._reputation.calculate_reputation(entity_id, method)

    def get_reputation(self, entity_id: str) -> Optional[Reputation]:
        """Get stored reputation."""
        return self._reputation.get_reputation(entity_id)

    def set_decay(
        self,
        decay_type: DecayType,
        decay_rate: float = 0.01
    ) -> None:
        """Set decay parameters."""
        self._reputation.set_decay(decay_type, decay_rate)

    # -------------------------------------------------------------------------
    # CREDIBILITY ASSESSMENT
    # -------------------------------------------------------------------------

    def assess_credibility(
        self,
        entity_id: str,
        assessor_id: Optional[str] = None
    ) -> CredibilityAssessment:
        """Assess credibility of an entity."""
        return self._credibility.assess(entity_id, assessor_id)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Reputation Manager."""
    print("=" * 70)
    print("BAEL - REPUTATION MANAGER DEMO")
    print("Advanced Trust Networks and Reputation Systems")
    print("=" * 70)
    print()

    manager = ReputationManager()

    # 1. Create Entities
    print("1. CREATE ENTITIES:")
    print("-" * 40)

    alice = manager.create_entity("Alice", {"role": "expert"})
    bob = manager.create_entity("Bob", {"role": "reviewer"})
    carol = manager.create_entity("Carol", {"role": "user"})
    dave = manager.create_entity("Dave", {"role": "newcomer"})

    print(f"   Created: {alice.name}, {bob.name}, {carol.name}, {dave.name}")
    print()

    # 2. Add Ratings
    print("2. ADD RATINGS:")
    print("-" * 40)

    # Alice rates Bob
    r1 = manager.rate(
        alice.entity_id, bob.entity_id, 0.9,
        metric=ReputationMetric.QUALITY
    )

    # Bob rates Carol
    r2 = manager.rate(
        bob.entity_id, carol.entity_id, 0.7,
        metric=ReputationMetric.HELPFULNESS
    )

    # Carol rates Alice
    r3 = manager.rate(
        carol.entity_id, alice.entity_id, 0.85,
        metric=ReputationMetric.RELIABILITY
    )

    # Dave rates everyone
    manager.rate(dave.entity_id, alice.entity_id, 0.6)
    manager.rate(dave.entity_id, bob.entity_id, 0.8)
    manager.rate(dave.entity_id, carol.entity_id, 0.5)

    print(f"   Alice -> Bob: 0.9 (quality)")
    print(f"   Bob -> Carol: 0.7 (helpfulness)")
    print(f"   Carol -> Alice: 0.85 (reliability)")
    print(f"   Dave rated Alice, Bob, Carol")
    print()

    # 3. Set Trust Relationships
    print("3. TRUST RELATIONSHIPS:")
    print("-" * 40)

    manager.set_trust(alice.entity_id, bob.entity_id, 0.9)
    manager.set_trust(bob.entity_id, carol.entity_id, 0.7)
    manager.set_trust(carol.entity_id, dave.entity_id, 0.5)
    manager.set_trust(alice.entity_id, carol.entity_id, 0.6)

    print(f"   Alice trusts Bob: 0.9")
    print(f"   Bob trusts Carol: 0.7")
    print(f"   Carol trusts Dave: 0.5")
    print(f"   Alice trusts Carol: 0.6")
    print()

    # 4. Direct vs Propagated Trust
    print("4. DIRECT VS PROPAGATED TRUST:")
    print("-" * 40)

    direct = manager.get_trust(alice.entity_id, bob.entity_id)
    propagated = manager.propagated_trust(alice.entity_id, dave.entity_id)

    print(f"   Alice -> Bob (direct): {direct}")
    print(f"   Alice -> Dave (propagated): {propagated:.3f}")
    print()

    # 5. Calculate Reputation
    print("5. CALCULATE REPUTATION:")
    print("-" * 40)

    for entity in [alice, bob, carol, dave]:
        rep = manager.calculate_reputation(
            entity.entity_id,
            AggregationMethod.WEIGHTED_AVERAGE
        )
        print(f"   {entity.name}: {rep.overall_score:.3f} ({rep.trust_level.value})")
        print(f"      Ratings: {rep.rating_count}, Metrics: {rep.metric_scores}")
    print()

    # 6. Bayesian Reputation
    print("6. BAYESIAN REPUTATION:")
    print("-" * 40)

    for entity in [alice, bob, carol]:
        rep = manager.calculate_reputation(
            entity.entity_id,
            AggregationMethod.BAYESIAN
        )
        print(f"   {entity.name}: {rep.overall_score:.3f}")
    print()

    # 7. Credibility Assessment
    print("7. CREDIBILITY ASSESSMENT:")
    print("-" * 40)

    cred = manager.assess_credibility(bob.entity_id, alice.entity_id)
    print(f"   Bob's credibility (from Alice's perspective):")
    print(f"   Score: {cred.credibility_score:.3f}")
    for factor, value in cred.factors.items():
        print(f"      {factor}: {value:.3f}")
    print()

    # 8. Set Decay
    print("8. DECAY SETTINGS:")
    print("-" * 40)

    manager.set_decay(DecayType.EXPONENTIAL, 0.01)
    print(f"   Decay type: Exponential")
    print(f"   Decay rate: 0.01 per day")
    print()

    # 9. Get Trustees
    print("9. TRUST NETWORK:")
    print("-" * 40)

    for entity in [alice, bob, carol]:
        trustees = manager.get_trustees(entity.entity_id)
        names = []
        for tid, tval in trustees:
            e = manager.get_entity(tid)
            names.append(f"{e.name if e else 'Unknown'}({tval:.1f})")
        print(f"   {entity.name} trusts: {', '.join(names) if names else 'nobody'}")
    print()

    # 10. Multi-metric Ratings
    print("10. MULTI-METRIC RATINGS:")
    print("-" * 40)

    # Add more ratings with different metrics
    manager.rate(alice.entity_id, bob.entity_id, 0.85, metric=ReputationMetric.ACCURACY)
    manager.rate(carol.entity_id, bob.entity_id, 0.75, metric=ReputationMetric.RESPONSIVENESS)

    rep = manager.calculate_reputation(bob.entity_id)
    print(f"   Bob's reputation by metric:")
    for metric, score in rep.metric_scores.items():
        print(f"      {metric}: {score:.3f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Reputation Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
