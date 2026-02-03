#!/usr/bin/env python3
"""
BAEL - Reputation Engine
Multi-dimensional reputation management for agents.

Features:
- Reputation scoring
- Behavioral history
- Reputation aggregation
- Context-aware reputation
- Reputation decay and recovery
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

class ReputationDimension(Enum):
    """Dimensions of reputation."""
    RELIABILITY = "reliability"
    COMPETENCE = "competence"
    INTEGRITY = "integrity"
    RESPONSIVENESS = "responsiveness"
    COLLABORATION = "collaboration"


class ReputationLevel(Enum):
    """Reputation levels."""
    UNKNOWN = 0
    POOR = 1
    FAIR = 2
    GOOD = 3
    EXCELLENT = 4
    OUTSTANDING = 5


class BehaviorType(Enum):
    """Types of behaviors."""
    TASK_COMPLETION = "task_completion"
    COMMUNICATION = "communication"
    RESOURCE_SHARING = "resource_sharing"
    PROMISE_KEEPING = "promise_keeping"
    ERROR_HANDLING = "error_handling"


class BehaviorOutcome(Enum):
    """Behavior outcomes."""
    EXCEPTIONAL = "exceptional"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    CRITICAL_FAILURE = "critical_failure"


class ContextType(Enum):
    """Context types for reputation."""
    GENERAL = "general"
    DOMAIN_SPECIFIC = "domain_specific"
    RELATIONSHIP = "relationship"
    TEMPORAL = "temporal"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ReputationScore:
    """A reputation score."""
    entity_id: str = ""
    overall: float = 0.5
    dimensions: Dict[str, float] = field(default_factory=dict)
    level: ReputationLevel = ReputationLevel.FAIR
    confidence: float = 0.0
    sample_size: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.dimensions:
            for dim in ReputationDimension:
                self.dimensions[dim.value] = 0.5


@dataclass
class BehaviorRecord:
    """A behavior record."""
    record_id: str = ""
    entity_id: str = ""
    behavior_type: BehaviorType = BehaviorType.TASK_COMPLETION
    outcome: BehaviorOutcome = BehaviorOutcome.POSITIVE
    context: Dict[str, Any] = field(default_factory=dict)
    impact: float = 1.0
    witnesses: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.record_id:
            self.record_id = str(uuid.uuid4())[:8]


@dataclass
class ReputationUpdate:
    """A reputation update."""
    update_id: str = ""
    entity_id: str = ""
    dimension: str = ""
    old_value: float = 0.0
    new_value: float = 0.0
    reason: str = ""
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.update_id:
            self.update_id = str(uuid.uuid4())[:8]


@dataclass
class ReputationContext:
    """A context for reputation."""
    context_id: str = ""
    context_type: ContextType = ContextType.GENERAL
    parameters: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def __post_init__(self):
        if not self.context_id:
            self.context_id = str(uuid.uuid4())[:8]


@dataclass
class Endorsement:
    """An endorsement."""
    endorsement_id: str = ""
    endorser_id: str = ""
    target_id: str = ""
    dimension: str = ""
    strength: float = 1.0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.endorsement_id:
            self.endorsement_id = str(uuid.uuid4())[:8]


@dataclass
class ReputationConfig:
    """Reputation configuration."""
    decay_rate: float = 0.01
    recovery_rate: float = 0.05
    min_samples: int = 5
    max_history: int = 1000


# =============================================================================
# BEHAVIOR TRACKER
# =============================================================================

class BehaviorTracker:
    """Track entity behaviors."""

    def __init__(self, max_records: int = 10000):
        self._records: Dict[str, List[BehaviorRecord]] = defaultdict(list)
        self._max_records = max_records

    def record(
        self,
        entity_id: str,
        behavior_type: BehaviorType,
        outcome: BehaviorOutcome,
        impact: float = 1.0,
        context: Optional[Dict[str, Any]] = None,
        witnesses: Optional[List[str]] = None
    ) -> BehaviorRecord:
        """Record a behavior."""
        record = BehaviorRecord(
            entity_id=entity_id,
            behavior_type=behavior_type,
            outcome=outcome,
            impact=impact,
            context=context or {},
            witnesses=witnesses or []
        )

        self._records[entity_id].append(record)

        if len(self._records[entity_id]) > self._max_records:
            self._records[entity_id] = self._records[entity_id][-self._max_records:]

        return record

    def get_records(
        self,
        entity_id: str,
        behavior_type: Optional[BehaviorType] = None,
        limit: int = 100
    ) -> List[BehaviorRecord]:
        """Get behavior records."""
        records = self._records.get(entity_id, [])

        if behavior_type:
            records = [r for r in records if r.behavior_type == behavior_type]

        return records[-limit:]

    def get_behavior_stats(
        self,
        entity_id: str
    ) -> Dict[str, Any]:
        """Get behavior statistics."""
        records = self._records.get(entity_id, [])

        if not records:
            return {
                "total_behaviors": 0,
                "outcome_distribution": {},
                "behavior_types": {}
            }

        outcome_counts: Dict[str, int] = defaultdict(int)
        type_counts: Dict[str, int] = defaultdict(int)

        for record in records:
            outcome_counts[record.outcome.value] += 1
            type_counts[record.behavior_type.value] += 1

        return {
            "total_behaviors": len(records),
            "outcome_distribution": dict(outcome_counts),
            "behavior_types": dict(type_counts)
        }

    def get_success_rate(
        self,
        entity_id: str,
        behavior_type: Optional[BehaviorType] = None
    ) -> float:
        """Get success rate for an entity."""
        records = self.get_records(entity_id, behavior_type)

        if not records:
            return 0.5

        positive_outcomes = {
            BehaviorOutcome.EXCEPTIONAL,
            BehaviorOutcome.POSITIVE
        }

        successes = sum(
            1 for r in records
            if r.outcome in positive_outcomes
        )

        return successes / len(records)


# =============================================================================
# SCORE CALCULATOR
# =============================================================================

class ScoreCalculator:
    """Calculate reputation scores."""

    def __init__(self):
        self._outcome_values = {
            BehaviorOutcome.EXCEPTIONAL: 1.0,
            BehaviorOutcome.POSITIVE: 0.7,
            BehaviorOutcome.NEUTRAL: 0.5,
            BehaviorOutcome.NEGATIVE: 0.3,
            BehaviorOutcome.CRITICAL_FAILURE: 0.0
        }

        self._behavior_to_dimension = {
            BehaviorType.TASK_COMPLETION: ReputationDimension.COMPETENCE,
            BehaviorType.COMMUNICATION: ReputationDimension.RESPONSIVENESS,
            BehaviorType.RESOURCE_SHARING: ReputationDimension.COLLABORATION,
            BehaviorType.PROMISE_KEEPING: ReputationDimension.INTEGRITY,
            BehaviorType.ERROR_HANDLING: ReputationDimension.RELIABILITY
        }

    def calculate_from_behaviors(
        self,
        records: List[BehaviorRecord],
        current_score: Optional[ReputationScore] = None
    ) -> ReputationScore:
        """Calculate reputation from behaviors."""
        if current_score is None:
            current_score = ReputationScore()

        dimension_values: Dict[str, List[float]] = defaultdict(list)

        for record in records:
            dimension = self._behavior_to_dimension.get(record.behavior_type)

            if dimension:
                value = self._outcome_values.get(record.outcome, 0.5)
                weighted_value = value * record.impact
                dimension_values[dimension.value].append(weighted_value)

        for dim, values in dimension_values.items():
            if values:
                avg = sum(values) / len(values)

                learning_rate = min(0.3, len(values) * 0.05)

                current_score.dimensions[dim] = (
                    current_score.dimensions.get(dim, 0.5) * (1 - learning_rate) +
                    avg * learning_rate
                )

        current_score.overall = sum(current_score.dimensions.values()) / len(current_score.dimensions)
        current_score.level = self._score_to_level(current_score.overall)
        current_score.sample_size = len(records)
        current_score.confidence = min(1.0, len(records) / 50)
        current_score.last_updated = datetime.now()

        return current_score

    def _score_to_level(self, score: float) -> ReputationLevel:
        """Convert score to level."""
        if score >= 0.9:
            return ReputationLevel.OUTSTANDING
        elif score >= 0.75:
            return ReputationLevel.EXCELLENT
        elif score >= 0.6:
            return ReputationLevel.GOOD
        elif score >= 0.4:
            return ReputationLevel.FAIR
        elif score >= 0.2:
            return ReputationLevel.POOR
        else:
            return ReputationLevel.UNKNOWN

    def apply_decay(
        self,
        score: ReputationScore,
        decay_rate: float = 0.01
    ) -> ReputationScore:
        """Apply reputation decay."""
        neutral = 0.5

        for dim in score.dimensions:
            current = score.dimensions[dim]
            score.dimensions[dim] = current + decay_rate * (neutral - current)

        score.overall = sum(score.dimensions.values()) / len(score.dimensions)
        score.level = self._score_to_level(score.overall)
        score.confidence *= (1 - decay_rate)

        return score


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class ContextManager:
    """Manage reputation contexts."""

    def __init__(self):
        self._contexts: Dict[str, ReputationContext] = {}
        self._entity_contexts: Dict[str, List[str]] = defaultdict(list)

    def create_context(
        self,
        context_type: ContextType,
        parameters: Dict[str, Any],
        weight: float = 1.0
    ) -> ReputationContext:
        """Create a reputation context."""
        context = ReputationContext(
            context_type=context_type,
            parameters=parameters,
            weight=weight
        )

        self._contexts[context.context_id] = context

        return context

    def assign_context(
        self,
        entity_id: str,
        context_id: str
    ) -> None:
        """Assign context to entity."""
        if context_id in self._contexts:
            self._entity_contexts[entity_id].append(context_id)

    def get_entity_contexts(
        self,
        entity_id: str
    ) -> List[ReputationContext]:
        """Get contexts for an entity."""
        context_ids = self._entity_contexts.get(entity_id, [])

        return [
            self._contexts[cid]
            for cid in context_ids
            if cid in self._contexts
        ]

    def get_contextual_weight(
        self,
        entity_id: str,
        behavior: BehaviorRecord
    ) -> float:
        """Get contextual weight for behavior."""
        contexts = self.get_entity_contexts(entity_id)

        if not contexts:
            return 1.0

        total_weight = 0.0

        for ctx in contexts:
            if ctx.context_type == ContextType.DOMAIN_SPECIFIC:
                domain = ctx.parameters.get("domain")
                if domain and behavior.context.get("domain") == domain:
                    total_weight += ctx.weight * 1.5
                else:
                    total_weight += ctx.weight * 0.8
            else:
                total_weight += ctx.weight

        return total_weight / len(contexts) if contexts else 1.0


# =============================================================================
# ENDORSEMENT MANAGER
# =============================================================================

class EndorsementManager:
    """Manage endorsements."""

    def __init__(self):
        self._endorsements: Dict[str, List[Endorsement]] = defaultdict(list)

    def add_endorsement(
        self,
        endorser_id: str,
        target_id: str,
        dimension: str,
        strength: float = 1.0,
        message: str = ""
    ) -> Endorsement:
        """Add an endorsement."""
        endorsement = Endorsement(
            endorser_id=endorser_id,
            target_id=target_id,
            dimension=dimension,
            strength=min(1.0, max(0.0, strength)),
            message=message
        )

        self._endorsements[target_id].append(endorsement)

        return endorsement

    def get_endorsements(
        self,
        target_id: str,
        dimension: Optional[str] = None
    ) -> List[Endorsement]:
        """Get endorsements for an entity."""
        endorsements = self._endorsements.get(target_id, [])

        if dimension:
            endorsements = [
                e for e in endorsements
                if e.dimension == dimension
            ]

        return endorsements

    def calculate_endorsement_bonus(
        self,
        target_id: str,
        endorser_reputations: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate endorsement bonus per dimension."""
        bonuses: Dict[str, float] = defaultdict(float)
        counts: Dict[str, int] = defaultdict(int)

        for endorsement in self._endorsements.get(target_id, []):
            endorser_rep = endorser_reputations.get(endorsement.endorser_id, 0.5)

            weighted_strength = endorsement.strength * endorser_rep

            bonuses[endorsement.dimension] += weighted_strength * 0.1
            counts[endorsement.dimension] += 1

        for dim in bonuses:
            if counts[dim] > 0:
                bonuses[dim] /= counts[dim]

        return dict(bonuses)


