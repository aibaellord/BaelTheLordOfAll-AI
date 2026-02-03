#!/usr/bin/env python3
"""
BAEL - Data Validation System
Comprehensive data validation and schema enforcement.

This module provides a complete data validation framework
for ensuring data integrity and type safety.

Features:
- Schema-based validation
- Type checking and coercion
- Nested object validation
- Array validation
- Custom validators
- Conditional validation
- Async validation
- Error aggregation
- Sanitization
- Default values
"""

import asyncio
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
from typing import (Any, Callable, Dict, Generic, List, Optional, Pattern, Set,
                    Tuple, Type, TypeVar, Union, get_args, get_origin,
                    get_type_hints)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ValidatorType(Enum):
    """Types of validators."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    EMAIL = "email"
    URL = "url"
    ENUM = "enum"
    ANY = "any"
    UNION = "union"


class ValidationSeverity(Enum):
    """Validation error severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CoercionMode(Enum):
    """Type coercion mode."""
    NONE = "none"
    SAFE = "safe"
    STRICT = "strict"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ValidationError:
    """A validation error."""
    path: str
    message: str
    value: Any = None
    code: str = "validation_error"
    severity: ValidationSeverity = ValidationSeverity.ERROR
    context: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    value: Any = None  # Transformed/coerced value

    def add_error(
        self,
        path: str,
        message: str,
        value: Any = None,
        code: str = "validation_error"
    ) -> None:
        """Add an error."""
        self.errors.append(ValidationError(
            path=path,
            message=message,
            value=value,
            code=code
        ))
        self.valid = False

    def add_warning(
        self,
        path: str,
        message: str,
        value: Any = None
    ) -> None:
        """Add a warning."""
        self.warnings.append(ValidationError(
            path=path,
            message=message,
            value=value,
            severity=ValidationSeverity.WARNING
        ))

    def merge(self, other: 'ValidationResult') -> None:
        """Merge another result."""
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": [
                {"path": e.path, "message": e.message, "code": e.code}
                for e in self.errors
            ],
            "warnings": [
                {"path": w.path, "message": w.message}
                for w in self.warnings
            ]
        }


@dataclass
class FieldContext:
    """Context for field validation."""
    path: str
    value: Any
    parent: Any = None
    root: Any = None
    siblings: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# VALIDATORS
# =============================================================================

class Validator(ABC):
    """Abstract base validator."""

    @abstractmethod
    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        """Validate a value."""
        pass

    def __and__(self, other: 'Validator') -> 'AndValidator':
        """Combine with AND."""
        return AndValidator([self, other])

    def __or__(self, other: 'Validator') -> 'OrValidator':
        """Combine with OR."""
        return OrValidator([self, other])


class AndValidator(Validator):
    """Combines validators with AND."""

    def __init__(self, validators: List[Validator]):
        self.validators = validators

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True, value=value)

        for validator in self.validators:
            sub_result = validator.validate(value, context)
            result.merge(sub_result)
            if sub_result.value is not None:
                value = sub_result.value

        result.value = value
        return result


class OrValidator(Validator):
    """Combines validators with OR."""

    def __init__(self, validators: List[Validator]):
        self.validators = validators

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        all_errors = []

        for validator in self.validators:
            sub_result = validator.validate(value, context)
            if sub_result.valid:
                return sub_result
            all_errors.extend(sub_result.errors)

        result = ValidationResult(valid=False, value=value)
        result.errors = all_errors
        return result


