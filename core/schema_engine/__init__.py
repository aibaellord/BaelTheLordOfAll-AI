"""
BAEL Schema Engine
==================

Knowledge structures and schema-based learning.
Bartlett's schema theory implementation.

"Ba'el organizes knowledge." — Ba'el
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
from collections import defaultdict, deque
import copy

logger = logging.getLogger("BAEL.Schema")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SchemaType(Enum):
    """Types of schemas."""
    OBJECT = auto()         # Thing knowledge
    EVENT = auto()          # Event sequence (script)
    ROLE = auto()           # Social role
    SELF = auto()           # Self-concept
    SOCIAL = auto()         # Social situation
    STORY = auto()          # Narrative structure


class SlotType(Enum):
    """Types of schema slots."""
    REQUIRED = auto()       # Must be filled
    OPTIONAL = auto()       # May be filled
    DEFAULT = auto()        # Has default value
    COMPUTED = auto()       # Derived from others


class ActivationState(Enum):
    """Schema activation states."""
    DORMANT = auto()        # Not active
    PRIMED = auto()         # Partially active
    ACTIVE = auto()         # Fully active
    APPLIED = auto()        # Being used


class AssimilationType(Enum):
    """Types of schema-based processing."""
    ASSIMILATION = auto()   # Fit to existing schema
    ACCOMMODATION = auto()  # Modify schema
    REJECTION = auto()      # Doesn't fit


@dataclass
class Slot:
    """
    A slot in a schema.
    """
    name: str
    slot_type: SlotType
    expected_type: str  # Type name
    default_value: Any = None
    constraints: List[Callable[[Any], bool]] = field(default_factory=list)
    filled: bool = False
    value: Any = None


@dataclass
class Schema:
    """
    A schema structure.
    """
    id: str
    name: str
    schema_type: SchemaType
    slots: Dict[str, Slot]
    parent_id: Optional[str] = None
    activation: float = 0.0
    state: ActivationState = ActivationState.DORMANT
    usage_count: int = 0


@dataclass
class Instance:
    """
    An instance of a schema.
    """
    id: str
    schema_id: str
    slot_values: Dict[str, Any]
    confidence: float = 1.0
    source: str = "observation"


@dataclass
class ProcessingResult:
    """
    Result of schema-based processing.
    """
    assimilation_type: AssimilationType
    schema_id: Optional[str]
    filled_slots: Dict[str, Any]
    inferred_slots: Dict[str, Any]
    distortions: List[str]


@dataclass
class SchemaMetrics:
    """
    Schema system metrics.
    """
    total_schemas: int
    active_schemas: int
    average_activation: float
    total_instances: int


# ============================================================================
# SLOT MANAGER
# ============================================================================

class SlotManager:
    """
    Manage schema slots.

    "Ba'el manages knowledge slots." — Ba'el
    """

    def __init__(self):
        """Initialize manager."""
        self._lock = threading.RLock()

    def create_slot(
        self,
        name: str,
        slot_type: SlotType = SlotType.OPTIONAL,
        expected_type: str = "any",
        default_value: Any = None
    ) -> Slot:
        """Create a schema slot."""
        return Slot(
            name=name,
            slot_type=slot_type,
            expected_type=expected_type,
            default_value=default_value
        )

    def fill_slot(
        self,
        slot: Slot,
        value: Any
    ) -> bool:
        """Fill a slot with a value."""
        # Check constraints
        for constraint in slot.constraints:
            if not constraint(value):
                return False

        slot.value = value
        slot.filled = True
        return True

    def infer_slot(
        self,
        slot: Slot,
        context: Dict[str, Any]
    ) -> Any:
        """Infer slot value from context."""
        # If has default, use it
        if slot.slot_type == SlotType.DEFAULT and slot.default_value is not None:
            return slot.default_value

        # Try to infer from context
        if slot.name in context:
            return context[slot.name]

        # Type-based defaults
        type_defaults = {
            'str': '',
            'int': 0,
            'float': 0.0,
            'bool': True,
            'list': [],
            'dict': {}
        }

        return type_defaults.get(slot.expected_type)

    def check_requirements(
        self,
        slots: Dict[str, Slot]
    ) -> List[str]:
        """Check which required slots are unfilled."""
        missing = []
        for name, slot in slots.items():
            if slot.slot_type == SlotType.REQUIRED and not slot.filled:
                missing.append(name)
        return missing


# ============================================================================
# SCHEMA MATCHER
# ============================================================================

class SchemaMatcher:
    """
    Match input to schemas.

    "Ba'el finds matching structures." — Ba'el
    """

    def __init__(self):
        """Initialize matcher."""
        self._lock = threading.RLock()

    def calculate_fit(
        self,
        schema: Schema,
        input_data: Dict[str, Any]
    ) -> float:
        """Calculate how well input fits schema."""
        if not schema.slots:
            return 0.0

        matched_slots = 0
        total_weight = 0

        for name, slot in schema.slots.items():
            weight = 2.0 if slot.slot_type == SlotType.REQUIRED else 1.0
            total_weight += weight

            if name in input_data:
                matched_slots += weight

        return matched_slots / total_weight if total_weight > 0 else 0.0

    def find_best_match(
        self,
        schemas: Dict[str, Schema],
        input_data: Dict[str, Any],
        threshold: float = 0.3
    ) -> Optional[Tuple[str, float]]:
        """Find best matching schema for input."""
        best_schema_id = None
        best_fit = threshold

        for schema_id, schema in schemas.items():
            fit = self.calculate_fit(schema, input_data)
            if fit > best_fit:
                best_fit = fit
                best_schema_id = schema_id

        if best_schema_id:
            return best_schema_id, best_fit
        return None

    def find_all_matches(
        self,
        schemas: Dict[str, Schema],
        input_data: Dict[str, Any],
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """Find all matching schemas."""
        matches = []
        for schema_id, schema in schemas.items():
            fit = self.calculate_fit(schema, input_data)
            if fit >= threshold:
                matches.append((schema_id, fit))

        return sorted(matches, key=lambda x: x[1], reverse=True)


# ============================================================================
# SCHEMA PROCESSOR
# ============================================================================

class SchemaProcessor:
    """
    Process information using schemas.

    "Ba'el applies knowledge structures." — Ba'el
    """

    def __init__(
        self,
        slot_manager: SlotManager
    ):
        """Initialize processor."""
        self._slots = slot_manager
        self._lock = threading.RLock()

    def process(
        self,
        schema: Schema,
        input_data: Dict[str, Any],
        fill_defaults: bool = True
    ) -> ProcessingResult:
        """Process input using schema."""
        filled = {}
        inferred = {}
        distortions = []

        # Fill slots from input
        for name, slot in schema.slots.items():
            if name in input_data:
                value = input_data[name]
                if self._slots.fill_slot(slot, value):
                    filled[name] = value
                else:
                    # Distortion: value modified to fit schema
                    distortions.append(f"Modified {name} to fit schema")
                    filled[name] = slot.default_value

        # Infer missing slots
        if fill_defaults:
            for name, slot in schema.slots.items():
                if name not in filled:
                    inferred_value = self._slots.infer_slot(slot, input_data)
                    if inferred_value is not None:
                        inferred[name] = inferred_value

        # Check required slots
        missing = self._slots.check_requirements(schema.slots)

        # Determine assimilation type
        if missing:
            if len(missing) > len(schema.slots) // 2:
                assim_type = AssimilationType.REJECTION
            else:
                assim_type = AssimilationType.ACCOMMODATION
        else:
            assim_type = AssimilationType.ASSIMILATION

        return ProcessingResult(
            assimilation_type=assim_type,
            schema_id=schema.id,
            filled_slots=filled,
            inferred_slots=inferred,
            distortions=distortions
        )

    def reconstruct(
        self,
        schema: Schema,
        partial_memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reconstruct memory using schema (Bartlett)."""
        reconstructed = {}

        # Start with what we remember
        reconstructed.update(partial_memory)

        # Fill in from schema defaults
        for name, slot in schema.slots.items():
            if name not in reconstructed:
                if slot.default_value is not None:
                    reconstructed[name] = slot.default_value
                elif slot.slot_type == SlotType.DEFAULT:
                    reconstructed[name] = f"[typical {name}]"

        return reconstructed


