#!/usr/bin/env python3
"""
BAEL - Dialogue Manager
Advanced dialogue and conversation management.

Features:
- Turn management
- Dialogue state tracking
- Conversation flow control
- Multi-turn context
- Dialogue acts
- Response generation
- Conversation repair
- Topic management
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

class DialogueAct(Enum):
    """Dialogue act types."""
    GREETING = "greeting"
    FAREWELL = "farewell"
    QUESTION = "question"
    ANSWER = "answer"
    STATEMENT = "statement"
    REQUEST = "request"
    CONFIRMATION = "confirmation"
    DENIAL = "denial"
    CLARIFICATION = "clarification"
    ACKNOWLEDGEMENT = "acknowledgement"
    APOLOGY = "apology"
    THANKS = "thanks"
    UNKNOWN = "unknown"


class TurnType(Enum):
    """Turn types."""
    USER = "user"
    SYSTEM = "system"


class DialogueStatus(Enum):
    """Dialogue status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TopicStatus(Enum):
    """Topic status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class FlowType(Enum):
    """Conversation flow type."""
    LINEAR = "linear"
    BRANCHING = "branching"
    SLOT_FILLING = "slot_filling"
    FREE_FORM = "free_form"


class RepairType(Enum):
    """Conversation repair type."""
    CLARIFICATION = "clarification"
    CORRECTION = "correction"
    RESTART = "restart"
    IGNORE = "ignore"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Turn:
    """Dialogue turn."""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turn_type: TurnType = TurnType.USER
    content: str = ""
    dialogue_act: DialogueAct = DialogueAct.STATEMENT
    intent: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    sentiment: float = 0.0  # -1 to 1
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Topic:
    """Conversation topic."""
    topic_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: TopicStatus = TopicStatus.ACTIVE
    depth: int = 0  # How many subtopics deep
    parent_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    turns: List[str] = field(default_factory=list)


@dataclass
class DialogueState:
    """Dialogue state."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: DialogueStatus = DialogueStatus.ACTIVE
    current_topic: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)  # Turn IDs
    turn_count: int = 0
    last_intent: str = ""
    last_act: DialogueAct = DialogueAct.UNKNOWN


@dataclass
class FlowNode:
    """Flow node in conversation."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    prompt: str = ""
    expected_intents: List[str] = field(default_factory=list)
    transitions: Dict[str, str] = field(default_factory=dict)  # intent -> next node
    slot_to_fill: Optional[str] = None
    is_terminal: bool = False


@dataclass
class DialoguePolicy:
    """Dialogue policy."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    rules: Dict[str, str] = field(default_factory=dict)  # condition -> action
    priority: int = 0


@dataclass
class DialogueStats:
    """Dialogue statistics."""
    total_turns: int = 0
    user_turns: int = 0
    system_turns: int = 0
    avg_turn_length: float = 0.0
    topics_discussed: int = 0
    repairs_made: int = 0


# =============================================================================
# DIALOGUE ACT CLASSIFIER
# =============================================================================

class DialogueActClassifier:
    """Classify dialogue acts."""

    ACT_PATTERNS = {
        DialogueAct.GREETING: ['hello', 'hi', 'hey', 'good morning', 'greetings'],
        DialogueAct.FAREWELL: ['bye', 'goodbye', 'see you', 'farewell', 'later'],
        DialogueAct.QUESTION: ['?', 'what', 'who', 'when', 'where', 'why', 'how', 'which'],
        DialogueAct.REQUEST: ['please', 'can you', 'could you', 'would you', 'i need', 'i want'],
        DialogueAct.CONFIRMATION: ['yes', 'yeah', 'sure', 'ok', 'correct', 'right', 'exactly'],
        DialogueAct.DENIAL: ['no', 'nope', 'wrong', 'incorrect', 'not'],
        DialogueAct.CLARIFICATION: ['what do you mean', 'can you explain', 'i don\'t understand'],
        DialogueAct.ACKNOWLEDGEMENT: ['i see', 'ok', 'got it', 'understood', 'alright'],
        DialogueAct.APOLOGY: ['sorry', 'apologies', 'my bad', 'excuse me'],
        DialogueAct.THANKS: ['thank', 'thanks', 'appreciate', 'grateful'],
    }

    def classify(self, text: str) -> Tuple[DialogueAct, float]:
        """Classify dialogue act."""
        text_lower = text.lower()
        scores = {}

        for act, patterns in self.ACT_PATTERNS.items():
            score = sum(1 for p in patterns if p in text_lower)
            if score > 0:
                scores[act] = score / len(patterns)

        if scores:
            best = max(scores.items(), key=lambda x: x[1])
            return best[0], min(best[1] * 2, 1.0)

        # Default to statement or answer
        if '?' in text:
            return DialogueAct.QUESTION, 0.7

        return DialogueAct.STATEMENT, 0.5


