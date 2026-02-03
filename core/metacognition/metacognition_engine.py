#!/usr/bin/env python3
"""
BAEL - Metacognition Engine
Advanced metacognitive reasoning and self-awareness system.

Features:
- Self-monitoring and introspection
- Cognitive process awareness
- Strategy selection and evaluation
- Confidence calibration
- Knowledge assessment
- Learning regulation
- Cognitive load management
- Meta-reasoning
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

class CognitiveProcess(Enum):
    """Cognitive processes."""
    PERCEPTION = "perception"
    ATTENTION = "attention"
    MEMORY = "memory"
    REASONING = "reasoning"
    LEARNING = "learning"
    DECISION_MAKING = "decision_making"
    PROBLEM_SOLVING = "problem_solving"
    PLANNING = "planning"


class MetacognitiveActivity(Enum):
    """Metacognitive activities."""
    MONITORING = "monitoring"
    PLANNING = "planning"
    EVALUATING = "evaluating"
    REGULATING = "regulating"
    REFLECTING = "reflecting"


class ConfidenceState(Enum):
    """Confidence states."""
    UNDERCONFIDENT = "underconfident"
    WELL_CALIBRATED = "well_calibrated"
    OVERCONFIDENT = "overconfident"
    UNCERTAIN = "uncertain"


class StrategyType(Enum):
    """Cognitive strategy types."""
    REHEARSAL = "rehearsal"
    ELABORATION = "elaboration"
    ORGANIZATION = "organization"
    MONITORING = "monitoring"
    AFFECTIVE = "affective"
    RETRIEVAL = "retrieval"


class KnowledgeType(Enum):
    """Types of knowledge."""
    DECLARATIVE = "declarative"
    PROCEDURAL = "procedural"
    CONDITIONAL = "conditional"
    METACOGNITIVE = "metacognitive"


class CognitiveLoadLevel(Enum):
    """Cognitive load levels."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    OVERLOADED = "overloaded"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CognitiveState:
    """Current cognitive state."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    active_processes: Set[CognitiveProcess] = field(default_factory=set)
    cognitive_load: float = 0.0  # 0-1
    attention_level: float = 1.0  # 0-1
    fatigue_level: float = 0.0  # 0-1
    confidence: float = 0.5  # 0-1
    uncertainty: float = 0.5  # 0-1
    arousal: float = 0.5  # 0-1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntrospectionResult:
    """Result of introspection."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    process: CognitiveProcess = CognitiveProcess.REASONING
    observations: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfidenceAssessment:
    """Confidence assessment."""
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: str = ""
    predicted_confidence: float = 0.5
    actual_performance: float = 0.5
    calibration_error: float = 0.0
    state: ConfidenceState = ConfidenceState.UNCERTAIN
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Strategy:
    """Cognitive strategy."""
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    strategy_type: StrategyType = StrategyType.MONITORING
    description: str = ""
    applicability: List[str] = field(default_factory=list)
    effectiveness: float = 0.5
    cost: float = 0.5
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyEvaluation:
    """Evaluation of strategy effectiveness."""
    evaluation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str = ""
    task: str = ""
    success: bool = False
    effectiveness: float = 0.5
    time_taken: float = 0.0
    resources_used: float = 0.0
    lessons: List[str] = field(default_factory=list)


@dataclass
class KnowledgeAssessment:
    """Assessment of knowledge state."""
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = ""
    known: List[str] = field(default_factory=list)
    unknown: List[str] = field(default_factory=list)
    uncertain: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    confidence_by_topic: Dict[str, float] = field(default_factory=dict)


@dataclass
class LearningRegulation:
    """Learning regulation directive."""
    regulation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_strategy: str = ""
    recommended_strategy: str = ""
    reason: str = ""
    adjustments: List[str] = field(default_factory=list)
    priority: float = 0.5


@dataclass
class CognitiveLoadAssessment:
    """Cognitive load assessment."""
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intrinsic_load: float = 0.0
    extraneous_load: float = 0.0
    germane_load: float = 0.0
    total_load: float = 0.0
    capacity: float = 1.0
    level: CognitiveLoadLevel = CognitiveLoadLevel.MODERATE
    recommendations: List[str] = field(default_factory=list)


