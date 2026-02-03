#!/usr/bin/env python3
"""
BAEL - World Model
Advanced world state modeling and simulation.

Features:
- Entity-component system
- State tracking
- Predictive modeling
- Counterfactual reasoning
- Event simulation
- Constraint management
- Temporal dynamics
"""

import asyncio
import copy
import hashlib
import math
import random
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

class EntityType(Enum):
    """Types of world entities."""
    AGENT = "agent"
    OBJECT = "object"
    LOCATION = "location"
    EVENT = "event"
    CONCEPT = "concept"


class PropertyType(Enum):
    """Types of entity properties."""
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    STRING = "string"
    ENUM = "enum"
    REFERENCE = "reference"
    LIST = "list"


class RelationType(Enum):
    """Types of relations between entities."""
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    PART_OF = "part_of"
    OWNERSHIP = "ownership"
    SOCIAL = "social"


class EventType(Enum):
    """Types of world events."""
    ACTION = "action"
    STATE_CHANGE = "state_change"
    CREATION = "creation"
    DESTRUCTION = "destruction"
    INTERACTION = "interaction"


class SimulationMode(Enum):
    """Simulation modes."""
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"
    MONTE_CARLO = "monte_carlo"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Property:
    """An entity property."""
    name: str
    property_type: PropertyType = PropertyType.STRING
    value: Any = None
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Entity:
    """A world entity."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: EntityType = EntityType.OBJECT
    properties: Dict[str, Property] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)


@dataclass
class Relation:
    """A relation between entities."""
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.SPATIAL
    name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldEvent:
    """A world event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.ACTION
    name: str = ""
    timestamp: float = 0.0
    participants: List[str] = field(default_factory=list)
    effects: Dict[str, Any] = field(default_factory=dict)
    preconditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldState:
    """A snapshot of world state."""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = 0.0
    entities: Dict[str, Entity] = field(default_factory=dict)
    relations: Dict[str, Relation] = field(default_factory=dict)
    active_events: List[str] = field(default_factory=list)


