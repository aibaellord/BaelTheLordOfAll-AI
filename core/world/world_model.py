#!/usr/bin/env python3
"""
BAEL - World Model System
Internal world representation and simulation.

Features:
- World state representation
- Entity and relationship modeling
- State prediction and simulation
- Counterfactual reasoning
- Mental simulation
- Model-based planning
"""

import asyncio
import copy
import hashlib
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class EntityType(Enum):
    """Types of entities."""
    OBJECT = "object"
    AGENT = "agent"
    LOCATION = "location"
    EVENT = "event"
    ABSTRACT = "abstract"


class PropertyType(Enum):
    """Types of properties."""
    STATIC = "static"       # Doesn't change
    DYNAMIC = "dynamic"     # Changes over time
    DERIVED = "derived"     # Computed from others


class RelationshipType(Enum):
    """Types of relationships."""
    SPATIAL = "spatial"       # at, near, in, on
    TEMPORAL = "temporal"     # before, after, during
    CAUSAL = "causal"         # causes, enables
    SOCIAL = "social"         # knows, owns, likes
    FUNCTIONAL = "functional" # uses, controls


@dataclass
class Property:
    """A property of an entity."""
    name: str
    value: Any
    property_type: PropertyType = PropertyType.DYNAMIC
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Entity:
    """An entity in the world model."""
    id: str
    name: str
    entity_type: EntityType
    properties: Dict[str, Property] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def set_property(
        self,
        name: str,
        value: Any,
        prop_type: PropertyType = PropertyType.DYNAMIC
    ) -> None:
        """Set a property."""
        self.properties[name] = Property(name, value, prop_type)

    def get_property(self, name: str) -> Optional[Any]:
        """Get property value."""
        prop = self.properties.get(name)
        return prop.value if prop else None

    def has_property(self, name: str) -> bool:
        """Check if entity has property."""
        return name in self.properties


@dataclass
class Relationship:
    """A relationship between entities."""
    id: str
    source_id: str
    target_id: str
    relation_type: RelationshipType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    strength: float = 1.0
    bidirectional: bool = False


# =============================================================================
# WORLD STATE
# =============================================================================

