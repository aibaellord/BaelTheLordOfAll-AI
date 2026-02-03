"""
BAEL - Need Anticipator
Predicts user needs before they're expressed.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.Proactive.NeedAnticipator")


class NeedCategory(Enum):
    """Categories of user needs."""
    INFORMATION = "information"      # Needs information/answers
    CLARIFICATION = "clarification"  # Needs clarification
    ASSISTANCE = "assistance"        # Needs help with task
    VALIDATION = "validation"        # Needs confirmation
    RESOURCES = "resources"          # Needs resources/tools
    LEARNING = "learning"            # Needs to learn something
    ORGANIZATION = "organization"    # Needs organization help
    AUTOMATION = "automation"        # Needs automation


@dataclass
class PredictedNeed:
    """A predicted user need."""
    id: str
    category: NeedCategory
    description: str
    confidence: float
    context_clues: List[str]
    suggested_action: str
    priority: int = 5


@dataclass
class ContextSignal:
    """A signal from user context."""
    signal_type: str
    value: Any
    timestamp: float
    weight: float = 1.0


class NeedAnticipator:
    """
    Anticipates user needs based on patterns and context.

    Features:
    - Pattern-based prediction
    - Context analysis
    - Behavioral modeling
    - Proactive suggestions
    """

    def __init__(self):
        self._context_signals: List[ContextSignal] = []
        self._need_history: List[PredictedNeed] = []
        self._patterns: Dict[str, float] = defaultdict(float)
        self._llm = None

        # Pattern weights for different signals
        self._signal_weights = {
            "question_mark": 0.8,
            "error_message": 0.9,
            "incomplete_task": 0.7,
            "repeated_action": 0.6,
            "context_switch": 0.5,
            "long_pause": 0.4,
            "frustration_indicator": 0.9,
            "learning_indicator": 0.6
        }

    async def _get_llm(self):
        """Lazy load LLM."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                pass
        return self._llm

    def add_signal(self, signal: ContextSignal) -> None:
        """Add a context signal."""
        self._context_signals.append(signal)

        # Update patterns
        self._patterns[signal.signal_type] += signal.weight

        # Trim old signals
        cutoff = time.time() - 1800  # 30 minutes
        self._context_signals = [
            s for s in self._context_signals
            if s.timestamp > cutoff
        ]

    async def predict_needs(
        self,
        current_context: Optional[Dict[str, Any]] = None
    ) -> List[PredictedNeed]:
        """
        Predict current user needs.

        Args:
            current_context: Current conversation/task context

        Returns:
            List of predicted needs sorted by confidence
        """
        predictions = []

        # Analyze recent signals
        recent_signals = [
            s for s in self._context_signals
            if time.time() - s.timestamp < 300
        ]

        # Pattern-based predictions
        predictions.extend(self._predict_from_patterns(recent_signals))

        # Context-based predictions
        if current_context:
            predictions.extend(
                await self._predict_from_context(current_context)
            )

        # Behavioral predictions
        predictions.extend(self._predict_from_behavior())

        # Deduplicate and sort
        seen = set()
        unique_predictions = []
        for pred in predictions:
            key = (pred.category, pred.description[:50])
            if key not in seen:
                seen.add(key)
                unique_predictions.append(pred)

        # Sort by confidence
        unique_predictions.sort(key=lambda p: p.confidence, reverse=True)

        return unique_predictions[:5]  # Top 5 predictions

    def _predict_from_patterns(
        self,
        signals: List[ContextSignal]
    ) -> List[PredictedNeed]:
        """Generate predictions from signal patterns."""
        predictions = []

        # Group signals by type
        signal_counts = defaultdict(int)
        for signal in signals:
            signal_counts[signal.signal_type] += 1

        # Question pattern
        if signal_counts.get("question_mark", 0) > 0:
            predictions.append(PredictedNeed(
                id=f"need_info_{int(time.time())}",
                category=NeedCategory.INFORMATION,
                description="User appears to be seeking information",
                confidence=min(0.9, 0.3 * signal_counts["question_mark"]),
                context_clues=["question_mark signals detected"],
                suggested_action="Prepare comprehensive answer",
                priority=8
            ))

        # Error pattern
        if signal_counts.get("error_message", 0) >= 2:
            predictions.append(PredictedNeed(
                id=f"need_debug_{int(time.time())}",
                category=NeedCategory.ASSISTANCE,
                description="User encountering multiple errors - may need debugging help",
                confidence=min(0.95, 0.4 * signal_counts["error_message"]),
                context_clues=["multiple error messages detected"],
                suggested_action="Offer debugging assistance",
                priority=9
            ))

        # Frustration pattern
        if signal_counts.get("frustration_indicator", 0) > 0:
            predictions.append(PredictedNeed(
                id=f"need_help_{int(time.time())}",
                category=NeedCategory.ASSISTANCE,
                description="User may be frustrated - offer alternative approaches",
                confidence=0.85,
                context_clues=["frustration indicators detected"],
                suggested_action="Suggest simpler alternative or offer to take over",
                priority=10
            ))

        # Repeated action pattern
        if signal_counts.get("repeated_action", 0) >= 3:
            predictions.append(PredictedNeed(
                id=f"need_auto_{int(time.time())}",
                category=NeedCategory.AUTOMATION,
                description="User performing repetitive actions - could be automated",
                confidence=min(0.8, 0.2 * signal_counts["repeated_action"]),
                context_clues=["repeated actions detected"],
                suggested_action="Offer to create automation or shortcut",
                priority=6
            ))

        # Learning pattern
        if signal_counts.get("learning_indicator", 0) >= 2:
            predictions.append(PredictedNeed(
                id=f"need_learn_{int(time.time())}",
                category=NeedCategory.LEARNING,
                description="User exploring new concepts - may benefit from tutorials",
                confidence=0.7,
                context_clues=["learning indicators detected"],
                suggested_action="Provide educational resources or explanations",
                priority=5
            ))

        return predictions

    async def _predict_from_context(
        self,
        context: Dict[str, Any]
    ) -> List[PredictedNeed]:
        """Generate predictions from current context."""
        predictions = []

        # Check for incomplete tasks
        if context.get("incomplete_task"):
            predictions.append(PredictedNeed(
                id=f"need_complete_{int(time.time())}",
                category=NeedCategory.ASSISTANCE,
                description="There's an incomplete task that could be finished",
                confidence=0.75,
                context_clues=["incomplete task in context"],
                suggested_action="Offer to complete the pending task",
                priority=7
            ))

        # Check for complex query
        query = context.get("query", "")
        if query and len(query) > 200:
            predictions.append(PredictedNeed(
                id=f"need_clarify_{int(time.time())}",
                category=NeedCategory.CLARIFICATION,
                description="Complex query may benefit from clarification",
                confidence=0.6,
                context_clues=["long/complex query detected"],
                suggested_action="Ask clarifying questions before proceeding",
                priority=6
            ))

        # Check for multi-step request
        if context.get("multi_step") or "and" in query.lower():
            predictions.append(PredictedNeed(
                id=f"need_plan_{int(time.time())}",
                category=NeedCategory.ORGANIZATION,
                description="Multi-step request - may need structured approach",
                confidence=0.7,
                context_clues=["multi-step indicators"],
                suggested_action="Create step-by-step plan before executing",
                priority=7
            ))

        # LLM-based prediction for deeper analysis
        llm = await self._get_llm()
        if llm and query:
            llm_predictions = await self._llm_predict(query, context)
            predictions.extend(llm_predictions)

        return predictions

    async def _llm_predict(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[PredictedNeed]:
        """Use LLM for deeper need prediction."""
        llm = await self._get_llm()
        if not llm:
            return []

        prompt = f"""Analyze this user query and predict their underlying needs.

Query: {query[:500]}

What might the user really need that they haven't explicitly stated?
Consider:
1. Information they might need but didn't ask for
2. Potential follow-up questions
3. Resources that could help
4. Common mistakes to avoid

Predict 1-2 hidden needs:
NEED: [category] - [description] - [suggested action]"""

        try:
            response = await llm.generate(prompt, temperature=0.5)

            predictions = []
            for line in response.split("\n"):
                if "NEED:" in line:
                    parts = line.split("NEED:")[-1].split(" - ")
                    if len(parts) >= 2:
                        category = self._parse_category(parts[0].strip())
                        predictions.append(PredictedNeed(
                            id=f"need_llm_{int(time.time())}",
                            category=category,
                            description=parts[1].strip() if len(parts) > 1 else "Predicted need",
                            confidence=0.65,
                            context_clues=["LLM analysis"],
                            suggested_action=parts[2].strip() if len(parts) > 2 else "Address proactively",
                            priority=6
                        ))

            return predictions
        except Exception as e:
            logger.warning(f"LLM prediction failed: {e}")
            return []

    def _parse_category(self, text: str) -> NeedCategory:
        """Parse need category from text."""
        text_lower = text.lower()

        for category in NeedCategory:
            if category.value in text_lower:
                return category

        # Defaults based on keywords
        if any(word in text_lower for word in ["info", "know", "what", "how"]):
            return NeedCategory.INFORMATION
        if any(word in text_lower for word in ["help", "assist", "fix"]):
            return NeedCategory.ASSISTANCE
        if any(word in text_lower for word in ["learn", "understand", "explain"]):
            return NeedCategory.LEARNING

        return NeedCategory.INFORMATION

    def _predict_from_behavior(self) -> List[PredictedNeed]:
        """Generate predictions from behavioral patterns."""
        predictions = []

        # Check pattern accumulations
        for pattern, weight in self._patterns.items():
            if weight > 5:  # High pattern accumulation
                if pattern == "context_switch":
                    predictions.append(PredictedNeed(
                        id=f"need_org_{int(time.time())}",
                        category=NeedCategory.ORGANIZATION,
                        description="Frequent context switching - may need organization help",
                        confidence=min(0.8, weight / 10),
                        context_clues=[f"High {pattern} pattern"],
                        suggested_action="Offer to organize or summarize different threads",
                        priority=5
                    ))

        return predictions

    def record_signal_from_text(self, text: str) -> None:
        """Analyze text and record relevant signals."""
        now = time.time()

        # Question detection
        if "?" in text:
            self.add_signal(ContextSignal(
                signal_type="question_mark",
                value=text.count("?"),
                timestamp=now
            ))

        # Error detection
        error_words = ["error", "exception", "failed", "crash", "bug", "broken"]
        if any(word in text.lower() for word in error_words):
            self.add_signal(ContextSignal(
                signal_type="error_message",
                value=text[:100],
                timestamp=now
            ))

        # Frustration detection
        frustration_words = ["ugh", "argh", "frustrated", "annoying", "why won't", "doesn't work"]
        if any(word in text.lower() for word in frustration_words):
            self.add_signal(ContextSignal(
                signal_type="frustration_indicator",
                value=True,
                timestamp=now,
                weight=1.5
            ))

        # Learning detection
        learning_words = ["how do", "what is", "explain", "teach me", "learn", "understand"]
        if any(word in text.lower() for word in learning_words):
            self.add_signal(ContextSignal(
                signal_type="learning_indicator",
                value=True,
                timestamp=now
            ))

    def get_signal_summary(self) -> Dict[str, Any]:
        """Get summary of current signals."""
        signal_counts = defaultdict(int)
        for signal in self._context_signals:
            signal_counts[signal.signal_type] += 1

        return {
            "total_signals": len(self._context_signals),
            "signal_types": dict(signal_counts),
            "accumulated_patterns": dict(self._patterns)
        }


# Global instance
_need_anticipator: Optional[NeedAnticipator] = None


def get_need_anticipator() -> NeedAnticipator:
    """Get or create need anticipator instance."""
    global _need_anticipator
    if _need_anticipator is None:
        _need_anticipator = NeedAnticipator()
    return _need_anticipator
