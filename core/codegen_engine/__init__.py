"""
BAEL Code Generation Engine Package
=====================================

Advanced code synthesis and generation capabilities.
"""

from .code_generator import (
    # Enums
    Language,
    CodeStyle,
    CodePattern,
    ComponentType,
    TestType,

    # Dataclasses
    CodeSpec,
    GeneratedCode,
    CodeTemplate,

    # Classes
    TemplateRegistry,
    CodeFormatter,
    PatternGenerator,
    TestGenerator,
    CodeGenerationEngine,

    # Convenience instance
    codegen_engine
)

__all__ = [
    # Enums
    "Language",
    "CodeStyle",
    "CodePattern",
    "ComponentType",
    "TestType",

    # Dataclasses
    "CodeSpec",
    "GeneratedCode",
    "CodeTemplate",

    # Classes
    "TemplateRegistry",
    "CodeFormatter",
    "PatternGenerator",
    "TestGenerator",
    "CodeGenerationEngine",

    # Instance
    "codegen_engine"
]
