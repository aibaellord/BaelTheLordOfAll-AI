"""
BAEL - Sandbox Executor
Secure sandboxed code execution environment.

Features:
- Container-based isolation
- Resource limits (CPU, memory, time)
- Network isolation
- Filesystem restrictions
- Multiple runtime support
- Output capture and streaming
"""

import asyncio
import hashlib
import json
import logging
import os
import resource
import shutil
import signal
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class SandboxType(Enum):
    """Types of sandbox environments."""
    SUBPROCESS = "subprocess"
    DOCKER = "docker"
    NSJAIL = "nsjail"
    FIREJAIL = "firejail"
    WASM = "wasm"


class ExecutionStatus(Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    KILLED = "killed"


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"
    RUBY = "ruby"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CPP = "cpp"
    C = "c"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ResourceLimits:
    """Resource limits for sandbox."""
    max_cpu_time: float = 30.0  # seconds
    max_wall_time: float = 60.0  # seconds
    max_memory_mb: int = 512  # megabytes
    max_processes: int = 10
    max_file_size_mb: int = 10  # megabytes
    max_output_size_mb: int = 5  # megabytes
    network_enabled: bool = False
    filesystem_read_only: bool = True


@dataclass
class ExecutionRequest:
    """Request to execute code."""
    code: str
    language: Language
    stdin: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    files: Dict[str, str] = field(default_factory=dict)
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    timeout: float = 30.0


@dataclass
class ExecutionResult:
    """Result of code execution."""
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    execution_time: float = 0.0
    memory_used_mb: float = 0.0
    error: Optional[str] = None
    files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "memory_used_mb": self.memory_used_mb,
            "error": self.error,
            "files": self.files
        }


# =============================================================================
# LANGUAGE RUNTIMES
# =============================================================================

class LanguageRuntime(ABC):
    """Abstract language runtime."""

    @property
    @abstractmethod
    def language(self) -> Language:
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        pass

    @abstractmethod
    def get_run_command(self, script_path: str, args: List[str]) -> List[str]:
        pass

    def prepare_code(self, code: str) -> str:
        """Prepare code for execution."""
        return code


class PythonRuntime(LanguageRuntime):
    """Python runtime."""

    @property
    def language(self) -> Language:
        return Language.PYTHON

    @property
    def file_extension(self) -> str:
        return ".py"

    def get_run_command(self, script_path: str, args: List[str]) -> List[str]:
        return ["python3", "-u", script_path] + args


class JavaScriptRuntime(LanguageRuntime):
    """JavaScript/Node.js runtime."""

    @property
    def language(self) -> Language:
        return Language.JAVASCRIPT

    @property
    def file_extension(self) -> str:
        return ".js"

    def get_run_command(self, script_path: str, args: List[str]) -> List[str]:
        return ["node", script_path] + args


class BashRuntime(LanguageRuntime):
    """Bash runtime."""

    @property
    def language(self) -> Language:
        return Language.BASH

    @property
    def file_extension(self) -> str:
        return ".sh"

    def get_run_command(self, script_path: str, args: List[str]) -> List[str]:
        return ["bash", script_path] + args


class RubyRuntime(LanguageRuntime):
    """Ruby runtime."""

    @property
    def language(self) -> Language:
        return Language.RUBY

    @property
    def file_extension(self) -> str:
        return ".rb"

    def get_run_command(self, script_path: str, args: List[str]) -> List[str]:
        return ["ruby", script_path] + args


class GoRuntime(LanguageRuntime):
    """Go runtime."""

    @property
    def language(self) -> Language:
        return Language.GO

    @property
    def file_extension(self) -> str:
        return ".go"

    def get_run_command(self, script_path: str, args: List[str]) -> List[str]:
        return ["go", "run", script_path] + args


# =============================================================================
# SANDBOX PROVIDERS
# =============================================================================

