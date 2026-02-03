#!/usr/bin/env python3
"""
BAEL - Intent Manager
Advanced intent recognition and management for AI agents.

Features:
- Intent classification
- Intent hierarchy
- Intent disambiguation
- Intent tracking
- Intent fulfillment
- Multi-intent handling
- Context-aware intent
- Intent confidence scoring
"""

import asyncio
import hashlib
import math
import random
import re
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

class IntentType(Enum):
    """Intent types."""
    QUERY = "query"
    COMMAND = "command"
    REQUEST = "request"
    STATEMENT = "statement"
    CONFIRMATION = "confirmation"
    NEGATION = "negation"
    GREETING = "greeting"
    FAREWELL = "farewell"
    UNKNOWN = "unknown"


class IntentStatus(Enum):
    """Intent status."""
    PENDING = "pending"
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class IntentPriority(Enum):
    """Intent priority."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class DisambiguationStrategy(Enum):
    """Disambiguation strategy."""
    ASK_USER = "ask_user"
    CONTEXT = "context"
    MOST_LIKELY = "most_likely"
    COMBINE = "combine"


class SlotType(Enum):
    """Slot types for intent extraction."""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    ENTITY = "entity"
    BOOLEAN = "boolean"
    LIST = "list"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Slot:
    """Intent slot (entity)."""
    name: str = ""
    slot_type: SlotType = SlotType.TEXT
    value: Any = None
    required: bool = False
    confidence: float = 0.0
    alternatives: List[Any] = field(default_factory=list)


@dataclass
class IntentPattern:
    """Pattern for intent matching."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    patterns: List[str] = field(default_factory=list)
    intent_name: str = ""
    slots: List[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class IntentMatch:
    """Intent match result."""
    intent_name: str = ""
    intent_type: IntentType = IntentType.UNKNOWN
    confidence: float = 0.0
    slots: Dict[str, Slot] = field(default_factory=dict)
    raw_text: str = ""
    matched_pattern: str = ""
    alternatives: List["IntentMatch"] = field(default_factory=list)


@dataclass
class Intent:
    """Intent instance."""
    intent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    intent_type: IntentType = IntentType.UNKNOWN
    status: IntentStatus = IntentStatus.PENDING
    priority: IntentPriority = IntentPriority.MEDIUM
    confidence: float = 0.0
    slots: Dict[str, Slot] = field(default_factory=dict)
    parent_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    fulfilled_at: Optional[datetime] = None


@dataclass
class IntentHandler:
    """Handler for intent."""
    handler_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent_name: str = ""
    handler: Optional[Callable] = None
    required_slots: List[str] = field(default_factory=list)


@dataclass
class ConversationContext:
    """Conversation context for intent resolution."""
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intents: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    topic: str = ""


@dataclass
class IntentStats:
    """Intent statistics."""
    total_intents: int = 0
    fulfilled_count: int = 0
    failed_count: int = 0
    avg_confidence: float = 0.0
    intent_counts: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# PATTERN MATCHER
# =============================================================================

class PatternMatcher:
    """Match patterns for intent recognition."""

    def __init__(self):
        self._patterns: Dict[str, List[IntentPattern]] = defaultdict(list)

    def add_pattern(
        self,
        intent_name: str,
        patterns: List[str],
        slots: Optional[List[str]] = None,
        priority: int = 0
    ) -> IntentPattern:
        """Add intent pattern."""
        pattern = IntentPattern(
            patterns=patterns,
            intent_name=intent_name,
            slots=slots or [],
            priority=priority
        )
        self._patterns[intent_name].append(pattern)
        return pattern

    def match(self, text: str) -> List[Tuple[str, float, str]]:
        """Match text against patterns."""
        text_lower = text.lower().strip()
        matches = []

        for intent_name, patterns_list in self._patterns.items():
            for pattern_obj in patterns_list:
                for pattern in pattern_obj.patterns:
                    # Direct match
                    if pattern.lower() in text_lower:
                        score = len(pattern) / len(text_lower)
                        matches.append((intent_name, score, pattern))

                    # Regex match
                    try:
                        if re.search(pattern, text_lower, re.IGNORECASE):
                            score = 0.8
                            matches.append((intent_name, score, pattern))
                    except re.error:
                        pass

        # Sort by score
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def get_patterns(self, intent_name: str) -> List[IntentPattern]:
        """Get patterns for intent."""
        return self._patterns.get(intent_name, [])


# =============================================================================
# SLOT EXTRACTOR
# =============================================================================

class SlotExtractor:
    """Extract slots from text."""

    # Common patterns
    NUMBER_PATTERN = r'\b(\d+(?:\.\d+)?)\b'
    DATE_PATTERN = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
    TIME_PATTERN = r'\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]m)?)\b'

    def __init__(self):
        self._custom_extractors: Dict[str, Callable[[str], Any]] = {}

    def register_extractor(
        self,
        slot_name: str,
        extractor: Callable[[str], Any]
    ) -> None:
        """Register custom extractor."""
        self._custom_extractors[slot_name] = extractor

    def extract(
        self,
        text: str,
        slot_definitions: Dict[str, SlotType]
    ) -> Dict[str, Slot]:
        """Extract slots from text."""
        slots = {}

        for slot_name, slot_type in slot_definitions.items():
            # Check custom extractor
            if slot_name in self._custom_extractors:
                value = self._custom_extractors[slot_name](text)
                if value is not None:
                    slots[slot_name] = Slot(
                        name=slot_name,
                        slot_type=slot_type,
                        value=value,
                        confidence=0.9
                    )
                continue

            # Default extraction by type
            value = self._extract_by_type(text, slot_type)
            if value is not None:
                slots[slot_name] = Slot(
                    name=slot_name,
                    slot_type=slot_type,
                    value=value,
                    confidence=0.7
                )

        return slots

    def _extract_by_type(self, text: str, slot_type: SlotType) -> Any:
        """Extract by slot type."""
        if slot_type == SlotType.NUMBER:
            match = re.search(self.NUMBER_PATTERN, text)
            if match:
                return float(match.group(1))

        elif slot_type == SlotType.DATE:
            match = re.search(self.DATE_PATTERN, text)
            if match:
                return match.group(1)

        elif slot_type == SlotType.TIME:
            match = re.search(self.TIME_PATTERN, text, re.IGNORECASE)
            if match:
                return match.group(1)

        elif slot_type == SlotType.BOOLEAN:
            text_lower = text.lower()
            if any(w in text_lower for w in ['yes', 'true', 'ok', 'sure', 'yeah']):
                return True
            if any(w in text_lower for w in ['no', 'false', 'nope', 'cancel']):
                return False

        elif slot_type == SlotType.TEXT:
            return text

        return None

    def extract_entities(
        self,
        text: str,
        entity_names: List[str]
    ) -> Dict[str, str]:
        """Extract named entities."""
        # Simple word matching
        entities = {}
        words = text.split()

        for entity in entity_names:
            for word in words:
                if entity.lower() in word.lower():
                    entities[entity] = word

        return entities


# =============================================================================
# INTENT CLASSIFIER
# =============================================================================

class IntentClassifier:
    """Classify intent from text."""

    # Intent indicators
    QUERY_INDICATORS = ['what', 'who', 'when', 'where', 'why', 'how', 'which', '?']
    COMMAND_INDICATORS = ['do', 'make', 'create', 'delete', 'update', 'run', 'start', 'stop']
    REQUEST_INDICATORS = ['please', 'can you', 'could you', 'would you', 'i need', 'i want']
    CONFIRMATION_INDICATORS = ['yes', 'ok', 'sure', 'confirm', 'agree', 'correct']
    NEGATION_INDICATORS = ['no', 'cancel', 'stop', 'don\'t', 'nevermind', 'wrong']
    GREETING_INDICATORS = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'greetings']
    FAREWELL_INDICATORS = ['bye', 'goodbye', 'see you', 'farewell', 'later', 'take care']

    def classify_type(self, text: str) -> Tuple[IntentType, float]:
        """Classify intent type."""
        text_lower = text.lower()

        # Check indicators
        scores = {
            IntentType.QUERY: self._score_indicators(text_lower, self.QUERY_INDICATORS),
            IntentType.COMMAND: self._score_indicators(text_lower, self.COMMAND_INDICATORS),
            IntentType.REQUEST: self._score_indicators(text_lower, self.REQUEST_INDICATORS),
            IntentType.CONFIRMATION: self._score_indicators(text_lower, self.CONFIRMATION_INDICATORS),
            IntentType.NEGATION: self._score_indicators(text_lower, self.NEGATION_INDICATORS),
            IntentType.GREETING: self._score_indicators(text_lower, self.GREETING_INDICATORS),
            IntentType.FAREWELL: self._score_indicators(text_lower, self.FAREWELL_INDICATORS),
        }

        # Get best match
        best_type = max(scores.items(), key=lambda x: x[1])

        if best_type[1] > 0:
            return best_type[0], min(best_type[1], 1.0)

        return IntentType.STATEMENT, 0.5

    def _score_indicators(self, text: str, indicators: List[str]) -> float:
        """Score text against indicators."""
        count = sum(1 for ind in indicators if ind in text)
        return count / len(indicators) if indicators else 0.0


