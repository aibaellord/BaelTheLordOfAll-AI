#!/usr/bin/env python3
"""
BAEL - Social Manager
Advanced social intelligence and relationship management system.

Features:
- Relationship modeling
- Social network analysis
- Reputation tracking
- Influence mapping
- Social dynamics simulation
- Communication adaptation
- Group dynamics
- Social norms enforcement
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

class RelationshipType(Enum):
    """Types of relationships."""
    PEER = "peer"
    MENTOR = "mentor"
    MENTEE = "mentee"
    COLLABORATOR = "collaborator"
    COMPETITOR = "competitor"
    AUTHORITY = "authority"
    SUBORDINATE = "subordinate"
    FRIEND = "friend"
    ACQUAINTANCE = "acquaintance"


class RelationshipStrength(Enum):
    """Strength of relationships."""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class SocialRole(Enum):
    """Social roles."""
    LEADER = "leader"
    FOLLOWER = "follower"
    MEDIATOR = "mediator"
    INNOVATOR = "innovator"
    CONNECTOR = "connector"
    EXPERT = "expert"
    OBSERVER = "observer"


class InteractionType(Enum):
    """Types of social interactions."""
    COOPERATION = "cooperation"
    COMPETITION = "competition"
    NEGOTIATION = "negotiation"
    CONFLICT = "conflict"
    SUPPORT = "support"
    INFORMATION_SHARING = "information_sharing"
    CASUAL = "casual"


class SocialNormType(Enum):
    """Types of social norms."""
    RECIPROCITY = "reciprocity"
    FAIRNESS = "fairness"
    COOPERATION = "cooperation"
    HONESTY = "honesty"
    RESPECT = "respect"
    PUNCTUALITY = "punctuality"


class InfluenceType(Enum):
    """Types of influence."""
    INFORMATIONAL = "informational"
    NORMATIVE = "normative"
    REFERENT = "referent"
    EXPERT = "expert"
    LEGITIMATE = "legitimate"
    REWARD = "reward"
    COERCIVE = "coercive"


class GroupRole(Enum):
    """Roles in a group."""
    LEADER = "leader"
    MEMBER = "member"
    MODERATOR = "moderator"
    OBSERVER = "observer"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SocialEntity:
    """A social entity (agent, person, etc.)."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: str = "agent"
    attributes: Dict[str, Any] = field(default_factory=dict)
    roles: Set[SocialRole] = field(default_factory=set)
    reputation: float = 0.5
    influence: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Relationship:
    """Relationship between entities."""
    relationship_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_a: str = ""
    entity_b: str = ""
    relationship_type: RelationshipType = RelationshipType.ACQUAINTANCE
    strength: float = 0.5  # 0-1
    trust: float = 0.5
    sentiment: float = 0.0  # -1 to 1
    interaction_count: int = 0
    last_interaction: datetime = field(default_factory=datetime.now)
    history: List[str] = field(default_factory=list)


@dataclass
class SocialInteraction:
    """Record of social interaction."""
    interaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    participants: List[str] = field(default_factory=list)
    interaction_type: InteractionType = InteractionType.CASUAL
    outcome: str = ""
    sentiment: float = 0.0
    impact: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SocialGroup:
    """Social group."""
    group_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    members: Dict[str, GroupRole] = field(default_factory=dict)
    norms: List[SocialNormType] = field(default_factory=list)
    cohesion: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SocialNorm:
    """Social norm."""
    norm_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    norm_type: SocialNormType = SocialNormType.RECIPROCITY
    description: str = ""
    importance: float = 0.5
    enforcement_level: float = 0.5
    violations: List[Tuple[str, datetime]] = field(default_factory=list)


@dataclass
class InfluenceEdge:
    """Influence relationship."""
    source: str = ""
    target: str = ""
    influence_type: InfluenceType = InfluenceType.INFORMATIONAL
    strength: float = 0.5
    is_bidirectional: bool = False


@dataclass
class SocialMetrics:
    """Social metrics for an entity."""
    entity_id: str = ""
    centrality: float = 0.0
    betweenness: float = 0.0
    closeness: float = 0.0
    degree: int = 0
    influence_score: float = 0.0
    reputation_score: float = 0.5


# =============================================================================
# RELATIONSHIP MANAGER
# =============================================================================

