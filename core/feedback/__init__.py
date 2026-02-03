"""
BAEL - Real-Time Feedback System
Continuous learning from every interaction.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.Feedback")


class FeedbackType(Enum):
    """Types of feedback."""
    EXPLICIT = "explicit"      # User directly provides feedback
    IMPLICIT = "implicit"      # Inferred from user behavior
    CORRECTION = "correction"  # User corrects an error
    PREFERENCE = "preference"  # User expresses preference
    RATING = "rating"          # Numeric rating
    OUTCOME = "outcome"        # Task success/failure


class SignalType(Enum):
    """Types of implicit signals."""
    ACCEPTANCE = "acceptance"    # User accepted suggestion
    REJECTION = "rejection"      # User rejected/ignored
    MODIFICATION = "modification"  # User modified output
    FOLLOW_UP = "follow_up"      # User asked follow-up
    ABANDONMENT = "abandonment"  # User abandoned interaction
    RETRY = "retry"              # User retried same task


@dataclass
class FeedbackItem:
    """A single feedback item."""
    id: str
    feedback_type: FeedbackType
    value: Any
    context: Dict[str, Any]
    timestamp: float
    interaction_id: Optional[str] = None
    weight: float = 1.0


@dataclass
class LearningSignal:
    """A learning signal derived from feedback."""
    signal_type: str
    strength: float  # -1.0 to 1.0
    topic: str
    evidence: List[str]
    actionable: bool = True


@dataclass
class Preference:
    """A learned user preference."""
    id: str
    category: str
    preference: str
    confidence: float
    examples: List[str]


# Lazy imports
def get_feedback_processor():
    """Get the feedback processor."""
    from .feedback_processor import FeedbackProcessor
    return FeedbackProcessor()


def get_learning_engine():
    """Get the learning engine."""
    from .learning_engine import LearningEngine
    return LearningEngine()


def get_preference_tracker():
    """Get the preference tracker."""
    from .preference_tracker import PreferenceTracker
    return PreferenceTracker()


__all__ = [
    "FeedbackType",
    "SignalType",
    "FeedbackItem",
    "LearningSignal",
    "Preference",
    "get_feedback_processor",
    "get_learning_engine",
    "get_preference_tracker"
]
