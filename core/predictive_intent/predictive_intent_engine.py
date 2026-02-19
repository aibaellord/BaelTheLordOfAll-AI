#!/usr/bin/env python3
"""
BAEL - Predictive Intent Engine
KNOWING WHAT YOU NEED BEFORE YOU KNOW IT

This engine predicts user intent by:
1. Analyzing patterns from past interactions
2. Understanding context deeply
3. Anticipating needs before they're expressed
4. Pre-computing likely next actions
5. Learning from every interaction
6. Cross-referencing with global patterns

"The best assistance is invisible - problems solved before they're noticed." - Ba'el
"""

import asyncio
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4
import hashlib
import math

logger = logging.getLogger("BAEL.PredictiveIntent")


# =============================================================================
# ENUMS
# =============================================================================

class IntentCategory(Enum):
    """Categories of user intent."""
    # Information
    QUERY = "query"
    SEARCH = "search"
    EXPLAIN = "explain"
    COMPARE = "compare"

    # Creation
    CREATE = "create"
    GENERATE = "generate"
    BUILD = "build"
    DESIGN = "design"

    # Modification
    EDIT = "edit"
    REFACTOR = "refactor"
    FIX = "fix"
    UPDATE = "update"

    # Analysis
    ANALYZE = "analyze"
    DEBUG = "debug"
    PROFILE = "profile"
    AUDIT = "audit"

    # Execution
    RUN = "run"
    TEST = "test"
    DEPLOY = "deploy"
    EXECUTE = "execute"

    # Navigation
    NAVIGATE = "navigate"
    FIND = "find"
    OPEN = "open"
    JUMP = "jump"

    # Communication
    DISCUSS = "discuss"
    CLARIFY = "clarify"
    CONFIRM = "confirm"
    REJECT = "reject"

    # Meta
    HELP = "help"
    UNDO = "undo"
    REPEAT = "repeat"
    STOP = "stop"


class Urgency(Enum):
    """Urgency levels."""
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.3
    BACKGROUND = 0.1


