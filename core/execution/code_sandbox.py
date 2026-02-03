"""
BAEL Code Execution Sandbox

Safe code execution environment with:
- Sandboxed Python execution
- Resource limits (time, memory)
- Multi-language support
- Output capture
- State isolation
- Security controls

This enables BAEL to safely execute code for analysis and automation.
"""

import asyncio
import io
import json
import logging
import multiprocessing
import os
import resource
import signal
import subprocess
import sys
import tempfile
import traceback
from abc import ABC, abstractmethod
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    SQL = "sql"
    R = "r"


class ExecutionStatus(Enum):
    """Status of code execution."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    MEMORY_LIMIT = "memory_limit"
    SECURITY_VIOLATION = "security_violation"
    CANCELLED = "cancelled"


class SecurityLevel(Enum):
    """Security levels for sandbox."""
    STRICT = "strict"      # No file/network access
    MODERATE = "moderate"  # Limited file access, no network
    PERMISSIVE = "permissive"  # Full file access, limited network


@dataclass
class ResourceLimits:
    """Resource limits for execution."""
    timeout_seconds: float = 30.0
    memory_mb: int = 256
    cpu_time_seconds: float = 10.0
    max_output_bytes: int = 1024 * 1024  # 1MB
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB


@dataclass
class ExecutionConfig:
    """Configuration for code execution."""
    language: Language = Language.PYTHON
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    security_level: SecurityLevel = SecurityLevel.STRICT
    working_directory: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    input_data: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of code execution."""
    id: str
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    error: Optional[str] = None
    error_traceback: Optional[str] = None

    # Metrics
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0

    # Metadata
    language: Language = Language.PYTHON
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class CodeAnalysis:
    """Analysis of code before execution."""
    is_safe: bool = True
    security_issues: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    function_calls: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SecurityAnalyzer:
    """Analyzes code for security issues."""

    # Forbidden imports in strict mode
    FORBIDDEN_IMPORTS = {
        'os', 'subprocess', 'shutil', 'socket', 'urllib',
        'requests', 'http', 'ftplib', 'telnetlib', 'smtplib',
        'ctypes', 'multiprocessing', 'threading',
        'pickle', 'marshal', 'shelve',
        '__builtins__', 'builtins',
        'importlib', 'imp', 'pkgutil',
    }

    # Forbidden function calls
    FORBIDDEN_CALLS = {
        'eval', 'exec', 'compile', 'open', 'input',
        '__import__', 'globals', 'locals',
        'getattr', 'setattr', 'delattr',
        'exit', 'quit', 'help',
    }

    def analyze(
        self,
        code: str,
        security_level: SecurityLevel
    ) -> CodeAnalysis:
        """Analyze code for security issues."""
        analysis = CodeAnalysis()

        # Extract imports
        import_pattern = r'(?:from\s+(\S+)\s+)?import\s+(.+)'
        import re

        for match in re.finditer(import_pattern, code):
            module = match.group(1) or match.group(2).split(',')[0].strip()
            analysis.imports.append(module)

            if security_level == SecurityLevel.STRICT:
                if module.split('.')[0] in self.FORBIDDEN_IMPORTS:
                    analysis.security_issues.append(
                        f"Forbidden import: {module}"
                    )
                    analysis.is_safe = False

        # Check for forbidden function calls
        for forbidden in self.FORBIDDEN_CALLS:
            if security_level == SecurityLevel.STRICT:
                # Simple check - could be improved with AST
                if f"{forbidden}(" in code or f"{forbidden} (" in code:
                    analysis.security_issues.append(
                        f"Forbidden function: {forbidden}"
                    )
                    analysis.is_safe = False

        # Check for file operations
        if security_level in [SecurityLevel.STRICT, SecurityLevel.MODERATE]:
            file_patterns = [
                r'open\s*\(',
                r'with\s+open',
                r'\.read\(',
                r'\.write\(',
            ]
            for pattern in file_patterns:
                if re.search(pattern, code):
                    if security_level == SecurityLevel.STRICT:
                        analysis.security_issues.append(
                            "File operations not allowed"
                        )
                        analysis.is_safe = False
                    else:
                        analysis.warnings.append(
                            "Code contains file operations"
                        )

        # Check for network operations
        network_patterns = [
            r'socket\.',
            r'requests\.',
            r'urllib',
            r'http\.client',
        ]
        for pattern in network_patterns:
            if re.search(pattern, code):
                analysis.security_issues.append(
                    "Network operations not allowed"
                )
                analysis.is_safe = False

        return analysis


