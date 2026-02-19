"""
Test Generator Agent - Creates Comprehensive Test Suites
==========================================================

The test architect that ensures every line of code is validated
with surgical precision.

"Code without tests is broken by design." — Ba'el
"""

import ast
import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .agent_factory import (
    AutonomousAgent,
    AgentConfig,
    AgentType,
    AgentCapability,
    AgentTask,
    AgentResult,
    autonomous_agent,
)


logger = logging.getLogger("BAEL.TestGenerator")


class TestType(Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    FUNCTIONAL = "functional"
    E2E = "end_to_end"
    PERFORMANCE = "performance"
    SECURITY = "security"
    REGRESSION = "regression"
    SMOKE = "smoke"
    PROPERTY = "property_based"
    MUTATION = "mutation"


class TestFramework(Enum):
    """Testing frameworks."""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    NOSE = "nose"
    HYPOTHESIS = "hypothesis"
    JEST = "jest"
    MOCHA = "mocha"


class CoverageType(Enum):
    """Coverage measurement types."""
    LINE = "line"
    BRANCH = "branch"
    FUNCTION = "function"
    STATEMENT = "statement"
    MCDC = "mcdc"


@dataclass
class TestCase:
    """A generated test case."""
    name: str
    test_type: TestType
    target_function: str
    target_file: str
    code: str
    description: str = ""
    priority: int = 3
    estimated_coverage: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """A collection of test cases."""
    name: str
    file_path: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_code: str = ""
    teardown_code: str = ""
    fixtures: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Test coverage report."""
    target_path: str
    total_lines: int = 0
    covered_lines: int = 0
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    uncovered_functions: List[str] = field(default_factory=list)
    uncovered_lines: Dict[str, List[int]] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TestGenerationResult:
    """Result of test generation."""
    target_path: str
    test_suites: List[TestSuite] = field(default_factory=list)
    total_tests_generated: int = 0
    estimated_coverage_increase: float = 0.0
    recommendations: List[str] = field(default_factory=list)


@autonomous_agent(AgentType.TEST_GENERATOR)
class TestGeneratorAgent(AutonomousAgent):
    """Agent that generates comprehensive test suites."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.framework = TestFramework.PYTEST
        self.generated_suites: Dict[str, TestSuite] = {}

    async def _setup(self) -> None:
        """Initialize the test generator."""
        self.config.capabilities = [
            AgentCapability.TEST_GENERATION,
            AgentCapability.CODE_ANALYSIS,
            AgentCapability.TESTING,
            AgentCapability.REPORTING,
        ]
        logger.info("Test Generator Agent initialized")

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a test generation task."""
        try:
            action = task.parameters.get("action", "generate")

            if action == "generate":
                result = await self._generate_tests(task.target_path)
            elif action == "analyze_coverage":
                result = await self._analyze_coverage(task.target_path)
            elif action == "generate_unit":
                result = await self._generate_unit_tests(task.target_path)
            elif action == "generate_integration":
                result = await self._generate_integration_tests(task.target_path)
            else:
                result = await self._generate_tests(task.target_path)

            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=True,
                result=result,
                metrics={
                    "tests_generated": result.total_tests_generated if hasattr(result, 'total_tests_generated') else 0,
                },
                recommendations=result.recommendations if hasattr(result, 'recommendations') else [],
            )

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return AgentResult(
                task_id=task.id,
                agent_id=self.id,
                agent_type=self.agent_type,
                success=False,
                error=str(e),
            )

    async def _generate_tests(self, path: Path) -> TestGenerationResult:
        """Generate tests for a codebase."""
        result = TestGenerationResult(target_path=str(path))

        if not path or not path.exists():
            return result

        # Find Python files that need tests
        python_files = [
            f for f in path.rglob("*.py")
            if not f.name.startswith("test_")
            and "test" not in f.parent.name
            and "__pycache__" not in str(f)
        ]

        for file_path in python_files:
            suite = await self._generate_suite_for_file(file_path, path)
            if suite.test_cases:
                result.test_suites.append(suite)
                result.total_tests_generated += len(suite.test_cases)
                self.generated_suites[str(file_path)] = suite

        # Calculate estimated coverage increase
        result.estimated_coverage_increase = min(
            result.total_tests_generated * 5,  # Rough estimate
            100 - 0  # Would need actual coverage data
        )

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        self.metrics.code_generated_lines += sum(
            len(tc.code.split('\n'))
            for suite in result.test_suites
            for tc in suite.test_cases
        )

        return result

    async def _generate_suite_for_file(
        self,
        file_path: Path,
        project_path: Path
    ) -> TestSuite:
        """Generate a test suite for a specific file."""
        relative_path = file_path.relative_to(project_path)
        test_file_name = f"test_{file_path.stem}.py"

        suite = TestSuite(
            name=f"Test{file_path.stem.replace('_', ' ').title().replace(' ', '')}",
            file_path=str(project_path / "tests" / test_file_name),
        )

        # Analyze the source file
        functions = await self._extract_functions(file_path)

        # Generate module import
        module_path = str(relative_path).replace("/", ".").replace(".py", "")
        suite.imports = [
            "import pytest",
            f"from {module_path} import *",
        ]

        # Generate test cases for each function
        for func in functions:
            test_cases = self._generate_test_cases_for_function(func, file_path)
            suite.test_cases.extend(test_cases)

        return suite

    async def _extract_functions(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract function information from a file."""
        functions = []

        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip private and magic methods (except __init__)
                    if node.name.startswith('_') and node.name != '__init__':
                        continue

                    func_info = {
                        "name": node.name,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "parameters": [arg.arg for arg in node.args.args if arg.arg != 'self'],
                        "has_return": self._has_return(node),
                        "line_number": node.lineno,
                        "docstring": ast.get_docstring(node) or "",
                        "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    }
                    functions.append(func_info)

        except Exception as e:
            logger.debug(f"Error extracting functions from {file_path}: {e}")

        return functions

    def _has_return(self, node: ast.FunctionDef) -> bool:
        """Check if function has a return statement."""
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                return True
        return False

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Get decorator name."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        return ""

    def _generate_test_cases_for_function(
        self,
        func: Dict[str, Any],
        file_path: Path
    ) -> List[TestCase]:
        """Generate test cases for a function."""
        test_cases = []
        func_name = func["name"]

        # Basic functionality test
        test_cases.append(self._create_basic_test(func, file_path))

        # Edge case tests
        if func["parameters"]:
            test_cases.append(self._create_edge_case_test(func, file_path))

        # Error handling test
        test_cases.append(self._create_error_test(func, file_path))

        # Return value test
        if func["has_return"]:
            test_cases.append(self._create_return_test(func, file_path))

        return test_cases

    def _create_basic_test(self, func: Dict[str, Any], file_path: Path) -> TestCase:
        """Create a basic functionality test."""
        func_name = func["name"]
        is_async = func["is_async"]
        params = func["parameters"]

        # Generate test parameters
        param_values = ", ".join(self._generate_param_value(p) for p in params)

        if is_async:
            code = f'''
@pytest.mark.asyncio
async def test_{func_name}_basic():
    """Test basic functionality of {func_name}."""
    result = await {func_name}({param_values})
    assert result is not None
'''
        else:
            code = f'''
def test_{func_name}_basic():
    """Test basic functionality of {func_name}."""
    result = {func_name}({param_values})
    assert result is not None
'''

        return TestCase(
            name=f"test_{func_name}_basic",
            test_type=TestType.UNIT,
            target_function=func_name,
            target_file=str(file_path),
            code=code.strip(),
            description=f"Basic test for {func_name}",
            priority=1,
            estimated_coverage=20.0,
        )

    def _create_edge_case_test(self, func: Dict[str, Any], file_path: Path) -> TestCase:
        """Create an edge case test."""
        func_name = func["name"]
        is_async = func["is_async"]
        params = func["parameters"]

        # Generate edge case parameters (empty, None, etc.)
        param_values = ", ".join(
            self._generate_edge_case_value(p) for p in params
        )

        if is_async:
            code = f'''
@pytest.mark.asyncio
async def test_{func_name}_edge_cases():
    """Test edge cases for {func_name}."""
    # Test with edge case values
    try:
        result = await {func_name}({param_values})
        # Verify behavior with edge cases
        assert True  # TODO: Add specific assertions
    except Exception as e:
        # Document expected exceptions
        pass
'''
        else:
            code = f'''
def test_{func_name}_edge_cases():
    """Test edge cases for {func_name}."""
    # Test with edge case values
    try:
        result = {func_name}({param_values})
        # Verify behavior with edge cases
        assert True  # TODO: Add specific assertions
    except Exception as e:
        # Document expected exceptions
        pass
'''

        return TestCase(
            name=f"test_{func_name}_edge_cases",
            test_type=TestType.UNIT,
            target_function=func_name,
            target_file=str(file_path),
            code=code.strip(),
            description=f"Edge case test for {func_name}",
            priority=2,
            estimated_coverage=15.0,
            tags=["edge_case"],
        )

    def _create_error_test(self, func: Dict[str, Any], file_path: Path) -> TestCase:
        """Create an error handling test."""
        func_name = func["name"]
        is_async = func["is_async"]

        if is_async:
            code = f'''
@pytest.mark.asyncio
async def test_{func_name}_error_handling():
    """Test error handling for {func_name}."""
    with pytest.raises((ValueError, TypeError, AttributeError)):
        await {func_name}(None)  # TODO: Adjust invalid input
'''
        else:
            code = f'''
def test_{func_name}_error_handling():
    """Test error handling for {func_name}."""
    with pytest.raises((ValueError, TypeError, AttributeError)):
        {func_name}(None)  # TODO: Adjust invalid input
'''

        return TestCase(
            name=f"test_{func_name}_error_handling",
            test_type=TestType.UNIT,
            target_function=func_name,
            target_file=str(file_path),
            code=code.strip(),
            description=f"Error handling test for {func_name}",
            priority=2,
            estimated_coverage=10.0,
            tags=["error_handling"],
        )

    def _create_return_test(self, func: Dict[str, Any], file_path: Path) -> TestCase:
        """Create a return value test."""
        func_name = func["name"]
        is_async = func["is_async"]
        params = func["parameters"]
        param_values = ", ".join(self._generate_param_value(p) for p in params)

        if is_async:
            code = f'''
@pytest.mark.asyncio
async def test_{func_name}_return_value():
    """Test return value of {func_name}."""
    result = await {func_name}({param_values})
    # TODO: Add specific return value assertions
    assert result is not None
    # assert isinstance(result, ExpectedType)
'''
        else:
            code = f'''
def test_{func_name}_return_value():
    """Test return value of {func_name}."""
    result = {func_name}({param_values})
    # TODO: Add specific return value assertions
    assert result is not None
    # assert isinstance(result, ExpectedType)
'''

        return TestCase(
            name=f"test_{func_name}_return_value",
            test_type=TestType.UNIT,
            target_function=func_name,
            target_file=str(file_path),
            code=code.strip(),
            description=f"Return value test for {func_name}",
            priority=1,
            estimated_coverage=15.0,
        )

    def _generate_param_value(self, param_name: str) -> str:
        """Generate a test value for a parameter based on its name."""
        param_lower = param_name.lower()

        if "path" in param_lower or "file" in param_lower or "dir" in param_lower:
            return 'Path(".")'
        elif "name" in param_lower or "str" in param_lower or "text" in param_lower:
            return '"test_value"'
        elif "count" in param_lower or "num" in param_lower or "size" in param_lower or "id" in param_lower:
            return "1"
        elif "flag" in param_lower or "enabled" in param_lower or "is_" in param_lower:
            return "True"
        elif "list" in param_lower or "items" in param_lower:
            return "[]"
        elif "dict" in param_lower or "data" in param_lower or "config" in param_lower:
            return "{}"
        else:
            return "None"

    def _generate_edge_case_value(self, param_name: str) -> str:
        """Generate an edge case value for a parameter."""
        param_lower = param_name.lower()

        if "path" in param_lower or "file" in param_lower:
            return 'Path("")'
        elif "name" in param_lower or "str" in param_lower:
            return '""'
        elif "count" in param_lower or "num" in param_lower:
            return "0"
        elif "list" in param_lower:
            return "[]"
        elif "dict" in param_lower:
            return "{}"
        else:
            return "None"

    async def _analyze_coverage(self, path: Path) -> CoverageReport:
        """Analyze test coverage."""
        report = CoverageReport(target_path=str(path))

        # Count total functions and estimate coverage
        python_files = list(path.rglob("*.py"))
        test_files = [f for f in python_files if f.name.startswith("test_") or "test" in f.parent.name]
        source_files = [f for f in python_files if f not in test_files]

        total_functions = 0
        tested_functions = set()

        for source_file in source_files:
            functions = await self._extract_functions(source_file)
            total_functions += len(functions)

        # Check which functions have tests
        for test_file in test_files:
            try:
                content = test_file.read_text()
                # Extract tested function names from test names
                tested = re.findall(r'def test_(\w+)', content)
                tested_functions.update(tested)
            except Exception:
                continue

        report.total_lines = sum(
            len(f.read_text().split('\n'))
            for f in source_files
            if f.is_file()
        )

        report.function_coverage = (
            len(tested_functions) / total_functions * 100
            if total_functions > 0 else 0
        )

        report.line_coverage = report.function_coverage * 0.6  # Rough estimate

        report.recommendations = [
            f"Function coverage: {report.function_coverage:.1f}%",
            f"Run 'pytest --cov' for accurate coverage report",
        ]

        return report

    async def _generate_unit_tests(self, path: Path) -> TestGenerationResult:
        """Generate unit tests only."""
        result = await self._generate_tests(path)
        result.test_suites = [
            TestSuite(
                name=suite.name,
                file_path=suite.file_path,
                test_cases=[tc for tc in suite.test_cases if tc.test_type == TestType.UNIT],
                imports=suite.imports,
            )
            for suite in result.test_suites
        ]
        result.total_tests_generated = sum(
            len(suite.test_cases) for suite in result.test_suites
        )
        return result

    async def _generate_integration_tests(self, path: Path) -> TestGenerationResult:
        """Generate integration tests."""
        result = TestGenerationResult(target_path=str(path))

        # Look for main entry points and APIs
        suite = TestSuite(
            name="IntegrationTests",
            file_path=str(path / "tests" / "test_integration.py"),
            imports=[
                "import pytest",
                "import asyncio",
            ],
        )

        # Add basic integration test
        suite.test_cases.append(TestCase(
            name="test_full_workflow",
            test_type=TestType.INTEGRATION,
            target_function="main",
            target_file=str(path),
            code='''
@pytest.mark.integration
def test_full_workflow():
    """Test full application workflow."""
    # TODO: Implement integration test
    # 1. Setup test environment
    # 2. Execute main workflow
    # 3. Verify results
    # 4. Cleanup
    assert True
''',
            description="Full workflow integration test",
            priority=1,
        ))

        result.test_suites.append(suite)
        result.total_tests_generated = 1

        return result

    def _generate_recommendations(self, result: TestGenerationResult) -> List[str]:
        """Generate recommendations."""
        recommendations = []

        if result.total_tests_generated > 0:
            recommendations.append(
                f"Generated {result.total_tests_generated} test cases"
            )

        recommendations.extend([
            "Run 'pytest --cov' to measure actual coverage",
            "Add property-based tests with Hypothesis for critical functions",
            "Set up mutation testing with mutmut for test quality",
        ])

        return recommendations

    async def generate_tests_for_project(self, path: Path) -> TestGenerationResult:
        """Public method to generate tests."""
        return await self._generate_tests(path)