@dataclass
class MetaReasoningResult:
    """Result of meta-reasoning."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    reasoning_about: str = ""
    conclusions: List[str] = field(default_factory=list)
    quality_assessment: float = 0.5
    improvements: List[str] = field(default_factory=list)


# =============================================================================
# SELF MONITOR
# =============================================================================

class SelfMonitor:
    """Monitor cognitive processes."""

    def __init__(self):
        self._state_history: deque = deque(maxlen=1000)
        self._process_metrics: Dict[CognitiveProcess, Dict[str, float]] = {}
        self._current_state = CognitiveState()

    def update_state(
        self,
        active_processes: Optional[Set[CognitiveProcess]] = None,
        cognitive_load: Optional[float] = None,
        attention_level: Optional[float] = None,
        fatigue_level: Optional[float] = None,
        confidence: Optional[float] = None
    ) -> CognitiveState:
        """Update cognitive state."""
        if active_processes is not None:
            self._current_state.active_processes = active_processes
        if cognitive_load is not None:
            self._current_state.cognitive_load = cognitive_load
        if attention_level is not None:
            self._current_state.attention_level = attention_level
        if fatigue_level is not None:
            self._current_state.fatigue_level = fatigue_level
        if confidence is not None:
            self._current_state.confidence = confidence

        self._current_state.timestamp = datetime.now()
        self._current_state.uncertainty = 1.0 - self._current_state.confidence

        # Store history
        self._state_history.append(CognitiveState(
            active_processes=self._current_state.active_processes.copy(),
            cognitive_load=self._current_state.cognitive_load,
            attention_level=self._current_state.attention_level,
            fatigue_level=self._current_state.fatigue_level,
            confidence=self._current_state.confidence,
            uncertainty=self._current_state.uncertainty
        ))

        return self._current_state

    def get_state(self) -> CognitiveState:
        """Get current cognitive state."""
        return self._current_state

    def record_process_metric(
        self,
        process: CognitiveProcess,
        metric_name: str,
        value: float
    ) -> None:
        """Record metric for cognitive process."""
        if process not in self._process_metrics:
            self._process_metrics[process] = {}

        self._process_metrics[process][metric_name] = value

    def get_process_metrics(
        self,
        process: CognitiveProcess
    ) -> Dict[str, float]:
        """Get metrics for cognitive process."""
        return self._process_metrics.get(process, {})

    def detect_anomalies(self) -> List[str]:
        """Detect anomalies in cognitive state."""
        anomalies = []

        if self._current_state.cognitive_load > 0.9:
            anomalies.append("Cognitive overload detected")

        if self._current_state.attention_level < 0.3:
            anomalies.append("Low attention level")

        if self._current_state.fatigue_level > 0.8:
            anomalies.append("High fatigue level")

        if self._current_state.uncertainty > 0.8:
            anomalies.append("High uncertainty")

        return anomalies

    def get_trend(
        self,
        attribute: str,
        window: int = 10
    ) -> str:
        """Get trend for attribute."""
        if len(self._state_history) < 2:
            return "stable"

        recent = list(self._state_history)[-window:]

        if len(recent) < 2:
            return "stable"

        values = [getattr(s, attribute, 0.5) for s in recent]

        # Calculate trend
        first_half = sum(values[:len(values)//2]) / (len(values)//2) if values else 0
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2) if values else 0

        diff = second_half - first_half

        if diff > 0.1:
            return "increasing"
        elif diff < -0.1:
            return "decreasing"
        return "stable"


# =============================================================================
# INTROSPECTION ENGINE
# =============================================================================

class IntrospectionEngine:
    """Engine for self-introspection."""

    def __init__(self, self_monitor: SelfMonitor):
        self._self_monitor = self_monitor
        self._introspection_history: List[IntrospectionResult] = []

    def introspect(
        self,
        query: str,
        process: Optional[CognitiveProcess] = None
    ) -> IntrospectionResult:
        """Perform introspection."""
        observations = []
        insights = []

        state = self._self_monitor.get_state()

        # Observe current state
        observations.append(f"Current cognitive load: {state.cognitive_load:.1%}")
        observations.append(f"Attention level: {state.attention_level:.1%}")
        observations.append(f"Confidence: {state.confidence:.1%}")
        observations.append(f"Active processes: {len(state.active_processes)}")

        # Process-specific observations
        if process:
            metrics = self._self_monitor.get_process_metrics(process)
            for name, value in metrics.items():
                observations.append(f"{process.value} {name}: {value:.2f}")

        # Generate insights based on query
        if "performance" in query.lower():
            if state.cognitive_load > 0.8:
                insights.append("High cognitive load may be impacting performance")
            if state.fatigue_level > 0.5:
                insights.append("Fatigue may be affecting task execution")

        if "confidence" in query.lower():
            if state.uncertainty > 0.7:
                insights.append("High uncertainty suggests need for more information")
            insights.append(f"Confidence trend: {self._self_monitor.get_trend('confidence')}")

        if "attention" in query.lower():
            trend = self._self_monitor.get_trend('attention_level')
            insights.append(f"Attention is {trend}")
            if state.attention_level < 0.5:
                insights.append("Low attention may require refocusing strategies")

        # Detect anomalies
        anomalies = self._self_monitor.detect_anomalies()
        for anomaly in anomalies:
            insights.append(f"Alert: {anomaly}")

        result = IntrospectionResult(
            query=query,
            process=process or CognitiveProcess.REASONING,
            observations=observations,
            insights=insights,
            confidence=state.confidence
        )

        self._introspection_history.append(result)

        return result

    def reflect(self, topic: str) -> List[str]:
        """Reflect on a topic."""
        reflections = []

        # Gather relevant introspection history
        relevant = [
            i for i in self._introspection_history
            if topic.lower() in i.query.lower()
        ][-5:]

        if relevant:
            reflections.append(f"Found {len(relevant)} past introspections on {topic}")

            # Analyze patterns
            avg_confidence = sum(i.confidence for i in relevant) / len(relevant)
            reflections.append(f"Average confidence on {topic}: {avg_confidence:.1%}")

            # Collect unique insights
            all_insights = set()
            for i in relevant:
                all_insights.update(i.insights)

            if all_insights:
                reflections.append(f"Key insights: {'; '.join(list(all_insights)[:3])}")
        else:
            reflections.append(f"No prior introspection on {topic}")
            reflections.append("This is a new area requiring careful attention")

        return reflections


# =============================================================================
# CONFIDENCE CALIBRATOR
# =============================================================================

class ConfidenceCalibrator:
    """Calibrate confidence levels."""

    def __init__(self):
        self._prediction_history: List[Tuple[float, float]] = []
        self._calibration_bins: Dict[int, List[Tuple[float, float]]] = defaultdict(list)

    def record_prediction(
        self,
        predicted_confidence: float,
        actual_outcome: float  # 0 or 1 for binary, or performance score
    ) -> None:
        """Record a prediction and its outcome."""
        self._prediction_history.append((predicted_confidence, actual_outcome))

        # Bin predictions
        bin_idx = int(predicted_confidence * 10)
        self._calibration_bins[bin_idx].append((predicted_confidence, actual_outcome))

    def assess(
        self,
        task: str,
        predicted_confidence: float
    ) -> ConfidenceAssessment:
        """Assess confidence calibration."""
        # Calculate historical calibration error
        if len(self._prediction_history) < 5:
            # Not enough data
            return ConfidenceAssessment(
                task=task,
                predicted_confidence=predicted_confidence,
                actual_performance=predicted_confidence,
                calibration_error=0.0,
                state=ConfidenceState.UNCERTAIN,
                recommendations=["Need more data to assess calibration"]
            )

        # Get historical performance at this confidence level
        bin_idx = int(predicted_confidence * 10)
        similar_predictions = self._calibration_bins.get(bin_idx, [])

        if similar_predictions:
            actual_avg = sum(o for _, o in similar_predictions) / len(similar_predictions)
        else:
            actual_avg = predicted_confidence

        # Calibration error
        calibration_error = predicted_confidence - actual_avg

        # Determine state
        if abs(calibration_error) < 0.1:
            state = ConfidenceState.WELL_CALIBRATED
        elif calibration_error > 0.1:
            state = ConfidenceState.OVERCONFIDENT
        else:
            state = ConfidenceState.UNDERCONFIDENT

        # Generate recommendations
        recommendations = []
        if state == ConfidenceState.OVERCONFIDENT:
            recommendations.append("Consider reducing confidence estimates")
            recommendations.append("Seek additional verification")
        elif state == ConfidenceState.UNDERCONFIDENT:
            recommendations.append("Historical performance suggests higher confidence is warranted")
            recommendations.append("Trust your abilities more")

        return ConfidenceAssessment(
            task=task,
            predicted_confidence=predicted_confidence,
            actual_performance=actual_avg,
            calibration_error=calibration_error,
            state=state,
            recommendations=recommendations
        )

    def get_calibration_curve(self) -> List[Tuple[float, float]]:
        """Get calibration curve data."""
        curve = []

        for bin_idx in range(11):
            predictions = self._calibration_bins.get(bin_idx, [])
            if predictions:
                avg_predicted = sum(p for p, _ in predictions) / len(predictions)
                avg_actual = sum(o for _, o in predictions) / len(predictions)
                curve.append((avg_predicted, avg_actual))

        return curve


# =============================================================================
# STRATEGY MANAGER
# =============================================================================

class StrategyManager:
    """Manage cognitive strategies."""

    def __init__(self):
        self._strategies: Dict[str, Strategy] = {}
        self._evaluations: List[StrategyEvaluation] = []
        self._current_strategy: Optional[str] = None

        # Register default strategies
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register default cognitive strategies."""
        defaults = [
            Strategy(
                name="chunking",
                strategy_type=StrategyType.ORGANIZATION,
                description="Break information into manageable chunks",
                applicability=["memory", "learning", "complex_tasks"],
                effectiveness=0.7,
                cost=0.3
            ),
            Strategy(
                name="elaboration",
                strategy_type=StrategyType.ELABORATION,
                description="Connect new information to existing knowledge",
                applicability=["learning", "understanding"],
                effectiveness=0.8,
                cost=0.5
            ),
            Strategy(
                name="self_testing",
                strategy_type=StrategyType.MONITORING,
                description="Periodically test understanding",
                applicability=["learning", "verification"],
                effectiveness=0.75,
                cost=0.4
            ),
            Strategy(
                name="spaced_practice",
                strategy_type=StrategyType.REHEARSAL,
                description="Distribute practice over time",
                applicability=["memory", "skill_acquisition"],
                effectiveness=0.85,
                cost=0.6
            ),
            Strategy(
                name="visualization",
                strategy_type=StrategyType.ELABORATION,
                description="Create mental images",
                applicability=["understanding", "memory"],
                effectiveness=0.65,
                cost=0.3
            ),
            Strategy(
                name="goal_decomposition",
                strategy_type=StrategyType.ORGANIZATION,
                description="Break goals into sub-goals",
                applicability=["planning", "problem_solving"],
                effectiveness=0.8,
                cost=0.4
            ),
        ]

        for strategy in defaults:
            self._strategies[strategy.name] = strategy

    def register_strategy(self, strategy: Strategy) -> None:
        """Register a new strategy."""
        self._strategies[strategy.name] = strategy

    def select_strategy(
        self,
        task_type: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Optional[Strategy]:
        """Select best strategy for task."""
        applicable = [
            s for s in self._strategies.values()
            if task_type in s.applicability
        ]

        if not applicable:
            return None

        # Filter by constraints
        if constraints:
            max_cost = constraints.get("max_cost", 1.0)
            applicable = [s for s in applicable if s.cost <= max_cost]

        if not applicable:
            return None

        # Select by effectiveness
        best = max(applicable, key=lambda s: s.effectiveness)
        self._current_strategy = best.name

        return best

    def evaluate_strategy(
        self,
        strategy_id: str,
        task: str,
        success: bool,
        time_taken: float,
        lessons: Optional[List[str]] = None
    ) -> StrategyEvaluation:
        """Evaluate strategy effectiveness."""
        evaluation = StrategyEvaluation(
            strategy_id=strategy_id,
            task=task,
            success=success,
            effectiveness=1.0 if success else 0.0,
            time_taken=time_taken,
            lessons=lessons or []
        )

        self._evaluations.append(evaluation)

        # Update strategy effectiveness
        strategy = self._strategies.get(strategy_id)
        if strategy:
            # Running average
            strategy.effectiveness = (
                strategy.effectiveness * 0.9 + evaluation.effectiveness * 0.1
            )

        return evaluation

    def get_strategy(self, name: str) -> Optional[Strategy]:
        """Get strategy by name."""
        return self._strategies.get(name)

    def get_all_strategies(self) -> List[Strategy]:
        """Get all strategies."""
        return list(self._strategies.values())


# =============================================================================
# KNOWLEDGE ASSESSOR
# =============================================================================

class KnowledgeAssessor:
    """Assess knowledge state."""

    def __init__(self):
        self._knowledge_base: Dict[str, Dict[str, float]] = {}

    def register_domain(
        self,
        domain: str,
        topics: Dict[str, float]  # topic -> confidence
    ) -> None:
        """Register domain knowledge."""
        self._knowledge_base[domain] = topics

    def update_knowledge(
        self,
        domain: str,
        topic: str,
        confidence: float
    ) -> None:
        """Update knowledge confidence."""
        if domain not in self._knowledge_base:
            self._knowledge_base[domain] = {}

        self._knowledge_base[domain][topic] = confidence

    def assess(self, domain: str) -> KnowledgeAssessment:
        """Assess knowledge in domain."""
        topics = self._knowledge_base.get(domain, {})

        known = [t for t, c in topics.items() if c >= 0.7]
        unknown = [t for t, c in topics.items() if c < 0.3]
        uncertain = [t for t, c in topics.items() if 0.3 <= c < 0.7]

        # Identify gaps (topics not yet encountered)
        gaps = []  # Would compare against expected curriculum

        return KnowledgeAssessment(
            domain=domain,
            known=known,
            unknown=unknown,
            uncertain=uncertain,
            gaps=gaps,
            confidence_by_topic=topics
        )

    def identify_learning_priorities(
        self,
        domain: str
    ) -> List[Tuple[str, float]]:
        """Identify learning priorities."""
        topics = self._knowledge_base.get(domain, {})

        # Prioritize unknown and uncertain topics
        priorities = [
            (topic, 1.0 - conf)
            for topic, conf in topics.items()
            if conf < 0.7
        ]

        # Sort by priority (inverse of confidence)
        priorities.sort(key=lambda x: x[1], reverse=True)

        return priorities


# =============================================================================
# LEARNING REGULATOR
# =============================================================================

class LearningRegulator:
    """Regulate learning process."""

    def __init__(
        self,
        strategy_manager: StrategyManager,
        knowledge_assessor: KnowledgeAssessor
    ):
        self._strategy_manager = strategy_manager
        self._knowledge_assessor = knowledge_assessor
        self._regulations: List[LearningRegulation] = []

    def regulate(
        self,
        domain: str,
        current_performance: float
    ) -> LearningRegulation:
        """Regulate learning based on performance."""
        assessment = self._knowledge_assessor.assess(domain)
        current_strategy = self._strategy_manager._current_strategy

        adjustments = []
        recommended = current_strategy
        reason = "Current strategy is effective"

        if current_performance < 0.3:
            # Poor performance - need strategy change
            adjustments.append("Consider switching to a different approach")
            adjustments.append("Break down material into smaller chunks")

            # Recommend different strategy
            new_strategy = self._strategy_manager.select_strategy("learning")
            if new_strategy and new_strategy.name != current_strategy:
                recommended = new_strategy.name
                reason = f"Performance ({current_performance:.1%}) suggests need for change"

        elif current_performance < 0.6:
            # Moderate performance - adjustments needed
            adjustments.append("Spend more time on uncertain topics")
            adjustments.append("Use active recall instead of passive review")

            if assessment.uncertain:
                adjustments.append(f"Focus on: {', '.join(assessment.uncertain[:3])}")

        else:
            # Good performance - continue with refinements
            if assessment.unknown:
                adjustments.append(f"Ready to tackle: {', '.join(assessment.unknown[:2])}")
            adjustments.append("Consider increasing difficulty")

        regulation = LearningRegulation(
            current_strategy=current_strategy or "none",
            recommended_strategy=recommended or "none",
            reason=reason,
            adjustments=adjustments,
            priority=1.0 - current_performance
        )

        self._regulations.append(regulation)

        return regulation


# =============================================================================
# COGNITIVE LOAD MANAGER
# =============================================================================

class CognitiveLoadManager:
    """Manage cognitive load."""

    def __init__(self, self_monitor: SelfMonitor):
        self._self_monitor = self_monitor
        self._task_complexity: Dict[str, float] = {}

    def register_task_complexity(
        self,
        task_type: str,
        complexity: float
    ) -> None:
        """Register task complexity."""
        self._task_complexity[task_type] = complexity

    def assess_load(
        self,
        active_tasks: List[str],
        context_complexity: float = 0.5
    ) -> CognitiveLoadAssessment:
        """Assess current cognitive load."""
        # Calculate intrinsic load (from task complexity)
        intrinsic = sum(
            self._task_complexity.get(task, 0.5)
            for task in active_tasks
        ) / max(1, len(active_tasks))

        # Extraneous load (from context)
        extraneous = context_complexity * 0.3

        # Germane load (productive cognitive effort)
        germane = min(0.3, 1.0 - intrinsic - extraneous)

        total_load = min(1.0, intrinsic + extraneous + germane)

        # Determine level
        if total_load < 0.2:
            level = CognitiveLoadLevel.MINIMAL
        elif total_load < 0.4:
            level = CognitiveLoadLevel.LOW
        elif total_load < 0.6:
            level = CognitiveLoadLevel.MODERATE
        elif total_load < 0.8:
            level = CognitiveLoadLevel.HIGH
        else:
            level = CognitiveLoadLevel.OVERLOADED

        # Generate recommendations
        recommendations = []

        if level == CognitiveLoadLevel.OVERLOADED:
            recommendations.append("Reduce number of active tasks")
            recommendations.append("Consider task delegation")
            recommendations.append("Take a break to reduce fatigue")
        elif level == CognitiveLoadLevel.HIGH:
            recommendations.append("Focus on one task at a time")
            recommendations.append("Minimize distractions")
        elif level == CognitiveLoadLevel.MINIMAL:
            recommendations.append("Capacity available for additional tasks")
            recommendations.append("Consider taking on more challenging work")

        # Update self-monitor
        self._self_monitor.update_state(cognitive_load=total_load)

        return CognitiveLoadAssessment(
            intrinsic_load=intrinsic,
            extraneous_load=extraneous,
            germane_load=germane,
            total_load=total_load,
            capacity=1.0 - total_load,
            level=level,
            recommendations=recommendations
        )


# =============================================================================
# META REASONER
# =============================================================================

class MetaReasoner:
    """Reason about reasoning."""

    def __init__(self):
        self._reasoning_traces: List[Dict[str, Any]] = []

    def record_reasoning(
        self,
        query: str,
        steps: List[str],
        conclusion: str,
        quality: float
    ) -> None:
        """Record reasoning process."""
        self._reasoning_traces.append({
            "query": query,
            "steps": steps,
            "conclusion": conclusion,
            "quality": quality,
            "timestamp": datetime.now()
        })

    def analyze_reasoning(
        self,
        query: str,
        steps: List[str],
        conclusion: str
    ) -> MetaReasoningResult:
        """Analyze reasoning quality."""
        conclusions = []
        improvements = []

        # Check step count
        if len(steps) < 2:
            conclusions.append("Reasoning may be too brief")
            improvements.append("Consider adding intermediate steps")
        elif len(steps) > 10:
            conclusions.append("Reasoning may be overly complex")
            improvements.append("Try to simplify reasoning chain")
        else:
            conclusions.append("Step count is reasonable")

        # Check for logical progression
        if steps:
            conclusions.append("Reasoning follows a structured approach")

        # Estimate quality
        quality = 0.5

        if len(steps) >= 2:
            quality += 0.1
        if len(steps) <= 10:
            quality += 0.1
        if conclusion:
            quality += 0.1

        # Check for common issues
        step_text = " ".join(steps).lower()

        if "assume" in step_text:
            improvements.append("Verify assumptions")
            quality -= 0.1

        if "maybe" in step_text or "might" in step_text:
            improvements.append("Strengthen uncertain claims with evidence")
            quality -= 0.05

        quality = max(0.0, min(1.0, quality))

        return MetaReasoningResult(
            query=query,
            reasoning_about="reasoning_process",
            conclusions=conclusions,
            quality_assessment=quality,
            improvements=improvements
        )

    def compare_reasoning(
        self,
        approach1: List[str],
        approach2: List[str]
    ) -> Dict[str, Any]:
        """Compare two reasoning approaches."""
        return {
            "approach1_steps": len(approach1),
            "approach2_steps": len(approach2),
            "more_detailed": "approach1" if len(approach1) > len(approach2) else "approach2",
            "recommendation": "Use the approach that best fits the problem complexity"
        }


# =============================================================================
# METACOGNITION ENGINE
# =============================================================================

class MetacognitionEngine:
    """
    Metacognition Engine for BAEL.

    Advanced metacognitive reasoning and self-awareness system.
    """

    def __init__(self):
        self._self_monitor = SelfMonitor()
        self._introspection = IntrospectionEngine(self._self_monitor)
        self._confidence_calibrator = ConfidenceCalibrator()
        self._strategy_manager = StrategyManager()
        self._knowledge_assessor = KnowledgeAssessor()
        self._learning_regulator = LearningRegulator(
            self._strategy_manager,
            self._knowledge_assessor
        )
        self._cognitive_load_manager = CognitiveLoadManager(self._self_monitor)
        self._meta_reasoner = MetaReasoner()

    # -------------------------------------------------------------------------
    # SELF MONITORING
    # -------------------------------------------------------------------------

    def update_cognitive_state(
        self,
        active_processes: Optional[Set[CognitiveProcess]] = None,
        cognitive_load: Optional[float] = None,
        attention_level: Optional[float] = None,
        fatigue_level: Optional[float] = None,
        confidence: Optional[float] = None
    ) -> CognitiveState:
        """Update cognitive state."""
        return self._self_monitor.update_state(
            active_processes,
            cognitive_load,
            attention_level,
            fatigue_level,
            confidence
        )

    def get_cognitive_state(self) -> CognitiveState:
        """Get current cognitive state."""
        return self._self_monitor.get_state()

    def detect_anomalies(self) -> List[str]:
        """Detect cognitive anomalies."""
        return self._self_monitor.detect_anomalies()

    # -------------------------------------------------------------------------
    # INTROSPECTION
    # -------------------------------------------------------------------------

    def introspect(
        self,
        query: str,
        process: Optional[CognitiveProcess] = None
    ) -> IntrospectionResult:
        """Perform introspection."""
        return self._introspection.introspect(query, process)

    def reflect(self, topic: str) -> List[str]:
        """Reflect on a topic."""
        return self._introspection.reflect(topic)

    # -------------------------------------------------------------------------
    # CONFIDENCE CALIBRATION
    # -------------------------------------------------------------------------

    def record_prediction(
        self,
        predicted_confidence: float,
        actual_outcome: float
    ) -> None:
        """Record prediction outcome for calibration."""
        self._confidence_calibrator.record_prediction(
            predicted_confidence,
            actual_outcome
        )

    def assess_confidence(
        self,
        task: str,
        predicted_confidence: float
    ) -> ConfidenceAssessment:
        """Assess confidence calibration."""
        return self._confidence_calibrator.assess(task, predicted_confidence)

    def get_calibration_curve(self) -> List[Tuple[float, float]]:
        """Get calibration curve."""
        return self._confidence_calibrator.get_calibration_curve()

    # -------------------------------------------------------------------------
    # STRATEGY MANAGEMENT
    # -------------------------------------------------------------------------

    def select_strategy(
        self,
        task_type: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Optional[Strategy]:
        """Select cognitive strategy."""
        return self._strategy_manager.select_strategy(task_type, constraints)

    def evaluate_strategy(
        self,
        strategy_name: str,
        task: str,
        success: bool,
        time_taken: float,
        lessons: Optional[List[str]] = None
    ) -> StrategyEvaluation:
        """Evaluate strategy effectiveness."""
        return self._strategy_manager.evaluate_strategy(
            strategy_name,
            task,
            success,
            time_taken,
            lessons
        )

    def get_all_strategies(self) -> List[Strategy]:
        """Get all available strategies."""
        return self._strategy_manager.get_all_strategies()

    # -------------------------------------------------------------------------
    # KNOWLEDGE ASSESSMENT
    # -------------------------------------------------------------------------

    def register_domain_knowledge(
        self,
        domain: str,
        topics: Dict[str, float]
    ) -> None:
        """Register domain knowledge."""
        self._knowledge_assessor.register_domain(domain, topics)

    def update_knowledge(
        self,
        domain: str,
        topic: str,
        confidence: float
    ) -> None:
        """Update knowledge confidence."""
        self._knowledge_assessor.update_knowledge(domain, topic, confidence)

    def assess_knowledge(self, domain: str) -> KnowledgeAssessment:
        """Assess knowledge in domain."""
        return self._knowledge_assessor.assess(domain)

    def get_learning_priorities(
        self,
        domain: str
    ) -> List[Tuple[str, float]]:
        """Get learning priorities."""
        return self._knowledge_assessor.identify_learning_priorities(domain)

    # -------------------------------------------------------------------------
    # LEARNING REGULATION
    # -------------------------------------------------------------------------

    def regulate_learning(
        self,
        domain: str,
        current_performance: float
    ) -> LearningRegulation:
        """Regulate learning process."""
        return self._learning_regulator.regulate(domain, current_performance)

    # -------------------------------------------------------------------------
    # COGNITIVE LOAD MANAGEMENT
    # -------------------------------------------------------------------------

    def register_task_complexity(
        self,
        task_type: str,
        complexity: float
    ) -> None:
        """Register task complexity."""
        self._cognitive_load_manager.register_task_complexity(
            task_type,
            complexity
        )

    def assess_cognitive_load(
        self,
        active_tasks: List[str],
        context_complexity: float = 0.5
    ) -> CognitiveLoadAssessment:
        """Assess cognitive load."""
        return self._cognitive_load_manager.assess_load(
            active_tasks,
            context_complexity
        )

    # -------------------------------------------------------------------------
    # META-REASONING
    # -------------------------------------------------------------------------

    def record_reasoning(
        self,
        query: str,
        steps: List[str],
        conclusion: str,
        quality: float
    ) -> None:
        """Record reasoning process."""
        self._meta_reasoner.record_reasoning(
            query,
            steps,
            conclusion,
            quality
        )

    def analyze_reasoning(
        self,
        query: str,
        steps: List[str],
        conclusion: str
    ) -> MetaReasoningResult:
        """Analyze reasoning quality."""
        return self._meta_reasoner.analyze_reasoning(
            query,
            steps,
            conclusion
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Metacognition Engine."""
    print("=" * 70)
    print("BAEL - METACOGNITION ENGINE DEMO")
    print("Advanced Metacognitive Reasoning and Self-Awareness")
    print("=" * 70)
    print()

    engine = MetacognitionEngine()

    # 1. Update Cognitive State
    print("1. UPDATE COGNITIVE STATE:")
    print("-" * 40)

    state = engine.update_cognitive_state(
        active_processes={
            CognitiveProcess.REASONING,
            CognitiveProcess.MEMORY
        },
        cognitive_load=0.6,
        attention_level=0.8,
        fatigue_level=0.2,
        confidence=0.7
    )

    print(f"   Active processes: {[p.value for p in state.active_processes]}")
    print(f"   Cognitive load: {state.cognitive_load:.1%}")
    print(f"   Attention: {state.attention_level:.1%}")
    print(f"   Confidence: {state.confidence:.1%}")
    print()

    # 2. Introspection
    print("2. INTROSPECTION:")
    print("-" * 40)

    result = engine.introspect(
        "How is my performance and confidence?",
        CognitiveProcess.REASONING
    )

    print("   Observations:")
    for obs in result.observations[:3]:
        print(f"     - {obs}")
    print("   Insights:")
    for insight in result.insights[:3]:
        print(f"     - {insight}")
    print()

    # 3. Detect Anomalies
    print("3. DETECT ANOMALIES:")
    print("-" * 40)

    # Set high load to trigger anomaly
    engine.update_cognitive_state(cognitive_load=0.95)
    anomalies = engine.detect_anomalies()

    if anomalies:
        for anomaly in anomalies:
            print(f"   ⚠️  {anomaly}")
    else:
        print("   ✓ No anomalies detected")
    print()

    # Reset load
    engine.update_cognitive_state(cognitive_load=0.5)

    # 4. Confidence Calibration
    print("4. CONFIDENCE CALIBRATION:")
    print("-" * 40)

    # Record some predictions
    engine.record_prediction(0.9, 1.0)  # Confident, correct
    engine.record_prediction(0.8, 1.0)  # Confident, correct
    engine.record_prediction(0.9, 0.0)  # Confident, wrong
    engine.record_prediction(0.5, 1.0)  # Uncertain, correct
    engine.record_prediction(0.7, 1.0)  # Moderate, correct

    assessment = engine.assess_confidence(
        "complex_analysis",
        predicted_confidence=0.85
    )

    print(f"   Task: {assessment.task}")
    print(f"   Predicted: {assessment.predicted_confidence:.1%}")
    print(f"   Historical: {assessment.actual_performance:.1%}")
    print(f"   State: {assessment.state.value}")
    print("   Recommendations:")
    for rec in assessment.recommendations:
        print(f"     - {rec}")
    print()

    # 5. Strategy Selection
    print("5. STRATEGY SELECTION:")
    print("-" * 40)

    strategy = engine.select_strategy(
        "learning",
        constraints={"max_cost": 0.8}
    )

    if strategy:
        print(f"   Selected: {strategy.name}")
        print(f"   Type: {strategy.strategy_type.value}")
        print(f"   Effectiveness: {strategy.effectiveness:.1%}")
        print(f"   Cost: {strategy.cost:.1%}")
        print(f"   Description: {strategy.description}")
    print()

    # 6. Strategy Evaluation
    print("6. STRATEGY EVALUATION:")
    print("-" * 40)

    evaluation = engine.evaluate_strategy(
        strategy.name if strategy else "default",
        "learn_new_concept",
        success=True,
        time_taken=120.0,
        lessons=["Visual aids helped", "Practice was key"]
    )

    print(f"   Strategy: {evaluation.strategy_id}")
    print(f"   Task: {evaluation.task}")
    print(f"   Success: {evaluation.success}")
    print(f"   Lessons: {', '.join(evaluation.lessons)}")
    print()

    # 7. Knowledge Assessment
    print("7. KNOWLEDGE ASSESSMENT:")
    print("-" * 40)

    engine.register_domain_knowledge(
        "machine_learning",
        {
            "linear_regression": 0.9,
            "logistic_regression": 0.85,
            "neural_networks": 0.6,
            "transformers": 0.3,
            "reinforcement_learning": 0.2
        }
    )

    knowledge = engine.assess_knowledge("machine_learning")

    print(f"   Domain: {knowledge.domain}")
    print(f"   Known: {', '.join(knowledge.known)}")
    print(f"   Unknown: {', '.join(knowledge.unknown)}")
    print(f"   Uncertain: {', '.join(knowledge.uncertain)}")
    print()

    # 8. Learning Priorities
    print("8. LEARNING PRIORITIES:")
    print("-" * 40)

    priorities = engine.get_learning_priorities("machine_learning")

    for topic, priority in priorities:
        print(f"   {topic}: priority {priority:.1%}")
    print()

    # 9. Learning Regulation
    print("9. LEARNING REGULATION:")
    print("-" * 40)

    regulation = engine.regulate_learning(
        "machine_learning",
        current_performance=0.45
    )

    print(f"   Current strategy: {regulation.current_strategy}")
    print(f"   Recommended: {regulation.recommended_strategy}")
    print(f"   Reason: {regulation.reason}")
    print("   Adjustments:")
    for adj in regulation.adjustments:
        print(f"     - {adj}")
    print()

    # 10. Cognitive Load Assessment
    print("10. COGNITIVE LOAD ASSESSMENT:")
    print("-" * 40)

    engine.register_task_complexity("analysis", 0.7)
    engine.register_task_complexity("writing", 0.5)
    engine.register_task_complexity("review", 0.3)

    load = engine.assess_cognitive_load(
        active_tasks=["analysis", "writing"],
        context_complexity=0.4
    )

    print(f"   Intrinsic load: {load.intrinsic_load:.1%}")
    print(f"   Extraneous load: {load.extraneous_load:.1%}")
    print(f"   Germane load: {load.germane_load:.1%}")
    print(f"   Total: {load.total_load:.1%}")
    print(f"   Level: {load.level.value}")
    print(f"   Capacity: {load.capacity:.1%}")
    print()

    # 11. Meta-Reasoning
    print("11. META-REASONING:")
    print("-" * 40)

    reasoning_result = engine.analyze_reasoning(
        query="Should we adopt new technology?",
        steps=[
            "Identify current pain points",
            "Evaluate available options",
            "Consider costs and benefits",
            "Assess implementation risks",
            "Make recommendation"
        ],
        conclusion="Adopt with phased rollout"
    )

    print(f"   Quality: {reasoning_result.quality_assessment:.1%}")
    print("   Conclusions:")
    for conclusion in reasoning_result.conclusions:
        print(f"     - {conclusion}")
    print("   Improvements:")
    for improvement in reasoning_result.improvements:
        print(f"     - {improvement}")
    print()

    # 12. Reflection
    print("12. REFLECTION:")
    print("-" * 40)

    reflections = engine.reflect("performance")
    for reflection in reflections:
        print(f"   - {reflection}")
    print()

    # 13. All Strategies
    print("13. AVAILABLE STRATEGIES:")
    print("-" * 40)

    strategies = engine.get_all_strategies()
    for s in strategies[:5]:
        print(f"   {s.name}: {s.strategy_type.value} ({s.effectiveness:.0%} eff)")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Metacognition Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
