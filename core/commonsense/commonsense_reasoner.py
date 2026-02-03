#!/usr/bin/env python3
"""
BAEL - Commonsense Reasoner
Advanced commonsense reasoning and world knowledge.

Features:
- Commonsense knowledge base
- Script and frame reasoning
- Default reasoning
- Physical world reasoning
- Social commonsense
- Temporal commonsense
- Qualitative reasoning
- Exception handling
"""

import asyncio
import hashlib
import math
import random
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

class KnowledgeType(Enum):
    """Types of commonsense knowledge."""
    PHYSICAL = "physical"  # Physical world
    SOCIAL = "social"  # Social interactions
    TEMPORAL = "temporal"  # Time-related
    CAUSAL = "causal"  # Cause and effect
    PSYCHOLOGICAL = "psychological"  # Mental states
    SPATIAL = "spatial"  # Space and location
    FUNCTIONAL = "functional"  # Object functions


class InferenceType(Enum):
    """Types of inference."""
    DEDUCTIVE = "deductive"
    ABDUCTIVE = "abductive"
    DEFAULT = "default"
    ANALOGICAL = "analogical"


class BeliefStatus(Enum):
    """Status of a belief."""
    CERTAIN = "certain"
    DEFAULT = "default"  # Believed unless contradicted
    POSSIBLE = "possible"
    CONTRADICTED = "contradicted"


class ScriptEvent(Enum):
    """Types of script events."""
    ENTRY = "entry"
    ACTION = "action"
    EXIT = "exit"
    PRECONDITION = "precondition"
    POSTCONDITION = "postcondition"


class QualitativeValue(Enum):
    """Qualitative values for reasoning."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STEADY = "steady"
    ZERO = "zero"
    POSITIVE = "positive"
    NEGATIVE = "negative"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Concept:
    """A commonsense concept."""
    concept_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: KnowledgeType = KnowledgeType.PHYSICAL
    properties: Dict[str, Any] = field(default_factory=dict)
    is_a: List[str] = field(default_factory=list)
    has_parts: List[str] = field(default_factory=list)


@dataclass
class Relation:
    """A commonsense relation."""
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    subject: str = ""
    object: str = ""
    weight: float = 1.0
    is_default: bool = False


@dataclass
class Script:
    """A script (stereotypical event sequence)."""
    script_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    roles: List[str] = field(default_factory=list)
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)


@dataclass
class Frame:
    """A frame (structured representation)."""
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slots: Dict[str, Any] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, str] = field(default_factory=dict)


@dataclass
class Belief:
    """A belief with status."""
    belief_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    status: BeliefStatus = BeliefStatus.DEFAULT
    confidence: float = 0.8
    source: str = ""
    exceptions: List[str] = field(default_factory=list)


@dataclass
class InferenceResult:
    """Result of commonsense inference."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    conclusions: List[str] = field(default_factory=list)
    inference_type: InferenceType = InferenceType.DEFAULT
    confidence: float = 0.0
    explanation: str = ""


# =============================================================================
# KNOWLEDGE BASE
# =============================================================================

