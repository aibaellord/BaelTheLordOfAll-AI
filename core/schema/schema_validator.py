#!/usr/bin/env python3
"""
BAEL - Schema Validator
Comprehensive data schema validation system.

Features:
- JSON Schema validation
- Type validation
- Constraint validation
- Nested object validation
- Array validation
- Custom validators
- Error collection
- Schema composition
- Default values
- Coercion support
- Pattern matching
- Format validation
"""

import asyncio
import logging
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum, auto
from ipaddress import IPv4Address, IPv6Address
from typing import (Any, Callable, Dict, Generator, List, Optional, Pattern,
                    Set, Tuple, Type, TypeVar, Union)
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class SchemaType(Enum):
    """Schema types."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"
    ANY = "any"


class ValidationSeverity(Enum):
    """Validation error severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class StringFormat(Enum):
    """String format types."""
    EMAIL = "email"
    URI = "uri"
    URL = "url"
    UUID = "uuid"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    HOSTNAME = "hostname"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    HEX_COLOR = "hex_color"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ValidationError:
    """Validation error."""
    path: str
    message: str
    value: Any = None
    expected: Any = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    code: str = ""

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Validation result."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    value: Any = None  # Coerced/processed value

    def add_error(self, error: ValidationError) -> None:
        if error.severity == ValidationSeverity.ERROR:
            self.errors.append(error)
            self.valid = False
        elif error.severity == ValidationSeverity.WARNING:
            self.warnings.append(error)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another result."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False


@dataclass
class SchemaDefinition:
    """Schema definition."""
    type: Union[SchemaType, List[SchemaType]]
    required: bool = False
    nullable: bool = False
    default: Any = None

    # String constraints
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    format: Optional[StringFormat] = None
    enum: Optional[List[Any]] = None

    # Numeric constraints
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    exclusive_minimum: Optional[float] = None
    exclusive_maximum: Optional[float] = None
    multiple_of: Optional[float] = None

    # Array constraints
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: bool = False
    items: Optional["SchemaDefinition"] = None

    # Object constraints
    properties: Optional[Dict[str, "SchemaDefinition"]] = None
    required_properties: Optional[List[str]] = None
    additional_properties: Union[bool, "SchemaDefinition"] = True
    min_properties: Optional[int] = None
    max_properties: Optional[int] = None

    # Custom
    custom_validator: Optional[Callable] = None
    coerce: bool = False
    description: str = ""


# =============================================================================
# FORMAT VALIDATORS
# =============================================================================

class FormatValidator:
    """Format validators."""

    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    TIME_REGEX = re.compile(r'^\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$')
    DATETIME_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$')
    HOSTNAME_REGEX = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$')
    PHONE_REGEX = re.compile(r'^\+?[1-9]\d{1,14}$')
    CREDIT_CARD_REGEX = re.compile(r'^\d{13,19}$')
    HEX_COLOR_REGEX = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

    @classmethod
    def validate(cls, value: str, format_type: StringFormat) -> bool:
        """Validate string format."""
        validators = {
            StringFormat.EMAIL: cls._validate_email,
            StringFormat.URI: cls._validate_uri,
            StringFormat.URL: cls._validate_url,
            StringFormat.UUID: cls._validate_uuid,
            StringFormat.DATE: cls._validate_date,
            StringFormat.DATETIME: cls._validate_datetime,
            StringFormat.TIME: cls._validate_time,
            StringFormat.IPV4: cls._validate_ipv4,
            StringFormat.IPV6: cls._validate_ipv6,
            StringFormat.HOSTNAME: cls._validate_hostname,
            StringFormat.PHONE: cls._validate_phone,
            StringFormat.CREDIT_CARD: cls._validate_credit_card,
            StringFormat.HEX_COLOR: cls._validate_hex_color,
        }

        validator = validators.get(format_type)
        if validator:
            return validator(value)
        return True

    @classmethod
    def _validate_email(cls, value: str) -> bool:
        return bool(cls.EMAIL_REGEX.match(value))

    @classmethod
    def _validate_uri(cls, value: str) -> bool:
        try:
            result = urlparse(value)
            return bool(result.scheme)
        except:
            return False

    @classmethod
    def _validate_url(cls, value: str) -> bool:
        try:
            result = urlparse(value)
            return bool(result.scheme and result.netloc)
        except:
            return False

    @classmethod
    def _validate_uuid(cls, value: str) -> bool:
        return bool(cls.UUID_REGEX.match(value))

    @classmethod
    def _validate_date(cls, value: str) -> bool:
        if not cls.DATE_REGEX.match(value):
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except:
            return False

    @classmethod
    def _validate_datetime(cls, value: str) -> bool:
        if not cls.DATETIME_REGEX.match(value):
            return False
        try:
            # Try parsing
            value = value.replace('Z', '+00:00')
            datetime.fromisoformat(value)
            return True
        except:
            return False

    @classmethod
    def _validate_time(cls, value: str) -> bool:
        return bool(cls.TIME_REGEX.match(value))

    @classmethod
    def _validate_ipv4(cls, value: str) -> bool:
        try:
            IPv4Address(value)
            return True
        except:
            return False

    @classmethod
    def _validate_ipv6(cls, value: str) -> bool:
        try:
            IPv6Address(value)
            return True
        except:
            return False

    @classmethod
    def _validate_hostname(cls, value: str) -> bool:
        if len(value) > 253:
            return False
        return bool(cls.HOSTNAME_REGEX.match(value))

    @classmethod
    def _validate_phone(cls, value: str) -> bool:
        return bool(cls.PHONE_REGEX.match(value.replace(' ', '').replace('-', '')))

    @classmethod
    def _validate_credit_card(cls, value: str) -> bool:
        value = value.replace(' ', '').replace('-', '')
        if not cls.CREDIT_CARD_REGEX.match(value):
            return False
        # Luhn check
        digits = [int(d) for d in value]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0

    @classmethod
    def _validate_hex_color(cls, value: str) -> bool:
        return bool(cls.HEX_COLOR_REGEX.match(value))