class SandboxProvider(ABC):
    """Abstract sandbox provider."""

    @property
    @abstractmethod
    def sandbox_type(self) -> SandboxType:
        pass

    @abstractmethod
    async def execute(
        self,
        request: ExecutionRequest,
        runtime: LanguageRuntime,
        work_dir: str
    ) -> ExecutionResult:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class SubprocessSandbox(SandboxProvider):
    """Subprocess-based sandbox with resource limits."""

    @property
    def sandbox_type(self) -> SandboxType:
        return SandboxType.SUBPROCESS

    def is_available(self) -> bool:
        return True

    async def execute(
        self,
        request: ExecutionRequest,
        runtime: LanguageRuntime,
        work_dir: str
    ) -> ExecutionResult:
        # Write script
        script_path = os.path.join(
            work_dir,
            f"script{runtime.file_extension}"
        )

        with open(script_path, 'w') as f:
            f.write(runtime.prepare_code(request.code))

        # Write additional files
        for filename, content in request.files.items():
            file_path = os.path.join(work_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)

        # Build command
        cmd = runtime.get_run_command(script_path, request.args)

        # Environment
        env = os.environ.copy()
        env.update(request.env)

        # Set resource limits via preexec_fn
        def set_limits():
            limits = request.limits

            # CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (int(limits.max_cpu_time), int(limits.max_cpu_time))
            )

            # Memory limit
            memory_bytes = limits.max_memory_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (memory_bytes, memory_bytes)
            )

            # File size limit
            file_bytes = limits.max_file_size_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_FSIZE,
                (file_bytes, file_bytes)
            )

            # Process limit
            resource.setrlimit(
                resource.RLIMIT_NPROC,
                (limits.max_processes, limits.max_processes)
            )

        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=env,
                preexec_fn=set_limits
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=request.stdin.encode()),
                    timeout=request.limits.max_wall_time
                )

                execution_time = time.time() - start_time

                return ExecutionResult(
                    status=ExecutionStatus.COMPLETED,
                    stdout=stdout.decode()[:1024 * 1024],  # Limit output
                    stderr=stderr.decode()[:1024 * 1024],
                    exit_code=process.returncode or 0,
                    execution_time=execution_time
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                return ExecutionResult(
                    status=ExecutionStatus.TIMEOUT,
                    error=f"Execution timed out after {request.limits.max_wall_time}s"
                )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=str(e)
            )


class DockerSandbox(SandboxProvider):
    """Docker container-based sandbox."""

    def __init__(self, image: str = "python:3.11-slim"):
        self.default_image = image
        self._language_images = {
            Language.PYTHON: "python:3.11-slim",
            Language.JAVASCRIPT: "node:20-slim",
            Language.RUBY: "ruby:3.2-slim",
            Language.GO: "golang:1.21-alpine",
            Language.BASH: "bash:5.2",
        }

    @property
    def sandbox_type(self) -> SandboxType:
        return SandboxType.DOCKER

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    async def execute(
        self,
        request: ExecutionRequest,
        runtime: LanguageRuntime,
        work_dir: str
    ) -> ExecutionResult:
        # Write script and files to work_dir
        script_path = os.path.join(
            work_dir,
            f"script{runtime.file_extension}"
        )

        with open(script_path, 'w') as f:
            f.write(runtime.prepare_code(request.code))

        for filename, content in request.files.items():
            file_path = os.path.join(work_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)

        # Build docker command
        image = self._language_images.get(
            request.language,
            self.default_image
        )

        limits = request.limits

        cmd = [
            "docker", "run",
            "--rm",  # Remove container after
            "--network=none" if not limits.network_enabled else "",
            f"--memory={limits.max_memory_mb}m",
            f"--cpus={1}",  # Single CPU
            "--read-only" if limits.filesystem_read_only else "",
            "-v", f"{work_dir}:/code:rw",
            "-w", "/code",
        ]

        # Add environment variables
        for key, value in request.env.items():
            cmd.extend(["-e", f"{key}={value}"])

        cmd.append(image)

        # Add run command
        run_cmd = runtime.get_run_command(
            f"/code/script{runtime.file_extension}",
            request.args
        )
        cmd.extend(run_cmd)

        # Filter empty strings
        cmd = [c for c in cmd if c]

        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=request.stdin.encode()),
                    timeout=limits.max_wall_time
                )

                execution_time = time.time() - start_time

                return ExecutionResult(
                    status=ExecutionStatus.COMPLETED,
                    stdout=stdout.decode()[:1024 * 1024],
                    stderr=stderr.decode()[:1024 * 1024],
                    exit_code=process.returncode or 0,
                    execution_time=execution_time
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                # Force kill any running container
                container_name = f"sandbox_{os.getpid()}"
                subprocess.run(
                    ["docker", "kill", container_name],
                    capture_output=True
                )

                return ExecutionResult(
                    status=ExecutionStatus.TIMEOUT,
                    error=f"Execution timed out after {limits.max_wall_time}s"
                )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=str(e)
            )


# =============================================================================
# SANDBOX EXECUTOR
# =============================================================================

