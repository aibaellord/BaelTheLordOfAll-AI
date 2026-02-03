#!/usr/bin/env python3
"""
BAEL - Schema Registry
Comprehensive schema management, validation, and evolution system.

Features:
- Schema definition and storage
- Schema validation
- Schema versioning
- Schema evolution
- Compatibility checking
- Schema registry
- Type inference
- Code generation
- Schema migration
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple,
                    Type, TypeVar, Union, get_type_hints)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class SchemaType(Enum):
    """Schema data types."""
    NULL = "null"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"
    UNION = "union"
    ANY = "any"


class CompatibilityMode(Enum):
    """Schema compatibility modes."""
    NONE = "none"
    BACKWARD = "backward"
    FORWARD = "forward"
    FULL = "full"
    BACKWARD_TRANSITIVE = "backward_transitive"
    FORWARD_TRANSITIVE = "forward_transitive"
    FULL_TRANSITIVE = "full_transitive"


class ValidationResult(Enum):
    """Validation result types."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SchemaField:
    """Schema field definition."""
    name: str
    type: SchemaType
    required: bool = False
    nullable: bool = False
    default: Any = None
    description: str = ""
    items: Optional['SchemaField'] = None  # For arrays
    properties: Dict[str, 'SchemaField'] = field(default_factory=dict)  # For objects
    enum_values: List[Any] = field(default_factory=list)
    pattern: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "type": self.type.value,
            "required": self.required,
            "nullable": self.nullable
        }

        if self.default is not None:
            result["default"] = self.default

        if self.description:
            result["description"] = self.description

        if self.items:
            result["items"] = self.items.to_dict()

        if self.properties:
            result["properties"] = {
                k: v.to_dict() for k, v in self.properties.items()
            }

        if self.enum_values:
            result["enum"] = self.enum_values

        if self.pattern:
            result["pattern"] = self.pattern

        return result