class RelationshipManager:
    """Manage relationships between entities."""

    def __init__(self):
        self._relationships: Dict[str, Relationship] = {}
        self._entity_relationships: Dict[str, Set[str]] = defaultdict(set)

    def add_relationship(
        self,
        entity_a: str,
        entity_b: str,
        relationship_type: RelationshipType = RelationshipType.ACQUAINTANCE,
        strength: float = 0.5,
        trust: float = 0.5
    ) -> Relationship:
        """Add relationship between entities."""
        rel_key = self._get_key(entity_a, entity_b)

        relationship = Relationship(
            entity_a=entity_a,
            entity_b=entity_b,
            relationship_type=relationship_type,
            strength=strength,
            trust=trust
        )

        self._relationships[rel_key] = relationship
        self._entity_relationships[entity_a].add(rel_key)
        self._entity_relationships[entity_b].add(rel_key)

        return relationship

    def _get_key(self, entity_a: str, entity_b: str) -> str:
        """Get consistent key for entity pair."""
        return f"{min(entity_a, entity_b)}:{max(entity_a, entity_b)}"

    def get_relationship(
        self,
        entity_a: str,
        entity_b: str
    ) -> Optional[Relationship]:
        """Get relationship between entities."""
        key = self._get_key(entity_a, entity_b)
        return self._relationships.get(key)

    def update_relationship(
        self,
        entity_a: str,
        entity_b: str,
        strength_delta: float = 0.0,
        trust_delta: float = 0.0,
        sentiment_delta: float = 0.0
    ) -> Optional[Relationship]:
        """Update relationship."""
        rel = self.get_relationship(entity_a, entity_b)
        if rel:
            rel.strength = max(0.0, min(1.0, rel.strength + strength_delta))
            rel.trust = max(0.0, min(1.0, rel.trust + trust_delta))
            rel.sentiment = max(-1.0, min(1.0, rel.sentiment + sentiment_delta))
            rel.interaction_count += 1
            rel.last_interaction = datetime.now()
            return rel
        return None

    def record_interaction(
        self,
        entity_a: str,
        entity_b: str,
        outcome: str
    ) -> None:
        """Record an interaction."""
        rel = self.get_relationship(entity_a, entity_b)
        if rel:
            rel.history.append(f"{datetime.now().isoformat()}: {outcome}")

    def get_entity_relationships(
        self,
        entity_id: str
    ) -> List[Relationship]:
        """Get all relationships for an entity."""
        rel_keys = self._entity_relationships.get(entity_id, set())
        return [
            self._relationships[key]
            for key in rel_keys
            if key in self._relationships
        ]

    def get_relationship_strength_category(
        self,
        entity_a: str,
        entity_b: str
    ) -> RelationshipStrength:
        """Get relationship strength category."""
        rel = self.get_relationship(entity_a, entity_b)
        if not rel:
            return RelationshipStrength.VERY_WEAK

        if rel.strength < 0.2:
            return RelationshipStrength.VERY_WEAK
        elif rel.strength < 0.4:
            return RelationshipStrength.WEAK
        elif rel.strength < 0.6:
            return RelationshipStrength.MODERATE
        elif rel.strength < 0.8:
            return RelationshipStrength.STRONG
        else:
            return RelationshipStrength.VERY_STRONG


# =============================================================================
# SOCIAL NETWORK ANALYZER
# =============================================================================