# =============================================================================
# AGGREGATOR
# =============================================================================

class ReputationAggregator:
    """Aggregate reputation from multiple sources."""

    def __init__(self):
        self._source_weights: Dict[str, float] = {}

    def set_source_weight(self, source: str, weight: float) -> None:
        """Set weight for a reputation source."""
        self._source_weights[source] = max(0.0, weight)

    def aggregate(
        self,
        scores: List[Tuple[str, ReputationScore]]
    ) -> ReputationScore:
        """Aggregate multiple reputation scores."""
        if not scores:
            return ReputationScore()

        aggregated = ReputationScore()

        total_weight = 0.0
        dimension_sums: Dict[str, float] = defaultdict(float)
        dimension_weights: Dict[str, float] = defaultdict(float)

        for source, score in scores:
            weight = self._source_weights.get(source, 1.0)
            weighted = weight * score.confidence

            for dim, value in score.dimensions.items():
                dimension_sums[dim] += value * weighted
                dimension_weights[dim] += weighted

            total_weight += weighted

        for dim in dimension_sums:
            if dimension_weights[dim] > 0:
                aggregated.dimensions[dim] = dimension_sums[dim] / dimension_weights[dim]

        if aggregated.dimensions:
            aggregated.overall = sum(aggregated.dimensions.values()) / len(aggregated.dimensions)

        if total_weight > 0:
            aggregated.confidence = total_weight / len(scores)

        aggregated.sample_size = sum(s.sample_size for _, s in scores)
        aggregated.last_updated = datetime.now()

        return aggregated


