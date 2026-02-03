"""
BAEL - Preference Tracker
Tracks and learns user preferences over time.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from . import Preference

logger = logging.getLogger("BAEL.Feedback.Preferences")


class PreferenceCategory(Enum):
    """Categories of preferences."""
    RESPONSE_STYLE = "response_style"
    OUTPUT_FORMAT = "output_format"
    VERBOSITY = "verbosity"
    TECHNICAL_LEVEL = "technical_level"
    LANGUAGE = "language"
    TONE = "tone"
    EXAMPLES = "examples"
    EXPLANATIONS = "explanations"
    CODE_STYLE = "code_style"
    COMMUNICATION = "communication"


@dataclass
class PreferenceEvidence:
    """Evidence supporting a preference."""
    action: str
    context: str
    timestamp: float
    strength: float


class PreferenceTracker:
    """
    Tracks and learns user preferences.

    Features:
    - Multi-category preference tracking
    - Confidence-based preference selection
    - Temporal preference decay
    - Preference conflict resolution
    - Profile building
    """

    def __init__(self):
        self._preferences: Dict[str, List[Preference]] = defaultdict(list)
        self._evidence: Dict[str, List[PreferenceEvidence]] = defaultdict(list)
        self._active_profile: Dict[str, str] = {}
        self._confidence_threshold = 0.6

    async def record_preference(
        self,
        category: str,
        preference: str,
        evidence: Optional[str] = None,
        confidence: float = 0.7
    ) -> Preference:
        """
        Record a new preference.

        Args:
            category: Preference category
            preference: The preference value
            evidence: Evidence for this preference
            confidence: Initial confidence level

        Returns:
            Created preference
        """
        # Check for existing preference
        existing = self._find_preference(category, preference)

        if existing:
            # Update existing preference
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.examples.append(evidence or "implicit")
            existing.examples = existing.examples[-10:]  # Keep last 10

            logger.debug(f"Updated preference {category}: {preference} (confidence: {existing.confidence:.2f})")
            return existing

        # Create new preference
        pref = Preference(
            id=f"pref_{category}_{int(time.time())}",
            category=category,
            preference=preference,
            confidence=confidence,
            examples=[evidence] if evidence else []
        )

        self._preferences[category].append(pref)

        # Update active profile if high confidence
        if confidence >= self._confidence_threshold:
            self._active_profile[category] = preference

        logger.info(f"Recorded new preference {category}: {preference}")
        return pref

    async def infer_preference(
        self,
        category: str,
        action: str,
        context: str
    ) -> Optional[str]:
        """
        Infer preference from user action.

        Args:
            category: Preference category
            action: User action that indicates preference
            context: Context of the action

        Returns:
            Inferred preference value or None
        """
        # Add evidence
        self._evidence[category].append(PreferenceEvidence(
            action=action,
            context=context,
            timestamp=time.time(),
            strength=0.5
        ))

        # Infer based on action patterns
        inferred = self._infer_from_action(category, action)

        if inferred:
            await self.record_preference(
                category=category,
                preference=inferred,
                evidence=f"Inferred from: {action}"
            )

        return inferred

    def _infer_from_action(
        self,
        category: str,
        action: str
    ) -> Optional[str]:
        """Infer preference value from action."""
        action_lower = action.lower()

        # Response style preferences
        if category == PreferenceCategory.RESPONSE_STYLE.value:
            if any(w in action_lower for w in ["concise", "brief", "short"]):
                return "concise"
            if any(w in action_lower for w in ["detailed", "thorough", "complete"]):
                return "detailed"
            if any(w in action_lower for w in ["simple", "easy", "basic"]):
                return "simple"

        # Verbosity preferences
        if category == PreferenceCategory.VERBOSITY.value:
            if any(w in action_lower for w in ["less", "shorter", "cut"]):
                return "low"
            if any(w in action_lower for w in ["more", "expand", "elaborate"]):
                return "high"

        # Technical level preferences
        if category == PreferenceCategory.TECHNICAL_LEVEL.value:
            if any(w in action_lower for w in ["explain", "beginner", "simple"]):
                return "beginner"
            if any(w in action_lower for w in ["advanced", "expert", "technical"]):
                return "advanced"

        # Tone preferences
        if category == PreferenceCategory.TONE.value:
            if any(w in action_lower for w in ["casual", "friendly", "informal"]):
                return "casual"
            if any(w in action_lower for w in ["formal", "professional"]):
                return "formal"

        # Code style preferences
        if category == PreferenceCategory.CODE_STYLE.value:
            if any(w in action_lower for w in ["comment", "document"]):
                return "well_documented"
            if any(w in action_lower for w in ["type", "typed"]):
                return "type_annotated"

        return None

    def _find_preference(
        self,
        category: str,
        preference: str
    ) -> Optional[Preference]:
        """Find an existing preference."""
        for pref in self._preferences.get(category, []):
            if pref.preference == preference:
                return pref
        return None

    def get_preference(
        self,
        category: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the current preference for a category.

        Returns the highest confidence preference.
        """
        # Check active profile first
        if category in self._active_profile:
            return self._active_profile[category]

        prefs = self._preferences.get(category, [])
        if not prefs:
            return default

        # Get highest confidence preference
        best = max(prefs, key=lambda p: p.confidence)

        if best.confidence >= self._confidence_threshold:
            return best.preference

        return default

    def get_all_preferences(
        self,
        category: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[Preference]:
        """Get all preferences, optionally filtered."""
        if category:
            prefs = self._preferences.get(category, [])
        else:
            prefs = [p for cat_prefs in self._preferences.values() for p in cat_prefs]

        return [p for p in prefs if p.confidence >= min_confidence]

    def get_profile(self) -> Dict[str, str]:
        """Get the complete active preference profile."""
        profile = dict(self._active_profile)

        # Fill in from high-confidence preferences
        for category, prefs in self._preferences.items():
            if category not in profile and prefs:
                best = max(prefs, key=lambda p: p.confidence)
                if best.confidence >= self._confidence_threshold:
                    profile[category] = best.preference

        return profile

    async def apply_decay(self, decay_factor: float = 0.95) -> None:
        """Apply temporal decay to preferences."""
        for category, prefs in self._preferences.items():
            for pref in prefs:
                pref.confidence *= decay_factor

        # Remove very low confidence preferences
        for category in list(self._preferences.keys()):
            self._preferences[category] = [
                p for p in self._preferences[category]
                if p.confidence >= 0.1
            ]

    def resolve_conflict(
        self,
        category: str
    ) -> Optional[str]:
        """
        Resolve conflicting preferences in a category.

        Returns the winner based on:
        1. Confidence level
        2. Recency of evidence
        3. Number of examples
        """
        prefs = self._preferences.get(category, [])

        if not prefs:
            return None

        if len(prefs) == 1:
            return prefs[0].preference

        # Score each preference
        scores = []
        for pref in prefs:
            score = pref.confidence * 0.5  # Confidence weight
            score += min(len(pref.examples), 5) * 0.1  # Example count weight
            scores.append((pref, score))

        winner = max(scores, key=lambda x: x[1])[0]
        return winner.preference

    async def learn_from_correction(
        self,
        category: str,
        wrong_value: str,
        correct_value: str
    ) -> None:
        """
        Learn from a user correction.

        Args:
            category: Preference category
            wrong_value: The incorrect preference
            correct_value: The correct preference
        """
        # Decrease confidence in wrong preference
        wrong_pref = self._find_preference(category, wrong_value)
        if wrong_pref:
            wrong_pref.confidence = max(0, wrong_pref.confidence - 0.3)

        # Increase/add correct preference
        await self.record_preference(
            category=category,
            preference=correct_value,
            evidence="User correction",
            confidence=0.9
        )

        # Update active profile
        self._active_profile[category] = correct_value

    def format_with_preferences(
        self,
        content: str
    ) -> str:
        """
        Apply preferences to format content.

        Args:
            content: Content to format

        Returns:
            Formatted content based on preferences
        """
        profile = self.get_profile()

        # Apply verbosity preference
        verbosity = profile.get(PreferenceCategory.VERBOSITY.value, "medium")
        if verbosity == "low" and len(content) > 500:
            # Would implement summarization here
            pass

        # Apply other preferences as needed
        # This is a simplified example

        return content

    def get_evidence_summary(
        self,
        category: str
    ) -> Dict[str, Any]:
        """Get summary of evidence for a category."""
        evidence = self._evidence.get(category, [])

        if not evidence:
            return {"count": 0, "categories": []}

        # Group by action type
        action_counts = defaultdict(int)
        for ev in evidence:
            action_counts[ev.action[:30]] += 1

        return {
            "count": len(evidence),
            "actions": dict(action_counts),
            "recent": [
                {
                    "action": ev.action[:50],
                    "timestamp": ev.timestamp
                }
                for ev in sorted(evidence, key=lambda e: e.timestamp, reverse=True)[:5]
            ]
        }

    def export_preferences(self) -> Dict[str, Any]:
        """Export all preferences for persistence."""
        return {
            "preferences": {
                category: [
                    {
                        "id": p.id,
                        "preference": p.preference,
                        "confidence": p.confidence,
                        "examples": p.examples
                    }
                    for p in prefs
                ]
                for category, prefs in self._preferences.items()
            },
            "active_profile": self._active_profile,
            "exported_at": time.time()
        }

    def import_preferences(self, data: Dict[str, Any]) -> None:
        """Import preferences from persisted data."""
        for category, prefs_data in data.get("preferences", {}).items():
            for pref_data in prefs_data:
                self._preferences[category].append(Preference(
                    id=pref_data["id"],
                    category=category,
                    preference=pref_data["preference"],
                    confidence=pref_data["confidence"],
                    examples=pref_data.get("examples", [])
                ))

        self._active_profile = data.get("active_profile", {})


# Global instance
_preference_tracker: Optional[PreferenceTracker] = None


def get_preference_tracker() -> PreferenceTracker:
    """Get or create preference tracker instance."""
    global _preference_tracker
    if _preference_tracker is None:
        _preference_tracker = PreferenceTracker()
    return _preference_tracker
