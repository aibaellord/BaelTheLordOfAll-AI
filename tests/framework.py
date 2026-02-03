#!/usr/bin/env python3
"""
BAEL - Testing Framework
Comprehensive test suite with unit, integration, and e2e tests.

Features:
- Unit test framework
- Integration testing
- End-to-end scenarios
- Performance benchmarks
- Coverage reporting
- Mock providers
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type
from unittest.mock import AsyncMock, MagicMock, patch

# =============================================================================
# TEST TYPES
# =============================================================================

class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestType(Enum):
    """Test type classification."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SMOKE = "smoke"


@dataclass
class TestResult:
    """Individual test result."""
    name: str
    status: TestStatus
    duration_ms: float
    test_type: TestType = TestType.UNIT
    error: Optional[str] = None
    traceback: Optional[str] = None
    assertions: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "test_type": self.test_type.value,
            "error": self.error,
            "assertions": self.assertions,
            "metadata": self.metadata
        }


@dataclass
class TestSuiteResult:
    """Test suite result summary."""
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_ms: float = 0
    results: List[TestResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0
        return (self.passed / self.total) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "success_rate": round(self.success_rate, 2),
            "results": [r.to_dict() for r in self.results]
        }


# =============================================================================
# ASSERTIONS
# =============================================================================

class AssertionError(Exception):
    """Custom assertion error."""
    pass


class Assertions:
    """Assertion helpers."""

    assertion_count = 0

    @classmethod
    def reset(cls):
        cls.assertion_count = 0

    @classmethod
    def assertEqual(cls, actual: Any, expected: Any, message: str = ""):
        cls.assertion_count += 1
        if actual != expected:
            msg = f"Expected {expected!r}, got {actual!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertNotEqual(cls, actual: Any, not_expected: Any, message: str = ""):
        cls.assertion_count += 1
        if actual == not_expected:
            msg = f"Expected value to not equal {not_expected!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertTrue(cls, value: Any, message: str = ""):
        cls.assertion_count += 1
        if not value:
            msg = f"Expected truthy value, got {value!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertFalse(cls, value: Any, message: str = ""):
        cls.assertion_count += 1
        if value:
            msg = f"Expected falsy value, got {value!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertNone(cls, value: Any, message: str = ""):
        cls.assertion_count += 1
        if value is not None:
            msg = f"Expected None, got {value!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertNotNone(cls, value: Any, message: str = ""):
        cls.assertion_count += 1
        if value is None:
            msg = "Expected non-None value"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertIn(cls, item: Any, container: Any, message: str = ""):
        cls.assertion_count += 1
        if item not in container:
            msg = f"Expected {item!r} to be in {container!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertNotIn(cls, item: Any, container: Any, message: str = ""):
        cls.assertion_count += 1
        if item in container:
            msg = f"Expected {item!r} to not be in {container!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertRaises(cls, exception: Type[Exception], func: Callable, *args, **kwargs):
        cls.assertion_count += 1
        try:
            func(*args, **kwargs)
            raise AssertionError(f"Expected {exception.__name__} to be raised")
        except exception:
            pass

    @classmethod
    async def assertRaisesAsync(cls, exception: Type[Exception], func: Callable, *args, **kwargs):
        cls.assertion_count += 1
        try:
            await func(*args, **kwargs)
            raise AssertionError(f"Expected {exception.__name__} to be raised")
        except exception:
            pass

    @classmethod
    def assertIsInstance(cls, obj: Any, types: type, message: str = ""):
        cls.assertion_count += 1
        if not isinstance(obj, types):
            msg = f"Expected instance of {types}, got {type(obj)}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertGreater(cls, a: Any, b: Any, message: str = ""):
        cls.assertion_count += 1
        if not a > b:
            msg = f"Expected {a!r} > {b!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertLess(cls, a: Any, b: Any, message: str = ""):
        cls.assertion_count += 1
        if not a < b:
            msg = f"Expected {a!r} < {b!r}"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)

    @classmethod
    def assertAlmostEqual(cls, a: float, b: float, places: int = 7, message: str = ""):
        cls.assertion_count += 1
        if round(abs(a - b), places) != 0:
            msg = f"Expected {a!r} ≈ {b!r} (to {places} places)"
            if message:
                msg = f"{message}: {msg}"
            raise AssertionError(msg)