class StringValidator(Validator):
    """String validator."""

    def __init__(
        self,
        min_length: int = None,
        max_length: int = None,
        pattern: str = None,
        enum: List[str] = None,
        trim: bool = False,
        lowercase: bool = False,
        uppercase: bool = False
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        self.enum = set(enum) if enum else None
        self.trim = trim
        self.lowercase = lowercase
        self.uppercase = uppercase

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, str):
            result.add_error(context.path, f"Expected string, got {type(value).__name__}", value)
            return result

        # Transformations
        if self.trim:
            value = value.strip()
        if self.lowercase:
            value = value.lower()
        if self.uppercase:
            value = value.upper()

        result.value = value

        # Length checks
        if self.min_length is not None and len(value) < self.min_length:
            result.add_error(
                context.path,
                f"String too short (min {self.min_length})",
                value,
                "string_too_short"
            )

        if self.max_length is not None and len(value) > self.max_length:
            result.add_error(
                context.path,
                f"String too long (max {self.max_length})",
                value,
                "string_too_long"
            )

        # Pattern check
        if self.pattern and not self.pattern.match(value):
            result.add_error(
                context.path,
                f"String does not match pattern",
                value,
                "pattern_mismatch"
            )

        # Enum check
        if self.enum and value not in self.enum:
            result.add_error(
                context.path,
                f"Value not in allowed values: {self.enum}",
                value,
                "invalid_enum"
            )

        return result


class NumberValidator(Validator):
    """Number validator."""

    def __init__(
        self,
        min_value: float = None,
        max_value: float = None,
        integer_only: bool = False,
        positive: bool = False,
        negative: bool = False,
        allow_infinity: bool = False,
        coerce: bool = False
    ):
        self.min_value = min_value
        self.max_value = max_value
        self.integer_only = integer_only
        self.positive = positive
        self.negative = negative
        self.allow_infinity = allow_infinity
        self.coerce = coerce

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        # Coercion
        if self.coerce and isinstance(value, str):
            try:
                if self.integer_only:
                    value = int(value)
                else:
                    value = float(value)
            except ValueError:
                result.add_error(context.path, f"Cannot convert to number: {value}", value)
                return result

        if not isinstance(value, (int, float, Decimal)):
            result.add_error(context.path, f"Expected number, got {type(value).__name__}", value)
            return result

        result.value = value

        # Integer check
        if self.integer_only and not isinstance(value, int):
            if not float(value).is_integer():
                result.add_error(context.path, "Expected integer", value, "not_integer")

        # Infinity check
        if not self.allow_infinity and isinstance(value, float):
            if value == float('inf') or value == float('-inf'):
                result.add_error(context.path, "Infinity not allowed", value, "infinity")

        # Range checks
        if self.min_value is not None and value < self.min_value:
            result.add_error(context.path, f"Value too small (min {self.min_value})", value, "too_small")

        if self.max_value is not None and value > self.max_value:
            result.add_error(context.path, f"Value too large (max {self.max_value})", value, "too_large")

        # Sign checks
        if self.positive and value <= 0:
            result.add_error(context.path, "Must be positive", value, "not_positive")

        if self.negative and value >= 0:
            result.add_error(context.path, "Must be negative", value, "not_negative")

        return result


class BooleanValidator(Validator):
    """Boolean validator."""

    def __init__(self, coerce: bool = False):
        self.coerce = coerce
        self.truthy = {"true", "1", "yes", "on"}
        self.falsy = {"false", "0", "no", "off"}

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if self.coerce and isinstance(value, str):
            lower = value.lower()
            if lower in self.truthy:
                value = True
            elif lower in self.falsy:
                value = False

        if not isinstance(value, bool):
            result.add_error(context.path, f"Expected boolean, got {type(value).__name__}", value)
            return result

        result.value = value
        return result


class ArrayValidator(Validator):
    """Array validator."""

    def __init__(
        self,
        item_validator: Validator = None,
        min_length: int = None,
        max_length: int = None,
        unique: bool = False
    ):
        self.item_validator = item_validator
        self.min_length = min_length
        self.max_length = max_length
        self.unique = unique

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, (list, tuple)):
            result.add_error(context.path, f"Expected array, got {type(value).__name__}", value)
            return result

        # Length checks
        if self.min_length is not None and len(value) < self.min_length:
            result.add_error(context.path, f"Array too short (min {self.min_length})", value)

        if self.max_length is not None and len(value) > self.max_length:
            result.add_error(context.path, f"Array too long (max {self.max_length})", value)

        # Uniqueness check
        if self.unique:
            seen = set()
            for i, item in enumerate(value):
                # Use JSON repr for hashable comparison
                try:
                    item_repr = str(item)
                    if item_repr in seen:
                        result.add_error(f"{context.path}[{i}]", "Duplicate value", item)
                    seen.add(item_repr)
                except:
                    pass

        # Validate items
        validated_items = []
        if self.item_validator:
            for i, item in enumerate(value):
                item_context = FieldContext(
                    path=f"{context.path}[{i}]",
                    value=item,
                    parent=value,
                    root=context.root
                )
                item_result = self.item_validator.validate(item, item_context)
                result.merge(item_result)
                validated_items.append(item_result.value if item_result.value is not None else item)
            result.value = validated_items
        else:
            result.value = list(value)

        return result