class SandboxExecutor:
    """Main sandbox executor orchestrator."""

    def __init__(
        self,
        sandbox_type: SandboxType = SandboxType.SUBPROCESS,
        work_base_dir: Optional[str] = None
    ):
        self._providers: Dict[SandboxType, SandboxProvider] = {
            SandboxType.SUBPROCESS: SubprocessSandbox(),
            SandboxType.DOCKER: DockerSandbox()
        }

        self._runtimes: Dict[Language, LanguageRuntime] = {
            Language.PYTHON: PythonRuntime(),
            Language.JAVASCRIPT: JavaScriptRuntime(),
            Language.BASH: BashRuntime(),
            Language.RUBY: RubyRuntime(),
            Language.GO: GoRuntime()
        }

        self._default_sandbox = sandbox_type
        self._work_base_dir = work_base_dir or tempfile.gettempdir()
        self._executions: Dict[str, ExecutionResult] = {}

    def get_available_providers(self) -> List[SandboxType]:
        """Get list of available sandbox providers."""
        return [
            t for t, p in self._providers.items()
            if p.is_available()
        ]

    def get_supported_languages(self) -> List[Language]:
        """Get list of supported languages."""
        return list(self._runtimes.keys())

    async def execute(
        self,
        request: ExecutionRequest,
        sandbox_type: Optional[SandboxType] = None
    ) -> ExecutionResult:
        """Execute code in sandbox."""
        sandbox_type = sandbox_type or self._default_sandbox

        # Get provider
        provider = self._providers.get(sandbox_type)
        if not provider:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=f"Unknown sandbox type: {sandbox_type}"
            )

        if not provider.is_available():
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=f"Sandbox provider not available: {sandbox_type}"
            )

        # Get runtime
        runtime = self._runtimes.get(request.language)
        if not runtime:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=f"Unsupported language: {request.language}"
            )

        # Create work directory
        work_dir = tempfile.mkdtemp(
            prefix="bael_sandbox_",
            dir=self._work_base_dir
        )

        try:
            # Execute
            result = await provider.execute(request, runtime, work_dir)

            # Collect output files
            result.files = self._collect_output_files(work_dir, request)

            # Store result
            execution_id = hashlib.md5(
                request.code.encode()
            ).hexdigest()[:12]
            self._executions[execution_id] = result

            return result

        finally:
            # Cleanup
            try:
                shutil.rmtree(work_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup work dir: {e}")

    def _collect_output_files(
        self,
        work_dir: str,
        request: ExecutionRequest
    ) -> Dict[str, str]:
        """Collect output files from work directory."""
        output_files = {}

        for root, dirs, files in os.walk(work_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, work_dir)

                # Skip input files
                if rel_path.startswith("script"):
                    continue
                if rel_path in request.files:
                    continue

                # Read file content
                try:
                    with open(file_path, 'r') as f:
                        content = f.read(1024 * 1024)  # 1MB limit
                        output_files[rel_path] = content
                except Exception:
                    pass

        return output_files

    async def execute_python(
        self,
        code: str,
        timeout: float = 30.0,
        **kwargs
    ) -> ExecutionResult:
        """Execute Python code."""
        request = ExecutionRequest(
            code=code,
            language=Language.PYTHON,
            timeout=timeout,
            **kwargs
        )
        return await self.execute(request)

    async def execute_javascript(
        self,
        code: str,
        timeout: float = 30.0,
        **kwargs
    ) -> ExecutionResult:
        """Execute JavaScript code."""
        request = ExecutionRequest(
            code=code,
            language=Language.JAVASCRIPT,
            timeout=timeout,
            **kwargs
        )
        return await self.execute(request)

    async def execute_bash(
        self,
        code: str,
        timeout: float = 30.0,
        **kwargs
    ) -> ExecutionResult:
        """Execute Bash script."""
        request = ExecutionRequest(
            code=code,
            language=Language.BASH,
            timeout=timeout,
            **kwargs
        )
        return await self.execute(request)


# =============================================================================
# CODE VALIDATOR
# =============================================================================

class CodeValidator:
    """Validate code before execution."""

    def __init__(self):
        # Dangerous patterns by language
        self._dangerous_patterns: Dict[Language, List[str]] = {
            Language.PYTHON: [
                r"import\s+subprocess",
                r"os\.system\s*\(",
                r"os\.popen\s*\(",
                r"exec\s*\(",
                r"eval\s*\(",
                r"__import__\s*\(",
                r"open\s*\([^)]*['\"][waxr+]+['\"]",
                r"socket\.",
                r"urllib",
                r"requests\."
            ],
            Language.JAVASCRIPT: [
                r"child_process",
                r"fs\.writeFile",
                r"fs\.unlink",
                r"require\s*\(\s*['\"]fs['\"]",
                r"process\.exit",
                r"eval\s*\(",
                r"Function\s*\("
            ],
            Language.BASH: [
                r"rm\s+-rf",
                r"dd\s+if=",
                r":(){ :|:& };:",  # Fork bomb
                r"chmod\s+777",
                r"curl\s+.*\s*\|\s*bash",
                r"wget\s+.*\s*-O\s*-\s*\|\s*bash"
            ]
        }

    def validate(
        self,
        code: str,
        language: Language,
        allow_dangerous: bool = False
    ) -> Tuple[bool, List[str]]:
        """Validate code for security issues."""
        import re

        warnings = []

        if allow_dangerous:
            return True, []

        patterns = self._dangerous_patterns.get(language, [])

        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                warnings.append(
                    f"Potentially dangerous pattern: {pattern}"
                )

        is_valid = len(warnings) == 0
        return is_valid, warnings


# =============================================================================
# SECURE EXECUTOR
# =============================================================================

class SecureSandboxExecutor:
    """Secure sandbox executor with validation."""

    def __init__(self, sandbox_type: SandboxType = SandboxType.DOCKER):
        self._executor = SandboxExecutor(sandbox_type)
        self._validator = CodeValidator()
        self._execution_log: List[Dict[str, Any]] = []

    async def execute_secure(
        self,
        request: ExecutionRequest,
        validate: bool = True,
        log: bool = True
    ) -> ExecutionResult:
        """Execute code with security validation."""
        # Validate
        if validate:
            is_valid, warnings = self._validator.validate(
                request.code,
                request.language
            )

            if not is_valid:
                result = ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error=f"Security validation failed: {warnings}"
                )

                if log:
                    self._log_execution(request, result, warnings)

                return result

        # Execute
        result = await self._executor.execute(request)

        # Log
        if log:
            self._log_execution(request, result)

        return result

    def _log_execution(
        self,
        request: ExecutionRequest,
        result: ExecutionResult,
        warnings: Optional[List[str]] = None
    ):
        """Log execution for audit."""
        self._execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "language": request.language.value,
            "code_hash": hashlib.sha256(
                request.code.encode()
            ).hexdigest()[:16],
            "status": result.status.value,
            "exit_code": result.exit_code,
            "execution_time": result.execution_time,
            "warnings": warnings or []
        })

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get execution audit log."""
        return self._execution_log.copy()


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def main():
    """Demonstrate sandbox execution."""
    executor = SandboxExecutor(SandboxType.SUBPROCESS)

    print("Available sandbox providers:", executor.get_available_providers())
    print("Supported languages:", executor.get_supported_languages())

    # Execute Python code
    print("\n--- Python Execution ---")
    result = await executor.execute_python("""
