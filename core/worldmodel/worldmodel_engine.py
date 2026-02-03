#!/usr/bin/env python3
"""
BAEL - World Model Engine
World representation and simulation for agents.

Features:
- Entity modeling
- Relationship tracking
- State management
- World simulation
- Prediction generation
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

class EntityType(Enum):
    """Types of world entities."""
    OBJECT = "object"
    AGENT = "agent"
    LOCATION = "location"
    EVENT = "event"
    CONCEPT = "concept"
    RESOURCE = "resource"


class RelationType(Enum):
    """Types of entity relationships."""
    CONTAINS = "contains"
    NEAR = "near"
    OWNS = "owns"
    USES = "uses"
    KNOWS = "knows"
    DEPENDS_ON = "depends_on"
    CAUSES = "causes"
    PART_OF = "part_of"


class PropertyType(Enum):
    """Types of entity properties."""
    PHYSICAL = "physical"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    RELATIONAL = "relational"
    FUNCTIONAL = "functional"


class StateType(Enum):
    """Types of world states."""
    CURRENT = "current"
    HYPOTHETICAL = "hypothetical"
    HISTORICAL = "historical"
    PREDICTED = "predicted"


class ChangeType(Enum):
    """Types of world changes."""
    ADDITION = "addition"
    REMOVAL = "removal"
    MODIFICATION = "modification"
    TRANSITION = "transition"


class SimulationType(Enum):
    """Types of simulations."""
    FORWARD = "forward"
    BACKWARD = "backward"
    COUNTERFACTUAL = "counterfactual"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class Entity:
    """A world entity."""
    entity_id: str = ""
    name: str = ""
    entity_type: EntityType = EntityType.OBJECT
    properties: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.entity_id:
            self.entity_id = str(uuid.uuid4())[:8]


@dataclass
class Relationship:
    """A relationship between entities."""
    relationship_id: str = ""
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.NEAR
    strength: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.relationship_id:
            self.relationship_id = str(uuid.uuid4())[:8]


@dataclass
class WorldState:
    """A snapshot of world state."""
    state_id: str = ""
    state_type: StateType = StateType.CURRENT
    entities: Dict[str, Entity] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.state_id:
            self.state_id = str(uuid.uuid4())[:8]


@dataclass
class WorldChange:
    """A change in the world."""
    change_id: str = ""
    change_type: ChangeType = ChangeType.MODIFICATION
    entity_id: str = ""
    before: Dict[str, Any] = field(default_factory=dict)
    after: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.change_id:
            self.change_id = str(uuid.uuid4())[:8]


@dataclass
class Prediction:
    """A world prediction."""
    prediction_id: str = ""
    predicted_state: Dict[str, Any] = field(default_factory=dict)
    probability: float = 0.5
    time_horizon: float = 0.0
    conditions: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.prediction_id:
            self.prediction_id = str(uuid.uuid4())[:8]


@dataclass
class WorldModelConfig:
    """World model configuration."""
    max_entities: int = 10000
    max_history_depth: int = 100
    prediction_horizon: float = 3600.0


# =============================================================================
# ENTITY MANAGER
# =============================================================================

class EntityManager:
    """Manage world entities."""

    def __init__(self, max_entities: int = 10000):
        self._entities: Dict[str, Entity] = {}
        self._by_type: Dict[EntityType, Set[str]] = defaultdict(set)
        self._max_entities = max_entities

    def create(
        self,
        name: str,
        entity_type: EntityType,
        properties: Optional[Dict[str, Any]] = None,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """Create an entity."""
        if len(self._entities) >= self._max_entities:
            raise ValueError("Maximum entity limit reached")

        entity = Entity(
            name=name,
            entity_type=entity_type,
            properties=properties or {},
            state=initial_state or {}
        )

        self._entities[entity.entity_id] = entity
        self._by_type[entity_type].add(entity.entity_id)

        return entity

    def get(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def get_by_name(self, name: str) -> Optional[Entity]:
        """Get entity by name."""
        for entity in self._entities.values():
            if entity.name == name:
                return entity
        return None

    def get_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get entities by type."""
        entity_ids = self._by_type.get(entity_type, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    def update_state(
        self,
        entity_id: str,
        state_updates: Dict[str, Any]
    ) -> Optional[Entity]:
        """Update entity state."""
        entity = self._entities.get(entity_id)

        if not entity:
            return None

        entity.state.update(state_updates)

        return entity

    def update_property(
        self,
        entity_id: str,
        property_key: str,
        property_value: Any
    ) -> Optional[Entity]:
        """Update entity property."""
        entity = self._entities.get(entity_id)

        if not entity:
            return None

        entity.properties[property_key] = property_value

        return entity

    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        entity = self._entities.get(entity_id)

        if not entity:
            return False

        self._by_type[entity.entity_type].discard(entity_id)
        del self._entities[entity_id]

        return True

    def search(
        self,
        property_filter: Optional[Dict[str, Any]] = None,
        state_filter: Optional[Dict[str, Any]] = None
    ) -> List[Entity]:
        """Search entities by filters."""
        results = []

        for entity in self._entities.values():
            matches = True

            if property_filter:
                for key, value in property_filter.items():
                    if entity.properties.get(key) != value:
                        matches = False
                        break

            if matches and state_filter:
                for key, value in state_filter.items():
                    if entity.state.get(key) != value:
                        matches = False
                        break

            if matches:
                results.append(entity)

        return results

    def count(self) -> int:
        """Count entities."""
        return len(self._entities)

    def all(self) -> List[Entity]:
        """Get all entities."""
        return list(self._entities.values())


# =============================================================================
# RELATIONSHIP MANAGER
# =============================================================================

class RelationshipManager:
    """Manage entity relationships."""

    def __init__(self):
        self._relationships: Dict[str, Relationship] = {}
        self._by_source: Dict[str, List[str]] = defaultdict(list)
        self._by_target: Dict[str, List[str]] = defaultdict(list)
        self._by_type: Dict[RelationType, List[str]] = defaultdict(list)

    def create(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0,
        properties: Optional[Dict[str, Any]] = None
    ) -> Relationship:
        """Create a relationship."""
        relationship = Relationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
            properties=properties or {}
        )

        self._relationships[relationship.relationship_id] = relationship
        self._by_source[source_id].append(relationship.relationship_id)
        self._by_target[target_id].append(relationship.relationship_id)
        self._by_type[relation_type].append(relationship.relationship_id)

        return relationship

    def get(self, relationship_id: str) -> Optional[Relationship]:
        """Get relationship by ID."""
        return self._relationships.get(relationship_id)

    def get_outgoing(self, source_id: str) -> List[Relationship]:
        """Get outgoing relationships."""
        rel_ids = self._by_source.get(source_id, [])
        return [self._relationships[rid] for rid in rel_ids if rid in self._relationships]

    def get_incoming(self, target_id: str) -> List[Relationship]:
        """Get incoming relationships."""
        rel_ids = self._by_target.get(target_id, [])
        return [self._relationships[rid] for rid in rel_ids if rid in self._relationships]

    def get_by_type(self, relation_type: RelationType) -> List[Relationship]:
        """Get relationships by type."""
        rel_ids = self._by_type.get(relation_type, [])
        return [self._relationships[rid] for rid in rel_ids if rid in self._relationships]

    def find(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relation_type: Optional[RelationType] = None
    ) -> List[Relationship]:
        """Find relationships by criteria."""
        results = []

        for rel in self._relationships.values():
            if source_id and rel.source_id != source_id:
                continue
            if target_id and rel.target_id != target_id:
                continue
            if relation_type and rel.relation_type != relation_type:
                continue

            results.append(rel)

        return results

    def update_strength(
        self,
        relationship_id: str,
        strength: float
    ) -> Optional[Relationship]:
        """Update relationship strength."""
        rel = self._relationships.get(relationship_id)

        if not rel:
            return None

        rel.strength = max(0.0, min(1.0, strength))

        return rel

    def delete(self, relationship_id: str) -> bool:
        """Delete a relationship."""
        rel = self._relationships.get(relationship_id)

        if not rel:
            return False

        self._by_source[rel.source_id].remove(relationship_id)
        self._by_target[rel.target_id].remove(relationship_id)
        self._by_type[rel.relation_type].remove(relationship_id)
        del self._relationships[relationship_id]

        return True

    def get_connected(
        self,
        entity_id: str,
        max_depth: int = 2
    ) -> Set[str]:
        """Get connected entities."""
        connected = set()
        to_visit = [(entity_id, 0)]
        visited = set()

        while to_visit:
            current, depth = to_visit.pop(0)

            if current in visited or depth > max_depth:
                continue

            visited.add(current)
            connected.add(current)

            for rel in self.get_outgoing(current):
                if rel.target_id not in visited:
                    to_visit.append((rel.target_id, depth + 1))

            for rel in self.get_incoming(current):
                if rel.source_id not in visited:
                    to_visit.append((rel.source_id, depth + 1))

        return connected

    def count(self) -> int:
        """Count relationships."""
        return len(self._relationships)

    def all(self) -> List[Relationship]:
        """Get all relationships."""
        return list(self._relationships.values())


