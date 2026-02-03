"""
BAEL - Feedback Processor
Processes and analyzes user feedback from multiple sources.
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from . import FeedbackItem, FeedbackType, LearningSignal, SignalType

logger = logging.getLogger("BAEL.Feedback.Processor")


@dataclass
class ProcessorConfig:
    """Configuration for feedback processor."""
    max_history: int = 1000
    signal_decay_hours: float = 24.0
    min_confidence: float = 0.3
    auto_learn: bool = True


class FeedbackProcessor:
    """
    Processes feedback from various sources.

    Features:
    - Multi-source feedback collection
    - Signal strength calculation
    - Trend detection
    - Feedback aggregation
    - Learning signal generation
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or ProcessorConfig()

        self._feedback_history: List[FeedbackItem] = []
        self._signals: List[LearningSignal] = []
        self._aggregates: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._callbacks: List[Callable[[FeedbackItem], Awaitable[None]]] = []

    async def record_feedback(
        self,
        feedback_type: FeedbackType,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
        interaction_id: Optional[str] = None,
        weight: float = 1.0
    ) -> FeedbackItem:
        """
        Record a feedback item.

        Args:
            feedback_type: Type of feedback
            value: Feedback value
            context: Context information
            interaction_id: Related interaction
            weight: Importance weight

        Returns:
            Recorded feedback item
        """
        feedback = FeedbackItem(
            id=f"fb_{uuid.uuid4().hex[:8]}",
            feedback_type=feedback_type,
            value=value,
            context=context or {},
            timestamp=time.time(),
            interaction_id=interaction_id,
            weight=weight
        )

        self._feedback_history.append(feedback)

        # Trim history if needed
        if len(self._feedback_history) > self.config.max_history:
            self._feedback_history = self._feedback_history[-self.config.max_history:]

        # Update aggregates
        self._update_aggregates(feedback)

        # Generate learning signals
        signals = await self._generate_signals(feedback)
        self._signals.extend(signals)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                await callback(feedback)
            except Exception as e:
                logger.warning(f"Feedback callback error: {e}")

        logger.debug(f"Recorded feedback: {feedback_type.value}")
        return feedback

    async def record_implicit_signal(
        self,
        signal_type: SignalType,
        context: Dict[str, Any],
        interaction_id: Optional[str] = None
    ) -> FeedbackItem:
        """
        Record an implicit signal (inferred from behavior).

        Args:
            signal_type: Type of implicit signal
            context: Context information
            interaction_id: Related interaction

        Returns:
            Recorded feedback item
        """
        # Map signal types to feedback values
        signal_weights = {
            SignalType.ACCEPTANCE: 1.0,
            SignalType.REJECTION: -0.5,
            SignalType.MODIFICATION: 0.3,
            SignalType.FOLLOW_UP: 0.5,
            SignalType.ABANDONMENT: -0.8,
            SignalType.RETRY: -0.3
        }

        return await self.record_feedback(
            feedback_type=FeedbackType.IMPLICIT,
            value={"signal": signal_type.value, "strength": signal_weights.get(signal_type, 0)},
            context=context,
            interaction_id=interaction_id,
            weight=abs(signal_weights.get(signal_type, 0.5))
        )

    async def record_correction(
        self,
        original: str,
        corrected: str,
        context: Optional[Dict[str, Any]] = None
    ) -> FeedbackItem:
        """Record a correction from the user."""
        return await self.record_feedback(
            feedback_type=FeedbackType.CORRECTION,
            value={"original": original, "corrected": corrected},
            context=context or {},
            weight=1.5  # Corrections are high-value signals
        )

    async def record_rating(
        self,
        rating: float,
        max_rating: float = 5.0,
        context: Optional[Dict[str, Any]] = None
    ) -> FeedbackItem:
        """Record a numeric rating."""
        normalized = (rating / max_rating) * 2 - 1  # Convert to -1 to 1
        return await self.record_feedback(
            feedback_type=FeedbackType.RATING,
            value={"rating": rating, "max": max_rating, "normalized": normalized},
            context=context or {}
        )

    async def record_preference(
        self,
        category: str,
        preference: str,
        context: Optional[Dict[str, Any]] = None
    ) -> FeedbackItem:
        """Record a user preference."""
        return await self.record_feedback(
            feedback_type=FeedbackType.PREFERENCE,
            value={"category": category, "preference": preference},
            context=context or {},
            weight=1.2
        )

    def _update_aggregates(self, feedback: FeedbackItem) -> None:
        """Update aggregate statistics."""
        fb_type = feedback.feedback_type.value

        if fb_type not in self._aggregates:
            self._aggregates[fb_type] = {
                "count": 0,
                "total_weight": 0.0,
                "values": []
            }

        agg = self._aggregates[fb_type]
        agg["count"] += 1
        agg["total_weight"] += feedback.weight
        agg["values"].append(feedback.value)

        # Keep only recent values
        if len(agg["values"]) > 100:
            agg["values"] = agg["values"][-100:]

    async def _generate_signals(
        self,
        feedback: FeedbackItem
    ) -> List[LearningSignal]:
        """Generate learning signals from feedback."""
        signals = []

        # Handle different feedback types
        if feedback.feedback_type == FeedbackType.CORRECTION:
            signals.append(LearningSignal(
                signal_type="error_pattern",
                strength=-0.8,
                topic=str(feedback.context.get("topic", "general")),
                evidence=[str(feedback.value.get("original", ""))[:100]],
                actionable=True
            ))

        elif feedback.feedback_type == FeedbackType.RATING:
            normalized = feedback.value.get("normalized", 0)
            signals.append(LearningSignal(
                signal_type="quality_rating",
                strength=normalized,
                topic=str(feedback.context.get("topic", "general")),
                evidence=[f"Rating: {feedback.value.get('rating')}/{feedback.value.get('max')}"],
                actionable=normalized < 0
            ))

        elif feedback.feedback_type == FeedbackType.PREFERENCE:
            signals.append(LearningSignal(
                signal_type="preference_learned",
                strength=0.9,
                topic=feedback.value.get("category", "general"),
                evidence=[feedback.value.get("preference", "")],
                actionable=True
            ))

        elif feedback.feedback_type == FeedbackType.IMPLICIT:
            strength = feedback.value.get("strength", 0)
            signals.append(LearningSignal(
                signal_type=f"implicit_{feedback.value.get('signal', 'unknown')}",
                strength=strength,
                topic=str(feedback.context.get("topic", "general")),
                evidence=[feedback.value.get("signal", "")],
                actionable=strength < 0
            ))

        return signals

    def get_recent_feedback(
        self,
        feedback_type: Optional[FeedbackType] = None,
        hours: float = 24.0,
        limit: int = 50
    ) -> List[FeedbackItem]:
        """Get recent feedback items."""
        cutoff = time.time() - (hours * 3600)

        feedback = [
            f for f in self._feedback_history
            if f.timestamp > cutoff
        ]

        if feedback_type:
            feedback = [f for f in feedback if f.feedback_type == feedback_type]

        return sorted(feedback, key=lambda f: f.timestamp, reverse=True)[:limit]

    def get_learning_signals(
        self,
        actionable_only: bool = False,
        min_strength: float = 0.0
    ) -> List[LearningSignal]:
        """Get learning signals."""
        signals = self._signals

        if actionable_only:
            signals = [s for s in signals if s.actionable]

        if min_strength > 0:
            signals = [s for s in signals if abs(s.strength) >= min_strength]

        return signals

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        return dict(self._aggregates)

    def add_callback(
        self,
        callback: Callable[[FeedbackItem], Awaitable[None]]
    ) -> None:
        """Add a feedback callback."""
        self._callbacks.append(callback)

    async def analyze_trends(
        self,
        topic: Optional[str] = None,
        hours: float = 24.0
    ) -> Dict[str, Any]:
        """
        Analyze feedback trends.

        Returns:
            Trend analysis including sentiment, issues, improvements
        """
        recent = self.get_recent_feedback(hours=hours)

        if topic:
            recent = [
                f for f in recent
                if f.context.get("topic") == topic
            ]

        if not recent:
            return {"status": "insufficient_data", "count": 0}

        # Calculate sentiment
        positive = 0
        negative = 0
        neutral = 0

        for feedback in recent:
            if feedback.feedback_type == FeedbackType.RATING:
                normalized = feedback.value.get("normalized", 0)
                if normalized > 0.2:
                    positive += 1
                elif normalized < -0.2:
                    negative += 1
                else:
                    neutral += 1
            elif feedback.feedback_type == FeedbackType.CORRECTION:
                negative += 1
            elif feedback.feedback_type == FeedbackType.IMPLICIT:
                strength = feedback.value.get("strength", 0)
                if strength > 0:
                    positive += 1
                elif strength < 0:
                    negative += 1
                else:
                    neutral += 1

        total = positive + negative + neutral

        # Identify issues
        issues = []
        corrections = [
            f for f in recent
            if f.feedback_type == FeedbackType.CORRECTION
        ]
        if corrections:
            issues.append({
                "type": "corrections_needed",
                "count": len(corrections),
                "samples": [c.value.get("original", "")[:50] for c in corrections[:3]]
            })

        # Identify improvements
        improvements = []
        preferences = [
            f for f in recent
            if f.feedback_type == FeedbackType.PREFERENCE
        ]
        if preferences:
            improvements.append({
                "type": "preferences_learned",
                "count": len(preferences),
                "samples": [p.value.get("preference", "") for p in preferences[:3]]
            })

        return {
            "status": "analyzed",
            "count": total,
            "sentiment": {
                "positive": positive / total if total > 0 else 0,
                "negative": negative / total if total > 0 else 0,
                "neutral": neutral / total if total > 0 else 0
            },
            "overall_score": (positive - negative) / total if total > 0 else 0,
            "issues": issues,
            "improvements": improvements
        }


# Global instance
_feedback_processor: Optional[FeedbackProcessor] = None


def get_feedback_processor(
    config: Optional[ProcessorConfig] = None
) -> FeedbackProcessor:
    """Get or create feedback processor instance."""
    global _feedback_processor
    if _feedback_processor is None or config is not None:
        _feedback_processor = FeedbackProcessor(config)
    return _feedback_processor
