"""
BAEL Testing Engine
====================

Comprehensive automated testing system.

"Test all possibilities. Accept only perfection." — Ba'el
"""

from .testing_framework import (
    # Enums
    TestStatus,
    TestType,
    AssertionType,
    MockType,
    CoverageMode,

    # Data structures
    TestCase,
    TestResult,
    TestSuite,
    TestReport,
    MockConfig,
    CoverageReport,

    # Classes
    TestingEngine,
    TestRunner,
    MockFactory,
    AssertionLibrary,
    CoverageAnalyzer,
    TestGenerator,

    # Instance
    testing_engine
)

__all__ = [
    # Enums
    "TestStatus",
    "TestType",
    "AssertionType",
    "MockType",
    "CoverageMode",

    # Data structures
    "TestCase",
    "TestResult",
    "TestSuite",
    "TestReport",
    "MockConfig",
    "CoverageReport",

    # Classes
    "TestingEngine",
    "TestRunner",
    "MockFactory",
    "AssertionLibrary",
    "CoverageAnalyzer",
    "TestGenerator",

    # Instance
    "testing_engine"
]