# =============================================================================
# INTENT DISAMBIGUATOR
# =============================================================================

class IntentDisambiguator:
    """Disambiguate between multiple intent matches."""

    def __init__(
        self,
        strategy: DisambiguationStrategy = DisambiguationStrategy.MOST_LIKELY
    ):
        self._strategy = strategy

    def disambiguate(
        self,
        matches: List[IntentMatch],
        context: Optional[ConversationContext] = None
    ) -> IntentMatch:
        """Disambiguate intents."""
        if not matches:
            return IntentMatch(intent_name="unknown", confidence=0.0)

        if len(matches) == 1:
            return matches[0]

        if self._strategy == DisambiguationStrategy.MOST_LIKELY:
            return self._most_likely(matches)

        elif self._strategy == DisambiguationStrategy.CONTEXT:
            return self._use_context(matches, context)

        elif self._strategy == DisambiguationStrategy.COMBINE:
            return self._combine(matches)

        return matches[0]

    def _most_likely(self, matches: List[IntentMatch]) -> IntentMatch:
        """Return most likely match."""
        return max(matches, key=lambda m: m.confidence)

    def _use_context(
        self,
        matches: List[IntentMatch],
        context: Optional[ConversationContext]
    ) -> IntentMatch:
        """Use context to disambiguate."""
        if not context or not context.intents:
            return self._most_likely(matches)

        # Prefer intents related to recent context
        recent_intents = set(context.intents[-5:])

        for match in matches:
            if match.intent_name in recent_intents:
                match.confidence *= 1.2  # Boost

        return self._most_likely(matches)

    def _combine(self, matches: List[IntentMatch]) -> IntentMatch:
        """Combine multiple intents."""
        # Keep top match but include alternatives
        top = max(matches, key=lambda m: m.confidence)
        top.alternatives = [m for m in matches if m != top][:3]
        return top

    def needs_clarification(self, matches: List[IntentMatch]) -> bool:
        """Check if clarification is needed."""
        if len(matches) < 2:
            return False

        # Check if top two are close in confidence
        sorted_matches = sorted(matches, key=lambda m: m.confidence, reverse=True)
        diff = sorted_matches[0].confidence - sorted_matches[1].confidence

        return diff < 0.2

    def generate_clarification_prompt(
        self,
        matches: List[IntentMatch]
    ) -> str:
        """Generate clarification prompt."""
        options = [m.intent_name for m in matches[:3]]
        return f"Did you mean: {', '.join(options)}?"