@dataclass
class Constraint:
    """A world constraint."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    condition: Callable[[WorldState], bool] = None
    error_message: str = ""


@dataclass
class Prediction:
    """A prediction about future state."""
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    future_state: WorldState = None
    probability: float = 1.0
    time_horizon: float = 0.0
    assumptions: List[str] = field(default_factory=list)


# =============================================================================
# ENTITY MANAGER
# =============================================================================

class EntityManager:
    """Manage world entities."""

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._by_type: Dict[EntityType, Set[str]] = defaultdict(set)
        self._by_tag: Dict[str, Set[str]] = defaultdict(set)

    def create_entity(
        self,
        name: str,
        entity_type: EntityType = EntityType.OBJECT,
        properties: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None
    ) -> Entity:
        """Create a new entity."""
        entity = Entity(
            name=name,
            entity_type=entity_type,
            tags=tags or set()
        )

        # Add properties
        if properties:
            for prop_name, prop_value in properties.items():
                prop_type = self._infer_type(prop_value)
                entity.properties[prop_name] = Property(
                    name=prop_name,
                    property_type=prop_type,
                    value=prop_value
                )

        # Index entity
        self._entities[entity.entity_id] = entity
        self._by_type[entity_type].add(entity.entity_id)

        for tag in entity.tags:
            self._by_tag[tag].add(entity.entity_id)

        return entity

    def _infer_type(self, value: Any) -> PropertyType:
        """Infer property type from value."""
        if isinstance(value, bool):
            return PropertyType.BOOLEAN
        if isinstance(value, (int, float)):
            return PropertyType.NUMERIC
        if isinstance(value, str):
            return PropertyType.STRING
        if isinstance(value, list):
            return PropertyType.LIST
        return PropertyType.STRING

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def get_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a type."""
        return [
            self._entities[eid]
            for eid in self._by_type[entity_type]
            if eid in self._entities
        ]

    def get_by_tag(self, tag: str) -> List[Entity]:
        """Get all entities with a tag."""
        return [
            self._entities[eid]
            for eid in self._by_tag[tag]
            if eid in self._entities
        ]

    def set_property(
        self,
        entity_id: str,
        prop_name: str,
        value: Any
    ) -> bool:
        """Set an entity property."""
        entity = self._entities.get(entity_id)
        if not entity:
            return False

        if prop_name in entity.properties:
            entity.properties[prop_name].value = value
        else:
            entity.properties[prop_name] = Property(
                name=prop_name,
                property_type=self._infer_type(value),
                value=value
            )

        return True

    def get_property(
        self,
        entity_id: str,
        prop_name: str
    ) -> Optional[Any]:
        """Get an entity property value."""
        entity = self._entities.get(entity_id)
        if not entity:
            return None

        prop = entity.properties.get(prop_name)
        return prop.value if prop else None

    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return False

        self._by_type[entity.entity_type].discard(entity_id)
        for tag in entity.tags:
            self._by_tag[tag].discard(entity_id)

        del self._entities[entity_id]
        return True

    def add_tag(self, entity_id: str, tag: str) -> bool:
        """Add a tag to an entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return False

        entity.tags.add(tag)
        self._by_tag[tag].add(entity_id)
        return True

    def get_all_entities(self) -> Dict[str, Entity]:
        """Get all entities."""
        return self._entities.copy()


# =============================================================================
# RELATION MANAGER
# =============================================================================

class RelationManager:
    """Manage relations between entities."""

    def __init__(self):
        self._relations: Dict[str, Relation] = {}
        self._by_source: Dict[str, Set[str]] = defaultdict(set)
        self._by_target: Dict[str, Set[str]] = defaultdict(set)
        self._by_type: Dict[RelationType, Set[str]] = defaultdict(set)

    def create_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        name: str = "",
        properties: Optional[Dict[str, Any]] = None
    ) -> Relation:
        """Create a relation."""
        relation = Relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            name=name,
            properties=properties or {}
        )

        self._relations[relation.relation_id] = relation
        self._by_source[source_id].add(relation.relation_id)
        self._by_target[target_id].add(relation.relation_id)
        self._by_type[relation_type].add(relation.relation_id)

        return relation

    def get_relations_from(self, entity_id: str) -> List[Relation]:
        """Get all relations from an entity."""
        return [
            self._relations[rid]
            for rid in self._by_source[entity_id]
            if rid in self._relations
        ]

    def get_relations_to(self, entity_id: str) -> List[Relation]:
        """Get all relations to an entity."""
        return [
            self._relations[rid]
            for rid in self._by_target[entity_id]
            if rid in self._relations
        ]

    def get_relations_by_type(self, relation_type: RelationType) -> List[Relation]:
        """Get all relations of a type."""
        return [
            self._relations[rid]
            for rid in self._by_type[relation_type]
            if rid in self._relations
        ]

    def delete_relation(self, relation_id: str) -> bool:
        """Delete a relation."""
        relation = self._relations.get(relation_id)
        if not relation:
            return False

        self._by_source[relation.source_id].discard(relation_id)
        self._by_target[relation.target_id].discard(relation_id)
        self._by_type[relation.relation_type].discard(relation_id)

        del self._relations[relation_id]
        return True

    def get_all_relations(self) -> Dict[str, Relation]:
        """Get all relations."""
        return self._relations.copy()


# =============================================================================
# EVENT PROCESSOR
# =============================================================================

class EventProcessor:
    """Process world events."""

    def __init__(self, entity_manager: EntityManager):
        self._entity_manager = entity_manager
        self._event_history: List[WorldEvent] = []
        self._event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)

    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[WorldEvent], None]
    ) -> None:
        """Register an event handler."""
        self._event_handlers[event_type].append(handler)

    def apply_event(self, event: WorldEvent) -> bool:
        """Apply an event to the world."""
        # Check preconditions
        for entity_id, conditions in event.preconditions.items():
            entity = self._entity_manager.get_entity(entity_id)
            if not entity:
                return False

            for prop_name, expected in conditions.items():
                actual = self._entity_manager.get_property(entity_id, prop_name)
                if actual != expected:
                    return False

        # Apply effects
        for entity_id, effects in event.effects.items():
            for prop_name, new_value in effects.items():
                self._entity_manager.set_property(entity_id, prop_name, new_value)

        # Call handlers
        for handler in self._event_handlers[event.event_type]:
            handler(event)

        self._event_history.append(event)
        return True

    def get_event_history(self) -> List[WorldEvent]:
        """Get event history."""
        return self._event_history.copy()

    def create_event(
        self,
        event_type: EventType,
        name: str,
        participants: Optional[List[str]] = None,
        effects: Optional[Dict[str, Dict[str, Any]]] = None,
        preconditions: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> WorldEvent:
        """Create a new event."""
        return WorldEvent(
            event_type=event_type,
            name=name,
            timestamp=datetime.now().timestamp(),
            participants=participants or [],
            effects=effects or {},
            preconditions=preconditions or {}
        )


# =============================================================================
# CONSTRAINT MANAGER
# =============================================================================

class ConstraintManager:
    """Manage world constraints."""

    def __init__(self):
        self._constraints: Dict[str, Constraint] = {}

    def add_constraint(
        self,
        name: str,
        condition: Callable[[WorldState], bool],
        error_message: str = ""
    ) -> Constraint:
        """Add a constraint."""
        constraint = Constraint(
            name=name,
            condition=condition,
            error_message=error_message
        )
        self._constraints[constraint.constraint_id] = constraint
        return constraint

    def check_constraints(
        self,
        state: WorldState
    ) -> Tuple[bool, List[str]]:
        """Check all constraints against a state."""
        violations = []

        for constraint in self._constraints.values():
            if constraint.condition and not constraint.condition(state):
                violations.append(
                    constraint.error_message or f"Constraint '{constraint.name}' violated"
                )

        return len(violations) == 0, violations

    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a constraint."""
        if constraint_id in self._constraints:
            del self._constraints[constraint_id]
            return True
        return False