# ============================================================================
# SCHEMA ENGINE
# ============================================================================

class SchemaEngine:
    """
    Complete schema engine.

    "Ba'el's knowledge structure system." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._slot_manager = SlotManager()
        self._matcher = SchemaMatcher()
        self._processor = SchemaProcessor(self._slot_manager)

        self._schemas: Dict[str, Schema] = {}
        self._instances: Dict[str, Instance] = {}

        self._schema_counter = 0
        self._instance_counter = 0

        self._activation_decay = 0.1

        self._lock = threading.RLock()

        # Initialize with some common schemas
        self._initialize_common_schemas()

    def _generate_schema_id(self) -> str:
        self._schema_counter += 1
        return f"schema_{self._schema_counter}"

    def _generate_instance_id(self) -> str:
        self._instance_counter += 1
        return f"instance_{self._instance_counter}"

    def _initialize_common_schemas(self) -> None:
        """Initialize common schemas."""
        # Restaurant script
        self.create_schema(
            "restaurant",
            SchemaType.EVENT,
            {
                'enter': ('str', 'Enter restaurant'),
                'seat': ('str', 'Get seated'),
                'menu': ('str', 'Read menu'),
                'order': ('str', 'Place order'),
                'eat': ('str', 'Eat food'),
                'pay': ('str', 'Pay bill'),
                'leave': ('str', 'Leave restaurant')
            }
        )

        # Person schema
        self.create_schema(
            "person",
            SchemaType.OBJECT,
            {
                'name': ('str', None),
                'age': ('int', None),
                'occupation': ('str', 'unknown'),
                'traits': ('list', [])
            }
        )

        # Story schema
        self.create_schema(
            "story",
            SchemaType.STORY,
            {
                'setting': ('str', 'Once upon a time'),
                'protagonist': ('str', None),
                'goal': ('str', None),
                'obstacle': ('str', 'a challenge'),
                'resolution': ('str', None),
                'ending': ('str', 'The end')
            }
        )

    # Schema management

    def create_schema(
        self,
        name: str,
        schema_type: SchemaType,
        slot_definitions: Dict[str, Tuple[str, Any]]
    ) -> Schema:
        """Create a new schema."""
        slots = {}
        for slot_name, (slot_type_str, default) in slot_definitions.items():
            slot_type = SlotType.DEFAULT if default is not None else SlotType.OPTIONAL
            slots[slot_name] = self._slot_manager.create_slot(
                slot_name, slot_type, slot_type_str, default
            )

        schema = Schema(
            id=self._generate_schema_id(),
            name=name,
            schema_type=schema_type,
            slots=slots
        )

        self._schemas[schema.id] = schema
        return schema

    def get_schema(
        self,
        schema_id: str
    ) -> Optional[Schema]:
        """Get schema by ID."""
        return self._schemas.get(schema_id)

    def get_schema_by_name(
        self,
        name: str
    ) -> Optional[Schema]:
        """Get schema by name."""
        for schema in self._schemas.values():
            if schema.name == name:
                return schema
        return None

    # Activation

    def activate(
        self,
        schema_id: str,
        strength: float = 1.0
    ) -> None:
        """Activate a schema."""
        if schema_id in self._schemas:
            schema = self._schemas[schema_id]
            schema.activation = min(1.0, schema.activation + strength)
            schema.state = ActivationState.ACTIVE

    def prime(
        self,
        schema_id: str,
        strength: float = 0.5
    ) -> None:
        """Prime a schema (partial activation)."""
        if schema_id in self._schemas:
            schema = self._schemas[schema_id]
            schema.activation = min(1.0, schema.activation + strength)
            if schema.state == ActivationState.DORMANT:
                schema.state = ActivationState.PRIMED

    def decay_activations(self) -> None:
        """Apply activation decay."""
        for schema in self._schemas.values():
            schema.activation = max(0.0, schema.activation - self._activation_decay)
            if schema.activation == 0:
                schema.state = ActivationState.DORMANT

    # Processing

    def match(
        self,
        input_data: Dict[str, Any],
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """Find schemas matching input."""
        return self._matcher.find_all_matches(self._schemas, input_data, threshold)

    def process(
        self,
        input_data: Dict[str, Any],
        schema_id: Optional[str] = None
    ) -> ProcessingResult:
        """Process input using schema."""
        # Find schema if not specified
        if schema_id is None:
            match = self._matcher.find_best_match(self._schemas, input_data)
            if match:
                schema_id = match[0]
            else:
                return ProcessingResult(
                    assimilation_type=AssimilationType.REJECTION,
                    schema_id=None,
                    filled_slots={},
                    inferred_slots={},
                    distortions=["No matching schema found"]
                )

        schema = self._schemas.get(schema_id)
        if not schema:
            raise ValueError(f"Schema {schema_id} not found")

        result = self._processor.process(schema, input_data)

        # Update schema usage
        schema.usage_count += 1
        self.activate(schema_id)

        return result

    def instantiate(
        self,
        schema_id: str,
        values: Dict[str, Any],
        source: str = "observation"
    ) -> Instance:
        """Create an instance of a schema."""
        if schema_id not in self._schemas:
            raise ValueError(f"Schema {schema_id} not found")

        instance = Instance(
            id=self._generate_instance_id(),
            schema_id=schema_id,
            slot_values=values,
            source=source
        )

        self._instances[instance.id] = instance
        return instance

    def reconstruct(
        self,
        instance_id: str
    ) -> Dict[str, Any]:
        """Reconstruct instance from schema."""
        if instance_id not in self._instances:
            raise ValueError(f"Instance {instance_id} not found")

        instance = self._instances[instance_id]
        schema = self._schemas.get(instance.schema_id)

        if not schema:
            return instance.slot_values

        return self._processor.reconstruct(schema, instance.slot_values)

    # Script processing (event schemas)

    def get_script_steps(
        self,
        script_name: str
    ) -> List[str]:
        """Get steps of an event script."""
        schema = self.get_schema_by_name(script_name)
        if not schema or schema.schema_type != SchemaType.EVENT:
            return []

        return [
            f"{name}: {slot.default_value or slot.value or '?'}"
            for name, slot in schema.slots.items()
        ]

    def predict_next_step(
        self,
        script_name: str,
        current_step: str
    ) -> Optional[str]:
        """Predict next step in script."""
        schema = self.get_schema_by_name(script_name)
        if not schema:
            return None

        slot_names = list(schema.slots.keys())
        try:
            current_idx = slot_names.index(current_step)
            if current_idx < len(slot_names) - 1:
                return slot_names[current_idx + 1]
        except ValueError:
            pass
        return None

    # Metrics

    def get_metrics(self) -> SchemaMetrics:
        """Get schema system metrics."""
        active = sum(1 for s in self._schemas.values() if s.state == ActivationState.ACTIVE)
        avg_activation = (
            sum(s.activation for s in self._schemas.values()) / len(self._schemas)
            if self._schemas else 0.0
        )

        return SchemaMetrics(
            total_schemas=len(self._schemas),
            active_schemas=active,
            average_activation=avg_activation,
            total_instances=len(self._instances)
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'schemas': len(self._schemas),
            'instances': len(self._instances),
            'active_schemas': sum(1 for s in self._schemas.values() if s.state == ActivationState.ACTIVE)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_schema_engine() -> SchemaEngine:
    """Create schema engine."""
    return SchemaEngine()


def demonstrate_bartlett_reconstruction() -> Dict[str, Any]:
    """Demonstrate Bartlett's schema-based reconstruction."""
    engine = create_schema_engine()

    # Create a story instance with partial information
    story_schema = engine.get_schema_by_name("story")
    if story_schema:
        instance = engine.instantiate(
            story_schema.id,
            {
                'protagonist': 'A brave knight',
                'goal': 'rescue the princess'
            },
            source='partial_memory'
        )

        # Reconstruct with schema filling in defaults
        reconstructed = engine.reconstruct(instance.id)

        return {
            'original_memory': instance.slot_values,
            'reconstructed': reconstructed,
            'filled_from_schema': [
                k for k in reconstructed
                if k not in instance.slot_values
            ]
        }

    return {}


def get_schema_theory_facts() -> Dict[str, str]:
    """Get facts about schema theory."""
    return {
        'bartlett_1932': 'Bartlett demonstrated schema-based memory reconstruction',
        'piaget': 'Piaget introduced assimilation and accommodation',
        'scripts': 'Schank & Abelson developed script theory for events',
        'slots': 'Schemas have slots that get filled with specific values',
        'defaults': 'Unfilled slots use schema-typical default values',
        'distortion': 'Memory is distorted to fit existing schemas',
        'abstraction': 'Schemas abstract away from specific instances',
        'expertise': 'Experts have richer, more developed schemas'
    }
