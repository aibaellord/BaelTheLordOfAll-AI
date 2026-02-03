#!/usr/bin/env python3
"""
BAEL - Validation Framework
Comprehensive data validation system.

Features:
- Field validators
- Schema validation
- Custom validators
- Async validation
- Error messages
- Nested validation
- Conditional validation
- Validator chaining
- Type coercion
- Validation groups
"""

import asyncio
import logging
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Pattern, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ValidationSeverity(Enum):
    """Validation error severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationMode(Enum):
    """Validation modes."""
    STRICT = "strict"
    LAX = "lax"
    COERCE = "coerce"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ValidationError:
    """Single validation error."""
    field: str
    message: str
    code: str = "invalid"
    severity: ValidationSeverity = ValidationSeverity.ERROR
    value: Any = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Validation result."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    coerced_data: Dict[str, Any] = field(default_factory=dict)

    def add_error(
        self,
        field: str,
        message: str,
        code: str = "invalid",
        value: Any = None
    ) -> None:
        """Add error."""
        self.errors.append(ValidationError(
            field=field,
            message=message,
            code=code,
            severity=ValidationSeverity.ERROR,
            value=value
        ))
        self.valid = False

    def add_warning(
        self,
        field: str,
        message: str,
        code: str = "warning",
        value: Any = None
    ) -> None:
        """Add warning."""
        self.warnings.append(ValidationError(
            field=field,
            message=message,
            code=code,
            severity=ValidationSeverity.WARNING,
            value=value
        ))

    def merge(self, other: 'ValidationResult', prefix: str = "") -> None:
        """Merge another result."""
        for error in other.errors:
            error.field = f"{prefix}.{error.field}" if prefix else error.field
            self.errors.append(error)

        for warning in other.warnings:
            warning.field = f"{prefix}.{warning.field}" if prefix else warning.field
            self.warnings.append(warning)

        if not other.valid:
            self.valid = False

        self.coerced_data.update(other.coerced_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": [
                {"field": e.field, "message": e.message, "code": e.code}
                for e in self.errors
            ],
            "warnings": [
                {"field": w.field, "message": w.message, "code": w.code}
                for w in self.warnings
            ]
        }


# =============================================================================
# BASE VALIDATOR
# =============================================================================

class Validator(ABC):
    """Abstract base validator."""

    def __init__(
        self,
        message: str = None,
        code: str = "invalid"
    ):
        self.message = message
        self.code = code

    @abstractmethod
    def validate(self, value: Any, field: str = "") -> ValidationResult:
        """Validate value."""
        pass

    def get_message(self, default: str) -> str:
        """Get error message."""
        return self.message or default


class AsyncValidator(ABC):
    """Abstract async validator."""

    def __init__(
        self,
        message: str = None,
        code: str = "invalid"
    ):
        self.message = message
        self.code = code

    @abstractmethod
    async def validate(self, value: Any, field: str = "") -> ValidationResult:
        """Validate value asynchronously."""
        pass

    def get_message(self, default: str) -> str:
        """Get error message."""
        return self.message or default


# =============================================================================
# TYPE VALIDATORS
# =============================================================================

class TypeValidator(Validator):
    """Validates value type."""

    def __init__(
        self,
        expected_type: Type,
        message: str = None,
        coerce: bool = False
    ):
        super().__init__(message, "type_error")
        self.expected_type = expected_type
        self.coerce = coerce

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if isinstance(value, self.expected_type):
            return result

        if self.coerce:
            try:
                coerced = self.expected_type(value)
                result.coerced_data[field] = coerced
                return result
            except (ValueError, TypeError):
                pass

        result.add_error(
            field,
            self.get_message(
                f"Expected {self.expected_type.__name__}, got {type(value).__name__}"
            ),
            self.code,
            value
        )

        return result


class StringValidator(Validator):
    """Validates string values."""

    def __init__(
        self,
        min_length: int = None,
        max_length: int = None,
        pattern: str = None,
        message: str = None
    ):
        super().__init__(message, "string_error")
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, str):
            result.add_error(
                field,
                self.get_message("Value must be a string"),
                "type_error",
                value
            )
            return result

        if self.min_length is not None and len(value) < self.min_length:
            result.add_error(
                field,
                f"Must be at least {self.min_length} characters",
                "min_length",
                value
            )

        if self.max_length is not None and len(value) > self.max_length:
            result.add_error(
                field,
                f"Must be at most {self.max_length} characters",
                "max_length",
                value
            )

        if self.pattern and not self.pattern.match(value):
            result.add_error(
                field,
                self.get_message("Does not match required pattern"),
                "pattern",
                value
            )

        return result


class NumberValidator(Validator):
    """Validates numeric values."""

    def __init__(
        self,
        min_value: float = None,
        max_value: float = None,
        allow_float: bool = True,
        message: str = None
    ):
        super().__init__(message, "number_error")
        self.min_value = min_value
        self.max_value = max_value
        self.allow_float = allow_float

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, (int, float, Decimal)):
            result.add_error(
                field,
                self.get_message("Value must be a number"),
                "type_error",
                value
            )
            return result

        if not self.allow_float and isinstance(value, float):
            result.add_error(
                field,
                "Value must be an integer",
                "integer_only",
                value
            )
            return result

        if self.min_value is not None and value < self.min_value:
            result.add_error(
                field,
                f"Must be at least {self.min_value}",
                "min_value",
                value
            )

        if self.max_value is not None and value > self.max_value:
            result.add_error(
                field,
                f"Must be at most {self.max_value}",
                "max_value",
                value
            )

        return result


class BooleanValidator(Validator):
    """Validates boolean values."""

    TRUTHY = {'true', '1', 'yes', 'on', 'y'}
    FALSY = {'false', '0', 'no', 'off', 'n'}

    def __init__(self, strict: bool = True, message: str = None):
        super().__init__(message, "boolean_error")
        self.strict = strict

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if isinstance(value, bool):
            return result

        if not self.strict and isinstance(value, str):
            lower_val = value.lower()

            if lower_val in self.TRUTHY:
                result.coerced_data[field] = True
                return result

            if lower_val in self.FALSY:
                result.coerced_data[field] = False
                return result

        result.add_error(
            field,
            self.get_message("Value must be a boolean"),
            self.code,
            value
        )

        return result


# =============================================================================
# FORMAT VALIDATORS
# =============================================================================

class EmailValidator(Validator):
    """Validates email format."""

    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def __init__(self, message: str = None):
        super().__init__(message, "email_format")

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, str):
            result.add_error(field, "Email must be a string", "type_error", value)
            return result

        if not self.EMAIL_PATTERN.match(value):
            result.add_error(
                field,
                self.get_message("Invalid email format"),
                self.code,
                value
            )

        return result


class URLValidator(Validator):
    """Validates URL format."""

    URL_PATTERN = re.compile(
        r'^https?://[^\s/$.?#].[^\s]*$',
        re.IGNORECASE
    )

    def __init__(
        self,
        require_https: bool = False,
        message: str = None
    ):
        super().__init__(message, "url_format")
        self.require_https = require_https

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, str):
            result.add_error(field, "URL must be a string", "type_error", value)
            return result

        if not self.URL_PATTERN.match(value):
            result.add_error(
                field,
                self.get_message("Invalid URL format"),
                self.code,
                value
            )
            return result

        if self.require_https and not value.lower().startswith('https://'):
            result.add_error(
                field,
                "URL must use HTTPS",
                "https_required",
                value
            )

        return result


class UUIDValidator(Validator):
    """Validates UUID format."""

    def __init__(self, version: int = None, message: str = None):
        super().__init__(message, "uuid_format")
        self.version = version

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        try:
            if isinstance(value, uuid.UUID):
                parsed = value
            else:
                parsed = uuid.UUID(str(value))

            if self.version and parsed.version != self.version:
                result.add_error(
                    field,
                    f"UUID must be version {self.version}",
                    "uuid_version",
                    value
                )

            result.coerced_data[field] = parsed

        except (ValueError, TypeError):
            result.add_error(
                field,
                self.get_message("Invalid UUID format"),
                self.code,
                value
            )

        return result


class DateValidator(Validator):
    """Validates date format."""

    def __init__(
        self,
        format: str = "%Y-%m-%d",
        min_date: date = None,
        max_date: date = None,
        message: str = None
    ):
        super().__init__(message, "date_format")
        self.format = format
        self.min_date = min_date
        self.max_date = max_date

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if isinstance(value, date):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.strptime(value, self.format).date()
                result.coerced_data[field] = parsed
            except ValueError:
                result.add_error(
                    field,
                    self.get_message(f"Invalid date format, expected {self.format}"),
                    self.code,
                    value
                )
                return result
        else:
            result.add_error(field, "Date must be a string or date", "type_error", value)
            return result

        if self.min_date and parsed < self.min_date:
            result.add_error(
                field,
                f"Date must be on or after {self.min_date}",
                "min_date",
                value
            )

        if self.max_date and parsed > self.max_date:
            result.add_error(
                field,
                f"Date must be on or before {self.max_date}",
                "max_date",
                value
            )

        return result


class PhoneValidator(Validator):
    """Validates phone number format."""

    PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{6,14}$')

    def __init__(self, message: str = None):
        super().__init__(message, "phone_format")

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, str):
            result.add_error(field, "Phone must be a string", "type_error", value)
            return result

        cleaned = re.sub(r'[\s\-\(\)]', '', value)

        if not self.PHONE_PATTERN.match(cleaned):
            result.add_error(
                field,
                self.get_message("Invalid phone number format"),
                self.code,
                value
            )
        else:
            result.coerced_data[field] = cleaned

        return result


# =============================================================================
# COLLECTION VALIDATORS
# =============================================================================

class ListValidator(Validator):
    """Validates list values."""

    def __init__(
        self,
        item_validator: Validator = None,
        min_length: int = None,
        max_length: int = None,
        unique: bool = False,
        message: str = None
    ):
        super().__init__(message, "list_error")
        self.item_validator = item_validator
        self.min_length = min_length
        self.max_length = max_length
        self.unique = unique

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, (list, tuple)):
            result.add_error(
                field,
                self.get_message("Value must be a list"),
                "type_error",
                value
            )
            return result

        if self.min_length is not None and len(value) < self.min_length:
            result.add_error(
                field,
                f"List must have at least {self.min_length} items",
                "min_length",
                value
            )

        if self.max_length is not None and len(value) > self.max_length:
            result.add_error(
                field,
                f"List must have at most {self.max_length} items",
                "max_length",
                value
            )

        if self.unique:
            try:
                if len(value) != len(set(value)):
                    result.add_error(
                        field,
                        "List items must be unique",
                        "unique",
                        value
                    )
            except TypeError:
                pass  # Unhashable types

        if self.item_validator:
            coerced_items = []

            for i, item in enumerate(value):
                item_result = self.item_validator.validate(item, f"{field}[{i}]")

                if not item_result.valid:
                    result.merge(item_result)

                coerced_items.append(
                    item_result.coerced_data.get(f"{field}[{i}]", item)
                )

            if result.valid:
                result.coerced_data[field] = coerced_items

        return result


class DictValidator(Validator):
    """Validates dictionary values."""

    def __init__(
        self,
        key_validator: Validator = None,
        value_validator: Validator = None,
        min_keys: int = None,
        max_keys: int = None,
        message: str = None
    ):
        super().__init__(message, "dict_error")
        self.key_validator = key_validator
        self.value_validator = value_validator
        self.min_keys = min_keys
        self.max_keys = max_keys

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if not isinstance(value, dict):
            result.add_error(
                field,
                self.get_message("Value must be a dictionary"),
                "type_error",
                value
            )
            return result

        if self.min_keys is not None and len(value) < self.min_keys:
            result.add_error(
                field,
                f"Dict must have at least {self.min_keys} keys",
                "min_keys",
                value
            )

        if self.max_keys is not None and len(value) > self.max_keys:
            result.add_error(
                field,
                f"Dict must have at most {self.max_keys} keys",
                "max_keys",
                value
            )

        if self.key_validator:
            for key in value.keys():
                key_result = self.key_validator.validate(key, f"{field}.key")
                result.merge(key_result)

        if self.value_validator:
            for key, val in value.items():
                val_result = self.value_validator.validate(val, f"{field}.{key}")
                result.merge(val_result)

        return result


# =============================================================================
# LOGICAL VALIDATORS
# =============================================================================

class RequiredValidator(Validator):
    """Validates required field."""

    def __init__(self, message: str = None):
        super().__init__(message, "required")

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None or value == "":
            result.add_error(
                field,
                self.get_message("This field is required"),
                self.code,
                value
            )

        return result


class ChoicesValidator(Validator):
    """Validates value is in choices."""

    def __init__(self, choices: List[Any], message: str = None):
        super().__init__(message, "invalid_choice")
        self.choices = choices

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if value not in self.choices:
            result.add_error(
                field,
                self.get_message(f"Value must be one of: {', '.join(str(c) for c in self.choices)}"),
                self.code,
                value
            )

        return result


class RangeValidator(Validator):
    """Validates value is in range."""

    def __init__(
        self,
        min_val: Any = None,
        max_val: Any = None,
        message: str = None
    ):
        super().__init__(message, "out_of_range")
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        if value is None:
            return result

        if self.min_val is not None and value < self.min_val:
            result.add_error(
                field,
                f"Value must be >= {self.min_val}",
                "below_minimum",
                value
            )

        if self.max_val is not None and value > self.max_val:
            result.add_error(
                field,
                f"Value must be <= {self.max_val}",
                "above_maximum",
                value
            )

        return result


# =============================================================================
# COMPOSITE VALIDATORS
# =============================================================================

class ChainValidator(Validator):
    """Chains multiple validators."""

    def __init__(self, *validators: Validator):
        super().__init__()
        self.validators = validators

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        for validator in self.validators:
            sub_result = validator.validate(value, field)
            result.merge(sub_result)

            if not sub_result.valid:
                break  # Stop on first failure

        return result


class AnyOfValidator(Validator):
    """Validates value matches any validator."""

    def __init__(self, *validators: Validator, message: str = None):
        super().__init__(message, "none_valid")
        self.validators = validators

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        result = ValidationResult(valid=True)

        for validator in self.validators:
            sub_result = validator.validate(value, field)

            if sub_result.valid:
                result.merge(sub_result)
                return result

        result.add_error(
            field,
            self.get_message("Value does not match any validator"),
            self.code,
            value
        )

        return result


class ConditionalValidator(Validator):
    """Validates conditionally."""

    def __init__(
        self,
        condition: Callable[[Any], bool],
        validator: Validator,
        message: str = None
    ):
        super().__init__(message)
        self.condition = condition
        self.validator = validator

    def validate(self, value: Any, field: str = "") -> ValidationResult:
        if self.condition(value):
            return self.validator.validate(value, field)

        return ValidationResult(valid=True)


# =============================================================================
# SCHEMA VALIDATOR
# =============================================================================

@dataclass
class FieldSchema:
    """Field schema definition."""
    name: str
    validators: List[Validator] = field(default_factory=list)
    required: bool = False
    default: Any = None
    alias: str = None


class SchemaValidator:
    """Schema-based validation."""

    def __init__(self, mode: ValidationMode = ValidationMode.STRICT):
        self.mode = mode
        self._fields: Dict[str, FieldSchema] = {}

    def add_field(
        self,
        name: str,
        *validators: Validator,
        required: bool = False,
        default: Any = None,
        alias: str = None
    ) -> 'SchemaValidator':
        """Add field to schema."""
        self._fields[name] = FieldSchema(
            name=name,
            validators=list(validators),
            required=required,
            default=default,
            alias=alias
        )
        return self

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate data against schema."""
        result = ValidationResult(valid=True)
        coerced = {}

        for name, field_schema in self._fields.items():
            # Get value (check alias too)
            value = data.get(name)

            if value is None and field_schema.alias:
                value = data.get(field_schema.alias)

            if value is None:
                value = field_schema.default

            # Required check
            if field_schema.required and (value is None or value == ""):
                result.add_error(
                    name,
                    f"{name} is required",
                    "required",
                    value
                )
                continue

            # Skip if None and not required
            if value is None:
                continue

            # Run validators
            for validator in field_schema.validators:
                sub_result = validator.validate(value, name)
                result.merge(sub_result)

                if name in sub_result.coerced_data:
                    value = sub_result.coerced_data[name]

            coerced[name] = value

        # Check for unknown fields in strict mode
        if self.mode == ValidationMode.STRICT:
            for key in data.keys():
                if key not in self._fields:
                    # Check aliases
                    is_alias = any(
                        f.alias == key for f in self._fields.values()
                    )

                    if not is_alias:
                        result.add_error(
                            key,
                            f"Unknown field: {key}",
                            "unknown_field",
                            data[key]
                        )

        result.coerced_data = coerced
        return result