# =============================================================================
# STATE MANAGER
# =============================================================================

class StateManager:
    """Manage world state snapshots."""

    def __init__(
        self,
        entity_manager: EntityManager,
        relation_manager: RelationManager
    ):
        self._entity_manager = entity_manager
        self._relation_manager = relation_manager
        self._history: List[WorldState] = []
        self._max_history = 100

    def capture_state(self) -> WorldState:
        """Capture current world state."""
        state = WorldState(
            timestamp=datetime.now().timestamp(),
            entities=copy.deepcopy(self._entity_manager.get_all_entities()),
            relations=copy.deepcopy(self._relation_manager.get_all_relations())
        )

        self._history.append(state)

        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return state

    def restore_state(self, state: WorldState) -> bool:
        """Restore a previous state."""
        # Clear current state
        for entity_id in list(self._entity_manager._entities.keys()):
            self._entity_manager.delete_entity(entity_id)

        for relation_id in list(self._relation_manager._relations.keys()):
            self._relation_manager.delete_relation(relation_id)

        # Restore entities
        for entity_id, entity in state.entities.items():
            new_entity = self._entity_manager.create_entity(
                name=entity.name,
                entity_type=entity.entity_type,
                tags=entity.tags
            )
            for prop_name, prop in entity.properties.items():
                self._entity_manager.set_property(new_entity.entity_id, prop_name, prop.value)

        # Restore relations
        for relation in state.relations.values():
            self._relation_manager.create_relation(
                source_id=relation.source_id,
                target_id=relation.target_id,
                relation_type=relation.relation_type,
                name=relation.name,
                properties=relation.properties
            )

        return True

    def get_history(self) -> List[WorldState]:
        """Get state history."""
        return self._history.copy()

    def get_state_at(self, index: int) -> Optional[WorldState]:
        """Get state at history index."""
        if 0 <= index < len(self._history):
            return self._history[index]
        return None


# =============================================================================
# SIMULATOR
# =============================================================================

class WorldSimulator:
    """Simulate world dynamics."""

    def __init__(
        self,
        entity_manager: EntityManager,
        event_processor: EventProcessor
    ):
        self._entity_manager = entity_manager
        self._event_processor = event_processor
        self._dynamics: List[Callable[[float], List[WorldEvent]]] = []

    def add_dynamics(
        self,
        dynamics_fn: Callable[[float], List[WorldEvent]]
    ) -> None:
        """Add a dynamics function that generates events."""
        self._dynamics.append(dynamics_fn)

    def step(self, dt: float = 1.0) -> List[WorldEvent]:
        """Advance simulation by time step."""
        all_events = []

        for dynamics_fn in self._dynamics:
            events = dynamics_fn(dt)
            for event in events:
                if self._event_processor.apply_event(event):
                    all_events.append(event)

        return all_events

    def run(
        self,
        duration: float,
        dt: float = 1.0
    ) -> List[WorldEvent]:
        """Run simulation for duration."""
        all_events = []
        current_time = 0.0

        while current_time < duration:
            events = self.step(dt)
            all_events.extend(events)
            current_time += dt

        return all_events