# =============================================================================
# STATE MANAGER
# =============================================================================

class StateManager:
    """Manage world states."""

    def __init__(self, max_history: int = 100):
        self._current: Optional[WorldState] = None
        self._history: deque = deque(maxlen=max_history)
        self._hypothetical: Dict[str, WorldState] = {}

    def create_snapshot(
        self,
        entities: Dict[str, Entity],
        relationships: List[Relationship],
        state_type: StateType = StateType.CURRENT
    ) -> WorldState:
        """Create a world state snapshot."""
        state = WorldState(
            state_type=state_type,
            entities=entities.copy(),
            relationships=relationships.copy()
        )

        if state_type == StateType.CURRENT:
            if self._current:
                self._history.append(self._current)
            self._current = state
        elif state_type == StateType.HYPOTHETICAL:
            self._hypothetical[state.state_id] = state

        return state

    def get_current(self) -> Optional[WorldState]:
        """Get current state."""
        return self._current

    def get_history(self, limit: int = 20) -> List[WorldState]:
        """Get state history."""
        return list(self._history)[-limit:]

    def get_hypothetical(self, state_id: str) -> Optional[WorldState]:
        """Get hypothetical state."""
        return self._hypothetical.get(state_id)

    def rollback(self, steps: int = 1) -> Optional[WorldState]:
        """Rollback to previous state."""
        for _ in range(steps):
            if self._history:
                self._current = self._history.pop()

        return self._current

    def diff(
        self,
        state_a: WorldState,
        state_b: WorldState
    ) -> List[WorldChange]:
        """Compute differences between states."""
        changes = []

        entities_a = set(state_a.entities.keys())
        entities_b = set(state_b.entities.keys())

        for entity_id in entities_b - entities_a:
            changes.append(WorldChange(
                change_type=ChangeType.ADDITION,
                entity_id=entity_id,
                after={"entity": state_b.entities[entity_id].state}
            ))

        for entity_id in entities_a - entities_b:
            changes.append(WorldChange(
                change_type=ChangeType.REMOVAL,
                entity_id=entity_id,
                before={"entity": state_a.entities[entity_id].state}
            ))

        for entity_id in entities_a & entities_b:
            before_state = state_a.entities[entity_id].state
            after_state = state_b.entities[entity_id].state

            if before_state != after_state:
                changes.append(WorldChange(
                    change_type=ChangeType.MODIFICATION,
                    entity_id=entity_id,
                    before=before_state,
                    after=after_state
                ))

        return changes

    def delete_hypothetical(self, state_id: str) -> bool:
        """Delete hypothetical state."""
        if state_id in self._hypothetical:
            del self._hypothetical[state_id]
            return True
        return False


