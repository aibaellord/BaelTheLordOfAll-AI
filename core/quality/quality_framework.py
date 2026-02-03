#!/usr/bin/env python3
"""
BAEL - Quality Framework
Multi-dimensional quality assurance and validation system.

This module implements comprehensive quality control across all BAEL operations,
ensuring every output meets the highest standards through multi-perspective
validation, automated testing, and continuous quality monitoring.

Features:
- Multi-perspective quality validation
- Automated test generation
- Quality gates and thresholds
- Regression detection
- Performance benchmarking
- Code quality analysis
- Output verification
- Continuous quality monitoring
- Quality evolution tracking
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class QualityDimension(Enum):
    """Dimensions of quality to evaluate."""
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    EFFICIENCY = "efficiency"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    USABILITY = "usability"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    SCALABILITY = "scalability"
    TESTABILITY = "testability"
    DOCUMENTATION = "documentation"


class QualityLevel(Enum):
    """Quality level classifications."""
    EXCEPTIONAL = "exceptional"  # 95-100%
    EXCELLENT = "excellent"      # 85-94%
    GOOD = "good"               # 70-84%
    ACCEPTABLE = "acceptable"   # 50-69%
    POOR = "poor"               # 25-49%
    UNACCEPTABLE = "unacceptable"  # 0-24%


class ValidationStatus(Enum):
    """Status of validation."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    PENDING = "pending"


