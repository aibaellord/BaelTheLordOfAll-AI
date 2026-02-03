"""
BAEL - Universal Tool Executor
Execute tools across multiple runtimes and environments.

Supports:
- Python code execution
- Shell commands
- JavaScript/Node.js
- API calls
- Database queries
- File operations
- Browser automation
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class ExecutionRuntime(Enum):
    """Available execution runtimes."""
    PYTHON = "python"
    SHELL = "shell"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    HTTP = "http"
    SQL = "sql"
    GRAPHQL = "graphql"
    FILE = "file"
    BROWSER = "browser"


class ExecutionStatus(Enum):
    """Status of execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SecurityLevel(Enum):
    """Security level for execution."""
    UNRESTRICTED = "unrestricted"
    SANDBOXED = "sandboxed"
    RESTRICTED = "restricted"
    READ_ONLY = "read_only"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExecutionContext:
    """Context for code execution."""
    runtime: ExecutionRuntime
    security_level: SecurityLevel = SecurityLevel.SANDBOXED
    timeout: int = 30  # seconds
    max_output_size: int = 1024 * 1024  # 1MB
    working_dir: Optional[Path] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    allowed_modules: Optional[Set[str]] = None
    blocked_modules: Optional[Set[str]] = None


@dataclass
class ExecutionResult:
    """Result of code execution."""
    id: str
    runtime: ExecutionRuntime
    status: ExecutionStatus
    output: str = ""
    error: str = ""
    return_value: Any = None
    duration_ms: float = 0.0
    memory_used: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "runtime": self.runtime.value,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "return_value": str(self.return_value),
            "duration_ms": self.duration_ms,
            "memory_used": self.memory_used,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ToolDefinition:
    """Definition of a tool."""
    name: str
    description: str
    runtime: ExecutionRuntime
    code: str
    parameters: Dict[str, Dict[str, Any]]  # name -> {type, description, required}
    returns: Dict[str, Any]  # {type, description}
    examples: List[Dict[str, Any]] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = "bael"
    tags: List[str] = field(default_factory=list)


# =============================================================================
# RUNTIME EXECUTORS
# =============================================================================