# =============================================================================
# TYPE COERCER
# =============================================================================

class TypeCoercer:
    """Type coercion utilities."""

    @classmethod
    def coerce(cls, value: Any, target_type: SchemaType) -> Tuple[Any, bool]:
        """Coerce value to target type. Returns (coerced_value, success)."""
        if value is None:
            return None, True

        try:
            if target_type == SchemaType.STRING:
                return str(value), True

            elif target_type == SchemaType.INTEGER:
                if isinstance(value, str):
                    return int(float(value)), True
                return int(value), True

            elif target_type == SchemaType.NUMBER:
                return float(value), True

            elif target_type == SchemaType.BOOLEAN:
                if isinstance(value, str):
                    if value.lower() in ('true', '1', 'yes', 'on'):
                        return True, True
                    elif value.lower() in ('false', '0', 'no', 'off'):
                        return False, True
                    return None, False
                return bool(value), True

            elif target_type == SchemaType.ARRAY:
                if isinstance(value, str):
                    # Try parsing JSON array
                    import json
                    return json.loads(value), True
                elif isinstance(value, (list, tuple)):
                    return list(value), True
                return [value], True

            elif target_type == SchemaType.OBJECT:
                if isinstance(value, str):
                    import json
                    return json.loads(value), True
                elif isinstance(value, dict):
                    return value, True
                return None, False

            return value, True

        except:
            return None, False


# =============================================================================
# SCHEMA BUILDER
# =============================================================================