# =============================================================================
# INTENT HIERARCHY
# =============================================================================

class IntentHierarchy:
    """Manage hierarchical intents."""

    def __init__(self):
        self._parent_map: Dict[str, str] = {}
        self._children_map: Dict[str, List[str]] = defaultdict(list)

    def add_child(self, parent: str, child: str) -> None:
        """Add child intent."""
        self._parent_map[child] = parent
        self._children_map[parent].append(child)

    def get_parent(self, intent: str) -> Optional[str]:
        """Get parent intent."""
        return self._parent_map.get(intent)

    def get_children(self, intent: str) -> List[str]:
        """Get child intents."""
        return self._children_map.get(intent, [])

    def get_ancestors(self, intent: str) -> List[str]:
        """Get all ancestors."""
        ancestors = []
        current = intent

        while current in self._parent_map:
            parent = self._parent_map[current]
            ancestors.append(parent)
            current = parent

        return ancestors

    def get_descendants(self, intent: str) -> List[str]:
        """Get all descendants."""
        descendants = []
        to_process = self._children_map.get(intent, []).copy()

        while to_process:
            child = to_process.pop(0)
            descendants.append(child)
            to_process.extend(self._children_map.get(child, []))

        return descendants

    def is_descendant(self, intent: str, ancestor: str) -> bool:
        """Check if intent is descendant of ancestor."""
        return ancestor in self.get_ancestors(intent)


