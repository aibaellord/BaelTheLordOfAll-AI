"""
BAEL - Self-Improvement Engine
Autonomous learning and continuous improvement system.

Features:
- Performance monitoring and analysis
- Automatic prompt optimization
- Learning from successes and failures
- Strategy evolution
- Skill acquisition
"""

import asyncio
import json
import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Evolution")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class ImprovementArea(Enum):
    """Areas for improvement."""
    REASONING = "reasoning"
    CODING = "coding"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    TOOL_USAGE = "tool_usage"
    MEMORY = "memory"
    PLANNING = "planning"


class FeedbackType(Enum):
    """Types of feedback."""
    EXPLICIT_POSITIVE = "explicit_positive"
    EXPLICIT_NEGATIVE = "explicit_negative"
    IMPLICIT_SUCCESS = "implicit_success"
    IMPLICIT_FAILURE = "implicit_failure"
    CORRECTION = "correction"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class PerformanceMetric:
    """A performance metric."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Feedback:
    """Feedback instance."""
    type: FeedbackType
    area: ImprovementArea
    task: str
    response: str
    details: Optional[str] = None
    score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LearningInsight:
    """An insight learned from experience."""
    id: str
    area: ImprovementArea
    pattern: str
    improvement: str
    confidence: float
    examples: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    applied_count: int = 0
    success_rate: float = 0.0


@dataclass
class PromptVariant:
    """A prompt variant for optimization."""
    id: str
    base_prompt: str
    variant: str
    performance_score: float = 0.0
    usage_count: int = 0
    success_count: int = 0


# =============================================================================
# PERFORMANCE MONITOR
# =============================================================================

class PerformanceMonitor:
    """Monitors and tracks performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self.feedback: List[Feedback] = []
        self._session_start = datetime.now()

    def record_metric(self, name: str, value: float, context: Dict[str, Any] = None) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            context=context or {}
        )
        self.metrics[name].append(metric)

    def record_feedback(self, feedback: Feedback) -> None:
        """Record feedback."""
        self.feedback.append(feedback)
        logger.debug(f"Recorded feedback: {feedback.type.value} for {feedback.area.value}")

    def get_average(self, metric_name: str, window_hours: int = 24) -> float:
        """Get average metric value over time window."""
        cutoff = datetime.now() - timedelta(hours=window_hours)
        values = [m.value for m in self.metrics.get(metric_name, [])
                 if m.timestamp > cutoff]
        return sum(values) / len(values) if values else 0.0

    def get_trend(self, metric_name: str, window_hours: int = 24) -> str:
        """Get metric trend (improving, stable, declining)."""
        metrics = self.metrics.get(metric_name, [])
        if len(metrics) < 2:
            return "insufficient_data"

        cutoff = datetime.now() - timedelta(hours=window_hours)
        recent = [m.value for m in metrics if m.timestamp > cutoff]

        if len(recent) < 2:
            return "insufficient_data"

        first_half = sum(recent[:len(recent)//2]) / (len(recent)//2)
        second_half = sum(recent[len(recent)//2:]) / (len(recent) - len(recent)//2)

        diff = second_half - first_half
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"

    def get_area_scores(self) -> Dict[ImprovementArea, float]:
        """Get performance scores by area."""
        scores = {}

        for area in ImprovementArea:
            area_feedback = [f for f in self.feedback if f.area == area]
            if area_feedback:
                positive = sum(1 for f in area_feedback
                             if f.type in [FeedbackType.EXPLICIT_POSITIVE, FeedbackType.IMPLICIT_SUCCESS])
                total = len(area_feedback)
                scores[area] = positive / total if total > 0 else 0.5
            else:
                scores[area] = 0.5  # Default neutral

        return scores

    def get_weakest_areas(self, n: int = 3) -> List[ImprovementArea]:
        """Get the weakest performing areas."""
        scores = self.get_area_scores()
        sorted_areas = sorted(scores.items(), key=lambda x: x[1])
        return [area for area, _ in sorted_areas[:n]]

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "session_duration": (datetime.now() - self._session_start).total_seconds(),
            "total_feedback": len(self.feedback),
            "metrics_tracked": list(self.metrics.keys()),
            "area_scores": {a.value: s for a, s in self.get_area_scores().items()},
            "weakest_areas": [a.value for a in self.get_weakest_areas()]
        }


# =============================================================================
# PROMPT OPTIMIZER
# =============================================================================

class PromptOptimizer:
    """Optimizes prompts based on performance."""

    def __init__(self, model_router=None):
        self.model_router = model_router
        self.variants: Dict[str, List[PromptVariant]] = defaultdict(list)
        self._active_experiments: Dict[str, str] = {}  # base_prompt -> variant_id

    async def optimize_prompt(self, base_prompt: str, context: str = "") -> str:
        """Get optimized version of a prompt."""
        variants = self.variants.get(base_prompt, [])

        if not variants:
            # Generate initial variants
            await self._generate_variants(base_prompt, context)
            variants = self.variants.get(base_prompt, [])

        if not variants:
            return base_prompt

        # Select best performing or explore
        if random.random() < 0.2:  # 20% exploration
            variant = random.choice(variants)
        else:
            variant = max(variants, key=lambda v: v.performance_score)

        self._active_experiments[base_prompt] = variant.id
        variant.usage_count += 1

        return variant.variant

    async def _generate_variants(self, base_prompt: str, context: str) -> None:
        """Generate prompt variants using LLM."""
        if not self.model_router:
            return

        generation_prompt = f"""Generate 3 improved versions of this prompt.
Make each version clearer, more specific, and more effective.

Original prompt:
{base_prompt}

Context: {context}

Provide 3 variants, each on its own line, labeled V1:, V2:, V3:"""

        try:
            response = await self.model_router.generate(generation_prompt)

            lines = response.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith(('V1:', 'V2:', 'V3:')):
                    variant_text = line.split(':', 1)[1].strip()
                    variant = PromptVariant(
                        id=f"{hash(base_prompt)}_{i}",
                        base_prompt=base_prompt,
                        variant=variant_text
                    )
                    self.variants[base_prompt].append(variant)

        except Exception as e:
            logger.error(f"Failed to generate variants: {e}")

    def record_result(self, base_prompt: str, success: bool) -> None:
        """Record result for active experiment."""
        variant_id = self._active_experiments.get(base_prompt)
        if not variant_id:
            return

        for variant in self.variants.get(base_prompt, []):
            if variant.id == variant_id:
                if success:
                    variant.success_count += 1
                variant.performance_score = variant.success_count / max(variant.usage_count, 1)
                break

    def get_best_variant(self, base_prompt: str) -> Optional[str]:
        """Get best performing variant."""
        variants = self.variants.get(base_prompt, [])
        if not variants:
            return None

        best = max(variants, key=lambda v: v.performance_score)
        return best.variant if best.usage_count >= 3 else None


# =============================================================================
# LEARNING ENGINE
# =============================================================================

class LearningEngine:
    """Learns from experience and improves."""

    def __init__(self, model_router=None, memory_manager=None):
        self.model_router = model_router
        self.memory = memory_manager
        self.insights: Dict[str, LearningInsight] = {}
        self.patterns: Dict[ImprovementArea, List[str]] = defaultdict(list)

    async def learn_from_interaction(
        self,
        task: str,
        response: str,
        feedback: Feedback
    ) -> Optional[LearningInsight]:
        """Learn from a task interaction."""

        # Analyze the interaction
        analysis = await self._analyze_interaction(task, response, feedback)

        if analysis and analysis.get("has_insight"):
            insight = LearningInsight(
                id=f"insight_{len(self.insights)}",
                area=feedback.area,
                pattern=analysis.get("pattern", ""),
                improvement=analysis.get("improvement", ""),
                confidence=analysis.get("confidence", 0.5),
                examples=[task[:200]]
            )

            self.insights[insight.id] = insight

            # Store in memory
            if self.memory:
                await self.memory.semantic.store(
                    concept=f"learning_insight_{insight.id}",
                    knowledge=json.dumps({
                        "pattern": insight.pattern,
                        "improvement": insight.improvement,
                        "area": insight.area.value
                    }),
                    category="learning"
                )

            logger.info(f"Learned new insight: {insight.pattern[:50]}...")
            return insight

        return None

    async def _analyze_interaction(
        self,
        task: str,
        response: str,
        feedback: Feedback
    ) -> Optional[Dict[str, Any]]:
        """Analyze interaction for learning opportunities."""
        if not self.model_router:
            return None

        analysis_prompt = f"""Analyze this interaction for learning opportunities.

Task: {task[:500]}

Response: {response[:500]}

Feedback type: {feedback.type.value}
Feedback details: {feedback.details or 'None'}

Questions:
1. Was the response effective? Why or why not?
2. What pattern or insight can be learned?
3. How should future similar tasks be handled differently?
4. Confidence level (0-1)?

Output JSON with: has_insight, pattern, improvement, confidence"""

        try:
            response = await self.model_router.generate(analysis_prompt)

            # Parse JSON from response
            # Simple extraction - in production, use proper JSON parsing
            if "has_insight" in response.lower():
                return {
                    "has_insight": "true" in response.lower()[:100],
                    "pattern": self._extract_field(response, "pattern"),
                    "improvement": self._extract_field(response, "improvement"),
                    "confidence": 0.7
                }

        except Exception as e:
            logger.error(f"Analysis failed: {e}")

        return None

    def _extract_field(self, text: str, field: str) -> str:
        """Extract field value from text."""
        # Simple extraction - look for field: value pattern
        lines = text.split('\n')
        for line in lines:
            if field.lower() in line.lower():
                parts = line.split(':', 1)
                if len(parts) > 1:
                    return parts[1].strip().strip('"')
        return ""

    def get_relevant_insights(self, area: ImprovementArea, limit: int = 5) -> List[LearningInsight]:
        """Get relevant insights for an area."""
        area_insights = [i for i in self.insights.values() if i.area == area]
        return sorted(area_insights, key=lambda i: i.confidence, reverse=True)[:limit]

    async def synthesize_learnings(self, area: ImprovementArea) -> str:
        """Synthesize learnings into actionable guidance."""
        insights = self.get_relevant_insights(area, limit=10)

        if not insights:
            return f"No specific learnings yet for {area.value}"

        guidance_parts = [f"Key learnings for {area.value}:"]
        for insight in insights:
            guidance_parts.append(f"- {insight.improvement}")

        return "\n".join(guidance_parts)


# =============================================================================
# SELF-IMPROVEMENT ENGINE
# =============================================================================

class SelfImprovementEngine:
    """Main engine for self-improvement."""

    def __init__(self, brain=None):
        self.brain = brain
        self.monitor = PerformanceMonitor()
        self.optimizer = PromptOptimizer(brain.model_router if brain else None)
        self.learner = LearningEngine(
            brain.model_router if brain else None,
            brain.memory_manager if brain else None
        )

        self._improvement_cycle_active = False

    async def record_interaction(
        self,
        task: str,
        response: str,
        feedback_type: FeedbackType,
        area: ImprovementArea,
        score: float = 0.0,
        details: str = None
    ) -> None:
        """Record an interaction for learning."""

        feedback = Feedback(
            type=feedback_type,
            area=area,
            task=task,
            response=response,
            score=score,
            details=details
        )

        # Record in monitor
        self.monitor.record_feedback(feedback)

        # Learn from interaction
        await self.learner.learn_from_interaction(task, response, feedback)

        # Update prompt optimization
        success = feedback_type in [FeedbackType.EXPLICIT_POSITIVE, FeedbackType.IMPLICIT_SUCCESS]
        self.optimizer.record_result(task[:100], success)

    async def get_enhanced_prompt(self, base_prompt: str, context: str = "") -> str:
        """Get an enhanced version of a prompt."""
        # Apply learned improvements
        area = self._detect_area(base_prompt)
        insights = self.learner.get_relevant_insights(area)

        enhanced = base_prompt

        # Add relevant learnings
        if insights:
            learnings = "\n".join([f"- {i.improvement}" for i in insights[:3]])
            enhanced = f"{base_prompt}\n\nConsider these learnings:\n{learnings}"

        # Apply prompt optimization
        optimized = await self.optimizer.optimize_prompt(enhanced, context)

        return optimized

    def _detect_area(self, prompt: str) -> ImprovementArea:
        """Detect improvement area from prompt."""
        prompt_lower = prompt.lower()

        if any(w in prompt_lower for w in ["code", "implement", "function", "class"]):
            return ImprovementArea.CODING
        elif any(w in prompt_lower for w in ["research", "find", "search", "learn"]):
            return ImprovementArea.RESEARCH
        elif any(w in prompt_lower for w in ["plan", "design", "architect"]):
            return ImprovementArea.PLANNING
        elif any(w in prompt_lower for w in ["explain", "describe", "communicate"]):
            return ImprovementArea.COMMUNICATION
        else:
            return ImprovementArea.REASONING

    async def run_improvement_cycle(self) -> Dict[str, Any]:
        """Run a self-improvement cycle."""
        if self._improvement_cycle_active:
            return {"status": "already_running"}

        self._improvement_cycle_active = True

        try:
            # 1. Analyze performance
            summary = self.monitor.get_summary()
            weak_areas = self.monitor.get_weakest_areas(3)

            # 2. Generate improvements for weak areas
            improvements = {}
            for area in weak_areas:
                guidance = await self.learner.synthesize_learnings(area)
                improvements[area.value] = guidance

            # 3. Identify patterns
            patterns = self._identify_failure_patterns()

            # 4. Create improvement plan
            plan = {
                "timestamp": datetime.now().isoformat(),
                "performance_summary": summary,
                "weak_areas": [a.value for a in weak_areas],
                "improvements": improvements,
                "failure_patterns": patterns,
                "recommendations": self._generate_recommendations(weak_areas, patterns)
            }

            return plan

        finally:
            self._improvement_cycle_active = False

    def _identify_failure_patterns(self) -> List[Dict[str, Any]]:
        """Identify patterns in failures."""
        patterns = []

        failures = [f for f in self.monitor.feedback
                   if f.type in [FeedbackType.EXPLICIT_NEGATIVE, FeedbackType.IMPLICIT_FAILURE, FeedbackType.ERROR]]

        # Group by area
        by_area = defaultdict(list)
        for f in failures:
            by_area[f.area].append(f)

        for area, area_failures in by_area.items():
            if len(area_failures) >= 3:
                patterns.append({
                    "area": area.value,
                    "count": len(area_failures),
                    "description": f"Repeated failures in {area.value}"
                })

        return patterns

    def _generate_recommendations(
        self,
        weak_areas: List[ImprovementArea],
        patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        for area in weak_areas:
            if area == ImprovementArea.CODING:
                recommendations.append("Focus on code quality and testing")
            elif area == ImprovementArea.REASONING:
                recommendations.append("Apply more structured reasoning approaches")
            elif area == ImprovementArea.RESEARCH:
                recommendations.append("Expand source diversity and verification")
            elif area == ImprovementArea.COMMUNICATION:
                recommendations.append("Improve clarity and structure of responses")
            elif area == ImprovementArea.PLANNING:
                recommendations.append("Break down complex tasks more effectively")

        return recommendations

    def get_stats(self) -> Dict[str, Any]:
        """Get improvement engine statistics."""
        return {
            "total_insights": len(self.learner.insights),
            "prompt_variants": sum(len(v) for v in self.optimizer.variants.values()),
            "performance_summary": self.monitor.get_summary(),
            "active_experiments": len(self.optimizer._active_experiments)
        }


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test self-improvement engine."""
    engine = SelfImprovementEngine()

    # Simulate some interactions
    await engine.record_interaction(
        task="Write a Python function to sort a list",
        response="def sort_list(lst): return sorted(lst)",
        feedback_type=FeedbackType.EXPLICIT_POSITIVE,
        area=ImprovementArea.CODING,
        score=0.9
    )

    await engine.record_interaction(
        task="Explain quantum computing",
        response="Quantum computing is...",
        feedback_type=FeedbackType.IMPLICIT_FAILURE,
        area=ImprovementArea.COMMUNICATION,
        score=0.3,
        details="Response was too brief"
    )

    # Run improvement cycle
    plan = await engine.run_improvement_cycle()

    print("Improvement Plan:")
    print(json.dumps(plan, indent=2, default=str))

    print("\nStats:")
    print(json.dumps(engine.get_stats(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
