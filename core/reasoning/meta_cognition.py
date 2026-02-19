"""
BAEL Meta Cognition
====================

Thinking about thinking - cognitive self-awareness.
Enables monitoring and regulation of cognitive processes.

Features:
- Cognitive state monitoring
- Confidence assessment
- Uncertainty quantification
- Strategy selection
- Learning monitoring
"""

import asyncio
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class CognitiveProcess(Enum):
    """Types of cognitive processes."""
    PERCEPTION = "perception"
    ATTENTION = "attention"
    MEMORY = "memory"
    REASONING = "reasoning"
    PLANNING = "planning"
    EXECUTION = "execution"
    EVALUATION = "evaluation"


class ResourceLevel(Enum):
    """Cognitive resource levels."""
    DEPLETED = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    OPTIMAL = 4


class StrategyType(Enum):
    """Meta-cognitive strategies."""
    FOCUS = "focus"  # Concentrate resources
    DISTRIBUTE = "distribute"  # Spread attention
    DELEGATE = "delegate"  # Offload to tools
    SIMPLIFY = "simplify"  # Reduce complexity
    DECOMPOSE = "decompose"  # Break into parts
    ANALOGIZE = "analogize"  # Use similar patterns
    BACKTRACK = "backtrack"  # Revise approach


@dataclass
class CognitiveState:
    """Current cognitive state."""
    # Process states
    process_states: Dict[CognitiveProcess, float] = field(default_factory=dict)

    # Resources
    attention_level: float = 1.0
    working_memory_load: float = 0.0
    processing_depth: float = 0.5

    # Performance
    current_task_difficulty: float = 0.5
    estimated_completion: float = 0.0

    # Meta
    self_awareness: float = 0.8

    # Timestamp
    measured_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.process_states:
            self.process_states = {p: 0.5 for p in CognitiveProcess}


@dataclass
class ConfidenceAssessment:
    """Assessment of confidence in an output."""
    overall_confidence: float = 0.5

    # Breakdown
    knowledge_confidence: float = 0.5  # Domain knowledge
    reasoning_confidence: float = 0.5  # Logic quality
    execution_confidence: float = 0.5  # Implementation

    # Calibration
    historical_accuracy: float = 0.5
    calibration_offset: float = 0.0

    # Uncertainty sources
    uncertainty_sources: List[str] = field(default_factory=list)

    def calibrated_confidence(self) -> float:
        """Get calibrated confidence score."""
        raw = self.overall_confidence
        # Apply historical calibration
        calibrated = raw - self.calibration_offset
        # Adjust based on historical accuracy
        adjusted = calibrated * (0.5 + 0.5 * self.historical_accuracy)
        return max(0.0, min(1.0, adjusted))


@dataclass
class UncertaintyModel:
    """Model of uncertainty in predictions."""
    # Types of uncertainty
    aleatoric: float = 0.0  # Inherent randomness
    epistemic: float = 0.0  # Knowledge gaps

    # Sources
    data_uncertainty: float = 0.0
    model_uncertainty: float = 0.0
    distribution_shift: float = 0.0

    # Confidence intervals
    lower_bound: float = 0.0
    upper_bound: float = 1.0

    def total_uncertainty(self) -> float:
        """Calculate total uncertainty."""
        return math.sqrt(self.aleatoric ** 2 + self.epistemic ** 2)

    def confidence_interval(self, level: float = 0.95) -> Tuple[float, float]:
        """Get confidence interval."""
        z = 1.96 if level == 0.95 else 2.58  # 95% or 99%
        total = self.total_uncertainty()
        margin = z * total
        return (
            max(0, self.lower_bound - margin),
            min(1, self.upper_bound + margin),
        )


