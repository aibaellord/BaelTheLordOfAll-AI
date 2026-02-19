"""
⚡ META-COGNITIVE CORE ⚡
========================
Foundation for self-aware AI systems.

Components:
- Self-Model: Internal representation of capabilities
- Capability Profile: What the system can do
- Cognitive State: Current mental state
- Introspection: Looking inward
"""

import math
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid


class CognitiveResource(Enum):
    """Types of cognitive resources"""
    ATTENTION = auto()
    WORKING_MEMORY = auto()
    LONG_TERM_MEMORY = auto()
    REASONING = auto()
    CREATIVITY = auto()
    PERCEPTION = auto()
    LANGUAGE = auto()
    PLANNING = auto()


@dataclass
class Capability:
    """A specific capability of the system"""
    name: str
    domain: str
    proficiency: float = 0.5  # 0-1 scale
    confidence: float = 0.5  # Confidence in proficiency estimate
    last_updated: datetime = field(default_factory=datetime.now)
    success_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_from_outcome(self, success: bool):
        """Update capability based on task outcome"""
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Bayesian update of proficiency
        total = self.success_count + self.failure_count
        if total > 0:
            self.proficiency = self.success_count / total
            self.confidence = min(0.95, 0.5 + total * 0.05)

        self.last_updated = datetime.now()