# =============================================================================
# REPUTATION ENGINE
# =============================================================================

class ReputationEngine:
    """
    Reputation Engine for BAEL.

    Multi-dimensional reputation management.
    """

    def __init__(self, config: Optional[ReputationConfig] = None):
        self._config = config or ReputationConfig()

        self._behavior_tracker = BehaviorTracker(self._config.max_history)
        self._calculator = ScoreCalculator()
        self._context_manager = ContextManager()
        self._endorsement_manager = EndorsementManager()
        self._aggregator = ReputationAggregator()

        self._scores: Dict[str, ReputationScore] = {}
        self._updates: List[ReputationUpdate] = []

    def record_behavior(
        self,
        entity_id: str,
        behavior_type: BehaviorType,
        outcome: BehaviorOutcome,
        impact: float = 1.0,
        context: Optional[Dict[str, Any]] = None,
        witnesses: Optional[List[str]] = None
    ) -> ReputationScore:
        """Record a behavior and update reputation."""
        record = self._behavior_tracker.record(
            entity_id, behavior_type, outcome, impact, context, witnesses
        )

        context_weight = self._context_manager.get_contextual_weight(
            entity_id, record
        )
        record.impact *= context_weight

        records = self._behavior_tracker.get_records(entity_id)

        current = self._scores.get(entity_id, ReputationScore(entity_id=entity_id))
        old_overall = current.overall

        updated = self._calculator.calculate_from_behaviors(records, current)
        updated.entity_id = entity_id

        self._scores[entity_id] = updated

        update = ReputationUpdate(
            entity_id=entity_id,
            dimension="overall",
            old_value=old_overall,
            new_value=updated.overall,
            reason=f"{behavior_type.value}: {outcome.value}",
            source="behavior"
        )
        self._updates.append(update)

        return updated

    def get_reputation(self, entity_id: str) -> ReputationScore:
        """Get reputation score for an entity."""
        if entity_id not in self._scores:
            self._scores[entity_id] = ReputationScore(entity_id=entity_id)

        return self._scores[entity_id]

    def get_reputation_level(self, entity_id: str) -> ReputationLevel:
        """Get reputation level for an entity."""
        score = self.get_reputation(entity_id)
        return score.level

    def get_dimension_score(
        self,
        entity_id: str,
        dimension: ReputationDimension
    ) -> float:
        """Get score for a specific dimension."""
        score = self.get_reputation(entity_id)
        return score.dimensions.get(dimension.value, 0.5)

    def add_endorsement(
        self,
        endorser_id: str,
        target_id: str,
        dimension: ReputationDimension,
        strength: float = 1.0,
        message: str = ""
    ) -> None:
        """Add an endorsement."""
        self._endorsement_manager.add_endorsement(
            endorser_id, target_id, dimension.value, strength, message
        )

        endorser_reps = {
            endorser_id: self.get_reputation(endorser_id).overall
        }

        bonuses = self._endorsement_manager.calculate_endorsement_bonus(
            target_id, endorser_reps
        )

        if target_id in self._scores:
            for dim, bonus in bonuses.items():
                if dim in self._scores[target_id].dimensions:
                    self._scores[target_id].dimensions[dim] = min(
                        1.0,
                        self._scores[target_id].dimensions[dim] + bonus
                    )

            dims = self._scores[target_id].dimensions
            self._scores[target_id].overall = sum(dims.values()) / len(dims)

    def get_endorsements(
        self,
        entity_id: str,
        dimension: Optional[ReputationDimension] = None
    ) -> List[Endorsement]:
        """Get endorsements for an entity."""
        dim_value = dimension.value if dimension else None
        return self._endorsement_manager.get_endorsements(entity_id, dim_value)

    def create_context(
        self,
        context_type: ContextType,
        parameters: Dict[str, Any],
        weight: float = 1.0
    ) -> ReputationContext:
        """Create a reputation context."""
        return self._context_manager.create_context(
            context_type, parameters, weight
        )

    def assign_context(
        self,
        entity_id: str,
        context_id: str
    ) -> None:
        """Assign context to an entity."""
        self._context_manager.assign_context(entity_id, context_id)

    def apply_decay(
        self,
        entity_id: Optional[str] = None
    ) -> None:
        """Apply reputation decay."""
        if entity_id:
            entities = [entity_id]
        else:
            entities = list(self._scores.keys())

        for eid in entities:
            if eid in self._scores:
                score = self._scores[eid]

                time_since_update = datetime.now() - score.last_updated

                if time_since_update > timedelta(days=1):
                    days = time_since_update.days
                    decay = self._config.decay_rate * days

                    self._calculator.apply_decay(score, decay)

    def get_behavior_stats(
        self,
        entity_id: str
    ) -> Dict[str, Any]:
        """Get behavior statistics."""
        return self._behavior_tracker.get_behavior_stats(entity_id)

    def get_success_rate(
        self,
        entity_id: str,
        behavior_type: Optional[BehaviorType] = None
    ) -> float:
        """Get success rate for an entity."""
        return self._behavior_tracker.get_success_rate(entity_id, behavior_type)

    def aggregate_reputations(
        self,
        entity_id: str,
        external_scores: List[Tuple[str, ReputationScore]]
    ) -> ReputationScore:
        """Aggregate reputation from multiple sources."""
        local_score = self.get_reputation(entity_id)

        all_scores = [("local", local_score)] + external_scores

        self._aggregator.set_source_weight("local", 1.5)

        aggregated = self._aggregator.aggregate(all_scores)
        aggregated.entity_id = entity_id

        return aggregated

    def compare_reputations(
        self,
        entity1_id: str,
        entity2_id: str
    ) -> Dict[str, Any]:
        """Compare reputations of two entities."""
        score1 = self.get_reputation(entity1_id)
        score2 = self.get_reputation(entity2_id)

        comparison = {
            "entity1": {
                "id": entity1_id,
                "overall": score1.overall,
                "level": score1.level.name
            },
            "entity2": {
                "id": entity2_id,
                "overall": score2.overall,
                "level": score2.level.name
            },
            "difference": score1.overall - score2.overall,
            "higher_reputation": entity1_id if score1.overall > score2.overall else entity2_id,
            "dimension_comparison": {}
        }

        for dim in ReputationDimension:
            d = dim.value
            comparison["dimension_comparison"][d] = {
                "entity1": score1.dimensions.get(d, 0.5),
                "entity2": score2.dimensions.get(d, 0.5)
            }

        return comparison

    def get_top_entities(
        self,
        dimension: Optional[ReputationDimension] = None,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Get top entities by reputation."""
        if dimension:
            scored = [
                (eid, score.dimensions.get(dimension.value, 0.5))
                for eid, score in self._scores.items()
            ]
        else:
            scored = [
                (eid, score.overall)
                for eid, score in self._scores.items()
            ]

        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:limit]

    def get_recent_updates(
        self,
        entity_id: Optional[str] = None,
        limit: int = 20
    ) -> List[ReputationUpdate]:
        """Get recent reputation updates."""
        updates = self._updates

        if entity_id:
            updates = [u for u in updates if u.entity_id == entity_id]

        return updates[-limit:]

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        total_entities = len(self._scores)

        if total_entities > 0:
            avg_reputation = sum(
                s.overall for s in self._scores.values()
            ) / total_entities
        else:
            avg_reputation = 0.0

        level_counts = defaultdict(int)
        for score in self._scores.values():
            level_counts[score.level.name] += 1

        return {
            "total_entities": total_entities,
            "avg_reputation": f"{avg_reputation:.2f}",
            "level_distribution": dict(level_counts),
            "total_updates": len(self._updates)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Reputation Engine."""
    print("=" * 70)
    print("BAEL - REPUTATION ENGINE DEMO")
    print("Multi-Dimensional Reputation Management")
    print("=" * 70)
    print()

    engine = ReputationEngine()

    # 1. Record Behaviors
    print("1. RECORD BEHAVIORS:")
    print("-" * 40)

    score1 = engine.record_behavior(
        "agent_alpha",
        BehaviorType.TASK_COMPLETION,
        BehaviorOutcome.POSITIVE
    )
    print(f"   agent_alpha after task: {score1.overall:.2f} ({score1.level.name})")

    score2 = engine.record_behavior(
        "agent_alpha",
        BehaviorType.COMMUNICATION,
        BehaviorOutcome.EXCEPTIONAL
    )
    print(f"   agent_alpha after communication: {score2.overall:.2f}")

    score3 = engine.record_behavior(
        "agent_beta",
        BehaviorType.PROMISE_KEEPING,
        BehaviorOutcome.NEGATIVE
    )
    print(f"   agent_beta after broken promise: {score3.overall:.2f}")
    print()

    # 2. Get Reputation
    print("2. GET REPUTATION:")
    print("-" * 40)

    for entity in ["agent_alpha", "agent_beta", "agent_gamma"]:
        rep = engine.get_reputation(entity)
        level = engine.get_reputation_level(entity)
        print(f"   {entity}: {rep.overall:.2f} ({level.name})")
    print()

    # 3. Dimension Scores
    print("3. DIMENSION SCORES:")
    print("-" * 40)

    print("   agent_alpha dimensions:")
    for dim in ReputationDimension:
        score = engine.get_dimension_score("agent_alpha", dim)
        print(f"     {dim.value}: {score:.2f}")
    print()

    # 4. Add Endorsements
    print("4. ADD ENDORSEMENTS:")
    print("-" * 40)

    engine.record_behavior(
        "agent_gamma",
        BehaviorType.TASK_COMPLETION,
        BehaviorOutcome.EXCEPTIONAL
    )

    engine.add_endorsement(
        "agent_gamma",
        "agent_alpha",
        ReputationDimension.COMPETENCE,
        strength=0.9,
        message="Excellent work on the project"
    )

    engine.add_endorsement(
        "agent_gamma",
        "agent_alpha",
        ReputationDimension.COLLABORATION,
        strength=0.8
    )

    updated = engine.get_reputation("agent_alpha")
    print(f"   agent_alpha after endorsements: {updated.overall:.2f}")

    endorsements = engine.get_endorsements("agent_alpha")
    print(f"   Total endorsements: {len(endorsements)}")
    print()

    # 5. Create Context
    print("5. CREATE AND ASSIGN CONTEXT:")
    print("-" * 40)

    ctx = engine.create_context(
        ContextType.DOMAIN_SPECIFIC,
        {"domain": "machine_learning", "expertise_level": "expert"},
        weight=1.5
    )

    engine.assign_context("agent_alpha", ctx.context_id)

    print(f"   Created context: {ctx.context_id}")
    print(f"   Assigned to agent_alpha")
    print()

    # 6. Behavior Stats
    print("6. BEHAVIOR STATISTICS:")
    print("-" * 40)

    stats = engine.get_behavior_stats("agent_alpha")

    print(f"   Total behaviors: {stats['total_behaviors']}")
    print(f"   Outcome distribution: {stats['outcome_distribution']}")
    print(f"   Behavior types: {stats['behavior_types']}")
    print()

    # 7. Success Rate
    print("7. SUCCESS RATE:")
    print("-" * 40)

    for entity in ["agent_alpha", "agent_beta"]:
        rate = engine.get_success_rate(entity)
        print(f"   {entity}: {rate:.0%}")
    print()

    # 8. More Behaviors
    print("8. BUILD UP REPUTATION:")
    print("-" * 40)

    behaviors = [
        (BehaviorType.TASK_COMPLETION, BehaviorOutcome.POSITIVE),
        (BehaviorType.RESOURCE_SHARING, BehaviorOutcome.EXCEPTIONAL),
        (BehaviorType.ERROR_HANDLING, BehaviorOutcome.POSITIVE),
        (BehaviorType.PROMISE_KEEPING, BehaviorOutcome.POSITIVE),
    ]

    for btype, outcome in behaviors:
        engine.record_behavior("agent_alpha", btype, outcome)

    final = engine.get_reputation("agent_alpha")
    print(f"   agent_alpha final reputation: {final.overall:.2f} ({final.level.name})")
    print(f"   Confidence: {final.confidence:.2f}")
    print(f"   Sample size: {final.sample_size}")
    print()

    # 9. Compare Reputations
    print("9. COMPARE REPUTATIONS:")
    print("-" * 40)

    comparison = engine.compare_reputations("agent_alpha", "agent_beta")

    print(f"   agent_alpha: {comparison['entity1']['overall']:.2f}")
    print(f"   agent_beta: {comparison['entity2']['overall']:.2f}")
    print(f"   Higher: {comparison['higher_reputation']}")
    print()

    # 10. Top Entities
    print("10. TOP ENTITIES:")
    print("-" * 40)

    top = engine.get_top_entities(limit=5)

    for i, (entity, score) in enumerate(top, 1):
        print(f"   {i}. {entity}: {score:.2f}")
    print()

    # 11. Recent Updates
    print("11. RECENT UPDATES:")
    print("-" * 40)

    updates = engine.get_recent_updates(limit=5)

    for update in updates:
        delta = update.new_value - update.old_value
        sign = "+" if delta > 0 else ""
        print(f"   {update.entity_id}: {sign}{delta:.3f} ({update.reason})")
    print()

    # 12. Summary
    print("12. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Reputation Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
