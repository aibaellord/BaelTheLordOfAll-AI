"""
BAEL Ontology Manager
======================

Manages ontologies and schemas for knowledge graphs.
Enables structured knowledge modeling.

Features:
- Ontology definition
- Class hierarchies
- Property definitions
- Constraint validation
- Schema evolution
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PropertyType(Enum):
    """Types of properties."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    URI = "uri"
    OBJECT = "object"  # Reference to another class


class Cardinality(Enum):
    """Property cardinality."""
    ONE = "1"
    ZERO_OR_ONE = "0..1"
    ZERO_OR_MORE = "0..*"
    ONE_OR_MORE = "1..*"


@dataclass
class OntologyProperty:
    """A property in an ontology."""
    id: str
    name: str

    # Type
    property_type: PropertyType

    # For object references
    range_class: Optional[str] = None

    # Cardinality
    cardinality: Cardinality = Cardinality.ZERO_OR_ONE

    # Constraints
    required: bool = False
    unique: bool = False

    # Validation
    pattern: Optional[str] = None  # Regex for strings
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: List[Any] = field(default_factory=list)

    # Metadata
    description: str = ""


@dataclass
class OntologyClass:
    """A class in an ontology."""
    id: str
    name: str

    # Hierarchy
    parent_class: Optional[str] = None

    # Properties
    properties: Dict[str, OntologyProperty] = field(default_factory=dict)

    # Constraints
    abstract: bool = False  # Cannot be instantiated directly

    # Metadata
    description: str = ""

    def add_property(self, prop: OntologyProperty) -> None:
        """Add a property to the class."""
        self.properties[prop.name] = prop

    def get_all_properties(
        self,
        ontology: "Ontology",
    ) -> Dict[str, OntologyProperty]:
        """Get all properties including inherited."""
        all_props = dict(self.properties)

        if self.parent_class:
            parent = ontology.get_class(self.parent_class)
            if parent:
                inherited = parent.get_all_properties(ontology)
                # Inherited properties can be overridden
                for name, prop in inherited.items():
                    if name not in all_props:
                        all_props[name] = prop

        return all_props


@dataclass
class Ontology:
    """An ontology definition."""
    id: str
    name: str

    # Version
    version: str = "1.0.0"

    # Namespace
    namespace: str = ""

    # Classes
    classes: Dict[str, OntologyClass] = field(default_factory=dict)

    # Metadata
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_class(self, cls: OntologyClass) -> None:
        """Add a class to the ontology."""
        self.classes[cls.name] = cls
        self.updated_at = datetime.now()

    def get_class(self, name: str) -> Optional[OntologyClass]:
        """Get a class by name."""
        return self.classes.get(name)

    def get_subclasses(self, class_name: str) -> List[OntologyClass]:
        """Get all subclasses of a class."""
        return [
            c for c in self.classes.values()
            if c.parent_class == class_name
        ]


