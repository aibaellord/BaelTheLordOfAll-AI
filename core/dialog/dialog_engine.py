#!/usr/bin/env python3
"""
BAEL - Dialog Engine
Dialog management and conversation handling for agents.

Features:
- Dialog state tracking
- Turn management
- Intent handling
- Response generation
- Conversation flow control
"""

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class DialogState(Enum):
    """States of a dialog."""
    IDLE = "idle"
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class TurnType(Enum):
    """Types of dialog turns."""
    USER = "user"
    SYSTEM = "system"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"


class IntentType(Enum):
    """Types of intents."""
    QUESTION = "question"
    COMMAND = "command"
    STATEMENT = "statement"
    GREETING = "greeting"
    FAREWELL = "farewell"
    CONFIRMATION = "confirmation"
    DENIAL = "denial"
    CLARIFICATION = "clarification"


class ResponseType(Enum):
    """Types of responses."""
    ANSWER = "answer"
    ACTION = "action"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    ERROR = "error"
    GREETING = "greeting"
    FAREWELL = "farewell"


class SlotStatus(Enum):
    """Status of dialog slots."""
    EMPTY = "empty"
    FILLED = "filled"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ConversationPhase(Enum):
    """Phases of conversation."""
    OPENING = "opening"
    INFORMATION_GATHERING = "information_gathering"
    PROCESSING = "processing"
    CONFIRMATION = "confirmation"
    CLOSING = "closing"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Turn:
    """A dialog turn."""
    turn_id: str = ""
    turn_type: TurnType = TurnType.USER
    content: str = ""
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.turn_id:
            self.turn_id = str(uuid.uuid4())[:8]


@dataclass
class Intent:
    """A dialog intent."""
    intent_id: str = ""
    name: str = ""
    intent_type: IntentType = IntentType.STATEMENT
    patterns: List[str] = field(default_factory=list)
    slots: List[str] = field(default_factory=list)
    priority: int = 1

    def __post_init__(self):
        if not self.intent_id:
            self.intent_id = str(uuid.uuid4())[:8]


@dataclass
class Slot:
    """A dialog slot."""
    slot_id: str = ""
    name: str = ""
    value: Optional[Any] = None
    status: SlotStatus = SlotStatus.EMPTY
    required: bool = True
    prompt: str = ""

    def __post_init__(self):
        if not self.slot_id:
            self.slot_id = str(uuid.uuid4())[:8]


@dataclass
class Response:
    """A dialog response."""
    response_id: str = ""
    response_type: ResponseType = ResponseType.ANSWER
    content: str = ""
    actions: List[str] = field(default_factory=list)
    slots_filled: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.response_id:
            self.response_id = str(uuid.uuid4())[:8]


@dataclass
class Conversation:
    """A conversation session."""
    conversation_id: str = ""
    state: DialogState = DialogState.IDLE
    phase: ConversationPhase = ConversationPhase.OPENING
    turns: List[Turn] = field(default_factory=list)
    slots: Dict[str, Slot] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())[:8]


@dataclass
class DialogConfig:
    """Dialog engine configuration."""
    max_turns: int = 100
    turn_timeout: float = 300.0
    confirmation_threshold: float = 0.8
    max_clarifications: int = 3


# =============================================================================
# INTENT RECOGNIZER
# =============================================================================

