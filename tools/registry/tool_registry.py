"""
BAEL - Advanced Tool Registry
Dynamic tool discovery, registration, and management.

Features:
- Dynamic tool registration
- Tool discovery
- Permission management
- Usage tracking
- Tool versioning
- Dependency management
"""

import asyncio
import hashlib
import inspect
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ToolCategory(Enum):
    """Tool categories."""
    SYSTEM = "system"
    FILE = "file"
    NETWORK = "network"
    CODE = "code"
    DATA = "data"
    SEARCH = "search"
    BROWSER = "browser"
    AI = "ai"
    UTILITY = "utility"
    CUSTOM = "custom"


class ToolStatus(Enum):
    """Tool status."""
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class PermissionLevel(Enum):
    """Tool permission levels."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    UNRESTRICTED = "unrestricted"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ToolParameter:
    """A parameter for a tool."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema."""
        schema = {
            "type": self.type,
            "description": self.description
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class ToolDefinition:
    """Complete tool definition."""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = "Any"
    version: str = "1.0.0"
    author: str = "BAEL"
    status: ToolStatus = ToolStatus.ACTIVE
    permissions: Set[PermissionLevel] = field(default_factory=lambda: {PermissionLevel.READ})
    dependencies: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Generate tool ID."""
        return hashlib.md5(f"{self.name}:{self.version}".encode()).hexdigest()[:12]

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema for LLM."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        p.name: p.to_json_schema()
                        for p in self.parameters
                    },
                    "required": [p.name for p in self.parameters if p.required]
                }
            }
        }


@dataclass
class ToolUsage:
    """Track tool usage."""
    tool_name: str
    invocation_id: str
    timestamp: datetime
    parameters: Dict[str, Any]
    success: bool
    duration_ms: float
    result_size: int
    error: Optional[str] = None


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# ABSTRACT TOOL
# =============================================================================

class BaseTool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """Validate parameters against definition."""
        errors = []

        for param in self.definition.parameters:
            if param.required and param.name not in params:
                errors.append(f"Missing required parameter: {param.name}")
            elif param.name in params:
                value = params[param.name]
                if param.enum and value not in param.enum:
                    errors.append(
                        f"Invalid value for {param.name}: {value}. "
                        f"Must be one of: {param.enum}"
                    )

        return errors


# =============================================================================
# TOOL DECORATOR
# =============================================================================

def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: ToolCategory = ToolCategory.UTILITY,
    version: str = "1.0.0",
    permissions: Optional[Set[PermissionLevel]] = None,
    tags: Optional[Set[str]] = None
):
    """Decorator to create a tool from a function."""

    def decorator(func: Callable) -> Type[BaseTool]:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description"

        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = []

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls"]:
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object"
                }
                param_type = type_map.get(param.annotation, "string")

            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter: {param_name}",
                required=param.default == inspect.Parameter.empty,
                default=None if param.default == inspect.Parameter.empty else param.default
            ))

        definition = ToolDefinition(
            name=tool_name,
            description=tool_description,
            category=category,
            parameters=parameters,
            version=version,
            permissions=permissions or {PermissionLevel.READ},
            tags=tags or set()
        )

        class DecoratedTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return definition

            async def execute(self, **kwargs) -> ToolResult:
                import time
                start = time.time()

                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(**kwargs)
                    else:
                        result = func(**kwargs)

                    duration = (time.time() - start) * 1000

                    return ToolResult(
                        success=True,
                        output=result,
                        duration_ms=duration
                    )

                except Exception as e:
                    duration = (time.time() - start) * 1000
                    return ToolResult(
                        success=False,
                        output=None,
                        error=str(e),
                        duration_ms=duration
                    )

        DecoratedTool.__name__ = f"{tool_name}Tool"
        return DecoratedTool

    return decorator


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
        self._usage_log: List[ToolUsage] = []
        self._hooks: Dict[str, List[Callable]] = {
            "before_execute": [],
            "after_execute": [],
            "on_register": [],
            "on_unregister": []
        }

    def register(self, tool_class: Type[BaseTool]) -> None:
        """Register a tool."""
        instance = tool_class()
        definition = instance.definition

        self._tools[definition.name] = instance
        self._definitions[definition.name] = definition

        logger.info(f"Registered tool: {definition.name} v{definition.version}")

        # Fire hooks
        for hook in self._hooks["on_register"]:
            hook(definition)

    def register_instance(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        definition = tool.definition
        self._tools[definition.name] = tool
        self._definitions[definition.name] = definition
        logger.info(f"Registered tool instance: {definition.name}")

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            definition = self._definitions.get(name)
            del self._tools[name]
            del self._definitions[name]

            for hook in self._hooks["on_unregister"]:
                hook(definition)

            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition."""
        return self._definitions.get(name)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None,
        tags: Optional[Set[str]] = None
    ) -> List[ToolDefinition]:
        """List tools with optional filters."""
        definitions = list(self._definitions.values())

        if category:
            definitions = [d for d in definitions if d.category == category]

        if status:
            definitions = [d for d in definitions if d.status == status]

        if tags:
            definitions = [d for d in definitions if tags & d.tags]

        return definitions

    async def execute(
        self,
        name: str,
        **kwargs
    ) -> ToolResult:
        """Execute a tool."""
        import time

        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool not found: {name}"
            )

        # Validate parameters
        errors = tool.validate_parameters(kwargs)
        if errors:
            return ToolResult(
                success=False,
                output=None,
                error="; ".join(errors)
            )

        # Fire before hooks
        for hook in self._hooks["before_execute"]:
            await hook(name, kwargs) if asyncio.iscoroutinefunction(hook) else hook(name, kwargs)

        # Execute
        start = time.time()
        invocation_id = hashlib.md5(
            f"{name}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        result = await tool.execute(**kwargs)

        duration = (time.time() - start) * 1000

        # Log usage
        usage = ToolUsage(
            tool_name=name,
            invocation_id=invocation_id,
            timestamp=datetime.now(),
            parameters=kwargs,
            success=result.success,
            duration_ms=duration,
            result_size=len(str(result.output)) if result.output else 0,
            error=result.error
        )
        self._usage_log.append(usage)

        # Fire after hooks
        for hook in self._hooks["after_execute"]:
            await hook(name, result) if asyncio.iscoroutinefunction(hook) else hook(name, result)

        return result

    def add_hook(self, event: str, handler: Callable) -> None:
        """Add an event hook."""
        if event in self._hooks:
            self._hooks[event].append(handler)

    def get_usage_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics."""
        logs = self._usage_log
        if tool_name:
            logs = [l for l in logs if l.tool_name == tool_name]

        if not logs:
            return {"total_calls": 0}

        successful = [l for l in logs if l.success]
        durations = [l.duration_ms for l in logs]

        return {
            "total_calls": len(logs),
            "successful_calls": len(successful),
            "failed_calls": len(logs) - len(successful),
            "success_rate": len(successful) / len(logs),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations)
        }

    def get_json_schemas(self) -> List[Dict[str, Any]]:
        """Get JSON schemas for all active tools."""
        return [
            d.to_json_schema()
            for d in self._definitions.values()
            if d.status == ToolStatus.ACTIVE
        ]


# =============================================================================
# BUILT-IN TOOLS
# =============================================================================

class EchoTool(BaseTool):
    """Simple echo tool for testing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="echo",
            description="Echo back the input message",
            category=ToolCategory.UTILITY,
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="The message to echo"
                )
            ]
        )

    async def execute(self, message: str = "") -> ToolResult:
        return ToolResult(
            success=True,
            output=f"Echo: {message}"
        )