class WorldState:
    """A snapshot of the world state."""

    def __init__(self, state_id: str = None):
        self.id = state_id or str(uuid4())
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.timestamp = datetime.now()

        # Indices
        self.entity_by_type: Dict[EntityType, Set[str]] = defaultdict(set)
        self.relations_by_entity: Dict[str, Set[str]] = defaultdict(set)

    def add_entity(self, entity: Entity) -> None:
        """Add entity to world state."""
        self.entities[entity.id] = entity
        self.entity_by_type[entity.entity_type].add(entity.id)

    def remove_entity(self, entity_id: str) -> None:
        """Remove entity from world state."""
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            self.entity_by_type[entity.entity_type].discard(entity_id)
            del self.entities[entity_id]

            # Remove related relationships
            for rel_id in list(self.relations_by_entity.get(entity_id, set())):
                self.remove_relationship(rel_id)

    def add_relationship(self, relationship: Relationship) -> None:
        """Add relationship to world state."""
        self.relationships[relationship.id] = relationship
        self.relations_by_entity[relationship.source_id].add(relationship.id)
        self.relations_by_entity[relationship.target_id].add(relationship.id)

    def remove_relationship(self, rel_id: str) -> None:
        """Remove relationship from world state."""
        if rel_id in self.relationships:
            rel = self.relationships[rel_id]
            self.relations_by_entity[rel.source_id].discard(rel_id)
            self.relations_by_entity[rel.target_id].discard(rel_id)
            del self.relationships[rel_id]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get entities by type."""
        entity_ids = self.entity_by_type.get(entity_type, set())
        return [self.entities[eid] for eid in entity_ids]

    def get_relationships(self, entity_id: str) -> List[Relationship]:
        """Get relationships involving entity."""
        rel_ids = self.relations_by_entity.get(entity_id, set())
        return [self.relationships[rid] for rid in rel_ids]

    def query_entities(
        self,
        entity_type: EntityType = None,
        property_filter: Dict[str, Any] = None
    ) -> List[Entity]:
        """Query entities with filters."""
        result = []

        if entity_type:
            candidates = self.get_entities_by_type(entity_type)
        else:
            candidates = list(self.entities.values())

        for entity in candidates:
            if property_filter:
                match = all(
                    entity.get_property(k) == v
                    for k, v in property_filter.items()
                )
                if not match:
                    continue
            result.append(entity)

        return result

    def clone(self) -> 'WorldState':
        """Create a deep copy of world state."""
        new_state = WorldState()
        new_state.entities = copy.deepcopy(self.entities)
        new_state.relationships = copy.deepcopy(self.relationships)
        new_state.entity_by_type = copy.deepcopy(self.entity_by_type)
        new_state.relations_by_entity = copy.deepcopy(self.relations_by_entity)
        return new_state

    def diff(self, other: 'WorldState') -> Dict[str, Any]:
        """Compute difference from other state."""
        diff = {
            "added_entities": [],
            "removed_entities": [],
            "modified_entities": [],
            "added_relationships": [],
            "removed_relationships": []
        }

        # Entity changes
        my_ids = set(self.entities.keys())
        other_ids = set(other.entities.keys())

        diff["added_entities"] = list(my_ids - other_ids)
        diff["removed_entities"] = list(other_ids - my_ids)

        for eid in my_ids & other_ids:
            if self.entities[eid].properties != other.entities[eid].properties:
                diff["modified_entities"].append(eid)

        # Relationship changes
        my_rels = set(self.relationships.keys())
        other_rels = set(other.relationships.keys())

        diff["added_relationships"] = list(my_rels - other_rels)
        diff["removed_relationships"] = list(other_rels - my_rels)

        return diff


# =============================================================================
# ACTIONS AND EFFECTS
# =============================================================================

@dataclass
class WorldAction:
    """An action that can modify world state."""
    name: str
    preconditions: List[Callable[[WorldState], bool]] = field(default_factory=list)
    effects: List[Callable[[WorldState], WorldState]] = field(default_factory=list)
    duration: float = 0.0
    probability: float = 1.0

    def is_applicable(self, state: WorldState) -> bool:
        """Check if action is applicable in state."""
        return all(cond(state) for cond in self.preconditions)

    def apply(self, state: WorldState) -> WorldState:
        """Apply action to state."""
        new_state = state.clone()
        for effect in self.effects:
            new_state = effect(new_state)
        return new_state


# =============================================================================
# SIMULATION
# =============================================================================

class WorldSimulator:
    """Simulate world state evolution."""

    def __init__(self):
        self.actions: Dict[str, WorldAction] = {}
        self.dynamics: List[Callable[[WorldState], WorldState]] = []

    def register_action(self, action: WorldAction) -> None:
        """Register an action."""
        self.actions[action.name] = action

    def register_dynamics(
        self,
        update_fn: Callable[[WorldState], WorldState]
    ) -> None:
        """Register a dynamics function."""
        self.dynamics.append(update_fn)

    async def step(
        self,
        state: WorldState,
        action: Optional[str] = None
    ) -> WorldState:
        """Simulate one step."""
        new_state = state.clone()

        # Apply action if specified
        if action and action in self.actions:
            act = self.actions[action]
            if act.is_applicable(new_state):
                new_state = act.apply(new_state)

        # Apply dynamics
        for dynamics in self.dynamics:
            new_state = dynamics(new_state)

        new_state.timestamp = datetime.now()
        return new_state

    async def simulate(
        self,
        initial_state: WorldState,
        action_sequence: List[str],
        steps: int = 10
    ) -> List[WorldState]:
        """Simulate action sequence."""
        trajectory = [initial_state]
        current = initial_state

        for i in range(steps):
            action = action_sequence[i] if i < len(action_sequence) else None
            current = await self.step(current, action)
            trajectory.append(current)

        return trajectory

    async def rollout(
        self,
        state: WorldState,
        policy: Callable[[WorldState], str],
        horizon: int = 10
    ) -> Tuple[List[WorldState], List[str]]:
        """Rollout with policy."""
        states = [state]
        actions = []
        current = state

        for _ in range(horizon):
            action = policy(current)
            actions.append(action)
            current = await self.step(current, action)
            states.append(current)

        return states, actions


# =============================================================================
# PREDICTION
# =============================================================================

class WorldPredictor:
    """Predict future world states."""

    def __init__(self, simulator: WorldSimulator):
        self.simulator = simulator
        self.prediction_cache: Dict[str, List[WorldState]] = {}

    async def predict(
        self,
        state: WorldState,
        actions: List[str],
        num_samples: int = 1
    ) -> List[List[WorldState]]:
        """Predict future states."""
        predictions = []

        for _ in range(num_samples):
            trajectory = await self.simulator.simulate(state, actions, len(actions))
            predictions.append(trajectory)

        return predictions

    async def predict_property(
        self,
        state: WorldState,
        entity_id: str,
        property_name: str,
        horizon: int = 10
    ) -> List[Tuple[datetime, Any]]:
        """Predict property evolution."""
        predictions = []
        current = state.clone()
        current_time = datetime.now()

        for i in range(horizon):
            entity = current.get_entity(entity_id)
            if entity:
                value = entity.get_property(property_name)
                predictions.append((current_time + timedelta(seconds=i), value))

            current = await self.simulator.step(current)

        return predictions

    async def will_hold(
        self,
        state: WorldState,
        condition: Callable[[WorldState], bool],
        horizon: int = 10
    ) -> Tuple[bool, Optional[int]]:
        """Check if condition will hold in future."""
        current = state.clone()

        for i in range(horizon):
            if condition(current):
                return (True, i)
            current = await self.simulator.step(current)

        return (False, None)


# =============================================================================
# COUNTERFACTUAL REASONING
# =============================================================================

class CounterfactualReasoner:
    """Reason about counterfactual scenarios."""

    def __init__(self, simulator: WorldSimulator):
        self.simulator = simulator

    async def what_if(
        self,
        initial_state: WorldState,
        intervention: Callable[[WorldState], WorldState],
        actions: List[str],
        comparison_fn: Callable[[WorldState, WorldState], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate 'what if' scenario."""
        # Actual trajectory
        actual = await self.simulator.simulate(initial_state, actions, len(actions))

        # Counterfactual trajectory
        modified_initial = intervention(initial_state.clone())
        counterfactual = await self.simulator.simulate(modified_initial, actions, len(actions))

        # Compare outcomes
        comparison = comparison_fn(actual[-1], counterfactual[-1])

        return {
            "actual_final": actual[-1],
            "counterfactual_final": counterfactual[-1],
            "comparison": comparison,
            "diverged_at": self._find_divergence(actual, counterfactual)
        }

    def _find_divergence(
        self,
        traj1: List[WorldState],
        traj2: List[WorldState]
    ) -> Optional[int]:
        """Find where trajectories diverged."""
        for i, (s1, s2) in enumerate(zip(traj1, traj2)):
            diff = s1.diff(s2)
            if any(diff.values()):
                return i
        return None

    async def necessary_cause(
        self,
        state: WorldState,
        cause_entity_id: str,
        effect_check: Callable[[WorldState], bool],
        horizon: int = 10
    ) -> bool:
        """Check if entity is necessary cause of effect."""
        # With cause
        with_cause = await self.simulator.simulate(state, [], horizon)
        effect_with = effect_check(with_cause[-1])

        # Without cause (remove entity)
        state_without = state.clone()
        state_without.remove_entity(cause_entity_id)
        without_cause = await self.simulator.simulate(state_without, [], horizon)
        effect_without = effect_check(without_cause[-1])

        # Necessary if effect only with cause
        return effect_with and not effect_without

    async def sufficient_cause(
        self,
        state: WorldState,
        cause_entity_id: str,
        effect_check: Callable[[WorldState], bool],
        horizon: int = 10
    ) -> bool:
        """Check if entity is sufficient cause of effect."""
        # With only cause
        state_only = WorldState()
        if cause_entity_id in state.entities:
            state_only.add_entity(copy.deepcopy(state.entities[cause_entity_id]))

        with_only = await self.simulator.simulate(state_only, [], horizon)
        effect_with_only = effect_check(with_only[-1])

        return effect_with_only