# =============================================================================
# TEST DECORATORS
# =============================================================================

def test(func: Callable = None, *, skip: bool = False, skip_reason: str = "",
         timeout: float = 30.0, test_type: TestType = TestType.UNIT):
    """Decorator to mark a function as a test."""

    def decorator(fn: Callable) -> Callable:
        fn._is_test = True
        fn._skip = skip
        fn._skip_reason = skip_reason
        fn._timeout = timeout
        fn._test_type = test_type
        return fn

    if func is not None:
        return decorator(func)
    return decorator


def skip(reason: str = ""):
    """Decorator to skip a test."""
    def decorator(func: Callable) -> Callable:
        func._is_test = True
        func._skip = True
        func._skip_reason = reason
        return func
    return decorator


def skip_if(condition: bool, reason: str = ""):
    """Decorator to conditionally skip a test."""
    def decorator(func: Callable) -> Callable:
        if condition:
            func._skip = True
            func._skip_reason = reason
        return func
    return decorator


def timeout(seconds: float):
    """Decorator to set test timeout."""
    def decorator(func: Callable) -> Callable:
        func._timeout = seconds
        return func
    return decorator


def parametrize(params: List[Dict[str, Any]]):
    """Decorator for parametrized tests."""
    def decorator(func: Callable) -> Callable:
        func._parametrized = params
        return func
    return decorator


# =============================================================================
# TEST FIXTURES
# =============================================================================

class Fixture:
    """Test fixture base class."""

    async def setup(self) -> None:
        """Setup fixture before test."""
        pass

    async def teardown(self) -> None:
        """Teardown fixture after test."""
        pass


class TempDirFixture(Fixture):
    """Temporary directory fixture."""

    def __init__(self):
        self.path: Optional[Path] = None

    async def setup(self) -> None:
        import tempfile
        self.path = Path(tempfile.mkdtemp())

    async def teardown(self) -> None:
        if self.path and self.path.exists():
            import shutil
            shutil.rmtree(self.path)


class MockServerFixture(Fixture):
    """Mock HTTP server fixture."""

    def __init__(self, responses: Dict[str, Any] = None):
        self.responses = responses or {}
        self.server = None
        self.port = 0

    async def setup(self) -> None:
        # Would start mock server
        self.port = 8765

    async def teardown(self) -> None:
        if self.server:
            # Would stop server
            pass

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"


# =============================================================================
# MOCK PROVIDERS
# =============================================================================