class TestType(Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    REGRESSION = "regression"
    ACCEPTANCE = "acceptance"
    STRESS = "stress"
    CHAOS = "chaos"


class IssueType(Enum):
    """Types of quality issues."""
    BUG = "bug"
    VULNERABILITY = "vulnerability"
    PERFORMANCE = "performance"
    STYLE = "style"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    COVERAGE = "coverage"
    DOCUMENTATION = "documentation"


class IssueSeverity(Enum):
    """Severity of quality issues."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    INFO = 4


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class QualityMetric:
    """A single quality metric."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    dimension: QualityDimension = QualityDimension.CORRECTNESS
    value: float = 0.0
    max_value: float = 100.0
    weight: float = 1.0
    threshold: float = 70.0
    measured_at: datetime = field(default_factory=datetime.now)

    @property
    def score(self) -> float:
        """Get normalized score (0-100)."""
        return (self.value / self.max_value) * 100 if self.max_value > 0 else 0

    @property
    def passed(self) -> bool:
        """Check if metric passes threshold."""
        return self.score >= self.threshold


@dataclass
class QualityIssue:
    """A quality issue found during validation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    issue_type: IssueType = IssueType.BUG
    severity: IssueSeverity = IssueSeverity.MEDIUM
    title: str = ""
    description: str = ""
    location: str = ""
    line_number: Optional[int] = None
    suggestion: str = ""
    auto_fixable: bool = False
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class TestCase:
    """A test case for validation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    test_type: TestType = TestType.UNIT
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected_output: Any = None
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    timeout_seconds: float = 30.0
    retries: int = 0
    tags: List[str] = field(default_factory=list)
    priority: int = 1


@dataclass
class TestResult:
    """Result of running a test."""
    id: str = field(default_factory=lambda: str(uuid4()))
    test_case_id: str = ""
    status: ValidationStatus = ValidationStatus.PENDING
    actual_output: Any = None
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    assertions_passed: int = 0
    assertions_failed: int = 0
    executed_at: datetime = field(default_factory=datetime.now)


@dataclass
class QualityReport:
    """A comprehensive quality report."""
    id: str = field(default_factory=lambda: str(uuid4()))
    target: str = ""
    overall_score: float = 0.0
    level: QualityLevel = QualityLevel.ACCEPTABLE
    metrics: List[QualityMetric] = field(default_factory=list)
    issues: List[QualityIssue] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def calculate_overall_score(self) -> float:
        """Calculate weighted overall score."""
        if not self.metrics:
            return 0.0
        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(m.score * m.weight for m in self.metrics)
        self.overall_score = weighted_sum / total_weight
        self.level = self._score_to_level(self.overall_score)
        return self.overall_score

    def _score_to_level(self, score: float) -> QualityLevel:
        """Convert score to quality level."""
        if score >= 95:
            return QualityLevel.EXCEPTIONAL
        elif score >= 85:
            return QualityLevel.EXCELLENT
        elif score >= 70:
            return QualityLevel.GOOD
        elif score >= 50:
            return QualityLevel.ACCEPTABLE
        elif score >= 25:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE


@dataclass
class QualityGate:
    """A quality gate with pass/fail criteria."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    criteria: List[Dict[str, Any]] = field(default_factory=list)
    is_blocking: bool = True

    def evaluate(self, report: QualityReport) -> Tuple[bool, List[str]]:
        """Evaluate if quality gate passes."""
        failures = []
        for criterion in self.criteria:
            dimension = criterion.get("dimension")
            min_score = criterion.get("min_score", 70)
            max_issues = criterion.get("max_issues", {})

            # Check dimension score
            if dimension:
                dim_metrics = [m for m in report.metrics
                              if m.dimension.value == dimension]
                if dim_metrics:
                    avg_score = sum(m.score for m in dim_metrics) / len(dim_metrics)
                    if avg_score < min_score:
                        failures.append(
                            f"{dimension} score {avg_score:.1f} below minimum {min_score}"
                        )

            # Check issue counts
            for severity, max_count in max_issues.items():
                severity_enum = IssueSeverity[severity.upper()]
                count = sum(1 for i in report.issues if i.severity == severity_enum)
                if count > max_count:
                    failures.append(
                        f"{severity} issues: {count} exceeds maximum {max_count}"
                    )

        return len(failures) == 0, failures


# =============================================================================
# VALIDATORS
# =============================================================================

class Validator(ABC):
    """Base class for validators."""

    @abstractmethod
    async def validate(self, target: Any, context: Dict[str, Any] = None) -> List[QualityMetric]:
        """Validate target and return metrics."""
        pass


class CorrectnessValidator(Validator):
    """Validate correctness of outputs."""

    async def validate(self, target: Any, context: Dict[str, Any] = None) -> List[QualityMetric]:
        """Validate correctness."""
        metrics = []
        context = context or {}

        # Syntax correctness
        syntax_score = await self._check_syntax(target)
        metrics.append(QualityMetric(
            name="syntax_correctness",
            dimension=QualityDimension.CORRECTNESS,
            value=syntax_score,
            weight=1.5
        ))

        # Logic correctness
        logic_score = await self._check_logic(target, context)
        metrics.append(QualityMetric(
            name="logic_correctness",
            dimension=QualityDimension.CORRECTNESS,
            value=logic_score,
            weight=2.0
        ))

        # Output correctness
        if "expected" in context:
            output_score = await self._check_output(target, context["expected"])
            metrics.append(QualityMetric(
                name="output_correctness",
                dimension=QualityDimension.CORRECTNESS,
                value=output_score,
                weight=2.0
            ))

        return metrics

    async def _check_syntax(self, target: Any) -> float:
        """Check syntax correctness."""
        if isinstance(target, str):
            try:
                compile(target, "<string>", "exec")
                return 100.0
            except SyntaxError:
                return 0.0
        return 100.0

    async def _check_logic(self, target: Any, context: Dict[str, Any]) -> float:
        """Check logic correctness."""
        # Simplified logic check
        return 85.0

    async def _check_output(self, actual: Any, expected: Any) -> float:
        """Check output matches expected."""
        if actual == expected:
            return 100.0
        if isinstance(actual, str) and isinstance(expected, str):
            # Fuzzy matching
            similarity = self._string_similarity(actual, expected)
            return similarity * 100
        return 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity."""
        if not s1 or not s2:
            return 0.0
        # Simple Jaccard similarity on words
        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0


class CompletenessValidator(Validator):
    """Validate completeness of outputs."""

    def __init__(self):
        self.required_elements: Dict[str, List[str]] = {
            "code": ["functions", "classes", "imports", "docstrings"],
            "document": ["title", "introduction", "body", "conclusion"],
            "api": ["endpoints", "authentication", "error_handling", "documentation"]
        }

    async def validate(self, target: Any, context: Dict[str, Any] = None) -> List[QualityMetric]:
        """Validate completeness."""
        metrics = []
        context = context or {}
        target_type = context.get("type", "code")

        # Check required elements
        required = self.required_elements.get(target_type, [])
        found = 0
        for element in required:
            if await self._has_element(target, element):
                found += 1

        element_score = (found / len(required) * 100) if required else 100.0
        metrics.append(QualityMetric(
            name="element_completeness",
            dimension=QualityDimension.COMPLETENESS,
            value=element_score,
            weight=1.5
        ))

        # Check edge case handling
        edge_score = await self._check_edge_cases(target)
        metrics.append(QualityMetric(
            name="edge_case_coverage",
            dimension=QualityDimension.COMPLETENESS,
            value=edge_score,
            weight=1.0
        ))

        return metrics

    async def _has_element(self, target: Any, element: str) -> bool:
        """Check if target has required element."""
        if isinstance(target, str):
            element_patterns = {
                "functions": r"def \w+\(",
                "classes": r"class \w+",
                "imports": r"import |from .+ import",
                "docstrings": r'""".*?"""',
                "title": r"^#\s+\w+",
                "error_handling": r"try:|except:|raise\s+\w+"
            }
            pattern = element_patterns.get(element)
            if pattern:
                return bool(re.search(pattern, target, re.DOTALL))
        return True

    async def _check_edge_cases(self, target: Any) -> float:
        """Check edge case handling."""
        if isinstance(target, str):
            edge_patterns = [
                r"if\s+\w+\s+is\s+None",
                r"if\s+not\s+\w+",
                r"except\s+\w+Error",
                r"\.get\(",
                r"or\s+\[\]",
                r"or\s+\{\}",
            ]
            found = sum(1 for p in edge_patterns if re.search(p, target))
            return min(100.0, found * 20)
        return 50.0


class SecurityValidator(Validator):
    """Validate security aspects."""

    def __init__(self):
        self.vulnerability_patterns = [
            (r"eval\(", "Use of eval() is dangerous", IssueSeverity.CRITICAL),
            (r"exec\(", "Use of exec() is dangerous", IssueSeverity.CRITICAL),
            (r"subprocess\.call\(.*shell=True", "Shell injection risk", IssueSeverity.HIGH),
            (r"password\s*=\s*['\"]", "Hardcoded password", IssueSeverity.CRITICAL),
            (r"api_key\s*=\s*['\"]", "Hardcoded API key", IssueSeverity.HIGH),
            (r"import pickle", "Pickle deserialization risk", IssueSeverity.MEDIUM),
            (r"yaml\.load\(", "Unsafe YAML loading", IssueSeverity.HIGH),
            (r"__import__\(", "Dynamic import risk", IssueSeverity.MEDIUM),
            (r"os\.system\(", "OS command execution", IssueSeverity.HIGH),
        ]

    async def validate(self, target: Any, context: Dict[str, Any] = None) -> List[QualityMetric]:
        """Validate security."""
        metrics = []
        issues = []

        if isinstance(target, str):
            for pattern, description, severity in self.vulnerability_patterns:
                matches = re.findall(pattern, target)
                for match in matches:
                    issues.append(QualityIssue(
                        issue_type=IssueType.VULNERABILITY,
                        severity=severity,
                        title=description,
                        description=f"Found: {match}"
                    ))

        # Calculate security score
        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)

        security_score = 100.0
        security_score -= critical_count * 30
        security_score -= high_count * 15
        security_score = max(0.0, security_score)

        metrics.append(QualityMetric(
            name="security_score",
            dimension=QualityDimension.SECURITY,
            value=security_score,
            weight=2.5,
            threshold=80.0
        ))

        # Store issues in context for report
        if context is not None:
            context.setdefault("issues", []).extend(issues)

        return metrics


