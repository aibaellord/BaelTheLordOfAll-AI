#!/usr/bin/env python3
"""
BAEL - Communication Intelligence System
Advanced natural language understanding and generation.

Features:
- Intent recognition
- Entity extraction
- Dialogue management
- Response generation
- Sentiment analysis
- Context tracking
- Multi-turn conversations
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class IntentType(Enum):
    """Types of user intents."""
    QUESTION = "question"
    COMMAND = "command"
    STATEMENT = "statement"
    GREETING = "greeting"
    FAREWELL = "farewell"
    CONFIRMATION = "confirmation"
    DENIAL = "denial"
    CLARIFICATION = "clarification"
    FEEDBACK = "feedback"
    UNKNOWN = "unknown"


class EntityCategory(Enum):
    """Categories of entities."""
    PERSON = "person"
    LOCATION = "location"
    ORGANIZATION = "organization"
    DATE = "date"
    TIME = "time"
    NUMBER = "number"
    MONEY = "money"
    PERCENTAGE = "percentage"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    CUSTOM = "custom"


class Sentiment(Enum):
    """Sentiment values."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class DialogueState(Enum):
    """Dialogue states."""
    INITIAL = "initial"
    IN_PROGRESS = "in_progress"
    WAITING_CONFIRMATION = "waiting_confirmation"
    WAITING_INFO = "waiting_info"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Entity:
    """An extracted entity."""
    text: str
    category: EntityCategory
    value: Any
    start: int
    end: int
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """A recognized intent."""
    intent_type: IntentType
    action: str
    confidence: float
    entities: List[Entity] = field(default_factory=list)
    slots: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogueTurn:
    """A single turn in dialogue."""
    id: str
    role: str  # user, assistant, system
    content: str
    intent: Optional[Intent] = None
    entities: List[Entity] = field(default_factory=list)
    sentiment: Optional[Sentiment] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A conversation session."""
    id: str
    turns: List[DialogueTurn] = field(default_factory=list)
    state: DialogueState = DialogueState.INITIAL
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# INTENT RECOGNITION
# =============================================================================

class IntentRecognizer:
    """Recognize intents from text."""

    def __init__(self):
        self.intent_patterns: Dict[str, List[Tuple[str, float]]] = {}
        self.action_handlers: Dict[str, Callable] = {}

        # Default patterns
        self._init_default_patterns()

    def _init_default_patterns(self) -> None:
        """Initialize default intent patterns."""
        self.intent_patterns = {
            "question": [
                (r"^(what|who|where|when|why|how|which|whose|whom)\b", 0.9),
                (r"\?$", 0.7),
                (r"^(can|could|would|will|do|does|did|is|are|was|were)\b.*\?", 0.8),
                (r"^(tell me|explain|describe)\b", 0.6),
            ],
            "command": [
                (r"^(please\s+)?(do|make|create|delete|update|show|list|find|get|set)\b", 0.8),
                (r"^(run|execute|start|stop|restart)\b", 0.9),
                (r"^(open|close|save|load)\b", 0.7),
            ],
            "greeting": [
                (r"^(hi|hello|hey|good morning|good afternoon|good evening)\b", 0.9),
                (r"^(greetings|howdy|yo)\b", 0.7),
            ],
            "farewell": [
                (r"^(bye|goodbye|see you|farewell|take care)\b", 0.9),
                (r"^(later|peace out|ciao)\b", 0.7),
            ],
            "confirmation": [
                (r"^(yes|yeah|yep|sure|ok|okay|correct|right|affirmative)\b", 0.9),
                (r"^(absolutely|definitely|of course)\b", 0.8),
            ],
            "denial": [
                (r"^(no|nope|nah|negative|wrong|incorrect)\b", 0.9),
                (r"^(not at all|never)\b", 0.8),
            ],
            "clarification": [
                (r"^(what do you mean|could you clarify|I don't understand)\b", 0.8),
                (r"^(pardon|sorry|come again)\b", 0.6),
            ],
            "feedback": [
                (r"^(thanks|thank you|great|awesome|good job)\b", 0.8),
                (r"^(that's wrong|incorrect|not what I meant)\b", 0.7),
            ],
        }

    def register_intent(
        self,
        intent_name: str,
        patterns: List[Tuple[str, float]]
    ) -> None:
        """Register custom intent patterns."""
        self.intent_patterns[intent_name] = patterns

    def register_action(
        self,
        action_name: str,
        handler: Callable
    ) -> None:
        """Register action handler."""
        self.action_handlers[action_name] = handler

    async def recognize(
        self,
        text: str,
        context: Dict[str, Any] = None
    ) -> Intent:
        """Recognize intent from text."""
        text_lower = text.lower().strip()

        best_intent = None
        best_confidence = 0.0
        best_action = ""

        for intent_name, patterns in self.intent_patterns.items():
            for pattern, confidence in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent_name
                        best_action = self._extract_action(text_lower, intent_name)

        if best_intent is None:
            return Intent(
                intent_type=IntentType.UNKNOWN,
                action="",
                confidence=0.0
            )

        intent_type = IntentType(best_intent) if best_intent in [e.value for e in IntentType] else IntentType.UNKNOWN

        return Intent(
            intent_type=intent_type,
            action=best_action,
            confidence=best_confidence
        )

    def _extract_action(self, text: str, intent_name: str) -> str:
        """Extract action from text."""
        # Simple extraction - get the main verb
        words = text.split()

        action_verbs = ["do", "make", "create", "delete", "update", "show",
                       "list", "find", "get", "set", "run", "execute",
                       "start", "stop", "open", "close", "save", "load"]

        for word in words:
            if word in action_verbs:
                return word

        return intent_name


# =============================================================================
# ENTITY EXTRACTION
# =============================================================================

class EntityExtractor:
    """Extract entities from text."""

    def __init__(self):
        self.patterns: Dict[EntityCategory, List[Tuple[str, Callable]]] = {}
        self.custom_extractors: Dict[str, Callable] = {}

        self._init_default_patterns()

    def _init_default_patterns(self) -> None:
        """Initialize default entity patterns."""
        self.patterns = {
            EntityCategory.EMAIL: [
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', lambda m: m.group())
            ],
            EntityCategory.PHONE: [
                (r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', lambda m: m.group())
            ],
            EntityCategory.URL: [
                (r'https?://[^\s]+', lambda m: m.group())
            ],
            EntityCategory.NUMBER: [
                (r'\b\d+(?:\.\d+)?\b', lambda m: float(m.group()) if '.' in m.group() else int(m.group()))
            ],
            EntityCategory.DATE: [
                (r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', lambda m: m.group()),
                (r'\b\d{4}-\d{2}-\d{2}\b', lambda m: m.group()),
                (r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?\b', lambda m: m.group())
            ],
            EntityCategory.TIME: [
                (r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm)?\b', lambda m: m.group())
            ],
            EntityCategory.MONEY: [
                (r'\$\d+(?:,\d{3})*(?:\.\d{2})?', lambda m: m.group()),
                (r'\b\d+(?:\.\d{2})?\s*(?:dollars?|usd|eur|euros?|gbp|pounds?)\b', lambda m: m.group())
            ],
            EntityCategory.PERCENTAGE: [
                (r'\b\d+(?:\.\d+)?%', lambda m: float(m.group().rstrip('%')))
            ],
        }

    def register_pattern(
        self,
        category: EntityCategory,
        pattern: str,
        value_extractor: Callable = None
    ) -> None:
        """Register custom pattern."""
        if category not in self.patterns:
            self.patterns[category] = []
        self.patterns[category].append((pattern, value_extractor or (lambda m: m.group())))

    def register_extractor(
        self,
        name: str,
        extractor: Callable
    ) -> None:
        """Register custom extractor function."""
        self.custom_extractors[name] = extractor

    async def extract(
        self,
        text: str,
        context: Dict[str, Any] = None
    ) -> List[Entity]:
        """Extract entities from text."""
        entities = []

        for category, patterns in self.patterns.items():
            for pattern, value_extractor in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    try:
                        value = value_extractor(match)
                        entities.append(Entity(
                            text=match.group(),
                            category=category,
                            value=value,
                            start=match.start(),
                            end=match.end()
                        ))
                    except Exception as e:
                        logger.warning(f"Entity extraction failed: {e}")

        # Run custom extractors
        for name, extractor in self.custom_extractors.items():
            try:
                custom_entities = await extractor(text, context)
                entities.extend(custom_entities)
            except Exception as e:
                logger.warning(f"Custom extractor {name} failed: {e}")

        return entities


# =============================================================================
# SENTIMENT ANALYSIS
# =============================================================================

class SentimentAnalyzer:
    """Analyze sentiment of text."""

    def __init__(self):
        self.positive_words = set([
            "good", "great", "excellent", "amazing", "wonderful", "fantastic",
            "love", "like", "happy", "pleased", "satisfied", "awesome",
            "perfect", "best", "beautiful", "nice", "helpful", "thank"
        ])

        self.negative_words = set([
            "bad", "terrible", "awful", "horrible", "hate", "dislike",
            "angry", "frustrated", "disappointed", "wrong", "worst",
            "ugly", "useless", "annoying", "stupid", "fail", "error"
        ])

        self.intensifiers = set([
            "very", "really", "extremely", "so", "too", "quite", "absolutely"
        ])

        self.negations = set([
            "not", "no", "never", "neither", "nobody", "nothing", "nowhere"
        ])

    async def analyze(
        self,
        text: str,
        context: Dict[str, Any] = None
    ) -> Tuple[Sentiment, float]:
        """Analyze sentiment of text."""
        words = text.lower().split()

        positive_score = 0
        negative_score = 0
        intensity = 1.0
        negated = False

        for i, word in enumerate(words):
            # Check for negation
            if word in self.negations:
                negated = True
                continue

            # Check for intensifier
            if word in self.intensifiers:
                intensity = 1.5
                continue

            # Score words
            if word in self.positive_words:
                if negated:
                    negative_score += intensity
                else:
                    positive_score += intensity
                negated = False
                intensity = 1.0
            elif word in self.negative_words:
                if negated:
                    positive_score += intensity
                else:
                    negative_score += intensity
                negated = False
                intensity = 1.0

        # Calculate overall sentiment
        total = positive_score + negative_score
        if total == 0:
            return (Sentiment.NEUTRAL, 0.5)

        score = positive_score / total

        if score > 0.8:
            return (Sentiment.VERY_POSITIVE, score)
        elif score > 0.6:
            return (Sentiment.POSITIVE, score)
        elif score > 0.4:
            return (Sentiment.NEUTRAL, score)
        elif score > 0.2:
            return (Sentiment.NEGATIVE, score)
        else:
            return (Sentiment.VERY_NEGATIVE, score)


# =============================================================================
# DIALOGUE MANAGEMENT
# =============================================================================

class DialogueManager:
    """Manage dialogue state and flow."""

    def __init__(self):
        self.conversations: Dict[str, Conversation] = {}
        self.intent_recognizer = IntentRecognizer()
        self.entity_extractor = EntityExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()

        # Dialogue policies
        self.policies: Dict[str, Callable] = {}

    def create_conversation(self) -> Conversation:
        """Create new conversation."""
        conv = Conversation(id=str(uuid4()))
        self.conversations[conv.id] = conv
        return conv

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self.conversations.get(conv_id)

    async def process_turn(
        self,
        conv_id: str,
        user_input: str
    ) -> DialogueTurn:
        """Process a user turn."""
        conv = self.get_conversation(conv_id)
        if not conv:
            conv = self.create_conversation()

        # Analyze input
        intent = await self.intent_recognizer.recognize(user_input, conv.context)
        entities = await self.entity_extractor.extract(user_input, conv.context)
        sentiment, sentiment_score = await self.sentiment_analyzer.analyze(user_input, conv.context)

        # Update intent with entities
        intent.entities = entities

        # Create turn
        turn = DialogueTurn(
            id=str(uuid4()),
            role="user",
            content=user_input,
            intent=intent,
            entities=entities,
            sentiment=sentiment
        )

        # Add to conversation
        conv.turns.append(turn)
        conv.updated_at = datetime.now()
        conv.state = DialogueState.IN_PROGRESS

        # Update context with entities
        for entity in entities:
            conv.context[entity.category.value] = entity.value

        return turn

    def register_policy(
        self,
        intent_type: IntentType,
        policy: Callable
    ) -> None:
        """Register dialogue policy for intent type."""
        self.policies[intent_type.value] = policy

    async def generate_response(
        self,
        conv_id: str
    ) -> DialogueTurn:
        """Generate response for current dialogue state."""
        conv = self.get_conversation(conv_id)
        if not conv or not conv.turns:
            return self._create_error_turn("No conversation found")

        last_turn = conv.turns[-1]

        # Apply policy if available
        if last_turn.intent:
            policy = self.policies.get(last_turn.intent.intent_type.value)
            if policy:
                response_text = await policy(conv, last_turn)
            else:
                response_text = self._default_response(last_turn)
        else:
            response_text = self._default_response(last_turn)

        # Create response turn
        response_turn = DialogueTurn(
            id=str(uuid4()),
            role="assistant",
            content=response_text
        )

        conv.turns.append(response_turn)
        conv.updated_at = datetime.now()

        return response_turn

    def _default_response(self, turn: DialogueTurn) -> str:
        """Generate default response."""
        if turn.intent:
            if turn.intent.intent_type == IntentType.GREETING:
                return "Hello! How can I help you today?"
            elif turn.intent.intent_type == IntentType.FAREWELL:
                return "Goodbye! Have a great day!"
            elif turn.intent.intent_type == IntentType.QUESTION:
                return "That's a good question. Let me think about that..."
            elif turn.intent.intent_type == IntentType.COMMAND:
                return f"I'll try to {turn.intent.action} that for you."
            elif turn.intent.intent_type == IntentType.CONFIRMATION:
                return "Great, proceeding with the action."
            elif turn.intent.intent_type == IntentType.DENIAL:
                return "Okay, I won't proceed with that."
            elif turn.intent.intent_type == IntentType.FEEDBACK:
                return "Thank you for your feedback!"

        return "I understand. How can I assist you further?"

    def _create_error_turn(self, message: str) -> DialogueTurn:
        """Create error response turn."""
        return DialogueTurn(
            id=str(uuid4()),
            role="system",
            content=f"Error: {message}"
        )

    def get_context(self, conv_id: str) -> Dict[str, Any]:
        """Get conversation context."""
        conv = self.get_conversation(conv_id)
        return conv.context if conv else {}

    def set_context(
        self,
        conv_id: str,
        key: str,
        value: Any
    ) -> None:
        """Set context value."""
        conv = self.get_conversation(conv_id)
        if conv:
            conv.context[key] = value


# =============================================================================
# RESPONSE GENERATION
# =============================================================================

class ResponseGenerator:
    """Generate natural language responses."""

    def __init__(self):
        self.templates: Dict[str, List[str]] = {}
        self.slot_fillers: Dict[str, Callable] = {}

        self._init_default_templates()

    def _init_default_templates(self) -> None:
        """Initialize default response templates."""
        self.templates = {
            "greeting": [
                "Hello! How can I help you today?",
                "Hi there! What can I do for you?",
                "Hey! Ready to assist you.",
            ],
            "farewell": [
                "Goodbye! Have a great day!",
                "See you later! Take care!",
                "Bye! Feel free to come back anytime.",
            ],
            "acknowledgment": [
                "I understand.",
                "Got it.",
                "Alright, I see.",
            ],
            "clarification": [
                "Could you please clarify what you mean?",
                "I'm not sure I understand. Could you explain more?",
                "Can you provide more details?",
            ],
            "error": [
                "I'm sorry, I encountered an error.",
                "Something went wrong. Please try again.",
                "I apologize, but I couldn't process that.",
            ],
            "not_found": [
                "I couldn't find what you're looking for.",
                "Sorry, no results found.",
                "That doesn't seem to exist.",
            ],
            "success": [
                "Done! {action} completed successfully.",
                "Success! I've {action} as requested.",
                "All set! {action} is done.",
            ],
        }

    def register_template(
        self,
        category: str,
        templates: List[str]
    ) -> None:
        """Register response templates."""
        self.templates[category] = templates

    def register_slot_filler(
        self,
        slot_name: str,
        filler: Callable
    ) -> None:
        """Register slot filler function."""
        self.slot_fillers[slot_name] = filler

    async def generate(
        self,
        category: str,
        slots: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Generate response from template."""
        templates = self.templates.get(category, ["I'm not sure how to respond."])

        import random
        template = random.choice(templates)

        # Fill slots
        if slots:
            for slot_name, value in slots.items():
                if slot_name in self.slot_fillers:
                    value = await self.slot_fillers[slot_name](value, context)
                template = template.replace(f"{{{slot_name}}}", str(value))

        return template