class Confidence(Enum):
    """Confidence levels for predictions."""
    CERTAIN = 0.95
    HIGH = 0.80
    MEDIUM = 0.60
    LOW = 0.40
    UNCERTAIN = 0.20


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Intent:
    """A predicted or detected intent."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Intent details
    category: IntentCategory = IntentCategory.QUERY
    action: str = ""
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Assessment
    confidence: float = 0.5
    urgency: Urgency = Urgency.MEDIUM

    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    source: str = "prediction"  # prediction, explicit, inferred

    # Timing
    predicted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class Prediction:
    """A prediction of future intent."""
    id: str = field(default_factory=lambda: str(uuid4()))

    intent: Intent = field(default_factory=Intent)

    # Prediction metadata
    probability: float = 0.5
    reasoning: str = ""

    # Action recommendation
    suggested_action: str = ""
    pre_compute: bool = False  # Should we pre-compute this?

    # Related predictions
    alternatives: List['Prediction'] = field(default_factory=list)

    # Timing
    time_horizon_seconds: int = 60  # How far ahead is this prediction?


@dataclass
class InteractionPattern:
    """A detected pattern in user interactions."""
    id: str = field(default_factory=lambda: str(uuid4()))

    # Pattern details
    sequence: List[IntentCategory] = field(default_factory=list)
    frequency: int = 0

    # Context conditions
    time_of_day: Optional[str] = None  # morning, afternoon, evening
    day_of_week: Optional[str] = None
    project_type: Optional[str] = None

    # Prediction
    likely_next: IntentCategory = IntentCategory.QUERY
    next_probability: float = 0.5


@dataclass
class UserContext:
    """Current context about the user session."""
    session_id: str = field(default_factory=lambda: str(uuid4()))

    # Recent activity
    recent_intents: List[Intent] = field(default_factory=list)
    current_file: Optional[str] = None
    current_project: Optional[str] = None

    # Session state
    session_start: datetime = field(default_factory=datetime.utcnow)
    interactions_count: int = 0

    # Inferred state
    focus_area: Optional[str] = None
    current_task: Optional[str] = None
    frustration_level: float = 0.0  # 0-1, detected from patterns

    # Preferences (learned)
    preferred_verbosity: float = 0.5
    preferred_detail_level: float = 0.5


# =============================================================================
# PATTERN MATCHERS
# =============================================================================

class IntentMatcher:
    """Matches text to intent categories."""

    def __init__(self):
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> Dict[IntentCategory, List[re.Pattern]]:
        """Build regex patterns for intent matching."""
        return {
            IntentCategory.CREATE: [
                re.compile(r'\b(create|make|build|generate|new|add)\b', re.I),
            ],
            IntentCategory.FIX: [
                re.compile(r'\b(fix|repair|solve|resolve|debug|correct)\b', re.I),
            ],
            IntentCategory.EXPLAIN: [
                re.compile(r'\b(explain|describe|what is|how does|why)\b', re.I),
            ],
            IntentCategory.REFACTOR: [
                re.compile(r'\b(refactor|improve|optimize|clean up|simplify)\b', re.I),
            ],
            IntentCategory.TEST: [
                re.compile(r'\b(test|verify|check|validate|ensure)\b', re.I),
            ],
            IntentCategory.ANALYZE: [
                re.compile(r'\b(analyze|review|examine|inspect|audit)\b', re.I),
            ],
            IntentCategory.SEARCH: [
                re.compile(r'\b(find|search|look for|where is|locate)\b', re.I),
            ],
            IntentCategory.RUN: [
                re.compile(r'\b(run|execute|start|launch|deploy)\b', re.I),
            ],
            IntentCategory.HELP: [
                re.compile(r'\b(help|assist|support|guide)\b', re.I),
            ],
        }

    def match(self, text: str) -> List[Tuple[IntentCategory, float]]:
        """Match text to intent categories with confidence."""
        matches = []

        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    # Calculate confidence based on match quality
                    match = pattern.search(text)
                    if match:
                        # Boost confidence for early matches (more intentional)
                        position_factor = 1.0 - (match.start() / max(len(text), 1)) * 0.3
                        confidence = 0.7 * position_factor
                        matches.append((category, confidence))

        # Sort by confidence
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches


# =============================================================================
# PREDICTIVE ENGINE
# =============================================================================

class PredictiveIntentEngine:
    """
    Predicts user intent before it's expressed.

    Uses:
    - Pattern recognition from history
    - Context analysis
    - Temporal patterns
    - Cross-user learning
    """

    def __init__(self):
        self.matcher = IntentMatcher()

        # Pattern storage
        self.patterns: List[InteractionPattern] = []
        self.sequence_buffer: List[IntentCategory] = []

        # User context
        self._context: UserContext = UserContext()

        # Prediction cache
        self._predictions: List[Prediction] = []
        self._pre_computed: Dict[str, Any] = {}

        # Learning
        self._sequence_counts: Dict[Tuple, int] = defaultdict(int)
        self._transition_matrix: Dict[IntentCategory, Dict[IntentCategory, float]] = {}

        self._initialize_transition_matrix()

        logger.info("PredictiveIntentEngine initialized")

    def _initialize_transition_matrix(self) -> None:
        """Initialize intent transition probabilities."""
        # Based on common coding workflows
        common_transitions = {
            IntentCategory.CREATE: {
                IntentCategory.TEST: 0.3,
                IntentCategory.RUN: 0.2,
                IntentCategory.EDIT: 0.2,
                IntentCategory.FIX: 0.15,
            },
            IntentCategory.FIX: {
                IntentCategory.TEST: 0.4,
                IntentCategory.RUN: 0.3,
                IntentCategory.ANALYZE: 0.1,
            },
            IntentCategory.TEST: {
                IntentCategory.FIX: 0.4,
                IntentCategory.RUN: 0.2,
                IntentCategory.ANALYZE: 0.2,
            },
            IntentCategory.ANALYZE: {
                IntentCategory.FIX: 0.3,
                IntentCategory.REFACTOR: 0.3,
                IntentCategory.EXPLAIN: 0.2,
            },
            IntentCategory.SEARCH: {
                IntentCategory.NAVIGATE: 0.3,
                IntentCategory.EDIT: 0.3,
                IntentCategory.EXPLAIN: 0.2,
            },
            IntentCategory.EXPLAIN: {
                IntentCategory.CREATE: 0.2,
                IntentCategory.EDIT: 0.2,
                IntentCategory.SEARCH: 0.2,
            },
        }

        self._transition_matrix = common_transitions

    def detect_intent(self, text: str) -> Intent:
        """Detect intent from user text."""
        matches = self.matcher.match(text)

        if matches:
            category, confidence = matches[0]
        else:
            category = IntentCategory.QUERY
            confidence = 0.3

        intent = Intent(
            category=category,
            action=text.split()[0] if text else "",
            target=self._extract_target(text),
            confidence=confidence,
            source="explicit"
        )

        # Update context
        self._update_context(intent)

        # Learn from this interaction
        self._learn_sequence(intent.category)

        return intent

    def _extract_target(self, text: str) -> str:
        """Extract the target of the intent."""
        # Look for file paths
        file_match = re.search(r'[\w/.-]+\.\w+', text)
        if file_match:
            return file_match.group()

        # Look for function/class names
        code_match = re.search(r'\b([A-Z][a-z]+[A-Z]\w*|\w+_\w+)\b', text)
        if code_match:
            return code_match.group()

        return ""

    def _update_context(self, intent: Intent) -> None:
        """Update user context with new intent."""
        self._context.recent_intents.append(intent)
        self._context.recent_intents = self._context.recent_intents[-20:]  # Keep last 20
        self._context.interactions_count += 1

        # Update focus area
        if intent.target:
            self._context.focus_area = intent.target

        # Detect frustration (multiple fix attempts)
        recent_fixes = sum(
            1 for i in self._context.recent_intents[-5:]
            if i.category == IntentCategory.FIX
        )
        self._context.frustration_level = min(1.0, recent_fixes / 5)

    def _learn_sequence(self, category: IntentCategory) -> None:
        """Learn from intent sequences."""
        self.sequence_buffer.append(category)
        self.sequence_buffer = self.sequence_buffer[-10:]  # Keep last 10

        # Count 2-grams and 3-grams
        if len(self.sequence_buffer) >= 2:
            bigram = tuple(self.sequence_buffer[-2:])
            self._sequence_counts[bigram] += 1

        if len(self.sequence_buffer) >= 3:
            trigram = tuple(self.sequence_buffer[-3:])
            self._sequence_counts[trigram] += 1

        # Update transition matrix
        if len(self.sequence_buffer) >= 2:
            prev = self.sequence_buffer[-2]
            curr = self.sequence_buffer[-1]

            if prev not in self._transition_matrix:
                self._transition_matrix[prev] = {}

            if curr not in self._transition_matrix[prev]:
                self._transition_matrix[prev][curr] = 0.0

            # Incremental update
            self._transition_matrix[prev][curr] = (
                self._transition_matrix[prev][curr] * 0.9 + 0.1
            )

    async def predict_next(
        self,
        num_predictions: int = 3
    ) -> List[Prediction]:
        """Predict the most likely next intents."""
        predictions = []

        if not self._context.recent_intents:
            # No history, use defaults
            return self._default_predictions()

        last_intent = self._context.recent_intents[-1]

        # Get transition probabilities
        transitions = self._transition_matrix.get(last_intent.category, {})

        # Sort by probability
        sorted_transitions = sorted(
            transitions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:num_predictions]

        for next_category, probability in sorted_transitions:
            prediction = Prediction(
                intent=Intent(
                    category=next_category,
                    confidence=probability,
                    source="prediction"
                ),
                probability=probability,
                reasoning=f"Based on transition from {last_intent.category.value}",
                suggested_action=self._get_suggested_action(next_category),
                pre_compute=probability > 0.5
            )
            predictions.append(prediction)

        # Add context-based predictions
        context_predictions = await self._predict_from_context()
        predictions.extend(context_predictions)

        # Deduplicate and sort
        seen = set()
        unique = []
        for p in predictions:
            key = p.intent.category.value
            if key not in seen:
                seen.add(key)
                unique.append(p)

        unique.sort(key=lambda x: x.probability, reverse=True)

        self._predictions = unique[:num_predictions]

        # Pre-compute high-probability predictions
        await self._pre_compute_predictions()

        return self._predictions

    def _default_predictions(self) -> List[Prediction]:
        """Default predictions for new sessions."""
        return [
            Prediction(
                intent=Intent(category=IntentCategory.CREATE),
                probability=0.3,
                reasoning="Common starting action"
            ),
            Prediction(
                intent=Intent(category=IntentCategory.SEARCH),
                probability=0.3,
                reasoning="Common starting action"
            ),
            Prediction(
                intent=Intent(category=IntentCategory.HELP),
                probability=0.2,
                reasoning="New session exploration"
            ),
        ]

    async def _predict_from_context(self) -> List[Prediction]:
        """Generate predictions based on current context."""
        predictions = []

        # Time-based predictions
        hour = datetime.now().hour
        if hour < 10:
            # Morning: likely reviewing/planning
            predictions.append(Prediction(
                intent=Intent(category=IntentCategory.ANALYZE),
                probability=0.3,
                reasoning="Morning review pattern"
            ))
        elif hour > 17:
            # Evening: likely wrapping up
            predictions.append(Prediction(
                intent=Intent(category=IntentCategory.TEST),
                probability=0.3,
                reasoning="End of day validation"
            ))

        # Frustration-based predictions
        if self._context.frustration_level > 0.5:
            predictions.append(Prediction(
                intent=Intent(category=IntentCategory.HELP),
                probability=0.4,
                reasoning="Detected difficulty, may need help"
            ))

        # Focus-based predictions
        if self._context.focus_area:
            if ".test." in self._context.focus_area or "_test" in self._context.focus_area:
                predictions.append(Prediction(
                    intent=Intent(category=IntentCategory.RUN),
                    probability=0.4,
                    reasoning="Working on tests, likely to run them"
                ))

        return predictions

    def _get_suggested_action(self, category: IntentCategory) -> str:
        """Get suggested action for an intent category."""
        suggestions = {
            IntentCategory.TEST: "Run test suite",
            IntentCategory.FIX: "Analyze and fix issues",
            IntentCategory.REFACTOR: "Suggest refactoring improvements",
            IntentCategory.CREATE: "Generate new code/files",
            IntentCategory.ANALYZE: "Run code analysis",
            IntentCategory.RUN: "Execute code/commands",
            IntentCategory.SEARCH: "Search codebase",
            IntentCategory.EXPLAIN: "Explain code/concepts",
        }
        return suggestions.get(category, "Assist with task")

    async def _pre_compute_predictions(self) -> None:
        """Pre-compute high-probability predictions."""
        for prediction in self._predictions:
            if prediction.pre_compute and prediction.probability > 0.6:
                key = f"{prediction.intent.category.value}_{prediction.intent.target}"

                # Mark as pre-computing
                logger.debug(f"Pre-computing: {key}")

                # In real implementation, would trigger actual pre-computation
                self._pre_computed[key] = {
                    "status": "ready",
                    "computed_at": datetime.utcnow().isoformat()
                }

    def get_pre_computed(self, category: IntentCategory, target: str = "") -> Optional[Any]:
        """Get pre-computed result if available."""
        key = f"{category.value}_{target}"
        return self._pre_computed.get(key)

    def get_context(self) -> UserContext:
        """Get current user context."""
        return self._context

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        intent_counts = defaultdict(int)
        for intent in self._context.recent_intents:
            intent_counts[intent.category.value] += 1

        return {
            "session_id": self._context.session_id,
            "duration_minutes": (
                datetime.utcnow() - self._context.session_start
            ).seconds / 60,
            "interactions": self._context.interactions_count,
            "focus_area": self._context.focus_area,
            "frustration_level": self._context.frustration_level,
            "intent_distribution": dict(intent_counts),
            "active_predictions": len(self._predictions),
            "pre_computed_ready": len(self._pre_computed)
        }

    async def suggest_proactive_actions(self) -> List[Dict[str, Any]]:
        """Suggest proactive actions based on predictions."""
        suggestions = []

        predictions = await self.predict_next(5)

        for pred in predictions:
            if pred.probability > 0.4:
                suggestion = {
                    "action": pred.suggested_action,
                    "intent": pred.intent.category.value,
                    "probability": pred.probability,
                    "reasoning": pred.reasoning,
                    "ready": pred.intent.category.value in str(self._pre_computed)
                }
                suggestions.append(suggestion)

        # Add context-specific suggestions
        if self._context.frustration_level > 0.7:
            suggestions.insert(0, {
                "action": "Would you like some help? I noticed you might be stuck.",
                "intent": "help",
                "probability": 0.9,
                "reasoning": "High frustration detected",
                "ready": True
            })

        return suggestions


# =============================================================================
# FACTORY
# =============================================================================

async def create_predictive_engine() -> PredictiveIntentEngine:
    """Create a new Predictive Intent Engine."""
    return PredictiveIntentEngine()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    async def main():
        print("🔮 BAEL Predictive Intent Engine")
        print("=" * 50)

        engine = await create_predictive_engine()

        # Simulate interactions
        interactions = [
            "create a new API endpoint",
            "add error handling",
            "test the endpoint",
            "fix the failing test",
            "run tests again"
        ]

        print("\n📝 Simulating interactions...")

        for text in interactions:
            print(f"\n> {text}")
            intent = engine.detect_intent(text)
            print(f"  Detected: {intent.category.value} (confidence: {intent.confidence:.2f})")

            predictions = await engine.predict_next(2)
            if predictions:
                print(f"  Next likely: {predictions[0].intent.category.value} ({predictions[0].probability:.2f})")

        print("\n" + "=" * 50)
        print("📊 Session Summary:")
        summary = engine.get_session_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")

        print("\n💡 Proactive Suggestions:")
        suggestions = await engine.suggest_proactive_actions()
        for i, s in enumerate(suggestions[:3], 1):
            print(f"  {i}. {s['action']} (prob: {s['probability']:.2f})")

        print("\n✅ Predictive engine ready")

    asyncio.run(main())