# =============================================================================
# SIMULATOR
# =============================================================================

class WorldSimulator:
    """Simulate world changes."""

    def __init__(self):
        self._rules: List[Callable] = []
        self._simulations: List[Dict[str, Any]] = []

    def add_rule(self, rule: Callable[[WorldState], List[WorldChange]]) -> None:
        """Add a simulation rule."""
        self._rules.append(rule)

    def simulate_step(
        self,
        state: WorldState
    ) -> Tuple[WorldState, List[WorldChange]]:
        """Simulate one step forward."""
        all_changes = []

        for rule in self._rules:
            changes = rule(state)
            all_changes.extend(changes)

        new_entities = {}

        for entity_id, entity in state.entities.items():
            new_entity = Entity(
                entity_id=entity.entity_id,
                name=entity.name,
                entity_type=entity.entity_type,
                properties=entity.properties.copy(),
                state=entity.state.copy()
            )
            new_entities[entity_id] = new_entity

        for change in all_changes:
            if change.change_type == ChangeType.MODIFICATION:
                if change.entity_id in new_entities:
                    new_entities[change.entity_id].state.update(change.after)
            elif change.change_type == ChangeType.REMOVAL:
                if change.entity_id in new_entities:
                    del new_entities[change.entity_id]

        new_state = WorldState(
            state_type=StateType.PREDICTED,
            entities=new_entities,
            relationships=state.relationships.copy()
        )

        return new_state, all_changes

    def simulate_forward(
        self,
        initial_state: WorldState,
        steps: int = 10
    ) -> List[WorldState]:
        """Simulate multiple steps forward."""
        states = [initial_state]
        current = initial_state

        for _ in range(steps):
            next_state, _ = self.simulate_step(current)
            states.append(next_state)
            current = next_state

        return states

    def simulate_counterfactual(
        self,
        state: WorldState,
        intervention: Dict[str, Any],
        steps: int = 5
    ) -> List[WorldState]:
        """Simulate counterfactual scenario."""
        modified_state = WorldState(
            state_type=StateType.HYPOTHETICAL,
            entities={
                eid: Entity(
                    entity_id=e.entity_id,
                    name=e.name,
                    entity_type=e.entity_type,
                    properties=e.properties.copy(),
                    state=e.state.copy()
                )
                for eid, e in state.entities.items()
            },
            relationships=state.relationships.copy()
        )

        for entity_id, changes in intervention.items():
            if entity_id in modified_state.entities:
                modified_state.entities[entity_id].state.update(changes)

        return self.simulate_forward(modified_state, steps)