@dataclass
class Schema:
    """Schema definition."""
    schema_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    namespace: str = ""
    version: int = 1
    type: SchemaType = SchemaType.OBJECT
    fields: Dict[str, SchemaField] = field(default_factory=dict)
    description: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""

    @property
    def full_name(self) -> str:
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name

    def compute_fingerprint(self) -> str:
        """Compute schema fingerprint."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "name": self.name,
            "namespace": self.namespace,
            "version": self.version,
            "type": self.type.value,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "description": self.description,
            "metadata": self.metadata
        }


@dataclass
class ValidationError:
    """Validation error."""
    path: str
    message: str
    code: str = ""
    expected: Any = None
    actual: Any = None


@dataclass
class ValidationReport:
    """Validation report."""
    result: ValidationResult
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.result == ValidationResult.VALID


@dataclass
class CompatibilityReport:
    """Compatibility report."""
    compatible: bool
    mode: CompatibilityMode
    issues: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)


@dataclass
class SchemaVersion:
    """Schema version record."""
    version: int
    schema: Schema
    created_at: float = field(default_factory=time.time)
    comment: str = ""


# =============================================================================
# VALIDATORS
# =============================================================================

class TypeValidator:
    """Type validation utilities."""

    @staticmethod
    def validate_type(value: Any, expected_type: SchemaType) -> bool:
        """Validate value type."""
        if value is None:
            return expected_type == SchemaType.NULL

        type_checks = {
            SchemaType.BOOLEAN: lambda v: isinstance(v, bool),
            SchemaType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            SchemaType.NUMBER: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            SchemaType.STRING: lambda v: isinstance(v, str),
            SchemaType.ARRAY: lambda v: isinstance(v, list),
            SchemaType.OBJECT: lambda v: isinstance(v, dict),
            SchemaType.ANY: lambda v: True
        }

        check = type_checks.get(expected_type)
        return check(value) if check else False


class SchemaValidator:
    """Schema validator."""

    def __init__(self, schema: Schema):
        self.schema = schema

    def validate(self, data: Any) -> ValidationReport:
        """Validate data against schema."""
        errors = []
        warnings = []

        self._validate_value(data, self.schema.type, self.schema.fields, "", errors, warnings)

        if errors:
            return ValidationReport(
                result=ValidationResult.INVALID,
                errors=errors,
                warnings=warnings
            )

        if warnings:
            return ValidationReport(
                result=ValidationResult.WARNING,
                warnings=warnings
            )

        return ValidationReport(result=ValidationResult.VALID)

    def _validate_value(
        self,
        value: Any,
        expected_type: SchemaType,
        fields: Dict[str, SchemaField],
        path: str,
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> None:
        """Recursively validate value."""
        # Handle null
        if value is None:
            return

        # Type check
        if not TypeValidator.validate_type(value, expected_type):
            errors.append(ValidationError(
                path=path or "root",
                message=f"Expected {expected_type.value}, got {type(value).__name__}",
                code="TYPE_MISMATCH",
                expected=expected_type.value,
                actual=type(value).__name__
            ))
            return

        # Object validation
        if expected_type == SchemaType.OBJECT and fields:
            self._validate_object(value, fields, path, errors, warnings)

        # Array validation
        if expected_type == SchemaType.ARRAY:
            self._validate_array(value, fields, path, errors, warnings)

    def _validate_object(
        self,
        obj: Dict[str, Any],
        fields: Dict[str, SchemaField],
        path: str,
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> None:
        """Validate object properties."""
        for field_name, field_schema in fields.items():
            field_path = f"{path}.{field_name}" if path else field_name

            if field_name not in obj:
                if field_schema.required:
                    errors.append(ValidationError(
                        path=field_path,
                        message=f"Required field missing",
                        code="REQUIRED_FIELD_MISSING"
                    ))
                continue

            value = obj[field_name]

            # Nullable check
            if value is None:
                if not field_schema.nullable:
                    errors.append(ValidationError(
                        path=field_path,
                        message="Field is not nullable",
                        code="NULL_NOT_ALLOWED"
                    ))
                continue

            # Type validation
            if not TypeValidator.validate_type(value, field_schema.type):
                errors.append(ValidationError(
                    path=field_path,
                    message=f"Expected {field_schema.type.value}",
                    code="TYPE_MISMATCH"
                ))
                continue

            # String constraints
            if field_schema.type == SchemaType.STRING:
                self._validate_string(value, field_schema, field_path, errors)

            # Number constraints
            if field_schema.type in [SchemaType.INTEGER, SchemaType.NUMBER]:
                self._validate_number(value, field_schema, field_path, errors)

            # Enum validation
            if field_schema.enum_values:
                if value not in field_schema.enum_values:
                    errors.append(ValidationError(
                        path=field_path,
                        message=f"Value must be one of {field_schema.enum_values}",
                        code="ENUM_MISMATCH"
                    ))

            # Nested object
            if field_schema.type == SchemaType.OBJECT and field_schema.properties:
                self._validate_object(
                    value,
                    field_schema.properties,
                    field_path,
                    errors,
                    warnings
                )

            # Array items
            if field_schema.type == SchemaType.ARRAY and field_schema.items:
                for i, item in enumerate(value):
                    item_path = f"{field_path}[{i}]"
                    self._validate_value(
                        item,
                        field_schema.items.type,
                        field_schema.items.properties,
                        item_path,
                        errors,
                        warnings
                    )

    def _validate_array(
        self,
        arr: List[Any],
        fields: Dict[str, SchemaField],
        path: str,
        errors: List[ValidationError],
        warnings: List[ValidationError]
    ) -> None:
        """Validate array items."""
        # Items schema would be in metadata or a special field
        pass

    def _validate_string(
        self,
        value: str,
        field: SchemaField,
        path: str,
        errors: List[ValidationError]
    ) -> None:
        """Validate string constraints."""
        if field.min_length is not None and len(value) < field.min_length:
            errors.append(ValidationError(
                path=path,
                message=f"String length below minimum {field.min_length}",
                code="MIN_LENGTH"
            ))

        if field.max_length is not None and len(value) > field.max_length:
            errors.append(ValidationError(
                path=path,
                message=f"String length exceeds maximum {field.max_length}",
                code="MAX_LENGTH"
            ))

        if field.pattern:
            if not re.match(field.pattern, value):
                errors.append(ValidationError(
                    path=path,
                    message=f"String doesn't match pattern",
                    code="PATTERN_MISMATCH"
                ))

    def _validate_number(
        self,
        value: Union[int, float],
        field: SchemaField,
        path: str,
        errors: List[ValidationError]
    ) -> None:
        """Validate number constraints."""
        if field.min_value is not None and value < field.min_value:
            errors.append(ValidationError(
                path=path,
                message=f"Value below minimum {field.min_value}",
                code="MIN_VALUE"
            ))

        if field.max_value is not None and value > field.max_value:
            errors.append(ValidationError(
                path=path,
                message=f"Value exceeds maximum {field.max_value}",
                code="MAX_VALUE"
            ))


# =============================================================================
# COMPATIBILITY CHECKER
# =============================================================================

class CompatibilityChecker:
    """Schema compatibility checker."""

    def check(
        self,
        old_schema: Schema,
        new_schema: Schema,
        mode: CompatibilityMode
    ) -> CompatibilityReport:
        """Check schema compatibility."""
        issues = []
        breaking = []

        if mode == CompatibilityMode.NONE:
            return CompatibilityReport(compatible=True, mode=mode)

        # Check for removed required fields (backward compatibility)
        if mode in [CompatibilityMode.BACKWARD, CompatibilityMode.FULL]:
            for name, field in old_schema.fields.items():
                if name not in new_schema.fields:
                    if field.required:
                        breaking.append(f"Required field '{name}' was removed")

        # Check for new required fields without defaults (forward compatibility)
        if mode in [CompatibilityMode.FORWARD, CompatibilityMode.FULL]:
            for name, field in new_schema.fields.items():
                if name not in old_schema.fields:
                    if field.required and field.default is None:
                        breaking.append(
                            f"New required field '{name}' without default"
                        )

        # Check for type changes
        for name, new_field in new_schema.fields.items():
            if name in old_schema.fields:
                old_field = old_schema.fields[name]

                if old_field.type != new_field.type:
                    breaking.append(
                        f"Type of '{name}' changed from "
                        f"{old_field.type.value} to {new_field.type.value}"
                    )

        compatible = len(breaking) == 0

        return CompatibilityReport(
            compatible=compatible,
            mode=mode,
            issues=issues,
            breaking_changes=breaking
        )


# =============================================================================
# TYPE INFERENCE
# =============================================================================

class TypeInferrer:
    """Infer schema from data."""

    def infer(self, data: Any, name: str = "inferred") -> Schema:
        """Infer schema from data."""
        schema = Schema(name=name)

        if isinstance(data, dict):
            schema.type = SchemaType.OBJECT
            schema.fields = self._infer_object_fields(data)
        elif isinstance(data, list):
            schema.type = SchemaType.ARRAY
            if data:
                schema.fields["items"] = self._infer_field("items", data[0])
        else:
            schema.type = self._infer_type(data)

        schema.fingerprint = schema.compute_fingerprint()
        return schema

    def _infer_object_fields(
        self,
        obj: Dict[str, Any]
    ) -> Dict[str, SchemaField]:
        """Infer fields from object."""
        fields = {}

        for key, value in obj.items():
            fields[key] = self._infer_field(key, value)

        return fields

    def _infer_field(self, name: str, value: Any) -> SchemaField:
        """Infer field schema."""
        field_type = self._infer_type(value)

        field = SchemaField(
            name=name,
            type=field_type,
            nullable=value is None
        )

        if field_type == SchemaType.OBJECT and value:
            field.properties = self._infer_object_fields(value)

        if field_type == SchemaType.ARRAY and value:
            field.items = self._infer_field("item", value[0]) if value else None

        return field

    def _infer_type(self, value: Any) -> SchemaType:
        """Infer type from value."""
        if value is None:
            return SchemaType.NULL
        if isinstance(value, bool):
            return SchemaType.BOOLEAN
        if isinstance(value, int):
            return SchemaType.INTEGER
        if isinstance(value, float):
            return SchemaType.NUMBER
        if isinstance(value, str):
            return SchemaType.STRING
        if isinstance(value, list):
            return SchemaType.ARRAY
        if isinstance(value, dict):
            return SchemaType.OBJECT
        return SchemaType.ANY


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================

class SchemaRegistry:
    """
    Comprehensive Schema Registry for BAEL.
    """

    def __init__(
        self,
        compatibility_mode: CompatibilityMode = CompatibilityMode.BACKWARD
    ):
        self.compatibility_mode = compatibility_mode
        self.schemas: Dict[str, Schema] = {}
        self.versions: Dict[str, List[SchemaVersion]] = defaultdict(list)
        self.compatibility_checker = CompatibilityChecker()
        self.type_inferrer = TypeInferrer()

    def register(
        self,
        schema: Schema,
        check_compatibility: bool = True
    ) -> Tuple[bool, Optional[CompatibilityReport]]:
        """Register a schema."""
        full_name = schema.full_name

        # Compute fingerprint
        schema.fingerprint = schema.compute_fingerprint()

        # Check if schema exists
        if full_name in self.schemas:
            existing = self.schemas[full_name]

            # Check compatibility
            if check_compatibility:
                report = self.compatibility_checker.check(
                    existing,
                    schema,
                    self.compatibility_mode
                )

                if not report.compatible:
                    return False, report

            # Increment version
            schema.version = existing.version + 1

        # Store schema
        self.schemas[full_name] = schema

        # Store version
        self.versions[full_name].append(SchemaVersion(
            version=schema.version,
            schema=schema
        ))

        return True, None

    def get(self, name: str, version: int = None) -> Optional[Schema]:
        """Get schema by name and optional version."""
        if version is not None:
            versions = self.versions.get(name, [])
            for v in versions:
                if v.version == version:
                    return v.schema
            return None

        return self.schemas.get(name)

    def list_schemas(self) -> List[str]:
        """List all registered schemas."""
        return list(self.schemas.keys())

    def list_versions(self, name: str) -> List[int]:
        """List all versions of a schema."""
        return [v.version for v in self.versions.get(name, [])]

    def delete(self, name: str) -> bool:
        """Delete a schema."""
        if name in self.schemas:
            del self.schemas[name]
            del self.versions[name]
            return True
        return False

    def validate(
        self,
        data: Any,
        schema_name: str,
        version: int = None
    ) -> ValidationReport:
        """Validate data against a registered schema."""
        schema = self.get(schema_name, version)

        if not schema:
            return ValidationReport(
                result=ValidationResult.INVALID,
                errors=[ValidationError(
                    path="",
                    message=f"Schema '{schema_name}' not found",
                    code="SCHEMA_NOT_FOUND"
                )]
            )

        validator = SchemaValidator(schema)
        return validator.validate(data)

    def infer_and_register(
        self,
        data: Any,
        name: str,
        namespace: str = ""
    ) -> Schema:
        """Infer schema from data and register it."""
        schema = self.type_inferrer.infer(data, name)
        schema.namespace = namespace

        self.register(schema)
        return schema

    def check_compatibility(
        self,
        schema_name: str,
        new_schema: Schema
    ) -> CompatibilityReport:
        """Check compatibility with registered schema."""
        existing = self.get(schema_name)

        if not existing:
            return CompatibilityReport(
                compatible=True,
                mode=self.compatibility_mode
            )

        return self.compatibility_checker.check(
            existing,
            new_schema,
            self.compatibility_mode
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_schemas": len(self.schemas),
            "total_versions": sum(len(v) for v in self.versions.values()),
            "schemas": [
                {
                    "name": s.full_name,
                    "version": s.version,
                    "fields": len(s.fields)
                }
                for s in self.schemas.values()
            ]
        }


# =============================================================================
# SCHEMA BUILDER
# =============================================================================

class SchemaBuilder:
    """Fluent schema builder."""

    def __init__(self, name: str, namespace: str = ""):
        self.schema = Schema(name=name, namespace=namespace)

    def description(self, desc: str) -> 'SchemaBuilder':
        self.schema.description = desc
        return self

    def field(
        self,
        name: str,
        field_type: SchemaType,
        required: bool = False,
        nullable: bool = False,
        default: Any = None,
        description: str = ""
    ) -> 'SchemaBuilder':
        """Add a field."""
        self.schema.fields[name] = SchemaField(
            name=name,
            type=field_type,
            required=required,
            nullable=nullable,
            default=default,
            description=description
        )
        return self

    def string_field(
        self,
        name: str,
        required: bool = False,
        min_length: int = None,
        max_length: int = None,
        pattern: str = ""
    ) -> 'SchemaBuilder':
        """Add a string field."""
        self.schema.fields[name] = SchemaField(
            name=name,
            type=SchemaType.STRING,
            required=required,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern
        )
        return self

    def integer_field(
        self,
        name: str,
        required: bool = False,
        min_value: int = None,
        max_value: int = None
    ) -> 'SchemaBuilder':
        """Add an integer field."""
        self.schema.fields[name] = SchemaField(
            name=name,
            type=SchemaType.INTEGER,
            required=required,
            min_value=min_value,
            max_value=max_value
        )
        return self

    def boolean_field(
        self,
        name: str,
        required: bool = False,
        default: bool = None
    ) -> 'SchemaBuilder':
        """Add a boolean field."""
        self.schema.fields[name] = SchemaField(
            name=name,
            type=SchemaType.BOOLEAN,
            required=required,
            default=default
        )
        return self

    def enum_field(
        self,
        name: str,
        values: List[Any],
        required: bool = False
    ) -> 'SchemaBuilder':
        """Add an enum field."""
        self.schema.fields[name] = SchemaField(
            name=name,
            type=SchemaType.ENUM,
            required=required,
            enum_values=values
        )
        return self

    def array_field(
        self,
        name: str,
        item_type: SchemaType,
        required: bool = False
    ) -> 'SchemaBuilder':
        """Add an array field."""
        self.schema.fields[name] = SchemaField(
            name=name,
            type=SchemaType.ARRAY,
            required=required,
            items=SchemaField(name="item", type=item_type)
        )
        return self

    def object_field(
        self,
        name: str,
        properties: Dict[str, SchemaField],
        required: bool = False
    ) -> 'SchemaBuilder':
        """Add an object field."""
        self.schema.fields[name] = SchemaField(
            name=name,
            type=SchemaType.OBJECT,
            required=required,
            properties=properties
        )
        return self

    def build(self) -> Schema:
        """Build the schema."""
        self.schema.fingerprint = self.schema.compute_fingerprint()
        return self.schema


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Schema Registry System."""
    print("=" * 70)
    print("BAEL - SCHEMA REGISTRY SYSTEM DEMO")
    print("Comprehensive Schema Management")
    print("=" * 70)
    print()

    registry = SchemaRegistry()

    # 1. Build Schema
    print("1. BUILD SCHEMA:")
    print("-" * 40)

    user_schema = (
        SchemaBuilder("User", "bael.models")
        .description("User entity schema")
        .string_field("id", required=True)
        .string_field("username", required=True, min_length=3, max_length=50)
        .string_field("email", required=True, pattern=r"^[^@]+@[^@]+\.[^@]+$")
        .integer_field("age", min_value=0, max_value=150)
        .boolean_field("active", default=True)
        .enum_field("role", ["user", "admin", "moderator"])
        .array_field("tags", SchemaType.STRING)
        .build()
    )

    print(f"   Schema: {user_schema.full_name}")
    print(f"   Fields: {len(user_schema.fields)}")
    print(f"   Fingerprint: {user_schema.fingerprint}")
    print()

    # 2. Register Schema
    print("2. REGISTER SCHEMA:")
    print("-" * 40)

    success, report = registry.register(user_schema)
    print(f"   Registered: {success}")
    print(f"   Version: {user_schema.version}")
    print()

    # 3. Validate Data
    print("3. VALIDATE DATA:")
    print("-" * 40)

    valid_user = {
        "id": "user-001",
        "username": "johndoe",
        "email": "john@example.com",
        "age": 30,
        "active": True,
        "role": "user",
        "tags": ["developer", "python"]
    }

    result = registry.validate(valid_user, user_schema.full_name)
    print(f"   Valid user: {result.is_valid}")

    invalid_user = {
        "id": "user-002",
        "username": "ab",  # Too short
        "email": "invalid-email",  # No @
        "age": -5  # Negative
    }

    result = registry.validate(invalid_user, user_schema.full_name)
    print(f"   Invalid user: {result.is_valid}")
    print(f"   Errors: {len(result.errors)}")

    for error in result.errors:
        print(f"      - {error.path}: {error.message}")
    print()

    # 4. Schema Versioning
    print("4. SCHEMA VERSIONING:")
    print("-" * 40)

    # Add a new optional field
    user_schema_v2 = (
        SchemaBuilder("User", "bael.models")
        .description("User entity schema v2")
        .string_field("id", required=True)
        .string_field("username", required=True)
        .string_field("email", required=True)
        .integer_field("age")
        .boolean_field("active", default=True)
        .enum_field("role", ["user", "admin", "moderator"])
        .array_field("tags", SchemaType.STRING)
        .string_field("avatar_url")  # New optional field
        .build()
    )

    success, report = registry.register(user_schema_v2)
    print(f"   Registered v2: {success}")
    print(f"   New version: {user_schema_v2.version}")

    versions = registry.list_versions(user_schema.full_name)
    print(f"   All versions: {versions}")
    print()

    # 5. Compatibility Check
    print("5. COMPATIBILITY CHECK:")
    print("-" * 40)

    # Breaking change: remove required field
    breaking_schema = (
        SchemaBuilder("User", "bael.models")
        .description("Breaking schema")
        .string_field("id", required=True)
        # Missing username!
        .string_field("email", required=True)
        .build()
    )

    compat_report = registry.check_compatibility(
        user_schema.full_name,
        breaking_schema
    )

    print(f"   Compatible: {compat_report.compatible}")
    print(f"   Mode: {compat_report.mode.value}")

    for change in compat_report.breaking_changes:
        print(f"   Breaking: {change}")
    print()

    # 6. Type Inference
    print("6. TYPE INFERENCE:")
    print("-" * 40)

    sample_data = {
        "product_id": "prod-123",
        "name": "Widget",
        "price": 29.99,
        "in_stock": True,
        "quantity": 100,
        "categories": ["electronics", "gadgets"],
        "specs": {
            "weight": 0.5,
            "dimensions": "10x5x3"
        }
    }

    inferred = registry.infer_and_register(
        sample_data,
        "Product",
        "bael.models"
    )

    print(f"   Inferred schema: {inferred.full_name}")
    print(f"   Fields detected: {len(inferred.fields)}")

    for name, field in inferred.fields.items():
        print(f"      - {name}: {field.type.value}")
    print()

    # 7. Get Schema
    print("7. GET SCHEMA:")
    print("-" * 40)

    schema = registry.get(user_schema.full_name)
    print(f"   Latest: v{schema.version}")

    schema_v1 = registry.get(user_schema.full_name, version=1)
    print(f"   Version 1 fields: {len(schema_v1.fields)}")

    schema_v2 = registry.get(user_schema.full_name, version=2)
    print(f"   Version 2 fields: {len(schema_v2.fields)}")
    print()

    # 8. List Schemas
    print("8. LIST SCHEMAS:")
    print("-" * 40)

    schemas = registry.list_schemas()
    print(f"   Registered schemas: {len(schemas)}")

    for name in schemas:
        s = registry.get(name)
        print(f"      - {name} (v{s.version})")
    print()

    # 9. Schema Export
    print("9. SCHEMA EXPORT:")
    print("-" * 40)

    schema = registry.get(user_schema.full_name)
    schema_dict = schema.to_dict()

    print(f"   Exported to dict: {len(json.dumps(schema_dict))} bytes")
    print(f"   Sample fields:")

    for name, field_dict in list(schema_dict["fields"].items())[:3]:
        print(f"      - {name}: {field_dict['type']}")
    print()

    # 10. Field Constraints
    print("10. FIELD CONSTRAINTS:")
    print("-" * 40)

    constrained_schema = (
        SchemaBuilder("ConstrainedData", "bael.test")
        .string_field("code", required=True, min_length=5, max_length=10)
        .integer_field("count", required=True, min_value=1, max_value=100)
        .string_field("pattern_field", pattern=r"^[A-Z]{3}-\d{4}$")
        .build()
    )

    registry.register(constrained_schema)

    # Valid
    result = registry.validate(
        {"code": "ABCDE", "count": 50, "pattern_field": "ABC-1234"},
        constrained_schema.full_name
    )
    print(f"   Valid data: {result.is_valid}")

    # Invalid
    result = registry.validate(
        {"code": "AB", "count": 200, "pattern_field": "invalid"},
        constrained_schema.full_name
    )
    print(f"   Invalid data: {result.is_valid} ({len(result.errors)} errors)")
    print()

    # 11. Nested Objects
    print("11. NESTED OBJECTS:")
    print("-" * 40)

    nested_data = {
        "order_id": "ord-001",
        "customer": {
            "name": "John",
            "address": {
                "city": "New York",
                "zip": "10001"
            }
        }
    }

    nested_schema = registry.infer_and_register(
        nested_data,
        "Order",
        "bael.models"
    )

    print(f"   Inferred nested: {nested_schema.full_name}")
    print(f"   Top-level fields: {len(nested_schema.fields)}")

    customer_field = nested_schema.fields.get("customer")
    if customer_field:
        print(f"   Customer properties: {len(customer_field.properties)}")
    print()

    # 12. Registry Stats
    print("12. REGISTRY STATISTICS:")
    print("-" * 40)

    stats = registry.get_stats()
    print(f"   Total schemas: {stats['total_schemas']}")
    print(f"   Total versions: {stats['total_versions']}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Schema Registry System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