class CommonsenseKB:
    """Commonsense knowledge base."""

    def __init__(self):
        self._concepts: Dict[str, Concept] = {}
        self._relations: Dict[str, List[Relation]] = defaultdict(list)
        self._inverse_relations: Dict[str, List[Relation]] = defaultdict(list)
        self._scripts: Dict[str, Script] = {}
        self._frames: Dict[str, Frame] = {}

        # Initialize with basic commonsense
        self._initialize_basic_knowledge()

    def _initialize_basic_knowledge(self) -> None:
        """Initialize with basic commonsense knowledge."""
        # Physical concepts
        self.add_concept("object", KnowledgeType.PHYSICAL,
                        properties={"has_mass": True, "has_location": True})
        self.add_concept("container", KnowledgeType.PHYSICAL,
                        is_a=["object"], properties={"can_hold": True})
        self.add_concept("liquid", KnowledgeType.PHYSICAL,
                        properties={"flows": True, "has_volume": True})
        self.add_concept("solid", KnowledgeType.PHYSICAL,
                        properties={"rigid": True, "has_shape": True})

        # Living things
        self.add_concept("living_thing", KnowledgeType.PHYSICAL,
                        properties={"alive": True, "needs_food": True})
        self.add_concept("person", KnowledgeType.SOCIAL,
                        is_a=["living_thing"],
                        properties={"has_emotions": True, "can_think": True})
        self.add_concept("animal", KnowledgeType.PHYSICAL,
                        is_a=["living_thing"],
                        properties={"can_move": True})

        # Physical relations
        self.add_relation("inside", "object", "container", is_default=True)
        self.add_relation("supports", "solid", "object", is_default=True)
        self.add_relation("heavier_than", "object", "object", is_default=False)

        # Causal relations
        self.add_relation("causes", "dropping", "falling", is_default=True)
        self.add_relation("causes", "heating", "temperature_increase", is_default=True)
        self.add_relation("causes", "pushing", "moving", is_default=True)

        # Basic scripts
        self._initialize_scripts()

    def _initialize_scripts(self) -> None:
        """Initialize common scripts."""
        # Restaurant script
        restaurant_script = Script(
            name="restaurant",
            roles=["customer", "waiter", "chef"],
            scenes=[
                {"event": "enter", "actor": "customer", "location": "restaurant"},
                {"event": "seat", "actor": "waiter", "target": "customer"},
                {"event": "order", "actor": "customer", "target": "waiter"},
                {"event": "cook", "actor": "chef", "object": "food"},
                {"event": "serve", "actor": "waiter", "object": "food"},
                {"event": "eat", "actor": "customer", "object": "food"},
                {"event": "pay", "actor": "customer", "object": "bill"},
                {"event": "leave", "actor": "customer", "location": "restaurant"}
            ],
            preconditions=["customer_has_money", "restaurant_is_open"],
            postconditions=["customer_is_fed", "restaurant_has_money"]
        )
        self._scripts["restaurant"] = restaurant_script

        # Shopping script
        shopping_script = Script(
            name="shopping",
            roles=["customer", "cashier"],
            scenes=[
                {"event": "enter", "actor": "customer", "location": "store"},
                {"event": "browse", "actor": "customer", "location": "store"},
                {"event": "select", "actor": "customer", "object": "items"},
                {"event": "checkout", "actor": "customer", "location": "counter"},
                {"event": "pay", "actor": "customer", "target": "cashier"},
                {"event": "bag", "actor": "cashier", "object": "items"},
                {"event": "leave", "actor": "customer", "location": "store"}
            ],
            preconditions=["customer_has_money", "store_is_open"],
            postconditions=["customer_has_items", "store_has_money"]
        )
        self._scripts["shopping"] = shopping_script

    def add_concept(
        self,
        name: str,
        category: KnowledgeType,
        properties: Optional[Dict[str, Any]] = None,
        is_a: Optional[List[str]] = None,
        has_parts: Optional[List[str]] = None
    ) -> Concept:
        """Add a concept."""
        concept = Concept(
            name=name,
            category=category,
            properties=properties or {},
            is_a=is_a or [],
            has_parts=has_parts or []
        )
        self._concepts[name] = concept
        return concept

    def add_relation(
        self,
        name: str,
        subject: str,
        object_: str,
        weight: float = 1.0,
        is_default: bool = False
    ) -> Relation:
        """Add a relation."""
        relation = Relation(
            name=name,
            subject=subject,
            object=object_,
            weight=weight,
            is_default=is_default
        )
        self._relations[name].append(relation)
        self._inverse_relations[object_].append(relation)
        return relation

    def get_concept(self, name: str) -> Optional[Concept]:
        """Get a concept by name."""
        return self._concepts.get(name)

    def get_relations(self, name: str) -> List[Relation]:
        """Get relations by name."""
        return self._relations.get(name, [])

    def get_script(self, name: str) -> Optional[Script]:
        """Get a script by name."""
        return self._scripts.get(name)

    def is_a(self, concept: str, parent: str) -> bool:
        """Check if concept is a type of parent."""
        c = self._concepts.get(concept)
        if not c:
            return False

        if parent in c.is_a:
            return True

        # Check transitively
        for p in c.is_a:
            if self.is_a(p, parent):
                return True

        return False

    def get_properties(self, concept: str) -> Dict[str, Any]:
        """Get all properties of a concept (including inherited)."""
        c = self._concepts.get(concept)
        if not c:
            return {}

        properties = dict(c.properties)

        # Inherit from parents
        for parent in c.is_a:
            parent_props = self.get_properties(parent)
            for key, val in parent_props.items():
                if key not in properties:
                    properties[key] = val

        return properties