# =============================================================================
# TURN MANAGER
# =============================================================================

class TurnManager:
    """Manage dialogue turns."""

    def __init__(self, max_history: int = 100):
        self._turns: Dict[str, Turn] = {}
        self._history: deque = deque(maxlen=max_history)
        self._act_classifier = DialogueActClassifier()

    def create_turn(
        self,
        content: str,
        turn_type: TurnType = TurnType.USER,
        intent: str = "",
        entities: Optional[Dict[str, Any]] = None
    ) -> Turn:
        """Create a new turn."""
        act, confidence = self._act_classifier.classify(content)

        turn = Turn(
            turn_type=turn_type,
            content=content,
            dialogue_act=act,
            intent=intent,
            entities=entities or {},
            confidence=confidence
        )

        self._turns[turn.turn_id] = turn
        self._history.append(turn.turn_id)

        return turn

    def get_turn(self, turn_id: str) -> Optional[Turn]:
        """Get turn by ID."""
        return self._turns.get(turn_id)

    def get_recent(self, n: int = 10) -> List[Turn]:
        """Get recent turns."""
        recent_ids = list(self._history)[-n:]
        return [self._turns[tid] for tid in recent_ids if tid in self._turns]

    def get_history(self) -> List[Turn]:
        """Get all history."""
        return [self._turns[tid] for tid in self._history if tid in self._turns]

    def get_by_type(self, turn_type: TurnType) -> List[Turn]:
        """Get turns by type."""
        return [t for t in self._turns.values() if t.turn_type == turn_type]

    def get_last_user_turn(self) -> Optional[Turn]:
        """Get last user turn."""
        for turn_id in reversed(self._history):
            turn = self._turns.get(turn_id)
            if turn and turn.turn_type == TurnType.USER:
                return turn
        return None

    def get_last_system_turn(self) -> Optional[Turn]:
        """Get last system turn."""
        for turn_id in reversed(self._history):
            turn = self._turns.get(turn_id)
            if turn and turn.turn_type == TurnType.SYSTEM:
                return turn
        return None


# =============================================================================
# TOPIC MANAGER
# =============================================================================

class TopicManager:
    """Manage conversation topics."""

    def __init__(self):
        self._topics: Dict[str, Topic] = {}
        self._active_topic: Optional[str] = None
        self._topic_stack: List[str] = []

    def create_topic(
        self,
        name: str,
        parent_id: Optional[str] = None
    ) -> Topic:
        """Create a new topic."""
        depth = 0
        if parent_id and parent_id in self._topics:
            depth = self._topics[parent_id].depth + 1

        topic = Topic(
            name=name,
            parent_id=parent_id,
            depth=depth
        )

        self._topics[topic.topic_id] = topic
        return topic

    def switch_topic(self, topic_id: str) -> Optional[Topic]:
        """Switch to a topic."""
        if topic_id not in self._topics:
            return None

        # Suspend current topic
        if self._active_topic:
            self._topics[self._active_topic].status = TopicStatus.SUSPENDED
            self._topic_stack.append(self._active_topic)

        # Activate new topic
        self._active_topic = topic_id
        self._topics[topic_id].status = TopicStatus.ACTIVE

        return self._topics[topic_id]

    def close_topic(self, topic_id: Optional[str] = None) -> Optional[Topic]:
        """Close a topic."""
        tid = topic_id or self._active_topic
        if not tid or tid not in self._topics:
            return None

        self._topics[tid].status = TopicStatus.CLOSED

        # Resume previous topic if this was active
        if tid == self._active_topic:
            self._active_topic = None
            if self._topic_stack:
                prev = self._topic_stack.pop()
                self._topics[prev].status = TopicStatus.ACTIVE
                self._active_topic = prev

        return self._topics[tid]

    def get_current(self) -> Optional[Topic]:
        """Get current topic."""
        if self._active_topic:
            return self._topics.get(self._active_topic)
        return None

    def add_turn_to_topic(self, turn_id: str, topic_id: Optional[str] = None) -> None:
        """Add turn to topic."""
        tid = topic_id or self._active_topic
        if tid and tid in self._topics:
            self._topics[tid].turns.append(turn_id)

    def get_topic_history(self) -> List[Topic]:
        """Get topic history."""
        return sorted(
            self._topics.values(),
            key=lambda t: t.started_at
        )