class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, responses: List[str] = None):
        self.responses = responses or ["Mock response"]
        self.call_count = 0
        self.calls: List[Dict[str, Any]] = []

    async def generate(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        self.calls.append({"prompt": prompt, "kwargs": kwargs})

        idx = (self.call_count - 1) % len(self.responses)
        return self.responses[idx]

    def reset(self):
        self.call_count = 0
        self.calls = []


class MockMemoryProvider:
    """Mock memory provider for testing."""

    def __init__(self):
        self.memories: Dict[str, Any] = {}

    async def store(self, key: str, value: Any) -> None:
        self.memories[key] = value

    async def retrieve(self, key: str) -> Optional[Any]:
        return self.memories.get(key)

    async def search(self, query: str, limit: int = 10) -> List[Any]:
        return list(self.memories.values())[:limit]

    def clear(self):
        self.memories = {}


class MockToolExecutor:
    """Mock tool executor for testing."""

    def __init__(self, results: Dict[str, Any] = None):
        self.results = results or {}
        self.executions: List[Dict[str, Any]] = []

    async def execute(self, tool_name: str, **params) -> Any:
        self.executions.append({"tool": tool_name, "params": params})
        return self.results.get(tool_name, {"status": "success"})


# =============================================================================
# TEST RUNNER
# =============================================================================

class TestRunner:
    """Test runner with discovery and execution."""

    def __init__(self):
        self.fixtures: Dict[str, Fixture] = {}
        self.before_all: List[Callable] = []
        self.after_all: List[Callable] = []
        self.before_each: List[Callable] = []
        self.after_each: List[Callable] = []

    def add_fixture(self, name: str, fixture: Fixture) -> None:
        """Add a fixture."""
        self.fixtures[name] = fixture

    async def run_test(self, test_func: Callable) -> TestResult:
        """Run a single test function."""
        name = test_func.__name__

        # Check if skipped
        if getattr(test_func, '_skip', False):
            return TestResult(
                name=name,
                status=TestStatus.SKIPPED,
                duration_ms=0,
                test_type=getattr(test_func, '_test_type', TestType.UNIT),
                metadata={"skip_reason": getattr(test_func, '_skip_reason', "")}
            )

        # Reset assertions
        Assertions.reset()

        start_time = time.perf_counter()

        try:
            # Setup fixtures
            for fixture in self.fixtures.values():
                await fixture.setup()

            # Run before_each hooks
            for hook in self.before_each:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()

            # Get timeout
            timeout_seconds = getattr(test_func, '_timeout', 30.0)

            # Run test with timeout
            if asyncio.iscoroutinefunction(test_func):
                await asyncio.wait_for(test_func(), timeout=timeout_seconds)
            else:
                test_func()

            # Run after_each hooks
            for hook in self.after_each:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()

            duration_ms = (time.perf_counter() - start_time) * 1000

            return TestResult(
                name=name,
                status=TestStatus.PASSED,
                duration_ms=duration_ms,
                test_type=getattr(test_func, '_test_type', TestType.UNIT),
                assertions=Assertions.assertion_count
            )

        except AssertionError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration_ms=duration_ms,
                test_type=getattr(test_func, '_test_type', TestType.UNIT),
                error=str(e),
                assertions=Assertions.assertion_count
            )

        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return TestResult(
                name=name,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                test_type=getattr(test_func, '_test_type', TestType.UNIT),
                error="Test timed out"
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return TestResult(
                name=name,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                test_type=getattr(test_func, '_test_type', TestType.UNIT),
                error=str(e),
                traceback=traceback.format_exc()
            )

        finally:
            # Teardown fixtures
            for fixture in self.fixtures.values():
                try:
                    await fixture.teardown()
                except:
                    pass

    async def run_suite(self, test_class: type) -> TestSuiteResult:
        """Run all tests in a test class."""
        suite_name = test_class.__name__
        suite_result = TestSuiteResult(name=suite_name)

        start_time = time.perf_counter()

        # Get test methods
        test_methods = [
            getattr(test_class, name)
            for name in dir(test_class)
            if name.startswith('test_') or getattr(getattr(test_class, name), '_is_test', False)
        ]

        # Run before_all hooks
        for hook in self.before_all:
            if asyncio.iscoroutinefunction(hook):
                await hook()
            else:
                hook()

        # Create instance
        instance = test_class()

        # Run tests
        for method in test_methods:
            bound_method = method.__get__(instance, test_class)
            result = await self.run_test(bound_method)
            suite_result.results.append(result)
            suite_result.total += 1

            if result.status == TestStatus.PASSED:
                suite_result.passed += 1
            elif result.status == TestStatus.FAILED:
                suite_result.failed += 1
            elif result.status == TestStatus.SKIPPED:
                suite_result.skipped += 1
            else:
                suite_result.errors += 1

        # Run after_all hooks
        for hook in self.after_all:
            if asyncio.iscoroutinefunction(hook):
                await hook()
            else:
                hook()

        suite_result.duration_ms = (time.perf_counter() - start_time) * 1000

        return suite_result

    def discover_tests(self, path: str) -> List[type]:
        """Discover test classes in a directory."""
        test_classes = []
        test_path = Path(path)

        for file in test_path.glob("**/test_*.py"):
            # Import module and find test classes
            import importlib.util
            spec = importlib.util.spec_from_file_location(file.stem, file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)

                    for name in dir(module):
                        obj = getattr(module, name)
                        if isinstance(obj, type) and name.startswith('Test'):
                            test_classes.append(obj)
                except Exception as e:
                    logging.warning(f"Failed to load {file}: {e}")

        return test_classes


# =============================================================================
# TEST REPORTER
# =============================================================================

class TestReporter(ABC):
    """Base test reporter."""

    @abstractmethod
    def report_result(self, result: TestResult) -> None:
        """Report single test result."""
        pass

    @abstractmethod
    def report_suite(self, result: TestSuiteResult) -> None:
        """Report suite result."""
        pass

    @abstractmethod
    def report_summary(self, results: List[TestSuiteResult]) -> None:
        """Report overall summary."""
        pass


class ConsoleReporter(TestReporter):
    """Console test reporter with colors."""

    COLORS = {
        TestStatus.PASSED: '\033[92m',
        TestStatus.FAILED: '\033[91m',
        TestStatus.SKIPPED: '\033[93m',
        TestStatus.ERROR: '\033[91m',
        TestStatus.RUNNING: '\033[94m',
    }
    END = '\033[0m'

    def _status_symbol(self, status: TestStatus) -> str:
        symbols = {
            TestStatus.PASSED: '✓',
            TestStatus.FAILED: '✗',
            TestStatus.SKIPPED: '○',
            TestStatus.ERROR: '!',
        }
        return symbols.get(status, '?')

    def report_result(self, result: TestResult) -> None:
        color = self.COLORS.get(result.status, '')
        symbol = self._status_symbol(result.status)

        print(f"  {color}{symbol}{self.END} {result.name} ({result.duration_ms:.1f}ms)")

        if result.error:
            print(f"      Error: {result.error}")

    def report_suite(self, result: TestSuiteResult) -> None:
        print(f"\n{result.name}")
        print("-" * 60)

        for test_result in result.results:
            self.report_result(test_result)

        print(f"\n  Total: {result.total} | "
              f"{self.COLORS[TestStatus.PASSED]}Passed: {result.passed}{self.END} | "
              f"{self.COLORS[TestStatus.FAILED]}Failed: {result.failed}{self.END} | "
              f"{self.COLORS[TestStatus.SKIPPED]}Skipped: {result.skipped}{self.END}")

    def report_summary(self, results: List[TestSuiteResult]) -> None:
        total = sum(r.total for r in results)
        passed = sum(r.passed for r in results)
        failed = sum(r.failed for r in results)
        skipped = sum(r.skipped for r in results)
        duration = sum(r.duration_ms for r in results)

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"\nSuites: {len(results)}")
        print(f"Tests:  {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)" if total > 0 else "Passed: 0")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Duration: {duration:.1f}ms")

        if failed > 0:
            print(f"\n{self.COLORS[TestStatus.FAILED]}TESTS FAILED{self.END}")
        else:
            print(f"\n{self.COLORS[TestStatus.PASSED]}ALL TESTS PASSED{self.END}")