# =============================================================================
# DEFAULT REASONER
# =============================================================================

class DefaultReasoner:
    """Non-monotonic default reasoning."""

    def __init__(self, kb: CommonsenseKB):
        self._kb = kb
        self._beliefs: Dict[str, Belief] = {}

    def assert_belief(
        self,
        content: str,
        status: BeliefStatus = BeliefStatus.DEFAULT,
        confidence: float = 0.8,
        source: str = ""
    ) -> Belief:
        """Assert a belief."""
        belief = Belief(
            content=content,
            status=status,
            confidence=confidence,
            source=source
        )
        self._beliefs[content] = belief
        return belief

    def add_exception(
        self,
        belief_content: str,
        exception: str
    ) -> None:
        """Add an exception to a default belief."""
        belief = self._beliefs.get(belief_content)
        if belief:
            belief.exceptions.append(exception)

    def query(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float]:
        """Query a belief with context."""
        belief = self._beliefs.get(content)

        if not belief:
            return False, 0.0

        if belief.status == BeliefStatus.CERTAIN:
            return True, belief.confidence

        if belief.status == BeliefStatus.CONTRADICTED:
            return False, 0.0

        if belief.status == BeliefStatus.DEFAULT:
            # Check exceptions
            if context:
                for exception in belief.exceptions:
                    if exception in str(context):
                        return False, 0.0
            return True, belief.confidence

        return True, belief.confidence * 0.5

    def defeat(self, belief_content: str, reason: str) -> None:
        """Defeat a default belief."""
        belief = self._beliefs.get(belief_content)
        if belief and belief.status == BeliefStatus.DEFAULT:
            belief.status = BeliefStatus.CONTRADICTED

    def reinstate(self, belief_content: str) -> None:
        """Reinstate a defeated belief."""
        belief = self._beliefs.get(belief_content)
        if belief and belief.status == BeliefStatus.CONTRADICTED:
            belief.status = BeliefStatus.DEFAULT


# =============================================================================
# PHYSICAL REASONER
# =============================================================================