# =============================================================================
# STATE TRACKER
# =============================================================================

class StateTracker:
    """Track dialogue state."""

    def __init__(self):
        self._state = DialogueState()
        self._history: List[DialogueState] = []

    def update(
        self,
        turn: Turn,
        topic_id: Optional[str] = None
    ) -> DialogueState:
        """Update state with turn."""
        # Save current state
        self._history.append(self._state)

        # Create new state
        self._state = DialogueState(
            status=DialogueStatus.ACTIVE,
            current_topic=topic_id or self._state.current_topic,
            slots=self._state.slots.copy(),
            context=self._state.context.copy(),
            history=self._state.history + [turn.turn_id],
            turn_count=self._state.turn_count + 1,
            last_intent=turn.intent or self._state.last_intent,
            last_act=turn.dialogue_act
        )

        # Update entities as slots
        for key, value in turn.entities.items():
            self._state.slots[key] = value

        return self._state

    def get_state(self) -> DialogueState:
        """Get current state."""
        return self._state

    def set_slot(self, key: str, value: Any) -> None:
        """Set slot value."""
        self._state.slots[key] = value

    def get_slot(self, key: str) -> Any:
        """Get slot value."""
        return self._state.slots.get(key)

    def set_context(self, key: str, value: Any) -> None:
        """Set context value."""
        self._state.context[key] = value

    def get_context(self, key: str) -> Any:
        """Get context value."""
        return self._state.context.get(key)

    def clear_slots(self) -> None:
        """Clear all slots."""
        self._state.slots.clear()

    def rollback(self, steps: int = 1) -> DialogueState:
        """Rollback state."""
        for _ in range(steps):
            if self._history:
                self._state = self._history.pop()
        return self._state


# =============================================================================
# FLOW CONTROLLER
# =============================================================================

class FlowController:
    """Control conversation flow."""

    def __init__(self, flow_type: FlowType = FlowType.FREE_FORM):
        self._flow_type = flow_type
        self._nodes: Dict[str, FlowNode] = {}
        self._current_node: Optional[str] = None
        self._start_node: Optional[str] = None

    def add_node(
        self,
        name: str,
        prompt: str,
        transitions: Optional[Dict[str, str]] = None,
        expected_intents: Optional[List[str]] = None,
        slot_to_fill: Optional[str] = None,
        is_terminal: bool = False
    ) -> FlowNode:
        """Add flow node."""
        node = FlowNode(
            name=name,
            prompt=prompt,
            transitions=transitions or {},
            expected_intents=expected_intents or [],
            slot_to_fill=slot_to_fill,
            is_terminal=is_terminal
        )
        self._nodes[node.node_id] = node

        if not self._start_node:
            self._start_node = node.node_id

        return node

    def set_start(self, node_id: str) -> None:
        """Set start node."""
        if node_id in self._nodes:
            self._start_node = node_id

    def start(self) -> Optional[FlowNode]:
        """Start flow."""
        if self._start_node:
            self._current_node = self._start_node
            return self._nodes.get(self._start_node)
        return None

    def transition(self, intent: str) -> Optional[FlowNode]:
        """Transition based on intent."""
        if not self._current_node:
            return None

        current = self._nodes.get(self._current_node)
        if not current:
            return None

        next_node_id = current.transitions.get(intent)
        if next_node_id and next_node_id in self._nodes:
            self._current_node = next_node_id
            return self._nodes[next_node_id]

        # Default transition
        if 'default' in current.transitions:
            next_node_id = current.transitions['default']
            if next_node_id in self._nodes:
                self._current_node = next_node_id
                return self._nodes[next_node_id]

        return None

    def get_current(self) -> Optional[FlowNode]:
        """Get current node."""
        if self._current_node:
            return self._nodes.get(self._current_node)
        return None

    def is_at_terminal(self) -> bool:
        """Check if at terminal node."""
        current = self.get_current()
        return current.is_terminal if current else False


