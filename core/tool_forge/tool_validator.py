"""
BAEL Tool Validator
====================

Safety and correctness checking for tools.
Ensures tools are safe to execute.

Features:
- Static code analysis
- Security scanning
- Sandbox testing
- Performance profiling
- Correctness verification
"""

import ast
import asyncio
import hashlib
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels."""
    SAFE = 1  # Fully safe, no restrictions
    LOW_RISK = 2  # Minor risks, monitored
    MEDIUM_RISK = 3  # Significant risks, sandboxed
    HIGH_RISK = 4  # Major risks, requires approval
    DANGEROUS = 5  # Unsafe, blocked


class IssueType(Enum):
    """Types of validation issues."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    STYLE = "style"
    DEPENDENCY = "dependency"


@dataclass
class SafetyCheck:
    """A safety check result."""
    name: str
    passed: bool

    # Details
    message: str = ""
    severity: SecurityLevel = SecurityLevel.SAFE

    # Location
    line: Optional[int] = None
    column: Optional[int] = None

    # Fix suggestion
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Result of tool validation."""
    id: str
    tool_name: str

    # Overall status
    valid: bool = True
    security_level: SecurityLevel = SecurityLevel.SAFE

    # Checks performed
    checks: List[SafetyCheck] = field(default_factory=list)

    # Issues found
    security_issues: List[str] = field(default_factory=list)
    correctness_issues: List[str] = field(default_factory=list)
    performance_issues: List[str] = field(default_factory=list)

    # Scores
    security_score: float = 1.0
    quality_score: float = 1.0

    # Metadata
    validated_at: datetime = field(default_factory=datetime.now)


class ToolValidator:
    """
    Tool validator for BAEL.

    Ensures tools are safe and correct.
    """

    # Dangerous patterns to check
    DANGEROUS_PATTERNS = [
        (r"eval\s*\(", "Use of eval() is dangerous", SecurityLevel.DANGEROUS),
        (r"exec\s*\(", "Use of exec() is dangerous", SecurityLevel.DANGEROUS),
        (r"__import__\s*\(", "Dynamic import is risky", SecurityLevel.HIGH_RISK),
        (r"os\.system\s*\(", "Shell command execution", SecurityLevel.HIGH_RISK),
        (r"subprocess\.", "Subprocess execution", SecurityLevel.MEDIUM_RISK),
        (r"open\s*\([^)]*['\"]w['\"]", "File write operation", SecurityLevel.MEDIUM_RISK),
        (r"pickle\.", "Pickle deserialization risk", SecurityLevel.MEDIUM_RISK),
        (r"\.popen\s*\(", "Process creation", SecurityLevel.HIGH_RISK),
        (r"ctypes\.", "Low-level memory access", SecurityLevel.HIGH_RISK),
        (r"socket\.", "Network socket access", SecurityLevel.MEDIUM_RISK),
    ]

    # Dangerous imports
    DANGEROUS_IMPORTS = {
        "os": SecurityLevel.MEDIUM_RISK,
        "sys": SecurityLevel.LOW_RISK,
        "subprocess": SecurityLevel.HIGH_RISK,
        "pickle": SecurityLevel.MEDIUM_RISK,
        "ctypes": SecurityLevel.HIGH_RISK,
        "socket": SecurityLevel.MEDIUM_RISK,
        "multiprocessing": SecurityLevel.MEDIUM_RISK,
        "threading": SecurityLevel.LOW_RISK,
    }

    def __init__(self):
        # Validation history
        self._history: Dict[str, ValidationResult] = {}

        # Custom rules
        self._custom_rules: List[Callable[[str], Optional[SafetyCheck]]] = []

        # Stats
        self.stats = {
            "validations_performed": 0,
            "tools_approved": 0,
            "tools_rejected": 0,
            "security_issues_found": 0,
        }

    def validate(
        self,
        code: str,
        tool_name: str = "unknown",
        allow_dangerous: bool = False,
    ) -> ValidationResult:
        """
        Validate tool code.

        Args:
            code: Tool source code
            tool_name: Tool name
            allow_dangerous: Allow dangerous operations

        Returns:
            Validation result
        """
        result_id = hashlib.md5(
            f"{tool_name}:{code[:100]}".encode()
        ).hexdigest()[:12]

        result = ValidationResult(
            id=result_id,
            tool_name=tool_name,
        )

        # Run checks
        self._check_syntax(code, result)
        self._check_patterns(code, result)
        self._check_imports(code, result)
        self._check_ast(code, result)
        self._run_custom_rules(code, result)

        # Calculate scores
        self._calculate_scores(result)

        # Determine overall validity
        if not allow_dangerous and result.security_level == SecurityLevel.DANGEROUS:
            result.valid = False

        self._history[result_id] = result
        self.stats["validations_performed"] += 1

        if result.valid:
            self.stats["tools_approved"] += 1
        else:
            self.stats["tools_rejected"] += 1

        self.stats["security_issues_found"] += len(result.security_issues)

        return result

    def _check_syntax(self, code: str, result: ValidationResult) -> None:
        """Check syntax validity."""
        try:
            ast.parse(code)
            result.checks.append(SafetyCheck(
                name="syntax",
                passed=True,
                message="Syntax is valid",
            ))
        except SyntaxError as e:
            result.valid = False
            result.correctness_issues.append(f"Syntax error: {e}")
            result.checks.append(SafetyCheck(
                name="syntax",
                passed=False,
                message=str(e),
                line=e.lineno,
            ))

    def _check_patterns(self, code: str, result: ValidationResult) -> None:
        """Check for dangerous patterns."""
        for pattern, message, severity in self.DANGEROUS_PATTERNS:
            matches = list(re.finditer(pattern, code))

            if matches:
                result.security_issues.append(message)

                if severity.value > result.security_level.value:
                    result.security_level = severity

                for match in matches:
                    line = code[:match.start()].count('\n') + 1

                    result.checks.append(SafetyCheck(
                        name=f"pattern_{pattern[:10]}",
                        passed=False,
                        message=message,
                        severity=severity,
                        line=line,
                        suggestion="Consider using safer alternatives",
                    ))

    def _check_imports(self, code: str, result: ValidationResult) -> None:
        """Check imports for security risks."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_import_name(alias.name, node.lineno, result)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_import_name(node.module, node.lineno, result)

    def _check_import_name(
        self,
        name: str,
        line: int,
        result: ValidationResult,
    ) -> None:
        """Check a single import name."""
        base_module = name.split('.')[0]

        if base_module in self.DANGEROUS_IMPORTS:
            severity = self.DANGEROUS_IMPORTS[base_module]

            result.security_issues.append(f"Import of {base_module}")

            if severity.value > result.security_level.value:
                result.security_level = severity

            result.checks.append(SafetyCheck(
                name=f"import_{base_module}",
                passed=False,
                message=f"Import of potentially dangerous module: {base_module}",
                severity=severity,
                line=line,
            ))

    def _check_ast(self, code: str, result: ValidationResult) -> None:
        """Check AST for issues."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        # Check for infinite loops
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    # while True: without obvious break
                    has_break = any(
                        isinstance(n, ast.Break) for n in ast.walk(node)
                    )
                    if not has_break:
                        result.performance_issues.append("Potential infinite loop")
                        result.checks.append(SafetyCheck(
                            name="infinite_loop",
                            passed=False,
                            message="Potential infinite loop detected",
                            severity=SecurityLevel.MEDIUM_RISK,
                            line=node.lineno,
                        ))

            # Check for recursion without base case
            if isinstance(node, ast.FunctionDef):
                self._check_recursion(node, result)

    def _check_recursion(
        self,
        func: ast.FunctionDef,
        result: ValidationResult,
    ) -> None:
        """Check for unbounded recursion."""
        func_name = func.name

        # Look for recursive calls
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == func_name:
                    # Check for obvious base case
                    has_return = any(
                        isinstance(n, ast.Return) for n in ast.walk(func)
                        if not any(isinstance(c, ast.Call) for c in ast.walk(n))
                    )

                    if not has_return:
                        result.performance_issues.append(f"Potential unbounded recursion in {func_name}")

    def _run_custom_rules(self, code: str, result: ValidationResult) -> None:
        """Run custom validation rules."""
        for rule in self._custom_rules:
            check = rule(code)
            if check:
                result.checks.append(check)

                if not check.passed:
                    if check.severity.value >= SecurityLevel.MEDIUM_RISK.value:
                        result.security_issues.append(check.message)

    def _calculate_scores(self, result: ValidationResult) -> None:
        """Calculate validation scores."""
        total_checks = len(result.checks)
        if total_checks == 0:
            return

        passed_checks = sum(1 for c in result.checks if c.passed)

        # Quality score based on passed checks
        result.quality_score = passed_checks / total_checks

        # Security score based on severity
        severity_weights = {
            SecurityLevel.SAFE: 0,
            SecurityLevel.LOW_RISK: 0.1,
            SecurityLevel.MEDIUM_RISK: 0.3,
            SecurityLevel.HIGH_RISK: 0.6,
            SecurityLevel.DANGEROUS: 1.0,
        }

        total_weight = sum(
            severity_weights.get(c.severity, 0)
            for c in result.checks if not c.passed
        )

        result.security_score = max(0, 1.0 - total_weight)

    def add_rule(
        self,
        rule: Callable[[str], Optional[SafetyCheck]],
    ) -> None:
        """Add a custom validation rule."""
        self._custom_rules.append(rule)

    async def sandbox_test(
        self,
        code: str,
        test_inputs: List[Dict[str, Any]],
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Test code in a sandbox environment.

        Args:
            code: Code to test
            test_inputs: Test input dictionaries
            timeout: Execution timeout

        Returns:
            Test results
        """
        results = {
            "success": True,
            "outputs": [],
            "errors": [],
            "execution_times": [],
        }

        # Create restricted globals
        restricted_globals = {
            "__builtins__": {
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "print": print,
                "isinstance": isinstance,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sorted": sorted,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "Exception": Exception,
            }
        }

        try:
            # Compile code
            compiled = compile(code, "<sandbox>", "exec")

            # Execute and get function
            namespace = {}
            exec(compiled, restricted_globals, namespace)

            # Find callable
            func = None
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith("_"):
                    func = obj
                    break

            if not func:
                results["success"] = False
                results["errors"].append("No callable found")
                return results

            # Run tests
            for inputs in test_inputs:
                import time
                start = time.time()

                try:
                    if asyncio.iscoroutinefunction(func):
                        output = await asyncio.wait_for(
                            func(**inputs),
                            timeout=timeout,
                        )
                    else:
                        output = func(**inputs)

                    results["outputs"].append(output)

                except asyncio.TimeoutError:
                    results["success"] = False
                    results["errors"].append(f"Timeout on inputs: {inputs}")

                except Exception as e:
                    results["errors"].append(f"Error: {e}")

                results["execution_times"].append(time.time() - start)

        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Compilation error: {e}")

        return results

    def get_result(self, result_id: str) -> Optional[ValidationResult]:
        """Get a validation result."""
        return self._history.get(result_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get validator statistics."""
        return {
            **self.stats,
            "custom_rules": len(self._custom_rules),
            "history_size": len(self._history),
        }


def demo():
    """Demonstrate tool validator."""
    import asyncio

    print("=" * 60)
    print("BAEL Tool Validator Demo")
    print("=" * 60)

    async def run_demo():
        validator = ToolValidator()

        # Test safe code
        print("\nValidating safe code...")
        safe_code = '''
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        result = validator.validate(safe_code, "add_numbers")
        print(f"  Valid: {result.valid}")
        print(f"  Security level: {result.security_level.name}")
        print(f"  Security score: {result.security_score:.2f}")

        # Test risky code
        print("\nValidating risky code...")
        risky_code = '''
import os
import subprocess

def run_command(cmd: str) -> str:
    """Run a shell command."""
    return subprocess.check_output(cmd, shell=True).decode()
'''
        result = validator.validate(risky_code, "run_command")
        print(f"  Valid: {result.valid}")
        print(f"  Security level: {result.security_level.name}")
        print(f"  Security issues: {result.security_issues}")

        # Test dangerous code
        print("\nValidating dangerous code...")
        dangerous_code = '''
def execute_code(code: str) -> Any:
    """Execute arbitrary code."""
    return eval(code)
'''
        result = validator.validate(dangerous_code, "execute_code")
        print(f"  Valid: {result.valid}")
        print(f"  Security level: {result.security_level.name}")

        # Sandbox test
        print("\nSandbox testing...")
        test_code = '''
def multiply(a, b):
    return a * b
'''
        test_result = await validator.sandbox_test(
            test_code,
            [{"a": 3, "b": 4}, {"a": 10, "b": 5}],
        )
        print(f"  Success: {test_result['success']}")
        print(f"  Outputs: {test_result['outputs']}")

        print(f"\nStats: {validator.get_stats()}")

    asyncio.run(run_demo())


if __name__ == "__main__":
    demo()