class PhysicalReasoner:
    """Reasoning about the physical world."""

    def __init__(self, kb: CommonsenseKB):
        self._kb = kb

    def can_support(
        self,
        supporter: str,
        supported: str
    ) -> Tuple[bool, str]:
        """Check if one object can support another."""
        # Get concepts
        supporter_concept = self._kb.get_concept(supporter)
        supported_concept = self._kb.get_concept(supported)

        if not supporter_concept or not supported_concept:
            return False, "Unknown concepts"

        # Check if supporter is solid
        supporter_props = self._kb.get_properties(supporter)
        if not supporter_props.get("rigid", False):
            return False, "Supporter is not rigid"

        # Check if supported has mass
        supported_props = self._kb.get_properties(supported)
        if not supported_props.get("has_mass", True):
            return False, "Supported has no mass"

        return True, "Rigid object can support objects with mass"

    def can_contain(
        self,
        container: str,
        content: str
    ) -> Tuple[bool, str]:
        """Check if container can contain content."""
        # Check if container
        if not self._kb.is_a(container, "container"):
            container_concept = self._kb.get_concept(container)
            if not container_concept:
                return False, "Unknown container"
            if not container_concept.properties.get("can_hold", False):
                return False, "Not a container"

        # Liquids need sealed containers
        if self._kb.is_a(content, "liquid"):
            return True, "Containers can hold liquids"

        return True, "Container can hold content"

    def predict_fall(
        self,
        object_name: str,
        is_supported: bool
    ) -> Tuple[bool, str]:
        """Predict if object will fall."""
        obj = self._kb.get_concept(object_name)
        if not obj:
            return False, "Unknown object"

        props = self._kb.get_properties(object_name)

        if not props.get("has_mass", True):
            return False, "Object has no mass"

        if is_supported:
            return False, "Object is supported"

        return True, "Unsupported objects with mass fall"

    def qualitative_physics(
        self,
        action: str,
        target: str
    ) -> Dict[str, QualitativeValue]:
        """Qualitative physics prediction."""
        results = {}

        if action == "heat":
            results["temperature"] = QualitativeValue.INCREASING
            if self._kb.is_a(target, "solid"):
                results["volume"] = QualitativeValue.INCREASING
            elif self._kb.is_a(target, "liquid"):
                results["evaporation"] = QualitativeValue.INCREASING

        elif action == "cool":
            results["temperature"] = QualitativeValue.DECREASING
            if self._kb.is_a(target, "liquid"):
                results["viscosity"] = QualitativeValue.INCREASING

        elif action == "push":
            results["position"] = QualitativeValue.INCREASING
            results["velocity"] = QualitativeValue.POSITIVE

        elif action == "drop":
            results["height"] = QualitativeValue.DECREASING
            results["velocity"] = QualitativeValue.INCREASING

        return results


# =============================================================================
# SOCIAL REASONER
# =============================================================================

class SocialReasoner:
    """Reasoning about social situations."""

    def __init__(self, kb: CommonsenseKB):
        self._kb = kb
        self._social_rules: List[Dict[str, Any]] = []
        self._initialize_social_rules()

    def _initialize_social_rules(self) -> None:
        """Initialize social reasoning rules."""
        self._social_rules = [
            {
                "name": "greeting_response",
                "condition": "person_greets",
                "expectation": "greet_back",
                "strength": 0.9
            },
            {
                "name": "help_in_need",
                "condition": "person_in_distress",
                "expectation": "offer_help",
                "strength": 0.7
            },
            {
                "name": "reciprocity",
                "condition": "received_favor",
                "expectation": "return_favor",
                "strength": 0.8
            },
            {
                "name": "politeness",
                "condition": "in_public",
                "expectation": "behave_politely",
                "strength": 0.85
            },
            {
                "name": "privacy",
                "condition": "personal_question",
                "expectation": "may_decline",
                "strength": 0.6
            }
        ]

    def predict_behavior(
        self,
        situation: str,
        actor: str
    ) -> List[Tuple[str, float]]:
        """Predict likely behaviors in situation."""
        predictions = []

        for rule in self._social_rules:
            if rule["condition"] in situation.lower():
                predictions.append((rule["expectation"], rule["strength"]))

        # Sort by strength
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions

    def infer_emotion(
        self,
        event: str,
        person: str
    ) -> List[Tuple[str, float]]:
        """Infer likely emotions from event."""
        emotions = []

        positive_events = ["gift", "praise", "success", "win", "help"]
        negative_events = ["loss", "failure", "insult", "rejection", "harm"]

        for pos in positive_events:
            if pos in event.lower():
                emotions.append(("happy", 0.8))
                emotions.append(("grateful", 0.6))
                break

        for neg in negative_events:
            if neg in event.lower():
                emotions.append(("sad", 0.7))
                emotions.append(("angry", 0.5))
                emotions.append(("disappointed", 0.6))
                break

        return emotions

    def check_social_norm(
        self,
        action: str,
        context: str
    ) -> Tuple[bool, str]:
        """Check if action violates social norms."""
        violations = {
            "shout": "public",
            "interrupt": "conversation",
            "steal": "any",
            "lie": "trust",
            "ignore": "greeting"
        }

        for violation, context_trigger in violations.items():
            if violation in action.lower():
                if context_trigger == "any" or context_trigger in context.lower():
                    return False, f"Violates norm: {violation} in {context}"

        return True, "No norm violation detected"


