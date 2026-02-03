"""
BAEL - Learning Engine
Continuous learning from feedback to improve performance.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import FeedbackType, LearningSignal

logger = logging.getLogger("BAEL.Feedback.Learning")


@dataclass
class LearningConfig:
    """Configuration for learning engine."""
    learning_rate: float = 0.1
    min_samples_for_learning: int = 3
    persistence_path: Optional[str] = None
    auto_save_interval: int = 300  # seconds


@dataclass
class LearnedPattern:
    """A pattern learned from feedback."""
    id: str
    pattern_type: str
    input_pattern: str
    learned_response: str
    confidence: float
    sample_count: int
    last_updated: float


@dataclass
class Adaptation:
    """An adaptation/change based on learning."""
    id: str
    category: str
    description: str
    before: str
    after: str
    impact_score: float
    created_at: float


class LearningEngine:
    """
    Continuous learning engine.

    Features:
    - Pattern extraction from feedback
    - Response adaptation
    - Error correction learning
    - Style adaptation
    - Knowledge accumulation
    """

    def __init__(self, config: Optional[LearningConfig] = None):
        self.config = config or LearningConfig()

        self._patterns: Dict[str, LearnedPattern] = {}
        self._adaptations: List[Adaptation] = []
        self._error_corrections: Dict[str, str] = {}
        self._style_preferences: Dict[str, Any] = {}
        self._knowledge_updates: List[Dict[str, Any]] = []
        self._last_save = time.time()

        # Load persisted learnings if available
        self._load_learnings()

    def _load_learnings(self) -> None:
        """Load persisted learnings from disk."""
        if not self.config.persistence_path:
            return

        path = Path(self.config.persistence_path)
        if not path.exists():
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)

            # Load patterns
            for p_data in data.get("patterns", []):
                pattern = LearnedPattern(**p_data)
                self._patterns[pattern.id] = pattern

            # Load error corrections
            self._error_corrections = data.get("error_corrections", {})

            # Load style preferences
            self._style_preferences = data.get("style_preferences", {})

            logger.info(f"Loaded {len(self._patterns)} patterns, {len(self._error_corrections)} corrections")

        except Exception as e:
            logger.warning(f"Failed to load learnings: {e}")

    def _save_learnings(self) -> None:
        """Save learnings to disk."""
        if not self.config.persistence_path:
            return

        path = Path(self.config.persistence_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = {
                "patterns": [
                    {
                        "id": p.id,
                        "pattern_type": p.pattern_type,
                        "input_pattern": p.input_pattern,
                        "learned_response": p.learned_response,
                        "confidence": p.confidence,
                        "sample_count": p.sample_count,
                        "last_updated": p.last_updated
                    }
                    for p in self._patterns.values()
                ],
                "error_corrections": self._error_corrections,
                "style_preferences": self._style_preferences,
                "saved_at": time.time()
            }

            with open(path, "w") as f:
                json.dump(data, f, indent=2)

            self._last_save = time.time()
            logger.debug("Saved learnings to disk")

        except Exception as e:
            logger.error(f"Failed to save learnings: {e}")

    async def learn_from_signals(
        self,
        signals: List[LearningSignal]
    ) -> List[Adaptation]:
        """
        Learn from a batch of signals.

        Args:
            signals: Learning signals from feedback

        Returns:
            List of adaptations made
        """
        adaptations = []

        for signal in signals:
            if not signal.actionable:
                continue

            # Process different signal types
            if signal.signal_type == "error_pattern":
                adaptation = await self._learn_error_correction(signal)
            elif signal.signal_type == "preference_learned":
                adaptation = await self._learn_preference(signal)
            elif signal.signal_type.startswith("implicit_"):
                adaptation = await self._learn_from_implicit(signal)
            else:
                adaptation = await self._learn_general_pattern(signal)

            if adaptation:
                adaptations.append(adaptation)
                self._adaptations.append(adaptation)

        # Auto-save if needed
        if time.time() - self._last_save > self.config.auto_save_interval:
            self._save_learnings()

        return adaptations

    async def _learn_error_correction(
        self,
        signal: LearningSignal
    ) -> Optional[Adaptation]:
        """Learn from an error correction signal."""
        if not signal.evidence:
            return None

        error_text = signal.evidence[0]
        topic = signal.topic

        # Store for future avoidance
        key = f"{topic}:{error_text[:50]}"

        if key not in self._error_corrections:
            self._error_corrections[key] = error_text

            return Adaptation(
                id=f"adapt_{int(time.time())}",
                category="error_correction",
                description=f"Learned to avoid: {error_text[:50]}...",
                before=error_text[:100],
                after="[Will avoid this pattern]",
                impact_score=0.8,
                created_at=time.time()
            )

        return None

    async def _learn_preference(
        self,
        signal: LearningSignal
    ) -> Optional[Adaptation]:
        """Learn from a preference signal."""
        if not signal.evidence:
            return None

        preference = signal.evidence[0]
        topic = signal.topic

        # Store preference
        if topic not in self._style_preferences:
            self._style_preferences[topic] = []

        if preference not in self._style_preferences[topic]:
            self._style_preferences[topic].append(preference)

            return Adaptation(
                id=f"pref_{int(time.time())}",
                category="preference",
                description=f"Learned preference: {preference}",
                before="default behavior",
                after=preference,
                impact_score=0.6,
                created_at=time.time()
            )

        return None

    async def _learn_from_implicit(
        self,
        signal: LearningSignal
    ) -> Optional[Adaptation]:
        """Learn from implicit signals (acceptance/rejection/etc)."""
        signal_name = signal.signal_type.replace("implicit_", "")

        # Accumulate signals for pattern detection
        pattern_key = f"{signal.topic}:{signal_name}"

        if pattern_key not in self._patterns:
            self._patterns[pattern_key] = LearnedPattern(
                id=pattern_key,
                pattern_type="implicit",
                input_pattern=signal.topic,
                learned_response=signal_name,
                confidence=abs(signal.strength),
                sample_count=1,
                last_updated=time.time()
            )
        else:
            pattern = self._patterns[pattern_key]
            pattern.sample_count += 1
            # Update confidence with exponential moving average
            alpha = self.config.learning_rate
            pattern.confidence = (1 - alpha) * pattern.confidence + alpha * abs(signal.strength)
            pattern.last_updated = time.time()

        # Create adaptation if enough samples
        pattern = self._patterns[pattern_key]
        if pattern.sample_count >= self.config.min_samples_for_learning:
            if signal.strength < 0:  # Negative signal
                return Adaptation(
                    id=f"implicit_{int(time.time())}",
                    category="behavior_adjustment",
                    description=f"Adjusting behavior for {signal.topic} based on {pattern.sample_count} signals",
                    before=f"Current approach (rejection rate: {pattern.confidence:.1%})",
                    after="Try alternative approach",
                    impact_score=pattern.confidence,
                    created_at=time.time()
                )

        return None

    async def _learn_general_pattern(
        self,
        signal: LearningSignal
    ) -> Optional[Adaptation]:
        """Learn general patterns from signals."""
        # Store as knowledge update
        self._knowledge_updates.append({
            "topic": signal.topic,
            "signal_type": signal.signal_type,
            "strength": signal.strength,
            "evidence": signal.evidence,
            "timestamp": time.time()
        })

        # Trim old updates
        cutoff = time.time() - 7 * 24 * 3600  # 7 days
        self._knowledge_updates = [
            u for u in self._knowledge_updates
            if u["timestamp"] > cutoff
        ]

        return None

    def get_learned_patterns(
        self,
        topic: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[LearnedPattern]:
        """Get learned patterns."""
        patterns = list(self._patterns.values())

        if topic:
            patterns = [p for p in patterns if topic in p.input_pattern]

        patterns = [p for p in patterns if p.confidence >= min_confidence]

        return sorted(patterns, key=lambda p: p.confidence, reverse=True)

    def get_adaptations(
        self,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Adaptation]:
        """Get recent adaptations."""
        adaptations = self._adaptations

        if category:
            adaptations = [a for a in adaptations if a.category == category]

        return sorted(adaptations, key=lambda a: a.created_at, reverse=True)[:limit]

    def get_preferences(self, topic: str) -> List[str]:
        """Get learned preferences for a topic."""
        return self._style_preferences.get(topic, [])

    def should_avoid(self, text: str, topic: str = "general") -> Tuple[bool, Optional[str]]:
        """
        Check if a pattern should be avoided based on learned corrections.

        Returns:
            Tuple of (should_avoid, reason)
        """
        text_lower = text.lower()

        for key, correction in self._error_corrections.items():
            key_topic, pattern = key.split(":", 1)
            if key_topic == topic or key_topic == "general":
                if pattern.lower() in text_lower:
                    return True, correction

        return False, None

    async def apply_learnings(
        self,
        response: str,
        topic: str = "general"
    ) -> str:
        """
        Apply learned patterns to a response.

        Args:
            response: Original response
            topic: Topic context

        Returns:
            Potentially modified response
        """
        # Check for patterns to avoid
        should_avoid, reason = self.should_avoid(response, topic)
        if should_avoid:
            logger.info(f"Avoiding learned error pattern in response")
            # In a real implementation, would modify the response
            # For now, just log

        # Apply style preferences
        preferences = self.get_preferences(topic)
        if preferences:
            logger.debug(f"Applying {len(preferences)} preferences for {topic}")
            # Would modify response style here

        return response

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of all learnings."""
        return {
            "total_patterns": len(self._patterns),
            "total_corrections": len(self._error_corrections),
            "total_adaptations": len(self._adaptations),
            "style_preferences": {
                topic: len(prefs) for topic, prefs in self._style_preferences.items()
            },
            "knowledge_updates": len(self._knowledge_updates),
            "high_confidence_patterns": len([
                p for p in self._patterns.values()
                if p.confidence > 0.8
            ])
        }

    def clear_learnings(self, category: Optional[str] = None) -> None:
        """Clear learnings (optionally by category)."""
        if category == "patterns":
            self._patterns.clear()
        elif category == "corrections":
            self._error_corrections.clear()
        elif category == "preferences":
            self._style_preferences.clear()
        elif category is None:
            self._patterns.clear()
            self._error_corrections.clear()
            self._style_preferences.clear()
            self._adaptations.clear()
            self._knowledge_updates.clear()

        self._save_learnings()


# Global instance
_learning_engine: Optional[LearningEngine] = None


def get_learning_engine(
    config: Optional[LearningConfig] = None
) -> LearningEngine:
    """Get or create learning engine instance."""
    global _learning_engine
    if _learning_engine is None or config is not None:
        _learning_engine = LearningEngine(config)
    return _learning_engine