# =============================================================================
# INTENT TRACKER
# =============================================================================

class IntentTracker:
    """Track intents in conversation."""

    def __init__(self, max_history: int = 100):
        self._active_intents: Dict[str, Intent] = {}
        self._history: deque = deque(maxlen=max_history)
        self._fulfillment_callbacks: Dict[str, List[Callable]] = defaultdict(list)

    def track(self, intent: Intent) -> None:
        """Track intent."""
        self._active_intents[intent.intent_id] = intent
        self._history.append(intent)

    def update_status(
        self,
        intent_id: str,
        status: IntentStatus
    ) -> Optional[Intent]:
        """Update intent status."""
        if intent_id in self._active_intents:
            intent = self._active_intents[intent_id]
            intent.status = status

            if status == IntentStatus.FULFILLED:
                intent.fulfilled_at = datetime.now()
                self._trigger_fulfillment(intent)

            if status in [IntentStatus.FULFILLED, IntentStatus.CANCELLED, IntentStatus.FAILED]:
                del self._active_intents[intent_id]

            return intent
        return None

    def get_active(self) -> List[Intent]:
        """Get active intents."""
        return list(self._active_intents.values())

    def get_by_status(self, status: IntentStatus) -> List[Intent]:
        """Get intents by status."""
        return [i for i in self._active_intents.values() if i.status == status]

    def get_history(self, n: int = 10) -> List[Intent]:
        """Get intent history."""
        return list(self._history)[-n:]

    def on_fulfillment(
        self,
        intent_name: str,
        callback: Callable[[Intent], None]
    ) -> None:
        """Register fulfillment callback."""
        self._fulfillment_callbacks[intent_name].append(callback)

    def _trigger_fulfillment(self, intent: Intent) -> None:
        """Trigger fulfillment callbacks."""
        for callback in self._fulfillment_callbacks.get(intent.name, []):
            try:
                callback(intent)
            except Exception:
                pass


# =============================================================================
# INTENT FULFILLER
# =============================================================================

class IntentFulfiller:
    """Fulfill intents."""

    def __init__(self):
        self._handlers: Dict[str, IntentHandler] = {}

    def register_handler(
        self,
        intent_name: str,
        handler: Callable[[Intent], Any],
        required_slots: Optional[List[str]] = None
    ) -> IntentHandler:
        """Register intent handler."""
        intent_handler = IntentHandler(
            intent_name=intent_name,
            handler=handler,
            required_slots=required_slots or []
        )
        self._handlers[intent_name] = intent_handler
        return intent_handler

    async def fulfill(self, intent: Intent) -> Tuple[bool, Any]:
        """Fulfill intent."""
        if intent.name not in self._handlers:
            return False, f"No handler for intent: {intent.name}"

        handler = self._handlers[intent.name]

        # Check required slots
        missing = self._check_slots(intent, handler.required_slots)
        if missing:
            return False, f"Missing slots: {missing}"

        # Execute handler
        try:
            if handler.handler:
                if asyncio.iscoroutinefunction(handler.handler):
                    result = await handler.handler(intent)
                else:
                    result = handler.handler(intent)
                return True, result
            return False, "Handler not defined"
        except Exception as e:
            return False, str(e)

    def _check_slots(
        self,
        intent: Intent,
        required: List[str]
    ) -> List[str]:
        """Check required slots."""
        missing = []
        for slot_name in required:
            if slot_name not in intent.slots or intent.slots[slot_name].value is None:
                missing.append(slot_name)
        return missing

    def can_fulfill(self, intent: Intent) -> bool:
        """Check if intent can be fulfilled."""
        if intent.name not in self._handlers:
            return False

        handler = self._handlers[intent.name]
        missing = self._check_slots(intent, handler.required_slots)
        return len(missing) == 0


