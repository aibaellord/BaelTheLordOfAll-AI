#!/usr/bin/env python3
"""
BAEL - Trust Manager
Advanced trust modeling and reputation management.

Features:
- Trust computation
- Trust propagation
- Reputation scoring
- Trust decay
- Trust evidence
- Trust policies
- Trust visualization
- Multi-dimensional trust
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

class TrustLevel(Enum):
    """Trust levels."""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FULLY_TRUSTED = "fully_trusted"


class TrustDimension(Enum):
    """Trust dimensions."""
    COMPETENCE = "competence"
    BENEVOLENCE = "benevolence"
    INTEGRITY = "integrity"
    RELIABILITY = "reliability"
    PREDICTABILITY = "predictability"
    TRANSPARENCY = "transparency"


class EvidenceType(Enum):
    """Trust evidence types."""
    DIRECT = "direct"
    INDIRECT = "indirect"
    REPUTATION = "reputation"
    CERTIFICATION = "certification"
    BEHAVIOR = "behavior"
    RECOMMENDATION = "recommendation"


class TrustEventType(Enum):
    """Trust event types."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    VIOLATION = "violation"
    FULFILLMENT = "fulfillment"


class PropagationType(Enum):
    """Trust propagation types."""
    DIRECT = "direct"
    TRANSITIVE = "transitive"
    AGGREGATE = "aggregate"


class TrustPolicy(Enum):
    """Trust policies."""
    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    NEUTRAL = "neutral"
    ADAPTIVE = "adaptive"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class TrustScore:
    """Trust score."""
    score_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    value: float = 0.5  # 0-1 scale
    confidence: float = 0.5
    dimension: Optional[TrustDimension] = None
    evidence_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class TrustEvidence:
    """Trust evidence."""
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    target: str = ""
    evidence_type: EvidenceType = EvidenceType.DIRECT
    value: float = 0.5  # -1 to 1 scale
    weight: float = 1.0
    dimension: Optional[TrustDimension] = None
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrustEvent:
    """Trust event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    target: str = ""
    event_type: TrustEventType = TrustEventType.NEUTRAL
    impact: float = 0.0
    context: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TrustRelationship:
    """Trust relationship between entities."""
    relationship_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trustor: str = ""  # Who is trusting
    trustee: str = ""  # Who is being trusted
    scores: Dict[TrustDimension, TrustScore] = field(default_factory=dict)
    overall_score: float = 0.5
    overall_confidence: float = 0.5
    level: TrustLevel = TrustLevel.MEDIUM
    evidence: List[TrustEvidence] = field(default_factory=list)
    history: List[TrustEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Entity:
    """Trusted entity."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: str = "agent"
    reputation: float = 0.5
    trust_as_trustor: List[str] = field(default_factory=list)
    trust_as_trustee: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TrustPath:
    """Path of trust between entities."""
    path: List[str] = field(default_factory=list)
    trust_values: List[float] = field(default_factory=list)
    combined_trust: float = 0.0
    confidence: float = 0.0


@dataclass
class TrustStats:
    """Trust manager statistics."""
    total_entities: int = 0
    total_relationships: int = 0
    total_evidence: int = 0
    total_events: int = 0
    trust_updates: int = 0


# =============================================================================
# TRUST CALCULATOR
# =============================================================================

