"""
BAEL Validation Engine Implementation
=====================================

Data validation with schemas and constraints.

"Ba'el's judgment is absolute and infallible." — Ba'el
"""

import asyncio
import logging
import re
import threading
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Type, Union, Callable, Pattern
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import uuid

logger = logging.getLogger("BAEL.Validation")


# ============================================================================
# ENUMS
# ============================================================================

class ValidationRule(Enum):
    """Built-in validation rules."""
    REQUIRED = "required"
    TYPE = "type"
    MIN = "min"
    MAX = "max"
    RANGE = "range"
    LENGTH = "length"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    EMAIL = "email"
    URL = "url"
    UUID = "uuid"
    DATE = "date"
    DATETIME = "datetime"
    ENUM = "enum"
    CHOICES = "choices"
    CUSTOM = "custom"


class ValidationSeverity(Enum):
    """Validation error severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ValidationError:
    """A validation error."""
    field: str
    message: str
    rule: ValidationRule
    value: Any = None
    severity: ValidationSeverity = ValidationSeverity.ERROR

    # Additional context
    expected: Any = None
    actual: Any = None


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    # Validated data (with coercion)
    data: Optional[Dict[str, Any]] = None

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def add_error(self, error: ValidationError) -> None:
        """Add an error."""
        if error.severity == ValidationSeverity.ERROR:
            self.errors.append(error)
            self.valid = False
        elif error.severity == ValidationSeverity.WARNING:
            self.warnings.append(error)

    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge with another result."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.valid = self.valid and other.valid
        return self


@dataclass
class FieldValidator:
    """Validation rules for a field."""
    field: str

    # Basic rules
    required: bool = False
    field_type: Optional[Type] = None
    nullable: bool = True

    # Numeric constraints
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    # String constraints
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None

    # Choices
    choices: Optional[List[Any]] = None

    # Custom validators
    validators: List[Callable] = field(default_factory=list)

    # Error messages
    messages: Dict[str, str] = field(default_factory=dict)


@dataclass
class ValidationSchema:
    """A validation schema."""
    name: str
    fields: Dict[str, FieldValidator] = field(default_factory=dict)

    # Schema-level validators
    validators: List[Callable] = field(default_factory=list)

    # Options
    strict: bool = False  # Reject unknown fields
    coerce: bool = True   # Attempt type coercion

    def add_field(
        self,
        name: str,
        **kwargs
    ) -> 'ValidationSchema':
        """Add a field validator."""
        self.fields[name] = FieldValidator(field=name, **kwargs)
        return self


@dataclass
class ValidationConfig:
    """Validation engine configuration."""
    raise_on_error: bool = False
    stop_on_first_error: bool = False
    coerce_types: bool = True


# ============================================================================
# VALIDATORS
# ============================================================================

class BaseValidator(ABC):
    """Base validator interface."""

    @abstractmethod
    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        """Validate value. Return error if invalid."""
        pass


class RequiredValidator(BaseValidator):
    """Required field validator."""

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return ValidationError(
                field=field,
                message=f"'{field}' is required",
                rule=ValidationRule.REQUIRED,
                value=value
            )
        return None


class TypeValidator(BaseValidator):
    """Type checking validator."""

    def __init__(self, expected_type: Type, coerce: bool = True):
        self.expected_type = expected_type
        self.coerce = coerce

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None:
            return None

        if isinstance(value, self.expected_type):
            return None

        if self.coerce:
            try:
                self.expected_type(value)
                return None
            except (ValueError, TypeError):
                pass

        return ValidationError(
            field=field,
            message=f"'{field}' must be of type {self.expected_type.__name__}",
            rule=ValidationRule.TYPE,
            value=value,
            expected=self.expected_type.__name__,
            actual=type(value).__name__
        )


class RangeValidator(BaseValidator):
    """Numeric range validator."""

    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None):
        self.min_value = min_value
        self.max_value = max_value

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None:
            return None

        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return ValidationError(
                field=field,
                message=f"'{field}' must be a number",
                rule=ValidationRule.RANGE,
                value=value
            )

        if self.min_value is not None and num_value < self.min_value:
            return ValidationError(
                field=field,
                message=f"'{field}' must be at least {self.min_value}",
                rule=ValidationRule.MIN,
                value=value,
                expected=f">= {self.min_value}"
            )

        if self.max_value is not None and num_value > self.max_value:
            return ValidationError(
                field=field,
                message=f"'{field}' must be at most {self.max_value}",
                rule=ValidationRule.MAX,
                value=value,
                expected=f"<= {self.max_value}"
            )

        return None


class LengthValidator(BaseValidator):
    """String/collection length validator."""

    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None):
        self.min_length = min_length
        self.max_length = max_length

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None:
            return None

        try:
            length = len(value)
        except TypeError:
            return ValidationError(
                field=field,
                message=f"'{field}' must have a length",
                rule=ValidationRule.LENGTH,
                value=value
            )

        if self.min_length is not None and length < self.min_length:
            return ValidationError(
                field=field,
                message=f"'{field}' must be at least {self.min_length} characters",
                rule=ValidationRule.MIN_LENGTH,
                value=value,
                expected=f">= {self.min_length} chars",
                actual=f"{length} chars"
            )

        if self.max_length is not None and length > self.max_length:
            return ValidationError(
                field=field,
                message=f"'{field}' must be at most {self.max_length} characters",
                rule=ValidationRule.MAX_LENGTH,
                value=value,
                expected=f"<= {self.max_length} chars",
                actual=f"{length} chars"
            )

        return None


class PatternValidator(BaseValidator):
    """Regex pattern validator."""

    def __init__(self, pattern: str, message: Optional[str] = None):
        self.pattern = re.compile(pattern)
        self.message = message

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        if not self.pattern.match(value):
            return ValidationError(
                field=field,
                message=self.message or f"'{field}' does not match required pattern",
                rule=ValidationRule.PATTERN,
                value=value,
                expected=self.pattern.pattern
            )

        return None


class EmailValidator(BaseValidator):
    """Email address validator."""

    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None:
            return None

        if not isinstance(value, str) or not self.EMAIL_PATTERN.match(value):
            return ValidationError(
                field=field,
                message=f"'{field}' must be a valid email address",
                rule=ValidationRule.EMAIL,
                value=value
            )

        return None


class URLValidator(BaseValidator):
    """URL validator."""

    URL_PATTERN = re.compile(
        r'^https?://[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+(/.*)?$'
    )

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None:
            return None

        if not isinstance(value, str) or not self.URL_PATTERN.match(value):
            return ValidationError(
                field=field,
                message=f"'{field}' must be a valid URL",
                rule=ValidationRule.URL,
                value=value
            )

        return None


class UUIDValidator(BaseValidator):
    """UUID validator."""

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None:
            return None

        try:
            uuid.UUID(str(value))
            return None
        except ValueError:
            return ValidationError(
                field=field,
                message=f"'{field}' must be a valid UUID",
                rule=ValidationRule.UUID,
                value=value
            )


class ChoicesValidator(BaseValidator):
    """Choices validator."""

    def __init__(self, choices: List[Any]):
        self.choices = choices

    def validate(
        self,
        value: Any,
        field: str,
        context: Dict[str, Any]
    ) -> Optional[ValidationError]:
        if value is None:
            return None

        if value not in self.choices:
            return ValidationError(
                field=field,
                message=f"'{field}' must be one of: {', '.join(str(c) for c in self.choices)}",
                rule=ValidationRule.CHOICES,
                value=value,
                expected=self.choices
            )

        return None


# ============================================================================
# MAIN ENGINE
# ============================================================================

class ValidationEngine:
    """
    Main validation engine.

    Features:
    - Schema-based validation
    - Built-in validators
    - Custom validators
    - Type coercion

    "Ba'el's judgment separates truth from falsehood." — Ba'el
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize validation engine."""
        self.config = config or ValidationConfig()

        # Registered schemas
        self._schemas: Dict[str, ValidationSchema] = {}

        self._lock = threading.RLock()

        logger.info("ValidationEngine initialized")

    # ========================================================================
    # SCHEMA MANAGEMENT
    # ========================================================================

    def register_schema(self, schema: ValidationSchema) -> None:
        """Register a validation schema."""
        with self._lock:
            self._schemas[schema.name] = schema

    def get_schema(self, name: str) -> Optional[ValidationSchema]:
        """Get schema by name."""
        return self._schemas.get(name)

    def create_schema(
        self,
        name: str,
        fields: Dict[str, dict]
    ) -> ValidationSchema:
        """
        Create and register a schema.

        Args:
            name: Schema name
            fields: Dict of field_name -> validator config
        """
        schema = ValidationSchema(name=name)

        for field_name, config in fields.items():
            schema.add_field(field_name, **config)

        self.register_schema(schema)
        return schema

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate(
        self,
        data: Dict[str, Any],
        schema: Union[str, ValidationSchema]
    ) -> ValidationResult:
        """
        Validate data against schema.

        Args:
            data: Data to validate
            schema: Schema name or object

        Returns:
            ValidationResult
        """
        if isinstance(schema, str):
            schema = self.get_schema(schema)
            if not schema:
                raise ValueError(f"Unknown schema: {schema}")

        result = ValidationResult(valid=True, data={})
        context = {'data': data, 'schema': schema}

        # Check for unknown fields if strict
        if schema.strict:
            for key in data.keys():
                if key not in schema.fields:
                    result.add_error(ValidationError(
                        field=key,
                        message=f"Unknown field: '{key}'",
                        rule=ValidationRule.CUSTOM,
                        value=data[key]
                    ))

        # Validate each field
        for field_name, field_validator in schema.fields.items():
            value = data.get(field_name)

            # Required check
            if field_validator.required:
                validator = RequiredValidator()
                error = validator.validate(value, field_name, context)
                if error:
                    result.add_error(error)
                    if self.config.stop_on_first_error:
                        return result
                    continue

            # Skip further validation if value is None and not required
            if value is None:
                continue

            # Type check
            if field_validator.field_type:
                validator = TypeValidator(
                    field_validator.field_type,
                    self.config.coerce_types
                )
                error = validator.validate(value, field_name, context)
                if error:
                    result.add_error(error)
                    if self.config.stop_on_first_error:
                        return result

            # Range check
            if field_validator.min_value is not None or field_validator.max_value is not None:
                validator = RangeValidator(
                    field_validator.min_value,
                    field_validator.max_value
                )
                error = validator.validate(value, field_name, context)
                if error:
                    result.add_error(error)
                    if self.config.stop_on_first_error:
                        return result

            # Length check
            if field_validator.min_length is not None or field_validator.max_length is not None:
                validator = LengthValidator(
                    field_validator.min_length,
                    field_validator.max_length
                )
                error = validator.validate(value, field_name, context)
                if error:
                    result.add_error(error)
                    if self.config.stop_on_first_error:
                        return result

            # Pattern check
            if field_validator.pattern:
                validator = PatternValidator(field_validator.pattern)
                error = validator.validate(value, field_name, context)
                if error:
                    result.add_error(error)
                    if self.config.stop_on_first_error:
                        return result

            # Choices check
            if field_validator.choices:
                validator = ChoicesValidator(field_validator.choices)
                error = validator.validate(value, field_name, context)
                if error:
                    result.add_error(error)
                    if self.config.stop_on_first_error:
                        return result

            # Custom validators
            for custom_validator in field_validator.validators:
                try:
                    custom_result = custom_validator(value, field_name, context)
                    if custom_result:
                        if isinstance(custom_result, ValidationError):
                            result.add_error(custom_result)
                        elif isinstance(custom_result, str):
                            result.add_error(ValidationError(
                                field=field_name,
                                message=custom_result,
                                rule=ValidationRule.CUSTOM,
                                value=value
                            ))
                except Exception as e:
                    result.add_error(ValidationError(
                        field=field_name,
                        message=f"Validation error: {str(e)}",
                        rule=ValidationRule.CUSTOM,
                        value=value
                    ))

            # Store validated value
            result.data[field_name] = value

        # Schema-level validators
        for schema_validator in schema.validators:
            try:
                validator_result = schema_validator(data, context)
                if validator_result:
                    if isinstance(validator_result, ValidationError):
                        result.add_error(validator_result)
                    elif isinstance(validator_result, str):
                        result.add_error(ValidationError(
                            field="_schema",
                            message=validator_result,
                            rule=ValidationRule.CUSTOM,
                            value=data
                        ))
            except Exception as e:
                result.add_error(ValidationError(
                    field="_schema",
                    message=f"Schema validation error: {str(e)}",
                    rule=ValidationRule.CUSTOM,
                    value=data
                ))

        return result

    # ========================================================================
    # CONVENIENCE VALIDATORS
    # ========================================================================

    def validate_email(self, value: str) -> ValidationResult:
        """Validate email address."""
        result = ValidationResult(valid=True)
        validator = EmailValidator()
        error = validator.validate(value, "email", {})
        if error:
            result.add_error(error)
        return result

    def validate_url(self, value: str) -> ValidationResult:
        """Validate URL."""
        result = ValidationResult(valid=True)
        validator = URLValidator()
        error = validator.validate(value, "url", {})
        if error:
            result.add_error(error)
        return result

    def validate_uuid(self, value: str) -> ValidationResult:
        """Validate UUID."""
        result = ValidationResult(valid=True)
        validator = UUIDValidator()
        error = validator.validate(value, "uuid", {})
        if error:
            result.add_error(error)
        return result

    # ========================================================================
    # ASYNC
    # ========================================================================

    async def validate_async(
        self,
        data: Dict[str, Any],
        schema: Union[str, ValidationSchema]
    ) -> ValidationResult:
        """Validate asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.validate(data, schema)
        )

    # ========================================================================
    # STATUS
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        with self._lock:
            return {
                'schemas': len(self._schemas),
                'schema_names': list(self._schemas.keys())
            }


# ============================================================================
# CONVENIENCE
# ============================================================================

validation_engine = ValidationEngine()


def validate(
    data: Dict[str, Any],
    schema: Union[str, ValidationSchema]
) -> ValidationResult:
    """Validate data against schema."""
    return validation_engine.validate(data, schema)
