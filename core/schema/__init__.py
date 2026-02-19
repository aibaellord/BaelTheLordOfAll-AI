"""
BAEL Schema Engine
===================

Schema theory for knowledge organization.
Scripts, frames, and structured knowledge.

"Ba'el organizes knowledge through schemas." — Ba'el
"""

import logging
import threading
import time
import math
import random
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict
import copy

logger = logging.getLogger("BAEL.Schema")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SchemaType(Enum):
    """Types of schemas."""
    OBJECT = auto()       # Object schemas
    EVENT = auto()        # Event schemas (scripts)
    SCENE = auto()        # Scene/situation schemas
    PERSON = auto()        # Person schemas
    ROLE = auto()          # Role schemas
    STORY = auto()         # Narrative schemas
    ABSTRACT = auto()      # Abstract concept schemas


class SlotType(Enum):
    """Types of schema slots."""
    REQUIRED = auto()      # Must be filled
    OPTIONAL = auto()      # May be filled
    DEFAULT = auto()       # Has default value
    DERIVED = auto()       # Computed from other slots
    CONSTRAINT = auto()    # Constrained values


class ActivationLevel(Enum):
    """Schema activation levels."""
    DORMANT = auto()
    PRIMED = auto()
    ACTIVE = auto()
    FOCAL = auto()


@dataclass
class Slot:
    """
    A slot in a schema.
    """
    name: str
    slot_type: SlotType
    default_value: Any = None
    constraints: List[Any] = field(default_factory=list)
    filler: Any = None
    confidence: float = 0.0

    @property
    def is_filled(self) -> bool:
        return self.filler is not None

    def fill(self, value: Any, confidence: float = 1.0) -> bool:
        """Fill slot with value."""
        if self.constraints:
            if value not in self.constraints:
                return False

        self.filler = value
        self.confidence = confidence
        return True


@dataclass
class Schema:
    """
    A cognitive schema.
    """
    id: str
    name: str
    schema_type: SchemaType
    slots: Dict[str, Slot]
    parent: Optional[str] = None  # Inheritance
    children: List[str] = field(default_factory=list)
    activation: float = 0.0
    access_count: int = 0
    creation_time: float = field(default_factory=time.time)

    @property
    def level(self) -> ActivationLevel:
        if self.activation < 0.1:
            return ActivationLevel.DORMANT
        elif self.activation < 0.4:
            return ActivationLevel.PRIMED
        elif self.activation < 0.8:
            return ActivationLevel.ACTIVE
        else:
            return ActivationLevel.FOCAL

    def get_slot(self, name: str) -> Optional[Slot]:
        return self.slots.get(name)

    def fill_slot(
        self,
        slot_name: str,
        value: Any,
        confidence: float = 1.0
    ) -> bool:
        """Fill a slot."""
        slot = self.slots.get(slot_name)
        if slot:
            return slot.fill(value, confidence)
        return False

    def get_filled_slots(self) -> Dict[str, Any]:
        """Get all filled slots."""
        return {
            name: slot.filler
            for name, slot in self.slots.items()
            if slot.is_filled
        }

    def get_unfilled_required(self) -> List[str]:
        """Get unfilled required slots."""
        return [
            name for name, slot in self.slots.items()
            if slot.slot_type == SlotType.REQUIRED and not slot.is_filled
        ]

    def completion_ratio(self) -> float:
        """Calculate slot completion ratio."""
        if not self.slots:
            return 1.0

        filled = sum(1 for s in self.slots.values() if s.is_filled)
        return filled / len(self.slots)


@dataclass
class Script:
    """
    A script (event schema) with sequences.
    """
    id: str
    name: str
    scenes: List[Dict[str, Any]]
    entry_conditions: Dict[str, Any]
    roles: List[str]
    props: List[str]
    current_scene: int = 0

    def advance(self) -> Optional[Dict]:
        """Advance to next scene."""
        if self.current_scene < len(self.scenes) - 1:
            self.current_scene += 1
            return self.scenes[self.current_scene]
        return None

    def reset(self) -> None:
        """Reset script."""
        self.current_scene = 0

    @property
    def current(self) -> Optional[Dict]:
        if 0 <= self.current_scene < len(self.scenes):
            return self.scenes[self.current_scene]
        return None


@dataclass
class Frame:
    """
    A frame (situation representation).
    """
    id: str
    name: str
    slots: Dict[str, Slot]
    relations: Dict[str, str]  # slot -> relation type
    constraints: List[str]
    default_inferences: List[str]


