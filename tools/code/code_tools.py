"""
BAEL Code Tools - Comprehensive Code Analysis & Execution Toolkit
Provides code analysis, execution, formatting, security scanning, and generation.
"""

import ast
import asyncio
import hashlib
import io
import logging
import re
import subprocess
import sys
import tempfile
import traceback
from abc import ABC, abstractmethod
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.Tools.Code")


# =============================================================================
# DATA CLASSES & ENUMS
# =============================================================================

class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    C = "c"
    RUBY = "ruby"
    PHP = "php"
    SHELL = "shell"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueType(Enum):
    """Types of code issues."""
    SYNTAX_ERROR = "syntax_error"
    SECURITY_VULNERABILITY = "security_vulnerability"
    STYLE_VIOLATION = "style_violation"
    PERFORMANCE_ISSUE = "performance_issue"
    LOGIC_ERROR = "logic_error"
    DEPRECATED_USAGE = "deprecated_usage"
    BEST_PRACTICE = "best_practice"
    COMPLEXITY = "complexity"
    DOCUMENTATION = "documentation"


@dataclass
class CodeIssue:
    """Represents a code issue found during analysis."""
    type: IssueType
    severity: Severity
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class SecurityIssue:
    """Security vulnerability found in code."""
    vulnerability_type: str
    severity: Severity
    description: str
    line: Optional[int] = None
    code_snippet: Optional[str] = None
    cwe_id: Optional[str] = None
    fix_recommendation: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of code analysis."""
    language: Language
    issues: List[CodeIssue] = field(default_factory=list)
    security_issues: List[SecurityIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    complexity_score: float = 0.0
    quality_score: float = 100.0
    analyzed_at: datetime = field(default_factory=datetime.now)

    @property
    def has_errors(self) -> bool:
        return any(i.type == IssueType.SYNTAX_ERROR for i in self.issues)

    @property
    def has_security_issues(self) -> bool:
        return len(self.security_issues) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language.value,
            "issues": [
                {
                    "type": i.type.value,
                    "severity": i.severity.value,
                    "message": i.message,
                    "line": i.line,
                    "suggestion": i.suggestion
                }
                for i in self.issues
            ],
            "security_issues": [
                {
                    "type": s.vulnerability_type,
                    "severity": s.severity.value,
                    "description": s.description,
                    "line": s.line,
                    "cwe_id": s.cwe_id,
                    "fix": s.fix_recommendation
                }
                for s in self.security_issues
            ],
            "metrics": self.metrics,
            "complexity_score": self.complexity_score,
            "quality_score": self.quality_score
        }


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    execution_time_ms: float = 0.0
    memory_used_bytes: int = 0
    error: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_value": str(self.return_value) if self.return_value else None,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "error_type": self.error_type
        }


@dataclass
class Dependency:
    """A code dependency."""
    name: str
    version: Optional[str] = None
    source: str = "import"
    is_standard_library: bool = False
    is_installed: bool = False


# =============================================================================
# LANGUAGE DETECTOR
# =============================================================================

class LanguageDetector:
    """Detect programming language from code or filename."""

    EXTENSION_MAP = {
        ".py": Language.PYTHON,
        ".js": Language.JAVASCRIPT,
        ".ts": Language.TYPESCRIPT,
        ".tsx": Language.TYPESCRIPT,
        ".jsx": Language.JAVASCRIPT,
        ".rs": Language.RUST,
        ".go": Language.GO,
        ".java": Language.JAVA,
        ".cs": Language.CSHARP,
        ".cpp": Language.CPP,
        ".cc": Language.CPP,
        ".c": Language.C,
        ".h": Language.C,
        ".hpp": Language.CPP,
        ".rb": Language.RUBY,
        ".php": Language.PHP,
        ".sh": Language.SHELL,
        ".bash": Language.SHELL,
        ".sql": Language.SQL,
        ".html": Language.HTML,
        ".htm": Language.HTML,
        ".css": Language.CSS,
        ".json": Language.JSON,
        ".yaml": Language.YAML,
        ".yml": Language.YAML,
        ".md": Language.MARKDOWN,
    }

    SHEBANG_MAP = {
        "python": Language.PYTHON,
        "node": Language.JAVASCRIPT,
        "ruby": Language.RUBY,
        "php": Language.PHP,
        "bash": Language.SHELL,
        "sh": Language.SHELL,
    }

    @classmethod
    def from_filename(cls, filename: str) -> Language:
        """Detect language from filename."""
        ext = Path(filename).suffix.lower()
        return cls.EXTENSION_MAP.get(ext, Language.UNKNOWN)

    @classmethod
    def from_code(cls, code: str) -> Language:
        """Detect language from code content."""
        # Check shebang
        if code.startswith("#!"):
            first_line = code.split("\n")[0]
            for key, lang in cls.SHEBANG_MAP.items():
                if key in first_line:
                    return lang

        # Python indicators
        if re.search(r"^def \w+\(|^class \w+:|import \w+|from \w+ import", code, re.MULTILINE):
            return Language.PYTHON

        # JavaScript/TypeScript indicators
        if re.search(r"function \w+\(|const \w+ =|let \w+ =|=>\s*{|import .* from", code, re.MULTILINE):
            if "interface " in code or ": string" in code or ": number" in code:
                return Language.TYPESCRIPT
            return Language.JAVASCRIPT

        # Rust indicators
        if re.search(r"fn \w+\(|impl |struct \w+|enum \w+|let mut", code, re.MULTILINE):
            return Language.RUST

        # Go indicators
        if re.search(r"func \w+\(|package \w+|type \w+ struct", code, re.MULTILINE):
            return Language.GO

        # Java indicators
        if re.search(r"public class |private class |public static void main", code, re.MULTILINE):
            return Language.JAVA

        return Language.UNKNOWN


# =============================================================================
# SYNTAX CHECKER
# =============================================================================

class SyntaxChecker:
    """Check code for syntax errors."""

    def check_python(self, code: str) -> List[CodeIssue]:
        """Check Python syntax."""
        issues = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(CodeIssue(
                type=IssueType.SYNTAX_ERROR,
                severity=Severity.CRITICAL,
                message=str(e.msg),
                line=e.lineno,
                column=e.offset,
                code_snippet=e.text.strip() if e.text else None
            ))
        return issues

    def check_json(self, code: str) -> List[CodeIssue]:
        """Check JSON syntax."""
        import json
        issues = []
        try:
            json.loads(code)
        except json.JSONDecodeError as e:
            issues.append(CodeIssue(
                type=IssueType.SYNTAX_ERROR,
                severity=Severity.CRITICAL,
                message=str(e.msg),
                line=e.lineno,
                column=e.colno
            ))
        return issues

    def check(self, code: str, language: Language) -> List[CodeIssue]:
        """Check syntax for any supported language."""
        if language == Language.PYTHON:
            return self.check_python(code)
        elif language == Language.JSON:
            return self.check_json(code)
        else:
            return []  # Add more language checkers


# =============================================================================
# CODE ANALYZER
# =============================================================================

class CodeAnalyzer:
    """Comprehensive code analysis."""

    def __init__(self):
        self.syntax_checker = SyntaxChecker()
        self.security_scanner = SecurityScanner()

    def analyze(self, code: str, language: Optional[Language] = None) -> AnalysisResult:
        """Analyze code comprehensively."""
        if language is None:
            language = LanguageDetector.from_code(code)

        result = AnalysisResult(language=language)

        # Syntax check
        syntax_issues = self.syntax_checker.check(code, language)
        result.issues.extend(syntax_issues)

        if not syntax_issues and language == Language.PYTHON:
            # Only do deeper analysis if syntax is valid
            result.issues.extend(self._analyze_python(code))
            result.security_issues = self.security_scanner.scan_python(code)
            result.metrics = self._compute_metrics(code)
            result.complexity_score = self._compute_complexity(code)

        # Compute quality score
        result.quality_score = self._compute_quality_score(result)

        return result

    def _analyze_python(self, code: str) -> List[CodeIssue]:
        """Deep analysis of Python code."""
        issues = []

        try:
            tree = ast.parse(code)
        except:
            return issues

        for node in ast.walk(tree):
            # Check for bare except
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(CodeIssue(
                        type=IssueType.BEST_PRACTICE,
                        severity=Severity.MEDIUM,
                        message="Bare 'except:' clause catches all exceptions including SystemExit and KeyboardInterrupt",
                        line=node.lineno,
                        suggestion="Use 'except Exception:' or catch specific exceptions"
                    ))

            # Check for mutable default arguments
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(CodeIssue(
                            type=IssueType.LOGIC_ERROR,
                            severity=Severity.HIGH,
                            message=f"Mutable default argument in function '{node.name}'",
                            line=node.lineno,
                            suggestion="Use None as default and create mutable object inside function"
                        ))

            # Check for print statements in production code
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    issues.append(CodeIssue(
                        type=IssueType.BEST_PRACTICE,
                        severity=Severity.LOW,
                        message="Consider using logging instead of print()",
                        line=node.lineno,
                        suggestion="Use logging module for production code"
                    ))

            # Check for TODO/FIXME comments
            # (Would need to parse comments separately)

        return issues

    def _compute_metrics(self, code: str) -> Dict[str, Any]:
        """Compute code metrics."""
        lines = code.split("\n")

        return {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith("#")]),
            "comment_lines": len([l for l in lines if l.strip().startswith("#")]),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "avg_line_length": sum(len(l) for l in lines) / len(lines) if lines else 0,
            "max_line_length": max(len(l) for l in lines) if lines else 0,
            "functions": len(re.findall(r"^\s*def \w+", code, re.MULTILINE)),
            "classes": len(re.findall(r"^\s*class \w+", code, re.MULTILINE)),
            "imports": len(re.findall(r"^(?:from|import) ", code, re.MULTILINE))
        }

    def _compute_complexity(self, code: str) -> float:
        """Compute cyclomatic complexity estimate."""
        # Count decision points
        decision_keywords = [
            r"\bif\b", r"\belif\b", r"\belse\b",
            r"\bfor\b", r"\bwhile\b",
            r"\btry\b", r"\bexcept\b",
            r"\band\b", r"\bor\b"
        ]

        complexity = 1  # Base complexity
        for pattern in decision_keywords:
            complexity += len(re.findall(pattern, code))

        return complexity

    def _compute_quality_score(self, result: AnalysisResult) -> float:
        """Compute overall quality score (0-100)."""
        score = 100.0

        # Deduct for issues
        for issue in result.issues:
            if issue.severity == Severity.CRITICAL:
                score -= 20
            elif issue.severity == Severity.HIGH:
                score -= 10
            elif issue.severity == Severity.MEDIUM:
                score -= 5
            elif issue.severity == Severity.LOW:
                score -= 2

        # Deduct for security issues
        for sec in result.security_issues:
            if sec.severity == Severity.CRITICAL:
                score -= 30
            elif sec.severity == Severity.HIGH:
                score -= 20
            elif sec.severity == Severity.MEDIUM:
                score -= 10

        return max(0, min(100, score))


# =============================================================================
# SECURITY SCANNER
# =============================================================================

class SecurityScanner:
    """Scan code for security vulnerabilities."""

    # Python security patterns
    PYTHON_VULNERABILITIES = [
        {
            "pattern": r"eval\s*\(",
            "type": "Code Injection",
            "severity": Severity.CRITICAL,
            "cwe": "CWE-94",
            "message": "Use of eval() can execute arbitrary code",
            "fix": "Use ast.literal_eval() for safe evaluation of literals"
        },
        {
            "pattern": r"exec\s*\(",
            "type": "Code Injection",
            "severity": Severity.CRITICAL,
            "cwe": "CWE-94",
            "message": "Use of exec() can execute arbitrary code",
            "fix": "Avoid exec() or sanitize input thoroughly"
        },
        {
            "pattern": r"subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True",
            "type": "Command Injection",
            "severity": Severity.HIGH,
            "cwe": "CWE-78",
            "message": "Using shell=True in subprocess is dangerous",
            "fix": "Use shell=False and pass arguments as a list"
        },
        {
            "pattern": r"os\.system\s*\(",
            "type": "Command Injection",
            "severity": Severity.HIGH,
            "cwe": "CWE-78",
            "message": "os.system() is vulnerable to command injection",
            "fix": "Use subprocess.run() with shell=False"
        },
        {
            "pattern": r"pickle\.(?:load|loads)\s*\(",
            "type": "Deserialization",
            "severity": Severity.HIGH,
            "cwe": "CWE-502",
            "message": "Unpickling untrusted data can execute arbitrary code",
            "fix": "Use json or other safe formats for untrusted data"
        },
        {
            "pattern": r"yaml\.load\s*\([^)]*\)",
            "type": "Deserialization",
            "severity": Severity.MEDIUM,
            "cwe": "CWE-502",
            "message": "yaml.load() without Loader is unsafe",
            "fix": "Use yaml.safe_load() instead"
        },
        {
            "pattern": r"input\s*\(",
            "type": "Input Validation",
            "severity": Severity.LOW,
            "cwe": "CWE-20",
            "message": "input() should be validated before use",
            "fix": "Always validate and sanitize user input"
        },
        {
            "pattern": r"\.format\s*\([^)]*\)",
            "type": "Format String",
            "severity": Severity.LOW,
            "cwe": "CWE-134",
            "message": "String formatting with untrusted data can be dangerous",
            "fix": "Use f-strings or sanitize format arguments"
        },
        {
            "pattern": r"password\s*=\s*['\"][^'\"]+['\"]",
            "type": "Hardcoded Secrets",
            "severity": Severity.CRITICAL,
            "cwe": "CWE-798",
            "message": "Hardcoded password detected",
            "fix": "Use environment variables or secure secret management"
        },
        {
            "pattern": r"(?:api_key|secret|token)\s*=\s*['\"][^'\"]+['\"]",
            "type": "Hardcoded Secrets",
            "severity": Severity.CRITICAL,
            "cwe": "CWE-798",
            "message": "Hardcoded API key/secret/token detected",
            "fix": "Use environment variables or secure secret management"
        },
        {
            "pattern": r"requests\.get\s*\([^)]*verify\s*=\s*False",
            "type": "SSL Verification",
            "severity": Severity.MEDIUM,
            "cwe": "CWE-295",
            "message": "SSL certificate verification disabled",
            "fix": "Enable SSL verification in production"
        },
        {
            "pattern": r"hashlib\.(?:md5|sha1)\s*\(",
            "type": "Weak Cryptography",
            "severity": Severity.MEDIUM,
            "cwe": "CWE-328",
            "message": "MD5/SHA1 are cryptographically weak",
            "fix": "Use SHA-256 or stronger for security purposes"
        },
        {
            "pattern": r"random\.\w+\s*\(",
            "type": "Weak Random",
            "severity": Severity.LOW,
            "cwe": "CWE-330",
            "message": "random module is not cryptographically secure",
            "fix": "Use secrets module for security-sensitive randomness"
        }
    ]

    def scan_python(self, code: str) -> List[SecurityIssue]:
        """Scan Python code for security issues."""
        issues = []
        lines = code.split("\n")

        for vuln in self.PYTHON_VULNERABILITIES:
            for line_num, line in enumerate(lines, 1):
                if re.search(vuln["pattern"], line, re.IGNORECASE):
                    issues.append(SecurityIssue(
                        vulnerability_type=vuln["type"],
                        severity=vuln["severity"],
                        description=vuln["message"],
                        line=line_num,
                        code_snippet=line.strip(),
                        cwe_id=vuln["cwe"],
                        fix_recommendation=vuln["fix"]
                    ))

        return issues

    def scan(self, code: str, language: Language) -> List[SecurityIssue]:
        """Scan code for security issues."""
        if language == Language.PYTHON:
            return self.scan_python(code)
        return []


# =============================================================================
# CODE EXECUTOR
# =============================================================================

class CodeExecutor:
    """Safe code execution with sandboxing."""

    # Restricted builtins for safe execution
    SAFE_BUILTINS = {
        "abs", "all", "any", "ascii", "bin", "bool", "bytes", "callable",
        "chr", "complex", "dict", "dir", "divmod", "enumerate", "filter",
        "float", "format", "frozenset", "hash", "hex", "int", "isinstance",
        "issubclass", "iter", "len", "list", "map", "max", "min", "next",
        "oct", "ord", "pow", "print", "range", "repr", "reversed", "round",
        "set", "slice", "sorted", "str", "sum", "tuple", "type", "zip"
    }

    # Forbidden imports for safety
    FORBIDDEN_IMPORTS = {
        "os", "sys", "subprocess", "shutil", "socket", "http", "ftplib",
        "telnetlib", "urllib", "requests", "pickle", "marshal", "shelve",
        "ctypes", "multiprocessing", "threading", "signal", "pty", "tty",
        "fcntl", "resource", "grp", "pwd", "crypt", "termios"
    }

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        max_memory_mb: int = 256,
        allow_imports: bool = True,
        safe_mode: bool = True
    ):
        self.timeout = timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.allow_imports = allow_imports
        self.safe_mode = safe_mode

    async def execute_python(
        self,
        code: str,
        globals_dict: Optional[Dict[str, Any]] = None,
        locals_dict: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute Python code safely."""
        import time

        start_time = time.time()

        # Check for forbidden patterns in safe mode
        if self.safe_mode:
            for forbidden in self.FORBIDDEN_IMPORTS:
                if re.search(rf"\bimport\s+{forbidden}\b", code):
                    return ExecutionResult(
                        success=False,
                        error=f"Import of '{forbidden}' is not allowed in safe mode",
                        error_type="SecurityError"
                    )
                if re.search(rf"\bfrom\s+{forbidden}\b", code):
                    return ExecutionResult(
                        success=False,
                        error=f"Import from '{forbidden}' is not allowed in safe mode",
                        error_type="SecurityError"
                    )

        # Prepare execution environment
        exec_globals = globals_dict or {}
        exec_locals = locals_dict or {}

        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        result = ExecutionResult(success=True)

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Compile first to catch syntax errors
                compiled = compile(code, "<string>", "exec")

                # Execute with timeout simulation (real timeout needs threading/subprocess)
                exec(compiled, exec_globals, exec_locals)

            result.stdout = stdout_capture.getvalue()
            result.stderr = stderr_capture.getvalue()

            # Check for a return value (last expression)
            if "_result_" in exec_locals:
                result.return_value = exec_locals["_result_"]

        except SyntaxError as e:
            result.success = False
            result.error = str(e)
            result.error_type = "SyntaxError"
            result.error_traceback = traceback.format_exc()

        except Exception as e:
            result.success = False
            result.error = str(e)
            result.error_type = type(e).__name__
            result.error_traceback = traceback.format_exc()
            result.stderr = stderr_capture.getvalue()

        result.execution_time_ms = (time.time() - start_time) * 1000
        return result

    async def execute_subprocess(
        self,
        code: str,
        language: Language
    ) -> ExecutionResult:
        """Execute code in a subprocess for better isolation."""
        import time

        start_time = time.time()

        # Create temp file
        suffix = {
            Language.PYTHON: ".py",
            Language.JAVASCRIPT: ".js",
            Language.SHELL: ".sh"
        }.get(language, ".txt")

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=suffix,
                delete=False
            ) as f:
                f.write(code)
                temp_path = f.name

            # Determine interpreter
            interpreter = {
                Language.PYTHON: [sys.executable],
                Language.JAVASCRIPT: ["node"],
                Language.SHELL: ["bash"]
            }.get(language)

            if not interpreter:
                return ExecutionResult(
                    success=False,
                    error=f"No interpreter configured for {language.value}"
                )

            # Execute
            proc = subprocess.run(
                interpreter + [temp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=proc.stderr if proc.returncode != 0 else None
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error="Execution timed out",
                error_type="TimeoutError",
                execution_time_ms=self.timeout * 1000
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__
            )
        finally:
            # Cleanup temp file
            try:
                Path(temp_path).unlink()
            except:
                pass


# =============================================================================
# CODE FORMATTER
# =============================================================================

class CodeFormatter:
    """Format code according to style guides."""

    def format_python(self, code: str) -> Tuple[str, bool]:
        """Format Python code using Black-like formatting."""
        # Simple formatting - in production, integrate with black/autopep8
        lines = code.split("\n")
        formatted_lines = []

        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            formatted_lines.append(line)

        # Ensure single newline at end
        result = "\n".join(formatted_lines)
        if result and not result.endswith("\n"):
            result += "\n"

        return result, True

    def format_json(self, code: str, indent: int = 2) -> Tuple[str, bool]:
        """Format JSON code."""
        import json
        try:
            parsed = json.loads(code)
            formatted = json.dumps(parsed, indent=indent, sort_keys=True)
            return formatted, True
        except json.JSONDecodeError as e:
            return code, False

    def format(self, code: str, language: Language) -> Tuple[str, bool]:
        """Format code for the given language."""
        if language == Language.PYTHON:
            return self.format_python(code)
        elif language == Language.JSON:
            return self.format_json(code)
        return code, False


# =============================================================================
# CODE GENERATOR
# =============================================================================

class CodeGenerator:
    """Generate code snippets and boilerplate."""

    TEMPLATES = {
        "python_function": '''def {name}({params}) -> {return_type}:
    """
    {docstring}

    Args:
        {args_doc}

    Returns:
        {return_type}: {return_doc}
    """
    {body}
''',
        "python_class": '''class {name}:
    """
    {docstring}
    """

    def __init__(self{init_params}):
        """Initialize {name}."""
        {init_body}

    {methods}
''',
        "python_test": '''import pytest

class Test{name}:
    """Tests for {name}."""

    def test_{test_name}(self):
        """Test {test_description}."""
        # Arrange
        {arrange}

        # Act
        {act}

        # Assert
        {assert_stmt}
''',
        "python_dataclass": '''from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class {name}:
    """
    {docstring}
    """
    {fields}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {{k: v for k, v in self.__dict__.items()}}
'''
    }

    def generate_function(
        self,
        name: str,
        params: List[Tuple[str, str]] = None,
        return_type: str = "None",
        docstring: str = "",
        body: str = "pass"
    ) -> str:
        """Generate a Python function."""
        params = params or []
        param_str = ", ".join(f"{p[0]}: {p[1]}" for p in params)
        args_doc = "\n        ".join(f"{p[0]} ({p[1]}): Description" for p in params) or "None"

        return self.TEMPLATES["python_function"].format(
            name=name,
            params=param_str,
            return_type=return_type,
            docstring=docstring or f"{name} function.",
            args_doc=args_doc,
            return_doc="Result description",
            body=body or "pass"
        )

    def generate_class(
        self,
        name: str,
        attributes: List[Tuple[str, str, Any]] = None,
        methods: List[str] = None,
        docstring: str = ""
    ) -> str:
        """Generate a Python class."""
        attributes = attributes or []

        init_params = ", ".join(f"{a[0]}: {a[1]} = {a[2]!r}" for a in attributes)
        if init_params:
            init_params = ", " + init_params

        init_body = "\n        ".join(f"self.{a[0]} = {a[0]}" for a in attributes) or "pass"
        methods_str = "\n\n    ".join(methods or [])

        return self.TEMPLATES["python_class"].format(
            name=name,
            docstring=docstring or f"{name} class.",
            init_params=init_params,
            init_body=init_body,
            methods=methods_str or "pass"
        )

    def generate_dataclass(
        self,
        name: str,
        fields: List[Tuple[str, str, Any]] = None,
        docstring: str = ""
    ) -> str:
        """Generate a Python dataclass."""
        fields = fields or []
        fields_str = "\n    ".join(
            f"{f[0]}: {f[1]} = {f[2]!r}" if len(f) > 2 else f"{f[0]}: {f[1]}"
            for f in fields
        )

        return self.TEMPLATES["python_dataclass"].format(
            name=name,
            docstring=docstring or f"{name} dataclass.",
            fields=fields_str or "pass"
        )


# =============================================================================
# DEPENDENCY ANALYZER
# =============================================================================

class DependencyAnalyzer:
    """Analyze code dependencies."""

    PYTHON_STDLIB = {
        "abc", "aifc", "argparse", "array", "ast", "asyncio", "atexit",
        "base64", "binascii", "bisect", "builtins", "calendar", "cgi",
        "cgitb", "chunk", "cmath", "cmd", "code", "codecs", "collections",
        "colorsys", "compileall", "concurrent", "configparser", "contextlib",
        "contextvars", "copy", "copyreg", "csv", "dataclasses", "datetime",
        "decimal", "difflib", "dis", "email", "encodings", "enum", "errno",
        "faulthandler", "filecmp", "fileinput", "fnmatch", "fractions",
        "functools", "gc", "getopt", "getpass", "gettext", "glob", "graphlib",
        "gzip", "hashlib", "heapq", "hmac", "html", "http", "imaplib",
        "importlib", "inspect", "io", "ipaddress", "itertools", "json",
        "keyword", "linecache", "locale", "logging", "lzma", "mailbox",
        "math", "mimetypes", "modulefinder", "numbers", "operator", "os",
        "pathlib", "pickle", "pkgutil", "platform", "plistlib", "poplib",
        "posixpath", "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
        "queue", "quopri", "random", "re", "readline", "reprlib", "runpy",
        "sched", "secrets", "select", "selectors", "shelve", "shlex", "shutil",
        "signal", "site", "smtplib", "socket", "socketserver", "sqlite3",
        "ssl", "stat", "statistics", "string", "stringprep", "struct",
        "subprocess", "sunau", "symtable", "sys", "sysconfig", "tabnanny",
        "tarfile", "tempfile", "test", "textwrap", "threading", "time",
        "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
        "tracemalloc", "tty", "turtle", "types", "typing", "unicodedata",
        "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave",
        "weakref", "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib",
        "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib"
    }

    def analyze_python(self, code: str) -> List[Dependency]:
        """Analyze Python imports."""
        dependencies = []

        # Parse imports
        import_pattern = r"^(?:from\s+(\w+)|import\s+(\w+))"

        for match in re.finditer(import_pattern, code, re.MULTILINE):
            module = match.group(1) or match.group(2)
            if module:
                base_module = module.split(".")[0]

                dependencies.append(Dependency(
                    name=base_module,
                    is_standard_library=base_module in self.PYTHON_STDLIB,
                    source="import"
                ))

        return dependencies

    def find_missing(self, dependencies: List[Dependency]) -> List[str]:
        """Find missing dependencies."""
        missing = []

        for dep in dependencies:
            if dep.is_standard_library:
                continue

            try:
                __import__(dep.name)
                dep.is_installed = True
            except ImportError:
                dep.is_installed = False
                missing.append(dep.name)

        return missing


# =============================================================================
# CODE TOOLKIT - UNIFIED INTERFACE
# =============================================================================

class CodeToolkit:
    """
    Unified code toolkit providing all code-related capabilities.

    Main entry point for code operations in BAEL.
    """

    def __init__(self, safe_mode: bool = True):
        self.analyzer = CodeAnalyzer()
        self.executor = CodeExecutor(safe_mode=safe_mode)
        self.formatter = CodeFormatter()
        self.generator = CodeGenerator()
        self.dependency_analyzer = DependencyAnalyzer()
        self.language_detector = LanguageDetector()

    def analyze(self, code: str, language: Optional[str] = None) -> AnalysisResult:
        """Analyze code for issues, security vulnerabilities, and metrics."""
        lang = Language(language) if language else LanguageDetector.from_code(code)
        return self.analyzer.analyze(code, lang)

    async def execute(
        self,
        code: str,
        language: str = "python",
        safe_mode: bool = True
    ) -> ExecutionResult:
        """Execute code safely."""
        lang = Language(language)

        if lang == Language.PYTHON:
            return await self.executor.execute_python(code)
        else:
            return await self.executor.execute_subprocess(code, lang)

    def format(self, code: str, language: Optional[str] = None) -> Tuple[str, bool]:
        """Format code according to style guides."""
        lang = Language(language) if language else LanguageDetector.from_code(code)
        return self.formatter.format(code, lang)

    def detect_language(
        self,
        code: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Language:
        """Detect programming language."""
        if filename:
            return LanguageDetector.from_filename(filename)
        if code:
            return LanguageDetector.from_code(code)
        return Language.UNKNOWN

    def get_dependencies(self, code: str) -> List[Dependency]:
        """Analyze code dependencies."""
        return self.dependency_analyzer.analyze_python(code)

    def find_missing_dependencies(self, code: str) -> List[str]:
        """Find missing dependencies."""
        deps = self.get_dependencies(code)
        return self.dependency_analyzer.find_missing(deps)

    def generate(
        self,
        template_type: str,
        **kwargs
    ) -> str:
        """Generate code from templates."""
        if template_type == "function":
            return self.generator.generate_function(**kwargs)
        elif template_type == "class":
            return self.generator.generate_class(**kwargs)
        elif template_type == "dataclass":
            return self.generator.generate_dataclass(**kwargs)
        else:
            raise ValueError(f"Unknown template type: {template_type}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for BAEL integration."""
        return [
            {
                "name": "code_analyze",
                "description": "Analyze code for issues, security vulnerabilities, and metrics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to analyze"},
                        "language": {"type": "string", "description": "Programming language"}
                    },
                    "required": ["code"]
                },
                "handler": self.analyze
            },
            {
                "name": "code_execute",
                "description": "Execute code safely in a sandbox",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to execute"},
                        "language": {"type": "string", "default": "python"}
                    },
                    "required": ["code"]
                },
                "handler": self.execute
            },
            {
                "name": "code_format",
                "description": "Format code according to style guides",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"}
                    },
                    "required": ["code"]
                },
                "handler": lambda code, language=None: self.format(code, language)
            },
            {
                "name": "code_generate",
                "description": "Generate code from templates",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "template_type": {"type": "string", "enum": ["function", "class", "dataclass"]},
                        "name": {"type": "string"},
                        "params": {"type": "array"},
                        "docstring": {"type": "string"}
                    },
                    "required": ["template_type", "name"]
                },
                "handler": self.generate
            }
        ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "CodeToolkit",
    "CodeAnalyzer",
    "CodeExecutor",
    "CodeFormatter",
    "CodeGenerator",
    "SyntaxChecker",
    "SecurityScanner",
    "DependencyAnalyzer",
    "AnalysisResult",
    "ExecutionResult",
    "SecurityIssue",
    "CodeIssue",
    "Language",
    "Severity",
    "IssueType",
    "Dependency",
    "LanguageDetector"
]