class TrustCalculator:
    """Calculate trust scores."""

    def __init__(
        self,
        policy: TrustPolicy = TrustPolicy.NEUTRAL,
        decay_rate: float = 0.01
    ):
        self._policy = policy
        self._decay_rate = decay_rate

    def compute_from_evidence(
        self,
        evidence: List[TrustEvidence]
    ) -> TrustScore:
        """Compute trust score from evidence."""
        if not evidence:
            return TrustScore(value=self._get_default_trust())

        # Filter valid evidence
        now = datetime.now()
        valid_evidence = [
            e for e in evidence
            if e.expires_at is None or e.expires_at > now
        ]

        if not valid_evidence:
            return TrustScore(value=self._get_default_trust())

        # Weighted average
        total_weight = sum(e.weight for e in valid_evidence)
        if total_weight == 0:
            return TrustScore(value=self._get_default_trust())

        weighted_sum = sum(e.value * e.weight for e in valid_evidence)
        value = weighted_sum / total_weight

        # Normalize to 0-1
        value = (value + 1) / 2  # Convert from -1,1 to 0,1

        # Compute confidence
        confidence = min(1.0, len(valid_evidence) / 10)

        return TrustScore(
            value=max(0.0, min(1.0, value)),
            confidence=confidence,
            evidence_count=len(valid_evidence)
        )

    def combine_dimensions(
        self,
        dimension_scores: Dict[TrustDimension, TrustScore],
        weights: Optional[Dict[TrustDimension, float]] = None
    ) -> float:
        """Combine dimension scores into overall trust."""
        if not dimension_scores:
            return self._get_default_trust()

        # Default weights
        if weights is None:
            weights = {dim: 1.0 for dim in TrustDimension}

        total_weight = 0.0
        weighted_sum = 0.0

        for dim, score in dimension_scores.items():
            w = weights.get(dim, 1.0) * score.confidence
            total_weight += w
            weighted_sum += score.value * w

        if total_weight == 0:
            return self._get_default_trust()

        return weighted_sum / total_weight

    def apply_decay(
        self,
        score: TrustScore,
        hours_elapsed: float
    ) -> TrustScore:
        """Apply time-based decay to trust score."""
        decay_factor = math.exp(-self._decay_rate * hours_elapsed)
        default = self._get_default_trust()

        # Decay toward default
        new_value = default + (score.value - default) * decay_factor
        new_confidence = score.confidence * decay_factor

        return TrustScore(
            score_id=score.score_id,
            value=new_value,
            confidence=max(0.1, new_confidence),
            dimension=score.dimension,
            evidence_count=score.evidence_count,
            last_updated=datetime.now()
        )

    def _get_default_trust(self) -> float:
        """Get default trust based on policy."""
        defaults = {
            TrustPolicy.OPTIMISTIC: 0.7,
            TrustPolicy.PESSIMISTIC: 0.3,
            TrustPolicy.NEUTRAL: 0.5,
            TrustPolicy.ADAPTIVE: 0.5,
        }
        return defaults.get(self._policy, 0.5)

    def score_to_level(self, score: float) -> TrustLevel:
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
            return TrustLevel.FULLY_TRUSTED


# =============================================================================
# TRUST PROPAGATOR
# =============================================================================

class TrustPropagator:
    """Propagate trust through network."""

    def __init__(
        self,
        attenuation: float = 0.8,
        max_depth: int = 3
    ):
        self._attenuation = attenuation
        self._max_depth = max_depth

    def find_trust_paths(
        self,
        source: str,
        target: str,
        relationships: Dict[Tuple[str, str], TrustRelationship]
    ) -> List[TrustPath]:
        """Find all trust paths between entities."""
        paths = []

        def dfs(
            current: str,
            path: List[str],
            trust_values: List[float],
            visited: Set[str]
        ):
            if len(path) > self._max_depth + 1:
                return

            if current == target:
                # Compute combined trust
                combined = 1.0
                for i, t in enumerate(trust_values):
                    combined *= t * (self._attenuation ** i)

                paths.append(TrustPath(
                    path=path.copy(),
                    trust_values=trust_values.copy(),
                    combined_trust=combined,
                    confidence=min(trust_values) if trust_values else 0
                ))
                return

            for (trustor, trustee), rel in relationships.items():
                if trustor == current and trustee not in visited:
                    visited.add(trustee)
                    path.append(trustee)
                    trust_values.append(rel.overall_score)

                    dfs(trustee, path, trust_values, visited)

                    path.pop()
                    trust_values.pop()
                    visited.remove(trustee)

        visited = {source}
        dfs(source, [source], [], visited)

        # Sort by combined trust
        paths.sort(key=lambda p: p.combined_trust, reverse=True)

        return paths

    def compute_transitive_trust(
        self,
        paths: List[TrustPath]
    ) -> float:
        """Compute transitive trust from paths."""
        if not paths:
            return 0.0

        # Use maximum path trust
        return paths[0].combined_trust

    def propagate_event(
        self,
        event: TrustEvent,
        relationships: Dict[Tuple[str, str], TrustRelationship]
    ) -> Dict[Tuple[str, str], float]:
        """Propagate trust event through network."""
        impacts = {}

        # Direct impact
        key = (event.source, event.target)
        if key in relationships:
            impacts[key] = event.impact

        # Transitive impact (attenuated)
        for (trustor, trustee), rel in relationships.items():
            if trustee == event.source:
                # Impact flows backward
                attenuated = event.impact * self._attenuation
                impacts[(trustor, event.target)] = attenuated

        return impacts


