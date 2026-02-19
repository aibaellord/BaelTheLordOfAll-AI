"""
⚡ WORLD MODEL ⚡
================
Comprehensive world state representation.

Features:
- Entity modeling with rich attributes
- Relation networks
- Spatial reasoning
- Temporal evolution
- Hierarchical world regions
"""

import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid


class EntityType(Enum):
    """Types of world entities"""
    OBJECT = auto()      # Physical objects
    AGENT = auto()       # Active agents
    LOCATION = auto()    # Places
    EVENT = auto()       # Temporal events
    CONCEPT = auto()     # Abstract concepts
    PROCESS = auto()     # Ongoing processes
    STATE = auto()       # Entity states
    BOUNDARY = auto()    # Spatial boundaries


class RelationType(Enum):
    """Types of relations between entities"""
    # Spatial
    CONTAINS = auto()
    NEAR = auto()
    ABOVE = auto()
    BELOW = auto()

    # Temporal
    BEFORE = auto()
    AFTER = auto()
    DURING = auto()

    # Causal
    CAUSES = auto()
    ENABLES = auto()
    PREVENTS = auto()

    # Compositional
    PART_OF = auto()
    HAS_PART = auto()
    INSTANCE_OF = auto()

    # Semantic
    SIMILAR_TO = auto()
    OPPOSITE_OF = auto()
    RELATED_TO = auto()

    # Agentive
    OWNS = auto()
    USES = auto()
    CREATED_BY = auto()