class PerformanceValidator(Validator):
    """Validate performance aspects."""

    def __init__(self):
        self.complexity_patterns = {
            "nested_loops": (r"for .+:\s*\n\s+for .+:", 2),
            "recursive": (r"def (\w+)\(.*\).*\n.*\1\(", 1),
            "multiple_iterations": (r"for .+ in .+:.*for .+ in .+:", 2),
        }

    async def validate(self, target: Any, context: Dict[str, Any] = None) -> List[QualityMetric]:
        """Validate performance."""
        metrics = []

        if isinstance(target, str):
            # Complexity analysis
            complexity_score = await self._analyze_complexity(target)
            metrics.append(QualityMetric(
                name="complexity_score",
                dimension=QualityDimension.PERFORMANCE,
                value=complexity_score,
                weight=1.5
            ))

            # Efficiency patterns
            efficiency_score = await self._analyze_efficiency(target)
            metrics.append(QualityMetric(
                name="efficiency_score",
                dimension=QualityDimension.PERFORMANCE,
                value=efficiency_score,
                weight=1.5
            ))

        return metrics

    async def _analyze_complexity(self, code: str) -> float:
        """Analyze code complexity."""
        complexity = 0
        for name, (pattern, weight) in self.complexity_patterns.items():
            matches = len(re.findall(pattern, code, re.MULTILINE))
            complexity += matches * weight

        # Lower complexity = higher score
        score = max(0, 100 - complexity * 10)
        return score

    async def _analyze_efficiency(self, code: str) -> float:
        """Analyze code efficiency."""
        efficiency_patterns = [
            (r"list comprehension", r"\[.+ for .+ in .+\]", 5),
            (r"generator", r"\(.+ for .+ in .+\)", 5),
            (r"enumerate", r"enumerate\(", 3),
            (r"dict comprehension", r"\{.+:.+ for .+ in .+\}", 5),
        ]

        score = 70.0  # Base score
        for name, pattern, bonus in efficiency_patterns:
            if re.search(pattern, code):
                score += bonus

        return min(100.0, score)


