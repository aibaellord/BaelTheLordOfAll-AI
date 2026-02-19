"""
BAEL Validation Engine
======================

Data validation with schemas and constraints.

"Ba'el ensures only truth passes through the gates." — Ba'el
"""

from .validation_engine import (
    # Enums
    ValidationRule,
    ValidationSeverity,

    # Data structures
    FieldValidator,
    ValidationError,
    ValidationResult,
    ValidationSchema,
    ValidationConfig,

    # Built-in validators
    RequiredValidator,
    TypeValidator,
    RangeValidator,
    PatternValidator,
    LengthValidator,
    EmailValidator,
    URLValidator,

    # Main engine
    ValidationEngine,

    # Convenience
    validate,
    validation_engine
)

__all__ = [
    'ValidationRule',
    'ValidationSeverity',
    'FieldValidator',
    'ValidationError',
    'ValidationResult',
    'ValidationSchema',
    'ValidationConfig',
    'RequiredValidator',
    'TypeValidator',
    'RangeValidator',
    'PatternValidator',
    'LengthValidator',
    'EmailValidator',
    'URLValidator',
    'ValidationEngine',
    'validate',
    'validation_engine'
]
