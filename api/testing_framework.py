"""
Comprehensive Testing & Quality Framework for BAEL

Provides unit tests, integration tests, performance tests, security tests,
load tests, chaos engineering, and automated testing pipelines.
"""

import asyncio
import json
import logging
import random
import sys
import time
import unittest
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestType(Enum):
    """Test classification"""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    LOAD = "load"
    CHAOS = "chaos"
    END_TO_END = "e2e"


class TestSeverity(Enum):
    """Test severity levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class TestResult:
    """Test execution result"""
    test_name: str
    test_type: TestType
    passed: bool
    duration: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: TestSeverity = TestSeverity.MEDIUM
    coverage: float = 0.0
    assertions: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.test_name,
            "type": self.test_type.value,
            "passed": self.passed,
            "duration": round(self.duration, 4),
            "error": self.error_message,
            "severity": self.severity.name,
            "coverage": round(self.coverage, 2),
            "assertions": self.assertions,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class TestSuite:
    """Test suite configuration"""
    name: str
    tests: List[Callable] = field(default_factory=list)
    setup_func: Optional[Callable] = None
    teardown_func: Optional[Callable] = None
    timeout: int = 30
    retry_count: int = 0
    parallel: bool = False
    max_workers: int = 4


class BaseTest(ABC):
    """Base test class"""

    def __init__(self, test_name: str, test_type: TestType):
        self.test_name = test_name
        self.test_type = test_type
        self.assertions = 0
        self.start_time = None
        self.end_time = None

    @abstractmethod
    async def run(self) -> TestResult:
        """Run the test"""
        pass

    def assert_true(self, condition: bool, message: str = ""):
        """Assert condition is true"""
        self.assertions += 1
        assert condition, message

    def assert_equal(self, actual: Any, expected: Any, message: str = ""):
        """Assert equality"""
        self.assertions += 1
        assert actual == expected, message or f"Expected {expected}, got {actual}"

    def assert_not_equal(self, actual: Any, unexpected: Any, message: str = ""):
        """Assert not equal"""
        self.assertions += 1
        assert actual != unexpected, message

    def assert_none(self, value: Any, message: str = ""):
        """Assert value is None"""
        self.assertions += 1
        assert value is None, message

    def assert_not_none(self, value: Any, message: str = ""):
        """Assert value is not None"""
        self.assertions += 1
        assert value is not None, message

    def assert_in(self, item: Any, container: Any, message: str = ""):
        """Assert item in container"""
        self.assertions += 1
        assert item in container, message

    def assert_raises(self, exception_type, callable_func, *args, **kwargs):
        """Assert function raises exception"""
        self.assertions += 1
        try:
            callable_func(*args, **kwargs)
            raise AssertionError(f"Expected {exception_type.__name__} to be raised")
        except exception_type:
            pass


class UnitTest(BaseTest):
    """Unit test for individual components"""

    def __init__(self, test_name: str, test_func: Callable):
        super().__init__(test_name, TestType.UNIT)
        self.test_func = test_func

    async def run(self) -> TestResult:
        """Run unit test"""
        self.start_time = time.time()
        try:
            await self.test_func(self)
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.UNIT,
                passed=True,
                duration=self.end_time - self.start_time,
                assertions=self.assertions,
                severity=TestSeverity.HIGH
            )
        except Exception as e:
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.UNIT,
                passed=False,
                duration=self.end_time - self.start_time,
                error_message=str(e),
                stack_trace=str(sys.exc_info()),
                assertions=self.assertions,
                severity=TestSeverity.CRITICAL
            )


class IntegrationTest(BaseTest):
    """Integration test for multiple components"""

    def __init__(self, test_name: str, test_func: Callable, components: List[str]):
        super().__init__(test_name, TestType.INTEGRATION)
        self.test_func = test_func
        self.components = components

    async def run(self) -> TestResult:
        """Run integration test"""
        self.start_time = time.time()
        try:
            await self.test_func(self)
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.INTEGRATION,
                passed=True,
                duration=self.end_time - self.start_time,
                assertions=self.assertions,
                severity=TestSeverity.HIGH,
                metadata={"components": self.components}
            )
        except Exception as e:
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.INTEGRATION,
                passed=False,
                duration=self.end_time - self.start_time,
                error_message=str(e),
                stack_trace=str(sys.exc_info()),
                assertions=self.assertions,
                severity=TestSeverity.CRITICAL,
                metadata={"components": self.components}
            )


class PerformanceTest(BaseTest):
    """Performance test measuring speed and efficiency"""

    def __init__(self, test_name: str, test_func: Callable, target_duration: float):
        super().__init__(test_name, TestType.PERFORMANCE)
        self.test_func = test_func
        self.target_duration = target_duration
        self.metrics: Dict[str, float] = {}

    async def run(self) -> TestResult:
        """Run performance test"""
        self.start_time = time.time()
        try:
            await self.test_func(self)
            self.end_time = time.time()
            duration = self.end_time - self.start_time

            passed = duration <= self.target_duration
            self.assert_true(passed,
                f"Performance target not met: {duration:.3f}s vs {self.target_duration:.3f}s")

            return TestResult(
                test_name=self.test_name,
                test_type=TestType.PERFORMANCE,
                passed=passed,
                duration=duration,
                assertions=self.assertions,
                severity=TestSeverity.MEDIUM,
                metadata={"target": self.target_duration, "actual": duration, **self.metrics}
            )
        except Exception as e:
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.PERFORMANCE,
                passed=False,
                duration=self.end_time - self.start_time,
                error_message=str(e),
                assertions=self.assertions,
                severity=TestSeverity.HIGH
            )


class SecurityTest(BaseTest):
    """Security vulnerability testing"""

    def __init__(self, test_name: str, test_func: Callable, vulnerability_type: str):
        super().__init__(test_name, TestType.SECURITY)
        self.test_func = test_func
        self.vulnerability_type = vulnerability_type

    async def run(self) -> TestResult:
        """Run security test"""
        self.start_time = time.time()
        try:
            await self.test_func(self)
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.SECURITY,
                passed=True,
                duration=self.end_time - self.start_time,
                assertions=self.assertions,
                severity=TestSeverity.CRITICAL,
                metadata={"vulnerability_type": self.vulnerability_type}
            )
        except Exception as e:
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.SECURITY,
                passed=False,
                duration=self.end_time - self.start_time,
                error_message=str(e),
                assertions=self.assertions,
                severity=TestSeverity.CRITICAL,
                metadata={"vulnerability_type": self.vulnerability_type}
            )


class LoadTest(BaseTest):
    """Load and stress testing"""

    def __init__(self, test_name: str, test_func: Callable, num_requests: int,
                 concurrency: int = 10):
        super().__init__(test_name, TestType.LOAD)
        self.test_func = test_func
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.response_times: List[float] = []
        self.errors: int = 0

    async def run(self) -> TestResult:
        """Run load test"""
        self.start_time = time.time()
        try:
            async def single_request():
                req_start = time.time()
                try:
                    await self.test_func()
                    self.response_times.append(time.time() - req_start)
                except:
                    self.errors += 1

            # Create tasks with controlled concurrency
            tasks = []
            for _ in range(self.num_requests):
                tasks.append(single_request())
                if len(tasks) >= self.concurrency:
                    await asyncio.gather(*tasks)
                    tasks = []

            if tasks:
                await asyncio.gather(*tasks)

            self.end_time = time.time()

            if self.response_times:
                avg_time = sum(self.response_times) / len(self.response_times)
                max_time = max(self.response_times)
                p95_time = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
            else:
                avg_time = max_time = p95_time = 0

            success_rate = (self.num_requests - self.errors) / self.num_requests * 100
            passed = success_rate >= 95

            return TestResult(
                test_name=self.test_name,
                test_type=TestType.LOAD,
                passed=passed,
                duration=self.end_time - self.start_time,
                severity=TestSeverity.MEDIUM,
                metadata={
                    "num_requests": self.num_requests,
                    "concurrency": self.concurrency,
                    "errors": self.errors,
                    "success_rate": round(success_rate, 2),
                    "avg_response_time": round(avg_time, 4),
                    "max_response_time": round(max_time, 4),
                    "p95_response_time": round(p95_time, 4)
                }
            )
        except Exception as e:
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.LOAD,
                passed=False,
                duration=self.end_time - self.start_time,
                error_message=str(e),
                severity=TestSeverity.HIGH
            )


class ChaosTest(BaseTest):
    """Chaos engineering - system resilience testing"""

    def __init__(self, test_name: str, test_func: Callable, failure_injection: str):
        super().__init__(test_name, TestType.CHAOS)
        self.test_func = test_func
        self.failure_injection = failure_injection
        self.recovery_time = 0

    async def run(self) -> TestResult:
        """Run chaos test"""
        self.start_time = time.time()
        try:
            await self.test_func(self)
            self.end_time = time.time()
            self.recovery_time = self.end_time - self.start_time

            return TestResult(
                test_name=self.test_name,
                test_type=TestType.CHAOS,
                passed=True,
                duration=self.recovery_time,
                assertions=self.assertions,
                severity=TestSeverity.MEDIUM,
                metadata={
                    "failure_injection": self.failure_injection,
                    "recovery_time": round(self.recovery_time, 3)
                }
            )
        except Exception as e:
            self.end_time = time.time()
            return TestResult(
                test_name=self.test_name,
                test_type=TestType.CHAOS,
                passed=False,
                duration=self.end_time - self.start_time,
                error_message=str(e),
                assertions=self.assertions,
                severity=TestSeverity.HIGH,
                metadata={"failure_injection": self.failure_injection}
            )


class TestRunner:
    """Test execution engine"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.results: List[TestResult] = []
        self.suites: Dict[str, TestSuite] = {}

    def register_suite(self, suite: TestSuite):
        """Register a test suite"""
        self.suites[suite.name] = suite

    async def run_test(self, test: BaseTest) -> TestResult:
        """Run single test"""
        logger.info(f"Running {test.test_type.value} test: {test.test_name}")
        result = await test.run()
        self.results.append(result)
        status = "✓ PASSED" if result.passed else "✗ FAILED"
        logger.info(f"{status} - {test.test_name} ({result.duration:.3f}s)")
        return result

    async def run_suite(self, suite_name: str) -> List[TestResult]:
        """Run a test suite"""
        suite = self.suites.get(suite_name)
        if not suite:
            logger.error(f"Suite not found: {suite_name}")
            return []

        logger.info(f"Running test suite: {suite_name}")

        if suite.setup_func:
            await suite.setup_func()

        results = []
        if suite.parallel:
            # Run tests in parallel
            tasks = [self.run_test(test) for test in suite.tests]
            results = await asyncio.gather(*tasks)
        else:
            # Run tests sequentially
            for test in suite.tests:
                result = await self.run_test(test)
                results.append(result)

        if suite.teardown_func:
            await suite.teardown_func()

        return results

    async def run_all_suites(self) -> Dict[str, List[TestResult]]:
        """Run all registered test suites"""
        suite_results = {}
        for suite_name in self.suites:
            suite_results[suite_name] = await self.run_suite(suite_name)
        return suite_results

    def get_coverage_report(self) -> Dict[str, Any]:
        """Generate coverage report"""
        if not self.results:
            return {}

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        by_type = {}
        for result in self.results:
            test_type = result.test_type.value
            if test_type not in by_type:
                by_type[test_type] = {"passed": 0, "failed": 0, "duration": 0}

            if result.passed:
                by_type[test_type]["passed"] += 1
            else:
                by_type[test_type]["failed"] += 1
            by_type[test_type]["duration"] += result.duration

        total_duration = sum(r.duration for r in self.results)

        return {
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / len(self.results) * 100, 2) if self.results else 0,
            "total_duration": round(total_duration, 3),
            "by_type": by_type,
            "by_severity": {
                "CRITICAL": sum(1 for r in self.results if r.severity == TestSeverity.CRITICAL),
                "HIGH": sum(1 for r in self.results if r.severity == TestSeverity.HIGH),
                "MEDIUM": sum(1 for r in self.results if r.severity == TestSeverity.MEDIUM),
                "LOW": sum(1 for r in self.results if r.severity == TestSeverity.LOW)
            },
            "assertions": sum(r.assertions for r in self.results),
            "failures": [r.to_dict() for r in self.results if not r.passed]
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        perf_tests = [r for r in self.results if r.test_type == TestType.PERFORMANCE]
        if not perf_tests:
            return {}

        return {
            "performance_tests": len(perf_tests),
            "passed": sum(1 for r in perf_tests if r.passed),
            "failed": sum(1 for r in perf_tests if not r.passed),
            "tests": [r.to_dict() for r in perf_tests]
        }

    def get_security_report(self) -> Dict[str, Any]:
        """Generate security audit report"""
        sec_tests = [r for r in self.results if r.test_type == TestType.SECURITY]
        if not sec_tests:
            return {}

        vulnerabilities = [r for r in sec_tests if not r.passed]

        return {
            "security_tests": len(sec_tests),
            "passed": sum(1 for r in sec_tests if r.passed),
            "vulnerabilities_found": len(vulnerabilities),
            "vulnerabilities": [r.to_dict() for r in vulnerabilities]
        }

    def export_results(self, filename: str):
        """Export results to JSON"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_coverage_report(),
            "performance": self.get_performance_report(),
            "security": self.get_security_report(),
            "all_results": [r.to_dict() for r in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Results exported to {filename}")


# Global test runner instance
_test_runner = TestRunner()


def get_test_runner() -> TestRunner:
    """Get global test runner"""
    return _test_runner


# Test utilities
class TestUtils:
    """Utility functions for testing"""

    @staticmethod
    def create_mock_data(data_type: str, count: int = 10) -> List[Dict[str, Any]]:
        """Create mock test data"""
        data = []
        for i in range(count):
            if data_type == "user":
                data.append({
                    "id": i,
                    "name": f"User{i}",
                    "email": f"user{i}@example.com",
                    "created_at": datetime.now().isoformat()
                })
            elif data_type == "task":
                data.append({
                    "id": i,
                    "title": f"Task{i}",
                    "status": random.choice(["pending", "in_progress", "completed"]),
                    "priority": random.choice(["low", "medium", "high"])
                })
            elif data_type == "metric":
                data.append({
                    "id": i,
                    "name": f"metric_{i}",
                    "value": random.uniform(0, 100),
                    "timestamp": datetime.now().isoformat()
                })
        return data

    @staticmethod
    def measure_memory_usage(func: Callable) -> Tuple[Any, int]:
        """Measure memory usage of function"""
        import tracemalloc
        tracemalloc.start()
        result = func()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return result, peak


if __name__ == "__main__":
    logger.info("Testing Framework initialized")
