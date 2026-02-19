"""
BAEL Fitness Evaluator
=======================

Evaluates code fitness for genetic programming.
Measures code quality, performance, and correctness.

Features:
- Multiple fitness metrics
- Test-based evaluation
- Performance benchmarking
- Code quality analysis
- Weighted scoring
"""

import ast
import io
import logging
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .code_genome import CodeGenome

logger = logging.getLogger(__name__)


class FitnessMetric(Enum):
    """Fitness metrics."""
    CORRECTNESS = "correctness"  # Test pass rate
    PERFORMANCE = "performance"  # Execution speed
    COMPLEXITY = "complexity"  # Code complexity
    READABILITY = "readability"  # Code readability
    SIZE = "size"  # Code size
    COVERAGE = "coverage"  # Test coverage
    SECURITY = "security"  # Security score
    MAINTAINABILITY = "maintainability"  # Maintainability index


@dataclass
class FitnessCriteria:
    """Criteria for fitness evaluation."""
    metrics: Dict[FitnessMetric, float] = field(default_factory=lambda: {
        FitnessMetric.CORRECTNESS: 0.4,
        FitnessMetric.PERFORMANCE: 0.2,
        FitnessMetric.COMPLEXITY: 0.15,
        FitnessMetric.READABILITY: 0.15,
        FitnessMetric.SIZE: 0.1,
    })

    # Thresholds
    min_correctness: float = 0.0
    max_complexity: float = 50.0
    max_size_lines: int = 1000

    # Test configuration
    test_timeout_seconds: float = 5.0
    max_test_iterations: int = 100


@dataclass
class TestCase:
    """A test case for evaluation."""
    name: str
    inputs: Dict[str, Any]
    expected_output: Any

    # Tolerance for numeric comparisons
    tolerance: float = 1e-6


@dataclass
class FitnessResult:
    """Result of fitness evaluation."""
    genome_id: str

    # Overall fitness (0-1)
    fitness: float = 0.0

    # Individual metrics (0-1)
    metrics: Dict[FitnessMetric, float] = field(default_factory=dict)

    # Test results
    tests_passed: int = 0
    tests_total: int = 0
    test_errors: List[str] = field(default_factory=list)

    # Performance
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0

    # Quality
    cyclomatic_complexity: float = 0.0
    lines_of_code: int = 0

    # Metadata
    evaluated_at: datetime = field(default_factory=datetime.now)
    evaluation_time_ms: float = 0.0


