"""
BAEL Schema Activation Engine
================================

Knowledge structures guide memory.
Bartlett's schema theory.

"Ba'el's templates shape understanding." — Ba'el
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

logger = logging.getLogger("BAEL.SchemaActivation")


T = TypeVar('T')


# ============================================================================
# CORE TYPES
# ============================================================================

class SchemaType(Enum):
    """Type of schema."""
    EVENT = auto()       # Scripts (restaurant, doctor)
    PERSON = auto()      # Stereotypes, traits
    OBJECT = auto()      # Object categories
    SPATIAL = auto()     # Place schemas
    SELF = auto()        # Self-schemas
    ROLE = auto()        # Social roles


class SchemaMatch(Enum):
    """Match to schema."""
    TYPICAL = auto()        # Matches schema
    ATYPICAL = auto()       # Violates schema
    IRRELEVANT = auto()     # Unrelated


class ProcessingMode(Enum):
    """Schema processing mode."""
    TOP_DOWN = auto()       # Schema guides perception
    BOTTOM_UP = auto()      # Data drives perception
    INTERACTIVE = auto()    # Both


@dataclass
class SchemaNode:
    """
    A node in a schema.
    """
    id: str
    name: str
    typicality: float      # 0-1
    slots: Dict[str, Any]
    defaults: Dict[str, Any]


@dataclass
class Schema:
    """
    A schema knowledge structure.
    """
    id: str
    name: str
    schema_type: SchemaType
    nodes: List[SchemaNode]
    activation: float = 0.0
    usage_count: int = 0


@dataclass
class MemoryEvent:
    """
    An event to be remembered.
    """
    id: str
    content: str
    details: Dict[str, Any]
    schema_match: SchemaMatch
    relevant_schema_id: Optional[str] = None


@dataclass
class RetrievalResult:
    """
    Schema-influenced retrieval.
    """
    event_id: str
    recalled_details: Dict[str, Any]
    intrusions: List[str]      # Schema-consistent false memories
    accurate_atypical: List[str]  # Atypical details remembered


@dataclass
class SchemaMetrics:
    """
    Schema activation metrics.
    """
    typical_recall: float
    atypical_recall: float
    intrusion_rate: float
    gist_preservation: float


# ============================================================================
# SCHEMA MODEL
# ============================================================================

class SchemaModel:
    """
    Bartlett's schema theory model.

    "Ba'el's knowledge templates." — Ba'el
    """

    def __init__(self):
        """Initialize model."""
        # Schema influence parameters
        self._schema_activation_base = 0.5
        self._activation_decay = 0.1
        self._spreading_rate = 0.3

        # Memory parameters
        self._typical_advantage = 0.2
        self._atypical_advantage = 0.15  # Von Restorff for atypical
        self._intrusion_rate = 0.15

        # Threshold for remembering
        self._recall_threshold = 0.4

        self._lock = threading.RLock()

    def calculate_activation(
        self,
        schema: Schema,
        cue_match: float
    ) -> float:
        """Calculate schema activation from cue."""
        activation = self._schema_activation_base
        activation += cue_match * self._spreading_rate
        activation *= (1 - self._activation_decay * (1 - schema.activation))

        return max(0, min(1, activation))

    def process_encoding(
        self,
        event: MemoryEvent,
        active_schema: Schema
    ) -> float:
        """Calculate encoding strength."""
        base_strength = 0.5

        if event.schema_match == SchemaMatch.TYPICAL:
            # Typical items encoded with schema
            strength = base_strength + self._typical_advantage
        elif event.schema_match == SchemaMatch.ATYPICAL:
            # Atypical items get special attention
            strength = base_strength + self._atypical_advantage
        else:
            # Irrelevant items weakly encoded
            strength = base_strength * 0.5

        # Schema activation boosts encoding
        strength *= (0.8 + 0.4 * active_schema.activation)

        return max(0, min(1, strength))

    def should_intrude(
        self,
        schema: Schema,
        detail: str
    ) -> bool:
        """Check if schema-consistent detail intrudes."""
        if random.random() < self._intrusion_rate * schema.activation:
            return True
        return False

    def calculate_recall(
        self,
        encoding_strength: float,
        retention_interval: float
    ) -> float:
        """Calculate recall probability."""
        # Forgetting over time
        decay = math.exp(-retention_interval * 0.1)

        return encoding_strength * decay


# ============================================================================
# SCHEMA SYSTEM
# ============================================================================

class SchemaSystem:
    """
    Schema activation system.

    "Ba'el's knowledge structure." — Ba'el
    """

    def __init__(self):
        """Initialize system."""
        self._model = SchemaModel()

        self._schemas: Dict[str, Schema] = {}
        self._events: Dict[str, MemoryEvent] = {}
        self._encodings: Dict[str, float] = {}  # event_id -> strength

        self._counter = 0
        self._lock = threading.RLock()

        # Create default schemas
        self._create_default_schemas()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"item_{self._counter}"

    def _create_default_schemas(self):
        """Create default schemas."""
        # Restaurant schema
        restaurant = Schema(
            id="restaurant",
            name="Restaurant Visit",
            schema_type=SchemaType.EVENT,
            nodes=[
                SchemaNode(
                    id="enter",
                    name="Enter restaurant",
                    typicality=0.9,
                    slots={"action": "entering"},
                    defaults={"greeted": True}
                ),
                SchemaNode(
                    id="seated",
                    name="Get seated",
                    typicality=0.85,
                    slots={"action": "sitting"},
                    defaults={"menu_given": True}
                ),
                SchemaNode(
                    id="order",
                    name="Order food",
                    typicality=0.95,
                    slots={"action": "ordering"},
                    defaults={"waiter": True}
                ),
                SchemaNode(
                    id="eat",
                    name="Eat food",
                    typicality=0.95,
                    slots={"action": "eating"},
                    defaults={}
                ),
                SchemaNode(
                    id="pay",
                    name="Pay bill",
                    typicality=0.9,
                    slots={"action": "paying"},
                    defaults={"tip": True}
                )
            ],
            activation=0.5
        )
        self._schemas["restaurant"] = restaurant

        # Office schema
        office = Schema(
            id="office",
            name="Office Environment",
            schema_type=SchemaType.SPATIAL,
            nodes=[
                SchemaNode(
                    id="desk",
                    name="Desk",
                    typicality=0.95,
                    slots={"object": "desk"},
                    defaults={"has_computer": True}
                ),
                SchemaNode(
                    id="chair",
                    name="Chair",
                    typicality=0.9,
                    slots={"object": "chair"},
                    defaults={}
                ),
                SchemaNode(
                    id="computer",
                    name="Computer",
                    typicality=0.85,
                    slots={"object": "computer"},
                    defaults={}
                )
            ],
            activation=0.5
        )
        self._schemas["office"] = office

    def create_schema(
        self,
        name: str,
        schema_type: SchemaType,
        typical_elements: List[str]
    ) -> Schema:
        """Create a new schema."""
        schema_id = self._generate_id()

        nodes = []
        for elem in typical_elements:
            node = SchemaNode(
                id=self._generate_id(),
                name=elem,
                typicality=random.uniform(0.7, 0.95),
                slots={"element": elem},
                defaults={}
            )
            nodes.append(node)

        schema = Schema(
            id=schema_id,
            name=name,
            schema_type=schema_type,
            nodes=nodes,
            activation=0.5
        )

        self._schemas[schema_id] = schema

        return schema

    def activate_schema(
        self,
        schema_id: str,
        cue_match: float = 0.7
    ) -> float:
        """Activate a schema."""
        schema = self._schemas.get(schema_id)
        if not schema:
            return 0.0

        activation = self._model.calculate_activation(schema, cue_match)
        schema.activation = activation
        schema.usage_count += 1

        return activation

    def encode_event(
        self,
        content: str,
        details: Dict[str, Any],
        schema_id: str,
        match: SchemaMatch = SchemaMatch.TYPICAL
    ) -> MemoryEvent:
        """Encode an event with schema."""
        schema = self._schemas.get(schema_id)
        if not schema:
            match = SchemaMatch.IRRELEVANT

        event = MemoryEvent(
            id=self._generate_id(),
            content=content,
            details=details,
            schema_match=match,
            relevant_schema_id=schema_id
        )

        self._events[event.id] = event

        if schema:
            strength = self._model.process_encoding(event, schema)
        else:
            strength = 0.4

        self._encodings[event.id] = strength

        return event

    def retrieve_event(
        self,
        event_id: str,
        retention_interval: float = 1.0
    ) -> Optional[RetrievalResult]:
        """Retrieve an event."""
        event = self._events.get(event_id)
        if not event:
            return None

        encoding_strength = self._encodings.get(event_id, 0.5)
        recall_prob = self._model.calculate_recall(encoding_strength, retention_interval)

        recalled = {}
        intrusions = []
        accurate_atypical = []

        schema = self._schemas.get(event.relevant_schema_id)

        for key, value in event.details.items():
            # Try to recall each detail
            if random.random() < recall_prob:
                recalled[key] = value

                # Track atypical items recalled
                if event.schema_match == SchemaMatch.ATYPICAL:
                    accurate_atypical.append(key)

        # Add schema-consistent intrusions
        if schema:
            for node in schema.nodes:
                if node.name not in event.details:
                    if self._model.should_intrude(schema, node.name):
                        intrusions.append(node.name)

        return RetrievalResult(
            event_id=event_id,
            recalled_details=recalled,
            intrusions=intrusions,
            accurate_atypical=accurate_atypical
        )


# ============================================================================
# SCHEMA PARADIGM
# ============================================================================

class SchemaParadigm:
    """
    Schema experimental paradigm.

    "Ba'el's knowledge template study." — Ba'el
    """

    def __init__(self):
        """Initialize paradigm."""
        self._lock = threading.RLock()

    def run_bartlett_paradigm(
        self,
        n_typical: int = 10,
        n_atypical: int = 5
    ) -> Dict[str, Any]:
        """Run Bartlett-style paradigm."""
        system = SchemaSystem()

        # Activate restaurant schema
        system.activate_schema("restaurant", 0.8)

        # Encode typical events
        typical_events = []
        for i in range(n_typical):
            event = system.encode_event(
                f"typical_event_{i}",
                {"action": f"action_{i}", "typical": True},
                "restaurant",
                SchemaMatch.TYPICAL
            )
            typical_events.append(event)

        # Encode atypical events
        atypical_events = []
        for i in range(n_atypical):
            event = system.encode_event(
                f"atypical_event_{i}",
                {"action": f"unusual_{i}", "atypical": True},
                "restaurant",
                SchemaMatch.ATYPICAL
            )
            atypical_events.append(event)

        # Test recall
        typical_recalled = 0
        atypical_recalled = 0
        total_intrusions = 0

        for event in typical_events:
            result = system.retrieve_event(event.id, 1.0)
            if result and result.recalled_details:
                typical_recalled += 1
            if result:
                total_intrusions += len(result.intrusions)

        for event in atypical_events:
            result = system.retrieve_event(event.id, 1.0)
            if result and result.recalled_details:
                atypical_recalled += 1

        return {
            'typical_recall': typical_recalled / n_typical,
            'atypical_recall': atypical_recalled / n_atypical,
            'intrusion_rate': total_intrusions / (n_typical + n_atypical),
            'interpretation': 'Schema-consistent info shows intrusions; atypical items often well-remembered'
        }

    def run_serial_reproduction(
        self,
        n_reproductions: int = 5
    ) -> Dict[str, Any]:
        """Run serial reproduction (Bartlett's chain)."""
        system = SchemaSystem()
        system.activate_schema("restaurant", 0.8)

        # Original story with typical and atypical elements
        original = {
            "entered": True,         # Typical
            "greeted": True,         # Typical
            "sat_at_bar": True,      # Atypical for formal restaurant
            "ordered": True,         # Typical
            "food_was_cold": True,   # Atypical
            "paid": True,            # Typical
            "left_no_tip": True      # Atypical
        }

        current = original.copy()
        reproduction_chain = [current]

        for rep in range(n_reproductions):
            # Encode current version
            event = system.encode_event(
                f"story_rep_{rep}",
                current,
                "restaurant",
                SchemaMatch.TYPICAL
            )

            # Retrieve (simulating recall by next person)
            result = system.retrieve_event(event.id, 1.5)

            if result:
                # Next version is what was recalled + intrusions
                new_version = result.recalled_details.copy()

                # Add intrusions as "recalled"
                for intrusion in result.intrusions:
                    new_version[intrusion] = True

                current = new_version
                reproduction_chain.append(current)

        # Calculate changes
        final = reproduction_chain[-1] if reproduction_chain else {}
        original_kept = sum(1 for k in original if k in final)

        return {
            'original_details': len(original),
            'final_details': len(final),
            'original_preserved': original_kept,
            'preservation_rate': original_kept / len(original),
            'chain': reproduction_chain,
            'interpretation': 'Story becomes schema-consistent over reproductions'
        }

    def run_office_scene_study(
        self
    ) -> Dict[str, Any]:
        """Run Brewer & Treyens office scene study."""
        system = SchemaSystem()
        system.activate_schema("office", 0.9)

        # Items in the office
        present_typical = ["desk", "chair", "computer"]
        present_atypical = ["skull", "picnic_basket"]  # Not typical
        absent_typical = ["books", "filing_cabinet"]   # Expected but absent

        # Encode what's present
        for item in present_typical:
            system.encode_event(
                item,
                {"object": item, "present": True},
                "office",
                SchemaMatch.TYPICAL
            )

        for item in present_atypical:
            system.encode_event(
                item,
                {"object": item, "present": True},
                "office",
                SchemaMatch.ATYPICAL
            )

        # Test memory
        false_alarms = 0  # Recall absent typical items

        # Check if absent typical items are "remembered"
        # (intrusions in new retrieval)
        test_event = system.encode_event(
            "test_recall",
            {},
            "office",
            SchemaMatch.TYPICAL
        )
        result = system.retrieve_event(test_event.id, 1.0)

        if result:
            for absent in absent_typical:
                if absent in result.intrusions:
                    false_alarms += 1

        return {
            'present_typical': present_typical,
            'present_atypical': present_atypical,
            'absent_typical': absent_typical,
            'false_alarms': false_alarms,
            'interpretation': 'People often "remember" schema-consistent items that were absent'
        }

    def run_schema_activation_levels(
        self
    ) -> Dict[str, Any]:
        """Study effect of schema activation levels."""
        activation_levels = [0.2, 0.5, 0.8]
        results = {}

        for level in activation_levels:
            system = SchemaSystem()
            system._schemas["restaurant"].activation = level

            # Encode events
            events = []
            for i in range(10):
                event = system.encode_event(
                    f"event_{i}",
                    {"detail": f"detail_{i}"},
                    "restaurant",
                    SchemaMatch.TYPICAL
                )
                events.append(event)

            # Count intrusions
            intrusions = 0
            for event in events:
                result = system.retrieve_event(event.id, 1.0)
                if result:
                    intrusions += len(result.intrusions)

            results[f"activation_{level}"] = {
                'intrusion_count': intrusions,
                'intrusions_per_event': intrusions / 10
            }

        return {
            'by_activation': results,
            'interpretation': 'Higher schema activation leads to more intrusions'
        }


# ============================================================================
# SCHEMA ENGINE
# ============================================================================

class SchemaActivationEngine:
    """
    Complete schema activation engine.

    "Ba'el's knowledge template engine." — Ba'el
    """

    def __init__(self):
        """Initialize engine."""
        self._paradigm = SchemaParadigm()
        self._system = SchemaSystem()

        self._experiment_results: List[Dict] = []

        self._lock = threading.RLock()

    # Schema management

    def create_schema(
        self,
        name: str,
        schema_type: SchemaType,
        elements: List[str]
    ) -> Schema:
        """Create schema."""
        return self._system.create_schema(name, schema_type, elements)

    def activate(
        self,
        schema_id: str,
        strength: float = 0.7
    ) -> float:
        """Activate schema."""
        return self._system.activate_schema(schema_id, strength)

    def encode(
        self,
        content: str,
        details: Dict[str, Any],
        schema_id: str,
        match: SchemaMatch = SchemaMatch.TYPICAL
    ) -> MemoryEvent:
        """Encode event."""
        return self._system.encode_event(content, details, schema_id, match)

    def retrieve(
        self,
        event_id: str,
        delay: float = 1.0
    ) -> Optional[RetrievalResult]:
        """Retrieve event."""
        return self._system.retrieve_event(event_id, delay)

    # Experiments

    def run_bartlett(
        self
    ) -> Dict[str, Any]:
        """Run Bartlett paradigm."""
        result = self._paradigm.run_bartlett_paradigm()
        self._experiment_results.append(result)
        return result

    def run_serial_reproduction(
        self
    ) -> Dict[str, Any]:
        """Run serial reproduction."""
        return self._paradigm.run_serial_reproduction()

    def run_office_scene(
        self
    ) -> Dict[str, Any]:
        """Run office scene study."""
        return self._paradigm.run_office_scene_study()

    def study_activation_levels(
        self
    ) -> Dict[str, Any]:
        """Study activation levels."""
        return self._paradigm.run_schema_activation_levels()

    # Analysis

    def get_metrics(self) -> SchemaMetrics:
        """Get metrics."""
        if not self._experiment_results:
            self.run_bartlett()

        last = self._experiment_results[-1]

        return SchemaMetrics(
            typical_recall=last['typical_recall'],
            atypical_recall=last['atypical_recall'],
            intrusion_rate=last['intrusion_rate'],
            gist_preservation=0.7
        )

    @property
    def state(self) -> Dict[str, Any]:
        """Get engine state."""
        return {
            'schemas': len(self._system._schemas),
            'events': len(self._system._events)
        }


# ============================================================================
# CONVENIENCE
# ============================================================================

def create_schema_activation_engine() -> SchemaActivationEngine:
    """Create schema activation engine."""
    return SchemaActivationEngine()


def demonstrate_schema_activation() -> Dict[str, Any]:
    """Demonstrate schema activation."""
    engine = create_schema_activation_engine()

    # Bartlett paradigm
    bartlett = engine.run_bartlett()

    # Serial reproduction
    serial = engine.run_serial_reproduction()

    # Office scene
    office = engine.run_office_scene()

    # Activation levels
    levels = engine.study_activation_levels()

    return {
        'bartlett': {
            'typical_recall': f"{bartlett['typical_recall']:.0%}",
            'atypical_recall': f"{bartlett['atypical_recall']:.0%}",
            'intrusions': f"{bartlett['intrusion_rate']:.0%}"
        },
        'serial_reproduction': {
            'original': serial['original_details'],
            'final': serial['final_details'],
            'preserved': f"{serial['preservation_rate']:.0%}"
        },
        'office_scene': {
            'false_alarms': office['false_alarms']
        },
        'interpretation': (
            f"Typical recall: {bartlett['typical_recall']:.0%}, "
            f"Atypical: {bartlett['atypical_recall']:.0%}. "
            f"Schemas cause intrusions and shape memory."
        )
    }


def get_schema_activation_facts() -> Dict[str, str]:
    """Get facts about schema activation."""
    return {
        'bartlett_1932': 'Remembering: A Study in Experimental and Social Psychology',
        'schema_def': 'Organized knowledge structure guiding memory',
        'intrusions': 'Schema-consistent false memories',
        'serial_reproduction': 'Memories become schema-consistent',
        'brewer_treyens_1981': 'Office scene study showing schema intrusions',
        'typical_advantage': 'Typical items processed efficiently',
        'atypical_attention': 'Atypical items get special attention',
        'gist_memory': 'General meaning preserved, details reconstructed'
    }