# =============================================================================
# PREDICTOR
# =============================================================================

class WorldPredictor:
    """Predict future world states."""

    def __init__(
        self,
        state_manager: StateManager,
        simulator: WorldSimulator
    ):
        self._state_manager = state_manager
        self._simulator = simulator

    def predict(
        self,
        horizon: float,
        num_samples: int = 1
    ) -> List[Prediction]:
        """Predict future states."""
        predictions = []

        # Capture current state
        current_state = self._state_manager.capture_state()

        for _ in range(num_samples):
            # Run simulation
            events = self._simulator.run(horizon)

            # Capture predicted state
            future_state = self._state_manager.capture_state()

            prediction = Prediction(
                future_state=future_state,
                probability=1.0 / num_samples,
                time_horizon=horizon,
                assumptions=[f"Event: {e.name}" for e in events[:5]]
            )
            predictions.append(prediction)

            # Restore for next sample
            self._state_manager.restore_state(current_state)

        return predictions

    def counterfactual(
        self,
        intervention: Dict[str, Dict[str, Any]],
        horizon: float
    ) -> Prediction:
        """Generate counterfactual prediction."""
        # Capture current state
        current_state = self._state_manager.capture_state()

        # Apply intervention
        for entity_id, changes in intervention.items():
            for prop_name, value in changes.items():
                self._state_manager._entity_manager.set_property(
                    entity_id, prop_name, value
                )

        # Simulate
        events = self._simulator.run(horizon)

        # Capture counterfactual state
        cf_state = self._state_manager.capture_state()

        # Restore original
        self._state_manager.restore_state(current_state)

        return Prediction(
            future_state=cf_state,
            probability=1.0,
            time_horizon=horizon,
            assumptions=[
                f"Intervention: {intervention}",
                *[f"Event: {e.name}" for e in events[:3]]
            ]
        )


# =============================================================================
# WORLD MODEL
# =============================================================================

