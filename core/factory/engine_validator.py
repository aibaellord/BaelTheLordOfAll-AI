"""
BAEL Engine Validator
======================

Validate generated engines for correctness.
Ensures quality and functionality.

Features:
- Syntax validation
- Type checking
- Style checking
- Security scanning
- Functionality testing
"""

import ast
import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation thoroughness levels."""
    QUICK = "quick"        # Syntax only
    STANDARD = "standard"  # Syntax + types + style
    THOROUGH = "thorough"  # All checks
    STRICT = "strict"      # All checks + security


class IssueSeverity(Enum):
    """Issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class IssueCategory(Enum):
    """Issue categories."""
    SYNTAX = "syntax"
    TYPE = "type"
    STYLE = "style"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    BEST_PRACTICE = "best_practice"


@dataclass
class ValidationIssue:
    """A validation issue."""
    message: str
    severity: IssueSeverity
    category: IssueCategory

    # Location
    line: Optional[int] = None
    column: Optional[int] = None

    # Fix suggestion
    suggestion: Optional[str] = None

    def __str__(self):
        loc = f"L{self.line}" if self.line else ""
        return f"[{self.severity.value}] {self.category.value}: {self.message} {loc}"


@dataclass
class ValidationRule:
    """A validation rule."""
    id: str
    name: str
    description: str
    category: IssueCategory
    severity: IssueSeverity = IssueSeverity.WARNING

    # Checker
    checker: Optional[Callable[[str, ast.AST], List[ValidationIssue]]] = None
    pattern: Optional[str] = None  # Regex pattern

    # Control
    enabled: bool = True
    fixable: bool = False