# ============================================================================
# SCHEMA LIBRARY
# ============================================================================

class SchemaLibrary:
    """
    Library of schemas.

    "Ba'el's schema library." — Ba'el
    """

    def __init__(self):
        """Initialize library."""
        self._schemas: Dict[str, Schema] = {}
        self._scripts: Dict[str, Script] = {}
        self._frames: Dict[str, Frame] = {}
        self._type_index: Dict[SchemaType, List[str]] = defaultdict(list)
        self._schema_counter = 0
        self._lock = threading.RLock()

    def _generate_id(self) -> str:
        self._schema_counter += 1
        return f"schema_{self._schema_counter}"

    def create_schema(
        self,
        name: str,
        schema_type: SchemaType,
        slots: Dict[str, Tuple[SlotType, Any]] = None,
        parent: Optional[str] = None
    ) -> Schema:
        """Create new schema."""
        with self._lock:
            # Build slots
            schema_slots = {}
            if slots:
                for slot_name, (slot_type, default) in slots.items():
                    schema_slots[slot_name] = Slot(
                        name=slot_name,
                        slot_type=slot_type,
                        default_value=default
                    )

            # Inherit parent slots
            if parent and parent in self._schemas:
                parent_schema = self._schemas[parent]
                for slot_name, slot in parent_schema.slots.items():
                    if slot_name not in schema_slots:
                        schema_slots[slot_name] = copy.deepcopy(slot)

            schema = Schema(
                id=self._generate_id(),
                name=name,
                schema_type=schema_type,
                slots=schema_slots,
                parent=parent
            )

            self._schemas[schema.id] = schema
            self._type_index[schema_type].append(schema.id)

            # Update parent
            if parent and parent in self._schemas:
                self._schemas[parent].children.append(schema.id)

            return schema

    def create_script(
        self,
        name: str,
        scenes: List[Dict[str, Any]],
        roles: List[str] = None,
        props: List[str] = None,
        entry_conditions: Dict[str, Any] = None
    ) -> Script:
        """Create event script."""
        with self._lock:
            script = Script(
                id=f"script_{len(self._scripts)}",
                name=name,
                scenes=scenes,
                entry_conditions=entry_conditions or {},
                roles=roles or [],
                props=props or []
            )

            self._scripts[script.id] = script
            return script

    def create_frame(
        self,
        name: str,
        slots: Dict[str, Tuple[SlotType, Any]],
        relations: Dict[str, str] = None,
        constraints: List[str] = None
    ) -> Frame:
        """Create situation frame."""
        with self._lock:
            frame_slots = {}
            for slot_name, (slot_type, default) in slots.items():
                frame_slots[slot_name] = Slot(
                    name=slot_name,
                    slot_type=slot_type,
                    default_value=default
                )

            frame = Frame(
                id=f"frame_{len(self._frames)}",
                name=name,
                slots=frame_slots,
                relations=relations or {},
                constraints=constraints or [],
                default_inferences=[]
            )

            self._frames[frame.id] = frame
            return frame

    def get_schema(self, schema_id: str) -> Optional[Schema]:
        """Get schema by ID."""
        return self._schemas.get(schema_id)

    def get_by_name(self, name: str) -> Optional[Schema]:
        """Get schema by name."""
        for schema in self._schemas.values():
            if schema.name == name:
                return schema
        return None

    def get_by_type(self, schema_type: SchemaType) -> List[Schema]:
        """Get schemas by type."""
        schema_ids = self._type_index.get(schema_type, [])
        return [self._schemas[sid] for sid in schema_ids if sid in self._schemas]

    @property
    def schemas(self) -> List[Schema]:
        return list(self._schemas.values())

    @property
    def scripts(self) -> List[Script]:
        return list(self._scripts.values())

    @property
    def frames(self) -> List[Frame]:
        return list(self._frames.values())


# ============================================================================
# SCHEMA MATCHER
# ============================================================================