class ObjectValidator(Validator):
    """Object/dict validator."""

    def __init__(
        self,
        schema: Dict[str, 'FieldSchema'] = None,
        additional_properties: bool = True,
        strip_unknown: bool = False
    ):
        self.schema = schema or {}
        self.additional_properties = additional_properties
        self.strip_unknown = strip_unknown

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, dict):
            result.add_error(context.path, f"Expected object, got {type(value).__name__}", value)
            return result

        validated = {}
        schema_keys = set(self.schema.keys())
        value_keys = set(value.keys())

        # Check for unknown keys
        unknown_keys = value_keys - schema_keys
        if unknown_keys and not self.additional_properties:
            for key in unknown_keys:
                result.add_error(f"{context.path}.{key}", f"Unknown property: {key}", value[key])

        # Validate schema fields
        for key, field_schema in self.schema.items():
            field_value = value.get(key)
            field_path = f"{context.path}.{key}" if context.path else key

            field_context = FieldContext(
                path=field_path,
                value=field_value,
                parent=value,
                root=context.root or value,
                siblings=value
            )

            field_result = field_schema.validate(field_context)
            result.merge(field_result)

            if field_result.value is not None:
                validated[key] = field_result.value
            elif key in value:
                validated[key] = value[key]

        # Include additional properties
        if self.additional_properties and not self.strip_unknown:
            for key in unknown_keys:
                validated[key] = value[key]

        result.value = validated
        return result


class EmailValidator(Validator):
    """Email validator."""

    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def __init__(self, normalize: bool = True):
        self.normalize = normalize

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, str):
            result.add_error(context.path, "Expected string for email", value)
            return result

        if self.normalize:
            value = value.strip().lower()

        if not self.EMAIL_PATTERN.match(value):
            result.add_error(context.path, "Invalid email format", value, "invalid_email")

        result.value = value
        return result


class URLValidator(Validator):
    """URL validator."""

    URL_PATTERN = re.compile(
        r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    )

    def __init__(self, require_https: bool = False):
        self.require_https = require_https

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, str):
            result.add_error(context.path, "Expected string for URL", value)
            return result

        if not self.URL_PATTERN.match(value):
            result.add_error(context.path, "Invalid URL format", value, "invalid_url")
        elif self.require_https and not value.startswith("https://"):
            result.add_error(context.path, "HTTPS required", value, "https_required")

        result.value = value
        return result


class UUIDValidator(Validator):
    """UUID validator."""

    def __init__(self, version: int = None):
        self.version = version

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        try:
            if isinstance(value, str):
                parsed = uuid.UUID(value)
            elif isinstance(value, uuid.UUID):
                parsed = value
            else:
                result.add_error(context.path, "Invalid UUID type", value)
                return result

            if self.version and parsed.version != self.version:
                result.add_error(context.path, f"UUID version must be {self.version}", value)

            result.value = str(parsed)

        except ValueError:
            result.add_error(context.path, "Invalid UUID format", value, "invalid_uuid")

        return result