# =============================================================================
# MENTAL SIMULATION
# =============================================================================

class MentalSimulation:
    """Mental simulation for planning and reasoning."""

    def __init__(self, simulator: WorldSimulator):
        self.simulator = simulator
        self.predictor = WorldPredictor(simulator)
        self.counterfactual = CounterfactualReasoner(simulator)

    async def imagine_action_sequence(
        self,
        state: WorldState,
        actions: List[str]
    ) -> Dict[str, Any]:
        """Mentally simulate action sequence."""
        trajectory = await self.simulator.simulate(state, actions, len(actions))

        return {
            "success": True,
            "steps": len(trajectory),
            "final_state": trajectory[-1],
            "state_changes": [
                trajectory[i].diff(trajectory[i+1])
                for i in range(len(trajectory) - 1)
            ]
        }

    async def evaluate_goal(
        self,
        state: WorldState,
        goal_check: Callable[[WorldState], bool],
        action_sequences: List[List[str]]
    ) -> List[Tuple[List[str], bool, int]]:
        """Evaluate action sequences for goal achievement."""
        results = []

        for actions in action_sequences:
            trajectory = await self.simulator.simulate(state, actions, len(actions))

            achieved = False
            steps_to_goal = -1

            for i, s in enumerate(trajectory):
                if goal_check(s):
                    achieved = True
                    steps_to_goal = i
                    break

            results.append((actions, achieved, steps_to_goal))

        return results

    async def find_obstacles(
        self,
        state: WorldState,
        goal_check: Callable[[WorldState], bool],
        actions: List[str]
    ) -> List[Dict[str, Any]]:
        """Find obstacles to goal achievement."""
        trajectory = await self.simulator.simulate(state, actions, len(actions))

        obstacles = []

        for i, s in enumerate(trajectory):
            # Check for entities that might be obstacles
            for entity in s.entities.values():
                # Simulate without this entity
                test_state = s.clone()
                test_state.remove_entity(entity.id)

                if goal_check(test_state):
                    obstacles.append({
                        "step": i,
                        "entity_id": entity.id,
                        "entity_name": entity.name,
                        "reason": "removing enables goal"
                    })

        return obstacles