class OntologyManager:
    """
    Ontology manager for BAEL.

    Manages ontology definitions and validation.
    """

    def __init__(self):
        # Ontologies
        self._ontologies: Dict[str, Ontology] = {}

        # Default ontology
        self._default: Optional[str] = None

        # Stats
        self.stats = {
            "ontologies_created": 0,
            "classes_defined": 0,
            "validations_performed": 0,
        }

    def create_ontology(
        self,
        name: str,
        namespace: str = "",
        description: str = "",
    ) -> Ontology:
        """
        Create a new ontology.

        Args:
            name: Ontology name
            namespace: Ontology namespace
            description: Description

        Returns:
            Created ontology
        """
        ont_id = hashlib.md5(
            f"{name}:{namespace}".encode()
        ).hexdigest()[:12]

        ontology = Ontology(
            id=ont_id,
            name=name,
            namespace=namespace,
            description=description,
        )

        self._ontologies[ont_id] = ontology

        if self._default is None:
            self._default = ont_id

        self.stats["ontologies_created"] += 1

        return ontology

    def define_class(
        self,
        ontology_id: str,
        name: str,
        parent: Optional[str] = None,
        description: str = "",
        abstract: bool = False,
    ) -> Optional[OntologyClass]:
        """
        Define a class in an ontology.

        Args:
            ontology_id: Ontology ID
            name: Class name
            parent: Parent class name
            description: Description
            abstract: Is abstract class

        Returns:
            Created class or None
        """
        ontology = self._ontologies.get(ontology_id)
        if not ontology:
            return None

        class_id = hashlib.md5(
            f"{ontology_id}:{name}".encode()
        ).hexdigest()[:12]

        cls = OntologyClass(
            id=class_id,
            name=name,
            parent_class=parent,
            description=description,
            abstract=abstract,
        )

        ontology.add_class(cls)
        self.stats["classes_defined"] += 1

        return cls

    def define_property(
        self,
        ontology_id: str,
        class_name: str,
        prop_name: str,
        prop_type: PropertyType,
        cardinality: Cardinality = Cardinality.ZERO_OR_ONE,
        required: bool = False,
        description: str = "",
        range_class: Optional[str] = None,
        **constraints,
    ) -> Optional[OntologyProperty]:
        """
        Define a property for a class.

        Args:
            ontology_id: Ontology ID
            class_name: Class name
            prop_name: Property name
            prop_type: Property type
            cardinality: Property cardinality
            required: Is required
            description: Description
            range_class: For object properties, the target class
            **constraints: Additional constraints

        Returns:
            Created property or None
        """
        ontology = self._ontologies.get(ontology_id)
        if not ontology:
            return None

        cls = ontology.get_class(class_name)
        if not cls:
            return None

        prop_id = hashlib.md5(
            f"{class_name}:{prop_name}".encode()
        ).hexdigest()[:12]

        prop = OntologyProperty(
            id=prop_id,
            name=prop_name,
            property_type=prop_type,
            cardinality=cardinality,
            required=required,
            range_class=range_class,
            description=description,
            pattern=constraints.get("pattern"),
            min_value=constraints.get("min_value"),
            max_value=constraints.get("max_value"),
            allowed_values=constraints.get("allowed_values", []),
        )

        cls.add_property(prop)

        return prop

    def validate_instance(
        self,
        ontology_id: str,
        class_name: str,
        instance: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate an instance against a class definition.

        Args:
            ontology_id: Ontology ID
            class_name: Class name
            instance: Instance data

        Returns:
            (is_valid, error_messages)
        """
        self.stats["validations_performed"] += 1

        errors = []

        ontology = self._ontologies.get(ontology_id)
        if not ontology:
            return False, ["Ontology not found"]

        cls = ontology.get_class(class_name)
        if not cls:
            return False, [f"Class {class_name} not found"]

        if cls.abstract:
            return False, [f"Cannot instantiate abstract class {class_name}"]

        # Get all properties including inherited
        all_props = cls.get_all_properties(ontology)

        # Check required properties
        for prop_name, prop in all_props.items():
            if prop.required and prop_name not in instance:
                errors.append(f"Required property '{prop_name}' is missing")

        # Validate each property
        for prop_name, value in instance.items():
            if prop_name not in all_props:
                # Unknown property - could be warning or error
                continue

            prop = all_props[prop_name]
            prop_errors = self._validate_property(prop, value, ontology)
            errors.extend(prop_errors)

        return len(errors) == 0, errors

    def _validate_property(
        self,
        prop: OntologyProperty,
        value: Any,
        ontology: Ontology,
    ) -> List[str]:
        """Validate a property value."""
        errors = []

        # Handle None
        if value is None:
            if prop.required:
                errors.append(f"Property '{prop.name}' cannot be null")
            return errors

        # Type validation
        type_valid, type_error = self._validate_type(prop, value)
        if not type_valid:
            errors.append(type_error)
            return errors  # Skip further validation if type is wrong

        # Cardinality
        if prop.cardinality in [Cardinality.ZERO_OR_MORE, Cardinality.ONE_OR_MORE]:
            if not isinstance(value, list):
                errors.append(f"Property '{prop.name}' should be a list")
            elif prop.cardinality == Cardinality.ONE_OR_MORE and len(value) == 0:
                errors.append(f"Property '{prop.name}' requires at least one value")

        # Value constraints
        if prop.property_type in [PropertyType.INTEGER, PropertyType.FLOAT]:
            if prop.min_value is not None and value < prop.min_value:
                errors.append(f"Property '{prop.name}' must be >= {prop.min_value}")
            if prop.max_value is not None and value > prop.max_value:
                errors.append(f"Property '{prop.name}' must be <= {prop.max_value}")

        # Pattern validation
        if prop.pattern and prop.property_type == PropertyType.STRING:
            import re
            if not re.match(prop.pattern, str(value)):
                errors.append(f"Property '{prop.name}' does not match pattern")

        # Allowed values
        if prop.allowed_values and value not in prop.allowed_values:
            errors.append(f"Property '{prop.name}' must be one of {prop.allowed_values}")

        # Object reference validation
        if prop.property_type == PropertyType.OBJECT and prop.range_class:
            if not ontology.get_class(prop.range_class):
                errors.append(f"Reference class '{prop.range_class}' not found")

        return errors

    def _validate_type(
        self,
        prop: OntologyProperty,
        value: Any,
    ) -> Tuple[bool, str]:
        """Validate property type."""
        type_checks = {
            PropertyType.STRING: lambda v: isinstance(v, str),
            PropertyType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            PropertyType.FLOAT: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            PropertyType.BOOLEAN: lambda v: isinstance(v, bool),
            PropertyType.OBJECT: lambda v: isinstance(v, (str, dict)),  # ID or object
        }

        checker = type_checks.get(prop.property_type, lambda v: True)

        if not checker(value):
            return False, f"Property '{prop.name}' has wrong type, expected {prop.property_type.value}"

        return True, ""

    def get_ontology(self, ontology_id: str) -> Optional[Ontology]:
        """Get an ontology by ID."""
        return self._ontologies.get(ontology_id)

    def get_default_ontology(self) -> Optional[Ontology]:
        """Get the default ontology."""
        if self._default:
            return self._ontologies.get(self._default)
        return None

    def get_class_hierarchy(
        self,
        ontology_id: str,
        class_name: str,
    ) -> List[str]:
        """Get class hierarchy (from class to root)."""
        ontology = self._ontologies.get(ontology_id)
        if not ontology:
            return []

        hierarchy = []
        current = class_name

        while current:
            hierarchy.append(current)
            cls = ontology.get_class(current)
            current = cls.parent_class if cls else None

        return hierarchy

    def export_ontology(self, ontology_id: str) -> Dict[str, Any]:
        """Export ontology to dictionary."""
        ontology = self._ontologies.get(ontology_id)
        if not ontology:
            return {}

        return {
            "id": ontology.id,
            "name": ontology.name,
            "version": ontology.version,
            "namespace": ontology.namespace,
            "description": ontology.description,
            "classes": {
                name: {
                    "id": cls.id,
                    "name": cls.name,
                    "parent": cls.parent_class,
                    "abstract": cls.abstract,
                    "properties": {
                        pname: {
                            "type": p.property_type.value,
                            "cardinality": p.cardinality.value,
                            "required": p.required,
                            "description": p.description,
                        }
                        for pname, p in cls.properties.items()
                    },
                }
                for name, cls in ontology.classes.items()
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            **self.stats,
            "ontologies": len(self._ontologies),
            "total_classes": sum(
                len(o.classes) for o in self._ontologies.values()
            ),
        }


# Need to import Tuple
from typing import Tuple


def demo():
    """Demonstrate ontology manager."""
    print("=" * 60)
    print("BAEL Ontology Manager Demo")
    print("=" * 60)

    manager = OntologyManager()

    # Create ontology
    print("\nCreating ontology...")
    ontology = manager.create_ontology(
        name="AI System Ontology",
        namespace="bael.ai",
        description="Ontology for AI system entities",
    )
    print(f"  Created: {ontology.name}")

    # Define classes
    print("\nDefining classes...")

    # Base class
    entity = manager.define_class(
        ontology.id,
        "Entity",
        description="Base entity class",
        abstract=True,
    )

    # Agent class
    agent = manager.define_class(
        ontology.id,
        "Agent",
        parent="Entity",
        description="An AI agent",
    )

    # Task class
    task = manager.define_class(
        ontology.id,
        "Task",
        parent="Entity",
        description="A task to execute",
    )

    print(f"  Defined {manager.stats['classes_defined']} classes")

    # Define properties
    print("\nDefining properties...")

    manager.define_property(
        ontology.id, "Entity", "name",
        PropertyType.STRING, required=True,
        description="Entity name",
    )

    manager.define_property(
        ontology.id, "Agent", "status",
        PropertyType.STRING,
        allowed_values=["idle", "running", "stopped"],
        description="Agent status",
    )

    manager.define_property(
        ontology.id, "Agent", "capabilities",
        PropertyType.STRING,
        cardinality=Cardinality.ZERO_OR_MORE,
        description="Agent capabilities",
    )

    manager.define_property(
        ontology.id, "Task", "priority",
        PropertyType.INTEGER,
        min_value=1, max_value=10,
        description="Task priority",
    )

    manager.define_property(
        ontology.id, "Task", "assigned_to",
        PropertyType.OBJECT,
        range_class="Agent",
        description="Assigned agent",
    )

    # Validate instances
    print("\nValidating instances...")

    # Valid agent
    valid_agent = {
        "name": "Agent-1",
        "status": "running",
        "capabilities": ["search", "code"],
    }

    is_valid, errors = manager.validate_instance(ontology.id, "Agent", valid_agent)
    print(f"  Valid agent: {is_valid}")

    # Invalid agent
    invalid_agent = {
        "status": "unknown",  # Not in allowed values
        # Missing required 'name'
    }

    is_valid, errors = manager.validate_instance(ontology.id, "Agent", invalid_agent)
    print(f"  Invalid agent: {is_valid}")
    print(f"    Errors: {errors}")

    # Invalid task
    invalid_task = {
        "name": "Task-1",
        "priority": 15,  # Out of range
    }

    is_valid, errors = manager.validate_instance(ontology.id, "Task", invalid_task)
    print(f"  Invalid task: {is_valid}")
    print(f"    Errors: {errors}")

    # Get hierarchy
    print("\nClass hierarchy for 'Agent':")
    hierarchy = manager.get_class_hierarchy(ontology.id, "Agent")
    print(f"  {' -> '.join(hierarchy)}")

    # Export
    print("\nExported ontology structure:")
    export = manager.export_ontology(ontology.id)
    print(f"  Classes: {list(export.get('classes', {}).keys())}")

    print(f"\nStats: {manager.get_stats()}")


if __name__ == "__main__":
    demo()
