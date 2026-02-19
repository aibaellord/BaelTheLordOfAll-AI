"""
BAEL Reflection Loop
=====================

Iterative self-improvement through reflection.
Enables learning from experience and adaptation.

Features:
- Experience reflection
- Learning extraction
- Strategy adaptation
- Performance monitoring
- Continuous improvement
"""

import asyncio
import hashlib
import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ReflectionDepth(Enum):
    """Depth of reflection."""
    SHALLOW = 1  # Quick review
    MODERATE = 2  # Standard analysis
    DEEP = 3  # Thorough examination
    COMPREHENSIVE = 4  # Full investigation


class LearningType(Enum):
    """Types of learning outcomes."""
    PROCEDURAL = "procedural"  # How to do something
    DECLARATIVE = "declarative"  # Facts/knowledge
    CONDITIONAL = "conditional"  # When to apply
    STRATEGIC = "strategic"  # Approach selection
    META = "meta"  # About learning itself


class AdaptationType(Enum):
    """Types of adaptation."""
    PARAMETER = "parameter"  # Adjust values
    STRATEGY = "strategy"  # Change approach
    REPRESENTATION = "representation"  # Change understanding
    GOAL = "goal"  # Modify objectives


@dataclass
class Experience:
    """A recorded experience."""
    id: str
    task: str

    # Outcome
    success: bool
    result: Any = None
    error: Optional[str] = None

    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    actions_taken: List[str] = field(default_factory=list)

    # Metrics
    duration_ms: float = 0.0
    confidence: float = 0.5
    difficulty: float = 0.5

    # Reflection
    reflected: bool = False
    learnings: List[str] = field(default_factory=list)

    # Timestamp
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass
class LearningOutcome:
    """An outcome from reflection."""
    id: str
    learning_type: LearningType

    # Content
    insight: str
    evidence: List[str] = field(default_factory=list)

    # Applicability
    applicable_contexts: List[str] = field(default_factory=list)
    confidence: float = 0.5

    # Usage
    times_applied: int = 0
    success_when_applied: int = 0

    # Metadata
    learned_at: datetime = field(default_factory=datetime.now)
    source_experiences: List[str] = field(default_factory=list)