class SocialNetworkAnalyzer:
    """Analyze social network structure."""

    def __init__(self, relationship_manager: RelationshipManager):
        self._relationship_manager = relationship_manager
        self._entities: Set[str] = set()

    def register_entity(self, entity_id: str) -> None:
        """Register an entity in the network."""
        self._entities.add(entity_id)

    def build_adjacency_matrix(self) -> Dict[str, Dict[str, float]]:
        """Build adjacency matrix of the network."""
        matrix: Dict[str, Dict[str, float]] = defaultdict(dict)

        for entity in self._entities:
            rels = self._relationship_manager.get_entity_relationships(entity)
            for rel in rels:
                other = rel.entity_b if rel.entity_a == entity else rel.entity_a
                matrix[entity][other] = rel.strength

        return dict(matrix)

    def compute_degree(self, entity_id: str) -> int:
        """Compute degree centrality."""
        rels = self._relationship_manager.get_entity_relationships(entity_id)
        return len(rels)

    def compute_centrality(self, entity_id: str) -> float:
        """Compute normalized degree centrality."""
        degree = self.compute_degree(entity_id)
        n = len(self._entities)
        if n <= 1:
            return 0.0
        return degree / (n - 1)

    def compute_closeness(self, entity_id: str) -> float:
        """Compute closeness centrality (simplified)."""
        if entity_id not in self._entities:
            return 0.0

        # Simple approximation using direct connections
        rels = self._relationship_manager.get_entity_relationships(entity_id)

        if not rels:
            return 0.0

        total_strength = sum(rel.strength for rel in rels)
        return total_strength / len(rels)

    def compute_betweenness(self, entity_id: str) -> float:
        """Compute betweenness centrality (simplified)."""
        if entity_id not in self._entities:
            return 0.0

        # Simple heuristic based on unique connections
        rels = self._relationship_manager.get_entity_relationships(entity_id)

        connected_entities = set()
        for rel in rels:
            other = rel.entity_b if rel.entity_a == entity_id else rel.entity_a
            connected_entities.add(other)

        # Count pairs that could be connected through this entity
        n_connections = len(connected_entities)
        potential_pairs = n_connections * (n_connections - 1) / 2

        total_pairs = len(self._entities) * (len(self._entities) - 1) / 2

        if total_pairs == 0:
            return 0.0

        return potential_pairs / total_pairs

    def compute_metrics(self, entity_id: str) -> SocialMetrics:
        """Compute all social metrics for an entity."""
        return SocialMetrics(
            entity_id=entity_id,
            centrality=self.compute_centrality(entity_id),
            betweenness=self.compute_betweenness(entity_id),
            closeness=self.compute_closeness(entity_id),
            degree=self.compute_degree(entity_id)
        )

    def find_clusters(self) -> List[Set[str]]:
        """Find clusters in the network."""
        visited: Set[str] = set()
        clusters: List[Set[str]] = []

        for entity in self._entities:
            if entity in visited:
                continue

            # BFS to find connected component
            cluster: Set[str] = set()
            queue = [entity]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue

                visited.add(current)
                cluster.add(current)

                rels = self._relationship_manager.get_entity_relationships(current)
                for rel in rels:
                    other = rel.entity_b if rel.entity_a == current else rel.entity_a
                    if other not in visited:
                        queue.append(other)

            if cluster:
                clusters.append(cluster)

        return clusters


# =============================================================================
# REPUTATION SYSTEM
# =============================================================================

