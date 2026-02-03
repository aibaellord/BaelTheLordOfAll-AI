#!/usr/bin/env python3
"""
BAEL - Ontology Manager
Advanced ontological reasoning and semantic knowledge representation.

Features:
- Class hierarchies
- Property definitions
- Instance management
- Inheritance reasoning
- Semantic relationships
- Constraint validation
- Ontology alignment
- Query processing
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
from typing import (Any, Callable, Dict, Generic, List, Optional, Set, Tuple,
                    Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class EntityType(Enum):
    """Types of ontological entities."""
    CLASS = "class"
    PROPERTY = "property"
    INSTANCE = "instance"
    RELATION = "relation"
    AXIOM = "axiom"


class PropertyType(Enum):
    """Types of properties."""
    OBJECT_PROPERTY = "object_property"
    DATA_PROPERTY = "data_property"
    ANNOTATION_PROPERTY = "annotation_property"
    TRANSITIVE_PROPERTY = "transitive_property"
    SYMMETRIC_PROPERTY = "symmetric_property"
    FUNCTIONAL_PROPERTY = "functional_property"
    INVERSE_FUNCTIONAL = "inverse_functional"


class RelationType(Enum):
    """Types of relations."""
    IS_A = "is_a"
    PART_OF = "part_of"
    HAS_PART = "has_part"
    INSTANCE_OF = "instance_of"
    EQUIVALENT_TO = "equivalent_to"
    DISJOINT_WITH = "disjoint_with"
    RELATED_TO = "related_to"


class ConstraintType(Enum):
    """Types of constraints."""
    CARDINALITY = "cardinality"
    VALUE_RESTRICTION = "value_restriction"
    TYPE_RESTRICTION = "type_restriction"
    DISJOINTNESS = "disjointness"
    SYMMETRY = "symmetry"


class InferenceType(Enum):
    """Types of inferences."""
    SUBSUMPTION = "subsumption"
    INSTANTIATION = "instantiation"
    PROPERTY_INHERITANCE = "property_inheritance"
    TRANSITIVITY = "transitivity"
    EQUIVALENCE = "equivalence"


class QueryType(Enum):
    """Types of ontology queries."""
    CLASS_QUERY = "class_query"
    INSTANCE_QUERY = "instance_query"
    PROPERTY_QUERY = "property_query"
    SPARQL_LIKE = "sparql_like"
    PATH_QUERY = "path_query"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class OntologyClass:
    """An ontology class."""
    class_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    parent_classes: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
    annotations: Dict[str, str] = field(default_factory=dict)
    is_abstract: bool = False


@dataclass
class OntologyProperty:
    """An ontology property."""
    property_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    property_type: PropertyType = PropertyType.DATA_PROPERTY
    domain: List[str] = field(default_factory=list)  # Class IDs
    range_type: str = ""  # Class ID or data type
    is_inherited: bool = True
    inverse_property: Optional[str] = None


@dataclass
class OntologyInstance:
    """An instance in the ontology."""
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    class_id: str = ""
    property_values: Dict[str, Any] = field(default_factory=dict)
    relations: List[Tuple[str, str]] = field(default_factory=list)  # (relation, target_id)


@dataclass
class OntologyRelation:
    """A relation between entities."""
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Constraint:
    """An ontology constraint."""
    constraint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    constraint_type: ConstraintType = ConstraintType.TYPE_RESTRICTION
    applies_to: str = ""  # Class or property ID
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


@dataclass
class Inference:
    """An inference result."""
    inference_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    inference_type: InferenceType = InferenceType.SUBSUMPTION
    subject: str = ""
    predicate: str = ""
    object_: str = ""
    confidence: float = 1.0
    justification: str = ""


@dataclass
class QueryResult:
    """Result of an ontology query."""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_type: QueryType = QueryType.CLASS_QUERY
    bindings: List[Dict[str, Any]] = field(default_factory=list)
    count: int = 0
    execution_time: float = 0.0


# =============================================================================
# CLASS HIERARCHY
# =============================================================================

class ClassHierarchy:
    """Manage class hierarchies."""

    def __init__(self):
        self._classes: Dict[str, OntologyClass] = {}
        self._subclass_map: Dict[str, Set[str]] = defaultdict(set)
        self._superclass_map: Dict[str, Set[str]] = defaultdict(set)

    def add_class(self, ontology_class: OntologyClass) -> None:
        """Add a class to the hierarchy."""
        self._classes[ontology_class.class_id] = ontology_class

        for parent_id in ontology_class.parent_classes:
            self._subclass_map[parent_id].add(ontology_class.class_id)
            self._superclass_map[ontology_class.class_id].add(parent_id)

    def get_class(self, class_id: str) -> Optional[OntologyClass]:
        """Get class by ID."""
        return self._classes.get(class_id)

    def get_class_by_name(self, name: str) -> Optional[OntologyClass]:
        """Get class by name."""
        for cls in self._classes.values():
            if cls.name == name:
                return cls
        return None

    def get_subclasses(
        self,
        class_id: str,
        direct_only: bool = False
    ) -> Set[str]:
        """Get subclasses of a class."""
        if direct_only:
            return self._subclass_map.get(class_id, set()).copy()

        # Transitive closure
        result = set()
        queue = deque([class_id])

        while queue:
            current = queue.popleft()
            for subclass in self._subclass_map.get(current, set()):
                if subclass not in result:
                    result.add(subclass)
                    queue.append(subclass)

        return result

    def get_superclasses(
        self,
        class_id: str,
        direct_only: bool = False
    ) -> Set[str]:
        """Get superclasses of a class."""
        if direct_only:
            return self._superclass_map.get(class_id, set()).copy()

        # Transitive closure
        result = set()
        queue = deque([class_id])

        while queue:
            current = queue.popleft()
            for superclass in self._superclass_map.get(current, set()):
                if superclass not in result:
                    result.add(superclass)
                    queue.append(superclass)

        return result

    def is_subclass_of(
        self,
        subclass_id: str,
        superclass_id: str
    ) -> bool:
        """Check if one class is subclass of another."""
        return superclass_id in self.get_superclasses(subclass_id)

    def get_common_ancestors(
        self,
        class_id1: str,
        class_id2: str
    ) -> Set[str]:
        """Get common ancestors of two classes."""
        ancestors1 = self.get_superclasses(class_id1)
        ancestors1.add(class_id1)
        ancestors2 = self.get_superclasses(class_id2)
        ancestors2.add(class_id2)
        return ancestors1 & ancestors2

    def get_lowest_common_ancestor(
        self,
        class_id1: str,
        class_id2: str
    ) -> Optional[str]:
        """Get lowest common ancestor."""
        common = self.get_common_ancestors(class_id1, class_id2)
        if not common:
            return None

        # Find the one with most ancestors (lowest in hierarchy)
        best = None
        best_depth = -1

        for cls_id in common:
            depth = len(self.get_superclasses(cls_id))
            if depth > best_depth:
                best_depth = depth
                best = cls_id

        return best


# =============================================================================
# PROPERTY MANAGER
# =============================================================================

class PropertyManager:
    """Manage ontology properties."""

    def __init__(self, hierarchy: ClassHierarchy):
        self._hierarchy = hierarchy
        self._properties: Dict[str, OntologyProperty] = {}
        self._class_properties: Dict[str, Set[str]] = defaultdict(set)

    def add_property(self, prop: OntologyProperty) -> None:
        """Add a property."""
        self._properties[prop.property_id] = prop

        for domain_class in prop.domain:
            self._class_properties[domain_class].add(prop.property_id)

    def get_property(self, property_id: str) -> Optional[OntologyProperty]:
        """Get property by ID."""
        return self._properties.get(property_id)

    def get_property_by_name(self, name: str) -> Optional[OntologyProperty]:
        """Get property by name."""
        for prop in self._properties.values():
            if prop.name == name:
                return prop
        return None

    def get_properties_for_class(
        self,
        class_id: str,
        include_inherited: bool = True
    ) -> Set[str]:
        """Get all properties applicable to a class."""
        result = self._class_properties.get(class_id, set()).copy()

        if include_inherited:
            for superclass in self._hierarchy.get_superclasses(class_id):
                result |= self._class_properties.get(superclass, set())

        return result

    def get_inverse_property(
        self,
        property_id: str
    ) -> Optional[OntologyProperty]:
        """Get inverse property."""
        prop = self._properties.get(property_id)
        if prop and prop.inverse_property:
            return self._properties.get(prop.inverse_property)
        return None

    def is_transitive(self, property_id: str) -> bool:
        """Check if property is transitive."""
        prop = self._properties.get(property_id)
        return prop and prop.property_type == PropertyType.TRANSITIVE_PROPERTY

    def is_symmetric(self, property_id: str) -> bool:
        """Check if property is symmetric."""
        prop = self._properties.get(property_id)
        return prop and prop.property_type == PropertyType.SYMMETRIC_PROPERTY


# =============================================================================
# INSTANCE MANAGER
# =============================================================================

class InstanceManager:
    """Manage ontology instances."""

    def __init__(
        self,
        hierarchy: ClassHierarchy,
        property_manager: PropertyManager
    ):
        self._hierarchy = hierarchy
        self._property_manager = property_manager
        self._instances: Dict[str, OntologyInstance] = {}
        self._class_instances: Dict[str, Set[str]] = defaultdict(set)

    def add_instance(self, instance: OntologyInstance) -> None:
        """Add an instance."""
        self._instances[instance.instance_id] = instance
        self._class_instances[instance.class_id].add(instance.instance_id)

    def get_instance(self, instance_id: str) -> Optional[OntologyInstance]:
        """Get instance by ID."""
        return self._instances.get(instance_id)

    def get_instance_by_name(self, name: str) -> Optional[OntologyInstance]:
        """Get instance by name."""
        for inst in self._instances.values():
            if inst.name == name:
                return inst
        return None

    def get_instances_of_class(
        self,
        class_id: str,
        include_subclasses: bool = True
    ) -> Set[str]:
        """Get instances of a class."""
        result = self._class_instances.get(class_id, set()).copy()

        if include_subclasses:
            for subclass in self._hierarchy.get_subclasses(class_id):
                result |= self._class_instances.get(subclass, set())

        return result

    def is_instance_of(
        self,
        instance_id: str,
        class_id: str
    ) -> bool:
        """Check if instance belongs to class."""
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        if instance.class_id == class_id:
            return True

        return self._hierarchy.is_subclass_of(instance.class_id, class_id)

    def set_property_value(
        self,
        instance_id: str,
        property_name: str,
        value: Any
    ) -> bool:
        """Set property value on instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        instance.property_values[property_name] = value
        return True

    def get_property_value(
        self,
        instance_id: str,
        property_name: str
    ) -> Optional[Any]:
        """Get property value from instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None

        return instance.property_values.get(property_name)

    def add_relation(
        self,
        source_id: str,
        relation: str,
        target_id: str
    ) -> bool:
        """Add relation between instances."""
        source = self._instances.get(source_id)
        if not source:
            return False

        source.relations.append((relation, target_id))
        return True

    def get_related_instances(
        self,
        instance_id: str,
        relation: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """Get related instances."""
        instance = self._instances.get(instance_id)
        if not instance:
            return []

        if relation:
            return [
                (rel, target)
                for rel, target in instance.relations
                if rel == relation
            ]
        return instance.relations.copy()


# =============================================================================
# CONSTRAINT VALIDATOR
# =============================================================================

class ConstraintValidator:
    """Validate ontology constraints."""

    def __init__(
        self,
        hierarchy: ClassHierarchy,
        property_manager: PropertyManager,
        instance_manager: InstanceManager
    ):
        self._hierarchy = hierarchy
        self._property_manager = property_manager
        self._instance_manager = instance_manager
        self._constraints: Dict[str, Constraint] = {}

    def add_constraint(self, constraint: Constraint) -> None:
        """Add a constraint."""
        self._constraints[constraint.constraint_id] = constraint

    def get_constraint(self, constraint_id: str) -> Optional[Constraint]:
        """Get constraint by ID."""
        return self._constraints.get(constraint_id)

    def validate_instance(
        self,
        instance: OntologyInstance
    ) -> List[Tuple[str, str]]:
        """Validate instance against constraints. Returns list of violations."""
        violations = []

        for constraint in self._constraints.values():
            if constraint.applies_to == instance.class_id:
                violation = self._check_constraint(instance, constraint)
                if violation:
                    violations.append(violation)

        return violations

    def _check_constraint(
        self,
        instance: OntologyInstance,
        constraint: Constraint
    ) -> Optional[Tuple[str, str]]:
        """Check a single constraint."""
        if constraint.constraint_type == ConstraintType.CARDINALITY:
            return self._check_cardinality(instance, constraint)
        elif constraint.constraint_type == ConstraintType.VALUE_RESTRICTION:
            return self._check_value_restriction(instance, constraint)
        elif constraint.constraint_type == ConstraintType.TYPE_RESTRICTION:
            return self._check_type_restriction(instance, constraint)
        return None

    def _check_cardinality(
        self,
        instance: OntologyInstance,
        constraint: Constraint
    ) -> Optional[Tuple[str, str]]:
        """Check cardinality constraint."""
        property_name = constraint.parameters.get("property")
        min_card = constraint.parameters.get("min", 0)
        max_card = constraint.parameters.get("max", float('inf'))

        value = instance.property_values.get(property_name)

        if value is None:
            count = 0
        elif isinstance(value, list):
            count = len(value)
        else:
            count = 1

        if count < min_card or count > max_card:
            return (
                constraint.constraint_id,
                constraint.error_message or f"Cardinality violation for {property_name}"
            )
        return None

    def _check_value_restriction(
        self,
        instance: OntologyInstance,
        constraint: Constraint
    ) -> Optional[Tuple[str, str]]:
        """Check value restriction constraint."""
        property_name = constraint.parameters.get("property")
        allowed_values = constraint.parameters.get("allowed_values", [])

        value = instance.property_values.get(property_name)

        if value is not None and value not in allowed_values:
            return (
                constraint.constraint_id,
                constraint.error_message or f"Value restriction violation for {property_name}"
            )
        return None

    def _check_type_restriction(
        self,
        instance: OntologyInstance,
        constraint: Constraint
    ) -> Optional[Tuple[str, str]]:
        """Check type restriction constraint."""
        property_name = constraint.parameters.get("property")
        expected_type = constraint.parameters.get("type")

        value = instance.property_values.get(property_name)

        if value is not None:
            actual_type = type(value).__name__
            if actual_type != expected_type:
                return (
                    constraint.constraint_id,
                    constraint.error_message or f"Type restriction violation for {property_name}"
                )
        return None

    def validate_all_instances(self) -> Dict[str, List[Tuple[str, str]]]:
        """Validate all instances."""
        results = {}

        for instance in self._instance_manager._instances.values():
            violations = self.validate_instance(instance)
            if violations:
                results[instance.instance_id] = violations

        return results


# =============================================================================
# REASONER
# =============================================================================

class OntologyReasoner:
    """Ontological reasoning engine."""

    def __init__(
        self,
        hierarchy: ClassHierarchy,
        property_manager: PropertyManager,
        instance_manager: InstanceManager
    ):
        self._hierarchy = hierarchy
        self._property_manager = property_manager
        self._instance_manager = instance_manager
        self._inferences: List[Inference] = []

    def infer_class_membership(
        self,
        instance_id: str
    ) -> List[Inference]:
        """Infer all class memberships for an instance."""
        instance = self._instance_manager.get_instance(instance_id)
        if not instance:
            return []

        inferences = []

        # Direct class membership
        inferences.append(Inference(
            inference_type=InferenceType.INSTANTIATION,
            subject=instance_id,
            predicate="instance_of",
            object_=instance.class_id,
            confidence=1.0,
            justification="Direct class assignment"
        ))

        # Infer superclass memberships
        for superclass in self._hierarchy.get_superclasses(instance.class_id):
            inferences.append(Inference(
                inference_type=InferenceType.SUBSUMPTION,
                subject=instance_id,
                predicate="instance_of",
                object_=superclass,
                confidence=1.0,
                justification=f"Inherited from {instance.class_id}"
            ))

        return inferences

    def infer_property_values(
        self,
        instance_id: str
    ) -> List[Inference]:
        """Infer property values through inheritance."""
        instance = self._instance_manager.get_instance(instance_id)
        if not instance:
            return []

        inferences = []

        # Get all applicable properties
        properties = self._property_manager.get_properties_for_class(
            instance.class_id,
            include_inherited=True
        )

        for prop_id in properties:
            prop = self._property_manager.get_property(prop_id)
            if prop:
                inferences.append(Inference(
                    inference_type=InferenceType.PROPERTY_INHERITANCE,
                    subject=instance_id,
                    predicate="has_property",
                    object_=prop.name,
                    confidence=1.0,
                    justification="Property domain includes class"
                ))

        return inferences

    def infer_transitive_relations(
        self,
        property_id: str
    ) -> List[Inference]:
        """Infer transitive relations."""
        if not self._property_manager.is_transitive(property_id):
            return []

        prop = self._property_manager.get_property(property_id)
        if not prop:
            return []

        inferences = []

        # Build relation graph
        relation_graph: Dict[str, Set[str]] = defaultdict(set)

        for instance in self._instance_manager._instances.values():
            for rel, target in instance.relations:
                if rel == prop.name:
                    relation_graph[instance.instance_id].add(target)

        # Compute transitive closure
        for source in list(relation_graph.keys()):
            visited = set()
            queue = deque(relation_graph[source])

            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)

                # Check if this is a new inferred relation
                if current not in relation_graph[source]:
                    inferences.append(Inference(
                        inference_type=InferenceType.TRANSITIVITY,
                        subject=source,
                        predicate=prop.name,
                        object_=current,
                        confidence=0.95,
                        justification=f"Transitive closure of {prop.name}"
                    ))

                for next_target in relation_graph.get(current, set()):
                    if next_target not in visited:
                        queue.append(next_target)

        return inferences

    def infer_symmetric_relations(
        self,
        property_id: str
    ) -> List[Inference]:
        """Infer symmetric relations."""
        if not self._property_manager.is_symmetric(property_id):
            return []

        prop = self._property_manager.get_property(property_id)
        if not prop:
            return []

        inferences = []
        existing_pairs: Set[Tuple[str, str]] = set()

        # Collect existing relations
        for instance in self._instance_manager._instances.values():
            for rel, target in instance.relations:
                if rel == prop.name:
                    existing_pairs.add((instance.instance_id, target))

        # Infer symmetric relations
        for source, target in existing_pairs:
            if (target, source) not in existing_pairs:
                inferences.append(Inference(
                    inference_type=InferenceType.EQUIVALENCE,
                    subject=target,
                    predicate=prop.name,
                    object_=source,
                    confidence=1.0,
                    justification=f"Symmetric property {prop.name}"
                ))

        return inferences

    def run_all_inferences(self) -> List[Inference]:
        """Run all inference types."""
        inferences = []

        # Class membership inferences
        for instance_id in self._instance_manager._instances:
            inferences.extend(self.infer_class_membership(instance_id))
            inferences.extend(self.infer_property_values(instance_id))

        # Property-based inferences
        for prop_id in self._property_manager._properties:
            inferences.extend(self.infer_transitive_relations(prop_id))
            inferences.extend(self.infer_symmetric_relations(prop_id))

        self._inferences = inferences
        return inferences


# =============================================================================
# QUERY PROCESSOR
# =============================================================================

class QueryProcessor:
    """Process ontology queries."""

    def __init__(
        self,
        hierarchy: ClassHierarchy,
        property_manager: PropertyManager,
        instance_manager: InstanceManager
    ):
        self._hierarchy = hierarchy
        self._property_manager = property_manager
        self._instance_manager = instance_manager

    def query_instances_by_class(
        self,
        class_name: str,
        include_subclasses: bool = True
    ) -> QueryResult:
        """Query instances by class."""
        start_time = time.time()

        cls = self._hierarchy.get_class_by_name(class_name)
        if not cls:
            return QueryResult(count=0, execution_time=time.time() - start_time)

        instances = self._instance_manager.get_instances_of_class(
            cls.class_id,
            include_subclasses
        )

        bindings = []
        for inst_id in instances:
            inst = self._instance_manager.get_instance(inst_id)
            if inst:
                bindings.append({
                    "instance_id": inst_id,
                    "name": inst.name,
                    "class": inst.class_id,
                    "properties": inst.property_values
                })

        return QueryResult(
            query_type=QueryType.INSTANCE_QUERY,
            bindings=bindings,
            count=len(bindings),
            execution_time=time.time() - start_time
        )

    def query_by_property_value(
        self,
        property_name: str,
        value: Any
    ) -> QueryResult:
        """Query instances by property value."""
        start_time = time.time()

        bindings = []

        for inst in self._instance_manager._instances.values():
            if inst.property_values.get(property_name) == value:
                bindings.append({
                    "instance_id": inst.instance_id,
                    "name": inst.name,
                    "class": inst.class_id,
                    "matched_property": property_name,
                    "matched_value": value
                })

        return QueryResult(
            query_type=QueryType.PROPERTY_QUERY,
            bindings=bindings,
            count=len(bindings),
            execution_time=time.time() - start_time
        )

    def query_related_instances(
        self,
        instance_name: str,
        relation: Optional[str] = None
    ) -> QueryResult:
        """Query instances related to a given instance."""
        start_time = time.time()

        instance = self._instance_manager.get_instance_by_name(instance_name)
        if not instance:
            return QueryResult(count=0, execution_time=time.time() - start_time)

        related = self._instance_manager.get_related_instances(
            instance.instance_id,
            relation
        )

        bindings = []
        for rel, target_id in related:
            target = self._instance_manager.get_instance(target_id)
            if target:
                bindings.append({
                    "source": instance_name,
                    "relation": rel,
                    "target_id": target_id,
                    "target_name": target.name
                })

        return QueryResult(
            query_type=QueryType.PATH_QUERY,
            bindings=bindings,
            count=len(bindings),
            execution_time=time.time() - start_time
        )

    def query_subclasses(
        self,
        class_name: str,
        direct_only: bool = False
    ) -> QueryResult:
        """Query subclasses of a class."""
        start_time = time.time()

        cls = self._hierarchy.get_class_by_name(class_name)
        if not cls:
            return QueryResult(count=0, execution_time=time.time() - start_time)

        subclasses = self._hierarchy.get_subclasses(cls.class_id, direct_only)

        bindings = []
        for sub_id in subclasses:
            sub = self._hierarchy.get_class(sub_id)
            if sub:
                bindings.append({
                    "class_id": sub_id,
                    "name": sub.name,
                    "description": sub.description
                })

        return QueryResult(
            query_type=QueryType.CLASS_QUERY,
            bindings=bindings,
            count=len(bindings),
            execution_time=time.time() - start_time
        )


# =============================================================================
# ONTOLOGY MANAGER
# =============================================================================

class OntologyManager:
    """
    Ontology Manager for BAEL.

    Advanced ontological reasoning and semantic knowledge representation.
    """

    def __init__(self, ontology_name: str = "bael_ontology"):
        self._name = ontology_name
        self._hierarchy = ClassHierarchy()
        self._property_manager = PropertyManager(self._hierarchy)
        self._instance_manager = InstanceManager(
            self._hierarchy,
            self._property_manager
        )
        self._constraint_validator = ConstraintValidator(
            self._hierarchy,
            self._property_manager,
            self._instance_manager
        )
        self._reasoner = OntologyReasoner(
            self._hierarchy,
            self._property_manager,
            self._instance_manager
        )
        self._query_processor = QueryProcessor(
            self._hierarchy,
            self._property_manager,
            self._instance_manager
        )

    # -------------------------------------------------------------------------
    # CLASS MANAGEMENT
    # -------------------------------------------------------------------------

    def create_class(
        self,
        name: str,
        description: str = "",
        parent_classes: Optional[List[str]] = None,
        is_abstract: bool = False
    ) -> OntologyClass:
        """Create a new class."""
        # Resolve parent names to IDs
        parent_ids = []
        if parent_classes:
            for parent_name in parent_classes:
                parent = self._hierarchy.get_class_by_name(parent_name)
                if parent:
                    parent_ids.append(parent.class_id)

        ontology_class = OntologyClass(
            name=name,
            description=description,
            parent_classes=parent_ids,
            is_abstract=is_abstract
        )
        self._hierarchy.add_class(ontology_class)
        return ontology_class

    def get_class(self, name: str) -> Optional[OntologyClass]:
        """Get class by name."""
        return self._hierarchy.get_class_by_name(name)

    def get_subclasses(
        self,
        class_name: str,
        direct_only: bool = False
    ) -> List[str]:
        """Get subclass names."""
        cls = self._hierarchy.get_class_by_name(class_name)
        if not cls:
            return []

        subclass_ids = self._hierarchy.get_subclasses(cls.class_id, direct_only)
        return [
            self._hierarchy.get_class(sid).name
            for sid in subclass_ids
            if self._hierarchy.get_class(sid)
        ]

    def get_superclasses(
        self,
        class_name: str,
        direct_only: bool = False
    ) -> List[str]:
        """Get superclass names."""
        cls = self._hierarchy.get_class_by_name(class_name)
        if not cls:
            return []

        superclass_ids = self._hierarchy.get_superclasses(cls.class_id, direct_only)
        return [
            self._hierarchy.get_class(sid).name
            for sid in superclass_ids
            if self._hierarchy.get_class(sid)
        ]

    # -------------------------------------------------------------------------
    # PROPERTY MANAGEMENT
    # -------------------------------------------------------------------------

    def create_property(
        self,
        name: str,
        property_type: PropertyType = PropertyType.DATA_PROPERTY,
        domain_classes: Optional[List[str]] = None,
        range_type: str = "str"
    ) -> OntologyProperty:
        """Create a new property."""
        # Resolve domain class names to IDs
        domain_ids = []
        if domain_classes:
            for class_name in domain_classes:
                cls = self._hierarchy.get_class_by_name(class_name)
                if cls:
                    domain_ids.append(cls.class_id)

        prop = OntologyProperty(
            name=name,
            property_type=property_type,
            domain=domain_ids,
            range_type=range_type
        )
        self._property_manager.add_property(prop)
        return prop

    def get_property(self, name: str) -> Optional[OntologyProperty]:
        """Get property by name."""
        return self._property_manager.get_property_by_name(name)

    def get_class_properties(
        self,
        class_name: str,
        include_inherited: bool = True
    ) -> List[str]:
        """Get property names for a class."""
        cls = self._hierarchy.get_class_by_name(class_name)
        if not cls:
            return []

        prop_ids = self._property_manager.get_properties_for_class(
            cls.class_id,
            include_inherited
        )

        return [
            self._property_manager.get_property(pid).name
            for pid in prop_ids
            if self._property_manager.get_property(pid)
        ]

    # -------------------------------------------------------------------------
    # INSTANCE MANAGEMENT
    # -------------------------------------------------------------------------

    def create_instance(
        self,
        name: str,
        class_name: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Optional[OntologyInstance]:
        """Create a new instance."""
        cls = self._hierarchy.get_class_by_name(class_name)
        if not cls:
            return None

        instance = OntologyInstance(
            name=name,
            class_id=cls.class_id,
            property_values=properties or {}
        )
        self._instance_manager.add_instance(instance)
        return instance

    def get_instance(self, name: str) -> Optional[OntologyInstance]:
        """Get instance by name."""
        return self._instance_manager.get_instance_by_name(name)

    def set_instance_property(
        self,
        instance_name: str,
        property_name: str,
        value: Any
    ) -> bool:
        """Set property value on instance."""
        instance = self._instance_manager.get_instance_by_name(instance_name)
        if not instance:
            return False

        return self._instance_manager.set_property_value(
            instance.instance_id,
            property_name,
            value
        )

    def get_instance_property(
        self,
        instance_name: str,
        property_name: str
    ) -> Optional[Any]:
        """Get property value from instance."""
        instance = self._instance_manager.get_instance_by_name(instance_name)
        if not instance:
            return None

        return self._instance_manager.get_property_value(
            instance.instance_id,
            property_name
        )

    def add_instance_relation(
        self,
        source_name: str,
        relation: str,
        target_name: str
    ) -> bool:
        """Add relation between instances."""
        source = self._instance_manager.get_instance_by_name(source_name)
        target = self._instance_manager.get_instance_by_name(target_name)

        if not source or not target:
            return False

        return self._instance_manager.add_relation(
            source.instance_id,
            relation,
            target.instance_id
        )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def add_cardinality_constraint(
        self,
        class_name: str,
        property_name: str,
        min_count: int = 0,
        max_count: int = -1
    ) -> Constraint:
        """Add cardinality constraint."""
        cls = self._hierarchy.get_class_by_name(class_name)

        constraint = Constraint(
            constraint_type=ConstraintType.CARDINALITY,
            applies_to=cls.class_id if cls else "",
            parameters={
                "property": property_name,
                "min": min_count,
                "max": max_count if max_count >= 0 else float('inf')
            },
            error_message=f"Cardinality constraint on {property_name}"
        )
        self._constraint_validator.add_constraint(constraint)
        return constraint

    def validate_instance(
        self,
        instance_name: str
    ) -> List[Tuple[str, str]]:
        """Validate instance against constraints."""
        instance = self._instance_manager.get_instance_by_name(instance_name)
        if not instance:
            return []

        return self._constraint_validator.validate_instance(instance)

    # -------------------------------------------------------------------------
    # REASONING
    # -------------------------------------------------------------------------

    def infer_class_memberships(
        self,
        instance_name: str
    ) -> List[str]:
        """Infer all classes an instance belongs to."""
        instance = self._instance_manager.get_instance_by_name(instance_name)
        if not instance:
            return []

        inferences = self._reasoner.infer_class_membership(instance.instance_id)

        return [
            self._hierarchy.get_class(inf.object_).name
            for inf in inferences
            if self._hierarchy.get_class(inf.object_)
        ]

    def run_reasoning(self) -> List[Inference]:
        """Run full reasoning."""
        return self._reasoner.run_all_inferences()

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    def query_instances(
        self,
        class_name: str,
        include_subclasses: bool = True
    ) -> QueryResult:
        """Query instances by class."""
        return self._query_processor.query_instances_by_class(
            class_name,
            include_subclasses
        )

    def query_by_property(
        self,
        property_name: str,
        value: Any
    ) -> QueryResult:
        """Query instances by property value."""
        return self._query_processor.query_by_property_value(property_name, value)

    def query_relations(
        self,
        instance_name: str,
        relation: Optional[str] = None
    ) -> QueryResult:
        """Query instance relations."""
        return self._query_processor.query_related_instances(instance_name, relation)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Ontology Manager."""
    print("=" * 70)
    print("BAEL - ONTOLOGY MANAGER DEMO")
    print("Advanced Ontological Reasoning and Semantic Knowledge")
    print("=" * 70)
    print()

    manager = OntologyManager("bael_agent_ontology")

    # 1. Create Class Hierarchy
    print("1. CREATE CLASS HIERARCHY:")
    print("-" * 40)

    # Root class
    manager.create_class("Entity", "Base class for all entities")

    # Agent hierarchy
    manager.create_class("Agent", "An autonomous agent", ["Entity"])
    manager.create_class("LearningAgent", "Agent that learns", ["Agent"])
    manager.create_class("PlanningAgent", "Agent that plans", ["Agent"])
    manager.create_class("HybridAgent", "Agent that learns and plans", ["LearningAgent", "PlanningAgent"])

    # Task hierarchy
    manager.create_class("Task", "A task to be performed", ["Entity"])
    manager.create_class("ComputeTask", "Computational task", ["Task"])
    manager.create_class("IOTask", "I/O task", ["Task"])

    print("   Created: Entity -> Agent -> LearningAgent, PlanningAgent -> HybridAgent")
    print("   Created: Entity -> Task -> ComputeTask, IOTask")
    print()

    # 2. Show Hierarchy
    print("2. CLASS HIERARCHY:")
    print("-" * 40)

    subclasses = manager.get_subclasses("Agent", direct_only=False)
    print(f"   All subclasses of Agent: {subclasses}")

    superclasses = manager.get_superclasses("HybridAgent", direct_only=False)
    print(f"   All superclasses of HybridAgent: {superclasses}")
    print()

    # 3. Create Properties
    print("3. CREATE PROPERTIES:")
    print("-" * 40)

    manager.create_property(
        "name",
        PropertyType.DATA_PROPERTY,
        ["Entity"],
        "str"
    )
    manager.create_property(
        "capability",
        PropertyType.DATA_PROPERTY,
        ["Agent"],
        "str"
    )
    manager.create_property(
        "learning_rate",
        PropertyType.DATA_PROPERTY,
        ["LearningAgent"],
        "float"
    )
    manager.create_property(
        "assigned_to",
        PropertyType.OBJECT_PROPERTY,
        ["Task"],
        "Agent"
    )

    print("   Created: name, capability, learning_rate, assigned_to")

    props = manager.get_class_properties("LearningAgent", include_inherited=True)
    print(f"   LearningAgent properties (incl. inherited): {props}")
    print()

    # 4. Create Instances
    print("4. CREATE INSTANCES:")
    print("-" * 40)

    manager.create_instance(
        "agent_alpha",
        "HybridAgent",
        {"name": "Alpha", "capability": "general", "learning_rate": 0.01}
    )
    manager.create_instance(
        "agent_beta",
        "LearningAgent",
        {"name": "Beta", "capability": "specialized", "learning_rate": 0.05}
    )
    manager.create_instance(
        "task_1",
        "ComputeTask",
        {"name": "Train Model"}
    )
    manager.create_instance(
        "task_2",
        "IOTask",
        {"name": "Load Data"}
    )

    print("   Created: agent_alpha (HybridAgent), agent_beta (LearningAgent)")
    print("   Created: task_1 (ComputeTask), task_2 (IOTask)")
    print()

    # 5. Add Relations
    print("5. ADD RELATIONS:")
    print("-" * 40)

    manager.add_instance_relation("task_1", "assigned_to", "agent_alpha")
    manager.add_instance_relation("task_2", "assigned_to", "agent_beta")
    manager.add_instance_relation("agent_alpha", "collaborates_with", "agent_beta")

    print("   task_1 -> assigned_to -> agent_alpha")
    print("   task_2 -> assigned_to -> agent_beta")
    print("   agent_alpha -> collaborates_with -> agent_beta")
    print()

    # 6. Run Queries
    print("6. QUERY ONTOLOGY:")
    print("-" * 40)

    result = manager.query_instances("Agent", include_subclasses=True)
    print(f"   Query 'Agent' instances: {result.count} found")
    for binding in result.bindings:
        print(f"     - {binding['name']}")

    result = manager.query_by_property("capability", "general")
    print(f"   Query capability='general': {result.count} found")

    result = manager.query_relations("task_1")
    print(f"   Query task_1 relations: {result.count} found")
    for binding in result.bindings:
        print(f"     - {binding['relation']} -> {binding['target_name']}")
    print()

    # 7. Reasoning
    print("7. ONTOLOGICAL REASONING:")
    print("-" * 40)

    memberships = manager.infer_class_memberships("agent_alpha")
    print(f"   agent_alpha is instance of: {memberships}")

    inferences = manager.run_reasoning()
    print(f"   Total inferences: {len(inferences)}")

    # Show some inferences
    for inf in inferences[:5]:
        print(f"     - {inf.inference_type.value}: {inf.subject} {inf.predicate} {inf.object_}")
    print()

    # 8. Constraints
    print("8. CONSTRAINT VALIDATION:")
    print("-" * 40)

    manager.add_cardinality_constraint("Agent", "name", min_count=1)

    violations = manager.validate_instance("agent_alpha")
    print(f"   Violations for agent_alpha: {len(violations)}")

    violations = manager.validate_instance("agent_beta")
    print(f"   Violations for agent_beta: {len(violations)}")
    print()

    # 9. Advanced Hierarchy Operations
    print("9. HIERARCHY OPERATIONS:")
    print("-" * 40)

    cls = manager.get_class("HybridAgent")
    if cls:
        print(f"   HybridAgent ID: {cls.class_id[:8]}...")
        print(f"   Parent classes: {len(cls.parent_classes)}")

    # Check subclass relationship
    is_sub = manager._hierarchy.is_subclass_of(
        manager.get_class("HybridAgent").class_id,
        manager.get_class("Entity").class_id
    )
    print(f"   HybridAgent is subclass of Entity: {is_sub}")

    # Common ancestor
    lca = manager._hierarchy.get_lowest_common_ancestor(
        manager.get_class("ComputeTask").class_id,
        manager.get_class("IOTask").class_id
    )
    if lca:
        lca_cls = manager._hierarchy.get_class(lca)
        print(f"   LCA of ComputeTask and IOTask: {lca_cls.name if lca_cls else 'None'}")
    print()

    # 10. Instance Properties
    print("10. INSTANCE PROPERTIES:")
    print("-" * 40)

    lr = manager.get_instance_property("agent_alpha", "learning_rate")
    print(f"   agent_alpha learning_rate: {lr}")

    manager.set_instance_property("agent_alpha", "learning_rate", 0.02)
    lr = manager.get_instance_property("agent_alpha", "learning_rate")
    print(f"   Updated learning_rate: {lr}")

    instance = manager.get_instance("agent_alpha")
    if instance:
        print(f"   All properties: {instance.property_values}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Ontology Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
