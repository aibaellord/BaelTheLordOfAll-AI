"""
BAEL Testing Engine
====================

Comprehensive automated testing system.

Features:
- Test case management
- Async test support
- Mock factory
- Assertion library
- Coverage analysis
- AI-powered test generation

"Every line of code must prove its worth." — Ba'el
"""

import asyncio
import hashlib
import inspect
import json
import logging
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from unittest.mock import MagicMock, patch, AsyncMock

logger = logging.getLogger("BAEL.Testing")


# =============================================================================
# ENUMS
# =============================================================================

class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class TestType(Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    REGRESSION = "regression"
    SMOKE = "smoke"


class AssertionType(Enum):
    """Assertion types."""
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    TRUE = "true"
    FALSE = "false"
    NONE = "none"
    NOT_NONE = "not_none"
    IN = "in"
    NOT_IN = "not_in"
    INSTANCE = "instance"
    RAISES = "raises"
    ALMOST_EQUAL = "almost_equal"
    GREATER = "greater"
    LESS = "less"
    CONTAINS = "contains"
    MATCHES = "matches"


class MockType(Enum):
    """Mock types."""
    FUNCTION = "function"
    CLASS = "class"
    PROPERTY = "property"
    ASYNC_FUNCTION = "async_function"
    CONTEXT_MANAGER = "context_manager"
    ITERATOR = "iterator"


class CoverageMode(Enum):
    """Coverage collection modes."""
    LINE = "line"
    BRANCH = "branch"
    FUNCTION = "function"
    STATEMENT = "statement"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TestCase:
    """A test case definition."""
    name: str
    test_fn: Callable
    test_type: TestType = TestType.UNIT
    description: str = ""
    tags: List[str] = field(default_factory=list)
    timeout: float = 30.0
    skip: bool = False
    skip_reason: str = ""
    setup_fn: Optional[Callable] = None
    teardown_fn: Optional[Callable] = None
    fixtures: List[str] = field(default_factory=list)
    expected_result: Any = None

    _id: str = field(default="", init=False)

    def __post_init__(self):
        self._id = hashlib.md5(self.name.encode()).hexdigest()[:8]


@dataclass
class TestResult:
    """Result of a test execution."""
    test_id: str
    name: str
    status: TestStatus
    duration_ms: float = 0.0
    message: str = ""
    error: Optional[str] = None
    traceback: Optional[str] = None
    assertions_passed: int = 0
    assertions_failed: int = 0
    output: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TestSuite:
    """A collection of test cases."""
    name: str
    tests: List[TestCase] = field(default_factory=list)
    description: str = ""
    setup_suite_fn: Optional[Callable] = None
    teardown_suite_fn: Optional[Callable] = None
    tags: List[str] = field(default_factory=list)
    parallel: bool = False


@dataclass
class TestReport:
    """Complete test report."""
    suite_name: str
    results: List[TestResult]
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    coverage: Optional["CoverageReport"] = None

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "pass_rate": f"{self.pass_rate:.2f}%",
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class MockConfig:
    """Mock configuration."""
    target: str
    mock_type: MockType = MockType.FUNCTION
    return_value: Any = None
    side_effect: Optional[Callable] = None
    autospec: bool = False


@dataclass
class CoverageReport:
    """Code coverage report."""
    total_lines: int = 0
    covered_lines: int = 0
    missed_lines: int = 0
    coverage_percent: float = 0.0
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    branches_covered: int = 0
    branches_total: int = 0


# =============================================================================
# ASSERTION LIBRARY
# =============================================================================

class AssertionError(Exception):
    """Custom assertion error."""
    pass


class AssertionLibrary:
    """Comprehensive assertion library."""

    def __init__(self):
        self._assertion_count = 0
        self._failed_assertions: List[str] = []

    def reset(self):
        """Reset assertion counters."""
        self._assertion_count = 0
        self._failed_assertions = []

    @property
    def passed_count(self) -> int:
        return self._assertion_count - len(self._failed_assertions)

    @property
    def failed_count(self) -> int:
        return len(self._failed_assertions)

    def _record(self, passed: bool, message: str):
        """Record assertion result."""
        self._assertion_count += 1
        if not passed:
            self._failed_assertions.append(message)
            raise AssertionError(message)

    def equal(self, actual: Any, expected: Any, message: str = ""):
        """Assert values are equal."""
        passed = actual == expected
        msg = message or f"Expected {expected!r}, got {actual!r}"
        self._record(passed, msg)

    def not_equal(self, actual: Any, expected: Any, message: str = ""):
        """Assert values are not equal."""
        passed = actual != expected
        msg = message or f"Expected {actual!r} to not equal {expected!r}"
        self._record(passed, msg)

    def is_true(self, value: Any, message: str = ""):
        """Assert value is truthy."""
        passed = bool(value)
        msg = message or f"Expected {value!r} to be truthy"
        self._record(passed, msg)

    def is_false(self, value: Any, message: str = ""):
        """Assert value is falsy."""
        passed = not bool(value)
        msg = message or f"Expected {value!r} to be falsy"
        self._record(passed, msg)

    def is_none(self, value: Any, message: str = ""):
        """Assert value is None."""
        passed = value is None
        msg = message or f"Expected None, got {value!r}"
        self._record(passed, msg)

    def is_not_none(self, value: Any, message: str = ""):
        """Assert value is not None."""
        passed = value is not None
        msg = message or f"Expected value to not be None"
        self._record(passed, msg)

    def is_in(self, item: Any, container: Any, message: str = ""):
        """Assert item is in container."""
        passed = item in container
        msg = message or f"Expected {item!r} to be in {container!r}"
        self._record(passed, msg)

    def is_not_in(self, item: Any, container: Any, message: str = ""):
        """Assert item is not in container."""
        passed = item not in container
        msg = message or f"Expected {item!r} to not be in {container!r}"
        self._record(passed, msg)

    def is_instance(self, obj: Any, cls: Type, message: str = ""):
        """Assert object is instance of class."""
        passed = isinstance(obj, cls)
        msg = message or f"Expected {type(obj).__name__} to be instance of {cls.__name__}"
        self._record(passed, msg)

    def raises(self, exception: Type[Exception], fn: Callable, *args, **kwargs):
        """Assert function raises exception."""
        try:
            fn(*args, **kwargs)
            self._record(False, f"Expected {exception.__name__} to be raised")
        except exception:
            self._record(True, "")
        except Exception as e:
            self._record(False, f"Expected {exception.__name__}, got {type(e).__name__}")

    async def raises_async(self, exception: Type[Exception], fn: Callable, *args, **kwargs):
        """Assert async function raises exception."""
        try:
            await fn(*args, **kwargs)
            self._record(False, f"Expected {exception.__name__} to be raised")
        except exception:
            self._record(True, "")
        except Exception as e:
            self._record(False, f"Expected {exception.__name__}, got {type(e).__name__}")

    def almost_equal(self, actual: float, expected: float, delta: float = 0.0001, message: str = ""):
        """Assert floats are almost equal."""
        passed = abs(actual - expected) <= delta
        msg = message or f"Expected {actual} to be within {delta} of {expected}"
        self._record(passed, msg)

    def greater(self, a: Any, b: Any, message: str = ""):
        """Assert a > b."""
        passed = a > b
        msg = message or f"Expected {a} > {b}"
        self._record(passed, msg)

    def less(self, a: Any, b: Any, message: str = ""):
        """Assert a < b."""
        passed = a < b
        msg = message or f"Expected {a} < {b}"
        self._record(passed, msg)

    def greater_equal(self, a: Any, b: Any, message: str = ""):
        """Assert a >= b."""
        passed = a >= b
        msg = message or f"Expected {a} >= {b}"
        self._record(passed, msg)

    def less_equal(self, a: Any, b: Any, message: str = ""):
        """Assert a <= b."""
        passed = a <= b
        msg = message or f"Expected {a} <= {b}"
        self._record(passed, msg)

    def contains(self, haystack: str, needle: str, message: str = ""):
        """Assert string contains substring."""
        passed = needle in haystack
        msg = message or f"Expected {haystack!r} to contain {needle!r}"
        self._record(passed, msg)

    def matches(self, text: str, pattern: str, message: str = ""):
        """Assert string matches regex pattern."""
        passed = bool(re.search(pattern, text))
        msg = message or f"Expected {text!r} to match pattern {pattern!r}"
        self._record(passed, msg)

    def has_length(self, obj: Any, length: int, message: str = ""):
        """Assert object has length."""
        actual = len(obj)
        passed = actual == length
        msg = message or f"Expected length {length}, got {actual}"
        self._record(passed, msg)

    def is_empty(self, obj: Any, message: str = ""):
        """Assert object is empty."""
        passed = len(obj) == 0
        msg = message or f"Expected empty, got {len(obj)} items"
        self._record(passed, msg)

    def is_not_empty(self, obj: Any, message: str = ""):
        """Assert object is not empty."""
        passed = len(obj) > 0
        msg = message or "Expected non-empty"
        self._record(passed, msg)


# =============================================================================
# MOCK FACTORY
# =============================================================================

class MockFactory:
    """Factory for creating mocks."""

    def __init__(self):
        self._mocks: Dict[str, Any] = {}
        self._patches: List[Any] = []

    def create(
        self,
        mock_type: MockType = MockType.FUNCTION,
        return_value: Any = None,
        side_effect: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """Create a mock object."""
        if mock_type == MockType.ASYNC_FUNCTION:
            mock = AsyncMock(return_value=return_value, side_effect=side_effect, **kwargs)
        else:
            mock = MagicMock(return_value=return_value, side_effect=side_effect, **kwargs)

        return mock

    def patch(self, target: str, **kwargs) -> Any:
        """Create a patch context manager."""
        patcher = patch(target, **kwargs)
        self._patches.append(patcher)
        return patcher

    def mock_response(
        self,
        status_code: int = 200,
        json_data: Optional[Dict] = None,
        text: str = "",
        headers: Optional[Dict] = None
    ) -> MagicMock:
        """Create a mock HTTP response."""
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data or {}
        mock.text = text
        mock.headers = headers or {}
        mock.ok = 200 <= status_code < 300
        return mock

    def mock_file(
        self,
        content: str = "",
        name: str = "mock_file.txt"
    ) -> MagicMock:
        """Create a mock file object."""
        mock = MagicMock()
        mock.read.return_value = content
        mock.readline.return_value = content.split('\n')[0] if content else ""
        mock.readlines.return_value = content.split('\n')
        mock.name = name
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    def reset_all(self):
        """Reset all mocks."""
        for mock in self._mocks.values():
            if hasattr(mock, 'reset_mock'):
                mock.reset_mock()

    def stop_all(self):
        """Stop all patches."""
        for patcher in self._patches:
            try:
                patcher.stop()
            except:
                pass
        self._patches.clear()


# =============================================================================
# COVERAGE ANALYZER
# =============================================================================

class CoverageAnalyzer:
    """Code coverage analyzer."""

    def __init__(self):
        self._tracking = False
        self._executed_lines: Dict[str, Set[int]] = defaultdict(set)
        self._total_lines: Dict[str, int] = {}

    def start(self):
        """Start coverage tracking."""
        self._tracking = True
        sys.settrace(self._trace_calls)

    def stop(self):
        """Stop coverage tracking."""
        self._tracking = False
        sys.settrace(None)

    def _trace_calls(self, frame, event, arg):
        """Trace function calls."""
        if not self._tracking:
            return None

        if event == 'line':
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno

            # Only track project files
            if 'site-packages' not in filename and 'lib/python' not in filename:
                self._executed_lines[filename].add(lineno)

        return self._trace_calls

    def get_report(self) -> CoverageReport:
        """Generate coverage report."""
        total_lines = 0
        covered_lines = 0
        files = {}

        for filename, executed in self._executed_lines.items():
            try:
                with open(filename, 'r') as f:
                    lines = f.readlines()

                # Count executable lines (skip blanks, comments)
                executable = []
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#'):
                        executable.append(i)

                file_total = len(executable)
                file_covered = len(executed.intersection(set(executable)))

                total_lines += file_total
                covered_lines += file_covered

                files[filename] = {
                    "total": file_total,
                    "covered": file_covered,
                    "missed": file_total - file_covered,
                    "percent": (file_covered / file_total * 100) if file_total > 0 else 0
                }
            except:
                pass

        return CoverageReport(
            total_lines=total_lines,
            covered_lines=covered_lines,
            missed_lines=total_lines - covered_lines,
            coverage_percent=(covered_lines / total_lines * 100) if total_lines > 0 else 0,
            files=files
        )

    def reset(self):
        """Reset coverage data."""
        self._executed_lines.clear()
        self._total_lines.clear()


# =============================================================================
# TEST RUNNER
# =============================================================================

class TestRunner:
    """Executes tests."""

    def __init__(self):
        self.assertions = AssertionLibrary()
        self.mocks = MockFactory()
        self.coverage = CoverageAnalyzer()

        self._fixtures: Dict[str, Callable] = {}
        self._current_output: List[str] = []

    def register_fixture(self, name: str, factory: Callable):
        """Register a test fixture."""
        self._fixtures[name] = factory

    async def run_test(self, test: TestCase) -> TestResult:
        """Run a single test case."""
        if test.skip:
            return TestResult(
                test_id=test._id,
                name=test.name,
                status=TestStatus.SKIPPED,
                message=test.skip_reason or "Skipped"
            )

        self.assertions.reset()
        self._current_output = []

        start_time = time.time()

        try:
            # Run setup
            if test.setup_fn:
                if asyncio.iscoroutinefunction(test.setup_fn):
                    await test.setup_fn()
                else:
                    test.setup_fn()

            # Prepare fixtures
            fixture_values = {}
            for fixture_name in test.fixtures:
                if fixture_name in self._fixtures:
                    factory = self._fixtures[fixture_name]
                    if asyncio.iscoroutinefunction(factory):
                        fixture_values[fixture_name] = await factory()
                    else:
                        fixture_values[fixture_name] = factory()

            # Run test with timeout
            try:
                if asyncio.iscoroutinefunction(test.test_fn):
                    await asyncio.wait_for(
                        test.test_fn(self.assertions, **fixture_values),
                        timeout=test.timeout
                    )
                else:
                    test.test_fn(self.assertions, **fixture_values)

                status = TestStatus.PASSED if self.assertions.failed_count == 0 else TestStatus.FAILED
                message = "Test passed" if status == TestStatus.PASSED else "Assertions failed"
                error = None
                tb = None

            except asyncio.TimeoutError:
                status = TestStatus.TIMEOUT
                message = f"Test timed out after {test.timeout}s"
                error = message
                tb = None

        except AssertionError as e:
            status = TestStatus.FAILED
            message = str(e)
            error = str(e)
            tb = traceback.format_exc()

        except Exception as e:
            status = TestStatus.ERROR
            message = f"Test error: {str(e)}"
            error = str(e)
            tb = traceback.format_exc()

        finally:
            # Run teardown
            if test.teardown_fn:
                try:
                    if asyncio.iscoroutinefunction(test.teardown_fn):
                        await test.teardown_fn()
                    else:
                        test.teardown_fn()
                except Exception as e:
                    logger.error(f"Teardown error: {e}")

            # Clean up mocks
            self.mocks.stop_all()

        duration_ms = (time.time() - start_time) * 1000

        return TestResult(
            test_id=test._id,
            name=test.name,
            status=status,
            duration_ms=duration_ms,
            message=message,
            error=error,
            traceback=tb,
            assertions_passed=self.assertions.passed_count,
            assertions_failed=self.assertions.failed_count,
            output="\n".join(self._current_output)
        )

    async def run_suite(self, suite: TestSuite, with_coverage: bool = False) -> TestReport:
        """Run a test suite."""
        results = []

        if with_coverage:
            self.coverage.start()

        try:
            # Suite setup
            if suite.setup_suite_fn:
                if asyncio.iscoroutinefunction(suite.setup_suite_fn):
                    await suite.setup_suite_fn()
                else:
                    suite.setup_suite_fn()

            start_time = time.time()

            if suite.parallel:
                # Run tests in parallel
                tasks = [self.run_test(test) for test in suite.tests]
                results = await asyncio.gather(*tasks)
            else:
                # Run tests sequentially
                for test in suite.tests:
                    result = await self.run_test(test)
                    results.append(result)

            duration_ms = (time.time() - start_time) * 1000

            # Suite teardown
            if suite.teardown_suite_fn:
                if asyncio.iscoroutinefunction(suite.teardown_suite_fn):
                    await suite.teardown_suite_fn()
                else:
                    suite.teardown_suite_fn()

        finally:
            if with_coverage:
                self.coverage.stop()

        # Generate report
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        coverage_report = self.coverage.get_report() if with_coverage else None

        return TestReport(
            suite_name=suite.name,
            results=results,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration_ms=duration_ms,
            coverage=coverage_report
        )


# =============================================================================
# TEST GENERATOR
# =============================================================================

class TestGenerator:
    """AI-powered test generation."""

    def __init__(self):
        self._templates: Dict[str, str] = {}
        self._setup_templates()

    def _setup_templates(self):
        """Setup test templates."""
        self._templates = {
            "unit_test": '''
async def test_{name}(assert_lib):
    """Test {description}."""
    # Arrange
    {setup}

    # Act
    result = {action}

    # Assert
    {assertions}
''',
            "parameterized": '''
@pytest.mark.parametrize("input,expected", [
    {params}
])
async def test_{name}(assert_lib, input, expected):
    """Test {description} with parameters."""
    result = {action}
    assert_lib.equal(result, expected)
''',
            "error_case": '''
async def test_{name}_raises_error(assert_lib):
    """Test {description} raises error."""
    await assert_lib.raises_async({exception}, {action})
'''
        }

    def generate_from_function(
        self,
        fn: Callable,
        test_type: str = "unit_test"
    ) -> str:
        """Generate tests from a function."""
        name = fn.__name__
        doc = fn.__doc__ or f"testing {name}"

        # Get signature
        sig = inspect.signature(fn)
        params = list(sig.parameters.keys())

        # Generate basic test
        template = self._templates.get(test_type, self._templates["unit_test"])

        test_code = template.format(
            name=name,
            description=doc,
            setup=f"# Setup for {name}",
            action=f"{name}({', '.join(params)})",
            assertions="assert_lib.is_not_none(result)"
        )

        return test_code

    def generate_edge_cases(self, fn: Callable) -> List[str]:
        """Generate edge case tests."""
        sig = inspect.signature(fn)
        tests = []

        for param_name, param in sig.parameters.items():
            annotation = param.annotation

            # Generate tests based on type hints
            if annotation == str:
                tests.append(f"# Test empty string for {param_name}")
                tests.append(f"# Test very long string for {param_name}")
                tests.append(f"# Test special characters for {param_name}")
            elif annotation == int:
                tests.append(f"# Test zero for {param_name}")
                tests.append(f"# Test negative number for {param_name}")
                tests.append(f"# Test very large number for {param_name}")
            elif annotation == list:
                tests.append(f"# Test empty list for {param_name}")
                tests.append(f"# Test single item list for {param_name}")

        return tests


# =============================================================================
# TESTING ENGINE
# =============================================================================

class TestingEngine:
    """Main testing engine."""

    def __init__(self):
        self.runner = TestRunner()
        self.generator = TestGenerator()

        self._suites: Dict[str, TestSuite] = {}
        self._reports: List[TestReport] = []

    def suite(self, name: str, **kwargs) -> TestSuite:
        """Create or get a test suite."""
        if name not in self._suites:
            self._suites[name] = TestSuite(name=name, **kwargs)
        return self._suites[name]

    def test(
        self,
        name: Optional[str] = None,
        suite: str = "default",
        **kwargs
    ):
        """Decorator to add a test."""
        def decorator(fn: Callable) -> Callable:
            test_name = name or fn.__name__
            test_case = TestCase(
                name=test_name,
                test_fn=fn,
                description=fn.__doc__ or "",
                **kwargs
            )

            target_suite = self.suite(suite)
            target_suite.tests.append(test_case)

            return fn
        return decorator

    def skip(self, reason: str = ""):
        """Decorator to skip a test."""
        def decorator(fn: Callable) -> Callable:
            fn._skip = True
            fn._skip_reason = reason
            return fn
        return decorator

    def fixture(self, name: str):
        """Decorator to register a fixture."""
        def decorator(fn: Callable) -> Callable:
            self.runner.register_fixture(name, fn)
            return fn
        return decorator

    async def run(
        self,
        suite_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        with_coverage: bool = False
    ) -> TestReport:
        """Run tests."""
        if suite_name:
            suite = self._suites.get(suite_name)
            if not suite:
                raise ValueError(f"Suite not found: {suite_name}")

            # Filter by tags
            if tags:
                suite.tests = [t for t in suite.tests if any(tag in t.tags for tag in tags)]

            report = await self.runner.run_suite(suite, with_coverage)
        else:
            # Run all suites
            all_results = []
            total_duration = 0.0

            for suite in self._suites.values():
                if tags:
                    suite.tests = [t for t in suite.tests if any(tag in t.tags for tag in tags)]

                report = await self.runner.run_suite(suite, with_coverage)
                all_results.extend(report.results)
                total_duration += report.duration_ms

            report = TestReport(
                suite_name="all",
                results=all_results,
                total_tests=len(all_results),
                passed=sum(1 for r in all_results if r.status == TestStatus.PASSED),
                failed=sum(1 for r in all_results if r.status == TestStatus.FAILED),
                errors=sum(1 for r in all_results if r.status == TestStatus.ERROR),
                skipped=sum(1 for r in all_results if r.status == TestStatus.SKIPPED),
                duration_ms=total_duration
            )

        self._reports.append(report)
        return report

    async def run_file(self, filepath: Path, with_coverage: bool = False) -> TestReport:
        """Run tests from a file."""
        # Import the module
        import importlib.util

        spec = importlib.util.spec_from_file_location("test_module", filepath)
        if not spec or not spec.loader:
            raise ValueError(f"Cannot load test file: {filepath}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find test functions
        suite = TestSuite(name=filepath.stem)

        for name, obj in inspect.getmembers(module):
            if name.startswith("test_") and callable(obj):
                suite.tests.append(TestCase(
                    name=name,
                    test_fn=obj,
                    skip=getattr(obj, '_skip', False),
                    skip_reason=getattr(obj, '_skip_reason', '')
                ))

        return await self.runner.run_suite(suite, with_coverage)

    def get_report(self, index: int = -1) -> Optional[TestReport]:
        """Get a test report."""
        if not self._reports:
            return None
        return self._reports[index]

    def print_report(self, report: TestReport):
        """Print a formatted test report."""
        print("\n" + "=" * 60)
        print(f"TEST REPORT: {report.suite_name}")
        print("=" * 60)

        for result in report.results:
            status_icon = {
                TestStatus.PASSED: "✓",
                TestStatus.FAILED: "✗",
                TestStatus.ERROR: "!",
                TestStatus.SKIPPED: "-",
                TestStatus.TIMEOUT: "⏱"
            }.get(result.status, "?")

            status_color = {
                TestStatus.PASSED: "\033[92m",
                TestStatus.FAILED: "\033[91m",
                TestStatus.ERROR: "\033[93m",
                TestStatus.SKIPPED: "\033[90m"
            }.get(result.status, "")

            reset = "\033[0m"

            print(f"{status_color}{status_icon} {result.name} ({result.duration_ms:.2f}ms){reset}")

            if result.error:
                print(f"  Error: {result.error}")

        print("-" * 60)
        print(f"Total: {report.total_tests} | "
              f"Passed: {report.passed} | "
              f"Failed: {report.failed} | "
              f"Errors: {report.errors} | "
              f"Skipped: {report.skipped}")
        print(f"Pass Rate: {report.pass_rate:.2f}% | "
              f"Duration: {report.duration_ms:.2f}ms")
        print("=" * 60)

    def get_status(self) -> Dict[str, Any]:
        """Get testing engine status."""
        return {
            "suites": len(self._suites),
            "total_tests": sum(len(s.tests) for s in self._suites.values()),
            "reports": len(self._reports),
            "fixtures": len(self.runner._fixtures),
            "last_report": self._reports[-1].to_dict() if self._reports else None
        }


# =============================================================================
# CONVENIENCE INSTANCE
# =============================================================================

testing_engine = TestingEngine()