# =============================================================================
# REPUTATION MANAGER
# =============================================================================

class ReputationManager:
    """Manage entity reputations."""

    def __init__(self):
        self._reputations: Dict[str, float] = {}
        self._reputation_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )

    def update_reputation(
        self,
        entity_id: str,
        relationships: List[TrustRelationship]
    ) -> float:
        """Update entity reputation from relationships."""
        if not relationships:
            return self._reputations.get(entity_id, 0.5)

        # Aggregate trust scores where entity is trustee
        scores = []
        for rel in relationships:
            if rel.trustee == entity_id:
                scores.append(rel.overall_score * rel.overall_confidence)

        if not scores:
            return self._reputations.get(entity_id, 0.5)

        reputation = sum(scores) / len(scores)

        old_reputation = self._reputations.get(entity_id, 0.5)
        # Smooth update
        new_reputation = old_reputation * 0.7 + reputation * 0.3

        self._reputations[entity_id] = new_reputation
        self._reputation_history[entity_id].append({
            "reputation": new_reputation,
            "timestamp": datetime.now()
        })

        return new_reputation

    def get_reputation(self, entity_id: str) -> float:
        """Get entity reputation."""
        return self._reputations.get(entity_id, 0.5)

    def get_reputation_history(
        self,
        entity_id: str
    ) -> List[Dict[str, Any]]:
        """Get reputation history."""
        return list(self._reputation_history.get(entity_id, []))

    def rank_entities(self) -> List[Tuple[str, float]]:
        """Rank entities by reputation."""
        return sorted(
            self._reputations.items(),
            key=lambda x: x[1],
            reverse=True
        )


# =============================================================================
# TRUST POLICY ENFORCER
# =============================================================================