class SchemaBuilder:
    """Fluent schema builder."""

    def __init__(self, schema_type: Union[SchemaType, List[SchemaType]] = SchemaType.ANY):
        self._schema = SchemaDefinition(type=schema_type)

    @classmethod
    def string(cls) -> "SchemaBuilder":
        return cls(SchemaType.STRING)

    @classmethod
    def integer(cls) -> "SchemaBuilder":
        return cls(SchemaType.INTEGER)

    @classmethod
    def number(cls) -> "SchemaBuilder":
        return cls(SchemaType.NUMBER)

    @classmethod
    def boolean(cls) -> "SchemaBuilder":
        return cls(SchemaType.BOOLEAN)

    @classmethod
    def array(cls, items: Optional["SchemaBuilder"] = None) -> "SchemaBuilder":
        builder = cls(SchemaType.ARRAY)
        if items:
            builder._schema.items = items.build()
        return builder

    @classmethod
    def object(cls) -> "SchemaBuilder":
        builder = cls(SchemaType.OBJECT)
        builder._schema.properties = {}
        return builder

    def required(self, value: bool = True) -> "SchemaBuilder":
        self._schema.required = value
        return self

    def nullable(self, value: bool = True) -> "SchemaBuilder":
        self._schema.nullable = value
        return self

    def default(self, value: Any) -> "SchemaBuilder":
        self._schema.default = value
        return self

    def min_length(self, value: int) -> "SchemaBuilder":
        self._schema.min_length = value
        return self

    def max_length(self, value: int) -> "SchemaBuilder":
        self._schema.max_length = value
        return self

    def pattern(self, value: str) -> "SchemaBuilder":
        self._schema.pattern = value
        return self

    def format(self, value: StringFormat) -> "SchemaBuilder":
        self._schema.format = value
        return self

    def enum(self, values: List[Any]) -> "SchemaBuilder":
        self._schema.enum = values
        return self

    def minimum(self, value: float) -> "SchemaBuilder":
        self._schema.minimum = value
        return self

    def maximum(self, value: float) -> "SchemaBuilder":
        self._schema.maximum = value
        return self

    def exclusive_minimum(self, value: float) -> "SchemaBuilder":
        self._schema.exclusive_minimum = value
        return self

    def exclusive_maximum(self, value: float) -> "SchemaBuilder":
        self._schema.exclusive_maximum = value
        return self

    def multiple_of(self, value: float) -> "SchemaBuilder":
        self._schema.multiple_of = value
        return self

    def min_items(self, value: int) -> "SchemaBuilder":
        self._schema.min_items = value
        return self

    def max_items(self, value: int) -> "SchemaBuilder":
        self._schema.max_items = value
        return self

    def unique_items(self, value: bool = True) -> "SchemaBuilder":
        self._schema.unique_items = value
        return self

    def items(self, schema: "SchemaBuilder") -> "SchemaBuilder":
        self._schema.items = schema.build()
        return self

    def property(self, name: str, schema: "SchemaBuilder") -> "SchemaBuilder":
        if self._schema.properties is None:
            self._schema.properties = {}
        self._schema.properties[name] = schema.build()
        if schema._schema.required:
            if self._schema.required_properties is None:
                self._schema.required_properties = []
            self._schema.required_properties.append(name)
        return self

    def additional_properties(self, value: Union[bool, "SchemaBuilder"]) -> "SchemaBuilder":
        if isinstance(value, SchemaBuilder):
            self._schema.additional_properties = value.build()
        else:
            self._schema.additional_properties = value
        return self

    def custom(self, validator: Callable) -> "SchemaBuilder":
        self._schema.custom_validator = validator
        return self

    def coerce(self, value: bool = True) -> "SchemaBuilder":
        self._schema.coerce = value
        return self

    def description(self, value: str) -> "SchemaBuilder":
        self._schema.description = value
        return self

    def build(self) -> SchemaDefinition:
        return self._schema


# =============================================================================
# SCHEMA VALIDATOR
# =============================================================================