class MetaCognition:
    """
    Meta-cognitive system for BAEL.

    Monitors and regulates cognitive processes.
    """

    def __init__(self):
        # Current state
        self.state = CognitiveState()

        # History
        self._state_history: deque = deque(maxlen=1000)
        self._performance_history: List[Tuple[float, float]] = []  # (predicted, actual)

        # Strategy
        self._active_strategy: Optional[StrategyType] = None

        # Calibration
        self._calibration_data: List[Tuple[float, bool]] = []

        # Stats
        self.stats = {
            "assessments": 0,
            "strategy_changes": 0,
            "calibrations": 0,
        }

    def assess_state(self) -> CognitiveState:
        """Assess current cognitive state."""
        state = CognitiveState()

        # Assess each process
        for process in CognitiveProcess:
            state.process_states[process] = self._assess_process(process)

        # Calculate aggregate metrics
        state.attention_level = state.process_states[CognitiveProcess.ATTENTION]
        state.working_memory_load = self._estimate_memory_load()
        state.processing_depth = state.process_states[CognitiveProcess.REASONING]

        # Self-awareness (how reliable is this assessment?)
        state.self_awareness = self._calculate_self_awareness()

        self.state = state
        self._state_history.append(state)
        self.stats["assessments"] += 1

        return state

    def _assess_process(self, process: CognitiveProcess) -> float:
        """Assess a specific cognitive process."""
        # Placeholder - in production would use actual metrics
        base = 0.5

        if process == CognitiveProcess.ATTENTION:
            # Check for recent distractions
            base = 0.7
        elif process == CognitiveProcess.MEMORY:
            # Check working memory utilization
            base = 0.6
        elif process == CognitiveProcess.REASONING:
            # Check reasoning chain quality
            base = 0.65
        elif process == CognitiveProcess.EXECUTION:
            # Check recent execution success
            base = 0.75

        return base

    def _estimate_memory_load(self) -> float:
        """Estimate working memory load."""
        # Placeholder - would track actual active items
        return 0.4

    def _calculate_self_awareness(self) -> float:
        """Calculate reliability of self-assessment."""
        if len(self._performance_history) < 5:
            return 0.5

        # Compare predictions to actuals
        recent = self._performance_history[-20:]
        errors = [abs(p - a) for p, a in recent]
        avg_error = sum(errors) / len(errors)

        # Lower error = higher self-awareness
        return max(0.0, 1.0 - avg_error)

    def assess_confidence(
        self,
        output: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConfidenceAssessment:
        """
        Assess confidence in an output.

        Args:
            output: Output to assess
            context: Context information

        Returns:
            Confidence assessment
        """
        context = context or {}

        assessment = ConfidenceAssessment()

        # Knowledge confidence
        domain = context.get("domain", "general")
        assessment.knowledge_confidence = self._assess_domain_knowledge(domain)

        # Reasoning confidence
        reasoning_steps = context.get("reasoning_steps", 0)
        assessment.reasoning_confidence = min(1.0, 0.5 + reasoning_steps * 0.1)

        # Execution confidence
        assessment.execution_confidence = self.state.process_states.get(
            CognitiveProcess.EXECUTION, 0.5
        )

        # Overall confidence
        assessment.overall_confidence = (
            0.4 * assessment.knowledge_confidence +
            0.35 * assessment.reasoning_confidence +
            0.25 * assessment.execution_confidence
        )

        # Calibration
        assessment.historical_accuracy = self._get_historical_accuracy()
        assessment.calibration_offset = self._get_calibration_offset()

        # Uncertainty sources
        if assessment.knowledge_confidence < 0.5:
            assessment.uncertainty_sources.append("domain_knowledge_gap")
        if reasoning_steps < 3:
            assessment.uncertainty_sources.append("limited_reasoning")

        return assessment

    def _assess_domain_knowledge(self, domain: str) -> float:
        """Assess knowledge in a domain."""
        # Placeholder - would check actual knowledge base
        domain_scores = {
            "programming": 0.9,
            "general": 0.7,
            "specialized": 0.5,
            "unknown": 0.3,
        }
        return domain_scores.get(domain, 0.5)

    def _get_historical_accuracy(self) -> float:
        """Get historical prediction accuracy."""
        if len(self._calibration_data) < 10:
            return 0.5

        recent = self._calibration_data[-50:]
        correct = sum(1 for conf, actual in recent if (conf > 0.5) == actual)
        return correct / len(recent)

    def _get_calibration_offset(self) -> float:
        """Get calibration offset (overconfidence/underconfidence)."""
        if len(self._calibration_data) < 10:
            return 0.0

        recent = self._calibration_data[-50:]
        avg_confidence = sum(conf for conf, _ in recent) / len(recent)
        accuracy = self._get_historical_accuracy()

        return avg_confidence - accuracy

    def quantify_uncertainty(
        self,
        prediction: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> UncertaintyModel:
        """
        Quantify uncertainty in a prediction.

        Args:
            prediction: Prediction to assess
            context: Context information

        Returns:
            Uncertainty model
        """
        context = context or {}

        model = UncertaintyModel()

        # Aleatoric uncertainty (irreducible)
        data_quality = context.get("data_quality", 0.8)
        model.aleatoric = 1.0 - data_quality

        # Epistemic uncertainty (knowledge gaps)
        domain = context.get("domain", "general")
        knowledge = self._assess_domain_knowledge(domain)
        model.epistemic = 1.0 - knowledge

        # Data uncertainty
        sample_size = context.get("sample_size", 100)
        model.data_uncertainty = 1.0 / math.sqrt(max(1, sample_size))

        # Model uncertainty
        model.model_uncertainty = 0.1  # Base model uncertainty

        # Distribution shift
        is_novel = context.get("novel_situation", False)
        model.distribution_shift = 0.3 if is_novel else 0.05

        return model

    def select_strategy(
        self,
        task_difficulty: float,
        time_available: float,
        importance: float,
    ) -> StrategyType:
        """
        Select appropriate cognitive strategy.

        Args:
            task_difficulty: Task difficulty (0-1)
            time_available: Time available (0-1, normalized)
            importance: Task importance (0-1)

        Returns:
            Recommended strategy
        """
        # Assess current resources
        resources = self.state.attention_level
        memory_load = self.state.working_memory_load

        # Decision logic
        if task_difficulty > 0.8 and resources < 0.5:
            strategy = StrategyType.DECOMPOSE
        elif memory_load > 0.8:
            strategy = StrategyType.DELEGATE
        elif task_difficulty > 0.7 and time_available < 0.3:
            strategy = StrategyType.SIMPLIFY
        elif importance > 0.8:
            strategy = StrategyType.FOCUS
        elif task_difficulty < 0.3:
            strategy = StrategyType.DISTRIBUTE
        else:
            strategy = StrategyType.ANALOGIZE

        if strategy != self._active_strategy:
            self.stats["strategy_changes"] += 1

        self._active_strategy = strategy

        logger.debug(f"Selected strategy: {strategy.value}")

        return strategy

    def record_outcome(
        self,
        predicted_confidence: float,
        actual_success: bool,
    ) -> None:
        """Record prediction outcome for calibration."""
        self._calibration_data.append((predicted_confidence, actual_success))
        self._performance_history.append((predicted_confidence, 1.0 if actual_success else 0.0))

        # Limit history size
        if len(self._calibration_data) > 1000:
            self._calibration_data = self._calibration_data[-1000:]

        self.stats["calibrations"] += 1

    def should_seek_help(
        self,
        confidence: ConfidenceAssessment,
        threshold: float = 0.4,
    ) -> bool:
        """Determine if external help should be sought."""
        calibrated = confidence.calibrated_confidence()

        if calibrated < threshold:
            return True

        if "domain_knowledge_gap" in confidence.uncertainty_sources:
            return True

        return False

    def get_cognitive_profile(self) -> Dict[str, Any]:
        """Get comprehensive cognitive profile."""
        return {
            "state": {
                "attention": self.state.attention_level,
                "memory_load": self.state.working_memory_load,
                "processing_depth": self.state.processing_depth,
                "self_awareness": self.state.self_awareness,
            },
            "processes": {
                p.value: self.state.process_states.get(p, 0.5)
                for p in CognitiveProcess
            },
            "calibration": {
                "accuracy": self._get_historical_accuracy(),
                "offset": self._get_calibration_offset(),
            },
            "strategy": self._active_strategy.value if self._active_strategy else None,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get meta-cognition statistics."""
        return {
            **self.stats,
            "history_size": len(self._state_history),
            "calibration_samples": len(self._calibration_data),
        }


def demo():
    """Demonstrate meta-cognition."""
    print("=" * 60)
    print("BAEL Meta Cognition Demo")
    print("=" * 60)

    meta = MetaCognition()

    # Assess cognitive state
    print("\nAssessing cognitive state...")
    state = meta.assess_state()

    print(f"  Attention level: {state.attention_level:.2f}")
    print(f"  Memory load: {state.working_memory_load:.2f}")
    print(f"  Self-awareness: {state.self_awareness:.2f}")

    print(f"\n  Process states:")
    for process, level in state.process_states.items():
        print(f"    {process.value}: {level:.2f}")

    # Assess confidence
    print("\nAssessing confidence...")
    confidence = meta.assess_confidence(
        output="Generated code solution",
        context={"domain": "programming", "reasoning_steps": 5},
    )

    print(f"  Overall: {confidence.overall_confidence:.2f}")
    print(f"  Calibrated: {confidence.calibrated_confidence():.2f}")
    print(f"  Knowledge: {confidence.knowledge_confidence:.2f}")
    print(f"  Reasoning: {confidence.reasoning_confidence:.2f}")

    if confidence.uncertainty_sources:
        print(f"  Uncertainties: {confidence.uncertainty_sources}")

    # Quantify uncertainty
    print("\nQuantifying uncertainty...")
    uncertainty = meta.quantify_uncertainty(
        prediction=0.8,
        context={"domain": "general", "sample_size": 50, "novel_situation": True},
    )

    print(f"  Total uncertainty: {uncertainty.total_uncertainty():.2f}")
    print(f"  Aleatoric: {uncertainty.aleatoric:.2f}")
    print(f"  Epistemic: {uncertainty.epistemic:.2f}")

    lower, upper = uncertainty.confidence_interval()
    print(f"  95% CI: [{lower:.2f}, {upper:.2f}]")

    # Select strategy
    print("\nSelecting strategy...")
    strategy = meta.select_strategy(
        task_difficulty=0.75,
        time_available=0.5,
        importance=0.8,
    )
    print(f"  Strategy: {strategy.value}")

    # Record some outcomes
    print("\nRecording outcomes for calibration...")
    meta.record_outcome(0.8, True)
    meta.record_outcome(0.9, True)
    meta.record_outcome(0.7, False)
    meta.record_outcome(0.6, True)

    # Check if help needed
    should_help = meta.should_seek_help(confidence)
    print(f"\nShould seek help: {should_help}")

    # Get profile
    print("\nCognitive profile:")
    profile = meta.get_cognitive_profile()
    print(f"  {profile}")

    print(f"\nStats: {meta.get_stats()}")


if __name__ == "__main__":
    demo()