# =============================================================================
# PREDICTOR
# =============================================================================

class WorldPredictor:
    """Predict world states."""

    def __init__(self):
        self._predictions: List[Prediction] = []
        self._patterns: Dict[str, Dict[str, float]] = {}

    def observe_transition(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> None:
        """Observe a state transition."""
        before_key = json.dumps(before, sort_keys=True, default=str)
        after_key = json.dumps(after, sort_keys=True, default=str)

        if before_key not in self._patterns:
            self._patterns[before_key] = {}

        if after_key not in self._patterns[before_key]:
            self._patterns[before_key][after_key] = 0

        self._patterns[before_key][after_key] += 1

    def predict(
        self,
        current_state: Dict[str, Any],
        conditions: Optional[List[str]] = None
    ) -> Prediction:
        """Predict next state."""
        state_key = json.dumps(current_state, sort_keys=True, default=str)

        if state_key in self._patterns:
            transitions = self._patterns[state_key]
            total = sum(transitions.values())

            best_next = max(transitions.items(), key=lambda x: x[1])
            probability = best_next[1] / total

            predicted_state = json.loads(best_next[0])
        else:
            predicted_state = current_state.copy()
            probability = 0.5

        prediction = Prediction(
            predicted_state=predicted_state,
            probability=probability,
            conditions=conditions or []
        )

        self._predictions.append(prediction)

        return prediction

    def predict_property(
        self,
        entity: Entity,
        property_key: str
    ) -> Tuple[Any, float]:
        """Predict a specific property."""
        current_value = entity.state.get(property_key)

        if current_value is None:
            return None, 0.0

        return current_value, 0.5

    def get_predictions(self, limit: int = 20) -> List[Prediction]:
        """Get recent predictions."""
        return self._predictions[-limit:]


# =============================================================================
# WORLD MODEL ENGINE
# =============================================================================

class WorldModelEngine:
    """
    World Model Engine for BAEL.

    World representation and simulation.
    """

    def __init__(self, config: Optional[WorldModelConfig] = None):
        self._config = config or WorldModelConfig()

        self._entity_manager = EntityManager(self._config.max_entities)
        self._relationship_manager = RelationshipManager()
        self._state_manager = StateManager(self._config.max_history_depth)
        self._simulator = WorldSimulator()
        self._predictor = WorldPredictor()

    # ----- Entity Operations -----

    def create_entity(
        self,
        name: str,
        entity_type: EntityType,
        properties: Optional[Dict[str, Any]] = None,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> Entity:
        """Create a world entity."""
        return self._entity_manager.create(
            name=name,
            entity_type=entity_type,
            properties=properties,
            initial_state=initial_state
        )

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self._entity_manager.get(entity_id)

    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Get entity by name."""
        return self._entity_manager.get_by_name(name)

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get entities by type."""
        return self._entity_manager.get_by_type(entity_type)

    def update_entity_state(
        self,
        entity_id: str,
        state_updates: Dict[str, Any]
    ) -> Optional[Entity]:
        """Update entity state."""
        return self._entity_manager.update_state(entity_id, state_updates)

    def delete_entity(self, entity_id: str) -> bool:
        """Delete entity."""
        return self._entity_manager.delete(entity_id)

    def search_entities(
        self,
        property_filter: Optional[Dict[str, Any]] = None,
        state_filter: Optional[Dict[str, Any]] = None
    ) -> List[Entity]:
        """Search entities."""
        return self._entity_manager.search(property_filter, state_filter)

    # ----- Relationship Operations -----

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0
    ) -> Relationship:
        """Create a relationship."""
        return self._relationship_manager.create(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength
        )

    def get_relationships(self, entity_id: str) -> List[Relationship]:
        """Get all relationships for entity."""
        outgoing = self._relationship_manager.get_outgoing(entity_id)
        incoming = self._relationship_manager.get_incoming(entity_id)
        return outgoing + incoming

    def find_relationships(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relation_type: Optional[RelationType] = None
    ) -> List[Relationship]:
        """Find relationships by criteria."""
        return self._relationship_manager.find(source_id, target_id, relation_type)

    def get_connected_entities(
        self,
        entity_id: str,
        max_depth: int = 2
    ) -> Set[str]:
        """Get connected entities."""
        return self._relationship_manager.get_connected(entity_id, max_depth)

    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete relationship."""
        return self._relationship_manager.delete(relationship_id)

    # ----- State Operations -----

    def snapshot(self) -> WorldState:
        """Create current state snapshot."""
        entities = {e.entity_id: e for e in self._entity_manager.all()}
        relationships = self._relationship_manager.all()

        return self._state_manager.create_snapshot(
            entities=entities,
            relationships=relationships,
            state_type=StateType.CURRENT
        )

    def get_current_state(self) -> Optional[WorldState]:
        """Get current world state."""
        return self._state_manager.get_current()

    def get_state_history(self, limit: int = 20) -> List[WorldState]:
        """Get state history."""
        return self._state_manager.get_history(limit)

    def rollback(self, steps: int = 1) -> Optional[WorldState]:
        """Rollback to previous state."""
        return self._state_manager.rollback(steps)

    def compute_changes(
        self,
        state_a: WorldState,
        state_b: WorldState
    ) -> List[WorldChange]:
        """Compute changes between states."""
        return self._state_manager.diff(state_a, state_b)

    # ----- Simulation Operations -----

    def add_simulation_rule(
        self,
        rule: Callable[[WorldState], List[WorldChange]]
    ) -> None:
        """Add simulation rule."""
        self._simulator.add_rule(rule)

    def simulate_step(self) -> Tuple[WorldState, List[WorldChange]]:
        """Simulate one step."""
        current = self._state_manager.get_current()

        if not current:
            current = self.snapshot()

        return self._simulator.simulate_step(current)

    def simulate_forward(self, steps: int = 10) -> List[WorldState]:
        """Simulate multiple steps forward."""
        current = self._state_manager.get_current()

        if not current:
            current = self.snapshot()

        return self._simulator.simulate_forward(current, steps)

    def simulate_counterfactual(
        self,
        intervention: Dict[str, Any],
        steps: int = 5
    ) -> List[WorldState]:
        """Simulate counterfactual scenario."""
        current = self._state_manager.get_current()

        if not current:
            current = self.snapshot()

        return self._simulator.simulate_counterfactual(current, intervention, steps)

    # ----- Prediction Operations -----

    def observe_change(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> None:
        """Observe a state transition."""
        self._predictor.observe_transition(before, after)

    def predict_state(
        self,
        current_state: Dict[str, Any]
    ) -> Prediction:
        """Predict next state."""
        return self._predictor.predict(current_state)

    def get_predictions(self, limit: int = 20) -> List[Prediction]:
        """Get recent predictions."""
        return self._predictor.get_predictions(limit)

    # ----- Query Operations -----

    def query(self, query: str) -> List[Entity]:
        """Query world model (simple keyword search)."""
        results = []
        query_lower = query.lower()

        for entity in self._entity_manager.all():
            if query_lower in entity.name.lower():
                results.append(entity)
                continue

            for value in entity.properties.values():
                if isinstance(value, str) and query_lower in value.lower():
                    results.append(entity)
                    break

        return results

    def summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        return {
            "entities": self._entity_manager.count(),
            "relationships": self._relationship_manager.count(),
            "history_depth": len(self._state_manager._history),
            "predictions": len(self._predictor._predictions)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the World Model Engine."""
    print("=" * 70)
    print("BAEL - WORLD MODEL ENGINE DEMO")
    print("World Representation and Simulation")
    print("=" * 70)
    print()

    engine = WorldModelEngine()

    # 1. Create Entities
    print("1. CREATE ENTITIES:")
    print("-" * 40)

    room = engine.create_entity(
        "living_room",
        EntityType.LOCATION,
        properties={"size": "large", "floor": 1},
        initial_state={"temperature": 22, "occupied": True}
    )

    agent = engine.create_entity(
        "robot_1",
        EntityType.AGENT,
        properties={"type": "service", "battery_capacity": 100},
        initial_state={"battery": 85, "active": True, "location": room.entity_id}
    )

    lamp = engine.create_entity(
        "desk_lamp",
        EntityType.OBJECT,
        properties={"type": "lighting", "wattage": 60},
        initial_state={"on": False}
    )

    print(f"   Created: {room.name} ({room.entity_id})")
    print(f"   Created: {agent.name} ({agent.entity_id})")
    print(f"   Created: {lamp.name} ({lamp.entity_id})")
    print()

    # 2. Create Relationships
    print("2. CREATE RELATIONSHIPS:")
    print("-" * 40)

    rel1 = engine.create_relationship(
        room.entity_id,
        lamp.entity_id,
        RelationType.CONTAINS
    )

    rel2 = engine.create_relationship(
        agent.entity_id,
        room.entity_id,
        RelationType.NEAR
    )

    rel3 = engine.create_relationship(
        agent.entity_id,
        lamp.entity_id,
        RelationType.USES
    )

    print(f"   {room.name} CONTAINS {lamp.name}")
    print(f"   {agent.name} NEAR {room.name}")
    print(f"   {agent.name} USES {lamp.name}")
    print()

    # 3. Query Entities
    print("3. QUERY ENTITIES:")
    print("-" * 40)

    agents = engine.get_entities_by_type(EntityType.AGENT)
    print(f"   Agents: {[a.name for a in agents]}")

    objects = engine.get_entities_by_type(EntityType.OBJECT)
    print(f"   Objects: {[o.name for o in objects]}")

    found = engine.get_entity_by_name("living_room")
    if found:
        print(f"   Found by name: {found.name}")
    print()

    # 4. Get Relationships
    print("4. GET RELATIONSHIPS:")
    print("-" * 40)

    agent_rels = engine.get_relationships(agent.entity_id)
    print(f"   {agent.name} relationships: {len(agent_rels)}")

    for rel in agent_rels:
        print(f"     - {rel.relation_type.value} -> {rel.target_id}")
    print()

    # 5. Get Connected Entities
    print("5. CONNECTED ENTITIES:")
    print("-" * 40)

    connected = engine.get_connected_entities(agent.entity_id, max_depth=2)
    print(f"   Connected to {agent.name}: {len(connected)} entities")

    for eid in connected:
        entity = engine.get_entity(eid)
        if entity:
            print(f"     - {entity.name}")
    print()

    # 6. Create Snapshot
    print("6. CREATE SNAPSHOT:")
    print("-" * 40)

    state1 = engine.snapshot()
    print(f"   State ID: {state1.state_id}")
    print(f"   Entities: {len(state1.entities)}")
    print(f"   Relationships: {len(state1.relationships)}")
    print()

    # 7. Update Entity State
    print("7. UPDATE ENTITY STATE:")
    print("-" * 40)

    print(f"   Before: lamp.on = {lamp.state.get('on')}")

    engine.update_entity_state(lamp.entity_id, {"on": True})

    print(f"   After: lamp.on = {lamp.state.get('on')}")
    print()

    # 8. Compute Changes
    print("8. COMPUTE CHANGES:")
    print("-" * 40)

    state2 = engine.snapshot()
    changes = engine.compute_changes(state1, state2)

    print(f"   Changes between states: {len(changes)}")
    for change in changes:
        print(f"     - {change.change_type.value}: {change.entity_id}")
        print(f"       Before: {change.before}")
        print(f"       After: {change.after}")
    print()

    # 9. Add Simulation Rule
    print("9. ADD SIMULATION RULE:")
    print("-" * 40)

    def battery_drain_rule(state: WorldState) -> List[WorldChange]:
        changes = []
        for entity in state.entities.values():
            if entity.entity_type == EntityType.AGENT:
                current_battery = entity.state.get("battery", 100)
                if current_battery > 0:
                    changes.append(WorldChange(
                        change_type=ChangeType.MODIFICATION,
                        entity_id=entity.entity_id,
                        before={"battery": current_battery},
                        after={"battery": current_battery - 5}
                    ))
        return changes

    engine.add_simulation_rule(battery_drain_rule)
    print("   Added battery drain rule")
    print()

    # 10. Simulate Forward
    print("10. SIMULATE FORWARD:")
    print("-" * 40)

    future_states = engine.simulate_forward(steps=3)

    for i, state in enumerate(future_states):
        for entity in state.entities.values():
            if entity.entity_type == EntityType.AGENT:
                battery = entity.state.get("battery", "N/A")
                print(f"   Step {i}: {entity.name} battery = {battery}")
    print()

    # 11. Simulate Counterfactual
    print("11. SIMULATE COUNTERFACTUAL:")
    print("-" * 40)

    cf_states = engine.simulate_counterfactual(
        intervention={agent.entity_id: {"battery": 100}},
        steps=3
    )

    print(f"   Counterfactual: What if battery was 100?")
    for i, state in enumerate(cf_states):
        for entity in state.entities.values():
            if entity.entity_type == EntityType.AGENT:
                battery = entity.state.get("battery", "N/A")
                print(f"   Step {i}: {entity.name} battery = {battery}")
    print()

    # 12. Observe and Predict
    print("12. OBSERVE AND PREDICT:")
    print("-" * 40)

    engine.observe_change({"state": "A"}, {"state": "B"})
    engine.observe_change({"state": "A"}, {"state": "B"})
    engine.observe_change({"state": "A"}, {"state": "C"})

    prediction = engine.predict_state({"state": "A"})

    print(f"   Observed transitions from state A")
    print(f"   Prediction: {prediction.predicted_state}")
    print(f"   Probability: {prediction.probability:.2f}")
    print()

    # 13. Query World
    print("13. QUERY WORLD:")
    print("-" * 40)

    results = engine.query("lamp")
    print(f"   Query 'lamp': {[e.name for e in results]}")

    results = engine.query("robot")
    print(f"   Query 'robot': {[e.name for e in results]}")
    print()

    # 14. Search Entities
    print("14. SEARCH ENTITIES:")
    print("-" * 40)

    active_agents = engine.search_entities(
        state_filter={"active": True}
    )

    print(f"   Active entities: {[e.name for e in active_agents]}")
    print()

    # 15. Summary
    print("15. ENGINE SUMMARY:")
    print("-" * 40)

    summary = engine.summary()

    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - World Model Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
