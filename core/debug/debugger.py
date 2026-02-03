"""
BAEL - Autonomous Debugger
AI-powered debugging with root cause analysis and fix generation.

Features:
- Error parsing and classification
- Stack trace analysis
- Variable inspection
- Root cause detection
- Automated fix suggestions
- Breakpoint management
"""

import asyncio
import hashlib
import logging
import re
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ErrorCategory(Enum):
    """Categories of errors."""
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    LOGIC = "logic"
    TYPE = "type"
    IMPORT = "import"
    ATTRIBUTE = "attribute"
    INDEX = "index"
    KEY = "key"
    VALUE = "value"
    FILE = "file"
    NETWORK = "network"
    MEMORY = "memory"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    ASSERTION = "assertion"
    UNKNOWN = "unknown"


class FixConfidence(Enum):
    """Confidence level for suggested fixes."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPECULATIVE = "speculative"


class DebugStrategy(Enum):
    """Debugging strategies."""
    TRACE = "trace"
    BISECT = "bisect"
    HYPOTHESIS = "hypothesis"
    ISOLATE = "isolate"
    COMPARE = "compare"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StackFrame:
    """A single stack frame."""
    file: str
    line: int
    function: str
    code: Optional[str] = None
    locals: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_traceback(cls, tb_frame: Any) -> "StackFrame":
        """Create from traceback frame."""
        return cls(
            file=tb_frame.tb_frame.f_code.co_filename,
            line=tb_frame.tb_lineno,
            function=tb_frame.tb_frame.f_code.co_name,
            locals=dict(tb_frame.tb_frame.f_locals)
        )


@dataclass
class ErrorInfo:
    """Parsed error information."""
    id: str
    type: str
    message: str
    category: ErrorCategory
    stack_trace: List[StackFrame]
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def origin(self) -> Optional[StackFrame]:
        """Get the originating stack frame."""
        return self.stack_trace[-1] if self.stack_trace else None


@dataclass
class FixSuggestion:
    """A suggested fix for an error."""
    id: str
    description: str
    code: str
    location: Tuple[str, int]  # file, line
    confidence: FixConfidence
    explanation: str
    side_effects: List[str] = field(default_factory=list)


@dataclass
class DebugSession:
    """A debugging session."""
    id: str
    error: ErrorInfo
    hypotheses: List[str]
    tested_hypotheses: List[Tuple[str, bool]]
    fixes: List[FixSuggestion]
    resolved: bool = False
    resolution: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None


# =============================================================================
# ERROR PARSER
# =============================================================================

class ErrorParser:
    """Parses error messages and stack traces."""

    # Error type to category mapping
    ERROR_CATEGORIES: Dict[str, ErrorCategory] = {
        "SyntaxError": ErrorCategory.SYNTAX,
        "IndentationError": ErrorCategory.SYNTAX,
        "TabError": ErrorCategory.SYNTAX,
        "TypeError": ErrorCategory.TYPE,
        "ValueError": ErrorCategory.VALUE,
        "IndexError": ErrorCategory.INDEX,
        "KeyError": ErrorCategory.KEY,
        "AttributeError": ErrorCategory.ATTRIBUTE,
        "ImportError": ErrorCategory.IMPORT,
        "ModuleNotFoundError": ErrorCategory.IMPORT,
        "FileNotFoundError": ErrorCategory.FILE,
        "IOError": ErrorCategory.FILE,
        "PermissionError": ErrorCategory.PERMISSION,
        "MemoryError": ErrorCategory.MEMORY,
        "TimeoutError": ErrorCategory.TIMEOUT,
        "ConnectionError": ErrorCategory.NETWORK,
        "AssertionError": ErrorCategory.ASSERTION,
        "RuntimeError": ErrorCategory.RUNTIME,
        "NameError": ErrorCategory.RUNTIME,
        "RecursionError": ErrorCategory.RUNTIME,
        "ZeroDivisionError": ErrorCategory.RUNTIME,
    }

    def parse_exception(
        self,
        exception: Exception,
        tb: Optional[Any] = None
    ) -> ErrorInfo:
        """Parse an exception into ErrorInfo."""
        error_type = type(exception).__name__
        error_message = str(exception)

        # Get stack trace
        if tb is None:
            tb = exception.__traceback__

        stack_frames = []
        current_tb = tb
        while current_tb:
            stack_frames.append(StackFrame.from_traceback(current_tb))
            current_tb = current_tb.tb_next

        # Determine category
        category = self.ERROR_CATEGORIES.get(error_type, ErrorCategory.UNKNOWN)

        error_id = hashlib.md5(
            f"{error_type}:{error_message}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        return ErrorInfo(
            id=error_id,
            type=error_type,
            message=error_message,
            category=category,
            stack_trace=stack_frames,
            timestamp=datetime.now()
        )

    def parse_traceback_string(self, traceback_str: str) -> ErrorInfo:
        """Parse a traceback string."""
        lines = traceback_str.strip().split("\n")

        # Parse the error type and message from last line
        error_line = lines[-1] if lines else ""
        match = re.match(r"(\w+Error|\w+Exception):\s*(.+)", error_line)

        if match:
            error_type = match.group(1)
            error_message = match.group(2)
        else:
            error_type = "UnknownError"
            error_message = error_line

        # Parse stack frames
        stack_frames = []
        frame_pattern = re.compile(
            r'File "([^"]+)", line (\d+), in (\w+)'
        )

        for i, line in enumerate(lines):
            match = frame_pattern.match(line.strip())
            if match:
                code_line = None
                if i + 1 < len(lines):
                    code_line = lines[i + 1].strip()

                stack_frames.append(StackFrame(
                    file=match.group(1),
                    line=int(match.group(2)),
                    function=match.group(3),
                    code=code_line
                ))

        category = self.ERROR_CATEGORIES.get(error_type, ErrorCategory.UNKNOWN)

        error_id = hashlib.md5(
            f"{error_type}:{error_message}".encode()
        ).hexdigest()[:12]

        return ErrorInfo(
            id=error_id,
            type=error_type,
            message=error_message,
            category=category,
            stack_trace=stack_frames,
            timestamp=datetime.now()
        )


# =============================================================================
# ROOT CAUSE ANALYZER
# =============================================================================

class RootCauseAnalyzer:
    """Analyzes errors to find root causes."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client
        self.common_patterns: Dict[ErrorCategory, List[Dict]] = {}
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load common error patterns."""
        self.common_patterns = {
            ErrorCategory.TYPE: [
                {
                    "pattern": r"'NoneType' object",
                    "cause": "Attempting to use a None value",
                    "fix": "Add null check before using the variable"
                },
                {
                    "pattern": r"can't multiply sequence by non-int",
                    "cause": "String multiplication with non-integer",
                    "fix": "Convert to integer using int()"
                },
                {
                    "pattern": r"unsupported operand type",
                    "cause": "Operation between incompatible types",
                    "fix": "Check and convert types before operation"
                }
            ],
            ErrorCategory.ATTRIBUTE: [
                {
                    "pattern": r"'NoneType' object has no attribute",
                    "cause": "Calling method on None",
                    "fix": "Ensure object is not None before access"
                },
                {
                    "pattern": r"'(\w+)' object has no attribute '(\w+)'",
                    "cause": "Incorrect attribute name or object type",
                    "fix": "Verify attribute name and object type"
                }
            ],
            ErrorCategory.INDEX: [
                {
                    "pattern": r"list index out of range",
                    "cause": "Accessing index beyond list length",
                    "fix": "Check list length before accessing"
                }
            ],
            ErrorCategory.KEY: [
                {
                    "pattern": r"KeyError: '(\w+)'",
                    "cause": "Dictionary key does not exist",
                    "fix": "Use .get() method or check key existence"
                }
            ],
            ErrorCategory.IMPORT: [
                {
                    "pattern": r"No module named '(\w+)'",
                    "cause": "Module not installed or incorrect name",
                    "fix": "Install module or fix import path"
                }
            ],
            ErrorCategory.FILE: [
                {
                    "pattern": r"No such file or directory",
                    "cause": "File path is incorrect or file doesn't exist",
                    "fix": "Verify file path and ensure file exists"
                }
            ],
            ErrorCategory.SYNTAX: [
                {
                    "pattern": r"unexpected EOF",
                    "cause": "Missing closing bracket or quote",
                    "fix": "Add missing closing character"
                },
                {
                    "pattern": r"invalid syntax",
                    "cause": "Python syntax error",
                    "fix": "Review syntax at indicated line"
                }
            ]
        }

    def analyze(self, error: ErrorInfo) -> Dict[str, Any]:
        """Analyze error for root cause."""
        analysis = {
            "error_id": error.id,
            "category": error.category.value,
            "hypotheses": [],
            "likely_cause": None,
            "suggested_fixes": [],
            "related_variables": [],
            "affected_scope": None
        }

        # Check against known patterns
        patterns = self.common_patterns.get(error.category, [])
        for pattern in patterns:
            if re.search(pattern["pattern"], error.message, re.IGNORECASE):
                analysis["likely_cause"] = pattern["cause"]
                analysis["suggested_fixes"].append(pattern["fix"])
                break

        # Analyze origin frame
        if error.origin:
            analysis["affected_scope"] = error.origin.function

            # Check local variables
            for var_name, var_value in error.origin.locals.items():
                if var_value is None:
                    analysis["related_variables"].append({
                        "name": var_name,
                        "value": "None",
                        "suspicious": True
                    })
                else:
                    analysis["related_variables"].append({
                        "name": var_name,
                        "value": repr(var_value)[:50],
                        "suspicious": False
                    })

        # Generate hypotheses
        analysis["hypotheses"] = self._generate_hypotheses(error, analysis)

        return analysis

    def _generate_hypotheses(
        self,
        error: ErrorInfo,
        analysis: Dict
    ) -> List[str]:
        """Generate debugging hypotheses."""
        hypotheses = []

        if error.category == ErrorCategory.TYPE:
            hypotheses.extend([
                "Variable may have unexpected type due to function return",
                "Type conversion may be missing",
                "Input validation may be insufficient"
            ])
        elif error.category == ErrorCategory.ATTRIBUTE:
            hypotheses.extend([
                "Object may not be initialized properly",
                "Wrong object type passed to function",
                "Typo in attribute name"
            ])
        elif error.category == ErrorCategory.INDEX:
            hypotheses.extend([
                "Loop bounds may be incorrect",
                "List may be empty or smaller than expected",
                "Off-by-one error"
            ])
        elif error.category == ErrorCategory.KEY:
            hypotheses.extend([
                "Dictionary key may have typo",
                "Key may be generated differently than expected",
                "Data may not contain expected structure"
            ])
        elif error.category == ErrorCategory.IMPORT:
            hypotheses.extend([
                "Package not installed in current environment",
                "Circular import causing issue",
                "Module path incorrect"
            ])

        # Add generic hypotheses
        if analysis.get("related_variables"):
            null_vars = [v["name"] for v in analysis["related_variables"] if v.get("suspicious")]
            if null_vars:
                hypotheses.append(f"Variables might be None: {', '.join(null_vars)}")

        return hypotheses


# =============================================================================
# FIX GENERATOR
# =============================================================================

class FixGenerator:
    """Generates fix suggestions for errors."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    async def generate_fixes(
        self,
        error: ErrorInfo,
        source_code: Optional[str] = None
    ) -> List[FixSuggestion]:
        """Generate fix suggestions."""
        fixes = []

        # Generate rule-based fixes
        rule_fixes = self._generate_rule_based_fixes(error)
        fixes.extend(rule_fixes)

        # Generate AI-powered fixes
        if self.llm_client and source_code:
            ai_fixes = await self._generate_ai_fixes(error, source_code)
            fixes.extend(ai_fixes)

        return fixes

    def _generate_rule_based_fixes(self, error: ErrorInfo) -> List[FixSuggestion]:
        """Generate fixes based on error patterns."""
        fixes = []

        if error.category == ErrorCategory.TYPE and "NoneType" in error.message:
            if error.origin:
                fixes.append(FixSuggestion(
                    id=f"fix_{error.id}_1",
                    description="Add None check",
                    code=f"if variable is not None:\n    # your code",
                    location=(error.origin.file, error.origin.line),
                    confidence=FixConfidence.HIGH,
                    explanation="Wrap code in None check to prevent NoneType error"
                ))

        elif error.category == ErrorCategory.KEY:
            match = re.search(r"KeyError: ['\"]?(\w+)['\"]?", error.message)
            if match and error.origin:
                key = match.group(1)
                fixes.append(FixSuggestion(
                    id=f"fix_{error.id}_1",
                    description="Use .get() with default",
                    code=f"value = dictionary.get('{key}', default_value)",
                    location=(error.origin.file, error.origin.line),
                    confidence=FixConfidence.HIGH,
                    explanation="Use dict.get() to provide default when key missing"
                ))
                fixes.append(FixSuggestion(
                    id=f"fix_{error.id}_2",
                    description="Check key existence",
                    code=f"if '{key}' in dictionary:\n    value = dictionary['{key}']",
                    location=(error.origin.file, error.origin.line),
                    confidence=FixConfidence.HIGH,
                    explanation="Check if key exists before accessing"
                ))

        elif error.category == ErrorCategory.INDEX:
            if error.origin:
                fixes.append(FixSuggestion(
                    id=f"fix_{error.id}_1",
                    description="Add bounds check",
                    code="if index < len(my_list):\n    value = my_list[index]",
                    location=(error.origin.file, error.origin.line),
                    confidence=FixConfidence.HIGH,
                    explanation="Check index is within bounds before accessing"
                ))
                fixes.append(FixSuggestion(
                    id=f"fix_{error.id}_2",
                    description="Use try-except",
                    code="try:\n    value = my_list[index]\nexcept IndexError:\n    value = None",
                    location=(error.origin.file, error.origin.line),
                    confidence=FixConfidence.MEDIUM,
                    explanation="Catch IndexError and handle gracefully"
                ))

        elif error.category == ErrorCategory.ATTRIBUTE:
            match = re.search(r"has no attribute '(\w+)'", error.message)
            if match and error.origin:
                attr = match.group(1)
                fixes.append(FixSuggestion(
                    id=f"fix_{error.id}_1",
                    description="Check attribute with hasattr()",
                    code=f"if hasattr(obj, '{attr}'):\n    value = obj.{attr}",
                    location=(error.origin.file, error.origin.line),
                    confidence=FixConfidence.MEDIUM,
                    explanation="Verify attribute exists before accessing"
                ))
                fixes.append(FixSuggestion(
                    id=f"fix_{error.id}_2",
                    description="Use getattr() with default",
                    code=f"value = getattr(obj, '{attr}', default_value)",
                    location=(error.origin.file, error.origin.line),
                    confidence=FixConfidence.MEDIUM,
                    explanation="Use getattr() to safely get attribute with fallback"
                ))

        elif error.category == ErrorCategory.IMPORT:
            match = re.search(r"No module named '([^']+)'", error.message)
            if match:
                module = match.group(1)
                fixes.append(FixSuggestion(
                    id=f"fix_{error.id}_1",
                    description=f"Install missing module",
                    code=f"pip install {module}",
                    location=("terminal", 0),
                    confidence=FixConfidence.HIGH,
                    explanation=f"Install the {module} package using pip"
                ))

        return fixes

    async def _generate_ai_fixes(
        self,
        error: ErrorInfo,
        source_code: str
    ) -> List[FixSuggestion]:
        """Generate AI-powered fixes."""
        if not self.llm_client:
            return []

        # Would call LLM here
        prompt = f"""Given this error:
{error.type}: {error.message}

At line {error.origin.line if error.origin else 'unknown'} in function {error.origin.function if error.origin else 'unknown'}

Source code context:
{source_code[:500]}

Suggest a fix with:
1. Description
2. Code change
3. Explanation"""

        # Return empty for now
        return []