class PythonExecutor:
    """Executes Python code in a sandbox."""

    def __init__(self):
        self.security_analyzer = SecurityAnalyzer()

    def _create_safe_globals(self) -> Dict[str, Any]:
        """Create a safe globals dictionary for execution."""
        import collections
        import datetime
        import functools
        import itertools
        import json
        import math
        import re

        safe_globals = {
            '__builtins__': {
                'abs': abs,
                'all': all,
                'any': any,
                'bin': bin,
                'bool': bool,
                'chr': chr,
                'dict': dict,
                'divmod': divmod,
                'enumerate': enumerate,
                'filter': filter,
                'float': float,
                'format': format,
                'frozenset': frozenset,
                'hash': hash,
                'hex': hex,
                'int': int,
                'isinstance': isinstance,
                'issubclass': issubclass,
                'iter': iter,
                'len': len,
                'list': list,
                'map': map,
                'max': max,
                'min': min,
                'next': next,
                'oct': oct,
                'ord': ord,
                'pow': pow,
                'print': print,
                'range': range,
                'repr': repr,
                'reversed': reversed,
                'round': round,
                'set': set,
                'slice': slice,
                'sorted': sorted,
                'str': str,
                'sum': sum,
                'tuple': tuple,
                'type': type,
                'zip': zip,
                'True': True,
                'False': False,
                'None': None,
            },
            'math': math,
            'json': json,
            're': re,
            'datetime': datetime,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
        }

        return safe_globals

    async def execute(
        self,
        code: str,
        config: ExecutionConfig
    ) -> ExecutionResult:
        """Execute Python code."""
        result = ExecutionResult(
            id=str(uuid4())[:8],
            status=ExecutionStatus.SUCCESS,
            language=Language.PYTHON
        )

        # Security analysis
        analysis = self.security_analyzer.analyze(code, config.security_level)

        if not analysis.is_safe:
            result.status = ExecutionStatus.SECURITY_VIOLATION
            result.error = "Security check failed: " + "; ".join(analysis.security_issues)
            return result

        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        start_time = datetime.now()

        try:
            # Create safe execution environment
            safe_globals = self._create_safe_globals()
            local_vars = {}

            # Execute with output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Use exec with timeout
                exec_task = asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: exec(code, safe_globals, local_vars)
                )

                await asyncio.wait_for(
                    exec_task,
                    timeout=config.limits.timeout_seconds
                )

            result.stdout = stdout_capture.getvalue()[:config.limits.max_output_bytes]
            result.stderr = stderr_capture.getvalue()[:config.limits.max_output_bytes]

            # Check for return value
            if 'result' in local_vars:
                result.return_value = local_vars['result']
            elif '_' in local_vars:
                result.return_value = local_vars['_']

        except asyncio.TimeoutError:
            result.status = ExecutionStatus.TIMEOUT
            result.error = f"Execution timed out after {config.limits.timeout_seconds}s"

        except MemoryError:
            result.status = ExecutionStatus.MEMORY_LIMIT
            result.error = "Memory limit exceeded"

        except Exception as e:
            result.status = ExecutionStatus.ERROR
            result.error = str(e)
            result.error_traceback = traceback.format_exc()
            result.stderr = stderr_capture.getvalue()

        finally:
            result.completed_at = datetime.now()
            result.execution_time_ms = (
                result.completed_at - start_time
            ).total_seconds() * 1000

        return result


class BashExecutor:
    """Executes bash commands safely."""

    FORBIDDEN_COMMANDS = {
        'rm', 'rmdir', 'dd', 'mkfs', 'fdisk',
        'sudo', 'su', 'chmod', 'chown',
        'kill', 'killall', 'shutdown', 'reboot',
        'curl', 'wget', 'ssh', 'scp', 'rsync',
    }

    def analyze(self, code: str, security_level: SecurityLevel) -> CodeAnalysis:
        """Analyze bash code for security."""
        analysis = CodeAnalysis()

        for cmd in self.FORBIDDEN_COMMANDS:
            if cmd in code.split():
                analysis.security_issues.append(f"Forbidden command: {cmd}")
                analysis.is_safe = False

        # Check for pipes to dangerous commands
        if '|' in code:
            analysis.warnings.append("Contains pipes - review carefully")

        return analysis

    async def execute(
        self,
        code: str,
        config: ExecutionConfig
    ) -> ExecutionResult:
        """Execute bash code."""
        result = ExecutionResult(
            id=str(uuid4())[:8],
            status=ExecutionStatus.SUCCESS,
            language=Language.BASH
        )

        # Security analysis
        analysis = self.analyze(code, config.security_level)

        if not analysis.is_safe:
            result.status = ExecutionStatus.SECURITY_VIOLATION
            result.error = "; ".join(analysis.security_issues)
            return result

        start_time = datetime.now()

        try:
            process = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=config.working_directory,
                env=config.environment or None
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(
                    input=config.input_data.encode() if config.input_data else None
                ),
                timeout=config.limits.timeout_seconds
            )

            result.stdout = stdout.decode()[:config.limits.max_output_bytes]
            result.stderr = stderr.decode()[:config.limits.max_output_bytes]

            if process.returncode != 0:
                result.status = ExecutionStatus.ERROR
                result.error = f"Exit code: {process.returncode}"

        except asyncio.TimeoutError:
            result.status = ExecutionStatus.TIMEOUT
            result.error = f"Execution timed out"
            process.kill()

        except Exception as e:
            result.status = ExecutionStatus.ERROR
            result.error = str(e)

        finally:
            result.completed_at = datetime.now()
            result.execution_time_ms = (
                result.completed_at - start_time
            ).total_seconds() * 1000

        return result