class CalculatorTool(BaseTool):
    """Basic calculator tool."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="Perform basic arithmetic calculations",
            category=ToolCategory.UTILITY,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Mathematical expression to evaluate"
                )
            ],
            examples=[
                {"expression": "2 + 2", "result": 4},
                {"expression": "10 * 5", "result": 50}
            ]
        )

    async def execute(self, expression: str = "") -> ToolResult:
        try:
            # Safe evaluation (basic)
            allowed = set("0123456789+-*/().% ")
            if not all(c in allowed for c in expression):
                raise ValueError("Invalid characters in expression")

            result = eval(expression, {"__builtins__": {}})
            return ToolResult(success=True, output=result)

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ShellTool(BaseTool):
    """Execute shell commands."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="shell",
            description="Execute shell commands",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="Shell command to execute"
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds",
                    required=False,
                    default=30
                )
            ],
            permissions={PermissionLevel.EXECUTE, PermissionLevel.ADMIN}
        )

    async def execute(
        self,
        command: str = "",
        timeout: int = 30
    ) -> ToolResult:
        import subprocess

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = result.stdout or result.stderr
            success = result.returncode == 0

            return ToolResult(
                success=success,
                output=output,
                error=result.stderr if not success else None,
                metadata={"return_code": result.returncode}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=None,
                error=f"Command timed out after {timeout}s"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class HTTPTool(BaseTool):
    """Make HTTP requests."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="http",
            description="Make HTTP requests",
            category=ToolCategory.NETWORK,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="URL to request"
                ),
                ToolParameter(
                    name="method",
                    type="string",
                    description="HTTP method",
                    required=False,
                    default="GET",
                    enum=["GET", "POST", "PUT", "DELETE", "PATCH"]
                ),
                ToolParameter(
                    name="headers",
                    type="object",
                    description="HTTP headers",
                    required=False
                ),
                ToolParameter(
                    name="body",
                    type="object",
                    description="Request body",
                    required=False
                )
            ],
            permissions={PermissionLevel.EXECUTE}
        )

    async def execute(
        self,
        url: str = "",
        method: str = "GET",
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None
    ) -> ToolResult:
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=body if method != "GET" else None
                ) as response:
                    text = await response.text()

                    return ToolResult(
                        success=response.status < 400,
                        output=text,
                        metadata={
                            "status_code": response.status,
                            "headers": dict(response.headers)
                        }
                    )

        except ImportError:
            return ToolResult(
                success=False,
                output=None,
                error="aiohttp not installed"
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# =============================================================================
# TOOL DISCOVERY
# =============================================================================

class ToolDiscovery:
    """Discover tools from modules and packages."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def discover_from_module(self, module: Any) -> int:
        """Discover tools from a module."""
        count = 0

        for name in dir(module):
            obj = getattr(module, name)

            if (
                isinstance(obj, type) and
                issubclass(obj, BaseTool) and
                obj is not BaseTool
            ):
                try:
                    self.registry.register(obj)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to register {name}: {e}")

        return count

    def discover_from_path(self, path: str) -> int:
        """Discover tools from a file path."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("tools_module", path)
        if not spec or not spec.loader:
            return 0

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return self.discover_from_module(module)


# =============================================================================
# DEFAULT REGISTRY
# =============================================================================

def create_default_registry() -> ToolRegistry:
    """Create a registry with built-in tools."""
    registry = ToolRegistry()

    # Register built-in tools
    registry.register(EchoTool)
    registry.register(CalculatorTool)
    registry.register(ShellTool)
    registry.register(HTTPTool)

    return registry


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def example_registry():
    """Demonstrate tool registry."""
    registry = create_default_registry()

    # List tools
    print("Available tools:")
    for tool_def in registry.list_tools():
        print(f"  - {tool_def.name}: {tool_def.description}")

    # Execute echo
    result = await registry.execute("echo", message="Hello, BAEL!")
    print(f"\nEcho result: {result.output}")

    # Execute calculator
    result = await registry.execute("calculator", expression="(5 + 3) * 2")
    print(f"Calculator result: {result.output}")

    # Create tool with decorator
    @tool(
        name="greet",
        description="Generate a greeting",
        category=ToolCategory.UTILITY
    )
    def greet(name: str, formal: bool = False) -> str:
        if formal:
            return f"Good day, {name}."
        return f"Hey {name}!"

    registry.register(greet)

    result = await registry.execute("greet", name="BAEL", formal=True)
    print(f"Greet result: {result.output}")

    # Get stats
    stats = registry.get_usage_stats()
    print(f"\nUsage stats: {stats}")

    # Get JSON schemas
    schemas = registry.get_json_schemas()
    print(f"\nTool schemas: {len(schemas)} tools")


if __name__ == "__main__":
    asyncio.run(example_registry())