class RuntimeExecutor(ABC):
    """Base class for runtime executors."""

    @abstractmethod
    async def execute(
        self,
        code: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute code and return result."""
        pass

    @abstractmethod
    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate code before execution."""
        pass


class PythonExecutor(RuntimeExecutor):
    """Execute Python code."""

    BLOCKED_IMPORTS = {
        "os.system", "subprocess", "socket",
        "ctypes", "multiprocessing", "threading"
    }

    RESTRICTED_BUILTINS = {
        "exec", "eval", "compile", "__import__",
        "open", "input", "breakpoint"
    }

    async def execute(
        self,
        code: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute Python code."""
        exec_id = hashlib.md5(f"{code}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        start_time = datetime.now()

        try:
            # Validate first
            valid, error = self.validate(code)
            if not valid:
                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.PYTHON,
                    status=ExecutionStatus.FAILED,
                    error=error or "Validation failed"
                )

            # Apply security restrictions
            if context.security_level != SecurityLevel.UNRESTRICTED:
                code = self._apply_restrictions(code, context)

            # Create safe globals
            safe_globals = self._create_safe_globals(context)

            # Capture output
            import io
            from contextlib import redirect_stderr, redirect_stdout

            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            result_value = None

            # Execute with timeout
            async def run_code():
                nonlocal result_value
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec_result = exec(code, safe_globals)
                    # Check for return value in globals
                    if "__result__" in safe_globals:
                        result_value = safe_globals["__result__"]
                    return exec_result

            try:
                await asyncio.wait_for(run_code(), timeout=context.timeout)
            except asyncio.TimeoutError:
                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.PYTHON,
                    status=ExecutionStatus.TIMEOUT,
                    error=f"Execution timed out after {context.timeout}s",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            output = stdout_capture.getvalue()
            error_output = stderr_capture.getvalue()

            # Truncate if too large
            if len(output) > context.max_output_size:
                output = output[:context.max_output_size] + "\n...[truncated]"

            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.PYTHON,
                status=ExecutionStatus.SUCCESS,
                output=output,
                error=error_output,
                return_value=result_value,
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

        except Exception as e:
            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.PYTHON,
                status=ExecutionStatus.FAILED,
                error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate Python code."""
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        return True, None

    def _apply_restrictions(
        self,
        code: str,
        context: ExecutionContext
    ) -> str:
        """Apply security restrictions to code."""
        # Add import restrictions
        if context.blocked_modules:
            for module in context.blocked_modules:
                if f"import {module}" in code or f"from {module}" in code:
                    raise SecurityError(f"Module {module} is blocked")

        return code

    def _create_safe_globals(
        self,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Create safe globals for execution."""
        import builtins

        safe_builtins = {}
        for name in dir(builtins):
            if not name.startswith("_") and name not in self.RESTRICTED_BUILTINS:
                safe_builtins[name] = getattr(builtins, name)

        # Add safe open if not read-only
        if context.security_level != SecurityLevel.READ_ONLY:
            safe_builtins["open"] = open

        return {
            "__builtins__": safe_builtins,
            "__name__": "__main__",
            "__doc__": None
        }


class ShellExecutor(RuntimeExecutor):
    """Execute shell commands."""

    DANGEROUS_COMMANDS = {
        "rm -rf /", "dd if=", "mkfs", ":(){ :|:& };:",
        "> /dev/sda", "wget", "curl | bash", "chmod 777"
    }

    async def execute(
        self,
        code: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute shell command."""
        exec_id = hashlib.md5(f"{code}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        start_time = datetime.now()

        try:
            # Validate
            valid, error = self.validate(code)
            if not valid:
                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.SHELL,
                    status=ExecutionStatus.FAILED,
                    error=error or "Validation failed"
                )

            # Set up environment
            env = os.environ.copy()
            env.update(context.env_vars)

            # Execute
            process = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(context.working_dir) if context.working_dir else None,
                env=env
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=context.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.SHELL,
                    status=ExecutionStatus.TIMEOUT,
                    error=f"Command timed out after {context.timeout}s"
                )

            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.SHELL,
                status=ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED,
                output=output,
                error=error_output,
                return_value=process.returncode,
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

        except Exception as e:
            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.SHELL,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate shell command."""
        code_lower = code.lower()

        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in code_lower:
                return False, f"Potentially dangerous command detected: {dangerous}"

        return True, None


class JavaScriptExecutor(RuntimeExecutor):
    """Execute JavaScript code using Node.js."""

    async def execute(
        self,
        code: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute JavaScript code."""
        exec_id = hashlib.md5(f"{code}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        start_time = datetime.now()

        try:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".js",
                delete=False
            ) as f:
                f.write(code)
                temp_path = f.name

            try:
                process = await asyncio.create_subprocess_exec(
                    "node", temp_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(context.working_dir) if context.working_dir else None
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=context.timeout
                )

                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.JAVASCRIPT,
                    status=ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED,
                    output=stdout.decode(),
                    error=stderr.decode(),
                    return_value=process.returncode,
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
            finally:
                os.unlink(temp_path)

        except FileNotFoundError:
            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.JAVASCRIPT,
                status=ExecutionStatus.FAILED,
                error="Node.js not found. Please install Node.js.",
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
        except Exception as e:
            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.JAVASCRIPT,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate JavaScript code."""
        # Basic validation - could use esprima or similar
        try:
            # Check for obvious issues
            if code.count("{") != code.count("}"):
                return False, "Mismatched braces"
            if code.count("(") != code.count(")"):
                return False, "Mismatched parentheses"
            return True, None
        except Exception as e:
            return False, str(e)


class HTTPExecutor(RuntimeExecutor):
    """Execute HTTP requests."""

    async def execute(
        self,
        code: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute HTTP request."""
        exec_id = hashlib.md5(f"{code}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        start_time = datetime.now()

        try:
            # Parse request specification
            spec = json.loads(code)

            method = spec.get("method", "GET").upper()
            url = spec["url"]
            headers = spec.get("headers", {})
            body = spec.get("body")

            # Use aiohttp if available, fallback to urllib
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method,
                        url,
                        headers=headers,
                        json=body if isinstance(body, dict) else None,
                        data=body if isinstance(body, str) else None,
                        timeout=aiohttp.ClientTimeout(total=context.timeout)
                    ) as response:
                        response_body = await response.text()

                        return ExecutionResult(
                            id=exec_id,
                            runtime=ExecutionRuntime.HTTP,
                            status=ExecutionStatus.SUCCESS,
                            output=response_body,
                            return_value=response.status,
                            duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                            metadata={
                                "status_code": response.status,
                                "headers": dict(response.headers)
                            }
                        )
            except ImportError:
                # Fallback to urllib
                import urllib.error
                import urllib.request

                req = urllib.request.Request(url, method=method)
                for key, value in headers.items():
                    req.add_header(key, value)

                if body:
                    req.data = json.dumps(body).encode() if isinstance(body, dict) else body.encode()

                try:
                    with urllib.request.urlopen(req, timeout=context.timeout) as response:
                        response_body = response.read().decode()

                        return ExecutionResult(
                            id=exec_id,
                            runtime=ExecutionRuntime.HTTP,
                            status=ExecutionStatus.SUCCESS,
                            output=response_body,
                            return_value=response.status,
                            duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                        )
                except urllib.error.HTTPError as e:
                    return ExecutionResult(
                        id=exec_id,
                        runtime=ExecutionRuntime.HTTP,
                        status=ExecutionStatus.FAILED,
                        error=f"HTTP Error: {e.code} {e.reason}",
                        duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                    )

        except json.JSONDecodeError:
            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.HTTP,
                status=ExecutionStatus.FAILED,
                error="Invalid JSON specification",
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
        except Exception as e:
            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.HTTP,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate HTTP request specification."""
        try:
            spec = json.loads(code)
            if "url" not in spec:
                return False, "Missing required field: url"
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"


class FileExecutor(RuntimeExecutor):
    """Execute file operations."""

    async def execute(
        self,
        code: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute file operation."""
        exec_id = hashlib.md5(f"{code}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        start_time = datetime.now()

        try:
            spec = json.loads(code)
            operation = spec.get("operation", "read")
            path = Path(spec["path"])

            # Security check
            if context.working_dir:
                try:
                    path.resolve().relative_to(context.working_dir.resolve())
                except ValueError:
                    return ExecutionResult(
                        id=exec_id,
                        runtime=ExecutionRuntime.FILE,
                        status=ExecutionStatus.FAILED,
                        error="Path traversal not allowed"
                    )

            if operation == "read":
                content = path.read_text()
                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.FILE,
                    status=ExecutionStatus.SUCCESS,
                    output=content,
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            elif operation == "write":
                if context.security_level == SecurityLevel.READ_ONLY:
                    return ExecutionResult(
                        id=exec_id,
                        runtime=ExecutionRuntime.FILE,
                        status=ExecutionStatus.FAILED,
                        error="Write not allowed in read-only mode"
                    )

                content = spec.get("content", "")
                path.write_text(content)
                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.FILE,
                    status=ExecutionStatus.SUCCESS,
                    output=f"Written {len(content)} bytes to {path}",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            elif operation == "list":
                if path.is_dir():
                    items = [str(p) for p in path.iterdir()]
                    return ExecutionResult(
                        id=exec_id,
                        runtime=ExecutionRuntime.FILE,
                        status=ExecutionStatus.SUCCESS,
                        output="\n".join(items),
                        return_value=items,
                        duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                    )
                else:
                    return ExecutionResult(
                        id=exec_id,
                        runtime=ExecutionRuntime.FILE,
                        status=ExecutionStatus.FAILED,
                        error=f"{path} is not a directory"
                    )

            elif operation == "delete":
                if context.security_level in [SecurityLevel.READ_ONLY, SecurityLevel.RESTRICTED]:
                    return ExecutionResult(
                        id=exec_id,
                        runtime=ExecutionRuntime.FILE,
                        status=ExecutionStatus.FAILED,
                        error="Delete not allowed"
                    )

                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)

                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.FILE,
                    status=ExecutionStatus.SUCCESS,
                    output=f"Deleted {path}",
                    duration_ms=(datetime.now() - start_time).total_seconds() * 1000
                )

            else:
                return ExecutionResult(
                    id=exec_id,
                    runtime=ExecutionRuntime.FILE,
                    status=ExecutionStatus.FAILED,
                    error=f"Unknown operation: {operation}"
                )

        except Exception as e:
            return ExecutionResult(
                id=exec_id,
                runtime=ExecutionRuntime.FILE,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate file operation specification."""
        try:
            spec = json.loads(code)
            if "path" not in spec:
                return False, "Missing required field: path"
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"


class SecurityError(Exception):
    """Security violation error."""
    pass


# =============================================================================
# TOOL EXECUTOR
# =============================================================================

class ToolExecutor:
    """Central tool execution engine."""

    def __init__(self):
        self.executors: Dict[ExecutionRuntime, RuntimeExecutor] = {
            ExecutionRuntime.PYTHON: PythonExecutor(),
            ExecutionRuntime.SHELL: ShellExecutor(),
            ExecutionRuntime.JAVASCRIPT: JavaScriptExecutor(),
            ExecutionRuntime.HTTP: HTTPExecutor(),
            ExecutionRuntime.FILE: FileExecutor(),
        }
        self.tools: Dict[str, ToolDefinition] = {}
        self.execution_history: List[ExecutionResult] = []
        self.max_history = 1000

    def register_executor(
        self,
        runtime: ExecutionRuntime,
        executor: RuntimeExecutor
    ) -> None:
        """Register a custom executor."""
        self.executors[runtime] = executor

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    async def execute(
        self,
        runtime: ExecutionRuntime,
        code: str,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """Execute code with specified runtime."""
        if runtime not in self.executors:
            return ExecutionResult(
                id="error",
                runtime=runtime,
                status=ExecutionStatus.FAILED,
                error=f"No executor for runtime: {runtime.value}"
            )

        if context is None:
            context = ExecutionContext(runtime=runtime)

        executor = self.executors[runtime]
        result = await executor.execute(code, context)

        # Store in history
        self.execution_history.append(result)
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]

        return result

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """Execute a registered tool."""
        tool = self.tools.get(tool_name)
        if not tool:
            return ExecutionResult(
                id="error",
                runtime=ExecutionRuntime.PYTHON,
                status=ExecutionStatus.FAILED,
                error=f"Unknown tool: {tool_name}"
            )

        # Validate parameters
        for param_name, param_spec in tool.parameters.items():
            if param_spec.get("required", False) and param_name not in parameters:
                return ExecutionResult(
                    id="error",
                    runtime=tool.runtime,
                    status=ExecutionStatus.FAILED,
                    error=f"Missing required parameter: {param_name}"
                )

        # Inject parameters into code
        code = tool.code
        for param_name, param_value in parameters.items():
            placeholder = f"{{{param_name}}}"
            code = code.replace(placeholder, str(param_value))

        return await self.execute(tool.runtime, code, context)

    async def execute_python(
        self,
        code: str,
        security: SecurityLevel = SecurityLevel.SANDBOXED,
        timeout: int = 30
    ) -> ExecutionResult:
        """Convenience method for Python execution."""
        context = ExecutionContext(
            runtime=ExecutionRuntime.PYTHON,
            security_level=security,
            timeout=timeout
        )
        return await self.execute(ExecutionRuntime.PYTHON, code, context)

    async def execute_shell(
        self,
        command: str,
        timeout: int = 30,
        working_dir: Optional[Path] = None
    ) -> ExecutionResult:
        """Convenience method for shell execution."""
        context = ExecutionContext(
            runtime=ExecutionRuntime.SHELL,
            timeout=timeout,
            working_dir=working_dir
        )
        return await self.execute(ExecutionRuntime.SHELL, command, context)

    async def http_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        timeout: int = 30
    ) -> ExecutionResult:
        """Convenience method for HTTP requests."""
        spec = {
            "url": url,
            "method": method,
            "headers": headers or {},
            "body": body
        }
        context = ExecutionContext(
            runtime=ExecutionRuntime.HTTP,
            timeout=timeout
        )
        return await self.execute(ExecutionRuntime.HTTP, json.dumps(spec), context)

    async def read_file(self, path: str) -> ExecutionResult:
        """Read a file."""
        spec = {"operation": "read", "path": path}
        return await self.execute(
            ExecutionRuntime.FILE,
            json.dumps(spec),
            ExecutionContext(runtime=ExecutionRuntime.FILE)
        )

    async def write_file(self, path: str, content: str) -> ExecutionResult:
        """Write a file."""
        spec = {"operation": "write", "path": path, "content": content}
        return await self.execute(
            ExecutionRuntime.FILE,
            json.dumps(spec),
            ExecutionContext(
                runtime=ExecutionRuntime.FILE,
                security_level=SecurityLevel.SANDBOXED
            )
        )

    def get_history(
        self,
        runtime: Optional[ExecutionRuntime] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100
    ) -> List[ExecutionResult]:
        """Get execution history."""
        results = self.execution_history

        if runtime:
            results = [r for r in results if r.runtime == runtime]
        if status:
            results = [r for r in results if r.status == status]

        return results[-limit:]


# =============================================================================
# BUILT-IN TOOLS
# =============================================================================

def get_builtin_tools() -> List[ToolDefinition]:
    """Get list of built-in tools."""
    return [
        ToolDefinition(
            name="python_eval",
            description="Evaluate a Python expression and return the result",
            runtime=ExecutionRuntime.PYTHON,
            code="__result__ = {expression}",
            parameters={
                "expression": {
                    "type": "string",
                    "description": "Python expression to evaluate",
                    "required": True
                }
            },
            returns={"type": "any", "description": "Result of evaluation"},
            examples=[{"expression": "2 + 2", "result": 4}]
        ),
        ToolDefinition(
            name="shell_command",
            description="Execute a shell command",
            runtime=ExecutionRuntime.SHELL,
            code="{command}",
            parameters={
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                    "required": True
                }
            },
            returns={"type": "string", "description": "Command output"}
        ),
        ToolDefinition(
            name="http_get",
            description="Make an HTTP GET request",
            runtime=ExecutionRuntime.HTTP,
            code='{"method": "GET", "url": "{url}", "headers": {}}',
            parameters={
                "url": {
                    "type": "string",
                    "description": "URL to request",
                    "required": True
                }
            },
            returns={"type": "string", "description": "Response body"}
        ),
        ToolDefinition(
            name="read_file",
            description="Read contents of a file",
            runtime=ExecutionRuntime.FILE,
            code='{"operation": "read", "path": "{path}"}',
            parameters={
                "path": {
                    "type": "string",
                    "description": "Path to file",
                    "required": True
                }
            },
            returns={"type": "string", "description": "File contents"}
        ),
        ToolDefinition(
            name="list_directory",
            description="List contents of a directory",
            runtime=ExecutionRuntime.FILE,
            code='{"operation": "list", "path": "{path}"}',
            parameters={
                "path": {
                    "type": "string",
                    "description": "Path to directory",
                    "required": True
                }
            },
            returns={"type": "array", "description": "List of files and directories"}
        ),
    ]


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_execution():
    """Demonstrate tool execution."""
    executor = ToolExecutor()

    # Register built-in tools
    for tool in get_builtin_tools():
        executor.register_tool(tool)

    # Execute Python code
    result = await executor.execute_python("""
import math
__result__ = math.factorial(10)
print(f"10! = {__result__}")
""")
    print(f"Python result: {result.output}, return: {result.return_value}")

    # Execute shell command
    result = await executor.execute_shell("echo 'Hello from shell!'")
    print(f"Shell result: {result.output}")

    # Execute HTTP request
    result = await executor.http_request(
        "https://api.github.com/users/octocat",
        timeout=10
    )
    print(f"HTTP result: {result.status.value}, length: {len(result.output)}")

    # Execute registered tool
    result = await executor.execute_tool(
        "python_eval",
        {"expression": "sum(range(100))"}
    )
    print(f"Tool result: {result.return_value}")


if __name__ == "__main__":
    asyncio.run(example_execution())