class ReputationSystem:
    """Track and manage reputation."""

    def __init__(self):
        self._reputations: Dict[str, float] = {}
        self._reputation_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self._feedback: Dict[str, List[Tuple[str, float, str]]] = defaultdict(list)

    def get_reputation(self, entity_id: str) -> float:
        """Get entity reputation."""
        return self._reputations.get(entity_id, 0.5)

    def set_reputation(self, entity_id: str, reputation: float) -> None:
        """Set entity reputation."""
        reputation = max(0.0, min(1.0, reputation))
        self._reputations[entity_id] = reputation
        self._reputation_history[entity_id].append((datetime.now(), reputation))

    def update_reputation(
        self,
        entity_id: str,
        delta: float,
        reason: str = ""
    ) -> float:
        """Update entity reputation."""
        current = self.get_reputation(entity_id)
        new_reputation = max(0.0, min(1.0, current + delta))

        self._reputations[entity_id] = new_reputation
        self._reputation_history[entity_id].append((datetime.now(), new_reputation))

        return new_reputation

    def add_feedback(
        self,
        entity_id: str,
        from_entity: str,
        score: float,
        comment: str = ""
    ) -> None:
        """Add reputation feedback."""
        self._feedback[entity_id].append((from_entity, score, comment))

        # Update reputation based on feedback
        feedbacks = self._feedback[entity_id]
        if feedbacks:
            avg_score = sum(f[1] for f in feedbacks) / len(feedbacks)
            current = self.get_reputation(entity_id)
            # Smooth update
            new_rep = current * 0.7 + avg_score * 0.3
            self.set_reputation(entity_id, new_rep)

    def get_reputation_history(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[Tuple[datetime, float]]:
        """Get reputation history."""
        history = self._reputation_history.get(entity_id, [])
        return history[-limit:]

    def get_top_entities(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top entities by reputation."""
        sorted_entities = sorted(
            self._reputations.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_entities[:n]


# =============================================================================
# INFLUENCE MAPPER
# =============================================================================

class InfluenceMapper:
    """Map and analyze influence relationships."""

    def __init__(self):
        self._influence_edges: List[InfluenceEdge] = []
        self._entity_influence: Dict[str, float] = {}

    def add_influence(
        self,
        source: str,
        target: str,
        influence_type: InfluenceType,
        strength: float,
        is_bidirectional: bool = False
    ) -> InfluenceEdge:
        """Add influence relationship."""
        edge = InfluenceEdge(
            source=source,
            target=target,
            influence_type=influence_type,
            strength=strength,
            is_bidirectional=is_bidirectional
        )

        self._influence_edges.append(edge)
        return edge

    def get_influences_from(self, entity_id: str) -> List[InfluenceEdge]:
        """Get outgoing influences from entity."""
        return [
            edge for edge in self._influence_edges
            if edge.source == entity_id or (edge.is_bidirectional and edge.target == entity_id)
        ]

    def get_influences_to(self, entity_id: str) -> List[InfluenceEdge]:
        """Get incoming influences to entity."""
        return [
            edge for edge in self._influence_edges
            if edge.target == entity_id or (edge.is_bidirectional and edge.source == entity_id)
        ]

    def compute_influence_score(self, entity_id: str) -> float:
        """Compute overall influence score."""
        outgoing = self.get_influences_from(entity_id)

        if not outgoing:
            return 0.0

        total_strength = sum(edge.strength for edge in outgoing)
        return min(1.0, total_strength / len(outgoing))

    def compute_susceptibility(self, entity_id: str) -> float:
        """Compute how susceptible an entity is to influence."""
        incoming = self.get_influences_to(entity_id)

        if not incoming:
            return 0.0

        total_strength = sum(edge.strength for edge in incoming)
        return min(1.0, total_strength / len(incoming))

    def find_influence_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5
    ) -> List[str]:
        """Find influence path from source to target."""
        visited: Set[str] = set()
        queue: List[Tuple[str, List[str]]] = [(source, [source])]

        while queue and len(visited) < max_depth * 100:
            current, path = queue.pop(0)

            if current == target:
                return path

            if current in visited:
                continue

            visited.add(current)

            for edge in self.get_influences_from(current):
                next_entity = edge.target if edge.source == current else edge.source
                if next_entity not in visited:
                    queue.append((next_entity, path + [next_entity]))

        return []


# =============================================================================
# GROUP DYNAMICS
# =============================================================================

class GroupDynamics:
    """Manage group dynamics."""

    def __init__(self):
        self._groups: Dict[str, SocialGroup] = {}

    def create_group(
        self,
        name: str,
        description: str = "",
        norms: Optional[List[SocialNormType]] = None
    ) -> SocialGroup:
        """Create a social group."""
        group = SocialGroup(
            name=name,
            description=description,
            norms=norms or [SocialNormType.COOPERATION, SocialNormType.RESPECT]
        )

        self._groups[group.group_id] = group
        return group

    def get_group(self, group_id: str) -> Optional[SocialGroup]:
        """Get group by ID."""
        return self._groups.get(group_id)

    def add_member(
        self,
        group_id: str,
        entity_id: str,
        role: GroupRole = GroupRole.MEMBER
    ) -> bool:
        """Add member to group."""
        group = self._groups.get(group_id)
        if group:
            group.members[entity_id] = role
            return True
        return False

    def remove_member(
        self,
        group_id: str,
        entity_id: str
    ) -> bool:
        """Remove member from group."""
        group = self._groups.get(group_id)
        if group and entity_id in group.members:
            del group.members[entity_id]
            return True
        return False

    def get_member_role(
        self,
        group_id: str,
        entity_id: str
    ) -> Optional[GroupRole]:
        """Get member's role in group."""
        group = self._groups.get(group_id)
        if group:
            return group.members.get(entity_id)
        return None

    def compute_cohesion(self, group_id: str) -> float:
        """Compute group cohesion."""
        group = self._groups.get(group_id)
        if not group or len(group.members) < 2:
            return 0.0

        # Simple cohesion based on member count and norm compliance
        member_factor = min(1.0, len(group.members) / 10)
        norm_factor = len(group.norms) / len(SocialNormType)

        cohesion = member_factor * 0.5 + norm_factor * 0.5
        group.cohesion = cohesion

        return cohesion

    def get_group_leaders(
        self,
        group_id: str
    ) -> List[str]:
        """Get group leaders."""
        group = self._groups.get(group_id)
        if not group:
            return []

        return [
            entity_id
            for entity_id, role in group.members.items()
            if role == GroupRole.LEADER
        ]


# =============================================================================
# NORM ENFORCER
# =============================================================================

class NormEnforcer:
    """Enforce social norms."""

    def __init__(self):
        self._norms: Dict[str, SocialNorm] = {}
        self._violations: List[Tuple[str, str, datetime, str]] = []

    def register_norm(
        self,
        norm_type: SocialNormType,
        description: str,
        importance: float = 0.5,
        enforcement_level: float = 0.5
    ) -> SocialNorm:
        """Register a social norm."""
        norm = SocialNorm(
            norm_type=norm_type,
            description=description,
            importance=importance,
            enforcement_level=enforcement_level
        )

        self._norms[norm.norm_id] = norm
        return norm

    def check_violation(
        self,
        entity_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> List[Tuple[SocialNorm, float]]:
        """Check if action violates norms."""
        violations = []

        for norm in self._norms.values():
            severity = self._assess_violation(norm, action, context)
            if severity > 0:
                violations.append((norm, severity))
                norm.violations.append((entity_id, datetime.now()))

        return violations

    def _assess_violation(
        self,
        norm: SocialNorm,
        action: str,
        context: Dict[str, Any]
    ) -> float:
        """Assess violation severity."""
        action_lower = action.lower()

        # Simple rule-based violation detection
        violation_keywords = {
            SocialNormType.HONESTY: ["lie", "deceive", "mislead"],
            SocialNormType.COOPERATION: ["refuse", "obstruct", "sabotage"],
            SocialNormType.RECIPROCITY: ["take_without_giving", "free_ride"],
            SocialNormType.RESPECT: ["insult", "disrespect", "demean"],
            SocialNormType.FAIRNESS: ["cheat", "unfair", "bias"],
            SocialNormType.PUNCTUALITY: ["late", "delay", "miss"],
        }

        keywords = violation_keywords.get(norm.norm_type, [])

        for keyword in keywords:
            if keyword in action_lower:
                return norm.importance * norm.enforcement_level

        return 0.0

    def record_violation(
        self,
        entity_id: str,
        norm_id: str,
        details: str
    ) -> None:
        """Record a norm violation."""
        self._violations.append((entity_id, norm_id, datetime.now(), details))

    def get_entity_violations(
        self,
        entity_id: str
    ) -> List[Tuple[str, datetime, str]]:
        """Get violations by entity."""
        return [
            (norm_id, time, details)
            for eid, norm_id, time, details in self._violations
            if eid == entity_id
        ]


# =============================================================================
# SOCIAL MANAGER
# =============================================================================

class SocialManager:
    """
    Social Manager for BAEL.

    Advanced social intelligence and relationship management system.
    """

    def __init__(self):
        self._entities: Dict[str, SocialEntity] = {}
        self._relationship_manager = RelationshipManager()
        self._network_analyzer = SocialNetworkAnalyzer(self._relationship_manager)
        self._reputation_system = ReputationSystem()
        self._influence_mapper = InfluenceMapper()
        self._group_dynamics = GroupDynamics()
        self._norm_enforcer = NormEnforcer()

        self._interactions: List[SocialInteraction] = []

    # -------------------------------------------------------------------------
    # ENTITY MANAGEMENT
    # -------------------------------------------------------------------------

    def register_entity(
        self,
        name: str,
        entity_type: str = "agent",
        attributes: Optional[Dict[str, Any]] = None,
        roles: Optional[Set[SocialRole]] = None
    ) -> SocialEntity:
        """Register a social entity."""
        entity = SocialEntity(
            name=name,
            entity_type=entity_type,
            attributes=attributes or {},
            roles=roles or set()
        )

        self._entities[entity.entity_id] = entity
        self._network_analyzer.register_entity(entity.entity_id)

        return entity

    def get_entity(self, entity_id: str) -> Optional[SocialEntity]:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def update_entity_roles(
        self,
        entity_id: str,
        roles: Set[SocialRole]
    ) -> bool:
        """Update entity roles."""
        entity = self._entities.get(entity_id)
        if entity:
            entity.roles = roles
            return True
        return False

    # -------------------------------------------------------------------------
    # RELATIONSHIP MANAGEMENT
    # -------------------------------------------------------------------------

    def create_relationship(
        self,
        entity_a: str,
        entity_b: str,
        relationship_type: RelationshipType = RelationshipType.ACQUAINTANCE,
        strength: float = 0.5,
        trust: float = 0.5
    ) -> Relationship:
        """Create relationship between entities."""
        return self._relationship_manager.add_relationship(
            entity_a,
            entity_b,
            relationship_type,
            strength,
            trust
        )

    def get_relationship(
        self,
        entity_a: str,
        entity_b: str
    ) -> Optional[Relationship]:
        """Get relationship between entities."""
        return self._relationship_manager.get_relationship(entity_a, entity_b)

    def update_relationship(
        self,
        entity_a: str,
        entity_b: str,
        strength_delta: float = 0.0,
        trust_delta: float = 0.0,
        sentiment_delta: float = 0.0
    ) -> Optional[Relationship]:
        """Update relationship."""
        return self._relationship_manager.update_relationship(
            entity_a,
            entity_b,
            strength_delta,
            trust_delta,
            sentiment_delta
        )

    def get_entity_relationships(
        self,
        entity_id: str
    ) -> List[Relationship]:
        """Get all relationships for entity."""
        return self._relationship_manager.get_entity_relationships(entity_id)

    # -------------------------------------------------------------------------
    # SOCIAL INTERACTIONS
    # -------------------------------------------------------------------------

    def record_interaction(
        self,
        participants: List[str],
        interaction_type: InteractionType,
        outcome: str,
        sentiment: float = 0.0
    ) -> SocialInteraction:
        """Record a social interaction."""
        interaction = SocialInteraction(
            participants=participants,
            interaction_type=interaction_type,
            outcome=outcome,
            sentiment=sentiment
        )

        self._interactions.append(interaction)

        # Update relationships based on interaction
        for i, p1 in enumerate(participants):
            for p2 in participants[i+1:]:
                self._relationship_manager.update_relationship(
                    p1, p2,
                    strength_delta=0.05,
                    sentiment_delta=sentiment * 0.1
                )
                self._relationship_manager.record_interaction(p1, p2, outcome)

        return interaction

    def get_interactions(
        self,
        entity_id: Optional[str] = None,
        interaction_type: Optional[InteractionType] = None,
        limit: int = 50
    ) -> List[SocialInteraction]:
        """Get interactions with optional filters."""
        interactions = self._interactions

        if entity_id:
            interactions = [
                i for i in interactions
                if entity_id in i.participants
            ]

        if interaction_type:
            interactions = [
                i for i in interactions
                if i.interaction_type == interaction_type
            ]

        return interactions[-limit:]

    # -------------------------------------------------------------------------
    # NETWORK ANALYSIS
    # -------------------------------------------------------------------------

    def compute_social_metrics(
        self,
        entity_id: str
    ) -> SocialMetrics:
        """Compute social metrics for entity."""
        return self._network_analyzer.compute_metrics(entity_id)

    def find_clusters(self) -> List[Set[str]]:
        """Find social clusters."""
        return self._network_analyzer.find_clusters()

    def get_network_overview(self) -> Dict[str, Any]:
        """Get network overview."""
        return {
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationship_manager._relationships),
            "clusters": len(self.find_clusters())
        }

    # -------------------------------------------------------------------------
    # REPUTATION
    # -------------------------------------------------------------------------

    def get_reputation(self, entity_id: str) -> float:
        """Get entity reputation."""
        return self._reputation_system.get_reputation(entity_id)

    def update_reputation(
        self,
        entity_id: str,
        delta: float,
        reason: str = ""
    ) -> float:
        """Update entity reputation."""
        return self._reputation_system.update_reputation(entity_id, delta, reason)

    def add_reputation_feedback(
        self,
        entity_id: str,
        from_entity: str,
        score: float,
        comment: str = ""
    ) -> None:
        """Add reputation feedback."""
        self._reputation_system.add_feedback(entity_id, from_entity, score, comment)

    def get_top_reputed_entities(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top entities by reputation."""
        return self._reputation_system.get_top_entities(n)

    # -------------------------------------------------------------------------
    # INFLUENCE
    # -------------------------------------------------------------------------

    def add_influence(
        self,
        source: str,
        target: str,
        influence_type: InfluenceType,
        strength: float
    ) -> InfluenceEdge:
        """Add influence relationship."""
        return self._influence_mapper.add_influence(
            source, target, influence_type, strength
        )

    def get_influence_score(self, entity_id: str) -> float:
        """Get entity influence score."""
        return self._influence_mapper.compute_influence_score(entity_id)

    def find_influence_path(
        self,
        source: str,
        target: str
    ) -> List[str]:
        """Find influence path."""
        return self._influence_mapper.find_influence_path(source, target)

    # -------------------------------------------------------------------------
    # GROUP MANAGEMENT
    # -------------------------------------------------------------------------

    def create_group(
        self,
        name: str,
        description: str = "",
        norms: Optional[List[SocialNormType]] = None
    ) -> SocialGroup:
        """Create a social group."""
        return self._group_dynamics.create_group(name, description, norms)

    def get_group(self, group_id: str) -> Optional[SocialGroup]:
        """Get group by ID."""
        return self._group_dynamics.get_group(group_id)

    def add_to_group(
        self,
        group_id: str,
        entity_id: str,
        role: GroupRole = GroupRole.MEMBER
    ) -> bool:
        """Add entity to group."""
        return self._group_dynamics.add_member(group_id, entity_id, role)

    def get_group_cohesion(self, group_id: str) -> float:
        """Get group cohesion."""
        return self._group_dynamics.compute_cohesion(group_id)

    # -------------------------------------------------------------------------
    # NORM ENFORCEMENT
    # -------------------------------------------------------------------------

    def register_norm(
        self,
        norm_type: SocialNormType,
        description: str,
        importance: float = 0.5
    ) -> SocialNorm:
        """Register a social norm."""
        return self._norm_enforcer.register_norm(
            norm_type, description, importance
        )

    def check_norm_violations(
        self,
        entity_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[SocialNorm, float]]:
        """Check for norm violations."""
        return self._norm_enforcer.check_violation(
            entity_id, action, context or {}
        )

    def get_entity_violations(
        self,
        entity_id: str
    ) -> List[Tuple[str, datetime, str]]:
        """Get norm violations by entity."""
        return self._norm_enforcer.get_entity_violations(entity_id)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Social Manager."""
    print("=" * 70)
    print("BAEL - SOCIAL MANAGER DEMO")
    print("Advanced Social Intelligence and Relationship Management")
    print("=" * 70)
    print()

    manager = SocialManager()

    # 1. Register Entities
    print("1. REGISTER ENTITIES:")
    print("-" * 40)

    alice = manager.register_entity(
        name="Alice",
        entity_type="agent",
        roles={SocialRole.LEADER, SocialRole.EXPERT}
    )

    bob = manager.register_entity(
        name="Bob",
        entity_type="agent",
        roles={SocialRole.CONNECTOR}
    )

    charlie = manager.register_entity(
        name="Charlie",
        entity_type="agent",
        roles={SocialRole.INNOVATOR}
    )

    diana = manager.register_entity(
        name="Diana",
        entity_type="agent",
        roles={SocialRole.MEDIATOR}
    )

    print(f"   Registered: Alice, Bob, Charlie, Diana")
    print(f"   Alice roles: {[r.value for r in alice.roles]}")
    print()

    # 2. Create Relationships
    print("2. CREATE RELATIONSHIPS:")
    print("-" * 40)

    manager.create_relationship(
        alice.entity_id,
        bob.entity_id,
        RelationshipType.COLLABORATOR,
        strength=0.8,
        trust=0.9
    )

    manager.create_relationship(
        bob.entity_id,
        charlie.entity_id,
        RelationshipType.PEER,
        strength=0.6
    )

    manager.create_relationship(
        charlie.entity_id,
        diana.entity_id,
        RelationshipType.MENTOR,
        strength=0.7
    )

    manager.create_relationship(
        alice.entity_id,
        diana.entity_id,
        RelationshipType.FRIEND,
        strength=0.5
    )

    rel = manager.get_relationship(alice.entity_id, bob.entity_id)
    print(f"   Alice-Bob: {rel.relationship_type.value}, strength={rel.strength:.1f}")
    print()

    # 3. Record Interactions
    print("3. RECORD INTERACTIONS:")
    print("-" * 40)

    interaction = manager.record_interaction(
        participants=[alice.entity_id, bob.entity_id],
        interaction_type=InteractionType.COOPERATION,
        outcome="Successful project collaboration",
        sentiment=0.8
    )

    manager.record_interaction(
        participants=[bob.entity_id, charlie.entity_id, diana.entity_id],
        interaction_type=InteractionType.INFORMATION_SHARING,
        outcome="Knowledge transfer session",
        sentiment=0.6
    )

    print(f"   Recorded {len(manager._interactions)} interactions")
    print(f"   Latest: {interaction.interaction_type.value}")
    print()

    # 4. Social Metrics
    print("4. SOCIAL METRICS:")
    print("-" * 40)

    for entity in [alice, bob, charlie, diana]:
        metrics = manager.compute_social_metrics(entity.entity_id)
        print(f"   {entity.name}:")
        print(f"     Degree: {metrics.degree}")
        print(f"     Centrality: {metrics.centrality:.2f}")
        print(f"     Closeness: {metrics.closeness:.2f}")
    print()

    # 5. Reputation
    print("5. REPUTATION MANAGEMENT:")
    print("-" * 40)

    manager.update_reputation(alice.entity_id, 0.2, "Excellent leadership")
    manager.update_reputation(bob.entity_id, 0.1, "Good collaboration")

    manager.add_reputation_feedback(alice.entity_id, bob.entity_id, 0.9, "Great mentor")

    for entity in [alice, bob, charlie]:
        rep = manager.get_reputation(entity.entity_id)
        print(f"   {entity.name}: {rep:.2f}")
    print()

    # 6. Influence Mapping
    print("6. INFLUENCE MAPPING:")
    print("-" * 40)

    manager.add_influence(
        alice.entity_id,
        bob.entity_id,
        InfluenceType.EXPERT,
        strength=0.8
    )

    manager.add_influence(
        bob.entity_id,
        charlie.entity_id,
        InfluenceType.INFORMATIONAL,
        strength=0.6
    )

    alice_influence = manager.get_influence_score(alice.entity_id)
    print(f"   Alice influence score: {alice_influence:.2f}")

    path = manager.find_influence_path(alice.entity_id, charlie.entity_id)
    if path:
        path_names = [manager.get_entity(p).name for p in path if manager.get_entity(p)]
        print(f"   Influence path: {' -> '.join(path_names)}")
    print()

    # 7. Groups
    print("7. GROUP DYNAMICS:")
    print("-" * 40)

    team = manager.create_group(
        name="Project Team",
        description="Cross-functional project team",
        norms=[SocialNormType.COOPERATION, SocialNormType.RESPECT, SocialNormType.PUNCTUALITY]
    )

    manager.add_to_group(team.group_id, alice.entity_id, GroupRole.LEADER)
    manager.add_to_group(team.group_id, bob.entity_id, GroupRole.MEMBER)
    manager.add_to_group(team.group_id, charlie.entity_id, GroupRole.MEMBER)

    cohesion = manager.get_group_cohesion(team.group_id)

    print(f"   Group: {team.name}")
    print(f"   Members: {len(team.members)}")
    print(f"   Cohesion: {cohesion:.2f}")
    print()

    # 8. Social Norms
    print("8. SOCIAL NORMS:")
    print("-" * 40)

    manager.register_norm(
        SocialNormType.COOPERATION,
        "Work together towards common goals",
        importance=0.9
    )

    manager.register_norm(
        SocialNormType.HONESTY,
        "Be truthful in all communications",
        importance=0.95
    )

    # Check violations
    violations = manager.check_norm_violations(
        charlie.entity_id,
        "refuse to help with task",
        {}
    )

    if violations:
        for norm, severity in violations:
            print(f"   Violation: {norm.norm_type.value}, severity={severity:.2f}")
    else:
        print("   No violations detected")
    print()

    # 9. Network Overview
    print("9. NETWORK OVERVIEW:")
    print("-" * 40)

    overview = manager.get_network_overview()
    for key, value in overview.items():
        print(f"   {key}: {value}")
    print()

    # 10. Clusters
    print("10. SOCIAL CLUSTERS:")
    print("-" * 40)

    clusters = manager.find_clusters()
    print(f"   Found {len(clusters)} cluster(s)")
    for i, cluster in enumerate(clusters, 1):
        names = [manager.get_entity(e).name for e in cluster if manager.get_entity(e)]
        print(f"   Cluster {i}: {', '.join(names)}")
    print()

    # 11. Update Relationship
    print("11. UPDATE RELATIONSHIP:")
    print("-" * 40)

    before = manager.get_relationship(alice.entity_id, bob.entity_id)
    print(f"   Before: strength={before.strength:.2f}, trust={before.trust:.2f}")

    manager.update_relationship(
        alice.entity_id,
        bob.entity_id,
        strength_delta=0.1,
        trust_delta=0.05
    )

    after = manager.get_relationship(alice.entity_id, bob.entity_id)
    print(f"   After: strength={after.strength:.2f}, trust={after.trust:.2f}")
    print()

    # 12. Top Reputed
    print("12. TOP REPUTED ENTITIES:")
    print("-" * 40)

    top = manager.get_top_reputed_entities(5)
    for entity_id, reputation in top:
        entity = manager.get_entity(entity_id)
        name = entity.name if entity else "Unknown"
        print(f"   {name}: {reputation:.2f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Social Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