# =============================================================================
# VALIDATION ENGINE
# =============================================================================

class ValidationEngine:
    """
    Comprehensive Validation Framework for BAEL.
    """

    def __init__(self):
        self._schemas: Dict[str, SchemaValidator] = {}
        self._custom_validators: Dict[str, Type[Validator]] = {}

    # -------------------------------------------------------------------------
    # SCHEMA MANAGEMENT
    # -------------------------------------------------------------------------

    def create_schema(
        self,
        name: str,
        mode: ValidationMode = ValidationMode.STRICT
    ) -> SchemaValidator:
        """Create and register a schema."""
        schema = SchemaValidator(mode)
        self._schemas[name] = schema
        return schema

    def get_schema(self, name: str) -> Optional[SchemaValidator]:
        """Get registered schema."""
        return self._schemas.get(name)

    def validate_schema(
        self,
        schema_name: str,
        data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate data against named schema."""
        schema = self._schemas.get(schema_name)

        if not schema:
            result = ValidationResult(valid=False)
            result.add_error("_schema", f"Unknown schema: {schema_name}", "unknown_schema")
            return result

        return schema.validate(data)

    # -------------------------------------------------------------------------
    # CUSTOM VALIDATORS
    # -------------------------------------------------------------------------

    def register_validator(
        self,
        name: str,
        validator_class: Type[Validator]
    ) -> None:
        """Register custom validator."""
        self._custom_validators[name] = validator_class

    def get_validator(self, name: str) -> Optional[Type[Validator]]:
        """Get custom validator class."""
        return self._custom_validators.get(name)

    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------

    def validate_email(self, value: str) -> ValidationResult:
        """Validate email."""
        return EmailValidator().validate(value, "email")

    def validate_url(self, value: str) -> ValidationResult:
        """Validate URL."""
        return URLValidator().validate(value, "url")

    def validate_uuid(self, value: str) -> ValidationResult:
        """Validate UUID."""
        return UUIDValidator().validate(value, "uuid")

    def validate_phone(self, value: str) -> ValidationResult:
        """Validate phone."""
        return PhoneValidator().validate(value, "phone")

    def validate_required(self, value: Any, field: str = "value") -> ValidationResult:
        """Validate required field."""
        return RequiredValidator().validate(value, field)


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Validation Framework."""
    print("=" * 70)
    print("BAEL - VALIDATION FRAMEWORK DEMO")
    print("Comprehensive Data Validation")
    print("=" * 70)
    print()

    engine = ValidationEngine()

    # 1. Basic Type Validation
    print("1. TYPE VALIDATION:")
    print("-" * 40)

    result = TypeValidator(int).validate("123", "age")
    print(f"   '123' as int (no coerce): Valid={result.valid}")

    result = TypeValidator(int, coerce=True).validate("123", "age")
    print(f"   '123' as int (coerce): Valid={result.valid}, Value={result.coerced_data.get('age')}")
    print()

    # 2. String Validation
    print("2. STRING VALIDATION:")
    print("-" * 40)

    validator = StringValidator(min_length=3, max_length=10)

    for value in ["ab", "hello", "hello world"]:
        result = validator.validate(value, "name")
        status = "✓" if result.valid else "✗"
        print(f"   [{status}] '{value}': {result.errors[0].message if result.errors else 'OK'}")
    print()

    # 3. Email Validation
    print("3. EMAIL VALIDATION:")
    print("-" * 40)

    for email in ["user@example.com", "invalid-email", "user@.com"]:
        result = engine.validate_email(email)
        status = "✓" if result.valid else "✗"
        print(f"   [{status}] {email}")
    print()

    # 4. Number Validation
    print("4. NUMBER VALIDATION:")
    print("-" * 40)

    validator = NumberValidator(min_value=0, max_value=100)

    for value in [-5, 50, 150]:
        result = validator.validate(value, "score")
        status = "✓" if result.valid else "✗"
        print(f"   [{status}] {value}: {result.errors[0].message if result.errors else 'OK'}")
    print()

    # 5. List Validation
    print("5. LIST VALIDATION:")
    print("-" * 40)

    validator = ListValidator(
        item_validator=NumberValidator(min_value=0),
        min_length=2,
        max_length=5
    )

    for value in [[1, 2, 3], [1], [-1, 2, 3], [1, 2, 3, 4, 5, 6]]:
        result = validator.validate(value, "numbers")
        status = "✓" if result.valid else "✗"
        errors = [e.message for e in result.errors]
        print(f"   [{status}] {value}: {errors if errors else 'OK'}")
    print()

    # 6. Schema Validation
    print("6. SCHEMA VALIDATION:")
    print("-" * 40)

    user_schema = engine.create_schema("user")
    user_schema.add_field("name", StringValidator(min_length=2), required=True)
    user_schema.add_field("email", EmailValidator(), required=True)
    user_schema.add_field("age", NumberValidator(min_value=0, max_value=150))
    user_schema.add_field("role", ChoicesValidator(["admin", "user", "guest"]))

    valid_user = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30,
        "role": "admin"
    }

    result = engine.validate_schema("user", valid_user)
    print(f"   Valid user: Valid={result.valid}")

    invalid_user = {
        "name": "J",
        "email": "invalid",
        "age": -5,
        "role": "superadmin"
    }

    result = engine.validate_schema("user", invalid_user)
    print(f"   Invalid user: Valid={result.valid}")

    for error in result.errors:
        print(f"      - {error.field}: {error.message}")
    print()

    # 7. Chained Validators
    print("7. CHAINED VALIDATORS:")
    print("-" * 40)

    password_validator = ChainValidator(
        RequiredValidator(),
        StringValidator(min_length=8, max_length=128),
        StringValidator(pattern=r'.*[A-Z].*', message="Must contain uppercase"),
        StringValidator(pattern=r'.*[0-9].*', message="Must contain number")
    )

    for password in ["short", "nouppercase1", "NONUMBER", "ValidPass123"]:
        result = password_validator.validate(password, "password")
        status = "✓" if result.valid else "✗"
        error = result.errors[0].message if result.errors else "OK"
        print(f"   [{status}] {password}: {error}")
    print()

    # 8. Choices Validation
    print("8. CHOICES VALIDATION:")
    print("-" * 40)

    validator = ChoicesValidator(["red", "green", "blue"])

    for color in ["red", "yellow", "blue"]:
        result = validator.validate(color, "color")
        status = "✓" if result.valid else "✗"
        print(f"   [{status}] {color}")
    print()

    # 9. Date Validation
    print("9. DATE VALIDATION:")
    print("-" * 40)

    from datetime import date

    validator = DateValidator(
        min_date=date(2020, 1, 1),
        max_date=date(2025, 12, 31)
    )

    for date_str in ["2022-06-15", "2019-01-01", "2026-01-01", "invalid"]:
        result = validator.validate(date_str, "date")
        status = "✓" if result.valid else "✗"
        error = result.errors[0].message if result.errors else "OK"
        print(f"   [{status}] {date_str}: {error}")
    print()

    # 10. UUID Validation
    print("10. UUID VALIDATION:")
    print("-" * 40)

    for value in ["550e8400-e29b-41d4-a716-446655440000", "not-a-uuid"]:
        result = engine.validate_uuid(value)
        status = "✓" if result.valid else "✗"
        print(f"   [{status}] {value[:30]}...")
    print()

    # 11. Nested Schema
    print("11. NESTED SCHEMA:")
    print("-" * 40)

    address_schema = engine.create_schema("address")
    address_schema.add_field("street", StringValidator(min_length=1), required=True)
    address_schema.add_field("city", StringValidator(min_length=1), required=True)
    address_schema.add_field("zip", StringValidator(pattern=r'^\d{5}$'))

    address_data = {
        "street": "123 Main St",
        "city": "Springfield",
        "zip": "12345"
    }

    result = engine.validate_schema("address", address_data)
    print(f"   Valid address: {result.valid}")

    bad_address = {"street": "", "city": "X", "zip": "abc"}
    result = engine.validate_schema("address", bad_address)
    print(f"   Invalid address: {result.valid} ({len(result.errors)} errors)")
    print()

    # 12. Result as Dict
    print("12. RESULT AS DICT:")
    print("-" * 40)

    result = engine.validate_schema("user", invalid_user)
    result_dict = result.to_dict()

    print(f"   Valid: {result_dict['valid']}")
    print(f"   Errors: {len(result_dict['errors'])}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Validation Framework Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