@dataclass
class EntityState:
    """State of an entity at a point in time"""
    properties: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Tuple[float, ...]] = None
    velocity: Optional[Tuple[float, ...]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def get(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def set(self, key: str, value: Any):
        self.properties[key] = value


@dataclass
class Entity:
    """
    World entity with rich properties.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entity_type: EntityType = EntityType.OBJECT

    # Current state
    state: EntityState = field(default_factory=EntityState)

    # History
    state_history: List[EntityState] = field(default_factory=list)

    # Embedding for similarity
    embedding: Optional[np.ndarray] = None

    # Metadata
    created: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_state(self, **properties):
        """Update entity state"""
        # Save current to history
        self.state_history.append(self.state)

        # Create new state
        new_props = dict(self.state.properties)
        new_props.update(properties)

        self.state = EntityState(
            properties=new_props,
            position=self.state.position,
            velocity=self.state.velocity
        )

    def set_position(self, position: Tuple[float, ...]):
        """Set entity position"""
        old_pos = self.state.position
        self.state.position = position

        # Calculate velocity if position changed
        if old_pos is not None:
            dt = 1.0  # Time unit
            velocity = tuple(
                (p - o) / dt
                for p, o in zip(position, old_pos)
            )
            self.state.velocity = velocity

    def get_state_at(self, timestamp: datetime) -> Optional[EntityState]:
        """Get state at specific time"""
        # Check current state
        if self.state.timestamp <= timestamp:
            return self.state

        # Search history
        for state in reversed(self.state_history):
            if state.timestamp <= timestamp:
                return state

        return None


@dataclass
class Relation:
    """Relation between entities"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO

    # Strength and confidence
    strength: float = 1.0
    confidence: float = 1.0

    # Temporal bounds
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid_at(self, timestamp: datetime) -> bool:
        """Check if relation is valid at time"""
        if self.valid_from and timestamp < self.valid_from:
            return False
        if self.valid_until and timestamp > self.valid_until:
            return False
        return True


@dataclass
class WorldRegion:
    """A region in the world"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Bounds (min/max for each dimension)
    bounds: List[Tuple[float, float]] = field(default_factory=list)

    # Contained entities
    entity_ids: Set[str] = field(default_factory=set)

    # Sub-regions
    sub_regions: List['WorldRegion'] = field(default_factory=list)

    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)

    def contains_point(self, point: Tuple[float, ...]) -> bool:
        """Check if point is in region"""
        if len(point) != len(self.bounds):
            return False

        for p, (min_b, max_b) in zip(point, self.bounds):
            if p < min_b or p > max_b:
                return False

        return True

    def get_volume(self) -> float:
        """Get region volume"""
        volume = 1.0
        for min_b, max_b in self.bounds:
            volume *= (max_b - min_b)
        return volume


@dataclass
class WorldState:
    """Complete world state at a moment"""
    timestamp: datetime = field(default_factory=datetime.now)
    entity_states: Dict[str, EntityState] = field(default_factory=dict)
    active_relations: Set[str] = field(default_factory=set)
    global_properties: Dict[str, Any] = field(default_factory=dict)

    def copy(self) -> 'WorldState':
        """Create copy of world state"""
        return WorldState(
            timestamp=self.timestamp,
            entity_states={
                k: EntityState(
                    properties=dict(v.properties),
                    position=v.position,
                    velocity=v.velocity,
                    timestamp=v.timestamp
                )
                for k, v in self.entity_states.items()
            },
            active_relations=set(self.active_relations),
            global_properties=dict(self.global_properties)
        )


class WorldModel:
    """
    Comprehensive world model.

    Maintains entities, relations, and world state.
    Supports temporal reasoning and prediction.
    """

    def __init__(self, dimensions: int = 3):
        self.dimensions = dimensions

        # Core data
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.regions: Dict[str, WorldRegion] = {}

        # Indexes
        self.by_type: Dict[EntityType, Set[str]] = defaultdict(set)
        self.by_name: Dict[str, str] = {}  # name -> id

        # Relations index
        self.outgoing: Dict[str, Set[str]] = defaultdict(set)  # entity -> relations
        self.incoming: Dict[str, Set[str]] = defaultdict(set)

        # State history
        self.state_history: List[WorldState] = []
        self.current_time: datetime = datetime.now()

    def add_entity(
        self,
        name: str,
        entity_type: EntityType = EntityType.OBJECT,
        properties: Dict[str, Any] = None,
        position: Tuple[float, ...] = None
    ) -> Entity:
        """Add entity to world"""
        entity = Entity(
            name=name,
            entity_type=entity_type,
            state=EntityState(
                properties=properties or {},
                position=position
            )
        )

        self.entities[entity.id] = entity
        self.by_type[entity_type].add(entity.id)
        self.by_name[name] = entity.id

        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        return self.entities.get(entity_id)

    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Get entity by name"""
        entity_id = self.by_name.get(name)
        if entity_id:
            return self.entities.get(entity_id)
        return None

    def remove_entity(self, entity_id: str):
        """Remove entity and its relations"""
        if entity_id not in self.entities:
            return

        entity = self.entities[entity_id]

        # Remove from indexes
        self.by_type[entity.entity_type].discard(entity_id)
        if entity.name in self.by_name:
            del self.by_name[entity.name]

        # Remove related relations
        for rel_id in list(self.outgoing.get(entity_id, set())):
            self._remove_relation(rel_id)
        for rel_id in list(self.incoming.get(entity_id, set())):
            self._remove_relation(rel_id)

        del self.entities[entity_id]

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0,
        confidence: float = 1.0
    ) -> Optional[Relation]:
        """Add relation between entities"""
        if source_id not in self.entities or target_id not in self.entities:
            return None

        relation = Relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
            confidence=confidence,
            valid_from=self.current_time
        )

        self.relations[relation.id] = relation
        self.outgoing[source_id].add(relation.id)
        self.incoming[target_id].add(relation.id)

        return relation

    def _remove_relation(self, relation_id: str):
        """Remove relation"""
        if relation_id not in self.relations:
            return

        relation = self.relations[relation_id]
        self.outgoing[relation.source_id].discard(relation_id)
        self.incoming[relation.target_id].discard(relation_id)
        del self.relations[relation_id]

    def get_relations(
        self,
        entity_id: str,
        direction: str = 'both',
        relation_type: RelationType = None
    ) -> List[Relation]:
        """Get relations for entity"""
        relations = []

        if direction in ['out', 'both']:
            for rel_id in self.outgoing.get(entity_id, set()):
                rel = self.relations.get(rel_id)
                if rel and (relation_type is None or rel.relation_type == relation_type):
                    relations.append(rel)

        if direction in ['in', 'both']:
            for rel_id in self.incoming.get(entity_id, set()):
                rel = self.relations.get(rel_id)
                if rel and (relation_type is None or rel.relation_type == relation_type):
                    relations.append(rel)

        return relations

    def add_region(
        self,
        name: str,
        bounds: List[Tuple[float, float]]
    ) -> WorldRegion:
        """Add world region"""
        region = WorldRegion(name=name, bounds=bounds)
        self.regions[region.id] = region

        # Assign entities to region
        for entity_id, entity in self.entities.items():
            if entity.state.position:
                if region.contains_point(entity.state.position):
                    region.entity_ids.add(entity_id)

        return region

    def get_entities_in_region(
        self,
        region_id: str
    ) -> List[Entity]:
        """Get entities in region"""
        region = self.regions.get(region_id)
        if not region:
            return []

        return [
            self.entities[eid]
            for eid in region.entity_ids
            if eid in self.entities
        ]

    def get_nearby_entities(
        self,
        entity_id: str,
        radius: float
    ) -> List[Tuple[Entity, float]]:
        """Get entities within radius"""
        entity = self.entities.get(entity_id)
        if not entity or not entity.state.position:
            return []

        nearby = []
        pos = np.array(entity.state.position)

        for other_id, other in self.entities.items():
            if other_id == entity_id:
                continue
            if not other.state.position:
                continue

            other_pos = np.array(other.state.position)
            distance = np.linalg.norm(pos - other_pos)

            if distance <= radius:
                nearby.append((other, distance))

        nearby.sort(key=lambda x: x[1])
        return nearby

    def get_current_state(self) -> WorldState:
        """Get current world state"""
        return WorldState(
            timestamp=self.current_time,
            entity_states={
                eid: EntityState(
                    properties=dict(entity.state.properties),
                    position=entity.state.position,
                    velocity=entity.state.velocity,
                    timestamp=entity.state.timestamp
                )
                for eid, entity in self.entities.items()
            },
            active_relations=set(self.relations.keys()),
            global_properties={}
        )

    def save_state(self):
        """Save current state to history"""
        state = self.get_current_state()
        self.state_history.append(state)

    def restore_state(self, state: WorldState):
        """Restore world to saved state"""
        self.current_time = state.timestamp

        for entity_id, entity_state in state.entity_states.items():
            if entity_id in self.entities:
                entity = self.entities[entity_id]
                entity.state = EntityState(
                    properties=dict(entity_state.properties),
                    position=entity_state.position,
                    velocity=entity_state.velocity,
                    timestamp=entity_state.timestamp
                )

    def query_entities(
        self,
        entity_type: EntityType = None,
        properties: Dict[str, Any] = None,
        near: Tuple[float, ...] = None,
        radius: float = None
    ) -> List[Entity]:
        """Query entities matching criteria"""
        candidates = list(self.entities.values())

        if entity_type:
            candidates = [e for e in candidates if e.entity_type == entity_type]

        if properties:
            for key, value in properties.items():
                candidates = [
                    e for e in candidates
                    if e.state.get(key) == value
                ]

        if near is not None and radius is not None:
            near_pos = np.array(near)
            filtered = []
            for e in candidates:
                if e.state.position:
                    dist = np.linalg.norm(np.array(e.state.position) - near_pos)
                    if dist <= radius:
                        filtered.append(e)
            candidates = filtered

        return candidates

    def get_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """Find path between entities via relations"""
        if source_id not in self.entities or target_id not in self.entities:
            return None

        # BFS
        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)

            if current == target_id:
                return path

            if len(path) >= max_depth:
                continue

            # Explore neighbors
            for rel_id in self.outgoing.get(current, set()):
                rel = self.relations.get(rel_id)
                if rel and rel.target_id not in visited:
                    visited.add(rel.target_id)
                    queue.append((rel.target_id, path + [rel.target_id]))

            for rel_id in self.incoming.get(current, set()):
                rel = self.relations.get(rel_id)
                if rel and rel.source_id not in visited:
                    visited.add(rel.source_id)
                    queue.append((rel.source_id, path + [rel.source_id]))

        return None


# Export all
__all__ = [
    'EntityType',
    'RelationType',
    'EntityState',
    'Entity',
    'Relation',
    'WorldRegion',
    'WorldState',
    'WorldModel',
]