@dataclass
class ValidationResult:
    """Result of validation."""
    valid: bool

    # Issues
    issues: List[ValidationIssue] = field(default_factory=list)

    # Summary
    errors: int = 0
    warnings: int = 0
    infos: int = 0

    # Metadata
    level: ValidationLevel = ValidationLevel.STANDARD
    time_ms: float = 0.0

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue."""
        self.issues.append(issue)

        if issue.severity == IssueSeverity.ERROR:
            self.errors += 1
            self.valid = False
        elif issue.severity == IssueSeverity.WARNING:
            self.warnings += 1
        elif issue.severity == IssueSeverity.INFO:
            self.infos += 1

    def get_summary(self) -> str:
        """Get validation summary."""
        status = "PASSED" if self.valid else "FAILED"
        return f"{status}: {self.errors} errors, {self.warnings} warnings, {self.infos} infos"


class EngineValidator:
    """
    Engine validation system for BAEL.
    """

    def __init__(self):
        # Rules
        self.rules: Dict[str, ValidationRule] = {}

        # Stats
        self.stats = {
            "validations": 0,
            "passed": 0,
            "failed": 0,
        }

        # Load default rules
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default validation rules."""
        # Syntax rules
        self.rules["syntax_valid"] = ValidationRule(
            id="syntax_valid",
            name="Valid Syntax",
            description="Code must have valid Python syntax",
            category=IssueCategory.SYNTAX,
            severity=IssueSeverity.ERROR,
        )

        # Documentation rules
        self.rules["has_docstrings"] = ValidationRule(
            id="has_docstrings",
            name="Has Docstrings",
            description="Functions and classes should have docstrings",
            category=IssueCategory.DOCUMENTATION,
            severity=IssueSeverity.WARNING,
        )

        # Type hint rules
        self.rules["has_type_hints"] = ValidationRule(
            id="has_type_hints",
            name="Has Type Hints",
            description="Functions should have type hints",
            category=IssueCategory.TYPE,
            severity=IssueSeverity.WARNING,
        )

        # Style rules
        self.rules["line_length"] = ValidationRule(
            id="line_length",
            name="Line Length",
            description="Lines should not exceed 100 characters",
            category=IssueCategory.STYLE,
            severity=IssueSeverity.INFO,
        )

        self.rules["naming_convention"] = ValidationRule(
            id="naming_convention",
            name="Naming Convention",
            description="Follow PEP8 naming conventions",
            category=IssueCategory.STYLE,
            severity=IssueSeverity.WARNING,
        )

        # Security rules
        self.rules["no_exec"] = ValidationRule(
            id="no_exec",
            name="No Exec/Eval",
            description="Avoid using exec() or eval()",
            category=IssueCategory.SECURITY,
            severity=IssueSeverity.ERROR,
            pattern=r"\b(exec|eval)\s*\(",
        )

        self.rules["no_hardcoded_secrets"] = ValidationRule(
            id="no_hardcoded_secrets",
            name="No Hardcoded Secrets",
            description="Do not hardcode passwords, keys, or tokens",
            category=IssueCategory.SECURITY,
            severity=IssueSeverity.ERROR,
            pattern=r"(?:password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
        )

        # Best practices
        self.rules["no_bare_except"] = ValidationRule(
            id="no_bare_except",
            name="No Bare Except",
            description="Avoid bare except clauses",
            category=IssueCategory.BEST_PRACTICE,
            severity=IssueSeverity.WARNING,
            pattern=r"except\s*:",
        )

        self.rules["no_mutable_default"] = ValidationRule(
            id="no_mutable_default",
            name="No Mutable Defaults",
            description="Avoid mutable default arguments",
            category=IssueCategory.BEST_PRACTICE,
            severity=IssueSeverity.WARNING,
        )

    def validate(
        self,
        code: str,
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> ValidationResult:
        """
        Validate code.

        Args:
            code: Code to validate
            level: Validation thoroughness

        Returns:
            ValidationResult
        """
        import time

        self.stats["validations"] += 1
        start_time = time.time()

        result = ValidationResult(valid=True, level=level)

        # Syntax check (always)
        tree = self._check_syntax(code, result)

        if level == ValidationLevel.QUICK:
            # Only syntax for quick validation
            pass

        elif level in (ValidationLevel.STANDARD, ValidationLevel.THOROUGH, ValidationLevel.STRICT):
            # Type and style checks
            if tree:
                self._check_documentation(tree, result)
                self._check_type_hints(tree, result)
                self._check_naming(tree, result)

            self._check_style(code, result)

            # Pattern-based checks
            self._check_patterns(code, result)

        if level in (ValidationLevel.THOROUGH, ValidationLevel.STRICT):
            # Best practices
            if tree:
                self._check_best_practices(tree, result)

        if level == ValidationLevel.STRICT:
            # Security checks
            self._check_security(code, result)

        # Calculate time
        result.time_ms = (time.time() - start_time) * 1000

        # Update stats
        if result.valid:
            self.stats["passed"] += 1
        else:
            self.stats["failed"] += 1

        return result

    def _check_syntax(
        self,
        code: str,
        result: ValidationResult,
    ) -> Optional[ast.AST]:
        """Check syntax validity."""
        try:
            tree = ast.parse(code)
            return tree
        except SyntaxError as e:
            result.add_issue(ValidationIssue(
                message=f"Syntax error: {e.msg}",
                severity=IssueSeverity.ERROR,
                category=IssueCategory.SYNTAX,
                line=e.lineno,
                column=e.offset,
            ))
            return None

    def _check_documentation(
        self,
        tree: ast.AST,
        result: ValidationResult,
    ) -> None:
        """Check documentation."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                if not docstring:
                    result.add_issue(ValidationIssue(
                        message=f"Missing docstring for {node.name}",
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.DOCUMENTATION,
                        line=node.lineno,
                        suggestion=f"Add a docstring to {node.name}",
                    ))

    def _check_type_hints(
        self,
        tree: ast.AST,
        result: ValidationResult,
    ) -> None:
        """Check type hints."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check return type
                if node.returns is None and node.name != "__init__":
                    result.add_issue(ValidationIssue(
                        message=f"Missing return type hint for {node.name}",
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.TYPE,
                        line=node.lineno,
                    ))

                # Check arguments
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != "self":
                        result.add_issue(ValidationIssue(
                            message=f"Missing type hint for argument '{arg.arg}' in {node.name}",
                            severity=IssueSeverity.INFO,
                            category=IssueCategory.TYPE,
                            line=node.lineno,
                        ))

    def _check_naming(
        self,
        tree: ast.AST,
        result: ValidationResult,
    ) -> None:
        """Check naming conventions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Classes should be PascalCase
                if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                    result.add_issue(ValidationIssue(
                        message=f"Class name '{node.name}' should be PascalCase",
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.STYLE,
                        line=node.lineno,
                    ))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Functions should be snake_case
                if not re.match(r"^[a-z_][a-z0-9_]*$", node.name) and not node.name.startswith("_"):
                    result.add_issue(ValidationIssue(
                        message=f"Function name '{node.name}' should be snake_case",
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.STYLE,
                        line=node.lineno,
                    ))

    def _check_style(
        self,
        code: str,
        result: ValidationResult,
    ) -> None:
        """Check style issues."""
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # Line length
            if len(line) > 100:
                result.add_issue(ValidationIssue(
                    message=f"Line too long ({len(line)} > 100 characters)",
                    severity=IssueSeverity.INFO,
                    category=IssueCategory.STYLE,
                    line=i,
                ))

            # Trailing whitespace
            if line.rstrip() != line:
                result.add_issue(ValidationIssue(
                    message="Trailing whitespace",
                    severity=IssueSeverity.INFO,
                    category=IssueCategory.STYLE,
                    line=i,
                ))

    def _check_patterns(
        self,
        code: str,
        result: ValidationResult,
    ) -> None:
        """Check pattern-based rules."""
        for rule in self.rules.values():
            if not rule.enabled or not rule.pattern:
                continue

            matches = list(re.finditer(rule.pattern, code, re.IGNORECASE))
            for match in matches:
                # Find line number
                line = code[:match.start()].count("\n") + 1

                result.add_issue(ValidationIssue(
                    message=rule.description,
                    severity=rule.severity,
                    category=rule.category,
                    line=line,
                ))

    def _check_best_practices(
        self,
        tree: ast.AST,
        result: ValidationResult,
    ) -> None:
        """Check best practices."""
        for node in ast.walk(tree):
            # Mutable default arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        result.add_issue(ValidationIssue(
                            message=f"Mutable default argument in {node.name}",
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.BEST_PRACTICE,
                            line=node.lineno,
                            suggestion="Use None and initialize in function body",
                        ))

            # Bare except
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    result.add_issue(ValidationIssue(
                        message="Bare except clause",
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.BEST_PRACTICE,
                        line=node.lineno,
                        suggestion="Specify exception type(s) to catch",
                    ))

    def _check_security(
        self,
        code: str,
        result: ValidationResult,
    ) -> None:
        """Check security issues."""
        # Dangerous functions
        dangerous_patterns = [
            (r"\b(exec|eval)\s*\(", "Use of exec/eval is dangerous"),
            (r"\bos\.system\s*\(", "Use subprocess instead of os.system"),
            (r"\bpickle\.loads?\s*\(", "Pickle can execute arbitrary code"),
            (r"\byaml\.load\s*\([^,]+\)", "Use yaml.safe_load instead"),
            (r"\bshell\s*=\s*True", "shell=True can be a security risk"),
        ]

        for pattern, message in dangerous_patterns:
            for match in re.finditer(pattern, code):
                line = code[:match.start()].count("\n") + 1
                result.add_issue(ValidationIssue(
                    message=message,
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.SECURITY,
                    line=line,
                ))

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self.rules[rule.id] = rule

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get validator statistics."""
        return {
            **self.stats,
            "rules_count": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
        }


def demo():
    """Demonstrate engine validator."""
    print("=" * 60)
    print("BAEL Engine Validator Demo")
    print("=" * 60)

    validator = EngineValidator()

    # Test code with various issues
    test_code = '''
class myclass:
    def __init__(self, data=[]):
        self.data = data

    def process(self, x):
        try:
            result = eval(x)
        except:
            result = None
        return result

password = "secret123"
'''

    print("\nValidating test code:")
    print("-" * 40)
    print(test_code)
    print("-" * 40)

    # Quick validation
    result = validator.validate(test_code, level=ValidationLevel.QUICK)
    print(f"\nQuick validation: {result.get_summary()}")

    # Strict validation
    result = validator.validate(test_code, level=ValidationLevel.STRICT)
    print(f"Strict validation: {result.get_summary()}")

    print(f"\nIssues found ({len(result.issues)}):")
    for issue in result.issues:
        print(f"  {issue}")

    # Validate good code
    good_code = '''
class DataProcessor:
    """Process data efficiently."""

    def __init__(self, data: list = None):
        """Initialize with optional data."""
        self.data = data or []

    def process(self, item: Any) -> str:
        """Process a single item."""
        try:
            return str(item)
        except ValueError as e:
            return ""
'''

    result2 = validator.validate(good_code, level=ValidationLevel.STRICT)
    print(f"\nGood code validation: {result2.get_summary()}")

    print(f"\nStats: {validator.get_stats()}")


if __name__ == "__main__":
    demo()