class IntentRecognizer:
    """Recognize intents from user input."""

    def __init__(self):
        self._intents: Dict[str, Intent] = {}
        self._patterns: Dict[str, str] = {}

    def register(
        self,
        name: str,
        intent_type: IntentType,
        patterns: List[str],
        slots: Optional[List[str]] = None,
        priority: int = 1
    ) -> Intent:
        """Register an intent."""
        intent = Intent(
            name=name,
            intent_type=intent_type,
            patterns=patterns,
            slots=slots or [],
            priority=priority
        )

        self._intents[intent.intent_id] = intent

        for pattern in patterns:
            self._patterns[pattern.lower()] = intent.intent_id

        return intent

    def recognize(self, text: str) -> Tuple[Optional[Intent], float]:
        """Recognize intent from text."""
        text_lower = text.lower()

        for pattern, intent_id in self._patterns.items():
            if pattern in text_lower:
                intent = self._intents.get(intent_id)
                if intent:
                    confidence = len(pattern) / max(len(text_lower), 1)
                    return intent, min(1.0, confidence + 0.3)

        if "?" in text:
            question_intent = self._find_by_type(IntentType.QUESTION)
            if question_intent:
                return question_intent, 0.6

        if any(word in text_lower for word in ["hello", "hi", "hey"]):
            greeting_intent = self._find_by_type(IntentType.GREETING)
            if greeting_intent:
                return greeting_intent, 0.9

        if any(word in text_lower for word in ["bye", "goodbye", "farewell"]):
            farewell_intent = self._find_by_type(IntentType.FAREWELL)
            if farewell_intent:
                return farewell_intent, 0.9

        if any(word in text_lower for word in ["yes", "ok", "sure", "correct"]):
            confirm_intent = self._find_by_type(IntentType.CONFIRMATION)
            if confirm_intent:
                return confirm_intent, 0.8

        if any(word in text_lower for word in ["no", "nope", "wrong", "incorrect"]):
            deny_intent = self._find_by_type(IntentType.DENIAL)
            if deny_intent:
                return deny_intent, 0.8

        return None, 0.0

    def _find_by_type(self, intent_type: IntentType) -> Optional[Intent]:
        """Find intent by type."""
        for intent in self._intents.values():
            if intent.intent_type == intent_type:
                return intent
        return None

    def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get intent by ID."""
        return self._intents.get(intent_id)

    def get_by_name(self, name: str) -> Optional[Intent]:
        """Get intent by name."""
        for intent in self._intents.values():
            if intent.name == name:
                return intent
        return None

    def count(self) -> int:
        """Count intents."""
        return len(self._intents)

    def all(self) -> List[Intent]:
        """Get all intents."""
        return list(self._intents.values())


# =============================================================================
# SLOT FILLER
# =============================================================================

class SlotFiller:
    """Fill slots from user input."""

    def __init__(self):
        self._extractors: Dict[str, Callable[[str], Optional[Any]]] = {}

    def register_extractor(
        self,
        slot_name: str,
        extractor: Callable[[str], Optional[Any]]
    ) -> None:
        """Register a slot extractor."""
        self._extractors[slot_name] = extractor

    def extract(
        self,
        text: str,
        slot_name: str
    ) -> Optional[Any]:
        """Extract slot value from text."""
        extractor = self._extractors.get(slot_name)

        if extractor:
            return extractor(text)

        return self._default_extract(text, slot_name)

    def _default_extract(
        self,
        text: str,
        slot_name: str
    ) -> Optional[Any]:
        """Default extraction logic."""
        words = text.split()

        if len(words) == 1:
            return words[0]

        return None

    def fill_slots(
        self,
        text: str,
        slots: Dict[str, Slot]
    ) -> Dict[str, Any]:
        """Fill multiple slots from text."""
        filled = {}

        for slot_name, slot in slots.items():
            if slot.status == SlotStatus.EMPTY:
                value = self.extract(text, slot_name)
                if value is not None:
                    filled[slot_name] = value
                    slot.value = value
                    slot.status = SlotStatus.FILLED

        return filled

    def get_missing_slots(
        self,
        slots: Dict[str, Slot]
    ) -> List[Slot]:
        """Get unfilled required slots."""
        missing = []

        for slot in slots.values():
            if slot.required and slot.status == SlotStatus.EMPTY:
                missing.append(slot)

        return missing

    def reset_slot(self, slot: Slot) -> None:
        """Reset a slot."""
        slot.value = None
        slot.status = SlotStatus.EMPTY

    def confirm_slot(self, slot: Slot) -> None:
        """Confirm a slot value."""
        if slot.status == SlotStatus.FILLED:
            slot.status = SlotStatus.CONFIRMED


# =============================================================================
# RESPONSE GENERATOR
# =============================================================================

class ResponseGenerator:
    """Generate dialog responses."""

    def __init__(self):
        self._templates: Dict[str, List[str]] = {
            ResponseType.GREETING.value: [
                "Hello! How can I help you today?",
                "Hi there! What can I do for you?",
            ],
            ResponseType.FAREWELL.value: [
                "Goodbye! Have a great day!",
                "Bye! Feel free to return if you need anything.",
            ],
            ResponseType.CONFIRMATION.value: [
                "Just to confirm: {details}. Is that correct?",
                "I understood: {details}. Please confirm.",
            ],
            ResponseType.CLARIFICATION.value: [
                "Could you please clarify {what}?",
                "I need more information about {what}.",
            ],
            ResponseType.ERROR.value: [
                "I'm sorry, I didn't understand that.",
                "Could you please rephrase that?",
            ],
        }

        self._responses: List[Response] = []

    def add_template(
        self,
        response_type: ResponseType,
        template: str
    ) -> None:
        """Add a response template."""
        if response_type.value not in self._templates:
            self._templates[response_type.value] = []

        self._templates[response_type.value].append(template)

    def generate(
        self,
        response_type: ResponseType,
        **kwargs
    ) -> Response:
        """Generate a response."""
        templates = self._templates.get(response_type.value, [])

        if templates:
            template = random.choice(templates)
            try:
                content = template.format(**kwargs)
            except KeyError:
                content = template
        else:
            content = "I understand."

        response = Response(
            response_type=response_type,
            content=content
        )

        self._responses.append(response)

        return response

    def generate_answer(self, answer: str) -> Response:
        """Generate an answer response."""
        response = Response(
            response_type=ResponseType.ANSWER,
            content=answer
        )

        self._responses.append(response)

        return response

    def generate_clarification(
        self,
        slot: Slot
    ) -> Response:
        """Generate a clarification request."""
        if slot.prompt:
            content = slot.prompt
        else:
            content = f"What is the {slot.name}?"

        response = Response(
            response_type=ResponseType.CLARIFICATION,
            content=content
        )

        self._responses.append(response)

        return response

    def generate_confirmation(
        self,
        slots: Dict[str, Slot]
    ) -> Response:
        """Generate a confirmation request."""
        details = ", ".join(
            f"{slot.name}: {slot.value}"
            for slot in slots.values()
            if slot.value is not None
        )

        return self.generate(ResponseType.CONFIRMATION, details=details)

    def get_responses(self, limit: int = 20) -> List[Response]:
        """Get recent responses."""
        return self._responses[-limit:]


# =============================================================================
# DIALOG STATE TRACKER
# =============================================================================

class DialogStateTracker:
    """Track dialog state."""

    def __init__(self, max_turns: int = 100):
        self._conversations: Dict[str, Conversation] = {}
        self._max_turns = max_turns

    def create_conversation(self) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation()
        self._conversations[conversation.conversation_id] = conversation
        return conversation

    def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self._conversations.get(conversation_id)

    def add_turn(
        self,
        conversation_id: str,
        turn: Turn
    ) -> bool:
        """Add a turn to conversation."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return False

        if len(conversation.turns) >= self._max_turns:
            return False

        conversation.turns.append(turn)

        if conversation.state == DialogState.IDLE:
            conversation.state = DialogState.ACTIVE

        return True

    def update_state(
        self,
        conversation_id: str,
        state: DialogState
    ) -> bool:
        """Update conversation state."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return False

        conversation.state = state

        return True

    def update_phase(
        self,
        conversation_id: str,
        phase: ConversationPhase
    ) -> bool:
        """Update conversation phase."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return False

        conversation.phase = phase

        return True

    def set_context(
        self,
        conversation_id: str,
        key: str,
        value: Any
    ) -> bool:
        """Set context value."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return False

        conversation.context[key] = value

        return True

    def get_context(
        self,
        conversation_id: str,
        key: str
    ) -> Optional[Any]:
        """Get context value."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return None

        return conversation.context.get(key)

    def add_slot(
        self,
        conversation_id: str,
        slot: Slot
    ) -> bool:
        """Add a slot to conversation."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return False

        conversation.slots[slot.name] = slot

        return True

    def get_slots(
        self,
        conversation_id: str
    ) -> Dict[str, Slot]:
        """Get conversation slots."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return {}

        return conversation.slots

    def get_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Turn]:
        """Get conversation history."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return []

        return conversation.turns[-limit:]

    def close_conversation(
        self,
        conversation_id: str
    ) -> bool:
        """Close a conversation."""
        conversation = self._conversations.get(conversation_id)

        if not conversation:
            return False

        conversation.state = DialogState.COMPLETED
        conversation.phase = ConversationPhase.CLOSING

        return True

    def count(self) -> int:
        """Count conversations."""
        return len(self._conversations)

    def active_conversations(self) -> List[Conversation]:
        """Get active conversations."""
        return [
            c for c in self._conversations.values()
            if c.state == DialogState.ACTIVE
        ]


# =============================================================================
# DIALOG ENGINE
# =============================================================================

class DialogEngine:
    """
    Dialog Engine for BAEL.

    Dialog management and conversation handling.
    """

    def __init__(self, config: Optional[DialogConfig] = None):
        self._config = config or DialogConfig()

        self._intent_recognizer = IntentRecognizer()
        self._slot_filler = SlotFiller()
        self._response_generator = ResponseGenerator()
        self._state_tracker = DialogStateTracker(self._config.max_turns)

        self._setup_default_intents()

    def _setup_default_intents(self) -> None:
        """Setup default intents."""
        self._intent_recognizer.register(
            "greeting",
            IntentType.GREETING,
            ["hello", "hi", "hey", "good morning", "good afternoon"]
        )

        self._intent_recognizer.register(
            "farewell",
            IntentType.FAREWELL,
            ["bye", "goodbye", "farewell", "see you", "talk later"]
        )

        self._intent_recognizer.register(
            "confirm",
            IntentType.CONFIRMATION,
            ["yes", "correct", "right", "sure", "ok", "okay"]
        )

        self._intent_recognizer.register(
            "deny",
            IntentType.DENIAL,
            ["no", "wrong", "incorrect", "nope", "not right"]
        )

        self._intent_recognizer.register(
            "help",
            IntentType.QUESTION,
            ["help", "how do i", "what can you", "assist"]
        )

    # ----- Conversation Operations -----

    def start_conversation(self) -> Conversation:
        """Start a new conversation."""
        return self._state_tracker.create_conversation()

    def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self._state_tracker.get_conversation(conversation_id)

    def end_conversation(self, conversation_id: str) -> Response:
        """End a conversation."""
        self._state_tracker.close_conversation(conversation_id)
        return self._response_generator.generate(ResponseType.FAREWELL)

    # ----- Intent Operations -----

    def register_intent(
        self,
        name: str,
        intent_type: IntentType,
        patterns: List[str],
        slots: Optional[List[str]] = None
    ) -> Intent:
        """Register an intent."""
        return self._intent_recognizer.register(
            name=name,
            intent_type=intent_type,
            patterns=patterns,
            slots=slots
        )

    def recognize_intent(
        self,
        text: str
    ) -> Tuple[Optional[Intent], float]:
        """Recognize intent from text."""
        return self._intent_recognizer.recognize(text)

    # ----- Slot Operations -----

    def register_slot_extractor(
        self,
        slot_name: str,
        extractor: Callable[[str], Optional[Any]]
    ) -> None:
        """Register a slot extractor."""
        self._slot_filler.register_extractor(slot_name, extractor)

    def add_slot(
        self,
        conversation_id: str,
        name: str,
        required: bool = True,
        prompt: str = ""
    ) -> Slot:
        """Add a slot to conversation."""
        slot = Slot(
            name=name,
            required=required,
            prompt=prompt or f"What is the {name}?"
        )

        self._state_tracker.add_slot(conversation_id, slot)

        return slot

    def fill_slots(
        self,
        conversation_id: str,
        text: str
    ) -> Dict[str, Any]:
        """Fill slots from user input."""
        slots = self._state_tracker.get_slots(conversation_id)
        return self._slot_filler.fill_slots(text, slots)

    def get_missing_slots(
        self,
        conversation_id: str
    ) -> List[Slot]:
        """Get missing required slots."""
        slots = self._state_tracker.get_slots(conversation_id)
        return self._slot_filler.get_missing_slots(slots)

    # ----- Process Input -----

    def process_input(
        self,
        conversation_id: str,
        text: str
    ) -> Response:
        """Process user input and generate response."""
        conversation = self._state_tracker.get_conversation(conversation_id)

        if not conversation:
            conversation = self._state_tracker.create_conversation()
            conversation_id = conversation.conversation_id

        intent, confidence = self._intent_recognizer.recognize(text)

        turn = Turn(
            turn_type=TurnType.USER,
            content=text,
            intent=intent.name if intent else None,
            confidence=confidence
        )

        self._state_tracker.add_turn(conversation_id, turn)

        if intent:
            if intent.intent_type == IntentType.GREETING:
                self._state_tracker.update_phase(
                    conversation_id,
                    ConversationPhase.OPENING
                )
                return self._response_generator.generate(ResponseType.GREETING)

            elif intent.intent_type == IntentType.FAREWELL:
                return self.end_conversation(conversation_id)

            elif intent.intent_type == IntentType.CONFIRMATION:
                self._confirm_pending_slots(conversation_id)
                return self._handle_confirmation(conversation_id)

            elif intent.intent_type == IntentType.DENIAL:
                self._reset_pending_slots(conversation_id)
                return self._handle_denial(conversation_id)

        self.fill_slots(conversation_id, text)

        missing = self.get_missing_slots(conversation_id)

        if missing:
            self._state_tracker.update_phase(
                conversation_id,
                ConversationPhase.INFORMATION_GATHERING
            )
            return self._response_generator.generate_clarification(missing[0])

        slots = self._state_tracker.get_slots(conversation_id)
        filled_slots = {k: s for k, s in slots.items() if s.value is not None}

        if filled_slots:
            unconfirmed = [s for s in filled_slots.values() if s.status != SlotStatus.CONFIRMED]

            if unconfirmed:
                self._state_tracker.update_phase(
                    conversation_id,
                    ConversationPhase.CONFIRMATION
                )
                return self._response_generator.generate_confirmation(filled_slots)

        return self._generate_response(conversation_id, intent)

    def _confirm_pending_slots(self, conversation_id: str) -> None:
        """Confirm pending slots."""
        slots = self._state_tracker.get_slots(conversation_id)

        for slot in slots.values():
            if slot.status == SlotStatus.FILLED:
                self._slot_filler.confirm_slot(slot)

    def _reset_pending_slots(self, conversation_id: str) -> None:
        """Reset pending slots."""
        slots = self._state_tracker.get_slots(conversation_id)

        for slot in slots.values():
            if slot.status == SlotStatus.FILLED:
                self._slot_filler.reset_slot(slot)

    def _handle_confirmation(self, conversation_id: str) -> Response:
        """Handle confirmation."""
        self._state_tracker.update_phase(
            conversation_id,
            ConversationPhase.PROCESSING
        )

        return self._response_generator.generate_answer(
            "Great! I'll process your request now."
        )

    def _handle_denial(self, conversation_id: str) -> Response:
        """Handle denial."""
        self._state_tracker.update_phase(
            conversation_id,
            ConversationPhase.INFORMATION_GATHERING
        )

        return self._response_generator.generate_answer(
            "I understand. Let's try again. What would you like to change?"
        )

    def _generate_response(
        self,
        conversation_id: str,
        intent: Optional[Intent]
    ) -> Response:
        """Generate appropriate response."""
        if intent and intent.intent_type == IntentType.QUESTION:
            return self._response_generator.generate_answer(
                "I'll help you with that. What specific information do you need?"
            )

        return self._response_generator.generate(ResponseType.ERROR)

    # ----- Response Operations -----

    def add_response_template(
        self,
        response_type: ResponseType,
        template: str
    ) -> None:
        """Add a response template."""
        self._response_generator.add_template(response_type, template)

    # ----- Context Operations -----

    def set_context(
        self,
        conversation_id: str,
        key: str,
        value: Any
    ) -> bool:
        """Set context value."""
        return self._state_tracker.set_context(conversation_id, key, value)

    def get_context(
        self,
        conversation_id: str,
        key: str
    ) -> Optional[Any]:
        """Get context value."""
        return self._state_tracker.get_context(conversation_id, key)

    # ----- History Operations -----

    def get_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Turn]:
        """Get conversation history."""
        return self._state_tracker.get_history(conversation_id, limit)

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "conversations": self._state_tracker.count(),
            "active_conversations": len(self._state_tracker.active_conversations()),
            "intents": self._intent_recognizer.count(),
            "responses_generated": len(self._response_generator._responses)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Dialog Engine."""
    print("=" * 70)
    print("BAEL - DIALOG ENGINE DEMO")
    print("Dialog Management and Conversation Handling")
    print("=" * 70)
    print()

    engine = DialogEngine()

    # 1. Start Conversation
    print("1. START CONVERSATION:")
    print("-" * 40)

    conv = engine.start_conversation()

    print(f"   Conversation ID: {conv.conversation_id}")
    print(f"   State: {conv.state.value}")
    print(f"   Phase: {conv.phase.value}")
    print()

    # 2. Register Custom Intent
    print("2. REGISTER CUSTOM INTENT:")
    print("-" * 40)

    book_intent = engine.register_intent(
        "book_appointment",
        IntentType.COMMAND,
        ["book", "schedule", "appointment", "meeting"],
        slots=["date", "time", "service"]
    )

    print(f"   Registered: {book_intent.name}")
    print(f"   Patterns: {book_intent.patterns}")
    print(f"   Slots: {book_intent.slots}")
    print()

    # 3. Add Slots
    print("3. ADD SLOTS:")
    print("-" * 40)

    date_slot = engine.add_slot(
        conv.conversation_id,
        "date",
        required=True,
        prompt="What date would you like to book?"
    )

    time_slot = engine.add_slot(
        conv.conversation_id,
        "time",
        required=True,
        prompt="What time works best for you?"
    )

    service_slot = engine.add_slot(
        conv.conversation_id,
        "service",
        required=True,
        prompt="What service do you need?"
    )

    print(f"   Added slot: {date_slot.name}")
    print(f"   Added slot: {time_slot.name}")
    print(f"   Added slot: {service_slot.name}")
    print()

    # 4. Process Greeting
    print("4. PROCESS GREETING:")
    print("-" * 40)

    response = engine.process_input(conv.conversation_id, "Hello!")

    print(f"   User: Hello!")
    print(f"   System: {response.content}")
    print()

    # 5. Process Intent
    print("5. PROCESS INTENT:")
    print("-" * 40)

    response = engine.process_input(
        conv.conversation_id,
        "I'd like to book an appointment"
    )

    print(f"   User: I'd like to book an appointment")
    print(f"   System: {response.content}")
    print()

    # 6. Recognize Intent
    print("6. RECOGNIZE INTENT:")
    print("-" * 40)

    intent, confidence = engine.recognize_intent("Can you help me schedule a meeting?")

    print(f"   Input: 'Can you help me schedule a meeting?'")
    if intent:
        print(f"   Intent: {intent.name}")
        print(f"   Confidence: {confidence:.2f}")
    print()

    # 7. Register Slot Extractor
    print("7. REGISTER SLOT EXTRACTOR:")
    print("-" * 40)

    def extract_date(text: str) -> Optional[str]:
        if "tomorrow" in text.lower():
            return "tomorrow"
        if "today" in text.lower():
            return "today"
        return None

    engine.register_slot_extractor("date", extract_date)

    print("   Registered date extractor")
    print()

    # 8. Fill Slots
    print("8. FILL SLOTS:")
    print("-" * 40)

    response = engine.process_input(
        conv.conversation_id,
        "I need it for tomorrow"
    )

    print(f"   User: I need it for tomorrow")
    print(f"   System: {response.content}")

    slots = engine.get_conversation(conv.conversation_id).slots
    print(f"   Date slot: {slots['date'].value}")
    print()

    # 9. Get Missing Slots
    print("9. GET MISSING SLOTS:")
    print("-" * 40)

    missing = engine.get_missing_slots(conv.conversation_id)

    print(f"   Missing slots: {[s.name for s in missing]}")
    print()

    # 10. Set Context
    print("10. SET CONTEXT:")
    print("-" * 40)

    engine.set_context(conv.conversation_id, "user_name", "Alice")
    engine.set_context(conv.conversation_id, "user_id", "12345")

    name = engine.get_context(conv.conversation_id, "user_name")

    print(f"   Set user_name: Alice")
    print(f"   Retrieved: {name}")
    print()

    # 11. Simulate Full Conversation
    print("11. SIMULATE CONVERSATION:")
    print("-" * 40)

    conv2 = engine.start_conversation()

    inputs = [
        "Hi there!",
        "I want to book an appointment",
        "tomorrow",
        "3pm",
        "haircut",
        "yes",
        "Thank you, goodbye!"
    ]

    engine.add_slot(conv2.conversation_id, "date", True, "What date?")
    engine.add_slot(conv2.conversation_id, "time", True, "What time?")
    engine.add_slot(conv2.conversation_id, "service", True, "What service?")

    for user_input in inputs:
        response = engine.process_input(conv2.conversation_id, user_input)
        print(f"   User: {user_input}")
        print(f"   System: {response.content}")
        print()

    # 12. Get History
    print("12. GET HISTORY:")
    print("-" * 40)

    history = engine.get_history(conv.conversation_id, limit=5)

    print(f"   Last {len(history)} turns:")
    for turn in history:
        print(f"     - [{turn.turn_type.value}] {turn.content[:30]}...")
    print()

    # 13. Check Conversation State
    print("13. CONVERSATION STATE:")
    print("-" * 40)

    conv_state = engine.get_conversation(conv2.conversation_id)
    if conv_state:
        print(f"   State: {conv_state.state.value}")
        print(f"   Phase: {conv_state.phase.value}")
        print(f"   Turns: {len(conv_state.turns)}")
    print()

    # 14. Add Custom Response Template
    print("14. ADD RESPONSE TEMPLATE:")
    print("-" * 40)

    engine.add_response_template(
        ResponseType.GREETING,
        "Welcome! I'm your AI assistant. How may I help you?"
    )

    print("   Added custom greeting template")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Dialog Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