# =============================================================================
# RESPONSE GENERATOR
# =============================================================================

class DialogueResponseGenerator:
    """Generate dialogue responses."""

    def __init__(self):
        self._templates: Dict[str, List[str]] = {
            DialogueAct.GREETING.value: [
                "Hello! How can I help you today?",
                "Hi there! What can I do for you?",
                "Greetings! How may I assist you?"
            ],
            DialogueAct.FAREWELL.value: [
                "Goodbye! Have a great day!",
                "See you later! Take care!",
                "Bye! Feel free to return anytime."
            ],
            DialogueAct.ACKNOWLEDGEMENT.value: [
                "I understand.",
                "Got it.",
                "Alright, noted."
            ],
            DialogueAct.CLARIFICATION.value: [
                "Could you please clarify what you mean?",
                "I'm not sure I understand. Can you explain?",
                "What exactly do you mean by that?"
            ],
            DialogueAct.APOLOGY.value: [
                "I'm sorry about that.",
                "My apologies for any confusion.",
                "Sorry for the inconvenience."
            ],
            DialogueAct.THANKS.value: [
                "You're welcome!",
                "Happy to help!",
                "Anytime!"
            ]
        }

    def generate(
        self,
        act: DialogueAct,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response for dialogue act."""
        templates = self._templates.get(act.value, ["I understand."])
        response = random.choice(templates)

        # Fill in context
        if context:
            for key, value in context.items():
                response = response.replace(f"{{{key}}}", str(value))

        return response

    def add_template(self, act: DialogueAct, template: str) -> None:
        """Add response template."""
        if act.value not in self._templates:
            self._templates[act.value] = []
        self._templates[act.value].append(template)

    def generate_from_prompt(self, prompt: str, slots: Dict[str, Any]) -> str:
        """Generate response from prompt with slots."""
        response = prompt
        for key, value in slots.items():
            response = response.replace(f"{{{key}}}", str(value))
        return response


# =============================================================================
# REPAIR HANDLER
# =============================================================================

class RepairHandler:
    """Handle conversation repairs."""

    def __init__(self):
        self._repair_count = 0

    def detect_repair_needed(
        self,
        turn: Turn,
        state: DialogueState
    ) -> Tuple[bool, RepairType]:
        """Detect if repair is needed."""
        # Low confidence
        if turn.confidence < 0.3:
            return True, RepairType.CLARIFICATION

        # Clarification request
        if turn.dialogue_act == DialogueAct.CLARIFICATION:
            return True, RepairType.CLARIFICATION

        # Contradiction
        if turn.dialogue_act == DialogueAct.DENIAL:
            return True, RepairType.CORRECTION

        # Unknown intent
        if not turn.intent and turn.dialogue_act == DialogueAct.UNKNOWN:
            return True, RepairType.CLARIFICATION

        return False, RepairType.IGNORE

    def generate_repair(
        self,
        repair_type: RepairType,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate repair response."""
        self._repair_count += 1

        if repair_type == RepairType.CLARIFICATION:
            return "I'm not sure I understand. Could you rephrase that?"

        elif repair_type == RepairType.CORRECTION:
            return "I apologize for the confusion. Let me correct that."

        elif repair_type == RepairType.RESTART:
            return "Let's start over. How can I help you?"

        return "I see. Let me try again."

    def get_repair_count(self) -> int:
        """Get repair count."""
        return self._repair_count


# =============================================================================
# DIALOGUE POLICY
# =============================================================================

class DialoguePolicyEngine:
    """Manage dialogue policies."""

    def __init__(self):
        self._policies: List[DialoguePolicy] = []
        self._default_responses: Dict[DialogueAct, str] = {
            DialogueAct.GREETING: "Hello! How can I help you?",
            DialogueAct.FAREWELL: "Goodbye!",
            DialogueAct.QUESTION: "Let me help you with that.",
            DialogueAct.REQUEST: "I'll do my best to help.",
            DialogueAct.THANKS: "You're welcome!",
        }

    def add_policy(
        self,
        name: str,
        rules: Dict[str, str],
        priority: int = 0
    ) -> DialoguePolicy:
        """Add policy."""
        policy = DialoguePolicy(
            name=name,
            rules=rules,
            priority=priority
        )
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority, reverse=True)
        return policy

    def select_action(
        self,
        state: DialogueState,
        turn: Turn
    ) -> str:
        """Select action based on state."""
        # Check policies
        for policy in self._policies:
            for condition, action in policy.rules.items():
                if self._evaluate_condition(condition, state, turn):
                    return action

        # Default response
        return self._default_responses.get(
            turn.dialogue_act,
            "I understand. How can I help further?"
        )

    def _evaluate_condition(
        self,
        condition: str,
        state: DialogueState,
        turn: Turn
    ) -> bool:
        """Evaluate policy condition."""
        # Simple condition evaluation
        if condition.startswith("intent:"):
            intent = condition.split(":")[1]
            return turn.intent == intent

        if condition.startswith("act:"):
            act = condition.split(":")[1]
            return turn.dialogue_act.value == act

        if condition.startswith("slot:"):
            slot = condition.split(":")[1]
            return slot in state.slots

        return False


