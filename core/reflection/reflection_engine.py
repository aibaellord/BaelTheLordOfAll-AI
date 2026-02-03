#!/usr/bin/env python3
"""
BAEL - Reflection Engine
Self-reflection and metacognition.

Features:
- Self-awareness
- Metacognitive monitoring
- Performance introspection
- Capability assessment
- Belief revision
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

class ReflectionType(Enum):
    """Types of reflection."""
    INTROSPECTIVE = "introspective"
    RETROSPECTIVE = "retrospective"
    PROSPECTIVE = "prospective"
    COMPARATIVE = "comparative"


class MetacognitiveLevel(Enum):
    """Levels of metacognition."""
    MONITORING = "monitoring"
    EVALUATING = "evaluating"
    PLANNING = "planning"
    REGULATING = "regulating"


class AwarenessType(Enum):
    """Types of awareness."""
    SELF = "self"
    SITUATIONAL = "situational"
    SOCIAL = "social"
    TEMPORAL = "temporal"


class InsightLevel(Enum):
    """Levels of insight."""
    SURFACE = "surface"
    MODERATE = "moderate"
    DEEP = "deep"
    TRANSFORMATIVE = "transformative"


class ConfidenceLevel(Enum):
    """Confidence levels."""
    VERY_LOW = 0.1
    LOW = 0.3
    MODERATE = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Belief:
    """A belief held by the agent."""
    belief_id: str = ""
    content: str = ""
    confidence: float = 0.5
    source: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_revised: Optional[datetime] = None
    revision_count: int = 0

    def __post_init__(self):
        if not self.belief_id:
            self.belief_id = str(uuid.uuid4())[:8]


@dataclass
class Capability:
    """An agent capability."""
    capability_id: str = ""
    name: str = ""
    description: str = ""
    proficiency: float = 0.5
    experience_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[datetime] = None

    def __post_init__(self):
        if not self.capability_id:
            self.capability_id = str(uuid.uuid4())[:8]


@dataclass
class Reflection:
    """A reflection entry."""
    reflection_id: str = ""
    reflection_type: ReflectionType = ReflectionType.INTROSPECTIVE
    subject: str = ""
    content: str = ""
    insights: List[str] = field(default_factory=list)
    insight_level: InsightLevel = InsightLevel.SURFACE
    action_items: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.reflection_id:
            self.reflection_id = str(uuid.uuid4())[:8]


@dataclass
class SelfModel:
    """A model of the self."""
    model_id: str = ""
    capabilities: Dict[str, float] = field(default_factory=dict)
    beliefs: Dict[str, float] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    values: Dict[str, float] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.model_id:
            self.model_id = str(uuid.uuid4())[:8]


@dataclass
class PerformanceRecord:
    """A performance record."""
    record_id: str = ""
    task_type: str = ""
    success: bool = False
    quality_score: float = 0.0
    time_taken: float = 0.0
    errors: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.record_id:
            self.record_id = str(uuid.uuid4())[:8]


@dataclass
class MetacognitiveState:
    """Metacognitive state."""
    state_id: str = ""
    level: MetacognitiveLevel = MetacognitiveLevel.MONITORING
    current_focus: str = ""
    cognitive_load: float = 0.0
    confidence: float = 0.5
    uncertainty_areas: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.state_id:
            self.state_id = str(uuid.uuid4())[:8]


@dataclass
class ReflectionStats:
    """Reflection statistics."""
    total_reflections: int = 0
    introspective: int = 0
    retrospective: int = 0
    prospective: int = 0
    comparative: int = 0
    beliefs_revised: int = 0
    insights_generated: int = 0
    avg_insight_level: float = 0.0


# =============================================================================
# BELIEF MANAGER
# =============================================================================

class BeliefManager:
    """Manage agent beliefs."""

    def __init__(self):
        self._beliefs: Dict[str, Belief] = {}
        self._revision_history: List[Tuple[str, float, float]] = []

    def add(
        self,
        content: str,
        confidence: float = 0.5,
        source: str = ""
    ) -> Belief:
        """Add a belief."""
        belief = Belief(
            content=content,
            confidence=max(0.0, min(1.0, confidence)),
            source=source
        )

        self._beliefs[belief.belief_id] = belief

        return belief

    def get(self, belief_id: str) -> Optional[Belief]:
        """Get a belief."""
        return self._beliefs.get(belief_id)

    def find_by_content(self, query: str) -> List[Belief]:
        """Find beliefs by content."""
        query_lower = query.lower()
        return [
            b for b in self._beliefs.values()
            if query_lower in b.content.lower()
        ]

    def add_evidence(
        self,
        belief_id: str,
        evidence: str,
        supporting: bool = True
    ) -> bool:
        """Add evidence to a belief."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False

        if supporting:
            belief.supporting_evidence.append(evidence)
        else:
            belief.contradicting_evidence.append(evidence)

        self._recalculate_confidence(belief)

        return True

    def _recalculate_confidence(self, belief: Belief) -> None:
        """Recalculate belief confidence."""
        old_confidence = belief.confidence

        supporting_weight = len(belief.supporting_evidence) * 0.1
        contradicting_weight = len(belief.contradicting_evidence) * 0.1

        net_evidence = supporting_weight - contradicting_weight

        new_confidence = 0.5 + net_evidence
        belief.confidence = max(0.0, min(1.0, new_confidence))

        if abs(belief.confidence - old_confidence) > 0.05:
            belief.revision_count += 1
            belief.last_revised = datetime.now()
            self._revision_history.append((
                belief.belief_id,
                old_confidence,
                belief.confidence
            ))

    def revise(
        self,
        belief_id: str,
        new_confidence: float
    ) -> bool:
        """Revise a belief's confidence."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            return False

        old_confidence = belief.confidence
        belief.confidence = max(0.0, min(1.0, new_confidence))
        belief.revision_count += 1
        belief.last_revised = datetime.now()

        self._revision_history.append((
            belief_id,
            old_confidence,
            belief.confidence
        ))

        return True

    def remove(self, belief_id: str) -> bool:
        """Remove a belief."""
        if belief_id in self._beliefs:
            del self._beliefs[belief_id]
            return True
        return False

    def get_by_confidence(
        self,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0
    ) -> List[Belief]:
        """Get beliefs by confidence range."""
        return [
            b for b in self._beliefs.values()
            if min_confidence <= b.confidence <= max_confidence
        ]

    def get_uncertain(self, threshold: float = 0.3) -> List[Belief]:
        """Get uncertain beliefs."""
        return [
            b for b in self._beliefs.values()
            if abs(b.confidence - 0.5) < threshold
        ]

    @property
    def revision_count(self) -> int:
        return len(self._revision_history)


# =============================================================================
# CAPABILITY ASSESSOR
# =============================================================================

class CapabilityAssessor:
    """Assess agent capabilities."""

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._usage_history: Dict[str, List[bool]] = defaultdict(list)

    def register(
        self,
        name: str,
        description: str = "",
        initial_proficiency: float = 0.5
    ) -> Capability:
        """Register a capability."""
        capability = Capability(
            name=name,
            description=description,
            proficiency=max(0.0, min(1.0, initial_proficiency))
        )

        self._capabilities[capability.capability_id] = capability

        return capability

    def get(self, capability_id: str) -> Optional[Capability]:
        """Get a capability."""
        return self._capabilities.get(capability_id)

    def find_by_name(self, name: str) -> Optional[Capability]:
        """Find capability by name."""
        for cap in self._capabilities.values():
            if cap.name.lower() == name.lower():
                return cap
        return None

    def record_usage(
        self,
        capability_id: str,
        success: bool
    ) -> bool:
        """Record capability usage."""
        capability = self._capabilities.get(capability_id)
        if not capability:
            return False

        capability.experience_count += 1
        capability.last_used = datetime.now()

        self._usage_history[capability_id].append(success)

        if len(self._usage_history[capability_id]) > 100:
            self._usage_history[capability_id] = self._usage_history[capability_id][-100:]

        history = self._usage_history[capability_id]
        capability.success_rate = sum(history) / len(history) if history else 0.0

        capability.proficiency = 0.7 * capability.proficiency + 0.3 * capability.success_rate

        return True

    def assess(self, capability_id: str) -> Dict[str, Any]:
        """Assess a capability."""
        capability = self._capabilities.get(capability_id)
        if not capability:
            return {}

        history = self._usage_history.get(capability_id, [])
        recent = history[-10:] if history else []

        return {
            "name": capability.name,
            "proficiency": capability.proficiency,
            "experience_count": capability.experience_count,
            "success_rate": capability.success_rate,
            "recent_success_rate": sum(recent) / len(recent) if recent else 0.0,
            "trend": self._calculate_trend(history)
        }

    def _calculate_trend(self, history: List[bool]) -> str:
        """Calculate capability trend."""
        if len(history) < 10:
            return "insufficient_data"

        first_half = history[:len(history)//2]
        second_half = history[len(history)//2:]

        first_rate = sum(first_half) / len(first_half)
        second_rate = sum(second_half) / len(second_half)

        diff = second_rate - first_rate

        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"

    def get_strongest(self, n: int = 5) -> List[Capability]:
        """Get strongest capabilities."""
        sorted_caps = sorted(
            self._capabilities.values(),
            key=lambda c: c.proficiency,
            reverse=True
        )
        return sorted_caps[:n]

    def get_weakest(self, n: int = 5) -> List[Capability]:
        """Get weakest capabilities."""
        sorted_caps = sorted(
            self._capabilities.values(),
            key=lambda c: c.proficiency
        )
        return sorted_caps[:n]

    def get_underused(self, threshold_days: int = 7) -> List[Capability]:
        """Get underused capabilities."""
        threshold = datetime.now() - timedelta(days=threshold_days)

        return [
            c for c in self._capabilities.values()
            if c.last_used is None or c.last_used < threshold
        ]


# =============================================================================
# PERFORMANCE ANALYZER
# =============================================================================

class PerformanceAnalyzer:
    """Analyze performance."""

    def __init__(self):
        self._records: List[PerformanceRecord] = []
        self._by_task_type: Dict[str, List[PerformanceRecord]] = defaultdict(list)

    def record(
        self,
        task_type: str,
        success: bool,
        quality_score: float = 0.0,
        time_taken: float = 0.0,
        errors: Optional[List[str]] = None,
        lessons: Optional[List[str]] = None
    ) -> PerformanceRecord:
        """Record performance."""
        record = PerformanceRecord(
            task_type=task_type,
            success=success,
            quality_score=max(0.0, min(1.0, quality_score)),
            time_taken=time_taken,
            errors=errors or [],
            lessons=lessons or []
        )

        self._records.append(record)
        self._by_task_type[task_type].append(record)

        if len(self._records) > 1000:
            self._records = self._records[-1000:]

        return record

    def analyze_task_type(self, task_type: str) -> Dict[str, Any]:
        """Analyze performance for a task type."""
        records = self._by_task_type.get(task_type, [])

        if not records:
            return {}

        successes = [r for r in records if r.success]
        failures = [r for r in records if not r.success]

        return {
            "task_type": task_type,
            "total_attempts": len(records),
            "success_rate": len(successes) / len(records),
            "avg_quality": sum(r.quality_score for r in records) / len(records),
            "avg_time": sum(r.time_taken for r in records) / len(records),
            "common_errors": self._get_common_errors(records),
            "lessons_learned": self._get_unique_lessons(records)
        }

    def _get_common_errors(
        self,
        records: List[PerformanceRecord]
    ) -> List[Tuple[str, int]]:
        """Get common errors."""
        error_counts: Dict[str, int] = defaultdict(int)

        for record in records:
            for error in record.errors:
                error_counts[error] += 1

        sorted_errors = sorted(
            error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_errors[:5]

    def _get_unique_lessons(
        self,
        records: List[PerformanceRecord]
    ) -> List[str]:
        """Get unique lessons."""
        lessons = set()

        for record in records:
            for lesson in record.lessons:
                lessons.add(lesson)

        return list(lessons)[:10]

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        if not self._records:
            return {}

        successes = [r for r in self._records if r.success]

        return {
            "total_records": len(self._records),
            "success_rate": len(successes) / len(self._records),
            "avg_quality": sum(r.quality_score for r in self._records) / len(self._records),
            "avg_time": sum(r.time_taken for r in self._records) / len(self._records),
            "task_types": len(self._by_task_type)
        }

    def get_trend(self, window: int = 20) -> str:
        """Get overall trend."""
        if len(self._records) < window:
            return "insufficient_data"

        recent = self._records[-window:]
        first_half = recent[:window//2]
        second_half = recent[window//2:]

        first_rate = sum(1 for r in first_half if r.success) / len(first_half)
        second_rate = sum(1 for r in second_half if r.success) / len(second_half)

        diff = second_rate - first_rate

        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"


# =============================================================================
# METACOGNITIVE MONITOR
# =============================================================================

class MetacognitiveMonitor:
    """Monitor metacognitive state."""

    def __init__(self):
        self._states: List[MetacognitiveState] = []
        self._current_state: Optional[MetacognitiveState] = None

    def update(
        self,
        level: MetacognitiveLevel,
        current_focus: str = "",
        cognitive_load: float = 0.0,
        confidence: float = 0.5,
        uncertainty_areas: Optional[List[str]] = None
    ) -> MetacognitiveState:
        """Update metacognitive state."""
        state = MetacognitiveState(
            level=level,
            current_focus=current_focus,
            cognitive_load=max(0.0, min(1.0, cognitive_load)),
            confidence=max(0.0, min(1.0, confidence)),
            uncertainty_areas=uncertainty_areas or []
        )

        self._states.append(state)
        self._current_state = state

        if len(self._states) > 100:
            self._states = self._states[-100:]

        return state

    def get_current(self) -> Optional[MetacognitiveState]:
        """Get current state."""
        return self._current_state

    def get_history(self, limit: int = 20) -> List[MetacognitiveState]:
        """Get state history."""
        return self._states[-limit:]

    def get_avg_cognitive_load(self, window: int = 10) -> float:
        """Get average cognitive load."""
        recent = self._states[-window:]

        if not recent:
            return 0.0

        return sum(s.cognitive_load for s in recent) / len(recent)

    def get_avg_confidence(self, window: int = 10) -> float:
        """Get average confidence."""
        recent = self._states[-window:]

        if not recent:
            return 0.5

        return sum(s.confidence for s in recent) / len(recent)

    def get_uncertainty_summary(self) -> Dict[str, int]:
        """Get uncertainty summary."""
        uncertainty_counts: Dict[str, int] = defaultdict(int)

        for state in self._states[-20:]:
            for area in state.uncertainty_areas:
                uncertainty_counts[area] += 1

        return dict(uncertainty_counts)


# =============================================================================
# SELF MODEL BUILDER
# =============================================================================

class SelfModelBuilder:
    """Build and maintain self-model."""

    def __init__(
        self,
        belief_manager: BeliefManager,
        capability_assessor: CapabilityAssessor,
        performance_analyzer: PerformanceAnalyzer
    ):
        self._beliefs = belief_manager
        self._capabilities = capability_assessor
        self._performance = performance_analyzer
        self._model: Optional[SelfModel] = None

    def build(self) -> SelfModel:
        """Build the self-model."""
        capabilities = {}
        for cap in self._capabilities._capabilities.values():
            capabilities[cap.name] = cap.proficiency

        beliefs = {}
        for belief in self._beliefs._beliefs.values():
            beliefs[belief.content[:50]] = belief.confidence

        limitations = []
        weak = self._capabilities.get_weakest(3)
        for cap in weak:
            if cap.proficiency < 0.5:
                limitations.append(f"Low proficiency in {cap.name}")

        self._model = SelfModel(
            capabilities=capabilities,
            beliefs=beliefs,
            limitations=limitations
        )

        return self._model

    def get_model(self) -> Optional[SelfModel]:
        """Get current self-model."""
        return self._model

    def update_capabilities(self) -> None:
        """Update capability section."""
        if not self._model:
            return

        self._model.capabilities.clear()
        for cap in self._capabilities._capabilities.values():
            self._model.capabilities[cap.name] = cap.proficiency

        self._model.updated_at = datetime.now()

    def update_beliefs(self) -> None:
        """Update belief section."""
        if not self._model:
            return

        self._model.beliefs.clear()
        for belief in self._beliefs._beliefs.values():
            self._model.beliefs[belief.content[:50]] = belief.confidence

        self._model.updated_at = datetime.now()

    def set_values(self, values: Dict[str, float]) -> None:
        """Set values."""
        if not self._model:
            return

        self._model.values = {
            k: max(0.0, min(1.0, v))
            for k, v in values.items()
        }

        self._model.updated_at = datetime.now()

    def set_goals(self, goals: List[str]) -> None:
        """Set goals."""
        if not self._model:
            return

        self._model.goals = goals
        self._model.updated_at = datetime.now()


# =============================================================================
# REFLECTION ENGINE
# =============================================================================

class ReflectionEngine:
    """
    Reflection Engine for BAEL.

    Self-reflection and metacognition.
    """

    def __init__(self):
        self._beliefs = BeliefManager()
        self._capabilities = CapabilityAssessor()
        self._performance = PerformanceAnalyzer()
        self._metacognition = MetacognitiveMonitor()
        self._self_model_builder = SelfModelBuilder(
            self._beliefs,
            self._capabilities,
            self._performance
        )

        self._reflections: List[Reflection] = []
        self._stats = ReflectionStats()

    def add_belief(
        self,
        content: str,
        confidence: float = 0.5,
        source: str = ""
    ) -> Belief:
        """Add a belief."""
        return self._beliefs.add(content, confidence, source)

    def revise_belief(
        self,
        belief_id: str,
        new_confidence: float
    ) -> bool:
        """Revise a belief."""
        result = self._beliefs.revise(belief_id, new_confidence)
        if result:
            self._stats.beliefs_revised += 1
        return result

    def add_belief_evidence(
        self,
        belief_id: str,
        evidence: str,
        supporting: bool = True
    ) -> bool:
        """Add evidence to a belief."""
        return self._beliefs.add_evidence(belief_id, evidence, supporting)

    def get_uncertain_beliefs(
        self,
        threshold: float = 0.3
    ) -> List[Belief]:
        """Get uncertain beliefs."""
        return self._beliefs.get_uncertain(threshold)

    def register_capability(
        self,
        name: str,
        description: str = "",
        initial_proficiency: float = 0.5
    ) -> Capability:
        """Register a capability."""
        return self._capabilities.register(name, description, initial_proficiency)

    def record_capability_usage(
        self,
        capability_id: str,
        success: bool
    ) -> bool:
        """Record capability usage."""
        return self._capabilities.record_usage(capability_id, success)

    def assess_capability(self, capability_id: str) -> Dict[str, Any]:
        """Assess a capability."""
        return self._capabilities.assess(capability_id)

    def get_strongest_capabilities(self, n: int = 5) -> List[Capability]:
        """Get strongest capabilities."""
        return self._capabilities.get_strongest(n)

    def get_weakest_capabilities(self, n: int = 5) -> List[Capability]:
        """Get weakest capabilities."""
        return self._capabilities.get_weakest(n)

    def record_performance(
        self,
        task_type: str,
        success: bool,
        quality_score: float = 0.0,
        time_taken: float = 0.0,
        errors: Optional[List[str]] = None,
        lessons: Optional[List[str]] = None
    ) -> PerformanceRecord:
        """Record performance."""
        return self._performance.record(
            task_type, success, quality_score, time_taken, errors, lessons
        )

    def analyze_performance(self, task_type: str) -> Dict[str, Any]:
        """Analyze performance for a task type."""
        return self._performance.analyze_task_type(task_type)

    def get_performance_trend(self) -> str:
        """Get performance trend."""
        return self._performance.get_trend()

    def update_metacognitive_state(
        self,
        level: MetacognitiveLevel,
        current_focus: str = "",
        cognitive_load: float = 0.0,
        confidence: float = 0.5,
        uncertainty_areas: Optional[List[str]] = None
    ) -> MetacognitiveState:
        """Update metacognitive state."""
        return self._metacognition.update(
            level, current_focus, cognitive_load, confidence, uncertainty_areas
        )

    def get_metacognitive_state(self) -> Optional[MetacognitiveState]:
        """Get current metacognitive state."""
        return self._metacognition.get_current()

    def get_cognitive_load(self) -> float:
        """Get average cognitive load."""
        return self._metacognition.get_avg_cognitive_load()

    def get_confidence(self) -> float:
        """Get average confidence."""
        return self._metacognition.get_avg_confidence()

    def build_self_model(self) -> SelfModel:
        """Build self-model."""
        return self._self_model_builder.build()

    def get_self_model(self) -> Optional[SelfModel]:
        """Get self-model."""
        return self._self_model_builder.get_model()

    def set_values(self, values: Dict[str, float]) -> None:
        """Set self-model values."""
        self._self_model_builder.set_values(values)

    def set_goals(self, goals: List[str]) -> None:
        """Set self-model goals."""
        self._self_model_builder.set_goals(goals)

    def reflect(
        self,
        reflection_type: ReflectionType,
        subject: str,
        content: str,
        insights: Optional[List[str]] = None,
        insight_level: InsightLevel = InsightLevel.SURFACE,
        action_items: Optional[List[str]] = None
    ) -> Reflection:
        """Create a reflection."""
        reflection = Reflection(
            reflection_type=reflection_type,
            subject=subject,
            content=content,
            insights=insights or [],
            insight_level=insight_level,
            action_items=action_items or []
        )

        self._reflections.append(reflection)
        self._update_stats(reflection)

        return reflection

    def _update_stats(self, reflection: Reflection) -> None:
        """Update statistics."""
        self._stats.total_reflections += 1

        if reflection.reflection_type == ReflectionType.INTROSPECTIVE:
            self._stats.introspective += 1
        elif reflection.reflection_type == ReflectionType.RETROSPECTIVE:
            self._stats.retrospective += 1
        elif reflection.reflection_type == ReflectionType.PROSPECTIVE:
            self._stats.prospective += 1
        elif reflection.reflection_type == ReflectionType.COMPARATIVE:
            self._stats.comparative += 1

        self._stats.insights_generated += len(reflection.insights)

        insight_values = {
            InsightLevel.SURFACE: 0.25,
            InsightLevel.MODERATE: 0.5,
            InsightLevel.DEEP: 0.75,
            InsightLevel.TRANSFORMATIVE: 1.0
        }

        all_levels = [r.insight_level for r in self._reflections]
        if all_levels:
            self._stats.avg_insight_level = sum(
                insight_values.get(l, 0.25) for l in all_levels
            ) / len(all_levels)

    def get_reflections(
        self,
        reflection_type: Optional[ReflectionType] = None,
        limit: int = 20
    ) -> List[Reflection]:
        """Get reflections."""
        if reflection_type:
            filtered = [
                r for r in self._reflections
                if r.reflection_type == reflection_type
            ]
            return filtered[-limit:]

        return self._reflections[-limit:]

    def introspect(self) -> Dict[str, Any]:
        """Perform introspection."""
        self.update_metacognitive_state(
            level=MetacognitiveLevel.EVALUATING,
            current_focus="self-introspection"
        )

        model = self.build_self_model()

        introspection = {
            "timestamp": datetime.now().isoformat(),
            "self_model": {
                "capabilities": model.capabilities,
                "limitations": model.limitations,
                "values": model.values,
                "goals": model.goals
            },
            "performance": self._performance.get_overall_stats(),
            "metacognition": {
                "cognitive_load": self.get_cognitive_load(),
                "confidence": self.get_confidence(),
                "uncertainties": self._metacognition.get_uncertainty_summary()
            },
            "beliefs": {
                "total": len(self._beliefs._beliefs),
                "uncertain": len(self.get_uncertain_beliefs()),
                "revisions": self._stats.beliefs_revised
            }
        }

        return introspection

    @property
    def stats(self) -> ReflectionStats:
        """Get statistics."""
        return self._stats

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "total_reflections": self._stats.total_reflections,
            "introspective": self._stats.introspective,
            "retrospective": self._stats.retrospective,
            "prospective": self._stats.prospective,
            "comparative": self._stats.comparative,
            "beliefs": len(self._beliefs._beliefs),
            "beliefs_revised": self._stats.beliefs_revised,
            "capabilities": len(self._capabilities._capabilities),
            "performance_records": len(self._performance._records),
            "insights_generated": self._stats.insights_generated,
            "avg_insight_level": f"{self._stats.avg_insight_level:.2f}",
            "cognitive_load": f"{self.get_cognitive_load():.2f}",
            "confidence": f"{self.get_confidence():.2f}"
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Reflection Engine."""
    print("=" * 70)
    print("BAEL - REFLECTION ENGINE DEMO")
    print("Self-Reflection and Metacognition")
    print("=" * 70)
    print()

    engine = ReflectionEngine()

    # 1. Add Beliefs
    print("1. ADD BELIEFS:")
    print("-" * 40)

    belief1 = engine.add_belief(
        "I can effectively solve complex problems",
        confidence=0.7,
        source="past_experience"
    )

    belief2 = engine.add_belief(
        "Continuous learning improves performance",
        confidence=0.9,
        source="observation"
    )

    belief3 = engine.add_belief(
        "I handle high-load situations well",
        confidence=0.5,
        source="inference"
    )

    print(f"   Belief 1: {belief1.content[:40]}... ({belief1.confidence})")
    print(f"   Belief 2: {belief2.content[:40]}... ({belief2.confidence})")
    print(f"   Belief 3: {belief3.content[:40]}... ({belief3.confidence})")
    print()

    # 2. Add Evidence
    print("2. ADD BELIEF EVIDENCE:")
    print("-" * 40)

    engine.add_belief_evidence(
        belief3.belief_id,
        "Handled 1000 requests/second successfully",
        supporting=True
    )

    engine.add_belief_evidence(
        belief3.belief_id,
        "Latency spike under heavy load",
        supporting=False
    )

    updated_belief = engine._beliefs.get(belief3.belief_id)
    print(f"   Original confidence: 0.5")
    print(f"   Updated confidence: {updated_belief.confidence:.2f}")
    print()

    # 3. Register Capabilities
    print("3. REGISTER CAPABILITIES:")
    print("-" * 40)

    reasoning = engine.register_capability(
        "logical_reasoning",
        "Ability to reason logically",
        initial_proficiency=0.7
    )

    learning = engine.register_capability(
        "pattern_learning",
        "Ability to learn patterns",
        initial_proficiency=0.6
    )

    planning = engine.register_capability(
        "strategic_planning",
        "Ability to plan strategically",
        initial_proficiency=0.5
    )

    print(f"   {reasoning.name}: {reasoning.proficiency}")
    print(f"   {learning.name}: {learning.proficiency}")
    print(f"   {planning.name}: {planning.proficiency}")
    print()

    # 4. Record Capability Usage
    print("4. RECORD CAPABILITY USAGE:")
    print("-" * 40)

    for i in range(10):
        success = random.random() > 0.3
        engine.record_capability_usage(reasoning.capability_id, success)

    assessment = engine.assess_capability(reasoning.capability_id)
    print(f"   {assessment['name']}:")
    print(f"     Proficiency: {assessment['proficiency']:.2f}")
    print(f"     Success Rate: {assessment['success_rate']:.2%}")
    print(f"     Trend: {assessment['trend']}")
    print()

    # 5. Record Performance
    print("5. RECORD PERFORMANCE:")
    print("-" * 40)

    for i in range(5):
        engine.record_performance(
            "text_analysis",
            success=random.random() > 0.2,
            quality_score=random.uniform(0.6, 1.0),
            time_taken=random.uniform(0.5, 2.0),
            lessons=["Improve tokenization"] if random.random() > 0.7 else []
        )

    analysis = engine.analyze_performance("text_analysis")
    print(f"   Task: {analysis['task_type']}")
    print(f"   Attempts: {analysis['total_attempts']}")
    print(f"   Success Rate: {analysis['success_rate']:.2%}")
    print(f"   Avg Quality: {analysis['avg_quality']:.2f}")
    print()

    # 6. Update Metacognitive State
    print("6. UPDATE METACOGNITIVE STATE:")
    print("-" * 40)

    state = engine.update_metacognitive_state(
        level=MetacognitiveLevel.MONITORING,
        current_focus="performance optimization",
        cognitive_load=0.6,
        confidence=0.75,
        uncertainty_areas=["memory management", "scaling"]
    )

    print(f"   Level: {state.level.value}")
    print(f"   Focus: {state.current_focus}")
    print(f"   Cognitive Load: {state.cognitive_load}")
    print(f"   Confidence: {state.confidence}")
    print()

    # 7. Build Self-Model
    print("7. BUILD SELF-MODEL:")
    print("-" * 40)

    engine.set_values({
        "accuracy": 0.9,
        "efficiency": 0.8,
        "adaptability": 0.75
    })

    engine.set_goals([
        "Improve reasoning accuracy",
        "Reduce response latency",
        "Learn new domains"
    ])

    model = engine.build_self_model()

    print(f"   Capabilities: {len(model.capabilities)}")
    print(f"   Beliefs: {len(model.beliefs)}")
    print(f"   Goals: {len(model.goals)}")
    print(f"   Values: {model.values}")
    print(f"   Limitations: {model.limitations}")
    print()

    # 8. Create Reflections
    print("8. CREATE REFLECTIONS:")
    print("-" * 40)

    reflection1 = engine.reflect(
        ReflectionType.RETROSPECTIVE,
        subject="Recent task handling",
        content="Analyzed how I handled recent complex tasks",
        insights=[
            "Breaking down tasks improved success rate",
            "Time management needs improvement"
        ],
        insight_level=InsightLevel.MODERATE,
        action_items=["Implement better task decomposition"]
    )

    reflection2 = engine.reflect(
        ReflectionType.PROSPECTIVE,
        subject="Future capability development",
        content="Planning for upcoming challenges",
        insights=[
            "Need to strengthen strategic planning",
            "Should improve pattern recognition"
        ],
        insight_level=InsightLevel.DEEP
    )

    print(f"   Reflection 1: {reflection1.subject}")
    print(f"     Type: {reflection1.reflection_type.value}")
    print(f"     Insights: {len(reflection1.insights)}")
    print(f"   Reflection 2: {reflection2.subject}")
    print(f"     Type: {reflection2.reflection_type.value}")
    print(f"     Insight Level: {reflection2.insight_level.value}")
    print()

    # 9. Perform Introspection
    print("9. PERFORM INTROSPECTION:")
    print("-" * 40)

    introspection = engine.introspect()

    print(f"   Self-model capabilities: {len(introspection['self_model']['capabilities'])}")
    print(f"   Performance records: {introspection['performance'].get('total_records', 0)}")
    print(f"   Cognitive load: {introspection['metacognition']['cognitive_load']:.2f}")
    print(f"   Confidence: {introspection['metacognition']['confidence']:.2f}")
    print(f"   Uncertain beliefs: {introspection['beliefs']['uncertain']}")
    print()

    # 10. Get Capabilities Analysis
    print("10. CAPABILITIES ANALYSIS:")
    print("-" * 40)

    strongest = engine.get_strongest_capabilities(3)
    weakest = engine.get_weakest_capabilities(3)

    print("   Strongest:")
    for cap in strongest:
        print(f"     - {cap.name}: {cap.proficiency:.2f}")

    print("   Weakest:")
    for cap in weakest:
        print(f"     - {cap.name}: {cap.proficiency:.2f}")
    print()

    # 11. Statistics
    print("11. REFLECTION STATISTICS:")
    print("-" * 40)

    stats = engine.stats

    print(f"   Total Reflections: {stats.total_reflections}")
    print(f"   Introspective: {stats.introspective}")
    print(f"   Retrospective: {stats.retrospective}")
    print(f"   Prospective: {stats.prospective}")
    print(f"   Insights Generated: {stats.insights_generated}")
    print(f"   Avg Insight Level: {stats.avg_insight_level:.2f}")
    print()

    # 12. Summary
    print("12. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Reflection Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