class JSONReporter(TestReporter):
    """JSON test reporter."""

    def __init__(self, output_file: str = "test-results.json"):
        self.output_file = output_file
        self.all_results: List[Dict] = []

    def report_result(self, result: TestResult) -> None:
        pass  # Collected at suite level

    def report_suite(self, result: TestSuiteResult) -> None:
        self.all_results.append(result.to_dict())

    def report_summary(self, results: List[TestSuiteResult]) -> None:
        output = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": sum(r.total for r in results),
                "passed": sum(r.passed for r in results),
                "failed": sum(r.failed for r in results),
                "skipped": sum(r.skipped for r in results),
                "duration_ms": sum(r.duration_ms for r in results)
            },
            "suites": [r.to_dict() for r in results]
        }

        with open(self.output_file, 'w') as f:
            json.dump(output, f, indent=2)


class JUnitReporter(TestReporter):
    """JUnit XML reporter for CI/CD integration."""

    def __init__(self, output_file: str = "junit.xml"):
        self.output_file = output_file
        self.suites: List[TestSuiteResult] = []

    def report_result(self, result: TestResult) -> None:
        pass

    def report_suite(self, result: TestSuiteResult) -> None:
        self.suites.append(result)

    def report_summary(self, results: List[TestSuiteResult]) -> None:
        import xml.etree.ElementTree as ET

        root = ET.Element('testsuites')

        for suite in results:
            suite_elem = ET.SubElement(root, 'testsuite', {
                'name': suite.name,
                'tests': str(suite.total),
                'failures': str(suite.failed),
                'errors': str(suite.errors),
                'skipped': str(suite.skipped),
                'time': str(suite.duration_ms / 1000)
            })

            for test in suite.results:
                test_elem = ET.SubElement(suite_elem, 'testcase', {
                    'name': test.name,
                    'time': str(test.duration_ms / 1000)
                })

                if test.status == TestStatus.FAILED:
                    failure = ET.SubElement(test_elem, 'failure', {
                        'message': test.error or ''
                    })
                    if test.traceback:
                        failure.text = test.traceback

                elif test.status == TestStatus.ERROR:
                    error = ET.SubElement(test_elem, 'error', {
                        'message': test.error or ''
                    })
                    if test.traceback:
                        error.text = test.traceback

                elif test.status == TestStatus.SKIPPED:
                    ET.SubElement(test_elem, 'skipped')

        tree = ET.ElementTree(root)
        tree.write(self.output_file, encoding='unicode', xml_declaration=True)