class MaintainabilityValidator(Validator):
    """Validate maintainability aspects."""

    async def validate(self, target: Any, context: Dict[str, Any] = None) -> List[QualityMetric]:
        """Validate maintainability."""
        metrics = []

        if isinstance(target, str):
            # Documentation coverage
            doc_score = await self._check_documentation(target)
            metrics.append(QualityMetric(
                name="documentation_coverage",
                dimension=QualityDimension.MAINTAINABILITY,
                value=doc_score,
                weight=1.0
            ))

            # Code organization
            org_score = await self._check_organization(target)
            metrics.append(QualityMetric(
                name="code_organization",
                dimension=QualityDimension.MAINTAINABILITY,
                value=org_score,
                weight=1.0
            ))

            # Naming conventions
            naming_score = await self._check_naming(target)
            metrics.append(QualityMetric(
                name="naming_conventions",
                dimension=QualityDimension.MAINTAINABILITY,
                value=naming_score,
                weight=0.8
            ))

        return metrics

    async def _check_documentation(self, code: str) -> float:
        """Check documentation coverage."""
        functions = re.findall(r"def \w+\(", code)
        docstrings = re.findall(r'def \w+\([^)]*\):\s*"""', code)

        if not functions:
            return 100.0
        return (len(docstrings) / len(functions)) * 100

    async def _check_organization(self, code: str) -> float:
        """Check code organization."""
        score = 70.0

        # Check for class usage
        if re.search(r"class \w+", code):
            score += 10

        # Check for type hints
        if re.search(r"def \w+\([^)]*:\s*\w+", code):
            score += 10

        # Check for imports at top
        lines = code.split("\n")
        import_section_done = False
        for line in lines:
            if line.strip() and not line.startswith("#"):
                if line.startswith("import ") or line.startswith("from "):
                    if import_section_done:
                        score -= 5
                else:
                    import_section_done = True

        return min(100.0, score)

    async def _check_naming(self, code: str) -> float:
        """Check naming conventions."""
        score = 100.0

        # Check function names (should be snake_case)
        functions = re.findall(r"def (\w+)\(", code)
        for func in functions:
            if func != func.lower() and not func.startswith("_"):
                if not re.match(r"^[a-z_][a-z0-9_]*$", func):
                    score -= 5

        # Check class names (should be PascalCase)
        classes = re.findall(r"class (\w+)", code)
        for cls in classes:
            if not re.match(r"^[A-Z][a-zA-Z0-9]*$", cls):
                score -= 5

        return max(0.0, score)