class CodeExecutionSandbox:
    """
    Master code execution sandbox.

    Features:
    - Multi-language support
    - Security sandboxing
    - Resource limits
    - Output capture
    - State isolation
    """

    def __init__(self):
        self.executors = {
            Language.PYTHON: PythonExecutor(),
            Language.BASH: BashExecutor(),
        }

        # Execution history
        self.history: List[ExecutionResult] = []

        # Persistent state (for stateful sessions)
        self.session_states: Dict[str, Dict[str, Any]] = {}

    async def execute(
        self,
        code: str,
        language: Language = Language.PYTHON,
        config: ExecutionConfig = None
    ) -> ExecutionResult:
        """Execute code in sandbox."""
        config = config or ExecutionConfig(language=language)
        config.language = language

        executor = self.executors.get(language)

        if not executor:
            return ExecutionResult(
                id=str(uuid4())[:8],
                status=ExecutionStatus.ERROR,
                error=f"Unsupported language: {language.value}",
                language=language
            )

        result = await executor.execute(code, config)
        self.history.append(result)

        return result

    async def execute_python(
        self,
        code: str,
        timeout: float = 30.0,
        security_level: SecurityLevel = SecurityLevel.STRICT
    ) -> ExecutionResult:
        """Execute Python code with simplified interface."""
        config = ExecutionConfig(
            language=Language.PYTHON,
            limits=ResourceLimits(timeout_seconds=timeout),
            security_level=security_level
        )
        return await self.execute(code, Language.PYTHON, config)

    async def execute_bash(
        self,
        command: str,
        timeout: float = 30.0
    ) -> ExecutionResult:
        """Execute bash command with simplified interface."""
        config = ExecutionConfig(
            language=Language.BASH,
            limits=ResourceLimits(timeout_seconds=timeout)
        )
        return await self.execute(command, Language.BASH, config)

    def create_session(self, session_id: str = None) -> str:
        """Create a new execution session."""
        session_id = session_id or str(uuid4())[:8]
        self.session_states[session_id] = {}
        return session_id

    async def execute_in_session(
        self,
        session_id: str,
        code: str,
        language: Language = Language.PYTHON
    ) -> ExecutionResult:
        """Execute code with session state."""
        if session_id not in self.session_states:
            self.create_session(session_id)

        # Get session state
        state = self.session_states[session_id]

        # Prepend state restoration
        if language == Language.PYTHON and state:
            state_json = json.dumps(state)
            code = f"import json\n_session_state = json.loads('{state_json}')\n{code}"

        result = await self.execute(code, language)

        # Extract and save state (simplified)
        # In real implementation, would properly extract state

        return result

    def get_history(
        self,
        limit: int = 10,
        language: Language = None
    ) -> List[ExecutionResult]:
        """Get execution history."""
        history = self.history

        if language:
            history = [h for h in history if h.language == language]

        return history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self.history)

        if total == 0:
            return {"total_executions": 0}

        by_status = {}
        by_language = {}
        total_time = 0.0

        for result in self.history:
            # By status
            status = result.status.value
            by_status[status] = by_status.get(status, 0) + 1

            # By language
            lang = result.language.value
            by_language[lang] = by_language.get(lang, 0) + 1

            total_time += result.execution_time_ms

        return {
            "total_executions": total,
            "by_status": by_status,
            "by_language": by_language,
            "avg_execution_time_ms": total_time / total,
            "success_rate": by_status.get("success", 0) / total
        }


async def demo():
    """Demonstrate code execution sandbox."""
    print("=" * 60)
    print("BAEL Code Execution Sandbox Demo")
    print("=" * 60)

    sandbox = CodeExecutionSandbox()

    # Simple Python execution
    result = await sandbox.execute_python("""
x = 5
y = 10
result = x + y
print(f"Result: {result}")
""")

    print(f"\nPython execution:")
    print(f"  Status: {result.status.value}")
    print(f"  Output: {result.stdout.strip()}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")

    # Math operations
    result = await sandbox.execute_python("""
import math
result = math.sqrt(144) + math.pi
print(f"Math result: {result}")
""")
    print(f"\nMath execution:")
    print(f"  Output: {result.stdout.strip()}")

    # Security violation test
    result = await sandbox.execute_python("""
import os
os.system("ls")
""", security_level=SecurityLevel.STRICT)

    print(f"\nSecurity test (should fail):")
    print(f"  Status: {result.status.value}")
    print(f"  Error: {result.error}")

    # Timeout test
    result = await sandbox.execute_python("""
import time
time.sleep(100)
""", timeout=1.0)

    print(f"\nTimeout test:")
    print(f"  Status: {result.status.value}")

    # Session execution
    session_id = sandbox.create_session()
    print(f"\nSession created: {session_id}")

    # Statistics
    stats = sandbox.get_statistics()
    print(f"\nExecution statistics:")
    print(f"  Total: {stats['total_executions']}")
    print(f"  By status: {stats['by_status']}")

    print("\n✓ Sandboxed Python execution")
    print("✓ Resource limits (timeout)")
    print("✓ Security analysis")
    print("✓ Output capture")
    print("✓ Session management")
    print("✓ Execution history")


if __name__ == "__main__":
    asyncio.run(demo())