# =============================================================================
# DIALOGUE MANAGER
# =============================================================================

class DialogueManager:
    """
    Dialogue Manager for BAEL.

    Advanced dialogue and conversation management.
    """

    def __init__(self, flow_type: FlowType = FlowType.FREE_FORM):
        self._turn_manager = TurnManager()
        self._topic_manager = TopicManager()
        self._state_tracker = StateTracker()
        self._flow_controller = FlowController(flow_type)
        self._response_generator = DialogueResponseGenerator()
        self._repair_handler = RepairHandler()
        self._policy_engine = DialoguePolicyEngine()
        self._act_classifier = DialogueActClassifier()
        self._stats = DialogueStats()

    # -------------------------------------------------------------------------
    # TURN MANAGEMENT
    # -------------------------------------------------------------------------

    def process_input(
        self,
        text: str,
        intent: str = "",
        entities: Optional[Dict[str, Any]] = None
    ) -> Turn:
        """Process user input."""
        # Create turn
        turn = self._turn_manager.create_turn(
            content=text,
            turn_type=TurnType.USER,
            intent=intent,
            entities=entities
        )

        # Update state
        topic = self._topic_manager.get_current()
        topic_id = topic.topic_id if topic else None
        self._state_tracker.update(turn, topic_id)

        # Add to topic
        self._topic_manager.add_turn_to_topic(turn.turn_id)

        # Update stats
        self._stats.total_turns += 1
        self._stats.user_turns += 1
        self._stats.avg_turn_length = (
            (self._stats.avg_turn_length * (self._stats.total_turns - 1) + len(text))
            / self._stats.total_turns
        )

        return turn

    def generate_response(self, turn: Turn) -> str:
        """Generate response for turn."""
        state = self._state_tracker.get_state()

        # Check for repair needed
        needs_repair, repair_type = self._repair_handler.detect_repair_needed(turn, state)
        if needs_repair and repair_type != RepairType.IGNORE:
            response = self._repair_handler.generate_repair(repair_type)
            self._stats.repairs_made += 1
        else:
            # Use flow if available
            current_node = self._flow_controller.get_current()
            if current_node:
                response = self._response_generator.generate_from_prompt(
                    current_node.prompt,
                    state.slots
                )
                # Transition
                if turn.intent:
                    self._flow_controller.transition(turn.intent)
            else:
                # Use policy engine
                response = self._policy_engine.select_action(state, turn)

        # Create system turn
        system_turn = self._turn_manager.create_turn(
            content=response,
            turn_type=TurnType.SYSTEM
        )

        self._stats.total_turns += 1
        self._stats.system_turns += 1

        return response

    def get_recent_turns(self, n: int = 10) -> List[Turn]:
        """Get recent turns."""
        return self._turn_manager.get_recent(n)

    def get_turn_history(self) -> List[Turn]:
        """Get full turn history."""
        return self._turn_manager.get_history()

    # -------------------------------------------------------------------------
    # TOPIC MANAGEMENT
    # -------------------------------------------------------------------------

    def start_topic(self, name: str) -> Topic:
        """Start a new topic."""
        topic = self._topic_manager.create_topic(name)
        self._topic_manager.switch_topic(topic.topic_id)
        self._stats.topics_discussed += 1
        return topic

    def switch_topic(self, topic_id: str) -> Optional[Topic]:
        """Switch to existing topic."""
        return self._topic_manager.switch_topic(topic_id)

    def close_topic(self) -> Optional[Topic]:
        """Close current topic."""
        return self._topic_manager.close_topic()

    def get_current_topic(self) -> Optional[Topic]:
        """Get current topic."""
        return self._topic_manager.get_current()

    def get_topic_history(self) -> List[Topic]:
        """Get topic history."""
        return self._topic_manager.get_topic_history()

    # -------------------------------------------------------------------------
    # STATE MANAGEMENT
    # -------------------------------------------------------------------------

    def get_state(self) -> DialogueState:
        """Get dialogue state."""
        return self._state_tracker.get_state()

    def set_slot(self, key: str, value: Any) -> None:
        """Set slot value."""
        self._state_tracker.set_slot(key, value)

    def get_slot(self, key: str) -> Any:
        """Get slot value."""
        return self._state_tracker.get_slot(key)

    def set_context(self, key: str, value: Any) -> None:
        """Set context value."""
        self._state_tracker.set_context(key, value)

    def get_context(self, key: str) -> Any:
        """Get context value."""
        return self._state_tracker.get_context(key)

    def clear_slots(self) -> None:
        """Clear all slots."""
        self._state_tracker.clear_slots()

    def rollback(self, steps: int = 1) -> DialogueState:
        """Rollback state."""
        return self._state_tracker.rollback(steps)

    # -------------------------------------------------------------------------
    # FLOW CONTROL
    # -------------------------------------------------------------------------

    def add_flow_node(
        self,
        name: str,
        prompt: str,
        transitions: Optional[Dict[str, str]] = None,
        slot_to_fill: Optional[str] = None,
        is_terminal: bool = False
    ) -> FlowNode:
        """Add flow node."""
        return self._flow_controller.add_node(
            name=name,
            prompt=prompt,
            transitions=transitions,
            slot_to_fill=slot_to_fill,
            is_terminal=is_terminal
        )

    def start_flow(self) -> Optional[FlowNode]:
        """Start conversation flow."""
        return self._flow_controller.start()

    def get_current_node(self) -> Optional[FlowNode]:
        """Get current flow node."""
        return self._flow_controller.get_current()

    def is_flow_complete(self) -> bool:
        """Check if flow is complete."""
        return self._flow_controller.is_at_terminal()

    # -------------------------------------------------------------------------
    # DIALOGUE ACT
    # -------------------------------------------------------------------------

    def classify_act(self, text: str) -> Tuple[DialogueAct, float]:
        """Classify dialogue act."""
        return self._act_classifier.classify(text)

    # -------------------------------------------------------------------------
    # RESPONSE TEMPLATES
    # -------------------------------------------------------------------------

    def add_response_template(self, act: DialogueAct, template: str) -> None:
        """Add response template."""
        self._response_generator.add_template(act, template)

    def generate_act_response(
        self,
        act: DialogueAct,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate response for dialogue act."""
        return self._response_generator.generate(act, context)

    # -------------------------------------------------------------------------
    # POLICIES
    # -------------------------------------------------------------------------

    def add_policy(
        self,
        name: str,
        rules: Dict[str, str],
        priority: int = 0
    ) -> DialoguePolicy:
        """Add dialogue policy."""
        return self._policy_engine.add_policy(name, rules, priority)

    # -------------------------------------------------------------------------
    # REPAIR
    # -------------------------------------------------------------------------

    def needs_repair(self, turn: Turn) -> Tuple[bool, RepairType]:
        """Check if repair is needed."""
        state = self._state_tracker.get_state()
        return self._repair_handler.detect_repair_needed(turn, state)

    def generate_repair(self, repair_type: RepairType) -> str:
        """Generate repair response."""
        return self._repair_handler.generate_repair(repair_type)

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_stats(self) -> DialogueStats:
        """Get dialogue statistics."""
        return self._stats

    def end_dialogue(self) -> DialogueStats:
        """End dialogue and get final stats."""
        self._state_tracker._state.status = DialogueStatus.COMPLETED
        self._topic_manager.close_topic()
        return self._stats


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Dialogue Manager."""
    print("=" * 70)
    print("BAEL - DIALOGUE MANAGER DEMO")
    print("Advanced Dialogue and Conversation Management")
    print("=" * 70)
    print()

    manager = DialogueManager(flow_type=FlowType.FREE_FORM)

    # 1. Process Input
    print("1. PROCESS INPUT:")
    print("-" * 40)

    turn = manager.process_input(
        "Hello, I need help with my order",
        intent="greeting",
        entities={"topic": "order"}
    )

    print(f"   User: \"{turn.content}\"")
    print(f"   Act: {turn.dialogue_act.value}")
    print(f"   Confidence: {turn.confidence:.2f}")
    print()

    # 2. Generate Response
    print("2. GENERATE RESPONSE:")
    print("-" * 40)

    response = manager.generate_response(turn)

    print(f"   Response: \"{response}\"")
    print()

    # 3. Dialogue Acts
    print("3. DIALOGUE ACTS:")
    print("-" * 40)

    test_texts = [
        "Hi there!",
        "What is the weather?",
        "Please help me",
        "Yes, that's correct",
        "Thanks a lot!"
    ]

    for text in test_texts:
        act, conf = manager.classify_act(text)
        print(f"   \"{text[:25]}...\" -> {act.value} ({conf:.2f})")
    print()

    # 4. Topic Management
    print("4. TOPIC MANAGEMENT:")
    print("-" * 40)

    topic1 = manager.start_topic("Order Support")
    print(f"   Started topic: {topic1.name}")

    topic2 = manager.start_topic("Shipping Question")
    print(f"   Started topic: {topic2.name}")

    current = manager.get_current_topic()
    print(f"   Current topic: {current.name if current else 'None'}")

    manager.close_topic()
    current = manager.get_current_topic()
    print(f"   After close: {current.name if current else 'None'}")
    print()

    # 5. Slot Management
    print("5. SLOT MANAGEMENT:")
    print("-" * 40)

    manager.set_slot("order_id", "12345")
    manager.set_slot("customer_name", "John")
    manager.set_slot("item", "laptop")

    print(f"   order_id: {manager.get_slot('order_id')}")
    print(f"   customer_name: {manager.get_slot('customer_name')}")
    print(f"   item: {manager.get_slot('item')}")
    print()

    # 6. Dialogue State
    print("6. DIALOGUE STATE:")
    print("-" * 40)

    state = manager.get_state()

    print(f"   Status: {state.status.value}")
    print(f"   Turn count: {state.turn_count}")
    print(f"   Last act: {state.last_act.value}")
    print(f"   Slots: {len(state.slots)}")
    print()

    # 7. Context
    print("7. CONTEXT:")
    print("-" * 40)

    manager.set_context("user_mood", "neutral")
    manager.set_context("conversation_type", "support")

    print(f"   user_mood: {manager.get_context('user_mood')}")
    print(f"   conversation_type: {manager.get_context('conversation_type')}")
    print()

    # 8. Flow Control
    print("8. FLOW CONTROL:")
    print("-" * 40)

    node1 = manager.add_flow_node(
        name="welcome",
        prompt="Welcome! How can I help you today?",
        transitions={"order": "order_info", "shipping": "shipping_info"}
    )

    node2 = manager.add_flow_node(
        name="order_info",
        prompt="What is your order number?",
        slot_to_fill="order_id"
    )

    node3 = manager.add_flow_node(
        name="shipping_info",
        prompt="Let me check your shipping status.",
        is_terminal=True
    )

    print(f"   Added nodes: welcome, order_info, shipping_info")

    start = manager.start_flow()
    print(f"   Started at: {start.name if start else 'None'}")
    print()

    # 9. Multiple Turns
    print("9. CONVERSATION SIMULATION:")
    print("-" * 40)

    exchanges = [
        ("What can you help me with?", "question"),
        ("I want to track my order", "track_order"),
        ("Order number is 98765", "provide_info"),
        ("Thanks for the help!", "thanks")
    ]

    for text, intent in exchanges:
        turn = manager.process_input(text, intent=intent)
        response = manager.generate_response(turn)
        print(f"   User: {text}")
        print(f"   System: {response}")
        print()

    # 10. Turn History
    print("10. TURN HISTORY:")
    print("-" * 40)

    history = manager.get_recent_turns(5)

    for t in history:
        speaker = "User" if t.turn_type == TurnType.USER else "System"
        print(f"   {speaker}: {t.content[:40]}...")
    print()

    # 11. Repair Detection
    print("11. REPAIR DETECTION:")
    print("-" * 40)

    # Create a turn that needs repair
    unclear_turn = Turn(
        content="asdfasdf",
        dialogue_act=DialogueAct.UNKNOWN,
        confidence=0.1
    )

    needs, repair_type = manager.needs_repair(unclear_turn)

    print(f"   Content: \"{unclear_turn.content}\"")
    print(f"   Needs repair: {needs}")
    print(f"   Repair type: {repair_type.value}")

    if needs:
        repair = manager.generate_repair(repair_type)
        print(f"   Repair: \"{repair}\"")
    print()

    # 12. Policies
    print("12. POLICIES:")
    print("-" * 40)

    manager.add_policy(
        "greeting_policy",
        rules={
            "act:greeting": "Hello! How can I assist you?",
            "intent:help": "I'm here to help. What do you need?"
        },
        priority=1
    )

    print("   Added greeting_policy with 2 rules")
    print()

    # 13. Response Templates
    print("13. RESPONSE TEMPLATES:")
    print("-" * 40)

    manager.add_response_template(
        DialogueAct.GREETING,
        "Welcome aboard! What brings you here today?"
    )

    response = manager.generate_act_response(DialogueAct.GREETING)
    print(f"   Greeting response: \"{response}\"")

    response = manager.generate_act_response(DialogueAct.THANKS)
    print(f"   Thanks response: \"{response}\"")
    print()

    # 14. Rollback
    print("14. ROLLBACK:")
    print("-" * 40)

    before = manager.get_state().turn_count
    manager.rollback(2)
    after = manager.get_state().turn_count

    print(f"   Before rollback: {before} turns")
    print(f"   After rollback: {after} turns")
    print()

    # 15. Statistics
    print("15. STATISTICS:")
    print("-" * 40)

    stats = manager.get_stats()

    print(f"   Total turns: {stats.total_turns}")
    print(f"   User turns: {stats.user_turns}")
    print(f"   System turns: {stats.system_turns}")
    print(f"   Avg turn length: {stats.avg_turn_length:.1f}")
    print(f"   Topics: {stats.topics_discussed}")
    print(f"   Repairs: {stats.repairs_made}")
    print()

    # End dialogue
    final_stats = manager.end_dialogue()

    print("=" * 70)
    print("DEMO COMPLETE - Dialogue Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