class DateValidator(Validator):
    """Date validator."""

    def __init__(
        self,
        format: str = "%Y-%m-%d",
        min_date: date = None,
        max_date: date = None
    ):
        self.format = format
        self.min_date = min_date
        self.max_date = max_date

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if isinstance(value, date):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.strptime(value, self.format).date()
            except ValueError:
                result.add_error(context.path, f"Invalid date format (expected {self.format})", value)
                return result
        else:
            result.add_error(context.path, "Expected date or string", value)
            return result

        if self.min_date and parsed < self.min_date:
            result.add_error(context.path, f"Date too early (min {self.min_date})", value)

        if self.max_date and parsed > self.max_date:
            result.add_error(context.path, f"Date too late (max {self.max_date})", value)

        result.value = parsed
        return result


class CustomValidator(Validator):
    """Custom function validator."""

    def __init__(
        self,
        func: Callable[[Any, FieldContext], ValidationResult],
        is_async: bool = False
    ):
        self.func = func
        self.is_async = is_async

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        if self.is_async:
            # Handle async validation
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self.func(value, context))
            except RuntimeError:
                # No event loop
                return asyncio.run(self.func(value, context))
        else:
            return self.func(value, context)


class ConditionalValidator(Validator):
    """Conditional validator based on sibling values."""

    def __init__(
        self,
        condition: Callable[[Dict[str, Any]], bool],
        then_validator: Validator,
        else_validator: Validator = None
    ):
        self.condition = condition
        self.then_validator = then_validator
        self.else_validator = else_validator

    def validate(self, value: Any, context: FieldContext) -> ValidationResult:
        if self.condition(context.siblings):
            return self.then_validator.validate(value, context)
        elif self.else_validator:
            return self.else_validator.validate(value, context)
        else:
            return ValidationResult(valid=True, value=value)


# =============================================================================
# FIELD SCHEMA
# =============================================================================

@dataclass
class FieldSchema:
    """Schema for a field."""
    validator: Validator
    required: bool = False
    nullable: bool = True
    default: Any = None
    default_factory: Callable[[], Any] = None
    description: str = ""

    def validate(self, context: FieldContext) -> ValidationResult:
        """Validate a field."""
        value = context.value

        # Handle missing/None values
        if value is None:
            if self.default_factory:
                return ValidationResult(valid=True, value=self.default_factory())
            elif self.default is not None:
                return ValidationResult(valid=True, value=self.default)
            elif self.required:
                result = ValidationResult(valid=False)
                result.add_error(context.path, "Required field missing", code="required")
                return result
            elif not self.nullable:
                result = ValidationResult(valid=False)
                result.add_error(context.path, "Field cannot be null", code="not_nullable")
                return result
            else:
                return ValidationResult(valid=True, value=None)

        # Run validator
        return self.validator.validate(value, context)


# =============================================================================
# SCHEMA BUILDER
# =============================================================================