class SchemaMatcher:
    """
    Match input to schemas.

    "Ba'el matches patterns to schemas." — Ba'el
    """

    def __init__(self, library: SchemaLibrary):
        """Initialize matcher."""
        self._library = library
        self._lock = threading.RLock()

    def match(
        self,
        input_data: Dict[str, Any],
        schema_type: Optional[SchemaType] = None,
        threshold: float = 0.3
    ) -> List[Tuple[Schema, float]]:
        """Match input to schemas."""
        with self._lock:
            matches = []

            candidates = (
                self._library.get_by_type(schema_type)
                if schema_type
                else self._library.schemas
            )

            for schema in candidates:
                score = self._compute_match_score(input_data, schema)
                if score >= threshold:
                    matches.append((schema, score))

            # Sort by score
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches

    def _compute_match_score(
        self,
        input_data: Dict[str, Any],
        schema: Schema
    ) -> float:
        """Compute match score."""
        if not schema.slots:
            return 0.0

        matched = 0
        total = 0

        for slot_name, slot in schema.slots.items():
            total += 1

            if slot_name in input_data:
                # Check value match
                input_value = input_data[slot_name]

                if slot.default_value is not None:
                    if input_value == slot.default_value:
                        matched += 1.0
                    elif slot.constraints and input_value in slot.constraints:
                        matched += 0.8
                    else:
                        matched += 0.5  # Slot name match
                else:
                    matched += 0.7  # Slot name match without default

        return matched / total if total > 0 else 0.0

    def instantiate(
        self,
        schema: Schema,
        input_data: Dict[str, Any]
    ) -> Schema:
        """Instantiate schema with input data."""
        with self._lock:
            # Create copy
            instance = copy.deepcopy(schema)
            instance.id = f"{schema.id}_instance_{time.time()}"

            # Fill slots
            for slot_name, value in input_data.items():
                instance.fill_slot(slot_name, value)

            # Fill defaults
            for slot in instance.slots.values():
                if not slot.is_filled and slot.default_value is not None:
                    slot.fill(slot.default_value, confidence=0.5)

            return instance


# ============================================================================
# SCRIPT PROCESSOR
# ============================================================================

class ScriptProcessor:
    """
    Process event scripts.

    "Ba'el follows scripts." — Ba'el
    """

    def __init__(self, library: SchemaLibrary):
        """Initialize processor."""
        self._library = library
        self._active_scripts: Dict[str, Tuple[Script, Dict]] = {}
        self._lock = threading.RLock()

    def activate_script(
        self,
        script_id: str,
        bindings: Dict[str, Any] = None
    ) -> bool:
        """Activate script with role bindings."""
        with self._lock:
            script = self._library._scripts.get(script_id)
            if not script:
                return False

            # Check entry conditions
            if script.entry_conditions:
                for condition, required in script.entry_conditions.items():
                    if bindings and condition in bindings:
                        if bindings[condition] != required:
                            return False

            # Activate
            active_script = copy.deepcopy(script)
            active_script.reset()

            self._active_scripts[script_id] = (active_script, bindings or {})
            return True

    def get_current_scene(
        self,
        script_id: str
    ) -> Optional[Dict]:
        """Get current scene with bindings applied."""
        with self._lock:
            if script_id not in self._active_scripts:
                return None

            script, bindings = self._active_scripts[script_id]
            scene = script.current

            if scene:
                # Apply bindings
                bound_scene = {}
                for key, value in scene.items():
                    if isinstance(value, str) and value.startswith("$"):
                        # Variable reference
                        var_name = value[1:]
                        bound_scene[key] = bindings.get(var_name, value)
                    else:
                        bound_scene[key] = value
                return bound_scene

            return None

    def advance_script(self, script_id: str) -> Optional[Dict]:
        """Advance to next scene."""
        with self._lock:
            if script_id not in self._active_scripts:
                return None

            script, _ = self._active_scripts[script_id]
            return script.advance()

    def predict_next(self, script_id: str) -> Optional[Dict]:
        """Predict next scene without advancing."""
        with self._lock:
            if script_id not in self._active_scripts:
                return None

            script, bindings = self._active_scripts[script_id]

            if script.current_scene < len(script.scenes) - 1:
                next_scene = script.scenes[script.current_scene + 1]

                # Apply bindings
                bound_scene = {}
                for key, value in next_scene.items():
                    if isinstance(value, str) and value.startswith("$"):
                        var_name = value[1:]
                        bound_scene[key] = bindings.get(var_name, value)
                    else:
                        bound_scene[key] = value
                return bound_scene

            return None

    def deactivate_script(self, script_id: str) -> None:
        """Deactivate script."""
        with self._lock:
            if script_id in self._active_scripts:
                del self._active_scripts[script_id]


# ============================================================================
# SCHEMA ENGINE
# ============================================================================