class WorldModel:
    """
    World Model for BAEL.

    Advanced world state modeling and simulation.
    """

    def __init__(self):
        self._entity_manager = EntityManager()
        self._relation_manager = RelationManager()
        self._event_processor = EventProcessor(self._entity_manager)
        self._constraint_manager = ConstraintManager()
        self._state_manager = StateManager(
            self._entity_manager, self._relation_manager
        )
        self._simulator = WorldSimulator(
            self._entity_manager, self._event_processor
        )
        self._predictor = WorldPredictor(
            self._state_manager, self._simulator
        )

    # -------------------------------------------------------------------------
    # ENTITY OPERATIONS
    # -------------------------------------------------------------------------

    def create_entity(
        self,
        name: str,
        entity_type: EntityType = EntityType.OBJECT,
        properties: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None
    ) -> Entity:
        """Create a new entity."""
        return self._entity_manager.create_entity(
            name, entity_type, properties, tags
        )

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity."""
        return self._entity_manager.get_entity(entity_id)

    def set_property(
        self,
        entity_id: str,
        prop_name: str,
        value: Any
    ) -> bool:
        """Set entity property."""
        return self._entity_manager.set_property(entity_id, prop_name, value)

    def get_property(
        self,
        entity_id: str,
        prop_name: str
    ) -> Optional[Any]:
        """Get entity property."""
        return self._entity_manager.get_property(entity_id, prop_name)

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get entities by type."""
        return self._entity_manager.get_by_type(entity_type)

    def get_entities_by_tag(self, tag: str) -> List[Entity]:
        """Get entities by tag."""
        return self._entity_manager.get_by_tag(tag)

    # -------------------------------------------------------------------------
    # RELATION OPERATIONS
    # -------------------------------------------------------------------------

    def create_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        name: str = "",
        properties: Optional[Dict[str, Any]] = None
    ) -> Relation:
        """Create a relation."""
        return self._relation_manager.create_relation(
            source_id, target_id, relation_type, name, properties
        )

    def get_relations_from(self, entity_id: str) -> List[Relation]:
        """Get relations from entity."""
        return self._relation_manager.get_relations_from(entity_id)

    def get_relations_to(self, entity_id: str) -> List[Relation]:
        """Get relations to entity."""
        return self._relation_manager.get_relations_to(entity_id)

    # -------------------------------------------------------------------------
    # EVENT OPERATIONS
    # -------------------------------------------------------------------------

    def apply_event(
        self,
        event_type: EventType,
        name: str,
        participants: Optional[List[str]] = None,
        effects: Optional[Dict[str, Dict[str, Any]]] = None,
        preconditions: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> bool:
        """Create and apply an event."""
        event = self._event_processor.create_event(
            event_type, name, participants, effects, preconditions
        )
        return self._event_processor.apply_event(event)

    def get_event_history(self) -> List[WorldEvent]:
        """Get event history."""
        return self._event_processor.get_event_history()

    # -------------------------------------------------------------------------
    # CONSTRAINT OPERATIONS
    # -------------------------------------------------------------------------

    def add_constraint(
        self,
        name: str,
        condition: Callable[[WorldState], bool],
        error_message: str = ""
    ) -> Constraint:
        """Add a constraint."""
        return self._constraint_manager.add_constraint(name, condition, error_message)

    def check_constraints(self) -> Tuple[bool, List[str]]:
        """Check all constraints."""
        state = self._state_manager.capture_state()
        return self._constraint_manager.check_constraints(state)

    # -------------------------------------------------------------------------
    # STATE OPERATIONS
    # -------------------------------------------------------------------------

    def capture_state(self) -> WorldState:
        """Capture current state."""
        return self._state_manager.capture_state()

    def restore_state(self, state: WorldState) -> bool:
        """Restore a state."""
        return self._state_manager.restore_state(state)

    def get_state_history(self) -> List[WorldState]:
        """Get state history."""
        return self._state_manager.get_history()

    # -------------------------------------------------------------------------
    # SIMULATION
    # -------------------------------------------------------------------------

    def add_dynamics(
        self,
        dynamics_fn: Callable[[float], List[WorldEvent]]
    ) -> None:
        """Add dynamics function."""
        self._simulator.add_dynamics(dynamics_fn)

    def simulate(
        self,
        duration: float,
        dt: float = 1.0
    ) -> List[WorldEvent]:
        """Run simulation."""
        return self._simulator.run(duration, dt)

    # -------------------------------------------------------------------------
    # PREDICTION
    # -------------------------------------------------------------------------

    def predict(
        self,
        horizon: float,
        num_samples: int = 1
    ) -> List[Prediction]:
        """Predict future states."""
        return self._predictor.predict(horizon, num_samples)

    def counterfactual(
        self,
        intervention: Dict[str, Dict[str, Any]],
        horizon: float
    ) -> Prediction:
        """Generate counterfactual."""
        return self._predictor.counterfactual(intervention, horizon)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the World Model."""
    print("=" * 70)
    print("BAEL - WORLD MODEL DEMO")
    print("Advanced World State Modeling and Simulation")
    print("=" * 70)
    print()

    model = WorldModel()

    # 1. Create Entities
    print("1. CREATE ENTITIES:")
    print("-" * 40)

    robot = model.create_entity(
        "Robot-1",
        EntityType.AGENT,
        properties={"x": 0, "y": 0, "battery": 100, "active": True},
        tags={"autonomous", "mobile"}
    )

    box = model.create_entity(
        "Box-A",
        EntityType.OBJECT,
        properties={"x": 5, "y": 5, "weight": 10, "picked_up": False}
    )

    goal = model.create_entity(
        "Goal-Zone",
        EntityType.LOCATION,
        properties={"x": 10, "y": 10, "radius": 2}
    )

    print(f"   Created: {robot.name} (Agent)")
    print(f"   Created: {box.name} (Object)")
    print(f"   Created: {goal.name} (Location)")
    print()

    # 2. Create Relations
    print("2. CREATE RELATIONS:")
    print("-" * 40)

    near_rel = model.create_relation(
        robot.entity_id,
        box.entity_id,
        RelationType.SPATIAL,
        "near_to",
        {"distance": 7.07}
    )

    target_rel = model.create_relation(
        robot.entity_id,
        goal.entity_id,
        RelationType.SPATIAL,
        "target",
        {"priority": 1}
    )

    print(f"   {robot.name} --[near_to]--> {box.name}")
    print(f"   {robot.name} --[target]--> {goal.name}")
    print()

    # 3. Get/Set Properties
    print("3. PROPERTY OPERATIONS:")
    print("-" * 40)

    battery = model.get_property(robot.entity_id, "battery")
    print(f"   Robot battery: {battery}%")

    model.set_property(robot.entity_id, "x", 2)
    model.set_property(robot.entity_id, "y", 2)

    new_x = model.get_property(robot.entity_id, "x")
    new_y = model.get_property(robot.entity_id, "y")
    print(f"   Robot moved to: ({new_x}, {new_y})")
    print()

    # 4. Apply Events
    print("4. APPLY EVENTS:")
    print("-" * 40)

    success = model.apply_event(
        EventType.ACTION,
        "move",
        participants=[robot.entity_id],
        effects={robot.entity_id: {"x": 5, "y": 5, "battery": 95}}
    )
    print(f"   Move event applied: {success}")

    x = model.get_property(robot.entity_id, "x")
    y = model.get_property(robot.entity_id, "y")
    battery = model.get_property(robot.entity_id, "battery")
    print(f"   Robot now at: ({x}, {y}), battery: {battery}%")

    # Pick up box
    success = model.apply_event(
        EventType.INTERACTION,
        "pick_up",
        participants=[robot.entity_id, box.entity_id],
        effects={
            box.entity_id: {"picked_up": True},
            robot.entity_id: {"carrying": True}
        }
    )
    print(f"   Pick up event applied: {success}")
    print()

    # 5. Query Entities
    print("5. QUERY ENTITIES:")
    print("-" * 40)

    agents = model.get_entities_by_type(EntityType.AGENT)
    print(f"   Agents: {[a.name for a in agents]}")

    mobile = model.get_entities_by_tag("mobile")
    print(f"   Mobile entities: {[e.name for e in mobile]}")
    print()

    # 6. State Capture
    print("6. STATE MANAGEMENT:")
    print("-" * 40)

    state1 = model.capture_state()
    print(f"   Captured state: {len(state1.entities)} entities")

    # Make changes
    model.set_property(robot.entity_id, "battery", 50)

    state2 = model.capture_state()

    # Restore
    model.restore_state(state1)
    battery = model.get_property(robot.entity_id, "battery")
    print(f"   Restored battery: {battery}%")
    print()

    # 7. Relations Query
    print("7. RELATION QUERIES:")
    print("-" * 40)

    relations_from = model.get_relations_from(robot.entity_id)
    print(f"   Relations from Robot: {len(relations_from)}")
    for rel in relations_from:
        target = model.get_entity(rel.target_id)
        print(f"     --[{rel.name}]--> {target.name if target else 'Unknown'}")
    print()

    # 8. Event History
    print("8. EVENT HISTORY:")
    print("-" * 40)

    history = model.get_event_history()
    print(f"   Events recorded: {len(history)}")
    for event in history:
        print(f"     - {event.name} ({event.event_type.value})")
    print()

    # 9. Constraints
    print("9. CONSTRAINT CHECKING:")
    print("-" * 40)

    def battery_check(state: WorldState) -> bool:
        for entity in state.entities.values():
            battery = entity.properties.get("battery")
            if battery and battery.value < 20:
                return False
        return True

    model.add_constraint("battery_low", battery_check, "Battery too low!")

    valid, violations = model.check_constraints()
    print(f"   Constraints valid: {valid}")
    if violations:
        for v in violations:
            print(f"     - {v}")
    print()

    # 10. Dynamics and Simulation
    print("10. SIMULATION:")
    print("-" * 40)

    def battery_drain(dt: float) -> List[WorldEvent]:
        # Simulate battery drain
        events = []
        for entity in model.get_entities_by_type(EntityType.AGENT):
            current = model.get_property(entity.entity_id, "battery")
            if current and current > 0:
                new_val = max(0, current - dt * 2)
                event = WorldEvent(
                    event_type=EventType.STATE_CHANGE,
                    name="battery_drain",
                    effects={entity.entity_id: {"battery": new_val}}
                )
                events.append(event)
        return events

    model.add_dynamics(battery_drain)

    events = model.simulate(duration=5, dt=1.0)
    print(f"   Simulated {len(events)} events over 5 time units")

    battery = model.get_property(robot.entity_id, "battery")
    print(f"   Final battery: {battery}%")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - World Model Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