# =============================================================================
# PERFORMANCE BENCHMARKS
# =============================================================================

@dataclass
class BenchmarkResult:
    """Benchmark result."""
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    ops_per_second: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time_ms": round(self.total_time_ms, 3),
            "avg_time_ms": round(self.avg_time_ms, 3),
            "min_time_ms": round(self.min_time_ms, 3),
            "max_time_ms": round(self.max_time_ms, 3),
            "ops_per_second": round(self.ops_per_second, 2)
        }


class Benchmark:
    """Performance benchmarking utility."""

    @staticmethod
    async def run_async(
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10
    ) -> BenchmarkResult:
        """Run async benchmark."""
        # Warmup
        for _ in range(warmup):
            await func()

        # Benchmark
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await func()
            times.append((time.perf_counter() - start) * 1000)

        total = sum(times)
        avg = total / iterations
        ops = 1000 / avg if avg > 0 else 0

        return BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=avg,
            min_time_ms=min(times),
            max_time_ms=max(times),
            ops_per_second=ops
        )

    @staticmethod
    def run_sync(
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10
    ) -> BenchmarkResult:
        """Run sync benchmark."""
        # Warmup
        for _ in range(warmup):
            func()

        # Benchmark
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            times.append((time.perf_counter() - start) * 1000)

        total = sum(times)
        avg = total / iterations
        ops = 1000 / avg if avg > 0 else 0

        return BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=avg,
            min_time_ms=min(times),
            max_time_ms=max(times),
            ops_per_second=ops
        )


# =============================================================================
# EXAMPLE TESTS
# =============================================================================

class TestAssertions:
    """Test the assertion helpers."""

    @test
    def test_assertEqual_pass(self):
        Assertions.assertEqual(1 + 1, 2)
        Assertions.assertEqual("hello", "hello")
        Assertions.assertEqual([1, 2, 3], [1, 2, 3])

    @test
    def test_assertTrue(self):
        Assertions.assertTrue(True)
        Assertions.assertTrue(1)
        Assertions.assertTrue("non-empty")

    @test
    def test_assertIn(self):
        Assertions.assertIn(2, [1, 2, 3])
        Assertions.assertIn("a", "abc")
        Assertions.assertIn("key", {"key": "value"})

    @test
    def test_assertIsInstance(self):
        Assertions.assertIsInstance("hello", str)
        Assertions.assertIsInstance(123, int)
        Assertions.assertIsInstance([1, 2], list)