class SchemaEngine:
    """
    Complete schema theory implementation.

    "Ba'el's schema-based cognition." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._library = SchemaLibrary()
        self._matcher = SchemaMatcher(self._library)
        self._script_processor = ScriptProcessor(self._library)
        self._active_schemas: Dict[str, Schema] = {}
        self._lock = threading.RLock()

    # Schema operations

    def create_schema(
        self,
        name: str,
        schema_type: SchemaType,
        slots: Dict[str, Tuple[SlotType, Any]] = None,
        parent: Optional[str] = None
    ) -> Schema:
        """Create schema."""
        return self._library.create_schema(name, schema_type, slots, parent)

    def create_object_schema(
        self,
        name: str,
        attributes: Dict[str, Any]
    ) -> Schema:
        """Create object schema."""
        slots = {
            attr: (SlotType.DEFAULT, value)
            for attr, value in attributes.items()
        }
        return self.create_schema(name, SchemaType.OBJECT, slots)

    def create_event_schema(
        self,
        name: str,
        roles: List[str],
        sequence: List[str]
    ) -> Script:
        """Create event schema (script)."""
        scenes = [{"action": action} for action in sequence]
        return self._library.create_script(name, scenes, roles)

    # Matching

    def match(
        self,
        input_data: Dict[str, Any],
        schema_type: Optional[SchemaType] = None
    ) -> List[Tuple[Schema, float]]:
        """Match input to schemas."""
        return self._matcher.match(input_data, schema_type)

    def best_match(
        self,
        input_data: Dict[str, Any]
    ) -> Optional[Schema]:
        """Get best matching schema."""
        matches = self.match(input_data)
        if matches:
            return matches[0][0]
        return None

    def instantiate(
        self,
        schema_name: str,
        data: Dict[str, Any]
    ) -> Optional[Schema]:
        """Instantiate schema."""
        schema = self._library.get_by_name(schema_name)
        if schema:
            instance = self._matcher.instantiate(schema, data)
            self._active_schemas[instance.id] = instance
            return instance
        return None

    # Script operations

    def activate_script(
        self,
        script_name: str,
        bindings: Dict[str, Any] = None
    ) -> bool:
        """Activate script."""
        for script in self._library.scripts:
            if script.name == script_name:
                return self._script_processor.activate_script(script.id, bindings)
        return False

    def predict_next_action(self, script_name: str) -> Optional[Dict]:
        """Predict next action in script."""
        for script in self._library.scripts:
            if script.name == script_name:
                return self._script_processor.predict_next(script.id)
        return None

    def advance_script(self, script_name: str) -> Optional[Dict]:
        """Advance script."""
        for script in self._library.scripts:
            if script.name == script_name:
                return self._script_processor.advance_script(script.id)
        return None

    # Inference

    def infer_missing(self, schema: Schema) -> Dict[str, Any]:
        """Infer missing slot values."""
        with self._lock:
            inferences = {}

            for slot_name, slot in schema.slots.items():
                if not slot.is_filled:
                    # Try default
                    if slot.default_value is not None:
                        inferences[slot_name] = slot.default_value
                    # Try parent inheritance
                    elif schema.parent:
                        parent = self._library.get_schema(schema.parent)
                        if parent:
                            parent_slot = parent.get_slot(slot_name)
                            if parent_slot and parent_slot.is_filled:
                                inferences[slot_name] = parent_slot.filler

            return inferences

    @property
    def library(self) -> SchemaLibrary:
        return self._library

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'schemas': len(self._library.schemas),
            'scripts': len(self._library.scripts),
            'frames': len(self._library.frames),
            'active_schemas': len(self._active_schemas),
            'active_scripts': len(self._script_processor._active_scripts)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_schema_engine() -> SchemaEngine:
    """Create schema engine."""
    return SchemaEngine()


def create_schema(
    name: str,
    schema_type: SchemaType,
    slots: Dict[str, Tuple[SlotType, Any]] = None
) -> Schema:
    """Create standalone schema."""
    schema_slots = {}
    if slots:
        for slot_name, (slot_type, default) in slots.items():
            schema_slots[slot_name] = Slot(
                name=slot_name,
                slot_type=slot_type,
                default_value=default
            )

    return Schema(
        id=f"schema_{random.randint(1000, 9999)}",
        name=name,
        schema_type=schema_type,
        slots=schema_slots
    )


def create_script(
    name: str,
    scenes: List[Dict[str, Any]],
    roles: List[str] = None
) -> Script:
    """Create standalone script."""
    return Script(
        id=f"script_{random.randint(1000, 9999)}",
        name=name,
        scenes=scenes,
        entry_conditions={},
        roles=roles or [],
        props=[]
    )