class SchemaValidator:
    """
    Comprehensive Schema Validator for BAEL.

    Validates data against schema definitions.
    """

    def __init__(self):
        self._schemas: Dict[str, SchemaDefinition] = {}
        self._custom_validators: Dict[str, Callable] = {}
        self._custom_formats: Dict[str, Callable[[str], bool]] = {}

    # -------------------------------------------------------------------------
    # SCHEMA REGISTRATION
    # -------------------------------------------------------------------------

    def register_schema(self, name: str, schema: SchemaDefinition) -> None:
        """Register a named schema."""
        self._schemas[name] = schema

    def get_schema(self, name: str) -> Optional[SchemaDefinition]:
        """Get a registered schema."""
        return self._schemas.get(name)

    def register_validator(self, name: str, validator: Callable) -> None:
        """Register a custom validator."""
        self._custom_validators[name] = validator

    def register_format(self, name: str, validator: Callable[[str], bool]) -> None:
        """Register a custom format validator."""
        self._custom_formats[name] = validator

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    def validate(
        self,
        data: Any,
        schema: Union[str, SchemaDefinition],
        path: str = "$"
    ) -> ValidationResult:
        """Validate data against schema."""
        if isinstance(schema, str):
            schema = self._schemas.get(schema)
            if not schema:
                return ValidationResult(
                    valid=False,
                    errors=[ValidationError(path, f"Schema '{schema}' not found")]
                )

        result = ValidationResult(valid=True)

        # Handle null/None
        if data is None:
            if schema.nullable:
                result.value = None
                return result
            elif schema.default is not None:
                result.value = schema.default
                return result
            elif schema.required:
                result.add_error(ValidationError(path, "Value is required", code="required"))
                return result
            else:
                result.value = None
                return result

        # Type coercion
        if schema.coerce and data is not None:
            target_type = schema.type if isinstance(schema.type, SchemaType) else schema.type[0]
            coerced, success = TypeCoercer.coerce(data, target_type)
            if success:
                data = coerced

        # Type validation
        type_valid = self._validate_type(data, schema, path, result)
        if not type_valid:
            return result

        # Type-specific validation
        schema_type = schema.type if isinstance(schema.type, SchemaType) else self._get_value_type(data)

        if schema_type == SchemaType.STRING:
            self._validate_string(data, schema, path, result)
        elif schema_type == SchemaType.INTEGER:
            self._validate_number(data, schema, path, result)
        elif schema_type == SchemaType.NUMBER:
            self._validate_number(data, schema, path, result)
        elif schema_type == SchemaType.ARRAY:
            self._validate_array(data, schema, path, result)
        elif schema_type == SchemaType.OBJECT:
            self._validate_object(data, schema, path, result)

        # Enum validation
        if schema.enum is not None:
            if data not in schema.enum:
                result.add_error(ValidationError(
                    path, f"Value must be one of: {schema.enum}",
                    value=data, expected=schema.enum, code="enum"
                ))

        # Custom validator
        if schema.custom_validator:
            try:
                custom_result = schema.custom_validator(data, path)
                if isinstance(custom_result, ValidationResult):
                    result.merge(custom_result)
                elif isinstance(custom_result, str):
                    result.add_error(ValidationError(path, custom_result, code="custom"))
                elif custom_result is False:
                    result.add_error(ValidationError(path, "Custom validation failed", code="custom"))
            except Exception as e:
                result.add_error(ValidationError(path, f"Custom validator error: {e}", code="custom_error"))

        result.value = data
        return result

    def _validate_type(
        self,
        data: Any,
        schema: SchemaDefinition,
        path: str,
        result: ValidationResult
    ) -> bool:
        """Validate value type."""
        if schema.type == SchemaType.ANY:
            return True

        allowed_types = [schema.type] if isinstance(schema.type, SchemaType) else schema.type
        value_type = self._get_value_type(data)

        # Special case: integer is also a number
        if value_type == SchemaType.INTEGER and SchemaType.NUMBER in allowed_types:
            return True

        if value_type not in allowed_types:
            expected = [t.value for t in allowed_types]
            result.add_error(ValidationError(
                path, f"Expected type {expected}, got {value_type.value}",
                value=data, expected=expected, code="type"
            ))
            return False

        return True

    def _get_value_type(self, value: Any) -> SchemaType:
        """Get schema type of value."""
        if value is None:
            return SchemaType.NULL
        elif isinstance(value, bool):
            return SchemaType.BOOLEAN
        elif isinstance(value, int):
            return SchemaType.INTEGER
        elif isinstance(value, float):
            return SchemaType.NUMBER
        elif isinstance(value, str):
            return SchemaType.STRING
        elif isinstance(value, (list, tuple)):
            return SchemaType.ARRAY
        elif isinstance(value, dict):
            return SchemaType.OBJECT
        return SchemaType.ANY

    def _validate_string(
        self,
        data: str,
        schema: SchemaDefinition,
        path: str,
        result: ValidationResult
    ) -> None:
        """Validate string value."""
        if schema.min_length is not None and len(data) < schema.min_length:
            result.add_error(ValidationError(
                path, f"String length must be at least {schema.min_length}",
                value=data, expected=f">= {schema.min_length}", code="min_length"
            ))

        if schema.max_length is not None and len(data) > schema.max_length:
            result.add_error(ValidationError(
                path, f"String length must be at most {schema.max_length}",
                value=data, expected=f"<= {schema.max_length}", code="max_length"
            ))

        if schema.pattern:
            if not re.match(schema.pattern, data):
                result.add_error(ValidationError(
                    path, f"String does not match pattern: {schema.pattern}",
                    value=data, expected=schema.pattern, code="pattern"
                ))

        if schema.format:
            if isinstance(schema.format, StringFormat):
                if not FormatValidator.validate(data, schema.format):
                    result.add_error(ValidationError(
                        path, f"Invalid {schema.format.value} format",
                        value=data, expected=schema.format.value, code="format"
                    ))
            elif isinstance(schema.format, str) and schema.format in self._custom_formats:
                if not self._custom_formats[schema.format](data):
                    result.add_error(ValidationError(
                        path, f"Invalid {schema.format} format",
                        value=data, code="format"
                    ))

    def _validate_number(
        self,
        data: Union[int, float],
        schema: SchemaDefinition,
        path: str,
        result: ValidationResult
    ) -> None:
        """Validate numeric value."""
        if schema.minimum is not None and data < schema.minimum:
            result.add_error(ValidationError(
                path, f"Value must be >= {schema.minimum}",
                value=data, expected=f">= {schema.minimum}", code="minimum"
            ))

        if schema.maximum is not None and data > schema.maximum:
            result.add_error(ValidationError(
                path, f"Value must be <= {schema.maximum}",
                value=data, expected=f"<= {schema.maximum}", code="maximum"
            ))

        if schema.exclusive_minimum is not None and data <= schema.exclusive_minimum:
            result.add_error(ValidationError(
                path, f"Value must be > {schema.exclusive_minimum}",
                value=data, expected=f"> {schema.exclusive_minimum}", code="exclusive_minimum"
            ))

        if schema.exclusive_maximum is not None and data >= schema.exclusive_maximum:
            result.add_error(ValidationError(
                path, f"Value must be < {schema.exclusive_maximum}",
                value=data, expected=f"< {schema.exclusive_maximum}", code="exclusive_maximum"
            ))

        if schema.multiple_of is not None:
            if data % schema.multiple_of != 0:
                result.add_error(ValidationError(
                    path, f"Value must be a multiple of {schema.multiple_of}",
                    value=data, expected=f"multiple of {schema.multiple_of}", code="multiple_of"
                ))

    def _validate_array(
        self,
        data: List,
        schema: SchemaDefinition,
        path: str,
        result: ValidationResult
    ) -> None:
        """Validate array value."""
        if schema.min_items is not None and len(data) < schema.min_items:
            result.add_error(ValidationError(
                path, f"Array must have at least {schema.min_items} items",
                value=len(data), expected=f">= {schema.min_items}", code="min_items"
            ))

        if schema.max_items is not None and len(data) > schema.max_items:
            result.add_error(ValidationError(
                path, f"Array must have at most {schema.max_items} items",
                value=len(data), expected=f"<= {schema.max_items}", code="max_items"
            ))

        if schema.unique_items:
            seen = set()
            for i, item in enumerate(data):
                item_hash = hash(str(item))
                if item_hash in seen:
                    result.add_error(ValidationError(
                        f"{path}[{i}]", "Duplicate item in array",
                        value=item, code="unique_items"
                    ))
                seen.add(item_hash)

        if schema.items:
            for i, item in enumerate(data):
                item_result = self.validate(item, schema.items, f"{path}[{i}]")
                result.merge(item_result)

    def _validate_object(
        self,
        data: Dict,
        schema: SchemaDefinition,
        path: str,
        result: ValidationResult
    ) -> None:
        """Validate object value."""
        if schema.min_properties is not None and len(data) < schema.min_properties:
            result.add_error(ValidationError(
                path, f"Object must have at least {schema.min_properties} properties",
                value=len(data), code="min_properties"
            ))

        if schema.max_properties is not None and len(data) > schema.max_properties:
            result.add_error(ValidationError(
                path, f"Object must have at most {schema.max_properties} properties",
                value=len(data), code="max_properties"
            ))

        # Check required properties
        if schema.required_properties:
            for prop in schema.required_properties:
                if prop not in data:
                    result.add_error(ValidationError(
                        f"{path}.{prop}", f"Required property '{prop}' is missing",
                        code="required"
                    ))

        # Validate defined properties
        if schema.properties:
            for prop_name, prop_schema in schema.properties.items():
                if prop_name in data:
                    prop_result = self.validate(
                        data[prop_name], prop_schema, f"{path}.{prop_name}"
                    )
                    result.merge(prop_result)
                elif prop_schema.default is not None:
                    data[prop_name] = prop_schema.default

        # Check additional properties
        if schema.properties:
            defined_props = set(schema.properties.keys())
            for prop_name in data.keys():
                if prop_name not in defined_props:
                    if schema.additional_properties is False:
                        result.add_error(ValidationError(
                            f"{path}.{prop_name}",
                            f"Additional property '{prop_name}' is not allowed",
                            code="additional_properties"
                        ))
                    elif isinstance(schema.additional_properties, SchemaDefinition):
                        prop_result = self.validate(
                            data[prop_name],
                            schema.additional_properties,
                            f"{path}.{prop_name}"
                        )
                        result.merge(prop_result)

    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------

    def is_valid(
        self,
        data: Any,
        schema: Union[str, SchemaDefinition]
    ) -> bool:
        """Check if data is valid."""
        return self.validate(data, schema).valid

    def validate_many(
        self,
        items: List[Any],
        schema: Union[str, SchemaDefinition]
    ) -> List[ValidationResult]:
        """Validate multiple items."""
        return [self.validate(item, schema) for item in items]

    def get_errors(
        self,
        data: Any,
        schema: Union[str, SchemaDefinition]
    ) -> List[ValidationError]:
        """Get validation errors only."""
        return self.validate(data, schema).errors

    # -------------------------------------------------------------------------
    # SCHEMA INTROSPECTION
    # -------------------------------------------------------------------------

    def list_schemas(self) -> List[str]:
        """List registered schemas."""
        return list(self._schemas.keys())

    def schema_to_dict(self, schema: SchemaDefinition) -> Dict:
        """Convert schema to dictionary (JSON Schema-like)."""
        result = {}

        if isinstance(schema.type, list):
            result["type"] = [t.value for t in schema.type]
        else:
            result["type"] = schema.type.value

        if schema.required:
            result["required"] = True
        if schema.nullable:
            result["nullable"] = True
        if schema.default is not None:
            result["default"] = schema.default
        if schema.description:
            result["description"] = schema.description

        # String
        if schema.min_length is not None:
            result["minLength"] = schema.min_length
        if schema.max_length is not None:
            result["maxLength"] = schema.max_length
        if schema.pattern:
            result["pattern"] = schema.pattern
        if schema.format:
            result["format"] = schema.format.value if isinstance(schema.format, StringFormat) else schema.format
        if schema.enum:
            result["enum"] = schema.enum

        # Numeric
        if schema.minimum is not None:
            result["minimum"] = schema.minimum
        if schema.maximum is not None:
            result["maximum"] = schema.maximum
        if schema.exclusive_minimum is not None:
            result["exclusiveMinimum"] = schema.exclusive_minimum
        if schema.exclusive_maximum is not None:
            result["exclusiveMaximum"] = schema.exclusive_maximum
        if schema.multiple_of is not None:
            result["multipleOf"] = schema.multiple_of

        # Array
        if schema.min_items is not None:
            result["minItems"] = schema.min_items
        if schema.max_items is not None:
            result["maxItems"] = schema.max_items
        if schema.unique_items:
            result["uniqueItems"] = True
        if schema.items:
            result["items"] = self.schema_to_dict(schema.items)

        # Object
        if schema.properties:
            result["properties"] = {
                k: self.schema_to_dict(v) for k, v in schema.properties.items()
            }
        if schema.required_properties:
            result["required"] = schema.required_properties
        if schema.additional_properties is False:
            result["additionalProperties"] = False
        elif isinstance(schema.additional_properties, SchemaDefinition):
            result["additionalProperties"] = self.schema_to_dict(schema.additional_properties)

        return result


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Schema Validator."""
    print("=" * 70)
    print("BAEL - SCHEMA VALIDATOR DEMO")
    print("Comprehensive Data Validation System")
    print("=" * 70)
    print()

    validator = SchemaValidator()

    # 1. Basic Type Validation
    print("1. BASIC TYPE VALIDATION:")
    print("-" * 40)

    string_schema = SchemaBuilder.string().min_length(3).max_length(50).build()

    test_values = ["Hello", "Hi", "", "A" * 100]
    for value in test_values:
        result = validator.validate(value, string_schema)
        status = "✓" if result.valid else "✗"
        print(f"   {status} '{value[:20]}...' - {result.errors[0].message if result.errors else 'Valid'}")
    print()

    # 2. Numeric Validation
    print("2. NUMERIC VALIDATION:")
    print("-" * 40)

    number_schema = (SchemaBuilder.number()
                    .minimum(0)
                    .maximum(100)
                    .build())

    test_values = [50, 0, 100, -5, 150]
    for value in test_values:
        result = validator.validate(value, number_schema)
        status = "✓" if result.valid else "✗"
        print(f"   {status} {value} - {result.errors[0].message if result.errors else 'Valid'}")
    print()

    # 3. Email Format Validation
    print("3. EMAIL FORMAT VALIDATION:")
    print("-" * 40)

    email_schema = (SchemaBuilder.string()
                   .format(StringFormat.EMAIL)
                   .build())

    emails = [
        "user@example.com",
        "invalid-email",
        "test@domain.org",
        "no-at-sign.com"
    ]

    for email in emails:
        result = validator.validate(email, email_schema)
        status = "✓" if result.valid else "✗"
        print(f"   {status} {email}")
    print()

    # 4. Object Schema
    print("4. OBJECT SCHEMA:")
    print("-" * 40)

    user_schema = (SchemaBuilder.object()
                  .property("name", SchemaBuilder.string().min_length(1).required())
                  .property("age", SchemaBuilder.integer().minimum(0).maximum(150))
                  .property("email", SchemaBuilder.string().format(StringFormat.EMAIL).required())
                  .additional_properties(False)
                  .build())

    validator.register_schema("user", user_schema)

    users = [
        {"name": "Alice", "age": 30, "email": "alice@example.com"},
        {"name": "", "age": 25, "email": "bob@test.com"},  # Empty name
        {"name": "Charlie", "age": -5, "email": "invalid"},  # Invalid age and email
        {"name": "David", "age": 40, "email": "david@test.com", "extra": "field"}  # Extra field
    ]

    for i, user in enumerate(users):
        result = validator.validate(user, "user")
        status = "✓" if result.valid else "✗"
        errors = ", ".join(str(e) for e in result.errors) if result.errors else "Valid"
        print(f"   {status} User {i + 1}: {errors}")
    print()

    # 5. Array Validation
    print("5. ARRAY VALIDATION:")
    print("-" * 40)

    tags_schema = (SchemaBuilder.array(SchemaBuilder.string().min_length(1))
                  .min_items(1)
                  .max_items(5)
                  .unique_items()
                  .build())

    tag_lists = [
        ["python", "javascript", "rust"],
        [],  # Empty
        ["a", "b", "c", "d", "e", "f"],  # Too many
        ["go", "go", "python"]  # Duplicates
    ]

    for tags in tag_lists:
        result = validator.validate(tags, tags_schema)
        status = "✓" if result.valid else "✗"
        errors = result.errors[0].message if result.errors else "Valid"
        print(f"   {status} {tags} - {errors}")
    print()

    # 6. Enum Validation
    print("6. ENUM VALIDATION:")
    print("-" * 40)

    status_schema = (SchemaBuilder.string()
                    .enum(["pending", "active", "completed", "cancelled"])
                    .build())

    statuses = ["active", "pending", "unknown", "ACTIVE"]

    for status in statuses:
        result = validator.validate(status, status_schema)
        valid = "✓" if result.valid else "✗"
        print(f"   {valid} '{status}'")
    print()

    # 7. Pattern Validation
    print("7. PATTERN VALIDATION:")
    print("-" * 40)

    phone_schema = (SchemaBuilder.string()
                   .pattern(r'^\+?[1-9]\d{1,14}$')
                   .build())

    phones = ["+1234567890", "123456789", "abc123", "+0123456"]

    for phone in phones:
        result = validator.validate(phone, phone_schema)
        status = "✓" if result.valid else "✗"
        print(f"   {status} '{phone}'")
    print()

    # 8. Nested Objects
    print("8. NESTED OBJECTS:")
    print("-" * 40)

    address_schema = (SchemaBuilder.object()
                     .property("street", SchemaBuilder.string().required())
                     .property("city", SchemaBuilder.string().required())
                     .property("zip", SchemaBuilder.string().pattern(r'^\d{5}$'))
                     .build())

    profile_schema = (SchemaBuilder.object()
                     .property("name", SchemaBuilder.string().required())
                     .property("address", SchemaBuilder(address_schema.type))
                     .build())
    profile_schema.properties["address"] = address_schema

    profiles = [
        {
            "name": "Alice",
            "address": {"street": "123 Main St", "city": "Boston", "zip": "02101"}
        },
        {
            "name": "Bob",
            "address": {"street": "456 Oak Ave", "city": "Chicago", "zip": "invalid"}
        }
    ]

    for profile in profiles:
        result = validator.validate(profile, profile_schema)
        status = "✓" if result.valid else "✗"
        errors = ", ".join(str(e) for e in result.errors) if result.errors else "Valid"
        print(f"   {status} {profile['name']}: {errors}")
    print()

    # 9. Type Coercion
    print("9. TYPE COERCION:")
    print("-" * 40)

    coerce_schema = (SchemaBuilder.integer()
                    .minimum(0)
                    .coerce()
                    .build())

    values = ["42", "3.14", 100, "abc"]

    for value in values:
        result = validator.validate(value, coerce_schema)
        status = "✓" if result.valid else "✗"
        coerced = result.value if result.valid else "N/A"
        print(f"   {status} {repr(value)} -> {coerced}")
    print()

    # 10. Default Values
    print("10. DEFAULT VALUES:")
    print("-" * 40)

    config_schema = (SchemaBuilder.object()
                    .property("timeout", SchemaBuilder.integer().default(30))
                    .property("retries", SchemaBuilder.integer().default(3))
                    .property("debug", SchemaBuilder.boolean().default(False))
                    .build())

    configs = [
        {},
        {"timeout": 60},
        {"timeout": 10, "retries": 5, "debug": True}
    ]

    for config in configs:
        result = validator.validate(config.copy(), config_schema)
        print(f"   Input: {config}")
        print(f"   Result: {result.value if result.valid else 'Invalid'}")
    print()

    # 11. Custom Validator
    print("11. CUSTOM VALIDATOR:")
    print("-" * 40)

    def validate_even(value: int, path: str) -> Optional[str]:
        if value % 2 != 0:
            return "Value must be even"
        return None

    even_schema = (SchemaBuilder.integer()
                  .custom(validate_even)
                  .build())

    for value in [2, 4, 5, 10, 11]:
        result = validator.validate(value, even_schema)
        status = "✓" if result.valid else "✗"
        print(f"   {status} {value}")
    print()

    # 12. Format Validators
    print("12. FORMAT VALIDATORS:")
    print("-" * 40)

    formats_to_test = [
        (StringFormat.UUID, "550e8400-e29b-41d4-a716-446655440000"),
        (StringFormat.IPV4, "192.168.1.1"),
        (StringFormat.URL, "https://example.com"),
        (StringFormat.DATE, "2024-01-15"),
        (StringFormat.HEX_COLOR, "#FF5733"),
    ]

    for format_type, value in formats_to_test:
        schema = SchemaBuilder.string().format(format_type).build()
        result = validator.validate(value, schema)
        status = "✓" if result.valid else "✗"
        print(f"   {status} {format_type.value}: {value}")
    print()

    # 13. Multiple Types
    print("13. MULTIPLE TYPES:")
    print("-" * 40)

    multi_schema = SchemaDefinition(type=[SchemaType.STRING, SchemaType.INTEGER])

    values = ["hello", 42, 3.14, True, None]

    for value in values:
        result = validator.validate(value, multi_schema)
        status = "✓" if result.valid else "✗"
        print(f"   {status} {repr(value)} ({type(value).__name__})")
    print()

    # 14. Schema Introspection
    print("14. SCHEMA INTROSPECTION:")
    print("-" * 40)

    product_schema = (SchemaBuilder.object()
                     .property("name", SchemaBuilder.string().min_length(1).required())
                     .property("price", SchemaBuilder.number().minimum(0).required())
                     .property("quantity", SchemaBuilder.integer().minimum(0).default(0))
                     .build())

    schema_dict = validator.schema_to_dict(product_schema)
    import json
    print(f"   Schema as JSON:")
    print(f"   {json.dumps(schema_dict, indent=4)[:200]}...")
    print()

    # 15. Bulk Validation
    print("15. BULK VALIDATION:")
    print("-" * 40)

    score_schema = SchemaBuilder.integer().minimum(0).maximum(100).build()

    scores = [85, 92, 78, 105, -10, 67, 88, 200]
    results = validator.validate_many(scores, score_schema)

    valid_count = sum(1 for r in results if r.valid)
    print(f"   Validated {len(scores)} scores")
    print(f"   Valid: {valid_count}, Invalid: {len(scores) - valid_count}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Schema Validator Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