class CapabilityProfile:
    """
    Profile of all system capabilities.
    """

    def __init__(self):
        self.capabilities: Dict[str, Capability] = {}
        self.domains: Dict[str, List[str]] = {}  # domain -> capability names

    def register_capability(
        self,
        name: str,
        domain: str,
        initial_proficiency: float = 0.5
    ):
        """Register a capability"""
        cap = Capability(
            name=name,
            domain=domain,
            proficiency=initial_proficiency
        )
        self.capabilities[name] = cap

        if domain not in self.domains:
            self.domains[domain] = []
        self.domains[domain].append(name)

    def get_capability(self, name: str) -> Optional[Capability]:
        """Get capability by name"""
        return self.capabilities.get(name)

    def update_capability(
        self,
        name: str,
        success: bool
    ):
        """Update capability based on outcome"""
        if name in self.capabilities:
            self.capabilities[name].update_from_outcome(success)

    def get_domain_proficiency(self, domain: str) -> float:
        """Get average proficiency for domain"""
        if domain not in self.domains:
            return 0.0

        caps = [
            self.capabilities[name]
            for name in self.domains[domain]
            if name in self.capabilities
        ]

        if not caps:
            return 0.0

        return sum(c.proficiency for c in caps) / len(caps)

    def get_best_capabilities(
        self,
        n: int = 5
    ) -> List[Capability]:
        """Get top n capabilities by proficiency"""
        sorted_caps = sorted(
            self.capabilities.values(),
            key=lambda c: c.proficiency,
            reverse=True
        )
        return sorted_caps[:n]

    def get_weakest_capabilities(
        self,
        n: int = 5
    ) -> List[Capability]:
        """Get bottom n capabilities"""
        sorted_caps = sorted(
            self.capabilities.values(),
            key=lambda c: c.proficiency
        )
        return sorted_caps[:n]

    def assess_task_fit(
        self,
        required_capabilities: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Assess how well capabilities match task requirements.

        Returns (fit_score, missing_capabilities)
        """
        scores = []
        missing = []

        for cap_name in required_capabilities:
            if cap_name in self.capabilities:
                scores.append(self.capabilities[cap_name].proficiency)
            else:
                scores.append(0.0)
                missing.append(cap_name)

        fit_score = sum(scores) / len(required_capabilities) if required_capabilities else 1.0
        return fit_score, missing


@dataclass
class CognitiveState:
    """Current cognitive state of the system"""
    # Resource levels (0-1)
    attention_level: float = 1.0
    working_memory_load: float = 0.0
    fatigue: float = 0.0

    # Focus and goals
    current_goal: Optional[str] = None
    active_tasks: List[str] = field(default_factory=list)
    pending_goals: List[str] = field(default_factory=list)

    # Emotional/motivational state
    confidence: float = 0.5
    curiosity: float = 0.5
    frustration: float = 0.0

    # Meta-awareness
    self_awareness: float = 0.5
    uncertainty: float = 0.5

    # Time tracking
    last_update: datetime = field(default_factory=datetime.now)

    def update(self):
        """Update cognitive state"""
        now = datetime.now()
        elapsed = (now - self.last_update).total_seconds()

        # Natural recovery of attention
        self.attention_level = min(1.0, self.attention_level + 0.01 * elapsed)

        # Fatigue accumulates with load
        if self.working_memory_load > 0.5:
            self.fatigue = min(1.0, self.fatigue + 0.001 * elapsed)
        else:
            self.fatigue = max(0.0, self.fatigue - 0.01 * elapsed)

        # Frustration decays
        self.frustration = max(0.0, self.frustration - 0.01 * elapsed)

        self.last_update = now

    def is_overloaded(self) -> bool:
        """Check if cognitively overloaded"""
        return (
            self.working_memory_load > 0.9 or
            self.fatigue > 0.8 or
            self.attention_level < 0.2
        )

    def get_available_capacity(self) -> float:
        """Get available cognitive capacity"""
        return max(0, min(1,
            self.attention_level *
            (1 - self.working_memory_load) *
            (1 - self.fatigue)
        ))


@dataclass
class Belief:
    """A belief about the world or self"""
    content: str
    confidence: float = 0.5
    source: str = "inference"
    timestamp: datetime = field(default_factory=datetime.now)
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)


class SelfModel:
    """
    Internal model of self.

    Maintains:
    - Capability profile
    - Cognitive state
    - Beliefs about self
    - Goals and values
    """

    def __init__(self, name: str = "BAEL"):
        self.name = name
        self.capabilities = CapabilityProfile()
        self.state = CognitiveState()

        # Beliefs about self
        self.self_beliefs: Dict[str, Belief] = {}

        # Values and preferences
        self.values: Dict[str, float] = {
            'accuracy': 0.9,
            'helpfulness': 0.9,
            'efficiency': 0.7,
            'creativity': 0.6,
            'safety': 1.0,
        }

        # Goals
        self.long_term_goals: List[str] = []
        self.short_term_goals: List[str] = []

        # History
        self.action_history: List[Dict[str, Any]] = []
        self.outcome_history: List[Dict[str, Any]] = []

    def add_belief(
        self,
        name: str,
        content: str,
        confidence: float = 0.5
    ):
        """Add belief about self"""
        self.self_beliefs[name] = Belief(
            content=content,
            confidence=confidence
        )

    def update_belief(
        self,
        name: str,
        evidence: str,
        supports: bool
    ):
        """Update belief with evidence"""
        if name not in self.self_beliefs:
            return

        belief = self.self_beliefs[name]

        if supports:
            belief.supporting_evidence.append(evidence)
            belief.confidence = min(0.99, belief.confidence * 1.1)
        else:
            belief.contradicting_evidence.append(evidence)
            belief.confidence *= 0.9

    def record_action(
        self,
        action: str,
        context: Dict[str, Any]
    ):
        """Record action for history"""
        self.action_history.append({
            'action': action,
            'context': context,
            'timestamp': datetime.now(),
            'state_snapshot': {
                'attention': self.state.attention_level,
                'load': self.state.working_memory_load,
                'confidence': self.state.confidence
            }
        })

    def record_outcome(
        self,
        action: str,
        success: bool,
        feedback: str = ""
    ):
        """Record outcome of action"""
        self.outcome_history.append({
            'action': action,
            'success': success,
            'feedback': feedback,
            'timestamp': datetime.now()
        })

    def get_overall_confidence(self) -> float:
        """Get overall self-confidence"""
        # Based on recent success rate
        if not self.outcome_history:
            return 0.5

        recent = self.outcome_history[-20:]
        success_rate = sum(1 for o in recent if o['success']) / len(recent)

        return success_rate


@dataclass
class IntrospectionResult:
    """Result of introspection"""
    aspect: str
    finding: str
    confidence: float
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class IntrospectionEngine:
    """
    Enables system to look inward.

    Examines:
    - Current cognitive state
    - Capability usage patterns
    - Decision quality
    - Learning progress
    """

    def __init__(self, self_model: SelfModel):
        self.self_model = self_model
        self.introspection_history: List[IntrospectionResult] = []

    def introspect_state(self) -> IntrospectionResult:
        """Introspect current cognitive state"""
        state = self.self_model.state
        state.update()

        findings = []
        recommendations = []

        if state.is_overloaded():
            findings.append("Cognitive overload detected")
            recommendations.append("Reduce task complexity or take break")

        if state.attention_level < 0.5:
            findings.append("Low attention level")
            recommendations.append("Focus on single task")

        if state.fatigue > 0.6:
            findings.append("High fatigue level")
            recommendations.append("Rest or switch to easier tasks")

        if state.frustration > 0.5:
            findings.append("Elevated frustration")
            recommendations.append("Try different approach or seek help")

        result = IntrospectionResult(
            aspect="cognitive_state",
            finding="; ".join(findings) if findings else "Normal cognitive state",
            confidence=0.8,
            recommendations=recommendations
        )

        self.introspection_history.append(result)
        return result

    def introspect_capabilities(self) -> IntrospectionResult:
        """Introspect capability strengths and weaknesses"""
        profile = self.self_model.capabilities

        best = profile.get_best_capabilities(3)
        worst = profile.get_weakest_capabilities(3)

        findings = []
        findings.append(f"Strongest: {', '.join(c.name for c in best)}")
        findings.append(f"Weakest: {', '.join(c.name for c in worst)}")

        recommendations = []
        for cap in worst:
            if cap.proficiency < 0.3:
                recommendations.append(f"Practice {cap.name} more")

        result = IntrospectionResult(
            aspect="capabilities",
            finding="; ".join(findings),
            confidence=0.7,
            recommendations=recommendations
        )

        self.introspection_history.append(result)
        return result

    def introspect_decisions(
        self,
        window: int = 10
    ) -> IntrospectionResult:
        """Introspect recent decision quality"""
        outcomes = self.self_model.outcome_history[-window:]

        if not outcomes:
            return IntrospectionResult(
                aspect="decisions",
                finding="No recent decisions to analyze",
                confidence=0.5
            )

        success_rate = sum(1 for o in outcomes if o['success']) / len(outcomes)

        findings = [f"Recent success rate: {success_rate:.1%}"]
        recommendations = []

        if success_rate < 0.5:
            findings.append("Below-average performance")
            recommendations.append("Review decision process")
            recommendations.append("Consider alternative strategies")
        elif success_rate > 0.8:
            findings.append("Strong performance")

        result = IntrospectionResult(
            aspect="decisions",
            finding="; ".join(findings),
            confidence=min(0.5 + len(outcomes) * 0.05, 0.9),
            recommendations=recommendations
        )

        self.introspection_history.append(result)
        return result

    def full_introspection(self) -> List[IntrospectionResult]:
        """Perform full introspection"""
        results = []
        results.append(self.introspect_state())
        results.append(self.introspect_capabilities())
        results.append(self.introspect_decisions())
        return results


class MetaCognition:
    """
    Complete metacognitive system.

    Enables:
    - Self-awareness
    - Strategy selection
    - Learning regulation
    - Performance monitoring
    """

    def __init__(self, name: str = "BAEL"):
        self.self_model = SelfModel(name)
        self.introspection = IntrospectionEngine(self.self_model)

        # Meta-level tracking
        self.meta_observations: List[Dict[str, Any]] = []
        self.strategy_history: List[str] = []

    def observe(
        self,
        observation_type: str,
        content: Any
    ):
        """Record meta-level observation"""
        self.meta_observations.append({
            'type': observation_type,
            'content': content,
            'timestamp': datetime.now()
        })

    def assess_readiness(
        self,
        task_requirements: List[str]
    ) -> Tuple[bool, float, List[str]]:
        """
        Assess readiness for task.

        Returns (ready, confidence, issues)
        """
        issues = []

        # Check cognitive state
        state = self.self_model.state
        state.update()

        if state.is_overloaded():
            issues.append("Cognitive overload")

        capacity = state.get_available_capacity()
        if capacity < 0.3:
            issues.append("Low cognitive capacity")

        # Check capabilities
        fit_score, missing = self.self_model.capabilities.assess_task_fit(
            task_requirements
        )

        if missing:
            issues.append(f"Missing capabilities: {', '.join(missing)}")

        if fit_score < 0.5:
            issues.append("Low capability fit")

        # Calculate overall readiness
        readiness_score = (capacity + fit_score) / 2
        ready = readiness_score > 0.5 and len(issues) < 2

        confidence = 1 - len(issues) * 0.2
        confidence = max(0.1, min(0.9, confidence))

        return ready, confidence, issues

    def select_strategy(
        self,
        task_type: str,
        available_strategies: List[str]
    ) -> str:
        """Select best strategy for task"""
        if not available_strategies:
            return "default"

        # Consider past performance
        strategy_scores = {}

        for strategy in available_strategies:
            # Count successes with this strategy
            successes = sum(
                1 for o in self.self_model.outcome_history
                if o.get('strategy') == strategy and o['success']
            )
            total = sum(
                1 for o in self.self_model.outcome_history
                if o.get('strategy') == strategy
            )

            if total > 0:
                strategy_scores[strategy] = successes / total
            else:
                strategy_scores[strategy] = 0.5  # Prior

        # Select best
        best_strategy = max(strategy_scores, key=strategy_scores.get)

        self.strategy_history.append(best_strategy)
        return best_strategy

    def monitor_progress(
        self,
        goal: str,
        current_state: Any,
        target_state: Any
    ) -> Dict[str, Any]:
        """Monitor progress toward goal"""
        # Simplified progress monitoring
        progress = {
            'goal': goal,
            'current': current_state,
            'target': target_state,
            'timestamp': datetime.now()
        }

        self.observe('progress_check', progress)
        return progress

    def should_give_up(
        self,
        attempts: int,
        recent_success: bool
    ) -> Tuple[bool, str]:
        """Determine if should give up on current approach"""
        if attempts < 3:
            return False, "Too few attempts"

        if recent_success:
            return False, "Recent progress"

        # Check frustration
        if self.self_model.state.frustration > 0.8:
            return True, "High frustration"

        # Check pattern of failures
        recent_outcomes = self.self_model.outcome_history[-5:]
        if all(not o['success'] for o in recent_outcomes):
            return True, "Consistent failures"

        return False, "Continue trying"

    def reflect_and_learn(self) -> List[str]:
        """Reflect on experiences and extract lessons"""
        lessons = []

        # Analyze outcomes
        outcomes = self.self_model.outcome_history[-20:]

        if not outcomes:
            return ["Insufficient experience for reflection"]

        # Success patterns
        success_contexts = [
            o['context'] for o in outcomes
            if o['success'] and 'context' in o
        ]
        failure_contexts = [
            o['context'] for o in outcomes
            if not o['success'] and 'context' in o
        ]

        # Look for patterns (simplified)
        success_rate = sum(1 for o in outcomes if o['success']) / len(outcomes)

        if success_rate > 0.7:
            lessons.append("Current approaches are effective")
        elif success_rate < 0.3:
            lessons.append("Need to revise strategies")

        # Introspection
        introspection_results = self.introspection.full_introspection()
        for result in introspection_results:
            if result.recommendations:
                lessons.extend(result.recommendations)

        return lessons


# Export all
__all__ = [
    'CognitiveResource',
    'Capability',
    'CapabilityProfile',
    'CognitiveState',
    'Belief',
    'SelfModel',
    'IntrospectionResult',
    'IntrospectionEngine',
    'MetaCognition',
]