class SchemaBuilder:
    """Fluent schema builder."""

    def __init__(self):
        self.fields: Dict[str, FieldSchema] = {}

    def string(
        self,
        name: str,
        required: bool = False,
        min_length: int = None,
        max_length: int = None,
        pattern: str = None,
        enum: List[str] = None,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add string field."""
        validator = StringValidator(
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            enum=enum
        )
        self.fields[name] = FieldSchema(validator, required=required, **kwargs)
        return self

    def number(
        self,
        name: str,
        required: bool = False,
        min_value: float = None,
        max_value: float = None,
        integer_only: bool = False,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add number field."""
        validator = NumberValidator(
            min_value=min_value,
            max_value=max_value,
            integer_only=integer_only
        )
        self.fields[name] = FieldSchema(validator, required=required, **kwargs)
        return self

    def boolean(
        self,
        name: str,
        required: bool = False,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add boolean field."""
        self.fields[name] = FieldSchema(BooleanValidator(), required=required, **kwargs)
        return self

    def email(
        self,
        name: str,
        required: bool = False,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add email field."""
        self.fields[name] = FieldSchema(EmailValidator(), required=required, **kwargs)
        return self

    def url(
        self,
        name: str,
        required: bool = False,
        require_https: bool = False,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add URL field."""
        self.fields[name] = FieldSchema(URLValidator(require_https), required=required, **kwargs)
        return self

    def uuid(
        self,
        name: str,
        required: bool = False,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add UUID field."""
        self.fields[name] = FieldSchema(UUIDValidator(), required=required, **kwargs)
        return self

    def date(
        self,
        name: str,
        required: bool = False,
        format: str = "%Y-%m-%d",
        **kwargs
    ) -> 'SchemaBuilder':
        """Add date field."""
        self.fields[name] = FieldSchema(DateValidator(format), required=required, **kwargs)
        return self

    def array(
        self,
        name: str,
        item_validator: Validator = None,
        required: bool = False,
        min_length: int = None,
        max_length: int = None,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add array field."""
        validator = ArrayValidator(item_validator, min_length, max_length)
        self.fields[name] = FieldSchema(validator, required=required, **kwargs)
        return self

    def object(
        self,
        name: str,
        schema: Dict[str, FieldSchema] = None,
        required: bool = False,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add nested object field."""
        validator = ObjectValidator(schema or {})
        self.fields[name] = FieldSchema(validator, required=required, **kwargs)
        return self

    def custom(
        self,
        name: str,
        validator: Validator,
        required: bool = False,
        **kwargs
    ) -> 'SchemaBuilder':
        """Add custom validator field."""
        self.fields[name] = FieldSchema(validator, required=required, **kwargs)
        return self

    def build(self) -> ObjectValidator:
        """Build the schema."""
        return ObjectValidator(self.fields)


# =============================================================================
# VALIDATOR MANAGER
# =============================================================================

class ValidationManager:
    """
    Master validation management for BAEL.

    Provides comprehensive data validation with schema support.
    """

    def __init__(self):
        self.schemas: Dict[str, ObjectValidator] = {}
        self.custom_validators: Dict[str, Validator] = {}

        # Statistics
        self.validations_performed = 0
        self.validations_passed = 0
        self.validations_failed = 0

    def register_schema(self, name: str, schema: ObjectValidator) -> None:
        """Register a schema."""
        self.schemas[name] = schema

    def register_validator(self, name: str, validator: Validator) -> None:
        """Register a custom validator."""
        self.custom_validators[name] = validator

    def get_schema(self, name: str) -> Optional[ObjectValidator]:
        """Get a registered schema."""
        return self.schemas.get(name)

    def validate(
        self,
        data: Any,
        schema: Union[str, ObjectValidator],
        root_path: str = ""
    ) -> ValidationResult:
        """Validate data against a schema."""
        self.validations_performed += 1

        if isinstance(schema, str):
            schema = self.schemas.get(schema)
            if not schema:
                result = ValidationResult(valid=False)
                result.add_error(root_path, f"Schema '{schema}' not found")
                return result

        context = FieldContext(
            path=root_path,
            value=data,
            root=data
        )

        result = schema.validate(data, context)

        if result.valid:
            self.validations_passed += 1
        else:
            self.validations_failed += 1

        return result

    def validate_field(
        self,
        value: Any,
        validator: Union[str, Validator],
        path: str = "value"
    ) -> ValidationResult:
        """Validate a single field."""
        if isinstance(validator, str):
            validator = self.custom_validators.get(validator)
            if not validator:
                result = ValidationResult(valid=False)
                result.add_error(path, f"Validator '{validator}' not found")
                return result

        context = FieldContext(path=path, value=value)
        return validator.validate(value, context)

    def create_schema(self) -> SchemaBuilder:
        """Create a new schema builder."""
        return SchemaBuilder()

    # Convenience validators
    @staticmethod
    def string(**kwargs) -> StringValidator:
        return StringValidator(**kwargs)

    @staticmethod
    def number(**kwargs) -> NumberValidator:
        return NumberValidator(**kwargs)

    @staticmethod
    def boolean(**kwargs) -> BooleanValidator:
        return BooleanValidator(**kwargs)

    @staticmethod
    def array(**kwargs) -> ArrayValidator:
        return ArrayValidator(**kwargs)

    @staticmethod
    def email(**kwargs) -> EmailValidator:
        return EmailValidator(**kwargs)

    @staticmethod
    def url(**kwargs) -> URLValidator:
        return URLValidator(**kwargs)

    @staticmethod
    def uuid(**kwargs) -> UUIDValidator:
        return UUIDValidator(**kwargs)

    @staticmethod
    def date(**kwargs) -> DateValidator:
        return DateValidator(**kwargs)

    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "validations_performed": self.validations_performed,
            "validations_passed": self.validations_passed,
            "validations_failed": self.validations_failed,
            "pass_rate": (
                self.validations_passed / self.validations_performed * 100
                if self.validations_performed > 0 else 0
            ),
            "registered_schemas": len(self.schemas),
            "registered_validators": len(self.custom_validators)
        }


# =============================================================================
# DECORATORS
# =============================================================================

def validate_input(schema: ObjectValidator):
    """Decorator to validate function input."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            context = FieldContext(path="input", value=kwargs, root=kwargs)
            result = schema.validate(kwargs, context)

            if not result.valid:
                raise ValueError(f"Validation failed: {result.errors}")

            # Use validated/transformed values
            return func(*args, **result.value)

        async def async_wrapper(*args, **kwargs):
            context = FieldContext(path="input", value=kwargs, root=kwargs)
            result = schema.validate(kwargs, context)

            if not result.valid:
                raise ValueError(f"Validation failed: {result.errors}")

            return await func(*args, **result.value)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Data Validation System."""
    print("=" * 70)
    print("BAEL - DATA VALIDATION SYSTEM DEMO")
    print("Schema-Based Data Validation")
    print("=" * 70)
    print()

    manager = ValidationManager()

    # 1. String Validation
    print("1. STRING VALIDATION:")
    print("-" * 40)

    string_val = StringValidator(min_length=3, max_length=50)

    ctx = FieldContext(path="name", value="John")
    result = string_val.validate("John", ctx)
    print(f"   'John' valid: {result.valid}")

    result = string_val.validate("Jo", ctx)
    print(f"   'Jo' valid: {result.valid}, error: {result.errors[0].message if result.errors else ''}")
    print()

    # 2. Number Validation
    print("2. NUMBER VALIDATION:")
    print("-" * 40)

    num_val = NumberValidator(min_value=0, max_value=100, integer_only=True)

    ctx = FieldContext(path="age", value=25)
    result = num_val.validate(25, ctx)
    print(f"   25 valid: {result.valid}")

    result = num_val.validate(150, ctx)
    print(f"   150 valid: {result.valid}, error: {result.errors[0].message if result.errors else ''}")

    result = num_val.validate(25.5, ctx)
    print(f"   25.5 valid: {result.valid}, error: {result.errors[0].message if result.errors else ''}")
    print()

    # 3. Email Validation
    print("3. EMAIL VALIDATION:")
    print("-" * 40)

    email_val = EmailValidator()

    ctx = FieldContext(path="email", value="test@example.com")
    result = email_val.validate("test@example.com", ctx)
    print(f"   'test@example.com' valid: {result.valid}")

    result = email_val.validate("invalid-email", ctx)
    print(f"   'invalid-email' valid: {result.valid}")
    print()

    # 4. Array Validation
    print("4. ARRAY VALIDATION:")
    print("-" * 40)

    array_val = ArrayValidator(
        item_validator=NumberValidator(positive=True),
        min_length=1,
        unique=True
    )

    ctx = FieldContext(path="numbers", value=[1, 2, 3])
    result = array_val.validate([1, 2, 3], ctx)
    print(f"   [1, 2, 3] valid: {result.valid}")

    result = array_val.validate([1, -2, 3], ctx)
    print(f"   [1, -2, 3] valid: {result.valid}")

    result = array_val.validate([], ctx)
    print(f"   [] valid: {result.valid}")
    print()

    # 5. Object Schema
    print("5. OBJECT SCHEMA VALIDATION:")
    print("-" * 40)

    user_schema = (
        manager.create_schema()
        .string("name", required=True, min_length=2)
        .email("email", required=True)
        .number("age", min_value=0, max_value=150)
        .boolean("active", default=True)
        .array("tags", item_validator=StringValidator())
        .build()
    )

    valid_user = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30,
        "tags": ["developer", "python"]
    }

    result = manager.validate(valid_user, user_schema)
    print(f"   Valid user: {result.valid}")
    print(f"   Transformed: {result.value}")

    invalid_user = {
        "name": "J",
        "email": "not-an-email",
        "age": 200
    }

    result = manager.validate(invalid_user, user_schema)
    print(f"   Invalid user: {result.valid}")
    print(f"   Errors: {[str(e) for e in result.errors]}")
    print()

    # 6. Nested Objects
    print("6. NESTED OBJECT VALIDATION:")
    print("-" * 40)

    address_fields = {
        "street": FieldSchema(StringValidator(), required=True),
        "city": FieldSchema(StringValidator(), required=True),
        "zip": FieldSchema(StringValidator(pattern=r'^\d{5}$'))
    }

    order_schema = (
        manager.create_schema()
        .string("orderId", required=True)
        .object("shipping_address", schema=address_fields, required=True)
        .number("total", min_value=0)
        .build()
    )

    order = {
        "orderId": "ORD-123",
        "shipping_address": {
            "street": "123 Main St",
            "city": "Boston",
            "zip": "02101"
        },
        "total": 99.99
    }

    result = manager.validate(order, order_schema)
    print(f"   Order valid: {result.valid}")
    print()

    # 7. Combined Validators
    print("7. COMBINED VALIDATORS:")
    print("-" * 40)

    # String OR Number
    flexible_val = StringValidator() | NumberValidator()

    ctx = FieldContext(path="value", value="hello")
    result = flexible_val.validate("hello", ctx)
    print(f"   'hello' with string|number: {result.valid}")

    result = flexible_val.validate(42, ctx)
    print(f"   42 with string|number: {result.valid}")
    print()

    # 8. Custom Validator
    print("8. CUSTOM VALIDATOR:")
    print("-" * 40)

    def password_validator(value: Any, ctx: FieldContext) -> ValidationResult:
        result = ValidationResult(valid=True, value=value)

        if len(value) < 8:
            result.add_error(ctx.path, "Password too short (min 8)")
        if not re.search(r'[A-Z]', value):
            result.add_error(ctx.path, "Password needs uppercase")
        if not re.search(r'[0-9]', value):
            result.add_error(ctx.path, "Password needs number")

        return result

    pw_val = CustomValidator(password_validator)

    result = pw_val.validate("short", FieldContext(path="password", value="short"))
    print(f"   'short' valid: {result.valid}, errors: {len(result.errors)}")

    result = pw_val.validate("SecurePass123", FieldContext(path="password", value="SecurePass123"))
    print(f"   'SecurePass123' valid: {result.valid}")
    print()

    # 9. Conditional Validation
    print("9. CONDITIONAL VALIDATION:")
    print("-" * 40)

    # Phone required if contactByPhone is true
    phone_schema = {
        "contactByPhone": FieldSchema(BooleanValidator(), default=False),
        "phone": FieldSchema(
            ConditionalValidator(
                condition=lambda siblings: siblings.get("contactByPhone", False),
                then_validator=StringValidator(pattern=r'^\d{10}$'),
                else_validator=StringValidator()
            )
        )
    }

    obj_val = ObjectValidator(phone_schema)

    ctx = FieldContext(path="", value={}, root={})
    result = obj_val.validate({"contactByPhone": True, "phone": "1234567890"}, ctx)
    print(f"   With phone contact + valid phone: {result.valid}")

    result = obj_val.validate({"contactByPhone": True, "phone": "invalid"}, ctx)
    print(f"   With phone contact + invalid phone: {result.valid}")

    result = obj_val.validate({"contactByPhone": False, "phone": "any"}, ctx)
    print(f"   Without phone contact: {result.valid}")
    print()

    # 10. Statistics
    print("10. STATISTICS:")
    print("-" * 40)

    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"    {key}: {value}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Data Validation System Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