# =============================================================================
# WORLD MODEL SYSTEM
# =============================================================================

class WorldModelSystem:
    """Main world model system."""

    def __init__(self):
        self.current_state = WorldState()
        self.state_history: List[WorldState] = []
        self.simulator = WorldSimulator()
        self.predictor = WorldPredictor(self.simulator)
        self.mental_sim = MentalSimulation(self.simulator)

    def create_entity(
        self,
        name: str,
        entity_type: EntityType,
        properties: Dict[str, Any] = None
    ) -> Entity:
        """Create and add entity."""
        entity = Entity(
            id=str(uuid4()),
            name=name,
            entity_type=entity_type
        )

        if properties:
            for k, v in properties.items():
                entity.set_property(k, v)

        self.current_state.add_entity(entity)
        return entity

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationshipType,
        name: str,
        properties: Dict[str, Any] = None
    ) -> Relationship:
        """Create and add relationship."""
        rel = Relationship(
            id=str(uuid4()),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            name=name,
            properties=properties or {}
        )

        self.current_state.add_relationship(rel)
        return rel

    def update_entity_property(
        self,
        entity_id: str,
        property_name: str,
        value: Any
    ) -> None:
        """Update entity property."""
        entity = self.current_state.get_entity(entity_id)
        if entity:
            entity.set_property(property_name, value)

    def register_action(self, action: WorldAction) -> None:
        """Register a world action."""
        self.simulator.register_action(action)

    def register_dynamics(
        self,
        update_fn: Callable[[WorldState], WorldState]
    ) -> None:
        """Register world dynamics."""
        self.simulator.register_dynamics(update_fn)

    async def step(self, action: str = None) -> WorldState:
        """Step world forward."""
        self.state_history.append(self.current_state.clone())
        self.current_state = await self.simulator.step(self.current_state, action)
        return self.current_state

    async def predict(
        self,
        actions: List[str],
        num_samples: int = 1
    ) -> List[List[WorldState]]:
        """Predict future states."""
        return await self.predictor.predict(
            self.current_state,
            actions,
            num_samples
        )

    async def what_if(
        self,
        intervention: Callable[[WorldState], WorldState],
        actions: List[str]
    ) -> Dict[str, Any]:
        """Evaluate counterfactual."""
        def compare(s1: WorldState, s2: WorldState) -> Dict[str, Any]:
            return s1.diff(s2)

        return await CounterfactualReasoner(self.simulator).what_if(
            self.current_state,
            intervention,
            actions,
            compare
        )

    async def imagine(self, actions: List[str]) -> Dict[str, Any]:
        """Mentally simulate actions."""
        return await self.mental_sim.imagine_action_sequence(
            self.current_state,
            actions
        )

    def query(
        self,
        entity_type: EntityType = None,
        property_filter: Dict[str, Any] = None
    ) -> List[Entity]:
        """Query current state."""
        return self.current_state.query_entities(entity_type, property_filter)

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "entities": len(self.current_state.entities),
            "relationships": len(self.current_state.relationships),
            "actions": len(self.simulator.actions),
            "history_length": len(self.state_history)
        }


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demo world model system."""
    print("=== World Model System Demo ===\n")

    # Create system
    wms = WorldModelSystem()

    # 1. Create entities
    print("1. Creating Entities:")

    robot = wms.create_entity("robot", EntityType.AGENT, {
        "position": (0, 0),
        "energy": 100,
        "carrying": None
    })
    print(f"   Created: {robot.name} ({robot.entity_type.value})")

    box = wms.create_entity("box", EntityType.OBJECT, {
        "position": (5, 5),
        "weight": 10,
        "movable": True
    })
    print(f"   Created: {box.name} ({box.entity_type.value})")

    goal_loc = wms.create_entity("goal", EntityType.LOCATION, {
        "position": (10, 10)
    })
    print(f"   Created: {goal_loc.name} ({goal_loc.entity_type.value})")

    # 2. Create relationships
    print("\n2. Creating Relationships:")

    rel = wms.create_relationship(
        robot.id,
        box.id,
        RelationshipType.SPATIAL,
        "near",
        {"distance": 5}
    )
    print(f"   Relationship: {robot.name} near {box.name}")

    # 3. Register actions
    print("\n3. Registering Actions:")

    def move_effect(state: WorldState) -> WorldState:
        robot_entity = state.get_entity(robot.id)
        if robot_entity:
            pos = robot_entity.get_property("position")
            new_pos = (pos[0] + 1, pos[1] + 1)
            robot_entity.set_property("position", new_pos)
            robot_entity.set_property("energy", robot_entity.get_property("energy") - 1)
        return state

    move_action = WorldAction(
        name="move",
        preconditions=[lambda s: s.get_entity(robot.id).get_property("energy") > 0],
        effects=[move_effect]
    )
    wms.register_action(move_action)
    print("   Registered: move action")

    def pickup_effect(state: WorldState) -> WorldState:
        robot_entity = state.get_entity(robot.id)
        box_entity = state.get_entity(box.id)
        if robot_entity and box_entity:
            robot_pos = robot_entity.get_property("position")
            box_pos = box_entity.get_property("position")
            if robot_pos == box_pos:
                robot_entity.set_property("carrying", box.id)
                box_entity.set_property("carried_by", robot.id)
        return state

    pickup_action = WorldAction(
        name="pickup",
        effects=[pickup_effect]
    )
    wms.register_action(pickup_action)
    print("   Registered: pickup action")

    # 4. Simulate
    print("\n4. Simulation:")

    initial_pos = wms.current_state.get_entity(robot.id).get_property("position")
    print(f"   Initial robot position: {initial_pos}")

    for i in range(3):
        await wms.step("move")
        pos = wms.current_state.get_entity(robot.id).get_property("position")
        energy = wms.current_state.get_entity(robot.id).get_property("energy")
        print(f"   Step {i+1}: position={pos}, energy={energy}")

    # 5. Prediction
    print("\n5. Prediction:")

    predictions = await wms.predict(["move", "move", "move"])
    print(f"   Predicted {len(predictions[0])} states")

    final_pos = predictions[0][-1].get_entity(robot.id).get_property("position")
    print(f"   Predicted final position: {final_pos}")

    # 6. Mental simulation
    print("\n6. Mental Simulation:")

    imagination = await wms.imagine(["move", "move", "pickup"])
    print(f"   Imagined {imagination['steps']} steps")
    print(f"   State changes: {len(imagination['state_changes'])}")

    # 7. Counterfactual reasoning
    print("\n7. Counterfactual Reasoning:")

    def double_energy(state: WorldState) -> WorldState:
        robot_entity = state.get_entity(robot.id)
        if robot_entity:
            robot_entity.set_property("energy", 200)
        return state

    result = await wms.what_if(double_energy, ["move"] * 5)
    actual_energy = result["actual_final"].get_entity(robot.id).get_property("energy")
    cf_energy = result["counterfactual_final"].get_entity(robot.id).get_property("energy")
    print(f"   Actual energy after 5 moves: {actual_energy}")
    print(f"   Counterfactual energy (started with 200): {cf_energy}")

    # 8. Query
    print("\n8. Querying World State:")

    agents = wms.query(EntityType.AGENT)
    print(f"   Agents: {[a.name for a in agents]}")

    objects = wms.query(EntityType.OBJECT)
    print(f"   Objects: {[o.name for o in objects]}")

    movable = wms.query(EntityType.OBJECT, {"movable": True})
    print(f"   Movable objects: {[o.name for o in movable]}")

    # 9. Status
    print("\n9. System Status:")
    status = wms.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