@dataclass
class AdaptationStrategy:
    """A strategy for adaptation."""
    id: str
    adaptation_type: AdaptationType

    # Change
    description: str
    old_value: Any = None
    new_value: Any = None

    # Rationale
    reason: str = ""
    expected_improvement: float = 0.0

    # Status
    applied: bool = False
    successful: bool = False

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReflectionCycle:
    """A cycle of reflection."""
    id: str
    trigger: str
    depth: ReflectionDepth

    # Input
    experiences: List[str] = field(default_factory=list)

    # Output
    learnings: List[LearningOutcome] = field(default_factory=list)
    adaptations: List[AdaptationStrategy] = field(default_factory=list)

    # Metrics
    patterns_found: int = 0
    improvements_identified: int = 0

    # Status
    completed: bool = False

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ReflectionLoop:
    """
    Reflection loop for BAEL.

    Enables continuous learning through reflection.
    """

    def __init__(
        self,
        auto_reflect_threshold: int = 10,
    ):
        self.auto_reflect_threshold = auto_reflect_threshold

        # Experience storage
        self._experiences: Dict[str, Experience] = {}
        self._unreflected: List[str] = []

        # Learnings
        self._learnings: Dict[str, LearningOutcome] = {}

        # Adaptations
        self._adaptations: Dict[str, AdaptationStrategy] = {}

        # Reflection history
        self._cycles: List[ReflectionCycle] = []

        # Patterns detected
        self._patterns: Dict[str, int] = {}

        # Stats
        self.stats = {
            "experiences_recorded": 0,
            "reflections_performed": 0,
            "learnings_generated": 0,
            "adaptations_made": 0,
        }

    def record_experience(
        self,
        task: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        actions: Optional[List[str]] = None,
        duration_ms: float = 0.0,
        confidence: float = 0.5,
    ) -> Experience:
        """
        Record an experience.

        Args:
            task: Task performed
            success: Whether successful
            result: Task result
            error: Error if failed
            context: Task context
            actions: Actions taken
            duration_ms: Duration
            confidence: Confidence level

        Returns:
            Recorded experience
        """
        exp_id = hashlib.md5(
            f"{task}:{datetime.now()}".encode()
        ).hexdigest()[:12]

        experience = Experience(
            id=exp_id,
            task=task,
            success=success,
            result=result,
            error=error,
            context=context or {},
            actions_taken=actions or [],
            duration_ms=duration_ms,
            confidence=confidence,
        )

        self._experiences[exp_id] = experience
        self._unreflected.append(exp_id)
        self.stats["experiences_recorded"] += 1

        # Auto-reflect if threshold reached
        if len(self._unreflected) >= self.auto_reflect_threshold:
            asyncio.create_task(self.reflect())

        return experience

    async def reflect(
        self,
        depth: ReflectionDepth = ReflectionDepth.MODERATE,
        focus_on_failures: bool = True,
    ) -> ReflectionCycle:
        """
        Perform a reflection cycle.

        Args:
            depth: Reflection depth
            focus_on_failures: Focus on failed experiences

        Returns:
            Reflection cycle results
        """
        cycle_id = hashlib.md5(
            f"reflect:{datetime.now()}".encode()
        ).hexdigest()[:12]

        cycle = ReflectionCycle(
            id=cycle_id,
            trigger="scheduled" if len(self._unreflected) >= self.auto_reflect_threshold else "manual",
            depth=depth,
            experiences=self._unreflected.copy(),
        )

        # Get experiences to reflect on
        experiences = [
            self._experiences[eid]
            for eid in self._unreflected
            if eid in self._experiences
        ]

        if focus_on_failures:
            # Prioritize failures
            experiences.sort(key=lambda e: (not e.success, -e.confidence))

        # Analyze experiences
        learnings = await self._analyze_experiences(experiences, depth)
        cycle.learnings = learnings

        for learning in learnings:
            self._learnings[learning.id] = learning
            self.stats["learnings_generated"] += 1

        # Identify patterns
        patterns = self._identify_patterns(experiences)
        cycle.patterns_found = len(patterns)

        # Generate adaptations
        adaptations = await self._generate_adaptations(learnings, patterns)
        cycle.adaptations = adaptations

        for adaptation in adaptations:
            self._adaptations[adaptation.id] = adaptation

        # Mark experiences as reflected
        for exp_id in self._unreflected:
            if exp_id in self._experiences:
                self._experiences[exp_id].reflected = True

        self._unreflected.clear()

        # Complete cycle
        cycle.completed = True
        cycle.completed_at = datetime.now()
        cycle.improvements_identified = len(adaptations)

        self._cycles.append(cycle)
        self.stats["reflections_performed"] += 1

        logger.info(
            f"Reflection cycle {cycle_id}: "
            f"{len(learnings)} learnings, {len(adaptations)} adaptations"
        )

        return cycle

    async def _analyze_experiences(
        self,
        experiences: List[Experience],
        depth: ReflectionDepth,
    ) -> List[LearningOutcome]:
        """Analyze experiences to extract learnings."""
        learnings = []

        # Group by task type
        by_task: Dict[str, List[Experience]] = {}
        for exp in experiences:
            task_type = exp.task.split()[0] if exp.task else "unknown"
            if task_type not in by_task:
                by_task[task_type] = []
            by_task[task_type].append(exp)

        # Analyze each group
        for task_type, task_exps in by_task.items():
            successes = [e for e in task_exps if e.success]
            failures = [e for e in task_exps if not e.success]

            # Success patterns
            if len(successes) >= 2:
                # Find common actions
                if all(e.actions_taken for e in successes):
                    common_actions = set(successes[0].actions_taken)
                    for exp in successes[1:]:
                        common_actions &= set(exp.actions_taken)

                    if common_actions:
                        learning = LearningOutcome(
                            id=f"learn_{task_type}_success",
                            learning_type=LearningType.PROCEDURAL,
                            insight=f"For {task_type}, these actions correlate with success: {list(common_actions)[:3]}",
                            applicable_contexts=[task_type],
                            confidence=len(successes) / len(task_exps),
                            source_experiences=[e.id for e in successes],
                        )
                        learnings.append(learning)

            # Failure analysis
            if failures:
                # Group errors
                error_types: Dict[str, int] = {}
                for exp in failures:
                    error = exp.error or "unknown_error"
                    error_type = error.split(":")[0]
                    error_types[error_type] = error_types.get(error_type, 0) + 1

                # Most common error
                if error_types:
                    top_error = max(error_types, key=lambda x: error_types[x])

                    learning = LearningOutcome(
                        id=f"learn_{task_type}_error",
                        learning_type=LearningType.CONDITIONAL,
                        insight=f"For {task_type}, watch for {top_error} (occurred {error_types[top_error]} times)",
                        applicable_contexts=[task_type],
                        confidence=0.7,
                        source_experiences=[e.id for e in failures],
                    )
                    learnings.append(learning)

            # Deep analysis
            if depth.value >= ReflectionDepth.DEEP.value:
                # Analyze confidence calibration
                avg_confidence = sum(e.confidence for e in task_exps) / len(task_exps)
                success_rate = len(successes) / len(task_exps) if task_exps else 0

                if abs(avg_confidence - success_rate) > 0.2:
                    calibration = "overconfident" if avg_confidence > success_rate else "underconfident"

                    learning = LearningOutcome(
                        id=f"learn_{task_type}_calibration",
                        learning_type=LearningType.META,
                        insight=f"For {task_type}, currently {calibration} by {abs(avg_confidence - success_rate):.0%}",
                        applicable_contexts=[task_type],
                        confidence=0.8,
                    )
                    learnings.append(learning)

        return learnings

    def _identify_patterns(
        self,
        experiences: List[Experience],
    ) -> Dict[str, int]:
        """Identify patterns in experiences."""
        patterns = {}

        # Action sequences
        for exp in experiences:
            if len(exp.actions_taken) >= 2:
                for i in range(len(exp.actions_taken) - 1):
                    pattern = f"{exp.actions_taken[i]}->{exp.actions_taken[i+1]}"
                    patterns[pattern] = patterns.get(pattern, 0) + 1

        # Context patterns
        context_values: Dict[str, List] = {}
        for exp in experiences:
            for key, value in exp.context.items():
                if key not in context_values:
                    context_values[key] = []
                context_values[key].append((value, exp.success))

        # Check for context-success correlations
        for key, values in context_values.items():
            if len(values) >= 3:
                successes = [v for v, s in values if s]
                if successes:
                    patterns[f"context:{key}"] = len(successes)

        # Update global patterns
        for pattern, count in patterns.items():
            self._patterns[pattern] = self._patterns.get(pattern, 0) + count

        return patterns

    async def _generate_adaptations(
        self,
        learnings: List[LearningOutcome],
        patterns: Dict[str, int],
    ) -> List[AdaptationStrategy]:
        """Generate adaptation strategies."""
        adaptations = []

        # From learnings
        for learning in learnings:
            if learning.learning_type == LearningType.META:
                # Calibration adjustment
                if "overconfident" in learning.insight:
                    adaptation = AdaptationStrategy(
                        id=f"adapt_calibration_{len(adaptations)}",
                        adaptation_type=AdaptationType.PARAMETER,
                        description="Reduce confidence in predictions",
                        old_value=1.0,
                        new_value=0.8,
                        reason=learning.insight,
                        expected_improvement=0.1,
                    )
                    adaptations.append(adaptation)

            elif learning.learning_type == LearningType.CONDITIONAL:
                # Add validation step
                adaptation = AdaptationStrategy(
                    id=f"adapt_validation_{len(adaptations)}",
                    adaptation_type=AdaptationType.STRATEGY,
                    description="Add extra validation for error-prone tasks",
                    reason=learning.insight,
                    expected_improvement=0.15,
                )
                adaptations.append(adaptation)

        # From patterns
        if patterns:
            top_pattern = max(patterns, key=lambda x: patterns[x])
            if patterns[top_pattern] >= 3:
                adaptation = AdaptationStrategy(
                    id=f"adapt_pattern_{len(adaptations)}",
                    adaptation_type=AdaptationType.STRATEGY,
                    description=f"Optimize for common pattern: {top_pattern}",
                    reason=f"Pattern occurred {patterns[top_pattern]} times",
                    expected_improvement=0.2,
                )
                adaptations.append(adaptation)

        return adaptations

    def apply_adaptation(
        self,
        adaptation_id: str,
    ) -> bool:
        """Apply an adaptation strategy."""
        if adaptation_id not in self._adaptations:
            return False

        adaptation = self._adaptations[adaptation_id]

        # In production, would actually apply the change
        adaptation.applied = True
        adaptation.successful = True  # Assumed for demo

        self.stats["adaptations_made"] += 1

        logger.info(f"Applied adaptation: {adaptation.description}")

        return True

    def get_applicable_learnings(
        self,
        context: str,
    ) -> List[LearningOutcome]:
        """Get learnings applicable to a context."""
        applicable = []

        for learning in self._learnings.values():
            if context in learning.applicable_contexts:
                applicable.append(learning)
            elif any(c in context for c in learning.applicable_contexts):
                applicable.append(learning)

        # Sort by confidence and usage success
        applicable.sort(
            key=lambda l: (
                l.success_when_applied / max(l.times_applied, 1),
                l.confidence
            ),
            reverse=True,
        )

        return applicable

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary from experiences."""
        if not self._experiences:
            return {}

        experiences = list(self._experiences.values())

        success_rate = sum(1 for e in experiences if e.success) / len(experiences)
        avg_confidence = sum(e.confidence for e in experiences) / len(experiences)
        avg_duration = sum(e.duration_ms for e in experiences) / len(experiences)

        # By task type
        by_task: Dict[str, Dict] = {}
        for exp in experiences:
            task_type = exp.task.split()[0] if exp.task else "unknown"
            if task_type not in by_task:
                by_task[task_type] = {"success": 0, "total": 0}
            by_task[task_type]["total"] += 1
            if exp.success:
                by_task[task_type]["success"] += 1

        return {
            "overall_success_rate": success_rate,
            "avg_confidence": avg_confidence,
            "avg_duration_ms": avg_duration,
            "calibration_error": abs(success_rate - avg_confidence),
            "by_task": {
                k: v["success"] / v["total"]
                for k, v in by_task.items()
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get reflection loop statistics."""
        return {
            **self.stats,
            "total_experiences": len(self._experiences),
            "unreflected": len(self._unreflected),
            "learnings": len(self._learnings),
            "adaptations": len(self._adaptations),
            "patterns": len(self._patterns),
        }