class TrustPolicyEnforcer:
    """Enforce trust policies."""

    def __init__(self):
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._default_policy = {
            "min_trust": 0.3,
            "min_confidence": 0.2,
            "required_evidence": 1,
            "max_age_hours": 720,  # 30 days
        }

    def set_policy(
        self,
        policy_name: str,
        policy: Dict[str, Any]
    ) -> None:
        """Set policy."""
        self._policies[policy_name] = policy

    def get_policy(self, policy_name: str) -> Dict[str, Any]:
        """Get policy."""
        return self._policies.get(policy_name, self._default_policy)

    def check_trust(
        self,
        relationship: TrustRelationship,
        policy_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Check if relationship meets trust policy."""
        policy = self.get_policy(policy_name) if policy_name else self._default_policy

        # Check minimum trust
        if relationship.overall_score < policy.get("min_trust", 0.3):
            return False, f"Trust {relationship.overall_score:.2f} below minimum {policy.get('min_trust')}"

        # Check confidence
        if relationship.overall_confidence < policy.get("min_confidence", 0.2):
            return False, f"Confidence {relationship.overall_confidence:.2f} below minimum {policy.get('min_confidence')}"

        # Check evidence count
        if len(relationship.evidence) < policy.get("required_evidence", 1):
            return False, f"Evidence count {len(relationship.evidence)} below required {policy.get('required_evidence')}"

        # Check age
        max_age = policy.get("max_age_hours", 720)
        age_hours = (datetime.now() - relationship.updated_at).total_seconds() / 3600
        if age_hours > max_age:
            return False, f"Trust data age {age_hours:.1f}h exceeds maximum {max_age}h"

        return True, "Trust requirements met"

    def filter_trusted(
        self,
        relationships: List[TrustRelationship],
        policy_name: Optional[str] = None
    ) -> List[TrustRelationship]:
        """Filter relationships that meet policy."""
        return [
            rel for rel in relationships
            if self.check_trust(rel, policy_name)[0]
        ]


# =============================================================================
# TRUST MANAGER
# =============================================================================

class TrustManager:
    """
    Trust Manager for BAEL.

    Advanced trust modeling and reputation management.
    """

    def __init__(
        self,
        policy: TrustPolicy = TrustPolicy.NEUTRAL,
        decay_rate: float = 0.01
    ):
        self._calculator = TrustCalculator(policy, decay_rate)
        self._propagator = TrustPropagator()
        self._reputation_manager = ReputationManager()
        self._policy_enforcer = TrustPolicyEnforcer()

        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[Tuple[str, str], TrustRelationship] = {}
        self._evidence_store: List[TrustEvidence] = []
        self._event_log: deque = deque(maxlen=10000)
        self._stats = TrustStats()

    # -------------------------------------------------------------------------
    # ENTITY MANAGEMENT
    # -------------------------------------------------------------------------

    def register_entity(
        self,
        name: str,
        entity_type: str = "agent",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """Register new entity."""
        entity = Entity(
            name=name,
            entity_type=entity_type,
            metadata=metadata or {}
        )

        self._entities[entity.entity_id] = entity
        self._stats.total_entities += 1

        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def find_entity_by_name(self, name: str) -> Optional[Entity]:
        """Find entity by name."""
        for entity in self._entities.values():
            if entity.name == name:
                return entity
        return None

    def list_entities(self) -> List[Entity]:
        """List all entities."""
        return list(self._entities.values())

    # -------------------------------------------------------------------------
    # TRUST RELATIONSHIP MANAGEMENT
    # -------------------------------------------------------------------------

    def create_relationship(
        self,
        trustor_id: str,
        trustee_id: str,
        initial_trust: float = 0.5
    ) -> TrustRelationship:
        """Create trust relationship."""
        key = (trustor_id, trustee_id)

        if key in self._relationships:
            return self._relationships[key]

        relationship = TrustRelationship(
            trustor=trustor_id,
            trustee=trustee_id,
            overall_score=initial_trust,
            level=self._calculator.score_to_level(initial_trust)
        )

        self._relationships[key] = relationship
        self._stats.total_relationships += 1

        # Update entity references
        if trustor_id in self._entities:
            self._entities[trustor_id].trust_as_trustor.append(trustee_id)
        if trustee_id in self._entities:
            self._entities[trustee_id].trust_as_trustee.append(trustor_id)

        return relationship

    def get_relationship(
        self,
        trustor_id: str,
        trustee_id: str
    ) -> Optional[TrustRelationship]:
        """Get trust relationship."""
        return self._relationships.get((trustor_id, trustee_id))

    def get_trust(
        self,
        trustor_id: str,
        trustee_id: str
    ) -> float:
        """Get trust score between entities."""
        rel = self.get_relationship(trustor_id, trustee_id)
        if rel:
            return rel.overall_score

        # Try transitive trust
        paths = self._propagator.find_trust_paths(
            trustor_id,
            trustee_id,
            self._relationships
        )

        return self._propagator.compute_transitive_trust(paths)

    def get_trust_level(
        self,
        trustor_id: str,
        trustee_id: str
    ) -> TrustLevel:
        """Get trust level between entities."""
        trust = self.get_trust(trustor_id, trustee_id)
        return self._calculator.score_to_level(trust)

    # -------------------------------------------------------------------------
    # EVIDENCE MANAGEMENT
    # -------------------------------------------------------------------------

    def add_evidence(
        self,
        trustor_id: str,
        trustee_id: str,
        value: float,
        evidence_type: EvidenceType = EvidenceType.DIRECT,
        dimension: Optional[TrustDimension] = None,
        weight: float = 1.0,
        ttl_hours: Optional[float] = None
    ) -> TrustEvidence:
        """Add trust evidence."""
        expires_at = None
        if ttl_hours:
            expires_at = datetime.now() + timedelta(hours=ttl_hours)

        evidence = TrustEvidence(
            source=trustor_id,
            target=trustee_id,
            evidence_type=evidence_type,
            value=max(-1.0, min(1.0, value)),
            weight=weight,
            dimension=dimension,
            expires_at=expires_at
        )

        self._evidence_store.append(evidence)
        self._stats.total_evidence += 1

        # Update relationship
        self._update_relationship_from_evidence(trustor_id, trustee_id)

        return evidence

    def _update_relationship_from_evidence(
        self,
        trustor_id: str,
        trustee_id: str
    ) -> None:
        """Update relationship from all evidence."""
        key = (trustor_id, trustee_id)

        if key not in self._relationships:
            self.create_relationship(trustor_id, trustee_id)

        relationship = self._relationships[key]

        # Gather evidence
        evidence = [
            e for e in self._evidence_store
            if e.source == trustor_id and e.target == trustee_id
        ]

        relationship.evidence = evidence

        # Compute dimension scores
        dimension_evidence: Dict[TrustDimension, List[TrustEvidence]] = defaultdict(list)
        general_evidence = []

        for e in evidence:
            if e.dimension:
                dimension_evidence[e.dimension].append(e)
            else:
                general_evidence.append(e)

        # Update dimension scores
        for dim in TrustDimension:
            dim_evid = dimension_evidence.get(dim, []) + general_evidence
            if dim_evid:
                score = self._calculator.compute_from_evidence(dim_evid)
                score.dimension = dim
                relationship.scores[dim] = score

        # Update overall score
        if relationship.scores:
            relationship.overall_score = self._calculator.combine_dimensions(
                relationship.scores
            )
            relationship.overall_confidence = sum(
                s.confidence for s in relationship.scores.values()
            ) / len(relationship.scores)
        else:
            score = self._calculator.compute_from_evidence(general_evidence)
            relationship.overall_score = score.value
            relationship.overall_confidence = score.confidence

        relationship.level = self._calculator.score_to_level(relationship.overall_score)
        relationship.updated_at = datetime.now()
        self._stats.trust_updates += 1

    # -------------------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------------------

    def record_event(
        self,
        source: str,
        target: str,
        event_type: TrustEventType,
        impact: float,
        context: str = ""
    ) -> TrustEvent:
        """Record trust event."""
        event = TrustEvent(
            source=source,
            target=target,
            event_type=event_type,
            impact=max(-1.0, min(1.0, impact)),
            context=context
        )

        self._event_log.append(event)
        self._stats.total_events += 1

        # Convert event to evidence
        evidence_value = impact
        if event_type == TrustEventType.VIOLATION:
            evidence_value = -abs(impact)
        elif event_type == TrustEventType.FULFILLMENT:
            evidence_value = abs(impact)

        self.add_evidence(
            source,
            target,
            evidence_value,
            EvidenceType.BEHAVIOR,
            weight=0.5
        )

        # Propagate through network
        impacts = self._propagator.propagate_event(event, self._relationships)
        for (trustor, trustee), imp in impacts.items():
            if (trustor, trustee) != (source, target):
                self.add_evidence(trustor, trustee, imp * 0.5, EvidenceType.INDIRECT)

        return event

    def get_event_history(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        limit: int = 100
    ) -> List[TrustEvent]:
        """Get event history."""
        events = list(self._event_log)

        if source:
            events = [e for e in events if e.source == source]
        if target:
            events = [e for e in events if e.target == target]

        return events[-limit:]

    # -------------------------------------------------------------------------
    # TRUST PROPAGATION
    # -------------------------------------------------------------------------

    def find_trust_paths(
        self,
        source_id: str,
        target_id: str
    ) -> List[TrustPath]:
        """Find trust paths between entities."""
        return self._propagator.find_trust_paths(
            source_id,
            target_id,
            self._relationships
        )

    def compute_transitive_trust(
        self,
        source_id: str,
        target_id: str
    ) -> float:
        """Compute transitive trust."""
        paths = self.find_trust_paths(source_id, target_id)
        return self._propagator.compute_transitive_trust(paths)

    # -------------------------------------------------------------------------
    # REPUTATION
    # -------------------------------------------------------------------------

    def update_reputation(self, entity_id: str) -> float:
        """Update entity reputation."""
        relationships = [
            rel for rel in self._relationships.values()
            if rel.trustee == entity_id
        ]

        reputation = self._reputation_manager.update_reputation(
            entity_id,
            relationships
        )

        if entity_id in self._entities:
            self._entities[entity_id].reputation = reputation

        return reputation

    def update_all_reputations(self) -> Dict[str, float]:
        """Update all entity reputations."""
        reputations = {}
        for entity_id in self._entities:
            reputations[entity_id] = self.update_reputation(entity_id)
        return reputations

    def get_reputation(self, entity_id: str) -> float:
        """Get entity reputation."""
        return self._reputation_manager.get_reputation(entity_id)

    def rank_by_reputation(self) -> List[Tuple[str, float]]:
        """Rank entities by reputation."""
        return self._reputation_manager.rank_entities()

    # -------------------------------------------------------------------------
    # TRUST POLICIES
    # -------------------------------------------------------------------------

    def set_policy(
        self,
        policy_name: str,
        policy: Dict[str, Any]
    ) -> None:
        """Set trust policy."""
        self._policy_enforcer.set_policy(policy_name, policy)

    def check_trust_policy(
        self,
        trustor_id: str,
        trustee_id: str,
        policy_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Check if trust meets policy."""
        relationship = self.get_relationship(trustor_id, trustee_id)
        if not relationship:
            return False, "No trust relationship exists"

        return self._policy_enforcer.check_trust(relationship, policy_name)

    def get_trusted_entities(
        self,
        trustor_id: str,
        policy_name: Optional[str] = None
    ) -> List[str]:
        """Get entities that meet trust policy."""
        relationships = [
            rel for rel in self._relationships.values()
            if rel.trustor == trustor_id
        ]

        trusted = self._policy_enforcer.filter_trusted(relationships, policy_name)
        return [rel.trustee for rel in trusted]

    # -------------------------------------------------------------------------
    # TRUST DECAY
    # -------------------------------------------------------------------------

    def apply_decay(self, hours: float = 24.0) -> int:
        """Apply time-based trust decay."""
        count = 0

        for relationship in self._relationships.values():
            for dim, score in relationship.scores.items():
                relationship.scores[dim] = self._calculator.apply_decay(
                    score,
                    hours
                )
                count += 1

        return count

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def get_trust_network(self) -> Dict[str, Any]:
        """Get trust network summary."""
        nodes = [
            {
                "id": e.entity_id,
                "name": e.name,
                "reputation": e.reputation
            }
            for e in self._entities.values()
        ]

        edges = [
            {
                "source": rel.trustor,
                "target": rel.trustee,
                "trust": rel.overall_score,
                "level": rel.level.value
            }
            for rel in self._relationships.values()
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "entity_count": len(nodes),
            "relationship_count": len(edges)
        }

    def get_trust_summary(
        self,
        entity_id: str
    ) -> Dict[str, Any]:
        """Get trust summary for entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return {}

        # Trust given
        trust_given = [
            {
                "trustee": rel.trustee,
                "trust": rel.overall_score,
                "level": rel.level.value
            }
            for rel in self._relationships.values()
            if rel.trustor == entity_id
        ]

        # Trust received
        trust_received = [
            {
                "trustor": rel.trustor,
                "trust": rel.overall_score,
                "level": rel.level.value
            }
            for rel in self._relationships.values()
            if rel.trustee == entity_id
        ]

        return {
            "entity": entity.name,
            "reputation": entity.reputation,
            "trust_given": trust_given,
            "trust_received": trust_received,
            "avg_trust_given": sum(t["trust"] for t in trust_given) / len(trust_given) if trust_given else 0,
            "avg_trust_received": sum(t["trust"] for t in trust_received) / len(trust_received) if trust_received else 0
        }

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> TrustStats:
        """Get manager statistics."""
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Trust Manager."""
    print("=" * 70)
    print("BAEL - TRUST MANAGER DEMO")
    print("Advanced Trust Modeling and Reputation Management")
    print("=" * 70)
    print()

    manager = TrustManager()

    # 1. Register Entities
    print("1. REGISTER ENTITIES:")
    print("-" * 40)

    alice = manager.register_entity("Alice", "agent")
    bob = manager.register_entity("Bob", "agent")
    charlie = manager.register_entity("Charlie", "agent")
    diana = manager.register_entity("Diana", "agent")

    print(f"   Registered: {alice.name} ({alice.entity_id[:8]}...)")
    print(f"   Registered: {bob.name} ({bob.entity_id[:8]}...)")
    print(f"   Registered: {charlie.name} ({charlie.entity_id[:8]}...)")
    print(f"   Registered: {diana.name} ({diana.entity_id[:8]}...)")
    print()

    # 2. Create Relationships
    print("2. CREATE RELATIONSHIPS:")
    print("-" * 40)

    rel_ab = manager.create_relationship(alice.entity_id, bob.entity_id, 0.7)
    rel_bc = manager.create_relationship(bob.entity_id, charlie.entity_id, 0.8)
    rel_cd = manager.create_relationship(charlie.entity_id, diana.entity_id, 0.6)

    print(f"   {alice.name} -> {bob.name}: {rel_ab.overall_score:.2f}")
    print(f"   {bob.name} -> {charlie.name}: {rel_bc.overall_score:.2f}")
    print(f"   {charlie.name} -> {diana.name}: {rel_cd.overall_score:.2f}")
    print()

    # 3. Add Evidence
    print("3. ADD TRUST EVIDENCE:")
    print("-" * 40)

    manager.add_evidence(
        alice.entity_id,
        bob.entity_id,
        0.8,
        EvidenceType.DIRECT,
        TrustDimension.COMPETENCE
    )

    manager.add_evidence(
        alice.entity_id,
        bob.entity_id,
        0.9,
        EvidenceType.BEHAVIOR,
        TrustDimension.RELIABILITY
    )

    manager.add_evidence(
        alice.entity_id,
        bob.entity_id,
        0.6,
        EvidenceType.REPUTATION,
        TrustDimension.INTEGRITY
    )

    rel = manager.get_relationship(alice.entity_id, bob.entity_id)
    print(f"   Added 3 evidence items for {alice.name} -> {bob.name}")
    print(f"   Updated trust: {rel.overall_score:.3f}")
    print(f"   Confidence: {rel.overall_confidence:.3f}")
    print()

    # 4. Get Trust Scores
    print("4. GET TRUST SCORES:")
    print("-" * 40)

    trust = manager.get_trust(alice.entity_id, bob.entity_id)
    level = manager.get_trust_level(alice.entity_id, bob.entity_id)

    print(f"   {alice.name} -> {bob.name}: {trust:.3f} ({level.value})")
    print()

    # 5. Dimension Scores
    print("5. DIMENSION SCORES:")
    print("-" * 40)

    rel = manager.get_relationship(alice.entity_id, bob.entity_id)
    for dim, score in rel.scores.items():
        print(f"   {dim.value}: {score.value:.3f} (conf: {score.confidence:.2f})")
    print()

    # 6. Record Trust Events
    print("6. RECORD TRUST EVENTS:")
    print("-" * 40)

    event1 = manager.record_event(
        bob.entity_id,
        charlie.entity_id,
        TrustEventType.FULFILLMENT,
        0.3,
        "Completed task successfully"
    )

    event2 = manager.record_event(
        charlie.entity_id,
        diana.entity_id,
        TrustEventType.VIOLATION,
        -0.2,
        "Missed deadline"
    )

    print(f"   Event: {event1.event_type.value} ({event1.impact:+.2f})")
    print(f"   Event: {event2.event_type.value} ({event2.impact:+.2f})")
    print()

    # 7. Transitive Trust
    print("7. TRANSITIVE TRUST:")
    print("-" * 40)

    trans_trust = manager.compute_transitive_trust(
        alice.entity_id,
        diana.entity_id
    )
    print(f"   {alice.name} -> {diana.name} (transitive): {trans_trust:.3f}")

    paths = manager.find_trust_paths(alice.entity_id, diana.entity_id)
    if paths:
        path = paths[0]
        entities = [manager.get_entity(eid).name for eid in path.path]
        print(f"   Path: {' -> '.join(entities)}")
    print()

    # 8. Update Reputations
    print("8. UPDATE REPUTATIONS:")
    print("-" * 40)

    reputations = manager.update_all_reputations()
    for entity_id, rep in reputations.items():
        entity = manager.get_entity(entity_id)
        print(f"   {entity.name}: {rep:.3f}")
    print()

    # 9. Rank by Reputation
    print("9. RANK BY REPUTATION:")
    print("-" * 40)

    rankings = manager.rank_by_reputation()
    for rank, (entity_id, rep) in enumerate(rankings, 1):
        entity = manager.get_entity(entity_id)
        if entity:
            print(f"   {rank}. {entity.name}: {rep:.3f}")
    print()

    # 10. Trust Policies
    print("10. TRUST POLICIES:")
    print("-" * 40)

    manager.set_policy("strict", {
        "min_trust": 0.7,
        "min_confidence": 0.5,
        "required_evidence": 2
    })

    passes, reason = manager.check_trust_policy(
        alice.entity_id,
        bob.entity_id,
        "strict"
    )
    print(f"   Strict policy check: {'PASS' if passes else 'FAIL'}")
    print(f"   Reason: {reason}")
    print()

    # 11. Get Trusted Entities
    print("11. GET TRUSTED ENTITIES:")
    print("-" * 40)

    trusted = manager.get_trusted_entities(alice.entity_id)
    print(f"   Trusted by {alice.name}:")
    for tid in trusted:
        entity = manager.get_entity(tid)
        if entity:
            print(f"     - {entity.name}")
    print()

    # 12. Trust Network
    print("12. TRUST NETWORK:")
    print("-" * 40)

    network = manager.get_trust_network()
    print(f"   Nodes: {network['entity_count']}")
    print(f"   Edges: {network['relationship_count']}")
    print()

    # 13. Trust Summary
    print("13. TRUST SUMMARY:")
    print("-" * 40)

    summary = manager.get_trust_summary(bob.entity_id)
    print(f"   Entity: {summary['entity']}")
    print(f"   Reputation: {summary['reputation']:.3f}")
    print(f"   Avg trust given: {summary['avg_trust_given']:.3f}")
    print(f"   Avg trust received: {summary['avg_trust_received']:.3f}")
    print()

    # 14. Apply Decay
    print("14. APPLY DECAY:")
    print("-" * 40)

    trust_before = manager.get_trust(alice.entity_id, bob.entity_id)
    decayed = manager.apply_decay(hours=168)  # 1 week
    trust_after = manager.get_trust(alice.entity_id, bob.entity_id)

    print(f"   Decayed {decayed} scores")
    print(f"   Trust before: {trust_before:.3f}")
    print(f"   Trust after: {trust_after:.3f}")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()
    print(f"   Total entities: {stats.total_entities}")
    print(f"   Total relationships: {stats.total_relationships}")
    print(f"   Total evidence: {stats.total_evidence}")
    print(f"   Total events: {stats.total_events}")
    print(f"   Trust updates: {stats.trust_updates}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Trust Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