class FitnessEvaluator:
    """
    Fitness evaluator for BAEL.

    Evaluates code genome fitness.
    """

    def __init__(
        self,
        criteria: Optional[FitnessCriteria] = None,
    ):
        self.criteria = criteria or FitnessCriteria()

        # Test cases
        self._test_cases: List[TestCase] = []

        # Reference implementation (for comparison)
        self._reference: Optional[Callable] = None

        # Stats
        self.stats = {
            "evaluations_performed": 0,
            "total_tests_run": 0,
            "total_tests_passed": 0,
        }

    def add_test_case(
        self,
        name: str,
        inputs: Dict[str, Any],
        expected: Any,
    ) -> None:
        """Add a test case."""
        self._test_cases.append(TestCase(
            name=name,
            inputs=inputs,
            expected_output=expected,
        ))

    def set_reference(self, reference: Callable) -> None:
        """Set reference implementation."""
        self._reference = reference

    def evaluate(
        self,
        genome: CodeGenome,
        function_name: Optional[str] = None,
    ) -> FitnessResult:
        """
        Evaluate genome fitness.

        Args:
            genome: Genome to evaluate
            function_name: Name of function to test

        Returns:
            Fitness result
        """
        start_time = time.time()

        result = FitnessResult(genome_id=genome.id)

        # Decode genome to code
        code = genome.source_code
        if not code:
            from .code_genome import GenomeEncoder
            encoder = GenomeEncoder()
            code = encoder.decode(genome)

        # Calculate metrics
        result.metrics[FitnessMetric.CORRECTNESS] = self._evaluate_correctness(
            code, function_name, result
        )
        result.metrics[FitnessMetric.PERFORMANCE] = self._evaluate_performance(
            code, function_name, result
        )
        result.metrics[FitnessMetric.COMPLEXITY] = self._evaluate_complexity(code, result)
        result.metrics[FitnessMetric.READABILITY] = self._evaluate_readability(code, result)
        result.metrics[FitnessMetric.SIZE] = self._evaluate_size(code, result)

        # Calculate weighted fitness
        result.fitness = self._calculate_weighted_fitness(result.metrics)

        # Update genome fitness
        genome.fitness = result.fitness

        result.evaluation_time_ms = (time.time() - start_time) * 1000

        self.stats["evaluations_performed"] += 1

        return result

    def _evaluate_correctness(
        self,
        code: str,
        function_name: Optional[str],
        result: FitnessResult,
    ) -> float:
        """Evaluate code correctness using test cases."""
        if not self._test_cases:
            return 1.0  # No tests = assume correct

        result.tests_total = len(self._test_cases)

        # Try to execute code
        try:
            namespace = {}
            exec(code, namespace)

            if function_name and function_name not in namespace:
                result.test_errors.append(f"Function '{function_name}' not found")
                return 0.0

            func = namespace.get(function_name) if function_name else None

            if not func:
                # Try to find first callable
                for name, obj in namespace.items():
                    if callable(obj) and not name.startswith('_'):
                        func = obj
                        break

            if not func:
                result.test_errors.append("No callable function found")
                return 0.0

            # Run tests
            for test in self._test_cases:
                try:
                    # Set timeout
                    start = time.time()
                    actual = func(**test.inputs)
                    elapsed = time.time() - start

                    if elapsed > self.criteria.test_timeout_seconds:
                        result.test_errors.append(f"{test.name}: Timeout")
                        continue

                    # Compare results
                    if self._compare_outputs(actual, test.expected_output, test.tolerance):
                        result.tests_passed += 1
                    else:
                        result.test_errors.append(
                            f"{test.name}: Expected {test.expected_output}, got {actual}"
                        )

                except Exception as e:
                    result.test_errors.append(f"{test.name}: {str(e)}")

            self.stats["total_tests_run"] += result.tests_total
            self.stats["total_tests_passed"] += result.tests_passed

            return result.tests_passed / result.tests_total

        except Exception as e:
            result.test_errors.append(f"Execution error: {str(e)}")
            return 0.0

    def _compare_outputs(
        self,
        actual: Any,
        expected: Any,
        tolerance: float,
    ) -> bool:
        """Compare actual and expected outputs."""
        if actual == expected:
            return True

        # Numeric comparison with tolerance
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return abs(actual - expected) <= tolerance

        # List/tuple comparison
        if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
            if len(actual) != len(expected):
                return False
            return all(
                self._compare_outputs(a, e, tolerance)
                for a, e in zip(actual, expected)
            )

        return False

    def _evaluate_performance(
        self,
        code: str,
        function_name: Optional[str],
        result: FitnessResult,
    ) -> float:
        """Evaluate code performance."""
        try:
            namespace = {}
            exec(code, namespace)

            func = namespace.get(function_name) if function_name else None
            if not func:
                for name, obj in namespace.items():
                    if callable(obj) and not name.startswith('_'):
                        func = obj
                        break

            if not func or not self._test_cases:
                return 0.5  # Unknown performance

            # Run performance tests
            times = []
            test = self._test_cases[0]  # Use first test case

            for _ in range(min(10, self.criteria.max_test_iterations)):
                start = time.time()
                try:
                    func(**test.inputs)
                except Exception:
                    break
                elapsed = (time.time() - start) * 1000  # ms
                times.append(elapsed)

            if times:
                avg_time = sum(times) / len(times)
                result.execution_time_ms = avg_time

                # Score: faster is better (inverse, capped)
                # 1ms or less = 1.0, 100ms = 0.5, 1000ms+ = 0.0
                if avg_time <= 1:
                    return 1.0
                elif avg_time >= 1000:
                    return 0.0
                else:
                    return 1.0 - (avg_time / 1000)

            return 0.5

        except Exception:
            return 0.0

    def _evaluate_complexity(
        self,
        code: str,
        result: FitnessResult,
    ) -> float:
        """Evaluate code complexity."""
        try:
            tree = ast.parse(code)
            complexity = self._calculate_cyclomatic_complexity(tree)
            result.cyclomatic_complexity = complexity

            # Score: lower is better
            # 1-10 = good, 10-20 = moderate, 20+ = complex
            max_complexity = self.criteria.max_complexity
            if complexity <= 10:
                return 1.0
            elif complexity >= max_complexity:
                return 0.0
            else:
                return 1.0 - ((complexity - 10) / (max_complexity - 10))

        except Exception:
            return 0.5

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.Assert):
                complexity += 1

        return complexity

    def _evaluate_readability(
        self,
        code: str,
        result: FitnessResult,
    ) -> float:
        """Evaluate code readability."""
        score = 1.0

        lines = code.split('\n')

        # Penalize very long lines
        long_lines = sum(1 for line in lines if len(line) > 120)
        if long_lines > 0:
            score -= 0.1 * min(long_lines / len(lines), 0.5)

        # Reward comments
        comments = sum(1 for line in lines if line.strip().startswith('#'))
        comment_ratio = comments / max(len(lines), 1)
        if 0.1 <= comment_ratio <= 0.3:
            score += 0.1

        # Penalize deeply nested code
        try:
            tree = ast.parse(code)
            max_depth = self._get_max_depth(tree)
            if max_depth > 5:
                score -= 0.1 * (max_depth - 5)
        except Exception:
            pass

        # Check for docstrings
        if '"""' in code or "'''" in code:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _get_max_depth(self, node: ast.AST, depth: int = 0) -> int:
        """Get maximum nesting depth."""
        max_depth = depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._get_max_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._get_max_depth(child, depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _evaluate_size(
        self,
        code: str,
        result: FitnessResult,
    ) -> float:
        """Evaluate code size."""
        lines = [l for l in code.split('\n') if l.strip()]
        result.lines_of_code = len(lines)

        max_lines = self.criteria.max_size_lines

        # Moderate size is best
        if result.lines_of_code <= 10:
            return 0.8  # Very small
        elif result.lines_of_code <= 50:
            return 1.0  # Optimal
        elif result.lines_of_code <= 200:
            return 0.9  # Good
        elif result.lines_of_code >= max_lines:
            return 0.2  # Too large
        else:
            return 0.5

    def _calculate_weighted_fitness(
        self,
        metrics: Dict[FitnessMetric, float],
    ) -> float:
        """Calculate weighted fitness score."""
        total = 0.0
        weight_sum = 0.0

        for metric, weight in self.criteria.metrics.items():
            if metric in metrics:
                total += metrics[metric] * weight
                weight_sum += weight

        return total / max(weight_sum, 1.0)

    def get_stats(self) -> Dict[str, Any]:
        """Get evaluator statistics."""
        return {
            **self.stats,
            "test_cases": len(self._test_cases),
            "pass_rate": (
                self.stats["total_tests_passed"] /
                max(self.stats["total_tests_run"], 1)
            ),
        }


def demo():
    """Demonstrate fitness evaluator."""
    print("=" * 60)
    print("BAEL Fitness Evaluator Demo")
    print("=" * 60)

    from .code_genome import GenomeEncoder

    encoder = GenomeEncoder()
    evaluator = FitnessEvaluator()

    # Add test cases
    evaluator.add_test_case("zero", {"n": 0}, 0)
    evaluator.add_test_case("one", {"n": 1}, 1)
    evaluator.add_test_case("five", {"n": 5}, 5)
    evaluator.add_test_case("ten", {"n": 10}, 55)

    print(f"\nTest cases: {len(evaluator._test_cases)}")

    # Good implementation
    good_code = '''
def fibonacci(n):
    """Calculate fibonacci number."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b
'''

    print("\nEvaluating good implementation...")
    good_genome = encoder.encode(good_code)
    good_result = evaluator.evaluate(good_genome, "fibonacci")

    print(f"  Fitness: {good_result.fitness:.2%}")
    print(f"  Tests passed: {good_result.tests_passed}/{good_result.tests_total}")
    print(f"  Metrics:")
    for metric, score in good_result.metrics.items():
        print(f"    {metric.value}: {score:.2%}")

    # Bad implementation
    bad_code = '''
def fibonacci(n):
    return n * 2  # Wrong!
'''

    print("\nEvaluating bad implementation...")
    bad_genome = encoder.encode(bad_code)
    bad_result = evaluator.evaluate(bad_genome, "fibonacci")

    print(f"  Fitness: {bad_result.fitness:.2%}")
    print(f"  Tests passed: {bad_result.tests_passed}/{bad_result.tests_total}")
    if bad_result.test_errors:
        print(f"  Errors: {bad_result.test_errors[:2]}")

    print(f"\nStats: {evaluator.get_stats()}")


if __name__ == "__main__":
    demo()