# =============================================================================
# DEBUGGER
# =============================================================================

class Debugger:
    """Main debugging orchestrator."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.parser = ErrorParser()
        self.analyzer = RootCauseAnalyzer(llm_client)
        self.fix_generator = FixGenerator(llm_client)
        self.sessions: Dict[str, DebugSession] = {}
        self.breakpoints: Dict[str, List[int]] = {}  # file -> line numbers

    async def debug_exception(
        self,
        exception: Exception,
        source_code: Optional[str] = None
    ) -> DebugSession:
        """Debug an exception."""
        # Parse error
        error = self.parser.parse_exception(exception)

        # Analyze
        analysis = self.analyzer.analyze(error)

        # Generate fixes
        fixes = await self.fix_generator.generate_fixes(error, source_code)

        # Create session
        session = DebugSession(
            id=error.id,
            error=error,
            hypotheses=analysis["hypotheses"],
            tested_hypotheses=[],
            fixes=fixes
        )

        self.sessions[session.id] = session

        return session

    async def debug_traceback(
        self,
        traceback_str: str,
        source_code: Optional[str] = None
    ) -> DebugSession:
        """Debug from traceback string."""
        error = self.parser.parse_traceback_string(traceback_str)
        analysis = self.analyzer.analyze(error)
        fixes = await self.fix_generator.generate_fixes(error, source_code)

        session = DebugSession(
            id=error.id,
            error=error,
            hypotheses=analysis["hypotheses"],
            tested_hypotheses=[],
            fixes=fixes
        )

        self.sessions[session.id] = session

        return session

    def set_breakpoint(self, file: str, line: int) -> None:
        """Set a breakpoint."""
        if file not in self.breakpoints:
            self.breakpoints[file] = []
        if line not in self.breakpoints[file]:
            self.breakpoints[file].append(line)
            logger.info(f"Breakpoint set: {file}:{line}")

    def remove_breakpoint(self, file: str, line: int) -> None:
        """Remove a breakpoint."""
        if file in self.breakpoints and line in self.breakpoints[file]:
            self.breakpoints[file].remove(line)

    def test_hypothesis(
        self,
        session_id: str,
        hypothesis: str,
        result: bool
    ) -> None:
        """Record hypothesis test result."""
        session = self.sessions.get(session_id)
        if session:
            session.tested_hypotheses.append((hypothesis, result))

    def mark_resolved(
        self,
        session_id: str,
        resolution: str
    ) -> None:
        """Mark session as resolved."""
        session = self.sessions.get(session_id)
        if session:
            session.resolved = True
            session.resolution = resolution
            session.ended_at = datetime.now()

    def format_session(self, session: DebugSession) -> str:
        """Format debug session for display."""
        lines = [
            "=" * 60,
            "DEBUG SESSION",
            "=" * 60,
            f"Error: {session.error.type}",
            f"Message: {session.error.message}",
            f"Category: {session.error.category.value}",
            "",
            "STACK TRACE:"
        ]

        for i, frame in enumerate(session.error.stack_trace):
            lines.append(f"  {i+1}. {frame.file}:{frame.line} in {frame.function}")
            if frame.code:
                lines.append(f"     > {frame.code}")

        lines.extend([
            "",
            "HYPOTHESES:"
        ])

        for hyp in session.hypotheses:
            status = ""
            for tested_hyp, result in session.tested_hypotheses:
                if tested_hyp == hyp:
                    status = " ✓" if result else " ✗"
                    break
            lines.append(f"  • {hyp}{status}")

        if session.fixes:
            lines.extend([
                "",
                "SUGGESTED FIXES:"
            ])
            for i, fix in enumerate(session.fixes, 1):
                lines.append(f"  {i}. [{fix.confidence.value}] {fix.description}")
                lines.append(f"     {fix.explanation}")

        if session.resolved:
            lines.extend([
                "",
                f"RESOLVED: {session.resolution}"
            ])

        return "\n".join(lines)


# =============================================================================
# CONTEXT MANAGER FOR AUTO-DEBUG
# =============================================================================

class AutoDebug:
    """Context manager for automatic debugging."""

    def __init__(self, debugger: Debugger):
        self.debugger = debugger
        self.session: Optional[DebugSession] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.session = await self.debugger.debug_exception(exc_val, None)
            logger.error(self.debugger.format_session(self.session))
        return False  # Don't suppress the exception


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_debug():
    """Demonstrate debugging capabilities."""
    debugger = Debugger()

    # Debug from traceback string
    traceback_str = '''Traceback (most recent call last):
  File "example.py", line 10, in main
    result = process_data(data)
  File "example.py", line 5, in process_data
    return data["missing_key"]
KeyError: 'missing_key'
'''

    session = await debugger.debug_traceback(traceback_str)
    print(debugger.format_session(session))

    # Debug live exception
    try:
        result = {"a": 1}["b"]
    except Exception as e:
        session2 = await debugger.debug_exception(e)
        print("\n" + debugger.format_session(session2))


if __name__ == "__main__":
    asyncio.run(example_debug())