def demo():
    """Demonstrate reflection loop."""
    import asyncio

    print("=" * 60)
    print("BAEL Reflection Loop Demo")
    print("=" * 60)

    async def run_demo():
        loop = ReflectionLoop(auto_reflect_threshold=5)

        # Record some experiences
        print("\nRecording experiences...")

        loop.record_experience(
            task="code debugging",
            success=True,
            actions=["read_error", "locate_line", "fix_bug", "test"],
            duration_ms=500,
            confidence=0.8,
        )

        loop.record_experience(
            task="code debugging",
            success=True,
            actions=["read_error", "check_logs", "fix_bug", "test"],
            duration_ms=700,
            confidence=0.7,
        )

        loop.record_experience(
            task="code debugging",
            success=False,
            error="timeout: unable to reproduce",
            actions=["read_error", "check_logs"],
            duration_ms=1000,
            confidence=0.6,
        )

        loop.record_experience(
            task="api integration",
            success=True,
            actions=["read_docs", "write_code", "test"],
            duration_ms=800,
            confidence=0.9,
        )

        loop.record_experience(
            task="api integration",
            success=False,
            error="auth: invalid token format",
            actions=["read_docs", "write_code"],
            duration_ms=600,
            confidence=0.8,
        )

        print(f"  Recorded {loop.stats['experiences_recorded']} experiences")

        # Perform reflection
        print("\nPerforming reflection...")
        cycle = await loop.reflect(depth=ReflectionDepth.DEEP)

        print(f"\nReflection cycle results:")
        print(f"  Experiences analyzed: {len(cycle.experiences)}")
        print(f"  Patterns found: {cycle.patterns_found}")
        print(f"  Learnings: {len(cycle.learnings)}")
        print(f"  Adaptations: {len(cycle.adaptations)}")

        print(f"\nLearnings:")
        for learning in cycle.learnings:
            print(f"  [{learning.learning_type.value}] {learning.insight}")

        print(f"\nAdaptations:")
        for adaptation in cycle.adaptations:
            print(f"  [{adaptation.adaptation_type.value}] {adaptation.description}")

            # Apply adaptation
            loop.apply_adaptation(adaptation.id)

        # Get applicable learnings
        print("\nApplicable learnings for 'debugging':")
        applicable = loop.get_applicable_learnings("debugging")
        for learning in applicable:
            print(f"  - {learning.insight}")

        # Performance summary
        print("\nPerformance summary:")
        summary = loop.get_performance_summary()
        print(f"  Success rate: {summary.get('overall_success_rate', 0):.0%}")
        print(f"  Calibration error: {summary.get('calibration_error', 0):.1%}")

        print(f"\nStats: {loop.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