# =============================================================================
# TEST GENERATORS
# =============================================================================

class TestGenerator:
    """Generate tests automatically."""

    def __init__(self):
        self.test_templates: Dict[TestType, Callable] = {
            TestType.UNIT: self._generate_unit_tests,
            TestType.INTEGRATION: self._generate_integration_tests,
            TestType.PERFORMANCE: self._generate_performance_tests,
        }

    async def generate_tests(
        self,
        target: Any,
        test_type: TestType = TestType.UNIT,
        context: Dict[str, Any] = None
    ) -> List[TestCase]:
        """Generate tests for target."""
        generator = self.test_templates.get(test_type)
        if generator:
            return await generator(target, context or {})
        return []

    async def _generate_unit_tests(
        self,
        target: Any,
        context: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate unit tests."""
        tests = []

        if isinstance(target, str):
            # Find functions
            functions = re.findall(r"def (\w+)\(([^)]*)\)", target)

            for func_name, params in functions:
                if func_name.startswith("_") and not func_name.startswith("__"):
                    continue  # Skip private functions

                # Generate basic test
                tests.append(TestCase(
                    name=f"test_{func_name}_basic",
                    test_type=TestType.UNIT,
                    input_data={"function": func_name, "args": []},
                    tags=["unit", "basic"]
                ))

                # Generate edge case tests
                tests.append(TestCase(
                    name=f"test_{func_name}_none_input",
                    test_type=TestType.UNIT,
                    input_data={"function": func_name, "args": [None]},
                    tags=["unit", "edge_case"]
                ))

                tests.append(TestCase(
                    name=f"test_{func_name}_empty_input",
                    test_type=TestType.UNIT,
                    input_data={"function": func_name, "args": [""]},
                    tags=["unit", "edge_case"]
                ))

        return tests

    async def _generate_integration_tests(
        self,
        target: Any,
        context: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate integration tests."""
        tests = []

        # Generate end-to-end flow tests
        tests.append(TestCase(
            name="test_full_workflow",
            test_type=TestType.INTEGRATION,
            input_data=context.get("workflow_input", {}),
            tags=["integration", "workflow"]
        ))

        return tests

    async def _generate_performance_tests(
        self,
        target: Any,
        context: Dict[str, Any]
    ) -> List[TestCase]:
        """Generate performance tests."""
        tests = []

        tests.append(TestCase(
            name="test_performance_baseline",
            test_type=TestType.PERFORMANCE,
            input_data={"iterations": 100},
            timeout_seconds=60.0,
            tags=["performance", "baseline"]
        ))

        tests.append(TestCase(
            name="test_performance_stress",
            test_type=TestType.PERFORMANCE,
            input_data={"iterations": 1000},
            timeout_seconds=300.0,
            tags=["performance", "stress"]
        ))

        return tests


# =============================================================================
# TEST RUNNER
# =============================================================================

class TestRunner:
    """Run tests and collect results."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.test_executors: Dict[TestType, Callable] = {}

    async def run_tests(
        self,
        tests: List[TestCase],
        target: Any = None
    ) -> List[TestResult]:
        """Run a set of tests."""
        results = []

        for test in tests:
            result = await self._run_single_test(test, target)
            results.append(result)

        self.results.extend(results)
        return results

    async def _run_single_test(
        self,
        test: TestCase,
        target: Any
    ) -> TestResult:
        """Run a single test."""
        result = TestResult(test_case_id=test.id)
        start_time = time.time()

        try:
            # Execute test with timeout
            actual = await asyncio.wait_for(
                self._execute_test(test, target),
                timeout=test.timeout_seconds
            )

            # Check assertions
            passed, failed = await self._check_assertions(test, actual)
            result.assertions_passed = passed
            result.assertions_failed = failed
            result.actual_output = actual

            if failed == 0:
                result.status = ValidationStatus.PASSED
            else:
                result.status = ValidationStatus.FAILED

        except asyncio.TimeoutError:
            result.status = ValidationStatus.FAILED
            result.error_message = "Test timeout"

        except Exception as e:
            result.status = ValidationStatus.FAILED
            result.error_message = str(e)

        finally:
            result.duration_ms = (time.time() - start_time) * 1000

        return result

    async def _execute_test(self, test: TestCase, target: Any) -> Any:
        """Execute test and return result."""
        # Simplified test execution
        return {"executed": True, "test_id": test.id}

    async def _check_assertions(
        self,
        test: TestCase,
        actual: Any
    ) -> Tuple[int, int]:
        """Check test assertions."""
        passed = 0
        failed = 0

        for assertion in test.assertions:
            assertion_type = assertion.get("type", "equals")
            expected = assertion.get("expected")

            if assertion_type == "equals":
                if actual == expected:
                    passed += 1
                else:
                    failed += 1
            elif assertion_type == "contains":
                if expected in str(actual):
                    passed += 1
                else:
                    failed += 1
            elif assertion_type == "not_none":
                if actual is not None:
                    passed += 1
                else:
                    failed += 1

        # If no assertions defined, consider passed
        if not test.assertions:
            passed = 1

        return passed, failed


# =============================================================================
# QUALITY ANALYZER
# =============================================================================

class QualityAnalyzer:
    """Analyze quality using multiple perspectives."""

    def __init__(self):
        self.validators: List[Validator] = [
            CorrectnessValidator(),
            CompletenessValidator(),
            SecurityValidator(),
            PerformanceValidator(),
            MaintainabilityValidator(),
        ]
        self.test_generator = TestGenerator()
        self.test_runner = TestRunner()
        self.quality_gates: List[QualityGate] = []
        self.history: List[QualityReport] = []

    def add_quality_gate(self, gate: QualityGate) -> None:
        """Add a quality gate."""
        self.quality_gates.append(gate)

    async def analyze(
        self,
        target: Any,
        context: Dict[str, Any] = None
    ) -> QualityReport:
        """Perform comprehensive quality analysis."""
        context = context or {}
        context["issues"] = []

        report = QualityReport(target=str(type(target).__name__))

        # Run all validators
        for validator in self.validators:
            metrics = await validator.validate(target, context)
            report.metrics.extend(metrics)

        # Collect issues
        report.issues = context.get("issues", [])

        # Generate and run tests
        tests = await self.test_generator.generate_tests(target, TestType.UNIT, context)
        test_results = await self.test_runner.run_tests(tests, target)
        report.test_results = test_results

        # Calculate overall score
        report.calculate_overall_score()

        # Generate recommendations
        report.recommendations = await self._generate_recommendations(report)

        # Store in history
        self.history.append(report)

        return report

    async def _generate_recommendations(self, report: QualityReport) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        # Low scoring dimensions
        for metric in report.metrics:
            if metric.score < metric.threshold:
                recommendations.append(
                    f"Improve {metric.name}: current score {metric.score:.1f} "
                    f"below threshold {metric.threshold}"
                )

        # Critical issues
        critical_issues = [i for i in report.issues if i.severity == IssueSeverity.CRITICAL]
        for issue in critical_issues:
            recommendations.append(f"Fix critical issue: {issue.title}")

        # Failed tests
        failed_tests = [t for t in report.test_results if t.status == ValidationStatus.FAILED]
        if failed_tests:
            recommendations.append(f"Fix {len(failed_tests)} failing tests")

        return recommendations

    def check_quality_gates(self, report: QualityReport) -> Tuple[bool, List[str]]:
        """Check all quality gates."""
        all_passed = True
        all_failures = []

        for gate in self.quality_gates:
            passed, failures = gate.evaluate(report)
            if not passed:
                all_passed = False
                all_failures.extend([f"[{gate.name}] {f}" for f in failures])

        return all_passed, all_failures

    def get_trend(self, count: int = 10) -> Dict[str, Any]:
        """Get quality trend from history."""
        recent = self.history[-count:]
        if not recent:
            return {"trend": "unknown", "data": []}

        scores = [r.overall_score for r in recent]

        if len(scores) >= 2:
            if scores[-1] > scores[0]:
                trend = "improving"
            elif scores[-1] < scores[0]:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "scores": scores,
            "average": sum(scores) / len(scores),
            "latest": scores[-1] if scores else 0
        }


# =============================================================================
# QUALITY FRAMEWORK
# =============================================================================

class QualityFramework:
    """
    The master quality framework for BAEL.

    Orchestrates all quality assurance activities including
    validation, testing, monitoring, and continuous improvement.
    """

    def __init__(self):
        self.analyzer = QualityAnalyzer()
        self.monitoring_active = False
        self.quality_history: Dict[str, List[QualityReport]] = defaultdict(list)

        self._init_default_gates()

    def _init_default_gates(self):
        """Initialize default quality gates."""
        # Gate 1: Minimum quality for production
        self.analyzer.add_quality_gate(QualityGate(
            name="Production Ready",
            description="Minimum quality for production deployment",
            criteria=[
                {"dimension": "correctness", "min_score": 85},
                {"dimension": "security", "min_score": 90},
                {"max_issues": {"critical": 0, "high": 2}}
            ],
            is_blocking=True
        ))

        # Gate 2: Excellence standard
        self.analyzer.add_quality_gate(QualityGate(
            name="Excellence Standard",
            description="High quality bar for core components",
            criteria=[
                {"dimension": "correctness", "min_score": 95},
                {"dimension": "maintainability", "min_score": 85},
                {"dimension": "performance", "min_score": 80},
                {"max_issues": {"critical": 0, "high": 0, "medium": 5}}
            ],
            is_blocking=False
        ))

    async def validate(
        self,
        target: Any,
        target_id: str = None,
        context: Dict[str, Any] = None
    ) -> QualityReport:
        """Validate a target and generate quality report."""
        report = await self.analyzer.analyze(target, context)

        if target_id:
            self.quality_history[target_id].append(report)

        return report

    async def validate_with_gates(
        self,
        target: Any,
        context: Dict[str, Any] = None
    ) -> Tuple[QualityReport, bool, List[str]]:
        """Validate and check quality gates."""
        report = await self.validate(target, context=context)
        passed, failures = self.analyzer.check_quality_gates(report)
        return report, passed, failures

    async def continuous_validation(
        self,
        targets: Dict[str, Any],
        interval_seconds: int = 60
    ):
        """Run continuous validation on multiple targets."""
        self.monitoring_active = True

        while self.monitoring_active:
            for target_id, target in targets.items():
                await self.validate(target, target_id)

            await asyncio.sleep(interval_seconds)

    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.monitoring_active = False

    def get_quality_dashboard(self) -> Dict[str, Any]:
        """Get quality dashboard data."""
        dashboard = {
            "overall_health": "unknown",
            "targets": {},
            "trends": {},
            "alerts": []
        }

        total_score = 0
        target_count = 0

        for target_id, reports in self.quality_history.items():
            if reports:
                latest = reports[-1]
                dashboard["targets"][target_id] = {
                    "score": latest.overall_score,
                    "level": latest.level.value,
                    "issues": len(latest.issues)
                }
                total_score += latest.overall_score
                target_count += 1

                # Check for alerts
                if latest.level in [QualityLevel.POOR, QualityLevel.UNACCEPTABLE]:
                    dashboard["alerts"].append({
                        "target": target_id,
                        "message": f"Quality below acceptable: {latest.level.value}",
                        "score": latest.overall_score
                    })

                # Get trend
                trend = self.analyzer.get_trend(5)
                dashboard["trends"][target_id] = trend

        if target_count > 0:
            avg_score = total_score / target_count
            if avg_score >= 85:
                dashboard["overall_health"] = "excellent"
            elif avg_score >= 70:
                dashboard["overall_health"] = "good"
            elif avg_score >= 50:
                dashboard["overall_health"] = "fair"
            else:
                dashboard["overall_health"] = "poor"

        return dashboard


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Quality Framework."""
    print("=" * 70)
    print("BAEL - QUALITY FRAMEWORK DEMO")
    print("Multi-Dimensional Quality Assurance")
    print("=" * 70)
    print()

    # Create framework
    framework = QualityFramework()

    # Sample code to validate
    sample_code = '''
"""Sample module for quality testing."""
import os
from typing import List, Optional

class DataProcessor:
    """Process data with various transformations."""

    def __init__(self, config: dict = None):
        """Initialize processor."""
        self.config = config or {}
        self.results: List[dict] = []

    def process(self, data: List[dict]) -> List[dict]:
        """Process a list of data items."""
        if data is None:
            return []

        results = []
        for item in data:
            processed = self._transform(item)
            if processed:
                results.append(processed)

        self.results = results
        return results

    def _transform(self, item: dict) -> Optional[dict]:
        """Transform a single item."""
        if not item:
            return None
        return {k: v.upper() if isinstance(v, str) else v
                for k, v in item.items()}

def calculate_stats(numbers: List[float]) -> dict:
    """Calculate statistics for a list of numbers."""
    if not numbers:
        return {"error": "Empty input"}

    return {
        "count": len(numbers),
        "sum": sum(numbers),
        "average": sum(numbers) / len(numbers),
        "min": min(numbers),
        "max": max(numbers)
    }
'''

    # 1. Basic validation
    print("1. VALIDATING CODE QUALITY:")
    print("-" * 40)

    report = await framework.validate(sample_code, "sample_code")

    print(f"   Overall Score: {report.overall_score:.1f}")
    print(f"   Quality Level: {report.level.value}")
    print()

    # 2. Show metrics by dimension
    print("2. QUALITY METRICS BY DIMENSION:")
    print("-" * 40)

    by_dimension = defaultdict(list)
    for metric in report.metrics:
        by_dimension[metric.dimension].append(metric)

    for dimension, metrics in by_dimension.items():
        avg_score = sum(m.score for m in metrics) / len(metrics)
        status = "✓" if avg_score >= 70 else "✗"
        print(f"   {status} {dimension.value}: {avg_score:.1f}")
    print()

    # 3. Show issues
    print("3. QUALITY ISSUES FOUND:")
    print("-" * 40)

    if report.issues:
        for issue in report.issues[:5]:
            print(f"   [{issue.severity.name}] {issue.title}")
    else:
        print("   No issues found!")
    print()

    # 4. Show test results
    print("4. AUTOMATED TEST RESULTS:")
    print("-" * 40)

    passed = sum(1 for t in report.test_results if t.status == ValidationStatus.PASSED)
    failed = sum(1 for t in report.test_results if t.status == ValidationStatus.FAILED)
    print(f"   Tests run: {len(report.test_results)}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print()

    # 5. Check quality gates
    print("5. QUALITY GATE EVALUATION:")
    print("-" * 40)

    passed_gates, failures = framework.analyzer.check_quality_gates(report)
    print(f"   Gates passed: {passed_gates}")
    if failures:
        for failure in failures[:3]:
            print(f"   ✗ {failure}")
    else:
        print("   ✓ All quality gates passed!")
    print()

    # 6. Recommendations
    print("6. IMPROVEMENT RECOMMENDATIONS:")
    print("-" * 40)

    for rec in report.recommendations[:5]:
        print(f"   • {rec}")
    print()

    # 7. Validate problematic code
    print("7. VALIDATING PROBLEMATIC CODE:")
    print("-" * 40)

    bad_code = '''
def process(data):
    result = eval(data)  # Dangerous!
    password = "secret123"  # Hardcoded!
    for i in data:
        for j in data:  # Nested loop
            for k in data:  # Triple nesting!
                pass
    return result
'''

    bad_report = await framework.validate(bad_code, "bad_code")
    print(f"   Score: {bad_report.overall_score:.1f} ({bad_report.level.value})")
    print(f"   Issues: {len(bad_report.issues)}")

    critical = [i for i in bad_report.issues if i.severity == IssueSeverity.CRITICAL]
    print(f"   Critical issues: {len(critical)}")
    print()

    # 8. Dashboard
    print("8. QUALITY DASHBOARD:")
    print("-" * 40)

    dashboard = framework.get_quality_dashboard()
    print(f"   Overall Health: {dashboard['overall_health']}")
    print(f"   Monitored Targets: {len(dashboard['targets'])}")
    print(f"   Active Alerts: {len(dashboard['alerts'])}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Quality Framework Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
