#!/usr/bin/env python3
"""
BAEL - Validator Engine
Comprehensive data and model validation for ML pipelines.

Features:
- Data validation (types, ranges, shapes)
- Model validation (architecture, weights)
- Input/output validation
- Schema validation
- Cross-validation
- Validation reporting
"""

import asyncio
import math
import random
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (Any, Callable, Dict, Generic, Iterator, List, Optional,
                    Pattern, Set, Tuple, Type, TypeVar, Union)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ValidationLevel(Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidatorType(Enum):
    """Validator types."""
    TYPE = "type"
    RANGE = "range"
    SHAPE = "shape"
    REGEX = "regex"
    CUSTOM = "custom"
    SCHEMA = "schema"
    MODEL = "model"


class ValidationStatus(Enum):
    """Validation status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class DataType(Enum):
    """Data types for validation."""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    NONE = "none"
    ANY = "any"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ValidationError:
    """A validation error."""
    field: str = ""
    message: str = ""
    level: ValidationLevel = ValidationLevel.ERROR
    value: Any = None
    expected: Any = None
    validator: str = ""


@dataclass
class ValidationResult:
    """Validation result."""
    status: ValidationStatus = ValidationStatus.PASSED
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    validated_fields: int = 0
    failed_fields: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.PASSED

    def add_error(self, error: ValidationError) -> None:
        """Add an error."""
        if error.level in [ValidationLevel.ERROR, ValidationLevel.CRITICAL]:
            self.errors.append(error)
            self.failed_fields += 1
            self.status = ValidationStatus.FAILED
        else:
            self.warnings.append(error)


@dataclass
class FieldSchema:
    """Schema for a field."""
    name: str = ""
    data_type: DataType = DataType.ANY
    required: bool = True
    nullable: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    choices: Optional[List[Any]] = None
    default: Any = None
    custom_validator: Optional[Callable[[Any], bool]] = None


@dataclass
class DataSchema:
    """Schema for data validation."""
    name: str = ""
    fields: Dict[str, FieldSchema] = field(default_factory=dict)
    allow_extra: bool = False
    strict: bool = True


@dataclass
class CrossValidationResult:
    """Cross-validation result."""
    n_folds: int = 0
    fold_results: List[Dict[str, float]] = field(default_factory=list)
    mean_scores: Dict[str, float] = field(default_factory=dict)
    std_scores: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# BASE VALIDATOR
# =============================================================================

class BaseValidator(ABC):
    """Abstract base validator."""

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__

    @abstractmethod
    def validate(self, value: Any, **kwargs) -> ValidationResult:
        """Validate a value."""
        pass


# =============================================================================
# VALIDATOR IMPLEMENTATIONS
# =============================================================================

class TypeValidator(BaseValidator):
    """Type validator."""

    TYPE_MAP = {
        DataType.INT: int,
        DataType.FLOAT: (int, float),
        DataType.STRING: str,
        DataType.BOOL: bool,
        DataType.LIST: list,
        DataType.DICT: dict,
        DataType.NONE: type(None),
    }

    def __init__(self, expected_type: DataType):
        super().__init__("TypeValidator")
        self._expected_type = expected_type

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate type."""
        result = ValidationResult(validated_fields=1)

        if self._expected_type == DataType.ANY:
            return result

        expected = self.TYPE_MAP.get(self._expected_type)

        if not isinstance(value, expected):
            result.add_error(ValidationError(
                field=field_name,
                message=f"Expected {self._expected_type.value}, got {type(value).__name__}",
                level=ValidationLevel.ERROR,
                value=value,
                expected=self._expected_type.value,
                validator=self.name
            ))

        return result


class RangeValidator(BaseValidator):
    """Range validator for numeric values."""

    def __init__(
        self,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        inclusive: bool = True
    ):
        super().__init__("RangeValidator")
        self._min = min_value
        self._max = max_value
        self._inclusive = inclusive

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate range."""
        result = ValidationResult(validated_fields=1)

        if not isinstance(value, (int, float)):
            result.add_error(ValidationError(
                field=field_name,
                message="Value must be numeric for range validation",
                level=ValidationLevel.ERROR,
                value=value,
                validator=self.name
            ))
            return result

        if self._min is not None:
            if self._inclusive:
                valid = value >= self._min
            else:
                valid = value > self._min

            if not valid:
                result.add_error(ValidationError(
                    field=field_name,
                    message=f"Value {value} is below minimum {self._min}",
                    level=ValidationLevel.ERROR,
                    value=value,
                    expected=f">= {self._min}" if self._inclusive else f"> {self._min}",
                    validator=self.name
                ))

        if self._max is not None:
            if self._inclusive:
                valid = value <= self._max
            else:
                valid = value < self._max

            if not valid:
                result.add_error(ValidationError(
                    field=field_name,
                    message=f"Value {value} is above maximum {self._max}",
                    level=ValidationLevel.ERROR,
                    value=value,
                    expected=f"<= {self._max}" if self._inclusive else f"< {self._max}",
                    validator=self.name
                ))

        return result


class ShapeValidator(BaseValidator):
    """Shape validator for arrays/lists."""

    def __init__(self, expected_shape: Tuple[int, ...]):
        super().__init__("ShapeValidator")
        self._expected_shape = expected_shape

    def _get_shape(self, data: Any) -> Tuple[int, ...]:
        """Get shape of data."""
        if isinstance(data, list):
            if not data:
                return (0,)

            if isinstance(data[0], list):
                inner_shapes = [self._get_shape(item) for item in data]
                if all(s == inner_shapes[0] for s in inner_shapes):
                    return (len(data),) + inner_shapes[0]
                return (len(data), -1)

            return (len(data),)

        return ()

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate shape."""
        result = ValidationResult(validated_fields=1)

        actual_shape = self._get_shape(value)

        if actual_shape != self._expected_shape:
            result.add_error(ValidationError(
                field=field_name,
                message=f"Shape {actual_shape} does not match expected {self._expected_shape}",
                level=ValidationLevel.ERROR,
                value=f"shape={actual_shape}",
                expected=f"shape={self._expected_shape}",
                validator=self.name
            ))

        return result


class RegexValidator(BaseValidator):
    """Regex pattern validator."""

    def __init__(self, pattern: str, flags: int = 0):
        super().__init__("RegexValidator")
        self._pattern = re.compile(pattern, flags)

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate against regex."""
        result = ValidationResult(validated_fields=1)

        if not isinstance(value, str):
            result.add_error(ValidationError(
                field=field_name,
                message="Value must be string for regex validation",
                level=ValidationLevel.ERROR,
                value=value,
                validator=self.name
            ))
            return result

        if not self._pattern.match(value):
            result.add_error(ValidationError(
                field=field_name,
                message=f"Value does not match pattern {self._pattern.pattern}",
                level=ValidationLevel.ERROR,
                value=value,
                expected=self._pattern.pattern,
                validator=self.name
            ))

        return result


class LengthValidator(BaseValidator):
    """Length validator for sequences."""

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ):
        super().__init__("LengthValidator")
        self._min = min_length
        self._max = max_length

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate length."""
        result = ValidationResult(validated_fields=1)

        try:
            length = len(value)
        except TypeError:
            result.add_error(ValidationError(
                field=field_name,
                message="Value has no length",
                level=ValidationLevel.ERROR,
                value=value,
                validator=self.name
            ))
            return result

        if self._min is not None and length < self._min:
            result.add_error(ValidationError(
                field=field_name,
                message=f"Length {length} is below minimum {self._min}",
                level=ValidationLevel.ERROR,
                value=length,
                expected=f">= {self._min}",
                validator=self.name
            ))

        if self._max is not None and length > self._max:
            result.add_error(ValidationError(
                field=field_name,
                message=f"Length {length} is above maximum {self._max}",
                level=ValidationLevel.ERROR,
                value=length,
                expected=f"<= {self._max}",
                validator=self.name
            ))

        return result


class ChoiceValidator(BaseValidator):
    """Choice validator."""

    def __init__(self, choices: List[Any]):
        super().__init__("ChoiceValidator")
        self._choices = set(choices)

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate choice."""
        result = ValidationResult(validated_fields=1)

        if value not in self._choices:
            result.add_error(ValidationError(
                field=field_name,
                message=f"Value must be one of {list(self._choices)}",
                level=ValidationLevel.ERROR,
                value=value,
                expected=list(self._choices),
                validator=self.name
            ))

        return result


class NotNullValidator(BaseValidator):
    """Not null validator."""

    def __init__(self):
        super().__init__("NotNullValidator")

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate not null."""
        result = ValidationResult(validated_fields=1)

        if value is None:
            result.add_error(ValidationError(
                field=field_name,
                message="Value cannot be null",
                level=ValidationLevel.ERROR,
                value=value,
                validator=self.name
            ))

        return result


class CustomValidator(BaseValidator):
    """Custom function validator."""

    def __init__(self, validator_func: Callable[[Any], bool], message: str = ""):
        super().__init__("CustomValidator")
        self._func = validator_func
        self._message = message or "Custom validation failed"

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate with custom function."""
        result = ValidationResult(validated_fields=1)

        try:
            valid = self._func(value)

            if not valid:
                result.add_error(ValidationError(
                    field=field_name,
                    message=self._message,
                    level=ValidationLevel.ERROR,
                    value=value,
                    validator=self.name
                ))
        except Exception as e:
            result.add_error(ValidationError(
                field=field_name,
                message=f"Validation error: {str(e)}",
                level=ValidationLevel.ERROR,
                value=value,
                validator=self.name
            ))

        return result


# =============================================================================
# SCHEMA VALIDATOR
# =============================================================================

class SchemaValidator(BaseValidator):
    """Schema-based validator."""

    def __init__(self, schema: DataSchema):
        super().__init__("SchemaValidator")
        self._schema = schema

    def validate(self, data: Dict[str, Any], **kwargs) -> ValidationResult:
        """Validate against schema."""
        result = ValidationResult()

        for name, field_schema in self._schema.fields.items():
            result.validated_fields += 1

            if name not in data:
                if field_schema.required:
                    result.add_error(ValidationError(
                        field=name,
                        message="Required field missing",
                        level=ValidationLevel.ERROR,
                        validator=self.name
                    ))
                continue

            value = data[name]

            if value is None:
                if not field_schema.nullable:
                    result.add_error(ValidationError(
                        field=name,
                        message="Field cannot be null",
                        level=ValidationLevel.ERROR,
                        value=value,
                        validator=self.name
                    ))
                continue

            type_validator = TypeValidator(field_schema.data_type)
            type_result = type_validator.validate(value, name)

            if not type_result.is_valid:
                result.errors.extend(type_result.errors)
                result.failed_fields += 1
                result.status = ValidationStatus.FAILED
                continue

            if field_schema.min_value is not None or field_schema.max_value is not None:
                range_validator = RangeValidator(field_schema.min_value, field_schema.max_value)
                range_result = range_validator.validate(value, name)

                if not range_result.is_valid:
                    result.errors.extend(range_result.errors)
                    result.failed_fields += 1
                    result.status = ValidationStatus.FAILED

            if field_schema.min_length is not None or field_schema.max_length is not None:
                length_validator = LengthValidator(field_schema.min_length, field_schema.max_length)
                length_result = length_validator.validate(value, name)

                if not length_result.is_valid:
                    result.errors.extend(length_result.errors)
                    result.failed_fields += 1
                    result.status = ValidationStatus.FAILED

            if field_schema.pattern is not None:
                regex_validator = RegexValidator(field_schema.pattern)
                regex_result = regex_validator.validate(value, name)

                if not regex_result.is_valid:
                    result.errors.extend(regex_result.errors)
                    result.failed_fields += 1
                    result.status = ValidationStatus.FAILED

            if field_schema.choices is not None:
                choice_validator = ChoiceValidator(field_schema.choices)
                choice_result = choice_validator.validate(value, name)

                if not choice_result.is_valid:
                    result.errors.extend(choice_result.errors)
                    result.failed_fields += 1
                    result.status = ValidationStatus.FAILED

            if field_schema.custom_validator is not None:
                custom_validator = CustomValidator(field_schema.custom_validator)
                custom_result = custom_validator.validate(value, name)

                if not custom_result.is_valid:
                    result.errors.extend(custom_result.errors)
                    result.failed_fields += 1
                    result.status = ValidationStatus.FAILED

        if not self._schema.allow_extra:
            extra_fields = set(data.keys()) - set(self._schema.fields.keys())

            if extra_fields and self._schema.strict:
                for extra in extra_fields:
                    result.add_error(ValidationError(
                        field=extra,
                        message="Extra field not allowed",
                        level=ValidationLevel.WARNING,
                        validator=self.name
                    ))

        return result


# =============================================================================
# VALIDATOR ENGINE
# =============================================================================

class ValidatorEngine:
    """
    Validator Engine for BAEL.

    Comprehensive data and model validation.
    """

    def __init__(self):
        self._validators: Dict[str, BaseValidator] = {}
        self._schemas: Dict[str, DataSchema] = {}

    def register_validator(self, name: str, validator: BaseValidator) -> None:
        """Register a validator."""
        self._validators[name] = validator

    def register_schema(self, name: str, schema: DataSchema) -> None:
        """Register a schema."""
        self._schemas[name] = schema
        self._validators[f"schema_{name}"] = SchemaValidator(schema)

    def validate(
        self,
        value: Any,
        validator_name: str,
        **kwargs
    ) -> ValidationResult:
        """Validate using named validator."""
        if validator_name not in self._validators:
            return ValidationResult(status=ValidationStatus.SKIPPED)

        return self._validators[validator_name].validate(value, **kwargs)

    def validate_schema(
        self,
        data: Dict[str, Any],
        schema_name: str
    ) -> ValidationResult:
        """Validate against schema."""
        return self.validate(data, f"schema_{schema_name}")

    def create_type_validator(self, name: str, data_type: DataType) -> TypeValidator:
        """Create and register type validator."""
        validator = TypeValidator(data_type)
        self._validators[name] = validator
        return validator

    def create_range_validator(
        self,
        name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> RangeValidator:
        """Create and register range validator."""
        validator = RangeValidator(min_value, max_value)
        self._validators[name] = validator
        return validator

    def cross_validate(
        self,
        data: List[Any],
        labels: List[Any],
        n_folds: int = 5,
        evaluator: Optional[Callable[[List, List], Dict[str, float]]] = None
    ) -> CrossValidationResult:
        """Perform cross-validation."""
        fold_size = len(data) // n_folds
        indices = list(range(len(data)))
        random.shuffle(indices)

        fold_results = []

        for fold in range(n_folds):
            test_start = fold * fold_size
            test_end = test_start + fold_size if fold < n_folds - 1 else len(data)

            test_indices = indices[test_start:test_end]
            train_indices = indices[:test_start] + indices[test_end:]

            train_data = [data[i] for i in train_indices]
            train_labels = [labels[i] for i in train_indices]
            test_data = [data[i] for i in test_indices]
            test_labels = [labels[i] for i in test_indices]

            if evaluator:
                metrics = evaluator(test_data, test_labels)
            else:
                metrics = {"fold": fold, "test_size": len(test_data)}

            fold_results.append(metrics)

        mean_scores = {}
        std_scores = {}

        all_keys = set()
        for result in fold_results:
            all_keys.update(result.keys())

        for key in all_keys:
            values = [r.get(key, 0) for r in fold_results]
            mean_scores[key] = sum(values) / len(values)

            variance = sum((v - mean_scores[key]) ** 2 for v in values) / len(values)
            std_scores[key] = math.sqrt(variance)

        return CrossValidationResult(
            n_folds=n_folds,
            fold_results=fold_results,
            mean_scores=mean_scores,
            std_scores=std_scores
        )


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Validator Engine."""
    print("=" * 70)
    print("BAEL - VALIDATOR ENGINE DEMO")
    print("Comprehensive Data and Model Validation")
    print("=" * 70)
    print()

    engine = ValidatorEngine()

    # 1. Type Validation
    print("1. TYPE VALIDATION:")
    print("-" * 40)

    engine.create_type_validator("int_validator", DataType.INT)

    result = engine.validate(42, "int_validator")
    print(f"   42 as int: {'PASSED' if result.is_valid else 'FAILED'}")

    result = engine.validate("hello", "int_validator")
    print(f"   'hello' as int: {'PASSED' if result.is_valid else 'FAILED'}")
    if result.errors:
        print(f"   Error: {result.errors[0].message}")
    print()

    # 2. Range Validation
    print("2. RANGE VALIDATION:")
    print("-" * 40)

    engine.create_range_validator("age_validator", 0, 120)

    result = engine.validate(25, "age_validator")
    print(f"   25 in [0, 120]: {'PASSED' if result.is_valid else 'FAILED'}")

    result = engine.validate(-5, "age_validator")
    print(f"   -5 in [0, 120]: {'PASSED' if result.is_valid else 'FAILED'}")
    if result.errors:
        print(f"   Error: {result.errors[0].message}")
    print()

    # 3. Regex Validation
    print("3. REGEX VALIDATION:")
    print("-" * 40)

    email_validator = RegexValidator(r"^[\w.-]+@[\w.-]+\.\w+$")
    engine.register_validator("email_validator", email_validator)

    result = engine.validate("user@example.com", "email_validator")
    print(f"   'user@example.com': {'PASSED' if result.is_valid else 'FAILED'}")

    result = engine.validate("invalid-email", "email_validator")
    print(f"   'invalid-email': {'PASSED' if result.is_valid else 'FAILED'}")
    print()

    # 4. Length Validation
    print("4. LENGTH VALIDATION:")
    print("-" * 40)

    length_validator = LengthValidator(3, 10)
    engine.register_validator("length_validator", length_validator)

    result = engine.validate("hello", "length_validator")
    print(f"   'hello' (len 5): {'PASSED' if result.is_valid else 'FAILED'}")

    result = engine.validate("hi", "length_validator")
    print(f"   'hi' (len 2): {'PASSED' if result.is_valid else 'FAILED'}")
    print()

    # 5. Choice Validation
    print("5. CHOICE VALIDATION:")
    print("-" * 40)

    choice_validator = ChoiceValidator(["red", "green", "blue"])
    engine.register_validator("color_validator", choice_validator)

    result = engine.validate("red", "color_validator")
    print(f"   'red' in colors: {'PASSED' if result.is_valid else 'FAILED'}")

    result = engine.validate("yellow", "color_validator")
    print(f"   'yellow' in colors: {'PASSED' if result.is_valid else 'FAILED'}")
    print()

    # 6. Custom Validation
    print("6. CUSTOM VALIDATION:")
    print("-" * 40)

    def is_even(x):
        return x % 2 == 0

    even_validator = CustomValidator(is_even, "Value must be even")
    engine.register_validator("even_validator", even_validator)

    result = engine.validate(4, "even_validator")
    print(f"   4 is even: {'PASSED' if result.is_valid else 'FAILED'}")

    result = engine.validate(7, "even_validator")
    print(f"   7 is even: {'PASSED' if result.is_valid else 'FAILED'}")
    print()

    # 7. Schema Validation
    print("7. SCHEMA VALIDATION:")
    print("-" * 40)

    user_schema = DataSchema(
        name="user",
        fields={
            "name": FieldSchema(name="name", data_type=DataType.STRING, min_length=1),
            "age": FieldSchema(name="age", data_type=DataType.INT, min_value=0, max_value=120),
            "email": FieldSchema(name="email", data_type=DataType.STRING, pattern=r"^[\w.-]+@[\w.-]+\.\w+$"),
            "role": FieldSchema(name="role", data_type=DataType.STRING, choices=["admin", "user", "guest"]),
        }
    )

    engine.register_schema("user", user_schema)

    valid_user = {
        "name": "Alice",
        "age": 30,
        "email": "alice@example.com",
        "role": "admin"
    }

    result = engine.validate_schema(valid_user, "user")
    print(f"   Valid user: {'PASSED' if result.is_valid else 'FAILED'}")

    invalid_user = {
        "name": "",
        "age": 150,
        "email": "invalid",
        "role": "superadmin"
    }

    result = engine.validate_schema(invalid_user, "user")
    print(f"   Invalid user: {'PASSED' if result.is_valid else 'FAILED'}")
    print(f"   Errors: {len(result.errors)}")
    for error in result.errors[:3]:
        print(f"     - {error.field}: {error.message}")
    print()

    # 8. Shape Validation
    print("8. SHAPE VALIDATION:")
    print("-" * 40)

    shape_validator = ShapeValidator((3, 3))
    engine.register_validator("matrix_3x3", shape_validator)

    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    result = engine.validate(matrix, "matrix_3x3")
    print(f"   3x3 matrix: {'PASSED' if result.is_valid else 'FAILED'}")

    matrix = [[1, 2], [3, 4]]
    result = engine.validate(matrix, "matrix_3x3")
    print(f"   2x2 matrix: {'PASSED' if result.is_valid else 'FAILED'}")
    print()

    # 9. Cross Validation
    print("9. CROSS VALIDATION:")
    print("-" * 40)

    data = list(range(100))
    labels = [i % 2 for i in range(100)]

    def mock_evaluator(test_data, test_labels):
        return {
            "accuracy": 0.8 + random.random() * 0.1,
            "f1": 0.75 + random.random() * 0.1
        }

    cv_result = engine.cross_validate(data, labels, n_folds=5, evaluator=mock_evaluator)

    print(f"   Folds: {cv_result.n_folds}")
    print(f"   Mean Accuracy: {cv_result.mean_scores['accuracy']:.4f} ± {cv_result.std_scores['accuracy']:.4f}")
    print(f"   Mean F1: {cv_result.mean_scores['f1']:.4f} ± {cv_result.std_scores['f1']:.4f}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Validator Engine Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