import math
print(f"Pi is approximately {math.pi:.6f}")
print(f"Square root of 2: {math.sqrt(2):.6f}")

for i in range(5):
    print(f"Fibonacci {i}: {i if i < 2 else 'computed'}")
""")

    print(f"Status: {result.status.value}")
    print(f"Exit code: {result.exit_code}")
    print(f"Execution time: {result.execution_time:.3f}s")
    print(f"Output:\n{result.stdout}")

    # Execute JavaScript
    print("\n--- JavaScript Execution ---")
    result = await executor.execute_javascript("""
console.log("Hello from JavaScript!");
const sum = [1, 2, 3, 4, 5].reduce((a, b) => a + b, 0);
console.log(`Sum of 1-5: ${sum}`);
""")

    print(f"Status: {result.status.value}")
    print(f"Output:\n{result.stdout}")

    # Test timeout
    print("\n--- Timeout Test ---")
    result = await executor.execute_python(
        code="import time; time.sleep(10); print('Done')",
        timeout=2.0,
        limits=ResourceLimits(max_wall_time=2.0)
    )

    print(f"Status: {result.status.value}")
    print(f"Error: {result.error}")

    # Secure executor with validation
    print("\n--- Security Validation ---")
    validator = CodeValidator()

    # Safe code
    is_valid, warnings = validator.validate(
        "print('Hello, World!')",
        Language.PYTHON
    )
    print(f"Safe code valid: {is_valid}")

    # Dangerous code
    is_valid, warnings = validator.validate(
        "import subprocess; subprocess.run(['rm', '-rf', '/'])",
        Language.PYTHON
    )
    print(f"Dangerous code valid: {is_valid}")
    print(f"Warnings: {warnings}")


if __name__ == "__main__":
    asyncio.run(main())