class TestMockProviders:
    """Test the mock providers."""

    @test
    async def test_mock_llm_provider(self):
        provider = MockLLMProvider(responses=["Hello!", "World!"])

        result1 = await provider.generate("Test prompt 1")
        Assertions.assertEqual(result1, "Hello!")
        Assertions.assertEqual(provider.call_count, 1)

        result2 = await provider.generate("Test prompt 2")
        Assertions.assertEqual(result2, "World!")
        Assertions.assertEqual(provider.call_count, 2)

    @test
    async def test_mock_memory_provider(self):
        memory = MockMemoryProvider()

        await memory.store("key1", "value1")
        result = await memory.retrieve("key1")
        Assertions.assertEqual(result, "value1")

        missing = await memory.retrieve("nonexistent")
        Assertions.assertNone(missing)


class TestBenchmarks:
    """Test performance benchmarks."""

    @test(test_type=TestType.PERFORMANCE)
    async def test_benchmark_async(self):
        async def simple_operation():
            await asyncio.sleep(0.001)

        result = await Benchmark.run_async(
            "simple_async",
            simple_operation,
            iterations=10,
            warmup=2
        )

        Assertions.assertGreater(result.iterations, 0)
        Assertions.assertGreater(result.ops_per_second, 0)


# =============================================================================
# CLI
# =============================================================================

async def run_tests(
    test_dir: str = "tests",
    pattern: str = "test_*.py",
    reporters: List[TestReporter] = None
) -> int:
    """Run all tests and return exit code."""
    runner = TestRunner()
    reporters = reporters or [ConsoleReporter()]

    # Discover tests
    test_classes = runner.discover_tests(test_dir)

    if not test_classes:
        print(f"No tests found in {test_dir}")
        return 0

    # Run all suites
    results: List[TestSuiteResult] = []

    for test_class in test_classes:
        suite_result = await runner.run_suite(test_class)
        results.append(suite_result)

        for reporter in reporters:
            reporter.report_suite(suite_result)

    # Report summary
    for reporter in reporters:
        reporter.report_summary(results)

    # Return exit code
    failed = sum(r.failed + r.errors for r in results)
    return 1 if failed > 0 else 0


def main():
    """Run test CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="BAEL Test Runner")
    parser.add_argument("--dir", default="tests", help="Test directory")
    parser.add_argument("--pattern", default="test_*.py", help="Test file pattern")
    parser.add_argument("--json", help="Output JSON report to file")
    parser.add_argument("--junit", help="Output JUnit XML to file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    reporters = [ConsoleReporter()]

    if args.json:
        reporters.append(JSONReporter(args.json))

    if args.junit:
        reporters.append(JUnitReporter(args.junit))

    # Run example tests if no test dir exists
    if not Path(args.dir).exists():
        print("Running built-in example tests...")
        asyncio.run(run_example_tests(reporters))
        return

    exit_code = asyncio.run(run_tests(args.dir, args.pattern, reporters))
    sys.exit(exit_code)


async def run_example_tests(reporters: List[TestReporter] = None):
    """Run the built-in example tests."""
    runner = TestRunner()
    reporters = reporters or [ConsoleReporter()]

    test_classes = [TestAssertions, TestMockProviders, TestBenchmarks]
    results = []

    for test_class in test_classes:
        suite_result = await runner.run_suite(test_class)
        results.append(suite_result)

        for reporter in reporters:
            reporter.report_suite(suite_result)

    for reporter in reporters:
        reporter.report_summary(results)


if __name__ == "__main__":
    main()