# =============================================================================
# MULTI-INTENT HANDLER
# =============================================================================

class MultiIntentHandler:
    """Handle multiple intents in single input."""

    SEPARATORS = [' and ', ' then ', ' also ', '; ', ', and ']

    def split_intents(self, text: str) -> List[str]:
        """Split text into multiple intent segments."""
        segments = [text]

        for sep in self.SEPARATORS:
            new_segments = []
            for segment in segments:
                parts = segment.split(sep)
                new_segments.extend(parts)
            segments = new_segments

        # Clean and filter
        return [s.strip() for s in segments if s.strip()]

    def detect_multi_intent(self, text: str) -> bool:
        """Detect if text contains multiple intents."""
        return any(sep in text.lower() for sep in self.SEPARATORS)


# =============================================================================
# INTENT MANAGER
# =============================================================================

class IntentManager:
    """
    Intent Manager for BAEL.

    Advanced intent recognition and management.
    """

    def __init__(
        self,
        disambiguation_strategy: DisambiguationStrategy = DisambiguationStrategy.CONTEXT
    ):
        self._pattern_matcher = PatternMatcher()
        self._slot_extractor = SlotExtractor()
        self._classifier = IntentClassifier()
        self._disambiguator = IntentDisambiguator(disambiguation_strategy)
        self._hierarchy = IntentHierarchy()
        self._tracker = IntentTracker()
        self._fulfiller = IntentFulfiller()
        self._multi_handler = MultiIntentHandler()
        self._context = ConversationContext()
        self._stats = IntentStats()

    # -------------------------------------------------------------------------
    # PATTERN REGISTRATION
    # -------------------------------------------------------------------------

    def register_intent(
        self,
        intent_name: str,
        patterns: List[str],
        slots: Optional[Dict[str, SlotType]] = None,
        handler: Optional[Callable[[Intent], Any]] = None,
        required_slots: Optional[List[str]] = None,
        parent: Optional[str] = None
    ) -> None:
        """Register intent with patterns and handler."""
        # Add patterns
        slot_names = list(slots.keys()) if slots else []
        self._pattern_matcher.add_pattern(intent_name, patterns, slot_names)

        # Add handler
        if handler:
            self._fulfiller.register_handler(intent_name, handler, required_slots)

        # Add hierarchy
        if parent:
            self._hierarchy.add_child(parent, intent_name)

    # -------------------------------------------------------------------------
    # INTENT RECOGNITION
    # -------------------------------------------------------------------------

    def recognize(
        self,
        text: str,
        slot_definitions: Optional[Dict[str, SlotType]] = None
    ) -> IntentMatch:
        """Recognize intent from text."""
        # Classify type
        intent_type, type_confidence = self._classifier.classify_type(text)

        # Match patterns
        matches = self._pattern_matcher.match(text)

        # Create intent matches
        intent_matches = []
        for intent_name, score, pattern in matches:
            # Extract slots
            slots = {}
            if slot_definitions:
                slots = self._slot_extractor.extract(text, slot_definitions)

            match = IntentMatch(
                intent_name=intent_name,
                intent_type=intent_type,
                confidence=score * type_confidence,
                slots=slots,
                raw_text=text,
                matched_pattern=pattern
            )
            intent_matches.append(match)

        # Disambiguate
        if intent_matches:
            result = self._disambiguator.disambiguate(intent_matches, self._context)
        else:
            result = IntentMatch(
                intent_name="unknown",
                intent_type=intent_type,
                confidence=type_confidence * 0.5,
                raw_text=text
            )

        # Update context
        if result.intent_name != "unknown":
            self._context.intents.append(result.intent_name)
            self._context.history.append(text)

        return result

    def recognize_multiple(
        self,
        text: str,
        slot_definitions: Optional[Dict[str, SlotType]] = None
    ) -> List[IntentMatch]:
        """Recognize multiple intents."""
        if not self._multi_handler.detect_multi_intent(text):
            return [self.recognize(text, slot_definitions)]

        segments = self._multi_handler.split_intents(text)
        return [self.recognize(seg, slot_definitions) for seg in segments]

    # -------------------------------------------------------------------------
    # INTENT CREATION
    # -------------------------------------------------------------------------

    def create_intent(
        self,
        match: IntentMatch,
        priority: IntentPriority = IntentPriority.MEDIUM
    ) -> Intent:
        """Create intent from match."""
        intent = Intent(
            name=match.intent_name,
            intent_type=match.intent_type,
            priority=priority,
            confidence=match.confidence,
            slots=match.slots,
            context={"raw_text": match.raw_text}
        )

        # Track
        self._tracker.track(intent)

        # Update stats
        self._stats.total_intents += 1
        if intent.name not in self._stats.intent_counts:
            self._stats.intent_counts[intent.name] = 0
        self._stats.intent_counts[intent.name] += 1

        return intent

    # -------------------------------------------------------------------------
    # INTENT FULFILLMENT
    # -------------------------------------------------------------------------

    async def fulfill(self, intent: Intent) -> Tuple[bool, Any]:
        """Fulfill intent."""
        intent.status = IntentStatus.ACTIVE

        success, result = await self._fulfiller.fulfill(intent)

        if success:
            self._tracker.update_status(intent.intent_id, IntentStatus.FULFILLED)
            self._stats.fulfilled_count += 1
        else:
            self._tracker.update_status(intent.intent_id, IntentStatus.FAILED)
            self._stats.failed_count += 1

        return success, result

    def can_fulfill(self, intent: Intent) -> bool:
        """Check if intent can be fulfilled."""
        return self._fulfiller.can_fulfill(intent)

    def get_missing_slots(self, intent: Intent) -> List[str]:
        """Get missing slots for intent."""
        if intent.name not in self._fulfiller._handlers:
            return []

        handler = self._fulfiller._handlers[intent.name]
        missing = []

        for slot_name in handler.required_slots:
            if slot_name not in intent.slots or intent.slots[slot_name].value is None:
                missing.append(slot_name)

        return missing

    # -------------------------------------------------------------------------
    # SLOT EXTRACTION
    # -------------------------------------------------------------------------

    def extract_slots(
        self,
        text: str,
        slot_definitions: Dict[str, SlotType]
    ) -> Dict[str, Slot]:
        """Extract slots from text."""
        return self._slot_extractor.extract(text, slot_definitions)

    def register_slot_extractor(
        self,
        slot_name: str,
        extractor: Callable[[str], Any]
    ) -> None:
        """Register custom slot extractor."""
        self._slot_extractor.register_extractor(slot_name, extractor)

    # -------------------------------------------------------------------------
    # HIERARCHY
    # -------------------------------------------------------------------------

    def add_child_intent(self, parent: str, child: str) -> None:
        """Add child intent."""
        self._hierarchy.add_child(parent, child)

    def get_parent_intent(self, intent: str) -> Optional[str]:
        """Get parent intent."""
        return self._hierarchy.get_parent(intent)

    def get_child_intents(self, intent: str) -> List[str]:
        """Get child intents."""
        return self._hierarchy.get_children(intent)

    # -------------------------------------------------------------------------
    # TRACKING
    # -------------------------------------------------------------------------

    def get_active_intents(self) -> List[Intent]:
        """Get active intents."""
        return self._tracker.get_active()

    def get_intent_history(self, n: int = 10) -> List[Intent]:
        """Get intent history."""
        return self._tracker.get_history(n)

    def cancel_intent(self, intent_id: str) -> Optional[Intent]:
        """Cancel intent."""
        return self._tracker.update_status(intent_id, IntentStatus.CANCELLED)

    def on_intent_fulfilled(
        self,
        intent_name: str,
        callback: Callable[[Intent], None]
    ) -> None:
        """Register fulfillment callback."""
        self._tracker.on_fulfillment(intent_name, callback)

    # -------------------------------------------------------------------------
    # CONTEXT
    # -------------------------------------------------------------------------

    def set_context(self, key: str, value: Any) -> None:
        """Set context value."""
        self._context.entities[key] = value

    def get_context(self, key: str) -> Any:
        """Get context value."""
        return self._context.entities.get(key)

    def set_topic(self, topic: str) -> None:
        """Set conversation topic."""
        self._context.topic = topic

    def get_topic(self) -> str:
        """Get conversation topic."""
        return self._context.topic

    def clear_context(self) -> None:
        """Clear context."""
        self._context = ConversationContext()

    # -------------------------------------------------------------------------
    # DISAMBIGUATION
    # -------------------------------------------------------------------------

    def needs_clarification(self, text: str) -> bool:
        """Check if clarification needed."""
        matches = self._pattern_matcher.match(text)
        intent_matches = [
            IntentMatch(intent_name=m[0], confidence=m[1])
            for m in matches
        ]
        return self._disambiguator.needs_clarification(intent_matches)

    def get_clarification_prompt(self, text: str) -> str:
        """Get clarification prompt."""
        matches = self._pattern_matcher.match(text)
        intent_matches = [
            IntentMatch(intent_name=m[0], confidence=m[1])
            for m in matches
        ]
        return self._disambiguator.generate_clarification_prompt(intent_matches)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> IntentStats:
        """Get intent statistics."""
        if self._stats.total_intents > 0:
            self._stats.avg_confidence = (
                self._stats.fulfilled_count / self._stats.total_intents
            )
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Intent Manager."""
    print("=" * 70)
    print("BAEL - INTENT MANAGER DEMO")
    print("Advanced Intent Recognition and Management")
    print("=" * 70)
    print()

    manager = IntentManager()

    # 1. Register Intents
    print("1. REGISTER INTENTS:")
    print("-" * 40)

    manager.register_intent(
        "greet",
        patterns=["hello", "hi", "hey", "good morning"],
        handler=lambda i: f"Hello! How can I help you?"
    )

    manager.register_intent(
        "search",
        patterns=["find", "search", "look for", "search for"],
        slots={"query": SlotType.TEXT},
        handler=lambda i: f"Searching for: {i.slots.get('query', {}).value}"
    )

    manager.register_intent(
        "set_reminder",
        patterns=["remind me", "set reminder", "reminder for"],
        slots={"time": SlotType.TIME, "task": SlotType.TEXT},
        required_slots=["time"],
        handler=lambda i: f"Reminder set for {i.slots.get('time', {}).value}"
    )

    manager.register_intent(
        "calculate",
        patterns=["calculate", "compute", "what is"],
        slots={"number": SlotType.NUMBER},
        handler=lambda i: f"Result: {i.slots.get('number', {}).value}"
    )

    print("   Registered: greet, search, set_reminder, calculate")
    print()

    # 2. Recognize Intent
    print("2. RECOGNIZE INTENT:")
    print("-" * 40)

    text = "Hello, how are you?"
    match = manager.recognize(text)

    print(f"   Input: \"{text}\"")
    print(f"   Intent: {match.intent_name}")
    print(f"   Type: {match.intent_type.value}")
    print(f"   Confidence: {match.confidence:.2f}")
    print()

    # 3. Extract Slots
    print("3. EXTRACT SLOTS:")
    print("-" * 40)

    text = "Remind me at 3:00 pm to call John"
    slots = manager.extract_slots(text, {"time": SlotType.TIME, "task": SlotType.TEXT})

    print(f"   Input: \"{text}\"")
    for name, slot in slots.items():
        print(f"   {name}: {slot.value} (confidence: {slot.confidence:.2f})")
    print()

    # 4. Create and Fulfill Intent
    print("4. CREATE AND FULFILL INTENT:")
    print("-" * 40)

    text = "Hello"
    match = manager.recognize(text)
    intent = manager.create_intent(match)

    print(f"   Created intent: {intent.name} (ID: {intent.intent_id[:8]}...)")

    success, result = await manager.fulfill(intent)

    print(f"   Fulfilled: {success}")
    print(f"   Response: {result}")
    print()

    # 5. Intent Classification
    print("5. INTENT CLASSIFICATION:")
    print("-" * 40)

    test_texts = [
        "What is the weather?",
        "Delete all files",
        "Yes, that's correct",
        "Goodbye!"
    ]

    for t in test_texts:
        match = manager.recognize(t)
        print(f"   \"{t[:25]}...\" -> {match.intent_type.value}")
    print()

    # 6. Multiple Intents
    print("6. MULTIPLE INTENTS:")
    print("-" * 40)

    text = "Search for cats and then remind me at 5pm"
    matches = manager.recognize_multiple(text)

    print(f"   Input: \"{text}\"")
    print(f"   Detected {len(matches)} intents:")
    for m in matches:
        print(f"     - {m.intent_name} ({m.confidence:.2f})")
    print()

    # 7. Intent Hierarchy
    print("7. INTENT HIERARCHY:")
    print("-" * 40)

    manager.add_child_intent("search", "search_web")
    manager.add_child_intent("search", "search_files")
    manager.add_child_intent("search_web", "search_images")

    children = manager.get_child_intents("search")
    parent = manager.get_parent_intent("search_images")

    print(f"   Children of 'search': {children}")
    print(f"   Parent of 'search_images': {parent}")
    print()

    # 8. Context Management
    print("8. CONTEXT MANAGEMENT:")
    print("-" * 40)

    manager.set_topic("shopping")
    manager.set_context("user_location", "New York")
    manager.set_context("user_preference", "electronics")

    print(f"   Topic: {manager.get_topic()}")
    print(f"   Location: {manager.get_context('user_location')}")
    print(f"   Preference: {manager.get_context('user_preference')}")
    print()

    # 9. Active Intents
    print("9. ACTIVE INTENTS:")
    print("-" * 40)

    # Create some intents
    match1 = manager.recognize("search for books")
    intent1 = manager.create_intent(match1)

    match2 = manager.recognize("remind me at 3pm")
    intent2 = manager.create_intent(match2)

    active = manager.get_active_intents()

    print(f"   Active intents: {len(active)}")
    for i in active:
        print(f"     - {i.name} ({i.status.value})")
    print()

    # 10. Intent History
    print("10. INTENT HISTORY:")
    print("-" * 40)

    history = manager.get_intent_history(5)

    print(f"   History ({len(history)} intents):")
    for i in history:
        print(f"     - {i.name}: {i.status.value}")
    print()

    # 11. Missing Slots
    print("11. MISSING SLOTS:")
    print("-" * 40)

    match = manager.recognize("set a reminder")
    intent = manager.create_intent(match)

    can_fulfill = manager.can_fulfill(intent)
    missing = manager.get_missing_slots(intent)

    print(f"   Intent: {intent.name}")
    print(f"   Can fulfill: {can_fulfill}")
    print(f"   Missing slots: {missing}")
    print()

    # 12. Cancel Intent
    print("12. CANCEL INTENT:")
    print("-" * 40)

    match = manager.recognize("search something")
    intent = manager.create_intent(match)

    print(f"   Created: {intent.intent_id[:8]}... (status: {intent.status.value})")

    cancelled = manager.cancel_intent(intent.intent_id)

    print(f"   Cancelled: {cancelled.status.value if cancelled else 'N/A'}")
    print()

    # 13. Number Extraction
    print("13. NUMBER EXTRACTION:")
    print("-" * 40)

    text = "Calculate 42 plus 8"
    slots = manager.extract_slots(text, {"number": SlotType.NUMBER})

    print(f"   Input: \"{text}\"")
    print(f"   Number: {slots.get('number', Slot()).value}")
    print()

    # 14. Clarification
    print("14. CLARIFICATION:")
    print("-" * 40)

    # Register similar intents
    manager.register_intent("find_files", ["find files", "locate files"])
    manager.register_intent("find_text", ["find text", "search text"])

    text = "find"
    needs = manager.needs_clarification(text)
    prompt = manager.get_clarification_prompt(text) if needs else "No clarification needed"

    print(f"   Input: \"{text}\"")
    print(f"   Needs clarification: {needs}")
    print(f"   Prompt: {prompt}")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total intents: {stats.total_intents}")
    print(f"   Fulfilled: {stats.fulfilled_count}")
    print(f"   Failed: {stats.failed_count}")
    print(f"   Intent counts: {dict(list(stats.intent_counts.items())[:3])}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Intent Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