# =============================================================================
# COMMUNICATION SYSTEM
# =============================================================================

class CommunicationSystem:
    """Main communication intelligence system."""

    def __init__(self):
        self.dialogue_manager = DialogueManager()
        self.response_generator = ResponseGenerator()

    def create_session(self) -> str:
        """Create new conversation session."""
        conv = self.dialogue_manager.create_conversation()
        return conv.id

    async def process(
        self,
        session_id: str,
        user_input: str
    ) -> Dict[str, Any]:
        """Process user input and generate response."""
        # Process user turn
        user_turn = await self.dialogue_manager.process_turn(session_id, user_input)

        # Generate response
        response_turn = await self.dialogue_manager.generate_response(session_id)

        return {
            "session_id": session_id,
            "user_input": user_input,
            "intent": user_turn.intent.intent_type.value if user_turn.intent else None,
            "action": user_turn.intent.action if user_turn.intent else None,
            "entities": [
                {
                    "text": e.text,
                    "category": e.category.value,
                    "value": e.value
                }
                for e in user_turn.entities
            ],
            "sentiment": user_turn.sentiment.value if user_turn.sentiment else None,
            "response": response_turn.content
        }

    def register_policy(
        self,
        intent_type: IntentType,
        policy: Callable
    ) -> None:
        """Register dialogue policy."""
        self.dialogue_manager.register_policy(intent_type, policy)

    def register_intent(
        self,
        intent_name: str,
        patterns: List[Tuple[str, float]]
    ) -> None:
        """Register custom intent."""
        self.dialogue_manager.intent_recognizer.register_intent(intent_name, patterns)

    def get_conversation_history(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get conversation history."""
        conv = self.dialogue_manager.get_conversation(session_id)
        if not conv:
            return []

        return [
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat()
            }
            for turn in conv.turns
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "active_sessions": len(self.dialogue_manager.conversations),
            "registered_policies": len(self.dialogue_manager.policies),
            "response_categories": len(self.response_generator.templates)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo communication intelligence system."""
    print("=== Communication Intelligence System Demo ===\n")

    # Create system
    comm = CommunicationSystem()

    # Create session
    session_id = comm.create_session()
    print(f"1. Created session: {session_id[:8]}...\n")

    # Test conversations
    test_inputs = [
        "Hello!",
        "What is the weather today?",
        "Please create a new document",
        "My email is test@example.com and I need help",
        "The meeting is at 2:30 PM tomorrow",
        "That's great, thank you!",
        "No, that's not what I meant",
        "Goodbye!"
    ]

    print("2. Processing Conversations:")
    print("-" * 50)

    for user_input in test_inputs:
        result = await comm.process(session_id, user_input)

        print(f"User: {result['user_input']}")
        print(f"Intent: {result['intent']} (action: {result['action']})")

        if result['entities']:
            print(f"Entities: {result['entities']}")

        if result['sentiment']:
            print(f"Sentiment: {result['sentiment']}")

        print(f"Response: {result['response']}")
        print("-" * 50)

    # Custom policy
    print("\n3. Custom Policy Registration:")

    async def weather_policy(conv, turn):
        return "The weather today is sunny with a high of 72°F."

    comm.register_policy(IntentType.QUESTION, weather_policy)
    print("   Registered custom policy for QUESTION intent")

    result = await comm.process(session_id, "What's the weather?")
    print(f"   User: {result['user_input']}")
    print(f"   Response: {result['response']}")

    # Custom intent
    print("\n4. Custom Intent Registration:")

    comm.register_intent("schedule", [
        (r"\b(schedule|book|reserve|appointment)\b", 0.8),
        (r"\b(meeting|call|event)\b.*\b(at|on|for)\b", 0.7)
    ])
    print("   Registered custom 'schedule' intent")

    # Entity extraction test
    print("\n5. Entity Extraction:")

    test_texts = [
        "Contact me at user@company.com",
        "The price is $99.99 with 15% discount",
        "Call me at 555-123-4567 tomorrow at 3:00 PM",
        "Visit https://example.com for more info"
    ]

    extractor = comm.dialogue_manager.entity_extractor

    for text in test_texts:
        entities = await extractor.extract(text)
        print(f"   '{text}'")
        for e in entities:
            print(f"      -> {e.category.value}: {e.value}")

    # Sentiment analysis
    print("\n6. Sentiment Analysis:")

    sentiment_texts = [
        "This is absolutely amazing!",
        "I really love this product",
        "It's okay, nothing special",
        "I'm disappointed with the service",
        "This is terrible, I hate it"
    ]

    analyzer = comm.dialogue_manager.sentiment_analyzer

    for text in sentiment_texts:
        sentiment, score = await analyzer.analyze(text)
        print(f"   '{text}'")
        print(f"      -> {sentiment.value} ({score:.2f})")

    # Conversation history
    print("\n7. Conversation History:")

    history = comm.get_conversation_history(session_id)
    print(f"   Total turns: {len(history)}")
    for turn in history[:3]:
        print(f"   [{turn['role']}] {turn['content'][:50]}...")

    # Status
    print("\n8. System Status:")
    status = comm.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