# =============================================================================
# SCRIPT PROCESSOR
# =============================================================================

class ScriptProcessor:
    """Process scripts for understanding and prediction."""

    def __init__(self, kb: CommonsenseKB):
        self._kb = kb

    def match_script(
        self,
        events: List[Dict[str, str]]
    ) -> Optional[Tuple[Script, float]]:
        """Match events to a known script."""
        best_match = None
        best_score = 0.0

        for script_name, script in self._kb._scripts.items():
            score = self._compute_match_score(events, script)
            if score > best_score:
                best_score = score
                best_match = script

        if best_match and best_score > 0.3:
            return (best_match, best_score)
        return None

    def _compute_match_score(
        self,
        events: List[Dict[str, str]],
        script: Script
    ) -> float:
        """Compute match score between events and script."""
        matched = 0

        for event in events:
            event_type = event.get("event", "")
            for scene in script.scenes:
                if scene.get("event") == event_type:
                    matched += 1
                    break

        return matched / max(len(script.scenes), 1)

    def predict_next(
        self,
        events: List[Dict[str, str]],
        script: Script
    ) -> Optional[Dict[str, Any]]:
        """Predict next event based on script."""
        if not events:
            return script.scenes[0] if script.scenes else None

        last_event = events[-1].get("event", "")

        # Find position in script
        for i, scene in enumerate(script.scenes):
            if scene.get("event") == last_event:
                if i + 1 < len(script.scenes):
                    return script.scenes[i + 1]

        return None

    def fill_roles(
        self,
        script: Script,
        bindings: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Fill script roles with specific bindings."""
        filled_scenes = []

        for scene in script.scenes:
            filled = dict(scene)
            for key, value in filled.items():
                if isinstance(value, str) and value in bindings:
                    filled[key] = bindings[value]
            filled_scenes.append(filled)

        return filled_scenes

    def check_preconditions(
        self,
        script: Script,
        context: Dict[str, bool]
    ) -> Tuple[bool, List[str]]:
        """Check if script preconditions are met."""
        unmet = []

        for precond in script.preconditions:
            if not context.get(precond, False):
                unmet.append(precond)

        return len(unmet) == 0, unmet


# =============================================================================
# FRAME PROCESSOR
# =============================================================================

class FrameProcessor:
    """Process frames for structured knowledge."""

    def __init__(self, kb: CommonsenseKB):
        self._kb = kb

    def create_frame(
        self,
        name: str,
        slots: Dict[str, Any],
        defaults: Optional[Dict[str, Any]] = None
    ) -> Frame:
        """Create a new frame."""
        frame = Frame(
            name=name,
            slots=slots,
            defaults=defaults or {}
        )
        self._kb._frames[name] = frame
        return frame

    def instantiate(
        self,
        frame_name: str,
        values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Instantiate a frame with values."""
        frame = self._kb._frames.get(frame_name)
        if not frame:
            return {}

        instance = dict(frame.defaults)
        instance.update(values)

        # Fill remaining slots with defaults
        for slot, default in frame.slots.items():
            if slot not in instance:
                instance[slot] = default

        return instance

    def match_frame(
        self,
        data: Dict[str, Any]
    ) -> Optional[Tuple[Frame, float]]:
        """Match data to best fitting frame."""
        best_frame = None
        best_score = 0.0

        for frame in self._kb._frames.values():
            score = self._compute_frame_match(data, frame)
            if score > best_score:
                best_score = score
                best_frame = frame

        if best_frame and best_score > 0.3:
            return (best_frame, best_score)
        return None

    def _compute_frame_match(
        self,
        data: Dict[str, Any],
        frame: Frame
    ) -> float:
        """Compute match score between data and frame."""
        matched = 0
        total = len(frame.slots)

        for slot in frame.slots:
            if slot in data:
                matched += 1

        return matched / max(total, 1)


# =============================================================================
# COMMONSENSE REASONER
# =============================================================================

class CommonsenseReasoner:
    """
    Commonsense Reasoner for BAEL.

    Advanced commonsense reasoning and world knowledge.
    """

    def __init__(self):
        self._kb = CommonsenseKB()
        self._default_reasoner = DefaultReasoner(self._kb)
        self._physical_reasoner = PhysicalReasoner(self._kb)
        self._social_reasoner = SocialReasoner(self._kb)
        self._script_processor = ScriptProcessor(self._kb)
        self._frame_processor = FrameProcessor(self._kb)

    # -------------------------------------------------------------------------
    # KNOWLEDGE BASE
    # -------------------------------------------------------------------------

    def add_concept(
        self,
        name: str,
        category: KnowledgeType,
        properties: Optional[Dict[str, Any]] = None,
        is_a: Optional[List[str]] = None
    ) -> Concept:
        """Add a concept to knowledge base."""
        return self._kb.add_concept(name, category, properties, is_a)

    def add_relation(
        self,
        name: str,
        subject: str,
        object_: str,
        is_default: bool = False
    ) -> Relation:
        """Add a relation to knowledge base."""
        return self._kb.add_relation(name, subject, object_, is_default=is_default)

    def get_concept(self, name: str) -> Optional[Concept]:
        """Get a concept."""
        return self._kb.get_concept(name)

    def is_a(self, concept: str, parent: str) -> bool:
        """Check is-a relationship."""
        return self._kb.is_a(concept, parent)

    # -------------------------------------------------------------------------
    # DEFAULT REASONING
    # -------------------------------------------------------------------------

    def assert_default(
        self,
        content: str,
        confidence: float = 0.8
    ) -> Belief:
        """Assert a default belief."""
        return self._default_reasoner.assert_belief(
            content, BeliefStatus.DEFAULT, confidence
        )

    def query_belief(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float]:
        """Query a belief."""
        return self._default_reasoner.query(content, context)

    def add_exception(
        self,
        belief: str,
        exception: str
    ) -> None:
        """Add exception to default."""
        self._default_reasoner.add_exception(belief, exception)

    # -------------------------------------------------------------------------
    # PHYSICAL REASONING
    # -------------------------------------------------------------------------

    def can_support(
        self,
        supporter: str,
        supported: str
    ) -> Tuple[bool, str]:
        """Check physical support."""
        return self._physical_reasoner.can_support(supporter, supported)

    def can_contain(
        self,
        container: str,
        content: str
    ) -> Tuple[bool, str]:
        """Check containment."""
        return self._physical_reasoner.can_contain(container, content)

    def predict_fall(
        self,
        obj: str,
        is_supported: bool
    ) -> Tuple[bool, str]:
        """Predict falling."""
        return self._physical_reasoner.predict_fall(obj, is_supported)

    def qualitative_physics(
        self,
        action: str,
        target: str
    ) -> Dict[str, QualitativeValue]:
        """Qualitative physics reasoning."""
        return self._physical_reasoner.qualitative_physics(action, target)

    # -------------------------------------------------------------------------
    # SOCIAL REASONING
    # -------------------------------------------------------------------------

    def predict_behavior(
        self,
        situation: str,
        actor: str
    ) -> List[Tuple[str, float]]:
        """Predict social behavior."""
        return self._social_reasoner.predict_behavior(situation, actor)

    def infer_emotion(
        self,
        event: str,
        person: str
    ) -> List[Tuple[str, float]]:
        """Infer emotion from event."""
        return self._social_reasoner.infer_emotion(event, person)

    def check_social_norm(
        self,
        action: str,
        context: str
    ) -> Tuple[bool, str]:
        """Check social norm compliance."""
        return self._social_reasoner.check_social_norm(action, context)

    # -------------------------------------------------------------------------
    # SCRIPT REASONING
    # -------------------------------------------------------------------------

    def match_script(
        self,
        events: List[Dict[str, str]]
    ) -> Optional[Tuple[Script, float]]:
        """Match events to script."""
        return self._script_processor.match_script(events)

    def predict_next_event(
        self,
        events: List[Dict[str, str]],
        script: Script
    ) -> Optional[Dict[str, Any]]:
        """Predict next event."""
        return self._script_processor.predict_next(events, script)

    def get_script(self, name: str) -> Optional[Script]:
        """Get a script."""
        return self._kb.get_script(name)

    # -------------------------------------------------------------------------
    # FRAME REASONING
    # -------------------------------------------------------------------------

    def create_frame(
        self,
        name: str,
        slots: Dict[str, Any],
        defaults: Optional[Dict[str, Any]] = None
    ) -> Frame:
        """Create a frame."""
        return self._frame_processor.create_frame(name, slots, defaults)

    def instantiate_frame(
        self,
        frame_name: str,
        values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Instantiate a frame."""
        return self._frame_processor.instantiate(frame_name, values)

    # -------------------------------------------------------------------------
    # INTEGRATED REASONING
    # -------------------------------------------------------------------------

    def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> InferenceResult:
        """Perform commonsense reasoning on a query."""
        conclusions = []
        confidence = 0.0
        explanation = ""

        # Try different reasoning strategies

        # 1. Check default beliefs
        belief_result, belief_conf = self.query_belief(query, context)
        if belief_result:
            conclusions.append(f"Believed: {query}")
            confidence = max(confidence, belief_conf)
            explanation += f"Default belief with confidence {belief_conf:.2f}. "

        # 2. Check physical reasoning
        words = query.lower().split()
        if any(w in words for w in ["fall", "drop", "support", "contain"]):
            if "fall" in words or "drop" in words:
                # Extract object
                will_fall, reason = self.predict_fall("object", False)
                conclusions.append(reason)
                confidence = max(confidence, 0.8)
                explanation += f"Physical reasoning: {reason}. "

        # 3. Check social reasoning
        if any(w in query.lower() for w in ["person", "people", "social", "feel"]):
            behaviors = self.predict_behavior(query, "person")
            for behavior, strength in behaviors[:2]:
                conclusions.append(f"Expected behavior: {behavior}")
                confidence = max(confidence, strength)
            explanation += "Social reasoning applied. "

        return InferenceResult(
            query=query,
            conclusions=conclusions,
            inference_type=InferenceType.DEFAULT,
            confidence=confidence,
            explanation=explanation.strip()
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Commonsense Reasoner."""
    print("=" * 70)
    print("BAEL - COMMONSENSE REASONER DEMO")
    print("Advanced Commonsense Reasoning and World Knowledge")
    print("=" * 70)
    print()

    reasoner = CommonsenseReasoner()

    # 1. Knowledge Base
    print("1. KNOWLEDGE BASE:")
    print("-" * 40)

    # Add some concepts
    reasoner.add_concept("cup", KnowledgeType.PHYSICAL,
                        properties={"can_hold": True, "fragile": True},
                        is_a=["container"])
    reasoner.add_concept("water", KnowledgeType.PHYSICAL,
                        properties={"drinkable": True},
                        is_a=["liquid"])
    reasoner.add_concept("table", KnowledgeType.PHYSICAL,
                        properties={"rigid": True},
                        is_a=["solid"])

    print("   Added concepts: cup, water, table")
    print(f"   cup is_a container: {reasoner.is_a('cup', 'container')}")
    print(f"   water is_a liquid: {reasoner.is_a('water', 'liquid')}")
    print()

    # 2. Physical Reasoning
    print("2. PHYSICAL REASONING:")
    print("-" * 40)

    can_support, reason = reasoner.can_support("table", "cup")
    print(f"   Can table support cup? {can_support}")
    print(f"   Reason: {reason}")

    can_contain, reason = reasoner.can_contain("cup", "water")
    print(f"   Can cup contain water? {can_contain}")
    print(f"   Reason: {reason}")

    will_fall, reason = reasoner.predict_fall("cup", is_supported=False)
    print(f"   Will unsupported cup fall? {will_fall}")
    print(f"   Reason: {reason}")
    print()

    # 3. Qualitative Physics
    print("3. QUALITATIVE PHYSICS:")
    print("-" * 40)

    effects = reasoner.qualitative_physics("heat", "water")
    print("   Effects of heating water:")
    for quantity, change in effects.items():
        print(f"     {quantity}: {change.value}")

    effects = reasoner.qualitative_physics("drop", "cup")
    print("   Effects of dropping cup:")
    for quantity, change in effects.items():
        print(f"     {quantity}: {change.value}")
    print()

    # 4. Default Reasoning
    print("4. DEFAULT REASONING:")
    print("-" * 40)

    reasoner.assert_default("birds can fly", confidence=0.9)
    reasoner.add_exception("birds can fly", "penguin")

    can_fly, conf = reasoner.query_belief("birds can fly")
    print(f"   Can birds fly? {can_fly} (confidence: {conf:.2f})")

    can_fly, conf = reasoner.query_belief("birds can fly", {"type": "penguin"})
    print(f"   Can penguins fly? {can_fly} (exception applied)")
    print()

    # 5. Social Reasoning
    print("5. SOCIAL REASONING:")
    print("-" * 40)

    behaviors = reasoner.predict_behavior("person greets me", "me")
    print("   Predicted behaviors when greeted:")
    for behavior, strength in behaviors:
        print(f"     {behavior}: {strength:.2f}")

    emotions = reasoner.infer_emotion("received a gift", "person")
    print("   Emotions from receiving gift:")
    for emotion, prob in emotions:
        print(f"     {emotion}: {prob:.2f}")

    ok, reason = reasoner.check_social_norm("shout loudly", "public library")
    print(f"   Shouting in library OK? {ok}")
    print(f"   Reason: {reason}")
    print()

    # 6. Script Reasoning
    print("6. SCRIPT REASONING:")
    print("-" * 40)

    restaurant_script = reasoner.get_script("restaurant")
    if restaurant_script:
        print(f"   Restaurant script roles: {restaurant_script.roles}")
        print(f"   Number of scenes: {len(restaurant_script.scenes)}")

        # Predict next event
        events = [{"event": "enter"}, {"event": "seat"}]
        next_event = reasoner.predict_next_event(events, restaurant_script)
        if next_event:
            print(f"   After enter → seat, next is: {next_event.get('event')}")
    print()

    # 7. Frame Reasoning
    print("7. FRAME REASONING:")
    print("-" * 40)

    reasoner.create_frame(
        "commercial_transaction",
        slots={"buyer": None, "seller": None, "item": None, "price": None},
        defaults={"currency": "USD", "quantity": 1}
    )

    instance = reasoner.instantiate_frame(
        "commercial_transaction",
        {"buyer": "John", "seller": "Store", "item": "book", "price": 20}
    )
    print("   Transaction frame instance:")
    for key, value in instance.items():
        print(f"     {key}: {value}")
    print()

    # 8. Integrated Reasoning
    print("8. INTEGRATED REASONING:")
    print("-" * 40)

    result = reasoner.reason("What happens when someone drops a cup?")
    print(f"   Query: {result.query}")
    print(f"   Conclusions: {result.conclusions}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Explanation: {result.explanation}")
    print()

    result = reasoner.reason("How would a person feel after receiving praise?")
    print(f"   Query: {result.query}")
    print(f"   Conclusions: {result.conclusions}")
    print(f"   Confidence: {result.confidence:.2f}")
    print()

    # 9. Complex Scenario
    print("9. COMPLEX SCENARIO:")
    print("-" * 40)

    print("   Scenario: Cup of water on table edge")

    # Check support
    supported, _ = reasoner.can_support("table", "cup")
    print(f"   Table can support cup: {supported}")

    # Check containment
    contained, _ = reasoner.can_contain("cup", "water")
    print(f"   Cup can contain water: {contained}")

    # If pushed off...
    print("   If cup is pushed off table:")
    will_fall, reason = reasoner.predict_fall("cup", is_supported=False)
    print(f"     Cup will fall: {will_fall}")

    physics = reasoner.qualitative_physics("drop", "cup")
    print(f"     Height: {physics.get('height', 'unknown')}")
    print(f"     Velocity: {physics.get('velocity', 'unknown')}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Commonsense Reasoner Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
